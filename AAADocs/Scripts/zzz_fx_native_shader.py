"""只读选择原生 Shader 证据，供独立候选预览或显式 UE 等效生产环境。

执行入口的 Pass 与全局关键字必须显式指定；审计逐程序区分完整材质输入和源声明。
候选存在不证明原游戏运行态选择；派生实现另记身份，不覆盖源文件。
"""
import hashlib
import json
import math
import re
from pathlib import Path

import zzz_dxbc_hlsl as T
import zzz_fx_ue_equivalent as UE


class NativeShaderError(ValueError):
    pass


TRANSMITTANCE_PREVIEW = "ue_fullres_transmittance_fragment_preview"


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def file_hash(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def render_state(state, floats, props, execution_environment=None):
    if execution_environment not in (None, TRANSMITTANCE_PREVIEW, UE.MODE):
        raise NativeShaderError("Unknown native preview execution environment: " + str(execution_environment))
    value = lambda item: state_value(item, floats, props)
    blend = state["rtBlend"][0]
    if execution_environment is None:
        if state["rtSeparateBlend"] or value(blend["blendOp"]) != 0 or value(blend["colMask"]) != 15:
            raise NativeShaderError("Independent RT blend, blend operation or color mask requires an explicit output environment")
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
    if value(state["offsetFactor"]) != 0 or value(state["offsetUnits"]) != 0:
        raise NativeShaderError("Native depth offset is not implemented")
    if value(state["zClip"]) != 1 or value(state["alphaToMask"]) != 0:
        raise NativeShaderError("Native depth clip/alpha-to-coverage is not implemented")
    resolved = {"cull": value(state["culling"]), "zwrite": value(state["zWrite"]),
                "ztest": value(state["zTest"])}
    if resolved["cull"] not in (0, 2) or resolved["zwrite"] != 0 or resolved["ztest"] not in (4, 8):
        raise NativeShaderError("Native source only supports Off/Back cull, no ZWrite and LEqual/Always: " + repr(resolved))
    factors = {0: "Zero", 1: "One", 2: "DstColor", 3: "SrcColor", 4: "OneMinusDstColor",
               5: "SrcAlpha", 6: "OneMinusSrcColor", 7: "DstAlpha", 8: "OneMinusDstAlpha",
               9: "SrcAlphaSaturate", 10: "OneMinusSrcAlpha"}
    src, dst = value(blend["srcBlend"]), value(blend["destBlend"])
    if src not in factors or dst not in factors:
        raise NativeShaderError("Unsupported native blend factors: " + repr((src, dst)))
    line = "Blend " + factors[src] + " " + factors[dst]
    if execution_environment is not None:
        line += ", DstAlpha Zero"
    return [line], resolved


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


def _program_from_row(audit, row, stage, *, inspection_only=False):
    """复用原字节／声明核验；审计读取不取得渲染执行权限。"""
    if audit.get("hashScope") not in (None, "file_bytes") or row.get("hashScope") not in (None, "file_bytes"):
        raise NativeShaderError("Native program audit must certify unmodified file bytes")
    if row.get("fileBytesSha256", row["sha256"]) != row["sha256"]:
        raise NativeShaderError("Native program byte digest fields disagree")
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
    profiles = (prefix + "4_0", prefix + "5_0") if inspection_only else (prefix + "5_0",)
    if not program["asm"] or program["asm"][0] not in profiles or not program["bind"]["cbbind"]:
        raise NativeShaderError("Native program profile/reflection is missing: " + str(path))
    if row.get("profile", program["asm"][0]) != program["asm"][0]:
        raise NativeShaderError("Native program profile metadata mismatch: " + str(path))
    return program, {"file": str(path), "sha256": row["sha256"], "hash64": row["hash64"]}


def program_from_audit(audit, stage, pass_index, globals_, locals_):
    """执行入口仍要求唯一完整匹配，不采用只读候选审计的关键词投影。"""
    matches = [row for row in audit["matches"] if row["stage"] == stage and row["passIndex"] == pass_index
               and set(row["globalKeywords"]) == set(globals_) and set(row["localKeywords"]) == set(locals_)]
    if len(matches) != 1:
        raise NativeShaderError("Expected one exact %s candidate for pass %s, found %s" % (stage, pass_index, len(matches)))
    return _program_from_row(audit, matches[0], stage)


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
        candidate = {key: row[key] for key in
                     ("stage", "globalKeywords", "localKeywords", "file", "sha256")}
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


def select_native(shader_entry, material, material_pid, configuration):
    purpose = configuration.get("purpose")
    equivalent = purpose == UE.PURPOSE
    if purpose != "source_program_preview" and not equivalent:
        raise NativeShaderError("Native source selection requires an explicit source_program_preview or UE equivalent purpose")
    pass_index = configuration.get("pass_index")
    globals_ = configuration.get("global_keywords")
    if type(pass_index) is not int or pass_index < 0 or not isinstance(globals_, list) or any(
            not isinstance(k, str) for k in globals_) or len(globals_) != len(set(globals_)):
        raise NativeShaderError("Explicit pass index and unique global keyword list are required")
    audit_path = Path(configuration["audit"])
    audit = read_json(audit_path)
    native_path, locals_ = validate_audit_identity(shader_entry, material, material_pid, audit)
    if equivalent:
        UE.validate_source(str(material_pid), shader_entry, locals_, configuration)
    elif configuration.get("execution_environment") == UE.MODE:
        raise NativeShaderError("UE production environment requires its explicit equivalent purpose")
    native = read_json(native_path)["m_ParsedForm"]
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
    environment = configuration.get("execution_environment")
    lines, resolved = render_state(state, material["m_SavedProperties"]["m_Floats"], props, environment)
    selected = {"name": state["m_Name"], "lightmode": lightmode, "state": lines, "resolved_state": resolved}
    programs = {}
    for stage in ("vp", "fp"):
        selected[stage], programs[stage] = program_from_audit(audit, stage, pass_index, globals_, locals_)
    evidence = {"purpose": purpose, "runtime_selection": "explicit_UE_equivalent_not_source_runtime" if equivalent else "unverified",
                "pass_index": pass_index, "global_keywords": globals_, "local_keywords": locals_,
                "serialized_enabled_pass_mask": material.get("m_EnabledPassMask"),
                "serialized_disabled_passes": disabled,
                "material_pid": str(material_pid), "shader_pid": str(shader_entry["pathID"]),
                "block": shader_entry["block"], "cab": shader_entry["cab"],
                "native_json": str(native_path), "native_sha256": file_hash(native_path),
                "audit": str(audit_path), "audit_sha256": file_hash(audit_path), "programs": programs}
    if environment is not None:
        if equivalent:
            if str(material_pid) == UE.SHADOW_PID:
                derived, adaptation = UE.derive_shadow_base({stage: selected[stage] for stage in ("vp", "fp")}, programs)
                selected.update(derived)
                evidence["adaptation"] = adaptation
            UE.validate_depth_sampling(selected["fp"])
            selected["execution_environment"] = UE.environment(selected["fp"], configuration["lighting"])
        else:
            selected["execution_environment"] = fragment_environment(environment, selected["fp"])
        evidence["execution_environment"] = selected["execution_environment"]
        evidence["render_state"] = {"native": state, "resolved_target0": {
            k: state_value(v, material["m_SavedProperties"]["m_Floats"], props)
            for k, v in state["rtBlend"][0].items()}}
    return {"props": props, "passes": [selected]}, evidence
