"""@file wire_player_key_settings.py
@brief 让 IMC_Default 的键盘／鼠标映射可在改键界面修改，并把 IMC_Default、IMC_Squad 登记到 BP_PlayerController。

在 Editor 内执行 py "<本文件>" "<报告路径>"，或以 -run=pythonscript 执行并由环境变量
GGYGO_ASSET_REPORT 给出报告路径（报告已存在时拒绝）。IMC_Default 中每一行按 动作＋键 归类：
主键位（WASD、Shift、Ctrl、空格、鼠标左键）改为逐行覆盖设置并给出固定改键名；方向键和手柄行设为
不参与改键（IgnoreSettings），避免与主键位共用名字后被当成同一行的其它槽位。不认识的行直接拒绝。
键、动作、修饰器、触发器都不改。逐包保存，不 SaveAll；存在脏包或 PIE 运行时拒绝。
"""
import json
import os
import sys
import traceback

SCHEMA = "GGYGO.PlayerKeySettings/v1"
CONTEXT = "/Game/Input/Mappings/IMC_Default"
SQUAD_CONTEXT = "/Game/Input/Mappings/IMC_Squad"
CONTROLLER = "/Game/BP/GamePlay/BP_PlayerController"
# (动作资产名, 键) → (改键名, 显示名, 分类)
MAPPABLE = {
    ("IA_Move", "W"): ("MoveForward", "前进", "移动"),
    ("IA_Move", "S"): ("MoveBackward", "后退", "移动"),
    ("IA_Move", "A"): ("MoveLeft", "左移", "移动"),
    ("IA_Move", "D"): ("MoveRight", "右移", "移动"),
    ("IA_Sprint", "LeftShift"): ("Sprint", "冲刺", "移动"),
    ("IA_ForceWalk", "LeftControl"): ("ForceWalk", "慢走", "移动"),
    ("IA_Jump", "SpaceBar"): ("Jump", "跳跃", "移动"),
    ("IA_Attack", "LeftMouseButton"): ("Attack", "普攻", "战斗"),
}
FIXED_KEYS = {"Up", "Down", "Left", "Right"}


def require(condition, reason):
    if not condition:
        raise RuntimeError("PlayerKeySettings: " + reason)


def dirty_packages(ue):
    utils = ue.EditorLoadingAndSavingUtils
    return sorted(p.get_path_name() for p in utils.get_dirty_content_packages()) + \
        sorted(p.get_path_name() for p in utils.get_dirty_map_packages())


def row_facts(row):
    action = row.get_editor_property("action")
    return (action.get_name() if action else None,
            str(row.get_editor_property("key").get_editor_property("key_name")))


def run(output):
    import unreal as ue
    report = {"schema": SCHEMA, "success": False, "saved": [], "errors": [], "rows": []}
    try:
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem) if hasattr(ue, "get_editor_subsystem") else None
        require(editor is None or editor.get_game_world() is None, "PIE 正在运行")
        report["dirty_before"] = dirty_packages(ue)
        require(not report["dirty_before"], "存在脏包，停止且不保存")
        context = ue.load_asset(CONTEXT)
        squad_context = ue.load_asset(SQUAD_CONTEXT)
        require(isinstance(context, ue.InputMappingContext) and isinstance(squad_context, ue.InputMappingContext), "IMC 加载失败")
        data = context.get_editor_property("default_key_mappings")
        rows = list(data.get_editor_property("mappings"))
        inherit = ue.PlayerMappableKeySettingBehaviors.INHERIT_SETTINGS_FROM_ACTION
        before = [row_facts(r) for r in rows]
        require(all(r.get_editor_property("setting_behavior") == inherit for r in rows), "原映射已有非默认改键设置，不覆盖")
        used = set()
        for row in rows:
            action, key = row_facts(row)
            spec = MAPPABLE.get((action, key))
            if spec:
                name, display, category = spec
                require(name not in used, "改键名重复：" + name)
                used.add(name)
                settings = ue.new_object(ue.PlayerMappableKeySettings, outer=context)
                settings.set_editor_property("name", name)
                settings.set_editor_property("display_name", display)
                settings.set_editor_property("display_category", category)
                row.set_editor_property("setting_behavior", ue.PlayerMappableKeySettingBehaviors.OVERRIDE_SETTINGS)
                row.set_editor_property("player_mappable_key_settings", settings)
                report["rows"].append({"action": action, "key": key, "mappable": name})
            else:
                require(key in FIXED_KEYS or key.startswith("Gamepad_"), "不认识的映射行：%s/%s" % (action, key))
                row.set_editor_property("setting_behavior", ue.PlayerMappableKeySettingBehaviors.IGNORE_SETTINGS)
                report["rows"].append({"action": action, "key": key, "mappable": None})
        require(used == {spec[0] for spec in MAPPABLE.values()}, "缺少预期的主键位行：" + ", ".join(sorted({s[0] for s in MAPPABLE.values()} - used)))
        data.set_editor_property("mappings", rows)
        context.set_editor_property("default_key_mappings", data)
        after = list(context.get_editor_property("default_key_mappings").get_editor_property("mappings"))
        require([row_facts(r) for r in after] == before, "键或动作被改变")
        for r in after:
            facts = row_facts(r)
            settings = r.get_editor_property("player_mappable_key_settings")
            expected = MAPPABLE.get(facts)
            require((settings is not None and str(settings.get_editor_property("name")) == expected[0]) if expected else settings is None,
                    "改键设置读回不符：%s/%s" % facts)

        blueprint = ue.load_asset(CONTROLLER)
        generated = ue.load_object(None, CONTROLLER + ".BP_PlayerController_C")
        require(blueprint is not None and generated is not None, "BP_PlayerController 加载失败")
        cdo = ue.get_default_object(generated)
        require(not list(cdo.get_editor_property("player_mappable_input_mappings")), "BP_PlayerController 已登记改键 IMC，不覆盖")
        cdo.set_editor_property("player_mappable_input_mappings", [context, squad_context])
        require(list(cdo.get_editor_property("player_mappable_input_mappings")) == [context, squad_context], "CDO 读回不符")

        allowed = {CONTEXT, CONTROLLER}
        now_dirty = dirty_packages(ue)
        report["dirty_before_save"] = now_dirty
        require(set(now_dirty).issubset(allowed), "出现非目标脏包：" + ", ".join(sorted(set(now_dirty) - allowed)))
        for asset, package in ((context, CONTEXT), (blueprint, CONTROLLER)):
            require(ue.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), "保存失败：" + package)
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
    run(sys.argv[1] if len(sys.argv) > 1 else os.environ["GGYGO_ASSET_REPORT"])
