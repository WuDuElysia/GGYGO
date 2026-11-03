# Design Document

## Overview

把 FX 关闭收敛为"持有者关闭"，把发布宿主从 ASC 迁到 FX 组件。行号为 2026-11-02 版本，开工重核。

改动面：
- `Source/GGYGO/FX/GGYGOMontageFXPublication.{h,cpp}`
- 新增 `Source/GGYGO/FX/Components/GGYGOMontageFXReplicationComponent.{h,cpp}`
- `Source/GGYGO/FX/Components/GGYGOLocomotionFXComponent.cpp`、`GGYGORemoteMontageFXComponent.cpp`
- `Source/GGYGO/FX/Tasks/GGYGOAbilityTask_PlayNiagaraEffect.cpp`
- `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.{h,cpp}`：FX 段、Retirement_Wrappers
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.{h,cpp}`：DispatchRetiredMontageFX、FindRetirementOutput 的 FX 用途
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOMontageActionResources.cpp`：发布入口
- `Source/GGYGO/Combatants/GGYGOCombatantState.{h,cpp}`：挂组件
- 测试：FX.MontagePublication

## 现状

```
GA 激活退休
  → ASC Retirement_Wrappers 收集 RetiredActivations
  → ExecuteWithMontageFXRetirement 收尾：
        PrepareMontageFXRetirements(按激活来源关闭)
        PrepareInvalidMontageFXSources(扫描全部来源，关闭已失效者)
        DispatchMontageFXRetirements
同时：FGGYGOMontageActionResources::ReleaseFX 按 lease 关闭（MontageActionResources.cpp:266-296）

移动 FX：LocomotionFXComponent → ASC::TryPublishLocomotionFX(932-988)
         → CMC 来源证明 → PublicationOwner::Begin
复制：ASC.MontageFXState（REPNOTIFY_Always）、ASC::MulticastMontageFXTerminal
```

## Architecture

### FX_Replication_Component

```cpp
UCLASS()
class UGGYGOMontageFXReplicationComponent : public UActorComponent
{
public:
    static UGGYGOMontageFXReplicationComponent* FindForASC(const UAbilitySystemComponent* ASC);

    // 权威端入口，核对事实与原 ASC::TryPublishMontageFX 相同
    bool PublishMontageFX(UGGYGOGameplayAbility* Ability, const FGGYGOAbilityActivationHandle& Activation,
        UGGYGOAbilityTask_PlayMontageAndWaitForEvent* Task, const FGGYGOMontageWindowFact& BeginFact,
        const FGGYGOMontageFXRecord& Request, FGGYGOMontageFXLease& OutLease, FString& OutError);
    bool PublishLocomotionFX(UGGYGOCharacterMovementComponent* Movement, const FGGYGOMotionExecutionSnapshot& Interval,
        const FGGYGOMontageFXRecord& Request, FGGYGOMontageFXLease& OutLease, FString& OutError);
    UGGYGOMontageFXPublicationOwner* GetPublicationOwner() const;

private:
    UPROPERTY(ReplicatedUsing = OnRep_State) FGGYGOMontageFXState State;
    UPROPERTY(Transient) TObjectPtr<UGGYGOMontageFXPublicationOwner> PublicationOwner;
    UFUNCTION() void OnRep_State();
    UFUNCTION(NetMulticast, Reliable) void MulticastTerminal(const FGGYGOMontageFXTerminal& Terminal);
};
```

- `AGGYGOCombatantState` 构造时 `CreateDefaultSubobject`，`SetIsReplicatedByDefault(true)`。
- `OnRegister` 中按现有 ASC::OnRegister 的方式创建或重新挂接 Publication_Owner（`RegisterHost`），`OnUnregister` 中 `Shutdown`。
- `FindForASC`：`ASC->GetOwner()->FindComponentByClass<>()`。
- `IGGYGOMontageFXHost` 接口删除，调用方改用 `FindForASC`。开工重核是否有蓝图或其它 C++ 依赖该接口。

### 关闭路径

- Montage FX：`FGGYGOMontageActionResources::ReleaseFX` 已逐 lease 关闭，保持不变。PlayerCombo 与 BossMelee 的终止清理（`CleanupAbilityResourcesForTermination` 及其调用的 Release*）覆盖所有原生结束路径。开工重核要确认 DestroyActiveState、RemoveAbility、ClearActorInfo 都会走到 GA 结束清理；若某条路径不走 EndAbility，就在该 GA 的 `OnRemoveAbility` 中补一次资源释放。
- 移动 FX：开工重核 LocomotionFXComponent 现在如何得知来源退役（CMC 的 `QueueLocomotionSourceRetirement`／`DispatchLocomotionSourceRetirements`）。由 LocomotionFXComponent 在收到退役时关闭对应 Cue 的租约，取代扫描。
- 兜底：Publication_Owner::Shutdown 关闭残留租约，按 Abort 处理并诊断一次（组件注销或 Actor 销毁时）。这是寿命终点的清理，不是周期扫描。

### ASC 与 GA 的删除项

ASC：
- 删除 `ExecuteWithMontageFXRetirement`、`FScopedMontageFXRetirementOutput`、`GetMontageFXRetirementOutput`、`GetMontageFXCloseOutput`、`PrepareMontageFXRetirements`、`DispatchMontageFXRetirements`、`PrepareInvalidMontageFXSources`。
- 删除全部 `*WithRetirementOutput` 函数。原生覆盖（DestroyActiveState、OnRemoveAbility、InitAbilityActorInfo、ClearActorInfo、RefreshAbilityActorInfo、NotifyAbilityActivated／Ended）直接调用原 *WithRetirementOutput 函数体里的逻辑。
- 删除 `TryPublishMontageFX`、`TryPublishLocomotionFX` 及两个 Locomotion 校验、`MontageFXState`、`MontageFXPublicationOwner`、`OnRep_MontageFXState`、`MulticastMontageFXTerminal`、`SendMontageFXTerminal`。

GA：
- 删除 `DispatchRetiredMontageFX`。
- `FindRetirementOutput` 不再取 ASC 的输出。GA 内 `RetiredActivations` 参数链在本步只剩激活退休的历史收集，没有 FX 消费者；该参数链在第 4 步随终止状态机一起删除。本步不扩大改动面。

### 绑定事务中的 FX 义务

`InvalidateAvatarBinding(..., TArray<FGGYGOMontageFXCloseObligation>* OutRetirements)` 与 CombatantState::CloseAvatarBindingLifecycle 的 FX 派发：
- 改为不携出 FX 义务；
- Avatar 解绑时，GA 被取消或结束，由持有者关闭。
- 开工重核 CloseAvatarBindingLifecycle 的调用时机：Actor EndPlay 时组件 Shutdown 会兜底关闭。

## Error Handling

- 找不到复制组件：拒绝发布，诊断包含 ASC 与 Owner 路径。
- Shutdown 时残留租约：按 Abort 关闭，诊断一次，内容为来源种类、occurrence、System 路径。

## Testing Strategy

- FX.MontagePublication 测试中断言 ASC 宿主或 Retirement_Wrappers 的部分，改为在 FX_Replication_Component 上断言同样的外部结果：
  - 发布后复制记录出现；
  - 持有者释放后终止多播发出、记录移除；
  - 晚加入客户端只收到活动记录。
- 新增：
  - GA 以 Cancel 结束时持有者关闭租约（Abort）；
  - 组件注销时残留租约被关闭并诊断。
- 联机：listen server + 1 客户端；中途加入的客户端用第二个客户端进程模拟。

## 开工重核结论与实现差异（2026-11-03）

- 持有者关闭已存在：PlayerCombo 的 `FGGYGOMontageActionResources::ReleaseFX` 逐 lease 关闭；`UGGYGOLocomotionFXComponent` 在 CMC 来源退役（`OnLocomotionSourceRetired`）、PawnExtension Released／Closing 通知和组件注销时关闭。BossMelee 不发布 FX。因此本步只删除另外两条写路径（ASC 退休包装、扫描），持有者路径不改。
- 原生结束路径：DestroyActiveState／RemoveAbility／取消都经 GA 的原生清理来源走到 `CleanupAbilityResourcesForTermination`。例外是原生清理被拒（本实例 ScopeLock 中、实例或 Allocation 已变、GAS 认为不可结束），此前由 ASC 按激活退休关闭 FX；现在 `UGGYGOPlayerComboAbility::OnRemoveAbility` 按 Abort 归还本段仍持有的 FX lease，不代做其它资源清理。组件注销／Actor 销毁时由 `Shutdown` 兜底并报告一次。
- 宿主：`UGGYGOMontageFXReplicationComponent`（`FX/Components/`），由 `AGGYGOCombatantState` 构造时创建（子对象名 `MontageFXReplication`）。`UGGYGOMontageFXPublicationOwner` 的签发者类型由 ASC 改为宿主组件 `UActorComponent`；Locomotion 本地能力核对改为"绑定签发 ASC 与宿主同属一个 Owner"。观察事实的 `Issuer` 字段现在是宿主组件，Editor 工具 `BeginFXObservation` 仍接收原 ASC，从其 Owner 取宿主。
- `IGGYGOMontageFXHost` 只被 ASC、Task、MontageActionResources 与 Editor 观察工具使用，没有蓝图依赖，已删除；调用方改用 `FindForASC`。
- 删除：ASC 的 15 个 `*WithRetirementOutput` 与退休输出栈、`TryPublishMontageFX`／`TryPublishLocomotionFX`、两个 Locomotion 校验、复制状态与多播、`GetLifetimeReplicatedProps`／`OnRegister` 覆盖；`InvalidateAvatarBinding` 的 FX 输出参数与 `MissingRetirementOutput` 原因；GA 的 `DispatchRetiredMontageFX`、`IsPublicationSourceCurrent`；发行者的 `PrepareCloseSource`；CombatantState 两处 FX 派发。保留只读的 `GetSourceIdentities`（测试使用）。
- GA 的 `RetiredActivations` 参数链保留到第 4 步：`FindRetirementOutput` 只返回 GA 自己外层调用安装的数组，ASC 受控 Try 自带一份，均随调用结束丢弃，不再有 FX 消费者。
- ASC.h 仍包含 `FX/GGYGOMontageFXPublication.h`，避免依赖它间接引入 FX 类型的文件在本步断编；ASC 本身已不使用 FX 类型。

## 风险

- 复制属性从 ASC 迁到组件后，网络序列化变化，客户端与服务器必须使用同一构建（本地测试满足）。
- 编辑器下已保存的 CharacterSlot／BossState 蓝图子类会自动获得新的默认子对象；开工后在 Editor 中确认这些蓝图的组件列表正常，不需要重新保存，除非 Editor 提示。
