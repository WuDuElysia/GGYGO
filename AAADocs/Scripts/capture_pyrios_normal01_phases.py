"""观察原 Normal01 首击的三个自然 Draw，相位由原 Automation 观察器发布。

在 Root 的干净 Editor 中、运行 ProductionNativeNormal01 前执行本入口。
PYRIOS_FX_PREFIX 必须是 Saved 下未使用的绝对文件名前缀。本脚本不预热材质、
不发输入、不启动或结束 PIE，不改机位、播放速度或资产。每张图只认发布它的
原 Draw；未自然出现的相位保留为 uncovered。最终 JSON 供集中宿主核收。
"""
import json
import math
import os
from pathlib import Path
import time

import unreal


PHASES = ("birth", "middle", "fade")
LAYERS = ("M00_root_Trail_rot_HighLight", "M00_root_Trail_rot_Shining",
          "M00_root_Trail_rot_light_edge")
SYSTEM = ("/Game/Characters/Player/Pyrios/FX/Skill/"
          "NS_Pyrios_Normal01_MainComposition_2a7c90937cab."
          "NS_Pyrios_Normal01_MainComposition_2a7c90937cab")
IDENTITY = ("world_path", "world_object_id", "viewport_identity",
            "game_viewport_client_object_id", "montage_task", "montage_instance_id",
            "fx_task", "component", "system", "niagara_id")
NATIVE_FIELDS = ("world_path", "world_object_id", "viewport_identity",
                 "game_viewport_client_object_id", "request_frame", "render_callback_frame",
                 "readback_complete_frame", "output_file_path", "output_file_size_bytes",
                 "file_write_complete", "file_readback_verified", "resources_released", "error")


def emit(stage, **values):
    unreal.log("PYRIOS_FX_CAPTURE " + json.dumps(dict(stage=stage, **values), ensure_ascii=False))


def dirty_packages():
    lib = unreal.EditorLoadingAndSavingUtils
    return sorted(p.get_path_name() for p in
                  list(lib.get_dirty_content_packages()) + list(lib.get_dirty_map_packages()))


def editor_state(editor, actors):
    p, r = editor.get_level_viewport_camera_info()
    return ((p.x, p.y, p.z, r.pitch, r.yaw, r.roll),
            sorted(a.get_path_name() for a in actors.get_selected_level_actors()),
            sorted(a.get_path_name() for a in actors.get_all_level_actors()))


def finite_vector(value, count):
    return (isinstance(value, list) and len(value) == count
            and all(isinstance(x, (int, float)) and math.isfinite(x) for x in value))


class ProductionPhaseCapture:
    def __init__(self):
        self.finished = self.observation_done = False
        self.observation_error = None
        self.callback = self.draw_callback = self.draw_probe = self.world = None
        self.original_state = self.identity = None
        self.started = time.monotonic()
        self.cleanup_errors = []
        self.tasks = {}
        self.records = {phase: dict(coverage="uncovered", reason="No matching natural Draw",
                                    request=None, native=None) for phase in PHASES}

    def start(self):
        self.editor = unreal.get_editor_subsystem(unreal.UnrealEditorSubsystem)
        self.actors = unreal.get_editor_subsystem(unreal.EditorActorSubsystem)
        editor_world = self.editor.get_editor_world()
        if not editor_world or editor_world.get_path_name() != "/Game/Map/L_Movement_Test.L_Movement_Test":
            raise RuntimeError("要求原 L_Movement_Test Editor World")
        if self.editor.get_game_world() is not None or dirty_packages():
            raise RuntimeError("观察器须在无 PIE、无脏包的制作后窗口安装")
        self.original_state = editor_state(self.editor, self.actors)
        prefix = Path(os.environ["PYRIOS_FX_PREFIX"])
        if not prefix.is_absolute():
            raise RuntimeError("PYRIOS_FX_PREFIX 必须是绝对路径")
        self.prefix = prefix.resolve()
        if not self.prefix.is_relative_to(Path(unreal.Paths.project_saved_dir()).resolve()):
            raise RuntimeError("观察输出必须位于本工程 Saved")
        if any(self.prefix.parent.glob(self.prefix.name + "*")):
            raise RuntimeError("拒绝覆盖既有观察文件")
        self.prefix.parent.mkdir(parents=True, exist_ok=True)
        self.draw_probe = unreal.get_default_object(unreal.GGYGOPlayerComboFXDrawTestBridge.static_class())
        self.draw_callback = self.on_draw
        self.draw_probe.on_bright_draw.add_callable(self.draw_callback)
        self.callback = unreal.register_slate_post_tick_callback(self.tick)
        if self.callback is None:
            raise RuntimeError("未注册原生观察回调")
        emit("production_phase_observer_started", system=SYSTEM, phases=list(PHASES),
             saved_assets=False, manual_tick=False, simulation_advance=False, material_warmup=False)

    def on_draw(self, world, sample_json):
        if self.observation_done or self.observation_error is not None:
            return
        try:
            sample = json.loads(sample_json)
            phase = sample["sample_phase"]
            if phase not in PHASES or sample["sample_index"] != PHASES.index(phase):
                raise RuntimeError("未知自然相位或相位索引不匹配")
            record = self.records[phase]
            if record["request"] is not None:
                raise RuntimeError("同一相位重复发布，拒绝替换原样本")
            frame = int(sample["draw_frame"])
            if (world != self.editor.get_game_world() or (self.world is not None and self.world != world)
                    or sample["world_path"] != world.get_path_name()
                    or frame != unreal.SystemLibrary.get_frame_count()
                    or sample["system"] != SYSTEM or sample["montage_section"] != "Main"
                    or sample["montage_instance_id"] < 0 or sample["niagara_tick"] <= 0):
                raise RuntimeError("样本不属于原生产 Main 的当前 Draw")
            identity = tuple(sample[key] for key in IDENTITY)
            if any(not sample[key] for key in IDENTITY if key != "montage_instance_id"):
                raise RuntimeError("样本缺原生产对象身份")
            if self.identity is not None and self.identity != identity:
                raise RuntimeError("相位来自不同的原生产实例")
            layers = sample["layers"]
            if [layer["name"] for layer in layers] != list(LAYERS):
                raise RuntimeError("样本未包含约定三层及原顺序")
            missing_parameters = []
            for layer in layers:
                particles = layer.get("particles", [])
                if (layer["coverage"] != "PublishedCPU" or not layer["emitter_id"]
                        or layer.get("particle_count", 0) <= 0 or len(particles) != layer["particle_count"]):
                    missing_parameters.append(dict(layer=layer["name"], attribute="PublishedCPU",
                                                   reason=layer.get("reason", "MissingParticles")))
                    continue
                for particle in particles:
                    for name in ("color_rgba", "dynamic_material_parameter",
                                 "dynamic_material_parameter1", "dynamic_material_parameter2"):
                        if not finite_vector(particle.get(name), 4):
                            missing_parameters.append(dict(layer=layer["name"],
                                                           particle=particle["index"], attribute=name))
            if phase != "birth":
                lower, upper = (0.25, 0.65) if phase == "middle" else (0.82, 1.0)
                if (any(not layer.get("particles") for layer in layers[:2])
                        or not all(lower <= p["normalized_age"] < upper
                                   for layer in layers[:2] for p in layer["particles"])):
                    raise RuntimeError("亮层真实年龄不在所发布的自然相位内")
            frames = [int(r["request"]["draw_frame"]) for r in self.records.values() if r["request"]]
            if frames and frame <= max(frames):
                raise RuntimeError("相位 Draw 未自然前进")
            self.world, self.identity = world, identity
            path = self.prefix.parent / (self.prefix.name + "_normal01_" + phase + ".png")
            record.update(request=sample, output_path=str(path), reason="Awaiting the original Draw",
                          parameter_coverage="uncovered" if missing_parameters else "PublishedCPU",
                          missing_parameters=missing_parameters)
            task = unreal.GGYGOViewportReadbackLibrary.begin_game_viewport_readback_to_file(world, str(path))
            if task is None:
                raise RuntimeError("原游戏视口读回入口未返回资源")
            self.tasks[phase] = dict(task=task, releasing=False)
            emit("production_phase_requested", phase=phase, output_path=str(path), sample=sample)
        except Exception as error:
            self.finish(str(error))

    def release(self, phase):
        item = self.tasks[phase]
        if not item["releasing"]:
            item["task"].release()
            item["releasing"] = True

    def poll(self):
        status = unreal.GGYGOViewportReadbackStatus
        for phase in list(self.tasks):
            record = self.records[phase]
            result = self.tasks[phase]["task"].read_result()
            record["native"] = {name: getattr(result, name) for name in NATIVE_FIELDS}
            record["native"]["status"] = str(result.status)
            if result.status in (status.FAILED, status.CANCELLED):
                record.update(coverage="failed", reason=result.error)
                self.release(phase)
            if result.status not in (status.COMPLETE, status.FAILED, status.CANCELLED):
                continue
            if not result.resources_released:
                continue
            self.release(phase)
            del self.tasks[phase]
            if result.status == status.COMPLETE and record["coverage"] != "failed":
                sample = record["request"]
                requested, drawn, complete = map(int, (result.request_frame, result.render_callback_frame,
                                                      result.readback_complete_frame))
                matches = (0 < int(sample["draw_frame"]) == requested == drawn <= complete
                           and all(getattr(result, key) == sample[key] for key in
                                   ("world_path", "world_object_id", "viewport_identity", "game_viewport_client_object_id"))
                           and Path(result.output_file_path).resolve() == Path(record["output_path"])
                           and result.file_write_complete and result.file_readback_verified
                           and result.output_file_size_bytes > 0)
                if matches:
                    record.update(coverage="captured_same_draw", reason="Visual review pending")
                else:
                    record.update(coverage="failed", reason="PNG or native Draw identity does not match")
            emit("production_phase_readback", phase=phase, viewport=record)

    def finish(self, error=None):
        if self.observation_done:
            return
        self.observation_done = True
        self.observation_error = error
        if self.draw_callback is not None:
            self.draw_probe.on_bright_draw.remove_callable(self.draw_callback)
            self.draw_callback = self.draw_probe = None
        if error is not None:
            for phase in list(self.tasks):
                self.records[phase].update(coverage="failed", reason=error)
                self.release(phase)

    def tick(self, _delta):
        if self.finished:
            return
        try:
            world = self.editor.get_game_world()
            if not self.observation_done:
                if self.world is None and world is not None:
                    self.world = world
                if self.world is not None and world != self.world:
                    self.finish("原生产 World 被替换" if world is not None else None)
                elif all(record["request"] is not None for record in self.records.values()):
                    self.finish()
            expired = time.monotonic() - self.started > 180.0
            if expired and not self.observation_done:
                self.finish("原生产观察超过 180 秒边界")
            if expired:
                for phase in list(self.tasks):
                    self.records[phase].update(coverage="failed", reason="原视口资源在观察边界内尚未归还")
                    self.release(phase)
            self.poll()
            if self.observation_done and not self.tasks and (world is None or expired):
                self.finalize(world is None)
        except Exception as error:
            self.cleanup_errors.append(str(error))
            self.finish(str(error))

    def finalize(self, protection_available):
        self.finished = True
        if self.callback is not None:
            unreal.unregister_slate_post_tick_callback(self.callback)
            self.callback = None
        if not protection_available:
            self.cleanup_errors.append("原 PIE 尚未退出，不能核收 Editor 保护")
        elif self.original_state != editor_state(self.editor, self.actors) or dirty_packages():
            self.cleanup_errors.append("原 Editor 机位、选择、Actor 集合或脏包发生变化")
        missed = [phase for phase in PHASES if self.records[phase]["coverage"] != "captured_same_draw"
                  or self.records[phase].get("parameter_coverage") != "PublishedCPU"]
        result = dict(schema="GGYGO.Normal01NaturalPhaseCapture/v1", samples=self.records,
                      missed=missed, error=self.observation_error, cleanup_errors=self.cleanup_errors,
                      editor_protection="failed" if self.cleanup_errors else "verified_after_original_PIE",
                      saved_assets=False, material_warmup=False, visual_review="pending")
        # 不覆盖原报告；只有实际读回与归还后写机器消费的证据。
        path = self.prefix.parent / (self.prefix.name + "_phases.json")
        with path.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
        emit("production_phase_capture_finished", report=str(path), **result)


if globals().get("_pyrios_fx_capture") is not None:
    raise RuntimeError("当前 Python 上下文已有特效观察器")
_pyrios_fx_capture = ProductionPhaseCapture()
try:
    _pyrios_fx_capture.start()
except Exception as error:
    _pyrios_fx_capture.finish(str(error))
    raise
