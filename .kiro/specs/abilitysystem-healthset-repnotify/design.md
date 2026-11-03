# Design Document

## Overview

先验证，后决定。行号为 2026-11-02 版本，开工重核。

改动面：
- `Source/GGYGO/AbilitySystem/Attributes/GGYGOHealthSet.{h,cpp}`、`GGYGOCombatSet.{h,cpp}`（视反算消费方）
- 新增 `Source/GGYGO/AbilitySystem/Attributes/GGYGOAttributeBaseCalculation.{h,cpp}`
- `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.{h,cpp}`：删除 264-460 的反算
- 测试：HealthMessage、DamageExecution、DeathProjection；新增复现测试

## 复现方法

- 新增自动化测试 `GGYGO.AbilitySystem.HealthRepro.*`。使用现有 HealthMessage 测试的夹具搭建权威端 ASC 与模拟客户端接收：
  - 用 PreNetReceive、OnRep、PostNetReceive 按原生顺序驱动；
  - 开工重核现有夹具是否已有这条路径。
- 每个场景记录 Health_Consumers 收到的事件：种类、Old、New、Magnitude、Instigator、次数。结果写入 `Saved/Kiro/abilitysystem-healthset-repnotify/repro_<场景>.log`。
- Lyra_Approach 以测试专用的 HealthSet 子类实现（只在测试模块内），不改生产类，便于同场景对比。
- 另做一次真实联机复现：listen server + 1 客户端，Boss 打玩家、玩家打 Boss，记录客户端 HealthComponent 回调日志，核对自动化复现的结论。

## 决定后的两条路径

### 等价：改用 Lyra_Approach

- **服务器**：PostGameplayEffectExecute 中处理 Damage／Healing／PoiseDamage 元属性，写 Health／Poise，并用 GE 精确幅度广播 Changed、OutOfHealth、PoiseBroken，发出 PoiseBreak 消息。
- **客户端**：OnRep_Health／OnRep_Poise 用 GAMEPLAYATTRIBUTE_REPNOTIFY 后的值，以 Old／New 广播，跨零点时广播 OutOfHealth／PoiseBroken 各一次（用 bOutOfHealth／bPoiseBroken 锁存）。
- **MaxHealth 下降**：权威端在 PostAttributeChange 中调用反算工具压低 Health；客户端不写。
- **删除**：ModifierFrame、ExpectedAttributeChange、RepNotifyFrame、NetReceiveFrame、QueuedResult、FlushPendingResults、AttributeChangeDepth、OnAttributeAggregatorCreated 覆盖。

### 不等价：保留

在 HealthSet.h 文件头写明：分类帧防止的具体差异、出现的场景、对应的消费方。差异写入活动记录，交用户判断。

## 反算迁移

```cpp
namespace GGYGOAttributeBase
{
    FGGYGOAttributeBaseCalculationResult CalculateBaseForCurrent(
        const UAbilitySystemComponent& ASC, const UAttributeSet& Set,
        const FGameplayAttribute& Attribute, float ExpectedCurrent, float DesiredCurrent);
}
```

原实现读取 ASC 的聚合器（ActiveGameplayEffects 的 Aggregator）。工具函数通过 ASC 的公开接口或现有 friend 访问。开工重核：若必须访问 ASC 受保护成员，就让 ASC 保留一个只做转发的受保护访问器，计算逻辑仍在工具函数中。

## Testing Strategy

- 复现测试保留为回归测试，断言最终选定方案的 Observable_Results。
- HealthMessage 现有 15 个测试：若改用 Lyra_Approach，删除断言内部帧阶段的部分，保留对事件序列的断言。

## 风险

- 客户端预测的伤害（如果存在）会让 OnRep 的 Old 值与服务器不同。开工重核项目是否有客户端预测伤害；当前伤害只在权威端结算（PlayerCombo HandleMeleeHit 要求 HasAuthority）。

## 复现结果与实现差异（2026-11-03）

- 复现测试 `GGYGO.AbilitySystem.HealthRepro.CurrentVersusLyra` 放在 HealthMessage 测试文件内，直接复用其夹具；Lyra 对照类 `UGGYGOHealthReproLyraSet` 在 `GGYGOHealthMessageTestTypes.h`。客户端用同一夹具的模拟接收：Setup 状态在两端都以权威施加（持续 GE 造出聚合器），然后客户端切为 SimulatedProxy，在一次 Pre/PostNetReceive 内按属性声明顺序复制有变化的 Base/Current 并调用 OnRep。Lyra 对照的 Current 写入同样经反算，以保持决定 #2。
- 结果（`Saved/Kiro/abilitysystem-healthset-repnotify/Repro_R14/`）：普通伤害、治疗、破韧、致死、持续 GE 下改当前 Health 五个场景两种做法完全一致；MaxHealthDrop（持续 GE 下调 MaxHealth）不一致——现行实现在服务器广播 HealthChanged 与 MaxHealthChanged，Lyra 只广播 HealthChanged（MaxHealth 来自持续 GE，不经 PostGameplayEffectExecute）。客户端在六个场景中都一致。
- 决定：走 Requirement 2.2，保留分类帧。差异写入 HealthSet.h 文件头与活动记录。曾考虑的简化（服务器保持 PostAttributeChange 广播，客户端只在 OnRep 广播并删去 RepNotifyFrame／NetReceiveFrame）不采用：它没有回卷、重入与客户端上限投影的等价证明（HealthMessage 的 RepNotify*、ClientMaxNetReceive 覆盖这些情形），而现行实现在复现和联机中结果正确。这是技术决定，收尾时由执行者定案。
- 联机核对（收尾，Test_R19）：同进程监听服务器＋1 客户端，服务器对客户端出战队员施加即时伤害、持续 GE 下调 MaxHealth、削韧至 0；两端属性、HealthComponent 数值与广播一致，持续 GE 下调上限时服务器也广播 MaxHealthChanged。
- 复现测试保留为回归：断言现行实现在六个场景的事件序列，Lyra 结果只写日志（测试运行时写到 `ProjectSavedDir()/Kiro/abilitysystem-healthset-repnotify/`，NullRHI 窗口中即该窗的 `Editor/Saved/`）。
- 反算迁移：`GGYGOAttributeBase::CalculateBaseForCurrent(ASC, Set, Attribute, ExpectedCurrent, DesiredCurrent)`，逻辑与失败分类照搬；原用 ASC 受保护的 `GetAttributeSubobject`，改用等价的公开 `GetAttributeSet`。
