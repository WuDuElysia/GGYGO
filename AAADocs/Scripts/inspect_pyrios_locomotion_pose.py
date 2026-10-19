"""@file inspect_pyrios_locomotion_pose.py
@brief 只读取得 Pyrios 当前 AnimBP 接线、角色配置和整身倾身必需骨链。

在协调好的独立标准 Editor 中调用 run(output_file, expected_pid)。输出必须
是 Saved 下不存在的文件，父目录由宿主准备。本工具不编译、修改或保存资产，
不创建 Actor/PIE/播放器，不承担同帧运行及视觉验证。SkeletonModifier 只读取
参考骨架，不调用任何骨骼修改或 commit。原生 API 依据本地 UE 源码及既有工具。
"""

import json
import math
import os
from pathlib import Path


ABP = "/Game/BP/Anim/ABP_Pyrios"
CHARACTER = "/Game/BP/Character/Player/BP_PC_Pyrios"
MESH = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"
BODY = "Bip001"
FEET = ("Bip001-L-Foot", "Bip001-R-Foot")
POSE_NODES = {
    "AnimGraphNode_SequencePlayer", "AnimGraphNode_SequenceEvaluator",
    "AnimGraphNode_BlendSpacePlayer", "AnimGraphNode_ModifyBone",
    "AnimGraphNode_Slot", "GGYGOAnimGraphNode_ActionPoseSlot",
    "GGYGOAnimGraphNode_BodyLean",
}


def require(condition, reason):
    if not condition:
        raise RuntimeError("[Animation][LocomotionInspection] " + reason)


def path(obj):
    return obj.get_path_name() if obj is not None else None


def dirty(ue):
    lib = ue.EditorLoadingAndSavingUtils
    return {
        "content": sorted(path(p) for p in lib.get_dirty_content_packages()),
        "maps": sorted(path(p) for p in lib.get_dirty_map_packages()),
    }


def graph_snapshot(ue, blueprint):
    result = {}
    for graph in ue.BlueprintEditorLibrary.list_graphs(blueprint):
        editor = ue.BlueprintGraphEditor.get_graph_editor(graph)
        require(editor is not None, path(graph) + ": 缺少原生 graph editor")
        nodes = {}
        for node in editor.list_all_nodes():
            cls = node.get_class().get_name()
            pos = node.get_node_pos()
            item = {"class": path(node.get_class()), "position": [pos.x, pos.y]}
            item["pins"] = [{
                "name": str(pin.get_pin_name()), "direction": str(pin.get_pin_direction()),
                "type": pin.get_pin_type_as_json_schema(), "value": pin.get_pin_value(),
                "links": sorted([path(other.get_owning_node()), str(other.get_pin_name())]
                                for other in pin.list_connected_pins()),
            } for pin in node.list_all_pins()]
            if cls in POSE_NODES:
                item["authored_node"] = node.get_editor_property("Node").export_text()
            if cls.startswith("K2Node_"):
                item["member_title"] = str(node.get_node_title())
            if cls == "K2Node_AnimGetter":
                association = ue.GGYGOAnimationGraphEditorLibrary.read_getter_association(node)
                require(association.succeeded, str(association.error))
                item["source_node"] = path(association.source_node)
                item["source_state_node"] = path(association.source_state_node)
                item["source_state_graph"] = path(association.source_state_graph)
                item["getter_class"] = path(association.getter_class)
                item["source_blueprint"] = str(association.source_blueprint_path)
                item["getter_function"] = str(association.function_name)
            nodes[path(node)] = item
        entry = {"outer": path(graph.get_outer()), "nodes": nodes,
                 "errors": sorted(path(n) for n in editor.list_nodes_with_errors()),
                 "warnings": sorted(path(n) for n in editor.list_nodes_with_warnings())}
        if graph.get_name() == "WalkRun":
            entry["body_lean_actions"] = [str(n) for n in editor.list_available_nodes([])
                                          if "GGYGO整身倾身" in str(n).replace(" ", "")]
        result[path(graph)] = entry
    # ListAllNodes 的原生签名只返回 UK2Node；本报告不声称包含非 K2 的状态机边。
    return result


def transform(value):
    result = {
        "translation": [float(getattr(value.translation, n)) for n in "xyz"],
        "rotation": [float(getattr(value.rotation, n)) for n in "xyzw"],
        "scale": [float(getattr(value.scale3d, n)) for n in "xyz"],
    }
    require(all(math.isfinite(v) for values in result.values() for v in values), "非有限参考变换")
    return result


def reference_legs(ue, mesh):
    reader = ue.SkeletonModifier()
    require(reader.set_skeletal_mesh(mesh), "原生参考骨架读取失败")
    inventory = {str(n) for n in reader.get_all_bone_names()}
    require({BODY, *FEET}.issubset(inventory), "Body/双脚不属于当前实际参考骨架")
    result = {}
    for foot in FEET:
        chain, current = [], foot
        while current.casefold() != "none":
            require(current in inventory and current not in chain, "参考父链缺项/循环：" + current)
            chain.append(current)
            current = str(reader.get_parent_name(current))
        require(len(chain) >= 4 and BODY in chain[3:], foot + ": 缺少 Body 下完整髋/膝/脚链")
        result[foot] = {
            "parent_chain": chain,
            "reference_local": {n: transform(reader.get_bone_transform(n, False)) for n in chain},
            "reference_component": {n: transform(reader.get_bone_transform(n, True)) for n in chain[:3]},
        }
    require(set(result[FEET[0]]["parent_chain"][:3]).isdisjoint(
        result[FEET[1]]["parent_chain"][:3]), "双腿链重叠")
    return result


def run(output_file, expected_pid):
    import unreal as ue

    output = Path(output_file)
    saved = Path(ue.Paths.project_saved_dir()).resolve()
    require(output.is_absolute() and output.resolve().is_relative_to(saved), "输出须为 Saved 下绝对路径")
    require(not output.exists() and output.parent.is_dir(), "输出已存在或父目录未由宿主准备")
    receipt = {"schema": "GGYGO.PyriosLocomotionInspection/v1", "pid": os.getpid(),
               "inspection_completed": False, "saved_assets": False,
               "runtime_or_visual_proof": False, "errors": []}
    try:
        require(int(expected_pid) == os.getpid(), "宿主 PID 不匹配")
        receipt["dirty_before"] = dirty(ue)
        require(receipt["dirty_before"] == {"content": [], "maps": []}, "宿主有未保存工作，停止只读检查")
        require(ue.get_editor_subsystem(ue.UnrealEditorSubsystem).get_game_world() is None, "宿主已有 PIE")
        anim_bp = ue.load_asset(ABP)
        character_bp = ue.load_asset(CHARACTER)
        require(isinstance(anim_bp, ue.AnimBlueprint) and isinstance(character_bp, ue.Blueprint), "原 BP 缺失/类型错误")
        require(anim_bp.generated_class() is not None and character_bp.generated_class() is not None, "原 BP 缺少生成类")
        anim = ue.get_default_object(anim_bp.generated_class())
        character = ue.get_default_object(character_bp.generated_class())
        # ACharacter 的两个 C++ getter 未反射；读取原有 UPROPERTY，不猜 Python 方法。
        mesh_component = character.get_editor_property("Mesh")
        capsule = character.get_editor_property("CapsuleComponent")
        require(mesh_component is not None and capsule is not None, "原角色 CDO 缺 Mesh/Capsule")
        mesh = mesh_component.get_skeletal_mesh_asset()
        require(isinstance(mesh, ue.SkeletalMesh) and path(mesh) == MESH + "." + MESH.rsplit("/", 1)[1], "原角色实际 Mesh 不匹配")
        receipt["character_defaults"] = {
            "class": path(character_bp.generated_class()),
            "use_controller_rotation_yaw": character.get_editor_property("bUseControllerRotationYaw"),
            "mesh": path(mesh), "mesh_relative": mesh_component.get_relative_transform().export_text(),
            "capsule_relative": capsule.get_relative_transform().export_text(),
            "scope": "CDO authored defaults; not possessed-instance flags or completed-frame world basis",
        }
        receipt["anim_defaults"] = {"class": path(anim_bp.generated_class()),
                                     "root_motion_mode": str(anim.get_editor_property("RootMotionMode")),
                                     "tuning": anim.get_editor_property("Tuning").export_text(),
                                     "anim_set": anim.get_editor_property("AnimSet").export_text()}
        receipt["graphs"] = graph_snapshot(ue, anim_bp)
        receipt["legs"] = reference_legs(ue, mesh)
        receipt["dirty_after"] = dirty(ue)
        require(receipt["dirty_after"] == receipt["dirty_before"], "读取后 dirty 改变；保留实际宿主状态")
        receipt["inspection_completed"] = True
    except Exception as exc:
        receipt["errors"].append(str(exc))
        receipt["dirty_after"] = dirty(ue)
        raise
    finally:
        # 单个真实机器读回，create-only；失败证据保留，不清 dirty 或回滚资产。
        with output.open("x", encoding="utf-8") as stream:
            json.dump(receipt, stream, ensure_ascii=False, indent=2)
        ue.log("[Animation][LocomotionInspection] " + str(output))
    return receipt
