"""@file create_pyrios_skill_montages.py
@brief 三技能 Main→完整 End Montage 的 create-only 制作和独立冷读。

create 消费成功的准确只读报告及启动者记录的 host_exit.json；cold 消费
成功 create 和实际正常退出，且必须是另一 PID。host_exit.json 包含 pid、
exit_code、report_sha256。真实窗口与宿主由统筹协调，工具不启动 UE 或编译。
只保存三个新 AM；不创建 FX／取消／命中窗，不修改 AS／ABP／Skeleton。
保存或退出失败保留新包及报告，不覆盖、回滚或自动重试。
"""
import argparse
import importlib.util
import json
import math
import os
from pathlib import Path
import struct
import traceback


PROJECT = Path("F:/ue_project/GGYGO")
AUDIT_FILE = PROJECT / "AAADocs/Scripts/audit_pyrios_skill_assets_readonly.py"
AUDIT_SHA = "42de1d1d770355ea7d0bc2d28fb1483ae5c4189563a53878809be9979efd6d1a"
SCHEMA = "PyriosSkillMontages/v1"
SLOT = "FullBody"
SECTION_NAMES = ("Main", "End")


def require(condition, reason):
    if not condition:
        raise RuntimeError("Animation.SkillMontages: " + reason)


def f32(value):
    require(math.isfinite(value), "表现参数必须有限")
    return struct.unpack("<f", struct.pack("<f", value))[0]


def read_receipt(filename, expected_schema, current_pid, hash_file):
    filename = Path(filename).resolve()
    require(filename.is_relative_to((PROJECT / "Saved").resolve()), "前阶段报告须在 Saved")
    report = json.loads(filename.read_text(encoding="utf-8"))
    exit_report = json.loads((filename.parent / "host_exit.json").read_text(encoding="utf-8"))
    require(report.get("schema") == expected_schema and report.get("success") is True, "前阶段准确报告未成功")
    require(type(report.get("pid")) is int and report["pid"] != current_pid, "必须使用另一个独立宿主")
    require(exit_report.get("pid") == report["pid"] and type(exit_report.get("exit_code")) is int
            and exit_report["exit_code"] == 0 and exit_report.get("report_sha256") == hash_file(filename),
            "缺少前阶段准确实际 exit0 及报告身份；不把 JSON success 当正常退出")
    return report


def validate_source_contract(report, audit):
    require(report.get("schema") == audit.SCHEMA and report.get("success") is True
            and report.get("script_sha256") == AUDIT_SHA, "不是冻结只读工具的成功报告")
    require(not report["asset_issues"], "已存源存在接入缺项；保留诊断，不补源／换源")
    for main, end in zip(audit.SEQUENCES[::2], audit.SEQUENCES[1::2]):
        a = report["reads"]["sequence:" + main]
        b = report["reads"]["sequence:" + end]
        require(a["available"] and b["available"], "完整源读取不成功")
        a, b = a["value"], b["value"]
        require(a["has_position_curves"] is True and b["has_position_curves"] is True, "完整源 PosXYZ 未齐")
        require(type(a["has_yaw_curve"]) is bool and a["has_yaw_curve"] == b["has_yaw_curve"],
                "完整绑定混合 Yaw；交 Movement，不自补 zero")
        require(a["skeleton"] == b["skeleton"] == audit.SKELETON + "." + audit.SKELETON.rsplit("/", 1)[1], "准确 Skeleton 不符")
    return report


def require_new_targets(audit, ue):
    for package in audit.MONTAGES:
        require(not any(audit.package_file(package).with_suffix(suffix).exists() for suffix in (".uasset", ".uexp", ".ubulk"))
                and not ue.EditorAssetLibrary.does_asset_exist(package)
                and ue.find_object(None, package + "." + package.rsplit("/", 1)[1]) is None,
                "准确候选 AM/sidecar 已存在或在内存中；拒绝覆盖：" + package)


def run(args):
    import unreal as ue

    require(args.expected_pid == os.getpid(), "必须显式绑定本次独立宿主 PID")
    spec = importlib.util.spec_from_file_location("_pyrios_skill_audit", AUDIT_FILE)
    audit = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(audit)
    require(audit.sha(AUDIT_FILE) == AUDIT_SHA, "只读工具冻结版本变化")
    output = (PROJECT / args.output).resolve()
    require(output.is_relative_to((PROJECT / "Saved").resolve()) and not output.exists(), "输出须为全新 Saved 目录")
    require(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() == PROJECT.resolve(), "宿主不是本工程")
    output.mkdir(parents=True)
    report = {"schema": SCHEMA, "mode": args.mode, "pid": os.getpid(), "success": False,
              "script_sha256": audit.sha(Path(__file__)), "audit_script_sha256": AUDIT_SHA,
              "meaning": "已存准确六源的 AM 资产制作／冷读；不认证 Unity activity、GA/grant、FX、生产或画面",
              "created": [], "saved": [], "readbacks": {}, "errors": [],
              "protected_before": {}, "protected_after": {}, "dirty_after": None}
    packages = audit.SEQUENCES + audit.LEGACY + (audit.MESH, audit.SKELETON)
    protected = [audit.package_file(package).with_suffix(suffix) for package in packages
                 for suffix in (".uasset", ".uexp", ".ubulk")]
    protected += [PROJECT / "Binaries/Win64" / ("UnrealEditor-" + name + ".dll") for name in ("GGYGO", "GGYGOEditor")]

    def file_state(path):
        present = path.is_file()
        return {"exists": present, "sha256": audit.sha(path) if present else None}

    def dirty():
        lib = ue.EditorLoadingAndSavingUtils
        return {"content": sorted(p.get_path_name() for p in lib.get_dirty_content_packages()),
                "maps": sorted(p.get_path_name() for p in lib.get_dirty_map_packages())}

    def native_snapshot(montage, sources, settings, filename):
        result = ue.GGYGOLinearMontageAuthorLibrary.validate_montage(montage, SLOT, sources, list(SECTION_NAMES))
        require(result.succeeded, "原生完整源／区段验证失败：" + str(result.error))
        require(montage.get_editor_property("rate_scale") == 1.0 and not montage.get_editor_property("loop")
                and montage.get_editor_property("enable_auto_blend_out") is True
                and montage.get_editor_property("blend_out_trigger_time") == 0.0, "Montage 正向速率／完整末端自然混出不符")
        for name in ("blend_in", "blend_out"):
            blend = montage.get_editor_property(name)
            require(blend.get_editor_property("blend_time") == settings[name]
                    and blend.get_editor_property("blend_option") == ue.AlphaBlendOption.HERMITE_CUBIC, "表现参数不符：" + name)
        require(not ue.AnimationLibrary.get_animation_notify_events(montage), "新 AM 存在未批准 Notify")
        require(montage.get_num_sections() == 2 and tuple(str(montage.get_section_name(i)) for i in range(2)) == SECTION_NAMES,
                "真实 Main／End 名称不符")
        task = ue.AssetExportTask()
        for name, value in (("object", montage), ("exporter", ue.ObjectExporterT3D()), ("filename", str(filename)),
                            ("automated", True), ("prompt", False), ("replace_identical", False)):
            task.set_editor_property(name, value)
        require(not filename.exists() and ue.Exporter.run_asset_export_task(task) and filename.is_file(), "原生 AM 导出失败")
        text = filename.read_text(encoding="utf-8-sig")
        sections = audit.root_arrays(text, "CompositeSections")
        require(len(sections) == 2, "原生 T3D 区段数量不符")
        tracks = montage.get_editor_property("slot_anim_tracks")
        segments = tracks[0].get_editor_property("anim_track").get_editor_property("anim_segments")
        return {"object": montage.get_path_name(), "length": float(result.duration_seconds),
                "section_starts": [float(value) for value in result.section_starts], "native_sections": sections,
                "segments": [segment.export_text() for segment in segments], "native_export": str(filename),
                "source_objects": [source.get_path_name() for source in sources], "settings": settings}

    try:
        report["dirty_before"] = dirty()
        require(report["dirty_before"] == {"content": [], "maps": []}, "宿主已有 dirty；保留用户工作")
        require(ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world() is None, "PIE 在运行")
        require(args.mode in ("create", "cold"), "模式无效")
        previous = read_receipt(args.baseline, audit.SCHEMA if args.mode == "create" else SCHEMA, os.getpid(), audit.sha)
        if args.mode == "create":
            validate_source_contract(previous, audit)
            settings = {"blend_in": f32(args.blend_in), "blend_out": f32(args.blend_out)}
            require(all(value >= 0.0 and math.isfinite(value) for value in settings.values()), "显式 blend 参数非法")
            require_new_targets(audit, ue)
        else:
            require(previous.get("mode") == "create" and previous.get("audit_script_sha256") == AUDIT_SHA
                    and previous.get("script_sha256") == report["script_sha256"]
                    and previous.get("saved") == list(audit.MONTAGES), "冷读必须消费同版工具的三 AM 完整创建报告")
            settings = previous["settings"]
            protected += [audit.package_file(package).with_suffix(suffix) for package in audit.MONTAGES
                          for suffix in (".uasset", ".uexp", ".ubulk")]
        report["settings"] = settings
        report["baseline_report_sha256"] = audit.sha(Path(args.baseline))
        report["protected_before"] = {str(path): file_state(path) for path in protected}
        if args.mode == "cold":
            require(all(file_state(Path(path)) == state for path, state in previous["target_disk_after"].items()),
                    "已创建 AM/sidecar 与生产冻结身份不符；不覆盖或恢复")
        # 相同六源的再次原生只读校验，允许独立已编译 DLL 更新；源包不得变化。
        for path, state in previous["protected_after"].items():
            if path in report["protected_before"] and not (args.mode == "create" and path.lower().endswith(".dll")):
                require(report["protected_before"][path] == state, "前阶段已存源／保护包变化：" + path)
        if args.mode == "create":
            fresh = validate_source_contract(audit.run(str(output / "Preflight"), os.getpid()), audit)
            report["preflight_report"] = str(output / "Preflight/readback.json")
            for package in audit.SEQUENCES:
                before = previous["reads"]["sequence:" + package]["value"]
                now = fresh["reads"]["sequence:" + package]["value"]
                for key in ("skeleton", "duration_seconds", "rate_scale", "model_rate", "target_sampling_rate", "frames", "keys",
                            "bone_tracks", "properties", "float_curves"):
                    require(before[key] == now[key], "前阶段原生源事实变化：" + package + "/" + key)
        library = ue.GGYGOLinearMontageAuthorLibrary
        for family, target, main, end in zip(audit.FAMILIES, audit.MONTAGES, audit.SEQUENCES[::2], audit.SEQUENCES[1::2]):
            sources = [ue.load_asset(package) for package in (main, end)]
            require(all(isinstance(source, ue.AnimSequence) and source.get_path_name() == package + "." + package.rsplit("/", 1)[1]
                        for source, package in zip(sources, (main, end))), "准确六源加载转向／类型错误")
            if args.mode == "create":
                require(all(file_state(path) == state for path, state in
                            ((Path(path), state) for path, state in report["protected_before"].items())), "创建前保护文件变化")
                require(not any(audit.package_file(target).with_suffix(suffix).exists() for suffix in (".uasset", ".uexp", ".ubulk")),
                        "候选包／sidecar 在本次创建前出现")
                factory = ue.AnimMontageFactory()
                factory.set_editor_property("source_animation", sources[0])
                montage = ue.AssetToolsHelpers.get_asset_tools().create_asset(target.rsplit("/", 1)[1], target.rsplit("/", 1)[0], ue.AnimMontage, factory)
                require(isinstance(montage, ue.AnimMontage) and montage.get_path_name() == target + "." + target.rsplit("/", 1)[1], "factory 没有创建准确 AM")
                report["created"].append(target)
                result = library.author_new_montage(montage, SLOT, sources, list(SECTION_NAMES))
                require(result.succeeded, "原生制作失败：" + str(result.error))
                for name, value in (("rate_scale", 1.0), ("loop", False), ("enable_auto_blend_out", True), ("blend_out_trigger_time", 0.0)):
                    montage.set_editor_property(name, value)
                for name in ("blend_in", "blend_out"):
                    blend = montage.get_editor_property(name)
                    blend.set_editor_property("blend_time", settings[name])
                    blend.set_editor_property("blend_option", ue.AlphaBlendOption.HERMITE_CUBIC)
                    montage.set_editor_property(name, blend)
                native_snapshot(montage, sources, settings, output / (family + "_before_save.t3d"))
                require(all(file_state(Path(path)) == state for path, state in report["protected_before"].items()), "保存前保护文件变化")
                require(not any(audit.package_file(target).with_suffix(suffix).exists() for suffix in (".uasset", ".uexp", ".ubulk")),
                        "保存前候选包／sidecar 出现；拒绝覆盖")
                require(ue.EditorAssetLibrary.save_loaded_asset(montage, only_if_is_dirty=False), "新 AM 保存失败")
                require(audit.package_file(target).is_file(), "save 返回成功但准确包缺失")
                report["saved"].append(target)
            else:
                montage = ue.load_asset(target)
                require(isinstance(montage, ue.AnimMontage) and montage.get_path_name() == target + "." + target.rsplit("/", 1)[1], "冷加载不是准确 AM")
            report["readbacks"][target] = native_snapshot(montage, sources, settings, output / (family + "_readback.t3d"))
            if args.mode == "cold":
                for key in ("object", "length", "section_starts", "native_sections", "segments", "source_objects", "settings"):
                    require(report["readbacks"][target][key] == previous["readbacks"][target][key], "冷读与创建读回不一致：" + target + "/" + key)
    except Exception as error:
        report["errors"].append({"error": str(error), "traceback": traceback.format_exc()})
        ue.log_error("[Animation.SkillMontages] " + str(error))
    finally:
        try:
            report["dirty_after"] = dirty()
            report["protected_after"] = {path: file_state(Path(path)) for path in report["protected_before"]}
            report["target_disk_after"] = {str(audit.package_file(package).with_suffix(suffix)):
                                          file_state(audit.package_file(package).with_suffix(suffix))
                                          for package in audit.MONTAGES for suffix in (".uasset", ".uexp", ".ubulk")}
        except Exception as error:
            report["errors"].append({"operation": "final_protection", "error": str(error), "traceback": traceback.format_exc()})
        report["changed_files"] = [path for path, state in report["protected_before"].items() if report["protected_after"].get(path) != state]
        report["success"] = (not report["errors"] and not report["changed_files"] and len(report["readbacks"]) == 3
                             and report["dirty_after"] == {"content": [], "maps": []}
                             and (args.mode == "cold" or report["saved"] == list(audit.MONTAGES)))
        (output / "readback.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        ue.log("[Animation.SkillMontages] " + json.dumps({"success": report["success"], "saved": report["saved"],
               "errors": len(report["errors"]), "changed_files": report["changed_files"], "output": str(output)}, ensure_ascii=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("create", "cold"), required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-pid", type=int, required=True)
    parser.add_argument("--blend-in", type=float)
    parser.add_argument("--blend-out", type=float)
    arguments = parser.parse_args()
    if arguments.mode == "create" and (arguments.blend_in is None or arguments.blend_out is None):
        parser.error("create 必须显式给出 blend 参数")
    require(run(arguments)["success"], "制作／冷读失败；保留真实报告和新包，不自动重试")
