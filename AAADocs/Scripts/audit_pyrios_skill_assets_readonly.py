"""@file audit_pyrios_skill_assets_readonly.py
@brief Special／ExSpecial／Rush 六源、候选 Montage 与挂点的原生只读合同。

仅在统筹协调的独立 Editor 安全窗口调用 run(output, expected_pid)。
output 必须是 Saved 下的全新目录；保存机器消费的读回，不保存资产。
AssetImportData／Registry 描述已存导入记录，不读取外部 FBX／游戏正文，
也不证明 Unity 活动版本。success 仅表示本次读回与保护通过；asset_issues
保留接入缺项。宿主实际退出码由启动者另行记录，不能由 success 推定。
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import re
import traceback


PROJECT = Path("F:/ue_project/GGYGO")
BASE = "/Game/Characters/Player/Pyrios/"
ANIMATION = BASE + "Animation/"
FAMILIES = ("Special", "ExSpecial", "Rush")
SEQUENCES = tuple(ANIMATION + "Avatar_Male_Size03_Pyrois_Ani_Attack_" + family + suffix
                  for family in FAMILIES for suffix in ("_01", "_01_End"))
MONTAGES = tuple(ANIMATION + "Attack/AM_Pyrios_Attack_" + family + "_01" for family in FAMILIES)
LEGACY = tuple(BASE + "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_Attack_ExSpecial_" + suffix
               for suffix in ("01", "01_End"))
MESH = BASE + "Avatar_Male_Size03_Pyrois_Model"
SKELETON = MESH + "_Skeleton"
POSITION_CURVES = tuple("RootMotion_Pos" + axis for axis in "XYZ")
YAW_CURVE = "RootMotion_Yaw"
OBSERVED_BONES = ("Root", "Bip001", "Bone_Root", "Avatar_Male_Size03_Pyrois_Model",
                  "Ctr_Weapon_A_01", "Ctr_Weapon_B_01")
SCHEMA = "PyriosSkillAssetsReadOnly/v1"


def require(condition, reason):
    if not condition:
        raise RuntimeError("Animation.SkillAssets.ReadOnly: " + reason)


def package_file(package):
    require(package in SEQUENCES + MONTAGES + LEGACY + (MESH, SKELETON), "包超出准确读取范围：" + package)
    return PROJECT / "Content" / (package[6:] + ".uasset")


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def root_arrays(text, property_name):
    """只解释 stock T3D 的根数组行，保留 struct／reference 原文。"""
    depth, roots, rows = 0, 0, {}
    pattern = re.compile(r"^\s*" + re.escape(property_name) + r"\((\d+)\)=(.*)$")
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("Begin Object"):
            roots += depth == 0
            depth += 1
        elif stripped == "End Object":
            depth -= 1
            require(depth >= 0, "T3D 对象层级不平衡")
        elif depth == 1:
            match = pattern.fullmatch(line)
            if match:
                index = int(match.group(1))
                require(index not in rows, "重复 T3D 根数组元素：" + property_name)
                rows[index] = match.group(2)
    require(depth == 0 and roots == 1, "T3D 必须有一个完整根对象")
    require(sorted(rows) == list(range(len(rows))), "T3D 根数组下标不连续：" + property_name)
    return [rows[index] for index in range(len(rows))]


def pair_timeline(main_length, main_rate, end_length, end_rate):
    """完整源、segment rate=1、loop=1 的 Montage 位置域；不是运行时 clock。"""
    require(all(math.isfinite(value) and value > 0 for value in
                (main_length, main_rate, end_length, end_rate)), "完整源时长／正向 RateScale 非法")
    boundary = main_length / main_rate
    duration = boundary + end_length / end_rate
    require(math.isfinite(duration), "完整 Main／End 位置域溢出")
    return {"Main": [0.0, boundary], "End": [boundary, duration],
            "segment_rate": 1.0, "looping_count": 1,
            "meaning": "候选完整源位置域；section 尚须实际 author/readback；不包含 Montage/GA rate"}


def skeleton_slot_groups(text):
    result = []
    for row in root_arrays(text, "SlotGroups"):
        groups = re.findall(r'(?:^|[,\(])GroupName="([^"]+)"', row)
        require(len(groups) <= 1, "Skeleton GroupName 不明确")
        # FAnimSlotGroup 原生构造值是 DefaultGroup，stock 导出可省略默认字段。
        group = groups[0] if groups else "DefaultGroup"
        match = re.search(r'(?:^|[,\(])SlotNames=\(([^()]*)\)', row)
        require(match is not None, "Skeleton SlotNames 原生数组不可读")
        names = re.findall(r'"([^"]+)"', match.group(1))
        require(re.sub(r'"[^"]+"|,|\s', "", match.group(1)) == "", "Skeleton SlotNames 语法不可读")
        result.append({"group": group, "slots": names, "native": row})
    return result


def run(output, expected_pid):
    """读取准确已存包；调用者协调宿主、实际退出及后续生产验证。"""
    import unreal as ue

    require(expected_pid == os.getpid(), "必须显式绑定本次独立宿主 PID")
    output = (PROJECT / output).resolve()
    require(output.is_relative_to((PROJECT / "Saved").resolve()) and not output.exists(), "输出须为全新 Saved 目录")
    require(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() == PROJECT.resolve(), "宿主不是本工程")
    output.mkdir(parents=True)
    report = {"schema": SCHEMA, "pid": os.getpid(), "success": False,
              "meaning": "已存资产本次原生读回；不证明 source activity、GA/授予、生产、画面、Cook 或联机",
              "script_sha256": sha(Path(__file__)), "assets": {}, "reads": {}, "errors": [],
              "asset_issues": [], "protected_before": {}, "protected_after": {},
              "dirty_before": None, "dirty_after": None}
    loaded, registered = {}, {}

    def dirty():
        library = ue.EditorLoadingAndSavingUtils
        return {"content": sorted(p.get_path_name() for p in library.get_dirty_content_packages()),
                "maps": sorted(p.get_path_name() for p in library.get_dirty_map_packages())}

    def capture(label, operation):
        try:
            result = operation()
            report["reads"][label] = {"available": True, "value": result}
            return result
        except Exception as error:
            report["reads"][label] = {"available": False, "error": str(error)}
            report["errors"].append({"operation": label, "error": str(error), "traceback": traceback.format_exc()})
            ue.log_error("[Animation.SkillAssets.ReadOnly] " + label + ": " + str(error))
            return None

    def file_state(path):
        return {"exists": path.is_file(), "sha256": sha(path) if path.is_file() else None}

    def registry_record(package):
        if package in registered:
            return registered[package]
        native_rows = registry.get_assets_by_package_name(package, include_only_on_disk_assets=True)
        # stock bool／单 out-array 的 Python 绑定可在未找到包时返回 None。
        # 是否确实缺包仍与磁盘核对，不把必需源的加载失败当正常缺省。
        rows = [] if native_rows is None else list(native_rows)
        require(len(rows) <= 1, "包包含多个资产，拒绝按名字选择：" + package)
        require(bool(rows) == package_file(package).is_file(), "Registry／磁盘包存在性不一致：" + package)
        data = rows[0] if rows else None
        registered[package] = data
        record = {"present": data is not None}
        if data is not None:
            record.update({"class": str(data.asset_class_path),
                           "full_name": ue.AssetRegistryHelpers.get_full_name(data),
                           "is_redirector": bool(ue.AssetRegistryHelpers.is_redirector(data))})
            if record["is_redirector"]:
                destination = ue.AssetRegistryHelpers.get_tag_value(data, "DestinationObject")
                require(isinstance(destination, str) and destination, "重定向 Registry 目标不可读：" + package)
                record["destination_registry_tag"] = destination
                record["meaning"] = "on-disk Registry 目标记录；未遍历或加载重定向目标"
        report["assets"][package] = record
        return data

    def load(package, expected_type):
        if package not in loaded:
            data = registry_record(package)
            require(data is not None and not ue.AssetRegistryHelpers.is_redirector(data), "准确源缺失／是重定向包：" + package)
            asset = ue.AssetRegistryHelpers.get_asset(data)
            require(isinstance(asset, expected_type), "原生资产类型不符：" + package)
            require(asset.get_path_name() == package + "." + package.rsplit("/", 1)[1], "原生读取转向其它资产：" + package)
            loaded[package] = asset
            report["assets"][package]["loaded_object"] = asset.get_path_name()
        return loaded[package]

    def native_export(obj, label):
        filename = output / (label + ".t3d")
        require(not filename.exists(), "拒绝覆盖 T3D：" + str(filename))
        task = ue.AssetExportTask()
        for field, value in (("object", obj), ("exporter", ue.ObjectExporterT3D()), ("filename", str(filename)),
                             ("automated", True), ("prompt", False), ("replace_identical", False)):
            task.set_editor_property(field, value)
        require(ue.Exporter.run_asset_export_task(task) and filename.is_file(), "原生 T3D 导出失败：" + obj.get_path_name())
        text = filename.read_text(encoding="utf-8-sig")
        root = '^Begin Object Class=' + re.escape(obj.get_class().get_path_name()) + ' Name="' + re.escape(obj.get_name()) + '"'
        require(re.search(root, text) is not None, "T3D 根不是准确对象：" + obj.get_path_name())
        return {"file": str(filename), "text": text}

    def sockets(owner, text):
        result = []
        for reference in root_arrays(text, "Sockets"):
            match = re.fullmatch(r'''"?/Script/Engine\.SkeletalMeshSocket'([^']+)'"?''', reference)
            require(match is not None, "Socket 根引用语法不可读：" + reference)
            socket = ue.find_object(owner, match.group(1))
            require(isinstance(socket, ue.SkeletalMeshSocket) and socket.get_outer() == owner, "Socket 不是准确 owner 的自有对象")
            record = {"object": socket.get_path_name(), "owner": owner.get_path_name(),
                      "name": str(socket.get_editor_property("socket_name")),
                      "bone": str(socket.get_editor_property("bone_name")),
                      "local_transform": socket.get_socket_local_transform().export_text(),
                      "force_always_animated": bool(socket.get_editor_property("force_always_animated"))}
            result.append(record)
        return result

    def curve_snapshot(asset):
        names = list(ue.AnimationLibrary.get_animation_curve_names(asset, ue.RawCurveTrackTypes.RCT_FLOAT))
        require(len(names) == len(set(str(name).casefold() for name in names)), "曲线名重复")
        if not names:
            return {"names": [], "curves": [], "meaning": "原生清单为空；未调用要求非空名称的 Snapshot"}
        snapshot = ue.GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot(asset, names)
        require(snapshot.succeeded, "完整曲线 DTO 读取失败：" + str(snapshot.error))
        require(float(snapshot.duration_seconds) == float(asset.get_play_length()), "曲线 DTO 与原生源时长不一致")
        curves = []
        for curve in snapshot.curves:
            keys = []
            for key in curve.keys:
                row = {field: float(getattr(key, field)) for field in (
                    "time", "value", "arrive_tangent", "leave_tangent", "arrive_tangent_weight", "leave_tangent_weight")}
                row.update({field: int(getattr(key, field)) for field in ("interp_mode", "tangent_mode", "tangent_weight_mode")})
                keys.append(row)
            curves.append({"name": str(curve.name), "flags": int(curve.flags), "default_value": float(curve.default_value),
                           "pre_infinity_extrap": int(curve.pre_infinity_extrap),
                           "post_infinity_extrap": int(curve.post_infinity_extrap), "keys": keys})
        require([str(name) for name in names] == [curve["name"] for curve in curves], "曲线 DTO 改变请求清单／顺序")
        return {"names": [str(name) for name in names], "duration_seconds": float(snapshot.duration_seconds), "curves": curves}

    def pose_endpoints(asset):
        options = ue.AnimPoseEvaluationOptions()
        for field, value in (("EvaluationType", ue.AnimDataEvalType.RAW), ("bShouldRetarget", False),
                             ("bExtractRootMotion", False), ("bIncorporateRootMotionIntoPose", True),
                             ("OptionalSkeletalMesh", mesh), ("bEvaluateCurves", False)):
            options.set_editor_property(field, value)
        rows = []
        def transform(value):
            record = {"translation": [float(getattr(value.translation, k)) for k in "xyz"],
                      "rotation_quat": [float(getattr(value.rotation, k)) for k in "xyzw"],
                      "scale": [float(getattr(value.scale3d, k)) for k in "xyz"]}
            require(all(math.isfinite(v) for values in record.values() for v in values), "原生 pose 变换含非有限数值")
            return record

        for time in (0.0, float(asset.get_play_length())):
            require(ue.AnimationLibrary.is_valid_time(asset, time) is True, "原生 pose 端点时间非法")
            pose = ue.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
            require(ue.AnimPoseExtensions.is_valid(pose), "原生 pose 端点无效")
            names = {str(name).casefold() for name in ue.AnimPoseExtensions.get_bone_names(pose)}
            require(all(name.casefold() in names for name in OBSERVED_BONES), "源 pose 缺观察骨")
            rows.append({"time": time, "bones": {name: {
                "local": transform(ue.AnimPoseExtensions.get_bone_pose(pose, name, ue.AnimPoseSpaces.LOCAL)),
                "component": transform(ue.AnimPoseExtensions.get_bone_pose(pose, name, ue.AnimPoseSpaces.WORLD))}
                for name in OBSERVED_BONES}})
        return {"evaluation": "RAW / retarget=false / OptionalSkeletalMesh=current / root extraction=false",
                "meaning": "仅端点姿态，不证明帧间 parent basis 恒定或姿态已归一", "rows": rows}

    def sequence(package):
        asset = load(package, ue.AnimSequence)
        model = asset.get_editor_property("DataModelInterface")
        require(model is not None, "源没有 DataModel")
        rate = model.get_frame_rate()
        duration, source_rate = float(asset.get_play_length()), float(asset.get_editor_property("rate_scale"))
        require(math.isfinite(duration) and duration > 0, "源时长无效")
        require(math.isfinite(source_rate) and source_rate > 0, "源 RateScale 不是有限正向倍率")
        require(int(rate.numerator) > 0 and int(rate.denominator) > 0, "源 DataModel 采样率无效")
        import_data = asset.get_editor_property("asset_import_data")
        require(isinstance(import_data, ue.AssetImportData), "AssetImportData 缺失")
        target_rate = asset.get_editor_property("platform_target_frame_rate").get_editor_property("default")
        curves = curve_snapshot(asset)
        names = {name.casefold() for name in curves["names"]}
        properties = {field: str(asset.get_editor_property(field)) for field in (
            "additive_anim_type", "root_motion_root_lock")}
        properties.update({field: bool(asset.get_editor_property(field)) for field in ("enable_root_motion", "force_root_lock")})
        value = {"skeleton": asset.get_editor_property("skeleton").get_path_name(),
                 "duration_seconds": duration, "rate_scale": source_rate,
                 "model_rate": [int(rate.numerator), int(rate.denominator)],
                 "target_sampling_rate": [int(target_rate.numerator), int(target_rate.denominator)],
                 "frames": int(model.get_number_of_frames()), "keys": int(model.get_number_of_keys()),
                 "bone_tracks": [str(name) for name in model.get_bone_track_names()], "properties": properties,
                 "import_data": {"object": import_data.get_path_name(), "resolved_filenames": list(import_data.extract_filenames()),
                                 "native": native_export(import_data, asset.get_name() + "_import"),
                                 "source_activity": "未核；已存导入记录不能认证 Unity 活动版本／当前外部文件"},
                 "metadata": {str(k): str(v) for k, v in ue.EditorAssetLibrary.get_metadata_tag_values(asset).items()},
                 "float_curves": curves, "pose_endpoints": pose_endpoints(asset),
                 "has_position_curves": all(name.casefold() in names for name in POSITION_CURVES),
                 "has_yaw_curve": YAW_CURVE.casefold() in names}
        if not value["has_position_curves"]:
            report["asset_issues"].append({"asset": package, "reason": "PosXYZ 必需曲线未齐"})
        if properties["enable_root_motion"] or properties["force_root_lock"] or asset.get_editor_property("additive_anim_type") != ue.AdditiveAnimationType.AAT_NONE:
            report["asset_issues"].append({"asset": package, "reason": "原生 root／additive 配置需与姿态及 CMC 契约收敛"})
        return value

    def montage(package):
        if registry_record(package) is None:
            return {"present": False, "meaning": "此准确候选包缺失；不推断全项目技能入口"}
        asset = load(package, ue.AnimMontage)
        length, source_rate = float(asset.get_play_length()), float(asset.get_editor_property("rate_scale"))
        require(math.isfinite(length) and length > 0 and math.isfinite(source_rate) and source_rate > 0, "Montage 时长／倍率非法")
        export = native_export(asset, asset.get_name())
        tracks = [{"slot": str(track.get_editor_property("slot_name")),
                   "segments": [segment.export_text() for segment in track.get_editor_property("anim_track").get_editor_property("anim_segments")]}
                  for track in asset.get_editor_property("slot_anim_tracks")]
        return {"present": True, "skeleton": asset.get_editor_property("skeleton").get_path_name(),
                "length": length, "rate_scale": source_rate,
                "tracks": tracks, "section_names": [str(asset.get_section_name(i)) for i in range(asset.get_num_sections())],
                "native_sections": root_arrays(export["text"], "CompositeSections"),
                "notify_events": [{"trigger_time": float(ue.AnimationLibrary.get_anim_notify_event_trigger_time(event)),
                                   "duration": float(ue.AnimationLibrary.get_anim_notify_event_duration(event)),
                                   "native": event.export_text()} for event in ue.AnimationLibrary.get_animation_notify_events(asset)],
                "native": export}

    try:
        report["dirty_before"] = dirty()
        require(report["dirty_before"] == {"content": [], "maps": []}, "宿主已有 dirty，保留用户工作")
        require(ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world() is None, "PIE 在运行")
        for package in SEQUENCES + MONTAGES + LEGACY + (MESH, SKELETON):
            for suffix in (".uasset", ".uexp", ".ubulk"):
                path = package_file(package).with_suffix(suffix)
                report["protected_before"][str(path)] = file_state(path)
        for module in ("GGYGO", "GGYGOEditor"):
            path = PROJECT / "Binaries/Win64" / ("UnrealEditor-" + module + ".dll")
            require(path.is_file(), "必需 Editor DLL 缺失：" + str(path))
            report["protected_before"][str(path)] = file_state(path)
        registry = ue.AssetRegistryHelpers.get_asset_registry()
        registry.wait_for_completion()
        require(not registry.is_loading_assets(), "原生 Registry 尚未就绪")
        mesh = load(MESH, ue.SkeletalMesh)
        skeleton = load(SKELETON, ue.Skeleton)
        require(mesh.get_editor_property("skeleton") == skeleton, "当前 Mesh 与准确 Skeleton 不一致")
        skeleton_export = native_export(skeleton, "Skeleton")
        mesh_export = native_export(mesh, "Mesh")
        report["assets"][SKELETON]["native_export_file"] = skeleton_export["file"]
        report["assets"][MESH]["native_export_file"] = mesh_export["file"]
        slots = capture("skeleton_slots", lambda: skeleton_slot_groups(skeleton_export["text"]))
        if slots is not None and sum(row["slots"].count("FullBody") for row in slots) != 1:
            report["asset_issues"].append({"asset": SKELETON, "reason": "FullBody 未唯一注册；本工具不写 Skeleton"})
        capture("skeleton_sockets", lambda: sockets(skeleton, skeleton_export["text"]))
        capture("mesh_sockets", lambda: sockets(mesh, mesh_export["text"]))
        capture("bone_parents", lambda: {name: str(ue.SkeletalMeshEditorSubsystem.get_bone_parent(mesh, name)) for name in OBSERVED_BONES})
        def weapon_chains():
            result = {}
            for name in OBSERVED_BONES[-2:]:
                chain, current = [], name
                while current.casefold() != "none":
                    require(current.casefold() not in {bone.casefold() for bone in chain}, "Mesh 武器父链循环")
                    chain.append(current)
                    current = str(ue.SkeletalMeshEditorSubsystem.get_bone_parent(mesh, current))
                result[name] = chain
            return result

        capture("weapon_parent_chains", weapon_chains)
        for package in SEQUENCES:
            capture("sequence:" + package, lambda p=package: sequence(p))
        for package in MONTAGES:
            capture("montage:" + package, lambda p=package: montage(p))
        for package in LEGACY:
            capture("legacy_registry:" + package, lambda p=package: (registry_record(p), report["assets"][p])[1])
        for family, main_path, end_path in zip(FAMILIES, SEQUENCES[::2], SEQUENCES[1::2]):
            main = report["reads"]["sequence:" + main_path]
            end = report["reads"]["sequence:" + end_path]
            if main["available"] and end["available"]:
                a, b = main["value"], end["value"]
                if a["skeleton"] != b["skeleton"] or a["skeleton"] != skeleton.get_path_name():
                    report["asset_issues"].append({"family": family, "reason": "Main／End／当前 Mesh 的 Skeleton 不一致"})
                if a["has_yaw_curve"] != b["has_yaw_curve"]:
                    report["asset_issues"].append({"family": family,
                        "reason": "Main／End Yaw 能力不同；须按真实 section binding 收敛，不能推断整对非法或替作者补零曲线"})
                capture("candidate_timeline:" + family, lambda: pair_timeline(a["duration_seconds"], a["rate_scale"], b["duration_seconds"], b["rate_scale"]))
    except Exception as error:
        report["errors"].append({"operation": "audit", "error": str(error), "traceback": traceback.format_exc()})
        ue.log_error("[Animation.SkillAssets.ReadOnly] " + str(error))
    finally:
        report["dirty_after"] = capture("dirty_after", dirty)
        for path in report["protected_before"]:
            result = capture("protection:" + path, lambda p=path: file_state(Path(p)))
            if result is not None:
                report["protected_after"][path] = result
        report["changed_files"] = [path for path, before in report["protected_before"].items()
                                   if report["protected_after"].get(path) != before]
        report["success"] = (not report["errors"] and not report["changed_files"]
                             and report["dirty_before"] == report["dirty_after"] == {"content": [], "maps": []})
        (output / "readback.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        ue.log("[Animation.SkillAssets.ReadOnly] " + json.dumps({"success": report["success"], "errors": len(report["errors"]),
               "asset_issues": len(report["asset_issues"]), "changed_files": report["changed_files"], "output": str(output)}, ensure_ascii=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-pid", type=int, required=True)
    arguments = parser.parse_args()
    require(run(arguments.output, arguments.expected_pid)["success"], "读回失败，保留原报告；不重试／不保存资产")
