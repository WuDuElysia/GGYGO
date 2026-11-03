# Implementation Plan: abilitysystem-input-request

## Overview

整改第 2 步。执行规则与命令同第 1 步（见 `../abilitysystem-redundancy-cleanup/tasks.md` 的 Overview），输出目录为 `Saved/Kiro/abilitysystem-input-request/`（Before/、before_manifest.tsv、Patches/、after_summary.tsv、make_patches.py）。批次 1 中与第 1 步同批推进，额度解决前只改源码。

## Tasks

- [x] 0. 开工重核
  - `QueueAbilityInputRetry` 公开包装不是 UFUNCTION，生产与测试都无调用方
  - `ReceiveAbilityInputRequest`（含 Prune）与 `EndAbilityInputRequest` 只改 ASC 输入表与 `Spec->InputPressed`，失败只写日志，无外调；据此删除 Hero 返回后重验
  - 现状差异：`InitAbilityActorInfo` 原先只在 Avatar 变化时清空输入，Owner 变化不清空；单一失效方式要求两者都清空，已补上
  - _Requirements: 1.6, 2.6_

- [x] 1. ASC 输入记录收敛（源码，未编译）
  - [x] 1.1 Request_Record 与 Edge 删除 Owner／Avatar／World 快照；Record 增加 Source；Receive 增加来源参数（默认无来源），既有身份复核时比较来源
    - _Requirements: 2.1, 2.5_
  - [x] 1.2 具名谓词 `IsAbilityInputActorInfoUsable`、`RequestMatchesSpec`、`IsBeforeDeadline` 取代 `IsAbilityInputContextCurrent`／`IsAbilityInputRequestCurrent`；ProcessAbilityInput 入口查一次 ActorInfo（不可用即清空返回），外调后只核 Revision 与输入阻断
    - _Requirements: 2.2, 2.3_
  - [x] 1.3 删除 Revision／Serial 用尽分支、排队序号重排、`ClearAbilityInput` 的 Revision 用尽判断；删除公开 `QueueAbilityInputRetry` 包装，内部函数改名为私有 `QueueAbilityInputRetry`
    - _Requirements: 2.4, 2.6_
  - [x] 1.4 新增 `EndAbilityInputRequestsFromSource`
    - _Requirements: 2.5_
  - [x] 1.5 Outcome 已只有四项；Reason 删除 InvalidEndKind、SerialExhausted、RevisionExhausted
    - _Requirements: 3.1, 3.2_

- [x] 2. Hero 输入结构收敛（源码，未编译）
  - [x] 2.1 删除 FAbilityInputObservation，`FAbilityActionBinding` 直接保存 `bPressed`、`CurrentRequest`（身份、Tag、截止、Token）和已报原因
    - _Requirements: 1.1_
  - [x] 2.2 删除 FAbilityInputAssociation，会话直接保存 `AssociatedResource` 与 `AssociatedSubscription`；关联变化、会话退役、Closing／Released 通知都走 `RetireSessionAbilityRequests` → `EndAbilityInputRequestsFromSource`
    - _Requirements: 1.2, 1.5_
  - [x] 2.3 Triggered／Released 按 design 主流程重写；Hero 侧拒绝按动作与原因只报一次
    - _Requirements: 1.3, 1.4, 1.6, 3.3_

- [x] 3. 测试适配
  - [x] 3.1 新增 `GGYGO.AbilitySystem.InputRequest.EndRequestsFromSource`：按来源结束只退役该来源，空来源不结束任何请求
    - _Requirements: 2.5_
  - [x] 3.2 PlayerCombo 夹具改走真实输入：复用 `FGGYGOInputTestFixture`（J 键映射攻击动作，`PlayerInput::InputKey`＋PC `TickPlayerInput`），同步完成 EnhancedInput 帧末映射重建与广播；Avatar 在 Host 绑定前组装；测试 Pawn 实现 `IAbilitySystemInterface`。准入拒绝用例保留受控 Try
    - _Requirements: 4.1-4.6, 5.2_
  - [x] 3.3 Input／Admission 既有测试未断言已删除的内部结构或原因值（编译通过；Admission.GroupLifecycle 的 reason=14 早于本步，归第 4 步）
    - _Requirements: 4.1-4.6_

- [x] 4. 首击不等移动键（用户 11-03 选 B）
  - 移动来源尚无物理证明时，`ValidateStepStartInputReadiness` 把 AwaitingPhysicalProof 记为零轴 Completed 事实，按当前朝向起段；WaitComboInput TargetData 与 CMC 段首事实校验接受该状态；移动执行仍只接受 Held
  - _Requirements: 4.2, 4.4, 5.3_

- [ ] 5. 检查点：编译、测试、PIE
  - [x] 编译与 NullRHI 测试：见 `Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/`（与第 1 步合批）。Input、PlayerCombo、InputRequest 用例通过；`ActivationCommitAndEndReentry`、`Admission.GroupLifecycle` 归第 4 步；`MovementOrigin.NativeBirthFirstDigitalPress` 需原生窗口，NullRHI 下不可运行
  - [ ] PlayerCombo 生产冒烟（真实 RHI＋L_Movement_Test，需另批额度）或用户手动 PIE：首击不碰移动键直接起段、连段缓冲、占用后缓冲生效、超窗不生效、按住不重复
  - _Requirements: 5.1-5.3_

- [x] 6. 更新活动记录
  - 已写入状态与证据路径；真实设备手感待用户试玩
  - _Requirements: 5.4, 5.5_
