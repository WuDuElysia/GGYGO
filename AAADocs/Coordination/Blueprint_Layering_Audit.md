# 全项目蓝图与 C++ 分层审查

任务：BLA-20261105-01。唯一报告／活动入口：本页。统筹：`01a1347b-ccee-7081-a783-0c3127b3dd48`；审查：`01a1aa9d-f20e-7092-8741-87890a6f1049`。

**2026-11-11：B06、B08 已验证完成；Q02～Q05 资产图读回和 Kevin 的 Q01 交给 Codex，见 [Codex 交接](Handover_Codex.md)。**

**第二轮实质复审完成：当前确认 2 项分层问题（B06、B08）；其余 7 项当前没有必须继续迁出 C++ 的依据，B04 旧命中撤回。** Kevin 制作链已沿最新接口重读，交回版本已消除期间读到的旧调用／旧字段差异，不留作未完成整改。Q01～Q05 是资产图／运行证据边界，不是另外五项确认违规。

本轮沿**当前** B01～B09、Q01～Q05 和 Kevin 新增改动的必要依赖复审，实际追读激活、调用、事件、作者配置和清理链，**不是仅重分旧结论**。没有重做第一轮 603 件清点或扩到其它需求。本页之外无写入；未启动 UE、构建、测试、制作／保存包，未冻结作者、派发整改或修改排程、Obsidian、Git。下列批次供统筹交原组长实施，本报告不授写权。

## 判定与当前状态

依据当前 [AGENTS.md](../../AGENTS.md) 架构条款和 [CodeConventions](../Architecture/CodeConventions.md) 的蓝图与 C++ 分层。允许“通用机制＋共享蓝图流程＋对象资产配置”；简单变体可仅配子蓝图／CDO／DA。只有定位仍固定于原生的具体业务分支、组合或时序，才确认归属问题；角色名、数字、原生算法／状态机、未暴露覆写口和缺完整图均不能单独确认违规。

这是作者不停工期间的逐文件读版本，末节记录身份，**不是冻结工程的原子快照**。源码、生产接线、编译、保存、运行和联机分别判断。没有从工具读到图，不等于资产没有图；制作代码能生成图，也不等于生产图已制作、保存或运行。

| 当前分类 | 编号 | 可据此安排的动作 |
| --- | --- | --- |
| 确认必须调整的分层位置 | B06、B08 | **已验证完成（2026-11-11）**：两项都已迁到共享蓝图并在真实运行中通过，见各节关闭记录和[蓝图分层收尾](../需求文档/blueprint_layering_followups.md)。 |
| 当前不用强制迁移／撤回 | B01、B02、B03、B04、B05、B07、B09 | 撤销按旧编号整体迁出的建议；实际资产接线仍按 Q 项核，不预建接口或第二套状态机。 |
| 尚缺实际资产／运行证据 | Q01～Q05 | 在各自原制作验收补最小证据；不据未知派发迁移，不为本轮另启 UE／全库导出。 |

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

本轮重核当前 `Content/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo.uasset` 为 45,776B，SHA256 `16EF3CE5DF98787342192C761B3D68FF187FDF7E5E6A844AB8EDDA0D41BE9B7A`，与 R53 准确读回一致；实际三段映射 1／2／0，Montage 为 Normal01／02／03。对象配置三段不代表机制写死三段。撤回因消费配置表／数据子类或 StartStep 未暴露 BP 而要求新增图／接口的建议。输入身份、预测、窗口和清理保留；完整共享图仍未知，不以图哈希判空图。

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

## Q01～Q05：仍未知及最小证据

| 编号 | 本轮事实与未知边界 | 最小证据／关闭条件 |
| --- | --- | --- |
| Q01 Kevin State／BTS／BT／GA | 已读新事实接口、实际 K2／BT 作者及共享模板消费。按当前配置准确检查 15 技能＋1 死亡＋3 模板共 19 个目标包，磁盘均未见；仅证这些包尚无落盘身份，不推断内存未保存图。当前需求也仍制作／验证未完成。 | 原制作窗读 `/Game/Characters/Boss/Kevin/DemonBattle/Abilities/Templates/` 下 BP_GA_BossGroundFlow_KVB／BP_GA_BossFlightFlow_KVB／BP_GA_BossDeathFlow_KVB 的事件、关键调用、exec／Token／失败／几何和等待参数连接；15 子类真实父类／必要 CDO；Definition 的 StateClass／Service／阶段池、实际 State／BTS／BT 图和授予引用。提供准确包身份／保存读回，不要求子类复制图。地面完成、飞行真实 Landed 后收尾、目标失效、死亡正常／中止仍按原集中运行验收。 |
| Q02 玩家 Death／SquadTransition | `GGYGODeathAbility.cpp:35`、`GGYGOSquadTransitionAbility.cpp:23` 的 BP 接管支路、原生通用播放回调与 Health 清理已复读，未定位本轮新增对象特化；旧报告不绑定当前全图。 | 当前实际授予类、共享父流程、子类 CDO／Montage、正常／中止连线及包身份。区分通用播放和额外表现业务，不因不覆写 K2_ActivateAbility 判违规。B08 只处理自动替补触发，不借缺图迁走整个进退场／生命周期。 |
| Q03 ABP_Pyrios | 源码语义／适配和作者工具不能证明当前生产图；无新完整图。B07／B09 均无强制迁移依据。 | 实际共享 ABP 的 Stop 语义／索引消费、相关过渡、Slot／BodyLean／倾角与恢复连接，对象序列／曲线配置及必要包身份；核模板＋数据能否表达差异。不导出全库、不另造 CMC FSM。 |
| Q04 Camera | 已核通用计算与 Hero 所有权，当前默认／GA 覆盖实际选择链和演出图未补签。 | 实际 PawnData.DefaultCameraMode、GA 覆盖／释放、必要共享镜头图及对象曲线／参数／包身份。无具体演出分支证据就不派数学迁移。 |
| Q05 Audio／FX／材质 | 沿 GA／作者窗制作消费复核了接口，未打开当前图、看原图或听音。脚本／配置不证明组合、音色、时窗或可见结果正确。 | 各原作者验收中读实际共享图／子资产、Notify 时窗、GA／Cue／组件引用和包身份；必要真实视听按原目标验。不要求每资源变体独立图，不签原版音效恢复／画面通过。 |

本轮实际消费的已有准确证据：

- `Saved/Codex/FXProduction_20261026_R1/ColdRead_20261102_R1/Run_R53/Leaf/readback.json` 的 `observations.ga['/Game/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo']`：父类 `/Script/GGYGO.GGYGOPlayerComboAbility`，包 SHA 与本轮一致，实际 combo_steps 已复读；图哈希 `314371a8ae322de71667ff7a256f90ff9c56ba93d2cdae928cfd0624edb26b3d`，**没有完整节点连接**。
- 第一轮已消费 `Saved/Codex/FXProduction_20261026_R1/Production_R107/return.json`／`Leaf/readback.json`，当时 Combo SHA `4559BD58…` 与当前不同，仅历史线索。`Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/Asset_R24e/asset_report.json` 只证当时 Death 创建保存，不签当前图。本轮未重读这些历史大报告或刷新 Death 包身份。

## 统筹核收与后续

当前仅针对 **B06、B08** 安排两个原作者等价整改批次，两项均可独立于 Kevin 收口。不得沿旧“9 项确认”或上次“3 项确认”派发 B01／B03／原 B04 的整体迁移。Kevin 原批已在做的共享图接线按原任务完成，不另立重复整改线。

本轮审查交付完成；两项整改、Kevin 整体需求和 Q01～Q05 尚未完成。后续由统筹沿真实前置统一冻结、构建、制作和必要最小集中验证，本页不增设 UE／编译／历史矩阵前置。各项通过后原位更新，源码、资产、运行、联机分别据实核收。

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
| `Source/GGYGO` 根级 | 5 | 模块／Build.cs，以及 `SyncMarkerImporter.*`。后者含具体旧角色默认目录，但调用链是显式导入工具，不是运行时选招／表现控制器，不能因路径名直接判业务违规。 |
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
