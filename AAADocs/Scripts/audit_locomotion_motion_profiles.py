# -*- coding: utf-8 -*-
"""Read-only locomotion asset audit for GGYGO.

Run offline with Python 3 from any working directory, or execute this file in
Unreal Editor Python. The only file this script may write is the migration
report JSON at REPORT_RELATIVE_PATH. It never edits or saves a UE package.

Offline mode fingerprints the current .uasset files and the selected curve
arrays in Saved/AnimRootMotion/Pyrios_RootMotion.json. Unreal mode additionally
reads ABP CDO AnimSet maps, BlendSpace axes/samples, MovementSet profile refs,
and animation curve names/key data when the installed Python API exposes them.
Full Snapshot values and explicit formal PawnData references are reported separately;
main(formal_pawn_data_object_path=...) requires a caller-selected formal root for
complete readback. This does not prove Profile generation, wiring or production Run.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import struct
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

try:  # Unreal's embedded Python provides this module.
    import unreal as _UNREAL  # type: ignore
except ImportError:
    _UNREAL = None


REPORT_RELATIVE_PATH = Path("AAADocs/Modules/Movement/Locomotion_Motion_Profile_Migration.json")
ROOT_MOTION_MANIFEST_RELATIVE_PATH = Path("Saved/AnimRootMotion/Pyrios_RootMotion.json")

ANIM_BLUEPRINT_OBJECT_PATH = "/Game/BP/Anim/ABP_Pyrios"
WALK_RUN_OBJECT_PATH = "/Game/Characters/Player/Pyrios/Animation/Movement/BS_Pyrios_WalkRun"
MOVEMENT_SET_OBJECT_PATH = "/Game/System/DA_Movement_Default"

NEW_WALK_RUN_PARAMETER = "WalkRunBlendAlpha"
LEGACY_SERIALIZED_PARAMETER = "GaitBlendY"
REQUIRED_PROFILE_CURVES = (
    "RootMotion_Speed",
    "RootMotion_DirX",
    "RootMotion_DirY",
    "RootMotion_Yaw",
)

PROFILE_SOURCES = (
    {
        "movementSetProperty": "WalkStartProfile",
        "motionType": "WalkStart",
        "profileAssetName": "DA_LocomotionMotionProfile_Pyrios_WalkStart",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_Walk_Start",
        "loop": False,
    },
    {
        "movementSetProperty": "WalkLoopProfile",
        "motionType": "WalkRun:WalkLoop",
        "profileAssetName": "DA_LocomotionMotionProfile_Pyrios_WalkLoop",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_Walk_Loop",
        "loop": True,
    },
    {
        "movementSetProperty": "RunLoopProfile",
        "motionType": "WalkRun:RunLoop",
        "profileAssetName": "DA_LocomotionMotionProfile_Pyrios_RunLoop",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_Run_Loop",
        "loop": True,
    },
    {
        "movementSetProperty": "StartStopProfile",
        "motionType": "StartStop",
        "profileAssetName": "DA_LocomotionMotionProfile_Pyrios_StartStop",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_Walk_Start_End",
        "loop": False,
    },
    {
        "movementSetProperty": "WalkStopProfile",
        "motionType": "WalkStop",
        "profileAssetName": "DA_LocomotionMotionProfile_Pyrios_WalkStop",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_Walk_End",
        "loop": False,
    },
    {
        "movementSetProperty": "RunStopProfile",
        "motionType": "RunStop",
        "profileAssetName": "DA_LocomotionMotionProfile_Pyrios_RunStop",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_Run_End",
        "loop": False,
    },
    {
        "movementSetProperty": "TurnBackProfile",
        "motionType": "TurnBack",
        "profileAssetName": "DA_LocomotionMotionProfile_Pyrios_TurnBack",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_TurnBack",
        "loop": False,
    },
)

STOP_VALUE_MAP = (
    {
        "stopValue": 0,
        "motionType": "StartStop",
        "movementSetProperty": "StartStopProfile",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_Walk_Start_End",
    },
    {
        "stopValue": 1,
        "motionType": "WalkStop",
        "movementSetProperty": "WalkStopProfile",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_Walk_End",
    },
    {
        "stopValue": 2,
        "motionType": "RunStop",
        "movementSetProperty": "RunStopProfile",
        "sourceAnimationName": "Avatar_Male_Size03_Pyrois_Ani_Run_End",
    },
)


def _find_project_root(start: Optional[Path] = None) -> Path:
    candidates: List[Path] = []
    if start is not None:
        candidates.append(start.resolve())
    try:
        candidates.append(Path(__file__).resolve().parent.parent.parent)
    except NameError:
        pass
    candidates.append(Path.cwd().resolve())

    for candidate in candidates:
        for root in (candidate, *candidate.parents):
            if (root / "Content").is_dir() and (root / "AAADocs").is_dir():
                return root
    raise RuntimeError("Could not locate the GGYGO project root (expected Content/ and AAADocs/).")


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and re.fullmatch(r"[0-9a-f]{64}", value) is not None


def _sha256_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as source_file:
        for block in iter(lambda: source_file.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _to_disk_path(root: Path, object_path: str) -> Path:
    package = object_path.split(".", 1)[0]
    if not package.startswith("/Game/"):
        raise ValueError("Only /Game asset paths can be mapped to project Content/: " + object_path)
    return root / "Content" / (package[len("/Game/") :] + ".uasset")


def _repo_relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.as_posix()


def _asset_record(root: Path, object_path: str, role: str) -> Dict[str, Any]:
    disk_path = _to_disk_path(root, object_path)
    return {
        "role": role,
        "objectPath": object_path,
        "diskPath": _repo_relative(disk_path, root),
        "exists": disk_path.is_file(),
        "fileBytes": disk_path.stat().st_size if disk_path.is_file() else None,
        "fileSha256": _sha256_file(disk_path),
    }


def _curve_payload_digest(clip: Dict[str, Any]) -> Tuple[Optional[str], Optional[str]]:
    curves = clip.get("curves") or {}
    missing = [name for name in REQUIRED_PROFILE_CURVES if name not in curves]
    if missing:
        return None, "missing curves: " + ", ".join(missing)

    payload = {
        "clipName": clip.get("name"),
        "duration": clip.get("duration"),
        "clipLength": clip.get("clipLength"),
        "sampleRate": clip.get("sampleRate"),
        "frameCount": clip.get("frameCount"),
        "times": clip.get("times"),
        "curves": {name: curves[name] for name in REQUIRED_PROFILE_CURVES},
    }
    try:
        encoded = json.dumps(
            payload,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as error:
        return None, "curve payload is not stable JSON: " + str(error)
    return _sha256_bytes(encoded), None


def _load_manifest(root: Path) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
    path = root / ROOT_MOTION_MANIFEST_RELATIVE_PATH
    record: Dict[str, Any] = {
        "path": ROOT_MOTION_MANIFEST_RELATIVE_PATH.as_posix(),
        "exists": path.is_file(),
        "fileSha256": _sha256_file(path),
        "clipCount": None,
        "model": None,
    }
    if not path.is_file():
        return None, record
    try:
        manifest = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        record["parseError"] = str(error)
        return None, record

    clips = manifest.get("clips")
    record["model"] = manifest.get("model")
    record["clipCount"] = len(clips) if isinstance(clips, list) else 0
    record["clipNameMatchOnly"] = True
    record["assetToManifestIdentityVerified"] = False
    record["identityLimit"] = (
        "The export manifest has no .uasset content digest; clip-name matching does not prove "
        "that this curve export and the current binary asset are the same revision."
    )
    return manifest, record


def _profile_records(root: Path, manifest: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    manifest_clips = manifest.get("clips", []) if manifest else []
    by_name: Dict[str, List[Dict[str, Any]]] = {}
    for clip in manifest_clips:
        if isinstance(clip, dict) and isinstance(clip.get("name"), str):
            by_name.setdefault(clip["name"], []).append(clip)

    records: List[Dict[str, Any]] = []
    for source in PROFILE_SOURCES:
        name = source["sourceAnimationName"]
        source_object_path = WALK_RUN_OBJECT_PATH.rsplit("/", 1)[0] + "/" + name
        source_asset = _asset_record(root, source_object_path, "profileSourceAnimation")
        profile_name = source["profileAssetName"]
        profile_object_path = (
            WALK_RUN_OBJECT_PATH.rsplit("/", 1)[0]
            + "/Profiles/"
            + profile_name
        )
        profile_asset = _asset_record(root, profile_object_path, "suggestedLocomotionMotionProfile")

        matches = by_name.get(name, [])
        clip = matches[0] if len(matches) == 1 else None
        digest, digest_error = _curve_payload_digest(clip) if clip else (None, None)
        curve_names = sorted((clip.get("curves") or {}).keys()) if clip else []
        lengths = {}
        if clip:
            times = clip.get("times") or []
            for curve_name in REQUIRED_PROFILE_CURVES:
                values = (clip.get("curves") or {}).get(curve_name)
                lengths[curve_name] = len(values) if isinstance(values, list) else None
            lengths["times"] = len(times) if isinstance(times, list) else None

        records.append(
            {
                **source,
                "sourceObjectPath": source_object_path,
                "sourceDiskPath": source_asset["diskPath"],
                "sourceAssetExists": source_asset["exists"],
                "sourceAssetBytes": source_asset["fileBytes"],
                "sourceAssetSha256": source_asset["fileSha256"],
                "suggestedProfileObjectPath": profile_object_path,
                "suggestedProfileDiskPath": profile_asset["diskPath"],
                "suggestedProfileExists": profile_asset["exists"],
                "manifestClipMatches": len(matches),
                "manifestClipName": clip.get("name") if clip else None,
                "manifestDurationSeconds": clip.get("duration") if clip else None,
                "manifestClipLengthSeconds": clip.get("clipLength") if clip else None,
                "manifestSampleRateHz": clip.get("sampleRate") if clip else None,
                "manifestFrameCount": clip.get("frameCount") if clip else None,
                "manifestCurveNames": curve_names,
                "profileCurveSources": {
                    "SpeedCurve": "RootMotion_Speed",
                    "DirectionXCurve": "RootMotion_DirX",
                    "DirectionYCurve": "RootMotion_DirY",
                    "YawCurve": "RootMotion_Yaw",
                },
                "curveSampleCounts": lengths,
                "curveSampleLengthsMatchTimes": bool(
                    clip
                    and isinstance(clip.get("times"), list)
                    and all(lengths.get(curve_name) == len(clip["times"]) for curve_name in REQUIRED_PROFILE_CURVES)
                ),
                "manifestCurvePayloadSha256": digest,
                "curveDigestError": digest_error,
            }
        )
    return records


def _stop_map_records(root: Path) -> List[Dict[str, Any]]:
    records = []
    for mapping in STOP_VALUE_MAP:
        source_object_path = WALK_RUN_OBJECT_PATH.rsplit("/", 1)[0] + "/" + mapping["sourceAnimationName"]
        source_asset = _asset_record(root, source_object_path, "stopMotionSourceAnimation")
        records.append(
            {
                **mapping,
                "sourceObjectPath": source_object_path,
                "sourceDiskPath": source_asset["diskPath"],
                "sourceAssetExists": source_asset["exists"],
                "sourceAssetSha256": source_asset["fileSha256"],
            }
        )
    return records


def _safe_get_editor_property(obj: Any, property_name: str) -> Tuple[bool, Any, Optional[str]]:
    try:
        return True, obj.get_editor_property(property_name), None
    except Exception as error:  # Unreal property names differ slightly across engine versions.
        return False, None, str(error)


def _object_path(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    try:
        return str(obj.get_path_name())
    except Exception:
        return str(obj)


def _object_class_name(obj: Any) -> Optional[str]:
    if obj is None:
        return None
    try:
        return str(obj.get_class().get_name())
    except Exception:
        return type(obj).__name__


def _mapping_records(value: Any) -> List[Dict[str, Any]]:
    records = []
    try:
        keys = list(value.keys())
    except Exception:
        return records
    for key in sorted(keys, key=lambda item: str(item)):
        try:
            item = value[key]
        except Exception:
            item = None
        records.append({"key": str(key), "objectPath": _object_path(item)})
    return records


def _vector_x(value: Any) -> Optional[float]:
    try:
        return float(value.x)
    except Exception:
        try:
            return float(value.get_editor_property("x"))
        except Exception:
            return None


def _blend_space_readback(unreal_module: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {"status": "not_loaded", "objectPath": WALK_RUN_OBJECT_PATH}
    try:
        blend_space = unreal_module.load_asset(WALK_RUN_OBJECT_PATH)
    except Exception as error:
        result["loadError"] = str(error)
        return result
    if blend_space is None:
        return result

    result["status"] = "loaded"
    result["actualObjectPath"] = _object_path(blend_space)
    result["actualClass"] = _object_class_name(blend_space)
    try:
        blend_space_1d = getattr(unreal_module, "BlendSpace1D", None)
        result["isBlendSpace1D"] = isinstance(blend_space, blend_space_1d) if blend_space_1d else None
    except Exception:
        result["isBlendSpace1D"] = None

    ok, axis_label, error = _safe_get_editor_property(blend_space, "axis_label")
    result["axisLabel"] = str(axis_label) if ok else None
    if not ok:
        result["axisLabelReadError"] = error

    ok, parameters, error = _safe_get_editor_property(blend_space, "blend_parameters")
    result["axes"] = []
    if ok:
        try:
            for index, parameter in enumerate(parameters):
                axis = {"index": index}
                for field in ("display_name", "min", "max", "grid_num"):
                    field_ok, value, _ = _safe_get_editor_property(parameter, field)
                    if field_ok:
                        axis[field] = str(value) if field == "display_name" else value
                result["axes"].append(axis)
        except Exception as axis_error:
            result["axisReadError"] = str(axis_error)
    else:
        result["axisReadError"] = error

    ok, samples, error = _safe_get_editor_property(blend_space, "sample_data")
    result["samples"] = []
    if ok:
        try:
            for sample in samples:
                animation_ok, animation, _ = _safe_get_editor_property(sample, "animation")
                value_ok, sample_value, _ = _safe_get_editor_property(sample, "sample_value")
                rate_ok, rate_scale, _ = _safe_get_editor_property(sample, "rate_scale")
                result["samples"].append(
                    {
                        "animationObjectPath": _object_path(animation) if animation_ok else None,
                        "x": _vector_x(sample_value) if value_ok else None,
                        "y": None if not value_ok else getattr(sample_value, "y", None),
                        "rateScale": rate_scale if rate_ok else None,
                    }
                )
        except Exception as sample_error:
            result["sampleReadError"] = str(sample_error)
    else:
        result["sampleReadError"] = error
    return result


def _anim_blueprint_readback(unreal_module: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {"status": "not_loaded", "objectPath": ANIM_BLUEPRINT_OBJECT_PATH}
    try:
        blueprint = unreal_module.load_asset(ANIM_BLUEPRINT_OBJECT_PATH)
        if blueprint is None:
            return result
        result["status"] = "loaded"
        result["actualObjectPath"] = _object_path(blueprint)
        result["actualClass"] = _object_class_name(blueprint)
        generated_class = blueprint.generated_class()
        cdo = unreal_module.get_default_object(generated_class)
        result["cdoClass"] = _object_class_name(cdo)
        ok, anim_set, error = _safe_get_editor_property(cdo, "anim_set")
        if not ok:
            result["animSetReadError"] = error
            return result
        sequences_ok, sequences, sequences_error = _safe_get_editor_property(anim_set, "sequences")
        blend_spaces_ok, blend_spaces, blend_spaces_error = _safe_get_editor_property(anim_set, "blend_spaces")
        result["animSet"] = {
            "sequences": _mapping_records(sequences) if sequences_ok else None,
            "blendSpaces": _mapping_records(blend_spaces) if blend_spaces_ok else None,
        }
        if not sequences_ok:
            result["sequencesReadError"] = sequences_error
        if not blend_spaces_ok:
            result["blendSpacesReadError"] = blend_spaces_error
    except Exception as error:
        result["readError"] = str(error)
    return result


def _movement_set_readback(unreal_module: Any) -> Dict[str, Any]:
    result: Dict[str, Any] = {"status": "not_loaded", "objectPath": MOVEMENT_SET_OBJECT_PATH}
    try:
        movement_set = unreal_module.load_asset(MOVEMENT_SET_OBJECT_PATH)
    except Exception as error:
        result["loadError"] = str(error)
        return result
    if movement_set is None:
        return result

    result["status"] = "loaded"
    result["actualObjectPath"] = _object_path(movement_set)
    result["actualClass"] = _object_class_name(movement_set)
    result["profileReferences"] = {}
    for source in PROFILE_SOURCES:
        property_name = _snake_case(source["movementSetProperty"])
        ok, profile, error = _safe_get_editor_property(movement_set, property_name)
        result["profileReferences"][source["movementSetProperty"]] = {
            "propertyName": property_name,
            "readStatus": "read" if ok else "unavailable",
            "objectPath": _object_path(profile) if ok else None,
            "isNull": profile is None if ok else None,
            "readError": None if ok else error,
        }
        if ok and profile is not None:
            profile_record = result["profileReferences"][source["movementSetProperty"]]
            for field, output_field in (
                ("source_asset_identifier", "sourceAssetIdentifier"),
                ("source_fingerprint", "sourceFingerprint"),
                ("duration", "durationSeconds"),
                ("b_loop", "loop"),
            ):
                field_ok, value, _ = _safe_get_editor_property(profile, field)
                if field_ok:
                    profile_record[output_field] = value
    return result


def _snake_case(name: str) -> str:
    output = []
    for index, character in enumerate(name):
        if character.isupper() and index > 0:
            output.append("_")
        output.append(character.lower())
    return "".join(output)


def _resolve_animation_read_api(unreal_module: Any) -> Tuple[Any, Any, Dict[str, Any]]:
    """Resolve only the public API verified in the installed UE source."""
    details: Dict[str, Any] = {
        "moduleName": "AnimationBlueprintLibrary",
        "librarySymbol": "unreal.AnimationLibrary",
        "curveTypeSymbol": "unreal.RawCurveTrackTypes.RCT_FLOAT",
        "methods": ["get_animation_curve_names", "get_float_keys", "get_sequence_length"],
    }
    load_module = getattr(unreal_module, "load_module", None)
    if not callable(load_module):
        details.update(status="module_api_unavailable", error="unreal.load_module is not callable.")
        return None, None, details
    try:
        load_module(details["moduleName"])
    except Exception as error:
        details.update(status="module_load_failed", error=str(error))
        return None, None, details
    # load_module returns None; completion alone does not prove API availability.
    details["moduleLoadCallCompleted"] = True
    library = getattr(unreal_module, "AnimationLibrary", None)
    if library is None:
        details.update(status="library_unavailable", error="unreal.AnimationLibrary was not exported after module load.")
        return None, None, details
    curve_type = getattr(getattr(unreal_module, "RawCurveTrackTypes", None), "RCT_FLOAT", None)
    if curve_type is None:
        details.update(status="curve_type_unavailable", error="unreal.RawCurveTrackTypes.RCT_FLOAT is unavailable.")
        return None, None, details
    missing = [name for name in details["methods"] if not callable(getattr(library, name, None))]
    if missing:
        details.update(status="api_unavailable", missingMethods=missing,
                       error="unreal.AnimationLibrary missing callable API: " + ", ".join(missing))
        return None, None, details
    details["status"] = "ready"
    return library, curve_type, details


def _curve_keys_from_result(value: Any, duration: float) -> List[Tuple[float, float]]:
    """Validate the exact GetFloatKeys time/value output; never synthesize keys."""
    if not isinstance(value, tuple) or len(value) != 2:
        raise ValueError("invalid key result: get_float_keys must return exactly (times, values).")
    times, values = value
    if isinstance(times, (str, bytes, dict)) or isinstance(values, (str, bytes, dict)):
        raise ValueError("invalid key arrays: expected numeric sequences.")
    try:
        times, values = list(times), list(values)
    except TypeError as error:
        raise ValueError("invalid key arrays: " + str(error)) from error
    if len(times) != len(values):
        raise ValueError("time/value count mismatch: {} times, {} values.".format(len(times), len(values)))
    if not times:
        raise ValueError("empty keys: required curve has no time/value data.")
    keys: List[Tuple[float, float]] = []
    for index, (time_value, key_value) in enumerate(zip(times, values)):
        if any(isinstance(item, bool) or not isinstance(item, (int, float)) for item in (time_value, key_value)):
            raise ValueError("non-numeric key: index {}.".format(index))
        try:
            time_value, key_value = float(time_value), float(key_value)
        except (ValueError, OverflowError) as error:
            raise ValueError("non-finite key: index {}.".format(index)) from error
        if not math.isfinite(time_value) or not math.isfinite(key_value):
            raise ValueError("non-finite key: index {}.".format(index))
        if time_value < 0.0 or time_value > duration:
            raise ValueError("key time outside [0, duration]: index {}, time {}, duration {}.".format(index, time_value, duration))
        if keys and time_value <= keys[-1][0]:
            raise ValueError("key times are not strictly increasing: index {}.".format(index))
        keys.append((time_value, key_value))
    return keys


def _read_animation_curve_fingerprint(
    unreal_module: Any, object_path: str,
    read_api: Optional[Tuple[Any, Any, Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "objectPath": object_path, "status": "not_loaded",
        "curveFingerprintCoverage": {
            "included": ["objectPath", "requiredCurveNames", "keyTimes", "keyValues"],
            "excluded": ["duration", "RichCurveInterpolation", "tangents", "tangentWeights",
                         "prePostInfinity", "boneTracks", "graphPins"],
            "migrationAuthorized": False,
        },
    }
    library, curve_type, api_details = read_api if read_api is not None else _resolve_animation_read_api(unreal_module)
    result["curveReadAPI"] = api_details
    if api_details["status"] != "ready":
        result["curveReadStatus"] = api_details["status"]
        result["curveReadError"] = api_details["error"]
        return result
    try:
        animation = unreal_module.load_asset(object_path)
    except Exception as error:
        result.update(curveReadStatus="asset_load_failed", loadError=str(error))
        return result
    if animation is None:
        result.update(curveReadStatus="asset_not_loaded", loadError="load_asset returned None for " + object_path)
        return result

    result["status"] = "loaded"
    result["actualObjectPath"] = _object_path(animation)
    result["actualClass"] = _object_class_name(animation)
    try:
        duration = library.get_sequence_length(animation)
    except Exception as error:
        result.update(curveReadStatus="duration_api_call_failed", curveReadError="get_sequence_length: " + str(error))
        return result
    if isinstance(duration, bool) or not isinstance(duration, (int, float)):
        result.update(curveReadStatus="duration_invalid", curveReadError="duration must be a finite positive number: " + repr(duration))
        return result
    try:
        duration = float(duration)
    except (ValueError, OverflowError) as error:
        result.update(curveReadStatus="duration_invalid", curveReadError=str(error))
        return result
    if not math.isfinite(duration) or duration <= 0.0:
        result.update(curveReadStatus="duration_invalid", curveReadError="duration must be finite and positive: " + repr(duration))
        return result
    result["durationSeconds"] = duration

    try:
        names = library.get_animation_curve_names(animation, curve_type)
    except Exception as error:
        result.update(curveReadStatus="api_call_failed", curveReadError="get_animation_curve_names: " + str(error))
        return result
    try:
        if names is None or isinstance(names, (str, bytes, dict)):
            raise ValueError("curve names must be a sequence of names.")
        name_strings = sorted(str(name) for name in names)
        if any(not name for name in name_strings) or len(set(name_strings)) != len(name_strings):
            raise ValueError("curve names contain empty or duplicate entries.")
    except (TypeError, ValueError) as error:
        result.update(curveReadStatus="curve_names_invalid", curveReadError=str(error))
        return result
    result["curveNames"] = name_strings
    result["requiredCurvesPresent"] = all(name in name_strings for name in REQUIRED_PROFILE_CURVES)
    if not result["requiredCurvesPresent"]:
        result.update(curveReadStatus="required_curves_missing",
                      missingRequiredCurves=[name for name in REQUIRED_PROFILE_CURVES if name not in name_strings])
        return result

    keys_by_curve: Dict[str, List[Tuple[float, float]]] = {}
    for curve_name in REQUIRED_PROFILE_CURVES:
        try:
            raw_keys = library.get_float_keys(animation, curve_name)
        except Exception as error:
            result.update(curveReadStatus="key_api_call_failed", failedCurve=curve_name,
                          curveReadError="get_float_keys(" + curve_name + "): " + str(error))
            return result
        try:
            keys_by_curve[curve_name] = _curve_keys_from_result(raw_keys, duration)
        except ValueError as error:
            result.update(curveReadStatus="key_data_invalid", failedCurve=curve_name,
                          curveReadError="get_float_keys(" + curve_name + "): " + str(error))
            return result

    # Preserve the existing key-only fingerprint algorithm for schema compatibility.
    payload = {
        "objectPath": result.get("actualObjectPath", object_path),
        "curves": {
            name: [[time_value, key_value] for time_value, key_value in keys_by_curve[name]]
            for name in REQUIRED_PROFILE_CURVES
        },
    }
    result["curveKeyCounts"] = {name: len(keys) for name, keys in keys_by_curve.items()}
    result["curvePayloadSha256"] = _sha256_bytes(
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    )
    result["curveReadStatus"] = "fingerprinted"
    return result


def _unreal_readback(profiles: Sequence[Dict[str, Any]]) -> Dict[str, Any]:
    if _UNREAL is None:
        return {
            "environment": "offline_python",
            "status": "unavailable",
            "detail": "Unreal Python module is not present; no CDO or package contents were read.",
        }

    read_api = _resolve_animation_read_api(_UNREAL)
    animation_curves = []
    for profile in profiles:
        animation_curves.append(_read_animation_curve_fingerprint(_UNREAL, profile["sourceObjectPath"], read_api))
    return {
        "environment": "unreal_python",
        "status": "read_only_inspection_attempted",
        "packageWriteCallsMade": False,
        "animationReadAPI": read_api[2],
        "animationCurveReadbackComplete": len(animation_curves) == len(PROFILE_SOURCES)
            and all(item["curveReadStatus"] == "fingerprinted" for item in animation_curves),
        "animBlueprint": _anim_blueprint_readback(_UNREAL),
        "walkRunBlendSpace": _blend_space_readback(_UNREAL),
        "movementSet": _movement_set_readback(_UNREAL),
        "animationCurveFingerprints": animation_curves,
    }



def _snapshot_float(value: Any, bits: int, label: str) -> float:
    """Reuse R3's exact native-float widening check, including signed zero."""
    if type(value) is not float or not math.isfinite(value):
        raise ValueError(label + ": expected a finite native float")
    if bits == 32 and struct.pack("<d", struct.unpack("<f", struct.pack("<f", value))[0]) != struct.pack("<d", value):
        raise ValueError(label + ": native float32 did not widen losslessly")
    return value


def _snapshot_int(value: Any, label: str) -> int:
    if type(value) is not int or not -(2 ** 31) <= value < 2 ** 31:
        raise ValueError(label + ": expected native int32")
    return value


def _snapshot_numeric_bits(value: Any) -> Any:
    if type(value) is float:
        return {"pythonBinary64LittleEndian": struct.pack("<d", value).hex()}
    if isinstance(value, dict):
        return {key: _snapshot_numeric_bits(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_snapshot_numeric_bits(item) for item in value]
    return value


def _complete_snapshot_payload(unreal_module: Any, result: Any, source_path: str) -> Dict[str, Any]:
    """Copy the fixed public DTO fields verified by R3; never reconstruct keys."""
    if not isinstance(result, unreal_module.GGYGOFloatCurveReadResult):
        raise TypeError(source_path + ": unexpected Snapshot result type")
    if type(result.succeeded) is not bool or type(result.error) is not str:
        raise TypeError(source_path + ": invalid succeeded/error fields")
    duration = _snapshot_float(result.duration_seconds, 64, source_path + ".duration_seconds")
    if not isinstance(result.curves, unreal_module.Array):
        raise TypeError(source_path + ": curves must be unreal.Array")
    if not result.succeeded:
        if result.curves or struct.pack("<d", duration) != struct.pack("<d", 0.0):
            raise ValueError(source_path + ": invalid failure payload; original error: " + result.error)
        raise RuntimeError(result.error)
    if result.error or duration <= 0.0 or len(result.curves) != len(REQUIRED_PROFILE_CURVES):
        raise ValueError(source_path + ": invalid successful Snapshot error/duration/curve count")

    curves = []
    float_fields = ("time", "value", "arrive_tangent", "leave_tangent",
                    "arrive_tangent_weight", "leave_tangent_weight")
    int_fields = ("interp_mode", "tangent_mode", "tangent_weight_mode")
    for index, curve in enumerate(result.curves):
        label = source_path + "." + REQUIRED_PROFILE_CURVES[index]
        if not isinstance(curve, unreal_module.GGYGOFloatCurveSnapshot):
            raise TypeError(label + ": unexpected curve DTO type")
        if not isinstance(curve.name, unreal_module.Name) or str(curve.name) != REQUIRED_PROFILE_CURVES[index]:
            raise ValueError(label + ": requested curve name/order differs")
        if not isinstance(curve.keys, unreal_module.Array) or not curve.keys:
            raise ValueError(label + ": keys must be a non-empty unreal.Array")
        keys = []
        for key_index, key in enumerate(curve.keys):
            key_label = label + ".keys[%d]" % key_index
            if not isinstance(key, unreal_module.GGYGOFloatCurveKeySnapshot):
                raise TypeError(key_label + ": unexpected key DTO type")
            values = {field: _snapshot_float(getattr(key, field), 32, key_label + "." + field)
                      for field in float_fields}
            values.update({field: _snapshot_int(getattr(key, field), key_label + "." + field)
                           for field in int_fields})
            keys.append(values)
        curves.append({
            "name": str(curve.name),
            "flags": _snapshot_int(curve.flags, label + ".flags"),
            "default_value": _snapshot_float(curve.default_value, 32, label + ".default_value"),
            "pre_infinity_extrap": _snapshot_int(curve.pre_infinity_extrap, label + ".pre_infinity_extrap"),
            "post_infinity_extrap": _snapshot_int(curve.post_infinity_extrap, label + ".post_infinity_extrap"),
            "keys": keys,
        })
    payload = {"objectPath": source_path, "duration_seconds": duration, "curves": curves}
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    bits = _snapshot_numeric_bits(payload)
    if bits != _snapshot_numeric_bits(json.loads(encoded)):
        raise ValueError(source_path + ": JSON changed Snapshot numeric bits or fields")
    return {
        "payload": payload,
        "fullSnapshotSha256": _sha256_bytes(json.dumps(
            bits, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")),
        "fingerprintDefinition": "objectPath/duration/name/flags/default/pre/post/ordered keys; floats as widened binary64 little-endian hex",
        "jsonNumericRoundtripVerified": True,
    }


def _exact_asset_path(path: str, label: str) -> str:
    if not isinstance(path, str) or path != path.strip() or not path.startswith("/") or path.count("/") < 2:
        raise ValueError(label + ": supply one explicit absolute asset path")
    package, separator, object_name = path.partition(".")
    if any(not part for part in package[1:].split("/")) or ":" in path or "\\" in path:
        raise ValueError(label + ": invalid asset path")
    expected_name = package.rsplit("/", 1)[1]
    if separator and object_name != expected_name:
        raise ValueError(label + ": package/object names differ")
    return package + "." + expected_name


def _formal_input_bindings(config: Any) -> Dict[str, Any]:
    result = {}
    for property_name in ("native_input_actions", "ability_input_actions"):
        records = []
        for index, binding in enumerate(config.get_editor_property(property_name)):
            action = binding.get_editor_property("input_action")
            tag = str(binding.get_editor_property("input_tag").get_editor_property("tag_name"))
            if action is None or tag in ("", "None"):
                raise ValueError(config.get_path_name() + "." + property_name + "[%d]: missing action/tag" % index)
            records.append({"inputTag": tag, "inputActionObjectPath": action.get_path_name()})
        result[property_name] = records
    return result


def _formal_configuration_readback(unreal_module: Any, pawn_data_path: Optional[str]) -> Dict[str, Any]:
    result = {
        "status": "failed", "complete": False, "explicitPawnDataInput": pawn_data_path,
        "selection": "Caller-supplied PawnData only; no Default candidate or asset-name search",
        "coverageLimit": "Static configuration references/CDOs; no spawned Pawn, input binding, CMC readiness or Run proof",
    }
    try:
        expected = _exact_asset_path(pawn_data_path, "formal_pawn_data_object_path")
        pawn_data = unreal_module.load_asset(expected)
        if not isinstance(pawn_data, unreal_module.GGYGOPawnData) or pawn_data.get_path_name() != expected:
            raise ValueError(expected + ": missing/wrong-class/identity-mismatched PawnData")
        result["pawnDataObjectPath"] = pawn_data.get_path_name()
        movement = pawn_data.get_editor_property("movement_set")
        input_config = pawn_data.get_editor_property("input_config")
        pawn_class = pawn_data.get_editor_property("pawn_class")
        if not isinstance(movement, unreal_module.GGYGOMovementSet):
            raise ValueError(expected + ".movement_set: missing or wrong class")
        result["movementSetObjectPath"] = movement.get_path_name()
        if not isinstance(input_config, unreal_module.GGYGOInputConfig):
            raise ValueError(expected + ".input_config: missing or wrong class")
        result["inputConfigObjectPath"] = input_config.get_path_name()
        if pawn_class is None:
            raise ValueError(expected + ".pawn_class: missing")
        pawn_cdo = unreal_module.get_default_object(pawn_class)
        if not isinstance(pawn_cdo, unreal_module.Character):
            raise ValueError(expected + ".pawn_class: expected a Character CDO for the formal locomotion route")
        result["pawnClassObjectPath"] = pawn_cdo.get_class().get_path_name()
        mesh = pawn_cdo.get_editor_property("mesh")
        if not isinstance(mesh, unreal_module.SkeletalMeshComponent):
            raise ValueError(result["pawnClassObjectPath"] + ".mesh: missing or wrong class")
        result["meshComponentObjectPath"] = mesh.get_path_name()
        anim_class = mesh.get_editor_property("anim_class")
        if anim_class is None:
            raise ValueError(result["meshComponentObjectPath"] + ".anim_class: missing")
        anim_cdo = unreal_module.get_default_object(anim_class)
        if not isinstance(anim_cdo, unreal_module.AnimInstance):
            raise ValueError(result["meshComponentObjectPath"] + ".anim_class: wrong class")
        result["animClassObjectPath"] = anim_cdo.get_class().get_path_name()
        result["inputBindings"] = _formal_input_bindings(input_config)
        references = {}
        issues = []
        for source in PROFILE_SOURCES:
            field = source["movementSetProperty"]
            profile = movement.get_editor_property(_snake_case(field))
            if profile is not None and not isinstance(profile, unreal_module.GGYGOLocomotionMotionProfile):
                raise ValueError(movement.get_path_name() + "." + field + ": wrong Profile class")
            references[field] = {"isNull": profile is None, "objectPath": profile.get_path_name() if profile is not None else None}
            if profile is None:
                issues.append({"field": field, "reason": "required Profile reference is null"})
        result.update(status="read", complete=True, profileReferences=references,
                      configurationIssues=issues, profileReferencesComplete=not issues)
    except Exception as error:
        result["error"] = str(error)
    return result


def _snapshot_dirty_packages(unreal_module: Any) -> Dict[str, List[str]]:
    utils = unreal_module.EditorLoadingAndSavingUtils
    return {
        "content": sorted(package.get_path_name() for package in utils.get_dirty_content_packages()),
        "maps": sorted(package.get_path_name() for package in utils.get_dirty_map_packages()),
    }


def _full_snapshot_readback(
    root: Path, profiles: Sequence[Dict[str, Any]], pawn_data_path: Optional[str],
) -> Dict[str, Any]:
    result: Dict[str, Any] = {
        "status": "failed", "complete": False, "snapshotCallCount": 0, "snapshots": [],
        "formalConfiguration": {"status": "not_attempted", "complete": False,
                                "explicitPawnDataInput": pawn_data_path},
        "errors": [], "packageWriteCallsMade": False, "assetMigrationValidated": False,
        "coverageLimit": "Current public DataModel Snapshot values and explicit static configuration; no Channel/disk semantic equality or production Run",
    }
    if _UNREAL is None:
        result.update(status="unavailable")
        result["errors"].append("Unreal Python is unavailable; complete Snapshot/formal references were not read.")
        return result
    before = None
    try:
        before = _snapshot_dirty_packages(_UNREAL)
        result["dirtyBefore"] = before
        _UNREAL.load_module("GGYGOEditor")
        method = _UNREAL.GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot
        if not callable(method):
            raise TypeError("GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot is not callable")
        for symbol in ("GGYGOFloatCurveReadResult", "GGYGOFloatCurveSnapshot", "GGYGOFloatCurveKeySnapshot"):
            getattr(_UNREAL, symbol)  # Fixed R3 types; absence is an explicit API failure.
        result["api"] = "unreal.GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot"
        names = [_UNREAL.Name(name) for name in REQUIRED_PROFILE_CURVES]
        if len(profiles) != 7 or len({p["sourceObjectPath"] for p in profiles}) != 7:
            raise ValueError("Expected exactly seven distinct PROFILE_SOURCES")
        for profile in profiles:
            path = profile["sourceObjectPath"]
            entry: Dict[str, Any] = {"sourceObjectPath": path, "status": "failed"}
            result["snapshots"].append(entry)
            try:
                expected_path = _exact_asset_path(path, "sourceObjectPath")
                disk = root / profile["sourceDiskPath"]
                entry["sourceAssetSha256Before"] = _sha256_file(disk)
                if not _is_sha256(entry["sourceAssetSha256Before"]):
                    raise ValueError(path + ": source .uasset is missing/unreadable")
                if entry["sourceAssetSha256Before"] != profile["sourceAssetSha256"]:
                    raise ValueError(path + ": source hash changed after the legacy candidate audit")
                source = _UNREAL.load_asset(path)
                if not isinstance(source, _UNREAL.AnimSequence) or source.get_path_name() != expected_path:
                    raise ValueError(path + ": missing/wrong-class/identity-mismatched AnimSequence")
                result["snapshotCallCount"] += 1
                entry.update(_complete_snapshot_payload(_UNREAL, method(source, names), source.get_path_name()))
                entry["sourceAssetSha256After"] = _sha256_file(disk)
                if entry["sourceAssetSha256Before"] != entry["sourceAssetSha256After"]:
                    raise ValueError(path + ": source hash changed during Snapshot read")
                entry["status"] = "read"
            except Exception as error:
                entry["error"] = str(error)
                result["errors"].append(path + ": " + str(error))
        result["formalConfiguration"] = _formal_configuration_readback(_UNREAL, pawn_data_path)
        if not result["formalConfiguration"]["complete"]:
            result["errors"].append("Formal configuration: " + result["formalConfiguration"].get("error", "not read"))
    except Exception as error:
        result["errors"].append("Complete Snapshot API/readback: " + str(error))
    finally:
        try:
            after = _snapshot_dirty_packages(_UNREAL)
            result["dirtyAfter"] = after
            if before is None or before != after:
                result["errors"].append("Dirty package sets changed or the initial dirty set was unavailable.")
            source_packages = {profile["sourceObjectPath"].split(".", 1)[0] for profile in profiles}
            dirty_sources = source_packages.intersection((before or {}).get("content", []) + after["content"])
            if dirty_sources:
                result["errors"].append("Source packages are dirty: " + ", ".join(sorted(dirty_sources)))
            for entry in result["snapshots"]:
                profile = next(p for p in profiles if p["sourceObjectPath"] == entry["sourceObjectPath"])
                final_hash = _sha256_file(root / profile["sourceDiskPath"])
                entry["sourceAssetSha256Final"] = final_hash
                if final_hash != entry.get("sourceAssetSha256Before"):
                    result["errors"].append(entry["sourceObjectPath"] + ": source hash changed before final publication")
        except Exception as error:
            result["errors"].append("Final read-only protection: " + str(error))
    result["complete"] = (
        not result["errors"] and result["snapshotCallCount"] == 7
        and len(result["snapshots"]) == 7 and all(item["status"] == "read" for item in result["snapshots"])
        and result["formalConfiguration"]["complete"]
    )
    if result["complete"]:
        result["status"] = "complete_readback_only"
    return result


def _static_source_evidence(root: Path) -> Dict[str, Any]:
    sources = {
        "blendSpaceCreator": "AAADocs/Scripts/create_walkrun_blendspace.py",
        "blendSpaceAxisReader": "AAADocs/Scripts/fix_blendspace_axis.py",
        "movementAssetOrganizer": "AAADocs/Scripts/organize_movement_assets.py",
        "animBlueprintStateNotes": "Source/GGYGO/Animation/zzzAnim/ZZZAnimInstance.h",
        "animStopMapping": "Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionRules.cpp",
        "legacySerializedField": "Source/GGYGO/Animation/zzzAnim/Data/ZZZAnimStateMemory.h",
        "movementSetProfileProperties": "Source/GGYGO/Character/Data/GGYGOMovementSet.h",
    }
    return {
        key: {
            "path": value,
            "exists": (root / Path(value)).is_file(),
        }
        for key, value in sources.items()
    }


def _build_report(root: Path, formal_pawn_data_object_path: Optional[str] = None) -> Dict[str, Any]:
    manifest, manifest_record = _load_manifest(root)
    profiles = _profile_records(root, manifest)
    stops = _stop_map_records(root)

    core_assets = [
        _asset_record(root, ANIM_BLUEPRINT_OBJECT_PATH, "animationBlueprint"),
        _asset_record(root, WALK_RUN_OBJECT_PATH, "walkRunBlendSpace"),
        _asset_record(root, MOVEMENT_SET_OBJECT_PATH, "candidateDefaultMovementSet"),
    ]
    source_assets = []
    for profile in profiles:
        source_assets.append(
            {
                "objectPath": profile["sourceObjectPath"],
                "diskPath": profile["sourceDiskPath"],
                "exists": profile["sourceAssetExists"],
                "fileBytes": profile["sourceAssetBytes"],
                "fileSha256": profile["sourceAssetSha256"],
            }
        )

    readback = _unreal_readback(profiles)
    full_readback = _full_snapshot_readback(root, profiles, formal_pawn_data_object_path)

    missing_items: List[Dict[str, Any]] = []
    for asset in core_assets + source_assets:
        if not asset["exists"]:
            missing_items.append({"kind": "required_source_asset_missing", "objectPath": asset["objectPath"], "diskPath": asset["diskPath"]})
    if not manifest_record["exists"] or manifest is None:
        missing_items.append({"kind": "root_motion_manifest_missing_or_invalid", "path": manifest_record["path"]})
    if manifest is not None and not _is_sha256(manifest_record.get("fileSha256")):
        missing_items.append({"kind": "root_motion_manifest_fingerprint_missing_or_invalid", "path": manifest_record["path"]})
    for profile in profiles:
        if profile["manifestClipMatches"] != 1:
            missing_items.append(
                {
                    "kind": "manifest_clip_missing_or_duplicated",
                    "sourceAnimationName": profile["sourceAnimationName"],
                    "matchCount": profile["manifestClipMatches"],
                }
            )
        elif profile["curveDigestError"]:
            missing_items.append(
                {
                    "kind": "required_curve_data_missing_or_invalid",
                    "sourceAnimationName": profile["sourceAnimationName"],
                    "detail": profile["curveDigestError"],
                }
            )
        elif not profile["curveSampleLengthsMatchTimes"]:
            missing_items.append(
                {
                    "kind": "curve_sample_count_mismatch",
                    "sourceAnimationName": profile["sourceAnimationName"],
                    "sampleCounts": profile["curveSampleCounts"],
                }
            )
        if profile["sourceAssetExists"] and not _is_sha256(profile.get("sourceAssetSha256")):
            missing_items.append(
                {
                    "kind": "source_asset_fingerprint_missing_or_invalid",
                    "sourceAnimationName": profile["sourceAnimationName"],
                    "diskPath": profile["sourceDiskPath"],
                }
            )
        if not profile["suggestedProfileExists"]:
            missing_items.append(
                {
                    "kind": "profile_asset_not_created_pending_ue_window",
                    "suggestedObjectPath": profile["suggestedProfileObjectPath"],
                    "movementSetProperty": profile["movementSetProperty"],
                }
            )

    static_sources = _static_source_evidence(root)
    for source_key, source_record in static_sources.items():
        if not source_record["exists"]:
            missing_items.append({"kind": "static_audit_source_missing", "source": source_key, "path": source_record["path"]})

    validations = [
        {
            "id": "core_asset_paths_exist",
            "status": "pass" if all(asset["exists"] for asset in core_assets) else "fail",
            "checked": [asset["diskPath"] for asset in core_assets],
        },
        {
            "id": "seven_profile_source_animations_exist",
            "status": "pass" if len(profiles) == 7 and all(item["sourceAssetExists"] for item in profiles) else "fail",
            "expectedCount": 7,
            "actualCount": sum(1 for item in profiles if item["sourceAssetExists"]),
        },
        {
            "id": "seven_manifest_clip_curve_fingerprints",
            "status": "pass"
            if len(profiles) == 7
            and all(item["manifestClipMatches"] == 1 and item["manifestCurvePayloadSha256"] for item in profiles)
            else "fail",
            "expectedCount": 7,
            "actualCount": sum(1 for item in profiles if item["manifestClipMatches"] == 1 and item["manifestCurvePayloadSha256"]),
        },
        {
            "id": "source_and_manifest_sha256_fingerprints",
            "status": "pass"
            if _is_sha256(manifest_record.get("fileSha256"))
            and all(_is_sha256(item.get("sourceAssetSha256")) for item in profiles)
            and all(_is_sha256(item.get("manifestCurvePayloadSha256")) for item in profiles)
            else "fail",
            "sourceAssetFingerprintCount": sum(1 for item in profiles if _is_sha256(item.get("sourceAssetSha256"))),
            "manifestCurveFingerprintCount": sum(1 for item in profiles if _is_sha256(item.get("manifestCurvePayloadSha256"))),
            "manifestFileFingerprintPresent": _is_sha256(manifest_record.get("fileSha256")),
        },
        {
            "id": "stop_value_semantics",
            "status": "pass"
            if [(item["stopValue"], item["motionType"]) for item in stops]
            == [(0, "StartStop"), (1, "WalkStop"), (2, "RunStop")]
            else "fail",
        },
        {
            "id": "blend_parameter_naming",
            "status": "pass"
            if NEW_WALK_RUN_PARAMETER == "WalkRunBlendAlpha" and LEGACY_SERIALIZED_PARAMETER == "GaitBlendY"
            else "fail",
            "newName": NEW_WALK_RUN_PARAMETER,
            "legacySerializedCompatibilityName": LEGACY_SERIALIZED_PARAMETER,
        },
        {
            "id": "asset_cdo_readback",
            "status": "pending" if readback["environment"] == "offline_python" else "attempted",
            "state": "PendingUEAssetWindow" if readback["environment"] == "offline_python" else "UE readback details are in unrealReadback",
        },
        {
            "id": "complete_snapshot_and_explicit_formal_source_readback",
            "status": "pass" if full_readback["complete"] else "fail",
            "state": full_readback["status"],
            "errors": full_readback["errors"],
            "evidenceLimit": "Readback only; null Profile references remain explicit configuration issues.",
        },
    ]

    return {
        "schemaVersion": 1,
        "auditMode": "read-only",
        "auditStatus": "PendingUEAssetWindow",
        "generatedBy": "AAADocs/Scripts/audit_locomotion_motion_profiles.py",
        "packageWritesMade": False,
        "assetMigrationWritesMadeByThisBatch": False,
        "scope": "Locomotion profile/AnimBP asset wiring audit; no UE package is modified or saved.",
        "unrealReadback": readback,
        "fullSnapshotReadback": full_readback,
        "currentAssets": {
            "core": core_assets,
            "profileSourceAnimations": source_assets,
            "rootMotionManifest": manifest_record,
        },
        "walkRunBlendSpace": {
            "objectPath": WALK_RUN_OBJECT_PATH,
            "diskPath": _repo_relative(_to_disk_path(root, WALK_RUN_OBJECT_PATH), root),
            "diskAssetExists": _to_disk_path(root, WALK_RUN_OBJECT_PATH).is_file(),
            "expectedClass": "BlendSpace1D",
            "expectedClassEvidence": "AAADocs/Scripts/create_walkrun_blendspace.py constructs unreal.BlendSpaceFactory1D and creates unreal.BlendSpace1D; CDO type is pending UE readback.",
            "axis": {
                "dimension": 1,
                "minimum": 0.0,
                "maximum": 1.0,
                "parameterName": NEW_WALK_RUN_PARAMETER,
                "legacySerializedName": LEGACY_SERIALIZED_PARAMETER,
                "legacyNameUse": "serialization compatibility only; do not use as a new API name",
                "sampleSemantics": [{"value": 0.0, "gait": "Walk"}, {"value": 1.0, "gait": "Run"}],
                "sourceEvidence": [
                    "create_walkrun_blendspace.py adds Walk_Loop at X=0 and Run_Loop at X=1",
                    "fix_blendspace_axis.py sets the axis display name to WalkRunBlendAlpha and range to 0..1",
                ],
                "cdoVerification": "PendingUEAssetWindow",
            },
            "animSetKeyFromCreatorScript": "walkRun",
            "sampleAssetPaths": [
                {"value": 0.0, "objectPath": WALK_RUN_OBJECT_PATH.rsplit("/", 1)[0] + "/Avatar_Male_Size03_Pyrois_Ani_Walk_Loop"},
                {"value": 1.0, "objectPath": WALK_RUN_OBJECT_PATH.rsplit("/", 1)[0] + "/Avatar_Male_Size03_Pyrois_Ani_Run_Loop"},
            ],
        },
        "stopValueMapping": stops,
        "movementSet": {
            "objectPath": MOVEMENT_SET_OBJECT_PATH,
            "diskPath": _repo_relative(_to_disk_path(root, MOVEMENT_SET_OBJECT_PATH), root),
            "candidateAssetExists": _to_disk_path(root, MOVEMENT_SET_OBJECT_PATH).is_file(),
            "profileReferenceProperties": [source["movementSetProperty"] for source in PROFILE_SOURCES],
            "referenceWriteStatus": "PendingUEAssetWindow",
            "referenceWriteNote": "The C++ properties exist; this batch did not author profile asset references into the MovementSet package. Existing CDO values are not inferred offline.",
        },
        "profileSuggestions": profiles,
        "curveFingerprintDefinition": {
            "sourceAssetFingerprint": "SHA-256 of each current source .uasset file on disk.",
            "manifestCurveFingerprint": "SHA-256 of clip name/timing/sample arrays and the four required RootMotion_* profile curves.",
            "requiredCurves": list(REQUIRED_PROFILE_CURVES),
            "profileFieldMapping": {
                "SpeedCurve": "RootMotion_Speed",
                "DirectionXCurve": "RootMotion_DirX",
                "DirectionYCurve": "RootMotion_DirY",
                "YawCurve": "RootMotion_Yaw",
            },
            "crossSourceIdentity": "Not proven by offline hashes: the export manifest carries no source .uasset digest. Compare UE curve readback fingerprint against the exported source during the UE asset window.",
        },
        "animBlueprintWiringAudit": {
            "objectPath": ANIM_BLUEPRINT_OBJECT_PATH,
            "assetWriteStatus": "PendingUEAssetWindow",
            "assetWriteNote": "This batch did not write ABP AnimSet references or graph pins. AnimBP CDO values and graph pins remain unverified until UE readback.",
            "sourceDocumentedStates": ["NotMoving", "EnterMove", "Moving", "Stop", "TurnBack", "WalkRun"],
            "sourceDocumentedStateMachines": ["MainStateMachine", "MainGroundState", "LocomotionState"],
            "sourceDocumentedConduits": ["Conduit"],
            "sourceDocumentedVariables": [
                "AnimationState.bHasMoveInput",
                "StateMemory.GaitBlendY (serialized compatibility field only)",
                "StateMemory.StopValue",
            ],
            "sourceDocumentedFunctions": ["IsAnimationRunGait", "IsTurnBackCurveDriven", "GetSeqByKey", "GetBlendSpaceByKey"],
            "knownBlendSpaceAnimSetKey": "walkRun",
            "migrationConnections": [
                {
                    "from": "Movement-authoritative FGGYGOAnimationStateFrame.WalkRunBlendAlpha",
                    "to": "AnimBP WalkRun BlendSpace1D X input",
                    "semantic": "0=Walk, 1=Run",
                    "status": "PendingUEAssetWindow",
                },
                {
                    "from": "Movement EGGYGOStopMotionType",
                    "to": "AnimBP StateMemory.StopValue",
                    "semantic": "0=StartStop, 1=WalkStop, 2=RunStop",
                    "status": "source mapping exists; asset graph readback pending",
                },
                {
                    "from": "GGYGOMovementSet seven profile reference properties",
                    "to": "seven suggested UGGYGOLocomotionMotionProfile assets",
                    "status": "PendingUEAssetWindow",
                },
            ],
            "evidenceLimit": "State/variable names come from current C++ documentation and source scripts; they are not claimed as independently verified ABP CDO or graph contents.",
        },
        "staticSourceEvidence": static_sources,
        "missingItems": missing_items,
        "validations": validations,
    }


def _write_report_if_changed(output_path: Path, report: Dict[str, Any]) -> bool:
    serialized = json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, allow_nan=False) + "\n"
    if output_path.is_file():
        try:
            if output_path.read_text(encoding="utf-8") == serialized:
                return False
        except (OSError, UnicodeError):
            pass
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(serialized, encoding="utf-8", newline="\n")
    return True


def main(*, formal_pawn_data_object_path: Optional[str] = None) -> Dict[str, Any]:
    root = _find_project_root()
    report = _build_report(root, formal_pawn_data_object_path)
    output_path = root / REPORT_RELATIVE_PATH
    changed = _write_report_if_changed(output_path, report)
    failed = [item["id"] for item in report["validations"] if item["status"] == "fail"]
    print("[LocomotionAudit] report={}".format(_repo_relative(output_path, root)))
    print("[LocomotionAudit] writeMode={} packageWritesMade=false".format("updated-report" if changed else "unchanged-report"))
    print("[LocomotionAudit] status={} profiles={} missingItems={} failedChecks={}".format(
        report["auditStatus"], len(report["profileSuggestions"]), len(report["missingItems"]), ",".join(failed) or "none"
    ))
    return report


if __name__ == "__main__":
    main()
