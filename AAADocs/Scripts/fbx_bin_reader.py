"""
最小纯 Python 二进制 FBX 解析器（FBX 版本 < 7500，32 位偏移）。

目的：无需 Autodesk FBX SDK / Blender，直接从二进制 FBX 中枚举：
  - 头部版本 / 创建者
  - Definitions 各 ObjectType 计数
  - 所有 AnimStack（动画 take）名字
  - 所有 Model 节点名字（骨骼 / 参考节点）
  - 用于后续按 take 抽取指定骨骼旋转轨道的底层节点树

对超大数组属性只读取 12 字节头并 seek 跳过其数据，避免把 333MB 读进内存。

用法:
  python fbx_bin_reader.py <fbx路径> overview
"""

import sys
import struct
import zlib


# 标量属性类型 -> (struct格式, 字节数)
SCALAR = {
    b'Y'[0]: ('<h', 2),
    b'C'[0]: ('<?', 1),
    b'I'[0]: ('<i', 4),
    b'F'[0]: ('<f', 4),
    b'D'[0]: ('<d', 8),
    b'L'[0]: ('<q', 8),
}

# 数组属性元素类型 -> 单元素字节数
ARRAY_ELEM = {
    b'f'[0]: 4,
    b'd'[0]: 8,
    b'l'[0]: 8,
    b'i'[0]: 4,
    b'b'[0]: 1,
}

ARRAY_STRUCT = {
    b'f'[0]: '<f',
    b'd'[0]: '<d',
    b'l'[0]: '<q',
    b'i'[0]: '<i',
    b'b'[0]: '<b',
}


class Node:
    __slots__ = ('name', 'props', 'children')

    def __init__(self, name):
        self.name = name
        self.props = []       # 标量/字符串已解码；数组存 ('array', typecode, length, data_offset, encoding, comp_len)
        self.children = []

    def __repr__(self):
        return f'<Node {self.name} props={len(self.props)} children={len(self.children)}>'


class FbxReader:
    def __init__(self, path, decode_arrays=False):
        self.path = path
        self.f = open(path, 'rb')
        self.decode_arrays = decode_arrays
        self.version = None

    def close(self):
        self.f.close()

    def read_header(self):
        self.f.seek(0)
        magic = self.f.read(23)
        assert magic.startswith(b'Kaydara FBX Binary'), 'not a binary FBX'
        self.version = struct.unpack('<I', self.f.read(4))[0]  # 版本紧跟 23 字节魔数
        return self.version

    def _read_prop(self):
        f = self.f
        type_code = f.read(1)[0]
        if type_code in SCALAR:
            fmt, size = SCALAR[type_code]
            val = struct.unpack(fmt, f.read(size))[0]
            return val
        if type_code in ARRAY_ELEM:
            arr_len, encoding, comp_len = struct.unpack('<III', f.read(12))
            data_off = f.tell()
            if encoding == 1:
                nbytes = comp_len
            else:
                nbytes = arr_len * ARRAY_ELEM[type_code]
            if self.decode_arrays:
                raw = f.read(nbytes)
                if encoding == 1:
                    raw = zlib.decompress(raw)
                vals = list(struct.unpack('<' + ARRAY_STRUCT[type_code][1] * arr_len, raw))
                return ('array', chr(type_code), arr_len, vals)
            else:
                f.seek(data_off + nbytes)
                return ('array', chr(type_code), arr_len, data_off, encoding, comp_len)
        if type_code == b'S'[0] or type_code == b'R'[0]:
            length = struct.unpack('<I', f.read(4))[0]
            data = f.read(length)
            if type_code == b'S'[0]:
                return data  # 字节串，含 \x00\x01 分隔的 Name::Class
            return ('raw', length)
        raise ValueError(f'unknown property type 0x{type_code:02x} at {f.tell()}')

    def _read_node(self, decode_arrays_for=None):
        """读取一个节点记录；返回 Node 或 None（遇到 null 终止块）。"""
        f = self.f
        end_offset, num_props, prop_list_len = struct.unpack('<III', f.read(12))
        name_len = f.read(1)[0]
        if end_offset == 0 and num_props == 0 and prop_list_len == 0 and name_len == 0:
            return None  # null 终止块
        name = f.read(name_len).decode('utf-8', 'replace')

        node = Node(name)
        # 是否为该节点解码数组（用于抽曲线）
        prev = self.decode_arrays
        if decode_arrays_for is not None and name in decode_arrays_for:
            self.decode_arrays = True
        for _ in range(num_props):
            node.props.append(self._read_prop())
        self.decode_arrays = prev

        # 嵌套子节点：直到 end_offset
        while f.tell() < end_offset:
            child = self._read_node(decode_arrays_for=decode_arrays_for)
            if child is None:
                break
            node.children.append(child)
        # 对齐到 end_offset
        f.seek(end_offset)
        return node

    def parse(self, decode_arrays_for=None):
        self.read_header()
        f = self.f
        roots = []
        file_end = f.seek(0, 2)
        f.seek(27)
        while f.tell() < file_end:
            pos = f.tell()
            node = self._read_node(decode_arrays_for=decode_arrays_for)
            if node is None:
                break
            roots.append(node)
            if f.tell() <= pos:
                break
        return roots


def decode_placeholder(f, ph):
    """按需解码惰性数组占位符：('array', typechar, arr_len, data_off, encoding, comp_len)。"""
    _, typechar, arr_len, data_off, encoding, comp_len = ph
    tc = typechar.encode()[0]
    f.seek(data_off)
    if encoding == 1:
        raw = zlib.decompress(f.read(comp_len))
    else:
        raw = f.read(arr_len * ARRAY_ELEM[tc])
    return list(struct.unpack('<' + ARRAY_STRUCT[tc][1] * arr_len, raw))


def prop_str(p):
    if isinstance(p, bytes):
        return p.decode('utf-8', 'replace')
    return str(p)


def first_string_prop(node):
    for p in node.props:
        if isinstance(p, bytes):
            return p.decode('utf-8', 'replace')
    return ''


def overview(path):
    r = FbxReader(path)
    roots = r.parse()
    print(f'FBX version: {r.version}')
    top = {n.name: n for n in roots}

    # 头部信息
    hdr = top.get('FBXHeaderExtension')
    if hdr:
        for c in hdr.children:
            if c.name in ('Creator', 'FBXVersion'):
                print(f'{c.name}: {first_string_prop(c) or (c.props[0] if c.props else "")}')

    # Definitions 计数
    defs = top.get('Definitions')
    if defs:
        print('\n=== Definitions (ObjectType 计数) ===')
        for c in defs.children:
            if c.name == 'ObjectType':
                otype = first_string_prop(c)
                count = ''
                for cc in c.children:
                    if cc.name == 'Count' and cc.props:
                        count = cc.props[0]
                print(f'  {otype}: {count}')

    # Objects 分类计数 + AnimStack / Model 名字
    objs = top.get('Objects')
    if objs:
        from collections import Counter, defaultdict
        type_count = Counter()
        anim_stacks = []
        models = defaultdict(list)
        for c in objs.children:
            type_count[c.name] += 1
            if c.name in ('AnimStack', 'AnimationStack'):
                anim_stacks.append(first_string_prop(c))
            elif c.name == 'Model':
                # props: id(L), "Name::Model"(S), subtype(S)
                nm = ''
                sub = ''
                strs = [p for p in c.props if isinstance(p, bytes)]
                if strs:
                    nm = strs[0].decode('utf-8', 'replace')
                if len(strs) > 1:
                    sub = strs[1].decode('utf-8', 'replace')
                models[sub].append(nm)

        print('\n=== Objects 分类计数 ===')
        for k, v in sorted(type_count.items(), key=lambda x: -x[1]):
            print(f'  {k}: {v}')

        print(f'\n=== AnimStack（动画 take）总数: {len(anim_stacks)} ===')
        for i, nm in enumerate(anim_stacks):
            clean = nm.split('\x00')[0]
            print(f'  [{i:03d}] {clean}')

        print('\n=== Model 节点分类 ===')
        for sub, names in models.items():
            print(f'  -- subtype={sub} count={len(names)}')
            for nm in names[:60]:
                print(f'     {nm.split(chr(0))[0]}')

    r.close()


if __name__ == '__main__':
    path = sys.argv[1]
    mode = sys.argv[2] if len(sys.argv) > 2 else 'overview'
    if mode == 'overview':
        overview(path)
