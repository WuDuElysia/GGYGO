"""Offline failure/lifecycle regressions; no UE process or project asset writes."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace as NS
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1]
SESSION = '_ggygo_movement_level_probe_session'
MAP = '/Game/Map/L_Movement_Test'
GRID = '/Game/Map/Materials/M_MovementGrid'
GM = '/Game/BP/GamePlay/BP_GameMode.BP_GameMode_C'


class Object:
    def __init__(self, path='', **props):
        self.path, self.props = path, props

    def get_path_name(self):
        return self.path

    def get_name(self):
        return self.path

    def get_editor_property(self, name):
        return self.props[name]

    def set_editor_property(self, name, value):
        self.props[name] = value


def vector(x=0, y=0, z=0):
    return NS(x=x, y=y, z=z)


class Component(Object):
    def set_static_mesh(self, value):
        self.props['static_mesh'] = value

    def set_material(self, index, value):
        self.props['material'] = value

    def get_material(self, index):
        return self.props.get('material')

    def set_mobility(self, value):
        self.props['mobility'] = value

    def set_intensity(self, value):
        self.props['intensity'] = value

    def set_collision_profile_name(self, value):
        self.props['profile'] = value

    def set_collision_enabled(self, value):
        self.props['collision'] = value

    def set_collision_object_type(self, value):
        self.props['object_type'] = value

    def get_collision_profile_name(self):
        return self.props['profile']

    def get_collision_enabled(self):
        return self.props['collision']

    def get_collision_object_type(self):
        return self.props['object_type']

    def get_collision_response_to_channel(self, channel):
        return 'Block'


class Actor(Object):
    def __init__(self, location=None, rotation=None):
        super().__init__()
        self.location, self.rotation = location, rotation
        self.scale = vector(1, 1, 1)
        self.static_mesh_component = Component()
        self.light_component = Component()

    def set_actor_label(self, value):
        self.label = value

    def get_actor_label(self):
        return self.label

    def set_actor_scale3d(self, value):
        self.scale = value

    def get_actor_scale3d(self):
        return self.scale

    def get_actor_location(self):
        return self.location

    def get_actor_rotation(self):
        return self.rotation

    def set_folder_path(self, value):
        self.folder = value


def load(name, ue):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    previous = sys.modules.get('unreal')
    sys.modules['unreal'] = ue
    try:
        spec.loader.exec_module(module)
    finally:
        if previous is None:
            sys.modules.pop('unreal', None)
        else:
            sys.modules['unreal'] = previous
    return module


class ToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        sys.modules.pop(SESSION, None)
        self.addCleanup(lambda: sys.modules.pop(SESSION, None))
        self.callbacks = {}
        self.worlds = []
        self.actors = []
        self.dirty_maps, self.dirty_content = [], []
        self.assets = {}
        self.ue = NS(Paths=NS(project_saved_dir=lambda: str(self.root / 'Saved'),
                            project_content_dir=lambda: str(self.root / 'Content'),
                            convert_relative_path_to_full=lambda p: p),
                     Vector=vector, Rotator=lambda **kw: NS(**kw), log=Mock(), log_error=Mock())
        for name in ('Pawn', 'GGYGOExperienceDefinition', 'GGYGOPawnData', 'GGYGOMovementSet',
                     'GGYGOInputConfig', 'StaticMesh', 'Material'):
            setattr(self.ue, name, type(name, (Object,), {}))
        for name in ('StaticMeshActor', 'PlayerStart', 'DirectionalLight', 'SkyAtmosphere', 'SkyLight'):
            setattr(self.ue, name, type(name, (Actor,), {}))
        for name in ('LevelEditorSubsystem', 'EditorActorSubsystem', 'UnrealEditorSubsystem',
                     'EnhancedInputLocalPlayerSubsystem'):
            setattr(self.ue, name, name)
        self.ue.ComponentMobility = NS(STATIC='Static', MOVABLE='Movable')
        self.ue.CollisionEnabled = NS(QUERY_AND_PHYSICS='QueryAndPhysics')
        self.ue.CollisionChannel = NS(ECC_WORLD_STATIC='WorldStatic', ECC_PAWN='Pawn')
        self.ue.CollisionResponse = NS(BLOCK='Block')
        self.ue.CustomMaterialOutputType = NS(CMOT_FLOAT3='Float3')
        self.ue.MaterialProperty = NS(MP_BASE_COLOR='BaseColor', MP_ROUGHNESS='Roughness')
        for name in ('MaterialExpressionWorldPosition', 'MaterialExpressionCustom',
                     'MaterialExpressionConstant', 'MaterialFactoryNew', 'CustomInput'):
            setattr(self.ue, name, Object)
        self.ue.MaterialEditingLibrary = NS(create_material_expression=lambda *a: Object(),
            connect_material_expressions=Mock(), connect_material_property=Mock(), recompile_material=Mock())
        self.settings = Object(default_game_mode=None)
        self.world = Object('/Game/Map/Untitled.Untitled')
        self.world.get_world_settings = lambda: self.settings
        self.levels = NS(new_level=Mock(side_effect=self.new_level),
                         save_current_level=Mock(side_effect=lambda: self.save_file(MAP, '.umap')))
        self.actor_api = NS(spawn_actor_from_class=Mock(side_effect=self.spawn_actor),
                            get_all_level_actors=lambda: self.actors)
        systems = {'LevelEditorSubsystem': self.levels, 'EditorActorSubsystem': self.actor_api,
                   'UnrealEditorSubsystem': NS(get_editor_world=lambda: self.world)}
        self.ue.get_editor_subsystem = lambda name: systems[name]
        self.ue.EditorLevelLibrary = NS(get_pie_worlds=lambda flag: list(self.worlds),
                                        set_level_viewport_camera_info=Mock())
        self.ue.EditorLoadingAndSavingUtils = NS(get_dirty_map_packages=lambda: self.dirty_maps,
                                                  get_dirty_content_packages=lambda: self.dirty_content)
        self.ue.EditorAssetLibrary = NS(does_asset_exist=lambda p: p in self.assets,
            save_loaded_asset=Mock(side_effect=lambda obj: self.save_file(GRID, '.uasset')))
        self.ue.AssetToolsHelpers = NS(get_asset_tools=lambda: NS(create_asset=Mock(side_effect=self.create_material)))
        self.ue.load_asset = lambda p: self.assets.get(p)
        self.gm_class = Object(GM)
        self.pawn_class = Object('/Game/Player.Player_C')
        self.data = self.ue.GGYGOPawnData('/Game/Data.Data', pawn_class=self.pawn_class,
            movement_set=None, input_config=None)
        self.experience = self.ue.GGYGOExperienceDefinition('/Game/Exp.Exp', squad_members=[self.data])
        self.gm = Object(experience=self.experience)
        self.ue.load_class = lambda context, name: self.gm_class if name == GM else None
        self.ue.get_default_object = lambda cls: self.gm if cls is self.gm_class else self.ue.Pawn()
        self.assets['/Engine/BasicShapes/Cube'] = self.ue.StaticMesh('/Engine/BasicShapes/Cube.Cube')
        self.performance = Object(bThrottleCPUWhenNotForeground=True)
        self.performance.set_editor_property = Mock(wraps=self.performance.set_editor_property)
        self.ue.find_object = lambda *args: self.performance
        self.inputs = Object('/Engine/Transient.Inputs')
        self.inputs.inject_input_vector_for_action = Mock()
        self.ue.ObjectIterator = lambda cls: [self.inputs]
        self.assets['/Game/Input/Actions/IA_Move'] = Object('IA_Move')
        self.anim = Object(animation_state=NS(horizontal_speed=10, grounded=True,
            has_move_input=True, turn_back_phase='None'), state_memory=NS(gait_blend_y=0))
        self.pawn = NS(mesh=NS(get_anim_instance=lambda: self.anim),
            get_movement_component=lambda: NS(get_resolved_gait=lambda: 'Walk', movement_mode='Walking'),
            get_actor_location=lambda: vector(0, 0, 90.15), get_actor_rotation=lambda: NS(yaw=0))
        self.ue.GameplayStatics = NS(get_player_pawn=lambda w, i: self.pawn)
        self.ue.register_ticker_callback = Mock(side_effect=self.register)
        self.ue.unregister_ticker_callback = Mock(side_effect=lambda h: self.callbacks.pop(h))
        self.create = load('create_movement_test_level', self.ue)
        self.probe = load('verify_movement_test_level', self.ue)

    def save_file(self, package, extension):
        path = self.root / 'Content' / (package.removeprefix('/Game/') + extension)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(b'fake saved package')
        return True

    def create_material(self, *args):
        self.assets[GRID] = self.ue.Material(GRID + '.M_MovementGrid')
        return self.assets[GRID]

    def new_level(self, path):
        self.world.path = path + '.L_Movement_Test'
        self.assets[MAP] = self.world
        # Model UE saving the empty world before actors have been populated.
        self.save_file(MAP, '.umap')
        return True

    def spawn_actor(self, cls, location, rotation):
        actor = cls(location, rotation)
        self.actors.append(actor)
        return actor

    def register(self, callback):
        handle = len(self.callbacks) + 1
        self.callbacks[handle] = callback
        return handle

    def start(self):
        self.world.path = '/Game/Map/UEDPIE_0_L_Movement_Test.L_Movement_Test'
        self.worlds[:] = [self.world]
        return self.probe.start()

    def assert_clean(self):
        self.assertTrue(self.performance.get_editor_property('bThrottleCPUWhenNotForeground'))
        self.assertFalse(self.callbacks)
        self.assertIsNone(sys.modules[SESSION].active)

    def test_import_is_inert(self):
        self.assertFalse(self.callbacks)
        self.levels.new_level.assert_not_called()
        self.performance.set_editor_property.assert_not_called()
        self.assertFalse((self.root / 'Saved').exists())

    def test_duplicate_start_and_reload_share_owner(self):
        first = self.start()
        again = load('verify_movement_test_level', self.ue)
        self.assertIs(again.start(), first)
        self.assertIs(self.probe.start(), first)
        with self.assertRaises(RuntimeError):
            first.begin()
        self.assertEqual(len(self.callbacks), 1)
        first.stop()
        first.stop()
        self.ue.unregister_ticker_callback.assert_called_once()
        self.assert_clean()

    def test_phase_values_normal_finish_and_unique_reports(self):
        first = self.start()
        for delta in (0.5, 0.5, 31, 3, 3):
            first.tick(delta)
        self.assertEqual([s['axis'] for s in first.samples], [0, 1, -1, 0, 0])
        report = json.loads(first.output.read_text())
        self.assertEqual(report['status'], 'completed')
        self.assertFalse(report['runtime_acceptance_verified'])
        self.assert_clean()
        second = self.probe.start()
        second.stop()
        self.assertNotEqual(first.output, second.output)

    def test_invalid_input_on_pie_end_does_not_block_restoration(self):
        probe = self.start()
        probe.tick(1)
        self.worlds.clear()
        self.inputs.inject_input_vector_for_action.side_effect = RuntimeError('destroyed subsystem')
        self.assertFalse(probe.tick(1))
        self.assert_clean()
        self.assertTrue(any('release_input' in e for e in probe.errors))

    def test_sampling_exception_restores_and_reports(self):
        probe = self.start()
        self.anim.props.pop('animation_state')
        self.assertFalse(probe.tick(1))
        self.assertEqual(probe.reason, 'sample_error')
        self.assert_clean()

    def test_registration_failure_restores_and_releases_owner(self):
        self.ue.register_ticker_callback.side_effect = RuntimeError('register failed')
        with self.assertRaises(RuntimeError):
            self.start()
        self.assert_clean()
        self.inputs.inject_input_vector_for_action.assert_not_called()

    def test_report_write_failure_still_cleans_up(self):
        probe = self.start()
        with patch.object(Path, 'write_text', side_effect=OSError('disk full')):
            probe.stop()
        self.assert_clean()
        self.assertFalse(probe.report_written)
        probe.stop()
        self.assertTrue(probe.report_written)

    def test_restore_failure_blocks_new_owner_until_retry(self):
        probe = self.start()
        self.performance.set_editor_property.side_effect = RuntimeError('setting unavailable')
        probe.stop()
        with self.assertRaises(RuntimeError):
            self.probe.start()
        self.performance.set_editor_property.side_effect = None
        self.probe.stop()
        self.assert_clean()

    def test_unregister_failure_is_inert_and_false_tick_retires_it(self):
        probe = self.start()
        self.ue.unregister_ticker_callback.side_effect = RuntimeError('unregister failed')
        probe.stop()
        self.assertTrue(self.performance.get_editor_property('bThrottleCPUWhenNotForeground'))
        with self.assertRaises(RuntimeError):
            self.probe.start()
        self.assertFalse(probe.tick(1))
        self.callbacks.clear()  # FTSTicker consumes False.
        self.assert_clean()
        self.inputs.inject_input_vector_for_action.assert_not_called()

    def test_missing_experience_preflight_has_no_asset_writes(self):
        self.gm.props['experience'] = None
        result = self.create.run()
        self.assertEqual(result['status'], 'preflight_failed')
        self.levels.new_level.assert_not_called()
        self.assertNotIn(GRID, self.assets)

    def test_missing_pawn_class_stops_before_creation(self):
        self.data.props['pawn_class'] = None
        self.assertEqual(self.create.run()['status'], 'preflight_failed')
        self.levels.new_level.assert_not_called()
        self.assertNotIn(GRID, self.assets)

    def test_all_roster_entries_checked_before_writes(self):
        self.experience.props['squad_members'].append(None)
        result = self.create.run()
        self.assertEqual(result['status'], 'preflight_failed')
        self.assertIn('index 1', result['error'])
        self.levels.new_level.assert_not_called()
        self.assertNotIn(GRID, self.assets)

    def test_null_optional_pawn_data_is_serialized_and_repeat_is_read_only(self):
        first = self.create.run()
        self.assertEqual(first['status'], 'created', first)
        self.assertIsNone(first['configuration']['roster'][0]['movement_set'])
        self.assertIsNone(first['configuration']['roster'][0]['input_config'])
        second = self.create.run()
        self.assertEqual(second['status'], 'existing_inspected', second)
        self.assertEqual(len(self.actors), 5)
        self.levels.new_level.assert_called_once()
        self.levels.save_current_level.assert_called_once()
        self.assertNotEqual(first['report_path'], second['report_path'])

    def test_dirty_dependency_or_map_prevents_asset_mutation(self):
        for dirty_list, path in ((self.dirty_maps, '/Game/UserMap'), (self.dirty_content, '/Game/Data')):
            with self.subTest(path=path):
                dirty_list.append(Object(path))
                self.assertEqual(self.create.run()['status'], 'preflight_failed')
                dirty_list.clear()
        self.levels.new_level.assert_not_called()
        self.assertNotIn(GRID, self.assets)

    def test_wrong_material_type_and_unsaved_material_are_preserved(self):
        self.assets[GRID] = Object(GRID)
        self.assertEqual(self.create.run()['status'], 'preflight_failed')
        self.assets[GRID] = self.ue.Material(GRID)
        self.assertEqual(self.create.run()['status'], 'preflight_failed')
        self.levels.new_level.assert_not_called()
        self.ue.EditorAssetLibrary.save_loaded_asset.assert_not_called()

    def test_material_save_failure_stops_before_map_and_records_allocation(self):
        self.ue.EditorAssetLibrary.save_loaded_asset.side_effect = None
        self.ue.EditorAssetLibrary.save_loaded_asset.return_value = False
        result = self.create.run()
        self.assertEqual(result['status'], 'partial_failure')
        self.assertTrue(result['material_created'])
        self.assertFalse(result['material_saved'])
        self.levels.new_level.assert_not_called()
        self.assertEqual(self.create.run()['status'], 'preflight_failed')

    def test_map_save_failure_never_claims_empty_disk_package_is_complete(self):
        self.levels.save_current_level.side_effect = None
        self.levels.save_current_level.return_value = False
        result = self.create.run()
        self.assertEqual(result['status'], 'partial_failure')
        self.assertTrue(result['map_package_present'])
        self.assertFalse(result['map_saved'])
        self.dirty_maps.append(Object(MAP))
        self.assertEqual(self.create.run()['status'], 'preflight_failed')
        self.assertEqual(len(self.actors), 5)

    def test_material_save_true_without_disk_file_is_failure(self):
        self.ue.EditorAssetLibrary.save_loaded_asset.side_effect = None
        self.ue.EditorAssetLibrary.save_loaded_asset.return_value = True
        result = self.create.run()
        self.assertEqual(result['status'], 'partial_failure')
        self.assertTrue(result['material_created'])
        self.assertFalse(result['material_saved'])
        self.levels.new_level.assert_not_called()

    def test_new_level_failure_reports_unknown_allocation_and_disk_presence(self):
        def allocate_then_fail(path):
            self.new_level(path)
            return False
        self.levels.new_level.side_effect = allocate_then_fail
        result = self.create.run()
        self.assertEqual(result['status'], 'partial_failure')
        self.assertIsNone(result['map_created'])
        self.assertTrue(result['map_creation_attempted'])
        self.assertTrue(result['map_package_present'])
        self.assertFalse(result['map_saved'])
        self.levels.save_current_level.assert_not_called()

    def test_partial_actor_failure_is_retained_not_duplicated(self):
        self.actor_api.spawn_actor_from_class.side_effect = RuntimeError('spawn failed')
        first = self.create.run()
        self.assertEqual(first['status'], 'partial_failure')
        self.assertTrue(first['map_created'])
        self.assertFalse(first['map_saved'])
        self.assertEqual(self.create.run()['status'], 'existing_requires_review')
        self.levels.new_level.assert_called_once()

    def test_report_failure_recovered_by_read_only_inspection(self):
        with patch.object(Path, 'write_text', side_effect=OSError('disk full')):
            first = self.create.run()
        self.assertEqual(first['status'], 'report_failed')
        self.assertTrue(first['map_saved'])
        second = self.create.run()
        self.assertEqual(second['status'], 'existing_inspected')
        self.levels.save_current_level.assert_called_once()

    def test_user_geometry_edit_blocks_recovery_without_mutation(self):
        self.assertEqual(self.create.run()['status'], 'created')
        self.actors[0].scale.x = 17
        self.assertEqual(self.create.run()['status'], 'existing_requires_review')
        self.assertEqual(self.actors[0].scale.x, 17)
        self.levels.save_current_level.assert_called_once()

    def test_floor_and_start_rotation_are_checked_before_geometry_claim(self):
        self.assertEqual(self.create.run()['status'], 'created')
        for actor in self.actors[:2]:
            with self.subTest(actor=actor.label):
                actor.rotation.pitch = 15
                result = self.create.run()
                self.assertEqual(result['status'], 'existing_requires_review')
                self.assertFalse(result['configuration_verified'])
                actor.rotation.pitch = 0
        self.levels.save_current_level.assert_called_once()


if __name__ == '__main__':
    unittest.main()
