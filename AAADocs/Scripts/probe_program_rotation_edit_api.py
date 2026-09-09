# -*- coding: utf-8 -*-
"""
probe_program_rotation_edit_api.py —— 只读探测 ProgramRotation AnimSequence 的 Python 接口。

本脚本只读取反射属性、getter 返回值和骨骼轨道相关对象，不写入、不修改、不保存资产。
在 Unreal Editor Python Console 中执行：
    exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/probe_program_rotation_edit_api.py", encoding="utf-8").read())
"""

import unreal


ASSET = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
         "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack_ProgramRotation")

TOKENS = (
    "raw", "track", "data", "controller", "curve", "key", "bone",
    "transform", "pose", "editor", "model", "compressed",
)

EDITOR_PROPERTIES = (
    "raw_animation_data",
    "raw_curve_data",
    "data_model",
    "controller",
    "bone_tracks",
    "animation_data",
    "sequence_length",
    "num_frames",
    "number_of_keys",
    "sampling_frame_rate",
    "compressed_data",
)

NO_ARGUMENT_GETTERS = (
    "get_controller",
    "get_data_model",
    "get_raw_animation_data",
    "get_bone_track_names",
    "get_number_of_frames",
    "get_number_of_keys",
    "get_play_length",
)

TRACK_GETTERS = (
    "get_bone_track_keys",
    "get_bone_track_key_times",
    "get_bone_track_transform_keys",
    "get_bone_track_transforms",
)


def _short(value, limit=1400):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"
    if len(text) > limit:
        return text[:limit] + "..."
    return text


def _describe(label, value):
    unreal.log("[ProgramProbe] %s type=%s value=%s" %
               (label, type(value).__name__, _short(value)))


def _dump_matching_names(obj, label):
    if obj is None:
        unreal.log_warning("[ProgramProbe] %s=None" % label)
        return []
    try:
        names = sorted(name for name in dir(obj) if not name.startswith("__"))
    except Exception as ex:
        unreal.log_warning("[ProgramProbe] dir(%s) failed: %s" % (label, ex))
        return []
    hits = [name for name in names
            if any(token in name.lower() for token in TOKENS)]
    unreal.log("[ProgramProbe] %s matching_names=%d/%d" %
               (label, len(hits), len(names)))
    unreal.log("[ProgramProbe] %s names=%s" %
               (label, ", ".join(hits) if hits else "<none>"))
    return hits


def _safe_editor_property(obj, label, property_name):
    try:
        value = obj.get_editor_property(property_name)
        _describe("%s.get_editor_property(%s)" % (label, property_name), value)
        return value
    except Exception as ex:
        unreal.log_warning("[ProgramProbe] %s.get_editor_property(%s) failed: %s" %
                           (label, property_name, ex))
        return None


def _inspect_sequence_value(label, value):
    if value is None:
        return
    try:
        count = len(value)
    except Exception:
        return
    unreal.log("[ProgramProbe] %s length=%d" % (label, count))
    if count <= 0:
        return
    try:
        first = value[0]
    except Exception as ex:
        unreal.log_warning("[ProgramProbe] %s[0] failed: %s" % (label, ex))
        return
    _describe("%s[0]" % label, first)
    _dump_matching_names(first, "%s[0]" % label)
    for field_name in ("pos_keys", "position_keys", "translation_keys",
                       "rot_keys", "rotation_keys", "scale_keys", "scale3d_keys"):
        try:
            field_value = first.get_editor_property(field_name)
            _describe("%s[0].%s" % (label, field_name), field_value)
        except Exception:
            try:
                field_value = getattr(first, field_name)
                _describe("%s[0].%s" % (label, field_name), field_value)
            except Exception:
                pass


def _call_no_argument_getter(anim, method_name):
    method = getattr(anim, method_name, None)
    if not callable(method):
        return None
    try:
        value = method()
        _describe("AnimSequence.%s()" % method_name, value)
        _dump_matching_names(value, "%s() result" % method_name)
        _inspect_sequence_value("%s() result" % method_name, value)
        return value
    except Exception as ex:
        unreal.log_warning("[ProgramProbe] AnimSequence.%s() failed: %s" %
                           (method_name, ex))
        return None


def _call_track_getter(obj, label, method_name):
    method = getattr(obj, method_name, None)
    if not callable(method):
        return
    try:
        value = method(unreal.Name("Bone_Root"))
        _describe("%s.%s(Bone_Root)" % (label, method_name), value)
        _dump_matching_names(value, "%s.%s result" % (label, method_name))
        _inspect_sequence_value("%s.%s result" % (label, method_name), value)
    except Exception as ex:
        unreal.log_warning("[ProgramProbe] %s.%s(Bone_Root) failed: %s" %
                           (label, method_name, ex))


def run():
    unreal.log("=" * 88)
    unreal.log("[ProgramProbe] target=%s" % ASSET)

    anim = unreal.load_asset(ASSET)
    if not isinstance(anim, unreal.AnimSequence):
        unreal.log_error("[ProgramProbe] 目标不是 AnimSequence: %s" % ASSET)
        return

    _describe("asset", anim)
    try:
        unreal.log("[ProgramProbe] path=%s" % anim.get_path_name())
    except Exception:
        pass
    _dump_matching_names(anim, "AnimSequence")

    for property_name in EDITOR_PROPERTIES:
        value = _safe_editor_property(anim, "AnimSequence", property_name)
        if property_name in ("raw_animation_data", "bone_tracks", "animation_data"):
            _inspect_sequence_value("editor_property.%s" % property_name, value)

    controller = _call_no_argument_getter(anim, "get_controller")
    model = _call_no_argument_getter(anim, "get_data_model")

    for method_name in NO_ARGUMENT_GETTERS:
        if method_name not in ("get_controller", "get_data_model"):
            _call_no_argument_getter(anim, method_name)

    for label, obj in (("AnimSequence", anim), ("Controller", controller),
                       ("DataModel", model)):
        if obj is None:
            continue
        _dump_matching_names(obj, label)
        for method_name in TRACK_GETTERS:
            _call_track_getter(obj, label, method_name)

    for class_name in ("RawAnimSequenceTrack", "AnimationSequenceTrack",
                       "AnimationDataController", "AnimationDataModel"):
        cls = getattr(unreal, class_name, None)
        if cls is not None:
            _dump_matching_names(cls, "unreal.%s" % class_name)
        else:
            unreal.log("[ProgramProbe] unreal.%s=<not exposed>" % class_name)

    unreal.log("[ProgramProbe] done; no write/save operation was called")


run()
