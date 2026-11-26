"""佩洛伊斯 Normal03 前半段刀弧和砸地时的贴地裂纹。"""
import json
from pathlib import Path

import unreal as ue

from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import NiagaraBuilder

LIB = ue.GGYGONiagaraCompileLibrary
EDITOR = ue.EditorAssetLibrary
SWEEPS = ('M00_root_andi_main_', 'M04_root_Trail_rot_', 'M06_root_MeleeTrail_andi_main_', 'M09_root_andi_main_',
          'M11_root_Trail_rot_', 'M12_root_Trail_rot_', 'M14_root_Trail_rot_')
IMPACT = 'M15_root_decal__1__UEFX'
STAMP = 'Pyrios.Normal03CleaveFracture'
VERSION = 'sweep-1'
SURFACE_VERSION = 'shattered-2'
SHADE = """
float age = saturate(Clock.r);
float radius = length((UV-0.5)*2.0);
float front = 0.24 + 1.18*smoothstep(0.0,0.105,age);
float open = 1-smoothstep(front-0.12,front,radius);
float close = 1-smoothstep(0.69,1,age);
Coverage = saturate(max(Ink.r,max(Ink.g,Ink.b))*1.65)*open*close;
float hot = 1-smoothstep(0.18,0.74,age);
float3 seam = lerp(float3(1.95,0.34,0.09),float3(0.24,0.32,2.35),saturate(radius*2));
SeamLight = open*close*(Ink.b*seam*(hot*1.72+0.025)+Ink.g*float3(0.11,0.15,0.23)*hot);
return lerp(float3(0.007,0.004,0.018),float3(0.46,0.43,0.51),Ink.g);
"""
GROUND_QUERY = """
bool hit; bool inside; float3 impactPosition; float3 normal; float friction; float restitution; int surface;
float3 start = Particles.Position + float3(0,0,50);
float3 end = Particles.Position - float3(0,0,200);
{{DI}}.PerformCollisionQuerySyncCPU(start,end,3,false,false,hit,inside,impactPosition,normal,friction,restitution,surface);
{{OUT:Particles.FractureVisible}} = hit && !inside && normal.z > 0.55;
{{OUT:Particles.FracturePosition}} = impactPosition + normal*0.6;
float4 rotation = float4(cross(float3(1,0,0),-normal),1.0-normal.x);
{{OUT:Particles.FractureRotation}} = rotation*rsqrt(max(0.001,dot(rotation,rotation)));
"""


def fracture_material(directory):
    edit = ue.MaterialEditingLibrary
    tools = ue.AssetToolsHelpers.get_asset_tools()
    name = 'M_Pyrios_SlamFracture'
    path = directory + '/' + name
    mat = ue.load_asset(path) if EDITOR.does_asset_exist(path) else None
    if mat and EDITOR.get_metadata_tag(mat, STAMP) == SURFACE_VERSION:
        return mat
    tex_name = 'T_Pyrios_SlamFracture'
    tex_path = directory + '/' + tex_name
    texture = ue.load_asset(tex_path) if EDITOR.does_asset_exist(tex_path) else None
    if not texture or EDITOR.get_metadata_tag(texture, STAMP) != SURFACE_VERSION:
        project = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
        task = ue.AssetImportTask()
        task.set_editor_properties(dict(filename=str(project/'AAADocs/Assets/Pyrios/FX'/(tex_name+'.png')),
            destination_path=directory, destination_name=tex_name, automated=True, replace_existing=True, save=False))
        tools.import_asset_tasks([task])
    texture = ue.load_asset(tex_path)
    if not isinstance(texture, ue.Texture2D):
        raise RuntimeError('缺少砸地裂纹贴图 '+tex_path)
    texture.set_editor_properties(dict(srgb=False, compression_settings=ue.TextureCompressionSettings.TC_MASKS,
        address_x=ue.TextureAddress.TA_CLAMP, address_y=ue.TextureAddress.TA_CLAMP))
    EDITOR.set_metadata_tag(texture, STAMP, SURFACE_VERSION)
    if not EDITOR.save_loaded_asset(texture, False):
        raise RuntimeError('保存裂纹贴图失败')
    if mat:
        edit.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, directory, ue.Material, ue.MaterialFactoryNew())
    mat.set_editor_properties(dict(material_domain=ue.MaterialDomain.MD_DEFERRED_DECAL, blend_mode=ue.BlendMode.BLEND_TRANSLUCENT))
    uv = edit.create_material_expression(mat, ue.MaterialExpressionTextureCoordinate, -640, -150)
    sampler = edit.create_material_expression(mat, ue.MaterialExpressionTextureSample, -640, 10)
    sampler.set_editor_properties(dict(texture=texture, sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_MASKS))
    color = edit.create_material_expression(mat, ue.MaterialExpressionDecalColor, -640, 210)
    shader = edit.create_material_expression(mat, ue.MaterialExpressionCustom, -200, 0)
    configure_native_custom(ue, shader, ['UV','Ink','Clock'], SHADE, 'CMOT_Float3', '裂隙扩散、岩壁和热缝冷却',
        native_sync=lambda _, call: call(), additional_outputs=[('Coverage','CMOT_Float1'),('SeamLight','CMOT_Float3')])
    for node, pin, target in [(uv,'','UV'),(sampler,'RGB','Ink'),(color,'','Clock')]:
        if not edit.connect_material_expressions(node, pin, shader, target):
            raise RuntimeError('裂纹材质输入接线失败 '+target)
    for output, prop in [('',ue.MaterialProperty.MP_BASE_COLOR),('Coverage',ue.MaterialProperty.MP_OPACITY),
                         ('SeamLight',ue.MaterialProperty.MP_EMISSIVE_COLOR)]:
        if not edit.connect_material_property(shader, output, prop):
            raise RuntimeError('裂纹材质输出接线失败 '+output)
    if edit.recompile_material(mat):
        raise RuntimeError('裂纹材质编译失败')
    EDITOR.set_metadata_tag(mat, STAMP, SURFACE_VERSION)
    if not EDITOR.save_loaded_asset(mat, False):
        raise RuntimeError('保存裂纹材质失败')
    return mat


def disable_baked_sweep(system, emitter, classes):
    # LinePoint 的横线和暗边也有 Sprite/Ribbon 版本，按原层移除，保留残影人物和砸地层。
    changed = False
    for info in LIB.authoring_get_renderer_identities(system, emitter).renderers:
        if not info.renderer_class.endswith(classes):
            continue
        props = json.loads(LIB.authoring_get_renderer_data(system, emitter, info.renderer_index).property_values)
        if props.get('bIsEnabled', True):
            result = LIB.authoring_set_renderer_data(system, emitter, info.renderer_index, json.dumps({'bIsEnabled':False}))
            if not result.succeeded:
                raise RuntimeError(result.error)
            changed = True
    return changed


def add_fracture(system, mat, tool, target, assign):
    di = ue.new_object(ue.load_class(None,'/Script/Niagara.NiagaraDataInterfaceCollisionQuery'))
    ps = 'ParticleSpawnScript'
    work = [dict(kind='ParticleRead',emitterName=IMPACT,scriptName=ps,interfaceTemplate={'refPath':di.get_path_name()},
        outputTargets=[target('FractureVisible','Bool'),target('FracturePosition','Position'),target('FractureRotation','Quat')],
        hlslBodyTemplate=GROUND_QUERY)]
    work.append(dict(assign(ps, FractureSize=('Vector','float3(18,350,330)'),FractureOrder=('Int','50'),
                    FractureColor=('LinearColor','float4(0,1,1,1)')),emitterName=IMPACT))
    work.append(dict(assign('ParticleUpdateScript',FractureColor=('LinearColor','float4(Particles.NormalizedAge,1,1,1)')),
                     emitterName=IMPACT))
    built = tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch',system={'refPath':system.get_path_name()},workItems=work)
    if not built.get('bApplied'):
        raise RuntimeError(built.get('error','裂纹 Niagara 制作失败'))
    result=LIB.authoring_add_renderer(system,IMPACT,ue.load_class(None,'/Script/Niagara.NiagaraDecalRendererProperties'))
    if not result.succeeded:
        raise RuntimeError(result.error)
    bind=NiagaraBuilder.attribute_binding
    props=dict(Material=mat.get_path_name(),PositionBinding=bind('Particles.FracturePosition'),
        DecalOrientationBinding=bind('Particles.FractureRotation'),DecalSizeBinding=bind('Particles.FractureSize'),
        DecalColorBinding=bind('Particles.FractureColor'),DecalVisibleBinding=bind('Particles.FractureVisible'),
        DecalSortOrderBinding=bind('Particles.FractureOrder'),DecalScreenSizeFade=0.0)
    configured=LIB.authoring_set_renderer_data(system,IMPACT,result.renderer_index,json.dumps(props))
    if not configured.succeeded:
        raise RuntimeError(configured.error)


def align_blade_wake(system, name, tool, target, weapon_frame):
    # 原折射网格最长约 18.4 米。将可见扰动限制在刀尖内侧的一小段，正负场继续用原材质。
    di, sample = weapon_frame()
    sample += """
bool valid = Count == 2 && Base >= 0 && Tip >= 0 && Width > 1.0;
float3 along = Axis / max(Width,0.001);
float4 q = float4(0,-along.z,along.y,1.0+along.x);
{{OUT:Particles.CutWakeValid}} = valid;
{{OUT:Particles.CutWakeOrigin}} = A + 0.78*Axis;
{{OUT:Particles.CutWakeScale}} = valid ? (Width/1842.0)*float3(0.40,0.12,0.12) : float3(0,0,0);
{{OUT:Particles.CutWakeRotation}} = dot(q,q) > 0.0001 ? q*rsqrt(max(dot(q,q),0.0001)) : float4(0,0,1,0);
"""
    outputs = [target('CutWakeValid','Bool'),target('CutWakeOrigin','Position'),
               target('CutWakeScale','Vector'),target('CutWakeRotation','Quat')]
    work = [dict(kind='ParticleRead',emitterName=name,scriptName=script,
                 interfaceTemplate={'refPath':di.get_path_name()},outputTargets=outputs,hlslBodyTemplate=sample)
            for script in ('ParticleSpawnScript','ParticleUpdateScript')]
    result = tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch',
                  system={'refPath':system.get_path_name()},workItems=work)
    if not result.get('bApplied'):
        raise RuntimeError(result.get('error','刀尖折射制作失败'))
    renderers = LIB.authoring_get_renderer_identities(system,name).renderers
    if len(renderers)!=1 or not renderers[0].renderer_class.endswith('GGYGOSignedFieldMeshRendererProperties'):
        raise RuntimeError('原刀光折射层与制作配置不符 '+name)
    bind = NiagaraBuilder.attribute_binding
    props = dict(PositionBinding=bind('Particles.CutWakeOrigin'), ScaleBinding=bind('Particles.CutWakeScale'),
                 MeshOrientationBinding=bind('Particles.CutWakeRotation'))
    saved = LIB.authoring_set_renderer_data(system,name,renderers[0].renderer_index,json.dumps(props))
    if not saved.succeeded:
        raise RuntimeError(saved.error)


def refine_normal03(system, directory, tool, target, assign, weapon_frame):
    names = [em.emitter_name for em in LIB.authoring_get_system_summary(system).emitters]
    surface = fracture_material(directory) if IMPACT in names else None
    has_fracture = EDITOR.get_metadata_tag(system, STAMP) == VERSION
    changed = False
    for name in names:
        if name.startswith(SWEEPS) and disable_baked_sweep(system, name, ('NiagaraMeshRendererProperties',)):
            changed = True
        if name.startswith('M05_root_') or (name.startswith(('M02_','M06_','M07_')) and 'LinePoint' in name):
            if disable_baked_sweep(system, name, ('NiagaraMeshRendererProperties','NiagaraSpriteRendererProperties','NiagaraRibbonRendererProperties')):
                changed = True
        if name == 'M06_root_MeleeTrail_andi_main_Distor_UEFX' and EDITOR.get_metadata_tag(system,'Pyrios.Normal03BladeWake') != 'blade-tip-1':
            align_blade_wake(system,name,tool,target,weapon_frame)
            EDITOR.set_metadata_tag(system,'Pyrios.Normal03BladeWake','blade-tip-1')
            changed = True
        if name == IMPACT and not has_fracture:
            add_fracture(system, surface, tool, target, assign)
            changed = True
    if changed:
        EDITOR.set_metadata_tag(system, STAMP, VERSION)
    return changed
