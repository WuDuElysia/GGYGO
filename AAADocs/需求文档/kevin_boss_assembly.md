# Kevin DemonBattle Boss 完整组装与视听制作

状态：完整组装与单机自验完成。正式 Encounter 战斗、完整 Dash_F 追击、两条空中连招真实落地、主要技能画面和死亡清理均有证据；核心评审问题已修复并定向复验，必要 Obsidian 已同步，分仓交付范围见末节。Kevin 联机、Cook、性能和设备试听未验。

## 目标与用户决定

- 把 Kevin DemonBattle 从素材和少量试招接线组装成可实际交战的 Boss：技能、动画、选招／阶段、位移、命中、特效和音效形成完整链路。
- 战斗调参由本项目设计（用户 2026-11-05 决定）：完整 DemonBattle 单形态、两阶段，暂定 50% 血量切换递进技能池；血量、伤害、冷却、权重和阶段都做成数据可调，不冒称原版参数。初版数值由负责人结合当前玩家能力自定。
- 动画和音效优先还原真实来源。特效允许参考原效果图适配创作，也允许完全原创，不用逐项审批，但要区分参考来源、实际改编和未知项。
- 只用现有 DemonBattle 形态，不引入其他 Kevin 形态、玩家 E／R／F、全员失败／复活系统或引擎修改。
- 用户 2026-11-11 选择：`Fly_Loop` 原片段约 0.033 秒且根位置跳变约 186 厘米，不能当作静止循环。取其最后一帧全身骨骼制作静止等待姿态，既定技能轨迹和 CMC 原生重力落地保持不变；原始序列只读。
- 用户 2026-11-11 选择：普通追击按原移动动画曲线补齐，不改成固定速度寻路；确认没有向前走／跑循环后，进一步选择用完整 Dash_F（约 1.07 秒、约 7.1 米）分段接近。它作为无伤害能力经 BT→GAS→CMC 执行，方向由原生 Focus 决定，每次保留完整轨迹，移除本 Boss 的 MoveTo 分支；不为 AI 伪造玩家输入请求。

## 交付范围

1. 按真实片段梳理可用技能、移动、待机、防御／反击、阶段／演出、死亡等用途，逐个说明已组装、辅助片段、缺配对或缺来源不启用。不按 AS／BS／Loop 名称机械拼招。
2. Kevin 的顶层行为、阶段策略、选招／连招组合、具体技能流程和表现由蓝图、BT、Montage、Niagara、材质图和数据资产完成；C++ 只提供通用机制和接口。BossAI 经既有 GAS 入口选招，形成真实的战斗循环，不停在测试脚本直接激活。
3. 按真实动作定前摇、有效段、收招和可中断点。Animation 管姿态和窗口，CMC 唯一执行胶囊位移；导出根轨迹与派生原地动画匹配，避免双重位移。远程、范围、召唤、投技不一律伪装成近战扫掠。
4. Combat 查询和去重，GA／GE／Execution／AttributeSet 结算。正常结束、取消、死亡和目标失效时归还本技能资源。
5. 每个启用的技能有适配动画的特效和声音；特效有统一的 Boss 视觉语言、危险提示和强弱层次，保留真实挂点、朝向、Follow／Stop 和清理语义。
6. 音效接挥击、命中、蓄力／爆发、循环、脚步等。没有原调用时点或原声时标"未知／候选"，不把替代声冒称原版；缺口只阻塞对应声音。
7. 在独立场景 `/Game/Map/BH3/L_KevinBoss_P3` 通过正式 Encounter 入口制作可交战场景：有玩家目标、血量、命中，Boss 正常结束和死亡后清理干净。不改其他地图和用户未保存的关卡。

## 方案要点与约束

- 多段地空轨迹按完整技能保留，不把各段独立当落地技能，也不静默清零 Z。飞行段用 CMC 的 `AcquireFlyingMovementMode`／`ReleaseFlyingMovementMode` 借用和归还 Flying 模式，原曲线结束后交给 CMC 原生重力，等真实 Landed 再回地面池或播落地表现；不固定下降速度，不伪造落地。`LandingRecovery` Montage（Main 2.45 s，Impact 0～0.35 s）只作表现，不代替真实 Landed。
- Kevin Pawn 已继承共享 `/Game/BP/Character/BP_BossCharacter`，保存及独立读回通过，消费已交付的死亡结束蓝图处理（下一帧 `K2_HandleDeathFinished` → `UninitAndDestroy` → true）；不复制原生自动销毁分支。正式战斗已验证死亡结束、Avatar 销毁及销毁后 5 秒无本技能资源残留。
- 共享 Kevin Skeleton／ABP／Montage 只能有一个写入者，串行制作；特效、音效、动画、GA、BT 包互不冲突的可以并行。
- 制作脚本和配置：
  - 特效：`AAADocs/Scripts/build_bh3_kevin_fx.py`，配置 `AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_FX_Config.json`（22 个 NS、8 个材质、13 个命中 Cue，共 43 包）。
  - 音效：`AAADocs/Scripts/build_bh3_kevin_audio.py`、`plan_bh3_kevin_audio.py`，配置 `BH3_Kevin_Audio_Config.json`，标签 `Config/Tags/BH3_Kevin_AudioTags.ini`。
  - 动画：`AAADocs/Scripts/build_kevin_skill_animation.py`，Editor 源 `KevinMotionAssetBuilder.cpp`、`KevinCombatAssetBuilder.cpp`、`KevinBossAnimBlueprintAuthor.*`，标签 `Config/Tags/KevinBossAnimationTags.ini`。
  - GA／AI：`AAADocs/Scripts/wire_kevin_boss_abilities.py`、`wire_bh3_kevin_combat.py`，Editor 源 `GGYGOBossAbilityGraphLibrary.*`、`GGYGOBossCombatAssetLibrary.*`，配置 `BH3_Kevin_Ability_Config.json`，标签 `Config/Tags/KevinBossTags.ini`。
  - 场景：`AAADocs/Scripts/configure_kevin_boss_p3.py`，配置 `BH3_Kevin_P3_Scene_Config.json`，`Config/DefaultEngine.ini` 的 KevinBoss 导航 Agent（半径 60、高 250，Default 保持第 0 项）。
- 资料入口：[导入核对](../Assets/BH3/BH3_Kevin_DemonBattle_Import.md)、[动作与职责契约](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Implementation.md)、[动作清单](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Action_Manifest.json)、[制作配置](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Wiring_Config.json)、[原验证入口](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Runtime_Verification.md)。

## 当前状态

- **FX 资产**：新增 22 个 Niagara 系统和 13 个命中 Cue，复用 8 个材质；43 包独立读回、引用和编译就绪通过。证据：`Saved/Codex/KevinBossAssembly_20261111/FX_Read_Ready/editor.log`。已保存 55 个声音包只读复用；参考／原创区别见下表。
- **动画资产**：26 份派生动画（含 Fly_Loop 末帧全身静止姿态）、ABP、19 个技能 Montage 与 5 个表现 Montage 已保存。原生轨迹、姿态、窗口和声音引用独立读回及两项作者图／输出保护回归通过，证据：`Animation_Read/editor.log`。
- **GA／AI 资产**：3 份共享模板、16 个动作子类、死亡 GA、初始化和冷却 GE 共 37 包，及 Pawn／State／BTS／BB／BT／Definition／PawnData／AbilitySet／两阶段动作池共 10 包已保存，独立读回通过（`DashF_Read/editor.log`，47 包）。包括无伤害 Dash_F、两阶段授予和动作池；该 BT 已移除 MoveTo 分支，动作流程仍由共享蓝图管理。
- **源码与测试**：BossAI、Boss GA、Combat、CMC 飞行和 Editor 制作接口已编译；15 项 BossAI、范围／弹体查询、ActionMotion TimingAndOwnership 及两项动画回归通过。Controller 恢复原生 AAIController Tick，使 BT Focus→ControlRotation→CMC 转向继续执行；跨引擎帧两次换向的 NativeFocusRotation 回归通过。证据：`Battle_R1/editor.log`、`Battle_R2/editor.log`、`Focus_Standalone/editor.log`；最新增量构建：`Build_DashF/build.log`。
- **P3 场景**：已保存并独立读回；唯一主灯带 GGYGO.KeyLight，双方间距 18 m，KevinBoss 导航的实际投影和完整路径、9 个空中净空采样通过。未修改原支撑碰撞。证据：`Scene_Create_NavExport/editor.log`、`Scene_Read/editor.log`。
- **正式战斗**：`Battle_R6/editor.log` 同场覆盖 11 个攻击选招入口、两条 AirChain 原生重力落地、50% 阶段切换、死亡结束及销毁后 5 秒无残留；玩家以真实普攻击败 Boss，结束剩余 2 HP。录得 15 种 Kevin 声音实例和 237 秒 Master WAV。该轮普通追击仍被 CMC 拒绝，玩家主动靠近才交战；修复后追击单独由 R7 验证，清晰取景由 R9 及火系／空中隔离复拍补齐，不把不同轮次合称一次完整胜利。

以上相对日志路径位于 `Saved/Codex/KevinBossAssembly_20261111/`。[运行验证](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Runtime_Verification.md) 记录入口、结果和未覆盖边界。

## 追击、画面与评审收尾

1. **普通追击已通过**：Dash_F 无伤害能力、两阶段池和不含 MoveTo 的 BT 已编译、保存并独立读回。`Battle_R7_DashF/editor.log` 中玩家静止，Boss 前两段水平位移各约 711.145 cm，与原片段约 711.144 cm 对应，距离 18 m→10.89 m→3.78 m；双方生命不变，随后进入正式攻击。该轮共 11 次 Dash_F，无旧 CMC 请求拒绝；玩家约 65 秒死亡，Boss 正常取消。R6 的旧拒绝保留，不冒充当时已有追击。声音复用同 Boss 闪避候选 E3188014124，原版映射与时点仍未证实。
2. **视听复验**：R8 俯视图确认 IceWarning 平面竖起、被地面截成半圆。原生 Python 读回证实配方 Pitch／Yaw／Roll 被传入了 Roll／Pitch／Yaw 位置参数；改具名构造后保存 9 个实际变化的子蓝图，37 包独立读回通过（`Rotation_Create`／`Rotation_Read/editor.log`）。正式场景的水平预警圆与地面破环已看图确认（`Battle_R9_Visual/027_NS_Kevin_IceWarning_14030df00bfc_030.png`、`030_NS_Kevin_IceGroundBreak_c6025809cf08.png`）。火系／空中由 `Visual_Fire_Air/editor.log` 补拍：五个既有能力均完成，52 张 viewport 读回、13 种声音实例；已看图确认水平火环、刀光、蓄力、空中聚集、冰火爆发及冰弹体。该轮暂停 BT 后走既有 GAS 入口，仅用于受影响表现与真实落地复验，不替代正式自动选招或完整交战。原失败图保留；诊断战斗玩家阵亡，不补签完整胜利。
3. **核心差分评审**：Movement 的 Flying 接口无阻塞。Combat 发现同 Actor 的 Touch→Block 被伤害去重吞掉，改为独立输出物理阻挡，弹体据此销毁，伤害仍按 Actor 去重；补同段和跨段回归。两处本批制作／读回工具及结果结构迁入 GGYGOEditor，内容包未查到旧类型序列化引用，不保留无消费者的运行时兼容。`Build_ReviewFix/build.log` 编译成功；`Review_Query/editor.log` 两项通过；`Review_Editor_Read/editor.log` 四个 Editor 类型绑定和 GA／AI 47 包、FX 43 包独立只读回通过。

## 验收标准

### 特效参考与创作对照

本次已查看原导出的武器贴图 `Monster_Boss_411_Texture_Weapon_Color.png` 和翼膜贴图 `Monster_Boss_411_Texture_Body_Wings_Blue_Color.png`（完整路径见 FX 配置的 `references`）。贴图能证明配色和轮廓，不能证明原游戏粒子、触发时点或战斗画面。下表对应配置中的全部 22 个系统；粒子、材质形状、数量、速度和寿命均为项目创作，启用技能的主要效果已在正式场景或专项画面核对；全部 22 个系统是制作清单，不等于全部进入当前战斗池或全部取得运行画面，未启用的防御、领域等效果只签资产读回。

| 系统 | 参考事实 | 项目创作与改编 |
| --- | --- | --- |
| IceWeaponTrail／FireWeaponTrail | 武器青蓝冰刃、橙黄火刃配色 | 武器世界空间 Ribbon；火刃增加短条粒子 |
| IceCharge／FireCharge | 同上配色 | 碎片／火条与光晕组合成蓄力层 |
| IceStrike／FireStrike | 同上配色 | 短促碎片／火条爆发及光晕 |
| IceWarning／FireWarning | 仅借用冰火配色 | 原创低亮地面提示；圆、扇区和线形尺寸消费实际判定几何 |
| IceGroundBreak／FireGroundBreak | 仅借用冰火配色 | 原创破环地面形状与向外碎片／火条 |
| IceDomain／FireDomain | 仅借用冰火配色 | 原创低遮挡持续破环，边缘清楚、中心留空 |
| WingGuard／GuardBreak | 翼膜青白、尖角和破碎轮廓 | 防御持续碎片及破防爆发；强度和时序为项目设计 |
| IceDashWake／FireDashWake | 武器冰火配色 | 原创移动尾迹碎片／火条 |
| AerialGather | 翼膜青白和细长尖角 | 原创空中聚集碎片 |
| IceHitImpact／FireHitImpact | 武器冰火配色 | 原创命中短爆发；13 个 Cue 引用对应效果和既有 SoundCue，使用真实命中参数 |
| IceProjectile | 冰刃配色与锐利轮廓 | 原创碎片弹体和 Ribbon 尾迹；移动与生命周期由实际 Projectile／GA 管理 |
| FireWingGuard | 翼膜尖角；火刃配色 | 两类参考的原创组合，无原版火翼防御效果证据 |
| DeathDissipate | 无直接原效果来源 | 原创中性青灰碎片消散 |

### 分项通过条件

- 特效：35 个包落盘，Niagara 编译无错，读回引用正确；对照表区分参考改编和原创。
- 动画：包落盘并编译，Montage 窗口和标签读回正确，派生动画根位移为 0 且与原轨迹对应。
- GA 与 AI：37 包落盘编译通过；模板图的事件和关键连线读回正确；Definition 的阶段池和授予引用正确。
- 场景：P3 保存后 NavMesh 覆盖战斗区，PlayerStart 和 Encounter 引用正确，其他地图没改。
- 实战：Boss 能完成至少一次完整战斗循环到死亡，两阶段切换可见，主要技能有画面和声音证据，死亡后没有残留。

## 交付文件与共享边界

源码提交：[完成 Kevin Boss 原生资源接口与单机战斗支撑](https://github.com/WuDuElysia/GGYGO_Source/commit/7b6742c)。Obsidian 提交：[同步 Kevin 战斗及跨模块接口](https://github.com/WuDuElysia/Lyra_Learn_note/commit/5fa4f68)。构建和运行基于完整工作树；统筹只在多线交付后做一轮受影响集成，不把这些结果声称为干净 HEAD 的独立验证。

共享文件的本需求边界：

- `Character/Components/GGYGOCharacterMovementComponent.h/.cpp` 的现有未提交差分均是本批 Flying 借还；已随子仓提交。
- `Character/Components/GGYGOActionMotionExecution.cpp` 只提交 `IsMontageActionMovementModeSupported` 增加 Flying，以及两处对应准入／运行诊断。网络取消、中性化和自然混出末段差分保留给 AbilitySystem；`GGYGOActionCurveRootMotionSource.h/.cpp` 本次完全不提交。
- `GGYGOProjectedDecalRendererProperties.h/.cpp` 的本批材质读回接口与结果结构已完整迁到 `GGYGOEditor/GGYGOMaterialAuthorLibrary`，当前 Rendering 文件的 FX 初始化差分未提交。未迁历史作者接口。
- `Blueprint_Layering_Audit.md` 只更新 Q01 及其摘要。用户的 `Module_Repair_04_Subleases.md`、Pyrios／Test 资产、AS／FX 制作及网络差分均保留。

父工程精确文件（不含其它工作线看板改动）：

```text
AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Ability_Config.json
AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Audio_Config.json
AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Action_Manifest.json
AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Montage_Config.json
AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Runtime_Verification.md
AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Wiring_Config.json
AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_FX_Config.json
AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_P3_Scene_Config.json
AAADocs/Coordination/Blueprint_Layering_Audit.md
AAADocs/Scripts/audit_kevin_action_motion.py
AAADocs/Scripts/audit_kevin_skill_poses.py
AAADocs/Scripts/build_bh3_kevin_audio.py
AAADocs/Scripts/build_bh3_kevin_fx.py
AAADocs/Scripts/build_kevin_skill_animation.py
AAADocs/Scripts/configure_kevin_boss_p3.py
AAADocs/Scripts/plan_bh3_kevin_audio.py
AAADocs/Scripts/wire_bh3_kevin_combat.py
AAADocs/Scripts/wire_kevin_boss_abilities.py
AAADocs/需求文档/kevin_boss_assembly.md
Config/DefaultEngine.ini
Config/DefaultGame.ini
Config/Tags/BH3_Kevin_AudioTags.ini
Config/Tags/KevinBossAnimationTags.ini
Config/Tags/KevinBossTags.ini
Content/Map/BH3/L_KevinBoss_P3.umap
Source/GGYGO
Source/GGYGOEditor/GGYGOEditor.Build.cs
Source/GGYGOEditor/Private/GGYGOBossAbilityAssetConfiguration.cpp
Source/GGYGOEditor/Private/GGYGOBossAbilityGraphLibrary.cpp
Source/GGYGOEditor/Private/GGYGOBossCombatAssetLibrary.cpp
Source/GGYGOEditor/Private/GGYGOMaterialAuthorLibrary.cpp
Source/GGYGOEditor/Private/KevinBossAnimBlueprintAuthor.cpp
Source/GGYGOEditor/Private/KevinBossAnimBlueprintAuthor.h
Source/GGYGOEditor/Private/KevinCombatAssetBuilder.cpp
Source/GGYGOEditor/Private/KevinMotionAssetBuilder.cpp
Source/GGYGOEditor/Public/GGYGOBossAbilityAssetConfiguration.h
Source/GGYGOEditor/Public/GGYGOBossAbilityGraphLibrary.h
Source/GGYGOEditor/Public/GGYGOBossCombatAssetLibrary.h
Source/GGYGOEditor/Public/GGYGOMaterialAuthorLibrary.h
```

Source/GGYGO 子仓精确文件：

```text
AI/Boss/Abilities/GGYGOBossAttackAbility.cpp
AI/Boss/Abilities/GGYGOBossAttackAbility.h
AI/Boss/Abilities/GGYGOBossAudioActor.cpp
AI/Boss/Abilities/GGYGOBossAudioActor.h
AI/Boss/Abilities/GGYGOBossDeathAbility.cpp
AI/Boss/Abilities/GGYGOBossDeathAbility.h
AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp
AI/Boss/Abilities/GGYGOBossMeleeAbility.h
AI/Boss/Abilities/GGYGOBossProjectile.cpp
AI/Boss/Abilities/GGYGOBossProjectile.h
AI/Boss/GGYGOBossAIController.cpp
AI/Boss/GGYGOBossAIController.h
AI/Boss/GGYGOBossCharacter.cpp
AI/Boss/GGYGOBossCharacter.h
AI/Boss/GGYGOBossDefinition.cpp
AI/Boss/GGYGOBossDefinition.h
AI/Boss/GGYGOBossEncounter.cpp
AI/Boss/GGYGOBossState.cpp
AI/Boss/GGYGOBossState.h
AI/Boss/Tests/GGYGOBossCombatDecisionTest.cpp
AI/Boss/Tests/GGYGOBossEncounterBehaviorTreeTest.cpp
AI/Boss/Tests/GGYGOBossMeleeEndReentryTest.cpp
AI/Boss/Tests/GGYGOBossProjectileTest.cpp
Character/Components/GGYGOActionMotionExecution.cpp
Character/Components/GGYGOCharacterMovementComponent.cpp
Character/Components/GGYGOCharacterMovementComponent.h
Combat/HitDetection/GGYGOCombatHitQuery.cpp
Combat/HitDetection/GGYGOCombatHitQuery.h
Combat/Tests/GGYGOCombatHitQueryTest.cpp
```

Obsidian 精确文件（相对 `F:/Obsidian/Doc/lyra学习笔记`）：

```text
GGYGO架构规划/Animation/GGYGO_流程_Kevin战斗动画.canvas
GGYGO架构规划/Animation/Kevin战斗动画实施.md
GGYGO架构规划/Audio/结构.md
GGYGO架构规划/BossAI/GGYGO_流程_BossAI.canvas
GGYGO架构规划/BossAI/GGYGO_流程_Boss选招.canvas
GGYGO架构规划/BossAI/GGYGO_结构_BossAI.canvas
GGYGO架构规划/BossAI/结构.md
GGYGO架构规划/BossAI/计划_Kevin_DemonBattle战斗接入.md
GGYGO架构规划/Combat/GGYGO_流程_Combat.canvas
GGYGO架构规划/Combat/GGYGO_结构_Combat.canvas
GGYGO架构规划/Combat/结构.md
GGYGO架构规划/Movement/GGYGO_流程_移动与位移.canvas
GGYGO架构规划/Movement/GGYGO_结构_移动与位移.canvas
GGYGO架构规划/Movement/结构.md
```

Obsidian 的 JSON、ID、边端点、新节点无重叠及改动链接已核对；保留既有节点布局，未做原生 Obsidian 渲染验收。

### 本地忽略资产

- `Content/Characters/Boss/Kevin/DemonBattle/`：Mesh／Skeleton、原序列、派生动画与 Montage／ABP、声音、FX、GA／GE、Blueprints／Data；包含本次保存并独立读回的制作产物及原导入依赖。
- `Content/Environments/BH3/Stage/Stage_KevinBoss_P3/`：已导入 P3 场景的网格／材质／贴图依赖。
- 上述目录继续按现有 `.gitignore` 留在本机，没有强制加入 Git 或放开忽略规则；已跟踪的 P3 地图随父工程提交。外部新 checkout 仍须具备这些本地导入素材，不能仅靠 Git 还原完整运行环境。
- 取证脚本、日志、PNG 和 Master WAV 在 `Saved/Codex/KevinBossAssembly_20261111/`，仅本机保留。
