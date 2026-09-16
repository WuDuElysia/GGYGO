# -*- coding: utf-8 -*-
"""
probe_root_bone.py —— 只读：确认骨架里的 `Root` 骨骼是否直接承载 root motion。

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/probe_root_bone.py", encoding="utf-8").read())

FBX 里的外部 Null 节点 `Root` 被导入成了骨架的一根骨骼（在骨骼列表末尾）。
如果它的轨道里带着完整的位移与 yaw，那它的 component transform 就是现成的
root motion，扣除时不需要手工推任何轴映射 —— 直接做 transform 运算即可。

同时打印它的父链，确认它与 Bip001 是否在同一个父空间下。
"""

import unreal

ANIM = "/Game/Characters/Player/Pyrios/Animation/Avatar_Male_Size03_Pyrois_Ani_TurnBack"
MESH = "/Game/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model"
FRAMES = [0, 20, 60, 72, 143]


def fmt(label, x):
    t = x.translation
    r = x.rotation.rotator()
    return ("%-22s T=(%9.2f %9.2f %9.2f) R=(P%8.2f Y%8.2f R%8.2f)"
            % (label, t.x, t.y, t.z, r.pitch, r.yaw, r.roll))


def parent_chain(mesh, bone):
    """从 bone 一路往上到根，返回 [bone, parent, ..., root]。"""
    chain = [bone]
    guard = 0
    while guard < 64:
        guard += 1
        try:
            p = unreal.SkeletalMeshTools.get_bone_parent(mesh, chain[-1]) \
                if hasattr(unreal, "SkeletalMeshTools") else None
        except Exception:
            p = None
        if not p:
            break
        chain.append(p)
    return chain


def comp_of(anim, chain, frame):
    """chain 是 [bone, parent, ..., root]，逐级累乘得到 component transform。"""
    comp = unreal.Transform()
    for bone in reversed(chain):
        local = unreal.AnimationLibrary.get_bone_pose_for_frame(anim, bone, frame, True)
        comp = local.multiply(comp)
    return comp


def run():
    anim = unreal.load_asset(ANIM)
    unreal.log("=" * 100)

    # Root 骨骼在动画里有没有轨道？没有轨道时 get_bone_pose_for_frame 会返回 ref pose。
    unreal.log("[RootBone] --- Root 与 Bip001 的 local / 累乘 comp ---")
    for frame in FRAMES:
        for bone, chain in (("Root", ["Root", "Avatar_Male_Size03_Pyrois_Model"]),
                            ("Bip001", ["Bip001", "Bone_Root", "Avatar_Male_Size03_Pyrois_Model"])):
            try:
                local = unreal.AnimationLibrary.get_bone_pose_for_frame(anim, bone, frame, True)
                comp = comp_of(anim, chain, frame)
                unreal.log("  f%-4d %s" % (frame, fmt("local " + bone, local)))
                unreal.log("        %s" % fmt("comp  " + bone, comp))
            except Exception as exc:
                unreal.log_warning("  f%d %s 失败: %s" % (frame, bone, exc))

    unreal.log("[RootBone] done.")


run()
