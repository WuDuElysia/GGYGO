# GGYGO 项目文档导航

先看[进度总览](进度总览.md)，再按模块查实现与证据。Obsidian架构Markdown及Canvas仍在`F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划`；这里保存项目执行、配置、工具及验证记录。

## 目录职责

| 目录 | 放什么 | 主要入口 |
| --- | --- | --- |
| `Coordination` | 统筹排程、问题清单、长期会话路由和全局诊断 | [有效排程](Coordination/Module_Repair_Parallel_Schedule.md)、[修复清单](Coordination/Module_Audit_Repair_Ledger.md)、[会话路由](Coordination/Module_Conversation_Routing.md) |
| `Architecture` | 代码规范、复杂度审核机制与整体实施路线 | [代码规范与审核机制](Architecture/CodeConventions.md)、[实施路线](Architecture/Implementation_Roadmap.md) |
| `Architecture/Interactions` | 跨模块接口、组件协作和共同生命周期契约 | [移动输入来源](Architecture/Interactions/Module_Repair_MovementInput_Contract.md)、[Avatar事务](Architecture/Interactions/Module_Repair_K4_ActorInfoTransaction.md)、[动画与移动接线](Architecture/Interactions/Locomotion_AnimBP_Wiring_Audit.md) |
| `Modules` | 按所属模块存放实现、原子范围与专项验收记录 | AbilitySystem、Animation、Camera、CombatActions、Combat、Combatants、Input、Movement、Teams、GameFeature、Messages、BossAI、System、Character；新增[Audio契约](Modules/Audio/Audio_Contract.md) |
| `Assets` | 导入盘点、角色／Boss素材配置与素材侧验收 | BH3、Pyrios |
| `Scripts` | 可执行资产工具、只读探针与离线测试 | 不因文档整理改变脚本自身位置；数据默认路径同步新目录 |
| `References` | 图片、着色器和运动参考数据 | 保留参考素材，不与源码职责记录混放 |
| `需求文档` | 用户需求与原始行为说明 | [TurnBack需求](需求文档/turnback.md) |
| `log` | 既有工具日志 | 历史数据，不作为最新验收状态 |

## 存放规则

- 根目录只留本导航和进度总览。不得为每个小步骤继续向根目录添加记录。
- 模块内部问题进入`Modules/对应模块`；跨模块接口或组件交互进入`Architecture/Interactions`，并标明唯一状态所有者、调用方向和清理责任。
- 输入／输出配置、导入清单与素材核验进入`Assets`或实际模块目录；执行工具留在`Scripts`。
- 新结论优先更新已有模块记录，不创建重复摘要或复制整段历史；接口定义、生产接入、编译、动态、图文状态分开写。
- 迁移保留原文件名与历史内容，修正可执行路径和文档链接。正在写的文件由作者冻结后再移动，不留下两份可继续写的副本。

原先暂留的输入来源记录已在作者冻结后迁入`Modules/AbilitySystem`；根目录现只保留导航与进度总览。
