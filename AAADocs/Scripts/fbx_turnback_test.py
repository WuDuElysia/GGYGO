"""
Pyrios TurnBack 离线验证工具。

用途：
  - 读取二进制 FBX 中 TurnBack 的 Root/Bone_Root/Bip001 层级与轨道；
  - 导出一个小型 JSON 测试副本，不修改原始 FBX / UAsset；
  - 用 Root 的 -180 度时间曲线作为“转身时序”，模拟把它重定向到任意输入夹角；
  - 验证“动画只提供姿态时序、Actor 由代码按实际输入角度转向”的数学关系。

用法：
  python fbx_turnback_test.py <fbx> [输出目录]
"""

from __future__ import annotations

import json
import math
import os
import sys
from pathlib import Path

from fbx_anim_extract import FbxReader, FBXTIME, build_index, get_curve_arrays, resolve_take_curvenodes

TAKE_SUBSTRING = "Avatar_Male_Size03_Pyrois_Ani_TurnBack"
KEY_NODES = ["Root", "Bone_Root", "Bip001", "Bip001 Pelvis", "Loc_Character"]
KEY_PROPS = ["Lcl Translation", "Lcl Rotation"]
KEY_CHANNELS = ["X", "Y", "Z"]


def find_take(idx):
    matches = [(sid, name) for sid, name in idx["stacks"].items() if TAKE_SUBSTRING.lower() in name.lower()]
    if not matches:
        raise RuntimeError(f"没有找到 take: {TAKE_SUBSTRING}")
    return matches[0]


def node_id_by_clean_name(idx, clean_name):
    for node_id, name in idx["model_id2name"].items():
        if name.split(chr(0))[0] == clean_name:
            return node_id
    return None


def hierarchy(idx):
    result = {}
    for name in KEY_NODES:
        node_id = node_id_by_clean_name(idx, name)
        if node_id is None:
            result[name] = {"found": False}
            continue
        parents = []
        children = []
        for parent_id, prop in idx["parent_conns"].get(node_id, []):
            parent_name = idx["model_id2name"].get(parent_id, str(parent_id)).split(chr(0))[0]
            parents.append({"name": parent_name, "property": prop})
        for child_id, prop in idx["child_conns"].get(node_id, []):
            if child_id in idx["model_id2name"]:
                child_name = idx["model_id2name"][child_id].split(chr(0))[0]
                children.append({"name": child_name, "property": prop})
        result[name] = {
            "found": True,
            "id": node_id,
            "parents": parents,
            "children": children,
        }
    return result


def extract_track(r, idx, curve_nodes, node_name, prop, channel):
    curve_id = curve_nodes.get(node_name, {}).get(prop, {}).get(channel)
    if curve_id is None:
        return None
    times, values = get_curve_arrays(r.f, idx["curves"][curve_id])
    return {
        "times": [float(t) / FBXTIME for t in times],
        "values": [float(v) for v in values],
    }


def sample_linear(track, normalized_time):
    if not track or not track["times"]:
        return 0.0
    times = track["times"]
    values = track["values"]
    if len(times) == 1:
        return values[0]
    start = times[0]
    end = times[-1]
    t = start + (end - start) * max(0.0, min(1.0, normalized_time))
    if t <= times[0]:
        return values[0]
    if t >= times[-1]:
        return values[-1]
    for i in range(1, len(times)):
        if t <= times[i]:
            alpha = (t - times[i - 1]) / (times[i] - times[i - 1])
            return values[i - 1] + (values[i] - values[i - 1]) * alpha
    return values[-1]


def shortest_delta(from_yaw, to_yaw):
    return (to_yaw - from_yaw + 180.0) % 360.0 - 180.0


def build_fixture(r, idx, stack_id, stack_name):
    curve_nodes = resolve_take_curvenodes(idx, stack_id)
    tracks = {}
    for node_name in KEY_NODES:
        for prop in KEY_PROPS:
            for channel in KEY_CHANNELS:
                track = extract_track(r, idx, curve_nodes, node_name, prop, channel)
                if track is not None:
                    tracks.setdefault(node_name, {}).setdefault(prop, {})[channel] = track

    all_times = []
    for node_props in tracks.values():
        for channel_props in node_props.values():
            for track in channel_props.values():
                all_times.extend(track["times"])
    duration = max(all_times) - min(all_times) if all_times else 0.0

    root_yaw = tracks.get("Root", {}).get("Lcl Rotation", {}).get("Y")
    if not root_yaw:
        raise RuntimeError("TurnBack 没有 Root.Lcl Rotation.Y 轨道")
    yaw_start = root_yaw["values"][0]
    yaw_end = root_yaw["values"][-1]
    yaw_delta = shortest_delta(yaw_start, yaw_end)

    # 用 Root 的原始转身轨道作为“时间权重”。
    # progress=0 表示不转，progress=1 表示动画转身时序结束。
    samples = []
    sample_count = 24
    for index in range(sample_count):
        normalized = index / float(sample_count - 1)
        source_yaw = sample_linear(root_yaw, normalized)
        source_progress = shortest_delta(yaw_start, source_yaw) / yaw_delta if abs(yaw_delta) > 1e-6 else 0.0
        source_progress = max(0.0, min(1.0, source_progress))
        samples.append({
            "normalized": normalized,
            "source_root_yaw": source_yaw,
            "turn_progress": source_progress,
            "root_translation_z": sample_linear(
                tracks.get("Root", {}).get("Lcl Translation", {}).get("Z"), normalized),
        })

    # 以一个假想进入朝向 0 度，验证不同输入夹角的代码目标。
    # 这里的“代码重定向”只使用 progress * desired_delta，动画不再决定最终角度。
    retarget_cases = []
    for desired_delta in [180.0, 135.0, 90.0, 45.0, -90.0, -135.0]:
        output = []
        for sample in samples:
            actor_yaw = sample["turn_progress"] * desired_delta
            output.append({
                "normalized": sample["normalized"],
                "turn_progress": sample["turn_progress"],
                "actor_yaw": actor_yaw,
            })
        retarget_cases.append({
            "desired_delta": desired_delta,
            "final_actor_yaw": output[-1]["actor_yaw"],
            "samples": output,
        })

    return {
        "source_take": stack_name,
        "duration_seconds": duration,
        "hierarchy": hierarchy(idx),
        "tracks": tracks,
        "source_root_yaw": {
            "start": yaw_start,
            "end": yaw_end,
            "shortest_delta": yaw_delta,
        },
        "turnback_progress_samples": samples,
        "retarget_cases": retarget_cases,
        "test_copy_policy": {
            "original_fbx_modified": False,
            "asset_copy_kind": "JSON轨道副本，仅用于离线验证",
            "root_yaw_used_as_timing_only": True,
            "desired_angle_is_runtime_input_angle": True,
        },
    }


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        raise SystemExit(2)
    fbx_path = Path(sys.argv[1])
    output_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(__file__).resolve().parents[1] / "Tests" / "PyriosTurnBack"
    output_dir.mkdir(parents=True, exist_ok=True)

    reader = FbxReader(str(fbx_path))
    roots = reader.parse()
    idx = build_index(roots)
    stack_id, stack_name = find_take(idx)
    fixture = build_fixture(reader, idx, stack_id, stack_name)
    reader.close()

    output_path = output_dir / "turnback_test_copy.json"
    output_path.write_text(json.dumps(fixture, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"take={stack_name}")
    print(f"duration={fixture['duration_seconds']:.6f}s")
    print(f"root_yaw={fixture['source_root_yaw']}")
    print(f"output={output_path}")
    print("retarget_final=" + ", ".join(
        f"{case['desired_delta']:.0f}->{case['final_actor_yaw']:.2f}"
        for case in fixture["retarget_cases"]
    ))


if __name__ == "__main__":
    main()
