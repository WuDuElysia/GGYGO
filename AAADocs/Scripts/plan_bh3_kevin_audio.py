"""@file plan_bh3_kevin_audio.py
@brief 将 Kevin 既有声音来源编成供 SoundCue、Animation 和 GA 实际消费的配置。

只读已发布 manifest、缓存 Bank XML 和既存 WAV；不解包、不复制媒体、不访问 UE。
原事件内部的单声、随机及静态多层分别保留。动作阶段是项目候选，原触发时间未知。
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import xml.etree.ElementTree as ET


PROJECT = Path("F:/ue_project/GGYGO")
SOURCE = Path("F:/AnimeStudio/Exports/BH3/Animator/Kevin/05_BOSS_411_DemonBattle")
AUDIO = SOURCE / "Audio"
CONFIG = PROJECT / "AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Audio_Config.json"
WAVE_ROOT = "/Game/Characters/Boss/Kevin/DemonBattle/Audio"
HIT_CUE_CONFIG = "AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_FX_Config.json"
ATTENUATION = WAVE_ROOT + "/SA_KevinDB_Combat"
MONTAGE_CONFIG = PROJECT / "AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Montage_Config.json"
EXTRA_EVENTS = (497205119, 549475289, 2736721907, 2736721901,
                2524282819, 1047260087, 2190265172, 2218789460, 3188014124)


def require(condition, reason):
    if not condition:
        raise RuntimeError("[Audio.Kevin] " + reason)


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def identity(path):
    path = Path(path)
    return {"path": str(path), "size": path.stat().st_size,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}


def package_files(package):
    require(package.startswith("/Game/"), "不是工程包：" + package)
    base = PROJECT / "Content" / package[6:]
    return {suffix: identity(base.with_suffix(suffix)) if base.with_suffix(suffix).is_file() else None
            for suffix in (".uasset", ".uexp", ".ubulk", ".uptnl")}


def properties(node):
    """读取缓存 XML 中定值的 AkPropBundle；不把随机范围或 RTPC 当作定值。"""
    result = {}
    for item in node.iter("object"):
        if item.get("name") != "AkPropBundle":
            continue
        fields = {field.get("name"): field for field in item.findall("field")}
        if "pID" in fields and "pValue" in fields:
            key = fields["pID"].get("valuefmt", fields["pID"].get("value"))
            result[key] = fields["pValue"].get("value")
    return result


def node_fields(node):
    return {field.get("name"): field.get("value") for field in node.iter("field")}


def build_config():
    manifest_path = AUDIO / "manifest.json"
    manifest = read_json(manifest_path)
    graph_path = Path(manifest["sourceGraphs"]["file"])
    require(identity(graph_path)["sha256"] == manifest["sourceGraphs"]["fileBytesSha256"],
            "缓存 Bank 图与发布来源不符")
    banks = read_json(graph_path)
    bank = next(bank for bank in banks if bank["language"] == "ja")
    xml_path = Path(bank["xmlFile"])
    require(identity(xml_path)["sha256"] == bank["xmlSha256"], "缓存 Bank XML 身份改变")
    nodes = {}
    for node in ET.parse(xml_path).getroot().iter("object"):
        if not node.get("name", "").startswith("CAk"):
            continue
        object_id = next((f for f in node.iter("field") if f.get("name") == "ulID"), None)
        if object_id is not None:
            nodes[int(object_id.get("value"))] = node

    waves, wave_by_hash, source_inputs, event_sources = [], {}, {}, {}

    def add_wave(source, target, published, existing):
        source = Path(source)
        actual = identity(source)
        require(actual["sha256"] == published["fileBytesSha256"], "源 WAV 身份改变：" + str(source))
        require(published["sampleWidthBytes"] == 2 and published["channels"] in (1, 2),
                "需要实际 PCM16 单/双声道来源：" + str(source))
        before = package_files(target)
        require(bool(before[".uasset"]) == existing, "SW 目标前像与导入状态不符：" + target)
        row = {"target": target, "source": actual, "source_wem_sha256": published["sourceWemSha256"],
               "existing": existing, "package_before": before,
               "sample_rate": published["sampleRate"], "channels": published["channels"],
               "duration_seconds": published["durationSeconds"],
               "defaults": {"looping": False, "volume": 1.0, "pitch": 1.0}}
        waves.append(row)
        wave_by_hash.setdefault(row["source_wem_sha256"], target)
        source_inputs[str(source)] = actual
        return target

    for file in manifest["files"]:
        relative = Path(file["file"])
        name = "SW_" + re.sub(r"[^A-Za-z0-9_]", "_", relative.stem)
        add_wave(AUDIO / relative, WAVE_ROOT + "/" + relative.parent.name + "/" + name, file, True)
    require(len(waves) == 46, "本批应消费现有 46 个 SW，来源数量发生变化")

    for action in manifest["animations"]:
        if not action["wavCount"]:
            continue
        path = AUDIO / action["mapping"]
        stamp = identity(path)
        require(stamp["sha256"] == action["mappingFileBytesSha256"], "动作 mapping 身份改变")
        source_inputs[str(path)] = stamp
        for event in read_json(path)["events"]:
            event_sources[event["eventShortId"]] = event
    unassigned = {event["eventShortId"]: event for event in manifest["unassignedEvents"]}
    for event_id in EXTRA_EVENTS:
        event = unassigned[event_id]
        require(event["resolutionStatus"] == "original_graph_resolved" and event["variants"],
                "额外候选原图不完整：" + str(event_id))
        require(event["eventName"].startswith("BOSS_411_") and "ABYSS" not in event["eventName"],
                "额外候选形态边界不符")
        event_sources[event_id] = event
        for variant in event["variants"]:
            require(variant["sharedAcrossLanguages"], "本批未选择语言专属语音")
            if variant["sourceWemSha256"] in wave_by_hash:
                continue
            published = dict(variant["decoded"], sourceWemSha256=variant["sourceWemSha256"])
            target = WAVE_ROOT + "/Shared/SW_KevinDB_WEM_" + str(min(variant["mediaIds"]))
            add_wave(published["file"], target, published, False)

    def groups_for(node_id):
        require(node_id in nodes, "原播放节点缺失：" + str(node_id))
        node, sound = nodes[node_id], bank["sounds"].get(str(node_id))
        kind, fields = node.get("name"), node_fields(node)
        if kind == "CAkSound":
            require(sound and sound["sourceWemSha256"] in wave_by_hash,
                    "原 Sound 没有本批可用媒体：" + str(node_id))
            props = properties(node)
            loop = next((float(v) for k, v in props.items() if k.endswith("[Loop]")), 1.0)
            require(loop in (0.0, 1.0), "原有限重复次数需单独制作，不能简化：" + str(node_id))
            return [{"wave_targets": [wave_by_hash[sound["sourceWemSha256"]]],
                     "wave_looping": [loop == 0.0], "weights": [1.0],
                     "source_node_ids": [node_id], "source_container": kind,
                     "source_static_properties": props, "source_avoid_repeat": 0}]
        children = [int(f.get("value")) for f in node.iter("field") if f.get("name") == "ulChildID"]
        require(children, "原容器没有子节点：" + str(node_id))
        nested = [groups_for(child) for child in children]
        if kind == "CAkLayerCntr":
            require(fields.get("ulNumLayers") == "0" and fields.get("ulNumRTPC") == "0",
                    "动态 Layer 需要真实参数，不能平铺：" + str(node_id))
            return [group for child in nested for group in child]
        require(kind == "CAkRanSeqCntr" and fields.get("eMode") == "0"
                and fields.get("eRandomMode") == "0" and fields.get("bIsContinuous") == "0"
                and fields.get("sLoopCount") == "1", "不支持静默改写原序列/连续容器：" + str(node_id))
        require(all(len(child) == 1 and len(child[0]["wave_targets"]) == 1 for child in nested),
                "嵌套随机/混层需要独立制作：" + str(node_id))
        weights = [float(f.get("value")) for f in node.iter("field") if f.get("name") == "weight"]
        require(len(weights) == len(children) and all(value > 0 for value in weights), "原权重缺失")
        return [{"wave_targets": [child[0]["wave_targets"][0] for child in nested],
                 "wave_looping": [child[0]["wave_looping"][0] for child in nested],
                 "weights": weights, "source_node_ids": [node_id] + children,
                 "source_container": kind, "source_static_properties": properties(node),
                 "source_avoid_repeat": int(fields.get("wAvoidRepeatCount", "0"))}]

    graph_events = {event["eventId"]: event for event in bank["events"]}
    sound_cues, events, gaps = [], [], []
    for event_id, source_event in sorted(event_sources.items()):
        graph = graph_events[event_id]
        if not source_event.get("outputs") and event_id not in EXTRA_EVENTS:
            gaps.append({"event_id": event_id, "event_name": source_event["eventName"],
                         "status": source_event["resolutionStatus"],
                         "control_only": source_event["controlOnly"],
                         "empty_event": source_event["emptyEvent"],
                         "missing_nodes": source_event["unresolvedPlaybackReferences"]})
            continue
        require(not graph["controlOnly"] and not graph["unresolvedPlaybackReferences"], "播放图不完整")
        groups = []
        for action in graph["actions"]:
            require(action["type"] == "CAkActionPlay", "原控制动作不能当 WAV 播放")
            props = properties(nodes[action["actionId"]])
            require(not any("Delay" in key and float(value) != 0 for key, value in props.items()),
                    "原动作延迟需显式保留：" + str(event_id))
            groups.extend(groups_for(action["targetId"]))
        targets = []
        for index, group in enumerate(groups):
            target = WAVE_ROOT + "/Cues/SC_KevinDB_E" + str(event_id) + "_" + str(index + 1)
            targets.append(target)
            sound_cues.append(dict(group, target=target, event_id=event_id,
                                   attenuation_target=ATTENUATION,
                                   project_volume=0.7, project_pitch=1.0,
                                   project_random_without_replacement=group["source_avoid_repeat"] > 0))
        events.append({"event_id": event_id, "event_name": graph["eventName"],
                       "association": "unassigned_original_boss_event" if event_id in EXTRA_EVENTS else "name_associated",
                       "sound_cues": targets, "original_trigger_seconds": None,
                       "original_timing_verified": False, "original_mix_verified": False})

    event_map = {event["event_id"]: event for event in events}
    # 这些项目角色不是原帧推断；Animation 用实际动作窗口给时间，Combat 只消费真实命中入口。
    roles = {**{f"Ice{i:02}": (497205119, 549475289, "same_boss_ice_candidate") for i in range(1, 6)},
             "Fire01": (230747614, 3810557962, "same_action_candidate"),
             "Fire02": (1624690420, 1624690421, "same_action_candidate"),
             "Fire03": (3969531162, 3980448763, "other_fire_action_project_candidate"),
             "Fire04": (3779481217, 2564483858, "same_action_candidate"),
             "Fly01": (3618384703, 3618384701, "same_action_candidate"),
             "Fly02": (93858526, 93858524, "same_action_candidate"),
             "Fly03": (93858525, 93858524, "other_fly_action_project_candidate"),
             "Counter": (4188079934, 4188079933, "same_action_candidate")}
    actions, hit_bindings = [], []
    for action_id, (release, hit, basis) in roles.items():
        require(len(event_map[hit]["sound_cues"]) == 1, "命中 Cue 需要明确单一 SoundBase")
        hit_bindings.append({"action_id": action_id, "event_id": hit,
                             "sound": event_map[hit]["sound_cues"][0], "binding_basis": basis,
                             "cue_writer": "FX", "cue_config": HIT_CUE_CONFIG, "cue_key": action_id})
        actions.append({"action_id": action_id, "binding_basis": basis,
                        "original_action_mapping_verified": False,
                        "point_event_id": release,
                        "hit_event_id": hit, "hit_sound": event_map[hit]["sound_cues"][0],
                        "hit_cue_owner": "FX", "hit_cue_config": HIT_CUE_CONFIG, "hit_cue_key": action_id,
                        "hit_authority": "Combat/GAS actual hit only"})
        if action_id == "Fire04":
            actions[-1]["point_binding_basis"] = "other_fly_action_project_candidate_not_landing"
    for action_id, event_id, basis in (
            ("DashF", 3188014124, "same_boss_evade_project_candidate"),
            ("DashB", 3188014124, "same_boss_evade_project_candidate"),
            ("FlyEvade", 3188014124, "same_boss_evade_project_candidate"),
            ("FireWingGuard", 4188079934, "other_counter_action_project_candidate")):
        actions.append({"action_id": action_id, "binding_basis": basis,
                        "original_action_mapping_verified": False, "point_event_id": event_id,
                        "hit_authority": "not_a_damage_action"})

    animation = read_json(MONTAGE_CONFIG)
    assemblies = {row["id"]: row for row in animation["skill_assemblies"]}
    montage_events, persistent_windows = [], []
    for action in actions:
        action_id = action["action_id"]
        require(action_id in assemblies, "缺少 Animation 实际组装配置：" + action_id)
        assembly = assemblies[action_id]
        phases = assembly["animation_phases"]
        selected = [phase for phase in phases if phase["role"] == "active"]
        if action_id == "FireWingGuard":
            selected = [phase for phase in phases if phase["role"] == "charge"]
        require(selected, "缺少本动作明确的项目播放阶段：" + action_id)
        action["enable_gate"] = assembly["enable_gate"]
        for phase in selected:
            start, end = phase["window_seconds"]
            require(math.isfinite(start) and 0 <= start < end <= assembly["expected_duration_seconds"],
                    "Animation 阶段越界：" + action_id + "/" + phase["phase_id"])
            for group_index, sound in enumerate(event_map[action["point_event_id"]]["sound_cues"]):
                key = action_id + "." + phase["phase_id"] + ".E" + str(action["point_event_id"]) + "." + str(group_index + 1)
                montage_events.append({"event_key": key, "action_id": action_id, "phase_id": phase["phase_id"],
                                       "event_id": action["point_event_id"], "time_seconds": start,
                                       "sound": sound, "parameters": {"volume": 1.0, "pitch": 1.0,
                                       "follow": True, "attach_name": "None"},
                                       "source_window_seconds": [start, end],
                                       "timing_basis": phase["timing_basis"],
                                       "binding_basis": action.get("point_binding_basis", action["binding_basis"]),
                                       "enable_gate": assembly["enable_gate"], "original_timing_verified": False})
        if action_id in ("Fire02", "Fly03"):
            warning = next(phase for phase in phases if phase["role"] == "warning")
            persistent_windows.append({"action_id": action_id, "phase_id": warning["phase_id"],
                                       "window_seconds": warning["window_seconds"],
                                       "begin_tag": "Event.Montage.AudioWindowBegin",
                                       "end_tag": "Event.Montage.AudioWindowEnd",
                                       "original_timing_verified": False,
                                       "timing_basis": warning["timing_basis"]})
    held = []
    for key, action, event_id, begin, end in (
            ("Fire02Hold", "Fire02", 3286683035, "HoldBegin", "HoldEnd"),
            ("Fly03Charge", "Fly03", 2524282819, "ChargeBegin", "ChargeEnd"),
            ("IceEnvironment", "PhaseIce", 1047260087, "EnvironmentBegin", "EnvironmentEnd")):
        sounds = event_map[event_id]["sound_cues"]
        require(len(sounds) == 1, "持续声音需要明确单一 SoundBase")
        persistent = {"sound": sounds[0], "begin_tag": "Event.Montage.AudioWindowBegin",
                      "end_tag": "Event.Montage.AudioWindowEnd", "socket": "None",
                      "relative_location": [0.0, 0.0, 0.0], "relative_rotation": [0.0, 0.0, 0.0],
                      "volume": 1.0, "pitch": 1.0}
        for row in actions:
            if row["action_id"] == action:
                row["persistent_audio"] = persistent
        held.append({"key": key, "action_id": action, "event_id": event_id,
                     "enabled": action != "PhaseIce",
                     "persistent_audio": persistent, "begin_phase": begin, "end_phase": end,
                     "binding_basis": "project_candidate", "original_trigger_seconds": None,
                     "cleanup_owner": "original GA AudioActor -> original AudioComponent; retire original identity",
                     "retire_on": ["phase_end", "normal_end", "cancel", "death", "target_invalid"],
                     "finite_source_is_not_forced_to_loop": True})
    # 复合空中链消费 Animation 已给出的整链时间；声音来源仍指回原动作，不重算另一套时钟。
    action_map = {row["action_id"]: row for row in actions}
    for chain_id, lead in (("AirChain01", "Fly01"), ("AirChain02", "Fly02")):
        assembly = assemblies[chain_id]
        sections = {segment["section"]: segment for segment in assembly["segments"]}
        source_regions = [(lead, sections["Main"]["expected_start_seconds"], sections["Main"]["expected_end_seconds"]),
                          ("Fly03", sections["CastPrepare"]["expected_start_seconds"], sections["CastRecovery"]["expected_end_seconds"]),
                          ("Fire04", sections["End"]["expected_start_seconds"], sections["End"]["expected_end_seconds"])]
        persistent = dict(action_map["Fly03"]["persistent_audio"])
        actions.append({"action_id": chain_id, "source_action_ids": [region[0] for region in source_regions],
                        "binding_basis": "project_authored_owned_air_chain", "original_action_mapping_verified": False,
                        "enable_gate": assembly["enable_gate"], "persistent_audio": persistent,
                        "hit_cue_owner": "FX", "hit_cue_config": HIT_CUE_CONFIG,
                        "hit_cue_keys": [region[0] for region in source_regions],
                        "hit_authority": "GA authenticated hit-window source_action_id"})
        for phase in assembly["animation_phases"]:
            if phase["role"] != "active":
                continue
            start, end = phase["window_seconds"]
            regions = [region for region in source_regions if region[1] <= start < region[2] and end <= region[2]]
            require(len(regions) == 1, "空中链阶段没有唯一原动作区间：" + chain_id + "/" + phase["phase_id"])
            source_action, offset, _ = regions[0]
            event_id = action_map[source_action]["point_event_id"]
            for group_index, sound in enumerate(event_map[event_id]["sound_cues"]):
                key = chain_id + "." + phase["phase_id"] + ".E" + str(event_id) + "." + str(group_index + 1)
                montage_events.append({"event_key": key, "action_id": chain_id, "phase_id": phase["phase_id"],
                                       "source_action_id": source_action, "source_offset_seconds": offset,
                                       "event_id": event_id, "time_seconds": start, "sound": sound,
                                       "parameters": {"volume": 1.0, "pitch": 1.0, "follow": True, "attach_name": "None"},
                                       "source_window_seconds": [start, end], "timing_basis": phase["timing_basis"],
                                       "binding_basis": action_map[source_action].get("point_binding_basis", action_map[source_action]["binding_basis"]),
                                       "enable_gate": assembly["enable_gate"], "original_timing_verified": False})
        charge = next(phase for phase in assembly["animation_phases"] if phase["phase_id"] == "CastWarning")
        persistent_windows.append({"action_id": chain_id, "phase_id": charge["phase_id"],
                                   "source_action_id": "Fly03", "window_seconds": charge["window_seconds"],
                                   "begin_tag": persistent["begin_tag"], "end_tag": persistent["end_tag"],
                                   "original_timing_verified": False, "timing_basis": charge["timing_basis"]})
        held.append({"key": chain_id + "Charge", "action_id": chain_id, "source_action_id": "Fly03",
                     "event_id": 2524282819, "enabled": True, "persistent_audio": persistent,
                     "begin_phase": "CastWarning.Begin", "end_phase": "CastWarning.End",
                     "binding_basis": "project_authored_owned_air_chain", "original_trigger_seconds": None,
                     "cleanup_owner": "original GA AudioActor -> original AudioComponent; retire original identity",
                     "retire_on": ["phase_end", "normal_end", "cancel", "death", "target_invalid"],
                     "finite_source_is_not_forced_to_loop": True})
    state_candidates = [
        {"state": "MoveLeft", "phase_id": "foot_left", "event_id": 2736721907},
        {"state": "MoveRight", "phase_id": "foot_right", "event_id": 2736721901},
        {"state": "WingDefence", "phase_id": "receive_hit", "event_id": 2190265172},
        {"state": "WingDefence", "phase_id": "ground_contact", "event_id": 2218789460},
        {"state": "LandingRecovery", "phase_id": "Impact", "event_id": 1107709958}]
    for state in state_candidates:
        state.update(sound_cues=event_map[state["event_id"]]["sound_cues"],
                     binding_basis="project_candidate_original_boss_event", original_timing_verified=False,
                     time_seconds=None, time_owner="Animation")
    landing = next(row for row in animation["presentation_contracts"] if row["id"] == "LandingRecovery")
    require(landing["trigger"] == "real_landed_only"
            and landing["movement_mode"] == "presentation_only_no_CMC_curve_execution",
            "落地声音需要真实 Landed 后的纯表现恢复契约")
    impact = next(phase for phase in landing["animation_phases"] if phase["phase_id"] == "Impact")
    start, end = impact["window_seconds"]
    require(math.isfinite(start) and 0 <= start < end <= landing["expected_duration_seconds"],
            "落地恢复 Impact 阶段越界")
    state = next(row for row in state_candidates if row["state"] == "LandingRecovery")
    state.update(enabled=True, trigger_authority=landing["trigger"], time_seconds=start,
                 montage=landing["montage"], section=landing["section"],
                 movement_mode=landing["movement_mode"], source_window_seconds=[start, end],
                 timing_basis=impact["timing_basis"])
    for group_index, sound in enumerate(state["sound_cues"]):
        montage_events.append({"event_key": "LandingRecovery.Impact.E1107709958." + str(group_index + 1),
                               "action_id": "LandingRecovery", "phase_id": "Impact", "source_action_id": "Fire04",
                               "event_id": 1107709958, "time_seconds": start, "sound": sound,
                               "parameters": {"volume": 1.0, "pitch": 1.0, "follow": True, "attach_name": "None"},
                               "montage": landing["montage"], "section": landing["section"],
                               "trigger_authority": landing["trigger"], "movement_mode": landing["movement_mode"],
                               "source_window_seconds": [start, end], "timing_basis": impact["timing_basis"],
                               "binding_basis": "project_real_landed_original_SFX_candidate",
                               "enable_gate": "", "original_timing_verified": False})
    substitutes = {3067816605: (3286683035, "Fire02 有限蓄力流，须由原 GA 认证窗退役"),
                   39755540: (3779481217, "Fly01 飞行流，需先确认 Fire04 下降阶段的项目适配")}
    for gap in gaps:
        if gap["event_id"] in substitutes:
            candidate, reason = substitutes[gap["event_id"]]
            gap["project_substitute"] = {"event_id": candidate,
                                         "sound_cues": event_map[candidate]["sound_cues"],
                                         "enabled": False, "basis": reason, "original_mapping_verified": False}
    sources = [identity(manifest_path), identity(graph_path), identity(xml_path)] + list(source_inputs.values())
    return {"schema_version": 1, "task_id": "KVB-20261105-01", "status": "offline_prepared_not_UE_executed",
            "source_inputs": sources, "soundwaves": waves, "sound_cues": sound_cues,
            "attenuations": [{"target": ATTENUATION, "radius_cm": 150.0, "falloff_cm": 2500.0,
                              "distance_model": "LINEAR", "shape": "SPHERE", "spatialize": True,
                              "basis": "project_authored_tunable_not_original_Wwise_attenuation"}],
            "hit_bindings": hit_bindings, "actions": actions, "owned_audio": held,
            "montage_events": montage_events, "persistent_windows": persistent_windows,
            "animation_timing_source": {"path": str(MONTAGE_CONFIG),
                                        "fields": "skill_assemblies.id/animation_phases/window_seconds/enable_gate; presentation_contracts.id/montage/section/trigger/movement_mode/animation_phases",
                                        "invalidate_on": "对应窗口、组装时长、启用门或表现触发契约变化；Animation 落Notify前核原窗口"},
            "required_tags": ["Event.Montage.AudioWindowBegin", "Event.Montage.AudioWindowEnd"],
            "state_candidates": state_candidates,
            "source_gaps": gaps + [
                {"event_id": 35317695, "event_name": "BOSS_411_FX_ICE_ATTACK_HINT", "missing_nodes": [106982489]},
                {"event_id": 575525440, "event_name": "BOSS_411_FX_WING_DEFENCE_HIT_ENEMY_BACK", "missing_nodes": [201801434]},
                {"state": "Death/Enter/HitReaction", "status": "no_verified_DemonBattle_action_binding",
                 "candidate_policy": "不借 FAKEKEVIN/ABYSS 语音，不自动把父动作声音继承给状态",
                 "implementable_candidates": [
                     {"use": "death_ice_shatter", "event_id": 549475289,
                      "sound_cues": event_map[549475289]["sound_cues"], "enabled": False},
                     {"use": "death_fire_dissipation", "event_id": 2564483858,
                      "sound_cues": event_map[2564483858]["sound_cues"], "enabled": False},
                     {"use": "physical_hit_reaction", "event_id": 2190265172,
                      "sound_cues": event_map[2190265172]["sound_cues"], "enabled": False}],
                 "candidate_basis": "project_adaptation_original_SFX_not_original_state_voice"}],
            "production_contract": {
                "montage_writer": "Animation", "GA_writer": "Combat", "exact_save_owner": "Root",
                "point_lifetime": "natural_end", "owned_lifetime": "GA retires original replicated AudioActor and component",
                "persistent_audio_events": ["Event.Montage.AudioWindowBegin", "Event.Montage.AudioWindowEnd"],
                "random_policy": "UE 原生不放回随机为项目配置；不声称等同 Wwise avoid-repeat 算法",
                "mix_policy": "原单声/随机/无动态参数静态层已拆成播放组；音量0.7、音高1为可调项目混音",
                "loop_policy": "只对原 Loop=0 的流启用 WavePlayer 循环；原循环边界与无缝性仍待试听",
                "readiness": "制作 SoundCue 可独立推进；点声时间已投影当前 Animation 项目阶段，原声时点仍未知"}}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write-config", action="store_true", help="只创建不存在的实际消费配置")
    args = parser.parse_args()
    config = build_config()
    if args.write_config:
        require(not CONFIG.exists(), "配置已存在，禁止自动覆盖作者调参")
        text = json.dumps(config, ensure_ascii=False, indent=2) + "\n"
        require(len(text.encode("utf-8")) <= 210 * 1024, "配置超出本批小文件预算")
        CONFIG.write_text(text, encoding="utf-8")
    print(json.dumps({"config": str(CONFIG), "existing_SW": sum(w["existing"] for w in config["soundwaves"]),
                      "new_SW": sum(not w["existing"] for w in config["soundwaves"]),
                      "new_source_bytes": sum(w["source"]["size"] for w in config["soundwaves"] if not w["existing"]),
                      "sound_cues": len(config["sound_cues"]), "FX_hit_bindings": len(config["hit_bindings"]),
                      "actions": len(config["actions"]), "UE_executed": False}, ensure_ascii=False))
