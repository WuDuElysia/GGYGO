"""@file normalize_pyrios_attack_pose.py
@brief 六个既有普攻源的 Body/Root 成对水平原地化与独立冷读。

audit 只读；apply 必须消费同工具成功 audit；cold 消费成功 apply 且使用
不同 PID。基线旁的 host_exit.json 必须由启动者在实际进程退出后记录 PID、
exit_code 和 readback.json 的 report_sha256。apply/cold 拒绝异常前阶段；
recover-cold 专门只读检查已完整保存但退出异常的包，原样保留退出失败，不再次修改包。
只保存六个 Sequence，不改曲线、Montage、ABP、Skeleton 或玩法。
全部源先预检，逐包保存前复验；失败保留原始备份、报告及 dirty，不自动回滚。
公共 controller 会重建 Euler 通道，先检查整数键重建，再核验实际帧间姿态。
源数据、当前 Mesh retarget 后姿态、生产运行与画面验收分别报告。
独立完整 Editor 使用 -ExecutePythonScript="本文件 --mode audit --output <全新Saved目录>"。
"""
import argparse
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import struct
import traceback


PROJECT = Path("F:/ue_project/GGYGO")
BASE = "/Game/Characters/Player/Pyrios/"
PREFIX = BASE + "Animation/Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_"
CASES = {name: (PREFIX + name, keys) for name, keys in (
    ("01", 102), ("01_End", 200), ("02", 82), ("02_End", 302),
    ("03", 85), ("03_End", 393))}
MESH = BASE + "Avatar_Male_Size03_Pyrois_Model"
SKELETON = MESH + "_Skeleton"
ABP = "/Game/BP/Anim/ABP_Pyrios"
BODY, ROOT, MODEL, BODY_PARENT = "Bip001", "Root", "Avatar_Male_Size03_Pyrois_Model", "Bone_Root"
WEAPONS = ("Ctr_Weapon_A_01", "Ctr_Weapon_B_01")
OBSERVED = (BODY, ROOT, BODY_PARENT, MODEL) + WEAPONS
SCHEMA = "PyriosAttackPose/v1"
POSITION_EPS = 0.0005  # 小于 0.005 mm；容纳大轨迹的 float32 写回误差。
ANGLE_EPS_DEGREES = 0.001
SCALE_EPS = 0.000001


def require(condition, reason):
    if not condition:
        raise RuntimeError("Animation.AttackPose: " + reason)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def disk(package):
    require(package.startswith("/Game/"), "非项目包：" + package)
    return PROJECT / "Content" / (package[6:] + ".uasset")


def sample_times(frames, numerator, denominator, duration):
    require(frames > 0 and numerator > 0 and denominator > 0 and math.isfinite(duration), "非法采样网格")
    step = denominator / numerator
    require(abs(duration - frames * step) < step * 0.001, "原生终点不匹配 DataModel")
    # 保留 DataModel 真末键用于写回，并单独评估 float Sequence 实际终点。
    times = [i * denominator / (2 * numerator) for i in range(2 * frames + 1)]
    if duration != times[-1]:
        times.append(duration)
    return times


def subtract(a, b):
    return [x - y for x, y in zip(a, b)]


def rotate(q, v):
    x, y, z, w = q
    tx, ty, tz = 2 * (y * v[2] - z * v[1]), 2 * (z * v[0] - x * v[2]), 2 * (x * v[1] - y * v[0])
    return [v[0] + w * tx + y * tz - z * ty,
            v[1] + w * ty + z * tx - x * tz,
            v[2] + w * tz + x * ty - y * tx]


def local_after_shift(local, parent, shift):
    """只改平移；水平 component 差值经各自父旋转/scale 逆变换。"""
    require(all(abs(s) > 1e-8 for s in parent["s"]), "父基 scale 不可逆")
    q = parent["q"]
    inverse_rotated = rotate([-q[0], -q[1], -q[2], q[3]], shift)
    return subtract(local, [v / s for v, s in zip(inverse_rotated, parent["s"])])


def angle(a, b):
    norm = math.sqrt(sum(x * x for x in a) * sum(x * x for x in b))
    require(norm > 1e-8, "非法 quaternion")
    cosine = min(1.0, abs(sum(x * y for x, y in zip(a, b))) / norm)
    return math.degrees(2 * math.acos(cosine))


def close_vector(actual, expected, epsilon, label):
    require(len(actual) == len(expected) and max(abs(a - b) for a, b in zip(actual, expected)) <= epsilon,
            label + ": " + repr(actual) + " != " + repr(expected))


def run(args):
    import unreal as ue

    output = (PROJECT / args.output).resolve()
    require(output.is_relative_to((PROJECT / "Saved").resolve()) and not output.exists(), "输出须为全新 Saved 目录")
    require(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() == PROJECT.resolve(), "宿主不是本工程")
    output.mkdir(parents=True)
    report = {"schema": SCHEMA, "mode": args.mode, "pid": os.getpid(), "success": False,
              "script_sha256": sha(Path(__file__)), "phase": "host_preflight", "assets": {}, "saved": [], "errors": [],
              "meaning": "源骨姿态和曲线保真；不证明生产 Slot、CMC、运行、画面、Cook 或联机"}
    backend_paths = [PROJECT / "Binaries/Win64" / ("UnrealEditor-" + module + ".dll") for module in ("GGYGO", "GGYGOEditor")]
    report["backend_dlls"] = {str(p): sha(p) for p in backend_paths}
    protected = [disk(p) for p in (MESH, SKELETON, ABP) + tuple(
        BASE + "Animation/Attack/AM_Pyrios_Attack_Normal_" + n for n in ("01", "02", "03"))]
    before_files = {str(p): sha(p) for p in protected}
    originals = {name: sha(disk(package)) for name, (package, _) in CASES.items()}
    report["source_disk_before"] = originals
    prior = None
    sources = {}

    def dirty():
        lib = ue.EditorLoadingAndSavingUtils
        return {"content": sorted(p.get_path_name() for p in lib.get_dirty_content_packages()),
                "maps": sorted(p.get_path_name() for p in lib.get_dirty_map_packages())}

    def transform(value):
        result = {"t": [float(getattr(value.translation, k)) for k in "xyz"],
                  "q": [float(getattr(value.rotation, k)) for k in "xyzw"],
                  "s": [float(getattr(value.scale3d, k)) for k in "xyz"]}
        require(all(math.isfinite(v) for values in result.values() for v in values), "非有限骨变换")
        return result

    def pose_at(asset, time, retarget):
        require(ue.AnimationLibrary.is_valid_time(asset, time) is True, "原生采样时间非法/绑定返回不明确；不夹断或猜末键：" + str(time))
        options = ue.AnimPoseEvaluationOptions()
        for field, value in (("EvaluationType", ue.AnimDataEvalType.RAW),
                             ("bShouldRetarget", retarget), ("bExtractRootMotion", False),
                             ("bIncorporateRootMotionIntoPose", True), ("OptionalSkeletalMesh", mesh),
                             ("bEvaluateCurves", False)):
            options.set_editor_property(field, value)
        pose = ue.AnimPoseExtensions.get_anim_pose_at_time(asset, time, options)
        require(ue.AnimPoseExtensions.is_valid(pose), asset.get_path_name() + ": 原生 pose 无效")
        return pose

    def capture(asset, retarget):
        model = asset.get_editor_property("DataModelInterface")
        rate = model.get_frame_rate()
        frames = int(model.get_number_of_frames())
        names = [str(n) for n in model.get_bone_track_names()]
        duration = float(asset.get_play_length())
        require(len(names) == len(set(n.casefold() for n in names)) and {BODY.casefold(), ROOT.casefold()}.issubset(
            n.casefold() for n in names), "Body/Root authored 轨道缺失或重名")
        rows = []
        inventory = None
        anchor = None
        for time in sample_times(frames, int(rate.numerator), int(rate.denominator), duration):
            pose = pose_at(asset, time, retarget)
            current = [str(n) for n in ue.AnimPoseExtensions.get_bone_names(pose)]
            require(set(n.casefold() for n in OBSERVED).issubset(n.casefold() for n in current), "观察骨不在当前 Mesh pose")
            if inventory is None:
                inventory = current
                ref = ue.AnimPoseExtensions.get_ref_bone_pose(pose, ROOT, ue.AnimPoseSpaces.WORLD)
                anchor = transform(ref)["t"][:2] + [0.0]
            require(current == inventory, "采样中 pose 骨清单改变")
            row = {"time": time, "local": {}, "component": {}}
            digest = hashlib.sha256()
            for name in current:
                local = transform(ue.AnimPoseExtensions.get_bone_pose(pose, name, ue.AnimPoseSpaces.LOCAL))
                if name.casefold() not in (BODY.casefold(), ROOT.casefold()):
                    digest.update(name.casefold().encode())
                    digest.update(struct.pack("<10d", *(local["t"] + local["q"] + local["s"])))
                if name.casefold() in {n.casefold() for n in OBSERVED}:
                    canonical = next(n for n in OBSERVED if n.casefold() == name.casefold())
                    row["local"][canonical] = local
                    row["component"][canonical] = transform(ue.AnimPoseExtensions.get_bone_pose(pose, name, ue.AnimPoseSpaces.WORLD))
            row["unmodified_local_sha256"] = digest.hexdigest()
            rows.append(row)
        props = {}
        for field in ("bEnableRootMotion", "bForceRootLock", "RootMotionRootLock", "RateScale", "AdditiveAnimType"):
            value = asset.get_editor_property(field)
            props[field] = value if isinstance(value, (bool, float, int)) else str(value)
        require(props["bEnableRootMotion"] is False and props["bForceRootLock"] is False, "原生 root 配置偏离非提取契约")
        return {"keys": int(model.get_number_of_keys()), "frames": frames, "rate": [rate.numerator, rate.denominator],
                "duration": duration, "tracks": names, "inventory": inventory, "properties": props,
                "anchor": anchor, "retarget": retarget, "rows": rows}

    def curves(asset):
        names = list(ue.AnimationLibrary.get_animation_curve_names(asset, ue.RawCurveTrackTypes.RCT_FLOAT))
        snapshot = ue.GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot(asset, names)
        require(snapshot.succeeded, "完整 float 曲线快照失败：" + str(snapshot.error))
        model = asset.get_editor_property("DataModelInterface")
        metadata = model.get_editor_property("CurveIdentifierToMetaData")
        precise = []
        for curve in snapshot.curves:
            keys = []
            for key in curve.keys:
                record = {field: float(getattr(key, field)).hex() for field in (
                    "time", "value", "arrive_tangent", "leave_tangent", "arrive_tangent_weight", "leave_tangent_weight")}
                record.update({field: int(getattr(key, field)) for field in ("interp_mode", "tangent_mode", "tangent_weight_mode")})
                keys.append(record)
            precise.append({"name": str(curve.name), "flags": int(curve.flags), "default": float(curve.default_value).hex(),
                            "pre": int(curve.pre_infinity_extrap), "post": int(curve.post_infinity_extrap), "keys": keys})
        # 此 struct 字段在 5.8 的 Python 绑定中为 protected。展示元数据只读
        # 公共原生 export_text，不伪造私有 getter；数值曲线采用上面的完整 DTO。
        meta = [[identifier.export_text(), value.export_text()] for identifier, value in metadata.items()]
        return {"names": [str(n) for n in names], "duration": float(snapshot.duration_seconds).hex(),
                "curves": precise, "native_auxiliary": snapshot.export_text(),
                "display_metadata_native_export": sorted(meta, key=lambda row: row[0])}

    def authoring(asset, label):
        """精确保护导入来源、metadata 和 Modifier 自有快照；不调用 apply/revert。"""
        objects = [asset.get_editor_property("AssetImportData")] + list(asset.get_editor_property("AssetUserData"))
        result = {"metadata": sorted([str(key), str(value)] for key, value in ue.EditorAssetLibrary.get_metadata_tag_values(asset).items()),
                  "objects": []}
        for i, obj in enumerate(objects):
            require(obj is not None, "导入/AssetUserData 对象无效")
            filename = output / (label + "_authoring_" + str(i) + ".t3d")
            task = ue.AssetExportTask()
            for field, value in (("object", obj), ("exporter", ue.ObjectExporterT3D()), ("filename", str(filename)),
                                 ("automated", True), ("prompt", False), ("replace_identical", False)):
                task.set_editor_property(field, value)
            require(ue.Exporter.run_asset_export_task(task) and filename.is_file(), "原生 authoring 导出失败")
            result["objects"].append({"path": obj.get_path_name(), "native": filename.read_text(encoding="utf-8-sig")})
        return result

    def check_basis(snapshot):
        first = snapshot["rows"][0]
        for row in snapshot["rows"]:
            for name in (BODY_PARENT, MODEL):
                close_vector(row["local"][name]["t"], first["local"][name]["t"], POSITION_EPS, name + " 父平移变化")
                close_vector(row["local"][name]["s"], first["local"][name]["s"], SCALE_EPS, name + " 父 scale 变化")
                require(angle(row["local"][name]["q"], first["local"][name]["q"]) <= ANGLE_EPS_DEGREES, name + " 父旋转变化")

    def check_euler(snapshot):
        # 5.8 EvaluateTrack 对整数键的 FTransform 做 Blend，并非跨帧 Euler lerp。
        # 此处只预检 controller 的 float32 quaternion -> Euler -> quaternion。
        # 帧间保真由实际写后 capture/verify 的原生半帧 pose 判定。
        maximum = 0.0
        for row in snapshot["rows"][:2 * snapshot["frames"] + 1:2]:
            for name in (BODY, ROOT):
                rotation = ue.Quat(*[struct.unpack("<f", struct.pack("<f", v))[0] for v in row["local"][name]["q"]])
                rebuilt = ue.MathLibrary.quat_make_from_euler(rotation.euler())
                error = angle(row["local"][name]["q"], [getattr(rebuilt, k) for k in "xyzw"])
                maximum = max(maximum, error)
                require(error <= ANGLE_EPS_DEGREES, name + " Euler 重建改变整数键姿态；拒绝写入，角差=" + str(error))
        return maximum

    def verify(original, after):
        for field in ("keys", "frames", "rate", "duration", "tracks", "inventory", "properties", "anchor", "retarget"):
            require(original[field] == after[field], field + " 改变")
        require(len(original["rows"]) == len(after["rows"]), "实际采样数量改变")
        for index, (before, actual) in enumerate(zip(original["rows"], after["rows"])):
            require(before["time"] == actual["time"] and before["unmodified_local_sha256"] == actual["unmodified_local_sha256"],
                    "非目标骨 local pose 改变，采样=" + str(index))
            shift = subtract(before["component"][ROOT]["t"], original["anchor"])
            shift[2] = 0.0
            for name in (BODY, ROOT):
                close_vector(actual["component"][name]["t"], subtract(before["component"][name]["t"], shift), POSITION_EPS,
                             name + " 组件平移，采样=" + str(index))
                close_vector(actual["local"][name]["s"], before["local"][name]["s"], SCALE_EPS, name + " scale")
                require(angle(actual["local"][name]["q"], before["local"][name]["q"]) <= ANGLE_EPS_DEGREES, name + " 旋转改变")
            close_vector(subtract(actual["component"][BODY]["t"], actual["component"][ROOT]["t"]),
                         subtract(before["component"][BODY]["t"], before["component"][ROOT]["t"]), POSITION_EPS, "Body−Root 残差")
            for name in WEAPONS:
                close_vector(subtract(actual["component"][name]["t"], actual["component"][BODY]["t"]),
                             subtract(before["component"][name]["t"], before["component"][BODY]["t"]), POSITION_EPS,
                             name + " 相对 Body 位置")
                require(angle(actual["component"][name]["q"], before["component"][name]["q"]) <= ANGLE_EPS_DEGREES,
                        name + " 组件旋转改变")

    try:
        require(not args.expected_pid or args.expected_pid == os.getpid(), "宿主 PID 不匹配")
        require(dirty() == {"content": [], "maps": []}, "宿主有 dirty；保留用户工作")
        require(ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world() is None, "PIE 在运行")
        mesh = ue.load_asset(MESH)
        require(isinstance(mesh, ue.SkeletalMesh), "当前 Mesh 无效")
        # 只读 ReferenceSkeleton 的公共编辑器入口，不创建运行时组件。
        parent_of = ue.SkeletalMeshEditorSubsystem.get_bone_parent
        require(str(parent_of(mesh, BODY)).casefold() == BODY_PARENT.casefold()
                and str(parent_of(mesh, BODY_PARENT)).casefold() == MODEL.casefold()
                and str(parent_of(mesh, ROOT)).casefold() == MODEL.casefold(), "实际父链不匹配，拒绝猜基")
        report["weapon_parent_chains"] = {}
        for name in WEAPONS:
            chain, current = [], name
            while current.casefold() != "none":
                require(current.casefold() not in {n.casefold() for n in chain}, "Mesh 父链循环")
                chain.append(current)
                current = str(parent_of(mesh, current))
            require(BODY.casefold() in {n.casefold() for n in chain} and chain[-1].casefold() == MODEL.casefold(),
                    name + " 不是完整 Body 后代链；停止并交接口影响")
            report["weapon_parent_chains"][name] = chain
        if args.mode != "audit":
            require(args.baseline is not None, "缺少前阶段实际报告")
            prior = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
            require(prior["schema"] == SCHEMA and prior["success"] and prior["mode"] == ("audit" if args.mode == "apply" else "apply")
                    and prior["backend_dlls"] == report["backend_dlls"], "基线未通过或 DLL 改变")
            report["producer_script_sha256"] = prior["script_sha256"]
            if args.mode == "apply":
                require(prior["script_sha256"] == report["script_sha256"], "生产工具改变，请重新 audit")
            else:
                require(set(prior["saved"]) == {package for package, _ in CASES.values()}, "生产未完整保存六包；不能当完整 cold 基线")
            host_exit = json.loads((Path(args.baseline).parent / "host_exit.json").read_text(encoding="utf-8-sig"))
            require(host_exit["pid"] == prior["pid"] and isinstance(host_exit["exit_code"], int)
                    and host_exit["report_sha256"].casefold() == sha(Path(args.baseline)), "真实进程退出回执与基线不匹配")
            report["producer_host_exit"] = host_exit
            if args.mode != "recover-cold":
                require(host_exit["exit_code"] == 0, "前阶段宿主未实际正常退出")
            else:
                require(host_exit["exit_code"] != 0, "recover-cold 只用于真实异常退出后的只读恢复检查")
            require(prior["protected_after"] == before_files, "保护依赖已改变，请重新 audit")
            require(args.mode not in ("cold", "recover-cold") or prior["pid"] != os.getpid(), "独立冷读必须新 PID")
        # 六源完整预检成功前，不修改任何一包。
        for name, (package, keys) in CASES.items():
            report["phase"] = "preflight:" + name
            asset = ue.load_asset(package)
            require(isinstance(asset, ue.AnimSequence), "目标不是 Sequence：" + package)
            require(asset.get_editor_property("Skeleton").get_path_name().split(".")[0] == SKELETON
                    and asset.get_editor_property("AdditiveAnimType") == ue.AdditiveAnimationType.AAT_NONE,
                    "源 Skeleton 或 nonadditive 契约偏离")
            if args.mode not in ("cold", "recover-cold"):
                controller = asset.get_editor_property("Controller")
                require(controller is not None and all(callable(getattr(controller, method, None)) for method in
                        ("set_model", "get_model_interface", "open_bracket", "close_bracket", "set_bone_track_keys")),
                        "必要 controller SDK 未暴露；拒绝继续")
            item = {"package": package, "disk_before": originals[name], "curves": curves(asset),
                    "authoring": authoring(asset, name + "_before"),
                    "source": capture(asset, False), "mesh_pose": capture(asset, True)}
            require(item["source"]["keys"] == keys and item["source"]["rate"] == [60, 1], "六源当前采样身份改变")
            check_basis(item["source"])
            if args.mode not in ("cold", "recover-cold"):
                item["euler_key_max_angle"] = check_euler(item["source"])
            if prior is not None:
                previous = prior["assets"][name]
                require(originals[name] == previous["disk_after"] and item["curves"] == previous["curves"], "包/曲线偏离前阶段：" + name)
                require(item["authoring"] == previous["authoring"], "导入/Modifier/metadata 偏离前阶段：" + name)
                require(item["source"] == previous["source"] and item["mesh_pose"] == previous["mesh_pose"], "骨姿态偏离前阶段：" + name)
            report["assets"][name] = item
            sources[name] = asset
            ue.log("ATTACK_POSE_PREFLIGHT " + name)
        require(dirty() == {"content": [], "maps": []}, "只读预检新增 dirty，停止")
        if args.mode == "apply":
            backups = output / "OriginalPackages"
            backups.mkdir()
            for name, asset in sources.items():
                report["phase"] = "apply:" + name
                package, _ = CASES[name]
                backup = backups / disk(package).name
                shutil.copy2(disk(package), backup)
                require(sha(backup) == originals[name], "原包备份校验失败")
            for name, asset in sources.items():
                item = report["assets"][name]
                source = item["source"]
                before_mesh = item["mesh_pose"]
                controller = asset.get_editor_property("Controller")
                require(controller is not None and callable(controller.set_bone_track_keys), "原生 controller 不可用")
                model = asset.get_editor_property("DataModelInterface")
                controller.set_model(model)
                require(controller.get_model_interface() == model, "controller 未关联当前源 DataModel")
                controller.open_bracket("普攻 Body/Root 成对水平原地化", should_transact=True)
                try:
                    for bone, parent in ((BODY, BODY_PARENT), (ROOT, MODEL)):
                        positions, rotations, scales = [], [], []
                        for row in source["rows"][:2 * source["frames"] + 1:2]:
                            shift = subtract(row["component"][ROOT]["t"], source["anchor"])
                            shift[2] = 0.0
                            local = row["local"][bone]
                            positions.append(ue.Vector(*local_after_shift(local["t"], row["component"][parent], shift)))
                            rotations.append(ue.Quat(*local["q"]))
                            scales.append(ue.Vector(*local["s"]))
                        require(controller.set_bone_track_keys(bone, positions, rotations, scales, should_transact=True), "SetBoneTrackKeys 失败：" + bone)
                finally:
                    controller.close_bracket(should_transact=True)
                after_source, after_mesh = capture(asset, False), capture(asset, True)
                verify(source, after_source)
                verify(before_mesh, after_mesh)
                require(curves(asset) == item["curves"], "已有 float 曲线改变；拒绝保存")
                require(authoring(asset, name + "_presave") == item["authoring"], "导入/Modifier/metadata 改变；拒绝保存")
                require(dirty() == {"content": [item["package"]], "maps": []}, "出现非当前目标 dirty，拒绝保存")
                require(ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), "唯一 Sequence 保存失败")
                report["saved"].append(item["package"])
                # 保存后的 DataModel 再读一次，供新 PID 精确消费。
                item["source"], item["mesh_pose"] = capture(asset, False), capture(asset, True)
                verify(source, item["source"])
                verify(before_mesh, item["mesh_pose"])
                require(curves(asset) == item["curves"], "保存后曲线改变")
                require(authoring(asset, name + "_saved") == item["authoring"], "保存后导入/Modifier/metadata 改变")
                require(dirty() == {"content": [], "maps": []}, "保存后仍有 dirty，保留宿主")
        for name, item in report["assets"].items():
            item["disk_after"] = sha(disk(item["package"]))
            if args.mode != "apply":
                require(item["disk_after"] == originals[name], "只读阶段原包变化")
        report["phase"] = "complete"
        report["success"] = True
    except Exception as error:
        report["errors"].append({"phase": report["phase"], "reason": str(error), "traceback": traceback.format_exc()})
    finally:
        report["protected_before"] = before_files
        report["protected_after"] = {str(p): sha(p) for p in protected}
        if before_files != report["protected_after"]:
            report["errors"].append("Mesh/Skeleton/ABP/Montage 保护文件变化")
        if {str(p): sha(p) for p in backend_paths} != report["backend_dlls"]:
            report["errors"].append("运行期间 DLL 改变")
        report["source_disk_after"] = {name: sha(disk(package)) for name, (package, _) in CASES.items()}
        for name, (package, _) in CASES.items():
            if package not in report["saved"] and report["source_disk_after"][name] != originals[name]:
                report["errors"].append("未保存目标的磁盘包变化：" + name)
        report["dirty_after"] = dirty()
        if report["dirty_after"] != {"content": [], "maps": []}:
            report["errors"].append("存在 dirty；保留宿主，不清标志/回滚/丢弃")
        report["success"] = report["success"] and not report["errors"]
        with (output / "readback.json").open("x", encoding="utf-8") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        ue.log("PYRIOS_ATTACK_POSE " + json.dumps({k: report[k] for k in ("mode", "success", "saved", "errors")}, ensure_ascii=False))
        if args.exit_editor and report["dirty_after"] == {"content": [], "maps": []}:
            ue.SystemLibrary.quit_editor()
    return report


def main():
    parser = argparse.ArgumentParser(description="六源同参考锚、保姿态/曲线的成对原地化")
    parser.add_argument("--mode", choices=("audit", "apply", "cold", "recover-cold"), required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--expected-pid", type=int)
    parser.add_argument("--exit-editor", action="store_true", help="仅供明确命令行运行本工具的自有宿主")
    return run(parser.parse_args())


if __name__ == "__main__":
    main()
