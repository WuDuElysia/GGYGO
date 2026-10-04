"""纯 Python PNG 读取与统计，用数值代替看图。

用法：
  python png_stats.py <png> hist [通道]            每通道 0~255 分 10 档的直方图（只统计非零像素可加 nz）
  python png_stats.py <png> row <y0> <y1>          指定行范围的每行均值（看纵向渐变）
  python png_stats.py <png> col <x0> <x1>          指定列范围的每列均值（看横向渐变）
  python png_stats.py <png> box x0 y0 x1 y1 ...    矩形区域的通道均值/最小/最大
"""
import struct
import sys
import zlib


def load(path):
    b = open(path, "rb").read()
    w, h, bd, ct = struct.unpack(">IIBB", b[16:26])
    if bd != 8:
        raise ValueError("only 8-bit PNG supported")
    i, dat = 8, b""
    while i < len(b):
        n = struct.unpack(">I", b[i:i + 4])[0]
        if b[i + 4:i + 8] == b"IDAT":
            dat += b[i + 8:i + 8 + n]
        i += 12 + n
    raw = zlib.decompress(dat)
    ch = {0: 1, 2: 3, 4: 2, 6: 4}[ct]
    st, rows, prev, p = w * ch, [], bytearray(w * ch), 0
    for _ in range(h):
        f, line = raw[p], bytearray(raw[p + 1:p + 1 + st])
        p += 1 + st
        for x in range(st):
            a = line[x - ch] if x >= ch else 0
            up = prev[x]
            c = prev[x - ch] if x >= ch else 0
            if f == 1:
                line[x] = (line[x] + a) & 255
            elif f == 2:
                line[x] = (line[x] + up) & 255
            elif f == 3:
                line[x] = (line[x] + ((a + up) >> 1)) & 255
            elif f == 4:
                pa, pb, pc = abs(up - c), abs(a - c), abs(a + up - 2 * c)
                line[x] = (line[x] + (a if pa <= pb and pa <= pc else (up if pb <= pc else c))) & 255
        rows.append(bytes(line))
        prev = line
    return w, h, ch, rows


def main():
    path, mode = sys.argv[1], sys.argv[2]
    w, h, ch, rows = load(path)
    print("size", w, h, "channels", ch)
    if mode == "hist":
        nz = "nz" in sys.argv[3:]
        for c in range(ch):
            bins = [0] * 10
            total = 0
            for r in rows:
                for x in range(c, len(r), ch):
                    v = r[x]
                    if nz and v == 0:
                        continue
                    bins[min(9, v * 10 // 256)] += 1
                    total += 1
            print("ch%d" % c, " ".join("%d" % (100 * n // max(1, total)) for n in bins), "(% per 0.1 bin)")
    elif mode == "box":
        # box x0 y0 x1 y1 [x0 y0 x1 y1 ...]：每个矩形的通道均值、最小、最大（0~1）
        nums = [int(v) for v in sys.argv[3:]]
        for k in range(0, len(nums), 4):
            x0, y0, x1, y1 = nums[k:k + 4]
            px = [rows[y][x * ch:x * ch + ch] for y in range(y0, y1) for x in range(x0, x1)]
            stats = [(sum(p[c] for p in px) / len(px) / 255, min(p[c] for p in px) / 255,
                      max(p[c] for p in px) / 255) for c in range(min(ch, 3))]
            print("box", (x0, y0, x1, y1), "mean", tuple(round(s[0], 3) for s in stats),
                  "min", tuple(round(s[1], 3) for s in stats), "max", tuple(round(s[2], 3) for s in stats))
    elif mode in ("row", "col"):
        a, z = int(sys.argv[3]), int(sys.argv[4])
        step = max(1, (z - a) // 32)
        for k in range(a, z, step):
            if mode == "row":
                vals = [rows[k][x * ch:x * ch + ch] for x in range(w)]
            else:
                vals = [rows[y][k * ch:k * ch + ch] for y in range(h)]
            print(k, tuple(round(sum(v[c] for v in vals) / len(vals) / 255, 3) for c in range(ch)))


if __name__ == "__main__":
    main()
