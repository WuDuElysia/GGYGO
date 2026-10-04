"""Fake-Unreal tests; never execute the audit entry point or modify real reports."""

import hashlib
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).resolve().parents[1] / "audit_locomotion_motion_profiles.py"
SPEC = importlib.util.spec_from_file_location("locomotion_readback_under_test", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
with patch.dict(sys.modules, {"unreal": None}):
    SPEC.loader.exec_module(AUDIT)

OBJECT_PATH = "/Game/Animation/ReadbackFixture"


class FakeAnimation:
    def get_path_name(self):
        return OBJECT_PATH + ".ReadbackFixture"

    def get_class(self):
        return SimpleNamespace(get_name=lambda: "AnimSequence")


def fake_unreal():
    events = []
    animation = FakeAnimation()
    keys = {name: ([0.0, 1.0], [0.0, 10.0]) for name in AUDIT.REQUIRED_PROFILE_CURVES}
    curve_type = object()
    library = SimpleNamespace(
        get_sequence_length=Mock(side_effect=lambda asset: events.append("length") or 1.0),
        get_animation_curve_names=Mock(side_effect=lambda asset, kind: events.append("names") or list(AUDIT.REQUIRED_PROFILE_CURVES)),
        get_float_keys=Mock(side_effect=lambda asset, name: events.append("keys:" + name) or keys[name]),
    )
    unreal = SimpleNamespace(
        RawCurveTrackTypes=SimpleNamespace(RCT_FLOAT=curve_type),
        load_asset=Mock(side_effect=lambda path: events.append("asset") or animation),
        # An obsolete symbol must never be used as an alternate library.
        AnimationBlueprintLibrary=Mock(),
    )

    def load_module(name):
        events.append("module:" + name)
        unreal.AnimationLibrary = library
        return None

    unreal.load_module = Mock(side_effect=load_module)
    return unreal, library, keys, events, animation, curve_type


class LocomotionReadbackAPITests(unittest.TestCase):
    def assert_failure(self, result, status, detail=None):
        self.assertEqual(result["curveReadStatus"], status)
        self.assertNotIn("curvePayloadSha256", result)
        self.assertNotIn("curveKeyCounts", result)
        self.assertEqual(result["objectPath"], OBJECT_PATH)
        if detail:
            self.assertIn(detail, result["curveReadError"])

    def test_real_script_name_and_module_call_order(self):
        unreal, library, _, events, animation, kind = fake_unreal()
        self.assertFalse(hasattr(unreal, "AnimationLibrary"))
        result = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
        self.assertEqual(result["curveReadStatus"], "fingerprinted")
        self.assertEqual(events[:4], ["module:AnimationBlueprintLibrary", "asset", "length", "names"])
        unreal.load_module.assert_called_once_with("AnimationBlueprintLibrary")
        library.get_animation_curve_names.assert_called_once_with(animation, kind)
        library.get_sequence_length.assert_called_once_with(animation)
        self.assertEqual(library.get_float_keys.call_count, 4)
        self.assertEqual(unreal.AnimationBlueprintLibrary.mock_calls, [])
        self.assertEqual(result["curveReadAPI"]["librarySymbol"], "unreal.AnimationLibrary")
        self.assertTrue(result["curveReadAPI"]["moduleLoadCallCompleted"])

    def test_missing_module_api_is_explicit(self):
        unreal, _, _, _, _, _ = fake_unreal()
        del unreal.load_module
        self.assert_failure(AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH),
                            "module_api_unavailable", "unreal.load_module")
        unreal.load_asset.assert_not_called()

    def test_module_failure_does_not_use_existing_symbols(self):
        unreal, library, _, _, _, _ = fake_unreal()
        unreal.AnimationLibrary = library
        unreal.load_module.side_effect = RuntimeError("DLL failed to load")
        self.assert_failure(AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH),
                            "module_load_failed", "DLL failed to load")
        unreal.load_asset.assert_not_called()
        library.get_sequence_length.assert_not_called()

    def test_missing_real_library_does_not_use_obsolete_name(self):
        unreal, _, _, _, _, _ = fake_unreal()
        unreal.load_module.side_effect = None
        self.assert_failure(AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH),
                            "library_unavailable", "unreal.AnimationLibrary")
        self.assertEqual(unreal.AnimationBlueprintLibrary.mock_calls, [])

    def test_missing_exact_enum_does_not_guess_other_enums(self):
        for missing in ("enum", "entry"):
            with self.subTest(missing=missing):
                unreal, _, _, _, _, _ = fake_unreal()
                unreal.AnimationCurveType = SimpleNamespace(FLOAT=0)
                if missing == "enum":
                    del unreal.RawCurveTrackTypes
                else:
                    unreal.RawCurveTrackTypes = SimpleNamespace(FLOAT=0)
                self.assert_failure(AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH),
                                    "curve_type_unavailable", "RawCurveTrackTypes.RCT_FLOAT")
                unreal.load_asset.assert_not_called()

    def test_each_required_method_is_checked_before_calls(self):
        for method in ("get_sequence_length", "get_animation_curve_names", "get_float_keys"):
            with self.subTest(method=method):
                unreal, library, _, _, _, _ = fake_unreal()
                delattr(library, method)
                library.get_float_curve_keys = Mock()
                result = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
                self.assert_failure(result, "api_unavailable", method)
                self.assertEqual(result["curveReadAPI"]["missingMethods"], [method])
                unreal.load_asset.assert_not_called()
                library.get_float_curve_keys.assert_not_called()

    def test_asset_loading_failures_are_not_success(self):
        for value in (None, RuntimeError("fixture asset load failed")):
            with self.subTest(value=value):
                unreal, library, _, _, _, _ = fake_unreal()
                unreal.load_asset.side_effect = value if isinstance(value, Exception) else None
                unreal.load_asset.return_value = value
                result = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
                self.assert_failure(result, "asset_load_failed" if isinstance(value, Exception) else "asset_not_loaded")
                self.assertIn("loadError", result)
                library.get_sequence_length.assert_not_called()

    def test_duration_api_exception(self):
        unreal, library, _, _, _, _ = fake_unreal()
        library.get_sequence_length.side_effect = RuntimeError("length unavailable")
        self.assert_failure(AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH),
                            "duration_api_call_failed", "get_sequence_length: length unavailable")
        library.get_animation_curve_names.assert_not_called()

    def test_invalid_duration_never_becomes_zero_success(self):
        for duration in (None, True, "1", (), 0, -1, float("nan"), float("inf"), 10 ** 400):
            with self.subTest(duration=duration):
                unreal, library, _, _, _, _ = fake_unreal()
                library.get_sequence_length.side_effect = None
                library.get_sequence_length.return_value = duration
                self.assert_failure(AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH), "duration_invalid")
                library.get_float_keys.assert_not_called()

    def test_names_api_exception(self):
        unreal, library, _, _, _, _ = fake_unreal()
        library.get_animation_curve_names.side_effect = RuntimeError("curve names unavailable")
        self.assert_failure(AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH),
                            "api_call_failed", "get_animation_curve_names")

    def test_malformed_names_are_explicit(self):
        for names in (None, "RootMotion_Speed", 7, {}, [""], list(AUDIT.REQUIRED_PROFILE_CURVES) * 2):
            with self.subTest(names=names):
                unreal, library, _, _, _, _ = fake_unreal()
                library.get_animation_curve_names.side_effect = None
                library.get_animation_curve_names.return_value = names
                self.assert_failure(AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH), "curve_names_invalid")
                library.get_float_keys.assert_not_called()

    def test_missing_required_curve_names(self):
        for names in ([], list(AUDIT.REQUIRED_PROFILE_CURVES[:-1])):
            with self.subTest(names=names):
                unreal, library, _, _, _, _ = fake_unreal()
                library.get_animation_curve_names.side_effect = None
                library.get_animation_curve_names.return_value = names
                result = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
                self.assert_failure(result, "required_curves_missing")
                self.assertFalse(result["requiredCurvesPresent"])
                self.assertIn("RootMotion_Yaw", result["missingRequiredCurves"])
                library.get_float_keys.assert_not_called()

    def test_keys_api_exception_identifies_curve(self):
        unreal, library, _, _, _, _ = fake_unreal()
        library.get_float_keys.side_effect = RuntimeError("keys unavailable")
        result = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
        self.assert_failure(result, "key_api_call_failed", "get_float_keys(RootMotion_Speed)")
        self.assertEqual(result["failedCurve"], "RootMotion_Speed")

    def check_bad_keys(self, key_results, message):
        for key_result in key_results:
            with self.subTest(keys=key_result):
                unreal, _, keys, _, _, _ = fake_unreal()
                keys["RootMotion_Yaw"] = key_result
                result = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
                self.assert_failure(result, "key_data_invalid", message)
                self.assertEqual(result["failedCurve"], "RootMotion_Yaw")

    def test_keys_missing_or_wrong_return_shape(self):
        self.check_bad_keys([None, [], ([0],), ([0], [1], [2]), [[0], [1]]], "invalid key result")

    def test_keys_empty(self):
        self.check_bad_keys([([], [])], "empty keys")

    def test_keys_count_mismatch(self):
        self.check_bad_keys([([0], []), ([], [1]), ([0, 1], [1])], "time/value count mismatch")

    def test_keys_invalid_arrays_and_non_numeric_values(self):
        self.check_bad_keys([(None, None), ("0", [1]), ({0: 0}, [1])], "invalid key arrays")
        self.check_bad_keys([([0], [None]), ([0], ["1"]), ([False], [1]), ([0], [True])], "non-numeric key")

    def test_keys_non_finite(self):
        self.check_bad_keys([([float("nan")], [1]), ([0], [float("inf")]),
                             ([0], [-float("inf")]), ([0], [10 ** 400])], "non-finite key")

    def test_keys_time_bounds_and_order(self):
        self.check_bad_keys([([-0.1], [1]), ([1.1], [1])], "outside [0, duration]")
        self.check_bad_keys([([0, 0], [1, 2]), ([1, 0], [1, 2])], "not strictly increasing")

    def test_success_preserves_hash_algorithm_and_explicit_coverage(self):
        unreal, library, keys, _, animation, _ = fake_unreal()
        first = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
        payload = {"objectPath": animation.get_path_name(),
                   "curves": {name: [[float(t), float(v)] for t, v in zip(*keys[name])]
                              for name in AUDIT.REQUIRED_PROFILE_CURVES}}
        expected = hashlib.sha256(json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                             separators=(",", ":"), allow_nan=False).encode("utf-8")).hexdigest()
        self.assertEqual(first["curvePayloadSha256"], expected)
        self.assertEqual(first["durationSeconds"], 1.0)
        self.assertEqual(first["curveKeyCounts"], dict.fromkeys(AUDIT.REQUIRED_PROFILE_CURVES, 2))
        library.get_animation_curve_names.side_effect = None
        library.get_animation_curve_names.return_value = list(reversed(AUDIT.REQUIRED_PROFILE_CURVES)) + ["UnrelatedCurve"]
        second = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
        self.assertEqual(first["curvePayloadSha256"], second["curvePayloadSha256"])
        library.get_sequence_length.side_effect = None
        library.get_sequence_length.return_value = 2.0
        third = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
        self.assertEqual(first["curvePayloadSha256"], third["curvePayloadSha256"], "duration is validated but not in the legacy key hash")
        coverage = first["curveFingerprintCoverage"]
        self.assertFalse(coverage["migrationAuthorized"])
        self.assertEqual(coverage["included"], ["objectPath", "requiredCurveNames", "keyTimes", "keyValues"])
        self.assertEqual(set(coverage["excluded"]), {"duration", "RichCurveInterpolation", "tangents",
                                                     "tangentWeights", "prePostInfinity", "boneTracks", "graphPins"})
        keys["RootMotion_Speed"] = ([0, 1], [0, 11])
        changed = AUDIT._read_animation_curve_fingerprint(unreal, OBJECT_PATH)
        self.assertNotEqual(first["curvePayloadSha256"], changed["curvePayloadSha256"])

    def read_batch(self, unreal):
        profiles = [{"sourceObjectPath": OBJECT_PATH} for _ in AUDIT.PROFILE_SOURCES]
        with patch.object(AUDIT, "_UNREAL", unreal), \
             patch.object(AUDIT, "_anim_blueprint_readback", return_value={}), \
             patch.object(AUDIT, "_blend_space_readback", return_value={}), \
             patch.object(AUDIT, "_movement_set_readback", return_value={}), \
             patch.object(AUDIT, "_write_report_if_changed", side_effect=AssertionError("must not write report")):
            return AUDIT._unreal_readback(profiles)

    def test_batch_loads_module_once_and_requires_all_seven(self):
        unreal, _, _, _, _, _ = fake_unreal()
        result = self.read_batch(unreal)
        unreal.load_module.assert_called_once_with("AnimationBlueprintLibrary")
        self.assertEqual(len(result["animationCurveFingerprints"]), 7)
        self.assertTrue(result["animationCurveReadbackComplete"])
        self.assertFalse(result["packageWriteCallsMade"])

    def test_batch_reports_module_and_partial_key_failures(self):
        unreal, _, _, _, _, _ = fake_unreal()
        unreal.load_module.side_effect = RuntimeError("module failed")
        result = self.read_batch(unreal)
        self.assertFalse(result["animationCurveReadbackComplete"])
        self.assertEqual(result["animationReadAPI"]["status"], "module_load_failed")
        unreal.load_module.assert_called_once()
        unreal.load_asset.assert_not_called()
        unreal, library, _, _, _, _ = fake_unreal()
        library.get_float_keys.side_effect = [([], [])] + [([0, 1], [0, 10])] * 24
        result = self.read_batch(unreal)
        self.assertFalse(result["animationCurveReadbackComplete"])
        self.assertEqual(result["animationCurveFingerprints"][0]["curveReadStatus"], "key_data_invalid")
        self.assertTrue(all(item["curveReadStatus"] == "fingerprinted" for item in result["animationCurveFingerprints"][1:]))

    def test_offline_behavior_and_report_contract_remain(self):
        with patch.object(AUDIT, "_UNREAL", None), \
             patch.object(AUDIT, "_resolve_animation_read_api", side_effect=AssertionError("offline must not resolve UE API")), \
             patch.object(AUDIT, "_write_report_if_changed", side_effect=AssertionError("must not write report")):
            self.assertEqual(AUDIT._unreal_readback([]), {
                "environment": "offline_python", "status": "unavailable",
                "detail": "Unreal Python module is not present; no CDO or package contents were read.",
            })
            with tempfile.TemporaryDirectory() as temp:
                root = Path(temp)
                report = AUDIT._build_report(root)
                self.assertEqual(report["schemaVersion"], 1)
                self.assertEqual(report["auditStatus"], "PendingUEAssetWindow")
                self.assertFalse(report["packageWritesMade"])
                self.assertFalse(report["assetMigrationWritesMadeByThisBatch"])
                self.assertEqual(len(report["profileSuggestions"]), 7)
                self.assertEqual(report["movementSet"]["objectPath"], "/Game/System/DA_Movement_Default")
                self.assertEqual(report["walkRunBlendSpace"]["objectPath"], AUDIT.WALK_RUN_OBJECT_PATH)
                self.assertEqual([(item["stopValue"], item["motionType"]) for item in report["stopValueMapping"]],
                                 [(0, "StartStop"), (1, "WalkStop"), (2, "RunStop")])
                self.assertFalse((root / AUDIT.REPORT_RELATIVE_PATH).exists())


if __name__ == "__main__":
    unittest.main()
