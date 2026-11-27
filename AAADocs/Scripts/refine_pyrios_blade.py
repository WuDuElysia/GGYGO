"""佩洛伊斯普通攻击刃光。正式 Montage 窗口驱动定形月牙、上挑轨迹与空间切口。"""
import json
import sys
from pathlib import Path
import unreal as ue

PROJECT = Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))
sys.path.insert(0, str(PROJECT / 'AAADocs/Scripts'))
from pyrios_authored_arc import opening, ground_sweep
from pyrios_normal03_finisher import refine_normal03
from pyrios_multicut_marks import SCARS, VERSION as CUT_VERSION, add_cut_light, add_opening_marks, extend_space_cuts, refraction_material, scar_material
from pyrios_prism_material import build_prism_materials
from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import NiagaraBuilder, TYPES, EMPTY_EMITTER

EDITOR = ue.EditorAssetLibrary
LIB = ue.GGYGONiagaraCompileLibrary
EDIT = ue.MaterialEditingLibrary
DAWN = '/Game/Characters/Player/Pyrios/FX/Dawn'
SKILL = '/Game/Characters/Player/Pyrios/FX/Skill/'
EMITTER = 'Emberglow_LiveBlade'
STAMP = 'Pyrios.EmberglowBrush'
VERSION = 'live-v1'
SYSTEM_VERSION = 'weapon-filament-v6'
FINISHER_BLADE = 'Pyrios_FinalSweep'
SYSTEMS = (
    ('NS_Pyrios_Normal01_MainComposition_2a7c90937cab', 0.23),
    ('NS_Pyrios_Normal02_MainComposition_d7bd1888f9a7', 0.245),
)
# 地面投影仍在原坐标系。关闭飘离斩击的烟团以及重复的刀弧和碎屑。
AIRBORNE_SMOKE = {'M00_Smoke_Cone01__2_', 'M01_root_Smoke_blur__1_', 'M03_root_smoke__2_',
                  'M03_root_Smoke_ci__1_', 'M03_root_An_Smoke_Ground__7_'}
SECONDARY_CUT = {'M01_root_lizi__1_', 'M01_root_Line_Trail__1_', 'M01_root_Line_Trail__1__ParticleTrail',
                 'M01_root_Particle_System', 'M02_X_WeaponTrailCustom', 'M02_X_WeaponTrailCustom_XWeaponTrailProxy',
                 'M03_root_Rocl__1_', 'M03_root_Particle_001', 'M03_root_Trail_Fire_02__5_'}
def require(ok, message):
    if not ok:
        raise RuntimeError(message)

def tool(full, **arguments):
    group, name = full.rsplit('.', 1)
    result = ue.ToolsetRegistry.execute_tool(group, name, json.dumps(arguments))
    require(result.is_complete and not result.error, name+' '+str(result.error))
    return json.loads(result.value or '{}').get('returnValue')

def material(warm=False):
    texture_name = 'T_Pyrios_Emberglow_Stroke'
    name = 'M_Pyrios_Blade' if warm else 'M_Pyrios_Emberglow'
    path = DAWN + '/' + name
    mat = ue.load_asset(path) if EDITOR.does_asset_exist(path) else None
    if mat and EDITOR.get_metadata_tag(mat, STAMP) == VERSION:
        return mat
    tools = ue.AssetToolsHelpers.get_asset_tools()
    texture = ue.load_asset(DAWN+'/'+texture_name) if EDITOR.does_asset_exist(DAWN+'/'+texture_name) else None
    if not texture:
        task = ue.AssetImportTask()
        task.set_editor_properties(dict(filename=str(PROJECT/'AAADocs/Assets/Pyrios/FX'/(texture_name+'.png')),
                                        destination_path=DAWN, destination_name=texture_name, automated=True, save=False))
        tools.import_asset_tasks([task])
        texture = ue.load_asset(DAWN+'/'+texture_name)
    require(isinstance(texture, ue.Texture2D), '未导入笔触纹理')
    if not warm:
        texture.set_editor_properties(dict(srgb=False, compression_settings=ue.TextureCompressionSettings.TC_MASKS,
            address_x=ue.TextureAddress.TA_CLAMP, address_y=ue.TextureAddress.TA_CLAMP))
        require(EDITOR.save_loaded_asset(texture, False), '纹理保存失败')
    if mat:
        EDIT.delete_all_material_expressions(mat)
    else:
        mat = tools.create_asset(name, DAWN, ue.Material, ue.MaterialFactoryNew())
    mat.set_editor_properties(dict(blend_mode=ue.BlendMode.BLEND_ALPHA_COMPOSITE,
        shading_model=ue.MaterialShadingModel.MSM_UNLIT, two_sided=True,
        used_with_niagara_ribbons=True, used_with_niagara_mesh_particles=True, used_with_niagara_sprites=warm))
    sample=EDIT.create_material_expression(mat,ue.MaterialExpressionTextureSample,-650,0)
    sample.set_editor_properties(dict(texture=texture,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_MASKS))
    particle=EDIT.create_material_expression(mat,ue.MaterialExpressionParticleColor,-650,220)
    color=EDIT.create_material_expression(mat,ue.MaterialExpressionCustom,-290,0)
    edge, threads, body = ('2.6,1.9,0.92','1.2,0.42,0.08','0.35,0.075,0.024') if warm else (
        '1.75,2.15,3.75','0.26,0.31,1.05','0.085,0.079,0.32')
    emission = f'return Fade*(Ink.r*float3({edge})+Ink.g*float3({threads})+Ink.b*float3({body}));'
    configure_native_custom(ue,color,['Ink','Fade'],emission,'CMOT_Float3','外刃、丝纹和透光底色',
                            native_sync=lambda _,fn:fn())
    opacity=EDIT.create_material_expression(mat,ue.MaterialExpressionMultiply,-290,220)
    connect=EDIT.connect_material_expressions
    require(all([connect(sample,'RGB',color,'Ink'),connect(particle,'A',color,'Fade'),
                 connect(sample,'A',opacity,'A'),connect(particle,'A',opacity,'B'),
                 EDIT.connect_material_property(color,'',ue.MaterialProperty.MP_EMISSIVE_COLOR),
                 EDIT.connect_material_property(opacity,'',ue.MaterialProperty.MP_OPACITY)]),'刀光采样接线失败')
    require(not EDIT.recompile_material(mat),'笔触材质编译失败')
    EDITOR.set_metadata_tag(mat,STAMP,VERSION)
    require(EDITOR.save_loaded_asset(mat,False),'刀光材质保存失败')
    return mat

def ref(obj):
    return {'refPath': obj.get_path_name()}

def module(script, asset, *, emitter=EMITTER, **inputs):
    return dict(kind='Module',emitterName=emitter,scriptName=script,
        moduleAsset={'refPath':asset+'.'+asset.rsplit('/',1)[-1]},
        inputs=[dict(namePath=[name],inputData=value) for name,value in inputs.items()])

def target(name, kind):
    return dict(name='Particles.'+name, type={'classStructOrEnum':{'refPath':TYPES[kind]}})

def assign(script, *, emitter=EMITTER, **rows):
    return dict(kind='Assignments',emitterName=emitter,scriptName=script,
                assignments=[dict(**target(name,kind),hlslExpression=value) for name,(kind,value) in rows.items()])

def blade_section():
    # X 从刀根到刀尖，Y 在扫掠面法向上。纹理 V 在正反面回走，外沿纹理咬合。
    # 把光量集中在刀锋外三分之一。V=.77 的白色亮脊准确压在刀尖，刃外是柔和的蓝晕。
    profile = [(0,0),(.18,-.012),(.52,-.029),(.77,-.013),(1,0),
               (.77,.019),(.52,.047),(.18,.018)]
    return [dict(Position=dict(X=.5+(v-.77)*.48,Y=y),TextureV=v) for v,y in profile]


def weapon_frame():
    di=ue.new_object(ue.load_class(None,'/Script/Niagara.NiagaraDataInterfaceSkeletalMesh'))
    state={'SourceMode':'AttachParent','bRequireCurrentFrameData':True,'FilteredBones':['Ctr_Weapon_A_02','Ctr_Weapon_B_05']}
    require(tool('EditorToolset.ObjectToolset.SetProperties',instance=ref(di),values=json.dumps(state)), '武器骨绑定失败')
    # 使用 Mesh 的世界空间骨位；场地层的 -64 cm 不参与刀光定位。
    # LOD0 参考网格的刀尖顶点对 B_05 的权重为 99.84%。CustomSideVector 以朝向的反向为纹理 V 正方向。
    # UE 5.9 的世界骨采样会把缩放向量一并旋转。用组件内、世界两份旋转消去这一旋转，再应用刀尖局部偏移。
    body = """
int Count; {{DI}}.GetFilteredBoneCount(Count);
int Base; int Tip; {{DI}}.GetFilteredBone(0,Base); {{DI}}.GetFilteredBone(1,Tip);
float3 A; float3 B; float3 AS; float3 BS; float3 AV; float3 BV;
float4 AR; float4 BR;
{{DI}}.GetSkinnedBoneDataWS(Base,A,AR,AS,AV);
{{DI}}.GetSkinnedBoneDataWS(Tip,B,BR,BS,BV);
float3 LocalB; float4 LocalBR; float3 LocalBS; float3 LocalBV;
{{DI}}.GetSkinnedBoneData(Tip,LocalB,LocalBR,LocalBS,LocalBV);
float3 InBoneAxes = BS + 2.0*cross(-BR.xyz, cross(-BR.xyz,BS)+BR.w*BS);
float3 BoneScale = InBoneAxes + 2.0*cross(LocalBR.xyz,cross(LocalBR.xyz,InBoneAxes)+LocalBR.w*InBoneAxes);
float3 Offset = float3(40.55396,-1.86295,0.0)*BoneScale;
float3 EndPoint = B + Offset + 2.0*cross(BR.xyz,cross(BR.xyz,Offset)+BR.w*Offset);
float3 Axis=EndPoint-A; float Width=length(Axis);
"""
    return di, body

def add_live_blade(system, mat, end, accents=None, combo_finisher=False):
    emitter = FINISHER_BLADE if combo_finisher else EMITTER
    made=LIB.authoring_add_emitter(system,ue.load_asset(EMPTY_EMITTER),emitter)
    require(made.succeeded,made.error)
    data=LIB.authoring_set_emitter_data(system,emitter,json.dumps({'bLocalSpace':False,'CalculateBoundsMode':'Dynamic',
        'AttributesToPreserve':['Particles.UniqueID']}))
    require(data.succeeded,data.error)
    di, body = weapon_frame()
    body += """
{{OUT:Particles.BladeHasSample}} = Count==2 && Base>=0 && Tip>=0 && Width>1;
{{OUT:Particles.Position}} = 0.5*(A+EndPoint);
{{OUT:Particles.RibbonFacing}} = -Axis/max(Width,0.001);
{{OUT:Particles.RibbonWidth}} = Width;
"""
    outputs = [target('BladeHasSample','Bool'),target('Position','Position'),
               target('RibbonFacing','Vector'),target('RibbonWidth','Float')]
    if combo_finisher:
        # 每次变招重新接带，前一刀的余光独立消散。分段只划分表现，不驱动动作。
        body += '''
float phase = Emitter.Age;
{{OUT:Particles.RibbonWidth}} = phase < 0.40 ? 0.0 : Width;
{{OUT:Particles.BladeStroke}}.Index =
    (phase < 0.095) ? 0 :
    (phase < 0.20)  ? 1 :
    (phase < 0.40)  ? 2 :
    (phase < 0.54)  ? 3 :
    (phase < 0.73)  ? 4 : 5;
{{OUT:Particles.BladeStroke}}.AcquireTag = 0;
'''
        outputs.append(target('BladeStroke','ID'))
    ps,pu,eu='ParticleSpawnScript','ParticleUpdateScript','EmitterUpdateScript'
    num=NiagaraBuilder.num
    lifetime = '0.18' if combo_finisher else '0.107'
    if accents:
        lifetime = '0.166'
    # 第二次挥刀先绕到角色另一侧蓄势。只在正式上挑时生成轨迹采样。
    first_sample = .134 if accents else (.40 if combo_finisher else .060)
    work=[module(eu,'/Niagara/Modules/Emitter/EmitterState',emitter=emitter,**{
        'Life Cycle Mode':NiagaraBuilder.enum('/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode','NewEnumerator1','Self'),
        'Loop Behavior':NiagaraBuilder.enum('/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions','NewEnumerator1','Once'),
        'Loop Duration':num('Float',end)}),
        module(eu,'/Niagara/Modules/Emitter/SpawnPerFrame',emitter=emitter,**{'Spawn Count':NiagaraBuilder.hlsl(f'Emitter.Age >= {first_sample} ? 1 : 0')}),
        assign(ps,emitter=emitter,Lifetime=('Float',lifetime),Color=('LinearColor','float4(1,1,1,1)')),
        dict(kind='ParticleRead',emitterName=emitter,scriptName=ps,interfaceTemplate=ref(di),
             outputTargets=outputs,
             hlslBodyTemplate=body),
        assign(ps,emitter=emitter,Alive=('Bool','Particles.Alive && Particles.BladeHasSample')),
        module(pu,'/Niagara/Modules/Update/Lifetime/ParticleState',emitter=emitter),
        assign(pu,emitter=emitter,Color=('LinearColor','float4(1,1,1,pow(saturate(1.0-Particles.NormalizedAge),1.15))'))]
    if accents:
        # 同一次挥刀的历史采样沿刀尖方向略微外展。出生帧先给渲染器有效坐标。
        echo_position = 'Particles.Position - Particles.RibbonFacing * Particles.RibbonWidth * '
        for script, expansion in [(ps, '0.35'), (pu, '(0.35 + 0.18 * saturate((Particles.NormalizedAge - 0.05) / 0.8))')]:
            work.append(assign(script, emitter=emitter, PrismEchoPosition=('Position',echo_position+expansion),
                               PrismEchoWidth=('Float','Particles.RibbonWidth * 0.115')))
        # 只选挥刀约 0.19 秒时的一个轨迹采样，让折光留在对应的外刃上。
        work.append(assign(ps,emitter=emitter, PrismFlareTag=('Int','Emitter.Age >= 0.19 && (Emitter.Age - Engine.DeltaTime) < 0.19 ? 1 : 0'),
                           PrismFlarePosition=('Position','Particles.Position - Particles.RibbonFacing * Particles.RibbonWidth * 0.31'),
                           PrismFlareSize=('Vector2','float2(75,75)')))
    res=tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch',system=ref(system),workItems=work)
    require(res.get('bApplied'),res.get('error','刀光栈制作失败'))
    def add_blade_renderer(surface, position, width, solid):
        renderer = LIB.authoring_add_renderer(system, emitter, ue.load_class(None, '/Script/Niagara.NiagaraRibbonRendererProperties'))
        require(renderer.succeeded, renderer.error)
        binding = NiagaraBuilder.attribute_binding
        props = dict(Material=surface.get_path_name(), FacingMode='CustomSideVector', Shape='Plane',
                     MaxNumRibbons=6 if combo_finisher else 1, bUseGPUInit=False, TessellationMode='Automatic',
                     PositionBinding=binding(position), RibbonWidthBinding=binding(width),
                     RibbonFacingBinding=binding('Particles.RibbonFacing'))
        if solid:
            enabled = LIB.authoring_set_renderer_data(system, emitter, renderer.renderer_index, json.dumps({'Shape':'Custom'}))
            require(enabled.succeeded, enabled.error)
            props.update(Shape='Custom', CustomVertices=blade_section(), bCustomShapeClosed=True)
        result = LIB.authoring_set_renderer_data(system, emitter, renderer.renderer_index, json.dumps(props))
        require(result.succeeded, result.error)
        link = LIB.configure_ribbon_unique_id(system, emitter, renderer.renderer_index, 'Particles.BladeStroke' if combo_finisher else '')
        require(link.applied, link.error)

    add_blade_renderer(mat, 'Particles.Position', 'Particles.RibbonWidth', True)
    if accents:
        add_blade_renderer(accents['Echo'], 'Particles.PrismEchoPosition', 'Particles.PrismEchoWidth', False)
        sprite = LIB.authoring_add_renderer(system, emitter, ue.load_class(None, '/Script/Niagara.NiagaraSpriteRendererProperties'))
        require(sprite.succeeded, sprite.error)
        binding = NiagaraBuilder.attribute_binding
        props = dict(Material=accents['Flare'].get_path_name(), PositionBinding=binding('Particles.PrismFlarePosition'),
                     SpriteSizeBinding=binding('Particles.PrismFlareSize'), RendererVisibility=1,
                     RendererVisibilityTagBinding=binding('Particles.PrismFlareTag'))
        result = LIB.authoring_set_renderer_data(system, emitter, sprite.renderer_index, json.dumps(props))
        require(result.succeeded, result.error)

def style_existing(system, mat, live):
    changed=False
    for em in LIB.authoring_get_system_summary(system).emitters:
        name=em.emitter_name
        if name in (EMITTER, FINISHER_BLADE, SCARS):
            continue
        # 固定的可见刀弧由活刃带替代。签名场仍由原动作场配置验证并消费。
        suppress=live and (name.startswith('M00_root_Trail_rot_') or name in SECONDARY_CUT or name in AIRBORNE_SMOKE)
        for renderer in LIB.authoring_get_renderer_identities(system,name).renderers:
            old=json.loads(LIB.authoring_get_renderer_data(system,name,renderer.renderer_index).property_values)
            update={}
            if live and 'SignedField' in renderer.renderer_class:
                if name == 'M00_root_Trail_rot_Main_Distor' and old.get('bIsEnabled') is False:
                    update = {'bIsEnabled': True}
            elif suppress:
                if old.get('bIsEnabled',True):
                    update={'bIsEnabled':False}
            elif not live and any(previous in json.dumps(old) for previous in ('/M_Pyrios_Blade.', '/M_Pyrios_Emberglow.')):
                if renderer.renderer_class.endswith('NiagaraMeshRendererProperties'):
                    update={'bOverrideMaterials':True,'OverrideMaterials':[{'ExplicitMat':mat.get_path_name()}]}
                else:
                    update={'Material':mat.get_path_name()}
            if update:
                out=LIB.authoring_set_renderer_data(system,name,renderer.renderer_index,json.dumps(update))
                require(out.succeeded,out.error)
                changed=True
    return changed

def add_refraction_shell(system, emitter, field):
    """刀身与折射共用世界空间武器采样、分刀 ID 和寿命。波面围在刃腹外侧。"""
    tag='Pyrios.BladeVolume'
    if EDITOR.get_metadata_tag(system,tag)=='wake-1':
        return False
    renderers=LIB.authoring_get_renderer_identities(system,emitter).renderers
    for renderer in renderers:
        if not renderer.renderer_class.endswith('NiagaraRibbonRendererProperties'):
            continue
        props=json.loads(LIB.authoring_get_renderer_data(system,emitter,renderer.renderer_index).property_values)
        if not props.get('bCustomShapeClosed') or not any(label in str(props.get('Material')) for label in
                ('MI_Pyrios_Prism_Draw','MI_Pyrios_Prism_Crescent','MI_Pyrios_Prism_Cross')):
            continue
        def configure(index,values):
            result=LIB.authoring_set_renderer_data(system,emitter,index,json.dumps(values))
            require(result.succeeded,result.error)
        profile=blade_section()
        configure(renderer.renderer_index,dict(CustomVertices=profile))
        wave=LIB.authoring_add_renderer(system,emitter,ue.load_class(None,'/Script/Niagara.NiagaraRibbonRendererProperties'))
        require(wave.succeeded,wave.error)
        index=wave.renderer_index
        configure(index,dict(Shape='Custom'))
        for vertex in profile:
            vertex['Position']['Y'] *= 1.55
            vertex['Position']['X'] = .5 + (vertex['Position']['X']-.5)*1.34
        bind=NiagaraBuilder.attribute_binding
        configure(index,dict(Shape='Custom',CustomVertices=profile,bCustomShapeClosed=True,Material=field.get_path_name(),
                FacingMode='CustomSideVector',MaxNumRibbons=6 if emitter==FINISHER_BLADE else 1,bUseGPUInit=False,
                PositionBinding=bind('Particles.Position'),RibbonWidthBinding=bind('Particles.RibbonWidth'),
                RibbonFacingBinding=bind('Particles.RibbonFacing'),ColorBinding=bind('Particles.Color'),SortOrderHint=-1))
        link=LIB.configure_ribbon_unique_id(system,emitter,index,'Particles.BladeStroke' if emitter==FINISHER_BLADE else '')
        require(link.applied,link.error)
        EDITOR.set_metadata_tag(system,tag,'wake-1')
        return True
    raise RuntimeError('当前武器的闭合刃面缺失 '+system.get_name())


def bind_animated_shape(system, emitter, work, indices, bindings):
    result = tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch', system=ref(system), workItems=work)
    require(result.get('bApplied'), result.get('error','刀痕粒子栈制作失败'))
    props = {key:NiagaraBuilder.attribute_binding('Particles.'+value) for key,value in bindings.items()}
    for index in indices:
        result = LIB.authoring_set_renderer_data(system,emitter,index,json.dumps(props))
        require(result.succeeded,result.error)


def apply_blade_volume(system, emitter, field):
    installed = add_refraction_shell(system,emitter,field)
    tag = 'Pyrios.BladeTrailTaper'
    if EDITOR.get_metadata_tag(system,tag)=='tip-anchored-1':
        return installed
    blade_indices, field_indices = [], []
    for entry in LIB.authoring_get_renderer_identities(system,emitter).renderers:
        if entry.renderer_class.endswith('NiagaraRibbonRendererProperties'):
            rd = LIB.authoring_get_renderer_data(system,emitter,entry.renderer_index)
            require(rd.succeeded,rd.error)
            props = json.loads(rd.property_values)
            surface = str(props.get('Material',''))
            if props.get('bCustomShapeClosed') and field.get_path_name() in surface:
                field_indices.append(entry.renderer_index)
            elif props.get('bCustomShapeClosed') and any(name in surface for name in
                    ('MI_Pyrios_Prism_Draw.','MI_Pyrios_Prism_Crescent.','MI_Pyrios_Prism_Cross.')):
                blade_indices.append(entry.renderer_index)
    require(len(blade_indices)==len(field_indices)==1,'武器刀面和折射应各有一个闭合 Ribbon：'+system.get_name())
    # 新采样保留全刃，旧采样的刀根向该帧刀尖收拢。原始中心与宽度仍供外弦和闪点读取。
    center = 'Particles.Position - Particles.RibbonFacing * (.5*(Particles.RibbonWidth-Particles.TrailWidth))'
    work = [assign('ParticleSpawnScript',emitter=emitter,
                   TrailCenter=('Position','Particles.Position'),TrailWidth=('Float','Particles.RibbonWidth')),
            assign('ParticleUpdateScript',emitter=emitter,
                   TrailRetraction=('Float','saturate((Particles.NormalizedAge-.075)/.795)')),
            assign('ParticleUpdateScript',emitter=emitter,
                   TrailWidth=('Float','Particles.RibbonWidth * (1.0 - .95*Particles.TrailRetraction*Particles.TrailRetraction*(3.0-2.0*Particles.TrailRetraction))')),
            assign('ParticleUpdateScript',emitter=emitter,
                   TrailCenter=('Position',center))]
    bind_animated_shape(system,emitter,work,blade_indices+field_indices,dict(PositionBinding='TrailCenter', RibbonWidthBinding='TrailWidth'))
    EDITOR.set_metadata_tag(system,tag,'tip-anchored-1')
    return True


def animate_opening_marks(system):
    tag = 'Pyrios.AftercutTravel'
    if EDITOR.get_metadata_tag(system,tag)=='entry-to-tip-1':
        return False
    renderers = LIB.authoring_get_renderer_identities(system,SCARS).renderers
    require(len(renderers)==2 and all(r.renderer_class.endswith('NiagaraMeshRendererProperties') for r in renderers),
            '三道斩痕的刀面与折射网格缺失：'+system.get_name())
    rd = LIB.authoring_get_renderer_data(system,SCARS,renderers[0].renderer_index)
    require(rd.succeeded,rd.error)
    length_scale = json.loads(rd.property_values)['Meshes'][0]['scale']['x']
    # 原始切面中心和朝向保持锁定。推进两端时固定入刀点，再让刀腹和折射面一起收窄。
    work = [assign('ParticleSpawnScript',emitter=SCARS,
                   CutDrawCenter=('Position','Particles.Position'),CutDrawScale=('Vector','float3(0,0,0)')),
            assign('ParticleUpdateScript',emitter=SCARS,
                   CutReach=('Float','1.0-.86*pow(1.0-saturate((Particles.NormalizedAge-.06)/.31),2)'),
                   CutGirth=('Float','lerp(1.0,.085,saturate((Particles.NormalizedAge-.34)/.58))')),
            assign('ParticleUpdateScript',emitter=SCARS,
                   CutDrawScale=('Vector','Particles.Scale * float3(Particles.CutReach,Particles.CutGirth,sqrt(Particles.CutGirth))'),
                   CutDrawCenter=('Position',f'Particles.Position - Particles.CutDirection * ((Particles.CutReverse ? -1.0 : 1.0) * {50.0*length_scale:.6f} * Particles.Scale.x * (1.0-Particles.CutReach))'))]
    bind_animated_shape(system,SCARS,work,[r.renderer_index for r in renderers],
                        dict(PositionBinding='CutDrawCenter',ScaleBinding='CutDrawScale'))
    EDITOR.set_metadata_tag(system,tag,'entry-to-tip-1')
    return True


def bind_cut_brushes(system):
    tag = 'Pyrios.AftercutBrush'
    if EDITOR.get_metadata_tag(system,tag)=='three-strokes-1':
        return False
    renderers=LIB.authoring_get_renderer_identities(system,SCARS).renderers
    faces=[]
    for entry in renderers:
        data=LIB.authoring_get_renderer_data(system,SCARS,entry.renderer_index)
        require(data.succeeded,data.error)
        if 'M_Pyrios_Aftercut.M_Pyrios_Aftercut' in data.property_values:
            faces.append(entry.renderer_index)
    require(len(faces)==1,'未找到唯一的三连切面渲染器')
    # 用 B 通道选原画的行，R/G/A 仍分别是显影、方向和退光；折射读取原粒子色。
    work=[assign('ParticleUpdateScript',emitter=SCARS,CutBrushColor=('LinearColor',
          'float4(Particles.Color.rg,Particles.UniqueID*.5,Particles.Color.a)'))]
    bind_animated_shape(system,SCARS,work,faces,dict(ColorBinding='CutBrushColor'))
    EDITOR.set_metadata_tag(system,tag,'three-strokes-1')
    return True


def finish(system):
    state=LIB.compile_authoring_batch(system)
    if not state.native_ready or not state.system_valid:
        diagnostics=LIB.read_system_compile_diagnostics(system)
        raise RuntimeError('Niagara 编译失败 '+system.get_name()+' '+diagnostics.export_text())
    EDITOR.set_metadata_tag(system,STAMP,SYSTEM_VERSION)
    require(EDITOR.save_loaded_asset(system,False),'未保存 '+system.get_name())
    ue.log('EMBERGLOW_SAVED '+system.get_name())

def build():
    material()  # 保留既有笔触材质供其它引用者使用。
    variants = build_prism_materials(DAWN)
    cut_surface = scar_material(DAWN)
    field = refraction_material(DAWN)
    for (name,end), style in zip(SYSTEMS, ('Draw','Crescent')):
        system=ue.load_asset(SKILL+name)
        require(system is not None,'缺正式普攻系统 '+name)
        if style=='Draw':
            installed=opening(system,DAWN,tool,assign,module)
            old={row.emitter_name for row in LIB.authoring_get_system_summary(system).emitters}
            if EMITTER in old:
                require(EDITOR.get_metadata_tag(system,STAMP) in ('live-v1','live-v2','live-v3','live-v4','live-v5','prism-v1','prism-v2','weapon-bevel-v3','weapon-filament-v4','weapon-filament-v5',SYSTEM_VERSION),'首刀旧发射器来源不明')
                tool('NiagaraToolsets.NiagaraToolset_System.RemoveEmitter',emitterRef={'system':ref(system),'emitterName':EMITTER})
                installed=True
            styled=style_existing(system,variants[style],True)
            if installed or styled:
                finish(system)
            continue
        if EDITOR.get_metadata_tag(system,STAMP)==SYSTEM_VERSION:
            if apply_blade_volume(system,EMITTER,field):
                finish(system)
            continue
        existing = [entry.emitter_name for entry in LIB.authoring_get_system_summary(system).emitters]
        if EMITTER in existing:
            require(EDITOR.get_metadata_tag(system,STAMP) in ('live-v1','live-v2','live-v3','live-v4','live-v5','prism-v1','prism-v2','weapon-bevel-v3','weapon-filament-v4','weapon-filament-v5'), '已有同名刀带且来源不明')
            tool('NiagaraToolsets.NiagaraToolset_System.RemoveEmitter',emitterRef={'system':ref(system),'emitterName':EMITTER})
        EDITOR.set_metadata_tag(system,'Pyrios.BladeVolume','')
        EDITOR.set_metadata_tag(system,'Pyrios.BladeTrailTaper','')
        add_live_blade(system, variants[style], end, variants if style == 'Crescent' else None)
        style_existing(system, variants[style], True)
        apply_blade_volume(system,EMITTER,field)
        finish(system)
    bp=ue.load_asset('/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo')
    fx=ue.get_default_object(bp.generated_class()).get_editor_property('combo_steps')[2].get_editor_property('fx')
    for unit in [fx,*list(fx.get_editor_property('system_units'))]:
        system=unit.get_editor_property('system')
        if not system:
            continue
        # Unit04 的末斩环使用金白掠光，其余实际刀弧使用蓝紫交叉斩材质。
        style = 'Crown' if '_Unit04_' in system.get_name() else 'Cross'
        styled = style_existing(system, variants[style], False)
        ground_or_sweep = refine_normal03(system, DAWN, tool, target, assign, weapon_frame)
        weapon_added = False
        if '_Unit00_' in system.get_name() and EDITOR.get_metadata_tag(system,'Pyrios.Normal03MultiCut') != CUT_VERSION:
            existing = {entry.emitter_name for entry in LIB.authoring_get_system_summary(system).emitters}
            for previous in ('Pyrios_FinisherBlade', EMITTER, FINISHER_BLADE, SCARS):
                if previous in existing:
                    require(EDITOR.get_metadata_tag(system,STAMP) in ('weapon-bevel-v3','weapon-filament-v4',SYSTEM_VERSION),'三段刀带来源不符 '+system.get_name())
                    tool('NiagaraToolsets.NiagaraToolset_System.RemoveEmitter',emitterRef={'system':ref(system),'emitterName':previous})
            for tag in ('Pyrios.BladeVolume','Pyrios.BladeTrailTaper','Pyrios.AftercutTravel','Pyrios.AftercutRefraction','Pyrios.CutLight','Pyrios.GroundBlueSweep','Pyrios.AftercutBrush'):
                EDITOR.set_metadata_tag(system,tag,'')
            add_live_blade(system, variants['Cross'], 0.84, combo_finisher=True)
            add_opening_marks(system, DAWN, cut_surface, tool, target, assign, module, weapon_frame)
            EDITOR.set_metadata_tag(system,'Pyrios.Normal03MultiCut',CUT_VERSION)
            weapon_added = True
        extended = '_Unit00_' in system.get_name() and extend_space_cuts(system, DAWN)
        volume = '_Unit00_' in system.get_name() and apply_blade_volume(system,FINISHER_BLADE,field)
        travel = '_Unit00_' in system.get_name() and animate_opening_marks(system)
        light = '_Unit00_' in system.get_name() and add_cut_light(system,tool,assign)
        wash = '_Unit00_' in system.get_name() and ground_sweep(system,DAWN,SCARS,tool,target,assign)
        brush = '_Unit00_' in system.get_name() and bind_cut_brushes(system)
        if brush or wash or light or travel or volume or extended or weapon_added or ground_or_sweep or styled:
            finish(system)
    # 兼容仍引用暖金笔触的资产。特殊技的逐层材质由 style_actions 配置。
    material(warm=True)
    ue.log('EMBERGLOW_COMPLETE')

if __name__=='__main__':
    build()
