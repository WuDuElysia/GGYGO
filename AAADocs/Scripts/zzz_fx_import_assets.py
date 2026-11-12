"""Plan and import immutable versions of FX textures/meshes into an exact batch.

The default command is offline. All inputs/settings/collisions and ALL destination
packages are checked before mutation. Existing packages and source export maps are
never changed. Returned maps are machine data; callers choose their output file.
"""
import argparse
import hashlib
import gzip
import re
import json
import math
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
        label = entry.get("name") or "PathID " + str(entry.get("pathID", "<missing>"))
        raise ValueError("Expected one existing %s for %s" % (extension, label))
    return files[0]


def texture_settings_source(entry):
    """Native 元数据须由映射明确指向；多个不同来源不按先后猜选。"""
    listed = [Path(f) for f in entry["files"] if f.lower().endswith(".json")]
    metadata = entry.get("metadataJson")
    if metadata is not None:
        metadata = Path(metadata)
        if metadata.suffix.lower() != ".json" or not metadata.is_file() \
                or any(path.resolve() != metadata.resolve() for path in listed) or len(listed) > 1:
            raise ValueError("Conflicting or invalid texture settings sources for PathID " + str(entry.get("pathID")))
        return metadata
    return source_file(entry, ".json")


def texture_properties(settings, *, unity_version=None):
    ts = settings["m_TextureSettings"]
    # Native 的历史字段名 m_WrapMode 表示 U；V/W 各自独立，不能覆盖。
    for axis in ("m_WrapMode", "m_WrapU", "m_WrapV", "m_WrapW"):
        if axis in ts and (type(ts[axis]) is not int or ts[axis] not in WRAP):
            raise ValueError("Unsupported texture wrap axis: " + axis + "=" + repr(ts[axis]))
    if "m_WrapMode" in ts and "m_WrapU" in ts and ts["m_WrapMode"] != ts["m_WrapU"]:
        raise ValueError("Conflicting m_WrapMode/U texture settings")
    if "m_WrapMode" not in ts and "m_WrapU" not in ts:
        raise ValueError("Missing serialized texture U wrap setting")
    wrap_u = ts["m_WrapU"] if "m_WrapU" in ts else ts["m_WrapMode"]
    if "m_WrapV" in ts:
        wrap_v = ts["m_WrapV"]
    else:
        # 只有来源明确声明的旧版共享布局才能用一个 wrap。
        # 缺版本或 2017+ 缺 V 是源字段缺口，不用 U 偷换 V。
        parts = unity_version.split(".") if isinstance(unity_version, str) else []
        legacy_shared = len(parts) >= 2 and parts[0].isdigit() and parts[1].isdigit() \
            and 0 < int(parts[0]) < 2017 and "m_WrapU" not in ts and "m_WrapW" not in ts
        if not legacy_shared:
            raise ValueError("Missing serialized texture V wrap; U does not prove V. Exact native settings or a declared pre-2017 layout is required")
        wrap_v = wrap_u
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
            settings_source = None
            texture_contract = None
            mesh_source = None
            if entry["type"] == "Texture2D":
                settings_path = texture_settings_source(entry)
                settings_raw = settings_path.read_bytes()
                settings = json.loads(settings_raw.decode("utf-8-sig"))
                half_texture = settings.get("m_TextureFormat") == 17
                source = source_file(entry, ".exr" if half_texture else ".png")
                try:
                    props = texture_properties(settings, unity_version=entry.get("unityVersion"))
                except (ValueError, KeyError) as error:
                    raise ValueError("TexturePID=%s Source=%s: %s" % (pid, settings_path, error)) from error
                if half_texture:
                    if settings["m_ColorSpace"] != 0 or settings["m_MipCount"] != 1:
                        raise ValueError("RGBAHalf 数据贴图目前仅支持线性单 Mip EXR")
                    # TC_HDR 保留半精度 RGBA，关闭颜色调整可保留位置数据的负值及 alpha。
                    props.update(CompressionSettings="TC_HDR", CompressionNoAlpha=False,
                        AdjustBrightness=1.0, AdjustBrightnessCurve=1.0, AdjustVibrance=0.0,
                        AdjustSaturation=1.0, AdjustRGBCurve=1.0, AdjustHue=0.0,
                        AdjustMinAlpha=0.0, AdjustMaxAlpha=1.0)
                if entry.get("vertex_sampling_bounds") is not None:
                    if entry["vertex_sampling_bounds"] != [0, 1] or settings.get("m_TextureFormat") != 25:
                        raise ValueError("顶点采样边界仅消费已证BC7 UNorm纹理")
                    props.update(AdjustBrightness=1.0, AdjustBrightnessCurve=1.0, AdjustVibrance=0.0,
                        AdjustSaturation=1.0, AdjustRGBCurve=1.0, AdjustHue=0.0,
                        AdjustMinAlpha=0.0, AdjustMaxAlpha=1.0, CompressionNoAlpha=False)
                settings_source = {"path": str(settings_path.resolve()), "size": len(settings_raw),
                                   "sha256": hashlib.sha256(settings_raw).hexdigest()}
                texture_contract = {"source_mip_count": settings["m_MipCount"],
                    "source_unity_version": entry.get("unityVersion"),
                    "wrap_layout": "NativeIndependentUV" if "m_WrapV" in settings["m_TextureSettings"] else "DeclaredPre2017SharedWrap",
                    "source_texture_settings": settings["m_TextureSettings"],
                    "w_axis": "PreservedSourceSettingUnusedByTexture2D",
                    "imported_image": "ExportedBaseImage",
                    "mip_policy": "UETextureGroupRegeneration" if settings["m_MipCount"] > 1 else "NoMipmaps",
                    "original_mip_pixels_verified": False, "original_sampler_equivalence_verified": False}
                if half_texture:
                    texture_contract["pixel_format"] = "RGBAHalf_EXR"
                if "pixelEvidence" in entry:
                    texture_contract["exported_pixel_evidence"] = entry["pixelEvidence"]
                if "sourceMipChainEvidence" in entry:
                    texture_contract["source_mip_chain_evidence"] = entry["sourceMipChainEvidence"]
                directory = TEX_DIR
            else:
                source = mesh_sources[pid] if pid in mesh_sources else source_file(entry, ".fbx")
                directory = MESH_DIR
                if source.suffix.lower() != ".fbx" or not source.is_file():
                    raise ValueError("Mesh 来源必须是实际 FBX 文件: " + str(source))
            if not isinstance(entry.get("name"), str) or not entry["name"]:
                raise ValueError("Missing source asset name for PathID " + pid)
            identity = {"type": entry["type"], "name": entry["name"], "pid": pid,
                        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                        "properties": props, "revision": revision}
            if entry["type"] == "Mesh":
                identity["mesh_import_settings"] = dict(MESH_IMPORT_SETTINGS)
                vertex_texture = entry.get("vertex_texture_mesh")
                if vertex_texture is not None:
                    if vertex_texture.get("mode") != "SourceVertexTextureMesh" \
                            or vertex_texture.get("texture_envelope_includes_all_addressed_frames") is not True:
                        raise ValueError("顶点位置贴图网格缺完整原帧包围范围")
                    identity["vertex_texture_mesh"] = vertex_texture
                    identity["mesh_import_settings"]["remove_degenerates"] = False
                    for side in ("Positive", "Negative"):
                        values = vertex_texture[side.lower() + "_bounds_extension_cm"]
                        if len(values) != 3 or any(not math.isfinite(v) or v < 0 for v in values):
                            raise ValueError("顶点位置贴图包围扩展无效")
                        props[side + "BoundsExtension"] = dict(zip("xyz", values))
                if entry.get("source_tangents_in_fbx") is True:
                    identity["mesh_tangent_mode"] = "PreserveSourceTangentAndBinormal"
                    mesh_json = source_file(entry, ".json")
                    mesh_raw = mesh_json.read_bytes()
                    mesh_data = json.loads(mesh_raw.decode("utf-8-sig"))
                    mesh_source = {"path": str(mesh_json.resolve()), "size": len(mesh_raw),
                                   "sha256": hashlib.sha256(mesh_raw).hexdigest()}
                    identity["source_mesh_json_sha256"] = mesh_source["sha256"]
            name = version_name(entry["name"], identity)
            item = {"identity": identity, "source": str(source), "path": directory + "/" + name,
                    "name": name, "directory": directory, "properties": props, "type": entry["type"]}
            if settings_source is not None:
                item.update(settings_source=settings_source, source_texture_contract=texture_contract)
            if mesh_source is not None:
                item.update(source_mesh_json=mesh_source, source_geometry_contract={"mesh": {
                    "pid": pid, "source_json": mesh_source["path"], "vertex_count": mesh_data["m_VertexCount"]}},
                    vertex_color_mode="SourceAbsentNativeWhite" if mesh_data.get("m_Colors") is None else "SourceRGBA")
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
    expected_settings = dict(MESH_IMPORT_SETTINGS)
    if item["identity"].get("vertex_texture_mesh") is not None:
        expected_settings["remove_degenerates"] = False
    if item["identity"]["mesh_import_settings"] != expected_settings:
        raise ValueError("未实现的 Mesh 导入契约")
    tangent_mode = item["identity"].get("mesh_tangent_mode")
    if tangent_mode not in (None, "PreserveSourceTangentAndBinormal"):
        raise ValueError("未实现的源Tangent导入契约")
    options = unreal.FbxImportUI()
    for prop, value in dict(automated_import_should_detect_type=False, import_mesh=True,
            import_as_skeletal=False, import_materials=False, import_textures=False, import_animations=False,
            override_full_name=True, mesh_type_to_import=unreal.FBXImportType.FBXIT_STATIC_MESH,
            original_import_type=unreal.FBXImportType.FBXIT_STATIC_MESH).items():
        options.set_editor_property(prop, value)
    data = options.get_editor_property("static_mesh_import_data")
    settings = {**expected_settings,
        "vertex_color_import_option": unreal.VertexColorImportOption.REPLACE,
        "normal_import_method": unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS
            if tangent_mode is not None else unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS,
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
    if item["identity"].get("vertex_texture_mesh") is not None:
        # UV 是整数取像素地址；半精度舍入可能跨像素。所有源三角还会在后续帧展开。
        editor = unreal.get_editor_subsystem(unreal.StaticMeshEditorSubsystem)
        build_settings = editor.get_lod_build_settings(mesh, 0)
        for name, value in (("use_full_precision_u_vs", True), ("remove_degenerates", False)):
            build_settings.set_editor_property(name, value)
        editor.set_lod_build_settings(mesh, 0, build_settings)
        actual = editor.get_lod_build_settings(mesh, 0)
        if not actual.get_editor_property("use_full_precision_u_vs") or actual.get_editor_property("remove_degenerates"):
            raise RuntimeError("位置贴图网格未保留全精度 UV 和动画三角形")


def _validate_import_sources(plan):
    # Check every source before importing the first item, including later items.
    for item in plan["entries"].values():
        if hashlib.sha256(Path(item["source"]).read_bytes()).hexdigest() != item["identity"]["source_sha256"]:
            raise ValueError("FX import source changed after planning: " + item["source"])
        mesh_source = item.get("source_mesh_json")
        if mesh_source is not None:
            data = Path(mesh_source["path"]).read_bytes()
            if len(data) != mesh_source["size"] or hashlib.sha256(data).hexdigest() != mesh_source["sha256"]:
                raise ValueError("FX source TBN JSON changed after planning: " + mesh_source["path"])
        settings_source = item.get("settings_source")
        if settings_source is not None:
            data = Path(settings_source["path"]).read_bytes()
            if len(data) != settings_source["size"] or hashlib.sha256(data).hexdigest() != settings_source["sha256"]:
                raise ValueError("FX texture settings changed after planning: " + settings_source["path"])


def _record_identity(pin):
    path = Path(pin["path"])
    size = pin["size"] if "size" in pin else pin["size_bytes"]
    sha = pin["sha256"]
    if (not path.is_absolute() or type(size) is not int or size < 0
            or not isinstance(sha, str) or re.fullmatch(r"[0-9a-fA-F]{64}", sha) is None):
        raise ValueError("FX复用文件record缺准确绝对路径/长度/SHA")
    return str(path.resolve()).lower(), size, sha.lower()


def _read_resume_record(pin):
    identity = _record_identity(pin)
    path = Path(pin["path"])
    raw = path.read_bytes()
    if len(raw) != identity[1] or hashlib.sha256(raw).hexdigest() != identity[2]:
        raise ValueError("FX复用文件身份改变: " + str(path))
    stat = path.stat()
    if ("device" in pin and stat.st_dev != pin["device"]
            or "inode" in pin and stat.st_ino != pin["inode"]):
        raise ValueError("FX复用文件实体改变: " + str(path))
    return raw


def _resume_json(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def validate_import_resume(plan, record):
    """核本次明确Root保留回执、完整来源配方及原位包文件；纯只读，不签Native就绪。"""
    recovery = json.loads(_read_resume_record(record))
    if (recovery.get("schema") != "GGYGO.RootAuthorFailureRecovery/v1"
            or recovery.get("recovery_success") is not True
            or recovery.get("retained_imports_complete") is not True):
        raise ValueError("FX复用需要完整归还且明确保留全部导入的Root原回执")
    before = json.loads(_read_resume_record(recovery["before"]))
    window = json.loads(_read_resume_record(recovery["failed_window"]))
    leaf = json.loads(_read_resume_record(recovery["failed_leaf"]))
    if (_record_identity(window["leaf_receipt"]) != _record_identity(recovery["failed_leaf"])
            or window.get("software_epoch") != recovery["retained_software_epoch"]
            or before.get("software_epoch") != recovery["retained_software_epoch"]
            or leaf.get("pending_tool") is not False or window.get("pending_tool") is not False):
        raise ValueError("FX复用前窗/leaf/软件或在途身份不一致")
    importer = recovery["retained_importer"]
    if _record_identity(importer)[0] != str(Path(__file__).resolve()).lower():
        raise ValueError("FX复用历史导入器不是当前原模块")
    preparation_pin = recovery["retained_preparation"]
    for pin in (importer, preparation_pin):
        if sum(_record_identity(row) == _record_identity(pin) for row in before["inputs"]) != 1:
            raise ValueError("FX复用旧导入器/准备身份未被准确前窗冻结")
    previous = json.loads(gzip.decompress(_read_resume_record(preparation_pin)))
    for action in previous["actions"].values():
        for member in action["members"].values():
            pins = [pin for pin in member["converter_inputs"]
                    if _record_identity(pin)[0] == _record_identity(importer)[0]]
            if len(pins) != 1 or _record_identity(pins[0]) != _record_identity(importer):
                raise ValueError("FX复用旧准备未消费准确历史导入器")
    # 历史源身份只对旧准备/旧冻结证据；新IA源码不能按旧hash伪称同一文件。
    provenance = leaf["observations"]["prepared_import_provenance"]
    if _resume_json(provenance) != _resume_json(plan["prepared_import_provenance"]):
        raise ValueError("FX复用当前完整来源见证与原实际导入来源不同")
    entries, assets = plan["entries"], plan["assets"]
    packages = set(plan["targets"])
    families = recovery["retained_asset_postimages"]
    if (set(entries) != set(assets) or packages != set(assets.values())
            or len(packages) != len(entries) or set(families) != packages
            or recovery["retained_created_asset_count"] != len(packages)
            or not packages.issubset(leaf["created_packages"])
            or not packages.issubset(leaf["saved_packages"])):
        raise ValueError("FX复用必须覆盖准确当前全部imports，且有原真实创建/保存事实")
    saved_events = {path for event in leaf["observations"]["save_tool_events"]
                    if event["tool"] == ASSET + "save_assets" and event["status"] == "returned"
                    and event["pending"] is False and event["return_value"] is True
                    for path in event["asset_paths"]}
    if not packages.issubset(saved_events):
        raise ValueError("FX复用缺完整原真实同步保存成功事件")
    for pid, item in entries.items():
        if item["type"] not in ("Texture2D", "Mesh"):
            raise ValueError("FX复用未支持的源资产类型: " + str(item["type"]))
        witness = provenance["execution_witnesses"][pid]
        selected = [row["entry"] for row in provenance["occurrences"][pid]
                    if row["action"] == witness["action"] and row["member"] == witness["member"]]
        if (len(selected) != 1 or _resume_json(selected[0]) != _resume_json(item)
                or item["identity"]["pid"] != pid or assets[pid] != item["path"]):
            raise ValueError("FX复用完整源recipe不同: " + pid)
    _validate_import_sources(plan)
    project = Path(__file__).resolve().parents[2]
    byte_count = 0
    for package in sorted(packages):
        if not re.fullmatch(r"/Game/[A-Za-z0-9_/]+", package):
            raise ValueError("FX复用包路径无效: " + package)
        rows = families[package]
        if _resume_json(rows) != _resume_json(window["target_postimages"][package]):
            raise ValueError("FX复用文件后像不是准确原窗: " + package)
        base = project / "Content" / package[len("/Game/"):]
        expected = {str(Path(str(base) + suffix).resolve()).lower()
                    for suffix in (".uasset", ".umap", ".uexp", ".ubulk", ".uptnl")}
        if len(rows) != len(expected) or {str(Path(row["path"]).resolve()).lower() for row in rows} != expected:
            raise ValueError("FX复用原位包文件族不完整: " + package)
        for row in rows:
            path = Path(row["path"])
            if (type(row["exists"]) is not bool or path.exists() != row["exists"]
                    or row["exists"] and not path.is_file()):
                raise ValueError("FX复用包文件存在性改变: " + str(path))
            if row["exists"]:
                pin = row["file"]
                if _record_identity(pin)[0] != str(path.resolve()).lower():
                    raise ValueError("FX复用包文件身份路径不同: " + str(path))
                byte_count += len(_read_resume_record(pin))
        if not Path(str(base) + ".uasset").is_file():
            raise ValueError("FX复用缺实际uasset: " + package)
    if byte_count != recovery["retained_created_asset_bytes"]:
        raise ValueError("FX复用原位包总字节与保留回执不同")
    return {"source_receipt": dict(record), "packages": sorted(packages),
            "source_importer": importer, "source_preparation": preparation_pin,
            "software_epoch": recovery["retained_software_epoch"], "asset_bytes": byte_count}


def _property_values_equal(actual, expected):
    """Native属性经JSON仅保number；有限数值精确比较，bool与其余类型不混用。"""
    if type(actual) in (int, float) and type(expected) in (int, float):
        return ((type(actual) is int or math.isfinite(actual))
                and (type(expected) is int or math.isfinite(expected)) and actual == expected)
    if type(actual) is not type(expected):
        return False
    if isinstance(actual, dict):
        return actual.keys() == expected.keys() and all(
            _property_values_equal(actual[key], expected[key]) for key in actual)
    if isinstance(actual, (list, tuple)):
        return len(actual) == len(expected) and all(
            _property_values_equal(a, e) for a, e in zip(actual, expected))
    return actual == expected


def verify_import_resume(plan, mcp, validation, receipt, *, unreal, geometry_reports):
    """消费同栈纯核验结果，只读当前Native资产；逐包事实留调用方回执，失败继续抛出。"""
    receipt["stage"] = "NativeContext"
    if unreal is None:
        raise ValueError("FX只读复用需要同一实际Editor上下文")
    project = Path(__file__).resolve().parents[2]
    if Path(unreal.Paths.project_dir()).resolve() != project:
        raise ValueError("FX只读复用Editor不属于准确工程")
    if set(validation["packages"]) != set(plan["targets"]):
        raise ValueError("FX只读复用核验结果不属于当前imports")
    for item in plan["entries"].values():
        path = item["path"]
        receipt.update(current_package=path, stage="NativeIdentity")
        asset = unreal.load_asset(path)
        expected_class = unreal.Texture2D if item["type"] == "Texture2D" else unreal.StaticMesh
        if not isinstance(asset, expected_class) or asset.get_path_name() != path + "." + item["name"]:
            raise RuntimeError("FX复用实际Native资产类型/身份不符: " + path)
        receipt["identity_readbacks"][path] = asset.get_class().get_path_name()
        if item["properties"]:
            receipt["stage"] = "NativeProperties"
            actual = json.loads(mcp.tool(OBJ + "get_properties", instance=ref(path),
                                        properties=list(item["properties"]))["returnValue"])
            receipt["property_readbacks"][path] = actual
            for key, expected_value in item["properties"].items():
                if key not in actual or not _property_values_equal(actual[key], expected_value):
                    raise RuntimeError("FX复用%s.%s: expected %r, got %r" %
                                       (path, key, expected_value, actual.get(key)))
        if item.get("source_mesh_json") is not None:
            receipt["stage"] = "NativeGeometry"
            from build_pyrios_ghost_fx import read_geometry
            report = read_geometry(unreal, item, item["source_geometry_contract"],
                                   vertex_color_mode=item["vertex_color_mode"], verify_tangents=True)
            if report.get("source_model_tangent_basis_verified") is not True:
                raise RuntimeError("FX复用原生SourceModel真TBN未通过: " + path)
            geometry_reports[path] = report
            receipt["geometry_readbacks"][path] = report
        receipt["verified_packages"].append(path)
        receipt["current_package"] = None
    receipt["stage"] = "Coverage"
    if (set(receipt["verified_packages"]) != set(validation["packages"])
            or len(receipt["verified_packages"]) != len(validation["packages"])):
        raise RuntimeError("FX只读复用Native验证未覆盖准确完整集合")
    receipt.update(stage="Complete", complete=True)


def apply_imports(plan, session, *, unreal=None, geometry_reports=None):
    _validate_import_sources(plan)
    if any(i["type"] == "Mesh" for i in plan["entries"].values()) and unreal is None:
        raise ValueError("源 Mesh 导入需要显式标准 Editor 宿主，通用 MCP 快捷入口不能保证顶点色契约")
    if any(item.get("source_mesh_json") is not None for item in plan["entries"].values()) \
            and not callable(getattr(unreal.GeometryScript_MeshQueries, "get_triangle_normal_tangents", None)):
        raise RuntimeError("实际Editor缺SourceModel真TBN读取ABI，未开始导入")
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
        if item.get("source_mesh_json") is not None:
            from build_pyrios_ghost_fx import read_geometry
            report = read_geometry(unreal, item, item["source_geometry_contract"],
                vertex_color_mode=item["vertex_color_mode"], verify_tangents=True)
            if report.get("source_model_tangent_basis_verified") is not True:
                raise RuntimeError("实际SourceModel未核收源TBN: " + path)
            if geometry_reports is not None:
                geometry_reports[path] = report
        if item["properties"]:
            remaining = item["properties"]
            if item["type"] == "Texture2D":
                # 自动识别的 Normalmap 压缩会在逐属性 PostEdit 时强制关闭 sRGB。
                # 先核定压缩前置，再应用源颜色空间；不依赖 JSON 属性遍历顺序。
                compression = item["properties"]["CompressionSettings"]
                session.m.tool(OBJ + "set_properties", instance=ref(path),
                               values=json.dumps({"CompressionSettings": compression}))
                compression_back = json.loads(session.m.tool(OBJ + "get_properties", instance=ref(path),
                    properties=["CompressionSettings"])["returnValue"])
                if compression_back.get("CompressionSettings") != compression:
                    raise RuntimeError("%s.CompressionSettings: expected %r, got %r before color-space settings" %
                                       (path, compression, compression_back.get("CompressionSettings")))
                remaining = {key: value for key, value in item["properties"].items()
                             if key != "CompressionSettings"}
            if remaining:
                session.m.tool(OBJ + "set_properties", instance=ref(path), values=json.dumps(remaining))
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
