"""Pyrios captures; the default toon commandlet invocation is preserved.

Toon: UnrealEditor-Cmd -run=pythonscript -script=<this file>
      -AllowCommandletRendering -dpcvars=Editor.AsyncTextureCompilation=0.
Body: a full RHI Editor on /Game/Map/L_Movement_Test, with
      PYRIOS_CAP_MODE=body, PYRIOS_BODY_PREFIX=<new Saved path without suffix>,
      PYRIOS_BODY_LOG=<the same fresh -AbsLog path>, PYRIOS_BODY_EXIT=1,
      -ForceLogFlush -ExecCmds="py <this file>".
Body soft: PYRIOS_CAP_MODE=body_soft preserves the original player camera,
      LitOriginalA -> LitSoftOff -> LitOriginalB, then Section2Wireframe.
      Only slot 2's transient MID changes L1/L2/L3_SoftCfg.x to zero.

Body owns one PIE and one bounded editor post-tick observer. It never drives
input, edits/saves assets, or uses SceneCapture2D. It pauses the actual player,
uses the native active PIE viewport high-resolution API and verified player
viewmode commands, then restores. The screenshot task uses a global completion
delegate; neither its completion nor a PNG proves which world was rendered.
PNG presence only means capture completed; both images still require visual
review of the original cloth region. Output and diagnostics stay in Saved/log.
"""
import json
import hashlib
import math
import os
from pathlib import Path
import re
import struct
import time
import unreal


def project_render_snapshot(character):
    """新主体接口的只读见证。由实际视口截图调用者配套保存，读回不能代替画面验收。

    历史 PyriosContributionCapture 仍只认其冻结源，不能放宽 hash 来消费新图。
    不启动 PIE、不暂停动作、不覆盖材质或修改相机；披风 shaderTime 未锁定。
    """
    from pyrios_material_plan import PREVIEW_DATA_NAMES, DISPLAY_PARAMETERS, load_plan
    from verify_pyrios_renderer import verify_project_surface_graph
    if not isinstance(character, unreal.Character):
        raise RuntimeError("Project render witness requires an actual Character")
    mesh = character.get_editor_property("mesh")
    components = character.get_components_by_class(unreal.GGYGOCharacterRenderComponent)
    if len(components) != 1:
        raise RuntimeError("Project render witness requires exactly one rendering component")
    component = components[0]
    root = Path(__file__).resolve().parents[1] / "Assets/Pyrios/Rendering"
    plan = load_plan(root / "UnityMaterials", root / "Pyrios_Toon_Globals.json")
    # GetParameterValue 只返回 MI 值，不表示 CPD 分支的实际输入；两者分别记录。
    # UE Python 省略 bool 返回值：成功返回两个 out 参数，失败返回 None。
    read_result = unreal.GGYGOPrimitiveDataReadLibrary.read_runtime_custom_primitive_data(mesh)
    if read_result is None:
        raise RuntimeError("Project render witness: runtime Custom Primitive Data read failed for " + mesh.get_path_name())
    cpd, _ = read_result
    cpd = list(cpd)
    materials = {}
    for binding in component.get_editor_property("material_slots"):
        slot = str(binding.get_editor_property("slot_name"))
        index = mesh.get_material_index(slot)
        if index < 0:
            raise RuntimeError("Missing configured render slot: " + slot)
        material = mesh.get_material(index)
        if not isinstance(material, (unreal.MaterialInstanceConstant, unreal.MaterialInstanceDynamic)):
            raise RuntimeError("Expected actual MI/MID at " + slot)
        parent = material.get_base_material()
        verify_project_surface_graph(parent, plan)
        mel = unreal.MaterialEditingLibrary
        if isinstance(material, unreal.MaterialInstanceDynamic):
            scalar_getter = material.get_scalar_parameter_value
            vector_getter = material.get_vector_parameter_value
        else:
            scalar_getter = lambda name: mel.get_material_instance_scalar_parameter_value(material, name)
            vector_getter = lambda name: mel.get_material_instance_vector_parameter_value(material, name)
        materials[slot] = dict(object=material.get_path_name(), parent=parent.get_path_name(),
            scalar={name: scalar_getter(name)
                    for name in ("SceneLightStrength", "KeyLightVisibility", *DISPLAY_PARAMETERS)},
            vector={name: _BodyCapture._rgba(vector_getter(name))
                    for name in ("KeyLightDirectionWS", "KeyLightColor")})
    world = character.get_world()
    result = dict(character=character.get_path_name(), world=world.get_path_name(),
        pie=world in unreal.EditorLevelLibrary.get_pie_worlds(True),
        preview_requested=component.get_editor_property("bPreviewSceneLighting"),
        actual_preview_active=bool(cpd and cpd[0] > 0.5),
        preview_cpd={name: cpd[i] if i < len(cpd) else None for i, name in enumerate(PREVIEW_DATA_NAMES)},
        component={name: component.get_editor_property(name) for name in
            ("reference_key_light_intensity", "key_light_intensity_response", "key_light_output_scale",
             "max_key_light_strength", "occluded_key_light_visibility")},
        transform=character.get_actor_transform().export_text(),
        pose=[mesh.get_socket_transform(mesh.get_bone_name(i), unreal.RelativeTransformSpace.RTS_WORLD).export_text()
              for i in range(mesh.get_num_bones())], materials=materials,
        fx_shader_time_locked=False, support=dict(direct="Directional", shadow="CharacterTrace",
            point=False, spot=False, skylight_gi=False, vsm=False))
    unreal.log("PYRIOS_PROJECT_RENDER_WITNESS " + json.dumps(result, ensure_ascii=False))
    return result


def _capture_toon():
    EAL = unreal.EditorAssetLibrary
    for p in EAL.list_assets("/Game/Characters/Player/Pyrios/Materials/Texture", recursive=False):
        t = EAL.load_asset(p)
        if isinstance(t, unreal.Texture2D):
            t.set_force_mip_levels_to_be_resident(60.0)
    world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
    sub = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
    mesh = EAL.load_asset("/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model")
    actor = sub.spawn_actor_from_class(unreal.SkeletalMeshActor, unreal.Vector(0, 0, 0), unreal.Rotator(0, 0, 0))
    actor.get_editor_property("skeletal_mesh_component").set_skeletal_mesh_asset(mesh)
    rt = unreal.RenderingLibrary.create_render_target2d(world, 768, 1024, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
    out = "F:/ue_project/GGYGO/AAADocs/References/Captures/PyriosToon"
    os.makedirs(out, exist_ok=True)
    tag = os.environ.get("PYRIOS_CAP_TAG", "cap")
    for name, yaw, z, dist, fov in (("front", 0, 95, 330, 40.0), ("chest", 0, 150, 160, 40.0), ("back", 180, 120, 260, 40.0)):
        center = unreal.Vector(0, 0, z)
        rad = math.radians(yaw)
        loc = unreal.Vector(dist * math.sin(rad), dist * math.cos(rad), z + 10)
        cap = sub.spawn_actor_from_class(unreal.SceneCapture2D, loc, unreal.MathLibrary.find_look_at_rotation(loc, center))
        cc = cap.get_editor_property("capture_component2d")
        cc.set_editor_property("texture_target", rt)
        cc.set_editor_property("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR)
        cc.set_editor_property("fov_angle", fov)
        pp = cc.get_editor_property("post_process_settings")
        for k, v in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL), ("auto_exposure_bias", 0.0),
                     ("auto_exposure_apply_physical_camera_exposure", False)):
            pp.set_editor_property("override_" + k, True)
            pp.set_editor_property(k, v)
        cc.set_editor_property("post_process_settings", pp)
        for _ in range(3):
            cc.capture_scene()
        unreal.RenderingLibrary.export_render_target(world, rt, out, "%s_toon_%s_%s.png" % (time.strftime("%Y%m%d"), tag, name))
        unreal.log("CAP_DONE " + name)


_MAP = "/Game/Map/L_Movement_Test.L_Movement_Test"
_MESH = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model.Avatar_Male_Size03_Pyrois_Model"
_OUTLINE = "/Game/Characters/Player/Pyrios/Materials/Generated/M_Pyrois_Outline.M_Pyrois_Outline"
_BODY_FX = "/Game/Characters/Player/Pyrios/Materials/Generated/MI_Pyrois_Body_FX.MI_Pyrois_Body_FX"


def _emit(stage, **values):
    unreal.log("PYRIOS_BODY_CAPTURE " + json.dumps(dict(stage=stage, **values), ensure_ascii=False))


def _dirty():
    packages = list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    packages += list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    return sorted(p.get_path_name() for p in packages)


def _xyz(v):
    return (v.x, v.y, v.z)


class _BodyCapture:
    """A finite diagnostic receipt; the native world/PC/mesh remain authoritative."""

    def __init__(self, soft_diagnostic=False):
        self.soft_diagnostic = soft_diagnostic
        saved = Path(unreal.Paths.project_saved_dir()).resolve()
        self.prefix = Path(os.environ["PYRIOS_BODY_PREFIX"]).resolve()
        self.log = Path(os.environ["PYRIOS_BODY_LOG"]).resolve()
        if saved not in self.prefix.parents or saved not in self.log.parents:
            raise RuntimeError("Body output prefix and -AbsLog must both be under project Saved")
        self.exit_after = os.environ.get("PYRIOS_BODY_EXIT", "0")
        if self.exit_after not in ("0", "1"):
            raise RuntimeError("PYRIOS_BODY_EXIT must be 0 or 1")
        names = (("LitOriginalA", "LitSoftOff", "LitOriginalB", "Section2Wireframe")
                 if soft_diagnostic else ("Lit", "Wireframe"))
        self.files = {name: Path(str(self.prefix) + "_" + name + ".png") for name in names}
        if any(p.exists() for p in self.files.values()):
            raise RuntimeError("Refusing to overwrite existing Body captures")
        if not self.log.is_file():
            raise RuntimeError("The current -AbsLog file must exist; use -ForceLogFlush")
        self.prefix.parent.mkdir(parents=True, exist_ok=True)
        self.ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        self.les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.smes = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
        if self.les.is_in_play_in_editor() or self.ues.get_game_world() is not None:
            raise RuntimeError("Refusing to attach to or stop somebody else's PIE")
        self.editor_world = self.ues.get_editor_world()
        if self.editor_world is None or self.editor_world.get_path_name() != _MAP:
            raise RuntimeError("Body diagnosis requires the original L_Movement_Test editor world")
        self.viewport_key = self.les.get_active_viewport_config_key()
        if self.viewport_key not in self.les.get_viewport_config_keys():
            raise RuntimeError("Cannot identify the original active Level Editor viewport")
        self.original_dirty = _dirty()
        if self.original_dirty:
            raise RuntimeError("Refusing Body capture with dirty packages: " + repr(self.original_dirty))
        camera = self.ues.get_level_viewport_camera_info()
        # UE Python strips a bool success return from functions with out parameters:
        # this native getter returns (location, rotation), or None on failure.
        if camera is None:
            raise RuntimeError("Cannot record the original editor viewport camera")
        self.editor_location, self.editor_rotation = camera
        self.editor_camera = (_xyz(self.editor_location), self._rotation(self.editor_rotation))
        self.selected_actors = list(self.actors.get_selected_level_actors())
        self.selected_assets = tuple(a.get_path_name() for a in unreal.EditorUtilityLibrary.get_selected_assets())
        self.source_mesh = unreal.EditorAssetLibrary.load_asset(_MESH)
        if not isinstance(self.source_mesh, unreal.SkeletalMesh):
            raise RuntimeError("Original Pyrios skeletal mesh asset is missing")
        self.source_slots = tuple(str(s.material_slot_name)
                                  for s in self.source_mesh.get_editor_property("materials"))
        # These editor getters reject PIE with INDEX_NONE. Read their render-data
        # mapping now, then qualify the runtime component against this same asset.
        self.source_sections = self._read_sections()
        self.handle = None
        self.capture_task = None
        self.advancing = False
        self.world = self.pc = self.pawn = self.mesh = self.camera = None
        self.original_mode = None
        self.mode_changed = False
        self.original_pause = None
        self.pause_changed = False
        self.hidden_outlines = []
        self.hidden_sections = []
        self.original_overrides = self.original_fx_material = None
        self.soft_mid = None
        self.soft_active = False
        self.expected_body_inputs = None
        self.pie_requested = False
        self.outcome = "not_started"
        self.steps = self._run()

    @staticmethod
    def _rotation(v):
        return (v.pitch, v.yaw, v.roll)

    def _read_sections(self):
        lod_count = self.smes.get_lod_count(self.source_mesh)
        if lod_count < 1 or not self.source_slots:
            raise RuntimeError("Original mesh has no valid LOD/material slots")
        result = []
        for lod in range(lod_count):
            count = self.smes.get_num_sections(self.source_mesh, lod)
            if count < 1:
                raise RuntimeError("Native Section count is invalid for original LOD " + str(lod))
            ids = tuple(self.smes.get_lod_material_slot(self.source_mesh, lod, section)
                        for section in range(count))
            if any(not 0 <= material_id < len(self.source_slots) for material_id in ids):
                raise RuntimeError("Native Section material mapping is invalid for original LOD " + str(lod))
            result.append(ids)
        _emit("static_sections", asset=self.source_mesh.get_path_name(),
              source="native editor render data before PIE", slots=self.source_slots, lods=result)
        return tuple(result)

    def _wait(self, predicate, label, timeout=30.0):
        deadline = time.monotonic() + timeout
        while True:
            value = predicate()
            if value:
                return value
            if time.monotonic() >= deadline:
                raise RuntimeError("Timed out waiting for " + label)
            yield

    def _own_world(self):
        worlds = list(unreal.EditorLevelLibrary.get_pie_worlds(True))
        if self.world is None or worlds != [self.world] or self.ues.get_game_world() != self.world:
            raise RuntimeError("Original sole PIE world changed; refusing to act on another world")

    def _live_player(self):
        self._own_world()
        if (unreal.GameplayStatics.get_player_controller(self.world, 0) != self.pc
                or self.pc.get_controlled_pawn() != self.pawn
                or self.mesh not in self.pawn.get_components_by_class(unreal.SkeletalMeshComponent)
                or self.mesh.get_editor_property("skeletal_mesh_asset") != self.source_mesh):
            raise RuntimeError("Original player/controller/mesh identity changed")
        if self.les.get_active_viewport_config_key() != self.viewport_key:
            raise RuntimeError("Original active PIE viewport changed")

    def _cmd(self, command):
        self._live_player()
        unreal.SystemLibrary.execute_console_command(self.world, command, self.pc)

    def _query_mode(self):
        cursor = self.log.stat().st_size
        self._cmd("viewmode")

        def response():
            with self.log.open("rb") as f:
                f.seek(cursor)
                text = f.read().decode("utf-8", errors="replace")
            match = re.search(r"Current view mode:\s*([A-Za-z0-9_]+)", text)
            return match.group(1) if match else None

        return (yield from self._wait(response, "native player viewmode response"))

    def _set_mode(self, mode):
        self.mode_changed = True
        self._cmd("viewmode " + mode)
        actual = yield from self._query_mode()
        if actual.lower() != mode.lower():
            raise RuntimeError("Native player viewmode did not apply: " + repr(actual))
        _emit("viewmode_verified", mode=actual, controller=self.pc.get_path_name())

    def _pose(self):
        self._live_player()
        if not unreal.GameplayStatics.is_game_paused(self.world):
            raise RuntimeError("Original diagnostic world is no longer paused")
        if self.mesh.get_num_bones() < 1:
            raise RuntimeError("Original player mesh has no bone pose")
        bones = []
        for index in range(self.mesh.get_num_bones()):
            transform = self.mesh.get_socket_transform(
                self.mesh.get_bone_name(index), unreal.RelativeTransformSpace.RTS_WORLD)
            q = transform.get_editor_property("rotation")
            bones.append((_xyz(transform.get_editor_property("translation")),
                          (q.x, q.y, q.z, q.w), _xyz(transform.get_editor_property("scale3d"))))
        location = _xyz(self.camera.get_camera_location())
        rotation = self._rotation(self.camera.get_camera_rotation())
        fov = self.camera.get_fov_angle()
        values = list(location) + list(rotation) + [fov]
        for translation, quaternion, scale in bones:
            values.extend(translation + quaternion + scale)
        if not all(math.isfinite(value) for value in values):
            raise RuntimeError("Original player camera/bone pose is not finite")
        return (location, rotation, fov, tuple(bones))

    def _setup_player(self):
        self._own_world()
        self.pc = unreal.GameplayStatics.get_player_controller(self.world, 0)
        if self.pc is None or not self.pc.is_local_controller():
            raise RuntimeError("Original local PlayerController is missing")
        self.pawn = self.pc.get_controlled_pawn()
        if self.pawn is None:
            raise RuntimeError("Original player pawn is missing")
        meshes = list(self.pawn.get_components_by_class(unreal.SkeletalMeshComponent))
        primary = [c for c in meshes if c.get_name() == "CharacterMesh0"]
        if len(primary) != 1:
            raise RuntimeError("Cannot identify the actual CharacterMesh0")
        self.mesh = primary[0]
        asset = self.mesh.get_editor_property("skeletal_mesh_asset")
        if asset != self.source_mesh or asset.get_path_name() != _MESH:
            raise RuntimeError("The actual player mesh is not the original Pyrios asset")
        cheat = self.pc.get_editor_property("cheat_manager")
        if cheat is None:
            raise RuntimeError("Actual PlayerController has no CheatManager; wireframe is unavailable")
        self.camera = unreal.GameplayStatics.get_player_camera_manager(self.world, 0)
        if self.camera is None or self.mesh.get_anim_instance() is None:
            raise RuntimeError("Original player camera or running animation instance is missing")
        self.outlines = []
        for other in meshes:
            if other == self.mesh or other.get_editor_property("leader_pose_component") != self.mesh:
                continue
            if other.get_editor_property("skeletal_mesh_asset") != asset:
                continue
            materials = [other.get_material(i) for i in range(other.get_num_materials())]
            if (not materials or any(not isinstance(m, unreal.MaterialInstance)
                    or m.get_editor_property("parent") is None
                    or m.get_editor_property("parent").get_path_name() != _OUTLINE for m in materials)):
                raise RuntimeError("Unidentified same-mesh follower would invalidate wireframe attribution")
            self.outlines.append(other)
        lod = self.mesh.get_predicted_lod_level()
        if not 0 <= lod < len(self.source_sections):
            raise RuntimeError("Actual component predicted LOD is invalid")
        slots = list(asset.get_editor_property("materials"))
        if tuple(str(s.material_slot_name) for s in slots) != self.source_slots:
            raise RuntimeError("Original asset material slot identities changed during PIE")
        sections = []
        for section, material_id in enumerate(self.source_sections[lod]):
            material = self.mesh.get_material(material_id)
            if material is None:
                raise RuntimeError("Actual Section material is missing")
            parents = []
            current = material
            while isinstance(current, unreal.MaterialInstance):
                current = current.get_editor_property("parent")
                if current is None or current.get_path_name() in parents:
                    raise RuntimeError("Actual Section material parent is missing or cyclic")
                parents.append(current.get_path_name())
            sections.append(dict(section=section, material_id=material_id,
                                 slot=str(slots[material_id].material_slot_name),
                                 material=material.get_path_name(), parents=parents,
                                 shown=self.mesh.is_material_section_shown(material_id, lod)))
        _emit("actual_player", world=self.world.get_path_name(), pawn=self.pawn.get_path_name(),
              mesh=self.mesh.get_path_name(), asset=asset.get_path_name(),
              animation=self.mesh.get_anim_instance().get_class().get_path_name(),
              controller=self.pc.get_path_name(), cheat_manager=cheat.get_path_name(),
              predicted_lod=lod, forced_lod=self.mesh.get_forced_lod(), sections=sections,
              visible=self.mesh.is_visible(), hidden_in_game=self.mesh.get_editor_property("hidden_in_game"),
              main_pass=self.mesh.get_editor_property("render_in_main_pass"),
              outlines=[o.get_path_name() for o in self.outlines],
              limits="predicted LOD is not GPU readback; per-Section triangles/bDisabled not exposed here")

    def _settle_player(self):
        since = None

        def stationary():
            nonlocal since
            self._live_player()
            anim = self.mesh.get_anim_instance()
            velocity = _xyz(self.pawn.get_velocity())
            if anim is None or not all(math.isfinite(v) for v in velocity):
                raise RuntimeError("Actual player animation/velocity is invalid")
            if anim.is_any_montage_playing() or sum(v * v for v in velocity) > 0.0001:
                since = None
                return False
            now = time.monotonic()
            if since is None:
                since = now
            return now - since >= 0.5

        yield from self._wait(stationary, "actual stationary player without a playing montage")
        _emit("player_settled", condition="stationary and no playing montage for 0.5 seconds",
              limits="does not assert a specific Animation Blueprint state")

    def _body_inputs(self):
        return (tuple(self.mesh.get_editor_property("override_materials")),
                tuple(self.mesh.is_material_section_shown(i, 0) for i in range(4)),
                self.mesh.get_predicted_lod_level())

    def _prepare_soft_diagnostic(self):
        if self.source_sections != ((0, 1, 2, 3),) or self.mesh.get_predicted_lod_level() != 0:
            raise RuntimeError("Soft comparison requires the verified single LOD0 with four unique sections")
        self.original_overrides = tuple(self.mesh.get_editor_property("override_materials"))
        if len(self.original_overrides) <= 2:
            raise RuntimeError("Cannot restore the exact original override array through slot2 SetMaterial")
        self.original_fx_material = self.mesh.get_material(2)
        if self.original_fx_material is None or self.original_fx_material.get_path_name() != _BODY_FX:
            raise RuntimeError("Actual slot2 material is not the original Pyrios Body FX instance")
        if not self.mesh.is_material_section_shown(2, 0):
            raise RuntimeError("Original Body FX section is hidden; there is no valid Lit baseline")
        self.expected_body_inputs = self._body_inputs()
        _emit("soft_baseline", effective_material=self.original_fx_material.get_path_name(),
              original_override=(self.original_overrides[2].get_path_name()
                                 if self.original_overrides[2] is not None else None),
              shown=self.expected_body_inputs[1], lod=0,
              limits="source Time ignores pause; both original Lit ROI images must be visually stable")

    @staticmethod
    def _rgba(color):
        return (color.r, color.g, color.b, color.a)

    def _apply_soft_off(self):
        names = tuple("L%d_SoftCfg" % i for i in range(1, 4))
        available = {str(n) for n in unreal.MaterialEditingLibrary.get_vector_parameter_names(
            self.original_fx_material)}
        if not set(names).issubset(available):
            raise RuntimeError("Original Body FX is missing required SoftCfg vector parameters")
        # The component factory can return an existing MID; this native library
        # always creates a distinct instance, leaving the original material intact.
        self.soft_mid = unreal.MaterialLibrary.create_dynamic_material_instance(
            self.world, self.original_fx_material, optional_name="PyriosBodySoftDiagnostic")
        if (not isinstance(self.soft_mid, unreal.MaterialInstanceDynamic)
                or self.soft_mid == self.original_fx_material
                or self.soft_mid.get_editor_property("parent") != self.original_fx_material):
            raise RuntimeError("Independent transient Body FX MID creation failed")
        before = {name: self._rgba(self.soft_mid.get_vector_parameter_value(name)) for name in names}
        if (not all(math.isfinite(v) for value in before.values() for v in value)
                or not any(value[0] > 0.5 for value in before.values())):
            raise RuntimeError("Original SoftCfg values are invalid or no layer has soft fade enabled")
        for name, value in before.items():
            changed = (0.0,) + value[1:]
            self.soft_mid.set_vector_parameter_value(name, unreal.LinearColor(*changed))
            if self._rgba(self.soft_mid.get_vector_parameter_value(name)) != changed:
                raise RuntimeError("Transient SoftCfg did not preserve y/z/w: " + name)
        if self._body_inputs() != self.expected_body_inputs:
            raise RuntimeError("Original Body material/visibility/LOD changed before soft comparison")
        self.soft_active = True
        self.mesh.set_material(2, self.soft_mid)
        expected = list(self.original_overrides)
        expected[2] = self.soft_mid
        self.expected_body_inputs = (tuple(expected), self.expected_body_inputs[1], 0)
        if self._body_inputs() != self.expected_body_inputs:
            raise RuntimeError("Transient MID slot2 assignment changed unexpected Body inputs")
        _emit("soft_off_applied", mid=self.soft_mid.get_path_name(), original=before,
              changed="only L1/L2/L3_SoftCfg.x=0; y/z/w and all other inherited inputs retained")

    def _restore_soft_material(self):
        if not self.soft_active:
            return
        if self.mesh.get_material(2) != self.soft_mid:
            raise RuntimeError("Slot2 diagnostic MID was replaced; refusing to overwrite another material")
        self.mesh.set_material(2, self.original_overrides[2])
        self.soft_active = False
        self.expected_body_inputs = (self.original_overrides, self.expected_body_inputs[1], 0)
        if (self._body_inputs() != self.expected_body_inputs
                or self.mesh.get_material(2) != self.original_fx_material):
            raise RuntimeError("Original effective Body FX / exact override array did not restore")
        _emit("soft_original_restored", exact_override_array=True,
              slot2_override=(self.original_overrides[2].get_path_name()
                              if self.original_overrides[2] is not None else None))

    def _isolate_body_wireframe(self):
        if self._body_inputs() != self.expected_body_inputs:
            raise RuntimeError("Original Body inputs changed before Section2 wire isolation")
        shown = list(self.expected_body_inputs[1])
        for material_id in (0, 1, 3):
            if not shown[material_id]:
                continue
            self.hidden_sections.append((material_id, True))
            self.mesh.show_material_section(material_id, material_id, False, 0)
            if self.mesh.is_material_section_shown(material_id, 0):
                raise RuntimeError("Could not hide non-FX material section " + str(material_id))
            shown[material_id] = False
        self.expected_body_inputs = (self.original_overrides, tuple(shown), 0)
        _emit("section2_wire_isolated", shown=shown,
              limits="geometry coverage only; hidden armor changes depth and is never used for Lit A/B")

    @staticmethod
    def _png_size(path):
        if not path.exists():
            return None
        data = path.read_bytes()
        if len(data) < 24 or data[-12:] != b"\x00\x00\x00\x00IEND\xaeB\x60\x82":
            return None
        if data[:8] != b"\x89PNG\r\n\x1a\n":
            raise RuntimeError("Native Shot output is not a PNG: " + str(path))
        size = struct.unpack(">II", data[16:24])
        if min(size) <= 0:
            raise RuntimeError("Native Shot PNG has invalid dimensions")
        return size

    def _shot(self, name):
        # Allow the verified native viewmode to render before requesting its framebuffer.
        for _ in range(3):
            yield
        if self.soft_diagnostic and self._body_inputs() != self.expected_body_inputs:
            raise RuntimeError("Expected Body material/section visibility/LOD changed before " + name)
        if self._pose() != self.frozen_pose:
            raise RuntimeError("Original bones/camera changed before " + name)
        path = self.files[name]
        # The native API requests the active SLevelViewport's own viewport,
        # which is our embedded PIE destination. Do not queue a global Shot.
        # A competing viewport can still consume the high-res global flag first;
        # the target keeps its own pending flag. Wait beyond the global task's
        # completion for the final file, and leave world attribution to review.
        self.capture_task = unreal.AutomationLibrary.take_high_res_screenshot(
            1280, 1280, str(path).replace("\\", "/"), camera=None,
            mask_enabled=False, capture_hdr=False, delay=0.0, force_game_view=False)
        if self.capture_task is None or not self.capture_task.is_valid_task():
            raise RuntimeError("Native active PIE high-resolution screenshot task is invalid")
        yield from self._wait(self.capture_task.is_task_done, name + " native screenshot task")
        previous = None
        stable_ticks = 0

        def complete_file():
            nonlocal previous, stable_ticks
            size = self._png_size(path)
            if size is None:
                return None
            stat = path.stat()
            receipt = (stat.st_mtime_ns, stat.st_size)
            stable_ticks = stable_ticks + 1 if receipt == previous else 0
            previous = receipt
            return size if stable_ticks >= 3 else None

        size = yield from self._wait(complete_file, name + " final complete PNG")
        self.capture_task = None
        if size != (1280, 1280):
            raise RuntimeError("Native high-resolution screenshot dimensions differ from the request: " + repr(size))
        if self._pose() != self.frozen_pose:
            raise RuntimeError("Original bones/camera changed during " + name + " capture")
        if self.soft_diagnostic and self._body_inputs() != self.expected_body_inputs:
            raise RuntimeError("Expected Body material/section visibility/LOD changed during " + name)
        _emit("shot_written_pending_visual_review", view=name, file=str(path),
              width=size[0], height=size[1], same_player_camera_and_bones=True,
              requested_viewport=str(self.viewport_key),
              capture="native active PIE viewport high-resolution task",
              limits="completion is global; verify actual player/world/viewmode visually")
        return size

    def _run(self):
        failure = None
        try:
            self.pie_requested = True
            self.les.editor_request_begin_play()
            self.world = yield from self._wait(self.ues.get_game_world, "self-started PIE world")
            settled = time.monotonic() + 1.0
            yield from self._wait(lambda: time.monotonic() >= settled, "native PIE initialization")
            self._setup_player()
            yield from self._settle_player()
            if self.soft_diagnostic:
                self._prepare_soft_diagnostic()
            self.original_mode = yield from self._query_mode()
            self.original_pause = unreal.GameplayStatics.is_game_paused(self.world)
            if not self.original_pause:
                self.pause_changed = True
                if not unreal.GameplayStatics.set_game_paused(self.world, True):
                    raise RuntimeError("Native game pause was refused")
            self.frozen_pose = self._pose()
            yield from self._set_mode("Lit")
            if self.soft_diagnostic:
                lit_size = yield from self._shot("LitOriginalA")
                self._apply_soft_off()
                yield from self._shot("LitSoftOff")
                self._restore_soft_material()
                yield from self._shot("LitOriginalB")
            else:
                lit_size = yield from self._shot("Lit")
            # These are qualified transient followers; hide only them, not primary Mesh sections.
            for outline in self.outlines:
                visible = outline.is_visible()
                self.hidden_outlines.append((outline, visible))
                outline.set_visibility(False, False)
                if outline.is_visible():
                    raise RuntimeError("Could not hide the identified outline for wireframe attribution")
            yield from self._set_mode("Wireframe")
            if self.soft_diagnostic:
                self._isolate_body_wireframe()
            wire_size = yield from self._shot("Section2Wireframe" if self.soft_diagnostic else "Wireframe")
            if lit_size != wire_size:
                raise RuntimeError("Native Lit/Wireframe viewport dimensions differ")
        except Exception as exc:
            failure = str(exc)
            unreal.log_error("PYRIOS_BODY_CAPTURE failed: " + failure)
        self.outcome = ("failed: " + failure if failure else
                        "soft_ABA_and_section2_wire_pending_visual_review" if self.soft_diagnostic else
                        "two_files_pending_visual_review")
        yield from self._cleanup()
        _emit("finished", outcome=self.outcome, files={k: str(v) for k, v in self.files.items()},
              cleanup="own PIE ended; owned material/section changes, mode/pause/outline/editor camera restored; packages clean",
              limits="inspect the original cloth ROI; soft attribution requires stable A/A and same-place B fill")

    def _cleanup(self):
        # Restore before End PIE; never use a replacement PC/world to finish an old receipt.
        errors = []
        if self.world is not None:
            self._own_world()
            if self.soft_active:
                try:
                    self._restore_soft_material()
                except Exception as exc:
                    errors.append("slot2 material: " + str(exc))
            for material_id, shown in self.hidden_sections:
                try:
                    self.mesh.show_material_section(material_id, material_id, shown, 0)
                    if self.mesh.is_material_section_shown(material_id, 0) != shown:
                        raise RuntimeError("original section visibility did not restore")
                except Exception as exc:
                    errors.append("Body section " + str(material_id) + ": " + str(exc))
            for outline, visible in self.hidden_outlines:
                try:
                    outline.set_visibility(visible, False)
                    if outline.is_visible() != visible:
                        raise RuntimeError("visibility did not restore")
                except Exception as exc:
                    errors.append("outline " + outline.get_path_name() + ": " + str(exc))
            if self.mode_changed:
                try:
                    self._cmd("viewmode " + self.original_mode)
                    if (yield from self._query_mode()).lower() != self.original_mode.lower():
                        raise RuntimeError("native original mode did not restore")
                    self.mode_changed = False
                except Exception as exc:
                    errors.append("GameViewport viewmode: " + str(exc))
            if self.pause_changed:
                try:
                    if not unreal.GameplayStatics.set_game_paused(self.world, self.original_pause):
                        raise RuntimeError("native pause restoration was refused")
                    if unreal.GameplayStatics.is_game_paused(self.world) != self.original_pause:
                        raise RuntimeError("native pause state did not restore")
                    self.pause_changed = False
                except Exception as exc:
                    errors.append("game pause: " + str(exc))
            # One failed temporary restoration must not prevent ending our own world.
            self._own_world()
            self.les.editor_request_end_play()
            yield from self._wait(lambda: not self.les.is_in_play_in_editor()
                                  and self.ues.get_game_world() is None, "own End PIE")
        elif self.pie_requested and self.les.is_in_play_in_editor():
            raise RuntimeError("PIE became active without an owned world; refusing to stop it")
        try:
            self.ues.set_level_viewport_camera_info(self.editor_location, self.editor_rotation)
            camera = self.ues.get_level_viewport_camera_info()
            if camera is None or (_xyz(camera[0]), self._rotation(camera[1])) != self.editor_camera:
                raise RuntimeError("native original camera did not restore")
        except Exception as exc:
            errors.append("editor camera: " + str(exc))
        try:
            self.actors.set_selected_level_actors(self.selected_actors)
            if list(self.actors.get_selected_level_actors()) != self.selected_actors:
                raise RuntimeError("original actor selection did not restore")
            assets = tuple(a.get_path_name() for a in unreal.EditorUtilityLibrary.get_selected_assets())
            if assets != self.selected_assets:
                raise RuntimeError("asset selection changed")
        except Exception as exc:
            errors.append("editor selection: " + str(exc))
        if _dirty() != self.original_dirty:
            errors.append("dirty packages changed; preserve editor for review")
        if errors:
            raise RuntimeError("Body cleanup failed: " + "; ".join(errors))

    def _advance(self):
        try:
            next(self.steps)
        except StopIteration:
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None
            self.world = self.pc = self.pawn = self.mesh = self.camera = None
            self.source_mesh = self.capture_task = None
            self.hidden_outlines.clear()
            self.hidden_sections.clear()
            self.original_overrides = self.original_fx_material = self.soft_mid = None
            self.expected_body_inputs = None
            self.outlines = []
            self.steps = None
            if globals().get("_pyrios_body_capture") is self:
                globals()["_pyrios_body_capture"] = None
            if self.exit_after == "1":
                unreal.SystemLibrary.quit_editor()
        except Exception as exc:
            # A cleanup failure is not success. Preserve the host/state and stop our observer.
            unreal.log_error("PYRIOS_BODY_CAPTURE cleanup_failed: " + str(exc))
            unreal.unregister_slate_post_tick_callback(self.handle)
            self.handle = None

    def tick(self, _delta_seconds):
        # Native screenshot loading can pump Slate before the outer next()
        # returns. That nested callback must leave the original generator and
        # its observer alive; the outer advancement still owns all progress.
        if self.advancing:
            return
        self.advancing = True
        try:
            self._advance()
        finally:
            self.advancing = False


_CONTRIBUTION_SHA = "97e19b7e145ea1cdd6b334f8ccd8a2d55e7ec2d958faf7af41d222a6130c6692"
_CONTRIBUTION_ROOT = "/Game/Characters/Player/Pyrios/Materials/Generated"
_CONTRIBUTION_NAMES = ("Master", "Body_1", "Body_2", "Weapon01")
_CONTRIBUTION_PATHS = tuple(_CONTRIBUTION_ROOT + "/__PyriosContribution_20261010_R1_" + n
                            for n in _CONTRIBUTION_NAMES)
_CONTRIBUTION_DISK = {
    "Avatar_Male_Size03_Pyrois_Model.uasset": "d6360f9741cbd1c1754dd814be8a1b58ab347e9ef98ee4364788c0998cfbeb34",
    "Materials/Generated/M_Pyrois_Toon.uasset": "c50f20b240db1b1f4fe3084e97c954473efa99468093c8f6f6722915450d88fc",
    "Materials/Generated/MI_Pyrois_Body_1.uasset": "198f9538cf52ed4e00c1fe42006d2c34429254d06176e54bce59aca12c496d59",
    "Materials/Generated/MI_Pyrois_Body_2.uasset": "bfd7b4ab5d641a0fea823a439bdb405d1a2e5f6d7a446ef0f41c319a68739403",
    "Materials/Generated/MI_Pyrois_Weapon01.uasset": "a3b23edc2ebd4e0bebcdb389f8dea50bd795e2cfbd27fee436ee1418a91d7ef6",
}


def contribution_code(source, stage):
    """仅替换实际返回值；寄存器锚点及整段源 SHA 必须与本次正式 Master 一致。"""
    if hashlib.sha256(source.encode("utf-8")).hexdigest() != _CONTRIBUTION_SHA:
        raise RuntimeError("贡献诊断拒绝未知 Toon 源码")
    if stage not in ("Final", "Albedo", "MatCap", "Surface", "Rim"):
        raise RuntimeError("未知贡献阶段: " + stage)
    if stage == "Final":
        return source
    before = "  r2.x = cmp(_CharacterMatCapEnable.x >= 0.5);"
    after = "  r0.y = cmp(0.5 < v7.z);\n  if (r3.w == 0) {"
    output = "  return c + max(0.0, max(c.x, max(c.y, c.z)) - 1.0) * HighlightBleed.x;"
    for anchor in (before, after, output):
        if source.count(anchor) != 1:
            raise RuntimeError("贡献阶段寄存器锚点不唯一")
    if stage == "Albedo":
        source = source.replace(before, "  float3 diagnosticAlbedo = r1.xyz;\n" + before)
    elif stage == "MatCap":
        source = source.replace(after, "  float3 diagnosticMatCap = r1.xyz;\n" + after)
    value = {"Albedo": "diagnosticAlbedo", "MatCap": "diagnosticMatCap",
             "Surface": "o0.xyz", "Rim": "min(rimOut, 25.0)"}[stage]
    return source.replace(output, "  return " + value + ";")


def _contribution_check_owned(dirty, owned):
    unexpected = set(dirty) - set(owned)
    if unexpected:
        raise RuntimeError("出现非自有脏包，保留宿主: " + repr(sorted(unexpected)))


_DISPLAY_EXPOSURE = "PyriosDiagnosticExposureWeight"
# 只用于隔离对照的暗面候选；是编辑器校准值，不是原游戏运行时数据。
_DISPLAY_SHADOWS = {"_PostShadowTint": (0.12, 0.18, 0.25, 1.0),
                    "_PostShadowFadeTint": (0.22, 0.30, 0.38, 1.0)}
# 亮面单独与已有 Exposure 对照；暗面恢复原值，不将两组变化混为同一原因。
_DISPLAY_SHALLOWS = {"_PostShallowTint": (0.30, 0.42, 0.50, 1.0),
                     "_PostShallowFadeTint": (0.25, 0.34, 0.42, 1.0)}


def display_parameters(original, stage):
    """有限亮／暗面候选及曝光对照，保留全部其它材质和实际主光参数。"""
    if stage not in ("Baseline", "Exposure", "ShadowTints", "ShadowTintsExposure", "ShallowTintsExposure"):
        raise RuntimeError("未知显示对照阶段: " + stage)
    if set(original) != {0, 1, 3}:
        raise RuntimeError("显示对照需要原三个表面槽")
    result = {}
    for index, parameters in original.items():
        if "scalar:" + _DISPLAY_EXPOSURE in parameters:
            raise RuntimeError("原材质已有诊断参数，拒绝覆盖")
        for name in (*_DISPLAY_SHADOWS, *_DISPLAY_SHALLOWS):
            value = parameters.get("vector:" + name)
            if value is None or len(value) != 4 or not all(math.isfinite(v) for v in value):
                raise RuntimeError("原后染色输入无效: " + name)
        values = dict(parameters)
        values["scalar:" + _DISPLAY_EXPOSURE] = 1.0 if stage in ("Exposure", "ShadowTintsExposure", "ShallowTintsExposure") else 0.0
        candidates = (_DISPLAY_SHADOWS if stage in ("ShadowTints", "ShadowTintsExposure") else
                      _DISPLAY_SHALLOWS if stage == "ShallowTintsExposure" else {})
        if candidates:
            # LinearColor 原生存 float32；期望值按相同位宽记录，不能用 double 误拒绝合法读回。
            values.update({"vector:" + n: struct.unpack("<4f", struct.pack("<4f", *v))
                           for n, v in candidates.items()})
        result[index] = values
    return result


def display_input_names(names):
    """使用原生反射读回的真实输入名，拒绝名称或顺序改变。"""
    names = tuple(str(n) for n in names)
    if names != ("LightValueInput", "AlphaInput"):
        raise RuntimeError("原生曝光节点输入契约不符: " + repr(names))
    return names


class PyriosContributionCapture:
    """MCP 分步调用的有限 SIE 诊断；无帧调度、无正式参数写入、无保存。"""

    def __init__(self):
        self.ues = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        self.les = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        self.materials, self.mids = [], {}
        self.expected_parameters = {}
        self.display_nodes = ()
        self.world = self.pawn = self.mesh = None
        self.stage = None
        self.end_requested = False
        if _dirty() or self.les.is_in_play_in_editor() or self.ues.get_game_world() is not None:
            raise RuntimeError("贡献诊断要求干净、非 PIE 的独立宿主")
        if self.ues.get_editor_world().get_path_name() != _MAP or unreal.SourceControl.is_enabled():
            raise RuntimeError("地图不符或源码管理启用；复制可能自动保存，拒绝诊断")
        self.camera = self.ues.get_level_viewport_camera_info()
        if self.camera is None:
            raise RuntimeError("无法保存原视口摄像机")
        self.code = Path(__file__).with_name("nap_avatar_toon.hlsl").read_text(encoding="utf-8")
        contribution_code(self.code, "Final")
        self.disk = self._disk()
        if any(self.disk.get(p) != value for p, value in _CONTRIBUTION_DISK.items()):
            raise RuntimeError("正式五包 SHA 与本次冻结输入不符")
        eal = unreal.EditorAssetLibrary
        if any(eal.does_asset_exist(p) or unreal.find_object(None, p + "." + p.rsplit("/", 1)[1])
               for p in _CONTRIBUTION_PATHS):
            raise RuntimeError("诊断目标包已存在，拒绝复用或覆盖")
        source = eal.load_asset(_CONTRIBUTION_ROOT + "/M_Pyrois_Toon")
        self.source_master = source
        self.clip = eal.load_asset("/Game/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Idle_Loop")
        if not isinstance(self.clip, unreal.AnimSequence):
            raise RuntimeError("非 PIE 预加载原 Idle 失败")
        self.source_graph = self._graph(source)
        if (self.source_graph[0] != self.code or len(self.source_graph[1]) != 185
                or self.source_graph[3] != 186
                or source.get_editor_property("shading_model") != unreal.MaterialShadingModel.MSM_UNLIT):
            raise RuntimeError("正式 Toon 图不是已冻结的 185 输入 Unlit 程序")
        sources = [source] + [eal.load_asset(_CONTRIBUTION_ROOT + "/MI_Pyrois_" + n)
                              for n in _CONTRIBUTION_NAMES[1:]]
        if any(not isinstance(mi, unreal.MaterialInstanceConstant)
               or mi.get_editor_property("parent") != source for mi in sources[1:]):
            raise RuntimeError("正式三个 MI 的父材质身份不符")
        # /Temp 是原生只读 mount，AssetTools 拒绝创建。只在原目录创建四个
        # 独占、不保存的诊断包；SCC 关闭后 DuplicateLoadedAsset 不会自动落盘。
        for original, path in zip(sources, _CONTRIBUTION_PATHS):
            copied = eal.duplicate_loaded_asset(original, path)
            if copied is None or copied.get_path_name() != path + "." + path.rsplit("/", 1)[1]:
                raise RuntimeError("原生复制失败，保留已创建现场: " + path)
            self.materials.append(copied)
        self.master = self.materials[0]
        self.custom = unreal.MaterialEditingLibrary.get_material_property_input_node(
            self.master, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        if self._graph(self.master) != self.source_graph:
            raise RuntimeError("复制材质图与正式图不等价")
        mel = unreal.MaterialEditingLibrary
        for original, copied in zip(sources[1:], self.materials[1:]):
            if original.get_editor_property("base_property_overrides").export_text() != copied.get_editor_property("base_property_overrides").export_text():
                raise RuntimeError("MI 原生属性覆盖复制不等价")
            mel.set_material_instance_parent(copied, self.master)
            mel.update_material_instance(copied)
            if copied.get_editor_property("parent") != self.master:
                raise RuntimeError("诊断 MI 父材质设置失败")
            if self._parameters(original) != self._parameters(copied):
                raise RuntimeError("诊断 MI 全部有效参数与正式 MI 不等价")
        self._protect()
        self.les.editor_play_simulate()
        _emit("contribution_sie_requested", owned_packages=_CONTRIBUTION_PATHS,
              limits="隔离旧 Idle 的材质贡献诊断，不代表生产初始化通过")

    @staticmethod
    def _graph(master, custom=None):
        mel = unreal.MaterialEditingLibrary
        if custom is None:
            custom = mel.get_material_property_input_node(master, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        if not isinstance(custom, unreal.MaterialExpressionCustom):
            raise RuntimeError("实际 Emissive 未直接连接 Toon Custom")
        pins = tuple(str(p.get_editor_property("input_name")) for p in custom.get_editor_property("inputs"))
        connections = mel.get_inputs_for_material_expression(master, custom)
        if len(connections) != len(pins) or not all(connections):
            raise RuntimeError("185 输入有断线")
        # 原生深复制重定向每个图内对象，比较其相对路径与类型，拒绝连回正式图。
        prefix = master.get_path_name() + ":"
        if any(not c.get_path_name().startswith(prefix) for c in connections):
            raise RuntimeError("诊断图输入引用了外部材质节点")
        links = tuple((c.get_path_name()[len(prefix):], c.get_class().get_name()) for c in connections)
        return (custom.get_editor_property("code"), pins, links, len(mel.get_material_expressions(master)))

    @staticmethod
    def _parameters(material):
        mel = unreal.MaterialEditingLibrary
        dynamic = isinstance(material, unreal.MaterialInstanceDynamic)
        result = {}
        if mel.get_static_switch_parameter_names(material):
            raise RuntimeError("本次诊断不支持未知静态开关变体")
        for kind in ("scalar", "vector", "texture"):
            names = getattr(mel, "get_" + kind + "_parameter_names")(material)
            getter = (getattr(material, "get_" + kind + "_parameter_value") if dynamic else
                      getattr(mel, "get_material_instance_" + kind + "_parameter_value"))
            for name in names:
                value = getter(name) if dynamic else getter(material, name)
                if kind == "vector":
                    value = _BodyCapture._rgba(value)
                elif kind == "texture":
                    value = value.get_path_name() if value else None
                if kind != "texture" and not all(math.isfinite(v) for v in (value if kind == "vector" else (value,))):
                    raise RuntimeError("非有限材质参数: " + str(name))
                result[kind + ":" + str(name)] = value
        return result

    @staticmethod
    def _disk():
        root = Path(unreal.Paths.project_content_dir()) / "Characters/Player/Pyrios"
        return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
                for p in root.rglob("*") if p.is_file() and p.suffix in (".uasset", ".uexp", ".ubulk")
                and p.relative_to(root).parts[0] != "FX"}

    def _protect(self):
        _contribution_check_owned(_dirty(), _CONTRIBUTION_PATHS[:len(self.materials)])
        if self._disk() != self.disk:
            raise RuntimeError("正式磁盘包或不保存临时包发生变化，保留宿主")
        if self._graph(self.source_master) != self.source_graph:
            raise RuntimeError("正式 Master 内存图发生变化")

    def resume_prepared_attachment(self):
        """仅恢复已证未修改角色的旧 load_asset/PIE 拒绝点，不吞失败。"""
        if (self.world is None or self.ues.get_game_world() != self.world
                or self.stage is not None or not hasattr(self, "flags")
                or tuple(self.mesh.get_editor_property("override_materials")) != self.overrides):
            raise RuntimeError("不是本次未修改的 attach 拒绝点")
        actual = (self.pawn.get_editor_property("hidden"), self.mesh.is_visible(),
                  self.mesh.get_editor_property("hidden_in_game"), self.mesh.is_component_tick_enabled(),
                  self.mesh.get_animation_mode(), unreal.GameplayStatics.is_game_paused(self.world))
        if actual != self.flags:
            raise RuntimeError("角色状态已变，不能重做 attach")
        # PyCore::LoadAsset 是原生资产读取，允许当前 SIE；不使用拒绝 PIE 的
        # EditorAssetLibrary。正常入口仍在非 PIE 前预加载，这里只恢复原失败现场。
        self.source_master = unreal.find_asset(_CONTRIBUTION_ROOT + "/M_Pyrois_Toon", type=unreal.Material)
        self.clip = unreal.load_asset("/Game/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Idle_Loop", type=unreal.AnimSequence)
        if self.source_master is None or not isinstance(self.clip, unreal.AnimSequence):
            raise RuntimeError("无法读回原两个资产，保留现场")
        self._protect()
        self.world = self.pawn = self.mesh = None
        self.attach()

    def attach(self):
        """仅在本实例发起的唯一 SIE 就绪后调用。"""
        if self.world is not None:
            raise RuntimeError("贡献诊断已绑定，拒绝重复接入")
        world = self.ues.get_game_world()
        if world is None or list(unreal.EditorLevelLibrary.get_pie_worlds(True)) != [world]:
            raise RuntimeError("尚无本次唯一 SIE world")
        candidates = [a for a in unreal.GameplayStatics.get_all_actors_of_class(world, unreal.Character)
                      if a.get_class().get_path_name() == "/Game/BP/Character/Player/BP_PC_Pyrios.BP_PC_Pyrios_C"]
        if len(candidates) != 1:
            raise RuntimeError("SIE 中无法唯一定位原 Pyrios")
        self.world, self.pawn = world, candidates[0]
        meshes = [c for c in self.pawn.get_components_by_class(unreal.SkeletalMeshComponent)
                  if c.get_name() == "CharacterMesh0"]
        if len(meshes) != 1 or meshes[0].get_editor_property("skeletal_mesh_asset").get_path_name() != _MESH:
            raise RuntimeError("原角色 Mesh 身份不符")
        self.mesh = meshes[0]
        self.overrides = tuple(self.mesh.get_editor_property("override_materials"))
        self.original_materials = tuple(self.mesh.get_material(i) for i in range(4))
        if len(self.overrides) != 4 or self.mesh.get_material(2).get_path_name() != _BODY_FX:
            raise RuntimeError("原四槽实际覆盖不符")
        self.original_parameters = {}
        for index, suffix, copied in zip((0, 1, 3), _CONTRIBUTION_NAMES[1:], self.materials[1:]):
            original = self.mesh.get_material(index)
            parent_path = _CONTRIBUTION_ROOT + "/MI_Pyrois_" + suffix + ".MI_Pyrois_" + suffix
            if (not isinstance(original, unreal.MaterialInstanceDynamic)
                    or original.get_editor_property("parent").get_path_name() != parent_path):
                raise RuntimeError("实际 RenderComponent MID 的父材质身份不符")
            self.original_parameters[index] = self._parameters(original)
            mid = unreal.MaterialLibrary.create_dynamic_material_instance(world, copied,
                      optional_name="PyriosContributionSlot" + str(index))
            if not isinstance(mid, unreal.MaterialInstanceDynamic) or mid.get_editor_property("parent") != copied:
                raise RuntimeError("自有 transient MID 创建失败")
            mid.copy_material_instance_parameters(original, False)
            if self._parameters(mid) != self.original_parameters[index]:
                raise RuntimeError("实际四灯值或 MI 参数复制不等价")
            self.mids[index] = mid
            self.expected_parameters[index] = dict(self.original_parameters[index])
        self.flags = (self.pawn.get_editor_property("hidden"), self.mesh.is_visible(),
                      self.mesh.get_editor_property("hidden_in_game"), self.mesh.is_component_tick_enabled(),
                      self.mesh.get_animation_mode(), unreal.GameplayStatics.is_game_paused(world))
        clip = self.clip
        if not isinstance(clip, unreal.AnimSequence) or clip.get_editor_property("skeleton") != self.mesh.get_editor_property("skeletal_mesh_asset").get_editor_property("skeleton"):
            raise RuntimeError("原 Idle 与原骨架不兼容")
        self.pawn.set_actor_hidden_in_game(False)
        self.mesh.set_visibility(True, False)
        self.mesh.set_hidden_in_game(False, False)
        self.mesh.set_component_tick_enabled(True)
        self.mesh.play_animation(clip, True)
        self.mesh.set_position(0.0, False)
        self.mesh.set_play_rate(0.0)
        if not self.flags[-1] and not unreal.GameplayStatics.set_game_paused(world, True):
            raise RuntimeError("原生暂停失败")
        _emit("contribution_attached", mesh=self.mesh.get_path_name(), parameters=self.original_parameters)

    def witness(self):
        if (self.world is None or self.ues.get_game_world() != self.world
                or list(unreal.EditorLevelLibrary.get_pie_worlds(True)) != [self.world]):
            raise RuntimeError("本次 SIE 身份变化")
        if not unreal.GameplayStatics.is_game_paused(self.world):
            raise RuntimeError("诊断姿态未暂停")
        if self.mesh.get_num_bones() != 177:
            raise RuntimeError("原177骨姿态不符")
        for index, values in self.original_parameters.items():
            if (self._parameters(self.overrides[index]) != values
                    or self._parameters(self.mids[index]) != self.expected_parameters[index]):
                raise RuntimeError("原灯光或诊断参数在阶段间变化")
            if self.mesh.get_material(index) not in (self.overrides[index], self.mids[index]):
                raise RuntimeError("出现非自有材质覆盖，拒绝覆盖")
        # slot2 的 override 原生为 None，实际材质来自 Mesh 默认槽。
        # 保护有效材质与完整 override 数组分别读回，不能把合法继承当变化。
        if self.mesh.get_material(2) != self.original_materials[2]:
            raise RuntimeError("披风材质发生变化")
        self._protect()
        return tuple(self.mesh.get_socket_transform(self.mesh.get_bone_name(i),
                     unreal.RelativeTransformSpace.RTS_WORLD).export_text() for i in range(177))

    def select(self, stage):
        if self.display_nodes:
            raise RuntimeError("显示对照不能混用贡献输出阶段")
        pose = self.witness()
        custom = unreal.MaterialEditingLibrary.get_material_property_input_node(self.master, unreal.MaterialProperty.MP_EMISSIVE_COLOR)
        custom.set_editor_property("code", contribution_code(self.code, stage))
        errors = unreal.MaterialEditingLibrary.recompile_material(self.master)
        if errors or unreal.MaterialEditingLibrary.get_statistics(self.master).num_pixel_shader_instructions <= 0:
            raise RuntimeError("诊断材质未成功编译: " + repr(errors))
        for index, mid in self.mids.items():
            self.mesh.set_material(index, mid)
        if self.witness() != pose:
            raise RuntimeError("阶段编译或绑定改变了姿态")
        graph = self._graph(self.master)
        if graph[0] != contribution_code(self.code, stage) or graph[1:] != self.source_graph[1:]:
            raise RuntimeError("诊断输出之外的图发生变化")
        self.stage = stage
        _emit("contribution_selected", contribution=stage, bone_count=len(pose), source_sha=_CONTRIBUTION_SHA)

    def select_display(self, stage):
        """原 Custom 保持逐字不变；原生节点在 GPU 使用真实曝光，PNG 不作精确曝光读回。"""
        expected = display_parameters(self.original_parameters, stage)
        pose = self.witness()
        mel = unreal.MaterialEditingLibrary
        if self._graph(self.master, self.custom)[:3] != self.source_graph[:3]:
            raise RuntimeError("显示对照要求原 Toon 程序及全部185输入不变")
        if not self.display_nodes:
            if self.stage is not None:
                raise RuntimeError("显示对照需要未改输出的临时材质")
            inverse = mel.create_material_expression(self.master, unreal.MaterialExpressionEyeAdaptationInverse, 4200, 0)
            weight = mel.create_material_expression(self.master, unreal.MaterialExpressionScalarParameter, 4000, 220)
            if inverse is None or weight is None:
                raise RuntimeError("原生曝光节点创建失败，保留临时现场")
            self.display_nodes = (inverse, weight)
            weight.set_editor_property("parameter_name", _DISPLAY_EXPOSURE)
            weight.set_editor_property("default_value", 0.0)
            # 原生查询会枚举尚未接线的 scalar；从创建开始保护这个零权重输入。
            self.expected_parameters = display_parameters(self.original_parameters, "Baseline")
        if self.stage is None:
            inverse, weight = self.display_nodes
            light_pin, alpha_pin = display_input_names(mel.get_material_expression_input_names(inverse))
            if not (mel.connect_material_expressions(self.custom, "", inverse, light_pin)
                    and mel.connect_material_expressions(weight, "", inverse, alpha_pin)
                    and mel.connect_material_property(inverse, "", unreal.MaterialProperty.MP_EMISSIVE_COLOR)):
                raise RuntimeError("原生曝光节点接线失败")
            errors = mel.recompile_material(self.master)
            if errors or mel.get_statistics(self.master).num_pixel_shader_instructions <= 0:
                raise RuntimeError("显示对照材质编译失败: " + repr(errors))
        for index, mid in self.mids.items():
            mid.set_scalar_parameter_value(_DISPLAY_EXPOSURE, expected[index]["scalar:" + _DISPLAY_EXPOSURE])
            for name in (*_DISPLAY_SHADOWS, *_DISPLAY_SHALLOWS):
                mid.set_vector_parameter_value(name, unreal.LinearColor(*expected[index]["vector:" + name]))
        self.expected_parameters = expected
        for index, mid in self.mids.items():
            self.mesh.set_material(index, mid)
        inverse, weight = self.display_nodes
        graph = self._graph(self.master, self.custom)
        if (graph[:3] != self.source_graph[:3] or graph[3] != self.source_graph[3] + 2
                or mel.get_material_property_input_node(self.master, unreal.MaterialProperty.MP_EMISSIVE_COLOR) != inverse
                or tuple(mel.get_inputs_for_material_expression(self.master, inverse)) != (self.custom, weight)):
            raise RuntimeError("显示对照改变了原图或曝光节点接线")
        if self.witness() != pose:
            raise RuntimeError("显示对照改变了原姿态")
        self.stage = stage
        _emit("display_selected", display=stage, bone_count=len(pose), source_sha=_CONTRIBUTION_SHA,
              diagnostic_parameters={i: {k: v for k, v in values.items()
                  if k == "scalar:" + _DISPLAY_EXPOSURE or k in ("vector:" + n for n in (*_DISPLAY_SHADOWS, *_DISPLAY_SHALLOWS))}
                  for i, values in expected.items()})

    def request_end(self):
        self.witness()
        for index in self.mids:
            self.mesh.set_material(index, self.overrides[index])
        if tuple(self.mesh.get_editor_property("override_materials")) != self.overrides:
            raise RuntimeError("原四槽覆盖未完整恢复")
        hidden, visible, mesh_hidden, tick, mode, paused = self.flags
        self.mesh.set_animation_mode(mode)
        self.mesh.set_component_tick_enabled(tick)
        self.mesh.set_visibility(visible, False)
        self.mesh.set_hidden_in_game(mesh_hidden, False)
        self.pawn.set_actor_hidden_in_game(hidden)
        if unreal.GameplayStatics.is_game_paused(self.world) != paused:
            unreal.GameplayStatics.set_game_paused(self.world, paused)
        if unreal.GameplayStatics.is_game_paused(self.world) != paused:
            raise RuntimeError("原暂停状态未恢复")
        if (self.pawn.get_editor_property("hidden"), self.mesh.is_visible(),
            self.mesh.get_editor_property("hidden_in_game"), self.mesh.is_component_tick_enabled(),
            self.mesh.get_animation_mode(), unreal.GameplayStatics.is_game_paused(self.world)) != self.flags:
            raise RuntimeError("原可见/动画/组件状态未恢复")
        self.end_requested = True
        self.les.editor_request_end_play()

    def finish(self):
        if not self.end_requested or self.les.is_in_play_in_editor() or self.ues.get_game_world() is not None:
            raise RuntimeError("本次 SIE 尚未原生结束，拒绝删临时包")
        self._protect()
        self.mids.clear()
        self.display_nodes = ()
        self.custom = None
        self.expected_parameters.clear()
        self.world = self.pawn = self.mesh = self.overrides = None
        # 只删除本实例创建的四个精确对象。无目录删除、无清 dirty、无 SaveAll。
        owned = list(reversed(self.materials))
        if [m.get_path_name().split(".")[0] for m in reversed(owned)] != list(_CONTRIBUTION_PATHS):
            raise RuntimeError("临时对象身份不符，拒绝清理")
        if not unreal.EditorAssetLibrary.delete_loaded_assets(owned):
            raise RuntimeError("原生精确临时包删除失败，保留宿主")
        if any(unreal.EditorAssetLibrary.does_asset_exist(p) for p in _CONTRIBUTION_PATHS):
            raise RuntimeError("临时资产仍存在，拒绝结束")
        self.materials.clear()
        self.master = None
        self.ues.set_level_viewport_camera_info(*self.camera)
        if self.ues.get_level_viewport_camera_info() != self.camera or _dirty() or self._disk() != self.disk:
            raise RuntimeError("摄像机/dirty/正式磁盘保护未恢复，保留宿主")
        _emit("contribution_cleaned", dirty=[], temporary_assets_absent=True, disk_unchanged=True)


if __name__ == "__main__":
    _mode = os.environ.get("PYRIOS_CAP_MODE", "toon")
    if _mode == "toon":
        _capture_toon()
    elif _mode in ("body", "body_soft"):
        if globals().get("_pyrios_body_capture") is not None:
            raise RuntimeError("Body observer is already registered in this Python session")
        _pyrios_body_capture = _BodyCapture(soft_diagnostic=_mode == "body_soft")
        _pyrios_body_capture.handle = unreal.register_slate_post_tick_callback(_pyrios_body_capture.tick)
        if _pyrios_body_capture.handle is None:
            raise RuntimeError("Body post-tick observation registration failed")
        _emit("registered", output_prefix=str(_pyrios_body_capture.prefix),
              log=str(_pyrios_body_capture.log), mode=_mode)
    else:
        raise RuntimeError("Unknown PYRIOS_CAP_MODE: " + _mode)
