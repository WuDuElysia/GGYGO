"""在独立 UE 编辑器制作佩洛伊斯的刀光、接触星屑和急转姿态。在包含原角色素材的工程运行。"""
import json
import math
import shutil
import sys
from pathlib import Path
import unreal as ue

ROOT = '/Game/Characters/Player/Pyrios'
LOOK = ROOT + '/FX/Dawn'
LIB = ue.GGYGONiagaraCompileLibrary
EDIT = ue.MaterialEditingLibrary
ASSETS = ue.EditorAssetLibrary
sys.path.insert(0, str(Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_dir()))/'AAADocs/Scripts'))
from zzz_fx_material_ue import configure_native_custom

# u 为刀弧走向，v 为刃宽。分出近白刃芯、琥珀亮面与溶开的朱红尾丝。
BLADE = """
float u = saturate(UV.x), v = saturate(UV.y);
float taper = pow(saturate(4*u*(1-u)),0.65);
float axis = 0.46 + 0.115*sin(3.14159*u) + 0.035*sin(7*u);
float d = (v-axis) / max(0.08,taper);
float core = exp2(-abs(d)*85);
float amber = exp2(-abs(d+0.026)*27);
float wake = exp2(-abs(d+0.105)*12)*smoothstep(-0.03,0.20,-d);
float flutes = 0.44 + 0.56*pow(abs(sin(55*d+8*u+1.6*sin(14*u))),3);
float tips = smoothstep(0.005,0.14,u)*(1-smoothstep(0.81,0.998,u));
return tips*taper*(float3(5.2,4.25,2.9)*core + float3(2.0,0.62,0.11)*amber + float3(1.05,0.07,0.019)*wake*flutes);
"""
GLINT = """
float2 p=UV*2-1;
float body=length(p*float2(0.97,1.2));
float ray1=exp2(-52*abs(p.y))*pow(saturate(1-abs(p.x)),2.3);
float ray2=exp2(-66*abs(p.x+0.24*p.y))*pow(saturate(1-abs(p.y)),3.0);
float chip=pow(saturate(1-abs(p.x)*3.0-abs(p.y)*5.0),2.7);
return (float3(4.6,3.5,1.9)*chip + float3(2.0,0.72,0.12)*(ray1+0.72*ray2))*(1-smoothstep(0.86,1,body));
"""
WAKE = """
float2 p=UV*2-1;
float t=saturate(0.5+0.5*p.x);
float envelope=pow(saturate(4*t*(1-t)),0.85);
float c=0.11*sin(4.8*t)-0.14*t;
float width=max(0.025,0.19*envelope);
float f=exp2(-3.8*abs((p.y-c)/width));
float echo=0.34*exp2(-4.9*abs((p.y-c-0.12-0.05*t)/width));
return envelope*(float3(1.55,0.66,0.27)*f+float3(0.65,0.16,0.09)*echo);
"""
def material(name, code):
    path=LOOK+'/M_Pyrios_'+name
    if ASSETS.does_asset_exist(path):
        asset = ue.load_asset(path)
        if not isinstance(asset, ue.Material):
            raise ValueError('同名资源不是材质 '+path)
        return asset
    mat=ue.AssetToolsHelpers.get_asset_tools().create_asset(path.rsplit('/',1)[1],LOOK,ue.Material,ue.MaterialFactoryNew())
    if not mat:
        raise RuntimeError('材质创建失败 '+path)
    mat.set_editor_properties(dict(blend_mode=ue.BlendMode.BLEND_ADDITIVE,shading_model=ue.MaterialShadingModel.MSM_UNLIT,
        two_sided=True,used_with_niagara_sprites=True,used_with_niagara_mesh_particles=True,used_with_niagara_ribbons=True))
    uv=EDIT.create_material_expression(mat,ue.MaterialExpressionTextureCoordinate,-620,0)
    shape=EDIT.create_material_expression(mat,ue.MaterialExpressionCustom,-300,0)
    configure_native_custom(ue,shape,['UV'],code,'CMOT_Float3',name,native_sync=lambda _,fn:fn())
    particles=EDIT.create_material_expression(mat,ue.MaterialExpressionParticleColor,-300,180)
    if not (EDIT.connect_material_expressions(uv,'',shape,'UV') and EDIT.connect_material_property(shape,'',ue.MaterialProperty.MP_EMISSIVE_COLOR) and EDIT.connect_material_property(particles,'A',ue.MaterialProperty.MP_OPACITY)):
        raise RuntimeError('材质接线失败 '+path)
    errors=EDIT.recompile_material(mat)
    if errors or not ASSETS.save_loaded_asset(mat):
        raise RuntimeError('材质编译或保存失败 '+str(errors))
    return mat

def classify(system,name):
    from pyrios_source_slashes import SOURCE_SURFACES
    if name in SOURCE_SURFACES.get(system.rsplit('/', 1)[-1], {}):
        return None
    key=name.lower()
    if 'Evade_' in system:
        if 'world_root' in key or 'smoke_trail' in key or 'smoke_an' in key:
            return 'Slipstream'
        if 'glow' in key:
            return 'Glint'
    elif any(k in key for k in ('highlight','light_edge','trail_main_star','weapontrailcustom')):
        return 'Blade'
    elif any(k in key for k in ('shining','flare01_line','dots01')):
        return 'Glint'
    return None

def systems():
    paths=set()
    for bp_path in ASSETS.list_assets(ROOT+'/Abilities',False,False):
        if 'GA_Pyrios_Attack_' not in bp_path:
            continue
        bp=ue.load_asset(bp_path)
        cdo=ue.get_default_object(bp.generated_class())
        if not isinstance(cdo,ue.GGYGOPlayerComboAbility):
            continue
        for step in cdo.get_editor_property('combo_steps'):
            fx=step.get_editor_property('fx')
            for unit in [fx,*list(fx.get_editor_property('system_units'))]:
                obj=unit.get_editor_property('system')
                if obj and obj.get_path_name().startswith(ROOT+'/FX/'): paths.add(obj.get_path_name().split('.')[0])
    for path in ASSETS.list_assets(ROOT+'/FX/Skill',False,False):
        if '/NS_UEEquivalent_Eff_Pyrois_Evade_' in path: paths.add(path.split('.')[0])
    return sorted(paths)

# 从原技能系统的同名渲染层读回。四段强化斩有各自的亮边，复用发射器名也要分别配置。
SKILL_SURFACES = {
    'NS_Pyrios_Special_Phased_Pyrios_Special_MainComposition_8279ab1ed40b_Unit00_ecf18f56cb44': {
        'M00_root_rot__1__HighLight_UEFX': 'MI_Eff_Objects_LKJ_GUID6cfcb6781f63a704fb97670a8c8a781a_8aeb989a7f97',
        'M00_root_rot__1__light_edge_UEFX': 'MI_Eff_Objects_LKJ_GUID93bbcefa9a0c9544d80a4a5a1b9c3fd6_586ffa00867e',
        'M00_root_rot__1__Shining_UEFX': 'MI_Eff_Objects_LKJ_GUID5b0312e87ded4644ca3051a1169e3fef_3fcc6f2064ed',
        'M01_root__1__rot__1__HighLight_UEFX': 'MI_Eff_Objects_LKJ_GUID6cfcb6781f63a704fb97670a8c8a781a_8aeb989a7f97',
        'M01_root__1__rot__1__light_edge_UEFX': 'MI_Eff_Objects_LKJ_GUID93bbcefa9a0c9544d80a4a5a1b9c3fd6_586ffa00867e',
        'M01_root__1__rot__1__Shining_UEFX': 'MI_Eff_Objects_LKJ_GUID5b0312e87ded4644ca3051a1169e3fef_3fcc6f2064ed',
        'M02_Trail_Main_002_Trail_Main_1_Trail_Main_star__1__UEFX': 'MI_Eff_Others_LZL_GUID5106122fc00cea348b084666824c6cb7_3e5d554acbd3',
        'M02_Trail_Main_002_Trail_Main_1_Trail_Main_star_UEFX': 'MI_Eff_Others_LZL_GUIDfcc275f4a300e164c959339b925745fa_cef55e7bfa75',
        'M02_Trail_Main_002_Trail_Main_1_Dots01_UEFX': 'MI_Eff_Others_ZZY_GUID00ba1247b1265a8449aa2c06138d9ec4_d75f833c273e',
        'M02_Trail_Main_002_Trail_Main_1_Trail_Main_star__2__UEFX': 'MI_Eff_Objects_LZL_GUIDded4aed73fe68d745acb8d492018a331_378632bd8591',
        'M03_X_WeaponTrailCustom_UEFX': 'MI_Eff_Others_LZL_GUIDddcf648f778786c43af60e1563e62140_b4b286895981',
    },
    'NS_Pyrios_ExSpecial_Phased_Pyrios_ExSpecial_MainComposition_c8e2e209220c_Unit00_3763cbd79b38': {
        'M00_root__1__root_MeleeTrail_andi_main_HighLight_main_UEFX': 'MI_Eff_Objects_LKJ_GUID088cf883ac8e06548bcd087a399ad3ce_8203a11cb384',
        'M00_root__1__root_MeleeTrail_andi_main_light_edge_UEFX': 'MI_Eff_Objects_LKJ_GUID42fc5bdfe3322b249b59a841bdbfc20a_a9112f9991b0',
        'M00_root__1__root_MeleeTrail_andi_main_Shining__1__UEFX': 'MI_Eff_Objects_LKJ_GUIDb09523a4a3293a94db98dda6c0bd4c2d_c54720cefb00',
    },
    'NS_Pyrios_ExSpecial_Phased_Pyrios_ExSpecial_MainComposition_c8e2e209220c_Unit01_7e685b5f5d78': {
        'M01_root__1__root_MeleeTrail_andi_main_HighLight_main_UEFX': 'MI_Eff_Objects_LKJ_GUID088cf883ac8e06548bcd087a399ad3ce_c2440d4ecc4f',
        'M01_root__1__root_MeleeTrail_andi_main_light_edge_UEFX': 'MI_Eff_Objects_LKJ_GUID42fc5bdfe3322b249b59a841bdbfc20a_9f27fea4f5fc',
        'M01_root__1__root_MeleeTrail_andi_main_Shining__1__UEFX': 'MI_Eff_Objects_LKJ_GUIDb09523a4a3293a94db98dda6c0bd4c2d_0eb6ec393b3b',
    },
    'NS_Pyrios_ExSpecial_Phased_Eff_Pyrois_Attack_ExSpecial_01_01_Trail_6e542cde2b42': {
        'root_Trail_rot_HighLight_UEFX': 'MI_Eff_Objects_LKJ_GUIDd169a75fdf987b64fbc9f5d996567768_4c24dc96d60d',
        'root_Trail_rot_light_edge_UEFX': 'MI_Eff_Objects_LKJ_GUID79ffe342eefaa2d46a5654b23731b7fd_b43385293147',
        'root_Trail_rot_Shining_UEFX': 'MI_Eff_Objects_LKJ_GUID5b0312e87ded4644ca3051a1169e3fef_e66a17bf2d62',
    },
    'NS_Pyrios_ExSpecial_Phased_Eff_Pyrois_Attack_ExSpecial_01_02_Trail_0f4d5adb982e': {
        'root_Trail_rot_HighLight_UEFX': 'MI_Eff_Objects_LKJ_GUIDd169a75fdf987b64fbc9f5d996567768_4c24dc96d60d',
        'root_Trail_rot_light_edge_UEFX': 'MI_Eff_Objects_LZL_GUID1e1e675fa82520b4c8f4324f8d2c8a4a_f008dfa10860',
        'root_Trail_rot_Shining_UEFX': 'MI_Eff_Objects_LKJ_GUID5b0312e87ded4644ca3051a1169e3fef_e66a17bf2d62',
    },
    'NS_Pyrios_ExSpecial_Phased_Eff_Pyrois_Attack_ExSpecial_01_03_Trail_95aca0e4929e': {
        'root_Trail_rot_HighLight_UEFX': 'MI_Eff_Objects_LKJ_GUIDd169a75fdf987b64fbc9f5d996567768_4c24dc96d60d',
        'root_Trail_rot_light_edge_UEFX': 'MI_Eff_Objects_LZL_GUID1e1e675fa82520b4c8f4324f8d2c8a4a_c68e1b1549f0',
        'root_Trail_rot_Shining_UEFX': 'MI_Eff_Objects_LKJ_GUID5b0312e87ded4644ca3051a1169e3fef_e66a17bf2d62',
    },
    'NS_Pyrios_ExSpecial_Phased_Eff_Pyrois_Attack_ExSpecial_01_04_Trail_b1031caaaf45': {
        'root_Trail_rot_HighLight_UEFX': 'MI_Eff_Objects_LKJ_GUIDd169a75fdf987b64fbc9f5d996567768_4c24dc96d60d',
        'root_Trail_rot_light_edge_UEFX': 'MI_Eff_Objects_LKJ_GUID79ffe342eefaa2d46a5654b23731b7fd_c8b55edf4099',
        'root_Trail_rot_Shining_UEFX': 'MI_Eff_Objects_LKJ_GUID5b0312e87ded4644ca3051a1169e3fef_e66a17bf2d62',
    },
    'NS_Eff_Pyrois_Attack_ExSpecial_01_09_MOD_3f003f915dcc': {
        'root__1__Glow__1__root__1__BG_Flare01_Line__1__UEFX': 'MI_Eff_Hit_LKJ_GUID99ab82550e8ceee4abc83b63e5367cb0_b5081f64afef',
        'root__1__Glow__1__root__1__BG_Flare01_Line__6__UEFX': 'MI_Eff_Hit_LKJ_GUID3a98e1501a55a78418e5bcdf870c984f_a13c65743ff4',
        'root__1__Glow__1__root__1__root__3__BG_Flare01_Line_UEFX': 'MI_Eff_Hit_LKJ_GUID1f37b9975a55f9b4e9cf0281494038e7_62127ad57938',
        'root__1__Glow__1__root__1__root__3__BG_Flare01_Line__1__UEFX': 'MI_Eff_Hit_LKJ_GUID7400c52ab2bfd7a4c99503e0ee481a4a_fe3121d3e132',
        'root__1__Glow__1__root__1__root__3__BG_Flare01_Line__2__UEFX': 'MI_Eff_Hit_LKJ_GUID1f37b9975a55f9b4e9cf0281494038e7_62127ad57938',
    },
}

def style_actions(only_skills=False):
    from pyrios_blade_reach import fit_blade_meshes
    mats={} if only_skills else {name:material(name,code) for name,code in [('Blade',BLADE),('Glint',GLINT),('Slipstream',WAKE)]}
    count=0
    for path in systems():
        system=ue.load_asset(path)
        is_skill = 'Special' in system.get_name()
        if only_skills and not is_skill:
            continue
        sources = SKILL_SURFACES.get(system.get_name(), {})
        summary=LIB.authoring_get_system_summary(system)
        if not summary.succeeded:
            raise RuntimeError(summary.error)
        changed=0
        for emitter in summary.emitters:
            name=emitter.emitter_name
            style=classify(path,name)
            source_name=sources.get(name)
            if is_skill and not source_name or not is_skill and not style:
                continue
            if is_skill:
                source=ue.load_asset('/Game/Characters/Shared/FX/ZZZ/MaterialInstances/'+source_name)
                if not isinstance(source,ue.MaterialInstanceConstant):
                    raise RuntimeError('技能粒子原材质缺失 '+source_name)
                dest=source.get_path_name()
            else:
                dest=mats[style].get_path_name()
            for entry in LIB.authoring_get_renderer_identities(system,name).renderers:
                kind=entry.renderer_class.split('.')[-1]
                if kind not in ('NiagaraSpriteRendererProperties','NiagaraMeshRendererProperties','NiagaraRibbonRendererProperties'):
                    continue
                idx=entry.renderer_index
                old=json.loads(LIB.authoring_get_renderer_data(system,name,idx).property_values)
                if is_skill and not any(LOOK+'/M_Pyrios_'+n+'.' in str(old) for n in ('Blade','Glint','Slipstream','Emberglow')):
                    continue
                if kind=='NiagaraMeshRendererProperties':
                    slots=old.get('OverrideMaterials',old.get('overrideMaterials',[]))
                    if len(slots)!=1:
                        continue
                    slot=slots[0]
                    if slot.get('userParamBinding',{}).get('parameter',{}).get('name','None')!='None':
                        continue
                    if slot.get('explicitMat',{}).get('refPath')==dest:
                        continue
                    update={'bOverrideMaterials':True,'OverrideMaterials':[{'ExplicitMat':dest}]}
                else:
                    if old.get('MaterialUserParamBinding',{}).get('parameter',{}).get('name','None')!='None':
                        continue
                    if old.get('Material',{}).get('refPath')==dest:
                        continue
                    update={'Material':dest}
                res=LIB.authoring_set_renderer_data(system,name,idx,json.dumps(update))
                if not res.succeeded:
                    raise RuntimeError(path+' '+name+': '+res.error)
                read=LIB.authoring_get_renderer_data(system,name,idx).property_values
                if dest not in read:
                    raise RuntimeError('材质未绑定 '+name)
                changed+=1
        if is_skill and fit_blade_meshes(system):
            ready = LIB.compile_authoring_batch(system)
            if not ready.native_ready or not ready.system_valid:
                raise RuntimeError('技能刀光编译失败 ' + path)
            changed += 1
        if changed:
            if not ASSETS.save_loaded_asset(system,False):
                raise RuntimeError('Niagara 保存失败 '+path)
            ue.log('PYRIOS_DAWN '+str(changed)+' '+path)
            count+=changed
    ue.log('PYRIOS_DAWN_COMPLETE '+str(count))


PACKAGE = '/Game/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_TurnBack'
MARK = 'Pyrios.PivotPose'
def mul(a,b):
    x,y,z,w=a
    i,j,k,r=b
    return (w*i+x*r+y*k-z*j,w*j+y*r+z*i-x*k,w*k+z*r+x*j-y*i,w*r-x*i-y*j-z*k)

def components(q):
    return (q.x,q.y,q.z,q.w)

def heading(pose):
    space=ue.AnimPoseSpaces.WORLD
    l=ue.AnimPoseExtensions.get_bone_pose(pose,'Bip001-L-Thigh',space).translation
    r=ue.AnimPoseExtensions.get_bone_pose(pose,'Bip001-R-Thigh',space).translation
    if math.hypot(r.y-l.y,r.x-l.x)<0.5:
        raise ValueError('髋横轴无法投影')
    return math.degrees(math.atan2(r.y-l.y,r.x-l.x))

def align_pivot():
    asset=ue.load_asset(PACKAGE)
    if ue.EditorAssetLibrary.get_metadata_tag(asset,MARK)=='hips-v1':
        return
    model=asset.get_editor_property('DataModelInterface')
    controller=asset.get_editor_property('Controller')
    count=model.get_number_of_keys()
    opts=ue.AnimPoseEvaluationOptions()
    opts.set_editor_properties({'EvaluationType':ue.AnimDataEvalType.RAW,'bShouldRetarget':False,'bExtractRootMotion':False,'bIncorporateRootMotionIntoPose':True})
    length=asset.get_play_length()
    def pose(i):
        return ue.AnimPoseExtensions.get_anim_pose_at_time(asset,length*i/(count-1),opts)
    def wrap(value):
        return (value+180.0)%360.0-180.0
    start=heading(pose(0))
    last=heading(pose(count-1))
    if abs(wrap(last-start))>15:
        raise RuntimeError('首尾不是同一跑姿')
    tkeys,rkeys,skeys=[],[],[]
    maximum=0
    for i in range(count):
        sample=pose(i)
        local=ue.AnimPoseExtensions.get_bone_pose(sample,'Bip001',ue.AnimPoseSpaces.LOCAL)
        parent=ue.AnimPoseExtensions.get_bone_pose(sample,'Bone_Root',ue.AnimPoseSpaces.WORLD)
        f=i/(count-1)
        delta=wrap(heading(sample)-(start+wrap(last-start)*f))
        # 允许自然的摆髋；仅将超过 16 度的反扭平滑限制到 30 度。
        excess=max(abs(delta)-16,0)
        kept=math.copysign(min(abs(delta),16)+14*math.tanh(excess/14),delta)
        correction=kept-delta
        maximum=max(maximum,abs(correction))
        p=components(parent.rotation)
        half=math.radians(correction)*0.5
        local_turn=mul(mul((-p[0],-p[1],-p[2],p[3]),(0,0,math.sin(half),math.cos(half))),p)
        q=mul(local_turn,components(local.rotation))
        if rkeys and sum(k*j for k,j in zip(components(rkeys[-1]),q))<0:q=tuple(-k for k in q)
        tkeys.append(local.translation)
        skeys.append(local.scale3d)
        rkeys.append(ue.Quat(*q))
    if maximum<20:
        raise RuntimeError('源动作没有复现大角度反拧')
    on_disk=Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_content_dir()))/(PACKAGE[6:]+'.uasset')
    backup=Path(ue.Paths.convert_relative_path_to_full(ue.Paths.project_saved_dir()))/'PyriosPivot'/'original.uasset'
    backup.parent.mkdir(parents=True,exist_ok=True)
    if not backup.exists():
        shutil.copy2(on_disk,backup)
    controller.set_model(model)
    controller.open_bracket('佩洛伊斯急转姿态对齐',should_transact=False)
    try:
        if not controller.set_bone_track_keys('Bip001',tkeys,rkeys,skeys,should_transact=False):
            raise RuntimeError('写骨轨失败')
    finally:
        controller.close_bracket(should_transact=False)
    bound=max(abs(wrap(heading(pose(i))-start)) for i in range(count))
    if bound>32 or abs(wrap(heading(pose(count-1))-last))>1:
        raise RuntimeError('未达到髋部方向或末键要求 '+str(bound))
    ue.EditorAssetLibrary.set_metadata_tag(asset,MARK,'hips-v1')
    if not ue.EditorAssetLibrary.save_loaded_asset(asset,False):
        raise RuntimeError('急转动画保存失败')
    ue.log('PYRIOS_TURN_POSE 保存 '+str(count)+' 帧，最大补偿 '+str(round(maximum,1))+' 度，修后相对髋朝向 '+str(round(bound,1))+' 度')


def style_impacts():
    root='/Game/Characters/Player/Pyrios/FX/Dawn'
    sparks=root+'/NS_Pyrios_ContactSparks'
    glint=ue.load_asset(root+'/M_Pyrios_Glint')
    if not glint:
        raise RuntimeError('缺 Pyrios 命中星点材质')
    lib=ue.GGYGONiagaraCompileLibrary
    editor=ue.EditorAssetLibrary
    src='/Game/Characters/Boss/Kevin/DemonBattle/FX/Systems/NS_Kevin_FireHitImpact_650061a4c087'
    system=ue.load_asset(sparks) if editor.does_asset_exist(sparks) else editor.duplicate_asset(src,sparks)
    if not system:
        raise RuntimeError('短促命中粒子模板不可用')
    changed = False
    draw=0
    for emit in lib.authoring_get_system_summary(system).emitters:
        for renderer in lib.authoring_get_renderer_identities(system,emit.emitter_name).renderers:
            if not renderer.renderer_class.endswith('NiagaraSpriteRendererProperties'):
                raise RuntimeError('模板渲染器不符')
            current=lib.authoring_get_renderer_data(system,emit.emitter_name,renderer.renderer_index)
            if not current.succeeded:
                raise RuntimeError(current.error)
            if json.loads(current.property_values).get('Material',{}).get('refPath')==glint.get_path_name():
                draw+=1
                continue
            changed = True
            change=lib.authoring_set_renderer_data(system,emit.emitter_name,renderer.renderer_index,json.dumps({'Material':glint.get_path_name()}))
            if not change.succeeded:
                raise RuntimeError(change.error)
            draw+=1
    if draw != 1 or (changed and not editor.save_loaded_asset(system, False)):
        raise RuntimeError('命中粒子保存失败')
    for step in ('Normal01','Normal02','Normal03','Special01','ExSpecial01'):
        bp=ue.load_asset('/Game/GameplayCues/GCN_Pyrios_Hit_'+step)
        cdo=ue.get_default_object(bp.generated_class())
        original=cdo.get_editor_property('default_effect')
        sound=original.get_editor_property('impact_sound')
        if original.get_editor_property('impact_effect')==system:
            continue
        bp.modify()
        original.set_editor_property('impact_effect',system)
        cdo.set_editor_property('default_effect',original)
        ue.BlueprintEditorLibrary.compile_blueprint(bp)
        after=ue.get_default_object(bp.generated_class()).get_editor_property('default_effect')
        if after.get_editor_property('impact_effect')!=system or after.get_editor_property('impact_sound')!=sound:
            raise RuntimeError(step+' Cue 读回失败')
        if not editor.save_loaded_asset(bp,False):
            raise RuntimeError(step+' Cue 保存失败')
    ue.log('PYRIOS_CONFIRMED_HIT_CUES 5')


def refresh_first_strike_field():
    """重新生成 5.9 普攻第一段所需的扭曲材质与实例缓存。"""
    material_instance = ue.load_asset(
        '/Game/Characters/Shared/FX/ZZZ/MaterialInstances/'
        'MI_Eff_Others_LKJ_GUID52624181e1174d44a868969214903b9a_60f481077dbf')
    parent = material_instance.get_editor_property('parent')
    if not isinstance(parent, ue.Material) or 'DualField' not in parent.get_name():
        raise ValueError('普攻第一段扭曲材质母版不匹配')
    if EDIT.recompile_material(parent):
        raise RuntimeError('首击扭曲材质编译失败')
    EDIT.update_material_instance(material_instance)
    ue.SystemLibrary.execute_console_command(None, 'Editor.AsyncAssetCompilationFinishAll')
    for asset in (parent, material_instance):
        if not ASSETS.save_loaded_asset(asset, False):
            raise RuntimeError('未保存扭曲材质 '+asset.get_path_name())


if __name__ == "__main__":
    style_actions()
    style_impacts()
    align_pivot()
    refresh_first_strike_field()
    from refine_pyrios_blade import build as build_live_blade
    build_live_blade()
