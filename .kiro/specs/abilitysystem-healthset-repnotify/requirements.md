# Requirements Document

## Introduction

本 spec 是整改的第 7 步，总索引见 [活动记录](../../../AAADocs/需求文档/refactor_and_squad_switch.md)，对应问题 12 与问题 3 的属性反算部分。

现状：HealthSet 用 ModifierFrame、ExpectedAttributeChange、RepNotifyFrame、QueuedResult 等结构（HealthSet.cpp:43-217、994-1166），区分 GAMEPLAYATTRIBUTE_REPNOTIFY 的回卷写入和真实变化，并延迟发布消息。属性反算（ASC 的 TryCalculateNumericAttributeBaseForCurrentValue）放在 ASC 中。

本 spec 先做最小复现，再决定分类帧是否可以改用 Lyra 做法：服务器在 PostGameplayEffectExecute 中用精确幅度广播，客户端在 OnRep 中按新旧值广播。属性反算是用户确认保留的功能（修复清单决定 #2：允许持续 GE 修改当前 Health／Poise），本 spec 只迁移它的位置，不删除。

依赖：第 6 步 teams-squad-switch-linger 已验收。第 5 步已完成 ASC 拆分，本步迁出反算时 ASC 不再有其它写入者。

## Glossary

- **Health_Consumers**：HealthSet 结果的全部消费方，包括：
  - HealthComponent 的 Health／MaxHealth／Poise 变化、OutOfHealth、PoiseBroken 回调；
  - Messages 通道的 PoiseBreak 消息；
  - 死亡状态投影；
  - 开工重核时列全的 UI 或蓝图绑定。
- **Observable_Results**：Health_Consumers 实际收到的事件序列，包括事件种类、Old、New、Magnitude、Instigator 与次数。
- **Lyra_Approach**：服务器在 PostGameplayEffectExecute 中按 GE 精确幅度广播；客户端在 OnRep 中以 Old／New 广播，Magnitude 取 New-Old；MaxHealth 下降时由服务器修正 Health。
- **Inverse_Base_Calculation**：给定期望 Current 值，反算应写入的 Base 值，用于持续 GE 存在时修改当前值。

## Requirements

### Requirement 1: 最小复现

**User Story:** 作为能力系统作者，我希望在决定删不删分类帧之前，先看到每种场景下消费方实际收到什么。

#### Acceptance Criteria

1. THE 作者 SHALL 构建最小复现，在服务器与一个客户端上分别记录 Observable_Results，场景包括：
   - 普通伤害；
   - 治疗；
   - PoiseDamage 导致破韧；
   - 致死伤害；
   - MaxHealth 下降导致 Health 被压低；
   - 持续 GE 存在时修改当前 Health。
2. THE 作者 SHALL 对同一场景分别记录现行实现与 Lyra_Approach（以临时分支或测试开关实现）的 Observable_Results。
3. THE 作者 SHALL 把两组结果的差异写入活动记录，并保留复现日志。

### Requirement 2: 根据复现结果决定

#### Acceptance Criteria

1. IF 两组 Observable_Results 对全部 Health_Consumers 等价（事件种类、次数、Old／New 一致，Magnitude 差异不被任何消费方使用）, THEN THE HealthSet SHALL 改用 Lyra_Approach，删除 ModifierFrame、ExpectedAttributeChange、RepNotifyFrame、NetReceiveFrame、QueuedResult 及其流程。
2. IF 存在消费方可见的差异, THEN THE 作者 SHALL 保留分类帧，在 HealthSet 头文件注释中写明它防止的具体差异与对应场景，并把差异作为需要用户判断的项写入活动记录。
3. THE 作者 SHALL NOT 在复现完成前删除分类帧。

### Requirement 3: 迁出属性反算

#### Acceptance Criteria

1. THE Inverse_Base_Calculation SHALL 从 ASC 迁到 AttributeSet 侧的工具函数（HealthSet 与 CombatSet 共用），输入为 ASC、AttributeSet、Attribute、当前值与期望值，输出为结果状态与 Base 值。
2. THE ASC SHALL 删除 TryCalculateNumericAttributeBaseForCurrentValue。
3. THE 迁移 SHALL 保持计算结果与失败分类不变。

### Requirement 4: 不回退的行为

#### Acceptance Criteria

1. THE 系统 SHALL 保持持续 GE 存在时可以修改当前 Health／Poise（决定 #2）。
2. THE 系统 SHALL 保持 OutOfHealth 与 PoiseBroken 在一次跨越零点时各只发一次。
3. THE 系统 SHALL 保持 MaxHealth 下降时由权威端压低 Health，客户端不自行写 Base。
4. THE 系统 SHALL 保持伤害执行（DamageExecution）与 PoiseDamage 结算不变。

### Requirement 5: 验收

#### Acceptance Criteria

1. WHEN 本 spec 全部任务完成, THE 作者 SHALL 编译 GGYGOEditor 并通过。
2. THE 作者 SHALL 运行并通过以下测试；若改用 Lyra_Approach，则按外部结果改写依赖内部帧的断言：
   - GGYGO.AbilitySystem.HealthMessage
   - GGYGO.AbilitySystem.DamageExecution
   - GGYGO.Combatants.DeathProjection
3. THE 作者 SHALL 在 PIE 与最小联机中验证：受击扣血、破韧、死亡在服务器与客户端表现一致。
4. WHEN 验收通过, THE 作者 SHALL 更新活动记录，写明 Requirement 2 走了哪一支及依据。
