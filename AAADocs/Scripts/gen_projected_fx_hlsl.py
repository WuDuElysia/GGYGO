"""@file gen_projected_fx_hlsl.py
@brief 将准确Decal程序的表面与遮罩计算移植到原生投影；场景光照由UE负责。

生成物保留源程序身份。投影坐标、源粒子流和实际实例Age由原FX提供；
缺失的原stage映射仍由调用方提供准确证据，不据共享VP外观认证匹配。
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import zzz_dxbc_hlsl as T

HERE = Path(__file__).resolve().parent
POLICY = HERE.parents[1] / 'Saved/Codex/FXRestoration_20261022_F1/ProjectShaders_R8/project_shader_policy.json'
DECAL_SID = '3236134733678291145'
PROP_SID = '108369129736756662'
PROGRAM_FILE = HERE / 'projected_fx_programs.json'

# 下标绑定准确程序字节；不把相似变体的寄存器位置套用到其它程序。
DECAL_CUTS = {
    'd7fdbec172180b22': dict(normal_sample=41, projection=(50, 73), local='r3.xyz',
        world='r2.xyz', main=117, normal_end=164, normal='r7.zwzz', normal_z='r3.w',
        receiver=(167, 175), roughness=171, emission_end=180, base='r8.xyz',
        opacity_end=236, emission='r10.xyzx', emission_fade='r5.yyyy',
        lighting_tail=651, alpha='r0.z', color='r0.xyw'),
    '81e3c1be3b0f474a': dict(normal_sample=43, projection=(52, 75), local='r3.xyz',
        world='r2.xyz', main=119, normal_end=166, normal='r7.zwzz', normal_z='r3.w',
        receiver=(169, 177), roughness=173, emission_end=188, base='r8.xyz',
        opacity_end=244, emission='r10.xyzx', emission_fade='r5.yyyy',
        lighting_tail=659, alpha='r0.z', color='r0.xyw'),
    '6390ece1999f1286': dict(normal_sample=43, projection=(52, 75), local='r3.xyz',
        world='r2.xyz', main=169, normal_end=210, normal='r3.xyxx', normal_z='r3.z',
        receiver=(213, 221), roughness=217, emission_end=226, base='r11.xyz',
        opacity_end=282, emission='r4.xzwx', emission_fade='r9.yyyy',
        lighting_tail=695, alpha='r0.z', color='r0.xyw'),
    'b8a5ab84ac38afc': dict(normal_sample=26, projection=(35, 58),
        local='r0.xyw', world=None, alpha='r0.x', color='r0.yzw'),
}

PRELUDE = r'''// 原DXBC表面计算；原生投影提供真实receiver位置和深度导数法线。
struct ProjectedFunctions {
 float3 U(float3 v) { return float3(-v.x,v.z,v.y); }
 float4 S(Texture2D T, SamplerState Smp, float2 uv) {
  return Texture2DSample(T,Smp,float2(uv.x,1.0-uv.y)); }
 float4 SL(Texture2D T, SamplerState Smp, float2 uv, float lod) {
  return Texture2DSampleLevel(T,Smp,float2(uv.x,1.0-uv.y),lod); }
 float4 SB(Texture2D T, SamplerState Smp, float2 uv, float bias) {
  return Texture2DSampleBias(T,Smp,float2(uv.x,1.0-uv.y),bias); }
};
ProjectedFunctions F;
float3 ReceiverU=F.U(ReceiverRelativeWS)*0.01;
float3 CameraU=F.U(CameraRelativeWS)*0.01;
float3 DerivedNormal=cross(ddy(ReceiverRelativeWS),ddx(ReceiverRelativeWS));
float NormalLength=dot(DerivedNormal,DerivedNormal);
if(NormalLength<=0.0) { clip(-1.0); }
DerivedNormal*=rsqrt(max(NormalLength,1e-20));
DerivedNormal*=dot(DerivedNormal,CameraRelativeWS-ReceiverRelativeWS)<0.0?-1.0:1.0;
float4 ReceiverNormal=float4(F.U(DerivedNormal)*0.5+0.5,0);
float4 RelativePoint=float4(ReceiverU,1);
float3 SourceLocal=float3(dot(UEFX_ProjectionRow0,RelativePoint),
 dot(UEFX_ProjectionRow1,RelativePoint),dot(UEFX_ProjectionRow2,RelativePoint));
'''

RAW_STREAMS = {'UEFX_SourceColor': 4, 'UEFX_SourceCenter': 4, 'UEFX_SourceSize': 4,
               'UEFX_SourceStableRandom': 4, 'UEFX_SourceCustom1': 4, 'UEFX_SourceCustom2': 4}
NATIVE_INPUTS = {'ReceiverRelativeWS', 'CameraRelativeWS'}

# 原FX作者实读的pass1唯一_DITHER_SWITCH程序；Flow材质采用明确stage投影配置。
PROP_GEOMETRY = {
    'vp': dict(sourceByteRange=dict(offset=952672, bytes=4924), sourceLine=24991,
        fileBytesSha256='9e1c22694b1fdef7edf9f3b2478ecbc7e32b7fe03ef43f3d2c689b6e0d8000df',
        hash64='4edda51e4d7612cc', globalKeywords=['_DITHER_SWITCH'], localKeywords=[]),
    'fp': dict(sourceByteRange=dict(offset=1147938, bytes=6421), sourceLine=30241,
        fileBytesSha256='2417ed4dd1675ded12fa7c9e3145c007fc1f4441de0083f3e583381df52e542c',
        hash64='79504799574199bb', globalKeywords=['_DITHER_SWITCH'], localKeywords=[]),
}


def read_program(shader, record):
    """只读准确字节区间；保真实原文件hash/偏移及stage关键词。"""
    span = record['sourceByteRange']
    with Path(shader).open('rb') as stream:
        stream.seek(span['offset'])
        raw = stream.read(span['bytes'])
    if len(raw) != span['bytes'] or hashlib.sha256(raw).hexdigest() != record['fileBytesSha256']:
        raise ValueError('投影Shader准确区间身份改变：' + str(shader))
    text = raw.decode('utf-8-sig')
    if not re.search(r'// hash:\s*' + re.escape(record['hash64']) + r'\b', text):
        raise ValueError('投影Shader原DXBC hash不符')
    return T.parse_subprogram(text.replace('\r\n', '\n'))


def _flatten_material_matrices(sub):
    params = sub['bind']['cb']['UnityPerMaterial']['params']
    flattened = []
    for parameter in params:
        if parameter['kind'] == 'V':
            flattened.append(parameter)
        elif parameter['arr'] == 0 and parameter['dim'] == 4:
            for row in range(4):
                flattened.append(dict(parameter, kind='V', arr=0, dim=4,
                    name=parameter['name'] + '_R' + str(row), offset=parameter['offset'] + 16 * row))
        else:
            raise ValueError('投影材质存在未支持的源矩阵/数组：' + parameter['name'])
    sub['bind']['cb']['UnityPerMaterial']['params'] = flattened


def _native_cb(sub):
    sub['bind']['cbbind'][14] = 'GGYGOProjectedInputs'
    names = ['ReceiverU', 'ReceiverNormal', 'SourceLocal']
    sub['bind']['cb']['GGYGOProjectedInputs'] = dict(size=48,
        params=[dict(kind='V', name=name, offset=index * 16, dim=4, arr=0, type=0)
                for index, name in enumerate(names)])


def _lower_decal(original, hash64):
    sub = deepcopy(original)
    _flatten_material_matrices(sub)
    _native_cb(sub)
    a, cut = sub['asm'], DECAL_CUTS[hash64]
    replacements, inserts = {}, {}
    # 源CameraNormal.a是源receiver资格；此移植显式采用UE的ReceivesDecals。
    n = cut['normal_sample']
    if not a[n].startswith('sample_') or a[n + 4] != 'ret' or a[n + 5] != 'endif':
        raise ValueError('源Decal receiver资格块边界改变')
    replacements[n] = (n + 6, ['mov r1.xyzw, cb14[1].xyzw'])
    start, end = cut['projection']
    if not a[start].startswith('sample_l_') or not a[end - 1].startswith('mul '):
        raise ValueError('源Decal深度重建/投影块边界改变')
    local = cut['local']
    projection = (['mov ' + cut['world'] + ', cb14[0].xyzx'] if cut['world'] else [])
    projection += ['mov ' + local + ', cb14[2].' + ('xyxz' if local.endswith('xyw') else 'xyzx'),
                   'mul ' + local + ', ' + local.split('.')[0] + '.'
                   + ('xywx' if local.endswith('xyw') else 'xyzx')
                   + ', v7.' + ('xyxz' if local.endswith('xyw') else 'xyzx')]
    replacements[start] = (end, projection)
    pbr = 'normal_end' in cut
    if pbr:
        # Raw albedo/normal/metallic/roughness在源场景混合和lighting之前取出。
        inserts[cut['main']] = ['mov o1.xyz, ' + cut['base']]
        normal = cut['normal']
        inserts[cut['normal_end']] = ['mov o3.xy, ' + normal, 'mov o3.z, ' + cut['normal_z']]
        receiver_start, receiver_end = cut['receiver']
        roughness = a[cut['roughness']]
        metallic = 'r3.w' if hash64 == '6390ece1999f1286' else 'r7.x'
        rough = 'r4.x' if hash64 == '6390ece1999f1286' else 'r7.y'
        replacements[receiver_start] = (receiver_end, [roughness,
            'mov o2.x, ' + metallic, 'mov o2.y, ' + rough])
        # 源receiver albedo混合由UE DBuffer合成承担；不能采尚未生产的GBuffer。
        replacements[cut['emission_end'] + 1] = (cut['emission_end'] + 3, [])
        replacements[cut['opacity_end'] + 1] = (cut['lighting_tail'], [
            'mul o4.xyz, ' + cut['emission'] + ', ' + cut['emission_fade']])
        # 保留源alpha的脚本fade/VerticalAlphaFade，颜色由原生PBR负责。
        tail_end = cut['lighting_tail'] + 5
        replacements[tail_end] = (len(a), ['mov o0.w, ' + cut['alpha'], 'ret'])
        a = [x for x in a]  # 声明新增的是Custom局部输出，不是硬件MRT。
        declaration = next(i for i, value in enumerate(a) if value.startswith('dcl_output '))
        inserts[declaration] = inserts.get(declaration, []) + [
            'dcl_output o1.xyz', 'dcl_output o2.xy', 'dcl_output o3.xyz', 'dcl_output o4.xyz']
    result, index = [], 0
    while index < len(a):
        if index in replacements:
            end, block = replacements[index]
            result.extend(block)
            index = end
            continue
        instruction = a[index]
        # 本项目明确两个源时间组都取真实System.Age；在ASM边界合并，
        # 避免生成一个会被HLSL优化掉、却被作者误当必需的IgnoreTimeScale参数。
        if re.fullmatch(r'movc (r\d+\.[xyzw]), r\d+\.[xyzw], cb0\[15\]\.x, cb0\[18\]\.y', instruction):
            result.append('mov ' + instruction.split(',')[0].split()[1] + ', cb0[15].x')
            index += 1
            continue
        # 仅准确透明无影响的early-return改为discard；其它ret仍由translator拒绝。
        if instruction == 'mov o0.xyzw, l(0,0,0,1.000000)' and a[index + 1] == 'ret':
            result.append('discard_nz l(0xffffffff)')
            index += 2
            continue
        result.append(instruction)
        result.extend(inserts.get(index, []))
        index += 1
    sub['asm'] = result
    return sub


def _translate(sub, outputs, prefix, provider):
    discovery = T.translate(sub, prefix, dict(provider, __discover__=True), outputs)
    global_rows = {}
    actual = dict(provider)
    for name, row, component in discovery['missing']:
        if row == 'dyn':
            raise ValueError('投影程序缺动态场景数组提供方：' + name)
        global_rows.setdefault(name, set()).add(row)
    for name, rows in global_rows.items():
        actual[name] = dict(rows=['Global_' + name.lstrip('_') + '_R' + str(i)
                                 for i in range(max(rows) + 1)])
    translated = T.translate(sub, prefix, actual, outputs)
    return translated, {name: sorted(rows) for name, rows in global_rows.items()}


def make_decal_program(original, vertex, hash64):
    """FP表面切出与原VP payload计算；原VP选择依据另由计划准入。"""
    sub = _lower_decal(original, hash64)
    provider = {'ReceiverU': dict(rows=['float4(ReceiverU,1)']),
                'ReceiverNormal': dict(rows=['ReceiverNormal']),
                'SourceLocal': dict(rows=['float4(SourceLocal,1)']),
                '_WorldSpaceCameraPos': dict(rows=['float4(CameraU,1)']),
                '_GlobalTimeParamsA': dict(rows=['UEFX_SystemAge.xxxx'] * 4),
                '_GlobalTimeParamsB': dict(rows=['UEFX_SystemAge.xxxx'] * 4)}
    cut = DECAL_CUTS[hash64]
    pbr = 'normal_end' in cut
    wanted = {0: 'w', 1: 'xyz', 2: 'xy', 3: 'xyz', 4: 'xyz'} if pbr else {0: 'xyzw'}
    fp, globals_fp = _translate(sub, wanted, 'p_', provider)
    required = {}
    for register, component in fp['live_inputs']:
        register = int(register[1:])
        if register != 0:
            required.setdefault(register, set()).add(component)
    vs = deepcopy(vertex)
    _flatten_material_matrices(vs)
    vp, globals_vp = _translate(vs, {r: ''.join(sorted(c)) for r, c in required.items()}, 'v_', {})
    if globals_vp or vp['textures']:
        raise ValueError('Decal活跃VP超出已核粒子payload合同')
    values = {1: {c: 'UEFX_SourceColor.' + c for c in 'xyzw'},
              2: dict(x='UEFX_SourceCenter.x', y='UEFX_SourceCenter.y', z='UEFX_SourceCenter.z', w='UEFX_SourceSize.x'),
              3: dict(x='UEFX_SourceSize.y', y='UEFX_SourceSize.z'),
              4: dict(y='UEFX_SourceStableRandom.x', z='UEFX_SourceStableRandom.y', w='UEFX_SourceStableRandom.z'),
              5: dict(x='UEFX_SourceStableRandom.w', y='UEFX_SourceCustom1.x', z='UEFX_SourceCustom1.y', w='UEFX_SourceCustom1.z'),
              6: dict(x='UEFX_SourceCustom1.w', y='UEFX_SourceCustom2.x', z='UEFX_SourceCustom2.y', w='UEFX_SourceCustom2.z'),
              7: dict(x='UEFX_SourceCustom2.w')}
    active_vp = sorted({int(reg[1:]) for reg, _ in vp['live_inputs']})
    if set(active_vp) - set(values):
        raise ValueError('Decal存在尚无实际流提供者的VP输入')
    declarations = ['uint4 v_v%d=(uint4)0;' % r for r in active_vp]
    for register, component in vp['live_inputs']:
        index = int(register[1:])
        if component not in values[index]:
            raise ValueError('Decal存在尚未映射的活跃VP流分量')
        declarations.append('v_v%d.%s=asuint(%s);' % (index, component, values[index][component]))
    varying_declarations = ['uint4 p_v%d=v_o%d;' % (r, r) for r in sorted(required)]
    # VP先算o2..o7，FP按同一插值语义取值；Decal payload为每粒子常量。
    code = PRELUDE + '\n'.join(declarations) + '\n' + vp['code'] + '\n'
    code += '\n'.join(varying_declarations) + '\n' + fp['code']
    if pbr:
        code += '\nBaseColorOut=asfloat(p_o1.xyz);\nMetallicOut=asfloat(p_o2.x);\nRoughnessOut=asfloat(p_o2.y);\n'
        code += 'float3 TN=asfloat(p_o3.xyz);\n'
        code += 'float3 NX=normalize(_ParticleDecalLocalToWorldMatrix_R0.xyz);\n'
        code += 'float3 NY=normalize(_ParticleDecalLocalToWorldMatrix_R1.xyz);\n'
        code += 'float3 NZ=normalize(_ParticleDecalLocalToWorldMatrix_R2.xyz);\n'
        code += 'NormalOut=normalize(F.U(NX*TN.x+NZ*TN.y+NY*TN.z));\n'
        code += 'OpacityOut=asfloat(p_o0.w);\nreturn asfloat(p_o4.xyz);\n'
        outputs = {'BaseColorOut': 3, 'MetallicOut': 1, 'RoughnessOut': 1, 'NormalOut': 3, 'OpacityOut': 1}
    else:
        # 原o0是premultiplied RGB + transmittance；保留源coverage，显式解预乘后接Native opacity。
        code += '\nOpacityOut=asfloat(p_' + cut['alpha'] + ');\n'
        code += 'return OpacityOut>0.0?asfloat(p_o0.xyz)/OpacityOut:float3(0,0,0);\n'
        outputs = {'OpacityOut': 1}
    params = dict(vp['mat_params'])
    params.update(fp['mat_params'])
    if pbr:
        params.update({'_ParticleDecalLocalToWorldMatrix_R' + str(i): 4 for i in range(3)})
    external = dict(RAW_STREAMS, UEFX_SystemAge=1, **{'UEFX_ProjectionRow' + str(i): 4 for i in range(3)})
    external = {name: dim for name, dim in external.items() if re.search(r'\b' + name + r'\b', code)}
    for name, rows in globals_fp.items():
        external.update({'Global_' + name.lstrip('_') + '_R' + str(row): 4 for row in rows})
    return dict(code=code, parameters=external, material_params=params, globals=globals_fp,
                textures=fp['textures'], builtins=sorted(NATIVE_INPUTS), outputs=outputs,
                surface='native_pbr' if pbr else 'source_unlit',
                source_lighting_replaced=pbr, source_framebuffer_encoding_replaced=True)


def _prop_varyings(sub, translated):
    # 按实际FP signature，v5是TEXCOORD5原VertexColor；不误接VP o6的未读SH。
    semantics = {
        ('TEXCOORD', 0): 'asuint(float4(UV0.x,1.0-UV0.y,0,0))',
        ('TEXCOORD', 2): 'asuint(float4(F.U(normalize(UEFX_NormalWS)),PosU.x))',
        ('TEXCOORD', 3): 'asuint(float4(F.U(normalize(UEFX_TangentWS)),PosU.y))',
        ('TEXCOORD', 4): 'asuint(float4(F.U(normalize(UEFX_BitangentWS)),PosU.z))',
        ('TEXCOORD', 5): 'asuint(VCol)',
        ('SV_POSITION', 0): 'asuint(float4(PixelPosition.xy,0,0))',
        ('SV_IsFrontFace', 0): 'uint4(FaceSign>0.0?1u:0u,0,0,0)',
    }
    active = {int(name[1:]) for name, component in translated['live_inputs']}
    lines = []
    for entry in sub['in']:
        if entry['reg'] not in active:
            continue
        key = entry['name'], entry['index']
        if key not in semantics:
            raise ValueError('Prop颜色/表面存在无实际Native提供方的活跃流：' + str(key))
        lines.append('uint4 p_v%d=%s;' % (entry['reg'], semantics[key]))
    return '\n'.join(lines)


def make_prop_program(original, role):
    sub = deepcopy(original)
    provider = {'_WorldSpaceCameraPos': dict(rows=['float4(CameraU,1)']),
                '_GlobalTimeParamsA': dict(rows=['UEFX_SystemAge.xxxx'] * 4),
                '_GlobalTimeParamsB': dict(rows=['UEFX_SystemAge.xxxx'] * 4),
                'unity_WorldToObject': dict(rows=['float4(UEFX_WorldToObjectColumn%d,0)' % i for i in range(3)])}
    if role == 'geometry':
        # 原o2.y为smoothness编码；此处在源编码边界取真实roughness。
        if sub['asm'][101] != 'add o2.y, -r0.w, l(1.000000)' or not sub['asm'][103].startswith('mad o3.xyz, r3.xyzx,'):
            raise ValueError('Prop Geometry源表面编码边界改变')
        sub['asm'][101] = 'mov o2.y, r0.w'
        sub['asm'][103] = 'mov o3.xyz, r3.xyzx'
        translated, global_rows = _translate(sub, {1: 'xyz', 2: 'yz', 3: 'xyz'}, 'p_', provider)
        tail = '\nMetallicOut=asfloat(p_o2.z);\nRoughnessOut=asfloat(p_o2.y);\n'
        tail += 'NormalOut=F.U(asfloat(p_o3.xyz));\nCoverageOut=1.0;\nreturn asfloat(p_o1.xyz);\n'
        outputs = dict(MetallicOut=1, RoughnessOut=1, NormalOut=3, CoverageOut=1)
    elif role == 'forward':
        if '_FlowTex' in {item['name'] for item in sub['bind']['tex'].values()}:
            # Source object-space point用真实原mesh-local插值，避免绝对坐标float精度与错误TRS逆矩阵。
            if not sub['asm'][69].startswith('mul r2.xyz, v3.wwww, cb1[5].xyzx') or not sub['asm'][72].startswith('add r2.xyz, r2.xyzx, cb1[7].xyzx'):
                raise ValueError('Prop Flow object-space位置边界改变')
            _native_cb(sub)
            sub['bind']['cb']['GGYGOProjectedInputs']['params'][0]['name'] = 'SourceMeshLocalPosition'
            sub['asm'][69:73] = ['mov r2.xyz, cb14[0].xyzx']
            provider['SourceMeshLocalPosition'] = dict(rows=['float4(UEFX_MeshLocalPosition,1)'])
        translated, global_rows = _translate(sub, {0: 'xyz'}, 'p_', provider)
        tail, outputs = '\nreturn asfloat(p_o0.xyz);\n', {}
    else:
        raise ValueError('未知Prop消费者role')
    prelude = PRELUDE.split('float3 ReceiverU=', 1)[0]
    prelude += '\nfloat3 PosU=float3(0,0,0);\nfloat3 CameraU=F.U(CameraVectorWS)*0.01;\n'
    code = prelude + _prop_varyings(sub, translated) + '\n' + translated['code'] + tail
    names = ['CameraVectorWS', 'UV0', 'PixelPosition', 'VCol', 'FaceSign', 'UEFX_SystemAge',
             'UEFX_NormalWS', 'UEFX_TangentWS', 'UEFX_BitangentWS',
             'UEFX_MeshLocalPosition', 'UEFX_WorldToObjectColumn0',
             'UEFX_WorldToObjectColumn1', 'UEFX_WorldToObjectColumn2']
    builtins = [name for name in names if re.search(r'\b' + name + r'\b', code)]
    parameters = {'Global_' + name.lstrip('_') + '_R' + str(row): 4
                  for name, rows in global_rows.items() for row in rows}
    return dict(code=code, outputs=outputs, parameters=parameters, material_params=dict(translated['mat_params']),
                textures=translated['textures'], builtins=builtins, globals=global_rows,
                surface='native_prop_pbr' if role == 'geometry' else 'source_prop_additive')


def _shader_defaults(shader):
    header = []
    with Path(shader).open(encoding='utf-8-sig') as stream:
        for line in stream:
            if line.strip().startswith('SubShader'):
                break
            header.append(line)
    return {name: item['default'] for name, item in T.parse_shader(''.join(header))['props'].items()
            if item['default'] is not None}


def generate():
    policy = json.loads(POLICY.read_text(encoding='utf-8-sig'))
    evidence = policy['shader_choices'][DECAL_SID]['source_evidence']
    shader = evidence['sourceShader']['path']
    candidate = evidence['sharedVertexCandidate']
    vertex = read_program(shader, candidate)
    defaults = _shader_defaults(shader)
    programs = {}
    for material in evidence['materials'].values():
        records = material['programCandidates']['fp']
        if len(records) != 1:
            raise ValueError('Decal缺唯一准确FP，不选择其它材质')
        record = records[0]
        hash64 = record['hash64']
        if hash64 not in programs:
            program = make_decal_program(read_program(shader, record), vertex, hash64)
            programs[hash64] = dict(program, source_shader=evidence['sourceShader'],
                source_fragment=record, source_vertex_candidate=candidate,
                material_defaults={name: defaults[name] for name in program['material_params'] if name in defaults},
                source_stage_pair_certified=False,
                stage_pair_requirement='准确Resource stage映射；共享候选不代原VP/FP配对')
    prop_evidence = policy['shader_choices'][PROP_SID]['source_evidence']
    prop_shader = prop_evidence['sourceShader']['path']
    prop_defaults = _shader_defaults(prop_shader)
    # 即使Native负责velocity，原o1程序和原VP仍保身份及完整算法，不能丢成颜色的unused pin。
    geometry_original = read_program(prop_shader, PROP_GEOMETRY['fp'])
    read_program(prop_shader, PROP_GEOMETRY['vp'])
    prop = {}
    for pid, item in prop_evidence['materials'].items():
        vertex_record = item['programCandidates']['vp'][0]
        forward_record = item['programCandidates']['fp'][0]
        read_program(prop_shader, vertex_record)
        original = read_program(prop_shader, forward_record)
        forward = make_prop_program(original, 'forward')
        geometry = make_prop_program(geometry_original, 'geometry')
        for program in (forward, geometry):
            program['material_defaults'] = {name: prop_defaults[name] for name in program['material_params'] if name in prop_defaults}
        prop[pid] = dict(geometry=geometry, forward=forward, source_shader=prop_evidence['sourceShader'],
            source_geometry=PROP_GEOMETRY, source_forward=dict(vp=vertex_record, fp=forward_record),
            source_stage_pair_certified=pid == '5017413851355136532',
            source_geometry_selection='ExactSourceKeywords' if pid == '5017413851355136532'
                                      else 'ProjectConfiguredGeometryWithoutForwardOnlyFlow',
            source_velocity=dict(role='NativePreciseVelocity',
                original_fragment_asm=original['asm'], original_vertex_asm=read_program(prop_shader, vertex_record)['asm'],
                original_switch='unity_MotionVectorsParams.y',
                native_switch='Configured MeshRenderer.MotionVectorSetting Precise/Disable',
                required='Actual previous source pose and native previous TRS, current/previous WPO use separate real snapshots',
                encoding='NativeVelocityShader replaces source sign*sqrt+bias MRT encoding'))
    PROGRAM_FILE.write_text(json.dumps(dict(schema='projected_fx_programs/v1', decal=programs, prop=prop),
        ensure_ascii=False, indent=1, allow_nan=False) + '\n', encoding='utf-8')
    print(str(PROGRAM_FILE), PROGRAM_FILE.stat().st_size)


if __name__ == '__main__':
    generate()
