"""只读盘点 Pyrios 动作、Niagara、音频及移动表现配置。

在独立 UE Editor 使用 -ExecutePythonScript 执行，输出目录由
GGYGO_ACTION_FX_OUT 指定。inventory.json 供接线盘点及网格来源检查消费；
T3D 保留 Montage 通知和 GA 配置的原生字段。不写入或保存生产资产。
"""
import json
import os
import traceback
from pathlib import Path

import unreal as ue

OUT = Path(os.environ["GGYGO_ACTION_FX_OUT"])
ROOT = "/Game/Characters/Player/Pyrios"
OUT.mkdir(parents=True, exist_ok=True)
report = {"abilities": {}, "montages": {}, "systems": {}, "audio": {},
          "hit_cues": {}, "locomotion_components": [], "meshes": {}, "errors": []}


def path(obj):
    return obj.get_path_name() if obj else None


def exported(obj, label):
    filename = OUT / (label + ".t3d")
    task = ue.AssetExportTask()
    for key, value in {"object": obj, "exporter": ue.ObjectExporterT3D(),
                       "filename": str(filename), "automated": True,
                       "prompt": False, "replace_identical": True}.items():
        task.set_editor_property(key, value)
    if not ue.Exporter.run_asset_export_task(task):
        raise RuntimeError("T3D 导出失败：" + path(obj))
    return str(filename)


def inspect(label, operation):
    try:
        return operation()
    except Exception:
        error = {"asset": label, "error": traceback.format_exc()}
        report["errors"].append(error)
        ue.log_warning("动作 FX 盘点失败：" + label + "\n" + error["error"])
        return None


def montage(asset):
    name = path(asset)
    if name in report["montages"]:
        return
    row = {"length": asset.get_play_length(), "rate_scale": asset.get_editor_property("rate_scale"),
           "sections": [str(asset.get_section_name(i)) for i in range(asset.get_num_sections())],
           "notifies": [], "native": exported(asset, asset.get_name())}
    report["montages"][name] = row
    for event in ue.AnimationLibrary.get_animation_notify_events(asset):
        item = {"time": ue.AnimationLibrary.get_anim_notify_event_trigger_time(event),
                "duration": ue.AnimationLibrary.get_anim_notify_event_duration(event),
                "native": event.export_text()}
        notify = event.get_editor_property("notify")
        if isinstance(notify, ue.AnimNotify_PlaySound):
            item["sound"] = path(notify.get_editor_property("sound"))
            item["follow"] = notify.get_editor_property("follow")
            item["attach_name"] = str(notify.get_editor_property("attach_name"))
        row["notifies"].append(item)


def ability(bp):
    cdo = ue.get_default_object(bp.generated_class())
    if not isinstance(cdo, ue.GGYGOPlayerComboAbility):
        return
    row = {"native": exported(cdo, bp.get_name()), "steps": []}
    report["abilities"][path(bp)] = row
    for step in cdo.get_editor_property("combo_steps"):
        fx = step.get_editor_property("fx")
        anim = step.get_editor_property("montage")
        item = {"montage": path(anim), "native": step.export_text(), "fx": fx.export_text(),
                "systems": [path(u.get_editor_property("system")) for u in fx.get_editor_property("system_units")]}
        single = fx.get_editor_property("system")
        if single:
            item["systems"].append(path(single))
        row["steps"].append(item)
        inspect(path(anim), lambda: montage(anim))


registry = ue.AssetRegistryHelpers.get_asset_registry()
registry.wait_for_completion()
deps = ue.AssetRegistryDependencyOptions(include_soft_package_references=True,
                                         include_hard_package_references=True,
                                         include_searchable_names=False,
                                         include_soft_management_references=False,
                                         include_hard_management_references=False)
mesh_packages = set()
for data in registry.get_assets_by_path(ROOT, recursive=True):
    package = str(data.package_name)
    cls = str(data.asset_class_path.asset_name)
    if cls == "Blueprint" and "/Abilities/" in package:
        inspect(package, lambda: ability(data.get_asset()))
    elif cls == "NiagaraSystem" and "/FX/" in package:
        references = sorted(str(d) for d in registry.get_dependencies(data.package_name, deps))
        report["systems"][package] = {"dependencies": references,
                                      "referencers": sorted(str(d) for d in registry.get_referencers(data.package_name, deps))}
        mesh_packages.update(d for d in references if "/Meshes/" in d)
    elif cls in ("SoundWave", "SoundCue") and "/Audio/" in package:
        def sound():
            asset = data.get_asset()
            row = {"class": cls, "duration": asset.get_editor_property("duration"),
                   "referencers": sorted(str(d) for d in registry.get_referencers(data.package_name, deps))}
            if cls == "SoundWave":
                row["source"] = list(asset.get_editor_property("asset_import_data").extract_filenames())
            report["audio"][package] = row
        inspect(package, sound)

for data in registry.get_assets_by_path("/Game/GameplayCues", recursive=True):
    if str(data.asset_name).startswith("GCN_Pyrios_Hit_"):
        def cue():
            bp = data.get_asset()
            cdo = ue.get_default_object(bp.generated_class())
            report["hit_cues"][str(data.package_name)] = {
                "native": exported(cdo, bp.get_name()),
                "default_effect": cdo.get_editor_property("default_effect").export_text()}
        inspect(str(data.package_name), cue)

for package in sorted(mesh_packages):
    def mesh():
        asset = ue.load_asset(package)
        report["meshes"][package] = {"sources": list(asset.get_editor_property("asset_import_data").extract_filenames()),
                                    "native": exported(asset, asset.get_name())}
    inspect(package, mesh)

bp = ue.load_asset("/Game/BP/Character/Player/BP_PC_Pyrios")
inspect(path(bp), lambda: exported(ue.get_default_object(bp.generated_class()), "BP_PC_Pyrios_CDO"))
for component in ue.ObjectIterator(ue.GGYGOLocomotionFXComponent):
    if "Pyrios" in component.get_path_name():
        report["locomotion_components"].append({"object": path(component),
                                               "cues": [c.export_text() for c in component.get_editor_property("cues")]})

report["dirty_packages"] = [path(p) for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()]
(OUT / "inventory.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
ue.log("动作 FX 盘点完成：" + str(OUT / "inventory.json") + "; errors=" + str(len(report["errors"])))
