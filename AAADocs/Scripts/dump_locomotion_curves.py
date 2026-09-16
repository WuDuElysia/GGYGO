# -*- coding: utf-8 -*-
"""从 anim_rootmotion_extract.py 的中间数据里打印 locomotion 动作的曲线形状。

纯本地读取，不碰 UE。用于在写运行时逻辑之前看清 TurnBack 等动作的
yaw / 位移 / 速度随时间的真实走向。

用法： python dump_locomotion_curves.py [clip名子串 ...]
"""
import json
import sys

SRC = r"F:\ue_project\GGYGO\Saved\AnimRootMotion\Pyrios_RootMotion.json"

DEFAULT = ["Ani_TurnBack", "Ani_Walk_Start", "Ani_Walk_Loop", "Ani_Walk_End",
           "Ani_Walk_Start_End", "Ani_Run_Loop", "Ani_Run_End"]

SAMPLES = 30

with open(SRC, "r", encoding="utf-8") as f:
    clips = {c["name"]: c for c in json.load(f)["clips"]}

wanted = sys.argv[1:] or DEFAULT

for sub in wanted:
    hits = [n for n in sorted(clips) if sub in n]
    for name in hits:
        c = clips[name]
        t = c["times"]
        cur = c["curves"]
        n = len(t)
        sc = c["scalars"]
        print("=" * 100)
        print("%s" % name)
        print("  fbxLen=%.4f clipLen=%.4f frames=%d dup=%s loopTime=%s cycleOffset=%s"
              % (c["duration"], c["clipLength"], n,
                 c["trailingDuplicateFrame"], sc.get("loopTime"),
                 sc.get("cycleOffset")))
        v = c["verify"]
        print("  path=%.1fcm peak=%.1fcm/s@f%d maxStep=%.2fcm yawEnd=%.2f jsonAvgSpeed=%.1f"
              % (v["pathLengthCm"], v["peakSpeedCms"], v["peakSpeedFrame"],
                 v["maxFrameStepCm"], v["fbxYawDeg"], v["jsonAvgSpeedCms"]))
        print("  %6s %6s | %9s %9s | %8s %9s | %7s %7s"
              % ("frame", "t", "PosX", "PosY", "Yaw", "Speed", "DirX", "DirY"))
        step = max(1, (n - 1) // SAMPLES)
        idxs = list(range(0, n, step))
        if idxs[-1] != n - 1:
            idxs.append(n - 1)
        for i in idxs:
            print("  %6d %6.3f | %9.2f %9.2f | %8.2f %9.1f | %7.3f %7.3f"
                  % (i, t[i], cur["RootMotion_PosX"][i], cur["RootMotion_PosY"][i],
                     cur["RootMotion_Yaw"][i], cur["RootMotion_Speed"][i],
                     cur["RootMotion_DirX"][i], cur["RootMotion_DirY"][i]))
