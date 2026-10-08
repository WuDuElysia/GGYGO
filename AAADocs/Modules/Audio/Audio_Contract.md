# Audio 配置与资源生命周期契约

## 当前状态与范围

Audio 负责动作、脚步、命中及持续音效的配置、播放资源生命周期与清理。首批 Pyrois `Attack_Normal_01` 一次性动作声已完成素材导入、唯一原生 PlaySound Notify 接线、预览及 R1 语义回读。2026-10-06 正式 GA 必要冒烟中，R2 已观察固定 Sound／原 Owner／primary Mesh 的唯一新候选实际 Playing，随后候选退出并从原 Owner 组件列表移除，观察回调成功注销。该有限结果不证明 Notify 源关联、创建时刻、自然结束原因、AutoDestroy 动态值或 GC 完成；人工听感、持续 Cue 与网络仍未验证，全 Audio 未完成。

原严格冷读的 `EndTriggerTimeOffset` 原始差异及失败保留；资产 R1 语义通过不等于原始记录完全一致。独立手动组件的自然结束／重播／Stop／自身归还与正式 GA 的 R2 观察分别记账。正式观察 R1 的 protected `bAutoDestroy` 读取失败也保留；R2 通过合法公开属性读取修正观察边界，没有改声音、时机或一次性退出政策。原游戏音频触发帧、混音及空间参数仍未知。2026-10-06 Pyrios 检查点集中同步本文档与外部 Audio 四图文，不授予源码、脚本、资产、UE / MCP、编译或 Git 写权。

2026-10-08 Kevin DemonBattle 的按动作素材检查点已完成：六个真实动作目录的 46 个 SoundWave 已导入、精确保存，并经独立新 Commandlet 逐份冷加载回读。这里只完成素材准备；实际设备播放、动作接线、原触发帧和混音仍未验证。该检查点仅集中更新本文档，不改变上述 Pyrios 结论或运行时职责，不据此重画 Canvas。

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

### Kevin DemonBattle 按动作素材（2026-10-08）

来源根目录为 `F:/AnimeStudio/Exports/BH3/Animator/Kevin/05_BOSS_411_DemonBattle/Audio/`，按 `<真实源动作>/mapping.json` 声明的实际 WAV 导入。源 `manifest.json` 用于定位与冻结交接，冻结 SHA256 为 `cfd02e6c73aa7c2c899a03436fb5a0ecf16c1689f71359771bc6343561384557`；事件归属、操作分类和缺项仍以各动作 mapping 为准。资源组长交回的两语言 `BK_BOSS_411`（Bank ID `2366159711`）各有 171 个事件、229 个内嵌媒体；此前转交的 115 事件统计只是旧检查点，不能代表当前完整 Bank。

79 个真实源动作均有目录与 mapping；其中六个动作有 46 个 PCM16 WAV，另 73 个动作没有可导入 WAV，不制造占位音效。46 份均为 `name_associated`，媒体图解析依据为 `original_graph_resolved`，`sourceNotifyVerified=false`、`animationTriggerSeconds=null`。名称和媒体图关联不能证明动画触发帧。`shared` 保留已核实的 ja／zh_CN 同源字节关系，不伪造两套语言音效；42 份唯一媒体按动作组织为 46 份文件，跨动作复用保留各动作副本。

UE 根目录为 `/Game/Characters/Boss/Kevin/DemonBattle/Audio/`，磁盘对应 `F:/ue_project/GGYGO/Content/Characters/Boss/Kevin/DemonBattle/Audio/`。每个动作目录仅新增 `SW_<WAV文件名主干>` SoundWave；不导入控制操作，不新增 SoundCue、Montage、Notify 或 GA 接线。

| 真实动作／根目录下子目录 | 已保存 SoundWave 数 |
| --- | ---: |
| `BOS_411_Ani_Counter` | 7 |
| `BOSS_411_Ani_Fire_Attack_01` | 5 |
| `BOSS_411_Ani_Fire_Attack_02` | 15 |
| `BOSS_411_Ani_Fire_Attack_04` | 6 |
| `BOSS_411_Ani_Fly_Attack_01` | 7 |
| `BOSS_411_Ani_Fly_Attack_02` | 6 |

整体模型／动画与资产导入状态见 [Kevin DemonBattle 导入核对](../../Assets/BH3/BH3_Kevin_DemonBattle_Import.md)；本文维护 Audio 配置、工具和验收边界，不重复维护逐件资产清单。

#### 固定来源、显式宿主与保存契约

工具为 [import_bh3_kevin_demonbattle_audio.py](../../Scripts/import_bh3_kevin_demonbattle_audio.py)，冻结 SHA256 `AE0E232919AFA6DF87319052347A282F3E2169BC6224CDE4C6027B360F2D5465`。离线 `build_plan(actions)`／`--mode plan` 只读实际 mapping、FBX 身份与 WAV；拒绝目录越界、未映射文件、计数／命名冲突及无效 PCM，不写资产或报告。

原生入口为 `run(mode, actions, expected_targets, host="editor")`，CLI 对应 `--mode import|readback --actions <明确动作集合> --expect-targets <已复核目标集合> --host editor|commandlet`。目标集合必须是本次 plan 的显式非空子集；首件与余 45 件分批均由统筹指定，已有目标不会自动跳过、覆盖或重导入。

- `editor` 是 GUI 调用的默认宿主，要求无 `-run` Commandlet、存在 `LevelEditorSubsystem` 且非 PIE。`commandlet` 必须显式选择并验证原生 `-run=PythonScript`，通过公开 PIE World 查询确认本进程非 PIE；不调用 Commandlet 中缺少 GUI 引擎上下文的 PIE 接口，也不因 API 缺失回落为“安全”。原生 `-Script="脚本绝对路径及全部Python参数"` 须将全部脚本参数放在同一引号内。
- 两宿主均核对固定项目、选定目标不脏；导入另要求目标在本进程磁盘、注册表与内存中均不存在。源／mapping 的 size、mtime 快照只在本次调用有效，真实原生导入／保存／加载回调后复核，不建立长期来源缓存。
- `SoundFactory` 关闭自动 Cue 与附带衰减／循环／调制节点，`AssetImportTask` 禁止覆盖且 `save=False`。返回必须是唯一计划 SoundWave，才显式设置非循环、Volume／Pitch=1；这些是本项目素材默认值，不表示已还原原事件循环、增益或音高。
- 保存前核对来源、采样率、声道、时长与默认值，并限制本进程新增脏包仅为自身目标；只调用该对象的 `save_loaded_asset`。保存后核对非空磁盘包和必需属性，Content／Map 脏包集合须保持入口事实；不 SaveAll，不保存或清除其他工作。
- `readback` 只加载已保存且不脏的精确目标并读取属性，不含 setter、导入或保存。来源使用命名 `AssetImportData` 子对象的 `extract_filenames()`，采样率使用公开 `ImportedSampleRate` 注册表 tag；不绕过 protected 属性。
- 原生失败明确传播并记录当前目标及此前已保存列表，不自动重试、删除或回滚，也不声称整批原子提交。Commandlet 的注册表／内存／脏包基线只描述自身进程；主编辑器与既有用户工作由统筹独立保护，不能据此声称 GUI 全局无修改。

实际执行由统筹独占标准 CLI 窗口，Audio 仅离线核对。统筹在执行期间禁用第二 MCP 自动启动并保留主编辑器；普通 Saved 日志／DDC 不计为受保护业务资产。统筹交回四份用户文件与 P1 两份文件的写轮前后磁盘指纹相同；此前 GUI 输入引发的 P1 非预期保存证据与备份仍保留，不改判为“从未保存”。本检查点结束后脚本、资产及执行窗口继续冻结。

#### 真实导入与独立冷读证据

以下原日志均位于 `F:/ue_project/GGYGO/Saved/Logs/`，由统筹执行；各原生进程退出码均为 0。Audio 已只读解析导入及全量冷读日志，与冻结 plan 逐份核对目标、来源、格式、时长和磁盘文件。

| 实际步骤 | 原始日志／结果位置 |
| --- | --- |
| 首件导入（PID 100472） | `KevinAudio_Commandlet_FirstImport_20261008_1740.log`：2047 行实际 1 件，2073 行原生 Python 成功 |
| 首件独立冷读（PID 95116） | `KevinAudio_Commandlet_FirstReadback_20261008_1746.log`：2035 行实际 1 件，2059 行原生 Python 成功 |
| 剩余 45 件导入（PID 82708） | `KevinAudio_Commandlet_Remaining45_20261008_1758.log`：2448 行实际 45 件，3001 行原生 Python 成功 |
| 全 46 件独立冷读（PID 79444） | `KevinAudio_Commandlet_All46Readback_20261008_1801.log`：2035 行实际 46 件，2552 行原生 Python 成功；`saved=[]` |

首件为 `BOSS_411_Ani_Fire_Attack_01/SW_ANI_FIRE_ATTACK_01__shared__wem_1036581940`；余 45 件与其互斥，合计正好 46 个非空磁盘资产。全量冷读的 36 份 44100Hz、4 份 32000Hz、6 份 36000Hz，以及 41 份双声道、5 份单声道均与 WAV 相同；最大时长差约 `1.11e-7` 秒，在原严格容差内。原生 `inspect_asset` 对每份非循环、Volume／Pitch=1 的断言通过；返回 JSON 未逐项列出这些默认值，不把它描述为独立 JSON 字段证据。

剩余 45 件导入日志的 2036、2158、2285、2304 行分别对以下 SoundWave 报告起始 DC 偏移大于 100：Counter 的 `SW_FX_COUNTER_WIN_P1__shared__wem_243896595`（2 声道）、Fire02 的 `SW_FX_FIRE_ATTACK_02_00__shared__wem_355178717`（1 声道）、Fire04 的 `SW_FX_FIRE_ATTACK_04_GROUND_CRACK_BOOM__shared__wem_355178717`（1 声道）、Fire04 的 `SW_FX_FIRE_ATTACK_04_HIT_DOWN_GROUND__shared__wem_710904726`（2 声道）。原警告提示可能爆音或不宜循环；没有修改源、归一化或重导入掩盖警告，实际听感未验证。

六动作 mapping 中另有六条无 WAV 的事件记录，包含控制／STOP 操作，不能统称为六个缺失音频。Fire04 的 `BOSS_411_FX_FIRE_ATTACK_04_FLY_DOWN_FOLLOW`（播放节点 `615330980`）与 `BOSS_411_FX_FIRE_ATTACK_04_HOLD_ENV`（`61986963`）仍为资源交回的真实未解析播放来源，不以固定声音或默认成功补齐。73 个无 WAV 动作、未分配 Bank 事件与其他来源缺项均未因本次导入关闭。

本检查点证明按动作素材导入、精确保存和独立新进程冷加载属性回读；`playback_tested=false`、`timing_mixing_verified=false`。设备发声／人工听感、原 Notify、触发帧、原增益／音高／路由／随机／材质／叠层／循环及最终混音、动作与命中接线、Cook 与网络均未验证，不称 Kevin 全部音效或战斗音效接入完成。

按代码规范六项自审，来源计划、显式执行宿主与单资产导入／回读有明确边界；只持本次来源和脏包快照，唯一资产提交仍由原生保存入口执行，失败如实传播。外调后的来源／脏包保护必要保留，未引入运行时状态、第二套播放／帧调度、循环依赖或通用角色业务分支；本次只改 Python 素材工具与已授权说明，不需要新增 C++ 构建。实际 Commandlet 导入和冷读验证已完成，未验证播放边界保留。

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

首批正式 GA 的实际播放与有限退出必要烟已完成，一次性声音不承诺 GA／Montage 取消即停的政策保持。完整 protected Section 数据、人工听感、自然完成原因、可取消／持续 Cue、动作专用命中选择、其他动作、脚步材质与时机、Kevin 动作音效接线、换 Pawn／EndPlay 和网络仍未完成。原游戏触发帧和混音仍未知，不以项目第 2 帧声称还原。

SoundWave、Montage 和所有脚本保持冻结；上述 Pyrios 检查点仅同步五份现有契约／Audio 图文，全局入口由统筹维护。当前未新增循环依赖、第二套生产状态／执行链或跨模块内部状态访问；一次性与持续音效退出责任不变。
