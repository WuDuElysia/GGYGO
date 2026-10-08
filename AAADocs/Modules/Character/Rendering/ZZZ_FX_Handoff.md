# ZZZ / Pyrios 特效还原交接（2026-10-08）

给接手会话用：目标、已完成、管线、数据格式、坑、边界、下一步。设计细节另见 Obsidian `GGYGO架构规划/Character/渲染实现.md`「身体 FX」「技能特效」两节。

## 0. 目标与硬约束

- 用绝区零（Unity 2019.4.40f1，miHoYo 改版）导出的数据在 UE 5.8 重建 Pyrios 的身体 FX 与技能特效。
- 数据驱动：数值来自导出数据。完整预制体任一启用的可见分支不受支持，整批预检失败、资产零写入；不跳过分支后报告完整还原。明确选择的源子树可以独立做 `NS_PREVIEW`，必须保留完整祖先变换，并标明父预制体未完成、动作接入未验。
- 角色/特效材质一律 Unlit，不走 UE 光照第二遍。
- 编辑器开着（带 `-ModelContextProtocolStartServer -ModelContextProtocolPort=8000`）时，所有导入、改资产、存盘走 MCP，在用户的编辑器里做；不要另起 `UnrealEditor-Cmd` 写同一批资产。
- `Content/` 只放 `.uasset/.umap`；源数据留在批准的导出/资料目录。批准清单中的新包才可创建、修改和保存；开始前既有包不可复用、覆盖或删除。失败的新包保留供诊断，不自动清理资产。
- 构建、UE 窗口和 Git 由统筹安排。不得 SaveAll、自动提交或强制添加整个被忽略的资源目录。FX109 七包与 FX110 八包均已保存冻结，两个 UE 窗口已归还，不能按本文命令重新写入。
- 实际图像检查与数值对照共同保留；编译、粒子存活、隔离探针和原效果一致性分别记录。此次证据保存在 `Saved/AutomationReports/`，见 §1。

## 1. 当前状态

| 项 | 状态 |
| --- | --- |
| 身体 FX（`MI_Pyrois_Body_FX`，三层溶解遮罩叠加） | 历史生成、SM6 编译和保存检查通过；原游戏视觉未验收。用户截图的斗篷上沿固定缺口仍未关闭，见 §14 |
| 表面 Toon（NapAvatarStandard 逐行移植） | 另一工作线的历史实现与截图修正，验证范围见 `Pyrios_Renderer_Implementation.md`；本批不修改或重新验收 |
| 历史技能试点 `Eff_Pyrois_Attack_Normal_01_01_Trail` | 旧 `NS_Eff_Pyrois_Attack_Normal_01_01_Trail` 生成了 7/8 发射器，曾编译 UpToDate、0 堆栈问题；属于不完整历史资产，未挂攻击、未做原游戏对照。当前完整预检仍阻塞，不沿用历史“跳过”策略 |
| 普通烟雾子树 `Smoke_Cone01 (2)`（2026-10-08） | 独立 `NS_PREVIEW` 七包已创建、保存；材质与 Niagara 编译通过，原材质实际有很淡的绘制输出。父预制体、普攻/技能/闪避整条链路未完成，原游戏同帧一致性未验 |
| Back03 子树 `root/smoke_flow`（2026-10-08） | 显式 native Shader 候选 `NS_PREVIEW` 八包已创建、保存并编译；原生预览近乎空白，实际烟雾输出未确认。完整 prefab、源运行态选择/全局值与动作接入未验 |
| 试点 `..._weapon` | 只有一个 MeshRenderer 节点，未生成系统 |
| 其余动作来源 | 资源组已交付 30 个根的完整组件/资源证据；不等于执行语义、触发时间和挂点已还原。v2 读取与单子树的显式 native 候选消费已接入，其余源分支和运行态取证仍未完成 |
| 历史提交 | `2cdca88`（源数据移出 Content）、`6e38fe5`（技能特效管线）；本轮未自行 Git |
| AnimeStudio 改动 | 未提交（见 §6） |

历史试点七个发射器：`root/Trail/rot/{HighLight, light_edge, Smoke_trail, Smoke Head, bloom, Shining}`、`Smoke_Cone01 (2)`；当时遗漏了 `Main_Distor`。当前完整源预检对屏幕扭曲以及不支持的变换剪切明确失败，不创建部分生产预制体。

### 普通 PREVIEW 小批的已验证检查点

- 源文件：`F:\AnimeStudio\Exports\ZZZ\Pyrois_SkillFX\Raw\3077361824\fx_json\Eff_Pyrois_Attack_Normal_01_01_Trail.fx.json`，同目录 `.deps.json`；选定节点 `Smoke_Cone01 (2)`，修订标识 `gateFX109`。
- 离线入口 `zzz_fx_preview.py`，执行入口 `zzz_fx_preview_apply.py`。最终只有下列七个包，旧版目标因 mip 设置修正已撤回且零创建：

```text
/Game/Characters/Player/Pyrios/FX/Skill/NS_PREVIEW_Eff_Pyrois_Attack_Normal_01_01_Trail_Smoke_Cone01__2__62a61f7b2dae
/Game/Characters/Shared/FX/ZZZ/MaterialInstances/MI_Eff_Others_LKJ_120_2236c13ef57c
/Game/Characters/Shared/FX/ZZZ/Materials/M_ZZZFX_Particles_Dust_a537e4f8_e3da3896754c
/Game/Characters/Shared/FX/ZZZ/Meshes/Eff_Cone_01_6a19ddf1a61f
/Game/Characters/Shared/FX/ZZZ/Textures/Eff_Noise_030_1cb670f2f7fd
/Game/Characters/Shared/FX/ZZZ/Textures/Eff_Noise_031_8e489bbd7796
/Game/Characters/Shared/FX/ZZZ/Textures/Eff_Smoke_002_3f1413552da9
```

- 三张源贴图的实际 `m_MipCount` 为 9/10/9，旧读取器 `m_MipMap=false` 不能表示没有 mip；本批改为 `TMGS_FromTextureGroup` 并回读一致。这是 UE 重新生成 mip，未声称保留原始逐级 mip 字节。
- 实际材质重编译通过；最终 Niagara `UpToDate`、无 Error/Warning、不在编译、不 stale。原生编辑器 .20 秒捕获一个粒子：Lifetime .219、Age .167、Color `(0,0,0,.06)`，数值为 UI 四舍五入读数。线框和隔离探针只用于诊断。
- 初看正常材质似乎空白，已纠正：恢复原 Custom 公式、逐字符回读一致并保存后，存活帧 .07 秒与消亡帧 .50 秒的图像 ROI `(100,320,390,510)` 有 743 个像素最大 RGB 差超过 8/255，最大差 67。原材质有很淡的实际绘制；无原游戏同帧对照，不能称视觉还原通过。
- Cone 网格边界回读与预期轴约定一致；源 X/Y 对称，因此 AABB 不足以证明反射符号或手性。源顶点色全白，UE 导入器去掉常量白色缓冲，不能据此判断丢失有效颜色。
- 结果：[构建与原生预览报告](../../../../Saved/AutomationReports/GGYGO_FX_OrdinaryPreview_20261008_0128.json)、[原材质存活帧](../../../../Saved/AutomationReports/FX109_OriginalMaterial_Alive_20261008.png)、[原材质消亡帧](../../../../Saved/AutomationReports/FX109_OriginalMaterial_Dead_20261008.png)。报告 `phase=asset_build_passed` 仅表示构建；`native_preview` 单独保留实际渲染、清理和未验收范围。`executed_script_sha256` 是执行前全部 `zzz_fx*.py` 文件快照，不表示每个文件都实际执行过。
- 只做非 PIE 的 Niagara 资产编辑器预览；未放 Actor、未改地图/GA/Montage/ABP/Toon/身体 FX。三个临时着色探针未保存，原公式恢复并保存成功。自身 observer_4/5 已撤销，observer_6 在属性窗口关闭后已不存在；Performance/Particle Counts 关闭、Lit 恢复，预览暂停 .10 秒，无业务回调或 FX 句柄。
- 归还时 PIE=false，地图 `/Game/Map/L_Movement_Test.L_Movement_Test`，`dirty_content=[]`、`dirty_maps=[]`。实际日志 `Saved/Logs/GGYGO_Gate106_R3_WalkRunSteering_Editor_20261007.log` 的 `FX109_RETURN_STATE` 留存。统筹已接回窗口，本批资产停写。

### Back03 native 候选小批的编译检查点（视觉未闭合）

- 源：新版证据根 `Prefabs/Eff_Pyrois_Evade_Back_03_Trail.fx.json` 与同名 `.deps.v2.json`；只选 `root/smoke_flow`，修订 `gateFX110`。仅以下八个新包，先前中间版本清单零创建：

```text
/Game/Characters/Player/Pyrios/FX/Skill/NS_PREVIEW_Eff_Pyrois_Evade_Back_03_Trail_root_smoke_flow_58dc364beabe
/Game/Characters/Shared/FX/ZZZ/MaterialInstances/MI_Eff_Objects_MSH_GUID53029b4738568da4e9cc9c9b20eae7da_743d32191c9c
/Game/Characters/Shared/FX/ZZZ/Materials/M_ZZZFX_Particles_Dissolve_CustomColor_Mask_df1104ec_b421cb1775a6
/Game/Characters/Shared/FX/ZZZ/Meshes/FXMD_TRAIL_9c24650bfe62
/Game/Characters/Shared/FX/ZZZ/Textures/Eff_Mask_036_YZ_02_aa73133347c1
/Game/Characters/Shared/FX/ZZZ/Textures/Eff_Mask_556_a266c0532e3f
/Game/Characters/Shared/FX/ZZZ/Textures/Eff_Noise_114_2a195f585094
/Game/Characters/Shared/FX/ZZZ/Textures/Eff_Smoke_305_26c3a19235ca
```

- 候选配置明确为 `purpose=source_program_preview`、Pass 0 `TransparentFullRes`、global keywords `[]`。材质五个本地关键字与 CAB/PPtr 身份、原生状态、反射/程序签名和真实文件字节一致；这不是原作实际运行态选择或全局常量证明。
- 旧 `Back03_shader_selection.json` 的 18 个程序摘要仍全部不符实际文件字节：旧摘要基于写盘前 LF，Windows 写盘转 CRLF。资源作者另交 `Back03_shader_selection.bytes-v3.json` 与 `Back03_ShaderVariants.bytes-v3.frozen.json`，本批执行前实际校验其覆盖的 20 个冻结文件字节；未改旧程序文件、旧审计或整套资源闭包。
- 八包实际创建、精确保存，注册表/内存/磁盘存在读回一致。材质原生重编译成功；冻结 `plan['code']` 为 28538 字符，既有构建器补入 40 字符的 VCol 输入拼装前导后，最终生成 Code 为 28578 字符。UE Custom Code 与这一最终生成 Code 逐字符及 SHA-256 相同，比较对象不是裸 `plan['code']`。Niagara 初次及恢复临时 Performance 后均 `UpToDate`、0 Error/Warning、非 compiling/stale。FBXImport 的“无平滑组”警告保留，源法线/UV/顶点色的视觉等价未验收。
- 原材质 .25 秒与 1.22 秒两张原生图像近乎空白；ROI `(10,85,250,360)` 超过 8/255 的差异像素为 0，最大差 7，不能证明烟雾绘制。只读组件读回确认新系统在 `Transient.World_5`，模拟边界中心 `(-22,-63,34)` cm、extent `284.8947` cm；没有取得运行时粒子数。未改 Shader 做可见性探针，未用图像差异替代原作同帧对照。
- 结果：[本批构建与预览报告](../../../../Saved/AutomationReports/GGYGO_FX_Back03_NativePreview_20261008_FX110.json)、[候选存活时段](../../../../Saved/AutomationReports/FX110_OriginalMaterial_Alive_20261008.png)、[候选消亡时段](../../../../Saved/AutomationReports/FX110_OriginalMaterial_Dead_20261008.png)。`phase=asset_build_passed_visual_unconfirmed` 明确区分编译与实际视觉。完整 prefab、动作时间轴/挂点与源运行态仍未完成。
- 收尾非 PIE，地图 `/Game/Map/L_Movement_Test`，全局 content/map dirty 均空，日志 `FX110_RETURN` 留存。Performance 已关闭，ParticleCounts 保持原 false、Lit、暂停 .25 秒；本次 observer_7 已注销，只留引擎根 observer_1，没有注册回调。八包及执行脚本停写并归还窗口；旧七包、地图/Actor/GA/Montage/ABP/Toon/bodyFX 保持。

## 2. 路径速查

| 用途 | 路径 |
| --- | --- |
| AnimeStudio CLI | `F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe` |
| 重编 CLI | `dotnet build F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release -v q -nologo` |
| 游戏资源块 | `F:\ZenlessZoneZero Game\ZenlessZoneZero_Data\StreamingAssets\Blocks\*.blk`（约 1 万个） |
| 全局 AssetMap | `F:\AnimeStudio\Exports\ZZZ\AssetMapAll\zzz_assets.json`（40 万条，148MB）+ 首次查询生成的 `zzz_assets.tsv` |
| 技能特效中间数据 | `F:\AnimeStudio\Exports\ZZZ\Pyrois_SkillFX\`：`blocks/`（8 个块硬链接）、`Raw/<块>/<类型>/<PathID>.dat`、`Raw/<块>/fx_index.json`、`Raw/<块>/fx_json/*.fx.json / *.deps.json / ue_assets.json / *.ue_report.json`、`Typed/<块>/<类型>/<名>#<PathID>.*` |
| 新版资源证据 | `F:\AnimeStudio\Exports\ZZZ\Pyrois_SkillFX_Evidence\`：`Prefabs/*.fx.json / *.deps.v2.json / *.resource_closure.v2.json`、精确 CAB 原始组件与资源、`Converted_v2/`、`Review/`；由资源组冻结，不能覆盖旧导出 |
| Shader 变体反汇编 | `F:\AnimeStudio\Exports\Shader\ZZZ_20260925\FXVariants\<Shader>\<关键字md5前8位或none>\Shader\*.shader` |
| UE 共享特效资产 | `/Game/Characters/Shared/FX/ZZZ/{Textures, Meshes, Materials, MaterialInstances}` |
| UE Niagara 系统 | `/Game/Characters/Player/Pyrios/FX/Skill/NS_<预制体名>` |
| 身体 FX | master `/Game/Characters/Shared/FX/Materials/M_FX_DissolveMaskLayers`，MI `/Game/Characters/Player/Pyrios/Materials/Generated/MI_Pyrois_Body_FX` |
| Unity 材质源数据 | `AAADocs/Assets/Pyrios/Rendering/UnityMaterials/`（`MAT_*.json`、`FXObjects/`、`TextureSettings/`） |
| 特效全局常量取值 | `AAADocs/Assets/Shared/FX/ZZZ_FX_Globals.json` |
| 脚本 | `AAADocs/Scripts/zzz_*.py`、`ue_mcp.py`、`build_pyrios_body_fx.py`、`pyrios_fx_plan.py`、`fx_dissolve_mask_layer.hlsl` |

技能特效 8 个资源块：`3817944121 1376282251 3077361824 4121720671 3979351637 993312222 2898863557 3288692478`。试点在 `3077361824`。

## 3. 当前生成管线与执行边界

```
# A. 原始导出（每个资源块一次，CLI 直接跑，不涉及 UE）
set ANIMESTUDIO_EXPORT_ALL=1 ; set ANIMESTUDIO_RAW_PATHID=1
AnimeStudio.CLI <块.blk> Raw/<块> --game ZZZ --export_type Raw --silent
python zzz_fx_index.py Raw/<块>                       # → fx_index.json（预制体根 → 子节点 → 组件）
python zzz_fx_summary.py Raw/<块>/fx_index.json Pyrois # 列出各根的组件统计；加 <根名> --tree 看层级
python zzz_fx_extract.py Raw/<块> "<根名正则>"         # → fx_json/<根>.fx.json
python zzz_fx_describe.py <根>.fx.json                 # 人读摘要：时长/Burst/渲染模式/启用模块

# B. 依赖（CLI，不涉及 UE）
python zzz_fx_fetch.py <根>.fx.json                    # 查 AssetMap，导出材质/网格/动画/贴图；网格 JSON→FBX；→ <根>.deps.json

# C. 默认只做离线预检，不连接 UE、不创建资产
python -B zzz_fx_import_assets.py <根>.deps.json --revision <修订>
python -B zzz_fx_build.py <根>.fx.json --plan-imports --revision <修订>
python -B zzz_fx_preview.py <根>.fx.json "Smoke_Cone01 (2)" --revision <修订>
```

`zzz_fx_build.py` / `zzz_fx_import_assets.py` 只有显式 `--apply --endpoint --approved-targets <精确清单>` 才执行。PREVIEW 执行入口要求 `--endpoint --approved-targets-json --result`，规划目标必须与批准集合完全一致，结果必须是 `Saved/AutomationReports/` 下的新文件。以上不是新 UE 窗口授权；本批当前已冻结。

生成顺序：

```
离线读取源、继承祖先 active、枚举全部启用分支与运行控制来源
每个可见分支完整生成 material plan 与 emitter spec
任何不支持的分支/源缺失 → PreflightError，整批零写入
汇总全部源文件、内容版本目标、依赖与唯一写入范围
统筹分配精确新包清单和非 PIE 窗口
AssetSession：写前确认所有目标不存在；每个创建前再次确认
导入 → 设置并回读 → 材质 → 有序 Niagara 堆栈 → 实际编译
只保存本批创建的包；保留失败结果与已创建资产，不删旧系统
实际原材质预览 → 保留未验边界 → 清理自身资源 → 归还窗口
```

七包归还后完成了独立离线适配：`schemaVersion=2` 自动选择同名 `.deps.v2.json`，缺失即失败、不回落旧 `.deps.json`；读取该源自身 `components/componentListProof`，不访问旧块的 `fx_index.json`。旧 schema 1 管线继续使用旧源。build/preview/preview_apply 可显式传 `--deps-path`；build 的此选项只允许单源，未知 schema 明确拒绝。

`zzz_fx_native_shader.py` 已接入单子树的显式候选选择：`--native-selections-json` 指定审计文件、purpose、pass index 与精确 global 集合，按 CAB/材质身份、本地关键字、native 状态、实际字节 SHA、程序签名及反射一致性验证。缺少选择或遇到未实现的独立 Alpha/MRT/Stencil/DepthOffset 等契约即失败，不假用同名旧变体缓存。完整生产预检拒绝 preview 候选配置；Back03 此次只编译一个源子树，不能把 30 根资源闭包交付写成 30 根生产预检通过。旧普通 PREVIEW 七包的离线计划保持。

## 4. 数据解析：无类型树对象（zzz_schema.py）

- ZZZ 资源包剥离了类型树，AnimeStudio 没实现 ParticleSystem 等类，只能 Raw 导出字节。
- 做法：UnityPy 1.10.18 的 TPK 里取 2019.4.40f1 内置类型树，叠加逐字节核对出的 miHoYo 补丁（`ZZZ_PATCHES`），自己写读取器；**必须恰好读完全部字节**，否则 `LayoutError`。
- 两套布局：`LAYOUTS = {"A", "B"}`，不同游戏版本构建的块不同；B 比 A 多 `LightsModule` ratio 后 1 个字、`ParticleSystemRenderer` 末尾多 7 个字。读取时逐个尝试，取恰好读完的那套。
- 已打补丁、8 块抽样全部读通的类：`ParticleSystem`、`ParticleSystemRenderer`、`MeshRenderer`、`Light`；原生即可读：`GameObject`、`Transform`、`MeshFilter`、`Animation`、`MonoScript`。
- 补丁要点：ParticleSystem 在 `lengthInSec` 前多 4 字、`stopAction` 后多 1 字、`EmissionModule.m_Bursts` 后多 7 字、末尾 17 字；Renderer 基类同 AnimeStudio `Renderer.cs` 的 ZZZ 分支（`m_RayTraceProcedural`、SortingOrder 后 3 个 bool + `m_CullingDistance`）。`zzz_unk*` 字段只确认了类型和位置，语义未知，不参与重建。
- 定位新布局分歧的工具：`zzz_schema_trace.py trace|stat`（逐字段偏移 / 目录成功率）、`zzz_schema_words.py`（从某字段起多样本并排打印字）、`zzz_schema_dist.py`（字段取值分布，看 bool 是否只出现 0/1）。
- MonoBehaviour（`MonoEffect*`、`NapEffectSimulatorComponent` 等，`Logic.dll`）没有类型树，只解析了基类头，脚本字段以 `payload_hex` 原样保留。

## 5. 预制体结构（以试点为例）

```
Eff_Pyrois_Attack_Normal_01_01_Trail   [MonoEffect, PluginFollow/Destroy/Fade, NapEffectSimulator..., Animation]
  root
    Trail                (scale 0.85,0.9,0.85 → 非均匀缩放)
      rot                ← Legacy Animation 旋转曲线（0~0.167s 快速转动）
        Main_Distor / HighLight / light_edge / Smoke_trail / Smoke Head / bloom / Shining   各一个 ParticleSystem（Mesh 渲染）
  RaycastBase (inactive)
  Smoke_Cone01 (2)       世界空间、startDelay 0.05
```

- 每个预制体根节点通常带一个 Legacy `Animation`（`m_Legacy: 1`），驱动子节点旋转/位置；`zzz_unity_anim.py` 解析 YAML 并按 Unity Hermite 求值。
- 大部分子发射器：`lengthInSec` 极短、单个 Burst(t=0, count=1)、`m_RenderMode=4`（Mesh）、`m_RenderAlignment=2`（Local）、`moveWithTransform=0`（Local 模拟）、开 CustomData。
- 旧 fetch 通过 PathID 查全局 AssetMap；新版证据按 sourceBlock/CAB/PPtr 精确闭包。已发现同 PathID 不同 CAB 的源字节差异，不能把 PathID 单独当成全局唯一来源。旧试点依赖 40 个（材质 8、网格 3、动画 1、贴图 24、Shader 4）。

## 6. AnimeStudio 本地改动（仓库 `F:\AnimeStudio\AnimeStudio`，均未提交）

| 文件 | 改动 | 用途 |
| --- | --- | --- |
| `AnimeStudio.CLI/Studio.cs` | `ANIMESTUDIO_EXPORT_ALL=1` 导出所有对象 | 无模型 GameObject、ParticleSystem 等也能 Raw 导出 |
| `AnimeStudio.CLI/Exporter.cs` | `ANIMESTUDIO_RAW_PATHID=1`：Raw 文件名 = `<PathID>.dat`，其它类型 = `<名>#<PathID>.<ext>` | 同名对象不再互相覆盖；按 PPtr 定位 |
| `AnimeStudio/Classes/Texture2D.cs` | JSON 带 `m_ColorSpace` | 贴图 sRGB 照抄 Unity |
| `AnimeStudio/Classes/Material.cs` | 公开 `m_ShaderKeywords`、`m_DisabledShaderPasses`、`m_EnabledPassMask` | 选 Shader 变体与 Pass |
| `AnimeStudio.Utility/ShaderConverter.cs` | ① `ANIMESTUDIO_SHADER_KEYWORDS="KW1 KW2"`（`NONE`=空集）只导出该关键字集合选中的子程序；② 每个子程序后输出 `//@ CBBIND/CB/V/M/TEX/SMP` 反射绑定表；③ 混合/ZTest/ZWrite/Cull 由属性驱动时打印 `[属性名]`；④ 修复反汇编指针 bug（`GetPinnableReference()` 被当首字节数值传成指针 → 0xC0000005），改为 `fixed` 取地址；⑤ 非 DXBC 数据先找魔数 | uber shader 上万变体不必全导；翻译器不用猜 cbuffer 布局 |

## 7. 材质：反汇编直译（zzz_dxbc_hlsl.py + zzz_fx_material.py）

```
plan(材质 JSON, renderer, tex_assets):
  旧源变体/Pass = 只读已导出的 m_ShaderKeywords 对应变体；按 COLOR_PASSES 选择未禁用 Pass
  native 候选 = 仅显式源子树预览配置；严格核对 CAB、原生状态、审计与实际程序字节
                缺源/未选择/契约不支持 → 失败，不启动导出或借用旧缓存
  ps     = translate(Pass.fp, 需要 o0)
  vs     = translate(Pass.vp, 只要 PS 实际读到的插值)     # SV_POSITION 不翻，像素位置用 UE 的
  av#    = 按渲染器 m_VertexStreams 打包成 VS 输入（Unity 规则：固定语义 + 其余挤进 TEXCOORD 分量）
  混合   = Pass 的 Blend [_SrcFactor] [_DstFactor] 取材质值，映射 BLEND_MAP
  参数   = 保留代码读到的 UnityPerMaterial 属性；Color 走 Unity 线性化；缺失属性取 Properties 默认值
  贴图   = 保留代码采样到的贴图 → ue_assets；空贴图 → 报错
```

翻译器规则：

- 寄存器一律 `uint4` 存位模式，指令按类型 `asfloat/asint/asuint`：DXBC 无类型，比较结果是 `0xFFFFFFFF`，用 float 存会变 NaN。
- `cbN[i].c` 由 `//@` 反射表还原：`UnityPerMaterial` → 同名材质参数；其它（`$Globals`、`UnityPerDraw`）→ provider 表（`ZZZ_FX_Globals.json`），**死代码消除后仍引用且没有 provider 的全局量 → 报错**。
- 采样走前导里的 `F.S/F.SL/F.SB`，负责 Unity→UE 的 V 翻转；`_CameraDepthTexture` 换成 `CalcSceneDepth`，编码成 `1/眼深(米)` 与 `_ZBufferParams=(0,0,1,0)` 配套。
- 旧 provider 表存在场景雾、亮度压缩、饱和度等固定中性取值；它们不是源游戏运行态证明，不能据此称完整等价。带 `disabled_by` 的只在对应开关关闭时成立，否则报错。原游戏 runtime global keyword、相机/后处理常量仍须取证。矩阵、相机方向和世界坐标按 Unity→UE 的同一换算处理。
- 颜色输出与原始 distortion field 是不同契约：普通颜色计划拒绝 MRT；离线 field 计划选择原 Pass 的实际目标寄存器并保留数据，UE 材质生成器在创建前拒绝未实现的 field。`_SoftParticles=1` 不证明实际开启 `_SOFTPARTICLES_ON` 变体。

顶点流映射（Niagara 网格粒子）：

| Unity 流 | Custom 输入 |
| --- | --- |
| Position / Normal | `WorldPos` / `VertexNormalWS`（转 Unity 约定，米） |
| Color | `ParticleColor × VertexColor`（网格粒子） |
| UV..UV4 | `TexCoord[k]`，`v = 1 - v`；网格缺的 UV 层送 0 |
| Center | `ParticlePositionWS` |
| Custom1 / Custom2 | DynamicParameter 0 / 1 |
| StableRandom* | DynamicParameter 2 |
| Size* / InvStartLifetime | DynamicParameter 3 |
| 未提供的流 | 0（与 Unity 未绑定输入一致），记 warning |

UE 侧（zzz_fx_material_ue.py，全走 MCP MaterialTools/ObjectTools）：

- master：Unlit、`BlendMode` 按方案、`TwoSided` 按 `_Cull==0`，**只开 `bUsedWithNiagaraMeshParticles`，关 `bAutomaticallySetUsageInEditor`**。
- 一个 Custom 节点（`CMOT_Float4`），输入 = 内置节点 + Scalar/Vector/TextureObject 参数；Custom → Emissive，A 通道经 ComponentMask → Opacity。
- master/MI 名带内容版本哈希；只允许复用本批刚创建的同方案 master，不读取、修改或复用开始前既有资产。本批实测 ParticleColor/DynamicParameter 使用完整 RGBA，VertexColor 的 RGB/A 分别接入。

## 8. 发射器：Unity 公式写成 Set Parameters（zzz_fx_niagara.py + _ue.py）

```
发射器更新  Emitter State(Self, Once/Infinite, Loop Duration=lengthInSec, Loop Delay=startDelay)
            Spawn Burst_Instantaneous × 每个 burst（展开 cycleCount） / Spawn Rate
粒子生成    Particles.URand*（按需分配的每粒子随机数）、Lifetime、UStartColor、UStartSize、URot、
            UStable（StableRandom）、USpeed；世界空间时还有 UWorldOrigin / UWorldDir
粒子更新    Particle State
            URot += 角速度·dt；USize = 起始尺寸 × SizeModule；Color = 起始色 × ColorModule（ApplyActiveColorSpace → sRGB 转线性）
            节点链 UChain*P/Q：预制体根→节点的 TRS，带动画的节点按 System.Age 求曲线
            Position = 链(本地 +Z·speed·age)；MeshOrientation = 链旋转 ⊗ Euler_ZXY(URot)；Scale = USize × lossyScale
            DynamicMaterialParameter0..3 = CustomData1 / CustomData2 / UStable / (Size, 1/Lifetime)
渲染器      Mesh 渲染器，OverrideMaterials = MI，SortOrderHint = m_SortingOrder
```

- 坐标：Unity (x,y,z) 米 → UE (-x, z, y)×100；四元数 (x,y,z,w) → (-x,z,y,w)；缩放 (sx,sy,sz) → (sx,sz,sy)。旧四元数公式已修正并通过向量旋转换算回归；原游戏画面对照仍未验。
- MinMaxCurve 模式 0 常量 / 1 曲线 / 2 双曲线随机 / 3 双常量随机；Gradient 线性或阶跃，时间 `ctime/atime ÷ 65535`。
- 曲线：普通段 Hermite；加权段保留三次贝塞尔，用 24 次二分反求时间参数后求值，已移除 16 段折线近似，非法权重明确失败。
- 父级非均匀缩放与子旋转按源变换契约检查；已删除 `lossyScale` 对角近似。无法由当前 Niagara TRS 表达的层级剪切、运动剪切等明确阻塞，不能把缺失分支掩盖成正常还原。
- 中间结果写成粒子属性（UChain0P、UChain1Q…）而不是嵌套表达式，否则四元数乘法会把表达式长度成倍放大。

## 9. 资产导入（zzz_mesh_fbx.py + zzz_fx_import_assets.py）

- 网格：AnimeStudio 的 OBJ 只有 UV0、无顶点色，特效 shader 会读顶点色和 UV1+，所以用 Mesh JSON 自写 FBX 7.4 ASCII。
  - 位置/法线 X 取反、三角形顶点顺序反向；顶点写成**厘米**（×100），`UnitScaleFactor=1`：MCP 的 FBX 导入不做单位换算。
  - UV 原样写（FBX 与 Unity 都是左下原点），UE 导入自己翻 V，材质里再翻回。
  - 校验：导入后 `StaticMeshTools.get_bounds` 与 Unity AABB×100 一致（FXMD_DAO_001 = ±150cm）。
- 贴图：`TextureTools.import_file` 导 PNG，再 `ObjectTools.set_properties` 设并回读：
  - `SRGB ← m_ColorSpace`，源提供独立 `m_WrapU/V` 时分别设置 `AddressX/Y`；只出现一个轴明确失败。两轴均不存在才使用源共用 `m_WrapMode`，MirrorOnce 报错。FX109 消费旧源共用模式；FX110 四张源活跃贴图已实际按独立轴导入并回读，Mask556 Clamp、其余 Wrap，均 sRGB/TC_Default/Bilinear、UE 生成 mip。
  - `m_MipCount` 必须为 ≥1 的整数；等于 1 用 `TMGS_NoMipmaps`，大于 1 用 `TMGS_FromTextureGroup`。旧 `m_MipMap` 读取值不参与判定；源原始 mip 字节未进入 UE。
  - `CompressionSettings = TC_Default`：UE 会把扭曲图猜成法线贴图（BC5，解码到 -1..1），与 Unity 不符。
- 名称结合类型、PathID、源字节哈希、设置和修订生成版本名。同 PathID 不同跨文件来源/设置明确失败；写前核对所有源哈希。只保存本批创建的资产，不 SaveAll。

## 10. MCP 使用要点（ue_mcp.py）

- IDE 侧 MCP 会话在编辑器重启后失效（`Unknown session id`），且无法从会话内重连；`ue_mcp.py` 直接以 Streamable HTTP 连 `http://127.0.0.1:8000/mcp`，自己 initialize。
  - `Mcp().tool("<toolset>.<tool>", **args)`、`Mcp().describe(toolset)`、`Mcp().script(py)`（ProgrammaticToolset）
- PIE 期间 `EditorAssetSubsystem` 的存在/保存检查不可靠。旧 MCP 客户端会等待；本批 `AssetSession` 在创建/保存前明确拒绝 PIE，不停止别人的 PIE、不把等待当成功。
- 长时间材质编译可能断连；保留真实结果与日志。后台进程不能超出窗口继续写入，归还前须确认没有在途请求。
- 有用工具：`MaterialTools.{create_material, add_expression, connect_expressions, connect_to_output, recompile}`（recompile 失败会抛出 HLSL 报错原文）、`MaterialInstanceTools.set_*_parameter`（LinearColor 键是小写 r/g/b/a，可为负）、`NiagaraToolset_System.*`、`EditorAppToolset.{OpenEditorForAsset, CaptureEditorImage, IsPIERunning}`。
- `CaptureAssetImage` 不支持 Niagara 系统；`CaptureEditorImage` 返回 JSON 里的 base64，需自己解码存盘。

## 11. Niagara MCP 的行为（实测）

- `CreateNiagaraSystem` 必须给模板；用 `/Niagara/DefaultAssets/DefaultSystem`，再 `RemoveEmitter(emitterToRemove=...)` 删掉自带的 Fountain。
- `AddEmitter` 用 `/Niagara/DefaultAssets/Templates/CascadeConversion/CompletelyEmpty`（无模块、无渲染器）。
- 参数名必须与 schema 完全一致：`RemoveEmitter(emitterToRemove)`、`GetEmitterTopology(emitterRef)`、`RemoveModule(moduleToRemove)`、`GetModuleInputValues(moduleRef)`、`SetStackInputData(stackInputRef, inputData)`。
- `SetStackInputData` 用 `NiagaraExt_StackInputData_HlslExpression` 写表达式（可引用 `Particles.* / Emitter.* / System.Age / Engine.DeltaTime / Engine.Owner.*`、`rand(x)`）。有依赖的每条赋值创建独立且有序的 `AddSetParametersModule`，不能假定同一个模块内多个条目顺序可读。
- 枚举输入用 `NiagaraExt_StackInputData_Enum`，`enumName` 是 `NewEnumeratorN` 这种内部名，用 `NiagaraToolset_Info.UEnum_Info` 查。Emitter State：Life Cycle Mode `NewEnumerator1`=Self；Loop Behavior `NewEnumerator0`=Infinite / `1`=Once。
- **编译状态陷阱**：只改堆栈时可能返回未实际编译的 UpToDate。先 `OpenEditorForAsset` 触发编译，有限等待并核对整体状态与 `scripts[].compileEvents`；Unknown、失败、超时均不保存成成功。编译完成仍不代替实际原材质预览。
- 删模块后旧 SetVariables 可能残留在堆栈里，探针改完要 `GetEmitterTopology` 核对。
- `CascadeToNiagaraConverter` 的 `FXConverterUtilitiesLibrary.Finalize` 在无头进程里因 Slate 断言崩溃，已弃用；该插件已从 `.uproject` 移除。

## 12. 踩过的坑与已做的处理

| 现象 | 原因 | 处理 |
| --- | --- | --- |
| 打开编辑器弹窗要求导入，导入失败 | JSON 放进了 `Content/` | 移到 `AAADocs/Assets/Pyrios/Rendering/UnityMaterials/`，规则写进 steering |
| AnimeStudio 导出 Shader 进程 0xC0000005 | 反汇编传了错误指针 | `fixed` 取真实地址 |
| 网格导入后小 100 倍 | FBX `UnitScaleFactor=100` 没被 MCP 导入换算 | 顶点写厘米、因子 1 |
| VectorParameter 读 `.w` 报越界 | 默认引脚只有 RGB | 连 `RGBA` 引脚（Scalar 仍用默认引脚） |
| DXIL "read uninitialized value" | `uint4 a, b = 0` 只初始化最后一个 | 每个寄存器单独 `= (uint4)0` |
| 编译材质时编辑器 D3D12 显存分配失败崩溃 | 开了 Sprite 等多种用途，排列翻倍 | 只开 `bUsedWithNiagaraMeshParticles` |
| 保存时报 Asset does not exist | PIE 中资产接口不可用 | 本批明确拒绝 PIE，交统筹排窗 |
| 扭曲贴图被当成法线图 | UE 导入按内容猜测 | 压缩固定 `TC_Default` |
| 解析树 15 层后表达式爆长 | 四元数乘法嵌套展开 | 中间结果写成粒子属性 `UChain*` |
| `_DisableCameraDistanceClip` 等材质里没有 | shader 后加的属性 | 取 Properties 默认值 |

## 13. 已知边界（完整预制体预检阻塞或独立未验收项）

- **屏幕扭曲**：已完成原 field 与 `DistortionBlit` 消费者的离线指令/输出契约取证；消费者按 `q=.1*D.xy`、`p=q*D.z` 对 RGB 分别偏移采样。完整 RGB 合成与简化 UE 原生折射有可见差异，仍待用户选择；无渲染插件实现租约，当前不写渲染 C++、不把 field 当颜色。
- **非粒子网格节点**（MeshRenderer + Legacy Animation，如 `Eff_Others_XL_171` 武器特效、ExQTE 的 BG/Mod 节点）：未实现，需要做成 Niagara 单粒子或 StaticMesh+时间轴。
- **粒子模块**：Shape、Velocity、Force、Noise、Collision、Sub、Trail、Lights、InheritVelocity、ClampVelocity、SizeBySpeed 等任一启用即报错；`gravityModifier≠0`、`randomizeRotationDirection≠0`、`prewarm`、`rateOverDistance`、Burst 无限循环/概率<1 报错。
- **渲染模式**：只做了 Mesh（mode 4）+ 对齐 Local/World；Billboard、Stretch、Horizontal/Vertical 报错；多材质网格粒子报错。
- **TrailRenderer / XWeaponTrailCustom**（武器刀光拖尾，`XWeaponTrail.dll`）：未解析。
- **MonoEffect 系列脚本**（Follow / Fade / Destroy / SelfAttachPoint / Dither / ScreenEffect / HitWallScratch）：无类型树，只有 `payload_hex`；跟随骨骼、淡出、销毁时机都在这里，未还原。
- **触发时机与挂点**：当前目标已包含普攻 1/2/3 和闪避表现；源技能时间轴、socket/跟随/销毁执行语义仍缺真实证据。不能猜 Notify 时间、拿 HitWindow 代替、手定挂点或新建攻击/移动能力。接入由 FX、Animation、Combat/GA 各自承担所属职责，取消/结束/切步/切角色/PIE 退出清理须整链验收。
- **全局后处理**：游戏的特效亮度压缩、Bloom、去色未移植，HDR 交给 UE Bloom/Tonemapper。
- **世界空间发射器的出生朝向**：按出生时组件变换计算，未经实测对照。
- 胸口白色光核疑为 `MAT_Pyrois_Body_FX03` + `Eff_Flare_005` 的独立 flare 特效，宿主对象未找到。

## 14. 身体 FX（历史生成检查通过，斗篷缺口仍开放）

```
骨骼网格槽 MAT_Pyrois_Body_FX01 → MI_Pyrois_Body_FX → M_FX_DissolveMaskLayers
  三层 [FX04, FX01, FX02] 预乘 over 合成（Unity 多材质画同一 submesh 的顺序）
  层逻辑 fx_dissolve_mask_layer.hlsl = Particles_Dissolve_CustomColor_Mask_Cap 在 _UsingNonPSR=1 下的 PS
历史生成入口: build_pyrios_body_fx.py；换算 pyrios_fx_plan.py
```

- 这条线是手写移植（早于反汇编直译管线），只实现三层材质启用的分支，其余报错。
- 如果要统一，可改用 §7 的直译管线重做，但需要先解决"一个槽三遍绘制"在 UE 里的合成。
- 用户指出站立时斗篷上沿、背部护甲下方固定缺一块。已有只读核对未发现四片源 FX 对象、材质绑定或 Section/LOD 的明确漏项；不能由此证明接缝/蒙皮正确。渲染组复核的 `FXObjects/Pyrois_Body_FX_01..04.json` 是组件引用证明，不包含逐顶点 bone weight/bindpose。
- 三层源材质均启用 SoftParticles，Near=0、RcpDistance=20。`fx_dissolve_mask_layer.hlsl:139` 的 `saturate(20*((SceneZ-PixelZ)*.01))` 在 UE 厘米深度约 5cm 内淡出，再经 PowerAlpha/AlphaFade；护甲与布料接缝被深度淡出吃掉是候选原因，不是已证根因。源/UE 屏幕 UV 与眼深等价、上沿逐顶点蒙皮和严格复现仍未验。
- 2026-10-04 记录仅确认材质编译、冷读回与槽位保存，未验收缺口。斗篷诊断当前冻结，本批烟雾 PREVIEW 没有修改身体 FX/Toon/骨骼网格；后续 UE 核对需统筹另排窗口。

## 15. 后续工作与交接

1. 查明 FX110 原材质近乎空白的实际原因并验证烟雾输出；现有八包停写，后继 UE 操作需重新排窗。继续取证源运行态选择与全局值，不猜关键字或更改原 Shader 伪造可见结果。
2. 继续普通源分支支持与完整预检。下一资产批次先交精确清单与未验边界，FX109/FX110 都不覆盖重建；地图/Actor/PIE 接入不能沿用纯资产预览窗口。
3. 原游戏同帧视觉对照仍缺，实际烟雾输出很淡不能单独判断亮度、朝向、尺寸、时序等价。
4. RGB 扭曲实现等待真实用户选择；未知 Mono 脚本、动作时间轴/挂点和世界空间出生朝向继续取证，各模块负责自己的权威状态与清理。
5. 本批文档完成后冻结交回统筹；Git 仅提供可运行脚本及必要依赖的精确交付方案，不自行提交、强制添加资产或提交 AnimeStudio 既有工作。

## 16. 规范提醒（来自项目规则）

- 汇报与文档用中文，解释带伪代码；代码注释中文、只描述现状。
- 按完整需求开发与约定测试完成后集中同步架构笔记；本次按统筹明确范围只更新此文件，不重画 Obsidian、不重复过程 JSON。
- 无子代理；长期模块会话直接承担分析、实现、自审和交接。源码、资产、UE/Git 窗口均遵守单一写入者和统筹排程。
- 本轮脚本位于 `AAADocs/Scripts`，未改 C++。FX109 执行前专项 16/16，后续 v2 离线适配 22/22；FX110 冻结前新增 native 候选专项后实际 30/30 通过（启用 ResourceWarning 错误门禁），没有在执行窗口修改脚本或重跑全模块矩阵。覆盖整批/保存/编译失败、竞态保护、继承 inactive、跨源身份、真实 mip/独立轴、加权曲线/四元数、v2 不回落、native 字节/关键字/身份/状态拒绝契约；这些离线专项不代替 §1 的实际 UE/视觉边界或完整动作恢复验收。
