"""核对 Slot 迁移后的资产状态，结果写文件（编辑器日志的中文在本机会乱码）。"""

import unreal

OUT = "f:/ue_project/GGYGO/Saved/slot_migration_check.txt"

ABILITY_SET = "/Game/Characters/Player/Pyrios/DA/DA_AbilitySet_Common"
PAWN_DATA = "/Game/Characters/Player/Pyrios/DA/DA_Pawn_Pyrios"


def run():
    lines = []

    aset = unreal.load_asset(ABILITY_SET)
    if aset is None:
        lines.append("ABILITYSET=MISSING")
    else:
        attrs = aset.get_editor_property("GrantedAttributes")
        abilities = aset.get_editor_property("GrantedGameplayAbilities")
        effects = aset.get_editor_property("GrantedGameplayEffects")
        lines.append("ABILITYSET_GrantedAttributes={}".format(len(attrs)))
        lines.append("ABILITYSET_GrantedAbilities={}".format(len(abilities)))
        lines.append("ABILITYSET_GrantedEffects={}".format(len(effects)))

    pdata = unreal.load_asset(PAWN_DATA)
    if pdata is None:
        lines.append("PAWNDATA=MISSING")
    else:
        pawn_class = pdata.get_editor_property("PawnClass")
        sets = pdata.get_editor_property("AbilitySets")
        group = pdata.get_editor_property("AbilityGroupConfig")
        lines.append("PAWNDATA_PawnClass={}".format(pawn_class.get_name() if pawn_class else "None"))
        lines.append("PAWNDATA_AbilitySets={}".format(len(sets)))
        lines.append("PAWNDATA_GroupConfig={}".format("SET" if group else "None"))

    # 新类是否已编译进模块并暴露给反射
    lines.append("SLOT_CLASS={}".format(
        "FOUND" if hasattr(unreal, "GGYGOCharacterSlot") else "MISSING"))

    with open(OUT, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


run()
