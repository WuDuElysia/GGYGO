# Implementation Plan: abilitysystem-activation-lifecycle

## Overview

整改第 4 步，改动面最大。执行规则与命令同第 1 步，输出目录为 `Saved/Kiro/abilitysystem-activation-lifecycle/`。开工前确认第 3 步已验收。

本 spec 内按小步编译：每完成 1-6 中的一项先编译一次（只编译，不跑完整测试），检查点 8 再跑完整测试。

## Tasks

- [x] 0. 开工重核
  - 按 design.md 核对当前源码的调用链、行号与消费者
  - 确认没有动画蓝图使用非 Guard 的 AnimInstance（在 Kiro 自己的 Editor 实例中查看全部 ABP 父类）
  - 确认 N3 纠正重放测试入口位置
  - _Requirements: 4.5, 9.5_
  - 结果（11-03）：生产动画蓝图 ABP_Pyrios（GGYGOAnimInstanceBase）与 ABP_Kevin_DemonBattle 都继承 Guard，按资产父类引用离线核对；N3 入口未核，随任务 8 的联机验证一起做

- [x] 1. 激活身份与结束
  - [x] 1.1 精简 FActivationProof，在 NotifyAbilityActivated 中签发，EndAbility 覆盖中退役并调用 CleanupAbilityResourcesForTermination
    - _Requirements: 1.1-1.4, 2.6_
  - [x] 1.2 重写 RequestAbilityEnd／RequestAbilityCancel，收敛 FGGYGOAbilityTerminationResult
    - _Requirements: 2.1-2.4_
  - [x] 1.3 删除 Termination_Machine 在 GA 与 ASC 中的全部代码，ActivateAbility 改为 design.md 中的主流程
    - _Requirements: 2.5, 1.1_
  - [x] 1.4 IsDataValid 增加 Instanced 与禁止重触发检查，删除 ASC 每次激活的重复检查
    - _Requirements: 1.5_
  - [x] 1.5 PlayerCombo、BossMelee 的 RequestAbilityEnd／Cancel 调用点改用新结果
    - _Requirements: 2.3_

- [x] 2. 输入失败排队与路由
  - [x] 2.1 用当前输入尝试取代评估令牌链，NotifyAbilityFailed 按 Spec 句柄匹配
    - _Requirements: 6.1_
  - [x] 2.2 Initial 路由与分段输入请求改用 Activation_Handle 与 bEndingActivation
    - _Requirements: 6.2, 6.3_

- [x] 3. BT 与 Editor 观察
  - [x] 3.1 BTTask 改用 TryActivateAbility + OnAbilityEnded，处理 Try 内同步结束
    - _Requirements: 3.1-3.4_
  - [x] 3.2 GGYGOPlayerActionObservation 改用 OnAbilityEnded
    - _Requirements: 3.5_

- [x] 4. Montage 播放
  - [x] 4.1 合并为单一播放入口，播放身份改为 Playback_Identity
    - _Requirements: 4.1, 4.2_
  - [x] 4.2 精简 MontageGuard 中只为 ASC 证明服务的部分，保留创建实例识别与 ActionPoseContract
    - _Requirements: 4.3_
  - 结果：`IsMontagePlayGuardIdentityCurrent` 被 Task 使用，生命周期代次被 ActionPoseContract 使用，没有只为 ASC 证明服务的部分，Guard 未改
  - [x] 4.3 删除 GA 终止时的播放所有权捕获；按重核结果处理 Legacy 分支
    - _Requirements: 4.4, 4.5_
  - [x] 4.4 Montage Task 精简 Activated* 字段与派发谓词
    - _Requirements: 4.6, 5.3_

- [x] 5. 段寿命
  - [x] 5.1 FStepMotionResources 按 design.md 的顺序释放并解绑
    - _Requirements: 5.1_
  - [x] 5.2 PlayerCombo 回调改为只比较 Step_Resources，跨帧回调另比较 StepToken；删除 ResolveOriginalCaller 等多层认证
    - _Requirements: 5.2_
  - [x] 5.3 BossMelee 采用同样规则
    - _Requirements: 5.4_
  - [x] 5.4 共享资源增加 BeginProfileMotion 与固定超时 Watchdog，ReleaseMotion 统一释放两种位移
    - _Requirements: 10.2, 10.3_
  - [x] 5.5 BossMelee 改用共享资源，保留 Mesh Tick 与 Tick 前置依赖处理，删除重复字段与起止逻辑
    - _Requirements: 10.1, 10.4, 10.5_

- [x] 6. 换人退出过渡与测试钩子
  - [x] 6.1 TryExitAbilitiesForAvatarSwitch 改为 RequestAbilityCancel，保持取消行为
    - _Requirements: 8.6_
  - [x] 6.2 删除 GA 的 *ForTest 钩子
    - _Requirements: 7.1_
  - [x] 6.3 删除 FinalizeAbilityGroupAdmission 中的测试日志块，依赖它的测试改为断言外部结果
    - _Requirements: 10.8_
  - [x] 6.4 合并不带 Facing 的 BeginMontageActionMotion 与共享资源的两个 BeginMotion 重载，调用方传默认 Facing
    - _Requirements: 10.7_

- [x] 7. 测试适配
  - OnAbilityTerminationCompleted 的使用改为 OnAbilityEnded；依赖钩子的测试改用子类覆盖；补齐 ABA 外部契约测试；删除内部状态断言
  - 批次 1 遗留：`PlayerCombo.ActivationCommitAndEndReentry` 第 3～5 子例在 Montage Ready 回调、End 广播或延期 End 后用裸 `TryActivateAbility` 重激活，后继 Initial 没有输入 edge，被现行来源规则拒绝；按任务 2.2 的新 Initial 路由重定这些子例的期望（后继须有自己的输入来源，或改为验证明确拒绝且旧栈不清理后继）
  - 批次 1 遗留：`Admission.GroupLifecycle` 报 reason=14（NativeEndNotObserved），2026-10-05 起已失败，随任务 1、6.3 一并处理
  - Boss 测试的 protected 接口与精确日志断言随共享资源迁移
  - _Requirements: 7.2, 8.1-8.7, 9.3, 10.6_

- [~] 8. 检查点：编译、测试、PIE、联机
  - 检查磁盘余量并告知，编译 GGYGOEditor
  - 运行 Requirement 9.2 列出的全部测试
  - PIE 与最小联机按 Requirement 9.4、9.5 验证。
  - [ ] N0/N1：复用 Build_R48 和原 D3D12 双端入口，按[最小联机需求记录](../../../AAADocs/需求文档/minimal_multiplayer.md)的内存要求采集同窗内存（当前负责人和占用见[看板](../../../AAADocs/Coordination/Board.md)）。闩停只记资源失败。真实 attack-only 中，同一原 Montage 和 Task 自然结束，同一 RMS 按真实步长消费最后的 XYZ/Yaw，GA 未取消且原资源全部归还。退出退役的取消不作自然收尾证据。
  - [ ] N5：读回具名 NET 的两项 lag 与五项 incoming，FrameDelay、Bloat 或 Loss 非零拒绝。记录预测段 1、服务器拒绝、沿 Mode2 原 basis 重放段 0、随后真正新起段 1；另证 Initial 无法提供时同激活 Reliable TargetDataCancelled 和准确归还。attack-only 独立取证，原双打断点和纠正身份保持。
  - _Requirements: 9.1-9.5_
  - 已完成编译与 NullRHI 测试（Build_R6～R10、Test_R7～R10，结论见活动记录"第 4 步"）；PIE 单机与最小联机需真实 RHI，另批

- [x] 9. 更新活动记录
  - _Requirements: 9.6_
