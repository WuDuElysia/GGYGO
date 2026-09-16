# -*- coding: utf-8 -*-
"""
diag_blendspace.py —— 只读诊断：为什么 WalkRun BlendSpace 没有表现。

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/diag_blendspace.py", encoding="utf-8").read())

按可能性从高到低逐项打印：
  1. 资产类型（BlendSpace1D 只用 X 轴；2D 才吃 Y）
  2. 目标骨架是否与动画/角色一致 —— 不一致时样本会被静默忽略
  3. 轴范围与样本坐标是否匹配
  4. 样本引用的动画是否有效、是否标记为 Looping（非循环样本在 BlendSpace 里会播一次就停）
  5. 每个样本的 RateScale 与动画时长（时长差异过大时同步混合会拉扯）
"""

import unreal

BS = "/Game/Characters/Player/Pyrios/Animation/Movement/BS_Pyrios_WalkRun"
SKELETON = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model_Skeleton"
ABP = "/Game/BP/Anim/ABP_Pyrios"


def run():
    bs = unreal.load_asset(BS)
    if not bs:
        unreal.log_error("[Diag] BlendSpace 加载失败: %s" % BS)
        return

    unreal.log("=" * 92)
    unreal.log("[Diag] 资产类型 = %s" % type(bs).__name__)
    unreal.log("[Diag] 是否 BlendSpace1D = %s（1D 只读 X 轴）"
               % isinstance(bs, unreal.BlendSpace1D))

    # 骨架一致性
    try:
        bs_skel = bs.get_editor_property("target_skeleton")
        unreal.log("[Diag] BlendSpace.target_skeleton = %s"
                   % (bs_skel.get_path_name() if bs_skel else "None"))
        unreal.log("[Diag] 期望骨架                    = %s" % SKELETON)
        if bs_skel:
            unreal.log("[Diag] 骨架匹配 = %s" % (bs_skel.get_path_name().startswith(SKELETON)))
    except Exception as exc:
        unreal.log_warning("[Diag] 读 target_skeleton 失败: %s" % exc)

    # 轴
    try:
        params = bs.get_editor_property("blend_parameters")
        for i in range(len(params)):
            p = params[i]
            unreal.log("[Diag] 轴[%d] name='%s' min=%.3f max=%.3f grid=%d"
                       % (i, p.get_editor_property("display_name"),
                          p.get_editor_property("min"),
                          p.get_editor_property("max"),
                          p.get_editor_property("grid_num")))
    except Exception as exc:
        unreal.log_warning("[Diag] 读轴失败: %s" % exc)

    # 样本
    try:
        samples = bs.get_editor_property("sample_data")
        unreal.log("[Diag] 样本数 = %d" % len(samples))
        for s in samples:
            anim = s.get_editor_property("animation")
            val = s.get_editor_property("sample_value")
            rate = s.get_editor_property("rate_scale")
            if not anim:
                unreal.log_warning("        样本动画为 None @ (%.3f %.3f)" % (val.x, val.y))
                continue
            length = 0.0
            looping = None
            anim_skel = None
            try:
                length = float(anim.get_editor_property("sequence_length"))
            except Exception:
                pass
            try:
                looping = bool(anim.get_editor_property("loop"))
            except Exception:
                try:
                    looping = bool(anim.get_editor_property("b_loop"))
                except Exception:
                    looping = None
            try:
                anim_skel = anim.get_editor_property("skeleton")
            except Exception:
                pass
            unreal.log("        %-50s @ (%.3f %.3f) rate=%.2f len=%.4f loop=%s"
                       % (anim.get_name(), val.x, val.y, rate, length, looping))
            if anim_skel:
                unreal.log("            animSkeleton=%s" % anim_skel.get_path_name())
    except Exception as exc:
        unreal.log_error("[Diag] 读样本失败: %s" % exc)

    # 其它可能让混合失效的属性
    for prop in ("per_bone_blend", "notify_trigger_mode", "b_loop",
                 "interpolation_param", "preferred_triangulation_direction"):
        try:
            unreal.log("[Diag] %s = %s" % (prop, bs.get_editor_property(prop)))
        except Exception:
            pass

    # ABP 里 AnimSet 的 blendSpaces 是否指向它
    abp = unreal.load_asset(ABP)
    if abp:
        try:
            cdo = unreal.get_default_object(abp.generated_class())
            anim_set = cdo.get_editor_property("anim_set")
            bs_map = anim_set.get_editor_property("blend_spaces")
            unreal.log("[Diag] AnimSet.blendSpaces:")
            for k in bs_map:
                v = bs_map[k]
                unreal.log("        '%s' -> %s" % (k, v.get_path_name() if v else "None"))
            seq_map = anim_set.get_editor_property("sequences")
            unreal.log("[Diag] AnimSet.sequences:")
            for k in seq_map:
                v = seq_map[k]
                unreal.log("        '%s' -> %s" % (k, v.get_name() if v else "None"))
        except Exception as exc:
            unreal.log_warning("[Diag] 读 AnimSet 失败: %s" % exc)

    unreal.log("[Diag] done.")


run()
