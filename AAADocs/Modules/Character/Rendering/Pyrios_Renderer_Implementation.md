# Pyrios 角色渲染契约（UE 5.8）

> 本页维护渲染职责、资源所有权和材质接口。任务进度、共享窗口及下一动作只看[当前排程](../../../Coordination/Module_Repair_Parallel_Schedule.md#当前窗口与关键路径)；旧验证见[历史证据入口](#历史证据入口)。材质公式、保存、Cold 或构建成功不能替代原图对照。

## 两条视觉线

| 工作线 | 实际用途与边界 | 准确入口 |
| --- | --- | --- |
| Raw 表面材质 | 自有临时角色、明确的 SingleNode 姿态用于隔离材质、主光和显示适配；不证明生产 ABP、CMC、动作或网络。R15 仍绑定旧 A2，不能当成 CS 同版结果；该轮未完成视觉验收。 | [R15 宿主](../../../../Saved/Codex/PyriosSurface_20261013_R15/visual_host.py)、[版本与保护](../../../../Saved/Codex/PyriosSurface_20261013_R15/visual_support_r15.py) |
| 生产 ABP | 原 GameMode/Experience/Controller 生成并附身的 Pawn，原 Mesh、生产 ABP 和自然骨 Finalize；场景由 Movement provider 交付。CS 同版消费要求真实玩家装配、实际暂停来源及两视角。当前尝试范围、缺口和共享窗口只看当前排程。 | [生产消费合同](../../../../Saved/Codex/PyriosProductionVisual_20261013_P6/README.md)、[准确运行归还](../../../../Saved/Codex/PyriosProductionVisual_20261013_P6/return.json)、[provider pin](../../../../Saved/Codex/MovementProductionScenario_20261013_P1/provider_pin.json) |

两线都按用户的游戏常态截图检查配色、区域明暗、金属反光、蓝光和描边。Raw 的静态姿态不替生产姿态，生产 idle 也不替 Lean、TurnBack、攻击或远端场景。截图生成后仍须实际看图；场景缺口按 provider 保留，不删减验收集。

生产宿主通过引擎公开 `ToolsetLibrary.GetObjectProperties` 从实际 `LevelEditorPlaySettings` CDO 原生读取单人 PIE 配置；要求 Standalone、单客户端、同进程、无额外服务器。玩家装配和暂停来源需要所属模块的公开读取接口；受保护字段不可读时明确拒绝，不以组件枚举或对象 Outer 推断权威输入指针。

## 职责与资源所有权

`UGGYGOCharacterRenderComponent` 只管理角色材质、受控主光输入及可选描边，不改场景灯、ASC、CMC 或 Animation 的权威状态，不另建帧调度。常改的槽位、材质、光强响应、色调和描边参数由角色 BP/材质资产配置。源码见[声明](../../../../Source/GGYGO/Character/Components/GGYGOCharacterRenderComponent.h)、[实现](../../../../Source/GGYGO/Character/Components/GGYGOCharacterRenderComponent.cpp)。

| 输入 → 接口 | 作用 → 输出或清理 |
| --- | --- |
| 显式 `MaterialSlots`、角色 Mesh → `RefreshMaterials()` | 先释放旧资源；BeginPlay 后且激活时按准确槽名建立 MID，记录 Mesh/槽身份、原 nullable override 和本次 MID。空配置不自动加载角色资产；配置无效给定位诊断。 |
| Mesh/装扮更换 → `ReleaseMaterials()` → 提供方更新配置 → `RefreshMaterials()` | 提供方明确管理更换边界。Tick 发现 Mesh/槽失效时释放，等待显式刷新，不猜替代 Mesh 或材质。 |
| 停用、EndPlay、OnUnregister → `ReleaseMaterials()` | 只处理当前覆盖仍等于自身 MID 的槽。同 Mesh/槽恢复原覆盖；身份改变则清自身遗留覆盖；保留第三方已接管的材质。清自身描边、预览数据和弱灯缓存。 |
| `bEnableOutline`、显式 `OutlineMaterial`、已配置表面槽 → `UpdateOutline()` | 创建自身 Leader Pose 壳，关闭碰撞、阴影和 Decals；未配置表面的槽透明。释放只销毁自己的壳。 |
| 显式 `KeyLight` 或自动弱缓存 → `SampleLighting()` → `UpdateLighting()` | 向 MID 写 `KeyLightDirectionWS`、`KeyLightColor`、`SceneLightStrength`、`KeyLightVisibility`。不改灯强度、颜色或位置，不把缓存写回配置。 |

`UGGYGOPyriosRenderComponent` 只保留旧序列化类路径；Hero 的 `StylizedRenderComponent` 名称保持。旧 `bAutoConfigurePyrios` 仅供迁移，不参与运行时资产选择。CoreRedirects 和已审计 BP 的迁移过程见[迁移历史](Character_Render_Migration.md)；不能从该历史外推其它 BP 的兼容性。

## 主光与显示适配

### 主光输入

自动模式复用同 World 的有效 DirectionalLight 弱缓存，失效后按对象路径排序选取。显式灯隐藏、关闭或无效时不换替代灯。没有有效灯时直接光颜色为黑、强度为零；MatCap、环境底色和自发光仍按材质公式计算，因此“关主灯后仍可见”本身不证明 UE 又叠加了 Lit 光照。

有效灯的强度响应为：

```text
Factor = Response == 0 ? 1 : (Intensity / ReferenceIntensity)^Response
SceneLightStrength = min(OutputScale * Factor, MaxStrength)
```

`ReferenceKeyLightIntensity`、`KeyLightIntensityResponse`、`KeyLightOutputScale`、`MaxKeyLightStrength`、`KeyLightTint`、`OccludedKeyLightVisibility` 是通用配置；角色实际值以该轮 BP 读回为准，不把历史 0.65 或固定强度模式当当前默认。非有限值、非法响应范围和必需输入无效时拒绝该生命周期；修正后显式刷新。更新沿组件既有 Tick，间隔由 `LightingUpdateInterval` 配置。

`bTraceKeyLightOcclusion` 的 Visibility 射线只给角色级遮挡。它不提供原游戏逐对象/级联阴影贴图，也不是逐像素投影阴影。

### 材质光照和后处理

表面 Master 为 Unlit，原 Toon 公式在 Emissive 路径内计算。UE DirectionalLight 作为方向、颜色和受控强度的输入；UE 默认 Lit BRDF、Lumen GI、Skylight 与点光没有再次叠加到该表面。原游戏的附加灯、阴影资源、曝光、LUT 和 Pass 调度不能从材质 JSON 推出，当前未实现完整多灯或逐像素 Toon 阴影。

项目显示适配与原 Shader 输入分开：主颜色、`RimRaw`、`BloomWeight` 分开输出，项目用 `RimCompositeGain`/`RimMaxIntensity` 合成边缘光；`ExposureCompensationWeight` 经公开原生 `EyeAdaptationInverse` 节点调节曝光抵偿，0 保留场景曝光、1 抵偿曝光。该路径不会取消雾、Bloom、tonemapper 或调色，也不是原游戏后处理等价实现。配置与公式见[纯数据计划](../../../Scripts/pyrios_material_plan.py)、[材质构建](../../../Scripts/build_pyrios_materials.py)和[场景级起始值](../../../Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json)。

## 编辑器预览

| 场景 | 输入 → 行为 | 验证边界 |
| --- | --- | --- |
| 材质球、模型资产窗口、BP 的 EditorPreview | 模型默认 MI 与其明确预览光参数 → 表面材质可直接显示，不需要 BeginPlay。 | 不从该独立预览 World 推断生产场景受光或运行组件就绪。 |
| 关卡 Editor World | 非模板、激活组件显式开启 `bPreviewSceneLighting` → 同一 `SampleLighting()` 结果经瞬态 CustomPrimitiveData 传给材质，可创建自身描边壳。 | 当前源码具备该路径；新版本的实际预览画面仍待对应视觉线验证。 |
| Game/PIE World | BeginPlay/激活后按显式槽建立 MID → 运行主光与描边。 | 真实生产 Pawn/ABP、自然骨 Finalize 和画面对照由生产视觉线核验。 |

Editor 场景预览独占主 Mesh 的 CPD 0..8：Valid、方向 XYZ、颜色 RGB、Strength、Visibility。材质必须具备准确的九个标量接口；配置槽必须与当前材质一致，未配置槽不得消费这些索引。已有序列化 CPD 默认值或预留槽被占用时明确拒绝。Mesh 尚未注册属于原生暂态，沿既有 Tick 等其就绪。

预览不改 Mesh 的材质覆盖或序列化默认。释放先核自身写入的 Valid，再只恢复仍等于自身写值的槽；外部接管的数据保留。Mesh、材质或数据所有权改变后停止并要求显式刷新，不覆盖第三方状态。

## 原 Shader 与材质数据

AnimeStudio 的 `MAT_Pyrois_*.json` 是 Unity 材质对象，含 Shader 引用、贴图、颜色、标量、关键字和禁用 Pass；它不是 Shader 程序。导出的 `.shader`/反汇编与 `.dat` 提供程序、变体和反射表，但仍不包含某个游戏帧的全局 cbuffer、角色实体缓冲、阴影资源和后处理调度。

生成链：

```text
NapAvatarStandard 的反汇编 + .dat 反射
    → gen_nap_avatar_hlsl.py
    → nap_avatar_toon.hlsl + nap_avatar_toon_inputs.json
三份材质 JSON + TextureSettings + 显式项目全局配置
    → pyrios_material_plan.py
    → build_pyrios_materials.py
    → M_Pyrois_Toon + 三份 MI + 模型默认表面槽
```

生成器选取 `CharacterToonDeferred` 的明确变体：`_NAP_SHADER_QUALITY_HIGH`、`_MATCAP_ON`、`_FX_UNCLIP_SCREEN_IMAGE_OVERRIDE_2_TONE`、`_FX_UNCLIP_SECONDARY_EMISSION_RIM_GLOW`。用同一 Pass 的反射表恢复 cbuffer 名称并移植像素运算；这不表示所有 Unity 渲染通道已还原。准确分支见[HLSL 生成器](../../../Scripts/gen_nap_avatar_hlsl.py)。

| 原输入/输出 | 移植与已知边界 |
| --- | --- |
| UV0、`LightTex`、两张 OtherData | 法线 RG、B 通道明暗偏移、Material ID 五组色带/高光/边缘光。打包数据图用线性 BC7 保留 B/A，具体 sRGB 和寻址按 TextureSettings。 |
| MatCap 数组 | 拆成五张贴图；“有贴图的组用对应切片”是重建推断，不能当作已取得运行时数组。 |
| Color/Vector | Color 的 LDR 按 sRGB 曲线转线性；HDR 用“gamma 底色 × 强度”，是对照图选择的换算，缺 Unity 存储约定的直接证据；Vector 原样。 |
| 顶点与坐标 | UV1 供描边平滑法线，UV2 供自发光；Unity Y 向上/米与 UE 坐标、UV 翻转和副切线符号显式适配。网格重导必须保留材质连接、顶点色及全部所需 UV。 |
| 主光与阴影 | 实体主光改用组件四个输入；实体环境/色调参数来自显式项目全局配置，阴影采样改为角色级 Visibility。 |
| 屏幕贴图、自发光、运行时覆盖 | 开启的分支必须有真实贴图；删除的 `_OverrideRimGlow`/`_Override2Tone` 等分支必须在源材质中为关闭，未知或未实现特性报错。运动矢量/GBuffer 输出未复刻。 |
| 项目 Emissive | 原主颜色与边缘输出经上述项目合成/曝光适配进入 Emissive；原游戏 UberPost/Bloom 未移植。 |

全局配置中的数值是编辑器起始值，不是从 JSON 得到的原游戏灯光。重新生成 HLSL 后需在受协调的 UE 窗口重建材质，不能只改源码文件就声称资产更新。

## 资产、工具与 FX 接缝

| 项 | 位置或接口 |
| --- | --- |
| 表面/描边资产 | `Content/Characters/Player/Pyrios/Materials/Generated/`：`M_Pyrois_Toon`、`M_Pyrois_Outline`、`MI_Pyrois_Body_1/Body_2/Weapon01`。 |
| 编辑器默认槽 | [bind_pyrios_editor_preview.py](../../../Scripts/bind_pyrios_editor_preview.py) 绑定模型默认 MI；Blueprint 的实际 override 必须单独读回，不能由脚本意图推断。 |
| 验证/生成 | [verify_pyrios_renderer.py](../../../Scripts/verify_pyrios_renderer.py) 默认只读，显式 `--compile` 可能使包变脏；生成器先核源数据、有限值、特性、纹理、槽位、类型和脏包，BuildJournal 区分尝试、保存与失败，不提供全资产事务。 |
| 模型重导 | [reimport_pyrios_mesh_uv.py](../../../Scripts/reimport_pyrios_mesh_uv.py) 沿既有 Interchange 设置；[素材导出 skill](../../../../.kiro/skills/zzz-anime-assets-cli/SKILL.md) 约束 CLI 来源。 |
| 身体 FX 槽 | `MAT_Pyrois_Body_FX01` 使用独立 `MI_Pyrois_Body_FX`；表面槽配置不接管它，描边对应槽透明。身体三层合成、技能 Niagara 和 cue/挂点等边界归[FX 接口与证据](ZZZ_FX_Handoff.md)。 |

Weapon01 的静态 JSON `_Emission=0` 不能解释截图中的全部剑光。剑身基本表面、运行时 FX 和 Bloom 必须分别核来源；Shader 候选存在不代表参考帧实际使用。胸口白芯、斗篷及未知挂载不由猜面罩区域、默认时间或替代特效补齐。

生成美术资产所在目录受项目忽略规则约束；跨 checkout 须经既有资产管线交付，不因本任务放开整个角色目录。失败日志、备份及旧执行副本保留。

## 历史证据入口

以下只用于追溯各自记录的版本和范围，不授当前 UE/构建/Git 窗口，也不替本轮视觉验收：

- [迁移历史](Character_Render_Migration.md)：旧类、BP 配置、首次失败与保存重开过程。
- [2026-09-29 Cold/PIE 记录](Character_Render_Runtime_Verification.md)：当时 MID/描边/主光响应、退出观察及无截图限制；旧参数不作当前值。
- [早期材质差距与 NTE 只读对照](Pyrios_Material_Fidelity_Audit.md)：旧接线问题、来源证据和方案边界。
- [旧项目实现原文](Pyrios_Renderer_Implementation_History_20261013.md)、[旧 Obsidian 原文](Pyrios_Renderer_Obsidian_History_20261013.md)：本次整理前逐字节存档，含旧验证和当时算法说明，不作为活动契约。
- [表面材质 Save](../../../../Saved/Codex/PyriosSurface_20261012_R10/Save.json)、[独立 Cold](../../../../Saved/Codex/PyriosSurface_20261012_R10/Cold.json)与[旧捕获索引](../../../References/Captures/PyriosToon/INDEX.md)：按原报告区分资产保存、编译与实际画面。
