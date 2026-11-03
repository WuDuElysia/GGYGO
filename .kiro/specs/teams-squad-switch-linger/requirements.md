# Requirements Document

## Introduction

本 spec 是整改的第 6 步，总索引见 [活动记录](../../../AAADocs/需求文档/refactor_and_squad_switch.md)。这是一项新行为，不是重构；行为由用户在 2026-11-02 确认。

现状与目标相反：
- SwitchToSlot 在交出控制前取消旧角色的全部能力。GA 的 AvatarExitPolicy 默认为 Cancel，现有 7 个 GA 资产都没有改这项配置。
- DeactivateSlot 立即隐藏旧角色、关闭碰撞并停用移动。

目标行为概要：
- 换人时，每个能力由蓝图决定取消还是留场放完；
- 留场角色不能受击，它放出的技能照常结算；
- 允许多人同时在场，可以切回留场角色，也可以切第三人；
- 切回留场角色时，控制权与镜头立即交接，新输入等技能放完才生效；
- 退场和进场有动作，由 GA 承载。

依赖：第 5 步 combatants-avatar-binding 已验收（换人不再重新绑定 ASC，每个槽位独立）。

## Glossary

- **Squad**：`UGGYGOSquadComponent`，管理编队槽位与当前出战槽位。
- **Slot**：`AGGYGOCharacterSlot`，一个队员的 ASC 宿主与 Avatar。
- **Active_Member**：当前被玩家 Controller 控制的队员。
- **Lingering_Member**：已被换下、仍有选择"放完"的能力在执行的队员。
- **Benched_Member**：已完成退场、隐藏待命的队员。
- **Switch_Out_Decision**：能力对一次换出的处理结果，取值 Cancel 或 ContinueOnField。
- **Switch_Context**：换出时传给能力的信息：目标槽位、切换来源（玩家请求、死亡自动切换、脚本）。
- **Off_Field_State**：留场期间施加在 Lingering_Member 上的状态，由一个无限时 GE 承载，授予 `State.OffField` 标签，并使伤害类 GE 免疫。
- **Return_Pending_State**：切回仍在留场的队员时，在其技能放完前施加的状态：阻止新能力激活与移动，按下的能力输入照常进入缓冲。
- **Switch_In_Ability／Switch_Out_Ability**：由 GameplayEvent `Event.Squad.SwitchIn`／`Event.Squad.SwitchOut` 触发的进场／退场能力，Montage 与时长由角色资产配置。

## Requirements

### Requirement 1: 换出时能力自行决定

**User Story:** 作为能力设计者，我希望每个能力在换人时自己决定取消还是留场放完，长按蓄力这类能力可以在蓝图里做特殊处理。

#### Acceptance Criteria

1. THE GA 基类 SHALL 提供 BlueprintNativeEvent `OnAvatarSwitchOut(const FGGYGOSwitchContext&)`，返回 Switch_Out_Decision；默认实现读取 AvatarExitPolicy（Cancel→Cancel，ContinueInBackground→ContinueOnField）。
2. WHEN 玩家切换出战角色, THE Squad SHALL 对旧 Active_Member 的每个活动能力调用一次 OnAvatarSwitchOut，返回 Cancel 的能力被取消，返回 ContinueOnField 的继续执行。
3. WHEN 旧 Active_Member 失去控制, THE 系统 SHALL 向其仍按住的能力输入补发一次真实的释放（触发 AbilitySpecInputReleased 与 WaitInputRelease），然后向其每个继续执行的能力调用 BlueprintImplementableEvent `OnOwnerControlLost`。
4. WHEN 玩家切回一个仍有继续执行能力的队员, THE 系统 SHALL 向这些能力调用 BlueprintImplementableEvent `OnOwnerControlRegained`。
5. THE AvatarExitPolicy 字段 SHALL 保留，作为 OnAvatarSwitchOut 默认实现的配置。

### Requirement 2: 留场角色

**User Story:** 作为玩家，我希望换人后旧角色留在场上把技能放完，期间不会被打。

#### Acceptance Criteria

1. WHILE 队员处于 Lingering_Member, THE 系统 SHALL 保持其可见、保持与地面和场景的碰撞、保持移动组件可执行技能位移。
2. WHILE 队员处于 Lingering_Member, THE 系统 SHALL 对其施加 Off_Field_State：近战命中检测跳过该角色，伤害类 GE 对其不生效，不播放受击 Cue 与受击反应。
3. WHILE 队员处于 Lingering_Member, THE 其能力 SHALL 照常命中目标并结算伤害。
4. WHEN Lingering_Member 的全部继续执行能力结束, THE 系统 SHALL 执行该队员的退场（Requirement 4）。
5. IF 队员换出时没有选择 ContinueOnField 的能力, THEN THE 系统 SHALL 直接执行退场，不进入留场。

### Requirement 3: 多人在场与切回

**User Story:** 作为玩家，我希望可以随时切到任意可出战队员，包括还在场上放技能的那个。

#### Acceptance Criteria

1. THE Squad SHALL 允许同一时刻存在一个 Active_Member 与任意数量的 Lingering_Member。
2. WHEN 玩家切到一个 Benched_Member, THE 系统 SHALL：
   1. 立即把控制权交给它；
   2. 显示它、恢复碰撞与行走；
   3. 触发其进场（Requirement 4）。
3. WHEN 玩家切到一个 Lingering_Member, THE 系统 SHALL：
   1. 立即把控制权与镜头交给它；
   2. 移除其 Off_Field_State，恢复可受击；
   3. 取消其尚未开始的退场；
   4. 不播放进场；
   5. 对其施加 Return_Pending_State，直到其继续执行的能力全部结束。
4. WHILE Return_Pending_State 生效, THE 系统 SHALL 阻止该队员激活新能力和移动；按下的能力输入照常进入现有缓冲窗口，状态解除后按缓冲规则执行。
5. WHEN 切换发生时被换下的队员自己也有继续执行的能力, THE 系统 SHALL 对它按 Requirement 1 与 2 同样处理。
6. THE Squad SHALL 拒绝切到当前 Active_Member、无 Avatar 或已死亡的槽位，并诊断。

### Requirement 4: 进场与退场

**User Story:** 作为角色设计者，我希望每个角色有自己的进场和退场动作，动作内容由资产决定。

#### Acceptance Criteria

1. WHEN 执行退场, THE Squad SHALL 向该队员的 ASC 发送 GameplayEvent `Event.Squad.SwitchOut`；IF 该事件激活了能力, THEN THE Squad SHALL 等待该能力结束后再隐藏角色、关闭碰撞并停用移动；IF 没有能力被激活, THEN THE Squad SHALL 立即执行隐藏。
2. WHEN 执行进场, THE Squad SHALL 先显示角色并恢复碰撞与行走，再发送 GameplayEvent `Event.Squad.SwitchIn`；控制权在切换开始时已交给该队员。
3. THE 进场与退场能力的 Montage、时长、能否被打断、进场位置 SHALL 由角色的能力资产与蓝图决定；C++ 只提供事件、等待与收尾。
4. THE 项目 SHALL 提供 C++ 基类 `UGGYGOSquadTransitionAbility`：
   - 配置 Montage；
   - 触发方式为对应的 GameplayEvent；
   - 播放结束时结束能力；
   - 蓝图子类可以覆盖。
5. WHEN 退场进行中玩家切回该队员, THE 系统 SHALL 取消退场能力，按 Requirement 3.3 处理（若已无继续执行的能力则不施加 Return_Pending_State）。

### Requirement 5: 网络

#### Acceptance Criteria

1. THE 切换 SHALL 由服务器执行；客户端的切换请求经 Server RPC 发送，服务器校验后执行。
2. THE 留场、退场、进场的可见性、碰撞与 Off_Field_State SHALL 由服务器设置并复制到客户端。
3. THE Lingering_Member 的能力 SHALL 在服务器上继续执行，客户端看到其 Montage、位移与 FX。
4. THE 客户端 SHALL 在切回 Lingering_Member 后看到镜头立即切换，输入在 Return_Pending_State 解除后生效。

### Requirement 6: 不回退的行为

#### Acceptance Criteria

1. THE 系统 SHALL 保持待命槽位的 ASC 状态（冷却、Buff、生命值）不被清理。
2. THE 系统 SHALL 保持死亡队员不可切入。
3. THE 系统 SHALL 保持现有编队装配、名单与存档行为。

### Requirement 7: 验收

#### Acceptance Criteria

1. WHEN 本 spec 全部任务完成, THE 作者 SHALL 编译 GGYGOEditor 并通过。
2. THE 作者 SHALL 新增并通过 GGYGO.Teams.SquadSwitch 自动化测试，覆盖：
   - Cancel 决定取消能力；ContinueOnField 决定留场；
   - 留场不受伤害且其技能照常结算；
   - 留场结束后执行退场；
   - 切回留场角色时立即交接控制、施加并解除 Return_Pending_State、缓冲输入生效；
   - 三人场景（1 留场时 2→3）；
   - 退场中切回取消退场；
   - 无进退场能力时立即完成；
   - 蓄力能力在 OnOwnerControlLost 中收到通知。
3. THE 作者 SHALL 在 PIE 中用至少两名队员验证上述主要场景；IF 编队资产只有一名可用队员, THEN THE 作者 SHALL 用测试编队验证并在活动记录中注明。
4. THE 作者 SHALL 做最小联机验证：客户端发起切换，服务器与客户端看到一致的留场、退场与进场。
5. THE 作者 SHALL 在活动记录中注明：进场与退场动作资产、手感需用户提供或确认。
6. WHEN 验收通过, THE 作者 SHALL 更新活动记录。
