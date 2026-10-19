"""Explicit UE environment for the complete, audited Evade smoke prefabs.

Source programs stay immutable. The one shadow material has a separately
identified base-effect program: UE translucency supplies RGB lighting, while
the source shadow palette and shadow-dependent opacity await visual calibration.
This module owns no runtime lighting state or ability lifecycle.
"""
import copy
import hashlib
import json
from pathlib import Path

MODE = "ue_native_evade_smoke_environment_v1"
PURPOSE = "ue_equivalent_source_particles"
SHADER_PID = "-8861675102675100451"
SHADER_CAB = "CAB-3f3bc03f15709ec085bef31f4953663b"
SHADOW_PID = "-8783148842178813392"
MATERIAL_KEYWORDS = {
    "-8628735267290221435": ["_DITHER_FROM_CAMERA", "_RAMPTEX_ON", "_SOFTPARTICLES_ON"],
    "4815780514172297095": ["_DITHER_FROM_CAMERA", "_SOFT_EDGE_ON", "_USEDISSOLVETEX_ON", "_USEDISTORTIONTEXTURE_ON"],
    "54218374060949528": ["_DITHER_FROM_CAMERA", "_SOFTPARTICLES_ON"],
    "6221463485550019036": ["_SOFTPARTICLES_ON"],
    SHADOW_PID: ["_SOFTPARTICLES_ON", "_VFX_VOLUMETRIC_SHADOW"],
}
SHADOW_DIGESTS = {
    "vp": "8a142027181607ce0c1063579c41eb51067abd70e558a01fa5521820744c934d",
    "fp": "9796d3777b55ec5f1ba148e8fb8555d7a72f5d1d8d9fb18cd7f5f8b88119414a",
}
PREFABS = {"Eff_Pyrois_Evade_Front_01_Smoke": 4, "Eff_Pyrois_Evade_Back_01_Smoke": 3}
RENDERERS = {
    "Eff_Pyrois_Evade_Front_01_Smoke": ["World/root/Particle System (14)", "Local/root/smoke_trail",
                                         "Local/root/Particle System (13)", "Local/root/glow"],
    "Eff_Pyrois_Evade_Back_01_Smoke": ["World/root/Particle System (14)", "Local/Smoke_an (1)",
                                        "Local/root/Particle System (13)"],
}


def configuration(path):
    """Read the explicit machine configuration; never infer a normal mode."""
    path = Path(path)
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if data.get("schema_version") != 1 or data.get("mode") != MODE:
        raise ValueError("Unknown UE smoke environment configuration")
    if set(data["materials"]) != set(MATERIAL_KEYWORDS):
        raise ValueError("UE smoke configuration must contain exactly the five source materials")
    if data["calibration"] != "reference_visual_comparison_pending":
        raise ValueError("Source pixel equivalence has not been validated")
    if data.get("global_environment") != "explicit_clear_scene_calibration_baseline_with_native_UE_fog":
        raise ValueError("UE smoke global environment must be explicitly configured")
    if set(data["prefabs"]) != set(PREFABS):
        raise ValueError("UE smoke configuration requires the complete Front/Back pair")
    for mid, row in data["materials"].items():
        validate_selection(mid, row)
    return data


def validate_prefab(path, data, renderers):
    name = Path(path).name.removesuffix(".fx.json")
    expected = data["prefabs"].get(name)
    if expected is None or Path(path).resolve() != Path(expected).resolve() or renderers != RENDERERS[name]:
        raise ValueError("UE smoke plan must retain the exact source prefab and its complete renderer sequence")


def validate_batch(plans):
    equivalent = [p for p in plans if "ue_environment" in p]
    if not equivalent:
        return
    if len(equivalent) != len(plans) or len(plans) != len(PREFABS) or {p["name"] for p in plans} != set(PREFABS):
        raise ValueError("UE equivalent smoke apply requires the complete Front/Back batch")
    for plan in plans:
        if plan["renderers"] != RENDERERS[plan["name"]] or plan["ue_environment"]["name"] != MODE:
            raise ValueError("Incomplete or mismatched UE smoke environment batch")


def validate_selection(mid, selection):
    if mid not in MATERIAL_KEYWORDS:
        raise ValueError("UE smoke environment has no contract for material " + mid)
    expected = {"purpose": PURPOSE, "pass_index": 1, "global_keywords": [],
                "execution_environment": MODE,
                "lighting": "ue_volumetric_nondirectional" if mid == SHADOW_PID else "unlit"}
    if any(selection.get(key) != value for key, value in expected.items()):
        raise ValueError("Explicit UE smoke pass/global/lighting environment mismatch: " + mid)
    if not isinstance(selection.get("audit"), str) or not Path(selection["audit"]).is_file():
        raise ValueError("UE smoke source audit is missing: " + mid)


def validate_source(mid, entry, locals_, selection):
    validate_selection(mid, selection)
    if str(entry["pathID"]) != SHADER_PID or entry["cab"] != SHADER_CAB:
        raise ValueError("UE smoke environment points to a different source Shader")
    if sorted(locals_) != MATERIAL_KEYWORDS[mid]:
        raise ValueError("UE smoke environment must preserve all original local keywords: " + mid)


def derive_shadow_base(programs, evidence):
    """Extract this audited program's base colour/opacity, without a fake shadow.

    The guarded VP block only produces TEXCOORD12.w. The guarded FP blocks
    apply the custom shadow palette and opacity; their replacement routes the
    existing base opacity directly into its original power/fade operations.
    No shader variant or source keyword is removed, and no shadow sample is
    replaced with a constant. A changed original program fails explicitly.
    """
    for stage, digest in SHADOW_DIGESTS.items():
        if evidence[stage]["sha256"] != digest:
            raise ValueError("Unverified source shadow program structure: " + stage)
    derived = copy.deepcopy(programs)
    vp, fp = derived["vp"]["asm"], derived["fp"]["asm"]
    guards = [(vp, 114, "frc r4.xyw, r3.xyxz"),
              (vp, 313, "mad o9.w, r4.y, r3.w, r4.x"),
              (vp, 314, "ne r3.w, l(0.000000, 0.000000, 0.000000, 0.000000), cb3[58].z"),
              (fp, 84, "div_sat r1.xyz, cb0[7].xyzx, cb0[7].wwww"),
              (fp, 92, "mad r0.yzw, v9.wwww, r1.xxyz, r0.yyzw"),
              (fp, 107, "dp4 r0.y, cb0[188].xyzw, icb[r1.w + 0].xyzw"),
              (fp, 111, "mul_sat r2.w, r0.y, r0.x")]
    if len(vp) != 402 or len(fp) != 157 or any(asm[index] != line for asm, index, line in guards):
        raise ValueError("Source shadow instruction boundaries differ from the audited program")
    derived["vp"]["asm"] = vp[:114] + vp[314:]
    derived["fp"]["asm"] = fp[:84] + fp[93:107] + ["mov r2.w, r0.x"] + fp[112:]
    # Remove the unused shadow semantic from the derived stage interface only.
    derived["vp"]["out"] = [row for row in derived["vp"]["out"]
                             if not (row["name"] == "TEXCOORD" and row["index"] == 12)]
    derived["fp"]["in"] = [row for row in derived["fp"]["in"]
                            if not (row["name"] == "TEXCOORD" and row["index"] == 12)]
    identity = {stage: hashlib.sha256("\n".join(p["asm"]).encode()).hexdigest()
                for stage, p in derived.items()}
    return derived, {"implementation": "derived_source_base_effect_with_UE_lighting",
                     "derived_assembly_sha256": identity,
                     "removed_environment": ["source_shadowmap_sampling", "source_shadow_RGB_palette", "source_shadow_opacity_multiplier"],
                     "shadow_RGB": "UE_native_translucency_lighting",
                     "shadow_alpha": "source_base_alpha_only_reference_calibration_pending"}


def environment(program, lighting):
    outputs = program["out"]
    if len(outputs) != 1 or any(outputs[0].get(k) != v for k, v in
                              {"name": "SV_Target", "index": 0, "reg": 0, "mask": "xyzw"}.items()):
        raise ValueError("UE smoke environment requires a single complete source Target0")
    if [s for s in program["asm"] if s.startswith("dcl_output")] != ["dcl_output o0.xyzw"]:
        raise ValueError("UE smoke environment cannot consume extra native render outputs")
    return {"name": MODE, "blend": "BLEND_AlphaComposite", "output_conversion": "rgb,1-alpha",
            "lighting": lighting, "native_alpha_role": "transmittance", "ue_opacity": "1 - native.a",
            "translucency_pass": "MTP_BeforeDOF", "native_scene_fog": True,
            "disabled_sheet_uv_streams": "explicit_UE_static_quad_reference_calibration_pending",
            "extra_UV_streams": "UV3_UV4_UE_quad_reference_calibration_pending_source_UV_modes_zero",
            "lit_HDR_range": "UE_BaseColor_saturate_not_source_HDR_identity" if lighting != "unlit" else "source_HDR_emissive",
            "source_halfres_pipeline": "not_reproduced_UE_standard_translucency",
            "depth": "UE_SceneDepth_reciprocal_eye_metres_LOD0_G",
            "global_keywords": "explicit_UE_environment_selection_not_original_runtime_evidence",
            "calibration": "reference_visual_comparison_pending"}


def material_properties(environment):
    if environment.get("name") != MODE or environment.get("blend") != "BLEND_AlphaComposite":
        raise ValueError("Invalid UE smoke material environment")
    lighting = environment.get("lighting")
    if lighting not in ("unlit", "ue_volumetric_nondirectional"):
        raise ValueError("UE smoke lighting mode has no material contract")
    if environment.get("translucency_pass") != "MTP_BeforeDOF" or environment.get("native_scene_fog") is not True:
        raise ValueError("UE smoke pass/fog contract is missing")
    props = {"MaterialDomain": "MD_Surface", "ShadingModel": "MSM_Unlit" if lighting == "unlit" else "MSM_DefaultLit",
             "TranslucencyPass": "MTP_BeforeDOF", "bUseTranslucencyVertexFog": True}
    if lighting != "unlit":
        props["TranslucencyLightingMode"] = "TLM_VolumetricNonDirectional"
    return props


def validate_texture_uv_modes(floats):
    # This cohort uses the primary UV selector. The explicit extra-quad stream
    # environment is not a native alternate-UV reconstruction.
    keys = ("_MainTexUVMode", "_MaskTexUVMode", "_DissolveTexUVMode", "_DistortionTexUVMode", "_DistortionTex2UVMode")
    if any(key not in floats or floats[key] != 0 for key in keys):
        raise ValueError("UE smoke extra UV contract requires the original primary texture UV selectors")


def provider(source_provider):
    """Use the declared clear-scene calibration inputs, without altering defaults.

    Engine camera/time/world bindings keep their source conventions. Existing
    weather/fog/brightness values are an explicit calibration baseline, not
    recovered game globals. UE supplies its scene depth and native scene fog.
    Original shadow resources deliberately have no provider in this environment.
    """
    result = copy.deepcopy(source_provider)
    for name in ("_VfxShadowInfoMatrix", "_MainLightShadowmapTexture"):
        result.pop(name, None)
    result["__textures__"]["_DepthMipChain"] = (
        "float4(0.0, 1.0 / (CalcSceneDepth(ViewportUVToBufferUV({uv})) * 0.01), 0.0, 0.0)")
    return result


def validate_depth_sampling(program):
    for slot, texture in program["bind"]["tex"].items():
        if texture["name"] != "_DepthMipChain":
            continue
        import re
        import zzz_dxbc_hlsl as T
        samples = [s for s in program["asm"] if s.startswith("sample") and re.search(r"\bt%d\." % slot, s)]
        valid = bool(samples)
        for sample in samples:
            op, _, operands = T.split_instr(sample)
            valid = valid and op == "sample_l_indexable" and sample.startswith("sample_l_indexable(texture2d)")
            valid = valid and operands[-1].kind == "l" and operands[-1].lit == ["0.000000"]
            destination, texture = operands[0], operands[2]
            # The resource swizzle is indexed by the destination component,
            # not by the textual position of 'y' in the instruction.
            valid = valid and all(texture.swz["xyzw".index(c)] == "y" for c in destination.swz)
        if not valid:
            raise ValueError("UE smoke depth adapter requires the audited LOD0 green-channel source reads")
