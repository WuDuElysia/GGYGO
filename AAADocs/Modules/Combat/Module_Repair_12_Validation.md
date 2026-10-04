# 第 12 批 Combat 命中链路验证交接

日期：2026-09-30  
状态：12-StrictCapture-I两项Base输入解析拒绝已实现、静态审查并冻结，尚未编译/加载/运行，专项测试另步。新增前第26轮完整构建Succeeded（6 actions、85.06秒、exit0），常规60/60、全部测试errors/warnings0；该旧DLL结果不涵盖本步生产改动。此前第25轮59/59及E6真实距离有限契约通过保留历史，测试pair未改；真实Player/Boss调用者、EndPlay、正式资产、PIE与网络仍开放。本轮仅获授Execution cpp与本批两记录，交回后冻结。

## 1. 范围与依赖

本批实现 E1–E6：Trace 物理材质与生命周期、共享命中载荷、Player/Boss 调用接线、EffectContext 显式来源快照的本地复制、距离衰减语义及 HitImpact 位置有效性。实现沿用既有 GAS、MeleeTrace 单窗口状态和 HealthSet 元属性结算，没有新建第二套命中状态机、帧调度器或属性结算链。

04/05/13 在本批开始前已通过完整 `GGYGOEditor Win64 Development` 构建和项目自动化 38/38、0 warning/error。该结果仅是前置基线，不包含本文件列出的第 12 批修改，不能作为本批构建或自动化通过证据。

## 2. 实际源码与测试差异

### 12-A1 SharedBuilder

文件：

- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp`

实际变化：

- 新增 `FGGYGOHitEffectPayload`，共同携带 EffectContext、可选 EffectSpec 和 Cue 参数。
- 新增受保护的 `BuildHitEffectPayload`，统一创建命中 Context、Spec 与 Cue。
- Context 先 `AddHitResult(..., true)`，再通过项目 Context 的 `SetSourceOriginSnapshot` 写入 Origin 与显式快照标志，避免把父类自动生成的 TraceStart Origin 当成来源快照。
- 有 GE 时走项目 `ApplyAbilityTagsToGameplayEffectSpec`、能力 Spec 的 SetByCaller 初值和 `BP_EditSpecValues`；无 GE 或 Spec 无效时仍初始化 Cue Context。
- Cue 同时汇入目标 ASC 当前 Owned Tag 和物理材质 Tag。

已修正的 UE 5.8 陷阱：带输出参数的 `UAbilitySystemComponent::GetOwnedGameplayTags(FGameplayTagContainer&)` 会先 `Reset` 传入容器。初版顺序会覆盖 `InitGameplayCueParameters_GESpec` 或无 GE 路径已经加入的表面 Tag。最终实现改为读取无参数 const getter 后 `AppendTags`，并在最后追加物理材质 Tag；有 GE 和无 GE 两条路径共享该顺序。

### 12-A2 PlayerCaller

文件：`Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp`

实际变化：

- `HandleMeleeHit` 改为调用 `BuildHitEffectPayload`。
- Origin 在命中回调内取源 Avatar 当时的位置。
- Player 能力只写当前 ComboStep 的 Damage/PoiseDamage SetByCaller 并尝试应用 Spec。
- 碰撞 Cue 在 GE 应用之后独立执行，GE 免疫、拒绝或没有 GE 不吞掉碰撞表现。
- 移除调用点直接 `MakeOutgoingSpec`、`AddHitResult` 和手工拼装 Cue 参数的重复职责。

### 12-A3 BossCaller

文件：`Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp`

实际变化：

- `HandleMeleeHit` 与 Player 使用相同 `BuildHitEffectPayload` 接口。
- Origin 在命中回调内取 Boss Avatar 当时的位置。
- Boss 能力只写自身 Damage/PoiseDamage SetByCaller 并提交 Spec。
- 碰撞 Cue 与 GE 结算结果解耦。
- 未改 Boss 选招、Montage 生命周期、Trace 窗口或 CMC 动作位移职责。

### 12-B1 TraceRuntime

文件：

- `Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.h`
- `Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.cpp`

实际变化：

- Sweep 查询参数启用 `bReturnPhysicalMaterial`。
- `EndTraceWindow` 统一关闭 Tick，清空 PreviousStart/PreviousEnd、baseline 和本窗口命中去重；仅活动窗口使 WindowSerial 失效，重复清理保持幂等。
- `Deactivate`、`OnUnregister`、`EndPlay` 都先调用统一清理入口。
- Trace 使用本文件的 `LogGGYGOMeleeTrace` 静态日志类别，移除 AbilitySystem 日志依赖。

### 12-B2 TraceTest

文件：

- `Source/GGYGO/Combat/Tests/GGYGOMeleeTraceSafetyTest.cpp`
- `Source/GGYGO/Combat/Tests/GGYGOMeleeTraceTestReceiver.h`

实际变化：

- 现有真实碰撞查询夹具增加 PhysicalMaterial 返回断言。
- 增加 Deactivate 和 OnUnregister 清端点、baseline、去重、Tick 及重复调用安全断言。
- EndPlay 与另外两个入口共用同一生产清理函数；没有人为构造脆弱的引擎销毁生命周期夹具。

最新冻结的夹具修正：

- 使用独立非零 Block Sweep 验证材质回填，保留 BodyInstance 材质身份、命中一次及返回原始 PhysicalMaterial 对象的断言；不降低或移除材质验收条件。
- 在创建测试 World/Physics Solver 前创建并强引用 PhysicalMaterial，调用 `GetPhysicsMaterial()` 建立材质句柄，使 Solver 初始化时能够将其纳入 `QueryMaterials_External`。这是合成夹具的初始化时序修正，生产 Trace 仍使用既有查询入口。
- 材质段结束后注销 SphereComponent，不再对没有 WorldContext 的合成世界目标调用 `DestroyActor`；目标随统一 `DestroyWorld(false)` 清理。
- 上述“Solver 创建前建立句柄”和“移除单独 DestroyActor”修正已进入第 13 轮成功构建与实际自动化；严格目标材质身份断言保留并通过，该用例 0 warning/error。该证据验证合成夹具中的查询材质回填与清理路径，不替代正式动画命中或生产资产验收。

### 12-C1 EffectContext

文件：

- `Source/GGYGO/AbilitySystem/GGYGOGameplayEffectContext.h`
- `Source/GGYGO/AbilitySystem/GGYGOGameplayEffectContext.cpp`

实际变化：

- `SetSourceOriginSnapshot` 是写入显式来源快照的入口，内部调用 `AddOrigin` 并设置 `bHasSourceOriginSnapshot`；`HasSourceOriginSnapshot` 同时要求该标志与父类 `HasOrigin()` 有效。
- `AddHitResult(..., true)` 清除旧的显式标志；父类自动写入的 TraceStart 即使使 `HasOrigin()` 为真，也不构成显式来源快照。
- `Duplicate` 先保存显式快照状态和值，深拷贝 HitResult 后通过 `SetSourceOriginSnapshot` 恢复；只有隐式 TraceStart 的 Context 不会因复制获得显式标志。
- 距离查询仅在显式来源快照与 HitResult 都存在时计算 Origin→ImpactPoint，否则返回 0。
- `NetSerialize` 与 Iris 均继续转发父类协议，`HitID`、`AbilitySourceObject`、`bHasSourceOriginSnapshot` 不复制。父类 Origin 的网络传输不代表显式标志也已传输；当前距离快照契约用于服务器结算，不能推导客户端可读取同一显式状态。将来若客户端需要该状态，须同时设计扩展网络协议与自定义 Iris NetSerializer。

### 12-C2 DistanceExecution

文件：`Source/GGYGO/AbilitySystem/Executions/GGYGODamageExecution.cpp`

实际变化：

- 距离衰减改为读取 EffectContext 的显式来源快照→ImpactPoint 距离。
- 不再用 EffectCauser 的当前 Actor 坐标计算距离。
- 属性捕获、材质衰减、SetByCaller 覆盖和 HealthSet 元属性输出职责未改变。

### 12-C3 HitCue

文件：

- `Source/GGYGO/AbilitySystem/Cues/GGYGOGameplayCueNotify_HitImpact.h`
- `Source/GGYGO/AbilitySystem/Cues/GGYGOGameplayCueNotify_HitImpact.cpp`

实际变化：

- 命中位置通过 `Parameters.EffectContext.GetHitResult()` 是否存在来判定。
- 有 HitResult 时使用 ImpactPoint，世界原点是合法命中位置。
- 无 HitResult 时回退 Target Actor 位置。
- 表面选择仍只消费 Cue 的 AggregatedTargetTags，不取得伤害权威。

### 12-C4 HitSemanticsTest

文件：

- `Source/GGYGO/AbilitySystem/Tests/GGYGOHitSemanticsTestTypes.h`
- `Source/GGYGO/AbilitySystem/Tests/GGYGOHitSemanticsTest.cpp`

实际变化：

- 新增本批自有的 `UGGYGOHitSemanticsTestAbility` transient UCLASS。
- 测试能力公开一个窄化 wrapper，在实际派生类型对象上调用受保护的 `BuildHitEffectPayload`。
- 测试实际 `GiveAbility` 并激活该能力，覆盖有 GE 和无 GE 两条 Cue 路径均保留目标 Owned Tag 与物理材质 Tag。
- 覆盖 Duplicate 保留显式标志/Origin/深拷贝 HitResult、显式 Origin→ImpactPoint 距离、缺字段返回 0、隐式 TraceStart 不取得显式标志、世界原点命中及无 HitResult 回退。
- 覆盖共享 builder 标记显式快照，以及源 Actor 后续移动不改变已记录的命中距离；没有覆盖客户端复制后的显式标志或联机距离结算。

已修正的 C++ protected 访问陷阱：没有保留通过辅助派生类静态函数、经任意 `UGGYGOGameplayAbility*` 调受保护方法的方案。最终 wrapper 属于实际授予和激活的测试派生能力；未把生产 builder 改为 public，也未修改第 04 批 Admission 测试类型。

## 3. 局部架构文档差异

实现阶段已同步并冻结以下局部文档与 Canvas：

- `AbilitySystem/结构.md`
- `AbilitySystem/GGYGO_结构_AbilitySystem.canvas`
- `AbilitySystem/GGYGO_流程_伤害结算.canvas`
- `Combat/结构.md`
- `Combat/GGYGO_结构_Combat.canvas`
- `Combat/GGYGO_流程_Combat.canvas`
- `Physics/结构.md`
- `Physics/GGYGO_结构_Physics.canvas`

内容记录共享载荷职责、显式 Origin、Origin→ImpactPoint 距离、碰撞 Cue 与 GE 解耦、Trace 物理材质查询及生命周期清理。五张修改的 Canvas 已通过 JSON 解析、节点/边 ID 唯一性与边端点引用检查。全局入口、实施状态和其他批次文档未由本批修改。

本轮授权范围仅为本文件，未重新写入或验证上述 Obsidian 文档与 Canvas；此处记录的旧检查不能替代最新显式快照标志及夹具修正的笔记一致性复核。

## 4. 已完成的静态检查

- Trace runtime 中不存在 AbilitySystem include 或 `LogGGYGOAbilitySystem` 引用。
- Trace Sweep 查询存在 `bReturnPhysicalMaterial = true`；三个生命周期入口都调用统一清理。
- PlayerCombo 与 BossMelee 调用点不存在直接 `MakeOutgoingSpec`、`AddHitResult` 或局部 `FGameplayCueParameters` 构造。
- SharedBuilder 顺序为 `AddHitResult(..., true)` → `SetSourceOriginSnapshot`；Cue 标签顺序为追加目标 const Owned Tags → 最后追加物理材质 Tags。
- EffectContext 距离查询要求显式标志；重置 HitResult 清标志，Duplicate 深拷贝后恢复显式快照，网络路径仍不复制扩展字段。
- DamageExecution 不再读取 `EffectCauser->GetActorLocation()`。
- HitImpact 不再用 `Location.IsNearlyZero()` 判断命中有效性。
- 专项测试只使用第 12 批自有测试能力 wrapper，不引用第 04 批 Admission 测试能力。
- 局部 Canvas JSON、节点/边唯一性和端点引用均通过。

这些静态检查证明源码形态与依赖边界符合本批契约；构建与实际自动化结果单独列于第 6 节。最新 Trace 夹具修正已取得第 13 轮构建和动态自动化证据。

## 5. 新增或扩展的自动化注册名

本批自动化注册名：

1. `GGYGO.Combat.MeleeTrace.SafetyAndCoverage`
2. `GGYGO.AbilitySystem.HitSemantics.ContextAndCueLocation`
3. `GGYGO.AbilitySystem.HitSemantics.PayloadTargetAndSurfaceTags`

第一项是既有用例的本批扩展；后两项是第 12 批新增用例。

## 6. 已执行结果与未验证边界

### 6.1 历史：第 11 轮完整构建与全项目门禁

当时由统筹确认本批 `GGYGOEditor Win64 Development` 完整构建通过，并登记于总账与并行排程。该历史结果对应以下门禁使用的版本，不涵盖随后冻结的 Trace 材质句柄时序及销毁修正；涵盖修正的最新构建见第 6.3 节。

报告：`Saved/AutomationReports/ModuleRepairGate_20260930_11/index.json`；日志：`Saved/Logs/GGYGO_ModuleRepairGate_20260930_11.log`。

- 实际执行 45 项：成功 44、失败 1、未运行 0、成功但有警告 0。
- `GGYGO.AbilitySystem.HitSemantics.ContextAndCueLocation`：成功，测试报告 0 warning / 0 error。
- `GGYGO.AbilitySystem.HitSemantics.PayloadTargetAndSurfaceTags`：成功，测试报告 0 warning / 0 error。
- `GGYGO.Combat.MeleeTrace.SafetyAndCoverage`：失败，测试报告 0 warning / 1 error；失败断言为“Trace 查询返回目标物理材质”。
- 除 Trace 外的 44 项均成功；不能将该轮写成全项目通过，也不能以测试报告计数宣称整个 UE 进程日志没有 warning/error。

### 6.2 历史：第 12 轮 Trace 单项复跑

报告：`Saved/AutomationReports/ModuleRepairGate_20260930_12_Trace/index.json`；日志：`Saved/Logs/GGYGO_ModuleRepairGate_20260930_12_Trace.log`。

- 实际执行 1 项，失败 1；该用例报告 1 warning / 1 error。
- BodyInstance 目标材质身份自检及“非初始阻挡 Sweep 命中材质目标一次”断言未报错，但命中回传的 PhysicalMaterial 身份断言仍失败，不能仅凭已命中或 BodyInstance 正确认定查询材质回填成功。
- 警告为 `UWorld::DestroyActor: World has no context!`，来自合成测试世界目标的独立销毁路径。
- 引擎源码只读诊断定位到材质句柄与 Solver 查询材质镜像的初始化时序；据此冻结第 2 节所列最新夹具修正。该复跑发生在最新修正之前，不能作为修正后的动态证据。

### 6.3 历史：第 13 轮完整构建与全项目门禁

构建日志：`Saved/Logs/ModuleRepairBuildGate_20260930_13.log`。

- `GGYGOEditor Win64 Development` 完整构建结果为 `Succeeded`，总耗时 25.49 秒；UHT 写入 12 个 generated files，完成 6 个构建动作，`UnrealEditor-GGYGO.dll` 链接成功。
- 本次构建涵盖第 2 节冻结的最新 Trace 材质句柄时序与清理修正，已替代“仅静态冻结、尚未构建”的旧状态。

报告：`Saved/AutomationReports/ModuleRepairGate_20260930_13/index.json`；日志：`Saved/Logs/GGYGO_ModuleRepairGate_20260930_13.log`。

- 实际执行 47 项：成功 47、成功但有警告 0、失败 0、未运行 0、进行中 0；测试报告中各项均为 0 warning/error。
- `GGYGO.Combat.MeleeTrace.SafetyAndCoverage`：`Success`，0 warning/error。当前源码仍严格断言 `Receiver->LastPhysicalMaterial == PhysicalMaterial.Get()`；未放宽为材质非空，也未移除身份断言。最新夹具已实际加载执行，先前材质失败与无 WorldContext 销毁警告未再出现在该用例结果中。
- `GGYGO.AbilitySystem.HitSemantics.ContextAndCueLocation` 与 `GGYGO.AbilitySystem.HitSemantics.PayloadTargetAndSurfaceTags`：均为 `Success`，各 0 warning/error。
- UE 日志确认 `47 tests performed`，并以 `RequestExitWithStatus(1, 0, ...)` 结束；退出码为 0。测试结果无 warning/error 不等于整个 UE 启动日志没有初始化等诊断。
- 本轮结果关闭本批源码构建与现有专项/全项目自动化门禁；统筹据此释放第 15 批默认 GE 消费接缝。第 11/12 轮失败保留为修正过程证据，不能反写成当时成功。
- 合成碰撞查询及 Context/Cue 测试不证明玩家/Boss 正式动画命中、生产资产接线、PIE 或联机/专服已经验证。

### 6.4 第 13 轮验证层状态（后续步骤见第 8/9 节）

| 验证层 | 本批状态 | 需要确认 |
| --- | --- | --- |
| UHT / 反射编译 | 第 13 轮 UHT 与完整构建成功 | 已有日志证据；新增源码后仍须重新冻结并构建 |
| 完整构建 | 第 13 轮 `Succeeded`，25.49 秒 | 涵盖最新 Trace 修正；不替代生产资产或动态场景验收 |
| 专项自动化 | Trace 与 HitSemantics 共 3/3 成功，各 0 warning/error | 现有专项门禁关闭；正式动画命中仍未验证 |
| 全项目自动化 | 第 13 轮 47/47 成功，UE 退出码 0 | 历史 `_11` 44/45 与 `_12_Trace` 失败仍保留；不扩张现有测试覆盖 |
| 资产验证 | 未运行 | PhysicalMaterialWithTags、Cue SurfaceEffects、伤害 GE 与 GA 配置实际接线 |
| PIE | 未运行 | 玩家/Boss 真实 Montage 窗口、命中、伤害、表面表现及清理 |
| 联机/专服 | 未运行 | 权威伤害、Cue 复制/可见性、Avatar/目标生命周期边界 |

本轮文档更新未操作 UE、UBT、Git 或资产；上列构建和自动化由统筹执行。此前 38/38、0 warning/error 仅属于第 12 批修改前的前置门禁，资产、PIE 与联机验证仍未运行。

## 7. 冻结结论与交接停止点

- 第 12 批生产源码、专项测试和局部架构文档已停止写入。
- 本文件完成后验证交接文档冻结。
- 第 13 轮已完成最新 Trace 夹具构建、加载、严格材质专项及全项目回归，关闭此前待复验项；统筹已释放第 15 批默认 GE 消费接缝。
- 最新显式快照标志和夹具修正的局部架构笔记一致性仍需按文件租约复核；本轮不扩大文档写入范围。
- 本批源码构建与现有自动化门禁已通过；正式动画命中、生产资产、PIE/联机边界尚未验证，不能标记生产验收全部完成。本会话对生产/测试源码、局部笔记/图文、资产及全局文件继续保持冻结，本轮无新增写入授权。

## 8. 12-E4-T1：实际 Spec / Context / 目标捕获专项（第22轮已运行）

### 8.1 新增前门禁与本步骤状态

只读核对 `Saved/Logs/ModuleRepairBuildGate_20260930_21.log`：完整构建 `Succeeded`，32.23 秒。`Saved/AutomationReports/ModuleRepairGate_20260930_21/index.json` 实际 52 succeeded、0 succeededWithWarnings/failed/notRun/inProcess；旧 Trace 与两项 HitSemantics 各 Success、0 warning/error。对应 UE 日志记录 `52 tests performed` 与退出码 0。

以上报告没有本步骤新注册名，不能作为新专项的运行证据。第 11/12 轮严格失败、第 13 轮通过及既有未验边界均保留。

本步骤由 Combat 组长直接执行，统筹唯一授权：

- `Source/GGYGO/AbilitySystem/Tests/GGYGOHitSemanticsTest.cpp`
- `AAADocs/Modules/Combat/Module_Repair_12_Subleases.md`
- 本文件

12-E4-T1 执行期间，生产接口、共享 types 头、其它测试、Obsidian/图文、资产与全局文件保持冻结。契约与基线先登记于 Subleases，再追加测试；源码静态审查冻结后记录本节。后续 types/cpp 的限定新增见第9节。

### 8.2 新叶与实际断言

注册名：`GGYGO.AbilitySystem.HitSemantics.PayloadSpecContextAndTargetCapture`，使用 `EditorContext | EngineFilter`，不是独立诊断分类。仅追加该叶与 `Misc/ScopeExit.h`，复用原 World/ASC/Finish helper 和实际测试能力 wrapper，不新增反射类型。

- 前置逐项检查 GEngine、临时 World 与 WorldContext、源/目标 Actor 和已注册权威 ASC、Owner/Avatar 与 Actor 对 ASC 的发现、工厂分配项目 Context、真实 GiveAbility 句柄、TryActivateAbility 与活跃实例。
- 构造 Spec 直接断言 Surface SpecTags/聚合 Tags；Cue 直接断言 Owned+Surface。构造 Spec 尚未捕获目标 Owned，测试没有手工向 CapturedTargetTags 灌入标签。
- Payload/Spec/Cue 直接比较同一个 Context 地址，并分别检查项目类型、显式快照标志与明确 Origin、Hit 目标/点/法线及原物材对象身份。改写输入 Hit 的目标/点/法线/物材后，原三份 Context 保持原值。
- 基础 `UGameplayEffect` 定义必须为未修改的空 Instant（无 Modifier/Execution/Cue）；真实调用 SourceASC 的 `ApplyGameplayEffectSpecToTarget`，用 `WasSuccessfullyApplied()` 判断 Instant 成功，不要求持久句柄有效。
- 从 Target 公开 `OnGameplayEffectAppliedDelegateToSelf` 的实际 Spec 副本观察：应用一次、来源 ASC 正确、ActorTags 含 Owned、SpecTags 含 Surface、聚合 Tags 同时含二者、Context 与原载荷一致；原构造 Spec 不被应用副本反写 Owned。回调内复制 Spec，不保存回调参数引用。
- 对 Builder 实际 Spec Context 调公开 `Duplicate()`，直接检查 Context/HitResult 地址独立、原内容与材质身份保持；通过公开接口仅修改副本 Origin/Hit/物材，再检查原 Payload/Spec/Cue 与应用 Spec 都保持原值。
- scope guard 先解绑公开回调，之后才结束测试能力、销毁 World/WorldContext；材质强引用覆盖所有数据与副本断言。未屏蔽日志或修改 GE CDO，失败断言不依靠生产短修变绿。

引擎阶段已只读核对：目标 Owned 由 `ExecuteActiveEffectsFrom` 捕获到实际应用副本；单独 `CaptureAttributeDataFromTarget` 只捕获属性。当前公开应用回调广播入口为 `AbilitySystemComponent.cpp:2160`，预检中的旧调用点行号不当作该入口精确行。

### 8.3 冻结与保护证据

- cpp 起始 SHA256：`4A373D6D48B93574BD5CAED6571D9B1A3C41C58274A9ABD9D49041DE2C2F15D8`。
- 本步骤交回时 cpp SHA256：`05254281C0D624F56B827062CB3F99887754DDC162AF4AF7ABC360F2CD4B643D`。
- 只读逆向移除新增 include 与独立测试块（197 行，含分隔空行），原文件全文精确恢复，SHA256 与起始基线相同。旧两项 HitSemantics 叶及所有既有 helper 正文保持；原第三叶 MeleeTrace 测试 cpp hash 也与步骤开始时一致。
- types 头保持 `5566A3BC969EBDF27457143909D081FE8B115758D4DC0B6F51B8C448D68496FF`；Builder 与 EffectContext 生产 h/cpp hash 均未变。
- 本步骤交回时源码已停止写入，三文件冻结；当时未运行 UHT/编译/链接、UE/自动化、Git、资产保存或代理。该叶随后由统筹第22轮实际构建/加载/执行，结果见第8.4节。
- 本叶仅补 E4 的 Spec/Context/目标捕获证据；不修复或补证 E6 的 Actor 移动前提/来源接口 Execution，不合并 EndPlay、真实 Player/Boss 命中调用者、生产动画、资产、PIE/联机或既有图文漂移。原 E6 移动覆盖描述不能作为真实移动已发生的证据。

### 8.4 统筹第22轮实际构建与自动化

只读核对 `Saved/Logs/ModuleRepairBuildGate_20260930_22.log`：`Succeeded`、5 actions、22.16秒，实际链接 `UnrealEditor-GGYGO.dll`。统筹确认构建exit0、UE进程退出exit0。

`Saved/AutomationReports/ModuleRepairGate_20260930_22/index.json` 于 `2026.09.30-08.50.07` UTC 记录常规55 succeeded，0 succeededWithWarnings/failed/notRun/inProcess，各用例errors/warnings均为0。新 `PayloadSpecContextAndTargetCapture` 为 `Success`，0.008485399186611176秒，entries为空；旧Trace及两项HitSemantics继续Success。该报告不含随后新增的E6注册名，不能作为第9节新测试的运行结果。

## 9. 12-E6-T1：实际 Execution 距离快照专项

### 9.1 授权、范围与唯一目标

统筹接受零写入预检后明确授权四文件：`GGYGOHitSemanticsTestTypes.h`、`GGYGOHitSemanticsTest.cpp`、本批Subleases与本文件。先登记契约，再追加测试类型及独立叶，源码静态审查冻结后更新记录；未创建代理。

唯一目标是通过真实 GAS 应用链，严格断言生产 `UGGYGODamageExecution` 传给 AbilitySource 的距离来自显式 Origin→Hit 快照，EffectCauser 后续真实移动不改变它。生产接口和结算链继续只读，不引入替代 Execution、不修旧测试使其变绿。

### 9.2 新增夹具和严格断言设计（第25轮实际通过，见9.4）

注册名：`GGYGO.AbilitySystem.HitSemantics.DistanceExecutionUsesOriginSnapshotAfterCauserMove`；分类为普通 `EditorContext | EngineFilter`。

- 追加反射 UObject `UGGYGOHitDistanceTestSource`：实现实际公开来源接口，仅记录生产调用的距离，明确选择夹具公式 `1 / (1 + Distance)`。它以SourceActor为Outer，强引用覆盖授予、Context、应用、回调副本和全部断言；不是业务错误触发的默认来源。
- 追加 `UGGYGOHitDistanceTestEffect`：构造器只配置Instant和唯一生产DamageExecution。没有普通Modifier/Cue，没有运行时修改基础GE或任何CDO，没有自定义替代计算。
- 复用原World/ASC/helper/能力wrapper。严格前置包括WITH_SERVER_CODE、World/context、注册权威ASC、Owner/Avatar/Actor发现、项目Context factory、真实授予句柄/激活实例、Spec.SourceObject身份、属性集Actor Outer/ASC归属和初始化、生产两项capture有效及GE配置。命名断言失败后立即停止后续业务验证；没有catch、日志屏蔽或隐式成功路径。
- SourceActor自有SceneRoot设Movable、作为Root并注册。初始SetActorLocation返回必须成功，Actor和Root实际世界坐标均为`(10,20,30)`。Origin从实际Actor读取；Hit为`(13,24,30)`、目标身份/法线明确，TraceStart另设远点，显式距离严格为5。
- 来源只经真实 `GiveAbility(FGameplayAbilitySpec(..., SourceObject))` → 原GA `MakeEffectContext` → Context接入；测试不手动补来源。Source真实CombatSet.BaseDamage为84、BasePoiseDamage为0；Target真实HealthSet为Health/MaxHealth=100、Poise/MaxPoise=50、meta=0，无免疫/GodMode。构造Spec无任何SetByCaller覆盖，生产capture定义均有效。
- Builder只生成一次Spec。第一次SourceASC实际应用，严格要求Instant `WasSuccessfullyApplied()`、来源距离调用/目标应用回调各一次、距离5、Health86、Damage/PoiseDamage消费为0、Poise仍50、材质衰减调用为0。
- EffectCauser实际移动到`(13,24,43)`，必须验证SetActorLocation成功、Actor/Root世界坐标正确且与快照不同；当前位置到Hit距离严格13。原Context必须仍有显式Origin标志和值、原Hit、实际来源和EffectCauser身份。
- 第二次实际应用同一构造Spec，严格要求累计两次调用、来源只记录`[5,5]`、Health72、meta清零。若生产读取当前EffectCauser位置，第二次会按13返回衰减并造成6伤害，无法通过72断言。
- Target公开应用回调按值复制每次真实Spec并记录实际SourceASC；检查同一Context、AbilitySource、SourceObject、Instigator/sourceASC、EffectCauser、Origin及Hit。无直接衰减getter调用、无手动Execution调用、无Context距离helper调用。
- RAII按析构顺序解绑本叶回调 → 原能力Finish/End → ClearAbility本叶句柄 → 移除本叶属性集 → 强引用退出 → 原World RAII清Actor自有Root/ASC及WorldContext。Instant没有持久GE句柄要回收。没有第二套伤害状态/执行链、循环依赖或生产内部状态写入。

### 9.3 冻结证据与准确边界

- cpp最终SHA256：`25568066A9A881325237EA34D2F56B7A910C80F4E16E85ECB26BFC9757323E25`；types最终SHA256：`DEB5DB58F3DE17833084DBE8F9F56E106C4C7CF0473A58C2EE04C570D4628C21`。
- cpp仅新增三条include和独立测试块，共211行；types仅新增三条include和两个测试类型，共43行。内存中只读移除这些新增内容后，恢复字节Base64与本步起始原始字节全文逐字节相同；恢复SHA256分别为`05254281C0D624F56B827062CB3F99887754DDC162AF4AF7ABC360F2CD4B643D`、`5566A3BC969EBDF27457143909D081FE8B115758D4DC0B6F51B8C448D68496FF`。旧三个叶、helper和原能力wrapper全文保持，包含原rootless移动断言的旧局限。
- Builder h/cpp、AbilitySource接口、Context h/cpp、DamageExecution h/cpp与旧Trace测试cpp均保持本步开始时hash。12-E6-T1实施交回时仅只读核对UE公开API及真实Native ExecuteActiveEffectsFrom→生产Execution→HealthSet路径；组长未运行UHT/编译/链接、UE加载/自动化、Git、资产保存或代理。随后统筹运行结果见9.4。
- 12-E6-T1四文件交回时冻结，当时尚无Success/Fail，初始化、移动、距离参数和扣血数值仅为已编写的严格断言；第22轮不包含它。统筹接受根静态审查后，在写入者冻结前提下执行后续第25轮门禁，本叶实际Success；不反写当时未运行的历史。
- 已按计划蓝图只读定位Combat/AbilitySystem并核对相关结构文档。本步不改变生产职责/接口；现有第12批旧“未构建”图文漂移仍属另步租约，图文保持冻结，不能在本测试步骤内擅自改写或把新测试标为通过。
- 不证明真实Player/Boss调用者、EndPlay、消息、正式资产接线、动画命中、PIE或联机/专服。未增加业务兜底；新的“禁止隐式业务兜底”约定已核对，生产疑似替代行为仅允许另行只读列证，不在本步删除或修正。

### 9.4 12-E6-V1：统筹第25轮实际门禁及有限通过结论

本记录步骤仅授权本文件和 `AAADocs/Modules/Combat/Module_Repair_12_Subleases.md`。只读核对原始构建日志、自动化JSON、UE日志及测试pair冻结hash后更新；没有改源码/测试/Obsidian/资产，没有执行UE/构建/Git或兜底修复。

构建：`Saved/Logs/ModuleRepairBuildGate_20260930_25.log` 为 `Succeeded`，4 actions、13.08秒，实际链接 `UnrealEditor-GGYGO.dll`；统筹确认构建exit0。

自动化：`Saved/AutomationReports/ModuleRepairGate_20260930_25/index.json` 创建于 `2026.09.30-10.49.09` UTC（北京时间18:49:09），实际59 succeeded，0 succeededWithWarnings/failed/notRun/inProcess，总耗时0.6763694882392883秒；全部59用例errors/warnings均为0。

- 新 `GGYGO.AbilitySystem.HitSemantics.DistanceExecutionUsesOriginSnapshotAfterCauserMove`：`Success`，0.009482499212026596秒，entries为空、errors/warnings0。该结果对应第9.2节严格前置与断言：实际Movable Root移动成功且坐标变化、当前位置距离5→13，同一构造Spec两次通过生产DamageExecution调用来源接口仍为[5,5]，真实HealthSet100→86→72、Damage清零及实际应用回调来源/Context保持。
- 旧 `ContextAndCueLocation`、`PayloadTargetAndSurfaceTags`、`PayloadSpecContextAndTargetCapture` 和 `MeleeTrace.SafetyAndCoverage` 均继续Success，errors/warnings0。第22轮旧55项在本轮仍全部Success；原有历史断言没有被本步骤改写或放宽。
- `Saved/Logs/GGYGO_ModuleRepairGate_20260930_25.log` 记录 `59 tests performed` 与 `RequestExitWithStatus(1, 0, ...)`。统筹确认UE PID32976已exit0退出；本组长只读日志，没有启动/操作UE。测试报告0 errors/warnings不表示整个UE启动日志没有其它诊断。
- 此轮测试pair仍是cpp `25568066A9A881325237EA34D2F56B7A910C80F4E16E85ECB26BFC9757323E25`、types `DEB5DB58F3DE17833084DBE8F9F56E106C4C7CF0473A58C2EE04C570D4628C21`，与交回冻结hash一致。

第25轮关闭本叶编译/加载/运行及上述合成权威链路的有限距离契约。它不证明真实Player/Boss命中调用者、EndPlay、消息、正式GE/GA/物材/Cue资产接线、生产动画、PIE或联机/专服，也不修正旧rootless移动断言、现有图文漂移或三项业务替代候选。旧第11/12轮失败、第13/22轮通过及12-E6-T1最初未运行状态保持历史。

12-E6-V1两记录核对完成后交回hash并冻结；全部源码、测试、Obsidian/Canvas、资产继续只读，不自动进入下一步骤。

## 10. 12-StrictCapture-I：两项基础输入拒绝（未编译/运行）

### 10.1 单一契约、范围与新增前门禁

统筹接受零写入预检并授权 `Source/GGYGO/AbilitySystem/Executions/GGYGODamageExecution.cpp`、本批Subleases及本文件，共三文件。先登记契约和原始字节基线，再改单cpp；完整差异及保护段核对后源码冻结，最后同步两记录。测试、Execution头、其它生产、Obsidian/Canvas、资产继续只读。

本步骤仅闭合BaseDamage/BasePoiseDamage所选输入来源的明确失败契约：任一必需来源缺失或数值非法，命名诊断并不新增本Execution的任何Modifier，不清除调用方已有输出。原生Execute为void，无GE应用失败返回值；不能把无输出写成整个GE/GA已拒绝。

只读核对新增前 `Saved/Logs/ModuleRepairBuildGate_20260930_26.log` 为Succeeded、6 actions、85.06秒，实际链接DLL；统筹确认exit0。`Saved/AutomationReports/ModuleRepairGate_20260930_26/index.json` 于 `2026.09.30-11.41.41` UTC（北京时间19:41:41）记录60 succeeded，0 failed/succeededWithWarnings/notRun/inProcess、全部errors/warnings0；旧E6叶Success、entries空、0.010166797786951065秒。UE日志记录60 tests performed与RequestExitWithStatus退出码0，统筹确认PID36128已退出。该门禁使用新增前生产代码，不证明下面的新拒绝路径。

### 10.2 实际生产差异与静态核对

- 新增两条include：既有 `GGYGOAbilitySystemLog.h` 和原生 `AbilitySystemComponent.h`，仅复用GAS层日志类别及完整ASC类型，不新增模块依赖或公共接口。
- 替换原20行基础输入区间为64行栈上解析/诊断；净增加46行（含两include）。两项各自使用公开 `Spec.SetByCallerTagMagnitudes.Find(Tag)` 确认键存在性，不再用getter返回的负数哨兵混淆显式覆盖与缺键。
- 键存在：有限且非负值直接使用，0合法；该项不调用capture。显式负值、NaN、Inf返回invalid，不退回capture。
- 键不存在：必须实际 `AttemptCalculateCapturedAttributeMagnitude` 返回true，且结果有限；返回false不能以初始0冒充输入。有限负capture保持原最终非负公式，不新增CombatSet值域约束。
- 两项均解析有效后才进入原衰减/公式/Health元属性输出尾部。任一invalid只输出一条Error，包含Execution对象路径、GE路径、Source/Target ASC路径、两个字段各自的来源/原因/值；capture失败显示value unavailable。没有Tick日志、持久抑制缓存或成功日志热路径分配。
- 失败分支不写Spec、不调用OutExecutionOutput修改接口、不Reset调用方已有输出。通过原生每次创建的ExecutionOutput可获得本次零新增Modifier；native GE应用句柄仍可能成功，失败传播到GA/GE不在本步骤。
- 新结果结构仅为当前Execute调用的栈上派生值，源数据唯一归属仍为Spec明确覆盖或GAS capture；没有重复属性状态、计时器、执行器、循环依赖或新资源清理责任。
- constructor/statics、源Tag/目标Tag评价参数及原衰减/Context/公式/Health输出完整尾部保持原字节。衰减接口非法值、乘积溢出、其它业务替代、HealthSet/GA/Cue、Movement和Editor读取均未修改，不宣称全部数值风险已关闭。

### 10.3 保护证据、架构核对与冻结停止点

- cpp起始SHA256：`77A64CCF63F735A7138B6F57FC636807A83DFB324DF563B3116CF6239195F4A1`；最终SHA256：`96074463D24F206EF6E49CC27746BFD3B117E0510D083B7AC38EFEAD16FF6134`。
- 完整差异限定为两include及20→64行基础输入区间，已逐行静态审查。在内存中只读删除新include并将新区间换回保存的原20行后，恢复字节Base64与实施前全文逐字节相同，SHA256精确恢复起始值；未写入任何恢复文件。
- 前保护段（去掉两新增include后，从文件起始到输入区间前）字节保持，SHA256 `AB5536DEB4BE0489EEA6E168B7357DBFB3CDF9152EB2B897DF983A74B7EA0A7B`；尾保护段（距离与材质衰减注释起至EOF）字节保持，SHA256 `65F2D3B56BC00E276D1252D5DC445EC218526857B1468E8D2B7C58E4CA748C69`。
- Execution头仍为 `3B5C8EC85C7AE338DF60BAD94D3D6A2B005FD601AEC97E4B8BF7DE49A3389B86`；既有HitSemantics测试pair仍为cpp `25568066A9A881325237EA34D2F56B7A910C80F4E16E85ECB26BFC9757323E25`、types `DEB5DB58F3DE17833084DBE8F9F56E106C4C7CF0473A58C2EE04C570D4628C21`。没有增加或修改测试，专项测试由统筹另步安排。
- 只读按计划蓝图定位AbilitySystem/Combat，并核对AbilitySystem结构文档及伤害流程Canvas的execute节点。职责和依赖方向仍为Spec/capture提供输入、Execution结算、HealthSet落地；图文尚未描述本次输入拒绝分支，既有第12批“未构建”漂移也仍在。统筹明确冻结Obsidian/Canvas，本步仅在获授记录记清待同步项，后续图文需精确租约；不擅自写入或标记已同步。
- 本步未运行UHT/编译/链接、UE/自动化、Git、资产或代理；新拒绝路径只有静态证据，没有Success/Fail运行结果。合法覆盖无需capture、混合来源、合法零/有限负capture、缺捕获/非法覆盖与捕获及不新增/不清除输出专项均留待独立测试步骤。
- 源码及两记录交回最终三hash后全部冻结停止，不自动进入测试、图文或其它兜底修复。

## 11. 12-StrictCapture-T / B6-T1a：基础输入原生专项（源码已冻结，未编译/运行）

### 11.1 租约、颗粒度调整与 Gate27 准确边界

统筹明确授权新 `Source/GGYGO/AbilitySystem/Tests/GGYGODamageExecutionStrictInputTest.cpp`、本批 Subleases 和本文件共三文件。两份记录只追加并保持全部旧字节；全部生产、Execution 头、旧测试/types、资产、Obsidian/Canvas、全局记录继续冻结。没有新 UCLASS 或第四文件。

初始零写入预检提出八族。统筹在实施期间要求尽快形成可审查源码，将本步收束为 T1a 原第1～6族；原第7非法明确覆盖与第8真实非有限捕获留作接续原子步骤。当前源码只实施六族，不把八族初始方案写成全部完成。

只读核对 `Saved/Logs/ModuleRepairBuildGate_20260930_27.log` 为 Succeeded，9 actions、87.41秒，实际链接 `UnrealEditor-GGYGO.dll`。`Saved/AutomationReports/ModuleRepairGate_20260930_27/index.json` 创建于 `2026.09.30-12.38.59` UTC（北京时间20:38:59），60 succeeded，failed/succeededWithWarnings/notRun/inProcess 均0，全部测试 errors/warnings 均0；报告不包含下述新叶。统筹确认该门禁编译了 StrictCapture-I 生产实现。Gate27关闭生产编译及旧60项回归，不证明新增拒绝矩阵或本 T1a 叶运行成功。

### 11.2 实际新增叶与可审查断言

新文件424行，一个普通 `EditorContext | EngineFilter` 叶：`GGYGO.AbilitySystem.DamageExecution.StrictBaseInputResolution`。复用只读 `UGGYGOHitDistanceTestEffect` 选择唯一生产 `UGGYGODamageExecution`，无新反射类型或替代计算器。

| 场景族 | 实际子例与常量期望 | 当前状态 |
| --- | --- | --- |
| 1 正常双捕获 | 源真实12/4 → Damage12/PoiseDamage4；另真实 Apply 一次，Health100→88、Poise50→46、meta0 | 已编写，未运行 |
| 2 无 CombatSet 明确覆盖 | 实际两 capture getter 均false，双覆盖7/2 → 两输出7/2 | 已编写，未运行 |
| 3 合法零 | 真双捕获0/0、无 CombatSet 双覆盖0/0 → 均无输出、无类别 Error/Warning | 已编写，未运行 |
| 4 混合来源 | Damage覆盖7/Poise捕获4 →7/4；Damage捕获12/Poise覆盖2 →12/2 | 已编写，未运行 |
| 5 有限负捕获 | 捕获-3/4 →仅Poise4；捕获12/-3 →仅Damage12，保留既有最终clamp | 已编写，未运行 |
| 6 必需capture真实失败 | 无 CombatSet，单向另项有效覆盖及双缺捕获，共3例；每例空/预填输出保持，诊断双方字段 | 已编写，未运行 |
| 7 非法明确覆盖 | 双向负/NaN/Inf 覆盖，正常capture可供潜在错误回退 | 接续步骤；本 cpp 未实施 |
| 8 非有限真实capture | 双向NaN/Inf公开Init后，实际getter成功且非有限 | 接续步骤；只读API结论保留，未实施/运行 |

- 合计11子例、14次公开生产 `Execute`（8合法例各一次、3拒绝例各空/预填一次），正常例另实际 `ApplyGameplayEffectSpecToTarget` 一次。输出期望均为明确常量，不复制生产解析器或伤害公式；拒绝例不调用 Apply，不宣称整个 native GE/GA 已应用失败。
- 严格前置：WITH_SERVER_CODE/GEngine/GLog，独立实际 World/WorldContext，Actor 自有已注册权威项目 ASC，Owner/Avatar/Actor组件发现一致，真实 HealthSet/可选 CombatSet 的 Actor Outer、OwningActor/ASC/注册集合一致，属性和meta实际初始化，无免疫/GodMode。
- 项目 `MakeEffectContext` 工厂必须成功，Instigator/EffectCauser/sourceASC为真实源Actor/ASC；无 AbilitySource 为本例明确选择的不衰减模式。真实 `MakeOutgoingSpec`、Instant GE/唯一生产Execution、无普通Modifier/Cue/scoped modifier及两项 Source snapshot capture 定义均严格检查。
- 缺捕获例真正不注册 CombatSet，双属性不存在；`HasValidCapturedAttributes`、公开 `FindCaptureSpecByDefinition(..., true)` 和实际 native `AttemptCalculateCapturedAttributeMagnitude` 均须反映失败。不会把输出变量初值0当成功。覆盖键和值位经原生 setter 后严格读取，getter验证在业务 Execute 前完成。
- 拒绝前置全成立后才登记完整 `LogGGYGOAbilitySystem: ...` 预期，使用 `AddExpectedMessagePlain / Error / Exact / 1`。每次拒绝使用独立命名 World/ASC 路径，避免 expected-message set 以文本合并重复键；没有正则泛配、日志屏蔽或改类别抑制设置。
- RAII 原生 `FOutputDevice` 观察器仅在 Execute 期间观察目标类别 Error/Warning，另断言原始 category、Error severity、完整原始文本和恰好1条；合法例断言该类别0条。观察器线程安全且走原生 unbuffered device，构造时回放的backlog不在观察窗口。
- 3个拒绝例各自验证空输出仍0条、预填 Healing/Additive/123 sentinel 仍原样1条，禁止半伤害和清除旧输出。Execute 前后检查公共 Spec 定义/Context身份、源与目标ASC、Instigator/EffectCauser/sourceObject/AbilitySource、level/stack、两种 SetByCaller map 键和值位、source/target tag语义，以及真实capture成功位和值位保持。没有拷贝整个Spec内部缓存或 const_cast。
- Execute 只产生 Modifier，Apply 前 Target Health/Poise/meta仍100/50/0。正常例再经真实 GAS/生产Execution/HealthSet落地，Instant成功使用 `WasSuccessfullyApplied()`；未以持久句柄有效性判断。
- 清理按实际作用域：观察器移除 → output/params/Spec/context析构 → 移除本例属性集并释放强引用 → World销毁Actor自有ASC → 移除WorldContext、清测试package dirty。没有GA/任务/持久GE或全局句柄表重置。

### 11.3 静态保护证据与未关闭项

- 新cpp最终SHA256：`95504F83DA0A939F8A7C897D2B26AEA3E497A79343A9D425C7764E0F694FCA87`。实际文件只含一个Editor叶、测试本地World/原生日志观察/原生捕获读取/小参数表，不增加生产权威状态、模块依赖、公共接口或第二个执行器。
- 只读核对UE 5.8当前公开 native ExecutionParams构造及capture getter、output字段、Spec public maps/capture容器、ExpectedMessagePlain/Exact计数、OutputDevice unbuffered注册、StrongObjectPtr与公开属性Init。未运行UHT/编译/链接、UE加载或自动化；这些断言尚无Success/Fail。
- 生产cpp仍 `96074463D24F206EF6E49CC27746BFD3B117E0510D083B7AC38EFEAD16FF6134`；生产头仍 `3B5C8EC85C7AE338DF60BAD94D3D6A2B005FD601AEC97E4B8BF7DE49A3389B86`；旧HitSemantics cpp仍 `25568066A9A881325237EA34D2F56B7A910C80F4E16E85ECB26BFC9757323E25`，types仍 `DEB5DB58F3DE17833084DBE8F9F56E106C4C7CF0473A58C2EE04C570D4628C21`。全部与本步开始时冻结hash相同。
- 两记录原字节已存内存；只读按各原长度取前缀Base64核对，Subleases原25037字节、Validation原36286字节完整保持。旧阶段“当时未编译”历史不改写，本节只追加Gate27实际后续结论与本步边界。
- 原第7/8族后续仍需真实矩阵。非有限夹具已只读确认 generated public Init直接设置属性base/current，而native capture/aggregator getter不自行校验有限性；该API判断未获得夹具运行验证，不能作为族8通过证据。后续若实际原生不能形成成功且非有限capture，必须停止并交回问题，不能mock、强改捕获缓存或修改生产使其通过。
- 本叶不证明正式Player/Boss/GA调用者、EndPlay、消息、正式资产、PIE/联机/专服，也不测试衰减非法值或乘积溢出。源spec真实输入、Execution结算、HealthSet落地的职责归属保持；没有循环依赖、重复业务事实来源或资源泄漏路径。
- 相关Obsidian结构/伤害Canvas仍缺输入拒绝分支及已有实施状态同步，统筹本轮明确冻结这些文件，仍待精确图文租约。没有擅自写图文、资产、全局记录、运行构建/UE/Git或创建/唤醒代理。
- T1a源码及两记录交回最终三hash后冻结停止；等待统筹统一构建/运行及接续第7/8族安排，不自动扩大任务。

## 12. B7 / 12-StrictCapture-T1b：非法明确覆盖（源码冻结，未编译/运行）

### 12.1 Gate29 已运行 T1a 的有限结论

只读核对 `Saved/Logs/ModuleRepairBuildGate_20260930_29.log` 为 Succeeded，5 actions、15.87秒，实际新DLL。`Saved/AutomationReports/ModuleRepairGate_20260930_29/index.json` 创建于 `2026.09.30-13.54.22` UTC（北京时间21:54:22），63 succeeded，failed/succeededWithWarnings/notRun/inProcess均0，全部测试errors/warnings均0。

`GGYGO.AbilitySystem.DamageExecution.StrictBaseInputResolution` 实际 Success，耗时0.061809998005628586秒、entries空、errors/warnings0，对应cpp `95504F83DA0A939F8A7C897D2B26AEA3E497A79343A9D425C7764E0F694FCA87` 的前六族/11子例/14次Execute及正常例一次Apply断言。UE日志实际记录6条完整基础输入capture失败拒绝，63 tests performed与退出码0；统筹确认UE PID26112退出及九source hash保持。本组长只读报告/日志，没有操作构建或UE。Gate29证明T1a的合成权威链路，尚不包含本次第7族。

### 12.2 三文件原子扩展、差异与保护

统筹明确授权同一专项cpp、本文件和本批Subleases三文件；先登记预检，cpp静态核对冻结后追加记录。生产、旧types/E6、反射头、新UCLASS、第8族、Obsidian/Canvas、资产与全局入口保持冻结，不调用UE/构建/Git/代理。

- cpp只增加 `<limits>` include、NaN/+Infinity两个常量与8个第7族case；更新范围注释，并给原case末行补分隔逗号。新增13行，424→437行，所有helper和前六族断言全文保持。
- 两字段分别测试明确SBC `-3`、NaN、+Inf、-Inf；每例真实CombatSet源12/4，原生两项source snapshot capture前置getter必须成功且分别为12/4，另一字段保留有效capture。若误把非法覆盖退回可用capture，将产生Damage/Poise输出并违反拒绝断言。
- 8新例复用原helper，空/预填各一次，共新增16次公开生产Execute。覆盖键和值位在调用前严格存在/保持；NaN按bits核对。拒绝预期为完整 `Plain / Error / Exact / 1`，原始category/severity/全文/条数由既有RAII观察器检查。输出须空保持或Healing/Additive/123 sentinel原样保持；相关public Spec facts与capture值位保持，断言未降级、日志未屏蔽。
- 当前累计七族、19子例、30次Execute断言、正常例一次Apply断言，22次拒绝诊断预期；这些累计计数是已编写源码范围，本次新增16次尚未编译/运行。
- cpp最终SHA256 `6DBF89F3E703767330683C58DF8B1CF91DDB028861B7F63D2CFFA8DE2CAC7FAB`。内存中只读撤去上述新增内容、恢复注释及末行逗号后，与本步起始原始字节Base64逐字节相同，SHA256精确恢复 `95504F83DA0A939F8A7C897D2B26AEA3E497A79343A9D425C7764E0F694FCA87`；未写恢复文件。
- 两记录原始全文已保存，只追加本步/Gate29；Subleases原31054字节、Validation原44343字节最终按原长度取prefix Base64精确核对。生产cpp/头、旧HitSemantics cpp/types继续核对起始冻结hash，不修改旧测试或生产来使本叶通过。

### 12.3 未关闭与冻结停止点

本步没有UHT/编译/链接、UE加载/自动化运行结果，Gate29不证明新第7族通过。第8族真实非有限capture仍需独立授权及实际成功getter前置；真实Player/Boss/GA调用者、EndPlay、消息、正式资产、PIE/联机/专服、衰减非法值及乘积溢出仍未证明。Obsidian拒绝分支及实施状态同步仍待精确租约。

第7族只扩测试数据，生产职责/接口、状态所有权、依赖及清理路径不变。cpp和两记录交回三hash后全部冻结停止，等待统筹统一门禁和第8族后续安排。


## 13. B8 / 12-StrictCapture-T1c：真实非有限capture（源码冻结，未编译/运行）

### 13.1 Gate30 实际 T1b 结果

只读核对 `Saved/Logs/ModuleRepairBuildGate_20261001_30.log` 为Succeeded、7 actions、43.46秒（UBA36.03秒）。统筹确认UHT写5 generated files、exit0、新DLL以及13源码hash前后保持，全部三个UE窗口已退出。本组长没有运行构建或UE。

`Saved/AutomationReports/ModuleRepairGate_20261001_30/index.json` 创建于 `2026.09.30-16.48.53` UTC（北京时间2026-10-01 00:48:53），SHA256 `65A1C9387911E0A4B64C04236C7B8F46525D8266D0878B93EA267B56E0BEBD23`；63 succeeded，failed/succeededWithWarnings/notRun/inProcess均0，全部叶errors/warnings均0。StrictBaseInputResolution实际Success，0.05470239743590355秒、entries空、errors/warnings0，UE日志实际22条基础输入拒绝。对应cpp `6DBF89F3E703767330683C58DF8B1CF91DDB028861B7F63D2CFFA8DE2CAC7FAB` 的前七族/19子例/30次Execute及一次Apply有限契约；本次第8族未由Gate30运行。

### 13.2 原子实施及静态证据

统筹正式授权同一专项cpp、本文件及12 Subleases三文件。先登记契约，源码静态核对冻结后追加两记录。生产、旧types/E6、新UCLASS/反射头、Obsidian/Canvas、资产和全局入口继续冻结，不运行UE/构建/Git或代理。

- 第8族两字段各NaN/+Inf/-Inf共六例，无SBC，另一项真实捕获为12或4；每例空/预填各一次，新增12次公开生产Execute。源CombatSet仅经公开Init在注册/aggregator创建前初始化，实际MakeOutgoingSpec/native getter/生产Execute链不变。
- 仅初始化和捕获两个前置位置适配NaN：预期NaN才用IsNaN，有限值和±Inf保留原严格相等比较。native getter成功、valid capture及来源归属前置保留；NaN特例不能接受finite或缺capture。
- 额外前置明确要求双方getter true、两种SBC map为空、所选值实际非有限、另一项有限且值正确；前置失败立即返回false，不登记预期Error，不更换路径或修改生产。新case原因常量为non-finite，完整日志来源由无SBC确定为CapturedAttribute，不能以capture-failed通过。
- 既有Plain/Error/Exact/1及category/severity/全文/恰好一次观察、空输出/Healing sentinel保持、public Spec/value bits保持和RAII原样保留。前七族case不变；没有新的状态所有权或生命周期。
- 完整差异见13.3：四处hunk、24新增/5删除行，净增19，437→456行。最终cpp SHA256 `4D62D94FB6FD28DB99C3A28B9C62028AFF6A91CAB54E8D5A93EA1C32CE2DA594`。在内存中撤销且每hunk严格匹配一次后，恢复Base64与本步起始全文逐字节一致，SHA256精确回到 `6DBF89F3E703767330683C58DF8B1CF91DDB028861B7F63D2CFFA8DE2CAC7FAB`；未写恢复文件。
- 当前八族/25子例/42次直接Execute断言及一次真实Apply，拒绝诊断预期共34次。这是源码已编写范围；第8族尚无编译、加载或运行Success/Fail，原生非有限初始化/捕获的实际前置仍待统筹门禁。
- 两记录只追加，原34253/48075字节prefix与各保存原文Base64精确核对；生产cpp/头、旧HitSemantics cpp/types保持本步冻结hash。三文件交回最终hash即全部停止写入。
- 真实Player/Boss/GA调用者、EndPlay、消息、正式资产、PIE/联机/专服、衰减非法值/乘积溢出及Obsidian拒绝分支/实施状态同步仍未关闭，不自动扩展其它矩阵。

### 13.3 完整 cpp 差异

```diff
--- F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGODamageExecutionStrictInputTest.cpp
+++ F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGODamageExecutionStrictInputTest.cpp
@@
-					&& CombatSet->GetBaseDamage() == Case.CapturedDamage
-					&& CombatSet->GetBasePoiseDamage() == Case.CapturedPoise)) { return false; }
+					&& (FMath::IsNaN(Case.CapturedDamage) ? FMath::IsNaN(CombatSet->GetBaseDamage()) : CombatSet->GetBaseDamage() == Case.CapturedDamage)
+					&& (FMath::IsNaN(Case.CapturedPoise) ? FMath::IsNaN(CombatSet->GetBasePoiseDamage()) : CombatSet->GetBasePoiseDamage() == Case.CapturedPoise))) { return false; }
@@
-				&& (!Case.bHasCombatSet || (DamageCapture.Value == Case.CapturedDamage && PoiseCapture.Value == Case.CapturedPoise)))) { return false; }
+				&& (!Case.bHasCombatSet || (
+					(FMath::IsNaN(Case.CapturedDamage) ? FMath::IsNaN(DamageCapture.Value) : DamageCapture.Value == Case.CapturedDamage)
+					&& (FMath::IsNaN(Case.CapturedPoise) ? FMath::IsNaN(PoiseCapture.Value) : PoiseCapture.Value == Case.CapturedPoise))))) { return false; }
+		if (!FMath::IsFinite(Case.CapturedDamage) || !FMath::IsFinite(Case.CapturedPoise))
+		{
+			if (!Test.TestTrue(Label + TEXT(" actual non-finite native capture and normal other input without SBC"),
+				Case.bHasCombatSet && Case.bReject && Spec.SetByCallerTagMagnitudes.IsEmpty() && Spec.SetByCallerNameMagnitudes.IsEmpty()
+				&& DamageCapture.bSucceeded && PoiseCapture.bSucceeded
+				&& ((!FMath::IsFinite(Case.CapturedDamage) && !FMath::IsFinite(DamageCapture.Value)
+					&& FMath::IsFinite(Case.CapturedPoise) && PoiseCapture.Value == Case.CapturedPoise)
+					|| (!FMath::IsFinite(Case.CapturedPoise) && !FMath::IsFinite(PoiseCapture.Value)
+						&& FMath::IsFinite(Case.CapturedDamage) && DamageCapture.Value == Case.CapturedDamage)))) { return false; }
+		}
@@
-	// T1a/T1b: seven scenario families. Non-finite real captures await a separate lease.
+	// T1a/T1b/T1c: eight scenario families through the real native capture/production execution path.
@@
-		{TEXT("NegativeInfinityPoiseOverride"), true, 12, 4, {}, -Infinity, 0, 0, true, TEXT("valid"), TEXT("non-finite")}
+		{TEXT("NegativeInfinityPoiseOverride"), true, 12, 4, {}, -Infinity, 0, 0, true, TEXT("valid"), TEXT("non-finite")},
+		// 8. Native getter must succeed with a non-finite capture; the other capture remains normal.
+		{TEXT("NaNDamageCapture"), true, NaN, 4, {}, {}, 0, 0, true, TEXT("non-finite"), TEXT("valid")},
+		{TEXT("PositiveInfinityDamageCapture"), true, Infinity, 4, {}, {}, 0, 0, true, TEXT("non-finite"), TEXT("valid")},
+		{TEXT("NegativeInfinityDamageCapture"), true, -Infinity, 4, {}, {}, 0, 0, true, TEXT("non-finite"), TEXT("valid")},
+		{TEXT("NaNPoiseCapture"), true, 12, NaN, {}, {}, 0, 0, true, TEXT("valid"), TEXT("non-finite")},
+		{TEXT("PositiveInfinityPoiseCapture"), true, 12, Infinity, {}, {}, 0, 0, true, TEXT("valid"), TEXT("non-finite")},
+		{TEXT("NegativeInfinityPoiseCapture"), true, 12, -Infinity, {}, {}, 0, 0, true, TEXT("valid"), TEXT("non-finite")}
```
