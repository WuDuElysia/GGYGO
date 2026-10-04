"""Preflight legacy BP render configuration; --apply is an explicit asset write.

Requires the old-DLL baseline and a cold start using the new DLL. Does not rebuild
materials or save unrelated packages. A second run with matching values is a no-op.
Run default mode again after a cold reload to verify persistence.
Preflight writes only to an unregistered transient probe, never the target BP/CDO.
After any target write failure, discard only the unsaved migration edits and cold
reload before retrying; never save a partially migrated Blueprint or use SaveAll.
"""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import unreal

ROOT = Path(unreal.Paths.project_dir()).resolve()
DEFAULT_BASELINE = ROOT / "Saved/Codex/character_render_legacy_baseline.json"
CONFIG = ROOT / "AAADocs/Assets/Pyrios/Rendering/Pyrios_Render_Migration.json"


def object_path(obj):
    return obj.get_path_name() if obj else None


def comparable(v):
    if isinstance(v, unreal.LinearColor):
        return [v.r, v.g, v.b, v.a]
    return object_path(v) if isinstance(v, unreal.Object) else v


def matches(actual, expected):
    if isinstance(expected, list):
        return isinstance(actual, list) and len(actual) == len(expected) and all(matches(a, b) for a, b in zip(actual, expected))
    if isinstance(expected, (int, float)) and not isinstance(expected, bool):
        return isinstance(actual, (int, float)) and abs(actual - expected) < 1e-5
    return actual == expected


def slots(component):
    return {str(s.get_editor_property("slot_name")): object_path(s.get_editor_property("material"))
            for s in component.get_editor_property("MaterialSlots")}


def validate_write_contract(values):
    """Exercise the loaded DLL's setters without touching an asset or its CDO."""
    probe = unreal.new_object(unreal.GGYGOPyriosRenderComponent, outer=unreal.get_transient_package())
    for name, value in values.items():
        try:
            probe.set_editor_property(name, value)
            actual = probe.get_editor_property(name)
            if name == "MaterialSlots":
                expected = {str(s.get_editor_property("slot_name")): object_path(s.get_editor_property("material"))
                            for s in value}
                valid = slots(probe) == expected
            else:
                valid = matches(comparable(actual), comparable(value))
            if not valid:
                raise RuntimeError("Setter readback mismatch")
        except Exception as exc:
            raise RuntimeError("Migration write contract failed for " + name
                               + "; cold-start the corrected DLL before retrying. Target unchanged.") from exc


def run(baseline_path=DEFAULT_BASELINE, apply=False):
    if not hasattr(unreal, "GGYGOCharacterRenderComponent"):
        raise RuntimeError("Cold-start the new DLL first; the editor still has the old reflected layout")
    baseline = json.loads(Path(baseline_path).read_text(encoding="utf-8"))
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if baseline.get("schema") != 1 or not baseline.get("complete") or baseline.get("errors"):
        raise RuntimeError("A complete old-DLL baseline is required")
    path = config["blueprint"]
    entries = [b for b in baseline["blueprints"] if b["asset"] == path]
    if len(entries) != 1 or len(entries[0]["components"]) != 1:
        raise RuntimeError("Expected one audited Blueprint component; resolve additional templates explicitly")
    unknown = [b["asset"] for b in baseline["blueprints"] if b["asset"] != path]
    if unknown:
        raise RuntimeError("Unmapped legacy users require their own migration plan: " + str(unknown))
    entry = entries[0]
    old = entry["components"][0]["properties"]
    bp = unreal.EditorAssetLibrary.load_asset(path)
    if not isinstance(bp, unreal.Blueprint):
        raise RuntimeError("Missing target Blueprint")
    cdo = unreal.get_default_object(bp.generated_class())
    components = [c for c in cdo.get_components_by_class(unreal.GGYGOCharacterRenderComponent)
                  if c.get_name() == config["component_name"]]
    if len(components) != 1:
        raise RuntimeError("Inherited component identity missing or duplicated")
    component = components[0]
    if component.get_class().get_path_name() != entry["components"][0]["class"]:
        raise RuntimeError("Legacy serialized component class changed unexpectedly")
    if component.get_path_name() != entry["components"][0]["object"]:
        raise RuntimeError("Legacy serialized component object path changed unexpectedly")
    dirty = {p.get_path_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()}
    if path in dirty:
        raise RuntimeError("Target Blueprint is dirty; refusing to include unrelated changes")
    mesh = cdo.get_editor_property("mesh").get_editor_property("skeletal_mesh_asset")
    if not mesh:
        raise RuntimeError("Missing character mesh")
    names = [str(s.get_editor_property("material_slot_name")) for s in mesh.get_editor_property("materials")]
    desired_slots = {s["slot_name"]: s["material"] for s in old["material_slots"] if s["material"]}
    if old["bAutoConfigurePyrios"]:
        for name, material in config["material_slots"].items():
            desired_slots.setdefault(name, material)
    loaded_slots = {}
    for name, material in desired_slots.items():
        if names.count(name) != 1:
            raise RuntimeError("Mesh slot missing/ambiguous: " + name)
        loaded = unreal.EditorAssetLibrary.load_asset(material)
        if not isinstance(loaded, unreal.MaterialInterface):
            raise RuntimeError("Missing material: " + material)
        loaded_slots[name] = loaded
    desired = {k: v for k, v in old.items() if k not in ("material_slots", "bAutoConfigurePyrios")}
    desired["OutlineMaterial"] = old["OutlineMaterial"] or config["outline_material"]
    loaded_outline = unreal.EditorAssetLibrary.load_asset(desired["OutlineMaterial"])
    if not isinstance(loaded_outline, unreal.MaterialInterface):
        raise RuntimeError("Missing outline material")
    desired["OutlineMaterial"] = object_path(loaded_outline)
    current = {k: comparable(component.get_editor_property(k)) for k in desired}
    expected_slots = {k: object_path(v) for k, v in loaded_slots.items()}
    already = (all(matches(current[k], v) for k, v in desired.items()) and slots(component) == expected_slots
               and not component.get_editor_property("bAutoConfigurePyrios")
               and component.get_editor_property("auto_activate"))
    if already:
        unreal.log("PYRIOS_RENDER_MIGRATION_ALREADY_CONFIGURED " + path)
        return
    file = ROOT / "Content" / (path[len("/Game/"):] + ".uasset")
    digest = hashlib.sha256(file.read_bytes()).hexdigest()
    if digest != entry["sha256"]:
        raise RuntimeError("Saved Blueprint changed since baseline; audit changes before migration")
    # Native defaults moved to a generic base. Only a baseline-inherited value may
    # legitimately change to a new native default without an authored BP change.
    native = unreal.get_default_object(unreal.GGYGOCharacterRenderComponent.static_class())
    old_native = baseline["native_default"]["properties"]
    for k, v in current.items():
        baseline_value = old[k]
        inherited_drift = matches(baseline_value, old_native[k]) and matches(v, comparable(native.get_editor_property(k)))
        if not matches(v, baseline_value) and not inherited_drift:
            raise RuntimeError("Unexpected loaded property change: " + k)
    if slots(component) != {s["slot_name"]: s["material"] for s in old["material_slots"]}:
        raise RuntimeError("Loaded material bindings differ from baseline")
    write_values = dict(desired)
    write_values["OutlineMaterial"] = loaded_outline
    write_values["KeyLight"] = unreal.load_object(None, desired["KeyLight"]) if desired["KeyLight"] else None
    if desired["KeyLight"] and write_values["KeyLight"] is None:
        raise RuntimeError("Missing authored KeyLight; refusing to replace it with auto selection")
    write_values["KeyLightTint"] = unreal.LinearColor(*desired["KeyLightTint"])
    material_slots = []
    for name, material in loaded_slots.items():
        s = unreal.GGYGOCharacterRenderSlot()
        s.set_editor_property("slot_name", name)
        s.set_editor_property("material", material)
        material_slots.append(s)
    write_values.update(MaterialSlots=material_slots, bAutoConfigurePyrios=False, auto_activate=True)
    validate_write_contract(write_values)
    unreal.log("PYRIOS_RENDER_MIGRATION_PREFLIGHT " + json.dumps({"asset": path, "properties": desired, "slots": expected_slots}))
    if not apply:
        return
    backup = ROOT / "Saved/Codex/RenderMigrationBackup" / (digest + "_BP_PC_Pyrios.uasset")
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(file, backup)
    if hashlib.sha256(backup.read_bytes()).hexdigest() != digest:
        raise RuntimeError("Backup hash mismatch")
    bp.modify()
    component.modify()
    for k, v in write_values.items():
        component.set_editor_property(k, v)
    unreal.BlueprintEditorLibrary.compile_blueprint(bp)
    if "ERROR" in str(bp.get_editor_property("status")).upper():
        raise RuntimeError("Blueprint compile failed; target remains dirty and was not saved")
    fresh = unreal.get_default_object(bp.generated_class()).get_editor_property("StylizedRenderComponent")
    if (slots(fresh) != expected_slots
            or any(not matches(comparable(fresh.get_editor_property(k)), v) for k, v in desired.items())
            or fresh.get_editor_property("bAutoConfigurePyrios")
            or not fresh.get_editor_property("auto_activate")):
        raise RuntimeError("Compile did not preserve component defaults; target was not saved")
    if not unreal.EditorAssetLibrary.save_loaded_asset(bp):
        raise RuntimeError("Migration save failed; do not report completion")
    unreal.log("PYRIOS_RENDER_MIGRATION_SAVED_RELOAD_REQUIRED " + path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(args.baseline, args.apply)
