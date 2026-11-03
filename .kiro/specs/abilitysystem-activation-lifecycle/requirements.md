# Requirements Document

## Introduction

本 spec 是整改的第 4 步，总索引见 [活动记录](../../../AAADocs/需求文档/refactor_and_squad_switch.md)，对应以下问题：

- **问题 1**：GA 与 ASC 自建了一套激活／终止状态机，与 GAS 原生寿命并行。
- **问题 8**：Montage 播放有五层包装、三套身份，GA 终止还会捕获播放所有权。
- **问题 5 的其余部分**：以 Task 寿命作为段寿命。
- **问题 10 的 GA 部分**：主流程中的 *ForTest 钩子。
- **由第 1 步收窄时移入**：问题 9（Boss 改用共享 Montage 动作资源）、问题 10 的 ASC 组准入测试日志、问题 11 的 CMC 两参 BeginMontageActionMotion 合并。见 Requirement 10。

目标：
- 每次激活只有一个身份，由一个原生时点签发；
- 结束和取消直接走原生 EndAbility／CancelAbility；
- BT 等待改用原生 OnAbilityEnded；
- 一次 Montage 播放只有一个身份；
- 段内回调靠资源释放时解绑来避免作用到后继，不再逐层认证。

依赖：第 3 步 fx-montage-publication-ownership 已验收。第 3 步完成后，FX 关闭已不依赖激活退休。

不在本 spec 内：
- 组准入规则（优先级、互斥、排队）保持不变；
- 换人退出能力的行为保持"换人取消能力"，第 6 步改为续放。

## Glossary

- **Activation_Handle**：`FGGYGOAbilityActivationHandle`，一次激活的身份。保留类型与 HasActivation、HasSameActivation、GetResourceIdentity 语义，内部只含签发者 ASC、能力实例、Spec 句柄、激活预测键、ActorInfo 分配和一个递增序号。
- **Issue_Point**：签发 Activation_Handle 的唯一时点，即原生 PreActivate 内对 ASC::NotifyAbilityActivated 的调用。
- **Termination_Machine**：将被删除的自建终止机制：
  - `FOriginalTerminationRecord` 及其 14 个阶段标志和 2 个计数；
  - `FScopedControlledActivationEnd`、`FScopedAbilityActivationCall`；
  - `NativeCleanupActivation`；
  - ASC 的 `FControlledAbilityActivationCall` 调用栈、激活评估令牌与查询深度；
  - `TryActivateAbilityWithTerminationBoundary`、`OnAbilityTerminationCompleted`；
  - GA 的 RetiredActivations 参数链。
- **Playback_Identity**：一次 Montage 播放的身份 = MontageGuard 报告的本次调用创建的 MontageInstanceId + Activation_Handle。
- **Step_Resources**：PlayerCombo 一段持有的 Task、位移、Trace 窗口、FX、Watchdog（`FStepMotionResources`）。

## Requirements

### Requirement 1: 单一激活身份

**User Story:** 作为能力作者，我希望每次激活只有一个身份、只在一个地方签发，回调里只需比较它是否等于当前激活。

#### Acceptance Criteria

1. WHEN 原生激活到达 Issue_Point, THE GA SHALL 签发新的 Activation_Handle 并设为当前激活；THE ASC SHALL NOT 再维护受控调用栈、评估令牌或本地见证。
2. THE GA SHALL 提供 `IsActivationCurrent(Handle)`：仅当 Handle 等于当前激活且能力处于 Active 时为真。
3. WHEN 能力的原生 EndAbility 完成, THE GA SHALL 退役当前激活；之后任何持有旧 Handle 的回调判断为非当前。
4. THE Activation_Handle SHALL 能区分 ServerOnly 能力的连续激活（这类能力的激活预测键为 0），靠递增序号区分。
5. THE GA SHALL 在 IsDataValid 中要求项目能力为 Instanced 且 bRetriggerInstancedAbility 为假；THE ASC SHALL NOT 在每次激活时重复检查。

### Requirement 2: 结束与取消走原生

**User Story:** 作为能力作者，我希望请求结束或取消时直接调用原生接口，ScopeLock 期间的延迟由引擎处理。

#### Acceptance Criteria

1. WHEN 调用 RequestAbilityEnd(Original, bReplicate, bWasCancelled), THE GA SHALL 在 Original 为当前激活时调用一次原生 EndAbility；否则返回 NotCurrent，不调用。
2. WHEN 调用 RequestAbilityCancel(Original, bReplicate), THE GA SHALL 在 Original 为当前激活且 CanBeCanceled 时调用一次原生 CancelAbility；不可取消时返回 NotCancelable。
3. THE `FGGYGOAbilityTerminationResult` SHALL 只表达 Accepted、NotCurrent、NotCancelable 三种结果。
4. THE GA SHALL 依赖原生 EndAbility／CancelAbility 在 ScopeLockCount>0 时的延迟执行（UE_5.8 GameplayAbility.cpp:745-748、806-809），SHALL NOT 自建延迟或续接机制。
5. THE GA SHALL 删除全部 Termination_Machine。
6. THE GA SHALL 保留 `CleanupAbilityResourcesForTermination` 作为子类释放自有资源的唯一钩子，在原生 EndAbility 内调用一次，参数只含被结束的 Activation_Handle 与 bWasCancelled。

### Requirement 3: BT 等待原生结束事件

#### Acceptance Criteria

1. THE BTTask_GGYGOActivateAbility SHALL 在调用原生 TryActivateAbility 前订阅 ASC::OnAbilityEnded，按 Spec 句柄匹配本次能力的结束。
2. WHEN 能力在 TryActivateAbility 内同步结束, THE BTTask SHALL 用本地标志接住该结束，Try 返回后直接以 Succeeded（未取消）或 Failed（被取消）完成。
3. WHEN TryActivateAbility 返回 false, THE BTTask SHALL 以 Failed 完成并解除订阅。
4. WHEN BT Abort, THE BTTask SHALL 只解除订阅，SHALL NOT 取消能力。
5. THE Editor 工具 GGYGOPlayerActionObservation 与相关测试 SHALL 改用 OnAbilityEnded。

### Requirement 4: 单一播放入口与身份

**User Story:** 作为动画与能力作者，我希望一次 Montage 播放只有一个入口、一个身份。

#### Acceptance Criteria

1. THE ASC SHALL 只提供一个项目 Montage 播放入口，取代 PlayMontageWithGuard、ExecuteMontagePlayWithGuard、TryPlayMontageWithOwnership；原生 PlayMontage 覆盖转到同一实现。
2. THE ASC 播放所有权核对 SHALL 只比较：LocalAnimMontageInfo 中的 AnimatingAbility、AnimMontage、PlayInstanceId 与 Playback_Identity 一致，且能力当前激活等于记录的 Activation_Handle；SHALL NOT 捕获或比较 ActorInfo 快照。
3. THE MontageGuardAnimInstance SHALL 保留：识别本次调用创建的 Montage 实例；ActionPoseContract。删除与 ASC 播放证明重复的部分。
4. THE GA SHALL NOT 在终止时捕获播放所有权；播放随 Task 结束按原生规则停止。
5. WHEN 开工重核发现没有动画蓝图使用非 Guard 的 AnimInstance, THE ASC SHALL 删除 PlayMontage 中的 Legacy 分支；否则保留并写明消费者。
6. THE Montage Task SHALL 只保存 Playback_Identity 与回调注册；删除 8 个 Activated* 弱引用中只用于重复认证的部分，保留确有消费的。

### Requirement 5: 段寿命等于 Task 寿命

**User Story:** 作为战斗作者，我希望换段时旧段的所有回调都随资源释放而解绑，回调里不再逐层认证。

#### Acceptance Criteria

1. WHEN 释放 Step_Resources, THE PlayerCombo SHALL 依次解绑：Task 原生回调、CMC 位移完成与失败观察、Trace 命中订阅、FX 本地启动票据，并清除 Watchdog。
2. THE PlayerCombo 回调 SHALL 只校验所属的 Step_Resources 是否仍为当前段；跨帧可能延迟到达且未被解绑的回调额外比较 StepToken。
3. THE Montage Task 派发谓词 SHALL NOT 每次调用 ASC 播放所有权核对；所有权变化（被别的播放替换）由原生 BlendOut／Interrupted 事件通知。
4. THE BossMelee SHALL 采用同样的规则。

### Requirement 6: 输入失败排队与 Initial 路由

#### Acceptance Criteria

1. THE ASC SHALL 用"ProcessAbilityInput 在原生 Try 期间设置的当前输入尝试（Spec 句柄 + 来源请求）"取代评估令牌链；NotifyAbilityFailed 只在 Spec 句柄匹配当前输入尝试时记录排队重试。
2. THE Initial 输入路由（InitialInputRoute）SHALL 改为以 Activation_Handle 判断来源；在该激活的原生 EndAbility 期间仍可发送 TargetDataCancelled。
3. THE 分段输入请求（StepInputRequest）SHALL 改为以 Activation_Handle 判断来源。

### Requirement 7: 测试钩子

#### Acceptance Criteria

1. THE GA SHALL 删除 ObserveAbilityActivationEntryForTest、ObserveAbilityActivationReturnForTest、ObserveAbilityEndEntryForTest 及其调用。
2. THE 依赖这些钩子的测试 SHALL 改用测试子类覆盖 ActivateAbilityBody／CleanupAbilityResourcesForTermination，或订阅 OnAbilityEnded。

### Requirement 8: 不回退的行为

#### Acceptance Criteria

1. THE 系统 SHALL 保持旧激活的迟到回调不作用到后继激活（含同帧结束后重新激活）。
2. THE 系统 SHALL 保持旧调用栈不清理后继的资源（Task、位移、Trace 窗口、FX、AnimatingAbility）。
3. THE 系统 SHALL 保持连段段序、纠正重放复用原 basis、同段纠正不重新采样。
4. THE 系统 SHALL 保持 Initial 输入不可提供时发送 Reliable TargetDataCancelled 并精准清理。
5. THE 系统 SHALL 保持 BT Abort 不取消能力。
6. THE 系统 SHALL 保持换人时取消旧角色能力（第 6 步才改为续放）。
7. THE 系统 SHALL 保持组准入、优先级与组释放唤醒排队输入的行为。

### Requirement 9: 验收

#### Acceptance Criteria

1. WHEN 本 spec 全部任务完成, THE 作者 SHALL 编译 GGYGOEditor 并通过。
2. THE 作者 SHALL 运行并通过以下测试：
   - GGYGO.AbilitySystem（全部）
   - GGYGO.BossAI
   - GGYGO.Animation.MontageGuard
   - GGYGO.Combat
   - GGYGO.Combatants
   - GGYGO.Teams.SquadSwitch
   - GGYGO.Editor.Animation
   - GGYGO.Movement.ActionMotion
3. THE 作者 SHALL 保留并通过 ABA 外部契约测试：结束后立即重新激活时旧回调无效、旧栈不清后继资源；内部 serial、receipt、phase 断言随机制删除。
4. THE 作者 SHALL 在 PIE 中验证：三段普攻、技能、TurnBack、Boss 招式、Boss BT 连续出招。
5. THE 作者 SHALL 做最小联机验证：预测连段在客户端与服务器一致；服务器拒绝后客户端纠正重放。
6. WHEN 验收通过, THE 作者 SHALL 更新活动记录。

### Requirement 10: 由第 1 步移入的收敛

**User Story:** 作为战斗作者，我希望玩家和 Boss 的 Montage 动作资源只有一套实现，位移入口没有仅默认参数不同的重载，主流程里没有测试日志。

移入原因：本 spec 重写共享资源结构、Boss 的身份／回调模型与 ASC 激活段；第 1 步窗口内 ASC.cpp 受保护，Boss 测试依赖其 protected 接口与精确日志。

#### Acceptance Criteria

1. THE BossMelee SHALL 使用 `FGGYGOMontageActionResources` 持有 Task、CMC 位移、Trace 窗口、Watchdog 与双完成事实，删除 `FOriginalMeleeResources` 中与之重复的字段和起止逻辑。
2. WHERE Boss 使用 ActionMotionProfile 而非 Montage 原生位移, THE 共享资源 SHALL 提供基于 Profile 的位移起止入口（`BeginProfileMotion`），由 `ReleaseMotion` 统一释放两种位移；行为与 BossMelee 现有 Profile 路径一致。
3. THE 共享资源的 Watchdog SHALL 支持 Boss 现有的固定超时（实际播放时长＋固定宽限），与 PlayerCombo 按 Mesh 位置与宽限计算的方式并存。
4. THE BossMelee SHALL 保留其特有的 Mesh Tick 选项保存与恢复，以及 Tick 前置依赖的添加与移除。
5. THE BossMelee 的外部行为 SHALL 保持不变：伤害、PoiseDamage、命中 Cue、Watchdog 超时结束、Montage 与位移双完成后才结束。
6. THE Boss 测试 SHALL 改为经真实入口断言外部结果：`GGYGOBossMeleeLifecycleTestAbility.h` 使用的 PrepareOriginalMeleeMesh、BeginOriginalMeleeMotion、HasOriginalMeleeMeshResource、GetOriginalMeleeResourceActivation 随实现迁移；依赖精确日志（如"BossMelee [%s] 原动作在 [Motion] 失败：…"、"原动作在 [Montage Task] 失败"）的断言改到新诊断，不降低断言。
7. THE CMC 与 `FGGYGOActionMotionExecution` SHALL 把不带 Facing 的 BeginMontageActionMotion 合并到带 Facing 的版本，调用方显式传入默认 Facing；共享资源的两个 BeginMotion 重载同样合并。
8. THE ASC FinalizeAbilityGroupAdmission SHALL 删除主流程中的 WITH_DEV_AUTOMATION_TESTS 日志块；IF 开工重核发现有测试依赖这些日志, THEN 测试改为断言组准入的外部结果（被拒绝、被取消、准入成功）。
