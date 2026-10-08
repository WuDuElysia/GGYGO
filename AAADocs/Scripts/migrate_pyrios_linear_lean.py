"""@file migrate_pyrios_linear_lean.py
@brief Migrate two Pyrios defaults and verify them in an independent Editor.

Run apply in the coordinator's exclusive two-package window. Run readback in a
new full Editor process with the successful apply record as --baseline. Only
apply sets/compiles/saves assets. Both modes write one machine record in Saved.
Failures retain backups and unsaved dirty state; no rollback or SaveAll occurs.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil

import unreal


ABP = "/Game/BP/Anim/ABP_Pyrios"
CAMERA = "/Game/Camera/Modes/BP_CameraMode_ThirdPerson_Pyrios"
PAWN = "/Game/BP/Character/Player/BP_PC_Pyrios"
PAWN_DATA = "/Game/Characters/Player/Pyrios/DA/DA_Pawn_Pyrios"
MOVEMENT = "/Game/Characters/Player/Pyrios/DA/DA_Movement_Pyrios"
SKELETON = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model_Skeleton"
BLEND_SPACE = "/Game/Characters/Player/Pyrios/Animation/Movement/BS_Pyrios_WalkRun"
TARGETS = (ABP, CAMERA)
SCHEMA = "GGYGO.PyriosLinearLean/v1"
ACTION_POSE_CLASS = "/Script/GGYGOEditor.GGYGOAnimGraphNode_ActionPoseSlot"
ANGLE_FIELD = "FullLeanDirectionErrorDegrees"
ANGLE_PATTERN = re.compile(r"(\bFullLeanDirectionErrorDegrees=)([^,()]+)")
CAMERA_FIELDS = (
    "SteeringOffsetResponse", "SteeringOffsetAmplitude", "SteeringOffsetMaxDistance",
    "WalkSteeringOffsetScale", "RunSteeringOffsetScale", "SteeringOffsetEnterSpeed",
    "SteeringOffsetReturnSpeed", "TargetOffset", "bPreventPenetration",
    "PenetrationProbeRadius", "PenetrationRecoverySpeed", "FieldOfView",
    "ViewPitchMin", "ViewPitchMax", "BlendTime", "BlendFunction", "BlendExponent",
)
WALKRUN_LINKS = (
    ("AnimGraphNode_BlendSpacePlayer_0", "Pose", "AnimGraphNode_LocalToComponentSpace_0", "LocalPose"),
    ("AnimGraphNode_LocalToComponentSpace_0", "ComponentPose", "AnimGraphNode_ModifyBone_0", "ComponentPose"),
    ("AnimGraphNode_ModifyBone_0", "Pose", "AnimGraphNode_ComponentToLocalSpace_0", "ComponentPose"),
    ("AnimGraphNode_ComponentToLocalSpace_0", "Pose", "AnimGraphNode_StateResult_0", "Result"),
    ("K2Node_VariableGet_1", "WalkRunLeanAngleDegrees", "K2Node_CallFunction_1", "Pitch"),
    ("K2Node_CallFunction_1", "ReturnValue", "AnimGraphNode_ModifyBone_0", "Rotation"),
    ("K2Node_VariableGet_2", "bWalkRunLeanPresentationValid", "K2Node_CallFunction_2", "bPickA"),
    ("K2Node_CallFunction_2", "ReturnValue", "AnimGraphNode_ModifyBone_0", "Alpha"),
)


def require(condition, reason):
    if not condition:
        raise RuntimeError("[GGYGO.PyriosLinearLean] " + reason)


def prop(obj, name):
    require(obj is not None, "missing receiver for " + name)
    try:
        return obj.get_editor_property(name)
    except Exception as exc:
        raise RuntimeError("[GGYGO.PyriosLinearLean] " + str(obj) + "." + name
                           + ": native property read failed: " + str(exc)) from exc


def path(obj):
    return obj.get_path_name() if obj is not None else None


def authored(value):
    if isinstance(value, unreal.Object):
        return path(value)
    if hasattr(value, "export_text"):
        return value.export_text()
    if isinstance(value, (bool, int, float, str)):
        require(not isinstance(value, float) or math.isfinite(value), "non-finite authored parameter")
        return value
    return str(value)


def protected_tuning(text):
    require(len(ANGLE_PATTERN.findall(text)) == 1, ABP + ": new angle field absent/ambiguous in Tuning")
    return ANGLE_PATTERN.sub(lambda m: m[1] + "<target>", text)


def dirty():
    return {
        "content": sorted(path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()),
        "maps": sorted(path(p) for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
    }


def check_dirty(allowed=()):
    current = dirty()
    require(not current["maps"] and set(current["content"]).issubset(allowed),
            "unexpected dirty packages: " + json.dumps(current))
    return current


def blueprint(package, parent=None):
    bp = unreal.EditorAssetLibrary.load_asset(package)
    require(isinstance(bp, unreal.Blueprint) and path(bp) == package + "." + package.rsplit("/", 1)[1],
            package + ": missing/wrong Blueprint")
    require(bp.generated_class() is not None, package + ": missing generated class")
    if parent is not None:
        require(path(bp.get_blueprint_parent_class()) == parent, package + ": unexpected parent class")
    require("BS_ERROR" not in str(prop(bp, "Status")), package + ": Blueprint is in Error status")
    return bp


def graphs(bp):
    result, errors, warnings = {}, [], []
    for graph in unreal.BlueprintEditorLibrary.list_graphs(bp):
        editor = unreal.BlueprintGraphEditor.get_graph_editor(graph)
        require(editor is not None, path(graph) + ": missing graph editor")
        nodes = {}
        for node in editor.list_all_nodes():
            position = node.get_node_pos()
            pins = [{"name": str(p.get_pin_name()), "direction": str(p.get_pin_direction()),
                     "value": p.get_pin_value(), "type": p.get_pin_type_as_json_schema(),
                     "links": sorted([path(q.get_owning_node()), str(q.get_pin_name()),
                                      str(q.get_pin_direction())] for q in p.list_connected_pins())}
                    for p in node.list_all_pins()]
            entry = {"class": path(node.get_class()), "position": [position.x, position.y], "pins": pins}
            cls = node.get_class().get_name()
            if cls in ("AnimGraphNode_ModifyBone", "AnimGraphNode_Slot", "AnimGraphNode_BlendSpacePlayer",
                       "GGYGOAnimGraphNode_ActionPoseSlot"):
                entry["authored_node"] = prop(node, "Node").export_text()
            elif cls in ("K2Node_VariableGet", "K2Node_VariableSet", "K2Node_CallFunction"):
                # Internal MemberReference properties are not Python-readable.
                # Use the native public node identity, as EditorToolset does;
                # complete pins retain the authored signature, defaults and links.
                entry["member_identity"] = {
                    "category": node.get_node_category(), "title": node.get_node_title(),
                }
            nodes[path(node)] = entry
        result[path(graph)] = nodes
        errors.extend(path(n) for n in editor.list_nodes_with_errors())
        warnings.extend(path(n) for n in editor.list_nodes_with_warnings())
    require(not errors, path(bp) + ": graph errors: " + str(errors))
    return result, sorted(warnings)


def check_walkrun(bp, graph_snapshot):
    matches = [g for g in unreal.BlueprintEditorLibrary.list_graphs(bp) if g.get_name() == "WalkRun"]
    require(len(matches) == 1, ABP + ": expected one WalkRun state")
    graph = matches[0]
    nodes = {n.get_name(): n for n in unreal.BlueprintGraphEditor.get_graph_editor(graph).list_all_nodes()}
    for a, ap, b, bp_pin in WALKRUN_LINKS:
        require(a in nodes and b in nodes, path(graph) + ": missing lean-chain node " + a + "/" + b)
        output, input_pin = nodes[a].find_output_pin(ap), nodes[b].find_input_pin(bp_pin)
        require(output is not None and input_pin is not None, path(graph) + ": missing lean-chain pin")
        links = list(output.list_connected_pins())
        require(len(links) == 1 and links[0].is_same_native_pin(input_pin),
                path(graph) + ": incorrect connection " + a + "." + ap + " -> " + b + "." + bp_pin)
    for name, pin_name, expected in (("K2Node_CallFunction_1", "Yaw", 0.0),
                                    ("K2Node_CallFunction_1", "Roll", 0.0),
                                    ("K2Node_CallFunction_2", "A", 1.0),
                                    ("K2Node_CallFunction_2", "B", 0.0)):
        pin = nodes[name].find_input_pin(pin_name)
        require(pin is not None and not pin.list_connected_pins() and float(pin.get_pin_value()) == expected,
                path(nodes[name]) + "." + pin_name + ": unexpected authored value/binding")
    modify = prop(nodes["AnimGraphNode_ModifyBone_0"], "Node").export_text()
    for token in ('BoneName="Bip001-Spine"', "RotationMode=BMM_Additive", "RotationSpace=BCS_ComponentSpace",
                  "TranslationMode=BMM_Ignore", "ScaleMode=BMM_Ignore", "AlphaScaleBias=(Scale=1.000000,Bias=0.000000)",
                  "bMapRange=False", "bClampResult=False", "bInterpResult=False"):
        require(token in modify, path(graph) + ": unexpected bone/axis/alpha setting " + token)


def check_action_pose(anim_cdo, graph_snapshot):
    # Pyrios uses one FullBody producer in its original top-level pose chain.
    # ActionPoseSlot is the node's semantic name, not its configured SlotName.
    required_slot = str(prop(anim_cdo, "RequiredPoseCorrectionSlot"))
    slots = [{"graph": g, "path": p, "class": n["class"], "node": n["authored_node"]}
             for g, ns in graph_snapshot.items() for p, n in ns.items()
             if n["class"] in (ACTION_POSE_CLASS, "/Script/AnimGraph.AnimGraphNode_Slot")]
    producers = [n for n in slots if n["class"] == ACTION_POSE_CLASS]
    main_path = ABP + ".ABP_Pyrios:AnimGraph"
    require(len(producers) == 1 and producers[0]["graph"] == main_path,
            ABP + ": expected one top-level action pose producer; required_slot=" + required_slot
            + "; actual_slots=" + json.dumps(slots, ensure_ascii=False))
    producer = unreal.load_object(None, producers[0]["path"])
    node = prop(producer, "Node")
    alignment = prop(node, "ComponentAlignment")
    config = {"path": path(producer), "class": path(producer.get_class()),
              "slot": str(prop(node, "SlotName")), "required_slot": required_slot,
              "body": str(prop(node, "BodyBoneName")), "trajectory": str(prop(node, "TrajectoryBoneName")),
              "alignment": [alignment.x, alignment.y, alignment.z],
              "always_update_source": prop(node, "bAlwaysUpdateSourcePose")}
    require(config["slot"] == required_slot == "FullBody" and config["body"] == "Bip001"
            and config["trajectory"] == "Root" and all(math.isfinite(v) for v in config["alignment"])
            and config["always_update_source"] is True,
            ABP + ": action pose producer/Guard contract differs: " + json.dumps(config, ensure_ascii=False))
    main = graph_snapshot[main_path]
    for a, ap, b, bp_pin in (
        ("AnimGraphNode_StateMachine_0", "Pose", "GGYGOAnimGraphNode_ActionPoseSlot_0", "Source"),
        ("GGYGOAnimGraphNode_ActionPoseSlot_0", "Pose", "AnimGraphNode_LocalToComponentSpace_0", "LocalPose"),
        ("AnimGraphNode_LocalToComponentSpace_0", "ComponentPose", "AnimGraphNode_ComponentToLocalSpace_0", "ComponentPose"),
        ("AnimGraphNode_ComponentToLocalSpace_0", "Pose", "AnimGraphNode_Inertialization_0", "Source"),
        ("AnimGraphNode_Inertialization_0", "Pose", "AnimGraphNode_Root_0", "Result"),
    ):
        outputs = [p for p in main.get(main_path + "." + a, {}).get("pins", [])
                   if p["name"] == ap and "EGPD_OUTPUT" in p["direction"]]
        require(len(outputs) == 1 and len(outputs[0]["links"]) == 1
                and outputs[0]["links"][0][:2] == [main_path + "." + b, bp_pin]
                and "EGPD_INPUT" in outputs[0]["links"][0][2],
                ABP + ": original action pose connection differs: " + a + "." + ap + " -> " + b + "." + bp_pin
                + "; producer=" + json.dumps(config, ensure_ascii=False))
    return required_slot


def snapshot(abp, camera):
    anim_cdo, camera_cdo = (unreal.get_default_object(bp.generated_class()) for bp in (abp, camera))
    tuning = prop(anim_cdo, "Tuning")
    lean = prop(tuning, "WalkRunLean")
    require(prop(lean, "bEnabled") is True, ABP + ": original enabled lean mode missing")
    for name, expected in (("WalkMaxAngleDegrees", 2.0), ("RunMaxAngleDegrees", 6.0),
                           ("RecoveryResponseSpeed", 8.0), ("FullLeanYawRateDegreesPerSecond", 180.0),
                           ("EnterResponseSpeed", 12.0)):
        require(prop(lean, name) == expected, ABP + ": original lean parameter differs: " + name)
    angle = prop(lean, ANGLE_FIELD)
    require(math.isfinite(angle) and angle in (0.0, 180.0), ABP + ": unexpected new angle baseline " + str(angle))
    flag = prop(camera_cdo, "bEnableWalkRunSteeringOffset")
    require(isinstance(flag, bool), CAMERA + ": steering switch is not bool")
    anim_graphs, anim_warnings = graphs(abp)
    camera_graphs, camera_warnings = graphs(camera)
    check_walkrun(abp, anim_graphs)
    required_slot = check_action_pose(anim_cdo, anim_graphs)
    anim_set = prop(anim_cdo, "AnimSet")
    blends = {str(k): path(v) for k, v in prop(anim_set, "BlendSpaces").items()}
    key = str(prop(anim_set, "WalkRunSourceKey"))
    require(blends.get(key) == BLEND_SPACE + ".BS_Pyrios_WalkRun", ABP + ": unexpected WalkRun BlendSpace route")
    pawn_bp = blueprint(PAWN)
    pawn_cdo = unreal.get_default_object(pawn_bp.generated_class())
    mesh = prop(pawn_cdo, "Mesh")
    require(isinstance(mesh, unreal.SkeletalMeshComponent), PAWN + ": missing native Mesh component")
    skeletal_mesh = mesh.get_skeletal_mesh_asset()
    require(skeletal_mesh is not None, PAWN + ": missing Mesh asset")
    skeleton = prop(skeletal_mesh, "Skeleton")
    require(path(skeleton) == SKELETON + "." + SKELETON.rsplit("/", 1)[1]
            and prop(abp, "TargetSkeleton") == skeleton, ABP + ": Mesh/ABP skeleton mismatch")
    require(prop(mesh, "AnimClass") == abp.generated_class(), PAWN + ": Mesh AnimClass differs")
    require(mesh.get_bone_index("Bip001-Spine") >= 0, PAWN + ": authored lean bone missing")
    rotation, location, scale = (prop(mesh, n) for n in ("RelativeRotation", "RelativeLocation", "RelativeScale3D"))
    values = [rotation.pitch, rotation.yaw, rotation.roll, location.x, location.y, location.z,
              scale.x, scale.y, scale.z]
    require(all(math.isfinite(v) for v in values), PAWN + ": non-finite Mesh relative transform")
    require(abs(rotation.pitch) < 1e-5 and abs(rotation.yaw + 90.0) < 1e-5 and abs(rotation.roll) < 1e-5,
            PAWN + ": Mesh basis differs from verified ComponentSpace Pitch/right-positive basis")
    require(scale.x > 0 and scale.x == scale.y == scale.z, PAWN + ": unexpected Mesh scale")
    quat = rotation.quaternion()
    pawn_data = unreal.EditorAssetLibrary.load_asset(PAWN_DATA)
    require(isinstance(pawn_data, unreal.GGYGOPawnData), PAWN_DATA + ": missing/wrong PawnData")
    require(prop(pawn_data, "DefaultCameraMode") == camera.generated_class(), PAWN_DATA + ": Camera reference differs")
    require(prop(pawn_data, "PawnClass") == pawn_bp.generated_class(), PAWN_DATA + ": PawnClass differs")
    movement = prop(pawn_data, "MovementSet")
    require(isinstance(movement, unreal.GGYGOMovementSet) and path(movement) == MOVEMENT + ".DA_Movement_Pyrios",
            PAWN_DATA + ": MovementSet reference differs")
    protected = {
        "anim": {"parent": path(abp.get_blueprint_parent_class()), "class": path(abp.generated_class()),
                 "skeleton": path(skeleton), "graphs": anim_graphs, "warnings": anim_warnings,
                 "required_pose_correction_slot": required_slot,
                 "anim_set": anim_set.export_text(), "tuning": protected_tuning(tuning.export_text())},
        "camera": {"parent": path(camera.get_blueprint_parent_class()), "class": path(camera.generated_class()),
                   "graphs": camera_graphs, "warnings": camera_warnings,
                   "parameters": {n: authored(prop(camera_cdo, n)) for n in CAMERA_FIELDS}},
        "pawn": {"class": path(pawn_bp.generated_class()), "mesh_component": path(mesh),
                 "mesh_asset": path(skeletal_mesh), "anim_class": path(prop(mesh, "AnimClass")),
                 "relative_location": location.export_text(), "relative_rotation": rotation.export_text(),
                 "relative_quaternion_xyzw": [quat.x, quat.y, quat.z, quat.w],
                 "relative_scale": scale.export_text(), "movement_set": path(movement),
                 "default_camera_mode": path(prop(pawn_data, "DefaultCameraMode"))},
    }
    return protected, {"full_lean_direction_error_degrees": angle, "camera_steering_enabled": flag}


def check_protected(actual, baseline):
    changed = [k for k in set(actual) | set(baseline) if actual.get(k) != baseline.get(k)]
    require(not changed, "protected configuration changed: " + ", ".join(sorted(changed)))


def saved_path(root, value):
    resolved = Path(value).resolve()
    require(resolved.is_relative_to((root / "Saved").resolve()), "evidence/backup path must be inside project Saved: " + str(resolved))
    return resolved


def package_files(root):
    files = []
    for package in TARGETS:
        base = root / "Content" / package.removeprefix("/Game/")
        require(base.with_suffix(".uasset").is_file(), package + ": original package file missing")
        files.extend(base.with_suffix(ext) for ext in (".uasset", ".uexp", ".ubulk") if base.with_suffix(ext).is_file())
    return files


def hashes(root):
    return {f.relative_to(root).as_posix(): hashlib.sha256(f.read_bytes()).hexdigest()
            for f in package_files(root)}


def backup(root, folder, original):
    folder.mkdir(parents=True, exist_ok=False)
    for relative, digest in original.items():
        source, dest = root / relative, folder / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, dest)
        require(hashlib.sha256(dest.read_bytes()).hexdigest() == digest, "backup mismatch: " + relative)
    require(hashes(root) == original, "target package changed while backing up")


def run(mode, record, backup_dir=None, baseline=None):
    """Apply the fixed two-field migration or compare a fresh Editor to its record.

    All paths are explicit and confined to Saved. Return the machine result;
    failures write success=false and re-raise without clearing dirty packages.
    """
    root = Path(unreal.Paths.project_dir()).resolve()
    output = saved_path(root, record)
    require(not output.exists(), "record already exists: " + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    result = {"schema": SCHEMA, "mode": mode, "success": False, "pid": os.getpid(),
              "utc": datetime.now(timezone.utc).isoformat(), "targets": list(TARGETS), "saved_packages": []}
    try:
        require(mode in ("apply", "readback"), "mode must be apply or readback")
        require(not re.search(r"(?:^|\s)-run=", unreal.SystemLibrary.get_command_line(), re.I),
                "requires full native Editor, not Commandlet")
        levels = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        require(levels is not None and not levels.is_in_play_in_editor(), "requires inactive PIE")
        check_dirty()
        expected = {"full_lean_direction_error_degrees": 180.0, "camera_steering_enabled": False}
        if mode == "readback":
            require(backup_dir is None and baseline is not None, "readback requires only --baseline")
            baseline_file = saved_path(root, baseline)
            prior = json.loads(baseline_file.read_text(encoding="utf-8"))
            require(prior.get("schema") == SCHEMA and prior.get("mode") == "apply" and prior.get("success") is True
                    and prior.get("targets") == list(TARGETS) and prior.get("saved_packages") == list(TARGETS)
                    and prior.get("after_target_values") == expected, "baseline is not a successful two-package apply")
            require(prior.get("pid") != os.getpid(), "cold readback requires a different Editor process")
            require(hashes(root) == prior["saved_files"], "saved target packages differ from apply record")
            result["baseline"] = str(baseline_file)
        else:
            require(backup_dir is not None and baseline is None, "apply requires only --backup-dir")
            backup_folder = saved_path(root, backup_dir)
            require(not backup_folder.exists(), "backup directory already exists: " + str(backup_folder))
        abp = blueprint(ABP, "/Script/GGYGO.ZZZAnimInstance")
        camera = blueprint(CAMERA, "/Script/GGYGO.GGYGOCameraMode_ThirdPerson")
        protected, before_targets = snapshot(abp, camera)
        check_dirty()
        if mode == "readback":
            check_protected(protected, prior["protected"])
            require(before_targets == expected, "cold target defaults differ from requested values")
            require(all("UP_TO_DATE" in str(prop(bp, "Status")) for bp in (abp, camera)),
                    "cold Blueprint status is not UpToDate")
            result["target_values"] = before_targets
            result["protected_matches"] = True
            require(hashes(root) == prior["saved_files"], "target files changed during cold readback")
        else:
            result["protected"] = protected
            result["before_target_values"] = before_targets
            result["original_files"] = hashes(root)
            backup(root, backup_folder, result["original_files"])
            result["backup_dir"] = str(backup_folder)
            # Copy through the native struct serializer before touching the CDO.
            # The whole original tuning, including legacy values, must round-trip.
            anim_cdo = unreal.get_default_object(abp.generated_class())
            original_text = prop(anim_cdo, "Tuning").export_text()
            tuning_copy = unreal.ZZZAnimTuning()
            require(tuning_copy.import_text(original_text), ABP + ": native Tuning copy import failed")
            require(tuning_copy.export_text() == original_text, ABP + ": native Tuning copy changed original fields")
            require(tuning_copy.import_text(ANGLE_PATTERN.sub(lambda m: m[1] + "180.000000", original_text)),
                    ABP + ": target Tuning import failed")
            require(protected_tuning(tuning_copy.export_text()) == protected["anim"]["tuning"]
                    and prop(prop(tuning_copy, "WalkRunLean"), ANGLE_FIELD) == 180.0,
                    ABP + ": target Tuning preparation changed protected fields")
            abp.modify()
            anim_cdo.modify()
            anim_cdo.set_editor_property("Tuning", tuning_copy)
            camera_cdo = unreal.get_default_object(camera.generated_class())
            camera.modify()
            camera_cdo.modify()
            camera_cdo.set_editor_property("bEnableWalkRunSteeringOffset", False)
            for bp in (abp, camera):
                require(unreal.BlueprintEditorLibrary.compile_blueprint(bp), path(bp) + ": compile failed")
                require("UP_TO_DATE" in str(prop(bp, "Status")), path(bp) + ": compile status not UpToDate")
            current, current_targets = snapshot(abp, camera)
            check_protected(current, protected)
            require(current_targets == expected, "compiled CDO target values differ")
            check_dirty(TARGETS)
            require(hashes(root) == result["original_files"], "original package files changed before exact save")
            for package, bp in zip(TARGETS, (abp, camera)):
                require(unreal.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False),
                        package + ": exact package save failed")
                result["saved_packages"].append(package)
                check_dirty(TARGETS)
            current, current_targets = snapshot(abp, camera)
            check_protected(current, protected)
            require(current_targets == expected, "saved CDO target values differ")
            result["after_target_values"] = current_targets
            result["saved_files"] = hashes(root)
        result["dirty"] = check_dirty()
        result["success"] = True
    except Exception as exc:
        result["error"] = str(exc)
        result["dirty"] = dirty()
        raise
    finally:
        with output.open("x", encoding="utf-8") as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2, allow_nan=False)
        unreal.log("PYRIOS_LINEAR_LEAN " + json.dumps({"mode": mode, "success": result["success"], "record": str(output)}))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("apply", "readback"), required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--backup-dir")
    parser.add_argument("--baseline")
    args = parser.parse_args()
    run(args.mode, args.record, args.backup_dir, args.baseline)
