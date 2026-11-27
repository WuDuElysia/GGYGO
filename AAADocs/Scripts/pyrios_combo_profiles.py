"""按普攻姿态校准刀面的展开范围、第二刀的起笔和落地亮部。"""
import json
import unreal as ue

from pyrios_blade_reach import update_slash_inputs
from pyrios_source_slashes import LIB, SOURCE_FIELDS, SOURCE_SURFACES
from zzz_fx_niagara_ue import NiagaraBuilder, NS


# 首刀剑尖在角色局部空间扫过的平面和朝向，由实机慢放采样。
# 时间从刀面爆发开始，以角度补偿原刀面网格自身的旋转。所有描边、烟和折射一起转。
FIRST_BURST = .083
FIRST_SWING = (
    (0, 120), (.009, 137), (.018, 171), (.030, 230), (.037, 279),
    (.054, 414), (.062, 468), (.065, 480), (.087, 497), (.112, 506),
)


def first_blade_rotation():
    q = 'Particles.SourceSlashOrientation'

    def left_product(x, y, z, w):
        axis = f'float3({x},{y},{z})'
        return (f'float4({w}*{q}.xyz+{q}.w*{axis}+cross({axis},{q}.xyz),'
                f'{w}*{q}.w-dot({axis},{q}.xyz))')

    yaw = str(FIRST_SWING[0][1])
    for (start, previous), (end, target) in zip(FIRST_SWING, FIRST_SWING[1:]):
        yaw += f'+({target-previous})*saturate((Particles.Age-{start:.3f})/{end-start:.3f})'
    half = f'radians({yaw})*0.5'
    # 左乘挥剑平面基准；第二个基底等于该平面单位法向四元数乘第一个基底。
    base = left_product(-.0114304, .2535602, .1570965, .9544113)
    normal_times_base = left_product(.0214334, -.0111426, .9869470, -.1592350)
    return f'normalize(cos({half})*{base}+sin({half})*{normal_times_base})'


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


def set_slash_burst(system, emitter, tool, time):
    """只移动原发射器的单次爆发，让刀面按对应招式起笔。"""
    script = dict(system={'refPath': system.get_path_name()}, emitterName=emitter, scriptName='EmitterUpdateScript')
    modules = tool(NS + 'GetScriptStackTopology', scriptRef=script)['modules']
    bursts = [m['moduleName'] for m in modules if m['moduleName'].startswith('SpawnBurst_Instantaneous')]
    if len(bursts) != 1:
        raise RuntimeError('刀面缺少唯一原爆发 ' + emitter)
    tool(NS + 'SetStackInputData', stackInputRef=dict(script, moduleName=bursts[0], inputNameStack=['Spawn Time']),
         inputData=NiagaraBuilder.num('Float', time))


def apply_combo_profile(system, tool, assign):
    key = system.get_name()
    tag = 'Pyrios.ComboPoseProfile'
    first = key.startswith('NS_Pyrios_Normal01_')
    second = key.startswith('NS_Pyrios_Normal02_')
    source = {*SOURCE_SURFACES.get(key, {}), *SOURCE_FIELDS.get(key, ())}
    stamp = 'film-combo-3' if first else 'film-combo-1'
    previous = ue.EditorAssetLibrary.get_metadata_tag(system, tag)
    if previous == stamp:
        return False
    if first and previous in ('film-combo-1', 'film-combo-2'):
        for emitter in sorted(source):
            set_slash_burst(system, emitter, tool, FIRST_BURST)
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
                set_slash_burst(system, name, tool, FIRST_BURST)
                values['FilmBladeRotation'] = ('Quat', first_blade_rotation())
                bindings['MeshOrientationBinding'] = 'FilmBladeRotation'
            elif second:
                set_slash_burst(system, name, tool, .058)
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
