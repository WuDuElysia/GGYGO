# Design Document

## Overview

在第 5 步完成的"每个槽位独立 ASC、换人不重绑"基础上，实现换人续放、留场、切回与进退场。行号为 2026-11-02 版本，开工重核。

改动面：
- `Source/GGYGO/Teams/GGYGOSquadComponent.{h,cpp}`：切换流程与队员状态
- `Source/GGYGO/Teams/GGYGOCharacterSlot.{h,cpp}`：队员状态复制（若需要）
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.{h,cpp}`：换出决定与控制事件
- `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.{h,cpp}`：删除换人退出旧实现；提供补发释放
- 新增 `Source/GGYGO/Teams/GGYGOSquadTransitionAbility.{h,cpp}`
- `Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.cpp`：目标过滤
- `Source/GGYGO/System/GGYGOGameplayTags.{h,cpp}`：新标签
- `Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp`：失去控制时的输入释放
- 资产：
  - `GE_OffField`（无限时，授予 State.OffField 与 Restriction.ImmuneDamage，带伤害免疫组件）
  - 测试用进场／退场能力

## 队员状态

| 当前状态 | 事件 | 下一状态 |
| --- | --- | --- |
| Benched | 被切入 | Active（显示、进场） |
| Active | 被换出，有续放能力 | Lingering（施加 Off_Field） |
| Active | 被换出，无续放能力 | Exiting（施加 Off_Field、退场） |
| Lingering | 续放能力全部结束 | Exiting（退场） |
| Lingering | 被切回 | Active（移除 Off_Field，施加 Return_Pending 直到续放结束，不进场） |
| Exiting | 退场能力结束或未授予 | Benched（移除 Off_Field，隐藏、停用） |
| Exiting | 被切回 | Active（取消退场，移除 Off_Field，有续放则施加 Return_Pending） |

Squad 为每个槽位保存一条记录：

```cpp
struct FSlotRuntime
{
    EGGYGOSquadMemberState State;                 // Benched, Active, Lingering, Exiting
    TArray<FGameplayAbilitySpecHandle> Continuing;// 选择 ContinueOnField 的能力
    FGameplayAbilitySpecHandle ExitAbility;       // 正在执行的退场能力（无则无效）
    FActiveGameplayEffectHandle OffFieldEffect;
    bool bReturnPending = false;
};
```

服务器上 Squad 订阅每个槽位 ASC 的 OnAbilityEnded，按 Spec 句柄更新 Continuing 与 ExitAbility。复制方面：可见性、碰撞、移动模式由 Pawn 原生复制；Off_Field 由 GE 复制。客户端是否需要知道 State，开工时按 UI 需求决定；当前不需要，不新增复制字段。

## 切换流程（服务器）

```
SwitchToSlot(Target)
  校验：目标有效、有 Avatar、未死亡、不是当前 Active
  Old = Active, New = Target
  // 1. 换出 Old
  for each active ability A on Old.ASC:
      Decision = A->OnAvatarSwitchOut(Context{Target, Source})
      Decision == Cancel ? A->RequestAbilityCancel : Old.Continuing.Add(A.Spec)
  Old.ASC.ReleaseHeldInputForControlLoss()      // 补发释放
  for each A in Old.Continuing: A->OnOwnerControlLost()
  Hero(Old)->ReleasePlayerInput()
  // 2. 控制权
  PC->UnPossess(); PC->Possess(New.Pawn)
  // 3. 切入 New
  if New.State == Lingering or Exiting:
      CancelExitIfAny(New); RemoveOffField(New)
      if (!New.Continuing.IsEmpty()) ApplyReturnPending(New)
      for each A in New.Continuing: A->OnOwnerControlRegained()
  else:
      ShowAndEnable(New); SendEvent(New.ASC, Event.Squad.SwitchIn)
  New.State = Active
  // 4. Old 去向
  ApplyOffField(Old)
  Old.Continuing.IsEmpty() ? BeginExit(Old) : (Old.State = Lingering)
OnAbilityEnded(Slot, Spec):
  Slot.Continuing.Remove(Spec)
  if (Slot.State == Lingering && Slot.Continuing.IsEmpty()) BeginExit(Slot)     // Off_Field 保持到退场结束
  if (Slot.State == Active && Slot.bReturnPending && Slot.Continuing.IsEmpty()) RemoveReturnPending(Slot)
  if (Spec == Slot.ExitAbility) FinishExit(Slot)
BeginExit(Slot):
  Slot.State = Exiting
  Activated = SendEvent(Slot.ASC, Event.Squad.SwitchOut)   // 记录被激活的退场能力 Spec
  if (Activated == 0) FinishExit(Slot)
FinishExit(Slot): RemoveOffField; Hide; DisableCollision; DisableMovement; Slot.State = Benched
```

- Exiting 期间保持 Off_Field_State，退场动作中也不可受击（与留场一致）。
- `ReleaseHeldInputForControlLoss`：由 ASC 输入缓冲协作者提供。对仍处于按住状态的 Spec 产生一次 Released 边沿并立即派发 AbilitySpecInputReleased，再清空输入。这是唯一新增的输入路径。

## 能力接口

```cpp
UENUM(BlueprintType) enum class EGGYGOSwitchOutDecision : uint8 { Cancel, ContinueOnField };
USTRUCT(BlueprintType) struct FGGYGOSwitchContext
{
    UPROPERTY(BlueprintReadOnly) int32 TargetSlotIndex = INDEX_NONE;
    UPROPERTY(BlueprintReadOnly) EGGYGOSwitchSource Source = EGGYGOSwitchSource::PlayerRequest;
};
UFUNCTION(BlueprintNativeEvent) EGGYGOSwitchOutDecision OnAvatarSwitchOut(const FGGYGOSwitchContext& Context);
UFUNCTION(BlueprintImplementableEvent) void OnOwnerControlLost();
UFUNCTION(BlueprintImplementableEvent) void OnOwnerControlRegained();
```

蓄力示例（蓝图）：OnAvatarSwitchOut 返回 ContinueOnField；在 OnOwnerControlLost 里释放已蓄的力。由于补发了真实释放，WaitInputRelease 也会触发；两种写法蓝图可任选其一。

## 留场与切回状态

- **Off_Field_State**：资产 `GE_OffField`，无限时。
  - 授予 `State.OffField`（新标签）与现有的 `Restriction.ImmuneDamage`；
  - 用 Immunity 组件免疫带 `Effect.Damage` 资产标签的 GE。开工重核现有伤害 GE 的资产标签，没有则补上。
  - MeleeTraceComponent 在收集命中目标时跳过 ASC 拥有 `State.OffField` 的角色，这样不会产生命中事件、Cue 或受击反应。
- **Return_Pending_State**：对 ASC 加 loose tag `State.SwitchReturnPending`（新标签）。
  - GA 基类把它加入激活阻止条件，即 `DoesAbilitySatisfyTagRequirements` 中统一追加；
  - CMC 的 `IsMovementBlockedByTag` 增加该标签。
  - 能力激活因标签失败后，开工重核现有 NotifyAbilityFailed 排队条件是否覆盖"标签阻止"；若只覆盖组阻塞，则把该标签加入可排队的失败原因，使缓冲窗口内的按下在标签移除时重试一次（复用组释放唤醒的同一路径）。
- 镜头：Possess 后 PlayerCameraManager 的 ViewTarget 跟随新 Pawn（原生）。开工重核项目相机是否另有混合，保持其现有行为。

## 进场与退场能力

```cpp
UCLASS(Abstract, Blueprintable)
class UGGYGOSquadTransitionAbility : public UGGYGOGameplayAbility
{
    UPROPERTY(EditDefaultsOnly) TObjectPtr<UAnimMontage> TransitionMontage;
    // ActivateAbilityBody：播放 Montage（项目 Montage Task），结束或被打断时 EndAbility
};
```

- 子类配置 AbilityTriggers 为对应 GameplayEvent；AvatarExitPolicy 不适用。
- 进场能力在 Active 角色上执行，是否阻止其它能力由子类的 ActivationOwnedTags 与 TagRelationshipMapping 决定。
- `SendGameplayEventToActor` 的返回值（激活数）决定是否等待。

## 网络

- Squad 所在 Actor 与现有切换入口在开工时重核。若没有 Server RPC，就在 Squad 上新增 `ServerRequestSwitchToSlot(int32)`（Reliable，WithValidation 只检查索引范围），由客户端输入或蓝图调用。
- 服务器执行全部流程。客户端 OnRep_ActiveSlotIndex 只做 UI 与本地输入重绑（沿用现有逻辑）。
- 留场队员没有 Controller，其能力在服务器执行。LocalPredicted 能力在失去控制后由服务器继续执行，客户端只表现。开工时用联机测试确认预测键在 UnPossess 后的行为不产生纠正抖动；如有，在换出时对 ContinueOnField 的能力不做额外处理，只记录现象交用户判断。

## Error Handling

- 切换目标无效：拒绝并诊断（槽位、原因）。
- GE_OffField 未配置：拒绝进入留场，改为直接退场并诊断"缺少 OffField GE 配置"。这是显式配置缺失的明确失败，不静默放行受击。
- 退场能力超时：退场能力自身负责结束；Squad 不另设计时器。

## Testing Strategy

- 自动化测试使用测试编队（两到三名使用测试 GA 的队员），覆盖 Requirement 7.2 的每一项。
- 测试 GA：
  - 一个返回 ContinueOnField 的长时能力；
  - 一个默认 Cancel 的能力；
  - 一个记录 OnOwnerControlLost／Regained 的蓄力能力；
  - 测试用进场与退场能力。
- PIE：使用实际编队资产。若只有一名可用队员，则用测试 Experience 配置两名队员。
- 联机：listen server + 1 客户端，客户端发起切换。

## 风险

- 现有 7 个 GA 资产默认 Cancel，上线后行为与现在一致，直到设计者把具体技能改为 ContinueOnField。这一点在活动记录中提示用户。
- 留场队员没有 Controller，若某能力依赖 PlayerController（例如瞄准方向），蓝图需要在 OnOwnerControlLost 中处理。在 GA 基类注释中写明。

## 实现差异（2026-11-03）

- **Off_Field 不用 GE 资产。** Squad 在服务器上施加 loose tag：`State.OffField`（TagOnly 复制）与 `Gameplay.Damage.Immunity`（不复制，伤害只在服务器结算）。现有伤害只有 PlayerCombo 与 BossMelee 两条路径，都经 MeleeTrace 命中回调；MeleeTrace 跳过 OffField 目标（不记入窗口去重表），因而没有命中事件、伤害 GE、Cue 或受击。HealthSet 已对 Immunity 清零 Damage／PoiseDamage。不需要 Editor，也就没有"GE_OffField 未配置"的失败分支。之后若出现不经 MeleeTrace 的伤害源，其 GE 的资产 Cue 仍会播放，需要另行处理。
- **Return_Pending 只拦输入发起的激活。** GA::CanActivateAbility 在父类检查之后，若 ASC 有 `State.SwitchReturnPending` 且该 Spec 正处于输入缓冲的 Try 内（`ASC::IsAbilityInputActivationAttempt`），返回失败并加 `Ability.ActivateFail.SwitchReturnPending`。事件触发（受击、死亡）、OnSpawn 和续放能力自身发起的激活不受影响。对仍在运行的续放能力，按键照常送入（`AbilitySpecInputPressed`），由能力在 OnOwnerControlRegained 后自行决定。输入缓冲认领该失败并登记重试许可；标签可能经复制移除、没有同步回调，所以由 ProcessAbilityInput 入口发现标签已移除后唤醒一次（与组释放同一路径）。CMC 的 `IsMovementBlockedByTag` 同样读该标签。
- **不可取消的 Cancel 决定。** 先向旧队员全部活动能力取得决定，若某个 Cancel 决定的能力不可取消，整次切换在任何取消之前拒绝（Reason=UncancelableAbility）。退场中切回而退场能力不可取消时同样拒绝（TargetExitNotCancelable）。这保持旧的"不可取消动作期间不能换人"。
- **留场移动。** 无 Controller 时原生 CMC 只在 `bRunPhysicsWithNoController` 或动画 RootMotion 时执行移动；项目动作位移是 RootMotionSource，所以 Squad 在施加 OffField 时打开该开关、解除时恢复原值。
- **控制丢失通知在解除附身前。** 顺序为：取得决定 → 登记续放、取消其余 → 补发释放（ReleaseHeldInputForControlLoss）→ OnOwnerControlLost（此时 Controller 仍可读）→ Hero ReleasePlayerInput → UnPossess → Possess 新队员 → 新队员进场或切回处理 → 旧队员 OffField 并留场或退场 → 广播。
- **退场能力的识别。** `SendGameplayEvent` 只返回激活数，Squad 在发事件期间临时订阅 ASC 的 `AbilityActivatedCallbacks`，记录这次事件同步激活且仍在执行的 Spec，等待它们结束。
- **进退场能力默认 ServerInitiated。** Squad 在服务器发事件，换下的队员不是本地控制，LocalPredicted 能力会被 GAS 以网络原因拒绝。
- **切换来源。** `SwitchToSlot(SlotIndex, Source = Script)`；`ServerRequestSwitchToSlot` 以 PlayerRequest 调用；`ServerRequestSwitchToAdjacentSlot(±1)` 由服务器从出战序号循环找相邻可出战位置，同样以 PlayerRequest 调用。玩家键位归 `AGGYGOPlayerController`（`IMC_Squad`，默认 Z 上一个、C 下一个，Started 触发），不放在 Hero 输入会话里：换人会同步退役旧 Pawn 的会话，而 Controller 跨 Pawn 存在。目前没有死亡自动切换，DeathAutoSwitch 只是枚举值。注册首位时的自动 SwitchToSlot(0) 也会向首位发 SwitchIn。
- **队员状态不复制。** `GetMemberState` 只在服务器有意义。
- **碰撞随角色复制（收尾修正）。** 引擎的 `bActorEnableCollision` 不复制；只在服务器关闭时，客户端仍有待命队员的胶囊，本地预测移动会撞上看不见的队员。Squad 改用 `AGGYGOCharacterBase::SetReplicatedActorEnableCollision`：服务器设置复制属性并立即应用，客户端在 OnRep 应用同一值。隐藏走引擎复制的 `bHidden`。
- **待命停骨架更新（收尾修正）。** 服务器上从未附身的队员没有 Controller，PawnExtension 停在 Spawned，CMC 没有 MovementSet；ACharacter 的 Mesh 隐藏时仍 AlwaysTickPoseAndRefreshBones，动画读到未初始化的移动配置并报 Error。`DeactivateSlot` 置 Mesh `bNoSkeletonUpdate=true`，`ActivateSlot`（在 Possess 之后）恢复。不关组件 Tick，因为开局登记早于 BeginPlay 时，注册会按 `bStartWithTickEnabled` 重新打开 Tick。只在服务器设置，客户端动画不受影响。
- **换人相机准入（Camera 侧收尾修正）。** 新 Pawn 被附身后 Hero 再次调 `ActivateCameraEvaluation`；管理器 Running 时允许准入 Controller 当前附身的 Pawn 替换准入来源，按首次准入同一流程校验并求值。
- **待命队员的相关性。** 按引擎 `APawn::IsNetRelevantFor`（当前未启用 Iris），隐藏、无碰撞且不属于观察者的 Pawn 不复制。初始待命队员 Owner 是原 Controller，对其客户端相关（隐藏、无碰撞）；换下后 UnPossess 清空 Owner，变为待命后按该规则不再相关，客户端副本会被销毁、切回时重新复制，客户端 Slot 随之释放并重新绑定。联机测试按"不存在或隐藏且无碰撞"判定客户端上的待命队员，没有单独断言副本被销毁。
- **测试夹具限制。** 未开局私有世界中 CMC 不订阅本地 ASC（只在 BeginPlay 订阅），locomotion 阻止只能在 PIE 验证；该世界没有消息路由，留场"技能照常结算"用不破韧的 PoiseDamage 核对。
