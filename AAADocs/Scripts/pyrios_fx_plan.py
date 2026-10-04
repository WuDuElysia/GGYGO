"""Pyrios 身体 FX 的纯数据规划（不依赖 Unreal，可单独运行自检）。

数据来源：
- 材质参数：Content/Characters/Player/Pyrios/Materials/MAT_Pyrois_Body_FX0*.json（AnimeStudio 导出的 Unity Material）。
- 层顺序：Materials/FXObjects/Pyrois_Body_FX_0*.json 的 SkinnedMeshRenderer.m_Materials。
  四个 FX 网格都只有一个 submesh，却挂了三个材质；Unity 会把多出的材质依次在同一几何上再画一遍，
  因此 m_Materials 的顺序就是叠加顺序（先画的在下）。
- 采样寻址与色彩空间：Materials/TextureSettings/*.json（AnimeStudio 以 JSON 导出的 Texture2D，取 m_WrapMode、m_ColorSpace）。
- 着色逻辑：F:/AnimeStudio/Exports/Shader/ZZZ_20260925 下
  miHoYo/Particles/Particles_Dissolve_CustomColor_Mask_Cap 的 D3D11 反汇编，cbuffer 偏移靠同目录 .dat
  里的反射表还原成属性名。FX02 用的非 Cap 变体没有导出，按同族同属性集处理。

master 材质只实现这三个材质实际启用的特性分支。源材质启用了未实现的特性时 load_plan 直接报错，
不静默降级成另一种效果。

用法：python pyrios_fx_plan.py   打印解析结果，用于离线核对。
"""
import json
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from pyrios_material_plan import load_texture_settings, unity_color_to_linear  # noqa: E402

LAYER_COUNT = 3
SHADER_FAMILY = "miHoYo/Particles/Particles_Dissolve_CustomColor_Mask"

# 每层在 master 材质里的贴图参数名 -> Unity 贴图属性名。
TEXTURE_SLOTS = {
    "MainTex": "_MainTex",
    "MaskTex": "_MaskTex",
    "DissolveTex": "_DissolveTex",
    "DissolveRampTex": "_DissolveRampTex",
    "RampTex": "_RampTex",
    "DistortionTex": "_DistortionTex",
    "DistortionTex2": "_DistortionTex2",
}

# 每层的 float4 参数名，顺序即 master 材质 Custom 节点的输入顺序。
VECTOR_PARAMS = (
    "MainST", "MaskST", "DissolveST", "DissolveRampST", "RampST", "DistST", "Dist2ST",
    "SpeedA", "SpeedB", "SpeedC",
    "CustomColor", "MultiplyColor", "AmbientColor",
    "FeatA", "FeatB", "ChanA", "ChanB", "RampCfg",
    "DissCfg", "DissCfg2", "DistI", "Dist2I", "AlphaCfg", "SoftCfg", "FlipA", "FlipB",
    "WrapA", "WrapB",
)

# Properties 块里声明为 Color 的属性。Unity 线性空间工程上传时会做 Gamma->Linear，
# 其余 m_Colors 条目（UV 速度、MoveStep 等）是 Vector，原样上传。
COLOR_PROPERTIES = {"_MultiplyParticleColor", "_AmbientColor", "_CustomDataColor"}

# master 未实现的分支：这些属性必须等于给定值，否则拒绝生成。
REQUIRED_VALUES = {
    "_UsingNonPSR": 1.0,           # 模型模式：溶解/扭曲强度来自材质而不是粒子 CustomData
    "_BlendMode": 0.0, "_SrcFactor": 1.0, "_DstFactor": 10.0,  # One / OneMinusSrcAlpha 预乘混合
    "_ZWrite": 0.0, "_ZTest": 4.0, "_ZOffset": 0.0,
    "_VertexExtrusion": 0.0, "_AnimationSheets_Switch": 0.0, "_InvFresnel": 0.0,
    "_ScreenEffects": 0.0, "_Distortion": 0.0, "_UseSphereFade": 0.0, "_FadeFromCameraOn": 0.0,
    "_UseClipPlane": 0.0, "_VertexAnimation": 0.0, "_RigidAnimation": 0.0, "_RibbonAnimation": 0.0,
    "_group_alphaCut": 0.0, "_AffectedByMainLightColor": 0.0, "_CollideWithAvatar": 0.0,
    "_BackfaceRevert": 0.0, "_2ToneUsingVertexAlpha": 0.0, "_OpaquenessFadeByScript": 1.0,
    "_AlphaFade_Timeline": 1.0, "_TimeScaleSpeed": 0.0, "_TimeOffset": 0.0,
    "_group_CharacterVfxMask": 0.0, "_StencilMode": 0.0, "_Saturation": 1.0, "_ApplySceneFog": 0.0,
    "_AffectByGlobalEtherColor": 0.0, "_AffectByGlobalWaterColor": 0.0, "_AffectByEffectFogColor": 0.0,
    "_AffectByEffectSandstormColor": 0.0, "_AffectByCamera3DUIAlpha": 0.0,
    "_group_maintex_blur": 0.0, "_MoonRockMode": 0.0, "_CustomData1W": 0.0,
    "_IgnoreVertexColor": 1.0,     # master 不接顶点色
}

# Unity TextureWrapMode：0 Repeat，1 Clamp。Mirror/MirrorOnce 未实现。
WRAP_REPEAT, WRAP_CLAMP = 0, 1
for _tex in ("MainTex", "MaskTex", "DissolveTex", "DistortionTex", "DistortionTex2"):
    REQUIRED_VALUES["_%sUVMode" % _tex] = 0.0
for _tex in ("MainTex", "MaskTex", "DissolveTex", "DissolveRampTex", "RampTex", "DistortionTex", "DistortionTex2"):
    REQUIRED_VALUES["_%sRotation" % _tex] = 0.0
    REQUIRED_VALUES["_%sClampU" % _tex] = 0.0
    REQUIRED_VALUES["_%sClampV" % _tex] = 0.0


def _num(v, label):
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        raise ValueError("需要有限数值: " + label)
    return float(v)


def _tex(props, unity_name):
    entry = props["m_TexEnvs"].get(unity_name)
    if entry is None:
        raise ValueError("材质缺少贴图属性 " + unity_name)
    tex = entry["m_Texture"]
    name = None if tex.get("IsNull", True) else tex.get("Name")
    st = (_num(entry["m_Scale"]["X"], unity_name), _num(entry["m_Scale"]["Y"], unity_name),
          _num(entry["m_Offset"]["X"], unity_name), _num(entry["m_Offset"]["Y"], unity_name))
    return name, st


def _vec(props, name, convert):
    c = props["m_Colors"].get(name)
    if c is None:
        raise ValueError("材质缺少向量/颜色属性 " + name)
    rgba = [_num(c[k], name + "." + k) for k in ("r", "g", "b", "a")]
    if convert:
        rgba = list(unity_color_to_linear(rgba[:3])) + [rgba[3]]
    return tuple(rgba)


def wrap_code(texture_name, wrap):
    """master 的采样模式编码：bit0 = U Repeat，bit1 = V Repeat。

    未启用的槽位不会被采样，编码固定为 3。导出的 Texture2D 只有单个 m_WrapMode，
    按 U/V 同一模式处理。
    """
    if texture_name is None:
        return 3.0
    if texture_name not in wrap:
        raise ValueError("缺少贴图采样设置: " + texture_name)
    mode = wrap[texture_name]
    if mode == WRAP_REPEAT:
        return 3.0
    if mode == WRAP_CLAMP:
        return 0.0
    raise ValueError("%s 的 m_WrapMode=%s 未实现" % (texture_name, mode))


def load_wrap_modes(settings):
    """{贴图名: m_WrapMode}，来源见 pyrios_material_plan.load_texture_settings。"""
    return {name: entry["wrap"] for name, entry in settings.items()}


def slot_srgb(layers, settings):
    """每个贴图槽的 sRGB 采样类型。master 的贴图参数采样类型按槽固定，三层同槽的贴图色彩空间必须一致。"""
    result = {}
    for layer in layers:
        for slot, tex in layer["textures"].items():
            if tex is None:
                continue
            if tex not in settings:
                raise ValueError("缺少贴图导入设置: " + tex)
            srgb = settings[tex]["srgb"]
            if result.setdefault(slot, srgb) != srgb:
                raise ValueError("槽 %s 在不同层里混用了 sRGB 与线性贴图" % slot)
    return result


def layer_params(data, wrap):
    """把一个 Unity 材质换算成 master 材质一层的参数。返回 (textures, vectors)。"""
    name = data.get("m_Name")
    shader = data["m_Shader"]["Name"]
    if not shader.startswith(SHADER_FAMILY):
        raise ValueError("%s 的 shader %s 不属于 %s" % (name, shader, SHADER_FAMILY))
    p = data["m_SavedProperties"]
    f = {k: _num(v, name + k) for k, v in p["m_Floats"].items()}
    for key, want in REQUIRED_VALUES.items():
        if key not in f:
            raise ValueError("%s 缺少属性 %s" % (name, key))
        if f[key] != want:
            raise ValueError("%s 的 %s=%s，master 只实现 %s" % (name, key, f[key], want))
    if f["_Cull"] not in (0.0, 2.0):
        raise ValueError("%s 的 _Cull=%s，只支持 Off(0)/Back(2)" % (name, f["_Cull"]))
    use_dissolve = f["_UseDissolveTex"] > 0.5
    if use_dissolve and f["_SoftEdge"] < 0.5:
        raise ValueError(name + " 开了溶解但没开软边，硬边分支未实现")

    enabled = {
        "MainTex": True,
        "MaskTex": f["_UseMask"] > 0.5,
        "DissolveTex": use_dissolve,
        "DissolveRampTex": use_dissolve and f["_group_dissolve_ramptex"] > 0.5,
        "RampTex": f["_group_ramptex"] > 0.5,
        "DistortionTex": f["_UseDistortionTexture"] > 0.5,
        "DistortionTex2": f["_UseDistortionTexture2"] > 0.5,
    }
    textures, st = {}, {}
    for slot, unity_name in TEXTURE_SLOTS.items():
        tex_name, tex_st = _tex(p, unity_name)
        if enabled[slot] and not tex_name:
            raise ValueError("%s 启用了 %s 但贴图为空" % (name, unity_name))
        textures[slot] = tex_name if enabled[slot] else None
        st[slot] = tex_st

    speed = {k: _vec(p, k, False) for k in ("_MainTexUVSpeed", "_MaskTexUVSpeed", "_DissolveUVSpeed",
                                            "_DistortionUVSpeed", "_Distortion2UVSpeed", "_MainTexMoveStep")}
    v = {
        "MainST": st["MainTex"], "MaskST": st["MaskTex"], "DissolveST": st["DissolveTex"],
        "DissolveRampST": st["DissolveRampTex"], "RampST": st["RampTex"],
        "DistST": st["DistortionTex"], "Dist2ST": st["DistortionTex2"],
        "SpeedA": speed["_MainTexUVSpeed"][:2] + speed["_MaskTexUVSpeed"][:2],
        "SpeedB": speed["_DissolveUVSpeed"][:2] + speed["_DistortionUVSpeed"][:2],
        "SpeedC": speed["_Distortion2UVSpeed"][:2] + speed["_MainTexMoveStep"][:2],
        "CustomColor": _vec(p, "_CustomDataColor", True),
        "MultiplyColor": _vec(p, "_MultiplyParticleColor", True),
        "AmbientColor": _vec(p, "_AmbientColor", True),
        "FeatA": (float(enabled["MaskTex"]), float(use_dissolve),
                  float(enabled["DistortionTex"]), float(enabled["DistortionTex2"])),
        "FeatB": (float(enabled["RampTex"]), float(enabled["DissolveRampTex"]),
                  f["_SoftEdge"], f["_UVMove"]),
        "ChanA": (f["_ColorChannelMapping"], f["_AlphaChannelMapping"],
                  f["_MaskChannelMapping"], f["_MaskDistortionChannelMapping"]),
        "ChanB": (f["_DissolveChannel"], f["_DissolveRampTexChannelMapping"],
                  f["_DistortionChannel"], f["_Distortion2Channel"]),
        # 第 4 分量对应 shader 读取的 _DissolveRampTex_UseMainTexUV。这个 cbuffer 变量不是材质属性
        # （Inspector 里的开关写的是另一个名字 _DissolveRampTex_UseDissolveTexUV），运行时恒为 0，
        # 所以溶解 ramp 实际总是用原始 uv0。
        "RampCfg": (f["_RampTexChannelMapping"], f["_RampTexOnlyAffectAlpha"], f["_RampTex_UseMainTexUV"], 0.0),
        "DissCfg": (f["_DissolveProgress"], f["_SoftRange"], f["_SoftEdgeUsingOldFunction"],
                    f["_DissolveRampTex_BlendOp"]),
        "DissCfg2": (f["_DissolveAffects2Tone"], f["_UsingAlphaAsDissolve"], f["_LerpBrightness"],
                     f["_DistortionIntensity_NonPSR"]),
        "DistI": (f["_DistortionIntensity"], f["_DissolveDistortionIntensity"],
                  f["_MaskDistortionIntensity"], f["_MaskAffectsDistortion"]),
        "Dist2I": (f["_Distortion2Intensity"], f["_DissolveDistortion2Intensity"],
                   f["_MaskDistortion2Intensity"], 0.0),
        "AlphaCfg": (f["_PowerRGB"], f["_PowerAlpha"], f["_AlphaFade"], 1.0 if f["_Cull"] == 2.0 else 0.0),
        # 软粒子距离单位是 Unity 米，master 里把 UE 厘米深度差除以 100 后再用。
        "SoftCfg": (f["_SoftParticles"], f["_SoftParticlesNearFadeDistance"],
                    f["_SoftParticlesRcpDistance"], 0.0),
        "FlipA": (f["_MainTexFlip"], f["_MaskTexFlip"], f["_DissolveTexFlip"], f["_DissolveRampTexFlip"]),
        # w 分量是层启用标记；master 默认值 0 让未赋值的层不出图。
        "FlipB": (f["_RampTexFlip"], f["_DistortionTexFlip"], f["_DistortionTex2Flip"], 1.0),
        "WrapA": tuple(wrap_code(textures[s], wrap) for s in ("MainTex", "MaskTex", "DissolveTex", "DissolveRampTex")),
        "WrapB": tuple(wrap_code(textures[s], wrap) for s in ("RampTex", "DistortionTex", "DistortionTex2")) + (3.0,),
    }
    if set(v) != set(VECTOR_PARAMS):
        raise AssertionError("向量参数表与 VECTOR_PARAMS 不一致")
    return textures, v


def load_order(objects_dir):
    """读取四个 FX 网格的材质顺序，要求一致。"""
    orders = {}
    for path in sorted(Path(objects_dir).glob("Pyrois_Body_FX_0*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        orders[path.stem] = tuple(m["Name"] for m in data["m_SkinnedMeshRenderer"]["m_Materials"])
    if len(orders) != 4:
        raise ValueError("应有 4 个 FX 网格对象，实际 %d" % len(orders))
    unique = set(orders.values())
    if len(unique) != 1:
        raise ValueError("FX 网格的材质顺序不一致: " + str(orders))
    order = unique.pop()
    if len(order) != LAYER_COUNT:
        raise ValueError("master 固定 %d 层，源对象有 %d 个材质" % (LAYER_COUNT, len(order)))
    return order


def load_plan(material_dir):
    material_dir = Path(material_dir)
    order = load_order(material_dir / "FXObjects")
    settings = load_texture_settings(material_dir / "TextureSettings")
    wrap = load_wrap_modes(settings)
    layers = []
    for mat_name in order:
        data = json.loads((material_dir / (mat_name + ".json")).read_text(encoding="utf-8"))
        if data.get("m_Name") != mat_name:
            raise ValueError("材质 JSON 名称不符: " + mat_name)
        textures, vectors = layer_params(data, wrap)
        layers.append({"source": mat_name, "textures": textures, "vectors": vectors})
    names = sorted({t for layer in layers for t in layer["textures"].values() if t})
    return {"order": order, "layers": layers, "textures": names,
            "srgb": {n: settings[n]["srgb"] for n in names}, "slot_srgb": slot_srgb(layers, settings)}


if __name__ == "__main__":
    here = Path(__file__).resolve()
    plan = load_plan(here.parents[2] / "Content/Characters/Player/Pyrios/Materials")
    print("ORDER", plan["order"])
    print("TEXTURES", plan["textures"])
    for i, layer in enumerate(plan["layers"], 1):
        print("L%d" % i, layer["source"])
        for k, t in layer["textures"].items():
            print("   tex", k, t)
        for k in VECTOR_PARAMS:
            print("   vec", k, tuple(round(x, 5) for x in layer["vectors"][k]))
