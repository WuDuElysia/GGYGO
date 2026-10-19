# 第 12 批 Combat 命中查询入口

更新：2026-10-13。本页仅保留仍需消费的命中契约、未完成验收与证据入口。活动需求、当前作者、依赖和共享窗口以[当前排程](../../Coordination/Module_Repair_Parallel_Schedule.md)为准；修复编号见[修复清单](../../Coordination/Module_Audit_Repair_Ledger.md)。原作者在职责内自主完成技术实现与自审，必要集成点按完整可运行链设置。

## 稳定必要契约

| 职责／入口 | 输入 → 作用 → 输出与边界 |
| --- | --- |
| Combat Trace | GA 自有命中窗口、Mesh 与 `RootTip`／`SocketChains` 配置 → 完整预检后执行固定世界半径 Sweep，请求 PhysicalMaterial → 同一窗口跨链／段 Actor 去重。窗口归属、Mesh／资源身份及失效清理保持；无效配置明确拒绝。 |
| Player／Boss 命中 Caller | 本次有效命中、原激活资源与目标 ASC → 取命中回调时原 Avatar 的当前位置为 Origin，调用 `BuildHitEffectPayload` → Caller 配置数值并提交 GE／Cue。Origin 的时点保持为命中回调。 |
| 共享载荷／EffectContext | 同次 HitResult、显式 Origin、双方 ASC 与所选 GE → `AddHitResult(reset=true)` 后写来源快照，统一构造 Context／Spec／Cue 并追加 Owner／物材 Tags → Context 保留显式快照，距离衰减使用 Origin→ImpactPoint。必需 Spec 构造失败返回空载荷并诊断；明确的 CueOnly 模式仍合法。 |
| Execution／HealthSet | `BaseDamage`／`BasePoiseDamage` 的明确 SetByCaller 或必需 capture → 解析、衰减及计算 → Execution 只新增 Damage／PoiseDamage 元属性，由 HealthSet 落地。覆盖值须有限且非负，零合法；非法覆盖不回 capture，缺失／非有限 capture 拒绝并不新增 Modifier。此拒绝不能冒称整个 GE／GA 应用失败。 |
| HitImpact Cue | HitResult／ParametersLocation／TargetCenter 的显式位置模式及表面策略 → 解析位置与匹配表面 → 使用配置表现；未命中表面与无表面按明确策略处理。未知资源、挂点或来源保持未知。 |

实现入口：[Trace](../../../Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.cpp)、[Player](../../../Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp)、[Boss](../../../Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp)、[Builder](../../../Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp)、[Context](../../../Source/GGYGO/AbilitySystem/GGYGOGameplayEffectContext.cpp)、[Execution](../../../Source/GGYGO/AbilitySystem/Executions/GGYGODamageExecution.cpp)、[Cue](../../../Source/GGYGO/AbilitySystem/Cues/GGYGOGameplayCueNotify_HitImpact.cpp)。稳定协作与审核规则见 [AGENTS.md](../../../AGENTS.md) 和 [CodeConventions](../../Architecture/CodeConventions.md)。

## 未完成事项与验收边界

- 正式 Player／Boss 动画命中、GE／GA／物材／Cue 资产接线和可见表现，以及 EndPlay／消息、PIE、权威伤害与 Cue 联机／专服边界仍需相应生产证据。专项合成链、构建、包存在或保存不代这些验收。
- Gate86 原报告仍有三项 `Fail`：`RuntimeHit.RequiredGEFailure`（1 Error）、`RuntimeHit.BuilderFailureUncancelable`（2 Error）、`TraceShape.InvalidConfiguration`（2 Error）。原错误及报告保留，不因其它叶通过改写为全成功。
- StrictCapture 第8族在旧交接中只记录源码静态冻结与未编译／运行；本页未核其后准确运行收据，不据本次归档升级结论。衰减非法值、乘积溢出及原局部图文同步的未验边界仍保留在[Validation 第13.2节及此前开放项](Module_Repair_12_Validation.md)。这些记录不新增实现范围或逐内部步骤审批。
- 后续写入须按当前排程确认唯一作者，并与执行者完整父保护求交；重叠输入在保护正常归还后才可改写。独立业务准备可继续，文档整理不作为业务前置。

## 已有证据与历史

| 范围 | 准确证据及有限结论 |
| --- | --- |
| E4／E6 合成权威链 | [Gate22](../../../Saved/AutomationReports/ModuleRepairGate_20260930_22/index.json) 的 PayloadSpecContextAndTargetCapture、[Gate25](../../../Saved/AutomationReports/ModuleRepairGate_20260930_25/index.json) 的 DistanceExecutionUsesOriginSnapshotAfterCauserMove 已记录 Success；原断言与有限边界见 [Validation 第8／9节](Module_Repair_12_Validation.md)。 |
| Context／Cue／Tag | [Gate64R1](../../../Saved/AutomationReports/ModuleRepairGate_20261004_64R1_Smoke/index.json) 两项 HitSemantics 为 Success，各0E0W；不代实际媒体或生产动画验收。 |
| Trace／运行命中夹具 | [Gate86](../../../Saved/AutomationReports/ModuleRepairGate_20261005_86_Smoke/index.json) 的 SafetyAndCoverage 与 RuntimeHit.NormalModes 为 Success、各0E0W；整份报告为5 Success／3 Fail，失败见上节。 |
| 原租约／门禁／失败 | [原文历史](Module_Repair_12_Subleases_History_20261013.md) 完整保留整理前37,909字节及全部旧标题、过程、旧授权和未完成项；[9/30冻结约束](Module_Repair_12_Subleases_History_20261013.md#冻结与集成约束)仅说明当时流程。历史临时代理、逐项停止点及“实现／测试／文档不得打包”不构成当前授权或内部步骤审批。旧Gate11／12失败等原验证记录仍见 [Validation](Module_Repair_12_Validation.md)。 |

后续交付沿当前排程原位更新事实与未完成项；已结束过程及时迁入同目录历史，保全原文、失败及仍被下游使用的契约，不在本入口累积逐轮日志。本轮归档只整理文档，未运行构建、UE、资产保存、PIE或网络验收。
