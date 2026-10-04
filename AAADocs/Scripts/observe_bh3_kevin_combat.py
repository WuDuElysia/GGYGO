"""PIE combat evidence observer. Importing this file performs no UE operations.

Explicit use after creating an isolated server PIE encounter:
    observer = start(source_avatar, target_avatar, label='Ice01_contact', seconds=8)
    # Activate the granted GA through its ASC separately.
    observer.mark('cancel_requested')  # immediately before an explicit interruption
    observer.stop()                    # optional; timeout also removes all listeners

Does not spawn actors, activate abilities, move targets, apply effects, or save assets.
Writes observations under Saved/Codex. Evidence is not an automatic gameplay PASS.
"""
import json
import math
from pathlib import Path
import re
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
_active = None


class CombatObserver:
    def __init__(self, source, target, label, seconds):
        import unreal
        self.ue = unreal
        assert source and target and source != target, '需要两个不同的 PIE Avatar'
        assert math.isfinite(seconds) and 0 < seconds <= 60, '观察时长必须为 (0, 60] 秒'
        self.world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_game_world()
        assert self.world, '需要活动 PIE 世界'
        actors = unreal.GameplayStatics.get_all_actors_of_class(self.world, unreal.Actor)
        assert source in actors and target in actors, '不能观察编辑器世界或其他 PIE 实例的 Actor'
        assert source.has_authority(), '在服务器实例观察权威判定'
        self.source, self.target = source, target
        self.source_path, self.target_path = source.get_path_name(), target.get_path_name()
        self.mesh = source.get_editor_property('Mesh')
        self.trace = source.get_component_by_class(unreal.GGYGOMeleeTraceComponent)
        self.movement = source.get_component_by_class(unreal.GGYGOCharacterMovementComponent)
        self.health = target.get_component_by_class(unreal.GGYGOHealthComponent)
        assert self.mesh and self.trace and self.movement and self.health, '缺少被测组件'
        assert self.health.get_health() > 0, '目标必须存活且完成 ASC/Health 初始化'
        self.label = re.sub(r'[^A-Za-z0-9_-]', '_', label)[:80] or 'observation'
        self.deadline = time.monotonic() + seconds
        self.started_game_time = unreal.GameplayStatics.get_time_seconds(self.world)
        self.samples, self.events, self.errors = [], [], []
        self.bindings = []
        self.tick_handle = None
        self.stopped = False
        self.initial = self.snapshot()

    @staticmethod
    def vector(value):
        return [float(value.x), float(value.y), float(value.z)]

    def snapshot(self):
        anim = self.mesh.get_anim_instance()
        montage = anim.get_current_active_montage() if anim else None
        return {
            'game_seconds': self.ue.GameplayStatics.get_time_seconds(self.world) - self.started_game_time,
            'montage': montage.get_path_name() if montage else None,
            'montage_seconds': float(anim.montage_get_position(montage)) if montage else None,
            'trace_open': bool(self.trace.is_tracing()),
            'action_motion_active': bool(self.movement.has_active_action_motion()),
            'source_location_cm': self.vector(self.source.get_actor_location()),
            'target_location_cm': self.vector(self.target.get_actor_location()),
            'target_health': float(self.health.get_health()),
            'mesh_tick_option': str(self.mesh.get_editor_property('VisibilityBasedAnimTickOption')),
            'mesh_uro': bool(self.mesh.get_editor_property('bEnableUpdateRateOptimizations')),
        }

    def mark(self, name):
        self.events.append({'kind': 'marker', 'name': str(name), **self.snapshot()})

    def on_hit(self, actor, hit):
        self.events.append({'kind': 'trace_hit', 'actor': actor.get_path_name() if actor else None,
            'is_test_target': actor == self.target, 'impact_cm': self.vector(hit.impact_point), **self.snapshot()})

    def on_health(self, component, old_value, new_value, instigator):
        self.events.append({'kind': 'health_changed', 'old': float(old_value), 'new': float(new_value),
            'instigator': instigator.get_path_name() if instigator else None, **self.snapshot()})

    def begin(self):
        try:
            for component, name, callback in [(self.trace, 'OnMeleeHit', self.on_hit),
                                               (self.health, 'OnHealthChanged', self.on_health)]:
                delegate = component.get_editor_property(name)
                delegate.add_callable(callback)
                self.bindings.append((delegate, callback))
            self.tick_handle = self.ue.register_slate_post_tick_callback(self.tick)
            self.mark('observation_started')
        except Exception as exc:
            self.errors.append(str(exc))
            self.stop('setup_error')
            raise
        return self

    def tick(self, delta_seconds):
        if self.stopped:
            return
        try:
            world = self.ue.get_editor_subsystem(self.ue.UnrealEditorSubsystem).get_game_world()
            if world != self.world:
                self.stop('PIE_world_changed')
                return
            self.samples.append(self.snapshot())
            if time.monotonic() >= self.deadline:
                self.stop('observation_timeout')
        except Exception as exc:
            self.errors.append(str(exc))
            self.stop('sampling_error')

    def stop(self, reason='manual_stop'):
        if self.stopped:
            return
        self.stopped = True
        if self.tick_handle is not None:
            try:
                self.ue.unregister_slate_post_tick_callback(self.tick_handle)
            except Exception as exc:
                self.errors.append('tick_cleanup: ' + str(exc))
            self.tick_handle = None
        for delegate, callback in self.bindings:
            try:
                delegate.remove_callable(callback)
            except Exception as exc:
                self.errors.append('delegate_cleanup: ' + str(exc))
        self.bindings.clear()
        report = {'status': 'observed_requires_review' if not self.errors else 'observer_error',
            'label': self.label, 'stop_reason': reason, 'source': self.source_path,
            'target': self.target_path, 'initial': self.initial,
            'events': self.events, 'samples': self.samples, 'errors': self.errors,
            'limitations': ['Slate samples may miss short windows; use hit/health delegates and native logs.',
                            'No automatic selection, multiplayer or original-game-hitbox claim.']}
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S_%fZ')
        output = ROOT / 'Saved/Codex' / ('kevin_combat_observe_' + self.label + '_' + stamp + '.json')
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
        self.ue.log('KEVIN_COMBAT_OBSERVATION ' + str(output))
        return report


def start(source_avatar, target_avatar, label='combat', seconds=8.0):
    global _active
    if _active and not _active.stopped:
        raise RuntimeError('上一次观察仍在运行；先调用 stop()')
    _active = CombatObserver(source_avatar, target_avatar, label, seconds).begin()
    return _active
