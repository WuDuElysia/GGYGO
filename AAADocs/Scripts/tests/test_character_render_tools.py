"""Offline failure-path tests; no Unreal process or project asset writes.

夹具复制项目里的三份 Pyrios 材质 JSON 与全局参数文件到临时目录再修改，源文件只读。
"""
import importlib.util
import json
from pathlib import Path
import shutil
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
PROJECT = SCRIPTS.parents[1]
sys.path.insert(0, str(SCRIPTS))
from pyrios_material_plan import BuildJournal, SUFFIXES, load_plan, unity_gamma_to_linear

SOURCE_JSON = PROJECT / "Content/Characters/Player/Pyrios/Materials"
SOURCE_GLOBALS = PROJECT / "AAADocs/Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json"


def module(name, unreal):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    result = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"unreal": unreal}):
        spec.loader.exec_module(result)
    return result


class Texture:
    def get_editor_property(self, name):
        return True
class Material: pass
class Instance: pass
class Mesh:
    def get_editor_property(self, name):
        return [types.SimpleNamespace(get_editor_property=lambda _, s=s: "MAT_Pyrois_" + s) for s in SUFFIXES]


@unittest.skipUnless(SOURCE_JSON.is_dir() and SOURCE_GLOBALS.is_file(), "Pyrios source JSON not present")
class RenderToolsTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        for suffix in SUFFIXES:
            shutil.copy(SOURCE_JSON / ("MAT_Pyrois_" + suffix + ".json"), self.root)
        shutil.copytree(SOURCE_JSON / "TextureSettings", self.root / "TextureSettings")
        self.globals = self.root / "globals.json"
        shutil.copy(SOURCE_GLOBALS, self.globals)

    def edit(self, path, fn):
        data = json.loads(path.read_text(encoding="utf-8"))
        fn(data)
        path.write_text(json.dumps(data), encoding="utf-8")

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
            CustomMaterialOutputType=types.SimpleNamespace(CMOT_FLOAT3=0),
            EditorLoadingAndSavingUtils=types.SimpleNamespace(get_dirty_content_packages=lambda:
                [types.SimpleNamespace(get_path_name=lambda: "/Game/Characters/Player/Pyrios/Materials/Generated/M_Pyrois_Toon")] if dirty else []))
        builder = module("build_pyrios_materials", fake)
        builder.JSON_DIR, builder.GLOBALS_PATH = self.root, self.globals
        return builder, writes

    def test_complete_source_plan(self):
        plan = load_plan(self.root, self.globals)
        self.assertEqual(set(plan["materials"]), set(SUFFIXES))
        inputs = {i["name"] for i in plan["inputs"] if i["kind"] == "material"}
        for suffix in SUFFIXES:
            self.assertTrue(inputs.issubset(plan["params"][suffix]))
        self.assertIn("Eff_Matcap_125", plan["texture_names"])

    def test_color_property_is_linearized_vector_is_not(self):
        def mutate(d):
            d["m_SavedProperties"]["m_Colors"]["_ShallowColor"] = dict(r=0.5, g=0.5, b=0.5, a=0.5)
            d["m_SavedProperties"]["m_Colors"]["_RefractParam"] = dict(r=0.5, g=0.5, b=0.5, a=0.5)
        self.edit(self.root / "MAT_Pyrois_Body_1.json", mutate)
        params = load_plan(self.root, self.globals)["params"]["Body_1"]
        self.assertAlmostEqual(params["_ShallowColor"][0], unity_gamma_to_linear(0.5))
        self.assertEqual(params["_ShallowColor"][3], 0.5)
        self.assertEqual(params["MC_Refract1"], (0.5, 0.5, 0.5, 0.5))

    def test_matcap_slice_only_for_assigned_textures(self):
        plan = load_plan(self.root, self.globals)
        for suffix in SUFFIXES:
            for g in range(1, 6):
                has_tex = plan["textures"][suffix]["MatCapTex%d" % g] is not None
                self.assertEqual(plan["params"][suffix]["MC_A%d" % g][0], float(g - 1) if has_tex else 100.0)

    def test_texture_colorspace_from_settings(self):
        plan = load_plan(self.root, self.globals)
        self.assertTrue(plan["texture_srgb"]["Pyrois_Body_Map1_D"])
        self.assertFalse(plan["texture_srgb"]["Pyrois_Body_Map1_N"])
        self.assertTrue(plan["slot_srgb"]["SpecialWeaponEmissionMaskTex"])

    def test_missing_texture_settings_rejected(self):
        (self.root / "TextureSettings" / "Eff_Mask_032.json").unlink()
        with self.assertRaisesRegex(ValueError, "Eff_Mask_032"):
            load_plan(self.root, self.globals)

    def test_hdr_color_scales_gamma_base(self):
        from pyrios_material_plan import unity_color_to_linear
        r, g, b = unity_color_to_linear((2.509804, 6.5254903, 47.937256))
        self.assertAlmostEqual(b, 47.937256)
        self.assertLess(g, 1.0)

    def test_unsupported_feature_rejected(self):
        self.edit(self.root / "MAT_Pyrois_Body_2.json",
                  lambda d: d["m_SavedProperties"]["m_Floats"].__setitem__("_DoubleSided", 1.0))
        with self.assertRaisesRegex(ValueError, "_DoubleSided"):
            load_plan(self.root, self.globals)

    def test_last_material_invalid_before_writes(self):
        self.edit(self.root / "MAT_Pyrois_Weapon01.json",
                  lambda d: d["m_SavedProperties"]["m_Colors"]["_SpecularColor5"].pop("a"))
        builder, writes = self.builder()
        with self.assertRaises(ValueError): builder.preflight()
        self.assertEqual(writes, [])

    def test_unknown_global_rejected(self):
        self.edit(self.globals, lambda d: d.__setitem__("TypoGain", [1, 0, 0, 0]))
        with self.assertRaisesRegex(ValueError, "TypoGain"): load_plan(self.root, self.globals)

    def test_missing_global_rejected(self):
        self.edit(self.globals, lambda d: d.pop("_PostShadowTint"))
        with self.assertRaisesRegex(ValueError, "_PostShadowTint"): load_plan(self.root, self.globals)

    def test_nonfinite_global_rejected(self):
        self.globals.write_text(self.globals.read_text(encoding="utf-8").replace(
            '"_CharacterAmbient": [0, 0, 0, 0]', '"_CharacterAmbient": [NaN, 0, 0, 0]'), encoding="utf-8")
        with self.assertRaises(ValueError): load_plan(self.root, self.globals)

    def test_missing_texture_before_writes(self):
        builder, writes = self.builder(missing="Pyrois_Weapon_A")
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
                recompile_material=lambda m: compiled.append(m),
                get_statistics=lambda m: types.SimpleNamespace(num_pixel_shader_instructions=1)),
            log=lambda *a: None)
        verifier = module("verify_pyrios_renderer", fake)
        # 两个 master 检查完后在第一个缺失的 MI 处停下；只读模式不重编译。
        with self.assertRaises(AssertionError): verifier.verify()
        self.assertEqual(compiled, [])
        with self.assertRaises(AssertionError): verifier.verify(recompile=True)
        self.assertEqual(len(compiled), 2)


if __name__ == "__main__":
    unittest.main()
