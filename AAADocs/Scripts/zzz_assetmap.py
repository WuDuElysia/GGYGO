"""ZZZ 全局 AssetMap 查询：按 PathID（+类型）找到资产名与所在资源块。

AnimeStudio 生成 AssetMap（JSON）：
    AnimeStudio.CLI <Blocks目录> <输出目录> --game ZZZ --map_op AssetMap --map_type JSON --map_name zzz_assets
        --types Texture2D Shader Mesh Material AnimationClip
首次使用时把 JSON 压成 TSV 索引（同目录 zzz_assets.tsv），之后直接读 TSV。

ZZZ 的 PathID 是哈希值，跨资源块基本唯一；PPtr 的 m_FileID 指向外部文件时，按 PathID + 类型即可定位。
同一 PathID 出现多次时全部返回，由调用方决定（通常同名同类型的重复是同一资产在多个块里的副本）。

用法：python zzz_assetmap.py <PathID> [Type]
"""
import json
import sys
from pathlib import Path

MAP_JSON = Path(r"F:\AnimeStudio\Exports\ZZZ\AssetMapAll\zzz_assets.json")
MAP_TSV = MAP_JSON.with_suffix(".tsv")

_INDEX = None


def _build_tsv():
    data = json.load(open(MAP_JSON, encoding="utf-8"))
    entries = data["AssetEntries"] if isinstance(data, dict) else data
    with open(MAP_TSV, "w", encoding="utf-8") as f:
        for e in entries:
            src = Path(e["Source"]).name
            f.write("%d\t%s\t%s\t%s\n" % (e["PathID"], e["Type"], e["Name"].replace("\t", " "), src))


def index():
    global _INDEX
    if _INDEX is None:
        if not MAP_TSV.exists():
            _build_tsv()
        _INDEX = {}
        with open(MAP_TSV, encoding="utf-8") as f:
            for line in f:
                pid, typ, name, src = line.rstrip("\n").split("\t")
                _INDEX.setdefault(int(pid), []).append((typ, name, src))
    return _INDEX


def lookup(pid, type_name=None):
    hits = index().get(int(pid), [])
    return [h for h in hits if type_name is None or h[0] == type_name]


def main():
    for h in lookup(int(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else None):
        print("\t".join(h))


if __name__ == "__main__":
    main()
