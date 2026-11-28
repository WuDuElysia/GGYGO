"""刀光制作工具的失败重试与 Niagara 查询回归。正向渲染由正式普攻实拍覆盖。"""
from contextlib import ExitStack
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPTS = Path(__file__).resolve().parents[1]
with patch.object(sys, 'path', [str(SCRIPTS), *sys.path]), patch.dict(sys.modules):
    import_ue = Mock()
    import_ue.Paths.convert_relative_path_to_full.return_value = str(SCRIPTS.parents[1])
    sys.modules['unreal'] = import_ue
    import pyrios_source_slashes as slashes
    import pyrios_blade_reach as reach
    import refine_pyrios_blade as blade
    import zzz_fx_material_ue


class Material(Mock):
    pass


class MaterialInstance(Mock):
    pass


class Expression(Mock):
    pass


class MaterialRetryTest(unittest.TestCase):
    def setUp(self):
        self.ue = Mock(Material=Material, MaterialInstanceConstant=MaterialInstance, MaterialExpressionCustom=Expression)
        self.mat = Material()
        self.mat.get_path_name.return_value = '/Test/Wake'
        self.instance = MaterialInstance()
        self.instance.get_path_name.return_value = '/Test/WakeInstance'
        self.instance.parent = self.mat
        self.source = Mock()
        self.source.parent.get_path_name.return_value = '/Test/Original'
        self.node = Expression()
        self.fields = dict(description='随刃散开的气纹', code='上次的着色器')
        self.node.get_editor_property.side_effect = self.fields.__getitem__
        self.node.set_editor_property.side_effect = self.fields.__setitem__
        self.edit = self.ue.MaterialEditingLibrary
        self.edit.get_material_property_input_node.return_value = self.node
        self.edit.recompile_material.return_value = []
        self.editor = self.ue.EditorAssetLibrary
        self.editor.does_asset_exist.return_value = True
        tags = {(self.mat, 'Pyrios.WakeSource'): '/Test/Original'}
        self.editor.get_metadata_tag.side_effect = lambda obj, key: tags.get((obj, key), '')
        self.editor.set_metadata_tag.side_effect = lambda obj, key, value: tags.update({(obj, key): value})
        self.editor.remove_metadata_tag.side_effect = lambda obj, key: tags.pop((obj, key))
        self.editor.save_loaded_asset.return_value = True
        self.ue.load_asset.side_effect = lambda path: self.instance if '/MI_' in path else self.mat
        contexts = ExitStack()
        self.addCleanup(contexts.close)
        contexts.enter_context(patch.object(slashes, 'ue', self.ue))
        contexts.enter_context(patch.dict(sys.modules, zzz_fx_material_ue=zzz_fx_material_ue))

    def author(self):
        return slashes.opening_wake_material(self.source, 'Head')

    def test_compile_failure_retries_same_graph_and_reports_compiler_text(self):
        self.edit.recompile_material.side_effect = [['shader diagnostic'], []]
        with self.assertRaisesRegex(RuntimeError, 'shader diagnostic'):
            self.author()
        self.editor.save_loaded_asset.assert_not_called()
        self.assertIs(self.author(), self.instance)
        self.assertIs(self.author(), self.instance)
        self.assertEqual(self.edit.recompile_material.call_count, 2)
        self.editor.save_loaded_asset.assert_called_once_with(self.mat, False)

    def test_save_failure_retries_until_written_then_skips(self):
        self.editor.save_loaded_asset.side_effect = [False, False, True]
        for _ in range(2):
            with self.assertRaisesRegex(RuntimeError, '/Test/Wake'):
                self.author()
        self.assertIs(self.author(), self.instance)
        self.assertIs(self.author(), self.instance)
        self.assertEqual(self.editor.save_loaded_asset.call_count, 3)

    def test_instance_retries_without_recompiling_or_reassigning_parent(self):
        self.instance.parent = self.source.parent
        self.edit.set_material_instance_parent.side_effect = lambda obj, mat: setattr(obj, 'parent', mat)
        self.editor.save_loaded_asset.side_effect = [True, False, True]
        with self.assertRaises(RuntimeError):
            self.author()
        self.assertIs(self.author(), self.instance)
        self.assertIs(self.author(), self.instance)
        self.edit.recompile_material.assert_called_once_with(self.mat)
        self.edit.set_material_instance_parent.assert_called_once_with(self.instance, self.mat)
        self.assertEqual(self.editor.save_loaded_asset.call_count, 3)


class RendererQueryTest(unittest.TestCase):
    def test_query_failures_include_scope_and_stop_before_writing(self):
        system = Mock()
        system.get_path_name.return_value = '/Test/System'
        emitter = SimpleNamespace(emitter_name='TestEmitter')
        item = SimpleNamespace(renderer_index=2)
        for failed, scope in (('summary', '/Test/System'), ('identities', 'TestEmitter'), ('data', r'TestEmitter\[2\]')):
            with self.subTest(failed=failed), patch.object(blade, 'LIB') as lib:
                lib.authoring_get_system_summary.return_value = SimpleNamespace(
                    succeeded=failed != 'summary', emitters=[emitter], error='native diagnostic')
                lib.authoring_get_renderer_identities.return_value = SimpleNamespace(
                    succeeded=failed != 'identities', renderers=[item], error='native diagnostic')
                lib.authoring_get_renderer_data.return_value = SimpleNamespace(succeeded=False, error='native diagnostic')
                with self.assertRaisesRegex(RuntimeError, scope + '.*native diagnostic'):
                    blade.style_existing(system, None, True)
                lib.authoring_set_renderer_data.assert_not_called()
        with patch.object(blade, 'LIB') as lib:
            lib.authoring_get_system_summary.return_value = SimpleNamespace(succeeded=True, emitters=[])
            self.assertFalse(blade.style_existing(system, None, True))

    def test_size_lookup_preserves_mesh_validation_without_property_export(self):
        system = Mock()
        system.get_name.return_value = 'NS_Pyrios_Normal01_MainComposition_2a7c90937cab'
        name = 'M00_root_Trail_rot_Smoke_trail'
        item = SimpleNamespace(renderer_path='/Test/Renderer', renderer_class='NiagaraMeshRendererProperties')
        with patch.object(reach, 'LIB') as lib, patch.object(reach, 'ue') as ue:
            lib.authoring_get_system_summary.return_value = SimpleNamespace(
                succeeded=True, emitters=[SimpleNamespace(emitter_name=name)])
            lib.authoring_get_renderer_identities.return_value = SimpleNamespace(succeeded=True, renderers=[item])
            ue.find_object.return_value.get_editor_property.return_value = []
            with self.assertRaisesRegex(RuntimeError, '缺少唯一网格'):
                reach.fit_blade_meshes(system)
            ue.find_object.assert_called_once_with(None, item.renderer_path)
            lib.authoring_get_renderer_data.assert_not_called()


if __name__ == '__main__':
    unittest.main()
