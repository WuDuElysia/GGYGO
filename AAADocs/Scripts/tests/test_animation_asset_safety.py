"""Offline regression tests. Fake Unreal APIs; writes only TemporaryDirectory packages."""
import importlib.util
import json
import os
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


class CancelSplitHarness:
    """Fake getter/authoring calls only. Offsets are explicit test inputs, not engine logic."""

    def __init__(self, temp, module_loader):
        self.root = Path(temp)
        self.unreal = SimpleNamespace()
        self.module = module_loader('create_pyrios_combo_montages', self.unreal)
        f32 = self.module._f32
        self.f32 = f32
        self.main_end = f32(1.35)
        self.length = f32(6.3666667)
        self.engine_offset = self.module.OFFSET_BEFORE
        self.dirty = set()
        self.montages = {}
        self.state = {}
        self.added_hooks = []
        content = self.root / 'Content'
        for relative in self.module.CANCEL_SPLIT_PROTECTED:
            file = content / (relative + '.uasset')
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'protected:' + relative.encode())
        for path in self.module.CANCEL_SPLIT_TARGETS:
            name = path.rsplit('/', 1)[1]
            obj = path + '.' + name
            file = content / (path[len('/Game/'):] + '.uasset')
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_bytes(b'target-v1:' + name.encode())
            self.state[obj] = dict(play_length=self.length, notifies=[
                self.notify(obj, 'Sound', 'None', f32(0.033333), cls='/Script/Engine.AnimNotify_PlaySound',
                            branching=False),
                self.notify(obj, 'Window', 'None', f32(0.283333), cls='', branching=False,
                            state='/Script/GGYGO.GGYGOAnimNotifyState_GameplayEventWindow',
                            duration=f32(1.366667)),
                self.notify(obj, 'Cancel', self.module.SIGNAL_NOTIFY_NAME, f32(0.294344634))],
                sections=[EditorStruct(section_name='Main', next_section_name='End', time=0.0,
                                       slot_index=0, segment_index=0),
                          EditorStruct(section_name='End', next_section_name='None', time=self.main_end,
                                       slot_index=0, segment_index=1)],
                segments=[EditorStruct(slot_name='FullBody', slot_index=0, segment_index=0, start_pos=0.0,
                                       end_pos=self.main_end, anim_reference='/Game/Main'),
                          EditorStruct(slot_name='FullBody', slot_index=0, segment_index=1,
                                       start_pos=self.main_end, end_pos=self.length,
                                       anim_reference='/Game/End')])
            blend = EditorStruct(blend_time=f32(0.1), blend_option='HermiteCubic')
            settings = dict(rate_scale=1.0, loop=False, enable_auto_blend_out=True,
                            blend_out_trigger_time=f32(0.016666668), blend_in=blend, blend_out=blend)
            self.montages[path] = SimpleNamespace(
                get_path_name=(lambda value=obj: value), package=path,
                get_editor_property=Mock(side_effect=settings.__getitem__))
        self.install()

    def notify(self, obj, guid, name, time, offset=0.0, cls=None, state='', duration=0.0,
               branching=True, linked=True, trigger=None):
        cls = self.module.STOCK_POINT_CLASS if cls is None else cls
        trigger = self.f32(time + offset) if trigger is None else trigger
        return EditorStruct(guid=guid, track_index=0, notify_class=cls, notify_object=obj + ':' + guid,
                            stock_notify_name=name, state_class=state, time=time,
                            trigger_time_offset=offset, trigger_time=trigger, duration=duration,
                            end_trigger_time=trigger, slot_index=0, segment_index=0,
                            link_method='Absolute', is_branching_point=branching, linked_to_self=linked)

    def facts(self, montage):
        value = self.state[montage.get_path_name()]
        return EditorStruct(succeeded=True, error='', play_length=value['play_length'],
                            sections=list(value['sections']), segments=list(value['segments']),
                            notifies=list(value['notifies']))

    def add_event(self, montage, track, display_time, notify_class):
        if notify_class is not self.unreal.AnimNotify_PlayMontageNotify or track != self.module.SIGNAL_TRACK:
            raise AssertionError('unexpected native creation request')
        obj = montage.get_path_name()
        fact = self.notify(obj, 'Move', 'None', display_time, offset=self.engine_offset)
        self.state[obj]['notifies'].append(fact)
        self.dirty.add(montage.package)
        for hook in self.added_hooks:
            hook(obj)
        point = SimpleNamespace(get_outer=lambda: montage, get_path_name=lambda: obj + ':Move')
        point.set_editor_property = Mock(side_effect=lambda key, value: fact.values.__setitem__(
            {'notify_name': 'stock_notify_name'}[key], value))
        return point

    def save(self, montage, only_if_is_dirty):
        self.dirty.discard(montage.package)
        file = self.root / 'Content' / (montage.package[len('/Game/'):] + '.uasset')
        file.write_bytes(file.read_bytes() + b'+move')
        return True

    def install(self):
        unreal = self.unreal
        unreal.AnimNotify_PlayMontageNotify = type('StockPoint', (), {})
        unreal.GGYGOLinearMontageAuthorLibrary = SimpleNamespace(
            read_montage_timeline_facts=Mock(side_effect=self.facts))
        unreal.AnimationLibrary = SimpleNamespace(
            get_animation_notify_track_names=lambda montage: ['ActionSignal'],
            add_animation_notify_track=Mock(),
            add_animation_notify_event=Mock(side_effect=self.add_event))
        unreal.EditorAssetLibrary = SimpleNamespace(save_loaded_asset=Mock(side_effect=self.save))
        unreal.EditorLoadingAndSavingUtils = SimpleNamespace(
            get_dirty_content_packages=lambda: [SimpleNamespace(get_path_name=(lambda v=p: v))
                                                for p in sorted(self.dirty)],
            get_dirty_map_packages=lambda: [], reload_packages=Mock())
        unreal.Paths = SimpleNamespace(project_content_dir=lambda: str(self.root / 'Content'),
                                       project_saved_dir=lambda: str(self.root / 'Saved'),
                                       convert_relative_path_to_full=lambda value: value)
        unreal.load_asset = Mock(side_effect=lambda path: self.montages[path])
        unreal.AssetToolsHelpers = Mock(side_effect=AssertionError('Montage rebuild is forbidden'))
        for name in ('run', 'configure_candidate', 'add_window', 'ensure_interruption_signal',
                     'requested_step_rate', 'segment'):
            setattr(self.module, name, Mock(side_effect=AssertionError(name + ' is forbidden')))

    def auth(self, mode):
        return dict(request_id=self.module.CANCEL_SPLIT_REQUEST_ID, mode=mode,
                    host_pid=os.getpid(), window_id='window-test')

    def run(self, mode, name=None, **kwargs):
        return self.module.run_cancel_split(self.auth(mode), self.root / 'Saved' / (name or mode), **kwargs)

    def legacy(self, obj):
        return [n for n in self.state[obj]['notifies'] if n.values['guid'] == 'Cancel'][0]

    def snapshot(self):
        return {obj: [dict(n.values) for n in value['notifies']] for obj, value in self.state.items()}

    def assert_untouched_side_effects(self, test):
        for name in ('run', 'configure_candidate', 'add_window', 'ensure_interruption_signal',
                     'requested_step_rate', 'segment'):
            getattr(self.module, name).assert_not_called()
        self.unreal.AssetToolsHelpers.assert_not_called()
        self.unreal.EditorLoadingAndSavingUtils.reload_packages.assert_not_called()
        loaded = {call.args[0] for call in self.unreal.load_asset.call_args_list}
        test.assertTrue(loaded <= set(self.module.CANCEL_SPLIT_TARGETS))
        for relative in self.module.CANCEL_SPLIT_PROTECTED:
            data = (self.root / 'Content' / (relative + '.uasset')).read_bytes()
            test.assertEqual(data, b'protected:' + relative.encode())


class CancelSplitTests(unittest.TestCase):
    def harness(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        return CancelSplitHarness(temp.name, load)

    def report(self, h, name):
        return json.loads((h.root / 'Saved' / name / ('cancel_split_' + name.split('_')[0] + '.json'))
                          .read_text(encoding='utf-8'))

    def test_plan_is_read_only_and_targets_native_end_section(self):
        h = self.harness()
        before = h.snapshot()
        report = h.run('plan')
        self.assertTrue(report['success'])
        for record in report['records'].values():
            self.assertEqual(record['plan']['action'], 'append')
            self.assertEqual(record['plan']['main_end_f32'], h.module._f32_bits(h.main_end))
        h.unreal.AnimationLibrary.add_animation_notify_event.assert_not_called()
        h.unreal.EditorAssetLibrary.save_loaded_asset.assert_not_called()
        self.assertEqual(before, h.snapshot())
        h.assert_untouched_side_effects(self)
        self.assertTrue(self.report(h, 'plan')['success'])

    def test_author_appends_only_move_point_keeps_old_facts_and_saves_only_targets(self):
        for offset in ('before', 'none'):
            with self.subTest(offset=offset):
                h = self.harness()
                h.engine_offset = h.module.OFFSET_BEFORE if offset == 'before' else h.module.NO_OFFSET
                before = h.snapshot()
                report = h.run('author')
                self.assertTrue(report['success'])
                self.assertEqual(report['saved'], list(h.module.CANCEL_SPLIT_TARGETS))
                saved = [call.args[0] for call in h.unreal.EditorAssetLibrary.save_loaded_asset.call_args_list]
                self.assertEqual(saved, [h.montages[p] for p in h.module.CANCEL_SPLIT_TARGETS])
                for obj, notifies in h.snapshot().items():
                    self.assertEqual(notifies[:-1], before[obj], 'old notifies must stay bit-identical')
                for record in report['records'].values():
                    point = record['new_point']
                    self.assertEqual(point['time_f32'], h.module._f32_bits(h.main_end))
                    self.assertEqual(point['trigger_time_offset'], h.engine_offset)
                    self.assertEqual(record['before']['facts']['sections'],
                                     record['after']['facts']['sections'])
                h.assert_untouched_side_effects(self)

                cold = h.run('cold', name='cold_check', author_report=h.root / 'Saved/author/cancel_split_author.json')
                self.assertTrue(cold['success'])
                self.assertTrue(all(r['plan']['action'] == 'existing preserved' for r in cold['records'].values()))
                self.assertEqual(h.unreal.AnimationLibrary.add_animation_notify_event.call_count, 3)
                self.assertEqual(h.unreal.EditorAssetLibrary.save_loaded_asset.call_count, 3)

    def test_legacy_point_missing_duplicate_or_invalid_rejects_before_any_write(self):
        for invalid in ('missing', 'duplicate', 'case_duplicate', 'window', 'subclass',
                        'not_branching', 'foreign_link', 'duration'):
            with self.subTest(invalid=invalid):
                h = self.harness()
                obj = sorted(h.state)[2]
                notifies = h.state[obj]['notifies']
                legacy = h.legacy(obj)
                if invalid == 'missing':
                    notifies.remove(legacy)
                elif invalid in ('duplicate', 'case_duplicate'):
                    name = h.module.SIGNAL_NOTIFY_NAME
                    notifies.append(h.notify(obj, 'Cancel2', name.lower() if invalid == 'case_duplicate'
                                             else name, h.f32(0.5)))
                elif invalid == 'window':
                    notifies.append(h.notify(obj, 'Window2', h.module.SIGNAL_NOTIFY_NAME, h.f32(0.6),
                                             cls='', state=h.module.STOCK_WINDOW_CLASS,
                                             duration=h.f32(0.1), branching=True))
                elif invalid == 'subclass':
                    legacy.values['notify_class'] = '/Game/BP_CustomPoint.BP_CustomPoint_C'
                elif invalid == 'not_branching':
                    legacy.values['is_branching_point'] = False
                elif invalid == 'foreign_link':
                    legacy.values['linked_to_self'] = False
                else:
                    legacy.values['duration'] = h.f32(0.1)
                with self.assertRaises(h.module.CancelSplitError):
                    h.run('author')
                h.unreal.AnimationLibrary.add_animation_notify_event.assert_not_called()
                h.unreal.EditorAssetLibrary.save_loaded_asset.assert_not_called()
                self.assertFalse(self.report(h, 'author')['success'])
                h.assert_untouched_side_effects(self)

    def test_existing_move_point_is_preserved_only_at_main_end_and_never_moved(self):
        for case in ('valid', 'wrong_time', 'duplicate'):
            with self.subTest(case=case):
                h = self.harness()
                for obj in h.state:
                    time = h.main_end if case != 'wrong_time' else h.f32(1.0)
                    h.state[obj]['notifies'].append(h.notify(obj, 'MoveOld', h.module.MOVE_SIGNAL_NOTIFY_NAME,
                                                             time, offset=h.module.OFFSET_BEFORE))
                    if case == 'duplicate':
                        h.state[obj]['notifies'].append(h.notify(obj, 'MoveOld2', h.module.MOVE_SIGNAL_NOTIFY_NAME,
                                                                 h.main_end))
                before = h.snapshot()
                if case == 'valid':
                    report = h.run('author')
                    self.assertTrue(report['success'])
                    self.assertEqual(report['saved'], [])
                else:
                    with self.assertRaises(h.module.CancelSplitError):
                        h.run('author')
                h.unreal.AnimationLibrary.add_animation_notify_event.assert_not_called()
                h.unreal.EditorAssetLibrary.save_loaded_asset.assert_not_called()
                self.assertEqual(before, h.snapshot())

    def test_getter_unavailable_failed_or_incomplete_has_no_fallback(self):
        for case in ('no_library', 'no_function', 'failed', 'missing_field', 'nonfinite',
                     'not_float32', 'wrong_next', 'wrong_names'):
            with self.subTest(case=case):
                h = self.harness()
                obj = sorted(h.state)[0]
                end = h.state[obj]['sections'][1]
                if case == 'no_library':
                    del h.unreal.GGYGOLinearMontageAuthorLibrary
                elif case == 'no_function':
                    h.unreal.GGYGOLinearMontageAuthorLibrary = SimpleNamespace()
                elif case == 'failed':
                    h.unreal.GGYGOLinearMontageAuthorLibrary.read_montage_timeline_facts.side_effect = (
                        lambda montage: EditorStruct(succeeded=False, error='native failure', play_length=0.0,
                                                     sections=[], segments=[], notifies=[]))
                elif case == 'missing_field':
                    del end.values['time']
                elif case == 'nonfinite':
                    end.values['time'] = float('nan')
                elif case == 'not_float32':
                    end.values['time'] = 1.35
                elif case == 'wrong_next':
                    h.state[obj]['sections'][0].values['next_section_name'] = 'None'
                else:
                    end.values['section_name'] = 'Recovery'
                with self.assertRaises(h.module.CancelSplitError):
                    h.run('author')
                if case in ('no_library', 'no_function'):
                    h.unreal.load_asset.assert_not_called()
                h.unreal.AnimationLibrary.add_animation_notify_event.assert_not_called()
                h.unreal.EditorAssetLibrary.save_loaded_asset.assert_not_called()

    def test_section_time_is_main_end_even_when_segment_seam_float_differs(self):
        h = self.harness()
        obj = sorted(h.state)[0]
        h.state[obj]['segments'][1].values['start_pos'] = h.f32(1.3500001)
        report = h.run('author')
        record = report['records'][h.module.CANCEL_SPLIT_TARGETS[0]]
        self.assertFalse(record['plan']['segment_seam']['bitwise_equal'])
        self.assertEqual(record['new_point']['time_f32'], h.module._f32_bits(h.main_end))
        self.assertEqual(record['after']['facts']['segments'], record['before']['facts']['segments'])

    def test_actual_branching_trigger_collision_or_changed_old_fact_is_not_saved(self):
        for case in ('collision', 'old_notify_changed', 'geometry_changed'):
            with self.subTest(case=case):
                h = self.harness()
                obj = sorted(h.state)[0]
                if case == 'collision':
                    h.state[obj]['notifies'].append(h.notify(
                        obj, 'Other', 'Other', h.f32(h.main_end + h.module.OFFSET_BEFORE)))
                elif case == 'old_notify_changed':
                    h.added_hooks.append(lambda o: h.legacy(o).values.__setitem__('time', h.f32(0.3)))
                else:
                    h.added_hooks.append(lambda o: h.state[o].__setitem__('play_length', h.f32(6.5)))
                with self.assertRaises(h.module.CancelSplitError):
                    h.run('author')
                self.assertEqual(h.unreal.AnimationLibrary.add_animation_notify_event.call_count, 1)
                h.unreal.EditorAssetLibrary.save_loaded_asset.assert_not_called()
                report = self.report(h, 'author')
                self.assertFalse(report['success'])
                self.assertEqual(report['dirty_retained']['content'], [h.module.CANCEL_SPLIT_TARGETS[0]])
                h.assert_untouched_side_effects(self)

    def test_authorization_dirty_and_protection_guards(self):
        h = self.harness()
        for key, value in (('host_pid', os.getpid() + 1), ('window_id', ''), ('request_id', 'other'),
                           ('mode', 'save_all')):
            with self.subTest(key=key):
                authorization = h.auth('author')
                authorization[key] = value
                with self.assertRaises(h.module.CancelSplitError):
                    h.module.run_cancel_split(authorization, h.root / 'Saved' / ('auth_' + key))
                self.assertFalse((h.root / 'Saved' / ('auth_' + key)).exists())
        h.unreal.load_asset.assert_not_called()
        h.dirty.add('/Game/UserWork')
        with self.assertRaises(h.module.CancelSplitError):
            h.run('author', name='author_dirty')
        h.unreal.load_asset.assert_not_called()
        h.dirty.clear()
        ga = h.root / 'Content' / (h.module.CANCEL_SPLIT_PROTECTED[0] + '.uasset')
        original_save = h.save
        h.unreal.EditorAssetLibrary.save_loaded_asset.side_effect = (
            lambda montage, only_if_is_dirty: (ga.write_bytes(b'changed'), original_save(montage, False))[1])
        with self.assertRaisesRegex(h.module.CancelSplitError, 'protected'):
            h.run('author', name='author_protect')
        with self.assertRaises(FileExistsError):
            h.run('author', name='author_protect')


if __name__ == '__main__':
    unittest.main()
