"""Passive observation of the saved /Game/Map/Untitled production PIE chain.

Import is inert. In the editor Python console (the coordinator owns UE):
    import runpy
    probe = runpy.run_path(r'F:/ue_project/GGYGO/AAADocs/Scripts/observe_formal_movement_pie.py')
    probe['verify_reflection']()  # All required Python methods/properties, no PIE needed.
    probe['start'](begin_play=True, duration_seconds=90)
    probe['mark']('physical W hold / release / repress')
    probe['stop'](end_play=True)

With an existing PIE, use start() without begin_play. The observation deadline
unregisters its Slate callback; PIE remains under the coordinator's control.
Explicit stop(end_play=True), while observation is active, requests native End PIE
for the captured world. After stopping, object references are released; End PIE
then belongs to the coordinator's native UI.
No input injection, movement writes, mapping changes, asset saves or settings edits.
Controller key state is sampled; the actual keyboard operation is performed by
the user. Non-reflected Source/Scope/receipt identity and networking are not proved.
"""

import json
import math
import re
import sys
import time
from types import ModuleType

import unreal


_MAP = '/Game/Map/Untitled'
_SLOT = '_ggygo_formal_movement_observer'
if _SLOT not in sys.modules:
    sys.modules[_SLOT] = ModuleType(_SLOT)
    sys.modules[_SLOT].active = None
    sys.modules[_SLOT].last = None
_session = sys.modules[_SLOT]


def _emit(event, **fields):
    unreal.log('[FormalMovement] ' + json.dumps(dict(event=event, **fields), ensure_ascii=False))


def _map_path(world):
    return re.sub(r'/UEDPIE_\d+_', '/', world.get_path_name().split('.')[0])


_FRAME_FIELDS = {'walk_run_blend_alpha': 'WalkRunBlendAlpha', 'gait': 'Gait',
                 'has_move_input': 'bHasMoveInput', 'grounded': 'bGrounded',
                 'movement_blocked': 'bMovementBlocked', 'turn_back_phase': 'TurnBackPhase'}


def verify_reflection():
    """Check every required reflected surface together; any missing field rejects startup."""
    failures = []
    surfaces = (
        ('unreal', unreal, ('get_default_object', 'get_editor_subsystem',
                           'register_slate_post_tick_callback', 'unregister_slate_post_tick_callback', 'log', 'log_error')),
        ('Object', unreal.Object, ('get_editor_property', 'get_path_name', 'get_class')),
        ('Key', unreal.Key, ('set_editor_property',)),
        ('GameplayStatics', unreal.GameplayStatics, ('get_player_controller', 'get_time_seconds')),
        ('Controller', unreal.Controller, ('get_controlled_pawn',)),
        ('Pawn', unreal.Pawn, ('get_controller',)),
        ('PlayerController', unreal.PlayerController, ('is_input_key_down',)),
        ('Actor', unreal.Actor, ('get_actor_location', 'get_actor_rotation', 'get_velocity')),
        ('SkeletalMeshComponent', unreal.SkeletalMeshComponent, ('get_anim_instance',)),
        ('CMC', unreal.GGYGOCharacterMovementComponent, ('get_resolved_gait', 'get_locomotion_motion_type',
                'get_stop_motion_type', 'is_force_walk_requested', 'get_walk_run_blend_alpha', 'get_movement_set')),
        ('EditorLevelLibrary', unreal.EditorLevelLibrary, ('get_pie_worlds',)),
        ('LevelEditorSubsystem', unreal.LevelEditorSubsystem,
                ('is_in_play_in_editor', 'editor_request_begin_play', 'editor_request_end_play')),
        ('UnrealEditorSubsystem', unreal.UnrealEditorSubsystem, ('get_editor_world',)),
    )
    for label, owner, required in surfaces:
        missing = sorted(set(required) - set(dir(owner)))
        if missing:
            failures.append(label + ' missing methods: ' + ', '.join(missing))
    # CDO reads check names/access only. They do not assert live configuration or spawn substitutes.
    # Protected owner/configuration fields are queried through public reflected getters.
    properties = ((unreal.Character, ('CharacterMovement', 'Mesh')),
                  (unreal.GGYGOMovementSet, ('WalkToRunHoldSeconds', 'WalkRunBlendInterpSpeed')),
                  (unreal.ZZZAnimInstance, ('AnimationState', 'StateMemory')))
    for owner_type, required in properties:
        owner = unreal.get_default_object(owner_type)
        for name in required:
            try:
                value = owner.get_editor_property(name)
                fields = _FRAME_FIELDS.values() if name == 'AnimationState' else ('GaitBlendY',) if name == 'StateMemory' else ()
                for field in fields:
                    try:
                        value.get_editor_property(field)
                    except Exception as error:
                        failures.append(owner_type.__name__ + '.' + name + '.' + field + ': ' + str(error))
            except Exception as error:
                failures.append(owner_type.__name__ + '.' + name + ': ' + str(error))
    if failures:
        raise RuntimeError('Required UE Python reflection is unavailable:\n' + '\n'.join(failures))
    _emit('reflection_surface_checked', surface_count=len(surfaces), live_movement_verified=False)


class FormalMovementObserver:
    def __init__(self, duration_seconds, begin_play):
        self.started = time.monotonic()
        self.deadline = self.started + duration_seconds
        self.bind_deadline = self.started + 15.0
        self.handle = None
        self.stopped = False
        self.reason = None
        self.origin = 'registered_before_native_begin' if begin_play else 'attached_to_existing_pie'
        self.world = self.pc = self.pawn = self.move = self.mesh = self.anim = None
        self.movement_set = None
        self.keys = {}
        for name in ('W', 'A', 'S', 'D'):
            key = unreal.Key()
            key.set_editor_property('KeyName', name)
            self.keys[name] = key
        self.samples = []
        self.next_sample = self.started
        self.next_log = self.started
        self.last_signature = None

    def _bind(self, worlds):
        if len(worlds) > 1:
            raise RuntimeError('Expected one local PIE world; multi-world PIE is outside this observation')
        if self.world is None:
            if not worlds:
                return False
            if _map_path(worlds[0]) != _MAP:
                raise RuntimeError('PIE map differs from saved production map: ' + worlds[0].get_path_name())
            self.world = worlds[0]
        if worlds != [self.world]:
            raise RuntimeError('Original PIE world ended or was replaced')
        current_pc = unreal.GameplayStatics.get_player_controller(self.world, 0)
        if self.pc is None:
            if current_pc is None:
                return False
            self.pc = current_pc
        elif current_pc != self.pc:
            raise RuntimeError('Original PlayerController was replaced')
        # K2_GetPawn has ScriptName=GetControlledPawn in UE5.8; GetPawn is plain C++.
        current_pawn = self.pc.get_controlled_pawn()
        if self.pawn is None:
            if current_pawn is None:
                return False
            self.pawn = current_pawn
        elif current_pawn != self.pawn:
            raise RuntimeError('Original possessed Pawn changed')
        pawn_controller = self.pawn.get_controller()
        if pawn_controller is None:
            return False  # Bounded native possession readiness, never a replacement Pawn.
        if pawn_controller != self.pc:
            raise RuntimeError('Original Pawn is possessed by a different Controller')
        if self.pawn.get_class().get_path_name() != '/Game/BP/Character/Player/BP_PC_Pyrios.BP_PC_Pyrios_C':
            raise RuntimeError('Unexpected production Pawn: ' + self.pawn.get_class().get_path_name())
        # GetCharacterMovement is plain C++; CharacterMovement is the reflected subobject.
        current_move = self.pawn.get_editor_property('CharacterMovement')
        current_mesh = self.pawn.get_editor_property('Mesh')
        if self.move is None:
            self.move = current_move
        elif current_move != self.move:
            raise RuntimeError('Original CMC changed during native initialization')
        if self.mesh is None:
            self.mesh = current_mesh
        elif current_mesh != self.mesh:
            raise RuntimeError('Original Mesh changed during native initialization')
        if not isinstance(self.move, unreal.GGYGOCharacterMovementComponent) or self.mesh is None:
            raise RuntimeError('Production Pawn has no project CMC or Mesh')
        current_anim = self.mesh.get_anim_instance()
        if current_anim is None:
            return False  # Native Mesh initialization may follow possession; bounded by bind_deadline.
        self.anim = current_anim
        if self.anim.get_class().get_path_name() != '/Game/BP/Anim/ABP_Pyrios.ABP_Pyrios_C':
            raise RuntimeError('Unexpected production AnimInstance: ' + self.anim.get_class().get_path_name())
        self.movement_set = self.move.get_movement_set()
        if self.movement_set is None:
            raise RuntimeError('Original CMC ' + self.move.get_path_name() + ' has no accepted MovementSet')
        _emit('bound', observation_origin=self.origin, world=self.world.get_path_name(), pc=self.pc.get_path_name(),
              pawn=self.pawn.get_path_name(), cmc=self.move.get_path_name(), anim=self.anim.get_path_name(),
              movement_set=self.movement_set.get_path_name(),
              walk_to_run_hold_seconds=self.movement_set.get_editor_property('WalkToRunHoldSeconds'),
              blend_interp_speed=self.movement_set.get_editor_property('WalkRunBlendInterpSpeed'))
        return True

    def _sample(self, now):
        if unreal.GameplayStatics.get_player_controller(self.world, 0) != self.pc:
            raise RuntimeError('Original PlayerController was replaced')
        if self.pc.get_controlled_pawn() != self.pawn or self.pawn.get_controller() != self.pc:
            raise RuntimeError('Original possessed Pawn changed')
        if self.pawn.get_editor_property('CharacterMovement') != self.move or self.pawn.get_editor_property('Mesh') != self.mesh:
            raise RuntimeError('Original CMC or Mesh changed')
        if self.mesh.get_anim_instance() != self.anim or self.move.get_movement_set() != self.movement_set:
            raise RuntimeError('Original AnimInstance or MovementSet changed')
        state = self.anim.get_editor_property('AnimationState')
        memory = self.anim.get_editor_property('StateMemory')
        frame = {name: state.get_editor_property(native_name) for name, native_name in _FRAME_FIELDS.items()}
        location = self.pawn.get_actor_location()
        velocity = self.pawn.get_velocity()
        sample = dict(wall_seconds=round(now - self.started, 3),
                      game_seconds=round(unreal.GameplayStatics.get_time_seconds(self.world), 3),
                      keys_down=[name for name, key in self.keys.items() if self.pc.is_input_key_down(key)],
                      gait=str(self.move.get_resolved_gait()),
                      motion=str(self.move.get_locomotion_motion_type()),
                      stop=str(self.move.get_stop_motion_type()), force_walk=self.move.is_force_walk_requested(),
                      cmc_alpha=self.move.get_walk_run_blend_alpha(), frame_alpha=frame['walk_run_blend_alpha'],
                      anim_alpha=memory.get_editor_property('GaitBlendY'), frame_gait=str(frame['gait']),
                      has_move_input=frame['has_move_input'], grounded=frame['grounded'],
                      movement_blocked=frame['movement_blocked'], turn_back_phase=str(frame['turn_back_phase']),
                      speed_cm_s=math.hypot(velocity.x, velocity.y),
                      position_cm=[location.x, location.y, location.z], yaw=self.pawn.get_actor_rotation().yaw)
        self.samples.append(sample)
        signature = (tuple(sample['keys_down']), sample['gait'], sample['motion'], sample['stop'],
                     sample['force_walk'], sample['has_move_input'], sample['grounded'], sample['movement_blocked'])
        if signature != self.last_signature or now >= self.next_log:
            _emit('sample', **sample)
            self.last_signature = signature
            self.next_log = now + 0.5

    def tick(self, _delta_seconds):
        if self.stopped:
            return
        try:
            now = time.monotonic()
            if now >= self.deadline:
                self.stop('observation_deadline')
                return
            worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(True))
            if self.movement_set is None:
                if now >= self.bind_deadline:
                    raise RuntimeError('Native PIE/possession/AnimInstance did not become ready within 15 seconds')
                if not self._bind(worlds):
                    return
            elif worlds != [self.world]:
                raise RuntimeError('Original PIE world ended or was replaced')
            if now >= self.next_sample:
                self._sample(now)
                self.next_sample = now + 0.1
        except Exception as error:
            unreal.log_error('[FormalMovement] observation failed: ' + str(error))
            self.stop('observation_error')

    def stop(self, reason='manual_stop', end_play=False):
        self.stopped = True
        self.reason = self.reason or reason
        if self.handle is not None:
            # A failed unregister remains an explicit, retryable resource, never reported as clean.
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
        try:
            if end_play:
                worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(True))
                if self.world is None or worlds != [self.world]:
                    raise RuntimeError('Refusing End PIE: the original captured world is no longer the sole PIE world')
                unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_end_play()
        finally:
            self.world = self.pc = self.pawn = self.move = self.mesh = self.anim = self.movement_set = None
            if _session.active is self:
                _session.active = None
            _session.last = self
        summary = dict(reason=self.reason, sample_count=len(self.samples),
                       observed_gaits=sorted({sample['gait'] for sample in self.samples}),
                       callback_released=self.handle is None, end_play_requested=end_play)
        _emit('stopped', **summary)
        return summary


def start(begin_play=False, duration_seconds=90):
    """Begin one bounded observer; optional Begin PIE uses the native active viewport."""
    if _session.active is not None:
        raise RuntimeError('An observer already owns the callback; stop it before starting another')
    if not math.isfinite(duration_seconds) or not 15 <= duration_seconds <= 180:
        raise ValueError('duration_seconds must be finite and between 15 and 180')
    verify_reflection()
    worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(True))
    if begin_play:
        if worlds or unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).is_in_play_in_editor():
            raise RuntimeError('Begin PIE requires no existing PIE session')
        editor_world = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem).get_editor_world()
        if editor_world is None or _map_path(editor_world) != _MAP:
            raise RuntimeError('Open the saved /Game/Map/Untitled map before Begin PIE')
    elif len(worlds) != 1 or _map_path(worlds[0]) != _MAP:
        raise RuntimeError('Attach requires exactly one PIE world from /Game/Map/Untitled')
    observer = FormalMovementObserver(duration_seconds, begin_play)
    _session.active = observer
    try:
        observer.handle = unreal.register_slate_post_tick_callback(observer.tick)
        if observer.handle is None:
            raise RuntimeError('Slate callback registration returned no handle')
        if begin_play:
            unreal.get_editor_subsystem(unreal.LevelEditorSubsystem).editor_request_begin_play()
        _emit('started', observation_origin=observer.origin, begin_play_requested=begin_play, duration_seconds=duration_seconds,
              source_first_sync_verified=False,
              instruction='User performs actual first W hold, release to neutral, then repress; no injected input')
        return observer
    except Exception:
        observer.stop('startup_error')
        raise


def mark(label):
    """Record a human annotation; it does not certify the marked behavior."""
    observer = _session.active
    if observer is None:
        raise RuntimeError('No active observer')
    _emit('mark', label=str(label), wall_seconds=round(time.monotonic() - observer.started, 3))


def stop(end_play=False):
    """Release observation; optionally request native End PIE for its original world."""
    observer = _session.active if _session.active is not None else _session.last
    return observer.stop(end_play=end_play) if observer is not None else None


def samples():
    """Return the actual captured samples in memory; no report file is created."""
    observer = _session.active if _session.active is not None else _session.last
    return [dict(sample) for sample in observer.samples] if observer is not None else []
