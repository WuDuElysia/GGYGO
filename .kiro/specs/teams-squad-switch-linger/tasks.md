# Implementation Plan: teams-squad-switch-linger

## Overview

整改第 6 步，新行为。执行规则与命令同第 1 步，输出目录为 `Saved/Kiro/teams-squad-switch-linger/`。开工前确认第 5 步已验收。资产制作需要启动 Kiro 自己的 Editor 实例，只保存本 spec 新建的资产，不 SaveAll。

状态（2026-11-03 收尾）：源码与 NullRHI 测试完成；监听服务器＋1 客户端的 NullRHI PIE（测试编队）全部通过，Test_R19 的 3 条生产 Error 已在收尾续修中消除（Test_R22，见任务 6、8）。玩法取舍由用户 11-04 决定并已落实（见任务 9）；换人键已接好。与 design.md 的差异见其「实现差异」。

## Tasks

- [x] 0. 开工重核
  - 核对 SquadComponent 所在 Actor、现有切换输入入口、OnRep_ActiveSlotIndex 的客户端逻辑
  - 核对现有伤害 GE 的资产标签、NotifyAbilityFailed 的排队条件、相机在 Possess 后的行为
  - 核对实际编队资产中可用队员数量
  - 结论见 `Saved/Kiro/teams-squad-switch-linger/progress.md`
  - _Requirements: 5.1, 2.2, 3.4, 7.3_

- [x] 1. 标签与能力接口
  - [x] 1.1 新增 State.OffField、State.SwitchReturnPending、Event.Squad.SwitchIn、Event.Squad.SwitchOut 标签（另加失败原因 Ability.ActivateFail.SwitchReturnPending）
    - _Requirements: 2.2, 3.4, 4.1, 4.2_
  - [x] 1.2 GA 基类新增 OnAvatarSwitchOut、OnOwnerControlLost、OnOwnerControlRegained 及 FGGYGOSwitchContext；默认实现读 AvatarExitPolicy
    - _Requirements: 1.1, 1.4, 1.5_
  - [x] 1.3 GA 基类激活条件追加 State.SwitchReturnPending 阻止（只拦输入缓冲发起的激活）；CMC 移动阻止追加该标签
    - _Requirements: 3.4_

- [x] 2. 输入补发释放与缓冲
  - [x] 2.1 ASC 输入缓冲协作者提供 ReleaseHeldInputForControlLoss
    - _Requirements: 1.3_
  - [x] 2.2 SwitchReturnPending 阻止的激活失败可排队，标签移除后的下一次 ProcessAbilityInput 唤醒
    - _Requirements: 3.4_

- [x] 3. 留场状态
  - [x] 3.1 MeleeTrace 跳过拥有 State.OffField 的目标
    - _Requirements: 2.2_
  - [x] 3.2 Off_Field 改为 Squad 施加的复制 loose tag（State.OffField＋仅服务器的 Gameplay.Damage.Immunity），不制作 GE_OffField 资产
    - _Requirements: 2.2_

- [x] 4. Squad 切换流程
  - [x] 4.1 FSlotRuntime 与队员状态；订阅各槽位 ASC 的 OnAbilityEnded
    - _Requirements: 3.1, 2.4_
  - [x] 4.2 重写 SwitchToSlot 为 design.md 的流程，删除旧的换人前退出与 DeactivateSlot 立即隐藏
    - _Requirements: 1.2, 1.3, 2.1, 2.5, 3.2, 3.3, 3.5, 3.6_
  - [x] 4.3 退场与进场：BeginExit／FinishExit／SwitchIn 事件，退场中切回取消退场
    - _Requirements: 4.1, 4.2, 4.5_
  - [x] 4.4 删除 ASC 中第 4、5 步留下的换人退出旧实现
    - _Requirements: 1.2_

- [x] 5. 进场／退场能力基类
  - 新增 UGGYGOSquadTransitionAbility；测试用进场与退场能力为 C++ 测试类，生产资产待用户提供
  - _Requirements: 4.3, 4.4_

- [x] 6. 网络
  - 新增 ServerRequestSwitchToSlot；开发期控制台入口 `GGYGOSwitchToSlot N`（PlayerController Exec，走同一 RPC）
  - 正式换人键（用户 11-03）：Controller 级上一个／下一个，默认 Z／C，键位在 `IMC_Squad`，两个 IA 带 PlayerMappable 名；经 `ServerRequestSwitchToAdjacentSlot(±1)` 由服务器选目标。Test_R23 联机测试中客户端真实按 Z／C 切换通过
  - 收尾发现并修复：引擎的整体碰撞开关不复制，待命队员在客户端保留胶囊；改为 `AGGYGOCharacterBase::SetReplicatedActorEnableCollision` 由服务器设置并复制
  - 联机验证 `GGYGO.Teams.SquadSwitch.ListenServerClientRequest`（Test_R19）：客户端 RPC 切人、留场可见与碰撞、OffField 复制且免疫不复制、ReturnPending 复制与解除、待命隐藏无碰撞、切回待命队员后控制与 ViewTarget 跟随
  - 收尾续修：待命队员在服务器停骨架更新（`bNoSkeletonUpdate`），消除从未附身队员的 WalkRunLean Error；Camera 管理器允许同一 Controller 新附身的 Pawn 重新准入。Test_R22 的 SquadSwitch 7 例全部通过，无生产 Error
  - _Requirements: 5.1-5.4_

- [x] 7. 测试
  - SquadSwitch 6 例：CancelAndPreserveState、UncancelableRejectsBeforeEffects、ContinueLingersThenExits、ReturnToLingeringMember、ThreeMembersOneLingering、ReturnDuringExitCancelsExit
  - _Requirements: 6.1-6.3, 7.2_

- [~] 8. 检查点：编译、测试、PIE、联机
  - 编译 GGYGOEditor：Build_R13 通过；收尾 Build_R16～R19 通过
  - Test_R13（114 例）109 通过，3 例既有失败，2 例夹具问题已修并在 Test_R14 通过；收尾 Test_R16a 受影响 54 例全部通过，Test_R17 SquadSwitch 私有 6 例通过
  - PIE 与最小联机：L_Movement_Test 上的同进程监听服务器＋1 客户端 NullRHI PIE，测试编队为 Experience 首位角色 Pyrios 的两份实例（PostLogin 写 Roster，走生产“已设 Roster”来源），续放能力用夹具 GA，无进退场 GA 时按规则立即进场／待命。行为断言全部通过（Test_R19）
  - Test_R19 的 Automation 结果为 Fail：3 条生产 Error，未过滤——服务器上从未被附身的待命队员 PawnExtension 停在 Spawned（权威端等 Controller），MovementSet 未应用，ABP_Pyrios 的 WalkRunLean 报错 2 次；客户端切到新队员时相机管理器拒绝第二个激活源（already-activated-for-another-original-source）1 次。收尾续修后 Test_R22 通过，无生产 Error。NullRHI 下角色渲染的 R32f 格式错误属运行环境，测试中声明为预期
  - 未验：画面、Montage／FX 表现、真实设备输入、真实 RHI
  - _Requirements: 7.1, 7.3, 7.4_

- [x] 9. 更新活动记录
  - 注明进退场动作资产与手感待用户提供或确认；提示现有 GA 默认仍为 Cancel
  - _Requirements: 7.5, 7.6_

- [x] 9. 用户 11-04 决定的落实（活动记录「收尾续二」）
  - 不可取消的 Cancel 决定改为留场放完；开局第一名不发 SwitchIn；玩家换人冷却 `SwitchCooldownSeconds`（DefaultGame.ini，0.5 秒，只限 PlayerRequest）；出战队员倒下期间玩家不能换人，死亡演出结束后以 DeathAutoSwitch 自动切到下一个存活队员
  - 死亡能力 `UGGYGODeathAbility` 与 Pyrios 资产（AM_Pyrios_Death、GA_Pyrios_Death，替换 DA_AbilitySet_Pyrios 中的 GA_Death）
  - 键盘改键界面 `SGGYGOKeyBindingMenu`（控制台 `GGYGOOpenKeySettings`），IMC_Default 主键位可改键
  - 测试：`UncancelableContinuesOnField`（替换 `UncancelableRejectsBeforeEffects`）、`PlayerCooldownAndDeathAutoSwitch`；联机测试补冷却、改键、客户端移动与普攻、主机按键、死亡自动换人。Test_R34 全部通过
  - 未验：真实 RHI 画面；客户端再次附身先前控制过的队员后不能移动（Movement owner-sync，已交原模块）
  - _Requirements: 用户决定_
