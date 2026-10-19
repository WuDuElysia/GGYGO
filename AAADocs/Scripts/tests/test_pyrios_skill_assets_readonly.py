"""@file test_pyrios_skill_assets_readonly.py
@brief 技能资产只读工具的离线解析、时间域和失败保护验证，不证明 UE 绑定。
"""
import importlib.util
import os
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPT = Path(__file__).absolute().parents[1] / "audit_pyrios_skill_assets_readonly.py"
SPEC = importlib.util.spec_from_file_location("skill_assets_readonly", SCRIPT)
AUDIT = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(AUDIT)


class SkillAssetReadOnlyTests(unittest.TestCase):
    def test_root_array_ignores_nested_objects(self):
        text = ('Begin Object Class=/Script/Engine.Skeleton Name="SK"\n'
                ' Begin Object Class=/Script/Engine.SkeletalMeshSocket Name="Tip"\n'
                '  SlotGroups(0)=(GroupName="Wrong",SlotNames=("Wrong"))\n End Object\n'
                ' SlotGroups(0)=(SlotNames=("DefaultSlot","FullBody"))\nEnd Object\n')
        groups = AUDIT.skeleton_slot_groups(text)
        self.assertEqual(groups[0]["group"], "DefaultGroup")
        self.assertEqual(groups[0]["slots"], ["DefaultSlot", "FullBody"])

    def test_rejects_ambiguous_or_broken_t3d(self):
        for middle in ('SlotGroups(0)=A\nSlotGroups(0)=B', 'SlotGroups(1)=A'):
            with self.subTest(middle=middle), self.assertRaises(RuntimeError):
                AUDIT.root_arrays('Begin Object\n' + middle + '\nEnd Object', "SlotGroups")
        for text in ('End Object', 'Begin Object', 'Begin Object\nEnd Object\nBegin Object\nEnd Object'):
            with self.subTest(text=text), self.assertRaises(RuntimeError):
                AUDIT.root_arrays(text, "SlotGroups")

    def test_explicit_group_and_unreadable_slot_list(self):
        text = 'Begin Object\n SlotGroups(0)=(GroupName="Action",SlotNames=("FullBody"))\nEnd Object'
        self.assertEqual(AUDIT.skeleton_slot_groups(text)[0]["group"], "Action")
        with self.assertRaises(RuntimeError):
            AUDIT.skeleton_slot_groups(text.replace('"FullBody"', 'UnquotedSlot'))

    def test_timeline_uses_each_source_rate(self):
        timeline = AUDIT.pair_timeline(4.0, 2.0, 3.0, 0.5)
        self.assertEqual(timeline["Main"], [0.0, 2.0])
        self.assertEqual(timeline["End"], [2.0, 8.0])

    def test_timeline_rejects_invalid_rates_and_overflow(self):
        for value in (0.0, -1.0, float("nan"), float("inf")):
            with self.subTest(value=value), self.assertRaises(RuntimeError):
                AUDIT.pair_timeline(1.0, value, 1.0, 1.0)
        with self.assertRaises(RuntimeError):
            AUDIT.pair_timeline(1e308, 1e-308, 1.0, 1.0)

    def test_package_scope_is_exact(self):
        self.assertEqual(len(AUDIT.SEQUENCES), 6)
        for package in ("/Game/../Other", AUDIT.ANIMATION + "Attack/AM_Pyrios_Attack_Normal_01"):
            with self.subTest(package=package), self.assertRaises(RuntimeError):
                AUDIT.package_file(package)

    def test_wrong_pid_does_not_enter_editor_or_write_output(self):
        with patch.dict(sys.modules, unreal=SimpleNamespace()), self.assertRaises(RuntimeError):
            AUDIT.run("Saved/NotCreated", os.getpid() + 1)

    def run_failure_host(self, root, dirty_packages, wait):
        mutations = Mock(side_effect=AssertionError("只读工具调用资产写入"))
        registry = SimpleNamespace(wait_for_completion=wait)
        unreal = SimpleNamespace(
            Paths=SimpleNamespace(project_dir=lambda: str(root), convert_relative_path_to_full=lambda p: p),
            EditorLoadingAndSavingUtils=SimpleNamespace(
                get_dirty_content_packages=lambda: dirty_packages, get_dirty_map_packages=lambda: []),
            UnrealEditorSubsystem=object,
            get_editor_subsystem=lambda _: SimpleNamespace(get_game_world=lambda: None),
            AssetRegistryHelpers=SimpleNamespace(get_asset_registry=lambda: registry),
            EditorAssetLibrary=SimpleNamespace(save_loaded_asset=mutations),
            log=Mock(), log_error=Mock())
        with patch.object(AUDIT, "PROJECT", root), patch.dict(sys.modules, unreal=unreal):
            report = AUDIT.run("Saved/Readback", os.getpid())
        mutations.assert_not_called()
        return report

    def test_dirty_host_preserves_user_work_and_fails(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package = SimpleNamespace(get_path_name=lambda: "/Game/UserUnsaved")
            wait = Mock(side_effect=AssertionError("dirty 宿主不应继续 native 读取"))
            report = self.run_failure_host(root, [package], wait)
            self.assertFalse(report["success"])
            self.assertEqual(report["dirty_before"], report["dirty_after"])
            self.assertEqual(report["dirty_after"]["content"], ["/Game/UserUnsaved"])
            wait.assert_not_called()

    def test_native_read_failure_and_new_package_are_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for module in ("GGYGO", "GGYGOEditor"):
                path = root / "Binaries/Win64" / ("UnrealEditor-" + module + ".dll")
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"offline protection fixture")
            new_package = root / "Content" / (AUDIT.MONTAGES[0][6:] + ".uasset")
            def unavailable_registry():
                new_package.parent.mkdir(parents=True)
                new_package.write_bytes(b"concurrent package fixture")
                raise RuntimeError("required native registry unavailable")

            report = self.run_failure_host(root, [], unavailable_registry)
            self.assertFalse(report["success"])
            self.assertIn(str(new_package), report["changed_files"])
            self.assertFalse(report["protected_before"][str(new_package)]["exists"])
            self.assertTrue(report["protected_after"][str(new_package)]["exists"])
            self.assertEqual(report["errors"][0]["operation"], "audit")


if __name__ == "__main__":
    unittest.main()
