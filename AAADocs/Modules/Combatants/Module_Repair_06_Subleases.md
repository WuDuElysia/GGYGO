# 第 06 批 Combatants 文件子租约

更新：2026-10-04。Host Refresh caller query三文件修正已落盘、有限静态核对并冻结交回：仅OriginalScope改为原Host/端点/原opaque槽查询，ASC独占原生权限和提交，原Context/H资格及真实Commit/Receipt保持。修正版未编译/UE，不能用Gate57旧DLL单叶Success验收；两次Entry生产Refresh/Release失败保留，待统筹新DLL同Entry必要冒烟。H1/H2/H3与接口保持，R0旧2 Fail/12 errors不变，Teams未放行。

## 已确认接口契约

- 玩家 `PawnData` 与 Boss `BossDefinition` 的复制回调和 Authority 初始化共用幂等 ASC 规则配置入口；AbilitySet 与属性授予仍只在 Authority 执行。
- Authority 不允许隐式跨宿主抢占 Pawn；调用方须先从旧宿主 Detach。PawnExtension 只在本地缓存与 ExpectedASC 匹配时处理解绑，并只在 ASC Avatar 身份仍匹配时修改该共享 ASC；宿主另行清理自己 ActorInfo 中仍指向旧 Pawn 的 Avatar。
- `AGGYGOCombatantState::EndPlay` 在服务器和客户端清理本地 Avatar 绑定、订阅与缓存；无 Avatar 时保留持久 ASC 的数值、GE、冷却与死亡标签。
- PawnExtension 只要存在本地 ASC 缓存，解绑便广播一次；只有它仍是 ASC 当前 Avatar 时才取消能力、清输入/Cue 与清 AvatarActor。继续复用 HeroComponent 已有的唯一解绑协调入口。
- `UGGYGOHealthComponent` 的死亡状态只向 ASC 单调投影 `State.Dying` / `State.Dead`；初始化和解绑不把默认 `NotDead` 当作隐式复活。Authority 给已有死亡投影的无 Avatar 宿主绑定新 Pawn 时，在任何副作用前拒绝；同一现有 Avatar 的重复 Attach 保持幂等。客户端按服务器 Avatar 复制收敛，不因复制到达顺序拒绝。
- 本批不实现复活、死亡后重新挂接、完整 Boss 换形态事务、输入解绑扩展或相机第二清理通道。普通存活 Boss 更换 Avatar 仍使用原宿主契约。

## 拆分预检

所有生产文件按状态所有权和变化原因拆成五个原子任务；测试按契约主题拆成三个互斥文件组；结构说明和两张 Canvas 各自独占一个文档文件。每个任务只允许在自己的停止点交回，不能顺带修改相邻任务文件。

### 生产代码原子任务

| 子任务 | 唯一写入者 | 精确可写文件 | 唯一结果 | 非目标 | 只读依赖 | 验收断言 | 停止点 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 06A-0 原生产接口任务 | 临时代理 `combatants_impl`（`gpt-6-luna / max`） | 原计划十个生产文件 | 无 | 不再继续整包实现 | AGENTS、台账、排程、十个源码文件 | 无文件落盘 | 只读分析完成即停止 | 已中断并释放 |
| 06A1-Player | 临时代理 `combatants_config`（`gpt-6-luna / max`） | `Source/GGYGO/Teams/GGYGOCharacterSlot.h`、`.cpp` | `PawnData` 复制到客户端后幂等应用 ASC 组规则与 Tag 关系 | Boss 配置、AbilitySet 授予规则、Avatar 生命周期 | ASC、PawnData、复制声明 | Authority 初始化和 `OnRep_PawnData` 共用配置入口；能力授予仍仅 Authority | 两文件实现落盘并自查后冻结 | 已冻结；组长审查完成 |
| 06A1-Boss | 临时代理 `combatants_config`（`gpt-6-luna / max`） | `Source/GGYGO/AI/Boss/GGYGOBossState.h`、`.cpp` | `BossDefinition` 复制到客户端后按初始形态 PawnData 幂等应用 ASC 规则配置 | Player Slot、阶段换形态合并规则、AbilitySet 授予规则 | ASC、PawnData、BossDefinition、复制声明 | Authority 初始化和 `OnRep_BossDefinition` 共用配置入口；能力授予仍仅 Authority | 两文件实现落盘并自查后冻结 | 已冻结；组长审查完成 |
| 06A2-Host | 临时代理 `combatants_host_atomic_v2`（`gpt-6-luna / max`）；原代理 `combatants_host_atomic` 已中断且无落盘 | `Source/GGYGO/Combatants/GGYGOCombatantState.h`、`.cpp` | 宿主负责 EndPlay 本地清理、Authority 跨宿主拒绝、死亡宿主新 Avatar 拒绝和身份安全 Detach | PawnExtension 内部解绑实现、Health 死亡投影、复活、完整换形态事务 | ASC、PawnExtension、GameplayTags、Actor 生命周期 | 所有拒绝均在副作用前；客户端按复制收敛；Detach 只清仍属于本宿主/Pawn 的绑定；EndPlay 不 ForceNetUpdate | 两文件实现与静态自查完成后冻结 | 已冻结；组长返修身份清理后审查完成 |
| 06A2-Pawn | 临时代理 `combatants_pawn_atomic`（`gpt-6-luna / max`） | `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h`、`.cpp` | PawnExtension 本地解绑必定先清缓存并广播一次，共享 ASC 仅在 Avatar 身份匹配时清理 | CombatantState 宿主策略、Hero 输入/相机第二清理通道、死亡投影 | ASC、HeroComponent 既有解绑协调入口 | ExpectedASC 不匹配时无操作；Initialize 踢旧 Avatar 时也必须传入 InASC；匹配时先本地置空再广播；只有当前 Avatar 为本 Pawn 才改共享 ASC；SurvivesDeath 保留 | 两文件实现与静态自查完成后冻结 | 已冻结；交叉审查返修完成 |
| 06A3-Health | 临时代理 `combatants_health`（`gpt-6-luna / max`） | `Source/GGYGO/Character/Components/GGYGOHealthComponent.h`、`.cpp` | DeathState 向当前 Avatar ASC 单调、幂等投影并支持晚绑定补投影 | 复活、解绑时清死亡标签、死亡事件重放、宿主 Attach 策略 | ASC、HealthSet、GameplayTags、Owner Avatar 身份 | `DeathStarted` 投影 Dying；`DeathFinished` 同时保持 Dying/Dead；`NotDead` 不清；非当前 Avatar 不写 | 两文件实现落盘并自查后冻结 | 已冻结；组长审查完成 |

### 测试原子任务（各自生产依赖冻结后独立派发）

| 子任务 | 唯一写入者 | 精确可写文件 | 唯一结果 | 非目标 | 依赖 | 验收断言 | 停止点 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 06B-Config | Combatants 长期组长；原临时代理 `combatants_config_tests` 已中断且无落盘 | `Source/GGYGO/Combatants/Tests/GGYGOCombatantConfigReplicationTest.cpp`、`Source/GGYGO/Combatants/Tests/GGYGOCombatantConfigReplicationTestTypes.h` | 覆盖 Player/Boss 复制回调配置契约 | Host/Pawn 生命周期、死亡投影 | 已冻结的 06A1-Player/Boss 接口 | 验证客户端配置可重入且不触发授予 | 两测试文件完成静态自查后冻结 | 已冻结；静态检查通过，未运行 |
| 06B-Binding | Combatants 长期组长 | `Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp`、`Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTestTypes.h` | 覆盖跨宿主拒绝、身份安全 Detach、EndPlay 与 Pawn 本地解绑契约 | 配置复制、死亡标签状态机本体 | 已冻结的 06A2-Host/Pawn 接口 | 验证拒绝无副作用、旧宿主不能清新绑定、解绑广播一次；InASC 仍指旧 Pawn 但旧 PawnExtension 已缓存 OtherASC 时，迟到踢除不得广播或清 OtherASC | 两测试文件完成静态自查后冻结 | 已落盘、静态检查通过，未运行 |
| 06B-DeathProjection | Combatants 长期组长；原临时代理 `combatants_death_tests` 已中断且无落盘 | `Source/GGYGO/Combatants/Tests/GGYGOCombatantDeathProjectionTest.cpp`、`Source/GGYGO/Combatants/Tests/GGYGOCombatantDeathProjectionTestTypes.h` | 覆盖死亡标签单调投影与晚绑定重放 | 复活、完整 Attach/Detach 场景、配置复制 | 已冻结的 06A3-Health 及必要只读测试接口 | 验证 Started/Finished、重复调用、晚绑定及非当前 Avatar 不写 | 两测试文件完成静态自查后冻结 | 已冻结；静态检查通过，未运行 |

### 文档原子任务（生产与测试内容冻结后派发）

| 子任务 | 唯一写入者 | 精确可写文件 | 唯一结果 | 非目标 | 依赖 | 验收断言 | 停止点 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 06C-Structure-MD | Combatants 长期组长 | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Combatants/结构.md` | 同步职责、接口、依赖、状态所有权与验证边界 | Canvas、全局入口、将未验证内容写成已验证 | 冻结源码、测试源码与相邻模块结构说明 | 当前实现与未验证边界均准确 | 单文件更新并检查链接后冻结 | 已更新、已冻结 |
| 06C-Combatants-Canvas | Combatants 长期组长 | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Combatants/GGYGO_结构_Combatants.canvas` | 同步 Combatants 结构与契约关系图 | Markdown、角色初始化流程图、全局入口 | 冻结源码与 Structure MD 只读结果、Canvas 技能规范 | JSON 合法、ID 唯一、边引用存在、当前/计划状态准确 | 单文件更新并校验 JSON/边后冻结 | 已冻结；JSON、ID、边引用校验通过 |
| 06C-Character-Flow | Combatants 长期组长 | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Character/GGYGO_流程_角色初始化.canvas` | 同步角色初始化与解绑顺序图 | Markdown、Combatants 结构图、全局入口 | 冻结源码与 Structure MD 只读结果、Canvas 技能规范 | JSON 合法、ID 唯一、边引用存在、Authority/客户端及解绑顺序准确 | 单文件更新并校验 JSON/边后冻结 | 已冻结；JSON、ID、边引用校验通过 |

### 组长记录

| 子任务 | 唯一写入者 | 精确可写文件 | 状态 |
| --- | --- | --- | --- |
| 06 组长记录 | Combatants 长期组长 | `AAADocs/Modules/Combatants/Module_Repair_06_Subleases.md`、`AAADocs/Modules/Combatants/Module_Repair_06_Validation.md` | 已收口；只记录实际证据，不改上级台账/排程 |

## 禁止范围

- 子任务不得写 HeroComponent、Camera、AbilitySystem/HealthSet、Combat Trace/HitContext/Cue、生产资产、Build.cs、全局 Obsidian 入口、总台账或并行排程。
- 子任务不得运行 UE、UBT/构建、Git 写操作，不得再派发写入者。
- 现有未提交改动全部保留；发现接口依赖超出上述文件时停止写入并交回组长处理。

## A9 / 06-L1-I 宿主绑定生命周期准入：实施前登记（2026-09-30）

- 授权：统筹在 Build29 成功、常规项目自动化 63/63 Success 且 UE26112 已退出后明确授权四文件；该门禁发生在本步改动前，不能证明本步已编译或已运行。
- 唯一写入者：Combatants 长期组长本人，按 gpt-6.1-sol / xhigh 执行；不创建或唤醒代理。历史子租约仍保留。
- 唯一结果：仅在宿主可控制的调用边界阻止关闭/原生销毁状态下建立非空 Avatar 绑定，同时保留必要清理及原生同实例下一次 BeginPlay 的合法准入。
- 精确范围：Source/GGYGO/Combatants/GGYGOCombatantState.h；Source/GGYGO/Combatants/GGYGOCombatantState.cpp；AAADocs/Modules/Combatants/Module_Repair_06_Subleases.md；AAADocs/Modules/Combatants/Module_Repair_06_Validation.md。
- 只读依赖：Actor/Level/World 原生生命周期；共享 ASC、PawnExtension、Hero、Slot、Teams、Boss 与既有测试；上级台账和并行排程；Obsidian 架构材料。
- 冻结契约：私有 permission 默认开放；所有 EndPlay 先关闭再 ClearLocal/Super；仅 IsActorBeginningPlay && IsValid(this) && !IsActorBeingDestroyed 时在 Super::BeginPlay 前重开，Super 后不再覆盖。非空 Attach/Synchronize 检查宿主及目标 Pawn；Detach/clear 回调返回后至提交/Initialize 前复核。关闭后不 ForceNetUpdate。null/Detach/ClearLocal 清理、Owner、ExpectedASC、唯一 Hero 通知与 SurvivesDeath 原链保持。
- 诊断：新增准入拒绝使用 Error，包含 Combatants、入口、宿主、ASC、目标 Pawn 与原因；不返回绑定成功语义，不补默认 Avatar，不重试，不增加公开 ready、原生状态缓存或 Tick。
- 非目标：普通开放态 Attach/Detach 同步后继事务；Initialize 内部销毁回调后继续写入；Engine/GAS 改动；BeginPlay 延迟 Destroy 私有意图覆盖；BossEncounter 自己的 bEndingPlay；测试、构建、UE、Git、资产、Obsidian、全局文档及 Teams 清理。
- 方法边界：PostInitialize 不重开；BeginPlay 只在原生入口重开；EndPlay 首关；Attach 非空入口/Detach 返回后提交前检查、Synchronize 返回后防关闭态 ForceNetUpdate；Detach 完成 ClearLocal 后检查并停止关闭态外层继续；Synchronize 非空入口/旧绑定 clear 返回后 Initialize 前检查；OnRep 共用 Synchronize；ClearLocal/HandleAvatarDestroyed 原清理路径保留。
- 验收断言：默认允许首次 PreBegin；关闭或宿主/目标 Pawn 原生销毁时非空绑定有明确拒绝；每处宿主可控制的回调返回后检查覆盖；ExpectedASC/身份清理保持；仅真实 BeginPlay 可重开；无公开接口变化、循环依赖、第二执行链或 Tick。
- 顺序：本登记 -> 两个生产文件实现/静态审查 -> 明确生产冻结 -> 两记录追加实际证据 -> 四文件哈希与本步实际源码差异交回。
- 停止点：实现并静态审查后冻结，不自行构建或运行；共享接口需求超出本四文件即停止交回。真实 Destroy/流送/客户端及回调测试、Obsidian 同步须独立后续租约。
- 当前状态：预检已登记；仅上述范围可实施，其余文件继续冻结。

## A9 / 06-L1-I 冻结交回（2026-09-30）

- 当前状态取代上方实施前状态：两生产文件实现并经静态核对后冻结；两记录仅追加本步预检/证据，交回后四文件全部停止写入。测试、构建、UE、Git、共享接口、资产与 Obsidian 仍未获本步授权。
- 实际改动：h 增加 protected BeginPlay、两个 private 校验方法与默认开放的私有 permission；cpp 增加 BeginPlay 原生入口重开/EndPlay 首关、Attach 入口及 Detach 返回后检查、Synchronize 入口及 clear 返回后 Initialize 前检查、Detach 清理后停止关闭态继续动作，以及两个 ForceNetUpdate 调用的准入条件。两文件逐项实际差异见 Module_Repair_06_Validation.md 的 A9 diff。
- 生产冻结 SHA256：GGYGOCombatantState.h = A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF；GGYGOCombatantState.cpp = 6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84。
- 已执行：实际新文本与登记的逐项修改完全一致；PostInitializeComponents、GetLifetimeReplicatedProps、OnRep_AvatarPawn、HandleAvatarDestroyed、ClearLocalAvatarBinding 方法文本与本步前完全一致；源码 LF/行尾空白检查通过；人工核对准入检查顺序、Owner 空 Avatar 分支、ExpectedASC 原调用、无新增依赖/公开接口/复制状态/Tick。
- 未执行：本步 UHT/完整构建、自动化、真实 Destroy/RemovedFromWorld 重入、客户端网络与回调动态测试。Build29/63 Success 为本步前历史基线，不证明本步代码。
- 保留限制：普通开放态后继事务；Initialize 内部回调销毁后继续写入；BeginPlay 延迟 Destroy 私有意图；任意 Pawn 非 Destroy EndPlay 的识别；BossEncounter 自有 bEndingPlay。不得据本步自动授 Teams 清理或共享 ASC/Extension 修改。
- 架构材料已只读核对：Combatants/结构.md、Combatants/GGYGO_结构_Combatants.canvas、Character/GGYGO_流程_角色初始化.canvas 需要补本步准入边界及验证状态；本租约禁止写入，等待独立图文租约，不能宣称模块文档一致性已完成。
- 停止点已到：交回实际 diff、四文件哈希及未验清单后停止；后续真实测试与文档同步分别预检、授权。

### A9 写入方式与早期错误补充

- 两份生产源码实际成功写入方式为 apply_patch。成功后全文逐项比对及源文件读回 SHA256 分别为 A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF / 6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84；统筹只读观察也确认相同前缀。
- 早期 shell WriteAllText 尝试对两源码均报告 Access denied；PowerShell 当时没有终止错误设置，进程 exit0 及尾部 A9_SOURCE_WRITTEN 不代表成功。随后的 Get-FileHash 仍为原 645D6F46… / A049826F…，故不能把该尝试记成源码已写入。首次替换校验和首次 apply_patch 校验也在写入前失败；随后修正完整行匹配，仅成功应用一次获授补丁。
- 未修改 ACL、只读属性或链接，没有把早期拒绝后的命令当作成功证据，没有重复套用成功补丁。
- 两记录此前通过 shell AppendAllText 追加，Subleases 本步新增尾部曾调整为原 LF；均保持本步前字节前缀。统筹最新要求后，本错误/方式补充仅使用 apply_patch；后续编辑遵循 apply_patch，不继续使用 shell 写入技巧。实际方式如实保留，不改写为所有文件均由 apply_patch 写入。

## A12 / 06-L1-T1 真实销毁拒绝清理回调重绑：实施前登记（2026-10-01）

- 授权与基线：统筹已审查只读预检及原生销毁顺序，在第30次完整构建成功、63项目叶 Success 且正常/探针/英文对照三个 UE 退出后授本步。第30次发生在新测试前，不证明本步新叶已编译或运行。
- 唯一写入者：Combatants 长期组长本人，gpt-6.1-sol / xhigh；本地编辑仅用 apply_patch，不创建/唤醒代理，不修改 ACL/属性。
- 精确三文件：Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp；AAADocs/Modules/Combatants/Module_Repair_06_Subleases.md；AAADocs/Modules/Combatants/Module_Repair_06_Validation.md。TestTypes.h、旧两测试/旧夹具、生产及全局文件继续冻结。
- 唯一目标：真实私有 GI/WorldContext、显式原生 BaseGameMode 与 World::BeginPlay 完成后调用 Host->Destroy()；仅旧 PawnExtension 清理回调尝试一次 Attach 候选，明确拒绝，且在 Garbage 前证明无绑定/缓存/销毁订阅残留并保留 Owner。
- 只读依赖：原生 GI/World/GameMode/GameState/Actor 与稀疏委托接口；冻结的 CombatantState、PawnExtension、ASC；现有 TestTypes；本轮台账/排程。测试用读取快照和计数，不新增生产接口或权威状态。
- 具体改点：既有 cpp 的 WITH_DEV_AUTOMATION_TESTS 内补直接头、独立真实 World 夹具及单一 GGYGO.Combatants.Binding.RealDestroyRejectsCleanupReattach 叶；现有类定义、旧测试和旧夹具原文保持，无需新 UCLASS 或 TestTypes 写入。
- 真实前置：GEngine；GI 按 InitializeStandalone 创建自己的 World/Context/ComponentManager；URL 指定 AGameModeBase::StaticClass 路径并核对精确类；InitializeActorsForPlay 与 GameState 成立；调用 World::BeginPlay，核对 World、所有目标 Actor 与注册组件完成 BeginPlay，宿主/ASC、旧/候选 PawnExtension 来源和身份有效。不接受默认类或手工 EndPlay/Dispatch 替代，失败明确断言并真实清理。
- 同步边界：World OnActorDestroyed 记录有效/BeingDestroyed/尚在 BeginPlay；旧 Extension Uninitialized 记录已清本地缓存/ASC Avatar 且 Owner 保留，再唯一一次 Attach 候选；World OnActorRemovedFromWorld 记录 EndPlay 后且未 Garbage 的最终引用/缓存/订阅。三事件顺序固定，计数各1；候选 Initialize 通知0。
- 诊断契约：完整 [Combatants] AttachAvatar.Entry 正文包含实际宿主/ASC/候选路径及“宿主正在原生销毁流程中”，AddExpectedErrorPlain + Exact + Occurrences=1；不匹配短片段，不接受额外诊断或无限次数。
- 身份与清理断言：Destroy 前 OtherASC ExpectedASC 不匹配完全无操作；宿主复制源 Avatar、ASC Avatar 与两 PawnExtension 缓存最终为空；旧/候选 Pawn OnDestroyed 均无宿主 Handler；Owner 在原生 Garbage 前仍为宿主。仅检查复制源，不把它写成联机复制证明。
- 退出责任：探针使用弱共享委托，关闭 armed 并移除两个 World handler；GI/Manager 存活期间真实销毁剩余 Actor并结束 World；随后 Shutdown/DestroyWorld/context、清临时包 dirty，恢复三原生网络加密委托，释放 GI。前置失败同样执行，无空 catch/业务兜底。
- 非目标：流送同实例重进；Initialize 内部销毁回调后继续写入；普通 successor 竞态；私有 BeginPlay 延迟 Destroy；Hero/SurvivesDeath 完整动态专项；Teams 清理；UE/构建/Git/代理/资产/Obsidian/全局入口。
- 顺序与停止点：本登记 -> 单 cpp 实现/静态核对冻结 -> 两记录追加实际 diff/hash/保护与未运行证据 -> 三文件冻结交回。不能证明候选或需第四文件时停止报告；不自行运行，不自动继续下一专项。
- 当前状态：预检登记；本步仅获上述三文件，不扩大共享范围。

## A12 / 06-L1-T1 静态冻结交回（2026-10-01）

- 当前状态取代本步实施前状态：仅获授三文件完成，新增测试 cpp 已静态冻结；两记录追加本步实际证据后冻结。全部本地编辑使用 apply_patch，未改 ACL/属性，未写 TestTypes/生产/共享接口/资产/Obsidian/全局文件。
- 单一新增叶：GGYGO.Combatants.Binding.RealDestroyRejectsCleanupReattach。既有 cpp 内加入独立真实 GI/World 夹具，无新 UCLASS，无 TestTypes 修改。源码差异 +341 / -0 行，删除本步新增内容可逐字恢复原 cpp（A837FD014A1322F81D94B3EA119791F9295C576168F65F4BAFC6213E61F29A77）。
- cpp 冻结 26352 字节，SHA256 35E97151BAD47F8239F66B9C82F9A99CA9BB4EC7360792ABC49E82E0CD2745C4；本步前 8596 字节。实际逐项 diff 见 Validation 的 A12 段。
- 已落实的断言：明确 GI/WorldContext/Manager、URL 指定原生 BaseGameMode、GameState、World 与四目标 Actor/所有注册组件 BeginPlay、两持久 ASC 独立 Owner；正常绑定前置；ExpectedASC 不匹配完整绑定快照/其它宿主与通知计数不变；真实 Host->Destroy；World 原生销毁/Extension 清理/Removed 三边界快照与固定次序，各通知1，Attach尝试1，候选初始化0。
- 新诊断只有 AddExpectedErrorPlain(ExpectedRejection, Exact, 1)，正文含实际宿主/ASC/候选路径与完整 NativeBeingDestroyed 原因。Probe 唯一 Attach 位于旧 Extension 清理回调，没有额外生命周期替代或宽匹配。
- 所有最终 Owner/复制源 Avatar/ASC Avatar/旧新缓存/旧新 OnDestroyed 订阅断言在原生 Removed 回调（Garbage 前）取证；不以销毁后弱引用无效冒充订阅清理，不把复制源检查写成网络验证。
- 资源清理：CreateSP 弱共享委托；退出关闭 armed、移除两个 World handler；GI/Manager 活着时真实销毁剩余 Actor，World::EndPlay(Quit) 仅用于退出清理；Shutdown GI、DestroyWorld/context、清临时包 dirty、恢复三个原生网络加密委托并释放 GI。早退同样走析构，无空 catch。
- 已执行的静态保护：新全文与登记修改完全相符；恢复旧整个 cpp 成功；Types.h 与生产 h/cpp SHA256 保持；测试源码 UTF-8 无 BOM/原 LF/无行尾空白；源注册宏从2到3，只新增一叶；唯一候选 Attach 调用点及 Plain/Exact/1 字面契约核对；直接接口与清理顺序对照本地原生源码。
- 未执行：本新增叶编译/自动化/真实运行；第30次是本步前门禁，只证明 A9 已编译及旧回归，不证明新增 Destroy 场景。流送、Initialize 内部事务、普通 successor、私有延迟 Destroy、网络、完整 Hero/SurvivesDeath 专项仍未关闭。
- 架构图文只读核对的待办沿用 A9：补六项专项源码现状、新叶未运行及准入验证边界；本步禁止 Obsidian 写入，不宣称文档一致性完成。
- 停止点已到：三文件实际 diff/完整哈希及未验清单交回后停止，等待统筹统一构建，不自动继续流送、共享接口或 Teams 清理。

## A15 / 06-L1-T1-R1 原生 Owner 销毁时点断言校正：预检登记（2026-10-01）

- 授权：统筹已独立核对原生 SetOwnerActor -> Actor OnDestroyed -> ASC OnOwnerActorDestroyed -> World Removed -> Unregister 顺序，明确授本三文件。与 Animation 独立 DTO 测试互斥；不扩大生产或共享接口租约。
- 唯一写入者：Combatants 长期组长本人，gpt-6.1-sol / xhigh；编辑使用 apply_patch，无代理/ACL/属性改动。
- 精确三文件：Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp；AAADocs/Modules/Combatants/Module_Repair_06_Subleases.md；AAADocs/Modules/Combatants/Module_Repair_06_Validation.md。
- 唯一目标：仅将测试当前537–538的 Removed.OwnerActor == Host 改为严格 TestNull，标签为 native Owner destruction callback clears ASC Owner before World removal；不接受 Host 或 null 的宽断言。
- 只读依赖：本地原生 Actor/LevelActor/ASC；Gate32真实报告；冻结的生产、TestTypes、旧测试/夹具与全部其它新测试断言；根ledger/schedule。Owner清空原因是原生 OnOwnerActorDestroyed，不是尚未发生的 OnUnregister/DestroyActiveState。
- 真实基线：Build32 Succeeded 7 actions/41.25秒/UBA38.31秒/exit0，新DLL报告62 Success/2 Fail；本叶 Fail/1 Error，错误仅原537的 Removed Owner保留期望不等；报告DFCE3543D4F570EB551BE3EC744589EB875671844635365DB37B077D2E0ABBFC、06:40:13 UTC；UE23112已退出，238source/14保护hash保持。报告没有打印实际Owner值，不能称严格null已动态观察。
- 必须保持：CleanupBefore/After的 Owner==Host、ExpectedASC不匹配无操作、唯一一次Attach与完整Plain/Error/Exact/1、事件/通知计数、缓存/复制源/订阅、真实World/Destroy与资源清理、原两测试/夹具、生产字节全部不变。
- 验收与停止点：source只有上述两行替换；内存逆向恢复A12旧完整hash35E97151BAD47F8239F66B9C82F9A99CA9BB4EC7360792ABC49E82E0CD2745C4；原记录字节前缀保持。source静态冻结后仅追加两记录32失败/原生原因/本步实际diff与保护证据，交回最终三hash并停止，等待根审查和下一统一门禁。
- 非目标：生产/Engine修复、放宽其它断言、重写32失败历史、预判新测试成功；UE/构建/Git/资产/Obsidian/全局/代理写入；流送、内部Initialize、普通successor及Teams清理。
- 当前状态：预检已登记，实施限上述唯一source替换及记录追加。

## A15 / 06-L1-T1-R1 静态冻结交回（2026-10-01）

- 当前本步状态：唯一source校正已完成并静态冻结；两记录只追加Gate32历史失败、原生原因及本步证据。A12“未运行”保留为当时状态；当前A12已在32实跑Fail，A15严格空值新期望尚未重新编译/运行。
- 唯一source实际diff为原537–538两行 TestEqual(Host) -> TestNull(Removed.OwnerActor)，新标签 native Owner destruction callback clears ASC Owner before World removal；+2/-2行，无其它source字节变化，不使用Host或null宽断言。
- source冻结：26325字节/SHA256 75EEA3073A19EE5C2462F2DE546F82BD34EE1B90829B87876052E2444EADCE7E；本步前26352字节/35E97151BAD47F8239F66B9C82F9A99CA9BB4EC7360792ABC49E82E0CD2745C4。内存逆向唯一替换后精确恢复后者，未落盘恢复文件。
- 保持：CleanupBefore/After Owner==Host、原两测试/所有夹具、ExpectedASC、完整Plain/Error/Exact/1及全部其它断言原文。Types.h、CombatantState h/cpp、PawnExtension.cpp、ASC.cpp五文件读回hash不变。
- 原生原因：ASC SetOwnerActor订阅Owner OnDestroyed；Actor::Destroyed在RouteEndPlay之后广播OnDestroyed，ASC OnOwnerActorDestroyed身份匹配后直接清缓存Owner字段；World Removed随后发生，UnregisterAllComponents与OnUnregister/DestroyActiveState尚在后面。后者不是本次Owner清空原因。
- Gate32真实历史仍为本叶Fail/1 Error，不能称本次严格null已观察或新叶成功；报告未打印Owner实际值。源边界校正必须等待统筹下一完整构建/新DLL实跑。
- 编辑方式均为apply_patch，原记录字节前缀保留；源码UTF-8无BOM/原LF/无行尾空白、唯一逆向和实际diff静态核对完成。无UE/构建/Git/Engine/资产/Obsidian/全局/代理/ACL/属性操作。
- 停止点已到：最终三文件hash、唯一diff及未验项交回后全部冻结；不自动继续内部Initialize、流送、普通successor、网络或Teams清理。

## A16 / 06-L1-T1-V1 实际销毁证据同步与冻结（2026-10-01）

- 拆分预检：唯一目标是同步已发生的33/35真实 A15 结果，同时逐字保留32失败、原生 OnOwnerActorDestroyed 原因及全部历史追加段。唯一写入者为 Combatants 长期组长本人，gpt-6.1-sol / xhigh；精确两文件为 AAADocs/Modules/Combatants/Module_Repair_06_Subleases.md 与 AAADocs/Modules/Combatants/Module_Repair_06_Validation.md，仅用 apply_patch。
- 依赖与顺序：统筹 A16 两记录租约和冻结的 A15 测试 -> 只读核对报告及哈希 -> 更新顶部当前/追加实际证据 -> 核对历史段与保护源码不变 -> 两记录冻结交回 -> A17仅零写入预检。报告、源码、全局台账/排程均只读；无共享接口修改或新状态所有权。
- 非目标与停止点：不写生产/测试/资产/Obsidian/全局笔记，不运行 UE/构建/Git，不创建或唤醒代理；不扩大真实 Destroy 证明范围，不释放 Teams 或 B0。两记录静态核对后停止写入，最终两哈希由交回消息提供；A17不承接记录写权。
- 33实际结果：统筹完整 Editor 构建 Succeeded，10 actions/33.74秒/UBA29.06秒/exit0，新 DLL 运行65叶64 Success/1 Fail；唯一 Fail 为 Animation DTO 夹具前置，不属于本叶。报告2026.10.01-07.51.34 UTC（北京时间15:51:34），总0.8156763911247253秒，SHA256 624287915CDBC1C3E7D7D4857FF9E50973EE15D6D8374F1439CF46365B5EA4E3。
- 本叶 GGYGO.Combatants.Binding.RealDestroyRejectsCleanupReattach 在33实际 Success/0.009637400507926941秒/entries[]/0 Error/0 Warning；在35继续 Success/0.008721999824047089秒/entries[]/0 Error/0 Warning。两报告与哈希已本地只读核对。A15 冻结测试 SHA256 仍为75EEA3073A19EE5C2462F2DE546F82BD34EE1B90829B87876052E2444EADCE7E；严格末段 Owner 空值、原 CleanupBefore/After Owner==Host 及本叶其它断言均通过，没有放宽断言。
- 35实际结果：统筹完整 Editor Succeeded/6 actions/34.99秒/UBA32.04秒/exit0，仅新运行时 DLL 实际链接，不声称本次新增 UHT 或 Editor DLL 重链。报告2026.10.01-09.37.52 UTC（北京时间17:37:52），65 Success、其它计数0、总0.7469504475593567秒；SHA256 F2DFBCF244512B11EB669D29DFAAD2C21310103E9D9EDA74D098B5ED8A1718A6。本地核对65路径与33一致、全部叶0 Error/Warning。
- 全局运行证据由统筹提供：33的 UE41716、35的 UE40532 均 exit0且已退出；33的240源码/14保护及35的242源码/14保护哈希保持，35未保存资产。35原始日志49 Error=Smoke13+Damage预期34+Bake预期2，2 Warning为DDC/Python枚举重名；不把叶0错误写成全日志无诊断。
- 验收边界：本次只证明已完整 BeginPlay 的真实 Host Destroy 中旧 Extension 清理回调重绑拒绝、分时点 Owner 及现有缓存/订阅/计数断言；32失败历史与 ASC 原生 Owner OnDestroyed 清空原因继续保留。Initialize 内部重入、普通后继、同实例流送再 BeginPlay、网络、完整 Hero/SurvivesDeath 仍不由本叶证明；A17须先完成根因/接口预检，不能自行实施或释放 Teams。
- 冻结交回：两记录仅修改顶部当前段并追加本节/Validation 的 A16；原历史段逐字保留，LF/UTF-8/行尾及只读保护静态核对后交回。交回后两记录明确冻结。

## A17-R0 / 06-Binding-R0 普通后继严格诊断：实施前预检（2026-10-01）

- 本节为最新独占步骤，取代此前仅A16记录/A17零写入的授权状态；A16真实证据、A17架构候选与全部历史原文保留。生产事务、身份通知、API兼容、Busy/Deferred及B0final仍未获用户决定，不能由本步测试授予实施权。
- 唯一目标：真实公开Uninitialized通知中仅一次成功接管后，严格证明旧Detach返回后的收尾不得清掉新绑定。组长本人gpt-6.1-sol / xhigh直接实施，不创建或唤醒代理；编辑仅apply_patch。
- 精确四文件：新增Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingSuccessorTest.cpp；新增同目录GGYGOCombatantBindingSuccessorTestTypes.h；AAADocs/Modules/Combatants/Module_Repair_06_Subleases.md；AAADocs/Modules/Combatants/Module_Repair_06_Validation.md。两个新源均已Test-Path确认不存在。两记录本步前分别31564字节/SHA256 4BF262151B3FEE2A7E480358EB86784FA8BEFA986FE742EBD4B41BA3B806AC5C、51917字节/D1F52BCCDEE54B458C1C246DB6007FB9B0CCB5373A6650E9A8C6AB949D6866B1；只追加，保持原字节前缀。
- 模块/依赖：测试只请求Combatants公开Attach/Detach，读取宿主Avatar、ASC缓存Owner/Avatar和公开ActorInfo、Extension缓存及公开销毁订阅。复用冻结BindingLifecycleTestTypes.h的AGGYGOCombatantBindingTestState/AGGYGOCombatantBindingTestPawn及真实生产Extension；新Types仅只读时点快照，不新增Host/Pawn/UCLASS、权威状态或生产执行链。
- 真实前置：独占base GI/WorldContext/ComponentManager，URL明确原生AGameModeBase，InitializeActorsForPlay及真实World::BeginPlay；Host、旧Pawn A、候选Pawn C及组件有效/同World/Authority/完成BeginPlay，ASC实例/ActorInfo来源吻合，Pawn无自有第二ASC；公开Attach(A)完整建立Host/ASC/ActorInfo/Extension/销毁订阅。任一前置失败明确返回false，不能作为目标红证据。
- 案例DifferentPawnTakeover：执行Host.DetachAvatar(A)，仅A Extension真实Uninitialized回调一次调用Host.AttachAvatar(C)。回调开始必须证明旧本地缓存及ASC Avatar已空、Owner保留、C未绑定，端点仍合法；Host引用与旧销毁订阅的退出顺序只记录快照，不锁成前置，以兼容已批准的提交后通知契约。回调返回必须先证明Host/ASC/ActorInfo/Extension均已完整指C且C initialized通知恰1；没有此成功证据不执行目标最终断言。
- 案例SamePawnRebind：同样Detach(A)，仅同一真实通知一次Host.AttachAvatar(A)，以证明同对象同ASC的新绑定也不能被旧收尾误清。回调当时必须完整Host/ASC/ActorInfo/Extension指A、initialized通知恰1、旧销毁订阅仍成立；不能仅用指针相同推定成功。
- 最终严格断言：外层Detach返回后Owner仍Host；Host Avatar、ASC cached Avatar、ActorInfo Owner/Avatar/ASC及其原allocation、目标Extension均保持回调中成功新绑定；对应Host销毁订阅存在。不同Pawn时A缓存/订阅为空，C不得收到后继解绑；同Pawn时A缓存/订阅保持，C仍未绑定。尝试恰1，原A Uninitialized恰1，目标Initialized恰1，成功接管后Uninitialized恰0，所有目标仍存活。逐项正常失败，不ExpectedError/吞日志/改旧断言。
- 隔离：IMPLEMENT_COMPLEX_AUTOMATION_TEST根ProjectDiagnostics.Combatants.BindingSuccessor；仅-GGYGOCombatantBindingSuccessorDiagnostic显式开关枚举DifferentPawnTakeover/SamePawnRebind，RunTest再次严格检查开关及精确参数。无开关不枚举，不并入普通GGYGO65叶。
- 清理：每个案例独占自有Fixture；弱共享观察者一次武装且在外部Attach前解除武装。任何退出先停止观察、释放弱回调目标，再仅Destroy自有A/C/Host，GI/Manager存活期间EndPlay，GI Shutdown后Destroy World/Context、清临时包dirty并恢复GI修改的三个FNetDelegates。公开注册接口无Remove，不改私有委托；释放观察对象摘除可调用目标，剩余弱槽随自有Extension销毁，不冒称调用Remove。
- 顺序/停止点：本预检与精确基线 -> 两新增源 -> 静态全文/枚举/参数/清理及保护hash核对 -> 两记录实际diff/证据 -> 四文件明确冻结交回。需要第五文件、真实公开接管前置不能成立或需要生产接口时立即停止。未构建/运行前只记静态，不声称动态复现；统筹另安排编译与独立真实诊断。
- 非目标：外层Attach(B)覆盖、Initialize/Cancel/Cue内部、真实Destroy/流送/网络、Hero/Movement消费、K3播放关联/Guard、B0及Teams回收；不写旧六测试、任何生产/共享接口/蓝图/资产/Obsidian/全局记录，不UE/构建/Git/代理。

### A17-R0 实际源码结果与冻结交回

- 两个新源已落盘，均仅apply_patch：SuccessorTest.cpp为445行/23035字节/SHA256 56974D6ACCE519E0EC4CD08FF3C885FECA7D0850B7E1841649889AF1FB307B36；Types.h为28行/894字节/SHA256 669831243F50B54AE6FF8E29C33F5933D1CF06DC8985F85CD86AE8793B24C2A1。新源是整文件新增，无旧源diff；Types只有只读快照，没有新UCLASS/Host/Pawn、generated头或第二协调者。
- 实际完整读回逐字等于本步预期源码；UTF-8无BOM/LF/无行尾空白；Complex注册恰1、GetTests/RunTest各自检查同一显式开关，两个精确参数无默认案例；目标Attach调用点恰1且先消耗武装，外层Detach调用点恰1。未发现ExpectedError、日志抑制或catch。
- 两案例只走正常公开Host/ASC/Extension链；回调成功先验是完整新绑定+初始化恰1，最终逐项严格检查新绑定仍在及无成功后继解绑。通知前Host引用/旧订阅的退出顺序只记录快照，不锁定内部实现时点；不会把未来合法提交后通知变成前置失败。
- 观察者弱CreateSP注册，没有伪造通知；所有退出先停用并Reset唯一观察对象，再销毁仅本Fixture A/C/Host，GI/Manager保留至真实Actor/World EndPlay，后GI Shutdown/World与Context释放、临时包dirty清除、三个GI网络委托恢复。注册补发发生于武装前，不算接管事件；弱槽随自有Extension销毁，不声称私有Remove。
- 统筹最新转达用户选择已知悉：native不可中断绑定写入阶段Busy且不自动排队；提交后带身份就绪通知允许后继；项目GA取消/结束捕获原播放归属及薄扩展点由战斗组长只读细化。此选择不扩大R0四文件租约，R0不得通过拒绝正常Uninitialized回调来通过；B0独立未批准。
- 完整保护清单见Validation本节：旧六Combatants测试与Host/Extension/Health/ASC八生产文件共14个本步只读hash核对；旧A15测试保持75EEA307…，两记录原31564/51917字节前缀保持基线完整hash。新源码先静态冻结，记录追加完成后四文件全部停写，最终四hash交回。
- 未执行UHT/Editor构建、真实诊断枚举或RunTest；只能证明静态源码和保护，不称两例动态红/通过、普通65运行不变或清理已实证。独立运行需统筹使用-GGYGOCombatantBindingSuccessorDiagnostic与ProjectDiagnostics.Combatants.BindingSuccessor另行安排。
- 停止点：A17-R0四文件冻结；未写任何第五文件、旧测试、生产/API/蓝图/资产/Obsidian/global，未UE/构建/Git/代理。新增诊断及未验证状态的局部架构笔记仍待独占租约，不称文档同步已完成；Initialize内部、native Busy、K3、流送/网络、Teams回收均未由R0关闭。

## A17-R0-V1 / 06-Binding-R0-V1 第36次真实证据同步：实施前登记（2026-10-01）

- 统筹已接受两记录只读预检并登记独占租约；唯一写入者Combatants长期组长本人，gpt-6.1-sol / xhigh，仅apply_patch。唯一目标是顶部当前状态及追加第36次真实严格结果，不修改R0测试断言或任何生产。
- 精确两文件：AAADocs/Modules/Combatants/Module_Repair_06_Subleases.md、AAADocs/Modules/Combatants/Module_Repair_06_Validation.md。入口完整基线已重新读回匹配：Subleases39050字节/A4B7090F3F2B41DDFF291A24A4944698E9C5036622804FF42021B5AC545834EA；Validation61721字节/5BF7261A85C858CB61E4906036CD4A99032F38DABCBF82AA48F8A8000F345BB2。
- 只读依赖：36两报告及统筹36构建/日志/进程/历史保护证据、当前ledger/schedule、冻结R0 cpp/Types与A15源。报告本地读回hash为CE53E5DB523A0E10ABDB422D69BB640AE4CA0D89C5C3BD7DB6030ABD3D3223E0和9C28CF4DB61E8909EF2908CD24479810738FC29E845921B4E249DCE3A3508E46；源码只读，不碰K4-I1/P1-T1在途范围。
- 验收：仅替换原第三行当前段、尾部追加本预检/真实证据；移除本步全部追加并恢复原当前段后，完整文本及SHA256须精确恢复入口两基线。A16/R0静态与32严格失败全部原文保持；12错误须区分DifferentPawn8与SamePawn4，明确全部前置及回调完整接管实际成功、额外Uninitialized与Extension残留差异。
- 顺序：入口核对 -> 本登记 -> 顶部真实状态/追加36结果 -> 两记录全文差异与逆向核对、三只读测试hash -> 最终两hash交回并冻结。普通70和exit0不能代替R0通过；248源码/14保护保持仅引用36窗口历史，不写当前全树静止。
- 非目标/停止点：不改source/test/types/生产/API/Guard/Teams/Obsidian/第三文件/global/资产，不UE/构建/Git/代理；不实施用户已选绑定事务或关闭native内部/流送/网络/K3。完成两记录后停止写入，不自动下一步。

### A17-R0-V1 第36次实际结果与冻结交回

- 本地只读报告：Saved/AutomationReports/ModuleRepairCombatantBindingSuccessor_20261001_36/index.json，2026.10.01-12.24.43 UTC（北京时间20:24:43），SHA256 CE53E5DB523A0E10ABDB422D69BB640AE4CA0D89C5C3BD7DB6030ABD3D3223E0。实际两叶2 Fail/12 errors/0 warnings，其它计数0，总0.1332578957080841秒；没有ExpectedError或断言修改。
- DifferentPawnTakeover实际Fail/8 errors/0 warnings/0.12345349788665771秒。公开Uninitialized内一次Attach(C)已完整成功、Initialized恰1；旧Detach返回后Host Avatar/ASC cached Avatar/ActorInfo Avatar清空，C Extension缓存与Host销毁订阅也清空，额外C Uninitialized1，目标成功后解绑1，事件5而非4。Owner、ActorInfo Owner及ASC来源仍保留，不能写成整个ASC/ActorInfo对象被清。
- SamePawnRebind实际Fail/4 errors/0 warnings/0.009804397821426392秒。一次Attach(A)完整成功、Initialized恰1；旧收尾清Host/ASC cached/ActorInfo Avatar及A销毁订阅，A Extension仍持该ASC，形成不一致。没有额外目标解绑；不能把它与DifferentPawn的缓存也被清/额外通知混为同一结果。
- 全部错误均在最终保持断言，真实GI/World/Actor BeginPlay、初始Attach、回调前置及完整接管成功门禁没有失败；合法普通后继已进入目标断言，不是夹具前置失败。原R0“未编译/运行”、静态推导是当时历史，逐字保留；当前由本节真实2 Fail更新，不抹红或标已修。
- 正常70与R0独立：本地正常报告Saved/AutomationReports/ModuleRepairGate_20261001_36/index.json，12:23:19 UTC（北京时间20:23:19），70 Success/其它0/0.8348187208175659秒、全部叶errors/warnings0，SHA256 9C28CF4DB61E8909EF2908CD24479810738FC29E845921B4E249DCE3A3508E46；A15继续Success/0.009493499994277954秒/0错误警告。正常70不能关闭独立R0两失败。
- 构建/日志/全局保护由统筹36历史门禁引用：完整Editor Succeeded/7 actions/94.44秒/UBA80.76秒/exit0，UHT7.822312秒但0 generated files写入，实际链接新运行时DLL，不声称Editor DLL重链。R0原日志27 Error=启动Smoke13+12断言+2Fail汇总，2 Warning为DDC/Python；正常原日志49 Error=启动Smoke13+Damage预期34+Bake预期2，2 Warning同类。两UE exit0且均已退出、248源码/14保护在36构建及两次运行保持、无资产保存；exit0不等于R0通过。
- 以上248/14只属于36窗口历史；当前共享ASC K4-I1与Movement P1-T1另有在途写入，不声称全树静止、不验证或撤销他人合法变化。K4-I1仅身份底层，不是绑定行为已修；本会话不写生产/接口、测试断言、Guard/K3或Teams。
- 本步只有两条顶部当前段替换及尾部预检/本结果追加；原A16/R0/早期历史整文保持。删除本步追加并恢复原当前段后，完整文本/hash须精确恢复A4B7090F3F2B41DDFF291A24A4944698E9C5036622804FF42021B5AC545834EA与5BF7261A85C858CB61E4906036CD4A99032F38DABCBF82AA48F8A8000F345BB2。R0 cpp56974D6A…、Types66983124…与A15 cpp75EEA307…继续只读冻结。
- 两文件静态全文/逆向/hash核对后明确冻结交回，最终两hash及实际差异由交回消息提供；仅apply_patch。没有第三文件/源码/测试/生产/API/Obsidian/global/资产写入，没有UE/构建/Git/代理；不自动任何下一步。

## Combatants-HostProductionRouting：实施前登记（2026-10-03）

- 统筹已接受有限预检并授权四文件：`Source/GGYGO/Combatants/GGYGOCombatantState.h`、同名 `.cpp`、本记录和 `Module_Repair_06_Validation.md`。唯一写入者为 Combatants 长期组长本人，当前 `gpt-6.1-sol / ultra`；仅 apply_patch，不创建或唤醒代理。
- 基线：`Saved/ValidationRecords/CombatantsHostProductionRouting_LeaseBefore.json`；四项 bytes/hash 已实际核对全部一致。h 4370/A83D67A5…，cpp 8950/6B53885E…，本记录44757/8CEF60DC…，Validation69165/F5DBC32E…。冻结 Host 接口定义结果见 `CharacterHostInterfaceDefinition_Result.json`。
- 唯一目标：Host 实现无状态 `RequestAvatarBinding` 的 Initialize/Release/Refresh 路由；旧 Attach/Detach/Sync、销毁和 EndPlay 复用唯一协调链。ASC唯一负责ActorInfo/Binding/Publish执行，Host选择及发布Avatar/订阅，Extension拥有本地opaque H；不新增绑定号、ASC状态机或原生执行器。
- 只读依赖：ASC三Try/Publish/C1a/C1b/认证查询、BindingTypes、Extension四阶段/当前槽、冻结Host请求/步骤历史接口，以及原R0/A15和现有派生宿主。已捕获共享七源码及原三测试的只读hash，完成时核对保持。
- 顺序：本登记 → h接口与宿主资源句柄 → cpp唯一请求路由与原资源清理/发布 → 旧入口收口 → 有限静态复核与两记录实际证据 → 四文件交回冻结。Character生产入口/Getter/回放切换由其组长后续租约执行；全部生产链冻结后由统筹统一编译和必要UE冒烟。
- 不变量：每次入口复制原端点/Context/H，原销毁订阅属于Host所持H；普通Ready/Released可当场完成后继，旧栈Stale停止且不清后继。实际原生Busy不排队。发布查询不要求Ready，撤出后的cleanup查询不依赖空槽/GetterReady。Cue先于ASC Clear；真实Steps保留原失败及已提交/本地改变事实。
- 失败策略：跨Host由外层显式旧释放→核对→新绑定；新绑定失败只清仍属于本请求的部分装配，不恢复旧Host。未提交原生部分变化若无法由公共契约证明精确清理权限，立即记录交回，不凭指针或旧Clear兜底。
- 验收：有限接口/调用链/步骤载荷/原资源重检/精确退订静态复核；用户最新只要求统筹统一编译＋必要冒烟，不新增夹具或严格矩阵。第36次R0原2 Fail/12 errors及其它失败原文保留，没有新结果不记通过。
- 非目标/停止点：共享ASC/GA/Extension/Teams/接口源码、原测试、资产、网络、Saved、Obsidian与全局文档均只读；无Build/UE/Git权限。第五文件、新政策或无法证明的原生清理权限立即停止；四文件交回即冻结，不自动续写。

### Combatants-HostProductionRouting：实际产出与冻结交回

- 实际只修改登记四文件，均由组长本人 apply_patch。h 新增 native Host 接口继承/override、三个操作与唯一选择协调、借用 Extension opaque H/ASC Context/Extension 弱引用；cpp 的 Attach/Detach/Sync、Pawn 销毁与 Host EndPlay 走同一请求链。未新增权威 Binding/Operation/计数器、ASC执行器、队列或帧调度。
- 原端点校验固定为 ExpectedHost==this、ExpectedASC==构造默认子对象、ASC组件 GetOwner()==this；不会从可变ActorInfo Owner选择Host。Initialize复制请求并选择单一公开ASC准入，Install后发布Host Avatar/原销毁订阅，再由真实ASC Dispatching桥接Ready；发布查询不以Ready为前置。Refresh只接受曾Ready的原H，提交后更新借用Context并重发带身份Ready。
- Release先撤出原H本地资源，再用原Context执行Cancel/Input/Cue/Clear，Host只退订和清除自己原H，最后真实Publish桥接Released。Release不要求Ready或允许新绑定；Closed Extension实际返回/本地改变历史保留，不冒称通知了观察者。普通Ready/Released回调可立即接管；每个旧栈重检原H、完整Context及原槽，后继成立即Stale停止，旧Detach无无条件清空尾部。跨Host仍由外层显式旧Release→核对→新Initialize；失败不自动恢复旧绑定。
- HostResult只返回本次真实Step历史；ASC/Local/Input各Step仅写其对应载荷。失败保留已提交和本地改变事实；安装失败的仍属本次提交/原H部分装配有精确撤出、Clear及Released义务消费，不能由清理成功把原失败写成成功。每个发布桥仅持栈局部精确DelegateHandle，作用域结束移除该槽，不RemoveAll或伪造Broadcast。
- 源码有限复核完成：h 135行/5936字节/SHA256 `86F7C6CEA874DB25AD5073EFEF5367DCC4464CB630E1997D883D20D1C4280903`；cpp 1059行/41350字节/SHA256 `10E4FE163FC93616EBBD47D823549AF288F608F8562AC795689644FE9BC54800`。忽略注释/字符串后括号计数平衡，UTF-8无BOM、无行尾空白；这不是C++/UHT编译证据。未发现直接旧ActorInfo写入、旧Extension Initialize/Uninitialize、RemoveAll或Host自行Broadcast ASC Notice。七共享源及R0 cpp/Types/A15三测试hash与入口完全一致。
- 精确停点：ASC `ValidateAvatarBindingActualSnapshot` 对Owner/Avatar正在Destroy拒绝，C1a及PreserveOwner Clear继承该准入；Host可撤出原本地H，但没有公共权限保证真实Destroy时完成原生Cancel/Clear。ASC native Init的Super写入后可能失败且不提交/不给Receipt；Host不得用失效Context、指针或旧Clear猜测其部分原生状态的清理权。当前显式失败/诊断，不声称“所有失败均原生无绑定”。共享ASC必须由统筹/其所有者决定并另租约处理，本步不写第五文件、不切换Clear模式兜底。
- 文档核对已只读查看Obsidian计划蓝图和Combatants结构：仍记旧Detach路径及“Host未实施”。需由统筹独占同步Combatants结构/Canvas、角色初始化流程、Character四阶段接线及实施状态，记录本次源码已落盘但未编译、Character迁移待办和上述停点。本租约未授权Obsidian/全局入口，未冒称已同步。
- 本次未运行Build/UHT/UE/自动化/严格R0，未新增夹具、未修改旧断言。第36次R0 2 Fail/12 errors、旧A15通过及Gate53 Extension证据仅保留为各自历史，不能作为新Host验证。Character后续适配后，统筹按用户最新选择安排统一编译＋必要UE冒烟。四文件交回即停写冻结；GameFeature合法在途范围不属于本次冻结，不宣称全树静止。

## HostCommittedCleanup-H1：实施前登记（2026-10-03）

- 统筹已接受零写入预检turn `01a1023b-b88e-7451-bd9d-b2d4e27628c4`并授权直接实施本纯技术消费者原子。唯一作者Combatants长期组长，`gpt-6.1-sol / xhigh`，取消代理；唯一写入Host cpp、本文和06 Validation三文件，先登记再写生产。
- 入口租约 `Saved/ValidationRecords/HostCommittedCleanup_20261003_LeaseBefore.json` 全部匹配：cpp 41350/10E4FE16…，Subleases51237/FD2E0894…，Validation75261/BD2B6512…。只读Host h5936/86F7C6CE…、ASC h40271/40535C42…、ASC cpp171437/CAD19824…亦匹配；ASC两个根接受JSON仅证明有限静态接受未编译。
- 唯一目标：Release输入清理前检查及Initialize已提交失败收尾消费 `CheckAvatarBindingCleanupContext`；原Owner/ASC宿主Closing或Host本次生命周期关闭时明确 `ClearActorInfo`，存活持久宿主正常解绑保持 `PreserveOwner`。清理拒绝不换模式重试；ASC唯一判原来源及写入，Host仅自身资源/端点/模式，Extension仍唯一掌本地资源/通知。
- 精确接缝：Host cpp `InitializeAvatarBinding` 内 `CleanupOwnCommit`、`ReleaseAvatarBinding` 的输入前检查/纯原资源query/Clear请求。仍固定原H/完整Context/端点/opaque槽，允许有效且已分配的原Actor处于Destroy/EndPlay；不绕过对象销毁/GC/无效ASC安全边界，不把Revoked清理资格授给新Init/Refresh/Ready。
- 顺序：登记→两方法消费者修改→有限读回/范围diff/保护检查→两记录当前及本原子实际结果→三hash交回并明确冻结。验收断言为原已提交清理可达、两Clear模式显式且无重试、普通解绑Owner保留、Busy/真实历史/精确退订/Closed结果保持、ABA/不同Pawn/Refresh后继隔离。仅静态，不开测试/矩阵/夹具，编译和必要UE冒烟由统筹。
- 非目标/停止点：H2及owner-only失败Init、Host h/Types、ASC/Extension/Hero/Input/Teams、Obsidian/资产/Saved/全局文档只读，不Build/UE/Git/代理。需要第四生产文件、新政策或具体接口缺口即停点交回，不扩调查；本三文件冻结后H2必须另租约。

### HostCommittedCleanup-H1：实际结果与冻结

- 生产差异严格限cpp两方法：`InitializeAvatarBinding` 内 `CleanupOwnCommit` 与 `ReleaseAvatarBinding`。已提交失败收尾仅用本次 `Initialized.CommittedContext`，Release仅用入口原 `Request.ExpectedContext`；两处工作Context检查改为ASC唯一 `CheckAvatarBindingCleanupContext`。清理查询Succeeded可消费Current/Revoked原记录；未让Init/Refresh/Ready使用清理资格。
- 两处Clear发出前直接选择：Host本生命周期已关闭、原Host/ASC组件宿主正在Destroy，或ASC验证过的原Owner正在Destroy时为 `ClearActorInfo`；存活持久宿主普通解绑为 `PreserveOwner`。只发出该模式一次，未按拒绝换模式、自动回滚或另走旧Clear。Owner读取只用于已授权原来源的模式选择，不创建ActorInfo快照/Proof/状态或执行器。
- 原资源query不依赖新工作准入、Ready或Withdraw后Installed。原Host/默认ASC/组件Owner端点再次核对，原H/完整Context/Extension/opaque槽及原选择保持；有效已分配原Actor可处于Destroy/EndPlay，对象销毁/GC、无效ASC安全边界保持。Release的纯本地失败收尾仍允许ASC失效时撤自身H/通知义务；没有给失效ASC原生权限，不把本地成功冒充原生成功。
- cpp 1075行/42636字节/SHA256 `8514BDF22B5C66A2A2FBE481B3B8F164F5BEB64B0F4BF34E214C1ECFEDDD0187`。内存范围diff确认仅上述两方法改变，方法集合、文件前部及其它方法原文一致；Init未commit失败前段及Install/Ready后段原文一致，`TryCleanupFailedAvatarActorInfoInit`调用仍0。两处清理查询、两处显式ClearMode已有限读回；忽略注释/字符串括号计数平衡、无行尾空白。以上不是C++/UHT或动态证明。
- Host h `86F7C6CE…`、ASC h `40535C42…`/cpp `CAD19824…`在本次核对时与入口匹配；hash仅为当时事实，不把后续另租约ASC输入变化当作Host停点。原Busy/输入无回调边界、真实步骤历史、精确DelegateHandle退订、Closed Extension真实通知、原H/Context后继保护相关机制没有新执行链或新增状态。
- 只读核对Obsidian当前Combatants结构：HostProductionRouting已同步，但“Destroy公开权限停点”尚未反映ASC新接口及本H1消费者，H2仍需接力。待源链冻结后由统筹独占同步Closing完整Clear/存活PreserveOwner、已提交清理资格及未commit消费者状态；本租约不写图文，不称同步完成。
- 三文件明确冻结交回，最终三hash另由消息提供。未运行Build/UHT/UE/Git/自动化，未新增测试/矩阵/夹具，R0历史2 Fail/12 errors未重跑、不改通过；H1只有源码消费者和有限静态证据，统一编译＋必要UE冒烟仍由统筹。H2、Character/Health/Base/Hero/Teams、资产/网络及最终验收仍分别开放，不自动续写。

## HostFailedInitCleanup-H2：实施前登记（2026-10-03）

- H1真实turn `01a1024d-9039-77a2-a05e-91af572799c9`已completed/冻结并获统筹有限静态接受，证据 `HostCommittedCleanup_20261003_RootAcceptance.json`。本原子由Combatants长期组长直接实施，`gpt-6.1-sol / xhigh`，无代理；唯一写入Host cpp、本文及06 Validation三文件，先登记再改源码。
- `Saved/ValidationRecords/HostFailedInitCleanup_20261003_LeaseBefore.json`实际六项bytes/hash匹配：cpp42636/8514BDF2…、Subleases56298/E4E1938D…、Validation79349/161D6955…；Host h5936/86F7C6CE…、ASC h40271/40535C42…/cpp171437/CAD19824…只读。H1方法/共享签名冻结，不借同文件租约重写H1。
- 唯一目标与接缝：`InitializeAvatarBinding`未commit失败返回，以及`InitializeOwnerActorInfo`失败返回。完整Try返回后，非commit且原Result.Operation有效才请求ASC `TryCleanupFailedAvatarActorInfoInit`；不假定Issued就有Proof，缺Proof/后继写入按实际拒绝保留。原失败Step及顶层Outcome/Reason不被清理成功覆盖，实际清理另记ActorInfoClear/ASCResult；owner-only仍false，分别诊断原失败/清理结果。
- 原清理query独立于新工作准入：固定原Host/默认ASC/组件Owner、原选择、入口空Host H和原本地槽；Avatar请求同时固定原Pawn/Extension端点。允许仍有效已分配的Closing对象，不以Ready/工作准入为前置。owner-only无Avatar本地安装资源，只校验其原Host/ASC/选择/空H，不创造Pawn/Extension资源。ASC唯一掌原actual写入Proof，Host不读当前Context或ActorInfo制造来源，不新增Proof/计数/状态/执行器。
- 顺序：登记→两失败分支消费→有限读回/范围diff/保护→两记录当前及本结果→三hash交回冻结。断言为原失败保留、无Operation不调用、缺Proof不兜底、后继写入隔离、无rollback/重试/Commit/Receipt/Notice/Ready、原Busy完整返回保持。只静态，不加矩阵/夹具，统一编译＋必要冒烟由统筹。
- 非目标/停止点：H1、正常Bootstrap/Replace准入、Host头/Types、ASC/Extension/Hero/Input/Teams、旧测试、Saved/Obsidian/global/资产只读，不Build/UE/Git/代理。需要第四生产文件/新共享接口/政策即具体停止交回；本三文件冻结后不自动继续源码或图文。

### HostFailedInitCleanup-H2：实际结果与冻结

- 仅cpp `InitializeAvatarBinding` 未commit失败返回段及 `InitializeOwnerActorInfo` 失败返回段变化。完整原Try返回后，非commit且原Operation有身份时才调用 `TryCleanupFailedAvatarActorInfoInit(Initialized.Operation, FailedInitCleanupScope)`；无Operation不调用。ASC失效不能调用时有明确诊断且不生成假Step；Issued但无Proof、Proof退休或后继实际写入由ASC返回真实拒绝，不清当前、不重试/rollback。
- Avatar原清理query固定入口Request Host/默认ASC/组件Owner/Pawn/Extension、原选择及入口空H/本地槽。owner-only原生Init无Avatar安装资源，仅固定原Host/ASC/选择/空H，不虚构Extension记录。两个query都不调用工作准入/Ready/Installed、不拒绝有效已分配原Actor的Closing，不读取当前Context/ActorInfo构造Proof；ASC仍唯一验证原actual写入来源并控制完整Busy原生窗口。
- Avatar原ActorInfoInit Step和顶层Outcome/Reason先保存，清理返回仅追加实际ActorInfoClear/ASCResult，未SetASCFailure或改写顶层失败。owner-only使用栈局部失败历史记录两个真实步骤，分别诊断原失败及清理Outcome/Reason/bCommitted，结束仍false；该栈历史不是新状态或权限。没有Commit/Receipt/Notice/Ready，也不把物理清理Succeeded升级原Init。
- cpp最终1143行/46732字节/SHA256 `9EF5B5E74AD25EF7E70DA05E0A99CAF7F12CB80D9A8C61C2B091924DE05AB959`。有限范围对比仅两方法；H1已提交CleanupOwnCommit连同Install/Ready后段和完整Release方法逐字保持，其它方法和方法集合保持。清理调用恰2、两个query无当前Context/ActorInfo读取及工作/Ready门禁；实际失败分支读回、括号计数平衡、UTF-8无BOM/无行尾空白。仅静态，不是C++/UHT或动态证明。
- Host h `86F7C6CE…`、ASC h `40535C42…`/cpp `CAD19824…`在本次核对时与入口匹配，未修改共享/头/Types。正常Bootstrap/Replace选择与成功发布保持，无新增依赖、权威Proof缓存、计数、执行器或调度器。原nativeBusy/完整返回和ASC后继写入退休原Proof机制继续由其唯一所有者执行。
- ObsidianCombatants结构已只读核对，仍写旧Destroy及未commit原写入公开权限停点；应在源链冻结后的独占文档步骤更新为ASC接口及H1/H2消费者已落盘但未编译/冒烟，保留具体运行未验，不冒称根因动态验收完成。本租约未改图文。
- 三文件明确冻结交回，最终三hash另由消息提供。未Build/UHT/UE/Git/自动化，未新增测试/矩阵/夹具；R0最近真实历史2 Fail/12 errors保持，旧A15/普通回归不代表本版。统一编译＋必要冒烟、其它消费者/Teams、图文、资产/网络仍由统筹分别排程，不自动继续源码或图文。

## HostLifecycle-H3：实施前登记（2026-10-04）

- 统筹已接受零写入预检turn `01a1029b-a704-70f2-bc05-f5170a6baf8c`并授权直接实施。唯一作者Combatants长期组长，`gpt-6.1-sol / xhigh`，无代理；唯一写入Host h、Host cpp、本文、06 Validation四文件，两记录先登记再写源码。入口 `Saved/ValidationRecords/CombatantsHostLifecycleH3_20261004_LeaseBefore.json` 四项实际全匹配：h5936/86F7C6CE…、cpp46732/9EF5B5E7…、Subleases61472/BC5A73A7…、Validation83585/F1E04FC2…。ASC/Extension/Host接口仅只读。
- 根因证据来自统筹已核对的UE原生调用链：pre-BeginPlay Destroy不保证EndPlay，Destroyed先RouteEndPlay再ReceiveDestroyed/OnDestroyed；Host已在PostInitializeComponents建立owner-only或Avatar ActorInfo，现只有EndPlay收尾且无H只Invalidate元数据。不能让Teams重建Host清理职责；本组未独立读取该引擎源码，不冒称引擎实测。
- 唯一目标：新增Destroyed override与唯一私有 `CloseAvatarBindingLifecycle(EntryPoint)`，两个入口均在Super前调用。先关闭既有 `bAvatarBindingPermitted`，再捕原Host/默认ASC/完整Context/H/selection；重复入口在捕获前返回，不重捕后继，不把关闭标记作为清理成功证据。真实BeginPlay重开原文保持。
- 接口冻结及责任：ASC唯一认证原Context/原生Clear/Receipt；有H只消费已冻结Release/H1/H2并从真实步骤找本次Clear Commit；无H用原Context cleanup认证及纯原Host/默认ASC/组件Owner/原selection/空H查询，显式一次ClearActorInfo，保留真实结果/Receipt并可发布真实ASC Clear Notice，无伪造Extension通知。最后仅Invalidate入口原Context或本次真实Clear Commit；Invalidate不等于物理Clear。
- 顺序/断言：两记录登记→h/cpp生命周期接缝→有限读回/范围diff/重入核对→两记录实际结果→四hash交回冻结。检查关闭先于外部调用、重复不重捕、H路径不重写、owner-only真实Clear/发布、失败与Busy保留、无getter追认后继/自动重试/新状态或执行链。生产仅生命周期方法与声明/标记注释；记录仅当前段及尾部追加，历史失败保留。
- 非目标/停止点：ASC/Extension/Host接口/Types/Teams/Hero/GA/旧测试/资产/引擎/Saved/Obsidian/global只读，不Build/UE/Git/代理，不新增矩阵/夹具。需要第五文件、新共享接口或业务政策即具体停点交回。统一编译＋必要UE冒烟由统筹安排；源码冻结后不自动续写图文，H3不释放Teams。

### HostLifecycle-H3：实际结果与冻结

- Host h新增protected `Destroyed()` override、private `CloseAvatarBindingLifecycle(const TCHAR*)`声明及既有标记注释；cpp仅替换EndPlay收尾并新增Destroyed/Close。两入口均先Close再Super；Close在关闭标记已为false时于所有快照前返回。首次先置false，再捕原Host/ASC/selection/Release请求与H；有H使用原请求的完整Context，无H捕原ASC已提交Context，不以当前不同Binding代替原H来源。真实BeginPlay重开和所有H1/H2方法逐字保持。
- 有H只发原 `RequestAvatarBinding(OriginalRelease)`，原Busy/失败及所有实际Step原样保留；仅从本次历史 `ActorInfoClear.bCommitted` 找自己的Commit供退休。无H先由ASC `CheckAvatarBindingCleanupContext(OriginalContext)`认证，纯query固定原Host/默认ASC/组件Owner/原selection/空H及已关闭准入；query无工作/Ready/Installed门禁和Context/ActorInfo读取，不作为原生权限。
- owner-only显式一次 `ClearActorInfo`真实事务，实际返回另记ActorInfoClear/ASCResult；仅自己的bCommitted可替换退休Context，包括提交后Outcome变Stale。Succeeded且commit后使用原真实Receipt调用ASC Publish并记真实PublishNotice返回，没有Extension H/通知/桥。Check拒绝、query失效或ASC失效不伪造Clear Step；真实Try/Publish失败及Busy不改为成功、不换模式/重试/排队。
- 最后只请求Invalidate原入口Context或自己的真实Clear Commit，不读取回调后的当前Context追认来源。元数据退休Accepted与清理历史独立，失败日志包含入口、原Host/ASC/选择/H有无/Binding/Write、实际Outcome/Reason/NativeReason/Steps及独立退休结果，未把Invalidate当物理Clear。原清理未成功时仍未闭合；重复入口不补清、不生成新成功结果或权威状态。
- 源码有限证据：h138行/6156字节/SHA256 `6C80F72921443B2CE1EC6BCA1C3FB8FEA423FF390E7504B9D3828FFE532AFC1A`；cpp1255行/51286字节/SHA256 `E36A2495F0AD208D164B5C9BED1D873941CDC1900A984DCCD0E1D42C7EA06E3A`。内存范围diff仅EndPlay改变、Destroyed/Close新增，无方法删除；cpp生命周期前部与GetLifetimeReplicatedProps起整段逐字一致，头严格只上述三编辑。两Close入口均在Super前、guard/关闭均在捕获前；无外调后Context getter、无伪造本地通知。括号计数平衡、UTF-8无BOM/源码无行尾空白，仅静态，不是编译或动态证明。
- 六项共享只读hash在本次核对与入口一致：ASC h40535C42…/cppCAD19824…、Extension h48AC44EF…/cpp69CFB9F4…、Host接口h84B989A6…/cppEB22E540…。仅当时事实，不阻塞后续独立输入租约。无新依赖/循环、权威Proof/缓存/计数/清理成功状态、资源执行链或调度器；唯一Close仍归原Host生命周期，ASC掌原生权限、Extension掌有H本地义务，无需拆出第二所有者。
- 两记录仅当前第三行及尾部H3预检/结果追加，旧正文前缀保持；本文无行尾空白，本Validation原有10处行尾空白逐字保留，未借本租约整理历史。曾有一次只读共享hash命令的PowerShell管道语法错误，修正为数组输出后成功，未写文件/新增脚本。
- Obsidian当前结构/Canvas已只读核对：H1/H2及Gate55/56已同步，但Host节点与接口表仍只有EndPlay/销毁回调概述。需统筹在源链接受后的独占图文步骤补Destroyed/pre-BeginPlay、唯一关闭先于Super、owner-only真实Clear/Receipt及Busy/失败边界，标为源码H3而非运行通过；本租约没有图文写权，未称已同步。
- 四文件明确冻结交回，最终四hash由消息提供。H3未Build/UHT/UE/Git/自动化，无新测试/矩阵/夹具；Gate55/56真实历史未链接DLL（Gate55 UHT生成33文件，Gate56仍有Hero三个旧调用），R0原2 Fail/12 errors未重跑。统一编译＋必要冒烟、图文、Teams及资产/网络由统筹分别排程；不自动继续源码，不宣称全树静止或真实Destroy验收完成。

## HostRefreshCallerQuery：实施前登记（2026-10-04）

- 统筹有限接受根因并授新的三文件精确写权：Host cpp仅 `RefreshAvatarBinding::OriginalScope`、本文、06 Validation。Combatants长期组长直接实施，`gpt-6.1-sol / xhigh`，Fast默认关闭，无代理。先登记两记录再改生产；入口实际cpp51286/E36A2495…、Subleases68019/9EA51524…、Validation90364/F0EE8AC9…与前次冻结匹配，不恢复H3头/生命周期范围。
- 原失败严格保留：Gate57 UE40416 `Saved/Logs/GGYGO_Gate57_Smoke_20261004.log` 18:16:15真实BP_GameMode_C/Entry/单Pyrios Possess，Refresh Operation3/Binding2/Write2/Stale CallerInvalidated/Steps1；18:16:55StopPIE，Release Operation2/同Context/Stale CallerInvalidated/Steps3，metadata Accepted1不是物理Clear。统筹另交回18:29:51～18:30:15同场景再次复现；旧IMC配置拒绝已消失，不将其作为本次绑定根因。后一次证据为统筹交回，本组未运行UE。
- 根因及唯一责任：Host Refresh query调用Extension Installed，而该查询进一步认证ASC已提交快照；ASC原生Refresh前已合法退休旧快照，原生返回后、Commit前重调query，于是正常调用被误否定为RequestContextExpired。失败退出保留旧Context为Revoked且无旧快照来源，后续Release cleanup认证失败。ASC独占actual/operation/Commit与Busy；Host query只认自己的原Context/H、端点和opaque本地槽，不能在ASC原生暂态重新索取已提交资格。
- 唯一修改接缝：OriginalScope保留原Host工作准入及 `IsOriginalAvatarResource(Request)` 的完整Context/H/Extension身份，追加原默认ASC/组件Owner及原Pawn/Extension端点和对象销毁flags核对；用 `GetCurrentLocalAbilitySystemResource().HasSameResource(Request.ExpectedResource)`替换Installed查询。getter仅比较入口原槽，不接纳/保存后继，不授原生权限。原ASC Try/Commit结果、提交后Host Context赋值及真实Receipt发布原文保持。
- 分阶段：本登记→cpp单lambda→有限范围diff/原query与失败及提交尾部读回→两记录实际结果→三hash冻结交回。断言为query无ASC Context/Identity/ActorInfo/Ready/Installed认证，原Context/H及端点/槽不符仍拒绝，所有外层入口资格/Busy/真实Steps/自身Commit/Receipt机制不变。无共享接口变更、状态/Proof/缓存/清理执行器或输入政策改变；接口冻结无需其它模块写入。
- 非目标/停止点：Host h、Release/H1/H2/H3、ASC/Extension/Host接口、Hero B1、输入、UE/GAS库、资产/测试/Obsidian/global/Saved只读，不Build/UE/Git/代理或新矩阵。Hero B1独立源码租约及全树其它在途不属本冻结。需要OriginalScope之外源码或新接口立即停点交回；统一编译＋同Entry必要冒烟由统筹，源码有限核对不能称原问题闭合。

### HostRefreshCallerQuery：实际结果与冻结

- 唯一生产差异为 `RefreshAvatarBinding::OriginalScope`。保留原Host准入及 `IsOriginalAvatarResource(Request)` 对完整Context/H/原Extension/ASC/Pawn身份的核对；纯读原ExpectedASC/ExpectedPawn/ExpectedExtension，确认Host默认组件、ASC组件Owner、Extension Owner及对象销毁flags；原 `GetCurrentLocalAbilitySystemResource().HasSameResource(Request.ExpectedResource)`比较替换Installed。没有ASC Context/Identity/ActorInfo/Ready/Installed认证，不持有新状态或把getter当前槽作为来源。
- 新query跨ASC自身合法暂态只证明原调用方范围；ASC仍在原Try内验证原operation/actual、控制完整Busy窗口并决定Commit。方法入口的Ready要求、Request完整复制、ASCResult/Steps及失败处理、提交后Host只取本次Refreshed.CommittedContext、原真实Receipt发布原文保持；回调若撤原槽或换opaque后继，原query仍false，不采纳后继/排队/重试。未扩生命周期权威或改输入政策。
- cpp1261行/51738字节/SHA256 `57D5279EA4F7DED9B971561DF77567E058B99DB3882ECE549BC1F13E63B8F883`。内存方法diff只Refresh，方法集合相同；逐字替换校验确认差异仅该lambda，方法入口和Try/Commit/Receipt尾部及所有其它方法保持，Release/H1/H2/H3没有改。实际lambda有限读回，无禁用资格读取；源码UTF-8无BOM/无行尾空白，括号180/180及787/787平衡，仅静态非编译证明。
- 七项只读hash核对时与入口保持：Host h6C80F729…；ASC h40535C42…/cppCAD19824…；Extension h48AC44EF…/cpp69CFB9F4…；Host接口h84B989A6…/cppEB22E540…。仅当时事实，不宣称Hero B1或全树冻结。没有新增include/接口、循环依赖、权威Proof/缓存/计数/执行器/调度器或清理路径；原native失败诊断及metadata不等于Clear仍保持。
- 两记录只更新第三行当前段、尾部本原子登记/结果，旧正文前缀逐字保持，R0和两次真实生产失败不改通过。Gate57编译及18:06:35单叶成功属于修正前DLL；18:16及统筹交回18:29:51～18:30:15生产失败仍是本修正验收基线。H3有H的NativeReason0默认值不被本步修改或用作物理Clear证明，Release实际Steps须由后续证据判断。
- Obsidian结构/Canvas已只读核对：H3与Gate57状态已同步且明确Host真实换绑未验，但没有本次Refresh query根因/源码修正版及两次生产失败。须统筹源链接受后的独占图文接力记录“query只核原端点/槽，ASC唯一认证”，修正版未编译/未冒烟及原失败保留；本租约未写图文/global。
- 三文件明确冻结交回，最终三hash由消息提供。没有Build/UHT/UE/Git/自动化、测试/新矩阵/夹具或第四文件写入，无代理；修正版根因尚未动态关闭。统筹待源码写入者冻结后统一编译＋同Entry/单Pyrios Possess与StopPIE必要冒烟，核实际Refresh Commit/Receipt及原Clear，不以metadata Accepted或日志无警告代替。其它模块/Teams/资产/网络和R0分别留账，不自动续写。
