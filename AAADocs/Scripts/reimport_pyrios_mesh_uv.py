"""@file reimport_pyrios_mesh_uv.py
@brief Pyrios 单 Mesh 颜色映射重导与原法线构建的独立生产入口。

标准 full-RHI Editor 中 run(output, apply=False) 预检；生产窗口才传 apply=True。
output 必须是 Saved 下的新目录。失败保留证据及内存，不自动回滚、丢弃或 SaveAll。
修正版记录为 Geometry source index 1；原 All/Skin 源保持。原生参考骨、槽、UV、
权重和其它包变化时拒绝保存。不重建材质，不改变法线／切线／曝光配置。
preserve_source_normals 消费同宿主原生源读回，只关闭法线重算；不重导、不改切线或材质。
"""
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from fbx_bin_reader import FbxReader, first_string_prop

MESH_PATH = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"
ORIGINAL = Path("F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model/Avatar_Male_Size03_Pyrois_Model.fbx")
ORIGINAL_SHA = "0c89d0ef09385299cc304ba0d17e2f0bb190a7ba22a54d8c1d185e15dacca277"
PROJECT = Path(__file__).resolve().parents[2]
SOURCE = PROJECT / "Saved/Codex/PyriosMeshSource_20261010_R1/Avatar_Male_Size03_Pyrois_Model.fbx"
SOURCE_SHA = "9b38deca9552d6889f6ebdb2148a3764ae9232f64a55851db695fcbd93a8b50f"
SLOTS = ("MAT_Pyrois_Body_1", "MAT_Pyrois_Body_2", "MAT_Pyrois_Body_FX01", "MAT_Pyrois_Weapon01")


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024*1024), b""):
            digest.update(block)
    return digest.hexdigest()


class EvidenceReader(FbxReader):
    """补保原 reader 跳过的 raw 属性；数组仍用其公开解码流程。"""
    def _read_prop(self):
        start = self.f.tell()
        value = super()._read_prop()
        end = self.f.tell()
        if isinstance(value, tuple) and value[0] == "raw":
            self.f.seek(start + 5)
            value = ("raw", self.f.read(value[1]))
            self.f.seek(end)
        return value


def read_fbx(path):
    reader = EvidenceReader(path, decode_arrays=True)
    try:
        roots = reader.parse()
        require(reader.version == 7300, "Expected qualified FBX2013: " + str(path))
        return roots
    finally:
        reader.close()


def child(node, name):
    matches = [n for n in node.children if n.name == name]
    require(len(matches) == 1, "Expected one " + name + " in " + node.name)
    return matches[0]


def values(node, name):
    value = child(node, name).props[0]
    require(value[0] == "array", "Expected array " + name)
    return value[3]


def named(node):
    return first_string_prop(node).split("\x00", 1)[0]


def tree(node, omit_colors=False, omit_normals=False):
    children = node.children
    if omit_colors:
        children = [n for n in children if n.name != "LayerElementColor" and not
                    (n.name == "LayerElement" and child(n, "Type").props == [b"LayerElementColor"])]
    if omit_normals:
        children = [n for n in children if n.name != "LayerElementNormal" and not
                    (n.name == "LayerElement" and child(n, "Type").props == [b"LayerElementNormal"])]
    return node.name, node.props, [tree(n, omit_colors, omit_normals) for n in children]


def normalize_colors(roots, mapping, expected_count=9):
    """只规范非空 Color0 的 mapping，并要求真正逐 CP 颜色及 Layer0 注册。"""
    objects = next(n for n in roots if n.name == "Objects")
    colors = {}
    for g in (n for n in objects.children if n.name == "Geometry"):
        cp_count = len(values(g, "Vertices")) // 3
        layers = [n for n in g.children if n.name == "LayerElementColor" and
                  any(c.name == "Colors" for c in n.children)]
        require(len(layers) == 1 and layers[0].props == [0], "Expected sole nonempty Color0: " + named(g))
        color = layers[0]
        require(child(color, "MappingInformationType").props == [mapping], "Invalid color mapping: " + named(g))
        require(child(color, "ReferenceInformationType").props == [b"Direct"], "Color must be Direct")
        rgba = values(color, "Colors")
        require(len(rgba) == cp_count * 4 and cp_count > 0, "Color/CP count mismatch")
        require(all(math.isfinite(c) and 0 <= c <= 1 for c in rgba), "Invalid source color")
        layer0 = [n for n in g.children if n.name == "Layer" and n.props == [0]]
        require(len(layer0) == 1, "Missing Layer0")
        require(any(n.name == "LayerElement" and child(n, "Type").props == [b"LayerElementColor"] and
                    child(n, "TypedIndex").props == [0] for n in layer0[0].children), "Color0 is not registered")
        colors[g.props[0]] = {tuple(round(c * 255) for c in rgba[i:i+4]) for i in range(0, len(rgba), 4)}
        child(color, "MappingInformationType").props = [b"ByVertice"]
    require(len(colors) == expected_count, "Qualified colored geometry count differs")
    return colors


def qualify_sources():
    require(sha(ORIGINAL) == ORIGINAL_SHA, "Original source identity changed")
    require(sha(SOURCE) == SOURCE_SHA, "Derived source identity changed")
    old, new = read_fbx(ORIGINAL), read_fbx(SOURCE)
    normalize_colors(old, b"NoMappingInformation")
    colors = normalize_colors(new, b"ByVertice")
    require([tree(n) for n in old] == [tree(n) for n in new], "Non-color-mapping FBX data changed")
    objects = next(n for n in new if n.name == "Objects")
    by_id = {n.props[0]: n for n in objects.children}
    connections = next(n for n in new if n.name == "Connections").children
    result = {}
    for geometry_id, rgba in colors.items():
        parents = [c.props[2] for c in connections if c.name == "C" and c.props[1] == geometry_id]
        require(len(parents) == 1, "Ambiguous geometry/model binding")
        materials = [by_id[c.props[1]] for c in connections if c.name == "C" and c.props[2] == parents[0] and
                     c.props[1] in by_id and by_id[c.props[1]].name == "Material"]
        require(len(materials) == 1, "Qualified geometry must use one source material")
        result.setdefault(named(materials[0]), set()).update(rgba)
    require(set(result) == set(SLOTS) and all(len(v) == 1 for v in result.values()), "Ambiguous source slot colors")
    return result


def geometry_contract(path, *, omit_colors=True, omit_normals=False):
    """同一原生导出器的几何、UV、法线、Skin、BindPose；排除有意变化的颜色。"""
    roots = read_fbx(path)
    objects = next(n for n in roots if n.name == "Objects")
    by_id = {n.props[0]: (n.name, tuple(n.props[1:])) for n in objects.children}
    connections = next(n for n in roots if n.name == "Connections")
    # UE 先把无变换临时父节点写进 BindPose，再从 Scene 移除它；只稳定该导出编号。
    # FbxSkeletalMeshExport.cpp 的 CreateBindPose / TmpNodeNoTransform 路径。
    temporary_parent = None
    for pose in (n for n in objects.children if n.name == "Pose"):
        nodes = [n for n in pose.children if n.name == "PoseNode"]
        unknown = [(i, n, child(n, "Node").props[0]) for i, n in enumerate(nodes)
                   if child(n, "Node").props[0] != 0 and child(n, "Node").props[0] not in by_id]
        if not unknown:
            continue
        identity = [1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1., 0., 0., 0., 0., 1.]
        require(temporary_parent is None and len(unknown) == 1 and unknown[0][0] == 1 and
                child(pose, "Type").props == [b"BindPose"] and len(nodes) > 2 and
                child(nodes[0], "Node").props == [0] and values(nodes[0], "Matrix") == identity and
                values(unknown[0][1], "Matrix") == identity,
                "Unknown native BindPose reference; cannot infer exporter temporary parent")
        temporary_parent = unknown[0][2]
        root = by_id.get(child(nodes[2], "Node").props[0])
        require(isinstance(temporary_parent, int) and temporary_parent > 0 and root and
                root[0] == "Model" and root[1][-1] == b"Root" and
                not any(temporary_parent in n.props for n in connections.children),
                "Unqualified native exporter temporary parent")
    def identities(value):
        if temporary_parent is not None and value == temporary_parent:
            return ("exporter_temporary_bind_parent",)
        if isinstance(value, int) and value in by_id:
            return ("object", by_id[value])
        if isinstance(value, (tuple, list)):
            return tuple(identities(v) for v in value)
        return value
    def fix(payload):
        name, props, kids = payload
        # 数组内整数是索引；不把它们误当 SDK object ID。
        p = [v if isinstance(v, tuple) and v[0] == "array" else identities(v) for v in props]
        return name, p, [fix(k) for k in kids]
    selected = [fix(tree(n, omit_colors=omit_colors, omit_normals=omit_normals)) for n in objects.children
                if n.name in ("Geometry", "Deformer", "Model", "Pose")]
    require(any(n[0] == "Geometry" for n in selected), "Native export has no geometry")
    links = identities(tree(connections))
    return selected, links


def validate_native_colors(path, source_colors, materials):
    """逐原生多边形角点检查其槽的源 RGBA，不以 has_vertex_colors 单独验收。"""
    roots = read_fbx(path)
    objects = next(n for n in roots if n.name == "Objects")
    by_id = {n.props[0]: n for n in objects.children}
    links = next(n for n in roots if n.name == "Connections").children
    expected = {m.material_interface.get_name(): source_colors[str(m.material_slot_name)] for m in materials}
    polygons = 0
    for g in (n for n in objects.children if n.name == "Geometry"):
        model = next(c.props[2] for c in links if c.name == "C" and c.props[1] == g.props[0])
        names = [named(by_id[c.props[1]]) for c in links if c.name == "C" and c.props[2] == model and
                 c.props[1] in by_id and by_id[c.props[1]].name == "Material"]
        color = child(g, "LayerElementColor")
        require(child(color, "MappingInformationType").props == [b"ByVertice"] and
                child(color, "ReferenceInformationType").props == [b"Direct"], "Unexpected native color mapping")
        rgba = values(color, "Colors")
        require(len(rgba) == len(values(g, "Vertices")) // 3 * 4, "Native Color/CP count mismatch")
        indexes = values(g, "PolygonVertexIndex")
        mat_layer = child(g, "LayerElementMaterial")
        require(child(mat_layer, "MappingInformationType").props == [b"ByPolygon"], "Expected polygon materials")
        mats = values(mat_layer, "Materials")
        poly = 0
        for index in indexes:
            cp = -index-1 if index < 0 else index
            require(0 <= cp < len(rgba)//4 and poly < len(mats) and 0 <= mats[poly] < len(names), "Invalid native corner/material")
            name = names[mats[poly]]
            require(name in expected, "Unexpected native material " + name)
            require(tuple(round(c*255) for c in rgba[cp*4:cp*4+4]) in expected[name], "Wrong source RGBA in slot " + name)
            if index < 0:
                poly += 1
                polygons += 1
        require(poly == len(mats), "Native polygon/material counts differ")
    require(polygons == 23408, "Qualified native topology changed")


def dirty(ue):
    return {p.get_path_name() for p in list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()) +
            list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages())}


def native_snapshot(ue, mesh):
    subsys = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem)
    modifier = ue.SkeletonModifier()
    require(modifier.set_skeletal_mesh(mesh), "Cannot read native mesh reference skeleton")
    bones = [(str(n), str(modifier.get_parent_name(n)), modifier.get_bone_transform(n, False).export_text())
             for n in modifier.get_all_bone_names()]
    require(bones, "Empty native reference skeleton")
    sockets = []
    for i in range(mesh.num_sockets()):
        s = mesh.get_socket_by_index(i)
        sockets.append((s.get_path_name(), str(s.socket_name), str(s.bone_name),
                        s.get_socket_local_transform().export_text(), s.force_always_animated))
    slots = list(mesh.get_editor_property("materials"))
    require(tuple(str(m.material_slot_name) for m in slots) == SLOTS, "Original slot identities changed")
    require(all(m.material_interface for m in slots), "Missing original material")
    require(not list(mesh.get_editor_property("mesh_clothing_assets")), "Registered cloth needs a supported reimport contract")
    require(not list(mesh.get_editor_property("morph_targets")), "Existing morphs cannot be silently dropped")
    require(not list(mesh.get_editor_property("skin_weight_profiles")), "Existing skin profiles require explicit protection")
    require(subsys.get_lod_count(mesh) == 1 and subsys.get_num_sections(mesh, 0) == 4, "Unexpected native LOD/sections")
    require(not any(mesh.is_section_using_cloth(i, True) for i in range(4)), "Native section has cloth binding")
    sections = [subsys.get_lod_material_slot(mesh, 0, i) for i in range(4)]
    require(sections == [0, 1, 2, 3], "Original section/slot mapping changed")
    def ref(name):
        obj = mesh.get_editor_property(name)
        return obj.get_path_name() if obj else None
    return dict(bones=bones, sockets=sockets, skeleton=ref("skeleton"), physics=ref("physics_asset"),
                shadow_physics=ref("shadow_physics_asset"), post_process=ref("post_process_anim_blueprint"),
                materials=[m.export_text() for m in slots], section_slots=sections,
                lod_build=subsys.get_lod_build_settings(mesh, 0).export_text(),
                lod_reduction=mesh.get_editor_property("source_models")[0].get_editor_property("reduction_settings").export_text(),
                nanite=mesh.get_editor_property("nanite_settings").export_text())


def assert_preserved(before, after):
    # 机器证据读回只会把 tuple 编码为 list；值和次序仍完整比较。
    before, after = (json.loads(json.dumps(value)) for value in (before, after))
    changes = [k for k in before if before[k] != after.get(k)]
    require(not changes, "Protected native mesh data changed: " + ", ".join(changes))


@contextmanager
def mesh_only_pipeline(ue, data):
    pipelines = list(data.get_pipelines())
    require(len(pipelines) == 1 and isinstance(pipelines[0], ue.InterchangeGenericAssetsPipeline), "Unknown import pipeline")
    p = pipelines[0]
    require(p.get_path_name().startswith("/Engine/Transient."), "Stored pipeline is not the native transient template")
    common = p.get_editor_property("common_meshes_properties")
    skel = p.get_editor_property("common_skeletal_meshes_and_animations_properties")
    mesh = p.get_editor_property("mesh_pipeline")
    material = p.get_editor_property("material_pipeline")
    settings = [(common, "vertex_color_import_option", ue.InterchangeVertexColorImportOption.IVCIO_REPLACE),
                (common, "import_sockets", False), (skel, "add_curve_metadata_to_skeleton", False),
                (mesh, "skeletal_mesh_import_content_type", ue.InterchangeSkeletalMeshContentType.GEOMETRY),
                (mesh, "import_static_meshes", False), (mesh, "import_skeletal_meshes", True),
                (mesh, "update_skeleton_reference_pose", False), (mesh, "create_physics_asset", False),
                (mesh, "import_morph_targets", False), (p.get_editor_property("animation_pipeline"), "import_animations", False),
                (material, "import_materials", False), (material.get_editor_property("texture_pipeline"), "import_textures", False)]
    originals = [(o, n, o.get_editor_property(n)) for o, n, _ in settings]
    try:
        for obj, name, value in settings:
            obj.set_editor_property(name, value)
            require(obj.get_editor_property(name) == value, "Import setting did not apply: " + name)
        yield p
    finally:
        for obj, name, value in reversed(originals):
            obj.set_editor_property(name, value)


def require_import_result(result, mesh):
    # UE Python 将 bool success + OutImportedObjects 映射为 Array[Object] 或 None。
    require(result is not None and not isinstance(result, (bool, str, bytes, dict)), "Native import failed: " + str(result))
    require(list(result) == [mesh], "Native import produced an unexpected asset set")


def package_hashes():
    root = PROJECT / "Content/Characters/Player/Pyrios"
    # FX 由其唯一作者在互斥包中工作，不把它的合法保存算成本网格导入副作用。
    return {str(p.relative_to(root)): sha(p) for p in root.rglob("*") if p.is_file() and
            p.relative_to(root).parts[0] != "FX" and
            p.suffix.lower() in (".uasset", ".uexp", ".ubulk")}


def assert_package_protection(before, after, allow_mesh=False):
    permitted = {MESH_PATH.rsplit("/", 1)[-1] + ext for ext in (".uasset", ".uexp", ".ubulk")} if allow_mesh else set()
    changes = {k for k in set(before) | set(after) if before.get(k) != after.get(k)}
    require(changes <= permitted, "Protected packages changed: " + repr(sorted(changes - permitted)))


def export_lod0(ue, mesh, output):
    require(not output.exists(), "Existing evidence file " + str(output))
    options = ue.FbxExportOption()
    for name, value in dict(fbx_export_compatibility=ue.FbxExportCompatibility.FBX_2013, ascii=False,
                            vertex_color=True, force_front_x_axis=False, level_of_detail=False, collision=False,
                            export_morph_targets=False, export_preview_mesh=False,
                            bake_material_inputs=ue.FbxMaterialBakeMode.DISABLED).items():
        options.set_editor_property(name, value)
    task = ue.AssetExportTask()
    for name, value in dict(object=mesh, exporter=ue.SkeletalMeshExporterFBX(), options=options,
                            filename=str(output), automated=True, prompt=False, selected=False,
                            replace_identical=False, write_empty_files=False).items():
        task.set_editor_property(name, value)
    require(ue.Exporter.run_asset_export_task(task) and not list(task.errors) and output.is_file(), "Native LOD0 export failed")


def run(output, apply=False):
    """预检只读生产包；apply 仅供获得单 Mesh 生产窗口的调用者。"""
    import unreal as ue
    output = Path(output).resolve()
    require((PROJECT / "Saved").resolve() in output.parents and not output.exists(), "Output must be a new directory under Saved")
    require(not ue.EditorLevelLibrary.get_pie_worlds(True) and not dirty(ue), "PIE or unsaved work exists; no import attempted")
    source_colors = qualify_sources()
    mesh = ue.EditorAssetLibrary.load_asset(MESH_PATH)
    require(isinstance(mesh, ue.SkeletalMesh), "Missing formal Pyrios skeletal mesh")
    data = mesh.get_editor_property("asset_import_data")
    require(isinstance(data, ue.InterchangeAssetImportData), "Expected Interchange import data")
    require([Path(str(f)).resolve() for f in data.extract_filenames()] == [ORIGINAL.resolve()], "Unexpected stored source files")
    before = native_snapshot(ue, mesh)
    require(not mesh.has_vertex_colors() and not dirty(ue), "This is not the qualified missing-color baseline")
    hashes = package_hashes()
    output.mkdir(parents=True)
    with (output / "before_protection.json").open("x", encoding="utf-8") as stream:
        json.dump(dict(native=before, package_hashes=hashes, source=str(SOURCE), source_sha256=SOURCE_SHA),
                  stream, ensure_ascii=False, indent=2)
    backup = output / "backup"
    backup.mkdir()
    for relative in hashes:
        if relative in {MESH_PATH.rsplit("/", 1)[-1] + e for e in (".uasset", ".uexp", ".ubulk")}:
            src = PROJECT / "Content/Characters/Player/Pyrios" / relative
            shutil.copyfile(src, backup / src.name)
            require(sha(backup / src.name) == hashes[relative], "Backup mismatch")
    export_lod0(ue, mesh, output / "before.fbx")
    assert_preserved(before, native_snapshot(ue, mesh))
    require(not dirty(ue), "Read-only preflight dirtied packages")
    assert_package_protection(hashes, package_hashes())
    if not apply:
        ue.log("PYRIOS_MESH_REIMPORT_PREFLIGHT_OK " + str(output))
        return before
    old_materials = [m.copy() for m in mesh.get_editor_property("materials")]
    with mesh_only_pipeline(ue, data) as pipeline:
        params = ue.ImportAssetParameters()
        params.set_editor_property("is_automated", True)
        params.set_editor_property("reimport_asset", mesh)
        params.set_editor_property("reimport_source_index", 1)
        params.set_editor_property("override_pipelines", [ue.SoftObjectPath(pipeline.get_path_name())])
        source = ue.InterchangeManager.create_source_data(str(SOURCE))
        manager = ue.InterchangeManager.get_interchange_manager_scripted()
        result = manager.import_asset(MESH_PATH.rsplit("/", 1)[0], source, params)
    require_import_result(result, mesh)
    return finish_import(ue, mesh, output, before, hashes, source_colors, old_materials)


def finish_import(ue, mesh, output, before, hashes, source_colors, old_materials):
    """同步导入成功后的唯一检查／单包提交段；不创建第二条导入链。"""
    slots = list(mesh.get_editor_property("materials"))
    def identity(m):
        return str(m.material_slot_name), str(m.get_editor_property("imported_material_slot_name"))
    require([identity(m) for m in slots] == [identity(m) for m in old_materials], "Reimport changed slot identities")
    # 恢复真实原槽结构及 MI；不再运行材质 builder。
    mesh.set_editor_property("materials", old_materials)
    assert_preserved(before, native_snapshot(ue, mesh))
    require(mesh.has_vertex_colors(), "Native render color stream is still absent")
    updated = mesh.get_editor_property("asset_import_data")
    require([Path(str(f)).resolve() for f in updated.extract_filenames()] ==
            [ORIGINAL.resolve(), SOURCE.resolve(), ORIGINAL.resolve()], "Unexpected All/Geometry/Skin source metadata")
    factory = updated.get_stored_factory_node(updated.get_editor_property("node_unique_id"))
    require(factory.get_custom_import_content_type() == ue.InterchangeSkeletalMeshContentType.GEOMETRY,
            "Native factory did not apply Geometry-only contract")
    export_lod0(ue, mesh, output / "after.fbx")
    require(geometry_contract(output / "before.fbx") == geometry_contract(output / "after.fbx"), "Native geometry/UV/normal/skin/bind data changed")
    validate_native_colors(output / "after.fbx", source_colors, old_materials)
    require(dirty(ue) == {MESH_PATH}, "Unexpected dirty packages after reimport: " + repr(sorted(dirty(ue))))
    assert_package_protection(hashes, package_hashes())
    require(ue.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=True), "Single mesh save failed")
    require(not dirty(ue) and mesh.has_vertex_colors(), "Saved mesh readback failed")
    assert_preserved(before, native_snapshot(ue, mesh))
    assert_package_protection(hashes, package_hashes(), allow_mesh=True)
    require(sha(ORIGINAL) == ORIGINAL_SHA and sha(SOURCE) == SOURCE_SHA, "Source files changed during import")
    with (output / "saved_readback.json").open("x", encoding="utf-8") as stream:
        json.dump(dict(native=native_snapshot(ue, mesh), package_hashes=package_hashes(),
                       has_vertex_colors=mesh.has_vertex_colors(),
                       source_files=list(updated.extract_filenames()),
                       scope="same native Editor readback; visual and independent cold load pending"),
                  stream, ensure_ascii=False, indent=2)
    ue.log("PYRIOS_MESH_REIMPORT_SAVED_NATIVE_CONTRACT_OK " + str(output))
    return before


def finish_current_import(output, expected_editor_pid):
    """仅续接本次已同步成功、getter 异常返栈的原宿主现场；不再次导入。

    原 before 证据、逐包备份、真实当前内存和源身份是提交依据；任一不符保留现场。
    """
    import unreal as ue
    output = Path(output).resolve()
    require(os.getpid() == expected_editor_pid and expected_editor_pid == 39372,
            "This is not the qualified in-memory Editor")
    require(output == PROJECT / "Saved/Codex/PyriosMeshReimport_20261010_R1" and
            not (output / "after.fbx").exists() and not (output / "saved_readback.json").exists(),
            "This is not the interrupted post-import evidence")
    protection = json.loads((output / "before_protection.json").read_text(encoding="utf-8"))
    require(protection["source"] == str(SOURCE) and protection["source_sha256"] == SOURCE_SHA,
            "Interrupted import source identity differs")
    hashes = protection["package_hashes"]
    filename = MESH_PATH.rsplit("/", 1)[-1] + ".uasset"
    require(hashes[filename] == "8ad7e0672caffea242fc693596ee496af8613c05419bc02be91aa22f92c52bc4" and
            sha(output / "backup" / filename) == hashes[filename], "Interrupted import baseline/backup differs")
    require(not ue.EditorLevelLibrary.get_pie_worlds(True) and dirty(ue) == {MESH_PATH},
            "Interrupted import no longer owns the sole dirty mesh")
    assert_package_protection(hashes, package_hashes())
    source_colors = qualify_sources()
    mesh = ue.EditorAssetLibrary.load_asset(MESH_PATH)
    require(isinstance(mesh, ue.SkeletalMesh) and mesh.has_vertex_colors(), "Interrupted native result is unavailable")
    assert_preserved(protection["native"], native_snapshot(ue, mesh))
    require(geometry_contract(output / "before.fbx") == geometry_contract(output / "after_import_failure.fbx"),
            "Interrupted native geometry/UV/normal/skin/bind evidence changed")
    old_materials = []
    for text in protection["native"]["materials"]:
        material = ue.SkeletalMaterial()
        require(material.import_text(text) and material.export_text() == text, "Cannot restore complete typed original slot")
        old_materials.append(material)
    validate_native_colors(output / "after_import_failure.fbx", source_colors, old_materials)
    return finish_import(ue, mesh, output, protection["native"], hashes, source_colors, old_materials)


NORMALS_ADMISSION_SHA = "d6360f9741cbd1c1754dd814be8a1b58ab347e9ef98ee4364788c0998cfbeb34"


def read_source_normals(ue, mesh):
    """从原生 SourceModel 读取逐角点法线；不应用构建设置、不请求切线。"""
    dynamic = ue.DynamicMesh()
    options = ue.GeometryScriptCopyMeshFromAssetOptions(
        apply_build_settings=False, request_tangents=False, use_build_scale=False)
    lod = ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.SOURCE_MODEL, lod_index=0)
    result = ue.GeometryScript_AssetUtils.copy_mesh_from_skeletal_mesh(mesh, dynamic, options, lod)
    require(result == (dynamic, ue.GeometryScriptOutcomePins.SUCCESS), "Native source mesh copy failed")
    query = ue.GeometryScript_MeshQueries
    require(not query.get_has_triangle_id_gaps(dynamic) and query.get_has_triangle_normals(dynamic),
            "Native source mesh has incomplete topology/normals")
    rows = []
    for tid in range(dynamic.get_triangle_count()):
        valid, *positions = query.get_triangle_positions(dynamic, tid)
        copied, n1, n2, n3, has_normals = query.get_triangle_normals(dynamic, tid)
        require(valid and copied == dynamic and has_normals, "Missing native source normals: " + str(tid))
        ps = [[v.x, v.y, v.z] for v in positions]
        ns = [[v.x, v.y, v.z] for v in (n1, n2, n3)]
        require(all(math.isfinite(x) for v in ps + ns for x in v) and
                all(sum(x*x for x in v) > 1e-12 for v in ns), "Invalid native source normal: " + str(tid))
        uvs = []
        for channel in range(3):
            u1, u2, u3, has_uv = query.get_triangle_u_vs(dynamic, channel, tid)
            require(has_uv, "Missing native UV channel: " + str((tid, channel)))
            uv = [[v.x, v.y] for v in (u1, u2, u3)]
            require(all(math.isfinite(x) for v in uv for x in v), "Nonfinite native UV")
            uvs.append(uv)
        rows.append([ps, ns, uvs])
    return rows


def source_normal_candidates():
    """读取已核身份的原 FBX；使用其 Mesh 节点旋转及 YUp→UE 转换。"""
    require(sha(ORIGINAL) == ORIGINAL_SHA, "Original normal source identity changed")
    roots = read_fbx(ORIGINAL)
    objects = next(n for n in roots if n.name == "Objects")
    by_id = {n.props[0]: n for n in objects.children}
    links = next(n for n in roots if n.name == "Connections").children
    candidates, triangle_count = {}, 0
    for g in (n for n in objects.children if n.name == "Geometry"):
        models = [by_id[c.props[2]] for c in links if c.name == "C" and c.props[1] == g.props[0]
                  and c.props[2] in by_id and by_id[c.props[2]].name == "Model"]
        require(len(models) == 1, "Ambiguous original geometry model")
        properties = child(models[0], "Properties70").children
        rotations = [p.props[4:] for p in properties if p.props[0] == b"Lcl Rotation"]
        rotation = rotations[0] if rotations else [0, 0, 0]
        # 源文件身份锁定了 YUp/cm、无平移缩放及这个只绕 X 的节点层级。
        require(len(rotations) <= 1 and rotation[0] in (-90, 0) and rotation[1:] == [0, 0],
                "Unqualified original geometry transform")
        radians = math.radians(90 + rotation[0])
        co, si = math.cos(radians), math.sin(radians)
        def convert(v):
            return (v[0], -co*v[1] + si*v[2], si*v[1] + co*v[2])
        normal = child(g, "LayerElementNormal")
        require(child(normal, "MappingInformationType").props == [b"ByVertice"] and
                child(normal, "ReferenceInformationType").props == [b"Direct"], "Invalid original normal mapping")
        vertices, normals = values(g, "Vertices"), values(normal, "Normals")
        uv_layers = [n for n in g.children if n.name == "LayerElementUV"]
        require([n.props for n in uv_layers] in ([[0], [1]], [[0], [1], [2]]), "Unexpected original UV layers")
        uv = [values(n, "UV") for n in uv_layers]
        require(len(vertices) > 0 and len(vertices) % 3 == 0 and len(normals) == len(vertices) and
                all(len(a) == len(vertices)//3*2 for a in uv), "Incomplete original normal/UV stream")
        require(all(math.isfinite(v) for a in [vertices, normals] + uv for v in a), "Nonfinite original stream")
        for i in range(len(vertices)//3):
            p, n = convert(vertices[i*3:i*3+3]), convert(normals[i*3:i*3+3])
            require(sum(v*v for v in n) > 1e-12, "Zero original normal")
            u = tuple(v for a in uv for v in (a[i*2], 1-a[i*2+1]))
            candidates.setdefault(tuple(round(v, 3) for v in p), []).append((p, n, u))
        indices = values(g, "PolygonVertexIndex")
        require(len(indices) % 3 == 0 and all(v < 0 for v in indices[2::3]), "Original topology is not triangles")
        triangle_count += len(indices)//3
    require(triangle_count == 23408, "Original qualified triangle count changed")
    return candidates, triangle_count


def validate_source_normals(rows, candidates, triangle_count):
    """每个原生角点须有同位置、有效 UV 和原法线；不接受 RenderData 回落的重算法线。"""
    require(len(rows) == triangle_count, "Native source triangle count differs")
    max_angle = 0.0
    for tid, (ps, ns, uvs) in enumerate(rows):
        require(len(ps) == len(ns) == 3 and len(uvs) == 3 and
                all(len(v) == 3 for v in ps + ns) and
                all(len(layer) == 3 and all(len(v) == 2 for v in layer) for layer in uvs),
                "Incomplete source triangle corner streams: " + str(tid))
        for corner, (p, n) in enumerate(zip(ps, ns)):
            uv = tuple(v for layer in uvs for v in layer[corner])
            require(all(math.isfinite(v) for v in tuple(p) + tuple(n) + uv) and
                    sum(v*v for v in n) > 1e-12, "Invalid source corner: " + str((tid, corner)))
            hits = [(pn, nn) for pn, nn, un in candidates.get(tuple(round(v, 3) for v in p), [])
                    if max(abs(a-b) for a, b in zip(p, pn)) <= 1e-4 and
                    max(abs(a-b) for a, b in zip(uv[:len(un)], un)) <= 2e-6]
            require(hits, "Source position/UV does not match original: " + str((tid, corner)))
            length = math.sqrt(sum(v*v for v in n))
            angle = min(math.degrees(math.acos(max(-1.0, min(1.0,
                        sum(a*b for a, b in zip(n, nn))/length/math.sqrt(sum(v*v for v in nn))))))
                        for _, nn in hits)
            require(angle <= 0.01, "Native source normal differs from original: " + str((tid, corner, angle)))
            max_angle = max(max_angle, angle)
    return dict(triangles=triangle_count, corners=triangle_count*3, max_angle_degrees=max_angle)


def exported_normal_rows(path):
    """原生 LOD 导出的 SoftVertices.TangentZ；用于验证实际构建输出。"""
    objects = next(n for n in read_fbx(path) if n.name == "Objects")
    geometries = [n for n in objects.children if n.name == "Geometry"]
    require(len(geometries) == 1, "Expected one native merged LOD geometry")
    g = geometries[0]
    vertices = values(g, "Vertices")
    normal = child(g, "LayerElementNormal")
    require(child(normal, "MappingInformationType").props == [b"ByVertice"] and
            child(normal, "ReferenceInformationType").props == [b"Direct"], "Invalid built normal mapping")
    normals = values(normal, "Normals")
    uv_layers = [n for n in g.children if n.name == "LayerElementUV"]
    require([n.props for n in uv_layers] == [[0], [1], [2]], "Built UV layout changed")
    uv = [values(n, "UV") for n in uv_layers]
    require(len(normals) == len(vertices) and all(len(a) == len(vertices)//3*2 for a in uv),
            "Built normal/UV stream is incomplete")
    indices = values(g, "PolygonVertexIndex")
    require(len(indices) % 3 == 0 and all(v < 0 for v in indices[2::3]), "Built topology is not triangles")
    def vector(data, i):
        x, y, z = data[i*3:i*3+3]
        return [x, -y, z]
    rows = []
    for start in range(0, len(indices), 3):
        ids = [v if v >= 0 else -v-1 for v in indices[start:start+3]]
        rows.append([[vector(vertices, i) for i in ids], [vector(normals, i) for i in ids],
                     [[[a[i*2], 1-a[i*2+1]] for i in ids] for a in uv]])
    return rows


def finish_normal_build(ue, mesh, output, expected, hashes, source_rows, source_files):
    """检查原生构建结果后只保存这一 Mesh；失败保留内存和证据。"""
    assert_preserved(expected, native_snapshot(ue, mesh))
    require(mesh.has_vertex_colors(), "Native color stream lost during normal build")
    require(read_source_normals(ue, mesh) == source_rows, "Source geometry/normal/UV data changed during build")
    require(list(mesh.get_editor_property("asset_import_data").extract_filenames()) == source_files,
            "Normal build changed import sources")
    export_lod0(ue, mesh, output / "after.fbx")
    candidates, count = source_normal_candidates()
    built_proof = validate_source_normals(exported_normal_rows(output / "after.fbx"), candidates, count)
    require(geometry_contract(output / "before.fbx", omit_colors=False, omit_normals=True) ==
            geometry_contract(output / "after.fbx", omit_colors=False, omit_normals=True),
            "Normal build changed protected native geometry/UV/color/skin/bind data")
    require(dirty(ue) == {MESH_PATH}, "Normal build has unexpected dirty packages")
    assert_package_protection(hashes, package_hashes())
    require(sha(ORIGINAL) == ORIGINAL_SHA and sha(SOURCE) == SOURCE_SHA, "Normal build changed source files")
    require(ue.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=True), "Single normal mesh save failed")
    require(not dirty(ue), "Normal mesh save left dirty packages")
    assert_preserved(expected, native_snapshot(ue, mesh))
    assert_package_protection(hashes, package_hashes(), allow_mesh=True)
    with (output / "saved_normals_readback.json").open("x", encoding="utf-8") as stream:
        json.dump(dict(editor_pid=os.getpid(), native=native_snapshot(ue, mesh),
                       package_hashes=package_hashes(), source_files=source_files,
                       built_normal_proof=built_proof,
                       has_vertex_colors=mesh.has_vertex_colors(), dirty=sorted(dirty(ue)),
                       scope="same Editor; actual pictures and independent cold load pending"),
                  stream, ensure_ascii=False, indent=2)
    ue.log("PYRIOS_SOURCE_NORMALS_SAVED_OK")


def preserve_source_normals(output, expected_editor_pid):
    """消费同宿主源法线读回，只关闭 LOD0 法线重算；不重导和不改切线配置。"""
    import unreal as ue
    output = Path(output).resolve()
    require((PROJECT / "Saved").resolve() in output.parents, "Normal evidence must be under Saved")
    baseline = json.loads((output / "NativeSourceReadback.json").read_text(encoding="utf-8"))
    require(os.getpid() == expected_editor_pid == baseline["editor_pid"], "Normal source Editor identity differs")
    require(not list(ue.EditorLevelLibrary.get_pie_worlds(True)) and not dirty(ue), "PIE or unsaved work exists")
    hashes = baseline["package_hashes"]
    filename = MESH_PATH.rsplit("/", 1)[-1] + ".uasset"
    require(hashes[filename] == NORMALS_ADMISSION_SHA and package_hashes() == hashes, "Normal mesh admission changed")
    require(not (output / "backup").exists() and not (output / "saved_normals_readback.json").exists(),
            "Refusing repeated normal migration")
    mesh = ue.EditorAssetLibrary.load_asset(MESH_PATH)
    require(isinstance(mesh, ue.SkeletalMesh) and mesh.has_vertex_colors(), "Qualified mesh is unavailable")
    assert_preserved(baseline["native"], native_snapshot(ue, mesh))
    source_rows = read_source_normals(ue, mesh)
    require(source_rows == baseline["source_triangles"], "Native source changed since readback")
    candidates, count = source_normal_candidates()
    proof = validate_source_normals(source_rows, candidates, count)
    subsystem = ue.get_editor_subsystem(ue.SkeletalMeshEditorSubsystem)
    settings = subsystem.get_lod_build_settings(mesh, 0)
    require(settings.recompute_normals and settings.recompute_tangents, "Expected explicit normal/tangent build changed")
    changed = settings.copy()
    changed.set_editor_property("recompute_normals", False)
    expected = dict(baseline["native"], lod_build=changed.export_text())
    source_files = list(mesh.get_editor_property("asset_import_data").extract_filenames())
    backup = output / "backup"
    backup.mkdir()
    for relative, digest in hashes.items():
        if Path(relative).name == relative and Path(relative).stem == Path(filename).stem:
            path = PROJECT / "Content/Characters/Player/Pyrios" / relative
            shutil.copyfile(path, backup / path.name)
            require(sha(backup / path.name) == digest, "Normal mesh backup mismatch")
    with (output / "normal_protection.json").open("x", encoding="utf-8") as stream:
        json.dump(dict(editor_pid=os.getpid(), native=baseline["native"], expected_native=expected,
                       package_hashes=hashes, source_files=source_files, source_normal_proof=proof),
                  stream, ensure_ascii=False, indent=2)
    export_lod0(ue, mesh, output / "before.fbx")
    require(not dirty(ue) and package_hashes() == hashes, "Normal preflight changed packages")
    subsystem.set_lod_build_settings(mesh, 0, changed)
    finish_normal_build(ue, mesh, output, expected, hashes, source_rows, source_files)


if __name__ == "__main__":
    run(os.environ["PYRIOS_MESH_REIMPORT_OUTPUT"], apply=os.environ.get("PYRIOS_MESH_REIMPORT_APPLY") == "1")
