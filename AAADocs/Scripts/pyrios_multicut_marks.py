"""佩洛伊斯三段起手的空间斩痕。每刀留下一个收锋的切面。"""
import json
from math import sin, pi

import unreal as ue

from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import EMPTY_EMITTER, NiagaraBuilder


SCARS = 'Pyrios_AftercutMarks'
VERSION = 'three-incisions-2'
SURFACE_VERSION = 'source-edge-1'
# Normal03 的 03/09_MeleeTrail 原 andi_main 刀面，以及三次 MeleeTrail 共用的 light_edge 与高光遮罩。
TEXTURES = {'Face': 'Eff_MeleeTrail_239_4f346e732ad4', 'Edge': 'Eff_MeleeTrail_089_LYX_01_2d474876c2a0',
            'Highlight': 'Eff_MeleeTrail_116_YZ_06_f2c948b7ce36'}
SHADE = """
float u = saturate(UV.x);
float v = abs(2.0*UV.y-1.0);
float edgeLuma = dot(Edge.rgb,float3(.23,.62,.15));
float etched = saturate(Face.r*.70 + Highlight.r*.30);
// 中线先亮，外侧仅留薄辉。原刀面纹理切开亮带，高光遮罩保留刃腹明暗变化。
float ridge = 1.0-smoothstep(.055,.30,v);
float shoulder = 1.0-smoothstep(.25,.82,v);
float lip = smoothstep(.55,.68,v)*(1.0-smoothstep(.68,.88,v))*etched;
float3 flank = lerp(float3(.028,.046,.19),float3(.13,.23,.78),etched);
float3 foil = flank*(.60+.40*shoulder) + Edge.rgb*(.33+.45*etched);
float3 light = float3(1.67,2.12,3.0)*(.75+.25*Highlight.r);
float3 color = lerp(foil,light,ridge) + float3(.34,.50,1.1)*lip;
float reveal = 1.0-smoothstep(Progress-.085,Progress,lerp(u,1.0-u,Reverse));
float feather = 1.0-smoothstep(.64,.99,v);
float flankAlpha = (.66+.26*etched+.08*edgeLuma)*feather;
float coverage = reveal*Life*max(flankAlpha,ridge);
Coverage=saturate(coverage);
return color*Coverage;
"""


def scar_material(directory):
    editor, edit = ue.EditorAssetLibrary, ue.MaterialEditingLibrary
    name = 'M_Pyrios_Aftercut'
    path = directory+'/'+name
    if editor.does_asset_exist(path):
        mat = ue.load_asset(path)
        if editor.get_metadata_tag(mat,'Pyrios.Aftercut') == SURFACE_VERSION:
            return mat
        if editor.get_metadata_tag(mat,'Pyrios.Aftercut') not in ('three-incisions-1', VERSION):
            raise RuntimeError('已有未识别的斩痕材质 '+path)
        edit.delete_all_material_expressions(mat)
    else:
        mat = ue.AssetToolsHelpers.get_asset_tools().create_asset(name,directory,ue.Material,ue.MaterialFactoryNew())
    textures = {k:ue.load_asset('/Game/Characters/Shared/FX/ZZZ/Textures/'+v) for k,v in TEXTURES.items()}
    if not all(isinstance(t,ue.Texture2D) for t in textures.values()):
        raise RuntimeError('缺少 Normal03 原刀面、亮刃或高光遮罩')
    mat.set_editor_properties(dict(blend_mode=ue.BlendMode.BLEND_ALPHA_COMPOSITE,
        shading_model=ue.MaterialShadingModel.MSM_UNLIT,two_sided=True,used_with_niagara_mesh_particles=True))
    uv = edit.create_material_expression(mat,ue.MaterialExpressionTextureCoordinate,-900,0)
    color = edit.create_material_expression(mat,ue.MaterialExpressionParticleColor,-600,380)
    node = edit.create_material_expression(mat,ue.MaterialExpressionCustom,-250,0)
    configure_native_custom(ue,node,['UV',*textures,'Life','Progress','Reverse'],SHADE,'CMOT_Float3','源纹理切面与刃口',
                            native_sync=lambda _,call:call(),additional_outputs=[('Coverage','CMOT_Float1')])
    def connect(src,pin,dst,field):
        if not edit.connect_material_expressions(src,pin,dst,field):
            raise RuntimeError('斩痕材质连接失败 '+field)
    connect(uv,'',node,'UV')
    # 源图的亮刃位于上沿。刀脊在 UV 的中线，两侧斜面使用同一段原图。
    coords = edit.create_material_expression(mat,ue.MaterialExpressionCustom,-720,-200)
    configure_native_custom(ue,coords,['UV'],'return float2(lerp(.04,.96,UV.x),.008+.46*abs(2.0*UV.y-1.0));',
                            'CMOT_Float2','沿刃脊展开原纹理',native_sync=lambda _,call:call())
    connect(uv,'',coords,'UV')
    for i,(key,t) in enumerate(textures.items()):
        sample = edit.create_material_expression(mat,ue.MaterialExpressionTextureSample,-470,-280+i*140)
        sample.set_editor_properties(dict(texture=t,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_COLOR))
        connect(coords,'',sample,'Coordinates')
        connect(sample,'RGBA',node,key)
    connect(color,'A',node,'Life')
    connect(color,'R',node,'Progress')
    connect(color,'G',node,'Reverse')
    if (not edit.connect_material_property(node,'',ue.MaterialProperty.MP_EMISSIVE_COLOR)
            or not edit.connect_material_property(node,'Coverage',ue.MaterialProperty.MP_OPACITY) or edit.recompile_material(mat)):
        raise RuntimeError('斩痕原纹理材质编译失败')
    editor.set_metadata_tag(mat,'Pyrios.Aftercut',SURFACE_VERSION)
    if not editor.save_loaded_asset(mat,False):
        raise RuntimeError('斩痕材质保存失败')
    return mat


def scar_mesh(directory):
    path = directory+'/SM_Pyrios_Aftercut'
    if ue.EditorAssetLibrary.does_asset_exist(path):
        return ue.load_asset(path)
    # 稍偏向收刀端的刀腹，四个硬切面共用两端尖点。UV 沿行刀方向，不随相机旋转。
    verts, uvs, tris = [], [], []
    rings = [(0,0),(.085,.13),(.28,.56),(.50,.97),(.60,1),(.76,.66),(.92,.18),(1,0)]
    section = [(-.5,0,0),(.035,.5,.5),(.5,0,1),(.035,-.5,.5)]
    for side,a in enumerate(section):
        b = section[(side+1)%len(section)]
        for j in range(len(rings)-1):
            face=[]
            for i,(y,z,v) in [(j,a),(j+1,a),(j+1,b),(j,b)]:
                u,width = rings[i]
                point = ue.Vector(100*(u-.5),100*y*width,100*(z*width+.06*sin(pi*u)))
                if not any(point==prev[0] for prev in face):
                    face.append((point,ue.Vector2D(u,v if width else .5)))
            base=len(verts)
            for point,uv in face:
                verts.append(point)
                uvs.append(uv)
            for i in range(1,len(face)-1):
                tris.append(ue.IntVector(base,base+i,base+i+1))
    mesh = ue.DynamicMesh()
    buffers = ue.GeometryScriptSimpleMeshBuffers(vertices=verts,uv0=uvs,triangles=tris)
    ue.GeometryScript_MeshEdits.append_buffers_to_mesh(mesh,buffers)
    if mesh.get_triangle_count()!=len(tris):
        raise RuntimeError('斩痕截面生成失败')
    opts=ue.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True,
                                                         enable_nanite=False,enable_collision=False)
    asset,result=ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(mesh,path,opts)
    if result!=ue.GeometryScriptOutcomePins.SUCCESS or not asset or not ue.EditorAssetLibrary.save_loaded_asset(asset,False):
        raise RuntimeError('斩痕网格保存失败')
    return asset


def add_opening_marks(system,directory,mat,tool,target,assign,module,weapon_frame):
    lib=ue.GGYGONiagaraCompileLibrary
    mesh=scar_mesh(directory)
    made=lib.authoring_add_emitter(system,ue.load_asset(EMPTY_EMITTER),SCARS)
    if not made.succeeded:
        raise RuntimeError(made.error)
    data=lib.authoring_set_emitter_data(system,SCARS,json.dumps({'bLocalSpace':False,'CalculateBoundsMode':'Dynamic',
                                                                'AttributesToPreserve':['Particles.UniqueID']}))
    if not data.succeeded:
        raise RuntimeError(data.error)
    eu,ps,pu='EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript'
    num=NiagaraBuilder.num
    work=[module(eu,'/Niagara/Modules/Emitter/EmitterState',emitter=SCARS,**{
        'Life Cycle Mode':NiagaraBuilder.enum('/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode','NewEnumerator1','Self'),
        'Loop Behavior':NiagaraBuilder.enum('/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions','NewEnumerator1','Once'),
        'Loop Duration':num('Float',.60)})]
    for t in (.031,.095,.194):
        work.append(module(eu,'/Niagara/Modules/Emitter/SpawnBurst_Instantaneous',emitter=SCARS,
                           **{'Spawn Time':num('Float',t),'Spawn Count':num('Int32',1)}))
    di,sample=weapon_frame()
    sample += """
{{OUT:Particles.HasContact}} = Count == 2 && Base >= 0 && Tip >= 0 && Width > 1;
{{OUT:Particles.Contact}} = A + Axis*.55;
// 用同一武器骨的组件与世界旋转求角色局部对角线，不受武器甩动或相机转动影响。
float3 D = normalize(float3(1,1,0));
float3 BoneD = D + 2*cross(-LocalBR.xyz,cross(-LocalBR.xyz,D)+LocalBR.w*D);
float3 PlaneAxis = BoneD + 2*cross(BR.xyz,cross(BR.xyz,BoneD)+BR.w*BoneD);
{{OUT:Particles.SlashPlane}} = normalize(float3(PlaneAxis.xy,0));
"""
    def sample_weapon(stage):
        return dict(kind='ParticleRead', emitterName=SCARS, scriptName=stage,
                    interfaceTemplate={'refPath':di.get_path_name()}, hlslBodyTemplate=sample,
                    outputTargets=[target('HasContact','Bool'), target('Contact','Position'), target('SlashPlane','Vector')])

    work.extend([sample_weapon(ps),assign(ps,emitter=SCARS,Alive=('Bool','Particles.Alive && Particles.HasContact'),
        Lifetime=('Float','Particles.UniqueID == 0 ? .255 : (Particles.UniqueID == 1 ? .224 : .190)'),
        CutStart=('Position','Particles.Contact'),CutFixed=('Bool','false'),CutReverse=('Bool','false'),
        Position=('Position','Particles.Contact'),Scale=('Vector','float3(0,0,0)'),
        MeshOrientation=('Quat','float4(0,0,0,1)'),Color=('LinearColor','float4(0,0,0,0)')),
        module(pu,'/Niagara/Modules/Update/Lifetime/ParticleState',emitter=SCARS),sample_weapon(pu)])
    # 用两次刀锋采样的中点落痕，在角色局部斩击面展开三个方向，显影从入刃指向出刃。
    # 锁定以后只显影和退光。角色转身、刀骨回摆都不再更新这道切口。
    work.extend([assign(pu,emitter=SCARS,
        CutLockNow=('Bool','!Particles.CutFixed && Particles.HasContact && Particles.Age >= .021 && length((Particles.Contact-Particles.CutStart).xy)>4')),
        assign(pu,emitter=SCARS,
        CutDirection=('Vector','normalize(float3(Particles.SlashPlane.xy,Particles.UniqueID==0 ? .06 : (Particles.UniqueID==1 ? -.73 : 1.95)))'),
        CutLength=('Float','Particles.UniqueID==0 ? 378.0 : (Particles.UniqueID==1 ? 350.0 : 290.0)')),
        assign(pu,emitter=SCARS,
        Position=('Position','Particles.CutLockNow ? Particles.CutStart + (Particles.Contact-Particles.CutStart)*.52 : Particles.Position'),
        Scale=('Vector','Particles.CutLockNow ? float3(Particles.CutLength,Particles.UniqueID==1 ? 32.0 : 27.0,18.0)*.01 : Particles.Scale'),
        MeshOrientation=('Quat','Particles.CutLockNow ? (Particles.CutDirection.x < -.9999 ? float4(0,0,1,0) : normalize(float4(0,-Particles.CutDirection.z,Particles.CutDirection.y,1+Particles.CutDirection.x))) : Particles.MeshOrientation'),
        CutReverse=('Bool','Particles.CutLockNow ? dot(Particles.Contact-Particles.CutStart,Particles.CutDirection)<0.0 : Particles.CutReverse'),
        CutFixed=('Bool','Particles.CutFixed || Particles.CutLockNow')),
        assign(pu,emitter=SCARS,Color=('LinearColor','float4(saturate((Particles.Age-.016)/.031)*1.10,Particles.CutReverse ? 1.0 : 0.0,1,Particles.CutFixed ? saturate((1.0-Particles.NormalizedAge)/.49) : 0.0)'))])
    res=tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch',system={'refPath':system.get_path_name()},workItems=work)
    if not res.get('bApplied'):
        raise RuntimeError(res.get('error','空间斩痕制作失败'))
    renderer=lib.authoring_add_renderer(system,SCARS,ue.load_class(None,'/Script/Niagara.NiagaraMeshRendererProperties'))
    if not renderer.succeeded:
        raise RuntimeError(renderer.error)
    bind=NiagaraBuilder.attribute_binding
    for props in ({'bOverrideMaterials':True},dict(Meshes=[dict(Mesh=mesh.get_path_name())],OverrideMaterials=[dict(ExplicitMat=mat.get_path_name())],
                PositionBinding=bind('Particles.Position'),ScaleBinding=bind('Particles.Scale'),
                MeshOrientationBinding=bind('Particles.MeshOrientation'),ColorBinding=bind('Particles.Color'))):
        result=lib.authoring_set_renderer_data(system,SCARS,renderer.renderer_index,json.dumps(props))
        if not result.succeeded:
            raise RuntimeError(result.error)
