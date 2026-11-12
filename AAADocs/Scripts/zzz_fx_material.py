"""@file zzz_fx_material.py @brief Unity 粒子/特效材质到 UE 材质方案（离线，不依赖 UE）。

    plan(材质 JSON, 渲染器信息):
        shader = 材质关键字对应的变体反汇编（zzz_shader_variants）
        pass   = 第一个未被材质关闭、LightMode 属于颜色 Pass 的 Pass
        ps     = translate(pass.fp, 需要 o0)
        vs     = translate(pass.vp, 需要 PS 实际读取的插值)
        code   = 前导（Unity 空间约定、采样函数）+ VS 输入装配（按渲染器顶点流）+ vs + 插值连接 + ps
        blend  = 按 Pass 的 Blend [_SrcFactor] [_DstFactor] 与材质取值映射到 UE 混合模式
        参数   = 材质里被保留代码读到的属性：Color 走 Unity 线性化，Vector/Float 原值，贴图按 PathID 找 UE 资产
        生成带 = 明确 UE 输入合同喂原 VS，原插值传 PS；Native Ribbon 提供几何，时钟沿用同一 NS

同一份 code（shader 变体 + Pass + 顶点流布局 + 网格 UV 层数）只生成一个 master 材质，Unity 材质各自一个 MI。
"""
from copy import deepcopy
import math
import hashlib
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import zzz_dxbc_hlsl as T  # noqa: E402
import zzz_shader_variants as V  # noqa: E402
import zzz_fx_particle_uv as PU  # noqa: E402
import zzz_fx_particle_renderer as PR  # noqa: E402
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


def dynamic_component(ctx, slot, component, role):
    """每次材质翻译独占的派生掩码，不从首批或整个 slot 推断分量。"""
    previous = ctx["dyn"].get(slot)
    if previous is not None and previous != role:
        raise PlanError("Dynamic parameter role conflict: " + str(slot))
    ctx["dyn"][slot] = role
    ctx["dynamic_parameter_components"] |= 1 << (slot * 4 + component)


def stream_component(name, k, ctx):
    """Unity 顶点流某分量对应的 Custom 节点表达式（Unity 空间约定）。ctx 记录用到的内置输入与动态参数槽。"""
    use = ctx["builtins"]
    if name == "Position":
        use.update(["WorldPos"])
        return "PosU.%s" % "xyz"[k]
    if name == "Normal":
        if not ctx["mesh"]:
            direction = ctx.get("sprite_normal_direction")
            if direction == 1:
                use.update(["CamPos", "PPos"])
                return "F.U(normalize(CamPos - PPos)).%s" % "xyz"[k]
            if direction != 0:
                raise PlanError("公告板 Normal 流需要明确的源 NormalDirection=0/1 契约")
        use.update(["NrmW"])
        return "F.U(normalize(NrmW)).%s" % "xyz"[k]
    if name == "Color":
        if ctx["renderer_kind"] == "mesh":
            use.add("VCol")
            return "VCol.%s" % "xyzw"[k]
        use.add("PCol")
        if ctx["mesh"]:
            use.add("VCol")
            return "(PCol * VCol).%s" % "xyzw"[k]
        return "PCol.%s" % "xyzw"[k]
    if name in ("UV", "UV2", "UV3", "UV4"):
        ch = {"UV": 0, "UV2": 1, "UV3": 2, "UV4": 3}[name]
        if not ctx["mesh"] and ctx.get("sprite_subuv") and ch in (0, 1):
            use.update(["UV0", "AtlasFrame"])
            return PU.stream_component(name, k, ctx["sprite_uv_tiles"], animation_type=ctx.get("sprite_uv_animation_type", 0))
        if not ctx["mesh"] and (ctx.get("sprite_static_quad_uv") or (ch >= 2 and ctx.get("sprite_extra_quad_uv"))):
            # Explicit UE billboard environment with source sheet animation off:
            # every declared static UV channel uses the unanimated quad.
            use.add("UV0")
            return "UV0.x" if k == 0 else "(1.0 - UV0.y)"
        if ch > 0 and not ctx["mesh"]:
            raise PlanError("公告板粒子的 %s 流需要明确的源 UV 通道契约" % name)
        if ch >= ctx["uv_count"]:
            return "0.0"  # Unity 对网格缺失的 UV 层送 0
        mesh_uv = (ctx.get("mesh_uv") or {}).get("contract")
        if ctx["mesh"] and mesh_uv and mesh_uv["animated"] and mesh_uv["uv_channel_mask"] & (1 << ch):
            use.update(["UV%d" % ch, "AtlasFrame"])
            return PU.stream_component("UV", k, mesh_uv["tiles"], animation_type=mesh_uv.get("animation_type", 0)).replace(
                "UV0.", "UV%d." % ch)
        use.add("UV%d" % ch)
        return "UV%d.x" % ch if k == 0 else "(1.0 - UV%d.y)" % ch
    if name == "AnimBlend" and not ctx["mesh"] and ctx.get("sprite_subuv"):
        use.add("AtlasFrame")
        return PU.stream_component(name, k, ctx["sprite_uv_tiles"], animation_type=ctx.get("sprite_uv_animation_type", 0))
    if name == "AnimBlend" and ctx["mesh"] and (ctx.get("mesh_uv") or {}).get("contract", {}).get("animated"):
        use.add("AtlasFrame")
        return "frac(AtlasFrame)"
    if name == "AnimBlend" and ctx["mesh"] and (ctx.get("mesh_uv") or {}).get("contract", {}).get("animated") is False:
        return "0.0"  # 原UVModule明确关闭；不创建帧动画或消费AtlasFrame。
    if name in ("Rotation", "Rotation3D") and not ctx["mesh"] and ctx.get("sprite_rotation_2d"):
        if name == "Rotation3D" and k < 2:
            return "0.0"
        use.add("PRot")
        return "(-PRot)"  # native sprite material value is radians, in UV-down basis
    if name == "Center":
        use.add("PPos")
        return "(F.U(PPos) * 0.01).%s" % "xyz"[k]
    if name == "AgePercent":
        use.add("PAge")
        return "PAge"
    if name.startswith("StableRandom"):
        dynamic_component(ctx, 2, k, "StableRandomXYZW")
        use.add("DP2")
        return "DP2.%s" % "xyzw"[k]
    if name.startswith("Custom1"):
        dynamic_component(ctx, 0, k, "Custom1")
        use.add("DP0")
        return "DP0.%s" % "xyzw"[k]
    if name.startswith("Custom2"):
        dynamic_component(ctx, 1, k, "Custom2")
        use.add("DP1")
        return "DP1.%s" % "xyzw"[k]
    if name.startswith("Size"):
        dynamic_component(ctx, 3, k, "SizeXYZ_InvLifetime")
        use.add("DP3")
        return "DP3.%s" % "xyz"[k]
    if name == "InvStartLifetime":
        dynamic_component(ctx, 3, 3, "SizeXYZ_InvLifetime")
        use.add("DP3")
        return "DP3.w"
    raise PlanError("顶点流 %s 未实现" % name)


def generated_ribbon_contract(renderer):
    """校验明确 UE 生成的 Ribbon 材质接缝；该合同不代表恢复了 Unity 生成器。"""
    value = renderer.get("generated_ribbon")
    if renderer.get("kind") != "generated_ribbon":
        if value is not None:
            raise PlanError("Generated Ribbon 输入不能挂到其它 renderer")
        return None
    if renderer.get("mesh") is not False or "uv_count" in renderer or any(renderer.get(key) is not None for key in (
            "component_age_binding", "mesh_affine", "mesh_uv", "viewport_clamp", "sprite_geometry")):
        raise PlanError("Generated Ribbon 不能借静态 Mesh／Sprite 的 UV、年龄或二次变换")
    value = _fields(value, ("schema", "uv_convention", "raw_uv6", "system_age"), "generated_ribbon")
    if value["schema"] != "GGYGO.GeneratedRibbonMaterial/v1" or value["uv_convention"] != "NativeUVToUnityUVDown":
        raise PlanError("Generated Ribbon 材质输入版本或 UV 约定无效")
    raw = _fields(value["raw_uv6"], ("z_attribute", "w_attribute"), "generated_ribbon.raw_uv6")
    if any(not isinstance(name, str) or not name.startswith("Particles.") or len(name) <= len("Particles.") or name in (
            "Particles.Age", "Particles.Lifetime", "Particles.NormalizedAge") for name in raw.values()) \
            or len(set(raw.values())) != 2:
        raise PlanError("Raw TC6 必须有独立的两个 float 属性，不改写真实生命周期")
    if value["system_age"] != {"parameter": "UEFX_GeneratedRibbonSystemAge", "source": "System.Age"}:
        raise PlanError("Generated Ribbon 必须消费同一 NS 的真实 System.Age 参数")
    return deepcopy(value)


def source_trail_length_color_contract(renderer):
    """@brief 校验源拖尾长度色；返回完整独立副本，未配置时返回 None。

    @param renderer Native Ribbon 输入及显式方向、UV0 缩放和原 MinMaxGradient。
    @return 仅接本批线性白到黑且 Alpha 恒一的源渐变，不拥有粒子年龄或历史。
    """
    value = renderer.get("source_trail_length_color")
    if value is None:
        return None
    if renderer.get("kind") != "generated_ribbon" or generated_ribbon_contract(renderer) is None:
        raise PlanError("源拖尾长度色需要完整 Generated Ribbon 输入")
    value = _fields(value, ("schema", "gradient", "native_u_scale", "native_u_offset", "direction"),
                    "source_trail_length_color")
    if value["schema"] != "GGYGO.SourceTrailLengthColor/v1" or value["direction"] not in ("Forward", "Reverse"):
        raise PlanError("源拖尾长度色缺明确版本或方向")
    if _number(value["native_u_scale"], "native_u_scale") == 0.0:
        raise PlanError("源拖尾长度色不能从零缩放 UV0 恢复弧长坐标")
    _number(value["native_u_offset"], "native_u_offset")
    gradient = _fields(value["gradient"], ("minMaxState", "minColor", "maxColor", "maxGradient", "minGradient"),
                       "source_trail_length_color.gradient")
    if type(gradient["minMaxState"]) is not int or gradient["minMaxState"] != 1 \
            or not isinstance(gradient["minGradient"], dict):
        raise PlanError("源拖尾长度色仅支持完整单 Gradient 模式")
    fields = [prefix + str(i) for prefix in ("key", "ctime", "atime") for i in range(8)]
    ramp = _fields(gradient["maxGradient"], fields + ["m_Mode", "m_NumColorKeys", "m_NumAlphaKeys"],
                   "source_trail_length_color.gradient.maxGradient")
    if any(type(ramp[name]) is not int or ramp[name] != expected for name, expected in
           (("m_Mode", 0), ("m_NumColorKeys", 2), ("m_NumAlphaKeys", 2),
            ("ctime0", 0), ("ctime1", 65535), ("atime0", 0), ("atime1", 65535))):
        raise PlanError("源拖尾长度色需要两端完整线性颜色及 Alpha key")
    for name in ("minColor", "maxColor"):
        color = _fields(gradient[name], "rgba", "gradient." + name)
        for axis in "rgba":
            _number(color[axis], "gradient." + name + "." + axis)
    for i in range(8):
        color = _fields(ramp["key" + str(i)], "rgba", "gradient.key" + str(i))
        for axis in "rgba":
            _number(color[axis], "gradient.key" + str(i) + "." + axis)
    if ramp["key0"] != dict(r=1.0, g=1.0, b=1.0, a=1.0) \
            or ramp["key1"] != dict(r=0.0, g=0.0, b=0.0, a=1.0):
        raise PlanError("源拖尾长度色尚未支持此白黑／Alpha 组合")
    return deepcopy(value)


def generated_ribbon_vs_inputs(vp, live, ctx, length_color=None):
    """将原 Shader 输入格子映到 Native Ribbon 实际通道，活跃未映射分量直接拒绝。"""
    slots = {
        ("POSITION", 0): ["PosU.x", "PosU.y", "PosU.z", "1.0"],
        ("COLOR", 0): ["PCol." + axis for axis in "xyzw"],
        ("TEXCOORD", 0): ["UV0.x", "(1.0 - UV0.y)", "UV1.x", "(1.0 - UV1.y)"],
        ("TEXCOORD", 6): [None, None, "RawTC6Z", "RawTC6W"],
    }
    ctx["builtins"].update({"WorldPos", "PCol", "UV0", "UV1", "RawTC6Z", "RawTC6W"})
    for slot in range(4):
        ctx["builtins"].add("DP%d" % slot)
        slots[("TEXCOORD", slot + 1)] = ["DP%d.%s" % (slot, axis) for axis in "xyzw"]
        for component in range(4):
            dynamic_component(ctx, slot, component, "GeneratedTC%d" % (slot + 1))
    lines = []
    if length_color is not None:
        scale, offset = (format(length_color[name], ".17g") for name in ("native_u_scale", "native_u_offset"))
        coordinate = "saturate((UV0.x - (%s)) / (%s))" % (offset, scale)
        if length_color["direction"] == "Reverse":
            coordinate = "(1.0 - %s)" % coordinate
        # Native UV 已按当前 Ribbon 总弧长归一；先去配置缩放，再在源 VS 前乘继承色一次。
        lines += ["    float UEFX_TrailLengthT = %s;" % coordinate,
                  "    float4 UEFX_TrailLengthColor = float4(1.0 - UEFX_TrailLengthT, 1.0 - UEFX_TrailLengthT, 1.0 - UEFX_TrailLengthT, 1.0);"]
        slots[("COLOR", 0)] = ["(PCol.%s * UEFX_TrailLengthColor.%s)" % (axis, axis) for axis in "xyzw"]
    inputs = {}
    for register, component in live:
        inputs.setdefault(int(register[1:]), set()).add(component)
    for row in vp["in"]:
        components = inputs.pop(row["reg"], set())
        if not components:
            continue
        values = slots.get((row["name"], row["index"]))
        if values is None or any(axis not in "xyzw" or values["xyzw".index(axis)] is None for axis in components):
            raise PlanError("Generated Ribbon 未映射原活跃输入 %s%d.%s" % (
                row["name"], row["index"], "".join(sorted(components))))
        values = [values[index] if axis in components else "0.0" for index, axis in enumerate("xyzw")]
        if row["name"] == "TEXCOORD" and 1 <= row["index"] <= 4:
            for component in components:
                ctx.setdefault("native_payload_bindings", {})[("v%d" % row["reg"], component)] = {
                    "builtin": "DP%d" % (row["index"] - 1), "component": component}
        lines.append("    uint4 av%d = asuint(float4(%s));" % (row["reg"], ", ".join(values)))
    if inputs:
        raise PlanError("Generated Ribbon 缺原活跃输入声明")
    return lines


def vs_inputs(vp, live, renderer, ctx):
    """按 VS 输入签名生成 av# 赋值；只装配活跃分量，其余置 0。"""
    if renderer["kind"] == "generated_ribbon":
        return generated_ribbon_vs_inputs(vp, live, ctx, source_trail_length_color_contract(renderer))
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
// 运算在 Unity 约定下进行：Y 轴向上、长度单位米；F.U() 与导入的 (-X,Z,Y) 轴换算互逆。
// 寄存器按位存放（uint4），与 D3D 反汇编一一对应，比较结果是 0xFFFFFFFF 掩码。
struct ZF
{
    float3 U(float3 v) { return float3(-v.x, v.z, v.y); }
    // Unity UV（V 向上）→ UE 贴图（V 向下）。寻址模式来自贴图资产，已按 Unity 导入设置配置。
    float4 S(Texture2D Tex, SamplerState Smp, float2 uv) { return Texture2DSample(Tex, Smp, float2(uv.x, 1.0 - uv.y)); }
    float4 L(Texture2D Tex, uint3 address) {
        uint width, height, levels;
        Tex.GetDimensions(0, width, height, levels);
        if (address.z >= levels) return float4(0,0,0,0);
        Tex.GetDimensions(address.z, width, height, levels);
        if (any(address.xy >= uint2(width, height))) return float4(0,0,0,0);
        return Tex.Load(int3(address.x, height - 1u - address.y, address.z));
    }
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


def _fields(value, keys, path):
    if not isinstance(value, dict) or set(value) != set(keys):
        raise PlanError(f"{path}: expected fields {sorted(keys)}")
    return value


def _number(value, path):
    if type(value) not in (int, float):
        raise PlanError(f"{path}: expected finite number")
    try:
        finite = math.isfinite(value)
    except OverflowError:
        finite = False
    if not finite:
        raise PlanError(f"{path}: expected finite number")
    return value


def _pointer(value, path):
    value = _fields(value, ("fileID", "pathID", "IsNull"), path)
    file_id, path_id, is_null = value["fileID"], value["pathID"], value["IsNull"]
    if type(file_id) is not int or not -(1 << 31) <= file_id < (1 << 31):
        raise PlanError(f"{path}.fileID: expected Int32")
    if (not isinstance(path_id, str) or len(path_id) > 20 or
            re.fullmatch(r"0|-?[1-9][0-9]*", path_id) is None):
        raise PlanError(f"{path}.pathID: expected canonical decimal Int64 string")
    if not -(1 << 63) <= int(path_id) < (1 << 63):
        raise PlanError(f"{path}.pathID: outside Int64")
    if type(is_null) is not bool or is_null != (file_id < 0 or int(path_id) == 0):
        raise PlanError(f"{path}.IsNull: inconsistent with Core pointer rule")
    # 不访问 Name，不解析外部引用；负 fileID 的合法空引用保留原指针。
    return {"m_FileID": file_id, "m_PathID": path_id, "IsNull": is_null}


def _vector2(value, path):
    value = _fields(value, ("x", "y"), path)
    return {axis.upper(): _number(value[axis], f"{path}.{axis}") for axis in ("x", "y")}


def _float(row, path):
    row = _fields(row, ("name", "value"), path)
    return _number(row["value"], f"{path}.value")


def _color(row, path):
    row = _fields(row, ("name", "value"), path)
    color = _fields(row["value"], ("r", "g", "b", "a"), f"{path}.value")
    return {axis: _number(color[axis], f"{path}.value.{axis}") for axis in ("r", "g", "b", "a")}


def _texture(row, path):
    row = _fields(row, ("name", "m_Texture", "m_Scale", "m_Offset"), path)
    return {"m_Texture": _pointer(row["m_Texture"], f"{path}.m_Texture"),
            "m_Scale": _vector2(row["m_Scale"], f"{path}.m_Scale"),
            "m_Offset": _vector2(row["m_Offset"], f"{path}.m_Offset")}


def _named(rows, path, decode):
    if not isinstance(rows, list):
        raise PlanError(f"{path}: expected v3 property array")
    values = {}
    for index, row in enumerate(rows):
        item_path = f"{path}[{index}]"
        if not isinstance(row, dict) or not isinstance(row.get("name"), str) or not row["name"]:
            raise PlanError(f"{item_path}.name: expected nonempty string")
        name = row["name"]
        if name in values:
            raise PlanError(f"{item_path}.name: duplicate {name!r}")
        values[name] = decode(row, item_path)
    return values


def adapt_v3_material(material):
    """转换已明确选出的 v3 字段；未知顶层字段保留，不猜 schema 或 Shader 名称。"""
    if not isinstance(material, dict):
        raise PlanError("material: expected object")
    for key in ("m_Shader", "m_SavedProperties"):
        if key not in material:
            raise PlanError(f"material.{key}: missing required field")
    saved = material["m_SavedProperties"]
    if not isinstance(saved, dict):
        raise PlanError("material.m_SavedProperties: expected object")
    output = deepcopy(material)
    output["m_Shader"] = _pointer(material["m_Shader"], "material.m_Shader")
    for key, decode in (("m_Floats", _float), ("m_Colors", _color), ("m_TexEnvs", _texture)):
        path = f"material.m_SavedProperties.{key}"
        if key not in saved:
            raise PlanError(f"{path}: missing required field")
        output["m_SavedProperties"][key] = _named(saved[key], path, decode)
    return output


def _dictionary_pointer(value, path):
    """Native 字典保 Int64 原值；IsNull 缺失时仅按已核 Core PPtr 规则派生。"""
    if not isinstance(value, dict) or not {"m_FileID", "m_PathID"} <= set(value):
        raise PlanError(f"{path}: expected native PPtr fields")
    file_id, path_id = value["m_FileID"], value["m_PathID"]
    if type(file_id) is not int or not -(1 << 31) <= file_id < (1 << 31):
        raise PlanError(f"{path}.m_FileID: expected Int32")
    if type(path_id) is int:
        exact_id = path_id
    elif isinstance(path_id, str) and len(path_id) <= 20 and re.fullmatch(r"0|-?[1-9][0-9]*", path_id):
        exact_id = int(path_id)
    else:
        raise PlanError(f"{path}.m_PathID: expected exact Int64 or canonical decimal string")
    if not -(1 << 63) <= exact_id < (1 << 63):
        raise PlanError(f"{path}.m_PathID: outside Int64")
    is_null = file_id < 0 or exact_id == 0
    if "IsNull" in value and (type(value["IsNull"]) is not bool or value["IsNull"] != is_null):
        raise PlanError(f"{path}.IsNull: inconsistent with Core pointer rule")
    return {**deepcopy(value), "IsNull": is_null}


def _dictionary_material(material):
    """统一已导出 Native／旧字典的 UV 大小写；不更改来源文件或补业务值。"""
    output = deepcopy(material)
    output["m_Shader"] = _dictionary_pointer(material["m_Shader"], "material.m_Shader")
    for name, env in material["m_SavedProperties"]["m_TexEnvs"].items():
        path = "material.m_SavedProperties.m_TexEnvs." + name
        if not isinstance(env, dict) or not {"m_Texture", "m_Scale", "m_Offset"} <= set(env):
            raise PlanError(f"{path}: missing native texture environment fields")
        target = output["m_SavedProperties"]["m_TexEnvs"][name]
        target["m_Texture"] = _dictionary_pointer(env["m_Texture"], path + ".m_Texture")
        for key in ("m_Scale", "m_Offset"):
            vector = env[key]
            if isinstance(vector, dict) and set(vector) == {"x", "y"}:
                target[key] = _vector2(vector, path + "." + key)
            else:
                _fields(vector, ("X", "Y"), path + "." + key)
                target[key] = {axis: _number(vector[axis], path + "." + key + "." + axis) for axis in ("X", "Y")}
    return output


def material_input(material):
    """归一化既有 Material 字段；不读取 Shader、纹理或其它依赖。"""
    if not isinstance(material, dict):
        raise PlanError("material: expected object")
    # 旧程序清单可以只消费 Shader 头；缺失属性组仍缺失，不补空字典。
    if "m_SavedProperties" not in material:
        return material
    saved = material["m_SavedProperties"]
    keys = ("m_Floats", "m_Colors", "m_TexEnvs")
    if not isinstance(saved, dict) or any(key not in saved for key in keys):
        raise PlanError("material.m_SavedProperties: missing required property groups")
    if all(isinstance(saved[key], dict) for key in keys):
        return _dictionary_material(material)
    if all(isinstance(saved[key], list) for key in keys):
        return adapt_v3_material(material)
    raise PlanError("material.m_SavedProperties: expected known dictionary groups or v3 arrays")



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


def plan(material_path, renderer, tex_assets, shader_name=None, output_contract="color", native_source=None,
         field_output_register=None):
    """renderer: particle／mesh 顶点流，或 generated_ribbon_contract 认证的明确生成带输入。
    tex_assets: Unity 贴图 PathID(str) → UE 资产路径。"""
    generated_ribbon = generated_ribbon_contract(renderer)
    length_color = source_trail_length_color_contract(renderer)
    if generated_ribbon is not None and (output_contract != "color" or native_source is None):
        raise PlanError("Generated Ribbon 需要真实 Native 原颜色程序")
    if output_contract == "distortion_field_pair":
        fields = [plan(material_path, renderer, tex_assets, shader_name, "distortion_field", native_source,
                       field_output_register=index) for index in (0, 1)]
        alignments = [(field.get("mesh_affine") or {}).get("project_alignment") for field in fields]
        if any(alignment is not None for alignment in alignments):
            if any(alignment is None for alignment in alignments):
                raise PlanError("Dual field geometry must share its complete Mesh frame")
            source_mask = 0
            for field,alignment in zip(fields,alignments):
                source_mask |= field["dynamic_parameter_components"] & 0x0FFF & ~alignment["required_components"]
            # 两输出共享同一原粒子数据集；按两路真实原字段并集选一次空闲运输，不能各自换槽。
            shared_renderer = {**renderer, "mesh_euler_source_components": source_mask}
            fields = [plan(material_path, shared_renderer, tex_assets, shader_name, "distortion_field", native_source,
                           field_output_register=index) for index in (0,1)]
        result = dict(fields[0])
        for key in ("params", "textures", "dyn_params"):
            combined = {}
            for field in fields:
                for name, value in field[key].items():
                    if name in combined and combined[name] != value:
                        raise PlanError("Dual field input conflicts: " + key + "/" + str(name))
                    combined[name] = value
            result[key] = combined
        result["builtins"] = sorted({v for field in fields for v in field["builtins"]})
        result["dynamic_parameter_components"] = fields[0]["dynamic_parameter_components"] | fields[1]["dynamic_parameter_components"]
        result["pixel_params"] = sorted({v for field in fields for v in field["pixel_params"]})
        result.update(output_contract="distortion_field_pair", fields={"DefaultField": fields[0], "OverlayField": fields[1]},
                      field_routing={"DefaultField": "source_o0", "OverlayField": "source_o1"})
        identity = json.dumps({"fields": fields}, sort_keys=True).encode("utf-8")
        result["master"] = "M_ZZZFX_ProjectConfigured_DualField_" + hashlib.sha256(identity).hexdigest()[:12]
        return result
    with open(material_path, encoding="utf-8-sig") as source:
        mat = material_input(json.load(source))
    # Planning must not invoke the exporter or overwrite a source export.
    shader_name = shader_name or mat["m_Shader"].get("Name")
    if not shader_name:
        raise PlanError("Shader name is missing; supply its resolved dependency name")
    keywords = sorted((mat.get("m_ShaderKeywords") or "").split())
    source_selection = None
    if native_source is not None:
        field_pair = output_contract == "distortion_field" and field_output_register in (0, 1) \
            and native_source["selection"].get("configuration_mode") == "ProjectConfigured"
        if output_contract != "color" and not field_pair:
            raise PlanError("Native source programs require the color output consumer; field/MRT needs its dedicated consumer")
        from zzz_fx_native_shader import select_native
        selection = dict(native_source["selection"])
        if selection.get("feature_off") is not None and Path(material_path).resolve() != Path(
                selection["feature_off"]["material_source"]).resolve():
            raise PlanError("FeatureOff is bound to another material source")
        if field_pair:
            selection["output_contract"] = "distortion_field_pair"
        shader, source_selection = select_native(native_source["shader_entry"], mat,
                                                  native_source["material_pid"], selection)
        shader_file = Path(source_selection["native_json"])
    else:
        variants = sorted(V.variant_dir(shader_name, keywords).glob("Shader/*.shader"))
        if len(variants) != 1:
            raise PlanError("Expected one existing shader variant for %s %s, found %d at %s"
                            % (shader_name, keywords, len(variants), V.variant_dir(shader_name, keywords)))
        shader_file = variants[0]
        shader = T.parse_shader(Path(shader_file).read_text(encoding="utf-8", errors="replace"))
    if output_contract == "distortion_field":
        if shader_name not in ("miHoYo/Particles/Distortion UVMove", "miHoYo/Particles/Distortion UVMove_Deprecated"):
            raise PlanError("Unverified distortion producer: " + shader_name)
        matches = [q for q in shader["passes"] if q["lightmode"] == "Distortion" and
                   q["lightmode"] not in (mat.get("m_DisabledShaderPasses") or [])]
        if len(matches) != 1:
            raise PlanError("Expected one enabled Distortion field pass")
        p = matches[0]
        mode = mat["m_SavedProperties"]["m_Floats"]["_DistortionMode"]
        if mode not in (0.0, 1.0):
            raise PlanError("Unknown original distortion mode: " + str(mode))
        output_register = int(mode) if field_output_register is None else field_output_register
        if output_register not in (0, 1):
            raise PlanError("Dual field routing requires source register 0/1")
    elif output_contract == "color":
        p = pick_pass(shader, mat)
        output_register = 0
    else:
        raise PlanError("Unknown shader output contract: " + output_contract)
    targets = [r for r in p["fp"]["out"] if r["name"] == "SV_Target"]
    if output_contract == "color" and any(r["index"] != 0 for r in targets):
        raise PlanError("%s/%s writes multiple render targets; its specific render output contract must be implemented"
                        % (shader_name, p["name"]))
    sp = mat["m_SavedProperties"]
    floats, colors, texenvs = sp["m_Floats"], sp["m_Colors"], sp["m_TexEnvs"]
    provider, builtin_docs = load_globals()
    environment = p.get("execution_environment")
    depth_velocity = None
    equivalent = source_selection is not None and source_selection["purpose"] == "ue_equivalent_source_particles"
    project_configured = source_selection is not None and source_selection.get("configuration_mode") == "ProjectConfigured"
    if environment is not None and environment.get("name") == "project_native_depth_velocity_fullres":
        from zzz_fx_native_shader import project_depth_velocity_contract
        if not project_configured or renderer["kind"] != "particle" \
                or output_contract != "color":
            raise PlanError("额外Depth/Velocity需要明确ProjectConfigured的Native粒子颜色材质")
        depth_velocity = project_depth_velocity_contract(environment["depth_velocity_contract"], source_selection["material_pid"])
        if depth_velocity is None:
            raise PlanError("额外Depth/Velocity缺准确源材质合同")
    if generated_ribbon is not None:
        if not project_configured or (source_selection or {}).get("vertex_deformation") is not None:
            raise PlanError("Generated Ribbon 需要明确 ProjectConfigured Native 几何消费者")
        for name in ("_CollideWithAvatar", "_ZOffset", "_ClampZToFar"):
            if name not in floats or _number(floats[name], name) != 0.0:
                raise PlanError("Generated Ribbon 当前 Native 几何不支持源位移／clip 修正: " + name)
        identity_rows = ["float4(1.0, 0.0, 0.0, 0.0)", "float4(0.0, 1.0, 0.0, 0.0)",
                         "float4(0.0, 0.0, 1.0, 0.0)", "float4(0.0, 0.0, 0.0, 1.0)"]
    translucency_pass = native_source["selection"].get("translucency_pass") if project_configured else None
    if project_configured and translucency_pass != "MTP_BeforeDOF":
        raise PlanError("ProjectConfigured materials require their explicit BeforeDOF stage")
    if equivalent:
        import zzz_fx_ue_equivalent as UE
        UE.validate_texture_uv_modes(floats)
        provider = UE.provider(provider)
    elif project_configured and environment is not None:
        from zzz_fx_native_shader import project_provider
        provider = project_provider(provider, environment)
    screen_index = None
    if renderer.get("project_camera") is not None:
        if not project_configured:
            raise PlanError("Current View输入仅用于明确ProjectConfigured材质")
        from zzz_fx_native_shader import project_camera_provider
        provider, screen_index = project_camera_provider(provider, renderer["project_camera"], native_source["shader_entry"]["pathID"])
    if output_contract == "distortion_field":
        screen_index = 3 if shader_name == "miHoYo/Particles/Distortion UVMove_Deprecated" else 4

    if output_contract == "distortion_field":
        depth_slots = [slot for slot, info in p["fp"]["bind"]["tex"].items()
                       if info["name"] == "_DepthMipChain"]
        for slot in depth_slots:
            samples = [s for s in p["fp"]["asm"] if re.search(r"\bt%d\." % slot, s)
                       and s.startswith("sample")]
            parsed = [T.split_instr(sample) for sample in samples]
            if not parsed or any(op not in ("sample_l", "sample_l_indexable")
                    or operands[-1].kind != "l" or operands[-1].lit != ["0.000000"]
                    for op, _, operands in parsed):
                raise PlanError("Distortion depth pyramid requires an unimplemented mip sampling contract")
        if depth_slots:
            provider["__textures__"] = dict(provider["__textures__"])
            provider["__textures__"]["_DepthMipChain"] = (
                "float4(1.0 / (CalcSceneDepth(ViewportUVToBufferUV({uv})) * 0.01), 0.0, 0.0, 0.0).xxxx")

    # 已序列化空 Material PPtr 的白色默认值来自 Shader Properties；
    # 直接保常量采样，不引入猜测的 UE 纹理资产或覆盖已有环境 provider。
    texture_defaults = {}
    default_samples = dict(provider.get("__textures__", {}))
    for name, env in texenvs.items():
        info = shader["props"].get(name) or {}
        if env["m_Texture"]["IsNull"] and info.get("type") == "2D" and info.get("tex_default") == "white":
            if name in default_samples:
                raise PlanError("源白色默认纹理与显式环境 provider 冲突: " + name)
            marker = "UEFX_SourceWhite_" + name
            default_samples[name] = "/* " + marker + " */ float4(1.0,1.0,1.0,1.0)"
            texture_defaults[name] = {"source_default": "white", "rgba": [1, 1, 1, 1],
                "binding": "SerializedNullMaterialPPtrAndShaderProperty",
                "semantic_reference": "https://docs.unity3d.com/cn/2019.4/Manual/SL-Properties.html", "marker": marker}
    if texture_defaults:
        provider = {**provider, "__textures__": default_samples}
    ps = T.translate(p["fp"], "b", provider, {output_register: "xyzw"})
    need = {}
    ps_special = []
    screen_override = False
    for row in p["fp"]["in"]:
        used = {c for v, c in ps["live_inputs"] if v == "v%d" % row["reg"] and c in row["mask"]}
        if not used:
            continue
        # 项目配置声明准确源屏幕语义；仍核原唯一xyz/w除法，保完整屏幕深度。
        if screen_index is not None and row["name"] == "TEXCOORD" and row["index"] == screen_index:
            reg = row["reg"]
            uses = [s for s in p["fp"]["asm"] if not s.startswith("dcl_") and
                    re.search(r"\bv%d\." % reg, s)]
            # This producer only divides its ComputeScreenPos interpolant by W.
            # Substitute the actual viewport UV and our canonical reciprocal eye
            # depth; no guessed projection sign or fabricated camera matrix.
            expected = r"div r\d+\.xyz, v%d\.xyzx, v%d\.wwww" % (reg, reg)
            if len(uses) != 1 or not re.fullmatch(expected, uses[0]):
                raise PlanError("Distortion screen interpolant contract changed: %s" % uses)
            ps_special.append("    uint4 bv%d = asuint(float4((Parameters.SvPosition.xy - View.ViewRectMin.xy) / ViewSize, "
                              "1.0 / (PixelDepth * 0.01), 1.0));" % reg)
            screen_override = True
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
    vs_provider = dict(provider)
    if screen_override:
        # 翻译器先处理死指令的部分provider。仅允许真实near分量，投影符号留下
        # 无效标记；DCE后仍活跃就明确拒绝，不能猜固定符号或丢near依赖。
        vs_provider["_ProjectionParams"] = {"rows": [
            "float4(UEFX_UnboundProjectionSign,View.NearPlane*0.01,0,0)"], "comps": "xy", "disabled_by": {}}
    deformation = (source_selection or {}).get("vertex_deformation")
    texture_position = (deformation or {}).get("mode") == "SourceVertexTexturePosition"
    vs_wanted = {k: "".join(sorted(v[0])) for k, v in need.items()}
    if texture_position:
        if output_contract != "color" or not project_configured or not renderer.get("mesh") \
                or renderer.get("mesh_affine") is not None or renderer.get("viewport_clamp") is not None:
            raise PlanError("顶点位置贴图需要 Native Mesh 粒子 TRS")
        mesh_source = renderer.get("vertex_texture_mesh")
        if not mesh_source or mesh_source.get("mode") != "SourceVertexTextureMesh" \
                or mesh_source.get("source_positions_zero") is not True \
                or mesh_source.get("source_texture_pid") != str(texenvs["_VertexPositionTex"]["m_Texture"]["m_PathID"]):
            raise PlanError("顶点位置贴图缺原零顶点网格、完整贴图包围范围及可导入基准形状")
        deformation = deepcopy(deformation)
        deformation["mesh_import"] = mesh_source
        output = deformation["local_position_output_register"]
        vs_wanted[output] = "xyz"
    elif deformation is not None:
        if output_contract != "color" or not project_configured or not renderer.get("mesh") \
                or deformation.get("mode") != "SourceVertexExtrusion" or renderer.get("viewport_clamp") is not None:
            raise PlanError("Source vertex extrusion requires its explicit Mesh geometry consumer")
        output = deformation["world_position_output_register"]
        declaration = next((r for r in p["vp"]["out"] if r["reg"] == output), None)
        if declaration is None or declaration["name"] != "TEXCOORD" or declaration["index"] != 6:
            raise PlanError("Source deformed world-position output declaration changed")
        vs_wanted[output] = "".join(sorted(set(vs_wanted.get(output, "")) | set("xyz")))
        identity_rows = ["float4(1.0, 0.0, 0.0, 0.0)", "float4(0.0, 1.0, 0.0, 0.0)",
                         "float4(0.0, 0.0, 1.0, 0.0)", "float4(0.0, 0.0, 0.0, 1.0)"]
        if provider["unity_ObjectToWorld"]["rows"] != identity_rows:
            raise PlanError("World-baked deformation bounds require the actual identity ObjectToWorld provider")
        deformation = deepcopy(deformation)
        deformation["geometry_constraint"] = source_selection["adaptation"]["vertex_geometry"]
        required_radius_cm = 100.0 * (abs(floats["_VertexExtrusionIntensity"]) + abs(floats["_VertexExtrusionIntensity2"]))
        if not math.isfinite(required_radius_cm) or required_radius_cm <= 0.0 \
                or deformation["additional_bounds_radius_cm"] != required_radius_cm:
            raise PlanError("顶点WPO世界半径不等于源幅度、单位法线、UNorm通道及PSR=1的真实上界")
        deformation["texture_bounds_inputs"] = []
        for name, pid in deformation["textures"].items():
            if str(texenvs[name]["m_Texture"]["m_PathID"]) != pid or texenvs[name]["m_Texture"]["IsNull"]:
                raise PlanError("Source vertex texture identity changed: " + name)
            entry = native_source["texture_entries"][pid]
            paths = [Path(path) for path in entry["files"] if str(path).endswith(".json")]
            if len(paths) != 1:
                raise PlanError("Source vertex texture requires one real sampling metadata input")
            raw = paths[0].read_bytes()
            metadata = json.loads(raw.decode("utf-8-sig"))
            if metadata.get("m_TextureFormat") != 25 or metadata.get("m_ColorSpace") not in (0, 1):
                raise PlanError("Vertex bounds require the actual bounded BC7 UNorm source texture")
            deformation["texture_bounds_inputs"].append({"parameter": name, "pathID": pid,
                "path": str(paths[0]), "size": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                "texture_format": 25, "sample_range": [0, 1]})
    if generated_ribbon is not None and (vs_provider.get("unity_ObjectToWorld") or {}).get("rows") != identity_rows:
        raise PlanError("Generated Ribbon 已烘焙 World 顶点，ObjectToWorld 不能再套 Node／Root")
    vs = T.translate(p["vp"], "a", vs_provider, vs_wanted)
    if "UEFX_UnboundProjectionSign" in vs["code"]:
        raise PlanError("源投影符号仍被活跃代码消费，不能以固定符号替代真实View投影")

    ctx = {"builtins": set(), "dyn": {}, "dynamic_parameter_components": 0, "renderer_kind": renderer["kind"],
           "mesh": renderer.get("mesh", False), "uv_count": renderer.get("uv_count", 1),
           "sprite_subuv": renderer.get("sprite_subuv", False),
           "sprite_static_quad_uv": (equivalent or source_selection is not None
               and source_selection.get("configuration_mode") == "ProjectConfigured") and renderer.get("sprite_static_quad_uv", False),
           "sprite_extra_quad_uv": (equivalent or source_selection is not None
               and source_selection.get("configuration_mode") == "ProjectConfigured") and renderer.get("sprite_extra_quad_uv", False),
           "sprite_uv_tiles": renderer.get("sprite_uv_tiles", (1, 1)),
           "sprite_uv_animation_type": renderer.get("sprite_uv_animation_type", 0),
           "mesh_uv": renderer.get("mesh_uv"),
           "sprite_normal_direction": renderer.get("sprite_normal_direction"),
           "sprite_rotation_2d": renderer.get("sprite_rotation_2d", False),
           "warnings": []}
    av = vs_inputs(p["vp"], vs["live_inputs"], renderer, ctx)
    affine = renderer.get("mesh_affine")
    if affine is not None:
        if not renderer.get("mesh") or affine.get("mode") != "full_affine_local_mesh_v1":
            raise PlanError("Invalid complete affine mesh adapter")
        if any(int(slot) == 3 for slot in ctx["dyn"]):
            raise PlanError("Affine DP3 transport collides with original source vertex streams")
        ctx["dyn"][3] = "FullAffineTransport"
        ctx["dynamic_parameter_components"] |= 0xF000
        alignment = affine.get("project_alignment")
        if alignment is not None:
            PR.mesh_alignment_policy(alignment["policy"])
            source_mask = ctx["dynamic_parameter_components"] & 0x0FFF
            allocation_mask = renderer.get("mesh_euler_source_components",source_mask)
            if type(allocation_mask) is not int or not 0 <= allocation_mask <= 0x0FFF or source_mask & ~allocation_mask:
                raise PlanError("Shared Mesh transport does not preserve this field's actual original inputs")
            free = [[slot,component] for slot in (2,1,0) for component in range(4)
                    if not allocation_mask & (1 << (slot*4+component))]
            if len(free) < 3:
                raise PlanError("Mesh Euler lacks three free DP components after preserving all live source streams")
            layout = free[:3]
            if layout != [[2,0],[2,1],[2,2]] or "mesh_euler_source_components" in renderer:
                affine = deepcopy(affine)
                alignment = PR.mesh_alignment_transport(alignment["policy"], layout, allocation_mask)
                affine["project_alignment"] = alignment
            for slot, component in layout:
                role = {0:"Custom1",1:"Custom2",2:"StableRandomXYZW"}[slot] \
                    if allocation_mask & (0xF << (slot*4)) else "MeshAlignmentEuler"
                ctx["dyn"].setdefault(slot, role)
                ctx["dynamic_parameter_components"] |= 1 << (slot*4+component)
                ctx["builtins"].add("DP"+str(slot))
        ctx["builtins"].add("DP3")
    sprite_geometry = (renderer.get("viewport_clamp") or {}).get("sprite_geometry")
    if sprite_geometry is not None:
        if renderer.get("mesh") or any(int(slot) == 3 for slot in ctx["dyn"]):
            raise PlanError("Sprite geometry DP3 transport conflicts with original source streams")
        PR.validate_sprite_geometry(sprite_geometry)
        ctx["dyn"][3] = "SpriteGeometryTransport"
        ctx["dynamic_parameter_components"] |= 0x7000 if "depth_pivot" in sprite_geometry else 0x3000
    link = ["    uint4 bv%d = ao%d;" % (preg, vreg) for vreg, (_, preg) in sorted(need.items())]

    # 全局量的"无效果"取值只在材质关闭对应开关时成立
    for compiled, stage_provider in ((ps, provider), (vs, vs_provider)):
        for name, _, _ in compiled["globals"]:
            if "disabled_by" not in stage_provider[name]:
                raise PlanError("全局量提供方未声明自己的前提合同: " + name)
            for prop, required in stage_provider[name]["disabled_by"].items():
                if floats.get(prop) != required:
                    raise PlanError("全局量 %s 取无效果值的前提是 %s=%s，材质里是 %r" % (name, prop, required, floats.get(prop)))

    src, dst = blend_of(p, floats)
    if environment is not None:
        blend, out_conv = environment["blend"], environment["output_conversion"]
    elif (src, dst) not in BLEND_MAP:
        raise PlanError("混合 %s %s 没有对应的 UE 混合模式" % (src, dst))
    else:
        blend, out_conv = BLEND_MAP[(src, dst)]
    if generated_ribbon is not None and blend != "BLEND_AlphaComposite":
        raise PlanError("Generated Ribbon 当前只接受原完整预乘 RGBA 的 AlphaComposite")
    cull = flag(floats, "Cull", " ".join(p["state"]))
    zwrite = flag(floats, "ZWrite", " ".join(p["state"]))
    ztest = flag(floats, "ZTest", " ".join(p["state"]))
    if "resolved_state" in p:
        cull, zwrite, ztest = (p["resolved_state"][k] for k in ("cull", "zwrite", "ztest"))
    if depth_velocity is not None:
        if {"cull": cull, "zwrite": zwrite, "ztest": ztest} != depth_velocity["source_render_state"] \
                or blend != "BLEND_AlphaComposite":
            raise PlanError("额外Depth/Velocity不能改写原状态或预乘RGBA")
    elif zwrite not in (None, 0.0):
        raise PlanError("ZWrite=%r 的半透明特效未实现" % zwrite)
    if ztest not in (None, 4.0, 8.0, 0.0):
        raise PlanError("ZTest=%r 未实现（只支持 LEqual / Always）" % ztest)
    disable_depth_test = ztest == 8.0

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
    returns = {"rgb": "return c;", "rgb*a": "return float4(c.rgb * c.a, c.a);",
               "rgb,1-alpha": "return float4(c.rgb, 1.0 - c.a);"}
    if out_conv not in returns:
        raise PlanError("Unknown material output conversion: " + out_conv)
    body = (PRELUDE % {"shader": shader_name, "pass": p["name"], "keywords": " ".join(keywords) or "无"}
            + pre_pos + "\n".join(av) + "\n" + vs["code"] + "\n" + "\n".join(link + ps_special) + "\n"
            + ps["code"] + "\n    float4 c = asfloat(bo%d);\n" % output_register
            + "    " + returns[out_conv] + "\n")
    vertex_stage = None
    if deformation is not None or generated_ribbon is not None:
        varying_outputs = [{"name": "UEFX_Varying_%d" % vreg, "source_register": vreg,
                            "pixel_register": preg, "components": "".join(sorted(used))}
                           for vreg, (used, preg) in sorted(need.items())]
        if generated_ribbon is not None:
            from zzz_fx_native_shader import native_payload_varyings
            payloads = native_payload_varyings(p["vp"], vs_provider, ctx.get("native_payload_bindings", {}),
                {row["source_register"]: row["components"] for row in varying_outputs},
                (source_selection or {}).get("programs", {}).get("vp"))
            for row in varying_outputs:
                if row["source_register"] in payloads:
                    row["native_payload"] = payloads[row["source_register"]]
        shared_prelude = PRELUDE % {"shader": shader_name, "pass": p["name"], "keywords": " ".join(keywords)}
        vertex_code = shared_prelude + pre_pos + "\n".join(av) + "\n" + vs["code"]
        vertex_code += "\n" + "\n".join("%s = asfloat(ao%d);" % (row["name"], row["source_register"])
                                       for row in varying_outputs)
        if texture_position:
            vertex_code += "\nreturn F.U(asfloat(ao%d).xyz) * 100.0;\n" % output
        elif deformation is not None:
            radius_parameter = "UEFX_SourceVertexWPOBoundsRadiusCM"
            radius_cm = deformation["additional_bounds_radius_cm"]
            if radius_parameter not in vs["mat_params"]:
                raise PlanError("源VS的实际位置约束未消费半径，不能把幅度倍率当上界")
            vertex_code += "\nreturn WorldPos - RawWorldPos + (F.U(asfloat(ao%d).xyz) * 100.0 - WorldPos) * (UEFX_SourceVertexWPO == 1.0 ? 1.0 : 0.0);\n" % output
        else:
            # Native Ribbon 已拥有生成顶点及 clip；原 VS 在这里输出真实插值，不再移动一次几何。
            vertex_code += "\nreturn float3(0.0, 0.0, 0.0);\n"
        body = shared_prelude + "\n".join("uint4 bv%d = asuint(%s);" % (row["pixel_register"], row["name"])
                                         for row in varying_outputs) + "\n" + "\n".join(ps_special)
        body += "\n" + ps["code"] + "\nfloat4 c = asfloat(bo%d);\n" % output_register + returns[out_conv] + "\n"
        vertex_stage = {"mode": "SourceVertexProgramWithInterpolatedOutputs", "code": vertex_code,
                        "builtins": sorted(set(ctx["builtins"]) | {"CamPos", "Time", "RawWorldPos"}),
                        "params": sorted(set(vs["mat_params"]) | ({"UEFX_SourceVertexWPO"} if deformation is not None and not texture_position else set())),
                        "textures": vs["textures"], "varyings": varying_outputs,
                        **({"deformation": deformation} if deformation is not None else {
                            "geometry": {"mode": "NativeGeneratedRibbon", "position_space": "WorldBakedUnityMetres",
                                         "additional_wpo_cm": 0.0, "source_uniform_constraints": {
                                             name: floats[name] for name in ("_CollideWithAvatar", "_ZOffset", "_ClampZToFar")}}})}
        if length_color is not None:
            vertex_stage["source_trail_length_color"] = deepcopy(length_color)
        # 像素阶段只接原插值与真实屏幕系统值，不在片元重新执行顶点采样。
        builtins = {"CamPos", "Time"} | ({"PixelDepth"} if any("PixelDepth" in row for row in ps_special) else set()) \
            | ({"FaceSign"} if any("FaceSign" in row for row in ps_special) else set())
    # Custom 节点函数体里不需要缩进；去掉 4 空格前缀便于阅读
    body = "\n".join(l[4:] if l.startswith("    ") else l for l in body.split("\n"))
    component_age = renderer.get("component_age_binding")
    if component_age is not None:
        if renderer["kind"] != "mesh" or not project_configured or component_age != {"DP0.x": "System.Age"}:
            raise PlanError("静态材质年龄需要明确原 Emitter System.Age 的 DP0.x 合同")
        dynamic_component(ctx, 0, 0, "ComponentAgeAndCoverage" if renderer.get("component_coverage_binding") else "ComponentAge")
        builtins.discard("Time")
        builtins.add("DP0")
        body = re.sub(r"\bTime\b", "DP0.x", body)
    component_coverage = renderer.get("component_coverage_binding")
    if component_coverage is not None:
        if component_age is None or component_coverage != {"DP0.y": "ParticleLifetimeFade"}:
            raise PlanError("静态网格消退需要明确的原粒子寿命覆盖率绑定")
        dynamic_component(ctx, 0, 1, "ComponentAgeAndCoverage")
        terminal = re.search(r"return ([^;]+);\s*$", body)
        if terminal is None:
            raise PlanError("静态网格消退缺唯一最终颜色输出")
        value = terminal.group(1)
        faded = ("float4((%s).rgb,(%s).a*saturate(DP0.y))" % (value, value)
                 if blend == "BLEND_Translucent" else "(%s)*saturate(DP0.y)" % value)
        body = body[:terminal.start()] + "return " + faded + ";\n"
    texture_defaults = {name: {key: value for key, value in item.items() if key != "marker"}
                        for name, item in texture_defaults.items() if item["marker"] in body}
    if equivalent:
        body = "// Explicit UE equivalent environment; source shadow response is replaced, visual calibration pending.\n" + body

    params = {}
    for name, dim in mat_params.items():
        if name.endswith("_TexelSize") and native_source is not None:
            texture_name = name[:-len("_TexelSize")]
            pointer = texenvs[texture_name]["m_Texture"]
            if dim != 4 or pointer["IsNull"]:
                raise PlanError("TexelSize 需要真实绑定的二维贴图")
            entry = native_source["texture_entries"][str(pointer["m_PathID"])]
            metadata = json.loads(Path(entry["nativeJson"]).read_text(encoding="utf-8-sig"))
            width, height = metadata["m_Width"], metadata["m_Height"]
            if width <= 0 or height <= 0:
                raise PlanError("TexelSize 的原贴图尺寸无效")
            params[name] = {"dim": 4, "value": [1.0 / width, 1.0 / height, width, height]}
        elif deformation is not None and not texture_position and name == radius_parameter:
            if dim != 1 or name in floats or name in colors or name in texenvs or name in shader["props"]:
                raise PlanError("源材质与派生VS位置约束半径反射冲突")
            params[name] = {"dim": 1, "value": radius_cm}
        elif native_source is not None and name in native_source["selection"].get("missing_scalar_parameters", {}):
            choice = native_source["selection"]["missing_scalar_parameters"][name]
            if not project_configured or dim != 1 or name in floats or name in colors or name in shader["props"] \
                    or not choice.get("reason") or type(choice.get("value")) not in (float, int) or not math.isfinite(choice["value"]):
                raise PlanError("缺失参数的项目值不能覆盖原材质或 Shader 默认值：" + name)
            params[name] = {"dim": 1, "value": choice["value"]}
        else:
            params[name] = {"dim": dim, "value": material_value(name, dim, shader["props"], floats, colors, texenvs)}
    if deformation is not None and not texture_position:
        if "UEFX_SourceVertexWPO" in params or "UEFX_SourceVertexWPO" in textures:
            raise PlanError("源材质与项目真实顶点WPO能力参数冲突")
        params["UEFX_SourceVertexWPO"] = {"dim": 1, "value": 1.0}
        if radius_parameter not in params or radius_parameter in textures:
            raise PlanError("源材质与项目真实顶点WPO半径参数冲突")
    pixel_params = list(ps["mat_params"]) if vertex_stage is not None else list(params)
    if generated_ribbon is not None:
        age_parameter = generated_ribbon["system_age"]["parameter"]
        if age_parameter in params or age_parameter in textures or any(age_parameter in group for group in (floats, colors, texenvs, shader["props"])):
            raise PlanError("源材质与 Native Ribbon 的派生时钟参数冲突")
        # 0 是 System.Age 的初始值；实际绑定必须由 Native renderer 验证，不能以该初值补绑定失败。
        params[age_parameter] = {"dim": 1, "value": 0.0}
        pixel_params.append(age_parameter)
        builtins.discard("Time")
        body = re.sub(r"\bTime\b", age_parameter, body)
        vertex_stage["builtins"] = [name for name in vertex_stage["builtins"] if name != "Time"]
        vertex_stage["params"] = sorted(set(vertex_stage["params"]) | {age_parameter})
        vertex_stage["code"] = re.sub(r"\bTime\b", age_parameter, vertex_stage["code"])
    viewport = renderer.get("viewport_clamp")
    if viewport is not None:
        if set(viewport["params"]) & (set(params) | set(textures)):
            raise PlanError("Source shader parameters collide with reserved UE viewport adapter parameters")
        if viewport.get("facing_adapter") is not None and "UEFX_PreviousView" in (set(params) | set(textures) | builtins):
            raise PlanError("Source shader collides with reserved material previous-view selector")
        params.update(viewport["params"])
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

    key_data = {"generator": 2, "renderer_kind": renderer["kind"], "mesh": renderer.get("mesh", False),
                          "output_contract": output_contract,
                          "code": body, "params": sorted(params), "tex": sorted(tex_params), "blend": blend,
                           "two_sided": cull == 0.0, "disable_depth_test": disable_depth_test, "builtins": sorted(builtins),
                           "dynamic_parameter_components": ctx["dynamic_parameter_components"]}
    if equivalent:
        key_data["ue_environment"] = environment
    if viewport is not None:
        key_data["viewport_adapter"] = {k: viewport[k] for k in ("mode", "metric", "code", "inputs")}
        if viewport.get("facing_adapter") is not None:
            key_data["viewport_adapter"]["facing_adapter"] = viewport["facing_adapter"]
    if affine is not None:
        key_data["mesh_affine"] = affine
    if vertex_stage is not None:
        key_data["vertex_stage"] = vertex_stage
    if generated_ribbon is not None:
        key_data["generated_ribbon"] = generated_ribbon
    if length_color is not None:
        key_data["source_trail_length_color"] = length_color
    if depth_velocity is not None:
        key_data["native_depth_velocity"] = depth_velocity
    if texture_defaults:
        key_data["source_texture_defaults"] = texture_defaults
    if source_selection is not None:
        if native_source["selection"].get("missing_scalar_parameters"):
            source_selection["project_missing_scalar_parameters"] = native_source["selection"]["missing_scalar_parameters"]
        if renderer.get("project_camera") is not None:
            source_selection["project_camera_adapter"] = renderer["project_camera"]
            source_selection["source_runtime_camera_verified"] = False
        source_selection["runtime_global_values"] = ("ProjectConfigured_provider_runtime_unverified" if project_configured else
                                                     "explicit_clear_scene_calibration_inputs_not_original_runtime" if equivalent
                                                     else "unverified_existing_preview_provider")
        source_selection["global_provider"] = str(GLOBALS_PATH)
        source_selection["global_provider_sha256"] = hashlib.sha256(GLOBALS_PATH.read_bytes()).hexdigest()
        key_data["source_selection"] = source_selection
    if translucency_pass is not None:
        key_data["translucency_pass"] = translucency_pass
    key_src = json.dumps(key_data, sort_keys=True)
    key = hashlib.md5(key_src.encode()).hexdigest()[:8]
    short = shader_name.split("/")[-1].replace(" ", "")
    return {
        "material": mat["m_Name"], "shader": shader_name, "keywords": keywords, "pass": p["name"],
        "master": "M_ZZZFX_%s%s_%s" % ("ProjectConfigured_" if project_configured else "UEEquivalent_" if equivalent else "", short, key), "code": body, "blend": blend,
        "two_sided": cull == 0.0, "builtins": sorted(builtins), "dyn_params": ctx["dyn"],
        "dynamic_parameter_components": ctx["dynamic_parameter_components"],
        "disable_depth_test": disable_depth_test,
        "params": params, "textures": tex_params,
        **({"vertex_stage": vertex_stage, "pixel_textures": ps["textures"],
            "additional_wpo_bounds_radius_cm": deformation["additional_bounds_radius_cm"] if deformation is not None else 0.0}
           if vertex_stage is not None else {}),
        **({"source_texture_defaults": texture_defaults} if texture_defaults else {}),
        "pixel_params": pixel_params,
        **({"viewport_clamp": viewport} if viewport is not None else {}),
        **({"mesh_affine": affine} if affine is not None else {}),
        **({"mesh_uv": renderer["mesh_uv"]} if renderer.get("mesh_uv") is not None else {}),
        "renderer_kind": renderer["kind"], "mesh": renderer.get("mesh", False),
        **({"generated_ribbon": generated_ribbon} if generated_ribbon is not None else {}),
        **({"source_trail_length_color": length_color} if length_color is not None else {}),
        **({"native_depth_velocity": depth_velocity} if depth_velocity is not None else {}),
        **({"component_age_binding": component_age} if component_age is not None else {}),
        **({"component_coverage_binding": component_coverage} if component_coverage is not None else {}),
        "output_contract": output_contract, "output_register": output_register,
        "source_variant": str(shader_file),
        "source_variant_sha256": source_selection["native_sha256"] if source_selection else
                                 hashlib.sha256(shader_file.read_bytes()).hexdigest(),
        **({"source_selection": source_selection} if source_selection else {}),
        **({"configuration_mode": "ProjectConfigured"} if project_configured else {}),
        **({"translucency_pass": translucency_pass} if translucency_pass is not None else {}),
        **({"ue_environment": environment} if equivalent else {}),
        **({"project_environment": environment} if project_configured and environment is not None else {}),
        "disabled_passes": mat.get("m_DisabledShaderPasses") or [], "warnings": ctx["warnings"],
        "skipped_passes": [q["lightmode"] for q in shader["passes"]
                           if q is not p and q["lightmode"] not in (mat.get("m_DisabledShaderPasses") or [])],
    }
