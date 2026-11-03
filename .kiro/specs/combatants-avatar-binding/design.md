# Design Document

## Overview

把 ASC 绑定收敛为 Lyra 式流程，合并三份本地 ASC 订阅，并把 ASC 的输入缓冲与分段输入路由拆成私有协作者。行号为 2026-11-02 版本，开工重核。

改动面：
- `Source/GGYGO/Combatants/GGYGOCombatantState.{h,cpp}`
- `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.{h,cpp}`
- `Source/GGYGO/Character/Components/GGYGOHeroComponent.{h,cpp}`、`GGYGOCharacterMovementComponent.{h,cpp}`（订阅段 5664-5905）、`GGYGOHealthComponent.{h,cpp}`
- `Source/GGYGO/Character/Interfaces/GGYGOAvatarBindingHostInterface.{h,cpp}`
- `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.{h,cpp}`：
  - 绑定段 3637-5900
  - 输入段 1857-2949
  - 分段输入路由 2131-2512
  - 原生覆盖 1122-1283
- `Source/GGYGO/AbilitySystem/GGYGOAvatarBindingTypes.h`、`Private/GGYGOAvatarBindingProtocol.{h,cpp}`
- 新增 `Source/GGYGO/AbilitySystem/Private/GGYGOAbilityInputBuffer.{h,cpp}`、`GGYGOAbilityStepInputRouter.{h,cpp}`
- `Source/GGYGO/Teams/GGYGOSquadComponent.cpp`、`Source/GGYGO/GameModes/GGYGOGameMode.cpp`、`Source/GGYGO/AI/Boss/GGYGOBossEncounter.cpp`：只改调用点
- 测试：Combatants、AbilitySystem.ActorInfoTransaction、Teams、BossAI.Encounter

## 现状

```
PawnExtension::InitializeAbilitySystem → DispatchOriginalAvatarHostRequest
  → CombatantState::RequestAvatarBinding(291) → InitializeAvatarBinding(479-769)
  → ExecuteHostActorInfo(69-87，三选一) → ASC::TryExecute/TryBootstrap/TryReplaceRevoked(5001-5025)
  → ExecuteActorInfoTransaction... → 原生 Init → PublishAvatarBindingNotice(5378)
  → PawnExtension::InstallLocalAbilitySystemResources / NotifyLocalResourcesReady(856)
  → Hero / CMC / Health 各自的订阅 → ConsumeLocalAbilitySystemNotice
Controller 变化：PawnExtension::HandleControllerChanged(366) → Host Refresh 请求 → 遍历 Steps 取 CommittedContext
```

## Architecture

### Host 绑定流程

```cpp
// CombatantState
EGGYGOAvatarBindResult AGGYGOCombatantState::BindAvatar(APawn* NewPawn)
{
    if (bBindingInProgress) { LogNested(); return EGGYGOAvatarBindResult::Reentrant; }
    TGuardValue<bool> Guard(bBindingInProgress, true);
    APawn* Old = Cast<APawn>(AbilitySystemComponent->GetAvatarActor());
    if (Old && Old != NewPawn) ReleaseAvatar(Old);           // 取消能力、清输入、移除 Cue、广播 Released
    if (!NewPawn) { AbilitySystemComponent->ClearActorInfo(); return EGGYGOAvatarBindResult::Cleared; }
    AbilitySystemComponent->InitAbilityActorInfo(this, NewPawn);
    if (UGGYGOPawnExtensionComponent* Ext = UGGYGOPawnExtensionComponent::FindPawnExtensionComponent(NewPawn))
        Ext->HandleAbilitySystemBound(AbilitySystemComponent);   // 写资源句柄、广播 Ready
    return EGGYGOAvatarBindResult::Bound;
}
```

- 权威端由 `AttachAvatar` 调用；客户端由 `OnRep_AvatarPawn` 调用（Avatar 引用已复制）。
- PawnExtension 的 InitState 流程（Lyra 的 GameFrameworkComponentManager）保持现状。开工重核 `CanChangeInitState`、`HandleChangeInitState` 中依赖 Host 请求结果的地方，改为依赖"已收到 Ready"。
- `HandleControllerChanged`：直接 `ASC->RefreshAbilityActorInfo()`，然后 `CheckDefaultInitialization()`。
- `ReleaseAvatar(Old)`：
  1. `ASC->CancelAbilities(...)`（保留现有不可取消能力的诊断）；
  2. `ASC->ClearAbilityInput()`；
  3. `ASC->RemoveAllGameplayCues()`（开工重核现有释放流程实际移除的 Cue 范围，保持一致）；
  4. `OldExt->HandleAbilitySystemReleased()`。
- 嵌套请求：`bBindingInProgress` 期间的 BindAvatar 被拒绝，并按 Host 与请求 Pawn 诊断一次。

### PawnExtension 与订阅

```cpp
struct FGGYGOPawnASCNotice { EKind Kind /*Ready, Released*/; FGGYGOPawnASCResourceHandle Resource; };

class FGGYGOLocalASCSubscription          // PawnExtension.h 中声明，消费方作为成员持有
{
public:
    void Subscribe(UGGYGOPawnExtensionComponent* Ext, TFunction<void(const FGGYGOPawnASCNotice&)> Callback);
    void Unsubscribe();                    // 幂等
    UGGYGOAbilitySystemComponent* GetReadyASC() const;
    const FGGYGOPawnASCResourceHandle& GetConsumedResource() const;
    ~FGGYGOLocalASCSubscription() { Unsubscribe(); }
};
```

- 资源句柄 `FGGYGOPawnASCResourceHandle` 保留（不透明共享记录，每次绑定新建），作为"同一次绑定"的唯一身份，取代 `FGGYGOAvatarBindingContext` 在本地消费方中的用途。
- 分发时先复制订阅者列表，跳过分发过程中已退订的订阅者。
- 订阅类型自己处理"重复 Ready 忽略、Released 只清理已消费的同一资源"，然后调用消费方回调。三个消费方的回调只写各自的业务（Hero：关联输入会话；CMC：缓存 ASC 并复位移动状态；Health：订阅属性变化）。

### ASC 删除项

- 绑定段 3637-5900 中的 Context／IdentityOperation／ActualSnapshot／FailedInitCleanup／PublicationRecord／NativeWrite 相关全部类型与函数。
- `GetAvatarBindingContext`、`CheckAvatarBindingContext`、`IsAvatarBindingPublicationContextCurrent` 的消费方在开工重核时列全并逐一迁移；无法迁移的写入活动记录，不保留空壳。
- 换人退出（`TryExitAbilitiesForAvatarSwitch`／`CheckAvatarSwitchAbilitiesExited`）在第 4 步已简化，本 spec 迁到 Squad 侧或保留为 ASC 的一个小函数；第 6 步改为续放。

### 协作者

```cpp
class FGGYGOAbilityInputBuffer             // ASC 成员，持有 ASC 指针
{
public:
    FGGYGOAbilityInputRequestResult Receive(...);
    FGGYGOAbilityInputRequestResult End(...);
    void EndFromSource(const FSourceKey&);
    void Process(float DeltaTime, bool bGamePaused);
    void Clear();
    void OnAbilityFailed(FGameplayAbilitySpecHandle, const FGameplayTagContainer&);
    void OnGroupFreed();
};
class FGGYGOAbilityStepInputRouter
{
public:
    // CaptureInitialInputRoute、CaptureStepInputRequest、CommitStepInputFact、
    // HandleServerTargetData、HandleServerTargetDataCancelled
};
```

两个协作者通过 ASC 的 friend 访问 `ActivatableAbilities`、`AbilityTargetDataMap` 等原生成员；不复制原生状态。

## Error Handling

- 嵌套绑定：拒绝并诊断（Host、当前 Avatar、请求 Pawn）。
- 新 Pawn 无 PawnExtension：Init 仍执行；诊断"Avatar 缺少 PawnExtension，本地消费方不会就绪"。
- 释放时能力不可取消：保留现有诊断，不强制结束。

## Testing Strategy

- ActorInfoTransaction 测试（9 个）断言的是事务内部阶段。改写为绑定流程的外部契约：
  - 绑定后 ASC 的 ActorInfo 指向新 Pawn；
  - 旧 Pawn 收到 Released、新 Pawn 收到 Ready；
  - 旧能力被取消、输入被清空；
  - 嵌套请求被拒；
  - 已被替换的旧 Pawn 延迟解绑不影响新绑定。
- Combatants.Binding、DeathProjection、Teams.SquadSwitch、BossAI.Encounter 保持外部断言，调用点改名。
- 新增 Local_ASC_Subscription 测试：即时回放、重复 Ready 忽略、分发中退订、Released 只清同一资源。
- 联机：listen server + 1 客户端，客户端出生、切人、死亡重生。

## 风险

- PawnExtension 的 InitState 与 Experience 加载顺序耦合，删除 Host 请求后要确认 DataAvailable→DataInitialized 的条件仍能满足。开工后先改 Host 流程并编译运行出生流程，再删协议。
- Binding Context 被 FX 移动来源身份引用（第 3 步保留）。本 spec 改为使用 CMC 的移动来源证明 + PawnExtension 资源句柄。

## 实现差异（2026-11-03）

- **释放顺序**：按 Lyra `UninitializeAbilitySystem` 与旧协议的实际顺序实现为"取消能力 → 清输入 → 移除全部 Cue → 解除 ActorInfo（宿主存活时 `InitAbilityActorInfo(Host, nullptr)` 保留 Owner，宿主 EndPlay／Destroyed 时 `ClearActorInfo`）→ 旧 Pawn 广播 Released"。Requirement 2.2 把 Released 写在 Clear 之前；按该顺序时 Boss Encounter 两例在 Released 回调里看到 ASC 仍以旧 Pawn 为 Avatar（Test_R11），与 Requirement 6 的"顺序不变"冲突，因此采用旧顺序。改绑时 ActorInfo 先回到 Owner-only，再对新 Pawn Init 并广播 Ready。
- **宿主接口**：`IGGYGOAvatarBindingHostInterface` 收敛为 `ReleaseAvatarBinding(APawn* ExpectedAvatar)`。重核后 PawnExtension 唯一的真实需要是死亡销毁前请求宿主立即释放（`CharacterBase::UninitAndDestroy`）；读取 ASC 已由 `IAbilitySystemInterface` 提供，没有保留"取得 ASC"的空接口。
- **延迟解绑**：宿主同时订阅 Avatar 的 `OnEndPlay` 与 `OnDestroyed`（未 BeginPlay 的 Actor 销毁时只有后者），两者都只在 Actor 仍是 `BoundAvatar` 时释放。`BoundAvatar` 是 ASC 实际绑定的 Pawn；客户端 `AvatarPawn` 是服务器选择的复制值，二者分开保存。
- **绑定拒绝**：除嵌套请求外，保留现有的两条拒绝：ASC 带 `State.Dying/Dead` 时不接受新 Avatar；目标 Pawn 仍绑定其它宿主的 ASC 时拒绝（跨宿主须先由原宿主释放）。`AttachAvatar` 直接返回 `EGGYGOAvatarBindResult`。
- **订阅消费方**：除 Hero、CMC、Health 外，`LocomotionFX` 也是 `RegisterLocalAbilitySystemNoticeAndCall` 的消费方，一并迁到 `FGGYGOLocalASCSubscription`。Health 的订阅从 `CharacterBase` 移入 Health 自身（注册时订阅，迟到时回放），`CharacterBase` 的转发样板删除。
- **Context 消费方迁移**：FX 移动来源身份改为"CMC 来源证明 + 发布时的 ASC"（`FGGYGOFXSourceIdentity::GetSourceAbilitySystem`）；Squad 换人请求与测试的绑定身份改用 PawnExtension 资源句柄；分段输入来源证明去掉 BindingContext（激活身份、Avatar、Controller、CMC 已覆盖同一次绑定）；换人退出 `TryExitAbilitiesForAvatarSwitch`／`CheckAvatarSwitchAbilitiesExited` 改为核对期望 Avatar。
- **ASC 拆分**：`FGGYGOAbilityInputBuffer`、`FGGYGOAbilityStepInputRouter` 放在 `AbilitySystem/Private/`，由 ASC 以 `TUniquePtr` 持有。Step 路由需要原生实现时经 ASC 私有的 `ForwardNativeTargetData*` 调回 `Super`；两处原生 RPC 覆盖留在 ASC 并委托。分发边沿 `FDispatch` 由路由持有，输入缓冲在原生按下／激活期间用 `FScopedDispatch` 登记。
- **测试**：`ActorInfoTransaction`（9 例）与 `PawnExtension.LocalResources` 删除，改为 `AbilitySystem.AvatarBinding.*`（3 例）与 `Character.PawnExtension.LocalASCSubscription`；`Combatants.Binding` 改为 3 例外部契约（其中失败 Init 清理一例随协议删除）；`ProjectDiagnostics.Combatants.BindingSuccessor` 断言"在 Released 回调中接管成功"，与 Requirement 2.4 的嵌套拒绝相反，删除，由 `NestedRequestRejected` 覆盖。共享测试世界 `FGGYGOCombatantBindingTestWorld` 调用 `InitializeActorsForPlay`：未初始化的世界不执行 Actor 的动态委托（`AActor::ProcessEvent`），也不走 PostInitializeComponents。
- **任务 2.4**：中间 PIE 检查未执行（PIE 需用户批准），以集中编译与 NullRHI 测试代替。
