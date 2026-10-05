"""把一个资源块的 Raw 导出（PathID 命名）整理成预制体层级索引。

输入：<RawBlockDir>/<Type>/<PathID>.dat（AnimeStudio ANIMESTUDIO_EXPORT_ALL=1 ANIMESTUDIO_RAW_PATHID=1 --export_type Raw）
输出：<RawBlockDir>/fx_index.json
    {"roots": [{"name", "go", "transform", "children": [...], "components": [{"type", "pathID"}]}]}

流程：
    types[pathID] = 所在类型目录
    for go in GameObject: 读 m_Name、m_Component
    for tr in Transform:  读 m_GameObject、m_Father、m_Children、局部 TRS
    roots = m_Father.m_PathID == 0 的 Transform，递归展开子节点
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_schema as S  # noqa: E402


def load_dir(root, type_name):
    d = root / type_name
    return {int(p.stem): p for p in d.glob("*.dat")} if d.is_dir() else {}


def build_index(root):
    types = {}
    for d in root.iterdir():
        if d.is_dir():
            for p in d.glob("*.dat"):
                types[int(p.stem)] = d.name
    gos = {pid: S.read("GameObject", p.read_bytes())[0] for pid, p in load_dir(root, "GameObject").items()}
    trs = {pid: S.read("Transform", p.read_bytes())[0] for pid, p in load_dir(root, "Transform").items()}

    def node(tr_id):
        tr = trs[tr_id]
        go_id = tr["m_GameObject"]["m_PathID"]
        go = gos.get(go_id, {})
        comps = []
        for c in go.get("m_Component", []):
            pid = c["component"]["m_PathID"]
            comps.append({"type": types.get(pid, "external"), "pathID": pid})
        kids = [node(c["m_PathID"]) for c in tr["m_Children"] if c["m_PathID"] in trs]
        return {
            "name": go.get("m_Name", "?"), "go": go_id, "transform": tr_id, "active": go.get("m_IsActive"),
            "pos": tr["m_LocalPosition"], "rot": tr["m_LocalRotation"], "scale": tr["m_LocalScale"],
            "components": comps, "children": kids,
        }

    roots = [node(pid) for pid, tr in trs.items() if tr["m_Father"]["m_PathID"] == 0]
    roots.sort(key=lambda n: n["name"])
    return {"roots": roots}


def main():
    root = Path(sys.argv[1])
    index = build_index(root)
    (root / "fx_index.json").write_text(json.dumps(index, ensure_ascii=False, indent=1), encoding="utf-8")
    for r in index["roots"]:
        print(r["name"])


if __name__ == "__main__":
    main()
