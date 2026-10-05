"""打印 fx_index.json 中各预制体根的组成统计；可按名字正则过滤，或展开单个根的层级。

用法：
    python zzz_fx_summary.py <fx_index.json> [名字正则]          每个根一行：节点数与组件计数
    python zzz_fx_summary.py <fx_index.json> <根名> --tree      展开层级
"""
import collections
import json
import re
import sys


def walk(n, depth=0):
    yield n, depth
    for c in n["children"]:
        yield from walk(c, depth + 1)


def main():
    index = json.load(open(sys.argv[1], encoding="utf-8"))
    pat = sys.argv[2] if len(sys.argv) > 2 else ""
    for r in index["roots"]:
        if "--tree" in sys.argv:
            if r["name"] != pat:
                continue
            for n, d in walk(r):
                comps = ",".join(c["type"] for c in n["components"] if c["type"] not in ("Transform",))
                print("%s%s%s  [%s]" % ("  " * d, n["name"], "" if n["active"] else " (inactive)", comps))
            continue
        if not re.search(pat, r["name"]):
            continue
        cnt = collections.Counter()
        nodes = 0
        for n, d in walk(r):
            nodes += 1
            for c in n["components"]:
                cnt[c["type"]] += 1
        cnt.pop("Transform", None)
        print("%-60s nodes=%-4d %s" % (r["name"], nodes, dict(cnt)))


if __name__ == "__main__":
    main()
