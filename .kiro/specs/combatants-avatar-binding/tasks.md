# Implementation Plan: combatants-avatar-binding

## Overview

整改第 5 步。执行规则与命令同第 1 步，输出目录为 `Saved/Kiro/combatants-avatar-binding/`。开工前确认第 4 步已验收。

本 spec 按"先新流程跑通，再删旧协议"的顺序推进：任务 1-2 完成后编译并跑一次 PIE 出生流程，再做任务 3。

实现与计划的差异见 design.md 末尾"实现差异"。

## Tasks

- [x] 0. 开工重核
  - 核对当前绑定链、PawnExtension InitState 条件、FGGYGOAvatarBindingContext 与 IGGYGOAvatarBindingHostInterface 的全部消费方
  - 确认现有释放流程实际移除的 Cue 范围
  - 结论见 `Saved/Kiro/combatants-avatar-binding/progress.md`
  - _Requirements: 3.2, 3.4, 2.2_

- [x] 1. 本地 ASC 订阅
  - [x] 1.1 PawnExtension 提供 FGGYGOLocalASCSubscription 与 Ready／Released 广播
    - _Requirements: 1.1, 1.5_
  - [x] 1.2 Hero、CMC、Health 改用该订阅，删除各自样板（LocomotionFX 同样迁移；Health 订阅从 CharacterBase 移入 Health）
    - _Requirements: 1.2-1.4_

- [x] 2. Host 绑定流程
  - [x] 2.1 CombatantState 实现 BindAvatar／ReleaseAvatar，AttachAvatar 与 OnRep_AvatarPawn 调用它；嵌套请求拒绝
    - _Requirements: 2.1, 2.2, 2.4, 2.5, 2.6_
  - [x] 2.2 PawnExtension 的 Initialize／Uninitialize／HandleControllerChanged 改为直接流程；InitState 条件不依赖宿主请求，保持不变
    - _Requirements: 2.3, 5.2_
  - [x] 2.3 GameMode、BossEncounter、SquadComponent 调用点适配（GameMode、BossEncounter 接口未变；Squad 改用资源句柄）
    - _Requirements: 5.1, 6.1_
  - [~] 2.4 中间检查：PIE 需用户批准，未执行；以 Build_R11／R12 与 NullRHI Test_R11／R12 代替
    - _Requirements: 6.1_

- [x] 3. 删除绑定协议
  - [x] 3.1 ASC 删除 Binding_Protocol，原生覆盖只保留清输入（Avatar 变化时的 Montage 状态由原生 InitAbilityActorInfo 复位）
    - _Requirements: 3.1_
  - [x] 3.2 迁移 FGGYGOAvatarBindingContext 的全部消费方（含 FX 移动来源身份）
    - _Requirements: 3.2_
  - [x] 3.3 CombatantState 删除事务实现与 FindClearCommit；Host 接口收敛为 ReleaseAvatarBinding
    - _Requirements: 3.3, 3.4_

- [x] 4. ASC 拆分
  - [x] 4.1 新建 FGGYGOAbilityInputBuffer，迁入输入段
    - _Requirements: 4.1, 4.3_
  - [x] 4.2 新建 FGGYGOAbilityStepInputRouter，迁入分段输入与 Initial 路由
    - _Requirements: 4.2, 4.3_

- [x] 5. 测试适配
  - 改写 ActorInfoTransaction 测试为绑定流程外部契约，新增订阅测试，其余测试调用点改名
  - _Requirements: 6.1-6.4_

- [~] 6. 检查点：编译、测试、PIE、联机
  - [x] 编译 GGYGOEditor：Build_R11 成功；修正释放顺序后 Build_R12 成功
  - [x] Requirement 7.2 测试：Test_R12 111 例 108 通过；3 例为既有失败（Camera.ModeOwnershipAndAvatarReceiver 未绑定仲裁、Input.MovementOrigin.NativeBirthFirstDigitalPress 需原生窗口、Locomotion.InputConsumer.FailedRequestRecovery 未声明的生产 Error 日志），失败内容与本步之前一致
  - [~] PIE（Requirement 7.3）与最小联机（Requirement 7.4）：收尾在 L_Movement_Test 上跑了 NullRHI 同进程监听服务器＋1 客户端（`GGYGO.Teams.SquadSwitch.ListenServerClientRequest`，Test_R19）——生产 GameMode 装配两名队员、客户端出生并附身首位、客户端请求切换后服务器与客户端看到同一出战角色；再次切到待命队员后，客户端控制该队员，其 HealthComponent 经本地 ASC 订阅取得的数值与服务器一致。未验：客户端移动与攻击（需真实输入）、死亡与重生、Boss 出场与出招、画面
  - _Requirements: 7.1-7.4_

- [x] 7. 更新活动记录
  - _Requirements: 7.5_
