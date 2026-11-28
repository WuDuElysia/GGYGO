"""按普攻姿态校准刀面的展开范围、第二刀的起笔和落地亮部。"""
import json
import unreal as ue

from pyrios_blade_reach import update_slash_inputs
from pyrios_source_slashes import LIB, SOURCE_FIELDS, SOURCE_SURFACES, SPACE_SWINGS
from zzz_fx_niagara_ue import NiagaraBuilder, NS


# 首刀剑尖在角色局部空间扫过的平面和朝向，由实机慢放采样。
# 时间从刀面爆发开始，以角度补偿原刀面网格自身的旋转。所有描边、烟和折射一起转。
FIRST_BURST = .083
# 近侧刀弧用余弦缓入缓出，峰值抬高 76 cm 掠过肩前。所有刀纹、软光和折射共用同一位移。
FIRST_CENTER = ('Particles.Position + float3(-28,54,2 + 19'
                ' * (1 - cos(3.141593 * saturate((Particles.Age-.001)/.017)))'
                ' * (1 + cos(3.141593 * saturate((Particles.Age-.033)/.025))))')
FIRST_SWING = (
    (0, 120), (.009, 137), (.018, 171), (.030, 230), (.037, 279),
    (.054, 414), (.062, 468), (.065, 480), (.087, 497), (.112, 506),
)


# 上挑在蓄力下探后反向，沿立面从脚下扫过身前，最后在举剑姿态退光。
UPPERCUT_BURST = .133
UPPERCUT_SWING = (
    (0, 193), (.006, 218), (.014, 255), (.023, 271),
    (.053, 318), (.077, 355), (.100, 368), (.123, 373),
)


def quat_product(source, rotation):
    x, y, z, w = rotation
    axis = f'float3({x},{y},{z})'
    return (f'float4({w}*{source}.xyz+{source}.w*{axis}+cross({axis},{source}.xyz),'
            f'{w}*{source}.w-dot({axis},{source}.xyz))')


def sweep_rotation(source, keys, plane_basis, normal_times_basis):
    yaw = str(keys[0][1])
    for (start, previous), (end, target) in zip(keys, keys[1:]):
        yaw += f'+({target-previous})*saturate((Particles.Age-{start:.3f})/{end-start:.3f})'
    half = f'radians({yaw})*0.5'
    base = quat_product(source, plane_basis)
    along_normal = quat_product(source, normal_times_basis)
    return f'normalize(cos({half})*{base}+sin({half})*{along_normal})'


def first_blade_rotation():
    return sweep_rotation('Particles.SourceSlashOrientation', FIRST_SWING,
                          (-.0114304, .2535602, .1570965, .9544113),
                          (.0214334, -.0111426, .9869470, -.1592350))


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
    stamp = 'film-combo-4' if first else 'film-combo-1'
    previous = ue.EditorAssetLibrary.get_metadata_tag(system, tag)
    if previous == stamp:
        return False
    if first and previous in ('film-combo-1', 'film-combo-2', 'film-combo-3'):
        targets = {'Particles.FilmBladeCenter': FIRST_CENTER}
        if previous != 'film-combo-3':
            targets['Particles.FilmBladeRotation'] = first_blade_rotation()
        for emitter in sorted(source):
            if previous != 'film-combo-3':
                set_slash_burst(system, emitter, tool, FIRST_BURST)
            for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
                script = dict(system={'refPath': system.get_path_name()}, emitterName=emitter, scriptName=stage)
                update_slash_inputs(tool, script, targets)
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
                center = FIRST_CENTER if first else 'Particles.Position + float3(0,18,-42)'
                values['FilmBladeCenter'] = ('Position', center)
                bindings['PositionBinding'] = 'FilmBladeCenter'
            if first:
                set_slash_burst(system, name, tool, FIRST_BURST)
                values['FilmBladeRotation'] = ('Quat', first_blade_rotation())
                bindings['MeshOrientationBinding'] = 'FilmBladeRotation'
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


def align_followup_swings(system, tool, assign):
    name = system.get_name()
    uppercut = name.startswith('NS_Pyrios_Normal02_')
    layers = sorted({*SOURCE_SURFACES.get(name, {}), *SOURCE_FIELDS.get(name, ())})
    if not uppercut:
        layers = [e for e in layers if name.startswith('NS_Pyrios_Normal03_') and e[:3] in SPACE_SWINGS]
    tag = 'Pyrios.FollowupSwing'
    previous = ue.EditorAssetLibrary.get_metadata_tag(system, tag)
    stamp = 'weapon-swing-2' if uppercut or '_Unit00_' in name else 'weapon-swing-1'
    if not layers or previous == stamp:
        return False
    work = []
    for emitter in layers:
        if uppercut:
            set_slash_burst(system, emitter, tool, UPPERCUT_BURST)
            rotation = sweep_rotation('Particles.MeshOrientation', UPPERCUT_SWING,
                                      (-.0263211, -.6468961, 0, .7621238), (.6468961, -.0263211, -.7621238, 0))
        else:
            delay, _, tilt = SPACE_SWINGS[emitter[:3]]
            # 移动整个原片段，内部旋转曲线与原有单次爆发一同起笔。
            ref = dict(system={'refPath': system.get_path_name()}, emitterName=emitter,
                       scriptName='EmitterUpdateScript', moduleName='EmitterState')
            # 首道伴随系统激活，首轮的循环延迟没有推迟原爆发，直接给爆发定时。
            first_cut = emitter.startswith('M00_')
            timing = [('UseLoopDelay', 'Bool', not first_cut)]
            if not first_cut:
                timing.append(('Loop Delay', 'Float', delay))
            for pin, kind, value in timing:
                tool(NS + 'SetStackInputData', stackInputRef=dict(ref, inputNameStack=[pin]),
                     inputData=NiagaraBuilder.num(kind, value))
            if first_cut:
                set_slash_burst(system, emitter, tool, delay)
            rotation = 'normalize(' + quat_product('Particles.SourceSlashOrientation', tilt) + ')'
        for stage in ('ParticleSpawnScript', 'ParticleUpdateScript'):
            if previous != 'weapon-swing-1':
                work.append(assign(stage, emitter=emitter, FilmBladeRotation=('Quat', rotation)))
            elif uppercut:
                ref = dict(system={'refPath': system.get_path_name()}, emitterName=emitter, scriptName=stage)
                update_slash_inputs(tool, ref, {'Particles.FilmBladeRotation': rotation})
    if not work:
        ue.EditorAssetLibrary.set_metadata_tag(system, tag, stamp)
        return True
    result = tool('GGYGOEditor.GGYGONiagaraCompileLibrary.ApplyAuthoringStackBatch',
                  system={'refPath': system.get_path_name()}, workItems=work)
    if not result.get('bApplied'):
        raise RuntimeError(result.get('error', '上挑与空间斩校准失败'))
    binding = NiagaraBuilder.attribute_binding('Particles.FilmBladeRotation')
    for emitter in layers:
        identity = LIB.authoring_get_renderer_identities(system, emitter)
        if not identity.succeeded or len(identity.renderers) != 1:
            raise RuntimeError('刀面缺少唯一渲染器 ' + emitter)
        result = LIB.authoring_set_renderer_data(system, emitter, identity.renderers[0].renderer_index,
                                                 json.dumps({'MeshOrientationBinding': binding}))
        if not result.succeeded:
            raise RuntimeError(result.error)
    ue.EditorAssetLibrary.set_metadata_tag(system, tag, stamp)
    return True
