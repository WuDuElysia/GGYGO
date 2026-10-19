"""@file test_nap_avatar_simple_materials.py
@brief 材质独立读回的只读边界与拒绝场景，不模拟真实 UE 编译或画面。
"""
import copy
import json
import struct
import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "AAADocs/Scripts"))
from build_nap_avatar_simple_materials import NapAvatarSimpleBuilder as Builder
from zzz_fx_material_ue import ref


class Asset:
    def __init__(self, path, properties):
        self.path, self.properties = path, properties

    def get_path_name(self):
        return ref(self.path)["refPath"]

    def get_editor_property(self, name):
        return self.properties[name]


class Texture(Asset):
    pass


class Material(Asset):
    pass


class Instance(Asset):
    pass


def float32(value):
    return struct.unpack("f", struct.pack("f", value))[0]


class ReadOnlyLibrary:
    def __init__(self, native):
        self.native = native

    def __getattr__(self, name):
        raise AssertionError("只读检查调用了未声明/写入 API: " + name)

    def get_statistics(self, material):
        return self.native.statistics[material.path]

    def get_scalar_parameter_names(self, material):
        return [n for n, p in material.spec["params"].items() if p["dim"] == 1 and n not in material.missing]

    def get_vector_parameter_names(self, material):
        return [n for n, p in material.spec["params"].items() if p["dim"] == 4 and n not in material.missing]

    def get_texture_parameter_names(self, material):
        return list(material.spec["textures"])

    def get_material_instance_scalar_parameter_value(self, instance, name):
        return instance.values[name]

    def get_material_instance_vector_parameter_value(self, instance, name):
        return SimpleNamespace(**dict(zip("rgba", instance.values[name])))

    def get_material_instance_texture_parameter_value(self, instance, name):
        return self.native.assets.get(instance.textures[name])


class ReadOnlyNative:
    Texture2D, Material, MaterialInstanceConstant = Texture, Material, Instance

    def __init__(self, plan):
        self.assets, self.statistics, self.loads = {}, {}, []
        self.MaterialEditingLibrary = ReadOnlyLibrary(self)
        for item in plan["textures"].values():
            self.assets[item["path"]] = Texture(item["path"], self.properties(item["properties"]))
        for spec in plan["materials"]:
            master = Material(spec["master"], self.properties(spec["properties"]))
            master.spec, master.missing = copy.deepcopy(spec), set()
            self.assets[master.path] = master
            self.statistics[master.path] = SimpleNamespace(num_pixel_shader_instructions=32, num_vertex_shader_instructions=24)
            instance = Instance(spec["instance"], {"parent": master})
            instance.values = {n: float32(p["value"]) if p["dim"] == 1 else [float32(v) for v in p["value"]]
                               for n, p in spec["params"].items()}
            instance.textures = dict(spec["textures"])
            self.assets[instance.path] = instance

    @staticmethod
    def properties(properties):
        return {Builder._property_name(k): "Enum." + Builder._property_name(v).upper() if isinstance(v, str) else v
                for k, v in properties.items()}

    def load_asset(self, path):
        self.loads.append(path)
        return self.assets.get(path)

    def __getattr__(self, name):
        raise AssertionError("只读检查触及写入/编译宿主入口: " + name)


class MaterialReadbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        resource = ROOT / "Saved/Codex/PyriosGhostResourceTools_20261010_R1/resource_plan.json"
        cls.plan = json.loads(resource.read_text(encoding="utf-8-sig"))["material_plan"]

    def setUp(self):
        self.native = ReadOnlyNative(self.plan)
        self.builder = Builder(None, unreal=self.native)

    def test_existing_assets_read_back_without_creation_compilation_or_session(self):
        result = self.builder.verify(self.plan)
        self.assertTrue(result["material_binding_readback_verified"])
        self.assertEqual(result["bindings"], self.plan["bindings"])
        self.assertEqual(set(self.native.loads), set(self.plan["targets"]))
        for name in ("cold_host_verified", "material_graph_bytes_verified", "gpu_draw_verified", "visual_verified"):
            self.assertFalse(result[name])

    def test_wrong_hdr_is_rejected(self):
        spec = self.plan["materials"][0]
        self.native.assets[spec["instance"]].values["_ScreenColor"] = [1, 1, 1, 1]
        with self.assertRaisesRegex(RuntimeError, "有效参数"):
            self.builder.verify(self.plan)

    def test_wrong_parent_is_rejected(self):
        surface, outline = self.plan["materials"]
        self.native.assets[surface["instance"]].properties["parent"] = self.native.assets[outline["master"]]
        with self.assertRaisesRegex(RuntimeError, "Parent"):
            self.builder.verify(self.plan)

    def test_missing_zero_parameter_is_not_accepted_as_valid_zero(self):
        spec = self.plan["materials"][0]
        self.native.assets[spec["master"]].missing.add("_OverrideRimGlow")
        with self.assertRaisesRegex(RuntimeError, "未注册必需参数"):
            self.builder.verify(self.plan)

    def test_missing_texture_binding_is_rejected(self):
        spec = self.plan["materials"][0]
        self.native.assets[spec["instance"]].textures["_ScreenTex"] = "/Game/Missing"
        with self.assertRaisesRegex(RuntimeError, "有效纹理"):
            self.builder.verify(self.plan)

    def test_changed_depth_policy_is_rejected(self):
        spec = self.plan["materials"][0]
        self.native.assets[spec["master"]].properties["disable_depth_test"] = True
        with self.assertRaisesRegex(RuntimeError, "资源设置"):
            self.builder.verify(self.plan)

    def test_unavailable_shader_statistics_does_not_trigger_recompile(self):
        spec = self.plan["materials"][0]
        self.native.statistics[spec["master"]].num_pixel_shader_instructions = 0
        with self.assertRaisesRegex(RuntimeError, "尚未取得有效编译统计"):
            self.builder.verify(self.plan)

    def test_no_native_host_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "unreal 宿主"):
            Builder(None).verify(self.plan)


if __name__ == "__main__":
    unittest.main()
