# -*- coding: utf-8 -*-
"""
probe_anim_api.py —— 只读：探测本引擎版本下 AnimSequence 读取曲线值的可用 API

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/probe_anim_api.py", encoding="utf-8").read())

打印 AnimSequence / Controller / DataModel 上与 curve/model/float/key 相关的方法名，
用于确定读取 RM_ 曲线数值的正确调用方式。不写任何资产。
"""

import unreal

ANIM = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
        "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack")

KEYWORDS = ("curve", "model", "data", "controller", "float", "key", "eval")


def dump(obj, label):
    if obj is None:
        unreal.log("[Probe] %s = None" % label)
        return
    ms = [m for m in dir(obj) if not m.startswith("__")]
    hit = [m for m in ms if any(k in m.lower() for k in KEYWORDS)]
    unreal.log("[Probe] %s (%s) 相关方法 %d/%d:" % (label, type(obj).__name__, len(hit), len(ms)))
    for m in hit:
        unreal.log("        %s" % m)


def run():
    a = unreal.load_asset(ANIM)
    unreal.log("=" * 72)
    dump(a, "AnimSequence")

    ctrl = None
    try:
        ctrl = a.get_controller()
    except Exception as ex:
        unreal.log_warning("[Probe] get_controller: %s" % ex)
    dump(ctrl, "Controller")

    if ctrl is not None:
        for f in ("get_model", "get_data_model", "get_data_model_interface"):
            try:
                m = getattr(ctrl, f)()
                unreal.log("[Probe] controller.%s -> %s" % (f, type(m).__name__ if m else "None"))
                if m:
                    dump(m, "Model(via ctrl.%s)" % f)
            except Exception as ex:
                unreal.log_warning("[Probe] controller.%s: %s" % (f, ex))

    for f in ("get_data_model", "get_data_model_interface", "get_data_model_object"):
        try:
            m = getattr(a, f)()
            unreal.log("[Probe] anim.%s -> %s" % (f, type(m).__name__ if m else "None"))
            if m:
                dump(m, "Model(via anim.%s)" % f)
        except Exception as ex:
            unreal.log_warning("[Probe] anim.%s: %s" % (f, ex))

    # AnimationLibrary 上与曲线相关的静态方法
    try:
        ms = [m for m in dir(unreal.AnimationLibrary) if not m.startswith("__")]
        hit = [m for m in ms if any(k in m.lower() for k in ("curve", "float", "key"))]
        unreal.log("[Probe] AnimationLibrary 曲线相关方法 %d:" % len(hit))
        for m in hit:
            unreal.log("        %s" % m)
    except Exception as ex:
        unreal.log_warning("[Probe] AnimationLibrary: %s" % ex)

    unreal.log("[Probe] done.")


run()
