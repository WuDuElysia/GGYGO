"""@file observe_pyrios_evade_pose.py
@brief 在独立标准 Editor 的自有、不保存预览关卡观察原闪避姿态。

PYRIOS_EVADE_POSE_OUT 必须是项目 Saved 下未存在的绝对目录。
只消费原 Mesh、Skeleton、两段 Evade 和 Idle；原生 SingleNode SetPosition
关闭 Notify，随后等待实际 Editor 帧求值。相机随姿态构图，不证明 CMC
位移或生产 Montage 衔接。PNG 和骨变换读回均保留；视觉结论另行实看。
工具拥有临时 Actor、RenderTarget 和有限观察回调，结束后精确释放，
重新加载最初干净的关卡。仅自有预览关卡可丢弃；不清除任何 dirty 标志。
"""
import hashlib
import json
import math
import os
from pathlib import Path
from statistics import median
import time

import unreal


ROOT = Path(unreal.Paths.project_dir()).resolve()
BASE = "/Game/Characters/Player/Pyrios/"
MESH = BASE + "Avatar_Male_Size03_Pyrois_Model"
SKELETON = MESH + "_Skeleton"
CLIPS = {
    "idle": BASE + "Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Idle_Loop",
    "front": BASE + "Animation/Avatar_Male_Size03_Pyrois_Ani_Evade_Front_01",
    "back": BASE + "Animation/Avatar_Male_Size03_Pyrois_Ani_Evade_Back_01",
}
ORIGINAL_MAP = "/Game/Map/L_Movement_Test.L_Movement_Test"
MAP_FILE = ROOT / "Content/Map/L_Movement_Test.umap"
PROTECTED = (
    "Config/DefaultEditor.ini",
    "Content/AI/Boss/Test/BB_Boss_Test.uasset",
    "Content/AI/Boss/Test/BT_Boss_Test.uasset",
    "Content/BP/Character/Player/BP_PC_Pyrios.uasset",
    "Content/Characters/Shared/Abilities/GA_Dodge.uasset",
    "Content/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo.uasset",
    "Saved/Autosaves/Game/Characters/Shared/Abilities/GA_Dodge_Auto2.uasset",
)


def emit(stage, **values):
    unreal.log("PYRIOS_EVADE_POSE " + json.dumps(dict(stage=stage, **values), ensure_ascii=False))


def dirty():
    library = unreal.EditorLoadingAndSavingUtils
    return sorted(p.get_path_name() for p in
                  list(library.get_dirty_content_packages()) + list(library.get_dirty_map_packages()))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def xyz(vector):
    return [vector.x, vector.y, vector.z]


def camera_values(camera):
    location, rotation = camera
    return xyz(location) + [rotation.pitch, rotation.yaw, rotation.roll]


class PoseObservation:
    """只拥有本进程预览资源和有限读回，不管理任何生产动作状态。"""

    def __init__(self):
        self.callback = self.target = self.preview_world = None
        self.owned_actors = []
        self.finished = False
        self.started = time.monotonic()
        self.protected_files = []
        self.receipt = dict(pid=os.getpid(), success=False, errors=[], captures=[],
                            saved_assets=False, pie=False, world_motion_proof=False,
                            visual_review="pending", animation_evaluation="native Editor ticks after SetPosition(false)")

    def start(self):
        requested_output = Path(os.environ["PYRIOS_EVADE_POSE_OUT"])
        if not requested_output.is_absolute():
            raise RuntimeError("输出目录必须是绝对路径")
        self.output = requested_output.resolve()
        saved = Path(unreal.Paths.project_saved_dir()).resolve()
        if not self.output.is_relative_to(saved) or self.output.exists():
            raise RuntimeError("输出须为 Saved 下未存在的绝对目录：" + str(self.output))
        self.output.mkdir(parents=True, exist_ok=False)
        self.actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        self.editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        initial = self.editor.get_editor_world()
        if not initial or initial.get_path_name() != ORIGINAL_MAP or self.editor.get_game_world():
            raise RuntimeError("要求独立、非 PIE 的原 L_Movement_Test Editor")
        self.receipt["dirty_before"] = dirty()
        if self.receipt["dirty_before"]:
            raise RuntimeError("原包已 dirty，拒绝切换环境：" + repr(self.receipt["dirty_before"]))
        self.original_camera = self.editor.get_level_viewport_camera_info()
        if self.original_camera is None:
            raise RuntimeError("无法读取原 Editor 视口相机")
        self.receipt["camera_before"] = camera_values(self.original_camera)
        self.original_selection = [a.get_path_name() for a in self.actors.get_selected_level_actors()]
        self.original_actors = sorted(a.get_path_name() for a in self.actors.get_all_level_actors())
        files = [ROOT / path for path in PROTECTED] + [MAP_FILE]
        files += [ROOT / ("Content/" + package.removeprefix("/Game/") + ".uasset")
                  for package in [MESH, SKELETON] + list(CLIPS.values())]
        files += list((ROOT / "Content/Characters/Player/Pyrios/Materials").rglob("*.uasset"))
        self.protected_files = sorted(set(files))
        self.receipt["protected_before"] = {str(path): sha(path) for path in self.protected_files}
        self.mesh = unreal.EditorAssetLibrary.load_asset(MESH)
        if not isinstance(self.mesh, unreal.SkeletalMesh):
            raise RuntimeError("原 SkeletalMesh 无效：" + MESH)
        skeleton = self.mesh.get_editor_property("skeleton")
        if skeleton is None or skeleton.get_path_name().split(".")[0] != SKELETON:
            raise RuntimeError("原 Mesh / Skeleton 身份不符")
        self.clips = {key: unreal.EditorAssetLibrary.load_asset(path) for key, path in CLIPS.items()}
        for key, clip in self.clips.items():
            if not isinstance(clip, unreal.AnimSequence) or clip.get_editor_property("skeleton") != skeleton:
                raise RuntimeError("原 AnimSequence / Skeleton 无效：" + CLIPS[key])
            if clip.get_play_length() <= 0:
                raise RuntimeError("原 AnimSequence 无有效时长：" + CLIPS[key])
        self.original_materials = self.materials()
        if dirty():
            raise RuntimeError("读取原资产后出现 dirty 包：" + repr(dirty()))
        # EditorActorSubsystem 经 ActorFactory 放置和 EditorDestroyActor(true)；
        # transient Actor 仍可能 Modify Level，因此所有放置只进入新建 /Temp 关卡。
        self.preview_world = unreal.EditorLoadingAndSavingUtils.new_blank_map(False)
        if not self.preview_world or self.editor.get_editor_world() != self.preview_world:
            raise RuntimeError("自有预览 World 创建失败")
        self.preview_package = self.preview_world.get_path_name().split(".")[0]
        if not self.preview_package.startswith("/Temp/"):
            raise RuntimeError("预览 World 不是独立 /Temp 包：" + self.preview_package)
        self.preview_initial_actors = sorted(a.get_path_name() for a in self.actors.get_all_level_actors())
        self.receipt.update(preview_world=self.preview_world.get_path_name(), materials=self.original_materials,
                            durations={key: clip.get_play_length() for key, clip in self.clips.items()})
        actor = self.spawn(unreal.SkeletalMeshActor, unreal.Vector(), unreal.Rotator())
        self.component = actor.get_editor_property("skeletal_mesh_component")
        self.component.set_skeletal_mesh_asset(self.mesh)
        self.component.set_animation_mode(unreal.AnimationMode.ANIMATION_SINGLE_NODE)
        self.component.set_update_animation_in_editor(True)
        self.component.set_editor_property("visibility_based_anim_tick_option",
                                           unreal.VisibilityBasedAnimTickOption.ALWAYS_TICK_POSE_AND_REFRESH_BONES)
        self.component.set_editor_property("enable_update_rate_optimizations", False)
        self.component.set_forced_lod(1)
        for rotation, intensity in ((unreal.Rotator(-35.0, -100.0, 0.0), 5.0),
                                    (unreal.Rotator(-25.0, 45.0, 0.0), 2.0)):
            light = self.spawn(unreal.DirectionalLight, unreal.Vector(), rotation).light_component
            light.set_mobility(unreal.ComponentMobility.MOVABLE)
            light.set_intensity(intensity)
        self.target = unreal.RenderingLibrary.create_render_target2d(
            self.preview_world, 900, 900, unreal.TextureRenderTargetFormat.RTF_RGBA8_SRGB)
        if self.target is None:
            raise RuntimeError("原生 RenderTarget 创建失败")
        self.capture_actor = self.spawn(unreal.SceneCapture2D, unreal.Vector(), unreal.Rotator())
        self.capture = self.capture_actor.get_editor_property("capture_component2d")
        for name, value in (("texture_target", self.target), ("capture_every_frame", False),
                            ("capture_on_movement", False), ("fov_angle", 40.0),
                            ("capture_source", unreal.SceneCaptureSource.SCS_FINAL_COLOR_LDR),
                            ("primitive_render_mode", unreal.SceneCapturePrimitiveRenderMode.PRM_USE_SHOW_ONLY_LIST)):
            self.capture.set_editor_property(name, value)
        self.capture.show_only_actor_components(actor)
        settings = self.capture.get_editor_property("post_process_settings")
        for name, value in (("auto_exposure_method", unreal.AutoExposureMethod.AEM_MANUAL),
                            ("auto_exposure_bias", 0.0), ("auto_exposure_apply_physical_camera_exposure", False)):
            settings.set_editor_property("override_" + name, True)
            settings.set_editor_property(name, value)
        self.capture.set_editor_property("post_process_settings", settings)
        self.bones = [self.component.get_bone_name(index) for index in range(self.component.get_num_bones())]
        if not self.bones or any(self.component.get_bone_index(name) < 0 for name in self.bones):
            raise RuntimeError("原 Mesh 骨名称读回无效")
        self.receipt["bone_names"] = [str(name) for name in self.bones]
        self.steps = self.observe()
        self.callback = unreal.register_slate_post_tick_callback(self.tick)
        if self.callback is None:
            raise RuntimeError("原生 Editor 帧观察注册失败")
        emit("started", preview_world=self.preview_world.get_path_name(), protected_count=len(self.protected_files),
             cases="Idle 对照、Front 0–3.05、Back 0–2.6、两个原末帧", output=str(self.output))

    def materials(self):
        result = []
        for item in self.mesh.get_editor_property("materials"):
            if item.material_interface is None:
                raise RuntimeError("原 Mesh 存在空材质槽：" + str(item.material_slot_name))
            result.append(dict(slot=str(item.material_slot_name), material=item.material_interface.get_path_name()))
        return result

    def spawn(self, actor_class, location, rotation):
        actor = self.actors.spawn_actor_from_class(actor_class, location, rotation, transient=True)
        if actor is None:
            raise RuntimeError("临时 Actor 创建失败：" + actor_class.__name__)
        self.owned_actors.append(actor)
        return actor

    def set_pose(self, key, seconds):
        self.component.set_animation(self.clips[key])
        self.component.set_play_rate(0.0)
        self.component.stop()
        self.component.set_position(seconds, False)

    def pose(self):
        result = []
        for name in self.bones:
            transform = self.component.get_bone_transform(name, unreal.RelativeTransformSpace.RTS_COMPONENT)
            p, q, s = transform.translation, transform.rotation, transform.scale3d
            values = xyz(p) + [q.x, q.y, q.z, q.w] + xyz(s)
            if not all(math.isfinite(value) for value in values):
                raise RuntimeError("非有限原生骨变换：" + str(name))
            result.append(values)
        return result

    def observe(self):
        self.set_pose("idle", 0.0)
        for _ in range(30):
            yield
        idle = self.pose()
        bounds_origin, _, radius = unreal.SystemLibrary.get_component_bounds(self.component)
        idle_median = [median(row[index] for row in idle) for index in range(3)]
        idle_mid_z = (min(row[2] for row in idle) + max(row[2] for row in idle)) * 0.5
        self.center_offset = [0.0, 0.0, idle_mid_z - idle_median[2]]
        self.camera_offset = unreal.Vector(210.0, 380.0, 20.0)
        self.receipt["framing"] = dict(method="骨位置中位数；高度对齐 Idle 全骨范围中点，固定距离和朝向",
                                        idle_bounds_origin=xyz(bounds_origin), idle_bounds_radius=radius,
                                        center_offset=self.center_offset, camera_offset=xyz(self.camera_offset))
        samples = [("idle", 0.0, "idle_zero"), ("idle", 0.5, "idle_half")]
        for key, end, candidate in (("front", 3.05, 2.75), ("back", 2.6, 2.283333302)):
            times = sorted(set([round(index * 0.1, 6) for index in range(int(end * 10) + 1)]
                               + [end, candidate]))
            samples += [(key, seconds, "candidate" if seconds == candidate else "sample") for seconds in times]
            samples.append((key, self.clips[key].get_play_length(), "original_last"))
        samples.append(("idle", 0.0, "idle_repeat"))
        for index, (key, seconds, purpose) in enumerate(samples):
            self.set_pose(key, seconds)
            for _ in range(3):
                yield
            if abs(self.component.get_position() - seconds) > 0.00001:
                raise RuntimeError("原生 SingleNode 时间未保持：" + key + " " + str(seconds))
            transforms = self.pose()
            center = unreal.Vector(*[median(row[axis] for row in transforms) + self.center_offset[axis]
                                     for axis in range(3)])
            location = center + self.camera_offset
            self.capture_actor.set_actor_location_and_rotation(
                location, unreal.MathLibrary.find_look_at_rotation(location, center), False, False)
            yield
            self.capture.capture_scene()
            for _ in range(2):
                yield
            name = f"{index:03d}_{key}_{seconds:.6f}_{purpose}.png"
            unreal.RenderingLibrary.export_render_target(self.preview_world, self.target, str(self.output), name)
            path = self.output / name
            if not path.is_file() or path.stat().st_size < 32:
                raise RuntimeError("原生 PNG 未生成：" + str(path))
            self.receipt["captures"].append(dict(sequence=CLIPS[key], case=key, seconds=seconds, purpose=purpose,
                                                  image=str(path), camera_center=xyz(center), bones=transforms,
                                                  pose_sha256=hashlib.sha256(json.dumps(transforms).encode()).hexdigest()))
            emit("captured", case=key, seconds=seconds, purpose=purpose, image=str(path))

    def tick(self, _delta):
        if self.finished:
            return
        try:
            if time.monotonic() - self.started > 240.0:
                raise RuntimeError("只读姿态观察超过 240 秒")
            if self.editor.get_editor_world() != self.preview_world or self.editor.get_game_world():
                raise RuntimeError("自有预览 World / 非 PIE 身份改变")
            next(self.steps)
        except StopIteration:
            self.finish(None)
        except Exception as error:
            self.finish(error)

    def finish(self, error):
        if self.finished:
            return
        self.finished = True
        errors = self.receipt["errors"]
        if error is not None:
            errors.append(str(error))
        if self.callback is not None:
            try:
                unreal.unregister_slate_post_tick_callback(self.callback)
                self.callback = None
            except Exception as cleanup_error:
                errors.append("注销观察：" + str(cleanup_error))
        for actor in reversed(self.owned_actors):
            try:
                if not self.actors.destroy_actor(actor):
                    errors.append("自有 Actor 删除失败：" + actor.get_path_name())
            except Exception as cleanup_error:
                errors.append("删除自有 Actor：" + str(cleanup_error))
        self.owned_actors.clear()
        if self.target is not None:
            try:
                unreal.RenderingLibrary.release_render_target2d(self.target)
                self.target = None
            except Exception as cleanup_error:
                errors.append("释放 RenderTarget：" + str(cleanup_error))
        try:
            if self.preview_world is not None:
                self.receipt["preview_dirty_after_cleanup"] = dirty()
                if any(package != self.preview_package for package in dirty()):
                    raise RuntimeError("出现非自有预览 dirty 包，保留 Editor：" + repr(dirty()))
                if sorted(a.get_path_name() for a in self.actors.get_all_level_actors()) != self.preview_initial_actors:
                    raise RuntimeError("自有预览 Actor 集合未恢复")
                restored = unreal.EditorLoadingAndSavingUtils.load_map(str(MAP_FILE))
                if restored is None or restored.get_path_name() != ORIGINAL_MAP:
                    raise RuntimeError("原干净关卡重新加载失败")
                self.preview_world = None
                self.editor.set_level_viewport_camera_info(*self.original_camera)
                current = {a.get_path_name(): a for a in self.actors.get_all_level_actors()}
                if sorted(current) != self.original_actors:
                    raise RuntimeError("重新加载后原 Actor 集合改变")
                self.actors.set_selected_level_actors([current[path] for path in self.original_selection])
                restored_camera = self.editor.get_level_viewport_camera_info()
                self.receipt["camera_after"] = camera_values(restored_camera) if restored_camera else None
                # Python Struct 的 str 含实例内存地址；保护必须比较原六个数值。
                if self.receipt["camera_after"] != self.receipt["camera_before"]:
                    raise RuntimeError("原视口相机未恢复")
                if sorted(a.get_path_name() for a in self.actors.get_selected_level_actors()) != sorted(self.original_selection):
                    raise RuntimeError("原选择未恢复")
                if self.materials() != self.original_materials:
                    raise RuntimeError("原 Mesh 材质引用改变")
                if self.mesh.get_editor_property("skeleton").get_path_name().split(".")[0] != SKELETON:
                    raise RuntimeError("原 Mesh / Skeleton 引用改变")
        except Exception as cleanup_error:
            errors.append("清理：" + str(cleanup_error))
        self.receipt["dirty_after"] = dirty()
        if self.receipt["dirty_after"]:
            errors.append("退出前仍有 dirty 包：" + repr(self.receipt["dirty_after"]))
        if self.protected_files:
            try:
                self.receipt["protected_after"] = {str(path): sha(path) for path in self.protected_files}
                self.receipt["changed_files"] = [path for path, value in self.receipt["protected_before"].items()
                                                  if self.receipt["protected_after"][path] != value]
                if self.receipt["changed_files"]:
                    errors.append("保护文件发生变化：" + repr(self.receipt["changed_files"]))
            except Exception as protection_error:
                errors.append("磁盘保护：" + str(protection_error))
        self.receipt["success"] = not errors and bool(self.receipt["captures"])
        if hasattr(self, "output") and self.output.is_dir():
            with (self.output / "readback.json").open("x", encoding="utf-8") as stream:
                json.dump(self.receipt, stream, ensure_ascii=False, indent=2)
        emit("completed" if self.receipt["success"] else "failed", errors=errors,
             captures=len(self.receipt["captures"]), dirty_after=self.receipt["dirty_after"])
        # 自有预览已释放且原关卡干净才正常退出；未知 dirty 不自动丢弃。
        if self.preview_world is None and not self.receipt["dirty_after"]:
            unreal.SystemLibrary.quit_editor()


if globals().get("_pyrios_evade_pose_observation") is not None:
    raise RuntimeError("拒绝在同一 Editor 再注册姿态观察器")
_pyrios_evade_pose_observation = PoseObservation()
try:
    _pyrios_evade_pose_observation.start()
except Exception as _start_error:
    _pyrios_evade_pose_observation.finish(_start_error)
