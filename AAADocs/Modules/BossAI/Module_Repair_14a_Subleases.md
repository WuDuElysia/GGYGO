# 14a Boss 选择配置：文件子租约

日期：2026-09-29。统筹授权范围以 Module_Repair_Parallel_Schedule.md 的 C 线为准；E9 留 14b。

## 唯一写入者

路径以 F:/ue_project/GGYGO 为根。未列文件禁止修改。所有子代理使用 gpt-6-luna / max；不得再派代理、操作 UE/MCP、编译、修改资产或执行 Git 写操作。

| 子任务 | 唯一写入范围 | 状态 / 验收 |
| --- | --- | --- |
| 组长：接口、审查、记录 | Source/GGYGO/AI/Boss/GGYGOBossActionSet.h；Source/GGYGO/AI/Boss/GGYGOBossAIController.h；AAADocs/Modules/BossAI/Module_Repair_14a_Subleases.md；AAADocs/Modules/BossAI/Module_Repair_14a_Validation.md；Obsidian GGYGO架构规划/BossAI/ 内 MD/Canvas | 接口/最终审查/静态门禁/局部笔记完成；全批冻结交回，构建与动态门禁待统筹 |
| /root/selection_impl（gpt-6-luna / max） | Source/GGYGO/AI/Boss/GGYGOBossActionSet.cpp；Source/GGYGO/AI/Boss/GGYGOBossAIController.cpp；Source/GGYGO/AI/Boss/BehaviorTree/BTTask_GGYGOChooseBossAction.cpp；Source/GGYGO/AI/Boss/BehaviorTree/BTTask_GGYGOActivateAbility.cpp | 已交回冻结，组长完成 diff 与接口/清理静态复核；子代理已结束，未提供可归档会话身份 |
| /root/selection_tests（gpt-6-luna / max） | Source/GGYGO/AI/Boss/Tests/GGYGOBossSelectionTest.cpp；Source/GGYGO/AI/Boss/Tests/GGYGOBossSelectionTestTypes.h | 已交回冻结，三项自动化源码静态复核完成；未构建/执行。子代理结束，不冒称已归档 |

组长不同时编辑子任务租出文件；子任务交回冻结后才可收回修正。两个 BT Task 头文件本轮暂不需改动，仍归组长；实现代理如需变更接口先报告。

## 已冻结接口与行为

- ActionSet::ValidateConfiguration(FString& OutError) const：统一 editor/runtime 规则，失败给出资产/行级原因；IsDataValid 复用。检查所有行（含 BaseWeight=0 行）的 Tag 有效且在 BossAction 命名空间、唯一，能力类非空/非抽象/非失效类且 CDO ActionTag 匹配；所有数值有限、非负，角度 0..180，RepeatPenalty 0..1，MaxDistance=0 或 >=MinDistance。MaxWeight 可以小于 BaseWeight，保持有效上限 max(MaxWeight, BaseWeight) 的现有语义。空集合/全零基础权重合法。FindAction 对重复目标 Tag 返回空，不能返回首条掩盖歧义。
- Controller::SelectAction(ActionSet, EligibleActionTags)：先校验全集；只从调用方已通过目标/Tag/GAS 筛选的合法 Tag 中选择，按 ActionSet 顺序遍历；BaseWeight=0 禁用。合格候选全耗尽时只恢复这些候选基础权重，同一次调用抽签；无候选不抽签。double 累计/更新防溢出，权重有限且钳制；确定性随机每次成功选招只抽一次。选中后由此函数调用 RecordActionSelection 一次。WeightSource 不同清旧派生权重。
- StoreActionSelection(Set, Phase, ASC, Tag, Spec)：清旧请求后验证全集、唯一动作、当前有效 Spec/class/Tag 与非空 Avatar，记录弱 Set/ASC/Class/Avatar 及 Phase/Tag/Spec；不激活能力。
- ConsumeActionSelection(Set, Phase, ASC, Tag, OutSpec)：先取出并清空，再比较所有身份与当前配置/Spec。失败也消费，输出无效 Handle；成功返回原 Handle，禁止按 Class 查找一个新 Spec。Set/Phase/ASC/Tag/Class/Avatar 或 Spec 变化均拒绝。
- ClearActionSelection：重选、初始化种子、Possess/UnPossess、EndPlay 均清请求。它是一次性请求身份，不是动作或阶段状态机，不持有冷却。
- ChooseTask：入口清旧请求/黑板；全文配置校验失败整体 Failed 并诊断；原有筛选之后再 SelectAction。调用 GAS 预检前复制 SpecHandle，避免回调后解引用旧 Spec。保存原候选 Handle 后写 Blackboard Tag。
- ActivateTask：入口清旧等待；消费短期请求并清 Blackboard，校验 Controller Pawn 与 ASC Avatar 一致；失败清旧请求。仅激活消费出的原 Handle，保留同步结束/取消/Abort 委托清理语义。

## 只读依赖与回归

只读：AGENTS、排程/台账；BossState/Definition、CombatantState、PawnExtension、ASC 公共接口、CombatActionAbility::GetActionTag、现有 BossMelee/测试。04/06 接口未冻结，禁止修共享文件，待后续集成复验。

测试至少覆盖：空/全零合法；重复 Tag/类标签不符/抽象或空类/非有限数值/非法范围整体拒绝；单招 penalty=0、长序列下溢、多招全耗尽、只恢复合法候选、基础零禁用、相同 seed 可复现、大有限值；一次性消费、失败消费、不同 Set/Phase/ASC/Tag/Class/Avatar、移除重授 Spec、清请求与重新初始化失效。测试不得启动资产生产或依赖现有 BB 资产。

局部文档收尾：结构.md、计划_BOSSAI.md、结构/主流程/选招 Canvas；E9/完整阶段/仇恨/换形态/Kevin 接线维持未完成。全局状态改动只在 Validation 文档交给统筹。
