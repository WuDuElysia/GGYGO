# 第 06 批 Combatants 验证记录

更新：2026-10-04。Host Refresh caller query三文件修正已落盘、有限静态核对并冻结交回，仅OriginalScope改读原Host/端点/opaque槽，原Context/H、ASC权限及自身Commit/Receipt保持；Release/H1/H2/H3与接口原文不变。修正版未编译/UE；Gate57及单叶成功为旧DLL证据，两次实际Entry Refresh/Release失败仍保留，待统筹新DLL同Entry必要冒烟。R0原2 Fail/12 errors/0 warnings未复测，metadata退休不是Clear，Teams未放行。

## 实现结果

- C1：`AGGYGOCharacterSlot` 的 `PawnData` 与 `AGGYGOBossState` 的 `BossDefinition` 使用 RepNotify；Authority 初始化和客户端复制回调复用幂等 ASC 规则配置入口。AbilitySet 授予仍位于 Authority 守卫后的初始化函数内。
- C2：Authority Attach 在副作用前拒绝 PawnExtension 已缓存另一 ASC 的跨宿主抢占；死亡宿主拒绝不同的新 Avatar，同一 Avatar 重复 Attach 幂等。客户端 OnRep 直接按复制结果收敛。
- C3：`AGGYGOCombatantState::EndPlay` 在服务器与客户端共用本地清理 helper，移除销毁订阅并清绑定，销毁期不调用 `ForceNetUpdate`。
- C4：`UGGYGOPawnExtensionComponent::UninitializeAbilitySystem(ExpectedASC)` 对 ExpectedASC 不匹配无操作；匹配时先清本地缓存，仅由当前 Avatar 修改共享 ASC，最后广播一次。踢旧 Avatar 的调用点传入 `InASC`。宿主另行清理自己 ASC 中仍指向旧 Pawn 的 Avatar，避免 ExpectedASC 拒绝后留下悬空 ActorInfo。
- C5：Health 死亡阶段只向当前 Avatar ASC 单调投影；Started 写 Dying，Finished 保持 Dying 并写 Dead，晚绑定补投影但不重放事件，解绑不清死亡标签，NotDead 不隐式复活。

## 文件与自动化覆盖

- 实际 10 个生产文件：
  - `Source/GGYGO/Teams/GGYGOCharacterSlot.h`
  - `Source/GGYGO/Teams/GGYGOCharacterSlot.cpp`
  - `Source/GGYGO/AI/Boss/GGYGOBossState.h`
  - `Source/GGYGO/AI/Boss/GGYGOBossState.cpp`
  - `Source/GGYGO/Combatants/GGYGOCombatantState.h`
  - `Source/GGYGO/Combatants/GGYGOCombatantState.cpp`
  - `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h`
  - `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp`
  - `Source/GGYGO/Character/Components/GGYGOHealthComponent.h`
  - `Source/GGYGO/Character/Components/GGYGOHealthComponent.cpp`
- 实际 6 个新增测试文件：
  - `Source/GGYGO/Combatants/Tests/GGYGOCombatantConfigReplicationTestTypes.h`
  - `Source/GGYGO/Combatants/Tests/GGYGOCombatantConfigReplicationTest.cpp`
  - `Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTestTypes.h`
  - `Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp`
  - `Source/GGYGO/Combatants/Tests/GGYGOCombatantDeathProjectionTestTypes.h`
  - `Source/GGYGO/Combatants/Tests/GGYGOCombatantDeathProjectionTest.cpp`
- 三组测试源码注册的全部自动化名：
  - `GGYGO.Combatants.Config.ClientReplicationCallbacks`
  - `GGYGO.Combatants.Binding.OwnershipAndDeathGuards`
  - `GGYGO.Combatants.Binding.ExpectedASCAndEndPlay`
  - `GGYGO.Combatants.DeathProjection.MonotonicAndPersistent`
  - `GGYGO.Combatants.DeathProjection.LateBindingAndAvatarIdentity`
- 未修改 Build.cs、Hero/Camera、ASC/HealthSet、Combat Trace/HitContext/Cue、生产资产、全局 Obsidian 入口、总台账或并行排程。

## 统筹退回修正

1. Pawn 交叉审查发现 `InitializeAbilitySystem` 踢除 `InASC` 的 ExistingAvatar 时仍调用无参数解绑。已改为 `OtherExtensionComponent->UninitializeAbilitySystem(InASC)`；旧 PawnExtension 若已缓存 OtherASC，迟到清理不会广播或清 OtherASC。
2. Host 交叉审查发现 PawnExtension 因 ExpectedASC 不匹配拒绝后，本宿主 ASC 仍可能以旧 Pawn 为 Avatar。已把两层清理拆开：先尝试 ExpectedASC 保护的扩展解绑，再独立检查本宿主 ASC 的 Avatar；仍匹配旧 Pawn 时用 `InitAbilityActorInfo(this, nullptr)` 保留 Owner 并清 Avatar。Binding 测试源码补了“OtherASC 保持、新宿主不受损、旧宿主自清理”的断言。

## 已执行静态验证

- 10 个已跟踪生产文件执行 `git diff --check`：无输出。6 个新增测试文件另行扫描行尾空白：`TEST_TRAILING_WHITESPACE=none`。
- `rg` 核对全部 `UninitializeAbilitySystem` 调用：跨对象清理均传 ExpectedASC；Pawn 自身 EndPlay/Controller 本地清理保留默认参数。
- 人工交叉审查 Authority 拒绝顺序、客户端 OnRep 路径、Owner 保留、SurvivesDeath 排除、Health Avatar 身份门禁与三组测试断言。
- 两张 Canvas 均可被 `ConvertFrom-Json` 解析：Combatants 8 节点/6 边，Character 初始化 10 节点/8 边；节点 ID 无重复，所有边引用均存在。
- Combatants 结构文档中的 Teams、BossAI、Character 与计划蓝图链接目标存在。

## 架构核对

- 状态唯一：持久 ASC/属性/GE/冷却/死亡标签仍归 CombatantState；PawnExtension 只持本地缓存；HealthComponent 只持死亡阶段。
- 依赖与职责：未新增循环依赖、第二套执行链或帧调度器；玩家/Boss 配置仍在各自派生宿主，Hero 解绑协调入口保持唯一。
- 清理路径：Detach、OnRep 更换、PawnExtension EndPlay 与 CombatantState EndPlay 都有明确身份门禁；旧宿主不会清新宿主 ASC，也不会保留自己的旧 Avatar。
- 范围边界：未实现复活、死亡后重新挂接或完整 Boss 换形态事务。

## 统一门禁结果

- 2026-09-30 完整 `GGYGOEditor Win64 Development` 构建成功。初次构建发现测试夹具把 `TObjectPtr<UGGYGOHealthSet>` 直接传给模板导致类型推导失败；修正为 `HealthSet.Get()` 后重新构建成功。
- `Saved/AutomationReports/ModuleRepairGate_20260930_11/index.json` 实际执行 45 项项目自动化。第 06 批以下五项全部成功：
  - `GGYGO.Combatants.Config.ClientReplicationCallbacks`
  - `GGYGO.Combatants.Binding.OwnershipAndDeathGuards`
  - `GGYGO.Combatants.Binding.ExpectedASCAndEndPlay`
  - `GGYGO.Combatants.DeathProjection.MonotonicAndPersistent`
  - `GGYGO.Combatants.DeathProjection.LateBindingAndAvatarIdentity`
- 同轮总结果为 44 成功、1 失败；唯一失败是第 12 批 `GGYGO.Combat.MeleeTrace.SafetyAndCoverage` 的 PhysicalMaterial 测试夹具，归 Combat 命中链路，不属于第 06 批。第 06 批因此完成源码/UHT/构建/专项自动化门禁并释放 07、08 与 14b 的前置依赖。
- 尚未执行真实 PIE、联机或专服验证；复活、死亡后重新挂接与完整 Boss 换形态事务仍保持范围外/待办状态。

## A9 / 06-L1-I 宿主调用边界准入：生产冻结记录（2026-09-30）

### 当前结果与门禁归属

- 唯一结果已落盘：宿主私有 permission 默认开放；所有 EndPlay 在清理及 Super 之前关闭；仅真实 IsActorBeginningPlay && IsValid(this) && !IsActorBeingDestroyed 入口在 Super::BeginPlay 前重开，Super 后不再覆盖关闭。首次 PreBegin 保留；不自动恢复旧 Avatar。
- Attach 非空入口和旧 Avatar Detach 返回后提交前校验宿主/目标 Pawn；Synchronize 非空入口和旧绑定 clear 返回后 Initialize 前复核。OnRep 共用同步门禁。新增准入拒绝为 Error，包含 Combatants、入口、宿主、ASC、目标 Pawn、原因。
- null Attach、Detach、ClearLocal 的必要清理继续合法。Detach 完成身份清理后若关闭，停止外层继续；Attach/Detach 的 ForceNetUpdate 均受当前准入限制。空 Avatar 的 Owner 保留分支不作为绑定成功。
- Build29 于本步前由统筹执行：完整构建 Succeeded、5 actions、15.87 秒、exit0；常规项目 63/63 Success，UE26112 已退出。这是本步前基线，不是 A9 编译、测试或流送证明；第28次编译失败仍保留为历史事实。
- 本次仅生产源码静态核对并冻结；没有执行 UHT、构建、UE、Git 或自动化，没有修改测试/共享接口/资产/Obsidian/全局记录。

### 实际静态证据

- 实现后两文件全文与本步前快照加已登记逐项修改完全一致，没有额外源码差异。
- PostInitializeComponents、GetLifetimeReplicatedProps、OnRep_AvatarPawn、HandleAvatarDestroyed、ClearLocalAvatarBinding 的方法文本与本步前逐字一致。
- 两个生产文件保持原 LF 和 UTF-8；逐行检查无行尾空白。实际 diff 由本步前内存快照与当前文件生成，未使用 Git。
- 人工核对：EndPlay 首关；BeginPlay 只在原生 BeginningPlay 且有效/非销毁时重开，Super 后不再写 permission；Attach 的 null 清理分支早于新门禁；Detach/clear 返回后到宿主非空提交/Initialize 前有检查；关闭后两个 ForceNetUpdate 均被阻止。
- ClearLocal 的 ExpectedASC、共享 ASC Avatar 身份比较、Owner=this/Avatar=null 清理和退订保持原文。SurvivesDeath 取消排除、Hero 唯一解绑链留在只读 PawnExtension/Hero；本步未接第二通知或执行链。
- 状态/依赖核对：permission 只归宿主管准入，不复制、不公开、不缓存原生状态；ASC/属性/GE/冷却/死亡规则所有权不变。没有新增 include、循环依赖、Ticker、调度器或隐式业务替代。

| 生产文件 | 本步前字节 / SHA256 | 冻结字节 / SHA256 |
| --- | --- | --- |
| GGYGOCombatantState.h | 3885 / 645D6F469631E2C716508EE7F41C8EDBAF7D5B33652FD9DA7E8C253067EA300A | 4370 / A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF |
| GGYGOCombatantState.cpp | 6549 / A049826FBB19820A5D26277C18983CE482A03959E064E39BDF5529E02C7EB47C | 8950 / 6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84 |

### 未验与范围限制

- 尚未编译或运行本步源码；既有直接 InvokeEndPlayForTest 的夹具不能证明真实 Destroy、BeginPlay 或流送路径。
- 后续独立真实矩阵：首次 PreBegin/幂等；真实 Destroy 的 World 通知及 EndPlay 解绑回调重入；Attach Detach 回调和 Synchronize clear 回调销毁宿主/目标 Pawn；RemovedFromWorld 后同一保留实例再次 AddToWorld；关闭期客户端 Avatar 复制；ExpectedASC/Owner/SurvivesDeath/Hero 原链回归；BeginPlay 延迟 Destroy 观察。
- 本步只覆盖宿主可控制的调用边界；PawnExtension::InitializeAbilitySystem 和 ASC::InitAbilityActorInfo 内部回调销毁后继续执行/写入未关闭，须所属接口另行拆分，不能由调用前校验推导为完整初始化事务安全。
- 普通开放态 Attach/Detach 同步后继覆盖、私有 bActorWantsDestroyDuringBeginPlay 意图、任意 Pawn 非 Destroy EndPlay、BossEncounter 自有 bEndingPlay 保持范围外。permission 当前值也不是跨完整 EndPlay/BeginPlay 嵌套往返的事务代际凭证。
- 已只读核对 Obsidian 计划蓝图及相关结构/流程材料。本步影响 Combatants/结构.md、Combatants/GGYGO_结构_Combatants.canvas、Character/GGYGO_流程_角色初始化.canvas；需后续独立图文租约补准入、复制路径门禁及当前验证状态。本步未更新这些冻结文件，不宣称全模块已验收。

### 两个生产文件本步实际差异

```diff
--- Source/GGYGO/Combatants/GGYGOCombatantState.cpp (A9 baseline)
+++ Source/GGYGO/Combatants/GGYGOCombatantState.cpp (A9 current)
@@ -55,8 +55,22 @@
 	}
 }
 
+void AGGYGOCombatantState::BeginPlay()
+{
+	// RemovedFromWorld 后同一实例可再次进入原生 BeginPlay，准入只封住上次生命周期。
+	if (IsActorBeginningPlay() && IsValid(this) && !IsActorBeingDestroyed())
+	{
+		bAvatarBindingPermitted = true;
+	}
+
+	Super::BeginPlay();
+	// Super 内的回调可能已关闭准入，返回后不能再覆盖。
+}
+
 void AGGYGOCombatantState::EndPlay(const EEndPlayReason::Type EndPlayReason)
 {
+	// 必须早于解绑和 Super 的外部回调；所有 EndPlay 原因均关闭本次准入。
+	bAvatarBindingPermitted = false;
 	ClearLocalAvatarBinding(AvatarPawn);
 	Super::EndPlay(EndPlayReason);
 }
@@ -84,6 +98,11 @@
 		return;
 	}
 
+	if (!ValidateAvatarBinding(NewAvatar, TEXT("AttachAvatar.Entry")))
+	{
+		return;
+	}
+
 	UGGYGOPawnExtensionComponent* NewExtension =
 		UGGYGOPawnExtensionComponent::FindPawnExtensionComponent(NewAvatar);
 	if (!NewExtension)
@@ -117,12 +136,17 @@
 	if (bAvatarChanged)
 	{
 		DetachAvatar(AvatarPawn);
+		if (!ValidateAvatarBinding(NewAvatar, TEXT("AttachAvatar.AfterDetach")))
+		{
+			return;
+		}
+
 		AvatarPawn = NewAvatar;
 		AvatarPawn->OnDestroyed.AddUniqueDynamic(this, &ThisClass::HandleAvatarDestroyed);
 	}
 
 	SynchronizeAvatarBinding();
-	if (bAvatarChanged)
+	if (bAvatarChanged && IsAvatarBindingPermitted())
 	{
 		ForceNetUpdate();
 	}
@@ -151,9 +175,18 @@
 	}
 
 	ClearLocalAvatarBinding(OldAvatar);
+	if (!IsAvatarBindingPermitted())
+	{
+		// 身份限定的本地清理已完成，关闭后不继续外层同步或网络更新。
+		return;
+	}
+
 	AvatarPawn = nullptr;
 	SynchronizeAvatarBinding();
-	ForceNetUpdate();
+	if (IsAvatarBindingPermitted())
+	{
+		ForceNetUpdate();
+	}
 }
 
 void AGGYGOCombatantState::OnRep_AvatarPawn()
@@ -169,6 +202,11 @@
 void AGGYGOCombatantState::SynchronizeAvatarBinding()
 {
 	if (!AbilitySystemComponent)
+	{
+		return;
+	}
+
+	if (AvatarPawn && !ValidateAvatarBinding(AvatarPawn, TEXT("SynchronizeAvatarBinding.Entry")))
 	{
 		return;
 	}
@@ -186,6 +224,12 @@
 		{
 			AbilitySystemComponent->InitAbilityActorInfo(this, nullptr);
 		}
+		return;
+	}
+
+	// 清旧绑定可回调 EndPlay/Destroy；重新读取当前目标并在初始化调用前复核。
+	if (!ValidateAvatarBinding(AvatarPawn, TEXT("SynchronizeAvatarBinding.BeforeInitialize")))
+	{
 		return;
 	}
 
@@ -228,3 +272,47 @@
 		AvatarPawn = nullptr;
 	}
 }
+
+bool AGGYGOCombatantState::IsAvatarBindingPermitted() const
+{
+	return bAvatarBindingPermitted && IsValid(this) && !IsActorBeingDestroyed();
+}
+
+bool AGGYGOCombatantState::ValidateAvatarBinding(APawn* AvatarToBind, const TCHAR* EntryPoint) const
+{
+	const TCHAR* RejectionReason = nullptr;
+	if (!IsAvatarBindingPermitted())
+	{
+		if (!IsValid(this))
+		{
+			RejectionReason = TEXT("宿主无效或已进入垃圾回收状态");
+		}
+		else if (IsActorBeingDestroyed())
+		{
+			RejectionReason = TEXT("宿主正在原生销毁流程中");
+		}
+		else
+		{
+			RejectionReason = TEXT("本次生命周期的绑定准入已关闭");
+		}
+	}
+	else if (!IsValid(AvatarToBind))
+	{
+		RejectionReason = TEXT("目标 Pawn 无效或已进入垃圾回收状态");
+	}
+	else if (AvatarToBind->IsActorBeingDestroyed())
+	{
+		RejectionReason = TEXT("目标 Pawn 正在原生销毁流程中");
+	}
+
+	if (!RejectionReason)
+	{
+		return true;
+	}
+
+	UE_LOG(LogGGYGOAbilitySystem, Error,
+		TEXT("[Combatants] %s: 宿主 [%s] ASC [%s] 拒绝绑定 Avatar [%s]，原因：%s。"),
+		EntryPoint, *GetPathNameSafe(this), *GetPathNameSafe(AbilitySystemComponent),
+		*GetPathNameSafe(AvatarToBind), RejectionReason);
+	return false;
+}
--- Source/GGYGO/Combatants/GGYGOCombatantState.h (A9 baseline)
+++ Source/GGYGO/Combatants/GGYGOCombatantState.h (A9 current)
@@ -63,6 +63,7 @@
 
 protected:
 	virtual void PostInitializeComponents() override;
+	virtual void BeginPlay() override;
 	virtual void EndPlay(const EEndPlayReason::Type EndPlayReason) override;
 	virtual void GetLifetimeReplicatedProps(TArray<FLifetimeProperty>& OutLifetimeProps) const override;
 
@@ -95,4 +96,14 @@
 	/** 当前 Avatar。复制后客户端会重新建立本地 AbilityActorInfo。 */
 	UPROPERTY(ReplicatedUsing = OnRep_AvatarPawn)
 	TObjectPtr<APawn> AvatarPawn;
+
+private:
+	/** 只读取本次生命周期准入与原生销毁状态，不限制必要清理。 */
+	bool IsAvatarBindingPermitted() const;
+
+	/** 非空绑定调用边界的校验与明确诊断；不提供绑定成功结果。 */
+	bool ValidateAvatarBinding(APawn* AvatarToBind, const TCHAR* EntryPoint) const;
+
+	/** 首次 PreBegin 可绑定；EndPlay 关闭，仅真实下一次 BeginPlay 入口重开。 */
+	bool bAvatarBindingPermitted = true;
 };
```

- 停止点：生产源码已冻结；本记录与 Subleases 仅追加实际内容，保持各自本步前字节前缀。四文件哈希在交回消息提供；未自动授予后续测试、图文、构建或 Teams 清理。

### A9 实际写入方式、失败与读回证据

- 原源码基线为 h 645D6F469631E2C716508EE7F41C8EDBAF7D5B33652FD9DA7E8C253067EA300A / cpp A049826FBB19820A5D26277C18983CE482A03959E064E39BDF5529E02C7EB47C。
- 早期 shell WriteAllText 对两源码均报告 Access denied；错误非终止，exit0 和 A9_SOURCE_WRITTEN 尾部提示不能证明写入。该尝试后实际读回哈希仍为以上原值。更早的唯一匹配校验失败也未写入。
- 首次 apply_patch 因匹配截断在半行而校验失败；补足完整行上下文后 apply_patch 成功。成功后的全文恰为基线加已登记修改，哈希变为上表 A83D67A5… / 6B53885E…，与统筹只读观察相符。因此两源码实际成功写入方式仅为 apply_patch，没有再次套补丁。
- 两记录此前实际由 shell AppendAllText 追加，Subleases 新增尾部曾调整 LF；没有覆盖原字节前缀。收到统筹最新本地编辑方式要求后，此补充使用 apply_patch，并停止 shell 写入。不把记录的实际方式冒称 apply_patch。
- 未改 ACL、文件属性或链接；本步所有动态验证仍未执行。最终四文件读回/哈希与原记录前缀复核后交回冻结。

## A12 / 06-L1-T1 真实 Destroy 拒绝清理回调重绑：静态冻结记录（2026-10-01）

### 唯一结果与门禁归属

- 新增唯一叶 GGYGO.Combatants.Binding.RealDestroyRejectsCleanupReattach；仅既有 GGYGOCombatantBindingLifecycleTest.cpp 增加独立真实 World 夹具和测试，旧两叶/旧夹具/已有 TestTypes 原文保持，生产接口冻结。
- 夹具执行原生 UGameInstance::InitializeStandalone，确认私有 GI/WorldContext/ComponentManager；显式 URL 使用 AGameModeBase::StaticClass 路径并断言精确类，确认 GameState 与 InitializeActorsForPlay 后真实 World::BeginPlay。四目标 Actor/其组件、ASC 与 PawnExtension 的初始化/来源/BeginPlay 均有前置断言；任何失败 return false 并由独立 RAII 清理，无默认替代。
- 正常绑定旧 Pawn 后先验证 OtherASC ExpectedASC 不匹配不改变完整观察快照、OtherHost/OtherASC 和通知计数。Probe 用 CreateSP 弱共享绑定，只有旧 Extension Uninitialized 回调尝试一次候选 Attach。
- 验证调用为 Host->Destroy()，不是手工 Actor EndPlay 或单独 DispatchBeginPlay；退出的 World::EndPlay(Quit) 仅在目标 Destroy 及断言后用于释放剩余 World 生命周期，不作为被验收动作。
- 完整预期正文由实际对象路径构造：[Combatants] AttachAvatar.Entry: 宿主 [HostPath] ASC [ASCPath] 拒绝绑定 Avatar [CandidatePath]，原因：宿主正在原生销毁流程中。仅登记 AddExpectedErrorPlain + Exact + Occurrences=1；生产冻结源码使用 Error。内置预期消息 API 按原生机制处理，未新增日志吞噬或宽匹配。
- 核心边界：World OnActorDestroyed 必须先观察有效/BeingDestroyed/尚 BegunPlay；Extension Uninitialized 观察缓存与 ASC Avatar 已空且 Owner 保留，执行唯一 Attach 并再次观察无候选提交；World OnActorRemovedFromWorld 在 EndPlay 后、MarkAsGarbage 前取证完整清理。
- 断言计数为 WorldDestroyed=1、OldUninitialized=1、AttachAttempt=1、WorldRemoved=1、CandidateInitialized=0；事件次序必须 NativeDestroy -> Uninitialized -> Removed。最后 Destroy 返回成功，Garbage 前复制源 Avatar/ASC Avatar/旧新缓存为空、旧新 Pawn OnDestroyed 均不包含宿主 Handler，Owner仍为宿主；返回后仅检查原生 IsValid 已为 false。
- 析构先关闭 armed 并移除两个 World handler，保持 GI/Manager 至剩余 Actor Destroy 与 World EndPlay 完成；再 Shutdown/DestroyWorld/context、清临时包 dirty、恢复三网络加密原始委托并释放 GI。弱共享接收者过期后不会被剩余组件委托调用，前置失败同样清理。
- 第30次统筹门禁在本测试前：完整构建 Succeeded，7 actions/43.46秒/UHT5/exit0；项目63 Success、叶诊断0，报告 ModuleRepairGate_20261001_30/index.json，2026-09-30 16:48:53 UTC，SHA256 65A1C9387911E0A4B64C04236C7B8F46525D8266D0878B93EA267B56E0BEBD23，13源码 hash 前后保持，三个 UE已退出。有限证明 A9 已编译及既有回归；不证明本新增叶已编译/运行。不覆盖或删除先前 A9 未编译时的历史记录。

### 已执行的静态证据与保护

- 实现后全文精确等于本步前源码加登记的新直接头及独立测试段，没有额外源码差异；实际 diff +341 / -0 行。移除新增内容可逐字恢复旧完整 cpp，故原类构造、旧 fixture/helper 和两个旧测试保持原文。
- 新增部分没有 InvokeEndPlayForTest 或 DispatchBeginPlay，只有清理探针一个 Host->AttachAvatar(CandidatePawn) 调用点及一条完整 Plain/Exact/1 预期；注册宏2 -> 3，无重复叶。
- 测试 cpp 保持 UTF-8 无 BOM/原 LF，逐行无行尾空白。直接接口对照本地原生 GameInstance/World/GameMode/GameState、SparseDelegate::Contains、CreateSP、AutomationTest API；人工核对所有失败前置、回调与析构资源顺序。本静态核对不是编译或动态执行。
- 类型/生产保护实际读回：TestTypes.h = A329AECDA0988E6109721BB3D47D8E1571990F1A18F62D3325752027033FAE17；CombatantState.h = A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF；CombatantState.cpp = 6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84。未写这些文件。
- 旧测试 cpp 基线：8596 字节 / A837FD014A1322F81D94B3EA119791F9295C576168F65F4BAFC6213E61F29A77；本步静态冻结：26352 字节 / 35E97151BAD47F8239F66B9C82F9A99CA9BB4EC7360792ABC49E82E0CD2745C4。
- 唯一生产归属仍是 CombatantState 的准入与 ASC/PawnExtension 原绑定/清理链；测试快照仅保留同步窗口读取值，不复制/授予业务状态，无新生产依赖、UCLASS、配置或执行机制。
- 三获授文件编辑均为 apply_patch；两记录只追加且原字节前缀保留。未运行 UE/构建/Git/代理，未改 ACL/属性、TestTypes、共享生产、资产、Obsidian或全局入口。

### 未运行与未关闭边界

- 新叶尚未经过 UHT/完整编译、UE自动化或任何真实执行，所有上述观察/计数/清理断言目前仅是已写源码，不能标记为已验证。下一统一构建/新 DLL 执行由统筹排队安排。
- 本步不混入 RemovedFromWorld 同实例重进、Initialize 内部回调后继续写入、普通 successor、私有 BeginPlay 延迟 Destroy、Teams清理。窗口外源问题原样保留，不因本步添加测试而关闭。
- Owner/订阅在 Garbage 前快照取证；原生 Actor/组件垃圾标记和 ASC OnUnregister/DestroyActiveState 之后不继续宣称业务 Owner 可用。复制源 Avatar 字段检查不证明网络复制收敛。
- 最小 Pawn 没有 Hero 或活跃 SurvivesDeath 能力；本步保持其生产链及旧测试原文，不宣称完整 Hero/SurvivesDeath 动态覆盖。
- Obsidian现有 Combatants结构及两张结构/初始化图仍需后续授权更新准入和六项测试源码/本叶未运行状态，本步未写，文档一致性仍待收口。

### 单测试 cpp 本步实际差异

```diff
--- Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp (A12 baseline)
+++ Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp (A12 current)
@@ -26,6 +26,13 @@
 }
 
 #if WITH_DEV_AUTOMATION_TESTS
+#include "Components/GameFrameworkComponentManager.h"
+#include "Engine/GameInstance.h"
+#include "Engine/NetworkDelegates.h"
+#include "GameFramework/GameModeBase.h"
+#include "GameFramework/GameStateBase.h"
+#include "Templates/SharedPointer.h"
+
 namespace
 {
 	struct FCombatantBindingTestWorld
@@ -205,4 +212,338 @@
 
 	return true;
 }
+
+namespace
+{
+	/** Values captured while the destroyed host is still valid, before MarkAsGarbage. */
+	struct FCombatantRealDestroySnapshot
+	{
+		bool bHostValid = false;
+		bool bHostBeingDestroyed = false;
+		bool bHostHasBegunPlay = false;
+		APawn* ReplicatedAvatar = nullptr;
+		AActor* OwnerActor = nullptr;
+		AActor* ASCAvatar = nullptr;
+		UGGYGOAbilitySystemComponent* OldCachedASC = nullptr;
+		UGGYGOAbilitySystemComponent* CandidateCachedASC = nullptr;
+		bool bOldDestroyedSubscription = false;
+		bool bCandidateDestroyedSubscription = false;
+	};
+
+	/** Owns a real playing World and only observes the synchronous native Destroy window. */
+	struct FCombatantRealDestroyFixture : TSharedFromThis<FCombatantRealDestroyFixture>
+	{
+		UEngine* Engine = GEngine;
+		TStrongObjectPtr<UGameInstance> GameInstance;
+		UWorld* World = nullptr;
+		UGameFrameworkComponentManager* Manager = nullptr;
+		AGGYGOCombatantBindingTestState* Host = nullptr;
+		AGGYGOCombatantBindingTestState* OtherHost = nullptr;
+		AGGYGOCombatantBindingTestPawn* OldPawn = nullptr;
+		AGGYGOCombatantBindingTestPawn* CandidatePawn = nullptr;
+		UGGYGOAbilitySystemComponent* ASC = nullptr;
+		UGGYGOAbilitySystemComponent* OtherASC = nullptr;
+		UGGYGOPawnExtensionComponent* OldExtension = nullptr;
+		UGGYGOPawnExtensionComponent* CandidateExtension = nullptr;
+		bool bGameInstanceInitialized = false;
+		bool bProbeArmed = false;
+		FDelegateHandle DestroyedHandle;
+		FDelegateHandle RemovedHandle;
+		FNetDelegates::FReceivedNetworkEncryptionToken SavedEncryptionToken = FNetDelegates::OnReceivedNetworkEncryptionToken;
+		FNetDelegates::FReceivedNetworkEncryptionAck SavedEncryptionAck = FNetDelegates::OnReceivedNetworkEncryptionAck;
+		FNetDelegates::FReceivedNetworkEncryptionFailure SavedEncryptionFailure = FNetDelegates::OnReceivedNetworkEncryptionFailure;
+		int32 DestroyedCount = 0;
+		int32 UninitializedCount = 0;
+		int32 ReattachAttemptCount = 0;
+		int32 CandidateInitializedCount = 0;
+		int32 RemovedCount = 0;
+		TArray<FName> Events;
+		FCombatantRealDestroySnapshot NativeDestroy;
+		FCombatantRealDestroySnapshot CleanupBeforeAttach;
+		FCombatantRealDestroySnapshot CleanupAfterAttach;
+		FCombatantRealDestroySnapshot Removed;
+
+		bool CheckPlayingActor(FAutomationTestBase& Test, AActor* Actor) const
+		{
+			const FString Prefix = Actor->GetName() + TEXT(": ");
+			bool bPassed = Test.TestTrue(Prefix + TEXT("real initialized authority Actor completed BeginPlay"),
+				Actor->IsActorInitialized() && Actor->HasAuthority() && Actor->HasActorBegunPlay()
+				&& !Actor->IsActorBeginningPlay() && !Actor->IsActorBeingDestroyed());
+			TInlineComponentArray<UActorComponent*> Components(Actor);
+			for (UActorComponent* Component : Components)
+			{
+				bPassed &= Test.TestTrue(Prefix + Component->GetName() + TEXT(" registered and began play"),
+					Component->IsRegistered() && Component->HasBegunPlay());
+			}
+			return bPassed;
+		}
+
+		bool Initialize(FAutomationTestBase& Test)
+		{
+			if (!Test.TestNotNull(TEXT("real Engine"), Engine)) { return false; }
+			GameInstance.Reset(NewObject<UGameInstance>(Engine, NAME_None, RF_Transient));
+			if (!Test.TestNotNull(TEXT("base GameInstance"), GameInstance.Get())) { return false; }
+			bGameInstanceInitialized = true;
+			GameInstance->InitializeStandalone(FName(TEXT("GGYGOCombatantRealDestroyTestWorld")));
+			World = GameInstance->GetWorld();
+			if (!Test.TestNotNull(TEXT("GI-owned real World"), World)) { return false; }
+			const FWorldContext* Context = Engine->GetWorldContextFromWorld(World);
+			if (!Test.TestTrue(TEXT("private initialized Game World and owning GI context"),
+				World->IsGameWorld() && World->IsInitialized() && World->GetGameInstance() == GameInstance.Get()
+				&& Context && Context->World() == World && Context->OwningGameInstance == GameInstance.Get()
+				&& GameInstance->GetWorldContext() == Context && GameInstance->GetLocalPlayers().IsEmpty()))
+			{
+				return false;
+			}
+			Manager = UGameInstance::GetSubsystem<UGameFrameworkComponentManager>(GameInstance.Get());
+			if (!Test.TestNotNull(TEXT("real ComponentManager from base GI Init"), Manager)) { return false; }
+
+			FURL PlayURL;
+			PlayURL.AddOption(*FString::Printf(TEXT("game=%s"), *AGameModeBase::StaticClass()->GetPathName()));
+			if (!Test.TestTrue(TEXT("explicit native BaseGameMode creation"), World->SetGameMode(PlayURL)))
+			{
+				return false;
+			}
+			AGameModeBase* GameMode = World->GetAuthGameMode();
+			if (!Test.TestTrue(TEXT("actual GameMode is exactly the requested native class"),
+				GameMode && GameMode->GetClass() == AGameModeBase::StaticClass()))
+			{
+				return false;
+			}
+			World->InitializeActorsForPlay(PlayURL);
+			if (!Test.TestTrue(TEXT("real Actor initialization precedes World BeginPlay"),
+				World->AreActorsInitialized() && !World->HasBegunPlay())
+				|| !Test.TestNotNull(TEXT("native GameState for StartPlay"), World->GetGameState()))
+			{
+				return false;
+			}
+
+			Host = SpawnHost(World);
+			OtherHost = SpawnHost(World);
+			OldPawn = SpawnPawn(World);
+			CandidatePawn = SpawnPawn(World);
+			if (!Test.TestNotNull(TEXT("destroy target host"), Host)
+				|| !Test.TestNotNull(TEXT("ExpectedASC mismatch host"), OtherHost)
+				|| !Test.TestNotNull(TEXT("old Avatar"), OldPawn)
+				|| !Test.TestNotNull(TEXT("unbound candidate Avatar"), CandidatePawn))
+			{
+				return false;
+			}
+			ASC = Host->GetGGYGOAbilitySystemComponent();
+			OtherASC = OtherHost->GetGGYGOAbilitySystemComponent();
+			OldExtension = OldPawn->GetPawnExtensionForTest();
+			CandidateExtension = CandidatePawn->GetPawnExtensionForTest();
+			if (!Test.TestNotNull(TEXT("host ASC"), ASC)
+				|| !Test.TestNotNull(TEXT("other host ASC"), OtherASC)
+				|| !Test.TestNotNull(TEXT("old real PawnExtension"), OldExtension)
+				|| !Test.TestNotNull(TEXT("candidate real PawnExtension"), CandidateExtension))
+			{
+				return false;
+			}
+
+			World->BeginPlay();
+			if (!Test.TestTrue(TEXT("native World/GameMode/GameState completed BeginPlay"),
+				World->HasBegunPlay() && GameMode->HasActorBegunPlay() && World->GetGameState()->HasActorBegunPlay()))
+			{
+				return false;
+			}
+			bool bPassed = CheckPlayingActor(Test, Host);
+			bPassed &= CheckPlayingActor(Test, OtherHost);
+			bPassed &= CheckPlayingActor(Test, OldPawn);
+			bPassed &= CheckPlayingActor(Test, CandidatePawn);
+			bPassed &= Test.TestTrue(TEXT("both persistent ASCs initialized with their own Owner and no Avatar"),
+				ASC != OtherASC && ASC->HasBeenInitialized() && OtherASC->HasBeenInitialized()
+				&& ASC->GetOwnerActor() == Host && OtherASC->GetOwnerActor() == OtherHost
+				&& !ASC->GetAvatarActor() && !OtherASC->GetAvatarActor()
+				&& !Host->GetAvatarPawn() && !OtherHost->GetAvatarPawn());
+			bPassed &= Test.TestTrue(TEXT("both real PawnExtensions use this GI manager and reached Spawned"),
+				UGameFrameworkComponentManager::GetForActor(OldPawn) == Manager
+				&& UGameFrameworkComponentManager::GetForActor(CandidatePawn) == Manager
+				&& OldExtension->GetInitState() == GGYGOGameplayTags::InitState_Spawned
+				&& CandidateExtension->GetInitState() == GGYGOGameplayTags::InitState_Spawned
+				&& !OldExtension->GetGGYGOAbilitySystemComponent()
+				&& !CandidateExtension->GetGGYGOAbilitySystemComponent());
+			bPassed &= Test.TestNull(TEXT("old Pawn has no second Pawn-owned ASC"),
+				OldPawn->FindComponentByClass<UGGYGOAbilitySystemComponent>());
+			bPassed &= Test.TestNull(TEXT("candidate Pawn has no second Pawn-owned ASC"),
+				CandidatePawn->FindComponentByClass<UGGYGOAbilitySystemComponent>());
+			return bPassed;
+		}
+
+		FCombatantRealDestroySnapshot Capture() const
+		{
+			FCombatantRealDestroySnapshot Snapshot;
+			Snapshot.bHostValid = IsValid(Host);
+			Snapshot.bHostBeingDestroyed = Host->IsActorBeingDestroyed();
+			Snapshot.bHostHasBegunPlay = Host->HasActorBegunPlay();
+			Snapshot.ReplicatedAvatar = Host->GetAvatarPawn();
+			Snapshot.OwnerActor = ASC->GetOwnerActor();
+			Snapshot.ASCAvatar = ASC->GetAvatarActor();
+			Snapshot.OldCachedASC = OldExtension->GetGGYGOAbilitySystemComponent();
+			Snapshot.CandidateCachedASC = CandidateExtension->GetGGYGOAbilitySystemComponent();
+			const FName HandlerName(TEXT("HandleAvatarDestroyed"));
+			Snapshot.bOldDestroyedSubscription = OldPawn->OnDestroyed.Contains(Host, HandlerName);
+			Snapshot.bCandidateDestroyedSubscription = CandidatePawn->OnDestroyed.Contains(Host, HandlerName);
+			return Snapshot;
+		}
+
+		void InstallProbe()
+		{
+			// CreateSP keeps no strong fixture reference and skips expired receivers.
+			DestroyedHandle = World->AddOnActorDestroyedHandler(
+				FOnActorDestroyed::FDelegate::CreateSP(AsShared(), &FCombatantRealDestroyFixture::HandleNativeDestroy));
+			RemovedHandle = World->AddOnActorRemovedFromWorldHandler(
+				FOnActorRemovedFromWorld::FDelegate::CreateSP(AsShared(), &FCombatantRealDestroyFixture::HandleRemoved));
+			OldExtension->OnAbilitySystemUninitialized_Register(
+				FSimpleMulticastDelegate::FDelegate::CreateSP(AsShared(), &FCombatantRealDestroyFixture::HandleUninitialized));
+			CandidateExtension->OnAbilitySystemInitialized_RegisterAndCall(
+				FSimpleMulticastDelegate::FDelegate::CreateSP(AsShared(), &FCombatantRealDestroyFixture::HandleCandidateInitialized));
+		}
+
+		void HandleNativeDestroy(AActor* Actor)
+		{
+			if (!bProbeArmed || Actor != Host) { return; }
+			++DestroyedCount;
+			Events.Add(FName(TEXT("NativeDestroy")));
+			NativeDestroy = Capture();
+		}
+
+		void HandleUninitialized()
+		{
+			++UninitializedCount;
+			if (!bProbeArmed) { return; }
+			Events.Add(FName(TEXT("Uninitialized")));
+			CleanupBeforeAttach = Capture();
+			++ReattachAttemptCount;
+			Host->AttachAvatar(CandidatePawn);
+			CleanupAfterAttach = Capture();
+		}
+
+		void HandleCandidateInitialized()
+		{
+			++CandidateInitializedCount;
+		}
+
+		void HandleRemoved(AActor* Actor)
+		{
+			if (!bProbeArmed || Actor != Host) { return; }
+			++RemovedCount;
+			Events.Add(FName(TEXT("Removed")));
+			Removed = Capture();
+		}
+
+		~FCombatantRealDestroyFixture()
+		{
+			bProbeArmed = false;
+			if (World)
+			{
+				World->RemoveOnActorDestroyedHandler(DestroyedHandle);
+				World->RemoveOnActorRemovedFromWorldHandler(RemovedHandle);
+				// Keep the real GI/ComponentManager alive for Actor and component EndPlay on every exit.
+				if (IsValid(OldPawn)) { OldPawn->Destroy(); }
+				if (IsValid(CandidatePawn)) { CandidatePawn->Destroy(); }
+				if (IsValid(Host)) { Host->Destroy(); }
+				if (IsValid(OtherHost)) { OtherHost->Destroy(); }
+				World->EndPlay(EEndPlayReason::Quit);
+			}
+			if (bGameInstanceInitialized && GameInstance.IsValid()) { GameInstance->Shutdown(); }
+			if (World)
+			{
+				World->DestroyWorld(false);
+				Engine->DestroyWorldContext(World);
+				if (UPackage* Package = World->GetPackage()) { Package->SetDirtyFlag(false); }
+			}
+			// Base GI Init/Shutdown mutate these globals; restore all three original bindings.
+			FNetDelegates::OnReceivedNetworkEncryptionToken = SavedEncryptionToken;
+			FNetDelegates::OnReceivedNetworkEncryptionAck = SavedEncryptionAck;
+			FNetDelegates::OnReceivedNetworkEncryptionFailure = SavedEncryptionFailure;
+			GameInstance.Reset();
+		}
+	};
+}
+
+IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGGYGOCombatantRealDestroyReattachTest,
+	"GGYGO.Combatants.Binding.RealDestroyRejectsCleanupReattach",
+	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
+
+bool FGGYGOCombatantRealDestroyReattachTest::RunTest(const FString& Parameters)
+{
+	TSharedRef<FCombatantRealDestroyFixture> Fixture = MakeShared<FCombatantRealDestroyFixture>();
+	if (!Fixture->Initialize(*this)) { return false; }
+
+	Fixture->Host->AttachAvatar(Fixture->OldPawn);
+	const FCombatantRealDestroySnapshot Bound = Fixture->Capture();
+	bool bPassed = TestTrue(TEXT("normal live binding exists before native Destroy"),
+		Bound.bHostValid && !Bound.bHostBeingDestroyed && Bound.bHostHasBegunPlay
+		&& Bound.ReplicatedAvatar == Fixture->OldPawn && Bound.OwnerActor == Fixture->Host
+		&& Bound.ASCAvatar == Fixture->OldPawn && Bound.OldCachedASC == Fixture->ASC
+		&& !Bound.CandidateCachedASC && Bound.bOldDestroyedSubscription && !Bound.bCandidateDestroyedSubscription);
+	if (!bPassed) { return false; }
+
+	Fixture->InstallProbe();
+	bPassed &= TestTrue(TEXT("both native World observation handlers installed"),
+		Fixture->DestroyedHandle.IsValid() && Fixture->RemovedHandle.IsValid());
+	Fixture->OldExtension->UninitializeAbilitySystem(Fixture->OtherASC);
+	const FCombatantRealDestroySnapshot AfterMismatch = Fixture->Capture();
+	bPassed &= TestTrue(TEXT("ExpectedASC mismatch leaves all observed bindings and subscriptions unchanged"),
+		AfterMismatch.bHostValid == Bound.bHostValid
+		&& AfterMismatch.bHostBeingDestroyed == Bound.bHostBeingDestroyed
+		&& AfterMismatch.bHostHasBegunPlay == Bound.bHostHasBegunPlay
+		&& AfterMismatch.ReplicatedAvatar == Bound.ReplicatedAvatar && AfterMismatch.OwnerActor == Bound.OwnerActor
+		&& AfterMismatch.ASCAvatar == Bound.ASCAvatar && AfterMismatch.OldCachedASC == Bound.OldCachedASC
+		&& AfterMismatch.CandidateCachedASC == Bound.CandidateCachedASC
+		&& AfterMismatch.bOldDestroyedSubscription == Bound.bOldDestroyedSubscription
+		&& AfterMismatch.bCandidateDestroyedSubscription == Bound.bCandidateDestroyedSubscription);
+	bPassed &= TestTrue(TEXT("mismatched expected ASC and its host remain untouched"),
+		Fixture->OtherASC->GetOwnerActor() == Fixture->OtherHost && !Fixture->OtherASC->GetAvatarActor()
+		&& !Fixture->OtherHost->GetAvatarPawn());
+	bPassed &= TestTrue(TEXT("mismatch and probe installation trigger no notifications or Attach attempt"),
+		Fixture->DestroyedCount == 0 && Fixture->UninitializedCount == 0 && Fixture->ReattachAttemptCount == 0
+		&& Fixture->CandidateInitializedCount == 0 && Fixture->RemovedCount == 0 && Fixture->Events.IsEmpty());
+	if (!bPassed) { return false; }
+
+	const FString ExpectedRejection = FString::Printf(
+		TEXT("[Combatants] AttachAvatar.Entry: 宿主 [%s] ASC [%s] 拒绝绑定 Avatar [%s]，原因：宿主正在原生销毁流程中。"),
+		*GetPathNameSafe(Fixture->Host), *GetPathNameSafe(Fixture->ASC), *GetPathNameSafe(Fixture->CandidatePawn));
+	AddExpectedErrorPlain(ExpectedRejection, EAutomationExpectedErrorFlags::Exact, 1);
+	Fixture->bProbeArmed = true;
+	const bool bDestroyed = Fixture->Host->Destroy();
+	Fixture->bProbeArmed = false;
+
+	bPassed &= TestTrue(TEXT("real Actor::Destroy succeeds"), bDestroyed);
+	bPassed &= TestEqual(TEXT("native World destruction notification occurs once"), Fixture->DestroyedCount, 1);
+	bPassed &= TestEqual(TEXT("old Extension uninitialization occurs once"), Fixture->UninitializedCount, 1);
+	bPassed &= TestEqual(TEXT("only cleanup callback attempts one Attach"), Fixture->ReattachAttemptCount, 1);
+	bPassed &= TestEqual(TEXT("native post-EndPlay removal notification occurs once"), Fixture->RemovedCount, 1);
+	bPassed &= TestEqual(TEXT("candidate never broadcasts initialized"), Fixture->CandidateInitializedCount, 0);
+	const TArray<FName> ExpectedEvents{FName(TEXT("NativeDestroy")), FName(TEXT("Uninitialized")), FName(TEXT("Removed"))};
+	bPassed &= TestTrue(TEXT("actual native destruction, cleanup and post-EndPlay removal order"),
+		Fixture->Events == ExpectedEvents);
+	bPassed &= TestTrue(TEXT("native Destroy sets BeingDestroyed before routing actual EndPlay"),
+		Fixture->NativeDestroy.bHostValid && Fixture->NativeDestroy.bHostBeingDestroyed
+		&& Fixture->NativeDestroy.bHostHasBegunPlay);
+	bPassed &= TestTrue(TEXT("cleanup callback sees cleared local/ASC binding while retaining Owner"),
+		Fixture->CleanupBeforeAttach.bHostValid && Fixture->CleanupBeforeAttach.bHostBeingDestroyed
+		&& Fixture->CleanupBeforeAttach.bHostHasBegunPlay && Fixture->CleanupBeforeAttach.OwnerActor == Fixture->Host
+		&& !Fixture->CleanupBeforeAttach.ASCAvatar && !Fixture->CleanupBeforeAttach.OldCachedASC
+		&& !Fixture->CleanupBeforeAttach.CandidateCachedASC);
+	bPassed &= TestTrue(TEXT("rejected callback Attach cannot commit the candidate or replace cleanup identity"),
+		Fixture->CleanupAfterAttach.ReplicatedAvatar == Fixture->OldPawn
+		&& Fixture->CleanupAfterAttach.OwnerActor == Fixture->Host && !Fixture->CleanupAfterAttach.ASCAvatar
+		&& !Fixture->CleanupAfterAttach.OldCachedASC && !Fixture->CleanupAfterAttach.CandidateCachedASC
+		&& Fixture->CleanupAfterAttach.bOldDestroyedSubscription && !Fixture->CleanupAfterAttach.bCandidateDestroyedSubscription);
+	bPassed &= TestTrue(TEXT("post-EndPlay snapshot is captured while host remains valid before Garbage"),
+		Fixture->Removed.bHostValid && Fixture->Removed.bHostBeingDestroyed && !Fixture->Removed.bHostHasBegunPlay);
+	bPassed &= TestEqual(TEXT("Owner is retained at the native pre-Garbage cleanup boundary"),
+		Fixture->Removed.OwnerActor, static_cast<AActor*>(Fixture->Host));
+	bPassed &= TestNull(TEXT("replicated source Avatar is cleared before Garbage"), Fixture->Removed.ReplicatedAvatar);
+	bPassed &= TestNull(TEXT("ASC Avatar is cleared before Garbage"), Fixture->Removed.ASCAvatar);
+	bPassed &= TestNull(TEXT("old Extension cache is cleared before Garbage"), Fixture->Removed.OldCachedASC);
+	bPassed &= TestNull(TEXT("candidate Extension stays unbound before Garbage"), Fixture->Removed.CandidateCachedASC);
+	bPassed &= TestFalse(TEXT("old Pawn has no stale host OnDestroyed subscription"), Fixture->Removed.bOldDestroyedSubscription);
+	bPassed &= TestFalse(TEXT("candidate Pawn has no rejected host OnDestroyed subscription"), Fixture->Removed.bCandidateDestroyedSubscription);
+	bPassed &= TestFalse(TEXT("native Destroy marks the host invalid after all observed cleanup"), IsValid(Fixture->Host));
+	return bPassed;
+}
+
 #endif // WITH_DEV_AUTOMATION_TESTS
```

- 冻结停止点：源码已静态冻结，记录追加完成后交回三文件完整 hash/实际 diff 与保护证据；不自动构建或继续下一专项。

## A15 / 06-L1-T1-R1 原生 Owner 销毁时点期望校正（2026-10-01）

### Gate32实际结果与保留历史

- 第32次完整构建实际Succeeded，7 actions/41.25秒/UBA38.31秒/exit0，链接runtime与Editor新DLL；报告Saved/AutomationReports/ModuleRepairGate_20261001_32/index.json于06:40:13 UTC（北京时间14:40:13）为64叶62 Success/2 Fail，其它计数0。
- 本叶GGYGO.Combatants.Binding.RealDestroyRejectsCleanupReattach实际Fail、duration0.13791629672050476秒、1 Error/0 Warning；唯一错误在当时cpp537：Owner is retained at the native pre-Garbage cleanup boundary: The two values are not equal.
- 本地报告SHA256已读回为DFCE3543D4F570EB551BE3EC744589EB875671844635365DB37B077D2E0ABBFC。UE23112 exit0已退出；exit0不是叶通过，238source/14保护hash保持由统筹验证。另一失败属于Movement，本步不修改或关闭它。
- 本叶其它已执行断言未报失败，包括真实World/BeginPlay、NativeDestroy/Uninitialized清理、CleanupBefore/After Owner保留、一次完整精确重绑拒绝、ExpectedASC、缓存/订阅/计数及事件次序；叶总体仍Fail。报告只输出“不相等”，没有打印Owner实际值，不能据此称null已动态观察。
- 原A12静态记录/diff及“未运行”属于当时历史，逐字保留；当前由上述32真实Fail更新实施状态。本次A15修正尚未重新编译或运行，不能提前写成功。

### 准确的原生调用原因

1. Engine GameplayAbilities Private/AbilitySystemComponent.cpp3119–3130：SetOwnerActor(Host)设置逻辑Owner并AddUniqueDynamic订阅Owner的OnDestroyed；GetOwnerActor读取该缓存字段。
2. Engine Runtime/Engine Private/Actor.cpp3311–3316：AActor::Destroyed先RouteEndPlay(Destroyed)，后ReceiveDestroyed和OnDestroyed.Broadcast(this)。
3. AbilitySystemComponent.cpp3156–3162：OnOwnerActorDestroyed在InActor==OwnerActor时直接OwnerActor=nullptr并标记复制属性dirty，先于World Removed。它不等同于Garbage导致的弱引用失效。
4. Engine Runtime/Engine Private/LevelActor.cpp1049–1055：World OnActorRemovedFromWorld之后才UnregisterAllComponents，再MarkAsGarbage。ASC.cpp236–251 OnUnregister调用DestroyActiveState；Abilities.cpp1386–1428该方法取消/清能力，不是上述Owner清空来源。
- 因此三个语义时点分别为：World NativeDestroy前置Owner仍为宿主；宿主ClearLocal内Extension解绑/拒绝Attach后Owner仍为宿主；Actor OnDestroyed原生回调结束后的World Removed时点要求缓存Owner严格为空。
- 本步校正测试对最后时点的错误期望，不改生产/Engine，不把解绑期Owner保留规则扩展为宿主实际Destroy后仍保留Owner。

### 唯一校正、保护与静态证据

- 租约精确三文件：既有CombatantBindingLifecycleTest.cpp及06 Subleases/Validation；唯一source替换537–538的TestEqual为严格TestNull，标签明确原生Owner销毁回调时点。CleanupBefore/After Owner==Host及其余整个source保持原文。
- 本步前source26352字节/35E97151BAD47F8239F66B9C82F9A99CA9BB4EC7360792ABC49E82E0CD2745C4；冻结source26325字节/75EEA3073A19EE5C2462F2DE546F82BD34EE1B90829B87876052E2444EADCE7E。
- 实际全文与基线加唯一替换一致；内存逆向恢复原两行后SHA256精确为35E97151BAD47F8239F66B9C82F9A99CA9BB4EC7360792ABC49E82E0CD2745C4，未写恢复文件。实际diff仅+2/-2行；UTF-8无BOM/原LF/无行尾空白。
- 五只读保护文件hash保持：TestTypes.h A329AECDA0988E6109721BB3D47D8E1571990F1A18F62D3325752027033FAE17；CombatantState.h A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF；CombatantState.cpp 6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84；PawnExtension.cpp E76FC4182469B76C30BB0FAE980B5DB2A6D4BD7676BA30C7741F6D24B8BC4E10；ASC.cpp 4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF。
- 三文件编辑方式均为apply_patch；两记录只追加，原字节前缀保留。未改类型/生产/其它断言或引入状态、执行链、依赖、兜底。
- 仅静态验证；未执行UE/构建/Git/Engine/资产/笔记/全局写入或代理操作。修改严格TestNull不代表实际null已验证。

### 唯一source实际diff

```diff
--- Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp (A15 baseline)
+++ Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp (A15 current)
@@ -534,8 +534,8 @@
 		&& Fixture->CleanupAfterAttach.bOldDestroyedSubscription && !Fixture->CleanupAfterAttach.bCandidateDestroyedSubscription);
 	bPassed &= TestTrue(TEXT("post-EndPlay snapshot is captured while host remains valid before Garbage"),
 		Fixture->Removed.bHostValid && Fixture->Removed.bHostBeingDestroyed && !Fixture->Removed.bHostHasBegunPlay);
-	bPassed &= TestEqual(TEXT("Owner is retained at the native pre-Garbage cleanup boundary"),
-		Fixture->Removed.OwnerActor, static_cast<AActor*>(Fixture->Host));
+	bPassed &= TestNull(TEXT("native Owner destruction callback clears ASC Owner before World removal"),
+		Fixture->Removed.OwnerActor);
 	bPassed &= TestNull(TEXT("replicated source Avatar is cleared before Garbage"), Fixture->Removed.ReplicatedAvatar);
 	bPassed &= TestNull(TEXT("ASC Avatar is cleared before Garbage"), Fixture->Removed.ASCAvatar);
 	bPassed &= TestNull(TEXT("old Extension cache is cleared before Garbage"), Fixture->Removed.OldCachedASC);
```

- 当前停止点：三文件全部冻结，最终hash由交回消息提供，待统筹审查及下一统一门禁。尚未重新编译/运行严格空值断言；流送/内部Initialize/普通successor/网络/Hero/SurvivesDeath完整动态与Teams清理边界保持，不自动继续。

## A16 / 06-L1-T1-V1 第33/35次真实证据同步（2026-10-01）

### 当前结果与严格历史

- 本节更新当前实施状态，不改写 A12/A15 当时“未运行”的历史记录。第32次本叶 Fail/1 Error 的原严格复现、唯一错误文本及报告哈希保留；A15只把最后 Owner 时点期望校正为严格 TestNull，CleanupBefore/After Owner==Host与整个其余测试不变。原生 ASC SetOwnerActor订阅 Owner OnDestroyed、Actor::Destroyed在 RouteEndPlay 后广播、OnOwnerActorDestroyed清 Owner 再发生 World Removed 的根因仍以 A15 原生原因段为准。
- 统筹根审查接受的测试保持冻结：Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp，26325字节，SHA256 75EEA3073A19EE5C2462F2DE546F82BD34EE1B90829B87876052E2444EADCE7E。本次没有生产/测试改动，没有降低、排除或另设宽断言。

### 第33次首次真实通过

- 统筹完整 Editor 构建 Succeeded，10 actions/33.74秒/UBA29.06秒/exit0，运行新 DLL；65叶64 Success/1 Fail，其它计数0，唯一 Fail 为 Animation DTO 夹具前置。本叶已通过，不能把该轮写成全项目65/65。
- Saved/AutomationReports/ModuleRepairGate_20261001_33/index.json：reportCreatedOn 2026.10.01-07.51.34 UTC（北京时间15:51:34），总0.8156763911247253秒；本地读回 SHA256 624287915CDBC1C3E7D7D4857FF9E50973EE15D6D8374F1439CF46365B5EA4E3。
- GGYGO.Combatants.Binding.RealDestroyRejectsCleanupReattach：Success，duration0.009637400507926941秒，entries[]，errors0/warnings0。严格 Removed.Owner为空、原CleanupBefore/After Owner保留及本叶其它断言均未报失败，真实拒绝链通过；不把单叶通过扩展为未执行场景通过。
- UE41716 exit0已退出、240源码/14保护哈希保持为统筹全局门禁证据；没有由本组长重跑 UE/构建。

### 第35次最新回归

- 统筹完整 Editor Succeeded，6 actions/34.99秒/UBA32.04秒/exit0；仅新运行时 DLL 实际链接，不声称本次新增 UHT 或 Editor DLL 重链。
- Saved/AutomationReports/ModuleRepairGate_20261001_35/index.json：reportCreatedOn 2026.10.01-09.37.52 UTC（北京时间17:37:52），65 Success、succeededWithWarnings/failed/notRun/inProcess均0，总0.7469504475593567秒；本地读回 SHA256 F2DFBCF244512B11EB669D29DFAAD2C21310103E9D9EDA74D098B5ED8A1718A6。
- 本叶继续 Success，duration0.008721999824047089秒，entries[]，errors0/warnings0。本地核对65个路径与33一致，全部叶errors/warnings0。
- 统筹门禁同时确认原始日志49 Error=Smoke13+Damage预期34+Bake预期2，2 Warning为DDC与Python枚举重名；叶errors0不能写成全日志无诊断。UE40532 exit0已退出、242源码/14保护哈希保持、未保存资产；exit0本身不充当叶通过证据。

### 本步边界与冻结

- A16唯一写入者为 Combatants 长期组长，gpt-6.1-sol / xhigh；租约只含06 Subleases/Validation两记录，采用apply_patch，仅替换顶部当前段并追加A16。两报告及测试哈希为本地只读核对，构建/UE/全局保护统计来自统筹真实门禁通知。
- 静态验收：原顶部之后至A15末尾的全部历史字节保持，A15 source冻结哈希与五只读保护文件不变；UTF-8无BOM/原LF、非diff段无行尾空白。最终两记录完整哈希在交回消息提供，交回后两文件明确冻结。
- 本叶证明的是已完成真实 BeginPlay 的 Host->Destroy() 中唯一一次旧 Extension清理回调重绑被拒、原ExpectedASC不匹配无操作、时点Owner/缓存/订阅/事件次序及资源清理。没有证明 Initialize内部回调重入、普通后继事务、同实例流送EndPlay/再BeginPlay、客户端网络、完整Hero或活跃SurvivesDeath能力动态。
- A17 / 06-Binding-Preflight只获零写入预检；Character/AbilitySystem/Teams接口均只读，B0扩展候选仍待用户决定。不得因33/35通过自动实现、扩大租约、释放Teams、写Obsidian或运行UE/构建/Git/代理。

## A17-R0 / 06-Binding-R0 实施前诊断契约（2026-10-01）

- 最新授权仅两个新增SuccessorTest cpp/Types.h与本批两记录，已先在Subleases登记完整原子预检；不批准A17生产方案或B0。新增源不存在；记录基线为Subleases31564字节/4BF262151B3FEE2A7E480358EB86784FA8BEFA986FE742EBD4B41BA3B806AC5C、Validation51917字节/D1F52BCCDEE54B458C1C246DB6007FB9B0CCB5373A6650E9A8C6AB949D6866B1，追加保持原前缀。
- 精确案例：DifferentPawnTakeover在真实A Extension Uninitialized中一次Host.AttachAvatar(C)；SamePawnRebind在同一位置一次Host.AttachAvatar(A)。共同外层动作仅Host.DetachAvatar(A)，不直接写Host/ASC/Extension内部状态，不人为广播。
- 共同真实前置：base GI/独占Game World与Manager、明确BaseGameMode、真实World BeginPlay、复用旧测试Host/Pawn真实类型；公开Attach(A)完整正常，端点同World且有效/Authority/已BeginPlay。回调内先断言旧缓存/ASC Avatar已清、Owner保留及目标合法，再执行唯一Attach；Host引用与旧订阅退出顺序只记录，不把实现时点当目标契约。回调后的完整新绑定和恰1 Initialized为目标断言门禁。前置失败只记前置失败，不视为已复现旧收尾。
- 最终按公开快照逐项要求成功新绑定保持，包括Host Avatar、ASC cached Owner/Avatar、ActorInfo allocation与Owner/Avatar/ASC、目标Extension缓存和销毁订阅；不同Pawn要求旧A缓存/订阅退出，同Pawn要求新A绑定/订阅不被清，成功接管后不得再有目标Uninitialized。次数及生命周期另行严格断言，无ExpectedError或失败吞噬。
- 两叶仅ProjectDiagnostics.Combatants.BindingSuccessor与-GGYGOCombatantBindingSuccessorDiagnostic显式开关，枚举和RunTest均检查；未知参数明确失败。普通GGYGO65叶及A15源码保持。观察一次武装，清理前停用并释放弱观察对象，随后仅清自有Fixture及独占GI/World/Context，恢复三个GI网络委托。
- 停止点为静态源码与四hash/原记录prefix/保护清单交回后全部停写；当前尚未实现、编译或运行。任何第五文件或生产接口需求先停止，不扩大租约，不UE/构建/Git/代理/Obsidian/资产。

### A17-R0 两新增文件与静态证据（四文件冻结）

- 实际新增源：Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingSuccessorTest.cpp，445行/23035字节/SHA256 56974D6ACCE519E0EC4CD08FF3C885FECA7D0850B7E1841649889AF1FB307B36；同目录GGYGOCombatantBindingSuccessorTestTypes.h，28行/894字节/SHA256 669831243F50B54AE6FF8E29C33F5933D1CF06DC8985F85CD86AE8793B24C2A1。两新源全文可直接审查；不存在原文件，实际diff为整文件新增+445/+28行，没有旧源替换。
- Types为只读时点快照，包含Host/ASC缓存/ActorInfo来源、两Extension缓存、生命周期与销毁订阅观察；没有新UCLASS、generated头、Host/Pawn、生产状态机或执行链。Actor类型直接复用冻结BindingLifecycleTestTypes.h及其已有实现；私有GI/World仅承担两个独立案例的自有测试资源生命周期。
- cpp通过真实base GI/Context/Manager、URL精确BaseGameMode、InitializeActorsForPlay与World::BeginPlay建立前置，并断言全部端点/组件Authority/存活/同World/完成BeginPlay、ASC Owner及ActorInfo来源、两Pawn无第二ASC、死亡标签未置位。随后公开Attach(A)须完整成功才开始观察。
- 两案例均只执行一次外层Host.DetachAvatar(A)，在A真实Uninitialized中消费一次武装再公开Attach(C)或Attach(A)。回调Before/After与Detach.Returned记录实际公开字段及计数；回调后完整Host/ASC/ActorInfo/目标Extension/订阅和initialized恰1为门禁。失败前置明确false且日志注明最终目标未评价，不把夹具失败当目标红证据。
- 最终严格断言逐项检查新Host/ASC cached Avatar、Owner、ActorInfo Owner/Avatar/ASC与allocation、目标缓存及订阅保持；同Pawn要求A的新绑定保留，异Pawn要求A退出/C保留。成功接管后目标Uninitialized严格0，尝试1、原A Uninitialized1、目标Initialized1及四事件顺序均独立断言，不ExpectedError或允许旧值/null的宽目标断言。
- 通知开始时Host引用与旧订阅的退出先后仅记录，不把当前实现位置写成成功契约；这与用户批准的提交后允许普通后继一致。严格保留的是回调成功证据及外层返回后新绑定仍完整，而不是限定内部清理顺序。
- 隔离：根ProjectDiagnostics.Combatants.BindingSuccessor，两个叶DifferentPawnTakeover/SamePawnRebind，-GGYGOCombatantBindingSuccessorDiagnostic是唯一显式开关；GetTests只在开关存在时追加两个精确名称/参数，RunTest再次检查开关和已知精确参数，未知参数失败后不创建Fixture。未向GGYGO普通根注册；未实跑枚举，不能把静态隔离称为65叶动态验证。
- 清理：Fixture唯一持有弱委托目标Probe，StopObserving先关闭观察/武装并Reset目标，再仅Destroy自有A/C/Host，World EndPlay时真实GI/Manager存活；随后GI Shutdown、World/Context释放、清临时包dirty并恢复三网络全局委托。Probe不持Fixture所有权、没有共享环或World handler；生产公开注册无Remove，释放弱目标摘除可调用观察，遗留弱槽由自有Extension销毁。原注册补发早于武装且不算接管。
- 静态全文：实际两源逐字与预期文本相同；UTF-8无BOM/原LF/无行尾空白。Complex注册1、显式开关检查2、武装接管调用点1、外层Detach调用点1；人工核对回调前置/最终断言/早退/析构顺序及C++直接声明使用。没有运行编译器或UE；这些不保证编译、真实前置、枚举、清理或目标结果。
- 两记录只追加R0预检及实际结果，原Subleases31564字节/Validation51917字节前缀需精确保持4BF262151B3FEE2A7E480358EB86784FA8BEFA986FE742EBD4B41BA3B806AC5C与D1F52BCCDEE54B458C1C246DB6007FB9B0CCB5373A6650E9A8C6AB949D6866B1；最终四hash与读回保护结果在交回消息提供。

### A17-R0 本步只读保护清单

以下为本组长本步捕获的14个文件，不冒充统筹全局保护集合；最终逐一读回相同后交回。

| 精确相对路径（根F:/ue_project/GGYGO） | 基线SHA256 |
| --- | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | E9AEB8AE04165D05DA8C6C18EB07B18F5C7DCB6D8A4AE0702B1D117845BC95E5 |
| Source/GGYGO/Character/Components/GGYGOHealthComponent.cpp | D2B319919DABFF115C4A91D95477DD87FE1CFAE453A57F8B38A3CB6FACE106BB |
| Source/GGYGO/Character/Components/GGYGOHealthComponent.h | 4D6CAD72C4162D6484FD9ACD5BE30F539517049D6CF673D303D23B349B365D02 |
| Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp | E76FC4182469B76C30BB0FAE980B5DB2A6D4BD7676BA30C7741F6D24B8BC4E10 |
| Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h | 6190EB9134ECDE4735FC67C0CD564D87C3EEDAE9BC477E16ACA296368F7C96FD |
| Source/GGYGO/Combatants/GGYGOCombatantState.cpp | 6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84 |
| Source/GGYGO/Combatants/GGYGOCombatantState.h | A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF |
| Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp | 75EEA3073A19EE5C2462F2DE546F82BD34EE1B90829B87876052E2444EADCE7E |
| Source/GGYGO/Combatants/Tests/GGYGOCombatantBindingLifecycleTestTypes.h | A329AECDA0988E6109721BB3D47D8E1571990F1A18F62D3325752027033FAE17 |
| Source/GGYGO/Combatants/Tests/GGYGOCombatantConfigReplicationTest.cpp | F112D16EA2C9C8C5BC0C04794CD96EB52DCEB5DAD9CC01327B83A4721A217082 |
| Source/GGYGO/Combatants/Tests/GGYGOCombatantConfigReplicationTestTypes.h | 01E0305B77D45A8CDD241D3ECCA6DDABCD353B51558937CAB0EA629F63F5C64C |
| Source/GGYGO/Combatants/Tests/GGYGOCombatantDeathProjectionTest.cpp | 2457C05CB40D4DF42FD9BCAD91744B7D7BC6610FD1630F5E838971B5A30FA7B8 |
| Source/GGYGO/Combatants/Tests/GGYGOCombatantDeathProjectionTestTypes.h | 8961EBCAFCC4400048836314C646C6321C3D66618265FD709BA36199F0E9CE56 |

### 当前用户决定、剩余边界与停止点

- 统筹最新转达用户已批准：native不可中断绑定写入阶段Busy、不自动排队；绑定提交后带身份就绪通知允许后继。项目GA取消/结束统一捕获原播放归属、薄扩展点迁移由战斗组长只读细化。此前预检中的“未决定”是当时历史，以上更新当前选择，不授予本组长生产/API/Guard/K3写权；B0final仍独立未批准。
- 静态推导的两风险仍在当前生产：DifferentPawn回调接管C后，外层Detach无条件清Avatar并Synchronize清C；SamePawn重新绑定A后，ClearLocal凭同Pawn匹配清ASC/订阅和Host。此为代码路径推导，未运行前不写成真实观察或两诊断已红。
- R0只验证普通公开Uninitialized成功接管后旧收尾不破坏新绑定，不混native Busy、Initialize/Cancel/Cue内部、自然Montage混出、流送/网络或Teams回收；不削弱/改写A15及旧测试。Busy不能用于拒绝R0的正常通知接管来规避严格目标。
- 新测试、预检和静态证据编辑全部apply_patch。无UE/构建/UHT/Git/代理、生产/API/蓝图/资产/Obsidian/global写入；涉及新增诊断实施状态的局部笔记等待独占租约，当前不宣称架构笔记同步完成。
- 四文件明确冻结交回：未编译、未真实枚举/运行，需统筹在写入者冻结后另安排完整构建及-GGYGOCombatantBindingSuccessorDiagnostic独立诊断。任何编译/前置失败仍须分清，不把正常65门禁或exit0代替本两叶结果；不自动继续生产或释放Teams。

## A17-R0-V1 / 06-Binding-R0-V1 第36次实际结果同步预检（2026-10-01）

- 唯一目标/范围：仅本批Subleases/Validation两记录顶部当前段与追加36真实证据，原A16/R0/早期失败及静态历史原文保留；已先在Subleases登记精确原子预检。
- 入口两基线已匹配：Subleases39050字节/A4B7090F3F2B41DDFF291A24A4944698E9C5036622804FF42021B5AC545834EA，Validation61721字节/5BF7261A85C858CB61E4906036CD4A99032F38DABCBF82AA48F8A8000F345BB2。实际两报告hash、两Case错误行与AfterTakeover/Detach.Returned/计数已只读读回。
- 验收为全文仅一行当前段替换加尾部追加，逆向恢复完整入口文本/hash；DifferentPawn8错误与SamePawn4错误必须保持真实差别，前置成功不能遗漏，正常70/exit0不冒充诊断通过；三个冻结测试源hash保持。
- 当前授权只有两记录；K4-I1/P1-T1在途写入由统筹另排程，36的248源/14保护是历史证据，不作当前全树保持声明。不得修改测试断言、生产/API/第三文件/Obsidian/资产/global或运行UE/构建/Git/代理；两记录交回即冻结。

### 第36次完整构建及两个独立报告

- 构建字段来自统筹36实际门禁记录：完整Editor Succeeded，7 actions/94.44秒/UBA80.76秒/exit0，UHT7.822312秒但0 generated files写入，实际链接新运行时DLL；不声称Editor DLL重新链接。R0两新源已进入本次构建及实际新DLL诊断，原静态段“未构建/未运行”保留为当时历史。
- 严格R0报告已本地读回：Saved/AutomationReports/ModuleRepairCombatantBindingSuccessor_20261001_36/index.json，reportCreatedOn 2026.10.01-12.24.43 UTC（北京时间20:24:43），SHA256 CE53E5DB523A0E10ABDB422D69BB640AE4CA0D89C5C3BD7DB6030ABD3D3223E0；succeeded/succeededWithWarnings/notRun/inProcess均0、failed2，两叶合计12 errors/0 warnings，总0.1332578957080841秒。
- 正常报告另行本地读回：Saved/AutomationReports/ModuleRepairGate_20261001_36/index.json，reportCreatedOn 2026.10.01-12.23.19 UTC（北京时间20:23:19），SHA256 9C28CF4DB61E8909EF2908CD24479810738FC29E845921B4E249DCE3A3508E46；70 Success、其它计数0、总0.8348187208175659秒、全部叶0 errors/warnings。旧65路径保持且新增A5五叶由统筹核对；R0是独立ProjectDiagnostics根，不混入正常70。
- A15 GGYGO.Combatants.Binding.RealDestroyRejectsCleanupReattach同轮继续Success/0.009493499994277954秒/0 errors/warnings。它与普通通知后继是不同契约；A15通过及正常70不关闭R0严格失败。

### R0回调成功与最终破坏：真实证据

两叶完整路径分别为ProjectDiagnostics.Combatants.BindingSuccessor.DifferentPawnTakeover与ProjectDiagnostics.Combatants.BindingSuccessor.SamePawnRebind。所有12条Error都在旧收尾后的目标保持断言；真实GI/World/Actor BeginPlay、初始正常Attach(A)、回调前置、回调内唯一Attach、完整Host/ASC/ActorInfo/Extension接管及Initialized恰1没有断言失败。源码门禁成立后才执行最终目标，不能把本两Fail归类为前置失败。

| 案例 | 回调内AfterTakeover实际快照 | 外层Detach.Returned实际快照 | 结果 |
| --- | --- | --- | --- |
| DifferentPawnTakeover | Live1；Host/Cached ASC/ActorInfo Avatar均为C，CCache为宿主ASC，CSubscription1；ACache空、ASubscription0 | Live1；上述三个Avatar均空，CCache空、CSubscription0；Cached/ActorInfo Owner仍Host、InfoASC仍原ASC | Fail；8 errors/0 warnings；0.12345349788665771秒 |
| SamePawnRebind | Live1；Host/Cached ASC/ActorInfo Avatar均为A，ACache为宿主ASC，ASubscription1 | Live1；三个Avatar均空、ASubscription0，但ACache仍为宿主ASC；C仍未绑定；Owner/InfoASC保留 | Fail；4 errors/0 warnings；0.009804397821426392秒 |

| 实际观察计数 | DifferentPawn | SamePawn |
| --- | --- | --- |
| A Uninitialized | 1 | 1 |
| C Uninitialized | 1 | 0 |
| A Initialized | 0 | 1 |
| C Initialized | 1 | 0 |
| Takeover Attempts | 1 | 1 |
| Target Uninitialized After Success | 1 | 0 |

- DifferentPawn八条严格错误（冻结cpp行号）：204 Host Avatar、206 cached ASC Avatar、209 ActorInfo Avatar、211目标Extension缓存、213目标销毁订阅，以及387成功后目标解绑1应0、388 C解绑1应0、401事件5应4。其前四事件仍为原通知/尝试/C Initialized/接管成功，额外通知发生在成功之后。
- SamePawn四条严格错误：204 Host Avatar、206 cached ASC Avatar、209 ActorInfo Avatar、213目标销毁订阅。Extension缓存与原ASC仍相等，没有多发解绑；“缓存还在”不是成功，因为其Host/ASC/ActorInfo Avatar及订阅已经失配。
- Owner、ActorInfo来源/allocation及存活断言未失败；这里只清Avatar字段/相关缓存订阅，不把结果描述为整个ASC或整个ActorInfo对象消失。报告有实际字段与计数快照，当前已从原代码静态推导推进到真实严格复现，但生产仍未修。
- 两案例保持原严格断言，无ExpectedError/吞失败/排除场景；未来修复须让合法提交后通知中的后继成功保留，不能用native Busy拒绝本普通通知来通过。

### 原日志、历史保护及当前权限

- 统筹36原日志分类：R0诊断27 Error=启动Smoke13+12目标断言+2失败汇总，2 Warning为DDC/Python枚举重名；正常日志49 Error=启动Smoke13+Damage预期34+Bake预期2，2 Warning同类。叶0 warnings/正常叶0 errors不能写成全日志无诊断。
- 两UE exit0且均已退出、248源码/14保护在36构建及两次UE运行保持、未保存资产，均按统筹36窗口历史引用；进程exit0不等于独立诊断通过。当前K4-I1/P1-T1另有在途写入，不能把历史hash保持写成当前全树静止，也不由本步核对或撤销其变化。
- 用户已选native不可中断绑定阶段Busy且不自动排队、提交后带身份通知允许后继；K4-I1只身份签发/核对/撤销底层，不自动证明Host/Extension/通知调用链已修。本会话无生产或Teams写权；Initialize/Cancel/Cue内部、K3播放归属、流送/再BeginPlay及网络仍待后续步骤。
- R0 cpp冻结SHA256 56974D6ACCE519E0EC4CD08FF3C885FECA7D0850B7E1841649889AF1FB307B36、Types 669831243F50B54AE6FF8E29C33F5933D1CF06DC8985F85CD86AE8793B24C2A1，A15 cpp 75EEA3073A19EE5C2462F2DE546F82BD34EE1B90829B87876052E2444EADCE7E；本步开始和交回仅只读核对这三文件，不写source/test/types。

### R0-V1实际差异、逆向验收与停止点

- 两记录唯一编辑为各自顶部第三行当前段替换、尾部追加本预检/36真实证据；原A16/R0/32失败/静态段全部原文保持。不删除旧“未运行”历史，也不保留其为最新状态。
- 静态验收方式：从实际新文件删除本步精确追加、将新当前段逆向恢复旧段；完整文本逐字与入口相同，内存SHA256须恢复Subleases A4B7090F3F2B41DDFF291A24A4944698E9C5036622804FF42021B5AC545834EA与Validation 5BF7261A85C858CB61E4906036CD4A99032F38DABCBF82AA48F8A8000F345BB2，不落盘恢复文件。UTF-8无BOM/LF、非历史diff段无行尾空白；最终两文件hash由交回消息提供。
- 编辑仅apply_patch，实际报告只读；未运行UE/构建/UHT/Git/代理，未写第三文件、源码/测试/生产/API/Guard/Teams/Obsidian/global/资产。两记录明确冻结交回后停止，不自动下一步骤或宣称架构笔记同步完成。

## Combatants-HostProductionRouting：四文件生产交回（2026-10-03）

### 范围与实际差异

- 统筹四文件租约入口记录 `Saved/ValidationRecords/CombatantsHostProductionRouting_LeaseBefore.json` 已匹配：Host h 4370/A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF；cpp 8950/6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84；Subleases44757/8CEF60DC2627D0285488023AC55C54FCF3C5CF52C1C83D9A0305B541A153F772；本记录69165/F5DBC32E7768C277696742BEE894CE41323DE5A65CA4AB28FCEC0B0B0B6DD642。先在Subleases登记预检，再改生产，再补本次实际结果；由Combatants长期组长直接完成，gpt-6.1-sol / ultra，未使用代理。
- Host h实现冻结native接口；cpp统一Initialize/Release/Refresh及旧Attach/Detach/Sync、销毁、EndPlay。Host只借用H/Context/弱Extension并拥有Avatar选择/复制/原销毁订阅，ASC唯一执行ActorInfo/Binding/Cancel/Cue/Publish，Extension唯一拥有本地资源。端点使用组件GetOwner()==this，ActorInfo Owner只作一致性校验，不作旧Host定位。
- Initialize要求空H及精确Context；正常Ready/Released允许同步后继。Request入口只在ASC真实原生写入未返回时Busy，不排队。原生提交、安装、通知、发布依实际顺序写Step；Notify桥认证本次Receipt与实际Dispatching，纯查询使用Installed且不形成Ready循环。Refresh不替代初次Ready。跨Host保持旧释放→核对→新绑定，失败保持原失败且不恢复旧Host。
- Release在Extension关闭新Install/Ready后仍可处理原H，不要求Ready或新绑定准入。Withdraw→原Context Cancel/Input/Cue/Clear→退原Host资源/订阅→真实发布Released；旧H/完整Context/当前opaque槽逐步重检，后继即停止。失败可消费仍属原H的本地义务，但不转换为原生成功；Closed Released保留真实Failed/LifecycleClosed及本地改变，不能称观察者已通知。未公布到Host的原H安装失败分支也消费Released义务。
- 两记录只更新顶部当前状态并追加本次登记/结果，原A16/R0/32失败/36真实历史正文保留。本步不做全文逆向验收、不新增严格矩阵或夹具；以用户最新验证范围为准。

### 有限静态证据与保护

- Host h：135行/5936字节/SHA256 `86F7C6CEA874DB25AD5073EFEF5367DCC4464CB630E1997D883D20D1C4280903`；cpp：1059行/41350字节/SHA256 `10E4FE163FC93616EBBD47D823549AF288F608F8562AC795689644FE9BC54800`。有限调用链读回，忽略注释/字符串的括号计数平衡，UTF-8无BOM/无行尾空白；不称为C++或UHT语义检查。
- 静态检索：Host没有直接调用旧InitAbilityActorInfo/ClearActorInfo/RefreshAbilityActorInfo、旧Extension InitializeAbilitySystem/UninitializeAbilitySystem、RemoveAll或直接广播ASC Notice。发布桥用栈局部FDelegateHandle并作用域精确Remove；步骤分别填ASCResult/LocalResult/InputClear，Input只记录已实际清理的原Context/H；Cleanup记录真实步骤，不生成成功占位。
- 七共享源入口/出口hash全匹配：ASC h `7A1FEDD04CBBA92C7B931238B0EDF4B1073AE3447FAF34F2C5BC0A02BD22EEA6`；ASC cpp `57CD3A4AE6282BDFE3246C9076AE3C0BFEC36031517F1D99F9D4C88E55D6EECA`；BindingTypes `31C616359B895B11EF4E72430DD34C138AD06DD1CA933563991DD3AADA649143`；Extension h `B500B53BD45B810B6CEF320F75334F06AD8E94C14BE23207CAE4FDF177994563`；Extension cpp `46C3CDBC464B379F37EFBFD62AFECD77736F3FB05C0B9A5ED2368E34E41EF267`；native Host Interface h `B658148B2E17CECD2A598FFBE4BE0B7964655833F4283822955ABBED24336316`；cpp `EB22E540948719D8D7EB4432EDD3C2F2CE78052B6D62E2ADCF2E45B56A86E143`。
- 三旧测试仍匹配：R0 cpp `56974D6ACCE519E0EC4CD08FF3C885FECA7D0850B7E1841649889AF1FB307B36`；R0 Types `669831243F50B54AE6FF8E29C33F5933D1CF06DC8985F85CD86AE8793B24C2A1`；BindingLifecycle/A15 cpp `75EEA3073A19EE5C2462F2DE546F82BD34EE1B90829B87876052E2444EADCE7E`。未改变断言、降低前置、抑制日志或新增ExpectedError。

### 精确停点、未验证范围与冻结

- 共享ASC静态边界一：cpp `ValidateAvatarBindingActualSnapshot` 在1421～1424拒绝Owner正在Destroy、1447～1450拒绝Avatar正在Destroy；C1a复用CheckContext，PreserveOwner预留另在1713～1717拒绝关闭Owner。因此真实Host/Pawn Destroy的原Release可先撤本地H，随后原生Cancel/Clear被拒；Host无公共接口保证完成原生销毁清理。本版不切换Clear模式、不走旧Clear兜底，不能沿用旧A15通过声称该链仍通过。
- 共享ASC静态边界二：native Execute中Super Init在2494，后2517复核失败可无2522提交/无Receipt。已颁Operation不能证明Host有清除部分原生状态的权限；本版保留真实Init失败及明确诊断，不能声称所有失败最终原生无绑定。需要统筹/ASC所有者决定精确失败清理契约后另租约实施；本任务到此停止，无第五文件。
- 原R0第36次2 Fail/12 errors依然是最近真实结果；本次未重跑，不标复现关闭。旧A15/正常70/Gate53分别是历史证据。按用户最新选择，后续只安排统一编译＋必要UE冒烟；没有新严格矩阵、新夹具或专项通过声明。Character完成生产调用方/Getter迁移并冻结后，由统筹排同一DLL及新World；接口定义、Host生产、Character接线、编译、运行验收分开记录。
- Obsidian已只读核对计划蓝图和Combatants结构，仍有旧Detach描述和“Host未实施”。需统筹后续独占同步结构/Canvas、角色初始化流程、Character四阶段与实施状态，并保留本次未编译及两项共享停点；本租约没有Obsidian/全局写入权，不称笔记同步完成。
- 四文件明确交回冻结；最终两记录hash由交回消息提供，不在文件中自嵌循环hash。未运行Build/UHT/UE/Git，未写共享源码/旧测试/资产/Saved/Obsidian/全局入口，未新建或唤醒代理。GameFeature另租约在途不属于本次冻结；Teams不释放，不自动续写。

## HostCommittedCleanup-H1：已提交Destroy/Closing消费者（2026-10-03）

### 授权与实际范围

- 统筹接受预检turn `01a1023b-b88e-7451-bd9d-b2d4e27628c4`，只授cpp、06 Subleases、本文三文件；模型 `gpt-6.1-sol / xhigh`，组长直接完成，无代理。入口 `HostCommittedCleanup_20261003_LeaseBefore.json` 三写文件及Host h/ASC h/cpp三只读项bytes/hash全部匹配。Subleases先登记，cpp实施后有限核对，再更新本记录；两记录仅第三行当前段和尾部本原子登记/结果变化，历史失败正文保留。
- 改动方法仅 `InitializeAvatarBinding` 的已提交 `CleanupOwnCommit` 和 `ReleaseAvatarBinding`：本次提交/原入口Context不变，两处改用 `CheckAvatarBindingCleanupContext`；两处明确选择ClearMode，并在纯原资源query追加默认ASC/组件Owner端点身份核对。未改Host h/Types/shared接口，未改未commit Init或owner-only失败分支。
- 模式在清理发出前选择，Host本生命周期关闭或原Owner/ASC宿主Destroy时请求 `ClearActorInfo`，存活持久Host普通解绑请求 `PreserveOwner`；不将ASC拒绝作为换模式重试触发。ASC仍唯一认证cleanup来源并执行原生写入，Host不持ActorInfo快照或原生写入Proof；GetOwnerActor仅在ASC已确认来源后供模式选择，GetOwner固定核对默认组件宿主。
- pure cleanup query固定原H/完整Context/Host/ASC/Pawn/Extension及opaque槽、原选择，不要求Ready/Installed/工作生命周期开放。仍有效且已分配的原Actor处于Destroy/EndPlay可继续原资源收尾；无效ASC和对象销毁/GC不获原生权限。Release在ASC失效时仍保留精确本地H收尾路径，未用其成功掩盖原生失败。Revoked清理Succeeded只授权原资源Cancel/Cue/Clear，不升级Init/Refresh/Ready。

### 有限静态检查

- cpp最终1075行/42636字节/SHA256 `8514BDF22B5C66A2A2FBE481B3B8F164F5BEB64B0F4BF34E214C1ECFEDDD0187`。范围diff仅两个方法；方法名称集合相同、文件前部及其它方法保持原文。Init未commit失败前段和安装/Ready后段与入口一致；H2 cleanup调用计数0，两处CheckAvatarBindingCleanupContext及两处显式模式有限读回。无行尾空白、忽略字符串/注释后括号计数平衡，不称编译或语义证明。
- 本次只读保护核对：Host h `86F7C6CEA874DB25AD5073EFEF5367DCC4464CB630E1997D883D20D1C4280903`；ASC h `40535C42E7CE32E08EBC64F2F1A06317BDC2E61FB1FEE4B71CA243CFAC5D6053`；ASC cpp `CAD19824EBCB3527E3A43051ADBECD7DA31D8DD33D6B941C014C219A7101199F`。均为核对当时事实，不将未来独立输入租约整文件hash变化作为Host收束停点。
- 原资源重检、Busy完整返回、Cancel→无回调Input→Cue→Clear→真实Released发布、历史载荷、精确退订及Closed实际结果保持原机制；普通同步后继仍能接管，旧H/Context/槽不符即停止。没有新增依赖、循环、权威状态、调度器或清理执行器。对Destroy/Closing原清理可达、普通Owner保留、ABA/不同Pawn/Refresh后继隔离只完成静态审查，未做动态断言执行。
- 当前Obsidian只读核对发现Host生产路由已同步，Destroy公开权限停点尚待按ASC新接口/H1修正；源链冻结后需统筹独占同步清理资格、Closing模式、H2消费者和未编译状态，本步不写Obsidian/Canvas。

### 剩余与冻结

- H1生产消费者已落盘，不等于真实Destroy链验收；ASC两个接口仍只有有限静态接受。H2原未commit Init失败消费尚未实施，其原失败诊断保持，须本三文件冻结后另租约授权，不自动接着写。
- 没有运行Build/UHT/UE/Git/自动化，未新增测试/矩阵/夹具。第36次R0 2 Fail/12 errors依然为历史最近真实结果，旧A15/正常回归不能证明本版；Character/其它消费者、Teams、资产/网络和统一编译＋必要UE冒烟分别留账。
- 三文件明确冻结交回，最终三hash由交回消息提供；未写第四文件、共享源/头/Types、测试、Saved、Obsidian/全局、资产，未创建或唤醒代理。其它合法工作线不属于本冻结，不宣称全树静止。

## HostFailedInitCleanup-H2：原未提交失败Init消费者（2026-10-03）

### 授权、产出与失败边界

- H1 turn `01a1024d-9039-77a2-a05e-91af572799c9`已completed/冻结，统筹根接受为finite_static_accepted_uncompiled。H2只授原cpp/Subleases/本记录三文件，组长直接 `gpt-6.1-sol / xhigh` 完成，无代理；Subleases先登记。入口 `HostFailedInitCleanup_20261003_LeaseBefore.json` 三写/三只读bytes/hash实际全匹配，未恢复H1或共享源写权。
- 改动仅 `InitializeAvatarBinding` 和 `InitializeOwnerActorInfo` 的原Try未commit失败返回分支。原Try完整返回、`!Initialized.bCommitted`且原Operation有身份后，调用ASC `TryCleanupFailedAvatarActorInfoInit`一次；没有原Operation不调用，不用当前Getter造来源，不假定有Operation就有Proof。原ASC失效则明确未调用诊断，不伪造Result/Step；缺Proof或后继退休返回真实拒绝，禁止清当前/回滚/重试。
- Avatar失败先保留原ASC Init Step及顶层失败，实际Cleanup仅追加ActorInfoClear/ASCResult；顶层Outcome/Reason不依CleanupSucceeded改写。owner-only建立栈局部真实失败步骤历史，原失败日志与CleanupOutcome/Reason/Operation/bCommitted及原失败分别输出，始终return false；该历史只属于当前调用栈，不产生另一事实来源。
- 两个独立pure query不使用原工作的IsAvatarBindingPermitted/Ready/Installed，也不读取当前Context或ActorInfo。Avatar固定原Host/ASC/Pawn/Extension端点、默认组件Owner、原选择及入口空Host H和空目标槽；owner-only无Avatar安装记录，只固定原Host/ASC/选择/空H。有效且已分配原对象Closing不因此阻断清理，失效对象/ASC仍不获权限；ASC唯一验证原operation/actual/allocation Proof、退休后继来源并执行完整Busy原生Clear。
- 没有清理后Commit/Receipt/Notice/Ready。原Init错误和Cleanup拒绝均可定位，不以物理清理成功隐藏业务失败。正常Bootstrap/Replace准入、成功Install/Ready/Publish、H1已提交清理和Release保持原实现。

### 有限静态证据

- cpp 1143行/46732字节/SHA256 `9EF5B5E74AD25EF7E70DA05E0A99CAF7F12CB80D9A8C61C2B091924DE05AB959`。方法范围对比仅上述两方法；从InstalledResource起的完整已提交CleanupOwnCommit/Install/Ready后段及完整Release逐字保持，其他方法/方法名称集合保持。清理API调用恰2，两个query均无Context/ActorInfo证明读取、无新工作/Ready/Installed前置；实际失败段完整读回，无行尾空白/UTF-8无BOM，忽略字符串/注释括号计数平衡。以上仅静态，不称C++/UHT或运行通过。
- 本次保护：Host h `86F7C6CEA874DB25AD5073EFEF5367DCC4464CB630E1997D883D20D1C4280903`；ASC h `40535C42E7CE32E08EBC64F2F1A06317BDC2E61FB1FEE4B71CA243CFAC5D6053`；ASC cpp `CAD19824EBCB3527E3A43051ADBECD7DA31D8DD33D6B941C014C219A7101199F`。实际hash与入口匹配，仅记录此时事实，不把未来独立输入租约hash变化当作本Host阻塞点。
- 两记录范围只当前第三行和尾部登记/实际结果；H1、历史R0/A15/旧接口缺口正文保留。不新增依赖、Proof缓存/计数/权威状态/执行链/调度器，不修改共享接口、头、Types、Extension或测试断言。
- Obsidian只读核对仍有旧Destroy及失败Init公开权限停点。源链冻结后应由独占文档步骤同步ASC新接口与H1/H2源码消费者状态、原失败保持及未编译/冒烟；本租约不写图文、不称已同步。

### 未验项与冻结

- 三文件明确冻结交回，最终三hash由消息提供。H1/H2消费者源码完成及有限静态结果不能代表Destroy、未commit部分写入/后继隔离动态验收完成；未Build/UHT/UE/Git/自动化，无新测试/矩阵/夹具。
- 原第36次R0 2 Fail/12 errors是最近真实历史结果，未复测通过，旧A15/普通回归/局部专项不能替代本版证据。消费者整链统一编译＋必要UE冒烟、Teams、图文、资产/网络与最终验收由统筹分别排程。
- 未写第四文件、H1重写、共享源/头/Types、旧测试、Saved、Obsidian/global或资产，未创建/唤醒代理。冻结后不自行继续源码或图文，不宣称全树静止。

## HostLifecycle-H3：实施前验证登记（2026-10-04）

- 统筹接受预检turn `01a1029b-a704-70f2-bc05-f5170a6baf8c`，只授Host h/cpp、06 Subleases和本文四文件。组长直接实施，`gpt-6.1-sol / xhigh`，无代理。入口 `CombatantsHostLifecycleH3_20261004_LeaseBefore.json` 四写入项bytes/hash实际全匹配；两记录先登记，随后才可写生命周期源码。ASC、Extension及原生Host接口只读，H1/H2方法原文冻结。
- 严格原问题保留：统筹核对原生Destroyed总入口先RouteEndPlay后蓝图/OnDestroyed，而pre-BeginPlay可能没有EndPlay；Host PostInitializeComponents已建立ActorInfo；无H EndPlay原先只Invalidate，没有物理Clear。本组使用统筹证据，未独立读取引擎/执行UE，不把静态新入口称为动态复现通过。
- 拟验契约：Destroyed/EndPlay在Super前调用唯一Close；既有准入先关闭，重复入口在快照前停止，不能重捕后继。有H复用原Release并只收录自己的真实Clear Commit；owner-only原Context cleanup认证＋原端点/selection/空H纯query，显式ClearActorInfo真实事务和真实Receipt/ASC Notice，无Extension假通知。Invalidate只退休入口原Context或自己的Commit，不等同Clear成功。
- 有限核对范围：生命周期方法/头声明及注释diff、其它方法逐字保护、快照/回调重入/Busy和失败实际结果、无重试/新Proof/缓存/计数/清理执行器、记录历史前缀保持、读回/格式及四hash。共享hash仅当时事实；不用未来独立输入变化制造本Host停点。无新测试/严格矩阵/夹具，统一编译＋必要UE冒烟由统筹。
- 停点与非目标：第五文件、新共享接口或业务选择即交回，不扩大租约；无Build/UE/Git/资产/引擎/Teams/Hero/GA/测试/Saved/图文/global写权。Gate55 UHT生成33文件但编译失败，Gate56仍因Hero三个旧调用失败，未链接DLL/未运行UE；R0历史2 Fail/12 errors未重跑。四文件冻结后图文由统筹接力，不宣称全树静止或Teams放行。

### H3源码产出与实际清理历史

- 新增Host protected Destroyed override和private Close声明；两个生命周期入口都在Super前Close。Close使用既有准入标记作单次派发/工作拒绝：重复于快照前void返回；首次先关闭，再固定原Host/默认ASC/完整Context/H/selection。标记不是清理成功状态，真实BeginPlay重开保持。H路径的原Context取原Release请求，只允许同Binding入口证据，不把入口已存在的无关后继认作原H。
- 有H仅复用原Request.Release和H1/H2，实际历史保留；从其ActorInfoClear真实bCommitted获取本次Commit。owner-only无H先认证原 `CheckAvatarBindingCleanupContext`，纯query只认原Host/ASC组件Owner/原选择/空H及本次已关闭准入，允许有效已分配Closing；无工作/Ready/Installed或当前Context/ActorInfo证明读取。ASC仍唯一掌认证及完整Busy原生窗口。
- 无H明确一次ClearActorInfo，真实ASC返回记录ActorInfoClear；仅本次bCommitted替换退休Context。Succeeded且commit后用原真实Receipt执行ASC Publish、记录真实PublishNotice；无Extension安装/假通知/本地桥。未调用时不制造Step，Checked实际Outcome/Reason、原生Busy/失败及发布失败保持；不回落另一模式、重试或排队。Receipt及操作历史均为当前栈证据，不是新状态。
- Invalidate只消费原入口Context或自己真实Clear Commit，与物理清理Outcome独立。日志分别给原范围/实际历史及metadata retirement Accepted/Reason；后继Context不符即真实拒绝，不读取当前Getter补来源。不把提交后发布Stale或退休拒绝抹掉，也不把Busy/无原已提交Context/ASC失效写成清理完成；第二生命周期入口不补清。

### H3有限静态检查

- h138行/6156字节/SHA256 `6C80F72921443B2CE1EC6BCA1C3FB8FEA423FF390E7504B9D3828FFE532AFC1A`；cpp1255行/51286字节/SHA256 `E36A2495F0AD208D164B5C9BED1D873941CDC1900A984DCCD0E1D42C7EA06E3A`。cpp方法diff：仅EndPlay改变，Destroyed/Close新增，无删除；生命周期前部及GetLifetimeReplicatedProps起整段与入口逐字一致，故BeginPlay、全部H1/H2/Release/请求/发布/选择方法保持。头逐字推导确认只有Destroyed声明、Close声明/注释及既有标记注释变化。
- 两入口Close均先于Super；重复return及置false均在捕获前。新Close内无首次外调后的Context getter；纯query未读Context/ActorInfo或工作/Ready/Installed，实际Clear事务调用1、原Receipt真实Publish1、Local通知/PublishAvatarResources/AppendLocalStep为0。清理与发布结果只在实际调用后追加，FindClearCommit只读取本次真实步骤；格式和方法完整读回。源码UTF-8无BOM/无行尾空白，忽略注释/字符串后h括号7/7、43/43，cpp180/180、781/781；这些只证明有限文本核对，不证明C++/UHT或运行通过。
- 六项只读共享hash与本次入口一致：ASC h `40535C42E7CE32E08EBC64F2F1A06317BDC2E61FB1FEE4B71CA243CFAC5D6053`、cpp `CAD19824EBCB3527E3A43051ADBECD7DA31D8DD33D6B941C014C219A7101199F`；Extension h48AC44EF…/cpp69CFB9F4…；Host接口h84B989A6…/cppEB22E540…。没有改共享契约/其它模块/引擎或新增状态所有者；hash仅当时事实，后续独立ASC输入租约不属于本次写入。
- 两记录旧正文前缀完整保持，只更新第三行当前状态并尾部追加H3预检/结果；Validation原有10处行尾空白未动，新增部分无行尾空白。一次只读hash命令管道语法错误后已正确重读，无文件副作用。没有新依赖/循环/Proof缓存/计数/清理成功Authority/另一执行器或调度器。

### H3剩余、图文与冻结

- H3仅源码产出与有限静态核对，没有独立引擎源码读取、Build/UHT/UE/Git/自动化、新矩阵/夹具或原问题动态复现。Gate55/56是已核对真实构建历史：Gate55 UHT生成33文件但失败；Gate56仍因Hero三个旧输入调用失败，runtime未链接/UE未运行；不能用部分聚合单元通过证明本H3。R0原2 Fail/12 errors未重跑，不以旧A15/普通回归覆盖。
- ObsidianCombatants结构/Canvas只读核对：已正确记录H1/H2与Gate55/56，但尚无H3 Destroyed/pre-BeginPlay、唯一Super前Close及owner-only真实Clear/Receipt。须统筹源链接受后的独占图文接力补实际源码状态和Busy/失败边界；本四文件租约未授权图文，不冒称同步完成。
- 四文件明确冻结交回，最终四hash由消息提供。实际pre-BeginPlay/正常EndPlay/Destroyed原资源与owner-only、原Busy/后继隔离由统筹统一编译＋必要UE冒烟核对，无本组额外矩阵。Teams、图文、资产/网络及整链验收分别开放，不因H3源码交回放行Teams；不自动续写、不宣称全树静止。未写第五文件或共享/测试/Saved/资产，未创建/唤醒代理。

## HostRefreshCallerQuery：实施前验证登记（2026-10-04）

- 统筹接受只读诊断后直接授Host cpp仅Refresh OriginalScope、06 Subleases/本文三文件。组长直接 `gpt-6.1-sol / xhigh`，Fast默认关闭，无代理；两记录先登记。入口实际cpp51286/SHA E36A2495…、Subleases68019/9EA51524…、本文90364/F0EE8AC9…与冻结一致。只读Host h与ASC/Extension/Host接口七项hash均与既有冻结一致；不扩大到其它生产方法。
- 构建/运行分开保留：统筹Gate57 Succeeded（9 actions/37.13s/7 UHT文件），runtime/Editor DLL已链接，H3/Hero A已入新DLL；18:06:35既有 `ActorInfoTransaction.NativeLifecycleAndHistory` 单叶Success、事件段0错误/警告不证明生产Host。18:16:15与18:16:55实际日志已读，分别Refresh Stale CallerInvalidated Steps1和EndPlay Release Stale CallerInvalidated Steps3/metadata Accepted1；原问题存在。18:29:51～18:30:15第二次同Entry/单Pyrios复现由统筹交回，本组未执行UE；IMC旧配置拒绝已消失，与本根因分开。
- 源码可复核链：Character PossessedBy→Extension HandleControllerChanged→Host Refresh→ASC Try。Host OriginalScope内Installed→ASC CheckAvatarBindingIdentity→已提交actual快照；ASC原生写入前退休该快照，原生返回后、Commit前再次query必被否定。失败退出撤原操作，Context仍原Binding2/Write2但已Revoked且无快照，Release cleanup资格失败；日志未展开Step载荷，Release三步为源码推导，不冒称实测dump。H3有H分支NativeReason0是未赋值默认None，不作为ASC Clear成功证明。
- 修正仅caller query：保留原Host准入/完整Context/H/Extension身份；纯核原默认ASC/组件Owner、原Pawn/Extension端点与原opaque本地槽。替换为GetCurrentLocalAbilitySystemResource().HasSameResource(入口原H)，不从当前槽采纳新身份，不在ASC原生暂态查询其已提交资格。ASC认证与提交保持唯一；外层Ready前置、实际Try结果及自身Commit/Receipt发布保持原文。
- 有限验收范围：仅lambda文本diff、原方法其它段及其它方法逐字保护，query无ASC资格/ActorInfo/Ready/Installed查询，端点/原槽和Context/H检查保留，失败/Busy/后继隔离契约有限审查，读回/格式/共享hash/记录历史及三hash。原问题关闭须统筹新DLL同Entry必要冒烟核实际Refresh Commit/Receipt及原资源Clear；不以无警告或metadata Accepted代替实际结果，不扩大R0/严格矩阵。
- 非目标与冻结边界：无Host h、Release/H1/H2/H3、ASC/Extension/shared接口/输入/Hero B1/引擎/测试/资产/Saved/Obsidian/global写权，不Build/UE/Git/代理。需要lambda之外源码/新接口即停止；Hero B1互斥源码租约及其它工作线不属本三文件冻结。Gate55/56、H3源码交回时未编译及R0历史正文保留，当前进展仅更新第三行和本尾部。

### Refresh caller query修正：实际产出

- 生产仅改OriginalScope。Host的原准入与完整Context/H/端点身份资格保持；新增纯原ExpectedASC/Pawn/Extension解引用、默认ASC/组件Owner/Extension Owner及对象销毁flags核对，再以当前local slot与入口原H的opaque身份相等判定原槽仍在。删除原lambda内Installed查询，未调用ASC Context/Identity/ActorInfo、Ready或PublishedContext；没有替代原生权限或从当前getter追认来源。
- ASC独占原operation/actual/Busy/Commit，query只证明caller范围，合法原生快照退休不再把本地槽误判失效。外层Ready前置、原Try、实际ActorInfoRefresh Step、失败/Busy返回、自身CommittedContext赋值和真实Receipt发布保持原文。提交前后slot改变/原端点消失/原Context/H不符仍使queryfalse；不排队、换来源或重试，不修改正常输入和生命周期政策。

### 有限静态证据

- cpp1261行/51738字节/SHA256 `57D5279EA4F7DED9B971561DF77567E058B99DB3882ECE549BC1F13E63B8F883`。仅Refresh方法改变、方法集合保持；精确lambda替换推导与读回确认只有OriginalScope改变，入口、Try/Commit/发布尾部及全部其它方法逐字一致。query包含IsOriginalAvatarResource和原slot HasSameResource，ASC资格/ActorInfo/Ready/Installed读取0。源码无BOM/行尾空白，忽略字符串/注释后的括号180/180、787/787；不是C++/UHT或动态证明。
- 七项只读保护实际保持：Host h `6C80F72921443B2CE1EC6BCA1C3FB8FEA423FF390E7504B9D3828FFE532AFC1A`；ASC h40535C42…/cppCAD19824…；Extension h48AC44EF…/cpp69CFB9F4…；Host接口h84B989A6…/cppEB22E540…。没有新增include、共享签名、依赖、Proof/状态/缓存/计数、资源执行链或调度器；Release/H1/H2/H3和原失败诊断保持。保护hash只表示核对时事实，不把独立Hero B1工作线说成冻结。
- 两记录只第三行和尾部追加，旧正文前缀逐字保持；Validation原有10处行尾空白未改，新增部分无行尾空白。原R0、Gate55/56历史失败、Gate57旧DLL单叶Success以及两次真实PIE失败均保留；没有将源码修正或原生单叶通过写成生产Host成功。

### 未验、图文与冻结

- 本修正版未Build/UHT/UE/Git/自动化，没有新测试/矩阵/夹具；18:16与统筹交回18:29:51～18:30:15是修正前真实失败基线。须统筹统一编译新DLL，按原Entry/单Pyrios Possess及StopPIE必要冒烟核实际Refresh Commit/Receipt与原资源Clear；现有metadata Accepted1及H3有H分支默认NativeReason0不构成Clear成功证据。原R0 2 Fail/12 errors未重跑，Teams正式装配/其它消费者/资产/网络分别未验。
- Obsidian结构/Canvas只读核对已含H3/Gate57，但尚无本次query修正/两次生产失败；统筹源链接受后的独占图文步骤须同步原端点/槽query与ASC权限唯一、源码已落盘但未新编译/冒烟，保持原失败与单叶边界。本三文件不写图文/全局入口，不冒称已同步此修正版。
- 三文件明确冻结交回，最终三hash由消息提供。无第四文件、Host h/其它生产方法/ASC/Extension/shared接口/输入/Hero B1/UE-GAS库/资产/测试/Saved写入，无代理；其它合法在途源码不属本冻结，不自动续写、不宣称全树静止或根因动态闭合。
