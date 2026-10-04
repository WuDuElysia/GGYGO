// ╔══════════════════════════════════════════════════════════════╗
// ║     ZZZ NapAvatarStandard — Fragment Shader 注释版           ║
// ║     来源: AnimeStudio + 3Dmigoto 反编译 HLSL                   ║
// ║     Shader: miHoYo/Character/NapAvatarStandard                ║
// ║     Pass:   CharacterToonDeferred (主渲染 Pass)               ║
// ║     用途:   Pyrios 角色身体/武器材质渲染                       ║
// ║                                                              ║
// ║     源文件路径 (AnimeStudio 导出):                             ║
// ║       正篇:  F:\AnimeStudio\Exports\Shader\                   ║
// ║              miHoYo_Character_NapAvatarStandard.shader        ║
// ║       附一:  miHoYo_Character_NapAvatarStandardEnergy.shader  ║
// ║       附二:  miHoYo_Character_NapAvatarStandardEye.shader     ║
// ║       附三:  miHoYo_Character_NapAvatarStandardFace.shader    ║
// ╚══════════════════════════════════════════════════════════════╝

// ═══════════════════════════════════════════════════════════════
// 零、架构总览
// ═══════════════════════════════════════════════════════════════
//
// 该像素着色器执行以下渲染管线:
//
//   [4张贴图] ──→ [通道拆解] ──→ [法线重建 + MatID分级]
//                                      │
//              ┌───────────────────────┤
//              ▼                       ▼
//      [阴影采样 9+12 tap]      [NdotL + Half-Lambert]
//              │                       │
//              ▼                       ▼
//      [Ramp混合]  ←──  [三区域解析Ramp]
//              │
//              ▼
//      [Diffuse最终] ──→ (+) ←── [Toon/GGX Specular]
//                              │
//                              ▼
//                      [Base Color输出]
//
//   [MatCap 3层] ──→ [MatCap叠加+遮罩] ──→ (+) ←── [Emission]
//                                            │      ←── [Rim Glow]
//                                            ▼
//                                    [Emissive输出]
//
// 纹理绑定:  t3=_MainTex  t4=_LightTex  t5=_OtherDataTex  t6=_OtherDataTex2
//           t7=MatCap2DArray(或Ramp贴图)  t0=ShadowMap  t1=LightProbe
//
// ═══════════════════════════════════════════════════════════════


// ═══════════════════════════════════════════════════════════════
// 一、纹理与常量缓冲区声明
// ═══════════════════════════════════════════════════════════════

// --- 纹理 ---
Texture2D<float4>      t7 : register(t7);  // MatCap2DArray (或_CharacterRampTex,取决于变体)
Texture2D<float4>      t6 : register(t6);  // _OtherDataTex2 (R=透明, G=光滑度, B=自发光遮罩)
Texture2D<float4>      t5 : register(t5);  // _OtherDataTex  (R=MatID, G=金属度, B=高光遮罩)
Texture2D<float4>      t4 : register(t4);  // _LightTex      (RG=法线, B=DiffuseBias)
Texture2D<float4>      t3 : register(t3);  // _MainTex       (RGB=基础色)
Texture2D<float4>      t2 : register(t2);  // Overlay/Detail 纹理

// 灯光探针数据 (结构化缓冲区)
struct LightProbe_t { float val[32]; };
StructuredBuffer<LightProbe_t> t1 : register(t1);

// 阴影级联贴图数组
Texture2DArray<float4> t0 : register(t0);

// --- 采样器 ---
SamplerComparisonState s1_s : register(s1);  // 阴影比较采样器 (用于SampleCmpLevelZero)
SamplerState           s0_s : register(s0);  // 通用线性采样器 (用于SampleBias)

// --- 常量缓冲区 ---
// cb4: 材质参数 (170个float4) — 主角!
//   [58]   = ColorTint (色调修正)
//   [75-79]= _SpecularColor[1-5] (5档高光颜色)
//   [80-84]= _RimGlowLightColor[1-5] (5档边缘光颜色)
//   [135]  = Material ID 匹配目标值
//   [136]  = _RampTexParams0 (Ramp行为控制)
//   [137]  = ShallowColor/ShadowColor 4级级联
//   [138]  = 阴影偏移 + Emission开关
//   [140]  = 表面属性 (UV缩放/BumpScale/金属度缩放/粗糙度乘数)
//   [141-142]= _SpecIntensity per tier
//   [143-146]= _SpecularRange / _ToonSpecular / _HighlightShape
//   [147]  = Rim Glow开关
//   [165-166]= ShadowIntensity per tier
cbuffer cb4 : register(b4) { float4 cb4[170]; }

// cb3: 全局光照参数
cbuffer cb3 : register(b3) { float4 cb3[41]; }

// cb2: 灯光相关 (级联阴影矩阵等)
cbuffer cb2 : register(b2) { float4 cb2[27]; }

// cb1: 对象变换
cbuffer cb1 : register(b1) { float4 cb1[29]; }

// cb0: 全局常量 (时间/相机/光照方向等, 209个float4)
cbuffer cb0 : register(b0) { float4 cb0[209]; }


// ═══════════════════════════════════════════════════════════════
// 二、主函数入口
// ═══════════════════════════════════════════════════════════════

// 3Dmigoto 宏: 因为反编译自DXBC, 用宏模拟HLSL的cmp指令
#define cmp -

void main(
  // --- 顶点着色器传来的插值数据 ---
  float4 v0 : TEXCOORD0,   // UV0 + 其他
  float4 v1 : TEXCOORD1,   // UV1 + 其他
  float4 v2 : TEXCOORD2,   // 世界空间法线 (TBN的N) + w=世界X
  float4 v3 : TEXCOORD3,   // 世界空间切线 (TBN的T) + w=世界Y
  float4 v4 : TEXCOORD4,   // 世界空间副法线 (TBN的B) + w=世界Z
  float4 v5 : TEXCOORD5,   // 屏幕空间坐标 (用于dither)
  float4 v6 : TEXCOORD6,   // 屏幕空间坐标2
  float4 v7 : TEXCOORD7,   // .x=?, .y=阴影遮罩, .z=Subsurface标记
  float3 v8 : TEXCOORD8,   // 环境光/间接光颜色
  float4 v9 : SV_POSITION0, // 屏幕像素坐标
  uint   v10: SV_IsFrontFace0, // 正面(1)还是背面(0)

  // --- 输出 (MRT: 多渲染目标) ---
  out float4 o0 : SV_Target0,  // 主颜色
  out float4 o1 : SV_Target1,  // 附加通道1
  out float4 o2 : SV_Target2,  // 附加通道2 (法线/材质标记)
  out float4 o3 : SV_Target3   // 附加通道3
)
{
  // 临时寄存器 (HLSL编译器会重用, 所以变量名不代表独立寄存器)
  float4 r0,r1,r2,r3,r4,r5,r6,r7,r8,r9,r10,r11,r12,r13,r14,r15,r16,r17,r18,r19,r20;
  uint4 bitmask, uiDest;
  float4 fDest;


  // ═══════════════════════════════════════════════════════════════
  // 三、法线重建 (从_LightTex解包 → 切空间→世界空间TBN变换)
  // ═══════════════════════════════════════════════════════════════

  // --- 3.1 采样_MainTex (t3) 获取基础色 ---
  r0.zw = /* 根据条件选择UV通道 */ r0.zz ? v0.zw : v0.xy;
  r1.xyz = t3.SampleBias(s0_s, r0.zw, cb0[199].x).xyz;  // cb0[199].x = MipBias
  r2.xyz = cb4[58].xyz * r1.xyz;      // cb4[58].xyz = _Color色调, 对Albedo做色彩修正

  // --- 3.2 采样_LightTex (t4) 获取切线法线+DiffuseBias ---
  r0.yz = r0.yy ? v0.zw : v0.xy;      // UV选择 (OverlayTex开关控制)
  r3.xyz = t4.SampleBias(s0_s, r0.yz, cb0[199].x).xyz;

  // --- 3.3 法线解压: [0,1] → [-1,1] ---
  r3.xyz = saturate(r3.xyz);           // 钳制到[0,1]
  r3.xyz = r3.xyz * float3(2,2,2) + float3(-1.00399995,-1.00399995,-1);
  // 结果: r3.xy = 切线空间法线XY (约[-1,1])
  //       r3.z  = DiffuseBias (约[-1,1], 负值=阴面, 正值=阳面)

  // --- 3.4 BumpScale (法线强度) ---
  r3.xy = cb4[140].yy * r3.xy;        // cb4[140].y = _BumpScale (默认1.0, 范围-5~5)

  // --- 3.5 法线Z分量重建: z = sqrt(1 - x² - y²) ---
  r0.w = dot(r3.xy, r3.xy);           // x² + y²
  r0.w = min(1, r0.w);                // 防止浮点精度导致>1
  r0.w = 1 + -r0.w;                   // 1 - (x² + y²)
  r0.w = sqrt(r0.w);                  // z分量

  // --- 3.6 切线空间 → 世界空间 (TBN矩阵变换) ---
  r0.x = r0.w * r0.x;
  r4.xyz = v4.xyz * r3.yyy;           // Bitangent(B) × Normal.y
  r3.xyw = r3.xxx * v3.xyz + r4.xyz;  // + Tangent(T) × Normal.x
  r3.xyw = r0.xxx * v2.xyz + r3.xyw;  // + Normal(N) × Normal.z
  // → r3.xyw = 世界空间法线 (注意w通道存放Z分量!)

  // --- 3.7 归一化法线 ---
  r0.x = dot(r3.xyw, r3.xyw);         // 长度平方
  r0.x = rsqrt(r0.x);                 // 1/长度
  r3.xyw = r3.xyw * r0.xxx;           // 归一化世界法线


  // ═══════════════════════════════════════════════════════════════
  // 四、采样_OtherDataTex (t5) 和 _OtherDataTex2 (t6)
  // ═══════════════════════════════════════════════════════════════

  // --- 4.1 _OtherDataTex (t5) — 注意 .zxy 通道重排! ---
  // 原始通道: R=MaterialID, G=Metallic, B=SpecularMask
  // .zxy 重排后: r4.x = B(SpecMask), r4.y = R(MatID), r4.z = G(Metallic)
  r4.xyz = t5.SampleBias(s0_s, r0.yz, cb0[199].x).zxy;
  r4.xyz = saturate(r4.xyz);

  r0.x = cb4[140].z * r4.z;   // cb4[140].z = 金属度缩放 × Metallic(G通道)
                               // → r0.x = 最终的Metallic值

  // --- 4.2 _OtherDataTex2 (t6) — 注意 .zy 通道重排! ---
  // 原始通道: R=Transparency, G=Smoothness, B=EmissionMask
  // .zy 重排后: r0.y = B(EmissionMask), r0.z = G(Smoothness)
  // 注意: R通道(Transparency)在此被舍弃!
  r0.yz = t6.SampleBias(s0_s, r0.yz, cb0[199].x).zy;
  r0.yz = saturate(r0.yz);

  // --- 4.3 Emission遮罩的条件处理 ---
  r0.w = cmp(0.5 < cb4[138].z);       // cb4[138].z = Emission启用阈值
  if (r0.w != 0) {
    r5.xy = cmp(float2(0.5,0.5) < cb4[147].xy);
    r0.w = r5.y ? r5.x : 0;
    r1.w = -0.200000003 + r0.y;       // EmissionMask - 0.2
    r1.w = 1.25 * r1.w;               // 缩放 1.25x (阈值重映射)
    r1.w = max(0, r1.w);              // 钳制≥0
    r0.w = r0.w ? r1.w : r0.y;        // 条件选择
    r0.y = r5.x ? r0.w : 0;           // 最终 Emission 值(或0)
  }


  // ═══════════════════════════════════════════════════════════════
  // 五、Material ID → 5档 ShallowColor/ShadowColor 选择
  // ═══════════════════════════════════════════════════════════════
  //
  // ZZZ用Material ID (0.0~1.0) 将材质分为5档:
  //   0.0~0.2 → 材质组1
  //   0.2~0.4 → 材质组2
  //   0.4~0.6 → 材质组3
  //   0.6~0.8 → 材质组4
  //   0.8~1.0 → 材质组5
  // 每档有独立的 ShallowColor(亮部色)、ShadowColor(暗部色)、Specular参数等

  // Material ID 整数值提取
  r0.w = 5 * r4.y;                   // MatID × 5
  r0.w = floor(r0.w);                // 向下取整 (0,1,2,3,4)
  r0.w = 4 + -r0.w;                  // 反转 (4,3,2,1,0)
  r0.w = max(0, r0.w);
  r0.w = (int)r0.w;
  r0.w = cmp((int)r0.w == asint(cb4[135].y));  // 与目标MatID比较
  r1.w = r0.w ? 0.000000 : 0;

  // --- Overlay/Detail 贴图混合 (t2) ---
  r2.w = cmp(0.5 < cb4[139].w);      // Overlay启用?
  r5.xy = cb4[140].xx * v0.xy;       // 缩放后的UV (cb4[140].x = UV缩放)
  r5.xyz = t2.SampleBias(s0_s, r5.xy, cb0[199].x).xyz;  // 采样Detail贴图
  r1.xyz = r1.xyz * cb4[58].xyz + r5.xyz;  // Albedo×色调 + Detail
  r1.xyz = float3(-0.5,-0.5,-0.5) + r1.xyz; // -0.5偏移
  r1.xyz = max(float3(0,0,0), r1.xyz);      // 钳制≥0
  r1.xyz = r2.www ? r1.xyz : r2.xyz;        // Overlay开启→混合色, 关闭→纯Albedo

  // --- 5档Material ID → 选择颜色/参数 ---
  // 用阶梯比较: MatID < 0.2? <0.4? <0.6? <0.8?
  r2.xyzw = cmp(r4.yyyy < float4(0.200000003,0.400000006,0.600000024,0.800000012));

  // 根据MatID选择对应的Shallow/Shadow颜色 (cb4[137]=4级级联)
  // cb4[136].w = 档位1, cb4[137].w=档1Shallow, .z=档2Shadow, .y=档3Shadow, .x=档4Shadow
  r4.y = r2.w ? cb4[137].x : cb4[136].w;  // MatID>=0.8 → cb4[137].x
  r4.y = r2.z ? cb4[137].y : r4.y;        // MatID>=0.6 → cb4[137].y
  r4.y = r2.y ? cb4[137].z : r4.y;        // MatID>=0.4 → cb4[137].z
  r4.y = r2.x ? cb4[137].w : r4.y;        // MatID< 0.2 → cb4[137].w


  // ═══════════════════════════════════════════════════════════════
  // 六、光照方向与距离计算
  // ═══════════════════════════════════════════════════════════════

  // 世界空间位置 (从v2/v3/v4的w通道读取)
  r5.x = v2.w;  r5.y = v3.w;  r5.z = v4.w;  // r5 = 世界坐标

  // cb0[53] = 主光源在世界空间的位置
  r6.xyz = cb0[53].xyz + -r5.xyz;    // 光源→像素的方向向量
  r4.w = dot(r6.xyz, r6.xyz);         // 距离平方
  r5.w = max(1.17549435e-38, r4.w);   // 防除零
  r5.w = rsqrt(r5.w);                 // 1/距离
  r7.xyz = r6.xyz * r5.www;           // r7 = 指向光源的单位向量
  r6.w = sqrt(r4.w);                  // 实际距离

  // --- 从StructuredBuffer读取灯光额外数据 ---
  r7.w = cmp(0 < asint(cb0[196].x));  // 灯光数据是否存在?
  if (r7.w != 0) {
    // 读取灯光位置、范围等数据
    r8.x = t1[lightIndex].val[0/4];   // Light Position
    // ... (省略灯光数据处理细节)
  }

  // 灯光衰减: 1 - (dist² / range²)
  r10.xyz = r10.xyz + -r5.xyz;       // LightPos - WorldPos
  r8.z = dot(r10.xyz, r10.xyz);       // 距离平方
  r8.w = rsqrt(r8.z);                 // 1/距离
  r9.w = r9.w * r9.w;                 // 灯光范围平方
  r8.z = r8.z / r9.w;                 // dist² / range²
  r8.z = 1 + -r8.z;                   // 衰减 = 1 - dist²/range²
  r8.z = max(0, r8.z);                // 钳制≥0


  // ═══════════════════════════════════════════════════════════════
  // 七、阴影计算 (9-tap PCF + 12-tap 抖动泊松盘)
  // ═══════════════════════════════════════════════════════════════

  // --- 7.1 阴影贴图采样 (9-tap PCF) ---
  r9.w = cmp(0.5 < cb0[22].x);       // 阴影启用?
  if (r9.w != 0) {
    // 根据MatID选择阴影强度 (5档)
    r9.w = r2.w ? cb4[166].x : cb4[165].w;
    r9.w = r2.z ? cb4[166].y : r9.w;
    r9.w = r2.y ? cb4[166].z : r9.w;
    r9.w = r2.x ? cb4[166].w : r9.w;

    // 阴影坐标 = 世界位置 + 法线偏移(消除阴影痤疮)
    r11.xyz = r3.xyw * cb4[138].xxx + r5.xyz;  // cb4[138].x = 法线偏移量
    // 变换到光源空间...
    // (省略矩阵变换细节)

    // ★ 9-tap PCF (Percentage Closer Filtering) ★
    // 中心 + 4轴 + 4对角 = 9个采样点
    r11.x = t7.SampleCmpLevelZero(s1_s, centerUV, depth).x;  // 中心
    // ... 8个偏移采样 ...
    r10.w = (sum of 9 taps) * 0.111100003 + -1;  // /9, 然后-1 (反转向量)
    r9.w = r10.w * r9.w;                          // ×阴影强度
  }

  // --- 7.2 级联阴影 (12-tap 抖动泊松盘) ---
  // 用三角函数生成旋转抖动偏移, 12个采样点分布在一个圆盘上
  // 每个采样点通过sincos旋转后加到阴影坐标
  // (12-tap 抖动泊松盘代码省略, 约60行)

  // 合并主阴影 + 级联阴影
  r8.x = r10.w * r8.x;               // 级联 × 点光阴影
  r8.y = saturate(r8.y * 2 + -1);
  r10.w = cb0[197].w * r8.y;
  // ...

  // ★ RampTexParams0.z (cb4[136].z) 应用到阴影混合 ★
  r8.y = 1 + -cb4[136].z;            // 1 - RampP0.z
  r8.y = r8.x * cb4[136].z + r8.y;   // lerp(1-RampP0.z, shadow, RampP0.z)


  // ═══════════════════════════════════════════════════════════════
  // 八、Diffuse — NdotL + 三区域解析式Ramp
  // ═══════════════════════════════════════════════════════════════
  //
  // ZZZ使用的是解析式Ramp, 不是Ramp贴图查找!
  // 将ramp值分为浅(Shallow)/中(Mid)/深(Deep)三个区域,
  // 每个区域独立计算贡献, 最后求和

  // --- 8.1 NdotL与Half-Lambert ---
  r8.w = dot(r3.xyw, r10.xyz);       // ★ NdotL = 世界法线·光源方向 ★
  r9.x = 1 + r8.w;                   // Half-Lambert基础: NdotL + 1

  // 基于光源高度的法线补偿 (让头顶更亮)
  r9.y = 3 * r10.y;                  // 光源Y分量 × 3
  r9.y = min(1, r9.y);
  r9.y = -r9.y * 0.5 + r3.y;        // 法线Y - 光源Y×0.5
  r9.y = saturate(1.5 + r9.y);

  r9.x = r9.x * r9.y + -1;           // 组合Half-Lambert
  r9.x = r9.x + -r8.w;
  r9.x = v7.y * r9.x + r8.w;         // 顶点遮罩混合 (v7.y = 阴影遮罩)

  // --- 8.2 DiffuseBias加成 ---
  r3.z = r3.z * 2 + r9.x;            // r3.z = DiffuseBias×2 + halfLambert

  // --- 8.3 三区域解析式Ramp ---
  r9.x = 3 * r3.z;                   // rampVal × 3

  // 基于表面属性的Ramp范围
  r11.xy = float2(1.5,4.5) * r4.yy;  // r4.y = 当前材质的ramp范围参数

  // 三个区域的坐标
  r9.yz = r3.zz * float2(3,3) + -r11.xy;
  r9.xyz = float3(3,1,-1) + r9.xyz;

  // 归一化
  r4.y = -r4.y * 3 + 2;
  r9.xyw = r9.xyz / r4.yyy;

  // 计算反向Ramp
  r11.xyz = float3(1,1,1) + -r9.xyw;

  // 偏移后的坐标
  r12.xyz = float3(0.333299994,-0.333299994,-0.333299994) + r3.zzz;
  r12.xyz = r4.www * r12.xyz + float3(0.5,0.5,-0.5);
  r13.xyz = float3(1,1,1) + -r12.xyz;

  // ★ min混合获得三通道Ramp权重 ★
  r14.xy = min(r13.yx, r9.yx);       // min(反向Ramp, 正向Ramp)
  r9.xz = min(r12.xz, r11.yz);

  // 组装最终Ramp权重
  r14.z = r11.x;
  r14.w = r9.x;
  r11.xyz = saturate(r14.zyw);
  r14.y = saturate(min(r13.z, r12.y));
  r14.x = saturate(r14.x);
  r9.zw = saturate(r9.zw);

  // --- 8.4 _RampTexParams0.y 应用到Ramp坐标 ---
  r19.xy = cb4[136].yy * r19.xy + float2(0,1);  // 缩放+偏移

  // 归一化Ramp颜色
  r11.w = r11.x + r11.y + r11.z;     // 三个区域权重之和
  r11.w = 0.333330005 * r11.w;       // 平均
  r20.xyz = saturate(r11.xyz / r11.www); // 归一化到单位向量

  // RampTexParams0.x/y混合
  r11.xyz = r11.xyz * r19.yyy;       // × RampP0.y
  r11.xyz = r20.xyz * r19.xxx + r11.xyz;  // lerp

  // --- 8.5 三区域贡献求和 ---
  // 选择5组ShallowColor/ShadowColor (cb4[60-69])
  r11.xyz = r2.www ? cb4[61].xyz : cb4[60].xyz;  // 亮部色
  r11.xyz = r2.zzz ? cb4[62].xyz : r11.xyz;
  r11.xyz = r2.yyy ? cb4[63].xyz : r11.xyz;
  r11.xyz = r2.xxx ? cb4[64].xyz : r11.xyz;

  r12.xzw = r2.www ? cb4[66].xyz : cb4[65].xyz;   // 中间色
  r12.xzw = r2.zzz ? cb4[67].xyz : r12.xzw;
  r12.xzw = r2.yyy ? cb4[68].xyz : r12.xzw;
  r12.xzw = r2.xxx ? cb4[69].xyz : r12.xzw;

  // 三个区域 × 各自颜色
  r13.xyz = r11.xyz * r13.xyz;       // Shallow区域
  r11.xyz = r11.xyz * r14.xyz;       // Mid区域
  r14.xyz = r12.xzw * r15.xyz;       // Deep区域
  r12.xzw = r12.xzw * r18.xyz;       // 额外区域

  // --- 8.6 光照强度归一化 ---
  r15.xyz = float3(1.17549435e-38,1.17549435e-38,1.17549435e-38) + r5.xyz;
  r11.w = max(r15.x, r15.y);         // 最大通道
  r11.w = max(r11.w, r15.z);
  r11.w = rcp(r11.w);                // 1/最大通道 (归一化因子)

  // --- 8.7 环境/间接光贡献 ---
  r14.w = 1 + -r8.z;                 // 1 - 直接光衰减
  r8.z = r13.w * r14.w + r8.z;       // 间接光 × (1-衰减) + 直接光衰减
  r15.xyz = r8.zzz * r5.xyz;         // 环境光 = 衰减 × 光源色

  // --- 8.8 最终Diffuse组装 ---
  r8.z = min(1, r11.w);
  r18.xyz = r15.xyz * r8.zzz;        // 高光补偿色

  // 各区域加权求和
  r14.xyz = r14.xyz * r10.www;
  r9.yzw = r12.xzw * r9.zzz + r14.xyz;
  r9.yzw = r11.xyz * r4.yyy + r9.yzw;
  r9.xyz = r13.xyz * r9.xxx + r9.yzw;

  r9.xyz = r9.xyz * r18.xyz;         // Diffuse × 高光补偿
  r9.xyz = r15.xyz * r16.xyz + r9.xyz; // + 间接光
  r9.xyz = r9.xyz + -r5.xyz;
  r5.xyz = cb4[58].www * r9.xyz + r5.xyz;  // ★ r5.xyz = 最终Diffuse ★


  // ═══════════════════════════════════════════════════════════════
  // 九、次表面散射近似 (Subsurface Scattering)
  // ═══════════════════════════════════════════════════════════════

  r4.y = cmp(0.5 < v7.z);            // v7.z = Subsurface标记
  if (r0.w == 0) {
    // 背光检测: NdotV vs NdotL 差异
    r9.xyz = r4.yyy ? r3.xyw : v2.xyz;
    r0.w = dot(r1.xyz, float3(0.289999992,0.600000024,0.109999999)); // 亮度
    r8.z = dot(r10.xyz, r9.xyz);     // 视线与法线的夹角
    r9.x = r8.z + -r8.w;             // NdotV - NdotL

    // 背光因子 (模拟次表面散射的透光感)
    r9.x = saturate(-r9.x * 3 + 1);  // 背光越强值越大
    r9.y = r9.x + r9.x;
    r9.x = sqrt(r9.x);
    r9.x = r9.y * r9.x;
    r9.x = min(1, r9.x);

    // 混合Half-Lambert和背光
    r9.y = r8.w * 0.5 + 0.5;
    r9.z = saturate(r8.w);
    r9.x = r9.y * r9.x + -r9.z;
    r9.x = r9.x * 0.5 + r9.z;

    // 色相保持的亮度调整 (log2空间)
    r9.yzw = log2(BaseColor);
    r9.xyz = r9.xxx * r9.yzw;
    r9.xyz = exp2(r9.xyz);

    // lerp回原始色
    r11.xzw = r9.xyz + -r1.xyz;
    r11.xzw = r11.xzw * float3(0.5,0.5,0.5) + r1.xyz;
    r9.xyz = -r11.xzw + r9.xyz;
    r9.xyz = r8.zzz * r9.xyz + r11.xzw;
    r1.xyz = r4.www ? r9.xyz : r11.xyz;  // ★ r1.xyz = 次表面散射后的BaseColor ★
  }


  // ═══════════════════════════════════════════════════════════════
  // 十、Specular — Toon高光 + GGX PBR 双分支
  // ═══════════════════════════════════════════════════════════════

  // --- 10.1 电介质F0计算 (Fresnel零度入射反射率) ---
  r0.w = -r0.x * 0.959999979 + 0.959999979;  // (1 - Metallic) × 0.96
  r9.xyz = r1.xyz * r0.www;                   // Diffuse部分 = BaseColor × (1-Metallic)

  // F0 = lerp(0.04, BaseColor, Metallic)
  r11.xyz = float3(-0.0399999991,-0.0399999991,-0.0399999991) + r1.xyz;
  r11.xyz = r0.xxx * r11.xyz + float3(0.0399999991,0.0399999991,0.0399999991);

  // --- 10.2 Roughness计算 (从SpecularMask反推) ---
  r4.w = -r0.z * cb4[140].w + 1;     // r0.z = SpecMask, cb4[140].w = 粗糙度乘数
                                      // Roughness = 1 - SpecMask × multiplier
  r4.w = r4.w * r4.w;                // Roughness² (GGX用)
  r8.z = r4.w * 4 + 2;               // k = Roughness² × 4 + 2 (GGX归一化因子)
  r9.w = r4.w * r4.w;                // Roughness⁴
  r10.w = r4.w * r4.w + -1;          // Roughness⁴ - 1

  // --- 10.3 光照亮度归一化 (Tone Mapping预处理) ---
  r12.xyz = cb0[2].xyz + r5.xyz;     // 全局环境光 + Diffuse
  r12.xyz = v8.xyz + r12.xyz;        // + 间接光
  r11.w = dot(r12.xyz, float3(0.212672904,0.715152204,0.0721750036)); // 亮度
  // ... Tone mapping ...
  r12.xyz = r11.www * r5.xyz;        // 归一化后的光照

  // --- 10.4 Toon Specular路径 ---
  // 根据MatID选择_SpecularColor (cb4[75-79])
  r13.xyz = r2.www ? cb4[76].xyz : cb4[75].xyz;
  r13.xyz = r2.zzz ? cb4[77].xyz : r13.xyz;
  r13.xyz = r2.yyy ? cb4[78].xyz : r13.xyz;
  r13.xyz = r2.xxx ? cb4[79].xyz : r13.xyz;

  // 根据MatID选择_ToonSpecular (cb4[144-146])
  r12.w = r2.w ? cb4[144].z : cb4[144].y;
  r12.w = r2.z ? cb4[144].w : r12.w;
  r12.w = r2.y ? cb4[145].x : r12.w;
  r12.w = r2.x ? cb4[145].y : r12.w;

  r13.w = cmp(0.5 < r12.w);          // Toon Specular启用?
  if (r13.w != 0) {
    // Half-Vector: H = normalize(L·NdotL + V)
    r3.z = saturate(r3.z * 1.5 + -0.5);
    r14.xyz = r6.xyz * r5.www + r10.xyz;
    r14.w = dot(r14.xyz, r14.xyz);
    r14.w = rsqrt(r14.w);
    r14.xyz = r14.xyz * r14.www;     // H = normalize(L+V)

    r14.x = saturate(dot(r3.xyw, r14.xyz));  // ★ NdotH ★

    // Schlick Fresnel: F = 1 - (NdotH × _ShapeSoftness)²
    r3.z = r3.z * r3.z;
    r3.z = -r3.z * r14.x + 1;       // Fresnel term

    // _HighlightShape / _SpecularRange 除法 → specMask
    r3.z = r4.x + -r3.z;
    r13.w = max(9.99999975e-06, r13.w);
    r4.x = saturate(r3.z / r13.w);   // Toon specular mask

    // 最终Toon高光
    r3.z = cb4[146].w * r4.x;        // × _SpecIntensity
    r13.xyz = r3.zzz * r13.xyz;      // × _SpecularColor
    r13.xyz = r13.xyz * r11.xyz;     // × F0
  }

  // --- 10.5 GGX PBR Specular路径 (非Toon材质走这里) ---
  r3.z = cmp(r12.w < 0.5);          // 非Toon → 走GGX

  // Half-Vector
  r6.xyz = r6.xyz * r5.www + r10.xyz; // L·NdotL + V
  r4.x = dot(r6.xyz, r6.xyz);
  r4.x = rsqrt(r4.x);
  r6.xyz = r6.xyz * r4.xxx;          // H = normalize(L+V)

  // _SpecularRange (cb4[143-144])
  r4.x = r2.w ? cb4[143].y : cb4[143].x;
  r4.x = r2.z ? cb4[143].z : r4.x;
  r4.x = r2.y ? cb4[143].w : r4.x;
  r4.x = r2.x ? cb4[144].x : r4.x;

  // ★ GGX 分布项 D ★
  // D = Roughness⁴ / (π · (NdotH² · (Roughness⁴-1) + 1)²)
  r5.w = r4.x * r8.w;               // SpecRange × Roughness
  r5.w = saturate(r5.w * 0.75 + 0.25);
  r12.w = dot(r3.xyw, r6.xyz);      // NdotH
  r12.w = r12.w * r4.x;
  r12.w = saturate(r12.w * 0.75 + 0.25);
  r6.x = dot(r10.xyz, r6.xyz);      // VdotH
  r4.x = r6.x * r4.x;
  r4.x = saturate(r4.x * 0.75 + 0.25);

  r6.x = r12.w * r12.w;             // NdotH²
  r6.x = r6.x * r10.w + 1.00001001; // NdotH²·(Roughness⁴-1)+1
  r4.x = r4.x * r4.x;
  r6.x = r6.x * r6.x;               // denom²
  r4.x = max(0.100000001, r4.x);
  r6.x = r6.x * r4.x;

  // ★ Smith G 项 (几何遮蔽) ★
  r6.x = r6.x * r8.z;               // × k
  r6.x = r9.w / r6.x;               // Roughness⁴ / (D·k)
  r0.z = saturate(-r0.z * cb4[140].w + r6.x);
  r0.z = r0.z * r5.w;
  r4.w = max(9.99999975e-06, r4.w);
  r0.z = r0.z / r4.w;               // G / Roughness²

  // --- 10.6 _SpecIntensity 和最终镜面高光 ---
  // 根据MatID选择 (cb4[141-142])
  r4.w = r2.w ? cb4[142].x : cb4[141].w;
  r4.w = r2.z ? cb4[142].y : r4.w;
  r4.w = r2.y ? cb4[142].z : r4.w;
  r4.w = r2.x ? cb4[142].w : r4.w;

  // 额外缩放 (cb4[168-169])
  r6.x = r2.w ? cb4[169].x : cb4[168].w;
  r6.x = r2.z ? cb4[169].y : r6.x;
  r6.x = r2.y ? cb4[169].z : r6.x;
  r6.x = r2.x ? cb4[169].w : r6.x;

  r4.w = r6.x * r4.w;
  r0.z = r4.w * r0.z;

  // --- 10.7 Toon vs Standard 最终分支 ---
  r0.z = saturate(10 * r0.z);       // Toon: saturate×10 → 硬边
  r0.z = 100 * r0.z;                // ×100 放大

  r4.x = 0.166663334 / r4.x;        // 1/(6·VdotH) 近似
  r4.x = min(1, r4.x);
  r4.x = r4.x * r5.w;
  r4.x = 100 * r4.x;                // Standard: 1/(6·VdotH)×100
  r0.z = r3.z ? r0.z : r4.x;        // Toon? → Toon路径 : Standard路径

  // ★ 最终镜面高光叠加 ★
  r6.xyz = r0.zzz * r13.xyz;         // SpecFinal × SpecColor
  r13.xyz = r6.xyz * r12.xyz;        // SpecFinal × SpecColor × LightColor
  r6.xyz = r6.xyz * r12.xyz + float3(-1,-1,-1);
  r6.xyz = max(float3(0,0,0), r6.xyz); // 过曝clamp
  r13.xyz = r9.xyz * r12.xyz + r13.xyz; // Diffuse + Specular


  // ═══════════════════════════════════════════════════════════════
  // 十一、Rim Glow 边缘光
  // ═══════════════════════════════════════════════════════════════

  r0.z = cmp(cb4[147].x >= 0.5);    // Rim Glow开关

  // 根据MatID选择_RimGlowLightColor (cb4[80-84])
  r14.xyz = r2.www ? cb4[81].xyz : cb4[80].xyz;
  r14.xyz = r2.zzz ? cb4[82].xyz : r14.xyz;
  r14.xyz = r2.yyy ? cb4[83].xyz : r14.xyz;
  r14.xyz = r2.xxx ? cb4[84].xyz : r14.xyz;

  r14.xyz = r14.xyz * r0.yyy;        // RimColor × EmissionMask
  r14.xyz = r14.xyz * r1.xyz;        // × BaseColor
  r14.xyz = r0.zzz ? r14.xyz : 0;    // 开关控制

  // --- 主Rim Glow计算 (Fresnel NdotV) ---
  r0.z = cmp(0.5 >= cb0[196].y);
  if (r0.z != 0) {
    r0.z = dot(r7.xyz, r10.xyz);    // NdotV (视线与法线)
    r0.z = saturate(-r0.z * 0.5 + 0.5); // Fresnel = 1 - NdotV*0.5

    // 多次smoothstep幂乘产生锐利边缘
    r1.x = r0.z * 0.800000012 + 0.200000003;
    r1.y = r3.y * 0.5 + 0.5;
    r3.z = r1.y * r1.y;
    r1.y = -0.200000003 + r1.y;
    r1.y = saturate(1.25 * r1.y);

    // smoothstep³ 柔和
    r3.z = r1.y * -2 + 3;
    r1.y = r1.y * r1.y;
    r1.y = r3.z * r1.y;

    // smoothstep^5 锐利边缘
    r3.z = r1.y * r1.y;
    r3.z = r3.z * r3.z;
    r3.z = r3.z * r1.y;

    // 区分光照面/阴影面的Rim参数
    r10.xyz = r1.www ? float3(1,0.300000012,-1) : float3(0.5,1,-0.5);

    // Fresnel^20 产生极窄的Rim
    r0.z = r0.z * r0.z;
    r0.z = log2(r0.z);
    r0.z = 20 * r0.z;
    r0.z = exp2(r0.z);

    // 最终Rim = RimColor × RimMask
    r1.x = r1.x * r1.y;
    r1.xyz = r1.xxx * r4.xzw;
  }


  // ═══════════════════════════════════════════════════════════════
  // 十二、Emission + 环境反射 + 最终输出
  // ═══════════════════════════════════════════════════════════════

  // --- 12.1 Emission (已在4.3节计算好 r0.y) ---
  // r0.y = 处理后的EmissionMask × _EmissionColor → 加回最终色

  // --- 12.2 环境反射 (来自Light Probe的镜面高光) ---
  r15.xyz = v8.xyz * r11.www;        // 间接光 × 亮度归一化
  r13.xyz = r15.xyz * r9.xyz + r13.xyz; // Diffuse+Specular + 间接光

  // 灯光镜面高光 (来自StructuredBuffer)
  if (r7.w != 0) {
    r16.xyz = lightProbeSpecular;    // 灯光探针的镜面高光颜色
  }
  r17.xyz = r11.www * r1.xyz;        // Fresnel × BaseColor
  r13.xyz = r16.xyz * r17.xyz + r13.xyz; // + 灯光镜面高光
  r6.xyz = r13.xyz + r6.xyz;         // + Specular溢出

  // ★ 最终颜色写入MRT (o0 = 主颜色) ★
  // o0 = Diffuse + Specular + Rim + Emission + 环境反射
  // (具体输出由前面的计算决定)
}


// ═══════════════════════════════════════════════════════════════
// 十三、MatCap 系统 (独立SubProgram变体, _MatCap=1时启用)
// ═══════════════════════════════════════════════════════════════
//
// 以下代码来自另一个SubProgram变体 (_NAP_SHADER_QUALITY_HIGH + MatCap启用)
// 位于原文件约第877000行

/*
  // --- MatCap 开关 ---
  r2.x = cmp(cb0[22].z >= 0.5);     // cb0[22].z = _MatCap 布尔开关

  if (r2.x != 0) {
    // --- 13.1 获取当前层索引 ---
    // r4.w = 循环中的层索引 (0~4, 共5层)

    // --- 13.2 MatCap UV 计算 ★核心公式★ ---
    // 视图空间法线的XY分量 → 映射到[0,1] UV空间
    r2.xy = cb0[118].xy * r3.yy;     // ModelView矩阵行0.xy × 法线.y
    r2.xy = cb0[117].xy * r3.xx + r2.xy;  // + 行1.xy × 法线.x
    r2.xy = cb0[119].xy * r3.ww + r2.xy;  // + 行2.xy × 法线.z(在w通道)
    r2.xy = r2.xy * float3(0.5,0.5) + float3(0.5,0.5);
    // ★ 等价于: Transform(normal, View).xy * 0.5 + 0.5 ★

    // --- 13.3 折射偏移 (如果_MatCapRefract=1) ---
    r1.w = cmp(0.5 < cb4[layer+15].z);  // Refract开关
    if (r1.w != 0) {
      r0.y = cb4[layer+15].w * r0.y;    // Refract深度
      r10.xy = cb4[layer+0].xy * UV + cb4[layer+0].zw;  // 折射UV偏移
      r2.xy = r0.yy * r2.xy + r10.xy;   // MatCap UV += 折射偏移
    }

    // --- 13.4 UV动画 ---
    r10.x = cb4[layer+10].w * cb0[40].y;  // U Speed × time
    r10.y = cb4[layer+15].x * cb0[40].y;  // V Speed × time
    r10.xy = r10.xy + r2.xy;              // 最终MatCap UV = 基础UV + 动画偏移

    // --- 13.5 MatCap2DArray 采样 ---
    r10.z = cb4[layer+10].x;              // 数组层级索引 (_MatCapTexID)
    r10.xyzw = t7.Sample(s2_s, r10.xyz).xyzw;  // ★ 采样MatCap贴图 ★

    // --- 13.6 颜色色调应用 ---
    r12.xyz = cb4[layer+5].xyz * r10.xyz;  // MatCap颜色 × _MatCapColorTint
    r0.y = r10.w * r0.w;                   // Alpha × ColorBurst

    // --- 13.7 混合模式分支 ---
    // BlendMode = cb4[layer+15].y
    r0.w = cmp(cb4[layer+15].y < 0.5);     // BlendMode == 0?
    if (r0.w != 0) {
      // ★ AlphaBlended 混合: lerp(BaseColor, MatCap, mask) ★
      r0.w = saturate(cb4[layer+10].z * r0.y);  // AlphaBurst
      r13.xyz = r12.xyz * cb4[layer+10].yyy + -r1.xyz; // TintedMatCap - BaseColor
      r1.xyz = r0.www * r13.xyz + r1.xyz;     // lerp
    } else {
      r0.w = cmp(cb4[layer+15].y < 1.5);     // BlendMode == 1?
      if (r0.w != 0) {
        // ★ Add 混合: BaseColor + MatCap × intensity ★
        r0.w = saturate(cb4[layer+10].z * r0.y);
        r13.xyz = r12.xyz * r0.www;
        r1.xyz = r13.xyz * cb4[layer+10].yyy + r1.xyz;
      } else {
        // ★ Overlay 混合 (Photoshop Overlay算法) ★
        r10.xyz = r10.xyz * cb4[layer+5].xyz + float3(-0.5,-0.5,-0.5);
        r10.xyz = saturate(r10.xyz * cb4[layer+10].yyy + r12.xyz);
        r0.y = saturate(cb4[layer+10].z * r0.y);
        r10.xyz = float3(-0.5,-0.5,-0.5) + r10.xyz;
        r10.xyz = r0.yyy * r10.xyz + float3(0.5,0.5,0.5);

        // Overlay = 2*Base*Blend (if Base<0.5) else 1-2*(1-Base)*(1-Blend)
        r12.xyz = r10.xyz * r1.xyz;
        r13.xyz = r12.xyz + r12.xyz;         // 2*Base*Blend
        r14.xyz = float3(1,1,1) + -r1.xyz;
        r14.xyz = r14.xyz + r14.xyz;         // 2*(1-Base)
        r10.xyz = float3(1,1,1) + -r10.xyz;  // 1-Blend
        r10.xyz = -r14.xyz * r10.xyz + float3(1,1,1); // 1-2*(1-Base)*(1-Blend)
        r14.xyz = cmp(r1.xyz >= float3(0.5,0.5,0.5)); // Base>=0.5?
        r14.xyz = r14.xyz ? float3(1,1,1) : 0;
        r10.xyz = -r12.xyz * float3(2,2,2) + r10.xyz;
        r1.xyz = r14.xyz * r10.xyz + r13.xyz; // 选择分支 → 最终Overlay结果
      }
    }
  }

  // --- 13.8 MatCap层间叠加 ---
  // 5层MatCap依次处理, 每层的结果 r1.xyz 作为下一层的BaseColor输入
  // 最终 r1.xyz = 包含所有层MatCap的颜色
*/

// ═══════════════════════════════════════════════════════════════
// 附录A: cb4 MatCap层参数偏移表
// ═══════════════════════════════════════════════════════════════
//
// 每层占用16个float4 (从 layer+0 到 layer+15)
//
//   offset      | 通道  | 参数名                  | 用途
//   ------------|-------|------------------------|------------------
//   layer+0     | .xy   | UV Offset              | 折射UV基准偏移
//   layer+0     | .zw   | UV Offset 2            | 折射UV缩放
//   layer+5     | .xyz  | _MatCapColorTint       | 颜色色调
//   layer+10    | .x    | _MatCapTexID           | 贴图数组层级索引
//   layer+10    | .y    | _MatCapColorBurst      | 颜色爆发强度
//   layer+10    | .z    | _MatCapAlphaBurst      | Alpha爆发强度
//   layer+10    | .w    | _MatCapUSpeed          | U方向滚动速度
//   layer+15    | .x    | _MatCapVSpeed          | V方向滚动速度
//   layer+15    | .y    | _MatCapBlendMode       | 0=AlphaBlended 1=Add 2=Overlay
//   layer+15    | .z    | _MatCapRefract         | 折射开关
//   layer+15    | .w    | _RefractDepth          | 折射深度

// ═══════════════════════════════════════════════════════════════
// 附录B: 关键cb4索引速查
// ═══════════════════════════════════════════════════════════════
//
// cb4[58]    = _Color (色调修正)
// cb4[60-64] = ShallowColor[1-5]
// cb4[65-69] = ShadowColor[1-5]
// cb4[75-79] = _SpecularColor[1-5]
// cb4[80-84] = _RimGlowLightColor[1-5]
// cb4[135].y  = 当前Material ID
// cb4[136]   = _RampTexParams0 (.x=min, .y=UVscale, .z=shadowBlend, .w=Shallow1)
// cb4[137]   = Shallow/Shadow 级联 (.w=S1, .z=S2, .y=S3, .x=S4)
// cb4[138].x  = ShadowNormalBias (阴影法线偏移)
// cb4[138].z  = Emission Enable
// cb4[140].xx = UVScale, .yy=_BumpScale, .z=金属度缩放, .w=粗糙度乘数
// cb4[141-142]= _SpecIntensity per tier
// cb4[143-144]= _SpecularRange per tier
// cb4[144-146]= _ToonSpecular / _HighlightShape
// cb4[147].x  = _RimGlow Enable
// cb4[165-166]= ShadowIntensity per tier
// cb4[168-169]= SpecIntensity额外缩放

// ═══════════════════════════════════════════════════════════════
// 附录C: 纹理寄存器映射
// ═══════════════════════════════════════════════════════════════
//
// t0 = Shadow Cascades (Texture2DArray, SampleCmpLevelZero)
// t1 = Light Probe Data (StructuredBuffer)
// t2 = Overlay/Detail Texture
// t3 = _MainTex — RGB = Base Color
// t4 = _LightTex — RG = Tangent Normal, B = Diffuse Bias
// t5 = _OtherDataTex — R=MatID, G=Metallic, B=SpecularMask
// t6 = _OtherDataTex2 — R=Transparency, G=Smoothness, B=EmissionMask
// t7 = MatCap2DArray / Shadow Cascade / _CharacterRampTex (取决于SubProgram变体)


// ╔══════════════════════════════════════════════════════════════╗
// ║  附篇一: NapAvatarStandardEnergy — 能量特效 Fragment Shader  ║
// ╚══════════════════════════════════════════════════════════════╝
//
// 来源: miHoYo/Character/NapAvatarStandardEnergy
// 这个Shader比主Shader简化很多:
//   - 没有Specular/Anisotropy/Silk/ThreadMap
//   - MatCap使用2D贴图(非2DArray)
//   - 多了OutlineFX和Glitch特效

#if 0  // --- Energy Shader 代码开始 ---

// --- 纹理声明 (Energy专用, 与主Shader不同) ---
Texture2D<float4> t7 : register(t7);  // 遮罩贴图 (用于MatCap遮罩)
Texture2D<float4> t6 : register(t6);  // MatCap 2D贴图 (不是2DArray!)
Texture2D<float4> t5 : register(t5);  // _OtherDataTex2 (Emission等)
Texture2D<float4> t4 : register(t4);  // _OtherDataTex (Metallic等)
Texture2D<float4> t3 : register(t3);  // _LightTex (法线贴图)
Texture2D<float4> t2 : register(t2);  // _MainTex (Albedo)
Texture2D<float4> t0 : register(t0);  // 遮罩/特效贴图

// cb3: 材质参数 (Energy专用, 约152个float4)
cbuffer cb3 : register(b3) { float4 cb3[152]; }
//   [47].xy   = MatCap UV Scale/Offset
//   [107]     = MatCap ColorTint
//   [120].xy  = MatCap UV 动画速度, .zw = 动画偏移
//   [145].y   = MatCap 开关
//   [146].x   = Refract 开关

void main_Energy(
  float4 v0 : TEXCOORD0,    // UV0
  float4 v1 : TEXCOORD1,    // UV1
  float4 v2 : TEXCOORD2,    // 世界法线 (TBN的N) + w=世界X
  float4 v3 : TEXCOORD3,    // 世界切线 (TBN的T) + w=世界Y
  float4 v4 : TEXCOORD4,    // 世界副法线 (TBN的B) + w=世界Z
  out float4 o0 : SV_Target0
)
{
  float4 r0,r1,r2,r3,r4,r5,r6;

  // ═══════════════════════════════════════════════
  // 1. MatCap UV 计算 (Energy使用投影位置而非视图法线!)
  // ═══════════════════════════════════════════════

  r1.w = cmp(0.5 < cb3[145].y);      // cb3[145].y = _MatCap 开关
  if (r1.w != 0) {
    r1.w = cmp(cb3[146].x < 0.5);    // Refract开关 (cb3[146].x = _RefractDepth?)
    r3.zw = r1.ww ? v0.xy : v1.xy;   // 选择UV通道

    // ★ Energy的MatCap UV使用投影后的世界位置, 不是法线! ★
    r1.w = cb0[117].z * v3.w;        // 投影矩阵 × 世界Y
    r1.w = cb0[116].z * v2.w + r1.w; // + 投影矩阵 × 世界X
    r1.w = cb0[118].z * v4.w + r1.w; // + 投影矩阵 × 世界Z
    r1.w = cb0[119].z + r1.w;        // + W分量

    // 缩放偏移后映射到[0,1]
    r3.xy = r3.xy * cb3[47].xy + cb3[47].zw;  // cb3[47].xy = UV缩放
    r3.xy = float2(0.5,0.5) + r3.xy;          // [-1,1] → [0,1]

    // UV动画: cb3[120].xy = 滚动速度, × cb0[40].y = 时间
    r4.xw = cb3[120].xy * cb0[40].yy + cb3[120].zw;
    r3.xy = r4.xw + r3.xy;           // 最终MatCap UV = 基础UV + 动画

    // ═══════════════════════════════════════════════
    // 2. MatCap 采样 + 混合
    // ═══════════════════════════════════════════════

    r5.xyzw = t6.Sample(s4_s, r3.xy).xyzw;    // ★ 采样MatCap 2D贴图
    r6.xyzw = cb3[107].xyzw * r5.xyzw;        // × _MatCapColorTint

    // ColorBurst: 颜色爆发 (脉冲效果)
    // cb3[107].w = burst强度, cb0[40].y = sin(time)用于脉冲
    r1.w = cb3[107].w * cb0[40].y;
    r1.w = r1.w * 0.5 + 0.5;
    r1.w = r1.w * r1.w;              // 平方使脉冲更明显

    // 混合模式分支 (cb3[120].z = BlendMode)
    r4.z = cmp(cb3[120].z < 0.5);   // BlendMode == 0?
    if (r4.z != 0) {
      // ★ AlphaBlended混合: lerp(BaseColor, MatCap, mask) ★
      r3.x = r6.w * r1.w;            // Alpha × burst
      r5.xyz = cb3[107].xyz * r5.xyz + -r1.xyz;
      r4.xyz = r3.xxx * r5.xyz + r1.xyz;
    } else {
      // ★ Add混合: BaseColor + MatCap ★
      r1.w = -r6.w * r1.w + 1;
      r4.xyz = r6.xyz * r3.xxx + r1.www;
      r4.xyz = r4.xyz * r1.xyz;     // × BaseColor
    }

    // MatCap遮罩: t7 = 遮罩贴图
    r5.xyzw = t7.Sample(s0_s, v0.xy).xyzw;
    r3.x = cb3[121].x * r5.x;        // cb3[121].x = 遮罩强度

    // 最终混合: 遮罩控制MatCap可见性
    r1.xyz = r3.xxx * r4.xyz + r0.yzw;
  }

  // ═══════════════════════════════════════════════
  // 3. 最终输出
  // ═══════════════════════════════════════════════
  o0.xyzw = float4(r1.xyz, 1.0);
}

#endif  // --- Energy Shader 代码结束 ---


// ╔══════════════════════════════════════════════════════════════╗
// ║  附篇二: NapAvatarStandardEye — 眼睛 Fragment Shader         ║
// ╚══════════════════════════════════════════════════════════════╝
//
// 来源: miHoYo/Character/NapAvatarStandardEye
// 独有特性:
//   - _EyeColorMap 眼睛颜色贴图
//   - _LightMapUVFlip 光照贴图UV翻转
//   - _FixedLightDirection 固定光照方向
//   - Face Shadow Point SDF阴影

#if 0  // --- Eye Shader 代码开始 ---

void main_Eye(
  float4 v0 : TEXCOORD0,   // UV0
  float4 v1 : TEXCOORD1,   // 光照贴图UV
  float3 v2 : TEXCOORD2,   // 世界法线
  float4 v3 : SV_POSITION0,
  uint   v4 : SV_IsFrontFace0,
  out float4 o0 : SV_Target0
)
{
  float4 r0,r1,r2,r3;

  // ═══════════════════════════════════════════════
  // 1. 基础贴图采样
  // ═══════════════════════════════════════════════

  // _MainTex: RGB = Albedo
  r0.xyzw = _MainTex.Sample(sampler, v0.xy).xyzw;

  // _EyeColorMap: 眼睛专用颜色贴图
  r1.xyzw = _EyeColorMap.Sample(sampler, v0.xy).xyzw;

  // ═══════════════════════════════════════════════
  // 2. SDF脸部阴影 (与Face Shader共用逻辑)
  // ═══════════════════════════════════════════════

  // _LightTex: R = Face light angle mapping (SDF查找坐标)
  //            G = lighting function
  r2.xyzw = _LightTex.Sample(sampler, v1.xy).xyzw;

  // _LightMapUVFlip: 控制光照贴图的UV方向
  //   Auto(0) = 使用原始UV
  //   UVX(1)  = U方向翻转
  //   FlipX(2) = 整轴翻转

  // ═══════════════════════════════════════════════
  // 3. 光照计算 (固定光照方向)
  // ═══════════════════════════════════════════════

  // 当_FixedLightDirection=1时, 使用头矩阵变换后的固定方向
  // _HeadMatrixWS2OS: 头部世界→对象空间矩阵 (4个Vector)

  // ═══════════════════════════════════════════════
  // 4. 最终眼睛颜色
  // ═══════════════════════════════════════════════

  // EyeColor × MainTex + 光照
  o0.xyz = r1.xyz * r0.xyz;  // 眼睛贴图 × Albedo
  o0.w = 1.0;
}

#endif  // --- Eye Shader 代码结束 ---


// ╔══════════════════════════════════════════════════════════════╗
// ║  附篇三: NapAvatarStandardFace — 脸部 Fragment Shader        ║
// ╚══════════════════════════════════════════════════════════════╝
//
// 来源: miHoYo/Character/NapAvatarStandardFace
// 独有特性:
//   - _NoseLine 鼻子线条系统 (HoriDisp / LkDnDisp)
//   - _NoseSpecularScale 鼻子高光缩放
//   - _HeadMatrixWS2OS 头部矩阵 (4个Vector)
//   - 3级Material (Face/EyeBrows)

#if 0  // --- Face Shader 代码开始 ---

void main_Face(
  float4 v0 : TEXCOORD0,   // UV0
  float4 v1 : TEXCOORD1,   // UV1 (光照贴图UV)
  float3 v2 : TEXCOORD2,   // 世界法线
  float4 v3 : TEXCOORD3,   // 世界空间位置
  float4 v4 : SV_POSITION0,
  out float4 o0 : SV_Target0
)
{
  float4 r0,r1,r2,r3,r4;

  // ═══════════════════════════════════════════════
  // 1. 脸部Shallow/Shadow选择 (3级, 比主体的5级简单)
  // ═══════════════════════════════════════════════

  // v6.z = 脸部光照贴图前向参数 (从顶点着色器传入)
  // 这是Face Shader的核心 — 使用SDF风格的脸部阴影
  r2.xy = cmp(v6.zz < float2(0.600000024, 0.800000012));
  // 阈值: <0.6 → Shallow, 0.6~0.8 → Shadow1, >0.8 → Shadow2

  r2.z = r2.y ? cb4[110].z : cb4[110].y;  // Shadow2 : Shadow1
  r2.z = r2.x ? cb4[110].w : r2.z;        // Shallow

  // ═══════════════════════════════════════════════
  // 2. 法线归一化
  // ═══════════════════════════════════════════════

  r4.y = dot(v3.xyz, v3.xyz);      // 法线长度平方
  r4.y = rsqrt(r4.y);              // 1/长度
  r4.yzw = v3.xyz * r4.yyy;        // 归一化世界法线

  // ═══════════════════════════════════════════════
  // 3. 光源方向
  // ═══════════════════════════════════════════════

  r5.xyz = cb0[53].xyz + -v4.xyz;  // cb0[53] = 主光源位置, v4 = 世界位置
                                     // → 指向光源的方向向量

  // ═══════════════════════════════════════════════
  // 4. 脸部光照贴图SDF查找
  // ═══════════════════════════════════════════════

  r6.y = trunc(v6.z);              // 取整v6.z (脸部光照贴图参数)
  // v6.z是连续值, trunc后做阈值比较

  // 3组颜色: cb4[62]=Shadow1, cb4[63]=Shadow2, cb4[64]=Shallow
  r7.xyz = r6.zzz ? cb4[63].xyz : cb4[62].xyz;  // Shadow2 : Shadow1
  r6.yzw = r6.yyy ? cb4[64].xyz : r7.xyz;        // Shallow : Shadow

  // ═══════════════════════════════════════════════
  // 5. 鼻子线条系统 (Face独有)
  // ═══════════════════════════════════════════════

  // _NoseLineHoriDisp: 水平消失值 (0.92)
  //   控制鼻子线条在水平视角下的可见性
  // _NoseLineLkDnDisp: 低头消失值 (0.62)
  //   控制角色低头时鼻子线条的消失程度
  // _NoseSpecularScale: 鼻子高光缩放
  // _NoseLineScale: 鼻子线条缩放

  // ═══════════════════════════════════════════════
  // 6. _HeadMatrixWS2OS 头部矩阵
  // ═══════════════════════════════════════════════

  // 4个Vector构成4×4矩阵, 用于将世界空间向量变换到头部的对象空间
  // 用于计算相对于头部的光照方向 (SDF脸部阴影的核心)
  //
  // _HeadMatrixWS2OS0 = (1,0,0,0)  // 第0行
  // _HeadMatrixWS2OS1 = (0,1,0,0)  // 第1行
  // _HeadMatrixWS2OS2 = (0,0,1,0)  // 第2行
  // _HeadMatrixWS2OS3 = (1,1,1,0)  // 平移分量

  // ═══════════════════════════════════════════════
  // 7. 最终输出
  // ═══════════════════════════════════════════════

  // Face Shader有多个Material组 (最多3组: 面部皮肤、眉毛等)
  // _MaterialNum控制当前使用哪组参数
  // 每组有独立的: ShallowColor, ShadowColor, AlbedoSmoothness
  //
  // 还有 _BrightMultiplier (1~3组) 控制亮度倍增

  o0.xyz = /* Shallow/Shadow混合后的颜色 */;
  o0.w = 1.0;
}

#endif  // --- Face Shader 代码结束 ---


// ╔══════════════════════════════════════════════════════════════╗
// ║                        全文完                                 ║
// ║  相关文档:                                                    ║
// ║    Pyrios_UE_Material_Spec.md — UE5材质重建操作规范           ║
// ║    NTE_AnimationSystem_Analysis.md — NTE动画系统分析          ║
// ╚══════════════════════════════════════════════════════════════╝
