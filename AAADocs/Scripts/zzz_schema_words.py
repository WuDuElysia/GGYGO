"""从某字段起点开始，按 4 字节并排打印多个样本的 int/float，用于推断未知字段的类型与语义。

用法：python zzz_schema_words.py <Class> <dir> <字段路径前缀> [样本数] [字数]
字段路径前缀是 zzz_schema.trace 输出的路径，例如 ParticleSystem.SizeModule.curve
"""
import struct
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import zzz_schema as S  # noqa: E402


def word(d, o):
    if o + 4 > len(d):
        return "--"
    i = struct.unpack_from("<i", d, o)[0]
    if -100000 < i < 100000:
        return str(i)
    return "%.4g" % struct.unpack_from("<f", d, o)[0]


def main():
    cls, d, prefix = sys.argv[1], Path(sys.argv[2]), sys.argv[3]
    n = int(sys.argv[4]) if len(sys.argv) > 4 else 8
    words = int(sys.argv[5]) if len(sys.argv) > 5 else 24
    cols = []
    for f in sorted(d.glob("*.dat"))[:n]:
        data = f.read_bytes()
        rows, err, pos = S.trace(cls, data, 99)
        starts = [r[0] for r in rows if r[2].startswith(prefix)]
        start = min(starts) if starts else pos
        cols.append([word(data, start + 4 * k) for k in range(words)])
    for k in range(words):
        print("+%-4d " % (4 * k) + " ".join("%10s" % c[k] for c in cols))


if __name__ == "__main__":
    main()
