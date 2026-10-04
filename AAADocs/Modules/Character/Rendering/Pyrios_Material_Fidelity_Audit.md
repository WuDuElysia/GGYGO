# Pyrios 材质还原差距核查（2026-09-24）

## 对照输入

- 游戏截图：`References/Pyrios_Game_Reference_01.png`、`References/Pyrios_Game_Reference_02.png`、`References/Pyrios_Game_Reference_03.png`。第一张适合检查能量爆发和后处理；第三张是 2026-09-25 提供的游戏内正常场景正面全身参考，优先用来校准角色常态配色和区域明暗。
- 原始数据：`F:/AnimeStudio/Exports/Animator/Avatar_Male_Size03_Pyrois_Model/Materials/MAT_Pyrois_*.json`、同目录 PNG，以及 `F:/AnimeStudio/Exports/Shader/miHoYo_Character_NapAvatarStandard.shader`。项目 `Content/Characters/Player/Pyrios/Materials/` 内的 Body_1 JSON 与原导出文件 SHA-256 相同：`599609426FC1AD57F7898875C8B447C2EED064D1FBE8D9617692EBFC2FC1F326`。
- UE 对照：`Saved/PyriosMeshTierFixedFocused.png` 为旧模型资产视口；`Saved/PyriosMeshNoMatcapFocused.png` 为临时关闭 MatCap 的诊断画面。2026-09-26 初次重建后见 `Saved/PyriosMCPMeshEditor_20260926.png`；降低预览增益并重新打开模型窗口后的画面见 `Saved/PyriosMCPMeshEditor_Final_20260926.png`。

## 结论

上一版只读取了 JSON 的四张主体贴图、五组浅/暗色和少量标量，主光照用一个固定 `smoothstep` 两色带代替原 Shader。MatCap 的贴图与强度曾由脚本手写，而非按 JSON 层位接线。因此上一版是 **风格近似**，不能称为原材质等价还原。Unity 导出格式本身不是主因：JSON 和贴图保留了逐材质参数，导出的 Shader 也可供核查。JSON 不包含运行中的全局灯光、阴影、曝光、LUT 和后处理，单独复刻材质仍无法复制游戏截图。

## 已确认的差距与修正

| 项目 | 证据 | 当前处理 |
| --- | --- | --- |
| 材质 ID 顺序 | `_OtherDataTex.R` 主要值为 `255/179/129`，对应原 Shader 的 `4 - floor(R*5)` 分组；上一版按从小到大选 `ShallowColor1..5`。 | 已按反序修正五组浅/暗色。 |
| MatCap 槽位 | Body_1 JSON 使用第 2/4 槽，Body_2 使用第 1/2/4 槽，Weapon01 使用第 2/3/5 槽；上一版只放两张手选贴图，并以手写 0.05～0.4 强度叠加。 | 五槽现在从 JSON 读取纹理、Tint、ColorBurst、AlphaBurst 和 BlendMode；仅对相应材质 ID 组启用。混合公式仍待逐变体核对。 |
| MatCap 遮罩 | 三张 `_M` 图的 Alpha 均为 1；将它作为遮罩再把多个 MatCap 加到整个人体会抬白所有区域。临时禁用 MatCap 后，UE 胸甲立刻恢复为深灰。 | 去掉全身叠加；保留 JSON `_UseMatCapMask` 开关。 |
| 编辑器 MatCap 方向 | 上一版用运行时组件写入的 CameraRight/Up；静态材质球没有实时相机向量。 | 材质内改用世界法线转 View 空间，静态预览可随视角变化。 |
| Diffuse 阴影 | 旧 HLSL 只用 `smoothstep(0.32,0.48)` 混合两个色带；当前 Shader 还包含顶点遮罩、间接光和逐组阴影参数。 | 2026-09-26 在 UE 主材质加入法线高度补偿、`_LightTex.B` 偏移、两阈值形成的三段明暗和五组 `PerObjectShadowIntensity`。阈值为编辑器校准值，仍非原版逐变体等价实现。 |
| 高光/边缘光 | 旧高光是固定 `pow(N·H,40)`，边缘光为单一白色 Fresnel；JSON 有五组高光与亮面/暗面边缘光参数。 | 当前改为由 `_M.G`、`_M.B`、`_A.G` 与 JSON `_Glossiness`、`_Metallic`、`_SpecIntensity` 控制的 GGX 近似，并按材质 ID 取五组高光色、边缘光色与阴影强度。仍缺原版各向异性和精确混合公式。 |
| 编辑器校准 | 原版运行时全局参数和目标夜景的曝光数值未从材质 JSON 导出。 | `Pyrios_Editor_Calibration.json` 只保存 UE 预览所需的 Diffuse/Specular/MatCap 增益、冷色 Tint 和 Ramp 阈值；它们是可调整的近似值，不冒充游戏参数。 |
| 场景与特效 | 原图是冷蓝夜景，亮银边和暗蓝主体共存，中心有强烈能量光与 Bloom；当前资产编辑器使用日间预览，材质采用 Unlit/Emissive，默认白色主光，`Body_FX01` 溶解/能量材质尚未移植。 | 需要用固定曝光的参考场景分别校准材质、光照和后处理；材质球只用于检查接线。 |

## 后续还原顺序

1. 以导出 Shader 的实际启用变体核查 Material ID、Ramp、MatCap 混合与五组镜面参数，不把已有注释文档当作最终实现依据。
2. 在固定相机、姿态、曝光和蓝色主光的 UE 对照场景中复拍；先对比无 MatCap 的 Albedo/Ramp，再逐组打开 MatCap 与高光。
3. 移植 `Body_FX01` 的能量/溶解路径及中心发光，最后调 Bloom、描边和场景调色。

2026-09-26 通过本地 UE MCP 在正在运行的 UE 5.8 编辑器内重建并保存 `M_Pyrois_Toon`、描边材质和三份 MI；两个主材质 D3D12 重新编译无错，验证脚本核对了 JSON 高光/边缘光/逐组阴影、校准参数、贴图和模型默认槽位。第二次降低预览增益后，模型视口相同亮色区域的固定取样均值约从 198 降至 174（8 位 RGB；只用于本地改动前后对照）。资产编辑器预览仍比游戏正常场景截图更亮，缺固定曝光的同场景对比，因此不标记为完成还原。

## 新增常态视觉基准（Reference 03）

游戏截图中的胸口和肩部是冷银蓝高光，面部/颈部与躯干内层是深蓝黑，披风与下半身主体保持深灰蓝；胸口光点和右臂是局部高饱和蓝色发光。头盔本体为银色，但不能把面部开口整体做成银白高反射。普通环境中仍有清楚的亮暗区域，不能依赖满屏 Bloom 或整体提高 Emissive 来取得金属感。截图经过游戏自身曝光、调色和场景光照，不能直接把像素值当材质参数。

## 导出文件的含义

`MAT_Pyrois_Body_1.json` 等四份 JSON 是 Unity `Material` 对象的导出：顶层只有 `m_Shader`、`m_SavedProperties` 和 `m_Name`。`m_Shader` 保存 Shader 名称和资源引用 ID；`m_SavedProperties` 保存贴图槽、整数、浮点数与颜色值，包括未绑定贴图的空槽。以 Body_1 为例，导出包含 30 个贴图槽、1 个整数、250 个浮点参数和 141 个颜色参数。这些是某个材质实例传给 Shader 的输入，不包含其照明、MatCap、Ramp 和混合运算程序，也不包含游戏运行时的灯光、阴影、曝光或后处理。

`F:/AnimeStudio/Exports/Shader/miHoYo_Character_NapAvatarStandard.shader` 是 2026-07 的旧版 Shader 导出资料，约 75 MB。文件头写明 `This is *not* a valid shader file`；内部有属性、SubShader/Pass 与大量 D3D11 SubProgram 的反编译表达式（如 `cb0[...]` 常量寄存器），可辅助逆向运算，但不是原始 ShaderLab/HLSL 源码，不能直接导入 UE 或按文本一键转换。下节记录 2026-09-25 对当前游戏资源的重新导出；FX Shader 已补齐。

## 当前游戏 Shader 重新导出（2026-09-25）

AnimeStudio CLI 对 `F:/ZenlessZoneZero Game/ZenlessZoneZero_Data/StreamingAssets/Blocks` 的 10,095 个资源文件重建 Shader 索引，在 1,328 条记录中找到 487 个不同 Shader 名称。旧 `F:/AnimeStudio/AssetMaps/zzz_live.map` 指向已不存在的资源文件，不能当作当前版本使用。当前索引与完整导出均放在 `F:/AnimeStudio/Exports/Shader/ZZZ_20260925/`，其中 Shader 分为 `PyriosFullText`、`FXFullText`、`SceneFullText` 及对应的 `PyriosRaw`、`SceneRaw`。本轮有针对性地导出 23 个 Shader，并未导出全部 487 种。

| 范围 | 当前版本的证据 | 用途与边界 |
| --- | --- | --- |
| 角色主体和武器 | `PyriosFullText/miHoYo_Character_NapAvatarStandard.shader`；PathID `3888839570379262989` 与 Body_1、Body_2、Weapon01 JSON 一致。Pass 包含 `ShadowCaster`、`CharacterOutlineDeferred`、`CharacterToonDeferred`、`CharDepthOnly`。 | 核对角色材质分组、光照、描边与阴影公式。 |
| Body_FX01 | `FXFullText/miHoYo_Particles_Particles_Dissolve_CustomColor_Mask_Cap.shader`；PathID `-8234219882186656621` 与 Body_FX01 JSON 一致。 | 补齐原先缺失的溶解/透明特效 Shader；Pass 为 `TransparentFullRes` 与 `TransparentHalfRes`。 |
| Pyrois 特效候选 | `PyriosFullText/miHoYo_Particles_Particles_PyroisExecute.shader`。 | 资源以 Pyrois 命名，包含 `Forward` 和 `ForwardHalfRes`；尚无材质或运行时抓帧证据证明它用于所给截图。 |
| 场景与屏幕效果 | `SceneFullText/` 中的 `miHoYo_Scene_Lit`、`Hidden_Universal Render Pipeline_ScreenSpaceShadows`、`Universal Render Pipeline_PerObjectShadowResolve`、`Hidden_Universal Render Pipeline_FinalPost`、`Hidden_Universal Render Pipeline_UberPost`、`Hidden_PostProcessing_Nap Bloom` 等 20 个。 | 这些是场景表面、阴影、Bloom/调色相关候选；资产存在不等于截图那一帧全部启用。 |

原版 CLI 输出目录缺 `HLSLDecompiler.dll`，文本转换失败后回退到会崩溃的原生反汇编器。本轮只在 `Saved/AnimeStudioShaderTool/` 的临时副本中补齐 DLL 并禁用这个崩溃回退；未修改 `F:/AnimeStudio/AnimeStudio/` 原始工具。23 个文本文件均导出，D3D11 变体可读，原始序列化数据另存为 `.dat`。这些导出仍不是可直接编译的 Unity 或 UE 源码，也不包含运行时的实际 Pass 调度、光源数值、曝光、LUT 和后处理配置；后续仍需游戏帧或同机对照来确认哪些变体和全局参数真正参与目标画面。

## Pyrios 主光参数与 NTE 对照（2026-09-26）

当前版本的 `NapAvatarStandard.shader` 暴露 `_LightDirectionFromCamera`、`_OverrideMainLightParam[1..5]`、`_OverrideMainLightColor[1..5]`、`_ReceiveShadows`、`_ReceiveAddShadows`、`_PerObjectShadowIntensity[1..5]`，还有隐藏的 `_CharacterMainLightData` 与 `_PerObjectShadowData`。Body_1 材质 JSON 中方向从相机读取的开关和主光覆盖值均为 0，接收阴影和附加阴影为 1，逐物体阴影强度为 1。这说明 JSON 保存了光照响应开关和材质调节值，但主光方向/运行时阴影数据需要游戏管线提供；不能从 JSON 还原一盏固定灯。

NTE 导出的 `Exports/HT/Content/Characters/Player/002_edgar/ter/weapon/MI_player_002_edgar_1.json` 指向角色 Toon 材质族；`Exports/HT/Content/CoreMaterials/Character/ToonMaterial/Master/MM_CharacterToon_Lit.json` 的 `ShadingModel` 为 `MSM_Toon`。`MPC/MPC_Toon_XL.json` 保存全局的 `OverrightLightVector`、`OverrightSunVector`、`RampContrast`、`RampMidGray` 等参数；其他角色实例还出现 `SunLightDir`、`LocalSunColor`、`LightdirZMul`、`EnablePointLights`。这是“场景光方向/调节值 + 每角色材质参数”的可借鉴分层。导出的 UE JSON 没有完整可执行材质图或游戏修改过的 Toon Shading Model 实现，不能直接搬进项目的标准 UE 5.8 引擎。

2026-09-26 的项目实现中，`M_Pyrois_Toon` 使用 Unlit/Emissive；旧版 `UGGYGOPyriosRenderComponent` 读取 UE DirectionalLight 的方向、颜色和强度，按可配置参考值、响应曲线及上限写入 `SceneLightStrength`，使 Toon 材质接收受控主光。当前关卡的 DirectionalLight 强度为 10、颜色为白色，故默认参考强度取 10，静态 MI 与运行时基准强度均为 0.65。此缩放只限制色带漫反射、镜面和边缘光，MatCap 与自发光仍独立；逐像素级联阴影、Skylight/点光响应和游戏后处理还没有等价移植。

UE MCP 中将 Body 1/2 的 `MatCapGain` 从 0.22 下调到 0.11、Weapon 从 0.30 下调到 0.18，并保留在 `Pyrios_Editor_Calibration.json`；这是编辑器亮度修正，不是导出的游戏参数。缩略图 `Saved/PyriosLightMatCapReduced_20260926.png` 仍比游戏常态参考亮，后续需用同一光向、同一曝光和姿态对照。保存并重启编辑器后，C++ 完整构建成功；UE MCP Simulate 验证 MID 的 `SceneLightStrength` 随主光强度 10 → 2.5 → 40 变化为 0.65 → 0.325 → 1.0（上限）。临时测试角色已删除，关卡灯光未被改动。

## 通用组件整改与视觉还原边界（2026-09-29）

2026-09-29：统筹离线测试22/22、完整 DLL 链接/冷启动、GGYGO自动化10/10（含两项渲染测试）通过，自动化零错误零警告。BP 单字段恢复后已编译、单包保存并冷回读15项参数/三槽/描边，legacy=false、autoActivate=true、is_dirty=false；最终哈希9e093db8…05dac3，双旧备份与原baseline保留。本会话MCP真实PIE确认3个表面MID及Leader Pose描边，灯强度10/2.5/0/40/10对应输出0.65/0.325/0/1/0.65。已恢复灯强度并停止自己启动的PIE，BP/原地图未变脏、哈希未变。结束时地图查询变化及MCP可读性限制另记，未宣称原版视觉还原完成。

源码中的光照/材质生命周期已迁入 `UGGYGOCharacterRenderComponent`；旧类仅保留序列化身份。角色名称判断和内置材质路径已移除，Pyrios 参数与槽位改由 BP 显式配置，该 BP 的迁移已保存并冷回读通过。无有效主灯时直接光为零；材质恢复校验 Mesh、槽位和当前 MID 所有权。详见 [迁移与验收](Character_Render_Migration.md)。

本批没有重建材质、重新调色或证明原 Shader 等价还原。MatCap 独立于主光、GGX/Ramp 近似、单射线遮挡以及静态预览与运行光向不同仍是观感差异来源。NTE 的 `MSM_Toon` 和 MPC 支持场景/角色分层的设计参考；场景公共 MPC、编辑器实时同步光照与完整 Toon 着色模型仍是方案，尚未实现。

## 光源接入方案复核（2026-09-29，只读分析）

- 再读当前 ZZZ Shader 和 Body_1、Body_2、Weapon01 三份 JSON：三者 `_LightDirectionFromCamera=0`、五组 `_OverrideMainLightParam=0`，`_ReceiveShadows=1`、`_ReceiveAddShadows=1`、五组 `_PerObjectShadowIntensity=1`、`_AdditionalLightIntensity=1`。参数存在不代表截图帧必然启用所有对应路径；实际光向、阴影资源与附加灯来自运行时，隐藏 `_CharacterMainLightData` 的分量含义不能仅凭名称认定。
- NTE 实际目录为 `F:/FModel/Output/Exports/HT/Content/`。`Characters/Player/002_edgar/ter/weapon/MI_player_002_edgar_1.json` 的父实例为 `MI_CharacterToon_Lit`；`CoreMaterials/Character/ToonMaterial/Master/MM_CharacterToon_Lit.json` 标记 `MSM_Toon`，缓存参数包括 `UseLocalLight`、`EnablePointLights`、`SunLightDir`、`LightdirZMul`、`LightNormalStrength`、`MatcapNomralStrength`。`MPC/MPC_Toon_XL.json` 的 `OverrightLightVector` 默认 (0,0.707,0.707)，另有太阳/月亮覆盖向量与 Ramp 调节。它们是导出默认值及接口证据，不能当作运行帧灯光或完整算法。
- 本机 `F:/UE_5.8/Engine/Source/Runtime/Engine/Classes/Engine/EngineTypes.h` 的着色模型枚举没有 `MSM_Toon`。该 NTE 主材质导出 `LoadedMaterialResources=[]`，未提供可直接执行的 Toon 着色实现。
- 当前生成脚本将材质设置为 `MSM_UNLIT`，结果接 Emissive；组件只传方向光方向、颜色、限幅强度和粗略遮挡。MatCap 在受主光控制的项之后独立混合，环境底色也是常量。因此“UE 默认 Lit 再照一遍”不符合当前接线；关灯仍亮、反光与场景脱节有明确待查路径，但本轮未取得新截图来量化各项贡献。

建议下一轮先固定曝光/相机对照，把主光色带、高光、MatCap、环境底色和真正自发光逐项隔离；提供每角色的光强响应、色带、反射环境响应和增益配置。MatCap 可保留艺术最低亮度并按环境控制，不能把它当自发光，也不应简单乘太阳强度导致所有反射随关太阳消失。补充编辑器预览更新，使非 PIE 拖动光源也能观察；静态 MI 默认参数仍负责独立材质球预览。

公共场景光参数若改由 MPC 提供，须有每 World 唯一写入者，角色组件只消费并写角色覆盖，不让多个角色竞争公共值；角色材质公式与常调值留在材质函数/MI/配置资产。此为设计建议，尚未授权为新架构实现。少量选定局部灯可另做方向/颜色/衰减近似，但不会自动获得 UE 点光/聚光阴影；完整场景多灯及逐像素阴影需要渲染器/自定义 Toon 着色模型方案，普通 Unlit 加几个参数不能等价实现。不要把已经算完的 Toon 颜色送进 Default Lit 再照明。
