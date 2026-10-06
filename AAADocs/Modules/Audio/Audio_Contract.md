# Audio 配置与资源生命周期契约

## 当前状态与范围

Audio 负责动作、脚步、命中及持续音效的配置、播放资源生命周期与清理。首批 Pyrois `Attack_Normal_01` 一次性动作声已完成素材导入、唯一原生 PlaySound Notify 接线、预览及 R1 语义回读。2026-10-06 正式 GA 必要冒烟中，R2 已观察固定 Sound／原 Owner／primary Mesh 的唯一新候选实际 Playing，随后候选退出并从原 Owner 组件列表移除，观察回调成功注销。该有限结果不证明 Notify 源关联、创建时刻、自然结束原因、AutoDestroy 动态值或 GC 完成；人工听感、持续 Cue 与网络仍未验证，全 Audio 未完成。

原严格冷读的 `EndTriggerTimeOffset` 原始差异及失败保留；资产 R1 语义通过不等于原始记录完全一致。独立手动组件的自然结束／重播／Stop／自身归还与正式 GA 的 R2 观察分别记账。正式观察 R1 的 protected `bAutoDestroy` 读取失败也保留；R2 通过合法公开属性读取修正观察边界，没有改声音、时机或一次性退出政策。原游戏音频触发帧、混音及空间参数仍未知。本轮集中同步本文档与外部 Audio 四图文，不授予源码、脚本、资产、UE / MCP、编译或 Git 写权。

## 职责与接口边界

| 所属模块 | 唯一职责 | 交给 Audio 的信息或资源 |
| --- | --- | --- |
| Animation / Montage / Notify | 动作姿态、真实触发时机及窗口语义 | 已确认的项目触发点、Mesh / Socket、音频配置引用 |
| Combat / Physics | 命中查询、去重及命中 / 表面语义 | 同一次命中的 HitResult 与表面 Tag |
| GAS / GA / GE | 能力生命周期、持续 Cue 的添加 / 移除及既有复制表现入口 | 原能力或原 Cue 的启动 / 终止请求 |
| Audio 配置与 Cue 表现 | 声音选择、音量 / 音高 / 变体 / 衰减 / 并发，以及自身播放资源释放 | SoundWave / SoundCue / MetaSound 配置及自身组件清理结果 |

- Audio 不建立动作计时器、命中逻辑、网络协议、第二套 Cue 路由或执行器；不读取或修改其他模块内部状态。
- 常改素材、表现组合与参数放 UE 资产和蓝图。首批使用原生 PlaySound Notify，无新增 C++ 类或通用调度器。
- 命中声继续通过既有 `UGGYGOGameplayCueNotify_HitImpact` 播放入口。招式专用音频不直接填入通用 `DefaultEffect`；动作 / 角色选择需由原调用方与 Cue 所有者冻结契约后另行接线。
- 现有 `DefaultEffect` 的显式正常配置模式与错误触发替代须分别核对。本文不直接判定现有资产配置非法，也不授予 HitImpact 修复范围。

## 首批来源与已保存接线

Pyrois 音频来源根目录：`F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model/Audio/`。`manifest.json` 用于定位动作；事件、Bank 与输出以各动作目录的 `mapping.json` 和实际文件列表为准，聚合计数不能代替实际文件清单。

Normal_01 来源目录：`F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model/Audio/Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_01/`。

| 项目 | 已核实值 / 边界 |
| --- | --- |
| 首批源文件 | 上述 Normal_01 目录的 `Skill_Attack_Normal_01.wav` |
| 原事件 | `Play_SFX_Char_Skill_Pyrois_Attack_Normal_01`，ID `667813318` |
| 映射记录 | 同目录 `mapping.json`；关联依据为 event-name prefix |
| 已保存首批资产 | `F:/ue_project/GGYGO/Content/Characters/Player/Pyrios/Audio/Normal01/SW_Pyrios_Normal01_Skill.uasset` |
| 已保存接线目标 | `F:/ue_project/GGYGO/Content/Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_Normal_01.uasset` |
| 已保存触发方式 | 原生 `AnimNotify_PlaySound`，轨道 `Audio_Normal01`，引用首批 SoundWave；GUID `A88EF5894349502A9527A2AF5905D5BF` |
| 音频文件信息 | 源 WAV 为 PCM、44.1kHz、16bit、双声道；UE 实际回读为 44100Hz、双声道、1.855351448 秒；已保存并取得原 Montage 预览组件 `IsPlaying=true` 证据，人工听感未验证 |
| 项目精确 Notify 帧 | 第 2 帧 / 60fps，配置时间 `2/60` 秒；原生回读 `0.03333333507180214` 秒。原游戏触发帧未知 |
| 游戏原混音 / 增益 / 空间参数 | 未确认，留空；后续项目参数须明确配置并区分原游戏证据 |

首批项目基线显式设置 SoundWave 非循环、Volume = 1.0、Pitch = 1.0；这是本项目配置，不代表已还原原事件增益或游戏混音。Audio 冻结、Animation 已写入且 R1 已回读的原生 PlaySound Notify 参数为 `bFollow = true`、`AttachName = NAME_None`、`VolumeMultiplier = 1.0`、`PitchMultiplier = 1.0`，`bPreviewIgnoreAttenuation = false`。声音跟随发起动作的 Mesh 组件，以组件为附着点，不依赖骨骼或 Socket；契约采用一次性声音自然结束，不承诺取消 Montage 即截断。R2 已观察正式链 Playing 后的候选退出，实际自然结束原因仍未证明。项目第 2 帧已确认并保存；原游戏触发帧、混音及空间参数证据继续留空。

同动作 `Impact_Attack_Normal_01.wav` 对应事件 ID `2052714205`；已核实文件信息，尚未导入或接入命中链。事件名称关联不能证明原游戏精确命中帧、表面适用条件或最终混音。

## 目录与配置规则

- 首批角色音频放 `F:/ue_project/GGYGO/Content/Characters/Player/Pyrios/Audio/Normal01/`，后续角色素材沿各自既有 Content 目录组织。
- 需要新增 Cue 资产时，留在当前扫描路径 `F:/ue_project/GGYGO/Content/GameplayCues/` 下；不新增独立扫描 / 播放链。
- 本地职责、来源和验收边界由本文档维护；完整需求开发及约定测试完成后集中同步外部 Audio 结构、计划和两张 Canvas，全局入口由统筹唯一维护。
- SoundWave / SoundCue / MetaSound 与 Notify 承担明确的音量、音高、变体、附着、衰减、并发和组合配置。缺失必需声音、无效引用或无效触发点时明确停止该步骤并定位原因，不替换为默认动作或另一声音。

## 播放资源与退出责任

| 声音类型 / 退出情形 | 所有者与契约 |
| --- | --- |
| 首批一次性动作声 | Notify 发真实时机，普通一次性声音自然结束；不持有 GA 可停止句柄，不承诺取消 Montage 时立即截断 |
| 一次性命中声 | 既有 HitImpact 的 `PlaySoundAtLocation` 路径自然结束；不用于持续循环或必须取消即停的音频 |
| 要求取消即停 / 持续声 | 单独明确 GA / GE 持有原 Cue 生命周期、Cue 持有自身 AudioComponent 的契约；优先复用引擎 `AGameplayCueNotify_Looping`，当前未实施 |
| 能力完成 / 取消 | 上游结束自己的持续 Cue；Cue 只停止 / 淡出并释放自己的播放资源，不能只依赖 NotifyEnd |
| 换 Pawn | 上游先结束旧 Avatar 的原持续 Cue，再启用新 Avatar 配置；不靠重新附着继承旧播放资源，不清理后继 Cue |
| Removed / 回收 / EndPlay | Cue 自身清理须幂等；复用引擎已有清理机制并验证实际退出路径。首批素材准备不证明这些生产清理链已闭合 |

## Run / Walk 与 Kevin 的证据边界

Pyrois `Run_Loop` 的 11 个装备声及 22 个脚步来源、`Walk_Loop` 的 5 个装备声及 18 个脚步来源，有真实 Bank 角色 Switch 分支证据；脚步容器与 Lycaon 共享。依据为音频根目录的 `movement_pyrois_armor_manifest.json`、`movement_pyrois_footsteps_manifest.json` 及各动作 `mapping.json`，不是凭目录名归属。

这些声音是 one-shot 随机短片段，动画目录名中的 `Loop` 不表示音频无限循环。地面材质名称、另一组 Switch 的业务含义、触发帧和混音未确认，配置留空；Audio 不另建走跑时钟或脚步碰撞查询。

Kevin 来源由统筹转交，PCK 为 `F:/Honkai Impact 3rd Game/BH3_Data/StreamingAssets/Audio/GeneratedSoundBanks/Windows/AUDIO_Vanilla_Default_2.pck`；名称索引为 `F:/AnimeStudio/_work/wwise_validation/bh3_wwise_names.json`，115 个实际 Bank 事件未另存为映射清单。`BK_BOSS_411` 的 Bank ID 为 `2366159711`，报告含 115 个事件、229 个内嵌 WEM；中文 Bank 起始偏移 `344246085`、长度 `8745260`，日文起始 `335360224`、长度 `8885861`。本会话未独立核验这些统计或解码文件。

| 统筹转交事件 / ID | 中文 WEM 来源（绝对 PCK 偏移 / 字节长度） | 当前边界 |
| --- | --- | --- |
| `BOSS_411_ANI_FIRE_ATTACK_01` / `230747614` | `908108476`：`351210565` / `40175`；`1036581940`：`352498197` / `41097` | RIFF WEM、双声道、44.1kHz；尚未单独提取或 UE 导入 |
| `FX_EVADE` / `3188014124` | `113223230`：`345293669` / `20575`；`682134181`：`349605413` / `19206` | RIFF WEM、双声道、44.1kHz；尚未单独提取或 UE 导入 |
| 对应 `_STOP` / `4062489817` | 停止节点 `618847005`，`Stop_E_O`；无独立结束音频 | 是停止操作，不能制造为结束 SoundWave |

精确动画映射、触发帧、解码输出路径与播放可用性仍未知；不阻塞 Pyrois 首批，也不据此导入 Kevin。

## 实施顺序、验收与停止点

| 原子步骤 | 唯一结果 / 精确范围 | 只读依赖、验收与停止点 |
| --- | --- | --- |
| Audio 导入准备与素材制作（已完成并冻结） | `AAADocs/Scripts/import_pyrois_normal01_skill_audio.py`、本文档、已保存首批 SoundWave | 单资产导入 / 保存成功；导入当时源 WAV / mapping / 原 Montage hash 保持，脏包恢复。该步骤只有同进程属性回读，资产 / 脚本保持冻结 |
| Animation 接线（已保存并冻结） | 已有 `AM_Pyrios_Attack_Normal_01.uasset` | 项目第 2 帧 / 60fps 增加一个原生 PlaySound Notify，显式参数已回读，两条既有 GameplayEvent 窗口保持。完整 protected Section 数据未取得，保留验收边界 |
| 原生资产回读 / 预览（部分验收） | 原冷读报告、R1 只读报告及原 Montage 预览证据 | 原严格冷读失败保留；R1 已加载对象语义回读通过，统筹另交回新 UE 进程加载证据。原 Notify 预览组件正在播放已证实；另行手动原临时组件自然结束 / 重播 / Stop / 自身归还已观察，不能代替原 Notify 退出、人工听感或新 GA |
| Gate57 统一编译（已通过） | 统筹冻结后统一构建 | `ModuleRepairGate_20261004_57_Result.json` 为 `Succeeded`，9 actions / 37.13 秒，runtime / Editor 链接完成，退出码未暴露。R1 在新 UE40416 / Gate57 DLL 中执行；编译及已有原生生命周期叶子冒烟均不证明 Audio 新 GA 实战链 |
| Normal_01 正式 GA 必要冒烟（有限完成） | Gate102 R2 五叶报告与原 Editor 日志 | 统筹确认新 UE39956／新 DLL；ProductionNativeHeld 为 Success／0 Error／4 Warning。实际 Playing→候选退出／原 Owner 列表移除及观察回调注销已观察，源关联、自然结束原因、听感和 GC 未证明；五叶整体为 3 Success／2 Fail，原失败保留 |
| 后续独立需求（未完成） | 听感、持续 Cue、换 Pawn／EndPlay、网络及其他声音 | 由各原所有者安排必要验证；一次性声不承诺 GA 取消即停。UE 操作仍由统筹独占，需统一构建时源码作者先冻结 |

### 固定目标脚本与资产保存保护

脚本：`F:/ue_project/GGYGO/AAADocs/Scripts/import_pyrois_normal01_skill_audio.py`。只接受 `import` / `readback` 两种模式，不提供任意 source / target、播放、Notify 编辑或其他资产创建功能。UE 控制台调用：

```text
py "F:/ue_project/GGYGO/AAADocs/Scripts/import_pyrois_normal01_skill_audio.py" --mode import
py "F:/ue_project/GGYGO/AAADocs/Scripts/import_pyrois_normal01_skill_audio.py" --mode readback
```

统筹通过 MCP Python 执行时，可使用 `runpy.run_path(脚本绝对路径)["run"]("import")` 或 `"readback"`；本会话不调用 UE / MCP 或运行脚本。

- `import`：要求目标文件 / 资产均不存在、原 Montage hash 符合导入前基线；原生 `SoundFactory` 显式关闭自动 SoundCue 和附带节点，`AssetImportTask` 禁止覆盖且 `save=False`。唯一输出须为固定 SoundWave；验证来源、44.1kHz、双声道、时长及非循环 / 1.0 音量音高后，仅调用目标 `save_loaded_asset`，核对文件已落盘。
- `readback`：要求目标已保存且执行前不脏；只加载 / 回读，禁止修改和保存。允许后续 Animation 已合法修改 Montage，记录本次入口实际 hash 并要求出口相同；此模式不替统筹验收此前 Montage 修改范围。
- 两模式都检查固定项目、源 WAV / mapping hash、真实来源元数据及脏 Content / Map 包前后集合。保存前最多允许新增目标 Content 脏包；保存后 / 回读后须恢复入口集合。不得 SaveAll、保存其他包、清除其他脏包或覆盖已有工作。
- 受保护的源与原 Montage 在 import 模式保存前再次核对；两模式出口也核对源 / mapping 和本次 Montage hash。目标已经存在、错误格式、必需属性 / API 不可读、额外输出 / 脏包或保存失败均明确失败；不选择另一 API / 素材作为隐式回落。
- 失败记录原异常和可取得的诊断快照，不自动重试、删除、回滚或保存失败资产。可能留下的目标内存资源 / 已保存包由统筹评估，不冒称已清理。
- UE `ImportedSampleRate` 与 `AssetImportData` 为 protected 属性：采样率通过原生 searchable AssetRegistry tag 回读；来源通过引擎创建的 `AssetImportData` 命名子对象及 `extract_filenames()` 读取，不新增反射 DTO 或绕过权限。
- 固定运行报告：`F:/ue_project/GGYGO/Saved/ValidationRecords/PyroisNormal01SkillAudio_20261004_import.json` 已生成，实际 `success=true`、`stage=complete`、`save_returned_true=true`；该导入脚本的独立 `PyroisNormal01SkillAudio_20261004_readback.json` 尚未生成。导入报告只证明导入后的同进程属性读取，不包含播放、Notify 或新 GA 验证；后来的 Notify 保存、预览和 R1 证据另列如下，不追写为该导入脚本的验收结果。

导入前冻结 SHA256：源 WAV `6EEAFD54C64C6D028DB1A734577860470BE657F3035CCE28529C562C289D3B55`；mapping `43884F9EA1EF79865CE91D2DDA7406A025491157CBE00288DD2E4ABFBC0B6F6C`；原 Montage `1D4D80F856385B7446F08F149034D7095A94B62CA5469DFFAB248D98C279E0B9`。

### 已完成的真实导入证据

2026-10-04 01:23:21（北京时间），统筹在真实 UE 执行 `import` 模式。唯一输出为 `/Game/Characters/Player/Pyrios/Audio/Normal01/SW_Pyrios_Normal01_Skill.SW_Pyrios_Normal01_Skill`，类型 `SoundWave`，真实来源为固定 Skill WAV。显式非循环、Volume / Pitch = 1.0；44100Hz、双声道、时长 1.855351448059082 秒。

资产文件 125471 字节，SHA256 为 `5F5665A04EFAE2938B5CC44CC6E82D9C817D0F79988E193D9E0E9FBF523E3248`。保存前只新增目标 Content 脏包，Map 脏包为空；保存后 Content / Map 均恢复为空。源 WAV、mapping 和原 Montage 三个冻结 hash 前后保持。本会话已实读导入报告并核对资产文件 hash；未操作 UE 或再次运行脚本。

该导入步骤证明原生导入、必需属性回读和精确单包保存；当时读取的是本次导入对象，单凭此报告不能证明冷加载、真实发声、停止、Notify 触发点或新 GA 生产调用链。后续证据按各自执行范围记录。

### 已保存的 Notify 与原生预览证据

接线报告为 `F:/ue_project/GGYGO/Saved/ValidationRecords/PyriosNormal01SoundNotify_20261004_Result.json`，保存成功。既有 Montage 只新增上述 `Audio_Normal01` 点 Notify；Sound 引用和显式跟随 / 附着 / 音量 / 音高参数已核对。两条旧 GameplayEvent 窗口 GUID `1B3A807246614835888A5E8CBB585861`、`793B4A2A49E3A4CF3CDDCF859F513B5A` 及其字段保持，源动画没有新增声音 Notify。Montage 保存后的 SHA256 为 `074A189170DBAFEAB31E779B12CEB1F992B6F7220288CFEDB6C47B6674FD88B3`；SoundWave 仍为上述已保存 hash。

统筹证据 `F:/ue_project/GGYGO/Saved/ValidationRecords/PyriosNormal01SoundNotify_20261004_RootSmoke.json` 记录：北京时间 2026-10-04 01:53:56.298（UTC 2026-10-03 17:53:56.298），原 Montage 预览经已保存的原生 PlaySound Notify 创建 `AudioComponent_124`，`IsPlaying=true`，Sound 为首批 SoundWave，Volume / Pitch = 1，附着 `DebugSkelMeshComponent_0`。这是原 Notify 的预览触发，未手工生成 SoundWave 播放；组件正在播放不等于人工已听见，也未观察自然结束、Stop 或新 GA 战斗链。

原生 UI 补充核对了 Main 第 0 帧 → End、End 第 101 帧（约 1.68 秒）→ None 等可见接线。`CompositeSections` 完整结构仍为 protected，脚本不能读取；UI 核对不能覆盖隐藏数值字段，完整 Section 数据验收仍未完成。

### 原严格冷读失败与 R1 语义回读

原报告 `F:/ue_project/GGYGO/Saved/ValidationRecords/PyriosNormal01SoundNotify_20261004_Readback.json` 保持 `status=failed`：新点 Notify 的导出原始字段 `EndTriggerTimeOffset` 从 `0.000000` 变为 `0.000100`，严格记录比对失败。`mutation_started=false`，失败时 Content / Map 脏包均为空；之后没有重接线或重保存资产。原失败报告 SHA256 保持 `CE0A78BEEE80C59DD7F17919608107C8C8D4BB82779629FFF5321A35679BF55F`，不得覆盖或改判通过。

R1 报告 `F:/ue_project/GGYGO/Saved/ValidationRecords/PyriosNormal01SoundNotify_20261004_Readback_R1.json` 为 `loaded_object_semantic_readback_passed_playback_unverified` / `phase=complete`。统筹交回的执行时间为北京时间 2026-10-04 02:26:46（UTC 2026-10-03 18:26:46）；该次执行在新 UE40416 / Gate57 DLL 中，只读既有加载对象，`mutation_started=false`、`save_succeeded=false`，Content / Map 脏包为空。

R1 使用已核实的原生契约 `F:/UE_5.8/Engine/Source/Runtime/Engine/Private/Animation/AnimTypes.cpp:86–98`：本事件 `NotifyStateClass=null`，普通点 Notify 的 `GetEndTriggerTime()` 返回 `GetTriggerTime()`，不消费 `EndTriggerTimeOffset`。因此仅此事件已观察到的未消费字段允许保留差异，其余字段继续精确核对；前后有效结束时间均为 `0.03333333507180214` 秒。报告明确 `raw_records_identical=false`，保留原始值变化，未证明实际执行过哪个原生刷新回调（`executed_refresh_callback_proven=false`）；不把该规则扩大为忽略 NotifyState 或其他字段差异。

R1 脚本本身 `fresh_reload_performed_by_script=false`，没有主动冷卸载 / 重载。新进程加载来自统筹另行提供的证据：原 UE11796 正常退出，新 UE40416 经原生 MCP 打开磁盘 Montage，执行 R1 前重新核对 PID40416 且没有活动 PIE；原失败后未保存或重接线。R1 的脚本结果与统筹加载证据分别成立，不能声称 R1 独立完成冷加载。R1 未执行播放，也未验证新 C++ / GA 链或完整 protected Section 数据。

### 独立手动组件的有限证据

原 Montage 的已保存 Notify、项目触发点及预览组件播放状态已有上述证据，无需再次作为待接线任务。统筹于 UTC 2026-10-03 18:52～18:55 在 UE40416 / Gate57 另行用原生 `SpawnSoundAttached` 创建手动临时组件 `AudioComponent_458`，附着原预览 Mesh，显式 `auto_destroy=false`。18:52:24.495 `IsPlaying=true`，18:53:47.623 在任何 Stop / 重播前 `IsPlaying=false`，随后 `Play(0)` 为 true、`Stop()` 后为 false。初次 `destroy_component()` 缺必需 Object 参数的 TypeError 原样保留；核对原生 `K2_DestroyComponent` 后，仅以原组件自身为 Object 修正清理，不重播或重做前面结果。原 owner 组件列表已移除该组件，Content / Map 脏包为空；Wave、Montage 和原失败报告 hash 保持。证据：`Saved/ValidationRecords/PyriosNormal01AudioComponentLifecycle_20261004_RootSmoke.json` 及原 UE 日志。

这项手动组件冒烟只证明该素材 / 原组件的可播、自然结束、可停和自身归还，不是原 Notify 的退出观察，也不证明 GA 取消即停、垃圾回收完成或人工已听见；后来的正式 GA 观察独立记录如下。

### 正式 GA 的 R1 失败与 R2 有限生产观察

原正式观察 R1 报告 `Saved/AutomationReports/GGYGO_Gate102_R1_RefreshEnd_BossBT_Audio_20261006_MCP.json` 保留真实失败：候选出现后读取 protected `bAutoDestroy` 被拒绝，`reason=prerequisite_or_read_failure`、`playing_seen=false`、`callback_removed=true`；该 Python Error 使 ProductionNativeHeld 原叶 Fail，原 End／Run 断言仍执行。不能用 R2 改写 R1 或此前 Gate57 严格冷读失败。

修正仅限有界只读观察脚本 `Saved/ValidationScripts/ObservePyriosNormal01Audio_20261006.py`：取消受保护字段读取；Pitch／Volume 使用公开 `pitch_multiplier`／`volume_multiplier`，启动时只读 CDO 验证访问，现场读候选实际值。`auto_destroy_live_observed=false`、`auto_destroy_live_value=None`，Notify 的 `SpawnSoundAttached` 默认政策仅作为静态依据，不能代替动态测量。脚本不启动 PIE、不发输入、不手工 spawn／Play／Stop、不重播、不写资产，不持 UObject 跨采样；身份键仅为非持有 path／hash／class 定位，不证明原生弱序号或 ABA 排除。它只通过自己注册的 Slate posttick 有界观察，并注销自己的回调。

2026-10-06 统筹在新 UE39956／新 DLL 执行 R2。原报告为 `Saved/AutomationReports/GGYGO_Gate102_R2_RefreshEnd_BossBT_Audio_20261006_MCP.json`，原日志为 `Saved/Logs/GGYGO_Gate102_R2_RefreshEnd_BossBT_Audio_Editor_20261006.log`（`[Normal01Audio]`，2587–2611 行；正式 End／移动断言在 2636–2637 行）。Audio 组长已只读核对这两项原证据。

| R2 现场事实 | 实际结果与解释边界 |
| --- | --- |
| 正式动作前基线 | `/Game/Map/L_Movement_Test` 的原 World／Pawn／primary `CharacterMesh0`／`ABP_Pyrios_C_0`，脚本校验原模型和 FullBody 配置，基线 AudioComponent 数为 0；不绑定预览 Mesh 或后继 Pawn |
| 目标动作与唯一候选 | Normal_01 Montage 的 Main、实际 Rate=1；固定 Sound、原 Owner 与原 Mesh 匹配的唯一新 `AudioComponent_0`，首次出现 audio-time 区间 `(0.009649299, 0.185087197)` 秒；这是采样出现区间，不是创建时刻或 Notify 源关联证明 |
| 实际播放 | `AudioComponentPlayState.PLAYING` 且 `IsPlaying=true`，候选公开 Pitch／Volume 均为 1；AutoDestroy 动态值与人工听感未观测 |
| 原动作退出及后续候选退出 | Montage 在 audio-time `1.698406294` 秒不再 active；随后候选 invalid／removed、原 Owner 仍有效且组件列表已移除候选。采样 presence bracket 为 `(1.951937400, 2.136754695)` 秒 |
| 观察分类与清理 | 198 样本，最大采样间隔 0.032 秒，`reason=playing_then_exit_in_duration_window_observed`，`callback_removed=true`。分类使用脚本 0.10 秒比较余量；不是精确时长吻合、自然完成／AutoDestroy／GC 原因证明 |
| 原生产叶与五叶整体 | ProductionNativeHeld 为 Success／0 Error／4 Warning；End 剩余 0.494577 秒发生正常策略中断，资源恢复，真实 Run 778.427 cm/s、位移 1021.141 cm。整体 3 Success／2 Fail：OriginalEndAfterSameBindingRefresh 的 Completed 断言失败、RequiredTreeRejectsInvalidRoot 的两条原生产 Error 均保留，不称整批全绿 |

首批正式 GA 的实际播放与有限退出必要烟已完成，一次性声音不承诺 GA／Montage 取消即停的政策保持。完整 protected Section 数据、人工听感、自然完成原因、可取消／持续 Cue、动作专用命中选择、其他动作、脚步材质与时机、Kevin 解码接线、换 Pawn／EndPlay 和网络仍未完成。原游戏触发帧和混音仍未知，不以项目第 2 帧声称还原。

SoundWave、Montage 和所有脚本保持冻结；本轮仅同步五份现有契约／Audio 图文，全局入口由统筹维护。当前未新增循环依赖、第二套生产状态／执行链或跨模块内部状态访问；一次性与持续音效退出责任不变。
