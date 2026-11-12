"""在独立 D3D12 Editor 中观察生产普攻与 Special／ExSpecial。

用 -ExecCmds="py ..." 或本进程控制台安装 Slate 观察。全部动作走现有 InputKey。
技能仅在独立 Editor 内存中替换 AbilitySet 的攻击授予行，保留其原输入 Tag，
由生产 Pawn 初始化授予；PIE 结束后恢复原行，不保存资产或修改生产输入。
GGYGO_ACTION_FX_OUT 指定输出；GGYGO_ACTION_FX_SCENARIOS 默认 Combo,Special,ExSpecial。
外部 control.py 消费 pie_request 文件，经本进程 MCP 启动 Floating PIE。
"""
import json
import os
import time
import traceback
from pathlib import Path

import unreal as ue

OUT = Path(os.environ["GGYGO_ACTION_FX_OUT"])
ROOT = "/Game/Characters/Player/Pyrios"
NAMES = {"Combo": "GA_Pyrios_Attack_Combo", "Special": "GA_Pyrios_Attack_Special_01",
         "ExSpecial": "GA_Pyrios_Attack_ExSpecial_01"}
CAPTURE_TIMES = tuple(float(value) for value in os.environ.get("GGYGO_ACTION_FX_CAPTURE_TIMES",
    "0.04,0.10,0.16,0.24,0.36,0.5,0.7,0.95,1.2,1.5,1.9,2.4").split(","))


def path(obj):
    return obj.get_path_name() if obj else None


def save(filename, data):
    filename.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")


class Run:
    def __init__(self):
        OUT.mkdir(parents=True, exist_ok=True)
        self.queue = os.environ.get("GGYGO_ACTION_FX_SCENARIOS", "Combo,Special,ExSpecial").replace(",", " ").split()
        if any(s not in NAMES for s in self.queue):
            raise ValueError("未知动作场景")
        self.last_combo_step = int(os.environ.get("GGYGO_ACTION_FX_LAST_COMBO_STEP", "2"))
        if self.last_combo_step not in (1, 2):
            raise ValueError("普攻观察只接受第二或第三段自然结束")
        self.cancel_seconds = float(os.environ.get("GGYGO_ACTION_FX_CANCEL_SECONDS", "-1"))
        self.les = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.ues = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        self.state, self.s, self.results = "boot", None, {}
        self.fixture = None
        self.in_tick = False
        self.deadline = time.monotonic() + 20
        self.handle = ue.register_slate_post_tick_callback(self.tick)
        ue.log("[ActionFX] 已注册动作实拍观察")

    def tick(self, _dt):
        # 资产加载／PostEdit 会泵送 Slate；同一次观察不能在尚未返栈时推进第二次。
        if self.in_tick:
            return
        self.in_tick = True
        try:
            self.step()
        except Exception:
            message = traceback.format_exc()
            ue.log_error("[ActionFX] " + message)
            if self.s and self.state not in ("ending", "draining"):
                self.s["error"] = message
                self.finish()
            else:
                self.quit(message)
        finally:
            self.in_tick = False

    def step(self):
        if self.state == "boot":
            if time.monotonic() < self.deadline or ue.AssetRegistryHelpers.get_asset_registry().is_loading_assets():
                return
            cmd = ue.SystemLibrary.get_command_line().lower()
            if "-nullrhi" in cmd or "-nosound" in cmd:
                raise RuntimeError("动作实拍需要真实 RHI 和音频")
            for command in ("au.DisableAppVolume 1", "t.MaxFPS 60", "Slate.bAllowThrottling 0"):
                ue.SystemLibrary.execute_console_command(None, command)
            if ue.SystemLibrary.get_console_variable_int_value("Slate.bAllowThrottling") != 0:
                raise RuntimeError("观察窗口的 Slate 限流配置未生效")
            self.next_scene()
        elif self.state == "starting":
            world = self.ues.get_game_world()
            if time.monotonic() > self.deadline:
                raise RuntimeError("PIE／角色准备超过 120 秒")
            if world:
                self.assemble(world)
        elif self.state == "running":
            self.observe()
        elif self.state == "draining":
            self.poll_images()
            if not self.s["pending"] or time.monotonic() > self.deadline:
                for item in self.s["pending"]:
                    item["status"] = "timeout"
                    item.pop("task").release()
                self.s["pending"].clear()
                if self.s.get("encounter"):
                    self.s["encounter"].destroy_actor()
                self.les.editor_request_end_play()
                self.state = "ending"
        elif self.state == "ending" and self.ues.get_game_world() is None:
            self.restore_fixture()
            self.write_scene()
            self.next_scene()

    def next_scene(self):
        if not self.queue:
            self.quit()
            return
        name = self.queue.pop(0)
        folder = OUT / name
        folder.mkdir(parents=True, exist_ok=True)
        self.s = dict(name=name, folder=folder, frames=[], images=[], pending=[], hits=[], events=[],
                      observers=[], observed_steps=set(), captures=set(), requested=set(), key_down=False, sections={}, error=None,
                      ability=None, ready_frames=0, audio={}, niagara={}, sample_time=-1)
        self.prepare_fixture(name)
        save(OUT / ("pie_request_" + name + ".json"), {"scenario": name})
        self.deadline, self.state = time.monotonic() + 120, "starting"
        ue.log("[ActionFX] 请求 PIE：" + name)

    def prepare_fixture(self, name):
        if name == "Combo":
            return
        if self.ues.get_game_world() or self.fixture:
            raise RuntimeError("临时技能授予必须在两个 PIE 之间配置")
        asset = ue.load_asset(ROOT + "/DA/DA_AbilitySet_Pyrios")
        original = [row.copy() for row in asset.get_editor_property("granted_gameplay_abilities")]
        combo = ue.load_asset(ROOT + "/Abilities/" + NAMES["Combo"]).generated_class()
        matches = [i for i, row in enumerate(original) if row.get_editor_property("ability") == combo]
        if len(matches) != 1:
            raise RuntimeError("AbilitySet 缺少唯一普攻授予行")
        rows = [row.copy() for row in original]
        cls = ue.load_asset(ROOT + "/Abilities/" + NAMES[name]).generated_class()
        previous = original[matches[0]]
        grant = ue.GGYGOAbilitySet_GameplayAbility()
        declaration = ('(Ability="' + cls.get_path_name() + '",AbilityLevel='
                       + str(previous.get_editor_property("ability_level")) + ',InputTag='
                       + previous.get_editor_property("input_tag").export_text() + ')')
        if not grant.import_text(declaration):
            raise RuntimeError("原授予 Struct 的临时技能行构造失败")
        rows[matches[0]] = grant
        self.fixture = (asset, original)
        asset.set_editor_property("granted_gameplay_abilities", rows)
        self.s["events"].append({"test_grant": path(cls), "entry": "existing InputKey to Process/ASC",
                                  "saved": False, "input_tag_preserved": True})

    def restore_fixture(self):
        if not self.fixture:
            return
        asset, original = self.fixture
        asset.set_editor_property("granted_gameplay_abilities", original)
        restored = asset.get_editor_property("granted_gameplay_abilities")
        if len(restored) != len(original) or any(
                a.get_editor_property("ability") != b.get_editor_property("ability")
                or a.get_editor_property("ability_level") != b.get_editor_property("ability_level")
                or a.get_editor_property("input_tag").export_text() != b.get_editor_property("input_tag").export_text()
                for a, b in zip(original, restored)):
            raise RuntimeError("临时授予配置未恢复")
        self.fixture = None
        if self.s:
            self.s["events"].append({"test_grant_configuration_restored": True, "saved": False})

    def assemble(self, world):
        s = self.s
        if not world.get_path_name().startswith("/Game/Map/UEDPIE_0_L_Movement_Test"):
            raise RuntimeError("不是 L_Movement_Test PIE")
        pc = ue.GameplayStatics.get_player_controller(world, 0)
        pawn = ue.GameplayStatics.get_player_pawn(world, 0) if pc else None
        if not pawn:
            return
        if pawn.get_class().get_name() != "BP_PC_Pyrios_C":
            raise RuntimeError("当前角色不是 Pyrios")
        # 观察从生产 Pawn 自身的 Ready 开始，不创建额外准备请求或补发被拒按键。
        extension = pawn.get_component_by_class(ue.GGYGOPawnExtensionComponent)
        requests = [request for request in ue.ObjectIterator(ue.GGYGONiagaraMaterialPreparation)
                    if request.get_outer() == extension]
        if not requests:
            return
        if len(requests) != 1:
            raise RuntimeError("生产 Pawn 的资源准备请求不唯一")
        preparation = requests[0]
        state = preparation.get_state()
        ready = state == ue.GGYGONiagaraMaterialPreparationState.READY
        save(s["folder"] / "production_gate.json", {"ready": ready, "state": str(state),
             "reason": preparation.get_error(), "world_seconds": ue.GameplayStatics.get_time_seconds(world),
             "extra_preparation": False})
        if state not in (ue.GGYGONiagaraMaterialPreparationState.PENDING, ue.GGYGONiagaraMaterialPreparationState.READY):
            raise RuntimeError("生产 Pawn 资源准备失败：" + preparation.get_error())
        if not ready:
            return
        mesh = pawn.get_editor_property("mesh")
        move = pawn.get_editor_property("character_movement")
        anim = mesh.get_anim_instance()
        if not anim or move.get_movement_set() is None:
            return
        velocity = pawn.get_velocity()
        idle = move.is_moving_on_ground() and velocity.length_squared() < 1e-5 and not move.has_active_action_motion()
        s["ready_frames"] = s["ready_frames"] + 1 if idle else 0
        if s["ready_frames"] < 60:
            return
        asc = ue.AbilitySystemLibrary.get_ability_system_component(pawn)
        bp = ue.load_asset(ROOT + "/Abilities/" + NAMES[s["name"]])
        cls = bp.generated_class()
        handles = [h for h in asc.get_all_abilities()
                   if ue.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(asc, h)[0].get_class() == cls]
        if len(handles) != 1:
            raise RuntimeError("生产 ASC 缺少唯一动作 Spec：" + NAMES[s["name"]])
        steps = ue.get_default_object(cls).get_editor_property("combo_steps")
        s.update(world=world, pc=pc, pawn=pawn, mesh=mesh, move=move, anim=anim, asc=asc, cls=cls,
                 spec=handles[0], montages=[st.get_editor_property("montage") for st in steps])
        lib = ue.get_default_object(ue.load_class(None, "/Script/Engine.SubsystemBlueprintLibrary"))
        sub = lib.call_method("GetLocalPlayerSubSystemFromPlayerController",
                              args=(pc, ue.EnhancedInputLocalPlayerSubsystem.static_class()))
        lp = sub.get_outer()
        status, ipc, ipawn, pinput, comp, user, device, diagnostic = \
            ue.GGYGOPlayerInputBridgeLibrary.read_local_player_input_assembly(world, lp)
        if status != ue.GGYGOPlayerInputAssemblyStatus.READY:
            raise RuntimeError("生产输入未准备：" + str(diagnostic))
        ctx = ue.load_asset("/Game/Input/Mappings/IMC_Default")
        action = ue.load_asset("/Game/Input/Actions/IA_Attack")
        keys = [row.get_editor_property("key")
                for row in ctx.get_editor_property("default_key_mappings").get_editor_property("mappings")
                if row.get_editor_property("action") == action
                and str(row.get_editor_property("key").get_editor_property("key_name")) == "LeftMouseButton"]
        if len(keys) != 1 or pc.is_input_key_down(keys[0]):
            raise RuntimeError("攻击映射不唯一或按键已按下")
        s.update(lp=lp, pinput=pinput, input_comp=comp, device=device, key=keys[0])
        self.spawn_target()
        if os.environ.get("GGYGO_ACTION_FX_CAMERA") == "side":
            self.place_diagnostic_camera()
        fx = ue.GGYGOPlayerActionObservation.create_observation()
        result = fx.begin_fx_observation(asc, pawn, mesh, s["name"], 4096)
        if result is None:
            raise RuntimeError("FX 原生观察未能安装")
        s["fx_observer"] = fx
        ue.AudioMixerLibrary.start_recording_output(world, 120.0, None)
        s["recording"] = True
        ue.SystemLibrary.execute_console_command(world, "Trace.File " + (s["folder"] / "audio.utrace").as_posix() + " Audio,AudioMixer", pc)
        ue.SystemLibrary.execute_console_command(world, "Trace.Disable Cpu,Gpu,Log,ChaosVD", pc)
        s["trace"] = True
        s["started"] = time.monotonic()
        self.key(True)
        s["requested"].add(0)
        self.state = "running"
        ue.log("[ActionFX] 已触发：" + s["name"])

    def place_diagnostic_camera(self):
        """仅本次 PIE 的侧面观察机位，用于辨别刀光侧对镜头与真正缺层。"""
        s = self.s
        location = s["pawn"].get_actor_location()
        camera_location = location + ue.Vector(0, -900, 350)
        rotation = ue.MathLibrary.find_look_at_rotation(camera_location, location + ue.Vector(150, 0, 80))
        transform = ue.Transform()
        transform.translation, transform.rotation = camera_location, rotation.quaternion()
        gameplay = ue.GameplayStatics.get_default_object()
        camera = gameplay.call_method("BeginDeferredActorSpawnFromClass", args=(s["world"],
            ue.CameraActor.static_class(), transform, ue.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,
            None, ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        gameplay.call_method("FinishSpawningActor", args=(camera, transform, ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        camera.get_component_by_class(ue.CameraComponent).set_field_of_view(80)
        s["pc"].set_view_target_with_blend(camera, 0.0)
        s["events"].append({"diagnostic_camera": path(camera), "production_camera_changed": False})

    def spawn_target(self):
        s = self.s
        definition = ue.load_asset("/Game/AI/Boss/Test/DA_Boss_Diagnostic_TargetVitals")
        if not definition or definition.get_editor_property("BehaviorTree"):
            raise RuntimeError("诊断目标无定义或包含行为树")
        transform = ue.Transform()
        transform.translation = s["pawn"].get_actor_location() + s["pawn"].get_actor_forward_vector() * 150
        gameplay = ue.GameplayStatics.get_default_object()
        encounter = gameplay.call_method("BeginDeferredActorSpawnFromClass", args=(s["world"],
            ue.GGYGOBossEncounter.static_class(), transform, ue.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,
            None, ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        s["encounter"] = encounter
        encounter.set_editor_property("bSpawnOnBeginPlay", False)
        encounter.set_editor_property("BossDefinition", definition)
        gameplay.call_method("FinishSpawningActor", args=(encounter, transform, ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        if not encounter.spawn_boss():
            raise RuntimeError("诊断目标生成失败")
        target = encounter.get_boss_avatar()
        health = ue.GGYGOHealthComponent.find_health_component(target)
        if not health:
            raise RuntimeError("诊断目标缺生命组件")
        s.update(target=target, health=health, health_before=health.get_health())
        callback = self.on_health
        health.on_health_changed.add_callable(callback)
        s["health_callback"] = callback

    def on_health(self, component, old, new, instigator):
        s = self.s
        s["hits"].append({"frame": ue.SystemLibrary.get_frame_count(), "old": old, "new": new,
                          "instigator": path(instigator),
                          "step": s["ability"].get_current_combo_step() if s["ability"] else None})

    def key(self, pressed):
        s = self.s
        result = ue.GGYGOPlayerInputBridgeLibrary.submit_digital_key_event(s["world"], s["lp"], s["pc"],
            s["pawn"], s["pinput"], s["input_comp"], s["device"], s["key"], pressed)
        if result is None:
            raise RuntimeError("生产 InputKey 被拒绝")
        s["key_down"] = pressed
        s["key_frame"] = ue.SystemLibrary.get_frame_count()
        s["events"].append({"frame": s["key_frame"], "key": pressed, "result": str(result)})

    def observe(self):
        s = self.s
        now = time.monotonic() - s["started"]
        frame = ue.SystemLibrary.get_frame_count()
        if now > 120:
            raise RuntimeError("动作观察超过 120 秒")
        if s["key_down"] and frame > s["key_frame"]:
            self.key(False)
        self.poll_images()
        ability, instance = ue.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(s["asc"], s["spec"])
        active = bool(instance and ue.AbilitySystemLibrary.is_gameplay_ability_active(ability))
        row = {"frame": frame, "seconds": now, "active": active, "health": s["health"].get_health(),
               "main_mesh_visible": s["mesh"].is_visible()}
        if active:
            s["ability"] = ability
            index = ability.get_current_combo_step()
            row["step"] = index
            montage = s["montages"][index] if 0 <= index < len(s["montages"]) else None
            if montage and s["anim"].montage_is_playing(montage):
                position = s["anim"].montage_get_position(montage)
                section = str(s["anim"].montage_get_current_section(montage))
                row.update(position=position, section=section)
                s["sections"].setdefault(str(index) + ":" + section, {"seconds": now, "position": position})
                if index not in s["observed_steps"]:
                    obs = ue.GGYGOPlayerActionObservation.create_observation()
                    result = obs.begin_observation(ability, s["asc"], s["pawn"], s["mesh"], montage, s["name"], 4096)
                    if result is None:
                        raise RuntimeError("原 GA 观察未能安装")
                    s["observers"].append(obs)
                    s["observed_steps"].add(index)
                if section == "Main" and (s["name"] != "Combo" or index > 0):
                    for threshold in CAPTURE_TIMES:
                        key = (index, threshold)
                        if position >= threshold and key not in s["captures"]:
                            s["captures"].add(key)
                            self.capture(str(index) + "_" + str(round(position, 3)))
                            break
                if (self.cancel_seconds >= 0 and "cancel" not in s and section == "Main"
                        and position >= self.cancel_seconds and (s["name"] != "Combo" or index == self.last_combo_step)):
                    step_fx = ability.get_editor_property("combo_steps")[index].get_editor_property("fx")
                    selected = {path(u.get_editor_property("system")) for u in step_fx.get_editor_property("system_units")}
                    if step_fx.get_editor_property("system"):
                        selected.add(path(step_fx.get_editor_property("system")))
                    # 仅测试原 GA 公开取消入口，不伪造通知或直接销毁 FX。
                    ability.cancel_ability()
                    s["cancel"] = {"frame": frame, "step": index, "position": position,
                                   "systems": sorted(selected), "entry": "GameplayAbility.CancelAbility"}
                    s["cancel"]["remaining_selected_fx"] = [item for item in self.components(ue.NiagaraComponent, {}, now)
                                                              if item["asset"] in selected]
            if s["name"] == "Combo" and index < self.last_combo_step and ability.is_attack_continuation_open() and index + 1 not in s["requested"]:
                self.key(True)
                s["requested"].add(index + 1)
        elif s["ability"]:
            s.setdefault("ended", now)
        elif now > 30:
            raise RuntimeError("触发后没有观察到生产 GA 激活")
        if now - s["sample_time"] >= 0.05:
            s["sample_time"] = now
            s["fx_observer"].sample(now)
            for obs in s["observers"]:
                obs.sample(now)
            row["fx"] = self.components(ue.NiagaraComponent, s["niagara"], now)
            row["audio"] = self.components(ue.AudioComponent, s["audio"], now)
            tail_system = os.environ.get("GGYGO_ACTION_FX_CAPTURE_TAIL_SYSTEM")
            if tail_system:
                game_seconds = ue.GameplayStatics.get_time_seconds(s["world"])
                row["game_seconds"] = game_seconds
                row["world_paused"] = ue.GameplayStatics.is_game_paused(s["world"])
                row["global_time_dilation"] = ue.GameplayStatics.get_global_time_dilation(s["world"])
                selected = [item for item in row["fx"] if item["asset"].split(".")[0] == tail_system]
                if any(item["attach_parent"] is None for item in selected):
                    s.setdefault("tail_started", game_seconds)
                if "tail_started" in s:
                    elapsed = game_seconds - s["tail_started"]
                    for threshold in (0.0, 0.15, 0.3, 0.6, 1.0, 2.0, 3.5):
                        key = ("tail", threshold)
                        if elapsed >= threshold and key not in s["captures"]:
                            s["captures"].add(key)
                            self.capture("tail_" + str(round(elapsed, 3)))
                            break
            s["frames"].append(row)
        if "ended" in s and now - s["ended"] > 4:
            s["remaining_fx"] = self.components(ue.NiagaraComponent, {}, now)
            if s["remaining_fx"] and now - s["ended"] < 15:
                return
            self.finish()

    def components(self, cls, seen, now):
        s, rows = self.s, []
        for component in ue.ObjectIterator(cls):
            if component.get_world() != s["world"]:
                continue
            asset = component.get_asset() if cls == ue.NiagaraComponent else component.get_editor_property("sound")
            if not asset or "Pyrios" not in asset.get_path_name():
                continue
            playing = component.is_active() if cls == ue.NiagaraComponent else component.is_playing()
            item = {"component": path(component), "asset": path(asset), "playing": playing,
                    "attach_parent": path(component.get_attach_parent())}
            if cls == ue.NiagaraComponent:
                parent = component.get_attach_parent()
                socket = component.get_attach_socket_name()
                item["attach_socket"] = str(socket)
                item["world_transform"] = component.get_world_transform().export_text()
                if parent:
                    socket_transform = parent.get_socket_transform(socket, ue.RelativeTransformSpace.RTS_WORLD)
                    item["parent_socket_transform"] = socket_transform.export_text()
                    item["identity_attachment_matches"] = ue.MathLibrary.nearly_equal_transform_transform(
                        component.get_world_transform(), socket_transform, 0.01, 0.01, 0.0001)
            seen.setdefault(path(component), {**item, "first_seen": now})["last_seen"] = now
            rows.append(item)
        return rows

    def capture(self, label):
        s = self.s
        filename = s["folder"] / (str(len(s["images"])).zfill(3) + "_" + label + ".png")
        task = ue.GGYGOViewportReadbackLibrary.begin_game_viewport_readback_to_file(s["world"], str(filename), 0)
        if not task:
            raise RuntimeError("游戏 viewport 截图请求失败")
        item = {"path": str(filename), "task": task, "frame": ue.SystemLibrary.get_frame_count()}
        s["images"].append(item)
        s["pending"].append(item)

    def poll_images(self):
        for item in list(self.s["pending"]):
            result = item["task"].read_result()
            if result.status in (ue.GGYGOViewportReadbackStatus.COMPLETE, ue.GGYGOViewportReadbackStatus.FAILED,
                                  ue.GGYGOViewportReadbackStatus.CANCELLED):
                item.update(status=str(result.status), error=result.error,
                            verified=result.file_write_complete and result.file_readback_verified,
                            render_frame=result.render_callback_frame)
                item.pop("task").release()
                self.s["pending"].remove(item)

    def finish(self):
        s = self.s
        if s.get("key_down"):
            self.key(False)
        if s.get("health_callback"):
            s["health"].on_health_changed.remove_callable(s.pop("health_callback"))
        for label, observers in (("action_observation", s["observers"]),
                                 ("fx_observation", [s["fx_observer"]] if "fx_observer" in s else [])):
            for obs in observers:
                obs.stop_observation()
                s[label] = json.loads(obs.get_observation_json())
                if label == "action_observation":
                    s.setdefault("action_observations", []).append(s[label])
        if s.get("recording"):
            ue.AudioMixerLibrary.stop_recording_output(s["world"], ue.AudioRecordingExportType.WAV_FILE,
                                                       "master", str(s["folder"]), None)
            s["recording"] = False
        if s.get("trace"):
            ue.SystemLibrary.execute_console_command(s["world"], "Trace.Stop", s["pc"])
            s["trace"] = False
        self.deadline, self.state = time.monotonic() + 15, "draining"

    def write_scene(self):
        s = self.s
        final = s.get("action_observation", {})
        expected_steps = set(range(self.last_combo_step + 1)) if s["name"] == "Combo" else {0}
        expected_hits = set(range(1, self.last_combo_step + 1)) if s["name"] == "Combo" else {0}
        s["checks"] = {
            "montage_steps_observed": s["observed_steps"] == expected_steps,
            "natural_end": final.get("natural_completion_history_complete", False),
            "not_cancelled": final.get("original_ga_full_exit_completed", False)
                             and not final.get("original_exit_cancelled", True),
            "hit_steps": expected_hits <= {hit["step"] for hit in s["hits"] if hit["new"] < hit["old"]},
            "fx_components_observed": bool(s["niagara"]),
            "audio_components_observed": bool(s["audio"]),
            "screenshots_written": bool(s["images"]) and all(i.get("verified") for i in s["images"]),
            "fx_components_released": "remaining_fx" in s and not s["remaining_fx"],
        }
        if self.cancel_seconds >= 0:
            # 自然结束场景仍完整保留上述断言；取消场景独立核原终止事实与本段立即清理。
            s["checks"].pop("natural_end")
            s["checks"].pop("not_cancelled")
            s["checks"].pop("hit_steps")
            s["checks"].update(cancel_requested="cancel" in s,
                original_exit_cancelled=final.get("original_ga_full_exit_completed", False)
                                        and final.get("original_exit_cancelled", False),
                current_step_fx_released="cancel" in s and not s["cancel"]["remaining_selected_fx"])
        fields = ("name", "error", "images", "hits", "events", "sections", "health_before", "ended",
                  "audio", "niagara", "action_observation", "action_observations", "fx_observation",
                  "remaining_fx", "checks", "cancel")
        save(s["folder"] / "observations.json", {k: s[k] for k in fields if k in s})
        with (s["folder"] / "frames.jsonl").open("w", encoding="utf-8") as stream:
            for row in s["frames"]:
                stream.write(json.dumps(row, ensure_ascii=False) + "\n")
        self.results[s["name"]] = {"error": s["error"], "images": len(s["images"]), "hits": len(s["hits"]),
                                   "checks": s["checks"], "passed": not s["error"] and all(s["checks"].values())}
        ue.log("[ActionFX] 场景结束：" + s["name"] + " " + str(self.results[s["name"]]))
        self.s = None

    def quit(self, error=None):
        ue.unregister_slate_post_tick_callback(self.handle)
        if self.ues.get_game_world() is None:
            self.restore_fixture()
        save(OUT / "run.json", {"results": self.results, "error": error,
                               "dirty": [path(p) for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()]})
        (OUT / "quit.flag").write_text("quit", encoding="utf-8")
        if os.environ.get("GGYGO_ACTION_FX_KEEP_EDITOR") != "1":
            ue.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")


ue._pyrios_action_fx_run = Run()
