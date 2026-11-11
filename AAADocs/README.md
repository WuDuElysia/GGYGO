# GGYGO 项目文档导航

先看[看板](Coordination/Board.md)找到自己的需求记录，再按需要查接口。历史与 Validation 只按需查相关段落，不作为续接默认输入。Obsidian架构Markdown及Canvas仍在`F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划`；这里保存项目执行、配置、工具及验证记录。

## 目录职责

| 目录 | 放什么 | 主要入口 |
| --- | --- | --- |
| `Coordination` | 需求看板与占用表、问题清单、长期会话路由 | [看板](Coordination/Board.md)、[修复清单](Coordination/Module_Audit_Repair_Ledger.md)、[会话路由](Coordination/Module_Conversation_Routing.md)、[Codex 交接](Coordination/Handover_Codex.md)、[旧排程（仅历史参考）](Coordination/Module_Repair_Parallel_Schedule.md) |
| `Rules` | 协作、架构、代码、验证交付与文档规则，由根 AGENTS.md 按场景索引 | [架构与分层](Rules/ArchitecturePrinciples.md)、[代码规范与审核](Rules/CodeConventions.md)、[任务推进](Rules/TaskWorkflow.md)、[验证与交付](Rules/VerificationDelivery.md)、[文档与上下文](Rules/Documentation.md) |
| `Architecture/Interactions` | 跨模块接口、组件协作和共同生命周期契约 | [移动输入来源](Architecture/Interactions/Module_Repair_MovementInput_Contract.md)、[Avatar事务](Architecture/Interactions/Module_Repair_K4_ActorInfoTransaction.md)、[动画与移动接线](Architecture/Interactions/Locomotion_AnimBP_Wiring_Audit.md) |
| `Modules` | 按所属模块存放实现与专项验收记录 | Animation、Audio、Character、CombatActions、Movement；[Audio契约](Modules/Audio/Audio_Contract.md) |
| `Assets` | 导入盘点、角色／Boss素材配置与素材侧验收 | BH3、Pyrios |
| `Scripts` | 可执行资产工具、只读探针与离线测试 | 不因文档整理改变脚本自身位置；数据默认路径同步新目录 |
| `References` | 图片、着色器和运动参考数据 | 保留参考素材，不与源码职责记录混放 |
| `需求文档` | 用户需求与原始行为说明 | [Kevin Boss 组装](需求文档/kevin_boss_assembly.md)、[整改与切人](需求文档/refactor_and_squad_switch.md) |

## 存放规则

- 根目录只留本导航和进度总览。不得为每个小步骤继续向根目录添加记录。
- 模块内部问题进入`Modules/对应模块`；跨模块接口或组件交互进入`Architecture/Interactions`，并标明唯一状态所有者、调用方向和清理责任。
- 输入／输出配置、导入清单与素材核验进入`Assets`或实际模块目录；执行工具留在`Scripts`。
- 新结论优先更新已有模块记录，不创建重复摘要或复制整段历史；接口定义、生产接入、编译、动态、图文状态分开写。
- 活动入口只留目标、现状、未完成项、验收与必要依赖／证据；已结束过程当次迁历史。续接先筛状态与标题，聊天只取必要最终回执，不全文回传历史或机器快照。
- 迁移保留原文件名与历史内容，修正可执行路径和文档链接。正在写的文件由作者冻结后再移动，不留下两份可继续写的副本。
