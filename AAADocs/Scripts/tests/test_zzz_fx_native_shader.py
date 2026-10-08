"""验证候选预览不能掩盖源字节、运行态选择和原生渲染状态缺口。"""
import copy
import hashlib
import json
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
import zzz_fx_build as B
import zzz_fx_material as F
import zzz_fx_native_shader as N
from test_zzz_fx_batch_safety import WorkspaceTemporaryDirectory


def fixed(value):
    return {"name": "<noninit>", "val": value}


def state():
    stencil = {"comp": fixed(8), "pass": fixed(0), "fail": fixed(0), "zFail": fixed(0)}
    return {"rtBlend": [{"srcBlend": {"name": "_SrcFactor", "val": 0},
                         "destBlend": {"name": "_DstFactor", "val": 0},
                         "blendOp": fixed(0), "colMask": fixed(15)}],
            "rtSeparateBlend": False, "stencilOp": stencil, "stencilOpFront": stencil,
            "stencilOpBack": stencil, "offsetFactor": fixed(0), "offsetUnits": fixed(0),
            "zClip": fixed(1), "alphaToMask": fixed(0),
            "culling": {"name": "_Cull", "val": 0}, "zWrite": {"name": "_ZWrite", "val": 0},
            "zTest": {"name": "_ZTest", "val": 0}}


def halfres_state():
    item = state()
    item["rtSeparateBlend"] = True
    item["rtBlend"][0] = {"srcBlend": {"name": "_HalfResSrcFactor", "val": 0},
        "destBlend": {"name": "_HalfResDstFactor", "val": 0},
        "srcBlendAlpha": {"name": "_HalfResSrcAlphaFactor", "val": 0},
        "destBlendAlpha": {"name": "_HalfResDstAlphaFactor", "val": 0},
        "blendOp": fixed(0), "blendOpAlpha": fixed(0), "colMask": fixed(15)}
    return item


def halfres_floats():
    return {"_HalfResSrcFactor": 1, "_HalfResDstFactor": 5, "_HalfResSrcAlphaFactor": 7,
            "_HalfResDstAlphaFactor": 0, "_SrcFactor": 1, "_DstFactor": 10,
            "_Cull": 0, "_ZWrite": 0, "_ZTest": 4}


def halfres_fixture(directory):
    """两个 Pass、可核字节及原关键字，不能通过换 Pass 或删关键字取得预览。"""
    shader_file = directory / "2.shader"
    shader_file.write_text("source Shader text", encoding="utf-8")
    native_file = directory / "2.native.json"
    native_state = halfres_state()
    native_state.update({"m_Name": "TransparentHalfRes", "m_Tags": {"tags": [
        {"Key": "LIGHTMODE", "Value": "TransparentHalfRes"}]}})
    native_file.write_text(json.dumps({"m_ParsedForm": {"m_Name": "UnitTest/Shader",
        "m_PropInfo": {"m_Props": []}, "m_SubShaders": [{"m_Passes": [
            {"m_State": copy.deepcopy(native_state)}, {"m_State": native_state}]}]}}), encoding="utf-8")
    keywords = ["_DITHER_FROM_CAMERA", "_RAMPTEX_ON", "_USEDISTORTIONTEXTURE2_ON",
                "_USEDISTORTIONTEXTURE_ON", "_USEMASK_ON"]
    material = {"m_Name": "UnitTestMaterial", "m_Shader": {"m_PathID": 2},
        "m_ShaderKeywords": " ".join(keywords), "m_DisabledShaderPasses": [], "m_EnabledPassMask": 1,
        "m_SavedProperties": {"m_Floats": halfres_floats(), "m_Colors": {}, "m_TexEnvs": {}}}
    material_file = directory / "1.native.json"
    material_file.write_text(json.dumps(material), encoding="utf-8")
    audit = {"shaderPathID": 2, "shaderName": "UnitTest/Shader", "materialPathID": 1,
             "sourceShader": str(shader_file), "serializedMaterialKeywords": keywords, "matches": []}
    for stage, profile in (("vp", "vs_5_0"), ("fp", "ps_5_0")):
        program = directory / (stage + ".txt")
        semantic = "SV_Target" if stage == "fp" else "SV_POSITION"
        raw = ('SubProgram "d3d11 " {\nLocal Keywords { ' + ' '.join('"' + k + '"' for k in keywords)
               + ' }\n"// hash: 0123456789abcdef\n// Output signature:\n//\n'
               '// Name Index Mask Register SysValue Format Used\n// -------------------------------------\n'
               '// ' + semantic + ' 0 xyzw 0 TARGET float xyzw\n//\n' + profile + '\n'
               'dcl_output o0.xyzw\nmov o0.xyzw, l(0.200000, 0.100000, 0.000000, 0.750000)\n'
               '// Approximately 1 instruction slots used\n//@ CBBIND UnityPerMaterial 0\n'
               '//@ CB UnityPerMaterial 16\n}\n').encode("utf-8")
        program.write_bytes(raw)
        audit["matches"].append({"stage": stage, "passIndex": 1, "globalKeywords": [],
            "localKeywords": keywords, "file": str(program), "sha256": hashlib.sha256(raw).hexdigest(),
            "hash64": "0123456789abcdef"})
    audit_file = directory / "selection.json"
    audit_file.write_text(json.dumps(audit), encoding="utf-8")
    entry = {"type": "Shader", "pathID": 2, "name": "UnitTest/Shader", "cab": "CAB_Test",
             "block": "Test", "nativeJson": str(native_file), "files": [str(shader_file)]}
    config = {"purpose": "source_program_preview", "pass_index": 1, "global_keywords": [],
              "audit": str(audit_file), "execution_environment": N.TRANSMITTANCE_PREVIEW}
    return entry, material, material_file, config, audit, native_state


class NativeSourceTests(unittest.TestCase):
    def test_exact_native_candidate_plan_keeps_runtime_selection_unverified(self):
        with WorkspaceTemporaryDirectory() as directory:
            directory = Path(directory)
            shader_file = directory / "2.shader"
            shader_file.write_text("source Shader text", encoding="utf-8")
            native_file = directory / "2.native.json"
            native_state = state()
            native_state.update({"m_Name": "TransparentFullRes", "m_Tags": {"tags": [
                {"Key": "LIGHTMODE", "Value": "TransparentFullRes"}]}})
            native_file.write_text(json.dumps({"m_ParsedForm": {"m_Name": "UnitTest/Shader",
                "m_PropInfo": {"m_Props": []}, "m_SubShaders": [{"m_Passes": [{"m_State": native_state}]}]}}),
                encoding="utf-8")
            floats = {"_SrcFactor": 1, "_DstFactor": 10, "_Cull": 0, "_ZWrite": 0, "_ZTest": 4}
            material = {"m_Name": "UnitTestMaterial", "m_Shader": {"m_PathID": 2},
                "m_ShaderKeywords": "_MASK_ON", "m_DisabledShaderPasses": [], "m_EnabledPassMask": 1,
                "m_SavedProperties": {"m_Floats": floats, "m_Colors": {}, "m_TexEnvs": {}}}
            material_file = directory / "1.native.json"
            material_file.write_text(json.dumps(material), encoding="utf-8")
            audit = {"shaderPathID": 2, "shaderName": "UnitTest/Shader", "materialPathID": 1,
                     "sourceShader": str(shader_file), "serializedMaterialKeywords": ["_MASK_ON"], "matches": []}
            for stage, profile in (("vp", "vs_5_0"), ("fp", "ps_5_0")):
                program = directory / (stage + ".txt")
                raw = ('SubProgram "d3d11 " {\nLocal Keywords { "_MASK_ON" }\n'
                       '"// hash: 0123456789abcdef\n' + profile + '\n'
                       'mov o0.xyzw, l(1.000000, 0.000000, 0.000000, 1.000000)\n'
                       '// Approximately 1 instruction slots used\n//@ CBBIND UnityPerMaterial 0\n'
                       '//@ CB UnityPerMaterial 16\n}\n').encode("utf-8")
                program.write_bytes(raw)
                audit["matches"].append({"stage": stage, "passIndex": 0, "globalKeywords": [],
                    "localKeywords": ["_MASK_ON"], "file": str(program),
                    "sha256": hashlib.sha256(raw).hexdigest(), "hash64": "0123456789abcdef"})
            audit_file = directory / "selection.json"
            audit_file.write_text(json.dumps(audit), encoding="utf-8")
            entry = {"type": "Shader", "pathID": 2, "name": "UnitTest/Shader", "cab": "CAB_Test",
                     "block": "Test", "nativeJson": str(native_file), "files": [str(shader_file)]}
            config = {"purpose": "source_program_preview", "pass_index": 0, "global_keywords": [],
                      "audit": str(audit_file)}
            plan = F.plan(material_file, {"kind": "particle", "mesh": False, "uv_count": 1,
                          "custom_streams": False}, {}, shader_name="UnitTest/Shader", native_source={
                              "shader_entry": entry, "material_pid": 1, "selection": config})
            self.assertTrue(plan["two_sided"])
            self.assertEqual(plan["blend"], "BLEND_AlphaComposite")
            self.assertEqual(plan["source_selection"]["runtime_selection"], "unverified")
            self.assertEqual(plan["source_selection"]["programs"]["fp"]["sha256"], audit["matches"][1]["sha256"])
            material["m_DisabledShaderPasses"] = ["TransparentFullRes"]
            with self.assertRaisesRegex(N.NativeShaderError, "disabled"):
                N.select_native(entry, material, 1, config)

    def test_parameterized_render_state_uses_bound_source_property(self):
        floats = {"_SrcFactor": 1, "_DstFactor": 10, "_SrcBlend": 1, "_DstBlend": 0,
                  "_Cull": 0, "_ZWrite": 0, "_ZTest": 4}
        lines, resolved = N.render_state(state(), floats, {})
        self.assertEqual(lines, ["Blend One OneMinusSrcAlpha"])
        self.assertEqual(resolved, {"cull": 0, "zwrite": 0, "ztest": 4})

    def test_missing_bound_source_property_does_not_use_serialized_zero(self):
        with self.assertRaisesRegex(N.NativeShaderError, "Missing source"):
            N.state_value({"name": "_ZTest", "val": 0}, {}, {})

    def test_independent_rt_blend_requires_explicit_environment(self):
        item = state()
        item["rtSeparateBlend"] = True
        with self.assertRaisesRegex(N.NativeShaderError, "explicit output environment"):
            N.render_state(item, {}, {})

    def test_transmittance_environment_preserves_exact_pass_programs_and_state(self):
        with WorkspaceTemporaryDirectory() as directory:
            entry, material, path, config, audit, original = halfres_fixture(Path(directory))
            before = {p: p.read_bytes() for p in Path(directory).iterdir()}
            plan = F.plan(path, {"kind": "particle", "mesh": False, "uv_count": 1,
                          "custom_streams": False}, {}, shader_name="UnitTest/Shader", native_source={
                              "shader_entry": entry, "material_pid": 1, "selection": config})
            source = plan["source_selection"]
            self.assertEqual(plan["pass"], "TransparentHalfRes")
            self.assertEqual(source["pass_index"], 1)
            self.assertEqual(source["local_keywords"], sorted(audit["serializedMaterialKeywords"]))
            self.assertEqual(source["global_keywords"], [])
            self.assertEqual(source["programs"]["fp"]["sha256"], audit["matches"][1]["sha256"])
            self.assertEqual(source["render_state"]["native"], original)
            self.assertEqual(source["render_state"]["resolved_target0"]["destBlend"], 5)
            self.assertEqual(plan["blend"], "BLEND_AlphaComposite")
            self.assertTrue(plan["code"].endswith("return float4(c.rgb, 1.0 - c.a);\n"))
            environment = source["execution_environment"]
            self.assertEqual(environment["source_halfres_pipeline"], "unverified_not_implemented")
            self.assertEqual(environment["destination_alpha_equivalence"], "not_implemented")
            self.assertEqual(source["runtime_selection"], "unverified")
            self.assertEqual(before, {p: p.read_bytes() for p in Path(directory).iterdir()})
            config.pop("execution_environment")
            with self.assertRaisesRegex(N.NativeShaderError, "explicit output environment"):
                N.select_native(entry, material, 1, config)
            config.update(execution_environment=N.TRANSMITTANCE_PREVIEW, pass_index=0)
            with self.assertRaisesRegex(N.NativeShaderError, "found 0"):
                N.select_native(entry, material, 1, config)

    def test_transmittance_preview_rejects_incompatible_native_state(self):
        N.render_state(halfres_state(), halfres_floats(), {}, N.TRANSMITTANCE_PREVIEW)
        changes = {"srcBlend": 5, "destBlend": 10, "srcBlendAlpha": 1,
                   "destBlendAlpha": 1, "blendOp": 1, "blendOpAlpha": 1, "colMask": 7}
        for key, value in changes.items():
            with self.subTest(key=key):
                item = halfres_state()
                item["rtBlend"][0][key] = fixed(value)
                with self.assertRaisesRegex(N.NativeShaderError, "One/SrcAlpha"):
                    N.render_state(item, halfres_floats(), {}, N.TRANSMITTANCE_PREVIEW)
        item = halfres_state()
        del item["rtBlend"][0]["blendOpAlpha"]
        with self.assertRaisesRegex(N.NativeShaderError, "complete native"):
            N.render_state(item, halfres_floats(), {}, N.TRANSMITTANCE_PREVIEW)
        with self.assertRaisesRegex(N.NativeShaderError, "Unknown"):
            N.render_state(state(), {}, {}, "implicit_halfres")

    def test_transmittance_preview_rejects_mrt_partial_and_depth_outputs(self):
        output = {"name": "SV_Target", "index": 0, "reg": 0, "mask": "xyzw"}
        valid = {"out": [output], "asm": ["ps_5_0", "dcl_output o0.xyzw"]}
        N.fragment_environment(N.TRANSMITTANCE_PREVIEW, valid)
        for outputs in ([], [dict(output, mask="xyz")], [dict(output, reg=1)],
                        [dict(output, name="SV_Depth")], [output, dict(output, index=1, reg=1)]):
            with self.subTest(outputs=outputs):
                with self.assertRaisesRegex(N.NativeShaderError, "exactly one"):
                    N.fragment_environment(N.TRANSMITTANCE_PREVIEW, dict(valid, out=outputs))
        with self.assertRaisesRegex(N.NativeShaderError, "extra native"):
            N.fragment_environment(N.TRANSMITTANCE_PREVIEW, dict(valid,
                asm=valid["asm"] + ["dcl_output_siv oDepth, depth"]))

    def test_adapter_rgb_matches_native_blending_across_ordered_fragments(self):
        background = (0.15, 0.4, 0.8)
        fragments = [((0.2, 0.0, 0.1), 0.75), ((0.05, 0.3, 0.0), 0.4), ((0, 0, 0), 1)]
        for ordered in (fragments, list(reversed(fragments)), [((0.2, 0.3, 0.4), 0)]):
            native, ue = background, background
            for rgb, transmittance in ordered:
                native = tuple(s + d * transmittance for s, d in zip(rgb, native))
                opacity = 1 - transmittance
                ue = tuple(s + d * (1 - opacity) for s, d in zip(rgb, ue))
                for actual, expected in zip(ue, native):
                    self.assertAlmostEqual(actual, expected)

    def test_active_stencil_requires_its_output_contract(self):
        item = state()
        item["stencilOp"] = {"comp": fixed(4), "pass": fixed(0), "fail": fixed(0), "zFail": fixed(0)}
        with self.assertRaisesRegex(N.NativeShaderError, "stencil"):
            N.render_state(item, {}, {})

    def test_native_selection_has_no_implicit_preview_or_global_keyword_choice(self):
        with self.assertRaisesRegex(N.NativeShaderError, "explicit source_program_preview"):
            N.select_native({}, {}, 1, {})
        with self.assertRaisesRegex(N.NativeShaderError, "Explicit pass index"):
            N.select_native({}, {}, 1, {"purpose": "source_program_preview", "pass_index": 0})

    def test_native_preview_configuration_cannot_be_applied_as_complete_prefab(self):
        with self.assertRaisesRegex(ValueError, "source subtree preview"):
            B.preflight("unused.fx.json", assets={}, native_selections={})

    def test_program_byte_digest_and_candidate_ambiguity_are_strict(self):
        with WorkspaceTemporaryDirectory() as directory:
            path = Path(directory) / "program.txt"
            text = ('SubProgram "d3d11 " {\nLocal Keywords { "_MASK_ON" }\n'
                    '"// hash: 0123456789abcdef\nvs_5_0\nmov o0.xyzw, v0.xyzw\n'
                    '// Approximately 1 instruction slots used\n//@ CBBIND UnityPerMaterial 0\n'
                    '//@ CB UnityPerMaterial 16\n}\n')
            raw = text.encode("utf-8")
            path.write_bytes(raw)
            row = {"stage": "vp", "passIndex": 0, "globalKeywords": [], "localKeywords": ["_MASK_ON"],
                   "file": str(path), "sha256": hashlib.sha256(raw).hexdigest(), "hash64": "0123456789abcdef"}
            program, evidence = N.program_from_audit({"matches": [row]}, "vp", 0, [], ["_MASK_ON"])
            self.assertEqual(program["asm"][0], "vs_5_0")
            self.assertEqual(evidence["sha256"], row["sha256"])
            with self.assertRaisesRegex(N.NativeShaderError, "found 2"):
                N.program_from_audit({"matches": [row, row]}, "vp", 0, [], ["_MASK_ON"])
            path.write_bytes(raw.replace(b"\n", b"\r\n"))
            with self.assertRaisesRegex(N.NativeShaderError, "byte digest"):
                N.program_from_audit({"matches": [row]}, "vp", 0, [], ["_MASK_ON"])


if __name__ == "__main__":
    unittest.main()
