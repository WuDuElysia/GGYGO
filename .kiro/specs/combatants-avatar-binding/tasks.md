# Implementation Plan: combatants-avatar-binding

## Overview

整改第 5 步。执行规则与命令同第 1 步，输出目录为 `Saved/Kiro/combatants-avatar-binding/`。开工前确认第 4 步已验收。

状态（2026-11-13）：源码及绑定回归完成，真实 RHI 客户端出生、移动、攻击、换人后重新操作及死亡替补已有证据，Boss 正式出场与出招已有单机证据。同一 Editor 的监听服务器＋两个客户端已补齐第三端换人实拍；复活流程尚不存在，任务 6 保持部分完成。

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
  - [x] 2.4 出生流程验证：Build_R11／R12 与 NullRHI Test_R11／R12 的证据保留；后续真实 RHI 已走通生产出生和客户端操作，证据见任务 6。
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
  - [x] 真实 RHI 出生／操作／换人：`Saved/Codex/CharacterDeathPolicy_20261111/rhi2.log` 的 `GGYGO.Teams.SquadSwitch.ListenServerClientRequest` 为 Success，覆盖客户端初次及重新附身后的移动、攻击、Z／C 请求切换、死亡自动替补和两端状态一致；更早集中运行见 `Verify_R2/RHI_Integrated_R1/Automation/index.json`。
  - [x] Boss 出场与连续出招：[Kevin 正式战斗交付](../../../AAADocs/需求文档/kevin_boss_assembly.md) 已核对原 Encounter、绑定、技能与死亡清理，不扩大为 Kevin 联机。
  - [ ] 复活：项目没有复活流程，不能由死亡替补或再次附身推断通过。
  - [x] 第三端观察换人：`GGYGO.Combatants.AvatarSwitch.ThirdClientObserver` 在 D3D12、同一 Editor 的监听服务器＋两个客户端中通过，零测试错误、六条警告。所属客户端经生产 RPC 完成 0→1→0，三端按同一 PlayerId／NetGUID 核对活动 Pawn、可见性、碰撞和 ASC ActorInfo；服务器与所属端保留两组原 Pawn／ASC 资源，观察端遵循原生相关性。服务器和另一客户端各三张自然视口截图已核对，原 Slot／ASC 未替换。使用两份现有 Pyrios 实例和临时诊断机位，不保存编队，不代表不同角色外观、独立进程或网络扰动验收。编译、日志、报告和图片见[第三端换人验收](../../../AAADocs/需求文档/refactor_and_squad_switch.md#avatar-绑定第三端换人观察)。
  - _Requirements: 7.1-7.4_

- [x] 7. 更新活动记录
  - _Requirements: 7.5_
