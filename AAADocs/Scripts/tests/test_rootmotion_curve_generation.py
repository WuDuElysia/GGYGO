"""Offline curve contract tests. Fake Unreal APIs; only small temporary fixtures."""
import copy
import importlib.util
import json
import math
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import anim_rootmotion_extract as extract


def record_from_positions(times, x, y=None):
    y = [0.0] * len(times) if y is None else y
    distance, speed, dx, dy = extract.derive_horizontal_motion(times, x, y)
    curves = {name: [0.0] * len(times) for name in extract.MOTION_CURVES}
    curves.update(RootMotion_PosX=x, RootMotion_PosY=y, RootMotion_Dist=distance,
                  RootMotion_Speed=speed, RootMotion_DirX=dx, RootMotion_DirY=dy)
    return {"name": "Test", "duration": times[-1], "frameCount": len(times),
            "times": times, "curves": curves,
            "scalars": {"startTime": 0.0, "stopTime": times[-1]}}


class FakeAnimation:
    def __init__(self, keys=3, length=1.0):
        self.keys, self.length = keys, length
        self.controller = SimpleNamespace(open_bracket=Mock(), close_bracket=Mock())
        self.get_controller = Mock(return_value=self.controller)
        self.modify = Mock()

    def get_number_of_sampled_keys(self):
        return self.keys

    def get_editor_property(self, name):
        assert name == "sequence_length"
        return self.length


class CurveGenerationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.anim = FakeAnimation()
        self.api = SimpleNamespace(does_curve_exist=Mock(return_value=False),
                                   add_curve=Mock(), remove_curve=Mock(),
                                   add_float_curve_keys=Mock())
        self.unreal = SimpleNamespace(
            RawCurveTrackTypes=SimpleNamespace(RCT_FLOAT=0), Name=str,
            AnimationLibrary=self.api, AnimSequence=FakeAnimation,
            load_asset=Mock(return_value=self.anim), log=Mock())
        spec = importlib.util.spec_from_file_location(
            "test_rootmotion_baker", SCRIPTS / "bake_anim_rootmotion_curves.py")
        self.bake = importlib.util.module_from_spec(spec)
        with patch.dict(sys.modules, unreal=self.unreal):
            spec.loader.exec_module(self.bake)

    def build(self, times, tracks, stop_time=None):
        meta = self.root / "clip.json"
        meta.write_text(json.dumps({"clip": {
            "sampleRate": 1.0 / (times[1] - times[0]) if times[1] > times[0] else 60.0,
            "muscleClip": {"startTime": 0.0,
                           "stopTime": times[-1] if stop_time is None else stop_time}}}),
            encoding="utf-8")
        with patch.object(extract, "read_root_tracks", return_value=(times, tracks)):
            record, error = extract.build_clip_record("Test", "test.fbx", str(meta))
        self.assertIsNone(error)
        return record

    def assert_no_mutation(self):
        self.anim.get_controller.assert_not_called()
        self.api.add_curve.assert_not_called()
        self.api.remove_curve.assert_not_called()
        self.api.add_float_curve_keys.assert_not_called()
        self.anim.modify.assert_not_called()

    def test_normal_axes_angles_distance_and_first_interval_are_preserved(self):
        record = self.build([0.0, 0.5, 1.0], {
            "tZ": [10.0, 13.0, 16.0], "tX": [3.0, 7.0, 11.0], "tY": [5.0, 6.0, 7.0],
            "rY": [179.0, -179.0, -177.0], "rX": [2.0, 3.0, 4.0], "rZ": [2.0, 5.0, 8.0]})
        expected = {"RootMotion_PosX": [0.0, 3.0, 6.0], "RootMotion_PosY": [0.0, 4.0, 8.0],
                    "RootMotion_PosZ": [0.0, 1.0, 2.0], "RootMotion_Yaw": [0.0, 2.0, 4.0],
                    "RootMotion_Pitch": [0.0, 1.0, 2.0], "RootMotion_Roll": [0.0, 3.0, 6.0],
                    "RootMotion_Dist": [0.0, 5.0, 10.0], "RootMotion_Speed": [10.0] * 3,
                    "RootMotion_DirX": [0.6] * 3, "RootMotion_DirY": [0.8] * 3}
        self.assertEqual(record["curves"], expected)
        self.assertEqual(record["duration"], 1.0)
        extract.validate_motion_record(record)

    def test_true_stationary_and_real_stop_have_zero_speed_and_direction(self):
        for x in ([0.0, 0.0, 0.0], [0.0, 1.0, 1.0]):
            with self.subTest(x=x):
                record = record_from_positions([0.0, 0.5, 1.0], list(x))
                extract.validate_motion_record(record)
                self.assertEqual(record["curves"]["RootMotion_Speed"][-1], 0.0)
                self.assertEqual(record["curves"]["RootMotion_DirX"][-1], 0.0)
                self.assertEqual(record["curves"]["RootMotion_DirY"][-1], 0.0)

    def test_original_stop_micro_displacements_keep_speed_and_get_direction(self):
        # Gate87 原两故障帧的实际位移，不修改原 manifest 来制造通过。
        for displacement in (3.096647560596466e-8, 3.0919909477233887e-7):
            with self.subTest(displacement=displacement):
                record = record_from_positions([0.0, 1.0 / 60.0, 2.0 / 60.0],
                                               [0.0, displacement, 2.0 * displacement])
                curves = record["curves"]
                self.assertGreater(curves["RootMotion_Speed"][1], 0.0)
                self.assertEqual(curves["RootMotion_DirX"], [1.0] * 3)
                self.assertEqual(curves["RootMotion_DirY"], [0.0] * 3)
                self.assertEqual(curves["RootMotion_PosX"][1], displacement)
                extract.validate_motion_record(record)
                bad = copy.deepcopy(record)
                bad["curves"]["RootMotion_DirX"][1] = 0.0
                with self.assertRaisesRegex(ValueError, "invalid Speed/Direction at frame 1"):
                    self.bake.bake_clip(bad)
                self.assert_no_mutation()

    def test_short_valid_interval_is_not_silently_skipped(self):
        record = record_from_positions([0.0, 1e-7, 2e-7], [0.0, 1e-8, 2e-8])
        self.assertAlmostEqual(record["curves"]["RootMotion_Speed"][1], 0.1)
        self.assertEqual(record["curves"]["RootMotion_DirX"], [1.0] * 3)
        extract.validate_motion_record(record)

    def test_existing_trailing_duplicate_sampling_convention_is_preserved(self):
        tracks = {name: [0.0] * 3 for name in ("tX", "tY", "tZ", "rX", "rY", "rZ")}
        tracks["tZ"] = [0.0, 2.0, 2.0]
        record = self.build([0.0, 0.5, 1.0], tracks, stop_time=0.5)
        self.assertTrue(record["trailingDuplicateFrame"])
        self.assertEqual(record["curves"]["RootMotion_PosX"], [0.0, 2.0, 2.0])
        self.assertEqual(record["curves"]["RootMotion_Dist"], [0.0, 2.0, 2.0])
        self.assertEqual(record["curves"]["RootMotion_Speed"], [4.0] * 3)
        self.assertEqual(record["curves"]["RootMotion_DirX"], [1.0] * 3)

    def test_invalid_required_source_data_is_rejected_before_asset_load(self):
        valid = record_from_positions([0.0, 0.5, 1.0], [0.0, 1.0, 2.0])
        cases = []
        for times in ([0.0, 0.0, 1.0], [0.0, 0.7, 0.6], [0.0, math.nan, 1.0]):
            bad = copy.deepcopy(valid)
            bad["times"] = times
            cases.append(bad)
        for curve in ("RootMotion_PosZ", "RootMotion_DirY"):
            bad = copy.deepcopy(valid)
            del bad["curves"][curve]
            cases.append(bad)
        for value in (math.nan, math.inf):
            bad = copy.deepcopy(valid)
            bad["curves"]["RootMotion_PosX"][1] = value
            cases.append(bad)
        bad = copy.deepcopy(valid)
        bad["curves"]["RootMotion_Yaw"].pop()
        cases.append(bad)
        bad = copy.deepcopy(valid)
        bad["duration"] = 2.0
        cases.append(bad)
        bad = copy.deepcopy(valid)
        bad["curves"]["RootMotion_Speed"][1] = -1.0
        cases.append(bad)
        bad = copy.deepcopy(valid)
        bad["curves"]["RootMotion_Speed"][1] = 0.0
        cases.append(bad)
        for bad in cases:
            with self.subTest(bad=bad):
                with self.assertRaises(ValueError):
                    self.bake.bake_clip(bad)
                self.assert_no_mutation()
                self.unreal.load_asset.assert_not_called()

    def test_invalid_target_or_float32_time_collision_is_rejected_before_write(self):
        valid = record_from_positions([0.0, 0.5, 1.0], [0.0, 1.0, 2.0])
        for keys, length in ((0, 1.0), (1, 1.0), (3, 0.0), (3, math.inf)):
            with self.subTest(keys=keys, length=length):
                self.anim.keys, self.anim.length = keys, length
                with self.assertRaises(ValueError):
                    self.bake.bake_clip(valid)
                self.assert_no_mutation()
        collision = record_from_positions([0.0, 1.0, 1.0 + 1e-9], [0.0, 1.0, 2.0])
        self.anim.keys, self.anim.length = 3, collision["duration"]
        with self.assertRaisesRegex(ValueError, "time must strictly increase"):
            self.bake.bake_clip(collision)
        self.assert_no_mutation()

    def test_float32_underflow_and_overflow_reject_without_clamping(self):
        for displacement, reason in ((1e-46, "underflows"), (1e40, "overflows")):
            with self.subTest(displacement=displacement):
                record = record_from_positions([0.0, 0.5, 1.0],
                                               [0.0, displacement, 2 * displacement])
                with self.assertRaisesRegex(ValueError, reason):
                    self.bake.bake_clip(record)
                self.assert_no_mutation()

    def test_resampling_direction_cancellation_rejects_before_write(self):
        record = record_from_positions([0.0, 1.0], [0.0, 1.0])
        record["curves"]["RootMotion_DirX"] = [1.0, -1.0]
        with self.assertRaisesRegex(ValueError, "planned: invalid Speed/Direction at frame 1"):
            self.bake.bake_clip(record)
        self.assert_no_mutation()

    def test_nonfinite_optional_scalar_is_rejected_before_any_motion_curve_write(self):
        record = record_from_positions([0.0, 0.5, 1.0], [0.0, 1.0, 2.0])
        record["scalars"]["cycleOffset"] = math.nan
        with self.assertRaisesRegex(ValueError, "cycleOffset.*non-finite"):
            self.bake.bake_clip(record)
        self.assert_no_mutation()

    def test_compression_only_removes_truly_constant_keys(self):
        times = [0.0, 0.5, 1.0]
        self.assertEqual(self.bake.compress_constant(times, [7.0] * 3),
                         ([0.0, 1.0], [7.0, 7.0]))
        small = [0.0, 1e-8, 2e-8]
        self.assertEqual(self.bake.compress_constant(times, small), (times, small))
        record = record_from_positions(times, small)
        writes, resampled = self.bake.prepare_curve_writes(record, 3, 1.0)
        self.assertFalse(resampled)
        self.assertEqual(len(writes["RootMotion_PosX"][0]), 3)
        self.assertGreater(writes["RootMotion_PosX"][1][1], 0.0)

    def test_valid_micro_motion_reaches_fake_baker_with_unit_direction(self):
        record = record_from_positions([0.0, 0.5, 1.0], [0.0, 1e-8, 2e-8])
        status, detail = self.bake.bake_clip(record)
        self.assertEqual(status, "ok")
        self.assertEqual(detail["curveCount"], len(self.bake.MOTION_CURVES)
                         + len(self.bake.SCALAR_CURVES) + 3)
        self.anim.controller.open_bracket.assert_called_once()
        self.anim.controller.close_bracket.assert_called_once()
        self.anim.modify.assert_called_once()
        written = {call.args[1]: call.args[3]
                   for call in self.api.add_float_curve_keys.call_args_list}
        self.assertGreater(written["RootMotion_Speed"][0], 0.0)
        self.assertEqual(written["RootMotion_DirX"], [1.0, 1.0])
        self.assertEqual(len(written["RootMotion_PosX"]), 3)

    def test_bad_later_manifest_record_is_rejected_before_batch_mutation(self):
        valid = record_from_positions([0.0, 0.5, 1.0], [0.0, 1.0, 2.0])
        bad = copy.deepcopy(valid)
        bad["name"] = "LaterBad"
        bad["curves"]["RootMotion_DirX"][1] = 0.0
        source = self.root / "source.json"
        source.write_text(json.dumps({"clips": [valid, bad]}), encoding="utf-8")
        self.bake.SOURCE_JSON = str(source)
        with self.assertRaisesRegex(ValueError, "LaterBad.*invalid Speed/Direction"):
            self.bake.run()
        self.unreal.load_asset.assert_not_called()
        self.assert_no_mutation()

    def test_invalid_generation_keeps_existing_output_unchanged(self):
        times = [0.0, 0.0, 1.0]
        tracks = {name: [0.0] * 3 for name in ("tX", "tY", "tZ", "rX", "rY", "rZ")}
        output = self.root / "existing.json"
        output.write_bytes(b"original output")
        (self.root / "Test.json").write_text('{"clip": {}}', encoding="utf-8")
        with patch.object(extract.glob, "glob", return_value=[str(self.root / "Test.fbx")]), \
                patch.object(extract, "read_root_tracks", return_value=(times, tracks)), \
                patch.object(sys, "argv", ["extract", str(self.root), str(output)]):
            with self.assertRaisesRegex(ValueError, "generation rejected; output unchanged"):
                extract.main()
        self.assertEqual(output.read_bytes(), b"original output")

    def test_nonfinite_output_is_rejected_before_truncating_existing_manifest(self):
        tracks = {name: [0.0] * 3 for name in ("tX", "tY", "tZ", "rX", "rY", "rZ")}
        record = self.build([0.0, 0.5, 1.0], tracks)
        record["scalars"]["cycleOffset"] = math.inf
        output = self.root / "existing.json"
        output.write_bytes(b"original output")
        (self.root / "Test.json").write_text('{"clip": {}}', encoding="utf-8")
        with patch.object(extract.glob, "glob", return_value=[str(self.root / "Test.fbx")]), \
                patch.object(extract, "build_clip_record", return_value=(record, None)), \
                patch.object(sys, "argv", ["extract", str(self.root), str(output)]), \
                patch("builtins.print"):
            with self.assertRaisesRegex(ValueError, "invalid output data; output unchanged"):
                extract.main()
        self.assertEqual(output.read_bytes(), b"original output")


if __name__ == "__main__":
    unittest.main()
