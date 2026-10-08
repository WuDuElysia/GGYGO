"""验证候选预览不能掩盖源字节、运行态选择和原生渲染状态缺口。"""
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

    def test_separate_alpha_requires_its_output_contract(self):
        item = state()
        item["rtSeparateBlend"] = True
        with self.assertRaisesRegex(N.NativeShaderError, "Separate alpha"):
            N.render_state(item, {}, {})

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
