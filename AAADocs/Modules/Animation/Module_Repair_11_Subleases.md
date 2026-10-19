# 第11批 Animation：必要契约与验收入口

更新：2026-10-13。旧租约、逐轮过程、已结束门禁和重复状态已迁入[完整历史原文](Module_Repair_11_Subleases_History_20261013.md)。本页保留模块接缝与未核销的验收边界。

本批唯一活动需求记录为[有效排程](../../Coordination/Module_Repair_Parallel_Schedule.md)：[需求与验收](../../Coordination/Module_Repair_Parallel_Schedule.md#本批需求与验收)、[当前事实与必要前置](../../Coordination/Module_Repair_Parallel_Schedule.md#当前事实作者与必要前置)、[共享窗口](../../Coordination/Module_Repair_Parallel_Schedule.md#当前窗口与关键路径)。写入者与保护交接以该记录为准，稳定规则见[AGENTS.md](../../../AGENTS.md)。

## 共同冻结契约

- **职责与事实来源**：CMC执行胶囊位移／朝向；Animation从原Pawn／CMC／ASC只读Capture，生成本生命周期的姿态事实。Animation不增加运动执行器、第二套帧调度或反馈写入。原运动源区间、姿态求值时间和生命周期身份须可追溯，不能把无来源的零时间当有效样本。
- **生命周期**：[UGGYGOAnimInstanceBase](../../../Source/GGYGO/Animation/Runtime/GGYGOAnimInstanceBase.h)在初始化、反初始化和Owner变化时统一调用`ResetAnimationLifecycleState()`；先退役自有源绑定、清基类运行时与远端姿态消费状态，再调用`OnAnimationLifecycleReset()`。`A → nullptr → B`、弱引用失效和重复回调不得泄漏旧Owner状态。派生类清理`StateMemory`／`Snap`／当帧上下文与表现字段，`AnimSet`／`Tuning`等配置保留。
- **姿态与兼容边界**：姿态、起伏、脚和动画窗口归Animation；移动执行与GA资源权限仍归原作者。`WalkRunBlendAlpha`、`StopMotionType`、本地`X=Forward／Y=Right`及旧表现轴适配契约保留；`GaitBlendY`／`StopValue`等生产序列化字段的迁移需要实际消费者与资产证据。
- **Montage调用作用域**：[FGGYGOMontagePlayGuardScope](../../../Source/GGYGO/Animation/Runtime/GGYGOMontagePlayGuard.h)由Caller调用栈持有；Guard仅借用登记。生命周期失效不清空尚未退栈的Scope链，析构只注销原实例自身登记，不停止新Owner资源。ASC／Task／GA仍各自校验原播放身份、权限和释放责任。
- **只读阶段查询**：[TryGetCurrentMontagePlayGuardStage](../../../Source/GGYGO/Animation/Runtime/GGYGOMontageGuardAnimInstance.cpp)输入`CallerIdentity`，仅在GameThread核对最内Scope、登记、原Guard与生命周期身份；成功返回即时`OutNativeStage`／`bOutCompleted`副本，失败重置输出。无祖先回查、外部谓词调用、生命周期刷新或新增状态。外调后需重新核对原资源；`Returned`不等于ASC整个Super完成，`Completed`不等于来源发布，查询结果不授予Task／GA资源权限。
- **验证层**：Editor曲线DTO／Python只读副本、静态图文、构建、夹具专项、生产资产、自然Finalize、视觉及联机各自记证据。旧构建或静态冻结不能验收新源码或生产接线，失败和未运行不得改成成功。

## 未完成验收与有效依赖

- 生产ABP／AnimClass接线与作者互认、普通Slot A/B、整身姿态／双腿、真实CMC源区间同帧、自然Finalize以及listen／SimulatedProxy的当前缺口与承担者，统一查有效排程。R8节点更新／单位专项仅证明夹具消费契约，不能关闭这些生产验收。
- [C37未闭合边界](Module_Repair_11_Subleases_History_20261013.md#c37--animation-montage-guard主结构原子范围登记2026-10-01)保留查询消费者、生产AnimClass迁移、严格P1／网络及Task权限／来源验收；[C37图文交回](Module_Repair_11_Subleases_History_20261013.md#c37--guard主结构产物冻结及实际编辑方式交回2026-10-01)保留旧节点容量和Obsidian原生视觉未验。后续仅凭对应正式结果核销，不从图文产物推断完成。
- [C28失败传播及旧偏差](Module_Repair_11_Subleases_History_20261013.md#c28-a--11-curve-m1-a-拆分预检与授权2026-10-01)和[当时实际消费分支](Module_Repair_11_Subleases_History_20261013.md#c28-c--11-curve-m1-c-流程图原子步骤登记2026-10-01)原样保留。是否仍适用、已修复或已退役须按当前源码与正式证据确认，本次整理不重开旧实现，也不删除其验收边界。
- 动态验证沿原作者交付、生产接线及统筹共享窗口接续；有完整父保护交集的写入等相关段正常归还，无交集的所属工作可独立推进。

## 历史与证据导航

- [D6至C37完整原文](Module_Repair_11_Subleases_History_20261013.md)：包含旧租约、作者／过程、构建与专项门禁、旧失败、编辑方式及未验范围；历史不授当前权限。
- [专项验证记录](Module_Repair_11_Validation.md)：按准确阶段查旧报告；当前验收结论仍查有效排程。
- [原主结构布局记录](Module_Repair_11_MainStructureLayout.md)：保存图文布局和静态边界，图文视觉未验状态保留。

已结束过程继续归入历史，当前事实原位更新在唯一活动记录。本次正文迁移只完成文档减量，不构成业务或生产动画验收。
