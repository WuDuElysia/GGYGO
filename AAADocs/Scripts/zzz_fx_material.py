"""Unity 粒子/特效材质 → UE 材质方案（离线，不依赖 UE）。

    plan(材质 JSON, 渲染器信息):
        shader = 材质关键字对应的变体反汇编（zzz_shader_variants）
        pass   = 第一个未被材质关闭、LightMode 属于颜色 Pass 的 Pass
        ps     = translate(pass.fp, 需要 o0)
        vs     = translate(pass.vp, 需要 PS 实际读取的插值)
        code   = 前导（Unity 空间约定、采样函数）+ VS 输入装配（按渲染器顶点流）+ vs + 插值连接 + ps
        blend  = 按 Pass 的 Blend [_SrcFactor] [_DstFactor] 与材质取值映射到 UE 混合模式
        参数   = 材质里被保留代码读到的属性：Color 走 Unity 线性化，Vector/Float 原值，贴图按 PathID 找 UE 资产

同一份 code（shader 变体 + Pass + 顶点流布局 + 网格 UV 层数）只生成一个 master 材质，Unity 材质各自一个 MI。
"""
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zzz_dxbc_hlsl as T  # noqa: E402
import zzz_shader_variants as V  # noqa: E402
from pyrios_material_plan import unity_color_to_linear  # noqa: E402

GLOBALS_PATH = HERE.parent / "Assets/Shared/FX/ZZZ_FX_Globals.json"
# 颜色 Pass 按优先级排列。miHoYo 管线的全分辨率与半分辨率透明 Pass 是同一效果的两种画法，
# 运行时只选其一；两者都可用时取全分辨率。
COLOR_PASSES = ("TransparentFullRes", "Forward", "TransparentHalfRes", "ForwardHalfRes", "UniversalForward",
                "SRPDefaultUnlit", "CharacterToonDeferred")

# Unity BlendMode 枚举
BLEND_NAMES = {0: "Zero", 1: "One", 2: "DstColor", 3: "SrcColor", 4: "OneMinusDstColor", 5: "SrcAlpha",
               6: "OneMinusSrcColor", 7: "DstAlpha", 8: "OneMinusDstAlpha", 9: "SrcAlphaSaturate", 10: "OneMinusSrcAlpha"}
# (Src, Dst) → (UE BlendMode, 输出约定)
#   AlphaComposite：最终 = Src.rgb + Dst*(1-Opacity)，shader 输出的 rgb 已经乘过 alpha
#   Translucent：  最终 = Src.rgb*Opacity + Dst*(1-Opacity)
#   Additive：     最终 = Src.rgb + Dst
BLEND_MAP = {("One", "OneMinusSrcAlpha"): ("BLEND_AlphaComposite", "rgb"),
             ("SrcAlpha", "OneMinusSrcAlpha"): ("BLEND_Translucent", "rgb"),
             ("One", "One"): ("BLEND_Additive", "rgb"),
             ("SrcAlpha", "One"): ("BLEND_Additive", "rgb*a"),
             ("DstColor", "Zero"): ("BLEND_Modulate", "rgb")}

# Unity ParticleSystemVertexStream：编号 → (名字, 分量数)
STREAMS = {0: ("Position", 3), 1: ("Normal", 3), 2: ("Tangent", 4), 3: ("Color", 4), 4: ("UV", 2), 5: ("UV2", 2),
           6: ("UV3", 2), 7: ("UV4", 2), 8: ("AnimBlend", 1), 9: ("AnimFrame", 1), 10: ("Center", 3),
           11: ("VertexID", 1), 12: ("SizeX", 1), 13: ("SizeXY", 2), 14: ("SizeXYZ", 3), 15: ("Rotation", 1),
           16: ("Rotation3D", 3), 17: ("RotationSpeed", 1), 18: ("RotationSpeed3D", 3), 19: ("Velocity", 3),
           20: ("Speed", 1), 21: ("AgePercent", 1), 22: ("InvStartLifetime", 1),
           23: ("StableRandomX", 1), 24: ("StableRandomXY", 2), 25: ("StableRandomXYZ", 3), 26: ("StableRandomXYZW", 4),
           27: ("VaryingRandomX", 1), 28: ("VaryingRandomXY", 2), 29: ("VaryingRandomXYZ", 3), 30: ("VaryingRandomXYZW", 4),
           31: ("Custom1X", 1), 32: ("Custom1XY", 2), 33: ("Custom1XYZ", 3), 34: ("Custom1XYZW", 4),
           35: ("Custom2X", 1), 36: ("Custom2XY", 2), 37: ("Custom2XYZ", 3), 38: ("Custom2XYZW", 4)}
DEFAULT_PARTICLE_STREAMS = [0, 1, 3, 4]  # 未开自定义顶点流时 Unity 的默认：Position, Normal, Color, UV


class PlanError(Exception):
    pass


# ---------------------------------------------------------------- 顶点输入装配

def pack_streams(streams):
    """按 Unity 规则把顶点流排进 VS 输入语义。返回 {(语义, 下标): [ (流名, 流内分量) 或 None ]*4}。
    Position/Normal/Tangent/Color 占固定语义，其余依次挤进 TEXCOORD0.. 的分量，可跨寄存器。"""
    slots = {}
    fixed = {"Position": "POSITION", "Normal": "NORMAL", "Tangent": "TANGENT", "Color": "COLOR"}
    flat = []
    for s in streams:
        if s not in STREAMS:
            raise PlanError("未知顶点流编号 %d" % s)
        name, n = STREAMS[s]
        if name in fixed:
            slots[(fixed[name], 0)] = [(name, k) for k in range(n)] + [None] * (4 - n)
        else:
            flat += [(name, k) for k in range(n)]
    for i in range(0, len(flat), 4):
        chunk = flat[i:i + 4]
        slots[("TEXCOORD", i // 4)] = chunk + [None] * (4 - len(chunk))
    return slots


def stream_component(name, k, ctx):
    """Unity 顶点流某分量对应的 Custom 节点表达式（Unity 空间约定）。ctx 记录用到的内置输入与动态参数槽。"""
    use = ctx["builtins"]
    if name == "Position":
        use.update(["WorldPos"])
        return "PosU.%s" % "xyz"[k]
    if name == "Normal":
        use.update(["NrmW"])
        return "F.U(normalize(NrmW)).%s" % "xyz"[k]
    if name == "Color":
        use.add("PCol")
        if ctx["mesh"]:
            use.add("VCol")
            return "(PCol * VCol).%s" % "xyzw"[k]
        return "PCol.%s" % "xyzw"[k]
    if name in ("UV", "UV2", "UV3", "UV4"):
        ch = {"UV": 0, "UV2": 1, "UV3": 2, "UV4": 3}[name]
        if ch > 0 and not ctx["mesh"]:
            raise PlanError("公告板粒子的 %s 流（序列帧下一帧 UV）未实现" % name)
        if ch >= ctx["uv_count"]:
            return "0.0"  # Unity 对网格缺失的 UV 层送 0
        use.add("UV%d" % ch)
        return "UV%d.x" % ch if k == 0 else "(1.0 - UV%d.y)" % ch
    if name == "Center":
        use.add("PPos")
        return "(F.U(PPos) * 0.01).%s" % "xyz"[k]
    if name == "AgePercent":
        use.add("PAge")
        return "PAge"
    if name.startswith("StableRandom"):
        ctx["dyn"][2] = "StableRandomXYZW"
        use.add("DP2")
        return "DP2.%s" % "xyzw"[k]
    if name.startswith("Custom1"):
        ctx["dyn"][0] = "Custom1"
        use.add("DP0")
        return "DP0.%s" % "xyzw"[k]
    if name.startswith("Custom2"):
        ctx["dyn"][1] = "Custom2"
        use.add("DP1")
        return "DP1.%s" % "xyzw"[k]
    if name.startswith("Size"):
        ctx["dyn"][3] = "SizeXYZ_InvLifetime"
        use.add("DP3")
        return "DP3.%s" % "xyz"[k]
    if name == "InvStartLifetime":
        ctx["dyn"][3] = "SizeXYZ_InvLifetime"
        use.add("DP3")
        return "DP3.w"
    raise PlanError("顶点流 %s 未实现" % name)


def vs_inputs(vp, live, renderer, ctx):
    """按 VS 输入签名生成 av# 赋值；只装配活跃分量，其余置 0。"""
    if renderer["kind"] == "particle":
        streams = renderer["streams"] if renderer["custom_streams"] else DEFAULT_PARTICLE_STREAMS
        slots = pack_streams(streams)
    else:
        slots = {("POSITION", 0): [("Position", k) for k in range(3)] + [None],
                 ("NORMAL", 0): [("Normal", k) for k in range(3)] + [None],
                 ("COLOR", 0): [("Color", k) for k in range(4)]}
        for ch in range(4):
            slots[("TEXCOORD", ch)] = [("UV%s" % ("" if ch == 0 else ch + 1), 0), ("UV%s" % ("" if ch == 0 else ch + 1), 1), None, None]
    lines = []
    live_comps = {}
    for v, c in live:
        live_comps.setdefault(int(v[1:]), set()).add(c)
    for row in vp["in"]:
        comps = live_comps.get(row["reg"])
        if not comps:
            continue
        src = slots.get((row["name"], row["index"]))
        exprs = []
        for k, c in enumerate("xyzw"):
            if c not in comps:
                exprs.append("0.0")
                continue
            if src is None or src[k] is None:
                if row["name"] == "POSITION" and k == 3:
                    exprs.append("1.0")
                    continue
                # 渲染器没开这条顶点流时 Unity 给 shader 的是 0（D3D 未绑定的输入），照此装配并记入警告
                ctx["warnings"].append("VS 读取 %s%d.%s，渲染器顶点流未提供，按 Unity 行为取 0" % (row["name"], row["index"], c))
                exprs.append("0.0")
                continue
            exprs.append(stream_component(src[k][0], src[k][1], ctx))
        lines.append("    uint4 av%d = asuint(float4(%s));" % (row["reg"], ", ".join(exprs)))
    return lines


# ---------------------------------------------------------------- 前导代码与方案

PRELUDE = r"""// 由 zzz_fx_material.py 生成，勿手改。Shader：%(shader)s，Pass：%(pass)s，关键字：%(keywords)s
// 运算在 Unity 约定下进行：Y 轴向上、长度单位米；F.U() 把 UE 向量换到该约定（交换 Y/Z）。
// 寄存器按位存放（uint4），与 D3D 反汇编一一对应，比较结果是 0xFFFFFFFF 掩码。
struct ZF
{
    float3 U(float3 v) { return float3(v.x, v.z, v.y); }
    // Unity UV（V 向上）→ UE 贴图（V 向下）。寻址模式来自贴图资产，已按 Unity 导入设置配置。
    float4 S(Texture2D Tex, SamplerState Smp, float2 uv) { return Texture2DSample(Tex, Smp, float2(uv.x, 1.0 - uv.y)); }
    float4 SL(Texture2D Tex, SamplerState Smp, float2 uv, float lod) { return Texture2DSampleLevel(Tex, Smp, float2(uv.x, 1.0 - uv.y), lod); }
    float4 SB(Texture2D Tex, SamplerState Smp, float2 uv, float b) { return Texture2DSampleBias(Tex, Smp, float2(uv.x, 1.0 - uv.y), b); }
};
ZF F;
float3 CamU = F.U(CamPos) * 0.01;
float3 CamRightU = F.U(normalize(View.ViewToTranslatedWorld[0].xyz));
float3 CamUpU = F.U(normalize(View.ViewToTranslatedWorld[1].xyz));
float3 CamFwdU = F.U(normalize(View.ViewToTranslatedWorld[2].xyz));
float2 ViewSize = View.ViewSizeAndInvSize.xy;
"""


def load_globals():
    data = json.loads(GLOBALS_PATH.read_text(encoding="utf-8"))
    prov = {}
    for name, g in data["globals"].items():
        prov[name] = {"rows": g["rows"], "comps": g.get("comps", "xyzw"), "disabled_by": g.get("disabled_by", {})}
    prov["__textures__"] = data.get("textures", {})
    return prov, data.get("builtins", {})


def blend_of(pass_, floats):
    line = next((s for s in pass_["state"] if s.startswith("Blend ") and not re.match(r"Blend [1-7] ", s)), None)
    if line is None:
        return ("One", "Zero")
    m = re.match(r"Blend (?:0 )?(\[?\w+\]?) (\[?\w+\]?)", line)

    def val(tok):
        if tok.startswith("["):
            prop = tok[1:-1]
            if prop not in floats:
                raise PlanError("混合因子属性 %s 不在材质里" % prop)
            return BLEND_NAMES[int(floats[prop])]
        return tok
    return (val(m.group(1)), val(m.group(2)))


def flag(floats, name, line):
    m = re.search(r"\b%s\s+\[(\w+)\]" % name, line)
    return floats.get(m.group(1)) if m else None


def material_value(name, dim, props, floats, colors, texenvs):
    """属性在 Unity 材质里的上传值（Color 已线性化）。"""
    if name.endswith("_ST"):
        env = texenvs.get(name[:-3])
        if env is None:
            raise PlanError("缺少贴图属性 %s（%s 需要它的 Tiling/Offset）" % (name[:-3], name))
        return [env["m_Scale"]["X"], env["m_Scale"]["Y"], env["m_Offset"]["X"], env["m_Offset"]["Y"]]
    if name in colors:
        c = colors[name]
        rgba = [c["r"], c["g"], c["b"], c["a"]]
        info = props.get(name)
        if info is None:
            raise PlanError("属性 %s 不在 Shader Properties 里，无法判断是否需要线性化" % name)
        if info["type"] == "Color" and "[Gamma]" not in info["attrs"]:
            rgba = list(unity_color_to_linear(rgba[:3])) + [rgba[3]]
        return rgba
    if name in floats:
        if dim != 1:
            raise PlanError("属性 %s 在材质里是 Float，shader 按 %d 分量读取" % (name, dim))
        return floats[name]
    # 材质创建后 shader 新增的属性不会写进材质，Unity 上传的是 Properties 里的默认值
    info = props.get(name)
    if info is None or info["default"] is None:
        raise PlanError("材质缺少属性 %s，shader Properties 里也没有默认值" % name)
    d = info["default"]
    if isinstance(d, list):
        if info["type"] == "Color" and "[Gamma]" not in info["attrs"]:
            d = list(unity_color_to_linear(d[:3])) + [d[3]]
        return d
    if dim != 1:
        raise PlanError("属性 %s 默认值是标量，shader 按 %d 分量读取" % (name, dim))
    return d


def pick_pass(shader, material):
    disabled = set(material.get("m_DisabledShaderPasses") or [])
    for mode in COLOR_PASSES:
        for p in shader["passes"]:
            if p["lightmode"] == mode and mode not in disabled and p["vp"] and p["fp"]:
                return p
    raise PlanError("没有可用的颜色 Pass（关闭的：%s；现有：%s）"
                    % (sorted(disabled), [p["lightmode"] for p in shader["passes"]]))


def plan(material_path, renderer, tex_assets):
    """renderer: {"kind": "particle"/"mesh", "streams": [...], "custom_streams": bool, "mesh": bool, "uv_count": n}
    tex_assets: Unity 贴图 PathID(str) → UE 资产路径。"""
    mat = json.load(open(material_path, encoding="utf-8"))
    shader_name, keywords, shader_file = V.export_variant(material_path)
    shader = T.parse_shader(Path(shader_file).read_text(encoding="utf-8", errors="replace"))
    p = pick_pass(shader, mat)
    sp = mat["m_SavedProperties"]
    floats, colors, texenvs = sp["m_Floats"], sp["m_Colors"], sp["m_TexEnvs"]
    provider, builtin_docs = load_globals()

    ps = T.translate(p["fp"], "b", provider, {0: "xyzw"})
    need = {}
    ps_special = []
    for row in p["fp"]["in"]:
        used = {c for v, c in ps["live_inputs"] if v == "v%d" % row["reg"]}
        if not used:
            continue
        if row["name"] == "SV_POSITION":
            ps_special.append("    uint4 bv%d = asuint(float4(Parameters.SvPosition.xy - View.ViewRectMin.xy, "
                              "1.0 / (PixelDepth * 0.01), 1.0));" % row["reg"])
            continue
        if row["name"] == "SV_IsFrontFace":
            ps_special.append("    uint4 bv%d = uint4(FaceSign > 0.0 ? 0xFFFFFFFFu : 0u, 0u, 0u, 0u);" % row["reg"])
            continue
        if row["sys"] != "NONE":
            raise PlanError("PS 读取系统值 %s，未实现" % row["name"])
        vo = next((r for r in p["vp"]["out"] if r["name"] == row["name"] and r["index"] == row["index"]), None)
        if vo is None:
            raise PlanError("PS 输入 %s%d 在 VS 输出里找不到" % (row["name"], row["index"]))
        need.setdefault(vo["reg"], (set(), row["reg"]))[0].update(used)
    vs = T.translate(p["vp"], "a", provider, {k: "".join(sorted(v[0])) for k, v in need.items()})

    ctx = {"builtins": set(), "dyn": {}, "mesh": renderer.get("mesh", False), "uv_count": renderer.get("uv_count", 1),
           "warnings": []}
    av = vs_inputs(p["vp"], vs["live_inputs"], renderer, ctx)
    link = ["    uint4 bv%d = ao%d;" % (preg, vreg) for vreg, (_, preg) in sorted(need.items())]

    # 全局量的"无效果"取值只在材质关闭对应开关时成立
    for name, _, _ in ps["globals"] + vs["globals"]:
        for prop, required in provider[name]["disabled_by"].items():
            if floats.get(prop) != required:
                raise PlanError("全局量 %s 取无效果值的前提是 %s=%s，材质里是 %r" % (name, prop, required, floats.get(prop)))

    src, dst = blend_of(p, floats)
    if (src, dst) not in BLEND_MAP:
        raise PlanError("混合 %s %s 没有对应的 UE 混合模式" % (src, dst))
    blend, out_conv = BLEND_MAP[(src, dst)]
    cull = flag(floats, "Cull", " ".join(p["state"]))
    zwrite = flag(floats, "ZWrite", " ".join(p["state"]))
    ztest = flag(floats, "ZTest", " ".join(p["state"]))
    if zwrite not in (None, 0.0):
        raise PlanError("ZWrite=%r 的半透明特效未实现" % zwrite)
    if ztest not in (None, 4.0, 8.0, 0.0):
        raise PlanError("ZTest=%r 未实现（只支持 LEqual / Always）" % ztest)

    mat_params = dict(ps["mat_params"])
    mat_params.update(vs["mat_params"])
    textures = list(dict.fromkeys(ps["textures"] + vs["textures"]))
    builtins = set(ctx["builtins"]) | {"CamPos", "Time"}
    if any(l.startswith("    uint4 bv") and "PixelDepth" in l for l in ps_special):
        builtins.add("PixelDepth")
    if any("FaceSign" in l for l in ps_special):
        builtins.add("FaceSign")
    if "WorldPos" in builtins:
        pre_pos = "float3 PosU = F.U(WorldPos) * 0.01;\n"
    else:
        pre_pos = ""
    body = (PRELUDE % {"shader": shader_name, "pass": p["name"], "keywords": " ".join(keywords) or "无"}
            + pre_pos + "\n".join(av) + "\n" + vs["code"] + "\n" + "\n".join(link + ps_special) + "\n"
            + ps["code"] + "\n    float4 c = asfloat(bo0);\n"
            + ("    return float4(c.rgb * c.a, c.a);\n" if out_conv == "rgb*a" else "    return c;\n"))
    # Custom 节点函数体里不需要缩进；去掉 4 空格前缀便于阅读
    body = "\n".join(l[4:] if l.startswith("    ") else l for l in body.split("\n"))

    params = {}
    for name, dim in mat_params.items():
        params[name] = {"dim": dim, "value": material_value(name, dim, shader["props"], floats, colors, texenvs)}
    tex_params = {}
    for name in textures:
        env = texenvs.get(name)
        if env is None:
            raise PlanError("shader 采样 %s，材质里没有该贴图属性" % name)
        if env["m_Texture"]["IsNull"]:
            default = (shader["props"].get(name) or {}).get("tex_default")
            raise PlanError("贴图 %s 为空（shader 默认 %r），默认贴图未实现" % (name, default))
        pid = str(env["m_Texture"]["m_PathID"])
        if pid not in tex_assets:
            raise PlanError("贴图 %s（PathID %s）没有导入到 UE" % (name, pid))
        tex_params[name] = tex_assets[pid]

    key_src = json.dumps({"code": body, "params": sorted(params), "tex": sorted(tex_params), "blend": blend,
                          "two_sided": cull == 0.0, "builtins": sorted(builtins)}, sort_keys=True)
    key = hashlib.md5(key_src.encode()).hexdigest()[:8]
    short = shader_name.split("/")[-1].replace(" ", "")
    return {
        "material": mat["m_Name"], "shader": shader_name, "keywords": keywords, "pass": p["name"],
        "master": "M_ZZZFX_%s_%s" % (short, key), "code": body, "blend": blend,
        "two_sided": cull == 0.0, "builtins": sorted(builtins), "dyn_params": ctx["dyn"],
        "params": params, "textures": tex_params,
        "disabled_passes": mat.get("m_DisabledShaderPasses") or [], "warnings": ctx["warnings"],
        "skipped_passes": [q["lightmode"] for q in shader["passes"]
                           if q is not p and q["lightmode"] not in (mat.get("m_DisabledShaderPasses") or [])],
    }
