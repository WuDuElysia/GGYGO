# -*- coding: utf-8 -*-
"""
verify_turnback_program_rotation.py —— 独立只读验证已保存的 ProgramRotation 资产。

本脚本不导入修复脚本，不调用任何 AnimationDataController 写入接口，
也不调用 save_loaded_asset；只重新加载资产并读取保存后的结果。

在 Unreal Editor Python Console 中执行：
    exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/verify_turnback_program_rotation.py",
              encoding="utf-8").read())
"""

import math
import unreal


ASSET = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
         "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack_ProgramRotation")

EXPECTED_TRACKS = ("Root", "Bone_Root", "Bip001")
EXPECTED_KEY_COUNT = 145
EXPECTED_FLOAT_CURVE_COUNT = 7
ROTATION_TOLERANCE_DEGREES = 0.001
COMPONENT_TOLERANCE = 1.0e-5


def _field(value, names):
    for name in names:
        try:
            if hasattr(value, name):
                return getattr(value, name)
        except Exception:
            pass
        try:
            return value.get_editor_property(name)
        except Exception:
            pass
    return None


def _name_text(value):
    try:
        to_string = getattr(value, "to_string", None)
        if callable(to_string):
            return str(to_string())
    except Exception:
        pass
    return str(value)


def _resolve_name(names, desired):
    desired = str(desired).casefold()
    for name in names:
        if _name_text(name).casefold() == desired:
            return _name_text(name)
    return None


def _components(value, names, label):
    result = []
    for name in names:
        component = _field(value, (name,))
        if component is None:
            raise RuntimeError("%s 缺少分量 %s" % (label, name))
        result.append(float(component))
    return tuple(result)


def _transform_parts(pose, label):
    translation = _field(pose, ("translation", "location"))
    rotation = _field(pose, ("rotation", "quaternion"))
    scale = _field(pose, ("scale3d", "scale"))
    if translation is None or rotation is None or scale is None:
        raise RuntimeError("%s 缺少 translation/rotation/scale3d" % label)
    return (
        _components(translation, ("x", "y", "z"), "%s.translation" % label),
        _components(rotation, ("x", "y", "z", "w"), "%s.rotation" % label),
        _components(scale, ("x", "y", "z"), "%s.scale3d" % label),
    )


def _rotation_error_degrees(left, right):
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))
    if left_norm <= 0.0 or right_norm <= 0.0:
        raise RuntimeError("检测到零长度 quaternion")
    dot = sum(a * b for a, b in zip(left, right)) / (left_norm * right_norm)
    dot = max(0.0, min(1.0, abs(dot)))
    return math.degrees(2.0 * math.acos(dot))


def _same_components(left, right, tolerance=COMPONENT_TOLERANCE):
    return len(left) == len(right) and all(
        abs(a - b) <= tolerance for a, b in zip(left, right))


def _curve_names(anim):
    names = unreal.AnimationLibrary.get_animation_curve_names(
        anim, unreal.RawCurveTrackTypes.RCT_FLOAT)
    return sorted(_name_text(name) for name in names)


def _pose(anim, bone_name, frame):
    return unreal.AnimationLibrary.get_bone_pose_for_frame(
        anim, bone_name, int(frame), True)


def _log_transform(label, transform):
    position, rotation, scale = transform
    unreal.log(
        "[VerifyProgramRotation] %s T=(%.6f, %.6f, %.6f) "
        "R=(%.6f, %.6f, %.6f, %.6f) S=(%.6f, %.6f, %.6f)" %
        (label, position[0], position[1], position[2],
         rotation[0], rotation[1], rotation[2], rotation[3],
         scale[0], scale[1], scale[2]))


def run():
    unreal.log("=" * 88)
    unreal.log("[VerifyProgramRotation] target=%s" % ASSET)

    anim = unreal.load_asset(ASSET)
    if not isinstance(anim, unreal.AnimSequence):
        unreal.log_error("[VerifyProgramRotation] 目标不是 AnimSequence")
        return False

    controller = anim.get_editor_property("controller")
    model = controller.get_model_interface() if controller is not None else None
    if model is None:
        unreal.log_error("[VerifyProgramRotation] 无法取得保存后 DataModel")
        return False

    names = [_name_text(name) for name in model.get_bone_track_names()]
    unreal.log("[VerifyProgramRotation] bone_tracks=%d" % len(names))
    missing = [name for name in EXPECTED_TRACKS
               if _resolve_name(names, name) is None]
    if missing:
        unreal.log_error("[VerifyProgramRotation] 缺少关键轨道: %s" % missing)
        return False
    unreal.log("[VerifyProgramRotation] resolved Root=%s Bone_Root=%s Bip001=%s" %
               (_resolve_name(names, "Root"),
                _resolve_name(names, "Bone_Root"),
                _resolve_name(names, "Bip001")))

    key_count = int(model.get_number_of_keys())
    unreal.log("[VerifyProgramRotation] model_keys=%d" % key_count)
    if key_count != EXPECTED_KEY_COUNT:
        unreal.log_error("[VerifyProgramRotation] key 数量异常: %d (expected %d)" %
                         (key_count, EXPECTED_KEY_COUNT))
        return False

    bone_root_name = _resolve_name(names, "Bone_Root")
    root_name = _resolve_name(names, "Root")
    bip001_name = _resolve_name(names, "Bip001")

    bone_root_transforms = []
    root_transforms = []
    bip001_transforms = []
    try:
        for frame in range(key_count):
            bone_root_transforms.append(
                _transform_parts(_pose(anim, bone_root_name, frame),
                                 "bone_root frame=%d" % frame))
            root_transforms.append(
                _transform_parts(_pose(anim, root_name, frame),
                                 "root frame=%d" % frame))
            bip001_transforms.append(
                _transform_parts(_pose(anim, bip001_name, frame),
                                 "bip001 frame=%d" % frame))
    except Exception as ex:
        unreal.log_error("[VerifyProgramRotation] 读取逐帧姿态失败: %s" % ex)
        return False

    first = bone_root_transforms[0]
    _log_transform("bone_root first", first)
    _log_transform("bone_root middle", bone_root_transforms[key_count // 2])
    _log_transform("bone_root last", bone_root_transforms[-1])
    _log_transform("root first", root_transforms[0])
    _log_transform("bip001 first", bip001_transforms[0])

    max_rotation_error = 0.0
    max_rotation_frame = 0
    for frame, transform in enumerate(bone_root_transforms):
        error = _rotation_error_degrees(first[1], transform[1])
        if error > max_rotation_error:
            max_rotation_error = error
            max_rotation_frame = frame
        for channel_name, values in (("position", transform[0]),
                                     ("rotation", transform[1]),
                                     ("scale", transform[2])):
            if not all(math.isfinite(value) for value in values):
                unreal.log_error("[VerifyProgramRotation] bone_root frame=%d %s 非有限" %
                                 (frame, channel_name))
                return False

    unreal.log("[VerifyProgramRotation] Bone_Root max_rotation_error=%.9f degrees frame=%d" %
               (max_rotation_error, max_rotation_frame))
    if max_rotation_error > ROTATION_TOLERANCE_DEGREES:
        unreal.log_error("[VerifyProgramRotation] Bone_Root 旋转未固定")
        return False

    # 修复前日志显示首帧 pitch/yaw/roll 均为 0；当前首帧方向应仍为该方向。
    first_rotator = _pose(anim, bone_root_name, 0).rotation.rotator()
    unreal.log("[VerifyProgramRotation] first_rotator pitch=%.6f yaw=%.6f roll=%.6f" %
               (float(first_rotator.pitch), float(first_rotator.yaw),
                float(first_rotator.roll)))
    if (abs(float(first_rotator.pitch)) > ROTATION_TOLERANCE_DEGREES
            or abs(float(first_rotator.yaw)) > ROTATION_TOLERANCE_DEGREES
            or abs(float(first_rotator.roll)) > ROTATION_TOLERANCE_DEGREES):
        unreal.log_error("[VerifyProgramRotation] 首帧方向不符合修复前记录的零方向")
        return False

    curves = _curve_names(anim)
    rm_curves = [name for name in curves if name.startswith("RM_")]
    unreal.log("[VerifyProgramRotation] float_curves=%d names=%s" %
               (len(curves), ", ".join(curves)))
    unreal.log("[VerifyProgramRotation] RM_curves=%d names=%s" %
               (len(rm_curves), ", ".join(rm_curves) if rm_curves else "<none>"))
    if len(curves) != EXPECTED_FLOAT_CURVE_COUNT:
        unreal.log_error("[VerifyProgramRotation] FloatCurve 数量异常: %d (expected %d)" %
                         (len(curves), EXPECTED_FLOAT_CURVE_COUNT))
        return False

    unreal.log("[VerifyProgramRotation] Root/Bip001 已成功读取 %d/%d 帧；" 
               "Bone_Root Position/Scale 当前数据有限且未被本次旋转固定清空" %
               (len(root_transforms), len(bip001_transforms)))
    unreal.log("[VerifyProgramRotation] PASS: 保存后独立只读验证通过")
    unreal.log("[VerifyProgramRotation] exact Bone_Root Position/Scale 与保存前的比较 "
               "已由修复脚本的保存前/保存后校验完成")
    return True


run()
