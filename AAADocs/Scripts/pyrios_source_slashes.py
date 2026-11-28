"""佩洛伊斯普攻原包刀面。每个材质实例对应各自的网格顶点流、纹理与原程序变体。"""
import json
from operator import eq

import unreal as ue


# 来自 Normal01 的组合制作记录和 Normal03 的分段制作记录。相同图纹在不同发射器上可能使用不同实例。
SOURCE_SURFACES = {
    'NS_Pyrios_Normal01_MainComposition_2a7c90937cab': {
        'M00_root_Trail_rot_Smoke_trail': 'MI_Eff_Objects_LKJ_GUID51a5af1cfffef0d489da7ac1b74b428c_b7a74746a1e8',
        'M00_root_Trail_rot_Smoke_Head': 'MI_Eff_Objects_Gl_GUID4bd39bb17c59bab4e9f27c417bc4501f_208dfeb79592',
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
        'M11_root_Trail_rot_bloom__1__UEFX': 'MI_Eff_Objects_UndefinedName_GUID90c46d939d3c4434ba0c8d322e734a2c_20a9e85070c7',
        'M11_root_Trail_rot_andi__6__UEFX': 'MI_Eff_Objects_UndefinedName_GUID71e6170c5ebb4d9468388e16bfc2a407_e6a0c8ab5274',
        'M11_root_Trail_rot_HighLight__3__UEFX': 'MI_Eff_Objects_UndefinedName_GUID5af9bc1e1bd42ac4ea2ade719947412f_feabd6aba987',
        'M11_root_Trail_rot_An_HighLight__4__UEFX': 'MI_Eff_Objects_UndefinedName_GUIDc4df72a78a3101e418284d5bb109c107_4439f7e1a7d4',
        'M11_root_Trail_rot_light_edge__3__UEFX': 'MI_Eff_Objects_UndefinedName_GUID3912249a10b128841b128c5a6ca8defd_c8a810b8733b',
        'M11_root_Trail_rot_bloom__3__UEFX': 'MI_Eff_Objects_UndefinedName_GUID7d418d14c985a7f4194dad15012b3829_300ac69d850a',
        'M11_root_Trail_rot_Shining__5__UEFX': 'MI_Eff_Objects_UndefinedName_GUID7c982a2c37c2b974ab645f1157c56e90_460999c61cda',
        'M11_root_Trail_rot_Smoke_Head__3__UEFX': 'MI_Eff_Objects_UndefinedName_GUID4013aef9cd100d247a5e070cd257965b_5eb784bd05c2',
        'M12_root_Trail_rot_HighLight_UEFX': 'MI_Eff_Objects_LKJ_GUID6cfcb6781f63a704fb97670a8c8a781a_8aeb989a7f97',
        'M12_root_Trail_rot_light_edge_UEFX': 'MI_Eff_Objects_LKJ_GUIDbd4b9c9095695f3458b9d6f8811d7613_43b46a12069d',
        'M12_root_Trail_rot_Smoke_trail_UEFX': 'MI_Eff_Objects_LKJ_GUID9e5143ba33a0998419daffdc21fc1339_17c6b46c9f88',
        'M12_root_Trail_rot_Smoke_Head_UEFX': 'MI_Eff_Objects_LKJ_GUID4fa86ebb41e59ea4ca07004f9cba7bcc_8b48724d50f8',
        'M12_root_Trail_rot_bloom_UEFX': 'MI_Eff_Objects_LKJ_GUID5a767948216a05b4bafacc3ab7701c34_bad8fa16266d',
        'M12_root_Trail_rot_Shining_UEFX': 'MI_Eff_Objects_LKJ_GUID0fc076df02e44b3489db13c3449b6f06_242e08331d10',
        'M09_root_andi_main_UEFX': 'MI_Eff_Objects_XL_GUID84886ddf1656e7b4a8c4a627b062d419_47ed8ebd0716',
        'M09_root_andi_main_HighLight_main_UEFX': 'MI_Eff_Objects_XL_GUID026b93635b2abf040adcb14604738e95_d7fde01298a8',
        'M09_root_andi_main_light_edge_UEFX': 'MI_Eff_Objects_XL_GUID4dc381e6df997c94ea265bc63ae1790f_0ea38604c054',
        'M09_root_andi_main_line_UEFX': 'MI_Eff_Objects_XL_GUIDa880635ae7874d24cbd32fdad4278593_841e7f4fee78',
        'M09_root_andi_main_bloom_UEFX': 'MI_Eff_Objects_XL_GUID250fc1a9ac56ec24a934f415085358c9_26f84020d82c',
    },
    'NS_Pyrios_Normal02_MainComposition_d7bd1888f9a7': {
        'M00_root_Trail_rot_HighLight': 'MI_Eff_Objects_LKJ_GUID6cfcb6781f63a704fb97670a8c8a781a_c0b36f669f7d',
        'M00_root_Trail_rot_light_edge': 'MI_Eff_Objects_LKJ_GUID93bbcefa9a0c9544d80a4a5a1b9c3fd6_9577471f949d',
        'M00_root_Trail_rot_Smoke_trail': 'MI_Eff_Objects_LKJ_GUID51a5af1cfffef0d489da7ac1b74b428c_7c4e9c023e49',
        'M00_root_Trail_rot_Smoke_Head': 'MI_Eff_Objects_Gl_GUID4bd39bb17c59bab4e9f27c417bc4501f_9d50e08c9d8e',
        'M00_root_Trail_rot_bloom': 'MI_Eff_Objects_LKJ_GUID3213633a82fc1934fa9f6f457be2eae4_7a47e3b6b719',
        'M00_root_Trail_rot_Shining': 'MI_Eff_Objects_LKJ_GUID5b0312e87ded4644ca3051a1169e3fef_16d89723bc62',
    },
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit04_a811afd462b6': {
        'M14_root_Trail_rot_HighLight_UEFX': 'MI_Eff_Objects_LKJ_GUID6cfcb6781f63a704fb97670a8c8a781a_8aeb989a7f97',
        'M14_root_Trail_rot_light_edge_UEFX': 'MI_Eff_Objects_LKJ_GUIDbd4b9c9095695f3458b9d6f8811d7613_31828544eb3b',
        'M14_root_Trail_rot_Smoke_trail_UEFX': 'MI_Eff_Objects_LKJ_GUID9e5143ba33a0998419daffdc21fc1339_17c6b46c9f88',
        'M14_root_Trail_rot_Smoke_Head_UEFX': 'MI_Eff_Objects_LKJ_GUID4fa86ebb41e59ea4ca07004f9cba7bcc_8b48724d50f8',
        'M14_root_Trail_rot_bloom_UEFX': 'MI_Eff_Objects_LKJ_GUID5a767948216a05b4bafacc3ab7701c34_bad8fa16266d',
        'M14_root_Trail_rot_Shining_UEFX': 'MI_Eff_Objects_LKJ_GUID0fc076df02e44b3489db13c3449b6f06_242e08331d10',
    },
}

LIB = ue.GGYGONiagaraCompileLibrary
MAT_DIR = '/Game/Characters/Shared/FX/ZZZ/MaterialInstances/'
SWEEP_MESH = '/Game/Characters/Shared/FX/ZZZ/Meshes/Cylinder005_efa096b130c7.Cylinder005_efa096b130c7'
BLADE_MESH = '/Game/Characters/Shared/FX/ZZZ/Meshes/FXMD_DAO_001_ced427b6fbbf.FXMD_DAO_001_ced427b6fbbf'


# 正式 FX 挂在骨架 root。测试场实测首刀 root 离地 66 cm，项目把刀弧绘制原点下移到脚底高度。
# 同一招的色层和折射场共同平移，原材质与粒子轨迹继续使用原局部坐标。
SOURCE_FIELDS = {
    'NS_Pyrios_Normal02_MainComposition_d7bd1888f9a7': ('M00_root_Trail_rot_Main_Distor',),
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit04_a811afd462b6': ('M14_root_Trail_rot_Main_Distor_UEFX',),
    'NS_Pyrios_Normal01_MainComposition_2a7c90937cab': ('M00_root_Trail_rot_Main_Distor',),
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit00_84b02fe541b2':
        ('M00_root_andi_main_Distor_UEFX', 'M04_root_Trail_rot_Main_Distor_UEFX'),
    'NS_Pyrios_Normal03_Phased_Pyrios_Normal03_MainComposition_07644e9c2bf4_Unit03_0365aeadd570':
        ('M09_root_andi_main_Distor_UEFX', 'M11_root_Trail_rot_Main_Distor__2__UEFX', 'M12_root_Trail_rot_Main_Distor_UEFX'),
}


# 第三段前三次挥动，按实际刃身在起笔与出笔之间的方向校准原刀面。
# 前缀与 SOURCE_SURFACES / SOURCE_FIELDS 共同限定具体渲染器。
SPACE_SWINGS = {
    'M00': (.034, (99, -76, -88), (.5356594, -.0313491, -.6469168, .5418347)),
    'M04': (.083, (-61, 65, -119), (.2516345, -.6902938, .6218227, .2711291)),
    'M09': (.126, (-146, -67, -18), (.0249107, .0118532, -.4316058, .9016404)),
}


def align_mesh_origin(data, system_name, emitter):
    renderer = ue.find_object(None, data.renderer_path)
    slots = list(renderer.get_editor_property('meshes'))
    if len(slots) != 1:
        raise RuntimeError('原刀光应只有一份网格 ' + data.renderer_path)
    slot = slots[0]
    target = ue.Vector(0, 0, -66)
    space = ue.NiagaraMeshPivotOffsetSpace.WORLD
    # 原刀面的原点在弧端。按角色自己的平面校准整道横斩与上挑的落点。
    if system_name.startswith('NS_Pyrios_Normal01_'):
        # 加上粒子中心后，弧心位于剑尖横扫圆心 (6, 38, 49) 厘米附近。
        target = ue.Vector(31, -17, -77)
        space = ue.NiagaraMeshPivotOffsetSpace.LOCAL
    elif system_name.startswith('NS_Pyrios_Normal02_'):
        target = ue.Vector(-25, -45, 28)
        space = ue.NiagaraMeshPivotOffsetSpace.LOCAL
    elif system_name.startswith('NS_Pyrios_Normal03_') and emitter[:3] in SPACE_SWINGS:
        target = ue.Vector(*SPACE_SWINGS[emitter[:3]][1])
        space = ue.NiagaraMeshPivotOffsetSpace.LOCAL
    if slot.pivot_offset == target and slot.pivot_offset_space == space:
        return False
    slot.pivot_offset = target
    slot.pivot_offset_space = space
    renderer.modify()
    renderer.set_editor_property('meshes', slots)
    return True


# 这两份原高光实例使用同一套弧形网格与烟纹。项目实例只重配刃腹遮罩和色阶。
FACE_MATERIALS = {
    'MI_Eff_Objects_LKJ_GUID6cfcb6781f63a704fb97670a8c8a781a_8aeb989a7f97': 'MI_Pyrios_SlashFace',
    'MI_Eff_Objects_LKJ_GUID6cfcb6781f63a704fb97670a8c8a781a_c0b36f669f7d': 'MI_Pyrios_UppercutFace',
}


def configure_slash_material(source, name, *, textures=None, vectors=None, scalars=None):
    directory = '/Game/Characters/Player/Pyrios/FX/Dawn'
    editor = ue.EditorAssetLibrary
    edit = ue.MaterialEditingLibrary
    path = directory + '/' + name
    instance = ue.load_asset(path) if editor.does_asset_exist(path) else None
    if instance and (not isinstance(instance, ue.MaterialInstanceConstant) or instance.parent != source):
        raise RuntimeError('刀光材质来源不符 ' + path)
    created = instance is None
    if created:
        instance = ue.AssetToolsHelpers.get_asset_tools().create_asset(
            name, directory, ue.MaterialInstanceConstant, ue.MaterialInstanceConstantFactoryNew())
        if not instance:
            raise RuntimeError('创建刀光材质失败 ' + path)
        edit.set_material_instance_parent(instance, source)

    def apply(getter, setter, parameters, equals):
        changed = False
        for key, value in (parameters or {}).items():
            if equals(getter(instance, key), value):
                continue
            setter(instance, key, value)
            if not equals(getter(instance, key), value):
                raise RuntimeError(f'{path} 材质参数回读不符 {key}')
            changed = True
        return changed

    dirty = apply(edit.get_material_instance_texture_parameter_value,
                  edit.set_material_instance_texture_parameter_value, textures, eq)
    dirty |= apply(edit.get_material_instance_vector_parameter_value,
                   edit.set_material_instance_vector_parameter_value, vectors, eq)
    dirty |= apply(edit.get_material_instance_scalar_parameter_value,
                   edit.set_material_instance_scalar_parameter_value, scalars, lambda a, b: abs(a - b) < .0001)
    if (created or dirty) and not editor.save_loaded_asset(instance, False):
        raise RuntimeError('刀光材质保存失败 ' + path)
    return instance


def opening_edge_material(source):
    """在首刀原刃缘材质的发光输出上增加短促峰值。针线、明暗和溶解仍由原图提供。"""
    from zzz_fx_material_ue import configure_native_custom
    editor = ue.EditorAssetLibrary
    edit = ue.MaterialEditingLibrary
    directory = '/Game/Characters/Player/Pyrios/FX/Dawn/'
    master_path = directory + 'M_Pyrios_OpeningEdge'
    instance_path = directory + 'MI_Pyrios_OpeningEdge'
    mat = (ue.load_asset(master_path) if editor.does_asset_exist(master_path)
           else editor.duplicate_asset(source.parent.get_path_name(), master_path))
    if not isinstance(mat, ue.Material):
        raise RuntimeError('首刀原刃缘着色图复制失败')
    prop = ue.MaterialProperty.MP_EMISSIVE_COLOR
    node = edit.get_material_property_input_node(mat, prop)
    if not node:
        raise RuntimeError('首刀原刃缘缺少自发光输出')
    # 白芯沿用原刃纹。峰值多出的能量以蓝光为主，经过相机泛光与色调映射后，
    # 白、浅青、蓝晕依次展开，尾段随原粒子退去。
    code = """
float luma = dot(max(Edge, 0), float3(.2126, .7152, .0722));
float pulse = smoothstep(.005, .17, Age) * (1 - smoothstep(.46, .93, Age));
float crest = luma * smoothstep(.04, 1.1, luma);
return Edge + crest * pulse * float3(.85, 11.0, 245.0);
"""
    origin = editor.get_metadata_tag(mat, 'OpeningEdgeSource')
    dirty = False
    if origin != source.parent.get_path_name():
        if origin:
            raise RuntimeError('首刀刃缘着色图来源变更')
        pin = edit.get_material_property_input_node_output_name(mat, prop)
        age = edit.create_material_expression(mat, ue.MaterialExpressionParticleRelativeTime, 480, 280)
        pulse = edit.create_material_expression(mat, ue.MaterialExpressionCustom, 830, 120)
        configure_native_custom(ue, pulse, ['Edge', 'Age'], code, 'CMOT_Float3', '首刀峰值刃光',
                                native_sync=lambda _, fn: fn())
        if not (edit.connect_material_expressions(node, pin, pulse, 'Edge')
                and edit.connect_material_expressions(age, '', pulse, 'Age')
                and edit.connect_material_property(pulse, '', prop)):
            raise RuntimeError('首刀刃光表达式接线失败')
        editor.set_metadata_tag(mat, 'OpeningEdgeSource', source.parent.get_path_name())
        dirty = True
    elif not isinstance(node, ue.MaterialExpressionCustom) or node.get_editor_property('description') != '首刀峰值刃光':
        raise RuntimeError('首刀刃缘发光节点与制作配置不符')
    elif node.get_editor_property('code') != code:
        node.set_editor_property('code', code)
        dirty = True
    if dirty:
        if edit.recompile_material(mat):
            raise RuntimeError('首刀刃光着色图编译失败')
        if not editor.save_loaded_asset(mat, False):
            raise RuntimeError('首刀刃光着色图保存失败')

    instance = (ue.load_asset(instance_path) if editor.does_asset_exist(instance_path)
                else editor.duplicate_asset(source.get_path_name(), instance_path))
    if not isinstance(instance, ue.MaterialInstanceConstant):
        raise RuntimeError('首刀原刃缘实例复制失败')
    if instance.parent == source.parent:
        edit.set_material_instance_parent(instance, mat)
        if not editor.save_loaded_asset(instance, False):
            raise RuntimeError('首刀刃缘实例保存失败')
    if instance.parent != mat:
        raise RuntimeError('首刀刃缘实例来源不符')
    # 固定原贴图上沿，向刃腹多铺一层浅青过渡；保留原高亮色阶给远处蓝晕供光。
    return configure_slash_material(
        mat, instance.get_name(), vectors={'_MainTex_ST': ue.LinearColor(1.1, 1.28, -.15, -.28)},
        scalars={'_PowerRGB': edit.get_material_instance_scalar_parameter_value(source, '_PowerRGB'),
                 '_PowerAlpha': 3.46})


def slash_material(system_name, emitter, source):
    opening = system_name == 'NS_Pyrios_Normal01_MainComposition_2a7c90937cab'
    if opening and emitter == 'M00_root_Trail_rot_light_edge':
        return opening_edge_material(source)
    if opening and emitter == 'M00_root_Trail_rot_Shining':
        # 内侧的细闪用原噪声和刀纹显影，降低它的白峰，避免在收笔处叠成硬白片。
        return configure_slash_material(
            source, 'MI_Pyrios_OpeningGlint', vectors={'_MultiplyParticleColor': ue.LinearColor(13, 21, 37, 1)},
            scalars={'_AlphaFade': .67, '_PowerRGB': .91})
    if opening and emitter == 'M00_root_Trail_rot_bloom':
        # 白芯和刃纹由独立刀面绘制。仅展宽软遮罩并提高光晕层的自发光。
        return configure_slash_material(
            source, 'MI_Pyrios_OpeningBloom',
            vectors={'_MainTex_ST': ue.LinearColor(1.3, .70, -.05, .15),
                     '_MultiplyParticleColor': ue.LinearColor(4.2, 14, 70, 1)},
            scalars={'_PowerRGB': 1.34, '_PowerAlpha': 1.38})

    if '_bloom' in emitter:
        edit = ue.MaterialEditingLibrary
        tint = edit.get_material_instance_vector_parameter_value(source, '_MultiplyParticleColor')
        falloff = edit.get_material_instance_scalar_parameter_value(source, '_PowerAlpha')
        # 上挑、空间斩和下劈各自继承原图纹、透明度与粒子寿命，峰值沿各自的刀弧展开。
        uv = edit.get_material_instance_vector_parameter_value(source, '_MainTex_ST')
        return configure_slash_material(
            source, 'MI_Pyrios_ComboBloom_' + source.get_name().rsplit('_', 1)[-1],
            vectors={'_MultiplyParticleColor': ue.LinearColor(tint.r * 1.7, tint.g * 1.95, tint.b * 1.8, tint.a),
                     '_MainTex_ST': ue.LinearColor(uv.r, uv.g * .88, uv.b, uv.a + uv.g * .06)},
            scalars={'_PowerAlpha': falloff * .84})

    name = FACE_MATERIALS.get(source.get_name())
    if not name:
        return source
    brush = ue.load_asset('/Game/Characters/Shared/FX/ZZZ/Textures/Eff_MeleeTrail_239_4f346e732ad4')
    if not isinstance(brush, ue.Texture2D):
        raise RuntimeError('缺少刀腹分叉笔纹 239')
    fade = ue.MaterialEditingLibrary.get_material_instance_scalar_parameter_value(source, '_AlphaFade')
    brush_uv = ue.LinearColor(.88, 1.05, .035, .016) if opening else ue.LinearColor(.64, 1.05, .13, .016)
    face_tint = ue.LinearColor(.95, 2.7, 7.6, 1) if opening else ue.LinearColor(.59, 2.9, 13, 1)
    return configure_slash_material(
        source, 'MI_Pyrios_OpeningFace' if opening else name,
        textures={'_MaskTex': brush},
        vectors={'_MaskTex_ST': brush_uv,
                 '_MultiplyParticleColor': face_tint},
        scalars={'_PowerAlpha': 1.12 if opening else .95, '_AlphaFade': fade * (.66 if opening else .68)})


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
        expected_mesh = SWEEP_MESH if emitter.startswith('M11_root_Trail_rot_') else BLADE_MESH
        if meshes != [expected_mesh] or len(slots) != 1:
            raise RuntimeError(f'{emitter} 的刀面或材质槽与原配置不符')
        if slots[0].get('userParamBinding', {}).get('parameter', {}).get('name', 'None') != 'None':
            raise RuntimeError(f'{emitter} 的材质由运行时参数覆盖')
        material = ue.load_asset(MAT_DIR + asset)
        if not isinstance(material, ue.MaterialInstanceConstant) or not material.parent or not material.parent.get_name().startswith('M_ZZZFX_ProjectConfigured_'):
            raise RuntimeError(f'{emitter} 缺少原程序移植材质 {asset}')
        changed = align_mesh_origin(data, system.get_name(), emitter) or changed
        path = slash_material(system.get_name(), emitter, material).get_path_name()
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
        changed = align_mesh_origin(data, system.get_name(), emitter) or changed
    return changed


def set_project_surface_enabled(system, emitter, material_name, enabled):
    """只切换指定材质的网格绘制，保留同发射器上的折射、光源和地面层。"""
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
        if props.get('bIsEnabled', True) == enabled:
            return False
        result = LIB.authoring_set_renderer_data(system, emitter, index, json.dumps(dict(bIsEnabled=enabled)))
        if not result.succeeded:
            raise RuntimeError(result.error)
        return True
    raise RuntimeError(f'{emitter} 找不到待替换的 {material_name}')

def disable_replaced_surface(system, emitter, material_name):
    return set_project_surface_enabled(system, emitter, material_name, False)


def align_slash_directions(system, tool, assign):
    """按本机原片的斩向校正原网格朝向。局部 Y 是角色前向，局部 Z 是竖直。"""
    from math import cos, radians, sin
    from zzz_fx_niagara_ue import NiagaraBuilder
    key = system.get_name()
    layers = [*SOURCE_SURFACES.get(key, {}), *SOURCE_FIELDS.get(key, ())]
    stamp = 'Pyrios.SourceSlashDirection'
    # 旧版已制作首刀亮面与空间斩。新增的首刀烟纹需要与原亮面共用同一朝向。
    if ue.EditorAssetLibrary.get_metadata_tag(system, stamp) == 'native-film-2':
        return False
    if ue.EditorAssetLibrary.get_metadata_tag(system, stamp) == 'native-film-1':
        layers = [n for n in layers if key.startswith('NS_Pyrios_Normal01_') and n.endswith(('Smoke_trail', 'Smoke_Head'))]
    work = []
    emitters = []
    for emitter in layers:
        if key.startswith('NS_Pyrios_Normal01_'):
            axis, angle = 'z', 180
        elif key.startswith('NS_Pyrios_Normal03_') and emitter.startswith('M00_'):
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
    ue.EditorAssetLibrary.set_metadata_tag(system, stamp, 'native-film-2')
    return True
