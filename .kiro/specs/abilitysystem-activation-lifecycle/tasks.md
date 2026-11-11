# Implementation Plan: abilitysystem-activation-lifecycle

## Overview

整改第 4 步，改动面最大。执行规则与命令同第 1 步，输出目录为 `Saved/Kiro/abilitysystem-activation-lifecycle/`。开工前确认第 3 步已验收。

当前按第 1 步 Overview 所链接的项目规则执行；本次状态核对只读取已有证据，不启动 UE 或重跑测试。

状态（2026-11-12）：激活寿命实现、相关回归、单机基本动作链及最小联机纠正已交付；任务 8 保留部分完成。现有交付记录没有给出 Requirement 9.2 中 `GGYGO.Editor.Animation` 完整过滤器的对应报告，不能把局部 Editor 测试推成整组通过。

## Tasks

- [x] 0. 开工重核
  - 按 design.md 核对当前源码的调用链、行号与消费者
  - 确认没有动画蓝图使用非 Guard 的 AnimInstance（在 Kiro 自己的 Editor 实例中查看全部 ABP 父类）
  - 确认 N3 纠正重放测试入口位置
  - _Requirements: 4.5, 9.5_
  - 生产动画蓝图 ABP_Pyrios（GGYGOAnimInstanceBase）与 ABP_Kevin_DemonBattle 均继承 Guard；真实玩家／Kevin 运行入口已有交付记录。纠正入口为 `run_minimal_multiplayer.ps1 -Case correction`，已完成真实双端验证，见任务 8。

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
  - `PlayerCombo.ActivationCommitAndEndReentry` 的旧裸重激活夹具已适配原输入来源，`Verify_R2/Test_R9`／`Test_R10`／`Test_R16a/Automation/index.json` 均为 Success，原失败保留。
  - `Admission.GroupLifecycle` 的旧 NativeEndNotObserved 失败已闭合，`Verify_R2/Test_R9/Automation/index.json` 为 Success；同 Spec 嵌套 Try 的后续来源问题在 `Saved/Codex/I23_20261111/Automation/index.json` 的原诊断及五项相关回归中通过。
  - Boss 测试的 protected 接口与精确日志断言随共享资源迁移
  - _Requirements: 7.2, 8.1-8.7, 9.3, 10.6_

- [~] 8. 检查点：编译、测试、PIE、联机
  - [x] GGYGOEditor 编译通过，最终联机源码构建为 `Saved/Codex/MinimalMultiplayer_20261111/build_tail_observation.log`。
  - [~] Requirement 9.2 自动化：`Verify_R2/Test_R9`、`Test_R10`、`Test_R16a` 保留各组结果及 ABA 回归；Test_R9 的 Camera 失败原样保留，其不属于本条要求的过滤器。当前 `GGYGO.Editor.Animation` 只找到 [SyncMarker 两项专项](../../../Saved/Codex/I22_20261111/Rerun/editor.log) 等局部交付，完整组结果未覆盖，不重跑或推断补齐。
  - [x] Requirement 9.4 基本动作链：三段普攻见 [生产冒烟](../../../AAADocs/需求文档/normal01_first_strike.md)，Special／ExSpecial 实跑和自然清理见 [FX 接线](../../../AAADocs/需求文档/fx_audio_wiring.md)，TurnBack 动作见 [生产镜头观察](../../../AAADocs/需求文档/walkrun_turnback_production_camera.md)，Boss 连续选招与正式战斗见 [Kevin 交付](../../../AAADocs/需求文档/kevin_boss_assembly.md)。保留两项 PoseFailure 原 Fail；以上不签用户待定的起停／镜头行为或视听还原。
  - [x] N0/N1：D3D12 双端真实 attack-only 中，同一原 Montage／Task 自然结束，同一 RMS 按真实步长消费最后的 XYZ／Yaw，GA 未取消且原资源全部归还；内存预检与断言证据见[最小联机需求记录](../../../AAADocs/需求文档/minimal_multiplayer.md)。
  - [x] N5：具名 NET 读回仅有 lag；预测段 1 被服务器拒绝，沿 Mode2 原 basis 重放段 0，随后真正新起段 1，两端自然结束并清理。Initial 无法提供的独立试次证明同激活 Reliable TargetDataCancelled 与精准归还。模拟代理独立 Apply／imported RMS 不属于 requirements 9.5 的前提，未扩建该执行链；证据与边界见最小联机需求记录。
  - _Requirements: 9.1-9.5_
  - 编译与既有 NullRHI 测试证据保持；最小联机已完成 D3D12 双端验证。此勾选不替代其余单机、Cook 或完整网络矩阵。

- [x] 9. 更新活动记录
  - _Requirements: 9.6_
