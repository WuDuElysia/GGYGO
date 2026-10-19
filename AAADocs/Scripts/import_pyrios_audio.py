"""@file import_pyrios_audio.py
@brief 按资源发布清单准备、导入和冷读 Pyrios SoundWave，不承担播放或动作接线。

离线 --mode plan 只输出机器消费的完整来源／目标计划，不写文件。
统筹保存并复核计划后，以 --plan 计划文件执行 preflight/import/readback。
--targets 只用于明确选择计划子集；不提供自动跳过或覆盖已有资产的模式。
原 Normal01 Skill 通过显式既有映射保留，只读验证，不再次导入。
执行前声明 --host editor|commandlet；失败保留真实已保存集，不删除或回滚。
"""

import argparse
import hashlib
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import wave


PROJECT = Path("F:/ue_project/GGYGO")
SOURCE = Path("F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model")
AUDIO = SOURCE / "Audio"
TARGET_ROOT = "/Game/Characters/Player/Pyrios/Audio"
ACTION_PREFIX = "Avatar_Male_Size03_Pyrois_Ani_"
NORMAL_ACTION = ACTION_PREFIX + "Attack_Normal_01"
LEGACY_SOURCE = NORMAL_ACTION + "/Skill_Attack_Normal_01.wav"
LEGACY_TARGET = TARGET_ROOT + "/Normal01/SW_Pyrios_Normal01_Skill"
LEGACY_ASSET_SHA = "5f5665a04efae2938b5cc44cc6e82d9c817d0f79988e193d9e0e9fbf523e3248"
LEGACY_SOURCE_SHA = "6eeafd54c64c6d028db1a734577860470be657f3035cce28529c562c289d3b55"
MONTAGE_FILE = PROJECT / "Content/Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_Normal_01.uasset"


def require(condition, reason):
    if not condition:
        raise RuntimeError("[Audio.Pyrios] " + reason)


def path_key(path):
    return os.path.normcase(str(Path(path).resolve()))


def stamp(path):
    value = path.stat()
    return value.st_size, value.st_mtime_ns


def fingerprint(path):
    before = stamp(path)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    require(stamp(path) == before, "读取期间文件变化：" + str(path))
    return {"size": before[0], "mtime_ns": before[1], "sha256": digest}


def read_json(path, inputs):
    before = stamp(path)
    raw = path.read_bytes()
    require(stamp(path) == before, "JSON 读取期间变化：" + str(path))
    try:
        data = json.loads(raw.decode("utf-8-sig"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise RuntimeError("[Audio.Pyrios] JSON 无效：" + str(path) + "; " + str(exc)) from exc
    inputs[str(path)] = {"size": before[0], "mtime_ns": before[1], "sha256": hashlib.sha256(raw).hexdigest()}
    require(isinstance(data, dict), "JSON 必须是对象：" + str(path))
    return data


def inspect_wav(path, inputs):
    """核对真实 PCM，不转码、不归一化、不以静音代替无效输入。"""
    identity = fingerprint(path)
    with wave.open(str(path), "rb") as reader:
        channels, width, rate = reader.getnchannels(), reader.getsampwidth(), reader.getframerate()
        frames = reader.getnframes()
        require(reader.getcomptype() == "NONE" and width == 2 and channels in (1, 2)
                and rate > 0 and frames > 0, "需要非空单／双声道 PCM16：" + str(path))
        read_frames, nonzero = 0, False
        while True:
            data = reader.readframes(65536)
            if not data:
                break
            require(len(data) % (channels * width) == 0, "PCM 帧截断：" + str(path))
            read_frames += len(data) // (channels * width)
            nonzero = nonzero or any(data)
    require(read_frames == frames and nonzero, "PCM 截断或全零：" + str(path))
    require(stamp(path) == (identity["size"], identity["mtime_ns"]), "WAV 读取期间变化：" + str(path))
    inputs[str(path)] = identity
    return {"sample_rate": rate, "channels": channels, "frames": frames,
            "duration_seconds": frames / rate, "source_sha256": identity["sha256"]}


def target_file(target):
    require(target.startswith(TARGET_ROOT + "/"), "目标不属于 Pyrios Audio：" + target)
    return PROJECT / "Content" / (target[6:] + ".uasset")


def event_evidence(event, mapping, movement_events):
    """消费资源已发布的两种动作关联和显式角色 Switch，不推测触发帧。"""
    require(isinstance(event, dict) and isinstance(event.get("eventName"), str)
            and event["eventName"] and type(event.get("eventShortId")) is int
            and event["eventShortId"] > 0 and isinstance(event.get("outputs"), list), "事件身份／输出声明无效")
    name = event["eventName"]
    banks = event.get("eventBankFiles") if "eventBankFiles" in event else [event.get("eventBankFile")]
    require(isinstance(banks, list) and banks and all(isinstance(b, str) and b for b in banks), "事件 Bank 来源为空：" + name)
    if "characterSwitchValue" in event:
        require(event.get("characterSwitchGroupId") == 4203091697
                and event["characterSwitchValue"] == 3763547777, "未选中已证 Pyrois 角色分支：" + name)
        require(name in movement_events, "角色分支缺少 movement manifest：" + name)
        original = movement_events[name]
        require(event["eventShortId"] == original["eventShortId"]
                and set(event["outputs"]) == set(original["outputs"])
                and len(banks) == 1 and path_key(banks[0]) == path_key(original["bank"]),
                "角色输出／Bank 与 movement manifest 不同：" + name)
        if "nodes" in original:
            require(event.get("characterSwitchRootId") == original["root"]
                    and event.get("characterNodeIds") == original["nodes"], "脚步角色节点与原清单不同：" + name)
        basis = event.get("selectionBasis")
        association = "character_switch_verified"
    elif "mappingMethod" in event:
        basis = event["mappingMethod"]
        association = "name_associated"
    else:
        require(isinstance(event.get("layerType"), str) and event["layerType"], "缺少已发布事件关联方式：" + name)
        basis = mapping.get("mappingBasis")
        association = "name_associated"
    require(isinstance(basis, str) and basis, "事件关联依据为空：" + name)
    require(event["outputs"], "动作事件未声明可导入媒体，需资源明确分类：" + name)
    return {"name": name, "id": event["eventShortId"], "association": association,
            "basis": basis, "banks": banks}


def build_plan():
    """只读生成完整已发布集及保护基线；输出可由统筹作为冻结机器计划保存。"""
    inputs = {}
    manifest = read_json(AUDIO / "manifest.json", inputs)
    declared = manifest.get("mappedAnimations")
    require(isinstance(declared, dict) and declared, "manifest 缺少完整动作清单")
    actual_mappings = {p.parent.name: p for p in AUDIO.glob("*/mapping.json")}
    require(set(actual_mappings) == set(declared), "动作 mapping 与 manifest 集合不同")
    movement_events = {}
    for filename in ("movement_pyrois_armor_manifest.json", "movement_pyrois_footsteps_manifest.json"):
        movement = read_json(AUDIO / filename, inputs)
        require(movement.get("character") == "Pyrois" and isinstance(movement.get("events"), list), "movement 角色／事件无效：" + filename)
        count = 0
        for event in movement["events"]:
            require(isinstance(event, dict) and event["eventName"] not in movement_events, "movement 事件重复")
            outputs = [item["file"] for item in event["outputs"]]
            require(len(outputs) == len(set(outputs)), "movement 输出重复：" + event["eventName"])
            if filename == "movement_pyrois_armor_manifest.json":
                require(event.get("switchGroupId") == 4203091697 and event.get("switchValue") == 3763547777, "Armor 未选中 Pyrois")
                branch = {"bank": event["eventBankFile"]}
            else:
                require(event.get("pyroisSwitchValue") == 3763547777 and event.get("pyroisNodes")
                        and event["pyroisNodes"] == event.get("lycaonNodes"), "脚步共享分支缺少证据")
                branch = {"bank": event["bank"], "root": event["characterSwitchRootId"], "nodes": event["pyroisNodes"]}
            movement_events[event["eventName"]] = {"eventShortId": event["eventShortId"], "outputs": outputs, **branch}
            count += len(outputs)
        require(count == movement.get("wavCount"), "movement wavCount 不同：" + filename)
    assets, seen_targets, seen_sources, event_count = [], set(), set(), 0
    for action in sorted(declared):
        require(action.startswith(ACTION_PREFIX) and re.fullmatch(r"[A-Za-z0-9_]+", action), "动作路径无效：" + action)
        mapping_path = actual_mappings[action]
        require(mapping_path.resolve().is_relative_to(AUDIO.resolve()), "mapping 越出来源目录：" + str(mapping_path))
        mapping = read_json(mapping_path, inputs)
        require(mapping.get("animationName") == action and isinstance(mapping.get("events"), list), "mapping 动作身份无效：" + action)
        for key, suffix in (("animationFbx", ".fbx"), ("animationJson", ".json")):
            clip = SOURCE / "anim" / (action + suffix)
            require(clip.is_file() and path_key(mapping[key]) == path_key(clip), "mapping 非真实源动作：" + action)
        events = mapping["events"]
        require(sorted(e["eventName"] for e in events) == sorted(declared[action]["events"]), "动作事件与 manifest 不同：" + action)
        files = {}
        for event in events:
            evidence = event_evidence(event, mapping, movement_events)
            event_count += 1
            for output in event["outputs"]:
                require(isinstance(output, str), "输出路径必须是字符串：" + action)
                relative = PurePosixPath(output.replace("\\", "/"))
                require(not relative.is_absolute() and len(relative.parts) == 2 and relative.parts[0] == action
                        and ".." not in relative.parts and relative.suffix.lower() == ".wav", "输出路径越界：" + output)
                file = AUDIO.joinpath(*relative.parts).resolve()
                require(file.parent == mapping_path.parent.resolve(), "WAV 链接越出动作目录：" + str(file))
                files.setdefault(file, []).append(evidence)
        require(set(files) == {p.resolve() for p in mapping_path.parent.rglob("*.wav")}, "WAV／mapping 文件集合不同：" + action)
        require(type(mapping.get("wavCount")) is int and mapping["wavCount"] == len(files)
                and declared[action]["wavCount"] == len(files), "动作 wavCount 不同：" + action)
        folder = "Normal01" if action == NORMAL_ACTION else action[len(ACTION_PREFIX):]
        for file, evidence in sorted(files.items()):
            relative = action + "/" + file.name
            if relative == LEGACY_SOURCE:
                target, kind = LEGACY_TARGET, "preserved"
            else:
                name = "SW_Pyrios_" + re.sub(r"[^A-Za-z0-9_]", "_", file.stem)
                target, kind = TARGET_ROOT + "/" + folder + "/" + name, "new"
            require(target.casefold() not in seen_targets and path_key(file) not in seen_sources, "目标／来源命名冲突：" + target)
            seen_targets.add(target.casefold())
            seen_sources.add(path_key(file))
            info = inspect_wav(file, inputs)
            if kind == "preserved":
                require(info["source_sha256"] == LEGACY_SOURCE_SHA, "已验收 Normal01 来源改变")
            assets.append({"action": action, "source": str(file), "mapping": str(mapping_path),
                           "target": target, "object_path": target + "." + target.rsplit("/", 1)[1],
                           "kind": kind, "events": evidence, **info})
    require(len(assets) == manifest.get("wavCount") and len(declared) == manifest.get("mappedAnimationCount")
            and event_count == manifest.get("mappedEventCount"), "manifest 总计与实际不同")
    require(seen_sources == {path_key(p) for p in AUDIO.rglob("*.wav")}, "发布根存在未声明 WAV")
    require(sum(a["kind"] == "preserved" for a in assets) == 1, "Normal01 既有映射必须唯一")
    protected = {str(target_file(LEGACY_TARGET)): fingerprint(target_file(LEGACY_TARGET)),
                 str(MONTAGE_FILE): fingerprint(MONTAGE_FILE)}
    require(protected[str(target_file(LEGACY_TARGET))]["sha256"] == LEGACY_ASSET_SHA, "已验收 Normal01 资产身份改变")
    return {"schema_version": 1, "source_root": str(AUDIO), "target_root": TARGET_ROOT,
            "source_scope": "仅资源已发布且可证明角色归属的素材，不表示全部游戏音频或已还原时序／混音",
            "assets": assets, "source_inputs": inputs, "protected_files": protected,
            "asset_defaults": {"looping": False, "volume": 1.0, "pitch": 1.0},
            "source_gaps": {"unmapped_decoded_events": manifest.get("unmappedDecodedEvents"),
                            "animations_without_matched_events": manifest.get("animationsWithoutMatchedDecodedEvents")},
            "playback_tested": False, "original_timing_mixing_verified": False}


def check_inputs(plan, names=None):
    """来源只持本次快照；原生回调后检查来源与既有资产，保护不是业务回落。"""
    for name in plan["source_inputs"] if names is None else names:
        identity = plan["source_inputs"][name]
        require(stamp(Path(name)) == (identity["size"], identity["mtime_ns"]), "冻结来源变化：" + name)
    for name, identity in plan["protected_files"].items():
        require(fingerprint(Path(name)) == identity, "受保护既有文件变化：" + name)


def dirty_packages(unreal):
    return {"content": {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()},
            "maps": {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()}}


def check_dirty(before, after, allowed=()):
    for kind in ("content", "maps"):
        extra = set(allowed) if kind == "content" else set()
        require(not (after[kind] - before[kind] - extra) and not (before[kind] - after[kind]),
                "脏包成员变化：" + kind + "; added=" + repr(sorted(after[kind] - before[kind] - extra))
                + "; removed=" + repr(sorted(before[kind] - after[kind])))


def require_host(unreal, host):
    require(host in ("editor", "commandlet"), "宿主必须显式为 editor 或 commandlet")
    commandlet = re.search(r"(?:^|\s)-run=(\S+)", unreal.SystemLibrary.get_command_line(), re.IGNORECASE)
    if host == "commandlet":
        require(commandlet is not None and commandlet.group(1).casefold() == "pythonscript", "需要原生 -run=PythonScript")
        require(not unreal.EditorLevelLibrary.get_pie_worlds(include_dedicated_server=True), "PIE 必须停止")
    else:
        require(commandlet is None, "Commandlet 不得声明为 editor")
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        require(subsystem is not None and not subsystem.is_in_play_in_editor(), "需要非 PIE 编辑器宿主")


def inspect_asset(unreal, asset, record):
    require(isinstance(asset, unreal.SoundWave) and asset.get_path_name() == record["object_path"], "非目标 SoundWave：" + record["target"])
    import_data = unreal.find_object(asset, "AssetImportData")
    require(isinstance(import_data, unreal.AssetImportData), "来源子对象不可读：" + record["target"])
    filenames = list(import_data.extract_filenames())
    require(len(filenames) == 1 and path_key(filenames[0]) == path_key(record["source"]), "原生导入来源不同：" + record["target"])
    data = unreal.AssetRegistryHelpers.create_asset_data(asset)
    rate = unreal.AssetRegistryHelpers.get_tag_value(data, "ImportedSampleRate")
    require(isinstance(rate, str) and rate, "ImportedSampleRate tag 不可读：" + record["target"])
    values = {"sample_rate": int(rate), "channels": asset.get_editor_property("num_channels"),
              "duration_seconds": asset.get_editor_property("duration"), "looping": asset.get_editor_property("looping"),
              "volume": asset.get_editor_property("volume"), "pitch": asset.get_editor_property("pitch")}
    require(values["sample_rate"] == record["sample_rate"] and values["channels"] == record["channels"], "原生格式不同：" + record["target"])
    require(math.isfinite(values["duration_seconds"]) and abs(values["duration_seconds"] - record["duration_seconds"])
            <= max(1e-5, 1 / values["sample_rate"]), "原生时长不同：" + record["target"])
    require(values["looping"] is False and values["volume"] == 1.0 and values["pitch"] == 1.0, "显式素材默认值不同：" + record["target"])
    return {"target": record["target"], "kind": record["kind"], "source_filenames": filenames, **values}


def require_new(unreal, record):
    require(record["kind"] == "new" and not target_file(record["target"]).exists()
            and not unreal.EditorAssetLibrary.does_asset_exist(record["target"])
            and unreal.find_object(None, record["object_path"], follow_redirectors=False) is None,
            "新增目标已存在／不属于新增范围：" + record["target"])


def import_one(unreal, record, before):
    require_new(unreal, record)
    factory = unreal.SoundFactory()
    for name in ("auto_create_cue", "include_attenuation_node", "include_looping_node", "include_modulator_node"):
        factory.set_editor_property(name, False)
    task = unreal.AssetImportTask()
    for name, value in {"filename": record["source"], "destination_path": record["target"].rsplit("/", 1)[0],
                        "destination_name": record["target"].rsplit("/", 1)[1], "automated": True,
                        "replace_existing": False, "replace_existing_settings": False, "save": False, "factory": factory}.items():
        task.set_editor_property(name, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects, paths = list(task.get_objects()), list(task.get_editor_property("imported_object_paths"))
    require(len(objects) == 1 and paths == [record["object_path"]] and not target_file(record["target"]).exists(), "导入输出／提前保存异常：" + record["target"])
    asset = objects[0]
    require(isinstance(asset, unreal.SoundWave) and asset.get_path_name() == record["object_path"], "原生返回非自有目标：" + record["target"])
    for name, value in (("looping", False), ("volume", 1.0), ("pitch", 1.0)):
        asset.set_editor_property(name, value)
    inspect_asset(unreal, asset, record)
    check_dirty(before, dirty_packages(unreal), {record["target"]})
    return asset


def run(mode, plan_path, targets=None, host="editor"):
    """@param mode preflight 只读预检、import 精确新增、readback 只读冷加载。
    @param plan_path 统筹复核的机器计划，必须与完整当前发布源及保护基线相同。
    @param targets 明确子集；省略时使用计划中的完整新增集／完整回读集。
    @return 实际保存、读取和未验证边界；错误传播，资源与脏包不自动回滚。
    """
    require(mode in ("preflight", "import", "readback"), "执行模式无效")
    plan_inputs = {}
    plan = read_json(Path(plan_path), plan_inputs)
    require(plan == build_plan(), "机器计划与实际发布来源／目标／保护基线不同")
    records = {a["target"]: a for a in plan["assets"]}
    approved = set(records) if mode == "readback" else {t for t, a in records.items() if a["kind"] == "new"}
    selected = sorted(approved) if targets is None else targets
    require(selected and len(selected) == len(set(selected)) and set(selected) <= approved, "目标不属于本模式明确计划集")
    import unreal
    require(path_key(unreal.Paths.project_dir()) == path_key(PROJECT), "项目不匹配")
    require_host(unreal, host)
    before = dirty_packages(unreal)
    legacy = records[LEGACY_TARGET]
    require(LEGACY_TARGET not in before["content"] and unreal.EditorAssetLibrary.does_asset_exist(LEGACY_TARGET), "既有 Normal01 脏包／注册资产无效")
    preserved = inspect_asset(unreal, unreal.EditorAssetLibrary.load_asset(LEGACY_TARGET), legacy)
    check_inputs(plan)
    check_dirty(before, dirty_packages(unreal))
    for target in selected:
        require(target not in before["content"], "目标已有未保存工作：" + target)
        if mode == "readback":
            require(target_file(target).is_file() and unreal.EditorAssetLibrary.does_asset_exist(target), "回读要求已保存注册目标：" + target)
        else:
            require_new(unreal, records[target])
    result = {"mode": mode, "host": host, "saved": [], "assets": [], "preserved": preserved,
              "explicit_targets": selected, "source_gaps": plan["source_gaps"],
              "playback_tested": False, "original_timing_mixing_verified": False}
    current = "preflight"
    try:
        if mode != "preflight":
            for target in selected:
                current, record = target, records[target]
                check_inputs(plan, (record["source"], record["mapping"]))
                if mode == "import":
                    asset = import_one(unreal, record, before)
                    check_inputs(plan, (record["source"], record["mapping"]))
                    require(unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), "目标保存失败：" + target)
                    result["saved"].append(target)
                    require(target_file(target).is_file() and target_file(target).stat().st_size > 0, "目标未落盘：" + target)
                else:
                    asset = unreal.EditorAssetLibrary.load_asset(target)
                result["assets"].append(inspect_asset(unreal, asset, record))
                check_dirty(before, dirty_packages(unreal))
        check_inputs(plan)
        for name, identity in plan_inputs.items():
            require(fingerprint(Path(name)) == identity, "执行期间机器计划变化：" + name)
    except Exception as exc:
        unreal.log_error("[Audio.Pyrios] " + mode + " 失败；target=" + current
                         + "; saved=" + repr(result["saved"]) + "; reason=" + str(exc) + "; 未回滚／重试")
        raise
    unreal.log("[Audio.Pyrios] " + mode + " host=" + host + " complete; assets=" + str(len(result["assets"]))
               + "; preserved=1; playback/timing/mixing unverified")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plan", "preflight", "import", "readback"), required=True)
    parser.add_argument("--plan")
    parser.add_argument("--targets", nargs="+")
    parser.add_argument("--host", choices=("editor", "commandlet"), default="editor")
    args = parser.parse_args()
    if args.mode == "plan":
        print(json.dumps(build_plan(), ensure_ascii=True, indent=2))
    else:
        require(args.plan, "原生执行必须提供统筹复核的 --plan")
        print(json.dumps(run(args.mode, args.plan, args.targets, args.host), ensure_ascii=True, indent=2))
