# -*- coding: utf-8 -*-
"""C23 / R3-P: one-source, complete public Snapshot DTO Python probe.

The coordinator must first confirm the latest build's new DLL and the actual C20
GGYGO.Editor.Animation.FloatCurveSnapshot success from that same build, with that UE process exited.
Only the coordinator may run this script in its exclusive UE window:
  F:/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe
  F:/ue_project/GGYGO/GGYGO.uproject -run=pythonscript
  -script=F:/ue_project/GGYGO/AAADocs/Scripts/probe_animation_float_curve_snapshot.py
  -EnablePlugins=PythonScriptPlugin -Unattended -NoSplash -NoSound -NullRHI
  -NoP4 -NoTurnkey -log=GGYGO_AnimationCurveSnapshot_Python_20261001_R3.log

Exactly two Snapshot calls: expected null-source rejection, then Walk_Start
and its four complete curves. Public exported names are fixed, never aliases.
No R1 tuple, Controller, Model access, sampling, setters, transactions or saves.
The only runtime file written is the new fixed JSON, created exclusively.
Old R2 evidence and all assets remain protected. Exceptions never mean success.

Naming: UE5.8 PyGenUtil.cpp:1951/3298 strips b before uppercase and snake-cases
properties; PyWrapperTypeRegistry.cpp:2250 registers that name as the getter.
Thus bSucceeded is succeeded. PyGenUtil.cpp:1152 packs a single Struct without
the bool/out-parameter None branch. PyConversion.cpp:154 widens native float
and preserves double via PyFloat_FromDouble. These are static API grounds;
only the actual run proves this DLL's public Python transport. C20 provides
the independent native Model-to-DTO comparison, not a second Python reader.
"""

import datetime
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import traceback


PROJECT_ROOT = Path("F:/ue_project/GGYGO")
REPORT_PATH = PROJECT_ROOT / "Saved/AnimationCurveReadback/ReadFloatCurveSnapshot_Python_20261001_R3.json"
LOG_PATH = PROJECT_ROOT / "Saved/Logs/GGYGO_AnimationCurveSnapshot_Python_20261001_R3.log"
SOURCE_PATH = (
    "/Game/Characters/Player/Pyrios/Animation/Movement/"
    "Avatar_Male_Size03_Pyrois_Ani_Walk_Start"
)
CURVE_NAMES = ("RootMotion_Speed", "RootMotion_DirX", "RootMotion_DirY", "RootMotion_Yaw")
NULL_ERROR = "ReadFloatCurves[<null-or-invalid>]: Source is null or invalid."
MOVEMENT = "Content/Characters/Player/Pyrios/Animation/Movement/"
PROTECTED_SHA256 = {
    "Content/BP/Anim/ABP_Pyrios.uasset": "48EE112C9E9BDA3EC22317F0D3A55C9545D19E36B17193AFD7859C0657E26359",
    MOVEMENT + "BS_Pyrios_WalkRun.uasset": "7B76721AD1BCC79B5FF03473C5098478369B3B901408CB55D69B87AC1294922E",
    "Content/System/DA_Movement_Default.uasset": "7943CDC3A9F761386EEB08E4D9785E4B98121CAB5D5FA45C4AE7A5ED8A01F678",
    MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Walk_Start.uasset": "A0F957803207E8BB53DB0CD2333F19E183B60BEFB4E3DA747B432CFA5952818D",
    MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Walk_Loop.uasset": "CA56C5DF7F1F1B7282780610E5F9BCB0C28E203086A603D9F3AC02FE80D936BA",
    MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Run_Loop.uasset": "922D51C476D9C93A4F5733FAF5E3E977F5B37D934DE85A007622AC3730CA3E88",
    MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Walk_Start_End.uasset": "4059B9A4615C9E4E4D4A3CE4E610D32B1754DD0EAF25FBBA730E9D395FB91976",
    MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Walk_End.uasset": "1DE5B73B22B0553E18823F9012BEEB4011CA730614032DA9DCDF3EC3A0B99227",
    MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_Run_End.uasset": "48076290557F12E8A849C061BEAFDF5B93FD178A93263C744C30B8CEE66BB93A",
    MOVEMENT + "Avatar_Male_Size03_Pyrois_Ani_TurnBack.uasset": "71C3B14549CD17FA337B61AEED0B8311D600C7E4592A66101839BD5D0186FD41",
    "Content/BP/Character/Player/BP_PC_Pyrios.uasset": "9E093DB87659B1A05281F000A97017F4141521E11B93E38F6E92A9DD8705DAC3",
    "Content/AI/Boss/Test/BB_Boss_Test.uasset": "B2A8400764133041F09A162B0F9BE72337FDD9D8BA635C558BF4D323B77A5660",
    "GGYGO.uproject": "D9B86F0FA9F462929AEF5E70737F0A219206D505B9663DB6ACD34E6AF897E174",
    ".kiro/steering/user-preferences.md": "6C49C81EB7B61A8DB3071A8738264B899A14C35E59B657F07D11DCD0D44AEB45",
}
KEY_FLOAT_FIELDS = (
    "time", "value", "arrive_tangent", "leave_tangent",
    "arrive_tangent_weight", "leave_tangent_weight",
)
KEY_INT_FIELDS = ("interp_mode", "tangent_mode", "tangent_weight_mode")


def _exception(report):
    error = sys.exc_info()[1]
    return {
        "type": type(error).__name__, "message": str(error),
        "traceback": traceback.format_exc(), "context": dict(report["context"]),
    }


def _hash_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def _hashes():
    return {relative: _hash_file(PROJECT_ROOT / relative) for relative in PROTECTED_SHA256}


def _hash_delta(before, after):
    return [
        {"path": str(PROJECT_ROOT / relative), "before": before[relative], "after": after[relative]}
        for relative in PROTECTED_SHA256 if before[relative] != after[relative]
    ]


def _dirty(unreal):
    utils = unreal.EditorLoadingAndSavingUtils
    return {
        "content": sorted(package.get_path_name() for package in utils.get_dirty_content_packages()),
        "maps": sorted(package.get_path_name() for package in utils.get_dirty_map_packages()),
    }


def _dirty_delta(before, after):
    return {
        kind: {
            "added": sorted(set(after[kind]) - set(before[kind])),
            "removed": sorted(set(before[kind]) - set(after[kind])),
        }
        for kind in ("content", "maps")
    }


def _finish_guard(report, unreal, entry):
    entry["hashesAfter"] = _hashes()
    report["hashesAfter"] = entry["hashesAfter"]
    entry["protectedDelta"] = _hash_delta(report["hashesBefore"], entry["hashesAfter"])
    entry["dirtyAfter"] = _dirty(unreal)
    entry["dirtyDelta"] = _dirty_delta(entry["dirtyBefore"], entry["dirtyAfter"])
    if entry["protectedDelta"] or entry["dirtyBefore"] != entry["dirtyAfter"]:
        raise RuntimeError("Dirty packages or protected hashes changed during " + entry["stage"])


def _guarded(report, unreal, stage, operation):
    report["context"] = {"stage": stage, "source": SOURCE_PATH}
    entry = {"stage": stage, "operationAttempted": False}
    report["guards"].append(entry)
    try:
        entry["hashesBefore"] = _hashes()
        report["hashesAfter"] = entry["hashesBefore"]
        entry["protectedDeltaBefore"] = _hash_delta(report["hashesBefore"], entry["hashesBefore"])
        if entry["protectedDeltaBefore"]:
            raise RuntimeError("Protected hashes changed before " + stage)
        entry["dirtyBefore"] = _dirty(unreal)
    except Exception:
        entry["guardException"] = _exception(report)
        raise
    entry["operationAttempted"] = True
    try:
        result = operation()
    except Exception:
        entry["operationException"] = _exception(report)
        try:
            _finish_guard(report, unreal, entry)
        except Exception:
            entry["guardException"] = _exception(report)
        raise  # Retain the original operation exception even when its guard also fails.
    try:
        _finish_guard(report, unreal, entry)
    except Exception:
        entry["guardException"] = _exception(report)
        raise
    return result


def _field(report, owner, name, location):
    stage = report["context"]["stage"]
    report["context"] = dict(
        location, stage=stage, source=SOURCE_PATH,
        property=name, ownerType=type(owner).__name__,
    )
    value = getattr(owner, name)  # One exact public getter; no editor/native alias fallback.
    report["fieldReads"].append(dict(report["context"], valueType=type(value).__name__))
    return value


def _real(report, value, native_bits):
    if type(value) is not float or not math.isfinite(value):
        raise TypeError("Expected finite Python float for native float%d, got %r" % (native_bits, value))
    bits64 = struct.pack("<d", value)
    if native_bits == 32:
        bits = struct.pack("<f", value)
        widened = struct.unpack("<f", bits)[0]
        if struct.pack("<d", widened) != bits64:
            raise ValueError("Native float32 property did not widen losslessly to Python float")
    elif native_bits == 64:
        bits = bits64
    else:
        raise ValueError("Unsupported native floating width")
    report["numericProof"].append(dict(
        report["context"], nativeBits=native_bits, hex=value.hex(),
        ieeeLittleEndian=bits.hex(), pythonBinary64LittleEndian=bits64.hex(),
    ))
    return value


def _int32(value):
    if type(value) is not int or not -(2 ** 31) <= value < 2 ** 31:
        raise TypeError("Expected native int32 Python integer, got %r" % (value,))
    return value


def _instance(value, expected, label):
    if not isinstance(value, expected):
        raise TypeError(label + " must be " + expected.__name__ + ", got " + type(value).__name__)


def _resolve(report, unreal):
    library = unreal.GGYGOAnimationCurveSnapshotLibrary
    method = library.read_float_curve_snapshot
    if not callable(method):
        raise TypeError("GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot is not callable")
    types = {
        "result": unreal.GGYGOFloatCurveReadResult,
        "curve": unreal.GGYGOFloatCurveSnapshot,
        "key": unreal.GGYGOFloatCurveKeySnapshot,
    }
    report["api"] = {
        "module": "GGYGOEditor", "library": "unreal.GGYGOAnimationCurveSnapshotLibrary",
        "method": "read_float_curve_snapshot", "doc": method.__doc__,
        "result": types["result"].__name__, "curve": types["curve"].__name__,
        "key": types["key"].__name__, "successProperty": "succeeded",
    }
    return method, types


def _call(report, method, source, names):
    report["snapshotCallCount"] += 1
    return method(source, names)  # The only curve-reading invocation in this script.


def _result_fields(report, unreal, types, result, destination):
    _instance(result, types["result"], "Snapshot return")
    observed = {"type": type(result).__name__}
    report[destination] = observed
    location = {"returnKind": destination}
    succeeded = _field(report, result, "succeeded", location)
    if type(succeeded) is not bool:
        raise TypeError("succeeded must be an actual bool")
    observed["succeeded"] = succeeded
    error = _field(report, result, "error", location)
    if type(error) is not str:
        raise TypeError("error must be a string")
    observed["error"] = error  # Preserve the complete native diagnostic before further checks.
    duration = _real(report, _field(report, result, "duration_seconds", location), 64)
    observed["duration_seconds"] = duration
    curves = _field(report, result, "curves", location)
    _instance(curves, unreal.Array, "curves")
    observed["curveCount"] = len(curves)
    return succeeded, error, duration, curves


def _null_result(report, unreal, types, result):
    succeeded, error, duration, curves = _result_fields(report, unreal, types, result, "failureReturn")
    if succeeded is not False or len(curves) != 0 or struct.pack("<d", duration) != struct.pack("<d", 0.0):
        raise ValueError("Null source must return false, empty curves and positive zero duration")
    if error != NULL_ERROR:
        raise ValueError("Null source diagnostic differs from frozen R1: " + error)


def _load_source(report, unreal):
    source = unreal.load_asset(SOURCE_PATH)
    _instance(source, unreal.AnimSequence, "Walk_Start source")
    actual_path = source.get_path_name()
    report["actualObjectPath"] = actual_path
    expected_path = SOURCE_PATH + "." + SOURCE_PATH.rsplit("/", 1)[1]
    if actual_path != expected_path:
        raise ValueError("Loaded asset identity differs from the single requested Walk_Start")
    return source


def _complete_fields(report, unreal, types, result):
    succeeded, error, duration, curves = _result_fields(report, unreal, types, result, "successReturn")
    if succeeded is not True:
        raise RuntimeError("Walk_Start Snapshot was rejected: " + error)
    if error != "" or duration <= 0.0 or len(curves) != len(CURVE_NAMES):
        raise ValueError("Success error/duration/four-curve contract failed: " + error)
    candidate = []
    for curve_index, curve in enumerate(curves):
        _instance(curve, types["curve"], "curve")
        location = {"curveIndex": curve_index, "requestedCurve": CURVE_NAMES[curve_index]}
        name = _field(report, curve, "name", location)
        _instance(name, unreal.Name, "curve name")
        if str(name) != CURVE_NAMES[curve_index]:
            raise ValueError("Returned curve name or request order differs")
        flags = _int32(_field(report, curve, "flags", location))
        default = _real(report, _field(report, curve, "default_value", location), 32)
        pre = _int32(_field(report, curve, "pre_infinity_extrap", location))
        post = _int32(_field(report, curve, "post_infinity_extrap", location))
        keys = _field(report, curve, "keys", location)
        _instance(keys, unreal.Array, "keys")
        key_values = []
        for key_index, key in enumerate(keys):
            _instance(key, types["key"], "key")
            key_location = dict(location, keyIndex=key_index)
            values = {
                field: _real(report, _field(report, key, field, key_location), 32)
                for field in KEY_FLOAT_FIELDS
            }
            values.update({
                field: _int32(_field(report, key, field, key_location))
                for field in KEY_INT_FIELDS
            })
            key_values.append(values)
        candidate.append({
            "name": str(name), "flags": flags, "default_value": default,
            "pre_infinity_extrap": pre, "post_infinity_extrap": post, "keys": key_values,
        })
    return {
        "objectPath": report["actualObjectPath"], "succeeded": succeeded,
        "error": error, "duration_seconds": duration, "curves": candidate,
    }


def _assert_json_exact(report, before, after, path):
    report["context"] = {"stage": "json_roundtrip", "source": SOURCE_PATH, "jsonPath": path}
    if type(before) is not type(after):
        raise TypeError("JSON changed a value type at " + path)
    if type(before) is float:
        if struct.pack("<d", before) != struct.pack("<d", after):
            raise ValueError("JSON changed floating bits at " + path)
    elif type(before) is dict:
        if list(before) != list(after):
            raise ValueError("JSON changed object fields or order at " + path)
        for key in before:
            _assert_json_exact(report, before[key], after[key], path + "." + key)
    elif type(before) is list:
        if len(before) != len(after):
            raise ValueError("JSON changed array length at " + path)
        for index, value in enumerate(before):
            _assert_json_exact(report, value, after[index], path + "[%d]" % index)
    elif before != after:
        raise ValueError("JSON changed a value at " + path)


def _roundtrip(report, candidate):
    # The same encoder/options are used for final publication; no fixed decimal formatting.
    encoded = json.dumps(candidate, ensure_ascii=False, indent=2, allow_nan=False)
    _assert_json_exact(report, candidate, json.loads(encoded), "snapshot")
    report["jsonRoundtrip"] = {"verified": True, "floatComparison": "binary64 bits, including signed zero"}


def _probe(report, unreal):
    _guarded(report, unreal, "load_module", lambda: unreal.load_module("GGYGOEditor"))
    method, types = _guarded(report, unreal, "resolve_api", lambda: _resolve(report, unreal))
    names = [unreal.Name(name) for name in CURVE_NAMES]
    rejected = _guarded(report, unreal, "null_snapshot_call", lambda: _call(report, method, None, names))
    _guarded(report, unreal, "read_null_result", lambda: _null_result(report, unreal, types, rejected))
    source = _guarded(report, unreal, "load_asset", lambda: _load_source(report, unreal))
    result = _guarded(report, unreal, "snapshot_call", lambda: _call(report, method, source, names))
    candidate = _guarded(report, unreal, "read_complete_fields", lambda: _complete_fields(report, unreal, types, result))
    _guarded(report, unreal, "json_roundtrip", lambda: _roundtrip(report, candidate))
    if report["snapshotCallCount"] != 2:
        raise RuntimeError("Expected exactly two Snapshot invocations")
    return candidate  # Still local: final global guards must pass before publishing a snapshot.


def _final_guard(report, unreal):
    report["context"] = {"stage": "final_guard", "source": SOURCE_PATH}
    report["hashesAfter"] = _hashes()
    report["protectedDelta"] = _hash_delta(PROTECTED_SHA256, report["hashesAfter"])
    if report["protectedDelta"]:
        raise RuntimeError("Protected hashes differ at final evidence publication")
    if unreal is None or "initialDirty" not in report:
        report["finalDirtyUnavailable"] = "Unreal import or initial dirty capture did not finish; no success is possible."
        return
    report["finalDirty"] = _dirty(unreal)
    report["finalDirtyDelta"] = _dirty_delta(report["initialDirty"], report["finalDirty"])
    if report["initialDirty"] != report["finalDirty"]:
        raise RuntimeError("Dirty package sets changed across the complete probe")


def _publish(report):
    try:
        encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with REPORT_PATH.open("x", encoding="utf-8", newline="\n") as output:
            output.write(encoded)
    except Exception:
        report["context"] = {"stage": "publish_evidence", "reportPath": str(REPORT_PATH)}
        report["publicationException"] = _exception(report)
        report["status"] = "failed"
        report["complete"] = False
        report["exitCode"] = 1
        report.pop("snapshot", None)  # A failed publication must not present a committed snapshot.
        # Preserve partial/existing files and the complete diagnostic in the coordinator's log.
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), file=sys.stderr)
        raise
    if report["exitCode"]:
        print(encoded, file=sys.stderr)
    else:
        print("R3-P complete for Walk_Start only: " + str(REPORT_PATH))


def main():
    report = {
        "schemaVersion": 1, "probe": "C23/R3-P", "status": "not_started", "complete": False,
        "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": SOURCE_PATH, "curveNames": list(CURVE_NAMES), "scope": "Walk_Start only",
        "reportPath": str(REPORT_PATH), "coordinatorLogPath": str(LOG_PATH),
        "context": {"stage": "initialization", "source": SOURCE_PATH},
        "guards": [], "fieldReads": [], "numericProof": [], "snapshotCallCount": 0,
        "protectedFiles": [
            {"path": str(PROJECT_ROOT / relative), "expectedSHA256": digest}
            for relative, digest in PROTECTED_SHA256.items()
        ],
        "defaultSemantics": "Native MAX_flt is an unset-default sentinel; retained numerically, never replaced or evaluated.",
        "coverageLimit": "Public Snapshot DTO transport only; Model alignment is independently gated by C20. No Channel/disk equality, bones, Graph, other sources or migration.",
        "runPrerequisite": "Coordinator-confirmed latest build new DLL and actual C20 success from that same build, with prior UE exited.",
    }
    unreal_module = None
    candidate = None
    try:
        if REPORT_PATH.exists():
            raise FileExistsError("Fixed R3 evidence already exists; it must be preserved, never overwritten")
        report["scriptSHA256"] = _hash_file(Path(__file__).resolve())
        report["context"] = {"stage": "protected_baseline", "source": SOURCE_PATH}
        report["hashesBefore"] = _hashes()
        report["protectedBaselineMismatch"] = _hash_delta(PROTECTED_SHA256, report["hashesBefore"])
        if report["protectedBaselineMismatch"]:
            raise RuntimeError("Protected files differ from the frozen R2/R3 baseline")
        report["context"] = {"stage": "import_unreal", "source": SOURCE_PATH}
        import unreal
        unreal_module = unreal
        report["initialDirty"] = _dirty(unreal)
        candidate = _probe(report, unreal)
    except Exception:
        report["failure"] = _exception(report)
    try:
        _final_guard(report, unreal_module)
    except Exception:
        report["finalGuardException"] = _exception(report)
    if "failure" not in report and "finalGuardException" not in report:
        try:
            report["context"] = {"stage": "completion_check", "source": SOURCE_PATH}
            if candidate is None or report["snapshotCallCount"] != 2 or "finalDirty" not in report:
                raise RuntimeError("Internal probe completion invariant failed; no report may claim success")
        except Exception:
            report["completionException"] = _exception(report)
    if not any(key in report for key in ("failure", "finalGuardException", "completionException")):
        report["snapshot"] = candidate
        report["status"] = "walk_start_complete"
        report["complete"] = True
        report["exitCode"] = 0
    else:
        report["status"] = "failed"
        report["complete"] = False
        report["exitCode"] = 1
    report["finishedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    _publish(report)
    return report["exitCode"]


if __name__ == "__main__":
    if main() != 0:
        raise SystemExit(1)
