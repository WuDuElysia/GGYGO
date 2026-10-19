"""@file wire_pyrios_skill_actions.py
@brief 为已冷读的三个 Pyrios 完整动作创建单步 GA，并追加既有授予表。

create 只写三个新 GA 和 DA_AbilitySet_Pyrios；cold 在另一宿主只读。
消费真实正常退出的 AM 来源、同工程 Input 冷读／GA 创建凭据。
显式核对当前宿主已加载 DLL 路径及磁盘版本，保留原四能力及其它包。
不启动 UE，不配置新命中、取消或 FX 窗；执行／姿态／输入验证另行完成。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import traceback


PROJECT = Path(__file__).resolve().parents[2]
SCHEMA = "PyriosSkillActions/v2"
BASE = "/Game/Characters/Player/Pyrios/"
FAMILIES = ("Special", "ExSpecial", "Rush")
GAS = tuple(BASE + "Abilities/GA_Pyrios_Attack_" + family + "_01" for family in FAMILIES)
AMS = tuple(BASE + "Animation/Attack/AM_Pyrios_Attack_" + family + "_01" for family in FAMILIES)
ABILITY_SET = BASE + "DA/DA_AbilitySet_Pyrios"
NORMAL_GA = BASE + "Abilities/GA_Pyrios_Attack_Combo"
PAWN_DATA = BASE + "DA/DA_Pawn_Pyrios"
AM_COLD_SHA = "4CB3944ED7CC698D9F8DEE8E71CE32C0285CC1B0586B7767D12590AB974FC837"
EXISTING_SET_SHA = "FE5D803B0F6CB587DB8E54CC45288790BBE17ABBD89AD8587A87DAF2F2C51A40"
ORIGINAL_ABILITIES = (
    NORMAL_GA + ".GA_Pyrios_Attack_Combo_C",
    "/Game/Characters/Shared/Abilities/GA_Dodge.GA_Dodge_C",
    "/Game/Characters/Shared/Abilities/HitReact/GA_HitReact.GA_HitReact_C",
    "/Game/Characters/Shared/Abilities/GA_Death.GA_Death_C",
)
ORIGINAL_INPUTS = ("InputTag.Attack.Light", "InputTag.Dodge", "None", "None")


def require(condition, reason):
    if not condition:
        raise RuntimeError("Combat.SkillActions: " + reason)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def saved_path(value):
    path = (PROJECT / value).resolve()
    require(path.is_relative_to((PROJECT / "Saved").resolve()), "报告须在本工程 Saved")
    return path


def package_file(package):
    require(package.startswith("/Game/") and ".." not in package, "非工程包")
    return PROJECT / "Content" / (package[6:] + ".uasset")


def object_path(package):
    return package + "." + package.rsplit("/", 1)[1]


def validate_input_names(names):
    require(len(names) == 3 and len(set(names)) == 3, "须提供三个不同的原 Input 作者确认 Tag")
    require(all(re.fullmatch(r"InputTag\.[A-Za-z0-9_]+(?:\.[A-Za-z0-9_]+)*", name) for name in names),
            "输入 Tag 格式无效")
    require(not set(names).intersection(ORIGINAL_INPUTS), "不能复用原普攻或 Dodge 的输入 Tag")
    return list(names)


def receipt_path(value, root=None):
    root = (root or PROJECT).resolve()
    path = (root / value).resolve()
    require(path.is_relative_to(root / "Saved"), "收据须在明确来源工程的 Saved")
    return path


def receipt(filename, schema, current_pid, root=None):
    filename = receipt_path(filename, root)
    report = json.loads(filename.read_text(encoding="utf-8"))
    exit_report = json.loads((filename.parent / "host_exit.json").read_text(encoding="utf-8"))
    require(report.get("schema") == schema and report.get("success") is True, "前阶段报告未成功")
    require(type(report.get("pid")) is int and report["pid"] != current_pid, "须独立宿主读回")
    require(exit_report.get("pid") == report["pid"] and type(exit_report.get("exit_code")) is int
            and exit_report["exit_code"] == 0
            and str(exit_report.get("report_sha256", "")).upper() == digest(filename),
            "缺少准确真实 exit0 或报告身份不符")
    return report


def loaded_modules(expected_hashes):
    """只查询本宿主已加载模块，不加载 DLL；路径与当下磁盘版本必须匹配。"""
    import ctypes
    from ctypes import wintypes
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    kernel.GetModuleHandleW.restype = wintypes.HMODULE
    kernel.GetModuleFileNameW.argtypes = [wintypes.HMODULE, wintypes.LPWSTR, wintypes.DWORD]
    kernel.GetModuleFileNameW.restype = wintypes.DWORD
    result = {}
    for module, expected in expected_hashes.items():
        require(re.fullmatch(r"[0-9A-Fa-f]{64}", expected or "") is not None, "须显式提供本次 DLL SHA")
        name = "UnrealEditor-" + module + ".dll"
        handle = kernel.GetModuleHandleW(name)
        require(handle, "本宿主未加载必需模块：" + name)
        buffer = ctypes.create_unicode_buffer(32768)
        length = kernel.GetModuleFileNameW(handle, buffer, len(buffer))
        require(0 < length < len(buffer), "无法读完整已加载模块路径：" + name)
        path = Path(buffer.value).resolve()
        require(path == (PROJECT / "Binaries/Win64" / name).resolve(), "已加载模块不属于实际执行工程：" + name)
        sha = digest(path)
        require(sha == expected.upper(), "已加载模块的磁盘版本不匹配：" + name)
        result[module] = {"path": str(path), "sha256": sha}
    return result


def check_digest_states(states, excluded=()):
    require(isinstance(states, dict) and bool(states), "缺少 Input Cold 保护条目")
    excluded_paths = {Path(raw).resolve() for raw in excluded}
    for raw, expected in states.items():
        path = Path(raw).resolve()
        require(path.is_relative_to(PROJECT.resolve()), "保护路径不属于实际执行工程：" + raw)
        require(expected is None or (isinstance(expected, str)
                and re.fullmatch(r"[0-9A-Fa-f]{64}", expected) is not None), "保护 SHA 格式无效：" + raw)
        if path in excluded_paths:
            continue
        require(path.is_file() == (expected is not None)
                and (expected is None or digest(path) == expected.upper()), "输入 Cold 后保护身份变化：" + raw)


def bind_asset_sources(report, origin):
    """原 Cold 仅为来源；在实际工程重绑并核每个源包，不改旧收据。"""
    origin = origin.resolve()
    require((origin / "GGYGO.uproject").is_file(), "AM 来源工程缺失")
    result = {}
    for raw, state in source_files(report).items():
        path = Path(raw).resolve()
        require(path.is_relative_to(origin / "Content"), "AM 来源保护条目越出来源 Content")
        target = (PROJECT / path.relative_to(origin)).resolve()
        require(target.is_relative_to((PROJECT / "Content").resolve()), "实际源包路径越界")
        result[str(target)] = dict(state)
    require(result, "缺少真实 AM/AS/骨架来源保护")
    check_source_files(result)
    return result


def file_states():
    # 集成点保护实际已存包；不依靠 Registry 列表推断文件不存在。
    content = PROJECT / "Content"
    paths = sorted(path for path in content.rglob("*") if path.suffix in (".uasset", ".uexp", ".ubulk", ".umap"))
    paths += [PROJECT / "Binaries/Win64" / ("UnrealEditor-" + name + ".dll") for name in ("GGYGO", "GGYGOEditor")]
    return {str(path): digest(path) for path in paths}


def unowned_changes(before, after, writable):
    return sorted(path for path in before.keys() | after.keys()
                  if path not in writable and before.get(path) != after.get(path))


def dirty(ue):
    return {"content": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()),
            "maps": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages())}


def native_valid(ue, obj):
    # UE 的 Blueprint::IsDataValid 调用真实 GeneratedClass CDO::IsDataValid。
    subsystem = ue.get_editor_subsystem(ue.EditorValidatorSubsystem)
    result, errors, warnings = subsystem.is_object_valid(obj, ue.DataValidationUsecase.MANUAL)
    require(result == ue.DataValidationResult.VALID and not errors and not warnings,
            "原生配置校验未严格通过：" + obj.get_path_name() + "; " + str((result, errors, warnings)))


def load_exact(ue, package, asset_type):
    obj = ue.load_asset(package)
    require(isinstance(obj, asset_type) and obj.get_path_name() == object_path(package), "准确对象缺失：" + package)
    return obj


def compiled_cdo(ue, bp):
    require(bp.get_blueprint_parent_class() == ue.GGYGOPlayerComboAbility.static_class(), "GA 父类不符")
    require(bp.get_editor_property("status") == ue.BlueprintStatus.BS_UP_TO_DATE, "GA 未无警告编译")
    cls = bp.generated_class()
    require(cls is not None, "GA GeneratedClass 缺失")
    return ue.get_default_object(cls)


def tag(ue, name):
    value = ue.GameplayTag()
    require(value.import_text('(TagName="' + name + '")')
            and ue.GameplayTagLibrary.is_gameplay_tag_valid(value)
            and str(ue.GameplayTagLibrary.get_tag_name(value)) == name, "真实 Tag 未注册：" + name)
    return value


def montage_snapshot(ue, montage, expected):
    sources = [ue.load_asset(path) for path in expected["source_objects"]]
    require(all(isinstance(source, ue.AnimSequence) for source in sources), "AM 完整源缺失")
    result = ue.GGYGOLinearMontageAuthorLibrary.validate_montage(montage, "FullBody", sources, ["Main", "End"])
    require(result.succeeded and float(result.duration_seconds) == expected["length"]
            and list(result.section_starts) == expected["section_starts"], "原生 AM 完整时域变化：" + str(result.error))
    tracks = montage.get_editor_property("slot_anim_tracks")
    segments = tracks[0].get_editor_property("anim_track").get_editor_property("anim_segments")
    require([segment.export_text() for segment in segments] == expected["segments"], "AM 原生段变化")
    require(montage.get_editor_property("rate_scale") == 1.0 and not montage.get_editor_property("loop")
            and montage.get_editor_property("enable_auto_blend_out") is True
            and montage.get_editor_property("blend_out_trigger_time") == 0.0
            and not ue.AnimationLibrary.get_animation_notify_events(montage), "AM 自然退出／无窗口合同变化")
    for name in ("blend_in", "blend_out"):
        blend = montage.get_editor_property(name)
        require(blend.get_editor_property("blend_time") == expected["settings"][name]
                and blend.get_editor_property("blend_option") == ue.AlphaBlendOption.HERMITE_CUBIC, "AM blend 变化")
    return {"object": montage.get_path_name(), "length": float(result.duration_seconds),
            "section_starts": list(result.section_starts), "segments": [segment.export_text() for segment in segments]}


def source_files(report):
    """前阶段已冻结源包保持；允许根正常批量编译更新 DLL。"""
    return {path: state for path, state in report["protected_after"].items() if not path.lower().endswith(".dll")}


def check_source_files(states):
    require(isinstance(states, dict) and bool(states), "缺少 AM／AS／骨架保护条目")
    for raw, state in states.items():
        path = Path(raw).resolve()
        require(path.is_relative_to((PROJECT / "Content").resolve()), "源保护路径越出实际 Content：" + raw)
        require(isinstance(state, dict) and type(state.get("exists")) is bool, "源保护状态格式无效：" + raw)
        sha = state.get("sha256")
        require(not state["exists"] or (isinstance(sha, str)
                and re.fullmatch(r"[0-9A-Fa-f]{64}", sha) is not None), "源保护 SHA 格式无效：" + raw)
        require(path.is_file() == state["exists"]
                and (not state["exists"] or digest(path) == sha.upper()), "原 AM／AS／骨架保护文件变化：" + raw)


def grant_snapshot(ue, asset):
    return {"abilities": [row.export_text() for row in asset.get_editor_property("GrantedGameplayAbilities")],
            "effects": [row.export_text() for row in asset.get_editor_property("GrantedGameplayEffects")],
            "attributes": [row.export_text() for row in asset.get_editor_property("GrantedAttributes")]}


def inspect_original_grants(ue, asset):
    rows = list(asset.get_editor_property("GrantedGameplayAbilities"))
    require(len(rows) == 4, "授予表不是准确原四项；拒绝覆盖")
    for row, cls, input_name in zip(rows, ORIGINAL_ABILITIES, ORIGINAL_INPUTS):
        require(row.get_editor_property("Ability").get_path_name() == cls
                and row.get_editor_property("AbilityLevel") == 1
                and str(ue.GameplayTagLibrary.get_tag_name(row.get_editor_property("InputTag"))) == input_name,
                "原授予接口变化")
    return rows


def values(ue, montage, shape):
    step = ue.GGYGOComboStep(montage=montage, main_section="Main", end_section="End", motion_slot_name="FullBody",
                           motion_translation_scale=1.0, next_step_index=-1,
                           interruption_mode=ue.GGYGOActionInterruptionMode.DISABLED, interruption_notify_name="None",
                           # 攻击接续与移动打断两门都显式 Disabled/None，锁到自然结束；不依赖新字段默认值。
                           movement_interruption_mode=ue.GGYGOActionInterruptionMode.DISABLED,
                           movement_interruption_notify_name="None",
                           play_rate=1.0, damage=0.0, poise_damage=0.0, trace_shape=shape,
                           fx=ue.GGYGOComboStepFX(mode=ue.GGYGOComboFXMode.DISABLED))
    owned = ue.GameplayTagContainer()
    blocked = ue.GameplayTagContainer()
    require(owned.import_text('(GameplayTags=((TagName="State.Attacking")))')
            and blocked.import_text('(GameplayTags=((TagName="State.Dead"),(TagName="Restriction.CantAttack"),(TagName="State.Attacking")))'),
            "原生技能占用／阻断 Tag 构造失败")
    for name in ("State.Attacking", "State.Dead", "Restriction.CantAttack"):
        tag(ue, name)
    # 使用现有 Skill 优先级和 GAS Exclusive 仲裁保护玩家动作；死亡／故障仍走原生强制退出。
    return {"combo_steps": [step], "activation_policy": ue.GGYGOAbilityActivationPolicy.ON_INPUT_TRIGGERED,
            "group_tag": tag(ue, "AbilityGroup.Attack"), "activation_priority": 400,
            "self_policy": ue.GGYGOAbilitySelfPolicy.EXCLUSIVE, "activation_owned_tags": owned,
            "activation_blocked_tags": blocked, "damage_effect": None,
            "use_shared_damage_effect_when_unset": False, "additional_costs": [],
            "cost_gameplay_effect_class": None, "cooldown_gameplay_effect_class": None}


def ability_snapshot(ue, bp, expected):
    cdo = compiled_cdo(ue, bp)
    native_valid(ue, bp)
    result = {"parent": bp.get_blueprint_parent_class().get_path_name(), "class": bp.generated_class().get_path_name()}
    for name, value in expected.items():
        actual = cdo.get_editor_property(name)
        if name == "combo_steps":
            actual = [step.export_text() for step in actual]
            value = [step.export_text() for step in value]
        elif hasattr(value, "export_text"):
            actual, value = actual.export_text(), value.export_text()
        require(actual == value, "GA 原生字段不符：" + name)
        result[name] = actual if isinstance(actual, (list, bool, int, float, str)) or actual is None else str(actual)
    return result


def run(args):
    import unreal as ue
    require(args.expected_pid == os.getpid(), "须绑定本次独立宿主 PID")
    require(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() == PROJECT.resolve(), "宿主不是本工程")
    output = saved_path(args.output)
    require(not output.exists(), "保留旧输出；须全新目录")
    output.mkdir(parents=True)
    writable = {str(package_file(package)) for package in GAS + (ABILITY_SET,)} if args.mode == "create" else set()
    report = {"schema": SCHEMA, "mode": args.mode, "pid": os.getpid(), "success": False,
              "script_sha256": digest(__file__), "created": [], "saved": [], "readbacks": {}, "errors": [],
              "project": str(PROJECT.resolve()),
              "meaning": "单步动作资产／授予配置；输入、ActorYaw、执行、伤害、FX、姿态及画面未验"}
    before = {}
    try:
        require(dirty(ue) == {"content": [], "maps": []}, "宿主有 dirty，保留用户工作")
        require(ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world() is None, "PIE 正在运行")
        report["loaded_modules"] = loaded_modules({"GGYGO": args.expected_runtime_sha, "GGYGOEditor": args.expected_editor_sha})
        if args.mode == "create":
            origin = Path(args.asset_origin_project).resolve()
            baseline = receipt_path(args.baseline, origin)
            previous = receipt(baseline, "PyriosSkillMontages/v1", os.getpid(), origin)
            require(digest(baseline) == AM_COLD_SHA and previous["mode"] == "cold"
                    and not previous["saved"], "须消费准确三 AM 独立冷读")
            names = validate_input_names(args.input_tags)
            am_records = previous["readbacks"]
            sources = bind_asset_sources(previous, origin)
            input_path = receipt_path(args.input_cold)
            inputs = receipt(input_path, "PyriosSkillInputs/v1", os.getpid())
            require(inputs.get("mode") == "cold" and inputs.get("tags") == names
                    and inputs.get("keys") == ["E", "R", "F"]
                    and inputs.get("dirty_after") == {"content": [], "maps": []}
                    and inputs.get("changed_unowned") == [], "须消费真实 Input 五包独立 Cold")
            check_digest_states(inputs["protected_after"])
            report.update(asset_origin=str(origin), asset_receipt=str(baseline),
                          input_cold=str(input_path), input_cold_sha256=digest(input_path),
                          input_protected_files=inputs["protected_after"])
            require(digest(package_file(ABILITY_SET)) == EXISTING_SET_SHA, "原授予包身份变化，先确认原作者")
            require(not any(package_file(ABILITY_SET).with_suffix(suffix).exists() for suffix in (".uexp", ".ubulk")), "原授予存在 sidecar，先确认写入范围")
            for package in GAS:
                require(not any(package_file(package).with_suffix(suffix).exists() for suffix in (".uasset", ".uexp", ".ubulk"))
                        and not ue.EditorAssetLibrary.does_asset_exist(package)
                        and ue.find_object(None, object_path(package)) is None, "候选 GA 已存在，拒绝覆盖：" + package)
        else:
            baseline = receipt_path(args.baseline)
            previous = receipt(baseline, SCHEMA, os.getpid())
            require(previous["mode"] == "create" and previous["script_sha256"] == report["script_sha256"]
                    and previous["project"] == report["project"]
                    and previous["saved"] == list(GAS) + [ABILITY_SET], "须消费同版完整创建结果")
            names, am_records = previous["input_tags"], previous["am_baseline"]
            sources = previous["source_files"]
            check_source_files(sources)
            check_digest_states(previous["input_protected_files"], excluded=(str(package_file(ABILITY_SET)),))
            for name in ("asset_origin", "asset_receipt", "input_cold", "input_cold_sha256", "input_protected_files"):
                report[name] = previous[name]
            for path, sha in previous["written_after"].items():
                require(digest(path) == sha, "准确 GA／授予包变化，拒绝覆盖")
        report.update(input_tags=names, am_baseline=am_records, source_files=sources,
                      baseline_sha256=digest(baseline))
        before = file_states()
        if args.mode == "cold":
            require(before == previous["protected_after"]
                    and report["loaded_modules"] == previous["loaded_modules"], "创建后包或宿主 DLL 身份变化")
        report["protected_before"] = before
        ability_set = load_exact(ue, ABILITY_SET, ue.GGYGOAbilitySet)
        pawn = load_exact(ue, PAWN_DATA, ue.GGYGOPawnData)
        require(ability_set in pawn.get_editor_property("AbilitySets"), "生产 PawnData 未授予准确 AbilitySet")
        pawn_class = pawn.get_editor_property("PawnClass")
        require(pawn_class is not None, "生产 PawnClass 缺失")
        pawn_cdo = ue.get_default_object(pawn_class)
        controller_yaw = pawn_cdo.get_editor_property("use_controller_rotation_yaw")
        require(controller_yaw is False, "SourceYaw 必须由 CMC 执行；生产 Pawn CDO 的 ControllerYaw 尚未关闭，交 Animation 作者收敛")
        report["pawn_prerequisite"] = {"class": pawn_class.get_path_name(), "use_controller_rotation_yaw": controller_yaw,
                                       "scope": "CDO 条件，不证明当前 Actor 或非零曲线转向"}
        template = compiled_cdo(ue, load_exact(ue, NORMAL_GA, ue.Blueprint))
        template_steps = list(template.get_editor_property("combo_steps"))
        require(len(template_steps) == 3, "普攻模板不是原三段")
        shape = template_steps[0].get_editor_property("trace_shape")
        report["trace_shape_source"] = {"class": template.get_class().get_path_name(), "step": 0, "shape": shape.export_text()}
        montages = [load_exact(ue, package, ue.AnimMontage) for package in AMS]
        report["montages"] = {package: montage_snapshot(ue, montage, am_records[package]) for package, montage in zip(AMS, montages)}
        input_tags = [tag(ue, name) for name in names]
        original = grant_snapshot(ue, ability_set)
        if args.mode == "create":
            rows = inspect_original_grants(ue, ability_set)
            report["original_grants"] = original
            shutil.copy2(package_file(ABILITY_SET), output / "DA_AbilitySet_Pyrios_before.uasset")
            require(digest(output / "DA_AbilitySet_Pyrios_before.uasset") == EXISTING_SET_SHA, "原授予保护副本不符")
        else:
            rows = list(ability_set.get_editor_property("GrantedGameplayAbilities"))[:4]
            report["original_grants"] = previous["original_grants"]
        additions = []
        for package, montage, input_tag in zip(GAS, montages, input_tags):
            expected = values(ue, montage, shape)
            if args.mode == "create":
                factory = ue.BlueprintFactory()
                factory.set_editor_property("parent_class", ue.GGYGOPlayerComboAbility)
                bp = ue.AssetToolsHelpers.get_asset_tools().create_asset(package.rsplit("/", 1)[1], package.rsplit("/", 1)[0], ue.Blueprint, factory)
                require(isinstance(bp, ue.Blueprint) and bp.get_path_name() == object_path(package), "准确 GA factory 失败")
                report["created"].append(package)
                cdo = ue.get_default_object(bp.generated_class())
                for name, value in expected.items():
                    cdo.set_editor_property(name, value)
                ue.BlueprintEditorLibrary.compile_blueprint(bp)
            else:
                bp = load_exact(ue, package, ue.Blueprint)
            require(bp.generated_class() is not None
                    and bp.generated_class().get_path_name() == object_path(package) + "_C", "准确 GeneratedClass 身份不符")
            report["readbacks"][package] = ability_snapshot(ue, bp, expected)
            if args.mode == "create":
                require(not unowned_changes(before, file_states(), writable), "保存前非所属包变化")
                require(not any(package_file(package).with_suffix(suffix).exists() for suffix in (".uasset", ".uexp", ".ubulk")), "GA 保存前目标文件出现")
                require(ue.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False), "GA 保存失败")
                require(package_file(package).is_file(), "save 返回成功但准确 GA 包缺失")
                report["saved"].append(package)
            grant = ue.GGYGOAbilitySet_GameplayAbility()
            require(grant.import_text('(Ability="' + bp.generated_class().get_path_name() + '",AbilityLevel=1,InputTag=' + input_tag.export_text() + ')'), "原生授予构造失败")
            additions.append(grant)
        expected_grants = {**report["original_grants"], "abilities": report["original_grants"]["abilities"] + [row.export_text() for row in additions]}
        if args.mode == "create":
            require(grant_snapshot(ue, ability_set) == original and digest(package_file(ABILITY_SET)) == EXISTING_SET_SHA, "追加前原授予变化")
            ability_set.set_editor_property("GrantedGameplayAbilities", rows + additions)
        require(grant_snapshot(ue, ability_set) == expected_grants, "授予表字段未完整保留／追加不符")
        native_valid(ue, ability_set)
        report["grants"] = expected_grants
        if args.mode == "create":
            require(not unowned_changes(before, file_states(), writable), "授予保存前非所属包变化")
            require(ue.EditorAssetLibrary.save_loaded_asset(ability_set, only_if_is_dirty=False), "授予保存失败")
            require(package_file(ABILITY_SET).is_file(), "save 返回成功但准确授予包缺失")
            report["saved"].append(ABILITY_SET)
        else:
            require(report["readbacks"] == previous["readbacks"] and report["grants"] == previous["grants"]
                    and report["montages"] == previous["montages"] and report["trace_shape_source"] == previous["trace_shape_source"], "独立冷读字段变化")
    except Exception as error:
        report["errors"].append({"error": str(error), "traceback": traceback.format_exc()})
        ue.log_error(str(error))
    finally:
        try:
            after = file_states()
            report["protected_after"] = after
            report["unowned_changes"] = unowned_changes(before, after, writable) if before else []
            report["written_after"] = {path: after[path] for path in sorted(writable) if path in after}
            report["dirty_after"] = dirty(ue)
        except Exception as error:
            report["errors"].append({"operation": "final_protection", "error": str(error), "traceback": traceback.format_exc()})
            report.update(unowned_changes=[], written_after={}, dirty_after=None)
        report["success"] = (bool(before) and not report["errors"] and not report["unowned_changes"]
                             and report["dirty_after"] == {"content": [], "maps": []}
                             and len(report["readbacks"]) == 3
                             and (args.mode == "cold" or (report["saved"] == list(GAS) + [ABILITY_SET]
                                                         and len(report["written_after"]) == 4)))
        (output / "readback.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        ue.log("[Combat.SkillActions] " + json.dumps({key: report[key] for key in ("success", "saved", "errors", "unowned_changes")}, ensure_ascii=False))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("create", "cold"), required=True)
    parser.add_argument("--baseline", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--expected-pid", type=int, required=True)
    parser.add_argument("--input-tags", nargs=3)
    parser.add_argument("--asset-origin-project")
    parser.add_argument("--input-cold")
    parser.add_argument("--expected-runtime-sha", required=True)
    parser.add_argument("--expected-editor-sha", required=True)
    args = parser.parse_args()
    if args.mode == "create" and (not args.input_tags or not args.asset_origin_project or not args.input_cold):
        parser.error("create 须显式提供原 Input 三 Tag、AM 来源工程和真实 Input Cold")
    require(run(args)["success"], "创建／冷读失败；保留实际报告和包，不回滚或自动覆盖重试")
