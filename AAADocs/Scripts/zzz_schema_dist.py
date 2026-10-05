"""统计目录内各对象某层字段的取值分布，用来核对补丁字段位置是否合理（例如 bool 只出现 0/1、枚举落在合法范围）。

用法：python zzz_schema_dist.py <Class> <dir> [字段路径前缀] [limit]
对读取失败的对象，统计到出错为止，并汇报剩余字节数分布。
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_schema as S  # noqa: E402


def main():
    cls, d = sys.argv[1], Path(sys.argv[2])
    prefix = sys.argv[3] if len(sys.argv) > 3 else cls
    limit = int(sys.argv[4]) if len(sys.argv) > 4 else 500
    dist = collections.defaultdict(collections.Counter)
    rest = collections.Counter()
    order = []
    for f in sorted(d.glob("*.dat"))[:limit]:
        data = f.read_bytes()
        rows, err, pos = S.trace(cls, data, 99)
        rest[len(data) - pos] += 1
        for s, e, p, t, v in rows:
            if not p.startswith(prefix) or isinstance(v, (dict, list)):
                continue
            key = p.split("[")[0] if "[" in p else p
            if key not in dist:
                order.append(key)
            dist[key][round(v, 4) if isinstance(v, float) else v] += 1
    for k in order:
        print("%-70s %s" % (k, dist[k].most_common(6)))
    print("剩余字节分布", rest.most_common(6))


if __name__ == "__main__":
    main()
