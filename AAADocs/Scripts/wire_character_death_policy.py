"""制作共享角色死亡处理蓝图，并接回既有玩家／敌人蓝图。

在独立 Editor 内执行。只保存三个原生角色分支的共享模板与既有蓝图；再次执行只读回已有接线。
"""
import unreal as ue


FUNCTION = "K2_HandleDeathFinished"
PAIRS = (
    ("/Game/BP/Character/BP_HeroCharacter", ue.GGYGOHeroCharacter,
     "/Game/BP/Character/Player/BP_PC_Pyrios"),
    ("/Game/BP/Character/BP_Character", ue.GGYGOCharacterBase,
     "/Game/BP/Character/Player/BP_Enemy"),
    ("/Game/BP/Character/BP_BossCharacter", ue.GGYGOBossCharacter,
     "/Game/AI/Boss/Test/BP_Boss_Test"),
    ("/Game/BP/Character/BP_Character", ue.GGYGOCharacterBase,
     "/Game/BP/BP_BaseCharacter"),
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def verify(shared, production):
    graph = ue.BlueprintEditorLibrary.find_graph(shared, FUNCTION)
    require(graph is not None, "共享模板缺少死亡处理覆盖图")
    editor = ue.BlueprintGraphEditor.get_graph_editor(graph)
    nodes = list(editor.list_all_nodes())
    calls = [n for n in nodes if n.get_class().get_name() == "K2Node_CallFunction"]
    returns = [n for n in nodes if n.get_class().get_name() == "K2Node_FunctionResult"]
    require(len(nodes) == 3 and len(calls) == 1 and len(returns) == 1, "死亡处理图节点数量不符")
    call, result = calls[0], returns[0]
    require(str(ue.GGYGOAnimationGraphEditorLibrary.get_called_function_name(call)) == "UninitAndDestroy",
            "死亡处理没有调用清理原语")
    # 继承的实例函数在编译后归为 Self 引用，声明类由本蓝图的 native 父类解析。
    require(ue.BlueprintEditorLibrary.get_blueprint_parent_class(shared)
            in tuple(native.static_class() for _, native, _ in PAIRS),
            "共享模板的原生父类不符")
    for source, target in ((editor.find_graph_entry_pin(), call.find_execute_pin()),
                           (call.find_then_pin(), result.find_execute_pin())):
        links = list(source.list_connected_pins())
        require(len(links) == 1 and links[0].is_same_native_pin(target), "死亡处理执行边不符")
    require(result.find_input_pin("ReturnValue").get_pin_value().lower() == "true", "共享模板未返回已处理")
    require(ue.BlueprintEditorLibrary.get_blueprint_parent_class(production) == shared.generated_class(),
            "生产蓝图没有继承共享模板")
    require(ue.BlueprintEditorLibrary.find_graph(production, FUNCTION) is None, "生产蓝图重复覆盖共享死亡处理")
    for blueprint in (shared, production):
        require(blueprint.get_editor_property("status") == ue.BlueprintStatus.BS_UP_TO_DATE,
                "蓝图编译未通过：" + blueprint.get_path_name())
    ue.log("[I24] 已读回共享死亡图与生产继承：" + production.get_path_name())


def run():
    dirty = (list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
             + list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()))
    require(not dirty, "Editor 有未保存内容，拒绝制作")
    pending = []
    for shared_path, native, production_path in PAIRS:
        production = ue.load_asset(production_path)
        require(isinstance(production, ue.Blueprint), "缺少生产蓝图：" + production_path)
        shared = ue.load_asset(shared_path) if ue.EditorAssetLibrary.does_asset_exist(shared_path) else None
        if shared:
            if ue.BlueprintEditorLibrary.get_blueprint_parent_class(production) == native.static_class():
                ue.BlueprintEditorLibrary.reparent_blueprint(production, shared.generated_class())
                ue.BlueprintEditorLibrary.compile_blueprint(production)
                pending.append(production)
            verify(shared, production)
            continue
        require(ue.BlueprintEditorLibrary.get_blueprint_parent_class(production) == native.static_class(),
                "生产父类变化，需重新核对继承关系：" + production_path)
        shared = ue.BlueprintEditorLibrary.create_blueprint_asset_with_parent(shared_path, native.static_class())
        require(shared is not None, "共享模板创建失败")
        graph = ue.BlueprintEditorLibrary.add_function_override(shared, FUNCTION)
        require(graph is not None, "死亡处理覆盖图创建失败")
        editor = ue.BlueprintGraphEditor.get_graph_editor(graph)
        result_nodes = [n for n in editor.list_all_nodes() if n.get_class().get_name() == "K2Node_FunctionResult"]
        result = result_nodes[0] if result_nodes else editor.add_return_node()
        entry = editor.find_graph_entry_pin()
        require(entry.break_pin_links(), "入口原连接清理失败")
        call = editor.add_call_function_node("/Script/GGYGO.GGYGOCharacterBase.UninitAndDestroy")
        require(call is not None, "清理节点创建失败")
        call.set_node_pos(ue.IntPoint(300, 0))
        result.set_node_pos(ue.IntPoint(600, 0))
        require(entry.try_create_connection(call.find_execute_pin()), "入口连接失败")
        require(call.find_then_pin().try_create_connection(result.find_execute_pin()), "返回连接失败")
        require(result.find_input_pin("ReturnValue").set_pin_value("true"), "返回值配置失败")
        ue.BlueprintEditorLibrary.compile_blueprint(shared)
        ue.BlueprintEditorLibrary.reparent_blueprint(production, shared.generated_class())
        ue.BlueprintEditorLibrary.compile_blueprint(production)
        verify(shared, production)
        pending.extend((shared, production))
    allowed = {path for shared, _, production in PAIRS for path in (shared, production)}
    dirty = (list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
             + list(ue.EditorLoadingAndSavingUtils.get_dirty_map_packages()))
    require(all(p.get_path_name() in allowed for p in dirty), "制作产生非目标脏包，拒绝保存")
    for blueprint in pending:
        require(ue.EditorAssetLibrary.save_loaded_asset(blueprint, only_if_is_dirty=True),
                "保存失败：" + blueprint.get_path_name())
    ue.log("[I24] 制作完成，仅保存本需求目标蓝图")


if __name__ == "__main__":
    run()
