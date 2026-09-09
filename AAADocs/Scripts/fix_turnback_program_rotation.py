# -*- coding: utf-8 -*-
"""
fix_turnback_program_rotation.py —— 直接修正既有 TurnBack ProgramRotation 资产。

只修改目标 AnimSequence 的 Bone_Root 旋转轨道：
  - 读取 Bone_Root 第一条 Rotation key；
  - 将 Bone_Root 的所有 Rotation keys 固定为第一条 key；
  - 原样传回 Bone_Root 的 Position/Scale keys；
  - 不创建新资产，不触碰 Root、Bip001、其他骨骼轨道或 RM_* 曲线；
  - 保存前后做结构和数据校验。

在 Unreal Editor Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/fix_turnback_program_rotation.py",
            encoding="utf-8").read())
"""

import unreal


ASSET = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
         "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack_ProgramRotation")
BONE_ROOT = "Bone_Root"
REQUIRED_TRACKS = ("Root", "Bone_Root", "Bip001")
FLOAT_EPSILON = 1.0e-6


def _as_list(value):
    if value is None:
        return []
    if isinstance(value, (list, tuple)):
        return list(value)
    try:
        return list(value)
    except Exception:
        return [value]


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


def _components(value, names):
    result = []
    for name in names:
        component = _field(value, (name,))
        if component is None:
            raise RuntimeError("无法读取 %s 的 %s" % (type(value).__name__, name))
        result.append(float(component))
    return tuple(result)


def _value_signature(value, component_names):
    try:
        return _components(value, component_names)
    except Exception:
        # 只作为最后的诊断/比较后备；正常路径使用显式浮点分量。
        return (repr(value),)


def _unpack_track_result(raw, source_name):
    """兼容 UE Python 将 RawAnimSequenceTrack、struct 或三元组暴露的情况。"""
    if raw is None:
        raise RuntimeError("%s 返回 None" % source_name)

    # get_bone_track_by_name() 返回 BoneAnimationTrack 时，实际 key 位于
    # 其 internal_track_data 字段中；先递归解析内部 RawAnimSequenceTrack。
    internal = _field(raw, ("internal_track_data", "track_data"))
    if internal is not None and internal is not raw:
        try:
            return _unpack_track_result(internal, "%s.internal_track_data" % source_name)
        except Exception:
            # 某些绑定会把空的 internal_track_data 反射出来；继续尝试其他表示。
            pass

    # UE 5.8 Python 对 AnimationDataModel.get_bone_track_by_name()
    # 返回 RawAnimSequenceTrack，并通过三个无参 getter 暴露 key 数组。
    getter_names = ("get_positional_keys", "get_rotational_keys", "get_scale_keys")
    getter_values = []
    getter_available = True
    for getter_name in getter_names:
        getter = getattr(raw, getter_name, None)
        if not callable(getter):
            getter_available = False
            break
        try:
            getter_values.append(_as_list(getter()))
        except Exception as ex:
            raise RuntimeError("%s.%s() 失败: %s" %
                               (source_name, getter_name, ex))
    if getter_available:
        return getter_values[0], getter_values[1], getter_values[2]

    if isinstance(raw, (tuple, list)):
        values = list(raw)
        if len(values) == 3:
            return _as_list(values[0]), _as_list(values[1]), _as_list(values[2])

    pos_keys = _field(raw, ("pos_keys", "position_keys", "translation_keys"))
    rot_keys = _field(raw, ("rot_keys", "rotation_keys"))
    scale_keys = _field(raw, ("scale_keys", "scale3d_keys"))
    if pos_keys is not None and rot_keys is not None and scale_keys is not None:
        return _as_list(pos_keys), _as_list(rot_keys), _as_list(scale_keys)

    raise RuntimeError("无法解析 %s 的骨骼轨道返回值: type=%s repr=%s" %
                       (source_name, type(raw).__name__, repr(raw)[:800]))


def _unpack_transform_keys(raw, source_name):
    """兼容仅暴露 Transform key 数组的 UE Python 版本。"""
    transforms = _as_list(raw)
    positions = []
    rotations = []
    scales = []
    for index, transform in enumerate(transforms):
        position = _field(transform, ("translation", "location"))
        rotation = _field(transform, ("rotation", "quaternion"))
        scale = _field(transform, ("scale3d", "scale"))
        if position is None or rotation is None or scale is None:
            raise RuntimeError("%s 第 %d 个 Transform 缺少 translation/rotation/scale3d" %
                               (source_name, index))
        positions.append(position)
        rotations.append(rotation)
        scales.append(scale)
    return positions, rotations, scales


def _get_controller(anim):
    """兼容 UE 5.8 中 get_controller() 不反射、但 controller 属性可用的情况。"""
    method = getattr(anim, "get_controller", None)
    if callable(method):
        try:
            controller = method()
            if controller is not None:
                return controller
        except Exception as ex:
            unreal.log_warning("[FixProgramRotation] get_controller() 失败: %s" % ex)

    for property_name in ("controller",):
        try:
            controller = anim.get_editor_property(property_name)
            if controller is not None:
                unreal.log("[FixProgramRotation] 使用 AnimSequence.%s 属性" % property_name)
                return controller
        except Exception as ex:
            unreal.log_warning("[FixProgramRotation] 读取 controller 属性失败: %s" % ex)

    try:
        controller = getattr(anim, "controller", None)
        if controller is not None:
            return controller
    except Exception:
        pass
    return None


def _get_data_model(anim, controller=None):
    """兼容 UE 5.8 中 AnimSequence.data_model=None 的编辑器控制器模型接口。"""
    owners = []
    if controller is not None:
        owners.append(("Controller", controller))
    owners.append(("AnimSequence", anim))

    for owner_name, owner in owners:
        for method_name in ("get_model_interface", "get_data_model", "get_data_model_interface"):
            method = getattr(owner, method_name, None)
            if callable(method):
                try:
                    model = method()
                    if model is not None:
                        unreal.log("[FixProgramRotation] 使用 %s.%s() 获取 DataModel" %
                                   (owner_name, method_name))
                        return model
                except Exception as ex:
                    unreal.log_warning("[FixProgramRotation] %s.%s() 失败: %s" %
                                       (owner_name, method_name, ex))

    for property_name in ("data_model", "data_model_interface"):
        try:
            model = anim.get_editor_property(property_name)
            if model is not None:
                unreal.log("[FixProgramRotation] 使用 AnimSequence.%s 属性" % property_name)
                return model
        except Exception as ex:
            unreal.log_warning("[FixProgramRotation] 读取 %s 属性失败: %s" %
                               (property_name, ex))
    return None


def _track_names(model):
    method = getattr(model, "get_bone_track_names", None)
    if not callable(method):
        raise RuntimeError("DataModel 没有 get_bone_track_names")
    return [str(name) for name in method()]


def _resolve_track_name(track_names, desired_name):
    """按不区分大小写匹配，并返回 DataModel 枚举出的原始轨道名。"""
    desired = str(desired_name).casefold()
    for track_name in track_names:
        if str(track_name).casefold() == desired:
            return track_name
    return None


def _has_track_keys(keys):
    positions, rotations, scales = keys
    return bool(positions or rotations or scales)


def _get_evaluated_track_keys(anim, model, bone_name):
    """用 AnimationLibrary 读取 imported asset 的逐帧 local Transform。"""
    count = 0
    if model is not None:
        method = getattr(model, "get_number_of_keys", None)
        if callable(method):
            try:
                count = int(method())
            except Exception:
                count = 0
    if count <= 0:
        try:
            count = int(unreal.AnimationLibrary.get_num_frames(anim)) + 1
        except Exception as ex:
            raise RuntimeError("无法确定 %s 的 evaluated key 数量: %s" % (bone_name, ex))
    if count <= 0:
        raise RuntimeError("%s 的 evaluated key 数量无效: %d" % (bone_name, count))

    positions = []
    rotations = []
    scales = []
    for frame in range(count):
        try:
            pose = unreal.AnimationLibrary.get_bone_pose_for_frame(
                anim, bone_name, frame, True)
        except Exception as ex:
            raise RuntimeError("读取 %s frame=%d 的 evaluated pose 失败: %s" %
                               (bone_name, frame, ex))
        position = _field(pose, ("translation", "location"))
        rotation = _field(pose, ("rotation", "quaternion"))
        scale = _field(pose, ("scale3d", "scale"))
        if position is None or rotation is None or scale is None:
            raise RuntimeError("%s frame=%d 的 evaluated pose 缺少 translation/rotation/scale3d" %
                               (bone_name, frame))
        positions.append(position)
        rotations.append(rotation)
        scales.append(scale)

    unreal.log("[FixProgramRotation] evaluated track=%s keys=%d" % (bone_name, count))
    return positions, rotations, scales


def _get_track_keys(model, controller, bone_name, anim=None):
    """读取轨道 keys；imported asset 优先使用逐帧 evaluated Transform。"""
    if anim is not None:
        return _get_evaluated_track_keys(anim, model, bone_name)

    name = unreal.Name(bone_name)
    errors = []

    if model is not None:
        method = getattr(model, "get_bone_track_by_name", None)
        if callable(method):
            try:
                raw = method(name)
                return _unpack_track_result(
                    raw, "DataModel.get_bone_track_by_name(%s)" % bone_name)
            except Exception as ex:
                errors.append("DataModel.get_bone_track_by_name: %s" % ex)

        # 兼容某些版本只暴露 get_bone_animation_tracks() 的情况。
        method = getattr(model, "get_bone_animation_tracks", None)
        if callable(method):
            try:
                tracks = _as_list(method())
                for track in tracks:
                    track_name = _field(track, ("name", "track_name"))
                    if track_name is None or str(track_name) != str(bone_name):
                        continue
                    internal = _field(track, ("internal_track_data", "track_data"))
                    return _unpack_track_result(
                        internal if internal is not None else track,
                        "DataModel.get_bone_animation_tracks(%s)" % bone_name)
            except Exception as ex:
                errors.append("DataModel.get_bone_animation_tracks: %s" % ex)

    # 保留旧版本中可能反射出的直接 getter 作为后备。
    for owner_name, owner in (("DataModel", model), ("Controller", controller)):
        if owner is None:
            continue
        method = getattr(owner, "get_bone_track_keys", None)
        if callable(method):
            try:
                raw = method(name)
                return _unpack_track_result(
                    raw, "%s.get_bone_track_keys(%s)" % (owner_name, bone_name))
            except Exception as ex:
                errors.append("%s.get_bone_track_keys: %s" % (owner_name, ex))

        method = getattr(owner, "get_bone_track_transform_keys", None)
        if callable(method):
            try:
                raw = method(name)
                return _unpack_transform_keys(
                    raw, "%s.get_bone_track_transform_keys(%s)" % (owner_name, bone_name))
            except Exception as ex:
                errors.append("%s.get_bone_track_transform_keys: %s" %
                              (owner_name, ex))

    raise RuntimeError("无法读取 %s 轨道 keys；尝试结果：%s" %
                       (bone_name, " | ".join(errors)))


def _track_signature(keys):
    positions, rotations, scales = keys
    return {
        "position": tuple(_value_signature(value, ("x", "y", "z")) for value in positions),
        "rotation": tuple(_value_signature(value, ("x", "y", "z", "w")) for value in rotations),
        "scale": tuple(_value_signature(value, ("x", "y", "z")) for value in scales),
    }


def _curve_names(anim):
    try:
        names = unreal.AnimationLibrary.get_animation_curve_names(
            anim, unreal.RawCurveTrackTypes.RCT_FLOAT)
        return sorted(str(name) for name in names)
    except Exception as ex:
        unreal.log_warning("[FixProgramRotation] 读取 FloatCurve 名称失败: %s" % ex)
        return []


def _rm_curve_names(anim):
    return [name for name in _curve_names(anim) if name.startswith("RM_")]


def _pose_rotation(anim, bone_name, frame):
    try:
        pose = unreal.AnimationLibrary.get_bone_pose_for_frame(
            anim, bone_name, int(frame), True)
        rotation = _field(pose, ("rotation", "quaternion"))
        if rotation is not None:
            return rotation
    except Exception as ex:
        unreal.log_warning("[FixProgramRotation] 读取 %s 第 %d 帧姿态失败: %s" %
                           (bone_name, frame, ex))
    return None


def _rotator_text(rotation):
    try:
        rotator = rotation.rotator()
        return "pitch=%.6f yaw=%.6f roll=%.6f" % (
            float(rotator.pitch), float(rotator.yaw), float(rotator.roll))
    except Exception:
        return repr(rotation)


def _same_signature(left, right):
    if left.keys() != right.keys():
        return False
    for channel in ("position", "rotation", "scale"):
        if len(left[channel]) != len(right[channel]):
            return False
        for left_value, right_value in zip(left[channel], right[channel]):
            if len(left_value) != len(right_value):
                return False
            for a, b in zip(left_value, right_value):
                if isinstance(a, str) or isinstance(b, str):
                    if a != b:
                        return False
                elif abs(a - b) > FLOAT_EPSILON:
                    return False
    return True


def _open_bracket(controller):
    method = getattr(controller, "open_bracket", None)
    if not callable(method):
        return False
    try:
        method("Fix Bone_Root rotation", False)
        return True
    except TypeError:
        method("Fix Bone_Root rotation")
        return True


def _close_bracket(controller):
    method = getattr(controller, "close_bracket", None)
    if not callable(method):
        return
    try:
        method(False)
    except TypeError:
        method()


def _set_bone_track_keys(controller, bone_name, positions, rotations, scales):
    method = getattr(controller, "set_bone_track_keys", None)
    if not callable(method):
        raise RuntimeError("AnimationDataController 没有 set_bone_track_keys")

    name = unreal.Name(bone_name)
    try:
        return method(name, positions, rotations, scales, False)
    except TypeError:
        # 兼容没有 bShouldTransact 参数的 Python 暴露版本。
        return method(name, positions, rotations, scales)


def _save_asset(anim):
    editor_asset_library = getattr(unreal, "EditorAssetLibrary", None)
    save_loaded_asset = getattr(editor_asset_library, "save_loaded_asset", None) \
        if editor_asset_library else None
    if not callable(save_loaded_asset):
        raise RuntimeError("找不到 unreal.EditorAssetLibrary.save_loaded_asset")
    if not bool(save_loaded_asset(anim)):
        raise RuntimeError("save_loaded_asset 返回 False")


def run():
    unreal.log("=" * 80)
    unreal.log("[FixProgramRotation] target=%s" % ASSET)

    anim = unreal.load_asset(ASSET)
    if not isinstance(anim, unreal.AnimSequence):
        unreal.log_error("[FixProgramRotation] 目标不是 AnimSequence，未修改: %s" % ASSET)
        return False

    controller = _get_controller(anim)
    model = _get_data_model(anim, controller)
    if controller is None or model is None:
        unreal.log_error("[FixProgramRotation] 缺少 AnimationDataController/DataModel，未保存")
        return False

    before_names = _track_names(model)
    resolved_required = {
        name: _resolve_track_name(before_names, name)
        for name in REQUIRED_TRACKS
    }
    missing = [name for name, resolved in resolved_required.items()
               if resolved is None]
    if missing:
        unreal.log_error("[FixProgramRotation] 缺少必需轨道 %s；实际轨道名示例=%s，未保存" %
                         (missing, ", ".join(before_names[:8])))
        return False
    bone_root_track_name = resolved_required[BONE_ROOT]
    unreal.log("[FixProgramRotation] resolved Bone_Root track=%s" % bone_root_track_name)

    try:
        before_tracks = {
            name: _track_signature(_get_track_keys(model, controller, name))
            for name in before_names
        }
        bone_root_keys = _get_track_keys(
            model, controller, bone_root_track_name, anim)
        before_tracks[bone_root_track_name] = _track_signature(bone_root_keys)
        preserved_track_names = (
            resolved_required["Root"],
            resolved_required["Bip001"],
        )
        before_preserved_tracks = {
            name: _track_signature(_get_track_keys(model, controller, name, anim))
            for name in preserved_track_names
        }
    except Exception as ex:
        unreal.log_error("[FixProgramRotation] 读取轨道失败，未保存: %s" % ex)
        return False

    positions, rotations, scales = bone_root_keys
    if not rotations:
        unreal.log_error("[FixProgramRotation] Bone_Root 没有 Rotation keys，未保存")
        return False

    first_rotation = rotations[0]
    fixed_rotations = [first_rotation for _ in rotations]
    before_curves = _curve_names(anim)
    before_rm_curves = _rm_curve_names(anim)
    first_pose_rotation = _pose_rotation(anim, bone_root_track_name, 0)

    unreal.log("[FixProgramRotation] Bone_Root keys: P=%d R=%d S=%d" %
               (len(positions), len(rotations), len(scales)))
    unreal.log("[FixProgramRotation] first raw rotation: %s" % _rotator_text(first_rotation))
    if first_pose_rotation is not None:
        unreal.log("[FixProgramRotation] first sampled pose rotation: %s" %
                   _rotator_text(first_pose_rotation))
    unreal.log("[FixProgramRotation] bone tracks=%d float curves=%d RM curves=%d" %
               (len(before_names), len(before_curves), len(before_rm_curves)))
    unreal.log("[FixProgramRotation] RM curves before: %s" %
               (", ".join(before_rm_curves) if before_rm_curves else "<none>"))

    bracket_open = False
    try:
        bracket_open = _open_bracket(controller)
        _set_bone_track_keys(
            controller, bone_root_track_name, positions, fixed_rotations, scales)
    except Exception as ex:
        unreal.log_error("[FixProgramRotation] 写入 Bone_Root 失败，未保存: %s" % ex)
        return False
    finally:
        if bracket_open:
            try:
                _close_bracket(controller)
            except Exception as ex:
                unreal.log_warning("[FixProgramRotation] close_bracket 失败: %s" % ex)

    # 保存前验证：只允许 Bone_Root.rotation 变化，且必须变成第一帧常量。
    try:
        after_pre_save = _track_signature(
            _get_track_keys(model, controller, bone_root_track_name, anim))
        if after_pre_save["position"] != before_tracks[bone_root_track_name]["position"]:
            raise RuntimeError("Bone_Root Position keys 被改变")
        if after_pre_save["scale"] != before_tracks[bone_root_track_name]["scale"]:
            raise RuntimeError("Bone_Root Scale keys 被改变")
        expected_rotation = tuple(
            _value_signature(first_rotation, ("x", "y", "z", "w"))
            for _ in rotations
        )
        if after_pre_save["rotation"] != expected_rotation:
            raise RuntimeError("Bone_Root Rotation keys 未全部固定为第一帧")

        after_names = _track_names(model)
        if after_names != before_names:
            raise RuntimeError("骨骼轨道名称/顺序发生变化")
        after_curves = _curve_names(anim)
        if after_curves != before_curves:
            raise RuntimeError("FloatCurve 名称发生变化")
        after_rm_curves = _rm_curve_names(anim)
        if after_rm_curves != before_rm_curves:
            raise RuntimeError("RM_* 曲线名称发生变化")

        # Root/Bip001 用 evaluated pose 做数据级校验；其余轨道由名称/顺序校验，
        # 且本次唯一写入调用明确只针对 bone_root。
        for name in preserved_track_names:
            current = _track_signature(_get_track_keys(model, controller, name, anim))
            if not _same_signature(current, before_preserved_tracks[name]):
                raise RuntimeError("保留骨骼轨道被改变: %s" % name)
    except Exception as ex:
        unreal.log_error("[FixProgramRotation] 保存前验证失败，未保存: %s" % ex)
        return False

    try:
        _save_asset(anim)
    except Exception as ex:
        unreal.log_error("[FixProgramRotation] 保存失败: %s" % ex)
        return False

    # 保存后重新读取资产，验证落盘结果而不是只验证内存对象。
    try:
        reloaded = unreal.load_asset(ASSET)
        reloaded_controller = _get_controller(reloaded)
        reloaded_model = _get_data_model(reloaded, reloaded_controller)
        if reloaded_controller is None or reloaded_model is None:
            raise RuntimeError("保存后重新加载资产缺少 Controller/DataModel")
        saved_signature = _track_signature(
            _get_track_keys(reloaded_model, reloaded_controller, bone_root_track_name, reloaded))
        if saved_signature["position"] != before_tracks[bone_root_track_name]["position"]:
            raise RuntimeError("保存后 Bone_Root Position keys 不一致")
        if saved_signature["scale"] != before_tracks[bone_root_track_name]["scale"]:
            raise RuntimeError("保存后 Bone_Root Scale keys 不一致")
        if saved_signature["rotation"] != expected_rotation:
            raise RuntimeError("保存后 Bone_Root Rotation 不是第一帧常量")
        if _track_names(reloaded_model) != before_names:
            raise RuntimeError("保存后骨骼轨道名称/顺序不一致")
        if _curve_names(reloaded) != before_curves:
            raise RuntimeError("保存后 FloatCurve 名称不一致")
        if _rm_curve_names(reloaded) != before_rm_curves:
            raise RuntimeError("保存后 RM_* 曲线名称不一致")
        for name in preserved_track_names:
            saved_preserved = _track_signature(
                _get_track_keys(reloaded_model, reloaded_controller, name, reloaded))
            if not _same_signature(saved_preserved, before_preserved_tracks[name]):
                raise RuntimeError("保存后保留骨骼轨道不一致: %s" % name)
    except Exception as ex:
        unreal.log_error("[FixProgramRotation] 保存后验证失败: %s" % ex)
        return False

    unreal.log("[FixProgramRotation] SUCCESS: 已覆盖保存既有资产")
    unreal.log("[FixProgramRotation] Bone_Root rotation=%d keys, constant=%s" %
               (len(saved_signature["rotation"]), str(True)))
    unreal.log("[FixProgramRotation] preserved tracks=%d curves=%d RM curves=%d" %
               (len(before_names), len(before_curves), len(before_rm_curves)))
    return True


run()
