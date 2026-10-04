# 14a Boss 选择配置：验证与交接

日期：2026-09-30。范围 E10/E11；E9 等待第06批宿主契约，14b另行授权。本批代码、测试源码与局部笔记已完成静态复核并冻结；统筹最终完整 C++ 构建成功，三项 BossSelection 自动化随项目统一门禁通过（项目38/38、0 warning/error）。真实 BT→GAS、生产资产与 PIE 仍未验证。

## 文件与所有权

精确子租约见 `Module_Repair_14a_Subleases.md`。组长先定义 ActionSet/Controller 头文件，两个 gpt-6-luna / max 子代理分别实现四个 cpp 和两份新测试，文件互斥。既有 BossMelee/宿主/ASC/GA/Encounter/BB 资产增量不在本批写入范围。

实际源码文件（相对 Source/GGYGO）：

- `AI/Boss/GGYGOBossActionSet.h`、`.cpp`
- `AI/Boss/GGYGOBossAIController.h`、`.cpp`
- `AI/Boss/BehaviorTree/BTTask_GGYGOChooseBossAction.cpp`
- `AI/Boss/BehaviorTree/BTTask_GGYGOActivateAbility.cpp`
- 新增 `AI/Boss/Tests/GGYGOBossSelectionTest.cpp`、`GGYGOBossSelectionTestTypes.h`

两个 BT Task 头文件无需改动。两个临时子代理已交回冻结并结束；无产品可归档会话身份，未声称归档。组长本批源码亦冻结，后续修正需由统筹重新安排文件所有权。

## 已确认行为

- BaseWeight=0 禁用。先做配置与目标/Tag/GAS 准入，只有合格候选的惩罚权重全耗尽时恢复它们的基础权重；RepeatPenalty=0 是软避重。空集、全基础零和无合格动作正常返回无选择。
- ActionSet 的 editor/runtime 共享全量校验，包含禁用行；坏行导致整集拒绝，提供行级原因。MaxWeight 仍按 max(MaxWeight, BaseWeight) 解释有效上限，保留原语义。
- Controller 仅持有派生权重与一次性请求身份。Set/Phase/ASC/Tag/Class/Spec/Avatar 必须仍匹配；消费失败也清请求。原 Spec 移除后即使同类重授，也不换 Handle 执行。
- BT 继续只向 GAS 请求；冷却/组规则/伤害/位移不迁入决策层。选择记录不新增阶段/动作状态机、Tick 或定时器；Blackboard 仍使用现有 SelectedAction Name 键。
- 预审修正：耗尽恢复先写回派生权重再惩罚/增长；选择前后复核初始来源；激活任务先消费再清黑板，观察者回调后重新核对来源/原 Spec；旧任务 Abort/完成仅解绑自身监听，避免清掉后来的请求。

## 静态与动态门禁

已运行：

- 六份生产文件 `git diff --check` 通过；两份新测试另查行尾空白通过。
- 静态复核 Tag/Class/数值校验、权重写回与确定性抽签、弱引用有效期、失败消费、生命周期清理、原 Spec 查找与 BT 委托释放路径。
- BossAI 四张 Canvas JSON、唯一 ID、边端点、非空语义标签及节点边界无重叠检查通过；其中换形态目标图仅核验未修改。
- BossAI MD/Canvas 的 41 处 wikilink 均能在笔记库解析。更新的是结构.md、计划_BOSSAI.md，以及结构/主流程/选招三张 Canvas。
- 架构复核：新增依赖仍从 Boss 决策指向既有 GAS 公共接口；未新增循环依赖、冷却或阶段权威副本、第二执行器、Tick/计时器。派生权重与一次请求身份的归属、失效和清理已说明。

新增自动化源码（已随最终统一门禁执行通过）：

| 测试名 | 覆盖 |
| --- | --- |
| `GGYGO.BossAI.Selection.ConfigurationValidation` | 空/全零合法，类与标签错误、重复标签、抽象/空类、NaN/Inf 和范围错误；MaxWeight 小于 BaseWeight 的兼容规则 |
| `GGYGO.BossAI.Selection.EligibleWeightsAndDeterminism` | 整集拒绝、单招 penalty=0、2048 次下溢序列、合格项耗尽恢复与写回、非候选增长、大有限值、来源变化、128 次同 seed 序列 |
| `GGYGO.BossAI.Selection.PendingSpecIdentity` | 保存不激活、成功/失败一次消费、禁用后失效、Set/Phase/ASC/Tag/Class/Avatar 变化、原 Spec 移除并同类重授、显式清除/重选/重置种子/UnPossess |

已执行：统筹完成 UHT、完整 C++ 编译/链接及上述三项自动化；报告 `Saved/AutomationReports/ModuleRepairGate_20260930_9/index.json`，项目38/38、0 warning/error。未执行：真实 BT→GAS 动态验收、生产资产回读与 PIE。遵循本批租约，模块会话未运行资产工具或 Git 写操作。04 的 ASC/GA 已完成门禁；06宿主接口冻结后仍须复核14b集成行为。

后续动态验收清单：验证真实 BT→GAS 正常结束/同步结束/取消/Abort，以及黑板观察者重入、选择后阶段/Avatar/能力撤销变化。既有 `BossMelee.EndReentry` 与三项 BossSelection 测试已在统一门禁通过。新增测试直接调用真实 ActionSet/Controller 接口，但未建立 BT 集成夹具；生产编辑器资产 IsDataValid/回读仍待实际验证。激活等待仍按原 SpecHandle 筛选结束事件，独立激活实例标识未在本批新增。

## 局部笔记与统筹待合并项

BossAI 结构.md、计划_BOSSAI.md、结构/主流程/选招 Canvas 已按最终实现更新；其中旧的“未构建/运行”状态应以本页最新门禁结果为准，换形态目标图仍为计划。全局 `模块参考.md`、`计划_实施状态.md`、排程与修复台账由统筹维护；E10/E11 可记为源码和专项自动化通过，真实 BT/生产资产动态验收仍待执行。E9保持未完成，Kevin资产/仇恨/完整阶段事务保持原边界。
