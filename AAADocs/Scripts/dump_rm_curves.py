# -*- coding: utf-8 -*-
"""
dump_rm_curves.py —— 只读：导出 AnimSequence 上已有 RM_ 授权曲线的实际数值

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/dump_rm_curves.py", encoding="utf-8").read())

用途：看清游戏真正消费的移动数据（rm_speed / RM_VelocityDirX/Y / rm_yaw / rm_pos / rm_dist）
      随时间的形状，判断 dirxy 当前在哪个坐标系、以及正确的 root 局部重表达方式。
不写任何资产。
"""

import unreal

ANIM = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
        "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack")
NAMES = ["RM_Speed", "RM_VelocityDirX", "RM_VelocityDirY", "RM_Yaw",
         "RM_PosX", "RM_PosY", "RM_Dist"]
SAMPLES = 28


def val(a, n, t):
    """按时间求曲线值（本引擎可用 API）。"""
    try:
        return float(unreal.AnimationLibrary.get_float_value_at_time(a, unreal.Name(n), float(t)))
    except Exception:
        return 0.0


def key_info(a, n):
    """返回 (键数, first, last, min, max)，读不到则 keys=0。"""
    try:
        res = unreal.AnimationLibrary.get_float_keys(a, unreal.Name(n))
        # 兼容返回 (times, values) 或 单一 values 列表
        vals = None
        if isinstance(res, (tuple, list)) and len(res) == 2 and \
                isinstance(res[0], (list, tuple)) and isinstance(res[1], (list, tuple)):
            vals = list(res[1])
        elif isinstance(res, (list, tuple)):
            vals = list(res)
        if vals:
            fv = [float(x) for x in vals]
            return (len(fv), fv[0], fv[-1], min(fv), max(fv))
    except Exception:
        pass
    return (0, 0.0, 0.0, 0.0, 0.0)


def run():
    a = unreal.load_asset(ANIM)
    if not isinstance(a, unreal.AnimSequence):
        unreal.log_warning("不是 AnimSequence: %s" % ANIM)
        return
    unreal.log("=" * 72)
    unreal.log("[Dump] %s" % a.get_name())
    try:
        length = float(a.get_editor_property("sequence_length"))
    except Exception:
        length = 0.0
    unreal.log("[Dump] sequence_length=%.4f" % length)

    for n in NAMES:
        exist = False
        try:
            exist = bool(unreal.AnimationLibrary.does_curve_exist(
                a, unreal.Name(n), unreal.RawCurveTrackTypes.RCT_FLOAT))
        except Exception:
            pass
        cnt, first, last, mn, mx = key_info(a, n)
        unreal.log("[Dump] %-16s exist=%s keys=%3d first=%.3f last=%.3f min=%.3f max=%.3f"
                   % (n, exist, cnt, first, last, mn, mx))

    unreal.log("     t    Speed    DirX    DirY     Yaw     PosX     PosY     Dist")
    if length <= 0.0:
        return
    for i in range(SAMPLES + 1):
        t = length * i / SAMPLES
        unreal.log("  %5.2f %7.1f %7.3f %7.3f %7.1f %8.2f %8.2f %8.2f"
                   % (t,
                      val(a, "RM_Speed", t),
                      val(a, "RM_VelocityDirX", t),
                      val(a, "RM_VelocityDirY", t),
                      val(a, "RM_Yaw", t),
                      val(a, "RM_PosX", t),
                      val(a, "RM_PosY", t),
                      val(a, "RM_Dist", t)))
    unreal.log("[Dump] done.")


run()
