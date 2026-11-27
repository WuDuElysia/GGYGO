"""按普攻姿态校准刀面的展开范围、第二刀的起笔和落地亮部。"""
import json
import unreal as ue

from pyrios_blade_reach import update_slash_inputs
from pyrios_source_slashes import LIB, SOURCE_FIELDS, SOURCE_SURFACES
from zzz_fx_niagara_ue import NiagaraBuilder, NS


# 在角色的局部空间调整横斩的俯仰，使放大的亮弧仍横穿出刀方向。
def first_blade_rotation():
    q = 'Particles.SourceSlashOrientation'
    axis = 'float3(-0.115176,0.189798,0.159831)'
    w = '0.961857'
    return (f'normalize(float4({w}*{q}.xyz+{q}.w*{axis}+cross({axis},{q}.xyz),'
            f'{w}*{q}.w-dot({axis},{q}.xyz)))')


# 半径只收在宽雾和直射白光上。地面裂纹、岩块与电弧继续使用原范围。
CONTACT = {
    'M10_root_ConeSmoke_UVmove__8__UEFX': ('Scale', .65, .46),
    'M15_root_Hit_Glow02_di_UEFX': ('SpriteSize', .60, .55),
    'M15_root_Hit_Glow02_di_Glow_Ground__4__UEFX': ('SpriteSize', .65, .56),
    'M15_root_Hit_Glow02_di_Cone01liang__13__UEFX': ('Scale', .66, .64),
    'M16_root__1__Root__3__Cone01liang__12__UEFX': ('Scale', .68, .63),
    'M16_root__1__Root__3__Hit_Glow__24__UEFX': ('SpriteSize', .59, .52),
    'M16_root__1__Root__3__Noise_Light__5__UEFX': ('Scale', .80, .64),
}


def delay_uppercut(system, emitter, tool):
    """原七个发射器均以一次零时刻爆发起笔；只移动该笔，与武器上挑对拍。"""
    script = dict(system={'refPath': system.get_path_name()}, emitterName=emitter, scriptName='EmitterUpdateScript')
    modules = tool(NS + 'GetScriptStackTopology', scriptRef=script)['modules']
    bursts = [m['moduleName'] for m in modules if m['moduleName'].startswith('SpawnBurst_Instantaneous')]
    if len(bursts) != 1:
        raise RuntimeError('上挑刀面缺少唯一原爆发 ' + emitter)
    tool(NS + 'SetStackInputData', stackInputRef=dict(script, moduleName=bursts[0], inputNameStack=['Spawn Time']),
         inputData=NiagaraBuilder.num('Float', .058))


def apply_combo_profile(system, tool, assign):
    key = system.get_name()
    tag = 'Pyrios.ComboPoseProfile'
    first = key.startswith('NS_Pyrios_Normal01_')
    second = key.startswith('NS_Pyrios_Normal02_')
    source = {*SOURCE_SURFACES.get(key, {}), *SOURCE_FIELDS.get(key, ())}
    stamp = 'film-combo-2' if first else 'film-combo-1'
    previous = ue.EditorAssetLibrary.get_metadata_tag(system, tag)
    if previous == stamp:
        return False
    if first and previous == 'film-combo-1':
        for emitter in sorted(source):
            for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
                script = dict(system={'refPath': system.get_path_name()}, emitterName=emitter, scriptName=stage)
                update_slash_inputs(tool, script, {'Particles.FilmBladeRotation': first_blade_rotation()})
        ue.EditorAssetLibrary.set_metadata_tag(system, tag, stamp)
        return True
    work, changes = [], []
    for entry in LIB.authoring_get_system_summary(system).emitters:
        name = entry.emitter_name
        values = {}
        bindings = {}
        if name in source and (first or second or name.startswith('M14_root_Trail_rot_')):
            # 使用发射器原局部空间，所有色层和折射场共用同一尺寸和起点。
            scale = 1.48 if first else 1.40 if second else 1.23
            values['FilmBladeScale'] = ('Vector', f'Particles.Scale * {scale}')
            bindings['ScaleBinding'] = 'FilmBladeScale'
            if first or second:
                shift = 'float3(-28,54,2)' if first else 'float3(0,18,-42)'
                values['FilmBladeCenter'] = ('Position', 'Particles.Position + ' + shift)
                bindings['PositionBinding'] = 'FilmBladeCenter'
            if first:
                # 在已校正的横斩之上压低斩面倾角；保留原网格内部随时间的旋转。
                values['FilmBladeRotation'] = ('Quat', first_blade_rotation())
                bindings['MeshOrientationBinding'] = 'FilmBladeRotation'
            elif second:
                delay_uppercut(system, name, tool)
        elif name in CONTACT:
            size, radius, gain = CONTACT[name]
            kind = 'Vector' if size == 'Scale' else 'Vector2'
            values['FilmContactSize'] = (kind, f'Particles.{size} * {radius}')
            values['FilmContactColor'] = ('LinearColor', f'float4(Particles.Color.rgb * {gain}, Particles.Color.a)')
            bindings[size + 'Binding'] = 'FilmContactSize'
            bindings['ColorBinding'] = 'FilmContactColor'
        else:
            continue
        data = LIB.authoring_get_renderer_identities(system, name)
        if not data.succeeded or len(data.renderers) != 1:
            raise RuntimeError('普攻表现层缺少唯一渲染器 ' + name)
        changes.append((name, data.renderers[0].renderer_index, bindings))
        for script in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            work.append(assign(script, emitter=name, **values))
    if not changes:
        return False
    result = tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch',
                  system={'refPath': system.get_path_name()}, workItems=work)
    if not result.get('bApplied'):
        raise RuntimeError(result.get('error', '普攻姿态校准失败'))
    for name, index, bindings in changes:
        props = {k: NiagaraBuilder.attribute_binding('Particles.' + value) for k, value in bindings.items()}
        update = LIB.authoring_set_renderer_data(system, name, index, json.dumps(props))
        if not update.succeeded:
            raise RuntimeError(update.error)
    ue.EditorAssetLibrary.set_metadata_tag(system, tag, stamp)
    return True
