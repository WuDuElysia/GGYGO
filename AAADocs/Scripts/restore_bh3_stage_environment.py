"""@file Controlled native UE asset creation and Stage-owned map application.

Offline: inspect --plan <Saved plan> --settings <machine input>
Full isolated Editor: preflight|textures|lighting|lighting_readback|materials|
assets_readback|map|readback. Existing affine/geometry modes retain their contracts.
Map writes require --map-sha256 and --map-backup of the current Saved map copy.
lighting consumes --geometry-result; map can consume that result directly or an
accepted --environment-result from lighting. Cold reads consume their apply result.

Settings contain explicit texture interpretation and material expression graphs.
No missing recipe, source, sampler or rendering policy gets a replacement.
Texture creation is an independent saved phase. The environment map phase starts only after
all required assets and the source-affine geometry are ready. Collision policy
is separate from the environment checkpoint. pawn_support_preflight reads the
selected original floor/Collision and player configuration without saving or PIE.
map_geometry requires --map-backup of the exact original map in Saved.
map_geometry_readback consumes that phase's --geometry-result in a fresh Editor.
geometry_baseline reads an already exact saved scene without a redundant map save;
its successful result can be consumed by lighting/map when no affine correction is needed.
"""

import argparse
import copy
import json
from pathlib import Path
import math
import re
import runpy
import sys
import struct
import time

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
import bh3_stage_environment_source as source


def targets(plan, mode):
    if mode in ('textures','probe_textures','surface_textures'):
        probes={r['texture'] for r in plan['probes']}
        return {v['package']: v['class'] for key,v in plan['textures'].items()
                if mode=='textures' or (key in probes)==(mode=='probe_textures')}
    if mode == 'materials':
        return {v['package']: 'Material' for v in plan['materials'].values()}
    if mode == 'affine':
        return {v['package']: 'StaticMesh' for v in plan['affine_meshes']}
    return {}


def validate_settings(plan, settings, mode):
    source.require(settings.get('plan_digest') == plan['digest'], 'settings belong to another source plan')
    if 'preserved_lighting' in settings or 'lighting_calibration' in settings:
        source.lighting_generation_digest(plan,settings)
    if mode in ('textures','probe_textures','surface_textures','surface_textures_readback','probe_textures_readback', 'preflight', 'map', 'readback', 'assets_readback', 'lighting', 'lighting_readback'):
        configs = settings.get('textures', {})
        source.require(set(configs) == set(plan['textures']), 'all source texture interpretations must be explicit')
        roles = {key: set() for key in plan['textures']}
        for material in plan['materials'].values():
            for slot, key in material['textures'].items():
                roles[key].add(slot)
        for key, row in plan['textures'].items():
            cfg = configs[key]
            source.require(type(cfg.get('srgb')) is bool and cfg.get('interpretation_authority'),
                           'texture color interpretation is not evidenced: '+key)
            mixed = bool(roles[key] & source.DATA_TEXTURE_SLOTS and roles[key] - source.DATA_TEXTURE_SLOTS)
            if mixed:
                source.require(plan['stage'] == 'P1' and roles[key] == {'_MainTex', '_BumpMap'}
                               and not cfg['srgb'] and cfg.get('color_decode_slots') == ['_MainTex'],
                               'mixed source color/BumpMap sampling policy is absent: ' + key)
            else:
                source.require(not cfg.get('color_decode_slots'), 'unexpected explicit texture color decode: ' + key)
            native = row['native_settings']
            if native is None:
                proof = cfg.get('native_metadata')
                source.require(proof is not None and source.evidence(proof['path']) == proof,
                               '2D texture native metadata is absent/changed: '+key)
                document = source.read_json(proof['path'])
                source.require(source.identity(document['source']) == tuple(row['identity']),
                               'texture native metadata identifies another object: '+key)
                native = document['fields']
            source.require(native['m_Width'] > 0 and native['m_Height'] > 0, 'invalid native texture dimensions')
            sampler = native['m_TextureSettings']
            source.require(cfg['filter'] == {0:'TF_NEAREST', 1:'TF_BILINEAR', 2:'TF_TRILINEAR'}[sampler['m_FilterMode']],
                           'texture filter differs from native source: '+key)
            if row['class'] == 'Texture2D':
                wrap = {0:'TA_WRAP', 1:'TA_CLAMP', 2:'TA_MIRROR'}
                source.require(cfg['address_x'] == wrap[sampler['m_WrapU']] and cfg['address_y'] == wrap[sampler['m_WrapV']],
                               'texture wrap differs from source or unsupported MirrorOnce: '+key)
            source.require(cfg['compression'] in ('TC_DEFAULT', 'TC_VECTOR_DISPLACEMENTMAP', 'TC_HDR'),
                           'raw native RGB sampling cannot silently use a normal-map reconstruction codec')
            source.require(cfg.get('mip_gen_settings') in ('TMGS_FROM_TEXTURE_GROUP', 'TMGS_LEAVE_EXISTING_MIPS'),
                           'texture mip production policy is not explicit: '+key)
            if row['class'] == 'TextureCube' and row['layout']['formatName'] == 'BC6H_UF16':
                source.require(cfg['compression'] == 'TC_HDR' and not cfg['srgb'], 'HDR cube must retain linear HDR data')
            source.cube_import_file(row,cfg)
    if mode in ('materials', 'preflight', 'map', 'readback', 'assets_readback'):
        rendering = settings.get('rendering', {})
        source.require(rendering.get('purpose') == 'ue_equivalent_stage',
                       'Stage UE adaptation is not selected; original runtime providers remain unimplemented')
        graphs = rendering.get('materials', {})
        source.require(set(graphs) == set(plan['materials']), 'material graphs do not cover exact source identities')
        for key, material in plan['materials'].items():
            graph = graphs[key]
            shader = plan['shaders'][material['shader']]
            source.require(graph.get('source_material') == material['identity']
                           and graph.get('source_shader_sha256') == shader['fields']['sha256'],
                           'material graph source provenance differs: '+key)
            source.require(graph.get('nodes') and graph.get('outputs') and graph.get('differences') is not None,
                           'material graph or explicit rendering differences are absent: '+key)
            source.require(graph['differences'], 'UE adaptation must identify its actual source differences')
            validate_graph(material, graph)
    if mode in ('map', 'preflight', 'readback', 'lighting', 'lighting_readback'):
        light = settings.get('lighting', {})
        source.require(light.get('purpose') == 'source_numeric_ue_calibration'
                       and light.get('color_space') in ('linear', 'srgb'),
                       'Unity light color/units require an explicit calibration policy')
        for key in ('directional_lux_scale', 'local_intensity_scale', 'local_falloff_exponent',
                    'indirect_lighting_intensity', 'volumetric_scattering_intensity', 'spot_inner_cone_ratio'):
            source.require(type(light.get(key)) in (int, float) and math.isfinite(light[key])
                           and light[key] >= 0, 'invalid light calibration: '+key)
        source.require(light['directional_lux_scale'] > 0 and light['local_intensity_scale'] > 0
                       and light['local_falloff_exponent'] > 0 and 0 <= light['spot_inner_cone_ratio'] <= 1
                       and light.get('differences'), 'light calibration/differences are incomplete')
        source.require(light.get('cube_orientation') == 'source_faces_unverified',
                       'this tool retains source DDS faces; it cannot claim a verified remap')
    return settings


def validate_graph(material, graph):
    """Only expressions with explicit inputs/properties are created, with no defaults inferred."""
    ids = set()
    for node in graph['nodes']:
        source.require(node['id'] not in ids and node['class'].startswith('MaterialExpression'), 'invalid/duplicate graph node')
        ids.add(node['id'])
        if 'source_texture' in node:
            source.require(node['source_texture'] in material['textures'], 'graph texture is not a native material slot')
        if 'source_scalar' in node:
            source.require(node['source_scalar'] in material['fields']['m_SavedProperties']['m_Floats'], 'missing native scalar')
        if 'source_vector' in node:
            source.require(node['source_vector'] in material['fields']['m_SavedProperties']['m_Colors'], 'missing native vector')
    adjacency = {i: [] for i in ids}
    connected = set()
    for edge in graph.get('edges', []):
        source.require(edge['from'] in ids and edge['to'] in ids, 'material graph edge is dangling')
        destination = (edge['to'], edge.get('input'))
        source.require(destination not in connected, 'two edges write one material input')
        connected.add(destination)
        adjacency[edge['from']].append(edge['to'])
    for node in graph['nodes']:
        if node['class'] == 'MaterialExpressionCustom':
            pins = node.get('custom_inputs', [])
            source.require(pins and len(pins) == len(set(pins)) and node.get('properties', {}).get('code'),
                           'custom expression inputs/code are incomplete')
            source.require({pin for name, pin in connected if name == node['id']} == set(pins),
                           'custom expression has missing/unplanned inputs: '+node['id'])
    properties = [out['property'] for out in graph['outputs']]
    source.require(len(properties) == len(set(properties)), 'two graph nodes write one material output')
    for output in graph['outputs']:
        source.require(output['node'] in ids and output['property'].startswith('MP_'), 'invalid material output')
    visiting, done = set(), set()
    def visit(node):
        source.require(node not in visiting, 'material expression graph is cyclic')
        if node in done:
            return
        visiting.add(node)
        for child in adjacency[node]:
            visit(child)
        visiting.remove(node)
        done.add(node)
    for node in ids:
        visit(node)
    source.require({n['source_texture'] for n in graph['nodes'] if 'source_texture' in n}==set(material['textures']),
                   'material graph does not bind every non-null native texture slot')


def verify_compile_result(errors):
    source.require(errors is not None and not isinstance(errors,(str,bytes,dict,bool))
                   and hasattr(errors,'__iter__'), 'native material compile API did not return diagnostics')
    diagnostics=list(errors)
    source.require(all(isinstance(e,str) for e in diagnostics), 'native material diagnostics have another schema')
    source.require(not diagnostics, 'native material compilation failed: '+str(diagnostics))


def package_file(package, extension='.uasset'):
    source.require(package.startswith('/Game/'), 'foreign package')
    return source.PROJECT/'Content'/(package[6:]+extension)


def absent_targets(u, plan, mode, resumed=()):
    source.require(set(resumed)<=set(targets(plan,mode)),'resume escapes the phase targets')
    for package in targets(plan, mode):
        if package in resumed:continue
        source.require(package.startswith(plan['asset_root']+'/'), 'target escapes approved Stage namespace')
        source.require(not package_file(package).exists() and not u.EditorAssetLibrary.does_asset_exist(package),
                       'create-only destination already exists: '+package)


def exact_asset(u, package, class_name, owned=False, plan=None):
    obj = u.EditorAssetLibrary.load_asset(package)
    source.require(obj is not None and obj.get_path_name() == package+'.'+package.rsplit('/', 1)[1]
                   and obj.get_class().get_name() == class_name, 'asset path/class differs: '+package)
    if owned:
        source.require(u.EditorAssetLibrary.get_metadata_tag(obj, 'BH3.EnvironmentOwner') == source.OWNER
                       and u.EditorAssetLibrary.get_metadata_tag(obj, 'BH3.EnvironmentPlan') == plan['digest'],
                       'environment asset belongs to another source plan: '+package)
        rows=list(plan['textures'].values())+list(plan['materials'].values())
        match=[row for row in rows if row['package']==package]
        if match:
            source.require(len(match)==1 and u.EditorAssetLibrary.get_metadata_tag(obj,'BH3.SourceIdentity')=='/'.join(match[0]['identity']),
                           'saved asset source identity differs: '+package)
    return obj


def stamp_save(u, obj, plan, ident, result):
    package = obj.get_path_name().split('.')[0]
    allowed={**targets(plan,'textures'),**targets(plan,'materials'),**targets(plan,'affine')}
    source.require(package in allowed and obj.get_class().get_name()==allowed[package]
                   and obj.get_path_name()==package+'.'+package.rsplit('/',1)[1],
                   'refusing to save foreign/unplanned object')
    u.EditorAssetLibrary.set_metadata_tag(obj, 'BH3.EnvironmentOwner', source.OWNER)
    u.EditorAssetLibrary.set_metadata_tag(obj, 'BH3.EnvironmentPlan', plan['digest'])
    u.EditorAssetLibrary.set_metadata_tag(obj, 'BH3.SourceIdentity', '/'.join(ident))
    source.require(u.EditorAssetLibrary.save_loaded_asset(obj, only_if_is_dirty=False), 'exact asset save failed: '+package)
    source.require(package_file(package).is_file() and obj.get_outer() not in
                   u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'saved asset missing/dirty: '+package)
    result['saved_assets'].append(package)


def texture_resume_packages(plan, settings, previous, mode):
    """仅已记录的同计划、同配置、同阶段失败保存可授权只读续接。"""
    source.require(mode in ('textures', 'probe_textures', 'surface_textures')
                   and previous.get('mode') == mode and previous.get('phase') == 'failed'
                   and previous.get('failure_phase') == mode and previous.get('plan_digest') == plan['digest']
                   and previous.get('settings_digest') == source.digest(settings)
                   and previous.get('map_saved') is False and previous.get('created_actors') == [],
                   'texture resume is not a failed asset-only result from this plan/settings/phase')
    saved, resumed = previous.get('saved_assets'), previous.get('resumed_assets', [])
    source.require(type(saved) is list and type(resumed) is list, 'texture resume package records are invalid')
    packages = resumed + saved
    source.require(packages and all(type(p) is str for p in packages)
                   and len(packages) == len(set(packages)) and set(packages) <= set(targets(plan, mode)),
                   'texture resume lists invalid/duplicate packages')
    return packages


def create_textures(u, plan, settings, result, mode='textures', previous_result=None):
    resumed = []
    if previous_result is not None:
        previous_path = Path(previous_result).resolve()
        source.require(previous_path.is_relative_to(source.PROJECT/'Saved'), 'texture resume result is outside project Saved')
        resumed = texture_resume_packages(plan, settings, source.read_json(previous_path), mode)
        for key, row in plan['textures'].items():
            if row['package'] not in resumed:
                continue
            obj = exact_asset(u, row['package'], row['class'], True, plan)
            cfg = settings['textures'][key]
            source.require(u.EditorAssetLibrary.get_metadata_tag(obj, 'BH3.TextureInterpretation') == source.digest(cfg),
                           'resumed texture interpretation differs: ' + row['package'])
            verify_texture(u, obj, row, cfg)
        source.require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                       and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
                       'texture resume unexpectedly dirtied existing packages')
        result['resumed_assets'] = resumed
        result['texture_resume_result'] = source.evidence(previous_path)
    absent_targets(u, plan, mode, resumed)
    selected=targets(plan,mode)
    for key, row in plan['textures'].items():
        package = row['package']
        if package not in selected or package in resumed:continue
        cfg = settings['textures'][key]
        import_file=cfg['decoded_cube']['file'] if 'decoded_cube' in cfg else row['file']
        task = u.AssetImportTask()
        for name, value in {'filename':import_file['path'], 'destination_path':package.rsplit('/',1)[0],
                            'destination_name':package.rsplit('/',1)[1], 'automated':True,
                            'replace_existing':False, 'save':False, 'factory':u.TextureFactory()}.items():
            task.set_editor_property(name, value)
        u.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        paths = list(task.get_editor_property('imported_object_paths'))
        source.require(paths == [package+'.'+package.rsplit('/',1)[1]],
                       'texture import failed/wrong objects: '+package+' source='+import_file['path']+' returned='+repr(paths))
        obj = exact_asset(u, package, row['class'])
        # 法线自动识别期间 UE 会清零 sRGB；先退出其压缩模式，再提交显式颜色策略。
        obj.set_editor_property('compression_settings', getattr(u.TextureCompressionSettings, cfg['compression']))
        obj.set_editor_property('srgb', cfg['srgb'])
        obj.set_editor_property('filter', getattr(u.TextureFilter, cfg['filter']))
        obj.set_editor_property('mip_gen_settings', getattr(u.TextureMipGenSettings, cfg['mip_gen_settings']))
        if row['class'] == 'Texture2D':
            obj.set_editor_property('address_x', getattr(u.TextureAddress, cfg['address_x']))
            obj.set_editor_property('address_y', getattr(u.TextureAddress, cfg['address_y']))
        verify_texture(u, obj, row, cfg)
        u.EditorAssetLibrary.set_metadata_tag(obj, 'BH3.TextureInterpretation', source.digest(cfg))
        stamp_save(u, obj, plan, row['identity'], result)


def material_resume_packages(plan,previous):
    source.require(previous.get('mode')=='materials' and previous.get('phase')=='failed'
                   and previous.get('failure_phase')=='materials' and previous.get('plan_digest')==plan['digest']
                   and previous.get('map_saved') is False and previous.get('created_actors')==[],
                   'material resume is not a failed asset-only result from this plan')
    packages=previous.get('resumed_assets',[])+previous.get('saved_assets',[])
    source.require(packages and len(packages)==len(set(packages))
                   and set(packages)<=set(targets(plan,'materials')),'material resume lists invalid/duplicate packages')
    return packages


def create_materials(u, plan, settings, result, previous_result=None):
    resumed=[]
    if previous_result is not None:
        previous_path=Path(previous_result).resolve()
        source.require(previous_path.is_relative_to(source.PROJECT/'Saved'),'material resume result is outside project Saved')
        resumed=material_resume_packages(plan,source.read_json(previous_path))
        for key,row in plan['materials'].items():
            if row['package'] in resumed:
                verify_material(u,exact_asset(u,row['package'],'Material',True,plan),plan,row,settings['rendering']['materials'][key])
        source.require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'material resume unexpectedly dirtied existing assets')
        result['resumed_assets']=resumed
        result['material_resume_result']=source.evidence(previous_path)
    absent_targets(u, plan, 'materials',resumed)
    verify_assets(u,plan,settings,False)
    textures = {k:exact_asset(u, v['package'], v['class'], True, plan) for k,v in plan['textures'].items()}
    for key, row in plan['materials'].items():
        graph = settings['rendering']['materials'][key]
        package = row['package']
        if package in resumed:continue
        mat = u.AssetToolsHelpers.get_asset_tools().create_asset(package.rsplit('/',1)[1],
                package.rsplit('/',1)[0], u.Material, u.MaterialFactoryNew())
        source.require(mat is not None, 'native material factory returned null: '+package)
        source.require(mat==exact_asset(u,package,'Material'), 'material factory returned another UObject')
        for name, enum_class in [('blend_mode',u.BlendMode), ('shading_model',u.MaterialShadingModel)]:
            mat.set_editor_property(name, getattr(enum_class, graph[name]))
        mat.set_editor_property('two_sided', graph['two_sided'])
        if graph['blend_mode'] == 'BLEND_MASKED':
            mat.set_editor_property('opacity_mask_clip_value', graph['opacity_mask_clip_value'])
        nodes = {}
        for number, spec in enumerate(graph['nodes']):
            node = u.MaterialEditingLibrary.create_material_expression(mat, getattr(u,spec['class']), -600+number*120, number*100)
            source.require(node is not None, 'material expression creation failed')
            node.set_editor_property('desc', 'BH3.Stage.Node:'+spec['id'])
            for prop, value in spec.get('properties',{}).items():
                node.set_editor_property(prop,native_value(u,value))
            if 'custom_inputs' in spec:
                pins = []
                for name in spec['custom_inputs']:
                    pin = u.CustomInput()
                    pin.set_editor_property('input_name',name)
                    pins.append(pin)
                node.set_editor_property('inputs',pins)
            props = row['fields']['m_SavedProperties']
            if 'source_texture' in spec:
                node.set_editor_property('texture', textures[row['textures'][spec['source_texture']]])
            if 'source_scalar' in spec:
                node.set_editor_property('default_value', props['m_Floats'][spec['source_scalar']])
            if 'source_vector' in spec:
                c = props['m_Colors'][spec['source_vector']]
                node.set_editor_property('default_value', u.LinearColor(c['r'],c['g'],c['b'],c['a']))
            nodes[spec['id']] = node
        for edge in graph.get('edges',[]):
            source.require(u.MaterialEditingLibrary.connect_material_expressions(nodes[edge['from']], edge['output'],
                           nodes[edge['to']],edge['input']), 'native expression connection failed: '+package+' '+str(edge))
        for output in graph['outputs']:
            source.require(u.MaterialEditingLibrary.connect_material_property(nodes[output['node']],output['output'],
                           getattr(u.MaterialProperty,output['property'])), 'native material output connection failed')
        errors = u.MaterialEditingLibrary.recompile_material(mat)
        verify_compile_result(errors)
        verify_material(u,mat,plan,row,graph,False)
        u.EditorAssetLibrary.set_metadata_tag(mat,'BH3.RenderingPurpose',settings['rendering']['purpose'])
        u.EditorAssetLibrary.set_metadata_tag(mat,'BH3.MaterialRecipe',source.digest(graph))
        u.EditorAssetLibrary.set_metadata_tag(mat,'BH3.UEEquivalentDifferences',json.dumps(graph['differences'],ensure_ascii=False))
        stamp_save(u,mat,plan,row['identity'],result)


def native_value(u, value):
    if isinstance(value,dict):
        if set(value)=={'linear_color'}:
            return u.LinearColor(*value['linear_color'])
        source.require(set(value)=={'enum','value'},'unknown typed material property')
        return getattr(getattr(u,value['enum']),value['value'])
    return value


def numeric_equal(actual, expected, context):
    source.require(math.isfinite(actual) and math.isfinite(expected)
                   and math.isclose(actual,expected,rel_tol=2e-6,abs_tol=1e-5),
                   'native numeric value differs: '+context+f' ({actual} != {expected})')


def verify_texture(u, obj, row, cfg):
    properties={'srgb':'srgb','compression_settings':'compression','filter':'filter','mip_gen_settings':'mip_gen_settings'}
    if row['class']=='Texture2D':properties.update(address_x='address_x',address_y='address_y')
    for prop,key in properties.items():
        actual=obj.get_editor_property(prop)
        source.require(actual==cfg[key] if type(cfg[key]) is bool else actual.name==cfg[key],
                       'texture property differs: '+row['package']+'/'+prop)
    if row['class']=='Texture2D':
        asset_data=u.EditorAssetLibrary.find_asset_data(obj.get_path_name())
        observed=asset_data.get_tag_value('Dimensions')
        expected=str(row['native_settings']['m_Width'])+'x'+str(row['native_settings']['m_Height'])
        source.require(observed==expected,'texture Source dimensions differ: '+row['package']
                       +' expected='+expected+' observed='+str(observed))
    imported=obj.get_editor_property('asset_import_data')
    import_file=cfg['decoded_cube']['file'] if 'decoded_cube' in cfg else row['file']
    source.require(imported is not None and [Path(p).resolve() for p in imported.extract_filenames()]
                   ==[Path(import_file['path']).resolve()], 'texture import source differs: '+row['package'])


def verify_material(u, mat, plan, row, graph, saved=True):
    """Read actual graph, typed defaults, texture identities and output links."""
    if saved:
        source.require(u.EditorAssetLibrary.get_metadata_tag(mat,'BH3.MaterialRecipe')==source.digest(graph),
                       'saved material policy differs: '+row['package'])
    for prop,enum in [('blend_mode',u.BlendMode),('shading_model',u.MaterialShadingModel)]:
        source.require(mat.get_editor_property(prop)==getattr(enum,graph[prop]),'material mode differs: '+row['package'])
    source.require(mat.get_editor_property('two_sided')==graph['two_sided']
                   and not mat.get_editor_property('use_material_attributes'),'material surface mode differs')
    if graph['blend_mode']=='BLEND_MASKED':
        numeric_equal(mat.get_editor_property('opacity_mask_clip_value'),graph['opacity_mask_clip_value'],row['package']+'/clip')
    expressions=list(u.MaterialEditingLibrary.get_material_expressions(mat))
    by_id={str(n.get_editor_property('desc')):n for n in expressions}
    source.require(len(by_id)==len(expressions)==len(graph['nodes']), 'material node identities/count differ: '+row['package'])
    nodes={}
    for spec in graph['nodes']:
        token='BH3.Stage.Node:'+spec['id']
        source.require(token in by_id,'material node disappeared: '+token)
        node=by_id[token];nodes[spec['id']]=node
        source.require(node.get_class().get_name()==spec['class'],'material expression class differs: '+token)
        for prop,value in spec.get('properties',{}).items():
            actual=node.get_editor_property(prop)
            expected=native_value(u,value)
            if isinstance(value,dict) and 'linear_color' in value:
                for c,v in zip((actual.r,actual.g,actual.b,actual.a),value['linear_color']):numeric_equal(c,v,token+'/'+prop)
            elif type(value) in (int,float):numeric_equal(actual,value,token+'/'+prop)
            else:source.require(actual==expected if isinstance(value,dict) else str(actual)==str(expected),
                                'material node property differs: '+token+'/'+prop)
        if 'custom_inputs' in spec:
            source.require([str(p.get_editor_property('input_name')) for p in node.get_editor_property('inputs')]
                           == spec['custom_inputs'],'custom inputs differ: '+token)
        if 'source_texture' in spec:
            texture=plan['textures'][row['textures'][spec['source_texture']]]
            source.require(object_path(node.get_editor_property('texture'))==texture['package']+'.'+texture['package'].rsplit('/',1)[1],
                           'material texture binding differs: '+token)
        props=row['fields']['m_SavedProperties']
        if 'source_scalar' in spec:numeric_equal(node.get_editor_property('default_value'),props['m_Floats'][spec['source_scalar']],token)
        if 'source_vector' in spec:
            actual=node.get_editor_property('default_value');expected=props['m_Colors'][spec['source_vector']]
            for name in ('r','g','b','a'):numeric_equal(getattr(actual,name),expected[name],token+'/'+name)
    for spec in graph['nodes']:
        node=nodes[spec['id']]
        names=[str(n) for n in u.MaterialEditingLibrary.get_material_expression_input_names(node)]
        inputs=list(u.MaterialEditingLibrary.get_inputs_for_material_expression(mat,node))
        source.require(len(names)==len(inputs),'native expression input schema differs')
        actual=dict(zip(names,inputs))
        edges=[e for e in graph['edges'] if e['to']==spec['id']]
        expected={e['input']:nodes[e['from']] for e in edges}
        source.require({key:value for key,value in actual.items() if value is not None}==expected,
                       'material input links differ: '+spec['id'])
        for edge in edges:
            from_node=nodes[edge['from']]
            index=expression_output_index(u,from_node,edge['output'])
            output_name=str(u.MaterialEditingLibrary.get_material_expression_output_names(from_node)[index])
            if 'custom_inputs' in spec:
                pin=node.get_editor_property('inputs')[names.index(edge['input'])]
                connection=custom_input_connection(pin,edge['to']+'/'+edge['input'])
                source.require(connection['OutputIndex']==index,
                               'material input channel differs: '+edge['to']+'/'+edge['input'])
                # Texture/vector native outputs use these explicit channel masks;
                # the other recipe expressions expose one unmasked output.
                source.require(output_name in ('','RGB','RGBA','R','G','B','A'),
                               'native recipe output mask schema differs: '+output_name)
                expected_mask=[0,0,0,0,0] if output_name=='' else [1]+[int(c in output_name) for c in 'RGBA']
                source.require([connection[f] for f in ('Mask','MaskR','MaskG','MaskB','MaskA')]==expected_mask,
                               'material input mask differs: '+edge['to']+'/'+edge['input'])
            else:
                source.require(sum(e['from']==edge['from'] for e in edges)==1,
                               'native non-Custom channel getter has multiple inputs from one source')
                observed=u.MaterialEditingLibrary.get_input_node_output_name_for_material_expression(node,from_node)
                source.require(observed==output_name,'material input channel differs: '+edge['to']+'/'+edge['input'])
    for out in graph['outputs']:
        prop=getattr(u.MaterialProperty,out['property'])
        node=nodes[out['node']]
        source.require(u.MaterialEditingLibrary.get_material_property_input_node(mat,prop)==node,
                       'material output link differs: '+out['property'])
        names=list(u.MaterialEditingLibrary.get_material_expression_output_names(node))
        source.require(u.MaterialEditingLibrary.get_material_property_input_node_output_name(mat,prop)
                       == names[expression_output_index(u,node,out['output'])], 'material output channel differs: '+out['property'])


def custom_input_connection(pin,context):
    # CustomInput.Input is not exposed to Python property access. StructBase's
    # native export_text serializes that FExpressionInput, including OutputIndex.
    # Inspect each named pin separately: the native source-node getter is ambiguous
    # when the same texture feeds both RGB and A inputs of one Custom expression.
    native=pin.export_text()
    values={name:re.findall(r'(?:^|[,()])'+name+r'=(-?\d+)(?=[,)])',native)
            for name in ('OutputIndex','Mask','MaskR','MaskG','MaskB','MaskA')}
    source.require(native.startswith('(InputName=') and ',Input=(' in native
                   and all(len(v)==1 and int(v[0])>=0 for v in values.values()),
                   'native CustomInput export schema differs: '+context+' '+native)
    return {name:int(v[0]) for name,v in values.items()}


def expression_output_index(u,node,name):
    names=[str(n) for n in u.MaterialEditingLibrary.get_material_expression_output_names(node)]
    if name=='':return 0
    source.require(name in names,'native expression output unavailable: '+name)
    return names.index(name)


def verify_assets(u,plan,settings,materials=True,texture_scope='textures',cube_export_root=None):
    selected=targets(plan,texture_scope)
    cube_exports=[]
    if cube_export_root is not None:
        cube_export_root=Path(cube_export_root).resolve()
        source.require(cube_export_root.is_relative_to(source.PROJECT/'Saved/BH3StageEnvironment') and not cube_export_root.exists(),
                       'native Cube source readback requires a fresh Saved cache')
        cube_export_root.mkdir(parents=True)
    for key,row in plan['textures'].items():
        if row['package'] not in selected:continue
        obj=exact_asset(u,row['package'],row['class'],True,plan)
        cfg=settings['textures'][key]
        source.require(u.EditorAssetLibrary.get_metadata_tag(obj,'BH3.TextureInterpretation')==source.digest(cfg),
                       'saved texture interpretation differs: '+row['package'])
        verify_texture(u,obj,row,cfg)
        if cube_export_root is not None and row['class']=='TextureCube':
            path=cube_export_root/(row['package'].rsplit('/',1)[1]+'.dds')
            task=u.AssetExportTask()
            for name,value in {'object':obj,'filename':str(path),'automated':True,'prompt':False,
                               'replace_identical':False,'exporter':u.TextureExporterDDS()}.items():task.set_editor_property(name,value)
            source.require(u.Exporter.run_asset_export_task(task) and path.is_file(),'native Cube Source DDS export failed: '+row['package'])
            observed=source.verify_exported_cube(path.read_bytes(),row,cfg)
            cube_exports.append({'package':row['package'],'file':source.evidence(path),**observed})
    if materials:
        for key,row in plan['materials'].items():
            verify_material(u,exact_asset(u,row['package'],'Material',True,plan),plan,row,settings['rendering']['materials'][key])
    source.require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'readback unexpectedly dirtied content assets')
    return {'textures':len(selected),'materials':len(plan['materials']) if materials else 0,
            'persisted_graph_and_bindings_verified':materials,'cube_source_readback':cube_exports,'visual_verified':False}


def pose_of(transform):
    t,s,q = transform.translation, transform.scale3d, transform.rotation
    return {'translation':[t.x,t.y,t.z], 'scale':[s.x,s.y,s.z], 'quaternion':[q.x,q.y,q.z,q.w]}


def ue_pose(u, pose):
    # The native MakeTransform constructor takes a Rotator; the stored property
    # accepts the source quaternion directly, without an Euler round trip.
    transform = u.Transform()
    transform.set_editor_property('translation',u.Vector(*pose['translation']))
    transform.set_editor_property('rotation',u.Quat(*pose['quaternion']))
    transform.set_editor_property('scale3d',u.Vector(*pose['scale']))
    return transform


def map_actors(u, plan, readback=False, load=True):
    levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
    if load:
        source.require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
                       'refusing to replace unsaved map work while loading Stage')
        source.require(levels.load_level(plan['map']), 'target Stage map failed to load')
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    expected_world = plan['map']+'.'+plan['map'].rsplit('/',1)[1]
    source.require(world.get_path_name() == expected_world, 'native editor loaded another world')
    all_actors = u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()
    by_path = {a.get_path_name():a for a in all_actors}
    mapped = {}
    corrected = {r['model']:r['package'] for r in plan['affine_meshes']}
    for mid,row in plan['geometry_actors'].items():
        source.require(row['actor'] in by_path, 'source actor identity disappeared: '+mid)
        actor = by_path[row['actor']]
        source.require(source.difference(source.matrix(pose_of(actor.get_actor_transform())),
                       source.matrix(row['world_transform'])) < .02, 'source actor world transform changed: '+mid)
        parent = actor.get_attach_parent_actor()
        expected_parent = row['parent_source_id']
        if expected_parent != '0':
            source.require(parent is not None and parent.get_path_name() == plan['geometry_actors'][expected_parent]['actor'],
                           'source parent changed: '+mid)
        if 'mesh' in row:
            components = actor.get_components_by_class(u.StaticMeshComponent)
            source.require(len(components) == 1, 'source renderer component identity differs')
            mesh = components[0].get_editor_property('static_mesh')
            expected_mesh = corrected.get(mid,row['mesh']) if readback else row['mesh']
            source.require(mesh is not None and mesh.get_path_name().split('.')[0] == expected_mesh,
                           'source mesh binding changed: '+mid)
            slots = [str(s.get_editor_property('imported_material_slot_name')) for s in mesh.get_editor_property('static_materials')]
            source.require(slots == row['material_slots'], 'source material-slot identities changed: '+mid)
        mapped[mid] = actor
    return world, mapped, by_path


def affine_assets(u, plan, result, read_only=False):
    """Sequential native TRS operations retain the source affine, including shear."""
    absent_targets(u, plan, 'affine')
    asset = u.GeometryScript_AssetUtils
    transforms = u.GeometryScript_MeshTransforms
    query = u.GeometryScript_MeshQueries
    for row in plan['affine_meshes']:
        original = exact_asset(u,row['mesh'],'StaticMesh')
        dm = u.DynamicMesh()
        value,outcome = asset.copy_mesh_from_static_mesh_v2(original,dm,u.GeometryScriptCopyMeshFromAssetOptions(),
                       u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0),False)
        source.require(value == dm and outcome == u.GeometryScriptOutcomePins.SUCCESS, 'source dynamic mesh copy failed')
        count = query.get_vertex_count(dm)
        before = {}
        for vertex in range(query.get_num_vertex_i_ds(dm)):
            p,valid = query.get_vertex_position(dm,vertex)
            if valid: before[vertex] = [p.x,p.y,p.z]
        source.require(len(before)==count and count>0, 'source geometry vertex enumeration failed')
        # Apply leaf->root before inverse(saved world); each operation transforms
        # normals/tangents through the native DynamicMesh attribute implementation.
        mid = row['model']
        while mid != '0':
            source.require(transforms.transform_mesh(dm,ue_pose(u,plan['native_local_poses'][mid]),True)==dm,
                           'source affine transform failed')
            mid = plan['geometry_actors'][mid]['parent_source_id']
        source.require(transforms.inverse_transform_mesh(dm,ue_pose(u,plan['geometry_actors'][row['model']]['world_transform']),True)==dm,
                       'source affine inverse failed')
        for vertex,p in before.items():
            actual,valid = query.get_vertex_position(dm,vertex)
            expected = source.point(row['correction'],p)
            source.require(valid and max(abs(x-y) for x,y in zip([actual.x,actual.y,actual.z],expected))<.02,
                           'native affine vertex readback differs')
        result.setdefault('affine_readback',[]).append({'model':row['model'],'vertices':count,
                            'source_mesh':row['mesh'],'target':row['package'],'vertex_matrix_verified':True})
        if read_only:
            continue
        duplicate = u.EditorAssetLibrary.duplicate_asset(row['mesh'],row['package'])
        source.require(duplicate is not None, 'source affine duplicate failed')
        options = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=False,enable_recompute_tangents=False,
                    enable_remove_degenerates=False,replace_materials=False,use_original_vertex_order=True)
        value,outcome = asset.copy_mesh_to_static_mesh(dm,duplicate,options,u.GeometryScriptMeshWriteLOD(lod_index=0),False)
        source.require(value==dm and outcome==u.GeometryScriptOutcomePins.SUCCESS, 'source affine asset copy failed')
        source.require([str(s.get_editor_property('imported_material_slot_name')) for s in duplicate.get_editor_property('static_materials')]
                       == plan['geometry_actors'][row['model']]['material_slots'], 'affine mesh lost material slots')
        stamp_save(u,duplicate,plan,[row['model'],row['mesh']],result)


def affine_vertex_snapshot(u, mesh, package):
    """Read SourceModel 0 through the same public copy contract as production."""
    dm = u.DynamicMesh()
    value,outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(
        mesh,dm,u.GeometryScriptCopyMeshFromAssetOptions(),
        u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL,lod_index=0),False)
    source.require(value==dm and outcome==u.GeometryScriptOutcomePins.SUCCESS,
                   'affine readback source-model copy failed: '+package)
    query = u.GeometryScript_MeshQueries
    vertices = {}
    for vertex in range(query.get_num_vertex_i_ds(dm)):
        position,valid = query.get_vertex_position(dm,vertex)
        if valid:
            point = [position.x,position.y,position.z]
            source.require(all(math.isfinite(v) for v in point),
                           'affine readback non-finite vertex '+str(vertex)+': '+package)
            vertices[vertex] = point
    source.require(len(vertices)==query.get_vertex_count(dm) and vertices,
                   'affine readback vertex enumeration failed: '+package)
    return vertices


def material_slot_bindings(mesh):
    """Preserve every ordered slot's names and both material bindings.

    UVChannelData is derived texture-streaming density, which changes with geometry;
    it is not a material binding or a second authoritative slot table.
    """
    bindings = []
    for slot in mesh.get_editor_property('static_materials'):
        row = {name:str(slot.get_editor_property(name))
               for name in ('material_slot_name','imported_material_slot_name')}
        for name in ('material_interface','overlay_material_interface'):
            material = slot.get_editor_property(name)
            row[name] = material.get_path_name() if material is not None else None
        bindings.append(row)
    return bindings


def affine_readback(u, plan, result):
    """Verify the exact ten persisted assets without creating or saving assets."""
    source.require(len(plan['affine_meshes'])==10,'affine readback requires the exact ten-asset plan')
    mesh_editor = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    source.require(mesh_editor is not None,'affine readback StaticMeshEditorSubsystem unavailable')
    verified = result.setdefault('affine_readback',[])
    for row in plan['affine_meshes']:
        package,original_package = row['package'],row['mesh']
        result['checking_asset'] = {'model':row['model'],'source_mesh':original_package,'target':package}
        context = package+' (source '+original_package+')'
        source.require(package_file(package).is_file() and package_file(original_package).is_file(),
                       'affine readback persisted asset missing: '+context)
        original = exact_asset(u,original_package,'StaticMesh')
        mesh = exact_asset(u,package,'StaticMesh',True,plan)
        source.require(u.EditorAssetLibrary.get_metadata_tag(mesh,'BH3.SourceIdentity')
                       == '/'.join([row['model'],original_package]),
                       'affine readback source identity differs: '+context)
        original_bindings,bindings = material_slot_bindings(original),material_slot_bindings(mesh)
        actor = plan['geometry_actors'][row['model']]
        source.require([s['imported_material_slot_name'] for s in original_bindings]==actor['material_slots']
                       and bindings==original_bindings,'affine readback material slot bindings differ: '+context)
        sections = [mesh_editor.get_lod_material_slot(mesh,0,i) for i in range(mesh.get_num_sections(0))]
        original_sections = [mesh_editor.get_lod_material_slot(original,0,i)
                             for i in range(original.get_num_sections(0))]
        source.require(sections==original_sections==actor['section_material_slots'],
                       'affine readback section material assignments differ: '+context)
        before,after = affine_vertex_snapshot(u,original,original_package),affine_vertex_snapshot(u,mesh,package)
        source.require(before.keys()==after.keys(),'affine readback vertex identities differ: '+context)
        for vertex,point in before.items():
            expected = source.point(row['correction'],point)
            source.require(max(abs(a-b) for a,b in zip(after[vertex],expected))<.02,
                           'affine readback vertex '+str(vertex)+' differs from source matrix: '+context)
        verified.append({'model':row['model'],'source_mesh':original_package,'target':package,
                         'vertices':len(after),'metadata_verified':True,'material_bindings':bindings,
                         'section_material_slots':sections,'persisted_vertex_matrix_verified':True})
    result.pop('checking_asset')


def object_path(obj):
    return obj.get_path_name() if obj is not None else None


def map_geometry_state(u):
    """A temporary preservation snapshot, consumed by the independent map cold read."""
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    state = {'world':world.get_path_name(),'actors':{}}
    for actor in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors():
        parent = actor.get_attach_parent_actor()
        row = {'class':actor.get_class().get_path_name(),'label':actor.get_actor_label(False),
               'tags':[str(t) for t in actor.get_editor_property('tags')],
               'hidden':bool(actor.get_editor_property('hidden')),
               'collision_enabled':actor.get_actor_enable_collision(),'parent':object_path(parent),
               'world_transform':pose_of(actor.get_actor_transform()),'components':{}}
        for component in actor.get_components_by_class(u.ActorComponent):
            component_state = {'class':component.get_class().get_path_name(),
                               'tags':[str(t) for t in component.get_editor_property('component_tags')]}
            if isinstance(component,u.SceneComponent):
                component_state.update(parent=object_path(component.get_attach_parent()),
                                       relative_transform=pose_of(component.get_relative_transform()),
                                       visible=bool(component.get_editor_property('visible')),
                                       hidden_in_game=bool(component.get_editor_property('hidden_in_game')),
                                       mobility=str(component.get_editor_property('mobility')))
            if isinstance(component,u.PrimitiveComponent):
                component_state['body_instance'] = component.get_editor_property('body_instance').export_text()
                component_state['cast_shadow'] = bool(component.get_editor_property('cast_shadow'))
            if isinstance(component,u.StaticMeshComponent):
                component_state.update(static_mesh=object_path(component.get_editor_property('static_mesh')),
                                       override_materials=[object_path(m) for m in component.get_editor_property('override_materials')],
                                       overlay_material=object_path(component.get_editor_property('overlay_material')),
                                       overlay_material_max_draw_distance=component.get_editor_property('overlay_material_max_draw_distance'))
            if isinstance(component,u.LightComponentBase):
                color = component.get_editor_property('light_color')
                component_state['light'] = {'color':[color.r,color.g,color.b,color.a],
                    **{p:component.get_editor_property(p) for p in
                       ('intensity','affects_world','cast_shadows','indirect_lighting_intensity','volumetric_scattering_intensity')}}
            if isinstance(component,u.ReflectionCaptureComponent):
                offset = component.get_editor_property('capture_offset')
                component_state['probe'] = {'cubemap':object_path(component.get_editor_property('cubemap')),
                    'source':str(component.get_editor_property('reflection_source_type')),
                    'brightness':component.get_editor_property('brightness'),'offset':[offset.x,offset.y,offset.z]}
            row['components'][component.get_path_name()] = component_state
        state['actors'][actor.get_path_name()] = row
    return state


def verify_geometry_state(actual, expected, path='map'):
    """Only poses use numeric comparison; identities and configuration stay exact."""
    if path.endswith('_transform'):
        source.require(source.difference(source.matrix(actual),source.matrix(expected))<1e-7,
                       'map geometry changed protected transform: '+path)
    elif isinstance(expected,dict):
        source.require(isinstance(actual,dict) and actual.keys()==expected.keys(),
                       'map geometry changed protected identities: '+path)
        for key,value in expected.items():verify_geometry_state(actual[key],value,path+'/'+key)
    else:
        source.require(actual==expected,'map geometry changed protected state: '+path)


def geometry_binding_changes(u, plan, actors):
    source.require(len(plan['affine_meshes'])==10,'map geometry requires exactly ten source-affine bindings')
    changes = []
    meshes = {}
    for row in plan['affine_meshes']:
        component = actors[row['model']].get_components_by_class(u.StaticMeshComponent)[0]
        mesh = exact_asset(u,row['package'],'StaticMesh',True,plan)
        source.require(u.EditorAssetLibrary.get_metadata_tag(mesh,'BH3.SourceIdentity')
                       == '/'.join([row['model'],row['mesh']]),'map geometry source identity differs: '+row['package'])
        meshes[row['model']] = mesh
        changes.append({'model':row['model'],'actor':actors[row['model']].get_path_name(),
                        'component':component.get_path_name(),
                        'from_mesh':row['mesh']+'.'+row['mesh'].rsplit('/',1)[1],
                        'to_mesh':mesh.get_path_name()})
    return changes,meshes


def geometry_expected_state(baseline, changes):
    expected = copy.deepcopy(baseline)
    for row in changes:
        component = expected['actors'][row['actor']]['components'][row['component']]
        source.require(component['static_mesh']==row['from_mesh'],
                       'map geometry baseline source reference differs: '+row['component'])
        component['static_mesh'] = row['to_mesh']
    return expected


def apply_map_geometry(u, plan, result, backup_path):
    """Commit only the ten existing component references; failures remain failures."""
    source.require(backup_path is not None,'map geometry requires an existing exact source-map backup')
    backup = Path(backup_path).resolve()
    map_file = package_file(plan['map'],'.umap')
    baseline_file = source.evidence(map_file)
    source.require(backup.is_relative_to(source.PROJECT/'Saved') and backup.is_file()
                   and source.evidence(backup)['sha256']==baseline_file['sha256'],
                   'map geometry backup is absent/foreign or differs from source map: '+str(backup))
    result['map_before'] = baseline_file
    result['map_backup'] = source.evidence(backup)
    world,actors,_ = map_actors(u,plan)
    changes,meshes = geometry_binding_changes(u,plan,actors)
    baseline = map_geometry_state(u)
    expected = geometry_expected_state(baseline,changes)
    source.require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
                   and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
                   'map geometry dependencies loaded with dirty map/content packages')
    result['map_geometry_baseline'],result['geometry_binding_changes'] = baseline,changes
    changed = []
    try:
        for row in changes:
            component = actors[row['model']].get_components_by_class(u.StaticMeshComponent)[0]
            original = component.get_editor_property('static_mesh')
            changed.append((component,original))
            # Modify marks this map component's package dirty even outside an undo transaction.
            component.modify(True)
            source.require(component.set_static_mesh(meshes[row['model']]),
                           'map geometry assignment failed: '+row['component'])
        # Verify the current world without reloading and discarding unsaved changes.
        map_actors(u,plan,True,False)
        verify_geometry_state(map_geometry_state(u),expected)
        source.require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
                       'map geometry unexpectedly dirtied content assets')
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        source.require(levels.get_current_level().get_path_name()==world.get_path_name()+':PersistentLevel'
                       and all(p==world.get_outer() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
                       'map geometry current/dirty level escapes the exact Stage map')
        result['map_save_attempted'] = True
        result['map_saved'] = bool(levels.save_current_level())
        source.require(result['map_saved'],'map geometry exact map save failed')
        source.require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
                       'map geometry save left dirty maps')
        result['map_file'] = source.evidence(map_file)
        result['geometry_bindings_verified'] = True
    except Exception:
        # Reclaim only this operation's references. Never save a failed operation
        # or replace its error with a successful rollback result.
        rollback_errors = []
        for component,original in reversed(changed):
            try:
                if component.get_editor_property('static_mesh')!=original:
                    source.require(component.set_static_mesh(original),'reference rollback was refused')
            except Exception as cleanup_error:
                rollback_errors.append(component.get_path_name()+': '+str(cleanup_error))
        result['reference_rollback_errors'] = rollback_errors
        try:verify_geometry_state(map_geometry_state(u),baseline)
        except Exception as cleanup_error:rollback_errors.append('protected state after rollback: '+str(cleanup_error))
        if map_file.is_file():result['map_file_after_failure'] = source.evidence(map_file)
        raise


def read_map_geometry(u, plan, result, applied_path):
    source.require(applied_path is not None,'map geometry cold read requires its successful apply result')
    applied = source.read_json(applied_path)
    source.require(applied['phase']=='map_geometry_passed' and applied['plan_digest']==plan['digest']
                   and applied['map_saved'] and applied['geometry_bindings_verified']
                   and not applied['saved_assets'] and not applied['created_actors']
                   and applied['map_file']==source.evidence(package_file(plan['map'],'.umap')),
                   'map geometry apply result is failed/stale or belongs to another plan/map')
    world,actors,_ = map_actors(u,plan,True)
    changes,_ = geometry_binding_changes(u,plan,actors)
    source.require(changes==applied['geometry_binding_changes'],'map geometry cold binding identities differ')
    verify_geometry_state(map_geometry_state(u),geometry_expected_state(applied['map_geometry_baseline'],changes))
    result.update(geometry_bindings_verified=True,geometry_binding_changes=changes,
                  source_actor_count=len(actors),total_actor_count=len(applied['map_geometry_baseline']['actors']),
                  apply_result=source.evidence(applied_path))


def read_geometry_baseline(u, plan, result):
    """只读核对已保存几何，不重复保存地图或网格。"""
    source.require(not plan['affine_meshes'], 'geometry baseline requires no pending source-affine correction')
    _, actors, all_actors = map_actors(u, plan, True)
    baseline = map_geometry_state(u)
    source.require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
                   and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
                   'saved geometry baseline has dirty map/content packages')
    result.update(map_file=source.evidence(package_file(plan['map'], '.umap')),
                  map_geometry_baseline=baseline, geometry_binding_changes=[], geometry_bindings_verified=True,
                  source_actor_count=len(actors), total_actor_count=len(all_actors))


def light_values(row, settings):
    f, policy = row['fields'], settings['lighting']
    colors = [f['m_Color'][name] for name in ('r','g','b')]
    source.require(all(math.isfinite(v) and 0 <= v <= 1 for v in colors), 'invalid source light color')
    if policy['color_space']=='linear':
        colors=[v*12.92 if v <= .0031308 else 1.055*v**(1/2.4)-.055 for v in colors]
    color=[int(math.floor(v*255+.5)) for v in colors]+[255]
    scale=policy['directional_lux_scale'] if f['m_Type']==1 else policy['local_intensity_scale']
    return {'light_color':color,'intensity':f['m_Intensity']*scale,'cast_shadows':bool(f['m_Shadows']['m_Type']),
            'affects_world':source.component_enabled(row),
            'indirect_lighting_intensity':policy['indirect_lighting_intensity'],
            'volumetric_scattering_intensity':policy['volumetric_scattering_intensity']}


def environment_pose(row, light):
    pose={'translation':[0.,0.,0.], 'quaternion':[0.,0.,0.,1.], 'scale':[1.,1.,1.]}
    if light:pose['quaternion']=[0.,-math.sqrt(.5),0.,math.sqrt(.5)]
    else:pose['scale']=[row['fields']['m_BoxSize'][axis]*50 for axis in ('x','y','z')]
    return pose


def spawn_environment(u,plan,settings,actors,result,created):
    editor=u.get_editor_subsystem(u.EditorActorSubsystem)
    settings_digest=source.lighting_generation_digest(plan,settings)
    for row in plan['lights']+plan['probes']:
        f=row['fields'];light='m_Shadows' in f
        cls={0:u.SpotLight,1:u.DirectionalLight,2:u.PointLight}[f['m_Type']] if light else u.BoxReflectionCapture
        actor=editor.spawn_actor_from_class(cls,u.Vector(0,0,0),u.Rotator(0,0,0),False)
        source.require(actor is not None,'environment actor spawn failed: '+row['source_path'])
        created.append(actor)
        actor.set_actor_label('BH3_Env_'+row['identity'][1])
        actor.set_editor_property('tags',[source.OWNER,plan['digest'],settings_digest,'/'.join(row['identity'])])
        result['created_actors'].append(actor.get_path_name())
        source.require(actor.attach_to_actor(actors[row['model']],'',u.AttachmentRule.KEEP_RELATIVE,
                       u.AttachmentRule.KEEP_RELATIVE,u.AttachmentRule.KEEP_RELATIVE,False),'environment attachment failed')
        comp=actor.get_component_by_class(u.LightComponent if light else u.BoxReflectionCaptureComponent)
        source.require(comp is not None,'environment native component is absent')
        if light:comp.set_mobility(u.ComponentMobility.MOVABLE)
        actor.set_actor_relative_transform(ue_pose(u,environment_pose(row,light)),False,False)
        enabled=source.component_enabled(row)
        actor.set_actor_hidden_in_game(not enabled)
        if light:
            values=light_values(row,settings)
            for prop,value in values.items():
                comp.set_editor_property(prop,u.Color(**dict(zip(('r','g','b','a'),value))) if prop=='light_color' else value)
            if f['m_Type']!=1:
                comp.set_editor_property('intensity_units',u.LightUnits.UNITLESS)
                comp.set_editor_property('use_inverse_squared_falloff',False)
                comp.set_editor_property('light_falloff_exponent',settings['lighting']['local_falloff_exponent'])
                comp.set_editor_property('attenuation_radius',f['m_Range']*100)
            if f['m_Type']==0:
                comp.set_editor_property('outer_cone_angle',f['m_SpotAngle']/2)
                comp.set_editor_property('inner_cone_angle',f['m_SpotAngle']/2*settings['lighting']['spot_inner_cone_ratio'])
        else:
            texture=plan['textures'][row['texture']]
            comp.set_editor_property('reflection_source_type',u.ReflectionSourceType.SPECIFIED_CUBEMAP)
            comp.set_editor_property('cubemap',exact_asset(u,texture['package'],'TextureCube',True,plan))
            comp.set_editor_property('brightness',f['m_IntensityMultiplier'] if enabled else 0.0)
            comp.set_editor_property('box_transition_distance',f['m_BlendDistance']*100)
            offset=f['m_BoxOffset']
            comp.set_editor_property('capture_offset',u.Vector(-offset['x']*100,-offset['y']*100,offset['z']*100))


def verify_environment(u,plan,settings,actors,all_actors):
    rows=plan['lights']+plan['probes']
    expected_labels={'BH3_Env_'+r['identity'][1] for r in rows}
    owned=[a for a in all_actors.values() if source.OWNER in [str(t) for t in a.get_editor_property('tags')]]
    labels={a.get_actor_label(False):a for a in owned}
    settings_digest=source.lighting_generation_digest(plan,settings)
    source.require(len(owned)==len(labels)==len(rows) and set(labels)==expected_labels,'environment actor set differs from source')
    for row in rows:
        f=row['fields'];light='m_Shadows' in f
        actor=labels['BH3_Env_'+row['identity'][1]]
        expected_class={0:u.SpotLight,1:u.DirectionalLight,2:u.PointLight}[f['m_Type']] if light else u.BoxReflectionCapture
        source.require(actor.get_class()==expected_class.static_class()
                       and [str(t) for t in actor.get_editor_property('tags')]
                       ==[source.OWNER,plan['digest'],settings_digest,'/'.join(row['identity'])]
                       and actor.get_attach_parent_actor()==actors[row['model']], 'environment identity/parent differs')
        component=actor.get_component_by_class(u.LightComponent if light else u.BoxReflectionCaptureComponent)
        source.require(component is not None,'environment component disappeared')
        local=pose_of(component.get_relative_transform())
        source.require(source.difference(source.matrix(local),source.matrix(environment_pose(row,light)))<.02,
                       'environment source-relative pose/volume differs: '+row['source_path'])
        enabled=source.component_enabled(row)
        source.require(bool(actor.get_editor_property('hidden'))==(not enabled),'environment enabled state differs')
        if light:
            source.require(component.get_editor_property('mobility')==u.ComponentMobility.MOVABLE,'light is not movable')
            for prop,value in light_values(row,settings).items():
                actual=component.get_editor_property(prop)
                if prop=='light_color':
                    observed=[actual.r,actual.g,actual.b,actual.a]
                    source.require(observed==value,'source light color differs: '+row['source_path']
                                   +' expected='+str(value)+' observed='+str(observed))
                elif type(value) is bool:source.require(actual==value,'light flag differs: '+prop)
                else:numeric_equal(actual,value,row['source_path']+'/'+prop)
            if f['m_Type']!=1:
                source.require(component.get_editor_property('intensity_units')==u.LightUnits.UNITLESS
                               and not component.get_editor_property('use_inverse_squared_falloff'),'local light unit model differs')
                numeric_equal(component.get_editor_property('attenuation_radius'),f['m_Range']*100,row['source_path']+'/range')
                numeric_equal(component.get_editor_property('light_falloff_exponent'),settings['lighting']['local_falloff_exponent'],'falloff')
            if f['m_Type']==0:
                numeric_equal(component.get_editor_property('outer_cone_angle'),f['m_SpotAngle']/2,'spot outer angle')
                numeric_equal(component.get_editor_property('inner_cone_angle'),f['m_SpotAngle']/2*settings['lighting']['spot_inner_cone_ratio'],'spot inner angle')
        else:
            texture=plan['textures'][row['texture']]
            source.require(component.get_editor_property('reflection_source_type')==u.ReflectionSourceType.SPECIFIED_CUBEMAP
                           and object_path(component.get_editor_property('cubemap'))==texture['package']+'.'+texture['package'].rsplit('/',1)[1],
                           'probe cube/source mode differs')
            numeric_equal(component.get_editor_property('brightness'),f['m_IntensityMultiplier'] if enabled else 0.,'probe brightness')
            numeric_equal(component.get_editor_property('box_transition_distance'),f['m_BlendDistance']*100,'probe blend')
            offset=component.get_editor_property('capture_offset');src=f['m_BoxOffset']
            for value,expected in zip((offset.x,offset.y,offset.z),(-src['x']*100,-src['y']*100,src['z']*100)):
                numeric_equal(value,expected,'probe offset')
    return labels


def environment_expected_state(baseline,plan,materials):
    expected=copy.deepcopy(baseline)
    if materials:
        for row in plan['renderers']:
            actor=expected['actors'][row['actor']]
            components=[c for c in actor['components'].values() if c['class']=='/Script/Engine.StaticMeshComponent']
            source.require(len(components)==1,'source renderer snapshot differs')
            component=components[0]
            component['override_materials']=[plan['materials'][key]['package']+'.'+plan['materials'][key]['package'].rsplit('/',1)[1]
                                             for key in row['materials']]
            enabled=source.component_enabled(row)
            component.update(visible=enabled,hidden_in_game=not enabled,cast_shadow=bool(row['fields']['m_CastShadows']))
    return expected


def preserved_environment_state(u,expected,created_paths):
    actual=map_geometry_state(u)
    source.require(set(actual['actors'])==set(expected['actors'])|set(created_paths),'map changed unplanned actor identities')
    for path in created_paths:actual['actors'].pop(path)
    verify_geometry_state(actual,expected)


def accepted_map_baseline(plan,settings,result_path,current_file,lighting_exists):
    source.require(result_path is not None,'environment apply requires its accepted geometry/lighting result')
    previous=source.read_json(result_path)
    saved_geometry = previous['phase'] == 'geometry_baseline_passed' and not previous['map_saved']
    source.require(previous['plan_digest']==plan['digest'] and (previous['map_saved'] or saved_geometry)
                   and previous['map_file']==current_file,'accepted map result is failed/stale/foreign')
    if lighting_exists:
        source.require(previous['phase']=='lighting_passed' and previous['settings_digest']==source.lighting_generation_digest(plan,settings)
                       and ('preserved_lighting' not in settings or settings['preserved_lighting']['apply_result']==source.evidence(result_path)),
                       'material apply requires this policy\'s accepted lighting checkpoint')
        return environment_expected_state(previous['environment_baseline'],plan,False),previous['created_actors']
    if saved_geometry:
        source.require(not plan['affine_meshes'] and previous['geometry_bindings_verified']
                       and not previous['geometry_binding_changes'] and not previous['saved_assets']
                       and not previous['created_actors'], 'saved geometry baseline contains unexpected mutations')
        return previous['map_geometry_baseline'], []
    source.require(previous['phase']=='map_geometry_passed' and previous['geometry_bindings_verified'],
                   'environment apply requires the saved affine geometry checkpoint')
    return geometry_expected_state(previous['map_geometry_baseline'],previous['geometry_binding_changes']),[]


def apply_map(u,plan,settings,result,map_sha,backup_path,previous_path,materials=True):
    """Commit source rendering overrides/owned lights; collision and geometry are protected."""
    map_file=package_file(plan['map'],'.umap');before=source.evidence(map_file)
    source.require(before['sha256'].lower()==map_sha.lower(),'map baseline changed')
    source.require(backup_path is not None,'environment map requires an exact existing Saved backup')
    backup=Path(backup_path).resolve()
    source.require(backup.is_relative_to(source.PROJECT/'Saved') and backup.is_file()
                   and source.evidence(backup)['sha256']==before['sha256'],'environment backup differs from current map')
    verify_assets(u,plan,settings,materials,'textures' if materials else 'probe_textures')
    source.require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'unsaved map work exists before environment load')
    world,actors,all_actors=map_actors(u,plan,True)
    baseline=map_geometry_state(u)
    owned=[a for a in all_actors.values() if source.OWNER in [str(t) for t in a.get_editor_property('tags')]]
    source.require(materials or not owned,'lighting phase is create-only; use lighting_readback for an existing checkpoint')
    expected_before,previous_created=accepted_map_baseline(plan,settings,previous_path,before,bool(owned))
    if owned:verify_environment(u,plan,settings,actors,all_actors)
    preserved_environment_state(u,expected_before,previous_created)
    source.require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'environment dependencies are dirty')
    result.update(map_before=before,map_backup=source.evidence(backup),previous_result=source.evidence(previous_path),
                  environment_baseline=baseline,settings_digest=source.digest(settings),materials_applied=materials)
    expected=environment_expected_state(baseline,plan,materials)
    changed=[];created=[]
    try:
        if materials:
            mats={key:exact_asset(u,row['package'],'Material',True,plan) for key,row in plan['materials'].items()}
            for row in plan['renderers']:
                component=actors[row['model']].get_components_by_class(u.StaticMeshComponent)[0]
                changed.append((component,copy.deepcopy(baseline['actors'][row['actor']]['components'][component.get_path_name()])))
                component.modify(True)
                for slot,key in enumerate(row['materials']):component.set_material(slot,mats[key])
                enabled=source.component_enabled(row)
                component.set_visibility(enabled,False);component.set_hidden_in_game(not enabled,False)
                component.set_editor_property('cast_shadow',bool(row['fields']['m_CastShadows']))
        if not owned:spawn_environment(u,plan,settings,actors,result,created)
        preserved_environment_state(u,expected,result['created_actors'])
        result['readback']=verify_map(u,plan,settings,materials,False)
        levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
        source.require(levels.get_current_level().get_path_name()==world.get_path_name()+':PersistentLevel'
                       and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                       and all(p==world.get_outer() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
                       'environment save would include unplanned map/content work')
        result['map_save_attempted']=True
        result['map_saved']=bool(levels.save_current_level())
        source.require(result['map_saved'] and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'exact environment map save failed')
        result['map_file']=source.evidence(map_file)
    except Exception:
        cleanup=[]
        for component,state in reversed(changed):
            try:
                component.set_editor_property('override_materials',[u.EditorAssetLibrary.load_asset(p) if p else None for p in state['override_materials']])
                component.set_visibility(state['visible'],False);component.set_hidden_in_game(state['hidden_in_game'],False)
                component.set_editor_property('cast_shadow',state['cast_shadow'])
            except Exception as exc:cleanup.append(component.get_path_name()+': '+str(exc))
        editor=u.get_editor_subsystem(u.EditorActorSubsystem)
        for actor in reversed(created):
            try:source.require(editor.destroy_actor(actor),'owned failed spawn cleanup refused')
            except Exception as exc:cleanup.append('owned actor cleanup: '+str(exc))
        try:verify_geometry_state(map_geometry_state(u),baseline)
        except Exception as exc:cleanup.append('map after cleanup: '+str(exc))
        result['cleanup_errors']=cleanup
        result['map_file_after_failure']=source.evidence(map_file)
        raise


def verify_map(u,plan,settings,materials=True,load=True):
    world,actors,all_actors=map_actors(u,plan,True,load)
    verify_environment(u,plan,settings,actors,all_actors)
    if materials:
        mats={key:exact_asset(u,row['package'],'Material',True,plan) for key,row in plan['materials'].items()}
        for row in plan['renderers']:
            comp=actors[row['model']].get_components_by_class(u.StaticMeshComponent)[0]
            overrides=list(comp.get_editor_property('override_materials'))
            source.require(len(overrides)==len(row['materials']),'renderer override slot cardinality differs')
            for slot,key in enumerate(row['materials']):
                source.require(comp.get_material(slot)==mats[key],
                               'renderer override does not match native source slot')
            enabled=source.component_enabled(row)
            source.require(comp.get_editor_property('visible')==enabled and comp.get_editor_property('hidden_in_game')==(not enabled)
                           and comp.get_editor_property('cast_shadow')==bool(row['fields']['m_CastShadows']), 'renderer source flags differ')
    return {'source_renderers':len(plan['renderers']),'material_slots':sum(len(r['materials']) for r in plan['renderers']) if materials else 0,
            'source_lights':len(plan['lights']),'source_probes':len(plan['probes']),'affine_meshes':len(plan['affine_meshes']),
            'source_colliders_activated':False,'collision_modified':False,'source_runtime_verified':False,
            'reflection_capture_runtime_processed_verified':False,'visual_verified':False,'restoration_complete':False}


def read_environment(u,plan,settings,result,applied_path,materials):
    source.require(applied_path is not None,'environment cold read requires its accepted apply result')
    applied=source.read_json(applied_path)
    source.require(applied['phase']==('map_passed' if materials else 'lighting_passed')
                   and applied['plan_digest']==plan['digest'] and applied['settings_digest']==source.digest(settings)
                   and applied['map_saved'] and applied['materials_applied']==materials
                   and applied['map_file']==source.evidence(package_file(plan['map'],'.umap')),'environment apply result is stale/failed/foreign')
    result['assets_readback']=verify_assets(u,plan,settings,materials,'textures' if materials else 'probe_textures')
    result['readback']=verify_map(u,plan,settings,materials,True)
    preserved_environment_state(u,environment_expected_state(applied['environment_baseline'],plan,materials),applied['created_actors'])
    source.require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),'cold environment read dirtied maps')
    result['apply_result']=source.evidence(applied_path)


def support_dynamic_mesh(u, spec, saved_mesh=None):
    """原 Floor OBJ 只换一次局部帧；P3 读取原 SourceModel0，不经过新导入器。"""
    dm = u.DynamicMesh()
    if saved_mesh is None and spec['stage'] == 'P1':
        for index, point in enumerate(spec['vertices']):
            value, actual = u.GeometryScript_MeshEdits.add_vertex_to_mesh(dm, u.Vector(*point), True)
            source.require(value == dm and actual == index, 'PawnSupport native vertex append identity differs')
        for index, triangle in enumerate(spec['native_triangles'] if 'native_winding_policy' in spec else spec['triangles']):
            value, actual = u.GeometryScript_MeshEdits.add_triangle_to_mesh(dm, u.IntVector(*triangle), 0, True)
            source.require(value == dm and actual == index, 'PawnSupport native triangle append failed: '+str(index))
    else:
        mesh = saved_mesh if saved_mesh is not None else exact_asset(u, spec['source_mesh'], 'StaticMesh')
        value, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(
            mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(),
            u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL, lod_index=0), False)
        source.require(value == dm and outcome == u.GeometryScriptOutcomePins.SUCCESS,
                       'PawnSupport original SourceModel0 copy failed')
    query = u.GeometryScript_MeshQueries
    vertices, triangles = {}, {}
    for index in range(query.get_num_vertex_i_ds(dm)):
        p, valid = query.get_vertex_position(dm, index)
        if valid:
            point = [p.x, p.y, p.z]
            source.require(all(math.isfinite(v) for v in point), 'PawnSupport native vertex is non-finite')
            vertices[index] = point
    for index in range(query.get_num_triangle_i_ds(dm)):
        face, valid = query.get_triangle_indices(dm, index)
        if valid:
            triangles[index] = [face.x, face.y, face.z]
            source.require(len(set(triangles[index])) == 3 and all(v in vertices for v in triangles[index]),
                           'PawnSupport native triangle connectivity differs')
    source.require(len(vertices) == query.get_vertex_count(dm) == spec['vertices_expected']
                   and len(triangles) == dm.get_triangle_count() == spec['triangles_expected'],
                   'PawnSupport native source topology cardinality differs')
    if spec['stage'] == 'P1' and saved_mesh is None:
        native = spec['native_triangles'] if 'native_winding_policy' in spec else spec['triangles']
        source.require(list(triangles.values()) == native, 'PawnSupport native OBJ winding conversion differs')
        for index, expected in enumerate(spec['vertices']):
            source.require(max(abs(a-b) for a, b in zip(vertices[index], expected)) < .002,
                           'PawnSupport native OBJ frame differs: '+str(index))
    return dm, {'vertices': vertices, 'triangles': triangles}


def support_capsule_cdo(u, pawn_class):
    """只读真实角色 CDO；角色尺寸与正常重力不从另一角色借用。"""
    source.require(pawn_class is not None, 'PawnSupport configured PawnClass is missing')
    pawn = u.get_default_object(pawn_class)
    source.require(isinstance(pawn, u.Character), 'PawnSupport configured PawnClass is not a Character')
    capsule = pawn.get_editor_property('CapsuleComponent')
    movement = pawn.get_editor_property('CharacterMovement')
    source.require(capsule is not None and movement is not None, 'PawnSupport configured capsule/CMC is missing')
    radius = float(capsule.get_unscaled_capsule_radius())
    half_height = float(capsule.get_unscaled_capsule_half_height())
    gravity = float(movement.get_editor_property('GravityScale'))
    direction = movement.get_gravity_direction()
    source.require(math.isfinite(radius) and math.isfinite(half_height) and 0 < radius <= half_height
                   and math.isfinite(gravity) and gravity > 0 and [direction.x, direction.y, direction.z] == [0., 0., -1.],
                   'PawnSupport selected capsule/normal downward gravity contract differs')
    return movement, {'class': object_path(pawn_class), 'radius_cm': radius, 'half_height_cm': half_height,
                      'gravity_scale': gravity, 'gravity_direction': [direction.x, direction.y, direction.z],
                      'profile': str(capsule.get_collision_profile_name()),
                      'trace_complex_on_move': bool(capsule.get_editor_property('bTraceComplexOnMove')),
                      'walkable_floor_z': float(movement.get_walkable_floor_z()),
                      'capsule_body_native_text': capsule.get_editor_property('body_instance').export_text(),
                      'capsule_relative_transform': capsule.get_relative_transform().export_text()}


def support_player_configuration(u, world, plan):
    """关卡覆盖与项目缺省按引擎入口读取；默认名单只是运行前候选。"""
    world_settings = u.GameplayStatics.get_all_actors_of_class(world, u.WorldSettings)
    source.require(len(world_settings) == 1, 'PawnSupport exact WorldSettings is missing/ambiguous')
    world_settings = world_settings[0]
    game_maps = u.GameMapsSettings.get_game_maps_settings()
    native_default = game_maps.get_editor_property('global_default_game_mode').export_text()
    prefixes = list(game_maps.get_editor_property('game_mode_map_prefixes'))
    game_mode_class = world_settings.get_editor_property('default_game_mode')
    origin = 'WorldSettings.DefaultGameMode'
    if game_mode_class is None:
        short_name = plan['map'].rsplit('/', 1)[1]
        matched = [p for p in prefixes if short_name.startswith(str(p.get_editor_property('name')))]
        source.require(not matched, 'PawnSupport map has a GameMode prefix override requiring explicit resolution')
        paths = re.findall(r'/[A-Za-z0-9_/]+\.[A-Za-z0-9_]+', native_default)
        source.require(len(paths) == 1 and paths[0].endswith('_C'),
                       'PawnSupport native project default GameMode path is missing/ambiguous: '+native_default)
        game_mode_class = u.load_class(None, paths[0])
        origin = 'GameMapsSettings.GlobalDefaultGameMode'
    source.require(game_mode_class is not None, 'PawnSupport selected GameMode class failed to load')
    cdo = u.get_default_object(game_mode_class)
    source.require(callable(getattr(cdo, 'get_experience', None)), 'PawnSupport configured GameMode has no Experience interface')
    experience = cdo.get_experience()
    source.require(experience is not None, 'PawnSupport configured GameMode Experience is missing')
    roster = list(experience.get_editor_property('SquadMembers'))
    roots = [str(v) for v in experience.get_editor_property('GameFeaturesToEnable')]
    declarations = [v.export_text() for v in experience.get_editor_property('GameFeatureSources')]
    result = {'world_settings': world_settings.get_path_name(), 'map_game_mode_override':
              object_path(world_settings.get_editor_property('default_game_mode')),
              'native_project_default': native_default, 'prefixes_native': [p.export_text() for p in prefixes],
              'game_mode_class': object_path(game_mode_class), 'selection_source': origin,
              'experience': object_path(experience), 'game_feature_roots': roots,
              'game_feature_declarations_native': declarations, 'default_roster': [],
              'default_roster_is_runtime_selection': False, 'runtime_game_feature_session_verified': False,
              'runtime_possession_verified': False}
    movements = []
    for data in roster:
        source.require(data is not None, 'PawnSupport Experience default roster contains a null entry')
        movement, capsule = support_capsule_cdo(u, data.get_editor_property('PawnClass'))
        row = {'pawn_data': object_path(data), 'capsule': capsule}
        for prop in ('MovementSet', 'InputConfig', 'DefaultCameraMode'):
            row[prop] = object_path(data.get_editor_property(prop))
        row['ability_sets'] = [object_path(a) for a in data.get_editor_property('AbilitySets')]
        source.require(row['MovementSet'] is not None and row['InputConfig'] is not None,
                       'PawnSupport default player MovementSet/InputConfig is missing: '+row['pawn_data'])
        result['default_roster'].append(row)
        movements.append(movement)
    result['default_roster_has_player_candidate'] = bool(roster)
    result['player_starts'] = [{'actor': a.get_path_name(), 'pose': pose_of(a.get_actor_transform())}
                               for a in u.GameplayStatics.get_all_actors_of_class(world, u.PlayerStart)]
    return result, movements


def support_body_state(u, actor):
    """保留来源和相机层的实际配置，不改 BodySetup 或碰撞响应。"""
    subsystem = u.get_editor_subsystem(u.StaticMeshEditorSubsystem)
    rows = []
    for comp in actor.get_components_by_class(u.StaticMeshComponent):
        mesh = comp.get_editor_property('static_mesh')
        source.require(mesh is not None, 'PawnSupport original collision component mesh is missing')
        simple = subsystem.get_simple_collision_count(mesh)
        convex = subsystem.get_convex_collision_count(mesh)
        complexity = subsystem.get_collision_complexity(mesh)
        body = mesh.get_editor_property('BodySetup')
        rows.append({'actor': actor.get_path_name(), 'component': comp.get_path_name(), 'mesh': object_path(mesh),
                     'body_setup': object_path(body), 'simple_collision_count': simple, 'convex_collision_count': convex,
                     'complexity': str(complexity), 'agg_geom': body.get_editor_property('AggGeom').export_text() if body else None,
                     'actor_collision': actor.get_actor_enable_collision(),
                     'collision_enabled': str(comp.get_collision_enabled()), 'profile': str(comp.get_collision_profile_name()),
                     'pawn_response': str(comp.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN)),
                     'camera_response': str(comp.get_collision_response_to_channel(u.CollisionChannel.ECC_CAMERA)),
                     'body_instance': comp.get_editor_property('body_instance').export_text()})
    return rows


def support_sweep(u, world, capsule, movement, start, end, complex_trace=False, ignored_actors=()):
    """复用真实 profile 的原生查询；未命中不制造命中法线或支撑成功。"""
    hit = u.SystemLibrary.capsule_trace_single_by_profile(world, u.Vector(*start), u.Vector(*end),
        capsule['radius_cm'], capsule['half_height_cm'], capsule['profile'], complex_trace,
        list(ignored_actors), u.DrawDebugTrace.NONE, False)
    query = {'profile': capsule['profile'], 'complex': complex_trace, 'start_cm': start, 'end_cm': end, 'hit': None}
    if hit is not None:
        source.require(isinstance(hit, u.HitResult), 'PawnSupport native sweep return differs')
        fields = hit.to_tuple()
        source.require(len(fields) == 18 and fields[0], 'PawnSupport native HitResult signature differs')
        text = hit.export_text()
        depths = re.findall(r'(?:^|[,\(])PenetrationDepth=([^,\)]+)', text)
        source.require(len(depths) == 1 and math.isfinite(float(depths[0])), 'PawnSupport penetration depth unavailable')
        query['hit'] = {'native_text': text, 'initial_penetration': bool(fields[1]),
                        'penetration_depth_cm': float(depths[0]), 'actor': object_path(fields[9]),
                        'component': object_path(fields[10]), 'location_cm': [fields[4].x, fields[4].y, fields[4].z],
                        'impact_normal': [fields[7].x, fields[7].y, fields[7].z],
                        'native_cmc_is_walkable': bool(movement.is_walkable(hit))}
    return query


def loaded_stage_actors(u, plan):
    """环境校验已核原件；同次只提取所需对象，不再完整验证每个 Renderer。"""
    world = u.get_editor_subsystem(u.UnrealEditorSubsystem).get_editor_world()
    by_path = {a.get_path_name(): a for a in u.get_editor_subsystem(u.EditorActorSubsystem).get_all_level_actors()}
    return world, {mid: by_path[row['actor']] for mid, row in plan['geometry_actors'].items()}, by_path


def support_visible_surface_check(u, plan, spec, actors):
    """源到 native 顶点帧先核准，再测原 Floor 到真实可见三角面的距离。"""
    surfaces, verified = [], []
    for row in spec['visual_surfaces']:
        source_vertices, source_triangles = source.parse_support_obj(
            Path(row['source_obj']['path']).read_text(encoding='utf-8-sig'),
            '# Original Unity coordinates / units / winding; no axis conversion.')
        mesh = exact_asset(u, row['package'], 'StaticMesh')
        dm = u.DynamicMesh()
        value, outcome = u.GeometryScript_AssetUtils.copy_mesh_from_static_mesh_v2(
            mesh, dm, u.GeometryScriptCopyMeshFromAssetOptions(),
            u.GeometryScriptMeshReadLOD(lod_type=u.GeometryScriptLODType.SOURCE_MODEL, lod_index=0), False)
        source.require(value == dm and outcome == u.GeometryScriptOutcomePins.SUCCESS,
                       'P2 region visible native SourceModel0 copy failed')
        query = u.GeometryScript_MeshQueries
        vertices = {}
        for i in range(query.get_num_vertex_i_ds(dm)):
            p, valid = query.get_vertex_position(dm, i)
            if valid:vertices[i] = [p.x, p.y, p.z]
        source.require(len(vertices) == query.get_vertex_count(dm) == row['vertex_count']
                       and dm.get_triangle_count() == row['triangle_count'], 'P2 region visible native topology counts differ')
        maximum = 0.
        for p in vertices.values():
            distance = min(max(abs(a-b) for a, b in zip(p, expected)) for expected in source_vertices)
            maximum = max(maximum, distance)
        source.require(maximum < .02, 'P2 region source visible mesh local frame differs from native import')
        transform = source.matrix(pose_of(actors[row['model']].get_actor_transform()))
        native_world = {i: source.point(transform, p) for i, p in vertices.items()}
        for i in range(query.get_num_triangle_i_ds(dm)):
            face, valid = query.get_triangle_indices(dm, i)
            if valid:surfaces.append([native_world[j] for j in (face.x, face.y, face.z)])
        verified.append({'model': row['model'], 'mesh': row['package'], 'native_vertices': len(vertices),
                         'native_triangles': dm.get_triangle_count(), 'maximum_source_local_error_cm': maximum})
    begin, end = spec['floor_vertex_range']
    transform = source.matrix(spec['source_world_pose'])
    distances = [min(source.point_triangle_distance(source.point(transform, p), *face) for face in surfaces)
                 for p in spec['vertices'][begin:end]]
    source.require(len(distances) == 41 and max(distances) < .1,
                   'P2 region original Floor does not match the actual P1 visible triangle surfaces')
    return {'native_visible_meshes': verified, 'floor_vertex_distances_cm': distances,
            'maximum_floor_surface_distance_cm': max(distances), 'runtime_world_registration_verified': False}


def pawn_support_preflight(u, plan, settings, result, environment_result, p1_source_manifest=None, asset_result=None):
    """只读原场景和瞬态几何；不建资产/Actor，不 PIE，不保存。"""
    source.require(plan['stage'] != 'P1' or p1_source_manifest is not None, 'P1 preflight needs its selected P2 source manifest')
    spec = source.pawn_support_spec(plan, p1_source_manifest)
    if asset_result is None:
        source.require(not package_file(spec['package']).exists() and not u.EditorAssetLibrary.does_asset_exist(spec['package']),
                       'PawnSupport create-only target already exists')
    read_environment(u, plan, settings, result, environment_result, True)
    world, actors, _ = loaded_stage_actors(u, plan)
    baseline = map_geometry_state(u)
    camera_mid = {'P1': '1580554021824', 'P3': '1934927154112'}[plan['stage']]
    protected_packages = {plan['map']: '.umap'}
    for mid in (spec['source_model'], camera_mid):
        if 'mesh' in plan['geometry_actors'][mid]:
            protected_packages[plan['geometry_actors'][mid]['mesh']] = '.uasset'
    for surface in spec.get('visual_surfaces', []):protected_packages[surface['package']] = '.uasset'
    protected = {p: source.evidence(package_file(p, ext)) for p, ext in protected_packages.items()}
    result.update(support_spec=spec, protected_packages=protected, source_scene_baseline=baseline,
                  pie_started=False, legal_spawn_verified=False, actual_cmc_landing_verified=False,
                  original_camera_preserved=False)
    try:
        result['phase'] = 'pawn_support_native_geometry'
        dm, topology = support_dynamic_mesh(u, spec)
        world_vertices = {i: source.point(source.matrix(spec['source_world_pose']), p)
                          for i, p in topology['vertices'].items()}
        bounds = {'min': [min(p[i] for p in world_vertices.values()) for i in range(3)],
                  'max': [max(p[i] for p in world_vertices.values()) for i in range(3)]}
        result.update(native_source_topology=topology, native_source_topology_digest=source.digest(topology),
                      source_world_bounds_cm=bounds,
                      original_source_body=support_body_state(u, actors[spec['source_model']]),
                      original_camera_body=support_body_state(u, actors[camera_mid]))
        if asset_result is not None:
            failed, evidence = support_asset_resume(spec, dict(result, phase='pawn_support_preflight_passed'), protected[plan['map']], asset_result)
            source.require(failed['phase'] == 'pawn_support_asset_repair_passed', 'PawnSupport existing-target preflight requires explicit asset repair')
            verify_support_asset(u, spec, topology)
            result['asset_repair_result'] = evidence
        floor_vertices = world_vertices.values()
        if 'floor_vertex_range' in spec:
            begin, end = spec['floor_vertex_range']
            floor_vertices = [world_vertices[i] for i in range(begin, end)]
            result['native_visible_surface_check'] = support_visible_surface_check(u, plan, spec, actors)
        result['floor_query_bounds_cm'] = {'min': [min(p[i] for p in floor_vertices) for i in range(3)],
                                         'max': [max(p[i] for p in floor_vertices) for i in range(3)]}
        result['phase'] = 'pawn_support_player_configuration'
        config, movements = support_player_configuration(u, world, plan)
        result['player_configuration'] = config
        result['native_queries'] = []
        for row, movement in zip(config['default_roster'], movements):
            capsule = row['capsule']
            center = [(bounds['min'][i]+bounds['max'][i])*.5 for i in range(2)]
            start = center+[bounds['max'][2]+capsule['half_height_cm']*3]
            end = center+[bounds['min'][2]-capsule['half_height_cm']*3]
            for complex_trace in (False, True):
                query = support_sweep(u, world, capsule, movement, start, end, complex_trace)
                query['pawn_data'] = row['pawn_data']
                result['native_queries'].append(query)
    finally:
        verify_geometry_state(map_geometry_state(u), baseline)
        source.require({p: source.evidence(package_file(p, ext)) for p, ext in protected_packages.items()} == protected,
                       'PawnSupport preflight changed protected source/map packages')
        source.require(not u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
                       and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
                       'PawnSupport preflight left dirty packages')
        result['original_camera_preserved'] = True


def verify_support_asset(u, spec, expected_topology):
    """同一 SourceModel0 入口读派生包；元数据不代替实际拓扑和碰撞模式。"""
    mesh = exact_asset(u, spec['package'], 'StaticMesh')
    for key, expected in {'Owner': spec['owner'], 'SourceSpec': source.digest(spec),
                          'Policy': spec['policy'], 'CameraPolicy': spec['camera_policy']}.items():
        source.require(u.EditorAssetLibrary.get_metadata_tag(mesh, 'BH3.PawnSupport.'+key) == expected,
                       'PawnSupport asset metadata differs: '+key)
    _, topology = support_dynamic_mesh(u, spec, mesh)
    expected = json.loads(json.dumps(expected_topology))
    actual = json.loads(json.dumps(topology))
    source.require(actual['triangles'] == expected['triangles'] and actual['vertices'].keys() == expected['vertices'].keys(),
                   'PawnSupport saved source topology identities/connectivity differ')
    # MeshDescriptionBuilder 明确将位置写为 FVector3f；按这个原生存储契约逐位核对。
    for vertex, point in expected['vertices'].items():
        canonical = [struct.unpack('<f', struct.pack('<f', value))[0] for value in point]
        source.require(actual['vertices'][vertex] == canonical, 'PawnSupport saved Float32 source position differs: '+vertex)
    complexity = u.get_editor_subsystem(u.StaticMeshEditorSubsystem).get_collision_complexity(mesh)
    source.require(complexity == u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE,
                   'PawnSupport saved collision complexity differs')
    source.require(mesh.get_editor_property('BodySetup') is not None, 'PawnSupport saved BodySetup is missing')
    return mesh


def configure_support_component(u, comp):
    """碰撞专用组件只参与 Pawn 查询，不参与编辑器或游戏渲染。"""
    comp.set_collision_profile_name('Custom', False)
    comp.set_collision_enabled(u.CollisionEnabled.QUERY_ONLY)
    comp.set_collision_object_type(u.CollisionChannel.ECC_WORLD_STATIC)
    comp.set_collision_response_to_all_channels(u.CollisionResponseType.ECR_IGNORE)
    comp.set_collision_response_to_channel(u.CollisionChannel.ECC_PAWN, u.CollisionResponseType.ECR_BLOCK)
    comp.generate_overlap_events = False
    comp.set_visibility(False, False)
    comp.set_hidden_in_game(True, False)


def support_actor_state(u, actor, spec, diagnostic=None, require_collision=True, require_hidden_render=True):
    """派生体只有明确的 Pawn 查询职责；原相机层由原场景保护快照核验。"""
    components = actor.get_components_by_class(u.StaticMeshComponent)
    source.require(isinstance(actor, u.StaticMeshActor) and len(components) == 1,
                   'PawnSupport owned Actor/component identity differs')
    comp = components[0]
    mesh = comp.get_editor_property('static_mesh')
    if diagnostic is not None:
        diagnostic.update(mesh=object_path(mesh), actor_collision=actor.get_actor_enable_collision(),
            actor_hidden=bool(actor.get_editor_property('hidden')), collision_enabled=str(comp.get_collision_enabled()),
            object_type=str(comp.get_collision_object_type()),
            pawn_response=str(comp.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN)),
            camera_response=str(comp.get_collision_response_to_channel(u.CollisionChannel.ECC_CAMERA)),
            generate_overlap_events=bool(comp.generate_overlap_events),
            component_visible=bool(comp.get_editor_property('visible')),
            component_hidden_in_game=bool(comp.get_editor_property('hidden_in_game')),
            use_default_collision=bool(comp.get_editor_property('use_default_collision')),
            body_instance=comp.get_editor_property('body_instance').export_text())
    source.require(mesh is not None and mesh.get_path_name().split('.')[0] == spec['package']
                   and actor.get_actor_enable_collision() and bool(actor.get_editor_property('hidden')),
                   'PawnSupport owned component mesh/Actor identity differs')
    source.require(not require_hidden_render or not comp.get_editor_property('visible')
                   and comp.get_editor_property('hidden_in_game'),
                   'PawnSupport collision-only component is exposed to rendering')
    source.require(not require_collision or not comp.get_editor_property('use_default_collision')
                   and comp.get_collision_enabled() == u.CollisionEnabled.QUERY_ONLY
                   and comp.get_collision_object_type() == u.CollisionChannel.ECC_WORLD_STATIC
                   and comp.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN) == u.CollisionResponseType.ECR_BLOCK
                   and comp.get_collision_response_to_channel(u.CollisionChannel.ECC_CAMERA) == u.CollisionResponseType.ECR_IGNORE
                   and not comp.generate_overlap_events,
                   'PawnSupport owned component Pawn/Camera contract differs')
    source.require(object_path(actor.get_attach_parent_actor()) == spec['source_actor']
                   and source.difference(source.matrix(pose_of(actor.get_actor_transform())),
                                         source.matrix(spec['source_world_pose'])) < .002,
                   'PawnSupport owned source attachment/frame differs')
    expected_tags = [spec['owner'], source.digest(spec), spec['source_plan_digest'], 'PawnQuery']
    source.require([str(t) for t in actor.get_editor_property('tags')] == expected_tags,
                   'PawnSupport owned Actor tags differ')
    return {'actor': actor.get_path_name(), 'component': comp.get_path_name(), 'mesh': mesh.get_path_name(),
            'parent': object_path(actor.get_attach_parent_actor()), 'world_pose': pose_of(actor.get_actor_transform()),
            'body_instance': comp.get_editor_property('body_instance').export_text(), 'tags': expected_tags}


def support_spawn_candidate(u, world, support, capsule, movement, xy, bounds, diagnostic=None):
    """出生候选由真实胶囊扫地和净空得出，不使用来源 AABB 的 Z 充当接触面。"""
    start = list(xy)+[bounds['max'][2]+capsule['half_height_cm']*3]
    end = list(xy)+[bounds['min'][2]-capsule['half_height_cm']*3]
    sweep = support_sweep(u, world, capsule, movement, start, end)
    if diagnostic is not None:
        diagnostic.update(expected_component=support['component'], capsule=capsule, floor_sweep=sweep)
    hit = sweep['hit']
    source.require(hit is not None and hit['component'] == support['component']
                   and not hit['initial_penetration'] and hit['penetration_depth_cm'] == 0
                   and hit['native_cmc_is_walkable'], 'PawnSupport spawn sweep lacks the exact walkable owned support')
    location = list(hit['location_cm'])
    location[2] += capsule['radius_cm']*.1
    clearance = support_sweep(u, world, capsule, movement, location, location)
    if diagnostic is not None:diagnostic.update(location_cm=location, clearance=clearance)
    source.require(clearance['hit'] is None, 'PawnSupport queried spawn capsule has no clearance')
    return {'location_cm': location, 'capsule': capsule, 'floor_sweep': sweep, 'clearance': clearance,
            'actual_spawn_verified': False}


def support_region_boundary_queries(u, world, spec, support, candidate, movement):
    """从围栏内部横扫原壁、向上扫原顶；反面顶面不充当出生地面。"""
    pose = source.matrix(spec['source_world_pose'])
    vertices = [source.point(pose, p) for p in spec['vertices']]
    wall = next(row for row in spec['source_instances'] if row['role'] == 'wall')
    wall_begin, wall_end = wall['vertex_range']
    face = next(f for f in spec['triangles'] if all(wall_begin <= i < wall_end for i in f))
    xy = [sum(vertices[i][axis] for i in face)/3 for axis in range(2)]
    center = candidate['location_cm']
    inward = [center[i]-xy[i] for i in range(2)]
    length = math.hypot(*inward)
    source.require(length > candidate['capsule']['radius_cm']*4, 'P2 region wall crossing is too close to the spawn candidate')
    offset = [v/length*candidate['capsule']['radius_cm']*4 for v in inward]
    start = [xy[i]+offset[i] for i in range(2)]+[center[2]]
    end = [xy[i]-offset[i] for i in range(2)]+[center[2]]
    wall_query = support_sweep(u, world, candidate['capsule'], movement, start, end)
    hit = wall_query['hit']
    source.require(hit is not None and hit['component'] == support['component'] and not hit['initial_penetration']
                   and not hit['native_cmc_is_walkable'] and abs(hit['impact_normal'][2]) < .1,
                   'P2 region original wall does not block the native inside-to-outside Pawn query')
    top = next(row for row in spec['source_instances'] if row['role'] == 'top')
    begin, end = top['vertex_range']
    top_z = max(p[2] for p in vertices[begin:end])
    roof_end = center[:2]+[top_z+candidate['capsule']['half_height_cm']*3]
    roof_query = support_sweep(u, world, candidate['capsule'], movement, center, roof_end)
    hit = roof_query['hit']
    source.require(hit is not None and hit['component'] == support['component'] and not hit['initial_penetration']
                   and not hit['native_cmc_is_walkable'] and hit['impact_normal'][2] < -.7,
                   'P2 region original downward top does not block the native upward Pawn query')
    return {'inside_to_outside_wall': wall_query, 'inside_upward_top': roof_query,
            'actual_cmc_edge_traversal_verified': False}


def support_asset_resume(spec, preflight, before_file, failed_path):
    """只接收地图未提交且已清理的真实失败；包内容仍由原生读回验证。"""
    failed_path = Path(failed_path).resolve()
    source.require(failed_path.is_relative_to(source.PROJECT/'Saved'), 'PawnSupport resume report is outside Saved')
    failed = source.read_json(failed_path)
    admissible = (failed.get('mode') == 'pawn_support' and failed.get('phase') == 'failed'
                   and failed.get('failure_phase') in ('pawn_support_asset', 'pawn_support_spawn_queries')
                   and failed.get('cleanup_errors') == []) or (failed.get('mode') == 'pawn_support_asset_repair'
                   and failed.get('phase') == 'pawn_support_asset_repair_passed')
    source.require(admissible
                   and failed.get('map_saved') is False and not failed.get('map_save_attempted')
                   and failed.get('saved_assets') == [spec['package']]
                   and failed.get('support_spec') == spec
                   and failed.get('plan_digest') == preflight['plan_digest']
                   and failed.get('settings_digest') == preflight['settings_digest']
                   and failed.get('map_before') == before_file
                   and failed.get('source_scene_baseline') == preflight['source_scene_baseline']
                   and failed.get('protected_packages') == preflight['protected_packages']
                   and failed.get('native_source_topology') == json.loads(json.dumps(preflight['native_source_topology'])),
                   'PawnSupport resume checkpoint is failed/foreign or has a map commit/cleanup risk')
    source.require(failed.get('support_package') == source.evidence(package_file(spec['package'])),
                   'PawnSupport resume saved package changed')
    return failed, source.evidence(failed_path)


def repair_support_asset(u, plan, settings, result, preflight_path, failed_path, environment_result,
                         p1_source_manifest, map_sha, asset_backup):
    """仅修正确切 P1 自有失败包的绕序；原始索引、坐标和失败证据保留。"""
    source.require(plan['stage'] == 'P1' and all(v is not None for v in
                   (preflight_path, failed_path, environment_result, p1_source_manifest, map_sha, asset_backup)),
                   'PawnSupport winding repair requires its exact P1 source/failure/map/backup inputs')
    spec = source.pawn_support_spec(plan, p1_source_manifest)
    legacy = {k: v for k, v in spec.items() if k not in ('native_winding_policy', 'native_triangles')}
    preflight = source.read_json(preflight_path)
    before = source.evidence(package_file(plan['map'], '.umap'))
    source.require(preflight['phase'] == 'pawn_support_preflight_passed' and preflight['support_spec'] == legacy
                   and before == preflight['protected_packages'][plan['map']] and before['sha256'].lower() == map_sha.lower(),
                   'PawnSupport winding repair source preflight/map baseline differs')
    failed, failed_evidence = support_asset_resume(legacy, preflight, before, failed_path)
    package = source.evidence(package_file(spec['package']))
    backup = Path(asset_backup).resolve()
    source.require(package['sha256'] == 'd22893c25e3944f6050f1511529625936312de6ec02b69727464fa05e1d4c1a7'
                   and backup.is_relative_to(source.PROJECT/'Saved') and backup.is_file()
                   and source.evidence(backup)['sha256'] == package['sha256'],
                   'PawnSupport winding repair exact owned failed package/backup differs')
    read_environment(u, plan, settings, result, environment_result, True)
    source.require(map_geometry_state(u) == preflight['source_scene_baseline'], 'PawnSupport winding repair source scene changed')
    mesh = verify_support_asset(u, legacy, preflight['native_source_topology'])
    body = mesh.get_editor_property('BodySetup')
    source.require(not body.get_editor_property('double_sided_geometry'), 'PawnSupport failed asset is unexpectedly double-sided')
    result.update(support_spec=spec, source_scene_baseline=preflight['source_scene_baseline'],
                  protected_packages=preflight['protected_packages'], map_before=before,
                  asset_before=package, asset_backup=source.evidence(backup), original_failure=failed_evidence)
    dm, topology = support_dynamic_mesh(u, spec)
    result['native_source_topology'] = topology
    result['phase'] = 'pawn_support_asset_winding'
    options = u.GeometryScriptCopyMeshToAssetOptions(enable_recompute_normals=True, enable_recompute_tangents=False,
        enable_remove_degenerates=False, replace_materials=False, use_original_vertex_order=True)
    value, outcome = u.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dm, mesh, options, u.GeometryScriptMeshWriteLOD(lod_index=0), False)
    source.require(value == dm and outcome == u.GeometryScriptOutcomePins.SUCCESS, 'PawnSupport native winding repair failed')
    u.EditorAssetLibrary.set_metadata_tag(mesh, 'BH3.PawnSupport.SourceSpec', source.digest(spec))
    verify_support_asset(u, spec, topology)
    source.require(not mesh.get_editor_property('BodySetup').get_editor_property('double_sided_geometry'),
                   'PawnSupport winding repair changed sidedness')
    source.require(u.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False), 'PawnSupport exact winding asset save failed')
    result['saved_assets'].append(spec['package'])
    result['support_package'] = source.evidence(package_file(spec['package']))
    source.require(all(source.evidence(package_file(p, '.umap' if p == plan['map'] else '.uasset')) == ev
                       for p, ev in preflight['protected_packages'].items())
                   and map_geometry_state(u) == preflight['source_scene_baseline']
                   and not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                   and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
                   'PawnSupport winding repair changed source/map or left dirty packages')
    result['original_camera_preserved'] = True


def apply_pawn_support(u, plan, settings, result, preflight_path, environment_result, map_sha, backup_path, p1_source_manifest=None,
                       asset_result=None):
    """一个派生包和一个地图提交；失败只清理本次 Actor，原件不保存或替换。"""
    source.require(plan['stage'] != 'P1' or p1_source_manifest is not None, 'P1 production needs its selected P2 source closure')
    source.require(preflight_path is not None and backup_path is not None and map_sha is not None,
                   'PawnSupport apply needs its exact preflight/map backup/SHA')
    preflight = source.read_json(preflight_path)
    spec = source.pawn_support_spec(plan, p1_source_manifest)
    source.require(preflight['phase'] == 'pawn_support_preflight_passed'
                   and preflight['plan_digest'] == plan['digest'] and preflight['settings_digest'] == source.digest(settings)
                   and preflight['support_spec'] == spec and preflight['original_camera_preserved']
                   and not preflight['map_saved'] and not preflight['saved_assets'] and not preflight['created_actors'],
                   'PawnSupport apply preflight is failed/foreign')
    map_file = package_file(plan['map'], '.umap')
    before_file = source.evidence(map_file)
    backup = Path(backup_path).resolve()
    source.require(before_file == preflight['protected_packages'][plan['map']]
                   and before_file['sha256'].lower() == map_sha.lower()
                   and backup.is_relative_to(source.PROJECT/'Saved') and backup.is_file()
                   and source.evidence(backup)['sha256'] == before_file['sha256'],
                   'PawnSupport map baseline/backup differs')
    resume = support_asset_resume(spec, preflight, before_file, asset_result) if asset_result is not None else None
    if resume is None:
        source.require(not package_file(spec['package']).exists() and not u.EditorAssetLibrary.does_asset_exist(spec['package']),
                       'PawnSupport create-only package exists')
    read_environment(u, plan, settings, result, environment_result, True)
    world, actors, _ = loaded_stage_actors(u, plan)
    baseline = map_geometry_state(u)
    source.require(baseline == preflight['source_scene_baseline'], 'PawnSupport preflight source scene changed')
    player_config, player_movements = support_player_configuration(u, world, plan)
    source.require(player_config == preflight['player_configuration'] and player_config['default_roster']
                   and not player_config['player_starts'], 'PawnSupport player configuration/PlayerStart differs')
    result.update(support_spec=spec, source_scene_baseline=baseline, map_before=before_file,
                  map_backup=source.evidence(backup), preflight=source.evidence(preflight_path),
                  protected_packages=preflight['protected_packages'], player_configuration=player_config,
                  actual_cmc_landing_verified=False, legal_spawn_verified=False)
    dm, topology = support_dynamic_mesh(u, spec)
    source.require(json.loads(json.dumps(topology)) == preflight['native_source_topology'],
                   'PawnSupport original topology differs from native preflight')
    result['native_source_topology'] = topology
    created = []
    try:
        result['phase'] = 'pawn_support_asset'
        if resume is not None:
            mesh = verify_support_asset(u, spec, topology)
            result.update(asset_resume_result=resume[1], reused_assets=[spec['package']])
        else:
            options = u.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=True,
                enable_recompute_tangents=False, enable_nanite=False, enable_collision=True,
                collision_mode=u.CollisionTraceFlag.CTF_USE_COMPLEX_AS_SIMPLE, use_original_vertex_order=True)
            mesh, outcome = u.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm, spec['package'], options)
            source.require(mesh is not None and outcome == u.GeometryScriptOutcomePins.SUCCESS
                           and mesh.get_path_name() == spec['package']+'.'+spec['package'].rsplit('/', 1)[1],
                           'PawnSupport native create-only asset failed')
            for key, value in {'Owner': spec['owner'], 'SourceSpec': source.digest(spec), 'Policy': spec['policy'],
                               'CameraPolicy': spec['camera_policy']}.items():
                u.EditorAssetLibrary.set_metadata_tag(mesh, 'BH3.PawnSupport.'+key, value)
            verify_support_asset(u, spec, topology)
            source.require(u.EditorAssetLibrary.save_loaded_asset(mesh, only_if_is_dirty=False), 'PawnSupport exact asset save failed')
            result['saved_assets'].append(spec['package'])
        result['support_package'] = source.evidence(package_file(spec['package']))
        source.require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages(), 'PawnSupport asset save left dirty content')
        editor = u.get_editor_subsystem(u.EditorActorSubsystem)
        support_actor = editor.spawn_actor_from_class(u.StaticMeshActor, u.Vector(0, 0, 0), u.Rotator(0, 0, 0), False)
        source.require(support_actor is not None, 'PawnSupport native Actor creation failed')
        created.append(support_actor)
        support_actor.set_actor_label('BH3_'+plan['stage']+'_PawnSupport')
        support_actor.set_editor_property('tags', [spec['owner'], source.digest(spec), plan['digest'], 'PawnQuery'])
        source.require(support_actor.attach_to_actor(actors[spec['source_model']], '', u.AttachmentRule.KEEP_RELATIVE,
                       u.AttachmentRule.KEEP_RELATIVE, u.AttachmentRule.KEEP_RELATIVE, False), 'PawnSupport attachment failed')
        support_actor.set_actor_relative_transform(ue_pose(u, {'translation': [0., 0., 0.],
                     'quaternion': [0., 0., 0., 1.], 'scale': [1., 1., 1.]}), False, False)
        support_actor.set_actor_hidden_in_game(True)
        support_actor.set_actor_enable_collision(True)
        comp = support_actor.get_component_by_class(u.StaticMeshComponent)
        source.require(comp.set_static_mesh(mesh), 'PawnSupport mesh assignment failed')
        configure_support_component(u, comp)
        result['support_contract_readback'] = {}
        result['support_actor'] = support_actor_state(u, support_actor, spec, result['support_contract_readback'])
        result['phase'] = 'pawn_support_spawn_queries'
        bounds = preflight['floor_query_bounds_cm']
        center = [(bounds['min'][i]+bounds['max'][i])*.5 for i in range(2)]
        player = player_config['default_roster'][0]['capsule']
        definition = None
        boss = None
        if plan['stage'] == 'P3':
            definition_path = '/Game/Characters/Boss/Kevin/DemonBattle/Data/DA_Boss_Kevin_DemonBattle'
            definition = exact_asset(u, definition_path, 'GGYGOBossDefinition')
            boss_class = u.EditorAssetLibrary.load_blueprint_class('/Game/Characters/Boss/Kevin/DemonBattle/Blueprints/BP_Kevin_DemonBattle')
            boss_movement, boss = support_capsule_cdo(u, boss_class)
        separation = (player['radius_cm']+boss['radius_cm'])*4 if boss is not None else 0.
        result['native_spawn_queries'] = {'player': {}}
        player_candidate = support_spawn_candidate(u, world, result['support_actor'], player, player_movements[0],
                                                  [center[0]-separation, center[1]], bounds, result['native_spawn_queries']['player'])
        result['player_spawn_candidate'] = player_candidate
        if plan['stage'] == 'P1':
            result['native_region_boundary_queries'] = support_region_boundary_queries(
                u, world, spec, result['support_actor'], player_candidate, player_movements[0])
        spawn_points = [(u.PlayerStart, 'BH3_'+plan['stage']+'_PlayerStart', 'PlayerStart', player_candidate)]
        if boss is not None:
            result['native_spawn_queries']['boss'] = {}
            boss_candidate = support_spawn_candidate(u, world, result['support_actor'], boss, boss_movement,
                                                    [center[0]+separation, center[1]], bounds, result['native_spawn_queries']['boss'])
            result['boss_spawn_candidate'] = boss_candidate
            spawn_points.append((u.GGYGOBossEncounter, 'BH3_P3_KevinEncounter', 'KevinEncounter', boss_candidate))
        for cls, label, kind, candidate in spawn_points:
            actor = editor.spawn_actor_from_class(cls, u.Vector(*candidate['location_cm']), u.Rotator(0, 0, 0), False)
            source.require(actor is not None, 'PawnSupport native spawn point creation failed: '+kind)
            created.append(actor)
            actor.set_actor_label(label)
            actor.set_editor_property('tags', [spec['owner'], source.digest(spec), plan['digest'], kind])
            if kind == 'KevinEncounter':
                actor.set_editor_property('BossDefinition', definition)
                actor.set_editor_property('bSpawnOnBeginPlay', True)
                actor.set_editor_property('EncounterSeed', 1337)
            result[kind] = {'actor': actor.get_path_name(), 'class': actor.get_class().get_path_name(),
                            'world_pose': pose_of(actor.get_actor_transform()), 'tags': [str(t) for t in actor.get_editor_property('tags')]}
        result['created_actors'] = [a.get_path_name() for a in created]
        preserved_environment_state(u, baseline, result['created_actors'])
        source.require(all(source.evidence(package_file(p)) == ev for p, ev in preflight['protected_packages'].items()
                           if p != plan['map']), 'PawnSupport changed original source/Camera assets')
        levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        source.require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                       and all(p == world.get_outer() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
                       'PawnSupport map commit has foreign dirty packages')
        result['phase'] = 'pawn_support_map_commit'
        result['map_save_attempted'] = True
        result['map_saved'] = bool(levels.save_current_level())
        source.require(result['map_saved'] and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
                       'PawnSupport exact map save failed')
        result['map_file'] = source.evidence(map_file)
        result['original_camera_preserved'] = True
    except Exception:
        result['created_actors'] = [a.get_path_name() for a in created]
        result['cleanup_errors'] = []
        for actor in reversed(created):
            try:
                source.require(u.get_editor_subsystem(u.EditorActorSubsystem).destroy_actor(actor),
                               'PawnSupport owned Actor cleanup refused')
            except Exception as cleanup_error:
                result['cleanup_errors'].append(str(cleanup_error))
        preserved_environment_state(u, baseline, [])
        raise


def load_support_checkpoint(u, plan, settings, result, applied_path, p1_source_manifest=None, collision_repair=False,
                            visibility_repair=False):
    """验证提交身份和全部原件；显式修正入口只放开自有组件的目标字段。"""
    source.require(applied_path is not None, 'PawnSupport cold read needs its saved apply result')
    applied = source.read_json(applied_path)
    source.require(plan['stage'] != 'P1' or p1_source_manifest is not None, 'P1 support read needs its selected P2 source manifest')
    spec = source.pawn_support_spec(plan, p1_source_manifest)
    source.require(applied['phase'] in ('pawn_support_passed', 'pawn_support_collision_passed', 'pawn_support_visibility_passed') and applied['map_saved']
                   and applied['support_spec'] == spec and applied['plan_digest'] == plan['digest']
                   and applied['settings_digest'] == source.digest(settings)
                   and applied['map_file'] == source.evidence(package_file(plan['map'], '.umap'))
                   and applied['support_package'] == source.evidence(package_file(spec['package'])),
                   'PawnSupport cold read apply checkpoint is stale/failed/foreign')
    verify_assets(u, plan, settings)
    verify_map(u, plan, settings, True, True)
    world, actors, all_actors = loaded_stage_actors(u, plan)
    owned = applied['created_actors'] if applied['phase'] == 'pawn_support_passed' else applied['owned_actors']
    preserved_environment_state(u, applied['source_scene_baseline'], owned)
    mesh = verify_support_asset(u, spec, applied['native_source_topology'])
    actor = all_actors.get(applied['support_actor']['actor'])
    source.require(actor is not None, 'PawnSupport saved owned Actor is missing')
    result['support_contract_readback'] = {}
    state = support_actor_state(u, actor, spec, result['support_contract_readback'], require_collision=not collision_repair,
                                require_hidden_render=not (collision_repair or visibility_repair))
    expected = applied['support_actor']
    source.require(({k: v for k, v in state.items() if k != 'body_instance'} ==
                    {k: v for k, v in expected.items() if k != 'body_instance'}) if collision_repair else state == expected,
                   'PawnSupport saved owned Actor state differs')
    for kind in (('PlayerStart', 'KevinEncounter') if plan['stage'] == 'P3' else ('PlayerStart',)):
        saved = applied[kind]
        point = all_actors.get(saved['actor'])
        source.require(point is not None and point.get_class().get_path_name() == saved['class']
                       and pose_of(point.get_actor_transform()) == saved['world_pose']
                       and [str(t) for t in point.get_editor_property('tags')] == saved['tags'],
                       'PawnSupport saved spawn point differs: '+kind)
        if kind == 'KevinEncounter':
            source.require(object_path(point.get_editor_property('BossDefinition')) ==
                           '/Game/Characters/Boss/Kevin/DemonBattle/Data/DA_Boss_Kevin_DemonBattle.DA_Boss_Kevin_DemonBattle'
                           and point.get_editor_property('bSpawnOnBeginPlay') and point.get_editor_property('EncounterSeed') == 1337,
                           'PawnSupport saved Encounter properties differ')
    for package, ev in applied['protected_packages'].items():
        if package != plan['map']:
            source.require(source.evidence(package_file(package)) == ev, 'PawnSupport original source/Camera package changed')
    player_config, movements = support_player_configuration(u, world, plan)
    original_config = {k: v for k, v in applied['player_configuration'].items() if k != 'player_starts'}
    source.require({k: v for k, v in player_config.items() if k != 'player_starts'} == original_config
                   and len(player_config['player_starts']) == 1
                   and player_config['player_starts'][0]['actor'] == applied['PlayerStart']['actor'],
                   'PawnSupport cold read selected player configuration/PlayerStart differs')
    preflight = source.read_json(applied['preflight']['path'])
    source.require(source.evidence(applied['preflight']['path']) == applied['preflight'],
                   'PawnSupport original native preflight evidence changed')
    return {'world': world, 'actors': actors, 'actor': actor, 'spec': spec, 'applied': applied, 'owned': owned,
            'player_configuration': player_config, 'movements': movements, 'preflight': preflight}


def query_support_checkpoint(u, plan, result, context):
    """在已验证的同次提交上复用真实胶囊查询，不另建角色执行链。"""
    world, actors, spec, applied = (context[k] for k in ('world', 'actors', 'spec', 'applied'))
    player_config, movements, preflight = (context[k] for k in ('player_configuration', 'movements', 'preflight'))
    result['cold_native_spawn_queries'] = {}
    candidates = [('player_spawn_candidate', player_config['default_roster'][0]['capsule'], movements[0])]
    if plan['stage'] == 'P3':
        boss_class = u.EditorAssetLibrary.load_blueprint_class('/Game/Characters/Boss/Kevin/DemonBattle/Blueprints/BP_Kevin_DemonBattle')
        boss_movement, boss_capsule = support_capsule_cdo(u, boss_class)
        candidates.append(('boss_spawn_candidate', boss_capsule, boss_movement))
    for key, capsule, movement in candidates:
        previous = applied[key]
        source.require(capsule == previous['capsule'], 'PawnSupport queried original capsule changed: '+key)
        current = support_spawn_candidate(u, world, applied['support_actor'], capsule, movement,
                                          previous['location_cm'][:2], preflight['floor_query_bounds_cm'])
        source.require(max(abs(a-b) for a, b in zip(current['location_cm'], previous['location_cm'])) < .02,
                       'PawnSupport cold native queried spawn contact differs: '+key)
        result['cold_native_spawn_queries'][key] = current
    if plan['stage'] == 'P1':
        result['native_region_boundary_queries'] = support_region_boundary_queries(
            u, world, spec, applied['support_actor'], result['cold_native_spawn_queries']['player_spawn_candidate'], movements[0])
        result['native_visible_surface_check'] = support_visible_surface_check(u, plan, spec, actors)


def read_pawn_support(u, plan, settings, result, applied_path, p1_source_manifest=None):
    """新进程读取真实支持包、出生点和原件保护；不重复保存。"""
    context = load_support_checkpoint(u, plan, settings, result, applied_path, p1_source_manifest)
    applied = context['applied']
    query_support_checkpoint(u, plan, result, context)
    source.require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                   and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(), 'PawnSupport cold read left dirty packages')
    result.update(apply_result=source.evidence(applied_path), support_actor=applied['support_actor'],
                  PlayerStart=applied['PlayerStart'],
                  map_file=applied['map_file'], support_package=applied['support_package'],
                  original_camera_preserved=True, actual_cmc_landing_verified=False, legal_spawn_verified=False)
    if plan['stage'] == 'P3':result['KevinEncounter'] = applied['KevinEncounter']
    return applied


def repair_support_component(u, plan, settings, result, applied_path, map_sha, backup_path, p1_source_manifest=None,
                             repair_kind='collision'):
    """消费确切已保存提交，显式修正自有组件的碰撞模式或渲染遗漏。"""
    source.require(repair_kind in ('collision', 'visibility'), 'PawnSupport component repair kind is invalid')
    source.require(map_sha is not None and backup_path is not None, 'PawnSupport component repair needs exact map SHA/backup')
    context = load_support_checkpoint(u, plan, settings, result, applied_path, p1_source_manifest,
                                      collision_repair=repair_kind == 'collision', visibility_repair=repair_kind == 'visibility')
    applied, actor, world = (context[k] for k in ('applied', 'actor', 'world'))
    before = source.evidence(package_file(plan['map'], '.umap'))
    backup = Path(backup_path).resolve()
    source.require(before['sha256'].lower() == map_sha.lower() and backup.is_relative_to(source.PROJECT/'Saved')
                   and backup.is_file() and source.evidence(backup)['sha256'] == before['sha256'],
                   'PawnSupport component repair map baseline/backup differs')
    comp = actor.get_component_by_class(u.StaticMeshComponent)
    if repair_kind == 'collision':
        source.require(comp.get_editor_property('use_default_collision')
                       and comp.get_collision_enabled() == u.CollisionEnabled.QUERY_AND_PHYSICS
                       and comp.get_collision_response_to_channel(u.CollisionChannel.ECC_PAWN) == u.CollisionResponseType.ECR_BLOCK
                       and comp.get_collision_response_to_channel(u.CollisionChannel.ECC_CAMERA) == u.CollisionResponseType.ECR_BLOCK,
                       'PawnSupport collision repair does not match the reproduced asset-default override')
    else:
        source.require(comp.get_editor_property('visible') and not comp.get_editor_property('hidden_in_game'),
                       'PawnSupport visibility repair does not match the reproduced rendering omission')
    result['render_before'] = {'visible': bool(comp.get_editor_property('visible')),
                               'hidden_in_game': bool(comp.get_editor_property('hidden_in_game'))}
    result['phase'] = 'pawn_support_'+repair_kind+'_configuration'
    actor.modify()
    comp.modify()
    configure_support_component(u, comp)
    context['applied'] = dict(applied, support_actor=support_actor_state(u, actor, context['spec']))
    source.require(repair_kind != 'visibility' or context['applied']['support_actor'] == applied['support_actor'],
                   'PawnSupport visibility repair changed collision, attachment or owned Actor identity')
    result['support_contract_readback'] = {}
    support_actor_state(u, actor, context['spec'], result['support_contract_readback'])
    query_support_checkpoint(u, plan, result, context)
    preserved_environment_state(u, applied['source_scene_baseline'], context['owned'])
    source.require(all(source.evidence(package_file(p)) == ev for p, ev in applied['protected_packages'].items()
                       if p != plan['map']) and source.evidence(package_file(context['spec']['package'])) == applied['support_package'],
                   'PawnSupport component repair changed an original or owned mesh package')
    source.require(not u.EditorLoadingAndSavingUtils.get_dirty_content_packages()
                   and all(p == world.get_outer() for p in u.EditorLoadingAndSavingUtils.get_dirty_map_packages()),
                   'PawnSupport component repair has foreign dirty packages')
    result.update(previous_apply_result=source.evidence(applied_path), map_before=before, map_backup=source.evidence(backup))
    result['phase'] = 'pawn_support_'+repair_kind+'_map_commit'
    result['map_save_attempted'] = True
    result['map_saved'] = bool(u.get_editor_subsystem(u.LevelEditorSubsystem).save_current_level())
    source.require(result['map_saved'] and not u.EditorLoadingAndSavingUtils.get_dirty_map_packages(),
                   'PawnSupport component repair exact map save failed')
    for key in ('support_spec', 'source_scene_baseline', 'protected_packages', 'native_source_topology',
                'player_configuration', 'preflight', 'support_package', 'PlayerStart', 'player_spawn_candidate'):
        result[key] = applied[key]
    if plan['stage'] == 'P3':
        for key in ('KevinEncounter', 'boss_spawn_candidate'):result[key] = applied[key]
    result.update(owned_actors=context['owned'], support_actor=context['applied']['support_actor'],
                  map_file=source.evidence(package_file(plan['map'], '.umap')), original_camera_preserved=True,
                  actual_cmc_landing_verified=False, legal_spawn_verified=False)


class StageSupportPlay:
    """有限 PIE 验证宿主；实际装配/输入/地面仍由原 GameMode、Hero 与 CMC 执行。"""
    def __init__(self, u, plan, settings, result, applied, output, image, standby_sha):
        self.u, self.plan, self.result, self.applied, self.output = u, plan, result, applied, output
        self.editor = u.get_editor_subsystem(u.UnrealEditorSubsystem)
        self.levels = u.get_editor_subsystem(u.LevelEditorSubsystem)
        self.baseline = map_geometry_state(u)
        self.image = Path(image).resolve()
        source.require(self.image.is_relative_to(source.PROJECT/'Saved') and self.image.suffix == '.png'
                       and not self.image.exists(), 'PawnSupport PIE screenshot must be a fresh Saved PNG')
        self.handle = self.world = self.pc = self.pawn = self.boss = self.encounter = self.input = self.action = self.task = None
        self.standby = None
        self.finished = self.advancing = False
        self.stage = 'bind'
        self.started = time.monotonic()
        self.game_stage_start = self.grounded_since = None
        self.error = None
        self.standby_api = None
        if plan['stage'] == 'P3':
            observer = SCRIPT_DIR/'observe_bh3_kevin_combat.py'
            source.require(standby_sha is not None and source.evidence(observer)['sha256'].lower() == standby_sha.lower(),
                           'PawnSupport PIE needs the exact frozen Boss observer tool')
            self.standby_api = runpy.run_path(str(observer))
            source.require(callable(self.standby_api.get('start_standby')), 'PawnSupport public Boss standby observer is unavailable')
        self.result.update(pie_requested=False, pie_started=False, samples=[], input_injection='original EnhancedInput IA_Move, finite action values',
                           physical_keyboard_verified=False, actual_cmc_landing_verified=False,
                           runtime_game_feature_session_verified=False, legal_spawn_verified=False)
        source.require(not self.levels.is_in_play_in_editor(), 'PawnSupport PIE observer refuses another existing PIE')
        try:
            self.u.EditorPythonScripting.set_keep_python_script_alive(True)
            self.handle = self.u.register_slate_post_tick_callback(self.tick)
            source.require(self.handle is not None, 'PawnSupport PIE callback registration failed')
            self.result['pie_requested'] = True
            self.levels.editor_request_begin_play()
        except Exception:
            if self.handle is not None:
                self.u.unregister_slate_post_tick_callback(self.handle)
            self.u.EditorPythonScripting.set_keep_python_script_alive(False)
            raise

    @staticmethod
    def source_path(obj):
        return re.sub(r'UEDPIE_\d+_', '', object_path(obj)) if obj is not None else None

    def ground_sample(self, pawn):
        u = self.u
        movement = pawn.get_editor_property('CharacterMovement')
        capsule = pawn.get_editor_property('CapsuleComponent')
        floor = movement.get_editor_property('CurrentFloor')
        hit = floor.get_editor_property('HitResult')
        fields = hit.to_tuple()
        source.require(len(fields) == 18, 'PawnSupport PIE native CurrentFloor HitResult signature differs')
        gravity = float(movement.get_editor_property('GravityScale'))
        direction = movement.get_gravity_direction()
        source.require(math.isfinite(gravity) and gravity > 0 and [direction.x, direction.y, direction.z] == [0., 0., -1.],
                       'PawnSupport PIE normal gravity changed')
        location, velocity = pawn.get_actor_location(), pawn.get_velocity()
        actual_capsule = {'radius_cm': float(capsule.get_scaled_capsule_radius()),
                          'half_height_cm': float(capsule.get_scaled_capsule_half_height()),
                          'profile': str(capsule.get_collision_profile_name())}
        current_position = [location.x, location.y, location.z]
        clearance = support_sweep(u, self.world, actual_capsule, movement,
                                  current_position, current_position, ignored_actors=[pawn])
        extension = pawn.get_component_by_class(u.GGYGOPawnExtensionComponent)
        asc = extension.get_ggygo_ability_system_component() if extension is not None else None
        grounded = bool(movement.is_moving_on_ground())
        exact_floor = grounded and bool(floor.get_editor_property('bBlockingHit')) and bool(floor.get_editor_property('bWalkableFloor')) \
                      and fields[0] and not fields[1] and self.source_path(fields[10]) == self.applied['support_actor']['component'] \
                      and bool(movement.is_walkable(hit))
        return {'pawn': pawn.get_path_name(), 'class': pawn.get_class().get_path_name(), 'ready_asc': object_path(asc),
                'pawn_data': object_path(extension.get_editor_property('PawnData')) if extension else None,
                'location_cm': [location.x, location.y, location.z], 'velocity_cm_s': [velocity.x, velocity.y, velocity.z],
                'radius_cm': actual_capsule['radius_cm'], 'half_height_cm': actual_capsule['half_height_cm'],
                'capsule_clearance_free': clearance['hit'] is None, 'capsule_clearance_query': clearance,
                'gravity_scale': gravity, 'movement_mode': str(movement.get_editor_property('MovementMode')),
                'moving_on_ground': grounded, 'exact_owned_walkable_floor': bool(exact_floor),
                'floor_component': object_path(fields[10]), 'floor_distance_cm': float(floor.get_editor_property('FloorDist')),
                'floor_native_text': floor.export_text()}

    def bind(self):
        u = self.u
        world = self.editor.get_game_world()
        if world is None:
            return False
        source.require(self.source_path(world).split('.')[0] == self.plan['map'], 'PawnSupport PIE world differs')
        if self.world is None:
            self.world = world
            self.result['pie_started'] = True
        source.require(world == self.world, 'PawnSupport original PIE world was replaced')
        pc = u.GameplayStatics.get_player_controller(world, 0)
        if pc is None or pc.get_controlled_pawn() is None:
            return False
        pawn = pc.get_controlled_pawn()
        source.require(pawn.get_controller() == pc and pawn.has_authority(), 'PawnSupport native possession/authority differs')
        sample = self.ground_sample(pawn)
        if sample['ready_asc'] is None:
            return False
        candidate = self.applied['player_configuration']['default_roster'][0]
        source.require(sample['pawn_data'] == candidate['pawn_data'] and sample['class'] == candidate['capsule']['class'],
                       'PawnSupport runtime selected player differs from queried spawn configuration')
        game_mode = u.GameplayStatics.get_game_mode(world)
        source.require(game_mode is not None and object_path(game_mode.get_experience()) ==
                       self.applied['player_configuration']['experience'], 'PawnSupport runtime Experience differs')
        boss, boss_sample = None, None
        if self.plan['stage'] == 'P3':
            encounters = u.GameplayStatics.get_all_actors_of_class(world, u.GGYGOBossEncounter)
            selected = [a for a in encounters if self.source_path(a) == self.applied['KevinEncounter']['actor']]
            source.require(len(selected) == 1, 'PawnSupport runtime exact Encounter is missing/ambiguous')
            self.encounter = selected[0]
            boss = self.encounter.get_boss_avatar()
            if boss is None:
                return False
            boss_sample = self.ground_sample(boss)
            if boss_sample['ready_asc'] is None:
                return False
        self.pc, self.pawn, self.boss = pc, pawn, boss
        # 内部蓝图库不生成 Python 类型；直接消费其原生反射 getter，不读取 Controller 私有 Player。
        library = u.load_object(None, '/Script/Engine.Default__SubsystemBlueprintLibrary')
        source.require(library is not None, 'PawnSupport native local-player subsystem getter object is missing')
        self.input = library.call_method('GetLocalPlayerSubSystemFromPlayerController', (pc, u.EnhancedInputLocalPlayerSubsystem))
        source.require(isinstance(self.input, u.EnhancedInputLocalPlayerSubsystem),
                       'PawnSupport actual Controller has no native EnhancedInput local-player subsystem')
        input_config = u.load_asset(candidate['InputConfig'])
        native = list(input_config.get_editor_property('NativeInputActions'))
        actions = [a.get_editor_property('InputAction') for a in native
                   if 'InputTag.Move' in a.get_editor_property('InputTag').export_text()]
        source.require(len(actions) == 1 and actions[0] is not None, 'PawnSupport actual IA_Move is missing/ambiguous')
        self.action = actions[0]
        support = [a for a in u.GameplayStatics.get_all_actors_of_class(world, u.StaticMeshActor)
                   if self.source_path(a) == self.applied['support_actor']['actor']]
        source.require(len(support) == 1, 'PawnSupport runtime exact owned support Actor is missing/ambiguous')
        support_component = support[0].get_component_by_class(u.StaticMeshComponent)
        source.require(self.source_path(support_component) == self.applied['support_actor']['component'],
                       'PawnSupport runtime support component differs')
        if self.plan['stage'] == 'P3':
            self.standby = self.standby_api['start_standby'](self.encounter, support_component, label='P3_StandBy', seconds=8.)
            self.standby_started = time.monotonic()
        self.result.update(world=world.get_path_name(), player_controller=pc.get_path_name(), player=sample,
                           boss=boss_sample, encounter=object_path(self.encounter), input_action=object_path(self.action),
                           runtime_experience=object_path(game_mode.get_experience()),
                           runtime_game_mode_spawn_admission_observed=True)
        return True

    def tick(self, _delta):
        if self.finished or self.advancing:
            return
        self.advancing = True
        try:
            if self.stage == 'end':
                if not self.levels.is_in_play_in_editor() and self.editor.get_game_world() is None:
                    self.finish()
                elif time.monotonic()-self.end_requested > 15:
                    self.error = self.error or RuntimeError('PawnSupport native End PIE exceeded 15 seconds')
                    self.finish()
                return
            source.require(time.monotonic()-self.started < 60, 'PawnSupport finite PIE observation exceeded 60 seconds')
            if self.stage == 'bind':
                if not self.bind():
                    return
                self.stage = 'ground'
            source.require(self.editor.get_game_world() == self.world and self.pc.get_controlled_pawn() == self.pawn
                           and (self.encounter is None or self.encounter.get_boss_avatar() == self.boss), 'PawnSupport observed native ownership changed')
            now = self.u.GameplayStatics.get_time_seconds(self.world)
            player = self.ground_sample(self.pawn)
            boss = self.ground_sample(self.boss) if self.boss is not None else None
            self.result['samples'].append({'game_seconds': now, 'stage': self.stage, 'player': player, 'boss': boss})
            both_grounded = player['exact_owned_walkable_floor'] and player['capsule_clearance_free'] \
                            and (boss is None or boss['exact_owned_walkable_floor'] and boss['capsule_clearance_free'])
            if self.stage == 'ground':
                if not both_grounded:
                    self.grounded_since = None
                    return
                self.grounded_since = now if self.grounded_since is None else self.grounded_since
                if now-self.grounded_since < .5:
                    return
                self.start_location = player['location_cm']
                self.result['grounding_observed'] = True
                self.game_stage_start = now
                self.stage = 'move'
            if self.stage == 'move':
                source.require(both_grounded, 'PawnSupport actual CMC lost the owned floor during finite movement')
                if now-self.game_stage_start < .35:
                    self.input.inject_input_vector_for_action(self.action, self.u.Vector(0., .4, 0.), [], [])
                    return
                self.input.inject_input_vector_for_action(self.action, self.u.Vector(0., 0., 0.), [], [])
                self.stage, self.game_stage_start = 'settle', now
            if self.stage == 'settle':
                source.require(both_grounded, 'PawnSupport actual CMC lost the owned floor after input release')
                if now-self.game_stage_start < .6:
                    return
                distance = math.hypot(*(player['location_cm'][i]-self.start_location[i] for i in range(2)))
                self.result.update(finite_input_displacement_cm=distance, player=player, boss=boss)
                try:
                    source.require(distance > 1., 'PawnSupport original IA_Move produced no finite CMC displacement')
                except source.SourceError as exc:
                    # 原移动断言仍失败；额外保存该失败场景的原生图像，最终结果保持 failed。
                    self.error = exc
                else:
                    self.result.update(actual_cmc_landing_verified=True, legal_spawn_verified=True)
                self.task = self.u.AutomationLibrary.take_high_res_screenshot(1280, 720, self.image.as_posix(),
                    camera=None, mask_enabled=False, capture_hdr=False, delay=0., force_game_view=False)
                source.require(self.task is not None and self.task.is_valid_task(), 'PawnSupport native PIE screenshot refused')
                self.stage = 'capture'
            if self.stage == 'capture' and self.task.is_task_done() and self.image.is_file():
                source.require(self.image.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n', 'PawnSupport PIE capture is not PNG')
                self.result['image'] = source.evidence(self.image)
                if self.standby is not None and time.monotonic()-self.standby_started < 8.:
                    return
                self.end()
        except Exception as exc:
            self.error = exc
            self.end()
        finally:
            self.advancing = False

    def end(self):
        if self.standby is not None:
            try:
                report = self.standby.stop(reason='stage_play_end')
                source.require(report.get('report_path') and Path(report['report_path']).is_file(),
                               'PawnSupport Boss observer did not write its native report')
                source.require(report.get('listeners_released') is True,
                               'PawnSupport Boss observer did not release its native listeners')
                self.result['standby_observation'] = source.evidence(report['report_path'])
            except Exception as exc:
                self.error = self.error or exc
            self.standby = None
        self.stage = 'end'
        self.end_requested = time.monotonic()
        self.levels.editor_request_end_play()

    def finish(self):
        self.finished = True
        cleanup = []
        try:
            if self.handle is not None:
                try:self.u.unregister_slate_post_tick_callback(self.handle)
                except Exception as exc:cleanup.append('PIE callback: '+str(exc))
                self.handle = None
            try:
                source.require(not self.levels.is_in_play_in_editor() and self.editor.get_game_world() is None,
                               'PawnSupport observer could not reclaim its own PIE')
                verify_geometry_state(map_geometry_state(self.u), self.baseline)
                source.require(source.evidence(package_file(self.plan['map'], '.umap')) == self.applied['map_file']
                               and source.evidence(package_file(self.applied['support_spec']['package'])) == self.applied['support_package']
                               and not self.u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
                               and not self.u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),
                               'PawnSupport PIE changed saved map/asset or left dirty packages')
            except Exception as exc:cleanup.append(str(exc))
            self.result.update(phase='failed' if self.error or cleanup else 'pawn_support_play_passed',
                               error=str(self.error) if self.error else None, cleanup_errors=cleanup,
                               standby_visual_verified=False, visual_verified=False)
            source.write_machine(self.output, self.result)
        finally:
            self.world = self.pc = self.pawn = self.boss = self.input = self.action = self.task = self.standby = None
            self.u.EditorPythonScripting.set_keep_python_script_alive(False)
            globals()['_stage_support_play'] = None


class StageCapture:
    """Bounded native viewport observer; restores its view and process settings."""
    def __init__(self,u,plan,settings,result,output,image,focus_model=None):
        self.u,self.plan,self.result,self.output=u,plan,result,output
        self.image=Path(image).resolve()
        source.require(self.image.is_relative_to(source.PROJECT/'Saved') and self.image.suffix.lower()=='.png'
                       and not self.image.exists(),'capture must be a fresh Saved PNG')
        self.baseline=map_geometry_state(u)
        self.task=self.handle=None;self.previous_view=None
        self.performance_settings=None;self.previous_throttle=None
        self.previous_selection=None
        self.actor_editor=u.get_editor_subsystem(u.EditorActorSubsystem)
        self.frames=0;self.advancing=False;self.finished=False;self.started=time.monotonic()
        self.editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        world,actors,_=map_actors(u,plan,True,False)
        self.world=world
        rows=[r for r in plan['renderers'] if source.component_enabled(r)
              and plan['shaders'][plan['materials'][r['materials'][0]]['shader']]['name'].endswith('/Scene_Base')]
        if focus_model is not None:
            rows=[r for r in rows if r['model']==focus_model]
            source.require(len(rows)==1,'capture focus is not one active source Scene_Base renderer: '+focus_model)
        bounds=[actors[r['model']].get_actor_bounds(False,False) for r in rows]
        source.require(bounds,'capture has no active source surface bounds')
        lo=[min(getattr(p,a)-getattr(e,a) for p,e in bounds) for a in ('x','y','z')]
        hi=[max(getattr(p,a)+getattr(e,a) for p,e in bounds) for a in ('x','y','z')]
        center=[(a+b)/2 for a,b in zip(lo,hi)]
        radius=math.sqrt(sum((b-a)**2 for a,b in zip(lo,hi)))/2
        source.require(math.isfinite(radius) and radius>1,'capture source bounds are invalid')
        distance=radius*2.4
        location=[v+distance*d for v,d in zip(center,(-.65,-.5,.57))]
        self.result['capture_view']={'source_bounds':[lo,hi],'location':location,'look_at':center,
                                     'purpose':'UE equivalent scene inspection; no original source camera is claimed'}
        if focus_model is not None:
            self.result['capture_view'].update(focus_model=focus_model,focus_source_path=rows[0]['source_path'],focus_actor=rows[0]['actor'])
        try:
            self.previous_selection=list(self.actor_editor.get_selected_level_actors())
            self.result['capture_selection']=[a.get_path_name() for a in self.previous_selection]
            self.performance_settings=u.load_object(None,'/Script/UnrealEd.Default__EditorPerformanceSettings')
            source.require(self.performance_settings is not None,'native Editor performance settings object is unavailable')
            self.previous_throttle=self.performance_settings.get_editor_property('bThrottleCPUWhenNotForeground')
            self.performance_settings.set_editor_property('bThrottleCPUWhenNotForeground',False)
            self.previous_view=self.editor.get_level_viewport_camera_info()
            source.require(self.previous_view is not None and len(self.previous_view)==2,'native level viewport camera is unavailable')
            point=u.Vector(*location)
            self.editor.set_level_viewport_camera_info(point,u.MathLibrary.find_look_at_rotation(point,u.Vector(*center)))
            u.EditorPythonScripting.set_keep_python_script_alive(True)
            self.handle=u.register_slate_post_tick_callback(self.tick)
            source.require(self.handle is not None,'native capture callback registration failed')
        except Exception as exc:
            self.finish(exc)

    def tick(self,delta):
        if self.advancing or self.finished:return
        self.advancing=True
        try:
            source.require(time.monotonic()-self.started<120,'native capture exceeded its deadline')
            self.frames+=1
            if self.frames>=12 and self.task is None:
                self.image.parent.mkdir(parents=True,exist_ok=True)
                self.task=self.u.AutomationLibrary.take_high_res_screenshot(1280,720,str(self.image))
                source.require(self.task is not None and self.task.is_valid_task(),'native viewport screenshot task failed to start')
            if self.task is not None and self.task.is_task_done() and self.image.is_file():
                source.require(self.image.read_bytes()[:8]==b'\x89PNG\r\n\x1a\n','native capture did not export a PNG')
                self.result['image']=source.evidence(self.image)
                self.finish(None)
        except Exception as exc:self.finish(exc)
        finally:self.advancing=False

    def finish(self,error):
        if self.finished:return
        self.finished=True
        cleanup=[]
        try:
            if self.handle is not None:
                try:self.u.unregister_slate_post_tick_callback(self.handle)
                except Exception as exc:cleanup.append('capture callback: '+str(exc))
                self.handle=None
            if self.task is not None and not self.task.is_task_done():cleanup.append('native viewport screenshot task is still pending')
            self.task=None
            if self.previous_view is not None:
                try:
                    self.editor.set_level_viewport_camera_info(*self.previous_view)
                    source.require(self.editor.get_level_viewport_camera_info()==self.previous_view,'capture viewport restoration differs')
                except Exception as exc:cleanup.append('capture viewport restoration: '+str(exc))
                self.previous_view=None
            if self.previous_selection is not None:
                try:
                    if list(self.actor_editor.get_selected_level_actors())!=self.previous_selection:
                        self.actor_editor.set_selected_level_actors(self.previous_selection)
                    source.require(list(self.actor_editor.get_selected_level_actors())==self.previous_selection,
                                   'capture selection restoration differs')
                except Exception as exc:cleanup.append('capture selection restoration: '+str(exc))
                self.previous_selection=None
            if self.performance_settings is not None and self.previous_throttle is not None:
                try:self.performance_settings.set_editor_property('bThrottleCPUWhenNotForeground',self.previous_throttle)
                except Exception as exc:cleanup.append('capture performance setting: '+str(exc))
                self.performance_settings=None
            try:
                verify_geometry_state(map_geometry_state(self.u),self.baseline)
                source.require(not self.u.EditorLoadingAndSavingUtils.get_dirty_map_packages()
                               and not self.u.EditorLoadingAndSavingUtils.get_dirty_content_packages(),'capture left dirty packages')
            except Exception as exc:cleanup.append(str(exc))
            self.result.update(phase='failed' if error or cleanup else 'capture_passed',
                               error=str(error) if error else None,cleanup_errors=cleanup,visual_verified=False)
            source.write_machine(self.output,self.result)
            self.u.log(json.dumps({'phase':self.result['phase'],'image':str(self.image),'visual_verified':False}))
        finally:
            self.u.EditorPythonScripting.set_keep_python_script_alive(False)
            globals()['_stage_capture']=None


def require_api(u,mode):
    required=['AssetToolsHelpers','AssetImportTask','TextureFactory','EditorAssetLibrary','EditorLoadingAndSavingUtils',
              'MaterialEditingLibrary','EditorActorSubsystem','LevelEditorSubsystem','UnrealEditorSubsystem']
    if mode in ('affine','affine_preflight'):
        required+=['GeometryScript_AssetUtils','GeometryScript_MeshTransforms','GeometryScript_MeshQueries','DynamicMesh']
    if mode=='affine_readback':
        required+=['GeometryScript_AssetUtils','GeometryScript_MeshQueries','DynamicMesh','StaticMeshEditorSubsystem',
                   'StaticMesh','GeometryScriptCopyMeshFromAssetOptions','GeometryScriptMeshReadLOD',
                   'GeometryScriptLODType','GeometryScriptOutcomePins']
    if mode in ('map_geometry','map_geometry_readback','geometry_baseline','map','readback','lighting','lighting_readback','capture'):
        required+=['Actor','ActorComponent','SceneComponent','PrimitiveComponent','StaticMeshComponent',
                   'LightComponentBase','ReflectionCaptureComponent']
    if mode in ('map','readback','lighting','lighting_readback','capture'):
        required+=['DirectionalLight','PointLight','SpotLight','BoxReflectionCapture','BoxReflectionCaptureComponent',
                   'LightComponent','LightUnits','ReflectionSourceType','ComponentMobility','Color']
    if mode=='capture':required+=['AutomationLibrary','AutomationEditorTask','EditorPythonScripting','MathLibrary']
    if mode in ('probe_textures_readback','surface_textures_readback'):required+=['AssetExportTask','Exporter','TextureExporterDDS']
    if mode in ('materials','preflight','map','readback','assets_readback'):
        required+=['Material','MaterialFactoryNew','CustomInput','CustomMaterialOutputType','MaterialSamplerType']
    if mode in ('pawn_support_preflight', 'pawn_support', 'pawn_support_readback', 'pawn_support_play', 'pawn_support_collision', 'pawn_support_visibility', 'pawn_support_asset_repair'):
        required += ['Actor','ActorComponent','SceneComponent','PrimitiveComponent','StaticMeshComponent',
                     'LightComponentBase','ReflectionCaptureComponent','LightComponent','BoxReflectionCaptureComponent',
                     'GeometryScript_AssetUtils','GeometryScript_MeshQueries','GeometryScript_MeshEdits',
                     'GeometryScript_NewAssetUtils','GeometryScriptCreateNewStaticMeshAssetOptions',
                     'DynamicMesh','StaticMeshEditorSubsystem','GeometryScriptCopyMeshFromAssetOptions',
                     'GeometryScriptMeshReadLOD','GeometryScriptLODType','GeometryScriptOutcomePins',
                     'CollisionTraceFlag','Character','GameMapsSettings','WorldSettings','PlayerStart',
                     'GameplayStatics','SystemLibrary','HitResult','IntVector','DrawDebugTrace',
                     'StaticMeshActor','GGYGOBossEncounter','CollisionEnabled','CollisionChannel','CollisionResponseType']
    if mode in ('pawn_support_preflight', 'pawn_support', 'pawn_support_play'):
        required += ['EditorPythonScripting','AutomationLibrary','AutomationEditorTask','GGYGOPawnExtensionComponent',
                     'EnhancedInputLocalPlayerSubsystem']
    if mode == 'pawn_support_asset_repair':required += ['GeometryScriptCopyMeshToAssetOptions','GeometryScriptMeshWriteLOD']
    missing = [name for name in required if not hasattr(u, name)]
    source.require(not missing, 'native full Editor APIs unavailable: '+', '.join(missing))


def require_recipe_api(u,plan,settings,mode):
    """Resolve all reflection before creating the first object in that phase."""
    if mode=='capture':
        for cls_name,names in [('UnrealEditorSubsystem',['get_level_viewport_camera_info','set_level_viewport_camera_info']),
                              ('EditorActorSubsystem',['get_selected_level_actors','set_selected_level_actors']),
                              ('AutomationLibrary',['take_high_res_screenshot']),('AutomationEditorTask',['is_valid_task','is_task_done'])]:
            for name in names:
                source.require(callable(getattr(getattr(u,cls_name),name,None)),'native viewport capture API unavailable: '+name)
    if mode in ('textures','probe_preflight','probe_textures','surface_textures','surface_textures_readback','probe_textures_readback','preflight','lighting','lighting_readback','map','readback','assets_readback','capture'):
        for cfg in settings['textures'].values():
            for cls,key in [(u.TextureCompressionSettings,'compression'),(u.TextureFilter,'filter'),
                            (u.TextureMipGenSettings,'mip_gen_settings')]:
                source.require(hasattr(cls,cfg[key]),'native texture enum unavailable: '+cfg[key])
            for key in ('address_x','address_y'):
                if key in cfg:source.require(hasattr(u.TextureAddress,cfg[key]),'native texture address unavailable: '+cfg[key])
    if mode in ('materials','preflight','map','readback','assets_readback'):
        for graph in settings['rendering']['materials'].values():
            for cls,key in [(u.BlendMode,'blend_mode'),(u.MaterialShadingModel,'shading_model')]:
                source.require(hasattr(cls,graph[key]),'native material mode is unavailable: '+graph[key]
                               +'; exposed='+','.join(v for v in dir(cls) if v.isupper()))
            for spec in graph['nodes']:
                source.require(hasattr(u,spec['class']),'native expression class unavailable: '+spec['class'])
                for value in spec.get('properties',{}).values():
                    if isinstance(value,dict) and 'enum' in value:
                        source.require(hasattr(u,value['enum']) and hasattr(getattr(u,value['enum']),value['value']),
                                       'native expression enum unavailable: '+str(value))
            for output in graph['outputs']:
                source.require(hasattr(u.MaterialProperty,output['property']),'native material output unavailable')
    if mode in ('affine','affine_preflight'):
        for cls_name,names in [('GeometryScript_AssetUtils',['copy_mesh_from_static_mesh_v2','copy_mesh_to_static_mesh']),
                              ('GeometryScript_MeshTransforms',['transform_mesh','inverse_transform_mesh']),
                              ('GeometryScript_MeshQueries',['get_vertex_count','get_num_vertex_i_ds','get_vertex_position'])]:
            cls = getattr(u,cls_name)
            for name in names:
                source.require(callable(getattr(cls,name,None)),
                               'native affine method unavailable: unreal.'+cls_name+'.'+name)
    if mode=='affine_readback':
        for cls_name,names in [('GeometryScript_AssetUtils',['copy_mesh_from_static_mesh_v2']),
                              ('GeometryScript_MeshQueries',['get_vertex_count','get_num_vertex_i_ds','get_vertex_position']),
                              ('StaticMeshEditorSubsystem',['get_lod_material_slot']),('StaticMesh',['get_num_sections'])]:
            cls = getattr(u,cls_name)
            for name in names:
                source.require(callable(getattr(cls,name,None)),
                               'native affine readback method unavailable: unreal.'+cls_name+'.'+name)
        source.require(hasattr(u.GeometryScriptLODType,'SOURCE_MODEL') and hasattr(u.GeometryScriptOutcomePins,'SUCCESS'),
                       'native affine readback source LOD/outcome enum unavailable')
    if mode in ('map_geometry','map_geometry_readback','geometry_baseline'):
        methods=[('Actor',['get_actor_enable_collision','get_actor_label','get_components_by_class']),
                 ('SceneComponent',['get_attach_parent','get_relative_transform'])]
        if mode=='map_geometry':methods.append(('StaticMeshComponent',['set_static_mesh','modify']))
        for cls_name,names in methods:
            for name in names:
                source.require(callable(getattr(getattr(u,cls_name),name,None)),
                               'native map geometry method unavailable: unreal.'+cls_name+'.'+name)
    if mode in ('materials','map','readback','assets_readback'):
        source.require(callable(getattr(u.CustomInput,'export_text',None)),
                       'native CustomInput struct export API unavailable')
        for name in ('get_material_expressions','get_material_expression_input_names',
                     'get_material_expression_output_names','get_inputs_for_material_expression',
                     'get_input_node_output_name_for_material_expression',
                     'get_material_property_input_node','get_material_property_input_node_output_name'):
            source.require(callable(getattr(u.MaterialEditingLibrary,name,None)), 'native graph readback API unavailable: '+name)
    if mode in ('pawn_support_preflight', 'pawn_support', 'pawn_support_readback', 'pawn_support_play', 'pawn_support_collision', 'pawn_support_visibility', 'pawn_support_asset_repair'):
        for cls_name, names in [
            ('GeometryScript_MeshEdits', ['add_vertex_to_mesh','add_triangle_to_mesh']),
            ('GeometryScript_MeshQueries', ['get_vertex_count','get_num_vertex_i_ds','get_vertex_position',
                                           'get_num_triangle_i_ds','get_triangle_indices']),
            ('DynamicMesh', ['get_triangle_count']),
            ('GeometryScript_AssetUtils', ['copy_mesh_from_static_mesh_v2']),
            ('GeometryScript_NewAssetUtils', ['create_new_static_mesh_asset_from_mesh']),
            ('GameMapsSettings', ['get_game_maps_settings']),
            ('SystemLibrary', ['capsule_trace_single_by_profile']),
            ('EditorAssetLibrary', ['load_blueprint_class']),
            ('SceneComponent', ['set_visibility', 'set_hidden_in_game']),
            ('PrimitiveComponent', ['set_collision_enabled','set_collision_object_type',
                                    'set_collision_profile_name','set_collision_response_to_all_channels','set_collision_response_to_channel'])]:
            for name in names:
                source.require(callable(getattr(getattr(u, cls_name), name, None)),
                               'PawnSupport native method unavailable: '+cls_name+'.'+name)
        source.require(hasattr(u.CollisionTraceFlag, 'CTF_USE_COMPLEX_AS_SIMPLE'),
                       'PawnSupport native complex-as-simple collision enum unavailable')
        source.require(all(hasattr(u.CollisionResponseType, name) for name in ('ECR_IGNORE', 'ECR_BLOCK')),
                       'PawnSupport native collision response enum unavailable')
        source.require(hasattr(u.get_default_object(u.StaticMeshComponent), 'generate_overlap_events'),
                       'PawnSupport native overlap BlueprintSetter property unavailable')
        u.get_default_object(u.StaticMeshComponent).get_editor_property('use_default_collision')
    if mode == 'pawn_support_asset_repair':
        source.require(callable(getattr(u.GeometryScript_AssetUtils, 'copy_mesh_to_static_mesh', None)),
                       'PawnSupport native asset repair write API unavailable')
    if mode in ('pawn_support_preflight', 'pawn_support', 'pawn_support_play'):
        missing = []
        for cls, names in [('UnrealEditorSubsystem', ['get_game_world']),
                           ('LevelEditorSubsystem', ['editor_request_begin_play','editor_request_end_play','is_in_play_in_editor']),
                           ('EnhancedInputLocalPlayerSubsystem', ['inject_input_vector_for_action']),
                           ('Object', ['call_method']),
                           ('GGYGOPawnExtensionComponent', ['get_ggygo_ability_system_component']),
                           ('CharacterMovementComponent', ['is_moving_on_ground','is_walkable']),
                           ('AutomationLibrary', ['take_high_res_screenshot'])]:
            for name in names:
                if not callable(getattr(getattr(u, cls), name, None)):missing.append(cls+'.'+name)
        source.require(not missing, 'PawnSupport production/PIE native methods unavailable: '+', '.join(missing))
        movement = u.get_default_object(u.Character).get_editor_property('CharacterMovement')
        floor = movement.get_editor_property('CurrentFloor')
        for name in ('bBlockingHit','bWalkableFloor','FloorDist','HitResult'):
            floor.get_editor_property(name)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['inspect','preflight','probe_preflight','textures','probe_textures','surface_textures','surface_textures_readback','probe_textures_readback','affine_preflight','affine','affine_readback',
                                       'map_geometry','map_geometry_readback','geometry_baseline','materials','map','readback',
                                       'lighting','lighting_readback','assets_readback','capture','pawn_support_preflight',
                                       'pawn_support','pawn_support_readback','pawn_support_play','pawn_support_collision','pawn_support_visibility','pawn_support_asset_repair'])
    parser.add_argument('--plan',required=True)
    parser.add_argument('--settings')
    parser.add_argument('--map-sha256')
    parser.add_argument('--map-backup')
    parser.add_argument('--geometry-result')
    parser.add_argument('--environment-result', help='accepted lighting checkpoint, or successful map result for cold read')
    parser.add_argument('--support-preflight', help='PawnSupport apply: exact successful read-only source/map preflight')
    parser.add_argument('--support-result', help='PawnSupport cold read: exact successful support/map apply result')
    parser.add_argument('--support-asset-result', help='PawnSupport apply: explicit failed result, read-only reuse of its saved support asset')
    parser.add_argument('--support-asset-backup', help='PawnSupport winding repair: exact owned failed asset copy in Saved')
    parser.add_argument('--standby-observer-sha256', help='PawnSupport PIE: exact frozen public Boss observer tool SHA256')
    parser.add_argument('--p1-support-source-manifest', help='P1 support modes: pinned resource P2 Collider/visible geometry source manifest')
    parser.add_argument('--materials-result', help='explicit failed material result; verify its saved graphs read-only and create only the remaining assets')
    parser.add_argument('--textures-result', help='explicit failed result from this texture phase/settings; verify recorded saved textures read-only and create only the remainder')
    parser.add_argument('--screenshot', help='capture mode: fresh Saved PNG, native viewport RHI screenshot')
    parser.add_argument('--capture-materials',action='store_true',help='capture the accepted full material map checkpoint')
    parser.add_argument('--capture-focus-model',help='capture only: use one active source Scene_Base model bounds for the observation camera')
    parser.add_argument('--cube-readback-cache', help='probe cold read: fresh Saved directory for actual native Source DDS exports')
    parser.add_argument('--output')
    args=parser.parse_args()
    source.require(args.materials_result is None or args.mode=='materials','material resume is only valid for material creation')
    source.require(args.textures_result is None or args.mode in ('textures','probe_textures','surface_textures'),
                   'texture resume is only valid for texture creation')
    source.require(args.support_asset_result is None or args.mode in ('pawn_support', 'pawn_support_preflight', 'pawn_support_asset_repair'),
                   'support asset result is only valid for explicit PawnSupport apply/preflight/repair')
    source.require(args.capture_focus_model is None or args.mode=='capture','capture focus is only valid for observation')
    plan=source.validate_plan(source.read_json(args.plan))
    source.require(args.settings is not None or args.mode in ('inspect','affine','affine_preflight','affine_readback',
                                                             'map_geometry','map_geometry_readback','geometry_baseline'),
                   'this phase requires explicit texture/rendering input')
    settings=source.read_json(args.settings) if args.settings else {'plan_digest':plan['digest']}
    if args.mode!='inspect':
        validation_mode={'capture':'readback' if args.capture_materials else 'lighting_readback',
                         'probe_preflight':'probe_textures','pawn_support_preflight':'readback',
                         'pawn_support':'readback','pawn_support_readback':'readback',
                         'pawn_support_play':'readback','pawn_support_collision':'readback','pawn_support_visibility':'readback',
                         'pawn_support_asset_repair':'readback'}.get(args.mode,args.mode)
        validate_settings(plan,settings,validation_mode)
    if args.mode=='inspect':
        print(json.dumps({'create_only':{m:targets(plan,m) for m in ['textures','materials','affine']},
                          'existing_map':plan['map'],'existing_source_actor_count':len(plan['geometry_actors']),'collision_activated':False}))
        return
    source.require(args.output is not None,'native execution requires a fresh Saved result')
    output=Path(args.output).resolve()
    source.require(output.is_relative_to(source.PROJECT/'Saved') and not output.exists(),'result target is not fresh project Saved')
    result={'mode':args.mode,'plan_digest':plan['digest'],'settings_digest':source.digest(settings),'phase':'preflight','saved_assets':[],
            'created_actors':[],'map_saved':False,'restoration_complete':False}
    if args.mode.startswith('pawn_support'):
        result['tool_files'] = {name: source.evidence(SCRIPT_DIR/name) for name in
                               ('bh3_stage_environment_source.py','restore_bh3_stage_environment.py','test_bh3_stage_environment.py')}
    try:
        import unreal as u
        require_api(u,args.mode)
        require_recipe_api(u,plan,settings,args.mode)
        editor=u.get_editor_subsystem(u.UnrealEditorSubsystem)
        levels=u.get_editor_subsystem(u.LevelEditorSubsystem)
        source.geometry._require_editor_process_host(u,plan['stage'],editor,levels,editor.get_editor_world())
        result['phase']=args.mode
        if args.mode in ('textures','probe_textures','surface_textures'):create_textures(u,plan,settings,result,args.mode,args.textures_result)
        elif args.mode in ('affine','affine_preflight','affine_readback'):
            source.require(args.map_sha256 is not None and source.evidence(package_file(plan['map'],'.umap'))['sha256'].lower()
                           == args.map_sha256.lower(),'affine phase requires the exact source map baseline')
            if args.mode=='affine_readback':affine_readback(u,plan,result)
            else:affine_assets(u,plan,result,args.mode=='affine_preflight')
        elif args.mode=='materials':create_materials(u,plan,settings,result,args.materials_result)
        elif args.mode=='geometry_baseline':
            source.require(args.map_sha256 is not None and source.evidence(package_file(plan['map'],'.umap'))['sha256'].lower()
                           == args.map_sha256.lower(),'geometry baseline requires the exact saved map SHA256')
            read_geometry_baseline(u,plan,result)
        elif args.mode in ('map_geometry','map_geometry_readback'):
            source.require(args.map_sha256 is not None and source.evidence(package_file(plan['map'],'.umap'))['sha256'].lower()
                           == args.map_sha256.lower(),'map geometry requires the exact current map baseline')
            if args.mode=='map_geometry':apply_map_geometry(u,plan,result,args.map_backup)
            else:read_map_geometry(u,plan,result,args.geometry_result)
        elif args.mode in ('map','lighting'):
            source.require(args.map_sha256 is not None,'map phase requires explicit baseline SHA256')
            source.require(not (args.geometry_result and args.environment_result),'select one accepted map checkpoint')
            previous=args.environment_result if args.environment_result else args.geometry_result
            apply_map(u,plan,settings,result,args.map_sha256,args.map_backup,previous,args.mode=='map')
        elif args.mode in ('readback','lighting_readback'):
            read_environment(u,plan,settings,result,args.environment_result,args.mode=='readback')
        elif args.mode == 'pawn_support_preflight':
            pawn_support_preflight(u, plan, settings, result, args.environment_result, args.p1_support_source_manifest, args.support_asset_result)
        elif args.mode == 'pawn_support_asset_repair':
            repair_support_asset(u, plan, settings, result, args.support_preflight, args.support_asset_result, args.environment_result,
                                 args.p1_support_source_manifest, args.map_sha256, args.support_asset_backup)
        elif args.mode == 'pawn_support':
            apply_pawn_support(u, plan, settings, result, args.support_preflight, args.environment_result,
                               args.map_sha256, args.map_backup, args.p1_support_source_manifest, args.support_asset_result)
        elif args.mode == 'pawn_support_readback':
            read_pawn_support(u, plan, settings, result, args.support_result, args.p1_support_source_manifest)
        elif args.mode in ('pawn_support_collision', 'pawn_support_visibility'):
            repair_support_component(u, plan, settings, result, args.support_result, args.map_sha256,
                                     args.map_backup, args.p1_support_source_manifest,
                                     repair_kind='visibility' if args.mode == 'pawn_support_visibility' else 'collision')
        elif args.mode == 'pawn_support_play':
            source.require(args.screenshot is not None, 'PawnSupport PIE requires its actual native image destination')
            applied = read_pawn_support(u, plan, settings, result, args.support_result, args.p1_support_source_manifest)
            play = StageSupportPlay(u, plan, settings, result, applied, output, args.screenshot, args.standby_observer_sha256)
            if not play.finished:globals()['_stage_support_play'] = play
            return
        elif args.mode=='capture':
            source.require(args.screenshot is not None,'capture requires its PNG destination')
            read_environment(u,plan,settings,result,args.environment_result,args.capture_materials)
            capture=StageCapture(u,plan,settings,result,output,args.screenshot,args.capture_focus_model)
            if not capture.finished:globals()['_stage_capture']=capture
            return
        elif args.mode=='assets_readback':result['assets_readback']=verify_assets(u,plan,settings)
        elif args.mode in ('probe_textures_readback','surface_textures_readback'):
            source.require(args.cube_readback_cache is not None,'texture cold read requires its native Cube Source export cache')
            scope='probe_textures' if args.mode=='probe_textures_readback' else 'surface_textures'
            result['assets_readback']=verify_assets(u,plan,settings,False,scope,args.cube_readback_cache)
        elif args.mode in ('preflight','probe_preflight'):
            for mode in (('probe_textures',) if args.mode=='probe_preflight' else ('surface_textures','materials') if 'preserved_lighting' in settings else ('textures','materials')):absent_targets(u,plan,mode)
            if 'preserved_lighting' in settings:verify_assets(u,plan,settings,False,'probe_textures')
            for row in plan['affine_meshes']:exact_asset(u,row['package'],'StaticMesh',True,plan)
        result['phase']=args.mode+'_passed'
        source.write_machine(output,result)
        print(json.dumps(result))
    except Exception as exc:
        result['failure_phase']=result['phase']
        result['phase']='failed'
        result['error']=type(exc).__name__+': '+str(exc)
        if not output.exists():source.write_machine(output,result)
        raise


if __name__=='__main__':main()
