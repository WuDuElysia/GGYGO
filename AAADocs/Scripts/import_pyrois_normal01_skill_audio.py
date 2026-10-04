"""Single-asset UE import/readback; execute only in the coordinator's UE window.

UE Python: py "F:/ue_project/GGYGO/AAADocs/Scripts/import_pyrois_normal01_skill_audio.py" --mode import
MCP Python: runpy.run_path(SCRIPT_PATH)["run"]("import")  # or "readback"
No playback, Montage edits, overwrite, SaveAll, or automatic failure cleanup.
"""

import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import traceback
import wave


PROJECT = Path("F:/ue_project/GGYGO")
SOURCE = Path("F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model/Audio/"
              "Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_01/Skill_Attack_Normal_01.wav")
MAPPING = SOURCE.parent / "mapping.json"
TARGET = "/Game/Characters/Player/Pyrios/Audio/Normal01/SW_Pyrios_Normal01_Skill"
OBJECT_PATH = TARGET + ".SW_Pyrios_Normal01_Skill"
TARGET_FILE = PROJECT / "Content/Characters/Player/Pyrios/Audio/Normal01/SW_Pyrios_Normal01_Skill.uasset"
MONTAGE_FILE = PROJECT / "Content/Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_Normal_01.uasset"
SOURCE_SHA256 = "6EEAFD54C64C6D028DB1A734577860470BE657F3035CCE28529C562C289D3B55"
MAPPING_SHA256 = "43884F9EA1EF79865CE91D2DDA7406A025491157CBE00288DD2E4ABFBC0B6F6C"
ORIGINAL_MONTAGE_SHA256 = "1D4D80F856385B7446F08F149034D7095A94B62CA5469DFFAB248D98C279E0B9"
REPORT_DIR = PROJECT / "Saved/ValidationRecords"
REPORTS = {mode: REPORT_DIR / ("PyroisNormal01SkillAudio_20261004_" + mode + ".json")
           for mode in ("import", "readback")}


def require(condition, reason):
    if not condition:
        raise RuntimeError("Audio Normal_01 [%s]: %s" % (TARGET, reason))


def path_key(path):
    return os.path.normcase(str(Path(path).resolve()))


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def dirty_packages(unreal):
    return {
        "content": sorted(p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages()),
        "maps": sorted(p.get_name() for p in unreal.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
    }


def check_dirty(before, after, allow_target):
    for kind in ("content", "maps"):
        original, current = set(before[kind]), set(after[kind])
        allowed = {TARGET} if kind == "content" and allow_target else set()
        require(not (current - original - allowed), "unexpected dirty %s packages: %s" %
                (kind, sorted(current - original - allowed)))
        require(not (original - current), "pre-existing dirty %s packages changed membership: %s" %
                (kind, sorted(original - current)))


def dirty_delta(before, after):
    return {kind: {"added": sorted(set(after[kind]) - set(before[kind])),
                   "removed": sorted(set(before[kind]) - set(after[kind]))}
            for kind in ("content", "maps")}


def inspect_source():
    require(SOURCE.is_file(), "source WAV missing: " + str(SOURCE))
    require(sha256(SOURCE) == SOURCE_SHA256, "source WAV hash differs from frozen source")
    require(sha256(MAPPING) == MAPPING_SHA256, "mapping hash differs from frozen evidence")
    mapping = json.loads(MAPPING.read_text(encoding="utf-8"))
    entries = [e for e in mapping["events"] if e["eventShortId"] == 667813318]
    require(len(entries) == 1, "expected one mapped Skill event 667813318")
    event = entries[0]
    require(event["eventName"] == "Play_SFX_Char_Skill_Pyrois_Attack_Normal_01", "event name mismatch")
    require(event["outputs"] == [SOURCE.parent.name + "/" + SOURCE.name], "mapped WAV output mismatch")
    with wave.open(str(SOURCE), "rb") as reader:
        channels, width, rate = reader.getnchannels(), reader.getsampwidth(), reader.getframerate()
        frames, compression = reader.getnframes(), reader.getcomptype()
        pcm = reader.readframes(frames)
    require((channels, width, rate, compression) == (2, 2, 44100, "NONE"), "unexpected source PCM format")
    require(frames > 0 and len(pcm) == frames * channels * width and any(pcm), "empty, truncated or silent PCM")
    return {"path": str(SOURCE), "sha256": SOURCE_SHA256, "event_id": 667813318,
            "mapping_sha256": MAPPING_SHA256, "channels": channels, "sample_width_bytes": width,
            "sample_rate": rate, "frames": frames, "duration_seconds": frames / rate}


def inspect_asset(unreal, asset, source):
    require(isinstance(asset, unreal.SoundWave), "output is not a SoundWave")
    require(asset.get_path_name() == OBJECT_PATH, "unexpected object path: " + asset.get_path_name())
    # SoundWave's ImportData and ImportedSampleRate properties are protected.
    # Use its native named import-data subobject and searchable registry tag.
    import_data = unreal.find_object(asset, "AssetImportData")
    require(isinstance(import_data, unreal.AssetImportData), "native AssetImportData subobject missing")
    filenames = list(import_data.extract_filenames())
    require(len(filenames) == 1 and path_key(filenames[0]) == path_key(SOURCE), "stored import source mismatch")
    asset_data = unreal.AssetRegistryHelpers.create_asset_data(asset)
    sample_rate_tag = unreal.AssetRegistryHelpers.get_tag_value(asset_data, "ImportedSampleRate")
    require(isinstance(sample_rate_tag, str) and sample_rate_tag != "", "ImportedSampleRate tag unreadable")
    values = {"object_path": asset.get_path_name(), "class": asset.get_class().get_name(),
              "source_filenames": filenames, "imported_sample_rate": int(sample_rate_tag),
              "channels": asset.get_editor_property("num_channels"),
              "duration_seconds": asset.get_editor_property("duration"),
              "looping": asset.get_editor_property("looping"),
              "volume": asset.get_editor_property("volume"), "pitch": asset.get_editor_property("pitch")}
    require(values["imported_sample_rate"] == 44100 and values["channels"] == 2, "imported format mismatch")
    require(math.isfinite(values["duration_seconds"]) and
            abs(values["duration_seconds"] - source["duration_seconds"]) <= 0.00001, "imported duration mismatch")
    require(values["looping"] is False, "SoundWave must be explicitly non-looping")
    require(values["volume"] == 1.0 and values["pitch"] == 1.0, "project volume/pitch must be explicitly 1.0")
    return values


def import_asset(unreal, report, source, before):
    require(not TARGET_FILE.exists() and not unreal.EditorAssetLibrary.does_asset_exist(TARGET),
            "import refuses existing target; use readback without overwrite")
    require(TARGET not in before["content"], "target package already dirty")
    factory = unreal.SoundFactory()
    for name in ("auto_create_cue", "include_attenuation_node", "include_looping_node", "include_modulator_node"):
        factory.set_editor_property(name, False)
    task = unreal.AssetImportTask()
    properties = {"filename": str(SOURCE), "destination_path": TARGET.rsplit("/", 1)[0],
                  "destination_name": TARGET.rsplit("/", 1)[1], "automated": True,
                  "replace_existing": False, "replace_existing_settings": False, "save": False,
                  "factory": factory}
    for name, value in properties.items():
        task.set_editor_property(name, value)
    report["stage"] = "import"
    unreal.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
    objects = list(task.get_objects())
    paths = list(task.get_editor_property("imported_object_paths"))
    report["imported_object_paths"] = paths
    require(len(objects) == 1 and paths == [OBJECT_PATH], "import must produce exactly the target asset")
    require(not TARGET_FILE.exists(), "import unexpectedly saved before validation")
    asset = objects[0]
    require(isinstance(asset, unreal.SoundWave) and asset.get_path_name() == OBJECT_PATH, "unexpected import output")
    for name, value in (("looping", False), ("volume", 1.0), ("pitch", 1.0)):
        asset.set_editor_property(name, value)
    report["asset"] = inspect_asset(unreal, asset, source)
    report["dirty_before_save"] = dirty_packages(unreal)
    report["dirty_delta_before_save"] = dirty_delta(before, report["dirty_before_save"])
    check_dirty(before, report["dirty_before_save"], allow_target=True)
    require(sha256(SOURCE) == SOURCE_SHA256 and sha256(MAPPING) == MAPPING_SHA256,
            "source or mapping changed before save")
    require(sha256(MONTAGE_FILE) == report["montage_before_sha256"], "Montage changed before save")
    report["stage"] = "save_target_only"
    require(unreal.EditorAssetLibrary.save_loaded_asset(asset, only_if_is_dirty=False), "target save failed")
    report["save_returned_true"] = True
    require(TARGET_FILE.is_file() and TARGET_FILE.stat().st_size > 0, "target package not persisted")
    report["asset"] = inspect_asset(unreal, asset, source)
    return asset


def run(mode):
    """Return the report on success; write failure evidence and raise on failure."""
    require(mode in REPORTS, "mode must be import or readback")
    report = {"mode": mode, "success": False, "stage": "preflight", "target": TARGET,
              "started_utc": datetime.now(timezone.utc).isoformat(),
              "original_montage_lease_sha256": ORIGINAL_MONTAGE_SHA256,
              "playback_tested": False, "notify_timing_verified": False, "new_ga_chain_verified": False}
    unreal_api, before, failure = None, None, None
    try:
        import unreal
        unreal_api = unreal
        require(path_key(unreal.Paths.project_dir()) == path_key(PROJECT), "wrong UE project")
        require(path_key(Path(__file__).resolve().parents[2]) == path_key(PROJECT), "script moved outside fixed project")
        report["source"] = inspect_source()
        report["montage_before_sha256"] = sha256(MONTAGE_FILE)
        report["target_existed_before"] = TARGET_FILE.is_file()
        if mode == "import":
            require(report["montage_before_sha256"] == ORIGINAL_MONTAGE_SHA256, "original Montage baseline changed")
        else:
            require(TARGET_FILE.is_file(), "readback requires a saved target")
            report["target_before_sha256"] = sha256(TARGET_FILE)
        before = dirty_packages(unreal)
        report["dirty_before"] = before
        require(TARGET not in before["content"], "target must be clean at entry")
        if mode == "import":
            import_asset(unreal, report, report["source"], before)
        else:
            report["stage"] = "readback_only"
            asset = unreal.EditorAssetLibrary.load_asset(TARGET)
            report["asset"] = inspect_asset(unreal, asset, report["source"])
        report["stage"] = "final_protection_checks"
        report["dirty_after"] = dirty_packages(unreal)
        report["dirty_delta_after"] = dirty_delta(before, report["dirty_after"])
        check_dirty(before, report["dirty_after"], allow_target=False)
        report["source_after_sha256"] = sha256(SOURCE)
        report["mapping_after_sha256"] = sha256(MAPPING)
        require(report["source_after_sha256"] == SOURCE_SHA256 and report["mapping_after_sha256"] == MAPPING_SHA256,
                "source or mapping changed during execution")
        report["montage_after_sha256"] = sha256(MONTAGE_FILE)
        require(report["montage_after_sha256"] == report["montage_before_sha256"], "Montage changed during execution")
        report["target_after_sha256"] = sha256(TARGET_FILE)
        if mode == "readback":
            require(report["target_after_sha256"] == report["target_before_sha256"], "readback modified target file")
        report["success"] = True
        report["stage"] = "complete"
    except Exception:
        failure = traceback.format_exc()
        report["failure"] = failure
        # Diagnostic snapshots only: no retry, deletion, rollback or saving on failure.
        report["failure_snapshot_errors"] = []
        if unreal_api is not None and before is not None:
            try:
                report["dirty_after_failure"] = dirty_packages(unreal_api)
                report["dirty_delta_after_failure"] = dirty_delta(before, report["dirty_after_failure"])
            except Exception as snapshot_error:
                report["failure_snapshot_errors"].append(str(snapshot_error))
        for name, path in (("source", SOURCE), ("mapping", MAPPING), ("montage", MONTAGE_FILE), ("target", TARGET_FILE)):
            try:
                report[name + "_after_failure_sha256"] = sha256(path) if path.is_file() else None
            except Exception as snapshot_error:
                report["failure_snapshot_errors"].append(name + ": " + str(snapshot_error))
    report["finished_utc"] = datetime.now(timezone.utc).isoformat()
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    REPORTS[mode].write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if failure is not None:
        if unreal_api is not None:
            unreal_api.log_error("Audio Normal_01 failed at %s; report=%s\n%s" %
                                 (report["stage"], REPORTS[mode], failure))
        raise RuntimeError("Audio Normal_01 failed; inspect " + str(REPORTS[mode]))
    unreal_api.log("Audio Normal_01 %s passed; report=%s" % (mode, REPORTS[mode]))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("import", "readback"), required=True)
    run(parser.parse_args().mode)
