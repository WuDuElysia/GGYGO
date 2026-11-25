"""佩洛伊斯 Normal03 前半段刀弧和砸地时的贴地裂纹。"""
import json
from pathlib import Path

import unreal as ue

from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import NiagaraBuilder

LIB = ue.GGYGONiagaraCompileLibrary
EDITOR = ue.EditorAssetLibrary
SWEEPS = ('M00_root_andi_main_', 'M04_root_Trail_rot_', 'M06_root_MeleeTrail_andi_main_', 'M09_root_andi_main_')
BLADES = ('FXMD_DAO_001_ced427b6fbbf', 'FXMD_Circle_bf347410c141')
IMPACT = 'M15_root_decal__1__UEFX'
STAMP = 'Pyrios.Normal03CleaveFracture'
VERSION = 'sweep-1'
SURFACE_VERSION = 'shattered-2'
NS = 'NiagaraToolsets.NiagaraToolset_System.'
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


def extend_sweep(system, emitter, tool):
    extended = False
    for info in LIB.authoring_get_renderer_identities(system,emitter).renderers:
        if not info.renderer_class.endswith('NiagaraMeshRendererProperties'):
            continue
        renderer = ue.find_object(None, info.renderer_path)
        slots = list(renderer.get_editor_property('meshes'))
        changed = False
        for slot in slots:
            mesh = slot.get_editor_property('mesh')
            if mesh and mesh.get_name() in BLADES:
                # 两种原生弧面都在网格局部 XY；保留挂点、旋转、法向厚度。
                slot.set_editor_property('scale', ue.Vector(1.32, 1.32, 1.0))
                changed = True
        if changed:
            renderer.set_editor_property('meshes', slots)
            extended = True
    if not extended:
        return False
    ref = dict(system={'refPath':system.get_path_name()}, emitterName=emitter, rendererIndex=-1,
               scriptName='ParticleSpawnScript', moduleName='', inputNameStack=[])
    modules = tool(NS+'GetScriptStackInputValues',scriptRef=ref)
    for module in modules:
        for item in module['inputs']:
            if item['name'] != 'Particles.Lifetime':
                continue
            value = item['value']
            expr = value['value'].get('hlslExpression','')
            try:
                seconds = float(expr)
            except ValueError:
                continue
            value['value']['hlslExpression'] = format(seconds*1.25,'.9g')
            saved = tool(NS+'SetStackInputData',stackInputRef=dict(ref,moduleName=module['moduleName'],
                         inputNameStack=['Particles.Lifetime']),inputData=value)
            if saved != value:
                raise RuntimeError('刀弧寿命读回不符 '+emitter)
    return True


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


def refine_normal03(system, directory, tool, target, assign):
    names = [em.emitter_name for em in LIB.authoring_get_system_summary(system).emitters]
    surface = fracture_material(directory) if IMPACT in names else None
    if EDITOR.get_metadata_tag(system, STAMP) == VERSION:
        return False
    changed = False
    for name in names:
        if name.startswith(SWEEPS) and extend_sweep(system, name, tool):
            changed = True
        if name == IMPACT:
            add_fracture(system, surface, tool, target, assign)
            changed = True
    if changed:
        EDITOR.set_metadata_tag(system, STAMP, VERSION)
    return changed
