"""@file import_bh3_kevin_demonbattle_audio.py
@brief Prepare and import new Kevin DemonBattle SoundWaves from action mappings.

Offline: --mode plan [--actions ACTUAL_CLIP_NAME ...]. No file writes.
UE: runpy.run_path(SCRIPT)["run"]("import", actions, expected_targets).
Use build_plan(actions) to review the exact targets before granting the UE window.
expected_targets is an explicit nonempty selection from that plan; it may be a
subset for a smoke batch or recovery after partial saves, never an auto-skip list.
Readback uses run("readback", actions, expected_targets) without setters or saves.
Commandlet: -run=PythonScript -Script="SCRIPT --mode import ... --host commandlet".
The host must be selected explicitly; editor remains the default for GUI callers.

Consumes Audio/<actual clip>/mapping.json, not event-name guesses in this tool.
Mapped WAVs are asset-only PCM16 sources, with explicit non-looping/volume/pitch=1
project defaults. Original event mixing, loops, timing and playback are unproved.
No overwrite/reimport, automatic rollback, SaveAll, playback or Montage edits.
Import failure may leave new dirty assets or earlier saved targets: it stops the
batch, logs the original failure and saved list, and never claims atomic rollback.
"""

import argparse
import json
import math
import os
from pathlib import Path, PurePosixPath
import re
import wave


PROJECT = Path("F:/ue_project/GGYGO")
SOURCE = Path("F:/AnimeStudio/Exports/BH3/Animator/Kevin/05_BOSS_411_DemonBattle")
AUDIO = SOURCE / "Audio"
TARGET_ROOT = "/Game/Characters/Boss/Kevin/DemonBattle/Audio"
ASSOCIATIONS = {"animation_event_verified", "name_associated", "unassigned", "control_only"}
MEDIA_ASSOCIATIONS = {"animation_event_verified", "name_associated"}


def require(condition, reason):
    if not condition:
        raise RuntimeError("[Audio.KevinDemonBattle] " + reason)


def path_key(path):
    return os.path.normcase(str(Path(path).resolve()))


def file_stamp(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def read_json(path):
    with path.open("r", encoding="utf-8-sig") as stream:
        try:
            return json.load(stream)
        except json.JSONDecodeError as exc:
            raise RuntimeError("[Audio.KevinDemonBattle] invalid mapping JSON: " + str(path) + "; " + str(exc)) from exc


def inspect_wav(path):
    """Read one exported PCM source; reject unsupported/truncated/empty input."""
    require(path.is_file(), "mapped WAV missing: " + str(path))
    stamp = file_stamp(path)
    with wave.open(str(path), "rb") as reader:
        channels, width, rate = reader.getnchannels(), reader.getsampwidth(), reader.getframerate()
        frames = reader.getnframes()
        require(reader.getcomptype() == "NONE" and width == 2,
                "expected decoded PCM16 WAV (no implicit conversion): " + str(path))
        require(channels in (1, 2) and rate > 0 and frames > 0,
                "unsupported channels or empty WAV: " + str(path))
        read_frames, nonzero_pcm = 0, False
        while True:
            data = reader.readframes(65536)
            if not data:
                break
            require(len(data) % (channels * width) == 0, "truncated PCM frame: " + str(path))
            read_frames += len(data) // (channels * width)
            nonzero_pcm = nonzero_pcm or any(data)
    require(read_frames == frames and nonzero_pcm, "truncated or all-zero PCM: " + str(path))
    require(file_stamp(path) == stamp, "source changed during inspection: " + str(path))
    return {"channels": channels, "sample_rate": rate, "frames": frames,
            "duration_seconds": frames / rate, "stamp": stamp}


def asset_name(stem):
    name = re.sub(r"[^A-Za-z0-9_]", "_", stem)
    require(name.strip("_"), "WAV filename has no usable asset name: " + stem)
    return "SW_" + name


def build_plan(actions=None):
    """Return source/target records and visible gaps; no UE import or file write."""
    require(AUDIO.is_dir(), "Audio export is not available: " + str(AUDIO))
    audio_root = AUDIO.resolve()
    available = {p.parent.name: p for p in AUDIO.glob("*/mapping.json")}
    require(available, "no action mapping.json found under " + str(AUDIO))
    selected = sorted(available) if actions is None else list(actions)
    require(selected and len(selected) == len(set(selected)), "actions must be nonempty and unique")
    records, gaps, stamps, targets = [], [], {}, set()
    for action in selected:
        require(isinstance(action, str) and action not in ("", ".", "..") and Path(action).name == action,
                "unsafe source action directory: " + repr(action))
        require(action in available, "action has no exported mapping: " + action)
        require((SOURCE / "anim" / (action + ".fbx")).is_file(), "not an actual source clip: " + action)
        mapping_path = available[action]
        require(mapping_path.resolve().is_relative_to(audio_root), "mapping link escapes Audio root: " + str(mapping_path))
        stamp = file_stamp(mapping_path)
        mapping = read_json(mapping_path)
        require(file_stamp(mapping_path) == stamp, "mapping changed during read: " + str(mapping_path))
        stamps[str(mapping_path)] = stamp
        require(isinstance(mapping, dict) and {"animationName", "mappingBasis", "events", "wavCount", "coverageStatus"} <= mapping.keys(),
                "required action mapping fields missing: " + str(mapping_path))
        require(mapping["animationName"] == action and isinstance(mapping["mappingBasis"], str) and mapping["mappingBasis"],
                "action/mapping basis mismatch: " + str(mapping_path))
        require(mapping["coverageStatus"] in ("mapped", "no_mapped_events"),
                "unknown coverage status: " + str(mapping_path))
        events = mapping["events"]
        require(isinstance(events, list), "events must be a list: " + str(mapping_path))
        files = {}
        for event in events:
            require(isinstance(event, dict) and {"eventName", "eventShortId", "outputs", "associationStatus", "controlOnly"} <= event.keys(),
                    "required event fields missing: " + str(mapping_path))
            require(isinstance(event["eventName"], str) and event["eventName"]
                    and type(event["eventShortId"]) is int and event["eventShortId"] > 0,
                    "invalid event identity: " + str(mapping_path))
            outputs = event["outputs"]
            require(isinstance(outputs, list), "outputs must be an explicit list: " + str(mapping_path))
            association, control = event["associationStatus"], event["controlOnly"]
            require(isinstance(association, str) and association in ASSOCIATIONS and type(control) is bool,
                    "unknown association/control classification: " + str(mapping_path))
            require(control == (association == "control_only") and (not control or not outputs),
                    "control-only operation cannot be a SoundWave: " + event["eventName"] + " in " + str(mapping_path))
            if not outputs:
                gaps.append({"action": action, "event": event["eventName"],
                             "association_status": association, "control_only": control,
                             "reason": "no WAV declared; original mapping owns operation/missing-source classification"})
                continue
            require(association in MEDIA_ASSOCIATIONS,
                    "unassigned event cannot be imported into an action: " + event["eventName"] + " in " + str(mapping_path))
            require(isinstance(event.get("mappingMethod"), str) and event["mappingMethod"],
                    "missing association evidence: " + str(mapping_path))
            for output in outputs:
                require(isinstance(output, str), "mapped output must be a relative path: " + str(mapping_path))
                relative = PurePosixPath(output.replace("\\", "/"))
                require(not relative.is_absolute() and len(relative.parts) == 2
                        and relative.parts[0] == action and relative.suffix.lower() == ".wav"
                        and ".." not in relative.parts,
                        "mapped output escapes action directory: " + repr(output))
                path = AUDIO.joinpath(*relative.parts).resolve()
                require(path.parent == mapping_path.parent.resolve(), "WAV link escapes action folder: " + str(path))
                files.setdefault(path, []).append({"name": event["eventName"], "id": event["eventShortId"],
                                                  "basis": event["mappingMethod"], "association_status": association})
        actual = {p.resolve() for p in mapping_path.parent.rglob("*.wav")}
        require(actual == set(files), "WAV/mapping inventory mismatch for " + action
                + "; unmapped=" + repr(sorted(str(p) for p in actual - set(files)))
                + "; missing=" + repr(sorted(str(p) for p in set(files) - actual)))
        require(type(mapping["wavCount"]) is int and mapping["wavCount"] == len(files),
                "wavCount differs from mapped distinct files: " + str(mapping_path))
        if not files:
            gaps.append({"action": action, "reason": "no importable WAV in this action mapping"})
        else:
            require(re.fullmatch(r"[A-Za-z0-9_]+", action),
                    "mapped source action needs an explicit valid UE target directory: " + action)
        for path, references in sorted(files.items()):
            name = asset_name(path.stem)
            target = TARGET_ROOT + "/" + action + "/" + name
            require(target.casefold() not in targets, "asset naming collision: " + target)
            targets.add(target.casefold())
            source = inspect_wav(path)
            stamps[str(path)] = source.pop("stamp")
            records.append({"action": action, "source": str(path), "mapping": str(mapping_path),
                            "events": references, "target": target, "object_path": target + "." + name,
                            "target_file": str(PROJECT / "Content" / (target[6:] + ".uasset")),
                            **source})
    require(records, "selected actions have no importable WAV; gaps=" + repr(gaps))
    return {"actions": selected, "assets": records, "gaps": gaps, "source_stamps": stamps,
            "asset_defaults": {"looping": False, "volume": 1.0, "pitch": 1.0},
            "original_timing_mixing_verified": False, "playback_tested": False}


def dirty_packages(unreal):
    return {"content": {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()},
            "maps": {p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()}}


def check_dirty(before, after, allowed=()):
    for kind in ("content", "maps"):
        extra = set(allowed) if kind == "content" else set()
        require(not (after[kind] - before[kind] - extra) and not (before[kind] - after[kind]),
                "unexpected dirty " + kind + " membership; added=" + repr(sorted(after[kind] - before[kind]))
                + "; removed=" + repr(sorted(before[kind] - after[kind])))


def check_sources(plan, filenames=None):
    names = plan["source_stamps"] if filenames is None else filenames
    for filename in names:
        stamp = plan["source_stamps"][filename]
        require(file_stamp(Path(filename)) == tuple(stamp), "frozen input changed: " + filename)


def require_new_target(unreal, record):
    target, object_path = record["target"], record["object_path"]
    require(not Path(record["target_file"]).exists()
            and not unreal.EditorAssetLibrary.does_asset_exist(target)
            and unreal.find_object(None, object_path, follow_redirectors=False) is None,
            "new-only target already exists on disk, registry or in memory: " + target)


def inspect_asset(unreal, asset, record):
    require(isinstance(asset, unreal.SoundWave) and asset.get_path_name() == record["object_path"],
            "unexpected SoundWave output for " + record["target"])
    import_data = unreal.find_object(asset, "AssetImportData")
    require(isinstance(import_data, unreal.AssetImportData), "native import source unavailable: " + record["target"])
    filenames = list(import_data.extract_filenames())
    require(len(filenames) == 1 and path_key(filenames[0]) == path_key(record["source"]),
            "stored import source differs: " + record["target"])
    asset_data = unreal.AssetRegistryHelpers.create_asset_data(asset)
    rate = unreal.AssetRegistryHelpers.get_tag_value(asset_data, "ImportedSampleRate")
    require(isinstance(rate, str) and rate, "public ImportedSampleRate tag unavailable: " + record["target"])
    channels = asset.get_editor_property("num_channels")
    duration = asset.get_editor_property("duration")
    require(int(rate) == record["sample_rate"] and channels == record["channels"],
            "imported format differs: " + record["target"])
    require(math.isfinite(duration) and abs(duration - record["duration_seconds"]) <= max(1e-5, 1 / int(rate)),
            "imported duration differs: " + record["target"])
    require(asset.get_editor_property("looping") is False
            and asset.get_editor_property("volume") == 1.0 and asset.get_editor_property("pitch") == 1.0,
            "explicit asset-only defaults differ: " + record["target"])
    return {"target": record["target"], "source_filenames": filenames,
            "sample_rate": int(rate), "channels": channels, "duration_seconds": duration}


def import_one(unreal, record, before):
    require_new_target(unreal, record)  # Earlier native imports may invoke editor callbacks.
    factory = unreal.SoundFactory()
    for name in ("auto_create_cue", "include_attenuation_node", "include_looping_node", "include_modulator_node"):
        factory.set_editor_property(name, False)
    task = unreal.AssetImportTask()
    for name, value in {"filename": record["source"], "destination_path": record["target"].rsplit("/", 1)[0],
                        "destination_name": record["target"].rsplit("/", 1)[1], "automated": True,
                        "replace_existing": False, "replace_existing_settings": False,
                        "save": False, "factory": factory}.items():
        task.set_editor_property(name, value)
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    paths = list(task.get_editor_property("imported_object_paths"))
    require(len(objects) == 1 and paths == [record["object_path"]],
            "import must return exactly the planned asset: " + record["target"] + "; paths=" + repr(paths))
    require(not Path(record["target_file"]).exists(), "native import saved before validation: " + record["target"])
    asset = objects[0]
    require(isinstance(asset, unreal.SoundWave) and asset.get_path_name() == record["object_path"],
            "native importer returned an unowned object: " + record["target"])
    for name, value in (("looping", False), ("volume", 1.0), ("pitch", 1.0)):
        asset.set_editor_property(name, value)
    inspect_asset(unreal, asset, record)
    check_dirty(before, dirty_packages(unreal), {record["target"]})
    return asset


def require_execution_host(unreal, host):
    """Validate the declared native host without invoking GUI-only commandlet APIs."""
    require(host in ("editor", "commandlet"), "host must be editor or commandlet")
    commandlet = re.search(r"(?:^|\s)-run=(\S+)", unreal.SystemLibrary.get_command_line(), re.IGNORECASE)
    if host == "commandlet":
        require(commandlet is not None and commandlet.group(1).casefold() == "pythonscript",
                "commandlet host requires the native -run=PythonScript launch")
        require(not unreal.EditorLevelLibrary.get_pie_worlds(include_dedicated_server=True), "PIE must be inactive")
    else:
        require(commandlet is None, "editor host cannot run under a -run commandlet; select --host commandlet")
        subsystem = unreal.get_editor_subsystem(unreal.LevelEditorSubsystem)
        require(subsystem is not None, "editor host has no LevelEditorSubsystem")
        require(not subsystem.is_in_play_in_editor(), "PIE must be inactive")


def run(mode, actions, expected_targets, host="editor"):
    """Import/read back the reviewed target list in the coordinator's UE window.

    Returns runtime results; never writes a report, retries, or deletes assets.
    Existing dirty packages may remain, but selected target packages must be new
    for import and clean/saved for readback. No state survives this invocation.
    Commandlet callers must explicitly select host="commandlet". Its native
    PythonScript launch is verified before using the public PIE-world query;
    it does not inspect another editor process's memory or dirty packages.
    """
    require(mode in ("import", "readback"), "run mode must be import or readback")
    plan = build_plan(actions)
    actual_targets = [r["target"] for r in plan["assets"]]
    require(expected_targets and len(expected_targets) == len(set(expected_targets))
            and set(expected_targets) <= set(actual_targets), "reviewed target is absent from the actual source plan")
    selected_targets = set(expected_targets)
    unselected_count = len(actual_targets) - len(selected_targets)
    plan["assets"] = [r for r in plan["assets"] if r["target"] in selected_targets]
    selected_sources = {r[key] for r in plan["assets"] for key in ("source", "mapping")}
    plan["source_stamps"] = {name: stamp for name, stamp in plan["source_stamps"].items() if name in selected_sources}
    import unreal
    require(path_key(unreal.Paths.project_dir()) == path_key(PROJECT), "wrong UE project")
    require_execution_host(unreal, host)
    before = dirty_packages(unreal)
    for record in plan["assets"]:
        require(record["target"] not in before["content"], "selected target is dirty: " + record["target"])
        if mode == "import":
            require_new_target(unreal, record)
        else:
            require(Path(record["target_file"]).is_file() and unreal.EditorAssetLibrary.does_asset_exist(record["target"]),
                    "readback requires a saved registered target: " + record["target"])
    result = {"mode": mode, "host": host, "saved": [], "assets": [], "gaps": plan["gaps"],
              "explicit_targets": expected_targets, "unselected_count": unselected_count,
              "playback_tested": False, "timing_mixing_verified": False}
    current = "batch preflight"
    try:
        for record in plan["assets"]:
            current = record["target"]
            source_names = (record["source"], record["mapping"])
            check_sources(plan, source_names)  # Earlier native callbacks may outlive source edits.
            if mode == "import":
                asset = import_one(unreal, record, before)
                check_sources(plan, source_names)
                require(unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False),
                        "exact target save failed: " + current)
                result["saved"].append(current)
                target_file = Path(record["target_file"])
                require(target_file.is_file() and target_file.stat().st_size > 0, "target was not persisted: " + current)
            else:
                asset = unreal.EditorAssetLibrary.load_asset(current)
            result["assets"].append(inspect_asset(unreal, asset, record))
            check_dirty(before, dirty_packages(unreal))
        check_sources(plan)  # Actual import/save/load callbacks occurred since the last check.
    except Exception as exc:
        unreal.log_error("[Audio.KevinDemonBattle] " + mode + " host=" + host + " failed at " + current
                         + "; saved=" + repr(result["saved"]) + "; reason=" + str(exc)
                         + "; no rollback/retry performed")
        raise
    unreal.log("[Audio.KevinDemonBattle] " + mode + " host=" + host + " complete; assets=" + str(len(result["assets"]))
               + "; gaps=" + repr(result["gaps"]) + "; playback/timing/mixing unverified")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("plan", "import", "readback"), required=True)
    parser.add_argument("--actions", nargs="+")
    parser.add_argument("--expect-targets", nargs="+")
    parser.add_argument("--host", choices=("editor", "commandlet"), default="editor")
    args = parser.parse_args()
    if args.mode == "plan":
        print(json.dumps(build_plan(args.actions), ensure_ascii=True, indent=2))
    else:
        require(args.actions is not None, "UE execution requires an explicit action selection")
        print(json.dumps(run(args.mode, args.actions, args.expect_targets, args.host), ensure_ascii=True, indent=2))
