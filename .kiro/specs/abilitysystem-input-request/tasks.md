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

- [ ] 5. 检查点：编译、测试、PIE（连段缓冲与要求 5.3 原文不一致，待用户决定；"过截止不重试"无测试；实体设备手感与 V4 的设备断连／外部失焦仍待用户，见下）
  - [x] 编译与 NullRHI 测试：见 `Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/`（与第 1 步合批）。Input、PlayerCombo、InputRequest 用例通过；`ActivationCommitAndEndReentry`、`Admission.GroupLifecycle` 归第 4 步；`MovementOrigin.NativeBirthFirstDigitalPress` 需原生窗口，NullRHI 下不可运行
  - [x] PlayerCombo 生产冒烟（真实 RHI＋L_Movement_Test）：2026-11-11 `GGYGO.AbilitySystem.PlayerCombo` 23 叶＋NativeBirth 共 24 项，Build_R2（Smoke_R2）与 Build_R3（Smoke_R3）两次都是 22 Success（其中 5 项只带引擎 CMC 步长 Warning）／2 契约性 Fail（PoseFailure×2，见 V2）。首击无移动键（Cold／零轴起段）、攻击接续点之后的连段接续、超窗拒绝（第三段攻击点前请求被拒且不挂起）、按住不重复均有生产证据。修正夹具：所有生产叶首按前等资源 Ready（进程首个 PIE 的 Pending 按下按契约被丢弃，旧夹具因此超时）。证据 [I08](../../../.agents/tasks/requirements-closeout/evidence/I08.md)。
  - [ ] 连段缓冲（要求 5.3 第一项，**需用户决定**）：5.3 原文是"连段缓冲输入在下一段生效"。当前 GA 不调用 `FGGYGOComboWindowState::Store`，攻击接续点（Normal01 在 0.275 s）之前的按下直接被拒、不存起来；冒烟证明的只是接续点之后按下，同一激活内 11～18 ms 接上下一段。HEAD 上就是这样，不是本批引入（台账 CR-1014-B1 已记 `Store` 无生产调用者）。选项：A 接受现状，把 5.3 改为"接续点后的按下在下一段生效，接续点前的按下不生效"；B 另立需求接回预输入（接续点前的按下存起来，开门后生效），玩家手感会变，需重跑冒烟。
  - [ ] 占用后缓冲（要求 5.3 第二项、4.1）：生产 PIE 到不了（只启用攻击一个能力，攻击自身连段走同一激活）。单元层已覆盖排队与重试：`Admission.GroupLifecycle`（Queued 组拒绝第二实例并报 `GroupOccupiedQueued`；`OnAbilityGroupFreed` 回调内重试成功）；`ProjectDiagnostics.Input.ActivationOrigin.QueuedFailureReleasesBlockerBeforeNotice`、`ProjectDiagnostics.Input.RetryIdentity.SameTimeReentrantPhysicalRequest`（真实 GroupFreed 后重试一次，重试带原有限截止时间）。"超过截止时间不再重试"**未验证**：没有任何测试叶把时间推过截止再断言不重试，只有代码路径（`GGYGOAbilityInputBuffer.cpp` 中 `IsBeforeDeadline` 为假时清空 `RetryableSpecHandles`，重试分发也先查 `IsBeforeDeadline`）。
    - [x] V1 Normal01 活尾：生产配置为单 NS、8 发射器全部 Once、t=0 一次 Burst，最长 Loop Duration 1.0 s，粒子寿命 ≤0.3 s；作者 FX End 在 1.6834 s。没有单元能活过作者 End，活尾分支在该配置下不存在；三次运行 9 次观察均 `NaturalRetiredBeforeEndUnits=1 TailDetachedUnits=0`。未人为续命。
    - [x] V2 两 PoseFailure：Build_R2 复跑结果与 R39b 相同，每叶两条关联诊断（Acquire／Poll 各一条 MontageTask.Pose，加同 Task 的 RequiredDependencyFailed），清理与自然后继断言通过。按既有测试契约保留未过滤 Error 与原 Fail。
    - [x] V3 R41 额外攻击：Build_R2 的 NewPress 叶通过，外来按键观察只见夹具自己的提交，没有复现，不追。
    - [x] V4 改键实际生效和持久化（自动化范围）：[V4i](../../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_KeySettings_V4i/return.json) 在同版 Build_R53 完成生产菜单 W→I、首按移动、异步存档、第二轮新对象磁盘加载、恢复默认和再次写盘；[V4h](../../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_KeySettings_V4h/return.json) 完成不改键的菜单返回与按住跨菜单后释放恢复。两原编辑器正常退出，保护归还。原 PC 软件桥与实体设备分证，设备断连和外部失焦的运行仍待。[先前失败及修复](../../../AAADocs/Coordination/Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-05-v4-改键验证过程)。复用真实 RHI、L_Movement_Test 和生产 Controller，先从宿主内读回全新隔离 UserDir 的 ProjectSavedDir，核该 SaveGames 入口原为空。选「移动 · 前进」，现场确认候选新键 I 未被原映射占用；实际点击菜单选键，原 Controller 回到 GameOnly 后再按下／松开。读取生产 `/Game/Input/Actions/IA_Move.IA_Move` 的已编译映射，按原装配身份核 Pawn 位移，证 W→I；需要跨帧保持时复用已存在的 Editor 原 PC.InputKey 桥，提交返回不作动作结果或物理设备证明。
      - 等实际 EnhancedInput 异步成功回调和隔离 `SaveGames/EnhancedInputUserSettings.sav` 后像（路径、大小、时间、SHA-256）再退 PIE；菜单提示只证明请求应用。
      - 同一 Editor 第二次 PIE 若能证新的 LocalPlayer、EnhancedInput 子系统和 Settings，且任何新设置写入前已显示并执行 I，则证正常读盘。身份不能区分就保缺证，另择同一隔离 UserDir 的全新 Editor 原进程证明。真实点击恢复默认，复验 I 无位移、W 恢复，等待第二次异步落盘后退出。
  - _Requirements: 5.1-5.3_

- [x] 6. 更新活动记录
  - 已写入状态与证据路径；真实设备手感待用户试玩
  - _Requirements: 5.4, 5.5_
