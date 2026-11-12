"""@file gen_nap_avatar_simple_hlsl.py
@brief 从准确NapAvatarSimple程序生成两MID的表面与轮廓Custom合同。

复用原DXBC位模式翻译器；仅实体缓冲、影图生产者、MRT消费和轮廓几何采用明确UE配置。
原程序与源渲染状态只读保留，生成物供原create-only材质作者消费，不启动UE或测试。
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re

import zzz_dxbc_hlsl as T

HERE = Path(__file__).resolve().parent
BASE = Path('F:/AnimeStudio/Exports/ZZZ/Pyrois_SkillFX_Evidence')
SHADER = BASE / 'Assets/3107640275/CAB-1c2eeb9738e76de5164cd32e39d127a5/Shader/7393264008099488228.shader'
WEAPON = '-2538972164699361705'
GHOST = '1604852325208651105'
GHOST_KEYWORDS = ('_EXTRA_DITHER_EFFECT', '_FX_CLIP', '_FX_UNCLIP_SCREEN_IMAGE_OVERRIDE_2_TONE', '_OVERRIDE_OUTLINE')
PROGRAMS = {
    'weapon_surface': ('CharacterToonDeferred', 'f37170516fe0dd4a', ()),
    'weapon_outline': ('CharacterOutlineDeferred', 'd5375af50b665698', ()),
    'ghost_surface': ('CharacterToonDeferred', '2ebb0973fd769c43', GHOST_KEYWORDS[:-1]),
    'ghost_outline': ('CharacterOutlineDeferred', '2c8bc9897724f3be',
                      ('_EXTRA_DITHER_EFFECT', '_FX_CLIP', '_OVERRIDE_OUTLINE')),
}
VERTEX_HASHES = {'weapon_surface': '717c463daafb81db', 'ghost_surface': '717c463daafb81db',
                 'weapon_outline': 'b320106e4eb08ad4', 'ghost_outline': '27898dbb6d3157dc'}
PRELUDE = r'''// 由gen_nap_avatar_simple_hlsl.py从准确DXBC生成。
struct SimpleFunctions {
 float3 U(float3 v) { return float3(v.x,v.z,v.y); }
 float4 S(Texture2D T, SamplerState Smp, float2 uv) {
  return Texture2DSample(T,Smp,float2(uv.x,1.0-uv.y)); }
 float4 SL(Texture2D T, SamplerState Smp, float2 uv, float lod) {
  return Texture2DSampleLevel(T,Smp,float2(uv.x,1.0-uv.y),lod); }
 float4 SB(Texture2D T, SamplerState Smp, float2 uv, float bias) {
  return Texture2DSampleBias(T,Smp,float2(uv.x,1.0-uv.y),bias); }
};
SimpleFunctions F;
float3 PosU=F.U(WorldPos)*0.01;
float3 CameraU=F.U(CameraPos)*0.01;
float3 N=normalize(F.U(Parameters.TangentToWorld[2]));
float3 TangentU=normalize(F.U(Parameters.TangentToWorld[0]));
float3 BitangentU=normalize(F.U(Parameters.TangentToWorld[1]))*NormalYSign.x;
float3 ToLightU=normalize(F.U(KeyLightDirectionWS.xyz));
float3 RightU=F.U(normalize(View.ViewToTranslatedWorld[0].xyz));
float3 UpU=F.U(normalize(View.ViewToTranslatedWorld[1].xyz));
float3 ForwardU=F.U(normalize(View.ViewToTranslatedWorld[2].xyz));
float4 MainLight=float4(KeyLightColor.rgb*SceneLightStrength,1);
float Coverage=VertexPartVisibility;
'''
BUILTINS = {'WorldPos', 'CameraPos', 'UV0', 'UV2', 'UV3', 'VCol', 'FaceSign', 'PixelPosition',
            'VertexAdditionalLight', 'VertexPartVisibility', 'VertexStyle', 'EffectAge'}
PARAMETERS = {'KeyLightDirectionWS': 4, 'KeyLightColor': 4, 'SceneLightStrength': 1,
              'KeyLightVisibility': 1, 'NormalYSign': 4,
              'EntityParams': 4, 'EntityAmbient': 4, 'KeyLightProxyDistanceMeters': 1,
              'KeyLightProxyRadiusMeters': 1}


def _programs():
    """精确匹配pass、阶段关键字与DXBC hash，不从文件名或首次候选猜选择。"""
    found, vertex = {}, set()
    part = stage = None
    current = None

    def finish():
        if current is None or current['api'] != 'd3d11':
            return
        text = ''.join(current['lines'])
        for name, (pass_name, hash64, keywords) in PROGRAMS.items():
            if current['pass'] != pass_name or current['keywords'] != set(keywords):
                continue
            expected = hash64 if current['stage'] == 'fp' else VERTEX_HASHES[name]
            if current['hash'] != expected:
                raise ValueError('准确Simple程序身份改变：' + name + '/' + current['stage'])
            if current['stage'] == 'vp':
                vertex.add(name)
                continue
            if name in found:
                raise ValueError('重复Simple片元候选：' + name)
            found[name] = dict(program=T.parse_subprogram(text),
                source=dict(path=str(SHADER), line_start=current['line'],
                            sha256=hashlib.sha256(text.encode('utf-8')).hexdigest(),
                            hash64=expected, pass_name=pass_name, local_keywords=sorted(keywords)))

    with SHADER.open(encoding='utf-8-sig', newline='') as stream:
        for number, line in enumerate(stream, 1):
            s = line.strip()
            if s.startswith('SubProgram "'):
                finish()
                current = dict(api=s.split('"')[1].strip(), stage=stage, **{'pass': part},
                               keywords=set(), hash=None, line=number, lines=[])
            if s.startswith('Name "'):
                part = s.split('"')[1]
            elif s.startswith('Program "'):
                stage = s.split('"')[1]
            if current is not None:
                current['lines'].append(line)
                if s.startswith(('Keywords {', 'Local Keywords {')):
                    current['keywords'].update(re.findall(r'"([^"]+)"', s))
                if s.startswith('"// hash:'):
                    current['hash'] = s.split(': ')[1]
        finish()
    if set(found) != set(PROGRAMS) or vertex != set(PROGRAMS):
        raise ValueError('缺准确Simple VP/FP来源')
    return found


def _lower(program, role):
    """只替换已核资源边界，影图后的ReceiveShadows/实体权重混合仍走原指令。"""
    sub = deepcopy(program)
    asm = sub['asm']
    start = next(i for i, s in enumerate(asm) if re.fullmatch(r'lt r\d+\.\w, l\(0.500000\), cb0\[22\]\.x', s))
    sample = next(i for i in range(start, len(asm)) if asm[i].startswith('sample_c_lz_'))
    shadow = re.search(r' (r\d+\.\w),', asm[sample]).group(1)
    valid = next(i for i in range(sample, len(asm)) if asm[i].startswith('movc ' + shadow + ',')
                 and 'l(1.000000)' in asm[i])
    end = next(i for i in range(valid, len(asm)) if asm[i] == 'else')
    if asm[start + 1].split()[0] != 'if_nz' or asm[end + 2] != 'endif':
        raise ValueError('Simple原阴影块边界改变')
    asm[start:end + 3] = ['mov ' + shadow + ', cb14[8].x'] + asm[valid + 1:end]
    # 显式单角色entity producer；本材质不伪装Unity的全局实体表或选择另一个实体。
    for i, instruction in enumerate(asm):
        if not instruction.startswith('ld_structured_'):
            continue
        match = re.fullmatch(r'ld_structured_indexable\(structured_buffer, stride=128\)'
                            r'\(mixed,mixed,mixed,mixed\) (r\d+\.[xyzw]+), r\d+\.\w, l\((\d+)\), t1\.([xyzw]+)', instruction)
        if not match or int(match[2]) not in (0, 16, 32, 112):
            raise ValueError('Simple未支持的真实实体字段：' + instruction)
        asm[i] = 'mov %s, cb14[%d].%s' % (match[1], int(match[2]) // 16, match[3])
    params = [('EntityLightColorRadius', 0), ('EntityLightPositionWeight', 16),
              ('EntityLightWeight', 32), ('EntityAmbientInput', 112), ('EntityShadowVisibility', 128)]
    sub['bind']['cbbind'][14] = 'GGYGOEntityInputs'
    sub['bind']['cb']['GGYGOEntityInputs'] = dict(size=144,
        params=[dict(kind='V', name=n, offset=o, dim=4, arr=0, type=0) for n, o in params])
    if role == 'surface':
        root = next(i for i, s in enumerate(asm) if s.startswith('sqrt ') and
                    i + 2 < len(asm) and asm[i + 2].startswith('min o1.xyz,'))
        reg = asm[root].split(',')[0].split()[1]
        if not asm[root + 1].startswith('mul ' + reg + ','):
            raise ValueError('Simple原Rim编码边界改变')
        asm[root:root + 3] = ['mov o1.xyz, ' + reg]
    return sub


def _provider():
    rows = {
        '_WorldSpaceCameraPos': ['float4(CameraU,0)'],
        '_AvatarMainLightColor': ['MainLight'],
        '_RenderedEntityCount': ['asfloat(uint4(1,0,0,0))'],
        '_PackedParams1': ['float4(0,0,0,0)'],
        'EntityLightColorRadius': ['float4(MainLight.rgb,KeyLightProxyRadiusMeters)'],
        'EntityLightPositionWeight': ['float4(PosU+ToLightU*KeyLightProxyDistanceMeters,EntityParams.x)'],
        'EntityLightWeight': ['float4(EntityParams.y,0,0,0)'],
        'EntityAmbientInput': ['EntityAmbient'],
        'EntityShadowVisibility': ['KeyLightVisibility.xxxx'],
        'unity_OrthoParams': ['float4(0,0,0,View.ViewToClip[3][3])'],
        'unity_CameraProjection': ['View.ViewToClip[0]', 'View.ViewToClip[1]',
                                   'View.ViewToClip[2]', 'View.ViewToClip[3]'],
        'unity_MatrixV': ['float4(RightU.x,UpU.x,-ForwardU.x,0)',
                          'float4(RightU.y,UpU.y,-ForwardU.y,0)',
                          'float4(RightU.z,UpU.z,-ForwardU.z,0)',
                          'float4(-dot(RightU,CameraU),-dot(UpU,CameraU),dot(ForwardU,CameraU),1)'],
        'unity_MatrixInvV': ['float4(RightU,0)', 'float4(UpU,0)', 'float4(-ForwardU,0)', 'float4(CameraU,1)'],
        '_ScreenSize': ['View.ViewSizeAndInvSize'],
        '_GlobalTimeParamsB': ['EffectAge.xxxx'] * 4,
    }
    return {name: dict(rows=value) for name, value in rows.items()}


def _varyings(sub, translated, role):
    live = {}
    for register, component in translated['live_inputs']:
        live.setdefault(int(register[1:]), set()).add(component)
    if role == 'surface':
        # 源o7.y/z来自顶点色的分组位和alpha，保DXBC布尔位的数值含义。
        values = dict(TEXCOORD={
            0: 'float4(UV0.x,1-UV0.y,UV3.x,1-UV3.y)',
            1: 'float4(UV2.x,1-UV2.y,0,0)',
            2: 'float4(N,PosU.x)', 3: 'float4(TangentU,PosU.y)', 4: 'float4(BitangentU,PosU.z)',
            7: 'float4(1,VertexStyle.xy,0)',
            8: 'float4(VertexAdditionalLight,0)'})
    else:
        values = dict(TEXCOORD={
            0: 'float4(float2(UV0.x,1-UV0.y)*_MainTex_ST.xy+_MainTex_ST.zw,0,0)',
            3: 'float4(0,0,UV2.x,1-UV2.y)',
            4: 'float4(float2(UV3.x,1-UV3.y)*_MainTex_ST.xy+_MainTex_ST.zw,0,0)',
            5: 'float4(PosU,0)', 7: 'float4(N,0)', 8: 'float4(VertexAdditionalLight,0)'})
    declarations = []
    for signature in sub['in']:
        reg, semantic, index = signature['reg'], signature['name'], signature['index']
        if reg not in live:
            continue
        if semantic == 'SV_IsFrontFace':
            expression = 'uint4(FaceSign>0?1u:0u,0,0,0)'
        elif semantic == 'SV_POSITION':
            expression = 'asuint(float4(PixelPosition.xy,0,0))'
        elif semantic in values and index in values[semantic]:
            expression = 'asuint(' + values[semantic][index] + ')'
        else:
            raise ValueError('Simple尚无实际提供者的活跃顶点流：' + str(signature))
        declarations.append('uint4 p_v%d = %s;' % (reg, expression))
    return '\n'.join(declarations)


def generate():
    output = {}
    for name, selected in _programs().items():
        role = name.split('_')[1]
        sub = _lower(selected['program'], role)
        provider = _provider()
        # 未绑定的Shader默认贴图沿原Properties的明确默认值，实际PPtr纹理仍由计划逐项核对。
        provider['__textures__'] = {'_MainTex': 'float4(1,1,1,1)', '_LightTex': 'float4(0.5,0.5,0.5,0.5)',
                                    '_OtherDataTex': 'float4(1,1,1,1)', '_OtherDataTex2': 'float4(1,1,1,1)'}
        provider['__discover__'] = True
        needed = {0: 'xyz', 1: 'xyzw'} if role == 'surface' else {0: 'xyz'}
        discovery = T.translate(sub, 'p_', provider, needed)
        globals_ = {}
        for global_name, row, component in discovery['missing']:
            if row == 'dyn':
                raise ValueError('Simple未绑定动态全局数组：' + global_name)
            globals_.setdefault(global_name, set()).add(row)
        for global_name, used_rows in globals_.items():
            provider[global_name] = dict(rows=['Global_' + global_name.lstrip('_') + '_R' + str(i)
                                               for i in range(max(used_rows) + 1)])
        provider.pop('__discover__')
        translated = T.translate(sub, 'p_', provider, needed)
        code = translated['code'].replace('clip(-1.0)', 'Coverage=0.0')
        tail = '\nCoverageOut=Coverage;\n'
        if role == 'surface':
            tail += 'RimRaw=asfloat(p_o1.xyz); BloomWeight=asfloat(p_o1.w);\n'
        tail += 'return asfloat(p_o0.xyz);\n'
        code = PRELUDE + _varyings(sub, translated, role) + '\n' + code + tail
        parameters = dict(PARAMETERS)
        for global_name, used_rows in globals_.items():
            parameters.update({'Global_' + global_name.lstrip('_') + '_R' + str(row): 4 for row in used_rows})
        if role == 'outline':
            parameters['_MainTex_ST'] = 4
        # 未消费的公有输入不制造额外Custom引脚；动态绑定名由完整计划统一保留。
        parameters = {n: d for n, d in parameters.items() if re.search(r'\b' + re.escape(n) + r'\b', code)}
        output[name] = dict(code=code, source=selected['source'], vertex_hash64=VERTEX_HASHES[name],
            material_params=dict(translated['mat_params']), parameters=parameters,
            textures=translated['textures'], builtins=sorted(BUILTINS),
            global_rows={n: sorted(rows) for n, rows in globals_.items()},
            outputs=['CoverageOut', 'RimRaw', 'BloomWeight'] if role == 'surface' else ['CoverageOut'])
    target = HERE / 'nap_avatar_simple_programs.json'
    target.write_text(json.dumps(output, ensure_ascii=False, indent=1, allow_nan=False) + '\n', encoding='utf-8')
    print(str(target), target.stat().st_size)


if __name__ == '__main__':
    generate()
