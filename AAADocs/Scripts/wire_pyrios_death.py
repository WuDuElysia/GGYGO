"""@file wire_pyrios_death.py
@brief 为 Pyrios 制作倒下 Montage 与死亡能力，并替换其能力集里的共用 GA_Death。

在 Editor 内执行 py "<本文件>" "<报告路径>"，或以 -run=pythonscript 执行并由环境变量
GGYGO_ASSET_REPORT 给出报告路径（报告已存在时拒绝）。新建 AM_Pyrios_Death（FullBody 槽、单段 Death）
与 GA_Pyrios_Death（父类 GGYGODeathAbility，DeathMontage 指向前者），把 DA_AbilitySet_Pyrios 中的
GA_Death 条目换成 GA_Pyrios_Death，其余条目与共用 GA_Death 本身不变。逐包保存，不 SaveAll；
目标已存在、存在脏包或 PIE 运行时拒绝。
"""
import json
import os
import sys
import traceback

SCHEMA = "GGYGO.PyriosDeath/v1"
SEQUENCE = "/Game/Characters/Player/Pyrios/Animation/Avatar_Male_Size03_Pyrois_Ani_Death"
MONTAGE = "/Game/Characters/Player/Pyrios/Animation/AM_Pyrios_Death"
ABILITY = "/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Death"
ABILITY_SET = "/Game/Characters/Player/Pyrios/DA/DA_AbilitySet_Pyrios"
SHARED_DEATH = "/Game/Characters/Shared/Abilities/GA_Death.GA_Death_C"
SLOT = "FullBody"
SECTION = "Death"
BLEND_IN = 0.1
BLEND_OUT = 0.25


def require(condition, reason):
    if not condition:
        raise RuntimeError("PyriosDeath: " + reason)


def dirty_packages(ue):
    utils = ue.EditorLoadingAndSavingUtils
    return sorted(p.get_path_name() for p in utils.get_dirty_content_packages()) + \
        sorted(p.get_path_name() for p in utils.get_dirty_map_packages())


def split(package):
    return package.rsplit("/", 1)[0], package.rsplit("/", 1)[1]


def run(output):
    import unreal as ue
    report = {"schema": SCHEMA, "success": False, "created": [], "saved": [], "errors": []}
    try:
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem) if hasattr(ue, "get_editor_subsystem") else None
        require(editor is None or editor.get_game_world() is None, "PIE 正在运行")
        report["dirty_before"] = dirty_packages(ue)
        require(not report["dirty_before"], "存在脏包，停止且不保存")
        library = ue.EditorAssetLibrary
        for package in (MONTAGE, ABILITY):
            require(not library.does_asset_exist(package), "目标资产已存在，不覆盖：" + package)
        sequence = ue.load_asset(SEQUENCE)
        require(isinstance(sequence, ue.AnimSequence), "倒下动画不是 AnimSequence：" + SEQUENCE)
        ability_set = ue.load_asset(ABILITY_SET)
        require(ability_set is not None, "缺少能力集：" + ABILITY_SET)
        tools = ue.AssetToolsHelpers.get_asset_tools()

        # 1. 倒下 Montage：与攻击 Montage 同一作者库，单段、FullBody 槽、自动淡出。
        factory = ue.AnimMontageFactory()
        factory.set_editor_property("source_animation", sequence)
        path, name = split(MONTAGE)
        montage = tools.create_asset(name, path, ue.AnimMontage, factory)
        require(isinstance(montage, ue.AnimMontage), "Montage 创建失败")
        report["created"].append(montage.get_path_name())
        result = ue.GGYGOLinearMontageAuthorLibrary.author_new_montage(montage, SLOT, [sequence], [SECTION])
        require(result.succeeded, "Montage 作者库失败：" + str(result.error))
        for prop, value in (("rate_scale", 1.0), ("loop", False), ("enable_auto_blend_out", True), ("blend_out_trigger_time", 0.0)):
            montage.set_editor_property(prop, value)
        for prop, seconds in (("blend_in", BLEND_IN), ("blend_out", BLEND_OUT)):
            blend = montage.get_editor_property(prop)
            blend.set_editor_property("blend_time", seconds)
            montage.set_editor_property(prop, blend)
        check = ue.GGYGOLinearMontageAuthorLibrary.validate_montage(montage, SLOT, [sequence], [SECTION])
        require(check.succeeded, "Montage 读回校验失败：" + str(check.error))
        report["montage"] = {"length": float(montage.get_play_length()), "slot": SLOT, "section": SECTION}

        # 2. 死亡能力蓝图：父类为 C++ GGYGODeathAbility，只配置倒下动作。
        bp_factory = ue.BlueprintFactory()
        bp_factory.set_editor_property("parent_class", ue.GGYGODeathAbility)
        path, name = split(ABILITY)
        blueprint = tools.create_asset(name, path, ue.Blueprint, bp_factory)
        require(blueprint is not None, "GA 蓝图创建失败")
        report["created"].append(blueprint.get_path_name())
        ue.BlueprintEditorLibrary.compile_blueprint(blueprint)
        generated = ue.load_object(None, ABILITY + "." + name + "_C")
        require(generated is not None, "GA 生成类缺失")
        cdo = ue.get_default_object(generated)
        cdo.set_editor_property("death_montage", montage)
        require(cdo.get_editor_property("death_montage") == montage, "DeathMontage 读回不符")

        # 3. 能力集：只把共用 GA_Death 换成 Pyrios 的死亡能力。
        shared = ue.load_object(None, SHARED_DEATH)
        require(shared is not None, "缺少共用 GA_Death 类")
        rows = list(ability_set.get_editor_property("granted_gameplay_abilities"))
        matches = [i for i, row in enumerate(rows) if row.get_editor_property("ability") == shared]
        require(len(matches) == 1, "能力集中 GA_Death 条目数不是 1：" + str(len(matches)))
        # 结构体字段是 EditDefaultsOnly，Python 不能逐字段改实例；按原行的等级与输入 Tag 文本重建该行。
        old = rows[matches[0]]
        grant = ue.GGYGOAbilitySet_GameplayAbility()
        require(grant.import_text('(Ability="' + generated.get_path_name() + '",AbilityLevel='
                                  + str(old.get_editor_property("ability_level"))
                                  + ',InputTag=' + old.get_editor_property("input_tag").export_text() + ')'), "授予行构造失败")
        rows[matches[0]] = grant
        ability_set.set_editor_property("granted_gameplay_abilities", rows)
        after = list(ability_set.get_editor_property("granted_gameplay_abilities"))
        report["ability_set"] = [{"ability": r.get_editor_property("ability").get_path_name() if r.get_editor_property("ability") else None,
                                  "input_tag": str(r.get_editor_property("input_tag").get_editor_property("tag_name"))} for r in after]
        require(sum(1 for r in after if r.get_editor_property("ability") == generated) == 1
                and not any(r.get_editor_property("ability") == shared for r in after), "能力集读回不符")

        allowed = {MONTAGE, ABILITY, ABILITY_SET}
        now_dirty = dirty_packages(ue)
        report["dirty_before_save"] = now_dirty
        require(set(now_dirty).issubset(allowed), "出现非目标脏包：" + ", ".join(sorted(set(now_dirty) - allowed)))
        for asset, package in ((montage, MONTAGE), (blueprint, ABILITY), (ability_set, ABILITY_SET)):
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
    run(sys.argv[1] if len(sys.argv) > 1 else os.environ["GGYGO_ASSET_REPORT"])
