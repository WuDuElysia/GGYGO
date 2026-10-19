"""反向绕序后的角点语义，以及显式源色导入的版本／准入契约。"""
import json
import re
import struct
import tempfile
import unittest
from pathlib import Path

import zzz_mesh_fbx as FBX
import zzz_fx_import_assets as IMPORT


def array(text, name, value_type=float):
    match = re.search(r"\b" + re.escape(name) + r":\s*\*(\d+)\s*\{\s*a:\s*([^}]+)\}", text)
    values = [value_type(v.strip()) for v in match[2].split(",")]
    if len(values) != int(match[1]):
        raise AssertionError("FBX 数组计数不同")
    return values


class MeshCorners(unittest.TestCase):
    def mesh(self):
        return {"m_Name": "Corners", "m_VertexCount": 4,
            "m_Vertices": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12],
            "m_Indices": [0, 1, 2, 0, 2, 3],
            "m_SubMeshes": [{"indexCount": 3}, {"indexCount": 3}],
            "m_Normals": [1, 0, 0, 0, 1, 0, 0, 0, 1, -1, 0, 0],
            "m_Colors": [1, 0, 0, 0, 0, 1, 0, .2, 0, 0, 1, .5, 1, 1, 1, 1],
            "m_UV0": [.1, .2, .3, .4, .5, .6, .7, .8],
            "m_UV1": [.8, .7, .6, .5, .4, .3, .2, .1]}

    def test_attributes_follow_exported_corner_after_winding_change(self):
        source = self.mesh()
        text = FBX.build(source)
        positions = array(text, "Vertices")
        polygons = array(text, "PolygonVertexIndex", int)
        normals, colors = array(text, "Normals"), array(text, "Colors")
        self.assertEqual(len(positions), 12)
        self.assertEqual(polygons, [2, 1, -1, 3, 2, -1])
        self.assertEqual(array(text, "Materials", int), [0, 1])
        self.assertNotIn('MappingInformationType: "ByControlPoint"', text)
        uv_layers = re.findall(r"LayerElementUV:\s*\d+\s*\{(.*?)\n\t\t\}", text, re.S)
        self.assertEqual(len(uv_layers), 2)
        for corner, encoded in enumerate(polygons):
            point = encoded if encoded >= 0 else -encoded - 1
            p = source["m_Vertices"][point * 3:point * 3 + 3]
            self.assertEqual(positions[point * 3:point * 3 + 3], [-p[0]*100, p[1]*100, p[2]*100])
            n = source["m_Normals"][point * 3:point * 3 + 3]
            self.assertEqual(normals[corner * 3:corner * 3 + 3], [-n[0], n[1], n[2]])
            self.assertEqual(colors[corner * 4:corner * 4 + 4], source["m_Colors"][point * 4:point * 4 + 4])
            for channel, layer in enumerate(uv_layers):
                values, indices = array(layer, "UV"), array(layer, "UVIndex", int)
                self.assertIn('MappingInformationType: "ByPolygonVertex"', layer)
                self.assertIn('ReferenceInformationType: "IndexToDirect"', layer)
                uv_point = indices[corner]
                self.assertEqual(values[uv_point * 2:uv_point * 2 + 2],
                                 source["m_UV%d" % channel][point * 2:point * 2 + 2])

    def test_uv_gap_is_rejected_instead_of_relabelled(self):
        mesh = self.mesh()
        mesh["m_UV2"] = mesh.pop("m_UV1")
        with self.assertRaisesRegex(ValueError, "缺失"):
            FBX.build(mesh)

    def test_preserved_winding_keeps_every_attribute_on_its_control_point(self):
        source = self.mesh()
        text = FBX.build(source, reverse_winding=False)
        polygons = array(text, "PolygonVertexIndex", int)
        self.assertEqual(polygons, [0, 1, -3, 0, 2, -4])
        points = [v if v >= 0 else -v - 1 for v in polygons]
        normals, colors = array(text, "Normals"), array(text, "Colors")
        for corner, point in enumerate(points):
            n = source["m_Normals"][point * 3:point * 3 + 3]
            self.assertEqual(normals[corner * 3:corner * 3 + 3], [-n[0], n[1], n[2]])
            self.assertEqual(colors[corner * 4:corner * 4 + 4], source["m_Colors"][point * 4:point * 4 + 4])
        for layer in re.findall(r"LayerElementUV:\s*\d+\s*\{(.*?)\n\t\t\}", text, re.S):
            self.assertEqual(array(layer, "UVIndex", int), points)
        with self.assertRaisesRegex(ValueError, "明确布尔值"):
            FBX.build(source, reverse_winding="source")

    def test_position_doubles_and_uv_float32_bits_survive_serialization(self):
        mesh = self.mesh()
        mesh["m_Vertices"] = [0.12345678901234568, -14.268642, 1.2345678901234567] * 4
        float32 = lambda value: struct.unpack("<f", struct.pack("<f", value))[0]
        mesh["m_UV2"] = [float32(value) for value in
            (32.000004, .123456789, -65.000007, 1.00000012, 1527.0, .000000123456789, .99999994, .7)]
        text = FBX.build(mesh)
        positions = array(text, "Vertices")
        self.assertEqual(positions, [value for _ in range(4) for value in
            (-mesh["m_Vertices"][0] * 100, mesh["m_Vertices"][1] * 100, mesh["m_Vertices"][2] * 100)])
        uv_layers = re.findall(r"LayerElementUV:\s*\d+\s*\{(.*?)\n\t\t\}", text, re.S)
        self.assertEqual(len(uv_layers), 3)
        uv2 = array(uv_layers[2], "UV")
        self.assertEqual([struct.pack("<f", value) for value in uv2],
                         [struct.pack("<f", value) for value in mesh["m_UV2"]])
        corners = array(uv_layers[2], "UVIndex", int)
        self.assertEqual(corners, [2, 1, 0, 3, 2, 0])


class MeshImportContract(unittest.TestCase):
    def setUp(self):
        self.temp_root = Path(__file__).resolve().parents[3] / "Saved/Codex/FXTestTemp"
        self.temp_root.mkdir(parents=True, exist_ok=True)

    def test_source_color_settings_are_part_of_content_identity(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            root = Path(tmp)
            self.assertTrue(root.resolve().is_relative_to(self.temp_root))
            original, normalized = root / "old.fbx", root / "new.fbx"
            original.write_text("old")
            normalized.write_text("per-corner")
            deps = root / "deps.json"
            deps.write_text(json.dumps({"1": {"type": "Mesh", "name": "Corners", "files": [str(original)]}}))
            plan = IMPORT.plan_imports([deps], selected_pids=["1"], mesh_sources={"1": normalized})
            item = plan["entries"]["1"]
            self.assertEqual(item["source"], str(normalized))
            self.assertEqual(item["identity"]["mesh_import_settings"]["vertex_color_import_option"], "REPLACE")
            self.assertNotEqual(item["path"], IMPORT.plan_imports([deps], selected_pids=["1"])["assets"]["1"])
            with self.assertRaisesRegex(ValueError, "标准 Editor"):
                IMPORT.apply_imports(plan, object())
            normalized.write_text("changed")
            with self.assertRaisesRegex(ValueError, "source changed"):
                IMPORT.apply_imports(plan, object())

    def test_unselected_source_override_is_rejected(self):
        with tempfile.TemporaryDirectory(dir=self.temp_root) as tmp:
            root = Path(tmp)
            self.assertTrue(root.resolve().is_relative_to(self.temp_root))
            fbx = root / "one.fbx"
            fbx.write_text("one")
            deps = root / "deps.json"
            deps.write_text(json.dumps({"1": {"type": "Mesh", "name": "One", "files": [str(fbx)]}}))
            with self.assertRaisesRegex(ValueError, "明确选择"):
                IMPORT.plan_imports([deps], selected_pids=["1"], mesh_sources={"2": fbx})


if __name__ == "__main__":
    unittest.main()
