"""Plan and import immutable versions of FX textures/meshes into an exact batch.

The default command is offline. All inputs/settings/collisions and ALL destination
packages are checked before mutation. Existing packages and source export maps are
never changed. Returned maps are machine data; callers choose their output file.
"""
import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from zzz_fx_asset_session import AssetSession, version_name

SHARED = "/Game/Characters/Shared/FX/ZZZ"
TEX_DIR, MESH_DIR = SHARED + "/Textures", SHARED + "/Meshes"
ASSET = "editor_toolset.toolsets.asset.AssetTools."
OBJ = "editor_toolset.toolsets.object.ObjectTools."
WRAP = {0: "TA_Wrap", 1: "TA_Clamp", 2: "TA_Mirror"}
FILTER = {0: "TF_Nearest", 1: "TF_Bilinear", 2: "TF_Trilinear"}
MESH_IMPORT_SETTINGS = {
    "vertex_color_import_option": "REPLACE", "normal_import_method": "FBXNIM_IMPORT_NORMALS",
    "combine_meshes": True, "generate_lightmap_u_vs": False,
    "convert_scene": True, "force_front_x_axis": False, "convert_scene_unit": False,
    "transform_vertex_to_absolute": True, "bake_pivot_in_vertex": False,
    "import_uniform_scale": 1.0,
}


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def ref(path):
    return {"refPath": "%s.%s" % (path, path.rsplit("/", 1)[1])}


def source_file(entry, extension):
    files = [Path(f) for f in entry["files"] if f.lower().endswith(extension)]
    if len(files) != 1 or not files[0].is_file():
        raise ValueError("Expected one existing %s for %s" % (extension, entry["name"]))
    return files[0]


def texture_properties(settings):
    ts = settings["m_TextureSettings"]
    if "m_WrapU" in ts or "m_WrapV" in ts:
        if "m_WrapU" not in ts or "m_WrapV" not in ts:
            raise ValueError("Both source texture wrap axes are required")
        wrap_u, wrap_v = ts["m_WrapU"], ts["m_WrapV"]
    else:
        wrap_u = wrap_v = ts["m_WrapMode"]
    if wrap_u not in WRAP or wrap_v not in WRAP:
        raise ValueError("Unsupported texture wrap mode: " + repr((wrap_u, wrap_v)))
    if settings["m_ColorSpace"] not in (0, 1) or ts["m_FilterMode"] not in FILTER:
        raise ValueError("Invalid texture color space/filter")
    # Unity 2019 serializes m_MipCount. The legacy m_MipMap reader member can
    # remain false even when the source texture has a complete mip chain.
    mip_count = settings.get("m_MipCount")
    if type(mip_count) is not int or mip_count < 1:
        raise ValueError("Actual serialized texture mip count is required")
    if ts.get("m_MipBias", 0.0) != 0.0:
        raise ValueError("Nonzero original texture mip bias needs a sampling contract")
    return {"SRGB": settings["m_ColorSpace"] == 1, "CompressionSettings": "TC_Default",
            "AddressX": WRAP[wrap_u], "AddressY": WRAP[wrap_v],
            "Filter": FILTER[ts["m_FilterMode"]],
            "MipGenSettings": "TMGS_FromTextureGroup" if mip_count > 1 else "TMGS_NoMipmaps"}


def plan_imports(deps_paths, revision="", selected_pids=None, mesh_sources=None):
    selected_pids = set(str(p) for p in selected_pids) if selected_pids is not None else None
    mesh_sources = {str(p): Path(f) for p, f in (mesh_sources or {}).items()}
    entries, assets = {}, {}
    for deps_path in deps_paths:
        for pid, entry in read_json(deps_path).items():
            if selected_pids is not None and pid not in selected_pids:
                continue
            if entry["type"] not in ("Texture2D", "Mesh"):
                continue
            props = {}
            if entry["type"] == "Texture2D":
                source = source_file(entry, ".png")
                props = texture_properties(read_json(source_file(entry, ".json")))
                directory = TEX_DIR
            else:
                source = mesh_sources[pid] if pid in mesh_sources else source_file(entry, ".fbx")
                directory = MESH_DIR
                if source.suffix.lower() != ".fbx" or not source.is_file():
                    raise ValueError("Mesh 来源必须是实际 FBX 文件: " + str(source))
            identity = {"type": entry["type"], "name": entry["name"], "pid": pid,
                        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "properties": props, "revision": revision}
            if entry["type"] == "Mesh":
                identity["mesh_import_settings"] = dict(MESH_IMPORT_SETTINGS)
            name = version_name(entry["name"], identity)
            item = {"identity": identity, "source": str(source), "path": directory + "/" + name,
                    "name": name, "directory": directory, "properties": props, "type": entry["type"]}
            if pid in entries and entries[pid]["identity"] != identity:
                raise ValueError("Conflicting cross-file source/settings for PathID " + pid)
            entries[pid] = item
            assets[pid] = item["path"]
    if selected_pids is not None and selected_pids != set(entries):
        raise ValueError("Selected texture/mesh dependencies are missing: " + repr(sorted(selected_pids - set(entries))))
    if any(pid not in entries or entries[pid]["type"] != "Mesh" for pid in mesh_sources):
        raise ValueError("FBX 来源覆盖只允许本批明确选择的 Mesh")
    return {"entries": entries, "assets": assets, "targets": sorted(set(assets.values()))}


def import_static_mesh(unreal, item):
    """标准 Editor 的显式 FBX 导入；不使用会默认忽略源顶点色的通用快捷入口。"""
    if item["identity"]["mesh_import_settings"] != MESH_IMPORT_SETTINGS:
        raise ValueError("未实现的 Mesh 导入契约")
    options = unreal.FbxImportUI()
    for prop, value in dict(automated_import_should_detect_type=False, import_mesh=True,
            import_as_skeletal=False, import_materials=False, import_textures=False, import_animations=False,
            override_full_name=True, mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
            original_import_type=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        options.set_editor_property(prop, value)
    data = options.get_editor_property("static_mesh_import_data")
    settings = {**MESH_IMPORT_SETTINGS,
        "vertex_color_import_option": unreal.VertexColorImportOption.REPLACE,
        "normal_import_method": unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
        "import_translation": unreal.Vector(0, 0, 0), "import_rotation": unreal.Rotator(0, 0, 0)}
    for prop, value in settings.items():
        data.set_editor_property(prop, value)
        if data.get_editor_property(prop) != value:
            raise RuntimeError("FBX 导入选项读回不同: " + prop)
    task = unreal.AssetImportTask()
    for prop, value in dict(filename=item["source"], destination_path=item["directory"],
            destination_name=item["name"], factory=unreal.FbxFactory(), options=options,
            automated=True, replace_existing=False, replace_existing_settings=False, save=False).items():
        task.set_editor_property(prop, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    expected = item["path"] + "." + item["name"]
    if list(task.get_editor_property("imported_object_paths")) != [expected]:
        raise RuntimeError("FBX 导入产物不是本批唯一新网格: " + item["path"])
    mesh = unreal.EditorAssetLibrary.load_asset(item["path"])
    if not isinstance(mesh, unreal.StaticMesh) or mesh.get_path_name() != expected:
        raise RuntimeError("FBX 新网格身份不同: " + item["path"])
    imported = mesh.get_editor_property("asset_import_data")
    for prop, value in settings.items():
        if imported.get_editor_property(prop) != value:
            raise RuntimeError("网格有效导入设置不同: " + prop)


def apply_imports(plan, session, *, unreal=None):
    # Check every source before importing the first item, including later items.
    for item in plan["entries"].values():
        if hashlib.sha256(Path(item["source"]).read_bytes()).hexdigest() != item["identity"]["source_sha256"]:
            raise ValueError("FX import source changed after planning: " + item["source"])
    if any(i["type"] == "Mesh" for i in plan["entries"].values()) and unreal is None:
        raise ValueError("源 Mesh 导入需要显式标准 Editor 宿主，通用 MCP 快捷入口不能保证顶点色契约")
    for item in plan["entries"].values():
        path = item["path"]
        if path in session.created:
            continue
        session.begin_create(path)
        if item["type"] == "Texture2D":
            session.m.tool("editor_toolset.toolsets.texture.TextureTools.import_file",
                           folder_path=item["directory"], asset_name=item["name"], source_file=item["source"])
        else:
            import_static_mesh(unreal, item)
        if not session.m.tool(ASSET + "exists", path=path)["returnValue"]:
            raise RuntimeError("Imported FX asset is missing: " + path)
        session.created_asset(path)
        if item["properties"]:
            session.m.tool(OBJ + "set_properties", instance=ref(path), values=json.dumps(item["properties"]))
            back = json.loads(session.m.tool(OBJ + "get_properties", instance=ref(path),
                                            properties=list(item["properties"]))["returnValue"])
            for key, value in item["properties"].items():
                if back.get(key) != value:
                    raise RuntimeError("%s.%s: expected %r, got %r" % (path, key, value, back.get(key)))
        session.save([path])
    return plan["assets"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("deps", nargs="+")
    parser.add_argument("--revision", default="")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--endpoint")
    parser.add_argument("--approved-targets", type=Path)
    args = parser.parse_args()
    plan = plan_imports(args.deps, args.revision)
    if not args.apply:
        print(json.dumps(plan, ensure_ascii=False, indent=1))
        return
    if not args.endpoint or not args.approved_targets:
        parser.error("--apply requires the assigned --endpoint and exact --approved-targets list")
    from ue_mcp import Mcp
    session = AssetSession(Mcp(args.endpoint), plan["targets"], read_json(args.approved_targets))
    print(json.dumps(apply_imports(plan, session), ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
