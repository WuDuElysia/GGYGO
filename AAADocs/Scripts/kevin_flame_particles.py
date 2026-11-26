"""沿 Kevin 实际武器运动绘制火刀扫面和剥落的余烬。"""
import json

import unreal as ue

from zzz_fx_material_ue import configure_native_custom
from zzz_fx_niagara_ue import EMPTY_EMITTER, NiagaraBuilder


# Ribbon 的 V 横跨刀身，Age 来自每个历史姿态的实际年龄。不同刃带在不同时间烧断。
SWEEP_SHADER = """
float age=saturate(Particle.r);
float v=saturate(UV.y);
float t=age*1.12;
float n=Noise.r;
float warp=.055*sin(13*t+7*v+3*n)+.025*sin(31*t-9*v);
float crossBlade=saturate(v+warp*smoothstep(.025,.25,t));
float lip=.84+.025*sin(12*t+2*n);
float bright=exp(-abs(crossBlade-lip)*(47-12*t));
float thread=exp(-abs(crossBlade-(.70+.035*sin(18*t+4*n)))*84);
float innerLine=exp(-abs(crossBlade-.16-.033*sin(16*t))*70);
float fold=.5+.5*sin(30*crossBlade-8*t+4*n+2*sin(10*t+7*crossBlade));
float sheet=smoothstep(.09,.21,crossBlade)*(1-smoothstep(.82,.99,crossBlade));
float cooling=smoothstep(.025,.68,t);
float pockets=smoothstep(-.12,.12,fold+.43*n+1.1-2.35*t);
float tail=pow(saturate(1-age),1.55);
float opacity=(sheet*(.19+.44*fold)*pockets+bright*.98+thread*.58+innerLine*.29)*tail;
float3 red=float3(1.1,.035,.003);
float3 amber=float3(2.5,.49,.016);
float3 c=lerp(amber,red,saturate(.22+cooling*.83-.33*fold));
c+=bright*float3(3.8,2.5,.68)+thread*float3(1.5,.77,.18);
Coverage=saturate(opacity)*Particle.a;
return c;
"""

# 大片为内里透光、边缘卷曲的离刃火舌，小片为金白火星。二者都使用独立出生位置和速度。
EMBER_SHADER = """
float age=Particle.r, seed=Particle.g, plume=Particle.b;
float h=saturate(UV.y);
float2 p=UV*2-1;
float wind=sin(h*6.7+seed*17+age*2.8)*.31*h+sin(h*13-seed*11)*.10*h;
float dist=abs(p.x-wind);
float width=(.06+.75*pow(sin(3.14159*h),.76))*(1-.58*h);
float shell=width-dist+.16*(Noise.r-.5);
float rim=exp(-15*abs(shell-.09));
float cut=abs(p.x-wind*.63+.17*sin(h*9+seed*6+age*3))-.17*h;
float flame=smoothstep(-.045,.08,shell)*lerp(.27,1.,smoothstep(-.06,.065,cut+.12*(Noise.r-.45)));
float shard=saturate(1.-abs(p.x)*2.35-abs(p.y)*1.04);
float pointHeat=pow(shard,.65);
float3 cinder=lerp(float3(1.5,.12,.006),float3(4.4,2.83,.84),pointHeat*(1.-age*.72));
float3 curl=lerp(float3(1.09,.034,.003),float3(2.84,.62,.018),saturate(.28+rim*.80+.37*(1-h)-.55*age));
Coverage=lerp(smoothstep(0,.13,shard),flame,plume)*Particle.a;
return lerp(cinder,curl,plume);
"""


IGNITION_SHADER = """
float2 p=UV*2.-1.;
float radius=length(p);
float core=exp(-radius*radius*76.);
float crossX=pow(saturate(1.-abs(p.x)),2.3)*exp(-abs(p.y)*42.);
float crossY=pow(saturate(1.-abs(p.y)),3.7)*exp(-abs(p.x)*57.);
float corona=exp(-radius*6.)*(.8+.2*Noise.r);
float peak=saturate(core+crossX*.9+crossY*.7);
Coverage=saturate(peak+corona*.35)*Particle.a;
return lerp(float3(2.1,.25,.016),float3(5.8,3.8,1.2),peak);
"""


def particle_material(folder, name, shader_code):
    editor = ue.EditorAssetLibrary
    sweep = shader_code == SWEEP_SHADER
    path = folder+'/'+name
    if editor.does_asset_exist(path):
        return ue.load_asset(path)
    mat = ue.AssetToolsHelpers.get_asset_tools().create_asset(name,folder,ue.Material,ue.MaterialFactoryNew())
    edit = ue.MaterialEditingLibrary
    mat.set_editor_properties(dict(blend_mode=ue.BlendMode.BLEND_TRANSLUCENT,
        shading_model=ue.MaterialShadingModel.MSM_UNLIT, two_sided=True))
    mat.set_editor_property('used_with_niagara_ribbons' if sweep else 'used_with_niagara_sprites',True)
    uv = edit.create_material_expression(mat,ue.MaterialExpressionTextureCoordinate,-830,-140)
    color = edit.create_material_expression(mat,ue.MaterialExpressionParticleColor,-830,140)
    noise = edit.create_material_expression(mat,ue.MaterialExpressionTextureSample,-320,220)
    tex = ue.load_asset('/Game/Characters/Boss/Kevin/DemonBattle/Textures/noise_rough')
    if not tex:
        raise RuntimeError('缺少 Kevin 原噪声纹理')
    noise.set_editor_properties(dict(texture=tex,sampler_type=ue.MaterialSamplerType.SAMPLERTYPE_COLOR
                                    if tex.get_editor_property('srgb') else ue.MaterialSamplerType.SAMPLERTYPE_LINEAR_COLOR))
    coords = edit.create_material_expression(mat,ue.MaterialExpressionCustom,-590,50)
    shader = edit.create_material_expression(mat,ue.MaterialExpressionCustom,0,0)
    sync = lambda _,call:call()
    coord_code = ('return float2(UV.x*1.7+Particle.r*.84,UV.y*.76+Particle.r*.32);' if sweep else
                  'return UV*float2(.67,.92)+float2(Particle.g*2.7,Particle.g-Particle.r*.71);')
    configure_native_custom(ue,coords,['UV','Particle'],coord_code,'CMOT_Float2','随余温流动的噪声',native_sync=sync)
    configure_native_custom(ue,shader,['UV','Particle','Noise'],shader_code,
        'CMOT_Float3',name,native_sync=sync,additional_outputs=[('Coverage','CMOT_Float1')])
    for dest in (coords,shader):
        if not edit.connect_material_expressions(uv,'',dest,'UV') or not edit.connect_material_expressions(color,'RGBA',dest,'Particle'):
            raise RuntimeError('火刃粒子输入失败 '+name)
    if not (edit.connect_material_expressions(coords,'',noise,'Coordinates') and
            edit.connect_material_expressions(noise,'RGB',shader,'Noise') and
            edit.connect_material_property(shader,'',ue.MaterialProperty.MP_EMISSIVE_COLOR) and
            edit.connect_material_property(shader,'Coverage',ue.MaterialProperty.MP_OPACITY)):
        raise RuntimeError('火刃粒子材质接线失败 '+name)
    if edit.recompile_material(mat) or not editor.save_loaded_asset(mat,False):
        raise RuntimeError('火刃粒子材质制作失败 '+name)
    return mat


def build_sweep_and_embers(system,folder,module,assign,tool):
    lib = ue.GGYGONiagaraCompileLibrary
    eu,ps,pu = 'EmitterUpdateScript','ParticleSpawnScript','ParticleUpdateScript'
    def ok(result):
        if not result.succeeded:
            raise RuntimeError(result.error)

    def emitter(name, local=False):
        ok(lib.authoring_add_emitter(system,ue.load_asset(EMPTY_EMITTER),name))
        ok(lib.authoring_set_emitter_data(system,name,json.dumps({'bLocalSpace':local,'CalculateBoundsMode':'Dynamic'})))
        return module(eu,'/Niagara/Modules/Emitter/EmitterState',emitter=name,**{
            'Life Cycle Mode':NiagaraBuilder.enum('/Niagara/Enums/ENiagaraEmitterLifeCycleMode.ENiagaraEmitterLifeCycleMode','NewEnumerator1','Self'),
            'Loop Behavior':NiagaraBuilder.enum('/Niagara/Enums/ENiagara_EmitterStateOptions.ENiagara_EmitterStateOptions','NewEnumerator1','Once'),
            'Loop Duration':NiagaraBuilder.num('Float',1.25)})

    def finish(name,work,renderer_type,props):
        result = tool('GGYGOEditor.GGYGONiagaraCompileLibrary','ApplyAuthoringStackBatch',
                      system={'refPath':system.get_path_name()},workItems=work)
        if not result.get('bApplied'):
            raise RuntimeError(name+' '+result.get('error','粒子编译栈写入失败'))
        renderer = lib.authoring_add_renderer(system,name,ue.load_class(None,'/Script/Niagara.'+renderer_type))
        ok(renderer)
        ok(lib.authoring_set_renderer_data(system,name,renderer.renderer_index,json.dumps(props)))

    bind = NiagaraBuilder.attribute_binding
    axis = 'normalize(Engine.Owner.SystemZAxis)'
    width = '158.0*abs(Engine.Owner.Scale.z)'
    name = 'SwordSweep'
    trail = particle_material(folder,'M_Kevin_SweptFlame',SWEEP_SHADER)
    work = [emitter(name),
            module(eu,'/Niagara/Modules/Emitter/SpawnPerFrame',emitter=name,**{'Spawn Count':NiagaraBuilder.num('Int32',1)}),
            assign(ps,emitter=name,Lifetime=('Float','.165'),Position=('Position','Engine.Owner.Position - '+axis+' * ('+width+')*.48'),
                   RibbonFacing=('Vector','-'+axis),RibbonWidth=('Float',width),Color=('LinearColor','float4(0,0,0,1)')),
            module(pu,'/Niagara/Modules/Update/Lifetime/ParticleState',emitter=name),
            assign(pu,emitter=name,Color=('LinearColor','float4(Particles.NormalizedAge,0,0,1)'))]
    finish(name,work,'NiagaraRibbonRendererProperties',dict(Material=trail.get_path_name(),Shape='Plane',
        FacingMode='CustomSideVector',TessellationMode='Automatic',MaxNumRibbons=1,bUseGPUInit=False,
        PositionBinding=bind('Particles.Position'),RibbonWidthBinding=bind('Particles.RibbonWidth'),
        RibbonFacingBinding=bind('Particles.RibbonFacing'),ColorBinding=bind('Particles.Color')))

    name = 'BladeEmbers'
    embers = particle_material(folder,'M_Kevin_SheddingEmbers',EMBER_SHADER)
    # 出生时锁定真实刀尖、刀轴和切向速度。短焰和细火星独自在场景运动，不跟着下一帧武器瞬移。
    seed = 'frac(sin((Particles.UniqueID+1.0)*'
    work = [emitter(name),module(eu,'/Niagara/Modules/Emitter/SpawnRate',emitter=name,SpawnRate=NiagaraBuilder.num('Float',112)),
            assign(ps,emitter=name,EmberSeed=('Float',seed+'73.31)*3471.81)'),
                   EdgeSample=('Float',seed+'41.47)*6172.19)'),EmberLane=('Float',seed+'13.27)*8341.17)')),
            assign(ps,emitter=name,IsFlame=('Bool','Particles.EmberSeed>.71'),
                   Birth=('Position','Engine.Owner.Position - '+axis+'*(10+Particles.EdgeSample*132)*abs(Engine.Owner.Scale.z) + Engine.Owner.SystemXAxis*(Particles.EmberLane>.48 ? 1.0 : -1.0)*(3+11*Particles.EdgeSample)*abs(Engine.Owner.Scale.x)'),
                   Velocity=('Vector','Engine.Owner.Velocity*min(.13,190./max(length(Engine.Owner.Velocity),1.)) + Engine.Owner.SystemXAxis*(Particles.EmberLane-.5)*175. + Engine.Owner.SystemYAxis*(Particles.EdgeSample-.5)*91. + float3(0,0,30+Particles.EmberSeed*88)')),
            assign(ps,emitter=name,Lifetime=('Float','.105+.17*Particles.EmberLane+.06*(Particles.IsFlame ? 1. : 0.)'),
                   Position=('Position','Particles.Birth'),
                   EmberSize=('Vector2','(Particles.IsFlame ? float2(15,35) : float2(3.3,15))*(.65+.83*Particles.EdgeSample)*abs(Engine.Owner.Scale.z)')),
            assign(ps,emitter=name,SpriteSize=('Vector2','Particles.EmberSize'),
                   Color=('LinearColor','float4(0,Particles.EmberLane,Particles.IsFlame ? 1 : 0,.85)')),
            module(pu,'/Niagara/Modules/Update/Lifetime/ParticleState',emitter=name),
            assign(pu,emitter=name,Position=('Position','Particles.Birth+Particles.Velocity*(1.-exp(-4.*Particles.Age))*.25+float3(0,0,105.*Particles.Age*Particles.Age)'),
                   SpriteSize=('Vector2','Particles.EmberSize*(.37+.63*(1.-Particles.NormalizedAge))'),
                   Color=('LinearColor','float4(Particles.NormalizedAge,Particles.EmberLane,Particles.IsFlame ? 1 : 0,pow(saturate(1.-Particles.NormalizedAge),.88))'))]
    finish(name,work,'NiagaraSpriteRendererProperties',dict(Material=embers.get_path_name(),Alignment='VelocityAligned',
        FacingMode='FaceCamera',PositionBinding=bind('Particles.Position'),VelocityBinding=bind('Particles.Velocity'),
        SpriteSizeBinding=bind('Particles.SpriteSize'),ColorBinding=bind('Particles.Color')))

    # 起火瞬间的刃尖闪点随刀运动，约十分之一秒消退。只在窗口开启时产生一次。
    name = 'EdgeIgnition'
    ignition = particle_material(folder,'M_Kevin_EdgeIgnition',IGNITION_SHADER)
    work = [emitter(name,local=True),
            module(eu,'/Niagara/Modules/Emitter/SpawnBurst_Instantaneous',emitter=name,**{
                'Spawn Count':NiagaraBuilder.num('Int32',1),'Spawn Time':NiagaraBuilder.num('Float',0)}),
            assign(ps,emitter=name,Lifetime=('Float','.115'),Position=('Position','float3(0,0,-10)'),
                   SpriteSize=('Vector2','float2(103,65)'),SpriteRotation=('Float','-18.'),
                   Color=('LinearColor','float4(0,0,0,.8)')),
            module(pu,'/Niagara/Modules/Update/Lifetime/ParticleState',emitter=name),
            assign(pu,emitter=name,SpriteSize=('Vector2','float2(103,65)*(.78+.22*Particles.NormalizedAge)'),
                   Color=('LinearColor','float4(Particles.NormalizedAge,0,0,pow(1.-saturate(Particles.NormalizedAge),1.6))'))]
    finish(name,work,'NiagaraSpriteRendererProperties',dict(Material=ignition.get_path_name(),Alignment='Unaligned',
        FacingMode='FaceCamera',PositionBinding=bind('Particles.Position'),SpriteRotationBinding=bind('Particles.SpriteRotation'),
        SpriteSizeBinding=bind('Particles.SpriteSize'),ColorBinding=bind('Particles.Color')))
