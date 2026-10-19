# Combat 玩家动作接续

本页为本模块的短接续入口。旧实施、租约、门禁和失败见[第04批完整历史](Module_Repair_04_Subleases_History_20261013.md)；历史措辞仅描述当时状态。

## 当前任务与原作者

- 当前需求、实际冻结点及UE/构建窗口：[有效排程](../../Coordination/Module_Repair_Parallel_Schedule.md)。
- 职责与会话：[路由](../../Coordination/Module_Conversation_Routing.md)。本模块负责玩家GA/段资源和授予配置；公共Montage Task由AbilitySystem原作者维护。
- 当前公共Task契约依据：[公共接口](../../../Source/GGYGO/AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.h)及[实现](../../../Source/GGYGO/AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.cpp)。

## 必要契约

- ASC独占能力输入准入/消费；GA持本次原激活与自有段资源，CMC执行胶囊位移，Animation执行姿态/作者窗口，Combat查询与去重命中。
- Task事实须绑定原激活、原Mesh、原Montage和固定原生实例；后继、失效及停止明确拒绝，不按同资产或播放计数推导身份。
- 攻击接续与移动打断为独立门。E/R/F及隔离Special诊断使用双门Disabled/None，完整Main＋End自然结束；不添加组合、取消、伤害、成本或FX窗口。
- 所属写集与完整父保护集合求交后才能写入。当前窗口及共享文件换手以有效排程和原作者实际冻结/归还为准。

## 未完成项与验收边界

- [A1正式归还](../../../Saved/Codex/PyriosSkillActions_20261013_A1/return.json)只证明CS副本三GA/Set保存和独立Cold。E/R/F实际输入、原激活/Task、自然结束、FullBody姿态、声音和联机仍未验。
- 诊断B仍需单声真实资产Cold、GA/Set切换及恢复Cold、实际trial与生产Pawn/Mesh/World、真实E及原激活观察。明确标记“非原时序、未还原”，不将候选关联升级为原cue或生产选声。离线准备见[所属B入口](../../../Saved/Codex/PyriosSkillActions_20261013_B_Prepare/)。
- Special实际入口的必要源码桥接接P4正常归还后的所属窗口；它不作为SlotA验证前置。准确前置和原作者沿当前排程收敛。
- 第04批原生Started重入P1失败与B4兼容缺口保留在[原验证记录](Module_Repair_04_Validation.md)及完整历史。A1资产Cold或后来的编译结果不关闭这些原问题；复验须指向该问题的实际证据。

## 历史与维护

[第04批完整历史](Module_Repair_04_Subleases_History_20261013.md)逐字节保存迁移前全文，包含旧拒绝/失败、旧租约和已结束门禁。相对源码/文档位置保持同目录可解析。

交付时覆盖本页仍未完成项和验收边界，将结束的过程原文归入历史；当前页不累计回执、哈希表或步骤日记。无事实变化不重复维护；稳定契约变化核源码，只更新受影响入口。
