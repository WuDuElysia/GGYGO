"""@file create_pyrios_evade_montages.py
@brief 仅生成两个完整原源、FullBody、单 Default section 的 Pyrios Montage。

独立完整 Editor：-ExecutePythonScript="本文件 --mode preflight --output <新Saved目录>"
create 必须提供成功的 preflight readback.json；cold 必须提供成功的 create
readback.json，且使用新 PID。--case front/back/both 支持统筹分件执行。
--exit-editor 仅用于命令行明确运行本文件的自有宿主，退出前必须无 dirty。

只保存两件新 Montage；同名包已存在则拒绝 create，失败不删除或覆盖产物。
Default 覆盖完整源及恢复尾段，StartSection=FinalSection=Default。源 AS、
Skeleton、GA、输入、CMC 与地图只读。FX 窗口是明确的项目测试基线，不能
当作原作 cue、取消点、无敌窗口、生产衔接或真实位移已经通过的证据。
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import struct

import unreal as ue


PROJECT = Path("F:/ue_project/GGYGO").resolve()
BASE = "/Game/Characters/Player/Pyrios/Animation/"
SKELETON = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model_Skeleton"
CASES = {
    "front": (BASE + "Avatar_Male_Size03_Pyrois_Ani_Evade_Front_01",
              BASE + "Evade/AM_Pyrios_Evade_Front_01", 371),
    "back": (BASE + "Avatar_Male_Size03_Pyrois_Ani_Evade_Back_01",
             BASE + "Evade/AM_Pyrios_Evade_Back_01", 303),
}
SCHEMA = "PyriosEvadeMontages/v1"
META_KEY = "GGYGO.EvadeMontage.ProjectContract"
SLOT = "FullBody"
SECTION = "Default"
FX_TRACK = "FXWindow"
FX_BEGIN = "Event.Montage.FXWindowBegin"
FX_END = "Event.Montage.FXWindowEnd"
WINDOW_CLASS = "/Script/GGYGO.GGYGOAnimNotifyState_GameplayEventWindow"
# UE 5.8 的该 enum 未声明 BlueprintType；实际可编辑字段是 uint8。
NO_MERGE_FLAG = 1  # EAnimNotifyStateBehaviorFlags::NoMergeOnConcurrentPlay
PROTECTED = (
    "Config/DefaultEditor.ini", "Content/AI/Boss/Test/BB_Boss_Test.uasset",
    "Content/AI/Boss/Test/BT_Boss_Test.uasset", "Content/BP/Character/Player/BP_PC_Pyrios.uasset",
    "Content/Characters/Shared/Abilities/GA_Dodge.uasset",
    "Saved/Autosaves/Game/Characters/Shared/Abilities/GA_Dodge_Auto2.uasset",
    "Content/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo.uasset",
    "Content/Map/L_Movement_Test.umap", "Content/Map/BH3/L_KevinBoss_P3.umap",
    "Content/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model.uasset",
)


def require(condition, reason):
    if not condition:
        raise RuntimeError("Animation.EvadeMontage: " + reason)


def f32(value):
    return struct.unpack("<f", struct.pack("<f", value))[0]


def disk(package):
    require(package.startswith("/Game/"), "不是项目包：" + package)
    return PROJECT / ("Content/" + package.removeprefix("/Game/") + ".uasset")


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def dirty():
    lib = ue.EditorLoadingAndSavingUtils
    return {"content": sorted(p.get_path_name() for p in lib.get_dirty_content_packages()),
            "maps": sorted(p.get_path_name() for p in lib.get_dirty_map_packages())}


def root_arrays(text, property_name):
    """只读 stock T3D 的根对象数组记录；不把子对象同名属性算入资产。"""
    depth, roots, result = 0, 0, {}
    for line in text.splitlines():
        if re.match(r"^\s*Begin Object\b", line):
            if depth == 0:
                roots += 1
            depth += 1
        elif re.match(r"^\s*End Object\s*$", line):
            depth -= 1
            require(depth >= 0, "原生 T3D 对象层级不平衡")
        elif depth == 1:
            match = re.match(r"^\s*" + re.escape(property_name) + r"\((\d+)\)=(.*)$", line)
            if match:
                index = int(match.group(1))
                require(index not in result, "重复根属性：" + property_name)
                result[index] = match.group(2)
    require(depth == 0 and roots == 1, "原生 T3D 必须有一个完整根对象")
    require(sorted(result) == list(range(len(result))), "原生数组下标不连续：" + property_name)
    return [result[index] for index in range(len(result))]


def native_export(asset, filename):
    require(not filename.exists(), "拒绝覆盖原生读回：" + str(filename))
    task = ue.AssetExportTask()
    for name, value in (("object", asset), ("exporter", ue.ObjectExporterT3D()),
                        ("filename", str(filename)), ("automated", True),
                        ("prompt", False), ("replace_identical", False)):
        task.set_editor_property(name, value)
    require(ue.Exporter.run_asset_export_task(task) and filename.is_file(),
            "原生 T3D 导出失败：" + asset.get_path_name())
    text = filename.read_text(encoding="utf-8-sig")
    expected = '^Begin Object Class=' + re.escape(asset.get_class().get_path_name())
    require(re.search(expected + ' Name="' + re.escape(asset.get_name()) + '"', text),
            "T3D 根对象不是目标资产：" + asset.get_path_name())
    return text


def skeleton_slots(text):
    result = []
    for row in root_arrays(text, "SlotGroups"):
        groups = re.findall(r'(?:^|[,\(])GroupName="([^"]+)"', row)
        require(len(groups) <= 1, "Skeleton SlotGroup 名称不明确")
        # FAnimSlotGroup 构造器 GroupName=DefaultGroup；stock 导出会省略相同值。
        group = groups[0] if groups else "DefaultGroup"
        match = re.search(r'(?:^|[,\(])SlotNames=\(([^()]*)\)', row)
        require(match is not None, "Skeleton SlotNames 原生数组不可读")
        names = re.findall(r'"([^"]+)"', match.group(1))
        require(names and re.sub(r'"[^"]+"|,|\s', "", match.group(1)) == "",
                "Skeleton SlotNames 含非预期值")
        result.append({"group": group, "slots": names})
    require(sum(row["slots"].count(SLOT) for row in result) == 1,
            "原 Skeleton 必须已经唯一注册 FullBody；本工具不注册 Slot")
    return result


def default_section(montage, text):
    require(montage.get_num_sections() == 1 and str(montage.get_section_name(0)) == SECTION,
            "必须是唯一 stock Default section：" + montage.get_path_name())
    rows = root_arrays(text, "CompositeSections")
    require(len(rows) == 1, "原生 section 记录不是单 Default")
    row = rows[0]
    require(re.search(r'(?:^|[,\(])SectionName="Default"(?:[,\)])', row), "原生 Default 名称不符")
    next_names = re.findall(r'(?:^|[,\(])NextSectionName=([^,\)]+)', row)
    require(not next_names or next_names == ['"None"'] or next_names == ["None"],
            "Default 必须自然终止；不可自循环或跳转")
    # FCompositeSection NextSectionName 构造值为 NAME_None。其 link base 与
    # AnimNotifyEvent 相同，通过新建原生公开 struct 读取真正的省略字段默认值。
    defaults = ue.AnimNotifyEvent().export_text()
    values = {}
    for name in ("LinkMethod", "LinkValue"):
        pattern = r"(?:^|[,\(])" + name + r"=([^,\)]+)(?:[,\)])"
        actual = re.findall(pattern, row)
        if actual:
            require(len(actual) == 1, "Default link 字段不明确：" + name)
            values[name] = actual[0]
        else:
            native_defaults = re.findall(pattern, defaults)
            require(native_defaults, "原生 link 构造值不可读：" + name)
            values[name] = native_defaults[-1]
    require(values["LinkMethod"] == "Absolute" and float(values["LinkValue"]) == 0.0,
            "Default 必须从原生绝对时间 0 开始")
    return {"name": SECTION, "start": 0.0, "next": "None"}


def tag(name):
    value = ue.GameplayTag()
    value.import_text('(TagName="' + name + '")')
    require(ue.GameplayTagLibrary.is_gameplay_tag_valid(value)
            and str(ue.GameplayTagLibrary.get_tag_name(value)) == name, "原生 GameplayTag 未注册：" + name)
    return value


def model_of(montage):
    # DataModelInterface 为 VisibleAnywhere / BlueprintReadOnly。冷加载时
    # transient Controller 可合法未创建；只读不要求也不创建 controller。
    model = montage.get_editor_property("data_model_interface")
    require(model is not None, "Montage 原生 model 缺失：" + montage.get_path_name())
    for method in ("get_frame_rate", "get_number_of_frames", "get_play_length"):
        require(callable(getattr(model, method, None)), "原生 SDK 必需接口缺失：" + method)
    return model


def model_snapshot(montage):
    model = model_of(montage)
    rate = model.get_frame_rate()
    return {"numerator": int(rate.numerator), "denominator": int(rate.denominator),
            "frames": int(model.get_number_of_frames()), "length": float(model.get_play_length())}


def align_model(montage, source):
    # 新对象构造器创建 controller；GetController() 未反射，不假设其
    # Python 方法存在，也不直接写受保护的 SequenceLength。
    controller = montage.get_editor_property("controller")
    require(controller is not None, "新 Montage 原生 controller 缺失：" + montage.get_path_name())
    for method in ("set_frame_rate", "set_number_of_frames"):
        require(callable(getattr(controller, method, None)), "原生 SDK 必需接口缺失：" + method)
    controller.set_frame_rate(ue.FrameRate(numerator=source["numerator"], denominator=source["denominator"]), False)
    controller.set_number_of_frames(ue.FrameNumber(value=source["frames"]), False)
    model = model_snapshot(montage)
    require((model["numerator"], model["denominator"], model["frames"]) ==
            (source["numerator"], source["denominator"], source["frames"])
            and f32(model["length"]) == source["length"] and montage.get_play_length() == source["length"],
            "原生 DataModel 帧域/完整末端未对齐；拒绝截尾或保存后碰运气")


def author_settings(args, source):
    interval = source["denominator"] / source["numerator"]
    begin = f32(interval if args.fx_begin is None else args.fx_begin)
    end = source["length"] if args.fx_end is None else f32(args.fx_end)
    require(math.isfinite(begin) and math.isfinite(end) and 0 < begin < end <= source["length"],
            "FX 项目开始窗必须在完整源内，且起点为真实播放后的正时间")
    duration = f32(end - begin)
    trigger = f32(interval / args.requested_play_rate)
    require(duration > 0 and f32(begin + duration) == end,
            "FX float32 起止不能准确表达所给终点；拒绝移动窗口末端")
    require(math.isfinite(trigger) and 0 < trigger < source["length"] / args.requested_play_rate,
            "末帧 blend trigger 不可表示或覆盖完整动作")
    return {"requested_play_rate": args.requested_play_rate, "blend_in": f32(args.blend_in),
            "blend_out": f32(args.blend_out), "blend_out_trigger": trigger,
            "fx_begin": begin, "fx_end": end, "fx_duration": duration}


def configure(montage, settings):
    tracks = montage.get_editor_property("slot_anim_tracks")
    require(len(tracks) == 1, "factory 没有产生唯一 track")
    tracks[0].set_editor_property("slot_name", SLOT)
    montage.set_editor_property("slot_anim_tracks", tracks)
    for property_name in ("blend_in", "blend_out"):
        blend = montage.get_editor_property(property_name)
        blend.set_editor_property("blend_time", settings[property_name])
        blend.set_editor_property("blend_option", ue.AlphaBlendOption.HERMITE_CUBIC)
        montage.set_editor_property(property_name, blend)
    for name, value in (("rate_scale", 1.0), ("loop", False), ("enable_auto_blend_out", True),
                        ("blend_out_trigger_time", settings["blend_out_trigger"])):
        montage.set_editor_property(name, value)
    require(not ue.AnimationLibrary.get_animation_notify_events(montage), "factory 新 Montage 已含非预期 Notify")
    ue.AnimationLibrary.add_animation_notify_track(montage, FX_TRACK)
    window = ue.AnimationLibrary.add_animation_notify_state_event(
        montage, FX_TRACK, settings["fx_begin"], settings["fx_duration"], ue.GGYGOAnimNotifyState_GameplayEventWindow)
    require(window is not None and window.get_outer() == montage, "原生 FXWindow 创建/outer 失败")
    window.set_editor_property("begin_event_tag", tag(FX_BEGIN))
    window.set_editor_property("end_event_tag", tag(FX_END))
    window.set_editor_property("notify_state_behavior_flags", NO_MERGE_FLAG)


def window_snapshot(montage, settings):
    events = ue.AnimationLibrary.get_animation_notify_events(montage)
    require(len(events) == 1, "必须只有唯一项目 FXWindow，不混入 Hit/Combo/CancelPoint")
    event = events[0]
    window = event.get_editor_property("notify_state_class")
    require(event.get_editor_property("notify") is None and window is not None
            and window.get_class().get_path_name() == WINDOW_CLASS and window.get_outer() == montage,
            "FXWindow 原生类型/归属不符")
    require(window.get_editor_property("begin_event_tag").export_text() == tag(FX_BEGIN).export_text()
            and window.get_editor_property("end_event_tag").export_text() == tag(FX_END).export_text()
            and int(window.get_editor_property("notify_state_behavior_flags")) == NO_MERGE_FLAG, "FXWindow tag/NoMerge 不符")
    require(event.get_editor_property("montage_tick_type") == ue.MontageNotifyTickType.QUEUED,
            "FXWindow 必须为原生 Queued")
    start = float(ue.AnimationLibrary.get_anim_notify_event_trigger_time(event))
    duration = float(ue.AnimationLibrary.get_anim_notify_event_duration(event))
    require(start == settings["fx_begin"] and duration == settings["fx_duration"], "FXWindow 真实起点/时长不符")
    exported = event.export_text()
    guid = re.search(r"(?:^|[,\(])Guid=([0-9A-Fa-f]{32})(?:[,\)])", exported)
    require(guid is not None and int(guid.group(1), 16) != 0, "FXWindow 没有有效原生 GUID")
    links = re.findall(r'LinkedMontage=("[^"]*"|None)', exported)
    require(len(links) == 2 and all("'" + montage.get_path_name() + "'" in value for value in links),
            "FXWindow 起止 link 未同时绑定本 Montage")
    require(re.findall(r"(?:^|[,\(])LinkMethod=([^,\)]+)", exported) == ["Absolute", "Absolute"],
            "FXWindow 起止必须为实际 absolute link")
    track_names = [str(name) for name in ue.AnimationLibrary.get_animation_notify_track_names(montage)]
    # TrackIndex 只有 UPROPERTY()，不可假设 Python editor property 可读。
    track = re.search(r"(?:^|[,\(])TrackIndex=(\d+)(?:[,\)])", exported)
    require(track is not None, "FXWindow 原生 TrackIndex 不可读")
    track_index = int(track.group(1))
    require(0 <= track_index < len(track_names) and track_names[track_index] == FX_TRACK, "FXWindow 原生 track 不符")
    return {"guid": guid.group(1).upper(), "start": start, "duration": duration,
            "begin": FX_BEGIN, "end": FX_END, "queued": True, "no_merge": True,
            "native_export": exported}


def montage_snapshot(montage, sequence, source, settings, contract, filename):
    require(isinstance(montage, ue.AnimMontage) and montage.get_editor_property("skeleton") ==
            sequence.get_editor_property("skeleton"), "Montage / 原 Skeleton 身份不符")
    tracks = montage.get_editor_property("slot_anim_tracks")
    require(len(tracks) == 1 and str(tracks[0].get_editor_property("slot_name")) == SLOT, "必须为唯一 FullBody track")
    segments = tracks[0].get_editor_property("anim_track").get_editor_property("anim_segments")
    require(len(segments) == 1 and segments[0].get_editor_property("anim_reference") == sequence,
            "必须是单个原 AS，不允许派生/嵌套/替代源")
    segment = segments[0]
    values = {name: segment.get_editor_property(name) for name in
              ("start_pos", "anim_start_time", "anim_end_time", "anim_play_rate", "looping_count", "cached_play_length")}
    require(values == {"start_pos": 0.0, "anim_start_time": 0.0, "anim_end_time": source["length"],
                       "anim_play_rate": 1.0, "looping_count": 1, "cached_play_length": source["length"]},
            "原单 segment 未覆盖完整源/缓存时长或速率不符")
    require(montage.get_play_length() == source["length"] and montage.get_editor_property("rate_scale") == 1.0
            and not montage.get_editor_property("loop") and montage.get_editor_property("enable_auto_blend_out")
            and montage.get_editor_property("blend_out_trigger_time") == settings["blend_out_trigger"],
            "Montage 完整长度/正向速率/自然 blend 末区间不符")
    for name in ("blend_in", "blend_out"):
        blend = montage.get_editor_property(name)
        require(blend.get_editor_property("blend_time") == settings[name]
                and blend.get_editor_property("blend_option") == ue.AlphaBlendOption.HERMITE_CUBIC, "Montage blend 不符：" + name)
    require(ue.EditorAssetLibrary.get_metadata_tag(montage, META_KEY) == contract, "项目基线来源 metadata 不符")
    model = model_snapshot(montage)
    rate = montage.get_editor_property("common_target_frame_rate")
    common = {"numerator": int(rate.numerator), "denominator": int(rate.denominator)}
    require((model["numerator"], model["denominator"], model["frames"]) ==
            (source["numerator"], source["denominator"], source["frames"])
            and f32(model["length"]) == source["length"]
            and (common["numerator"], common["denominator"]) == (source["numerator"], source["denominator"]),
            "Montage model / CommonTarget 帧域不符，不能证明完整源末端映射")
    text = native_export(montage, filename)
    return {"path": montage.get_path_name(), "source": sequence.get_path_name(), "slot": SLOT,
            "segment": values, "model": model, "common_target": common, "section": default_section(montage, text),
            "fx": window_snapshot(montage, settings), "contract": contract}


def editor_state():
    editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
    actors = ue.get_editor_subsystem(ue.EditorActorSubsystem)
    world = editor.get_editor_world()
    require(world is not None and world.get_path_name() == "/Game/Map/L_Movement_Test.L_Movement_Test"
            and editor.get_game_world() is None, "要求独立非 PIE 的 L_Movement_Test 完整 Editor")
    camera = editor.get_level_viewport_camera_info()
    require(camera is not None, "原 Editor 相机不可读")
    p, r = camera
    return {"world": world.get_path_name(), "camera": [p.x, p.y, p.z, r.pitch, r.yaw, r.roll],
            "actors": sorted(a.get_path_name() for a in actors.get_all_level_actors()),
            "selection": sorted(a.get_path_name() for a in actors.get_selected_level_actors())}


def run(args):
    output = Path(args.output)
    require(output.is_absolute(), "output 必须为绝对路径")
    output = output.resolve()
    require(output.is_relative_to(PROJECT / "Saved") and not output.exists(), "output 必须为未存在的项目 Saved 目录")
    output.mkdir(parents=True, exist_ok=False)
    report = {"schema": SCHEMA, "mode": args.mode, "pid": os.getpid(), "success": False,
              "tool_sha256": digest(Path(__file__)), "engine_version": ue.SystemLibrary.get_engine_version(),
              "phase": "preflight", "errors": [], "assets": {}, "saved_packages": [],
              "settings": {name: getattr(args, name) for name in
                           ("case", "blend_in", "blend_out", "requested_play_rate", "fx_begin", "fx_end")},
              "start_section": SECTION, "final_section": SECTION, "project_test_only": True,
              "original_game_timing_known": False, "production_playback_verified": False,
              "world_motion_proof": False, "idle_blend_verified": False}
    protected, skeleton, skeleton_text, original_state, sources = [], None, None, None, {}
    try:
        require(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() == PROJECT, "原生项目路径不符")
        require(not re.search(r"(?:^|\s)-run=", ue.SystemLibrary.get_command_line(), re.I), "不支持 commandlet 宿主")
        require(ue.SystemLibrary.get_engine_version().startswith("5.8."), "原生构造/导出合同限定 UE 5.8")
        for name in ("blend_in", "blend_out", "requested_play_rate"):
            value = getattr(args, name)
            require(math.isfinite(value) and value > 0 and math.isfinite(f32(value)) and f32(value) > 0,
                    "必需参数不是可表示的有限正值：" + name)
        if args.exit_editor:
            command = ue.SystemLibrary.get_command_line().replace("\\", "/").casefold()
            require(str(Path(__file__).resolve()).replace("\\", "/").casefold() in command,
                    "exit-editor 要求本文件明确出现在自有宿主命令行")
        original_state = editor_state()
        report["dirty_before"] = dirty()
        require(report["dirty_before"] == {"content": [], "maps": []}, "存在原 dirty 包，拒绝作者操作")
        selected = list(CASES) if args.case == "both" else [args.case]
        protected = [PROJECT / path for path in PROTECTED] + [disk(SKELETON)]
        protected += [disk(row[0]) for row in CASES.values()]
        report["protected_before"] = {str(path): digest(path) for path in protected}
        prior = None
        if args.mode != "preflight":
            require(args.baseline is not None, "create/cold 必须提供上一成功阶段的 baseline")
            prior = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
            require(prior.get("schema") == SCHEMA and prior.get("success") is True
                    and prior.get("mode") == ("preflight" if args.mode == "create" else "create")
                    and prior.get("settings") == report["settings"]
                    and prior.get("tool_sha256") == report["tool_sha256"]
                    and prior.get("engine_version") == report["engine_version"], "baseline 阶段/工具/宿主/设置不匹配")
            require(prior["protected_after"] == report["protected_before"], "保护文件不同于前一阶段")
            if args.mode == "cold":
                require(prior["pid"] != report["pid"], "cold 必须使用新 PID")
        else:
            require(args.baseline is None, "preflight 不接受 baseline")
        skeleton = ue.load_asset(SKELETON)
        require(isinstance(skeleton, ue.Skeleton) and skeleton.get_path_name() ==
                SKELETON + "." + SKELETON.rsplit("/", 1)[1], "原 Skeleton 无效或被 redirect")
        skeleton_text = native_export(skeleton, output / "skeleton_before.t3d")
        report["skeleton_slots"] = skeleton_slots(skeleton_text)
        for key in selected:
            package, target, expected_frames = CASES[key]
            if args.mode == "cold":
                require(disk(target).is_file(), "cold 目标包不存在：" + target)
            else:
                require(not disk(target).exists() and not ue.EditorAssetLibrary.does_asset_exist(target),
                        "create-only 目标已存在，拒绝覆盖：" + target)
            sequence = ue.load_asset(package)
            require(isinstance(sequence, ue.AnimSequence) and sequence.get_path_name() == package + "." + package.rsplit("/", 1)[1]
                    and sequence.get_editor_property("skeleton") == skeleton,
                    "原 AS / Skeleton 身份不符：" + package)
            rate = sequence.get_editor_property("platform_target_frame_rate").get_editor_property("default")
            source = {"path": sequence.get_path_name(), "length": float(sequence.get_play_length()),
                      "rate_scale": float(sequence.get_editor_property("rate_scale")),
                      "numerator": int(rate.numerator), "denominator": int(rate.denominator), "frames": expected_frames}
            require(source["rate_scale"] == 1.0 and (source["numerator"], source["denominator"]) == (60, 1)
                    and source["length"] == f32(expected_frames / 60.0),
                    "原源速率/60Hz完整帧域变化，须重新核契约：" + package)
            source["native_sha256"] = hashlib.sha256(native_export(sequence, output / (key + "_source_before.t3d")).encode()).hexdigest()
            sources[key] = (sequence, source)
            settings = author_settings(args, source)
            contract = json.dumps({"schema": SCHEMA, "source": source, "slot": SLOT, "section": SECTION,
                                   "project_test_only": True, "original_game_timing_known": False,
                                   "settings": settings}, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
            report["assets"][key] = {"target": target, "source": source, "author_settings": settings,
                                    "contract": contract, "saved_this_run": False}
        require(dirty() == report["dirty_before"], "读取原资产使原包 dirty，拒绝继续")
        if prior is not None:
            for key in selected:
                for field in ("source", "author_settings", "contract"):
                    require(report["assets"][key][field] == prior["assets"][key][field], "作者输入偏离 baseline：" + key + "/" + field)
        # 每个实际宿主先在自有 transient Montage 验证必需 SDK 真调用与帧域。
        # 仅形成有限编辑器数据，不播放、不建持久包、不改原 AS 或 Skeleton。
        for key, (sequence, source) in sources.items():
            probe = ue.AnimMontage()
            factory = ue.AnimMontageFactory()
            factory.set_editor_property("source_animation", sequence)
            align_model(probe, source)
            configure(probe, report["assets"][key]["author_settings"])
            window_snapshot(probe, report["assets"][key]["author_settings"])
            report["assets"][key]["sdk_model"] = model_snapshot(probe)
            probe = factory = None
        report["sdk_preflight_passed"] = True
        require(dirty() == report["dirty_before"], "SDK transient 核验触及原包")
        if args.mode != "preflight":
            report["phase"] = args.mode
            for key, (sequence, source) in sources.items():
                item = report["assets"][key]
                if args.mode == "create":
                    factory = ue.AnimMontageFactory()
                    factory.set_editor_property("source_animation", sequence)
                    package, name = item["target"].rsplit("/", 1)
                    montage = ue.AssetToolsHelpers.get_asset_tools().create_asset(name, package, ue.AnimMontage, factory)
                    require(montage is not None, "原生 factory 创建失败：" + item["target"])
                    align_model(montage, source)
                    configure(montage, item["author_settings"])
                    ue.EditorAssetLibrary.set_metadata_tag(montage, META_KEY, item["contract"])
                else:
                    montage = ue.load_asset(item["target"])
                item["snapshot"] = montage_snapshot(montage, sequence, source, item["author_settings"],
                                                     item["contract"], output / (key + "_montage.t3d"))
                current_dirty = dirty()
                require(not current_dirty["maps"] and set(current_dirty["content"]) <=
                        ({item["target"]} if args.mode == "create" else set()), "触及非当前新 Montage 的 dirty 包")
                if args.mode == "create":
                    # 完整原 SDK 和单 Default 全源已实读通过，才发布唯一新包。
                    require(ue.EditorAssetLibrary.save_loaded_asset(montage, only_if_is_dirty=False),
                            "唯一新 Montage 保存失败：" + item["target"])
                    item["saved_this_run"] = True
                    report["saved_packages"].append(item["target"])
                item["disk_sha256"] = digest(disk(item["target"]))
                if args.mode == "cold":
                    require(item["snapshot"] == prior["assets"][key]["snapshot"]
                            and item["disk_sha256"] == prior["assets"][key]["disk_sha256"], "cold 读回偏离真实创建结果：" + key)
                require(dirty() == report["dirty_before"], "当前阶段后仍有 dirty，保留宿主检查")
        report["phase"] = "completed"
        report["success"] = True
    except Exception as error:
        report["errors"].append({"phase": report["phase"], "reason": str(error)})
    finally:
        # 原对象内存保护在失败路径同样执行；不清 dirty、不回滚用户对象。
        for key, (sequence, source) in sources.items():
            try:
                after = native_export(sequence, output / (key + "_source_after.t3d"))
                require(hashlib.sha256(after.encode()).hexdigest() == source["native_sha256"], "原 AS 内存数据变化：" + key)
            except Exception as error:
                report["errors"].append({"phase": "protection", "reason": str(error)})
        if skeleton_text is not None:
            try:
                require(native_export(skeleton, output / "skeleton_after.t3d") == skeleton_text, "原 Skeleton 内存数据变化")
            except Exception as error:
                report["errors"].append({"phase": "protection", "reason": str(error)})
        report["dirty_after"] = dirty()
        if report["dirty_after"] != {"content": [], "maps": []}:
            report["errors"].append({"phase": "protection", "reason": "存在 dirty 包，保留宿主，不清标志或自动丢弃"})
        if protected and "protected_before" in report:
            try:
                report["protected_after"] = {str(path): digest(path) for path in protected}
                report["changed_files"] = [path for path, value in report["protected_before"].items()
                                           if report["protected_after"][path] != value]
                require(not report["changed_files"], "保护磁盘文件变化：" + repr(report["changed_files"]))
            except Exception as error:
                report["errors"].append({"phase": "protection", "reason": str(error)})
        if original_state is not None:
            try:
                report["editor_state_after"] = editor_state()
                report["editor_state_before"] = original_state
                require(report["editor_state_after"] == original_state, "原 World/相机/Actor/选择改变")
            except Exception as error:
                report["errors"].append({"phase": "protection", "reason": str(error)})
        report["success"] = report["success"] and not report["errors"]
        with (output / "readback.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2)
        ue.log("PYRIOS_EVADE_MONTAGES " + json.dumps({"mode": args.mode, "success": report["success"],
               "saved_packages": report["saved_packages"], "errors": report["errors"], "output": str(output)}, ensure_ascii=False))
        if args.exit_editor and original_state is not None and report["dirty_after"] == {"content": [], "maps": []}:
            ue.SystemLibrary.quit_editor()
    return report


def main():
    parser = argparse.ArgumentParser(description="两个完整原源 Pyrios Montage 的明确作者合同")
    parser.add_argument("--mode", required=True, choices=("preflight", "create", "cold"))
    parser.add_argument("--case", default="both", choices=("front", "back", "both"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--blend-in", type=float, default=0.1)
    parser.add_argument("--blend-out", type=float, default=0.25)
    parser.add_argument("--requested-play-rate", type=float, default=1.0)
    parser.add_argument("--fx-begin", type=float, help="项目 FX 起点，缺省为原源首个 target 采样点")
    parser.add_argument("--fx-end", type=float, help="项目 FX 终点，缺省为完整原源末端")
    parser.add_argument("--exit-editor", action="store_true")
    return run(parser.parse_args())


if __name__ == "__main__":
    main()
