# -*- coding: utf-8 -*-
"""统计 anim/ 目录下按动作拆分的 per-clip JSON：字段集合、曲线是否含有效数值、标量设置分布。

判定“曲线有效”的口径：
  - 平移分量（*T.x/y/z）出现过非 0 值；
  - 四元数分量（*Q.x/y/z/w）出现过非 0 值，且 w 至少有一帧接近 ±1（否则是未填充的占位）。

用法： python anim_json_stats.py [anim目录]
"""
import glob
import json
import os
import sys
from collections import Counter

root = sys.argv[1] if len(sys.argv) > 1 else \
    r"F:\AnimeStudio\Exports\ZZZ\Avatar_Male_Size03_Pyrois_Model\anim"

files = sorted(glob.glob(os.path.join(root, "*.json")))
print("json 文件数 =", len(files))

top_keys = Counter()
clip_keys = Counter()
muscle_keys = Counter()
attr_present = Counter()
attr_nonzero = Counter()
qw_valid = Counter()
total_keys = 0
nonzero_clips = set()
loop_true = []
ang_speed = []
avg_speed = []

for fp in files:
    with open(fp, "r", encoding="utf-8") as f:
        d = json.load(f)
    top_keys.update(d.keys())
    clip = d.get("clip") or {}
    clip_keys.update(k for k in clip.keys() if k != "rootMotionCurves")
    mc = clip.get("muscleClip") or {}
    muscle_keys.update(mc.keys())

    name = clip.get("name") or os.path.splitext(os.path.basename(fp))[0]
    for cur in clip.get("rootMotionCurves") or []:
        a = cur["attribute"]
        ks = cur.get("keys") or []
        attr_present[a] += 1
        total_keys += len(ks)
        vs = [k["v"] for k in ks]
        if any(abs(v) > 1e-6 for v in vs):
            attr_nonzero[a] += 1
            nonzero_clips.add(name)
        if a.endswith("Q.w") and any(abs(abs(v) - 1.0) < 1e-3 for v in vs):
            qw_valid[a] += 1

    if mc.get("loopTime"):
        loop_true.append(name)
    if mc:
        ang_speed.append((abs(mc.get("averageAngularSpeed", 0.0)), name))
        s = mc.get("averageSpeed") or {}
        mag = (s.get("x", 0) ** 2 + s.get("y", 0) ** 2 + s.get("z", 0) ** 2) ** 0.5
        avg_speed.append((mag, name))

print("\n顶层键:", dict(top_keys))
print("\nclip 键(除 rootMotionCurves):", dict(clip_keys))
print("\nmuscleClip 键:", sorted(muscle_keys.keys()))
print("\n曲线 key 总量 =", total_keys)
print("\n属性: 出现次数 / 含非零值的 clip 数 / (w 分量出现过 ±1 的次数)")
for a in sorted(attr_present):
    print("  %-10s present=%3d nonzero=%3d qw_valid=%3d"
          % (a, attr_present[a], attr_nonzero[a], qw_valid[a]))
print("\n至少有一条曲线含非零值的 clip 数 =", len(nonzero_clips))
for n in sorted(nonzero_clips)[:20]:
    print("   ", n)

print("\nloopTime=True 的 clip 数 =", len(loop_true))
print("averageAngularSpeed 绝对值最大的 5 个:")
for v, n in sorted(ang_speed, reverse=True)[:5]:
    print("   %8.4f  %s" % (v, n))
print("averageSpeed 模长最大的 5 个:")
for v, n in sorted(avg_speed, reverse=True)[:5]:
    print("   %8.4f  %s" % (v, n))
