"""Native FX images in a coordinator-owned full RHI Editor on L_Movement_Test.

Set PYRIOS_FX_PREFIX to a fresh absolute filename prefix under project Saved;
PYRIOS_FX_CASE=normal01_production (default) observes the original strict
ProductionNativeNormal01 leaf. Start this script before that leaf. It never
starts/ends PIE, sends input, pauses, changes playback, or advances simulation.
Three images follow the original Task instance and authored FX window. Missed
natural frames are reported rather than manufactured. PYRIOS_FX_EXIT is ignored
in this mode: the original test and coordinator retain their Editor lifecycle.

Explicit front/back/both select the historical standalone smoke diagnostic,
whose 60 Hz/manual 400 cm/s fixture is not production action evidence. Only that
historical mode consumes PYRIOS_FX_EXIT=1. No mode saves assets or maps. Images
require visual review; production SceneCapture views are not original-game or
original-viewport pixel comparisons.
"""
import json
import os
from pathlib import Path
import time

import unreal


SYSTEMS = {
    "front": "/Game/Characters/Player/Pyrios/FX/Skill/NS_UEEquivalent_Eff_Pyrois_Evade_Front_01_Smoke_6b2909fcd7b0",
    "back": "/Game/Characters/Player/Pyrios/FX/Skill/NS_UEEquivalent_Eff_Pyrois_Evade_Back_01_Smoke_c04093b9a602",
}
NORMAL01_MONTAGE = "/Game/Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_Normal_01.AM_Pyrios_Attack_Normal_01"
NORMAL01_SYSTEM = "/Game/Characters/Player/Pyrios/FX/Skill/NS_Eff_Pyrois_Attack_Normal_01_01_Trail.NS_Eff_Pyrois_Attack_Normal_01_01_Trail"
DT = 1.0 / 60.0
CAPTURE_STEPS = (15, 30, 60)
ORIGIN = unreal.Vector(9000.0, 2200.0, 120.0)
SPEED_CM_S = 400.0


def emit(stage, **values):
    unreal.log("PYRIOS_FX_CAPTURE " + json.dumps(dict(stage=stage, **values), ensure_ascii=False))


def dirty_packages():
    lib = unreal.EditorLoadingAndSavingUtils
    return sorted(p.get_path_name() for p in
                  list(lib.get_dirty_content_packages()) + list(lib.get_dirty_map_packages()))


def camera_state(subsystem):
    p, r = subsystem.get_level_viewport_camera_info()
    return (p.x, p.y, p.z, r.pitch, r.yaw, r.roll)


class SmokeCapture:
    def __init__(self):
        self.callback = None
        self.component = None
        self.capture_actor = None
        self.target = None
        self.started = time.monotonic()
        self.finished = False
        self.images = []
        self.case_index = 0
        self.step = 0
        self.capture_index = 0
        self.render_wait = 0
        self.observation = None
        self.waiting_for_activation = False
        self.activation_started = None
        self.original_camera = None
        self.original_selection = None
        self.original_actors = None

    def start(self):
        self.actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        self.world = self.editor.get_editor_world()
        if not self.world or self.world.get_path_name() != "/Game/Map/L_Movement_Test.L_Movement_Test":
            raise RuntimeError("Requires the original L_Movement_Test Editor world")
        if self.editor.get_game_world() is not None:
            raise RuntimeError("Requires a non-PIE auxiliary Editor")
        if dirty_packages():
            raise RuntimeError("Requires clean original packages: " + repr(dirty_packages()))
        self.original_camera = camera_state(self.editor)
        self.original_selection = sorted(a.get_path_name() for a in self.actors.get_selected_level_actors())
        self.original_actors = {a.get_path_name() for a in self.actors.get_all_level_actors()}
        requested_prefix = Path(os.environ["PYRIOS_FX_PREFIX"])
        if not requested_prefix.is_absolute():
            raise RuntimeError("Capture prefix must be absolute")
        self.prefix = requested_prefix.resolve()
        saved = Path(unreal.Paths.project_saved_dir()).resolve()
        if not self.prefix.is_relative_to(saved):
            raise RuntimeError("Capture prefix must be under project Saved")
        case = os.environ.get("PYRIOS_FX_CASE", "both")
        self.cases = list(SYSTEMS) if case == "both" else [case]
        if any(k not in SYSTEMS for k in self.cases):
            raise RuntimeError("PYRIOS_FX_CASE must be front, back or both")
        if any(self.prefix.parent.glob(self.prefix.name + "*.png")):
            raise RuntimeError("Refusing to overwrite existing captures")
        self.prefix.parent.mkdir(parents=True, exist_ok=True)
        self.target = unreal.RenderingLibrary.create_render_target2d(
            self.world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        if self.target is None:
            raise RuntimeError("Native render target creation failed")
        location = ORIGIN + unreal.Vector(-600.0, -800.0, 350.0)
        look_at = ORIGIN + unreal.Vector(180.0, 0.0, 40.0)
        self.capture_actor = self.actors.spawn_actor_from_class(
            unreal.SceneCapture2D, location,
            unreal.MathLibrary.find_look_at_rotation(location, look_at), transient=True)
        if self.capture_actor is None:
            raise RuntimeError("Native transient SceneCapture2D creation failed")
        self.capture = self.capture_actor.get_editor_property("capture_component2d")
        for name, value in (("texture_target", self.target), ("capture_every_frame", False),
                            ("capture_on_movement", False), ("fov_angle", 50.0),
                            ("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)):
            self.capture.set_editor_property(name, value)
        emit("started", cases=self.cases, systems=SYSTEMS, fixture_origin=[ORIGIN.x, ORIGIN.y, ORIGIN.z],
             fixture_speed_cm_s=SPEED_CM_S, native_step_seconds=DT,
             captures_seconds=[s * DT for s in CAPTURE_STEPS],
             scene="original UE L_Movement_Test lighting/fog; UE-equivalent materials",
             action_integration=False, reference_visual_comparison=False)
        self.start_case()
        self.callback = unreal.register_slate_post_tick_callback(self.tick)
        if self.callback is None:
            raise RuntimeError("Native post-tick observation registration failed")

    def start_case(self):
        self.case = self.cases[self.case_index]
        system = unreal.EditorAssetLibrary.load_asset(SYSTEMS[self.case])
        if not isinstance(system, unreal.NiagaraSystem):
            raise RuntimeError("Missing exact saved Niagara System: " + SYSTEMS[self.case])
        self.component = unreal.NiagaraFunctionLibrary.spawn_system_at_location(
            self.world, system, ORIGIN, unreal.Rotator(0.0, 0.0, 0.0), unreal.Vector(1.0, 1.0, 1.0),
            auto_destroy=False, auto_activate=False, pooling_method=unreal.NCPoolMethod.NONE,
            pre_cull_check=False)
        if self.component is None:
            raise RuntimeError("Native transient Niagara component creation failed")
        self.component.set_force_solo(True)
        self.component.activate(True)
        self.component.set_component_tick_enabled(False)
        self.step = self.capture_index = self.render_wait = 0
        self.waiting_for_activation = True
        self.activation_started = time.monotonic()
        emit("case_started", case=self.case, component=self.component.get_path_name(),
             forced_solo=True, automatic_component_tick=False, preview_pre_spawn_cull=False,
             activation="native readiness pending; no simulation steps claimed")

    def observe(self):
        result = {"active": self.component.is_active(), "visible": self.component.is_visible()}
        try:
            lib = unreal.NiagaraSimCacheFunctionLibrary
            cache = lib.create_niagara_sim_cache(self.component)
            # This native function writes the supplied cache. Python suppresses
            # its bool success return when it has an out Object; inspect the
            # original cache's real data instead of assuming a tuple binding.
            lib.capture_niagara_sim_cache_immediate(
                cache, unreal.NiagaraSimCacheCreateParameters(), self.component, advance_simulation=False)
            if cache is None or not cache.is_cache_valid() or cache.get_num_frames() < 1:
                raise RuntimeError("Native immediate cache has no valid frames")
            result["runtime_layers"] = [
                {"name": str(name), "age_attribute_particle_count": len(cache.read_float_attribute("Age", name, 0))}
                for name in cache.get_emitter_names()]
            result["particle_read_status"] = "native SimCache Age attribute lengths"
        except Exception as error:
            # Observation may be unavailable in the SDK; the image remains real.
            result["particle_read_status"] = "unavailable"
            result["particle_read_error"] = str(error)
        return result

    def tick(self, _editor_delta):
        if self.finished:
            return
        try:
            if time.monotonic() - self.started > 90.0:
                raise RuntimeError("Bounded native preview exceeded 90 seconds")
            if self.waiting_for_activation:
                # ActivateInternal polls compilation/world/PSO readiness and
                # normally requests native component ticks to finish startup.
                # This manual diagnostic keeps ticks disabled and invokes that
                # same native startup entry until actually active, with a bound.
                if time.monotonic() - self.activation_started > 15.0:
                    raise RuntimeError("Native Niagara activation did not become active within 15 seconds")
                if not self.component.is_active():
                    self.component.activate(True)
                    self.component.set_component_tick_enabled(False)
                if self.component.is_active():
                    self.waiting_for_activation = False
                    emit("native_active", case=self.case, active=True, simulation_steps=0)
                return
            if self.render_wait:
                self.render_wait -= 1
                if self.render_wait == 2:
                    self.capture.capture_scene()
                if self.render_wait == 0:
                    name = self.prefix.name + "_" + self.case + "_" + str(self.step) + ".png"
                    unreal.RenderingLibrary.export_render_target(self.world, self.target, str(self.prefix.parent), name)
                    path = self.prefix.parent / name
                    if not path.is_file() or path.stat().st_size < 32:
                        raise RuntimeError("Native PNG export missing: " + str(path))
                    self.images.append(str(path))
                    emit("captured", case=self.case, native_steps=self.step, preview_seconds=self.step * DT,
                         image=str(path), visual_review="pending", **self.observation)
                    self.capture_index += 1
                    if self.capture_index == len(CAPTURE_STEPS):
                        self.destroy_component()
                        self.case_index += 1
                        if self.case_index == len(self.cases):
                            self.finish(None)
                        else:
                            self.start_case()
                return
            self.step += 1
            self.component.set_world_location(ORIGIN + unreal.Vector(SPEED_CM_S * self.step * DT, 0.0, 0.0),
                                              False, False)
            self.component.advance_simulation(1, DT)
            if self.step == CAPTURE_STEPS[self.capture_index]:
                self.observation = self.observe()
                self.render_wait = 3
        except Exception as error:
            self.finish(error)

    def destroy_component(self):
        component = self.component
        if component is not None:
            component.deactivate()
            # K2_DestroyComponent's Object is a caller-qualification input.
            # Native code explicitly permits Object == this exact component.
            component.destroy_component(component)
            self.component = None

    def finish(self, error):
        self.finished = True
        cleanup_errors = []
        if self.callback is not None:
            unreal.unregister_slate_post_tick_callback(self.callback)
            self.callback = None
        for operation in (self.destroy_component,
                          lambda: self.actors.destroy_actor(self.capture_actor) if self.capture_actor else None,
                          lambda: unreal.RenderingLibrary.release_render_target2d(self.target) if self.target else None):
            try:
                operation()
            except Exception as cleanup_error:
                cleanup_errors.append(str(cleanup_error))
        self.capture_actor = self.target = None
        if self.original_camera is not None:
            camera = camera_state(self.editor)
            selected = sorted(a.get_path_name() for a in self.actors.get_selected_level_actors())
            actors = {a.get_path_name() for a in self.actors.get_all_level_actors()}
            if camera != self.original_camera or selected != self.original_selection or actors != self.original_actors:
                cleanup_errors.append("Original camera, selection, or Actor set changed")
        dirty = dirty_packages()
        if dirty:
            cleanup_errors.append("Dirty packages remain: " + repr(dirty))
        emit("failed" if error or cleanup_errors else "capture_completed", error=str(error) if error else None,
             cleanup_errors=cleanup_errors, dirty_packages=dirty, images=self.images,
             saved_assets=False, visual_review="pending", action_integration=False)
        if os.environ.get("PYRIOS_FX_EXIT") == "1":
            unreal.SystemLibrary.quit_editor()


class ProductionCapture:
    """A finite observer of the first original playback; it owns only capture resources."""

    def __init__(self):
        self.callback = self.capture = self.target = None
        self.world = self.pawn = self.mesh = self.task = None
        self.started = time.monotonic()
        self.finished = False
        self.observation_done = False
        self.observation_error = None
        self.cleanup_errors = []
        self.images, self.missed = [], []
        self.index = 0
        self.bound_position = self.last_observed_position = None
        self.last_captured_frame = None
        self.original_camera = self.original_selection = self.original_actors = None

    def start(self):
        self.editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        self.actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        editor_world = self.editor.get_editor_world()
        if not editor_world or editor_world.get_path_name() != "/Game/Map/L_Movement_Test.L_Movement_Test":
            raise RuntimeError("Requires the original L_Movement_Test Editor world")
        if self.editor.get_game_world() is not None or dirty_packages():
            raise RuntimeError("Install before the original test in a clean non-PIE Editor")
        self.original_camera = camera_state(self.editor)
        self.original_selection = sorted(a.get_path_name() for a in self.actors.get_selected_level_actors())
        self.original_actors = {a.get_path_name() for a in self.actors.get_all_level_actors()}
        requested = Path(os.environ["PYRIOS_FX_PREFIX"])
        if not requested.is_absolute():
            raise RuntimeError("Capture prefix must be absolute")
        self.prefix = requested.resolve()
        if not self.prefix.is_relative_to(Path(unreal.Paths.project_saved_dir()).resolve()):
            raise RuntimeError("Capture prefix must be under project Saved")
        if any(self.prefix.parent.glob(self.prefix.name + "*.png")):
            raise RuntimeError("Refusing to overwrite existing captures")
        self.prefix.parent.mkdir(parents=True, exist_ok=True)
        self.callback = unreal.register_slate_post_tick_callback(self.tick)
        if self.callback is None:
            raise RuntimeError("Native post-tick observation registration failed")
        emit("production_observer_started", montage=NORMAL01_MONTAGE, system=NORMAL01_SYSTEM,
             input_owner="original strict production leaf", saved_assets=False,
             manual_tick=False, simulation_advance=False, visual_review="pending")

    def prepare_capture(self, world):
        """先准备首个原 Pawn 的采样资源；这里不猜测播放 Task 或 Mesh。"""
        pawn = unreal.GameplayStatics.get_player_pawn(world, 0)
        if self.pawn is not None and (not unreal.SystemLibrary.is_valid(self.pawn) or pawn != self.pawn):
            raise RuntimeError("First production Pawn changed; no replacement is queried")
        if pawn is None:
            return False
        self.pawn = pawn
        if self.capture is not None:
            if not unreal.SystemLibrary.is_valid(self.capture):
                raise RuntimeError("Original capture component retired; no replacement is created")
            return True
        self.target = unreal.RenderingLibrary.create_render_target2d(
            world, 1280, 720, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        if self.target is None:
            raise RuntimeError("Native transient render target creation failed")
        # 原 Pawn 只拥有新采样组件；原 Task/Mesh 身份仍须由下面的原生快照证实。
        self.capture = pawn.call_method("AddComponentByClass", args=(
            unreal.SceneCaptureComponent2D.static_class(), True, unreal.Transform(), True))
        if self.capture is None:
            raise RuntimeError("Native PIE capture component creation failed")
        for name, value in (("texture_target", self.target), ("capture_every_frame", False),
                            ("capture_on_movement", False), ("fov_angle", 50.0),
                            ("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)):
            self.capture.set_editor_property(name, value)
        pawn.call_method("FinishAddComponent", args=(self.capture, True, unreal.Transform()))
        emit("production_capture_resources_ready", world=world.get_path_name(), pawn=pawn.get_path_name(),
             native_frame=unreal.SystemLibrary.get_frame_count(), original_playback_bound=False,
             manual_tick=False, simulation_advance=False)
        return True

    def bind_original(self, world):
        if not self.prepare_capture(world):
            return
        pawn = self.pawn
        candidates = []
        for task in unreal.ObjectIterator(unreal.GGYGOAbilityTask_PlayMontageAndWaitForEvent):
            section = task.try_get_original_section_snapshot()
            if section is None or section.montage.get_path_name() != NORMAL01_MONTAGE:
                continue
            # Native Python bool+out packing is None on false, (fact, position) on true.
            notify = task.try_get_original_montage_notify_snapshot()
            if notify is None:
                continue
            fact, _position = notify
            if fact.mesh is None or fact.mesh.get_owner() != pawn:
                continue
            if (fact.montage != section.montage or fact.montage_instance_id != section.montage_instance_id
                    or fact.mesh not in pawn.get_components_by_class(unreal.SkeletalMeshComponent)):
                raise RuntimeError("Original Task snapshots disagree on playback/Mesh identity")
            candidates.append((task, section, fact.mesh))
        if len(candidates) > 1:
            raise RuntimeError("Multiple original Normal01 tasks match the first production Pawn")
        if not candidates:
            return
        self.task, section, self.mesh = candidates[0]
        self.world, self.pawn = world, pawn
        self.instance = section.montage_instance_id
        self.bound_position = section.position_seconds
        windows = []
        for event in unreal.AnimationLibrary.get_animation_notify_events(section.montage):
            state = event.get_editor_property("notify_state_class")
            if state is None or not isinstance(state, unreal.GGYGOAnimNotifyState_GameplayEventWindow):
                continue
            if state.get_editor_property("begin_event_tag").export_text() != '(TagName="Event.Montage.FXWindowBegin")':
                continue
            if state.get_editor_property("end_event_tag").export_text() != '(TagName="Event.Montage.FXWindowEnd")':
                raise RuntimeError("Original FX window end tag differs")
            begin = float(unreal.AnimationLibrary.get_anim_notify_event_trigger_time(event))
            end = begin + float(unreal.AnimationLibrary.get_anim_notify_event_duration(event))
            if state.get_outer() != section.montage or not 0 <= begin < end:
                raise RuntimeError("Original FX window ownership/range is invalid")
            windows.append((begin, end))
        if len(windows) != 1:
            raise RuntimeError("Requires one exact authored Normal01 FX window")
        begin, end = windows[0]
        # Observation bands only; these never drive the Montage or Niagara clock.
        self.bands = [("active_early", begin + (end - begin) * .25, end, "full"),
                      ("active_late", begin + (end - begin) * .70, end, "full"),
                      ("after_window", end + .10, end + .40, "upper_back")]
        emit("production_original_bound", world=world.get_path_name(), pawn=pawn.get_path_name(),
             mesh=self.mesh.get_path_name(), task=self.task.get_path_name(), instance=self.instance,
             actual_position=section.position_seconds, native_frame=unreal.SystemLibrary.get_frame_count(),
             authored_window=[begin, end], bands=self.bands)

    def original_snapshot(self):
        if self.editor.get_game_world() != self.world or not unreal.SystemLibrary.is_valid(self.pawn):
            raise RuntimeError("Original production world/Pawn retired; no replacement is queried")
        section = self.task.try_get_original_section_snapshot()
        notify = self.task.try_get_original_montage_notify_snapshot()
        if section is None or notify is None:
            raise RuntimeError("Original production Task no longer supplies its native snapshots")
        fact, _position = notify
        if (section.montage.get_path_name() != NORMAL01_MONTAGE or section.montage_instance_id != self.instance
                or fact.montage != section.montage or fact.montage_instance_id != self.instance
                or fact.mesh != self.mesh or self.mesh.get_owner() != self.pawn):
            raise RuntimeError("Original production playback identity changed")
        return section

    @staticmethod
    def particle_pose(component):
        """Read one native frame; the cache's real System age owns the timestamp."""
        try:
            lib = unreal.NiagaraSimCacheFunctionLibrary
            cache = lib.create_niagara_sim_cache(component)
            lib.capture_niagara_sim_cache_immediate(
                cache, unreal.NiagaraSimCacheCreateParameters(), component, advance_simulation=False)
            if cache is None or not cache.is_cache_valid() or cache.get_num_frames() != 1:
                raise RuntimeError("Native immediate cache has no single valid frame")
            layers = []
            for emitter in cache.get_emitter_names():
                ages = cache.read_float_attribute("Age", emitter, 0)
                positions = cache.read_position_attribute("Position", emitter, False, 0)
                orientations = cache.read_quat_attribute("MeshOrientation", emitter, False, 0)
                if len(ages) != len(positions) or len(ages) != len(orientations):
                    raise RuntimeError("Native particle Pose attribute counts disagree: " + str(emitter))
                layers.append(dict(name=str(emitter), count=len(ages),
                    first_age=ages[0] if ages else None,
                    first_position=[positions[0].x, positions[0].y, positions[0].z] if positions else None,
                    first_orientation=[orientations[0].x, orientations[0].y,
                                       orientations[0].z, orientations[0].w] if orientations else None))
            return dict(status="native_single_frame", system_age_seconds=cache.get_start_seconds(),
                        frame_count=1, local_space_to_world=False, advance_simulation=False, layers=layers)
        except Exception as error:
            # Missing SDK/data is not a zero-particle or fixed-pose observation.
            return dict(status="unavailable", error=str(error), advance_simulation=False)

    def capture_image(self, name, view, section):
        origin = self.pawn.get_actor_location()
        forward, right = self.pawn.get_actor_forward_vector(), self.pawn.get_actor_right_vector()
        if view == "full":
            location = origin - forward * 420.0 - right * 330.0 + unreal.Vector(0, 0, 225.0)
            target = origin + unreal.Vector(0, 0, 105.0)
        else:
            location = origin - forward * 230.0 - right * 70.0 + unreal.Vector(0, 0, 155.0)
            target = origin + unreal.Vector(0, 0, 105.0)
        rotation = unreal.MathLibrary.find_look_at_rotation(location, target)
        self.capture.set_world_location_and_rotation(location, rotation, False, False)
        components = []
        for component in self.pawn.get_components_by_class(unreal.NiagaraComponent):
            asset = component.get_asset()
            if asset is not None and asset.get_path_name() == NORMAL01_SYSTEM:
                parent = component.get_attach_parent()
                components.append(dict(path=component.get_path_name(), active=component.is_active(),
                                       parent=parent.get_path_name() if parent else None,
                                       particle_pose=self.particle_pose(component) if view == "full" else None))
        frame = unreal.SystemLibrary.get_frame_count()
        self.capture.capture_scene()
        filename = self.prefix.name + "_normal01_" + name + ".png"
        unreal.RenderingLibrary.export_render_target(self.world, self.target, str(self.prefix.parent), filename)
        path = self.prefix.parent / filename
        if not path.is_file() or path.stat().st_size < 32:
            raise RuntimeError("Native production PNG export missing: " + str(path))
        self.images.append(str(path))
        after = self.original_snapshot()
        if after.position_seconds != section.position_seconds or unreal.SystemLibrary.get_frame_count() != frame:
            raise RuntimeError("Native capture returned across a different production frame")
        emit("production_captured", image=str(path), view=view, native_frame=frame,
             task=self.task.get_path_name(), instance=self.instance, section=str(section.section_name),
             montage_position_seconds=section.position_seconds, instance_play_rate=section.instance_play_rate,
             camera_location=[location.x, location.y, location.z],
             camera_rotation=[rotation.pitch, rotation.yaw, rotation.roll],
             original_system_components=components, capture="native PIE SceneCapture2D",
             simulation_advance=False, visual_review="pending", reference_visual_comparison=False)
        self.last_captured_frame = frame

    def tick(self, _editor_delta):
        if self.finished:
            return
        try:
            if self.observation_done:
                if self.editor.get_game_world() is None:
                    self.finalize(True)
                elif time.monotonic() - self.started > 80.0:
                    self.finalize(False)
                return
            if time.monotonic() - self.started > 80.0:
                raise RuntimeError("Bounded production observation exceeded 80 seconds")
            if self.task is None:
                world = self.editor.get_game_world()
                if self.world is None and world is not None:
                    self.world = world
                    emit("production_world_observed", world=world.get_path_name())
                if self.world is not None:
                    if world != self.world:
                        raise RuntimeError("First production world retired before Task binding")
                    self.bind_original(self.world)
                if self.task is None:
                    return
            section = self.original_snapshot()
            previous_position = self.last_observed_position
            self.last_observed_position = section.position_seconds
            # Slate 可以在同一个引擎帧多次更新；不把同一自然帧冒充第二张时序证据。
            if self.last_captured_frame == unreal.SystemLibrary.get_frame_count():
                return
            while self.index < len(self.bands):
                name, begin, end, view = self.bands[self.index]
                if section.position_seconds < begin:
                    return
                self.index += 1
                if section.position_seconds >= end:
                    self.missed.append(name)
                    emit("production_band_missed", name=name, instance=self.instance,
                         actual_position=section.position_seconds, observation_band=[begin, end],
                         bound_position=self.bound_position, previous_observed_position=previous_position,
                         reason="No observed natural frame in this band; no playback change")
                    continue
                self.capture_image(name, view, section)
                break
            if self.index == len(self.bands):
                self.finish(None)
        except Exception as error:
            self.finish(error)

    def finish(self, error):
        if self.finished or self.observation_done:
            return
        self.observation_done = True
        self.observation_error = str(error) if error else None
        # Only our original component/target retire. The test owns its PIE,
        # Montage, Niagara components, input and Editor completion.
        for operation in (lambda: self.capture.destroy_component(self.capture)
                          if unreal.SystemLibrary.is_valid(self.capture) else None,
                          lambda: unreal.RenderingLibrary.release_render_target2d(self.target) if self.target else None):
            try:
                operation()
            except Exception as cleanup_error:
                self.cleanup_errors.append(str(cleanup_error))
        self.capture = self.target = None
        self.task = self.mesh = self.pawn = self.world = None
        if self.editor.get_game_world() is None:
            self.finalize(True)
        elif time.monotonic() - self.started > 80.0:
            self.finalize(False)
        else:
            # EditorActorSubsystem rejects PIE queries. Keep this same finite
            # observer until the original test retires PIE; never stop PIE here.
            emit("production_protection_waiting", images=self.images, missed=self.missed,
                 error=self.observation_error, capture_resources_released=True,
                 reason="Original test still owns PIE; Editor checks await its retirement")

    def finalize(self, protection_available):
        self.finished = True
        if self.callback is not None:
            unreal.unregister_slate_post_tick_callback(self.callback)
            self.callback = None
        dirty = None
        protection = "unavailable"
        if not protection_available:
            self.cleanup_errors.append("Original PIE did not retire within the observation bound; Editor protection unverified")
        else:
            try:
                if self.original_camera is not None:
                    if (camera_state(self.editor) != self.original_camera
                            or sorted(a.get_path_name() for a in self.actors.get_selected_level_actors()) != self.original_selection
                            or {a.get_path_name() for a in self.actors.get_all_level_actors()} != self.original_actors):
                        self.cleanup_errors.append("Original Editor camera/selection/Actor set changed")
                dirty = dirty_packages()
                if dirty:
                    self.cleanup_errors.append("Dirty packages remain: " + repr(dirty))
                protection = "failed" if self.cleanup_errors else "verified_after_original_PIE"
            except Exception as protection_error:
                self.cleanup_errors.append("Editor protection query failed: " + str(protection_error))
        emit("production_capture_failed" if self.observation_error or self.cleanup_errors else
             "production_capture_incomplete" if self.missed else "production_capture_completed",
             error=self.observation_error, cleanup_errors=self.cleanup_errors, missed=self.missed,
             images=self.images, dirty_packages=dirty, editor_protection=protection,
             saved_assets=False, visual_review="pending")


if globals().get("_pyrios_fx_capture") is not None:
    raise RuntimeError("Refusing a second FX observer in this Editor")
_pyrios_fx_capture = (ProductionCapture() if os.environ.get("PYRIOS_FX_CASE", "normal01_production")
                      == "normal01_production" else SmokeCapture())
try:
    _pyrios_fx_capture.start()
except Exception as _start_error:
    _pyrios_fx_capture.finish(_start_error)
