"""打印按 zzz_schema 读取原始对象时各字段的偏移与值，用于逐段核对布局。

用法：
    python zzz_schema_trace.py trace <Class> <file.dat> [depth] [tail]   打印字段，tail>0 只看最后 tail 行
    python zzz_schema_trace.py stat  <Class> <dir> [limit]               统计目录内完整读取成功率与失败位置
"""
import collections
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_schema as S  # noqa: E402


def brief(v):
    if isinstance(v, dict):
        return "{..}"
    if isinstance(v, list):
        return "[%d]" % len(v)
    if isinstance(v, float):
        return "%.5g" % v
    return repr(v)[:60]


def cmd_trace(cls, path, depth=2, tail=0):
    rows, err, pos = S.trace(cls, Path(path).read_bytes(), depth)
    if tail:
        rows = rows[-tail:]
    for s, e, p, t, v in rows:
        print("%6d %6d  %-60s %-18s %s" % (s, e, p, t, brief(v)))
    print("ERR:" if err else "OK", err or "", "pos", pos)


def cmd_stat(cls, d, limit=100000):
    files = sorted(Path(d).glob("*.dat"))[:limit]
    ok, errs = 0, collections.Counter()
    first = {}
    for f in files:
        try:
            S.read(cls, f.read_bytes())
            ok += 1
        except S.LayoutError as e:
            rows, err, pos = S.trace(cls, f.read_bytes(), 99)
            last = rows[-1][2] if rows else "?"
            key = last.split("[")[0][:80]
            errs[key] += 1
            first.setdefault(key, f.name)
    print("%s OK %d / %d" % (cls, ok, len(files)))
    for k, n in errs.most_common(15):
        print("  %5d  最后成功字段 %s  例 %s" % (n, k, first[k]))


if __name__ == "__main__":
    a = sys.argv
    if a[1] == "trace":
        cmd_trace(a[2], a[3], int(a[4]) if len(a) > 4 else 2, int(a[5]) if len(a) > 5 else 0)
    else:
        cmd_stat(a[2], a[3], int(a[4]) if len(a) > 4 else 100000)
