"""从生产普攻三段读资源列表，补齐角色现有输入资源门的制作配置。

只写 BP_PC_Pyrios 的 AbilityInputRenderSystems 默认值；GA、Montage 和图接线只读。
调用前确认目标蓝图的未提交改动来源；inspect 生成候选，apply 显式编译并只保存该包。
"""

BP = "/Game/BP/Character/Player/BP_PC_Pyrios"
GA = "/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo"
VARIABLE = "AbilityInputRenderSystems"


def inspect(ue):
    blueprint = ue.load_asset(BP)
    ability = ue.get_default_object(ue.EditorAssetLibrary.load_blueprint_class(GA))
    cdo = ue.get_default_object(blueprint.generated_class())
    systems, steps = [], []
    for index, step in enumerate(ability.get_editor_property("combo_steps")):
        fx = step.get_editor_property("fx")
        if fx.get_editor_property("mode") == ue.GGYGOComboFXMode.DISABLED:
            continue
        if fx.get_editor_property("mode") != ue.GGYGOComboFXMode.MONTAGE_WINDOW:
            raise RuntimeError("当前普攻 FX 模式不在制作范围内")
        system = fx.get_editor_property("system")
        units = list(fx.get_editor_property("system_units"))
        if (system is not None) == bool(units):
            raise RuntimeError("每段必须显式配置单 System 或完整 SystemUnits")
        values = [system] if system else [unit.get_editor_property("system") for unit in units]
        if not values or any(not isinstance(value, ue.NiagaraSystem) for value in values):
            raise RuntimeError("普攻资源配置包含空或非 Niagara System")
        for value in values:
            if value not in systems:
                systems.append(value)
        steps.append(dict(index=index, montage=step.get_editor_property("montage").get_path_name(),
                          systems=[value.get_path_name() for value in values]))
    if not systems:
        raise RuntimeError("生产普攻没有可准备的 FX 资源")
    previous = list(cdo.get_editor_property(VARIABLE))
    # 保留蓝图中其它用途的资源顺序，只追加本次生产连段的缺项。
    expected = previous + [value for value in systems if value not in previous]
    return dict(blueprint=blueprint, expected=expected, facts=dict(
        before=[value.get_path_name() for value in previous],
        after=[value.get_path_name() for value in expected], steps=steps))


def apply(ue, expected_facts):
    if ue.EditorLevelLibrary.get_pie_worlds(True):
        raise RuntimeError("角色资源列表只能在非 PIE 制作窗口修改")
    if any(package.get_path_name() == BP for package in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()):
        raise RuntimeError("目标角色蓝图有当前 Editor 未保存修改")
    candidate = inspect(ue)
    if candidate["facts"] != expected_facts:
        raise RuntimeError("角色资源列表或生产 GA 已变化，请重新检查差分")
    blueprint = candidate["blueprint"]
    cdo = ue.get_default_object(blueprint.generated_class())
    cdo.set_editor_property(VARIABLE, candidate["expected"])
    ue.BlueprintEditorLibrary.compile_blueprint(blueprint)
    actual = [value.get_path_name() for value in ue.get_default_object(blueprint.generated_class()).get_editor_property(VARIABLE)]
    if actual != expected_facts["after"]:
        raise RuntimeError("编译后资源列表与候选不符；未保存")
    if not ue.EditorAssetLibrary.save_loaded_asset(blueprint, only_if_is_dirty=False):
        raise RuntimeError("目标角色蓝图保存失败")
    return dict(saved=True, systems=actual)
