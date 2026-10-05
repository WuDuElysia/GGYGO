"""ZZZ（miHoYo 改版 Unity 2019.4.40f1）内置类的序列化布局。

ZZZ 资源包剥离了类型树。以 UnityPy TPK 中 2019.4 的内置类型树为底，叠加逐字节核对出的
miHoYo 改动（ZZZ_PATCHES），得到能完整读取 ZZZ 原始对象的布局。

读取规则：
    read(class, bytes):
        tree = tpk_tree(class) 叠加 ZZZ_PATCHES
        obj  = read_node(tree)
        若未恰好用完全部字节 -> 抛 LayoutError（布局仍有未知改动，结果不可信）

补丁里的未知字段统一命名为 zzz_unk*：只确认了类型和位置，语义未知，不参与重建。
"""
import struct

from UnityPy.enums import ClassIDType
from UnityPy.helpers import TypeTreeHelper
from UnityPy.helpers.Tpk import get_typetree_nodes

UNITY_VERSION = (2019, 4, 40, 1)
ALIGN_FLAG = 0x4000


class LayoutError(Exception):
    pass


class Node:
    __slots__ = ("type", "name", "align", "children")

    def __init__(self, type_, name, align=False, children=None):
        self.type, self.name, self.align, self.children = type_, name, align, children or []

    def copy(self):
        return Node(self.type, self.name, self.align, [c.copy() for c in self.children])


def F(type_, name, align=False):
    """补丁用的简单字段。"""
    return Node(type_, name, align)


# 补丁：struct 类型名 -> [(锚点字段名, "after"/"before", [新字段...])]
# 同一 struct 类型在树中的每个出现位置都会被打补丁（例如所有 MinMaxCurve）。
# 不同资源块来自不同的游戏版本构建，同一个类可能有多套布局（LAYOUTS 里的变体），
# 读取时逐个尝试，只接受恰好用完全部字节的那一套。
ZZZ_PATCHES = {
    "ParticleSystem": [
        ("lengthInSec", "before", [F("SInt32", "zzz_unk0"), F("SInt32", "zzz_unk1"),
                                   F("float", "zzz_unk2"), F("float", "zzz_unk3")]),
        ("stopAction", "after", [F("SInt32", "zzz_unk4")]),
        # 末尾 17 个字：样本中恒为 -1, 0×13, 1, 1, 1
        ("CustomDataModule", "after", [F("SInt32", "zzz_tail%d" % k) for k in range(17)]),
    ],
    "EmissionModule": [
        ("m_Bursts", "after", [F("SInt32", "zzz_unk0"), F("SInt32", "zzz_unk1"),
                               F("float", "zzz_unk2"), F("float", "zzz_unk3"), F("float", "zzz_unk4"),
                               F("float", "zzz_unk5"), F("SInt32", "zzz_unk6")]),
    ],
}


# Renderer 基类字段（与 AnimeStudio Renderer.cs 的 ZZZ 分支一致）：
# RayTracingMode 后多 m_RayTraceProcedural；SortingOrder 后多 3 个 bool。
_RENDERER_PATCH = [
    ("m_RayTracingMode", "replace", [F("UInt8", "m_RayTracingMode"), F("UInt8", "m_RayTraceProcedural", True)]),
    ("m_SortingOrder", "after", [F("bool", "m_NeedHizCulling"), F("bool", "m_HighShadingRate"),
                                 F("bool", "m_RayTracingLayerMask", True)]),
]
ZZZ_PATCHES["ParticleSystemRenderer"] = _RENDERER_PATCH + [
    ("m_RayTracingLayerMask", "after", [F("float", "m_CullingDistance")]),
    ("m_SortMode", "after", [F("UInt16", "zzz_unk0a"), F("UInt16", "zzz_unk0b")]),
    ("m_AllowRoll", "after", [F("SInt32", "zzz_unk1"), F("SInt32", "zzz_unk2"), F("SInt32", "zzz_unk3")]),
    ("m_MaskInteraction", "after", [F("SInt32", "zzz_tail%d" % k) for k in range(6)]),
]
ZZZ_PATCHES["Light"] = [("m_UseBoundingSphereOverride", "after", [F("SInt32", "zzz_tail0")])]
ZZZ_PATCHES["MeshRenderer"] = _RENDERER_PATCH + [
    ("m_RayTracingLayerMask", "after", [F("float", "m_CullingDistance"), F("SInt32", "zzz_unk0"),
                                        F("SInt32", "zzz_unk1"), F("SInt32", "zzz_unk2")]),
    ("m_AdditionalVertexStreams", "after", [F("SInt32", "zzz_tail0")]),
]


def _extend(base, extra):
    out = {k: list(v) for k, v in base.items()}
    for k, v in extra.items():
        out.setdefault(k, []).extend(v)
    return out


# 较新构建：LightsModule 在 ratio 后多一个字（样本中恒为 1）。
ZZZ_PATCHES_B = _extend(ZZZ_PATCHES, {
    "LightsModule": [("ratio", "after", [F("SInt32", "zzz_unk0")])],
    "ParticleSystemRenderer": [("zzz_tail5", "after", [F("SInt32", "zzz_tailB%d" % k) for k in range(7)])],
})

LAYOUTS = {"A": ZZZ_PATCHES, "B": ZZZ_PATCHES_B}


def _build(flat, i):
    n = flat[i]
    node = Node(n.m_Type, n.m_Name, bool(n.m_MetaFlag & ALIGN_FLAG))
    j = i + 1
    while j < len(flat) and flat[j].m_Level > n.m_Level:
        child, j = _build(flat, j)
        node.children.append(child)
    return node, j


def _apply(node, patches):
    for c in node.children:
        _apply(c, patches)
    for anchor, where, fields in patches.get(node.type, []):
        names = [c.name for c in node.children]
        if anchor not in names:
            raise LayoutError("补丁锚点 %s.%s 不存在" % (node.type, anchor))
        k = names.index(anchor)
        if where == "replace":
            node.children[k:k + 1] = [f.copy() for f in fields]
        else:
            k += 1 if where == "after" else 0
            node.children[k:k] = [f.copy() for f in fields]


_TREE_CACHE = {}


def tree_for(class_name, patches=None):
    key = (class_name, id(patches))
    if key not in _TREE_CACHE:
        flat = TypeTreeHelper.check_nodes(get_typetree_nodes(ClassIDType[class_name].value, UNITY_VERSION))
        root, _ = _build(flat, 0)
        _apply(root, ZZZ_PATCHES if patches is None else patches)
        _TREE_CACHE[key] = root
    return _TREE_CACHE[key]


_PRIM = {
    "SInt8": "b", "UInt8": "B", "char": "B", "bool": "?", "short": "h", "SInt16": "h", "UInt16": "H",
    "unsigned short": "H", "int": "i", "SInt32": "i", "UInt32": "I", "unsigned int": "I", "Type*": "I",
    "long long": "q", "SInt64": "q", "UInt64": "Q", "unsigned long long": "Q", "FileSize": "Q",
    "float": "f", "double": "d",
}


class Reader:
    def __init__(self, data, trace=None):
        self.data, self.pos, self.trace = data, 0, trace

    def unpack(self, fmt):
        size = struct.calcsize("<" + fmt)
        if self.pos + size > len(self.data):
            raise LayoutError("越界：在 %d 读取 %d 字节，总长 %d" % (self.pos, size, len(self.data)))
        v = struct.unpack_from("<" + fmt, self.data, self.pos)[0]
        self.pos += size
        return v

    def align(self):
        self.pos = (self.pos + 3) & ~3

    def read(self, node, path=""):
        start = self.pos
        t = node.type
        if t in _PRIM:
            v = self.unpack(_PRIM[t])
        elif t == "string":
            n = self.unpack("i")
            v = self.data[self.pos:self.pos + n].decode("utf-8", "replace")
            self.pos += n
            self.align()
        elif t == "TypelessData":
            n = self.unpack("i")
            v = self.data[self.pos:self.pos + n]
            self.pos += n
        elif node.children and node.children[0].type == "Array":
            arr = node.children[0]
            n = self.unpack("i")
            if n < 0 or n > 1_000_000:
                raise LayoutError("%s 数组长度异常 %d @%d" % (path, n, start))
            elem = arr.children[1]
            v = [self.read(elem, "%s[%d]" % (path, k)) for k in range(n)]
            if arr.align:
                self.align()
        elif t == "map":
            arr = node.children[0]
            n = self.unpack("i")
            pair = arr.children[1]
            v = [(self.read(pair.children[0], path + ".k"), self.read(pair.children[1], path + ".v")) for _ in range(n)]
            if arr.align:
                self.align()
        else:
            v = {}
            for c in node.children:
                v[c.name] = self.read(c, path + "." + c.name)
        if node.align:
            self.align()
        if self.trace is not None:
            self.trace.append((start, self.pos, path, t, v))
        return v


def read_layout(class_name, data, patches):
    r = Reader(data)
    obj = r.read(tree_for(class_name, patches), class_name)
    if r.pos != len(data):
        raise LayoutError("%s 读取 %d / %d 字节" % (class_name, r.pos, len(data)))
    return obj


def read(class_name, data):
    """按 LAYOUTS 逐个尝试，返回 (对象, 布局名)。全部失败时抛出走得最远那套布局的错误。"""
    best = None
    for name, patches in LAYOUTS.items():
        try:
            return read_layout(class_name, data, patches), name
        except LayoutError as e:
            rows, err, pos = trace(class_name, data, 0, patches)
            if best is None or pos > best[0]:
                best = (pos, name, e)
    raise LayoutError("%s（最接近的布局 %s）" % (best[2], best[1]))


def trace(class_name, data, depth=2, patches=None):
    """逐字段读取并返回 (起点, 终点, 路径, 类型, 值) 列表；出错时附带错误位置，用于定位布局分歧。

    patches 为空时选用读得最远的布局。
    """
    if patches is None:
        results = [trace(class_name, data, depth, p) for p in LAYOUTS.values()]
        ok = [x for x in results if x[1] is None]
        return ok[0] if ok else max(results, key=lambda x: x[2])
    log = []
    r = Reader(data, log)
    err = None
    try:
        r.read(tree_for(class_name, patches), class_name)
        if r.pos != len(data):
            err = "读取 %d / %d 字节" % (r.pos, len(data))
    except LayoutError as e:
        err = str(e)
    rows = [x for x in log if x[2].count(".") <= depth]
    rows.sort(key=lambda x: (x[0], -x[1]))
    return rows, err, r.pos
