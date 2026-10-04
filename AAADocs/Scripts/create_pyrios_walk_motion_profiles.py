"""Prepare seven fixed locomotion Profiles through the native authoring contract.

Importing this file performs no UE operations or writes. The completed Start
failure/R1 and Loop receipts remain bound to their actual historical script.
The coordinator calls each remaining fixed entry separately after that history
passes; existing reports refuse overwrite and no automatic batch is provided.
Each call owns at most one target package. Failed and ExistingMatched never
save; CreatedUnsaved saves that exact Package, scans that exact .uasset, then
requires native ExistingMatched and complete same-process readback.

The fresh native Snapshot DTO and its duration_seconds are passed unchanged to
CreateOrInspectProfile. JSON is used only for evidence/comparison/reporting:
no curve reconstruction, manifest duration, external curve, asset overwrite,
MovementSet wiring, SaveAll, retry, rollback or cold-read claim is provided.
If a step fails after native creation/save, preserve its actual pending/saved
state and diagnostic. An already completed WalkStart is never rolled back.
"""

import hashlib
import json
import math
from pathlib import Path
import re
import struct


PROJECT = Path("F:/ue_project/GGYGO")
EVIDENCE = PROJECT / "Saved/ValidationRecords/LocomotionAssetReadback_20261003_Pawn00.json"
EVIDENCE_SHA256 = "159c5b59079f6d88860a07c2e3699755435f6eaef0b9f1828d55735f46a345a2"
MOVEMENT = "/Game/Characters/Player/Pyrios/Animation/Movement/"
PROFILE_CLASS = "/Script/GGYGO.GGYGOLocomotionMotionProfile"
CURVES = ("RootMotion_Speed", "RootMotion_DirX", "RootMotion_DirY", "RootMotion_Yaw")
FLOAT_FIELDS = ("time", "value", "arrive_tangent", "leave_tangent",
                "arrive_tangent_weight", "leave_tangent_weight")
INT_FIELDS = ("interp_mode", "tangent_mode", "tangent_weight_mode")
PROFILE_CURVES = ("speed_curve", "direction_x_curve", "direction_y_curve", "yaw_curve")
STEPS = {
    "WalkStart": {"source": MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Walk_Start",
                  "target": MOVEMENT + "Profiles/DA_LocomotionMotionProfile_Pyrios_WalkStart",
                  "movement_set_property": "WalkStartProfile", "loop": False},
    "WalkLoop": {"source": MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Walk_Loop",
                 "target": MOVEMENT + "Profiles/DA_LocomotionMotionProfile_Pyrios_WalkLoop",
                 "movement_set_property": "WalkLoopProfile", "loop": True},
    "RunLoop": {"source": MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Run_Loop",
                "target": MOVEMENT + "Profiles/DA_LocomotionMotionProfile_Pyrios_RunLoop",
                "movement_set_property": "RunLoopProfile", "loop": True},
    "StartStop": {"source": MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Walk_Start_End",
                  "target": MOVEMENT + "Profiles/DA_LocomotionMotionProfile_Pyrios_StartStop",
                  "movement_set_property": "StartStopProfile", "loop": False},
    "WalkStop": {"source": MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Walk_End",
                 "target": MOVEMENT + "Profiles/DA_LocomotionMotionProfile_Pyrios_WalkStop",
                 "movement_set_property": "WalkStopProfile", "loop": False},
    "RunStop": {"source": MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Run_End",
                "target": MOVEMENT + "Profiles/DA_LocomotionMotionProfile_Pyrios_RunStop",
                "movement_set_property": "RunStopProfile", "loop": False},
    "TurnBack": {"source": MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_TurnBack",
                 "target": MOVEMENT + "Profiles/DA_LocomotionMotionProfile_Pyrios_TurnBack",
                 "movement_set_property": "TurnBackProfile", "loop": False},
}
REMAINING_STEPS = ("RunLoop", "StartStop", "WalkStop", "RunStop", "TurnBack")
REPORTS = {step: PROJECT / ("Saved/ValidationRecords/Pyrios%sMotionProfile_20261004_Result.json" % step)
           for step in STEPS}
START_FAILED_SHA256 = "1b7c55003547c6a6084bc766774f93d611d8c941e9ed7cbfc088d1b0893b841a"
START_SAVED_SHA256 = "288c5aa32276089c0c40cff78a736070e01f2c5a0fb9aa7e4faf945ee6f81561"
START_R1_REPORT = PROJECT / "Saved/ValidationRecords/PyriosWalkStartMotionProfile_20261004_Readback_R1.json"
WALK_HISTORY_SCRIPT_SHA256 = "080d2dc76f63f4b6b141369c24bf87459669f57002272e85831c43c6fdafb85c"
START_R1_SHA256 = "3400b670c757eb3041388345522b984654baaeb120168f44a217a06b1163deb2"
LOOP_REPORT_SHA256 = "e0e6ea2e94f229de84f0d976ed6cd013102e74acae464f81c7786082582ba7ff"
LOOP_SAVED_SHA256 = "d76850a65914dfd90da6f9f60e98c92e34ce2daf708c575bb2b1b1fde19f3ad1"
WALK_ROOT_ACCEPTANCE = PROJECT / "Saved/ValidationRecords/PyriosWalkLoopMotionProfile_20261004_RootAcceptance.json"
WALK_ROOT_ACCEPTANCE_SHA256 = "3ca377496fa96786816015473d5100b9ef94466ecbcdd80c9dc8fa98eb91a35d"


def _require(condition, reason):
    if not condition:
        raise RuntimeError("[GGYGOEditor.WalkProfileScript] " + reason)


def _object_path(package):
    _require(package.startswith("/Game/") and "." not in package and ":" not in package,
             "invalid fixed package path: " + package)
    return package + "." + package.rsplit("/", 1)[1]


def _file(package):
    _object_path(package)
    return PROJECT / "Content" / (package[6:] + ".uasset")


def _sha(path):
    _require(path.is_file(), "required file missing: " + str(path))
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _file_state(path):
    _require(not path.exists() or path.is_file(), "file/directory conflict: " + str(path))
    return _sha(path) if path.is_file() else None


def _bits(value):
    if type(value) is float:
        return {"pythonBinary64LittleEndian": struct.pack("<d", value).hex()}
    if isinstance(value, dict):
        return {k: _bits(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_bits(v) for v in value]
    return value


def _snapshot_sha(payload):
    encoded = json.dumps(_bits(payload), ensure_ascii=False, sort_keys=True,
                         separators=(",", ":"), allow_nan=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _float(value, width, label):
    _require(type(value) is float and math.isfinite(value), "invalid native float: " + label)
    if width == 32:
        widened = struct.unpack("<f", struct.pack("<f", value))[0]
        _require(struct.pack("<d", widened) == struct.pack("<d", value),
                 "float32 widening lost bits: " + label)
    return value


def _int(value, label):
    _require(type(value) is int and -(2 ** 31) <= value < 2 ** 31, "invalid native int32: " + label)
    return value


def _curve(ue, dto, source_curve, label):
    cls = ue.GGYGOFloatCurveSnapshot if source_curve else ue.GGYGOLocomotionRichCurveReadback
    _require(isinstance(dto, cls), "wrong native curve DTO: " + label)
    _require(isinstance(dto.keys, ue.Array) and len(dto.keys) > 0, "empty/wrong key array: " + label)
    result = {
        "default_value": _float(dto.default_value, 32, label + ".default_value"),
        "pre_infinity_extrap": _int(dto.pre_infinity_extrap, label + ".pre"),
        "post_infinity_extrap": _int(dto.post_infinity_extrap, label + ".post"),
        "keys": [],
    }
    if source_curve:
        _require(isinstance(dto.name, ue.Name), "wrong native curve Name: " + label)
        result.update(name=str(dto.name), flags=_int(dto.flags, label + ".flags"))
    else:
        _require(type(dto.has_external_curve) is bool, "invalid external curve flag: " + label)
        result["has_external_curve"] = dto.has_external_curve
    for index, key in enumerate(dto.keys):
        _require(isinstance(key, ue.GGYGOFloatCurveKeySnapshot), "wrong key DTO: " + label)
        prefix = label + ".keys[%d]." % index
        values = {f: _float(getattr(key, f), 32, prefix + f) for f in FLOAT_FIELDS}
        values.update({f: _int(getattr(key, f), prefix + f) for f in INT_FIELDS})
        result["keys"].append(values)
    return result


def _snapshot(ue, dto, source_object):
    _require(isinstance(dto, ue.GGYGOFloatCurveReadResult), "wrong native Snapshot result type")
    _require(type(dto.succeeded) is bool and type(dto.error) is str, "invalid Snapshot status/error fields")
    _require(dto.succeeded and not dto.error, "native Snapshot failed: " + dto.error)
    duration = _float(dto.duration_seconds, 64, "Snapshot.duration_seconds")
    _require(duration > 0 and isinstance(dto.curves, ue.Array) and len(dto.curves) == 4,
             "invalid successful Snapshot duration/curve count")
    curves = [_curve(ue, c, True, source_object + "." + CURVES[i]) for i, c in enumerate(dto.curves)]
    _require(tuple(c["name"] for c in curves) == CURVES, "Snapshot curve names/order changed")
    payload = {"objectPath": source_object, "duration_seconds": duration, "curves": curves}
    roundtrip = json.loads(json.dumps(payload, ensure_ascii=False, allow_nan=False))
    _require(_bits(roundtrip) == _bits(payload), "JSON changed Snapshot bits")
    return payload


def _profile_readback(ue, dto, source_payload, loop):
    _require(isinstance(dto, ue.GGYGOLocomotionProfileReadback), "wrong native Profile readback type")
    _require(type(dto.loop) is bool and type(dto.source_asset_identifier) is str
             and type(dto.source_fingerprint) is str, "invalid Profile identity/configuration fields")
    actual = {
        "duration": _float(dto.duration, 32, "Profile.duration"), "loop": dto.loop,
        "source_asset_identifier": dto.source_asset_identifier,
        "source_fingerprint": dto.source_fingerprint,
        "curves": [_curve(ue, getattr(dto, f), False, "Profile." + f) for f in PROFILE_CURVES],
    }
    _require(re.fullmatch(r"locomotion-richcurve-v1:blake3-256:[0-9a-f]{64}", actual["source_fingerprint"]),
             "native SourceFingerprint format invalid")
    expected_curves = []
    for source_curve in source_payload["curves"]:
        expected_curves.append({**{k: v for k, v in source_curve.items() if k not in ("name", "flags")},
                                "has_external_curve": False})
    expected = {
        "duration": struct.unpack("<f", struct.pack("<f", source_payload["duration_seconds"]))[0],
        "loop": loop, "source_asset_identifier": source_payload["objectPath"],
        # Native authoring owns the BLAKE3 computation and verifies its value.
        # Python checks its format here and exact stability in the second call.
        "source_fingerprint": actual["source_fingerprint"], "curves": expected_curves,
    }
    _require(_bits(actual) == _bits(expected), "Profile full fields/bits differ from fresh Snapshot")
    return actual


def _evidence():
    _require(_sha(EVIDENCE) == EVIDENCE_SHA256, "frozen complete evidence hash changed")
    document = json.loads(EVIDENCE.read_text(encoding="utf-8-sig"))
    full = document["fullSnapshotReadback"]
    _require(full["complete"] is True and full["status"] == "complete_readback_only"
             and full["snapshotCallCount"] == 7 and len(full["snapshots"]) == 7 and not full["errors"],
             "complete seven-source evidence unavailable")
    entries = {}
    for entry in full["snapshots"]:
        payload = entry["payload"]
        path = entry["sourceObjectPath"]
        _require(payload["objectPath"] == _object_path(path) and path not in entries and entry["status"] == "read",
                 "evidence source path/status conflict: " + path)
        sha = entry["sourceAssetSha256Before"]
        _require(re.fullmatch(r"[0-9a-f]{64}", sha) and sha == entry["sourceAssetSha256After"]
                 == entry["sourceAssetSha256Final"], "source hash evidence incomplete: " + path)
        _require(_snapshot_sha(payload) == entry["fullSnapshotSha256"], "complete Snapshot evidence digest invalid: " + path)
        _require(_sha(_file(path)) == sha, "source disk hash differs from evidence: " + path)
        entries[path] = entry
    suggestions = {s["movementSetProperty"]: s for s in document["profileSuggestions"]}
    _require(len(suggestions) == len(document["profileSuggestions"]) == len(STEPS),
             "formal seven-Profile evidence mapping is incomplete/duplicated")
    for spec in STEPS.values():
        _require(spec["source"] in entries, "fixed source missing from complete evidence")
        suggested = suggestions[spec["movement_set_property"]]
        _require(suggested["sourceObjectPath"] == spec["source"]
                 and suggested["suggestedProfileObjectPath"] == spec["target"]
                 and suggested["loop"] is spec["loop"], "fixed Profile mapping differs from frozen evidence")
    return document, entries


def _dirty(ue):
    utils = ue.EditorLoadingAndSavingUtils
    return {"content": sorted(p.get_path_name() for p in utils.get_dirty_content_packages()),
            "maps": sorted(p.get_path_name() for p in utils.get_dirty_map_packages())}


def _protection(document, entries, active_target):
    packages = set(entries)
    for core in document["currentAssets"]["core"]:
        path = core["objectPath"]
        _require(_sha(_file(path)) == core["fileSha256"], "core asset hash differs from frozen evidence: " + path)
        packages.add(path)
    for suggested in document["profileSuggestions"]:
        packages.add(suggested["suggestedProfileObjectPath"])
    packages.discard(active_target)
    files = {str(_file(p)): _file_state(_file(p)) for p in sorted(packages)}
    files[str(EVIDENCE)] = _sha(EVIDENCE)
    return packages, files


def _check_files(files):
    for path, expected in files.items():
        _require(_file_state(Path(path)) == expected, "protected file/presence changed: " + path)


def _disk_asset_data(ue, registry, target):
    data = registry.k2_get_asset_by_object_path(ue.SoftObjectPath(_object_path(target)), True, True)
    _require(ue.AssetRegistryHelpers.is_valid(data), "disk-only AssetData missing: " + target)
    full_name = ue.AssetRegistryHelpers.get_full_name(data)
    _require(full_name == PROFILE_CLASS + " " + _object_path(target), "disk AssetData path/class mismatch: " + full_name)
    _require(str(data.package_name) == target and str(data.asset_name) == target.rsplit("/", 1)[1],
             "disk AssetData package/object mismatch")
    return {"full_name": full_name, "package_name": str(data.package_name),
            "asset_name": str(data.asset_name), "include_only_on_disk_assets": True}


def _saved_start_failure():
    """Require this exact partial-save history; never reinterpret it as passed."""
    path = REPORTS["WalkStart"]
    _require(_sha(path) == START_FAILED_SHA256, "original WalkStart failure history changed")
    failed = json.loads(path.read_text(encoding="utf-8"))
    spec = STEPS["WalkStart"]
    _require(failed["status"] == "failed" and failed["phase"] == "exact_file_registry_scan"
             and failed["step"] == "WalkStart" and failed["initial_native_status"] == "CreatedUnsaved"
             and failed["package_save_called"] is True and failed["package_save_succeeded"] is True
             and failed["same_process_full_readback_passed"] is False,
             "original report is not the frozen saved-but-registry-failed Start")
    _require(failed["target_object_path"] == _object_path(spec["target"])
             and failed["source_object_path"] == _object_path(spec["source"])
             and failed["loop"] is False and failed["evidence_sha256"] == EVIDENCE_SHA256
             and failed["target_sha256_after"] == START_SAVED_SHA256,
             "original saved Start identity/evidence/hash differs")
    _require(_sha(_file(spec["target"])) == START_SAVED_SHA256,
             "saved Start disk package changed/missing; read-only R1 refuses creation/save")
    _require(_sha(_file(spec["source"])) == failed["source_sha256"],
             "WalkStart source changed after original save")
    return failed



def _start_receipt():
    path = START_R1_REPORT
    _require(path.is_file(), "WalkLoop requires the actual successful WalkStart receipt first")
    _require(_sha(path) == START_R1_SHA256, "frozen successful Start R1 report changed")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    start = STEPS["WalkStart"]
    _require(receipt["status"] == "passed" and receipt["step"] == "WalkStart"
             and receipt["mode"] == "readback_saved_walk_start_r1"
             and receipt["package_save_called"] is False and receipt["package_save_succeeded"] is False
             and receipt["original_failed_report_sha256"] == START_FAILED_SHA256
             and receipt["final_native_status"] == "ExistingMatched"
             and receipt["same_process_full_readback_passed"] is True
             and receipt["target_object_path"] == _object_path(start["target"]), "WalkStart receipt did not pass")
    _require(receipt["script_sha256"] == WALK_HISTORY_SCRIPT_SHA256
             and receipt["evidence_sha256"] == EVIDENCE_SHA256,
             "WalkStart historical script/evidence contract differs")
    _saved_start_failure()
    _require(receipt["target_sha256_after"] == START_SAVED_SHA256, "R1 receipt saved Start hash differs")
    _require(_sha(_file(start["target"])) == receipt["target_sha256_after"]
             and _sha(_file(start["source"])) == receipt["source_sha256"], "WalkStart source/target changed after acceptance")
    return {"path": str(path), "sha256": _sha(path), "target_sha256": receipt["target_sha256_after"]}


def _accepted_walk_history():
    """Protect accepted historical receipts/packages without rerunning either asset."""
    start = _start_receipt()
    path = REPORTS["WalkLoop"]
    _require(_sha(path) == LOOP_REPORT_SHA256, "frozen successful WalkLoop report changed")
    receipt = json.loads(path.read_text(encoding="utf-8"))
    spec = STEPS["WalkLoop"]
    _require(receipt["status"] == "passed" and receipt["phase"] == "complete"
             and receipt["step"] == "WalkLoop" and receipt["loop"] is True
             and receipt["initial_native_status"] == "CreatedUnsaved"
             and receipt["final_native_status"] == "ExistingMatched"
             and receipt["package_save_called"] is True and receipt["package_save_succeeded"] is True
             and receipt["same_process_full_readback_passed"] is True,
             "WalkLoop history is not the actual accepted one-package save/readback")
    _require(receipt["script_sha256"] == WALK_HISTORY_SCRIPT_SHA256
             and receipt["evidence_sha256"] == EVIDENCE_SHA256
             and receipt["source_object_path"] == _object_path(spec["source"])
             and receipt["target_object_path"] == _object_path(spec["target"])
             and receipt["walk_start_receipt"] == start,
             "WalkLoop historical script/evidence/source/target/Start binding differs")
    _require(receipt["target_sha256_after"] == LOOP_SAVED_SHA256
             and _sha(_file(spec["target"])) == LOOP_SAVED_SHA256
             and _sha(_file(spec["source"])) == receipt["source_sha256"],
             "accepted WalkLoop source/target disk hash changed")
    _require(_sha(WALK_ROOT_ACCEPTANCE) == WALK_ROOT_ACCEPTANCE_SHA256,
             "frozen root Walk acceptance changed/missing")
    acceptance = json.loads(WALK_ROOT_ACCEPTANCE.read_text(encoding="utf-8"))
    _require(acceptance["scriptSHA256"].lower() == WALK_HISTORY_SCRIPT_SHA256
             and acceptance["reportSHA256"].lower() == LOOP_REPORT_SHA256
             and acceptance["targetSHA256"].lower() == LOOP_SAVED_SHA256
             and acceptance["StartR1ReportSHA256"].lower() == START_R1_SHA256
             and acceptance["StartSavedHashPreserved"] is True
             and acceptance["StartOriginalFailurePreserved"] is True
             and acceptance["assetWriteWindowClosed"] is True,
             "root acceptance is not bound to the frozen actual Walk history")
    protected = {
        str(REPORTS["WalkStart"]): START_FAILED_SHA256,
        str(START_R1_REPORT): START_R1_SHA256,
        str(_file(STEPS["WalkStart"]["target"])): START_SAVED_SHA256,
        str(path): LOOP_REPORT_SHA256,
        str(_file(spec["target"])): LOOP_SAVED_SHA256,
        str(WALK_ROOT_ACCEPTANCE): WALK_ROOT_ACCEPTANCE_SHA256,
    }
    _check_files(protected)
    return {"history_script_sha256": WALK_HISTORY_SCRIPT_SHA256,
            "walk_start_receipt": start, "protected_files": protected}


def _status(ue, result):
    _require(isinstance(result, ue.GGYGOLocomotionProfileAuthorResult), "wrong native author result type")
    _require(type(result.error) is str, "invalid native author Error type")
    enum = ue.GGYGOLocomotionProfileAuthorStatus
    for value, label in ((enum.FAILED, "Failed"), (enum.CREATED_UNSAVED, "CreatedUnsaved"),
                         (enum.EXISTING_MATCHED, "ExistingMatched")):
        if result.status == value:
            return label
    _require(False, "unknown native author status")


def _native(ue, source, snapshot, spec, report, label):
    # Pass the original DTO and its actual double duration; never rebuild curves.
    result = ue.GGYGOLocomotionMotionProfileAuthorLibrary.create_or_inspect_profile(
        source, _object_path(spec["source"]), snapshot, _object_path(spec["target"]),
        snapshot.duration_seconds, spec["loop"])
    status = _status(ue, result)
    report[label + "_native_status"] = status
    report[label + "_native_error"] = result.error
    _require(status != "Failed", "native CreateOrInspectProfile failed: " + result.error)
    _require(not result.error, "successful native author result contains Error: " + result.error)
    profile = result.profile
    _require(isinstance(profile, ue.GGYGOLocomotionMotionProfile)
             and profile.get_path_name() == _object_path(spec["target"])
             and profile.get_class().get_path_name() == PROFILE_CLASS, "native Profile identity/type mismatch")
    return result, status


def _publish(report, output):
    _require(not output.exists(), "preserve existing report history: " + str(output))
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("x", encoding="utf-8", newline="\n") as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write("\n")


def _run(step):
    import unreal as ue

    spec, output = STEPS[step], REPORTS[step]
    _require(not output.exists(), "fixed report already exists; no operation/overwrite: " + str(output))
    report = {"schema": "PyriosWalkProfileAuthoring/v1", "step": step, "status": "running",
              "phase": "preflight", "source_object_path": _object_path(spec["source"]),
              "target_object_path": _object_path(spec["target"]), "loop": spec["loop"],
              "movement_set_property": spec["movement_set_property"],
              "package_save_called": False, "package_save_succeeded": False,
              "same_process_full_readback_passed": False, "cold_read_performed": False,
              "movement_set_writes": False, "production_walk_or_run_verified": False}
    protected = None
    try:
        _require(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() == PROJECT.resolve(),
                 "wrong UE project")
        report["script_sha256"] = _sha(Path(__file__))
        document, entries = _evidence()
        report["evidence_sha256"] = EVIDENCE_SHA256
        if step == "WalkLoop":
            report["walk_start_receipt"] = _start_receipt()
        elif step in REMAINING_STEPS:
            report["accepted_walk_history"] = _accepted_walk_history()
        protected_packages, protected = _protection(document, entries, spec["target"])
        if step == "WalkLoop":
            protected[str(START_R1_REPORT)] = report["walk_start_receipt"]["sha256"]
            protected[str(REPORTS["WalkStart"])] = START_FAILED_SHA256
        elif step in REMAINING_STEPS:
            protected.update(report["accepted_walk_history"]["protected_files"])
        protected[str(Path(__file__))] = report["script_sha256"]
        report["protected_files_before"] = protected
        dirty_before = _dirty(ue)
        report["dirty_before"] = dirty_before
        _require(not (protected_packages | {spec["target"]}).intersection(dirty_before["content"] + dirty_before["maps"]),
                 "source/core/other Profile/target package is dirty")
        target_file = _file(spec["target"])
        target_before = _file_state(target_file)
        report["target_sha256_before"] = target_before
        ue.load_module("GGYGOEditor")
        registry = ue.AssetRegistryHelpers.get_asset_registry()
        _require(callable(registry.k2_get_asset_by_object_path)
                 and callable(registry.scan_files_synchronous), "required exact Registry API unavailable")
        _require(callable(ue.GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot)
                 and callable(ue.GGYGOLocomotionMotionProfileAuthorLibrary.create_or_inspect_profile)
                 and callable(ue.EditorLoadingAndSavingUtils.save_packages), "required native API unavailable")
        source = ue.load_asset(_object_path(spec["source"]))
        _require(isinstance(source, ue.AnimSequence) and source.get_path_name() == _object_path(spec["source"]),
                 "source type/identity mismatch")
        report["phase"] = "fresh_complete_snapshot"
        snapshot = ue.GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot(source, [ue.Name(n) for n in CURVES])
        report["snapshot_native_error"] = snapshot.error
        payload = _snapshot(ue, snapshot, _object_path(spec["source"]))
        evidence = entries[spec["source"]]
        _require(_bits(payload) == _bits(evidence["payload"]), "fresh Snapshot fields/bits differ from frozen complete evidence")
        report["source_snapshot"] = payload
        report["source_snapshot_sha256"] = _snapshot_sha(payload)
        report["source_sha256"] = evidence["sourceAssetSha256Before"]
        _check_files(protected)
        _require(_dirty(ue) == dirty_before, "source load/Snapshot changed dirty packages")
        report["phase"] = "native_create_or_inspect"
        result, status = _native(ue, source, snapshot, spec, report, "initial")
        initial_readback = _profile_readback(ue, result.readback, payload, spec["loop"])
        report["initial_full_profile_readback"] = initial_readback
        package = result.profile.get_outermost()
        _require(isinstance(package, ue.Package) and package.get_path_name() == spec["target"]
                 and result.profile.get_outer() == package, "returned Profile/Package identity mismatch")
        _check_files(protected)
        if status == "CreatedUnsaved":
            _require(target_before is None and not target_file.exists(), "new target disk package became occupied")
            expected_dirty = {"content": sorted(dirty_before["content"] + [spec["target"]]), "maps": dirty_before["maps"]}
            _require(_dirty(ue) == expected_dirty, "CreatedUnsaved dirty delta is not exactly its target package")
            report["phase"] = "save_exact_package"
            report["package_save_called"] = True
            # SaveLoadedAsset's AssetRegistry registration gate is intentionally
            # not used. Native creation returns the exact unsaved Package.
            _require(ue.EditorLoadingAndSavingUtils.save_packages([package], True), "save_packages returned false")
            report["package_save_succeeded"] = True
        else:
            _require(status == "ExistingMatched" and target_before is not None
                     and _sha(target_file) == target_before and _dirty(ue) == dirty_before,
                     "ExistingMatched is not a clean unchanged persisted target; no save permitted")
        report["target_sha256_after"] = _sha(target_file)
        _require(_dirty(ue) == dirty_before, "post-save/inspection dirty set differs")
        _check_files(protected)
        report["phase"] = "exact_file_registry_scan"
        registry = ue.AssetRegistryHelpers.get_asset_registry()
        registry.scan_files_synchronous([str(target_file)], True)
        report["registry_scan_files"] = [str(target_file)]
        report["disk_asset_data"] = _disk_asset_data(ue, registry, spec["target"])
        report["phase"] = "native_existing_matched_readback"
        final, final_status = _native(ue, source, snapshot, spec, report, "final")
        _require(final_status == "ExistingMatched", "post-save native readback did not return ExistingMatched")
        final_readback = _profile_readback(ue, final.readback, payload, spec["loop"])
        _require(_bits(final_readback) == _bits(initial_readback), "complete native Profile readback changed after save/scan")
        report["final_full_profile_readback"] = final_readback
        _require(_sha(target_file) == report["target_sha256_after"], "target disk hash changed during readback")
        _require(_dirty(ue) == dirty_before, "final readback changed dirty packages")
        _check_files(protected)
        report["same_process_full_readback_passed"] = True
        report["status"], report["phase"] = "passed", "complete"
    except Exception as error:
        report["status"] = "failed"
        report["error"] = str(error)
        report["dirty_on_failure"] = _dirty(ue)
        failed_target = _file(spec["target"])
        report["target_disk_state_on_failure"] = {
            "exists": failed_target.exists(), "is_file": failed_target.is_file(),
        }
        ue.log_error("[GGYGOEditor.WalkProfileScript] step=%s source=%s target=%s phase=%s: %s" % (
            step, report["source_object_path"], report["target_object_path"], report["phase"], error))
        _publish(report, output)
        raise
    _publish(report, output)
    ue.log("PYRIOS_WALK_PROFILE " + json.dumps({"step": step, "status": report["status"],
                                             "report": str(output), "cold_read_performed": False}))
    return report


def readback_walk_start_r1():
    """Coordinator's fixed saved-Start R1: inspect only, no asset creation/save."""
    import unreal as ue

    spec, output = STEPS["WalkStart"], START_R1_REPORT
    _require(not output.exists(), "preserve existing R1 report history: " + str(output))
    report = {
        "schema": "PyriosWalkProfileAuthoring/v1", "step": "WalkStart",
        "mode": "readback_saved_walk_start_r1", "status": "running", "phase": "preflight",
        "source_object_path": _object_path(spec["source"]),
        "target_object_path": _object_path(spec["target"]), "loop": False,
        "package_save_called": False, "package_save_succeeded": False,
        "same_process_full_readback_passed": False, "cold_read_performed": False,
        "movement_set_writes": False, "production_walk_or_run_verified": False,
    }
    try:
        _require(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir())).resolve() == PROJECT.resolve(),
                 "wrong UE project")
        failed = _saved_start_failure()
        report["original_failed_report_path"] = str(REPORTS["WalkStart"])
        report["original_failed_report_sha256"] = START_FAILED_SHA256
        report["original_failure_error"] = failed["error"]
        report["script_sha256"] = _sha(Path(__file__))
        document, entries = _evidence()
        report["evidence_sha256"] = EVIDENCE_SHA256
        packages, protected = _protection(document, entries, spec["target"])
        packages.add(spec["target"])
        protected[str(_file(spec["target"]))] = START_SAVED_SHA256
        protected[str(REPORTS["WalkStart"])] = START_FAILED_SHA256
        protected[str(Path(__file__))] = report["script_sha256"]
        report["protected_files_before"] = protected
        before = _dirty(ue)
        report["dirty_before"] = before
        _require(not packages.intersection(before["content"] + before["maps"]),
                 "read-only R1 protected source/core/Profile package is dirty")
        report["target_sha256_before"] = START_SAVED_SHA256
        ue.load_module("GGYGOEditor")
        registry = ue.AssetRegistryHelpers.get_asset_registry()
        _require(callable(registry.k2_get_asset_by_object_path)
                 and callable(registry.scan_files_synchronous), "required exact Registry API unavailable")
        # Preload the frozen persisted target and keep its reference alive.
        # The native call must inspect this same object and return ExistingMatched.
        existing = ue.load_asset(_object_path(spec["target"]))
        _require(isinstance(existing, ue.GGYGOLocomotionMotionProfile)
                 and existing.get_path_name() == _object_path(spec["target"])
                 and existing.get_class().get_path_name() == PROFILE_CLASS,
                 "saved Start object missing/wrong type; R1 refuses creation")
        source = ue.load_asset(_object_path(spec["source"]))
        _require(isinstance(source, ue.AnimSequence) and source.get_path_name() == _object_path(spec["source"]),
                 "WalkStart source type/identity mismatch")
        _require(_dirty(ue) == before, "saved target/source loading changed dirty set")
        _check_files(protected)
        report["phase"] = "fresh_complete_snapshot"
        snapshot = ue.GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot(
            source, [ue.Name(name) for name in CURVES])
        report["snapshot_native_error"] = snapshot.error
        payload = _snapshot(ue, snapshot, _object_path(spec["source"]))
        _require(_bits(payload) == _bits(entries[spec["source"]]["payload"])
                 == _bits(failed["source_snapshot"]),
                 "fresh complete Start Snapshot differs from frozen evidence/original save")
        report["source_snapshot"] = payload
        report["source_snapshot_sha256"] = _snapshot_sha(payload)
        report["source_sha256"] = failed["source_sha256"]
        _require(_dirty(ue) == before, "fresh R1 Snapshot changed dirty set")
        _check_files(protected)
        report["phase"] = "native_existing_matched_readback"
        result, status = _native(ue, source, snapshot, spec, report, "final")
        _require(status == "ExistingMatched" and result.profile == existing,
                 "R1 must inspect the existing saved Start; no new target is accepted")
        readback = _profile_readback(ue, result.readback, payload, False)
        _require(_bits(readback) == _bits(failed["initial_full_profile_readback"]),
                 "saved Start full Profile bits differ from original native readback")
        report["final_full_profile_readback"] = readback
        _require(_dirty(ue) == before, "native R1 inspection changed dirty set")
        _check_files(protected)
        report["phase"] = "exact_file_registry_readback"
        target_file = _file(spec["target"])
        registry.scan_files_synchronous([str(target_file)], True)
        report["registry_scan_files"] = [str(target_file)]
        report["disk_asset_data"] = _disk_asset_data(ue, registry, spec["target"])
        _require(_dirty(ue) == before, "Registry R1 readback changed dirty set")
        _check_files(protected)
        report["target_sha256_after"] = _sha(target_file)
        _require(report["target_sha256_after"] == START_SAVED_SHA256, "R1 changed saved Start disk hash")
        report["same_process_full_readback_passed"] = True
        report["status"], report["phase"] = "passed", "complete"
    except Exception as error:
        report["status"], report["error"] = "failed", str(error)
        report["dirty_on_failure"] = _dirty(ue)
        ue.log_error("[GGYGOEditor.WalkProfileScript] saved Start R1 phase=%s: %s" % (report["phase"], error))
        _publish(report, output)
        raise
    _publish(report, output)
    ue.log("PYRIOS_WALK_START_R1 " + json.dumps({"status": report["status"], "report": str(output),
                                              "package_save_called": False, "cold_read_performed": False}))
    return report



def create_walk_start():
    """Coordinator's first asset lease: only WalkStart, non-looping."""
    return _run("WalkStart")


def create_walk_loop():
    """Coordinator's next asset lease: only WalkLoop, after actual Start success."""
    return _run("WalkLoop")


def create_run_loop():
    """Coordinator's single RunLoop target; requires frozen accepted Walk history."""
    return _run("RunLoop")


def create_start_stop():
    """Coordinator's single StartStop target; requires frozen accepted Walk history."""
    return _run("StartStop")


def create_walk_stop():
    """Coordinator's single WalkStop target; requires frozen accepted Walk history."""
    return _run("WalkStop")


def create_run_stop():
    """Coordinator's single RunStop target; requires frozen accepted Walk history."""
    return _run("RunStop")


def create_turn_back():
    """Coordinator's single TurnBack target; requires frozen accepted Walk history."""
    return _run("TurnBack")
