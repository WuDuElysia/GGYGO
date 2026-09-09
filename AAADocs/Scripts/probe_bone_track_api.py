# -*- coding: utf-8 -*-
"""
probe_bone_track_api.py —— 只读探测 UE 5.8 AnimSequence 骨骼轨道 API。

只打印反射结果和现有 Bone_Root 轨道读取结果，不复制、不修改、不保存任何资产。
"""

import unreal

ANIM = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
        "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack")


def dump_methods(obj, label):
    if obj is None:
        unreal.log_warning("[BoneProbe] %s=None" % label)
        return
    names = [name for name in dir(obj) if not name.startswith("__")]
    hits = [name for name in names if any(token in name.lower() for token in ("bone", "track", "key", "pose"))]
    unreal.log("[BoneProbe] %s type=%s methods=%d/%d" %
               (label, type(obj).__name__, len(hits), len(names)))
    for name in hits:
        unreal.log("    %s" % name)


def describe_value(label, value):
    try:
        text = repr(value)
    except Exception:
        text = "<repr failed>"
    if len(text) > 1200:
        text = text[:1200] + "..."
    unreal.log("[BoneProbe] %s type=%s value=%s" %
               (label, type(value).__name__, text))


def try_call(label, fn):
    try:
        value = fn()
        describe_value(label, value)
        return value
    except Exception as ex:
        unreal.log_warning("[BoneProbe] %s failed: %s" % (label, ex))
        return None


def run():
    anim = unreal.load_asset(ANIM)
    if not isinstance(anim, unreal.AnimSequence):
        unreal.log_error("[BoneProbe] 不是 AnimSequence: %s" % ANIM)
        return

    unreal.log("=" * 72)
    unreal.log("[BoneProbe] asset=%s" % anim.get_path_name())
    get_controller = getattr(anim, "get_controller", None)
    controller = try_call("anim.get_controller", get_controller) if callable(get_controller) else None
    get_model = getattr(anim, "get_data_model", None)
    model = try_call("anim.get_data_model", get_model) if callable(get_model) else None
    dump_methods(anim, "AnimSequence")
    dump_methods(controller, "Controller")
    dump_methods(model, "DataModel")

    names = try_call("model.get_bone_track_names", model.get_bone_track_names if model else lambda: None)
    if names:
        names = [str(name) for name in names]
        unreal.log("[BoneProbe] track_names=%s" % ", ".join(names[:80]))

    bone_name = unreal.Name("Bone_Root")
    if controller:
        for method_name in ("get_bone_track_keys", "get_bone_track_key_times", "get_bone_track_transform_keys"):
            method = getattr(controller, method_name, None)
            if callable(method):
                try_call("controller.%s(Bone_Root)" % method_name,
                         lambda method=method: method(bone_name))
    if model:
        for method_name in ("get_bone_track_keys", "get_bone_track_key_times", "get_bone_track_transform_keys"):
            method = getattr(model, method_name, None)
            if callable(method):
                try_call("model.%s(Bone_Root)" % method_name,
                         lambda method=method: method(bone_name))

    unreal.log("[BoneProbe] done")


run()
