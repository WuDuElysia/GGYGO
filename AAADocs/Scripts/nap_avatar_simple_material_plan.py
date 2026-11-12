"""@file nap_avatar_simple_material_plan.py
@brief 两个准确Simple MID的源程序、材质参数与显式UE移植配置；供FX原create-only批次消费。
"""
import hashlib
import json
import math
from pathlib import Path

from zzz_fx_asset_session import version_name
from zzz_fx_import_assets import plan_imports
from gen_nap_avatar_simple_hlsl import WEAPON, GHOST, GHOST_KEYWORDS, BASE
from pyrios_material_plan import additional_material_values

HERE = Path(__file__).resolve().parent
SCHEMA = "nap_avatar_simple_project/v2"
SHADER_PID = "7393264008099488228"
SHARED = "/Game/Characters/Shared/FX/ZZZ"
PROGRAM_FILE = HERE / "nap_avatar_simple_programs.json"
CONFIG_FILE = HERE.parent / "Assets/Pyrios/Rendering/Pyrios_Simple_Rendering.json"
GLOBALS_FILE = HERE.parent / "Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json"
TEXTURE_PIDS = ("8348973968083319186", "-2525522941621002874", "-7386911108408904686")
LIGHT_INPUTS = {"KeyLightDirectionWS": 4, "KeyLightColor": 4,
                "SceneLightStrength": 1, "KeyLightVisibility": 1}
PART_CODE = """uint id=min((uint)(VCol.a*255.0+_PartIDOffset+0.5),63u);
uint4 masks=(uint4)round(_ShowPartIDs);
return ((masks[id>>4u] & (1u<<(id&15u)))!=0u)?1.0:0.0;"""
STYLE_CODE = """uint flag=((uint)(VCol.b*255.0+0.5)>>5u)&1u;
return float2(flag!=0u?0.0:VCol.a,(float)flag);"""
WPO_CODE = """float width=min(max(_Outline,0.0)*max(_OutlineWidth,0.0)*UE_OutlineWidthCm,
UE_OutlineMaxOffsetCm);
return normalize(VertexNormalWS)*width;"""
DISPLAY_CODE = """return (BaseRGB + clamp(RimRaw*UE_RimGain,0.0,UE_RimMaxIntensity))*UE_OutputScale;"""


def _read(path):
    data = Path(path).read_bytes()
    return json.loads(data.decode("utf-8-sig")), hashlib.sha256(data).hexdigest()


def _number(value, name):
    if type(value) not in (int, float) or not math.isfinite(value) or abs(value) > 3.4028234663852886e38:
        raise ValueError("Simple材质值必须有限且可表示为float32：" + name)
    return float(value)


def _value(value, dim, name):
    if dim == 1:
        return _number(value, name)
    if not isinstance(value, (list, tuple)) or len(value) != dim:
        raise ValueError("Simple参数维度不同：" + name)
    return [_number(v, name) for v in value]


def project_configuration(config_path=CONFIG_FILE, globals_path=GLOBALS_FILE):
    """显式UE初值与共享Toon配置；预览初值不证明运行已接实际灯或System.Age。"""
    config, config_sha = _read(config_path)
    shared, shared_sha = _read(globals_path)
    if (config["mode"] != "ProjectConfiguredMaskedDoubleDraw"
            or config["color_mapping"] != "RawSerializedValues"
            or config["lighting_transport"] != "ExplicitOwnerSnapshot"
            or config["shadow_transport"] != "OwnerKeyLightVisibility"
            or config["outline_geometry"] != "BoundedUEVertexNormalWorldOffset"
            or config["source_runtime_certified"] is not False):
        raise ValueError("未支持的Simple工程配置")
    parameters = dict(config["parameters"])
    parameters.update({name: shared[name] for name in ("EntityParams", "EntityAmbient", "NormalYSign")})
    programs, program_sha = _read(PROGRAM_FILE)
    for program in programs.values():
        for name in program["parameters"]:
            if not name.startswith("Global_") or name in parameters:
                continue
            source_name, row = name[len("Global_"):].rsplit("_R", 1)
            if row != "0" or "_" + source_name not in shared:
                raise ValueError("Simple缺明确全局配置：" + name)
            parameters[name] = shared["_" + source_name]
    additional = shared["ProjectAdditionalLighting"]
    if additional["configured"] is not True:
        raise ValueError("Simple缺明确的局部灯配置")
    values = additional_material_values(additional["sample"])
    if values["scalars"]["AdditionalLightCount"] != 0:
        raise ValueError("Simple材质初值要求明确零局部灯；活动灯由真实宿主快照绑定")
    parameters.update(values["scalars"])
    parameters.update({name: list(value) for name, value in values["vectors"].items()})
    for name in ("UE_OutputScale", "UE_RimGain", "UE_RimMaxIntensity", "UE_OutlineWidthCm", "UE_OutlineMaxOffsetCm"):
        if _number(parameters[name], name) < 0:
            raise ValueError("Simple表现配置必须非负：" + name)
    if (not 0 < parameters["KeyLightProxyDistanceMeters"] < parameters["KeyLightProxyRadiusMeters"]
            or not 0 < parameters["UE_OutlineMaxOffsetCm"]
            or not 0 <= parameters["ExposureCompensationWeight"] <= 1
            or not 0 <= parameters["KeyLightVisibility"] <= 1
            or parameters["SceneLightStrength"] < 0):
        raise ValueError("Simple灯代理／阴影／轮廓／曝光配置无效")
    return dict(mode=config["mode"], parameters=parameters,
                inputs=[dict(path=str(Path(p).resolve()), sha256=s)
                        for p, s in ((config_path, config_sha), (globals_path, shared_sha), (PROGRAM_FILE, program_sha))])


def _material_value(saved, name, dim):
    if name.endswith("_ST") and name[:-3] in saved["m_TexEnvs"]:
        env = saved["m_TexEnvs"][name[:-3]]
        value = [env["m_Scale"]["X"], env["m_Scale"]["Y"], env["m_Offset"]["X"], env["m_Offset"]["Y"]]
    elif dim == 1:
        value = saved["m_Floats"][name]
    else:
        value = [saved["m_Colors"][name][channel] for channel in "rgba"]
    return _value(value, dim, name)


def make_plan(material_source, dependency_source, *, texture_targets, revision, configuration):
    """两MID沿准确dependency建立两role，不接收未知材质或替换已有MI。
    configuration必须显式传project_configuration结果；FX负责同NS绑定实际灯/年龄及重复槽绘制。
    """
    if not isinstance(revision, str) or not revision.strip() or configuration != project_configuration():
        raise ValueError("Simple需要明确revision和当前完整工程配置")
    material, material_sha = _read(material_source)
    deps, deps_sha = _read(dependency_source)
    matches = [(pid, row) for pid, row in deps.items() if isinstance(row, dict) and row.get("type") == "Material"
               and Path(row["nativeJson"]).resolve() == Path(material_source).resolve()]
    if len(matches) != 1 or matches[0][0] not in (WEAPON, GHOST):
        raise ValueError("Simple只接受准确Normal03 Weapon／Ghost源MID")
    pid, entry = matches[0]
    cab = "CAB-aaae0e8930cadde29956f3036cb74bc6" if pid == WEAPON else "CAB-503295c6de2682dd5d07068d8f5f5d41"
    if Path(material_source).resolve() != (BASE / "Assets/3077361824" / cab / "Material" / (pid + ".native.json")).resolve():
        raise ValueError("Simple MID不在原准确CAB")
    if (str(material["m_Shader"]["m_PathID"]) != SHADER_PID
            or deps[SHADER_PID]["name"] != "miHoYo/Character/NapAvatarSimple"
            or set(material["m_ShaderKeywords"].split()) != (set(GHOST_KEYWORDS) if pid == GHOST else set())):
        raise ValueError("Simple shader／关键字身份不符")
    saved = material["m_SavedProperties"]
    # 当前两个源MID四张基础图均使用Shader默认；不能把运行时猜测的角色图放进来。
    for name in ("_MainTex", "_LightTex", "_OtherDataTex", "_OtherDataTex2"):
        env = saved["m_TexEnvs"][name]
        if not env["m_Texture"]["IsNull"] or env["m_Texture"]["m_PathID"] != 0:
            raise ValueError("Simple基础图出现未支持的实际PPtr：" + name)
    imported = (plan_imports([dependency_source], revision=revision, selected_pids=TEXTURE_PIDS)
                if pid == GHOST else dict(assets={}, entries={}, targets=[]))
    if texture_targets != imported["assets"]:
        raise ValueError("Simple纹理目标须等于同revision准确导入计划")
    textures = {}
    for texture_pid, item in imported["entries"].items():
        native, native_sha = _read(deps[texture_pid]["nativeJson"])
        if native["m_Name"] != deps[texture_pid]["name"]:
            raise ValueError("Simple纹理源名与dependency不同")
        textures[texture_pid] = {**item, "pid": texture_pid, "native": deps[texture_pid]["nativeJson"],
                                 "native_sha256": native_sha, "png_sha256": item["identity"]["source_sha256"]}
    programs, program_sha = _read(PROGRAM_FILE)
    source = dict(material=str(Path(material_source).resolve()), material_sha256=material_sha,
                  dependency=str(Path(dependency_source).resolve()), dependency_sha256=deps_sha,
                  shader_pid=SHADER_PID, material_pid=pid, serialized_keywords=material["m_ShaderKeywords"].split(),
                  disabled_passes=material["m_DisabledShaderPasses"], enabled_pass_mask=material["m_EnabledPassMask"],
                  configuration=configuration, programs_sha256=program_sha)
    materials, bindings = [], {}
    for role in ("surface", "outline"):
        key = ("ghost_" if pid == GHOST else "weapon_") + role
        program = programs[key]
        params = {name: dict(dim=dim, value=_material_value(saved, name, dim), origin="source_material")
                  for name, dim in program["material_params"].items()}
        for name, dim in program["parameters"].items():
            if name == "_MainTex_ST":
                params[name] = dict(dim=4, value=_material_value(saved, name, 4), origin="source_material")
            else:
                params[name] = dict(dim=dim, value=_value(configuration["parameters"][name], dim, name),
                                    origin="project_configuration")
        for name in ("_Outline", "_OutlineWidth", "_PartIDOffset", "_ShowPartIDs"):
            dim = 4 if name == "_ShowPartIDs" else 1
            params[name] = dict(dim=dim, value=_material_value(saved, name, dim), origin="source_material")
        masks = params["_ShowPartIDs"]["value"]
        offset = params["_PartIDOffset"]["value"]
        if any(v != int(v) or not 0 <= v <= 65535 for v in masks) or offset != int(offset) or not 0 <= offset <= 63:
            raise ValueError("Simple源PartID位集或偏移无效")
        for name, value in configuration["parameters"].items():
            if name.startswith(("UE_", "Additional")) or name == "ExposureCompensationWeight":
                dim = 4 if isinstance(value, list) else 1
                params[name] = dict(dim=dim, value=_value(value, dim, name), origin="project_configuration")
        bound_textures = {}
        for name in program["textures"]:
            env = saved["m_TexEnvs"][name]
            texture_pid = str(env["m_Texture"]["m_PathID"])
            if texture_pid not in textures or env["m_Texture"]["IsNull"]:
                raise ValueError("Simple缺真实纹理：" + name)
            bound_textures[name] = texture_targets[texture_pid]
        # 保留原未启用Rim覆盖图与完整SavedProperties来源；它不冒充本变体活跃采样。
        properties = dict(BlendMode="BLEND_Masked", ShadingModel="MSM_Unlit", TwoSided=True,
                          OpacityMaskClipValue=0.5, bDisableDepthTest=False,
                          bUsedWithNiagaraMeshParticles=True, bUsedWithNiagaraSprites=False,
                          bAutomaticallySetUsageInEditor=False, bHasPixelAnimation=True)
        spec = dict(role=role, properties=properties, params=params, textures=bound_textures,
                    shader=program, part_code=PART_CODE, style_code=STYLE_CODE,
                    wpo=WPO_CODE if role == "outline" else None,
                    display=DISPLAY_CODE, face_mask="back" if role == "outline" else ("front" if pid == WEAPON else "both"),
                    source_render_state={n: saved["m_Floats"][n] for n in ("_ZTestPreZ", "_ZWritePreZ", "_Cull")})
        identity = dict(schema=SCHEMA, source=source, revision=revision, spec=spec)
        spec["master"] = SHARED + "/Materials/" + version_name("M_NapAvatarSimple_" + key, identity)
        spec["instance"] = SHARED + "/MaterialInstances/" + version_name("MI_Pyrois_Simple_" + key, identity)
        materials.append(spec)
        bindings[role] = spec["instance"]
    targets = imported["targets"] + [value for spec in materials for value in (spec["master"], spec["instance"])]
    return dict(schema=SCHEMA, revision=revision, source_identity=source, textures=textures,
                materials=materials, bindings={pid: bindings}, targets=sorted(targets),
                runtime_inputs=dict(main_light=LIGHT_INPUTS, effect_age={"DP0.x": "System.Age"},
                    additional_lights="AdditionalLightCount/AdditionalLightGlobalIntensity＋四槽Position/Direction/Attenuation/Color float4",
                    source_clip="原_DitherAlpha/_DitherAlpha2/_DitherEffectAlpha；未证明的MPB/cue不自动补",
                    dynamic_parameter_mask=0x0001, transport="灯沿私有MID登记；Age沿原Emitter动态材质参数，不另建模拟"),
                bounds=dict(mode="WorldCentimeterClampedOffset", max_outline_offset_cm=configuration["parameters"]["UE_OutlineMaxOffsetCm"],
                    source_geometry_required=True, emitter_must_transform_world_margin_to_local=True),
                equivalence=dict(mode=configuration["mode"], source_runtime_certified=False, visual_calibrated=False,
                    differences=["原PS位模式数学保留，entity/主灯代理与粗阴影由真实Owner输入",
                        "Color先按明确RawSerializedValues配置；原游戏GPU颜色上传/运行MPB值未证，仍需原图校准",
                        "原CSM采样改OwnerKeyLightVisibility，不宣称逐像素或原影图等价",
                        "原MRT边缘光编码前输出由可调UE Emissive合成，源Deferred消费者未证",
                        "UE Masked深度/背面双draw替代源PreZ/Equal/Stencil调度，原状态另存",
                        "轮廓用有界UE世界法线外扩，原屏幕宽度/深度偏移未冒称复刻",
                        "原VP PartID遮蔽改顶点可见度插值Mask，UE原生Velocity代源前帧流"]),
                unresolved_source_runtime=["实际游戏pass/global选择", "entity/MPB运行覆盖", "宿主/年龄/fade/cue/stop绑定"])


def validate_plan(plan):
    """按准确源与当前生成程序重建同一计划，不运行UE或保存资产。"""
    if not isinstance(plan, dict) or plan.get("schema") != SCHEMA:
        raise ValueError("不是当前Simple源程序移植合同")
    source = plan["source_identity"]
    expected = make_plan(source["material"], source["dependency"],
                         texture_targets={pid: item["path"] for pid, item in plan["textures"].items()},
                         revision=plan["revision"], configuration=source["configuration"])
    if plan != expected:
        raise ValueError("Simple计划与源程序／参数／渲染配置不一致")
    return plan
