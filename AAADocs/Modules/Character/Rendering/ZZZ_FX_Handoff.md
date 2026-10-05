# ZZZ / Pyrios 特效还原交接（2026-10-05）

给接手会话用：目标、已完成、管线、数据格式、坑、边界、下一步。设计细节另见 Obsidian `GGYGO架构规划/Character/渲染实现.md`「身体 FX」「技能特效」两节。

## 0. 目标与硬约束

- 用绝区零（Unity 2019.4.40f1，miHoYo 改版）导出的数据在 UE 5.8 重建 Pyrios 的身体 FX 与技能特效。
- 数据驱动：数值来自导出数据；未实现的功能**报错跳过**，不做近似替代、不悄悄兜底（AGENTS.md「禁止隐式业务兜底」）。
- 角色/特效材质一律 Unlit，不走 UE 光照第二遍。
- 编辑器开着（带 `-ModelContextProtocolStartServer -ModelContextProtocolPort=8000`）时，所有导入、改资产、存盘走 MCP，在用户的编辑器里做；不要另起 `UnrealEditor-Cmd` 写同一批资产。
- `Content/` 只放 `.uasset/.umap`；JSON 等源数据放 `AAADocs/Assets/...`（否则编辑器自动导入弹窗且失败）。临时资产当场删。
- 图片存 `AAADocs/References/Captures/<主题>/` + `INDEX.md`，不读进会话；能用 `png_stats.py` 数值判断就别看图。
- 每完成一个需求单独提交，中文提交信息；`Content/` 在 git 中被忽略（`.gitignore:63 /Content/*`），UE 资产不进提交，汇报里说明。

## 1. 当前状态

| 项 | 状态 |
| --- | --- |
| 身体 FX（`MI_Pyrois_Body_FX`，三层溶解遮罩叠加） | 已完成，SM6 编译，已提交；未与游戏画面对照 |
| 表面 Toon（NapAvatarStandard 逐行移植） | 已完成，已对照截图修正（另一条线，见渲染实现.md） |
| 技能特效试点 `Eff_Pyrois_Attack_Normal_01_01_Trail`（普攻 1 段刀光） | `NS_Eff_Pyrois_Attack_Normal_01_01_Trail` 生成，7/8 发射器，Niagara 编译 UpToDate、0 堆栈问题；**未挂攻击、未在视口/PIE 与游戏对照** |
| 试点 `..._weapon` | 只有一个 MeshRenderer 节点，未生成系统 |
| 其余 7 个技能 | 只完成原始数据导出与层级索引，未生成 |
| 提交 | `2cdca88`（源数据移出 Content）、`6e38fe5`（技能特效管线） |
| AnimeStudio 改动 | 未提交（见 §6） |

试点 7 个发射器：`root/Trail/rot/{HighLight, light_edge, Smoke_trail, Smoke Head, bloom, Shining}`、`Smoke_Cone01 (2)`。跳过：`root/Trail/rot/Main_Distor`（屏幕扭曲，见 §8）。

## 2. 路径速查

| 用途 | 路径 |
| --- | --- |
| AnimeStudio CLI | `F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe` |
| 重编 CLI | `dotnet build F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\AnimeStudio.CLI.csproj -c Release -v q -nologo` |
| 游戏资源块 | `F:\ZenlessZoneZero Game\ZenlessZoneZero_Data\StreamingAssets\Blocks\*.blk`（约 1 万个） |
| 全局 AssetMap | `F:\AnimeStudio\Exports\ZZZ\AssetMapAll\zzz_assets.json`（40 万条，148MB）+ 首次查询生成的 `zzz_assets.tsv` |
| 技能特效中间数据 | `F:\AnimeStudio\Exports\ZZZ\Pyrois_SkillFX\`：`blocks/`（8 个块硬链接）、`Raw/<块>/<类型>/<PathID>.dat`、`Raw/<块>/fx_index.json`、`Raw/<块>/fx_json/*.fx.json / *.deps.json / ue_assets.json / *.ue_report.json`、`Typed/<块>/<类型>/<名>#<PathID>.*` |
| Shader 变体反汇编 | `F:\AnimeStudio\Exports\Shader\ZZZ_20260925\FXVariants\<Shader>\<关键字md5前8位或none>\Shader\*.shader` |
| UE 共享特效资产 | `/Game/Characters/Shared/FX/ZZZ/{Textures, Meshes, Materials, MaterialInstances}` |
| UE Niagara 系统 | `/Game/Characters/Player/Pyrios/FX/Skill/NS_<预制体名>` |
| 身体 FX | master `/Game/Characters/Shared/FX/Materials/M_FX_DissolveMaskLayers`，MI `/Game/Characters/Player/Pyrios/Materials/Generated/MI_Pyrois_Body_FX` |
| Unity 材质源数据 | `AAADocs/Assets/Pyrios/Rendering/UnityMaterials/`（`MAT_*.json`、`FXObjects/`、`TextureSettings/`） |
| 特效全局常量取值 | `AAADocs/Assets/Shared/FX/ZZZ_FX_Globals.json` |
| 脚本 | `AAADocs/Scripts/zzz_*.py`、`ue_mcp.py`、`build_pyrios_body_fx.py`、`pyrios_fx_plan.py`、`fx_dissolve_mask_layer.hlsl` |

技能特效 8 个资源块：`3817944121 1376282251 3077361824 4121720671 3979351637 993312222 2898863557 3288692478`。试点在 `3077361824`。

## 3. 端到端管线（新技能照此跑）

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

# C. 进 UE（必须编辑器开着，走 MCP）
python zzz_fx_import_assets.py <根>.deps.json          # 贴图+网格导入并按 Unity 设置配置；→ ue_assets.json
python zzz_fx_build.py <根>.fx.json                    # 材质 master/MI + Niagara 系统；→ <根>.ue_report.json
```

zzz_fx_build 内部：

```
for 预制体里每个 active、renderer enabled、有材质的 ParticleSystem 节点:
    plan = zzz_fx_material.plan(Unity 材质, 渲染器顶点流, 网格 UV 层数, ue_assets)
    master = Builder.build_master(plan)       # 名字 M_ZZZFX_<Shader>_<代码哈希>，已存在则复用
    mi     = Builder.build_instance(plan)     # MI_<Unity材质名>
    spec   = zzz_fx_niagara.emitter_spec(节点, 根→节点路径, Legacy 动画片段, ...)
    任何 PlanError / SpecError / TranslateError → skipped[原因]，继续下一个
MeshRenderer 节点 → 直接记入 skipped（未实现）
NiagaraBuilder.build_system(路径, specs)        # 已存在先删后建；打开编辑器触发完整编译，有错就抛
```

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
- 外部依赖 `m_FileID≠0` 时用 PathID 查全局 AssetMap（`zzz_assetmap.lookup(pid, 类型)`）；ZZZ 的 PathID 是哈希，跨块基本唯一。试点依赖 40 个（材质 8、网格 3、动画 1、贴图 24、Shader 4）。

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
  变体   = zzz_shader_variants.export_variant(材质)   # 按 m_ShaderKeywords 导出唯一变体
  Pass   = COLOR_PASSES 优先级里第一个未被 m_DisabledShaderPasses 关掉的
           (TransparentFullRes > Forward > TransparentHalfRes > ForwardHalfRes > ...)
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
- 全局量取"无效果"值并写理由（场景雾、沙尘、全局亮度压缩、饱和度、区域淡出、UI alpha…）；带 `disabled_by` 的只在材质关掉对应开关时成立，否则报错。`unity_ObjectToWorld` 取单位阵（粒子顶点本就是世界坐标），`unity_MatrixV` 用相机基向量构造。

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
- master 名带代码哈希：代码或参数集变了就是新 master，同方案复用。

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

- 坐标：Unity (x,y,z) 米 → UE (-x, z, y)×100；四元数 (x,y,z,w) → (x,-z,-y,w)；缩放 (sx,sy,sz) → (sx,sz,sy)。与网格 FBX 导入同一约定，先在 Unity 空间算完最后一步再转换。
- MinMaxCurve 模式 0 常量 / 1 曲线 / 2 双曲线随机 / 3 双常量随机；Gradient 线性或阶跃，时间 `ctime/atime ÷ 65535`。
- 曲线：普通段 Hermite（展开成三次多项式）；加权切线段按 Unity 二维贝塞尔每段采样 16 份成折线。
- 父级非均匀缩放 + 子旋转：可交换（单轴旋转且另两轴缩放相等）照常；否则按 `lossyScale` 取对角近似，只允许出现在链末端，之后还有子节点或动画 → 报错。
- 中间结果写成粒子属性（UChain0P、UChain1Q…）而不是嵌套表达式，否则四元数乘法会把表达式长度成倍放大。

## 9. 资产导入（zzz_mesh_fbx.py + zzz_fx_import_assets.py）

- 网格：AnimeStudio 的 OBJ 只有 UV0、无顶点色，特效 shader 会读顶点色和 UV1+，所以用 Mesh JSON 自写 FBX 7.4 ASCII。
  - 位置/法线 X 取反、三角形顶点顺序反向；顶点写成**厘米**（×100），`UnitScaleFactor=1`：MCP 的 FBX 导入不做单位换算。
  - UV 原样写（FBX 与 Unity 都是左下原点），UE 导入自己翻 V，材质里再翻回。
  - 校验：导入后 `StaticMeshTools.get_bounds` 与 Unity AABB×100 一致（FXMD_DAO_001 = ±150cm）。
- 贴图：`TextureTools.import_file` 导 PNG，再 `ObjectTools.set_properties` 设并回读：
  - `SRGB ← m_ColorSpace`，`AddressX/Y ← m_WrapMode`（MirrorOnce 报错），`Filter ← m_FilterMode`，`m_MipMap=false → NoMipmaps`
  - `CompressionSettings = TC_Default`：UE 会把扭曲图猜成法线贴图（BC5，解码到 -1..1），与 Unity 不符。
- 同名不同 PathID → 报错，防覆盖。只保存本脚本动过的资产（编辑器可能有别的会话的未存改动）。

## 10. MCP 使用要点（ue_mcp.py）

- IDE 侧 MCP 会话在编辑器重启后失效（`Unknown session id`），且无法从会话内重连；`ue_mcp.py` 直接以 Streamable HTTP 连 `http://127.0.0.1:8000/mcp`，自己 initialize。
  - `Mcp().tool("<toolset>.<tool>", **args)`、`Mcp().describe(toolset)`、`Mcp().script(py)`（ProgrammaticToolset）
- PIE 期间 `EditorAssetSubsystem` 拒绝读写（`exists` 恒 False、保存报 "Asset does not exist"）。`tool()` 每次调用前检查 `IsPIERunning`，PIE 时等待；不要去停别人的 PIE。
- 长时间调用（材质编译）可能因编辑器崩溃断连（`ConnectionResetError`）；脚本后台跑（`control_pwsh_process`），日志写文件再查。
- 有用工具：`MaterialTools.{create_material, add_expression, connect_expressions, connect_to_output, recompile}`（recompile 失败会抛出 HLSL 报错原文）、`MaterialInstanceTools.set_*_parameter`（LinearColor 键是小写 r/g/b/a，可为负）、`NiagaraToolset_System.*`、`EditorAppToolset.{OpenEditorForAsset, CaptureEditorImage, IsPIERunning}`。
- `CaptureAssetImage` 不支持 Niagara 系统；`CaptureEditorImage` 返回 JSON 里的 base64，需自己解码存盘。

## 11. Niagara MCP 的行为（实测）

- `CreateNiagaraSystem` 必须给模板；用 `/Niagara/DefaultAssets/DefaultSystem`，再 `RemoveEmitter(emitterToRemove=...)` 删掉自带的 Fountain。
- `AddEmitter` 用 `/Niagara/DefaultAssets/Templates/CascadeConversion/CompletelyEmpty`（无模块、无渲染器）。
- 参数名必须与 schema 完全一致：`RemoveEmitter(emitterToRemove)`、`GetEmitterTopology(emitterRef)`、`RemoveModule(moduleToRemove)`、`GetModuleInputValues(moduleRef)`、`SetStackInputData(stackInputRef, inputData)`。
- `AddSetParametersModule` 可一次建多个条目；之后 `SetStackInputData` 用 `NiagaraExt_StackInputData_HlslExpression` 写表达式（可引用 `Particles.* / Emitter.* / System.Age / Engine.DeltaTime / Engine.Owner.*`、`rand(x)`）。条目按顺序求值，后面的能读前面的。
- 枚举输入用 `NiagaraExt_StackInputData_Enum`，`enumName` 是 `NewEnumeratorN` 这种内部名，用 `NiagaraToolset_Info.UEnum_Info` 查。Emitter State：Life Cycle Mode `NewEnumerator1`=Self；Loop Behavior `NewEnumerator0`=Infinite / `1`=Once。
- **编译状态陷阱**：只改堆栈时 `GetSystemCompileState` 一直报 UpToDate、0 错误，实际没编译。要先 `OpenEditorForAsset(assetPath=...)` 触发完整编译，再轮询 `bIsCompiling`，读 `scripts[].compileEvents` 的 Error（含 HLSL 报错原文）。
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
| 保存时报 Asset does not exist | 别的会话在跑 PIE | `ue_mcp` 自动等待 PIE |
| 扭曲贴图被当成法线图 | UE 导入按内容猜测 | 压缩固定 `TC_Default` |
| 解析树 15 层后表达式爆长 | 四元数乘法嵌套展开 | 中间结果写成粒子属性 `UChain*` |
| `_DisableCameraDistanceClip` 等材质里没有 | shader 后加的属性 | 取 Properties 默认值 |

## 13. 已知边界（未实现 → 报错跳过）

- **屏幕扭曲**：`Distortion UVMove`（`Main_Distor`）的 `TransparentHalfRes`/`Distortion` Pass 读 `_ProjectionParams.x`、`unity_MatrixV`、`glstate_matrix_projection` 并需要抓屏；`DistortionOpaque` 被材质关闭。需要 UE 的折射/SceneColor 方案，未做。
- **非粒子网格节点**（MeshRenderer + Legacy Animation，如 `Eff_Others_XL_171` 武器特效、ExQTE 的 BG/Mod 节点）：未实现，需要做成 Niagara 单粒子或 StaticMesh+时间轴。
- **粒子模块**：Shape、Velocity、Force、Noise、Collision、Sub、Trail、Lights、InheritVelocity、ClampVelocity、SizeBySpeed 等任一启用即报错；`gravityModifier≠0`、`randomizeRotationDirection≠0`、`prewarm`、`rateOverDistance`、Burst 无限循环/概率<1 报错。
- **渲染模式**：只做了 Mesh（mode 4）+ 对齐 Local/World；Billboard、Stretch、Horizontal/Vertical 报错；多材质网格粒子报错。
- **TrailRenderer / XWeaponTrailCustom**（武器刀光拖尾，`XWeaponTrail.dll`）：未解析。
- **MonoEffect 系列脚本**（Follow / Fade / Destroy / SelfAttachPoint / Dither / ScreenEffect / HitWallScratch）：无类型树，只有 `payload_hex`；跟随骨骼、淡出、销毁时机都在这里，未还原。
- **触发时机与挂点**：由游戏技能时间轴配置决定（未解析）；挂到攻击上要按动画对照手定（用户已明确“挂到哪个攻击后续再考虑”）。
- **全局后处理**：游戏的特效亮度压缩、Bloom、去色未移植，HDR 交给 UE Bloom/Tonemapper。
- **世界空间发射器的出生朝向**：按出生时组件变换计算，未经实测对照。
- 胸口白色光核疑为 `MAT_Pyrois_Body_FX03` + `Eff_Flare_005` 的独立 flare 特效，宿主对象未找到。

## 14. 身体 FX（已完成，独立于技能特效管线）

```
骨骼网格槽 MAT_Pyrois_Body_FX01 → MI_Pyrois_Body_FX → M_FX_DissolveMaskLayers
  三层 [FX04, FX01, FX02] 预乘 over 合成（Unity 多材质画同一 submesh 的顺序）
  层逻辑 fx_dissolve_mask_layer.hlsl = Particles_Dissolve_CustomColor_Mask_Cap 在 _UsingNonPSR=1 下的 PS
生成: build_pyrios_body_fx.py（无头，需编辑器关闭或包未脏）；换算 pyrios_fx_plan.py
```

- 这条线是手写移植（早于反汇编直译管线），只实现三层材质启用的分支，其余报错。
- 如果要统一，可改用 §7 的直译管线重做，但需要先解决"一个槽三遍绘制"在 UE 里的合成。

## 15. 建议的下一步

1. **视觉验证试点**：在视口放 `NS_Eff_Pyrois_Attack_Normal_01_01_Trail`，用 Sequencer 或慢放截帧，与游戏视频对照方向、尺寸、颜色；结论写 `AAADocs/References/Captures/PyriosSkillFX/INDEX.md`。重点核对坐标/四元数换算、Local 对齐朝向、颜色线性化。
2. 对 8 个块跑 §3 的 A/B，列出所有 `Eff_Pyrois_*` 根，用 `zzz_fx_describe` 统计各技能启用的模块，按"缺什么功能挡住最多发射器"排序实现（预计 Shape、Billboard、Velocity 优先）。
3. 屏幕扭曲方案（UE Refraction 或自定义 SceneColor 采样）。
4. MeshRenderer 节点（BG/Mod/weapon）→ Niagara 单粒子网格，复用节点链与材质管线。
5. 触发：确定后用 GameplayCue（`/Game/GameplayCues/`）或 AnimNotify 生成系统，挂点按骨骼/socket 对照。
6. 视需要提交 AnimeStudio 的改动（该仓库有用户自己的未提交改动，提交前先核对范围）。

## 16. 规范提醒（来自项目规则）

- 汇报与文档用中文，解释带伪代码；代码注释中文、只描述现状。
- 改动后同步 Obsidian `GGYGO架构规划/Character/渲染实现.md`「技能特效」与 `计划_实施状态.md`。
- 代码搜索只在 `Source/GGYGO/**`；本管线全在 `AAADocs/Scripts`，不涉及 C++。
- 离线测试：`python -m unittest discover -s AAADocs/Scripts/tests`（目前 75 个，覆盖表面/身体 FX 生成器，技能特效脚本还没有单测）。

