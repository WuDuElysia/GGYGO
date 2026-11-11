"""从当前生产 GA 和原授予表读取 Normal01 资源来源，供 Character 制作脚本消费。

不保存、不改 GA/NS，不替调用方列举材质；Renderer 与最终材质参数由原生准备入口解析。
本模块无导入副作用，只允许在统筹安排的 UE 制作窗口调用 read_current_sources。
"""

ABILITY = "/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo"
ABILITY_SET = "/Game/Characters/Player/Pyrios/DA/DA_AbilitySet_Pyrios"
MONTAGE = "/Game/Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_Normal_01"


def read_current_sources(ue):
    ability_class = ue.EditorAssetLibrary.load_blueprint_class(ABILITY)
    ability_set = ue.load_asset(ABILITY_SET)
    montage = ue.load_asset(MONTAGE)
    if ability_class is None or ability_set is None or montage is None:
        raise RuntimeError("Normal01 准备来源缺生产 GA、授予表或原 Montage")
    cdo = ue.get_default_object(ability_class)
    steps = list(cdo.get_editor_property("combo_steps"))
    matches = [(index, step) for index, step in enumerate(steps)
               if step.get_editor_property("montage") == montage]
    if len(matches) != 1:
        raise RuntimeError("当前生产 GA 未唯一配置原 Normal01 Montage")
    index, step = matches[0]
    fx = step.get_editor_property("fx")
    if fx.get_editor_property("mode") != ue.GGYGOComboFXMode.MONTAGE_WINDOW:
        raise RuntimeError("原 Normal01 没有启用作者 Montage FX 窗口")
    system = fx.get_editor_property("system")
    units = list(fx.get_editor_property("system_units"))
    if (system is not None) == bool(units):
        raise RuntimeError("原 FX 必须使用单 System 或完整 SystemUnits 其中一种")
    systems = [system] if system is not None else [unit.get_editor_property("system") for unit in units]
    if not systems or any(not isinstance(item, ue.NiagaraSystem) for item in systems):
        raise RuntimeError("原配置包含无效 Niagara System")
    grants = [row for row in ability_set.get_editor_property("GrantedGameplayAbilities")
              if row.get_editor_property("Ability") == ability_class]
    if len(grants) != 1:
        raise RuntimeError("当前授予表未唯一绑定生产普攻 GA")
    input_tag = grants[0].get_editor_property("InputTag")
    if str(ue.GameplayTagLibrary.get_tag_name(input_tag)) != "InputTag.Attack.Light":
        raise RuntimeError("当前授予输入已变化，不能将资源准备门接到其它玩法输入")
    # 普攻 FX 配置没有调用方材质覆盖字段；保留 NS 的真实参数默认值。
    # 不把此事实误记成“材质闭包为空”，原生准备仍须解析每个启用 Renderer。
    return dict(systems=systems, input_tag=input_tag, user_object_overrides={},
                source_ability=ability_class.get_path_name(), source_step_index=index,
                source_montage=montage.get_path_name(), source_fx_text=fx.export_text())
