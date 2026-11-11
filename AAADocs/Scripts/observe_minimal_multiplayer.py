"""@file observe_minimal_multiplayer.py
@brief 独立 Editor 的最小联机输入及观察宿主。

由 run_minimal_multiplayer.ps1 设置输出目录、角色和试次，再用 ExecCmds 安装。
一个 Slate 回调消费自然帧；输入走原装配，观察走现有 Editor 接口。
captured 只表示数据已收集；场景断言和实际截图仍须检查。
"""
import copy
import json
import os
import sys
import time
import traceback
from pathlib import Path

import unreal as ue

sys.path.insert(0, str(Path(__file__).resolve().parent))
import minimal_multiplayer_checks as check
import minimal_multiplayer_input as input_ops
from minimal_multiplayer_status import append_status, read_status

ROOT_OUT = Path(os.environ["GGYGO_MULTIPLAYER_OUT"])
ROLE = os.environ["GGYGO_MULTIPLAYER_ROLE"]
CASES = os.environ["GGYGO_MULTIPLAYER_CASE"].split(",")
if CASES == ["all"]:
    CASES = ["attack_only", "correction", "initial_unavailable", "live_first", "closed_first", "reacquire"]
CASE = CASES.pop(0)
OUT = ROOT_OUT / CASE
LOG = ROOT_OUT / ROLE / "editor.log"
PORT = int(os.environ["GGYGO_MULTIPLAYER_PORT"])
TAIL_PROBE = os.environ.get("GGYGO_MULTIPLAYER_TAIL_PROBE") == "1"
COMBO = "/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo.GA_Pyrios_Attack_Combo_C"
FX_CASES = ("live_first", "closed_first", "reacquire")
# Normal03 的 M14 下劈与 M15 地面层；原资产在 Main 0.75／0.8 秒发射。
VISUAL_FX_SYSTEM = ("/Game/Characters/Player/Pyrios/FX/Skill/"
    "NS_Pyrios_Normal03_MainComposition_a66c4d372b54_Unit04_e65d18ad8b75."
    "NS_Pyrios_Normal03_MainComposition_a66c4d372b54_Unit04_e65d18ad8b75")


def path(obj):
    return obj.get_path_name() if obj is not None else None


def save(filename, value):
    temporary = filename.with_suffix(".writing")
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=1, allow_nan=False), encoding="utf-8")
    temporary.replace(filename)


def read_page(getter, previous=None):
    count = len(previous["records"]) if previous else 0
    return check.merge_observation_page(previous, json.loads(getter(count, -1)))


def read_final(getter, previous):
    merged = read_page(getter, previous)
    full = json.loads(getter())
    check.require(merged["records"] == full["records"], "增量记录与原无参全量读回不一致")
    return full


def worlds():
    return list(ue.EditorLevelLibrary.get_pie_worlds(True))


def local_pc(world):
    controllers = [ue.GameplayStatics.get_player_controller(world, i)
                   for i in range(ue.GameplayStatics.get_num_player_controllers(world))]
    local = [pc for pc in controllers if pc and pc.get_world() == world and pc.is_local_controller()]
    check.require(len(local) <= 1, "本试次每个 World 只允许一个 LocalPlayer")
    return local[0] if local else None


def player_pawn(world, player_id):
    state = ue.GameplayStatics.get_game_state(world)
    matches = [ps for ps in state.get_editor_property("player_array")
               if ps and ps.get_world() == world and check.player_id(ps) == player_id] if state else []
    check.require(len(matches) <= 1, "同 World 的 PlayerId 配对不唯一")
    return matches[0].get_pawn() if matches else None


def endpoint(pawn, expected_role):
    if pawn is None:
        return None
    roles = {1: ue.NetRole.ROLE_SIMULATED_PROXY, 2: ue.NetRole.ROLE_AUTONOMOUS_PROXY, 3: ue.NetRole.ROLE_AUTHORITY}
    check.require(pawn.get_local_role() == roles[expected_role], "配对 Pawn 的网络角色错误")
    ps = pawn.get_editor_property("player_state")
    asc = ue.AbilitySystemLibrary.get_ability_system_component(pawn)
    mesh = pawn.get_component_by_class(ue.SkeletalMeshComponent)
    move = pawn.get_component_by_class(ue.GGYGOCharacterMovementComponent)
    if not all((ps, asc, mesh, move, mesh.get_anim_instance())):
        return None
    squad = ps.call_method("GetSquadComponent")
    slot = squad.call_method("GetActiveSlot") if squad else None
    if not slot or slot.call_method("GetAvatarPawn") != pawn:
        return None
    check.require(slot.call_method("GetGGYGOAbilitySystemComponent") == asc
                  and pawn.call_method("GetGGYGOAbilitySystemComponent") == asc,
                  "PlayerState/Slot/Pawn 的 ASC 不一致")
    cls = ue.load_class(None, COMBO)
    handles = [h for h in asc.get_all_abilities()
               if ue.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(asc, h)[0].get_class() == cls]
    if not handles and expected_role != 1:
        return None
    check.require(expected_role == 1 or len(handles) == 1, "原 Combo Spec 不唯一")
    return dict(world=pawn.get_world(), pawn=pawn, ps=ps, asc=asc, mesh=mesh,
                move=move, anim=mesh.get_anim_instance(), spec=handles[0] if handles else None, cls=cls)


class Run:
    def __init__(self):
        check.require(ROLE in ("authority", "observer"), "未知 Editor 角色")
        check.require(CASE in ("attack_only", "correction", "initial_unavailable", *FX_CASES), "未接入的试次")
        self.folder = OUT / ROLE
        self.folder.mkdir(parents=True, exist_ok=True)
        self.les = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        self.pose = ue.get_engine_subsystem(ue.GGYGOAnimationPoseObservationSubsystem)
        self.state, self.phase = "boot", "waiting"
        self.started, self.phase_started = time.monotonic(), time.monotonic()
        self.endpoints, self.actions, self.action_states = {}, {}, {}
        self.pose_rows, self.pose_owned = [], False
        self.clock_rows = []
        self.editor_slate_throttling = None
        self.viewport_sizes, self.pie_request = {}, None
        self.preparations, self.preparation_records, self.prepare_systems = {}, {}, []
        self.peer, self.player_id, self.input = {}, None, None
        self.keys, self.held, self.events = {}, set(), []
        self.arm, self.driver_original, self.driver_current = None, None, None
        self.driver_changed, self.pose_meta = False, None
        self.pending_images, self.images = [], []
        self.capture_requested = False
        self.camera, self.camera_record = None, None
        self.camera_framed_fx = False
        self.camera_anchor = None
        self.fx, self.fx_state = None, None
        self.fx_key = None
        self.tail_probe, self.tail_component = None, None
        self.visual_fx = dict(system=VISUAL_FX_SYSTEM, combo_step=2, minimum_age=0.8) \
            if CASE in ("live_first", "reacquire") else None
        self.network_fx, self.network_fx_state, self.join_record = None, None, None
        self.relevancy, self.cull_before, self.channel_cursor = {}, None, 0
        self.viewer_id, self.old_proxy = None, None
        self.old_fx_state = None
        self.log_offset, self.error, self.in_tick = None, None, False
        self.verification = None
        self.driver = dict(variant="reject_replay", frame_domain="OwnerInputSubmissionGFrameCounter",
            sample_frame_domain="ReadTimeGFrameCounter_NotInputEvaluation", attack_attempts=0,
            held_samples=[], third_samples=[], second_samples=[], rejected_attempt=None,
            first_press_frame=None, second_press_frame=None, third_press_frame=None)
        self.handle = ue.register_slate_post_tick_callback(self.tick)

    def publish(self):
        state = dict(role=ROLE, case=CASE, pid=os.getpid(),
            state=self.state, phase=self.phase, player_id=self.player_id, error=self.error,
            verification=self.verification,
            elapsed_seconds=time.monotonic() - self.started,
            fx_active=self.active_fx() if CASE in FX_CASES else None,
            fx_closed=self.closed_fx() if CASE in FX_CASES else None,
            relevancy=self.relevancy,
            camera_anchor=self.camera_anchor,
            authority_steps={str(key[1]): value["original_source"] for key, value in self.action_states.items()
                             if key[0] == "authority"})
        append_status(self.folder / "state.jsonl", state)

    def active_fx(self):
        active = check.fx_active(self.fx_state, self.visual_fx["system"] if self.visual_fx else None)
        if active and self.visual_fx:
            if self.fx_key is not None:
                check.require(self.fx_key == active["occurrence"], "目标 FX 出现了另一发布键")
            self.fx_key = active["occurrence"]
        return active

    def closed_fx(self):
        if self.visual_fx and self.fx_key is None:
            return None
        return check.fx_dispatched_close(self.fx_state, self.fx_key)

    def tick(self, _dt):
        if self.in_tick:
            return
        self.in_tick = True
        try:
            peer_file = OUT / ("observer" if ROLE == "authority" else "authority") / "state.jsonl"
            if peer_file.exists():
                latest = read_status(peer_file)
                if latest is not None:
                    self.peer = latest
                    check.require(self.peer["case"] == CASE, "两端试次不同")
            if self.state not in ("ending", "done"):
                check.require(time.monotonic() - self.started < 180, "试次超过 180 秒")
                check.require(not self.peer.get("error"), "另一端失败：" + str(self.peer.get("error")))
            self.step()
            self.publish()
            if self.state == "done":
                self.advance_queue()
        except Exception:
            self.error = traceback.format_exc()
            ue.log_error("[MinimalMultiplayer] " + self.error)
            if self.state == "done":
                self.publish()
                self.advance_queue()
                return
            try:
                self.finish()
            except Exception:
                self.error += "\n清理失败：\n" + traceback.format_exc()
                self.state = "ending"
                self.publish()
                self.les.editor_request_end_play()
        finally:
            self.in_tick = False

    def step(self):
        if self.state == "boot":
            if time.monotonic() - self.started < 15 or ue.AssetRegistryHelpers.get_asset_registry().is_loading_assets():
                return
            check.require("-nullrhi" not in ue.SystemLibrary.get_command_line().lower(), "本入口要求真实 RHI")
            check.require(not worlds(), "本宿主只能创建自己的 PIE")
            for name in ("create_observation", "begin_observation", "begin_fx_observation", "sample"):
                check.require(hasattr(ue.GGYGOPlayerActionObservation, name), "缺实际 Python 绑定：" + name)
            check.require(callable(getattr(ue.PlayerController, "get_controlled_pawn", None))
                          and callable(getattr(ue.PlayerState, "get_pawn", None)),
                          "缺 Controller／PlayerState 的实际 Pawn 查询绑定")
            check.require(callable(getattr(ue, "log_flush", None)), "缺实际 log_flush 绑定")
            settings = ue.get_default_object(ue.load_class(None, "/Script/UnrealEd.LevelEditorPlaySettings"))
            # EndPIE 会把带窗口边框的尺寸写回 CDO；每个独立场景先重设本进程的测试尺寸。
            ue.ToolsetLibrary.set_object_properties(settings, json.dumps(dict(
                NewWindowWidth=640, NewWindowHeight=360, ClientWindowWidth=640, ClientWindowHeight=360)))
            actual = json.loads(ue.ToolsetLibrary.get_object_properties(settings,
                ["PlayNetMode", "PlayNumberOfClients", "RunUnderOneProcess", "bLaunchSeparateServer",
                 "NewWindowWidth", "NewWindowHeight", "ClientWindowWidth", "ClientWindowHeight"]))
            expected = dict(PlayNetMode="PIE_ListenServer" if ROLE == "authority" else "PIE_Standalone",
                PlayNumberOfClients=2 if ROLE == "authority" else 1,
                RunUnderOneProcess=True, bLaunchSeparateServer=False,
                NewWindowWidth=640, NewWindowHeight=360, ClientWindowWidth=640, ClientWindowHeight=360)
            check.require(actual == expected, "PIE 配置不符：" + repr(actual))
            # 最小联机不验冷加载；在 World 计时开始前加载原 Combo 及其硬引用资产。
            self.preloaded_combo = ue.load_class(None, COMBO)
            check.require(self.preloaded_combo is not None, "原 Combo 及其硬引用资产加载失败")
            for step in list(ue.get_default_object(self.preloaded_combo).get_editor_property("combo_steps"))[:3]:
                fx = step.get_editor_property("fx")
                check.require(fx.get_editor_property("mode") == ue.GGYGOComboFXMode.MONTAGE_WINDOW,
                              "原三段 Combo 未使用 Montage FX 窗口")
                system, units = fx.get_editor_property("system"), list(fx.get_editor_property("system_units"))
                check.require((system is not None) != bool(units), "原 FX 必须唯一选择 System 或 SystemUnits")
                for item in [system] if system is not None else [unit.get_editor_property("system") for unit in units]:
                    check.require(isinstance(item, ue.NiagaraSystem), "原 Combo 含无效 Niagara System")
                    if item not in self.prepare_systems:
                        self.prepare_systems.append(item)
            check.require(self.prepare_systems, "原 Combo 无待准备的 FX 资源")
            # Slate 通知动画的响应节流会跳过全部 PIE World Tick；仅本测试 Editor 关闭此 UI 节流。
            ue.SystemLibrary.execute_console_command(None, "Slate.bAllowThrottling 0")
            self.editor_slate_throttling = ue.SystemLibrary.get_console_variable_int_value("Slate.bAllowThrottling")
            check.require(self.editor_slate_throttling == 0, "本测试 Editor 的 Slate 节流未实际关闭")
            ue.SystemLibrary.execute_console_command(None, "t.MaxFPS 60")
            # 浮动 PIE 自己绘制游戏；后台 Level Editor 视口只停实时重绘，不停 PIE World。
            check.require(callable(getattr(self.les, "editor_set_viewport_realtime", None)),
                          "缺 Level Editor 原实时视口控制绑定")
            self.les.editor_set_viewport_realtime(False)
            # 原 Toolset 的进程内浮动 PIE 遵守明确分辨率，避免三 World 各用整个编辑器视口。
            self.pie_request = ue.ToolsetRegistry.execute_tool("EditorToolset.EditorAppToolset", "StartPIE",
                json.dumps(dict(options=dict(playMode="PlayMode_InEditorFloating", warmupSeconds=0.0))))
            check.require(self.pie_request is not None, "原 Toolset 未返回 PIE 启动请求")
            self.state = "pairing"
            return
        if self.state == "pairing":
            check.require(not self.pie_request.get_editor_property("error"),
                          "原 Toolset PIE 启动失败：" + self.pie_request.get_editor_property("error"))
            if not self.pie_request.get_editor_property("is_complete"):
                return
            self.pair()
            return
        if self.state == "reacquire":
            self.reacquire_observer()
            return
        if self.state == "running":
            if ROLE == "observer" and CASE == "reacquire" and self.old_fx_state is None \
                    and not ue.SystemLibrary.is_valid(self.old_proxy):
                # 原 Avatar 已退役时只排空原窗；不调用要求活 Avatar 的 CaptureObservation。
                self.fx.stop_observation()
                self.old_fx_state = read_final(self.fx.get_observation_json, self.fx_state)
                self.pose.stop_observation()
                self.pose_owned = False
                self.pose_rows = []
                self.fx = None
                self.state = "reacquire"
                self.reacquire_observer()
                return
            self.sample()
            if ROLE == "authority":
                self.drive()
            elif CASE in FX_CASES:
                self.observe_fx_trial()
            elif self.peer.get("phase") == "captured":
                self.phase = "captured"
                self.finish()
            self.poll_images()
            return
        if self.state == "ending":
            self.poll_images()
            if worlds():
                return
            self.state = "done"

    def advance_queue(self):
        global CASE, OUT
        if not self.error and not self.peer.get("error") and self.peer.get("state") != "done":
            check.require(time.monotonic() - self.finish_started < 30, "另一端未归还原 PIE")
            return
        if not self.error and not self.peer.get("error"):
            if ROLE == "authority" and self.verification is None:
                import verify_minimal_multiplayer
                result = verify_minimal_multiplayer.verify(OUT)
                save(OUT / "checks.json", result)
                self.verification = "numeric_passed"
                self.publish()
            elif ROLE == "observer" and self.peer.get("verification") != "numeric_passed":
                return
        ue.unregister_slate_post_tick_callback(self.handle)
        self.handle = None
        if CASES and not self.error and not self.peer.get("error"):
            CASE = CASES.pop(0)
            OUT = ROOT_OUT / CASE
            ue._minimal_multiplayer_run = Run()
        else:
            ue.SystemLibrary.execute_console_command(None, "QUIT_EDITOR")

    def preparation_finished(self, request):
        record = self.preparation_records[path(request)]
        record.update(state=str(request.get_state()), error=request.get_error(),
                      finished_seconds=time.monotonic() - self.started)

    def prepare_resources(self, world):
        # 每个实际 PIE World 使用生产准备接口；不激活系统，不推进模拟或改资产。
        key = path(world)
        request = self.preparations.get(key)
        if request is None:
            request = ue.GGYGONiagaraMaterialPreparation.create_for_system_assets(world, world, self.prepare_systems)
            check.require(request is not None, "原 Niagara 材质准备请求创建失败")
            self.preparations[key] = request
            self.preparation_records[path(request)] = dict(world=key, systems=[path(s) for s in self.prepare_systems],
                started_seconds=time.monotonic() - self.started)
            request.on_finished.add_callable(self.preparation_finished)
            request.start()
        state = request.get_state()
        check.require(state in (ue.GGYGONiagaraMaterialPreparationState.PENDING,
                                ue.GGYGONiagaraMaterialPreparationState.READY),
                      "原 Niagara 材质准备失败：" + request.get_error())
        return state == ue.GGYGONiagaraMaterialPreparationState.READY

    def pair(self):
        current = worlds()
        if ROLE == "observer":
            if self.player_id is None:
                if self.peer.get("player_id") is None or len(current) != 1:
                    return
                check.require(ue.SystemLibrary.is_standalone(current[0]), "Travel 前不是独立 PIE World")
                self.phase = "standby"
                if CASE in FX_CASES and self.network_fx is None:
                    self.network_fx = ue.GGYGOPlayerActionObservation.create_observation()
                    check.native_success(self.network_fx.begin_network_fx_observation(current[0], CASE, 4096), "NetworkFX.Begin")
                if CASE == "live_first":
                    if self.peer.get("relevancy", {}).get("first_hidden_cull") != 1:
                        return
                if CASE == "closed_first":
                    if not self.peer.get("fx_closed"):
                        return
                    self.join_record = copy.deepcopy(self.peer["fx_closed"])
                self.player_id = self.peer["player_id"]
                ue.GameplayStatics.open_level(current[0], ue.Name("127.0.0.1:" + str(PORT)), True, "")
                return
            clients = [w for w in current if not ue.SystemLibrary.is_server(w) and not ue.SystemLibrary.is_standalone(w)]
            if len(clients) != 1:
                return
            if CASE == "live_first":
                pc = local_pc(clients[0])
                ps = pc.get_editor_property("player_state") if pc else None
                if not ps:
                    return
                self.viewer_id = check.player_id(ps)
                connection = json.loads(self.network_fx.read_network_fx_channel(clients[0], self.viewer_id, None))
                if not connection.get("connection_open"):
                    return
                if not pc.get_controlled_pawn():
                    return
                if not self.prepare_resources(clients[0]):
                    return
                if not self.place_observer_camera(clients[0], pc, self.peer["camera_anchor"]):
                    return
                self.relevancy.setdefault("first_connection", connection)
                self.phase = "waiting_relevance"
                record = self.peer.get("relevancy", {}).get("first_release_record")
                if record is None:
                    return
                self.join_record = copy.deepcopy(record)
            ep = endpoint(player_pawn(clients[0], self.player_id), 1)
            if not ep:
                return
            if CASE != "live_first" and not self.prepare_resources(ep["world"]):
                return
            self.endpoints["observer"] = ep
            if CASE == "live_first":
                channel = json.loads(self.network_fx.read_network_fx_channel(ep["world"], self.viewer_id, ep["pawn"]))
                if not channel.get("channel_id"):
                    return
                check.require(channel["connection_id"] == self.relevancy["first_connection"]["connection_id"],
                              "首次相关性恢复前客户端连接换代")
                self.relevancy["first_new"] = channel
            if CASE in ("closed_first", "reacquire"):
                if not self.place_observer_camera(ep["world"], local_pc(ep["world"]), self.peer["camera_anchor"]):
                    return
            if self.network_fx:
                check.native_success(self.network_fx.select_network_fx_publisher(ep["asc"]), "NetworkFX.Select")
            if CASE == "reacquire":
                self.viewer_id = check.player_id(local_pc(ep["world"]).get_editor_property("player_state"))
                old = json.loads(self.network_fx.read_network_fx_channel(ep["world"], self.viewer_id, ep["pawn"]))
                if not old.get("channel_id") or not old.get("connection_open"):
                    return
                self.relevancy["old"] = old
                self.old_proxy = ep["pawn"]
                self.channel_cursor = LOG.stat().st_size
        else:
            servers = [w for w in current if ue.SystemLibrary.is_server(w) and not ue.SystemLibrary.is_standalone(w)]
            clients = [w for w in current if not ue.SystemLibrary.is_server(w) and not ue.SystemLibrary.is_standalone(w)]
            if len(servers) != 1 or len(clients) != 1:
                return
            pc = local_pc(clients[0])
            owner = endpoint(pc.get_controlled_pawn(), 2) if pc else None
            if not owner:
                return
            self.player_id = check.player_id(owner["ps"])
            authority = endpoint(player_pawn(servers[0], self.player_id), 3)
            if not authority:
                return
            self.endpoints.update(owner=owner, authority=authority)
            ready_worlds = [self.prepare_resources(ep["world"]) for ep in self.endpoints.values()]
            if not all(ready_worlds):
                return
            lib = ue.get_default_object(ue.load_class(None, "/Script/Engine.SubsystemBlueprintLibrary"))
            sub = lib.call_method("GetLocalPlayerSubSystemFromPlayerController",
                args=(pc, ue.EnhancedInputLocalPlayerSubsystem.static_class()))
            ready = ue.GGYGOPlayerInputBridgeLibrary.read_local_player_input_assembly(clients[0], sub.get_outer())
            if isinstance(ready, tuple) and ready[0] == ue.GGYGOPlayerInputAssemblyStatus.WAITING:
                return
            self.input = input_ops.pin_ready_assembly(ue, clients[0], sub.get_outer())
            context = ue.load_asset("/Game/Input/Mappings/IMC_Default")
            for name, action, key in (("Attack", "IA_Attack", "LeftMouseButton"),
                                      ("W", "IA_Move", "W"), ("S", "IA_Move", "S")):
                self.keys[name] = input_ops.read_mapped_key(context, ue.load_asset("/Game/Input/Actions/" + action), key)
                check.require(not pc.is_input_key_down(self.keys[name]), "入场键已持有：" + name)
        self.begin_sampling()

    def begin_sampling(self):
        ep = self.endpoints["authority" if ROLE == "authority" else "observer"]
        for side, source in self.endpoints.items():
            pc = local_pc(source["world"])
            size = pc.get_viewport_size()
            self.viewport_sizes[side] = list(size)
            # 保留窗口边框／DPI 取整后的真实尺寸，约束三个 World 的渲染规模。
            check.require(0 < size[0] <= 704 and 0 < size[1] <= 400,
                          "实际 PIE 视口超过本测试渲染尺寸范围：" + repr(size))
        check.native_success(self.pose.begin_observation(ep["mesh"], [ep["mesh"].get_bone_name(0)], 4096), "Pose.Begin")
        self.pose_owned = True
        self.fx = ue.GGYGOPlayerActionObservation.create_observation()
        self.fx_state = None
        check.native_success(self.fx.begin_fx_observation(ep["asc"], ep["pawn"], ep["mesh"], CASE, 4096), "FX.Begin")
        if ROLE == "authority" and CASE == "live_first":
            # 连接准备与 FX 窗口分开：B 首次建立连接时还没有此 Pawn 的 ActorChannel。
            self.cull_before = ep["pawn"].call_method("GetNetCullDistanceSquared")
            check.require(self.cull_before > 1, "原 Pawn 裁剪范围不足以构造首次相关性")
            ep["pawn"].call_method("SetNetCullDistanceSquared", args=(1.0,))
            self.relevancy["first_hidden_cull"] = ep["pawn"].call_method("GetNetCullDistanceSquared")
            check.require(self.relevancy["first_hidden_cull"] == 1, "首次相关性裁剪未读回")
        if ROLE == "authority" and CASE in FX_CASES:
            location = ep["pawn"].get_actor_location()
            self.camera_anchor = [location.x, location.y, location.z]
        ue.log_flush()
        self.log_offset = LOG.stat().st_size
        self.state, self.phase, self.phase_started = "running", "ready", time.monotonic()

    def sample_network_fx(self):
        if self.network_fx:
            check.native_success(self.network_fx.sample(time.monotonic() - self.started), "NetworkFX.Sample")
            self.network_fx_state = read_page(self.network_fx.get_network_fx_observation_json, self.network_fx_state)
            check.require(not self.network_fx_state["evidence_incomplete"], "连续 FX 观察溢出或失效")

    def key(self, name, down):
        check.require((name in self.held) != down, "重复按下或归还未持有键：" + name)
        # 外调发生前承担清理义务；失败时不重放按下。
        if down:
            self.held.add(name)
        result = input_ops.submit_digital_key(ue, self.input, self.keys[name], down)
        result["connection_state"] = str(result["connection_state"])
        if not down:
            self.held.remove(name)
        self.events.append(dict(action=name, edge="Press" if down else "Release", status="submitted",
            owner_submission_frame=str(ue.SystemLibrary.get_frame_count()), **result))

    def press_attack(self, ordinal):
        self.key("Attack", True)
        self.driver[ordinal + "_press_frame"] = ue.SystemLibrary.get_frame_count()
        self.driver["attack_attempts"] += 1

    def read_action(self, side):
        ep = self.endpoints[side]
        ability, instance = ue.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(ep["asc"], ep["spec"])
        active = bool(instance and ue.AbilitySystemLibrary.is_gameplay_ability_active(ability))
        step = ability.get_current_combo_step() if instance else None
        facts = dict(current_step=step, attack_continuation_open=ability.is_attack_continuation_open() if active else False,
                     step_source=None, step_record=None, active=active)
        current = [(key, state) for key, state in self.action_states.items() if key[0] == side and state["records"]
                   and state["records"][-1]["original_ga_resource_source_current"]]
        check.require(len(current) <= 1, "同端存在多个当前原动作资源")
        if active and step is not None and step >= 0 and not current:
            steps = ue.get_default_object(ep["cls"]).get_editor_property("combo_steps")
            montage = steps[step].get_editor_property("montage")
            if ep["anim"].montage_is_playing(montage):
                obj = ue.GGYGOPlayerActionObservation.create_observation()
                key = side, step, sum(k[:2] == (side, step) for k in self.actions)
                self.actions[key] = obj
                check.native_success(obj.begin_observation(ability, ep["asc"], ep["pawn"], ep["mesh"], montage,
                    CASE + "_" + "_".join(map(str, key)), 4096), "Action.Begin")
                check.native_success(obj.sample(time.monotonic() - self.started), "Action.Sample")
                state = json.loads(obj.get_observation_json())
                check.require(state["original_source"]["original_native_source_authenticated"], "原动作来源未认证")
                self.action_states[key] = state
                current = [(key, state)]
        if current:
            state = current[0][1]
            facts.update(step_source=copy.deepcopy(state["original_source"]), step_record=copy.deepcopy(state["records"][-1]))
        return facts

    def sample(self):
        elapsed = time.monotonic() - self.started
        self.clock_rows.append(dict(elapsed_seconds=elapsed, worlds={side:
            json.loads(ue.GGYGOPlayerActionObservation.read_world_clock(ep["world"]))
            for side, ep in self.endpoints.items()}))
        self.sample_network_fx()
        page = json.loads(self.pose.get_observation_json(len(self.pose_rows), -1))
        check.require(page["read_success"] and page["active"] and page["records_start_index"] == len(self.pose_rows),
                      "Pose 分页已失效或窗口被替换")
        self.pose_rows.extend(page["records"])
        self.pose_meta = {k: v for k, v in page.items() if k != "records"}
        for key, obj in self.actions.items():
            if json.loads(obj.get_observation_json(0, 0))["active"]:
                check.native_success(obj.sample(elapsed), "Action.Sample")
            state = read_page(obj.get_observation_json, self.action_states.get(key))
            check.require(not state["evidence_incomplete"], "动作观察溢出")
            if key in self.action_states:
                check.require(state["original_source"] == self.action_states[key]["original_source"], "原动作观察换源")
            self.action_states[key] = state
        if ROLE == "authority":
            self.live = {side: self.read_action(side) for side in ("owner", "authority")}
        check.native_success(self.fx.sample(elapsed), "FX.Sample")
        self.fx_state = read_page(self.fx.get_observation_json, self.fx_state)
        check.require(not self.fx_state["evidence_incomplete"], "FX 观察溢出")
        if ROLE == "observer" and CASE not in FX_CASES and not self.capture_requested \
                and any(check.fx_reached(r) for r in self.fx_state["records"]):
            self.capture()
        if self.pose_rows:
            network = self.pose_rows[-1]["network_driver_live"]
            check.require(network["available"] and network["named_driver_matches"], "原 NetDriver 配置不可读")
            check.require(all(network[k] == 0 for k in ("incoming_loss_percent", "incoming_frame_delay", "incoming_buffer_bloat_ms")),
                          "网络模拟包含延迟之外的设置")
            if self.driver_original is None:
                self.driver_original = copy.deepcopy(network)
            self.driver_current = network

    def set_lag(self, milliseconds):
        network = self.driver_current
        check.require(network is not None and ROLE == "authority", "只修改本进程原 Authority Driver")
        self.driver_changed = True
        ue.SystemLibrary.execute_console_command(self.endpoints["authority"]["world"],
            "NET " + network["driver_name"] + " PktIncomingLagMin=" + str(milliseconds)
            + " PktIncomingLagMax=" + str(milliseconds))

    def arm_tasks(self):
        if self.arm or not self.pose_rows:
            return self.arm is not None
        ep = self.endpoints["authority"]
        expected = dict(world=path(ep["world"]), pawn=path(ep["pawn"]), ability_system=path(ep["asc"]), local_role=3)
        live = check.ability_system_live(self.pose_rows[-1], expected)
        if not live["available"]:
            return False
        cdo = path(ue.get_default_object(ep["cls"]))
        specs = [s for s in live["specs"] if s["ability"] == cdo]
        check.require(len(specs) == 1 and not specs[0]["active"] and not live["unread_known_task_count"], "入场原 Spec 或任务未空闲")
        self.arm = dict(record_index=len(self.pose_rows)-1, live_frame=live["live_frame"], expected=expected,
            spec_handle=specs[0]["spec_handle"], ability_cdo=cdo, ability_class=COMBO,
            task_class=path(ue.load_class(None, "/Script/GGYGO.GGYGOAbilityTask_WaitComboInput")),
            **{k: live[k] for k in ("pawn_object_id", "ability_system_object_id", "owner_actor")})
        return True

    def drive(self):
        frame = ue.SystemLibrary.get_frame_count()
        if "Attack" in self.held:
            ordinal = ("first", "second", "third")[self.driver["attack_attempts"] - 1]
            if frame > self.driver[ordinal + "_press_frame"]:
                self.key("Attack", False)
                self.driver[ordinal + "_release_frame"] = frame
        if self.phase == "ready":
            peer_ready = self.peer.get("state") == "running"
            if CASE == "live_first":
                peer_ready = self.peer.get("phase") == "waiting_relevance"
            if CASE == "closed_first":
                peer_ready = self.peer.get("phase") == "standby"
            if CASE == "reacquire":
                peer_ready = bool(self.peer.get("relevancy", {}).get("old")) and self.peer.get("state") == "running"
            if not peer_ready or not self.arm_tasks() or time.monotonic() - self.phase_started < 1:
                return
            if CASE == "live_first":
                ep = self.endpoints["authority"]
                viewer = self.peer["relevancy"]["first_connection"]["viewer_player_id"]
                hidden = json.loads(self.fx.read_network_fx_channel(ep["world"], viewer, ep["pawn"]))
                if not hidden.get("connection_open") or "pawn_relevant_to_viewer" not in hidden:
                    return
                check.require(hidden.get("actor_channel_absent")
                              and hidden.get("pawn_relevant_to_viewer") is False and hidden.get("pawn_net_guid"),
                              "首次入场前原连接已有 Pawn 通道或未实际失去相关性")
                self.relevancy["first_hidden"] = hidden
            if CASE == "correction":
                self.key("W", True)
                self.driver["forward_frame"] = frame
                self.phase = "forward"
            else:
                if CASE == "initial_unavailable":
                    self.inject_missing_initial()
                self.press_attack("first")
                self.phase = "action"
            self.action_started = time.monotonic()
            return
        if self.phase == "forward" and frame >= self.driver["forward_frame"] + 3:
            # Initial 到达前留足三次真实 owner 推进；随后清除延迟，只让原初始包保留既定延后。
            self.driver["initial_lag_ms"] = 1000
            self.set_lag(self.driver["initial_lag_ms"])
            self.phase = "forward_lag"
        if self.phase == "forward_lag" and self.driver_current["incoming_lag_min_ms"] \
                == self.driver_current["incoming_lag_max_ms"] == self.driver["initial_lag_ms"]:
            self.press_attack("first")
            self.phase = "initial"
        if CASE == "correction":
            self.drive_correction(frame)
        if self.visual_fx and self.phase == "action" and self.driver["attack_attempts"] < 3 and "Attack" not in self.held:
            step = self.driver["attack_attempts"] - 1
            if all(v["current_step"] == step and v["attack_continuation_open"] for v in self.live.values()):
                self.press_attack(("first", "second", "third")[self.driver["attack_attempts"]])
        if CASE == "reacquire" and self.phase == "action":
            self.reacquire_authority()
        if CASE == "live_first" and self.phase == "action" and self.cull_before is not None:
            record = self.active_fx()
            if record is not None:
                self.relevancy["first_release_record"] = copy.deepcopy(record)
                self.restore_cull()
        if self.phase == "action" and time.monotonic() - self.action_started > 2:
            idle = all(not row["active"] for row in self.live.values())
            tasks = check.combo_task_evidence(self.pose_rows, self.arm)
            # 移动输入在动作内释放后，可合法接入原 WalkStop；等其自然收尾再取最终清理证据。
            if idle and tasks["cleanup_verified"] and self.pose_rows[-1]["movement_action_native"]["status"] == 2 \
                    and self.owner_public()["cleanup_verified"]:
                self.phase, self.phase_started = "authority_done" if CASE in FX_CASES else "captured", time.monotonic()
        if self.phase == "authority_done" and self.peer.get("phase") == "captured":
            self.phase = "captured"
        if self.phase == "captured" and (self.peer.get("phase") == "captured" or time.monotonic() - self.phase_started > 5):
            self.finish()

    def drive_correction(self, frame):
        owner, authority = self.live["owner"], self.live["authority"]
        if self.phase == "initial" and owner["step_source"]:
            check.require(not authority["step_source"], "Authority 已起段，未覆盖可施加初始延迟的窗口")
            # 原 Initial 已携 W 提交；从 owner 真正起段后收集 S 的自然帧，避免把三帧都挤在 Authority 开门前。
            self.key("S", True)
            self.key("W", False)
            self.driver["reverse_frame"] = frame
            self.phase = "initial_lag"
        if self.phase == "initial_lag" and frame > self.driver["reverse_frame"]:
            self.progress_sample("held_samples", owner, frame)
        if self.phase == "initial_lag" and len(self.driver["held_samples"]) == 3:
            check.require(self.driver_current["incoming_lag_min_ms"] == self.driver_current["incoming_lag_max_ms"]
                          == self.driver["initial_lag_ms"],
                          "原 Driver 未读到设定延迟")
            self.set_lag(0)
            self.phase = "initial_delivery"
        if self.phase == "initial_delivery" and all(v["step_source"] for v in self.live.values()):
            self.initial_sources = {side: copy.deepcopy(v["step_source"]) for side, v in self.live.items()}
            self.phase = "reverse"
        if self.phase == "reverse":
            if self.driver_current["incoming_lag_min_ms"] != 0 or self.driver_current["incoming_lag_max_ms"] != 0:
                return
            check.require(owner["current_step"] == authority["current_step"] == 0, "门差前原初段已结束")
            if len(self.driver["held_samples"]) == 3 and owner["attack_continuation_open"]:
                check.require(not authority["attack_continuation_open"], "未覆盖 owner 开门而 Authority 关门")
                self.driver["rejected_attempt"] = dict(owner_submission_frame=str(frame),
                    frame_domain="OwnerInputSubmissionGFrameCounter_NotInputEvaluation", **copy.deepcopy(self.live))
                self.press_attack("second")
                self.phase = "await_replay"
        if self.phase == "await_replay":
            log = check.facing_log_rows(LOG, self.log_offset)
            receives = [r for r in log["rows"] if r["kind"] == "Combat.PlayerCombo.CorrectionReceive"
                        and r["fields"].get("Accepted") == "0" and r["fields"].get("World") == path(self.endpoints["owner"]["world"])]
            if receives and owner["step_source"] and owner["current_step"] == 0:
                starts = check.facing_start_rows(log["rows"], owner["step_source"], 2)
                if starts:
                    check.require(authority["step_source"] == self.initial_sources["authority"], "重放替换了原 Authority 初段")
                    self.replayed_source = copy.deepcopy(owner["step_source"])
                    self.phase = "third_gate"
        if self.phase == "third_gate":
            check.require(owner["current_step"] == authority["current_step"] == 0, "重放后第三次输入门未覆盖")
            if owner["attack_continuation_open"] and authority["attack_continuation_open"] and "Attack" not in self.held:
                self.press_attack("third")
                self.phase = "final_step"
        if self.phase == "final_step" and owner["current_step"] == authority["current_step"] == 1:
            self.progress_sample("third_samples", owner, frame)
            if len(self.driver["third_samples"]) == 3 and "Attack" not in self.held:
                self.key("S", False)
                self.phase = "action"

    def progress_sample(self, name, facts, frame):
        record = facts["step_record"]
        samples = self.driver[name]
        if record and record["live_original_snapshot_available"] and record.get("section") == "Main" and len(samples) < 3:
            position = record["position_seconds"]
            if not samples or position > samples[-1]["position"]:
                samples.append(dict(read_gframe=str(frame), position=position))

    def inject_missing_initial(self):
        owner, authority = (self.endpoints[k] for k in ("owner", "authority"))
        cls = ue.load_class(None, "/Script/GGYGO.GGYGOMeleeTraceComponent")
        original = owner["pawn"].get_component_by_class(cls)
        remote = authority["pawn"].get_component_by_class(cls)
        check.require(original and remote and original != remote and original.get_owner() == owner["pawn"]
                      and remote.get_owner() == authority["pawn"], "缺初始数据故障没有原 Trace 配对")
        self.fault = dict(owner_trace=path(original), authority_trace=path(remote), frame=ue.SystemLibrary.get_frame_count())
        original.call_method("K2_DestroyComponent", args=(owner["pawn"],))
        check.require(not ue.SystemLibrary.is_valid(original) and owner["pawn"].get_component_by_class(cls) is None
                      and ue.SystemLibrary.is_valid(remote) and authority["pawn"].get_component_by_class(cls) == remote,
                      "故障注入未局限于原 owner Trace")
        self.fault["applied"] = True

    def owner_public(self):
        if not self.input:
            return None
        ep = self.endpoints["owner"]
        ability, instance = ue.AbilitySystemLibrary.get_gameplay_ability_from_spec_handle(ep["asc"], ep["spec"])
        active = bool(instance and ue.AbilitySystemLibrary.is_gameplay_ability_active(ability))
        tags = ue.GameplayTagLibrary.break_gameplay_tag_container(ue.get_default_object(ep["cls"]).get_editor_property("activation_owned_tags"))
        attacking = [tag for tag in tags if str(ue.GameplayTagLibrary.get_tag_name(tag)) == "State.Attacking"]
        check.require(len(attacking) == 1, "生产 Combo 缺唯一 State.Attacking Tag")
        count = ep["asc"].call_method("GetGameplayTagCount", args=(attacking[0],))
        motion = ep["move"].has_active_action_motion()
        montage = ep["anim"].get_current_active_montage()
        locomotion = ep["move"].get_locomotion_motion_type()
        locomotion_state = json.loads(ue.GGYGOPlayerActionObservation.read_locomotion_state(ep["move"]))
        step = ability.get_current_combo_step() if instance else None
        return dict(world=path(ep["world"]), pawn=path(ep["pawn"]), mesh=path(ep["mesh"]), asc=path(ep["asc"]),
            ability=path(ability), active=active, step=step, attacking=count, action_motion=motion, montage=path(montage),
            locomotion=locomotion_state,
            cleanup_verified=not active and count == 0 and not motion and montage is None
                and locomotion == ue.GGYGOLocomotionMotionType.NONE and step in (None, -1))

    def reacquire_authority(self):
        peer = self.peer.get("relevancy", {})
        old = peer.get("old")
        if old is None:
            return False
        ep = self.endpoints["authority"]
        current = json.loads(self.fx.read_network_fx_channel(ep["world"], old["viewer_player_id"], ep["pawn"]))
        check.require(current.get("connection_open"), "相关性试次连接中断")
        if "old" not in self.relevancy:
            if not current.get("channel_id"):
                return False
            active = self.active_fx()
            remote_active = self.peer.get("fx_active")
            if active is None or remote_active is None:
                return False
            if not check.fx_reached(remote_active):
                return False
            check.require(active["occurrence"] == remote_active["occurrence"]
                          and active["begin_server_time"] == remote_active["begin_server_time"], "丢失相关性前没有同键原活动 FX")
            check.require(all(current[k] == old[k] for k in ("viewer_player_id", "channel_index", "pawn_net_guid")),
                          "两端旧 ActorChannel 不匹配")
            check.require(current["pawn_relevant_to_viewer"] and current["viewer_distance_squared"] > 1
                          and current["net_cull_distance_squared"] > 1, "当前 Viewer 距离不足以构造相关性丢失")
            self.relevancy["old"] = current
            self.relevancy["authority_active"] = copy.deepcopy(active)
            self.cull_before = current["net_cull_distance_squared"]
            # 启动器通过原生进程内 Config 覆盖关闭等待；这里读同一个真实 NetDriver。
            self.relevancy["timeout"] = dict(actual=current["relevant_timeout"], source="process_ini_override")
            check.require(abs(self.relevancy["timeout"]["actual"] - 0.05) < 0.000001, "相关性等待配置未读回")
            self.channel_cursor = LOG.stat().st_size
            ep["pawn"].call_method("SetNetCullDistanceSquared", args=(1.0,))
            ep["pawn"].force_net_update()
            narrowed = json.loads(self.fx.read_network_fx_channel(ep["world"], old["viewer_player_id"], ep["pawn"]))
            check.require(narrowed["pawn_relevant_to_viewer"] is False, "原 Pawn 裁剪刺激未生效")
            self.relevancy["narrowed"] = narrowed
            return False
        check.require(all(current[k] == self.relevancy["old"][k] for k in ("world", "connection_id", "pawn_id", "pawn_net_guid")),
                      "相关性丢失期间 Authority 连接或 Pawn 换代")
        if "close" not in self.relevancy:
            self.channel_cursor, event = check.read_fx_channel_event(LOG, self.channel_cursor,
                self.relevancy["old"], cleanup=False)
            if event:
                self.relevancy["close"] = event
        # Authority 原通道已真正关闭后即可恢复范围；Client 仍独立核 CleanUp、旧资源退役与新代理。
        # 不为脚本跨进程回执额外延迟原生重开，避免错过生产 FX 的短可见区间。
        lost = bool(self.relevancy.get("close") and current.get("actor_channel_absent"))
        if lost and self.cull_before is not None:
            check.require(self.active_fx() is not None, "原 FX 已闭窗，重获剩余 Age 未覆盖")
            self.restore_cull()
        if self.cull_before is None and "close" in self.relevancy and current.get("channel_id"):
            self.relevancy["new"] = current
        return lost

    def reacquire_observer(self):
        self.sample_network_fx()
        ep = self.endpoints["observer"]
        current = json.loads(self.network_fx.read_network_fx_channel(ep["world"], self.viewer_id, None))
        old = self.relevancy["old"]
        check.require(current.get("connection_open") and all(current[k] == old[k]
                      for k in ("world", "connection_id", "viewer_player_id")), "重获期间原客户端连接换代")
        if "cleanup" not in self.relevancy:
            self.channel_cursor, event = check.read_fx_channel_event(LOG, self.channel_cursor, old, cleanup=True)
            if event:
                self.relevancy["cleanup"] = event
        if "cleanup" in self.relevancy and not ue.SystemLibrary.is_valid(self.old_proxy):
            self.relevancy.setdefault("retired", dict(retired_frame=current["observed_frame"], old_proxy_id=old["pawn_id"]))
        active = self.peer.get("relevancy", {}).get("authority_active")
        if active is None or "retired" not in self.relevancy:
            return
        pawn = player_pawn(ep["world"], self.player_id)
        new = endpoint(pawn, 1)
        if not new:
            return
        channel = json.loads(self.network_fx.read_network_fx_channel(ep["world"], self.viewer_id, pawn))
        if not channel.get("channel_id"):
            return
        self.relevancy["new_candidate"] = channel
        check.require(channel["pawn_net_guid"] == old["pawn_net_guid"] and channel["pawn_id"] != old["pawn_id"],
                      "没有同 NetGUID 的新 Proxy")
        # UE 默认复用 ActorChannel UObject；以原 Close/CleanUp 后的新 ProcessBunch 证明重开。
        self.channel_cursor, created = check.read_fx_channel_event(LOG, self.channel_cursor,
            channel, cleanup=False, creation=True)
        if not created:
            return
        self.relevancy["creation"] = created
        self.relevancy["new"] = channel
        self.join_record = copy.deepcopy(active)
        self.endpoints["observer"] = new
        self.begin_sampling()

    def restore_cull(self):
        if self.cull_before is not None:
            pawn = self.endpoints["authority"]["pawn"]
            pawn.call_method("SetNetCullDistanceSquared", args=(self.cull_before,))
            pawn.force_net_update()
            check.require(pawn.call_method("GetNetCullDistanceSquared") == self.cull_before, "原 Pawn 裁剪距离未恢复")
            self.relevancy["cull_restored"] = self.cull_before
            self.cull_before = None

    def place_observer_camera(self, world, pc, anchor):
        """只在本次客户端 PIE 设置侧面观察机位，保留生产角色和 FX。"""
        if self.camera:
            check.require(pc.get_view_target() == self.camera, "观察机位被后续初始化替换")
            return ue.SystemLibrary.get_frame_count() > self.camera_record["set_frame"] + 3
        library = ue.get_default_object(ue.load_class(None, "/Script/Engine.SubsystemBlueprintLibrary"))
        sub = library.call_method("GetLocalPlayerSubSystemFromPlayerController",
            args=(pc, ue.EnhancedInputLocalPlayerSubsystem.static_class()))
        ready = ue.GGYGOPlayerInputBridgeLibrary.read_local_player_input_assembly(world, sub.get_outer())
        if isinstance(ready, tuple) and ready[0] == ue.GGYGOPlayerInputAssemblyStatus.WAITING:
            return False
        input_ops.pin_ready_assembly(ue, world, sub.get_outer())
        origin = ue.Vector(*anchor)
        location = origin + ue.Vector(0, -900, 350)
        rotation = ue.MathLibrary.find_look_at_rotation(location, origin + ue.Vector(150, 0, 80))
        transform = ue.Transform()
        transform.translation, transform.rotation = location, rotation.quaternion()
        gameplay = ue.GameplayStatics.get_default_object()
        self.camera = gameplay.call_method("BeginDeferredActorSpawnFromClass", args=(world,
            ue.CameraActor.static_class(), transform, ue.SpawnActorCollisionHandlingMethod.ALWAYS_SPAWN,
            None, ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        gameplay.call_method("FinishSpawningActor", args=(self.camera, transform, ue.SpawnActorScaleMethod.MULTIPLY_WITH_ROOT))
        self.camera.get_component_by_class(ue.CameraComponent).set_field_of_view(80)
        pc.set_view_target_with_blend(self.camera, 0.0)
        check.require(pc.get_view_target() == self.camera, "客户端观察机位未实际选中")
        self.camera_record = dict(actor=path(self.camera), world=path(world), anchor=anchor,
                                  location=[location.x, location.y, location.z], fov=80,
                                  set_frame=ue.SystemLibrary.get_frame_count())
        return False

    def observe_fx_trial(self):
        if CASE == "reacquire" and self.join_record is None:
            return
        if self.visual_fx and not self.camera_framed_fx:
            ep = self.endpoints["observer"]
            origin = ep["pawn"].get_actor_location()
            location = origin + ue.Vector(0, -900, 350)
            rotation = ue.MathLibrary.find_look_at_rotation(location, origin + ue.Vector(150, 0, 80))
            camera = self.camera.get_component_by_class(ue.CameraComponent)
            camera.set_world_location_and_rotation(location, rotation, False, False)
            self.camera_record["fx_anchor"] = [origin.x, origin.y, origin.z]
            self.camera_record["fx_frame"] = ue.SystemLibrary.get_frame_count()
            self.camera_framed_fx = True
        closed = CASE == "closed_first"
        witness = check.fx_replication_witness(self.network_fx_state, self.join_record, closed=closed)
        ready = check.fx_closed_rows(self.fx_state["records"], self.join_record) if closed \
            else check.fx_live_rows(self.fx_state["records"], self.join_record)
        if TAIL_PROBE:
            if witness:
                self.observe_tail_probe(ready)
            return
        # 在可见点前两原生步长预约 Draw，给读回留出下一帧；过早入场不耗尽有限图片数。
        # 验收仍逐张要求真实 Draw 的 Age 落入可见区间，不以请求帧或相邻帧代替。
        samples = [check.fx_viewport_witness(CASE, self.fx_state, self.join_record, image["native"])
                   for image in self.images if not image["native"]["error"]]
        matched = any(row and (not self.visual_fx or row["controller_age"] >= self.visual_fx["minimum_age"])
                      for row in samples)
        count = len(self.images) + len(self.pending_images)
        near_visible = not self.visual_fx or (ready and ready[-1]["target_age"]
                        >= self.visual_fx["minimum_age"] - 2 * ready[-1]["effective_step"])
        if witness and ready and not matched and count < (1 if closed else 8) \
                and near_visible and (closed or self.active_fx()):
            self.capture()
        if self.images and not self.pending_images and self.peer.get("phase") == "authority_done":
            self.phase = "captured"
            self.finish()
        elif not closed and not self.capture_requested and self.peer.get("fx_closed"):
            raise RuntimeError("窗口关闭前未取得远端真实进度及视口，本试次未覆盖")

    def observe_tail_probe(self, ready):
        """只缩小原实例的公开 seek CPU 预算，观察真实隐藏、正常闭窗、原生活尾及自然销毁。"""
        if self.tail_probe is None:
            if not ready:
                return
            row = ready[-1]
            self.tail_component = ue.find_object(None, row["component"])
            check.require(ue.SystemLibrary.is_valid(self.tail_component), "专项原组件已失效")
            original = self.tail_component.get_max_sim_time()
            self.tail_component.set_max_sim_time(0.000001)
            actual = self.tail_component.get_max_sim_time()
            check.require(0 < actual < original, "原 seek CPU 预算未实际缩小")
            self.tail_probe = dict(start=copy.deepcopy(row), original_budget=original, applied_budget=actual,
                                   applied_frame=str(ue.SystemLibrary.get_frame_count()))
        probe = self.tail_probe
        rows = [r for r in self.fx_state["records"] if r["component_id"] == probe["start"]["component_id"]]
        hidden = [r for r in rows if int(r["native_event_frame"]) > int(probe["applied_frame"])
                  and r["reached"] and not r["rendering_enabled"] and r["active_record"]]
        if hidden:
            probe.setdefault("hidden", copy.deepcopy(hidden[0]))
        tails = [r for r in rows if "hidden" in probe and r["kind"] == "TailTransferred"
                 and int(r["native_event_frame"]) > int(probe["hidden"]["native_event_frame"])]
        if tails:
            probe.setdefault("tail", copy.deepcopy(tails[0]))
            if ue.SystemLibrary.is_valid(self.tail_component):
                probe["tail_native_tick_mode"] = self.tail_component.get_age_update_mode() == ue.NiagaraAgeUpdateMode.TICK_DELTA_TIME
            if len(self.images) + len(self.pending_images) < 8 and rows[-1]["controller_valid"] \
                    and not rows[-1]["controller_complete"]:
                self.capture()
        complete = any(r["kind"] == "NaturalCompleted" for r in rows)
        destroyed = any(r["kind"] == "ComponentDestroyed" for r in rows)
        if self.peer.get("phase") == "authority_done" and complete and destroyed:
            check.require("hidden" in probe and tails and self.images, "未覆盖再次追赶隐藏到有效活尾绘制")
            if not self.pending_images:
                self.phase = "captured"
                self.finish()

    def capture(self):
        self.capture_requested = True
        if self.camera:
            check.require(local_pc(self.endpoints["observer"]["world"]).get_view_target() == self.camera,
                          "截图时原观察机位已被替换")
        ordinal = len(self.images) + len(self.pending_images)
        filename = self.folder / ("client.png" if ordinal == 0 else "client_" + str(ordinal) + ".png")
        task = ue.GGYGOViewportReadbackLibrary.begin_game_viewport_readback_to_file(
            self.endpoints["observer"]["world"], str(filename), 0)
        self.pending_images.append(dict(task=task, file=filename))

    def poll_images(self):
        for item in list(self.pending_images):
            result = item["task"].read_result()
            if result.status not in (ue.GGYGOViewportReadbackStatus.COMPLETE,
                                     ue.GGYGOViewportReadbackStatus.FAILED, ue.GGYGOViewportReadbackStatus.CANCELLED):
                continue
            item["task"].release()
            self.pending_images.remove(item)
            names = ("world_path", "world_object_id", "game_viewport_client_path", "game_viewport_client_object_id",
                     "viewport_identity", "pie_instance", "world_type", "net_mode", "request_frame",
                     "render_callback_frame", "readback_complete_frame", "render_target_format", "hdr",
                     "player_view_only", "player_view_json", "output_file_size_bytes", "file_write_complete",
                     "file_readback_verified", "resources_released", "error")
            self.images.append(dict(file=str(item["file"]), status=str(result.status),
                native=dict(world_context_handle=str(result.world_context_handle),
                            **{name: getattr(result, name) for name in names})))

    def finish(self):
        if self.state == "ending":
            return
        self.state = "ending"
        self.finish_started = time.monotonic()
        cleanup_errors = []
        if self.tail_probe and ue.SystemLibrary.is_valid(self.tail_component):
            self.tail_component.set_max_sim_time(self.tail_probe["original_budget"])
        for request in self.preparations.values():
            if ue.SystemLibrary.is_valid(request) \
                    and request.get_state() == ue.GGYGONiagaraMaterialPreparationState.PENDING:
                request.cancel()
        try:
            self.restore_cull()
        except Exception as error:
            cleanup_errors.append(str(error))
        for name in tuple(self.held):
            try:
                self.key(name, False)
            except Exception as error:
                cleanup_errors.append(str(error))
        if self.driver_changed and self.driver_original:
            try:
                original = self.driver_original
                ue.SystemLibrary.execute_console_command(self.endpoints["authority"]["world"],
                    "NET " + original["driver_name"] + " PktIncomingLagMin=" + str(original["incoming_lag_min_ms"])
                    + " PktIncomingLagMax=" + str(original["incoming_lag_max_ms"]))
            except Exception as error:
                cleanup_errors.append(str(error))
        for key, obj in self.actions.items():
            obj.stop_observation()
            self.action_states[key] = read_final(obj.get_observation_json, self.action_states.get(key))
        if self.fx:
            self.fx.stop_observation()
            self.fx_state = read_final(self.fx.get_observation_json, self.fx_state)
        if self.network_fx:
            self.network_fx.stop_observation()
            self.network_fx_state = read_final(self.network_fx.get_network_fx_observation_json, self.network_fx_state)
        if self.pose_owned:
            self.pose.stop_observation()
            self.pose_owned = False
        # 截点前一次性写出本试次日志；逐行强制刷盘会使密集网络日志阻塞 PIE 收尾。
        ue.log_flush()
        save(self.folder / "observations.json", dict(case=CASE, role=ROLE, error=self.error,
            phase=self.phase, cleanup_errors=cleanup_errors, input_events=self.events, direction_driver=self.driver,
            actions=[dict(key=list(key), state=value) for key, value in self.action_states.items()],
            pose=dict(metadata=self.pose_meta, records=self.pose_rows), arm=self.arm, fx=self.fx_state,
            clocks=self.clock_rows,
            editor_slate_throttling=self.editor_slate_throttling,
            viewport_sizes=self.viewport_sizes,
            resource_preparation=list(self.preparation_records.values()),
            tail_seek_probe=self.tail_probe,
            fault=getattr(self, "fault", None), images=self.images, camera=self.camera_record,
            visual_fx=self.visual_fx, log_offset=self.log_offset,
            log_path=str(LOG), log_end=LOG.stat().st_size,
            network_fx=self.network_fx_state, join_record=self.join_record, relevancy=self.relevancy,
            old_fx=self.old_fx_state,
            owner_public=self.owner_public(),
            bindings=[dict(key=list(key), slot=str(ue.get_default_object(self.endpoints[key[0]]["cls"])
                .get_editor_property("combo_steps")[key[1]].get_editor_property("motion_slot_name")),
                main=str(ue.get_default_object(self.endpoints[key[0]]["cls"])
                .get_editor_property("combo_steps")[key[1]].get_editor_property("main_section"))) for key in self.actions],
            driver_original=self.driver_original, driver_last=self.driver_current,
            owner_endpoint={k: path(getattr(self.input, attr)) for k, attr in
                (("world", "world"), ("pc", "player_controller"), ("pawn", "pawn"), ("player_input", "player_input"))}
                if self.input else None))
        self.publish()
        self.les.editor_request_end_play()


ue._minimal_multiplayer_run = Run()
