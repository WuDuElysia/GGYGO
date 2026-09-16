# -*- coding: utf-8 -*-
"""校验 GGYGO 架构 Canvas：JSON 合法性、ID 唯一性、边引用、wikilink 目标存在性。"""
import glob
import json
import os
import re
import sys

ROOT = r"F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划"

files = sorted(glob.glob(os.path.join(ROOT, "*.canvas")))
existing = {os.path.basename(p) for p in glob.glob(os.path.join(ROOT, "*"))}
# wikilink 也可能指向无扩展名的 md 笔记
existing_stems = {os.path.splitext(os.path.basename(p))[0]
                  for p in glob.glob(os.path.join(ROOT, "*"))}

ok = True
for fp in files:
    name = os.path.basename(fp)
    with open(fp, "r", encoding="utf-8") as f:
        raw = f.read()
    try:
        data = json.loads(raw)
    except Exception as exc:
        print("[FAIL] %s JSON 解析失败: %s" % (name, exc))
        ok = False
        continue

    nodes = data.get("nodes") or []
    edges = data.get("edges") or []
    node_ids = [n["id"] for n in nodes]
    edge_ids = [e["id"] for e in edges]

    dup_n = {i for i in node_ids if node_ids.count(i) > 1}
    dup_e = {i for i in edge_ids if edge_ids.count(i) > 1}
    if dup_n:
        print("[FAIL] %s 节点 ID 重复: %s" % (name, dup_n)); ok = False
    if dup_e:
        print("[FAIL] %s 边 ID 重复: %s" % (name, dup_e)); ok = False

    idset = set(node_ids)
    for e in edges:
        for side in ("fromNode", "toNode"):
            if e[side] not in idset:
                print("[FAIL] %s 边 %s 的 %s=%s 指向不存在的节点"
                      % (name, e["id"], side, e[side])); ok = False
        if not (e.get("label") or "").strip():
            print("[FAIL] %s 边 %s 缺少 label" % (name, e["id"])); ok = False

    # 节点重叠检测
    for i, a in enumerate(nodes):
        for b in nodes[i + 1:]:
            ax1, ay1 = a["x"], a["y"]
            ax2, ay2 = ax1 + a["width"], ay1 + a["height"]
            bx1, by1 = b["x"], b["y"]
            bx2, by2 = bx1 + b["width"], by1 + b["height"]
            if ax1 < bx2 and bx1 < ax2 and ay1 < by2 and by1 < ay2:
                print("[WARN] %s 节点重叠: %s <-> %s" % (name, a["id"], b["id"]))

    # wikilink 目标
    links = set()
    for n in nodes:
        for m in re.finditer(r"\[\[([^\]\|]+)(?:\|[^\]]*)?\]\]", n.get("text", "")):
            links.add(m.group(1).strip())
    for link in sorted(links):
        if link in existing or link in existing_stems:
            continue
        print("[FAIL] %s wikilink 目标不存在: %s" % (name, link)); ok = False

    print("[ OK ] %-40s nodes=%2d edges=%2d links=%d"
          % (name, len(nodes), len(edges), len(links)))

print("\n结论:", "全部通过" if ok else "存在问题")
sys.exit(0 if ok else 1)
