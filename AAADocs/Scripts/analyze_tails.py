# -*- coding: utf-8 -*-
"""分析各动画"位移结束"与"clip 结束"之间的尾巴，判断尾巴是有意保留还是制作副产物。

判据：
  - activeEnd = 最后一帧速度超过阈值的时间（动作实际结束）
  - tail      = clipLength - activeEnd
  - 若尾巴长度在同类动画间高度一致 → 更可能是有意的统一约定
  - 若尾巴长度散乱、且原地动画整段都是 0 → 更可能是"这段动画本来就没位移"

同时统计原地动画（全程零位移）的占比，因为对它们而言"尾巴"这个概念不成立。
"""
import json
from collections import defaultdict

SRC = r"F:\ue_project\GGYGO\Saved\AnimRootMotion\Pyrios_RootMotion.json"
SPEED_EPS = 1.0   # cm/s，低于此视为静止

with open(SRC, "r", encoding="utf-8") as f:
    clips = json.load(f)["clips"]

rows = []
for c in clips:
    t = c["times"]
    sp = c["curves"]["RootMotion_Speed"]
    dist = c["curves"]["RootMotion_Dist"][-1]
    clip_len = c["clipLength"]

    # 最后一个速度超阈值的帧
    active_end_idx = -1
    for i in range(len(sp) - 1, -1, -1):
        if sp[i] > SPEED_EPS:
            active_end_idx = i
            break
    # 第一个速度超阈值的帧
    active_start_idx = -1
    for i, v in enumerate(sp):
        if v > SPEED_EPS:
            active_start_idx = i
            break

    if active_end_idx < 0:
        rows.append((c["name"], clip_len, None, None, dist, True))
        continue

    active_end = t[active_end_idx]
    tail = clip_len - active_end
    rows.append((c["name"], clip_len, active_end, tail, dist, False))

static = [r for r in rows if r[5]]
moving = [r for r in rows if not r[5]]

print("clip 总数 = %d" % len(rows))
print("全程零位移（原地动画，尾巴概念不成立）= %d" % len(static))
print("有位移 = %d\n" % len(moving))

print("=== 有位移的动画：clipLength / 位移结束 / 尾巴 / 总路程 ===")
print("%-56s %8s %8s %8s %9s" % ("name", "clipLen", "actEnd", "tail", "path"))
for name, cl, ae, tail, dist, _ in sorted(moving, key=lambda r: -r[3]):
    print("%-56s %8.3f %8.3f %8.3f %9.1f"
          % (name.replace("Avatar_Male_Size03_Pyrois_", ""), cl, ae, tail, dist))

tails = [r[3] for r in moving]
print("\n尾巴统计（有位移的 %d 个）：" % len(moving))
print("  最小 %.3f  最大 %.3f  平均 %.3f" % (min(tails), max(tails), sum(tails) / len(tails)))

# 尾巴长度的分布：看是否聚集在某几个值
buckets = defaultdict(list)
for name, cl, ae, tail, dist, _ in moving:
    buckets[round(tail, 2)].append(name)
print("\n尾巴长度分布（按 0.01s 归并，只列出现 2 次以上的）：")
for k in sorted(buckets, reverse=True):
    if len(buckets[k]) >= 2:
        print("  %.2fs × %d" % (k, len(buckets[k])))

# 一帧的尾巴有多少个（对应"末尾重复帧"）
one_frame = [r for r in moving if abs(r[3]) < 0.02]
print("\n尾巴 < 0.02s（基本贴着 clip 末尾结束）= %d 个" % len(one_frame))

# locomotion 关注的那几个
print("\n=== locomotion 关注项 ===")
focus = ["Ani_Walk_Start", "Ani_Walk_Loop", "Ani_Walk_End", "Ani_Walk_Start_End",
         "Ani_Run_Loop", "Ani_Run_End", "Ani_TurnBack"]
by_name = {r[0]: r for r in rows}
for f_ in focus:
    for full, r in by_name.items():
        if full.endswith(f_):
            name, cl, ae, tail, dist, st = r
            if st:
                print("  %-24s clipLen=%.3f  全程零位移" % (f_, cl))
            else:
                print("  %-24s clipLen=%.3f  位移结束=%.3f  尾巴=%.3f (%.0f%%)  路程=%.1f"
                      % (f_, cl, ae, tail, 100.0 * tail / cl, dist))
            break
