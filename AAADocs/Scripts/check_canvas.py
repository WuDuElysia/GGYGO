# -*- coding: utf-8 -*-
"""只读校验模块化 Canvas 与指定 Markdown 的 JSON、几何及 wikilink。

无参数时递归检查整个笔记目录的 Canvas；显式路径只检查冻结的目标文件。
不保存笔记，不以静态校验代替 Obsidian 视觉或 UE 运行验收。
"""
import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(r"F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划")
WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
HEADING = re.compile(r"^ {0,3}#{1,6}\s+(.+?)\s*#*\s*$", re.MULTILINE)


def build_index(root):
    files = sorted(p for p in root.rglob("*") if p.is_file()
                   and p.suffix.casefold() in (".md", ".canvas"))
    relative = {p.relative_to(root).as_posix().casefold(): p for p in files}
    names = {}
    for p in files:
        for key in (p.name.casefold(), p.stem.casefold()):
            names.setdefault(key, set()).add(p)
    return relative, names


def resolve_link(link, source, root, index):
    # 表格中的 escaped pipe 仍是显示文本分隔符，不属于文件名。
    target = link.split("|", 1)[0].rstrip("\\").strip()
    file_name, separator, anchor = target.partition("#")
    file_name = file_name.replace("\\", "/")
    if not file_name:
        target_path = source
    else:
        relative, names = index
        candidates = [file_name]
        if not Path(file_name).suffix:
            candidates.extend((file_name + ".md", file_name + ".canvas"))
        target_path = None
        parent = source.parent.relative_to(root).as_posix()
        for candidate in candidates:
            for key in (candidate.casefold(),
                        (parent + "/" + candidate).casefold()):
                if key in relative:
                    target_path = relative[key]
                    break
            if target_path:
                break
        if target_path is None:
            matches = names.get(file_name.casefold(), set())
            if len(matches) != 1:
                return None, "目标不存在或同名歧义: " + target
            target_path = next(iter(matches))
    if separator and anchor:
        if target_path.suffix.casefold() != ".md":
            return None, "非 Markdown 目标不支持标题/块锚点: " + target
        text = target_path.read_text(encoding="utf-8-sig")
        if anchor.startswith("^"):
            exists = re.search(r"(?m)\^" + re.escape(anchor[1:]) + r"\s*$", text)
        else:
            exists = anchor in {m.group(1).strip() for m in HEADING.finditer(text)}
        if not exists:
            return None, "锚点不存在: " + target
    return target_path, None


def validate_file(path, root, index):
    raw = path.read_text(encoding="utf-8-sig")
    errors, warnings = [], []
    nodes, edges = [], []
    if path.suffix.casefold() == ".canvas":
        data = json.loads(raw)
        if not isinstance(data, dict) or not isinstance(data.get("nodes"), list) \
                or not isinstance(data.get("edges"), list):
            raise ValueError("Canvas 必须包含 nodes/edges 数组")
        nodes, edges = data["nodes"], data["edges"]
        ids = [item.get("id") for item in nodes + edges]
        if any(not isinstance(value, str) or not value for value in ids):
            errors.append("节点/边 ID 缺失或非法")
        duplicates = [value for value, count in Counter(ids).items() if count > 1]
        if duplicates:
            errors.append("节点/边 ID 重复: " + repr(duplicates))
        node_ids = {item.get("id") for item in nodes}
        for edge in edges:
            for side in ("fromNode", "toNode"):
                if edge.get(side) not in node_ids:
                    errors.append("边 %s 的 %s 引用不存在" % (edge.get("id"), side))
            if not isinstance(edge.get("label"), str) or not edge["label"].strip():
                errors.append("边 %s 缺少 label" % edge.get("id"))
        geometry = []
        for node in nodes:
            values = [node.get(key) for key in ("x", "y", "width", "height")]
            if any(not isinstance(value, (int, float)) or isinstance(value, bool)
                   or not math.isfinite(value) for value in values) \
                    or values[2] <= 0 or values[3] <= 0:
                errors.append("节点 %s 几何非法" % node.get("id"))
            else:
                geometry.append(node)
        for i, a in enumerate(geometry):
            for b in geometry[i + 1:]:
                if a["x"] < b["x"] + b["width"] and b["x"] < a["x"] + a["width"] \
                        and a["y"] < b["y"] + b["height"] and b["y"] < a["y"] + a["height"]:
                    warnings.append("节点重叠: %s <-> %s" % (a["id"], b["id"]))
        text = "\n".join(node.get("text", "") for node in nodes
                         if isinstance(node.get("text", ""), str))
    elif path.suffix.casefold() == ".md":
        text = raw
    else:
        raise ValueError("仅接受 .canvas 或 .md")
    links = {match.group(1).strip() for match in WIKILINK.finditer(text)}
    for link in sorted(links):
        _, error = resolve_link(link, path, root, index)
        if error:
            errors.append(error)
    return errors, warnings, len(nodes), len(edges), len(links)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("paths", nargs="*", type=Path)
    args = parser.parse_args(argv)
    root = args.root.resolve()
    if not root.is_dir():
        parser.error("笔记根目录不存在: " + str(root))
    index = build_index(root)
    files = [p.resolve() for p in args.paths] if args.paths \
        else sorted(root.rglob("*.canvas"))
    if not files:
        parser.error("没有目标文件，不能报告校验成功")
    failures = 0
    for path in files:
        try:
            path.relative_to(root)
            errors, warnings, nodes, edges, links = validate_file(path, root, index)
        except (OSError, ValueError, TypeError, KeyError) as error:
            errors, warnings, nodes, edges, links = [str(error)], [], 0, 0, 0
        name = str(path)
        for error in errors:
            print("[FAIL] %s: %s" % (name, error))
        for warning in warnings:
            print("[WARN] %s: %s" % (name, warning))
        failures += bool(errors)
        print("[%s] %s nodes=%d edges=%d links=%d" %
              ("FAIL" if errors else " OK ", name, nodes, edges, links))
    print("静态结论: files=%d failed=%d；不代表视觉/运行验收" % (len(files), failures))
    return 1 if failures else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    sys.exit(main())
