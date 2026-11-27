"""佩洛伊斯三段起手的空间斩痕。每刀留下一个收锋的切面。"""
import json
from math import sin, pi

import unreal as ue

from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import EMPTY_EMITTER, NiagaraBuilder


SCARS = 'Pyrios_AftercutMarks'
VERSION = 'three-incisions-2'
SURFACE_VERSION = 'slow-reference-edge-2'
# Normal03 的 03/09_MeleeTrail 原 andi_main 刀面，以及三次 MeleeTrail 共用的 light_edge 与高光遮罩。
TEXTURES = {'Face': 'Eff_MeleeTrail_239_4f346e732ad4', 'Edge': 'Eff_MeleeTrail_089_LYX_01_2d474876c2a0',
            'Highlight': 'Eff_MeleeTrail_116_YZ_06_f2c948b7ce36'}
SHADE = """
float u = saturate(UV.x);
float v = 2.0*UV.y-1.0;
float travel = lerp(u,1-u,Reverse);
float reveal = 1-smoothstep(Progress-.09,Progress,travel);
// 239 的锯齿轮廓形成刀腹，089 的原色只出现在切口，116 单独控制掠过的高光。
float profile = saturate(Face.r);
float ridge = saturate(max(Edge.r,max(Edge.g,Edge.b)));
float gleam = saturate(Highlight.r);
float tipFade = smoothstep(0,.055,u)*(1-smoothstep(.966,1,u));
float ageFade = saturate(Life);
float body = smoothstep(.04,.82,profile)*(.10+.17*gleam);
float lip = sqrt(ridge)*(.55+.45*ageFade);
float flash = gleam*smoothstep(-.10,.17,v)*(1-smoothstep(.22,.87,v));
// 迎刃面明亮、背刃面压暗，两者在浅色场地上仍能读出斩痕的厚度。
float shadow = profile*(1-smoothstep(.54,.97,abs(v)))*lerp(.42,1,smoothstep(-.22,.44,-v));
float bevel = (1-smoothstep(.018,.185,abs(v+.11-.17*gleam)))*profile;
float3 N = normalize(FacetNormal);
float3 V = normalize(View);
float faceLight = saturate(.5+.5*dot(N,normalize(float3(-.48,.28,.82))));
float sheen = pow(saturate(dot(reflect(-V,N),normalize(float3(-.56,.31,.76)))),5);
float grain = frac(v*2.35+.30*u+.55*(profile-gleam));
float incision = (1-smoothstep(.025,.115+fwidth(grain),abs(grain-.50)))*profile;
// 暗腔占据真实切面的中央。两侧折唇错开，视角改变时背壁沿刀宽错动。
float parallax = .13 * dot(reflect(-V,N),normalize(float3(.42,.64,-.35)));
float seam = v - (.14*(profile-.5) + .075*sin(12*u + 1.8*gleam) + parallax);
float throat = 1-smoothstep(.14,.38,abs(seam));
float iceLip = 1-smoothstep(.025,.12+fwidth(seam),abs(seam-.35));
float farLip = 1-smoothstep(.018,.095+fwidth(seam),abs(seam+.31));
float cover = saturate(body + lip*.76 + flash*.32 + shadow*.68 + bevel*.49 + incision*.39);
float3 haze = lerp(float3(.11,.12,.55),float3(.37,.55,1.25),saturate(.52+.48*v));
float3 rim = lerp(float3(1.35,1.53,2.45), Edge.rgb/max(.001,ridge)*2.4,.35);
// 新刀的亮点沿出刃方向走；旧刀腹先退，窄边在下一刀经过时仍可读。
float pulseTravel = saturate(.72*saturate(Progress)+.28*(1-ageFade));
float pulse = exp2(-40*(travel-pulseTravel)*(travel-pulseTravel));
float wake = smoothstep(.08,.9,ageFade) * (.28+.72*pulse);
float visibility = reveal*tipFade*ageFade;
float cutIn = reveal*tipFade*smoothstep(.06,.76,ageFade);
float edgeHold = reveal*tipFade*sqrt(ageFade);
Coverage = saturate(max(visibility*cover*(.36+.64*wake),
    cutIn*throat*(.93+.06*wake) + edgeHold*(.80*iceLip+.66*farLip)));
float3 folded = lerp(float3(.015,.010,.071),float3(.12,.22,.76),faceLight);
float3 outer = body*haze+shadow*folded+bevel*float3(.58,.84,2.05)
    +incision*(.28+.76*faceLight)*lerp(float3(.18,.27,1.08),float3(1.36,1.56,2.45),sheen)
    +lip*rim+flash*float3(.65,.78,1.25);
float3 walls = lerp(float3(.005,.009,.058),float3(.026,.053,.26),faceLight)*(.35+.65*profile);
float3 inner = iceLip*(.34+.76*gleam)*lerp(float3(.15,.46,1.65),float3(2.3,3.0,4.6),pulse)
    + farLip*(.14+.65*profile)*lerp(float3(.10,.17,.66),float3(.38,.36,.94),sheen);
return visibility*outer*(.28+.72*wake)*(1-.86*throat) + cutIn*walls*throat + edgeHold*inner;
"""


def scar_material(directory):
    editor, edit = ue.EditorAssetLibrary, ue.MaterialEditingLibrary
    name = 'M_Pyrios_Aftercut'
    path = directory+'/'+name
    if editor.does_asset_exist(path):
        mat = ue.load_asset(path)
        if editor.get_metadata_tag(mat,'Pyrios.Aftercut') == SURFACE_VERSION:
            return mat
        if editor.get_metadata_tag(mat,'Pyrios.Aftercut') not in ('three-incisions-1', 'source-edge-1', 'refracted-edge-1', 'refracted-edge-2', 'source-lamella-1', 'source-lamella-2', 'fluted-scar-1','rift-facets-2','slow-reference-edge-1', VERSION):
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
    configure_native_custom(ue,node,['UV',*textures,'Life','Progress','Reverse','FacetNormal','View'],SHADE,'CMOT_Float3','源纹理切面与刃口',
                            native_sync=lambda _,call:call(),additional_outputs=[('Coverage','CMOT_Float1')])
    def connect(src,pin,dst,field):
        if not edit.connect_material_expressions(src,pin,dst,field):
            raise RuntimeError('斩痕材质连接失败 '+field)
    connect(uv,'',node,'UV')
    # 亮边像素在 089 图顶端，两个刀面分别采样。镜像截面保留原图沿行刀方向的渐变。
    for i,(key,t) in enumerate(textures.items()):
        sample = edit.create_material_expression(mat,ue.MaterialExpressionTextureSample,-470,-280+i*140)
        sample.set_editor_properties(dict(texture=t,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_COLOR))
        coords = edit.create_material_expression(mat,ue.MaterialExpressionCustom,-740,-280+i*140)
        if key == 'Edge':
            mapping = 'return float2(lerp(.08,.91,UV.x),.008+.94*abs(2*UV.y-1));'
        elif key == 'Highlight':
            mapping = 'return float2(lerp(.12,.96,UV.x),.07+.85*abs(2*UV.y-1));'
        else:
            mapping = 'return float2(lerp(.12,.94,UV.x),.09+.88*abs(2*UV.y-1));'
        configure_native_custom(ue,coords,['UV'],mapping,'CMOT_Float2','原图切面展开',native_sync=lambda _,call:call())
        connect(uv,'',coords,'UV')
        connect(coords,'',sample,'Coordinates')
        connect(sample,'RGBA',node,key)
    for y,kind,slot in [(350,ue.MaterialExpressionPixelNormalWS,'FacetNormal'),(490,ue.MaterialExpressionCameraVectorWS,'View')]:
        connect(edit.create_material_expression(mat,kind,-450,y),'',node,slot)
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


def extend_space_cuts(system, directory):
    """共用原三刀的落点、方向与寿命。在同一斩痕周围折射场地背景。"""
    lib = ue.GGYGONiagaraCompileLibrary
    editor = ue.EditorAssetLibrary
    tag = 'Pyrios.AftercutRefraction'
    sheath = refraction_material(directory)
    if editor.get_metadata_tag(system, tag) == 'volume-cut-1':
        return False
    renderers = lib.authoring_get_renderer_identities(system, SCARS).renderers
    if len(renderers) not in (1,2) or any(not r.renderer_class.endswith('NiagaraMeshRendererProperties') for r in renderers):
        raise RuntimeError('缺少三刀的切面渲染器 '+system.get_name())
    mesh = scar_mesh(directory)
    core = renderers[0].renderer_index
    def configure(index, props):
        result = lib.authoring_set_renderer_data(system, SCARS, index, json.dumps(props))
        if not result.succeeded:
            raise RuntimeError(result.error)
    def shape(width, depth):
        return [dict(Mesh=mesh.get_path_name(), Scale=dict(X=1.85,Y=width,Z=depth))]
    configure(core, dict(Meshes=shape(1.40,1.65)))
    if len(renderers)==1:
        layer = lib.authoring_add_renderer(system, SCARS, ue.load_class(None, '/Script/Niagara.NiagaraMeshRendererProperties'))
        if not layer.succeeded:
            raise RuntimeError(layer.error)
        field_index=layer.renderer_index
    else:
        field_index=renderers[1].renderer_index
        data=lib.authoring_get_renderer_data(system,SCARS,field_index)
        if not data.succeeded or sheath.get_path_name() not in data.property_values:
            raise RuntimeError('现有斩痕折射层与配置不符')
    configure(field_index, {'bOverrideMaterials':True})
    bind = NiagaraBuilder.attribute_binding
    configure(field_index, dict(Meshes=shape(3.6,3.1),
        OverrideMaterials=[dict(ExplicitMat=sheath.get_path_name())],
        PositionBinding=bind('Particles.Position'), MeshOrientationBinding=bind('Particles.MeshOrientation'),
        ScaleBinding=bind('Particles.Scale'),ColorBinding=bind('Particles.Color'),SortOrderHint=-1))
    editor.set_metadata_tag(system, tag, 'volume-cut-1')
    return True


def refraction_material(directory):
    """用原 Distor 层的扰动与遮罩，按刀线在视口的实际方向偏移背景采样。"""
    editor, edit = ue.EditorAssetLibrary, ue.MaterialEditingLibrary
    name = 'M_Pyrios_AftercutRefraction'
    path = directory+'/'+name
    if editor.does_asset_exist(path):
        material = ue.load_asset(path)
        stamp = editor.get_metadata_tag(material, 'Pyrios.AftercutRefraction')
        if stamp == 'travelling-wave-1':
            return material
        if stamp not in ('cut-field-1','cut-field-2'):
            raise RuntimeError('已有未识别的空间斩折射材质 '+path)
        edit.delete_all_material_expressions(material)
    else:
        material = ue.AssetToolsHelpers.get_asset_tools().create_asset(name,directory,ue.Material,ue.MaterialFactoryNew())
    material.set_editor_properties(dict(blend_mode=ue.BlendMode.BLEND_TRANSLUCENT,shading_model=ue.MaterialShadingModel.MSM_UNLIT,
        two_sided=False,used_with_niagara_mesh_particles=True,used_with_niagara_ribbons=True,refraction_method=ue.RefractionMode.RM_2D_OFFSET,
        translucency_pass=ue.MaterialTranslucencyPass.MTP_BEFORE_DOF))
    def connect(a, pin, b, field):
        if not edit.connect_material_expressions(a,pin,b,field):
            raise RuntimeError('空间斩折射输入失败 '+field)
    uv = edit.create_material_expression(material,ue.MaterialExpressionTextureCoordinate,-970,0)
    coords = edit.create_material_expression(material,ue.MaterialExpressionCustom,-740,-200)
    configure_native_custom(ue,coords,['UV'],'return float2(UV.x,.015+.50*abs(UV.y*2-1));',
        'CMOT_Float2','展开原折射遮罩',native_sync=lambda _,f:f())
    connect(uv,'',coords,'UV')
    node = edit.create_material_expression(material,ue.MaterialExpressionCustom,-230,0)
    code = """
float s = UV.y*2-1;
float across = abs(s);
float belly = smoothstep(0,.12,UV.x)*(1-smoothstep(.86,1,UV.x));
float reveal = 1-smoothstep(Clock.r-.085,Clock.r,lerp(UV.x,1-UV.x,Clock.g));
float width = 1-smoothstep(.25,.98,across);
float etching = .28+.72*sqrt(saturate(Mask.r));
float field = Life*belly*width*reveal*etching;
// 由屏幕导数求刀宽的投影方向。刀脊两侧偏移相反，切面退光时位移同时归零。
float2 gradient = float2(ddx(s),ddy(s));
float2 normal = gradient*rsqrt(max(dot(gradient,gradient),1e-9));
// 前缘推出、后缘回吸；相位随粒子老化远离刀脊，角色停下后波峰仍继续传播。
float phase = saturate(1-Life);
float travel = lerp(UV.x,1-UV.x,Clock.g);
float front = .13+.62*phase+.085*Noise.r+.09*(travel-.5);
float distanceToFront = across-front;
float outward = exp2(-72*distanceToFront*distanceToFront);
float trailing = exp2(-130*(distanceToFront+.22)*(distanceToFront+.22));
float displacement = (outward-.73*trailing)*s/(.075+across);
float curl = (Noise.r-.42)*sin(3.14159*travel);
float2 tangent = float2(-normal.y,normal.x);
Offset = (normal*displacement+tangent*(.16*curl*outward))*field*(Size.y*.037/max(Size,float2(1,1)));
Haze = field*(.047+.19*outward+.052*trailing);
return lerp(float3(.05,.08,.32),float3(.28,.53,1.15),outward);

"""
    configure_native_custom(ue,node,['UV','Clock','Life','Size','Mask','Noise'],code,'CMOT_Float3','刀线两侧的屏幕折射',
        native_sync=lambda _,f:f(),additional_outputs=[('Offset','CMOT_Float2'),('Haze','CMOT_Float1')])
    connect(uv,'',node,'UV')
    color=edit.create_material_expression(material,ue.MaterialExpressionParticleColor,-660,360)
    connect(color,'',node,'Clock')
    connect(color,'A',node,'Life')
    view=edit.create_material_expression(material,ue.MaterialExpressionViewSize,-680,480)
    connect(view,'',node,'Size')
    directory_tex='/Game/Characters/Shared/FX/ZZZ/Textures/'
    for i,(key,asset) in enumerate((('Mask','Eff_MeleeTrail_244_18e1e41208b4'),('Noise','Eff_Noise_098_c0bd347eec31'))):
        texture=ue.load_asset(directory_tex+asset)
        if not isinstance(texture,ue.Texture2D):
            raise RuntimeError('缺少原折射纹理 '+asset)
        sample=edit.create_material_expression(material,ue.MaterialExpressionTextureSample,-510,-220+i*140)
        sample.set_editor_properties(dict(texture=texture,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.srgb
            else ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR))
        connect(coords,'',sample,'Coordinates')
        connect(sample,'RGB',node,key)
    for pin,prop in (('',ue.MaterialProperty.MP_EMISSIVE_COLOR),('Offset',ue.MaterialProperty.MP_REFRACTION),('Haze',ue.MaterialProperty.MP_OPACITY)):
        if not edit.connect_material_property(node,pin,prop):
            raise RuntimeError('空间斩折射输出失败 '+pin)
    errors=edit.recompile_material(material)
    if errors:
        raise RuntimeError('空间斩折射材质编译失败 '+str(errors))
    editor.set_metadata_tag(material,'Pyrios.AftercutRefraction','travelling-wave-1')
    if not editor.save_loaded_asset(material,False):
        raise RuntimeError('空间斩折射材质保存失败')
    return material
