"""Wire only the existing production combo's Normal01 FX defaults.

Run audit, apply, then cold in a fresh full Editor with the new native DLL.
The selected Montage window must already be saved. This tool never edits a
Montage, graph, other step, or Niagara asset and never creates a replacement GA.
"""
import argparse
import hashlib
import json
import math
import os
import shutil
from pathlib import Path

PROJECT = Path(__file__).resolve().parents[2]
GA = "/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo"
PARENT = "/Script/GGYGO.GGYGOPlayerComboAbility"
SYSTEM = "/Game/Characters/Player/Pyrios/FX/Skill/NS_Eff_Pyrois_Attack_Normal_01_01_Trail"
MONTAGE = "/Game/Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_Normal_01"
BEGIN = "Event.Montage.FXWindowBegin"
END = "Event.Montage.FXWindowEnd"
SCHEMA = "PyriosComboNormal01FX/v1"


def require(condition, reason):
    if not condition:
        raise RuntimeError("Combat combo FX: " + reason)


def saved_path(value):
    result = (PROJECT / value).resolve()
    require(result.is_relative_to((PROJECT / "Saved").resolve()), "output/baseline/backup must be inside Saved")
    return result


def disk_file(package):
    require(package.startswith("/Game/"), "unexpected package")
    return PROJECT / "Content" / (package[6:] + ".uasset")


def digest(path):
    require(path.is_file(), "required saved package missing: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dirty(ue):
    return {"content": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()),
            "maps": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages())}


def graph_snapshot(ue, bp):
    result = {}
    for graph in ue.BlueprintEditorLibrary.list_graphs(bp):
        editor = ue.BlueprintGraphEditor.get_graph_editor(graph)
        require(editor is not None, "missing native graph editor")
        require(not editor.list_nodes_with_errors(), "existing graph has errors")
        nodes = {}
        for node in editor.list_all_nodes():
            position = node.get_node_pos()
            nodes[node.get_path_name()] = {"class": node.get_class().get_path_name(),
                "title": node.get_node_title(), "position": [position.x, position.y],
                "pins": [{"name": str(pin.get_pin_name()), "direction": str(pin.get_pin_direction()),
                          "value": pin.get_pin_value(), "type": pin.get_pin_type_as_json_schema(),
                          "links": sorted([other.get_owning_node().get_path_name(), str(other.get_pin_name()),
                                           str(other.get_pin_direction())] for other in pin.list_connected_pins())}
                         for pin in node.list_all_pins()]}
        result[graph.get_path_name()] = nodes
    return result


def replace_step0_fx(text, fx_text):
    """Replace exactly the top-level FX member, preserving every other export byte."""
    require(text.startswith("(") and text.endswith(")"), "unexpected native step export")
    fields, start, depth, quoted, escaped = [], 1, 0, False, False
    for index in range(1, len(text) - 1):
        char = text[index]
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            require(depth >= 0, "unbalanced native step export")
        elif char == "," and depth == 0:
            fields.append(text[start:index])
            start = index + 1
    fields.append(text[start:-1])
    require(not quoted and depth == 0, "incomplete native step export")
    matches = [i for i, field in enumerate(fields) if field.strip().startswith("FX=")]
    require(len(matches) == 1, "native step export has no unique FX member")
    fields[matches[0]] = "FX=" + fx_text
    return "(" + ",".join(fields) + ")"


def protect_step0(text):
    return replace_step0_fx(text, "<selected>")


def snapshot(ue, bp, cdo):
    steps = list(cdo.get_editor_property("combo_steps"))
    require(len(steps) == 3, "formal combo must retain its three steps")
    require([int(step.get_editor_property("next_step_index")) for step in steps] == [1, 2, 0],
            "formal 1/2/0 step links differ")
    first_montage = steps[0].get_editor_property("montage")
    require(first_montage is not None and first_montage.get_path_name() == MONTAGE + "." + MONTAGE.rsplit("/", 1)[1],
            "formal step0 is not the existing Normal01 Montage")
    exports = [step.export_text() for step in steps]
    return {"parent": bp.get_blueprint_parent_class().get_path_name(),
            "generated_class": bp.generated_class().get_path_name(), "graphs": graph_snapshot(ue, bp),
            "protected_steps": [protect_step0(exports[0]), *exports[1:]],
            "fx": steps[0].get_editor_property("fx").export_text()}


def selected_fx(ue, system):
    begin, end = ue.GameplayTag(), ue.GameplayTag()
    require(begin.import_text('(TagName="' + BEGIN + '")') and end.import_text('(TagName="' + END + '")'),
            "native FX tags are unavailable")
    require(ue.GameplayTagLibrary.is_gameplay_tag_valid(begin) and ue.GameplayTagLibrary.is_gameplay_tag_valid(end)
            and str(ue.GameplayTagLibrary.get_tag_name(begin)) == BEGIN
            and str(ue.GameplayTagLibrary.get_tag_name(end)) == END, "native FX tag registration differs")
    identity = ue.Transform()
    values = {"mode": ue.GGYGOComboFXMode.MONTAGE_WINDOW, "system": system,
              "begin_event_tag": begin, "end_event_tag": end,
              "space": ue.GGYGONiagaraEffectSpace.ATTACHED,
              "socket_name": ue.Name("None"), "local_transform": identity,
              "normal_stop_mode": ue.GGYGONiagaraEffectStopMode.DEACTIVATE_DETACH_KEEP_WORLD,
              "abort_stop_mode": ue.GGYGONiagaraEffectStopMode.DESTROY_IMMEDIATELY}
    # 原生结构构造初始化字段；独立结构实例不能逐项编辑 EditDefaultsOnly 属性。
    fx = ue.GGYGOComboStepFX(**values)
    for name, value in values.items():
        actual = fx.get_editor_property(name)
        actual_text = actual.export_text() if hasattr(actual, "export_text") else str(actual)
        expected_text = value.export_text() if hasattr(value, "export_text") else str(value)
        if name == "local_transform":
            components = {"translation": "xyz", "rotation": "xyzw", "scale3d": "xyz"}
            actual_values = {part: [float(actual.get_editor_property(part).get_editor_property(axis)) for axis in axes]
                             for part, axes in components.items()}
            expected_values = {part: [float(value.get_editor_property(part).get_editor_property(axis)) for axis in axes]
                               for part, axes in components.items()}
            identity_values = {"translation": [0.0, 0.0, 0.0], "rotation": [0.0, 0.0, 0.0, 1.0], "scale3d": [1.0, 1.0, 1.0]}
            # 数值读回精确确认 Identity 与复制值；原生比较三个零容差，拒绝 NaN/Inf。
            matches = all(math.isfinite(number) for data in (actual_values, expected_values) for values_part in data.values()
                          for number in values_part) and expected_values == identity_values and actual_values == expected_values \
                and ue.MathLibrary.nearly_equal_transform_transform(actual, value, 0.0, 0.0, 0.0)
            actual_text += "; components=" + str(actual_values)
            expected_text += "; components=" + str(expected_values)
        elif hasattr(value, "export_text"):
            matches = actual_text == expected_text
        else:
            matches = actual == value
        require(matches, "native FX construction differs: " + name + "; actual=" + actual_text + "; expected=" + expected_text)
    return fx


def validate_window(ue, montage):
    matches = []
    for event in ue.AnimationLibrary.get_animation_notify_events(montage):
        state = event.get_editor_property("notify_state_class")
        if state is None or state.get_class().get_path_name() != "/Script/GGYGO.GGYGOAnimNotifyState_GameplayEventWindow":
            continue
        begin = state.get_editor_property("begin_event_tag").export_text()
        end = state.get_editor_property("end_event_tag").export_text()
        if BEGIN not in begin and END not in end:
            continue
        require(begin == '(TagName="' + BEGIN + '")' and end == '(TagName="' + END + '")', "conflicting FX tags")
        matches.append(event)
        require(event.get_editor_property("montage_tick_type") == ue.MontageNotifyTickType.QUEUED,
                "FX window must be Queued")
        require(int(state.get_editor_property("notify_state_behavior_flags")) & 1, "FX window must prevent native instance merging")
        require(abs(float(ue.AnimationLibrary.get_anim_notify_event_trigger_time(event)) - .05) < .000001
                and abs(float(ue.AnimationLibrary.get_anim_notify_event_duration(event)) - .167) < .000001,
                "FX project-test author window must be .05-.217 seconds")
    require(len(matches) == 1, "saved Normal01 must contain exactly one selected FX window")


def run(mode, *, record, baseline=None, backup_dir=None):
    import unreal as ue
    require(mode in ("audit", "apply", "cold"), "invalid mode")
    require((mode == "audit" and baseline is None and backup_dir is None)
            or (mode == "apply" and baseline is not None and backup_dir is not None)
            or (mode == "cold" and baseline is not None and backup_dir is None), "mode arguments disagree")
    output = saved_path(record)
    require(not output.exists(), "record already exists")
    result = {"schema": SCHEMA, "mode": mode, "pid": os.getpid(), "success": False, "target": GA}
    try:
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        require(levels is not None and not levels.is_in_play_in_editor(), "PIE must be stopped")
        original_dirty = dirty(ue)
        require(original_dirty == {"content": [], "maps": []}, "Editor must start clean")
        bp = ue.EditorAssetLibrary.load_asset(GA)
        require(isinstance(bp, ue.Blueprint) and bp.generated_class() is not None, "formal GA Blueprint/class missing")
        require(bp.get_blueprint_parent_class().get_path_name() == PARENT, "formal native parent differs")
        require("BS_ERROR" not in str(bp.get_editor_property("status")), "formal GA has a Blueprint error")
        system = ue.EditorAssetLibrary.load_asset(SYSTEM)
        require(isinstance(system, ue.NiagaraSystem), "exact seven-color NS missing or wrong class")
        montage = ue.EditorAssetLibrary.load_asset(MONTAGE)
        require(isinstance(montage, ue.AnimMontage), "formal Normal01 missing")
        validate_window(ue, montage)
        cdo = ue.get_default_object(bp.generated_class())
        before = snapshot(ue, bp, cdo)
        expected = selected_fx(ue, system)
        default_fx = ue.GGYGOComboStepFX().export_text()
        require(before["fx"] in (default_fx, expected.export_text()), "existing FX selection conflicts; replacement not authorized")
        require(dirty(ue) == original_dirty, "loading/read-only audit dirtied packages")
        current_hash = digest(disk_file(GA))
        result.update(before=before, expected_fx=expected.export_text(), before_hash=current_hash,
                      dependencies={SYSTEM: digest(disk_file(SYSTEM)), MONTAGE: digest(disk_file(MONTAGE))})
        if baseline is not None:
            prior = json.loads(saved_path(baseline).read_text(encoding="utf-8"))
            require(prior.get("schema") == SCHEMA and prior.get("success") is True and prior.get("target") == GA,
                    "invalid baseline")
            require(prior.get("mode") == ("audit" if mode == "apply" else "apply"), "wrong baseline stage")
            require(prior["expected_fx"] == expected.export_text(), "selected FX configuration changed since baseline")
            require(prior["dependencies"] == result["dependencies"], "saved dependencies changed since baseline")
            require(current_hash == prior["after_hash"], "target changed since baseline")
            if mode == "apply":
                require(before == prior["after"], "live target differs from audit")
            else:
                require(prior["pid"] != os.getpid(), "cold read requires a fresh Editor process")
                require(before == prior["after"] and before["fx"] == expected.export_text(), "cold saved defaults/protection differ")
                require("UP_TO_DATE" in str(bp.get_editor_property("status")), "cold formal GA is not compiled UpToDate")
        if mode == "apply" and before["fx"] != expected.export_text():
            backup = saved_path(backup_dir) / "Content" / (GA[6:] + ".uasset")
            require(not backup.exists(), "backup already exists")
            backup.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(disk_file(GA), backup)
            require(digest(backup) == current_hash, "original backup differs")
            result["backup"] = str(backup)
            steps = list(cdo.get_editor_property("combo_steps"))
            prepared = ue.GGYGOComboStep()
            require(prepared.import_text(replace_step0_fx(steps[0].export_text(), expected.export_text())),
                    "native step0 FX copy import failed")
            require(protect_step0(prepared.export_text()) == before["protected_steps"][0], "step0 preparation changed protected fields")
            require(prepared.get_editor_property("fx").export_text() == expected.export_text(), "prepared step0 FX differs")
            steps[0] = prepared
            bp.modify()
            cdo.modify()
            cdo.set_editor_property("combo_steps", steps)
            require(ue.BlueprintEditorLibrary.compile_blueprint(bp), "formal GA compilation failed")
            require("UP_TO_DATE" in str(bp.get_editor_property("status")), "formal GA is not compiled UpToDate")
            cdo = ue.get_default_object(bp.generated_class())
            changed = snapshot(ue, bp, cdo)
            require(changed == dict(before, fx=expected.export_text()), "fields/other steps/graphs/class changed")
            live_dirty = dirty(ue)
            require(not live_dirty["maps"] and set(live_dirty["content"]).issubset({GA}), "unrelated package dirtied")
            require(digest(disk_file(GA)) == current_hash, "saved target changed before exact save")
            require(ue.EditorAssetLibrary.save_loaded_asset(bp, only_if_is_dirty=False), "exact GA save failed")
        after = snapshot(ue, bp, cdo)
        expected_after = dict(before, fx=expected.export_text()) if mode != "audit" else before
        require(after == expected_after, "final target readback differs")
        require(dirty(ue) == original_dirty, "final dirty set differs")
        after_hash = digest(disk_file(GA))
        if mode != "apply":
            require(after_hash == current_hash, "read-only mode changed saved target")
        elif before["fx"] != expected.export_text():
            require(after_hash != current_hash, "save returned success without changing the target package")
        require(result["dependencies"] == {SYSTEM: digest(disk_file(SYSTEM)), MONTAGE: digest(disk_file(MONTAGE))},
                "saved dependency changed")
        result.update(success=True, after=after, after_hash=after_hash,
                      status="configured_playback_pending" if mode == "apply" else "cold_defaults_verified_playback_pending" if mode == "cold" else "audited_no_save")
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
        ue.log("PYRIOS_COMBO_FX " + json.dumps({key: result.get(key) for key in ("mode", "success", "status", "error")}, ensure_ascii=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("audit", "apply", "cold"), required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--backup-dir")
    options = parser.parse_args()
    run(options.mode, record=options.record, baseline=options.baseline, backup_dir=options.backup_dir)
