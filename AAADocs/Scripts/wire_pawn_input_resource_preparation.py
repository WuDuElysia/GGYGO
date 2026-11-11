"""为原角色 BP 制作装配时的渲染资源请求，保留已有 BeginPlay 后继。

Root 在获准资产窗传入原 Blueprint、PawnData 和完整 known_dirty。
prepare 只制作图及配置，不编译或保存；compile 后调用 verify_compiled 核真实默认值。
具体资源由 FX 的生产配置读取器提供，运行时选择和调用流程保留在 BP 中。
"""

import importlib.util
import re
from pathlib import Path


BP_PATH = "/Game/BP/Character/Player/BP_PC_Pyrios.BP_PC_Pyrios"
DATA_PATH = "/Game/Characters/Player/Pyrios/DA/DA_Pawn_Pyrios.DA_Pawn_Pyrios"
EXTENSION = "/Script/GGYGO.GGYGOPawnExtensionComponent"
SYSTEM = "/Script/Engine.KismetSystemLibrary"
PREPARATION = "/Script/GGYGORendering.GGYGONiagaraMaterialPreparation"
MARKER = "GGYGO.AbilityInputResourcePreparation"
RESOURCE_VARIABLE = "AbilityInputRenderSystems"


def _require(value, reason):
    if not value:
        raise RuntimeError("[Character.InputResources] " + reason)


def _one(values, reason):
    values = list(values)
    _require(len(values) == 1, reason + ": " + str(len(values)))
    return values[0]


def _pin(node, name):
    return _one((p for p in node.list_all_pins() if str(p.get_pin_name()) == name),
                node.get_path_name() + "." + name)


def _connect(source, target):
    _require(source.try_create_connection(target), "原生连接拒绝")
    _require(any(p.is_same_native_pin(target) for p in source.list_connected_pins()), "连接读回缺失")


def _linked_pin_name(pin):
    name = str(pin.get_pin_name())
    if name != "None":
        return name
    # LinkedTo 返回隐藏端点的代理。原生名称访问会过滤隐藏 Pin，但 Struct 序列化保留 PinName。
    member = re.search(r'\bPinName="?([^",)]+)"?', pin.export_text())
    _require(member is not None, "连边代理缺少原 PinName")
    return member.group(1)


def _same_link_endpoint(actual, expected):
    if actual.is_same_native_pin(expected):
        return True
    return (not actual.is_same_native_pin(actual) and not expected.is_same_native_pin(expected)
            and actual.get_owning_node() == expected.get_owning_node()
            and actual.get_pin_direction() == expected.get_pin_direction()
            and _linked_pin_name(actual) == _linked_pin_name(expected))


def _same_pins(actual, expected):
    if len(actual) != len(expected):
        return False
    unmatched = list(expected)
    for pin in actual:
        matches = [i for i, other in enumerate(unmatched) if _same_link_endpoint(pin, other)]
        if len(matches) != 1:
            return False
        unmatched.pop(matches[0])
    return True


def _pin_label(pin):
    return (pin.get_owning_node().get_path_name() + "." + _linked_pin_name(pin)
            + " [" + str(pin.get_pin_direction()) + "]")


def _dirty(ue):
    return list(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()) + list(
        ue.EditorLoadingAndSavingUtils.get_dirty_map_packages())


def _read_sources(ue):
    source_path = Path(__file__).with_name("prepare_pyrios_normal01_resources.py")
    spec = importlib.util.spec_from_file_location("ggygo_normal01_resource_sources", source_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.read_current_sources(ue)


def prepare(ue, blueprint, pawn_data, *, known_dirty, apply=False):
    """原生产二包的制作入口；拒绝重复插图，不回滚或覆盖未知 dirty。"""
    _require(not ue.EditorLevelLibrary.get_pie_worlds(True), "只允许非 PIE 制作窗口")
    _require(isinstance(blueprint, ue.Blueprint) and blueprint.get_path_name() == BP_PATH,
             "必须提供原生产角色 Blueprint")
    _require(isinstance(pawn_data, ue.GGYGOPawnData) and pawn_data.get_path_name() == DATA_PATH,
             "必须提供原生产 PawnData")
    original_dirty = _dirty(ue)
    _require(set(original_dirty) == set(known_dirty), "完整原 dirty Package 集合不匹配")
    sources = _read_sources(ue)
    _require(not sources["user_object_overrides"], "实际 FX 已增加覆盖，须同步 BP 请求参数")
    graph_library = ue.GGYGOAnimationGraphEditorLibrary
    for cls, members in (
            (ue.BlueprintGraphEditor, ("add_member_variable", "add_get_member_variable_node",
                                      "add_call_function_node", "add_branch_node", "list_available_nodes",
                                      "retarget_node_class")),
            (ue.BlueprintEditorLibrary, ("get_array_type", "get_object_reference_type")),
            (graph_library, ("read_blueprint_node_comment", "write_blueprint_node_comment",
                             "connect_blueprint_call_world_context", "get_called_function_name"))):
        _require(all(hasattr(cls, member) for member in members), str(cls) + " 缺少实际制作接口")
    generated = ue.BlueprintEditorLibrary.generated_class(blueprint)
    _require(generated is not None and pawn_data.get_editor_property("PawnClass") == generated,
             "PawnData 未使用本次生产 BP")
    graph = ue.BlueprintEditorLibrary.find_event_graph(blueprint)
    _require(graph is not None, "原 BP 缺少 EventGraph")
    editor = ue.BlueprintGraphEditor.get_graph_editor(graph)
    old_nodes = list(editor.list_all_nodes())
    for node in old_nodes:
        comment = graph_library.read_blueprint_node_comment(blueprint, node)
        _require(comment.succeeded, "无法读取原节点注释")
        _require(not str(comment.comment).startswith(MARKER), "已存在本项接线，拒绝重复制作")
    members = list(map(str, ue.BlueprintEditorLibrary.list_member_variable_names(blueprint, True)))
    _require(all(name.rsplit(".", 1)[-1] != RESOURCE_VARIABLE for name in members), "资源变量已存在")
    begin = editor.find_event_node("ReceiveBeginPlay")
    _require(begin is not None, "原生产 BP 必须保有已接线的 BeginPlay")
    start = _pin(begin, "then")
    original_tail = list(start.list_connected_pins())
    _require(len(original_tail) <= 1, "BeginPlay 有多个直接后继")
    original_pins = [(p, str(p.get_pin_value()), list(p.list_connected_pins()))
                     for node in old_nodes for p in node.list_all_pins()]
    old_tags = pawn_data.get_editor_property("InputTagsRequiringRenderResources")
    expected_tags = ue.GameplayTagLibrary.make_gameplay_tag_container_from_tag(sources["input_tag"])
    _require(not ue.GameplayTagLibrary.break_gameplay_tag_container(old_tags)
             or old_tags.export_text() == expected_tags.export_text(), "已有其它输入准备配置，须明确合并范围")
    resource_type = ue.BlueprintEditorLibrary.get_array_type(
        ue.BlueprintEditorLibrary.get_object_reference_type(ue.NiagaraSystem.static_class()))
    paths = [system.get_path_name() for system in sources["systems"]]
    _require(all("\"" not in path and "'" not in path for path in paths), "资源路径不可序列化")
    # 数组元素类型已是 NiagaraSystem；用原对象路径交原生 FObjectProperty 导入器解析。
    defaults = "(" + ",".join('"' + path + '"' for path in paths) + ")"
    actions = list(map(str, editor.list_available_nodes([])))
    self_action = _one((a for a in actions if a.rsplit("|", 1)[-1] == "Getareferencetoself"), "Self action")
    # 接口固定为本批 Rendering 正式 ABI，真实反射缺项在修改前拒绝。
    required_functions = {
        EXTENSION: ("FindPawnExtensionComponent", "SetAbilityInputResourcePreparation"),
        SYSTEM: ("IsDedicatedServer",),
        PREPARATION: ("CreateForSystemAssets", "Start"),
    }
    for path, functions in required_functions.items():
        cls = ue.load_class(None, path)
        _require(cls is not None, "缺原生类 " + path)
        for function in functions:
            _require(ue.find_object(cls, function, ue.Function) is not None, "缺函数 " + path + "." + function)
    _require(set(_dirty(ue)) == set(original_dirty), "只读预检改变 dirty")
    result = dict(applied=False, blueprint=blueprint, pawn_data=pawn_data, sources=sources,
                  systems=paths, expected_tags=expected_tags.export_text(),
                  original_successors=[dict(node=p.get_owning_node().get_name(), pin=str(p.get_pin_name()))
                                       for p in original_tail],
                  objects=[blueprint, pawn_data], compiled=False, saved=False)
    if not apply:
        return result

    created = []
    right = max([node.get_node_pos().x for node in old_nodes] + [0]) + 700

    def place(node, label):
        _require(node is not None, "创建节点拒绝 " + label)
        node.set_node_pos(ue.IntPoint(right + (len(created) % 4) * 520, (len(created) // 4) * 350))
        comment = graph_library.write_blueprint_node_comment(blueprint, node, MARKER + ": " + label)
        _require(comment.succeeded, "节点注释写入失败 " + label)
        created.append(node)
        return node

    def call(path, function):
        return place(editor.add_call_function_node(path + "." + function), function)

    _require(editor.add_member_variable(RESOURCE_VARIABLE, resource_type, defaults), "资源变量制作失败")
    self_node = place(editor.create_node_from_name(self_action, ue.Vector2D(0, 0), [], None), "当前 Pawn")
    owner = _pin(self_node, "self")
    extension = call(EXTENSION, "FindPawnExtensionComponent")
    _connect(owner, _pin(extension, "Actor"))
    extension_result = _pin(extension, "ReturnValue")
    dedicated = call(SYSTEM, "IsDedicatedServer")
    binding = graph_library.connect_blueprint_call_world_context(
        blueprint, dedicated, "WorldContextObject", self_node, "self")
    _require(binding.succeeded, "WorldContext 连接拒绝: " + binding.error)
    branch = place(editor.add_branch_node(), "专用服务器无需本地渲染准备")
    _connect(_pin(dedicated, "ReturnValue"), _pin(branch, "Condition"))
    resources = place(editor.add_get_member_variable_node(RESOURCE_VARIABLE, ""), "生产首击资源")
    request = call(PREPARATION, "CreateForSystemAssets")
    _connect(extension_result, _pin(request, "Owner"))
    _connect(_pin(resources, RESOURCE_VARIABLE), _pin(request, "Systems"))
    binding = graph_library.connect_blueprint_call_world_context(
        blueprint, request, "WorldContextObject", self_node, "self")
    _require(binding.succeeded, "请求 WorldContext 连接拒绝: " + binding.error)
    register = call(EXTENSION, "SetAbilityInputResourcePreparation")
    _connect(extension_result, _pin(register, "self"))
    _connect(_pin(request, "ReturnValue"), _pin(register, "Preparation"))
    _connect(_pin(branch, "else"), _pin(request, "execute"))
    _connect(_pin(request, "then"), _pin(register, "execute"))
    accepted = place(editor.add_branch_node(), "原请求已归本 Pawn 持有")
    _connect(_pin(register, "ReturnValue"), _pin(accepted, "Condition"))
    _connect(_pin(register, "then"), _pin(accepted, "execute"))
    start_request = call(PREPARATION, "Start")
    _connect(_pin(request, "ReturnValue"), _pin(start_request, "self"))
    _connect(_pin(accepted, "then"), _pin(start_request, "execute"))
    finishes = [_pin(branch, "then"), _pin(accepted, "else"), _pin(start_request, "then")]
    for tail in original_tail:
        _require(start.break_single_pin_link(tail), "原 BeginPlay 摘接失败")
    _connect(start, _pin(branch, "execute"))
    for finish in finishes:
        for tail in original_tail:
            _connect(finish, tail)
    pawn_data.set_editor_property("InputTagsRequiringRenderResources", expected_tags)

    for pin, value, links in original_pins:
        expected = list(links)
        if pin.is_same_native_pin(start):
            expected = [_pin(branch, "execute")]
        elif any(pin.is_same_native_pin(tail) for tail in original_tail):
            expected = [p for p in links if not p.is_same_native_pin(start)] + finishes
        current_value = str(pin.get_pin_value())
        current_links = list(pin.list_connected_pins())
        if current_value != value or not _same_pins(current_links, expected):
            raise RuntimeError(
                f"[Character.InputResources] 非约定原 Pin 被改变 {_pin_label(pin)} "
                f"默认值 期望={value!r} 当前={current_value!r} "
                f"连边 期望={list(map(_pin_label, expected))} 当前={list(map(_pin_label, current_links))}")
    after_dirty = _dirty(ue)
    packages = {blueprint.get_outermost(), pawn_data.get_outermost()}
    _require(packages.issubset(set(after_dirty)) and set(original_dirty).issubset(set(after_dirty))
             and set(after_dirty).issubset(set(original_dirty) | packages), "dirty 写集越界或原 dirty 被清除")
    _require(pawn_data.get_editor_property("InputTagsRequiringRenderResources").export_text()
             == result["expected_tags"], "输入 Tag 配置读回失败")
    result.update(applied=True, created_nodes=created, dirty_packages=after_dirty)
    return result


def verify_compiled(ue, prepared):
    """Root 编译后读真实 CDO；本方法不执行编译、保存或运行测试。"""
    _require(prepared["applied"], "必须先完成制作")
    facts = dict(systems=prepared["systems"], input_tags=prepared["expected_tags"],
                 original_successors=prepared["original_successors"])
    return read_saved(ue, prepared["blueprint"], prepared["pawn_data"], facts)


def read_saved(ue, blueprint, pawn_data, expected_facts):
    """新 Cold 进程的纯读入口；expected_facts 直接使用制作期 verify_compiled 的可序列化返回值。

    核真实 CDO、单 Tag、函数引用、数据/执行连接及原后继；不加载或修改其它资产。
    该读回不证明字节码执行、渲染资源 Ready 或实拍通过。
    """
    _require(blueprint.get_path_name() == BP_PATH and pawn_data.get_path_name() == DATA_PATH, "二包对象不符")
    original_dirty = _dirty(ue)
    generated = ue.BlueprintEditorLibrary.generated_class(blueprint)
    cdo = ue.get_default_object(generated)
    actual = list(cdo.get_editor_property(RESOURCE_VARIABLE))
    paths = [system.get_path_name() if system else None for system in actual]
    _require(paths and paths == expected_facts["systems"], "BP 默认资源未保留实际 NS 列表")
    tags = pawn_data.get_editor_property("InputTagsRequiringRenderResources")
    _require(tags.export_text() == expected_facts["input_tags"]
             and [str(ue.GameplayTagLibrary.get_tag_name(tag))
                  for tag in ue.GameplayTagLibrary.break_gameplay_tag_container(tags)] == ["InputTag.Attack.Light"],
             "PawnData 单一普攻输入门配置变化")
    _require(pawn_data.get_editor_property("PawnClass") == generated, "PawnData 未指向原角色类")
    graph = ue.BlueprintEditorLibrary.find_event_graph(blueprint)
    _require(graph is not None, "缺少原 EventGraph")
    editor = ue.BlueprintGraphEditor.get_graph_editor(graph)
    all_nodes = list(editor.list_all_nodes())
    marked = {}
    for node in all_nodes:
        comment = ue.GGYGOAnimationGraphEditorLibrary.read_blueprint_node_comment(blueprint, node)
        _require(comment.succeeded, "原生节点注释读取失败")
        if str(comment.comment).startswith(MARKER + ": "):
            label = str(comment.comment)[len(MARKER) + 2:]
            _require(label not in marked, "重复准备节点 " + label)
            marked[label] = node
    functions = {"FindPawnExtensionComponent": EXTENSION, "IsDedicatedServer": SYSTEM,
                 "CreateForSystemAssets": PREPARATION, "SetAbilityInputResourcePreparation": EXTENSION,
                 "Start": PREPARATION}
    other = {"当前 Pawn": "/Script/BlueprintGraph.K2Node_Self",
             "专用服务器无需本地渲染准备": "/Script/BlueprintGraph.K2Node_IfThenElse",
             "生产首击资源": "/Script/BlueprintGraph.K2Node_VariableGet",
             "原请求已归本 Pawn 持有": "/Script/BlueprintGraph.K2Node_IfThenElse"}
    _require(set(marked) == set(functions) | set(other), "准备节点集合变化")
    for name, parent in functions.items():
        node = marked[name]
        _require(node.get_class().get_path_name() == "/Script/BlueprintGraph.K2Node_CallFunction",
                 "调用节点类型变化 " + name)
        called = str(ue.GGYGOAnimationGraphEditorLibrary.get_called_function_name(node))
        _require(called == name, f"原函数名称变化 {node.get_path_name()} 期望={name} 当前={called}")
        expected_class = ue.load_class(None, parent)
        _require(expected_class is not None, "缺原函数声明类 " + parent)
        # UE 5.8 中传入同一个类时，匹配和不匹配均在重定向、重建节点之前返回。
        _require(editor.retarget_node_class(node, expected_class, expected_class),
                 f"原函数声明类变化 {node.get_path_name()} 期望={parent}.{name}")
    for name, node_class in other.items():
        _require(marked[name].get_class().get_path_name() == node_class, "节点类型变化 " + name)

    def pin(label, name):
        return _pin(marked[label], name)

    def link(source, target_label, target_pin):
        # 从来源的原生 LinkedTo 读隐藏 WorldContext 端点，勿访问受保护的 PinName 属性。
        targets = [p for p in source.list_connected_pins()
                   if p.get_owning_node() == marked[target_label]
                   and _linked_pin_name(p) == target_pin]
        target = _one(targets, f"连边不唯一 {_pin_label(source)} 到 {target_label}.{target_pin}")
        if target_pin != "WorldContextObject":
            _require(_same_pins(list(target.list_connected_pins()), [source]),
                     "目标存在异源连接 " + _pin_label(target))

    for source_label, source_pin, target_label, target_pin in (
            ("当前 Pawn", "self", "FindPawnExtensionComponent", "Actor"),
            ("当前 Pawn", "self", "IsDedicatedServer", "WorldContextObject"),
            ("当前 Pawn", "self", "CreateForSystemAssets", "WorldContextObject"),
            ("FindPawnExtensionComponent", "ReturnValue", "CreateForSystemAssets", "Owner"),
            ("FindPawnExtensionComponent", "ReturnValue", "SetAbilityInputResourcePreparation", "self"),
            ("生产首击资源", RESOURCE_VARIABLE, "CreateForSystemAssets", "Systems"),
            ("CreateForSystemAssets", "ReturnValue", "SetAbilityInputResourcePreparation", "Preparation"),
            ("CreateForSystemAssets", "ReturnValue", "Start", "self"),
            ("IsDedicatedServer", "ReturnValue", "专用服务器无需本地渲染准备", "Condition"),
            ("SetAbilityInputResourcePreparation", "ReturnValue", "原请求已归本 Pawn 持有", "Condition"),
            ("专用服务器无需本地渲染准备", "else", "CreateForSystemAssets", "execute"),
            ("CreateForSystemAssets", "then", "SetAbilityInputResourcePreparation", "execute"),
            ("SetAbilityInputResourcePreparation", "then", "原请求已归本 Pawn 持有", "execute"),
            ("原请求已归本 Pawn 持有", "then", "Start", "execute")):
        link(pin(source_label, source_pin), target_label, target_pin)
    begin = editor.find_event_node("ReceiveBeginPlay")
    _require(begin is not None, "原 BeginPlay 缺失")
    link(_pin(begin, "then"), "专用服务器无需本地渲染准备", "execute")
    _require(_same_pins(list(_pin(begin, "then").list_connected_pins()),
                       [pin("专用服务器无需本地渲染准备", "execute")]), "BeginPlay 仍有旁路")
    successors = [_pin(_one((n for n in all_nodes if n.get_name() == item["node"]), "原后继节点"), item["pin"])
                  for item in expected_facts["original_successors"]]
    for finish in (pin("专用服务器无需本地渲染准备", "then"), pin("原请求已归本 Pawn 持有", "else"), pin("Start", "then")):
        _require(_same_pins(list(finish.list_connected_pins()), successors), "原 BeginPlay 后继未完整保留")
    _require(set(_dirty(ue)) == set(original_dirty), "Cold 读回改变 dirty")
    return dict(systems=paths, input_tags=tags.export_text(), original_successors=expected_facts["original_successors"],
                graph_verified=True, saved=False)
