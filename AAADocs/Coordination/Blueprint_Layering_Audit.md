# 全项目蓝图与 C++ 分层审查

任务：BLA-20261105-01。唯一报告／活动入口：本页。统筹：`01a1347b-ccee-7081-a783-0c3127b3dd48`；审查：`01a1aa9d-f20e-7092-8741-87890a6f1049`。

**2026-11-11：B06、B08 已验证完成；Q01～Q05 资产读回已完成，未新增确认分层问题。Kevin 的运行边界随原需求继续；本次读图不补签运行、视听或联机验收。**

**第二轮实质复审完成：当前确认 2 项分层问题（B06、B08）；其余 7 项当前没有必须继续迁出 C++ 的依据，B04 旧命中撤回。** Kevin 制作链已沿最新接口重读，交回版本已消除期间读到的旧调用／旧字段差异，不留作未完成整改。Q01～Q05 是资产图／运行证据边界，不是另外五项确认违规。

2026-11-05 的第二轮源码复审沿 B01～B09、Q01～Q05 和 Kevin 新增改动的必要依赖，追读激活、调用、事件、作者配置和清理链，当时未启动 UE。2026-11-11 另以隔离 NullRHI Editor 补齐下方 Q02～Q05 的保存资产读回，只写审查文档和自有 Saved 证据；没有修改源码或资产、重做第一轮 603 件清点、运行游戏或重测 B06／B08。本报告不授其它任务写权。

## 判定与当前状态

依据当前 [AGENTS.md](../../AGENTS.md) 架构条款和 [CodeConventions](../Architecture/CodeConventions.md) 的蓝图与 C++ 分层。允许“通用机制＋共享蓝图流程＋对象资产配置”；简单变体可仅配子蓝图／CDO／DA。只有定位仍固定于原生的具体业务分支、组合或时序，才确认归属问题；角色名、数字、原生算法／状态机、未暴露覆写口和缺完整图均不能单独确认违规。

这是作者不停工期间的逐文件读版本，末节记录身份，**不是冻结工程的原子快照**。源码、生产接线、编译、保存、运行和联机分别判断。没有从工具读到图，不等于资产没有图；制作代码能生成图，也不等于生产图已制作、保存或运行。

| 当前分类 | 编号 | 可据此安排的动作 |
| --- | --- | --- |
| 确认必须调整的分层位置 | B06、B08 | **已验证完成（2026-11-11）**：两项都已迁到共享蓝图并在真实运行中通过，见各节关闭记录和[蓝图分层收尾](../需求文档/blueprint_layering_followups.md)。 |
| 当前不用强制迁移／撤回 | B01、B02、B03、B04、B05、B07、B09 | 撤销按旧编号整体迁出的建议；实际资产接线仍按 Q 项核，不预建接口或第二套状态机。 |
| 资产读回已完成 | Q01～Q05 | 已读当前保存图、CDO 和直接引用。Q01 由 Kevin 原负责人完成制作后独立读回；未新增对象业务固定在 C++ 的具体问题。运行未覆盖见下文。 |
| 单机运行已验 | Q01 运行边界 | Kevin 正式地面／飞行／死亡、完整追击及主要画面已有运行证据；联机、Cook 和设备试听未验，详见原需求。 |

## 当前确认必须改的两个批次

### B06：完整改键页面和页面业务仍固定在原生

**当前证据与场景。** `Source/GGYGO/Input/GGYGOKeyBindingMenu.cpp:77` 的 Construct 在 `:91` 起创建完整页面，固定尺寸、标题、提示和按钮；`:154` 起安排排序及行布局；`:214`、`:257`、`:275`、`:288` 编排选键反馈、恢复默认、关闭和 Escape。`Source/GGYGO/Player/GGYGOPlayerController.cpp:471` 的 OpenKeySettings 在 `:486` 固定 `SNew(SGGYGOKeyBindingMenu)`，`:493` 起加 Viewport／切 UI 输入与光标；`:500` 关闭后切回 GameOnly。当前调用链没有配置共享 Widget 类表达这套页面业务。玩家打开页面或修改结构／反馈，必须改 C++；这是表现层业务归属问题，未声称已复现运行错误。

**最小批次／原作者。** Input 原组长（`01a0e5b5-276c-7ea0-b469-4797f5059e2b`）牵头，Controller 消费改动由统筹指定所属原作者。范围只含当前菜单及必要公开桥、`GGYGOPlayerController.h/.cpp` 的菜单入口、`/Game/BP/GamePlay/BP_PlayerController` 消费的共享页面资产。用一份可编辑 UMG／共享蓝图承载布局、行呈现、反馈与页面流程，C++ 留数据操作、必要原生控件桥和资源清理；样式／映射集合只配数据。不顺手改键位、冲突规则、输入模式语义或技能输入，不要求每个菜单实例独立 EventGraph。

**必须保留。** EnhancedInput UserSettings 的真实读写、ApplySettings／AsyncSaveSettings（菜单 `:298`）、映射重建、LocalPlayer 身份与菜单资源释放。尤其 `:29`～`:65` 的原始同栈 KeyUp 传递及 `:281` 的 BeginKeyBindingMenuClose 所依赖的释放认证／held barrier 是底层机制；不得用 BP 合成事件冒充实际 KeyUp 或因迁页面删除保护。

**关闭条件。** 生产入口实际消费共享页面，布局／反馈可在资产编辑。集中验收只补原场景：改键、冲突反馈、恢复默认、关闭／Escape、保存后重载；按住键穿越菜单、选键时真实释放与关页后的输入恢复；Controller／LocalPlayer 结束时归还页面和原输入资源。保留当前行为。

**状态：已验证完成（2026-11-11）。** 生产 `BP_PlayerController` 使用共享页面 `WBP_KeySettings`／`WBP_KeySettingsRow`；在真实 Windows 前台的两轮 PIE 中走通上述全部场景：冲突提示、选键 Escape 取消、页面 Escape 关闭、W→I 改键生效、存档写出并在新会话读回、恢复默认、按住键穿过菜单后不残留移动、PIE 结束时页面退役。实体键鼠和跨进程读回没有覆盖。证据见 [I03 证据](../../.agents/tasks/requirements-closeout/evidence/I03.md)。

### B08：原生死亡回调固定发起自动替补

**当前证据与场景。** `Source/GGYGO/Teams/GGYGOSquadComponent.cpp:451` 订阅 OnDeathFinished；`:791` 的 HandleMemberDeathFinished 在权限／终止检查（`:794`）和当前出战 Avatar 认证（`:795`～`:796`）后，`:798` 直接 `SwitchToAdjacentSlot(1, DeathAutoSwitch)`。上层未传入替补请求，原生直接决定“当前成员死亡后立即向后替补”的玩法流程。应由一份共享队伍／PlayerState 蓝图消费带原 Slot／Avatar 身份的事实，并等价请求现有下一个可出战成员；不改变同步时机、方向、来源分类或已确认行为。

**最小批次／原作者。** Teams 原组长（`01a0e5b5-910c-71e3-a75c-b17c22fea33e`）牵头，范围限 `GGYGOSquadComponent.h/.cpp` 的事实通知／必要公开请求和实际承载 Squad 的共享业务蓝图。`Source/GGYGO/Player/GGYGOPlayerState.cpp:14` 创建 SquadComponent，`.h:30` 公开 GetSquadComponent；复用此所有权，不建第二宿主。若需调整实际生产 PlayerState 类的共享 BP 配置，由统筹交原作者。现有 Next／Previous BP 入口使用 Script 来源，不能直接冒充 DeathAutoSwitch；保留能表达原来源的最小公开请求。

**必须保留。** 服务器权限、原 Avatar／Slot 认证、死亡广播同栈时序、`:806`～`:831` 的候选查询、切换准入、来源／冷却、Layout／Possess／RPC／复制和 GA 清理归原机制。`:830` 真实切换失败后不换候选重试；无候选保留失败／诊断，不假成功。`:697` 的 Lingering／Exiting／ReturnPending 与首名免重复入场含合法生命周期约束，不在本项整体迁移；不搬整个 Squad 状态机。

**关闭条件。** Native 回调只认证／发布事实，生产共享图发原 DeathAutoSwitch 请求；当前出战死亡仍选下一个存活成员、后台死亡不切换、无人存活不假成功。集中最小验证这三种场景及现有权威／复制链，核销毁前同步交接与 PlayerRequest／Script／DeathAutoSwitch 区分。

**状态：已验证完成。** `UGGYGOSquadComponent` 只认证并广播 `OnActiveMemberDeathFinished(Slot, Avatar)`；共享 `BP_PlayerState` 在同一次广播里调用 `RequestNextAfterActiveMemberDeath`，来源仍是 DeathAutoSwitch，每次死亡最多请求一次，没有请求被消费时报 Error。`BP_GameMode` 使用该 PlayerState。集中真实 RHI 运行中，联机死亡自动换人、后台死亡不切换、无人存活不假成功三类断言通过（[集中 RHI 回执](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Integrated_R1/return.json)）；2026-11-11 角色阴影修复后的联机回归里 SquadSwitch 8 例也全部通过。

## 当前不用改／撤回及实际源码依据

### B01：通用候选过滤、权重更新和抽签可保留

重新核了 `Source/GGYGO/AI/Boss/BehaviorTree/BTTask_GGYGOChooseBossAction.cpp:91` 起标签／距离／朝向／LOS 过滤、`:141` GAS 准入和 `:173` SelectAction；`GGYGOBossAIController.cpp:260` 更新权重、`:303` 通用抽签。`GGYGOBossActionSet.h:24`、`:44`、`:47`、`:50` 由作者配 BaseWeight／RepeatPenalty／UnusedWeightGain／MaxWeight，阶段提供候选 ActionSet。本链未定位本轮可确认的 Kevin 专属选招条件硬编码，撤回整体搬通用算法或每招建 Task 的要求。

旧阶段／目标命中不恢复：`GGYGOBossState.cpp:118`、`:140` 发布血量事实，`:122` 权威 SetCurrentPhase；`GGYGOBossDefinition.h:85`／`:97` 指定 StateClass／CombatTargetService，`GGYGOBossEncounter.cpp:138` 消费 StateClass。`Source/GGYGOEditor/Private/GGYGOBossCombatAssetLibrary.cpp:166` 起创建 State／BTS 图（Health 事件 `:183`、阶段提交 `:215`、目标查询／提交 `:252`／`:254`），`:325` 起制 BT、`:349` 挂配置 Service。这是 Editor 图作者，不是运行时第二套原生阶段调度。已保存图／运行树按 Q01 核。

### B02：实际连段关系来自资产，原生是通用消费

重读 `Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp:865` 激活及 `:1966` 原 Step 请求消费；`:1992` 首段从 0 开始，`:1993` 后续读取 ComboSteps 的 NextStepIndex。`GGYGOComboTypes.h:37`～`:56` 配 Montage／Section／NextStepIndex，后续配作者 Notify／窗口。没有本轮确认的角色／招式特化组合隐藏在这些入口。

2026-11-11 直接读取 `GA_Pyrios_Attack_Combo` 的 ComboSteps 和 EventGraph：三段 NextStepIndex 为 1／2／0，Montage 为 Normal01／02／03；两枚默认事件节点均 Disabled，实际使用通用原生消费链。对象配置三段不代表机制写死三段。撤回因消费配置表／数据子类或 StartStep 未暴露 BP 而要求新增图／接口的建议；输入身份、预测、窗口和清理保留。详见 Q05。

### B03：目标、范围基准和正常完成策略已由 BP 显式提供

当前 `Source/GGYGO/AI/Boss/Abilities/GGYGOBossAttackAbility.cpp:160`～`:184` 捕获原资源后调用 PrepareBossAction，不原生自动选 Controller 目标；BP 通过 `BindBossTarget`（`:634`）显式绑定。`:231` 通知 BossHitWindow，`:235` 的 ExecuteBossWindow 接收 AreaBasis／ProjectileAimPoint，`:274` 只计算传入瞄准点的方向、`:300` 消费传入范围基准。目标死亡／EndPlay（`:371`／`:380`）、控制权变更（`:502`）和 Montage 完成（`:519`）回调 BP，不在这些点固定正常业务结束。

`GGYGOBossAbilityGraphLibrary.cpp:180`～`:207` 实际创建 Prepare→取 Controller 目标→Bind、HitWindow→显式几何→Execute、失效策略，以及地面完成或飞行归还→真实 Landed→收尾→结束的共享图。飞行句柄、超时失败、落地认证、原 Task、查询／去重／伤害、音频窗和清理应留底层。当前不要求整体迁走这些机制。实际模板／引用按 Q01 核。

### B04：旧“timer 原生自动正常完成”命中撤回

最新 `Source/GGYGO/AI/Boss/Abilities/GGYGOBossDeathAbility.cpp:31`～`:44` 要求实际 PrepareBossDeath BP 实现并调用它。`:65` 等待接口须由 BP 请求，到时 `:77` **只回调 BossDeathPresentationFinished**；timer 不自动正常 End。`:82` 的 FinishBossDeath 由 BP 显式请求结束，`:95`～`:106` 归还本次实际取得的 Health 义务是原生命周期清理。

`GGYGOBossAbilityGraphLibrary.cpp:210`～`:231` 当前制作／核验共享死亡图：取消其它动作→StartDeath→配置时长等待→BP 完成事件→FinishBossDeath。无需再为旧命中搬 timer／Health 清理。资产保存、动画显示及正常／中止结果仍未验证，不能将撤回源码命中写成死亡验收完成。

### B05：保留数据驱动的通用镜头计算／所有权

`Source/GGYGO/Camera/GGYGOCameraMode_ThirdPerson.cpp:137` 消费曲线／幅度／步态增益求侧移，`:197` 按配置插值；`.h:41`～`:82` 暴露启用、曲线、增益和进退速度。`Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp:355`～`:365` 仲裁能力覆盖和 PawnData 默认模式。本链未定位对象演出条件／具体招式时序固定在这些数学函数；不因原生 UpdateView／缺每对象覆写图而要求迁移。实际选择链按 Q04 核。

### B07：保留 CMC 通用步态、起停和 TurnBack 执行

重核 `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:3949` ResolveGait、`:4004` WalkToRunHoldSeconds、`:4235` TurnBack 执行、`:4283` Locomotion 更新及 `:4407` StartStopSelectionSeconds。参数来自 `Character/Data/GGYGOMovementSet.h:51`／`:59` 等，与 SavedMove／原生模拟／曲线阶段耦合。本轮未定位具体角色／技能新增分支需要移出，撤回整体迁移走跑／起停 FSM 的建议。胶囊、预测／重放、Yaw、曲线区间和真实完成／失败仍归 CMC；动画消费按 Q03 核，不另建 BP 移动权威。

### B09：StopValue 可按稳定模板输入适配保留

`Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionRules.cpp:10` 将 StopMotionType 转 0／1／2，`ZZZLocomotionEvents.cpp:29` 发布 StopValue。本轮未发现具体对象新增候选、组合／时序藏在转换中；数字和 ABP_Pyrios 注释不足以要求删除／迁移。当前不用改该适配、ZZZ 基类、Slot／BodyLean 或已验 CMC；实际 Stop 图按 Q03 核，发现真实特化后再凭具体分支处理，不预建泛化层。

### Kevin 制作接口差异：交回前已消除，不留整改

期间确实读到过旧脚本与新 Native 签名不一致；最新 `AAADocs/Scripts/wire_kevin_boss_abilities.py:178`～`:194` 已先制作／校验 ground、flight、death 三份共享抽象模板，`:190` 按当前 `(Blueprint, bFlightLanding)` 调用动作图接口；`:223`～`:224` 让 15 招继承对应共享模板；`:269`～`:273` 填 LandingTimeoutSeconds／LandingRecoveryMontage／RecoveryPlayRate／RecoveryFX；`:274`～`:276` 已不写退役 bAreaAtTarget；`:288` 死亡子类继承 death 模板，配置 templates 与之对应。

因此旧参数调用、退役字段、落地配置漏消费和死亡模板漏消费不计当前缺陷；不要求每招独立图。这里只确认本轮所查接口静态对齐，**未执行 Python／反射调用、编译 BP 或验证整个制作链通过**。

## Q01～Q05：资产读回结论与剩余边界

| 编号 | 本轮事实与未知边界 | 最小证据／关闭条件 |
| --- | --- | --- |
| Q01 Kevin State／BTS／BT／GA | **资产读回完成。** 3 份共享模板、16 个动作子类、死亡 GA、初始化及冷却 GE 共 37 包，及 10 个 Pawn／AI 配套包已保存。独立 Editor 验证共享图关键连线、子类 CDO、实际阶段图、BT 和授予引用；Kevin Pawn 继承共享死亡处理蓝图。无伤害 Dash_F 复用地面模板与原 Montage，阶段池选招，BT 不含 MoveTo。 | 证据：`Saved/Codex/KevinBossAssembly_20261111/DashF_Read/editor.log`（47 包）。正式战斗已覆盖 11 个攻击入口、两条 AirChain 真实落地、阶段切换与死亡清理；完整 Dash_F 追击和受影响冰火／空中画面复验已通过；两处纯制作／读回工具迁入 GGYGOEditor 后绑定及 47＋43 包独立读回通过。Kevin 联机、Cook、设备试听未验，见 [原需求](../需求文档/kevin_boss_assembly.md)；不要求子类复制图。 |
| Q02 玩家 Death／SquadTransition | **只读审查关闭。** 已读默认 Experience、PawnData 授予、Death CDO／Montage、保存后的共享角色死亡图及正常／中止调用链。未新增分层问题。 | 默认授予链没有 SquadTransition 子类，因此没有可补签的生产过渡 Montage／图。未运行死亡／换人场景，不重复 B08。 |
| Q03 ABP_Pyrios | **只读审查关闭。** Stop 索引、过渡端点及 Getter 绑定、FullBody Slot、BodyLean、显示角和恢复图、对象序列与曲线均有保存图证据。B07／B09 无新增强制迁移依据。 | 不代表起停跳变、倾角、TurnBack 连续性或画面验收通过；这些仍按走跑需求处理。 |
| Q04 Camera | **只读审查关闭。** 默认模式与参数已读，当前授予 GA 没有镜头覆盖；通用覆盖／清理保留原 Hero、Spec 和 generation 所有权。 | 没有实际配置的 GA 演出覆盖图可验，不补签动态覆盖／释放或取景效果。 |
| Q05 Audio／FX／材质 | **只读审查关闭。** 已读普攻及两技能的 Montage 通知、GA 配置、五份命中 Cue、Niagara 作者图／Renderer／材料引用、角色共享材质图和组件模板。未新增分层问题。 | 两特殊技能未在默认 PawnData 授予；其 Montage 只有技能声和 FX 窗，未见命中／连段窗。真实声音、画面、资源就绪和联机表现继续由原需求验收。 |

### 读回范围与证据

入口为 `/Game/BP/GamePlay/BP_GameMode` → `/Game/System/Experiences/DA_Experience_Default` → `/Game/Characters/Player/Pyrios/DA/DA_Pawn_Pyrios`。Experience 的 GameFeaturesToEnable 为空，默认名单只有该 PawnData；这是默认装配配置，不代表地图覆盖、玩家存档编队或运行中额外授予的快照。随后只跟随本项 GA、Montage、Cue、组件和材质直接引用，未扩做历史全库审计。

- [Core/readback.json](../../Saved/Codex/I14_20261111/Core/readback.json)：生产 PawnData、四个已配置能力、角色继承／死亡图、ABP、默认镜头及五份命中 Cue；同目录 T3D 保存对象属性与原生引脚连接。
- [References/readback.json](../../Saved/Codex/I14_20261111/References/readback.json)：默认 Experience、ComboSteps、两特殊技能、六个 Montage 的通知及直接表现引用；同目录 T3D 和 `graph_evidence.json` 保存 Niagara／材质节点与引用。
- [Components/readback.json](../../Saved/Codex/I14_20261111/Components/readback.json)：通过 SubobjectDataSubsystem 读取已有组件模板及扭曲 Profile；不调用会创建继承覆盖的 GetObjectForBlueprint。

各隔离 Editor 均正常退出，读前／读后脏包为空，无保存操作。`ReadStateMachineTransitions` 不支持 Conduit，已用实际 T3D 中的状态端点和 TransitionGraph 引脚补核，未把该辅助接口的失败写成通过。首次组件枚举调用的 Python 接口不存在，原错误留在 References；Components 使用项目现有接口补读。启动日志中的既有 `LogAutomationTest: Error: Condition failed` 也保留；本项没有运行自动化测试，不以 exit0 声称工程无错误。

### Q02：实际死亡与换人配置

`DA_AbilitySet_Pyrios` 当前授予 Combo、共享 Dodge、共享 HitReact、`GA_Pyrios_Death`，没有引用旁边的 `DA_AbilitySet_Common`。Death 继承 `GGYGODeathAbility`，以 `Event.Death` 触发；EventGraph 的 Activate／End 默认节点均 Disabled，无接管连线。CDO 的 DeathMontage 是 `/Game/Characters/Player/Pyrios/Animation/AM_Pyrios_Death`，FullBody 槽、Death Section 引用 `Avatar_Male_Size03_Pyrois_Ani_Death`，无 Notify。

正常完成采用原生通用 Montage Task 的 BlendOut／Completed，Interrupted／Cancelled／Failed 走取消；终止清理消费本次捕获的 Health 并调用 FinishDeath。随后 Character 原生下一帧派发 `K2_HandleDeathFinished`。Character 负责人确认七个目标包已保存后，本项独立读到 `BP_Character`、`BP_HeroCharacter`、`BP_BossCharacter` 三份共享图的 `Entry → UninitAndDestroy → Return true`；`BP_PC_Pyrios`、`BP_Enemy`、`BP_BaseCharacter`、`BP_Boss_Test` 继承对应模板。具体 Pawn 处理已在共享蓝图。

默认授予链未出现 SquadTransition 子类或进退场事件触发器。原生 `GGYGOSquadTransitionAbility` 默认 TransitionMontage=None；其通用 Task 正常 Completed 结束，Interrupted／Cancelled／Failed 取消，缺 Montage 明确诊断并取消。这里只确认现有配置没有该过渡资产，不声称已实现或验证进退场动画，也不据此迁走 Squad 生命周期机制。

### Q03：ABP 的停止、Slot 与侧倾图

`/Game/BP/Anim/ABP_Pyrios` 继承 ZZZAnimInstance。Stop 图将 `StateMemory.StopValue` 接到 Select 索引：0→WalkStartEnd，1→WalkEnd，2→RunEnd，再送 `GetSeqByKey` 和不循环 SequencePlayer。AnimSet 把这些键绑定到 Pyrios 对应的 Walk_Start_End／Walk_End／Run_End；IdleLoop、WalkStart、TurnBack 和 WalkRun BlendSpace 也由资产配置。

NotMoving 在有移动输入时进 Conduit，由 IsAnimationRunGait 分流到 EnterMove／Moving；EnterMove 无输入进 Stop，剩余比例≤0.03 进 Moving。Moving 在无输入且非 TurnBack 曲线驱动时进 Stop；Stop 有输入回 Conduit，剩余比例≤0.5 进 NotMoving。两个剩余时间 Getter 分别确实绑定 EnterMove 和 Stop。Moving 内 WalkRun→TurnBack 条件是曲线驱动且 TurnBack Pose 活跃；返回条件为 Pose 已结束，或既非曲线驱动也非 RunOut。

主状态机输出进入 `GGYGOActionPoseSlot(FullBody)`，经空间转换与 Inertialization 到 Root；槽持续更新 SourcePose。Moving 内子状态机接 BodyLean，LeanDegrees 来自蓝图 `MovingLeanDisplayedAngle`，轴和 Up 来自通用动画事实，Alpha 受表现与输出有效标志共同控制。EnterMovingLean／ExitMovingLean／节点重新相关时清理显示角、步态和原 Motion 上下文；UpdateMovingLean 显式选择 TurnBack 恢复、步态混合或普通恢复。普通恢复用 Tuning.RecoveryResponseSpeed=8 和动画 Delta 做指数衰减；TurnBack 按本次源序列时间读取 MovingLeanRecoveryCurve，再将进入角插值到 0，曲线关键点为 (0,0)、(0.15,1)、(2.383333,1)。步行／跑步角度曲线、序列选择和这些恢复组合都在 ABP／CDO 中，不另建 CMC 权威。

### Q04：默认镜头与覆盖所有权

PawnData.DefaultCameraMode 指向 `/Game/Camera/Modes/BP_CameraMode_ThirdPerson_Pyrios`，父类 GGYGOCameraMode_ThirdPerson；EventGraph 没有节点，是数据变体。当前 FOV=85、TargetOffset=(-350,0,60)、Pitch=-70～70、BlendTime=0.5；WalkRunSteeringOffset 关闭，其曲线和增益虽已配置，不能据此声称运行中启用。

四个默认授予 GA 和额外读取的两特殊技能均为 AbilityCameraMode=None、位置／FOV 偏移为 0。若以后配置覆盖，GGYGOGameplayAbility 在激活准入后应用，Hero 按最新能力覆盖或 PawnData 默认模式选择；统一终止清理以原 Hero、SpecHandle、generation 释放本次模式和偏移，正常与取消共用该清理链。本次未发现藏在原生中的具体招式镜头编排。

### Q05：实际声音、特效、材质与引用

普攻 ComboSteps 为 Normal01→Normal02→Normal03→Normal01；两特殊技能各只有一步，NextStepIndex=-1。它们都继承 GGYGOPlayerComboAbility，没有启用的 Activate／End 接管图。特效系统分别是 Normal01／02 的单个 MainComposition、Normal03 的七个 SystemUnits、Special／ExSpecial 各两个 SystemUnits。系统选择、事件 Tag、附着空间及正常 `DeactivateDetachKeepWorld`／中止 `DestroyImmediately` 均在 CDO；原生 MontageActionResources／Niagara Task 负责窗口认证和资源生命周期。

以下为实际保存的 Montage 时间，单位秒。首帧 PlaySound／FX Begin 的引擎触发时间为 0.0001，作者 LinkValue 为 0；区间终点按通知 EndLink 读取，不把首帧偏移累加成作者时间。

| Montage | FX 窗 | Hit 窗 | Combo 窗 | CancelPoint／MoveCancelPoint 触发时刻 |
| --- | --- | --- | --- | --- |
| Normal01 | 0～1.683333 | 0.066667～0.233333 | 0.266667～1.916667 | 0.275024／1.683233 |
| Normal02 | 0～1.35 | 0.066667～0.25 | 0.283333～1.65 | 0.294345／1.349900 |
| Normal03 | 0～1.4 | 0.333333～0.9 | 0.933333～1.7 | 1.111460／1.399900 |
| Special01 | 0～2.016667 | 无 | 无 | 无 |
| ExSpecial01 | 0～2.35 | 无 | 无 | 无 |

五份 Montage 的 PlaySound 均直连对应 Skill SoundWave 且 bFollow=True，当前没有 SoundCue 混音图参与该引用链；Normal01 音量倍率为 0.354813。五份 `GCN_Pyrios_Hit_*` 由各 Step.HitCueTag 引用，继承通用 HitImpact Cue，空 EventGraph，DefaultEffect 指向各动作 Impact SoundWave，ImpactEffect=None，Burst 音频／粒子为空。声音区分由资产表达；这不证明两特殊技能有命中能力或音色、响度、时点符合原版。

直接读到了 13 个 Niagara 系统的作者节点／引脚、EmitterState／SpawnBurst／ParticleState 等模块及 Mesh／Sprite／Ribbon／ProjectedDecal／SignedField Renderer 配置，并沿 Renderer 材质实例读到父图。例如 Normal01 主弧 Mesh 使用共享 FXMD_DAO 网格和对应材质实例，扭曲支路使用独立 SignedField Renderer、显式材质与 Profile。共享材质中的 Custom 节点、纹理／动态参数输入和输出组合属于可编辑资产图；本项没有验证 GPU 执行或画面。

角色 StylizedRenderComponent 的三个材质槽使用 `MI_Pyrois_Body_1`／`Body_2`／`Weapon01`，共同父图为 `M_Pyrois_Toon`；主 Custom 输出经 Project Toon Composite 和 EyeAdaptationInverse 接 EmissiveColor。轮廓图独立为 `M_Pyrois_Outline`，颜色、背面遮罩和法线挤出分别接 Emissive／OpacityMask／WPO。旧 GGYGOPyriosRenderComponent 只保留序列化兼容类，执行继承通用 GGYGOCharacterRenderComponent。具体受光／资源配置仍由保存的角色蓝图和材质提供。

通过只读 SubobjectDataSubsystem 核对现有及继承组件模板后，`BP_PC_Pyrios` 没有配置 GGYGOLocomotionFXComponent；当前移动表现组件接线仍留在 FX 原需求，不能由攻击 Niagara 的存在推定冲刺／转身特效已接好。

**未覆盖与后续归属。** 本次未做 PIE、真实 RHI、试听、Cook、实体设备或联机测试；未判断原版视听还原、冷首击、活尾和起停跳变通过。两特殊技能的默认授予与通知缺口、移动表现接线由 [FX／Audio 接线需求](../需求文档/fx_audio_wiring.md) 的原负责人处理；本项只记录当前引用，不修改或重复制作。未发现需另列的对象业务 C++ 分层整改项。

## 统筹核收与后续

B06、B08 两项整改已在 2026-11-11 验证完成（见上方两节的状态）。不要按旧的"9 项确认"或"3 项确认"派发 B01／B03／原 B04 的整体迁移。Kevin 原批已在做的共享图接线按原任务完成，不另立重复整改线。

Q02～Q05 的只读资产审查已完成；Kevin 整体需求（含 Q01）和各表现需求的运行验收仍按各自记录推进。默认配置没有授予的能力不写成已接入，读到图也不写成运行或联机通过。

## 第一轮范围与历史身份（仅保留覆盖证据）

第一轮曾写 9 项确认，补充规则后改为 3 项确认／6 项待核；**两种计数均被上方第二轮当前调用链结论替代**。下方保留第一轮范围和原版本身份，未重新清点 603 件；折叠原文中的 B／Q 分类、当前／本轮字样均指第一轮，不能作现行派发清单或当前文件状态。旧阶段／自动目标策略命中也不恢复。

<details>
<summary>第一轮原覆盖记录（其中判定引用已被上方替代）</summary>

清点使用 `rg --files --hidden -uu`，包含被 Git 忽略但实际存在的源码。检查扩展名含 `.h/.hpp/.cpp/.c/.cc/.cs/.py/.usf/.ush/.hlsl/.ps1/.bat/.cmd/.sh/.js/.ts/.lua`，另核整个候选树扩展名，未遗漏 `.inl/.ipp/.cxx/.mjs/.cjs/.jsx/.tsx/.glsl/.fx/.vert/.frag/.compute/.shader/.patch/.diff` 入口。

交回前范围清点共 **603 个源码／脚本／Shader 候选文件**：602 个项目维护或制作执行候选，另 1 个纯参考 Shader。初次身份记录为 602 个；期间原作者删除两件原生目标 Service、新增一件 Kevin 能力制作脚本和两件动作图作者源，新增／变化均按本次实际工作树复核，不把旧文件仍算生产实现。关键命中另按末节时刻复核，不宣称冻结后的全工程一致状态。

| 路径范围 | 文件数（含测试） | 审查覆盖与归类 |
| --- | ---: | --- |
| `Source/GGYGO/AI` | 37（测试 9） | Boss State／Definition／Encounter／Controller、两 BTTask、Attack／Melee／Death／Projectile／AudioActor、GE 制作接口；确认 B04，B01／B03 待核；阶段与目标新接口见 C01，图接线见 Q01。 |
| `Source/GGYGO/AbilitySystem` | 84（测试 22） | ASC、输入缓冲／Step Router、组仲裁、GA、Task、Cue、GE Context、Execution、AttributeSet 全部入口；B02 待核，原生死亡可替换支路见 Q02，其余机制见 C02。 |
| `Source/GGYGO/Character` | 58（测试 10） | Pawn 装配／Avatar／Health／Hero、CMC／RMS／预测／远端快照、动作与移动数据求值、角色渲染；B07 待核，不再把通用走跑／起停状态机直接判为上层违规；执行／生命周期见 C03。 |
| `Source/GGYGO/Animation` | 51（测试 9） | 只读语义帧、远端姿态、Montage Guard、Slot／BodyLean 节点、Notify、ZZZ 兼容层、动画制作函数；B09 待核，现有 AnimBP／倾身图见 Q03，通用节点见 C04。 |
| `Source/GGYGO/Camera` | 10（测试 2） | CameraComponent、Mode／Stack、ThirdPerson、PlayerCameraManager；B05 待核；所有权／最终碰撞及通用构图计算机制保留。 |
| `Source/GGYGO/Input` | 14（测试 3） | InputConfig／绑定、原始物理输入来源与消费、改键菜单；确认 B06；物理来源认证保留。 |
| `Source/GGYGO/Player` | 6 | LocalPlayer 生命周期、输入创建／移除、Controller 设置界面／队伍请求、PlayerState；B06 的实际调用方；调试控制台与生产调用分开。 |
| `Source/GGYGO/Teams` | 11（测试 2） | Slot、Squad 切换／进退场、Preset 读写及来源生命周期；确认 B08，Transition GA 活跃分支见 Q02。 |
| `Source/GGYGO/GameModes` | 12 | Experience、GameMode 装配、GameFeature 闭包／加载持有／Session／Subsystem；核为数据装配、权限和原生异步资源机制，未见具体 Boss 战斗／技能脚本。 |
| `Source/GGYGO/Combatants` | 8（测试 6） | 持久 ASC 宿主、Avatar 绑定／归还；机制保留。 |
| `Source/GGYGO/Combat` | 7（测试 2） | MeleeTrace、范围 Overlap／弹体 Sweep 与窗口去重；机制保留，窗口与组合交调用方。 |
| `Source/GGYGO/System` | 8 | AssetManager、共享 GameData／GE 加载、Tag、InitState 注册；未见按角色／Boss 名称决定业务的分支。 |
| `Source/GGYGO/Physics`、`Messages` | 2、1 | 带 Tag 的物材、消息载荷；符合数据／接口职责。 |
| `Source/GGYGO` 根级 | 5（原审查时） | 模块／Build.cs，以及原审查时的 `SyncMarkerImporter.*`。该工具现已迁到 GGYGOEditor，保留原反射入口并配置 CoreRedirects，见 [I22](../需求文档/refactor_and_squad_switch.md)；具体旧角色默认目录只用于显式资产导入。 |
| `Source/GGYGOEditor` | 42（测试 5） | 全部原生制作／图编辑／曲线／Montage／Niagara 桥、观察与读回、Kevin 两 Builder／AnimBP 作者、Boss BT／决策图作者及新增 `GGYGOBossAbilityGraphLibrary.*`；按最终图编辑性及制作／运行分离核查，见 Q01／C05。 |
| `Source/GGYGOAnimGraph` | 6 | Slot／BodyLean 编辑节点、编译校验及模块注册；符合编辑器机制。 |
| `Source/GGYGORendering` | 38 | 灯事实、阴影捕获、Distortion Profile／World／View／RDG、材质表达式、ProjectedDecal／SignedField Renderer／VF；符合渲染机制，不迁移渲染线程算法到 BP。 |
| `Source/*.Target.cs` | 2 | Target 配置，无玩法流程。以上 Source 合计 422 个。 |
| `Shaders/Private` | 5 | 四件 `.usf`、一件 `.ush`，均为采样／双场／VF／合成算法，无角色技能时间线。 |
| `AAADocs/Scripts` | 173（离线测试 24） | 根级制作／接线／采样／读回、全部 `zzz_*` 转换链、RenderingOverlay 三件入口及 12 件 Engine／UBT 覆层；逐类入口与产物去向均已定位，细分见下表。 |
| `AAADocs/Assets/Pyrios/Rendering/UnityMaterials` | 2 | `extract_material_params.py` 为离线提取，`accepted_single_output.hlsl` 为制作生成 Shader；无运行时技能控制。 |
| `AAADocs/References/Rendering/ZZZ_Shader_Annotated.hlsl` | 1 | 原 Shader 注释参考，清点但排除生产合规判定。 |

脚本覆盖不是以名称代替实现判断：已对作者 API、CDO 赋值、图创建／连接、Montage Notify、Niagara Stack、SoundCue 节点、注册回调及保存入口作全量结构筛查，再追读对应输出链。

| 脚本集合 | 实际覆盖 |
| --- | --- |
| 玩家／队伍／输入接线 | `wire_player_key_settings.py`、`wire_squad_switch_inputs.py`、`wire_pyrios_skill_inputs.py`、`wire_pyrios_skill_actions.py`、`wire_pyrios_death.py`、`wire_pyrios_combo_fx.py`、`wire_pyrios_normal01_*`、`wire_pyrios_locomotion_*`、`wire_pyrios_runtime_key_light.py`；`bind_*`、`migrate_*`、`slot_migration_*`。部分负责 CDO 数据配置，部分创建连接图，均可属于合法制作职责；前者本身不构成薄壳，合规性取决于共享流程和配置实际表达的业务。 |
| 动画／Boss 制作与导入 | `create_*`、`bake_anim_rootmotion_curves.py`、`normalize_pyrios_attack_pose.py`、`fix_*`、`organize_movement_assets.py`、`run_*`、FBX 读取／提取、`import_bh3_*`／`import_pyrios_*`／`import_pyrois_*`、`setup_bh3_kevin_materials.py`、`build_kevin_skill_animation.py`、`wire_bh3_kevin_combat.py`、本轮新增 `wire_kevin_boss_abilities.py`；追到原生 Builder／AuthorLibrary 与对应 Montage／BP／GE／DA。 |
| 材质／FX／音频制作 | 全部 `zzz_*` 文件、`build_pyrios_*`、`build_bh3_kevin_fx.py`／`build_bh3_kevin_audio.py`、`plan_bh3_kevin_audio.py`、`build_nap_*`／`gen_nap_*`／`nap_avatar_*`、`build_projected_*`／`gen_projected_*`／`projected_fx_*`、`pyrios_*_plan.py`、`reimport_pyrios_mesh_uv.py`／`export_pyrios_body_mesh.py`、`set_pyrios_light_response.py`、`configure_ggygo_level_key_light.py`。源码是制作图／节点／配置的入口，不是可据此签已制作的运行控制器。 |
| 审计／观测与支持 | 全部 `audit_*`／`inspect_*`／`verify_*`／`probe_*`／`diag_*`／`dump_*`／`capture_*`／`observe_*`／`check_*`、`test_bh3_stage_environment.py`、`png_stats.py`／`anim_json_stats.py`／`analyze_tails.py`／`ue_mcp.py`／`bh3_stage_environment_source.py`／`restore_bh3_stage_environment.py`、24 件 `tests/*`。Slate／Ticker 注册位于制作采样或诊断入口，不能机械认定为生产的第二套技能调度。 |
| RenderingOverlay | `launch-thin-runtime.ps1`、`write-overlay-config.ps1`、`OverlayHost.cs`，以及 `Engine/Source/Programs/UnrealBuildTool` 的 10 件 C# 与 `Engine/Source/Runtime/Renderer` 的两件覆层稿；它们是项目维护的构建／渲染入口，已纳入，不借“Engine”目录名漏掉。 |

明确排除：`.git`、`Binaries`、`Intermediate`、`Saved`、`DerivedDataCache`、`.vs/.idea`、`__pycache__`、`node_modules` 及对应嵌套生成目录；Saved 中仅按准确入口读取下述已有证据。Content 的二进制包不作源码阅读，不从字符串缺失推定图不存在。整机安装引擎与外部 AnimeStudio 不属本项目自有源码范围。

项目 `Plugins` 全量定位四件描述符：`GameplayMessageRouter`（Epic）、`UEFormat`（Zain／Marcel K.）、`VisualStudioTools`（Microsoft）、`Developer/RiderLink`（JetBrains）。分别清点 11／93／22／378 件代码候选，核描述符、来源头与项目特化标识检索；未定位本项目自研插件或另藏的 GGYGO 玩法实现。其第三方／引擎／生成源不纳入迁蓝图整改清单，也未把 `.uproject` 中仅启用的安装插件误算为项目自研源码。

</details>

<details>
<summary>2026-11-05 15:58:07 +08 原读源码身份（仅历史）</summary>

原记录基础提交父工程 `01d5948`／Source/GGYGO 子仓 `48c4427`，当时已有多人未提交改动；HEAD 不代表实际读版本。下表不授保护／写权，也不承诺文件至今未变化。

| 证据文件 | 字节数 | SHA256 前 12 位 |
| --- | ---: | --- |
| `Source/GGYGO/AI/Boss/GGYGOBossState.cpp` | 7332 | `6BC7A7CFFB89` |
| `Source/GGYGO/AI/Boss/GGYGOBossState.h` | 3094 | `C540CC2E4016` |
| `Source/GGYGO/AI/Boss/GGYGOBossAIController.cpp` | 23899 | `128DD054895F` |
| `Source/GGYGO/AI/Boss/BehaviorTree/BTTask_GGYGOChooseBossAction.cpp` | 6682 | `2DCAD94B5A9A` |
| `Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp` | 137684 | `AFC602C770E1` |
| `Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.h` | 18466 | `2FAEE6E47A2F` |
| `Source/GGYGO/AI/Boss/Abilities/GGYGOBossAttackAbility.cpp` | 29791 | `FDE2DA6686E0` |
| `Source/GGYGO/AI/Boss/Abilities/GGYGOBossDeathAbility.cpp` | 3209 | `DA2F3E330156` |
| `Source/GGYGO/Camera/GGYGOCameraMode.h` | 13857 | `6B621368E5A1` |
| `Source/GGYGO/Camera/GGYGOCameraMode_ThirdPerson.cpp` | 14066 | `62E5D506E556` |
| `Source/GGYGO/Input/GGYGOKeyBindingMenu.cpp` | 10019 | `422691041E21` |
| `Source/GGYGO/Player/GGYGOPlayerController.cpp` | 32953 | `46DD6AA4CA4D` |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp` | 276318 | `8B30F6C8B50C` |
| `Source/GGYGO/Teams/GGYGOSquadComponent.cpp` | 44813 | `FE6BF045045C` |
| `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionRules.cpp` | 516 | `7441A05F4780` |
| `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.cpp` | 835 | `A390570A59B8` |
| `Source/GGYGO/AbilitySystem/Abilities/GGYGODeathAbility.cpp` | 4776 | `CEBC9DF65ED1` |
| `Source/GGYGO/Teams/GGYGOSquadTransitionAbility.cpp` | 2668 | `798617CA52CE` |
| `Source/GGYGOEditor/Private/GGYGOBossCombatAssetLibrary.cpp` | 23955 | `C1B12057507D` |
| `Source/GGYGOEditor/Private/KevinBossAnimBlueprintAuthor.cpp` | 12875 | `ADB37C924724` |
| `AAADocs/Scripts/wire_bh3_kevin_combat.py` | 81685 | `5115A9431FBD` |
| `AAADocs/Scripts/wire_pyrios_locomotion_pose.py` | 159583 | `9BD9287DB03A` |
| `AAADocs/Scripts/wire_kevin_boss_abilities.py` | 14540 | `B1803BC5B6BE` |
| `Source/GGYGO/AI/Boss/Abilities/GGYGOBossAttackAbility.h` | 7557 | `EA9759083DA6` |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h` | 66269 | `7B3E8E1E9267` |
| `Source/GGYGOEditor/Public/GGYGOBossAbilityGraphLibrary.h` | 950 | `CAC213A5CDA8` |
| `Source/GGYGOEditor/Private/GGYGOBossAbilityGraphLibrary.cpp` | 10245 | `BA9D03BDC4D9` |

</details>

## 第二轮交回版本身份

复核时刻：2026-11-05 16:52:43 +0800。只列本轮消费的关键路径，SHA256 前 12 位定位版本；不是全工程保护快照。

| 本轮关键路径 | 字节数 | SHA256 前 12 位 |
| --- | ---: | --- |
| `Source/GGYGO/Input/GGYGOKeyBindingMenu.cpp` | 10019 | `422691041E21` |
| `Source/GGYGO/Player/GGYGOPlayerController.cpp` | 32953 | `46DD6AA4CA4D` |
| `Source/GGYGO/Teams/GGYGOSquadComponent.cpp` | 44813 | `FE6BF045045C` |
| `Source/GGYGO/AI/Boss/GGYGOBossAIController.cpp` | 23899 | `128DD054895F` |
| `Source/GGYGO/AI/Boss/GGYGOBossActionSet.h` | 2503 | `2AA426B18A40` |
| `Source/GGYGO/AI/Boss/BehaviorTree/BTTask_GGYGOChooseBossAction.cpp` | 6682 | `2DCAD94B5A9A` |
| `Source/GGYGO/AI/Boss/GGYGOBossState.cpp` | 7332 | `6BC7A7CFFB89` |
| `Source/GGYGO/AI/Boss/GGYGOBossDefinition.h` | 4576 | `AAEE8020AD06` |
| `Source/GGYGO/AI/Boss/GGYGOBossEncounter.cpp` | 8702 | `C80DB6DD473C` |
| `Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp` | 137684 | `AFC602C770E1` |
| `Source/GGYGO/AbilitySystem/Abilities/GGYGOComboTypes.h` | 7317 | `C6D5EEAAC2C4` |
| `Source/GGYGO/AI/Boss/Abilities/GGYGOBossAttackAbility.cpp` | 40837 | `464008D0042D` |
| `Source/GGYGO/AI/Boss/Abilities/GGYGOBossAttackAbility.h` | 10261 | `813BA7073DB0` |
| `Source/GGYGO/AI/Boss/Abilities/GGYGOBossDeathAbility.cpp` | 5550 | `9D1EB0281791` |
| `Source/GGYGO/Camera/GGYGOCameraMode_ThirdPerson.cpp` | 14066 | `62E5D506E556` |
| `Source/GGYGO/Camera/GGYGOCameraMode_ThirdPerson.h` | 5660 | `EC67A732F279` |
| `Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp` | 76110 | `71AA8A698D2F` |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp` | 276318 | `8B30F6C8B50C` |
| `Source/GGYGO/Character/Data/GGYGOMovementSet.h` | 13686 | `08C98176A08C` |
| `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionRules.cpp` | 516 | `7441A05F4780` |
| `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.cpp` | 835 | `A390570A59B8` |
| `Source/GGYGO/AbilitySystem/Abilities/GGYGODeathAbility.cpp` | 4776 | `CEBC9DF65ED1` |
| `Source/GGYGO/Teams/GGYGOSquadTransitionAbility.cpp` | 2668 | `798617CA52CE` |
| `Source/GGYGOEditor/Private/GGYGOBossCombatAssetLibrary.cpp` | 24997 | `770FC6B83539` |
| `Source/GGYGOEditor/Public/GGYGOBossAbilityGraphLibrary.h` | 962 | `6D77663ABC59` |
| `Source/GGYGOEditor/Private/GGYGOBossAbilityGraphLibrary.cpp` | 19587 | `EC129B7F16A1` |
| `AAADocs/Scripts/wire_kevin_boss_abilities.py` | 19108 | `897EB2B467F2` |
| `AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Ability_Config.json` | 14807 | `7464DA59D625` |

本页是本轮唯一改动；不含实现／资产修复，不补签未运行验证。
