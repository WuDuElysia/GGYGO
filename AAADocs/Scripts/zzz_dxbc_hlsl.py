"""把 AnimeStudio 导出的 D3D11 反汇编（vs_5_0 / ps_5_0）逐条翻译成可放进 UE 材质 Custom 节点的 HLSL。

输入是 zzz_shader_variants.py 导出的 .shader 文本：每个 SubProgram 后带 "//@ " 反射绑定表
（常量缓冲布局、贴图寄存器）。翻译规则：

    寄存器 r#/x#[]/o#/v# 一律用 uint4 存位模式，按指令类型 asfloat/asint 取值、asuint 写回
        —— DXBC 寄存器无类型，比较结果是 0xFFFFFFFF 位掩码，用 float 存会被当 NaN 改写。
    cbN[i].c → 按绑定表找到属性：UnityPerMaterial 的属性变成 Custom 输入（同名材质参数），
        其余（$Globals、UnityPerDraw…）交给 provider 表；provider 没列出的全局量直接报错。
    tN → 绑定表里的贴图名，采样走 F.S / F.SL（由调用方的前导代码定义，负责 Unity→UE 的 V 翻转）。
    先做死代码消除：VS 只保留 PS 实际读取的输出（SV_POSITION 不要，像素位置由 UE 给），
        PS 只保留 o0；剩下引用的全局量才需要 provider。

未知指令、未知全局量、无法解析的操作数一律抛 TranslateError，不生成近似代码。
"""
import re
from collections import OrderedDict


class TranslateError(Exception):
    pass


COMP = "xyzw"


# ---------------------------------------------------------------- 解析 .shader 文本

def parse_shader(text):
    """返回 {"props": {name: (display, type)}, "passes": [{name, state:[...], vp, fp}]}，只取 d3d11 子程序。"""
    props = OrderedDict()
    passes = []
    lines = text.split("\n")
    i = 0
    in_props = False
    cur_pass = None
    prog = None
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("Properties {"):
            in_props = True
        elif in_props:
            if s == "}":
                in_props = False
            else:
                m = re.match(r'((?:\[[^\]]*\]\s*)*)(\w+)\s*\("([^"]*)",\s*(\w+)', s)
                if m:
                    dm = re.search(r'=\s*"(\w*)"', s)
                    dv = re.search(r'\)\s*=\s*(\([^)]*\)|[-+0-9.eE]+)\s*$', s)
                    default = None
                    if dv:
                        txt = dv.group(1)
                        default = [float(x) for x in txt.strip("()").split(",")] if txt.startswith("(") else float(txt)
                    props[m.group(2)] = {"type": m.group(4), "attrs": m.group(1),
                                         "tex_default": dm.group(1) if dm else None, "default": default}
        if s.startswith("Pass {"):
            cur_pass = {"name": "", "lightmode": "", "state": [], "vp": None, "fp": None}
            passes.append(cur_pass)
            prog = None
        elif cur_pass is not None and s.startswith('Name "') and not cur_pass["name"]:
            cur_pass["name"] = s.split('"')[1]
        elif cur_pass is not None and s.startswith("Tags {") and not cur_pass["lightmode"]:
            lm = re.search(r'"LIGHTMODE"\s*=\s*"([^"]+)"', s)
            cur_pass["lightmode"] = lm.group(1) if lm else ""
        elif cur_pass is not None and re.match(r"(Blend|BlendOp|ZWrite|ZTest|Cull|ColorMask|Offset)\b", s):
            cur_pass["state"].append(s)
        elif s.startswith('Program "'):
            prog = s.split('"')[1]
        elif s.startswith('SubProgram "') and cur_pass is not None:
            api = s.split('"')[1].strip()
            j = i + 1
            body = []
            while j < len(lines) and not lines[j].startswith("SubProgram ") and not lines[j].startswith("}"):
                body.append(lines[j])
                j += 1
            if api == "d3d11" and prog in ("vp", "fp") and cur_pass[prog] is None:
                cur_pass[prog] = parse_subprogram("\n".join(body))
            i = j - 1
        i += 1
    return {"props": props, "passes": passes}


def parse_subprogram(text):
    keywords = set()
    for m in re.finditer(r'(?:Local )?Keywords \{([^}]*)\}', text):
        keywords |= set(re.findall(r'"([^"]+)"', m.group(1)))
    sig_in, sig_out = parse_signature(text, "Input signature"), parse_signature(text, "Output signature")
    asm = []
    started = False
    for line in text.split("\n"):
        s = line.strip().strip('"')
        if re.match(r"(vs|ps)_[45]_[01]$", s):
            started = True
            asm.append(s)
            continue
        if started:
            if s.startswith("//") or not s:
                if s.startswith("// Approximately"):
                    break
                continue
            asm.append(s)
    binds = parse_bindings(text)
    return {"keywords": keywords, "in": sig_in, "out": sig_out, "asm": asm, "bind": binds}


def parse_signature(text, title):
    m = re.search(r"// %s:\n//\n// Name.*\n// -+.*\n((?://.*\n)*?)//\n" % title, text)
    rows = []
    if not m:
        return rows
    for line in m.group(1).split("\n"):
        p = line[2:].split()
        if len(p) < 6:
            continue
        name, idx, mask, reg = p[0], int(p[1]), p[2], int(p[3])
        used = p[6] if len(p) > 6 else ""
        rows.append({"name": name, "index": idx, "mask": mask, "reg": reg, "sys": p[4], "used": used})
    return rows


def parse_bindings(text):
    b = {"cbbind": {}, "cb": {}, "tex": {}, "smp": {}}
    for line in text.split("\n"):
        line = line.lstrip('"')
        if not line.startswith("//@ "):
            continue
        p = line[4:].split()
        if p[0] == "CBBIND":
            b["cbbind"][int(p[2])] = p[1]
        elif p[0] == "CB":
            b["cb"].setdefault(p[1], {"size": int(p[2]), "params": []})["size"] = int(p[2])
        elif p[0] in ("V", "M"):
            cb = b["cb"].setdefault(p[1], {"size": 0, "params": []})
            cb["params"].append({"kind": p[0], "name": p[2], "offset": int(p[3]), "dim": int(p[4]),
                                 "arr": int(p[5]), "type": int(p[6])})
        elif p[0] == "TEX":
            b["tex"][int(p[2])] = {"name": p[1], "sampler": int(p[3]), "dim": int(p[4])}
        elif p[0] == "SMP":
            b["smp"][int(p[2])] = int(p[1])
    return b


# ---------------------------------------------------------------- 操作数

OPND_RE = re.compile(r"^(?P<kind>icb|cb|r|x|v|o|t|s)(?P<idx>\d*)(?:\[(?P<arr>[^\]]+)\])?(?:\.(?P<swz>[xyzw]+))?$")


class Opnd:
    __slots__ = ("kind", "idx", "arr", "swz", "neg", "abs", "lit")

    def __init__(self):
        self.kind = self.idx = self.arr = self.swz = self.lit = None
        self.neg = self.abs = False

    def comps(self, positions):
        """按目标写掩码的位置取源分量；单分量 swizzle 视为广播。"""
        sw = self.swz or "xyzw"
        if len(sw) == 1:
            return [sw] * len(positions)
        return [sw[p] for p in positions]


def split_operands(s):
    out, depth, cur = [], 0, ""
    for ch in s:
        if ch in "([" and not (ch == "(" and cur.strip() == ""):
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "," and depth == 0:
            out.append(cur.strip())
            cur = ""
        else:
            cur += ch
    if cur.strip():
        out.append(cur.strip())
    return out


def parse_operand(tok):
    o = Opnd()
    t = tok.strip()
    if t.startswith("-"):
        o.neg, t = True, t[1:]
    if t.startswith("|"):
        end = t.rindex("|")
        o.abs, t = True, t[1:end] + t[end + 1:]
    if t == "null":
        o.kind = "null"
        return o
    if t.startswith("l("):
        o.kind = "l"
        o.lit = [x.strip() for x in t[2:-1].split(",")]
        return o
    m = OPND_RE.match(t)
    if not m:
        raise TranslateError("无法解析操作数: " + tok)
    o.kind = m.group("kind")
    o.idx = int(m.group("idx")) if m.group("idx") else None
    o.arr = m.group("arr")
    o.swz = m.group("swz")
    return o


def split_instr(line):
    m = re.match(r"^(\S+?)(\([^)]*\))*(?:\s+(.*))?$", line)
    head = line.split(None, 1)
    op = head[0]
    rest = head[1] if len(head) > 1 else ""
    # sample_indexable(texture2d)(float,float,float,float) 这类带类型后缀的写法
    while rest.startswith("("):
        k = rest.index(")")
        op += rest[:k + 1]
        rest = rest[k + 1:].lstrip()
    base = re.sub(r"\(.*$", "", op)
    sat = base.endswith("_sat")
    if sat:
        base = base[:-4]
    return base, sat, [parse_operand(x) for x in split_operands(rest)] if rest else []


# ---------------------------------------------------------------- 值渲染

def lit_comp(token, typ):
    """字面量单分量 → HLSL 常量。反汇编里浮点总带小数点，整数不带，十六进制是位模式。"""
    t = token
    if t.startswith("0x") or t.startswith("-0x"):
        v = int(t, 16) & 0xFFFFFFFF
        if typ == "u":
            return "%du" % v
        if typ == "i":
            return "asint(%du)" % v
        return "asfloat(%du)" % v
    is_float = "." in t or "e" in t or "inf" in t.lower() or "nan" in t.lower()
    if is_float:
        f = float(t)
        if typ == "f":
            return repr(f) if "inf" not in t else ("(1.#INF)" if f > 0 else "(-1.#INF)")
        return ("asuint(%r)" if typ == "u" else "asint(%r)") % f
    v = int(t)
    if typ == "f":
        return "0.0" if v == 0 else "asfloat(%du)" % (v & 0xFFFFFFFF)
    if typ == "u":
        return "%du" % (v & 0xFFFFFFFF)
    return "%d" % v


def vec(typ, n):
    base = {"f": "float", "u": "uint", "i": "int"}[typ]
    return base if n == 1 else "%s%d" % (base, n)


def convert(expr, src, dst, n):
    if src == dst:
        return expr
    if dst == "f":
        return "asfloat(%s)" % expr
    if dst == "u":
        return "asuint(%s)" % expr
    return "asint(%s)" % expr


class Ctx:
    """一次翻译的上下文：寄存器前缀、常量缓冲解析器、引用到的贴图/材质参数/全局量。"""

    def __init__(self, sub, prefix, provider, material_cb="UnityPerMaterial"):
        self.sub, self.p, self.provider, self.material_cb = sub, prefix, provider, material_cb
        self.mat_params = OrderedDict()   # name -> dim
        self.globals_used = OrderedDict()  # (name,row,comp)
        self.textures = OrderedDict()      # tex name -> kind
        self.dyn_arrays = OrderedDict()    # local array name -> (cb, param)
        self.missing = OrderedDict()       # 没有 provider 的全局量引用
        self.icb = None

    # -- 常量缓冲 ----------------------------------------------------------
    def cb_param(self, slot, reg):
        name = self.sub["bind"]["cbbind"].get(slot)
        if name is None:
            raise TranslateError("cb%d 没有绑定信息" % slot)
        cb = self.sub["bind"]["cb"].get(name)
        if cb is None:
            raise TranslateError("缺少常量缓冲 %s 的布局" % name)
        return name, cb

    def resolve_cb(self, slot, reg, comp):
        """静态下标：返回 (cbname, param, element/row, comp_index)。"""
        name, cb = self.cb_param(slot, reg)
        off = reg * 16 + COMP.index(comp) * 4
        for p in cb["params"]:
            if p["kind"] == "V":
                n = max(1, p["arr"])
                for e in range(n):
                    base = p["offset"] + e * 16
                    if base <= off < base + 4 * p["dim"]:
                        return name, p, (e if p["arr"] else None), (off - base) // 4
            else:
                rows = p["dim"]
                n = max(1, p["arr"]) * 4
                for r in range(n):
                    base = p["offset"] + r * 16
                    if base <= off < base + 16:
                        return name, p, r, (off - base) // 4
        raise TranslateError("%s 偏移 %d（cb%d[%d].%s）没有对应属性" % (name, off, slot, reg, comp))

    def cb_expr(self, slot, reg, comp):
        cbname, p, elem, ci = self.resolve_cb(slot, reg, comp)
        if cbname == self.material_cb:
            if p["kind"] != "V" or elem is not None:
                raise TranslateError("材质属性 %s 是数组/矩阵，Custom 节点无法直接表达" % p["name"])
            self.mat_params[p["name"]] = p["dim"]
            return p["name"] if p["dim"] == 1 else "%s.%s" % (p["name"], COMP[ci])
        return self.global_expr(p["name"], elem or 0, COMP[ci])

    def global_expr(self, name, row, comp):
        g = self.provider.get(name)
        if g is None:
            # 先记下，死代码消除后仍被引用才报错（只喂给 SV_POSITION 的相机矩阵会被删掉）
            self.missing[(name, row, comp)] = True
            return "G_%s_%d.%s" % (name.lstrip("_"), row, comp)
        rows = g["rows"]
        if row >= len(rows):
            raise TranslateError("全局量 %s 第 %d 行未提供" % (name, row))
        allowed = g.get("comps", "xyzw")
        allowed = allowed[row] if isinstance(allowed, list) else allowed
        if comp not in allowed:
            raise TranslateError("全局量 %s[%d].%s 未提供（只确认了 %s）" % (name, row, comp, allowed))
        self.globals_used[(name, row, comp)] = True
        return "(%s).%s" % (rows[row], comp)

    def cb_dynamic(self, slot, arr, comp):
        m = re.match(r"^(r|x)(\d+)\.([xyzw])\s*\+\s*(\d+)$", arr.strip())
        if not m:
            raise TranslateError("无法解析动态下标 " + arr)
        idx_reg, idx_comp, base = "%s%s%s" % (self.p, m.group(1), m.group(2)), m.group(3), int(m.group(4))
        cbname, p, elem, _ = self.resolve_cb(slot, base, "x")
        if cbname == self.material_cb:
            raise TranslateError("材质常量缓冲的动态下标（%s）不支持" % p["name"])
        start = (p["offset"] // 16)
        g = self.provider.get(p["name"])
        if g is None:
            self.missing[(p["name"], "dyn", comp)] = True
            return "GA_%s[%s.%s + %d].%s" % (p["name"].lstrip("_"), idx_reg, idx_comp, base - start, comp)
        allowed = g.get("comps", "xyzw")
        for r in range(len(g["rows"])):
            a = allowed[r] if isinstance(allowed, list) else allowed
            if comp not in a:
                raise TranslateError("全局量 %s[*].%s 未全部提供" % (p["name"], comp))
            self.globals_used[(p["name"], r, comp)] = True
        arrname = "GA_" + p["name"].lstrip("_")
        self.dyn_arrays[arrname] = g["rows"]
        return "%s[%s.%s + %d].%s" % (arrname, idx_reg, idx_comp, base - start, comp)

    # -- 读操作数 ------------------------------------------------------------
    def read(self, o, positions, typ):
        """返回 (表达式, 分量数)。positions 是目标掩码位置（0..3）。"""
        n = len(positions)
        if o.kind == "l":
            vals = o.lit if len(o.lit) > 1 else o.lit * 4
            parts = [lit_comp(vals[p], typ) for p in positions]
            e = parts[0] if n == 1 else "%s(%s)" % (vec(typ, n), ", ".join(parts))
            return self.mod(e, o, typ), n
        comps = o.comps(positions)
        if o.kind in ("r", "o", "v"):
            e = "%s%s%d.%s" % (self.p, o.kind, o.idx, "".join(comps))
            e = convert(e, "u", typ, n)
        elif o.kind == "x":
            idx = self.index_expr(o.arr)
            e = convert("%sx%d[%s].%s" % (self.p, o.idx, idx, "".join(comps)), "u", typ, n)
        elif o.kind == "icb":
            idx = self.index_expr(o.arr)
            e = convert("%sicb[%s].%s" % (self.p, idx, "".join(comps)), "u", typ, n)
        elif o.kind == "cb":
            slot = o.idx
            if re.match(r"^\d+$", o.arr):
                parts = [self.cb_expr(slot, int(o.arr), c) for c in comps]
            else:
                parts = [self.cb_dynamic(slot, o.arr, c) for c in comps]
            e = self.join_parts(parts, n)
            e = convert(e, "f", typ, n)
        else:
            raise TranslateError("不能作为数值读取的操作数类型 " + o.kind)
        return self.mod(e, o, typ), n

    @staticmethod
    def join_parts(parts, n):
        if n == 1:
            return parts[0]
        # 同一属性连续分量合成 name.xyz
        m = [re.match(r"^(\w+)\.([xyzw])$", x) for x in parts]
        if all(m) and len({x.group(1) for x in m}) == 1:
            return "%s.%s" % (m[0].group(1), "".join(x.group(2) for x in m))
        return "float%d(%s)" % (n, ", ".join(parts))

    def mod(self, e, o, typ):
        if o.abs:
            e = "abs(%s)" % e
        if o.neg:
            e = "(-%s)" % e
        return e

    def index_expr(self, arr):
        a = arr.strip()
        if re.match(r"^\d+$", a):
            return a
        m = re.match(r"^(r|x)(\d+)\.([xyzw])\s*\+\s*(\d+)$", a)
        if not m:
            raise TranslateError("无法解析下标 " + arr)
        e = "%s%s%s.%s" % (self.p, m.group(1), m.group(2), m.group(3))
        return e if m.group(4) == "0" else "%s + %s" % (e, m.group(4))

    def dest(self, o):
        if o.kind not in ("r", "o", "x"):
            raise TranslateError("非法目标 " + o.kind)
        mask = o.swz or "xyzw"
        positions = [COMP.index(c) for c in mask]
        if o.kind == "x":
            name = "%sx%d[%s].%s" % (self.p, o.idx, self.index_expr(o.arr), mask)
        else:
            name = "%s%s%d.%s" % (self.p, o.kind, o.idx, mask)
        return name, positions


# ---------------------------------------------------------------- 指令

FLOAT_UNARY = {"frc": "frac", "round_ne": "round", "round_ni": "floor", "round_pi": "ceil", "round_z": "trunc",
               "log": "log2", "exp": "exp2", "rsq": "rsqrt", "sqrt": "sqrt", "rcp": "rcp",
               "deriv_rtx": "ddx", "deriv_rty": "ddy", "deriv_rtx_coarse": "ddx", "deriv_rty_coarse": "ddy",
               "deriv_rtx_fine": "ddx_fine", "deriv_rty_fine": "ddy_fine"}
FLOAT_BINARY = {"add": "({a} + {b})", "mul": "({a} * {b})", "div": "({a} / {b})", "min": "min({a}, {b})",
                "max": "max({a}, {b})"}
FLOAT_CMP = {"lt": "<", "ge": ">=", "eq": "==", "ne": "!="}
INT_BINARY = {"iadd": ("i", "({a} + {b})"), "and": ("u", "({a} & {b})"), "or": ("u", "({a} | {b})"),
              "xor": ("u", "({a} ^ {b})"), "ishl": ("i", "({a} << ({b} & 31))"), "ishr": ("i", "({a} >> ({b} & 31))"),
              "ushr": ("u", "({a} >> ({b} & 31u))"), "imin": ("i", "min({a}, {b})"), "imax": ("i", "max({a}, {b})"),
              "umin": ("u", "min({a}, {b})"), "umax": ("u", "max({a}, {b})")}
INT_CMP = {"ilt": ("i", "<"), "ige": ("i", ">="), "ieq": ("i", "=="), "ine": ("i", "!="),
           "ult": ("u", "<"), "uge": ("u", ">=")}
CONV = {"ftou": ("f", "uint"), "ftoi": ("f", "int"), "utof": ("u", "float"), "itof": ("i", "float")}
SAMPLE = {"sample", "sample_l", "sample_b", "sample_d", "sample_indexable", "sample_l_indexable",
          "sample_b_indexable", "sample_d_indexable"}


def mask_str(positions):
    return "".join(COMP[p] for p in positions)


class Ins:
    __slots__ = ("defs", "uses", "side", "text", "refs")

    def __init__(self, text, defs=(), uses=(), side=False):
        self.text, self.defs, self.uses, self.side = text, list(defs), set(uses), side
        self.refs = None


def var_of(ctx, o):
    """操作数涉及的寄存器变量与分量（用于活跃性分析）。"""
    out = set()
    if o.kind in ("r", "o", "v"):
        sw = o.swz or "xyzw"
        out |= {("%s%d" % (o.kind, o.idx), c) for c in sw}
    elif o.kind == "x":
        out.add(("x%d" % o.idx, "*"))
    if o.arr:
        for m in re.finditer(r"(r|x)(\d+)\.([xyzw])", o.arr):
            out.add((("%s%s" % (m.group(1), m.group(2))) if m.group(1) == "r" else "x" + m.group(2),
                     m.group(3) if m.group(1) == "r" else "*"))
    return out


def src_uses(ctx, o, positions):
    if o.kind in ("r", "o", "v"):
        return {("%s%d" % (o.kind, o.idx), c) for c in o.comps(positions)}
    return var_of(ctx, o)


def dest_defs(o):
    if o.kind == "x":
        return [("x%d" % o.idx, "*", False)]
    kill = True
    return [("%s%d" % (o.kind, o.idx), c, kill) for c in (o.swz or "xyzw")]


def translate_ins(ctx, op, sat, ops):
    """返回 Ins。"""
    def wr(d, expr_f=None, expr_u=None, n=None):
        name, pos = ctx.dest(d)
        if expr_f is not None:
            e = "saturate(%s)" % expr_f if sat else expr_f
            rhs = "asuint(%s)" % e
        else:
            if sat:
                raise TranslateError("%s 带 _sat 但结果不是浮点" % op)
            rhs = expr_u
        return "%s = %s;" % (name, rhs)

    if op in ("mov", "movc", "swapc") or op in FLOAT_UNARY or op in FLOAT_BINARY or op in FLOAT_CMP \
            or op in INT_BINARY or op in INT_CMP or op in CONV or op in ("mad", "not", "ineg", "dp2", "dp3", "dp4"):
        d = ops[0]
        _, pos = ctx.dest(d)
        n = len(pos)
        uses = set()
        if op in ("dp2", "dp3", "dp4"):
            k = int(op[2])
            dpos = list(range(k))
            a, _ = ctx.read(ops[1], dpos, "f")
            b, _ = ctx.read(ops[2], dpos, "f")
            uses |= src_uses(ctx, ops[1], dpos) | src_uses(ctx, ops[2], dpos)
            e = "dot(%s, %s)" % (a, b)
            if n > 1:
                e = "(%s)%s" % (vec("f", n), e)
            text = wr(d, expr_f=e)
        else:
            for s in ops[1:]:
                uses |= src_uses(ctx, s, pos)
            if op == "mov":
                typed = ops[1].neg or ops[1].abs or sat
                if typed:
                    text = wr(d, expr_f=ctx.read(ops[1], pos, "f")[0])
                else:
                    text = wr(d, expr_u=ctx.read(ops[1], pos, "u")[0])
            elif op == "movc":
                c = ctx.read(ops[1], pos, "u")[0]
                typed = any(x.neg or x.abs for x in ops[2:]) or sat
                t = "f" if typed else "u"
                a, b = ctx.read(ops[2], pos, t)[0], ctx.read(ops[3], pos, t)[0]
                e = "select(%s != 0u, %s, %s)" % (c, a, b) if n > 1 else "((%s != 0u) ? %s : %s)" % (c, a, b)
                text = wr(d, expr_f=e) if typed else wr(d, expr_u=e)
            elif op in FLOAT_UNARY:
                text = wr(d, expr_f="%s(%s)" % (FLOAT_UNARY[op], ctx.read(ops[1], pos, "f")[0]))
            elif op in FLOAT_BINARY:
                a, b = ctx.read(ops[1], pos, "f")[0], ctx.read(ops[2], pos, "f")[0]
                text = wr(d, expr_f=FLOAT_BINARY[op].format(a=a, b=b))
            elif op == "mad":
                a, b, c = [ctx.read(x, pos, "f")[0] for x in ops[1:4]]
                text = wr(d, expr_f="(%s * %s + %s)" % (a, b, c))
            elif op in FLOAT_CMP:
                a, b = ctx.read(ops[1], pos, "f")[0], ctx.read(ops[2], pos, "f")[0]
                cond = "(%s %s %s)" % (a, FLOAT_CMP[op], b)
                e = ("select(%s, (uint%d)0xFFFFFFFFu, (uint%d)0u)" % (cond, n, n)) if n > 1 else \
                    "(%s ? 0xFFFFFFFFu : 0u)" % cond
                text = wr(d, expr_u=e)
            elif op in INT_BINARY:
                t, f = INT_BINARY[op]
                a, b = ctx.read(ops[1], pos, t)[0], ctx.read(ops[2], pos, t)[0]
                text = wr(d, expr_u=convert(f.format(a=a, b=b), t, "u", n))
            elif op in INT_CMP:
                t, cmpop = INT_CMP[op]
                a, b = ctx.read(ops[1], pos, t)[0], ctx.read(ops[2], pos, t)[0]
                cond = "(%s %s %s)" % (a, cmpop, b)
                e = ("select(%s, (uint%d)0xFFFFFFFFu, (uint%d)0u)" % (cond, n, n)) if n > 1 else \
                    "(%s ? 0xFFFFFFFFu : 0u)" % cond
                text = wr(d, expr_u=e)
            elif op == "not":
                text = wr(d, expr_u="(~%s)" % ctx.read(ops[1], pos, "u")[0])
            elif op == "ineg":
                text = wr(d, expr_u="asuint(-%s)" % ctx.read(ops[1], pos, "i")[0])
            elif op in CONV:
                t, to = CONV[op]
                e = "(%s)(%s)" % (vec("f" if to == "float" else ("u" if to == "uint" else "i"), n),
                                  ctx.read(ops[1], pos, t)[0])
                if to == "float":
                    text = wr(d, expr_f=e)
                else:
                    text = wr(d, expr_u=convert(e, "u" if to == "uint" else "i", "u", n))
            else:
                raise TranslateError("未实现 " + op)
        return Ins(text, dest_defs(d), uses)

    if op in ("sincos",):
        dsin, dcos, s = ops
        lines, defs, uses = [], [], set()
        for d, fn in ((dsin, "sin"), (dcos, "cos")):
            if d.kind == "null":
                continue
            _, pos = ctx.dest(d)
            uses |= src_uses(ctx, s, pos)
            lines.append(wr(d, expr_f="%s(%s)" % (fn, ctx.read(s, pos, "f")[0])))
            defs += dest_defs(d)
        return Ins(" ".join(lines), defs, uses)

    if op in SAMPLE:
        base = op.replace("_indexable", "")
        d, coord, tex, smp = ops[:4]
        name, pos = ctx.dest(d)
        tinfo = ctx.sub["bind"]["tex"].get(tex.idx)
        if tinfo is None:
            raise TranslateError("t%d 没有绑定信息" % tex.idx)
        if tinfo["dim"] != 2:
            raise TranslateError("贴图 %s 维度 %d 不支持（只支持 2D）" % (tinfo["name"], tinfo["dim"]))
        tname = tinfo["name"]
        ctx.textures[tname] = True
        uv = ctx.read(coord, [0, 1], "f")[0]
        uses = src_uses(ctx, coord, [0, 1])
        rsw = "".join((tex.swz or "xyzw")[p] for p in pos)
        if base == "sample":
            call = "F.S(%s, %sSampler, %s)" % (tname, tname, uv)
        elif base == "sample_l":
            lod = ctx.read(ops[4], [0], "f")[0]
            uses |= src_uses(ctx, ops[4], [0])
            call = "F.SL(%s, %sSampler, %s, %s)" % (tname, tname, uv, lod)
        elif base == "sample_b":
            bias = ctx.read(ops[4], [0], "f")[0]
            uses |= src_uses(ctx, ops[4], [0])
            call = "F.SB(%s, %sSampler, %s, %s)" % (tname, tname, uv, bias)
        else:
            raise TranslateError("未实现采样指令 " + op)
        if tname in ctx.provider.get("__textures__", {}):
            call = ctx.provider["__textures__"][tname].format(uv=uv)
            del ctx.textures[tname]
        return Ins(wr(d, expr_f="(%s).%s" % (call, rsw)), dest_defs(d), uses)

    raise TranslateError("未实现指令 " + op)


# ---------------------------------------------------------------- 程序结构与死代码消除

REF_FIELDS = ("mat_params", "globals_used", "textures", "dyn_arrays", "missing")


def capture(ctx, fn):
    """在独立的引用集合里执行 fn，返回 (结果, 引用)；死代码删掉后只按保留指令的引用汇总。"""
    saved = {k: getattr(ctx, k) for k in REF_FIELDS}
    for k in REF_FIELDS:
        setattr(ctx, k, OrderedDict())
    try:
        res = fn()
        refs = {k: getattr(ctx, k) for k in REF_FIELDS}
    finally:
        for k, v in saved.items():
            setattr(ctx, k, v)
    return res, refs


def parse_program(ctx, asm):
    decl = {"temps": 0, "x": {}, "icb": None, "inputs": {}, "outputs": {}}
    root = []
    stack = [root]
    i = 1  # 跳过 vs_5_0 / ps_5_0
    while i < len(asm):
        s = asm[i]
        if s.startswith("dcl_immediateConstantBuffer"):
            buf = s
            while not re.search(r"\}\s*\}\s*$", buf) and i + 1 < len(asm):
                i += 1
                buf += " " + asm[i]
            rows = re.findall(r"\{([^{}]*)\}", buf)
            decl["icb"] = [[x.strip() for x in r.split(",")] for r in rows]
        elif s.startswith("dcl_temps"):
            decl["temps"] = int(s.split()[1])
        elif s.startswith("dcl_indexableTemp"):
            m = re.match(r"dcl_indexableTemp x(\d+)\[(\d+)\], (\d+)", s)
            decl["x"][int(m.group(1))] = int(m.group(2))
        elif s.startswith("dcl_input"):
            m = re.search(r"\bv(\d+)\.?([xyzw]*)", s)
            if m:
                decl["inputs"].setdefault(int(m.group(1)), set()).update(m.group(2) or "xyzw")
        elif s.startswith("dcl_output"):
            m = re.search(r"\bo(\d+)\.?([xyzw]*)", s)
            if m:
                decl["outputs"][int(m.group(1))] = m.group(2) or "xyzw"
        elif s.startswith("dcl_"):
            pass
        else:
            op, sat, ops = split_instr(s)
            if op in ("if_nz", "if_z"):
                c, refs = capture(ctx, lambda: ctx.read(ops[0], [0], "u")[0])
                node = {"t": "if", "cond": "%s %s 0u" % (c, "!=" if op == "if_nz" else "=="),
                        "uses": src_uses(ctx, ops[0], [0]), "then": [], "else": None, "refs": refs}
                stack[-1].append(node)
                stack.append(node["then"])
            elif op == "else":
                stack.pop()
                node = stack[-1][-1]
                node["else"] = []
                stack.append(node["else"])
            elif op == "endif":
                stack.pop()
            elif op == "loop":
                node = {"t": "loop", "body": []}
                stack[-1].append(node)
                stack.append(node["body"])
            elif op == "endloop":
                stack.pop()
            elif op in ("break", "continue"):
                stack[-1].append(Ins("%s;" % op, side=True))
            elif op in ("breakc_nz", "breakc_z", "continuec_nz", "continuec_z", "discard_nz", "discard_z"):
                c = ctx.read(ops[0], [0], "u")[0]
                kind = op.split("c_")[0] if not op.startswith("discard") else "discard"
                cmpop = "!=" if op.endswith("_nz") else "=="
                act = "clip(-1.0)" if kind == "discard" else kind
                stack[-1].append(Ins("if (%s %s 0u) { %s; }" % (c, cmpop, act), (), src_uses(ctx, ops[0], [0]), True))
            elif op == "ret":
                if len(stack) != 1 or i != len(asm) - 1:
                    raise TranslateError("程序中途 ret 不支持")
            else:
                ins, refs = capture(ctx, lambda: translate_ins(ctx, op, sat, ops))
                ins.refs = refs
                stack[-1].append(ins)
        i += 1
    if len(stack) != 1:
        raise TranslateError("控制流未闭合")
    return decl, root


def live_block(nodes, live):
    kept = []
    live = set(live)
    for node in reversed(nodes):
        if isinstance(node, Ins):
            need = node.side or any((v, c) in live for v, c, _ in node.defs)
            if need:
                kept.append(node)
                for v, c, kill in node.defs:
                    if kill:
                        live.discard((v, c))
                live |= node.uses
        elif node["t"] == "if":
            tk, lt = live_block(node["then"], live)
            ek, le = live_block(node["else"], live) if node["else"] is not None else ([], set(live))
            if tk or ek:
                kept.append({"t": "if", "cond": node["cond"], "then": tk, "refs": node.get("refs"),
                             "else": ek if node["else"] is not None else None})
                live = lt | le | node["uses"]
        else:
            cur = set(live)
            while True:
                bk, li = live_block(node["body"], cur | live)
                if li <= cur:
                    break
                cur |= li
            if bk:
                kept.append({"t": "loop", "body": bk})
                live = cur | live
    kept.reverse()
    return kept, live


def collect_refs(ctx, nodes):
    for node in nodes:
        refs = node.refs if isinstance(node, Ins) else node.get("refs")
        if refs:
            for k in REF_FIELDS:
                getattr(ctx, k).update(refs[k])
        if not isinstance(node, Ins):
            collect_refs(ctx, node.get("then") or node.get("body") or [])
            collect_refs(ctx, node.get("else") or [])


def emit(nodes, indent="    "):
    out = []
    for node in nodes:
        if isinstance(node, Ins):
            out.append(indent + node.text)
        elif node["t"] == "if":
            out.append(indent + "if (%s) {" % node["cond"])
            out += emit(node["then"], indent + "    ")
            if node["else"]:
                out.append(indent + "} else {")
                out += emit(node["else"], indent + "    ")
            out.append(indent + "}")
        else:
            out.append(indent + "[loop] while (true) {")
            out += emit(node["body"], indent + "    ")
            out.append(indent + "}")
    return out


def translate(sub, prefix, provider, needed_outputs):
    """needed_outputs: {o寄存器号: 分量串}。返回 dict(code, live_inputs, mat_params, textures, ...)。"""
    ctx = Ctx(sub, prefix, provider)
    decl, tree = parse_program(ctx, sub["asm"])
    need = {("o%d" % r, c) for r, comps in needed_outputs.items() for c in comps}
    kept, live_in = live_block(tree, need)
    for k in REF_FIELDS:
        setattr(ctx, k, OrderedDict())
    collect_refs(ctx, kept)
    if ctx.missing and not provider.get("__discover__"):
        raise TranslateError("全局量没有提供方（provider 表需显式列出）: %s" % sorted({m[0] for m in ctx.missing}))
    # 可索引临时数组按 0 初始化且只做部分写入，活跃性分析里不会被“杀死”，不算未定义读取。
    bad = [v for v in live_in if not v[0].startswith(("v", "x"))]
    if bad:
        raise TranslateError("寄存器在写入前被读取: %s" % sorted(bad)[:6])
    lines = []
    if decl["temps"]:
        lines.append("    uint4 %s;" % ", ".join("%sr%d = (uint4)0" % (prefix, k) for k in range(decl["temps"])))
    for k, n in decl["x"].items():
        lines.append("    uint4 %sx%d[%d] = (uint4[%d])0;" % (prefix, k, n, n))
    if decl["icb"]:
        rows = ["uint4(%s)" % ", ".join(lit_comp(v, "u") for v in r) for r in decl["icb"]]
        lines.append("    const uint4 %sicb[%d] = { %s };" % (prefix, len(rows), ", ".join(rows)))
    for arr, rows in ctx.dyn_arrays.items():
        lines.append("    const float4 %s[%d] = { %s };" % (arr, len(rows), ", ".join(rows)))
    outs = sorted(decl["outputs"])
    if outs:
        lines.append("    uint4 %s;" % ", ".join("%so%d = (uint4)0" % (prefix, k) for k in outs))
    lines += emit(kept)
    return {"code": "\n".join(lines), "live_inputs": sorted(v for v in live_in if v[0].startswith("v")), "mat_params": ctx.mat_params,
            "textures": list(ctx.textures), "globals": list(ctx.globals_used), "outputs": outs,
            "missing": list(ctx.missing)}
