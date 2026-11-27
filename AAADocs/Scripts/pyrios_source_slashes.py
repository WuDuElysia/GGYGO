"""佩洛伊斯普攻原包刀面。每个材质实例对应各自的网格顶点流、纹理与原程序变体。"""
import json

import unreal as ue


# 来自 Normal01 的组合制作记录和 Normal03 的分段制作记录。相同图纹在不同发射器上可能使用不同实例。
SOURCE_SURFACES = {
    'NS_Pyrios_Normal01_MainComposition_2a7c90937cab': {
        'M00_root_Trail_rot_HighLight': 'MI_Eff_Objects_LKJ_GUID6cfcb6781f63a704fb97670a8c8a781a_8aeb989a7f97',
        'M00_root_Trail_rot_light_edge': 'MI_Eff_Objects_LKJ_GUID93bbcefa9a0c9544d80a4a5a1b9c3fd6_586ffa00867e',
        'M00_root_Trail_rot_bloom': 'MI_Eff_Objects_LKJ_GUID3213633a82fc1934fa9f6f457be2eae4_304124c40135',
        'M00_root_Trail_rot_Shining': 'MI_Eff_Objects_LKJ_GUID5b0312e87ded4644ca3051a1169e3fef_3fcc6f2064ed',
    },
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit00_84b02fe541b2': {
        'M00_root_andi_main_UEFX': 'MI_Eff_Objects_XL_GUID84886ddf1656e7b4a8c4a627b062d419_47ed8ebd0716',
        'M00_root_andi_main_HighLight_main_UEFX': 'MI_Eff_Objects_XL_GUID026b93635b2abf040adcb14604738e95_8bd817fc605e',
        'M00_root_andi_main_light_edge_UEFX': 'MI_Eff_Objects_XL_GUID4dc381e6df997c94ea265bc63ae1790f_556addd379e1',
        'M00_root_andi_main_line_UEFX': 'MI_Eff_Objects_XL_GUIDa880635ae7874d24cbd32fdad4278593_4ab06fc679ed',
        'M00_root_andi_main_bloom_UEFX': 'MI_Eff_Objects_XL_GUID250fc1a9ac56ec24a934f415085358c9_ecb302b3d28a',
    },
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit01_e3c8c9a42aa0': {
        'M04_root_Trail_rot_HighLight_UEFX': 'MI_Eff_Objects_XL_GUID00285030f66023545b850373a220528c_80112536f42e',
        'M04_root_Trail_rot_light_edge_UEFX': 'MI_Eff_Objects_XL_GUIDbe5cb3732d739b543a626a825a023641_cac881dfa797',
        'M04_root_Trail_rot_bloom_UEFX': 'MI_Eff_Objects_XL_GUID48748ac0b3b323e4f90d945391c805eb_55cbcf7ef222',
        'M04_root_Trail_rot_andi_UEFX': 'MI_Eff_Objects_XL_GUID2d323b2e5c70593418b5063a9ba73083_603e2332bfdc',
        'M04_root_Trail_rot_Line_Side_UEFX': 'MI_Eff_Objects_XL_GUIDf2f9fd33fd8050742a4d3a227cc994e5_ae92847177fe',
        'M04_root_Trail_rot_Shining_UEFX': 'MI_Eff_Objects_XL_GUID6713655e752a41248be3600f8043b99b_9ce766964cb8',
        'M04_root_Trail_rot_Line_Side__1__UEFX': 'MI_Eff_Objects_XL_GUID3bb950557a7035943a2fed76b880e0cc_f461c647b46c',
    },
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit02_2394eebd80d7': {
        'M08_root_Particle_System_UEFX': 'MI_Eff_Objects_XL_GUID87945e2760e662744ba655930eabbc3a_b78f841766cc',
    },
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit03_0365aeadd570': {
        'M09_root_andi_main_UEFX': 'MI_Eff_Objects_XL_GUID84886ddf1656e7b4a8c4a627b062d419_47ed8ebd0716',
        'M09_root_andi_main_HighLight_main_UEFX': 'MI_Eff_Objects_XL_GUID026b93635b2abf040adcb14604738e95_d7fde01298a8',
        'M09_root_andi_main_light_edge_UEFX': 'MI_Eff_Objects_XL_GUID4dc381e6df997c94ea265bc63ae1790f_0ea38604c054',
        'M09_root_andi_main_line_UEFX': 'MI_Eff_Objects_XL_GUIDa880635ae7874d24cbd32fdad4278593_841e7f4fee78',
        'M09_root_andi_main_bloom_UEFX': 'MI_Eff_Objects_XL_GUID250fc1a9ac56ec24a934f415085358c9_26f84020d82c',
    },
}

LIB = ue.GGYGONiagaraCompileLibrary
MAT_DIR = '/Game/Characters/Shared/FX/ZZZ/MaterialInstances/'
BLADE_MESH = '/Game/Characters/Shared/FX/ZZZ/Meshes/FXMD_DAO_001_ced427b6fbbf.FXMD_DAO_001_ced427b6fbbf'


# 正式 FX 挂在骨架 root。测试场实测首刀 root 离地 66 cm，项目把刀弧绘制原点下移到脚底高度。
# 同一招的色层和折射场共同平移，原材质与粒子轨迹继续使用原局部坐标。
SOURCE_FIELDS = {
    'NS_Pyrios_Normal01_MainComposition_2a7c90937cab': ('M00_root_Trail_rot_Main_Distor',),
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit00_84b02fe541b2':
        ('M00_root_andi_main_Distor_UEFX', 'M04_root_Trail_rot_Main_Distor_UEFX'),
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit03_0365aeadd570':
        ('M09_root_andi_main_Distor_UEFX',),
}


def align_mesh_origin(data):
    renderer = ue.find_object(None, data.renderer_path)
    slots = list(renderer.get_editor_property('meshes'))
    if len(slots) != 1:
        raise RuntimeError('原刀光应只有一份网格 ' + data.renderer_path)
    slot = slots[0]
    target = ue.Vector(0, 0, -66)
    if slot.pivot_offset == target and slot.pivot_offset_space == ue.NiagaraMeshPivotOffsetSpace.WORLD:
        return False
    slot.pivot_offset = target
    slot.pivot_offset_space = ue.NiagaraMeshPivotOffsetSpace.WORLD
    renderer.modify()
    renderer.set_editor_property('meshes', slots)
    return True


def restore_source_surfaces(system):
    """恢复原发射器的颜色绘制；扰动场、地面贴花各走自己的渲染器。"""
    surfaces = SOURCE_SURFACES.get(system.get_name(), {})
    changed = False
    for emitter, asset in surfaces.items():
        ids = LIB.authoring_get_renderer_identities(system, emitter)
        if not ids.succeeded or len(ids.renderers) != 1:
            raise RuntimeError(f'{emitter} 缺少唯一的原网格渲染器')
        renderer = ids.renderers[0]
        if not renderer.renderer_class.endswith('.NiagaraMeshRendererProperties'):
            raise RuntimeError(f'{emitter} 不是原刀面网格')
        index = renderer.renderer_index
        data = LIB.authoring_get_renderer_data(system, emitter, index)
        if not data.succeeded:
            raise RuntimeError(data.error)
        props = json.loads(data.property_values)
        meshes = [entry.get('mesh', {}).get('refPath') for entry in props.get('Meshes', [])]
        slots = props.get('OverrideMaterials', [])
        if meshes != [BLADE_MESH] or len(slots) != 1:
            raise RuntimeError(f'{emitter} 的刀面或材质槽与原配置不符')
        if slots[0].get('userParamBinding', {}).get('parameter', {}).get('name', 'None') != 'None':
            raise RuntimeError(f'{emitter} 的材质由运行时参数覆盖')
        material = ue.load_asset(MAT_DIR + asset)
        if not isinstance(material, ue.MaterialInstanceConstant) or not material.parent or not material.parent.get_name().startswith('M_ZZZFX_ProjectConfigured_'):
            raise RuntimeError(f'{emitter} 缺少原程序移植材质 {asset}')
        changed = align_mesh_origin(data) or changed
        path = material.get_path_name()
        if props.get('bIsEnabled', True) and props.get('bOverrideMaterials') and slots[0].get('explicitMat', {}).get('refPath') == path:
            continue
        update = dict(bIsEnabled=True, bOverrideMaterials=True, OverrideMaterials=[dict(ExplicitMat=path)])
        result = LIB.authoring_set_renderer_data(system, emitter, index, json.dumps(update))
        if not result.succeeded:
            raise RuntimeError(result.error)
        changed = True
    for emitter in SOURCE_FIELDS.get(system.get_name(), ()):
        data = LIB.authoring_get_renderer_data(system, emitter, 0)
        if not data.succeeded or not data.renderer_class.endswith('.GGYGOSignedFieldMeshRendererProperties'):
            raise RuntimeError(f'{emitter} 缺少原折射网格')
        changed = align_mesh_origin(data) or changed
    return changed


def disable_replaced_surface(system, emitter, material_name):
    """只关闭被替换的项目刀面，保留同发射器上的折射、光源和地面层。"""
    ids = LIB.authoring_get_renderer_identities(system, emitter)
    if not ids.succeeded:
        raise RuntimeError(ids.error)
    for renderer in ids.renderers:
        if not renderer.renderer_class.endswith('.NiagaraMeshRendererProperties'):
            continue
        index = renderer.renderer_index
        data = LIB.authoring_get_renderer_data(system, emitter, index)
        if not data.succeeded:
            raise RuntimeError(data.error)
        props = json.loads(data.property_values)
        if not any(slot.get('explicitMat', {}).get('refPath', '').endswith('.' + material_name)
                   for slot in props.get('OverrideMaterials', [])):
            continue
        if not props.get('bIsEnabled', True):
            return False
        result = LIB.authoring_set_renderer_data(system, emitter, index, json.dumps(dict(bIsEnabled=False)))
        if not result.succeeded:
            raise RuntimeError(result.error)
        return True
    raise RuntimeError(f'{emitter} 找不到待替换的 {material_name}')

def align_slash_directions(system, tool, assign):
    """按本机原片的斩向校正原网格朝向。局部 Y 是角色前向，局部 Z 是竖直。"""
    from math import cos, radians, sin
    from zzz_fx_niagara_ue import NiagaraBuilder
    key = system.get_name()
    layers = [*SOURCE_SURFACES.get(key, {}), *SOURCE_FIELDS.get(key, ())]
    stamp = 'Pyrios.SourceSlashDirection'
    if ue.EditorAssetLibrary.get_metadata_tag(system, stamp) == 'native-film-1':
        return False
    work = []
    emitters = []
    for emitter in layers:
        if key.startswith('NS_Pyrios_Normal01_'):
            axis, angle = 'z', 180
        elif emitter.startswith('M00_'):
            axis, angle = 'y', -28
        elif emitter.startswith('M04_'):
            axis, angle = 'y', -38
        elif emitter.startswith('M09_'):
            axis, angle = 'y', -12
        else:
            continue
        v = sin(radians(angle)/2)
        axis_vector = f'float3(0,{v:.9f},0)' if axis == 'y' else f'float3(0,0,{v:.9f})'
        w = cos(radians(angle)/2)
        q = 'Particles.MeshOrientation'
        rotation = (f'float4({w:.9f}*{q}.xyz+{q}.w*{axis_vector}+cross({axis_vector},{q}.xyz),'
                    f'{w:.9f}*{q}.w-dot({axis_vector},{q}.xyz))')
        for script in ('ParticleSpawnScript','ParticleUpdateScript'):
            work.append(assign(script, emitter=emitter, SourceSlashOrientation=('Quat', rotation)))
        emitters.append(emitter)
    if not work:
        return False
    result = tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch',
                  system={'refPath':system.get_path_name()}, workItems=work)
    if not result.get('bApplied'):
        raise RuntimeError(result.get('error','原刀面方向制作失败'))
    binding = NiagaraBuilder.attribute_binding('Particles.SourceSlashOrientation')
    for emitter in emitters:
        result = LIB.authoring_set_renderer_data(system, emitter, 0, json.dumps({'MeshOrientationBinding':binding}))
        if not result.succeeded:
            raise RuntimeError(result.error)
    ue.EditorAssetLibrary.set_metadata_tag(system, stamp, 'native-film-1')
    return True
