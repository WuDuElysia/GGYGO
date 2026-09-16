# -*- coding: utf-8 -*-
"""
fix_blendspace_axis.py —— 回读并修正 BS_Pyrios_WalkRun 的轴范围。

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/fix_blendspace_axis.py", encoding="utf-8").read())

轴必须是 0..1，因为驱动它的 FZZZAnimStateMemory::GaitBlendY 就是 0（Walk）到 1（Run）。
BlendSpace 的默认轴范围不是这个区间，不改的话两个样本会挤在轴的最左端，
混合权重实际上永远停在 Walk 上。
"""

import unreal

ASSET = "/Game/Characters/Player/Pyrios/Animation/BS_Pyrios_WalkRun"


def dump(bs, label):
    unreal.log("[Axis] --- %s ---" % label)
    try:
        params = bs.get_editor_property("blend_parameters")
        unreal.log("        blend_parameters 类型=%s 长度=%s"
                   % (type(params).__name__, len(params) if hasattr(params, "__len__") else "?"))
        for i in range(len(params)):
            p = params[i]
            unreal.log("        [%d] name='%s' min=%.3f max=%.3f gridNum=%d"
                       % (i,
                          p.get_editor_property("display_name"),
                          p.get_editor_property("min"),
                          p.get_editor_property("max"),
                          p.get_editor_property("grid_num")))
    except Exception as exc:
        unreal.log_warning("        读取失败: %s" % exc)

    try:
        for s in bs.get_editor_property("sample_data"):
            a = s.get_editor_property("animation")
            v = s.get_editor_property("sample_value")
            unreal.log("        sample %-50s @ (%.3f %.3f)"
                       % (a.get_name() if a else "None", v.x, v.y))
    except Exception as exc:
        unreal.log_warning("        样本读取失败: %s" % exc)


def run():
    bs = unreal.load_asset(ASSET)
    if not bs:
        unreal.log_error("[Axis] 加载失败: %s" % ASSET)
        return

    dump(bs, "修改前")

    try:
        params = bs.get_editor_property("blend_parameters")
        p = params[0]
        p.set_editor_property("display_name", "GaitBlendY")
        p.set_editor_property("min", 0.0)
        p.set_editor_property("max", 1.0)
        # grid_num=1 表示轴上只有两个格点（0 与 1），正好对应 Walk / Run 两个样本。
        p.set_editor_property("grid_num", 1)
        params[0] = p
        bs.set_editor_property("blend_parameters", params)
        unreal.log("[Axis] 轴已写入")
    except Exception as exc:
        unreal.log_error("[Axis] 轴写入失败: %s" % exc)
        return

    unreal.EditorAssetLibrary.save_loaded_asset(bs, False)

    reloaded = unreal.load_asset(ASSET)
    dump(reloaded, "修改并保存后（回读）")
    unreal.log("[Axis] done.")


run()
