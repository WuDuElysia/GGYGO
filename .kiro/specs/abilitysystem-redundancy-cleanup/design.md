# Design Document

## Overview

本 spec 只删除和收敛，不改玩法。依据是 2026-11-02 静态审核；开工重核结果和实现中的修订已写入本文，行号以实现前基线为准。

实际写集（统筹 2026-11-02 授权的收窄写集）：
- `AAADocs/Architecture/CodeConventions.md`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.{h,cpp}`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp`（只动 BuildHitEffectPayload）
- `Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp`
- `Source/GGYGO/AI/Boss/BehaviorTree/BTTask_GGYGOActivateAbility.cpp`、`BTTask_GGYGOChooseBossAction.cpp`
- `Source/GGYGO/AI/Boss/GGYGOBossAIController.cpp`
- `Source/GGYGO/Animation/Runtime/GGYGOMontageGuardAnimInstance.h`（注释）

批次 1（用户让 Kiro 按原计划自主推进）新增写集：`GGYGOBossState.{h,cpp}`、`GGYGOBossAIController.h`（注释）、`GGYGOPlayerComboLifecycleTest.cpp`、`GGYGOBossSelectionTest.cpp`、`GGYGOBossEncounterBehaviorTreeTest.cpp`、`GGYGOHitSemanticsTest.cpp`。

未改：`GGYGOMontageActionResources.{h,cpp}`（Boss 改用共享资源在第 4 步）、`GGYGOBossMeleeAbility.h`、`GGYGOBossMeleeEndReentryTest.cpp`、`GGYGOAbilitySystemComponent.cpp`。

## 现状与问题（开工重核）

### 运行期重复校验

`ValidateComboConfiguration`（PlayerCombo.cpp:556-660）对全部段重建动作源绑定，并解析窗口、通知、FX、Trace。调用点：

| 调用点 | 频率 | 处理 |
| --- | --- | --- |
| IsDataValid | 编辑器 | 保留完整校验（纯解析） |
| CanActivateAbilityAdditional | 每次 CanActivate 查询 | 读授予期缓存 |
| NativeOnAbilityFailedToActivate | 每次失败 | 读授予期缓存，失败时按类别诊断一次 |
| ActivateAbilityBody | 每次激活 | 读授予期缓存并存为本次快照 |
| StartStep 内逐段再解析（约 1597-1653） | 每段 | 读本次快照 |
| HandleMeleeHit 伤害依赖与段数值检查 | 每次命中 | 删除，改用快照的 GE 与模式 |

重核发现的约束及处理：
- 测试在 GiveAbility 之后用 ConfigureStepsForTest、UseSingleStepForTest、AddMovementPointForTest、AddHitWindowForTest、ConfigureRuntimeHitDamage 修改主实例配置。处理：这些 helper 只在未激活时改，并先调用 `InvalidatePreparedConfiguration()`，对应生产中"改配置的一方负责失效"。
- `ValidateComboConfiguration` 是公开函数，测试直接调用并匹配错误文字（"TraceShape"、"历史存值"、"MotionSlotName"）。处理：它只调纯解析，不读写缓存。
- 命中时可变的输入只剩两类：BP_EditSpecValues 可以替换 Def；AbilitySpec 的 SetByCaller 可能与伤害键冲突。共享 GE 在准入时解析，弱引用失效即视为缓存失效。RuntimeHit 的 MissingMultiplier 与运行期 InvalidRequiredGE 靠激活中途改作者配置构造，生产不可达，改为准入期用例。

### 无外调重验

- StartStep 释放旧段前后四次相同重验。`ClearWatchdog` 只调 ClearTimer，且 `ReleaseStepMotion` 已清 Watchdog；`ReleaseTraceWindow` 只改 Trace 组件内部状态，析构的命中回调只有弱捕获；`ReleaseStepFX` 会执行失败委托，可同步结束激活；`ReleaseStepMotion` 结束原 Task 与 CMC 位移，会回调观察者。
- 两次 `ASC::CurrentMontageSetNextSectionName` 之后各一次重验。UE 5.8 实现只调 `Montage_SetNextSection`，再 `AnimMontage_UpdateReplicatedData` 或发 Server RPC，项目 ASC 未覆盖，无本地回调。
- `StepTokenCounter == MAX_uint64` 判断：64 位单调计数，删除。`StepSyncRevision == MAX_int32` 与 SourceRequestId 0..65535 对应窄网络字段，保留。
- HandleMeleeHit 只在三处真实外调后重验（基线 2477、2482、2532、2574 行），已满足 R4.3。
- BuildHitEffectPayload：`MakeEffectContext`、`ApplyAbilityTagsToGameplayEffectSpec` 是 C++ 虚函数，项目覆盖实现不销毁 Source／Target，`HasOriginalObjects` 重验可删。测试子类覆盖 ApplyAbilityTags 并使 Spec 失效，断言 "RequiredSpecInvalidAfterApplyAbilityTags"，所以 `HasValidRequiredSpec` 检查全部保留。

### Boss 与选招

- BossMelee Body：Commit 前 `ValidateMeleeConfiguration`，Commit 后再 `ResolveMeleeConfiguration`；两者是同一解析。配置属性为 EditDefaultsOnly＋BlueprintReadOnly，BP 与 Commit 不会改写。
- ActionSet 全表校验在一个选招周期内执行五次：SelectAction、StoreActionSelection、ConsumeActionSelection、ChooseBossAction、ActivateAbility BT。ActionSet 是静态数据资产。

## Architecture

### 预备配置（授予期缓存＋激活快照）

```
ValidateComboConfiguration(OutError)                 // 纯解析，IsDataValid 与测试使用
  return PrepareComboSteps(OutError).IsValid()

FindOrPrepareConfiguration(OutError, bOutDamageFailure) const
  if PreparedConfiguration 有效 且 IsDamageEffectCurrent: return 它
  ValidateDamageEffectDependency      失败 → 伤害类
  Prepared = PrepareComboSteps        失败 → 段配置类
  ValidateGGYGOComboDamageModes(..., Prepared->DamageMode)  失败 → 伤害类
  Prepared->DamageEffect = 弱引用 GE；bHasDamageEffect
  if IsInstantiated(): PreparedConfiguration = Prepared   // CDO 不缓存
  return Prepared

CanActivateAbilityAdditional → FindOrPrepareConfiguration().IsValid()
NativeOnAbilityFailedToActivate → 失败时按类别记"激活失败时…"一次
ActivateAbilityBody
  Super::ActivateAbilityBody          // BP 回调改不了 EditDefaultsOnly 配置，之后不复验
  PreparedActivation = FindOrPrepareConfiguration() 或按类别记"提交前…"并 End
  … Commit、Mesh Tick、Input Task（不变）
CleanupAbilityResourcesForTermination
  PreparedActivation.Reset()
```

- 缓存位置：`mutable TSharedPtr<const FPreparedComboConfiguration> PreparedConfiguration`，只由 FindOrPrepareConfiguration 写入。实例随授予创建、随移除销毁，因此不另挂 OnRemoveAbility；实例在编辑器里没有 PostEditChangeProperty 入口，也不挂。
- CDO 不缓存：`CanActivateAbilityByHandle` 在 CDO 上做纯查询，CDO 跨 PIE 存活，缓存会在编辑器改 Montage/GE 后给出旧结果。
- GE 弱引用：`TWeakObjectPtr<UClass>` 不延长类生命周期；类卸载或带 `CLASS_NewerVersionExists`（编辑器重编译）时视为失效，下次准入重新解析，命中时中止原激活。放弃 TStrongObjectPtr（跨线程析构风险）和 mutable UPROPERTY。
- 段数据：运行期仍读实时 `ComboSteps[i]` 的数值字段（伤害、Cue、PlayRate 等），不另做段配置快照；契约是作者配置只在未激活时改。
- 放弃的方案：每次激活解析（为迁就授予后改配置的夹具而保留完整 CanActivate 校验）。

私有类型（定义在 .cpp）：

```cpp
struct FPreparedComboStep
{
    FGGYGOActionMotionSourceBindingPtr MotionSource;   // 不可变共享绑定，段资源直接引用
    FGGYGOMontageNotifyDeclaration AttackDeclaration;
    FGGYGOMontageNotifyDeclaration MovementDeclaration;
    float MovementFloor;                               // 当前 Montage Main 真实末端
    FGGYGOMontageFXWindowDeclaration FXWindow;
    TArray<FGGYGOMontageWindowDeclaration> WindowDeclarations;
};
struct FPreparedComboConfiguration
{
    TArray<FPreparedComboStep> Steps;
    TWeakObjectPtr<UClass> DamageEffect;
    bool bHasDamageEffect = false;
    EGGYGOComboDamageMode DamageMode = NoGE;
    bool IsDamageEffectCurrent() const;                // 无 GE 恒真；否则类仍在且未被替换
};
```

- 成员 `TSharedPtr<const FPreparedComboConfiguration> PreparedActivation`。StartStep 本栈复制共享引用，外调期间终止清理释放成员也不影响本段读取。
- Initialize 的"资源未归还"检查与 Cleanup 的来源不匹配诊断都纳入 PreparedActivation。

### StartStep 三步

```
StartStep(Original, Index, Position, RequestId, bReplay, ReplayBasis*, EntryAttempt)
  ReadStepStartInputs(..., Inputs)   // 入场尝试、请求号、预备段、Facing 请求、basis、CMC、Socket、TraceShape
  ReleaseCurrentStep(Original)       // Trace（无外调）→ FX（外调，后重验）→ 位移（外调，后重验）
  BeginStep(..., Inputs)             // 段令牌、Task、窗口、通知、Ready、NextSection、位移、Watchdog
```

- `FStepStartInputs` 保存预备配置共享引用、段指针、`FGGYGOComboStep` 副本、CMC、basis 副本，只在三步之间传递，不跨外调借用入口内存。
- `ReleaseCurrentStep` 先在本栈持有旧段资源，再依次释放，保证 FX 释放针对原资源。
- 依赖当前 Mesh 资产的 FX Socket 与 TraceShape 核对留在运行期：换装后可能变化。

### 命中时的检查

```
Prepared = PreparedActivation
if !Prepared 或 !IsDamageEffectCurrent → Abort("ComboDamage: prepared-damage-effect-unavailable")
BuildHitEffectPayload(Prepared GE)              // 外调，之后重验原命中
if Spec 有效:
  if Spec.Def != 预备 GE 的 CDO → Abort("ComboDamage: returned-spec-definition-mismatch")
  按 Prepared->DamageMode 写 SetByCaller，并核对冲突键（不变）
```

删除 `ValidateDamageEffectDependency`、`ResolveGGYGOComboDamageMode`、`ValidateGGYGOComboStepDamage` 的命中时调用；后者无其它调用方，一并删除。段数值的有限／非负与模式匹配已在准入校验，作者配置不在激活中改。

### Boss 与选招

- BossMelee：Commit 前一次 `ResolveMeleeConfiguration` 写入 `Resources->MotionSource`；Commit 后只复核 Mesh／Trace／Socket／AnimInstance、播放速率与位移前置；删除重复的 `Resources->Montage` 赋值。
- BossMelee 不缓存配置，保留每次激活 Commit 前一次 Resolve：解析只在激活时发生一次，缓存收益可忽略。这是与原计划的有意差异。
- 选招：BossState::InitializeFromDefinition 在写入定义前遍历全部阶段，对非空 ActionSet 调 `ValidateConfiguration`，失败即诊断并返回 false（定义、形态与阶段标签都不写）。BT 取用的 ActionSet 都来自已采纳的定义。SelectAction、Store、Consume、两个 BT Task 都不做全表校验；ActivateAbility BT 删除紧随其后的冗余 `IsActionSourceCurrent`。
- BossSelectionTest：原 SelectAction(坏表) 用例改为 `GGYGO.BossAI.Selection.ActionSetValidatedOnAdoption`，坏表放在非初始阶段（测试内静态原生 Tag `State.Boss.Phase.GGYGOTests.Later`），断言拒绝采纳、诊断恰好一次、拒绝后仍能用合法定义采纳。Store／Consume 的行检查用例不变。

### 规范修订

在 CodeConventions 现有条款上原位改写：

| 条款 | 修改 |
| --- | --- |
| Busy／NotHeld 结果条 | 结果枚举只列真实消费者会分支的结果 |
| 外调条 | 正向清单，引擎函数按实现认定，重验须对应清单 |
| 同栈复用条 | 后置检查举证；有寿命与清理点的预备配置不属于未经失效管理的缓存 |
| 单一权威条之后 | 新增 ABA 原生寿命与身份合并 |
| 计数耗尽条 | 64 位不判耗尽，窄字段按宽度处理；预备配置代替"已校验"标志 |
| serial／Origin 合并段 | 同一拥有者同一寿命合并，其余分开 |
| "不以瘦身名义"之后 | 新增"应主动退役的模式" |

## Error Handling

- 预备配置失败：Body 以现有诊断拒绝激活；CanActivate 的纯查询不记日志，NativeOnAbilityFailedToActivate 在真实失败时诊断一次。
- StartStep 缺预备段：诊断"prepared step/Mesh/Trace/original World is invalid"并取消原激活。
- 命中时 Spec 被 BP 扩展替换或伤害键冲突：沿现有失败路径结束本次激活并诊断。

## Testing Strategy

- 夹具改法见 Requirement 11。Test_R3 的四类失败对应：
  - 13 例 PlayerCombo 夹具在 Initial 处被拒：来自 10-25 未提交的输入改动（首次请求必须来自真实 edge 并带移动评价 Token），夹具改走真实输入在第 2 步完成。
  - 8 例生产冒烟：Entry 地图选错；改用 L_Movement_Test 后（Test_R4），首段入场在等移动输入物理证明，测试把等待判为失败；OwnerSync 拒绝是之后 PIE 收尾的连带结果。见第 2 步任务 4。
  - TraceShape、RequiredTreeRejectsInvalidRoot：生产 Error 已声明为恰好一次的预期。
  - HitSemantics 距离专项：已改用带 GameInstance 的世界。
- 验证窗口需确认：`RestartFirstStepForTest` 在激活中直调 StartStep 读同一快照；RuntimeHit 各失败测试与 `RequiredSpecInvalidAfterApplyAbilityTags` 诊断；`ActionSetValidatedOnAdoption` 的预期日志。
- PIE 冒烟见 Requirement 10.3。

## 风险

- 作者配置只在未激活时改。PIE 运行中修改所引用的 Montage/GE 不会反映到已缓存的实例，需要重新授予（重开 PIE）。
- 本批次未编译。签名、访问权限与 TSharedPtr 转换已按阅读自审，最终以验证窗口的编译为准。
