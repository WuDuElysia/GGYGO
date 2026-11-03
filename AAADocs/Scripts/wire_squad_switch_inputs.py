"""@file wire_squad_switch_inputs.py
@brief 创建队伍换人的两个 InputAction 与 IMC_Squad（默认 Z 上一个、C 下一个），并接到 BP_PlayerController。

在 Editor 内执行 py "<本文件>" "<报告路径>"，或以 -run=pythonscript 执行并由环境变量
GGYGO_SQUAD_INPUT_REPORT 给出报告路径（报告已存在时拒绝）。只新建三个包、只改 BP_PlayerController 的 CDO 三个属性，
逐包保存，不 SaveAll。目标包已存在、存在脏包或 PIE 运行时拒绝。改键：改 IMC_Squad 的映射；
两个 InputAction 带 PlayerMappableKeySettings，供以后的按键设置界面按名字改键。
"""
import json
import os
import sys
import traceback

SCHEMA = "GGYGO.SquadSwitchInputs/v1"
ACTION_DIR = "/Game/Input/Actions"
MAPPING_DIR = "/Game/Input/Mappings"
ACTIONS = (
    # (资产名, 默认键, PlayerMappable 名, 显示名)
    ("IA_SwitchCharacter_Prev", "Z", "SwitchCharacterPrevious", "上一个角色"),
    ("IA_SwitchCharacter_Next", "C", "SwitchCharacterNext", "下一个角色"),
)
CONTEXT_NAME = "IMC_Squad"
CONTROLLER = "/Game/BP/GamePlay/BP_PlayerController"
CATEGORY = "队伍"


def require(condition, reason):
    if not condition:
        raise RuntimeError("Input.SquadSwitch: " + reason)


def dirty_packages(ue):
    utils = ue.EditorLoadingAndSavingUtils
    return sorted(p.get_path_name() for p in utils.get_dirty_content_packages()) + \
        sorted(p.get_path_name() for p in utils.get_dirty_map_packages())


def make_key(ue, name):
    key = ue.Key()
    key.set_editor_property("key_name", name)
    return key


def run(output):
    import unreal as ue
    report = {"schema": SCHEMA, "success": False, "created": [], "saved": [], "errors": []}
    try:
        # 以 commandlet 执行时没有 Editor 子系统，也不会有 PIE。
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem) if hasattr(ue, "get_editor_subsystem") else None
        require(editor is None or editor.get_game_world() is None, "PIE 正在运行")
        report["dirty_before"] = dirty_packages(ue)
        require(not report["dirty_before"], "存在脏包，停止且不保存")
        library = ue.EditorAssetLibrary
        targets = [ACTION_DIR + "/" + a[0] for a in ACTIONS] + [MAPPING_DIR + "/" + CONTEXT_NAME]
        for package in targets:
            require(not library.does_asset_exist(package), "目标资产已存在，不覆盖：" + package)
        require(library.does_asset_exist(CONTROLLER), "缺少 BP_PlayerController")

        tools = ue.AssetToolsHelpers.get_asset_tools()
        actions = []
        for name, _, mappable_name, display in ACTIONS:
            action = tools.create_asset(name, ACTION_DIR, ue.InputAction, ue.InputAction_Factory())
            require(action is not None, "创建失败：" + name)
            report["created"].append(action.get_path_name())
            action.set_editor_property("value_type", ue.InputActionValueType.BOOLEAN)
            settings = ue.new_object(ue.PlayerMappableKeySettings, outer=action)
            settings.set_editor_property("name", mappable_name)
            settings.set_editor_property("display_name", display)
            settings.set_editor_property("display_category", CATEGORY)
            action.set_editor_property("player_mappable_key_settings", settings)
            actions.append(action)

        context = tools.create_asset(CONTEXT_NAME, MAPPING_DIR, ue.InputMappingContext, ue.InputMappingContext_Factory())
        require(context is not None, "创建失败：" + CONTEXT_NAME)
        report["created"].append(context.get_path_name())
        # 与 Hero 的 IMC 同一注册策略：多方注册按计数归还。
        context.set_editor_property("registration_tracking_mode",
                                    ue.MappingContextRegistrationTrackingMode.COUNT_REGISTRATIONS)
        for action, (_, key, _, _) in zip(actions, ACTIONS):
            context.map_key(action, make_key(ue, key))

        blueprint = ue.load_asset(CONTROLLER)
        generated = ue.load_object(None, CONTROLLER + ".BP_PlayerController_C")
        require(blueprint is not None and generated is not None, "BP_PlayerController 加载失败")
        cdo = ue.get_default_object(generated)
        for prop in ("squad_switch_input_mapping", "switch_to_previous_member_action", "switch_to_next_member_action"):
            require(cdo.get_editor_property(prop) is None, "BP_PlayerController 已配置 " + prop + "，不覆盖")
        cdo.set_editor_property("squad_switch_input_mapping", context)
        cdo.set_editor_property("switch_to_previous_member_action", actions[0])
        cdo.set_editor_property("switch_to_next_member_action", actions[1])

        # 读回：映射、键、注册策略、可改键名与 CDO 引用。
        rows = list(context.get_editor_property("default_key_mappings").get_editor_property("mappings"))
        report["mappings"] = [{"action": r.get_editor_property("action").get_path_name(),
                               "key": str(r.get_editor_property("key").get_editor_property("key_name"))} for r in rows]
        require(report["mappings"] == [{"action": a.get_path_name(), "key": k}
                                       for a, (_, k, _, _) in zip(actions, ACTIONS)], "IMC 映射读回不符")
        report["actions"] = [{"object": a.get_path_name(),
                              "value_type": str(a.get_editor_property("value_type")),
                              "mappable_name": str(a.get_editor_property("player_mappable_key_settings").get_editor_property("name"))}
                             for a in actions]
        require([r["mappable_name"] for r in report["actions"]] == [a[2] for a in ACTIONS], "可改键名读回不符")
        require(cdo.get_editor_property("squad_switch_input_mapping") == context
                and cdo.get_editor_property("switch_to_previous_member_action") == actions[0]
                and cdo.get_editor_property("switch_to_next_member_action") == actions[1], "CDO 引用读回不符")

        allowed = set(targets + [CONTROLLER])
        now_dirty = dirty_packages(ue)
        report["dirty_before_save"] = now_dirty
        require(set(now_dirty).issubset(allowed), "出现非目标脏包：" + ", ".join(sorted(set(now_dirty) - allowed)))
        for asset, package in zip([*actions, context, blueprint], [*targets, CONTROLLER]):
            require(library.save_loaded_asset(asset, only_if_is_dirty=False), "保存失败：" + package)
            report["saved"].append(package)
        report["dirty_after"] = dirty_packages(ue)
        require(not report["dirty_after"], "保存后仍有脏包")
        report["success"] = True
    except Exception as error:
        report["errors"].append({"error": str(error), "traceback": traceback.format_exc()})
    with open(output, "x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    return report


if __name__ == "__main__":
    run(sys.argv[1] if len(sys.argv) > 1 else os.environ["GGYGO_SQUAD_INPUT_REPORT"])
