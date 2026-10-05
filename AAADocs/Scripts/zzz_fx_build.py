"""把一个 ZZZ 特效预制体完整做进 UE（经 MCP，在用户打开的编辑器里）。

    python zzz_fx_build.py <file.fx.json> [更多 .fx.json]

    for 预制体:
        deps / ue_assets       ← zzz_fx_fetch + zzz_fx_import_assets 的产物（需先跑）
        for 渲染中的粒子节点:
            材质方案 = zzz_fx_material.plan(Unity 材质, 顶点流, 网格 UV 层数)
            master / MI       ← zzz_fx_material_ue（同一方案只建一次）
            发射器方案        = zzz_fx_niagara.emitter_spec(...)
            任一步失败 → 记入 skipped（原因原文），不生成替代效果
        NS_<预制体名>        ← zzz_fx_niagara_ue.build_system
        报告                  → <fx 同目录>/<预制体名>.ue_report.json
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_fx_material as FM  # noqa: E402
import zzz_fx_niagara as FN  # noqa: E402
import zzz_unity_anim as UA  # noqa: E402
from zzz_fx_material_ue import Builder  # noqa: E402
from zzz_fx_niagara_ue import NiagaraBuilder  # noqa: E402
from ue_mcp import Mcp  # noqa: E402

SYSTEM_DIR = "/Game/Characters/Player/Pyrios/FX/Skill"


def walk(n, path=()):
    yield n, path
    for c in n["children"]:
        yield from walk(c, path + (c,))


def uv_count(deps, mesh_pid):
    js = [f for f in deps[mesh_pid]["files"] if f.endswith(".json")]
    mj = json.load(open(js[0], encoding="utf-8"))
    return sum(1 for k in range(8) if mj.get("m_UV%d" % k))


def mi_name(unity_name):
    return "MI_" + re.sub(r"[^A-Za-z0-9_]", "_", unity_name)


def build(fx_path, mcp):
    fx = json.load(open(fx_path, encoding="utf-8"))
    deps = json.load(open(str(fx_path).replace(".fx.json", ".deps.json"), encoding="utf-8"))
    assets = json.load(open(Path(fx_path).with_name("ue_assets.json"), encoding="utf-8"))
    root = fx["root"]
    clip = None
    anim = root.get("animation")
    if anim:
        if len(anim["clips"]) != 1:
            raise SystemExit("%s 的 Animation 有 %d 个片段，未实现" % (fx["name"], len(anim["clips"])))
        pid = str(anim["clips"][0]["m_PathID"])
        clip = UA.load(next(f for f in deps[pid]["files"] if f.endswith(".anim")))
    mats = Builder(mcp)
    specs, skipped, materials = [], [], {}
    for node, path in walk(root):
        if path and "mesh" in node and node["mesh"]["enabled"] and node["active"]:
            skipped.append({"node": "/".join(n["name"] for n in path),
                            "reason": "MeshRenderer 节点（非粒子网格，可能由 Animation 驱动）未实现"})
        if not path or "particle" not in node:
            continue
        rd = node["particle"]["renderer"]
        label = "/".join(n["name"] for n in path)
        if not node["active"] or not rd["m_Enabled"] or all(m["m_PathID"] == 0 for m in rd["m_Materials"]):
            continue  # 不渲染的容器节点
        try:
            mpid = next(str(m["m_PathID"]) for m in rd["m_Materials"] if m["m_PathID"] != 0)
            mesh_pid = str(rd["m_Mesh"]["m_PathID"])
            renderer = {"kind": "particle", "streams": rd["m_VertexStreams"], "custom_streams": rd["m_UseCustomVertexStreams"],
                        "mesh": rd["m_RenderMode"] == 4, "uv_count": uv_count(deps, mesh_pid) if mesh_pid != "0" else 1}
            plan = FM.plan(deps[mpid]["files"][0], renderer, assets)
            master = mats.build_master(plan)
            mi = mats.build_instance(plan, master, mi_name(deps[mpid]["name"]))
            materials[mpid] = {"mi": mi, "master": master, "warnings": plan["warnings"],
                               "skipped_passes": plan["skipped_passes"]}
            spec = FN.emitter_spec(node, list(path), clip, assets, {mpid: mi}, plan)
            specs.append(spec)
        except (FM.PlanError, FN.SpecError, FM.T.TranslateError) as e:
            skipped.append({"node": label, "reason": "%s: %s" % (type(e).__name__, e)})
    sys_path = "%s/NS_%s" % (SYSTEM_DIR, re.sub(r"[^A-Za-z0-9_]", "_", fx["name"]))
    state = None
    if specs:
        state = NiagaraBuilder(mcp).build_system(sys_path, specs)
    report = {"system": sys_path if specs else None, "emitters": [s["path"] for s in specs], "skipped": skipped,
              "materials": materials, "compile": state and state["aggregateStatus"]}
    out = Path(fx_path).with_name(fx["name"] + ".ue_report.json")
    out.write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
    return report


def main():
    mcp = Mcp()
    for p in sys.argv[1:]:
        r = build(p, mcp)
        print(json.dumps({k: r[k] for k in ("system", "emitters", "skipped", "compile")}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
