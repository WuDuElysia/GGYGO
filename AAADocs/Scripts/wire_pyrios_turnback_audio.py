"""在 BP_PC_Pyrios 的既有 MovementUpdated 委托上接 TurnBack 起始衣甲声。

项目配置：首次进入 Turning 播第一段 Foley；离开 Turning 后允许下一次转身。
只观察 CMC 的公开相位，不驱动位移或动画。音频附着 Mesh，由引擎自然结束并销毁。
在独立 Editor 调用 apply(ue, output_dir)，只保存该 Blueprint。
"""
import json
import shutil
from pathlib import Path

BP = "/Game/BP/Character/Player/BP_PC_Pyrios"
SOUND = "/Game/Characters/Player/Pyrios/Audio/TurnBack/SW_Pyrios_Foley_Pyrois_TurnBack"
MARKER = "GGYGO.TurnBackFoley"
VARIABLE = "bWasTurnBackTurningForFoley"
CHARACTER = "/Script/Engine.Character"
BASE = "/Script/GGYGO.GGYGOCharacterBase"
CMC = "/Script/GGYGO.GGYGOCharacterMovementComponent"


def require(condition, reason):
    if not condition:
        raise RuntimeError("[Pyrios.TurnBackFoley] " + reason)


def pin(node, name):
    matches = [p for p in node.list_all_pins() if str(p.get_pin_name()) == name]
    require(len(matches) == 1, node.get_name() + " 缺唯一 Pin " + name)
    return matches[0]


def connect(source, target):
    require(source.try_create_connection(target), "连接失败 " + str(source.get_pin_name()) + " → " + str(target.get_pin_name()))


def apply(ue, output_dir):
    require(not ue.EditorLevelLibrary.get_pie_worlds(True), "PIE 期间不能制作角色 Blueprint")
    blueprint = ue.load_asset(BP)
    require(isinstance(blueprint, ue.Blueprint), "缺角色 Blueprint")
    dirty = set(ue.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    require(blueprint.get_outermost() not in dirty, "角色 Blueprint 已有未保存工作")
    sound = ue.load_asset(SOUND)
    require(isinstance(sound, ue.SoundWave), "缺已选 Foley")
    library = ue.BlueprintEditorLibrary
    graph = library.find_event_graph(blueprint)
    require(graph is not None, "角色缺 EventGraph")
    editor = ue.BlueprintGraphEditor.get_graph_editor(graph)
    metadata = ue.GGYGOAnimationGraphEditorLibrary
    old_nodes = list(editor.list_all_nodes())
    for node in old_nodes:
        comment = metadata.read_blueprint_node_comment(blueprint, node)
        require(comment.succeeded, "节点注释读取失败")
        require(not str(comment.comment).startswith(MARKER), "已经接过转身声音，不重复插入")
    require(not any(str(name).rsplit(".", 1)[-1] == VARIABLE for name in library.list_member_variable_names(blueprint, True)),
            "表现观察变量已存在")
    begin = editor.find_event_node("ReceiveBeginPlay")
    require(begin is not None, "角色必须已有 BeginPlay，先核对生产初始化链")
    start = pin(begin, "then")
    original_tail = list(start.list_connected_pins())
    require(len(original_tail) <= 1, "BeginPlay 存在多个后继")
    actions = list(map(str, editor.list_available_nodes([])))

    def action(suffix):
        matches = [value for value in actions if value.rsplit("|", 1)[-1] == suffix]
        require(len(matches) == 1, "原生节点不唯一或不存在 " + suffix)
        return matches[0]

    bind_action = action("BindEventtoOnCharacterMovementUpdated")
    self_nodes = [n for n in old_nodes if n.get_class().get_path_name() == "/Script/BlueprintGraph.K2Node_Self"]
    require(bool(self_nodes), "角色 EventGraph 缺 Self 节点")
    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    shutil.copy2(Path(ue.Paths.project_content_dir()) / "BP/Character/Player/BP_PC_Pyrios.uasset",
                 output / "BP_PC_Pyrios.before.uasset")
    require(editor.add_member_variable(VARIABLE, library.get_basic_type_by_name("bool"), "false"), "创建表现变量失败")
    require(library.compile_blueprint(blueprint), "表现变量编译失败")
    editor = ue.BlueprintGraphEditor.get_graph_editor(graph)
    created = []
    left = max([n.get_node_pos().x for n in old_nodes] + [0]) + 800

    def place(node, label):
        require(node is not None, "创建节点失败 " + label)
        node.set_node_pos(ue.IntPoint(left + (len(created) % 5) * 480, (len(created) // 5) * 350))
        result = metadata.write_blueprint_node_comment(blueprint, node, MARKER + ": " + label)
        require(result.succeeded, "节点注释写入失败 " + label)
        created.append(node)
        return node

    def call(path, name, **values):
        node = place(editor.add_call_function_node(path + "." + name), name)
        for key, value in values.items():
            target = pin(node, key)
            if isinstance(value, str):
                require(target.set_pin_value(value), "常量设置失败 " + name + "." + key)
            else:
                connect(value, target)
        return node

    def branch(flow, condition, label):
        node = place(editor.add_branch_node(), label)
        connect(flow, pin(node, "execute"))
        connect(condition, pin(node, "Condition"))
        return node

    def set_observed(flow, value):
        node = place(editor.add_set_member_variable_node(VARIABLE, ""), "记录本次观察是否在 Turning")
        require(pin(node, VARIABLE).set_pin_value(value), "设置观察值失败")
        connect(flow, pin(node, "execute"))
        return pin(node, "then")

    self_node = self_nodes[0]
    owner = pin(self_node, "self")
    binding = place(editor.create_node_from_name(bind_action, ue.Vector2D(0, 0), [], ue.Character.static_class()),
                    "订阅既有 CharacterMovementUpdated")
    require(binding.get_class().get_path_name() == "/Script/BlueprintGraph.K2Node_AddDelegate", "绑定节点类型不符")
    event = place(editor.add_dispatcher_event_node("OnCharacterMovementUpdated", ue.Character.static_class()),
                  "原生移动完成后只读观察转身相位")
    connect(owner, pin(binding, "self"))
    connect(pin(event, "OutputDelegate"), pin(binding, "Delegate"))
    movement = call(BASE, "GetGGYGOMovementComponent", self=owner)
    phase = call(CMC, "GetTurnBackPhase", self=pin(movement, "ReturnValue"))
    turning = call("/Script/Engine.KismetMathLibrary", "EqualEqual_ByteByte",
                   A=pin(phase, "ReturnValue"), B=str(ue.GGYGOTurnBackPhase.TURNING.value))
    current = branch(pin(event, "then"), pin(turning, "ReturnValue"), "Turning 入场播放")
    previous = place(editor.add_get_member_variable_node(VARIABLE, ""), "上次观察相位，仅用于音频去重")
    already_played = branch(pin(current, "then"), pin(previous, VARIABLE), "同一次 Turning 只播放一次")
    play_flow = set_observed(pin(already_played, "else"), "true")
    set_observed(pin(current, "else"), "false")
    mesh = place(editor.add_get_member_variable_node("Mesh", CHARACTER), "声音跟随角色 Mesh")
    audio = call("/Script/Engine.GameplayStatics", "SpawnSoundAttached", Sound=sound.get_path_name(),
                 AttachToComponent=pin(mesh, "Mesh"), AttachPointName="None", bStopWhenAttachedToDestroyed="true",
                 VolumeMultiplier="1", PitchMultiplier="1", StartTime="0", bAutoDestroy="true")
    connect(play_flow, pin(audio, "execute"))

    # 新链完整后才接入既有 BeginPlay，保留原初始化后继。
    for successor in original_tail:
        start.break_single_pin_link(successor)
        connect(pin(binding, "then"), successor)
    connect(start, pin(binding, "execute"))
    editor.add_comment_to_nodes("项目配置：TurnBack 起始播放第一段衣甲声一次；原版触发条件未知。\n"
                                "监听原生移动完成事件，读取 CMC 相位；不驱动运动。RunOut 后重入 Turning 可再次播放。",
                                created, 70)
    require(library.compile_blueprint(blueprint), "TurnBack 声音图编译失败")
    require(ue.EditorAssetLibrary.save_loaded_asset(blueprint, False), "角色 Blueprint 保存失败")
    report = {"blueprint": blueprint.get_path_name(), "sound": sound.get_path_name(),
              "configuration_source": "项目配置：用户选择转身起始播放第一段一次", "compiled": True, "saved": True,
              "nodes": [{"name": n.get_name(), "class": n.get_class().get_path_name(),
                         "pins": [{"name": str(p.get_pin_name()), "value": str(p.get_pin_value()),
                                   "links": [q.get_owning_node().get_name() + "." + str(q.get_pin_name())
                                             for q in p.list_connected_pins()]} for p in n.list_all_pins()]}
                        for n in created]}
    (output / "authoring.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
