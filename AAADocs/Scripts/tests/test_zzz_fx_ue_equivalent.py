"""Verify the explicit UE smoke environment without using an editor executor."""
import copy
import contextlib
import io
import json
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import zzz_dxbc_hlsl as T
import zzz_fx_build as B
import zzz_fx_material as F
import zzz_fx_native_shader as N
import zzz_fx_ue_equivalent as UE

CONFIG = Path(__file__).parents[2] / "Assets/Shared/FX/ZZZ_FX_EvadeSmokes_UEEquivalent.json"


class UEEnvironmentTests(unittest.TestCase):
    def test_configuration_preserves_all_five_source_keyword_contracts(self):
        data = UE.configuration(CONFIG)
        self.assertEqual(set(data["materials"]), set(UE.MATERIAL_KEYWORDS))
        self.assertEqual(set(data["prefabs"]), set(UE.PREFABS))
        for mid, row in data["materials"].items():
            audit = N.read_json(row["audit"])
            self.assertEqual(sorted(audit["serializedMaterialKeywords"]), UE.MATERIAL_KEYWORDS[mid])
            for stage in ("vp", "fp"):
                program, _ = N.program_from_audit(audit, stage, 1, [], UE.MATERIAL_KEYWORDS[mid])
                if stage == "fp":
                    UE.validate_depth_sampling(program)

    def test_source_keywords_and_explicit_stage_policy_cannot_be_omitted(self):
        data = UE.configuration(CONFIG)
        mid = UE.SHADOW_PID
        selection = data["materials"][mid]
        entry = {"pathID": UE.SHADER_PID, "cab": UE.SHADER_CAB}
        with self.assertRaisesRegex(ValueError, "all original local keywords"):
            UE.validate_source(mid, entry, ["_SOFTPARTICLES_ON"], selection)
        wrong = {**selection, "global_keywords": ["_DITHER_SWITCH"]}
        with self.assertRaisesRegex(ValueError, "pass/global/lighting"):
            UE.validate_source(mid, entry, UE.MATERIAL_KEYWORDS[mid], wrong)
        with self.assertRaisesRegex(ValueError, "different source Shader"):
            UE.validate_source(mid, {**entry, "cab": "CAB_Another"}, UE.MATERIAL_KEYWORDS[mid], selection)

    def test_derived_shadow_base_keeps_source_bytes_and_base_alpha_operations(self):
        data = UE.configuration(CONFIG)
        audit = N.read_json(data["materials"][UE.SHADOW_PID]["audit"])
        programs, evidence = {}, {}
        for stage in ("vp", "fp"):
            programs[stage], evidence[stage] = N.program_from_audit(audit, stage, 1, [], UE.MATERIAL_KEYWORDS[UE.SHADOW_PID])
        before = copy.deepcopy(programs)
        derived, contract = UE.derive_shadow_base(programs, evidence)
        self.assertEqual(programs, before)
        self.assertEqual(derived["fp"]["asm"], programs["fp"]["asm"][:84] + programs["fp"]["asm"][93:107]
                         + ["mov r2.w, r0.x"] + programs["fp"]["asm"][112:])
        self.assertFalse(any("sample_c" in line for line in derived["vp"]["asm"]))
        self.assertEqual(contract["shadow_alpha"], "source_base_alpha_only_reference_calibration_pending")
        provider = UE.provider(F.load_globals()[0])
        ps = T.translate(derived["fp"], "b", provider, {0: "xyzw"})
        self.assertNotIn(("v9", "w"), ps["live_inputs"])
        self.assertFalse(any(name == "_VfxShadowInfoMatrix" or (name == "_MainLightColor" and comp == "w")
                             for name, _, comp in ps["globals"]))
        needed = {}
        for row in derived["fp"]["in"]:
            comps = {c for var, c in ps["live_inputs"] if var == "v%d" % row["reg"] and c in row["mask"]}
            if comps and row["sys"] == "NONE":
                vo = next(v for v in derived["vp"]["out"] if (v["name"], v["index"]) == (row["name"], row["index"]))
                needed.setdefault(vo["reg"], set()).update(comps)
        vs = T.translate(derived["vp"], "a", provider, {r: "".join(sorted(c)) for r, c in needed.items()})
        self.assertFalse(any(name.startswith("_MainLightShadow") or name == "_MainLightWorldToShadow" for name, _, _ in vs["globals"]))
        bad = copy.deepcopy(evidence)
        bad["fp"]["sha256"] = "changed"
        with self.assertRaisesRegex(ValueError, "Unverified source shadow program"):
            UE.derive_shadow_base(programs, bad)
        changed = copy.deepcopy(programs)
        changed["fp"]["asm"][111] = "mov r2.w, l(1.000000)"
        with self.assertRaisesRegex(ValueError, "instruction boundaries"):
            UE.derive_shadow_base(changed, evidence)

    def test_depth_adapter_is_green_lod_zero_and_does_not_change_default_provider(self):
        original, _ = F.load_globals()
        before = copy.deepcopy(original)
        equivalent = UE.provider(original)
        self.assertEqual(original, before)
        self.assertNotIn("_DepthMipChain", original["__textures__"])
        self.assertIn("float4(0.0, 1.0 /", equivalent["__textures__"]["_DepthMipChain"])
        self.assertNotIn("_VfxShadowInfoMatrix", equivalent)
        data = UE.configuration(CONFIG)
        audit = N.read_json(data["materials"][UE.SHADOW_PID]["audit"])
        program, _ = N.program_from_audit(audit, "fp", 1, [], UE.MATERIAL_KEYWORDS[UE.SHADOW_PID])
        program["asm"] = [s.replace("l(0.000000)", "l(1.000000)") if s.startswith("sample_l") else s for s in program["asm"]]
        with self.assertRaisesRegex(ValueError, "LOD0 green-channel"):
            UE.validate_depth_sampling(program)

    def test_partial_equivalent_batch_cannot_reach_the_editor(self):
        plan = {"name": next(iter(UE.PREFABS)), "ue_environment": {"name": UE.MODE}}
        with self.assertRaisesRegex(ValueError, "complete Front/Back batch"):
            B.apply_batch([plan], None, [])

    def test_static_extra_uv_contract_is_explicit_and_keeps_atlas_channels(self):
        selectors = {key: 0 for key in ("_MainTexUVMode", "_MaskTexUVMode", "_DissolveTexUVMode", "_DistortionTexUVMode", "_DistortionTex2UVMode")}
        UE.validate_texture_uv_modes(selectors)
        with self.assertRaisesRegex(ValueError, "primary texture UV selectors"):
            UE.validate_texture_uv_modes({**selectors, "_MainTexUVMode": 5})
        context = {"builtins": set(), "mesh": False, "uv_count": 1, "sprite_subuv": False}
        with self.assertRaises(F.PlanError):
            F.stream_component("UV2", 0, context)
        with self.assertRaises(F.PlanError):
            F.stream_component("UV3", 1, context)
        context.update({"sprite_static_quad_uv": True, "sprite_extra_quad_uv": True})
        self.assertEqual(F.stream_component("UV2", 0, context), "UV0.x")
        self.assertEqual(F.stream_component("UV3", 1, context), "(1.0 - UV0.y)")
        context.update({"sprite_subuv": True, "sprite_uv_tiles": (10, 5)})
        self.assertEqual(F.stream_component("UV2", 0, context), F.PU.stream_component("UV2", 0, (10, 5)))

    def test_lit_material_environment_requires_the_full_contract(self):
        program = {"out": [{"name": "SV_Target", "index": 0, "reg": 0, "mask": "xyzw"}], "asm": ["dcl_output o0.xyzw"]}
        environment = UE.environment(program, "ue_volumetric_nondirectional")
        self.assertEqual(UE.material_properties(environment)["ShadingModel"], "MSM_DefaultLit")
        with self.assertRaisesRegex(ValueError, "pass/fog contract"):
            UE.material_properties({**environment, "native_scene_fog": False})
        with self.assertRaisesRegex(ValueError, "no material contract"):
            UE.material_properties({**environment, "lighting": "constant_shadow"})

    def test_cli_uses_the_same_explicit_revision_for_import_and_render_targets(self):
        data = UE.configuration(CONFIG)
        paths = list(data["prefabs"].values())
        plans = [{"name": name, "renderers": UE.RENDERERS[name], "ue_environment": {"name": UE.MODE}}
                 for name in data["prefabs"]]
        with patch.object(sys, "argv", ["zzz_fx_build.py", *paths, "--ue-equivalent", str(CONFIG), "--plan-imports"]), \
             patch("zzz_fx_import_assets.plan_imports", return_value={"assets": {}}) as imports, \
             patch.object(B, "preflight", side_effect=plans) as preflight, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(B.main(), 0)
        self.assertEqual(imports.call_args.args[1], data["revision"])
        self.assertEqual([call.kwargs["revision"] for call in preflight.call_args_list], [data["revision"]] * 2)

    def test_all_seven_viewport_graphs_keep_native_custom_array_position_and_alpha_contracts(self):
        from test_zzz_fx_particle_modules import RecordingMaterialGraph, source_rows, POLICY
        import zzz_fx_particle_renderer as R
        from zzz_fx_material_ue import Builder

        class NativePinsGraph(RecordingMaterialGraph):
            """UE 5.8 pin contract, including the actual MCP TransformPosition readback.

            MaterialGraphNode shortens Input to NAME_None; the tools expose
            'None'. MaterialEditingLibrary also accepts '' for the first pin.
            """
            def tool(self, name, **args):
                if name.endswith(".set_properties"):
                    values = json.loads(args["values"])
                    if "Inputs" in values:
                        old = self.nodes[args["instance"]["refPath"]]["Inputs"]
                        new = values["Inputs"]
                        if len(old) != len(new) and old[:min(len(old), len(new))] != new[:min(len(old), len(new))]:
                            raise ValueError("ArrayAdd: elements changed alongside size change; insertion points are ambiguous")
                if name.endswith(".connect_expressions"):
                    src = self.classes[args["from_expression"]["refPath"]].rsplit(".", 1)[1]
                    dst_path = args["to_expression"]["refPath"]
                    dst = self.classes[dst_path].rsplit(".", 1)[1]
                    if dst in ("MaterialExpressionTransformPosition", "MaterialExpressionComponentMask"):
                        valid_inputs = ("None", "")
                    elif dst == "MaterialExpressionCustom":
                        valid_inputs = [v["inputName"] for v in self.nodes[dst_path]["Inputs"]]
                    else:
                        raise AssertionError("Unaudited destination node: " + dst)
                    if args["to_input_name"] not in valid_inputs:
                        raise ValueError("Failed to connect to native input %r on %s" % (args["to_input_name"], dst))
                    named_outputs = {
                        "MaterialExpressionParticleColor": ("RGB", "R", "G", "B", "A", "RGBA"),
                        "MaterialExpressionVertexColor": ("R", "G", "B", "A"),
                        "MaterialExpressionVectorParameter": ("RGB", "R", "G", "B", "A", "RGBA"),
                        "MaterialExpressionDynamicParameter": ("Param1", "Param2", "Param3", "Param4", "RGB", "RGBA"),
                    }
                    if args["from_output_name"] and args["from_output_name"] not in named_outputs.get(src, ()):
                        raise AssertionError("Invalid native output on " + src)
                return super().tool(name, **args)

        program = {"out": [{"name": "SV_Target", "index": 0, "reg": 0, "mask": "xyzw"}],
                   "asm": ["dcl_output o0.xyzw"]}
        rows = source_rows("Front") + source_rows("Back")
        self.assertEqual(len(rows), 7)
        for node, path in rows:
            with self.subTest(node="/".join(p["name"] for p in path)):
                viewport = R.viewport_plan(node["particle"]["renderer"], POLICY, node["name"])
                graph, saved = NativePinsGraph(), []
                session = SimpleNamespace(m=graph, begin_create=lambda p: None, created_asset=lambda p: None, save=saved.append)
                plan = {"master": "M_NativePinFixture", "shader": "Graph fixture", "renderer_kind": "particle", "mesh": False,
                        "blend": "BLEND_AlphaComposite", "two_sided": True, "disable_depth_test": False,
                        "builtins": ["CamPos", "PPos", "PCol", "VCol", "DP0", "UV0", "AtlasFrame"],
                        "params": {**viewport["params"], "Tint": {"dim": 4, "value": [1, 1, 1, 1]}},
                        "pixel_params": ["Tint"], "textures": {}, "code": "return float4(0.2, 0.1, 0.0, 0.5);",
                        "viewport_clamp": viewport,
                        "ue_environment": UE.environment(program, "ue_volumetric_nondirectional" if node["name"] == "Smoke_an (1)" else "unlit")}
                Builder(session).build_master(plan)
                customs = [p for p, klass in graph.classes.items() if klass.endswith(".MaterialExpressionCustom")]
                for custom in customs:
                    writes = [json.loads(args["values"]) for name, args in graph.calls
                              if name.endswith(".set_properties") and args["instance"]["refPath"] == custom]
                    self.assertEqual(set(writes[0]), {"Inputs"})
                    self.assertTrue(all(entry["inputName"] == "" for entry in writes[0]["Inputs"]))
                    self.assertEqual(len(writes[0]["Inputs"]), len(writes[1]["Inputs"]))
                links = [args for name, args in graph.calls if name.endswith(".connect_expressions")]
                transform = next(p for p, klass in graph.classes.items() if klass.endswith(".MaterialExpressionTransformPosition"))
                incoming = next(link for link in links if link["to_expression"]["refPath"] == transform)
                self.assertTrue(graph.classes[incoming["from_expression"]["refPath"]].endswith(".MaterialExpressionParticlePositionWS"))
                self.assertEqual((incoming["from_output_name"], incoming["to_input_name"]), ("", "None"))
                self.assertEqual(graph.nodes[transform]["TransformSourceType"], "TRANSFORMPOSSOURCE_World")
                self.assertEqual(graph.nodes[transform]["TransformType"], "TRANSFORMPOSSOURCE_View")
                center = next(link for link in links if link["to_input_name"] == "CenterView")
                self.assertEqual(center["from_expression"]["refPath"], transform)
                wpo = center["to_expression"]["refPath"]
                self.assertEqual(graph.nodes[wpo]["Code"], viewport["code"])
                outputs = {args["material_property"]: args["expression"]["refPath"]
                           for name, args in graph.calls if name.endswith(".connect_to_output")}
                self.assertEqual(outputs["MP_WorldPositionOffset"], wpo)
                alpha = outputs["MP_Opacity"]
                self.assertTrue(graph.classes[alpha].endswith(".MaterialExpressionComponentMask"))
                self.assertEqual({k: graph.nodes[alpha][k] for k in "RGBA"}, {"R": False, "G": False, "B": False, "A": True})
                self.assertEqual(len(saved), 1)


if __name__ == "__main__":
    unittest.main()
