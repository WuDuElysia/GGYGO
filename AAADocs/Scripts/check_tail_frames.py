# -*- coding: utf-8 -*-
"""核对 locomotion 动作的末尾若干帧与首尾衔接，判断"末尾重复帧"这个判定是否与数据相符。

关心三件事：
  1. 末帧的位移是否真的等于倒数第二帧（重复帧的定义）。
  2. 循环动画（loopTime=True）首帧与"有效末帧"的速度是否连续，决定循环点会不会顿一下。
  3. clipLength 对应的帧索引落在哪里。
"""
import json

SRC = r"F:\ue_project\GGYGO\Saved\AnimRootMotion\Pyrios_RootMotion.json"
NAMES = ["Ani_TurnBack", "Ani_Run_Loop", "Ani_Walk_Loop", "Ani_Walk_Start",
         "Ani_Walk_End", "Ani_Walk_Start_End", "Ani_Run_End"]

with open(SRC, "r", encoding="utf-8") as f:
    clips = {c["name"]: c for c in json.load(f)["clips"]}

for sub in NAMES:
    for name in [n for n in sorted(clips) if sub in n]:
        c = clips[name]
        t, cur = c["times"], c["curves"]
        px, py = cur["RootMotion_PosX"], cur["RootMotion_PosY"]
        sp, yaw = cur["RootMotion_Speed"], cur["RootMotion_Yaw"]
        n = len(t)
        dt = 1.0 / (c["sampleRate"] or 60.0)
        # clipLength 对应的帧索引
        eff = int(round(c["clipLength"] / dt))
        print("=" * 92)
        print("%s  frames=%d dup=%s loopTime=%s" % (name, n,
              c["trailingDuplicateFrame"], c["scalars"].get("loopTime")))
        print("  fbxLen=%.4f clipLen=%.4f -> clipLength 对应帧索引 %d (末帧索引 %d)"
              % (c["duration"], c["clipLength"], eff, n - 1))
        print("  末 4 帧:")
        for i in range(max(0, n - 4), n):
            print("     f%-4d t=%.4f PosX=%9.3f PosY=%8.3f Speed=%8.1f Yaw=%8.2f"
                  % (i, t[i], px[i], py[i], sp[i], yaw[i]))
        d_last = abs(px[-1] - px[-2]) + abs(py[-1] - py[-2])
        print("  末帧与倒数第二帧的位移差 = %.6f cm  -> %s"
              % (d_last, "是重复帧" if d_last < 1e-4 else "不是重复帧"))
        if c["scalars"].get("loopTime"):
            # 循环点：有效末帧(索引 eff) 接回首帧
            i_eff = min(eff, n - 1)
            step_loop = abs(px[i_eff] - px[i_eff - 1])
            print("  循环点检查: f0 Speed=%.1f, f%d Speed=%.1f, f%d 单帧位移=%.3f cm"
                  % (sp[0], i_eff, sp[i_eff], i_eff, step_loop))
            print("             每帧应走 %.3f cm (按 f%d 位移 %.3f / %d 个间隔)"
                  % (px[i_eff] / max(i_eff, 1), i_eff, px[i_eff], i_eff))
