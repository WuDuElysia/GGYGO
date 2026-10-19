"""@file nap_avatar_simple_material_plan.py
@brief 首个 Ghost 资源专项的纯离线材质计划；不读取 Shader/Raw，不操作 UE。

保留已审计源材质和裁剪算法，明确采用 UE 对应的受光、深度和运动矢量。
返回数据供 FX 的完整 create-only 批次消费；不决定实例时序或动态 Fade。
"""
import hashlib
import json
import math
import re
from pathlib import Path

from zzz_fx_asset_session import version_name
from zzz_fx_import_assets import plan_imports

SCHEMA = "nap_avatar_simple_ue_ghost/v1"
MATERIAL_PID = "1604852325208651105"
SHADER_PID = "7393264008099488228"
MATERIAL_SHA = "49c51577019ded756decc34b03786f90342eef36ed0c42a4bb77c743d7b0b3f6"
DEPENDENCY_SHA = "2043160ab98e68e66db323b32f48dd10d74b59db1ae9be95da17d11bfda81222"
KEYWORDS = ("_EXTRA_DITHER_EFFECT", "_FX_CLIP", "_FX_UNCLIP_SCREEN_IMAGE_OVERRIDE_2_TONE", "_OVERRIDE_OUTLINE")
TEXTURE_PIDS = ("8348973968083319186", "-2525522941621002874", "-7386911108408904686")
SHARED = "/Game/Characters/Shared/FX/ZZZ"
SCALARS = ("_DitherAlpha", "_DitherAlpha2", "_DitherEffectAlpha", "_ScreenImage", "_ScreenScale",
           "_OverrideOutline", "_OverrideOutlineUseUV2", "_Outline", "_OutlineWidth", "_Metallic",
           "_SpecIntensity", "_Glossiness", "_RimGlow", "_OverrideRimGlow")
VECTORS = ("_Color", "_ScreenColor", "_OutlineColor", "_OverrideOutlineColor",
           "_OverrideOutlineSpeed", "_ScreenImageUvMove")
# 对应效果的初始配置，尚未经过 UE 画面校准；与原 HDR 值分别保存。
UE_DEFAULTS = {"UE_SurfaceLitScale": 0.25, "UE_SurfaceEmissionScale": 0.1,
               "UE_OutlineEmissionScale": 0.5, "UE_OutlineWidthCm": 0.2}
UE_RANGES = {"UE_SurfaceLitScale": (0, 1), "UE_SurfaceEmissionScale": (0, 8),
             "UE_OutlineEmissionScale": (0, 8), "UE_OutlineWidthCm": (0, 2)}
THRESHOLDS = (0.058824, 0.529412, 0.176471, 0.647059, 0.764706, 0.294118, 0.882353, 0.411765,
              0.235294, 0.705882, 0.117647, 0.588235, 0.941176, 0.470588, 0.823529, 0.352941)
# 来自既有 fp104/fp920 缓存反汇编；不认证 GPU binary 或实际游戏 pass 选择。
DITHER_CODE = """const float thresholds[16] = {0.058824,0.529412,0.176471,0.647059,
0.764706,0.294118,0.882353,0.411765,0.235294,0.705882,0.117647,0.588235,
0.941176,0.470588,0.823529,0.352941};
uint2 p = uint2(PixelPosition.xy);
float threshold = thresholds[((p.x & 3u) << 2u) | (p.y & 3u)];
float alpha = _DitherAlpha * _DitherAlpha2;
float coverage = 1.0;
if (_DitherEffectAlpha < 0.941176 && _DitherEffectAlpha < threshold) coverage = 0.0;
if (alpha < 0.941176 && alpha < threshold) coverage = 0.0;
return coverage;"""
SURFACE_CODE = """float3 base = _Color.rgb;
float2 screenUV = NormalView.xy * float2(0.5,-0.5) + 0.5;
screenUV = screenUV * _ScreenTex_ST.xy + _ScreenTex_ST.zw;
screenUV += _ScreenImageUvMove.xy * Time + _ScreenImageUvMove.zw;
float4 screen = Texture2DSample(_ScreenTex, _ScreenTexSampler, screenUV) * _ScreenColor;
float2 maskUV = UV2 * _ScreenMask_ST.xy + _ScreenMask_ST.zw;
float mask = Texture2DSample(_ScreenMask, _ScreenMaskSampler, maskUV).r;
float3 image = lerp(base, screen.rgb, screen.a);
return (_ScreenImage > 0.5) ? lerp(base, image, mask) : base;"""
OUTLINE_CODE = """float2 uv = (_OverrideOutlineUseUV2 > 0.5) ? UV2 : UV0;
uv = uv * _OverrideOutlineTex_ST.xy + _OverrideOutlineTex_ST.zw;
uv += _OverrideOutlineSpeed.xy * Time;
float4 noise = Texture2DSample(_OverrideOutlineTex, _OverrideOutlineTexSampler, uv);
float3 base = _Color.rgb * _OutlineColor.rgb;
float3 overrideColor = noise.rgb * _OverrideOutlineColor.rgb;
return (_OverrideOutline > 0.5) ? lerp(base, overrideColor, noise.a * _OverrideOutlineColor.a) : base;"""
WPO_CODE = "return normalize(VertexNormalWS) * (_Outline * _OutlineWidth * UE_OutlineWidthCm);"


def _read(path):
    path = Path(path)
    data = path.read_bytes()
    return json.loads(data.decode("utf-8-sig")), hashlib.sha256(data).hexdigest()


def _number(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise ValueError("非有限数值参数: " + name)
    return float(value)


def _package(path, directory):
    if not isinstance(path, str) or not re.fullmatch(re.escape(directory) + r"/[A-Za-z0-9_]+", path):
        raise ValueError("无效或越界的资源目标: " + repr(path))
    return path


def dither_coverage(x, y, effect_alpha, alpha, alpha2):
    """源 16-cell 双裁剪判断的 CPU 参考；只检验静态覆盖率，不生成 Fade。"""
    t = THRESHOLDS[((int(x) & 3) << 2) | (int(y) & 3)]
    a = alpha * alpha2
    return int(not (effect_alpha < 0.941176 and effect_alpha < t)
               and not (a < 0.941176 and a < t))


def shader_contract(role):
    """材质图使用的既有审计算法及明确 UE 对应投影/背面轮廓策略。"""
    if role not in ("surface", "outline"):
        raise ValueError("未知材质角色: " + repr(role))
    return {"coverage": DITHER_CODE, "color": SURFACE_CODE if role == "surface" else OUTLINE_CODE,
            "wpo": None if role == "surface" else WPO_CODE,
            "face_mask": "both" if role == "surface" else "back_faces_only"}


def make_plan(material_source, dependency_source, *, texture_targets, revision, ue_parameters=None):
    """@return 固定源身份、纹理导入项、两材质及 MIC、绑定和未闭合来源。
    @param texture_targets 同 revision 的 plan_imports 返回的三个准确纹理包。
    @param ue_parameters 仅允许公开 UE 对应参数；不接收 entity/cue/Fade 值。
    """
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError("资源 revision 必须明确且非空")
    material, sha = _read(material_source)
    deps, deps_sha = _read(dependency_source)
    entry = deps.get(MATERIAL_PID)
    if sha != MATERIAL_SHA or deps_sha != DEPENDENCY_SHA or not entry or entry["type"] != "Material":
        raise ValueError("本资源专项只接受已冻结的 Ghost 材质身份")
    if Path(entry["nativeJson"]).resolve() != Path(material_source).resolve():
        raise ValueError("材质来源与 dependency 的 nativeJson 不一致")
    if str(material["m_Shader"]["m_PathID"]) != SHADER_PID or deps[SHADER_PID]["name"] != "miHoYo/Character/NapAvatarSimple":
        raise ValueError("未支持的 Shader family/身份")
    if set(material["m_ShaderKeywords"].split()) != set(KEYWORDS):
        raise ValueError("材质关键字与已审计模式不一致")
    imported = plan_imports([dependency_source], revision=revision, selected_pids=TEXTURE_PIDS)
    if texture_targets != imported["assets"]:
        raise ValueError("三个纹理目标必须等于同 revision 的准确 create-only 导入计划")
    textures = {}
    for pid, item in imported["entries"].items():
        native, native_sha = _read(deps[pid]["nativeJson"])
        if native["m_Name"] != deps[pid]["name"]:
            raise ValueError("纹理 native 身份不一致: " + pid)
        textures[pid] = {**item, "pid": pid, "native": deps[pid]["nativeJson"], "native_sha256": native_sha,
                         "png_sha256": item["identity"]["source_sha256"]}
        _package(item["path"], SHARED + "/Textures")
    saved = material["m_SavedProperties"]
    params = {n: {"dim": 1, "value": _number(saved["m_Floats"][n], n), "origin": "source_material"} for n in SCALARS}
    for n in VECTORS:
        params[n] = {"dim": 4, "value": [_number(saved["m_Colors"][n][k], n) for k in "rgba"], "origin": "source_material"}
    texture_params = {}
    for n in ("_ScreenTex", "_ScreenMask", "_OverrideOutlineTex", "_OverrideRimGlowTexFX"):
        env = saved["m_TexEnvs"][n]
        pid = str(env["m_Texture"]["m_PathID"])
        if pid not in textures or env["m_Texture"]["IsNull"]:
            raise ValueError("实际绑定纹理缺失: " + n)
        texture_params[n] = texture_targets[pid]
        params[n + "_ST"] = {"dim": 4, "value": [env["m_Scale"]["X"], env["m_Scale"]["Y"],
                                                 env["m_Offset"]["X"], env["m_Offset"]["Y"]], "origin": "source_material"}
    overrides = {} if ue_parameters is None else ue_parameters
    if not isinstance(overrides, dict) or set(overrides) - set(UE_DEFAULTS):
        raise ValueError("只允许公开 UE 调色/受光/描边参数，禁止填入源 runtime 伪值")
    for n, default in UE_DEFAULTS.items():
        v = _number(overrides.get(n, default), n)
        lo, hi = UE_RANGES[n]
        if not lo <= v <= hi:
            raise ValueError("UE 参数越界: " + n)
        params[n] = {"dim": 1, "value": v, "origin": "ue_equivalent_uncalibrated"}
    source = {"material_pid": MATERIAL_PID, "material": str(Path(material_source)), "material_sha256": sha,
              "dependency": str(Path(dependency_source)), "dependency_sha256": deps_sha, "shader_pid": SHADER_PID,
              "shader_family": "miHoYo/Character/NapAvatarSimple", "keywords": list(KEYWORDS),
              "disabled_passes": material["m_DisabledShaderPasses"], "enabled_pass_mask": material["m_EnabledPassMask"]}
    materials, binding = [], {}
    for role in ("surface", "outline"):
        properties = {"BlendMode": "BLEND_Masked", "ShadingModel": "MSM_DefaultLit" if role == "surface" else "MSM_Unlit",
                      "TwoSided": True, "OpacityMaskClipValue": 0.5, "bDisableDepthTest": False,
                      "bUsedWithNiagaraMeshParticles": True, "bUsedWithNiagaraSprites": False,
                      "bAutomaticallySetUsageInEditor": False, "bHasPixelAnimation": True}
        spec = {"role": role, "properties": properties, "params": params, "textures": texture_params,
                "shader": shader_contract(role)}
        identity = {"source": source, "revision": revision, "spec": spec, "schema": SCHEMA}
        spec["master"] = SHARED + "/Materials/" + version_name("M_NapAvatarSimple_Ghost_" + role, identity)
        spec["instance"] = SHARED + "/MaterialInstances/" + version_name("MI_Pyrois_Ghost_" + role, identity)
        materials.append(spec)
        binding[role] = spec["instance"]
    targets = imported["targets"] + [p for m in materials for p in (m["master"], m["instance"])]
    return {"schema": SCHEMA, "revision": revision, "source_identity": source, "textures": textures,
            "materials": materials, "bindings": {MATERIAL_PID: binding}, "targets": sorted(targets),
            "equivalence": {"mode": "ue_native_lit_masked_mesh", "source_runtime_certified": False,
                "visual_calibrated": False, "source_outputs": ["SV_Target0", "SV_Target1", "SV_Target2", "SV_Target3"],
                "default_textures": {"white": ["_MainTex", "_OtherDataTex", "_OtherDataTex2", "_CharacterRampTex"], "linearGray": ["_LightTex"]},
                "differences": ["UE DefaultLit 替代源 toon/主灯/附加灯及影图响应；自发光独立",
                    "当前材质不采样 normal map/anisotropy；使用 UE normal/TBN，源 tangent4 的执行未验证",
                    "UE Masked 深度替代原 Outline/PreZ/Equal/Stencil/四 RT 合成，不保证原 pass 顺序",
                    "UE view-normal 投影屏幕图案；原 ScreenScale/相机矩阵投影未复刻",
                    "UE 世界厘米轮廓外扩和背面 OpacityMask；不复刻原屏幕轮廓宽度/阴影染色",
                    "UE 原生 velocity/TSR；不输入 Unity TEXCOORD4.xyz previous position",
                    "UE Time 仅驱动已知 UV scroll；不提供源 Fade/cue/Stop；halo 依 UE 后处理",
                    "源 OverrideRimGlow=0；其绑定纹理保留但当前模式不启用该分支；源运行时 rim 全局量未复刻"]},
            "required_inputs": {"static": ["准确三个纹理与材质参数", "POSITION/NORMAL/UV0/UV2，源其它流由 FX 保留"],
                "ue_managed": ["scene lighting/shadows", "masked depth/occlusion", "instance previous transform/velocity"],
                "runtime_entity_mode": "UE vertex factory，未模拟源 NapEntityGPUData 或声称源 zero-entity"},
            "unresolved_source_runtime": ["actual pass/keyword selection", "entity/MPB/composite", "cue/anchor/TRS/Follow",
                "Legacy Age consumer", "dynamic Dither/Fade", "source Stop/tail ownership"]}


def validate_plan(plan):
    """完整重新生成离线计划以拒绝路径、算法、参数或来源被改写；不调用 UE。"""
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("未知 Ghost 材质计划")
    s = plan["source_identity"]
    ue = {n: plan["materials"][0]["params"][n]["value"] for n in UE_DEFAULTS}
    targets = {pid: item["path"] for pid, item in plan["textures"].items()}
    expected = make_plan(s["material"], s["dependency"], texture_targets=targets, revision=plan["revision"], ue_parameters=ue)
    if plan != expected:
        raise ValueError("Ghost 材质计划与源身份/完整静态契约不一致")
    return plan
