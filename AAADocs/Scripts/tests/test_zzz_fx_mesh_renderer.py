"""@file 静态源几何准备、材质重绘及完整预制体拒绝的离线验证。"""
import copy
import json
import math
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent))
import zzz_fx_build as B
import zzz_fx_mesh_renderer as M


def node(name="Mesh"):
    return {"name": name, "active": True, "pos": dict(x=0, y=0, z=0),
            "rot": dict(x=0, y=0, z=0, w=1), "scale": dict(x=1, y=1, z=1),
            "components": [{"type": "MeshFilter"}, {"type": "MeshRenderer"}],
            "componentListProof": {"status": "complete"}, "scripts": [], "children": [],
            "mesh": {"enabled": True, "mesh": {"m_FileID": 1, "m_PathID": 7},
                     "materials": [{"m_FileID": 1, "m_PathID": 9}, {"m_FileID": 1, "m_PathID": 9}]}}


def geometry():
    return {"m_VertexCount": 3, "m_Vertices": [0, 0, 0, 1, 0, 0, 0, 1, 0],
            "m_Indices": [0, 1, 2], "m_SubMeshes": [{"firstByte": 0, "indexCount": 3,
            "baseVertex": 0, "topology": "Triangles"}], "m_Colors": [.5, .25, .75, 1] * 3,
            "m_UV0": [0, 0, 1, 0, 0, 1], "m_UV1": [.2, .3] * 3,
            "m_BindPose": [], "m_BoneNameHashes": [], "m_Skin": None}


class MeshTests(unittest.TestCase):
    def setUp(self):
        test_root = Path(__file__).resolve().parents[3] / "Saved" / "Codex"
        self.directory = tempfile.TemporaryDirectory(dir=test_root, prefix="FXMeshRenderer_Test_")
        if not Path(self.directory.name).resolve().is_relative_to(test_root.resolve()):
            raise AssertionError("测试临时目录必须位于工程 Saved/Codex")
        self.addCleanup(self.directory.cleanup)
        self.mesh_file = Path(self.directory.name) / "mesh.json"
        self.write_geometry(geometry())
        self.deps = {"7": {"type": "Mesh", "pathID": 7, "name": "Pose", "cab": "MeshCAB",
                    "files": [str(self.mesh_file)], "coordinateConversion": "explicit source export basis"},
                     "9": {"type": "Material", "pathID": 9, "name": "Ghost", "cab": "MaterialCAB"}}

    def write_geometry(self, data):
        self.mesh_file.write_text(json.dumps(data), encoding="utf-8")

    def inspect(self, n=None, path=None, clip=None):
        n = n or node()
        return M.inspect(n, path if path is not None else [n], self.deps, clip)

    def test_duplicate_material_slots_remain_two_draws_of_same_submesh(self):
        c = self.inspect()
        self.assertEqual([(m["slot"], m["submesh"], m["pid"]) for m in c["materials"]],
                         [(0, 0, "9"), (1, 0, "9")])
        self.assertEqual(c["mesh"]["vertex_channels"], {"m_Colors": 4, "m_UV0": 2, "m_UV1": 2})
        self.assertEqual(c["render_preflight"], "inspection_only")
        self.assertTrue(c["required_consumers"])

    def test_child_offset_is_scaled_and_rotated_by_full_ancestor_chain(self):
        parent, child = node("Parent"), node("Child")
        parent["pos"]["x"] = 4
        parent["scale"] = dict(x=2, y=2, z=2)
        parent["rot"] = dict(x=0, y=0, z=math.sqrt(.5), w=math.sqrt(.5))
        child["pos"]["x"] = 1
        c = self.inspect(child, [parent, child])
        position = [float(v) for v in c["transform"]["position_hlsl"][7:-1].split(",")]
        for actual, expected in zip(position, (4, 2, 0)):
            self.assertAlmostEqual(actual, expected)
        self.assertEqual(c["transform"]["scale"], [2, 2, 2])
        self.assertEqual(len(c["transform"]["source_nodes"]), 2)

    def test_prefab_root_placement_does_not_become_guessed_actor_offset(self):
        n = node()
        n["pos"]["z"] = 999
        c = self.inspect(n, [])
        self.assertEqual(c["transform"]["position_hlsl"], "float3(0.0, 0.0, 0.0)")
        self.assertEqual(c["transform"]["root_actor_binding"], "unresolved")

    def test_existing_animation_expression_does_not_supply_source_lifetime(self):
        n = node()
        keys = [{"time": t, "value": [t, 0, 0], "in": [1, 0, 0], "out": [1, 0, 0], "weighted": 0}
                for t in (0, .1)]
        clip = {"position": {"Mesh": keys}, "rotation": {}, "scale": {}, "euler": {},
                "float": [], "length": 1, "wrap": 0}
        c = self.inspect(n, [n], clip)
        self.assertTrue(c["transform"]["animated"])
        self.assertTrue(any("System.Age" in item[2] for item in c["transform"]["temporaries"]))
        self.assertNotIn("lifetime", c)
        self.assertEqual(c["render_preflight"], "inspection_only")

    def test_mesh_pointer_zero_is_not_replaced_by_baked_geometry(self):
        n = node()
        n["mesh"]["mesh"]["m_PathID"] = 0
        with self.assertRaisesRegex(M.MeshContractError, "PPtr=0"):
            self.inspect(n)

    def test_invalid_geometry_is_rejected_before_contract(self):
        cases = [("索引超出", lambda d: d["m_Indices"].__setitem__(0, 3)),
                 ("有限数值", lambda d: d["m_Vertices"].__setitem__(0, float("nan"))),
                 ("静态 Mesh", lambda d: d.__setitem__("m_Skin", [1])),
                 ("子网格索引字宽", lambda d: d["m_SubMeshes"].append(copy.deepcopy(d["m_SubMeshes"][0]))),
                 ("数量与顶点数", lambda d: d["m_Colors"].pop())]
        for reason, change in cases:
            with self.subTest(reason=reason):
                data = geometry()
                change(data)
                self.write_geometry(data)
                with self.assertRaisesRegex(M.MeshContractError, reason):
                    self.inspect()

    def test_shear_cannot_use_lossy_scale_for_complete_mesh_geometry(self):
        parent, child = node("Parent"), node("Child")
        parent["scale"]["x"] = 2
        child["rot"] = dict(x=0, y=0, z=math.sin(math.pi/8), w=math.cos(math.pi/8))
        with self.assertRaisesRegex(M.MeshContractError, "切变"):
            self.inspect(child, [parent, child])

    def test_missing_material_or_source_component_is_not_a_ready_renderer(self):
        for change in [lambda n: n["mesh"].__setitem__("materials", []),
                       lambda n: n.__setitem__("componentListProof", None),
                       lambda n: n["components"].append({"type": "MeshRenderer"})]:
            n = node()
            change(n)
            with self.assertRaises(M.MeshContractError):
                self.inspect(n)

    def test_missing_bone_fields_and_export_basis_are_not_guessed(self):
        data = geometry()
        del data["m_Skin"]
        self.write_geometry(data)
        with self.assertRaisesRegex(M.MeshContractError, "不把缺字段当空值"):
            self.inspect()
        self.write_geometry(geometry())
        del self.deps["7"]["coordinateConversion"]
        with self.assertRaisesRegex(M.MeshContractError, "坐标约定"):
            self.inspect()

    def test_full_prefab_preflight_exposes_prepared_contract_and_blocks_all_writes(self):
        source = Path(self.directory.name) / "source.fx.json"
        source.write_text(json.dumps({"schemaVersion": 2, "name": "Fixture", "root": node()}), encoding="utf-8")
        source.with_name("source.deps.v2.json").write_text(json.dumps(self.deps), encoding="utf-8")
        with patch.object(B, "AssetSession", side_effect=AssertionError("禁止资产写入")):
            with self.assertRaises(B.PreflightError) as raised:
                B.preflight(source, assets={})
        report = raised.exception.report
        self.assertEqual(report["renderers"], [])
        self.assertEqual(report["mesh_renderer_contracts"][0]["render_preflight"], "inspection_only")
        self.assertEqual(len(report["blocked"]), 3)
        self.assertEqual(report["action_integration"], "unverified")

    def test_component_inventory_without_mesh_description_is_not_silently_skipped(self):
        source = Path(self.directory.name) / "source.fx.json"
        n = node()
        del n["mesh"]
        source.write_text(json.dumps({"schemaVersion": 2, "name": "Fixture", "root": n}), encoding="utf-8")
        source.with_name("source.deps.v2.json").write_text(json.dumps(self.deps), encoding="utf-8")
        with self.assertRaisesRegex(B.PreflightError, "source description is missing"):
            B.preflight(source, assets={})

    def test_real_exported_ghosts_preserve_geometry_and_repeated_materials(self):
        root = Path("F:/AnimeStudio/Exports/ZZZ/Pyrois_SkillFX_Evidence/Prefabs")
        cases = [("Eff_Pyrois_Attack_Normal_03_02_Hit", 13667, 2),
                 ("Eff_Pyrois_Attack_Normal_03_08_Hit", 13662, 1)]
        for name, vertices, draws in cases:
            with self.subTest(name=name):
                source = json.loads((root/(name + ".fx.json")).read_text(encoding="utf-8-sig"))
                deps = json.loads((root/(name + ".deps.v2.json")).read_text(encoding="utf-8-sig"))
                target = next(n for n in source["root"]["children"] if n.get("mesh"))
                c = M.inspect(target, [target], deps)
                self.assertEqual(c["mesh"]["vertex_count"], vertices)
                self.assertEqual(c["mesh"]["index_count"], 39258)
                self.assertEqual(len(c["materials"]), draws)
                self.assertEqual(c["mesh"]["vertex_channels"]["m_Colors"], 4)
                self.assertTrue(all("m_UV%d" % i in c["mesh"]["vertex_channels"] for i in range(3)))
                self.assertEqual(c["transform"]["root_actor_binding"], "unresolved")


if __name__ == "__main__":
    unittest.main()
