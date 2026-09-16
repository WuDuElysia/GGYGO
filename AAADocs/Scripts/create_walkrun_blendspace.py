# -*- coding: utf-8 -*-
"""
create_walkrun_blendspace.py —— 创建走跑混合用的 BlendSpace1D 并接进 ABP 的 AnimSet。

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/create_walkrun_blendspace.py", encoding="utf-8").read())

为什么是 1D 而不是 2D：Pyrios 只有 Walk_Loop / Run_Loop 两个移动循环动画，
没有侧向或后退的循环，2D 的另一个轴无从填充。ZZZ 的移动是「角色转向移动方向」，
方向靠 Actor 朝向解决，混合只需要表达速度档位。

轴对应 FZZZAnimStateMemory::GaitBlendY：0 = Walk，1 = Run。
那个值由 FZZZLocomotionEvents::AdvanceGaitBlend 用 FInterpConstantTo 平滑推进，
所以 BlendSpace 自己不需要再做平滑（两级平滑串联会让混合明显滞后于实际步态切换）。
"""

import unreal

FOLDER = "/Game/Characters/Player/Pyrios/Animation"
ASSET_NAME = "BS_Pyrios_WalkRun"
SKELETON = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model_Skeleton"
WALK = FOLDER + "/Avatar_Male_Size03_Pyrois_Ani_Walk_Loop"
RUN = FOLDER + "/Avatar_Male_Size03_Pyrois_Ani_Run_Loop"
ABP = "/Game/BP/Anim/ABP_Pyrios"
ANIMSET_KEY = "walkRun"


def run():
    asset_path = "%s/%s" % (FOLDER, ASSET_NAME)

    walk = unreal.load_asset(WALK)
    run_anim = unreal.load_asset(RUN)
    skeleton = unreal.load_asset(SKELETON)
    if not walk or not run_anim or not skeleton:
        unreal.log_error("[BS] 缺少 Walk_Loop / Run_Loop / Skeleton")
        return

    if unreal.EditorAssetLibrary.does_asset_exist(asset_path):
        unreal.log_warning("[BS] 已存在，先删除再重建: %s" % asset_path)
        unreal.EditorAssetLibrary.delete_asset(asset_path)

    factory = unreal.BlendSpaceFactory1D()
    factory.set_editor_property("target_skeleton", skeleton)

    tools = unreal.AssetToolsHelpers.get_asset_tools()
    bs = tools.create_asset(ASSET_NAME, FOLDER, unreal.BlendSpace1D, factory)
    if not bs:
        unreal.log_error("[BS] 创建失败")
        return

    # 轴：0..1，命名与 GaitBlendY 对齐，方便在 AnimBP 里连线时不必猜含义。
    try:
        axis = unreal.InterpolationParameter()
        axis.set_editor_property("interpolation_time", 0.0)
        bs.set_editor_property("interpolation_param_x", axis)
    except Exception as exc:
        unreal.log_warning("[BS] 轴插值参数设置跳过: %s" % exc)

    applied = []
    for prop, value in (("axis_label", "GaitBlendY"),
                        ("blend_parameters", None)):
        if value is None:
            continue
        try:
            bs.set_editor_property(prop, value)
            applied.append(prop)
        except Exception:
            pass

    # 轴范围与名称。BlendParameter 是结构体，逐字段设。
    try:
        param = bs.get_editor_property("blend_parameters")
        param.set_editor_property("display_name", "GaitBlendY")
        param.set_editor_property("min", 0.0)
        param.set_editor_property("max", 1.0)
        param.set_editor_property("grid_num", 1)
        bs.set_editor_property("blend_parameters", param)
        unreal.log("[BS] 轴设置完成: GaitBlendY 0..1 grid=1")
    except Exception as exc:
        unreal.log_warning("[BS] 轴设置失败（可在编辑器里手改）: %s" % exc)

    # 样本：Walk @0，Run @1。
    added = 0
    add_sample = getattr(unreal.AnimationBlendSpaceSampleLibrary, "add_blend_space_sample", None) \
        if hasattr(unreal, "AnimationBlendSpaceSampleLibrary") else None
    if callable(add_sample):
        for anim, value in ((walk, 0.0), (run_anim, 1.0)):
            try:
                add_sample(bs, anim, unreal.Vector(value, 0.0, 0.0))
                added += 1
            except Exception as exc:
                unreal.log_warning("[BS] add_blend_space_sample 失败: %s" % exc)
    else:
        # 退回直接写 blend_samples 数组。
        try:
            samples = []
            for anim, value in ((walk, 0.0), (run_anim, 1.0)):
                s = unreal.BlendSample()
                s.set_editor_property("animation", anim)
                s.set_editor_property("sample_value", unreal.Vector(value, 0.0, 0.0))
                s.set_editor_property("rate_scale", 1.0)
                samples.append(s)
            bs.set_editor_property("sample_data", samples)
            added = len(samples)
            unreal.log("[BS] 用 sample_data 写入 %d 个样本" % added)
        except Exception as exc:
            unreal.log_error("[BS] 样本写入失败: %s" % exc)

    unreal.EditorAssetLibrary.save_loaded_asset(bs, False)
    unreal.log("[BS] 创建完成 %s 样本数=%d" % (asset_path, added))

    # 回读确认
    try:
        reloaded = unreal.load_asset(asset_path)
        data = reloaded.get_editor_property("sample_data")
        unreal.log("[BS] 回读样本数=%d" % len(data))
        for s in data:
            a = s.get_editor_property("animation")
            v = s.get_editor_property("sample_value")
            unreal.log("        %-52s @ %.2f" % (a.get_name() if a else "None", v.x))
    except Exception as exc:
        unreal.log_warning("[BS] 回读失败: %s" % exc)

    # 接进 ABP 的 AnimSet
    abp = unreal.load_asset(ABP)
    if abp:
        try:
            gen = abp.generated_class()
            cdo = unreal.get_default_object(gen)
            anim_set = cdo.get_editor_property("anim_set")
            bs_map = anim_set.get_editor_property("blend_spaces")
            bs_map[ANIMSET_KEY] = unreal.load_asset(asset_path)
            anim_set.set_editor_property("blend_spaces", bs_map)
            cdo.set_editor_property("anim_set", anim_set)
            unreal.EditorAssetLibrary.save_loaded_asset(abp, False)
            unreal.log("[BS] 已接进 ABP_Pyrios 的 AnimSet['%s']" % ANIMSET_KEY)
        except Exception as exc:
            unreal.log_warning("[BS] 接入 ABP 失败（可在细节面板手连）: %s" % exc)

    unreal.log("[BS] done.")


run()
