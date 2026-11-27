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
ARC_SURFACE_VERSION = 'pearl-and-afterglow-5'
WASH_VERSION = 'surface-sweep-4'
TAG = 'Pyrios.AuthoredSlash'

# 时间沿整张弧面推进。白晕在挥刀前半拍变宽，后半拍只剩远侧的一段亮弦。
ARC_SHADE = """
float u=saturate(UV.x);
float v=UV.y;
float t=saturate(Clock.r);
float head=smoothstep(0.0,.29,t);
// 远侧先熄，留下进刀一侧的一段切线，从角色身前划过。
head=min(head,1-.48*smoothstep(.34,.84,t));
float tail=smoothstep(.31,.90,t)*.22;
float along=smoothstep(tail-.09,tail+.035,u)*(1-smoothstep(head-.04,head+.035,u));
float peak=smoothstep(.045,.24,t)*(1-smoothstep(.28,.50,t));
float local=exp2(-27*(u-.21)*(u-.21));
float bright=peak*(.035+.965*local);
float taper=pow(saturate(sin(3.14159*u)),.42);
float d=(v-.63)/max(.09,.3+.7*taper);
float tailWidth=lerp(1,.43,smoothstep(.38,.72,t));
d/=tailWidth;
float aa=max(fwidth(d),.002);
float core=1-smoothstep(.013+bright*.026,.027+bright*.035+aa,abs(d));
float hot=exp2(-d*d/(.003+.015*bright));
float pearl=exp2(-d*d/(.018+.055*bright));
float azure=exp2(-d*d/(.049+.065*bright));
float vein=saturate(Ink.r);
float life=along*smoothstep(0,.045,t)*(1-smoothstep(.74,1,t));
float soft=smoothstep(0,.16,v)*(1-smoothstep(.84,1,v));
float3 light=core*lerp(float3(.48,.95,3.6),float3(6.8,7.8,11.0),bright)+hot*lerp(float3(.22,.65,3.9),float3(9,10,13),bright);
light+=pearl*(.24+2.7*bright)*float3(.21,.54,2.8)+azure*(.35+.4*vein)*float3(.011,.047,1.48);
Coverage=life*soft*saturate(core+hot*.85+pearl*(.44+.46*bright)+azure*.62);
float residual=smoothstep(.36,.61,t);
return life*soft*(light*(1+2.6*residual)+pearl*residual*float3(.32,.35,2.7));
"""

# 地面反光是一抹宽而断续的蓝色，中心的白光沿切口横扫，两端先后熄灭。
WASH_SHADE = """
float u=Clock.g>.5 ? 1-UV.x : UV.x;
float y=2*UV.y-1;
float t=saturate(Clock.r);
float front=smoothstep(0,.62,t);
float passed=front-u;
float end=smoothstep(0,.11,u)*(1-smoothstep(.82,1,u));
float trail=smoothstep(-.17,.035,passed)*exp2(-3.5*max(0,passed));
float bank=y-(.085*sin(6.28*u+.65)+.09*(Ink.r-.5));
float body=exp2(-3.8*bank*bank);
float streak=exp2(-28*bank*bank)*(.45+.55*Ink.r);
float echo=exp2(-42*(bank+.51-.34*u)*(bank+.51-.34*u))*(.24+.76*Ink.r);
float flare=exp2(-26*passed*passed-7*bank*bank);
float fade=Clock.b*end*(1-smoothstep(.75,1,t))*smoothstep(0,.05,t);
Coverage=saturate(body*trail*.75+(streak+.35*echo)*trail*.32+flare*.62)*fade;
Tint=float3(.026,.048,.133);
return body*float3(.014,.052,.48)+(streak+.36*echo)*float3(.035,.16,1.34)+flare*float3(1.08,2.0,6.8)+body*trail*float3(.015,.026,.45);
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
    code=edit.create_material_expression(mat,ue.MaterialExpressionCustom,-220,0)
    configure_native_custom(ue,code,['UV','Clock','Ink'],WASH_SHADE if ground else ARC_SHADE,'CMOT_Float3',
        '横扫的地面余光' if ground else '月牙亮峰和退弦',native_sync=lambda _,fn:fn(),additional_outputs=[('Coverage','CMOT_Float1')]+([('Tint','CMOT_Float3')] if ground else []))
    for node,pin,slot in [(uv,'','UV'),(clock,'RGBA' if not ground else '','Clock'),(ink,'RGB','Ink')]:
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
    if EDITOR.get_metadata_tag(system,'Pyrios.GroundBlueSweep')=='fanned-ground-2':
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
          assign(pu,emitter=emitter,WashTwist=('Float','.5*atan2(dot(cross(Particles.WashBasis,Particles.CutDirection),-Particles.WashNormal),dot(Particles.WashBasis,Particles.CutDirection)+.000001) + (Particles.UniqueID==0 ? -.63 : (Particles.UniqueID==1 ? -.31 : .06))')),
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
    EDITOR.set_metadata_tag(system,'Pyrios.GroundBlueSweep','fanned-ground-2')
    return True
