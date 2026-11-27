"""首刀的定形月牙与三段切口的地面蓝光。两层均由原 Niagara 表现窗口驱动。"""
import json
from math import cos, pi, sin

import unreal as ue

from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import EMPTY_EMITTER, NiagaraBuilder

EDITOR = ue.EditorAssetLibrary
LIB = ue.GGYGONiagaraCompileLibrary
ARC = 'Pyrios_OpeningCrescent'
ARC_VERSION = 'horizontal-crescent-4'
ARC_SURFACE_VERSION = 'brushed-crescent-11'
WASH_VERSION = 'brushed-reflection-10'
TAG = 'Pyrios.AuthoredSlash'

# 时间沿整张弧面推进。白晕在挥刀前半拍变宽，后半拍只剩远侧的一段亮弦。
ARC_SHADE = """
float u=saturate(UV.x);
float v=UV.y;
float t=saturate(Clock.r);
// 亮锋从月牙的收口一侧扫向出刀一侧。刃面已亮过的部分分别留下细边和更长的蓝晕。
float advance=smoothstep(.205,.405,t);
float retire=smoothstep(.41,.76,t);
float peakAt=.95-.73*advance+.095*retire;
float behind=u-peakAt;
float reveal=smoothstep(-.085,-.015,behind)*smoothstep(.045,.16,t);
float edgeEnd=smoothstep(.0,.048,u)*(1-smoothstep(.955,1,u));
float tailLoss=smoothstep(.38,.66,t);
float tailEnd=1-smoothstep(.91-.55*tailLoss,1.0-.45*tailLoss,u);
float envelope=reveal*edgeEnd*tailEnd*(1-smoothstep(.77,1,t));
float lead=exp2(-pow(behind/(behind<0 ? .050 : .132),2));
float after=exp2(-max(0,behind)*lerp(2.15,4.5,retire));
float earlyBlue=1-smoothstep(.38,.545,t);
float wake=after*(.63+.37*earlyBlue);
float grain=saturate(Ink.r);
float taper=sqrt(saturate(sin(3.14159*u)));
float width=(.36+.64*taper)*lerp(1,.50,retire);
float d=(v-.63)/width;
float aa=max(fwidth(d),.0015);
float core=1-smoothstep(.013+.015*lead,.024+.021*lead+aa,abs(d));
float shoulder=exp2(-pow(d/(.029+.092*lead+.025*after),2));
float halo=exp2(-pow(d/(.13+.20*lead),2));
float inner=exp2(-pow((d+.14)/.16,2))*grain*lead;
float soft=smoothstep(0,.14,v)*(1-smoothstep(.85,1,v));
// 细边可以贯穿刚展开的月牙；只有掠过的这一小段具有宽白芯。
float white=lead*(1-.68*retire);
float filament=.16+.94*wake+.54*earlyBlue+.64*retire*after;
float3 light=core*(filament*float3(2.3,3.55,6.0)+white*float3(8.2,8.4,10.8));
light+=shoulder*(wake*float3(.26,.50,2.02)+white*float3(2.7,3.9,8.1));
light+=halo*(.56*wake+1.03*lead)*float3(.018,.074,2.55)+inner*float3(.23,.45,1.21);
// 116 的透明通道保存的是带缺口的笔锋。两次取样的透明边界错开，笔尖与白锋一同移动。
float depth=-d;
float face=smoothstep(.005,.05,depth)*(1-smoothstep(.47,.60,depth));
float run=saturate(max(0,behind));
float nibX=clamp(.91-.86*run-.045*retire,.06,.94);
float2 brushUV=float2(clamp(.48+.85*run,.09,.94),clamp(.16+2.19*depth+.13*run,.015,.975));
float feather=Texture2DSample(FlowMask,FlowMaskSampler,brushUV).r;
float curl=.09*(grain-.35)+.105*(feather-.38);
float2 nibUV=float2(nibX,clamp(.07+1.89*depth+curl,.012,.985));
float shape=Texture2DSample(Nib,NibSampler,nibUV).a;
float inset=Texture2DSample(Nib,NibSampler,float2(clamp(nibX-.085,.05,.92),clamp(nibUV.y+.11,.012,.985))).a;
float softNib=Texture2DSample(Nib,NibSampler,float2(nibX,clamp(nibUV.y+.045,.012,.985))).a;
float lip=saturate((.54*shape+.46*softNib-inset)*1.40);
float body=face*shape;
float splitY=depth-.115-.14*(1-run)+.30*curl;
float innerNib=Texture2DSample(Nib,NibSampler,float2(clamp(nibX-.12,.05,.90),clamp(.08+3.35*splitY,.012,.985))).a;
float strand=face*smoothstep(.005,.048,splitY)*innerNib;
float strokeEnd=1-smoothstep(.19,.63,run);
float strength=(.14+.86*max(lead,wake))*strokeEnd*(1-.66*retire);
float pigment=.16+.84*sqrt(saturate(feather));
light*=1-face*strength*(.77-.20*grain);
light+=strength*(body*float3(.019,.083,.58)+face*lip*pigment*float3(.15,.63,1.80)
    +strand*pigment*float3(.085,.39,1.32)+body*feather*float3(.035,.25,.76));
float opacity=core*(.63+.30*wake)+shoulder*(.22+.73*lead)+halo*(.67*wake+.42*lead);
Coverage=envelope*soft*saturate(opacity+strength*face*(.26+.56*shape*pigment));
return envelope*soft*light;
"""

# 地面反光是一抹宽而断续的蓝色，中心的白光沿切口横扫，两端先后熄灭。
WASH_SHADE = """
// UE 投影贴花的 UV 顺序为局部 Z、Y，切口长度在局部 Y 上。
float u=Clock.g>.5 ? 1-UV.y : UV.y;
float y=2*UV.x-1;
float t=saturate(Clock.r);
float front=lerp(.235,.83,smoothstep(.03,.78,t));
float behind=front-u;
float end=smoothstep(0,.07,u)*(1-smoothstep(.91,1,u));
float textureFlow=saturate(Ink.r);
float bank=y-.095*sin(6.28*u+.65)-.08*(textureFlow-.5);
// 白芯只占亮头中央；后方的长蓝光分成中脊和向外散开的暗蓝侧纹。
float lag=max(0,behind);
float head=exp2(-pow(behind/(behind<0 ? .042 : .123),2));
float wake=smoothstep(-.022,.045,behind)*exp2(-2.5*lag);
float forkGap=.11+.76*lag+.035*sin(13*u+2*textureFlow);
float mainLine=exp2(-pow(bank/(.14+.09*head+.045*lag),2));
float sideLine=exp2(-pow((bank+forkGap)/(.11+.11*lag),2));
float haze=exp2(-pow(bank/(.37+.26*lag),2));
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
Coverage=fade*saturate(.80*pearl+.71*thread+.51*veil);
Tint=float3(.011,.026,.102);
return fade*(pearl*float3(1.54,2.3,5.2)+thread*float3(.085,.37,3.45)+veil*float3(.017,.083,1.64));
"""


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
