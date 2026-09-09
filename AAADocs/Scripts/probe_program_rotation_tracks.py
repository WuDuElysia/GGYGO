# -*- coding: utf-8 -*-
"""只读枚举 ProgramRotation 的 AnimationDataModel 骨骼轨道。"""

import unreal


ASSET = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
         "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack_ProgramRotation")
REQUIRED = ("Root", "Bone_Root", "Bip001")


def _short(value, limit=1200):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"
    return text if len(text) <= limit else text[:limit] + "..."


def _describe(label, value):
    unreal.log("[TrackProbe] %s type=%s value=%s" %
               (label, type(value).__name__, _short(value)))


def _name_text(value):
    try:
        to_string = getattr(value, "to_string", None)
        if callable(to_string):
            return str(to_string())
    except Exception:
        pass
    return str(value)


def _dump_track(label, track):
    if track is None:
        unreal.log_warning("[TrackProbe] %s=None" % label)
        return
    _describe(label, track)
    for getter_name in ("get_positional_keys", "get_rotational_keys", "get_scale_keys"):
        getter = getattr(track, getter_name, None)
        if not callable(getter):
            unreal.log_warning("[TrackProbe] %s.%s 不存在" % (label, getter_name))
            continue
        try:
            values = list(getter())
            unreal.log("[TrackProbe] %s.%s count=%d first=%s" %
                       (label, getter_name, len(values),
                        _short(values[0]) if values else "<none>"))
        except Exception as ex:
            unreal.log_warning("[TrackProbe] %s.%s failed: %s" %
                               (label, getter_name, ex))


def _try_call(label, fn):
    try:
        value = fn()
        _describe(label, value)
        return value
    except Exception as ex:
        unreal.log_warning("[TrackProbe] %s failed: %s" % (label, ex))
        return None


def run():
    unreal.log("=" * 88)
    unreal.log("[TrackProbe] target=%s" % ASSET)
    anim = unreal.load_asset(ASSET)
    if not isinstance(anim, unreal.AnimSequence):
        unreal.log_error("[TrackProbe] 目标不是 AnimSequence")
        return

    controller = _try_call(
        "AnimSequence.controller",
        lambda: anim.get_editor_property("controller"))
    if controller is None:
        unreal.log_error("[TrackProbe] controller=None")
        return

    model = _try_call(
        "Controller.get_model_interface()",
        controller.get_model_interface)
    if model is None:
        unreal.log_error("[TrackProbe] model=None")
        return

    _try_call("DataModel.get_num_bone_tracks()", model.get_num_bone_tracks)
    _try_call("DataModel.get_number_of_keys()", model.get_number_of_keys)
    names = _try_call("DataModel.get_bone_track_names()", model.get_bone_track_names)
    if names is not None:
        try:
            names = list(names)
            unreal.log("[TrackProbe] names_count=%d" % len(names))
            for index, name in enumerate(names):
                unreal.log("[TrackProbe] name[%d] repr=%s str=%s text=%s" %
                           (index, _short(name), str(name), _name_text(name)))
        except Exception as ex:
            unreal.log_warning("[TrackProbe] 枚举 names 失败: %s" % ex)

    get_by_index = getattr(model, "get_bone_track_by_index", None)
    if callable(get_by_index):
        try:
            count = int(model.get_num_bone_tracks())
        except Exception:
            count = 0
        for index in range(count):
            track = _try_call(
                "DataModel.get_bone_track_by_index(%d)" % index,
                lambda index=index: get_by_index(index))
            _dump_track("track[%d]" % index, track)

    get_by_name = getattr(model, "get_bone_track_by_name", None)
    get_index_by_name = getattr(model, "get_bone_track_index_by_name", None)
    if callable(get_by_name):
        for required_name in REQUIRED:
            for argument_label, argument in (("Name", unreal.Name(required_name)),
                                              ("str", required_name)):
                track = _try_call(
                    "DataModel.get_bone_track_by_name(%s,%s)" %
                    (required_name, argument_label),
                    lambda argument=argument: get_by_name(argument))
                _dump_track("by_name[%s,%s]" % (required_name, argument_label), track)
                if callable(get_index_by_name):
                    _try_call(
                        "DataModel.get_bone_track_index_by_name(%s,%s)" %
                        (required_name, argument_label),
                        lambda argument=argument: get_index_by_name(argument))

    unreal.log("[TrackProbe] done; no write/save operation was called")


run()
