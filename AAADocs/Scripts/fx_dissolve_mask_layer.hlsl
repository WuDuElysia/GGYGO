// M_FX_DissolveMaskLayers 单层 Custom 节点体。由 build_pyrios_body_fx.py 读入，三层共用同一份代码。
// 对应 miHoYo/Particles/Particles_Dissolve_CustomColor_Mask(_Cap) 在 _UsingNonPSR=1（模型模式）下的像素逻辑。
// UV 运算在 Unity 空间（V 向上）完成，采样前再翻成 UE 空间；FBX 导入时 UE 已把网格 V 翻过一次。
// 返回预乘颜色 float4(rgb * a, a)，由合成节点按 Unity 绘制顺序做 over 叠加。
struct FXL
{
    float Ch(float4 v, float i)
    {
        return i < 0.5 ? v.r : (i < 1.5 ? v.g : (i < 2.5 ? v.b : v.a));
    }
    // Unity 的 Flip 枚举：0 不翻，1 翻 U，2 翻 V，3 都翻；翻转发生在 _ST 缩放之前。
    float2 Xf(float2 uv, float f, float4 st)
    {
        float2 m = float2((abs(f - 1.0) < 0.5 || abs(f - 3.0) < 0.5) ? 1.0 : 0.0,
                          (abs(f - 2.0) < 0.5 || abs(f - 3.0) < 0.5) ? 1.0 : 0.0);
        float2 r = lerp(uv, 1.0 - uv, m);
        return (r - m) * st.xy + st.zw + m;
    }
    // mode：bit0 = U 轴 Repeat，bit1 = V 轴 Repeat；3 走共享 Wrap 采样器，其余走 Clamp 采样器并对 Repeat 轴取 frac。
    float4 Smp(Texture2D T, SamplerState WrapS, float2 uvU, float mode)
    {
        float2 uv = float2(uvU.x, 1.0 - uvU.y);
        if (mode > 2.5)
        {
            return Texture2DSample(T, WrapS, uv);
        }
        float wu = fmod(mode, 2.0);
        float wv = floor(mode * 0.5);
        uv = float2(wu > 0.5 ? frac(uv.x) : uv.x, wv > 0.5 ? frac(uv.y) : uv.y);
        return Texture2DSample(T, View.MaterialTextureBilinearClampedSampler, uv);
    }
};
FXL F;

if (FlipB.w < 0.5)
{
    return float4(0.0, 0.0, 0.0, 0.0);
}

float2 uv0 = float2(UV.x, 1.0 - UV.y);

float2 mainUV = F.Xf(uv0, FlipA.x, MainST);
if (FeatB.w > 0.5)
{
    float2 mv = frac(SpeedA.xy * Time);
    if (SpeedC.z != 0.0) mv.x = floor(mv.x / SpeedC.z) * SpeedC.z;
    if (SpeedC.w != 0.0) mv.y = floor(mv.y / SpeedC.w) * SpeedC.w;
    mainUV += mv;
}
float2 maskUV = F.Xf(uv0, FlipA.y, MaskST) + frac(SpeedA.zw * Time);
float2 dissUV = F.Xf(uv0, FlipA.z, DissolveST) + frac(SpeedB.xy * Time);
float2 distUV = F.Xf(uv0, FlipB.y, DistST) + frac(SpeedB.zw * Time);
float2 dist2UV = F.Xf(uv0, FlipB.z, Dist2ST) + frac(SpeedC.xy * Time);

// 扭曲值以 127/255 为零点；原 shader 写作 dot(d.xx, I.xx)，即 2 * d * I。
float d1 = 0.0;
float d2 = 0.0;
if (FeatA.z > 0.5)
{
    d1 = 2.0 * (F.Ch(F.Smp(DistortionTex, DistortionTexSampler, distUV, WrapB.y), ChanB.z) - 0.498039216) * DissCfg2.w;
}
if (FeatA.w > 0.5)
{
    d2 = 2.0 * (F.Ch(F.Smp(DistortionTex2, DistortionTex2Sampler, dist2UV, WrapB.z), ChanB.w) - 0.498039216) * DissCfg2.w;
}

float maskA = 1.0;
if (FeatA.x > 0.5)
{
    maskUV += d1 * DistI.z + d2 * Dist2I.z;
    float4 m = F.Smp(MaskTex, MaskTexSampler, maskUV, WrapA.y);
    maskA = F.Ch(m, ChanA.z);
    float k = (F.Ch(m, ChanA.w) - 1.0) * DistI.w + 1.0;
    d1 *= k;
    d2 *= k;
}
mainUV += d1 * DistI.x + d2 * Dist2I.x;
dissUV += d1 * DistI.y + d2 * Dist2I.y;

float diss = 1.0;
if (FeatA.y > 0.5)
{
    diss = F.Ch(F.Smp(DissolveTex, DissolveTexSampler, dissUV, WrapA.z), ChanB.x);
    if (FeatB.y > 0.5)
    {
        float2 druv = F.Xf(RampCfg.w > 0.5 ? dissUV : uv0, FlipA.w, DissolveRampST);
        float dr = F.Ch(F.Smp(DissolveRampTex, DissolveRampTexSampler, druv, WrapA.w), ChanB.y);
        diss = DissCfg.w > 0.5 ? lerp(diss, dr, 0.5) : diss * dr;
    }
}

float4 mainS = F.Smp(MainTex, MainTexSampler, mainUV, WrapA.x);

float3 rampRGB = float3(1.0, 1.0, 1.0);
float rampA = 1.0;
if (FeatB.x > 0.5)
{
    float2 ruv = F.Xf(RampCfg.z > 0.5 ? mainUV : uv0, FlipB.x, RampST);
    float4 r = F.Smp(RampTex, RampTexSampler, ruv, WrapB.x);
    float rc = F.Ch(r, min(RampCfg.x, 3.0));
    if (RampCfg.y > 0.5)
    {
        rampA = rc;
    }
    else
    {
        rampRGB = RampCfg.x > 3.5 ? r.rgb : float3(rc, rc, rc);
    }
}

// 2Tone：在 CustomDataColor 与 MultiplyParticleColor 之间按主图亮度（与溶解）插值。
bool rgbMode = ChanA.x > 3.5;
float lum = rgbMode ? 1.0 : F.Ch(mainS, ChanA.x);
float3 mainRGB = rgbMode ? mainS.rgb : float3(1.0, 1.0, 1.0);
float aMain = F.Ch(mainS, min(ChanA.y, 3.0));
float lerpT = saturate((DissCfg2.x > 0.5 ? diss : 1.0) * DissCfg2.z * lum);
float4 col = lerp(CustomColor, float4(MultiplyColor.rgb, CustomColor.a), lerpT);
float3 rgb = col.rgb * mainRGB * rampRGB * (1.0 + AmbientColor.rgb);

float alpha;
if (FeatA.y > 0.5)
{
    float d = DissCfg2.y > 0.5 ? diss * aMain : diss;
    float p = DissCfg.x;
    float soft = (DissCfg.z <= 0.5 ? 1.0 : 0.0) * DissCfg.y;
    d = saturate((d - p + soft * (1.0 - p)) / max(0.001, DissCfg.y));
    d *= col.a;
    alpha = DissCfg2.y > 0.5 ? d : d * aMain;
}
else
{
    alpha = col.a * aMain;
}
alpha *= maskA;

// 软粒子：Unity 距离单位是米，UE 深度是厘米。
if (SoftCfg.x > 0.5)
{
    alpha *= saturate(SoftCfg.z * ((SceneZ - PixelZ) * 0.01 - SoftCfg.y));
}

rgb = exp2(log2(max(rgb, 1e-8)) * AlphaCfg.x);
alpha = exp2(log2(max(alpha, 1e-8)) * AlphaCfg.y);
alpha = saturate(AlphaCfg.z * alpha * rampA);
if (AlphaCfg.w > 0.5 && FaceSign < 0.0)
{
    alpha = 0.0;
}
return float4(rgb * alpha, alpha);
