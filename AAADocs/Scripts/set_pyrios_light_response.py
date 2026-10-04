"""Run with UnrealEditor-Cmd -run=pythonscript -script=<this file>.

把 BP_PC_Pyrios 的 StylizedRenderComponent 改成“只取 UE 主光方向与颜色，不随 UE 光强缩放”：
  KeyLightIntensityResponse = 0  -> 场景光强比的幂次为 0，强度恒为 KeyLightOutputScale
  KeyLightOutputScale       = 1  -> 与 M_Pyrois_Toon 的编辑器预览 SceneLightStrength=1 一致
M_Pyrois_Toon 移植的是原游戏的角色光照，原 Shader 的 _AvatarMainLightColor 是角色专用主光，
不随场景灯的物理强度变化；继续按 UE 灯光强度缩放会把 UE 的光照数值叠回角色上。
已是目标值时不写入；写入前备份原 .uasset 并记录哈希；编译后回读核对再保存。
"""
import hashlib
import json
import shutil
from pathlib import Path
import unreal

BP_PATH = "/Game/BP/Character/Player/BP_PC_Pyrios"
COMPONENT = "StylizedRenderComponent"
TARGET = {"KeyLightIntensityResponse": 0.0, "KeyLightOutputScale": 1.0}
ROOT = Path(__file__).resolve().parents[2]
BACKUP_DIR = ROOT / "Saved/RenderLightResponseBackup"


def main():
    bp = unreal.EditorAssetLibrary.load_asset(BP_PATH)
    if not isinstance(bp, unreal.Blueprint):
        raise RuntimeError("Missing Blueprint " + BP_PATH)
    dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if BP_PATH in dirty:
        raise RuntimeError("Blueprint has unsaved edits; refusing to save them along with this change")
    component = unreal.get_default_object(bp.generated_class()).get_editor_property(COMPONENT)
    if not isinstance(component, unreal.GGYGOCharacterRenderComponent):
        raise RuntimeError("Missing render component on " + BP_PATH)
    before = {k: component.get_editor_property(k) for k in TARGET}
    if all(abs(before[k] - v) < 1e-6 for k, v in TARGET.items()):
        unreal.log("PYRIOS_LIGHT_RESPONSE_ALREADY " + json.dumps(before))
        return
    file = ROOT / "Content" / (BP_PATH[len("/Game/"):] + ".uasset")
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    backup = BACKUP_DIR / (digest[:16] + "_BP_PC_Pyrios.uasset")
    if not backup.exists():
        shutil.copy2(file, backup)
    bp.modify()
    component.modify()
    for k, v in TARGET.items():
        component.set_editor_property(k, v)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    if "ERROR" in str(bp.get_editor_property("status")).upper():
        raise RuntimeError("Blueprint compile failed; not saved")
    fresh = unreal.get_default_object(bp.generated_class()).get_editor_property(COMPONENT)
    after = {k: fresh.get_editor_property(k) for k in TARGET}
    if any(abs(after[k] - v) > 1e-6 for k, v in TARGET.items()):
        raise RuntimeError("Compiled defaults differ from target: " + json.dumps(after))
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp):
        raise RuntimeError("Blueprint save failed")
    unreal.log("PYRIOS_LIGHT_RESPONSE_SAVED " + json.dumps(
        {"before": before, "after": after, "backup": str(backup), "old_sha256": digest}))


if __name__ == "__main__":
    main()
