# 第10批 Movement：契约与验收入口

整理：2026-10-13。旧租约、逐轮过程和已结束门禁已迁入同目录历史；本页只保留稳定契约、未完成验收和当前入口。文档整理不更新业务验收结论。

## 当前任务与验证入口

- 当前任务、唯一作者、有效写集、依赖及共享 UE／构建／Git 窗口，以[有效排程](../../Coordination/Module_Repair_Parallel_Schedule.md)为准。当前状态原位维护在排程，本页不复制逐轮进度。
- 源码／静态、生产接线、编译、专项、保存／Cold、PIE／视觉及联机分别查证。历史失败和旧门禁保留其原验证层；构建、夹具或离线合同通过不能升级为生产运行通过。
- 修复编号见[修复清单](../../Coordination/Module_Audit_Repair_Ledger.md)，原作者见[会话路由](../../Coordination/Module_Conversation_Routing.md)。历史租约不授权当前开工；独立写集仍须与执行者完整父保护核交集。

## 稳定职责与来源契约

- **权威与消费**：CMC 唯一负责移动请求准入、影响胶囊位移的步态／WalkRun／起停／TurnBack、相位与模拟时间，以及胶囊位移和 Yaw 执行。CurveRMS 消费原 CMC 求值结果，Animation 消费姿态事实；不建立第二套求值时钟、帧调度或胶囊执行链。GAS／Combat 保持各自生命周期及结算职责。
- **WalkRun 与命名**：`ABP_Pyrios` 的 WalkRun 使用 `BS_Pyrios_WalkRun` 单个 BlendSpace1D；单轴语义为 `WalkRunBlendAlpha`，`0 = Walk`、`1 = Run`。Movement 提供 `GetWalkRunBlendAlpha()`，Animation 将 `FGGYGOAnimationStateFrame` 映射至 AnimBP 的混合及 Stop 语义。旧 `GaitBlendY` 只留在序列化兼容边界，名称／引脚实际保存状态需资产回读证明。CMC 本地轴为 `X = Forward`、`Y = Right`，表现轴映射由 Animation 兼容层负责。
- **配置与曲线**：保留真实 Start／WalkRun 动画曲线速度包络，通用 C++ 不硬编码角色或招式参数；不以固定 WalkSpeed／RunSpeed 替换真实曲线，不恢复已退役曲线 DA。必需配置、绑定或曲线无效时明确拒绝、等待真实就绪或中止，并给出可定位诊断。
- **来源与资格**：输入、Origin、绑定、Prepared 和派生值保留原请求、资源身份、原 owner 及已接受配置。同名资源、同资产和当前后继不能替代原来源。`GetMovementOwnerSyncScope`／`QueryQualifiedMovementIntent` 提供原 owner 作用域和输入资格，消费方按实际结果决定，不读取 Movement 内部状态。
- **区间与回放**：Prepared 限于原区间和回放作用域；重复回放不额外推进计时。[完成区间快照](../../../Source/GGYGO/Character/Data/GGYGOMotionExecutionTypes.h)经原来源及当前／上一帧核验后只提供已完成运动事实，不授予执行或播放许可。SavedMove／NetworkMoveData／校正回放只传最小语义和时间，服务端按自身已接受配置与来源校验，不接受客户端资产、曲线或速度作为权威。
- **远端消费**：`GetMotionExecutionSnapshot()` 提供本地执行事实，`GetRemoteMotionPoseSnapshot()` 提供有来源与有效期的远端姿态事实；远端消费保持真实角色、源身份和时域，不新增动画时钟，不以无来源默认 0 冒充正常采样。
- **清理边界**：原来源退役、Reset、EndPlay 和回放结束按各自作用域清理本 CMC 自有上下文及派生引用，订阅按原句柄精确注销。清理幂等、保护后继，执行失败只影响原请求，不写成 Finished。`SetMovementSet` 切换／置空只清 Locomotion 自有状态并恢复 CMC 基线，不结束 ActionMotion／GAS 或其它模块资源。接口以[当前 CMC 声明](../../../Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h)为准。

## 未完成验收与有效依赖

以下边界仍须以有效排程中的正式证据关闭；本次整理没有新增运行证据。

| 验收线 | 必须保留的验收边界与依赖 |
| --- | --- |
| WalkRun／Run 与生产接线 | 真实玩家输入下合理切换已有 BlendSpace 的 Walk／Run，保留 camera-relative 行为、真实起步／走跑曲线和 Stop／TurnBack 分支；检查松开再按及原 owner 资格。源码、历史走跑样本及资产静态读回不代当前 Run 可见结果；AnimBP／BlendSpace 名称、引脚及配置保存由原资产作者核证。 |
| CMC 实际区间／全部 Yaw | 真实原生部分／零／补偿区间、失败与后继隔离、SavedMove／回放须有实际证据；TurnBack D0 按源时序真实转胶囊，D1 不重复，完整结束保朝向。同一原来源的 Anim 播放器、CMC 完成区间及自然 Finalize 要同帧，无漏转、重复、回摆或错帧。 |
| 整身倾斜／普通 Slot／生产 ABP | 方向夹角 20° 对应身体相对地面约 70°；60° 对应约 40～50°，直立为 90°。髋、膝、双腿需同帧可见；普通 Slot A/B、源播放器姿态和脚部表现须真实对照，生产 ABP 接线及写入者归属仍待原作者收敛。provider／pin／H1 维持冻结，Rendering 消费同源事实；SlotA 离线准入只允许尝试该场景，不能覆盖其余场景。 |
| 最小联机 | 完成既定 SimulatedProxy／listen 远端最小复现，使用真实 PlayerState／生产角色、实际网络角色和源采样时域；不得以夹具注入、快照模拟或猜测全局同帧替代。远端暂停、复制与观察证据须按真实宿主条件核验。 |
| 集中交付 | 本批运行、视觉和联机验收及已授范围内的保存／Cold 仍独立核证；已通过的六源／三 Montage 原地化不重烘焙。受影响模块／Obsidian 笔记和各仓 Git 由统筹在完整需求交付时集中安排。延期 Dodge GA／CMC 不因文档整理恢复。 |

当前共享关键路径、各层已验结果、正式证据和下一窗口统一查有效排程；上述边界不另开验证矩阵或独占 UE 窗口。

## 历史与追溯

迁移前完整原文已逐字节保存在[2026-10-13 历史正文](Module_Repair_10_Subleases_History_20261013.md)。其中旧租约、失败、逐轮身份、已结束门禁和旧接口交接均保留；历史中的未编译／未保存等状态只描述当时结果，当前状态需回到有效排程查证。

按需追溯[旧租约与门禁](Module_Repair_10_Subleases_History_20261013.md#历史租约与旧门禁)或[原共同冻结契约](Module_Repair_10_Subleases_History_20261013.md#共同冻结契约)。历史保全不表示其中业务、资产、PIE 或联机已经验收。
