# BH3 Kevin DemonBattle 导入核对

> 当前检查点（2026-10-08）：Kevin 目录当前 Registry 为 150 个资产，即既有 104 个模型／动画／材质包加新增 46 个 SoundWave；音频已保存并完成独立 Commandlet 回读。素材已入库，设备播放、原动作触发时机及 Boss 场景／战斗接线仍未验收，详见本文末尾的本轮交付记录。

## 结果（2026-09-29，UE 5.8）

- 先清点 BH3 全目录：931 文件，320 FBX / 424 JSON / 187 PNG。只导入 `F:/AnimeStudio/Exports/BH3/Animator/Kevin/05_BOSS_411_DemonBattle`。
- 目标 `/Game/Characters/Boss/Kevin/DemonBattle/`，本模块写入 `Mesh/` 和 `Animation/`。
- 已保存 1 SkeletalMesh、1 独立 Skeleton、75 AnimSequence，共 77 资产。75/75 含曲线动画成功；79 条源索引中 4 条没有动画曲线，未生成动画。
- 模型 `Mesh/SK_Kevin_DemonBattle`，Skeleton `Mesh/SK_Kevin_DemonBattle_Skeleton`，动画 `Animation/AS_<源clip名>`。
- `BOS_411_Ani_Counter` 与 `BOSS_340_Ani_Stun` 已按完整层级匹配并成功导入；没有按名称过滤。非法字符确定性替换为下划线，审计无命名碰撞。

## 骨架、尺度与样片

源 FBX 7300，Y-up，UnitScaleFactor=1cm，导出已烘焙100倍。导入统一比例1、坐标转换开启、单位转换开启、ForceFrontXAxis=false、额外平移旋转为零。源文件只读，未执行 Pyrios 去根、重定向或骨架复用。

模型有484个非网格Model与7个网格；79动画以LimbNode保留网格名，491节点名称/父子层级与模型一致。UE Skeleton回读491节点，根BOSS_411，Bip001和名为Root的辅助节点均在其下。JSON Avatar骨数358是来源元数据，不能作为实际导入骨数。

Mesh参考包围盒约399.56×460.36×335.91cm，包含武器和翼部。StandBy Persona预览人物直立、武器/翼部完整，没有明显蒙皮爆开；玩法前向尚未验收。

StandBy以60fps导入，132键、131帧区间、2.1833334s。JSON stopTime=2.1666667s，FBX原始Take多一帧，保留原导出范围。Fly_Attack_03_AS/Summon/Between/Shoot/BS按来源30fps导入，其余按60fps。每条动画回读同一Skeleton、正时长、enable_root_motion=false、force_root_lock=false。Unity loopTime仅保存在BH3.SourceLoopTime元数据中，未生成状态机循环接线。

## 源空片段

| 源clip | 结果 |
| --- | --- |
| BOSS_411_Ani_Add_HitBox | 无AnimationCurve，1秒空Take；未生成AnimSequence |
| BOSS_411_Ani_Normal_HitBox | 同上 |
| BOSS_411_Ani_No_Weapon | 同上 |
| BOSS_411_Ani_Have_Weapon | 同上 |

初次UE批量返回4个导入失败（未找到网格或动画轨道）；原始报告保留。最终报告结合源审计归类source_empty，脚本已补充空曲线预检。没有合成动作、修改原FBX或把此问题归为骨架不兼容。

## 渲染接线契约

| 槽序号 | 实际材质槽名 |
| --- | --- |
| 0 | BOSS_411_Weapon_Blade_Material |
| 1 | BOSS_411_Material_Face |
| 2 | BOSS_411_Material_Eye |
| 3 | BOSS_411_Material_Hair |
| 4 | BOSS_411_Material_Wing |
| 5 | BOSS_411_Material_Body02 |
| 6 | BOSS_411_Material_Wings_Blue |
| 7 | BOSS_411_Material_Body01 |

导入阶段关闭材质/贴图自动导入，保留8槽。Materials、Textures及后续材质接线交给渲染模块。本轮动画预览不需PhysicsAsset，因此未创建；没有BossAI、ABP、Montage或主关卡接线。

## 脚本与报告

脚本 `AAADocs/Scripts/import_bh3_kevin_demonbattle.py`：

```text
python import_bh3_kevin_demonbattle.py --stage audit
py "F:/ue_project/GGYGO/AAADocs/Scripts/import_bh3_kevin_demonbattle.py" --stage smoke
py "F:/ue_project/GGYGO/AAADocs/Scripts/import_bh3_kevin_demonbattle.py" --stage all
```

后两条在独占编辑器时段、底部Cmd执行；先核对smoke预览再all。脚本使用FbxFactory，临时关闭Interchange FBX并在finally恢复原值。已有资产必须匹配BH3.ImportOwner与来源SHA256（动画同时匹配Skeleton）、没有未保存修改且有磁盘包才只读跳过，未知资产停止，不覆盖。保存返回值和磁盘包存在性都通过才标 imported；保存失败不能计为完成。整批重复执行尚未另跑一轮；StandBy在原 all 阶段已通过旧版已有资产分支。A5 新保护只做离线测试，尚未重跑 UE 导入；见 `AAADocs/Modules/Animation/Animation_Asset_Production_Safety.md`。

运行报告位于项目`Saved/Codex/`：

- `bh3_demonbattle_source_audit.json`：全目录统计、骨架层级、单位、源哈希、79条映射。
- `bh3_demonbattle_smoke_report.json`：模型+StandBy成功。
- `bh3_demonbattle_all_report.json`：原始批量执行，74新增/1已存验证/4源空失败。
- `bh3_demonbattle_final_report.json`：保留原始失败信息并分类4项source_empty；importable_complete=true，index_fully_imported=false。
- `bh3_demonbattle_verification.json`：独立只读核验已执行；75 条动画共用本包 Skeleton、491 层级节点，材质导入后全目录为 104 资产。

UE日志`Saved/Logs/GGYGO.log`：08:21:46模型导入，08:21:49样片保存，08:25:23批量结束（日志时间UTC）。模型存在缺失平滑组与部分bind pose信息提示，UE报告重建绑定姿势成功。75动画仅StandBy进行了视觉预览；其余逐条视觉、材质质量、物理和玩法表现仍未验收。

2026-09-29 导入阶段的架构说明与三张 Animation Canvas、根导航/状态及总览入口已同步。Content/Characters 依照现有美术资产管线处于 Git 忽略范围；该阶段提交脚本与说明，当时的 104 个 `.uasset` 保存在本机，不随普通 Git 提交分发。

## 本轮资产交付（2026-10-08）

### 既有模型与动画复核

本轮复用指定 DemonBattle 来源的已保存资产。音频导入前，BossAI 在非 PIE 的只读 UE／MCP 窗口核对了目标目录 Registry 与磁盘，104 个包一致，无缺包或多余包，Kevin 目标包无未保存修改。

| 已核证据范围 | 实际资产分类 |
| --- | --- |
| 音频导入前的 Registry／磁盘对照：104 包 | 1 SkeletalMesh、1 Skeleton、75 AnimSequence、8 MaterialInstanceConstant、3 Material、16 Texture2D |
| 本轮独立 Commandlet 回读：新增 46 包 | 46 SoundWave，位于下列 6 个动作目录 |
| 统筹最新原生 AssetTools 全目录查询：150 资产 | 上述既有 104 个资产加 46 SoundWave；AnimMontage 为 0 |

75 条序列与现有有效动作清单完全一致，均使用独立 Kevin Skeleton、正时长、`enable_root_motion=false`、`force_root_lock=false`，导入 Owner 元数据一致。模型与 75 条动画的 76 份来源 FBX 摘要匹配；491 骨骼层级及 8 个材质槽保持。4 条源空片段仍未生成动画。本轮没有重新导入或覆盖模型、骨架、动画及材质。

统筹随后在当前 8000 编辑器原生核对了全部 150 个资产：模型为 `Mesh/SK_Kevin_DemonBattle`，75 条动画位于 `Animation/`，46 个 SoundWave 位于 `Audio/` 的六个动作目录，其余为独立 Skeleton、8 个材质实例、3 个 Preview 主材质及 16 个贴图。现有 `Mesh/`、`Animation/`、`Materials/`、`Textures/`、`Audio/<动作>/` 层级已按素材职责划分。逐动作视觉、材质质量、模型物理及战斗表现仍保留原未验边界。

[现有战斗准备记录](KevinDemonBattle/BH3_Kevin_Combat_Implementation.md)中的 55 条 Montage 准备项与独立 ABP 方案仍属候选生产记录。只读检查的既有 104 包中没有 Montage、ABP、Motion 或 Gameplay 资产；本轮音频交付没有新增这些资产或生产接线。

### Boss 场景与生产接线状态

[Kevin 接线配置](KevinDemonBattle/BH3_Kevin_Combat_Wiring_Config.json)明确为 `prepared_not_executed`，生产目标是 `Gameplay/BP_Kevin_DemonBattle`、`BP_GA_Kevin_Ice01/02` 及配套 Pawn／AbilitySet／ActionSet／Boss DataAsset；动画目标为 `Animation/ABP_Kevin_DemonBattle` 与候选 Montage，另依赖 `Motion/` 中的动作资产。当前 Kevin 的 150 项 Registry 分类及项目磁盘命名盘点均未发现这些配置预期的已保存资产。配置中的 BehaviorTree 为空，玩法调参仍标为 provisional。

只读磁盘盘点同时检查了角色目录外的资产：`/Game/AI/Boss/Test` 已有 `BP_Boss_Test`、`BP_GA_BossMelee_Test`、`AM_BossMelee_Test` 与测试 Pawn／Boss／ActionSet 及 `L_BossAI_Test`。这些是既有 Boss 测试资产；Kevin 专用配置的生产目标仍待创建与接线。

BossAI 随后在统筹授予的短独占只读窗口完成原生 Registry／包引用核对，使用 `AssetTools.find_assets`、`get_asset_class`、`get_referencers`：

| 原生查询 | 实际结果 |
| --- | --- |
| 全项目 Registry（含插件内容），资产名包含 `Kevin` 或 `DemonBattle` | 去重 9 项：3 Material、1 SkeletalMesh、1 Skeleton、1 Texture2D、2 World、1 InterchangeSceneImportAsset；没有相关命名的 Blueprint、AnimationBlueprint 或 GA 资产 |
| `Mesh/SK_Kevin_DemonBattle` 的包引用者 | 仅 `Mesh/SK_Kevin_DemonBattle_Skeleton` |
| Kevin Skeleton 的包引用者 | 75 条已导入 AnimSequence＋该 SkeletalMesh，共 76 项；没有 Pawn／Blueprint、ABP、Montage 或地图包 |

两张 World 为 `/Game/Map/BH3/L_KevinBoss_P1`、`L_KevinBoss_P3`；`SceneImport_Stage_KevinBoss_P1` 的类型为 InterchangeSceneImportAsset。它们是场景资源，当前原生模型／Skeleton 包引用链没有已注册的 Boss Pawn 或地图装配引用。素材入库与 Boss 场景装配是两个验收阶段，Kevin 专用生产 Pawn、ABP、Montage、GA 及战斗链仍待生产接线。

该核对覆盖命名候选与模型／Skeleton 的直接包引用及其一级链路；当前关卡 Actor 实例、未保存实例配置和动态加载／运行时装配未回读，场景可见或可玩状态未验。窗口内仅执行注册 GET 工具，没有开图、放 Actor、编译或保存资产；核对结束即归还公共窗口。

### 按真实动作目录交付音效

资源解包组的真实输出位于源目录 `Audio/`，机器消费入口为 [manifest.json](F:/AnimeStudio/Exports/BH3/Animator/Kevin/05_BOSS_411_DemonBattle/Audio/manifest.json)，各动作使用自己的 `mapping.json`。79 个目录与现存配对 JSON／FBX 的真实动作名一致；6 个动作有名称关联媒体，共 46 个 WAV。音频来源／宿主校验、原生导入警告及后续接线责任统一见 [Audio 契约](../../Modules/Audio/Audio_Contract.md)，本文记录整体资产检查点。

| 实际动作目录 | 已保存 SoundWave |
| --- | ---: |
| `BOS_411_Ani_Counter` | 7 |
| `BOSS_411_Ani_Fire_Attack_01` | 5 |
| `BOSS_411_Ani_Fire_Attack_02` | 15 |
| `BOSS_411_Ani_Fire_Attack_04` | 6 |
| `BOSS_411_Ani_Fly_Attack_01` | 7 |
| `BOSS_411_Ani_Fly_Attack_02` | 6 |
| 合计 | 46 |

目标为 `/Game/Characters/Boss/Kevin/DemonBattle/Audio/<真实动作名>/SW_<源 WAV 文件名主干>`。46 个动作目录内文件对应 42 份不同原媒体，跨动作及中日 Bank 的共享来源保留在映射中；没有把共享媒体视为额外独立来源，也没有把父动作事件自动分配给阶段／循环片段。

本轮使用 [import_bh3_kevin_demonbattle_audio.py](../../Scripts/import_bh3_kevin_demonbattle_audio.py)，由统筹在标准 UE Commandlet 中执行 new-only 导入、精确保存及独立回读。四次原日志均记录脚本成功与 Commandlet `result 0`，统筹交回四次进程 `exit 0`：

| 执行阶段 | 实际结果 | 原日志 |
| --- | --- | --- |
| 首件导入 | 保存 1 个 SoundWave | [FirstImport](../../../Saved/Logs/KevinAudio_Commandlet_FirstImport_20261008_1740.log) |
| 首件独立回读 | 回读 1 件，`saved=[]` | [FirstReadback](../../../Saved/Logs/KevinAudio_Commandlet_FirstReadback_20261008_1746.log) |
| 其余 45 件导入 | 保存 45 个 SoundWave | [Remaining45](../../../Saved/Logs/KevinAudio_Commandlet_Remaining45_20261008_1758.log) |
| 全部 46 件独立回读 | 回读 46 件，`saved=[]` | [All46Readback](../../../Saved/Logs/KevinAudio_Commandlet_All46Readback_20261008_1801.log) |

原日志的 1＋45 保存集合、全部 46 件回读集合与资源 manifest 的目标集合一致，统筹已核磁盘实际 46 个 SoundWave。每件来源、ImportedSampleRate、声道、时长及显式 `Looping=false`、`Volume=1`、`Pitch=1` 校验通过。保留源采样率 44100Hz×36、32000Hz×4、36000Hz×6，以及双声道 41／单声道 5；未重采样或转换声道。源 WAV 为 PCM16，实际文件／完整 PCM／来源摘要的离线核验已通过。

### 验收边界与剩余缺口

- 当前完成的是资产保存及独立进程格式／来源回读。四份结果均为 `playback_tested=false`、`timing_mixing_verified=false`；设备实际播放、人工听感、原混音／增益／随机选择／循环行为未验。原音频导入警告及未试听边界保留在原日志与 Audio 契约中。
- 73 个源动作没有可证音效关联；根 manifest 的 143 个未分配事件记录未挂到动作或生成替代声。动作目录内 28 个记录事件包含 27 个 `name_associated` 与 1 个无 WAV 的 `control_only`，不证明原动画触发配置或精确帧。
- `Fire_Attack_04` 的 `FLY_DOWN_FOLLOW` 与 `HOLD_ENV` 仍分别缺播放节点 `615330980`、`61986963`，映射保留 `failed_unresolved_playback_reference` 与空输出。全 Bank 的 7 项播放节点缺失、停止／空事件及静音生成器继续按真实来源记录，不制造 WAV；检索范围与其它未分配项详见资源 manifest。
- 六个动作有部分真实 WAV，完整 Boss 音效及 Notify／Montage／GA 接线仍未完成。准确触发时机、动作组合、伤害与移动等战斗链不在本次资产验收范围。

本轮仅集中同步本导入记录，Audio 详细契约由 Audio 唯一维护。新增 SoundWave 已保存在本机，沿用既有美术资源忽略政策；Git 与全局进度入口由统筹安排。
