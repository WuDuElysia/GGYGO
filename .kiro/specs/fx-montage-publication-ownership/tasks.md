# Implementation Plan: fx-montage-publication-ownership

## Overview

整改第 3 步。执行规则与命令同第 1 步，输出目录为 `Saved/Kiro/fx-montage-publication-ownership/`（Before/、before_manifest.tsv、Patches/、after_summary.tsv、make_patches.py、edit_*.py）。编译与测试证据与批次 1 同目录：`Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/Build_R5`、`Test_R6`。重核结论与实现差异见 design.md 对应节。

## Tasks

- [x] 0. 开工重核
  - 持有者关闭路径已存在（PlayerCombo ReleaseFX；LocomotionFX 的退役、通知、注销）；BossMelee 不发布 FX
  - 原生清理被拒时 FX 不会经 GA 清理关闭，由任务 3.3 补上
  - IGGYGOMontageFXHost 无蓝图依赖
  - _Requirements: 1.2, 3.3_

- [x] 1. 新增 FX_Replication_Component
  - [x] 1.1 新建 `UGGYGOMontageFXReplicationComponent`，持有复制状态（REPNOTIFY_Always）、终止多播与发行者；OnRegister／OnUnregister 管理发行者寿命
    - _Requirements: 2.1, 1.5_
  - [x] 1.2 CombatantState 构造时创建该组件
    - _Requirements: 2.1, 2.5_
  - [x] 1.3 `PublishMontageFX` 自 ASC 迁入，入口核对事实不变（原 GA 的 ASC 须与宿主同 Owner）
    - _Requirements: 3.4_
  - [x] 1.4 `PublishLocomotionFX` 自 ASC 迁入，LocomotionFXComponent 直接调用
    - _Requirements: 3.1_

- [x] 2. 发布方改用组件
  - MontageActionResources、PlayNiagaraEffect Task、LocomotionFXComponent、Editor 观察工具改用 `FindForASC`；找不到时拒绝并带 ASC/Owner 路径诊断
  - _Requirements: 2.3, 2.4_

- [x] 3. 关闭路径收敛
  - [x] 3.1 LocomotionFXComponent 在来源退役时关闭对应租约（既有实现，未改）
    - _Requirements: 3.3, 1.1_
  - [x] 3.2 Publication_Owner::Shutdown 关闭残留租约并按来源种类／occurrence／System 诊断一次（Warning）
    - _Requirements: 1.5_
  - [x] 3.3 `UGGYGOPlayerComboAbility::OnRemoveAbility` 按 Abort 归还仍持有的 FX lease
    - _Requirements: 1.2_

- [x] 4. 删除 ASC 与 GA 中的旧机制
  - [x] 4.1 删除 Retirement_Wrappers 与扫描，原生覆盖直接执行原函数体
    - _Requirements: 1.3, 1.4_
  - [x] 4.2 删除 ASC 上的 FX 宿主成员、复制属性与多播
    - _Requirements: 2.2, 3.2_
  - [x] 4.3 删除 GA 的 DispatchRetiredMontageFX 与扫描谓词；绑定事务与 CombatantState 不再携出 FX 义务。GA 的退休历史参数链在第 4 步随终止状态机删除
    - _Requirements: 1.3_

- [x] 5. 测试适配
  - 既有 FX 发布测试改用宿主组件语义；新增 `ShutdownClosesResidualLeases`（残留 lease 寿命终点 Abort 关闭、诊断一次、持有者迟到关闭为 AlreadyClosed）与 `ReplicationHostLifecycle`（注册即建立发行者、FindForASC、缺来源拒绝并诊断、重注册复用资源视图）
  - _Requirements: 4.1-4.7, 1.6_

- [ ] 6. 检查点：编译、测试、PIE、联机
  - [x] 编译 GGYGOEditor：Build_R5 成功（19 个 action）
  - [x] NullRHI 测试：Test_R6 共 74 例（批次 1 回归 58 例＋FX 6 例＋Locomotion 10 例），71 通过。未通过 3 例均非本步引入：`Admission.GroupLifecycle`、`PlayerCombo.ActivationCommitAndEndReentry`（第 4 步）；`Movement.Locomotion.InputConsumer.FailedRequestRecovery` 行为断言全部完成，因生产 Error 日志未声明为预期而判失败，2026-10-02 起已失败（当时 2 条，现 3 条，新增一条为 CMC 来源准入拒绝），属 Movement 模块
  - [x] Editor 中核对 CharacterSlot／BossState 蓝图子类已获得新组件：`GGYGO.FX.MontagePublication.HostSubclassAudit`（Test_R16a，NullRHI）由资产注册表列出 CombatantState 全部 9 个子类，项目中没有蓝图子类；每个类的 CDO 都带 `MontageFXReplication` 组件
  - [ ] PIE 单机与最小联机（Requirement 5.3、5.4）：真实 RHI 下观察 FX 出现、结束与 Abort；Test_R19 的 NullRHI 不覆盖 FX。联机各用独立试次和同版生产配置，当前入口见[最小联机需求记录](../../../AAADocs/需求文档/minimal_multiplayer.md)，负责人和占用见[看板](../../../AAADocs/Coordination/Board.md)。
    - [x] N2 live_first：同发布键／代次／原组件的发布、完整快照、Controller、BeginServerTime 对齐及终态通过；同一 Active Draw 的实际 PNG 已查看，下劈弧和地面层可见。原 FX 时长与闭窗语义保持，证据见最小联机需求记录。
    - [x] N3 closed_first：B 在 A 闭窗后首获相关性，收到完整复制快照、同键未 RemoteCreated，实际视口无补播。
    - [x] N4 reacquire：同连接原 ActorChannel Close／CleanUp 的原因、索引和 NetGUID、新 Proxy、剩余 Age 的同帧可见 FX 均通过；旧资源退役后同键新 generation 继续推进。原生 RelevantTimeout 的进程内测试覆盖为 0.05 秒，不代验生产默认关闭等待时长。
    - [x] 活尾回归：原实例 reached 后实际追赶不足并隐藏，正常闭窗恢复时间模式与渲染，真实尾图可见并自然完成／销毁；使用原实例公开 seek 预算刺激，与正常晚加入验收分别记录。
  - _Requirements: 5.1-5.4_

- [x] 7. 更新活动记录
  - 已写入状态与证据路径；画面效果需用户对照原版确认
  - _Requirements: 5.5_
