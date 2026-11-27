"""首刀的定形月牙与三段切口的地面蓝光。两层均由原 Niagara 表现窗口驱动。"""
import json
from pathlib import Path
from math import cos, pi, sin

import unreal as ue

from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import EMPTY_EMITTER, NiagaraBuilder

EDITOR = ue.EditorAssetLibrary
LIB = ue.GGYGONiagaraCompileLibrary
ARC = 'Pyrios_OpeningCrescent'
ARC_VERSION = 'horizontal-crescent-4'
ARC_SURFACE_VERSION = 'pearl-crescent-16'
WASH_VERSION = 'fanned-reflection-12'
TAG = 'Pyrios.AuthoredSlash'

# 时间沿整张弧面推进。白晕在挥刀前半拍变宽，后半拍只剩远侧的一段亮弦。
ARC_SHADE = """
float u = saturate(UV.x);
float t = saturate(Clock.r);
// 笔锋整片升起；热白沿外刃跑过，冷蓝刀腹稍后才显影。
float front = .95-.73*smoothstep(.205,.405,t)+.095*smoothstep(.41,.76,t);
float lag = u-front;
float pulse = exp2(-pow(lag/(lag<0 ? .058 : .117),2));
float sweep = smoothstep(-.088,-.002,lag)*smoothstep(.045,.15,t);
float retire = smoothstep(.40,.73,t);
float wake = exp2(-max(0,lag)*lerp(1.9,4.2,retire));
float tail = 1-smoothstep(.92-.54*retire,1.0-.43*retire,u);
float fade = sweep*tail*(1-smoothstep(.76,1,t));
float v = (UV.y-.64)/lerp(1.05,.70,retire)+.64;
float2 grainUV = clamp(float2(.08+.84*u,.10+1.22*v),.012,.985);
float feather = Texture2DSample(FlowMask,FlowMaskSampler,grainUV).r;
float nib = Texture2DSample(Nib,NibSampler,float2(.14+.75*u,clamp(.18+1.15*v,.015,.98))).a;
float y = v+.024*(feather-.5)+.012*(Ink.r-.5);
float2 brushUV = float2(u,clamp(y,.004,.996)*.25);
float3 brush = Texture2DSample(Brush,BrushSampler,brushUV).rgb;
float outside = Texture2DSample(Brush,BrushSampler,brushUV+float2(0,.008)).r;
float lip = saturate((brush.r-outside)*2.2);
float body = brush.r;
float groove = brush.b;
float bevel = brush.g;
// 蓝紫背面覆盖场地底色，凹口、刃脊和内纹分别退去。
float edgeAge = 1-.44*retire;
float faceAge = (1-.78*retire)*(.52+.48*wake);
float pigment = .38+.40*nib+.22*feather;
float3 color = body*faceAge*lerp(float3(.006,.018,.10),float3(.018,.17,1.09),pigment);
color *= 1-.98*groove;
color += bevel*edgeAge*(.36+.64*wake)*lerp(float3(.028,.31,1.65),float3(.25,.89,2.72),pigment);
float softV = (v-.655-.033*sin(6.28*u))/lerp(.16,.24,pulse);
float halo = exp2(-softV*softV)*(.11*wake+.64*pulse);
float hotSpine = lip+.16*bevel;
color += pulse*(hotSpine*float3(9.8,10.9,11.7)+body*float3(.21,.37,.68))*(1-.72*groove);
color += lip*(.17+.83*wake)*float3(.75,1.62,3.35);
color += halo*float3(.026,.098,2.10)+pulse*halo*float3(.42,.56,.83);
// 峰值处的乳白散光向弧外铺开；用刀腹及暗槽的遮罩给笔纹让出空间。
float peakTime = smoothstep(.11,.23,t)*(1-smoothstep(.375,.535,t));
float nearHead = exp2(-2.0*pow((lag-.026)/(lag<.026 ? .073 : .158),2));
float offset = v-(.655+.033*sin(6.28*u));
float scatter = exp2(-1.55*pow((offset-.032)/(offset>0 ? .285 : .23),2));
float clearFace = 1-saturate(.82*body+.85*groove+.24*bevel);
float pearlMist = peakTime*nearHead*scatter*(.055+.945*clearFace);
color += pearlMist*float3(.20,.29,.64);
float extent = smoothstep(.003,.043,u)*(1-smoothstep(.956,.998,u));
float fringe = smoothstep(.005,.095,UV.y)*(1-smoothstep(.865,.995,UV.y));
Coverage = fade*extent*fringe*saturate(smoothstep(.06,.75,body)*lerp(.79,.97,faceAge)+bevel*.83+halo*.40+pearlMist*.17);
return fade*extent*fringe*color;
"""

# 地面反光是一抹宽而断续的蓝色，中心的白光沿切口横扫，两端先后熄灭。
WASH_SHADE = """
// UE 投影贴花的 UV 顺序为局部 Z、Y，切口长度在局部 Y 上。
float u=Clock.g>.5 ? 1-UV.y : UV.y;
float y=2*UV.x-1;
float t=saturate(Clock.r);
float front=lerp(.315,.784,smoothstep(.03,.78,t));
float behind=front-u;
float end=smoothstep(0,.07,u)*(1-smoothstep(.91,1,u));
float textureFlow=saturate(Ink.r);
float bank=y-.095*sin(6.28*u+.65)-.08*(textureFlow-.5);
// 白芯只占亮头中央；后方的长蓝光分成中脊和向外散开的暗蓝侧纹。
float lag=max(0,behind);
float head=exp2(-pow(behind/(behind<0 ? .042 : .123),2));
float wake=smoothstep(-.022,.045,behind)*exp2(-2.5*lag);
float forkGap=.11+.76*lag+.035*sin(13*u+2*textureFlow);
float mainLine=exp2(-pow(bank/(.17+.12*head+.066*lag),2));
float sideLine=exp2(-pow((bank+forkGap)/(.14+.16*lag),2));
float haze=exp2(-pow(bank/(.48+.28*lag),2));
float brush=.48+.52*textureFlow;
float fade=Clock.b*end*(1-smoothstep(.74,1,t))*smoothstep(.01,.08,t);
float split=.66+.34*sin(14*u+2.4*textureFlow+3*bank);
// 原分叉笔触沿地面长轴摊开，远端的两条细纹错开收尖。
float forkBrush=Texture2DSample(FlowMask,FlowMaskSampler,float2(clamp(.20+1.21*lag,.04,.96),clamp(.49+1.48*bank,.02,.98))).r;
float bristle=Texture2DSample(FlowMask,FlowMaskSampler,float2(clamp(.61+.94*lag,.10,.91),clamp(.48+1.64*bank+.12*textureFlow,.02,.98))).r;
float pearl=head*(.72*mainLine+.25*haze)*(.24+.88*sqrt(saturate(bristle)));
float glaze=Texture2DSample(FlowMask,FlowMaskSampler,float2(clamp(.35+.92*lag,.05,.97),clamp(.49+1.39*(bank+forkGap),.02,.98))).r;
float thread=wake*(mainLine*(.27+1.10*forkBrush)+sideLine*split*(.18+.93*glaze))*brush;
float veil=(.49*head+.79*wake)*haze*(.45+.69*sqrt(saturate(forkBrush)));
// 亮头掠过之后，低位散射向切口侧后方张开，地面中央仍透得出原笔触。
float fanAxis=bank+.12+.33*lag;
float fanRadius=lerp(.48,.84,smoothstep(.015,.38,lag));
float crossFalloff=exp2(-pow(fanAxis/fanRadius,2))*(1-smoothstep(.79,.995,abs(y)));
float spill=exp2(-pow(behind/(behind<0 ? .088 : .29),2));
float2 plumeUV=clamp(float2(.27+.96*lag,.53+bank*.84+lag*.25),.015,.985);
float plume=Texture2DSample(FlowMask,FlowMaskSampler,plumeUV).r;
float scatter=crossFalloff*(.65*spill+.68*wake)*(.38+.42*sqrt(saturate(plume))+.20*forkBrush);
float edgeFade=1-smoothstep(.88,.998,abs(y));
Coverage=fade*edgeFade*saturate(.73*pearl+.65*thread+.50*veil+.71*scatter);
Tint=float3(.011,.026,.102);
return fade*edgeFade*(pearl*float3(1.40,2.15,4.6)+thread*float3(.075,.34,3.05)
    +veil*float3(.024,.12,1.47)+scatter*float3(.069,.32,1.79));

"""


def cut_brush(directory):
    """四行线性遮罩对应首刀和三次切口，RGB 分别控制刀腹、刃脊和暗槽。"""
    name = 'T_Pyrios_CutBrushes'
    path = directory+'/'+name
    if EDITOR.does_asset_exist(path):
        texture = ue.load_asset(path)
    else:
        project = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
        task = ue.AssetImportTask()
        task.set_editor_properties(dict(filename=str(project/'AAADocs/Assets/Pyrios/FX'/(name+'.png')),
                                        destination_path=directory,destination_name=name,automated=True,save=False))
        ue.AssetToolsHelpers.get_asset_tools().import_asset_tasks([task])
        texture = ue.load_asset(path)
        if not isinstance(texture,ue.Texture2D):
            raise RuntimeError('四刀笔纹导入失败 '+path)
        texture.set_editor_properties(dict(srgb=False,compression_settings=ue.TextureCompressionSettings.TC_MASKS,
                                            address_x=ue.TextureAddress.TA_CLAMP,address_y=ue.TextureAddress.TA_CLAMP))
        if not EDITOR.save_loaded_asset(texture,False):
            raise RuntimeError('四刀笔纹保存失败 '+path)
    if not isinstance(texture,ue.Texture2D) or texture.srgb or texture.compression_settings!=ue.TextureCompressionSettings.TC_MASKS:
        raise RuntimeError('四刀笔纹需要线性遮罩 '+path)
    # 一刀不到四分之一秒，首帧须能读到窄脊和缺口。
    if not texture.never_stream:
        texture.set_editor_property('never_stream',True)
        if not EDITOR.save_loaded_asset(texture,False):
            raise RuntimeError('首刀纹理驻留设置保存失败 '+path)
    return texture


def surface(directory, ground):
    edit = ue.MaterialEditingLibrary
    name = 'M_Pyrios_GroundBlueSweep' if ground else 'M_Pyrios_OpeningCrescent'
    version = WASH_VERSION if ground else ARC_SURFACE_VERSION
    path = directory+'/'+name
    mat = ue.load_asset(path) if EDITOR.does_asset_exist(path) else None
    if mat and EDITOR.get_metadata_tag(mat,TAG)==version:
        return mat
    if mat:
        if not EDITOR.get_metadata_tag(mat,TAG):
            raise RuntimeError('存在同名手工材质 '+path)
        edit.delete_all_material_expressions(mat)
    else:
        mat=ue.AssetToolsHelpers.get_asset_tools().create_asset(name,directory,ue.Material,ue.MaterialFactoryNew())
    if ground:
        mat.set_editor_properties(dict(material_domain=ue.MaterialDomain.MD_DEFERRED_DECAL,blend_mode=ue.BlendMode.BLEND_TRANSLUCENT))
    else:
        mat.set_editor_properties(dict(shading_model=ue.MaterialShadingModel.MSM_UNLIT,blend_mode=ue.BlendMode.BLEND_ALPHA_COMPOSITE,
                                       used_with_niagara_mesh_particles=True,two_sided=True))
    uv=edit.create_material_expression(mat,ue.MaterialExpressionTextureCoordinate,-650,-160)
    clock=edit.create_material_expression(mat,ue.MaterialExpressionDecalColor if ground else ue.MaterialExpressionParticleColor,-650,80)
    tex=ue.load_asset('/Game/Characters/Shared/FX/ZZZ/Textures/Eff_MeleeTrail_125_YZ_01_318015ec2a80')
    if not isinstance(tex,ue.Texture2D):
        raise RuntimeError('缺少原刀面流纹')
    ink=edit.create_material_expression(mat,ue.MaterialExpressionTextureSample,-540,260)
    ink.set_editor_properties(dict(texture=tex,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_COLOR))
    inputs=[(uv,'','UV'),(clock,'' if ground else 'RGBA','Clock'),(ink,'RGB','Ink')]
    textures={'FlowMask':'Eff_MeleeTrail_237_148ae2cbe983'}
    if not ground:
        textures['Nib']='Eff_MeleeTrail_116_YZ_03_8a06449ff0e4'
    for i,(slot,asset) in enumerate(textures.items()):
        texture=ue.load_asset('/Game/Characters/Shared/FX/ZZZ/Textures/'+asset)
        if not isinstance(texture,ue.Texture2D):
            raise RuntimeError('缺少刀纹 '+asset)
        obj=edit.create_material_expression(mat,ue.MaterialExpressionTextureObjectParameter,-560,450+i*200)
        obj.set_editor_properties(dict(parameter_name=slot,texture=texture,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_COLOR))
        inputs.append((obj,'',slot))
    if not ground:
        brush=edit.create_material_expression(mat,ue.MaterialExpressionTextureObjectParameter,-560,850)
        brush.set_editor_properties(dict(parameter_name='Brush',texture=cut_brush(directory),sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_MASKS))
        inputs.append((brush,'','Brush'))
    code=edit.create_material_expression(mat,ue.MaterialExpressionCustom,-220,0)
    configure_native_custom(ue,code,[slot for _,_,slot in inputs],WASH_SHADE if ground else ARC_SHADE,'CMOT_Float3',
        '切口落地的分叉蓝纹' if ground else '沿月牙展开的笔锋与退弦',native_sync=lambda _,fn:fn(),additional_outputs=[('Coverage','CMOT_Float1')]+([('Tint','CMOT_Float3')] if ground else []))
    for node,pin,slot in inputs:
        if not edit.connect_material_expressions(node,pin,code,slot):
            raise RuntimeError('刀光输入缺失 '+slot)
    for pin,slot in [('',ue.MaterialProperty.MP_EMISSIVE_COLOR),('Coverage',ue.MaterialProperty.MP_OPACITY)]:
        if not edit.connect_material_property(code,pin,slot):
            raise RuntimeError('刀光输出缺失 '+pin)
    if ground and not edit.connect_material_property(code,'Tint',ue.MaterialProperty.MP_BASE_COLOR):
        raise RuntimeError('地面蓝光底色接线失败')
    if edit.recompile_material(mat):
        raise RuntimeError('刀光材质编译失败 '+name)
    EDITOR.set_metadata_tag(mat,TAG,version)
    if not EDITOR.save_loaded_asset(mat,False):
        raise RuntimeError('刀光材质保存失败 '+name)
    return mat


def crescent_mesh(directory):
    path=directory+'/SM_Pyrios_OpeningCrescent'
    if EDITOR.does_asset_exist(path):
        return ue.load_asset(path)
    verts,uvs,tris=[],[],[]
    radial=(0,.22,.46,.57,.63,.70,.84,1)
    # 非闭合弧。内侧留出透光刀腹，亮脊在外三分之一，外缘另留柔光的几何宽度。
    for i in range(89):
        u=i/88
        a=(-155+280*u)*pi/180
        belly=sin(pi*u)**.53
        for j,v in enumerate(radial):
            r=242+(v-.63)*(36+97*belly)
            verts.append(ue.Vector(r*cos(a),.95*r*sin(a),16*sin(a)+14*cos(a)+(1-abs(v-.63)*2)*8*belly))
            uvs.append(ue.Vector2D(u,v))
            if i and j:
                k=len(verts)-1
                h=len(radial)
                tris.extend([ue.IntVector(k-h-1,k-h,k),ue.IntVector(k-h-1,k,k-1)])
    dm=ue.DynamicMesh()
    ue.GeometryScript_MeshEdits.append_buffers_to_mesh(dm,ue.GeometryScriptSimpleMeshBuffers(vertices=verts,uv0=uvs,triangles=tris))
    opts=ue.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True,enable_nanite=False,enable_collision=False)
    asset,result=ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dm,path,opts)
    if result!=ue.GeometryScriptOutcomePins.SUCCESS or not EDITOR.save_loaded_asset(asset,False):
        raise RuntimeError('月牙弧面制作失败 '+path)
    return asset


def apply_stack(system,tool,work):
    result=tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch',system={'refPath':system.get_path_name()},workItems=work)
    if not result.get('bApplied'):
        raise RuntimeError(result.get('error','刀光栈制作失败'))


def configure(system,emitter,index,data):
    result=LIB.authoring_set_renderer_data(system,emitter,index,json.dumps(data))
    if not result.succeeded:
        raise RuntimeError(result.error)


def opening(system,directory,tool,assign,module):
    mat=surface(directory,False)
    mesh=crescent_mesh(directory)
    existing={r.emitter_name for r in LIB.authoring_get_system_summary(system).emitters}
    if ARC in existing:
        if EDITOR.get_metadata_tag(system,TAG)==ARC_VERSION:
            return False
        if not EDITOR.get_metadata_tag(system,TAG):
            raise RuntimeError('未识别的首刀月牙发射器')
        tool('NiagaraToolsets.NiagaraToolset_System.RemoveEmitter',emitterRef={'system':{'refPath':system.get_path_name()},'emitterName':ARC})
    made=LIB.authoring_add_emitter(system,ue.load_asset(EMPTY_EMITTER),ARC)
    if not made.succeeded:
        raise RuntimeError(made.error)
    data=LIB.authoring_set_emitter_data(system,ARC,json.dumps({'bLocalSpace':False,'CalculateBoundsMode':'Dynamic'}))
    if not data.succeeded:
        raise RuntimeError(data.error)
    eu,ps,pu='EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript'
    num=NiagaraBuilder.num
    # 只在出生时读取招式坐标系。之后角色移动、手腕回转均不会拖动弧面。
    work=[module(eu,'/Niagara/Modules/Emitter/EmitterState',emitter=ARC,**{
              'Life Cycle Mode':NiagaraBuilder.enum('/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode','NewEnumerator1','Self'),
              'Loop Behavior':NiagaraBuilder.enum('/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions','NewEnumerator1','Once'),
              'Loop Duration':num('Float',.32)}),
          module(eu,'/Niagara/Modules/Emitter/SpawnBurst_Instantaneous',emitter=ARC,**{'Spawn Time':num('Float',.058),'Spawn Count':num('Int32',1)}),
          assign(ps,emitter=ARC,Lifetime=('Float','.202'),ArcOrigin=('Position','Engine.Owner.Position + Engine.Owner.SystemYAxis*119 + float3(0,0,28)'),
                 Position=('Position','Engine.Owner.Position + Engine.Owner.SystemYAxis*119 + float3(0,0,28)'),
                 ArcYaw=('Float','atan2(Engine.Owner.SystemXAxis.y,Engine.Owner.SystemXAxis.x)'),
                 Scale=('Vector','float3(.86,-.86,1)'),MeshOrientation=('Quat','float4(0,0,0,1)'),Color=('LinearColor','float4(0,0,0,1)')),
          module(pu,'/Niagara/Modules/Update/Lifetime/ParticleState',emitter=ARC),
          assign(pu,emitter=ARC,ArcRetireT=('Float','saturate((Particles.NormalizedAge-.32)/.40)')),
          assign(pu,emitter=ARC,ArcRetire=('Float','Particles.ArcRetireT*Particles.ArcRetireT*(3.0-2.0*Particles.ArcRetireT)')),
          assign(pu,emitter=ARC,Position=('Position','Particles.ArcOrigin + float3(-sin(Particles.ArcYaw)*68,cos(Particles.ArcYaw)*68,58)*Particles.ArcRetire'),
                 ArcHalfAngle=('Float','.5*(Particles.ArcYaw + (.08 - .18*Particles.ArcRetire))'),
                 Scale=('Vector','float3(1.0-.83*Particles.ArcRetire,-1,1.0-.63*Particles.ArcRetire)*lerp(.90,1.19,saturate(Particles.NormalizedAge*2.9))'),
                 Color=('LinearColor','float4(Particles.NormalizedAge,0,0,1)')),
          assign(pu,emitter=ARC,MeshOrientation=('Quat','float4(-sin(Particles.ArcHalfAngle)*.130526,cos(Particles.ArcHalfAngle)*.130526,sin(Particles.ArcHalfAngle)*.991445,cos(Particles.ArcHalfAngle)*.991445)'))]
    apply_stack(system,tool,work)
    renderer=LIB.authoring_add_renderer(system,ARC,ue.NiagaraMeshRendererProperties)
    if not renderer.succeeded:
        raise RuntimeError(renderer.error)
    configure(system,ARC,renderer.renderer_index,{'bOverrideMaterials':True})
    configure(system,ARC,renderer.renderer_index,dict(Meshes=[dict(Mesh=mesh.get_path_name())],OverrideMaterials=[dict(ExplicitMat=mat.get_path_name())]))
    EDITOR.set_metadata_tag(system,TAG,ARC_VERSION)
    return True


FLOOR_CAST = """
bool hit; bool inside; float3 contactPos; float3 normal; float friction; float bounce; int surface;
float3 start=Particles.Position+float3(0,0,24);
{{DI}}.PerformCollisionQuerySyncCPU(start,start-float3(0,0,410),3,!Particles.CutLockNow,false,hit,inside,contactPos,normal,friction,bounce,surface);
{{OUT:Particles.WashProbeHit}}=hit && !inside && normal.z>.55;
{{OUT:Particles.WashProbePos}}=contactPos+normal*.8;
{{OUT:Particles.WashProbeNormal}}=normal;
"""


def ground_sweep(system,directory,emitter,tool,target,assign):
    mat=surface(directory,True)
    if EDITOR.get_metadata_tag(system,'Pyrios.GroundBlueSweep')=='fanned-ground-3':
        return False
    di=ue.new_object(ue.load_class(None,'/Script/Niagara.NiagaraDataInterfaceCollisionQuery'))
    ps,pu='ParticleSpawnScript','ParticleUpdateScript'
    # 切口锁定时投一次地面。三个返光方向由刀向向外散开，第一刀的蓝色扇光最宽。
    work=[assign(ps,emitter=emitter,WashLocked=('Bool','false'),WashHasGround=('Bool','false'),WashNormal=('Vector','float3(0,0,1)'),
                 WashOrigin=('Position','Particles.Position'),WashRotation=('Quat','float4(0,0,0,1)'),
                 WashOrder=('Int','41'),WashSize=('Vector','float3(13,1,1)'),WashColor=('LinearColor','float4(0,0,0,0)')),
          dict(kind='ParticleRead',emitterName=emitter,scriptName=pu,interfaceTemplate={'refPath':di.get_path_name()},
               outputTargets=[target('WashProbeHit','Bool'),target('WashProbePos','Position'),target('WashProbeNormal','Vector')],hlslBodyTemplate=FLOOR_CAST),
          assign(pu,emitter=emitter,WashHasGround=('Bool','Particles.WashHasGround || Particles.WashProbeHit'),
                 WashOrigin=('Position','Particles.WashProbeHit ? Particles.WashProbePos : Particles.WashOrigin'),
                 WashNormal=('Vector','Particles.WashProbeHit ? Particles.WashProbeNormal : Particles.WashNormal')),
          assign(pu,emitter=emitter,WashLocked=('Bool','Particles.WashHasGround && Particles.CutFixed'),
                 WashDown=('Quat','normalize(float4(0,Particles.WashNormal.z,-Particles.WashNormal.y,max(.0001,1.0-Particles.WashNormal.x)))')),
          assign(pu,emitter=emitter,WashBasis=('Vector','float3(0,1,0)+2*cross(Particles.WashDown.xyz,cross(Particles.WashDown.xyz,float3(0,1,0))+Particles.WashDown.w*float3(0,1,0))')),
          assign(pu,emitter=emitter,WashTwist=('Float','.5*atan2(dot(cross(Particles.WashBasis,Particles.CutDirection),-Particles.WashNormal),dot(Particles.WashBasis,Particles.CutDirection)+.000001) + (Particles.UniqueID==0 ? -.48 : (Particles.UniqueID==1 ? .14 : -.10))')),
          assign(pu,emitter=emitter,WashSpin=('Vector','-Particles.WashNormal*sin(Particles.WashTwist)')),
          assign(pu,emitter=emitter,WashRotation=('Quat','float4(cos(Particles.WashTwist)*Particles.WashDown.xyz+Particles.WashDown.w*Particles.WashSpin+cross(Particles.WashSpin,Particles.WashDown.xyz),cos(Particles.WashTwist)*Particles.WashDown.w-dot(Particles.WashSpin,Particles.WashDown.xyz))')),
          assign(pu,emitter=emitter,WashSize=('Vector','float3(13,Particles.CutLength*2.1,154)'),
                 WashColor=('LinearColor','float4(Particles.NormalizedAge,Particles.CutReverse ? 1.0 : 0.0,Particles.Color.a,1)'))]
    apply_stack(system,tool,work)
    renderer=LIB.authoring_add_renderer(system,emitter,ue.NiagaraDecalRendererProperties)
    if not renderer.succeeded:
        raise RuntimeError(renderer.error)
    bind=NiagaraBuilder.attribute_binding
    configure(system,emitter,renderer.renderer_index,dict(Material=mat.get_path_name(),PositionBinding=bind('Particles.WashOrigin'),
              DecalOrientationBinding=bind('Particles.WashRotation'),DecalSizeBinding=bind('Particles.WashSize'),
              DecalColorBinding=bind('Particles.WashColor'),DecalVisibleBinding=bind('Particles.WashLocked'),
              DecalSortOrderBinding=bind('Particles.WashOrder'),DecalScreenSizeFade=0.0))
    EDITOR.set_metadata_tag(system,'Pyrios.GroundBlueSweep','fanned-ground-3')
    return True
