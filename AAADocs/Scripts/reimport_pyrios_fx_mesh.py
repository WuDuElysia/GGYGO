"""按源角点核对并原位修复 Pyrios FX StaticMesh。

沿用已验证的 SourceCorners FBX／FbxFactory 路径。GGYGO_FX_MESH_PLAN 指向
脚本实际消费的清单：output、apply、items（mesh 与 source_json）。apply=false 只读。
只对位置、UV0 和 alpha 的共同来源失配执行重导入；不改 Niagara 或材质引用。
"""
import json
import math
import os
import shutil
import sys
from itertools import product
from pathlib import Path

import unreal as ue

sys.path.insert(0, str(Path(__file__).parent))
from zzz_mesh_fbx import build


def dirty():
    lib = ue.EditorLoadingAndSavingUtils
    return sorted(p.get_name() for p in list(lib.get_dirty_content_packages()) + list(lib.get_dirty_map_packages()))


def check(mesh, source):
    """同一源顶点须同时匹配位置、UV0 和 alpha，允许原生浮点及颜色量化。"""
    vertices, uvs, colors = source["m_Vertices"], source.get("m_UV0"), source.get("m_Colors")
    count = source["m_VertexCount"]
    width = len(vertices) // count
    uv_width = len(uvs) // count if uvs else 0
    positions, cells = [], {}
    for i in range(count):
        p = (-vertices[width*i]*100, vertices[width*i+2]*100, vertices[width*i+1]*100)
        positions.append(p)
        cells.setdefault(tuple(math.floor(v / 0.05) for v in p), []).append(i)
    dyn = ue.DynamicMesh()
    options = ue.GeometryScriptCopyMeshFromAssetOptions(apply_build_settings=False,
                                                        request_tangents=False, use_build_scale=True)
    ue.GeometryScript_AssetUtils.copy_mesh_from_static_mesh(mesh, dyn, options,
        ue.GeometryScriptMeshReadLOD(lod_type=ue.GeometryScriptLODType.SOURCE_MODEL, lod_index=0))
    query = ue.GeometryScript_MeshQueries
    has_colors = query.get_has_vertex_colors(dyn)
    result = dict(corners=0, position_mismatch=0, uv_mismatch=0, alpha_mismatch=0, joint_mismatch=0)
    for triangle in range(dyn.get_triangle_count()):
        _, *ps = query.get_triangle_positions(dyn, triangle)
        *us, valid_uv = query.get_triangle_u_vs(dyn, 0, triangle)
        cs = query.get_triangle_vertex_colors(dyn, triangle)
        if uvs and not valid_uv:
            raise RuntimeError("导入网格缺少源 UV0")
        for j, vertex in enumerate(ps):
            result["corners"] += 1
            p = (vertex.x, vertex.y, vertex.z)
            cell = tuple(math.floor(v / 0.05) for v in p)
            candidates = [i for offset in product((-1, 0, 1), repeat=3)
                          for i in cells.get(tuple(c+d for c,d in zip(cell, offset)), [])
                          if all(abs(a-b) <= 0.01 for a,b in zip(p, positions[i]))]
            if not candidates:
                result["position_mismatch"] += 1
                result["joint_mismatch"] += 1
                continue
            uv = us[j]
            good_uv = [i for i in candidates if not uvs or
                       (abs(uv.x-uvs[uv_width*i]) < 0.002 and abs(uv.y-(1-uvs[uv_width*i+1])) < 0.002)]
            good_alpha = [i for i in candidates if not colors or
                          (has_colors and abs(cs[1+j].a-colors[4*i+3]) <= 1/255 + 1e-5)]
            result["uv_mismatch"] += not good_uv
            result["alpha_mismatch"] += not good_alpha
            result["joint_mismatch"] += not (set(good_uv) & set(good_alpha))
    if result["corners"] != len(source["m_Indices"]):
        raise RuntimeError("源与 UE 三角角点数不同：" + str(result["corners"]))
    return result


def state(mesh):
    bounds = mesh.get_bounds()
    return dict(path=mesh.get_path_name(), triangles=mesh.get_num_triangles(0), sections=mesh.get_num_sections(0),
                materials=[(str(m.material_slot_name), m.material_interface.get_path_name() if m.material_interface else None)
                           for m in mesh.get_editor_property("static_materials")],
                bounds=[bounds.origin.x, bounds.origin.y, bounds.origin.z,
                        bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z])


def repair(item, out, apply):
    package = item["mesh"]
    if not package.startswith("/Game/Characters/Shared/FX/ZZZ/Meshes/"):
        raise ValueError("清单包含范围外网格：" + package)
    source = json.loads(Path(item["source_json"]).read_text(encoding="utf-8-sig"))
    mesh = ue.load_asset(package)
    row = {"mesh": package, "source_json": item["source_json"], "before": check(mesh, source), "saved": False}
    ue.log("[FXMesh] " + package + " " + str(row["before"]))
    if not apply or not row["before"]["joint_mismatch"]:
        return row
    original = state(mesh)
    materials = mesh.get_editor_property("static_materials")
    fbx = out / (mesh.get_name() + "_SourceCorners.fbx")
    fbx.write_text(build(source, reverse_winding=True), encoding="utf-8")
    package_file = Path(ue.Paths.project_content_dir()) / (package[len("/Game/"):] + ".uasset")
    backup = out / "Backup"
    backup.mkdir(exist_ok=True)
    for suffix in (".uasset", ".uexp", ".ubulk"):
        filename = package_file.with_suffix(suffix)
        if filename.exists():
            destination = backup / filename.name
            if destination.exists():
                raise RuntimeError("拒绝覆盖已有修复备份：" + str(destination))
            shutil.copy2(filename, destination)
    options = ue.FbxImportUI()
    for k, v in dict(import_mesh=True, import_materials=False, import_textures=False, import_animations=False,
                     import_as_skeletal=False, override_full_name=True,
                     mesh_type_to_import=ue.FBXImportType.FBXIT_STATIC_MESH,
                     original_import_type=ue.FBXImportType.FBXIT_STATIC_MESH).items():
        options.set_editor_property(k, v)
    static = options.get_editor_property("static_mesh_import_data")
    for k, v in dict(vertex_color_import_option=ue.VertexColorImportOption.REPLACE,
                     normal_import_method=ue.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
                     combine_meshes=True, generate_lightmap_u_vs=False, convert_scene=True, force_front_x_axis=False,
                     convert_scene_unit=False, transform_vertex_to_absolute=True, bake_pivot_in_vertex=False,
                     import_uniform_scale=1.0).items():
        static.set_editor_property(k, v)
    task = ue.AssetImportTask()
    task.filename = str(fbx)
    task.destination_path, task.destination_name = package.rsplit("/", 1)
    task.automated, task.save = True, False
    task.replace_existing, task.replace_existing_settings = True, False
    task.options, task.factory = options, ue.FbxFactory()
    ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    mesh = ue.load_asset(package)
    mesh.set_editor_property("static_materials", materials)
    after = state(mesh)
    row["after"] = check(mesh, source)
    if any(original[k] != after[k] for k in ("path", "triangles", "sections", "materials")):
        raise RuntimeError("重导入改变了对象、拓扑或材质槽：" + package)
    if any(abs(a-b) >= 0.05 for a,b in zip(original["bounds"], after["bounds"])):
        raise RuntimeError("重导入改变了网格边界：" + package)
    if row["after"]["joint_mismatch"] or dirty() != [package]:
        raise RuntimeError("角点仍不一致或出现其它脏包：" + str(row) + str(dirty()))
    row["saved"] = bool(ue.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False))
    if not row["saved"]:
        raise RuntimeError("目标网格保存失败：" + package)
    ue.log("[FXMesh] 已修复 " + package + " " + str(row["after"]))
    return row


def main():
    plan = json.loads(Path(os.environ["GGYGO_FX_MESH_PLAN"]).read_text(encoding="utf-8"))
    out = Path(plan["output"])
    out.mkdir(parents=True, exist_ok=True)
    if dirty() or ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world():
        raise RuntimeError("修复需无脏包且无 PIE 的独立 Editor")
    rows = []
    try:
        for item in plan["items"]:
            rows.append(repair(item, out, plan["apply"]))
    finally:
        (out / "mesh_checks.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
