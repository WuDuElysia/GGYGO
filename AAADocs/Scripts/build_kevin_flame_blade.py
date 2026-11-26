"""Kevin 火刃制作入口。运行于项目 Editor，仅保存火刃及实际使用它的能力蓝图。"""
import json
import math
import sys
from pathlib import Path

import unreal as ue

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wire_kevin_boss_abilities as abilities
from kevin_flame_particles import build_sweep_and_embers
from kevin_flame_preparation import install as install_preparation
from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import DEFAULT_SYSTEM, EMPTY_EMITTER, NS, TYPES, NiagaraBuilder

EDITOR = ue.EditorAssetLibrary
LIB = ue.GGYGONiagaraCompileLibrary
FX = abilities.read_json(abilities.ROOT / abilities.read_json(abilities.CONFIG)['fx_config'])
BLADE = FX['blade_flame']
FOLDER, SYSTEM_NAME = BLADE['system'].rsplit('/', 1)
EMITTER = 'BurningBlade'
TEXTURES = '/Game/Characters/Boss/Kevin/DemonBattle/Textures/'
# 武器骨本地 Z、半刃宽和半厚，单位 cm。护手上方起火。
SECTIONS = [(17, 17, 3), (28, 24, 5), (45, 25.4, 5.8), (62, 21, 5.3), (85, 16, 3),
            (100, 14, 3.4), (124, 11.7, 2.3), (150, 10.5, 1.8), (166, 10, 1.7),
            (177, 7, 1), (183.104, .2, .2)]

SHADE = """
float side=step(1.5,UV.x), u=UV.x-2.0*side, v=UV.y;
float phase=Age*7.1+side*2.74;
float folded=u-.39*v*v+.040*sin(11*u-phase+5*v)+.041*(Fine.g-.5);
float wave=.5+.5*sin(25*folded-phase+2.9*Coarse.r);
float wave2=.5+.5*sin(47*folded-phase*1.42+2*Fine.g);
float reach=.255+(.16+.18*side)*wave*wave+.09*wave2;
float cap=smoothstep(0,.075,u)*(1-smoothstep(.978,1,u));
float inside=smoothstep(-.019,.035,reach-v);
float rim=exp(-abs(v-.25)*47);
float filament=pow(wave,5)*smoothstep(.21,.32,v)*inside;
float gap=smoothstep(.08,.48,wave2+.24*(Coarse.r-.5));
float foil=.27+.73*smoothstep(.07,.24,v);
float ivory=rim*(.75+.25*Fine.r);
float3 colour=lerp(float3(.86,.027,.004),float3(2.1,.43,.017),saturate(.25+.78*wave-.6*v));
colour=lerp(colour,float3(3.8,2.02,.46),ivory)+filament*float3(.65,.17,.015);
Coverage=cap*Ignition*inside*foil*lerp(.52+.32*Blade.r,gap,smoothstep(.22,.48,v));
return colour;
"""


def need(value, message):
    if not value:
        raise RuntimeError(message)
    return value


def save(obj):
    need(EDITOR.save_loaded_asset(obj, False), '保存失败 '+obj.get_path_name())
    return obj


def material():
    name = 'M_Kevin_BladeFire'
    path = FOLDER+'/'+name
    if EDITOR.does_asset_exist(path):
        mat=ue.load_asset(path)
        if EDITOR.get_metadata_tag(mat,'Kevin.BladeSurface')=='tempered-edge':
            return mat
        ue.MaterialEditingLibrary.delete_all_material_expressions(mat)
    else:
        mat=ue.AssetToolsHelpers.get_asset_tools().create_asset(name,FOLDER,ue.Material,ue.MaterialFactoryNew())
    mat.set_editor_properties(dict(blend_mode=ue.BlendMode.BLEND_TRANSLUCENT,
        shading_model=ue.MaterialShadingModel.MSM_UNLIT,two_sided=True,used_with_niagara_mesh_particles=True))
    edit = ue.MaterialEditingLibrary

    def expr(cls,x,y):
        return edit.create_material_expression(mat,cls,x,y)

    def join(src,pin,dst,field):
        need(edit.connect_material_expressions(src,pin,dst,field),'材质接线失败 '+field)

    uv = expr(ue.MaterialExpressionTextureCoordinate,-980,-100)
    age = expr(ue.MaterialExpressionParticleColor,-980,180)
    shader = expr(ue.MaterialExpressionCustom,0,0)
    configure_native_custom(ue,shader,['UV','Coarse','Fine','Blade','Age','Ignition'],SHADE,'CMOT_Float3',
        '沿刃流焰、焰尖及金白刃芯',native_sync=lambda _,call:call(),additional_outputs=[('Coverage','CMOT_Float1')])
    join(uv,'',shader,'UV')
    join(age,'R',shader,'Age')
    join(age,'A',shader,'Ignition')
    for index,(pin,tex,coords) in enumerate((
        ('Coarse','noise_rough','return float2(2.4*UV.x+.30*UV.y-Age*.81, .73*UV.y+.39*UV.x-Age*.36);'),
        ('Fine','noise_rough','return float2(6.6*UV.x-.42*UV.y-Age*1.83,2.2*UV.y-Age*.93);'),
        ('Blade','Monster_Boss_411_Texture_Weapon_Color','return float2(.53+.22*(UV.x-2*step(1.5,UV.x)),.94+.025*UV.y);'))):
        p = expr(ue.MaterialExpressionCustom,-660,100+index*190)
        configure_native_custom(ue,p,['UV','Age'],coords,'CMOT_Float2',pin+' 纹理坐标',native_sync=lambda _,call:call())
        join(uv,'',p,'UV')
        join(age,'R',p,'Age')
        texture = need(ue.load_asset(TEXTURES+tex),'缺原纹理 '+tex)
        sampler = ue.MaterialSamplerType.SAMPLERTYPE_COLOR if texture.get_editor_property('srgb') else ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR
        sample = expr(ue.MaterialExpressionTextureSample,-350,100+index*190)
        sample.set_editor_properties(dict(texture=texture,sampler_type=sampler))
        join(p,'',sample,'Coordinates')
        join(sample,'RGBA',shader,pin)
    need(edit.connect_material_property(shader,'',ue.MaterialProperty.MP_EMISSIVE_COLOR) and
         edit.connect_material_property(shader,'Coverage',ue.MaterialProperty.MP_OPACITY),'火刃材质输出失败')
    need(not edit.recompile_material(mat),'火刃材质编译失败')
    EDITOR.set_metadata_tag(mat,'Kevin.BladeSurface','tempered-edge')
    return save(mat)


def mesh():
    path = FOLDER+'/SM_Kevin_BladeFire'
    existing=ue.load_asset(path) if EDITOR.does_asset_exist(path) else None
    if existing and EDITOR.get_metadata_tag(existing,'Kevin.BladeUV')=='two-edges':
        return existing
    vertices,uvs,triangles = [],[],[]
    # 以刀尖挂点为原点。四面在刃脊相接，外沿逐渐变薄并顺刀尖偏移。
    for xsign in (-1,1):
        for ysign in (-1,1):
            start = len(vertices)
            for z,width,depth in SECTIONS:
                u = (z-SECTIONS[0][0])/(SECTIONS[-1][0]-SECTIONS[0][0])
                taper = math.sin(math.pi*u)**.57
                for v in (0,.25,.55,1):
                    x = width*(v/.25) if v<=.25 else width+(v-.25)/.75*(6+43*taper)
                    y = depth+1.8+4*math.sin(math.pi*v)*taper
                    vertices.append(ue.Vector(xsign*x,ysign*y,z-SECTIONS[-1][0]+v*(4+27*taper)))
                    uvs.append(ue.Vector2D(u+(2 if xsign>0 else 0),v))
            for j in range(len(SECTIONS)-1):
                for k in range(3):
                    a=start+4*j+k
                    triangles.extend((ue.IntVector(a,a+4,a+5),ue.IntVector(a,a+5,a+1)))
    dyn=ue.DynamicMesh()
    ue.GeometryScript_MeshEdits.append_buffers_to_mesh(dyn,ue.GeometryScriptSimpleMeshBuffers(
        vertices=vertices,uv0=uvs,triangles=triangles))
    opts=ue.GeometryScriptCreateNewStaticMeshAssetOptions(enable_recompute_normals=True,enable_recompute_tangents=True,
                                                         enable_nanite=False,enable_collision=False)
    if existing:
        asset=existing
        _,result=ue.GeometryScript_AssetUtils.copy_mesh_to_static_mesh(dyn,asset,
            ue.GeometryScriptCopyMeshToAssetOptions(),ue.GeometryScriptMeshWriteLOD(lod_index=0),False)
    else:
        asset,result=ue.GeometryScript_NewAssetUtils.create_new_static_mesh_asset_from_mesh(dyn,path,opts)
    need(result==ue.GeometryScriptOutcomePins.SUCCESS and asset,'刀身火焰网格生成失败')
    EDITOR.set_metadata_tag(asset,'Kevin.BladeUV','two-edges')
    return save(asset)


def tool(group,name,**args):
    result=ue.ToolsetRegistry.execute_tool(group,name,json.dumps(args))
    need(result.is_complete and not result.error,name+' '+str(result.error))
    return json.loads(result.value or '{}').get('returnValue')


def system(mat,blade):
    ns=NS.rstrip('.')
    if EDITOR.does_asset_exist(BLADE['system']):
        obj=ue.load_asset(BLADE['system'])
        version=EDITOR.get_metadata_tag(obj,'Kevin.FlameBlade')
        if version=='swept-fire-ignition':
            return obj
        need(version in ('1','socket-release','swept-fire'),'已有未识别的火刃系统')
    else:
        tool(ns,'CreateNiagaraSystem',assetName=SYSTEM_NAME,assetPath=FOLDER,templateSystem={'refPath':DEFAULT_SYSTEM})
        obj=need(ue.load_asset(BLADE['system']),'未创建火刃系统')
    ref={'refPath':obj.get_path_name()}
    for old in tool(ns,'GetSystemSummary',system=ref)['emitters']:
        tool(ns,'RemoveEmitter',emitterRef={'system':ref,'emitterName':old['emitterName'],'rendererIndex':-1})
    def check(result):
        need(result.succeeded,result.error)
    check(LIB.authoring_add_emitter(obj,ue.load_asset(EMPTY_EMITTER),EMITTER))
    check(LIB.authoring_set_emitter_data(obj,EMITTER,json.dumps({'bLocalSpace':True,'CalculateBoundsMode':'Dynamic'})))
    eu,ps,pu='EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript'

    def module(script,path,*,emitter=EMITTER,**inputs):
        return dict(kind='Module',emitterName=emitter,scriptName=script,
            moduleAsset={'refPath':path+'.'+path.rsplit('/',1)[1]},
            inputs=[dict(namePath=[key],inputData=val) for key,val in inputs.items()])

    def assign(script,*,emitter=EMITTER,**values):
        return dict(kind='Assignments',emitterName=emitter,scriptName=script,
            assignments=[dict(name='Particles.'+key,type={'classStructOrEnum':{'refPath':TYPES[kind]}},
                hlslExpression=val) for key,(kind,val) in values.items()])

    num,enum=NiagaraBuilder.num,NiagaraBuilder.enum
    work=[module(eu,'/Niagara/Modules/Emitter/EmitterState',**{
          'Life Cycle Mode':enum('/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode','NewEnumerator1','Self'),
          'Loop Behavior':enum('/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions','NewEnumerator1','Once'),
          'Loop Duration':num('Float',1.25)}),
          module(eu,'/Niagara/Modules/Emitter/SpawnBurst_Instantaneous',**{'Spawn Count':num('Int32',1),'Spawn Time':num('Float',0)}),
          assign(ps,Lifetime=('Float','1.25'),Position=('Position','float3(0,0,0)'),Scale=('Vector','float3(1,1,1)'),
                 MeshOrientation=('Quat','float4(0,0,0,1)'),Color=('LinearColor','float4(0,1,1,.24)')),
          module(pu,'/Niagara/Modules/Update/Lifetime/ParticleState'),
          assign(pu,Color=('LinearColor','float4(Particles.Age,1,1,saturate(.24+Particles.Age*30))'),
                    Alive=('Bool','Particles.Alive && Engine.Owner.ExecutionState==0'))]
    result=tool('GGYGOEditor.GGYGONiagaraCompileLibrary','ApplyAuthoringStackBatch',system=ref,workItems=work)
    need(result['bApplied'],result.get('error','火刃 Niagara Stack 失败'))
    renderer=LIB.authoring_add_renderer(obj,EMITTER,ue.load_class(None,'/Script/Niagara.NiagaraMeshRendererProperties'))
    check(renderer)
    bind=NiagaraBuilder.attribute_binding
    for props in ({'bOverrideMaterials':True},dict(Meshes=[dict(Mesh=blade.get_path_name())],
            OverrideMaterials=[dict(ExplicitMat=mat.get_path_name())],PositionBinding=bind('Particles.Position'),
            ScaleBinding=bind('Particles.Scale'),MeshOrientationBinding=bind('Particles.MeshOrientation'),ColorBinding=bind('Particles.Color'))):
        check(LIB.authoring_set_renderer_data(obj,EMITTER,renderer.renderer_index,json.dumps(props)))
    build_sweep_and_embers(obj,FOLDER,module,assign,tool)
    state=LIB.force_compile(obj)
    need(state.native_ready and state.system_valid,'火刃 Niagara 编译失败 '+LIB.read_system_compile_diagnostics(obj).export_text())
    EDITOR.set_metadata_tag(obj,'Kevin.FlameBlade','swept-fire-ignition')
    return save(obj)


def wire(read_only=False):
    cfg=abilities.read_json(abilities.CONFIG)
    plan=abilities._fx_plan(cfg)
    source={a['action_id']:{p['begin_event_tag']:p['effect'] for p in a['phases'] if p['effect'] in BLADE['effects']}
            for a in FX['actions']}
    for spec in cfg['abilities']:
        tags=source.get(spec['animation_id'])
        if not tags:
            continue
        bp=ue.load_asset(abilities.package(spec['ability']))
        cdo=ue.get_default_object(bp.generated_class())
        windows=list(cdo.get_editor_property('MontageFXWindows'))
        changed=False
        found=set()
        for i,window in enumerate(windows):
            key=window.get_editor_property('BeginEventTag')
            tagname=str(key.get_editor_property('TagName'))
            if tagname not in tags:
                continue
            authored=next(w for w in plan['action_windows'] if w['begin_event_tag']==tagname)
            expected=[u['system'] for u in authored['system_units']]
            units=list(window.get_editor_property('SystemUnits'))
            paths=[u.get_editor_property('System').get_path_name().split('.')[0] for u in units]
            original={'system':plan['systems'][tags[tagname]]['package'],'field_settings':{'mode':'NoCustomField'}}
            legacy=[original['system'],BLADE['system']]
            need(paths in (expected,legacy,legacy[:1]) and str(window.get_editor_property('SocketName'))==BLADE['socket'],
                 '现有火招窗口配置有冲突 '+tagname)
            target=abilities.playback_value(ue,authored,ue.load_asset)
            if window.export_text()!=target.export_text():
                need(not read_only,'冷载时火刃窗口不一致 '+tagname)
                old_units=[original,authored['system_units'][-1]][:len(paths)]
                before={**authored,'system_units':old_units,'normal_stop_mode':(
                    BLADE['normal_stop_mode'] if len(paths)==2 else FX['effects'][tags[tagname]]['normal_stop'])}
                need(window.export_text()==abilities.playback_value(ue,before,ue.load_asset).export_text(),
                     '现有窗口参数与配方不匹配 '+tagname)
                windows[i]=target
                changed=True
            found.add(tagname)
        need(found==set(tags),'GA 缺少动作窗口 '+spec['key'])
        if changed:
            bp.modify()
            cdo.set_editor_property('MontageFXWindows',windows)
            ue.BlueprintEditorLibrary.compile_blueprint(bp)
            need(bp.get_editor_property('Status')==ue.BlueprintStatus.BS_UP_TO_DATE,'GA 编译失败 '+spec['key'])
            save(bp)
        ue.log('KEVIN_FIRE_WINDOWS '+spec['key']+' '+str(len(found)))


def build_assets():
    """重建工程时先制作可视化资产，GA 作者配方随后会引用返回的系统。"""
    EDITOR.make_directory(FOLDER)
    return system(material(),mesh())


def build():
    flame=build_assets()
    wire()
    install_preparation(FOLDER,flame)
    ue.log('KEVIN_FIRE_READY '+flame.get_path_name())


if __name__=='__main__':
    build()
