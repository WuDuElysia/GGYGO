"""@file test_pyrios_skill_inputs.py
@brief 离线验证三入口追加、覆盖拒绝与 Cold 来源契约；不导入 UE。
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "wire_pyrios_skill_inputs.py"
subject = types.ModuleType("pyrios_skill_inputs_test_subject")
subject.__file__ = str(SCRIPT)
exec(compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec"), subject.__dict__)


def original():
    return {"native": ["Native" + str(i) for i in range(4)],
            "ability": ["Ability" + str(i) for i in range(4)],
            "ability_bindings": [{"action": "/Game/Old" + str(i), "tag": "InputTag.Old" + str(i)}
                                 for i in range(4)],
            "mappings": [{"key": "OldKey" + str(i), "action": "/Game/Old", "export": "Mapping" + str(i)}
                         for i in range(15)],
            "settings": {"mapping_profile_overrides": {}, "registration_tracking_mode": "Untracked"}}


def appended(before):
    after = copy.deepcopy(before)
    exports = ["NewAbility" + name for name in subject.FAMILIES]
    after["ability"] += exports
    after["ability_bindings"] += [{"action": subject.object_path(package), "tag": tag}
                                  for package, tag in zip(subject.ACTIONS, subject.TAGS)]
    after["mappings"] += [{"key": key, "action": subject.object_path(package), "export": "NewMapping" + key}
                          for key, package in zip(subject.KEYS, subject.ACTIONS)]
    return after, exports


class InputContractTests(unittest.TestCase):
    def test_import_does_not_import_unreal(self):
        module = types.ModuleType("inert_input_import")
        module.__file__ = str(SCRIPT)
        with mock.patch.dict(sys.modules, {"unreal": None}):
            exec(compile(SCRIPT.read_text(encoding="utf-8"), str(SCRIPT), "exec"), module.__dict__)
        self.assertEqual(module.TARGETS, subject.TARGETS)

    def test_exact_append_preserves_original_rows(self):
        before = original()
        after, exports = appended(before)
        subject.validate_original(before)
        subject.validate_append(before, after, exports)
        self.assertEqual(before, original())

    def test_conflicting_original_is_rejected(self):
        changes = (
            lambda data: data["mappings"][0].update(key="E"),
            lambda data: data["mappings"][0].update(action=subject.object_path(subject.ACTIONS[0])),
            lambda data: data["ability_bindings"][0].update(tag=subject.TAGS[0]),
            lambda data: data["settings"]["mapping_profile_overrides"].update(Gamepad="override"),
            lambda data: data["ability"].pop(),
        )
        for change in changes:
            with self.subTest(change=change):
                data = original()
                change(data)
                with self.assertRaises(RuntimeError):
                    subject.validate_original(data)

    def test_append_rejects_changed_old_rows_or_wrong_pairing(self):
        changes = (
            lambda data: data["native"].__setitem__(0, "Changed"),
            lambda data: data["ability"].__setitem__(0, "Changed"),
            lambda data: data["mappings"][0].update(export="ChangedModifier"),
            lambda data: data["settings"].update(registration_tracking_mode="CountRegistrations"),
            lambda data: data["mappings"][-1].update(key="R"),
            lambda data: data["ability_bindings"][-1].update(tag=subject.TAGS[0]),
            lambda data: data["mappings"].pop(),
        )
        for change in changes:
            with self.subTest(change=change):
                before = original()
                after, exports = appended(before)
                change(after)
                with self.assertRaises(RuntimeError):
                    subject.validate_append(before, after, exports)

    def test_protection_includes_new_unowned_and_source_changes(self):
        self.assertEqual(subject.unowned_changes({"Target": "old", "Source": "old"},
                         {"Target": "new", "Source": "new", "Other": "new"}, {"Target"}), ["Other", "Source"])

    def test_action_collision_is_rejected_from_disk_registry_or_memory(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(subject, "PROJECT", Path(folder)):
            asset_library = types.SimpleNamespace(does_asset_exist=mock.Mock(return_value=False))
            ue = types.SimpleNamespace(EditorAssetLibrary=asset_library, find_object=mock.Mock(return_value=None))
            package = subject.ACTIONS[0]
            subject.require_unused_action(ue, package)
            asset_library.does_asset_exist.return_value = True
            with self.assertRaises(RuntimeError):
                subject.require_unused_action(ue, package)
            asset_library.does_asset_exist.return_value = False
            ue.find_object.return_value = object()
            with self.assertRaises(RuntimeError):
                subject.require_unused_action(ue, package)
            ue.find_object.return_value = None
            sidecar = subject.package_file(package).with_suffix(".uexp")
            sidecar.parent.mkdir(parents=True)
            sidecar.write_bytes(b"existing")
            with self.assertRaises(RuntimeError):
                subject.require_unused_action(ue, package)

    def test_cold_requires_independent_host_actual_exit_and_exact_saved_set(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(subject, "PROJECT", Path(folder)):
            output = Path(folder) / "Saved/Create/readback.json"
            output.parent.mkdir(parents=True)
            report = {"schema": subject.SCHEMA, "mode": "create", "success": True,
                      "saved": list(subject.TARGETS), "pid": 100}
            output.write_text(json.dumps(report), encoding="utf-8")
            host = {"pid": 100, "exit_code": 0, "report_sha256": subject.digest(output)}
            receipt = output.parent / "host_exit.json"
            receipt.write_text(json.dumps(host), encoding="utf-8")
            self.assertEqual(subject.previous_create(str(output), 200), report)
            with self.assertRaises(RuntimeError):
                subject.previous_create(str(output), 100)
            for changes in ({"exit_code": -1}, {"exit_code": False}, {"pid": 101}, {"report_sha256": "wrong"}):
                receipt.write_text(json.dumps(dict(host, **changes)), encoding="utf-8")
                with self.assertRaises(RuntimeError):
                    subject.previous_create(str(output), 200)
            receipt.write_text(json.dumps(host), encoding="utf-8")
            report["saved"].pop()
            output.write_text(json.dumps(report), encoding="utf-8")
            with self.assertRaises(RuntimeError):
                subject.previous_create(str(output), 200)

    def test_dirty_preflight_and_failed_cleanup_preserve_failure_report(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(subject, "PROJECT", Path(folder)):
            ue = types.SimpleNamespace(UnrealEditorSubsystem=object(),
                get_editor_subsystem=lambda unused: types.SimpleNamespace(get_game_world=lambda: None))
            ue.EditorAssetLibrary = types.SimpleNamespace(save_loaded_asset=mock.Mock())
            ue.AssetToolsHelpers = types.SimpleNamespace(get_asset_tools=mock.Mock())
            with mock.patch.dict(sys.modules, {"unreal": ue}), mock.patch.object(subject, "dirty",
                    side_effect=[{"content": ["/Game/UserWork"], "maps": []}, RuntimeError("cleanup diagnostic")]):
                with self.assertRaises(RuntimeError):
                    subject.run("create", "Saved/Failure/readback.json")
            report = json.loads((Path(folder) / "Saved/Failure/readback.json").read_text(encoding="utf-8"))
            self.assertFalse(report["success"])
            self.assertEqual(report["created"], [])
            self.assertEqual(report["saved"], [])
            self.assertEqual(len(report["errors"]), 2)
            self.assertIsNone(report["dirty_after"])
            ue.EditorAssetLibrary.save_loaded_asset.assert_not_called()
            ue.AssetToolsHelpers.get_asset_tools.assert_not_called()

    def test_existing_report_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.object(subject, "PROJECT", Path(folder)):
            output = Path(folder) / "Saved/Existing/readback.json"
            output.parent.mkdir(parents=True)
            output.write_bytes(b"original evidence")
            with self.assertRaises(RuntimeError):
                subject.run("create", str(output))
            self.assertEqual(output.read_bytes(), b"original evidence")


if __name__ == "__main__":
    unittest.main()
