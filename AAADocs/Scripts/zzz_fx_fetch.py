"""收集 .fx.json 依赖的全部外部资产（材质、网格、动画、贴图），按 AssetMap 找到资源块并用 AnimeStudio 导出。

用法：python zzz_fx_fetch.py <file.fx.json> [更多 .fx.json ...]
输出：
    <TYPED_ROOT>/<block>/<Type>/<名字>#<PathID>.<ext>     AnimeStudio 导出结果（同块只导出一次）
    <file>.deps.json                                       PathID -> {type, name, block, files}

流程：
    refs = fx.json 中材质 / 网格 / 动画的 PPtr
    export(blocks_of(refs), types=Material Mesh AnimationClip)
    refs2 = 材质里的贴图与 Shader
    export(blocks_of(贴图), types=Texture2D，PNG 与 JSON 各一份；JSON 带 m_ColorSpace)
找不到的 PathID 直接报错：缺依赖时生成的特效会与原版不一致，不能静默跳过。
"""
import json
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_assetmap as A  # noqa: E402
import zzz_mesh_fbx  # noqa: E402

CLI = r"F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe"
BLOCKS = Path(r"F:\ZenlessZoneZero Game\ZenlessZoneZero_Data\StreamingAssets\Blocks")
TYPED_ROOT = Path(r"F:\AnimeStudio\Exports\ZZZ\Pyrois_SkillFX\Typed")


def walk(n):
    yield n
    for c in n["children"]:
        yield from walk(c)


def fx_refs(fx):
    refs = []
    for n in walk(fx["root"]):
        if "particle" in n:
            rd, ps = n["particle"]["renderer"], n["particle"]["system"]
            refs += [("Material", m["m_PathID"]) for m in rd["m_Materials"]]
            refs += [("Mesh", rd[k]["m_PathID"]) for k in ("m_Mesh", "m_Mesh1", "m_Mesh2", "m_Mesh3")]
            if "ShapeModule" in ps:
                refs.append(("Mesh", ps["ShapeModule"]["m_Mesh"]["m_PathID"]))
        if "mesh" in n:
            refs.append(("Mesh", n["mesh"]["mesh"]["m_PathID"]))
            refs += [("Material", m["m_PathID"]) for m in n["mesh"]["materials"]]
        if "animation" in n:
            refs += [("AnimationClip", c["m_PathID"]) for c in n["animation"]["clips"]]
    return [(t, p) for t, p in refs if p != 0]


def resolve(refs):
    out = {}
    for t, pid in refs:
        hits = A.lookup(pid, t)
        if not hits:
            raise SystemExit("AssetMap 中找不到 %s PathID=%d" % (t, pid))
        out[pid] = {"type": t, "name": hits[0][1], "block": Path(hits[0][2]).stem}
    return out


def export(block, types, export_type=None):
    dst = TYPED_ROOT / block
    marker = dst / (".done_%s_%s" % ("_".join(types), export_type or "Convert"))
    if marker.exists():
        return
    env = dict(os.environ, ANIMESTUDIO_EXPORT_ALL="1", ANIMESTUDIO_RAW_PATHID="1")
    cmd = [CLI, str(BLOCKS / (block + ".blk")), str(dst), "--game", "ZZZ", "--silent", "--types", *types]
    if export_type:
        cmd += ["--export_type", export_type]
    subprocess.run(cmd, check=True, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    dst.mkdir(parents=True, exist_ok=True)
    marker.write_text("")


def files_for(block, type_name, pid):
    d = TYPED_ROOT / block / type_name
    return sorted(str(p) for p in d.glob("*#%d.*" % pid)) if d.is_dir() else []


def fetch(fx_path):
    fx = json.load(open(fx_path, encoding="utf-8"))
    deps = resolve(fx_refs(fx))
    for block in sorted({d["block"] for d in deps.values()}):
        export(block, ["Material", "Mesh", "AnimationClip"])
    tex_refs, shader_refs = [], []
    for pid, d in deps.items():
        d["files"] = files_for(d["block"], d["type"], pid)
        if not d["files"]:
            raise SystemExit("导出后找不到 %s %s#%d（块 %s）" % (d["type"], d["name"], pid, d["block"]))
        if d["type"] == "Material":
            m = json.load(open(d["files"][0], encoding="utf-8"))
            shader_refs.append(("Shader", m["m_Shader"]["m_PathID"]))
            for _, env in m["m_SavedProperties"]["m_TexEnvs"].items():
                if not env["m_Texture"]["IsNull"]:
                    tex_refs.append(("Texture2D", env["m_Texture"]["m_PathID"]))
    # 网格另导一份 JSON 并转 FBX：OBJ 不带顶点色和 UV1+，特效 shader 会读它们。
    mesh_blocks = sorted({d["block"] for d in deps.values() if d["type"] == "Mesh"})
    for block in mesh_blocks:
        export(block, ["Mesh"], "JSON")
    for pid, d in deps.items():
        if d["type"] != "Mesh":
            continue
        js = [f for f in files_for(d["block"], "Mesh", pid) if f.endswith(".json")]
        if len(js) != 1:
            raise SystemExit("网格 %s#%d 的 JSON 导出缺失" % (d["name"], pid))
        fbx = Path(js[0]).with_suffix(".fbx")
        if not fbx.exists():
            fbx.write_text(zzz_mesh_fbx.build(json.load(open(js[0], encoding="utf-8"))), encoding="utf-8")
        d["files"] = files_for(d["block"], "Mesh", pid)
    tex = resolve(tex_refs)
    for block in sorted({d["block"] for d in tex.values()}):
        export(block, ["Texture2D"])
        export(block, ["Texture2D"], "JSON")
    for pid, d in tex.items():
        d["files"] = files_for(d["block"], "Texture2D", pid)
        if not d["files"]:
            raise SystemExit("导出后找不到贴图 %s#%d（块 %s）" % (d["name"], pid, d["block"]))
    shaders = resolve(shader_refs)
    deps.update(tex)
    deps.update(shaders)
    out = Path(str(fx_path).replace(".fx.json", ".deps.json"))
    out.write_text(json.dumps({str(k): v for k, v in deps.items()}, ensure_ascii=False, indent=1), encoding="utf-8")
    print(out, "deps=%d" % len(deps))


def main():
    for p in sys.argv[1:]:
        fetch(p)


if __name__ == "__main__":
    main()
