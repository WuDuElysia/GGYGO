# locomotion-gait-authority 实现总览

> 面向开发者的逻辑侧步态权威改造与最终交付说明。本文依据 `requirements.md`、`design.md`、`tasks.md` 以及 `Source/GGYGO/**` 范围内的实现核对整理。本文不读取、不修改 `Content/**`，也不把蓝图资产推断写成 C++ 实现事实。

## 1. 改造目标与最终架构

本 spec 将步态解析权收归逻辑侧唯一决策者 `FGaitAuthorityProcessor`。它在 `FIntentPipeline::ProcessGait`（Tick 第 3.5 步）中统一决定 `FRuntimeData::ResolvedGait`，并在同一阶段写入 `FAnimRuntimeData::Gait`。动画层通过 `FZZZAnimSnapshot::Gait` 消费该结果，不再自行维护另一套步态或 Walk→Run 计时规则。

最终步态规则为：

1. 正常移动的唯一初始步态是 `Walk`；
2. `Walk` 连续保持达到 `FMovementConfig::WalkToRunHoldSeconds`（默认 `5.0` 秒）后升级为 `Run`；
3. 后续闪避系统兑现 `bDodgeRunPending` 契约时，在仍有方向输入且未被阻止移动的帧直接进入 `Run`。

`EMovementGait` 只保留 `None`、`Walk`、`Run`，其中 `None` 表示当前无移动步态。Sprint 的步态、触发、动画分流和阈值镜像均已移除；`bSprintHeld`、`bForceWalkHeld`、`SetSprintHeld`、`IA_Sprint` 以及 `SprintSpeed` / `SprintMultiplier` 声明按兼容要求保留，但不参与新的步态解析。

### 1.1 Tick 数据流

```text
ArbiterPipeline::Process
  -> InputPipeline::Process
  -> FIntentPipeline::ProcessIntents
  -> FIntentPipeline::ProcessGait / FGaitAuthorityProcessor   [第 3.5 步]
  -> FIntentPipeline::ProcessParameters（Gait 阶段看门狗）
  -> StateManager::Update
  -> MotionDriver::Process
  -> UZZZAnimInstance::PipelineDrive
```

`ProcessGait` 位于 `ProcessIntents` 之后、`ProcessParameters` 之前，并早于 `MotionDriver::Process` 与 `PipelineDrive`。因此 MotionDriver 读取本帧的 `ResolvedGait`，动画快照读取本帧的 `AnimData.Gait`。

### 1.2 Gait Authority 固定七步

`FGaitAuthorityProcessor::Process` 按固定顺序执行：采样输入与边沿；解析 `DeltaTime`；解析基线步态；先归零再推进 `WalkHoldTimer`；按重新求值的有效阈值判断升级；一次性写入 `ResolvedGait` 与 `AnimData.Gait`；更新边沿基线。步骤三至五只操作局部 `FrameGait`，确保每帧对两个逻辑步态通道各至多一次落盘。

判定输入仅为移动输入是否存在、`CurrentState`、`bBlockMove` 与 `bDodgeRunPending`；不读取 `CurrentSpeed`、`AnimSpeed`、root motion、`VelocityLength`、`Velocity2DLength` 或 `FMotionDriver` 的 `WalkSpeedCap` / `RunSpeedCap`，速度上限缓存只由 MotionDriver 自身使用。计时器只存在于 `FGaitAuthorityProcessor::WalkHoldTimer`，范围自愈并保持在 `[0.0, 3600.0]`，不进入 `FRuntimeData`，也不参与 `ResetFrameIntents()`。

优先级为 `bBlockMove -> 无移动输入 -> bDodgeRunPending -> 既有 Run 且未发生离开 Moving 边沿 -> Walk`。无效帧间隔（负值或非有限值）时，Requirement 9.3 优先于归零条件：计时器保持不变，基线步态和升级判定仍照常执行，并输出节流诊断。`CurrentState` 在第 3.5 步观察到的是上一帧状态，这是设计已接受的一帧观察延迟；计时验证以 `WalkHoldTimer` 累计值为准，不以墙钟时间替代。

## 2. 关键数据与职责变化

### 2.1 RuntimeData 与 MotionDriver

`FRuntimeData` 不再包含 `FGaitThresholds`，因此不再有 `GaitThresholds` 速度上限镜像。`FMotionDriver` 改为在 `Init` 中从 `MovementConfig.WalkSpeed` 与 `MovementConfig.RunSpeed` 初始化私有缓存 `WalkSpeedCap`、`RunSpeedCap`；`Process` 与 `ProcessLocomotion` 均使用这两个缓存按 Walk/Run 两档设置速度上限。`DefaultMaxWalkSpeed`、`SetRootMotionMode(ERootMotionMode::IgnoreRootMotion)`、root motion 分支和 `ProcessRootMotionMovement` 保持既有边界，不在本 spec 内重构。

`FRuntimeData::bDodgeRunPending` 是跨帧闪避契约，初值为假，不在帧末意图重置中清零。当前 spec 内 `FGaitAuthorityProcessor` 是唯一读取方与唯一置假方，真正的置真方留给后续闪避 spec。

### 2.2 动画层

`FZZZAnimSnapshot::Gait` 是动画层唯一的步态输入，由 `FZZZAnimSnapshotCapture` 从 `FAnimRuntimeData::Gait` 直读。`FZZZAnimStateMemory` 最终仅保留 `GaitBlendY`，不再保留动画状态、进入步态、移动计时或 Sprint 触发记忆，也不再存在对应的状态入口写入链路。

`FZZZLocomotionEvents::EnterMoving` 依据 `Snapshot Gait == Run` 初始化 `GaitBlendY` 与 `LastGaitBlendTarget`，否则从 `0.0` 起步。`AdvanceGaitBlend` 依据 `Snapshot CurrentState == Moving` 判断是否处于 Moving；非 Moving 时执行既有的 `GaitBlendY` 与目标值复位语义。Moving 驻留期间 `Gait_None` 沿用上一帧目标值，`Run` 目标为 `1.0`，其他合法步态目标为 `0.0`，非法值只诊断、不改写快照源值，并按 Walk 目标处理。

Conduit 分流只读取 `Snapshot_Gait`：`Conduit_To_Moving_Direct` 在步态为 `Run` 时为真，`Conduit_To_EnterMove` 为其互补分支；上下文缺失时确定性地进入起步路径。两条判定均为 `const`，不修改动画记忆。

停止过渡由两个独立的 Blueprint 入口分别提供，但共享同一个 `FZZZLocomotionDecisions::ShouldStopMoving()` 底层判定：`Moving → Stop` 连接到 `UZZZAnimInstance::Locomotion_Moving_To_Stop()`，`EnterMove → Stop` 连接到 `UZZZAnimInstance::Locomotion_EnterMove_To_Stop()`。底层函数只在快照存在且 `Snapshot.bShouldMove == false` 时返回真，因此它们都是停止移动输入判定，不是速度为零判断，也不负责 `EnterMove → Moving` 的动画完成判断。

### 2.3 EnterMove → Moving 动画完成条件

EnterMove → Moving 的动画播放完成条件由 AnimBP 直接使用 `Time Remaining (ratio) <= 0` 处理，不需要 C++ 函数。

## 3. 文件映射与范围核对

### 3.1 新增文件（4 个）

| 编号 | 文件 | 内容 |
| --- | --- | --- |
| N1 | `Source/GGYGO/Public/Pipeline/Gait/GaitAuthorityProcessor.h` | `FGaitAuthorityProcessor` 声明、计时器、边沿基线和阈值常量 |
| N2 | `Source/GGYGO/Private/Pipeline/Gait/GaitAuthorityProcessor.cpp` | 七步处理、优先级、计时、升级、闪避契约消费和 `LogGait` 诊断 |
| N3 | `Source/GGYGO/Public/Pipeline/Gait/GaitLog.h` | `LogGait` 声明 |
| N4 | `Source/GGYGO/Private/Pipeline/Gait/GaitLog.cpp` | `LogGait` 唯一定义 |

### 3.2 修改条目（20 项）

| 编号 | 文件 | 最终修改范围 |
| --- | --- | --- |
| M1 | `Public/StateMachine/CharacterStateType.h` | 移除 `EMovementGait::Sprint`，保留 `None/Walk/Run` 顺序与数值 |
| M2 | `Public/Movement/MovementConfig.h` | 新增 `WalkToRunHoldSeconds`；保留 Sprint 配置声明 |
| M3 | `Public/Data/Logic/RuntimeData.h` | 新增 `bDodgeRunPending`；移除 `FGaitThresholds`；修正步态/速度注释 |
| M4 | `Public/Data/Anim/AnimRuntimeData.h` | 移除 `bSprintTrigger`，修正 `Gait` 注释 |
| M5 | `Public/Pipeline/IntentPipeline.h` | 新增 `ProcessGait`、Gait Authority 成员与阶段看门狗成员 |
| M6 | `Private/Pipeline/IntentPipeline.cpp` | 初始化并调用 Gait Authority，实现阶段看门狗 |
| M7 | `Public/Pipeline/Intents/LocomotionIntentProcessor.h` | 移除旧步态基线成员与无关包含 |
| M8 | `Private/Pipeline/Intents/LocomotionIntentProcessor.cpp` | 收缩为方向处理和 `bShouldMove` 同步，移除旧步态规则 |
| M9 | `Private/BaseCharacter.cpp` | 在 Tick 第 3 步后接入 `ProcessGait` |
| M10 | `Public/BaseCharacter.h` | 更新 `GetResolvedGait` 注释，移除 Sprint 描述 |
| M11 | `Private/Drivers/MotionDriver.cpp` | 移除 RuntimeData 阈值同步，使用 `WalkSpeedCap` / `RunSpeedCap` 两档缓存 |
| M12 | `Public/Animation/zzzAnim/Data/ZZZAnimSnapshot.h` | 移除 `bSprintTrigger`，保留快照 `Gait` |
| M13 | `Private/Animation/zzzAnim/Capture/ZZZAnimSnapshotCapture.cpp` | 移除 Sprint trigger 抓取，保留 `Gait` 唯一抓取 |
| M14 | `Public/Animation/zzzAnim/Data/ZZZAnimStateMemory.h` | 收缩为仅 `GaitBlendY`，移除其余动画状态、步态、计时与 Sprint 触发记忆字段/包含 |
| M15 | `Public/Animation/zzzAnim/Data/ZZZAnimTuning.h` | 移除 `WalkToRunHoldSeconds`，保留插值配置 |
| M16 | `Public/Animation/zzzAnim/Locomotion/ZZZLocomotionRules.h` | 移除旧步态规则和计时常量，保留 GaitBlend 规则 |
| M17 | `Private/Animation/zzzAnim/Locomotion/ZZZLocomotionRules.cpp` | 实现 Snapshot Gait 的正向 Run 目标映射和容错 |
| M18 | `Public/Animation/zzzAnim/Locomotion/ZZZLocomotionDecisions.h` + 对应 `.cpp` | 移除 Walk→Run 判定，改造 Conduit 分流判定，保留唯一 `ShouldStopMoving()` 停止逻辑供两个独立 Blueprint 入口转发 |
| M19 | `Public/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.h` + 对应 `.cpp` | 清理旧状态入口与 Sprint 事件链路，按 Snapshot Gait/CurrentState 推进 `GaitBlendY` |
| M20 | `Public/Animation/zzzAnim/ZZZAnimInstance.h` + 对应 `.cpp` | 清理旧状态入口与 Sprint 事件转发，更新快照刷新和 `AdvanceGaitBlend` 调用，新增 `Locomotion_Moving_To_Stop` 与 `Locomotion_EnterMove_To_Stop` 两个独立 Blueprint 转发入口 |

上述映射包含 4 个新增文件和 20 个修改条目；未把 `Content/**` 资产作为文件映射或 C++ 实现依据。

### 3.3 明确边界

`RootMotionParameterProcessor.cpp`、`DodgeIntentProcessor.cpp`、旧 NTE 动画层 `UNTEAnimInstance` 与 `Animation/Decisions/**`、GAS 仲裁、状态集合及 Dodge Tag 定义均不属于本次新增实现。闪避契约的写入方、root motion 重构和蓝图资产拓扑均留在各自后续范围。

## 4. 验证状态与最终结论

### 4.1 任务 9.1 静态检查

任务 9.1 的静态检查范围限定为 `Source/GGYGO/**`，结论如下：

- **A 组：通过。** 唯一写入方、单一数据源、`GaitBlendY` 唯一写入方和闪避契约读取/置假边界符合核对项。
- **B 组：通过。** Sprint 枚举、阈值字段、Sprint trigger 链路和旧 Sprint Conduit 符号清理符合核对项；兼容输入字段与 Sprint 配置声明保留且无新的读取方。
- **C 组：部分结论。** C6/C7 未做与历史版本的逐字对照，因此不写成 C 组全部通过；其余已执行的当前源码结构核对按核对结果记录。
- **D 组：通过。** Tick 时序、接口稳定性、七步顺序、速度字段解耦和帧末意图重置边界符合核对项。
- **E 组：存在既有范围/边界限制。** E1、E8、E9 属于 root motion 文件、旧 NTE 动画边界和既有工作树改动集合的历史/范围问题，不归因于本次文档或新改造。
- **F 组：通过。** 两档速度映射、入口初始化、配置字段默认值/钳制、初值和 root motion 保留项符合核对项。

因此 9.1 的总体表述为：**A、B、D、F 静态检查通过；C6/C7 未做历史逐字对照；E1/E8/E9 为既有工作树范围/边界限制。** 这不是代理编译结论。

### 4.2 任务 9.6 收尾核对

9.6 的 Source-only 静态核对已通过，核对范围仅为 `Source/GGYGO/**`：

- `FRuntimeData` 不再有 `GaitThresholds`；`FMotionDriver` 使用由 `MovementConfig.WalkSpeed` / `.RunSpeed` 初始化的私有 `WalkSpeedCap` / `RunSpeedCap`；
- `FZZZAnimStateMemory` 仅保留 `GaitBlendY`；动画状态入口记忆及相关链路已移除；
- `EnterMoving` 依据 `Snapshot Gait` 初始化，`AdvanceGaitBlend` 依据 `Snapshot CurrentState` 判断 Moving；
- 删除符号、缓存初始化/使用点及相关注释引用完成一致性核对。

9.6 **未执行编译或测试**；此处“通过”仅指 Source-only 静态核对通过。

### 4.3 用户确认的检查点与未执行项目

- **任务 7**：本地 C++ 编译由用户确认通过；本文不把代理执行的静态核对写成代理编译。
- **蓝图**：用户完成一个函数绑定修改，并确认编译通过。本次代理未读取 `Content/**`，不声称具体资产路径、节点或额外蓝图拓扑修改。
- **可选任务 9.2–9.5**：未执行，未标记完成，也不声称运行过属性测试或其他测试。
- **测试声明**：本次最终收尾未运行测试。

### 4.3.1 Requirement 17.4–17.9 验证用例采集矩阵

以下 U1–U6 仅记录当前采集边界，不把静态核对写成运行测试：

| 用例 | 覆盖内容 | 当前结果 |
| --- | --- | --- |
| U1 / 17.4 | 无闪避契约、输入由无到有时首帧为 `Walk` | 未运行运行期用例；静态结构/初值与优先级核对包含于 9.1 F 组，待本地行为验证 |
| U2 / 17.5 | 累计 `4.9` 秒为 `Walk`、达到 `5.0` 秒为 `Run` | 未运行运行期用例；计时逻辑已完成 Source-only 静态核对，判定基准为 `Walk_Hold_Timer`，待本地行为验证 |
| U3 / 17.6 | 无输入、阻止移动、非 Moving 状态分别使计时归零 | 未运行运行期用例；归零分支已纳入 9.1 D/F 静态核对，待本地行为验证 |
| U4 / 17.7 | `Run` 在持续移动观察窗口内不回落 | 未运行运行期用例；Run 保持逻辑已纳入 9.1 A/D/F 静态核对，待本地行为验证 |
| U5 / 17.8 | 闪避契约为真且有输入时进入 `Run` 并消费契约 | 未运行运行期用例；契约读取/置假边界已纳入 9.1 A/F 静态核对，待后续闪避写入方接入后本地验证 |
| U6 / 17.9 | 改变速度类字段不改变步态解析结果 | 未运行运行期用例；速度字段零读取约束已纳入 9.1 D 静态核对，待本地行为验证 |

### 4.4 已知设计取舍

1. `CurrentState` 的一帧观察延迟已接受：Gait 阶段先于 `StateManager::Update`，因此 Walk 计时起点相对方向输入最多晚一帧，墙钟阈值时刻最多晚 `0.1` 秒；U2 类判定以 `Walk_Hold_Timer` 累计值而非墙钟时长为基准。
2. 无效帧间隔时 Requirement 9.3 优先于全部归零条件：该帧不修改计时器，基线步态仍照常解析并记录诊断。
3. 阶段一曾暂时存在旧处理器与 Gait Authority 的双写入方；该临时状态已在阶段二移除，最终唯一写入方约束成立。

## 5. 任务状态收尾

任务 1、2、5、6、7、9.1、9.6 已完成。任务 10、11.1、11.2 已完成。任务 4 与任务 8 的既有顶层状态不改变；其已记录的子任务状态也不改变。可选任务 9.2、9.3、9.4、9.5 保持未完成/未执行。

## 6. 后续蓝图处理清单（按用户确认收敛）

蓝图的 `Moving → Stop` 过渡绑定 `Locomotion_Moving_To_Stop()`，`EnterMove → Stop` 过渡绑定 `Locomotion_EnterMove_To_Stop()`；两个函数都直接转发 `LocomotionDecisions.ShouldStopMoving()`，共享唯一的停止移动输入判定。该底层判定仅在 `Snapshot.bShouldMove == false` 且快照存在时为真。`EnterMove → Moving` 的动画播放完成条件仍由 AnimBP 直接使用 `Time Remaining (ratio) <= 0` 处理，不需要 C++ 函数。

## 7. 仍需用户决定的事项

- 是否在后续测试 spec 中补做可选属性测试 9.2–9.5；本次不将其视为交付阻塞项。
- 后续闪避系统何时、由何处写入 `bDodgeRunPending`；本 spec 仅提供契约和消费方。
- 如需进一步蓝图运行期拓扑或 PIE 行为复核，由用户在编辑器中决定范围；本次不读取 `Content/**`。
