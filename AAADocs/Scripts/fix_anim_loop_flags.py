# -*- coding: utf-8 -*-
"""
fix_anim_loop_flags.py —— 按 Cfg_LoopTime 曲线设置 AnimSequence 的 loop 标记。

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/fix_anim_loop_flags.py", encoding="utf-8").read())

FBX 导入出来的 AnimSequence 一律 loop=False。循环动画保持 False 的后果很隐蔽：
单独播放看不出问题（播完停在最后一帧），但放进 BlendSpace 当样本时，
角色一移动动画就播一次然后冻住 —— 表现为「完全没有走跑动画」。

哪些该循环不靠猜：烘焙管线已经把 Unity 的 muscleClip.loopTime 写成了
每个动画上的 Cfg_LoopTime 常量曲线，这里直接读它。
"""

import unreal

FOLDER = "/Game/Characters/Player/Pyrios/Animation"
LOOP_CURVE = "Cfg_LoopTime"
DRY_RUN = False


def read_loop_flag_curve(anim):
    """读 Cfg_LoopTime 曲线；曲线不存在返回 None（不是 0，两者要区分）。"""
    try:
        exists = unreal.AnimationLibrary.does_curve_exist(
            anim, unreal.Name(LOOP_CURVE), unreal.RawCurveTrackTypes.RCT_FLOAT)
    except Exception:
        exists = False
    if not exists:
        return None
    try:
        return float(unreal.AnimationLibrary.get_float_value_at_time(
            anim, unreal.Name(LOOP_CURVE), 0.0))
    except Exception:
        return None


def list_animation_paths():
    """列出目标目录下的全部资产路径。

    走 AssetRegistry 而不是 EditorAssetLibrary.list_assets：后者对本目录返回空列表，
    而 AssetRegistry 是内容浏览器自己用的那条路径，行为与界面一致。
    """
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    datas = registry.get_assets_by_path(unreal.Name(FOLDER), recursive=True)
    paths = []
    for data in datas:
        try:
            paths.append(str(data.get_editor_property("package_name")))
        except Exception:
            pass
    return paths


def run():
    paths = list_animation_paths()
    unreal.log("[Loop] AssetRegistry 返回 %d 个资产" % len(paths))

    changed = []
    already = []
    no_curve = []
    for path in paths:
        anim = unreal.load_asset(path)
        if not isinstance(anim, unreal.AnimSequence):
            continue

        value = read_loop_flag_curve(anim)
        if value is None:
            no_curve.append(anim.get_name())
            continue

        want_loop = value > 0.5
        try:
            current = bool(anim.get_editor_property("loop"))
        except Exception as exc:
            unreal.log_warning("[Loop] %s 读 loop 失败: %s" % (anim.get_name(), exc))
            continue

        if current == want_loop:
            already.append((anim.get_name(), want_loop))
            continue

        if not DRY_RUN:
            try:
                anim.set_editor_property("loop", want_loop)
                unreal.EditorAssetLibrary.save_loaded_asset(anim, False)
            except Exception as exc:
                unreal.log_error("[Loop] %s 写 loop 失败: %s" % (anim.get_name(), exc))
                continue
        changed.append((anim.get_name(), current, want_loop))

    unreal.log("=" * 92)
    unreal.log("[Loop] 扫描 %d 个资产，改写 %d，已正确 %d，无 Cfg_LoopTime 曲线 %d，dryRun=%s"
               % (len(paths), len(changed), len(already), len(no_curve), DRY_RUN))
    unreal.log("[Loop] 改写明细（loop: 旧 -> 新）：")
    for name, old, new in changed:
        unreal.log("        %-52s %s -> %s" % (name, old, new))
    loop_true = [n for n, v in already if v] + [n for n, o, v in changed if v]
    unreal.log("[Loop] 最终 loop=True 的动画共 %d 个：" % len(loop_true))
    for n in sorted(loop_true):
        unreal.log("        %s" % n)
    for n in no_curve:
        unreal.log_warning("[Loop] 无 Cfg_LoopTime 曲线，未处理: %s" % n)
    unreal.log("[Loop] done.")


run()
