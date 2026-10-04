"""Offline regression tests. Fake Unreal APIs; writes only TemporaryDirectory packages."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))


def load(name, unreal):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, unreal=unreal):
        spec.loader.exec_module(module)
    return module


class AssetSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.unreal = SimpleNamespace(
            RawCurveTrackTypes=SimpleNamespace(RCT_FLOAT=0),
            Paths=SimpleNamespace(project_content_dir=lambda: str(self.root),
                                  convert_relative_path_to_full=lambda p: p),
            EditorAssetLibrary=SimpleNamespace(save_loaded_asset=Mock(return_value=True)),
            EditorLoadingAndSavingUtils=SimpleNamespace(get_dirty_content_packages=lambda: []),
            load_asset=Mock(return_value=object()), log=Mock(), log_error=Mock())
        self.bake = load('bake_anim_rootmotion_curves', self.unreal)
        self.bake.PROGRESS_JSON = str(self.root / 'progress.json')
        self.bake.REPORT_JSON = str(self.root / 'report.json')
        self.bake.ANIM_FOLDER = '/Game/Animation'
        self.record = {'name': 'Attack', 'times': [0, 1], 'curves': {'x': [0, 2]}}
        self.bake.load_records = lambda: [self.record]
        self.bake.bake_clip = Mock(return_value=('ok', {'name': 'Attack', 'keyTotal': 2}))
        self.package = self.root / 'Animation/Attack.uasset'
        self.package.parent.mkdir()
        self.package.write_bytes(b'package-v1')

    def test_save_false_is_retryable_and_never_done(self):
        self.unreal.EditorAssetLibrary.save_loaded_asset.return_value = False
        self.assertFalse(self.bake.run()['complete'])
        self.assertEqual(self.bake.load_progress()['entries']['Attack']['status'], 'failed')
        self.unreal.EditorAssetLibrary.save_loaded_asset.return_value = True
        self.assertTrue(self.bake.run()['complete'])
        self.assertEqual(self.bake.bake_clip.call_count, 2)
        self.bake.run()
        self.assertEqual(self.bake.bake_clip.call_count, 2, 'valid completion should skip')

    def test_missing_is_retried_when_dependency_appears(self):
        self.bake.bake_clip.return_value = ('missing', {'name': 'Attack', 'reason': 'not imported'})
        self.assertEqual(len(self.bake.run()['missing']), 1)
        self.bake.bake_clip.return_value = ('ok', {'name': 'Attack'})
        self.assertTrue(self.bake.run()['complete'])

    def test_source_script_config_and_reimport_invalidate_success(self):
        self.assertTrue(self.bake.run()['complete'])
        self.record['curves']['x'][1] = 5
        self.bake.run()
        self.assertEqual(self.bake.bake_clip.call_count, 2)
        self.package.write_bytes(b'reimported-package')
        self.bake.run()
        self.assertEqual(self.bake.bake_clip.call_count, 3)
        self.package.with_suffix('.ubulk').write_bytes(b'new bulk')
        self.bake.run()
        self.assertEqual(self.bake.bake_clip.call_count, 4)
        self.bake.MOTION_CURVES = self.bake.MOTION_CURVES + ['new-config']
        self.bake.run()
        self.assertEqual(self.bake.bake_clip.call_count, 5)
        script = self.root / 'changed-script.py'
        script.write_text('# revised tool')
        self.bake.__file__ = str(script)
        self.bake.run()
        self.assertEqual(self.bake.bake_clip.call_count, 6)

    def test_legacy_progress_cannot_skip_asset(self):
        Path(self.bake.PROGRESS_JSON).write_text(json.dumps({'done': ['Attack'], 'failed': [], 'missing': []}))
        self.assertTrue(self.bake.run()['complete'])
        self.bake.bake_clip.assert_called_once()

    def test_unsaved_package_is_preserved(self):
        package = SimpleNamespace(get_name=lambda: '/Game/Animation/Attack')
        self.unreal.EditorLoadingAndSavingUtils.get_dirty_content_packages = lambda: [package]
        self.assertFalse(self.bake.run()['complete'])
        self.bake.bake_clip.assert_not_called()
        self.unreal.EditorAssetLibrary.save_loaded_asset.assert_not_called()

    def test_failed_first_clip_does_not_starve_next(self):
        self.bake.BATCH_SIZE = 1
        self.bake.load_records = lambda: [self.record, {'name': 'Next'}]
        self.bake.bake_clip.return_value = ('missing', {'reason': 'missing'})
        self.bake.run()
        self.bake.run()
        self.assertEqual([c.args[0]['name'] for c in self.bake.bake_clip.call_args_list], ['Attack', 'Next'])

    def test_true_save_without_disk_package_is_not_success(self):
        self.package.unlink()
        self.assertFalse(self.bake.run()['complete'])
        self.assertEqual(self.bake.run()['done'], [])

    def test_import_save_requires_true_and_persisted_package(self):
        importer = load('import_bh3_kevin_demonbattle', self.unreal)
        asset = SimpleNamespace(get_path_name=lambda: '/Game/Animation/Attack.Attack')
        self.unreal.EditorAssetLibrary.save_loaded_asset.return_value = False
        with self.assertRaisesRegex(RuntimeError, 'save failed'):
            importer.save_checked(self.unreal, asset)
        self.unreal.EditorAssetLibrary.save_loaded_asset.return_value = True
        importer.save_checked(self.unreal, asset)
        self.package.unlink()
        with self.assertRaisesRegex(RuntimeError, 'package is absent'):
            importer.save_checked(self.unreal, asset)


if __name__ == '__main__':
    unittest.main()
