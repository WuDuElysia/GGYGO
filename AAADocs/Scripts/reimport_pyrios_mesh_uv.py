"""Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>.

用带 UV1/UV2 的 FBX 重新导入 Pyrios 骨骼网格，其余导入设置沿用资产里保存的 Interchange 导入数据。
- UV1：描边 Pass 用的切线空间平滑法线（xy，z 由 1-x²-y² 求出）；
- UV2：表面 Pass 的屏幕贴图遮罩、特殊武器自发光、二次自发光用的 UV（材质里叫 "Use UV2"）。
早期导出只写了 UV0（AnimeStudio CLI 的 uvs 设置里 UV2 关闭），胸口、右臂的蓝光因此没有 UV 可用。

FBX 源：F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model/Avatar_Male_Size03_Pyrois_Model.fbx
（已用带 UV 的导出覆盖，原只含 UV0 的文件保留为 .uv0only.bak）。
重导会重置材质槽的默认材质，之后需重跑 build_pyrios_materials.py 与 build_pyrios_body_fx.py。
"""
import unreal

MESH_PATH = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"
FBX = "F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model/Avatar_Male_Size03_Pyrois_Model.fbx"


def main():
    eal = unreal.EditorAssetLibrary
    mesh = eal.load_asset(MESH_PATH)
    if not isinstance(mesh, unreal.SkeletalMesh):
        raise RuntimeError("Missing mesh " + MESH_PATH)
    dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if MESH_PATH in dirty:
        raise RuntimeError("Mesh has unsaved edits")
    skeleton = mesh.get_editor_property("skeleton")
    slots_before = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("materials")]
    data = mesh.get_editor_property("asset_import_data")
    files = [f.replace("\\", "/").lower() for f in data.extract_filenames()]
    if FBX.lower() not in files:
        raise RuntimeError("Mesh source differs from expected FBX: " + str(files))
    # 网格由 Interchange 导入；ReimportAsset 沿用资产里保存的导入管线与设置，只重新读取源文件。
    params = unreal.ImportAssetParameters()
    params.set_editor_property("is_automated", True)
    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    result = manager.reimport_asset(mesh, params)
    ok = result[0] if isinstance(result, tuple) else result
    if not ok:
        raise RuntimeError("Interchange reimport failed")
    mesh = eal.load_asset(MESH_PATH)
    slots_after = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("materials")]
    if slots_after != slots_before:
        raise RuntimeError("Material slots changed: %s -> %s" % (slots_before, slots_after))
    if mesh.get_editor_property("skeleton") != skeleton:
        raise RuntimeError("Skeleton changed")
    if not eal.save_loaded_asset(mesh, only_if_is_dirty=False):
        raise RuntimeError("Save failed")
    unreal.log("PYRIOS_REIMPORT_OK slots=%s" % slots_after)


if __name__ == "__main__":
    main()
