"""Offline regression tests. Fake Unreal APIs; writes only TemporaryDirectory packages."""
import importlib.util
import json
import re
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


class EditorStruct:
    def __init__(self, **values):
        self.values = values

    def get_editor_property(self, key):
        return self.values[key]


def install_signal_api(unreal, montage, events=None):
    """Model native point ownership/name/link and an independently read trigger."""
    events = [] if events is None else events
    tracks = ['Sound', 'HitWindow', 'ComboWindow']

    class StockPoint(EditorStruct):
        @staticmethod
        def static_class():
            return StockPoint

        def __init__(self, name='None', outer=montage):
            super().__init__(notify_name=name)
            self.get_outer = lambda: outer
            self.get_path_name = lambda: montage.get_path_name() + ':Point'
            self.set_editor_property = Mock(side_effect=self.values.__setitem__)

        def get_notify_name(self):
            return self.values['notify_name']

        def get_class(self):
            return type(self)

    class StockWindow(StockPoint):
        pass

    class Event(EditorStruct):
        def export_text(self):
            link = self.values['linked_montage']
            reference = ('"/Script/Engine.AnimMontage\'%s\'"' % link
                         if link is not None else 'None')
            return '(NotifyName="None",EndLink=(LinkedMontage=None),LinkedMontage=%s)' % reference

    def event(point, trigger, state=None):
        return Event(notify=point, notify_state_class=state, trigger_seconds=trigger,
                     duration_seconds=0, linked_montage=montage.get_path_name())

    def add_point(asset, track, display_time, notify_class):
        if asset is not montage or track not in tracks or notify_class is not StockPoint:
            raise AssertionError('invalid native creation request')
        point = StockPoint()
        # Deliberately separate display/trigger: callers must read the native API.
        events.append(event(point, display_time + 0.0001))
        return point

    unreal.AnimNotify_PlayMontageNotify = StockPoint
    unreal.AnimNotify_PlayMontageNotifyWindow = StockWindow
    unreal.AnimationLibrary = SimpleNamespace(
        get_animation_notify_events=lambda asset: list(events),
        get_anim_notify_event_trigger_time=lambda value: value.values['trigger_seconds'],
        get_anim_notify_event_duration=lambda value: value.values['duration_seconds'],
        get_animation_notify_track_names=lambda asset: list(tracks),
        add_animation_notify_track=Mock(side_effect=lambda asset, name: tracks.append(name)),
        add_animation_notify_event=Mock(side_effect=add_point))
    return events, event


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


class PyriosFullEndGenerationTests(unittest.TestCase):
    @staticmethod
    def source(length, target_numerator=60, target_denominator=1, rate_scale=1):
        rate = SimpleNamespace(get_editor_property=lambda key: {
            'numerator': target_numerator, 'denominator': target_denominator}[key])
        platform = SimpleNamespace(get_editor_property=lambda key: {'default': rate}[key])
        return SimpleNamespace(
            get_path_name=lambda: '/Game/Animation/End.End',
            get_play_length=lambda: length,
            get_editor_property=lambda key: {'platform_target_frame_rate': platform,
                                            'rate_scale': rate_scale,
                                            'skeleton': 'shared-skeleton'}[key])

    def test_new_montage_uses_full_end_and_actual_target_sampling_and_rates(self):
        with tempfile.TemporaryDirectory() as temp:
            unreal = SimpleNamespace()
            module = load('create_pyrios_combo_montages', unreal)
            step = module.STEPS[0]
            module.STEPS = [step]
            main = self.source(step['main_frames'] / module.FPS)
            end = self.source(7.125, 30000, 1001, rate_scale=2)
            unreal.load_asset = lambda path: end if path.endswith('_End') else main
            unreal.EditorAssetLibrary = SimpleNamespace(
                does_asset_exist=lambda path: False, save_loaded_asset=Mock(return_value=True))
            unreal.Paths = SimpleNamespace(project_saved_dir=lambda: temp,
                                           convert_relative_path_to_full=lambda path: path)
            unreal.log_warning = Mock()

            class Segment:
                def __init__(self):
                    self.values = {}

                def import_text(self, text):
                    self.values.update({key: float(value) for key, value in re.findall(
                        r'(StartPos|AnimEndTime)=([^,\)]+)', text)})

                def set_editor_property(self, key, value):
                    self.values[key] = value

                def get_editor_property(self, key):
                    return self.values[{'start_pos': 'StartPos'}.get(key, key)]

            unreal.AnimSegment = Segment
            unreal.AnimTrack = lambda anim_segments: EditorStruct(anim_segments=anim_segments)
            unreal.SlotAnimationTrack = EditorStruct
            unreal.AnimMontageFactory = lambda: SimpleNamespace(set_editor_property=Mock())
            unreal.AnimMontage = object
            unreal.AlphaBlendOption = SimpleNamespace(HERMITE_CUBIC='HermiteCubic')
            blend = SimpleNamespace(set_editor_property=Mock())
            properties = {'rate_scale': 1.25, 'blend_in': blend, 'blend_out': blend}
            montage = SimpleNamespace(
                get_editor_property=lambda key: properties[key],
                set_editor_property=lambda key, value: properties.__setitem__(key, value),
                get_path_name=lambda: '/Game/Animation/Attack.Attack',
                get_outer=lambda: object(),
                get_play_length=lambda: main.get_play_length() + end.get_play_length() / 2)
            events, _ = install_signal_api(unreal, montage)
            create = Mock(return_value=montage)
            unreal.AssetToolsHelpers = SimpleNamespace(
                get_asset_tools=lambda: SimpleNamespace(create_asset=create))
            unreal.EditorLoadingAndSavingUtils = SimpleNamespace(reload_packages=Mock())
            unreal.ReloadPackagesInteractionMode = SimpleNamespace(ASSUME_POSITIVE=1)
            original_load = unreal.load_asset
            unreal.load_asset = lambda path: (montage if '/Attack/' in path else original_load(path))
            module.add_window = Mock()

            module.run(play_rates={'01': 0.5})

            segments = properties['slot_anim_tracks'][0].get_editor_property(
                'anim_track').get_editor_property('anim_segments')
            self.assertEqual(segments[1].values['AnimEndTime'], 7.125)
            self.assertEqual(segments[0].values['AnimEndTime'], main.get_play_length())
            self.assertAlmostEqual(properties['blend_out_trigger_time'],
                                   (1001 / 30000) / (2 * 1.25 * 0.5))
            self.assertEqual(module.add_window.call_args_list[0].args[2], step['hit'])
            self.assertEqual(module.add_window.call_args_list[1].args[2], step['combo'])
            unreal.AnimationLibrary.add_animation_notify_event.assert_called_once_with(
                montage, module.SIGNAL_TRACK, main.get_play_length(),
                unreal.AnimNotify_PlayMontageNotify)
            self.assertEqual(events[0].get_editor_property('notify').get_notify_name(),
                             module.SIGNAL_NOTIFY_NAME)
            result = json.loads((Path(temp) / 'Codex/PyriosComboCreation.json').read_text())[0]
            self.assertAlmostEqual(result['interruption_signal']['trigger_seconds'],
                                   main.get_play_length() + 0.0001)
            self.assertEqual(properties['blend_out'], blend)
            self.assertTrue(properties['enable_auto_blend_out'])
            create.assert_called_once()

    def signal_fixture(self):
        unreal = SimpleNamespace()
        properties = {'slot_anim_tracks': [EditorStruct(
            slot_name='FullBody', anim_track=EditorStruct(anim_segments=[
                EditorStruct(start_pos=0), EditorStruct(start_pos=1.6)]))]}
        montage = SimpleNamespace(get_path_name=lambda: '/Game/Animation/Attack.Attack',
                                  get_play_length=lambda: 5.0,
                                  get_editor_property=Mock(side_effect=properties.__getitem__))
        events, event = install_signal_api(unreal, montage)
        return unreal, load('create_pyrios_combo_montages', unreal), montage, events, event

    def test_existing_authored_signal_preserves_main_or_late_point_and_legacy_notifies(self):
        for position in (0.7, 4.99):
            with self.subTest(position=position):
                unreal, module, montage, events, event = self.signal_fixture()
                sound = unreal.AnimNotify_PlayMontageNotify('PlaySound')
                hit = unreal.AnimNotify_PlayMontageNotifyWindow('HitWindow')
                combo = unreal.AnimNotify_PlayMontageNotifyWindow('ComboWindow')
                point = unreal.AnimNotify_PlayMontageNotify(module.SIGNAL_NOTIFY_NAME)
                events.extend([event(sound, 0.03), event(None, 0.06, hit),
                               event(None, 0.26, combo), event(point, position)])
                before = [(value, dict(value.values), value.export_text()) for value in events]

                result = module.ensure_interruption_signal(montage)

                self.assertEqual(result['status'], 'existing signal preserved')
                self.assertEqual(result['trigger_seconds'], position)
                self.assertEqual(before, [(value, dict(value.values), value.export_text())
                                          for value in events])
                for notify in (sound, hit, combo, point):
                    notify.set_editor_property.assert_not_called()
                montage.get_editor_property.assert_not_called()
                unreal.AnimationLibrary.add_animation_notify_track.assert_not_called()
                unreal.AnimationLibrary.add_animation_notify_event.assert_not_called()

    def test_duplicate_or_invalid_native_signal_fails_without_authoring(self):
        for invalid in ('duplicate', 'case_duplicate', 'subclass', 'window',
                        'foreign_outer', 'foreign_link', 'nonfinite', 'outside'):
            with self.subTest(invalid=invalid):
                unreal, module, montage, events, event = self.signal_fixture()
                point = unreal.AnimNotify_PlayMontageNotify(module.SIGNAL_NOTIFY_NAME)
                if invalid == 'subclass':
                    class OverridePoint(unreal.AnimNotify_PlayMontageNotify):
                        def get_notify_name(self):
                            return 'Different Blueprint display name'
                    point = OverridePoint(module.SIGNAL_NOTIFY_NAME)
                if invalid == 'foreign_outer':
                    point = unreal.AnimNotify_PlayMontageNotify(module.SIGNAL_NOTIFY_NAME, object())
                events.append(event(point, 0.7))
                if invalid in ('duplicate', 'case_duplicate'):
                    name = (module.SIGNAL_NOTIFY_NAME.lower() if invalid == 'case_duplicate'
                            else module.SIGNAL_NOTIFY_NAME)
                    events.append(event(unreal.AnimNotify_PlayMontageNotify(name), 4.99))
                elif invalid == 'window':
                    events[0] = event(None, 0.7,
                        unreal.AnimNotify_PlayMontageNotifyWindow(module.SIGNAL_NOTIFY_NAME))
                elif invalid == 'foreign_link':
                    events[0].values['linked_montage'] = '/Game/Animation/Other.Other'
                elif invalid in ('nonfinite', 'outside'):
                    events[0].values['trigger_seconds'] = float('nan') if invalid == 'nonfinite' else 5.1

                with self.assertRaisesRegex(RuntimeError, 'Animation signal authoring:'):
                    module.ensure_interruption_signal(montage)

                point.set_editor_property.assert_not_called()
                unreal.AnimationLibrary.add_animation_notify_track.assert_not_called()
                unreal.AnimationLibrary.add_animation_notify_event.assert_not_called()

    def test_ga_signal_and_explicit_next_steps_are_required_without_repair(self):
        unreal = SimpleNamespace()
        module = load('create_pyrios_combo_montages', unreal)
        configured = [EditorStruct(interruption_notify_name=module.SIGNAL_NOTIFY_NAME,
                                   next_step_index=index, play_rate=1.0)
                      for index in (1, 2, 0)]
        unreal.load_asset = Mock(return_value=SimpleNamespace(generated_class=lambda: object()))
        unreal.get_default_object = lambda value: EditorStruct(combo_steps=configured)
        for step in module.STEPS:
            self.assertEqual(module.requested_step_rate(step, None), 1.0)
        for key, invalid in (('next_step_index', -1), ('interruption_notify_name', 'None')):
            with self.subTest(key=key):
                original = configured[2].values[key]
                configured[2].values[key] = invalid
                with self.assertRaisesRegex(RuntimeError, 'GA signal/next-step configuration'):
                    module.requested_step_rate(module.STEPS[2], None)
                self.assertEqual(configured[2].values[key], invalid)
                configured[2].values[key] = original

    def test_missing_or_invalid_target_sampling_cannot_use_source_fps(self):
        module = load('create_pyrios_combo_montages', SimpleNamespace())
        missing = SimpleNamespace(get_path_name=lambda: '/Game/Animation/End.End',
                                  get_editor_property=Mock(side_effect=AttributeError('unavailable')))
        with self.assertRaisesRegex(RuntimeError, 'target sampling rate unavailable'):
            module.full_end_settings(missing, 1, 1, 1)
        with self.assertRaisesRegex(RuntimeError, 'invalid full End'):
            module.full_end_settings(self.source(7.125, 0), 1, 1, 1)
        with self.assertRaisesRegex(RuntimeError, 'invalid full End'):
            module.full_end_settings(self.source(7.125), 1, 1, 0)

    def test_existing_montages_are_preserved_without_loading_sources_or_ga(self):
        with tempfile.TemporaryDirectory() as temp:
            unreal = SimpleNamespace(
                EditorAssetLibrary=SimpleNamespace(does_asset_exist=lambda path: True),
                load_asset=Mock(),
                Paths=SimpleNamespace(project_saved_dir=lambda: temp,
                                      convert_relative_path_to_full=lambda path: path),
                log_warning=Mock())
            module = load('create_pyrios_combo_montages', unreal)
            module.run()
            unreal.load_asset.assert_not_called()
            results = json.loads((Path(temp) / 'Codex/PyriosComboCreation.json').read_text())
            self.assertEqual(len(results), 3)
            self.assertTrue(all(row['status'] == 'existing asset preserved' for row in results))


if __name__ == '__main__':
    unittest.main()
