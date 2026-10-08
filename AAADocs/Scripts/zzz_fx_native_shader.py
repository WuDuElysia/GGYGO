"""只读选择已取证的原生 Shader 程序，用于明确标识的独立候选预览。

本地关键字来自材质；Pass 与全局关键字必须由调用者显式指定。
候选存在不证明原游戏运行态选择，不导出或覆盖任何源文件。
"""
import hashlib
import json
import math
import re
from pathlib import Path

import zzz_dxbc_hlsl as T


class NativeShaderError(ValueError):
    pass


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


def render_state(state, floats, props):
    value = lambda item: state_value(item, floats, props)
    blend = state["rtBlend"][0]
    if state["rtSeparateBlend"] or value(blend["blendOp"]) != 0 or value(blend["colMask"]) != 15:
        raise NativeShaderError("Separate alpha blend, blend operation or color mask requires its native output contract")
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
    if resolved["cull"] not in (0, 2) or resolved["zwrite"] != 0 or resolved["ztest"] != 4:
        raise NativeShaderError("Native preview only supports source Off/Back cull, no ZWrite and LEqual: " + repr(resolved))
    factors = {0: "Zero", 1: "One", 2: "DstColor", 3: "SrcColor", 4: "OneMinusDstColor",
               5: "SrcAlpha", 6: "OneMinusSrcColor", 7: "DstAlpha", 8: "OneMinusDstAlpha",
               9: "SrcAlphaSaturate", 10: "OneMinusSrcAlpha"}
    src, dst = value(blend["srcBlend"]), value(blend["destBlend"])
    if src not in factors or dst not in factors:
        raise NativeShaderError("Unsupported native blend factors: " + repr((src, dst)))
    return ["Blend " + factors[src] + " " + factors[dst]], resolved


def program_from_audit(audit, stage, pass_index, globals_, locals_):
    matches = [row for row in audit["matches"] if row["stage"] == stage and row["passIndex"] == pass_index
               and set(row["globalKeywords"]) == set(globals_) and set(row["localKeywords"]) == set(locals_)]
    if len(matches) != 1:
        raise NativeShaderError("Expected one exact %s candidate for pass %s, found %s" % (stage, pass_index, len(matches)))
    row = matches[0]
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
    if actual_local != set(locals_) or actual_global != set(globals_):
        raise NativeShaderError("Native program keyword metadata mismatch: " + str(path))
    if not text.startswith('SubProgram "d3d11 ') or not re.search(r'// hash: ' + re.escape(row["hash64"]) + r'\b', text):
        raise NativeShaderError("Native program API/hash identity mismatch: " + str(path))
    program = T.parse_subprogram(text)
    profile = "vs_5_0" if stage == "vp" else "ps_5_0"
    if not program["asm"] or program["asm"][0] != profile or not program["bind"]["cbbind"]:
        raise NativeShaderError("Native program profile/reflection is missing: " + str(path))
    return program, {"file": str(path), "sha256": row["sha256"], "hash64": row["hash64"]}


def select_native(shader_entry, material, material_pid, configuration):
    if configuration.get("purpose") != "source_program_preview":
        raise NativeShaderError("Native source selection requires an explicit source_program_preview purpose")
    pass_index = configuration.get("pass_index")
    globals_ = configuration.get("global_keywords")
    if type(pass_index) is not int or pass_index < 0 or not isinstance(globals_, list) or any(
            not isinstance(k, str) for k in globals_) or len(globals_) != len(set(globals_)):
        raise NativeShaderError("Explicit pass index and unique global keyword list are required")
    audit_path = Path(configuration["audit"])
    audit = read_json(audit_path)
    locals_ = sorted((material.get("m_ShaderKeywords") or "").split())
    if str(audit["shaderPathID"]) != str(shader_entry["pathID"]) or audit["shaderName"] != shader_entry["name"]:
        raise NativeShaderError("Native Shader audit identity mismatch")
    if str(audit["materialPathID"]) != str(material_pid) or set(audit["serializedMaterialKeywords"]) != set(locals_):
        raise NativeShaderError("Native material audit identity/keywords mismatch")
    shader_files = [Path(p).resolve() for p in shader_entry["files"] if str(p).endswith(".shader")]
    if shader_files != [Path(audit["sourceShader"]).resolve()]:
        raise NativeShaderError("Native audit points to another Shader source")
    native_path = Path(shader_entry["nativeJson"])
    expected_native = Path(audit["sourceShader"]).with_suffix(".native.json").resolve()
    if native_path.resolve() != expected_native:
        raise NativeShaderError("Native state/Properties source differs from the audited Shader")
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
    lines, resolved = render_state(state, material["m_SavedProperties"]["m_Floats"], props)
    selected = {"name": state["m_Name"], "lightmode": lightmode, "state": lines, "resolved_state": resolved}
    programs = {}
    for stage in ("vp", "fp"):
        selected[stage], programs[stage] = program_from_audit(audit, stage, pass_index, globals_, locals_)
    evidence = {"purpose": "source_program_preview", "runtime_selection": "unverified",
                "pass_index": pass_index, "global_keywords": globals_, "local_keywords": locals_,
                "serialized_enabled_pass_mask": material.get("m_EnabledPassMask"),
                "serialized_disabled_passes": disabled,
                "material_pid": str(material_pid), "shader_pid": str(shader_entry["pathID"]),
                "block": shader_entry["block"], "cab": shader_entry["cab"],
                "native_json": str(native_path), "native_sha256": file_hash(native_path),
                "audit": str(audit_path), "audit_sha256": file_hash(audit_path), "programs": programs}
    return {"props": props, "passes": [selected]}, evidence
