"""@file projected_fx_material_plan.py
@brief 准确Decal源材质到Native投影的create-only计划及完整粒子输入合同。

本文件不执行UE。FX提供stage选择证据、原实例数据与源affine；
Renderer仅沿原Niagara钩子提交同tick私有MID，原FX拥有失败与完成状态。
"""
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from gen_projected_fx_hlsl import DECAL_SID, PROP_SID, POLICY, PROGRAM_FILE, RAW_STREAMS
from zzz_fx_asset_session import version_name
from zzz_fx_import_assets import plan_imports
from zzz_fx_material import material_input

HERE = Path(__file__).resolve().parent
CONFIG_FILE = HERE.parent / 'Assets/Pyrios/Rendering/Pyrios_ProjectedFX_Rendering.json'
SCHEMA = 'projected_fx_material_plan/v1'
SHARED = '/Game/Characters/Shared/FX/ZZZ'


def _read(path):
    raw = Path(path).read_bytes()
    return json.loads(raw.decode('utf-8-sig')), dict(path=str(Path(path).resolve()), bytes=len(raw),
                                                  sha256=hashlib.sha256(raw).hexdigest())


def _finite(value, name):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('投影参数不是有限数值：' + name)
    return float(value)


def project_configuration(path=CONFIG_FILE):
    configuration, identity = _read(path)
    return dict(configuration=configuration, inputs=[identity])


def _configuration(value):
    data = value['configuration']
    expected = dict(schema='projected_fx_configuration/v1', mode='NativeDeferredDecalSourceSurface',
        color_mapping='RawSerializedValues', decal_vertex_selection='ProjectConfiguredDecalVertex',
        receiver_normal='NativeDepthDerivativesFacingCamera', receiver_eligibility='NativeReceivesDecals',
        projection='SourceAffineRelativeToNativeProjectorOrigin', native_volume='ConservativeSourceVolumeWithPadding',
        native_fade='SourceCoverageWithinNativeFlatFadeRegion', time='OriginalSystemAgeForBothSourceTimeGroups',
        projector_geometry='NativeUnitCubeProjector', source_builtin_mesh_recovered=False,
        framebuffer='NativeDBufferAndEmissive', source_runtime_certified=False, visual_calibrated=False)
    if any(data.get(name) != item for name, item in expected.items()):
        raise ValueError('未支持的投影/场景/时间配置')
    if (type(data['max_material_instances']) is not int or data['max_material_instances'] <= 0
            or _finite(data['native_enclosure_scale'], 'native_enclosure_scale') < 4.0 / 3.0
            or _finite(data['emissive_output_scale'], 'emissive_output_scale') < 0
            or not 0 <= _finite(data['exposure_compensation_weight'], 'exposure_compensation_weight') <= 1):
        raise ValueError('投影容量、包围体、输出或曝光配置无效')
    configurations = []
    for identity in value['inputs']:
        supplied, actual = _read(identity['path'])
        if actual != identity:
            raise ValueError('投影配置来源已变化')
        if supplied.get('schema') == 'projected_fx_configuration/v1':
            configurations.append(supplied)
    if configurations != [data]:
        raise ValueError('投影配置值不等于准确配置文件，不能只沿用旧身份')
    return data


def _stage_selection(source_programs, program, material):
    """选择事实由原提取者交入，stage证据必须仍有准确文件身份。"""
    mode = source_programs.get('selection_mode')
    if mode not in ('ExactSourceStageKeywords', 'ProjectConfiguredDecalVertex'):
        raise ValueError('Decal仍缺准确源stage映射；共享VP候选不代表已匹配')
    if (source_programs.get('serialized_keywords') != sorted(material['m_ShaderKeywords'].split())
            or not source_programs.get('evidence')):
        raise ValueError('Decal stage选择缺当前材质关键词/证据')
    keys = ('sourceByteRange', 'fileBytesSha256', 'hash64')
    for field, original in (('vertex', program['source_vertex_candidate']),
                            ('fragment', program['source_fragment'])):
        if any(source_programs[field].get(key) != original[key] for key in keys):
            raise ValueError('Decal stage选择不是当前已移植的准确程序：' + field)
    for identity in source_programs['evidence']:
        _, actual = _read(identity['path'])
        if actual != identity:
            raise ValueError('Decal stage证据文件已变化')


def _material_value(saved, name, dim, defaults):
    if name.endswith('_ST') and name[:-3] in saved['m_TexEnvs']:
        texture = saved['m_TexEnvs'][name[:-3]]
        value = [texture['m_Scale']['X'], texture['m_Scale']['Y'], texture['m_Offset']['X'], texture['m_Offset']['Y']]
    elif dim == 1:
        return _finite(saved['m_Floats'][name] if name in saved['m_Floats'] else defaults[name], name)
    else:
        value = ([saved['m_Colors'][name][channel] for channel in 'rgba'] if name in saved['m_Colors'] else defaults[name])[:dim]
    if len(value) != dim:
        raise ValueError('源Decal参数维度无效：' + name)
    return value


def _vector_parameter(value, dim, name):
    if dim == 1:
        return dict(dim=1, value=_finite(value, name))
    if len(value) != dim:
        raise ValueError('投影源参数维度无效：' + name)
    # UE vector parameter是float4，Custom仍按源float2/3表达式取活跃分量。
    return dict(dim=4, value=[_finite(x, name) for x in value] + [0.0] * (4 - dim), source_dim=dim)


def _renderer_contract(parameters, configuration):
    vectors = sorted(name for name, item in parameters.items() if item['origin'] == 'original_cpu_particle')
    return dict(renderer_class='/Script/GGYGORendering.GGYGOProjectedDecalRendererProperties',
        native_subobject='NativeDecal', native_authoring_getter='get_native_decal_for_authoring',
        native_configuration_owner='ReturnedNativeDecalSubobject',
        properties=dict(bPayloadConfigured=True, ParticleVectorAttributes=['Particles.' + name for name in vectors],
            MaterialVectorParameters=vectors, SimulationAgeParameter='UEFX_SystemAge',
            MaxMaterialInstances=configuration['max_material_instances']),
        source_reference='OriginalPrefab/Transform/Renderer identity supplied by FX',
        simulation='OriginalCPUInstanceParticles', update='OriginalNiagaraPostSystemTick_GameThread',
        material='ExactlyOneOriginalUserMaterial; private per-visible-particle MIDs',
        required_native_bindings=['Position', 'DecalOrientation', 'DecalSize', 'DecalVisible',
                                  'RendererVisibilityTag', 'DecalColor', 'DecalFade', 'DecalSortOrder'],
        native_constants=dict(DecalScreenSizeFade=0.0, DecalFade=1.0, DecalColor=[1.0, 1.0, 1.0, 1.0]),
        material_authoring='bind_source_user_material_for_authoring(System, UserParameterName, Material); inspect actual reflected out-parameter ABI',
        compiled_layout_reader='read_compiled_payload_layout_for_authoring; cached names/accessor validity only, current compile epoch and real frame still required',
        capacity_failure='ReportOriginalFXFailureWithoutTruncation',
        failure_receiver='IGGYGOFXRendererFailureReceiver::ReportFXRendererFailure',
        per_emitter_material_parameters='Empty; all dynamic inputs listed in same-tick contract')


def _make_prop_plan(material, material_identity, dependencies, dependency_identity, pid, *,
                    texture_targets, revision, configuration, source_programs, config):
    policy, _ = _read(POLICY)
    evidence = policy['shader_choices'][PROP_SID]['source_evidence']
    selected = evidence['materials'][pid]
    if (material_identity['sha256'] != selected['materialSource']['sha256']
            or set(material['m_ShaderKeywords'].split()) != set(selected['serializedMaterialKeywords'])):
        raise ValueError('Prop源材质或关键词身份不符')
    programs, program_identity = _read(PROGRAM_FILE)
    program = programs['prop'][pid]
    prop = config['prop']
    if (prop['mode'] != 'NativeDeferredSurfaceAndAdditiveForward' or prop['geometry'] != 'NativeTRSOnly'
            or prop['flow_coordinates'] != 'NativeMeshInstanceWorldToLocal'
            or prop['geometry_flow_selection'] != 'ProjectConfiguredGeometryWithoutForwardOnlyFlow'):
        raise ValueError('Prop需要明确的Native几何/Flow/stage配置')
    if (source_programs.get('selection_mode') != 'NativePropRoles'
            or source_programs.get('serialized_keywords') != sorted(material['m_ShaderKeywords'].split())
            or source_programs.get('geometry_selection') != program['source_geometry_selection']
            or not source_programs.get('evidence')):
        raise ValueError('Prop缺准确源选择与显式Geometry stage政策')
    for key, expected in (('geometry', program['source_geometry']), ('forward', program['source_forward'])):
        for stage in ('vp', 'fp'):
            actual = source_programs[key][stage]
            for name in ('sourceByteRange', 'fileBytesSha256', 'hash64'):
                if actual.get(name) != expected[stage][name]:
                    raise ValueError('Prop准确程序不是当前已移植来源：' + key + '/' + stage)
    for identity in source_programs['evidence']:
        _, actual = _read(identity['path'])
        if actual != identity:
            raise ValueError('Prop源选择/几何证据已变化')
    uv = source_programs['mesh_uv']
    if uv.get('mode') not in ('OriginalMeshUV0', 'FXAnimatedMeshUV0') or not uv.get('source'):
        raise ValueError('Prop需要真实Mesh UV模块/adapter合同，不默认关闭动画UV')
    from zzz_fx_particle_uv import mesh_uv_adapter
    adapter = uv['adapter']
    if (uv['mode'] != adapter['mode'] or uv['source']['source_node'] != adapter['source_node']
            or adapter != mesh_uv_adapter(adapter['source_module'], adapter['source_node'])):
        raise ValueError('Prop UV合同不等于原FX唯一helper的当前算法')
    raw_uv_source = Path(uv['source']['path']).read_bytes()
    if (len(raw_uv_source) != uv['source']['bytes']
            or hashlib.sha256(raw_uv_source).hexdigest() != uv['source']['sha256']
            or not str(uv['source']['transform']).strip()):
        raise ValueError('Prop UV原prefab/Transform身份无效')
    if source_programs.get('geometry_transport') != 'NativeTRSOnly':
        raise ValueError('Prop实际几何不能由Native TRS完整表达；需要原作者补准确接口')
    if source_programs.get('vertex_color') != 'ParticleColorTimesMeshVertexColor':
        raise ValueError('Prop原particle+mesh COLOR流需要真实ParticleColor×MeshVertexColor')
    motion = prop['motion'][pid]
    if (motion['native'] not in ('Precise', 'Disable')
            or (motion['source_mode'], motion['native']) not in ((1, 'Precise'), (2, 'Disable'))):
        raise ValueError('Prop原MotionVectors与配置不一致')
    age = prop['system_age_transport']
    if type(age['slot']) is not int or not 0 <= age['slot'] <= 3 or type(age['component']) is not int or not 0 <= age['component'] <= 3:
        raise ValueError('Prop真实Age运输槽无效')
    saved = material['m_SavedProperties']
    names = sorted({name for role in ('geometry', 'forward') for name in program[role]['textures']})
    texture_pids = []
    for name in names:
        pointer = saved['m_TexEnvs'][name]['m_Texture']
        if pointer['IsNull'] or str(pointer['m_PathID']) not in dependencies:
            raise ValueError('Prop缺活跃源纹理：' + name)
        texture_pids.append(str(pointer['m_PathID']))
    imported = plan_imports([dependency_identity['path']], revision=revision, selected_pids=texture_pids)
    if imported['assets'] != texture_targets:
        raise ValueError('Prop纹理目标不等于同revision准确导入计划')
    source = dict(material=material_identity, dependency=dependency_identity, material_pid=pid, shader_pid=PROP_SID,
        source_programs=deepcopy(source_programs), program_file=program_identity,
        configuration=deepcopy(configuration), revision=revision)
    materials, bindings = [], {}
    roles = dict(geometry='prop_surface', forward='prop_forward_color')
    for source_role, role in roles.items():
        shader = program[source_role]
        params = {}
        for name, dim in shader['material_params'].items():
            value = _material_value(saved, name, dim, shader['material_defaults'])
            params[name] = dict(_vector_parameter(value, dim, name), origin='source_material_or_shader_default')
        for name, dim in shader['parameters'].items():
            params[name] = dict(_vector_parameter(prop['globals'][name], dim, name), origin='project_configuration')
        if source_role == 'forward':
            params['UE_EmissiveOutputScale'] = dict(dim=1, value=config['emissive_output_scale'], origin='project_configuration')
            params['UE_ExposureCompensationWeight'] = dict(dim=1, value=config['exposure_compensation_weight'], origin='project_configuration')
        properties = dict(MaterialDomain='MD_Surface',
            BlendMode='BLEND_Masked' if source_role == 'geometry' else 'BLEND_Additive',
            ShadingModel='MSM_DefaultLit' if source_role == 'geometry' else 'MSM_Unlit',
            TwoSided=False, bTangentSpaceNormal=False, bAutomaticallySetUsageInEditor=False,
            bUsedWithNiagaraMeshParticles=True, bUsedWithNiagaraSprites=False, bHasPixelAnimation=True)
        if source_role == 'geometry':
            properties['OpacityMaskClipValue'] = 0.5
        else:
            properties.update(TranslucencyPass=prop['forward_pass'], bDisableDepthTest=False,
                              bOutputTranslucentVelocity=False)
        spec = dict(role=role, shader=shader, params=params, properties=properties,
            mesh_uv=deepcopy(uv), age_transport=deepcopy(age),
            textures={name: texture_targets[str(saved['m_TexEnvs'][name]['m_Texture']['m_PathID'])]
                      for name in shader['textures']},
            source_render_state=deepcopy(selected['resolvedSourceState']))
        identity = dict(schema=SCHEMA, source=source, spec=spec)
        spec['master'] = SHARED + '/Materials/' + version_name('M_Prop_' + role + '_' + pid, identity)
        spec['instance'] = SHARED + '/MaterialInstances/' + version_name('MI_Prop_' + role + '_' + pid, identity)
        materials.append(spec)
        bindings[role] = spec['instance']
    contract = dict(renderer_class='/Script/Niagara.NiagaraMeshRendererProperties',
        roles=list(roles.values()), geometry='NativeTRSOnly', motion_vector_setting=motion['native'],
        source_motion_vectors=motion['source_mode'], velocity_consumer='Native prop_surface geometry velocity draw',
        forward_color_velocity='Disabled duplicate output; geometry role owns native velocity',
        compiled_motion_reader='GGYGOProjectedDecalRendererProperties.read_native_mesh_motion_for_authoring(System, EmitterName, RendererIndex); inspect actual reflected out-parameter ABI',
        mesh_uv=deepcopy(uv), system_age_transport=deepcopy(age),
        system_age_dynamic_parameter_mask=(1 << (4 * age['slot'] + age['component']))
            if any('UEFX_SystemAge' in program[role]['builtins'] for role in ('geometry', 'forward')) else 0,
        stage_selection=program['source_geometry_selection'],
        per_role_source='Same original CPU instance, particle pose, mesh, UV and visibility; preserve both draws')
    required = dict(geometry='Actual source mesh/UV0/RGBA/TBN and complete native particle/root TRS; reject unrepresented shear/WPO',
        source_vertex_color='Original COLOR stream, source particle tint/mesh-color composition supplied by FX contract',
        mesh_uv=deepcopy(uv), age=dict(required=any('UEFX_SystemAge' in program[role]['builtins'] for role in ('geometry', 'forward')),
            source='Original same-instance System.Age written by original Niagara update', **age),
        current='Original completed CPU data set and current native Position/Scale/MeshOrientation plus current primitive root',
        previous=(dict(required=True, source='Actual original adjacent previous pose and primitive root',
            native_bindings=['PrevPositionBinding', 'PrevScaleBinding', 'PrevMeshOrientationBinding'],
            proof='Compiled Native layout must contain true Previous attributes; SelectVFComponent current fallback is not acceptance',
            spawn='Native initial previous-pose rule; subsequent original updates keep real previous values',
            extra_history_payload=False) if motion['native'] == 'Precise' else dict(required=False, reason='Source ForceNoMotion')),
        flow='Real native WorldToInstance position/vector transforms; no identity or OwnerRoot-only inverse',
        raw_source_data='Preserve original Random/Custom data in original dataset; inactive shader streams need no extra material DP',
        source_motion_validation='Actual source renderer m_MotionVectors must equal native_renderer_contract.source_motion_vectors')
    targets = imported['targets'] + [value for spec in materials for value in (spec['master'], spec['instance'])]
    return dict(schema=SCHEMA, source_identity=source, revision=revision, roles=list(roles.values()),
        materials=materials, textures=imported['entries'], targets=sorted(targets), bindings={pid: bindings},
        required_source_inputs=required, native_renderer_contract=contract,
        source_runtime_certified=False, visual_calibrated=False,
        equivalence=dict(mode=prop['mode'], differences=[
            'Source Geometry surface channels map raw albedo/metallic/roughness/normal to native PBR; source encoded GBuffer/SH scheduling differs',
            'Own exact Forward RGB, including Flow/Fresnel/dither, maps to additive color draw with native depth instead of source Equal prepass',
            'Native opaque velocity consumes source current/previous pose semantics; source sqrt+bias MRT encoding and alpha are replaced',
            'ForceNoMotion disables object velocity in configured native renderer; UE camera/depth reconstruction may differ',
            'Flow uses actual native mesh-instance frame; original Unity per-draw runtime overrides are not recovered',
            'Mesh UV modules are mandatory source inputs; real native graph/atlas ABI and visible result remain to verify',
            'Flow Geometry is an explicit project stage choice, original pairing/runtime is not certified'] ))


def make_plan(material_source, dependency_source, *, texture_targets, revision, configuration, source_programs):
    """返回roles、required_source_inputs及Native合同；缺真实source输入时拒绝制作。

    source_programs来自原Shader提取者，不能由共享VP相似性合成。
    texture_targets必须属于相同revision的原纹理导入计划。
    """
    if not isinstance(revision, str) or not revision.strip():
        raise ValueError('投影材质需要明确的整批revision')
    config = _configuration(configuration)
    material, material_identity = _read(material_source)
    # 文件身份仍取原始字节；内存值沿既有 Material 边界统一 Native／旧导出布局。
    material = material_input(material)
    dependencies, dependency_identity = _read(dependency_source)
    pid = str(Path(material_source).name.split('.')[0])
    if (dependencies[pid]['type'] != 'Material'
            or Path(dependencies[pid]['nativeJson']).resolve() != Path(material_source).resolve()):
        raise ValueError('投影材质不属于当前准确dependency来源')
    if str(material['m_Shader']['m_PathID']) == PROP_SID:
        return _make_prop_plan(material, material_identity, dependencies, dependency_identity, pid,
            texture_targets=texture_targets, revision=revision, configuration=configuration,
            source_programs=source_programs, config=config)
    if str(material['m_Shader']['m_PathID']) != DECAL_SID:
        raise ValueError('当前投影计划只接受准确Decal SID；Prop由独立颜色/速度roles消费')
    policy, _ = _read(source_programs.get('shader_policy', POLICY))
    evidence = policy['shader_choices'][DECAL_SID]['source_evidence']
    selected = evidence['materials'][pid]
    if (material_identity['sha256'] != selected['materialSource']['sha256']
            or set(material['m_ShaderKeywords'].split()) != set(selected['serializedMaterialKeywords'])):
        raise ValueError('Decal源材质或序列化关键词身份不符')
    saved = material['m_SavedProperties']
    if saved['m_Floats']['_UsingNonPSR'] != 0:
        raise ValueError('本合同只覆盖实际PSR Decal，不猜NonPSR宿主')
    programs, program_identity = _read(source_programs.get('program_file', PROGRAM_FILE))
    record = selected['programCandidates']['fp'][0]
    program = programs['decal'][record['hash64']]
    _stage_selection(source_programs, program, material)
    parameters = {}
    for name, dim in program['material_params'].items():
        dynamic = name.startswith('_ParticleDecalLocalToWorldMatrix_R')
        value = [0.0] * dim if dynamic else _material_value(saved, name, dim, program['material_defaults'])
        origin = ('source_material' if name in saved['m_Floats'] or name in saved['m_Colors']
                  or name.endswith('_ST') else 'source_shader_default')
        parameters[name] = dict(_vector_parameter(value, dim, name),
            origin='original_cpu_particle' if dynamic else origin,
            **({'default_usage': 'DormantAuthoringOnly; every draw requires real CPU payload'} if dynamic else {}))
    for name, dim in program['parameters'].items():
        if name.startswith('Global_'):
            values = config['globals'][name]
            if not isinstance(values, list) or len(values) != 4:
                raise ValueError('投影全局配置缺实际float4：' + name)
            parameters[name] = dict(_vector_parameter(values, 4, name), origin='project_configuration')
        elif name == 'UEFX_SystemAge':
            parameters[name] = dict(dim=1, value=0.0, origin='original_cpu_system_age',
                                    default_usage='DormantAuthoringOnly')
        else:
            parameters[name] = dict(dim=4, value=[0.0] * 4, origin='original_cpu_particle',
                                    default_usage='DormantAuthoringOnly; every draw requires real CPU payload')
    parameters['UE_EmissiveOutputScale'] = dict(dim=1, value=config['emissive_output_scale'], origin='project_configuration')
    parameters['UE_ExposureCompensationWeight'] = dict(dim=1, value=config['exposure_compensation_weight'], origin='project_configuration')
    texture_pids = []
    for name in program['textures']:
        pointer = saved['m_TexEnvs'][name]['m_Texture']
        texture_pid = str(pointer['m_PathID'])
        if pointer['IsNull'] or texture_pid not in dependencies:
            raise ValueError('Decal活跃贴图缺真实引用：' + name)
        texture_pids.append(texture_pid)
    imported = plan_imports([dependency_source], revision=revision, selected_pids=texture_pids)
    expected_targets = imported['assets']
    if texture_targets != expected_targets:
        raise ValueError('投影纹理目标不等于同revision的准确导入计划')
    textures = {pid: item for pid, item in imported['entries'].items()}
    bound_textures = {name: texture_targets[str(saved['m_TexEnvs'][name]['m_Texture']['m_PathID'])]
                      for name in program['textures']}
    source = dict(material=material_identity, dependency=dependency_identity, material_pid=pid,
        shader_pid=DECAL_SID, source_programs=deepcopy(source_programs), program_file=program_identity,
        configuration=deepcopy(configuration), revision=revision)
    role = 'projected_decal'
    spec = dict(role=role, shader=program, params=parameters, textures=bound_textures,
        properties=dict(MaterialDomain='MD_DeferredDecal', BlendMode='BLEND_Translucent',
            ShadingModel='MSM_DefaultLit' if program['surface'] == 'native_pbr' else 'MSM_Unlit',
            bTangentSpaceNormal=False, bAutomaticallySetUsageInEditor=False),
        source_render_state=deepcopy(selected['resolvedSourceState']))
    identity = dict(schema=SCHEMA, source=source, spec=spec)
    spec['master'] = SHARED + '/Materials/' + version_name('M_ProjectedDecal_' + pid.replace('-', 'N'), identity)
    spec['instance'] = SHARED + '/MaterialInstances/' + version_name('MI_ProjectedDecal_' + pid.replace('-', 'N'), identity)
    contract = _renderer_contract(parameters, config)
    required = dict(raw_streams={name: dim for name, dim in RAW_STREAMS.items() if name in parameters},
        vector_attributes=contract['properties']['ParticleVectorAttributes'],
        projection_rows='A maps actual source mesh-local to Unity world, INCLUDING actual source Size; p=actual particle world center, n=Native projector world origin. Rows express diag(SourceSize)*inverse(A)*(receiverU-p), with affine w evaluated at n-p. Material multiplies original VP.o7 once, avoiding double division by Size',
        relative_origin='Material ActorPositionWS is actual Native projector origin; subtract in material graph before float Custom',
        coordinate_conversion='UE centimeters -> Unity meters C=(-X,Z,Y)',
        source_matrix='ProjectConfigured RenderedParticleAffine; forward basis columns retain hierarchy/shear/mirroring; original MPB matrix values are not recovered',
        original_mpb_recovered=False,
        conservative_volume=dict(mode=config['native_volume'], padding=config['native_enclosure_scale'],
            geometry=config['projector_geometry'], local_bounds=config['projector_local_bounds'],
            source_builtin_mesh_recovered=False,
            requirement='Enclose all configured source unit-cube corners after complete source affine, including shear; native transform does not replace source affine'),
        instance='OriginalSystem+OriginalInstanceId+completedCPUDataSet+TickCount+SimulationAge',
        time=config['time'], source_age_parameter='UEFX_SystemAge',
        before_publish='Finite vectors; invertible required projection/basis; exact current same-world original instance',
        no_draw='Native current data null/zero/renderer disabled or finite zero-volume particle invisible; invalid required frames fail before visibility filtering')
    differences = ['Source Front/Greater/half-resolution becomes native projector cull/depth and full-resolution DBuffer/emissive',
        'Native receiver eligibility and depth-derivative normal replace source CameraNormal channels; detailed normal/coverage differs',
        'PBR raw surface feeds native light/shadow/BRDF; source cluster BUF/environment/LUT lighting is not emulated',
        'Source receiver GBuffer blending/framebuffer alpha encoding becomes native DBuffer blend policy',
        'Configured unit-cube bounds replace unrecovered source builtin mesh; original MPB matrices remain unknown',
        'Padding>=4/3 puts configured source volume in native flat-fade region; NativeFade=1 and screen fade=0, source coverage/fade remains in shader',
        'Both source time groups explicitly use original System.Age; original game group clock/MPB values remain unknown']
    return dict(schema=SCHEMA, source_identity=source, revision=revision, roles=[role], materials=[spec],
        textures=textures, targets=sorted(imported['targets'] + [spec['master'], spec['instance']]),
        bindings={pid: {role: spec['instance']}}, required_source_inputs=required,
        native_renderer_contract=contract, source_runtime_certified=False, visual_calibrated=False,
        equivalence=dict(mode=config['mode'], differences=differences))


def validate_plan(plan):
    """制作前重建来源/配置合同；不将源码一致性当UE编译或画面验收。"""
    if not isinstance(plan, dict) or plan.get('schema') != SCHEMA:
        raise ValueError('不是当前投影材质计划')
    source = plan['source_identity']
    expected = make_plan(source['material']['path'], source['dependency']['path'],
        texture_targets={pid: item['path'] for pid, item in plan['textures'].items()},
        revision=source['revision'], configuration=source['configuration'], source_programs=source['source_programs'])
    if plan != expected:
        raise ValueError('投影材质计划与真实来源/配置不一致')
    return plan
