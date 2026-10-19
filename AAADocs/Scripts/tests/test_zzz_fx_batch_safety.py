"""Regression checks for partial builds, existing assets and compile failures."""
import copy
import contextlib
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import zzz_fx_build as B
from zzz_fx_asset_session import AssetSession, AssetConflict
from zzz_fx_import_assets import plan_imports, texture_properties
from zzz_fx_niagara_ue import (NiagaraBuilder, snapshot_differences, partition_configuration_differences,
    NORMAL01_SYSTEM, NORMAL01_EMITTERS, FX_MESH_ROOT, normal01_orientation_expressions,
    normal01_orientation_plan, verify_normal01_mesh_basis)

SYSTEM = B.SYSTEM_DIR + "/NS_Test_Version"


class WorkspaceTemporaryDirectory(tempfile.TemporaryDirectory):
    def __init__(self):
        self.test_root = Path(__file__).parent.resolve()
        super().__init__(dir=self.test_root, prefix=".zzz_fx_test_")

    def cleanup(self):
        # Validate the resolved Windows target before recursive fixture cleanup.
        if Path(self.name).exists() and Path(self.name).resolve().parent != self.test_root:
            raise RuntimeError("Test cleanup target escaped the workspace test directory")
        super().cleanup()


class FakeMcp:
    def __init__(self, existing=(), compile_state=None, native_state=None, compile_requested=True):
        self.existing = set(existing)
        self.calls = []
        self.compile_state = compile_state
        self.compile_requested = compile_requested
        self.native_state = native_state or {
            "systemPath": SYSTEM + ".NS_Test_Version", "bCompilationPending": False,
            "bSystemValid": True, "bNativeReady": True, "bVMAttributesEqual": True, "error": ""}

    def tool(self, name, **args):
        self.calls.append((name, args))
        if name.endswith(".IsPIERunning"):
            return {"returnValue": False}
        if name.endswith(".exists"):
            return {"returnValue": args["path"] in self.existing}
        if name.endswith(".GetSystemCompileState"):
            return {"returnValue": self.compile_state}
        if name.endswith(".ForceCompile"):
            return {"returnValue": {**self.native_state, "bForceCompileRequested": self.compile_requested}}
        if name.endswith(".ReadSystemState"):
            return {"returnValue": self.native_state}
        if name.endswith(".save_assets"):
            return {"returnValue": True}
        raise AssertionError("Unexpected mutation/tool: " + name)


def node(name="Root", active=True, children=None, particle=False):
    result = {"name": name, "active": active, "children": children or [], "component_types": ["Transform"]}
    if particle:
        result["particle"] = {"renderer": {"m_Materials": [{"m_PathID": 1}], "m_Enabled": True,
            "m_Mesh": {"m_PathID": 0}, "m_RenderMode": 0, "m_VertexStreams": [], "m_UseCustomVertexStreams": False},
            "system": {"UVModule": {"enabled": False}}}
    return result


class BatchSafety(unittest.TestCase):
    def test_inspection_cli_cannot_enter_production_or_import_branches(self):
        conflicting = (["--apply"], ["--plan-imports"], ["--assets-map", "assets.json"],
                       ["--deps-path", "deps.json"], ["--revision", "Revision"],
                       ["--particle-equivalence", "particle.json"], ["--ue-equivalent", "ue.json"],
                       ["--endpoint", "localhost"], ["--approved-targets", "targets.json"])
        for options in conflicting:
            with self.subTest(options=options), patch.object(sys, "argv", ["zzz_fx_build.py", "source.fx.json",
                    "--inspect-source-programs", "--material-audits", "audits.json"] + options), \
                    patch.object(B, "preflight") as preflight, patch.object(B, "apply_batch") as apply, \
                    patch.object(B, "inspect_source_programs") as inspect, \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    B.main()
                self.assertEqual(raised.exception.code, 2)
                preflight.assert_not_called()
                apply.assert_not_called()
                inspect.assert_not_called()

    def test_inspection_cli_requires_its_exact_mapping_and_keeps_failures(self):
        for options in (["--inspect-source-programs"], ["--material-audits", "audits.json"]):
            with patch.object(sys, "argv", ["zzz_fx_build.py", "source.fx.json"] + options), \
                    contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as raised:
                    B.main()
                self.assertEqual(raised.exception.code, 2)
        with patch.object(sys, "argv", ["zzz_fx_build.py", "source.fx.json", "--inspect-source-programs",
                "--material-audits", "audits.json"]), patch.object(B, "read_json", return_value={"1": "candidate.json"}), \
                patch.object(B, "inspect_source_programs", side_effect=ValueError("source byte digest mismatch")) as inspect, \
                patch.object(B, "preflight") as preflight, contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(B.main(), 1)
            result = json.loads(output.getvalue())
            self.assertEqual(result["status"], "failed")
            self.assertEqual(result["error"], "source byte digest mismatch")
            self.assertEqual(result["runtime_selection"], "unverified")
            inspect.assert_called_once_with(["source.fx.json"], {"1": "candidate.json"})
            preflight.assert_not_called()

    @staticmethod
    def orientation_snapshot():
        config = dict(summary=dict(emitters=[]), emitters=[], stacks=[])
        for index, (name, (old, _new)) in enumerate(normal01_orientation_expressions().items()):
            config["summary"]["emitters"].append(dict(emitterName=name, bEnabled=True, simTarget="CPUSim"))
            mesh = "Eff_Cone_01" if index == 6 else "FXMD_DAO_001"
            config["emitters"].append(dict(topology=dict(emitterName=name, renderers=[dict(
                rendererIndex=0, rendererClass=dict(refPath="/Script/Niagara.NiagaraMeshRendererProperties"))]),
                renderers=[dict(propertyValues=dict(Meshes=[dict(mesh=dict(refPath=FX_MESH_ROOT + mesh + "." + mesh),
                    scale=dict(x=1,y=1,z=1), rotation=dict(pitch=0,yaw=0,roll=0), pivotOffset=dict(x=0,y=0,z=0),
                    pivotOffsetSpace="Mesh")], bIsEnabled=True, SourceMode="Particles", FacingMode="Default",
                    bLockedAxisEnable=False, MeshOrientationBinding=dict(paramMapVariable=dict(name="Particles.MeshOrientation"))))]))
            config["stacks"].append(dict(emitterName=name, topology=dict(scriptName="ParticleUpdateScript",
                modules=[dict(moduleName="OriginalAssignment_" + name, enabled=True, bIsSetParametersModule=True)]),
                modules=[dict(values=dict(moduleName="OriginalAssignment_" + name, inputs=[
                    dict(name="Particles.UChain3Q", value=NiagaraBuilder.hlsl("normalize(SourceHermite(System.Age))")),
                    dict(name="Particles.MeshOrientation", value=NiagaraBuilder.hlsl(old))]), dynamic=[])]))
        return config

    def test_orientation_plan_changes_only_seven_original_pins(self):
        before = self.orientation_snapshot()
        protected = copy.deepcopy(before)
        expected, plan = normal01_orientation_plan(before, NORMAL01_SYSTEM)
        differences = list(snapshot_differences(before, expected))
        self.assertEqual(before, protected)
        self.assertEqual(len(differences), 7)
        self.assertTrue(all(d["path"].endswith(".inputs[1].value.value.hlslExpression") for d in differences))
        self.assertEqual([p["ref"]["emitterName"] for p in plan], list(NORMAL01_EMITTERS))
        current, _ = normal01_orientation_plan(expected, NORMAL01_SYSTEM, require_current=True)
        self.assertEqual(current, expected)
        for stack in expected["stacks"]:
            self.assertEqual(stack["modules"][0]["values"]["inputs"][0]["value"],
                             NiagaraBuilder.hlsl("normalize(SourceHermite(System.Age))"))

    def test_orientation_unknown_last_pin_and_duplicate_reject_entire_plan(self):
        for change in ("unknown_hlsl", "different_struct", "duplicate", "disabled"):
            before = self.orientation_snapshot()
            last = before["stacks"][-1]
            value = last["modules"][0]["values"]["inputs"][-1]
            if change == "unknown_hlsl":
                value["value"]["value"]["hlslExpression"] += " + User.OtherRotation"
            elif change == "different_struct":
                value["value"]["struct"]["refPath"] = "/Script/NiagaraEditor.NiagaraExt_StackInputData_Linked"
            elif change == "duplicate":
                last["modules"][0]["values"]["inputs"].append(copy.deepcopy(value))
            else:
                last["topology"]["modules"][0]["enabled"] = False
            protected = copy.deepcopy(before)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                normal01_orientation_plan(before, NORMAL01_SYSTEM)
            self.assertEqual(before, protected)

    def test_orientation_rejects_wrong_system_and_renderer_compensation(self):
        for change in ("system", "mesh", "rotation", "scale", "binding", "facing"):
            before = self.orientation_snapshot()
            rd = before["emitters"][0]["renderers"][0]["propertyValues"]
            path = NORMAL01_SYSTEM
            if change == "system":
                path = SYSTEM
            elif change == "mesh":
                rd["Meshes"][0]["mesh"]["refPath"] = FX_MESH_ROOT + "Unknown.Unknown"
            elif change == "rotation":
                rd["Meshes"][0]["rotation"]["yaw"] = 180
            elif change == "scale":
                rd["Meshes"][0]["scale"]["x"] = -1
            elif change == "binding":
                rd["MeshOrientationBinding"]["paramMapVariable"]["name"] = "Particles.OtherQuat"
            else:
                rd["FacingMode"] = "Velocity"
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                normal01_orientation_plan(before, path)

    def test_orientation_other_author_changes_remain_blocking(self):
        before = self.orientation_snapshot()
        expected, _ = normal01_orientation_plan(before, NORMAL01_SYSTEM)
        after = copy.deepcopy(expected)
        after["stacks"][2]["modules"][0]["values"]["inputs"][0]["value"] = NiagaraBuilder.hlsl("0.0")
        authored, derived = partition_configuration_differences(expected, after, list(snapshot_differences(expected, after)))
        self.assertEqual(len(authored), 1)
        self.assertEqual(derived, [])

    def test_mesh_basis_rejects_import_rotation_and_nonfinite_bounds(self):
        for change in ("import_rotation", "nonfinite_bounds"):
            def call(name, **kw):
                if name.endswith("get_properties"):
                    if "assetImportData" in kw["properties"]:
                        return json.dumps(dict(assetImportData=dict(refPath="OriginalImport"),
                            positiveBoundsExtension=dict(x=0,y=0,z=0), negativeBoundsExtension=dict(x=0,y=0,z=0)))
                    values = dict(importTranslation=dict(x=0,y=0,z=0), importRotation=dict(pitch=0,yaw=0,roll=0),
                        importUniformScale=1, coordinateSystemPolicy="MatchUpForwardAxes", bConvertScene=True,
                        bForceFrontXAxis=False, bConvertSceneUnit=False, bUsingLUFCoordinateSysem=False,
                        bTransformVertexToAbsolute=True, bBakePivotInVertex=False)
                    if change == "import_rotation":
                        values["importRotation"]["roll"] = 90
                    return json.dumps(values)
                if name.endswith("get_bounds"):
                    return dict(isValid=True, min=dict(x=float("nan"),y=0,z=0), max=dict(x=0,y=0,z=0))
                self.fail("Unexpected tool call: " + name)
            with self.subTest(change=change), self.assertRaises(RuntimeError):
                verify_normal01_mesh_basis(call)

    @staticmethod
    def mesh_binding_snapshot():
        return {"emitters": [{"topology": {"renderers": [{"rendererIndex": 0,
                    "rendererClass": {"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"}}]},
                "renderers": [{"propertyValues": {"ColorBinding": {"RootName": "Color",
                    "ParamMapVariable": {"Name": "Particles.Color", "TypeDefHandle": {"RegisteredTypeIndex": 7}},
                    "BindingSourceMode": "ImplicitFromSource", "bBindingExistsOnSource": False}}}]}]}

    def test_only_proven_mesh_binding_cache_transition_is_derived(self):
        before = self.mesh_binding_snapshot()
        after = copy.deepcopy(before)
        after["emitters"][0]["renderers"][0]["propertyValues"]["ColorBinding"]["bBindingExistsOnSource"] = True
        authored, derived = partition_configuration_differences(before, after, list(snapshot_differences(before, after)))
        self.assertEqual(authored, [])
        self.assertEqual(len(derived), 1)
        self.assertIs(before["emitters"][0]["renderers"][0]["propertyValues"]["ColorBinding"]["bBindingExistsOnSource"], False)

    def test_binding_authorship_and_other_values_remain_blocking(self):
        for field, changed in (("RootName", "Wrong"), ("BindingSourceMode", "ExplicitUser"),
                               ("ParamMapVariable", {"Name": "Particles.Wrong", "TypeDefHandle": {"RegisteredTypeIndex": 8}})):
            before = self.mesh_binding_snapshot()
            after = copy.deepcopy(before)
            binding = after["emitters"][0]["renderers"][0]["propertyValues"]["ColorBinding"]
            binding["bBindingExistsOnSource"] = True
            binding[field] = changed
            with self.subTest(field=field):
                authored, _ = partition_configuration_differences(before, after, list(snapshot_differences(before, after)))
                self.assertTrue(authored)
                self.assertTrue(any(field in d["path"] for d in authored))

    def test_cache_name_on_other_type_or_path_and_binding_loss_are_not_ignored(self):
        for kind in ("renderer_class", "unknown_field", "module_input", "binding_loss"):
            before = self.mesh_binding_snapshot()
            if kind == "renderer_class":
                before["emitters"][0]["topology"]["renderers"][0]["rendererClass"]["refPath"] = "/Script/Niagara.NiagaraSpriteRendererProperties"
            if kind == "unknown_field":
                props = before["emitters"][0]["renderers"][0]["propertyValues"]
                props["UnverifiedBinding"] = props.pop("ColorBinding")
            if kind == "module_input":
                before = {"stacks": [{"bBindingExistsOnSource": False}]}
                after = {"stacks": [{"bBindingExistsOnSource": True}]}
            else:
                after = copy.deepcopy(before)
                props = after["emitters"][0]["renderers"][0]["propertyValues"]
                props[next(iter(props))]["bBindingExistsOnSource"] = True
            if kind == "binding_loss":
                before, after = after, before
            with self.subTest(kind=kind):
                authored, derived = partition_configuration_differences(before, after, list(snapshot_differences(before, after)))
                self.assertTrue(authored)
                self.assertEqual(derived, [])

    def test_snapshot_difference_preserves_authored_and_possible_cache_fields(self):
        before = {"renderers": [{"binding": {"rootName": "Age", "bBindingExistsOnSource": False}}]}
        after = {"renderers": [{"binding": {"rootName": "Wrong", "bBindingExistsOnSource": True}}]}
        changes = list(snapshot_differences(before, after))
        self.assertEqual([c["path"] for c in changes], ["$.renderers[0].binding.bBindingExistsOnSource",
                                                       "$.renderers[0].binding.rootName"])
        self.assertEqual([(c["before"], c["after"]) for c in changes], [(False, True), ("Age", "Wrong")])

    def test_snapshot_difference_distinguishes_missing_null_and_bool_number(self):
        changes = list(snapshot_differences({"removed": None, "flag": False}, {"flag": 0, "added": None}))
        self.assertEqual([c["path"] for c in changes], ["$.added", "$.flag", "$.removed"])
        self.assertFalse(changes[0]["beforeExists"])
        self.assertFalse(changes[2]["afterExists"])
        self.assertEqual(changes[1]["before"], False)

    def test_any_existing_target_prevents_all_mutations(self):
        existing = "/Game/Characters/Shared/FX/ZZZ/Materials/M_ManualEdit"
        mcp = FakeMcp([existing])
        with self.assertRaises(AssetConflict):
            AssetSession(mcp, [SYSTEM, existing], [SYSTEM, existing])
        self.assertTrue(all(name.endswith((".exists", ".IsPIERunning")) for name, _ in mcp.calls))

    def test_unapproved_target_does_not_even_query_editor(self):
        mcp = FakeMcp()
        with self.assertRaises(AssetConflict):
            AssetSession(mcp, [SYSTEM], [])
        self.assertEqual(mcp.calls, [])

    def test_target_created_after_preflight_is_protected(self):
        mcp = FakeMcp()
        session = AssetSession(mcp, [SYSTEM], [SYSTEM])
        mcp.existing.add(SYSTEM)
        with self.assertRaises(AssetConflict):
            session.begin_create(SYSTEM)
        self.assertEqual(session.created, set())

    def test_save_never_includes_existing_or_unowned_package(self):
        mcp = FakeMcp()
        session = AssetSession(mcp, [SYSTEM], [SYSTEM])
        with self.assertRaises(AssetConflict):
            session.save([SYSTEM])
        self.assertTrue(all(name.endswith((".exists", ".IsPIERunning")) for name, _ in mcp.calls))

    def test_incomplete_compile_is_not_saved(self):
        mcp = FakeMcp(compile_state={"bIsCompiling": False, "aggregateStatus": "Unknown", "scripts": []})
        session = AssetSession(mcp, [SYSTEM], [SYSTEM])
        session.created_asset(SYSTEM)
        builder = NiagaraBuilder(session)
        builder.sref = {"refPath": SYSTEM + ".NS_Test_Version"}
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            builder.finish_compile(SYSTEM, timeout=0)
        self.assertEqual(session.saved, set())

    def test_compile_error_is_not_saved_even_with_success_aggregate(self):
        state = {"bIsCompiling": False, "bIsStale": False, "bHasErrors": True, "aggregateStatus": "UpToDate", "scripts": [
            {"emitterName": "Smoke", "scriptName": "Update", "compileEvents": [
                {"severity": "Error", "message": "bad HLSL"}]}]}
        mcp = FakeMcp(compile_state=state)
        session = AssetSession(mcp, [SYSTEM], [SYSTEM])
        session.created_asset(SYSTEM)
        builder = NiagaraBuilder(session)
        builder.sref = {"refPath": SYSTEM + ".NS_Test_Version"}
        with self.assertRaisesRegex(RuntimeError, "bad HLSL"):
            builder.finish_compile(SYSTEM)
        self.assertEqual(session.saved, set())

    def test_up_to_date_with_mismatched_system_attributes_is_not_saved(self):
        native = {"systemPath": SYSTEM + ".NS_Test_Version", "bCompilationPending": False,
                  "bSystemValid": True, "bNativeReady": False, "bVMAttributesEqual": False,
                  "spawnAttributeCount": 79, "updateAttributeCount": 80, "error": ""}
        mcp = FakeMcp(compile_state=self.successful_compile(), native_state=native)
        session = AssetSession(mcp, [SYSTEM], [SYSTEM])
        session.created_asset(SYSTEM)
        builder = NiagaraBuilder(session)
        builder.sref = {"refPath": SYSTEM + ".NS_Test_Version"}
        with self.assertRaisesRegex(RuntimeError, "VM attributes mismatch"):
            builder.finish_compile(SYSTEM)
        self.assertEqual(session.saved, set())

    def test_native_readiness_is_required_after_successful_compile(self):
        mcp = FakeMcp(compile_state=self.successful_compile())
        mcp.native_state["bNativeReady"] = False
        session = AssetSession(mcp, [SYSTEM], [SYSTEM])
        session.created_asset(SYSTEM)
        builder = NiagaraBuilder(session)
        builder.sref = {"refPath": SYSTEM + ".NS_Test_Version"}
        with self.assertRaisesRegex(RuntimeError, "incomplete"):
            builder.finish_compile(SYSTEM, timeout=0)
        self.assertEqual(session.saved, set())

    def test_unrequested_full_compile_is_not_saved(self):
        mcp = FakeMcp(compile_state=self.successful_compile(), compile_requested=False)
        session = AssetSession(mcp, [SYSTEM], [SYSTEM])
        session.created_asset(SYSTEM)
        builder = NiagaraBuilder(session)
        builder.sref = {"refPath": SYSTEM + ".NS_Test_Version"}
        with self.assertRaisesRegex(RuntimeError, "not requested"):
            builder.finish_compile(SYSTEM)
        self.assertEqual(session.saved, set())

    def test_full_compile_and_native_ready_save_only_owned_system(self):
        mcp = FakeMcp(compile_state=self.successful_compile())
        session = AssetSession(mcp, [SYSTEM], [SYSTEM])
        session.created_asset(SYSTEM)
        builder = NiagaraBuilder(session)
        builder.sref = {"refPath": SYSTEM + ".NS_Test_Version"}
        state = builder.finish_compile(SYSTEM)
        self.assertTrue(state["native"]["bNativeReady"])
        self.assertEqual(session.saved, {SYSTEM})
        mutations = [name.rsplit(".", 1)[-1] for name, _ in mcp.calls
                     if name.endswith((".ForceCompile", ".save_assets"))]
        self.assertEqual(mutations, ["ForceCompile", "save_assets"])

    @staticmethod
    def successful_compile():
        return {"bIsCompiling": False, "bIsStale": False, "bHasErrors": False,
                "aggregateStatus": "UpToDate", "scripts": []}

    def test_disabled_subimage_binding_matches_actual_native_name_none_readback(self):
        actual = {"subImageIndexBinding": {
            "rootName": "None", "paramMapVariable": {"name": "None", "typeDefHandle": {"registeredTypeIndex": 99}},
            "dataSetName": "None", "boundVariable": {"varData": [], "name": "None", "typeDefHandle": {"registeredTypeIndex": 105}},
            "cachedDisplayName": "None", "bindingSourceMode": "ImplicitFromSource",
            "bBindingExistsOnSource": False, "bIsCachedParticleValue": True}}
        expected = {"SubImageIndexBinding": NiagaraBuilder.attribute_binding(None)}
        NiagaraBuilder.verify_properties(expected, actual, "World_root_Particle_System__14_")

    def test_name_none_cannot_hide_wrong_live_binding_or_normalize_other_strings(self):
        expected = {"SubImageIndexBinding": NiagaraBuilder.attribute_binding(None)}
        for field in ("RootName", "ParamMapVariable", "DataSetName", "CachedDisplayName"):
            actual = copy.deepcopy(expected)
            actual["SubImageIndexBinding"][field] = {"Name": "Particles.SubImageIndex"} if field == "ParamMapVariable" else "SubImageIndex"
            with self.subTest(field=field), self.assertRaisesRegex(RuntimeError, field):
                NiagaraBuilder.verify_properties(expected, actual, "Smoke")
        active = {"MaterialRandomBinding": NiagaraBuilder.attribute_binding("Particles.SubImageIndex")}
        disabled = {"MaterialRandomBinding": NiagaraBuilder.attribute_binding(None)}
        with self.assertRaisesRegex(RuntimeError, "RootName"):
            NiagaraBuilder.verify_properties(active, disabled, "Smoke")
        with self.assertRaisesRegex(RuntimeError, "Label"):
            NiagaraBuilder.verify_properties({"Label": ""}, {"Label": "None"}, "Smoke")

    def test_distance_emission_uses_native_spacing_and_inline_condition_names(self):
        from test_zzz_fx_particle_renderer import RecordingBuilder

        class NativeDistanceInputs(RecordingBuilder):
            def __init__(self):
                super().__init__()
                self.distance_module = None
                self.distance_inputs = {}

            def ns(self, name, **args):
                if name == "SetStackInputData" and args["stackInputRef"]["moduleName"] == self.distance_module:
                    pin = args["stackInputRef"]["inputNameStack"][0]
                    if pin not in ("Spawn Spacing", "Velocity Vector", "Module.Use Movement Tolerance", "Module.Use Max Movement Threshold"):
                        raise RuntimeError("Input not found in native SpawnPerUnit: " + pin)
                    self.distance_inputs[pin] = args["inputData"]
                result = super().ns(name, **args)
                if name == "AddModule" and args["moduleAsset"]["refPath"].endswith("/SpawnPerUnit.SpawnPerUnit"):
                    self.distance_module = result["moduleName"]
                return result

            def build_renderer(self, name, rd):
                pass  # This fixture checks the native distance module, not renderer construction.

        spec = {"name": "Smoke", "renderer": {"kind": "sprite"}, "local_space": False,
                "loop": False, "duration": 1, "delay": 0, "bursts": [], "rate": 0, "distance_rate": 1,
                "spawn": [], "update": []}
        builder = NativeDistanceInputs()
        builder.build_emitter(spec)
        values = builder.distance_inputs
        self.assertEqual(values["Spawn Spacing"], NiagaraBuilder.num("Float", 100.0))
        self.assertEqual(values["Velocity Vector"], NiagaraBuilder.hlsl("Transient.UEFX_EmissionVelocity"))
        self.assertEqual(values["Module.Use Movement Tolerance"], NiagaraBuilder.num("Bool", 0))
        self.assertEqual(values["Module.Use Max Movement Threshold"], NiagaraBuilder.num("Bool", 0))

    def test_partial_prefab_never_reaches_asset_builder(self):
        root = node(children=[node("Supported", particle=True), node("Unsupported", particle=True)])
        plan = {"material": "Mat", "master": "M_Test", "params": {}, "textures": {}}
        def emitter(item, path, *args):
            if item["name"] == "Unsupported":
                raise B.FN.SpecError("source distortion is unsupported")
            return {"name": item["name"], "path": item["name"], "renderer": {"kind": "mesh"}}
        mcp = FakeMcp()
        with WorkspaceTemporaryDirectory() as directory:
            fx = Path(directory) / "Test.fx.json"
            fx.write_text(json.dumps({"name": "Test", "root": root}), encoding="utf-8")
            fx.with_name("Test.deps.json").write_text("{}", encoding="utf-8")
            with patch.object(B, "material_plan", return_value=plan), patch.object(B.FN, "emitter_spec", side_effect=emitter):
                with self.assertRaises(B.PreflightError) as error:
                    B.build(fx, mcp, [SYSTEM], assets={})
                preview = B.preflight(fx, assets={}, preview_node="Supported")
                self.assertEqual(preview["renderers"], ["Supported"])
                self.assertEqual(preview["scope"], "source_subtree_preview")
                self.assertEqual(preview["source_prefab_restore"], "incomplete")
                self.assertIn("NS_PREVIEW", preview["system"])
            self.assertEqual(error.exception.report["renderers"], ["Supported"])
            self.assertIn("distortion", error.exception.report["blocked"][0]["reason"])
        self.assertEqual(mcp.calls, [])

    def test_sprite_viewport_material_mismatch_fails_before_any_editor_query(self):
        mcp = FakeMcp()
        plan = {"render_preflight": "complete", "blocked": [], "targets": [SYSTEM], "materials": {},
                "specs": [{"name": "Smoke", "renderer": {"kind": "sprite", "material": "/Test/Smoke",
                                                          "viewport_adapter_signature": "expected"}}]}
        with self.assertRaisesRegex(ValueError, "viewport adapter contract mismatch"):
            B.apply_batch([plan], mcp, [SYSTEM])
        self.assertEqual(mcp.calls, [])

    def test_missing_material_depth_state_fails_before_imports_or_editor_queries(self):
        mcp = FakeMcp()
        plan = {"render_preflight": "complete", "blocked": [], "targets": [SYSTEM],
                "materials": {"/Test/Mat": {"output_contract": "color"}},
                "specs": [{"name": "Mesh", "renderer": {"kind": "mesh"}}]}
        with self.assertRaisesRegex(ValueError, "resolved source depth-test"):
            B.apply_batch([plan], mcp, [SYSTEM], imports={"targets": ["/Test/Texture"]})
        self.assertEqual(mcp.calls, [])

    def test_inactive_parent_disables_visible_child(self):
        root = node(children=[node("Hidden", active=False, children=[node("Smoke", particle=True)])])
        rows = list(B.walk(root))
        self.assertFalse(rows[-1][2])

    def test_invalid_wrap_fails_before_import(self):
        with self.assertRaisesRegex(ValueError, "wrap"):
            texture_properties({"m_TextureSettings": {"m_WrapMode": 3}})

    def test_legacy_mipmap_false_does_not_discard_actual_source_mips(self):
        settings = {"m_TextureSettings": {"m_WrapMode": 0, "m_FilterMode": 1, "m_MipBias": 0.0},
                    "m_ColorSpace": 1, "m_MipMap": False, "m_MipCount": 9}
        self.assertEqual(texture_properties(settings)["MipGenSettings"], "TMGS_FromTextureGroup")
        settings["m_MipCount"] = 1
        self.assertEqual(texture_properties(settings)["MipGenSettings"], "TMGS_NoMipmaps")

    def test_independent_source_wrap_axes_are_preserved(self):
        settings = {"m_TextureSettings": {"m_WrapMode": 0, "m_WrapU": 1, "m_WrapV": 2,
                                         "m_FilterMode": 1}, "m_ColorSpace": 1, "m_MipCount": 1}
        result = texture_properties(settings)
        self.assertEqual((result["AddressX"], result["AddressY"]), ("TA_Clamp", "TA_Mirror"))

    def test_incomplete_independent_wrap_axes_do_not_fall_back_to_common_mode(self):
        with self.assertRaisesRegex(ValueError, "Both source"):
            texture_properties({"m_TextureSettings": {"m_WrapMode": 0, "m_WrapU": 1}})

    def test_version_two_uses_its_component_inventory_and_dependency_file(self):
        root = node(children=[node("Smoke", particle=True)])
        for item, _, _ in B.walk(root):
            item["components"] = [{"type": "Transform"}]
            item["componentListProof"] = "all original pointers retained"
        plan = {"material": "Mat", "master": "M_Test", "params": {}, "textures": {}}
        with WorkspaceTemporaryDirectory() as directory:
            fx = Path(directory) / "Test.fx.json"
            fx.write_text(json.dumps({"schemaVersion": 2, "name": "Test", "block": "NeverReadLegacy",
                                      "root": root}), encoding="utf-8")
            fx.with_name("Test.deps.v2.json").write_text("{}", encoding="utf-8")
            fx.with_name("Test.deps.json").write_text("invalid legacy source", encoding="utf-8")
            with patch.object(B, "material_plan", return_value=plan), patch.object(
                    B.FN, "emitter_spec", return_value={"name": "Smoke", "path": "Smoke", "renderer": {"kind": "mesh"}}):
                result = B.preflight(fx, assets={})
            self.assertEqual(result["renderers"], ["Smoke"])

    def test_missing_version_two_dependencies_never_use_legacy_file(self):
        with WorkspaceTemporaryDirectory() as directory:
            fx = Path(directory) / "Test.fx.json"
            fx.write_text(json.dumps({"schemaVersion": 2, "name": "Test", "root": node()}), encoding="utf-8")
            fx.with_name("Test.deps.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(FileNotFoundError):
                B.preflight(fx, assets={})

    def test_version_two_missing_inventory_does_not_read_legacy_index(self):
        with WorkspaceTemporaryDirectory() as directory:
            fx = Path(directory) / "Test.fx.json"
            fx.write_text(json.dumps({"schemaVersion": 2, "name": "Test", "block": "NeverReadLegacy",
                                      "root": node()}), encoding="utf-8")
            fx.with_name("Test.deps.v2.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(B.PreflightError) as error:
                B.preflight(fx, assets={})
            self.assertIn("explicit source component", error.exception.report["blocked"][0]["reason"])

    def test_native_shader_does_not_use_unrelated_legacy_keyword_cache(self):
        with WorkspaceTemporaryDirectory() as directory:
            mat = Path(directory) / "Material.json"
            mat.write_text(json.dumps({"m_Shader": {"m_PathID": 2}}), encoding="utf-8")
            deps = {"1": {"files": [str(mat)]}, "2": {"type": "Shader", "name": "Shader",
                     "nativeJson": "exact native source", "cab": "CAB_source"}}
            with patch.object(B.FM, "plan", side_effect=AssertionError("Legacy variant cache was used")):
                with self.assertRaisesRegex(B.FM.PlanError, "exact subprogram"):
                    B.material_plan(deps, "1", {}, {})

    def test_cross_file_dependency_conflict_is_detected_before_import(self):
        with WorkspaceTemporaryDirectory() as directory:
            directory = Path(directory)
            sources = []
            for index in range(2):
                source = directory / (str(index) + ".fbx")
                source.write_text("mesh version " + str(index), encoding="utf-8")
                deps = directory / (str(index) + ".deps.json")
                deps.write_text(json.dumps({"1": {"type": "Mesh", "name": "Mesh", "files": [str(source)]}}), encoding="utf-8")
                sources.append(deps)
            with self.assertRaisesRegex(ValueError, "cross-file"):
                plan_imports(sources)


if __name__ == "__main__":
    unittest.main()
