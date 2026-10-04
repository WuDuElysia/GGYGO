# -*- coding: utf-8 -*-
"""C15 / R2-P: probe the existing read-only R1 Python reflection boundary.

One source only: Walk_Start and its four required RootMotion curves. Resolve
the exact library/method, observe the None failure and successful tuple, then
read every required field from returned value copies. Stop at the first error;
never substitute defaults, parse object strings, fall back to keys, or scan
other animations. No asset setters, Controller, Modify, transactions or saves.

The coordinator runs this frozen script in its exclusive UE window:
  F:/UE_5.8/Engine/Binaries/Win64/UnrealEditor-Cmd.exe
  F:/ue_project/GGYGO/GGYGO.uproject -run=pythonscript
  -script=F:/ue_project/GGYGO/AAADocs/Scripts/probe_animation_float_curve_readback.py
  -EnablePlugins=PythonScriptPlugin -Unattended -NoSplash -NoSound -NullRHI
  -NoP4 -NoTurnkey -log=GGYGO_AnimationCurveReadback_Python_20260930_R2.log

Runtime output is only the fixed new JSON below (exclusive creation). The UE
log is coordinator-owned. Failure keeps its context/traceback and exits nonzero.
The legacy audit script/report, R1/T1, assets and records remain untouched.
"""

import datetime
import hashlib
import json
import math
from pathlib import Path
import sys
import traceback


PROJECT_ROOT = Path("F:/ue_project/GGYGO")
REPORT_PATH = PROJECT_ROOT / "Saved/AnimationCurveReadback/ReadFloatCurves_Python_20260930_R2.json"
LOG_PATH = PROJECT_ROOT / "Saved/Logs/GGYGO_AnimationCurveReadback_Python_20260930_R2.log"
SOURCE_PATH = (
    "/Game/Characters/Player/Pyrios/Animation/Movement/"
    "Avatar_Male_Size03_Pyrois_Ani_Walk_Start"
)
CURVE_NAMES = ("RootMotion_Speed", "RootMotion_DirX", "RootMotion_DirY", "RootMotion_Yaw")
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
    "Time", "Value", "ArriveTangent", "LeaveTangent",
    "ArriveTangentWeight", "LeaveTangentWeight",
)
KEY_ENUM_FIELDS = ("InterpMode", "TangentMode", "TangentWeightMode")


def _exception():
    error = sys.exc_info()[1]
    return {"type": type(error).__name__, "message": str(error), "traceback": traceback.format_exc()}


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


def _finish_guard(report, unreal, entry):
    entry["dirtyAfter"] = _dirty(unreal)
    entry["dirtyDelta"] = {
        kind: {
            "added": sorted(set(entry["dirtyAfter"][kind]) - set(entry["dirtyBefore"][kind])),
            "removed": sorted(set(entry["dirtyBefore"][kind]) - set(entry["dirtyAfter"][kind])),
        }
        for kind in ("content", "maps")
    }
    report["hashesAfter"] = _hashes()
    entry["protectedDelta"] = _hash_delta(report["hashesBefore"], report["hashesAfter"])
    if entry["dirtyBefore"] != entry["dirtyAfter"] or entry["protectedDelta"]:
        raise RuntimeError("Dirty packages or protected hashes changed during " + entry["stage"])


def _guarded(report, unreal, stage, operation):
    report["context"] = {"stage": stage, "source": SOURCE_PATH}
    current_hashes = _hashes()
    report["hashesAfter"] = current_hashes
    delta = _hash_delta(report["hashesBefore"], current_hashes)
    if delta:
        report["protectedDelta"] = delta
        raise RuntimeError("Protected hashes changed before " + stage)
    entry = {"stage": stage, "dirtyBefore": _dirty(unreal)}
    report["guards"].append(entry)
    try:
        result = operation()
    except Exception:
        entry["operationException"] = _exception()
        try:
            _finish_guard(report, unreal, entry)
        except Exception:
            entry["guardException"] = _exception()
        raise  # Keep the original field/call exception even if a guard also failed.
    _finish_guard(report, unreal, entry)
    return result


def _number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise TypeError("Expected a finite numeric property, got " + type(value).__name__)
    return float(value)


def _integer(value):
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError("Expected an integer property, got " + type(value).__name__)
    return value


def _field(report, owner, name, curve_index, key_index=None):
    report["context"] = {
        "stage": "read_properties", "source": SOURCE_PATH,
        "curveIndex": curve_index, "requestedCurve": CURVE_NAMES[curve_index],
        "keyIndex": key_index, "property": name, "ownerType": type(owner).__name__,
    }
    value = owner.get_editor_property(name)  # Native UPROPERTY name; no alternate access path.
    report["fieldReads"].append(dict(report["context"], valueType=type(value).__name__))
    return value


def _snapshot(report, unreal, curves, duration):
    candidate = []
    for index, curve in enumerate(curves):
        if not isinstance(curve, unreal.FloatCurve):
            raise TypeError("OutCurves contains " + type(curve).__name__)
        name = _field(report, curve, "CurveName", index)
        if not isinstance(name, unreal.Name) or str(name) != CURVE_NAMES[index]:
            raise ValueError("Returned curve name/order does not match the request")
        flags = _integer(_field(report, curve, "CurveTypeFlags", index))
        rich = _field(report, curve, "FloatCurve", index)
        default = _number(_field(report, rich, "DefaultValue", index))
        pre = _integer(_field(report, rich, "PreInfinityExtrap", index).value)
        post = _integer(_field(report, rich, "PostInfinityExtrap", index).value)
        keys = _field(report, rich, "Keys", index)
        key_snapshots = []
        for key_index, key in enumerate(keys):
            values = {
                field: _number(_field(report, key, field, index, key_index))
                for field in KEY_FLOAT_FIELDS
            }
            values.update({
                field: _integer(_field(report, key, field, index, key_index).value)
                for field in KEY_ENUM_FIELDS
            })
            key_snapshots.append(values)
        candidate.append({
            "name": str(name), "flags": flags, "DefaultValue": default,
            "PreInfinityExtrap": pre, "PostInfinityExtrap": post, "keys": key_snapshots,
        })
    return {"objectPath": report["actualObjectPath"], "durationSeconds": duration, "curves": candidate}


def _probe(report, unreal):
    _guarded(report, unreal, "load_module", lambda: unreal.load_module("GGYGOEditor"))
    report["context"] = {"stage": "resolve_api", "source": SOURCE_PATH}
    library = unreal.GGYGOAnimationCurveReadLibrary
    method = library.read_float_curves
    if not callable(method):
        raise TypeError("GGYGOAnimationCurveReadLibrary.read_float_curves is not callable")
    report["api"] = {
        "module": "GGYGOEditor", "library": "unreal.GGYGOAnimationCurveReadLibrary",
        "method": "read_float_curves", "doc": method.__doc__,
    }
    names = [unreal.Name(name) for name in CURVE_NAMES]
    failed_result = _guarded(report, unreal, "null_source_call", lambda: method(None, names))
    report["failureReturn"] = {
        "type": type(failed_result).__name__, "isNone": failed_result is None,
    }
    if failed_result is not None:
        raise TypeError("Null source did not produce the expected None failure wrapper")
    report["failureReturn"]["nativeOutErrorVisible"] = False
    source = _guarded(report, unreal, "load_asset", lambda: unreal.load_asset(SOURCE_PATH))
    if not isinstance(source, unreal.AnimSequence):
        raise TypeError("Walk_Start did not load as an AnimSequence")
    report["actualObjectPath"] = source.get_path_name()
    expected_path = SOURCE_PATH + "." + SOURCE_PATH.rsplit("/", 1)[1]
    if report["actualObjectPath"] != expected_path:
        raise ValueError("Loaded asset identity differs from the requested Walk_Start")
    result = _guarded(report, unreal, "read_float_curves", lambda: method(source, names))
    report["successReturn"] = {"type": type(result).__name__, "isNone": result is None}
    if isinstance(result, tuple):
        report["successReturn"]["tupleLength"] = len(result)
    if not isinstance(result, tuple) or len(result) != 3:
        raise TypeError("Expected the R1 success wrapper to be a three-element tuple")
    curves, raw_duration, error = result
    report["successReturn"].update(
        tupleLength=len(result), curvesType=type(curves).__name__, curveCount=len(curves),
        durationType=type(raw_duration).__name__, errorType=type(error).__name__,
    )
    if not isinstance(curves, unreal.Array) or len(curves) != len(CURVE_NAMES):
        raise TypeError("Expected exactly four native OutCurves")
    duration = _number(raw_duration)
    report["successReturn"]["durationSeconds"] = duration
    if not isinstance(error, str):
        raise TypeError("Expected OutError to be a string")
    report["successReturn"]["outError"] = error
    if duration <= 0.0 or error != "":
        raise ValueError("Success duration/error does not satisfy the R1 contract")
    snapshot = _guarded(report, unreal, "read_properties", lambda: _snapshot(report, unreal, curves, duration))
    report["snapshot"] = snapshot  # Commit only after every requested field was read.
    report["status"] = "walk_start_complete"
    report["complete"] = True  # Applies only to this one source's public DataModel snapshot.


def main():
    report = {
        "schemaVersion": 1, "status": "not_started", "complete": False,
        "startedUTC": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "source": SOURCE_PATH, "curveNames": list(CURVE_NAMES), "scope": "Walk_Start only",
        "reportPath": str(REPORT_PATH), "coordinatorLogPath": str(LOG_PATH),
        "context": {"stage": "initialization", "source": SOURCE_PATH},
        "guards": [], "fieldReads": [],
        "protectedFiles": [
            {"path": str(PROJECT_ROOT / relative), "expectedSHA256": digest}
            for relative, digest in PROTECTED_SHA256.items()
        ],
        "coverageLimit": "Current public DataModel only; no underlying Channel/disk equality, bones, Graph or migration.",
    }
    exit_code = 1
    try:
        if REPORT_PATH.exists():
            raise FileExistsError("Fixed R2 evidence already exists; coordinator must preserve it before a rerun")
        report["scriptSHA256"] = _hash_file(Path(__file__).resolve())
        report["context"]["stage"] = "protected_baseline"
        report["hashesBefore"] = _hashes()
        mismatch = _hash_delta(PROTECTED_SHA256, report["hashesBefore"])
        if mismatch:
            report["protectedBaselineMismatch"] = mismatch
            raise RuntimeError("One or more protected files differ from the frozen R2 preflight baseline")
        report["context"]["stage"] = "import_unreal"
        import unreal
        _probe(report, unreal)
        exit_code = 0
    except Exception:
        report["status"] = "failed"
        report["complete"] = False
        report["failure"] = dict(_exception(), context=dict(report["context"]))
    try:
        report["hashesAfter"] = _hashes()
        if "hashesBefore" in report:
            report["protectedDelta"] = _hash_delta(report["hashesBefore"], report["hashesAfter"])
            if report["protectedDelta"]:
                raise RuntimeError("Protected files changed before final evidence publication")
    except Exception:
        report["finalGuardException"] = _exception()
        report["status"] = "failed"
        report["complete"] = False
        exit_code = 1
    report["exitCode"] = exit_code
    report["finishedUTC"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    encoded = json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False) + "\n"
    try:
        REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
        with REPORT_PATH.open("x", encoding="utf-8") as output:
            output.write(encoded)
    except Exception:
        # Preserve the whole report and publication exception in the coordinator's log.
        report["publicationException"] = dict(
            _exception(), context={"stage": "publish_evidence", "reportPath": str(REPORT_PATH)},
        )
        report["status"] = "failed"
        report["complete"] = False
        report["exitCode"] = 1
        print(json.dumps(report, ensure_ascii=False, indent=2, allow_nan=False), file=sys.stderr)
        raise
    if exit_code:
        print(encoded, file=sys.stderr)
    else:
        print("R2-P complete for Walk_Start only: " + str(REPORT_PATH))
    return exit_code


if __name__ == "__main__":
    if main() != 0:
        raise SystemExit(1)
