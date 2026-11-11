# GGYGO 协作规则

中文交流、文档、注释和 commit；代码标识符及 UE 术语保持原文。本文只放常驻红线和入口，细则按场景读 `AAADocs/Rules/`。

## 常驻红线

- 权威状态唯一：BossAI 选招请求 GAS；GA 管能力生命周期；CMC 执行胶囊位移；Animation 管姿态及窗口；Combat 查询／去重命中；GA／GE／Execution／AttributeSet 结算伤害。不读写其它模块内部状态，不新增循环依赖或第二套帧调度。
- C++ 只做底层通用机制、接口、权限、校验和资源生命周期；顶层流程、表现层和具体 Boss／角色／招式逻辑用蓝图及可视化资产实现。
- 必需配置／资产无效时明确拒绝并诊断，不偷换默认值或成功结果。
- 只做当前需求及其必要依赖；修根因，不顺手重构。
- 一个需求一个负责人，端到端实现并自己编译自测；跨模块也不拆给多人。开工前在[看板](AAADocs/Coordination/Board.md)登记占用，只有同文件、同共享资产、同时构建才算冲突。
- 默认不发消息，只在阻塞、需要决定、交付时发；收到不用回确认。
- 需求歧义、玩法／输入／镜头行为、实质兼容选择、引擎修改或可能丢失现有工作时，给出场景和选项请用户决定。
- 不覆盖用户未保存工作，不 SaveAll。
- 父工程、Source/GGYGO 子仓、Obsidian 分别提交；只 stage 本需求的文件。

## 按场景读取

| 场景 | 文档 |
| --- | --- |
| 接需求、分配、并行、占用 UE／构建 | [TaskWorkflow](AAADocs/Rules/TaskWorkflow.md) |
| 改架构、跨模块、C++／蓝图分工 | [ArchitecturePrinciples](AAADocs/Rules/ArchitecturePrinciples.md) |
| 写代码、审代码 | [CodeConventions](AAADocs/Rules/CodeConventions.md) |
| 编译测试、验收、提交 | [VerificationDelivery](AAADocs/Rules/VerificationDelivery.md) |
| 写文档、同步 Obsidian、控制上下文 | [Documentation](AAADocs/Rules/Documentation.md) |
| 当前需求与占用 | [看板](AAADocs/Coordination/Board.md)、[会话路由](AAADocs/Coordination/Module_Conversation_Routing.md) |
