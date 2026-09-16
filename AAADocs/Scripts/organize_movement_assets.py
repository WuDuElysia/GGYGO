# -*- coding: utf-8 -*-
"""
organize_movement_assets.py —— 把移动相关动画与 BlendSpace 归到 Animation/Movement/。

在 UE 编辑器 Python 命令行执行：
  exec(open(r"F:/ue_project/GGYGO/AAADocs/Scripts/organize_movement_assets.py", encoding="utf-8").read())

范围按「locomotion 状态机会用到的表现」划：走跑起停、转身、以及站立待机。
待机放进来是因为它属于同一个状态机的 NotMoving 分支，不是独立系统；
索道（ZipLine）、UI 立绘、Gal 演出、战斗类都不进来，那些各有自己的状态机。

用 AssetTools.rename_loaded_asset 而不是文件系统移动：前者会修正所有引用者
（ABP_Pyrios 的 AnimSet、BlendSpace 的样本引用），文件系统移动只会留下一堆红引用。
"""

import unreal

SRC_FOLDER = "/Game/Characters/Player/Pyrios/Animation"
DST_FOLDER = SRC_FOLDER + "/Movement"
PREFIX = "Avatar_Male_Size03_Pyrois_Ani_"

# locomotion 状态机直接引用的
STATE_MACHINE = [
    "Idle_Loop",        # NotMoving
    "Walk_Start",       # EnterMove
    "Walk_Loop",        # WalkRun BlendSpace 样本
    "Run_Loop",         # WalkRun BlendSpace 样本
    "Walk_Start_End",   # Stop / StopValue 0
    "Walk_End",         # Stop / StopValue 1
    "Run_End",          # Stop / StopValue 2
    "TurnBack",         # TurnBack
]

# 同属站立待机域，当前状态机还没接，但归类上属于移动表现
IDLE_VARIANTS = [
    "Idle_AFK",
    "Idle_AFK_Loop",
    "MC_Stand_Idle01_Loop",
    "MC_Stand_Think_Loop",
]

# 非 AnimSequence 的移动资产
OTHER_ASSETS = [
    "BS_Pyrios_WalkRun",
]


def move_one(asset_name):
    src = "%s/%s" % (SRC_FOLDER, asset_name)
    dst = "%s/%s" % (DST_FOLDER, asset_name)

    if not unreal.EditorAssetLibrary.does_asset_exist(src):
        if unreal.EditorAssetLibrary.does_asset_exist(dst):
            return "already", asset_name
        return "missing", asset_name

    ok = unreal.EditorAssetLibrary.rename_asset(src, dst)
    return ("moved" if ok else "failed"), asset_name


def run():
    if not unreal.EditorAssetLibrary.does_directory_exist(DST_FOLDER):
        unreal.EditorAssetLibrary.make_directory(DST_FOLDER)
        unreal.log("[Move] 创建目录 %s" % DST_FOLDER)

    targets = [PREFIX + n for n in STATE_MACHINE + IDLE_VARIANTS] + OTHER_ASSETS

    result = {"moved": [], "already": [], "missing": [], "failed": []}
    for name in targets:
        status, asset = move_one(name)
        result[status].append(asset)
        if status == "failed":
            unreal.log_error("[Move] 移动失败: %s" % asset)

    unreal.log("=" * 92)
    unreal.log("[Move] 目标 %d 个：移动 %d，已在目标位置 %d，未找到 %d，失败 %d"
               % (len(targets), len(result["moved"]), len(result["already"]),
                  len(result["missing"]), len(result["failed"])))
    for key in ("moved", "already", "missing", "failed"):
        for name in result[key]:
            unreal.log("        %-10s %s" % (key, name))

    # 保存被改名的资产以及所有引用者（AnimSet 的软引用需要落盘）
    unreal.EditorAssetLibrary.save_directory(SRC_FOLDER, only_if_is_dirty=True, recursive=True)
    try:
        unreal.EditorAssetLibrary.save_asset("/Game/BP/Anim/ABP_Pyrios", only_if_is_dirty=False)
    except Exception as exc:
        unreal.log_warning("[Move] 保存 ABP_Pyrios 失败: %s" % exc)

    # 回读 ABP 的 AnimSet，确认引用已跟着改名走
    abp = unreal.load_asset("/Game/BP/Anim/ABP_Pyrios")
    if abp:
        cdo = unreal.get_default_object(abp.generated_class())
        anim_set = cdo.get_editor_property("anim_set")
        unreal.log("[Move] 回读 AnimSet.sequences：")
        seqs = anim_set.get_editor_property("sequences")
        for k in seqs:
            v = seqs[k]
            unreal.log("        '%s' -> %s" % (k, v.get_path_name() if v else "None"))
        unreal.log("[Move] 回读 AnimSet.blendSpaces：")
        bss = anim_set.get_editor_property("blend_spaces")
        for k in bss:
            v = bss[k]
            unreal.log("        '%s' -> %s" % (k, v.get_path_name() if v else "None"))

    unreal.log("[Move] done.")


run()
