"""@file set_pyrios_mesh_bounds_scale.py
@brief 设置 BP_PC_Pyrios 角色 Mesh（CharacterMesh0）的 BoundsScale，只保存该蓝图包。

背景：Pyrios 的 Mesh 包围盒由物理资产计算，物理资产只覆盖躯干，武器、头发、披风和小腿在动作中大幅超出。
VSM 按图元包围盒失效缓存页，超出包围盒的投影不会被重画，旧姿态的阴影残留在地面上（倒下、转身时最明显）。
物理资产和网格是本地导入资产（不入库），所以在入库的蓝图上用原生 BoundsScale 做保守扩张。
倍率依据见 AAADocs/需求文档/refactor_and_squad_switch.md 的"角色受光与阴影"一节。

用法：Editor 内 py "<本文件>" <倍率> "<报告路径>"；报告已存在、PIE 运行中或存在脏包时拒绝。
"""
import json
import sys
import traceback

BLUEPRINT = "/Game/BP/Character/Player/BP_PC_Pyrios"


def run(scale, output):
    import unreal as ue
    report = {"blueprint": BLUEPRINT, "requested": scale, "success": False, "errors": []}
    try:
        editor = ue.get_editor_subsystem(ue.UnrealEditorSubsystem)
        if editor.get_game_world() is not None:
            raise RuntimeError("PIE 正在运行")
        utils = ue.EditorLoadingAndSavingUtils
        dirty = [p.get_path_name() for p in utils.get_dirty_content_packages() + utils.get_dirty_map_packages()]
        if dirty:
            raise RuntimeError("存在脏包，停止且不保存：" + ", ".join(dirty))
        if not (scale > 0):
            raise RuntimeError("BoundsScale 必须为正")
        blueprint = ue.load_asset(BLUEPRINT)
        mesh = ue.get_default_object(blueprint.generated_class()).get_editor_property("mesh")
        report["before"] = float(mesh.get_editor_property("bounds_scale"))
        mesh.set_editor_property("bounds_scale", scale)
        ue.BlueprintEditorLibrary.compile_blueprint(blueprint)
        fresh = ue.get_default_object(blueprint.generated_class()).get_editor_property("mesh")
        report["after"] = float(fresh.get_editor_property("bounds_scale"))
        if abs(report["after"] - scale) > 1e-4:
            raise RuntimeError("编译后读回不符")
        dirty = [p.get_path_name() for p in utils.get_dirty_content_packages() + utils.get_dirty_map_packages()]
        report["dirty_before_save"] = dirty
        if set(dirty) - {BLUEPRINT}:
            raise RuntimeError("出现非目标脏包：" + ", ".join(sorted(set(dirty) - {BLUEPRINT})))
        if not ue.EditorAssetLibrary.save_loaded_asset(blueprint, only_if_is_dirty=False):
            raise RuntimeError("保存失败")
        report["success"] = True
    except Exception as error:
        report["errors"].append({"error": str(error), "traceback": traceback.format_exc()})
    with open(output, "x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2)
    return report


if __name__ == "__main__":
    run(float(sys.argv[1]), sys.argv[2])
