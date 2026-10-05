"""把一个 ZZZ 特效预制体根（fx_index.json 里的根）展开成自包含的 JSON 描述，供 UE 侧生成 Niagara 系统。

用法：python zzz_fx_extract.py <RawBlockDir> <根名正则> [输出目录]
输出：<输出目录>/<根名>.fx.json（默认输出到 <RawBlockDir>/fx_json/）

每个节点：
    {name, active, pos, rot, scale,              Unity 局部 TRS（左手 Y 上，米）
     particle: {system, renderer},               ParticleSystem/ParticleSystemRenderer 解析结果，已剔除 enabled=false 的模块
     mesh: {mesh, materials},                    MeshFilter + MeshRenderer
     animation: {clips},                         Legacy Animation 引用的 AnimationClip
     light, scripts: [MonoScript 类名], children}
所有 PPtr 保留 {m_FileID, m_PathID}；m_FileID != 0 表示在其它资源块，按 PathID 查全局 AssetMap 解析。
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_schema as S  # noqa: E402

MODULE_KEYS_ALWAYS = ("InitialModule",)


def read_obj(root, type_name, pid):
    p = root / type_name / ("%d.dat" % pid)
    obj, layout = S.read(type_name, p.read_bytes())
    return obj


def strip_disabled(ps):
    """模块 enabled=false 时 Unity 不执行它，剔除后 JSON 只保留实际生效的数据。"""
    out = {}
    for k, v in ps.items():
        if isinstance(v, dict) and "enabled" in v and k not in MODULE_KEYS_ALWAYS and not v["enabled"]:
            continue
        if k.startswith("zzz_"):
            continue
        out[k] = v
    return out


def script_names(root):
    names = {}
    d = root / "MonoScript"
    for p in d.glob("*.dat") if d.is_dir() else []:
        o, _ = S.read("MonoScript", p.read_bytes())
        names[int(p.stem)] = ("%s.%s" % (o["m_Namespace"], o["m_ClassName"])).strip(".")
    return names


def mono_header(root, pid):
    """MonoBehaviour 只解析基类头（GameObject/Enabled/Script/Name），脚本字段没有类型树，原样保留十六进制。"""
    data = (root / "MonoBehaviour" / ("%d.dat" % pid)).read_bytes()
    r = S.Reader(data)
    tree = S.tree_for("MonoBehaviour")
    head = {}
    for c in tree.children:
        head[c.name] = r.read(c, c.name)
    head["payload_hex"] = data[r.pos:].hex()
    return head


def build_node(root, n, scripts):
    out = {k: n[k] for k in ("name", "active", "pos", "rot", "scale")}
    out["transform"] = n["transform"]
    comps = {}
    for c in n["components"]:
        comps.setdefault(c["type"], []).append(c["pathID"])
    if "ParticleSystem" in comps:
        ps = read_obj(root, "ParticleSystem", comps["ParticleSystem"][0])
        rd = read_obj(root, "ParticleSystemRenderer", comps["ParticleSystemRenderer"][0])
        out["particle"] = {
            "system": strip_disabled(ps),
            "renderer": {k: v for k, v in rd.items() if not k.startswith("zzz_")},
        }
    if "MeshFilter" in comps:
        mf = read_obj(root, "MeshFilter", comps["MeshFilter"][0])
        mr = read_obj(root, "MeshRenderer", comps["MeshRenderer"][0]) if "MeshRenderer" in comps else None
        out["mesh"] = {"mesh": mf["m_Mesh"], "materials": mr["m_Materials"] if mr else [],
                       "enabled": bool(mr["m_Enabled"]) if mr else False}
    if "Animation" in comps:
        an = read_obj(root, "Animation", comps["Animation"][0])
        out["animation"] = {"clips": an["m_Animations"], "default": an["m_Animation"],
                            "playAutomatically": an["m_PlayAutomatically"], "wrapMode": an["m_WrapMode"]}
    if "Light" in comps:
        out["light"] = {k: v for k, v in read_obj(root, "Light", comps["Light"][0]).items() if not k.startswith("zzz_")}
    monos = []
    for pid in comps.get("MonoBehaviour", []):
        h = mono_header(root, pid)
        sid = h["m_Script"]["m_PathID"]
        monos.append({"script": scripts.get(sid, "external:%d" % sid), "enabled": h["m_Enabled"],
                      "payload_hex": h["payload_hex"]})
    out["scripts"] = monos
    out["children"] = [build_node(root, c, scripts) for c in n["children"]]
    return out


def main():
    root = Path(sys.argv[1])
    pat = re.compile(sys.argv[2])
    out_dir = Path(sys.argv[3]) if len(sys.argv) > 3 else root / "fx_json"
    out_dir.mkdir(parents=True, exist_ok=True)
    index = json.load(open(root / "fx_index.json", encoding="utf-8"))
    scripts = script_names(root)
    for r in index["roots"]:
        if not pat.search(r["name"]):
            continue
        fx = {"name": r["name"], "block": root.name, "root": build_node(root, r, scripts)}
        path = out_dir / (r["name"] + ".fx.json")
        path.write_text(json.dumps(fx, ensure_ascii=False, indent=1), encoding="utf-8")
        print(path)


if __name__ == "__main__":
    main()
