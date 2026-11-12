"""只读选择原生 Shader 证据，供独立候选预览或显式 UE 等效生产环境。

执行入口的 Pass 与全局关键字必须显式指定；审计逐程序区分完整材质输入和源声明。
候选存在不证明原游戏运行态选择；派生实现另记身份，不覆盖源文件。
"""
import hashlib
from functools import lru_cache
from copy import deepcopy
import json
import math
import re
import struct
from pathlib import Path

import zzz_dxbc_hlsl as T
import zzz_fx_ue_equivalent as UE


class NativeShaderError(ValueError):
    pass


TRANSMITTANCE_PREVIEW = "ue_fullres_transmittance_fragment_preview"
PROJECT_PURPOSE = "project_configured_source_particles"
PROJECT_FULLRES = "project_fullres_source_transmittance"
PROJECT_SHADOW = "project_native_shadow_fullres"
PROJECT_DEPTH_VELOCITY = "project_native_depth_velocity_fullres"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@lru_cache(maxsize=16)
def _native_shader_state(path, source_sha256):
    """仅缓存原文件摘要对应的必要状态，避免逐材质反复解析数百MiB程序Blob。

    调用方每次重核原文件摘要；整批prepare结束清理，既不缓存Source Ready也不保程序正文。
    """
    raw = Path(path).read_bytes()
    if hashlib.sha256(raw).hexdigest() != source_sha256:
        raise NativeShaderError("Native Shader changed while reading its state: " + path)
    form = json.loads(raw.decode("utf-8-sig"))["m_ParsedForm"]
    return {"m_Name": form["m_Name"], "m_PropInfo": form["m_PropInfo"], "m_SubShaders": [
        {"m_Passes": [{"m_State": p["m_State"]} for p in sub["m_Passes"]]} for sub in form["m_SubShaders"]]}


def clear_native_shader_states():
    """归还离线准备批次持有的只读派生状态。"""
    _native_shader_state.cache_clear()


def native_payload_varyings(program, provider, bindings, outputs, source_identity):
    """仅证明copy、draw统一选择和字面恒等乘；其余输出继续使用原顶点插值。

    bindings由实际Native Ribbon输入映射提供。局部来源分析不执行Shader；
    返回代码仍由原T.translate从同一VP指令生成，不把非线性顶点运算迁往PS。
    """
    ctx = T.Ctx(program, "n", provider)
    state, fixed_globals = {}, set()

    def source(operand, position):
        component = operand.comps([position])[0]
        value = None
        if operand.kind in ("r", "o"):
            value = state.get((operand.kind + str(operand.idx), component))
        elif operand.kind == "v" and ("v" + str(operand.idx), component) in bindings:
            value = ("payload", None, frozenset())
        elif operand.kind == "l":
            token = operand.lit[position] if len(operand.lit) > 1 else operand.lit[0]
            if not token.lower().startswith(("0x", "-0x")) and any(mark in token.lower() for mark in (".", "e", "inf", "nan")):
                constant = float(token)
            else:
                constant = struct.unpack("<f", struct.pack("<I", int(token, 0) & 0xFFFFFFFF))[0]
            value = ("uniform", constant, frozenset())
        elif operand.kind == "cb" and re.fullmatch(r"\d+", operand.arr):
            cbname, parameter, row, index = ctx.resolve_cb(operand.idx, int(operand.arr), component)
            if cbname == ctx.material_cb and parameter["kind"] == "V" and row is None:
                value = ("uniform", None, frozenset())
            else:
                configured = provider.get(parameter["name"])
                if configured is not None:
                    text = configured["rows"][row or 0]
                    match = re.fullmatch(r"float4\(\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*,\s*([-+0-9.eE]+)\s*\)", text)
                    allowed = configured.get("comps", "xyzw")
                    allowed = allowed[row or 0] if isinstance(allowed, list) else allowed
                    if match and "xyzw"[index] in allowed:
                        constant = float(match[index + 1])
                        if math.isfinite(constant):
                            value = ("uniform", constant, frozenset())
                            fixed_globals.add((parameter["name"], row or 0, text))
        if value is not None and (operand.neg or operand.abs):
            if value[0] != "uniform":
                return None
            number = value[1]
            if number is not None:
                number = abs(number) if operand.abs else number
                number = -number if operand.neg else number
            value = ("uniform", number, value[2])
        return value

    depth = 0
    for index, line in enumerate(program["asm"]):
        if line.startswith(("dcl_", "vs_")):
            continue
        op, saturated, operands = T.split_instr(line)
        if op.startswith("if") or op == "loop":
            depth += 1
            continue
        if op in ("endif", "endloop"):
            depth -= 1
            continue
        if op == "ret":
            if depth:
                return {}
            break
        if op == "else":
            continue
        lowered = T.translate_ins(ctx, op, saturated, operands)
        updates = {}
        if depth == 0 and operands and operands[0].kind in ("r", "o"):
            destination = operands[0]
            for component in destination.swz or "xyzw":
                values = [source(operand, "xyzw".index(component)) for operand in operands[1:]]
                value = None
                if not saturated and op == "mov" and len(values) == 1:
                    value = values[0]
                elif not saturated and op == "movc" and len(values) == 3:
                    condition, left, right = values
                    if condition is not None and condition[0] == "uniform" and left is not None and right is not None:
                        value = ("payload" if "payload" in (left[0], right[0]) else "uniform", None, frozenset())
                elif not saturated and op == "mul" and len(values) == 2 and all(v is not None for v in values):
                    left, right = values
                    if left[0] == "uniform" and left[1] == 1.0:
                        value = right
                    elif right[0] == "uniform" and right[1] == 1.0:
                        value = left
                elif op in ("lt", "ge", "eq", "ne") and values and all(v is not None and v[0] == "uniform" for v in values):
                    value = ("uniform", None, frozenset())
                if value is not None:
                    origins = frozenset({index}).union(*(v[2] for v in values if v is not None))
                    value = (value[0], value[1], origins)
                updates[(destination.kind + str(destination.idx), component)] = value
        # 分支/未知运算及多目标写均按原lowerer给出的真实写集失效，不继承旧来源。
        for register, component, _ in lowered.defs:
            state[(register, component)] = updates.get((register, component))

    result = {}
    for register, components in outputs.items():
        lanes = "".join(c for c in "xyzw" if c in components)
        values = [state.get(("o" + str(register), c)) for c in lanes]
        if not values or any(value is None for value in values):
            continue
        translated = T.translate(program, "n", provider, {register: lanes})
        if translated["textures"] or any(tuple(value) not in bindings for value in translated["live_inputs"]):
            continue
        live = {}
        for input_register, component in translated["live_inputs"]:
            live.setdefault(input_register, {})[component] = bindings[(input_register, component)]
        seeds = []
        for input_register, fields in sorted(live.items()):
            seeds.append("uint4 n%s = asuint(float4(%s));" % (input_register, ",".join(
                fields[c]["builtin"] + "." + fields[c]["component"] if c in fields else "0.0" for c in "xyzw")))
        code = translated["code"]
        # 原翻译器保留已解析的数组声明；未读声明不引入额外、未消费的uniform输入。
        code = "\n".join(line for line in code.splitlines() if not (
            (match := re.match(r"\s*const float4 (\w+)\[", line)) and len(re.findall(r"\b" + match[1] + r"\b", code)) == 1))
        code = "\n".join(seeds) + "\n" + code + "\nreturn asfloat(no%d);" % register
        origins = sorted(set().union(*(value[2] for value in values)))
        result[register] = {"schema": "GGYGO.SourceProvenNativeVarying/v1", "components": lanes,
            "inputs": sorted({field["builtin"] for fields in live.values() for field in fields.values()}) + list(translated["mat_params"]),
            "code": code, "proof": {"source_program": source_identity,
                "program_state_sha256": hashlib.sha256(json.dumps({key: program[key]
                    for key in ("asm", "in", "out", "bind")}, sort_keys=True).encode()).hexdigest(),
                "provider_sha256": hashlib.sha256(json.dumps(provider, sort_keys=True).encode()).hexdigest(),
                "output_register": register, "components": lanes, "scalar_type": "float32",
                "native_interpolation": "default_perspective", "uniform_scope": "MaterialParametersWithoutCustomPrimitiveData",
                "uniform_parameters": dict(translated["mat_params"]),
                "rule": "CopyUniformSelectLiteralOne", "source_instructions": [{"index": i, "asm": program["asm"][i]} for i in origins],
                "native_inputs": [{"register": name, "source_component": c, **field} for name, fields in sorted(live.items()) for c, field in sorted(fields.items())],
                "fixed_global_rows": [list(value) for value in sorted(fixed_globals)
                    if (value[0], value[1]) in {(name, row) for name, row, _ in translated["globals"]}],
                "code_sha256": hashlib.sha256(code.encode()).hexdigest()}}
    return result


def project_camera_provider(provider, configuration, shader_pid):
    """明确UE当前View的最小相机输入；其它分量仍由翻译器拒绝，未还原Unity运行相机。"""
    if not isinstance(configuration, dict) or set(configuration) != {"mode", "decision_reference", "screen_position_semantics"} \
            or configuration["mode"] != "NativeCurrentViewBindings" or not configuration["decision_reference"] \
            or not isinstance(configuration["screen_position_semantics"], dict) \
            or any(not isinstance(sid, str) or type(index) is not int or index < 0
                   for sid, index in configuration["screen_position_semantics"].items()):
        raise NativeShaderError("Current-view adapter requires its explicit source semantic configuration")
    result = deepcopy(provider)
    result["unity_CameraProjection"] = {"rows": ["float4(0,0,0,0)",
        "float4(0,View.ViewToClip[1][1],0,0)", "float4(0,0,0,0)", "float4(0,0,0,0)"],
        "comps": ["", "y", "", ""], "disabled_by": {}}
    result["unity_OrthoParams"] = {"rows": ["float4(0,0,0,View.ViewToClip[3][3])"], "comps": "w", "disabled_by": {}}
    return result, configuration["screen_position_semantics"].get(str(shader_pid))


def properties(form):
    types = {0: "Color", 1: "Vector", 2: "Float", 3: "Range", 4: "2D"}
    result = {}
    for prop in form["m_PropInfo"]["m_Props"]:
        kind = prop["m_Type"]
        if kind not in types or prop["m_Name"] in result:
            raise NativeShaderError("Unsupported/duplicate native Shader property: " + prop["m_Name"])
        values = prop["m_DefValue"]
        result[prop["m_Name"]] = {
            "type": types[kind], "attrs": " ".join("[" + a + "]" for a in prop["m_Attributes"]),
            "default": values if kind in (0, 1) else values[0] if kind in (2, 3) else None,
            "tex_default": prop["m_DefTexture"]["m_DefaultName"] if kind == 4 else None,
        }
    return result


def state_value(value, floats, props):
    name = value["name"]
    if name and name != "<noninit>":
        if name in floats:
            number = floats[name]
        elif name in props and isinstance(props[name]["default"], (int, float)):
            number = props[name]["default"]
        else:
            raise NativeShaderError("Missing source render-state property: " + name)
    else:
        number = value["val"]
    if not isinstance(number, (int, float)) or not math.isfinite(number):
        raise NativeShaderError("Nonfinite/invalid source render state: " + str(name))
    return number


def keyword_enum_selection(material, props, property_names):
    """按明确列出的原 KeywordEnum 属性值选择项目变体，保留序列化关键词证据。"""
    selected = set((material.get("m_ShaderKeywords") or "").split())
    evidence = {}
    for name in property_names:
        prop = props[name]
        attributes = re.findall(r'\[KeywordEnum\(([^)]*)\)\]', prop["attrs"])
        if len(attributes) != 1:
            raise NativeShaderError("需要唯一原 KeywordEnum 属性声明: " + name)
        options = [value.strip() for value in attributes[0].split(",")]
        value = material["m_SavedProperties"]["m_Floats"][name]
        if not isinstance(value, (int, float)) or not math.isfinite(value) \
                or int(value) != value or not 0 <= value < len(options):
            raise NativeShaderError("原 KeywordEnum 索引无效: " + name)
        family = {(name + "_" + option).replace(" ", "_").upper() for option in options}
        keyword = (name + "_" + options[int(value)]).replace(" ", "_").upper()
        if selected & family and selected & family != {keyword}:
            raise NativeShaderError("原序列化关键词与枚举值冲突: " + name)
        selected.add(keyword)
        evidence[name] = {"source_value": value, "keyword": keyword,
                          "source_attribute": attributes[0], "source_runtime_application_verified": False}
    return sorted(selected), evidence


def project_depth_velocity_contract(value, material_pid=None):
    """@brief 校验显式的原生额外 Depth/Velocity 移植配置，未配置时返回 None。

    @param value 完整源材质身份、原状态及 UE 阈值／阶段／Renderer／全局前置。
    @param material_pid 调用方已核实的源材质身份；传入时必须严格配对。
    @return 独立配置副本；不写全局值、不拥有粒子历史，也不证明实际 GPU 执行。
    """
    if value is None:
        return None
    fields = {"schema", "material_pid", "source_reference", "source_render_state", "opacity_mask_clip_value",
              "motion_vector_setting", "depth_stage", "runtime_cvars"}
    if not isinstance(value, dict) or set(value) != fields \
            or value["schema"] != "GGYGO.ProjectNativeDepthVelocity/v1":
        raise NativeShaderError("额外Depth/Velocity缺完整明确合同")
    if not isinstance(value["material_pid"], str) or not re.fullmatch(r"-?\d+", value["material_pid"]) \
            or material_pid is not None and value["material_pid"] != str(material_pid) \
            or not isinstance(value["source_reference"], str) or not value["source_reference"]:
        raise NativeShaderError("额外Depth/Velocity缺准确材质身份／政策来源")
    source = value["source_render_state"]
    if not isinstance(source, dict) or set(source) != {"cull", "zwrite", "ztest"} \
            or any(type(v) not in (int, float) or not math.isfinite(v) for v in source.values()) \
            or source["cull"] not in (0, 2) or source["zwrite"] != 1 or source["ztest"] != 4:
        raise NativeShaderError("额外Depth/Velocity仅接已核源ZWrite1／LEqual状态")
    cutoff = value["opacity_mask_clip_value"]
    if type(cutoff) not in (int, float) or not math.isfinite(cutoff) or not 0.0 <= cutoff <= 1.0:
        raise NativeShaderError("额外Depth/Velocity缺有限显式透明度阈值")
    expected_cvars = {"r.Translucency.Velocity": 1, "r.Translucency.EarlyVelocityPass": 0, "r.VelocityOutputPass": 0}
    if value["motion_vector_setting"] != "Precise" or value["depth_stage"] != "LateTranslucentVelocity" \
            or not isinstance(value["runtime_cvars"], dict) or value["runtime_cvars"] != expected_cvars \
            or any(type(v) is not int for v in value["runtime_cvars"].values()):
        raise NativeShaderError("额外Depth/Velocity需要明确Precise／Late及三项运行前置")
    return deepcopy(value)


def render_state(state, floats, props, execution_environment=None, project_depth_bias=None, depth_velocity=None):
    if execution_environment not in (None, TRANSMITTANCE_PREVIEW, UE.MODE, PROJECT_FULLRES, PROJECT_SHADOW, PROJECT_DEPTH_VELOCITY):
        raise NativeShaderError("Unknown native preview execution environment: " + str(execution_environment))
    depth_velocity = project_depth_velocity_contract(depth_velocity)
    if (execution_environment == PROJECT_DEPTH_VELOCITY) != (depth_velocity is not None):
        raise NativeShaderError("额外Depth/Velocity环境与完整合同未配对")
    value = lambda item: state_value(item, floats, props)
    blend = state["rtBlend"][0]
    if execution_environment in (None, PROJECT_SHADOW, PROJECT_DEPTH_VELOCITY):
        if state["rtSeparateBlend"] or value(blend["blendOp"]) != 0 or value(blend["colMask"]) != 15:
            raise NativeShaderError("Independent RT blend, blend operation or color mask requires an explicit output environment")
        if execution_environment in (PROJECT_SHADOW, PROJECT_DEPTH_VELOCITY):
            expected = {"srcBlend": 1, "destBlend": 10, "srcBlendAlpha": 8, "destBlendAlpha": 1,
                        "blendOp": 0, "blendOpAlpha": 0, "colMask": 15}
            if {k: value(blend[k]) for k in expected} != expected:
                raise NativeShaderError("额外Depth/Velocity需要原完整预乘RGBA混合状态" if execution_environment == PROJECT_DEPTH_VELOCITY
                                        else "Project native shadow requires the reviewed complete source RGBA blend state")
    else:
        expected = {"srcBlend": 1, "destBlend": 5, "srcBlendAlpha": 7, "destBlendAlpha": 0,
                    "blendOp": 0, "blendOpAlpha": 0, "colMask": 15}
        if any(k not in blend for k in expected):
            raise NativeShaderError("Transmittance preview requires complete native Target0 blend state")
        actual = {k: value(blend[k]) for k in expected}
        if actual != expected:
            raise NativeShaderError("Transmittance preview requires One/SrcAlpha, DstAlpha/Zero, Add/Add, RGBA: " + repr(actual))
    for stencil in ("stencilOp", "stencilOpFront", "stencilOpBack"):
        item = state[stencil]
        if value(item["comp"]) not in (0, 8) or any(value(item[k]) != 0 for k in ("pass", "fail", "zFail")):
            raise NativeShaderError("Active native stencil requires its render-state contract")
    source_bias = {"factor": value(state["offsetFactor"]), "units": value(state["offsetUnits"])}
    if not all(math.isfinite(v) for v in source_bias.values()):
        raise NativeShaderError("Native depth offset requires finite source factor/units")
    if project_depth_bias is not None and (not isinstance(project_depth_bias, dict)
            or set(project_depth_bias) != {"mode", "decision_reference"}
            or project_depth_bias["mode"] != "PreserveWithoutHardwareInjection"
            or not isinstance(project_depth_bias["decision_reference"], str) or not project_depth_bias["decision_reference"]):
        raise NativeShaderError("Project depth-bias policy must explicitly preserve source values without injection")
    if any(source_bias.values()) and project_depth_bias is None:
        raise NativeShaderError("Native depth offset is not implemented")
    if value(state["zClip"]) != 1 or value(state["alphaToMask"]) != 0:
        raise NativeShaderError("Native depth clip/alpha-to-coverage is not implemented")
    resolved = {"cull": value(state["culling"]), "zwrite": value(state["zWrite"]),
                "ztest": value(state["zTest"])}
    if project_depth_bias is not None:
        resolved["depth_bias"] = {**project_depth_bias, "source": source_bias,
            "hardware_injected": False, "source_bias_equivalence": False}
    if depth_velocity is not None:
        if {key: resolved[key] for key in ("cull", "zwrite", "ztest")} != depth_velocity["source_render_state"]:
            raise NativeShaderError("额外Depth/Velocity与真实源渲染状态不同")
    elif resolved["cull"] not in (0, 2) or resolved["zwrite"] != 0 or resolved["ztest"] not in (4, 8):
        raise NativeShaderError("Native source only supports Off/Back cull, no ZWrite and LEqual/Always: " + repr(resolved))
    factors = {0: "Zero", 1: "One", 2: "DstColor", 3: "SrcColor", 4: "OneMinusDstColor",
               5: "SrcAlpha", 6: "OneMinusSrcColor", 7: "DstAlpha", 8: "OneMinusDstAlpha",
               9: "SrcAlphaSaturate", 10: "OneMinusSrcAlpha"}
    src, dst = value(blend["srcBlend"]), value(blend["destBlend"])
    if src not in factors or dst not in factors:
        raise NativeShaderError("Unsupported native blend factors: " + repr((src, dst)))
    line = "Blend " + factors[src] + " " + factors[dst]
    if execution_environment in (TRANSMITTANCE_PREVIEW, UE.MODE, PROJECT_FULLRES):
        line += ", DstAlpha Zero"
    return [line], resolved


def project_environment(identifier, program, material_pid, shadow_adaptation=None, depth_velocity=None):
    """真人已选的 UE 消费环境；只验证对应源程序，不宣称复制原 half-res 管线。"""
    outputs = program["out"]
    if len(outputs) != 1 or any(outputs[0].get(k) != v for k, v in
            {"name": "SV_Target", "index": 0, "reg": 0, "mask": "xyzw"}.items()):
        raise NativeShaderError("Project colour environment requires exactly source o0 RGBA")
    if [s for s in program["asm"] if s.startswith("dcl_output")] != ["dcl_output o0.xyzw"]:
        raise NativeShaderError("Project colour environment cannot discard extra native outputs")
    if identifier == PROJECT_FULLRES:
        UE.validate_depth_sampling(program)  # 共享纯 LOD0/G 源指令核验，不采用 Evade 环境。
        return {"name": identifier, "configuration_mode": "ProjectConfigured", "blend": "BLEND_AlphaComposite",
            "output_conversion": "rgb,1-alpha", "lighting": "unlit", "translucency_pass": "MTP_BeforeDOF",
            "native_alpha_role": "transmittance", "ue_opacity": "1-source.a",
            "source_fade_camera_depth": "preserved_source_program_with_UE_scene_bindings",
            "depth": "UE_current_view_reciprocal_eye_metres_LOD0_G",
            "source_halfres_pipeline": "not_reproduced_UE_full_resolution",
            "source_destination_alpha_equivalence": "not_claimed_UE_standard_alpha_composite",
            "visual_calibration": "pending"}
    if identifier == PROJECT_SHADOW:
        if not isinstance(shadow_adaptation, dict) \
                or shadow_adaptation.get("implementation") != "ProjectConfigured_source_base_with_UE_native_shadow" \
                or shadow_adaptation.get("material_pid") != str(material_pid) \
                or shadow_adaptation.get("derived_assembly_sha256", {}).get("fp") != hashlib.sha256(
                    "\n".join(program["asm"]).encode()).hexdigest():
            raise NativeShaderError("Project native shadow requires this material's exact guarded base derivation")
        return {"name": identifier, "configuration_mode": "ProjectConfigured", "blend": "BLEND_AlphaComposite",
            "output_conversion": "rgb", "lighting": "ue_volumetric_nondirectional", "translucency_pass": "MTP_BeforeDOF",
            "source_shadow": "explicit_UE_native_replacement_not_source_runtime",
            "source_base_fade_depth": "must_be_preserved_by_exact_derived_program",
            "visual_calibration": "pending"}
    if identifier == PROJECT_DEPTH_VELOCITY:
        contract = project_depth_velocity_contract(depth_velocity, material_pid)
        if contract is None:
            raise NativeShaderError("额外Depth/Velocity环境缺源合同")
        return {"name": identifier, "configuration_mode": "ProjectConfigured", "material_pid": str(material_pid),
            "blend": "BLEND_AlphaComposite", "output_conversion": "rgb", "lighting": "unlit",
            "translucency_pass": "MTP_BeforeDOF", "depth_velocity_contract": contract,
            "source_rgba_program": "unchanged", "source_main_pass_zwrite": 1,
            "ue_color_pass_main_depth_write": False, "ue_additional_depth_pass": "LateTranslucentVelocity",
            "opacity_coverage": "Opacity >= 1/255 + OpacityMaskClipValue",
            "source_same_draw_depth_and_order_equivalence": False,
            "source_destination_alpha_equivalence": False,
            "source_previous_DP3_WPO_and_private_material_age_equivalence": False,
            "runtime_view_eligibility": "supported_deferred_velocity_non_debug_camera_history_and_native_screen_size_gate",
            "runtime_velocity_draw_verified": False, "visual_calibration": "pending"}
    raise NativeShaderError("Unconfigured project colour environment/material pair")


def project_provider(provider, environment):
    if environment.get("name") not in (PROJECT_FULLRES, PROJECT_SHADOW, PROJECT_DEPTH_VELOCITY):
        raise NativeShaderError("Unknown project scene provider")
    result = deepcopy(provider)
    result["__textures__"]["_DepthMipChain"] = (
        "float4(0.0, 1.0 / (CalcSceneDepth(ViewportUVToBufferUV({uv})) * 0.01), 0.0, 0.0)")
    if environment["name"] == PROJECT_SHADOW:
        for name in ("_VfxShadowInfoMatrix", "_MainLightShadowmapTexture"):
            result.pop(name, None)
    return result


def project_material_properties(environment):
    if environment.get("name") not in (PROJECT_FULLRES, PROJECT_SHADOW, PROJECT_DEPTH_VELOCITY) \
            or environment.get("configuration_mode") != "ProjectConfigured" \
            or environment.get("blend") != "BLEND_AlphaComposite":
        raise NativeShaderError("Project material environment is not configured")
    lighting = environment.get("lighting")
    if lighting not in ("unlit", "ue_volumetric_nondirectional"):
        raise NativeShaderError("Project material has no declared native lighting consumer")
    props = {"MaterialDomain": "MD_Surface", "ShadingModel": "MSM_Unlit" if lighting == "unlit" else "MSM_DefaultLit",
             "TranslucencyPass": "MTP_BeforeDOF", "bUseTranslucencyVertexFog": True}
    if lighting != "unlit":
        props["TranslucencyLightingMode"] = "TLM_VolumetricNonDirectional"
    if environment["name"] == PROJECT_DEPTH_VELOCITY:
        contract = project_depth_velocity_contract(environment["depth_velocity_contract"], environment["material_pid"])
        if contract is None or lighting != "unlit" or environment.get("translucency_pass") != "MTP_BeforeDOF":
            raise NativeShaderError("额外Depth/Velocity材质环境不完整")
        props.update(bOutputTranslucentVelocity=True, OpacityMaskClipValue=contract["opacity_mask_clip_value"])
    return props


def derive_project_shadow_base(programs, evidence, material, material_pid, contract_input):
    """消费已逐分量审阅的原字节／区间契约，派生 UE 阴影的完整基础效果。"""
    if isinstance(contract_input, dict):
        contract = deepcopy(contract_input)
        reference = contract.get("source_reference")
        if not isinstance(reference, str) or not reference:
            raise NativeShaderError("Inline shadow contract requires its explicit policy reference")
        contract_digest = hashlib.sha256(json.dumps(contract, sort_keys=True, separators=(",", ":"),
            ensure_ascii=False).encode("utf-8")).hexdigest()
        hash_scope = "semantic_json_utf8"
    elif isinstance(contract_input, str) and Path(contract_input).is_file():
        contract = read_json(contract_input)
        reference, contract_digest, hash_scope = str(Path(contract_input).resolve()), file_hash(contract_input), "file_bytes"
    else:
        raise NativeShaderError("Missing reviewed source shadow/base-effect derivation")
    if contract.get("kind") != "GuardedSourceBaseWithUENativeShadow/v1" \
            or contract.get("material_pid") != str(material_pid) or set(contract.get("stages", {})) != {"vp", "fp"}:
        raise NativeShaderError("Missing exact source/base-effect derivation contract")
    floats = material["m_SavedProperties"]["m_Floats"]
    if any(floats.get(k) != v for k, v in contract["required_material_floats"].items()):
        raise NativeShaderError("Source MainLight colour mapping requires a new explicit UE lighting contract")
    derived, identities = deepcopy(programs), {}
    for stage in ("vp", "fp"):
        rule = contract["stages"][stage]
        asm = programs[stage]["asm"]
        if evidence[stage]["sha256"] != rule["program_sha256"] or len(asm) != rule["length"]:
            raise NativeShaderError("Source shadow program identity/length changed: " + stage)
        previous = 0
        rewritten = []
        for block in rule["blocks"]:
            begin, end = block["begin"], block["end"]
            if not (type(begin) is int and type(end) is int and previous <= begin < end <= len(asm)) \
                    or hashlib.sha256("\n".join(asm[begin:end]).encode()).hexdigest() != block["sha256"]:
                raise NativeShaderError("Source shadow instruction boundary changed: " + stage)
            rewritten += asm[previous:begin] + block["replacement"]
            previous = end
        rewritten += asm[previous:]
        for declaration in rule["remove_declarations"]:
            if rewritten.count(declaration) != 1:
                raise NativeShaderError("Source shadow declaration is not unique: " + declaration)
            rewritten.remove(declaration)
        digest = hashlib.sha256("\n".join(rewritten).encode()).hexdigest()
        if len(rewritten) != rule["derived_length"] or digest != rule["derived_sha256"]:
            raise NativeShaderError("Derived base-effect program differs from the reviewed contract: " + stage)
        derived[stage]["asm"] = rewritten
        field = "out" if stage == "vp" else "in"
        signature = rule["remove_signature"]
        matches = [row for row in derived[stage][field] if all(row.get(k) == v for k, v in signature.items())]
        if len(matches) != 1:
            raise NativeShaderError("Source shadow varying signature is not unique")
        derived[stage][field] = [row for row in derived[stage][field] if row is not matches[0]]
        identities[stage] = digest
    return derived, {"implementation": "ProjectConfigured_source_base_with_UE_native_shadow",
        "material_pid": str(material_pid), "contract": reference,
        "contract_sha256": contract_digest, "contract_hash_scope": hash_scope,
        "derived_assembly_sha256": identities, "source_local_declarations": "unchanged",
        "source_custom_shadow_RGB_and_opacity": "replaced_by_UE_native_response",
        "source_ambient_depth_fresnel_power_fade_and_premultiplication": "preserved",
        "native_and_visual_acceptance": "pending"}


def fragment_environment(identifier, program):
    """转换输出解释，不改原程序；这里只声明单 Target0 的逐片元 RGB 预览。"""
    if identifier != TRANSMITTANCE_PREVIEW:
        raise NativeShaderError("Unknown native preview execution environment: " + str(identifier))
    outputs = program["out"]
    if len(outputs) != 1 or any(outputs[0].get(k) != v for k, v in
                              {"name": "SV_Target", "index": 0, "reg": 0, "mask": "xyzw"}.items()):
        raise NativeShaderError("Transmittance preview requires exactly one SV_Target0 xyzw output in o0")
    declarations = [line for line in program["asm"] if line.startswith("dcl_output")]
    if declarations != ["dcl_output o0.xyzw"]:
        raise NativeShaderError("Transmittance preview cannot execute extra native output declarations")
    return {"name": identifier, "blend": "BLEND_AlphaComposite", "output_conversion": "rgb,1-alpha",
            "fragment_rgb_equation": "native.rgb + destination.rgb * native.a",
            "native_alpha_role": "transmittance", "ue_opacity": "1 - native.a",
            "rgb_equivalence_domain": "finite native.a in [0,1], same ordered fragments and background",
            "requested_render_resolution": "UE full resolution", "actual_ue_render_resolution": "unverified",
            "sv_position_xy": "UE viewport pixels",
            "destination_alpha_equivalence": "not_implemented",
            "source_halfres_pipeline": "unverified_not_implemented",
            "source_halfres_clear_resolve_depth_ordering": "unverified_not_implemented",
            "source_screen_coordinates_and_runtime_globals": "unverified"}


def vertex_texture_local_output(program):
    """保留 Lightning 原贴图取帧和插值，在粒子 TRS 之前导出局部位置。

    Native Mesh renderer 执行粒子 TRS。AgeClip 仍把整粒几何收为一点；
    不把原投影矩阵或未知运行时 _LocalToWorld 填成固定矩阵。
    """
    asm = program["asm"]
    anchors = {
        24: "mov_sat r0.x, v4.w",
        37: "mul r1.xy, v2.zwzz, cb2[1].zwzz",
        42: "ld r3.xyzw, r2.xyww, t0.xyzw",
        47: "ld r4.xyzw, r1.xzww, t0.xyzw",
        52: "mad r3.xyz, r0.xxxx, r3.xyzx, r4.xyzx",
        53: "add r4.xyz, r3.xyzx, cb2[18].xyzx",
        87: "add r4.xyz, r4.xyzx, v0.xyzx",
        89: "ge r0.y, v4.z, cb2[10].z",
        91: "mad r4.xyz, r0.yyyy, r8.xyzx, r4.xyzx",
    }
    if any(len(asm) <= index or asm[index] != value for index, value in anchors.items()) \
            or program["bind"]["tex"].get(0, {}).get("name") != "_VertexPositionTex" \
            or any(row["reg"] >= 6 for row in program["out"]):
        raise NativeShaderError("VertexAnimation 原局部位置／AgeClip 指令结构变化")
    result = deepcopy(program)
    result["out"].append({"name": "TEXCOORD", "index": 6, "mask": "xyz", "reg": 6,
                          "sys": "NONE", "used": "xyz"})
    result["asm"] = []
    for index, instruction in enumerate(asm):
        result["asm"].append(instruction)
        if index == 22:
            result["asm"].append("dcl_output o6.xyz")
        elif index == 53:
            result["asm"].append("mov o6.xyz, r4.xyzx")
        elif index == 89:
            result["asm"].append("movc o6.xyz, r0.yyyy, l(1.000000, 1.000000, 1.000000, 0.000000), o6.xyzx")
    return result, {"mode": "SourceVertexTexturePosition", "local_position_output_register": 6,
                    "position_space": "ParticleLocalUnityMetres", "additional_bounds_radius_cm": 0.0,
                    "bounds_owner": "StaticMeshSourceTextureEnvelope", "source_capture_after": 53,
                    "source_age_clip_after": 89, "age_clip_geometry": "CollapseAllVertices",
                    "transform_owner": "NativeNiagaraMeshInstance"}


def _program_from_row(audit, row, stage, *, inspection_only=False, project_configured=False):
    """复用原字节／声明核验；审计读取不取得渲染执行权限。"""
    if audit.get("hashScope") not in (None, "file_bytes") or row.get("hashScope") not in (None, "file_bytes", "source_range_bytes"):
        raise NativeShaderError("Native program audit must certify unmodified source bytes")
    if row.get("fileBytesSha256", row["sha256"]) != row["sha256"]:
        raise NativeShaderError("Native program byte digest fields disagree")
    span = row.get("sourceByteRange")
    if span is not None:
        if "file" in row or row.get("hashScope") != "source_range_bytes" or not isinstance(span, dict) \
                or set(span) != {"offset", "bytes"} or type(span["offset"]) is not int \
                or type(span["bytes"]) is not int or span["offset"] < 0 or span["bytes"] <= 0:
            raise NativeShaderError("Invalid exact source program range")
        path = Path(audit["sourceShader"])
        if span["offset"] + span["bytes"] > path.stat().st_size or file_hash(path) != audit["sourceShaderSha256"]:
            raise NativeShaderError("Original Shader identity/range changed: " + str(path))
        with path.open("rb") as source:
            source.seek(span["offset"])
            raw = source.read(span["bytes"])
        if len(raw) != span["bytes"] or hashlib.sha256(
                raw.decode("utf-8-sig").replace("\r\n", "\n").encode("utf-8")).hexdigest() != row["normalizedTextSha256"]:
            raise NativeShaderError("Source range normalized digest mismatch: " + str(path))
    else:
        if row.get("hashScope") == "source_range_bytes":
            raise NativeShaderError("Source range hash scope has no byte range")
        path = Path(row["file"])
        raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != row["sha256"]:
        raise NativeShaderError("Native program byte digest does not match its audit: " + str(path))
    # 摘要只核原始字节；解析层统一换行，兼容只读共享解析器的 LF 签名格式。
    text = "\n".join(raw.decode("utf-8-sig").splitlines()) + "\n"
    local_lines = re.findall(r'^Local Keywords \{([^}]*)\}', text, re.M)
    global_lines = re.findall(r'^Keywords \{([^}]*)\}', text, re.M)
    actual_local = {k for line in local_lines for k in re.findall(r'"([^\"]+)"', line)}
    actual_global = {k for line in global_lines for k in re.findall(r'"([^\"]+)"', line)}
    if actual_local != set(row["localKeywords"]) or actual_global != set(row["globalKeywords"]):
        raise NativeShaderError("Native program keyword metadata mismatch: " + str(path))
    if not text.startswith('SubProgram "d3d11 ') or not re.search(r'// hash: ' + re.escape(row["hash64"]) + r'\b', text):
        raise NativeShaderError("Native program API/hash identity mismatch: " + str(path))
    program = T.parse_subprogram(text)
    prefix = "vs_" if stage == "vp" else "ps_"
    # SM4 使用已存在的共同指令翻译链；保原 profile，不改汇编或源声明。
    # 这里仅准入源程序，实际指令、资源和阶段联接仍由 Material plan 的 T.translate 核。
    profiles = (prefix + "4_0", prefix + "5_0") if inspection_only or project_configured else (prefix + "5_0",)
    if not program["asm"] or program["asm"][0] not in profiles or not program["bind"]["cbbind"]:
        raise NativeShaderError("Native program profile/reflection is missing: " + str(path))
    if row.get("profile", program["asm"][0]) != program["asm"][0]:
        raise NativeShaderError("Native program profile metadata mismatch: " + str(path))
    location = ({"sourceShader": str(path), "sourceShaderSha256": audit["sourceShaderSha256"], "sourceByteRange": span}
                if span is not None else {"file": str(path)})
    return program, {**location, "sha256": row["sha256"], "hash64": row["hash64"]}


def program_from_audit(audit, stage, pass_index, globals_, locals_, *, project_configured=False):
    """执行入口仍要求唯一完整匹配，不采用只读候选审计的关键词投影。"""
    matches = [row for row in audit["matches"] if row["stage"] == stage and row["passIndex"] == pass_index
               and set(row["globalKeywords"]) == set(globals_) and set(row["localKeywords"]) == set(locals_)]
    if len(matches) != 1:
        raise NativeShaderError("Expected one exact %s candidate for pass %s, found %s" % (stage, pass_index, len(matches)))
    return _program_from_row(audit, matches[0], stage, project_configured=project_configured)


def inspect_program_candidates(audit, pass_index, serialized_keywords, *, verify_bytes=True):
    """逐候选报告真实声明和完整材质输入，不选运行变体或认证全 Pass 声明全集。"""
    def names(value, label):
        if not isinstance(value, list) or any(not isinstance(k, str) or not k or k.strip() != k for k in value):
            raise NativeShaderError("Invalid keyword list: " + label)
        if len(value) != len(set(value)):
            raise NativeShaderError("Duplicate keyword declaration: " + label)
        return set(value)

    material = names(serialized_keywords, "serialized material keywords")
    if material != names(audit["serializedMaterialKeywords"], "audited material keywords"):
        raise NativeShaderError("Native material audit identity/keywords mismatch")
    if type(pass_index) is not int or pass_index < 0:
        raise NativeShaderError("Invalid audit pass index")
    candidates, groups = [], {}
    for row in audit["matches"]:
        if row["passIndex"] != pass_index:
            continue
        stage = row["stage"]
        if stage not in ("vp", "fp"):
            raise NativeShaderError("Unsupported audited program stage: " + str(stage))
        local = names(row["localKeywords"], "local keywords")
        global_ = names(row["globalKeywords"], "global keywords")
        if local & global_:
            raise NativeShaderError("Keyword declared as both LOCAL and GLOBAL in one program")
        candidate = {key: row[key] for key in ("stage", "globalKeywords", "localKeywords", "sha256")}
        if "sourceByteRange" in row:
            candidate.update(sourceShader=audit["sourceShader"], sourceByteRange=row["sourceByteRange"])
        else:
            candidate["file"] = row["file"]
        if verify_bytes:
            program, _ = _program_from_row(audit, row, stage, inspection_only=True)
            candidate["profile"] = program["asm"][0]
        candidate["program_bytes_verified"] = verify_bytes
        candidate["keyword_evidence"] = "verified_program_declarations" if verify_bytes else "audit_metadata_only"
        candidate["material_keyword_roles"] = {
            "local": sorted(material & local), "global": sorted(material & global_),
            "not_declared_by_candidate": sorted(material - local - global_),
            "candidate_local_not_serialized": sorted(local - material),
            "candidate_global_not_serialized": sorted(global_ - material)}
        candidates.append(candidate)
        key = (stage, tuple(sorted(global_)), tuple(sorted(local)))
        groups.setdefault(key, []).append(len(candidates) - 1)
    ambiguities = [{"stage": key[0], "globalKeywords": list(key[1]), "localKeywords": list(key[2]),
                    "candidate_indices": indices}
                   for key, indices in groups.items() if len(indices) > 1]
    return {"candidates": candidates, "ambiguities": ambiguities,
            "keyword_declaration_scope": "audited_candidates_only", "runtime_selection": "unverified"}


def validate_audit_identity(shader_entry, material, material_pid, audit):
    """Shared read boundary for candidate inventory and explicit selection.

    This verifies source identities/keywords, not a runtime pass/global policy.
    Program byte checks remain at consumption, and render state at selection.
    """
    serialized_keywords = sorted((material.get("m_ShaderKeywords") or "").split())
    if str(audit["shaderPathID"]) != str(shader_entry["pathID"]) or audit["shaderName"] != shader_entry["name"]:
        raise NativeShaderError("Native Shader audit identity mismatch")
    if str(audit["materialPathID"]) != str(material_pid) or set(audit["serializedMaterialKeywords"]) != set(serialized_keywords):
        raise NativeShaderError("Native material audit identity/keywords mismatch")
    shader_files = [Path(p).resolve() for p in shader_entry["files"] if str(p).endswith(".shader")]
    if shader_files != [Path(audit["sourceShader"]).resolve()]:
        raise NativeShaderError("Native audit points to another Shader source")
    native_path = Path(shader_entry["nativeJson"])
    expected_native = Path(audit["sourceShader"]).with_suffix(".native.json").resolve()
    if native_path.resolve() != expected_native:
        raise NativeShaderError("Native state/Properties source differs from the audited Shader")
    return native_path, serialized_keywords


def _zero_contribution_variant_keywords(shader_entry, material, material_pid, configuration, audit, props):
    """明确快照移植：原词不改，只有已证失活的UV扰动可选完整现成程序。"""
    contract = configuration["zero_contribution_variant"]
    original = sorted(material["m_ShaderKeywords"].split())
    selected = contract["selected_keywords"]
    required = {"_MainTexDistorMul", "_MainTexDistor2Mul", "_DistortionTexDissolveMul", "_DistortionTex2DissolveMul"}
    if configuration.get("program_selection") != "ProjectConfiguredZeroContributionVariant" \
            or configuration.get("configuration_mode") != "ProjectConfigured" \
            or contract["schema"] != "GGYGO.FX.ZeroContributionVariant/v1" \
            or str(material_pid) != contract["material_pid"] or str(shader_entry["pathID"]) != contract["shader_pid"] \
            or original != sorted(contract["serialized_keywords"]) or len(selected) != len(set(selected)) \
            or set(selected)-set(original) != {"_ASE_DISTORTIONTEX_ON", "_ASE_DISTORTIONTEX2_ON"} \
            or not set(original) <= set(selected) or set(contract["required_float_values"]) != required:
        raise NativeShaderError("ZeroContribution requires its exact material/Shader/original and selected keyword sets")
    if file_hash(contract["material_source"]) != contract["material_sha256"] \
            or audit["sourceShaderSha256"] != contract["shader_source_sha256"]:
        raise NativeShaderError("ZeroContribution original source snapshot changed")
    floats = material["m_SavedProperties"]["m_Floats"]
    if any(contract["required_float_values"][name] != 0 or floats.get(name) != 0 for name in required) \
            or contract["finite_sample_inputs_required"] is not True \
            or contract["dynamic_material_override_policy"] != "ProofPropertiesNotOverriddenInProjectConfiguredSnapshot":
        raise NativeShaderError("ZeroContribution finite zero-coefficient/override premises changed")
    texenvs = material["m_SavedProperties"]["m_TexEnvs"]
    for name, pointer in contract["required_texture_pointers"].items():
        actual = texenvs[name]["m_Texture"]
        if [actual["m_FileID"], str(actual["m_PathID"])] != pointer:
            raise NativeShaderError("ZeroContribution exact texture binding changed: " + name)
    # 0乘子只对有限采样消去贡献；真实UNorm头和Shader白默认均须在本快照核验。
    samples = contract["finite_texture_samples"]
    bound = {name for name in contract["required_texture_pointers"] if not texenvs[name]["m_Texture"]["IsNull"]}
    if set(samples) != bound:
        raise NativeShaderError("ZeroContribution finite sample proof does not cover exact non-null bindings")
    for name, proof in samples.items():
        raw = Path(proof["metadata"]["path"]).read_bytes()
        if len(raw) != proof["metadata"]["size"] or hashlib.sha256(raw).hexdigest() != proof["metadata"]["sha256"]:
            raise NativeShaderError("ZeroContribution finite texture metadata identity changed: " + name)
        if proof["texture_pointer"] != contract["required_texture_pointers"][name]:
            raise NativeShaderError("ZeroContribution finite texture proof points at another binding: " + name)
        header = json.loads(raw.decode("utf-8-sig"))
        if proof["sample_domain"] != "BC7_UNorm" or header["m_TextureFormat"] != 25 \
                or not header["m_Width"] > 0 or not header["m_Height"] > 0:
            raise NativeShaderError("ZeroContribution requires its proven finite UNorm texture domain: " + name)
    floats_to_check = material["m_SavedProperties"]["m_Floats"].values()
    if any(type(value) not in (int, float) or not math.isfinite(value) for value in floats_to_check):
        raise NativeShaderError("ZeroContribution source scalar parameters must be finite")
    for name in contract["required_texture_pointers"]:
        transform = texenvs[name]
        if any(not math.isfinite(value) for field in ("m_Scale", "m_Offset") for value in transform[field].values()):
            raise NativeShaderError("ZeroContribution source sample transform must be finite: " + name)
    for name in ("_DistortionTex2", "_DissolveTex"):
        if not texenvs[name]["m_Texture"]["IsNull"] or props[name]["type"] != "2D" or props[name]["tex_default"] != "white":
            raise NativeShaderError("ZeroContribution requires original null + Shader white default: " + name)
    for stage in ("vp", "fp"):
        rows = [row for row in audit["matches"] if row["stage"] == stage]
        if len(rows) != 1 or rows[0]["sha256"] != contract["stage_sha256"][stage] \
                or rows[0]["passIndex"] != configuration["pass_index"] \
                or set(rows[0]["globalKeywords"]+rows[0]["localKeywords"]) != set(selected):
            raise NativeShaderError("ZeroContribution requires its complete exact selected stage pair")
    return sorted(selected)


def _feature_off_audit(shader_entry, material, material_pid, configuration, fragment_audit):
    """明确项目分支：保留各 stage 原声明，只消去已证明为零的 Distortion 项。"""
    contract = configuration["feature_off"]
    if configuration.get("program_selection") != "ProjectConfiguredFeatureOff" or configuration.get("configuration_mode") != "ProjectConfigured" \
            or contract.get("schema") != "GGYGO.FX.ProjectConfiguredFeatureOff/v1" \
            or contract.get("disabled_feature") != "_USEDISTORTIONTEXTURE_ON" \
            or str(material_pid) != contract["material_pid"] or str(shader_entry["pathID"]) != contract["shader_pid"] \
            or sorted(material["m_ShaderKeywords"].split()) != sorted(contract["serialized_keywords"]):
        raise NativeShaderError("FeatureOff requires its exact material, Shader and original keyword set")
    if file_hash(contract["material_source"]) != contract["material_sha256"]:
        raise NativeShaderError("FeatureOff material source changed")
    floats = material["m_SavedProperties"]["m_Floats"]
    required = contract["required_float_values"]
    if any(required.get(k) != 0 for k in ("_UseDistortionTexture", "_DistortionIntensity", "_MaskDistortionIntensity")) \
            or any(floats.get(k) != value for k, value in required.items()) \
            or not material["m_SavedProperties"]["m_TexEnvs"]["_DistortionTex"]["m_Texture"]["IsNull"]:
        raise NativeShaderError("FeatureOff zero-contribution/source deformation premises changed")
    vp = contract["vertex_program"]
    if vp.get("stage") != "vp" or vp.get("passIndex") != configuration["pass_index"] \
            or set(vp["globalKeywords"] + vp["localKeywords"]) != set(contract["serialized_keywords"]):
        raise NativeShaderError("FeatureOff must retain all serialized vertex features")
    fragment_keywords = (set(contract["serialized_keywords"]) - {"_VERTEX_EXTRUSION_ON", "_VERTEX_EXTRUSION_MASKTEX"}) \
        | {"_USEDISTORTIONTEXTURE_ON"}
    matches = [row for row in fragment_audit["matches"] if row["stage"] == "fp" \
        and row["passIndex"] == configuration["pass_index"] and not row["globalKeywords"] \
        and set(row["localKeywords"]) == fragment_keywords and row["sha256"] == contract["fragment_program_sha256"]]
    if len(matches) != 1:
        raise NativeShaderError("FeatureOff requires one exact audited fragment candidate")
    audit = {**fragment_audit, "materialPathID": str(material_pid),
             "serializedMaterialKeywords": contract["serialized_keywords"], "matches": [vp, matches[0]]}
    return audit


def _lower_feature_off(programs):
    """精确已证零项：不采空纹理，不改其余 Mask／Ramp／Soft／Fresnel 指令。"""
    fp = deepcopy(programs["fp"])
    block = ["sample_indexable(texture2d)(float,float,float,float) r1.xyzw, r1.xyxx, t3.xyzw, s3",
             "ftou r2.x, cb1[34].w", "umin r2.x, r2.x, l(3)",
             "dp4 r1.x, r1.xyzw, icb[r2.x + 0].xyzw", "add r1.x, r1.x, l(-0.498039)",
             "dp2 r1.x, r1.xxxx, v4.zzzz"]
    starts = [i for i in range(len(fp["asm"]) - len(block) + 1) if fp["asm"][i:i + len(block)] == block]
    if len(starts) != 1 or fp["bind"]["tex"][3]["name"] != "_DistortionTex":
        raise NativeShaderError("FeatureOff fragment zero block/reflection changed")
    index = starts[0]
    fp["asm"][index:index + len(block)] = ["mov r1.x, l(0.000000)"]
    return fp, {"mode": "ProjectConfiguredFeatureOff", "disabled_feature": "_USEDISTORTIONTEXTURE_ON",
        "proof": "SerializedZeroMainAndMaskDistortionIntensity", "removed_instructions": block,
        "replacement": "mov r1.x, l(0.000000)", "source_runtime_certified": False,
        "derived_asm_sha256": hashlib.sha256("\n".join(fp["asm"]).encode("utf-8")).hexdigest()}


def _bound_source_vertex(program):
    """在真VS产生额外世界位移后限长；原位置派生插值沿同一后续指令消费。"""
    vp = deepcopy(program)
    anchors = ["mad r3.xyz, r4.xyzx, r0.zzzz, r3.xyzx", "mul r4.xyz, r3.yyyy, cb1[1].xyzx"]
    matches = [i for i in range(len(vp["asm"])-1) if vp["asm"][i:i+2] == anchors]
    position = [row for row in vp["in"] if row["name"] == "POSITION" and row["index"] == 0]
    slots = [slot for slot,name in vp["bind"]["cbbind"].items() if name == "UnityPerMaterial"]
    if len(matches) != 1 or len(position) != 1 or position[0]["reg"] != 0 or len(slots) != 1:
        raise NativeShaderError("Source vertex world-position/extrusion boundary changed")
    slot = slots[0]
    cb = vp["bind"]["cb"]["UnityPerMaterial"]
    parameter = "UEFX_SourceVertexWPOBoundsRadiusCM"
    if any(row["name"] == parameter for row in cb["params"]):
        raise NativeShaderError("Source vertex reflection collides with reserved world radius")
    offset = (cb["size"]+15)//16*16
    cb["size"] = offset+16
    cb["params"].append({"kind": "V", "name": parameter, "offset": offset, "dim": 1, "arr": 0, "type": 0})
    declaration = [i for i,line in enumerate(vp["asm"])
                   if re.match(r"dcl_constantbuffer\s+cb%d\[" % slot, line, re.I)]
    temporaries = [i for i,line in enumerate(vp["asm"]) if re.fullmatch(r"dcl_temps \d+", line)]
    if len(declaration) != 1 or len(temporaries) != 1:
        raise NativeShaderError("Source vertex constant/temporary declaration is ambiguous")
    index = temporaries[0]
    first = int(vp["asm"][index].split()[1])
    if any(int(value) >= first for line in vp["asm"] for value in re.findall(r"\br(\d+)\b", line)):
        raise NativeShaderError("Source vertex temporary declaration does not cover its actual registers")
    vp["asm"][index] = "dcl_temps %d" % (first+2)
    index = declaration[0]
    vp["asm"][index] = re.sub(r"\bcb%d\[\d+\]" % slot, "cb%d[%d]" % (slot, cb["size"]//16),
                              vp["asm"][index], flags=re.I)
    delta, radius = "r%d" % first, "r%d" % (first+1)
    # VS输入已是完整affine后的world-baked米坐标，ObjectToWorld=identity由原Material plan再核。
    # 先缩放向量再求长度，避免公开强度较大时长度平方溢出。
    instructions = ["add %s.xyz, r3.xyzx, -v0.xyzx" % delta,
        "max %s.x, |%s.x|, |%s.y|" % (radius, delta, delta),
        "max %s.x, %s.x, |%s.z|" % (radius, radius, delta),
        "lt %s.y, l(0.000000), %s.x" % (radius, radius), "if_nz %s.y" % radius,
        "div %s.xyz, %s.xyzx, %s.xxxx" % (delta, delta, radius),
        "dp3 %s.w, %s.xyzx, %s.xyzx" % (delta, delta, delta),
        "sqrt %s.w, %s.w" % (delta, delta),
        "mul %s.z, cb%d[%d].x, l(0.010000)" % (radius, slot, offset//16),
        "div %s.z, %s.z, %s.x" % (radius, radius, radius),
        "lt %s.y, %s.z, %s.w" % (radius, radius, delta), "if_nz %s.y" % radius,
        "div %s.xyz, %s.xyzx, %s.wwww" % (delta, delta, delta),
        "mul %s.z, cb%d[%d].x, l(0.010000)" % (radius, slot, offset//16),
        "mad r3.xyz, %s.xyzx, %s.zzzz, v0.xyzx" % (delta, radius), "endif", "endif"]
    vp["asm"][matches[0]+1:matches[0]+1] = instructions
    return vp, {"mode": "WorldEuclideanSourceExtraDisplacementLimit", "world_baked_identity_required": True,
        "source_position": "v0.xyz", "constrained_position": "r3.xyz before original ObjectToWorld and derived varyings",
        "radius_parameter": parameter, "radius_unit": "centimetres", "affine_baseline_constrained": False,
        "all_source_varyings_and_WPO_share_position": True, "default_source_math_preserved_within_radius": True,
        "inserted_instructions": instructions,
        "derived_asm_sha256": hashlib.sha256("\n".join(vp["asm"]).encode("utf-8")).hexdigest(),
        "derived_reflection_parameter": cb["params"][-1], "source_runtime_certified": False}


def project_stage_keywords(configuration, serialized):
    """项目显式选择各阶段原程序；缺少原 stage mask 时不声称原配对已恢复。"""
    stages = configuration.get("stage_keywords")
    if stages is None:
        return None
    if configuration.get("configuration_mode") != "ProjectConfigured" \
            or configuration.get("program_selection") != "ProjectConfiguredStageKeywords" \
            or not configuration.get("stage_selection_reason") or set(stages) != {"vp", "fp"}:
        raise NativeShaderError("Stage keywords require an explicit project choice for both stages")
    for stage, roles in stages.items():
        if set(roles) != {"global", "local"} or any(not isinstance(v, list) for v in roles.values()):
            raise NativeShaderError("Stage keyword roles are invalid: " + stage)
        names = roles["global"] + roles["local"]
        if any(not isinstance(k, str) for k in names) or len(names) != len(set(names)) \
                or not set(names) <= set(serialized):
            raise NativeShaderError("Stage selection must preserve unique declared source keyword roles: " + stage)
    return stages


def select_native(shader_entry, material, material_pid, configuration):
    purpose = configuration.get("purpose")
    equivalent = purpose == UE.PURPOSE
    project_configured = purpose == PROJECT_PURPOSE
    if purpose != "source_program_preview" and not equivalent and not project_configured:
        raise NativeShaderError("Native source selection requires an explicit preview, ProjectConfigured or UE equivalent purpose")
    if project_configured and configuration.get("configuration_mode") != "ProjectConfigured":
        raise NativeShaderError("Project source programs require explicit ProjectConfigured provenance")
    if project_configured and configuration.get("execution_environment") not in (None, PROJECT_FULLRES, PROJECT_SHADOW, PROJECT_DEPTH_VELOCITY):
        raise NativeShaderError("ProjectConfigured requires its complete consumer; preview/Evade environments cannot be substituted")
    pass_index = configuration.get("pass_index")
    globals_ = configuration.get("global_keywords")
    if type(pass_index) is not int or pass_index < 0 or not isinstance(globals_, list) or any(
            not isinstance(k, str) for k in globals_) or len(globals_) != len(set(globals_)):
        raise NativeShaderError("Explicit pass index and unique global keyword list are required")
    audit_path = Path(configuration["audit"])
    audit = read_json(audit_path)
    feature_off = configuration.get("feature_off") is not None
    zero_variant = configuration.get("zero_contribution_variant") is not None
    if zero_variant and (not project_configured or feature_off):
        raise NativeShaderError("ZeroContribution requires its separate explicit ProjectConfigured path")
    if feature_off:
        if not project_configured or configuration.get("execution_environment") is not None:
            raise NativeShaderError("FeatureOff requires its dedicated ProjectConfigured consumer")
        audit = _feature_off_audit(shader_entry, material, material_pid, configuration, audit)
    native_path, serialized = validate_audit_identity(shader_entry, material, material_pid, audit)
    stage_keywords = project_stage_keywords(configuration, serialized)
    if stage_keywords is not None and (not project_configured or feature_off or zero_variant
                                      or configuration.get("keyword_enum_properties")):
        raise NativeShaderError("Stage keyword selection requires its separate project source path")
    # 序列化集合包含两类角色；global只按已审原声明选择，余项才是local。
    locals_ = sorted(set(serialized) - set(globals_))
    if equivalent:
        UE.validate_source(str(material_pid), shader_entry, serialized, configuration)
    elif configuration.get("execution_environment") == UE.MODE:
        raise NativeShaderError("UE production environment requires its explicit equivalent purpose")
    native_sha = file_hash(native_path)
    native = deepcopy(_native_shader_state(str(native_path.resolve()), native_sha))
    if native["m_Name"] != shader_entry["name"] or len(native["m_SubShaders"]) != 1:
        raise NativeShaderError("Native Shader name/subshader mapping is ambiguous")
    passes = native["m_SubShaders"][0]["m_Passes"]
    if pass_index >= len(passes):
        raise NativeShaderError("Native pass index is out of range")
    state = passes[pass_index]["m_State"]
    lightmode = next((item["Value"] for item in state["m_Tags"]["tags"] if item["Key"] == "LIGHTMODE"), "")
    disabled = material.get("m_DisabledShaderPasses") or []
    if state["m_Name"] in disabled or lightmode in disabled:
        raise NativeShaderError("Explicit native pass is disabled by source material")
    props = properties(native)
    selected_keywords = _zero_contribution_variant_keywords(shader_entry, material, material_pid, configuration, audit, props) \
        if zero_variant else serialized
    enum_properties = configuration.get("keyword_enum_properties", [])
    enum_evidence = None
    if enum_properties:
        if not project_configured or zero_variant or feature_off:
            raise NativeShaderError("KeywordEnum 选择仅用于独立 ProjectConfigured 原材质路径")
        selected_keywords, enum_evidence = keyword_enum_selection(material, props, enum_properties)
    if zero_variant or enum_evidence:
        locals_ = sorted(set(selected_keywords)-set(globals_))
    environment = configuration.get("execution_environment")
    depth_velocity = project_depth_velocity_contract(configuration.get("depth_velocity_contract"), material_pid)
    if (environment == PROJECT_DEPTH_VELOCITY) != (depth_velocity is not None) \
            or depth_velocity is not None and (not project_configured or configuration.get("lighting") != "unlit"):
        raise NativeShaderError("额外Depth/Velocity需要独立明确的ProjectConfigured选择")
    lines, resolved = render_state(state, material["m_SavedProperties"]["m_Floats"], props, environment,
        configuration.get("hardware_depth_bias") if project_configured else None, depth_velocity)
    selected = {"name": state["m_Name"], "lightmode": lightmode, "state": lines, "resolved_state": resolved}
    programs = {}
    for stage in ("vp", "fp"):
        if feature_off:
            row = next(row for row in audit["matches"] if row["stage"] == stage)
            selected[stage], programs[stage] = _program_from_row(audit, row, stage, project_configured=True)
        else:
            stage_globals = stage_keywords[stage]["global"] if stage_keywords else globals_
            stage_locals = stage_keywords[stage]["local"] if stage_keywords else locals_
            selected[stage], programs[stage] = program_from_audit(
                audit, stage, pass_index, stage_globals, stage_locals, project_configured=project_configured)
    adaptation = None
    vertex_texture = None
    if shader_entry["name"] == "miHoYo/Particles/Particles_VertexAnimation_Lightning":
        if not project_configured or feature_off or material["m_SavedProperties"]["m_Floats"].get("_ZOffset") != 0.0:
            raise NativeShaderError("VertexAnimation 当前端口需明确项目原程序选择及原 ZOffset=0")
        selected["vp"], vertex_texture = vertex_texture_local_output(selected["vp"])
    if feature_off:
        selected["fp"], adaptation = _lower_feature_off(selected)
        selected["vp"], vertex_adaptation = _bound_source_vertex(selected["vp"])
        adaptation["vertex_geometry"] = vertex_adaptation
    if configuration.get("output_contract") == "distortion_field_pair":
        if not project_configured or shader_entry["name"] not in (
                "miHoYo/Particles/Distortion UVMove", "miHoYo/Particles/Distortion UVMove_Deprecated") \
                or lightmode != "Distortion":
            raise NativeShaderError("Dual field requires its exact ProjectConfigured Distortion producer")
        targets = selected["fp"]["out"]
        if {(r["name"], r["index"], r["reg"], r["mask"]) for r in targets} != {
                ("SV_Target", 0, 0, "xyzw"), ("SV_Target", 1, 1, "xyzw")}:
            raise NativeShaderError("Dual field must preserve exactly the original o0/o1 RGBA outputs")
        expected_blend = {"srcBlend": 1, "destBlend": 1, "srcBlendAlpha": 1, "destBlendAlpha": 1,
                          "blendOp": 0, "blendOpAlpha": 0, "colMask": 15}
        blend_states = state["rtBlend"][:2] if state["rtSeparateBlend"] else state["rtBlend"][:1]
        if not blend_states or any({k: state_value(b[k], material["m_SavedProperties"]["m_Floats"], props)
                                    for k in expected_blend} != expected_blend for b in blend_states):
            raise NativeShaderError("Dual signed field requires original full RGBA One/One Add/Add")
    runtime_selection = ("ProjectConfigured_not_source_runtime" if project_configured else
                         "explicit_UE_equivalent_not_source_runtime" if equivalent else "unverified")
    evidence = {"purpose": purpose, "runtime_selection": runtime_selection,
                "pass_index": pass_index, "global_keywords": globals_, "local_keywords": locals_,
                "serialized_enabled_pass_mask": material.get("m_EnabledPassMask"),
                "serialized_disabled_passes": disabled,
                "material_pid": str(material_pid), "shader_pid": str(shader_entry["pathID"]),
                "block": shader_entry["block"], "cab": shader_entry["cab"],
                "native_json": str(native_path), "native_sha256": native_sha,
                "audit": str(audit_path), "audit_sha256": file_hash(audit_path), "programs": programs}
    if project_configured:
        evidence["configuration_mode"] = "ProjectConfigured"
        if "depth_bias" in resolved:
            evidence["project_depth_bias"] = resolved["depth_bias"]
    if vertex_texture is not None:
        evidence["vertex_deformation"] = vertex_texture
    if feature_off:
        evidence.update(adaptation=adaptation, feature_off_contract=configuration["feature_off"],
                        audit_role="FragmentCandidateProvenanceOnly", original_stage_pair_verified=False,
                        vertex_deformation=configuration["feature_off"]["vertex_deformation"])
        evidence["stage_keywords"] = {row["stage"]: {"global": row["globalKeywords"], "local": row["localKeywords"]}
                                      for row in audit["matches"]}
        evidence["serialized_keywords"] = serialized
        evidence.pop("global_keywords")
        evidence.pop("local_keywords")
    if zero_variant:
        evidence.update(zero_contribution_variant=configuration["zero_contribution_variant"],
            serialized_keywords=serialized, selected_keywords=selected_keywords,
            original_serialized_variant_obtained=False, original_runtime_pair_verified=False)
    if enum_evidence:
        evidence.update(keyword_enum_properties=enum_evidence, serialized_keywords=serialized,
                        selected_keywords=selected_keywords, original_runtime_pair_verified=False)
    if stage_keywords is not None:
        evidence.update(stage_keywords=stage_keywords, serialized_keywords=serialized,
                        stage_selection_reason=configuration["stage_selection_reason"],
                        original_runtime_pair_verified=False)
        evidence.pop("global_keywords")
        evidence.pop("local_keywords")
    if environment is not None:
        if equivalent:
            if str(material_pid) == UE.SHADOW_PID:
                derived, adaptation = UE.derive_shadow_base({stage: selected[stage] for stage in ("vp", "fp")}, programs)
                selected.update(derived)
                evidence["adaptation"] = adaptation
            UE.validate_depth_sampling(selected["fp"])
            selected["execution_environment"] = UE.environment(selected["fp"], configuration["lighting"])
        elif project_configured:
            adaptation = None
            if environment == PROJECT_SHADOW:
                derived, adaptation = derive_project_shadow_base({stage: selected[stage] for stage in ("vp", "fp")},
                    programs, material, material_pid, configuration.get("shadow_base_contract"))
                selected.update(derived)
                evidence["adaptation"] = adaptation
            selected["execution_environment"] = project_environment(environment, selected["fp"], material_pid, adaptation, depth_velocity)
        else:
            selected["execution_environment"] = fragment_environment(environment, selected["fp"])
        evidence["execution_environment"] = selected["execution_environment"]
        evidence["render_state"] = {"native": state, "resolved_target0": {
            k: state_value(v, material["m_SavedProperties"]["m_Floats"], props)
            for k, v in state["rtBlend"][0].items()}}
    return {"props": props, "passes": [selected]}, evidence
