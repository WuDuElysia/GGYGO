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
is intentionally not executed by this tool while its user decision is pending.
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
import sys
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
    if 'preserved_lighting' in settings:source.lighting_generation_digest(plan,settings)
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
    for name in required:source.require(hasattr(u,name),'native full Editor API unavailable: '+name)


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


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['inspect','preflight','probe_preflight','textures','probe_textures','surface_textures','surface_textures_readback','probe_textures_readback','affine_preflight','affine','affine_readback',
                                       'map_geometry','map_geometry_readback','geometry_baseline','materials','map','readback',
                                       'lighting','lighting_readback','assets_readback','capture'])
    parser.add_argument('--plan',required=True)
    parser.add_argument('--settings')
    parser.add_argument('--map-sha256')
    parser.add_argument('--map-backup')
    parser.add_argument('--geometry-result')
    parser.add_argument('--environment-result', help='accepted lighting checkpoint, or successful map result for cold read')
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
    source.require(args.capture_focus_model is None or args.mode=='capture','capture focus is only valid for observation')
    plan=source.validate_plan(source.read_json(args.plan))
    source.require(args.settings is not None or args.mode in ('inspect','affine','affine_preflight','affine_readback',
                                                             'map_geometry','map_geometry_readback','geometry_baseline'),
                   'this phase requires explicit texture/rendering input')
    settings=source.read_json(args.settings) if args.settings else {'plan_digest':plan['digest']}
    if args.mode!='inspect':
        validation_mode={'capture':'readback' if args.capture_materials else 'lighting_readback','probe_preflight':'probe_textures'}.get(args.mode,args.mode)
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
