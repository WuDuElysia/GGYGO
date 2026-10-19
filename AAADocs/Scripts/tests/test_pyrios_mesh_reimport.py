"""只验证本次颜色源边界及单 Mesh 保存保护，不启动 UE 或重导生产包。"""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch
from types import SimpleNamespace
import tempfile

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import reimport_pyrios_mesh_uv as tool
from fbx_bin_reader import Node


def node(name, props=(), *kids):
    value = Node(name)
    value.props = list(props)
    value.children = list(kids)
    return value


def array(name, values, kind="d"):
    return node(name, (("array", kind, len(values), list(values)),))


def source():
    color = node("LayerElementColor", (0,),
                 node("MappingInformationType", (b"ByVertice",)),
                 node("ReferenceInformationType", (b"Direct",)),
                 array("Colors", [0.5, 0.5, 0, 0]*3))
    registration = node("LayerElement", (), node("Type", (b"LayerElementColor",)), node("TypedIndex", (0,)))
    g = node("Geometry", (101, b"Body\x00\x01Geometry", b"Mesh"),
             array("Vertices", [0, 0, 0, 1, 0, 0, 0, 1, 0]),
             array("PolygonVertexIndex", [0, 1, -3], "i"),
             color, node("Layer", (0,), registration))
    return [node("Objects", (), g)]


def native(ids=(101, 102, 103, 104, 105)):
    g, model, skin, bone1, bone2 = ids
    geometry = source()[0].children[0]
    geometry.props[0] = g
    objects = node("Objects", (), geometry,
                   node("Model", (model, b"Mesh\x00\x01Model", b"Mesh")),
                   node("Deformer", (skin, b"BoneA\x00\x01SubDeformer", b"Cluster"),
                        array("Indexes", [0, 1, 2], "i"), array("Weights", [1, 1, 1])),
                   node("Model", (bone1, b"BoneA\x00\x01Model", b"LimbNode")),
                   node("Model", (bone2, b"BoneB\x00\x01Model", b"LimbNode")))
    links = node("Connections", (), node("C", (b"OO", g, model)), node("C", (b"OO", bone1, skin)))
    return [objects, links]


class SourceColorTests(unittest.TestCase):
    def check(self, roots):
        return tool.normalize_colors(roots, b"ByVertice", expected_count=1)

    def test_legal_cp_colors_preserve_zero_alpha(self):
        rgba = self.check(source())
        self.assertEqual(rgba, {101: {(128, 128, 0, 0)}})

    def test_mapping_empty_data_and_registration_are_real_requirements(self):
        for defect in ("mapping", "count", "registration", "nan"):
            roots = source()
            g = roots[0].children[0]
            color = tool.child(g, "LayerElementColor")
            if defect == "mapping":
                tool.child(color, "MappingInformationType").props = [b"NoMappingInformation"]
            elif defect == "count":
                tool.child(color, "Colors").props[0][3].pop()
            elif defect == "registration":
                tool.child(g, "Layer").children.clear()
            else:
                tool.child(color, "Colors").props[0][3][0] = float("nan")
            with self.subTest(defect=defect), self.assertRaises(RuntimeError):
                self.check(roots)

    def test_source_normalization_does_not_hide_geometry_or_alpha_changes(self):
        a, b = source(), source()
        self.check(a)
        self.check(b)
        self.assertEqual([tool.tree(n) for n in a], [tool.tree(n) for n in b])
        tool.child(b[0].children[0], "LayerElementColor").children[-1].props[0][3][3] = 1
        self.assertNotEqual([tool.tree(n) for n in a], [tool.tree(n) for n in b])


class NativeGeometryTests(unittest.TestCase):
    def contract(self, roots):
        with patch.object(tool, "read_fbx", return_value=roots):
            return tool.geometry_contract("native.fbx")

    def test_object_id_changes_are_not_geometry_changes(self):
        self.assertEqual(self.contract(native()), self.contract(native((201, 202, 203, 204, 205))))

    def bind_pose(self, temporary_id=999):
        roots = native()
        roots[0].children[3].props[-1] = b"Root"
        identity = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.]
        pose = node("Pose", (106, b"Mesh\x00\x01Pose", b"BindPose"),
                    node("Type", (b"BindPose",)), node("NbPoseNodes", (3,)),
                    *(node("PoseNode", (), node("Node", (i,)), array("Matrix", identity[:]))
                      for i in (0, temporary_id, 104)))
        roots[0].children.append(pose)
        return roots

    def test_removed_exporter_parent_id_is_stable_but_bind_matrices_remain_protected(self):
        baseline = self.contract(self.bind_pose())
        self.assertEqual(baseline, self.contract(self.bind_pose(998)))
        for index in (0, 1, 2):
            roots = self.bind_pose()
            nodes = [n for n in roots[0].children[-1].children if n.name == "PoseNode"]
            tool.child(nodes[index], "Matrix").props[0][3][12] = 1
            with self.subTest(index=index):
                if index < 2:
                    with self.assertRaises(RuntimeError):
                        self.contract(roots)
                else:
                    self.assertNotEqual(baseline, self.contract(roots))

    def test_unknown_bind_reference_or_connected_parent_is_not_normalized(self):
        for defect in ("unknown_bone", "connected_parent", "position"):
            roots = self.bind_pose()
            nodes = [n for n in roots[0].children[-1].children if n.name == "PoseNode"]
            if defect == "unknown_bone":
                tool.child(nodes[2], "Node").props = [998]
            elif defect == "connected_parent":
                roots[1].children.append(node("C", (b"OO", 999, 0)))
            else:
                tool.child(nodes[1], "Node").props = [104]
                tool.child(nodes[2], "Node").props = [999]
            with self.subTest(defect=defect), self.assertRaises(RuntimeError):
                self.contract(roots)

    def test_color_difference_is_intentional_but_uv_skin_and_bone_binding_are_protected(self):
        baseline = self.contract(native())
        colors = native()
        tool.child(colors[0].children[0], "LayerElementColor").children[-1].props[0][3][0] = 1
        self.assertEqual(baseline, self.contract(colors))
        for defect in ("skin", "binding", "geometry", "uv"):
            roots = native()
            if defect == "skin":
                tool.child(roots[0].children[2], "Weights").props[0][3][0] = 0.5
            elif defect == "binding":
                roots[1].children[-1].props[-2] = 105
            elif defect == "geometry":
                tool.child(roots[0].children[0], "Vertices").props[0][3][0] = 1
            else:
                roots[0].children[0].children.append(node("LayerElementUV", (0,), array("UV", [0.2, 0.7])))
            with self.subTest(defect=defect):
                self.assertNotEqual(baseline, self.contract(roots))

    def test_wrong_rgba_in_the_correct_material_slot_is_rejected(self):
        roots = native()
        g = roots[0].children[0]
        tool.child(g, "PolygonVertexIndex").props[0] = ("array", "i", 23408*3, [0, 1, -3]*23408)
        g.children.append(node("LayerElementMaterial", (0,),
                               node("MappingInformationType", (b"ByPolygon",)),
                               array("Materials", [0]*23408, "i")))
        roots[0].children.append(node("Material", (106, b"MI_Body\x00\x01Material")))
        roots[1].children.append(node("C", (b"OO", 106, 102)))
        material = SimpleNamespace(material_interface=SimpleNamespace(get_name=lambda: "MI_Body"),
                                   material_slot_name="SourceSlot")
        expected = {"SourceSlot": {(128, 128, 0, 0)}}
        with patch.object(tool, "read_fbx", return_value=roots):
            tool.validate_native_colors("native.fbx", expected, [material])
            for channel in (2, 3):
                broken = copy.deepcopy(roots)
                tool.child(broken[0].children[0], "LayerElementColor").children[-1].props[0][3][channel] = 1
                with patch.object(tool, "read_fbx", return_value=broken), self.subTest(channel=channel), self.assertRaises(RuntimeError):
                    tool.validate_native_colors("native.fbx", expected, [material])


class SingleMeshSaveTests(unittest.TestCase):
    def test_started_failed_partial_or_foreign_import_is_not_success(self):
        mesh = object()
        tool.require_import_result([mesh], mesh)
        for result in (None, True, False, [], [mesh, object()], (True, [mesh])):
            with self.subTest(result=result), self.assertRaises(RuntimeError):
                tool.require_import_result(result, mesh)

    def test_shared_state_changes_reject_save(self):
        before = dict(bones=[("Root", "None", "pose")], sockets=["WeaponSocket"], skeleton="Skeleton",
                      materials=["OriginalMI"], section_slots=[0, 1, 2, 3], lod_build="KeepNormals")
        tool.assert_preserved(before, copy.deepcopy(before))
        tool.assert_preserved(json.loads(json.dumps(before)), before)
        for key in before:
            after = copy.deepcopy(before)
            after[key] = "changed"
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                tool.assert_preserved(before, after)

    def test_only_mesh_bytes_may_change_after_save(self):
        filename = tool.MESH_PATH.rsplit("/", 1)[-1] + ".uasset"
        before = {filename: "a", "Skeleton.uasset": "s", "Animation/Idle.uasset": "i", "Materials/MI.uasset": "m"}
        after = dict(before, **{filename: "b"})
        with self.assertRaises(RuntimeError):
            tool.assert_package_protection(before, after)
        tool.assert_package_protection(before, after, allow_mesh=True)
        for key in ("Skeleton.uasset", "Animation/Idle.uasset", "Materials/MI.uasset", "new.uasset"):
            broken = dict(after, **{key: "changed"})
            with self.subTest(key=key), self.assertRaises(RuntimeError):
                tool.assert_package_protection(before, broken, allow_mesh=True)


class SourceNormalTests(unittest.TestCase):
    def streams(self):
        ps = [[0, 0, 0], [1, 0, 0], [0, 1, 0]]
        ns = [[0, 0, 1]] * 3
        uv = [[[0, 0], [1, 0], [0, 1]]] * 3
        rows = [[ps, ns, uv]]
        candidates = {tuple(p): [(tuple(p), (0, 0, 1), tuple(v for layer in uv for v in layer[i]))]
                      for i, p in enumerate(ps)}
        return rows, candidates

    def test_complete_original_normals_and_uvs_are_required(self):
        rows, candidates = self.streams()
        self.assertEqual(tool.validate_source_normals(rows, candidates, 1)["corners"], 3)
        for defect in ("missing_triangle", "missing_corner", "normal", "zero", "nan", "position", "uv"):
            bad = copy.deepcopy(rows)
            if defect == "missing_triangle":
                bad.clear()
            elif defect == "missing_corner":
                bad[0][1].pop()
            elif defect == "normal":
                bad[0][1][0] = [1, 0, 0]
            elif defect == "zero":
                bad[0][1][0] = [0, 0, 0]
            elif defect == "nan":
                bad[0][1][0] = [float("nan"), 0, 1]
            elif defect == "position":
                bad[0][0][0][0] = 0.2
            else:
                bad[0][2][0][0][0] = 0.2
            with self.subTest(defect=defect), self.assertRaises(RuntimeError):
                tool.validate_source_normals(bad, candidates, 1)

    def test_normal_omission_keeps_vertex_colors_and_skin_protected(self):
        roots = native()
        g = roots[0].children[0]
        g.children.append(node("LayerElementNormal", (0,), array("Normals", [0, 0, 1]*3)))
        def contract(r):
            with patch.object(tool, "read_fbx", return_value=r):
                return tool.geometry_contract("mesh.fbx", omit_colors=False, omit_normals=True)
        baseline = contract(roots)
        changed = copy.deepcopy(roots)
        tool.child(changed[0].children[0], "LayerElementNormal").children[-1].props[0][3][0] = 0.8
        self.assertEqual(baseline, contract(changed))
        for defect in ("color", "skin"):
            bad = copy.deepcopy(changed)
            if defect == "color":
                tool.child(bad[0].children[0], "LayerElementColor").children[-1].props[0][3][0] = 1
            else:
                tool.child(bad[0].children[2], "Weights").props[0][3][0] = 0.5
            with self.subTest(defect=defect):
                self.assertNotEqual(baseline, contract(bad))

    def test_native_reader_refuses_failed_copy_or_render_fallback_normals(self):
        dynamic = SimpleNamespace(get_triangle_count=lambda: 1)
        failure = object()
        ue = SimpleNamespace(DynamicMesh=lambda: dynamic, GeometryScriptCopyMeshFromAssetOptions=lambda **kw: kw,
                             GeometryScriptMeshReadLOD=lambda **kw: kw,
                             GeometryScriptLODType=SimpleNamespace(SOURCE_MODEL="source"),
                             GeometryScriptOutcomePins=SimpleNamespace(SUCCESS="success"),
                             GeometryScript_AssetUtils=SimpleNamespace(copy_mesh_from_skeletal_mesh=lambda *a: (dynamic, failure)))
        with self.assertRaisesRegex(RuntimeError, "copy failed"):
            tool.read_source_normals(ue, object())
        rows, candidates = self.streams()
        # 原生接口可能回落 RenderData；重算法线必须在原源对照处拒绝，而非补原法线。
        rows[0][1][1] = [0, 1, 0]
        with self.assertRaisesRegex(RuntimeError, "differs from original"):
            tool.validate_source_normals(rows, candidates, 1)

    def test_save_only_follows_complete_native_build_protection(self):
        from contextlib import ExitStack
        saved = Path(__file__).resolve().parents[3] / "Saved"
        saved.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(prefix="PyriosNormalTest_", dir=saved) as name:
            output = Path(name).resolve()
            self.assertEqual(output.parent, saved.resolve())
            mesh = SimpleNamespace(has_vertex_colors=lambda: True,
                                   get_editor_property=lambda n: SimpleNamespace(extract_filenames=lambda: ["source"]))
            rows, candidates = self.streams()
            expected = dict(lod_build="NormalsFalse_TangentsTrue", bones=["Root"], materials=["OriginalMI"])
            hashes = {"Avatar_Male_Size03_Pyrois_Model.uasset": "before", "Materials/Master.uasset": "keep"}
            for defect in (None, "native", "source", "built_normal", "geometry", "foreign_dirty", "foreign_disk", "save_false"):
                events = []
                actual = copy.deepcopy(expected)
                if defect == "native":
                    actual["bones"] = ["Changed"]
                raw = copy.deepcopy(rows)
                if defect == "source":
                    raw[0][1][0] = [1, 0, 0]
                disk = dict(hashes)
                dirty = {tool.MESH_PATH, "/Game/Foreign"} if defect == "foreign_dirty" else {tool.MESH_PATH}
                if defect == "foreign_disk":
                    disk["Materials/Master.uasset"] = "changed"
                def save(asset, only_if_is_dirty):
                    self.assertIs(asset, mesh)
                    self.assertTrue(only_if_is_dirty)
                    events.append("save")
                    if defect == "save_false":
                        return False
                    dirty.clear()
                    disk["Avatar_Male_Size03_Pyrois_Model.uasset"] = "after"
                    return True
                ue = SimpleNamespace(EditorAssetLibrary=SimpleNamespace(save_loaded_asset=save), log=lambda s: events.append(s))
                with ExitStack() as stack:
                    stack.enter_context(patch.object(tool, "native_snapshot", return_value=actual))
                    stack.enter_context(patch.object(tool, "read_source_normals", return_value=raw))
                    built = copy.deepcopy(rows)
                    if defect == "built_normal":
                        built[0][1][0] = [1, 0, 0]
                    stack.enter_context(patch.object(tool, "exported_normal_rows", return_value=built))
                    stack.enter_context(patch.object(tool, "source_normal_candidates", return_value=(candidates, 1)))
                    stack.enter_context(patch.object(tool, "export_lod0", side_effect=lambda *a: events.append("export")))
                    stack.enter_context(patch.object(tool, "geometry_contract", side_effect=lambda p, **kw: "bad" if defect == "geometry" and p.name == "after.fbx" else "same"))
                    stack.enter_context(patch.object(tool, "dirty", side_effect=lambda u: set(dirty)))
                    stack.enter_context(patch.object(tool, "package_hashes", side_effect=lambda: dict(disk)))
                    stack.enter_context(patch.object(tool, "sha", side_effect=lambda p: tool.ORIGINAL_SHA if p == tool.ORIGINAL else tool.SOURCE_SHA))
                    if defect:
                        with self.subTest(defect=defect), self.assertRaises(RuntimeError):
                            tool.finish_normal_build(ue, mesh, output, expected, hashes, rows, ["source"])
                        self.assertEqual(events.count("save"), 1 if defect == "save_false" else 0)
                        self.assertFalse((output / "saved_normals_readback.json").exists())
                    else:
                        tool.finish_normal_build(ue, mesh, output, expected, hashes, rows, ["source"])
                        self.assertLess(events.index("export"), events.index("save"))
                        self.assertEqual(events.count("save"), 1)
                        (output / "saved_normals_readback.json").unlink()


if __name__ == "__main__":
    unittest.main()
