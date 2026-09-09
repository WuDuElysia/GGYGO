# -*- coding: utf-8 -*-
"""
run_turnback_yaw_bake.py —— 只转发 Editor 控制台命令。

实际资产复制、RM_Yaw 采样、Bip001 写入和保存由 GGYGOEditor 的
ZZZBakeTurnBackYaw C++ 工具完成；Bone_Root 作为 Actor 正方向参考保持不变；
本脚本不直接操作 AnimSequence。
"""

import unreal

SOURCE = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
          "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack")
DESTINATION = ("/Game/Characters/Player/Pyrios/Animation/Locomotion/"
               "Avatar_Male_Size03_Pyrois_ModelAvatar_Male_Size03_Pyrois_Ani_TurnBack_ProgramRotation_Bip001")
COMMAND = "ZZZBakeTurnBackYaw %s %s" % (SOURCE, DESTINATION)


def run():
    unreal.log("[TurnBackBakeRunner] execute: %s" % COMMAND)
    execute = getattr(unreal, "execute_console_command", None)
    if callable(execute):
        execute(COMMAND)
        return

    system_library = getattr(unreal, "SystemLibrary", None)
    execute = getattr(system_library, "execute_console_command", None) if system_library else None
    if callable(execute):
        execute(None, COMMAND)
        return

    unreal.log_error("[TurnBackBakeRunner] 找不到 execute_console_command Python API")


run()
