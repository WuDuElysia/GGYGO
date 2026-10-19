# Pyrios 渲染实现

> 返回 [[计划蓝图]] · [[Character/结构|角色结构]] · [[GGYGO_结构_角色与组件.canvas|结构图]] · [[GGYGO_流程_Pyrios渲染.canvas|流程图]]

## 当前验收状态

2026-09-29：统筹离线测试22/22、完整 DLL 链接/冷启动、GGYGO自动化10/10（含两项渲染测试）通过，自动化零错误零警告。BP 单字段恢复后已编译、单包保存并冷回读15项参数/三槽/描边，legacy=false、autoActivate=true、is_dirty=false；最终哈希9e093db8…05dac3，双旧备份与原baseline保留。本会话MCP真实PIE确认3个表面MID及Leader Pose描边，灯强度10/2.5/0/40/10对应输出0.65/0.325/0/1/0.65。已恢复灯强度并停止自己启动的PIE，BP/原地图未变脏、哈希未变。结束时地图查询变化及MCP可读性限制另记，未宣称原版视觉还原完成。

旧类路径与 `StylizedRenderComponent` 名称保留；旧 `bAutoConfigurePyrios` 只供迁移。运行逻辑属于 `UGGYGOCharacterRenderComponent`，无角色名判断或资产路径加载。迁移脚本与门禁见项目 `AAADocs/Character_Render_Migration.md`。

## 当前源码链路（BP 配置已迁移并冷回读）

| 环节 | 输入 → 接口 → 结果 |
| --- | --- |
| 组件归属 | `AGGYGOHeroCharacter` 构造 `StylizedRenderComponent`；`BP_PC_Pyrios` 继承该默认子组件。 |
| 材质装配 | `RefreshMaterials()` 先释放旧绑定；BeginPlay 后且激活时读取 Mesh 与显式 `MaterialSlots`，准确槽名匹配 → MID + 原覆盖所有权记录。空配置不自动加载角色资产。 |
| 描边 | `bEnableOutline`、显式 `OutlineMaterial` 与表面 MID 就绪 → `UpdateOutline()` 创建 Leader Pose 壳；关闭碰撞、投影阴影与 Decals，未绑定表面的槽透明。 |
| 光照 | 显式 `KeyLight` 或自动弱缓存的有效 DirectionalLight → 方向、颜色、限幅强度、角色级遮挡 → MID。显式灯不可用不选替代灯，无灯则直接光为零。 |
| 更换与结束 | 换装前 `ReleaseMaterials()`，配置完成后 `RefreshMaterials()`；Tick 检测 Mesh/槽变更则释放等待刷新。EndPlay / OnUnregister / Deactivate 均释放；只还原仍由自身持有的覆盖。 |

三个 MI：`MI_Pyrois_Body_1`、`MI_Pyrois_Body_2`、`MI_Pyrois_Weapon01`。它们与 `M_Pyrois_Toon`、`M_Pyrois_Outline` 位于 `Content/Characters/Player/Pyrios/Materials/Generated/`。生成与验证脚本分别为 `AAADocs/Scripts/build_pyrios_materials.py`、`AAADocs/Scripts/verify_pyrios_renderer.py`；通用 C++ 在 `Source/GGYGO/Character/Components/GGYGOCharacterRenderComponent.*`，原 Pyrios 同名文件只保留兼容子类。

编辑器预览已落盘：`AAADocs/Scripts/bind_pyrios_editor_preview.py` 将三个 MI 写入 Pyrois 骨骼模型的默认槽位；`BP_PC_Pyrios` 的 Mesh 无材质覆盖，模型缩略图、材质球和角色蓝图视口都直接显示 Toon 材质，不依赖 `BeginPlay`。`MAT_Pyrois_Body_FX01` 槽位绑定身体 FX 材质，见下文「身体 FX」。`build_pyrios_materials.py` 重跑时也会绑定；`verify_pyrios_renderer.py` 已检查槽位。编辑器静态预览只覆盖表面 Toon 材质；描边壳仍由运行时组件创建。

## 光照边界

### 表面材质：NapAvatarStandard 逐行移植

`M_Pyrois_Toon` 是 Unlit 材质，整个着色在一个 Custom 节点里，代码 `AAADocs/Scripts/nap_avatar_toon.hlsl` 由 `gen_nap_avatar_hlsl.py` 生成：取 `miHoYo/Character/NapAvatarStandard` 的 `CharacterToonDeferred` Pass、变体 `{_NAP_SHADER_QUALITY_HIGH, _MATCAP_ON, _FX_UNCLIP_SCREEN_IMAGE_OVERRIDE_2_TONE, _FX_UNCLIP_SECONDARY_EMISSION_RIM_GLOW}` 的 D3D11 反汇编（后两个关键字打开屏幕贴图、二次自发光与特殊武器自发光分支，Pyrios 胸口与右臂的蓝光就在这里），用同一 Shader `.dat` 里该 Pass 的反射表把 `cb0~cb4[i]` 还原成属性名，其余代码逐行保留。为什么不能走 UE Lit：这个 Pass 自己算完整的卡通光照并直接写颜色，再交给 UE 的 BRDF/GI/天光会算两遍。

```
// 原 Pass 的像素流程（保留函数式结构，省略寄存器细节）
albedo = MainTex * _Color ; N = TBN(LightTex.xy * _BumpScale) ; M = OtherDataTex ; A = OtherDataTex2
group  = M.r 分五档（<0.2 → 第5组 … ≥0.8 → 第1组）；matId = 4 - floor(5*M.r)
L      = lerp(V, 主光方向, _Color.w) ; ndl = dot(N, L)
s      = lerp(ndl, 高度补偿ndl, 顶点色.a) + 2*(LightTex.b*2-1)          // 明暗偏移
带权   = 五段分段线性(s, _AlbedoSmoothness[group])                          // 亮/亮过渡/中/暗过渡/暗
带权  *= 阴影(r8.w/r9.w) 拆成的 lit/shadow 带                               // KeyLightVisibility
light  = Σ 带权 * (_ShallowColor/_ShadowColor[group] * _Post*Tint 或 _Skin*Tint) * 主光色
if MatCap 组有贴图: albedo = blend(albedo, MatCapTex[group](视空间法线) * Tint, mode, Burst)   // 先于光照
if !皮肤: albedo 按亮度做 pow 微调
diffuse = albedo*(1-0.96*metal) * light * 亮度压缩(_CharacterLightTonemapParams)
spec    = ToonSpecular/HighlightShape 分支 * _SpecularColor[group] * _SpecIntensity
color   = diffuse + spec + albedo * EntityAmbient + 自发光(_Emission)
color   = 经 _DecolorizationContrast / _Override
if _SecondaryEmission:     color += SecondaryEmissionTex(UV2)*mask*_SecondaryEmissionColor     // Pyrios 关
if _SpecialWeaponEmission: color += Eff_Mask_032(UV2*ST) * LKJ_02.r(UV2) * _SpecialWeaponEmissionColor  // 右臂/躯干蓝光
if _ScreenImage:           color = lerp(color, _ScreenColor*ScreenTex(屏幕UV), ScreenMask.r(UV0))       // 胸前纹路
rim     = 原 SV_Target1 的边缘光（_RimGlow*ForChara、_RimGlowLightColor[group]）
out     = color + rim ; out += max(0, max(out) - 1) * HighlightBleed       // 近似游戏后处理的强光推白
```

被替换的部分：逐对象阴影与级联阴影采样改为组件的 `KeyLightVisibility`（仍按 `_ReceiveShadows` 混合）；角色实体缓冲 `t1` 的灯色/灯位置改为组件写入的 `KeyLightColor * SceneLightStrength` 与 `KeyLightDirectionWS`，其余字段改为 `EntityParams/EntityAmbient/EntitySkinAmbient`；MatCap 贴图数组换成五张独立贴图，组号即切片号；运动矢量和 GBuffer 标记位输出删除；运行时 FX 覆盖分支（`_OverrideRimGlow`、`_Override2Tone`）删除，Pyrios 材质里都是 0，生成时要求如此。网格 UV1 是描边用平滑法线、UV2 是自发光 UV，原顶点着色器把 TEXCOORD2 传给像素的 `v1`，所以材质里的 "Use UV2" 读网格 UV2。运算在 Unity 约定下进行（Y 向上、米），UE 向量交换 Y/Z 后只参与点积；Unity 法线贴图 G 通道朝 +V，UE 副切线朝 +V_UE，所以 `NormalYSign=-1`。`_SkinMatId` 在反射表中是 int，按取整比较，否则 4.0 的位模式永远不等于组号。

改了会坏什么：把材质改成 Lit 会重复光照；把 `Color` 属性当 `Vector` 处理（不做 Gamma→Linear）会让暗色、阴影色整体发亮；把 MatCap 混合挪到光照之后会让银甲亮面不受明暗影响而发白。

参数来源：材质属性由 `pyrios_material_plan.py` 从三份 JSON 读入。Unity 的 `Color` 属性做 Gamma→Linear：LDR 逐分量走 sRGB 曲线；HDR（最大分量 >1）按“gamma 底色 × 强度”换算，即 `lin(rgb/max)*max`。逐分量 `pow(x,2.2)` 会把右臂颜色 (2.5,6.5,47.9) 变成 (7.6,62,4983)，绿色也远超 1，整条手臂只能是青白；按底色×强度是 (0.2,0.8,47.9)，与游戏的深蓝 + 白纹一致。这一换算是对照游戏画面选定的，没有 Unity 源码层面的直接证据。贴图 sRGB 照抄 Unity 导入设置 `m_ColorSpace`（`AAADocs/Assets/Pyrios/Rendering/UnityMaterials/TextureSettings/*.json`，由 AnimeStudio 导出；工具原本不输出这个字段，已在 `AnimeStudio/Classes/Texture2D.cs` 补上）：D 图与特效遮罩/噪声是 sRGB，N/M/A 与 `Eff_Noise_095` 是线性。特效遮罩若按线性采样，0.2 的遮罩底色就是 0.2 而不是 0.03，自发光底区整体过亮。MatCap 打包数组（`_MatCapTexID_*` 等）在游戏里由运行时脚本填写，JSON 里 TexID 都是 100（未分配），这里按“该组有贴图就用组号作切片”重建，属于推断。场景/角色级全局量（`_Post*Tint`、`_Skin*Tint`、`EntityAmbient`、`_CharacterLightTonemapParams`、`_RimGlow*ForChara` 等）材质里没有，放在 `AAADocs/Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json`，是编辑器起始值，不是原游戏数据；对照游戏画面调色时改这个文件后重跑 `build_pyrios_materials.py`。

UE 的 DirectionalLight 是运行时主光输入；Lumen、Skylight、点光源和 Lit BRDF 不叠加到 Pyrios 表面。可见性射线只提供角色级遮挡，不等于逐像素投影阴影。

2026-10-05 验证：PCD3D_SM6 编译通过（PS 1042 指令）；离线测试 16/16；`verify_pyrios_renderer.py` 只读核对（参数回读、贴图 sRGB 与 Unity 一致）。骨骼网格已用带 UV1/UV2 的 FBX 经 Interchange 重导（`reimport_pyrios_mesh_uv.py`，原 FBX 保留为 `.uv0only.bak`，原资产备份在 `Saved/MeshReimportBackup/`），几何与材质连接与原 FBX 逐项一致。SceneCapture 对照图与逐版文字结论在 `AAADocs/References/Captures/PyriosToon/INDEX.md`：v6 右臂为饱和深蓝带明暗，强处发白；外甲有镀铬明暗。仍缺：胸口白芯（游戏里像独立光斑特效，`MAT_Pyrois_Body_FX03` 用 `Eff_Flare_005`，挂载对象未找到）、锁骨深色区阶梯色块未查明。注意：命令行里贴图异步编译未完成时截图会显示灰色占位，拍摄时需 `-dpcvars=Editor.AsyncTextureCompilation=0` 并强制 mip 常驻。尚未与游戏截图并排调色。UE 骨骼网格保留了顶点色：用 SceneCapture 读回材质里的顶点色，得到 RG=0.5、A=0，与 FBX 一致，所以高度补偿 ndl 的权重为 0，与游戏相同。

通用 C++ 的参考强度/响应/输出系数/上限默认均为 1。组件的强度公式是 `clamp(OutputScale * (灯强/ReferenceKeyLightIntensity)^Response, 0, MaxKeyLightStrength)`。`KeyLightTint` 和 `OccludedKeyLightVisibility=0.35` 也暴露在组件 Details/蓝图中；这些字段可按角色调节。2026-09-29 已完成新组件真实 PIE 主光响应复测，结果见末节。`SceneLightStrength` 乘到主光颜色上（即原 Shader 的 `_AvatarMainLightColor`），进入漫反射、高光和亮度压缩。原 Shader 的这盏灯是角色专用主光，不随场景灯的物理强度变化，所以 `BP_PC_Pyrios` 现在设为 `KeyLightIntensityResponse=0`、`KeyLightOutputScale=1`（`AAADocs/Scripts/set_pyrios_light_response.py`，原 BP 备份在 `Saved/RenderLightResponseBackup/`）：UE 的 DirectionalLight 只提供方向和颜色，强度恒为 1，与 MI 的静态预览一致。参考强度/上限字段保留但不再影响结果。

角色表面不经过 UE 的任何光照计算：Unlit 不吃 Lit BRDF、Lumen GI、天光、点光、SSAO 和投影阴影。仍会作用在角色像素上的只剩整屏阶段：指数高度雾/体积雾（场景开了才有）、Bloom、tonemapper 与调色。原游戏的 UberPost/Bloom 没有移植；要让角色颜色更接近 shader 计算值，可在关卡 PostProcessVolume 里把 Tone Curve Amount 调到 0 并关闭雾，但这会同时改变整个场景，属于关卡层的选择。当前只有一个主 DirectionalLight 和角色级遮挡输入，未接点光、Skylight 或原版逐像素阴影。

2026-09-29 再读 ZZZ 三份主体/武器 JSON 和 NTE 导出后，建议继续使用“场景提供光源、Toon 材质控制响应”的分层，先隔离校准主光/环境/MatCap/自发光，并补非 PIE 光照同步。NTE 的 `MSM_Toon`、MPC 光向及 `EnablePointLights` 是接口证据，不含底层实现；本机标准引擎枚举没有该 Toon 模型。公共 MPC 若实施须由每 World 唯一来源写入，角色只消费和覆盖；当前仍为建议，未增加公共写入者。局部灯传参只能近似，完整多灯/逐像素阴影需要渲染器接入。具体文件、三份 JSON 参数值和方案边界见项目 `AAADocs/Pyrios_Material_Fidelity_Audit.md` 的“光源接入方案复核”。现有 Canvas 的实现边界不变。

该组件是角色视觉适配，不写 ASC、CMC 或 AnimBP 状态。它没有加入 PawnExtension 的 InitState 队列；材质装配依赖 Mesh 是否就绪，不依赖 ASC。若以后角色 Mesh 在 `BeginPlay` 之后才赋值，赋值方需要调用 `RefreshMaterials()`。

## 历史验证与视觉缺口（2026-09-24～26）

以下证据来自旧版组件及已保存材质，不代表本次通用实现和蓝图迁移已完成验收。

- `GGYGOEditor Win64 Development` 编译通过；两个主材质在完整编辑器 D3D12 下重新编译无错误。
- UE Simulate 中用临时 `ACharacter`、Pyrois Mesh 和该组件验证了自动替换材质。把临时组件描边宽度调到 3 cm 时能清楚看到描边；项目默认仍为 0.6 cm。临时角色已移除。
- 游戏正常场景参考为深蓝主体、亮银装甲边缘和局部强蓝光；旧 UE 预览大面积泛白。原导出 JSON 与项目副本哈希一致。此前只移植少量参数、Material ID 顺序反了、MatCap 手写且整身叠加；编辑器预览与游戏夜景的曝光/光照也不同。2026-09-26 已通过本地 UE MCP 8000 更新并保存主材质与三个 MI，三段明暗、五组高光/边缘光和编辑器校准参数编译、接线检查通过；降低增益并重新打开模型资产后的截图在 `Saved/PyriosMCPMeshEditor_Final_20260926.png`。默认环境下银甲仍偏亮，缺固定曝光的同场景比较。原版 Ramp 参数、级联阴影、准确 MatCap/各向异性和 FX01 仍未实现，不能标记为视觉还原完成。详见项目 `AAADocs/Pyrios_Material_Fidelity_Audit.md`。
- `ABP_Pyrios` 的七条旧 `Locomotion_*` 过渡函数调用已在原资产内替换为语义字段/查询节点，编辑器编译并保存通过；`BP_PC_Pyrios` 随后重新编译通过。编辑器视口已确认白灰/蓝色 Toon 材质即时可见。未做本轮目标关卡的参考图并排调色。
- 项目 `.gitignore` 仅放行部分自研 `Content` 路径。生成的五个材质 `.uasset` 与已修改默认槽位的 Pyrois 骨骼模型都在被忽略的美术目录，跨 checkout 时须通过资产管线一起交付；`ABP_Pyrios` 在 Git 白名单内。

## 新增视觉参考与导出数据边界（2026-09-25）

项目保存了新的游戏内常态正面全身参考 `AAADocs/References/Pyrios_Game_Reference_03.png`：银蓝头盔与胸肩外甲、深蓝黑面部及躯干内层、暗灰蓝披风与腿部，以及局部强蓝色胸口和右臂发光。后续材质校准以此约束角色常态配色；截图仍包含游戏环境光、曝光与调色，像素值不能直接当材质参数。

AnimeStudio 的 `MAT_Pyrois_*.json` 是 Unity 材质对象的序列化结果，保存 `m_Shader` 名称/引用及 `m_SavedProperties` 的贴图槽、整数、浮点和颜色，并不包含 Shader 运算程序。原有约 75 MB 的 `F:/AnimeStudio/Exports/Shader/miHoYo_Character_NapAvatarStandard.shader` 是 2026-07 的旧导出，文件自述并非有效 Shader 源文件。2026-09-25 用 AnimeStudio CLI 重新扫描当前游戏的 10,095 个资源文件，找到 1,328 条 Shader 记录、487 个不同名称，并针对性导出 23 个 Shader 到 `F:/AnimeStudio/Exports/Shader/ZZZ_20260925/`，索引副本也在该目录。旧 `zzz_live.map` 指向已经不存在的资源文件。

新导出的 `miHoYo/Character/NapAvatarStandard` 的 PathID `3888839570379262989` 与 Body_1、Body_2、Weapon01 材质 JSON 一致；`miHoYo/Particles/Particles_Dissolve_CustomColor_Mask_Cap` 的 PathID `-8234219882186656621` 与 Body_FX01 一致，原先缺失的 FX Shader 已补齐。另找到以 Pyrois 命名的 `Particles_PyroisExecute`，但暂不能确认它参与参考截图。场景候选包括 `miHoYo/Scene/Lit`、`ScreenSpaceShadows`、`PerObjectShadowResolve`、`FinalPost`、`UberPost`、`Nap Bloom`；资产存在不证明某帧实际启用。可读导出包含属性、Pass 和反编译的 D3D11 变体，`.dat` 保存原始序列化资源，但这些仍不是可直接编译的 UE 源码，也不能替代运行时帧中曝光、LUT、光源和 Pass 调度的证据。详情见项目 `AAADocs/Pyrios_Material_Fidelity_Audit.md`。

Weapon01 的静态 JSON `_Emission=0`，当前三个 MI 中它负责剑的基本表面材质；参考图中的剑身蓝光需要另查运行时 FX、激活时序和 Bloom。Body_FX01 所在的身体 FX 已按该 Shader 重建为 UE 材质（见「身体 FX」）；`Particles_PyroisExecute` 目前只是候选，不能宣称它已经确定驱动剑光。

当前 `NapAvatarStandard.shader` 有 `_LightDirectionFromCamera`、`_OverrideMainLightParam` / `_OverrideMainLightColor`、`_ReceiveShadows`、`_ReceiveAddShadows`、逐组 `_PerObjectShadowIntensity` 等参数；Body_1 JSON 的主光覆盖为 0、接收阴影为 1，说明游戏运行时另供主光和阴影。NTE 导出的 `MM_CharacterToon_Lit.json` 使用 `MSM_Toon`，`MPC_Toon_XL.json` 提供全局光向量、Ramp 对比度等参数；可借鉴“场景光参数 + 角色实例参数”分层，但项目标准 UE 5.8 没有该游戏自定义 Toon Shading Model。当前项目使用 Unlit 材质和组件传参是可编辑、可控的近似实现，尚未复制 NTE 或 ZZZ 的渲染管线。

## 身体 FX

### 来源与绘制方式

Pyrois 的四个 `Pyrois_Body_FX_01..04` 网格（各约 100 顶点、单 submesh）蒙皮在身体骨骼上，导入 UE 后合并进骨骼网格的 `MAT_Pyrois_Body_FX01` 槽。Unity 端每个 FX 网格的 `SkinnedMeshRenderer.m_Materials` 是 `[FX04, FX01, FX02]` 三个材质；材质数多于 submesh 时 Unity 把多余材质在同一几何上依次再画，所以这是三遍叠加，FX04 在最下。FBX 只保留了一个材质名，叠加关系要从 GameObject JSON 读。

UE 一个槽只能放一个材质，所以三遍绘制在一个材质内合成：

```
// M_FX_DissolveMaskLayers，BlendMode = AlphaComposite（预乘），Unlit，双面
L1 = Layer(FX04 参数) ; L2 = Layer(FX01 参数) ; L3 = Layer(FX02 参数)
c = L1
c = L2 + c * (1 - L2.a)        // Unity One/OneMinusSrcAlpha 的 over
c = L3 + c * (1 - L3.a)
Emissive = c.rgb * EmissiveScale ; Opacity = c.a

Layer(p):                       // 对应 Particles_Dissolve_CustomColor_Mask(_Cap)，_UsingNonPSR=1
  uv  = (UV.x, 1 - UV.y)        // 回到 Unity UV 空间做 _ST、滚动、翻转
  d1  = 2*(DistTex[ch](uv*ST + frac(speed*t)) - 127/255) * _DistortionIntensity_NonPSR   // 有扭曲时
  d2  = 同上（DistTex2）
  mask = MaskTex(maskUV + d1*I + d2*I2)[ch]
  diss = DissolveTex(dissUV + d*I)[ch] ; 有溶解 ramp 时与 DissolveRampTex 相乘或取平均
  main = MainTex(mainUV + d*I)
  col  = lerp(_CustomDataColor, _MultiplyParticleColor, saturate(diss? * _LerpBrightness * main[ch]))
  rgb  = col.rgb * rampRGB * (1 + _AmbientColor.rgb)
  a    = 有溶解 ? saturate((diss - _DissolveProgress + _SoftRange*(1-p)) / _SoftRange) : 1
  a   *= main[alphaCh] * mask * 软粒子(场景深度差, 米)
  a    = saturate(_AlphaFade * pow(a, _PowerAlpha) * rampA) ; Cull Back 的层背面 a = 0
  return (pow(rgb, _PowerRGB) * a, a)
```

为什么这样写：参数名、偏移和分支来自 `F:/AnimeStudio/Exports/Shader/ZZZ_20260925` 的 D3D11 反汇编，cbuffer 偏移用同目录 `.dat` 的反射表还原成属性名，不是按属性名猜的组合方式。Unity 的 `Color` 属性按与表面材质相同的规则做 Gamma→Linear（HDR 按“gamma 底色 × 强度”），`Vector` 属性原样；FX02 的 `_MultiplyParticleColor (16.9, 8.6, 2.57)` 因此成为约 `(16.9, 3.75, 0.34)`。改了会坏什么：把合成顺序换掉会让橙色火焰层被烟层盖住；去掉 V 翻转会让滚动方向和 `_ST` 偏移反向；把 `Color` 当 `Vector` 处理会让火焰颜色偏色（暗分量过亮）。

### 资产与脚本

| 项 | 位置 |
| --- | --- |
| master 材质 | `/Game/Characters/Shared/FX/Materials/M_FX_DissolveMaskLayers`（不含角色参数，可复用于同族 FX） |
| 材质实例 | `/Game/Characters/Player/Pyrios/Materials/Generated/MI_Pyrois_Body_FX`，骨骼网格 `MAT_Pyrois_Body_FX01` 槽的资产默认材质 |
| 源数据 | `AAADocs/Assets/Pyrios/Rendering/UnityMaterials/MAT_Pyrois_Body_FX01/02/04.json`、`FXObjects/`（层顺序）、`TextureSettings/`（`m_WrapMode`、`m_ColorSpace`） |
| 生成 | `AAADocs/Scripts/build_pyrios_body_fx.py`；纯数据换算 `pyrios_fx_plan.py`；层 HLSL `fx_dissolve_mask_layer.hlsl` |

`UGGYGOCharacterRenderComponent` 不管理 FX 槽：`BP_PC_Pyrios` 的 `MaterialSlots` 不含它，Mesh 组件也没有材质覆盖，运行时直接使用资产默认的 MI；描边壳对该槽透明度为 0。FX 材质不读主光，与组件的光照参数无关。

### 当前边界

- master 只实现这三个材质启用的分支。源材质开了顶点偏移、序列帧、菲涅尔、屏幕扭曲、Mirror 寻址、旋转/Clamp UV、非软边溶解等，`pyrios_fx_plan.load_plan` 直接报错。
- 原游戏全局后处理（cb0 中的高亮压缩、Bloom 贴图叠加、全局去色）没有移植，亮度和光晕由 UE 后处理决定；`EmissiveScale`（默认 1）是唯一的整体调节口。
- 贴图 sRGB：照抄 Unity 导入设置 `m_ColorSpace`（`TextureSettings/*.json`）。11 张 FX 贴图里只有 `Eff_Noise_095`（扭曲图）是线性，其余为 sRGB；master 的贴图参数采样类型按槽决定，三层同槽贴图的色彩空间必须一致，否则 `pyrios_fx_plan` 报错。改为 sRGB 后烟雾层的遮罩/溶解值变低，黑底上几乎不可见，这是按 Unity 设置解码后的亮度。
- FX02 使用的非 Cap 变体 Shader 没有导出，按同族同属性集处理。
- 2026-10-04：master 在 PCD3D_SM6 编译通过（PS 1138 指令），MI 参数回读一致，网格槽位保存；尚未在视口或 PIE 与游戏截图对照。

## 技能特效（Niagara）

状态：试点 `Eff_Pyrois_Attack_Normal_01_01_Trail`（普攻 1 段刀光）已生成 `NS_Eff_Pyrois_Attack_Normal_01_01_Trail`，8 个渲染发射器中 7 个做进系统，Niagara 编译 UpToDate、0 个堆栈问题；**未挂到任何攻击，未与游戏画面对照**。

### 管线

```
ZZZ 资源块 (.blk)
  └ AnimeStudio Raw 导出（ANIMESTUDIO_EXPORT_ALL=1, ANIMESTUDIO_RAW_PATHID=1，文件名 = PathID）
      zzz_schema.read(类, 字节)        // 2019.4 类型树 + 逐字节核对的 miHoYo 改动；不恰好读完 → 报错
      zzz_fx_index  → 预制体层级        zzz_fx_extract → <根>.fx.json（粒子模块、渲染器、动画、脚本）
  └ zzz_fx_fetch  : 按全局 AssetMap 找材质/网格/动画/贴图所在块并导出；网格 JSON → zzz_mesh_fbx（带顶点色与全部 UV）
  └ zzz_fx_import_assets（MCP）: 贴图（sRGB/寻址/过滤/压缩照 Unity）、网格 → /Game/Characters/Shared/FX/ZZZ/
  └ zzz_fx_build（MCP）:
      for 渲染中的粒子节点:
          材质 = zzz_fx_material.plan()   // Shader 变体反汇编 → zzz_dxbc_hlsl 逐条翻译 → Custom 节点
          master/MI = zzz_fx_material_ue  // 同一方案（代码哈希）只建一个 master
          发射器 = zzz_fx_niagara.emitter_spec()
          任何未实现的功能 → skipped（写原因），不做替代效果
      NS_<根名> = zzz_fx_niagara_ue.build_system()   // 打开编辑器触发编译，读编译事件，报错即失败
```

### 材质：反汇编直译

```
plan(材质):
  变体 = 材质 m_ShaderKeywords 对应的子程序（AnimeStudio ANIMESTUDIO_SHADER_KEYWORDS 只导出这一个）
  Pass = 第一个未被 m_DisabledShaderPasses 关闭的颜色 Pass（TransparentFullRes > HalfRes …）
  ps = translate(Pass.fp, 输出 o0)      vs = translate(Pass.vp, 只要 PS 实际读取的插值)
  translate: 寄存器一律 uint4 按位存，逐条指令 asfloat/asint；cbN[i] 按 "//@" 反射表还原成属性名
             死代码消除后仍引用的全局量必须在 ZZZ_FX_Globals.json 有取值，否则报错
  VS 输入 = 按渲染器 m_VertexStreams 打包（Center/Custom1/Custom2/StableRandom → 粒子位置/动态参数 0..2）
  混合 = Pass 的 Blend [_SrcFactor] [_DstFactor] 取材质值 → One/OneMinusSrcAlpha = AlphaComposite
```

为什么直译而不是手写近似：特效 shader 是 uber shader，同名材质在不同关键字下逻辑完全不同；直译保证每个分支、通道选择、Clamp/翻转都与原版一致，代价是 Custom 节点很长（单个 PS 约 200 行）。改了会坏什么：把寄存器改成 float 存储会让比较掩码（0xFFFFFFFF）变 NaN；去掉 `//@` 反射表改用偏移猜测会让参数错位；打开 master 的额外用途（Sprite/骨骼网格）会多编一整套排列，编辑器在编译时出现过 D3D12 显存分配失败，所以只开 `bUsedWithNiagaraMeshParticles`。

全局量（场景雾、天气、全局亮度压缩、主光颜色…）在 `AAADocs/Assets/Shared/FX/ZZZ_FX_Globals.json` 取“无效果”值并写明理由；带 `disabled_by` 的项只在材质关掉对应开关时成立，否则报错。这些是本项目没有的全局系统，不是游戏数据。

### 发射器：Unity 公式写成 Set Parameters

```
发射器更新: Emitter State(Self, Once/Infinite, 时长=lengthInSec, 延迟=startDelay) + Spawn Burst / Spawn Rate
粒子生成  : URand* 随机数、Lifetime / 起始色 / 起始尺寸 / 起始旋转 / startSpeed（MinMaxCurve 按模式展开）
粒子更新  : 节点链 = 预制体根→节点的局部 TRS，Legacy Animation 的旋转/位置曲线按 System.Age 求值（Hermite）
            Position = 链(本地 +Z * speed * age)    // 形状模块关闭时 Unity 沿本地 +Z 发射
            MeshOrientation = 链旋转 ⊗ Euler(ZXY)(URot)，Scale = 尺寸 × lossyScale
            Color = 起始色 × 颜色渐变，ApplyActiveColorSpace 时转线性；DynamicMaterialParameter = CustomData
坐标: Unity (x,y,z) 米 → UE (-x, z, y)×100；四元数 (x,y,z,w) → (x,-z,-y,w)；与网格导入同一约定
```

为什么不用 Niagara 自带模块：Unity 的 MinMaxCurve/Gradient、Euler 顺序、lossyScale 与 Niagara 模块语义不完全对应，直接写表达式数值可核对。加权切线曲线按 Unity 的二维贝塞尔每段采样 16 份成折线；父级非均匀缩放下子节点任意旋转（切变）按 Unity `lossyScale` 取对角近似，只允许出现在链末端。

### 当前边界

- `Main_Distor`（屏幕扭曲，`Distortion UVMove`）跳过：需要 `_ProjectionParams.x` 与抓屏扭曲 Pass，未实现。
- 武器预制体 `Eff_Pyrois_Attack_Normal_01_01_weapon` 只有一个 MeshRenderer 节点（非粒子），未生成系统。
- 未实现即报错的模块：形状发射、速度/力/噪声/碰撞/子发射器/拖尾/灯光、公告板/拉伸渲染、Burst 无限循环与概率；`MonoEffect*` 脚本（跟随、淡出、销毁、挂点）没有类型树，数据未解析。
- 触发时机与挂点由游戏时间轴配置决定，未解析；挂到攻击上待后续按动画对照定。
- 没有在视口或 PIE 中与游戏画面对照，数值正确性只做了离线与编译核对。

| 项 | 位置 |
| --- | --- |
| Niagara 系统 | `/Game/Characters/Player/Pyrios/FX/Skill/NS_Eff_Pyrois_Attack_Normal_01_01_Trail` |
| master / MI | `/Game/Characters/Shared/FX/ZZZ/Materials/M_ZZZFX_*`、`.../MaterialInstances/MI_*` |
| 贴图 / 网格 | `/Game/Characters/Shared/FX/ZZZ/Textures/`、`.../Meshes/` |
| 中间数据 | `F:/AnimeStudio/Exports/ZZZ/Pyrois_SkillFX/`（Raw、Typed、fx_json；`*.ue_report.json` 记录跳过原因） |
| 脚本 | `AAADocs/Scripts/zzz_*.py`、`ue_mcp.py`（直连编辑器 MCP；编辑器在 PIE 时自动等待） |

## 所有权与工具约束

- 绑定记录保存槽名/索引、原 `OverrideMaterials` 值（允许 null）、本次安装 MID。释放时当前 override 必须仍等于该 MID；同 Mesh/槽恢复原覆盖，否则清到 null 使用新 Mesh 默认材质。不会覆盖后来安装的第三方材质。
- `KeyLight` 是用户配置；`ResolvedKeyLight` 是 transient 弱缓存，自动选择不污染配置。自动灯隐藏/失效/强度为零会重选，显式灯关闭时输出零直接光。
- `verify_pyrios_renderer.py` 默认只读，`--compile` 显式重编译；生成器完整预检后再写入，保存失败用 BuildJournal 报告部分结果。当前 9 项离线测试不等于 UE 资产验证。
- `GGYGO.Rendering.MaterialOwnership` 与 `GGYGO.Rendering.KeyLightLifecycle` 在最新 DLL 冷启动后通过，复测零错误零警告。WorldContext / RAII 修复已得到本次测试验证；这不代表 BP 迁移或实际关卡渲染已验收。旧标志已补 false 并保存重开核对；真实 PIE 的三槽 MID/描边与主光响应通过，详见下节。
- 静态 MI 预览已存在；编辑器实时场景光同步、公共 MPC、多点光和逐像素 Toon 阴影属于待设计/实现，不能由静态预览或完整链接通过推断已经可用。

## 迁移后的真实 PIE 验收

统筹单字段恢复后保存重开已验收，最终 BP 哈希 `9e093db8…05dac3`。本会话在原 `Untitled` 地图启动一次标准 PIE，游戏实际生成 `BP_PC_Pyrios_C_0`：Body1/Body2/Weapon 三个 MID 正确，FX 槽不覆盖；描边壳跟随 CharacterMesh0，四槽透明度为[1,1,0,1]、宽度约0.6。灯强度10/2.5/0/40/10对应全部表面MID强度0.65/0.325/0/1/0.65，关灯颜色为黑，自动选灯未写回 KeyLight。

灯恢复10后仅停止本会话PIE，末次IsPIERunning=false、角色查询为空，Editor主灯未变、BP/原地图不脏、哈希未变。停止后工具曾返回L_Movement_Test地图及其瞬态角色，随后角色为空；本会话未调用切图，原因待统筹核对，未擅自恢复地图。MCP无法直接读取bIsActive及私有清理数组，运行链有效由MID持续更新证明；内部Release分支沿用自动化证据。本次未取得截图，不作为视觉还原验收。完整证据见项目 `AAADocs/Character_Render_Runtime_Verification.md`。
