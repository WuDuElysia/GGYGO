# Design Document

## Overview

用 GAS 原生寿命替换自建的激活／终止状态机，合并 Montage 播放身份，把段内防 ABA 交给资源释放时的解绑。行号为 2026-11-02 版本，开工重核。

改动面：
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.{h,cpp}`：构造前约 940 行协议代码，以及 ActivateAbility／EndAbility／CancelAbility
- `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.{h,cpp}`：
  - 激活段 1454-1806
  - 评估令牌 4270-4560
  - 播放段 541-790、1059-1121、1285-1453
  - Initial 路由与分段输入 2131-2512
  - 换人退出 5542-5770
- `Source/GGYGO/AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.{h,cpp}`
- `Source/GGYGO/Animation/Runtime/GGYGOMontageGuardAnimInstance.{h,cpp}`、`GGYGOMontagePlayGuard.h`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.{h,cpp}`、`GGYGOMontageActionResources.{h,cpp}`
- `Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.{h,cpp}`、`BehaviorTree/BTTask_GGYGOActivateAbility.cpp`
- `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.{h,cpp}`、`GGYGOActionMotionExecution.{h,cpp}`（只合并两参入口）
- `Source/GGYGOEditor/Private/GGYGOPlayerActionObservation.cpp`
- 测试：AbilitySystem、BossAI（含 `GGYGOBossMeleeLifecycleTestAbility.h`）、Animation.MontageGuard、Combatants、Teams、Editor.Animation、Movement.ActionMotion

## 现状调用链

```
ProcessAbilityInput → TryActivateAbilityWithTerminationBoundary → ExecuteWithMontageFXRetirement(第3步已删)
  → ActivateAbilityWithRetirementOutput → FControlledAbilityActivationCall 入栈
  → Super::TryActivateAbility → CanActivateAbility(评估令牌) → PreActivate → NotifyAbilityActivated
  → ObserveControlledAbilityActivation → IssueControlledActivation
  → GA::ActivateAbility → FScopedRetirementOutput → ExecuteActivationWithRetirement
  → InitializeAbilityActivation → 组准入 Finalize → 镜头 → ActivateAbilityBody
结束：RequestAbilityEnd → BeginOriginalTermination → ResumeOriginalTermination → EndAbility
  → ExecuteEndWithRetirement → TryCompleteOriginalTermination → ASC::TryPublishOriginalTerminationCompleted
  → OnAbilityTerminationCompleted（BT 与 Editor 观察消费）
```

## Architecture

### 激活身份

```cpp
struct FGGYGOAbilityActivationHandle::FActivationProof
{
    TWeakObjectPtr<UGGYGOAbilitySystemComponent> ASC;
    TWeakObjectPtr<UGGYGOGameplayAbility> Ability;
    FGameplayAbilitySpecHandle Spec;
    FPredictionKey ActivationKey;
    TWeakPtr<const FGameplayAbilityActorInfo> Allocation;
    uint64 Serial = 0;   // GA 内单调递增，区分 ServerOnly 能力的连续激活
};
```

- 签发：`ASC::NotifyAbilityActivated(Handle, Ability)` 中调用 `ProjectAbility->IssueActivation(Handle)`。原生 PreActivate 在调用 ActivateAbility 之前调用它，是唯一签发点。
- 当前激活：`UGGYGOGameplayAbility::CurrentActivation`。
- 退役：`UGGYGOGameplayAbility::EndAbility` 覆盖中，`IsEndAbilityValid` 且未被 ScopeLock 延迟时：
  1. 调用 `CleanupAbilityResourcesForTermination({CurrentActivation, bWasCancelled})`；
  2. 调用 `Super::EndAbility`；
  3. 返回后把 CurrentActivation 置空。

  ScopeLock 延迟时原生会把 EndAbility 排进 WaitingToExecute 并直接返回。覆盖函数要先判断 `ScopeLockCount > 0`，直接转给 Super，不做清理；之后真正执行时会再次进入覆盖函数。
- `IsActivationCurrent(H)`：`H.HasSameActivation(CurrentActivation) && IsActive()`。
- 结束期间：`bEndingActivation` 在清理和 Super 执行期间为真。供 Initial 路由判断"本激活正在结束"。

### 结束与取消

```cpp
FGGYGOAbilityTerminationResult RequestAbilityEnd(const FGGYGOAbilityActivationHandle& Original, bool bReplicate, bool bWasCancelled)
{
    if (!IsActivationCurrent(Original)) return {ENotCurrent};
    EndAbility(CurrentSpecHandle, CurrentActorInfo, CurrentActivationInfo, bReplicate, bWasCancelled);
    return {EAccepted};
}
RequestAbilityCancel：多一步 CanBeCanceled 检查，调用 CancelAbility。
```

调用方现有的 switch（Completed／Accepted／Deferred／AlreadyPending）合并为 Accepted 与非 Accepted 两支，只用于诊断。

### ActivateAbility 主流程

```
ActivateAbility(Handle, ActorInfo, ActivationInfo, Trigger)
  Original = CurrentActivation              // Issue_Point 已签发
  InitializeAbilityActivation(Original)
  if (!IsActivationCurrent(Original)) return  // 初始化可能经 BP 结束能力（真实外调）
  if (!FinalizeGroupAdmission()) { EndAbility(...cancelled); return }
  if (!IsActivationCurrent(Original)) return  // 组准入会取消其它能力（真实外调）
  镜头模式与偏移（Hero 接收方可能外调）→ 各后一次核对
  ActivateAbilityBody(Original, ...)
```

### 输入失败排队

`ProcessAbilityInput` 的 TryOnce 中：

```
FScopedInputActivationAttempt Attempt(this, Handle, CurrentSources);  // 设置 ASC.CurrentInputAttempt
bActivated = TryActivateAbility(Handle);
```

`NotifyAbilityFailed(Handle, Ability, Reason)`：仅当 `CurrentInputAttempt && CurrentInputAttempt->Handle == Handle` 时，把当前来源记为可排队重试（沿用现有组阻塞判断）。删除 `FScopedAbilityActivationEvaluation`、`FScopedAbilityActivationQuery`、`BeginAbilityActivationEvaluation` 系列、`ConsumeAbilityActivationFailureOrigin`。

### BT 等待

```
Wait.Handle = Spec
Wait.bTryInProgress = true
Wait.Binding = ASC->OnAbilityEnded.AddUObject(..., HandleEnded)   // 匹配 AbilitySpecHandle
bool bOk = ASC->TryActivateAbility(Spec)
Wait.bTryInProgress = false
if (!bOk) { Unbind; return Failed }
if (Wait.bEndedDuringTry) { Unbind; return Wait.bWasCancelled ? Failed : Succeeded }
return InProgress
HandleEnded(Data): if (Data.AbilitySpecHandle != Wait.Handle) return;
  if (Wait.bTryInProgress) { Wait.bEndedDuringTry = true; Wait.bWasCancelled = Data.bWasCancelled; return }
  Unbind; FinishLatentTask(...)
```

InstancedPerActor 且禁止重触发，同一 Spec 同时只有一次激活，所以按 Spec 句柄匹配足够。

### Montage 播放

```
ASC::PlayAbilityMontage(Ability, ActivationInfo, Montage, Rate, Section, StartTime, FGGYGOMontagePlayback& Out)
  Guard = Cast<UGGYGOMontageGuardAnimInstance>(AnimInstance)
  if (!Guard) → Legacy 分支（视重核结果保留或删除）
  FGGYGOMontagePlayGuardScope Scope(Guard, ...)   // 识别本次调用创建的实例
  Duration = Super::PlayMontage(...)
  Out = { Scope.CreatedInstanceId, Ability->CurrentActivation, Montage }
ASC::IsPlaybackCurrent(const FGGYGOMontagePlayback& P)
  LocalAnimMontageInfo.AnimatingAbility == P.Ability && AnimMontage == P.Montage
  && Ability->IsActivationCurrent(P.Activation)
ASC::ClearPlayback(P): IsPlaybackCurrent 时清 AnimatingAbility 与能力 CurrentMontage
```

删除：
- `FGGYGOAbilityMontagePlaybackHandle::FPlaybackProof`、`MontagePlaybackProvenance`、`ReconcileMontagePlaybackOwnership`；
- `CheckMontagePlaybackOwnership` 与 `CaptureMontagePlaybackOwnership` 中的 ActorInfo 快照比较；
- GA 终止时的 `OriginalMontageCapture`。

Avatar 变化时 `InitAbilityActorInfo` 已清空 Local 播放信息，所有权自然失效。

MontageGuard 保留 Scope 链（识别创建实例、处理播放期间重入）与 ActionPoseContract。开工重核其中仅为 ASC 证明服务的字段（LifecycleGeneration 的对外查询等），没有其它消费者的删除。

### 段寿命

`FStepMotionResources` 的 Release 顺序：
1. `UnregisterNativeCallbacks`
2. `ReleaseMontageActionMotion`（解除位移观察）
3. 解除 Trace 订阅并关闭窗口
4. 取消 FX 本地启动票据并关闭发布
5. `ClearWatchdog`
6. `EndTask`

回调 lambda 只捕获 `TWeakPtr<FStepMotionResources>`，处理时比较 `Self->StepMotionResources == Pinned`。FX 本地启动 Ready 可能跨帧到达，额外比较 StepToken。Task 派发谓词去掉 `CheckMontagePlaybackOwnership`，只保留"Task 未结束、实例 ID 匹配"。

### 换人退出（过渡）

`TryExitAbilitiesForAvatarSwitch` 改为：
- 对 AvatarExitPolicy=Cancel 的活动能力调用 `RequestAbilityCancel(CurrentActivation)`；
- 随后检查这些能力已不再 Active。

删除取消预留与 `FScopedAvatarSwitchAbilityExit` 中依赖 Termination_Machine 的部分。第 6 步再改为续放。

### 由第 1 步移入的收敛

**Boss 共享资源。** 现状：`FOriginalMeleeResources`（BossMelee.cpp:33-66）自持 Task、Movement、MotionSource、MotionHandle、MontageInstanceId、TraceWindow、Watchdog、双完成标志，起止逻辑在 248-330、740-760，与 `FGGYGOMontageActionResources`（MontageActionResources.h:18-103）重复。Boss 另有 Profile 位移（`CMC::BeginActionMotion(Profile, PlayRate)`）、固定超时 Watchdog 与 Mesh Tick 保存恢复。

`FGGYGOMontageActionResources` 在本 spec 重写段寿命时增加：

```
bool BeginProfileMotion(const UGGYGOActionMotionProfile* Profile, float PlayRate, FString& OutError);
bool ArmFixedWatchdog(UWorld* World, float TimeoutSeconds, FTimerDelegate Callback, FString& OutError);
```

两种位移互斥，`ReleaseMotion` 统一释放（Profile 句柄走 `CMC::EndActionMotion`）。BossMelee 自己只保留 `SavedMeshTick`、`bSavedUpdateRateOptimizations`、`bRestoreMesh`、`bRemovePrerequisite`。Boss 回调按"段寿命"一节同样只比较所属资源。

**两参入口合并。** CMC.cpp:2046-2430 中不带 Facing 的 `BeginMontageActionMotion` 与带 Facing 版本合一，调用方显式传默认 Facing；共享资源的两个 `BeginMotion` 重载同步合并。CMC 其余对 `FGGYGOActionMotionExecution` 的一行转发保留。

**组准入测试日志。** 删除 `FinalizeAbilityGroupAdmission` 中的 `WITH_DEV_AUTOMATION_TESTS` 日志块（基线 ASC.cpp:3207-3374 一带），开工重核其测试消费者，必要时改为断言外部结果。

## Error Handling

- 签发时 ActorInfo 不可用：不签发，诊断一次；ActivateAbility 发现无当前激活时直接 EndAbility(cancelled)。
- RequestAbilityEnd 返回 NotCurrent：调用方只诊断，不重试。
- 播放入口找不到 AnimInstance 或 Guard 拒绝：返回失败与原因，Task 走现有失败路径。

## Testing Strategy

- 现有依赖 OnAbilityTerminationCompleted 的 4 个测试文件改为订阅 OnAbilityEnded，断言同样的外部时序：Try 内同步结束、Try 后结束、被取消。
- ABA 外部契约（保留并补齐）：
  - 能力结束后同帧重新激活：旧 Task、旧位移完成、旧 Trace 命中、旧 Watchdog 均不作用到新激活；
  - 旧激活的 RequestAbilityEnd 返回 NotCurrent，新激活不受影响；
  - Montage 被同帧替换时，旧 Task 不清除新播放的 AnimatingAbility。
- 删除：断言 TerminationRecord 阶段、OpenTryCalls、评估令牌、PlaybackProof 内部字段的测试。
- 联机：listen server + 1 客户端，打三段普攻；用服务器拒绝某段的测试开关验证纠正重放（沿用现有 N3 测试入口，开工重核其位置）。

## 风险

- 这是改动面最大的一步。按"身份与结束 → 输入排队 → BT → 播放 → 段寿命 → 测试"分小步编译，每小步在本会话内编译一次，不跑完整测试。
- PlayerCombo、BossMelee 中 RequestAbilityEnd 的调用点很多（PlayerCombo 约 40 处），统一改为新返回值语义。

## 实现差异（2026-11-03）

- 退役时点：在 `ASC::NotifyAbilityEnded` 调 Super 之前退役（置空 CurrentActivation 并清 bEndingActivation），不是在 `EndAbility` 的 Super 返回后。原因：原生 `OnAbilityEnded` 在 Super 内广播，广播内重激活签发的后继若在返回后被置空，后继会失去身份。`EndAbility` 返回后只在当前身份仍是本次结束的身份时补退役（原生未到达 ASC 通知的情况）。
- 延后请求：原生 ScopeLock 期间，`RequestAbilityEnd／Cancel` 不调原生 End／Cancel 排队，而是排一个"重新请求原激活"的委托，执行时重核 `IsActivationCurrent`。原生排队的 End 不比较激活，会结束后继。原生调用方（ClearAbility 等）的 ScopeLock 延后仍按原生规则。
- 播放身份：`IsPlaybackCurrent` 除 AnimatingAbility、AnimMontage、PlayInstanceId 与激活外，还要求 ASC 当前 AnimInstance 是本次播放的 Guard 实例。Avatar 变化会重置 Local 播放信息，PlayInstanceId 从头计数，同一能力在新 Avatar 上播放同一资产时序号可能重合。
- 激活准入：`CanActivateAbility` 只对 InstancedPerActor 拒绝"Spec 已激活"（AI 查询如实返回不可用）；InstancedPerExecution 仍可并发，`IsDataValid` 只拒绝 NonInstanced 与 `bRetriggerInstancedAbility`。
- 相机：`CleanupAbilityResourcesForTermination` 直接调 `ClearCameraOffset／ClearCameraMode`，它们只归还申请时保存的接收者与凭证，不再在终止记录里复制一份。
- 共享资源：Trace 窗口（窗口句柄、作者声明、命中订阅）进入 `FGGYGOMontageActionResources`，BossMelee 使用；PlayerCombo 的 Trace 仍在 GA 上，释放顺序在 GA 内保证。`BeginProfileMotion` 同时登记 CMC 失败观察。
- 换人退出：候选准入改为"有当前激活身份；默认取消的实例可取消"；取消后实例仍 Active 即 `TerminationNotCompleted`，结果字段改为 `TerminationOutcome`。
