"""Append the explicitly selected project FX window to the existing Normal01.

Run in a full Unreal Editor after the FX/Combo/Tag/Notify DLL is ready. Audit,
apply and fresh-process readback share actual asset snapshots. This entry never
rebuilds Montages or changes source animation, combat windows or playback rules.
Missing native property access fails before mutation; it is not a successful
partial audit. Window seconds are project settings, not recovered game frames.
"""
import argparse
import json
import math
import os
import re
import shutil
from pathlib import Path


PROJECT = Path(__file__).resolve().parents[2]
MONTAGE = "/Game/Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_Normal_01"
TRACK = "FXWindow"
BEGIN = "Event.Montage.FXWindowBegin"
END = "Event.Montage.FXWindowEnd"
WINDOW_CLASS = "/Script/GGYGO.GGYGOAnimNotifyState_GameplayEventWindow"
ORIGIN_KEY = "GGYGO.FXWindow.Origin"
ORIGIN = "project_test; original_game_timing_unknown"
SCHEMA = "PyriosNormal01FXWindow/v1"
EPSILON = 0.000001
# UE 5.8 AnimNotifyState.h declares this bit on an editable uint8. The enum
# itself is not BlueprintType, so do not assume a generated Python enum exists.
NO_MERGE_FLAG = 1


def require(condition, reason):
    if not condition:
        raise RuntimeError("Animation Normal01 FX window: " + reason)


def saved_path(value):
    path = (PROJECT / value).resolve()
    require(path.is_relative_to((PROJECT / "Saved").resolve()), "output must be inside Saved: " + str(path))
    return path


def disk_file(package):
    require(package.startswith("/Game/"), "unexpected source package: " + package)
    return PROJECT / "Content" / (package[6:] + ".uasset")


def digest(path):
    import hashlib
    require(path.is_file(), "required package file missing: " + str(path))
    with path.open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest().upper()


def dirty(ue):
    return {"content": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_content_packages()),
            "maps": sorted(p.get_path_name() for p in ue.EditorLoadingAndSavingUtils.get_dirty_map_packages())}


def object_path(obj):
    return obj.get_path_name() if obj is not None else None


def notify_object(obj):
    if obj is None:
        return None
    cls = obj.get_class().get_path_name()
    result = {"path": obj.get_path_name(), "class": cls}
    if cls == WINDOW_CLASS:
        result.update(begin=obj.get_editor_property("begin_event_tag").export_text(),
                      end=obj.get_editor_property("end_event_tag").export_text(),
                      behavior_flags=int(obj.get_editor_property("notify_state_behavior_flags")))
    elif cls == "/Script/Engine.AnimNotify_PlaySound":
        result["sound"] = object_path(obj.get_editor_property("sound"))
        for prop in ("VolumeMultiplier", "PitchMultiplier", "bFollow", "bPreviewIgnoreAttenuation"):
            result[prop] = obj.get_editor_property(prop)
        result["attach_name"] = str(obj.get_editor_property("attach_name"))
    elif cls == "/Script/AnimGraphRuntime.AnimNotify_PlayMontageNotify":
        result["notify_name"] = str(obj.get_editor_property("notify_name"))
    else:
        raise RuntimeError("Animation Normal01 FX window: original Notify configuration needs its native author audit: "
                           + result["path"] + " class=" + cls)
    return result


def events(ue, asset):
    result = {}
    for event in ue.AnimationLibrary.get_animation_notify_events(asset):
        exported = event.export_text()
        match = re.search(r"(?:^|[,\(])Guid=([0-9A-Fa-f]{32})(?:[,\)])", exported)
        require(match is not None, "unreadable Notify GUID: " + asset.get_path_name())
        guid = match.group(1).upper()
        require(guid not in result, "duplicate Notify GUID: " + guid)
        track = re.search(r"(?:^|[,\(])TrackIndex=(\d+)(?:[,\)])", exported)
        require(track is not None, "Notify track index unreadable: " + guid)
        result[guid] = {"export": exported,
                        "time": float(ue.AnimationLibrary.get_anim_notify_event_trigger_time(event)),
                        "duration": float(ue.AnimationLibrary.get_anim_notify_event_duration(event)),
                        "track_index": int(track.group(1)),
                        "tick_type": str(event.get_editor_property("montage_tick_type")),
                        "notify": notify_object(event.get_editor_property("notify")),
                        "state": notify_object(event.get_editor_property("notify_state_class"))}
    return result


def native_text_parts(text):
    """Keep native Section records and owned subobject bodies without inventing defaults."""
    sections = {}
    children = {}
    stack = []
    for line in text.splitlines():
        begin = re.match(r'^\s*Begin Object\b.*?\bName="([^"]+)"', line)
        if begin:
            for item in stack:
                item[1].append(line)
            stack.append([begin.group(1), [line]])
            continue
        if re.match(r"^\s*End Object\s*$", line):
            require(bool(stack), "unbalanced native object export")
            name, body = stack.pop()
            body.append(line)
            if stack:
                key = "/".join([item[0] for item in stack] + [name])
                children.setdefault(key, []).append("\n".join(body))
                for item in stack:
                    item[1].append(line)
            continue
        for item in stack:
            item[1].append(line)
        if len(stack) == 1:
            section = re.match(r"^\s*CompositeSections\((\d+)\)=(.*)$", line)
            if section:
                index = int(section.group(1))
                require(index not in sections, "duplicate native Section export")
                sections[index] = section.group(2)
    require(not stack and sorted(sections) == [0, 1], "native export lacks the exact Main/End Section pair")
    return [sections[i] for i in (0, 1)], children


def native_sections(ue, montage, filename):
    # The stock UObjectExporterT3D exports native properties, including protected
    # Section links. This is the chosen author audit route, not an error fallback
    # from an incomplete Python property snapshot.
    require(not filename.exists(), "native export already exists: " + str(filename))
    task = ue.AssetExportTask()
    task.set_editor_property("object", montage)
    task.set_editor_property("exporter", ue.ObjectExporterT3D())
    task.set_editor_property("filename", str(filename))
    task.set_editor_property("automated", True)
    task.set_editor_property("prompt", False)
    task.set_editor_property("replace_identical", False)
    require(ue.Exporter.run_asset_export_task(task) and filename.is_file(), "native Montage text export failed")
    text = filename.read_text(encoding="utf-8-sig")
    require(re.search(r'^Begin Object Class=/Script/Engine.AnimMontage Name="' + re.escape(montage.get_name()) + '"', text),
            "native export is not the target Montage")
    raw_sections, children = native_text_parts(text)
    # CompositeSection is not a script exposed struct. Native T3D omits values
    # equal to the struct constructor: its FAnimLinkableElement base is shared
    # with the publicly wrapped AnimNotifyEvent. Read those actual base defaults
    # from a native event, rather than assuming an absent time/enum is readable.
    base_defaults = ue.AnimNotifyEvent().export_text()
    sections = []
    for index, raw in enumerate(raw_sections):
        name = re.search(r'(?:^|[,\(])SectionName="([^"]+)"(?:[,\)])', raw)
        require(name is not None and name.group(1) == str(montage.get_section_name(index)), "native Section name/getter disagree")
        next_name = re.search(r'(?:^|[,\(])NextSectionName="([^"]+)"(?:[,\)])', raw)
        require(next_name is not None or "NextSectionName=" not in raw, "unreadable explicit native NextSectionName")
        # FCompositeSection's native constructor initializes NextSectionName to
        # NAME_None; omission by this native exporter denotes that exact value.
        sections.append({"name": name.group(1), "next": next_name.group(1) if next_name else "None",
                         "time": section_time(raw, base_defaults)})
    return sections, raw_sections, children


def section_time(exported, native_defaults):
    def field(name):
        pattern = r"(?:^|[,\(])" + name + r"=([^,\)]+)(?:[,\)])"
        actual = re.findall(pattern, exported)
        if actual:
            require(len(actual) == 1, "ambiguous Section field: " + name)
            return actual[0]
        values = re.findall(pattern, native_defaults)
        require(bool(values), "native link constructor default unavailable: " + name)
        return values[-1]  # Last is the inherited main link, after EndLink.
    require(field("LinkMethod") == "Absolute",
            "Section time requires an actual absolute native link, not an inferred segment time")
    value = float(field("LinkValue"))
    require(math.isfinite(value), "nonfinite Section link time")
    return value


def capture(ue, start, end, export_file, *, authored_target_pending=False):
    montage = ue.load_asset(MONTAGE)
    require(isinstance(montage, ue.AnimMontage), "required existing Montage missing/wrong type: " + MONTAGE)
    length = float(montage.get_play_length())
    require(math.isfinite(length) and 0 <= start < end < length, "project window outside actual Montage length")
    skeleton = montage.get_editor_property("skeleton")
    require(skeleton is not None, "Montage Skeleton missing")
    slots = montage.get_editor_property("slot_anim_tracks")
    require(len(slots) == 1 and str(slots[0].get_editor_property("slot_name")) == "FullBody", "expected original FullBody slot")
    segments = slots[0].get_editor_property("anim_track").get_editor_property("anim_segments")
    require(len(segments) == 2, "expected original Main/End source pair")
    sections, section_exports, native_children = native_sections(ue, montage, export_file)
    require(len(sections) == 2 and [s["name"] for s in sections] == ["Main", "End"],
            "expected original Main/End Sections")
    require([s["next"] for s in sections] == ["End", "None"], "original Section links differ")
    starts = [s["time"] for s in sections]
    require(abs(starts[0]) <= EPSILON and end < starts[1], "project FX window must be inside the actual Main section")
    sources = {}
    source_disk = {skeleton.get_outermost().get_path_name(): digest(disk_file(skeleton.get_outermost().get_path_name()))}
    for index, segment in enumerate(segments):
        sequence = segment.get_editor_property("anim_reference")
        require(isinstance(sequence, ue.AnimSequence), "source is not an original AnimSequence")
        require(sequence.get_editor_property("skeleton") == skeleton, "source/Skeleton mismatch: " + sequence.get_path_name())
        source_length = float(sequence.get_play_length())
        values = {name: float(segment.get_editor_property(name)) for name in
                  ("start_pos", "anim_start_time", "anim_end_time", "anim_play_rate", "looping_count")}
        rate = float(sequence.get_editor_property("rate_scale"))
        require(all(math.isfinite(v) for v in [source_length, rate, *values.values()]) and source_length > 0,
                "invalid original segment/source domain")
        require(abs(values["start_pos"] - starts[index]) <= EPSILON and abs(values["anim_start_time"]) <= EPSILON
                and abs(values["anim_end_time"] - source_length) <= EPSILON
                and values["anim_play_rate"] == 1 and values["looping_count"] == 1 and rate == 1,
                "original full source/forward rate contract differs: " + sequence.get_path_name())
        package = sequence.get_outermost().get_path_name()
        require(package not in sources, "Main and End require distinct original sequences")
        source_disk[package] = digest(disk_file(package))
        sources[package] = {"length": source_length, "rate": rate, "skeleton": skeleton.get_path_name(), "events": events(ue, sequence)}
    require(abs(length - starts[1] - list(sources.values())[1]["length"]) <= EPSILON, "Montage does not retain the full native End clip")
    blend_in = montage.get_editor_property("blend_in")
    blend_out = montage.get_editor_property("blend_out")
    blend_seconds = float(blend_out.get_editor_property("blend_time"))
    trigger = float(montage.get_editor_property("blend_out_trigger_time"))
    require(math.isfinite(trigger) and math.isfinite(blend_seconds) and 0 <= blend_seconds < length, "invalid native BlendOut settings")
    natural_start = length - (blend_seconds if trigger < 0 else trigger)
    require(end < natural_start, "project window reaches the actual natural BlendOut boundary")
    require(bool(montage.get_editor_property("bEnableAutoBlendOut")) and not montage.get_editor_property("bLoop")
            and float(montage.get_editor_property("rate_scale")) == 1, "original natural playback/rate contract differs")
    snapshot = {"path": montage.get_path_name(), "length": length, "skeleton": skeleton.get_path_name(),
                "slots": [s.export_text() for s in slots], "sections": section_exports,
                "native_notify_subobjects": native_children,
                "sources": sources, "source_disk_sha256": source_disk,
                "blend_in": blend_in.export_text(), "blend_out": blend_out.export_text(),
                "blend_out_trigger_time": trigger, "natural_blend_out_start": natural_start,
                "auto_blend_out": True, "loop": False, "rate_scale": 1.0,
                "tracks": [str(v) for v in ue.AnimationLibrary.get_animation_notify_track_names(montage)],
                "events": events(ue, montage),
                "metadata": {str(k): str(v) for k, v in ue.EditorAssetLibrary.get_metadata_tag_values(montage).items()}}
    require(len({n.casefold() for n in snapshot["tracks"]}) == len(snapshot["tracks"]), "duplicate original Notify track names")
    protected = set(source_disk)
    if not authored_target_pending:
        protected.add(MONTAGE)
    require(not protected.intersection(dirty(ue)["content"] + dirty(ue)["maps"]), "an involved package is dirty")
    return montage, snapshot


def configured_fx(snapshot, start, end, flag, queued):
    matches = []
    for guid, event in snapshot["events"].items():
        state = event["state"]
        if state is not None and state["class"] == WINDOW_CLASS and (BEGIN in state["begin"] or END in state["end"]):
            matches.append((guid, event))
    track_matches = [i for i, name in enumerate(snapshot["tracks"]) if name.casefold() == TRACK.casefold()]
    if not matches:
        require(not track_matches and ORIGIN_KEY not in snapshot["metadata"], "conflicting existing FX track/origin without a declared window")
        return None
    require(len(matches) == 1 and len(track_matches) == 1, "duplicate/conflicting declared FX window or track")
    guid, event = matches[0]
    state = event["state"]
    require(state["begin"] == '(TagName="' + BEGIN + '")' and state["end"] == '(TagName="' + END + '")'
            and event["notify"] is None and event["track_index"] == track_matches[0]
            and event["tick_type"] == queued and state["behavior_flags"] == flag
            and abs(event["time"] - start) <= EPSILON and abs(event["duration"] - (end - start)) <= EPSILON
            and snapshot["metadata"].get(ORIGIN_KEY) == ORIGIN,
            "existing FX declaration differs; replacement/retiming is not authorized")
    require(state["path"].startswith(snapshot["path"] + ":"), "FX window is not owned by this Montage")
    return guid


def appended_only(before, after, guid):
    require(after["tracks"] == before["tracks"] + [TRACK], "original Notify tracks changed")
    require(set(after["events"]) == set(before["events"]) | {guid} and guid not in before["events"], "not exactly one appended Notify")
    for old_guid, old_event in before["events"].items():
        require(after["events"][old_guid] == old_event, "original Notify changed: " + old_guid)
    expected_metadata = dict(before["metadata"], **{ORIGIN_KEY: ORIGIN})
    require(after["metadata"] == expected_metadata, "unrelated asset metadata changed")
    for key, body in before["native_notify_subobjects"].items():
        require(after["native_notify_subobjects"].get(key) == body, "original native subobject changed: " + key)
    added_objects = set(after["native_notify_subobjects"]) - set(before["native_notify_subobjects"])
    expected_object = after["events"][guid]["state"]["path"].rsplit(":", 1)[1]
    require(added_objects == {before["path"].rsplit(".", 1)[1] + "/" + expected_object}, "unexpected added native subobjects")
    for key in before:
        if key not in ("tracks", "events", "metadata", "native_notify_subobjects"):
            require(after[key] == before[key], "protected asset/source field changed: " + key)


def run(mode, *, start_seconds, end_seconds, record, baseline=None, backup_dir=None):
    import unreal as ue
    require(mode in ("audit", "apply", "readback"), "unknown mode")
    require(all(type(v) in (int, float) and math.isfinite(v) for v in (start_seconds, end_seconds))
            and 0 <= start_seconds < end_seconds, "explicit finite ordered project seconds required")
    output = saved_path(record)
    require(not output.exists(), "result already exists; preserve history: " + str(output))
    require((mode == "audit" and baseline is None and backup_dir is None)
            or (mode == "apply" and baseline is not None and backup_dir is not None)
            or (mode == "readback" and baseline is not None and backup_dir is None), "mode/baseline/backup arguments disagree")
    result = {"schema": SCHEMA, "mode": mode, "pid": os.getpid(), "success": False,
              "project_test_only": True, "original_game_timing_known": False,
              "playback_verified": False, "montage": MONTAGE, "start_seconds": start_seconds,
              "end_seconds": end_seconds, "saved_packages": [], "phase": "preflight"}
    try:
        require(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() == PROJECT, "wrong native UE project")
        require(not re.search(r"(?:^|\s)-run=", ue.SystemLibrary.get_command_line(), re.I), "requires full Editor, not Commandlet")
        levels = ue.get_editor_subsystem(ue.LevelEditorSubsystem)
        require(levels is not None and not levels.is_in_play_in_editor(), "requires inactive PIE")
        require(ue.SystemLibrary.get_engine_version().startswith("5.8."), "native constructor/export contract is scoped to UE 5.8")
        flag = NO_MERGE_FLAG
        queued = str(ue.AnimNotifyEvent().get_editor_property("montage_tick_type"))
        tags = []
        for name in (BEGIN, END):
            tag = ue.GameplayTag()
            tag.import_text('(TagName="' + name + '")')
            require(ue.GameplayTagLibrary.is_gameplay_tag_valid(tag)
                    and str(ue.GameplayTagLibrary.get_tag_name(tag)) == name, "native Tag not registered: " + name)
            tags.append(tag)
        original_dirty = dirty(ue)
        export_dir = output.with_suffix("")
        require(not export_dir.exists(), "native export directory already exists")
        export_dir.mkdir(parents=True)
        result["native_export_dir"] = str(export_dir)
        montage, before = capture(ue, start_seconds, end_seconds, export_dir / "before.t3d")
        require(dirty(ue) == original_dirty, "loading changed dirty package set")
        current_hash = digest(disk_file(MONTAGE))
        guid = configured_fx(before, start_seconds, end_seconds, flag, queued)
        result.update(snapshot=before, montage_disk_sha256=current_hash, dirty_before=original_dirty, fx_guid=guid)
        prior = None
        if baseline is not None:
            prior = json.loads(saved_path(baseline).read_text(encoding="utf-8-sig"))
            require(prior.get("schema") == SCHEMA and prior.get("success") is True
                    and prior.get("mode") == ("audit" if mode == "apply" else "apply")
                    and prior.get("start_seconds") == start_seconds and prior.get("end_seconds") == end_seconds,
                    "baseline is not the successful matching authoring phase")
            require(prior["snapshot"] == before and prior["montage_disk_sha256"] == current_hash, "actual asset differs from baseline")
        if mode == "apply" and guid is None:
            destination = saved_path(backup_dir)
            require(not destination.exists(), "backup directory already exists")
            destination.mkdir(parents=True)
            backup = destination / disk_file(MONTAGE).name
            shutil.copy2(disk_file(MONTAGE), backup)
            require(digest(backup) == current_hash, "original Montage backup differs")
            result["backup"] = str(backup)
            # No external UE call intervenes between this audit and authoring.
            require(dirty(ue) == original_dirty, "dirty set changed before mutation")
            result["phase"] = "append_window"
            ue.AnimationLibrary.add_animation_notify_track(montage, TRACK)
            window = ue.AnimationLibrary.add_animation_notify_state_event(
                montage, TRACK, start_seconds, end_seconds - start_seconds, ue.GGYGOAnimNotifyState_GameplayEventWindow)
            require(window is not None and window.get_outer() == montage, "native Notify creation/outer invalid")
            window.set_editor_property("begin_event_tag", tags[0])
            window.set_editor_property("end_event_tag", tags[1])
            window.set_editor_property("notify_state_behavior_flags", flag)
            # Native AddAnimationNotifyStateEvent constructs Queued. Validate its
            # actual event below; do not replace the full original Notify array.
            ue.EditorAssetLibrary.set_metadata_tag(montage, ORIGIN_KEY, ORIGIN)
            pending_dirty = dirty(ue)
            require(set(pending_dirty["content"]) - {MONTAGE} == set(original_dirty["content"])
                    and pending_dirty["maps"] == original_dirty["maps"], "authoring dirtied another package")
            _, after = capture(ue, start_seconds, end_seconds, export_dir / "pending.t3d", authored_target_pending=True)
            guid = configured_fx(after, start_seconds, end_seconds, flag, queued)
            require(guid is not None, "native new FX window not readable")
            appended_only(before, after, guid)
            result["phase"] = "save_one_montage"
            require(ue.EditorAssetLibrary.save_loaded_asset(montage, only_if_is_dirty=True), "native Montage save failed")
            result["saved_packages"] = [MONTAGE]
            _, saved = capture(ue, start_seconds, end_seconds, export_dir / "saved.t3d")
            require(saved == after and dirty(ue) == original_dirty, "save changed asset contract or dirty set")
            result.update(snapshot=saved, montage_disk_sha256=digest(disk_file(MONTAGE)), fx_guid=guid)
            result["status"] = "one_fx_window_saved_cold_and_playback_pending"
        else:
            if mode == "readback":
                require(prior["pid"] != os.getpid(), "cold read requires a new native Editor process")
                require(guid is not None, "saved FX window missing")
            require(dirty(ue) == original_dirty and digest(disk_file(MONTAGE)) == current_hash, "readonly mode changed asset/dirty set")
            result["status"] = "cold_readback_passed_playback_pending" if mode == "readback" else (
                "existing_matching_fx_preserved" if guid is not None else "actual_asset_audit_passed")
        result.update(success=True, phase="complete", dirty_after=dirty(ue))
    except Exception as error:
        result["error"] = str(error)
        raise
    finally:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("x", encoding="utf-8", newline="\n") as target:
            json.dump(result, target, ensure_ascii=False, indent=2, allow_nan=False)
            target.write("\n")
        summary = {key: result[key] for key in ("mode", "pid", "phase", "success", "saved_packages")}
        summary.update(record=str(output), project_test_only=True, original_game_timing_known=False)
        for key in ("status", "error", "fx_guid"):
            if key in result:
                summary[key] = result[key]
        ue.log("PYRIOS_NORMAL01_FX_WINDOW " + json.dumps(summary, ensure_ascii=False, allow_nan=False))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("audit", "apply", "readback"), required=True)
    parser.add_argument("--start-seconds", type=float, required=True)
    parser.add_argument("--end-seconds", type=float, required=True)
    parser.add_argument("--record", required=True)
    parser.add_argument("--baseline")
    parser.add_argument("--backup-dir")
    options = parser.parse_args()
    run(options.mode, start_seconds=options.start_seconds, end_seconds=options.end_seconds,
        record=options.record, baseline=options.baseline, backup_dir=options.backup_dir)
