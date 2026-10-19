"""Coordinator-authorized fresh Editor readback; no PIE, compilation or asset saves."""
import argparse
import hashlib
import importlib.util
import json
import os
import traceback
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
PLAYER = "/Game/Characters/Player/Pyrios"
DODGE = "/Game/Characters/Shared/Abilities/GA_Dodge"
PAWN = PLAYER + "/DA/DA_Pawn_Pyrios"
INPUT = PLAYER + "/DA/DA_InputConfig_Default"
SETS = [PLAYER + "/DA/DA_AbilitySet_Common", PLAYER + "/DA/DA_AbilitySet_Pyrios"]
IMC = "/Game/Input/Mappings/IMC_Default"
MONTAGES = [PLAYER + "/Animation/Attack/AM_Pyrios_Attack_Normal_" + n for n in ("02", "03")]
SEQUENCES = [PLAYER + "/Animation/Avatar_Male_Size03_Pyrois_Ani_" + n for n in (
    "Evade_Front_01", "Evade_Back_01", "Attack_Normal_02", "Attack_Normal_02_End",
    "Attack_Normal_03", "Attack_Normal_03_End")]
COMBO = PLAYER + "/Abilities/GA_Pyrios_Attack_Combo"
AUTOSAVE = PROJECT / "Saved/Autosaves/Game/Characters/Shared/Abilities/GA_Dodge_Auto2.uasset"


def run(output):
    import unreal as ue
    output = (PROJECT / output).resolve()
    if not output.is_relative_to((PROJECT / "Saved").resolve()) or output.exists():
        raise RuntimeError("Readback output must be a fresh directory inside Saved: " + str(output))
    output.mkdir(parents=True)
    report = {"schema": "PyriosExistingActionsReadOnly/v1", "pid": os.getpid(), "success": False,
              "meaning": "saved asset/configuration readback; no runtime ability/grant assertion",
              "assets": {}, "reads": {}, "errors": [], "protected_before": {},
              "dirty_before": None, "dirty_after": None}
    loaded = {}

    def protect_file(path):
        path = path.resolve()
        key = str(path)
        if key not in report["protected_before"]:
            if not path.is_file():
                raise RuntimeError("Required saved package missing: " + key)
            report["protected_before"][key] = hashlib.sha256(path.read_bytes()).hexdigest().upper()

    def protect_package(package):
        if not package.startswith("/Game/"):
            raise RuntimeError("Unexpected package outside authorized Game content: " + package)
        protect_file(PROJECT / "Content" / (package[6:] + ".uasset"))

    def dirty():
        return {"content": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()),
                "maps": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages())}

    def capture(label, operation):
        try:
            value = operation()
            report["reads"][label] = {"available": True, "value": value}
            return value
        except Exception as error:
            detail = {"operation": label, "error": str(error), "traceback": traceback.format_exc()}
            report["errors"].append(detail)
            report["reads"][label] = {"available": False, "error": str(error)}
            ue.log_error("[Combat.ExistingActions.ReadOnly] " + label + ": " + str(error))

    def load(package):
        if package not in loaded:
            protect_package(package)
            asset = ue.EditorAssetLibrary.load_asset(package)
            if asset is None:
                raise RuntimeError("Native load returned no asset: " + package)
            loaded[package] = asset
            report["assets"][package] = {"object": asset.get_path_name(), "class": asset.get_class().get_path_name()}
        return loaded[package]

    def object_path(value):
        return None if value is None else value.get_path_name()

    def export_native(obj):
        filename = output / (str(len(list(output.glob("*.t3d")))).zfill(2) + "_" + obj.get_name() + ".t3d")
        task = ue.AssetExportTask()
        for name, value in {"object": obj, "exporter": ue.ObjectExporterT3D(), "filename": str(filename),
                            "automated": True, "prompt": False, "replace_identical": False}.items():
            task.set_editor_property(name, value)
        if not ue.Exporter.run_asset_export_task(task) or not filename.is_file():
            raise RuntimeError("Native ObjectExporterT3D failed: " + obj.get_path_name())
        return str(filename)

    def blueprint(package):
        bp = load(package)
        generated = bp.generated_class()
        if generated is None:
            raise RuntimeError("Blueprint has no generated class: " + package)
        cdo = ue.get_default_object(generated)
        if cdo is None:
            raise RuntimeError("Blueprint has no native CDO: " + package)
        if isinstance(cdo, ue.GGYGOGameplayAbility):
            capture("project_ability_policy:" + package, lambda: {
                "activation_policy": str(cdo.get_editor_property("activation_policy")),
                "avatar_exit_policy": str(cdo.get_editor_property("avatar_exit_policy")),
                "group_tag": cdo.get_editor_property("group_tag").export_text(),
                "activation_priority": int(cdo.get_editor_property("activation_priority")),
                "self_policy": str(cdo.get_editor_property("self_policy"))})
        return {"parent": bp.get_blueprint_parent_class().get_path_name(), "status": str(bp.get_editor_property("status")),
                "generated_class": generated.get_path_name(), "cdo": cdo.get_path_name(),
                "blueprint_t3d": export_native(bp), "cdo_t3d": export_native(cdo)}

    def ability_set(package):
        asset = load(package)
        return {"abilities": [row.export_text() for row in asset.get_editor_property("granted_gameplay_abilities")],
                "effects": [row.export_text() for row in asset.get_editor_property("granted_gameplay_effects")],
                "native_t3d": export_native(asset)}

    def input_config(package):
        asset = load(package)
        return {"native_actions": [row.export_text() for row in asset.get_editor_property("native_input_actions")],
                "ability_actions": [row.export_text() for row in asset.get_editor_property("ability_input_actions")],
                "native_t3d": export_native(asset)}

    def mapping(package):
        asset = load(package)
        return {"default_key_mappings": asset.get_editor_property("default_key_mappings").export_text(),
                "profile_overrides": {str(name): value.export_text() for name, value in
                                      asset.get_editor_property("mapping_profile_overrides").items()},
                "native_t3d": export_native(asset)}

    def pawn_references():
        data = load(PAWN)
        pawn_class = data.get_editor_property("pawn_class")
        result = {"pawn_class": object_path(pawn_class), "input_config": object_path(data.get_editor_property("input_config")),
                  "ability_sets": [object_path(a) for a in data.get_editor_property("ability_sets")],
                  "group_config": object_path(data.get_editor_property("ability_group_config")),
                  "tag_relationship_mapping": object_path(data.get_editor_property("tag_relationship_mapping")),
                  "movement_set": object_path(data.get_editor_property("movement_set")), "native_t3d": export_native(data)}
        for asset in data.get_editor_property("ability_sets"):
            if asset is not None:
                package = asset.get_path_name().split(".")[0]
                capture("actual_ability_set:" + package, lambda p=package: ability_set(p))
        config = data.get_editor_property("input_config")
        if config is not None:
            package = config.get_path_name().split(".")[0]
            capture("actual_input_config:" + package, lambda: input_config(package))
        if pawn_class is None:
            raise RuntimeError("Actual PawnData PawnClass is null; no substituted Pawn")
        if pawn_class.get_path_name().startswith("/Game/"):
            result["pawn_blueprint"] = blueprint(pawn_class.get_path_name().split(".")[0])
        pawn_cdo = ue.get_default_object(pawn_class)
        hero = pawn_cdo.get_editor_property("hero_component")
        if hero is None:
            raise RuntimeError("Actual Pawn CDO HeroComponent is null; IMC application remains unknown")
        result["hero_template"] = hero.get_path_name()
        result["hero_template_t3d"] = export_native(hero)
        result["mapping_priority"] = int(hero.get_editor_property("input_mapping_priority"))
        result["default_input_mappings"] = [object_path(m) for m in hero.get_editor_property("default_input_mappings")]
        for context in hero.get_editor_property("default_input_mappings"):
            if context is not None:
                package = context.get_path_name().split(".")[0]
                capture("actual_imc:" + package, lambda p=package: mapping(p))
        return result

    def montage(package):
        asset = load(package)
        tracks = []
        for track in asset.get_editor_property("slot_anim_tracks"):
            tracks.append({"slot": str(track.get_editor_property("slot_name")), "native_export": track.export_text(),
                           "segments": [segment.export_text() for segment in
                                        track.get_editor_property("anim_track").get_editor_property("anim_segments")]})
        events = [{"trigger_time": float(ue.AnimationLibrary.get_anim_notify_event_trigger_time(event)),
                   "duration": float(ue.AnimationLibrary.get_anim_notify_event_duration(event)),
                   "event_native_export": event.export_text()} for event in ue.AnimationLibrary.get_animation_notify_events(asset)]
        return {"native_t3d": export_native(asset), "tracks": tracks, "notify_events": events}

    def sequence(package):
        asset = load(package)
        names = ue.AnimationLibrary.get_animation_curve_names(asset, ue.RawCurveTrackTypes.RCT_FLOAT)
        result = ue.GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot(asset, list(names))
        if not result.succeeded:
            report["errors"].append({"operation": "curve_snapshot:" + package, "error": str(result.error),
                                     "native_result_succeeded": False})
            ue.log_error("[Combat.ExistingActions.ReadOnly] curve_snapshot:" + package + ": " + str(result.error))
        curves = []
        for curve in result.curves:
            keys = []
            for key in curve.keys:
                values = {field: float(getattr(key, field)) for field in (
                    "time", "value", "arrive_tangent", "leave_tangent", "arrive_tangent_weight", "leave_tangent_weight")}
                values.update({field: int(getattr(key, field)) for field in (
                    "interp_mode", "tangent_mode", "tangent_weight_mode")})
                keys.append(values)
            curves.append({"name": str(curve.name), "flags": int(curve.flags),
                           "default_value": float(curve.default_value),
                           "pre_infinity_extrap": int(curve.pre_infinity_extrap),
                           "post_infinity_extrap": int(curve.post_infinity_extrap), "keys": keys})
        return {"curve_names": [str(name) for name in names], "succeeded": bool(result.succeeded),
                "error": str(result.error), "duration_seconds": float(result.duration_seconds),
                "curves": curves, "full_native_snapshot": result.export_text(), "native_t3d": export_native(asset)}

    try:
        report["dirty_before"] = capture("dirty_before", dirty)
        if report["dirty_before"] is None:
            raise RuntimeError("Native dirty-package read unavailable; read-only baseline is unknown")
        if any(report["dirty_before"].values()):
            raise RuntimeError("Fresh read-only host already has dirty packages")
        protect_package(COMBO)
        if AUTOSAVE.is_file():
            protect_file(AUTOSAVE)
        capture("dodge_blueprint", lambda: blueprint(DODGE))
        spec = importlib.util.spec_from_file_location("_combat_existing_fx_read", PROJECT / "AAADocs/Scripts/wire_pyrios_combo_fx.py")
        helper = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(helper)
        capture("dodge_graphs", lambda: helper.graph_snapshot(ue, load(DODGE)))
        capture("pawn_references", pawn_references)
        for package in SETS:
            capture("candidate_ability_set:" + package, lambda p=package: ability_set(p))
        capture("candidate_input_config", lambda: input_config(INPUT))
        capture("candidate_imc", lambda: mapping(IMC))
        for package in MONTAGES:
            capture("montage:" + package, lambda p=package: montage(p))
        for package in SEQUENCES:
            capture("sequence:" + package, lambda p=package: sequence(p))
    except Exception as error:
        report["errors"].append({"operation": "audit", "error": str(error), "traceback": traceback.format_exc()})
        ue.log_error("[Combat.ExistingActions.ReadOnly] audit: " + str(error))
    finally:
        report["dirty_after"] = capture("dirty_after", dirty)
        report["protected_after"] = {}
        for path in report["protected_before"]:
            after = capture("protected_after:" + path, lambda p=path: hashlib.sha256(Path(p).read_bytes()).hexdigest().upper())
            if after is not None:
                report["protected_after"][path] = after
        report["changed_files"] = [path for path, before in report["protected_before"].items()
                                   if path in report["protected_after"] and report["protected_after"][path] != before]
        report["success"] = (not report["errors"] and not report["changed_files"] and report["dirty_before"] is not None
                             and report["dirty_before"] == report["dirty_after"])
        (output / "readback.json").write_text(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        ue.log("[Combat.ExistingActions.ReadOnly] " + json.dumps({"success": report["success"], "errors": len(report["errors"]),
               "changed_files": report["changed_files"], "output": str(output)}, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True)
    run(parser.parse_args().output)
