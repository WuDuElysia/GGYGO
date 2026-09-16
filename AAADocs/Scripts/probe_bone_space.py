# -*- coding: utf-8 -*-
"""
probe_bone_space.py —— 只读：查清 Bip001 的 local 轴向与 component space 的关系。

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/probe_bone_space.py", encoding="utf-8").read())

要回答的问题：FBX Y-up 到 UE Z-up 的坐标系转换烘在哪一级？
Bip001 的 local 位移里前进量落在 Z 轴，说明它自己没被转换；
那么转换要么在根骨骼 Avatar_..._Model 的 transform 里，要么根本没做。

逐级累乘 local transform 得到 component space，再看 Bip001 在 component space 里
的位移是否落在 UE 的 X（前）轴上 —— 那才是能和 RootMotion_* 曲线直接相减的空间。
"""

import unreal

ANIM = "/Game/Characters/Player/Pyrios/Animation/Avatar_Male_Size03_Pyrois_Ani_TurnBack"
MESH = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"
CHAIN = ["Avatar_Male_Size03_Pyrois_Model", "Bone_Root", "Bip001"]
FRAMES = [0, 72, 143]


def fmt_x(label, x):
    t = x.translation
    r = x.rotation.rotator()
    s = x.scale3d
    return ("%-34s T=(%9.2f %9.2f %9.2f) R=(P%8.2f Y%8.2f R%8.2f) S=(%.2f %.2f %.2f)"
            % (label, t.x, t.y, t.z, r.pitch, r.yaw, r.roll, s.x, s.y, s.z))


def run():
    anim = unreal.load_asset(ANIM)
    mesh = unreal.load_asset(MESH)
    unreal.log("=" * 100)

    # 骨架 reference pose：确认根骨骼是否承载轴转换
    unreal.log("[Space] --- 骨架 reference pose（local）---")
    for bone in CHAIN:
        try:
            x = unreal.AnimationLibrary.get_reference_pose_for_bone(mesh.skeleton, bone) \
                if hasattr(unreal.AnimationLibrary, "get_reference_pose_for_bone") else None
            if x is not None:
                unreal.log("        " + fmt_x("ref " + bone, x))
        except Exception as exc:
            unreal.log_warning("        ref %s 读取失败: %s" % (bone, exc))

    # 动画里逐级 local，以及累乘出的 component space
    for frame in FRAMES:
        unreal.log("[Space] --- frame %d ---" % frame)
        comp = unreal.Transform()
        for bone in CHAIN:
            try:
                local = unreal.AnimationLibrary.get_bone_pose_for_frame(anim, bone, frame, True)
            except Exception as exc:
                unreal.log_warning("        %s 读取失败: %s" % (bone, exc))
                continue
            unreal.log("        " + fmt_x("local " + bone, local))
            # UE 的 Transform 组合：child_component = child_local * parent_component
            comp = local.multiply(comp) if hasattr(local, "multiply") else comp
            unreal.log("        " + fmt_x("  comp " + bone, comp))

    unreal.log("[Space] done.")


run()
