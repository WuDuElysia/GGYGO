"""In PIE on L_Movement_Test, inject IA_Move and record actual runtime state.
38 seconds: settle, forward 31 seconds, reverse 3 seconds, release.
Does not edit movement, animation, input assets, or actor transforms.
"""
import json
from pathlib import Path
import unreal

class MovementLevelProbe:
    def __init__(self):
        self.world = unreal.EditorLevelLibrary.get_pie_worlds(False)[0]
        assert 'L_Movement_Test' in self.world.get_path_name()
        self.pawn = unreal.GameplayStatics.get_player_pawn(self.world, 0)
        self.move = self.pawn.get_movement_component()
        self.anim = self.pawn.mesh.get_anim_instance()
        subs = [s for s in unreal.ObjectIterator(unreal.EnhancedInputLocalPlayerSubsystem) if s.get_path_name().startswith('/Engine/Transient.')]
        assert len(subs) == 1, 'Expected one PIE local player'
        self.inputs = subs[0]
        self.action = unreal.load_asset('/Game/Input/Actions/IA_Move')
        assert self.action
        self.elapsed = 0.0
        self.samples = []
        self.performance = unreal.find_object(None, '/Script/UnrealEd.Default__EditorPerformanceSettings')
        self.throttle = self.performance.get_editor_property('bThrottleCPUWhenNotForeground')
        self.performance.set_editor_property('bThrottleCPUWhenNotForeground', False)
        self.handle = unreal.register_ticker_callback(self.tick)

    def tick(self, dt):
        try:
            self.elapsed += dt
            axis = 1.0 if 1 <= self.elapsed < 32 else (-1.0 if self.elapsed < 35 and self.elapsed >= 32 else 0.0)
            self.inputs.inject_input_vector_for_action(self.action, unreal.Vector(0,axis,0), [], [])
            state = self.anim.get_editor_property('animation_state')
            loc = self.pawn.get_actor_location()
            self.samples.append(dict(time=round(self.elapsed,4), axis=axis, location_cm=[loc.x,loc.y,loc.z], gait=str(self.move.get_resolved_gait()), speed_cm_s=state.horizontal_speed, grounded=state.grounded, movement_mode=str(self.move.movement_mode), has_move_input=state.has_move_input, turn_back_phase=str(state.turn_back_phase), yaw=self.pawn.get_actor_rotation().yaw, blend=self.anim.get_editor_property('state_memory').gait_blend_y))
            if self.elapsed >= 38:
                self.finish()
                return False
            return True
        except Exception as error:
            self.samples.append(dict(error=str(error)))
            self.finish()
            return False

    def finish(self):
        self.inputs.inject_input_vector_for_action(self.action, unreal.Vector(0,0,0), [], [])
        self.performance.set_editor_property('bThrottleCPUWhenNotForeground', self.throttle)
        output = Path(unreal.Paths.convert_relative_path_to_full(unreal.Paths.project_saved_dir())) / 'LevelDesign'
        output.mkdir(parents=True,exist_ok=True)
        (output/'movement_runtime.json').write_text(json.dumps(self.samples,indent=2),encoding='utf-8')
        unreal.log('MovementLevelProbe finished: '+str(len(self.samples))+' samples')

movement_level_probe = MovementLevelProbe()
