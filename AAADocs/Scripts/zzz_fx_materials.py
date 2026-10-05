"""列出 .fx.json 引用的材质：名字、Shader PathID、关键字、贴图与非默认参数，用于确定需要移植哪些 Shader。

用法：python zzz_fx_materials.py <file.fx.json> <TypedRoot> [--full]
TypedRoot 为 AnimeStudio 按 PathID 命名导出的目录（<TypedRoot>/<block>/Material/<名字>#<PathID>.json），
会在全部块目录里按 PathID 查找材质。
"""
import json
import sys
from pathlib import Path


def collect(n, acc):
    if "particle" in n:
        for m in n["particle"]["renderer"]["m_Materials"]:
            acc.setdefault(m["m_PathID"], []).append(n["name"])
    if "mesh" in n:
        for m in n["mesh"]["materials"]:
            acc.setdefault(m["m_PathID"], []).append(n["name"])
    for c in n["children"]:
        collect(c, acc)


def material_files(typed_root):
    out = {}
    for p in Path(typed_root).glob("*/Material/*.json"):
        out[int(p.stem.rsplit("#", 1)[1])] = p
    return out


def main():
    fx = json.load(open(sys.argv[1], encoding="utf-8"))
    files = material_files(sys.argv[2])
    acc = {}
    collect(fx["root"], acc)
    for pid, users in acc.items():
        if pid == 0:
            continue
        p = files.get(pid)
        if not p:
            print("MISSING material", pid, users)
            continue
        m = json.load(open(p, encoding="utf-8"))
        props = m["m_SavedProperties"]
        print("== %s  shader=%d  users=%s" % (p.stem, m["m_Shader"]["m_PathID"], users))
        print("   keywords:", m.get("m_ShaderKeywords") or m.get("m_ValidKeywords"))
        tex = {k: v["m_Texture"]["m_PathID"] for k, v in props["m_TexEnvs"].items() if not v["m_Texture"]["IsNull"]}
        print("   tex:", tex)
        if "--full" in sys.argv:
            print("   floats:", props["m_Floats"])
            print("   colors:", props["m_Colors"])


if __name__ == "__main__":
    main()
