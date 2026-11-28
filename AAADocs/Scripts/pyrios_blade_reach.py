"""佩洛伊斯刀光可见范围。倍率作用于刀面网格自身的展开轴。"""
import unreal as ue

from pyrios_source_slashes import FACE_MATERIALS, LIB, SOURCE_FIELDS, SOURCE_SURFACES
from zzz_fx_niagara_ue import NiagaraBuilder, NS


# 前三道空间斩已有 1.32 的刀面底尺；贴地宽光与独立光晕不在此表中。
COMBO_RADIUS = {
    'Normal01': {'M00': (1.0, 1.0)},
    'Normal02': {'M00': (1.83, 1.83)},
    'Normal03': {'M00': (1.52, 1.15), 'M04': (1.52, 1.15), 'M09': (1.52, 1.15),
                 'M11': (1.34, 1.34), 'M12': (1.38, 1.38), 'M14': (1.25, 1.25)},
}
# 模型坐标系不同：原刀面在 XY，锥形折射面在 XZ。直线刻痕只拉长 X。
MESH_AXES = {
    'FXMD_DAO_001': 'xy', 'Cylinder005': 'xy', 'Eff_Trail_Cone_04': 'xz',
    'FXMD_Circle': 'xy', 'Plane018': 'x', 'Plane004': 'xz', 'Plane006': 'xz',
    'Plane002': 'xz', 'Plane009': 'xz', 'Cylinder003': 'xz',
}
# 原长切口长度同时驱动网格和沿刃移动的光。地面的扫光有独立宽度和范围。
CUT_LENGTH = 'Particles.UniqueID==0 ? 612.0 : (Particles.UniqueID==1 ? 567.0 : 470.0)'
# 实机逐帧取刃身 55% 处，按每次穿切的整段位移定向。用招式坐标系在出生时落笔，
# 避免较长的游戏帧跨过两次穿切，把后一刀的方向画在前一道切痕上。
CUT_BURSTS = (.044, .088, .138)


def stroke_vector(vectors):
    def world(v):
        return '(' + ' + '.join(f'Engine.Owner.System{axis}Axis*({value})'
                                for axis, value in zip('XYZ', v)) + ')'
    a, b, c = map(world, vectors)
    return f'(Particles.UniqueID==0 ? {a} : (Particles.UniqueID==1 ? {b} : {c}))'


CUT_CENTER = 'Engine.Owner.Position + ' + stroke_vector(((-106, 52, 72), (-59, 12, 50), (70, -4, 101)))
CUT_AXIS = 'normalize(' + stroke_vector(((-.60, .60, -.54), (.91, .41, .08), (-.88, -.48, -.06))) + ')'
CUT_LOCK = '!Particles.CutFixed && Particles.HasContact'
CUT_POSITION = 'Particles.CutLockNow ? Particles.CutStart : Particles.Position'
# 锁定后由网格自身的朝向还原世界轴，灯光、地面反射和折射沿同一次入刀走。
CUT_DIRECTION = ('Particles.CutLockNow ? ' + CUT_AXIS + ' : '
                 'float3(1,0,0)+2*cross(Particles.MeshOrientation.xyz,'
                 'cross(Particles.MeshOrientation.xyz,float3(1,0,0))+Particles.MeshOrientation.w*float3(1,0,0))')
GROUND_SIZE = 'float3(13,(Particles.UniqueID==0 ? 378.0 : (Particles.UniqueID==1 ? 350.0 : 290.0))*2.1,154)'


def skill_radius(system_name, emitter):
    if system_name.startswith('NS_Pyrios_Special_Phased_'):
        if emitter.startswith(('M00_root_rot__1__', 'M01_root__1__rot__1__')):
            return 1.55
        if emitter.startswith('M02_Trail_Main_002_'):
            return 1.40
    if system_name.startswith('NS_Pyrios_ExSpecial_Phased_'):
        if '_05_Trail_' in system_name and emitter.startswith('root__7__root__3__New_NormalFx_Node_'):
            return 1.42
        if emitter.startswith('root_Trail_rot_') and 'Smoke_Cone' not in emitter:
            return 1.55
        if emitter.startswith(('M00_root__1__root_MeleeTrail_', 'M01_root__1__root_MeleeTrail_')):
            return 1.32
    return None


def fit_blade_meshes(system):
    key = system.get_name()
    combo = next((name for name in COMBO_RADIUS if key.startswith('NS_Pyrios_' + name + '_')), None)
    if not combo and not key.startswith(('NS_Pyrios_Special_Phased_', 'NS_Pyrios_ExSpecial_Phased_')):
        return False
    source = SOURCE_SURFACES.get(key, {})
    fields = SOURCE_FIELDS.get(key, ())
    changed = False
    summary = LIB.authoring_get_system_summary(system)
    if not summary.succeeded:
        raise RuntimeError(summary.error)
    for entry in summary.emitters:
        name = entry.emitter_name
        if combo:
            sizes = COMBO_RADIUS[combo].get(name.split('_', 1)[0])
            if sizes is None or (name not in source and name not in fields):
                continue
            radius = sizes[1] if name in fields else sizes[0]
        else:
            radius = skill_radius(key, name)
            if radius is None:
                continue
        identities = LIB.authoring_get_renderer_identities(system, name)
        if not identities.succeeded:
            raise RuntimeError(identities.error)
        for identity in identities.renderers:
            if not identity.renderer_class.endswith(('NiagaraMeshRendererProperties', 'GGYGOSignedFieldMeshRendererProperties')):
                continue
            obj = ue.find_object(None, identity.renderer_path)
            if not obj:
                raise RuntimeError(f'{key}/{name} 找不到渲染器 {identity.renderer_path}')
            slots = list(obj.get_editor_property('meshes'))
            if len(slots) != 1 or not slots[0].mesh:
                raise RuntimeError('攻击刀面缺少唯一网格 ' + name)
            slot = slots[0]
            mesh_name = slot.mesh.get_name().rsplit('_', 1)[0]
            axes = MESH_AXES.get(mesh_name)
            if axes is None:
                raise RuntimeError(f'{key}/{name} 的网格缺少展开轴配置 {mesh_name}')
            target = ue.Vector(*(radius if axis in axes else 1.0 for axis in 'xyz'))
            # 原刀面沿 UV 的刃脊有起伏。只把刃腹高光层的厚度展开，外缘与切尖仍在原平面。
            if mesh_name == 'FXMD_DAO_001' and source.get(name) in FACE_MATERIALS:
                target.z = 2.85 if combo == 'Normal01' else 2.4
            # 首刀横扫时刀面近乎侧对镜头，软光沿网格起伏展开，白芯和刀纹仍在原刃面。
            if combo == 'Normal01' and name == 'M00_root_Trail_rot_bloom':
                target.z = 3.25
            if all(abs(a-b) < .0001 for a, b in zip(slot.scale.to_tuple(), target.to_tuple())):
                continue
            obj.modify()
            slot.scale = target
            obj.set_editor_property('meshes', slots)
            changed = True
    return changed


def update_locked_cuts(system, tool):
    """更新已有资产的三次起笔和随刃落痕，沿用原显影与碰撞投影。"""
    script = dict(system={'refPath': system.get_path_name()}, emitterName='Pyrios_AftercutMarks',
                  scriptName='ParticleUpdateScript')
    targets = {'Particles.CutLength': CUT_LENGTH, 'Particles.WashSize': GROUND_SIZE,
               'Particles.CutLockNow': CUT_LOCK, 'Particles.CutDirection': CUT_DIRECTION,
               'Particles.Position': CUT_POSITION, 'Particles.CutReverse': 'false'}
    changed = update_slash_inputs(tool, dict(script, scriptName='ParticleSpawnScript'),
                                  {'Particles.CutStart': CUT_CENTER})
    changed = update_slash_inputs(tool, script, targets) or changed
    emitter_script = dict(script, scriptName='EmitterUpdateScript')
    modules = tool(NS + 'GetScriptStackTopology', scriptRef=emitter_script)['modules']
    bursts = [m['moduleName'] for m in modules if m['moduleName'].startswith('SpawnBurst_Instantaneous')]
    if len(bursts) != len(CUT_BURSTS):
        raise RuntimeError('空间斩缺少三次独立起笔')
    for name, time in zip(bursts, CUT_BURSTS):
        ref = dict(emitter_script, moduleName=name)
        inputs = tool(NS + 'GetModuleInputValues', moduleRef=ref)['inputs']
        value = next(i['value'] for i in inputs if i['name'] == 'Spawn Time')
        if abs(value['value']['value'] - time) < .00001:
            continue
        tool(NS + 'SetStackInputData', stackInputRef=dict(ref, inputNameStack=['Spawn Time']),
             inputData=NiagaraBuilder.num('Float', time))
        changed = True
    return changed


def update_slash_inputs(tool, script, targets):
    """在现有赋值节点更新刀面表达式，避免重复叠加缩放或旋转。"""
    stack = tool(NS + 'GetScriptStackTopology', scriptRef=script)
    found = set()
    changed = False
    for module in stack['modules']:
        names = {i['name'] for i in module.get('inputs', [])} & targets.keys()
        if not names or not module.get('bIsSetParametersModule'):
            continue
        ref = dict(script, moduleName=module['moduleName'])
        values = tool(NS + 'GetModuleInputValues', moduleRef=ref)['inputs']
        for name in names:
            if name in found:
                raise RuntimeError('刀面参数出现重复赋值 ' + name)
            found.add(name)
            expected = NiagaraBuilder.hlsl(targets[name])
            actual = next(i['value'] for i in values if i['name'] == name)
            if actual.get('value', {}).get('hlslExpression') == targets[name]:
                continue
            tool(NS + 'SetStackInputData', stackInputRef=dict(ref, inputNameStack=[name]), inputData=expected)
            changed = True
    if found != targets.keys():
        raise RuntimeError('刀面缺少赋值 ' + str(targets.keys() - found))
    return changed
