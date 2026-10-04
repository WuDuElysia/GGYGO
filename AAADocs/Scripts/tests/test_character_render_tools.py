"""Offline failure-path tests; no Unreal process or project asset writes."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
from pyrios_material_plan import BuildJournal, SUFFIXES, load_plan


def module(name, unreal):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"unreal": unreal}):
        spec.loader.exec_module(result)
    return result


class Texture: pass
class Material: pass
class Instance: pass
class Mesh:
    def get_editor_property(self, name):
        return [types.SimpleNamespace(get_editor_property=lambda _, s=s: "MAT_Pyrois_" + s) for s in SUFFIXES]


class RenderToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.calibration = self.root / "calibration.json"
        self.calibration.write_text('{"shared":{"SceneLightStrength":0.65}}')
        for suffix in SUFFIXES:
            colors = {name + ("" if i == 1 else str(i)): dict(r=1, g=1, b=1, a=1)
                      for name in ("_ShallowColor", "_ShadowColor", "_SpecularColor", "_RimGlowLightColor")
                      for i in range(1, 6)}
            colors.update({k: dict(r=1, g=1, b=1, a=1) for k in ("_EmissionColor", "_RimGlowShadowColor")})
            data = {"m_Name": "MAT_Pyrois_" + suffix, "m_SavedProperties": {
                "m_Colors": colors, "m_Floats": {}, "m_TexEnvs": {
                    k: {"m_Texture": {"Name": suffix + "_" + k, "IsNull": False}}
                    for k in ("_MainTex", "_LightTex", "_OtherDataTex", "_OtherDataTex2")}}}
            (self.root / (data["m_Name"] + ".json")).write_text(json.dumps(data))

    def builder(self, missing=None, dirty=False, wrong_type=False):
        writes = []
        def load(path):
            if missing and path.endswith(missing): return None
            if path.endswith("Avatar_Male_Size03_Pyrois_Model"): return Mesh()
            if "/Generated/" in path: return Texture() if wrong_type else None
            return Texture()
        eal = types.SimpleNamespace(load_asset=load, does_asset_exist=lambda p: wrong_type,
            make_directory=lambda *a: writes.append("mkdir"), save_loaded_asset=lambda *a: writes.append("save"))
        fake = types.SimpleNamespace(EditorAssetLibrary=eal, MaterialEditingLibrary=types.SimpleNamespace(),
            Texture2D=Texture, Material=Material, MaterialInstanceConstant=Instance, SkeletalMesh=Mesh,
            MaterialSamplerType=types.SimpleNamespace(SAMPLERTYPE_COLOR=0),
            EditorLoadingAndSavingUtils=types.SimpleNamespace(get_dirty_content_packages=lambda:
                [types.SimpleNamespace(get_path_name=lambda: "/Game/Characters/Player/Pyrios/Materials/Generated/M_Pyrois_Toon")] if dirty else []))
        builder = module("build_pyrios_materials", fake)
        builder.JSON_DIR, builder.CALIBRATION_PATH = self.root, self.calibration
        return builder, writes

    def test_complete_source_plan(self):
        plan = load_plan(self.root, self.calibration)
        self.assertEqual(set(plan["materials"]), set(SUFFIXES))
        self.assertEqual(len(plan["textures"]), 13)

    def test_last_material_invalid_before_writes(self):
        p = self.root / "MAT_Pyrois_Weapon01.json"
        data = json.loads(p.read_text())
        del data["m_SavedProperties"]["m_Colors"]["_SpecularColor5"]["a"]
        p.write_text(json.dumps(data))
        builder, writes = self.builder()
        with self.assertRaises(ValueError): builder.preflight()
        self.assertEqual(writes, [])

    def test_unknown_calibration_rejected(self):
        self.calibration.write_text('{"shared":{"TypoGain":1}}')
        with self.assertRaises(ValueError): load_plan(self.root, self.calibration)

    def test_nonfinite_calibration_rejected(self):
        self.calibration.write_text('{"shared":{"SceneLightStrength":NaN}}')
        with self.assertRaises(ValueError): load_plan(self.root, self.calibration)

    def test_missing_texture_before_writes(self):
        builder, writes = self.builder(missing="Weapon01__OtherDataTex2")
        with self.assertRaisesRegex(RuntimeError, "texture type"): builder.preflight()
        self.assertEqual(writes, [])

    def test_dirty_target_before_writes(self):
        builder, writes = self.builder(dirty=True)
        with self.assertRaisesRegex(RuntimeError, "dirty target"): builder.preflight()
        self.assertEqual(writes, [])

    def test_wrong_existing_output_type_before_writes(self):
        builder, writes = self.builder(wrong_type=True)
        with self.assertRaisesRegex(RuntimeError, "output asset type"): builder.preflight()
        self.assertEqual(writes, [])

    def test_save_failure_is_not_reported_complete(self):
        journal = BuildJournal()
        journal.touch("first")
        journal.save("first", lambda: True)
        journal.touch("second")
        with self.assertRaises(RuntimeError): journal.save("second", lambda: False)
        report = journal.report("failed", "disk error")
        self.assertEqual(report["saved"], ["first"])
        self.assertEqual(report["unsaved_or_failed"], ["second"])

    def test_verifier_compile_is_opt_in(self):
        compiled = []
        fake = types.SimpleNamespace(Material=Material, MaterialUsage=types.SimpleNamespace(MATUSAGE_SKELETAL_MESH=0),
            EditorAssetLibrary=types.SimpleNamespace(does_asset_exist=lambda p: True,
                load_asset=lambda p: Material() if "/Generated/" in p and p.split("/")[-1].startswith("M_") else None),
            MaterialEditingLibrary=types.SimpleNamespace(has_material_usage=lambda *a: True,
                recompile_material=lambda m: compiled.append(m) or []), log=lambda *a: None)
        verifier = module("verify_pyrios_renderer", fake)
        # Stop at the first missing MI after checking both masters; no asset mutation
        # should be required to reach the read-only asset check.
        with self.assertRaises(AssertionError): verifier.verify()
        self.assertEqual(compiled, [])
        with self.assertRaises(AssertionError): verifier.verify(recompile=True)
        self.assertEqual(len(compiled), 2)


if __name__ == "__main__":
    unittest.main()
