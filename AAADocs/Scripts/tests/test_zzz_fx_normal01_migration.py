"""Normal01 迁移严格限定批准指针，其它配置变化阻止保存。"""
import copy
import hashlib
import json
from pathlib import Path
import tempfile
from enum import Enum
from types import SimpleNamespace
import unittest

import zzz_fx_niagara_ue as UE


def configuration():
    config = {"summary": {"emitters": []}, "system": {"unique_setting": 17}, "emitters": [], "stacks": []}
    for index, name in enumerate(UE.NORMAL01_EMITTERS):
        config["summary"]["emitters"].append({"emitterName": name, "bEnabled": True, "simTarget": "CPUSim"})
        mesh = "Eff_Cone_01" if index == 6 else "FXMD_DAO_001"
        rd = {"Meshes": [{"mesh": {"refPath": UE.FX_MESH_ROOT + mesh + "." + mesh},
               "scale": dict(x=1, y=1, z=1), "rotation": dict(pitch=0, yaw=0, roll=0),
               "pivotOffset": dict(x=0, y=0, z=0), "pivotOffsetSpace": "Mesh", "private_sibling": "preserve"}],
              "OverrideMaterials": [{"explicitMat": {"refPath": "/Game/Old/MI_" + name + ".MI_" + name},
                                     "private_sibling": "preserve"}], "bOverrideMaterials": True,
              "bIsEnabled": True, "SourceMode": "Particles", "FacingMode": "Default", "bLockedAxisEnable": False,
              "MeshOrientationBinding": {"paramMapVariable": {"name": "Particles.MeshOrientation"},
                                         "bBindingExistsOnSource": False}}
        config["emitters"].append({"topology": {"emitterName": name, "renderers": [{"rendererIndex": 0,
            "rendererClass": {"refPath": "/Script/Niagara.NiagaraMeshRendererProperties"}}]},
            "data": {}, "renderers": [{"propertyValues": rd}]})
        mt = {"moduleName": "Orientation", "enabled": True, "bIsSetParametersModule": True}
        config["stacks"].append({"emitterName": name, "topology": {"scriptName": "ParticleUpdateScript", "modules": [mt]},
            "modules": [{"values": {"moduleName": "Orientation", "inputs": [{"name": "Particles.MeshOrientation",
                "value": UE.NiagaraBuilder.hlsl(UE.normal01_orientation_expressions()[name][1])}]}}]})
    return config


class ExactMigration(unittest.TestCase):
    def refs(self):
        return {"root_Trail_rot_" + n: "/Game/Characters/Shared/FX/ZZZ/MaterialInstances/MI_New_" + n
                for n in UE.NORMAL01_MATERIAL_LAYERS}

    def test_four_material_pointers_only_and_struct_siblings_preserved(self):
        before = configuration()
        original = copy.deepcopy(before)
        after, edits = UE.normal01_reference_plan(before, self.refs())
        differences = list(UE.snapshot_differences(before, after))
        self.assertEqual(before, original)
        self.assertEqual(len(differences), 4)
        self.assertTrue(all(d["path"].endswith(".OverrideMaterials[0].explicitMat.refPath") for d in differences))
        self.assertTrue(all(set(e["properties"]) == {"OverrideMaterials"} for e in edits))
        self.assertTrue(all(e["properties"]["OverrideMaterials"][0]["private_sibling"] == "preserve" for e in edits))

    def test_exact_seven_mesh_and_four_material_changes(self):
        before = configuration()
        meshes = {n: UE.FX_MESH_ROOT + ("Cone_New" if i == 6 else "DAO_New") for i, n in enumerate(UE.NORMAL01_EMITTERS)}
        after, edits = UE.normal01_reference_plan(before, self.refs(), meshes)
        differences = list(UE.snapshot_differences(before, after))
        self.assertEqual(len(differences), 11)
        self.assertEqual(len(edits), 7)
        self.assertEqual(sum(d["path"].endswith(".Meshes[0].mesh.refPath") for d in differences), 7)

    def test_unapproved_configuration_changes_rejected(self):
        before = configuration()
        expected, _ = UE.normal01_reference_plan(before, self.refs())
        changed = copy.deepcopy(expected)
        changed["emitters"][0]["renderers"][0]["propertyValues"]["Meshes"][0]["pivotOffset"]["x"] = 1
        with self.assertRaisesRegex(RuntimeError, "批准指针以外"):
            UE.verify_normal01_configuration(expected, changed)
        changed = copy.deepcopy(expected)
        changed["stacks"][0]["modules"][0]["values"]["inputs"][0]["value"] = None
        with self.assertRaisesRegex(RuntimeError, "批准指针以外"):
            UE.verify_normal01_configuration(expected, changed)

    def test_only_native_binding_false_to_true_is_derived(self):
        expected = configuration()
        actual = copy.deepcopy(expected)
        actual["emitters"][0]["renderers"][0]["propertyValues"]["MeshOrientationBinding"]["bBindingExistsOnSource"] = True
        self.assertEqual(len(UE.verify_normal01_configuration(expected, actual)), 1)
        with self.assertRaises(RuntimeError):
            UE.verify_normal01_configuration(actual, expected)

    def test_partial_or_outside_reference_set_rejected(self):
        refs = self.refs()
        refs.pop("root_Trail_rot_bloom")
        with self.assertRaises(ValueError):
            UE.normal01_reference_plan(configuration(), refs)
        refs = self.refs()
        refs["root_Trail_rot_bloom"] = "/Game/Character/Body"
        with self.assertRaises(ValueError):
            UE.normal01_reference_plan(configuration(), refs)


class NativeBlend(Enum):
    BLEND_ALPHA_COMPOSITE = 6
    BLEND_TRANSLUCENT = 2
    BLEND_ADDITIVE = 3
    BLEND_MODULATE = 4

    def __str__(self):
        # 对应 UE5.8 PyWrapperEnum.cpp 的原生 tp_str 格式。
        return "<BlendMode." + self.name + ": " + str(self.value) + ">"


class NativeShading(Enum):
    MSM_UNLIT = 0
    MSM_DEFAULT_LIT = 1


class NativeMaterialEnumReadback(unittest.TestCase):
    def native(self, blend, shading):
        class Material:
            def get_editor_property(self, name):
                return {"two_sided": True, "disable_depth_test": False,
                        "used_with_niagara_mesh_particles": True, "used_with_niagara_sprites": False,
                        "automatically_set_usage_in_editor": False, "blend_mode": blend,
                        "shading_model": shading}[name]

            def get_path_name(self):
                return "/Game/Test/M_Normal01.M_Normal01"

        def graph_probe(*args):
            raise RuntimeError("已通过原生枚举门槛，进入 Custom 图核验")

        return SimpleNamespace(Material=Material, BlendMode=NativeBlend, MaterialShadingModel=NativeShading,
            EditorAssetLibrary=SimpleNamespace(load_asset=lambda path: Material()),
            MaterialEditingLibrary=SimpleNamespace(get_material_property_input_node=graph_probe),
            MaterialProperty=SimpleNamespace(MP_EMISSIVE_COLOR=0))

    def row(self):
        return {"master": "/Game/Test/M_Normal01", "plan": {
            "two_sided": True, "disable_depth_test": False, "blend": "BLEND_AlphaComposite"}}

    def test_native_enum_display_format_does_not_reject_valid_material(self):
        native = self.native(NativeBlend.BLEND_ALPHA_COMPOSITE, NativeShading.MSM_UNLIT)
        with self.assertRaisesRegex(RuntimeError, "已通过原生枚举门槛"):
            UE.verify_normal01_material(native, self.row())

    def test_wrong_native_blend_rejected_before_custom_graph(self):
        native = self.native(NativeBlend.BLEND_TRANSLUCENT, NativeShading.MSM_UNLIT)
        with self.assertRaisesRegex(RuntimeError, "新材质混合／光照属性不同.*actual_blend.*BLEND_TRANSLUCENT"):
            UE.verify_normal01_material(native, self.row())

    def test_lit_material_rejected_before_custom_graph(self):
        native = self.native(NativeBlend.BLEND_ALPHA_COMPOSITE, NativeShading.MSM_DEFAULT_LIT)
        with self.assertRaisesRegex(RuntimeError, "新材质混合／光照属性不同.*actual_shading.*MSM_DEFAULT_LIT"):
            UE.verify_normal01_material(native, self.row())


def fbx_node(name, props=(), children=()):
    return SimpleNamespace(name=name, props=list(props), children=list(children))


class NativeRenderColors(unittest.TestCase):
    def source(self):
        return {"m_VertexCount": 3, "m_Indices": [0, 1, 2], "m_Colors": [1.] * 12}

    def geometry(self, explicit=False):
        geometry = fbx_node("Geometry", children=[
            fbx_node("PolygonVertexIndex", [("i", 3, 0, [0, 1, -3])])])
        if explicit:
            geometry.children += [fbx_node("LayerElementColor", [0], [
                fbx_node("MappingInformationType", [b"ByPolygonVertex"]),
                fbx_node("ReferenceInformationType", [b"IndexToDirect"]),
                fbx_node("Colors", [("d", 8, 0, [1., 1., 1., 1., .2, .2, .2, .2])]),
                fbx_node("ColorIndex", [("i", 3, 0, [0, 1, 0])])]),
                fbx_node("Layer", [0], [fbx_node("LayerElement", children=[
                    fbx_node("Type", [b"LayerElementColor"]), fbx_node("TypedIndex", [0])])])]
        return geometry

    def read(self, geometry, source):
        return UE.normal01_render_colors(geometry, source, vertex_color=True, export_source_mesh=False)

    def test_complete_white_corners_use_native_implicit_white(self):
        self.assertEqual(self.read(self.geometry(), self.source()),
                         ([1., 1., 1., 1.], [0, 0, 0], "implicit_opaque_white"))

    def test_nonwhite_missing_layer_rejected_including_nonopaque_alpha(self):
        for channel in (0, 3):
            with self.subTest(channel=channel):
                source = self.source()
                source["m_Colors"][4 + channel] = .999
                with self.assertRaisesRegex(RuntimeError, "非白源角点"):
                    self.read(self.geometry(), source)

    def test_missing_or_invalid_rgba_never_becomes_white(self):
        for colors in (None, [], [1.] * 11, [1.] * 11 + [float("nan")], [1.] * 11 + [2.]):
            with self.subTest(colors=colors):
                source = self.source()
                source["m_Colors"] = colors
                with self.assertRaisesRegex(RuntimeError, "源 RGBA"):
                    self.read(self.geometry(), source)

    def test_export_request_must_read_back_as_render_data_with_vertex_color(self):
        for vertex_color, export_source_mesh in ((False, False), (True, True), (None, False)):
            with self.subTest(options=(vertex_color, export_source_mesh)):
                with self.assertRaisesRegex(RuntimeError, "实际启用 vertex_color"):
                    UE.normal01_render_colors(self.geometry(), self.source(),
                        vertex_color=vertex_color, export_source_mesh=export_source_mesh)

    def test_explicit_color_buffer_keeps_actual_corner_values(self):
        rgba, indices, storage = self.read(self.geometry(explicit=True), self.source())
        self.assertEqual(rgba[4:8], [.2] * 4)
        self.assertEqual(indices, [0, 1, 0])
        self.assertEqual(storage, "explicit_render_color_buffer")

    def test_explicit_rgba_and_corner_arrays_must_be_complete(self):
        for fault in ("missing_rgba", "short_rgba", "nonfinite_rgba", "bad_index", "short_indices", "short_geometry"):
            with self.subTest(fault=fault):
                geometry = self.geometry(explicit=True)
                color = geometry.children[1]
                if fault == "missing_rgba":
                    color.children.pop(2)
                elif fault == "short_rgba":
                    color.children[2].props[0] = ("d", 3, 0, [1.] * 3)
                elif fault == "nonfinite_rgba":
                    color.children[2].props[0][3][0] = float("nan")
                elif fault == "bad_index":
                    color.children[3].props[0][3][1] = 2
                elif fault == "short_indices":
                    color.children[3].props[0][3].pop()
                else:
                    geometry.children[0].props[0][3].pop()
                with self.assertRaises(RuntimeError):
                    self.read(geometry, self.source())

    def test_wrong_multiple_and_dangling_color_layers_rejected(self):
        for fault in ("layer_index", "reference_index", "reference_layer", "multiple", "dangling"):
            with self.subTest(fault=fault):
                geometry = self.geometry(explicit=True)
                color, layer = geometry.children[1:]
                if fault == "layer_index":
                    color.props = [1]
                elif fault == "reference_index":
                    layer.children[0].children[1].props = [1]
                elif fault == "reference_layer":
                    layer.props = [1]
                elif fault == "multiple":
                    geometry.children.append(copy.deepcopy(color))
                else:
                    geometry.children.remove(color)
                with self.assertRaisesRegex(RuntimeError, "颜色层"):
                    self.read(geometry, self.source())


class ExactCreatedStage(unittest.TestCase):
    def setUp(self):
        saved = Path(__file__).resolve().parents[3] / "Saved"
        temporary = tempfile.TemporaryDirectory(dir=saved)
        self.root = Path(temporary.name)
        self.assertTrue(self.root.resolve().is_relative_to(saved.resolve()))
        self.addCleanup(temporary.cleanup)
        materials = {str(i): {"master": "/Game/FX/M_" + str(i), "instance": "/Game/FX/MI_" + str(i)} for i in range(4)}
        meshes = {str(i): {"path": "/Game/FX/Mesh_" + str(i)} for i in range(2)}
        targets = sorted([r[k] for r in materials.values() for k in ("master", "instance")]
                         + [r["path"] for r in meshes.values()])
        for package in targets + [UE.NORMAL01_SYSTEM, "/Game/FX/Old"]:
            path = self.disk(package)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(package.encode())
        self.manifest = {"targets": targets, "materials": materials, "imports": {"entries": meshes},
            "protected_hashes": {p: self.sha(self.disk(p)) for p in (UE.NORMAL01_SYSTEM, "/Game/FX/Old")},
            "before_configuration": configuration()}
        backup = self.root / "NS_before.uasset"
        backup.write_bytes(self.disk(UE.NORMAL01_SYSTEM).read_bytes())
        self.report = {"system": UE.NORMAL01_SYSTEM, "saved": False,
            "errors": ["原生 FBX 缺少唯一字段: LayerElementColor"], "saved_new_packages": targets,
            "new_package_hashes": {p: self.sha(self.disk(p)) for p in targets}, "protected_unchanged": True,
            "dirty_after": [], "before_configuration": configuration(), "backup": str(backup),
            "protected_hashes_after": {"/Game/FX/Old": self.manifest["protected_hashes"]["/Game/FX/Old"]}}
        self.path = self.root / "failed_creation.json"

    def disk(self, package):
        return self.root / (package[6:] + ".uasset")

    def sha(self, path):
        return hashlib.sha256(path.read_bytes()).hexdigest()

    def read(self):
        self.path.write_text(json.dumps(self.report), encoding="utf-8")
        return UE.normal01_created_packages(self.manifest, self.path, self.sha(self.path), self.disk)

    def test_complete_saved_phase_and_unchanged_old_system_are_accepted(self):
        result = self.read()
        self.assertFalse(result["saved"])
        self.assertEqual(len(result["saved_new_packages"]), 10)

    def test_partial_duplicate_or_outside_package_sets_are_rejected(self):
        original = copy.deepcopy(self.report)
        for saved in (original["saved_new_packages"][:-1],
                      original["saved_new_packages"][:-1] + [original["saved_new_packages"][0]],
                      original["saved_new_packages"] + ["/Game/FX/Other"]):
            with self.subTest(saved=saved):
                self.report = copy.deepcopy(original)
                self.report["saved_new_packages"] = saved
                with self.assertRaisesRegex(RuntimeError, "精确失败批次"):
                    self.read()

    def test_saved_system_wrong_failure_or_dirty_phase_are_rejected(self):
        original = copy.deepcopy(self.report)
        for key, value in (("saved", True), ("errors", ["其他错误"]), ("dirty_after", ["/Game/FX/Old"]),
                           ("protected_unchanged", False), ("new_package_hashes", {})):
            with self.subTest(key=key):
                self.report = copy.deepcopy(original)
                self.report[key] = value
                with self.assertRaisesRegex(RuntimeError, "精确失败批次"):
                    self.read()

    def test_changed_new_or_protected_disk_package_is_rejected(self):
        for package in (self.manifest["targets"][0], UE.NORMAL01_SYSTEM, "/Game/FX/Old"):
            with self.subTest(package=package):
                path = self.disk(package)
                original = path.read_bytes()
                path.write_bytes(b"changed")
                with self.assertRaisesRegex(RuntimeError, "实际包身份不同"):
                    self.read()
                path.write_bytes(original)

    def test_changed_report_backup_and_protection_identity_are_rejected(self):
        self.read()
        with self.assertRaisesRegex(RuntimeError, "冻结 SHA"):
            UE.normal01_created_packages(self.manifest, self.path, "0" * 64, self.disk)
        backup = Path(self.report["backup"])
        backup.write_bytes(b"wrong")
        with self.assertRaisesRegex(RuntimeError, "备份身份"):
            self.read()
        backup.write_bytes(self.disk(UE.NORMAL01_SYSTEM).read_bytes())
        self.report["protected_hashes_after"] = {}
        with self.assertRaisesRegex(RuntimeError, "原保护集合"):
            self.read()


if __name__ == "__main__":
    unittest.main()
