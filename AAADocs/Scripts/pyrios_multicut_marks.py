"""佩洛伊斯第三段起手的刀痕。沿已有刀带采样留下宽刃面与楔形收锋。"""
import json

import unreal as ue

from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import NiagaraBuilder


# 横向覆盖整块切面，亮边只占外沿。使用每刀自己的进度，尾部消散时棱线不游动。
SHADE = """
float along = saturate(Stroke.r);
float across = saturate(UV.y);
float fade = saturate(Life);
float tip = abs(2.0*along-1.0);
float notch = sin(along*13.0+across*4.0)*0.021 + (Ink.g-.5)*.027;
float spine = .59 + .13*sin(along*3.14159) - .11*along + notch;
float bevel = smoothstep(spine-.030,spine+.020,across);
float lit = saturate(.48 + .43*dot(normalize(Normal),float3(-.25,.38,.89)));
float3 shadow = lerp(float3(.055,.007,.14),float3(.125,.032,.28),lit);
float3 violet = lerp(float3(.26,.075,.84),float3(.21,.33,1.12),Stroke.g);
float3 face = lerp(shadow, violet*(.60+.38*lit),bevel);
float ridge = 1.0-smoothstep(.010,.071,abs(across-spine));
float edge = smoothstep(.78,.96,across+notch);
float3 silver = lerp(float3(.91,.77,1.8),float3(.57,1.34,1.76),Stroke.g);
face += silver*(edge*.99+ridge*.19);
float groove = 1.0-smoothstep(.01,.032,abs(across-(spine-.14+.048*sin(along*5.1))));
face *= 1.0-.40*groove;
face += Ink.g*violet*.40 + Ink.b*float3(.52,.37,.68)*(.45+.55*tip);
// 沿行刀方向把切口收成斜尖，亮刃多留一截，宽刀腹稍早消退。
float arc = saturate(UV.x);
float endTaper = smoothstep(0,.15,arc)*smoothstep(0,.22,1.0-arc);
float bladeDistance = abs(across-.77)/lerp(.77,.23,step(.77,across));
float silhouette = 1.0-smoothstep(.10+.85*endTaper,.18+.85*endTaper,bladeDistance);
float opacity = smoothstep(.01,.37,fade)*(.79+.13*lit)*silhouette;
Coverage = opacity;
return face*opacity;
"""


def slash_material(directory):
    editor = ue.EditorAssetLibrary
    name = 'M_Pyrios_MultiCutScar'
    path = directory+'/'+name
    mat = ue.load_asset(path) if editor.does_asset_exist(path) else None
    if mat and editor.get_metadata_tag(mat,'Pyrios.MultiCutSurface') == 'etched-1':
        return mat
    texture = ue.load_asset(directory+'/T_Pyrios_PrismInlay')
    if not isinstance(texture, ue.Texture2D):
        raise RuntimeError('三段刀痕缺少棱纹贴图')
    edit = ue.MaterialEditingLibrary
    if mat:
        edit.delete_all_material_expressions(mat)
    else:
        mat = ue.AssetToolsHelpers.get_asset_tools().create_asset(name, directory, ue.Material, ue.MaterialFactoryNew())
    mat.set_editor_properties(dict(blend_mode=ue.BlendMode.BLEND_ALPHA_COMPOSITE,
        shading_model=ue.MaterialShadingModel.MSM_UNLIT, two_sided=True, used_with_niagara_ribbons=True))
    uv = edit.create_material_expression(mat,ue.MaterialExpressionTextureCoordinate,-630,-120)
    ink = edit.create_material_expression(mat,ue.MaterialExpressionTextureSample,-630,0)
    ink.set_editor_properties(dict(texture=texture,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_MASKS))
    color = edit.create_material_expression(mat,ue.MaterialExpressionParticleColor,-630,160)
    normal = edit.create_material_expression(mat,ue.MaterialExpressionPixelNormalWS,-630,310)
    node = edit.create_material_expression(mat,ue.MaterialExpressionCustom,-210,35)
    configure_native_custom(ue,node,['UV','Ink','Stroke','Life','Normal'],SHADE,'CMOT_Float3','斩痕宽切面与收锋',
        native_sync=lambda _,call:call(),additional_outputs=[('Coverage','CMOT_Float1')])
    for source,pin,target in [(uv,'','UV'),(ink,'RGBA','Ink'),(color,'RGB','Stroke'),(color,'A','Life'),(normal,'','Normal')]:
        if not edit.connect_material_expressions(source,pin,node,target):
            raise RuntimeError('刀痕材质输入未连接 '+target)
    if (not edit.connect_material_property(node,'',ue.MaterialProperty.MP_EMISSIVE_COLOR)
            or not edit.connect_material_property(node,'Coverage',ue.MaterialProperty.MP_OPACITY)
            or edit.recompile_material(mat)):
        raise RuntimeError('刀痕材质编译失败')
    editor.set_metadata_tag(mat,'Pyrios.MultiCutSurface','etched-1')
    if not editor.save_loaded_asset(mat,False):
        raise RuntimeError('刀痕材质保存失败')
    return mat


def add_opening_marks(system, emitter, mat, tool, assign):
    lib = ue.GGYGONiagaraCompileLibrary
    original = lib.authoring_get_renderer_identities(system,emitter).renderers
    if len(original)!=1 or not original[0].renderer_class.endswith('NiagaraRibbonRendererProperties'):
        raise RuntimeError('第三段起手需要现有的单层武器刀带')
    ps,pu = 'ParticleSpawnScript','ParticleUpdateScript'
    # 刀痕仅在前三次分刀时采样。每个截面的位置、方向来自本帧实际武器，新采样不会拖动旧刀痕。
    phase = ('Emitter.Age < 0.095 ? Emitter.Age/0.095 : '
             '(Emitter.Age < 0.20 ? (Emitter.Age-0.095)/0.105 : (Emitter.Age-0.20)/0.20)')
    work = [assign(ps,emitter=emitter,CutActive=('Bool','Emitter.Age < 0.40'),CutPhase=('Float','saturate('+phase+')'),
                   CutTone=('Float','Emitter.Age < 0.095 ? 0.0 : (Emitter.Age < 0.20 ? 0.5 : 1.0)'))]
    work.append(assign(ps,emitter=emitter,
        CutWidth=('Float','Particles.CutActive ? Particles.RibbonWidth*(0.035+0.965*pow(max(0.0,sin(3.141593*Particles.CutPhase)),0.60)) : 0.0'),
        CutCenter=('Position','Particles.Position - Particles.RibbonFacing*Particles.RibbonWidth*(0.06+0.23*abs(2.0*Particles.CutPhase-1.0))')))
    for stage in (ps,pu):
        work.append(assign(stage,emitter=emitter,
            CutColor=('LinearColor','float4(Particles.CutPhase,Particles.CutTone,0,Particles.CutActive ? saturate((1.0-Particles.NormalizedAge)*1.7) : 0.0)'),
            EdgeColor=('LinearColor','float4(1,1,1,Particles.CutActive ? 0.22*saturate(1.0-Particles.NormalizedAge*1.70) : Particles.Color.w)')))
    built = tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch',system={'refPath':system.get_path_name()},workItems=work)
    if not built.get('bApplied'):
        raise RuntimeError(built.get('error','起手刀痕制作失败'))
    bind = NiagaraBuilder.attribute_binding
    def configure(index,props):
        result = lib.authoring_set_renderer_data(system,emitter,index,json.dumps(props))
        if not result.succeeded:
            raise RuntimeError(result.error)
    configure(original[0].renderer_index,dict(ColorBinding=bind('Particles.EdgeColor')))
    mark = lib.authoring_add_renderer(system,emitter,ue.load_class(None,'/Script/Niagara.NiagaraRibbonRendererProperties'))
    if not mark.succeeded:
        raise RuntimeError(mark.error)
    configure(mark.renderer_index,{'Shape':'Custom'})
    # 靠近切刃收薄，背棱厚。正反面有独立斜面，从侧视也能读出刀痕的宽腹。
    profile = [(-.50,0),(-.35,-.078),(-.11,-.145),(.25,-.098),(.45,-.027),
               (.50,0),(.40,.060),(.16,.192),(-.12,.255),(-.39,.131)]
    verts = [dict(Position=dict(X=x,Y=y),TextureV=x+.50) for x,y in profile]
    configure(mark.renderer_index,dict(Material=mat.get_path_name(),FacingMode='CustomSideVector',MaxNumRibbons=3,
        bUseGPUInit=False,TessellationMode='Automatic',CustomVertices=verts,bCustomShapeClosed=True,
        PositionBinding=bind('Particles.CutCenter'),RibbonWidthBinding=bind('Particles.CutWidth'),
        RibbonFacingBinding=bind('Particles.RibbonFacing'),ColorBinding=bind('Particles.CutColor')))
    linked = lib.configure_ribbon_unique_id(system,emitter,mark.renderer_index,'Particles.BladeStroke')
    if not linked.applied:
        raise RuntimeError(linked.error)
