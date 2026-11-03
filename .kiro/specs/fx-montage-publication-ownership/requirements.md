# Requirements Document

## Introduction

本 spec 是整改的第 3 步，总索引见 [活动记录](../../../AAADocs/需求文档/refactor_and_squad_switch.md)，对应问题 2。

现状：同一个"FX 关闭"事实有三条写路径——
- 资源持有者释放时关闭；
- GA 激活退休时，经 ASC 的 15 个 *WithRetirementOutput 包装把关闭义务层层带出；
- 每次包装收尾时扫描全部在播来源，关闭"已失效"的来源。

此外，ASC 兼任 Montage FX 与移动 FX 的发布宿主，复制状态挂在 ASC 上。

目标：
- 发布租约（lease）只由持有者在释放资源时关闭；
- 复制状态和发布宿主迁到 FX 自己的组件，挂在同一个 CombatantState 上，复制寿命与相关性不变；
- 移动 FX 不再经过 ASC。

顺序说明：原计划把本步排在激活/终止状态机之后。依赖分析后提前：本步完成后，第 4 步重写激活与终止时不再需要维护 FX 关闭义务。

## Glossary

- **Publication_Owner**：`UGGYGOMontageFXPublicationOwner`，负责派生复制数据、精确关闭和本地资源能力。
- **FX_Lease**：`FGGYGOMontageFXLease`，一次发布的本地许可，以 occurrence 标识。
- **Lease_Holder**：持有 FX_Lease 的对象。
  - Montage FX：GA 持有的 `FGGYGOMontageActionResources`；
  - 移动 FX：`UGGYGOLocomotionFXComponent` 的 Cue 记录。
- **FX_Replication_Component**：新增的 `UGGYGOMontageFXReplicationComponent`，挂在 `AGGYGOCombatantState` 上，持有复制状态 `FGGYGOMontageFXState`、终止多播和 Publication_Owner。
- **Retirement_Wrappers**：ASC.h 中的 `*WithRetirementOutput` 包装、`ExecuteWithMontageFXRetirement`、`PrepareMontageFXRetirements`、`PrepareInvalidMontageFXSources`，以及 GA 的 `DispatchRetiredMontageFX`。

## Requirements

### Requirement 1: 租约只由持有者关闭

**User Story:** 作为 FX 作者，我希望每次发布的关闭只有一个写入者，这样关闭时点和原因都能直接从持有者读出来。

#### Acceptance Criteria

1. WHEN Lease_Holder 释放其资源（正常结束或中止）, THE Lease_Holder SHALL 按 Normal 或 Abort 关闭它持有的每个 FX_Lease，各一次。
2. WHEN GA 以任何原生方式结束（EndAbility、CancelAbility、DestroyActiveState、RemoveAbility、ClearActorInfo 引发的取消）, THE GA SHALL 经现有资源清理路径释放 Lease_Holder，从而关闭租约。
3. THE ASC SHALL 删除全部 Retirement_Wrappers，原生入口恢复为直接调用 Super 或项目自身逻辑。
4. THE 系统 SHALL NOT 保留任何"遍历全部来源、关闭已失效者"的扫描逻辑。
5. IF 某个租约在其 Publication_Owner 关闭（组件注销、Actor 销毁）时仍未关闭, THEN THE Publication_Owner SHALL 在 Shutdown 中按 Abort 关闭并诊断一次。
6. THE occurrence SHALL 继续作为唯一跨端身份；旧持有者关闭只作用于自己的 occurrence，不影响后继发布。

### Requirement 2: 复制宿主迁到 FX 组件

**User Story:** 作为 FX 作者，我希望 FX 的复制状态由 FX 模块自己的组件持有，ASC 只做能力相关的事。

#### Acceptance Criteria

1. THE FX_Replication_Component SHALL 挂在 AGGYGOCombatantState（含 CharacterSlot、BossState）上，持有 `FGGYGOMontageFXState`（REPNOTIFY_Always）与终止多播 RPC，并在注册时创建 Publication_Owner。
2. THE ASC SHALL NOT 再实现 IGGYGOMontageFXHost，也 SHALL NOT 持有 MontageFXState、MontageFXPublicationOwner 或终止多播。
3. THE FX 发布方（MontageActionResources、PlayNiagaraEffect Task、LocomotionFXComponent）SHALL 通过一个查找函数从 ASC 的 Owner Actor 取得 FX_Replication_Component。
4. WHEN 找不到 FX_Replication_Component, THE 发布方 SHALL 明确拒绝发布并诊断，SHALL NOT 改为本地直接播放。
5. THE 复制寿命与相关性 SHALL 与迁移前一致：状态仍随 CombatantState 复制，晚加入和重获相关性时客户端收到当前全部活动记录。

### Requirement 3: 移动 FX 不经过 ASC

#### Acceptance Criteria

1. THE LocomotionFXComponent SHALL 直接向 FX_Replication_Component 发布，来源身份仍用 CMC 的移动来源证明。
2. THE ASC SHALL 删除 TryPublishLocomotionFX、IsLocomotionFXAvatarCurrent、IsLocomotionFXSourceCurrent。
3. WHEN CMC 退役一个移动来源, THE LocomotionFXComponent SHALL 关闭该来源对应的租约。
4. THE Montage FX 的发布入口 SHALL 从 ASC::TryPublishMontageFX 迁到 FX_Replication_Component，入口核对的事实不变：权威端、原 GA 的当前激活、原 Task 的 Begin 窗口事实、Mesh 与 Avatar 一致。

### Requirement 4: 不回退的行为

#### Acceptance Criteria

1. THE 系统 SHALL 保持晚加入或重获相关性的客户端看到仍有效的剩余 FX，并按 BeginServerTime 计算 Age 跳到对应进度。
2. THE 系统 SHALL 保持已结束的窗口不补播。
3. THE 系统 SHALL 保持 Normal 与 Abort 两种停止方式及其配置。
4. THE 系统 SHALL 保持专用服务器上没有本地组件时也关闭发布记录。
5. THE 系统 SHALL 保持远端组件的寿命与 generation 规则，旧清理不触及同 key 的后继实例。
6. THE 系统 SHALL 保持 Editor 观察窗（FGGYGOMontageFXObservation）对现有工具和测试可用。
7. THE 系统 SHALL 保持 Normal03 两条独立失真路径、各层顺序与现有表现配置不变。

### Requirement 5: 验收

#### Acceptance Criteria

1. WHEN 本 spec 全部任务完成, THE 作者 SHALL 编译 GGYGOEditor 并通过。
2. THE 作者 SHALL 运行并通过 GGYGO.FX、GGYGO.AbilitySystem.PlayerCombo、GGYGO.Movement.Locomotion。
3. THE 作者 SHALL 在 PIE 单机验证：三段普攻与 Normal03 FX 正常出现与结束；TurnBack 烟雾正常；连段中途被打断时 FX 按 Abort 停止。
4. THE 作者 SHALL 做最小联机验证（listen server + 1 客户端）：客户端看到服务器角色的普攻 FX；在 FX 播放中途加入的客户端看到剩余 FX，不补播已结束窗口。
5. WHEN 验收通过, THE 作者 SHALL 更新活动记录，注明画面效果需用户对照原版确认。
