"""Single-owner PIE probe. Import is inert; call start(), or execute as __main__.

38 seconds: settle 1, forward 31, reverse 3, release 3. Timing is editor ticker
time (not simulation time). No movement/animation/input assets are edited.
"""
import json
from pathlib import Path
import sys
from types import ModuleType
from uuid import uuid4
import unreal

# A separate session slot survives importlib.reload and repeated console exec.
_SESSION_KEY = '_ggygo_movement_level_probe_session'
if _SESSION_KEY not in sys.modules:
    sys.modules[_SESSION_KEY] = ModuleType(_SESSION_KEY)
    sys.modules[_SESSION_KEY].active = None
_session = sys.modules[_SESSION_KEY]
_THROTTLE = 'bThrottleCPUWhenNotForeground'


class MovementLevelProbe:
    def __init__(self):
        self.handle = None
        self.restore_pending = False
        self.input_used = False
        self.stopped = False
        self.reason = None
        self.errors = []
        self.samples = []
        self.elapsed = 0.0
        self.report_written = False
        self.world = self.pawn = self.move = self.anim = None
        self.inputs = self.action = self.performance = None
        self.output = (Path(unreal.Paths.convert_relative_path_to_full(
            unreal.Paths.project_saved_dir())) / 'LevelDesign' /
            ('movement_runtime_' + uuid4().hex + '.json'))

    def begin(self):
        if _session.active is not self or self.handle is not None or self.stopped:
            raise RuntimeError('Use start() to acquire the single probe owner')
        worlds = unreal.EditorLevelLibrary.get_pie_worlds(False)
        if len(worlds) != 1 or worlds[0].get_path_name().split('.')[-1] != 'L_Movement_Test':
            raise RuntimeError('Expected exactly one L_Movement_Test PIE world')
        self.world = worlds[0]
        self.pawn = unreal.GameplayStatics.get_player_pawn(self.world, 0)
        if not self.pawn:
            raise RuntimeError('No player pawn')
        self.move = self.pawn.get_movement_component()
        self.anim = self.pawn.mesh.get_anim_instance()
        subs = [s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem)
                if s.get_path_name().startswith('/Engine/Transient.')]
        if len(subs) != 1:
            raise RuntimeError('Expected one PIE local player input subsystem')
        self.inputs = subs[0]
        self.action = unreal.load_asset('/Game/Input/Actions/IA_Move')
        if not all((self.move, self.anim, self.action)):
            raise RuntimeError('Missing movement, animation or IA_Move')
        self.anim.get_editor_property('animation_state')
        self.anim.get_editor_property('state_memory').gait_blend_y
        self.performance = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
        self.throttle = self.performance.get_editor_property(_THROTTLE)
        self.restore_pending = True
        self.performance.set_editor_property(_THROTTLE, False)
        self.handle = unreal.register_ticker_callback(self.tick)
        if self.handle is None:
            raise RuntimeError('Ticker registration returned no handle')
        return self

    def tick(self, dt):
        if self.stopped:
            # If explicit unregister failed, FTSTicker retires this callback.
            self.handle = None
            self.stop(self.reason)
            return False
        try:
            if self.world not in unreal.EditorLevelLibrary.get_pie_worlds(False):
                self.stop('pie_ended_or_world_changed')
                return False
            if unreal.GameplayStatics.get_player_pawn(self.world, 0) != self.pawn:
                self.stop('pawn_changed')
                return False
            self.elapsed += dt
            axis = 1.0 if 1 <= self.elapsed < 32 else (-1.0 if 32 <= self.elapsed < 35 else 0.0)
            self.input_used = True
            self.inputs.inject_input_vector_for_action(self.action, unreal.Vector(0, axis, 0), [], [])
            state = self.anim.get_editor_property('animation_state')
            loc = self.pawn.get_actor_location()
            self.samples.append(dict(time=round(self.elapsed, 4), axis=axis,
                location_cm=[loc.x, loc.y, loc.z], gait=str(self.move.get_resolved_gait()),
                speed_cm_s=state.horizontal_speed, grounded=state.grounded,
                movement_mode=str(self.move.movement_mode), has_move_input=state.has_move_input,
                turn_back_phase=str(state.turn_back_phase), yaw=self.pawn.get_actor_rotation().yaw,
                blend=self.anim.get_editor_property('state_memory').gait_blend_y))
            if self.elapsed >= 38:
                self.stop('completed')
                return False
            return True
        except Exception as error:
            self.errors.append('sample: ' + str(error))
            self.stop('sample_error')
            return False

    def stop(self, reason='manual_stop'):
        if (self.report_written and self.handle is None and not self.restore_pending
                and _session.active is not self):
            return self
        self.stopped = True
        self.reason = self.reason or reason
        try:
            if self.handle is not None:
                try:
                    unreal.unregister_ticker_callback(self.handle)
                    self.handle = None
                except Exception as error:
                    self.errors.append('unregister: ' + str(error))
            if self.inputs is not None and self.input_used:
                try:
                    self.inputs.inject_input_vector_for_action(self.action, unreal.Vector(0, 0, 0), [], [])
                except Exception as error:
                    self.errors.append('release_input: ' + str(error))
                finally:
                    self.input_used = False
        finally:
            # Never put restoration after an unguarded input/PIE operation.
            if self.restore_pending:
                try:
                    self.performance.set_editor_property(_THROTTLE, self.throttle)
                    self.restore_pending = False
                    self.performance = None
                except Exception as error:
                    self.errors.append('restore_setting: ' + str(error))
            self.world = self.pawn = self.move = self.anim = None
            self.inputs = self.action = None
            cleanup_pending = self.handle is not None or self.restore_pending
            if not cleanup_pending and _session.active is self:
                _session.active = None
            self.report_written = False
            try:
                self.output.parent.mkdir(parents=True, exist_ok=True)
                self.output.write_text(json.dumps(dict(
                    status=('completed' if self.reason == 'completed' and not self.errors else 'stopped_or_error'),
                    reason=self.reason, cleanup_pending=cleanup_pending,
                    clock='editor_ticker_seconds', runtime_acceptance_verified=False,
                    errors=self.errors, samples=self.samples), indent=2), encoding='utf-8')
                self.report_written = True
                unreal.log('MovementLevelProbe: ' + str(self.output))
            except Exception as error:
                unreal.log_error('MovementLevelProbe report failed: ' + str(error))
        return self

    def finish(self):
        """Compatibility alias; manual completion is not a 38-second success."""
        return self.stop()


def start():
    active = _session.active
    if active is not None:
        if active.stopped:
            raise RuntimeError('Previous probe cleanup is pending; call stop() to retry')
        return active
    probe = MovementLevelProbe()
    _session.active = probe
    try:
        return probe.begin()
    except Exception:
        probe.stop('startup_error')
        raise


def stop():
    """Stop current owner, including retrying a failed resource release."""
    if _session.active is not None:
        return _session.active.stop()
    return None


if __name__ == '__main__':
    movement_level_probe = start()
