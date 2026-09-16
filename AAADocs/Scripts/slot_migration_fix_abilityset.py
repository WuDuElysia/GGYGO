"""把基础属性集从 AbilitySet 移出。

D1 修订后 HealthSet 与 CombatSet 由 AGGYGOCharacterSlot 以默认子对象持有，
AbilitySet 若仍在 GrantedAttributes 里配着同类型属性集，会在授予时再挂一份，
同一个 ASC 上出现两份 UGGYGOHealthSet，GetSet 只返回其中一份，
于是 GE 改的属性和 HealthComponent 读的属性可能不是同一份。

本脚本只清空 GrantedAttributes，不动能力与效果列表。
"""

import unreal

TARGET = "/Game/Characters/Player/Pyrios/DA/DA_AbilitySet_Common"


def run():
    asset = unreal.load_asset(TARGET)
    if asset is None:
        unreal.log_error("找不到资产 {}".format(TARGET))
        return

    before = asset.get_editor_property("GrantedAttributes")
    unreal.log("GrantedAttributes 当前有 {} 项".format(len(before)))

    asset.set_editor_property("GrantedAttributes", [])

    after = asset.get_editor_property("GrantedAttributes")
    unreal.log("清空后有 {} 项".format(len(after)))

    abilities = asset.get_editor_property("GrantedGameplayAbilities")
    unreal.log("GrantedGameplayAbilities 保留 {} 项".format(len(abilities)))

    if unreal.EditorAssetLibrary.save_asset(TARGET, only_if_is_dirty=False):
        unreal.log("已保存 {}".format(TARGET))
    else:
        unreal.log_error("保存失败 {}".format(TARGET))


run()
