"""Export the current Pyrios imported LOD0/reference pose, without saving assets.

Run in a separate full RHI UnrealEditor.exe with -ExecutePythonScript=<this file>
and PYRIOS_BODY_FBX set to a new .fbx filename under project Saved. The stock
SkeletalMeshExporterFBX requires rendering resources even when material baking
is disabled; use this validated full Editor/RHI host. Binary FBX 2013 lets the
existing fbx_bin_reader consume its records.
The output is imported-model evidence, not a GPU pose or Opacity verification.
"""
import json
import os
from pathlib import Path
import struct
import unreal


MESH = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model.Avatar_Male_Size03_Pyrois_Model"
SLOTS = ("MAT_Pyrois_Body_1", "MAT_Pyrois_Body_2", "MAT_Pyrois_Body_FX01", "MAT_Pyrois_Weapon01")


def emit(stage, **values):
    unreal.log("PYRIOS_BODY_MESH_EXPORT " + json.dumps(dict(stage=stage, **values), ensure_ascii=False))


def dirty_packages():
    packages = list(unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    packages += list(unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages())
    return tuple(sorted(p.get_path_name() for p in packages))


def snapshot(mesh, subsystem):
    skeleton = mesh.get_editor_property("skeleton")
    if skeleton is None:
        raise RuntimeError("Current Pyrios mesh has no Skeleton")
    materials = mesh.get_editor_property("materials")
    if tuple(str(m.material_slot_name) for m in materials) != SLOTS:
        raise RuntimeError("Current Pyrios material slot identities differ from the qualified four slots")
    if any(m.material_interface is None for m in materials):
        raise RuntimeError("Current Pyrios material slot has no actual material")
    lod_count = subsystem.get_lod_count(mesh)
    if lod_count < 1:
        raise RuntimeError("Current Pyrios mesh has no valid LOD")
    count = subsystem.get_num_sections(mesh, 0)
    if count != 4:
        raise RuntimeError("Current Pyrios LOD0 must have the four qualified native sections")
    ids = tuple(subsystem.get_lod_material_slot(mesh, 0, i) for i in range(count))
    if ids != (0, 1, 2, 3):
        raise RuntimeError("Current Pyrios LOD0 Section/material mapping changed: " + repr(ids))
    clothing = tuple(mesh.get_editor_property("mesh_clothing_assets"))
    if any(asset is None for asset in clothing):
        raise RuntimeError("Current Pyrios registered clothing asset reference is invalid")
    return dict(asset=mesh.get_path_name(), skeleton=skeleton.get_path_name(), lod_count=lod_count,
                lod0_sections=ids, registered_clothing_assets=[a.get_path_name() for a in clothing],
                slots=[dict(index=i, slot=str(m.material_slot_name), material=m.material_interface.get_path_name())
                       for i, m in enumerate(materials)])


def main():
    saved = Path(unreal.Paths.project_saved_dir()).resolve()
    output = Path(os.environ["PYRIOS_BODY_FBX"]).resolve()
    if saved not in output.parents or output.suffix.lower() != ".fbx":
        raise RuntimeError("PYRIOS_BODY_FBX must be a .fbx filename under project Saved")
    if output.exists():
        raise RuntimeError("Refusing to replace an existing FBX: " + str(output))
    if unreal.EditorLevelLibrary.get_pie_worlds(True):
        raise RuntimeError("Refusing mesh export while PIE is active")
    original_dirty = dirty_packages()
    if original_dirty:
        raise RuntimeError("Refusing mesh export with dirty packages: " + repr(original_dirty))
    mesh = unreal.EditorAssetLibrary.load_asset(MESH)
    if not isinstance(mesh, unreal.SkeletalMesh) or mesh.get_path_name() != MESH:
        raise RuntimeError("Current formal Pyrios skeletal mesh is missing")
    subsystem = unreal.get_editor_subsystem(unreal.SkeletalMeshEditorSubsystem)
    if subsystem is None:
        raise RuntimeError("Native SkeletalMeshEditorSubsystem is unavailable")
    before = snapshot(mesh, subsystem)
    if dirty_packages() != original_dirty:
        raise RuntimeError("Loading the source mesh changed dirty packages; no export attempted")
    options = unreal.FbxExportOption()
    settings = dict(fbx_export_compatibility=unreal.FbxExportCompatibility.FBX_2013,
                    ascii=False, force_front_x_axis=False, level_of_detail=False,
                    vertex_color=True, collision=False, export_morph_targets=False,
                    export_preview_mesh=False, bake_material_inputs=unreal.FbxMaterialBakeMode.DISABLED)
    for name, value in settings.items():
        options.set_editor_property(name, value)
        if options.get_editor_property(name) != value:
            raise RuntimeError("Native FBX export option did not apply: " + name)
    task = unreal.AssetExportTask()
    for name, value in dict(object=mesh, exporter=unreal.SkeletalMeshExporterFBX(), options=options,
                            filename=str(output), automated=True, prompt=False, selected=False,
                            replace_identical=False, write_empty_files=False, use_file_archive=False).items():
        task.set_editor_property(name, value)
    emit("source_qualified", **before, file=str(output),
         representation="native non-clothing imported LOD0/reference pose; UV layers and skin weights",
         options="binary FBX2013; LOD0 only; no morph/animation/collision/material baking",
         limits="use polygon material indices; exporter skips HasClothingData sections; registered cloth is not per-section binding")
    output.parent.mkdir(parents=True, exist_ok=True)
    try:
        ok = unreal.Exporter.run_asset_export_task(task)
        errors = list(task.get_editor_property("errors"))
        if not ok or errors or not output.is_file():
            raise RuntimeError("Native skeletal FBX export failed: " + repr(errors))
        with output.open("rb") as stream:
            header = stream.read(27)
        if len(header) != 27 or header[:23] != b"Kaydara FBX Binary  \x00\x1a\x00":
            raise RuntimeError("Native output is not a binary FBX; preserve it for failure review")
        version = struct.unpack("<I", header[23:27])[0]
        if version != 7300:
            raise RuntimeError("Native output does not match requested FBX2013: " + str(version))
    finally:
        if snapshot(mesh, subsystem) != before or dirty_packages() != original_dirty:
            raise RuntimeError("Native export changed source bindings/dirty packages; do not save the assets")
        if unreal.EditorLevelLibrary.get_pie_worlds(True):
            raise RuntimeError("PIE appeared during mesh export; no capture or PIE cleanup is owned here")
    emit("exported_pending_geometry_comparison", file=str(output), bytes=output.stat().st_size,
         fbx_version=version, original_bindings_unchanged=True, packages_clean=True,
         limits="counts alone do not prove topology/UV/bone weights match; not GPU pose or Opacity evidence")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        unreal.log_error("PYRIOS_BODY_MESH_EXPORT failed: " + str(exc))
        raise
