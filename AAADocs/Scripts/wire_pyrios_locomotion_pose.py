"""@file wire_pyrios_locomotion_pose.py
@brief Pyrios 姿态接线：只读 preflight 与同步 prepare；不自动执行、保存或运行世界。

preflight 只读完成可在修改前知道的全部检查：原节点/连线、源 Key/Sequence、
函数图冲突、骨链与膝轴、BodyLean 开关与响应曲线试导入、原生类/函数可用性，
以及由 GGYGOEditor 只读接口读出的真实过渡方向和规则标志。已知坏配置在任何
修改前拒绝；缺少该接口的旧 Editor DLL 明确拒绝，不退回结构计数。
prepare 在同一次 GT 调用中先 preflight，再立即消费局部计划修改指定 ABP 并完整
编译；原生建节点、连线或编译失败时保留本次未保存现场，不回滚、不 SaveAll。
调用方完整读回后才能单包保存；独立 Cold、自然 finalize 和视觉另验。
"""

import math

import unreal as ue
from inspect_pyrios_locomotion_pose import BODY, FEET, MESH, dirty, reference_legs


ABP = "/Game/BP/Anim/ABP_Pyrios"
POSE_FUNCTION = "UpdateTurnBackSourcePose"
BASE = "/Script/GGYGO.GGYGOAnimInstanceBase"
EVALUATOR_LIBRARY = "/Script/AnimGraphRuntime.SequenceEvaluatorLibrary"
MATH_LIBRARY = "/Script/Engine.KismetMathLibrary"
BODY_LEAN_NODE = "/Script/GGYGOAnimGraph.GGYGOAnimGraphNode_BodyLean"
EVALUATOR_NODE = "/Script/AnimGraph.AnimGraphNode_SequenceEvaluator"
OBSERVER = "/Script/GGYGOEditor.GGYGOAnimationPoseObservationSubsystem"
# prepare 实际创建调用的原生函数；全部须在修改前可解析。
REQUIRED_FUNCTIONS = (
    (BASE, ("IsMotionPoseActive", "IsMotionPoseEnded", "IsTurnBackCurveDriven", "ApplyMotionPoseToEvaluator")),
    (EVALUATOR_LIBRARY, ("ConvertToSequenceEvaluator", "SetSequenceWithInertialBlending")),
    (MATH_LIBRARY, ("BooleanAND", "BooleanNOR", "BooleanOR")),
)
# 原生 ETransitionLogicType::TLT_Custom；自定义混合图未审，拒绝。
TRANSITION_LOGIC_CUSTOM = 2
# 角色表现配置：角度相对直立。超过 60 度方向偏差后逐渐收缓，无插值过冲。
LEAN_KEYS = ((0., 0.), (20., 20.), (60., 45.), (90., 50.), (180., 55.))


def require(condition, reason):
    if not condition:
        raise RuntimeError("[Animation.PyriosPoseWiring] " + reason)


def one(values, reason):
    require(len(values) == 1, reason + ": expected one, got " + str(len(values)))
    return values[0]


def pin(node, name):
    return one([p for p in node.list_all_pins() if str(p.get_pin_name()) == name],
               node.get_path_name() + "." + name)


def connect(source, source_name, target, target_name):
    output, incoming = pin(source, source_name), pin(target, target_name)
    require(output.try_create_connection(incoming), "原生连接拒绝 " + source_name + " -> " + target_name)
    require(any(p.is_same_native_pin(incoming) for p in output.list_connected_pins()), "连接读回缺失")


def named(editor, name):
    return one([n for n in editor.list_all_nodes() if n.get_name() == name], "原节点 " + name)


NODE_CLASS_PATHS = {
    **{name: "/Script/AnimGraph." + name for name in (
        "AnimGraphNode_SequencePlayer", "AnimGraphNode_StateResult", "AnimGraphNode_TransitionResult",
        "K2Node_AnimGetter", "AnimStateNode")},
    **{name: "/Script/BlueprintGraph." + name for name in (
        "K2Node_CallFunction", "K2Node_FunctionEntry", "K2Node_PromotableOperator")},
}


def resolve_node_class(path):
    cls = ue.load_class(None, path)
    require(cls is not None, "必需 UClass 不可解析：" + path)
    require(cls.get_path_name() == path, "UClass 模块归属不符：" + path)
    return cls


def require_node_classes(editor, names, reason):
    wanted = [resolve_node_class(NODE_CLASS_PATHS[name]) for name in names]
    nodes = list(editor.list_all_nodes())
    require(len(nodes) == len(wanted) and all(
        sum(n.get_class() == cls for n in nodes) == wanted.count(cls) for cls in wanted), reason)


def node_class(editor, class_name):
    cls = resolve_node_class(NODE_CLASS_PATHS[class_name])
    return one([n for n in editor.list_all_nodes() if n.get_class() == cls], class_name)


def animation_node(blueprint, editor, class_path, position):
    node_type = resolve_node_class(class_path)
    require(node_type is not None, "动画节点类缺失 " + class_path)
    result = ue.GGYGOAnimationGraphEditorLibrary.create_animation_node(
        blueprint, editor.get_graph(), node_type, ue.Vector2D(*position))
    require(result.succeeded, str(result.error))
    node = result.node
    require(node is not None and node.get_class() == node_type, "原生节点类型读回不符 " + class_path)
    return node


def function_node(editor, declaring_class, member):
    require(ue.load_class(None, declaring_class) is not None, "声明类不存在 " + declaring_class)
    node = editor.add_call_function_node(declaring_class + "." + member)
    require(node is not None, "原生函数创建拒绝 " + declaring_class + "." + member)
    called = str(ue.GGYGOAnimationGraphEditorLibrary.get_called_function_name(node))
    require(called == member, "原生函数目标读回不符：" + called)
    return node


def copy_struct(value):
    """原生 StructBase.copy() 是无 owner 的独立实例；get_editor_property 返回的是
    绑定原对象内存的引用，绝不能直接在其上 import_text 试写。"""
    result = value.copy()
    require(type(result) is type(value) and result.export_text() == value.export_text(), "原生结构复制改变字段")
    return result


def linked_only_to(source, source_name, target, target_name):
    links = pin(source, source_name).list_connected_pins()
    return len(links) == 1 and links[0].is_same_native_pin(pin(target, target_name))


def unit(values):
    length = math.sqrt(sum(v * v for v in values))
    require(math.isfinite(length) and length > 1.e-8, "参考膝弯方向退化")
    return [v / length for v in values]


def knee_axis(leg):
    foot, knee, hip = leg["parent_chain"][:3]
    transforms = leg["reference_component"]
    subtract = lambda a, b: [x - y for x, y in zip(a, b)]
    direction = unit(subtract(transforms[foot]["translation"], transforms[hip]["translation"]))
    joint = subtract(transforms[knee]["translation"], transforms[hip]["translation"])
    projection = sum(a * b for a, b in zip(joint, direction))
    bend = unit([a - projection * b for a, b in zip(joint, direction)])
    # 共轭单位 Quaternion 将真实参考 CS 膝弯向量转到髋局部空间。
    x, y, z, w = transforms[hip]["rotation"]
    require(abs(x*x + y*y + z*z + w*w - 1.) < 1.e-5, "参考髋 Quaternion 未归一化")
    q = [-x, -y, -z]
    cross = lambda a, b: [a[1]*b[2]-a[2]*b[1], a[2]*b[0]-a[0]*b[2], a[0]*b[1]-a[1]*b[0]]
    uv = cross(q, bend)
    uuv = cross(q, uv)
    return unit([bend[i] + 2. * (w * uv[i] + uuv[i]) for i in range(3)])


def lean_curve_keys(response):
    return ue.GGYGOAnimationGraphEditorLibrary.read_runtime_curve_keys(response)


def require_lean_curve(response, label):
    keys = lean_curve_keys(response)
    require(tuple((float(k.time), float(k.value)) for k in keys) == LEAN_KEYS, label + "：响应曲线原生键值读回不符")
    # 原生 ERichCurveInterpMode 的 RCIM_Linear 为 0；与运行时校验同样要求 [0,180]、零偏差零倾身、值在 [0,90)。
    require(all(int(k.interp_mode) == 0 for k in keys), label + "：响应曲线不是原生线性插值")
    require(keys[0].time == 0. and keys[-1].time == 180. and keys[0].value == 0.
            and all(0. <= k.value < 90. for k in keys), label + "：响应曲线越出运行时契约")


def preflight_lean_tuning(anim):
    """只在独立 Tuning 副本试导入角色响应曲线；资产 Tuning 导出前后必须相同。"""
    original_export = anim.get_editor_property("Tuning").export_text()
    trial = copy_struct(anim.get_editor_property("Tuning"))
    settings = trial.get_editor_property("WalkRunLean")  # 引用属于 trial 副本
    require(settings.get_editor_property("bEnabled"), "本角色未开启原 WalkRunLean")
    response = settings.get_editor_property("DirectionErrorToLeanDegrees")
    keys = ",".join("(InterpMode=RCIM_Linear,Time=%.17g,Value=%.17g)" % item for item in LEAN_KEYS)
    require(response.import_text("(EditorCurveData=(Keys=(" + keys + ")),ExternalCurve=None)"), "角色响应曲线导入拒绝")
    settings.set_editor_property("DirectionErrorToLeanDegrees", response)
    trial.set_editor_property("WalkRunLean", settings)
    require_lean_curve(trial.get_editor_property("WalkRunLean").get_editor_property("DirectionErrorToLeanDegrees"),
                       "Tuning 试导入")
    require(anim.get_editor_property("Tuning").export_text() == original_export, "试导入改变了资产 Tuning")
    return trial, original_export


def preflight_walk_run(editor, anim, mesh):
    original = named(editor, "AnimGraphNode_ModifyBone_0")
    require(str(original.get_editor_property("Node").get_editor_property("BoneToModify")
                .get_editor_property("BoneName")) == "Bip001-Spine", "旧 Spine 节点不符")
    source = named(editor, "AnimGraphNode_LocalToComponentSpace_0")
    target = named(editor, "AnimGraphNode_ComponentToLocalSpace_0")
    alpha = named(editor, "K2Node_CallFunction_2")
    angle = named(editor, "K2Node_VariableGet_1")
    rotator = named(editor, "K2Node_CallFunction_1")
    require(linked_only_to(original, "ComponentPose", source, "ComponentPose"), "旧 Spine 输入链已改变")
    require(linked_only_to(original, "Pose", target, "ComponentPose"), "旧 Spine 输出链已改变")
    require(linked_only_to(rotator, "ReturnValue", original, "Rotation"), "旧 Rotator 存在其它消费者")
    require(linked_only_to(alpha, "ReturnValue", original, "Alpha"), "旧 Alpha 链已改变")
    require(str(ue.GGYGOAnimationGraphEditorLibrary.get_called_function_name(alpha)) == "SelectFloat", "旧 Alpha 选择函数不符")
    pin(angle, "WalkRunLeanAngleDegrees")
    # BodyLean 轴/上方向输入来自既有 Transient 表现属性；缺失时 get_editor_property 直接拒绝。
    for name in ("WalkRunLeanAxisCS", "WalkRunLeanUpCS"):
        require(isinstance(anim.get_editor_property(name), ue.Vector), "缺少表现属性 " + name)
    # reference_legs 已拒绝缺骨、父链不含 Body 或双腿链重叠，与节点编译校验同一骨链约束。
    legs = reference_legs(ue, mesh)
    lean_config, lean_base_export = preflight_body_lean_config(legs)
    tuning, tuning_export = preflight_lean_tuning(anim)
    return {"original": original, "source": source, "target": target, "alpha": alpha, "angle": angle,
            "rotator": rotator, "legs": legs, "lean_config": lean_config, "lean_base_export": lean_base_export,
            "tuning": tuning, "tuning_export": tuning_export}


def preflight_body_lean_config(legs):
    """在 BodyLean 节点类 CDO 的 Node 独立副本上完成全部骨/膝轴配置并读回；CDO 不变。

    新建节点由 FGraphNodeCreator 以该类默认值构造，apply 先核其 Node 等同这里的类默认导出，
    再整体 set 此配置，因此骨名导入失败不会发生在图修改之后。
    """
    defaults = ue.get_default_object(ue.load_class(None, BODY_LEAN_NODE))
    base_export = defaults.get_editor_property("Node").export_text()
    config = copy_struct(defaults.get_editor_property("Node"))
    body = config.get_editor_property("Body")  # 引用属于独立 config
    require(body.import_text("(BoneName=" + BODY + ")"), "Body 骨配置拒绝")
    config.set_editor_property("Body", body)
    require(str(config.get_editor_property("Body").get_editor_property("BoneName")) == BODY, "Body 骨配置读回不符")
    for field, foot in zip(("LeftLeg", "RightLeg"), FEET):
        axis = knee_axis(legs[foot])
        # 与 BodyLean 节点编译及 InitializeBoneReferences 的单位轴容差一致。
        require(abs(sum(v * v for v in axis) - 1.) < 1.e-4, foot + "：参考膝弯轴不是单位向量")
        leg = config.get_editor_property(field)
        bone = leg.get_editor_property("Foot")
        require(bone.import_text("(BoneName=" + foot + ")"), foot + "：脚骨配置拒绝")
        leg.set_editor_property("Foot", bone)
        leg.set_editor_property("KneeBendAxisLocal", ue.Vector(*axis))
        config.set_editor_property(field, leg)
        stored = config.get_editor_property(field)
        stored_axis = stored.get_editor_property("KneeBendAxisLocal")
        require(str(stored.get_editor_property("Foot").get_editor_property("BoneName")) == foot
                and max(abs(a - b) for a, b in zip((stored_axis.x, stored_axis.y, stored_axis.z), axis)) < 1.e-6,
                field + "：脚骨或膝轴配置读回不符")
    require(defaults.get_editor_property("Node").export_text() == base_export, "试配置改变了 BodyLean 类默认值")
    return config, base_export


def apply_walk_run(editor, blueprint, anim, plan):
    original = plan["original"]
    lean = animation_node(blueprint, editor, BODY_LEAN_NODE, (original.get_node_pos().x, original.get_node_pos().y))
    require(lean.get_editor_property("Node").export_text() == plan["lean_base_export"],
            "新建 BodyLean 默认配置与类默认不一致；保留 unsaved 现场")
    config = plan["lean_config"]
    lean.set_editor_property("Node", config)
    require(lean.get_editor_property("Node").export_text() == config.export_text(), "BodyLean 配置读回不符")
    axis = editor.add_get_member_variable_node("WalkRunLeanAxisCS", "")
    up = editor.add_get_member_variable_node("WalkRunLeanUpCS", "")
    connect(plan["source"], "ComponentPose", lean, "ComponentPose")
    connect(lean, "Pose", plan["target"], "ComponentPose")
    connect(plan["alpha"], "ReturnValue", lean, "Alpha")
    connect(plan["angle"], "WalkRunLeanAngleDegrees", lean, "LeanDegrees")
    connect(axis, "WalkRunLeanAxisCS", lean, "LeanAxisCS")
    connect(up, "WalkRunLeanUpCS", lean, "UpDirectionCS")
    editor.remove_nodes([original, plan["rotator"]])
    require(anim.get_editor_property("Tuning").export_text() == plan["tuning_export"], "接线期间资产 Tuning 已改变")
    anim.set_editor_property("Tuning", plan["tuning"])
    return {"body": BODY, "legs": plan["legs"], "lean_keys": LEAN_KEYS,
            "body_lean_node": lean.get_path_name(), "authored": config.export_text()}


def preflight_turn_back(editor, exit_editor, blueprint, anim):
    old_player = node_class(editor, "AnimGraphNode_SequencePlayer")
    result = node_class(editor, "AnimGraphNode_StateResult")
    source_lookup = node_class(editor, "K2Node_CallFunction")
    require(str(ue.GGYGOAnimationGraphEditorLibrary.get_called_function_name(source_lookup)) == "GetSeqByKey",
            "原 TurnBack 源查询函数不符")
    require(str(pin(source_lookup, "Key").get_pin_value()).casefold() == "turnback", "原 TurnBack 源键不符")
    require(linked_only_to(source_lookup, "ReturnValue", old_player, "Sequence"), "原 TurnBack 源连线已改变")
    require(linked_only_to(old_player, "Pose", result, "Result"), "原 TurnBack 姿态输出已改变")
    sequence = anim.get_seq_by_key("TurnBack")
    require(sequence is not None, "原 TurnBack 配置源缺失")
    require(ue.BlueprintEditorLibrary.find_graph(blueprint, POSE_FUNCTION) is None, "源姿态函数已存在；拒绝重复迁移")
    # UpdateFunction 是 UAnimGraphNode_Base 的 FMemberReference；在原播放器同类型属性的独立副本上试导入。
    player_export = old_player.get_editor_property("UpdateFunction").export_text()
    member = copy_struct(old_player.get_editor_property("UpdateFunction"))
    require(member.import_text("(MemberName=" + POSE_FUNCTION + ",bSelfContext=True)")
            and POSE_FUNCTION in member.export_text(), "原生节点更新函数引用拒绝")
    require(old_player.get_editor_property("UpdateFunction").export_text() == player_export, "试导入改变了原播放器")
    exit_result = node_class(exit_editor, "AnimGraphNode_TransitionResult")
    return {"old_player": old_player, "result": result, "source_lookup": source_lookup, "sequence": sequence,
            "update_function": member, "exit_result": exit_result,
            "old_exit": [n for n in exit_editor.list_all_nodes() if n != exit_result]}


def apply_turn_back(editor, exit_editor, blueprint, plan):
    old_player, result, sequence = plan["old_player"], plan["result"], plan["sequence"]
    evaluator = animation_node(blueprint, editor, EVALUATOR_NODE,
                               (old_player.get_node_pos().x, old_player.get_node_pos().y))
    config = copy_struct(evaluator.get_editor_property("Node"))
    for field, value in (("Sequence", sequence), ("ExplicitTime", 0.), ("bShouldLoop", False),
                         ("bTeleportToExplicitTime", True), ("bUseExplicitFrame", False)):
        config.set_editor_property(field, value)
    evaluator.set_editor_property("Node", config)
    dynamic = ue.GGYGOAnimationGraphEditorLibrary.mark_animation_node_properties_dynamic(
        blueprint, evaluator, ["Sequence", "ExplicitTime"])
    require(dynamic.succeeded, str(dynamic.error))
    graph = ue.BlueprintEditorLibrary.add_function_graph(blueprint, POSE_FUNCTION)
    function = ue.BlueprintGraphEditor.get_graph_editor(graph)
    require(function is not None, "源姿态更新函数创建拒绝")
    function.set_is_thread_safe_function(True)
    function.set_function_is_private()
    convert = function_node(function, EVALUATOR_LIBRARY, "ConvertToSequenceEvaluator")
    # 仅借用公开 pin 类型，删除该未接线节点，不执行/保留推进时间或惯性混合调用。
    prototype = function_node(function, EVALUATOR_LIBRARY, "SetSequenceWithInertialBlending")
    context = function.add_graph_input_parameter("Context", pin(prototype, "UpdateContext").get_pin_type(), "")
    node = function.add_graph_input_parameter("Node", pin(convert, "Node").get_pin_type(), "")
    function.remove_nodes([prototype])
    require(str(context.get_pin_name()) == "Context" and str(node.get_pin_name()) == "Node", "更新原型参数不符")
    entry = node_class(function, "K2Node_FunctionEntry")
    # 姿态写入与真实节点消费记录在同一原生调用中完成；远端 Held 只对已进入该段的同一节点生效。
    # 无可用姿态时该调用不写节点，保持上一显式时间，不写 null/0 或换另一动作。
    apply = function_node(function, BASE, "ApplyMotionPoseToEvaluator")
    require(pin(apply, "MotionType").set_pin_value("TurnBack"), "运动源类型拒绝")
    connect(entry, "then", convert, "execute")
    connect(entry, "Node", convert, "Node")
    connect(convert, "Succeeded", apply, "execute")
    connect(entry, "Context", apply, "UpdateContext")
    connect(convert, "ReturnValue", apply, "Evaluator")
    evaluator.set_editor_property("UpdateFunction", plan["update_function"])
    # 原生写入时会补全 MemberGuid（实测 Saved/Codex/AnimationRemoteIntegration_20261012_R4），
    # 逐字导出比较必然不等；只按引用语义读回：同一函数名且为 Self 上下文。
    stored = evaluator.get_editor_property("UpdateFunction").export_text()
    require('MemberName="' + POSE_FUNCTION + '"' in stored and "bSelfContext=True" in stored,
            "Evaluator 更新函数引用读回不符")
    connect(evaluator, "Pose", result, "Result")
    editor.remove_nodes([old_player, plan["source_lookup"]])
    # 同源认证自然末端可以正常融合退出（远端 Provider 资格等待时也只用保留的真实关闭事实，不造终点姿态）；
    # 原 Phase 消失也允许原取消/失败生命周期退出。合法等待保留相位，不被当作完成。
    # 此规则不向 GAS/CMC 发布 Finished，RunOut 本身仍不等于动画源结束。
    exit_result = plan["exit_result"]
    valid_end = function_node(exit_editor, BASE, "IsMotionPoseEnded")
    require(pin(valid_end, "MotionType").set_pin_value("TurnBack"), "退出同源类型拒绝")
    curve_phase = function_node(exit_editor, BASE, "IsTurnBackCurveDriven")
    run_out = exit_editor.add_get_member_variable_node("bTurnBackRunOut", "")
    phase_none = function_node(exit_editor, MATH_LIBRARY, "BooleanNOR")
    exit_or = function_node(exit_editor, MATH_LIBRARY, "BooleanOR")
    connect(curve_phase, "ReturnValue", phase_none, "A")
    connect(run_out, "bTurnBackRunOut", phase_none, "B")
    connect(valid_end, "ReturnValue", exit_or, "A")
    connect(phase_none, "ReturnValue", exit_or, "B")
    connect(exit_or, "ReturnValue", exit_result, "bCanEnterTransition")
    exit_editor.remove_nodes(plan["old_exit"])
    return {"evaluator": evaluator.get_path_name(), "sequence": sequence.get_path_name(),
            "update_function": graph.get_path_name(), "exit_graph": exit_editor.get_graph().get_path_name()}


def original_turn_back_entry(entry_editor):
    """只接受原“仅 IsTurnBackCurveDriven”规则；修改前后同一校验。"""
    require_node_classes(entry_editor, ["AnimGraphNode_TransitionResult", "K2Node_CallFunction"], "原 TurnBack 进入规则包含其它逻辑，拒绝覆盖")
    result = node_class(entry_editor, "AnimGraphNode_TransitionResult")
    old_phase = node_class(entry_editor, "K2Node_CallFunction")
    require(str(ue.GGYGOAnimationGraphEditorLibrary.get_called_function_name(old_phase)) == "IsTurnBackCurveDriven",
            "原 TurnBack 进入规则函数不符")
    incoming = pin(result, "bCanEnterTransition").list_connected_pins()
    require(len(incoming) == 1 and incoming[0].is_same_native_pin(pin(old_phase, "ReturnValue")), "原进入规则连接已改变")
    return result, old_phase


def apply_turn_back_entry(entry_editor):
    """进入 TurnBack 须同时有曲线相位和 CMC 已完成同源区间。

    相位来自 CMC 当前状态；本地 D0 首次 Turning 时完成区间可能尚未发布，Simulated
    Proxy／重放／过期或被替换的区间也会是 NotApplicable。此时进入只会求值 Evaluator
    的作者默认时间，等于偷换 0 时刻；因此留在原状态等待真实完成区间，不写 0、
    不发布 Finished。已结束区间不再进入，结束由退出规则读取 bEnded。
    """
    result, old_phase = original_turn_back_entry(entry_editor)
    phase = function_node(entry_editor, BASE, "IsTurnBackCurveDriven")
    source = function_node(entry_editor, BASE, "IsMotionPoseActive")
    require(pin(source, "MotionType").set_pin_value("TurnBack"), "进入同源类型拒绝")
    both = function_node(entry_editor, MATH_LIBRARY, "BooleanAND")
    entry_editor.remove_nodes([old_phase])
    connect(phase, "ReturnValue", both, "A")
    connect(source, "ReturnValue", both, "B")
    connect(both, "ReturnValue", result, "bCanEnterTransition")
    require(len(pin(result, "bCanEnterTransition").list_connected_pins()) == 1, "进入规则结果存在多余连接")
    return {"entry_graph": entry_editor.get_graph().get_path_name()}


def preflight_transitions(blueprint, graphs, walk, turn, exit_graph):
    """真实过渡方向和规则标志来自 GGYGOEditor 只读接口；原 getter 关联只作一致性旁证。

    过渡节点不是 K2 节点，BlueprintGraphEditor.list_all_nodes 无法枚举；共享规则的过渡
    也不拥有可由 list_graphs 列出的规则图，因此按状态机读取全部过渡。
    """
    require(hasattr(ue.GGYGOAnimationGraphEditorLibrary, "read_state_machine_transitions"),
            "当前 GGYGOEditor DLL 缺少过渡端点读取接口；需同版新构建，拒绝退回结构计数")
    machine = turn.get_outer().get_outer()
    require(walk.get_outer().get_outer() == machine, "WalkRun 与 TurnBack 不在同一原状态机")
    # 本角色迁移的资产前提：原机只有这两个状态与两条过渡；方向由下方原生端点证明，不由数量推断。
    require(sorted(g.get_name() for g in graphs if g.get_outer().get_class() == resolve_node_class(NODE_CLASS_PATHS["AnimStateNode"])
                   and g.get_outer().get_outer() == machine) == ["TurnBack", "WalkRun"],
            "TurnBack 所属状态机不是原 TurnBack／WalkRun 两状态")
    read = ue.GGYGOAnimationGraphEditorLibrary.read_state_machine_transitions(blueprint, machine)
    require(read.succeeded, str(read.error))
    require(read.state_machine_graph == machine, "过渡读取返回了另一状态机")
    transitions = list(read.transitions)
    require(len(transitions) == 2, "TurnBack 所属状态机不是原两条过渡")
    entry = one([t for t in transitions if t.next_state_graph == turn], "进入 TurnBack 的过渡")
    exit_ = one([t for t in transitions if t.previous_state_graph == turn], "离开 TurnBack 的过渡")
    require(entry.previous_state_graph == walk, "TurnBack 进入不是来自 WalkRun")
    require(exit_.next_state_graph == walk, "TurnBack 退出不是回到 WalkRun")
    facts = {}
    for label, item in (("entry", entry), ("exit", exit_)):
        require(item.rule_graph_owned and not item.shared_rules and not item.bound_graph_shared,
                label + "：共享规则图，修改会影响另一过渡")
        require(not item.bidirectional and not item.disabled, label + "：双向或禁用过渡")
        require(not item.automatic_rule, label + "：自动规则可绕过规则图结果")
        require(int(item.logic_type) != TRANSITION_LOGIC_CUSTOM, label + "：未审自定义过渡混合")
        facts[label] = {"transition": item.transition.get_path_name(), "rule_graph": item.rule_graph.get_path_name(),
                        "logic_type": int(item.logic_type),
                        "has_custom_transition_graph": bool(item.has_custom_transition_graph)}
    require(exit_.rule_graph == exit_graph and entry.rule_graph != exit_graph, "过渡规则图与原 getter 退出不一致")
    return entry.rule_graph, facts


def require_native_interfaces():
    """prepare 将创建的类与函数在修改前全部可解析。

    add_call_function_node 以 FSoftObjectPath("类路径.函数") 解析，即 Outer 为该类、名为函数的
    UFunction；这里用同一 Outer/名称并限定 Function 类型读取同一对象。
    """
    for class_path, members in REQUIRED_FUNCTIONS:
        declaring = ue.load_class(None, class_path)
        require(declaring is not None, "声明类不存在 " + class_path)
        for member in members:
            require(ue.find_object(declaring, member, ue.Function) is not None,
                    "原生函数缺失 " + class_path + "." + member)
    for class_path in (BODY_LEAN_NODE, EVALUATOR_NODE, OBSERVER):
        require(ue.load_class(None, class_path) is not None, "原生类缺失 " + class_path)


def preflight(blueprint, mesh, package=ABP):
    """全只读；返回本次调用栈内使用的局部计划，不保存、不跨调用缓存。

    @param package 生产为 ABP；仅自有宿主的 /Temp 内存副本验证可传入其包路径，
           此时只允许该包自身 dirty。
    """
    before = dirty(ue)
    if package == ABP:
        require(not before["content"] and not before["maps"], "存在未保存工作，拒绝制作")
    else:
        require(package.startswith("/Temp/") and not before["maps"] and set(before["content"]).issubset({package}),
                "非生产包只允许自有 /Temp 内存副本，且不得有其它未保存工作")
    require(isinstance(blueprint, ue.AnimBlueprint)
            and blueprint.get_path_name() == package + "." + package.rsplit("/", 1)[1], "目标 ABP 不符")
    require(mesh is not None and mesh.get_path_name() == MESH + "." + MESH.rsplit("/", 1)[1], "参考 Mesh 不符")
    require_native_interfaces()
    graphs = list(ue.BlueprintEditorLibrary.list_graphs(blueprint))
    walk = one([g for g in graphs if g.get_name() == "WalkRun"], "WalkRun graph")
    turn = one([g for g in graphs if g.get_name() == "TurnBack"], "TurnBack graph")
    exits = []
    for graph in graphs:
        editor = ue.BlueprintGraphEditor.get_graph_editor(graph)
        for node in editor.list_all_nodes():
            if node.get_class() == resolve_node_class(NODE_CLASS_PATHS["K2Node_AnimGetter"]):
                association = ue.GGYGOAnimationGraphEditorLibrary.read_getter_association(node)
                require(association.succeeded, str(association.error))
                if association.source_state_graph == turn:
                    require(str(association.function_name) == "GetRelevantAnimTimeRemainingFraction",
                            "原退出 getter 原生函数不符")
                    exits.append(graph)
    exit_graph = one(exits, "实际关联 TurnBack 的原 fraction 退出")
    entry_graph, transition_facts = preflight_transitions(blueprint, graphs, walk, turn, exit_graph)
    entry_editor = ue.BlueprintGraphEditor.get_graph_editor(entry_graph)
    exit_editor = ue.BlueprintGraphEditor.get_graph_editor(exit_graph)
    original_turn_back_entry(entry_editor)
    require_node_classes(exit_editor, ["AnimGraphNode_TransitionResult", "K2Node_AnimGetter", "K2Node_PromotableOperator"],
            "原退出规则包含其它逻辑，拒绝覆盖")
    require(float(pin(node_class(exit_editor, "K2Node_PromotableOperator"), "B").get_pin_value()) == 0.03,
            "原退出 fraction 阈值已改变")
    anim = ue.get_default_object(blueprint.generated_class())
    require(isinstance(anim.get_editor_property("bTurnBackRunOut"), bool), "缺少 bTurnBackRunOut 表现属性")
    walk_editor = ue.BlueprintGraphEditor.get_graph_editor(walk)
    turn_editor = ue.BlueprintGraphEditor.get_graph_editor(turn)
    plan = {"package": package, "anim": anim, "walk_editor": walk_editor, "turn_editor": turn_editor,
            "entry_editor": entry_editor, "exit_editor": exit_editor, "transitions": transition_facts,
            "anim_set_export": anim.get_editor_property("AnimSet").export_text(),
            "root_motion_mode": str(anim.get_editor_property("RootMotionMode")),
            "walk_run": preflight_walk_run(walk_editor, anim, mesh),
            "turn_back": preflight_turn_back(turn_editor, exit_editor, blueprint, anim)}
    require(dirty(ue) == before, "preflight 改变了 dirty；保留实际宿主状态")
    return plan


def prepare(blueprint, mesh, package=ABP):
    """同步 GT 调用：fresh preflight 后立即消费局部计划，修改、完整编译并读回。

    已知坏配置在 preflight 拒绝且图未变；之后的原生建节点、连线或编译失败保留本次
    未保存现场，由调用方诊断，不回滚、不 SaveAll。返回事实不代表已保存或运行通过。
    """
    plan = preflight(blueprint, mesh, package)
    anim = plan["anim"]
    walk_facts = apply_walk_run(plan["walk_editor"], blueprint, anim, plan["walk_run"])
    turn_facts = apply_turn_back(plan["turn_editor"], plan["exit_editor"], blueprint, plan["turn_back"])
    turn_facts.update(apply_turn_back_entry(plan["entry_editor"]))
    turn_facts["transitions"] = plan["transitions"]
    require(ue.BlueprintEditorLibrary.compile_blueprint(blueprint), "完整 ABP 编译拒绝；保留 unsaved 现场")
    current = ue.get_default_object(blueprint.generated_class())
    require(str(current.get_editor_property("RootMotionMode")) == plan["root_motion_mode"], "制作改变 RootMotionMode")
    require(current.get_editor_property("AnimSet").export_text() == plan["anim_set_export"], "制作改变 AnimSet")
    current_tuning = current.get_editor_property("Tuning")
    require_lean_curve(current_tuning.get_editor_property("WalkRunLean").get_editor_property("DirectionErrorToLeanDegrees"),
                       "编译后 Tuning")
    # 将唯一目标曲线换回原值后，完整 Tuning 必须仍逐字段等同；只改独立副本，不保存。
    original_tuning = copy_struct(current_tuning)
    require(original_tuning.import_text(plan["walk_run"]["tuning_export"]), "原 Tuning 导出无法回读")
    check_tuning = copy_struct(current_tuning)
    check_lean = check_tuning.get_editor_property("WalkRunLean")
    check_lean.set_editor_property("DirectionErrorToLeanDegrees", original_tuning.get_editor_property("WalkRunLean")
                                   .get_editor_property("DirectionErrorToLeanDegrees"))
    check_tuning.set_editor_property("WalkRunLean", check_lean)
    require(check_tuning.export_text() == plan["walk_run"]["tuning_export"], "制作改变其它 Tuning 字段")
    after = dirty(ue)
    require(not after["maps"] and set(after["content"]).issubset({package}), "制作污染其它包")
    return {"prepared": True, "saved_assets": False, "runtime_or_visual_proof": False,
            "root_motion_mode": plan["root_motion_mode"], "walk_run": walk_facts, "turn_back": turn_facts}
