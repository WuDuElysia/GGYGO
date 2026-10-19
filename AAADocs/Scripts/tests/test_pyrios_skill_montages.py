"""@file test_pyrios_skill_montages.py @brief 制作入口的阶段退出、来源和 create-only 保护离线验证。"""
import importlib.util
import json
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).absolute().parents[1]
def load(name):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + ".py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module

CREATE = load("create_pyrios_skill_montages")
AUDIT = load("audit_pyrios_skill_assets_readonly")


class SkillMontagePreparationTests(unittest.TestCase):
    def receipt(self, root, exit_code=0):
        filename = root / "Saved/Baseline/readback.json"
        filename.parent.mkdir(parents=True)
        baseline = {"schema": AUDIT.SCHEMA, "success": True, "pid": os.getpid() + 1}
        filename.write_text(json.dumps(baseline), encoding="utf-8")
        receipt = {"pid": baseline["pid"], "exit_code": exit_code,
                   "report_sha256": AUDIT.sha(filename)}
        (filename.parent / "host_exit.json").write_text(json.dumps(receipt), encoding="utf-8")
        return filename

    def test_accepts_bound_normal_exit_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            filename = self.receipt(root)
            with patch.object(CREATE, "PROJECT", root):
                self.assertTrue(CREATE.read_receipt(filename, AUDIT.SCHEMA, os.getpid(), AUDIT.sha)["success"])

    def test_success_json_does_not_replace_process_exit(self):
        for exit_code in (-1073741819, 3221225477, False):
            with self.subTest(exit_code=exit_code), tempfile.TemporaryDirectory() as directory:
                root = Path(directory)
                filename = self.receipt(root, exit_code)
                with patch.object(CREATE, "PROJECT", root), self.assertRaises(RuntimeError):
                    CREATE.read_receipt(filename, AUDIT.SCHEMA, os.getpid(), AUDIT.sha)

    def test_rejects_same_pid_and_changed_receipt_identity(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            filename = self.receipt(root)
            with patch.object(CREATE, "PROJECT", root), self.assertRaises(RuntimeError):
                CREATE.read_receipt(filename, AUDIT.SCHEMA, os.getpid() + 1, AUDIT.sha)
            filename.write_text(filename.read_text(encoding="utf-8") + " ", encoding="utf-8")
            with patch.object(CREATE, "PROJECT", root), self.assertRaises(RuntimeError):
                CREATE.read_receipt(filename, AUDIT.SCHEMA, os.getpid(), AUDIT.sha)

    def source_report(self):
        skeleton = AUDIT.SKELETON + "." + AUDIT.SKELETON.rsplit("/", 1)[1]
        return {"schema": AUDIT.SCHEMA, "success": True, "script_sha256": CREATE.AUDIT_SHA, "asset_issues": [],
                "reads": {"sequence:" + package: {"available": True, "value": {
                    "has_position_curves": True, "has_yaw_curve": False, "skeleton": skeleton}}
                    for package in AUDIT.SEQUENCES}}

    def test_explicit_translation_only_and_mixed_yaw(self):
        report = self.source_report()
        CREATE.validate_source_contract(report, AUDIT)
        report["reads"]["sequence:" + AUDIT.SEQUENCES[1]]["value"]["has_yaw_curve"] = True
        with self.assertRaises(RuntimeError):
            CREATE.validate_source_contract(report, AUDIT)

    def test_missing_position_and_wrong_skeleton_rejected(self):
        for field, value in (("has_position_curves", False), ("skeleton", "/Game/Other.Other")):
            report = self.source_report()
            report["reads"]["sequence:" + AUDIT.SEQUENCES[0]]["value"][field] = value
            with self.subTest(field=field), self.assertRaises(RuntimeError):
                CREATE.validate_source_contract(report, AUDIT)

    def test_orphan_sidecar_and_in_memory_target_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            ue = SimpleNamespace(EditorAssetLibrary=SimpleNamespace(does_asset_exist=lambda _: False),
                                 find_object=lambda *_: None)
            with patch.object(AUDIT, "PROJECT", root):
                CREATE.require_new_targets(AUDIT, ue)
                sidecar = AUDIT.package_file(AUDIT.MONTAGES[0]).with_suffix(".uexp")
                sidecar.parent.mkdir(parents=True)
                sidecar.write_bytes(b"existing orphan sidecar")
                with self.assertRaises(RuntimeError):
                    CREATE.require_new_targets(AUDIT, ue)
                self.assertEqual(sidecar.read_bytes(), b"existing orphan sidecar")
            with patch.object(AUDIT, "PROJECT", root / "AnotherScope"):
                ue.find_object = lambda *_: object()
                with self.assertRaises(RuntimeError):
                    CREATE.require_new_targets(AUDIT, ue)

    def test_non_finite_and_float32_overflow_parameters_rejected(self):
        for value in (float("nan"), float("inf"), 1e300):
            with self.subTest(value=value), self.assertRaises((RuntimeError, OverflowError)):
                CREATE.f32(value)


if __name__ == "__main__":
    unittest.main()
