"""离线生成 M_Pyrois_Toon 的 Custom 节点 HLSL（不依赖 Unreal）。

输入：
- AnimeStudio 导出的 miHoYo/Character/NapAvatarStandard 可读文本（D3D11 反汇编）；
- 同一 Shader 的原始序列化 .dat，用其中 CharacterToonDeferred Pass 的反射表把 cbN[i] 还原成属性名。

输出（与本脚本同目录）：
- nap_avatar_toon.hlsl：CharacterToonDeferred 在 {_NAP_SHADER_QUALITY_HIGH, _MATCAP_ON} 变体下的像素逻辑；
- nap_avatar_toon_inputs.json：Custom 节点的输入顺序与类别，以及 Properties 中声明为 Color 的属性名。

替换规则（其余代码逐行保留）：
- 运动矢量与 GBuffer 标记位输出删除；
- 逐对象阴影与级联阴影采样替换为组件提供的 KeyLightVisibility；
- 角色实体缓冲 t1 替换为材质参数：主光颜色/方向来自组件，其余字段来自 Entity* 参数；
- t3/t4/t5/t6 换成 MainTex/LightTex/OtherDataTex/OtherDataTex2，t7 MatCap 数组换成五张独立贴图；
- 主色、编码前边缘光和 Bloom 亮度权重分别输出到 Custom 引脚，由材质图配置合成；不是 UE MRT。

用法：python gen_nap_avatar_hlsl.py
"""
import json
import re
import struct
from pathlib import Path

HERE = Path(__file__).resolve().parent
SHADER_DIR = Path(r"F:\AnimeStudio\Exports\Shader\ZZZ_20260925")
TEXT_PATH = SHADER_DIR / "PyriosFullText/miHoYo_Character_NapAvatarStandard.shader"
DAT_PATH = SHADER_DIR / "PyriosRaw/miHoYo_Character_NapAvatarStandard.dat"
PASS_NAME = "CharacterToonDeferred"
# 原始 DXBC 的 hash；该片元的 and r5.w, r3.w, l(0x00000001) 用作布尔分组标志。
SKIN_FLAG_FRAGMENT_HASH = "9225f290963128b1"
# 两个 _FX_UNCLIP_* 变体打开屏幕贴图（_ScreenImage）、二次自发光与特殊武器自发光分支；
# Pyrios 胸口和右臂的蓝光就来自 Body_1 的 _ScreenImage / _SpecialWeaponEmission。
KEYWORDS = {"_NAP_SHADER_QUALITY_HIGH", "_MATCAP_ON",
            "_FX_UNCLIP_SCREEN_IMAGE_OVERRIDE_2_TONE", "_FX_UNCLIP_SECONDARY_EMISSION_RIM_GLOW"}
DISABLED_BLOCKS = ("_OverrideRimGlow", "_Override2Tone")
TEXTURE_REGISTERS = {
    "t3": "MainTex", "t4": "LightTex", "t5": "OtherDataTex", "t6": "OtherDataTex2",
    "t8": "SecondaryEmissionTex", "t9": "SecondaryEmissionMaskTex",
    "t10": "SpecialWeaponEmissionTex", "t11": "SpecialWeaponEmissionMaskTex",
    "t12": "ScreenTex", "t13": "ScreenMask",
}
OUT_HLSL = HERE / "nap_avatar_toon.hlsl"
OUT_INPUTS = HERE / "nap_avatar_toon_inputs.json"

# 像素着色器的 cbuffer 槽位 -> 反射表里用来识别该 cbuffer 的特征名。
# cb4 是 UnityPerMaterial；片元与顶点程序的 UnityPerMaterial 布局相差 4 字节，用 _BumpScale 偏移区分。
CB_SIGNATURES = {
    "cb0": ("_CharacterAmbient", "_PostShallowTint", "_RenderedEntityCount", "_WorldSpaceCameraPos",
            "_GlobalTimeParamsA", "_GlobalTimeParamsB", "unity_MatrixV", "_MainLightPosition"),
    "cb1": ("unity_WorldTransformParams",),
    "cb2": ("_CascadeShadowSplitSpheres0",),
    "cb3": ("_PackedParams0", "_PerObjectShadowData"),
}
FRAGMENT_BUMPSCALE_OFFSET = 2244

# 角色实体缓冲 t1 的字节偏移 -> 替换表达式。
ENTITY_FIELDS = {
    0: "_AvatarMainLightColor.x", 4: "_AvatarMainLightColor.y", 8: "_AvatarMainLightColor.z", 12: "10000.0",
    16: "(r7.x + LightDirU.x * 1000.0)", 20: "(r7.y + LightDirU.y * 1000.0)",
    24: "(r7.z + LightDirU.z * 1000.0)", 28: "EntityParams.x",
    32: "EntityParams.y",
    96: "EntitySkinAmbient.x", 100: "EntitySkinAmbient.y", 104: "EntitySkinAmbient.z",
    112: "EntityAmbient.x", 116: "EntityAmbient.y", 120: "EntityAmbient.z",
}

# 由前导代码在函数内定义的名字，不作为 Custom 输入。
LOCAL_NAMES = {"_WorldSpaceCameraPos", "_AvatarMainLightColor"}
# 组件每帧写入的参数（ScalarParameter / VectorParameter），名字与 UGGYGOCharacterRenderComponent 一致。
COMPONENT_VECTORS = ("KeyLightDirectionWS", "KeyLightColor")
COMPONENT_SCALARS = ("SceneLightStrength", "KeyLightVisibility")
# 前导/替换代码引入的额外材质参数。
EXTRA_VECTORS = ("EntityParams", "EntityAmbient", "EntitySkinAmbient", "NormalYSign", "HighlightBleed",
                 "MC_Refract1", "MC_Refract2", "MC_Refract3", "MC_Refract4", "MC_Refract5",
                 "MC_Tint1", "MC_Tint2", "MC_Tint3", "MC_Tint4", "MC_Tint5",
                 "MC_A1", "MC_A2", "MC_A3", "MC_A4", "MC_A5",
                 "MC_B1", "MC_B2", "MC_B3", "MC_B4", "MC_B5")
TEXTURES = tuple(TEXTURE_REGISTERS.values()) + ("MatCapTex1", "MatCapTex2", "MatCapTex3", "MatCapTex4", "MatCapTex5")
BUILTINS = ("UV", "UV2", "Time", "WorldPos", "CameraPos", "VCol", "FaceSign")


def find_variant():
    """返回 (片元程序文本, Properties 块文本)。"""
    props, in_pass, prog, cur, found = [], False, None, None, None
    with TEXT_PATH.open(encoding="utf-8", errors="replace") as fh:
        in_props = False
        for line in fh:
            s = line.strip()
            if s.startswith("Properties {"):
                in_props = True
            elif in_props and s == "}":
                in_props = False
            elif in_props:
                props.append(s)
            if s.startswith('Name "'):
                in_pass = s == 'Name "%s"' % PASS_NAME
            if not in_pass:
                continue
            if s.startswith('Program "'):
                prog = s.split('"')[1]
            elif s.startswith('SubProgram "'):
                if found is not None:
                    break
                cur = {"prog": prog, "api": s.split('"')[1].strip(), "kw": set(), "lines": [line]}
            elif cur is not None:
                if s.startswith("Keywords {") or s.startswith("Local Keywords {"):
                    cur["kw"] |= set(re.findall(r'"([^"]+)"', s))
                cur["lines"].append(line)
                if cur["prog"] == "fp" and cur["api"] == "d3d11" and cur["kw"] == KEYWORDS and s.startswith('"// hash'):
                    found = cur
    if found is None:
        raise RuntimeError("未找到 %s 的片元变体 %s" % (PASS_NAME, sorted(KEYWORDS)))
    return "".join(found["lines"]), props


def parse_name_maps(blob):
    maps = []
    for m in re.finditer(rb"\x08\x00\x00\x00\$Globals", blob):
        o = m.start() - 4
        n = struct.unpack_from("<i", blob, o)[0]
        p, names = o + 4, {}
        for _ in range(n):
            ln = struct.unpack_from("<i", blob, p)[0]
            names[struct.unpack_from("<i", blob, p + 4 + ((ln + 3) & ~3))[0]] = blob[p + 4:p + 4 + ln].decode()
            p += 8 + ((ln + 3) & ~3)
        maps.append((o, p, names))
    return maps


def vector_runs(blob, names, start, end):
    """扫描 VectorParameter 记录序列：nameIndex, offset, arraySize, type(u8), dim(u8), pad。"""
    runs, i = [], start
    while i < end - 16:
        j, recs = i, []
        while j < end - 16:
            ni, off, arr = struct.unpack_from("<iii", blob, j)
            t, d = blob[j + 12], blob[j + 13]
            if ni in names and 0 <= off < 8192 and off % 4 == 0 and 0 <= arr < 256 and t <= 3 \
                    and 1 <= d <= 4 and blob[j + 14] == 0 and blob[j + 15] == 0:
                recs.append((names[ni], off, d))
                j += 16
            else:
                break
        if len(recs) >= 2:
            runs.append(recs)
            i = j
        else:
            i += 4
    return runs


def cbuffer_maps(material_props):
    blob = DAT_PATH.read_bytes()
    maps = parse_name_maps(blob)
    # 每个 Pass 一张名字表，CharacterToonDeferred 的表最大（数百个名字）。
    o, start, names = max(maps, key=lambda m: len(m[2]))
    end = min([m[0] for m in maps if m[0] > o] or [len(blob)])
    runs = vector_runs(blob, names, start, end)
    result = {}

    def merge(target, recs):
        for n, off, d in recs:
            if n in target and target[n] != (off, d):
                raise RuntimeError("cbuffer 布局冲突: %s %s vs %s" % (n, target[n], (off, d)))
            target.setdefault(n, (off, d))

    mat = {}
    for recs in runs:
        if len(recs) >= 6 and sum(n in material_props for n, _, _ in recs) >= 0.8 * len(recs) and \
                any(n == "_BumpScale" and off == FRAGMENT_BUMPSCALE_OFFSET for n, off, _ in recs):
            merge(mat, recs)
    result["cb4"] = mat
    for cb, sig in CB_SIGNATURES.items():
        m = {}
        for recs in runs:
            if {n for n, _, _ in recs}.intersection(sig):
                merge(m, recs)
        result[cb] = m
    by_offset = {}
    for cb, m in result.items():
        table = {}
        for n, (off, d) in m.items():
            for k in range(d):
                if off + 4 * k in table:
                    raise RuntimeError("%s 偏移重叠: %s" % (cb, n))
                table[off + 4 * k] = (n, k)
        by_offset[cb] = table
    return by_offset


def annotate(code, tables):
    def sub(cb):
        def f(m):
            i, sw = int(m.group(1)), m.group(2)
            parts = [tables[cb].get(i * 16 + 4 * "xyzw".index(c)) for c in sw]
            if not all(parts):
                return m.group(0)
            if len({p[0] for p in parts}) == 1:
                return parts[0][0] + "." + "".join("xyzw"[k] for _, k in parts)
            return "float%d(%s)" % (len(parts), ", ".join(n + "." + "xyzw"[k] for n, k in parts))
        return f
    for cb in tables:
        code = re.sub(cb + r"\[(\d+)\]\.([xyzw]+)", sub(cb), code)
    return code


def cut_block(lines, start_pred, desc):
    """返回 (起始行号, 结束行号)：从满足 start_pred 的行开始，到其后 if/else 花括号完全闭合为止。"""
    start = next((i for i, l in enumerate(lines) if start_pred(l)), None)
    if start is None:
        raise RuntimeError("未找到代码块: " + desc)
    depth, opened, i = 0, False, start
    while i < len(lines):
        s = lines[i].strip()
        depth += s.count("{") - s.count("}")
        opened = opened or "{" in s
        if opened and depth == 0 and not (i + 1 < len(lines) and lines[i + 1].strip().startswith("} else")) \
                and not s.endswith("else {"):
            return start, i
        i += 1
    raise RuntimeError("代码块未闭合: " + desc)


def must_sub(pattern, repl, text, desc, count=None):
    new, n = re.subn(pattern, repl, text)
    if n == 0 or (count is not None and n != count):
        raise RuntimeError("替换次数不符(%s): %d" % (desc, n))
    return new


def replace_main_light_shadows(lines):
    """只替换阴影输出，保留跨越源阴影块的光向归一化及距离衰减。"""
    start, end = cut_block(lines, lambda line: "_is_main_light_shadows_on" in line, "shadow")
    block = "\n".join(lines[start:end + 1])
    # r9.w 是块外计算、块后消费的逆距离；源变体寄存器布局变化时必须重新核对。
    if any("w" in components for components in re.findall(r"\br9\.([xyzw]+)\s*=", block)) or any(
            not re.search(r"\b" + register + r"\.w\s*=", block) for register in ("r11", "r10")):
        raise RuntimeError("源主光阴影寄存器契约变化：预期输出 r11.w/r10.w，保留 r9.w")
    # 原程序有两路阴影结果：r11.w 直接混合 ReceiveShadows；r10.w 还受实体主光权重影响。
    # r12.y 此时仍是实体主光权重，后续 PackedParams 分支会按原程序消费 r10.w。
    lines[start:end + 1] = [
        "  r11.w = lerp(1.0, KeyLightVisibility, _ReceiveShadows.x);",
        "  r10.w = lerp(1.0, KeyLightVisibility, _ReceiveShadows.x * _AvatarMainLightColor.w * saturate(r12.y * 2.0 - 1.0));",
    ]


def restore_skin_group_flag(program):
    """恢复反编译器丢失的非零布尔值；只接受已核原片元及分组判断。"""
    if not re.search(r'^"// hash: ' + SKIN_FLAG_FRAGMENT_HASH + r"\s*$", program, re.M):
        raise RuntimeError("源材质分组片元身份变化，不能恢复未知立即数")
    # DXBC 比较结果为 0xFFFFFFFF/0，再与 1 做 AND。反编译器把 0x00000001
    # 当浮点并打印为 0.000000；这里用数值 1 保持后续布尔选择，避免次正规浮点被清零。
    pattern = (r"(?m)^(\s*r3\.w = cmp\(\(int\)r2\.w == asint\(_SkinMatId\.x\)\);\n"
               r"\s*)r5\.w = r3\.w \? 0\.000000 : 0;$")
    return must_sub(pattern, r"\g<1>r5.w = r3.w ? 1 : 0;", program,
                    "材质分组布尔寄存器契约", count=1)


def transform(program):
    program = restore_skin_group_flag(program)
    body = program[program.index("{", program.index("void main(")) + 1:]
    body = body[:body.rindex("return;")]
    lines = body.split("\n")

    # 1. 运动矢量与 GBuffer 标记位
    a = next(i for i, l in enumerate(lines) if "unity_MotionVectorsParams" in l)
    b = next(i for i, l in enumerate(lines) if "o2.z = " in l)
    del lines[a:b + 1]

    # 2. 阴影：组件提供角色级可见度，保留原程序输出与其它活跃寄存器。
    replace_main_light_shadows(lines)

    # 3'. 运行时 FX 覆盖分支（覆盖边缘光、覆盖双色调）。Pyrios 材质都关着，pyrios_material_plan 要求其为 0；
    # 整段删掉，避免引入对象矩阵和额外贴图。
    for name in DISABLED_BLOCKS:
        if any(("cmp(0.5 < %s.x)" % name) in l for l in lines):
            s, e = cut_block(lines, lambda l, n=name: ("cmp(0.5 < %s.x)" % n) in l, name)
            del lines[s:e + 1]
    text = "\n".join(lines)

    # 3. 角色实体缓冲
    text = text.replace("asint(_RenderedEntityCount.x)", "1").replace("(int)_PackedParams1.z", "0")

    def entity(m):
        off = int(m.group(1)) + 4 * int(m.group(2) or 0)
        if off not in ENTITY_FIELDS:
            raise RuntimeError("未映射的实体缓冲偏移 %d" % off)
        return ENTITY_FIELDS[off]
    text = must_sub(r"t1\[r\d+\.\w\]\.val\[(\d+)/4(?:\+(\d))?\]", entity, text, "entity")

    # 4. 贴图。UV 都在 Unity 约定（V 向上）下计算，F.S 采样时翻成 UE 的 V。
    for reg, name in TEXTURE_REGISTERS.items():
        text = must_sub(reg + r"\.Sample(?:Bias)?\(s\d_s, ([^,()]+)(?:, _CharacterSampleTextureBias\.x)?\)",
                        r"F.S(%s, %sSampler, \1)" % (name, name), text, reg)
    text = must_sub(r"t2\.SampleBias\(s0_s, [^,]+, _CharacterSampleTextureBias\.x\)\.xyz",
                    "float3(0.0, 0.0, 0.0)", text, "overlay", 1)
    text = must_sub(r"t7\.Sample\(s2_s, (r\d+\.xyz)\)",
                    r"F.MatCap(MatCapTex1, MatCapTex1Sampler, MatCapTex2, MatCapTex3, MatCapTex4, MatCapTex5, \1)",
                    text, "matcap", 1)

    # 5. Unity 视图矩阵（cbuffer 里按列存放 unity_MatrixV 的四列）：行 0/1/2 是右、上、-前。
    text = text.replace("unity_MatrixV.xy", "float2(ViewRightU.x, ViewUpU.x)")
    text = text.replace("cb0[118].xy", "float2(ViewRightU.y, ViewUpU.y)")
    text = text.replace("cb0[119].xy", "float2(ViewRightU.z, ViewUpU.z)")
    text = text.replace("unity_MatrixV.z", "(-ViewFwdU.x)").replace("cb0[118].z", "(-ViewFwdU.y)")
    text = text.replace("cb0[119].z", "(-ViewFwdU.z)")
    text = text.replace("cb0[120].z", "dot(ViewFwdU, _WorldSpaceCameraPos.xyz)")
    # cb0[94].y 是投影矩阵 m11（1/tan(fovY/2)），unity_OrthoParams.w 为 1 表示正交相机。
    text = text.replace("cb0[94].y", "View.ViewToClip[1][1]").replace("unity_OrthoParams.w", "0.0")
    text = text.replace("_ScreenSize.", "View.ViewSizeAndInvSize.").replace("v9.xy", "Parameters.SvPosition.xy")

    # 6. 按材质组索引的 MatCap 打包数组
    text = must_sub(r"cb4\[(r\d+\.\w)\+(\d+)\]", r"MC[(int)\1+\2]", text, "mcarray")

    # 反射表里 _SkinMatId 是 int 型 cbuffer 成员，Unity 上传时把 Float 属性转成整数；
    # UE 参数都是 float，所以 asint 改成取整，否则 4.0 的位模式永远不等于组号。
    text = must_sub(r"asint\((_\w+)\.x\)", r"((int)round(\1.x))", text, "asint")

    # 7. 时间与正反面
    # Time 是标量，"_GlobalTimeParamsB.yy" 这类多分量写法换成标量重复 .xx。
    text = re.sub(r"_GlobalTimeParamsB\.(y+)\b",
                  lambda m: "Time" if len(m.group(1)) == 1 else "Time." + "x" * len(m.group(1)), text)
    text = must_sub(r"v10\.x \? 1 : -1", "(FaceSign > 0.0 ? 1 : -1)", text, "face", 1)
    text = must_sub(r"cmp\(\(int\)v10\.x == 0\)", "cmp(FaceSign < 0.0)", text, "face0", 1)

    # UE5 的 DXC 用 HLSL 2021：向量条件的三目运算必须改写成 select()。
    text = re.sub(r"^(\s*[\w.]+ = )(r\d+\.[xyzw]{2,4}) \? (.+) : (.+);$",
                  r"\1select(\2, \3, \4);", text, flags=re.M)

    # 8. 保留可定位的源输出。Deferred 消费者未知，项目合成不冒称原游戏 RT 调度。
    lines = text.split("\n")
    k = next(i for i, l in enumerate(lines) if re.match(r"\s*(r\d+\.[xyzw]{3}) = sqrt\(\1\);", l))
    rim = re.match(r"\s*(r\d+\.[xyzw]{3})", lines[k]).group(1)
    kept = [l for l in lines[k + 1:] if re.match(r"\s*o0\.xyz = ", l)]
    glow = next(re.search(r"o1\.w = ([^;]+);", l).group(1) for l in lines[k + 1:] if "o1.w = " in l)
    text = "\n".join(lines[:k] + ["  RimRaw = %s;" % rim] + kept +
                     ["  BloomWeight = %s;" % glow, "  return o0.xyz;", ""])
    if re.search(r"\bcb[0-4]\[|\bt[0-9]\.|\bv(5|6|9)\.", text):
        raise RuntimeError("仍有未替换的寄存器: " + str(re.findall(r"\bcb[0-4]\[\d+\][^;]*|\bt[0-9]\.\w+", text)[:5]))
    return text


PRELUDE = r"""// 由 gen_nap_avatar_hlsl.py 生成，勿手改。
// 原 Shader：miHoYo/Character/NapAvatarStandard，Pass CharacterToonDeferred，变体见 gen_nap_avatar_hlsl.KEYWORDS。
// 运算在 Unity 约定下进行：Y 轴向上、长度单位米。U() 把 UE 向量换到该约定（交换 Y/Z，只用于点积，不影响结果）。
struct NAPF
{
    float3 U(float3 v) { return float3(v.x, v.z, v.y); }
    // Unity UV（V 向上）采样 UE 导入的贴图（V 向下）。
    float4 S(Texture2D T, SamplerState Smp, float2 uv) { return Texture2DSample(T, Smp, float2(uv.x, 1.0 - uv.y)); }
    // MatCap UV 在 Unity 贴图空间（V 向上），采样前翻成 UE 空间。slice 为材质组索引，>=5 时不会被调用。
    float4 MatCap(Texture2D T1, SamplerState S, Texture2D T2, Texture2D T3, Texture2D T4, Texture2D T5, float3 uvs)
    {
        float2 uv = float2(uvs.x, 1.0 - uvs.y);
        int slice = (int)(uvs.z + 0.5);
        if (slice == 0) return Texture2DSample(T1, S, uv);
        if (slice == 1) return Texture2DSample(T2, S, uv);
        if (slice == 2) return Texture2DSample(T3, S, uv);
        if (slice == 3) return Texture2DSample(T4, S, uv);
        return Texture2DSample(T5, S, uv);
    }
};
NAPF F;
#ifndef cmp
#define cmp -
#endif
// 寄存器 r0..r21 由下方移植代码自行声明。
float4 o0 = 0;

// 顶点阶段的输出（Unity 的 v0..v8）。v2/v3/v4 的 w 分量是世界坐标。
float3 nrmW = normalize(Parameters.TangentToWorld[2]);
float3 tanW = normalize(Parameters.TangentToWorld[0]);
float3 bitW = normalize(Parameters.TangentToWorld[1]) * NormalYSign.x;
float3 posU = F.U(WorldPos) * 0.01;
// v0.xy 是网格 UV0，v1.xy 是网格 UV2（原顶点着色器把 TEXCOORD2 传到 TEXCOORD1，材质里叫 "Use UV2"），都换成 Unity 约定（FBX 导入时 UE 把 V 翻过一次，这里翻回）。`n// 网格 UV1 存的是描边用平滑法线，表面 Pass 不用。v0.zw 是 UV3，双面/对称 UV 分支关闭时不用。
float4 v0 = float4(UV.x, 1.0 - UV.y, 0.0, 0.0);
float4 v1 = float4(UV2.x, 1.0 - UV2.y, 0.0, 0.0);
float4 v2 = float4(F.U(nrmW), posU.x);
float4 v3 = float4(F.U(tanW), posU.y);
float4 v4 = float4(F.U(bitW), posU.z);
float4 vcol = float4(VCol, Parameters.VertexColor.a);
bool vcFlag = ((((int)(vcol.b * 255.0 + 0.5)) >> 5) & 1) != 0;
float4 v7 = float4(1.0 - EntityParams.z * vcol.a, vcFlag ? 0.0 : vcol.a, vcFlag ? 1.0 : 0.0, 0.0);
float3 v8 = float3(0.0, 0.0, 0.0);

float4 _WorldSpaceCameraPos = float4(F.U(CameraPos) * 0.01, 1.0);
float4 _AvatarMainLightColor = float4(KeyLightColor.rgb * SceneLightStrength, 1.0);
float3 LightDirU = normalize(F.U(KeyLightDirectionWS.xyz));
float3 ViewRightU = F.U(normalize(View.ViewToTranslatedWorld[0].xyz));
float3 ViewUpU = F.U(normalize(View.ViewToTranslatedWorld[1].xyz));
float3 ViewFwdU = F.U(normalize(View.ViewToTranslatedWorld[2].xyz));

float4 MC[20];
MC[0] = MC_Refract1; MC[1] = MC_Refract2; MC[2] = MC_Refract3; MC[3] = MC_Refract4; MC[4] = MC_Refract5;
MC[5] = MC_Tint1; MC[6] = MC_Tint2; MC[7] = MC_Tint3; MC[8] = MC_Tint4; MC[9] = MC_Tint5;
MC[10] = MC_A1; MC[11] = MC_A2; MC[12] = MC_A3; MC[13] = MC_A4; MC[14] = MC_A5;
MC[15] = MC_B1; MC[16] = MC_B2; MC[17] = MC_B3; MC[18] = MC_B4; MC[19] = MC_B5;
"""


def main():
    program, props = find_variant()
    color_props = sorted(re.match(r".*?(_\w+)\s*\(", p).group(1) for p in props
                         if re.search(r'"\s*,\s*Color\)', p) and re.match(r".*?(_\w+)\s*\(", p))
    all_props = {re.match(r".*?(_\w+)\s*\(", p).group(1) for p in props if re.match(r".*?(_\w+)\s*\(", p)}
    tables = cbuffer_maps(all_props)
    code = transform(annotate(program, tables))

    referenced = sorted(set(re.findall(r"\b(_\w+|unity_\w+)\.[xyzw]+", code)) - LOCAL_NAMES)
    material = [n for n in referenced if any(n == t[0] for t in tables["cb4"].values())]
    globals_ = [n for n in referenced if n not in material]
    inputs = ([{"name": n, "kind": "texture"} for n in TEXTURES] +
              [{"name": n, "kind": "builtin"} for n in BUILTINS] +
              [{"name": n, "kind": "component_vector"} for n in COMPONENT_VECTORS] +
              [{"name": n, "kind": "component_scalar"} for n in COMPONENT_SCALARS] +
              [{"name": n, "kind": "extra"} for n in EXTRA_VECTORS] +
              [{"name": n, "kind": "material"} for n in material] +
              [{"name": n, "kind": "global"} for n in globals_])
    # 输出分离不改变原185输入或色彩属性身份；契约变化必须另行迁移，不能顺手重写。
    if json.loads(OUT_INPUTS.read_text(encoding="utf-8")) != {"inputs": inputs, "color_properties": color_props}:
        raise RuntimeError("原 Toon 输入契约变化，拒绝生成")
    OUT_HLSL.write_text(PRELUDE + "\n" + code, encoding="utf-8")
    print("material", len(material), "global", globals_)


if __name__ == "__main__":
    main()
