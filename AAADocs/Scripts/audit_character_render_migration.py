"""Read saved render templates using the currently loaded DLL; never save assets.

Run with the OLD DLL before changing the reflected hierarchy. Output is evidence,
not permission to migrate. Failed/partial audits must not unlock that change.
"""
import hashlib
import json
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
OUTPUT = ROOT / "Saved/Codex/character_render_legacy_baseline.json"
FIELDS = (
    "bAutoConfigurePyrios", "LightingUpdateInterval",
    "ReferenceKeyLightIntensity", "KeyLightIntensityResponse",
    "KeyLightOutputScale", "MaxKeyLightStrength", "KeyLightTint",
    "OccludedKeyLightVisibility", "bTraceKeyLightOcclusion",
    "bEnableOutline", "OutlineWidth", "OutlineMaterial", "KeyLight",
)


def value(v):
    if v is None or isinstance(v, (str, bool, int, float)):
        return v
    if isinstance(v, unreal.LinearColor):
        return [v.r, v.g, v.b, v.a]
    if isinstance(v, unreal.Object):
        return v.get_path_name()
    raise TypeError("Unsupported baseline value: " + str(type(v)))


def snapshot(component):
    result = {"object": component.get_path_name(), "class": component.get_class().get_path_name()}
    result["properties"] = {name: value(component.get_editor_property(name)) for name in FIELDS}
    result["properties"]["material_slots"] = [
        {"slot_name": str(s.get_editor_property("slot_name")),
         "material": value(s.get_editor_property("material"))}
        for s in component.get_editor_property("material_slots")]
    return result


def main():
    if OUTPUT.exists():
        raise RuntimeError("Refusing to replace baseline: " + str(OUTPUT))
    dirty_before = sorted(p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    registry = unreal.AssetRegistryHelpers.get_asset_registry()
    registry.search_all_assets(True)
    assets = registry.get_assets_by_class(unreal.TopLevelAssetPath("/Script/Engine", "Blueprint"), True)
    report = {"schema": 1, "complete": False, "blueprints": [], "errors": [],
              "native_class": "/Script/GGYGO.GGYGOPyriosRenderComponent", "dirty_before": dirty_before}
    report["native_default"] = snapshot(unreal.get_default_object(unreal.GGYGOPyriosRenderComponent.static_class()))
    subsystem = unreal.get_engine_subsystem(unreal.SubobjectDataSubsystem)
    library = unreal.SubobjectDataBlueprintFunctionLibrary
    for data in sorted(assets, key=lambda a: str(a.package_name)):
        package = str(data.package_name)
        if not package.startswith("/Game/"):
            continue
        try:
            bp = data.get_asset()
            if not isinstance(bp, unreal.Blueprint) or not bp.generated_class():
                continue
            cdo = unreal.get_default_object(bp.generated_class())
            components = {}
            if isinstance(cdo, unreal.GGYGOPyriosRenderComponent):
                components[cdo.get_path_name()] = snapshot(cdo)
            elif not isinstance(cdo, unreal.Actor):
                continue
            if isinstance(cdo, unreal.Actor):
                for comp in cdo.get_components_by_class(unreal.GGYGOPyriosRenderComponent):
                    components[comp.get_path_name()] = snapshot(comp)
            # Includes inherited templates and components authored through SCS.
            for handle in subsystem.k2_gather_subobject_data_for_blueprint(bp):
                subdata = library.get_data(handle)
                # GetObjectForBlueprint can CREATE inherited SCS overrides; a
                # read-only audit must inspect the existing object instead.
                obj = library.get_object(subdata)
                if isinstance(obj, unreal.GGYGOPyriosRenderComponent):
                    components[obj.get_path_name()] = snapshot(obj)
            if not components:
                continue
            file = ROOT / "Content" / (package[len("/Game/"):] + ".uasset")
            report["blueprints"].append({"asset": package, "class": bp.generated_class().get_path_name(),
                "cdo": cdo.get_path_name(), "sha256": hashlib.sha256(file.read_bytes()).hexdigest(),
                "components": list(components.values()),
                "referencers": sorted(str(p) for p in registry.get_referencers(
                    package, unreal.AssetRegistryDependencyOptions()))})
        except Exception as error:
            report["errors"].append({"asset": package, "error": str(error)})
    expected = "/Game/BP/Character/Player/BP_PC_Pyrios"
    if not any(b["asset"] == expected for b in report["blueprints"]):
        report["errors"].append({"asset": expected, "error": "Required legacy component not discovered"})
    report["dirty_after"] = sorted(p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages())
    for entry in report["blueprints"]:
        if entry["asset"] in report["dirty_before"] or entry["asset"] in report["dirty_after"]:
            report["errors"].append({"asset": entry["asset"], "error": "Dirty blueprint cannot be a saved-asset baseline"})
    report["complete"] = not report["errors"]
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    unreal.log("CHARACTER_RENDER_LEGACY_BASELINE " + str(OUTPUT))
    if not report["complete"]:
        raise RuntimeError("Baseline incomplete; inspect errors before changing reflection")


if __name__ == "__main__":
    main()
