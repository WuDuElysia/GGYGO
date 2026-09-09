# -*- coding: utf-8 -*-
"""
diag_rootmotion_source.py —— 只读诊断：找出 AnimSequence 里到底哪根骨骼承载位移/转身

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/diag_rootmotion_source.py", encoding="utf-8").read())

只读日志，不写任何资产。用于确定：
  - 骨架里实际存在的骨骼轨道名；
  - 哪根骨骼在整段动画里位移最大（真正的 root motion 平移源）；
  - Root（及候选骨骼）的 yaw 是台阶突变还是渐变；
  - 资产上已有的浮点曲线名（看看 velocitycurvex/y 之类还在不在）。
"""

import unreal
import math

ANIM = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
        "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack")
USE_RAW = True
CAND = ["Root", "Bone_Root", "Loc_Character", "Bip001",
        "Bip001 Pelvis", "Bip001 Spine", "Bip001 Spine1"]
TRACE_SAMPLES = 24


def num_keys(a):
    try:
        return unreal.AnimationLibrary.get_num_frames(a) + 1
    except Exception:
        try:
            return a.get_number_of_sampled_keys()
        except Exception:
            return a.get_number_of_keys()


def pose(a, bone, f):
    return unreal.AnimationLibrary.get_bone_pose_for_frame(a, bone, f, USE_RAW)


def bone_track_names(a):
    for getter in ("get_data_model", "get_data_model_interface"):
        try:
            dm = getattr(a, getter)()
            names = dm.get_bone_track_names()
            return [str(x) for x in names]
        except Exception:
            continue
    return []


def curve_names(a):
    for call in (
        lambda: unreal.AnimationLibrary.get_animation_curve_names(
            a, unreal.RawCurveTrackTypes.RCT_FLOAT),
        lambda: a.get_curve_names(unreal.RawCurveTrackTypes.RCT_FLOAT),
    ):
        try:
            return [str(x) for x in call()]
        except Exception:
            continue
    return []


def run():
    a = unreal.load_asset(ANIM)
    if not isinstance(a, unreal.AnimSequence):
        unreal.log_warning("不是 AnimSequence: %s" % ANIM)
        return
    n = num_keys(a)
    unreal.log("=" * 64)
    unreal.log("[Diag] %s  keys=%d" % (a.get_name(), n))

    # 1) 实际骨骼轨道名
    names = bone_track_names(a)
    unreal.log("[Diag] 骨骼轨道数=%d" % len(names))
    if names:
        unreal.log("       " + ", ".join(names[:50]))

    # 2) 找位移最大的骨骼：遍历实际轨道名（没有则用候选表）
    scan = names if names else CAND
    movers = []
    for b in scan:
        try:
            p0 = pose(a, b, 0)
            p1 = pose(a, b, n - 1)
            # 逐帧累计位移，避免首尾相同却中途跑一圈的情况被漏掉
            path = 0.0
            prev = pose(a, b, 0).translation
            for i in range(1, n):
                cur = pose(a, b, i).translation
                path += math.hypot(cur.x - prev.x, cur.y - prev.y)
                prev = cur
            dx = p1.translation.x - p0.translation.x
            dy = p1.translation.y - p0.translation.y
            y0 = p0.rotation.rotator().yaw
            y1 = p1.rotation.rotator().yaw
            movers.append((path, b, dx, dy, y0, y1))
        except Exception:
            pass
    movers.sort(reverse=True)
    unreal.log("[Diag] 位移排行（累计水平路径 path，前 12）：")
    unreal.log("        path      dX      dY    yaw0    yaw1  bone")
    for path, b, dx, dy, y0, y1 in movers[:12]:
        unreal.log("     %8.2f %7.2f %7.2f %7.1f %7.1f  %s"
                   % (path, dx, dy, y0, y1, b))

    # 3) Root 的 yaw / 平移逐帧轨迹（看台阶还是渐变）
    unreal.log("[Diag] Root 逐帧 yaw / T：")
    unreal.log("        i    yaw   pitch    roll        Tx        Ty        Tz")
    step = max(1, n // TRACE_SAMPLES)
    for i in range(0, n, step):
        r = pose(a, "Root", i).rotation.rotator()
        t = pose(a, "Root", i).translation
        unreal.log("     %4d %7.1f %7.1f %7.1f %9.2f %9.2f %9.2f"
                   % (i, r.yaw, r.pitch, r.roll, t.x, t.y, t.z))

    # 4) 已有浮点曲线名
    cn = curve_names(a)
    unreal.log("[Diag] 浮点曲线数=%d" % len(cn))
    if cn:
        unreal.log("       " + ", ".join(cn))
    unreal.log("[Diag] done.")


run()
