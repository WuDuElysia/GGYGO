"""Bounded Normal01 PlaySound authoring, executed only by the coordinator.

Importing this file performs no UE calls and writes nothing. Call audit(),
wire(), or readback() explicitly from the coordinator's Editor Python window.
audit/readback never mutate, reload, or save assets. wire appends one native
PlaySound event on one new track and saves only the named existing Montage.
It does not rebuild the Montage or edit SoundWave/sequence/skeleton/ABP assets.

The project initial time is frame 2 at 60 fps. Original-game event timing is
unknown. Audio supplies all playback parameters; this script has no substitute
sound or playback configuration. Pitch 1 is required for this timing batch.

Reports distinguish loaded-object verification from a fresh disk reload and
from native Section checks / real-device playback. No entry performs playback.
On a post-mutation failure the Montage may remain dirty, or already be saved:
record the failure and let the coordinator inspect it; do not auto-rollback.
"""

import hashlib
import json
import math
from pathlib import Path
import re


PROJECT = Path("F:/ue_project/GGYGO")
MONTAGE = "/Game/Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_Normal_01"
MAIN = "/Game/Characters/Player/Pyrios/Animation/Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_01"
END = MAIN + "_End"
SOUND = "/Game/Characters/Player/Pyrios/Audio/Normal01/SW_Pyrios_Normal01_Skill"
SOURCE_WAV = Path("F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model/Audio/"
                  "Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_01/Skill_Attack_Normal_01.wav")
SOURCE_WAV_SHA256 = "6EEAFD54C64C6D028DB1A734577860470BE657F3035CCE28529C562C289D3B55"
TRACK = "Audio_Normal01"
TIME = 2.0 / 60.0
WINDOW_CLASS = "/Script/GGYGO.GGYGOAnimNotifyState_GameplayEventWindow"
PLAY_SOUND_CLASS = "/Script/Engine.AnimNotify_PlaySound"
REPORT_NAMES = {
    "audit": "PyriosNormal01SoundNotify_20261004_Audit.json",
    "wire": "PyriosNormal01SoundNotify_20261004_Result.json",
    "readback": "PyriosNormal01SoundNotify_20261004_Readback_R1.json",
}
PARAM_PROPERTIES = {
    "volume_multiplier": "VolumeMultiplier",
    "pitch_multiplier": "PitchMultiplier",
    "follow": "bFollow",
    "attach_name": "AttachName",
}


def _require(condition, reason):
    if not condition:
        raise RuntimeError("Animation Normal01 [%s]: %s" % (MONTAGE, reason))


def _sha(path):
    _require(path.is_file(), "required file missing: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _digest(value, label):
    _require(isinstance(value, str) and re.fullmatch(r"[0-9a-fA-F]{64}", value),
             label + " must be an explicit SHA256")
    return value.upper()


def _package_file(package):
    _require(package.startswith("/Game/"), "unsupported protected package: " + package)
    return PROJECT / "Content" / (package[6:] + ".uasset")


def _path(obj):
    return obj.get_path_name() if obj is not None else None


def _package(obj):
    return obj.get_outermost().get_path_name()


def _dirty(ue):
    utils = ue.EditorLoadingAndSavingUtils
    return {
        "content": sorted(p.get_path_name() for p in utils.get_dirty_content_packages()),
        "maps": sorted(p.get_path_name() for p in utils.get_dirty_map_packages()),
    }


def _params(value):
    keys = set(PARAM_PROPERTIES) | {"evidence_ref"}
    _require(isinstance(value, dict) and set(value) == keys,
             "Audio parameters must contain exactly: " + ", ".join(sorted(keys)))
    result = dict(value)
    _require(isinstance(result["evidence_ref"], str) and result["evidence_ref"].strip(),
             "Audio handoff evidence_ref missing")
    for key in ("volume_multiplier", "pitch_multiplier"):
        number = result[key]
        _require(type(number) in (int, float) and math.isfinite(number) and number > 0,
                 "invalid Audio parameter: " + key)
        result[key] = float(number)
    _require(result["pitch_multiplier"] == 1.0,
             "frame-2 initial timing requires Audio Pitch=1; re-freeze timing for another pitch")
    _require(type(result["follow"]) is bool, "Audio parameter must be bool: follow")
    attach = result["attach_name"]
    _require(isinstance(attach, str) and attach.strip() == attach and bool(attach),
             "Audio attach_name must explicitly name a socket/bone or be 'None'")
    _require(attach == "None" or result["follow"],
             "non-None AttachName requires Follow=true in native PlaySound")
    return result


def _play_params(obj):
    result = {}
    for key, prop in PARAM_PROPERTIES.items():
        value = obj.get_editor_property(prop)
        result[key] = str(value) if key == "attach_name" else value
    return result


def _notify_object(obj):
    if obj is None:
        return None
    cls = obj.get_class().get_path_name()
    result = {"path": _path(obj), "class": cls}
    if cls == WINDOW_CLASS:
        result["tags"] = {
            "begin": obj.get_editor_property("BeginEventTag").export_text(),
            "end": obj.get_editor_property("EndEventTag").export_text(),
        }
        result["checked_properties"] = ["BeginEventTag", "EndEventTag"]
    elif cls == PLAY_SOUND_CLASS:
        result["sound"] = _path(obj.get_editor_property("Sound"))
        result["audio_parameters"] = _play_params(obj)
        result["preview_ignore_attenuation"] = bool(obj.get_editor_property("bPreviewIgnoreAttenuation"))
        result["checked_properties"] = ["Sound", "bPreviewIgnoreAttenuation"] + list(PARAM_PROPERTIES.values())
    else:
        result["object_properties_not_enumerated"] = True
    return result


def _events(ue, asset):
    records = {}
    for event in ue.AnimationLibrary.get_animation_notify_events(asset):
        exported = event.export_text()
        match = re.search(r"(?:^|[,\(])Guid=([0-9A-Fa-f]{32})(?:[,\)])", exported)
        _require(match is not None, "Notify lacks a readable GUID: " + asset.get_path_name())
        guid = match.group(1).upper()
        _require(guid not in records, "duplicate Notify GUID: " + guid)
        records[guid] = {
            "guid": guid,
            "event_export": exported,
            "trigger_seconds": float(ue.AnimationLibrary.get_anim_notify_event_trigger_time(event)),
            "duration_seconds": float(ue.AnimationLibrary.get_anim_notify_event_duration(event)),
            "notify": _notify_object(event.get_editor_property("Notify")),
            "state": _notify_object(event.get_editor_property("NotifyStateClass")),
        }
    return records


def _sections(montage):
    names = [str(montage.get_section_name(i)) for i in range(montage.get_num_sections())]
    result = {"names": names, "native_data_readable": False}
    # Native UPROPERTY name, not an invented Python getter. Failure is exposed
    # as a capability gap; it is never reported as verified Section preservation.
    try:
        sections = montage.get_editor_property("CompositeSections")
        result["native_exports"] = [s.export_text() for s in sections]
        result["native_names"] = [str(s.get_editor_property("SectionName")) for s in sections]
        result["next_sections"] = [str(s.get_editor_property("NextSectionName")) for s in sections]
    except Exception as error:
        result["native_property_error"] = str(error)
        result["required_coordinator_check"] = (
            "Read before/after native CompositeSections: SectionName, linked start time, "
            "NextSectionName, link method/slot/segment and metadata. Confirm Main starts "
            "at 0, End at 101/60 seconds, Main->End and End->None; preserve all fields."
        )
        return result
    _require(result["native_names"] == names, "Section name readback disagrees")
    result["native_data_readable"] = True
    return result


def _montage(ue, asset):
    tracks = asset.get_editor_property("SlotAnimTracks")
    _require(len(tracks) == 1, "expected one FullBody slot track")
    slot = tracks[0]
    _require(str(slot.get_editor_property("SlotName")) == "FullBody", "unexpected slot")
    segments = slot.get_editor_property("AnimTrack").get_editor_property("AnimSegments")
    _require(len(segments) == 2, "expected unchanged Main/End segments")
    expected = [(MAIN, 0.0, 101.0 / 60.0), (END, 101.0 / 60.0, 30.0 / 60.0)]
    for segment, (path, start, finish) in zip(segments, expected):
        reference = segment.get_editor_property("AnimReference")
        _require(reference is not None and _package(reference) == path, "unexpected segment source")
        for prop, number in (("StartPos", start), ("AnimStartTime", 0.0),
                             ("AnimEndTime", finish), ("AnimPlayRate", 1.0), ("LoopingCount", 1)):
            _require(abs(float(segment.get_editor_property(prop)) - number) <= 0.000001,
                     "unexpected segment %s: %s" % (path, prop))
    length = float(asset.get_play_length())
    _require(abs(length - 131.0 / 60.0) <= 0.000001, "unexpected Montage length")
    sections = _sections(asset)
    _require(sections["names"] == ["Main", "End"], "unexpected Section names/order")
    blends = {}
    for prop, seconds in (("BlendIn", 0.10), ("BlendOut", 0.25)):
        blend = asset.get_editor_property(prop)
        _require(abs(float(blend.get_editor_property("BlendTime")) - seconds) <= 0.000001,
                 "unexpected " + prop)
        blends[prop] = blend.export_text()
    _require(bool(asset.get_editor_property("bEnableAutoBlendOut")), "auto BlendOut disabled")
    _require(not asset.get_editor_property("bLoop"), "Montage looping is not this batch")
    _require(abs(float(asset.get_editor_property("RateScale")) - 1.0) <= 0.000001,
             "authored timing requires Montage RateScale=1")
    return {
        "path": _path(asset), "length_seconds": length,
        "skeleton": _path(asset.get_editor_property("Skeleton")),
        "slot_exports": [s.export_text() for s in tracks], "sections": sections,
        "blends": blends, "blend_out_trigger_time": float(asset.get_editor_property("BlendOutTriggerTime")),
        "auto_blend_out": bool(asset.get_editor_property("bEnableAutoBlendOut")),
        "loop": bool(asset.get_editor_property("bLoop")), "rate_scale": float(asset.get_editor_property("RateScale")),
        "notify_tracks": [str(n) for n in ue.AnimationLibrary.get_animation_notify_track_names(asset)],
        "events": _events(ue, asset),
    }


def _windows(snapshot):
    found = {}
    for event in snapshot["events"].values():
        state = event["state"]
        if state is None or state["class"] != WINDOW_CLASS:
            continue
        begin = re.fullmatch(r'\(TagName="([^\"]+)"\)', state["tags"]["begin"])
        end = re.fullmatch(r'\(TagName="([^\"]+)"\)', state["tags"]["end"])
        _require(begin is not None and end is not None, "invalid GameplayEventWindow tags")
        key = begin.group(1)
        _require(key not in found, "duplicate GameplayEventWindow: " + key)
        found[key] = (event["trigger_seconds"], event["duration_seconds"], end.group(1))
    expected = {
        "Event.Montage.HitWindowBegin": (4.0 / 60, 10.0 / 60, "Event.Montage.HitWindowEnd"),
        "Event.Montage.ComboWindowBegin": (16.0 / 60, 99.0 / 60, "Event.Montage.ComboWindowEnd"),
    }
    _require(set(found) == set(expected), "GameplayEventWindow set changed")
    for key, values in expected.items():
        actual = found[key]
        _require(actual[2] == values[2] and all(abs(actual[i] - values[i]) <= 0.000001 for i in (0, 1)),
                 "GameplayEventWindow time/tag changed: " + key)


def _sound_sources(ue, assets):
    duplicates = []
    unresolved = []
    for asset in assets:
        for event in ue.AnimationLibrary.get_animation_notify_events(asset):
            notify = event.get_editor_property("Notify")
            if notify is None or notify.get_class().get_path_name() != PLAY_SOUND_CLASS:
                continue
            sound = notify.get_editor_property("Sound")
            _require(sound is not None, "existing PlaySound has a null Sound: " + _path(notify))
            same_source = _package(sound) == SOUND
            if isinstance(sound, ue.SoundWave):
                data = ue.find_object(sound, "AssetImportData")
                _require(isinstance(data, ue.AssetImportData), "existing SoundWave AssetImportData subobject missing/wrong type: " + _path(sound))
                filenames = list(data.extract_filenames())
                _require(bool(filenames), "existing SoundWave import filenames missing: " + _path(sound))
                for filename in filenames:
                    file = Path(filename)
                    _require(file.is_absolute() and file.is_file(),
                             "existing SoundWave provenance cannot be checked: " + filename)
                    same_source = same_source or file.resolve() == SOURCE_WAV.resolve() or _sha(file) == SOURCE_WAV_SHA256
            else:
                unresolved.append({"notify": _path(notify), "sound": _path(sound),
                                   "reason": "non-SoundWave graph needs Audio/native source check"})
            if same_source:
                duplicates.append({"asset": _path(asset), "notify": _path(notify), "sound": _path(sound)})
    return {"same_source_events": duplicates, "unresolved_source_graphs": unresolved}


def _capture(ue, expected_montage_sha256, expected_sound_sha256, params):
    disk = {MONTAGE: _sha(_package_file(MONTAGE)), SOUND: _sha(_package_file(SOUND)),
            MAIN: _sha(_package_file(MAIN)), END: _sha(_package_file(END))}
    _require(disk[MONTAGE] == expected_montage_sha256, "Montage SHA256 differs from frozen baseline")
    _require(disk[SOUND] == expected_sound_sha256, "SoundWave SHA256 differs from Audio handoff")
    _require(_sha(SOURCE_WAV) == SOURCE_WAV_SHA256, "source WAV SHA256 changed")
    assets = []
    for path, cls in ((MONTAGE, ue.AnimMontage), (SOUND, ue.SoundWave), (MAIN, ue.AnimSequence), (END, ue.AnimSequence)):
        asset = ue.load_asset(path)
        _require(isinstance(asset, cls) and _package(asset) == path, "missing/wrong asset type: " + path)
        assets.append(asset)
    montage, sound, main, end = assets
    skeleton = montage.get_editor_property("Skeleton")
    _require(skeleton is not None, "Montage Skeleton missing")
    _require(main.get_editor_property("Skeleton") == skeleton and end.get_editor_property("Skeleton") == skeleton,
             "Main/End/Montage Skeleton mismatch")
    skeleton_package = _package(skeleton)
    disk[skeleton_package] = _sha(_package_file(skeleton_package))
    _require(not sound.get_editor_property("bLooping"), "SoundWave is looping; native PlaySound requires one-shot")
    imported = ue.find_object(sound, "AssetImportData")
    _require(isinstance(imported, ue.AssetImportData), "target SoundWave AssetImportData subobject missing/wrong type: " + _path(sound))
    filenames = list(imported.extract_filenames())
    _require(len(filenames) == 1 and Path(filenames[0]).is_absolute()
             and Path(filenames[0]).resolve() == SOURCE_WAV.resolve(), "SoundWave import source differs from Audio source")
    dirty = _dirty(ue)
    _require(not set(disk).intersection(dirty["content"] + dirty["maps"]), "protected package is dirty")
    snap = _montage(ue, montage)
    _windows(snap)
    sources = {path: {"path": _path(obj), "events": _events(ue, obj),
                      "skeleton": _path(obj.get_editor_property("Skeleton"))}
               for path, obj in ((MAIN, main), (END, end))}
    return assets, {"montage": snap, "source_sequences": sources, "disk_sha256": disk,
                    "dirty": dirty, "audio_parameters": params,
                    "sound_import_filenames": filenames, "sound_looping": False,
                    "source_sound_check": _sound_sources(ue, (montage, main, end))}


def _unchanged(ue, before, assets, allow_montage_save=False):
    now = _montage(ue, assets[0])
    for key, value in before["montage"].items():
        if key not in ("events", "notify_tracks"):
            _require(now[key] == value, "protected Montage field changed: " + key)
    for guid, event in before["montage"]["events"].items():
        _require(now["events"].get(guid) == event, "original Notify changed/removed: " + guid)
    for path, obj in ((MAIN, assets[2]), (END, assets[3])):
        actual = {"path": _path(obj), "events": _events(ue, obj),
                  "skeleton": _path(obj.get_editor_property("Skeleton"))}
        _require(actual == before["source_sequences"][path], "source sequence readback changed: " + path)
    for package, sha in before["disk_sha256"].items():
        if not (allow_montage_save and package == MONTAGE):
            _require(_sha(_package_file(package)) == sha, "protected disk hash changed: " + package)
    _require(_sha(SOURCE_WAV) == SOURCE_WAV_SHA256, "source WAV changed during entry")
    return now


def _new_event(snapshot, before, params):
    added = set(snapshot["events"]) - set(before["montage"]["events"])
    _require(len(added) == 1 and len(snapshot["events"]) == len(before["montage"]["events"]) + 1,
             "expected exactly one appended Notify")
    _require(snapshot["notify_tracks"] == before["montage"]["notify_tracks"] + [TRACK],
             "expected exactly one appended audio track")
    event = snapshot["events"][next(iter(added))]
    notify = event["notify"]
    _require(event["state"] is None and notify is not None and notify["class"] == PLAY_SOUND_CLASS,
             "new event is not the native one-shot PlaySound Notify")
    _require(notify["sound"] == SOUND + "." + SOUND.rsplit("/", 1)[1], "new Sound reference incorrect")
    _require(abs(event["trigger_seconds"] - TIME) <= 0.000001 and event["duration_seconds"] == 0.0,
             "new PlaySound event timing/duration incorrect")
    for key in PARAM_PROPERTIES:
        actual, expected = notify["audio_parameters"][key], params[key]
        if key in ("volume_multiplier", "pitch_multiplier"):
            _require(abs(float(actual) - expected) <= 0.000001, "new Audio parameter differs: " + key)
        else:
            _require(actual == expected, "new Audio parameter differs: " + key)
    return event


def _compare_readback_point_event(expected, actual):
    """Compare the observed ordinary event; retain raw exports and derived delta.

    Native FAnimNotifyEvent::GetEndTriggerTime returns GetTriggerTime when
    NotifyStateClass is null (UE 5.8 AnimTypes.cpp:86-98). This rule is restricted
    to the original Normal01 event and the observed 0 -> 0.000100 transition.
    It neither normalizes an asset nor permits other payload/offset changes.
    """
    comparison = {
        "guid": expected["guid"],
        "before_raw_record": expected,
        "after_raw_record": actual,
        "raw_records_identical": expected == actual,
        "derived_field_difference": None,
        "comparison_rule": "exact_except_observed_ordinary_notify_unused_end_offset",
    }
    if expected == actual:
        return comparison
    point_guid = "A88EF5894349502A9527A2AF5905D5BF"
    _require(expected["guid"] == actual["guid"] == point_guid,
             "EndOffset rule only permits the original Normal01 PlaySound GUID")
    for record in (expected, actual):
        notify = record["notify"]
        _require(record["state"] is None and record["duration_seconds"] == 0.0
                 and notify is not None and notify["class"] == PLAY_SOUND_CLASS
                 and notify["sound"] == SOUND + "." + SOUND.rsplit("/", 1)[1],
                 "EndOffset rule requires the original zero-duration non-State native PlaySound")
        _require(",NotifyStateClass=None,Duration=0.000000,EndLink=" in record["event_export"],
                 "EndOffset rule requires unchanged raw non-State/zero Duration fields")
    expected_fields = {k: v for k, v in expected.items() if k != "event_export"}
    actual_fields = {k: v for k, v in actual.items() if k != "event_export"}
    _require(expected_fields == actual_fields, "saved Notify structured fields differ from wire")

    # The native export puts these two scalar fields first. Anchor here to avoid
    # matching a nested EndLink or a quoted object path. Every remaining byte of
    # the export (including real TriggerTimeOffset, links and flags) stays exact.
    pattern = r"^\(TriggerTimeOffset=[^,()]+,(EndTriggerTimeOffset=([^,()]+),)"
    projected = []
    offset_values = []
    for record in (expected, actual):
        exported = record["event_export"]
        match = re.match(pattern, exported)
        _require(match is not None, "EndOffset field is not in the proven native export layout")
        projected.append(exported[:match.start(1)] + exported[match.end(1):])
        offset_values.append(match.group(2))
    _require(offset_values == ["0.000000", "0.000100"],
             "EndOffset rule rejects an unobserved offset value/direction")
    _require(projected[0] == projected[1], "saved Notify export has another field difference")
    comparison["derived_field_difference"] = {
        "field": "EndTriggerTimeOffset",
        "before_raw_value": offset_values[0],
        "after_raw_value": offset_values[1],
        "consumed_for_this_event": False,
        "reason": "NotifyStateClass=null: native GetEndTriggerTime returns GetTriggerTime",
        "native_contract": "UE_5.8/Engine/Source/Runtime/Engine/Private/Animation/AnimTypes.cpp:86-98",
        "effective_end_seconds_by_native_contract": {
            "before": expected["trigger_seconds"], "after": actual["trigger_seconds"],
        },
        "executed_refresh_callback_proven": False,
    }
    return comparison


def _compare_readback_montage(expected, actual, expected_new_event):
    """Retain exact Montage/original-event checks around one scoped point rule."""
    _require({k: v for k, v in expected.items() if k != "events"}
             == {k: v for k, v in actual.items() if k != "events"},
             "saved Montage non-event fields differ from wire report")
    _require(set(expected["events"]) == set(actual["events"]),
             "saved Montage Notify GUID set differs from wire report")
    new_guid = expected_new_event["guid"]
    _require(expected["events"].get(new_guid) == expected_new_event,
             "wire report new event disagrees with its post-save Montage snapshot")
    for guid, event in expected["events"].items():
        if guid != new_guid:
            _require(actual["events"][guid] == event, "original Notify differs on readback: " + guid)
    return _compare_readback_point_event(expected_new_event, actual["events"][new_guid])


def _publish(ue, mode, report, report_path):
    if report_path is not None:
        destination = Path(report_path).resolve()
        expected = (PROJECT / "Saved" / "ValidationRecords" / REPORT_NAMES[mode]).resolve()
        _require(destination == expected, "report path outside this entry's bounded output")
        _require(not destination.exists(), "report already exists; preserve history: " + str(destination))
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("x", encoding="utf-8", newline="\n") as output:
            json.dump(report, output, ensure_ascii=False, indent=2, allow_nan=False)
            output.write("\n")
    ue.log("PYRIOS_NORMAL01_NOTIFY " + json.dumps({"mode": mode, "status": report["status"],
                                                 "phase": report["phase"]}))


def _run(mode, *, expected_montage_sha256, expected_sound_sha256, audio_parameters,
         baseline=None, report_path=None, coordinator_reload_evidence=None):
    import unreal as ue

    report = {"schema": "PyriosNormal01SoundNotify/v1", "mode": mode, "phase": "parameter_validation",
              "status": "running", "montage": MONTAGE, "sound": SOUND,
              "project_initial_frame": 2, "fps": 60, "time_seconds": TIME,
              "original_game_timing_known": False, "playback_test_performed": False,
              "new_cpp_or_ga_chain_verified": False, "mutation_started": False, "save_succeeded": False}
    try:
        _require(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() == PROJECT.resolve(),
                 "wrong UE project")
        montage_sha = _digest(expected_montage_sha256, "expected_montage_sha256")
        sound_sha = _digest(expected_sound_sha256, "expected_sound_sha256")
        params = _params(audio_parameters)
        # Validate output before any mutation; do not discover a report conflict after save.
        if report_path is not None:
            destination = Path(report_path).resolve()
            _require(destination == (PROJECT / "Saved" / "ValidationRecords" / REPORT_NAMES[mode]).resolve()
                     and not destination.exists(), "report path invalid or existing history")
        report["phase"] = "asset_audit"
        dirty_before_loading = _dirty(ue)
        assets, captured = _capture(ue, montage_sha, sound_sha, params)
        _require(captured["dirty"] == dirty_before_loading, "asset loading changed dirty package set")
        report["captured"] = captured
        report["native_sections_verified_by_script"] = captured["montage"]["sections"]["native_data_readable"]
        report["required_coordinator_checks"] = []
        if not report["native_sections_verified_by_script"]:
            report["required_coordinator_checks"].append(captured["montage"]["sections"]["required_coordinator_check"])
        unknown_objects = [r["path"] for records in
                           [captured["montage"]["events"]] + [s["events"] for s in captured["source_sequences"].values()]
                           for event in records.values() for r in (event["notify"], event["state"])
                           if r is not None and r.get("object_properties_not_enumerated")]
        if unknown_objects:
            report["required_coordinator_checks"].append(
                "Native property preservation for unenumerated original Notify objects: " + ", ".join(unknown_objects))
        if mode in ("audit", "wire"):
            check = captured["source_sound_check"]
            _require(not check["same_source_events"], "duplicate source sound Notify: " + json.dumps(check["same_source_events"]))
            _require(not check["unresolved_source_graphs"], "source sound identity unresolved: " + json.dumps(check["unresolved_source_graphs"]))
            _require(TRACK not in captured["montage"]["notify_tracks"], "audio track already exists; wire refuses duplicate/replacement")
        if mode == "audit":
            _require(_unchanged(ue, captured, assets) == captured["montage"], "audit Montage snapshot changed")
            _require(_dirty(ue) == dirty_before_loading, "audit changed dirty package set")
            report["status"] = "asset_preflight_passed_native_and_playback_checks_separate"
        elif mode == "wire":
            # Final guards immediately before the only mutation sequence.
            _unchanged(ue, captured, assets)
            _require(_dirty(ue) == captured["dirty"], "dirty set changed before mutation")
            report["phase"] = "append_native_notify"
            report["mutation_started"] = True
            ue.AnimationLibrary.add_animation_notify_track(assets[0], TRACK)
            notify = ue.AnimationLibrary.add_animation_notify_event(assets[0], TRACK, TIME, ue.AnimNotify_PlaySound)
            _require(notify is not None and notify.get_outer() == assets[0], "native Notify creation/outer invalid")
            notify.set_editor_property("Sound", assets[1])
            for key, prop in PARAM_PROPERTIES.items():
                notify.set_editor_property(prop, params[key])
            now = _unchanged(ue, captured, assets)
            report["new_event"] = _new_event(now, captured, params)
            dirty = _dirty(ue)
            _require(dirty["maps"] == captured["dirty"]["maps"]
                     and set(dirty["content"]) - {MONTAGE} == set(captured["dirty"]["content"]),
                     "mutation dirtied an unrelated package")
            report["phase"] = "save_only_montage"
            _require(ue.EditorAssetLibrary.save_loaded_asset(assets[0], only_if_is_dirty=False), "Montage save returned false")
            report["save_succeeded"] = True
            report["saved_montage_sha256"] = _sha(_package_file(MONTAGE))
            report["phase"] = "post_save_loaded_object_checks"
            after = _unchanged(ue, captured, assets, allow_montage_save=True)
            _require(_new_event(after, captured, params) == report["new_event"], "new event changed on save")
            _require(_dirty(ue) == captured["dirty"], "post-save dirty set differs")
            report["after_montage"] = after
            report["status"] = "saved_requires_coordinator_fresh_reload_and_playback"
        elif mode == "readback":
            _require(isinstance(baseline, dict) and baseline.get("mode") == "wire"
                     and baseline.get("status") == "saved_requires_coordinator_fresh_reload_and_playback"
                     and baseline.get("save_succeeded") is True, "readback requires successful wire report")
            _require(baseline["saved_montage_sha256"] == montage_sha, "readback SHA differs from wire saved SHA")
            _require(baseline["captured"]["audio_parameters"] == params, "Audio handoff differs from wire")
            for path, sha in baseline["captured"]["disk_sha256"].items():
                if path != MONTAGE:
                    _require(captured["disk_sha256"].get(path) == sha, "protected baseline hash changed: " + path)
            before = baseline["captured"]
            now = _unchanged(ue, before, assets, allow_montage_save=True)
            new_event = _new_event(now, before, params)
            _require(new_event["guid"] == baseline["new_event"]["guid"], "saved Notify GUID differs from wire")
            report["readback_event_comparison"] = _compare_readback_montage(
                baseline["after_montage"], now, baseline["new_event"])
            duplicates = captured["source_sound_check"]
            _require(len(duplicates["same_source_events"]) == 1
                     and duplicates["same_source_events"][0]["asset"] == now["path"]
                     and not duplicates["unresolved_source_graphs"], "readback source sound count/identity incorrect")
            _require(_dirty(ue) == dirty_before_loading, "readback changed dirty package set")
            if coordinator_reload_evidence is not None:
                _require(isinstance(coordinator_reload_evidence, str) and coordinator_reload_evidence.strip(),
                         "coordinator_reload_evidence must identify actual reload evidence")
                report["coordinator_supplied_reload_evidence"] = coordinator_reload_evidence
            report["fresh_reload_performed_by_script"] = False
            report["status"] = "loaded_object_semantic_readback_passed_playback_unverified"
        else:
            _require(False, "unknown mode: " + str(mode))
        report["phase"] = "complete"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        report["dirty_on_failure"] = _dirty(ue)
        ue.log_error("Animation Normal01 [%s] phase=%s: %s" % (MONTAGE, report["phase"], error))
        _publish(ue, mode, report, report_path)
        raise
    _publish(ue, mode, report, report_path)
    return report


def audit(**kwargs):
    """Asset-read-only preflight. Requires frozen SoundWave and explicit Audio handoff."""
    return _run("audit", **kwargs)


def wire(**kwargs):
    """Coordinator's exclusive asset window only: append once and save only Montage."""
    return _run("wire", **kwargs)


def readback(**kwargs):
    """Asset-read-only comparison to wire report; coordinator separately reloads from disk."""
    return _run("readback", **kwargs)
