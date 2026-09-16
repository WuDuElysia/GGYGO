# -*- coding: utf-8 -*-
"""
verify_anim_rootmotion_curves.py —— 只读校验：回读全部 119 个 AnimSequence 的曲线，
与 anim_rootmotion_extract.py 的源数据逐点比对。不写任何资产。

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/verify_anim_rootmotion_curves.py", encoding="utf-8").read())

查两件事：
  1. 帧时间点上的值是否与源数据一致（写入正确性）。
  2. 相邻两帧中点是否落在两端值之间（插值形状）。若 key 用的是三次插值，
     中点会冲出两端区间，运行时在非帧时刻采样就会读到源数据里不存在的值。
     位移曲线过冲会造成速度尖峰，方向曲线过冲会让归一化方向超出 ±1。
"""

import json
import os

import unreal

SOURCE_JSON = r"F:/ue_project/GGYGO/Saved/AnimRootMotion/Pyrios_RootMotion.json"
ANIM_FOLDER = "/Game/Characters/Player/Pyrios/Animation"
REPORT = r"F:/ue_project/GGYGO/Saved/AnimRootMotion/VerifyReport.json"

MOTION_CURVES = [
    "RootMotion_PosX", "RootMotion_PosY", "RootMotion_PosZ",
    "RootMotion_Yaw", "RootMotion_Pitch", "RootMotion_Roll",
    "RootMotion_Dist", "RootMotion_Speed",
    "RootMotion_DirX", "RootMotion_DirY",
]

# 每条曲线取这么多个均匀分布的帧做比对，避免全量采样把编辑器卡太久
SAMPLES_PER_CURVE = 24


def read_at(anim, name, t):
    return float(unreal.AnimationLibrary.get_float_value_at_time(
        anim, unreal.Name(name), float(t)))


def run():
    with open(SOURCE_JSON, "r", encoding="utf-8") as f:
        clips = json.load(f)["clips"]

    worst_value = (0.0, "", "")      # (误差, clip, curve)
    worst_overshoot = (0.0, "", "")  # (超出区间的量, clip, curve)
    missing_curves = []
    missing_assets = []
    checked_points = 0
    per_clip = []

    for rec in clips:
        name = rec["name"]
        anim = unreal.load_asset("%s/%s" % (ANIM_FOLDER, name))
        if anim is None:
            missing_assets.append(name)
            continue

        times = rec["times"]
        n = len(times)
        idxs = sorted(set(
            [0, n - 1] + [i * (n - 1) // (SAMPLES_PER_CURVE - 1)
                          for i in range(SAMPLES_PER_CURVE)]))

        clip_err = 0.0
        clip_over = 0.0
        for curve in MOTION_CURVES:
            src = rec["curves"].get(curve)
            if src is None:
                continue
            if not unreal.AnimationLibrary.does_curve_exist(
                    anim, unreal.Name(curve), unreal.RawCurveTrackTypes.RCT_FLOAT):
                missing_curves.append("%s/%s" % (name, curve))
                continue

            for i in idxs:
                got = read_at(anim, curve, times[i])
                err = abs(got - src[i])
                checked_points += 1
                if err > clip_err:
                    clip_err = err
                if err > worst_value[0]:
                    worst_value = (err, name, curve)

                # 帧间中点的过冲检查
                if i + 1 < n:
                    lo = min(src[i], src[i + 1])
                    hi = max(src[i], src[i + 1])
                    mid_t = 0.5 * (times[i] + times[i + 1])
                    mid = read_at(anim, curve, mid_t)
                    over = max(lo - mid, mid - hi, 0.0)
                    if over > clip_over:
                        clip_over = over
                    if over > worst_overshoot[0]:
                        worst_overshoot = (over, name, curve)

        per_clip.append({"name": name, "maxErr": clip_err, "maxOvershoot": clip_over})

    per_clip.sort(key=lambda d: -d["maxErr"])
    unreal.log("=" * 78)
    unreal.log("[Verify] 比对点数 %d，clip %d，缺资产 %d，缺曲线 %d"
               % (checked_points, len(per_clip), len(missing_assets),
                  len(missing_curves)))
    unreal.log("[Verify] 帧点最大误差 %.6g  (%s / %s)"
               % (worst_value[0], worst_value[1], worst_value[2]))
    unreal.log("[Verify] 帧间中点最大过冲 %.6g  (%s / %s)"
               % (worst_overshoot[0], worst_overshoot[1], worst_overshoot[2]))
    unreal.log("[Verify] 帧点误差最大的 5 个 clip:")
    for d in per_clip[:5]:
        unreal.log("    err=%.6g overshoot=%.6g  %s"
                   % (d["maxErr"], d["maxOvershoot"], d["name"]))
    over_sorted = sorted(per_clip, key=lambda d: -d["maxOvershoot"])
    unreal.log("[Verify] 过冲最大的 5 个 clip:")
    for d in over_sorted[:5]:
        unreal.log("    overshoot=%.6g err=%.6g  %s"
                   % (d["maxOvershoot"], d["maxErr"], d["name"]))
    for m in missing_curves[:10]:
        unreal.log_warning("    缺曲线: %s" % m)
    for m in missing_assets:
        unreal.log_warning("    缺资产: %s" % m)

    try:
        os.makedirs(os.path.dirname(REPORT), exist_ok=True)
        with open(REPORT, "w", encoding="utf-8") as f:
            json.dump({
                "checkedPoints": checked_points,
                "worstValueError": {"error": worst_value[0],
                                    "clip": worst_value[1],
                                    "curve": worst_value[2]},
                "worstOvershoot": {"overshoot": worst_overshoot[0],
                                   "clip": worst_overshoot[1],
                                   "curve": worst_overshoot[2]},
                "missingCurves": missing_curves,
                "missingAssets": missing_assets,
                "perClip": per_clip,
            }, f, ensure_ascii=False, indent=1)
    except Exception as exc:
        unreal.log_warning("[Verify] 写报告失败: %s" % exc)

    unreal.log("[Verify] done.")


run()
