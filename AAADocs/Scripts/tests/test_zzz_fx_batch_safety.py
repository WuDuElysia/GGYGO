"""Regression checks for partial builds, existing assets and compile failures."""
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
from zzz_fx_niagara_ue import NiagaraBuilder

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
    def __init__(self, existing=(), compile_state=None):
        self.existing = set(existing)
        self.calls = []
        self.compile_state = compile_state

    def tool(self, name, **args):
        self.calls.append((name, args))
        if name.endswith(".IsPIERunning"):
            return {"returnValue": False}
        if name.endswith(".exists"):
            return {"returnValue": args["path"] in self.existing}
        if name.endswith(".GetSystemCompileState"):
            return {"returnValue": self.compile_state}
        if name.endswith(".save_assets"):
            return {"returnValue": True}
        raise AssertionError("Unexpected mutation/tool: " + name)


def node(name="Root", active=True, children=None, particle=False):
    result = {"name": name, "active": active, "children": children or [], "component_types": ["Transform"]}
    if particle:
        result["particle"] = {"renderer": {"m_Materials": [{"m_PathID": 1}], "m_Enabled": True,
            "m_Mesh": {"m_PathID": 0}, "m_RenderMode": 0, "m_VertexStreams": [], "m_UseCustomVertexStreams": False}}
    return result


class BatchSafety(unittest.TestCase):
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
        state = {"bIsCompiling": False, "aggregateStatus": "UpToDate", "scripts": [
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

    def test_partial_prefab_never_reaches_asset_builder(self):
        root = node(children=[node("Supported", particle=True), node("Unsupported", particle=True)])
        plan = {"material": "Mat", "master": "M_Test", "params": {}, "textures": {}}
        def emitter(item, path, *args):
            if item["name"] == "Unsupported":
                raise B.FN.SpecError("source distortion is unsupported")
            return {"name": item["name"], "path": item["name"]}
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
                    B.FN, "emitter_spec", return_value={"name": "Smoke", "path": "Smoke"}):
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
