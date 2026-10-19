"""@file wire_pyrios_skill_inputs.py
@brief 为 Pyrios 三个动作配置独立 E/R/F 输入；导入不执行 UE 操作。

audit 只读；create 只创建三 IA、追加原 InputConfig/IMC；cold 独立只读。
执行须由统筹安排原生窗口及同版 native Tag DLL。工具不启动/关闭 UE，
不改 GA/AbilitySet，不注入按键，不保存地图或恢复延期 Dodge 接口。
失败保留真实已存/脏状态与备份，不自动撤回、删除、SaveAll 或补成功。
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import traceback


PROJECT = Path(os.path.abspath(__file__)).parents[2]
SCHEMA = "PyriosSkillInputs/v1"
FAMILIES = ("Special", "ExSpecial", "Rush")
KEYS = ("E", "R", "F")
TAGS = tuple("InputTag.Attack." + name for name in FAMILIES)
ACTIONS = tuple("/Game/Input/Actions/IA_Attack_" + name for name in FAMILIES)
CONFIG = "/Game/Characters/Player/Pyrios/DA/DA_InputConfig_Default"
CONTEXT = "/Game/Input/Mappings/IMC_Default"
TARGETS = (*ACTIONS, CONFIG, CONTEXT)
BASE_HASHES = {
    CONFIG: "D9AF148ECB6F0AB6653DF89B4AE5BE7164F2E7F79B5E8816813BF221EBD48DBE",
    CONTEXT: "5152A4C51AA35DDDBD99E5FEF2A71276BA5C6BF9F2D01D75731C6A214919C493",
}
PROTECTED_PACKAGES = (CONFIG, CONTEXT, "/Game/Input/Actions/IA_Attack",
    "/Game/Input/Mappings/IMC_MouseLook", "/Game/BP/Character/Player/BP_PC_Pyrios",
    *tuple("/Game/Characters/Player/Pyrios/DA/" + name for name in
           ("DA_Pawn_Pyrios", "DA_AbilitySet_Pyrios", "DA_AbilitySet_Common")),
    "/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo", *ACTIONS)
SOURCE_PATHS = tuple("Source/GGYGO/" + path for path in (
    "System/GGYGOGameplayTags.h", "System/GGYGOGameplayTags.cpp",
    "Input/GGYGOPlayerInput.h", "Input/GGYGOPlayerInput.cpp",
    "Character/Components/GGYGOHeroComponent.h", "Character/Components/GGYGOHeroComponent.cpp"))


def require(condition, reason):
    if not condition:
        raise RuntimeError("Input.PyriosSkill: " + reason)


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest().upper()


def object_path(package):
    return package + "." + package.rsplit("/", 1)[1]


def package_file(package):
    require(package.startswith("/Game/") and ".." not in package, "非工程包路径")
    return PROJECT / "Content" / (package[6:] + ".uasset")


def saved_path(value):
    path = Path(os.path.abspath(PROJECT / value))
    root = Path(os.path.abspath(PROJECT / "Saved"))
    require(root in path.parents, "报告须在工程 Saved 内")
    for ancestor in (path, *path.parents):
        if ancestor.exists():
            require(not ancestor.lstat().st_file_attributes & stat.FILE_ATTRIBUTE_REPARSE_POINT,
                    "报告路径包含链接或重解析点：" + str(ancestor))
        if ancestor == root:
            break
    return path


def file_states():
    paths = [package_file(package).with_suffix(suffix)
             for package in PROTECTED_PACKAGES for suffix in (".uasset", ".uexp", ".ubulk")]
    paths += [PROJECT / path for path in SOURCE_PATHS]
    paths += [PROJECT / "Binaries/Win64" / ("UnrealEditor-" + module + ".dll")
              for module in ("GGYGO", "GGYGOEditor")]
    return {str(path): digest(path) if path.is_file() else None for path in paths}


def unowned_changes(before, after, writable):
    return sorted(path for path in before.keys() | after.keys()
                  if path not in writable and before.get(path) != after.get(path))


def dirty(ue):
    utils = ue.EditorLoadingAndSavingUtils
    return {"content": sorted(p.get_path_name() for p in utils.get_dirty_content_packages()),
            "maps": sorted(p.get_path_name() for p in utils.get_dirty_map_packages())}


def registered_tag(ue, name):
    tag = ue.GameplayTag()
    require(tag.import_text('(TagName="' + name + '")')
            and ue.GameplayTagLibrary.is_gameplay_tag_valid(tag)
            and str(ue.GameplayTagLibrary.get_tag_name(tag)) == name,
            "同版 native Tag 未就绪：" + name)
    return tag


def load_exact(ue, package, asset_type):
    asset = ue.load_asset(package)
    require(isinstance(asset, asset_type) and asset.get_path_name() == object_path(package),
            "准确资产缺失或类型不符：" + package)
    return asset


def require_unused_action(ue, package):
    require(all(not package_file(package).with_suffix(suffix).exists()
                for suffix in (".uasset", ".uexp", ".ubulk"))
            and not ue.EditorAssetLibrary.does_asset_exist(package)
            and ue.find_object(None, object_path(package)) is None,
            "目标 IA 已存或在内存中，拒绝覆盖：" + package)


def ability_binding(ue, row):
    action = row.get_editor_property("input_action")
    return {"action": action.get_path_name() if action else None,
            "tag": str(ue.GameplayTagLibrary.get_tag_name(row.get_editor_property("input_tag")))}


def mapping_rows(context):
    return list(context.get_editor_property("default_key_mappings").get_editor_property("mappings"))


def mapping_snapshot(row):
    action = row.get_editor_property("action")
    return {"action": action.get_path_name() if action else None,
            "key": str(row.get_editor_property("key").get_editor_property("key_name")),
            "export": row.export_text()}


def snapshot(ue, config, context):
    properties = ("registration_tracking_mode", "context_description", "input_mode_filter_options",
                  "input_mode_query_override")
    settings = {}
    for name in properties:
        value = context.get_editor_property(name)
        settings[name] = value.export_text() if hasattr(value, "export_text") else str(value)
    settings["mapping_profile_overrides"] = {
        str(key): value.export_text() for key, value in context.get_editor_property("mapping_profile_overrides").items()}
    return {"native": [row.export_text() for row in config.get_editor_property("native_input_actions")],
            "ability": [row.export_text() for row in config.get_editor_property("ability_input_actions")],
            "ability_bindings": [ability_binding(ue, row) for row in config.get_editor_property("ability_input_actions")],
            "mappings": [mapping_snapshot(row) for row in mapping_rows(context)], "settings": settings}


def validate_original(before):
    require(len(before["native"]) == 4 and len(before["ability"]) == 4
            and len(before["mappings"]) == 15, "原输入数组基线数量不符")
    require(not any(row["key"] in KEYS or row["action"] in map(object_path, ACTIONS)
                    for row in before["mappings"]), "三入口已被占用或已接入")
    require(len(before["ability_bindings"]) == 4
            and not any(row["tag"] in TAGS or row["action"] in map(object_path, ACTIONS)
                        for row in before["ability_bindings"]), "三 Tag/IA 已存在于原能力输入")
    require(not before["settings"]["mapping_profile_overrides"],
            "存在需单独收敛的 profile override，不能绕过三入口检查")


def validate_append(before, after, addition_exports):
    require(after["native"] == before["native"] and after["settings"] == before["settings"],
            "Native 输入或 IMC 策略被改变")
    require(after["ability"] == before["ability"] + addition_exports, "原能力输入被改写或追加不符")
    require(after["ability_bindings"] == before["ability_bindings"]
            + [{"action": object_path(package), "tag": tag} for package, tag in zip(ACTIONS, TAGS)],
            "三 IA 与 Tag 未精确配对")
    rows = after["mappings"]
    require(len(rows) == len(before["mappings"]) + 3 and rows[:-3] == before["mappings"],
            "原 mapping 被改变或追加数量不符")
    require([(row["key"], row["action"]) for row in rows[-3:]]
            == list(zip(KEYS, map(object_path, ACTIONS))), "E/R/F 与动作未精确配对")


def action_snapshot(ue, action):
    values = {name: action.get_editor_property(name) for name in
              ("value_type", "consume_input", "trigger_when_paused", "triggers", "modifiers",
               "consumes_action_and_axis_mappings", "reserve_all_mappings", "accumulation_behavior",
               "player_mappable_key_settings")}
    require(values["value_type"] == ue.InputActionValueType.BOOLEAN
            and values["consume_input"] and not values["trigger_when_paused"]
            and not values["triggers"] and not values["modifiers"], "IA 不是无额外触发器的 Boolean 输入")
    require(not values["consumes_action_and_axis_mappings"] and not values["reserve_all_mappings"]
            and values["accumulation_behavior"] == ue.InputActionAccumulationBehavior.TAKE_HIGHEST_ABSOLUTE_VALUE
            and values["player_mappable_key_settings"] is None, "IA 含非本次约定的消费/累积/重映射策略")
    return {"object": action.get_path_name(), "value_type": str(values["value_type"]),
            "consume_input": bool(values["consume_input"]), "trigger_when_paused": False,
            "triggers": [], "modifiers": [], "consumes_action_and_axis_mappings": False,
            "reserve_all_mappings": False, "accumulation_behavior": str(values["accumulation_behavior"]),
            "player_mappable_key_settings": None}


def previous_create(filename, current_pid):
    path = saved_path(filename)
    report = json.loads(path.read_text(encoding="utf-8"))
    host = json.loads((path.parent / "host_exit.json").read_text(encoding="utf-8"))
    require(report.get("schema") == SCHEMA and report.get("mode") == "create"
            and report.get("success") is True and report.get("saved") == list(TARGETS),
            "前阶段五包创建未完整成功")
    require(type(report.get("pid")) is int and report["pid"] > 0 and report["pid"] != current_pid
            and type(host.get("pid")) is int and host["pid"] == report["pid"] and type(host.get("exit_code")) is int
            and host["exit_code"] == 0 and host.get("report_sha256", "").upper() == digest(path),
            "独立 Cold 缺少准确父报告及真实 exit0")
    return report


def run(mode, output, previous=None):
    require(mode in ("audit", "create", "cold") and (mode == "cold") == (previous is not None),
            "模式或前阶段参数不符")
    output = saved_path(output)
    require(not output.exists(), "结果文件已存在，不覆盖")
    output.parent.mkdir(parents=True, exist_ok=True)
    report = {"schema": SCHEMA, "mode": mode, "pid": os.getpid(), "success": False,
              "created": [], "saved": [], "backups": {}, "errors": [], "targets": list(TARGETS),
              "tags": list(TAGS), "keys": list(KEYS), "protected_before": {}, "protected_after": {}}
    writable = {str(package_file(package).with_suffix(suffix)) for package in TARGETS
                for suffix in (".uasset", ".uexp", ".ubulk")} if mode == "create" else set()
    ue = None
    try:
        import unreal as ue
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        require(editor.get_game_world() is None, "PIE 正在运行")
        report["dirty_before"] = dirty(ue)
        require(not any(report["dirty_before"].values()), "存在用户或外部脏包，停止且不保存")
        report["protected_before"] = file_states()
        for path in SOURCE_PATHS:
            require(report["protected_before"][str(PROJECT / path)] is not None, "原输入/Tag 源缺失")
        for module in ("GGYGO", "GGYGOEditor"):
            require(report["protected_before"][str(PROJECT / "Binaries/Win64" /
                    ("UnrealEditor-" + module + ".dll"))] is not None, "准确 DLL 缺失")
        prior = previous_create(previous, report["pid"]) if mode == "cold" else None
        if prior:
            require(report["protected_before"] == prior["protected_after"], "创建后的包/源/DLL 身份变化")
        else:
            for package, expected in BASE_HASHES.items():
                require(digest(package_file(package)) == expected, "原输入磁盘基线变化：" + package)
            for package in ACTIONS:
                require_unused_action(ue, package)
        tags = [registered_tag(ue, name) for name in TAGS]
        config = load_exact(ue, CONFIG, ue.GGYGOInputConfig)
        context = load_exact(ue, CONTEXT, ue.InputMappingContext)
        before = prior["before"] if prior else snapshot(ue, config, context)
        validate_original(before)
        report["before"] = before
        original_rows = list(config.get_editor_property("ability_input_actions"))
        if mode == "create":
            backup = output.parent / "Backups"
            backup.mkdir(exist_ok=False)
            for package in (CONFIG, CONTEXT):
                for suffix in (".uasset", ".uexp", ".ubulk"):
                    source = package_file(package).with_suffix(suffix)
                    if source.exists():
                        target = backup / (package.rsplit("/", 1)[1] + suffix)
                        shutil.copyfile(source, target)
                        require(digest(target) == digest(source), "精确备份不符")
                        report["backups"][str(source)] = {"path": str(target), "sha256": digest(target)}
        actions, additions = [], []
        expected_files = report["protected_before"]
        for package, tag in zip(ACTIONS, tags):
            if mode == "create":
                require(file_states() == expected_files, "创建前磁盘保护发生变化")
                require_unused_action(ue, package)
                action = ue.AssetToolsHelpers.get_asset_tools().create_asset(package.rsplit("/", 1)[1],
                    package.rsplit("/", 1)[0], ue.InputAction, ue.InputAction_Factory())
                require(isinstance(action, ue.InputAction) and action.get_path_name() == object_path(package),
                        "准确 IA Factory 创建失败")
                report["created"].append(package)
                for name, value in (("value_type", ue.InputActionValueType.BOOLEAN), ("consume_input", True),
                                    ("trigger_when_paused", False), ("triggers", []), ("modifiers", [])):
                    action.set_editor_property(name, value)
            elif mode == "cold":
                action = load_exact(ue, package, ue.InputAction)
            else:
                continue
            action_snapshot(ue, action)
            actions.append(action)
            additions.append(ue.GGYGOInputAction(input_action=action, input_tag=tag))
        if mode != "audit":
            addition_exports = [row.export_text() for row in additions]
            if mode == "create":
                require(snapshot(ue, config, context) == before, "追加前原输入内存变化")
                config.set_editor_property("ability_input_actions", original_rows + additions)
                for action, name in zip(actions, KEYS):
                    key = ue.Key()
                    key.set_editor_property("key_name", name)
                    context.map_key(action, key)
            after = snapshot(ue, config, context)
            validate_append(before, after, addition_exports)
            for row in mapping_rows(context)[-3:]:
                require(not row.get_editor_property("modifiers") and not row.get_editor_property("triggers"),
                        "新 mapping 不能含隐含修饰器/触发器")
            report["after"] = after
            report["actions"] = [action_snapshot(ue, action) for action in actions]
            if mode == "create":
                for package, asset in zip(TARGETS, [*actions, config, context]):
                    require(file_states() == expected_files, "保存前磁盘保护发生变化")
                    require(snapshot(ue, config, context) == after
                            and [action_snapshot(ue, action) for action in actions] == report["actions"],
                            "保存前输入内存变化")
                    now_dirty = dirty(ue)
                    require(not now_dirty["maps"] and set(now_dirty["content"]).issubset(TARGETS), "出现非所属脏包")
                    require(ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), "单包保存失败：" + package)
                    require(package_file(package).is_file(), "保存返回成功但准确包缺失：" + package)
                    report["saved"].append(package)
                    saved_files = file_states()
                    single_package = {str(package_file(package).with_suffix(suffix))
                                      for suffix in (".uasset", ".uexp", ".ubulk")}
                    require(not unowned_changes(expected_files, saved_files, single_package), "单包保存越过准确目标")
                    expected_files = saved_files
                require(snapshot(ue, config, context) == after
                        and [action_snapshot(ue, action) for action in actions] == report["actions"],
                        "保存后输入字段变化")
            else:
                require(report["after"] == prior["after"] and report["actions"] == prior["actions"],
                        "独立 Cold 与创建字段不一致")
    except Exception as error:
        report["errors"].append({"error": str(error), "traceback": traceback.format_exc()})
    finally:
        report["changed_unowned"] = None
        report["dirty_after"] = None
        try:
            report["protected_after"] = file_states() if report["protected_before"] else {}
            report["changed_unowned"] = unowned_changes(report["protected_before"], report["protected_after"], writable)
        except Exception as error:
            report["errors"].append({"stage": "保护收尾", "error": str(error), "traceback": traceback.format_exc()})
        try:
            if ue is not None:
                report["dirty_after"] = dirty(ue)
        except Exception as error:
            report["errors"].append({"stage": "脏包收尾", "error": str(error), "traceback": traceback.format_exc()})
        report["success"] = not report["errors"] and not report["changed_unowned"] \
            and report["dirty_after"] == {"content": [], "maps": []} \
            and (mode != "create" or report["saved"] == list(TARGETS))
        with output.open("x", encoding="utf-8", newline="\n") as stream:
            json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
            stream.write("\n")
    require(report["success"], "实际阶段失败，保留报告与已存/脏状态：" + str(output))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("audit", "create", "cold"))
    parser.add_argument("--output", required=True)
    parser.add_argument("--previous", help="cold 消费准确 create 报告及同目录真实 host_exit.json")
    args = parser.parse_args()
    run(args.mode, args.output, args.previous)


if __name__ == "__main__":
    main()
