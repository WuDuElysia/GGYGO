"""@file Limited offline contracts and the original Stage affine reproduction.

Run with bundled Python -B. These tests neither import Unreal nor write fixtures
or evidence. Passing does not establish native API availability or visual smoke.
"""

import copy
import json
import math
import struct
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest import mock

import bh3_stage_environment_source as source
import restore_bh3_stage_environment as restore

REPORT = source.PROJECT/'Saved/AutomationReports/BH3_Stage_P3_Geometry_ac54612cec8243a0a6bdf86a5ae94f5d.json'


class StageSourceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = source.build_plan('P3',REPORT)
        cls.audit = source.geometry.audit_stage('P3')
        cls.components = source.read_json(cls.plan['source_components']['path'])['components']

    def test_actual_saved_geometry_and_exact_native_material_links(self):
        plan = source.validate_plan(self.plan)
        self.assertEqual(len(plan['geometry_actors']),120)
        self.assertEqual(len(plan['renderers']),97)
        self.assertEqual(sum(len(r['materials']) for r in plan['renderers']),99)
        self.assertEqual(sum(len(r['sections']) for r in plan['renderers']),99)
        self.assertEqual(len(plan['textures']),17)
        self.assertEqual((len(plan['lights']),len(plan['probes'])),(5,2))
        png = [t for t in plan['textures'].values() if t['class']=='Texture2D']
        self.assertEqual(len(png),14)
        self.assertEqual({t['native_settings']['m_ColorSpace'] for t in png},{1})
        self.assertTrue(all(not t['interpretation_verified'] for t in png))

    def test_repeated_display_paths_are_not_identity(self):
        paths = [c['nodePath'] for c in self.components if c['source']['type']=='GameObject']
        self.assertLess(len(set(paths)),120)
        mapping,poses,objects = source.map_nodes(self.components,self.audit,self.plan['geometry_actors'])
        self.assertEqual(len(set(mapping.values())),120)
        bad = copy.deepcopy(self.components)
        tr = next(c for c in bad if c['source']['type']=='Transform' and c['fields']['m_Father']['m_PathID']!=0)
        tr['fields']['m_LocalPosition']['x']+=1000
        with self.assertRaisesRegex(source.SourceError,'FBX matches'):
            source.map_nodes(bad,self.audit,self.plan['geometry_actors'])

    def test_parent_child_disagreement_is_not_a_name_fallback(self):
        bad = copy.deepcopy(self.components)
        tr = next(c for c in bad if c['source']['type']=='Transform' and c['fields']['m_Father']['m_PathID']!=0)
        tr['fields']['m_Father']['m_PathID']=123
        with self.assertRaisesRegex(source.SourceError,'child/parent disagreement'):
            source.map_nodes(bad,self.audit,self.plan['geometry_actors'])

    def test_original_nonuniform_scale_failure_and_full_affine_correction(self):
        expected_ids = {'1934927611984','1934927619984','1934927617984','1934927621984','1934927615984',
                        '1934927613984','1934927623984','1934927609984','1934927625984','1934927637984'}
        self.assertEqual({r['model'] for r in self.plan['affine_meshes']},expected_ids)
        for row in self.plan['affine_meshes']:
            # Preserve the original failure: saved native TRS is not the source
            # parent*child affine. Setting a Ready flag or comparing translation
            # alone would conceal this mismatch.
            self.assertGreater(source.difference(row['source_world'],row['saved_world']),.1)
            self.assertEqual(self.plan['geometry_actors'][row['model']]['parent_source_id'],'1934927451616')
            corrected = source.multiply(row['saved_world'],row['correction'])
            self.assertLess(source.difference(corrected,row['source_world']),1e-7)
            for vertex in ([0,0,0],[100,-20,40],[-100,20,-40]):
                actual=source.point(row['saved_world'],source.point(row['correction'],vertex))
                expected=source.point(row['source_world'],vertex)
                self.assertLess(max(abs(a-b) for a,b in zip(actual,expected)),1e-7)

    def test_resolved_cube_and_native_water_depth_are_retained(self):
        water = next(m for m in self.plan['materials'].values() if m['name']=='Stage_KevinBossP3_Nat_Ground_01_LOD0')
        self.assertEqual(water['fields']['m_SavedProperties']['m_Floats']['_Zwrite'],1)
        self.assertIn(water['textures']['_ReflectionCube'],self.plan['textures'])
        self.assertEqual(self.plan['textures'][water['textures']['_ReflectionCube']]['class'],'TextureCube')

    def test_source_disabled_collision_is_not_activated_by_preview(self):
        real_mesh=[c for c in self.plan['colliders'] if not c['mesh_is_null']]
        self.assertEqual(len(real_mesh),2)
        self.assertTrue(all(not c['owner_active'] for c in real_mesh))
        self.assertTrue(all(c['fields']['m_Enabled'] for c in real_mesh))
        self.assertEqual(sum(c['mesh_is_null'] for c in self.plan['colliders']),1)
        self.assertFalse(self.plan['restoration_complete'])

    def test_explicit_program_selection_preserves_pass_context(self):
        shader = next(s for s in self.plan['shaders'].values() if s['name'].endswith('/Layer1/Additive'))
        keywords=shader['passes'][0]['programs']['ps'][0]['keywords']
        selected=source.select_program(shader,0,'ps',keywords)
        self.assertEqual(selected['source_stage'],'progFragment')
        with self.assertRaises(source.SourceError):source.select_program(shader,0,'ps',keywords+['unknown_keyword'])
        with self.assertRaises(source.SourceError):source.select_program(shader,99,'ps',keywords)
        reflected=source.reflected_subprogram(selected)
        self.assertTrue(reflected['asm'][0].startswith('ps_'))
        self.assertTrue(reflected['bind']['cbbind'])
        dependencies=source.native_fragment_dependencies(shader,0,keywords)
        self.assertIn('_BlackEffect',dependencies['missing_globals'])
        self.assertFalse(dependencies['source_runtime_selection_verified'])

    def test_plan_tampering_and_duplicate_json_keys_fail(self):
        bad=copy.deepcopy(self.plan)
        bad['renderers'][0]['materials'][0]='invented/material'
        with self.assertRaisesRegex(source.SourceError,'plan content changed'):source.validate_plan(bad)
        with mock.patch.object(Path,'read_text',return_value='{"stage":"P3","stage":"P1"}'):
            with self.assertRaisesRegex(source.SourceError,'duplicate JSON key'):source.read_json('not-written')

    def test_material_policy_and_source_bindings_are_required(self):
        with self.assertRaisesRegex(source.SourceError,'Stage UE adaptation'):
            restore.validate_settings(self.plan,{'plan_digest':self.plan['digest']},'materials')
        material=next(iter(self.plan['materials'].values()))
        graph={'nodes':[{'id':'sample','class':'MaterialExpressionTextureSampleParameter2D','source_texture':'absent'}],
               'outputs':[{'node':'sample','property':'MP_BASE_COLOR'}]}
        with self.assertRaisesRegex(source.SourceError,'native material slot'):restore.validate_graph(material,graph)
        graph={'nodes':[{'id':'a','class':'MaterialExpressionMultiply'},{'id':'b','class':'MaterialExpressionMultiply'}],
               'edges':[{'from':'a','to':'b'},{'from':'b','to':'a'}],
               'outputs':[{'node':'a','property':'MP_BASE_COLOR'}]}
        with self.assertRaisesRegex(source.SourceError,'cyclic'):restore.validate_graph(material,graph)

    def test_create_only_registry_and_disk_each_protect_existing_work(self):
        class Assets:
            @staticmethod
            def does_asset_exist(package):return True
        u=type('NativeStub',(),{'EditorAssetLibrary':Assets})
        with mock.patch.object(Path,'exists',return_value=False):
            with self.assertRaisesRegex(source.SourceError,'already exists'):restore.absent_targets(u,self.plan,'textures')
        with mock.patch.object(Path,'exists',return_value=True):
            with self.assertRaisesRegex(source.SourceError,'already exists'):restore.absent_targets(u,self.plan,'materials')

    def test_affine_phase_does_not_require_a_material_policy(self):
        restore.validate_settings(self.plan,{'plan_digest':self.plan['digest']},'affine')
        self.assertEqual(len(restore.targets(self.plan,'affine')),10)
        self.assertTrue(all('/StaticMeshes/SourceAffine/' in p for p in restore.targets(self.plan,'affine')))

    def test_unplanned_object_refused_before_any_metadata_or_save(self):
        class ForeignObject:
            def get_path_name(self):return self.plan_root+'/Materials/NotInSource.NotInSource'
        obj=ForeignObject();obj.plan_root=self.plan['asset_root']
        with self.assertRaisesRegex(source.SourceError,'foreign/unplanned'):
            restore.stamp_save(None,obj,self.plan,['foreign','identity'],{'saved_assets':[]})

    def test_compile_failure_and_old_void_api_cannot_publish_success(self):
        class NativeArray:
            def __iter__(self):return iter([])
        restore.verify_compile_result(NativeArray())
        with self.assertRaisesRegex(source.SourceError,'compilation failed'):
            restore.verify_compile_result(['unknown source input'])
        for invalid in [None,True,'',{}]:
            with self.assertRaisesRegex(source.SourceError,'did not return diagnostics'):
                restore.verify_compile_result(invalid)


class StageEquivalentContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan=source.validate_plan(source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P3_Source_Plan_20261008_233000.json'))
        cls.settings=source.equivalent_settings(cls.plan)
        cls.geometry=source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P3_Map_Geometry_Apply_20261009_Resume.json')
        cls.baseline=restore.geometry_expected_state(cls.geometry['map_geometry_baseline'],cls.geometry['geometry_binding_changes'])

    def test_selected_equivalent_policy_is_complete_without_changing_source_identity(self):
        before=copy.deepcopy(self.plan)
        policy=source.equivalent_settings(self.plan)
        for mode in ('textures','materials','map','lighting','readback','lighting_readback','assets_readback','preflight'):
            restore.validate_settings(self.plan,policy,mode)
        self.assertEqual(self.plan,before)
        self.assertEqual(policy['plan_digest'],'c63267d0124107931cc369f921d52b4d5ce15b5260b8ea5ad54e2b7ab7d2bebf')
        self.assertEqual({g['family'] for g in policy['rendering']['materials'].values()},
                         {'Scene_Base','Water_Base','FogEffect_Texture_Additive_Soft','AirEffect_LightMap','Additive'})
        self.assertFalse(policy['source_runtime_verified'])
        self.assertFalse(policy['collision_modified'])
        self.assertEqual(len(policy['rendering']['materials']),10)

    def test_every_real_texture_slot_is_bound_and_null_slots_are_not_invented(self):
        for key,m in self.plan['materials'].items():
            graph=self.settings['rendering']['materials'][key]
            slots=[n['source_texture'] for n in graph['nodes'] if 'source_texture' in n]
            self.assertEqual(set(slots),set(m['textures']))
            self.assertEqual(len(slots),len(set(slots)))
        self.assertEqual(len(self.settings['textures']),17)
        data={key for m in self.plan['materials'].values() for slot,key in m['textures'].items()
              if slot in ('_BumpMap','_Normal01','_Normal02','_MaskTex','_CausticTex')}
        self.assertTrue(all(not self.settings['textures'][key]['srgb'] for key in data))
        for key,t in self.plan['textures'].items():
            if t['class']=='TextureCube' and t['layout']['formatName']=='BC6H_UF16':
                self.assertEqual(self.settings['textures'][key]['compression'],'TC_HDR')
                self.assertFalse(self.settings['textures'][key]['srgb'])

    def test_partial_material_failure_only_accepts_recorded_owned_targets(self):
        previous=source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P3_Materials_Create_20261009_R2.json')
        packages=restore.material_resume_packages(self.plan,previous)
        self.assertEqual(len(packages),4)
        self.assertEqual(packages,previous['saved_assets'])
        for field,value in [('mode','map'),('phase','materials_passed'),('plan_digest','foreign'),
                            ('map_saved',True),('created_actors',['foreign'])]:
            bad=copy.deepcopy(previous);bad[field]=value
            with self.assertRaises(source.SourceError):restore.material_resume_packages(self.plan,bad)
        for extra in (packages[0],'/Game/Foreign/Material'):
            bad=copy.deepcopy(previous);bad['saved_assets'].append(extra)
            with self.assertRaises(source.SourceError):restore.material_resume_packages(self.plan,bad)

    def test_probe_first_window_has_exactly_two_disjoint_cube_targets(self):
        probes=restore.targets(self.plan,'probe_textures')
        surface=restore.targets(self.plan,'surface_textures')
        self.assertEqual(len(probes),2)
        self.assertEqual(set(probes.values()),{'TextureCube'})
        self.assertEqual({p.rsplit('/',1)[1] for p in probes},
                         {'T_LunarCrater_Reflection_Probe_Importance2','T_Stage_ElysionSkill_Sky_Ocean'})
        self.assertFalse(set(probes)&set(surface))
        self.assertEqual(len(surface),15)
        self.assertEqual(set(probes)|set(surface),set(restore.targets(self.plan,'textures')))
        restore.validate_settings(self.plan,self.settings,'probe_textures_readback')

    def test_source_uv_alpha_test_water_and_disabled_caustics_have_distinct_semantics(self):
        for key,m in self.plan['materials'].items():
            graph=self.settings['rendering']['materials'][key]
            nodes={n['id']:n for n in graph['nodes']}
            for slot in m['textures']:
                if self.plan['textures'][m['textures'][slot]]['class']=='TextureCube':continue
                env=m['fields']['m_SavedProperties']['m_TexEnvs'][slot]
                self.assertEqual(nodes['UE_UVScale'+slot]['properties']['default_value']['linear_color'][:2],
                                 [env['m_Scale']['X'],env['m_Scale']['Y']])
                self.assertEqual(nodes['UE_UVOffset'+slot]['properties']['default_value']['linear_color'][:2],
                                 [env['m_Offset']['X'],env['m_Offset']['Y']])
            if graph['family']=='Scene_Base':
                enabled=m['fields']['m_SavedProperties']['m_Floats']['_EnableAlphaTest']
                self.assertEqual(graph['blend_mode'],'BLEND_MASKED' if enabled else 'BLEND_OPAQUE')
                if enabled:
                    mask=next(o for o in graph['outputs'] if o['property']=='MP_OPACITY_MASK')
                    self.assertEqual(mask,{'node':'Texture_MainTex','output':'A','property':'MP_OPACITY_MASK'})
            if graph['family']=='Water_Base':
                self.assertEqual(m['fields']['m_SavedProperties']['m_Floats']['_Zwrite'],1)
                self.assertEqual(graph['shading_model'],'MSM_SINGLE_LAYER_WATER')
                self.assertEqual(graph['blend_mode'],'BLEND_OPAQUE')
                self.assertEqual(nodes['EnableCaustics']['source_scalar'],'_EnableCausticTex')

    def test_actual_cube_transport_keeps_all_tail_mips_and_hdr_half_values(self):
        settings=source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P3_UE_Equivalent_Settings_20261009_Lighting_R3.json')
        converted=[(self.plan['textures'][k],v) for k,v in settings['textures'].items() if 'decoded_cube' in v]
        self.assertEqual(len(converted),2)
        for row,cfg in converted:
            proof=cfg['decoded_cube'];path=source.cube_import_file(row,cfg);raw=Path(path['path']).read_bytes()
            self.assertEqual(len(proof['subresources']),54)
            self.assertEqual([(r['width'],r['height']) for r in proof['subresources'][-2:]],[(2,2),(1,1)])
            observed=source.verify_exported_cube(raw,row,cfg)
            self.assertTrue(observed['source_pixels_exact'])
            if observed['hdr']:
                rgb=[v for pixel in struct.iter_unpack('<4e',raw[148:]) for v in pixel[:3]]
                self.assertAlmostEqual(max(rgb),2.2109375)
                self.assertEqual(sum(v>1 for v in rgb),365)
                self.assertTrue(all(pixel[3]==1 for pixel in struct.iter_unpack('<4e',raw[148:])))

    def test_cube_native_readback_rejects_lost_pixels_and_accepts_bgra_swizzle(self):
        settings=source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P3_UE_Equivalent_Settings_20261009_Lighting_R3.json')
        key=next(k for k,v in settings['textures'].items() if 'decoded_cube' in v and self.plan['textures'][k]['layout']['formatName']=='BC1_UNORM')
        row,cfg=self.plan['textures'][key],settings['textures'][key]
        raw=bytearray(Path(cfg['decoded_cube']['file']['path']).read_bytes())
        pixels=bytes(raw[148:]);raw[148::4],raw[150::4]=pixels[2::4],pixels[0::4]
        struct.pack_into('<I',raw,128,91)
        self.assertTrue(source.verify_exported_cube(raw,row,cfg)['source_pixels_exact'])
        raw[150]^=1
        with self.assertRaisesRegex(source.SourceError,'face 0 mip 0'):source.verify_exported_cube(raw,row,cfg)
        with self.assertRaises(source.SourceError):source.verify_exported_cube(raw[:-8],row,cfg)

    def test_surface_continuation_preserves_lamp_generation_and_two_cube_policies(self):
        settings=source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P3_UE_Equivalent_Settings_20261009_Materials.json')
        original=source.read_json(settings['preserved_lighting']['settings']['path'])
        generation=source.lighting_generation_digest(self.plan,settings)
        self.assertEqual(generation,source.digest(original))
        self.assertNotEqual(generation,source.digest(settings))
        restore.validate_settings(self.plan,settings,'map')
        for key in {r['texture'] for r in self.plan['probes']}:
            self.assertEqual(settings['textures'][key],original['textures'][key])
        broken=copy.deepcopy(settings)
        broken['lighting']['local_intensity_scale']*=2
        with self.assertRaisesRegex(source.SourceError,'preserved lighting policy'):
            source.lighting_generation_digest(self.plan,broken)
        broken=copy.deepcopy(settings)
        key=self.plan['probes'][0]['texture'];broken['textures'][key]['srgb']=not broken['textures'][key]['srgb']
        with self.assertRaisesRegex(source.SourceError,'preserved probe Cube'):
            source.lighting_generation_digest(self.plan,broken)

    def test_explicit_intensity_calibration_preserves_generation_and_rejects_other_changes(self):
        path=source.PROJECT/'Saved/BH3StageEnvironment/P3_UE_Equivalent_Settings_20261009_Materials_R2.json'
        original=source.read_json(path)
        selected=copy.deepcopy(original)
        selected['lighting'].update(directional_lux_scale=1.,local_intensity_scale=1.)
        selected['lighting_calibration']={'purpose':'ue_visual_intensity_calibration',
            'source_photometry_verified':False,'reason':'同相机直接光隔离验证',
            'baseline_settings':source.evidence(path)}
        self.assertEqual(source.lighting_generation_digest(self.plan,selected),
                         source.lighting_generation_digest(self.plan,original))
        restore.validate_settings(self.plan,selected,'lighting_readback')
        for field in ('local_falloff_exponent','indirect_lighting_intensity'):
            broken=copy.deepcopy(selected);broken['lighting'][field]*=2
            with self.assertRaisesRegex(source.SourceError,'protected light policy'):
                source.lighting_generation_digest(self.plan,broken)
        broken=copy.deepcopy(selected)
        key=self.plan['probes'][0]['texture'];broken['textures'][key]['srgb']=not broken['textures'][key]['srgb']
        with self.assertRaisesRegex(source.SourceError,'protected surface/probe'):
            source.lighting_generation_digest(self.plan,broken)
        broken=copy.deepcopy(selected);broken['lighting']['local_intensity_scale']=0.
        with self.assertRaisesRegex(source.SourceError,'intensity is invalid'):
            source.lighting_generation_digest(self.plan,broken)

    def test_missing_slot_custom_input_and_zero_light_calibration_fail(self):
        key=next(iter(self.plan['materials']))
        broken=copy.deepcopy(self.settings)
        graph=broken['rendering']['materials'][key]
        graph['nodes']=[n for n in graph['nodes'] if n.get('source_texture')!='_MainTex']
        with self.assertRaises(source.SourceError):restore.validate_settings(self.plan,broken,'materials')
        broken=copy.deepcopy(self.settings)
        graph=broken['rendering']['materials'][key]
        custom=next(n for n in graph['nodes'] if 'custom_inputs' in n)
        graph['edges']=[e for e in graph['edges'] if e['to']!=custom['id']]
        with self.assertRaisesRegex(source.SourceError,'missing/unplanned inputs'):
            restore.validate_settings(self.plan,broken,'materials')
        for value in (0,-1,float('nan')):
            broken=copy.deepcopy(self.settings);broken['lighting']['local_intensity_scale']=value
            with self.assertRaises(source.SourceError):restore.validate_settings(self.plan,broken,'lighting')

    def test_light_color_quantization_and_calibration_do_not_add_a_default_sun(self):
        self.assertEqual(len(self.plan['lights']),5)
        for row in self.plan['lights']:
            values=restore.light_values(row,self.settings)
            rgb=[int(math.floor(row['fields']['m_Color'][c]*255+.5)) for c in ('r','g','b')]
            self.assertEqual(values['light_color'],rgb+[255])
            scale=self.settings['lighting']['directional_lux_scale' if row['fields']['m_Type']==1
                                            else 'local_intensity_scale']
            self.assertAlmostEqual(values['intensity'],row['fields']['m_Intensity']*scale)
            self.assertFalse(values['cast_shadows'])
            pose=restore.environment_pose(row,True)
            self.assertEqual(pose['translation'],[0.,0.,0.])
            self.assertAlmostEqual(sum(v*v for v in pose['quaternion']),1)
        for probe in self.plan['probes']:
            pose=restore.environment_pose(probe,False)
            self.assertEqual(pose['scale'],[probe['fields']['m_BoxSize'][a]*50 for a in ('x','y','z')])

    def test_lighting_and_material_checkpoints_preserve_actual_geometry_and_collision(self):
        self.assertEqual(restore.environment_expected_state(self.baseline,self.plan,False),self.baseline)
        expected=restore.environment_expected_state(self.baseline,self.plan,True)
        self.assertEqual(len(expected['actors']),121)
        changes={r['actor'] for r in self.plan['renderers']}
        for path,actor in self.baseline['actors'].items():
            after=expected['actors'][path]
            self.assertEqual(actor['parent'],after['parent'])
            self.assertEqual(actor['world_transform'],after['world_transform'])
            self.assertEqual(actor['collision_enabled'],after['collision_enabled'])
            for cp,c in actor['components'].items():
                a=after['components'][cp]
                for key in ('static_mesh','body_instance','relative_transform','parent'):
                    if key in c:self.assertEqual(c[key],a[key])
            if path not in changes:self.assertEqual(actor,after)
        for binding in self.geometry['geometry_binding_changes']:
            self.assertEqual(expected['actors'][binding['actor']]['components'][binding['component']]['static_mesh'],binding['to_mesh'])
        bad=copy.deepcopy(expected)
        renderer=self.plan['renderers'][0]['actor']
        component=next(c for c in bad['actors'][renderer]['components'].values() if 'body_instance' in c)
        component['body_instance']='CollisionEnabled=NoCollision'
        with self.assertRaisesRegex(source.SourceError,'protected state'):
            restore.verify_geometry_state(bad,expected)

    def test_old_or_foreign_map_checkpoint_cannot_authorize_a_write(self):
        current=self.geometry['map_file']
        with mock.patch.object(source,'read_json',return_value=self.geometry):
            expected,created=restore.accepted_map_baseline(self.plan,self.settings,'accepted',current,False)
            self.assertEqual(expected,self.baseline);self.assertEqual(created,[])
            with self.assertRaisesRegex(source.SourceError,'stale/foreign'):
                restore.accepted_map_baseline(self.plan,self.settings,'accepted',{'sha256':'old'},False)
            with self.assertRaisesRegex(source.SourceError,'lighting checkpoint'):
                restore.accepted_map_baseline(self.plan,self.settings,'accepted',current,True)

    def environment_apply_fixture(self):
        world=mock.Mock();world.get_path_name.return_value=self.baseline['world']
        levels=mock.Mock();levels.get_current_level.return_value.get_path_name.return_value=self.baseline['world']+':PersistentLevel'
        levels.save_current_level.return_value=True
        editor=mock.Mock();editor.destroy_actor.return_value=True
        class Native:
            LevelEditorSubsystem=object()
            EditorActorSubsystem=object()
            EditorLoadingAndSavingUtils=mock.Mock()
            @classmethod
            def get_editor_subsystem(cls,kind):
                return levels if kind is cls.LevelEditorSubsystem else editor
        Native.EditorLoadingAndSavingUtils.get_dirty_map_packages.return_value=[]
        Native.EditorLoadingAndSavingUtils.get_dirty_content_packages.return_value=[]
        return Native,world,levels,editor

    def run_lighting_fixture(self,verify):
        u,world,levels,editor=self.environment_apply_fixture()
        result={'saved_assets':[],'created_actors':[],'map_saved':False}
        def spawn(u,plan,settings,actors,result,created):
            created.extend(mock.Mock() for _ in range(7))
            result['created_actors'].extend('owned_'+str(i) for i in range(7))
        with mock.patch.object(Path,'is_file',return_value=True), \
             mock.patch.object(source,'evidence',return_value=self.geometry['map_file']), \
             mock.patch.object(restore,'verify_assets'), \
             mock.patch.object(restore,'map_actors',return_value=(world,{},{})), \
             mock.patch.object(restore,'map_geometry_state',return_value=copy.deepcopy(self.baseline)), \
             mock.patch.object(restore,'accepted_map_baseline',return_value=(self.baseline,[])), \
             mock.patch.object(restore,'preserved_environment_state'), \
             mock.patch.object(restore,'spawn_environment',side_effect=spawn), \
             mock.patch.object(restore,'verify_map',side_effect=verify):
            try:
                restore.apply_map(u,self.plan,self.settings,result,self.geometry['map_file']['sha256'],
                                  source.PROJECT/'Saved/ExistingBackup.umap','accepted',False)
            except source.SourceError:
                return result,levels,editor,True
        return result,levels,editor,False

    def test_lighting_commit_checks_current_world_and_saves_only_once(self):
        calls=[]
        def verify(u,plan,settings,materials,load):
            calls.append((materials,load))
            self.assertFalse(load,'verification must not reload and discard unsaved lamps')
            return {'source_lights':5,'source_probes':2,'visual_verified':False}
        result,levels,editor,failed=self.run_lighting_fixture(verify)
        self.assertFalse(failed)
        self.assertEqual(calls,[(False,False)])
        self.assertTrue(result['map_saved'])
        self.assertFalse(result['materials_applied'])
        self.assertEqual(result['saved_assets'],[])
        levels.save_current_level.assert_called_once_with()
        editor.destroy_actor.assert_not_called()

    def test_failed_lamp_contract_reclaims_only_owned_spawns_and_never_saves(self):
        def reject(*args):raise source.SourceError('source lamp binding invalid')
        result,levels,editor,failed=self.run_lighting_fixture(reject)
        self.assertTrue(failed)
        self.assertFalse(result['map_saved'])
        self.assertEqual(editor.destroy_actor.call_count,7)
        self.assertEqual(result['cleanup_errors'],[])
        levels.save_current_level.assert_not_called()

    def test_dirty_map_is_rejected_before_load_not_after_discard(self):
        u,world,levels,editor=self.environment_apply_fixture()
        u.EditorLoadingAndSavingUtils.get_dirty_map_packages.return_value=['user_unsaved_map']
        with self.assertRaisesRegex(source.SourceError,'unsaved map work'):
            restore.map_actors(u,self.plan,True)
        levels.load_level.assert_not_called()

    def capture_finish_fixture(self):
        capture=restore.StageCapture.__new__(restore.StageCapture)
        capture.u,capture.world,_,capture.editor=self.environment_apply_fixture()
        capture.u.EditorPythonScripting=mock.Mock()
        capture.u.unregister_slate_post_tick_callback=mock.Mock()
        capture.u.log=mock.Mock()
        capture.finished=False
        capture.performance_settings=None;capture.previous_throttle=None
        capture.task=None;capture.handle='owned_callback';capture.previous_view=('original_location','original_rotation')
        capture.previous_selection=None
        capture.editor.get_level_viewport_camera_info.return_value=capture.previous_view
        capture.baseline=self.baseline
        capture.result={};capture.output=Path('unused-result');capture.image=Path('unused-image.png')
        return capture

    def test_capture_cleanup_failure_stays_failed_and_finishes_once(self):
        capture=self.capture_finish_fixture()
        capture.editor.set_level_viewport_camera_info.side_effect=RuntimeError('viewport restoration denied')
        with mock.patch.object(restore,'map_geometry_state',return_value=self.baseline), \
             mock.patch.object(source,'write_machine') as write:
            capture.finish(None)
            capture.finish(None)
        self.assertEqual(capture.result['phase'],'failed')
        self.assertIn('viewport restoration denied',capture.result['cleanup_errors'][0])
        write.assert_called_once()
        capture.u.unregister_slate_post_tick_callback.assert_called_once_with('owned_callback')
        capture.editor.set_level_viewport_camera_info.assert_called_once_with('original_location','original_rotation')
        capture.u.EditorPythonScripting.set_keep_python_script_alive.assert_called_once_with(False)

    def test_capture_result_write_failure_still_releases_editor_lifetime(self):
        capture=self.capture_finish_fixture()
        with mock.patch.object(restore,'map_geometry_state',return_value=self.baseline), \
             mock.patch.object(source,'write_machine',side_effect=OSError('result write denied')):
            with self.assertRaisesRegex(OSError,'result write denied'):capture.finish(None)
        self.assertTrue(capture.finished)
        capture.editor.set_level_viewport_camera_info.assert_called_once_with('original_location','original_rotation')
        capture.u.EditorPythonScripting.set_keep_python_script_alive.assert_called_once_with(False)


class StageP1Contracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = source.validate_plan(source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P1_Source_Plan_20261009.json'))
        cls.settings = source.equivalent_settings(cls.plan)
        cls.audit = source.geometry.audit_stage('P1')
        cls.components = source.read_json(cls.plan['source_components']['path'])['components']

    def test_coincident_props_require_authored_rotation_identity(self):
        mapping, _, _ = source.map_nodes(self.components, self.audit, self.plan['geometry_actors'])
        self.assertEqual(len(set(mapping.values())), 146)
        self.assertEqual(mapping['2114235041343653701'], '1580591275680')
        bad = copy.deepcopy(self.components)
        transform = next(c for c in bad if c['source']['type'] == 'Transform'
                         and str(c['fields']['m_GameObject']['m_PathID']) == '2114235041343653701')
        transform['fields']['m_LocalRotation'] = {'x': 0., 'y': 0., 'z': 0., 'w': 1.}
        with self.assertRaisesRegex(source.SourceError, 'FBX matches'):
            source.map_nodes(bad, self.audit, self.plan['geometry_actors'])

    def test_exact_scene_targets_record_the_one_native_fbx_binding_difference(self):
        self.assertEqual((len(self.plan['renderers']), sum(len(r['materials']) for r in self.plan['renderers'])), (77, 221))
        self.assertEqual((len(self.plan['materials']), len(self.plan['textures']), len(self.plan['lights']), len(self.plan['probes'])), (40, 75, 27, 1))
        self.assertEqual(self.plan['affine_meshes'], [])
        self.assertEqual(self.plan['unbound_materials'], [])
        self.assertIn('Stage_NewSpaceship_Fan_PropsA_Star', {m['name'] for m in self.plan['materials'].values()})
        self.assertEqual(self.plan['fbx_binding_differences'], source.P1_SOURCE_BINDING_DIFFERENCES)
        self.assertEqual(len(restore.targets(self.plan, 'textures')), 75)
        self.assertEqual(len(restore.targets(self.plan, 'materials')), 40)
        bad = copy.deepcopy(self.plan)
        bad['fbx_binding_differences'] = []
        bad['digest'] = source.digest({k: v for k, v in bad.items() if k != 'digest'})
        with self.assertRaisesRegex(source.SourceError, 'native renderer binding contract'):
            source.validate_plan(bad)
        restore.validate_settings(self.plan, self.settings, 'materials')
        old = source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P3_Source_Plan_20261008_233000.json')
        self.assertEqual(source.build_plan('P3', old['geometry_report']['path'])['digest'], old['digest'])

    def test_disabled_ancestors_hide_seven_enabled_renderers(self):
        inherited = [r for r in self.plan['renderers'] if r['owner_active'] and not r['hierarchy_active']]
        self.assertEqual(len(inherited), 7)
        self.assertTrue(all(not source.component_enabled(r) for r in inherited))
        self.assertEqual(sum(source.component_enabled(r) for r in self.plan['renderers']), 69)
        bad = copy.deepcopy(self.plan)
        bad['renderers'][0].pop('hierarchy_active')
        bad['digest'] = source.digest({k: v for k, v in bad.items() if k != 'digest'})
        with self.assertRaisesRegex(source.SourceError, 'hierarchy activation'):
            source.validate_plan(bad)

    def test_same_da_identity_keeps_raw_bump_and_explicit_color_decode(self):
        material = next(m for m in self.plan['materials'].values() if m['name'] == 'Stage_KevinbossP1_Fan_PropsA_01_1003')
        key = material['textures']['_MainTex']
        self.assertEqual(key, material['textures']['_BumpMap'])
        cfg = self.settings['textures'][key]
        self.assertFalse(cfg['srgb'])
        self.assertEqual(cfg['color_decode_slots'], ['_MainTex'])
        graph = self.settings['rendering']['materials']['/'.join(material['identity'])]
        self.assertIn({'from': 'UEColorDecode_MainTex', 'output': '', 'to': 'UEBaseColor', 'input': 'Main'}, graph['edges'])
        self.assertIn({'from': 'Texture_BumpMap', 'output': 'RGB', 'to': 'UENormal', 'input': 'Normal'}, graph['edges'])
        bad = copy.deepcopy(self.settings)
        bad['textures'][key].pop('color_decode_slots')
        with self.assertRaisesRegex(source.SourceError, 'mixed source color/BumpMap'):
            restore.validate_settings(self.plan, bad, 'textures')

    def test_readonly_geometry_checkpoint_never_claims_a_map_save(self):
        u = mock.Mock()
        u.EditorLoadingAndSavingUtils.get_dirty_map_packages.return_value = []
        u.EditorLoadingAndSavingUtils.get_dirty_content_packages.return_value = []
        baseline = {'actors': {'original_actor': {'preserved': True}}}
        result = {'phase': 'geometry_baseline_passed', 'plan_digest': self.plan['digest'],
                  'map_saved': False, 'saved_assets': [], 'created_actors': []}
        with mock.patch.object(restore, 'map_actors', return_value=(None, {'original_actor': None}, {'original_actor': None})), \
             mock.patch.object(restore, 'map_geometry_state', return_value=baseline):
            restore.read_geometry_baseline(u, self.plan, result)
        self.assertFalse(result['map_saved'])
        u.EditorAssetLibrary.save_loaded_asset.assert_not_called()
        u.get_editor_subsystem.assert_not_called()
        with mock.patch.object(source, 'read_json', return_value=result):
            self.assertEqual(restore.accepted_map_baseline(self.plan, self.settings, 'unused', result['map_file'], False), (baseline, []))
            stale = dict(result['map_file'], sha256='different-current-map')
            with self.assertRaisesRegex(source.SourceError, 'failed/stale/foreign'):
                restore.accepted_map_baseline(self.plan, self.settings, 'unused', stale, False)
            result['phase'] = 'lighting_passed'
            with self.assertRaisesRegex(source.SourceError, 'failed/stale/foreign'):
                restore.accepted_map_baseline(self.plan, self.settings, 'unused', result['map_file'], False)

    def test_normal_autodetection_original_failure_and_explicit_color_commit(self):
        row = next(t for t in self.plan['textures'].values() if t['package'].endswith('_Crystal_DA'))
        key = '/'.join(row['identity'])
        cfg = self.settings['textures'][key]
        self.assertTrue(cfg['srgb'])
        default, normal = SimpleNamespace(name='TC_DEFAULT'), SimpleNamespace(name='TC_Normalmap')

        class AutoNormalTexture:
            def __init__(self):
                self.props = {'compression_settings': normal, 'srgb': False,
                              'asset_import_data': SimpleNamespace(extract_filenames=lambda: [row['file']['path']])}
            def set_editor_property(self, name, value):
                self.props[name] = value
                # UE Texture.cpp 的真实限制：Normal 压缩期间提交 sRGB 会被清零。
                if self.props['compression_settings'] is normal:
                    self.props['srgb'] = False
            def get_editor_property(self, name):return self.props[name]
            def get_path_name(self):return row['package']+'.'+row['package'].rsplit('/', 1)[1]
            def get_class(self):return SimpleNamespace(get_name=lambda: 'Texture2D')

        original = AutoNormalTexture()
        original.set_editor_property('srgb', True)
        original.set_editor_property('compression_settings', default)
        self.assertFalse(original.get_editor_property('srgb'))
        current = AutoNormalTexture()
        task = mock.Mock()
        task.get_editor_property.return_value = [current.get_path_name()]
        u = mock.Mock()
        u.AssetImportTask.return_value = task
        u.EditorAssetLibrary.load_asset.return_value = current
        u.EditorAssetLibrary.find_asset_data.return_value.get_tag_value.return_value = '512x512'
        u.TextureCompressionSettings = SimpleNamespace(TC_DEFAULT=default)
        u.TextureFilter = SimpleNamespace(TF_BILINEAR=SimpleNamespace(name='TF_BILINEAR'))
        u.TextureMipGenSettings = SimpleNamespace(TMGS_FROM_TEXTURE_GROUP=SimpleNamespace(name='TMGS_FROM_TEXTURE_GROUP'))
        u.TextureAddress = SimpleNamespace(TA_WRAP=SimpleNamespace(name='TA_WRAP'))
        plan = dict(self.plan, textures={key: row})
        with mock.patch.object(restore, 'absent_targets'), mock.patch.object(restore, 'stamp_save') as save:
            restore.create_textures(u, plan, self.settings, {})
        self.assertTrue(current.get_editor_property('srgb'))
        self.assertIs(current.get_editor_property('compression_settings'), default)
        save.assert_called_once_with(u, current, plan, row['identity'], {})

    def test_texture_resume_requires_exact_failure_and_rejects_unrecorded_existing(self):
        previous = source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P1_Textures_Create_20261009.json')
        settings = source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P1_UE_Equivalent_Settings_20261009.json')
        recorded = restore.texture_resume_packages(self.plan, settings, previous, 'textures')
        self.assertEqual(len(recorded), 60)
        for field, value in [('phase', 'textures_passed'), ('settings_digest', 'old-settings'),
                             ('plan_digest', 'foreign-plan'), ('mode', 'surface_textures')]:
            bad = dict(previous, **{field: value})
            with self.assertRaisesRegex(source.SourceError, 'plan/settings/phase'):
                restore.texture_resume_packages(self.plan, settings, bad, 'textures')
        for packages in [recorded + [recorded[0]], recorded + ['/Game/Foreign/Texture']]:
            with self.assertRaisesRegex(source.SourceError, 'invalid/duplicate packages'):
                restore.texture_resume_packages(self.plan, settings, dict(previous, saved_assets=packages), 'textures')
        remaining = set(restore.targets(self.plan, 'textures')) - set(recorded)
        self.assertEqual(len(remaining), 15)
        u = mock.Mock()
        u.EditorAssetLibrary.does_asset_exist.side_effect = lambda package: package in remaining
        with mock.patch.object(Path, 'exists', return_value=False):
            with self.assertRaisesRegex(source.SourceError, 'already exists'):
                restore.absent_targets(u, self.plan, 'textures', recorded)


class StagePawnSupportContracts(unittest.TestCase):
    def test_support_resume_rejects_foreign_package_or_map_commit_and_changed_bytes(self):
        spec = {'package': '/Game/Support'}
        before = {'sha256': 'map'}
        preflight = {'plan_digest': 'plan', 'settings_digest': 'settings', 'source_scene_baseline': {},
                     'protected_packages': {}, 'native_source_topology': {'vertices': {}, 'triangles': {}}}
        package = {'sha256': 'asset'}
        failed = dict(preflight, mode='pawn_support', phase='failed', failure_phase='pawn_support_asset',
                      map_saved=False, cleanup_errors=[], saved_assets=[spec['package']],
                      support_spec=spec, map_before=before, support_package=package)
        path = source.PROJECT/'Saved/SupportFailure.json'
        with mock.patch.object(source, 'read_json', return_value=failed), \
             mock.patch.object(source, 'evidence', return_value=package):
            self.assertEqual(restore.support_asset_resume(spec, preflight, before, path)[0], failed)
        repaired = dict(failed, mode='pawn_support_asset_repair', phase='pawn_support_asset_repair_passed')
        with mock.patch.object(source, 'read_json', return_value=repaired), \
             mock.patch.object(source, 'evidence', return_value=package):
            self.assertEqual(restore.support_asset_resume(spec, preflight, before, path)[0], repaired)
        for key, value in (('phase', 'pawn_support_passed'), ('map_save_attempted', True),
                           ('cleanup_errors', ['Actor cleanup failed']), ('saved_assets', ['/Game/Foreign']),
                           ('support_spec', {'package': '/Game/Foreign'}), ('map_before', {'sha256': 'changed'}),
                           ('native_source_topology', {'triangles': {'0': [0, 1, 2]}})):
            invalid = dict(failed, **{key: value})
            with mock.patch.object(source, 'read_json', return_value=invalid), \
                 mock.patch.object(source, 'evidence', return_value=package):
                with self.assertRaisesRegex(source.SourceError, 'checkpoint'):
                    restore.support_asset_resume(spec, preflight, before, path)
        with mock.patch.object(source, 'read_json', return_value=failed), \
             mock.patch.object(source, 'evidence', return_value={'sha256': 'tampered'}):
            with self.assertRaisesRegex(source.SourceError, 'saved package changed'):
                restore.support_asset_resume(spec, preflight, before, path)

    def test_p2_composition_keeps_three_original_instances_and_excludes_camera(self):
        plan = source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P1_Source_Plan_20261009.json')
        before = copy.deepcopy(plan)
        manifest = 'F:/AnimeStudio/_work/bh3_stage_candidates_20261009/P2CollisionReference/contract_input_manifest.json'
        spec = source.pawn_support_spec(plan, manifest)
        self.assertEqual(plan, before)
        self.assertEqual((len(spec['vertices']), len(spec['triangles'])), (242, 160))
        self.assertEqual([r['role'] for r in spec['source_instances']], ['floor', 'wall', 'top'])
        self.assertEqual(spec['native_triangles'], [[f[0], f[2], f[1]] for f in spec['triangles']])
        self.assertNotEqual(spec['native_triangles'], spec['triangles'])
        self.assertEqual([r['sourceGameObjectLayer'] for r in spec['excluded_camera_colliders']], [25, 25])
        self.assertEqual(spec['source_model'], '1580595554368')
        self.assertFalse(spec['runtime_world_registration_verified'])
        self.assertFalse(spec['source_cooking_verified'])
        world = [source.point(source.matrix(spec['source_world_pose']), p) for p in spec['vertices']]
        for face in spec['triangles'][:40]:
            a, b, c = [world[i] for i in face]
            self.assertGreater((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]), 0)
        for face in spec['triangles'][-40:]:
            a, b, c = [world[i] for i in face]
            self.assertLess((b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0]), 0)
        self.assertAlmostEqual(world[0][2], -.28885922*100, places=4)
        with self.assertRaisesRegex(source.SourceError, 'manifest is missing/foreign'):
            source.pawn_support_spec(plan, Path(manifest).with_name('p2_collision_reference.json'))

    def test_p2_floor_matches_actual_source_triangles_and_old_registration_stays_wrong(self):
        plan = source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P1_Source_Plan_20261009.json')
        spec = source.pawn_support_spec(plan,
            'F:/AnimeStudio/_work/bh3_stage_candidates_20261009/P2CollisionReference/contract_input_manifest.json')
        triangles = []
        for row in spec['visual_surfaces']:
            vertices, faces = source.parse_support_obj(Path(row['source_obj']['path']).read_text(encoding='utf-8-sig'),
                '# Original Unity coordinates / units / winding; no axis conversion.')
            world = [source.point(source.matrix(plan['geometry_actors'][row['model']]['world_transform']), p) for p in vertices]
            triangles.extend([[world[i] for i in face] for face in faces])
        floor = [source.point(source.matrix(spec['source_world_pose']), p) for p in spec['vertices'][:41]]
        distance = [min(source.point_triangle_distance(p, *face) for face in triangles) for p in floor]
        self.assertLess(max(distance), .1)
        old = source.pawn_support_spec(plan)
        wrong = source.point(source.matrix(old['source_world_pose']), old['vertices'][0])
        self.assertGreater(min(source.point_triangle_distance(wrong, *face) for face in triangles), 28.)
        self.assertAlmostEqual(source.point_triangle_distance([.2, .2, 1.5], [0, 0, 0], [1, 0, 0], [0, 1, 0]), 1.5)

    def test_spawn_query_requires_exact_owned_walkable_nonpenetrating_floor(self):
        capsule = {'radius_cm': 34., 'half_height_cm': 88.}
        support = {'component': 'owned.PawnQuery'}
        hit = {'component': support['component'], 'initial_penetration': False,
               'penetration_depth_cm': 0., 'native_cmc_is_walkable': True, 'location_cm': [8., 9., 14.]}
        bounds = {'min': [-50., -50., -500.], 'max': [50., 50., 900.]}
        with mock.patch.object(restore, 'support_sweep', side_effect=[{'hit': hit}, {'hit': None}]):
            candidate = restore.support_spawn_candidate(None, None, support, capsule, None, [8., 9.], bounds)
        self.assertEqual(candidate['location_cm'], [8., 9., 17.4])
        self.assertFalse(candidate['actual_spawn_verified'])
        invalid = [None]
        for key, value in (('component', 'original.Camera'), ('initial_penetration', True),
                           ('penetration_depth_cm', .1), ('native_cmc_is_walkable', False)):
            wrong = dict(hit)
            wrong[key] = value
            invalid.append(wrong)
        for wrong in invalid:
            with mock.patch.object(restore, 'support_sweep', return_value={'hit': wrong}):
                with self.assertRaisesRegex(source.SourceError, 'exact walkable owned support'):
                    restore.support_spawn_candidate(None, None, support, capsule, None, [8., 9.], bounds)
        with mock.patch.object(restore, 'support_sweep', side_effect=[{'hit': hit}, {'hit': dict(hit)}]):
            with self.assertRaisesRegex(source.SourceError, 'no clearance'):
                restore.support_spawn_candidate(None, None, support, capsule, None, [8., 9.], bounds)

    def test_selected_sources_keep_environment_and_camera_policy(self):
        for stage, filename, model, counts in (
            ('P1', 'P1_Source_Plan_20261009.json', '1580554081600', (41, 40)),
            ('P3', 'P3_Source_Plan_20261008_233000.json', '1934927152128', (201, 120))):
            plan = source.read_json(source.PROJECT/'Saved/BH3StageEnvironment'/filename)
            before = copy.deepcopy(plan)
            spec = source.pawn_support_spec(plan)
            self.assertEqual(plan, before)
            self.assertEqual(spec['source_model'], model)
            self.assertEqual((spec['vertices_expected'], spec['triangles_expected']), counts)
            self.assertEqual(spec['package'], plan['asset_root']+'/StaticMeshes/SM_KevinBoss'+stage+'_PawnSupport')
            self.assertEqual(spec['camera_policy'], 'preserve_original')
            self.assertFalse(spec['source_runtime_activation_restored'])
            self.assertFalse(spec['source_cooking_verified'])
            bad = copy.deepcopy(plan)
            bad['colliders'] = [c for c in bad['colliders'] if c['model'] != model]
            with self.assertRaisesRegex(source.SourceError, 'exact source collider'):
                source.pawn_support_spec(bad)

    def test_original_p1_obj_frame_retains_upward_floor_and_native_tail(self):
        plan = source.read_json(source.PROJECT/'Saved/BH3StageEnvironment/P1_Source_Plan_20261009.json')
        spec = source.pawn_support_spec(plan)
        self.assertEqual(spec['unparsed_tail'], 'f98b470000803f00000000')
        self.assertFalse(spec['native_mesh_layout_fully_parsed'])
        world = [source.point(source.matrix(spec['source_world_pose']), p) for p in spec['vertices']]
        for face in spec['triangles']:
            a, b, c = [world[i] for i in face]
            ab, ac = [[p[i]-a[i] for i in range(3)] for p in (b, c)]
            self.assertGreater(ab[0]*ac[1]-ab[1]*ac[0], 0)
        self.assertLess(max(p[2] for p in world)-min(p[2] for p in world), .001)
        self.assertGreater(max(p[0] for p in world)-min(p[0] for p in world), 8200)

    def test_obj_requires_source_frame_and_rejects_invalid_collision_geometry(self):
        header = '# Original Unity local coordinates and index winding; no axis/unit conversion.\n'
        geometry = 'v 0 0 0\nv 1 0 0\nv 0 1 0\nf 1 2 3\n'
        vertices, faces = source.parse_support_obj(header+geometry)
        self.assertEqual(vertices, [[0, 0, 0], [-100, 0, 0], [0, -100, 0]])
        self.assertEqual(faces, [[0, 1, 2]])
        for invalid in ('', geometry, header+geometry.replace('f 1 2 3', 'f 1 2 4'),
                        header+geometry.replace('v 0 1 0', 'v 2 0 0'),
                        header+geometry.replace('v 0 1 0', 'v nan 1 0'),
                        header+geometry+'usemtl invented\n'):
            with self.assertRaises(source.SourceError):
                source.parse_support_obj(invalid)


if __name__=='__main__':unittest.main(verbosity=2)
