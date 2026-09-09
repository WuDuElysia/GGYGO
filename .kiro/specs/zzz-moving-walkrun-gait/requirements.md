# Requirements Document

## Introduction

本功能在新版 ZZZ 动画层（`UZZZAnimInstance` + ZZZ AnimBP）中固定 `Moving` 子状态机内部的 Walk/Run 步态机制，并明确冲刺触发开关的消费边界。

范围限定在 `Animation/zzzAnim/` 下的新版链路：`FRuntimeData::AnimData` → `FZZZAnimSnapshotCapture` → `FZZZAnimSnapshot` → `FZZZLocomotionDecisions` / `FZZZLocomotionEvents` → `FZZZAnimStateMemory` → ZZZ AnimBP。本功能不扩展旧 `UNTEAnimInstance`、旧 `Animation/Decisions` 模块，也不改动 `FIntentPipeline` 的公开接口。

核心机制包括四点：`Moving` 子状态机只有 `WalkRun` 与 `TurnBack` 两个状态；Walk 与 Run 不拆成独立动画状态，共用同一个 BlendSpace，由 Y 参数表达 walk ↔ run 的插值；Run 只有两个触发来源（闪避后经 `Conduit → Moving` 进入即为 Run、`WalkRun` 内 Walk 持续超过阈值时长自动升 Run）；冲刺触发开关只在 `Conduit → Moving` 这条路上消费，`EnterMove → Moving` 不消费。

## Glossary

- **ZZZ_Animation_Layer**：以 `UZZZAnimInstance` 为 C++ 决策载体、ZZZ AnimBP 为蓝图消费端的新版动画层。
- **UZZZAnimInstance**：新版动画实例类，只保留 AnimBP 可调用的 `UFUNCTION` 转发与每帧上下文刷新调度，不承载具体判定或记忆写入逻辑。
- **ZZZ_Locomotion_Decisions**：`FZZZLocomotionDecisions`，只读判断过渡条件的模块；其函数为 `const`，只读 `ZZZAnimSnapshot` 与 `ZZZAnimStateMemory`，不产生副作用。
- **ZZZ_Locomotion_Events**：`FZZZLocomotionEvents`，处理 AnimBP `On Entry` 事件与跨帧记忆写入的模块。
- **ZZZAnimSnapshot**：`FZZZAnimSnapshot` 每帧只读快照，由 `FZZZAnimSnapshotCapture` 从 `FRuntimeData::AnimData` 抓取。
- **ZZZAnimStateMemory**：`FZZZAnimStateMemory` 动画状态机跨帧记忆；现有字段为 `PreviousState`、`EnteredGait`、`bSprintTriggerPending`。
- **Locomotion_StateMachine**：ZZZ AnimBP 的 Locomotion 顶层状态机，状态集合为 `NotMoving` / `Conduit` / `EnterMove` / `Moving`（对应 `EZZZAnimLocomotionState`）。
- **Moving_State**：`Locomotion_StateMachine` 中的 `Moving` 顶层状态，其内部实现为 `Moving_SubStateMachine`。
- **Moving_SubStateMachine**：`Moving_State` 内部的子状态机，状态集合为 `WalkRun_State` 与 `TurnBack_State`。
- **WalkRun_State**：`Moving_SubStateMachine` 的入口状态，同时承载 Walk 与 Run 两种表现，采样单一 `WalkRun_BlendSpace`。
- **TurnBack_State**：`Moving_SubStateMachine` 中的转身状态，仅由 `WalkRun_State` 进入并仅返回 `WalkRun_State`。
- **WalkRun_BlendSpace**：`WalkRun_State` 采样的唯一 BlendSpace 资产，从 `FZZZAnimSet::BlendSpaces` 按固定 key 查询。
- **GaitBlendY**：`WalkRun_BlendSpace` 的 Y 轴输入值，取值区间 `[0.0, 1.0]`；`0.0` 表示纯 Walk 采样，`1.0` 表示纯 Run 采样。
- **MovingGait**：`Moving_State` 内部的有效步态，取值域为 `EMovementGait::Walk` 与 `EMovementGait::Run`，作为 `GaitBlendY` 的目标值来源。
- **WalkHoldSeconds**：`MovingGait` 为 `Walk` 期间累计的连续行走时长（秒），存于 `ZZZAnimStateMemory`。
- **WalkToRunHoldSeconds**：Walk 自动升 Run 的时长阈值（秒），默认值 `5.0`，在 `FZZZAnimTuning` 中配置。
- **GaitBlendInterpSpeed**：`GaitBlendY` 向目标值收敛的插值速率（单位 1/秒），在 `FZZZAnimTuning` 中配置。
- **Effective_WalkToRunThreshold**：本次判定实际生效的 Walk 升 Run 阈值；`WalkToRunHoldSeconds` 为有限值且大于 `0.0` 时取该配置值，否则取默认值 `5.0` 秒。
- **Frame_Delta_Seconds**：`Context_Refresh` 传入的本帧时间增量（秒），参与计时与插值前先钳制到 `[0.0, 0.1]` 闭区间。
- **Snapshot_Gait**：`FZZZAnimSnapshot::Gait`，由 `FLocomotionIntentProcessor` 每帧解析写入的实时输入步态。
- **SprintTriggerPulse**：`FAnimRuntimeData::bSprintTrigger`，由 `FLocomotionIntentProcessor` 在步态升到 `Sprint` 的那一帧产生的上升沿单帧脉冲。
- **SprintTriggerPending**：`FZZZAnimStateMemory::bSprintTriggerPending`，对 `SprintTriggerPulse` 的跨帧锁存标记。
- **Sprint_Entry_Path**：`Conduit → Moving` 过渡路径，即"闪避触发且有移动输入"时进入 `Moving_State` 的路径。
- **Normal_Entry_Path**：`EnterMove → Moving` 过渡路径，即经起步动画进入 `Moving_State` 的路径。
- **Context_Refresh**：`UZZZAnimInstance::RefreshDecisionContext()` 每帧一次的上下文刷新流程，负责抓取快照、锁存脉冲、推进跨帧记忆、注入决策与事件上下文。
- **Unreal_Environment_Diagnostic**：因 Unreal Header Tool、模块 include path 或编辑器索引未加载 Unreal 头文件而产生的诊断信息，例如 `CoreMinimal.h`、`UFUNCTION`、`UPROPERTY`、`TMap` 未识别。

## Requirements

### Requirement 1: Moving 子状态机结构与状态职责

**User Story:** 作为动画程序员，我想让 `Moving` 内部只保留 `WalkRun` 与 `TurnBack` 两个状态，以便步态表现集中在单一状态中，拓扑保持最小。

#### Acceptance Criteria

1. THE `Moving_State` SHALL 以 `Moving_SubStateMachine` 实现，且该子状态机的状态集合恰好为 `WalkRun_State` 与 `TurnBack_State` 这 2 个状态，不含第 3 个动画状态，也不含额外的嵌套子状态机。
2. WHEN `Locomotion_StateMachine` 进入 `Moving_State`, THE `Moving_SubStateMachine` SHALL 以 `WalkRun_State` 作为唯一入口状态，使该次驻留的第 1 帧内 `WalkRun_State` 权重为 `1.0`、`TurnBack_State` 权重为 `0.0`。
3. THE `TurnBack_State` SHALL 只有 1 条入边且其源状态为 `WalkRun_State`，只有 1 条出边且其目标状态为 `WalkRun_State`；不存在由 `Moving_SubStateMachine` 的 Entry 或 `Locomotion_StateMachine` 其他状态直接进入 `TurnBack_State` 的路径。
4. THE `Moving_SubStateMachine` SHALL 把 Walk 与 Run 的姿态表现全部放在 `WalkRun_State` 中，不为 Walk 或 Run 新增独立动画状态，且 Walk 与 Run 之间的变化不产生 `Moving_SubStateMachine` 的状态切换。
5. WHILE `Moving_SubStateMachine` 处于 `WalkRun_State`, THE `WalkRun_State` SHALL 以单次 `WalkRun_BlendSpace` 采样输出姿态，其 Walk 与 Run 采样权重均落在 `[0.0, 1.0]` 闭区间且权重之和恒为 `1.0`，并由 `GaitBlendY` 唯一决定：`GaitBlendY` 为 `0.0` 时 Walk 权重为 `1.0`，为 `1.0` 时 Run 权重为 `1.0`，取 `(0.0, 1.0)` 内取值时两者权重同时大于 `0.0`。
6. THE `ZZZ_Animation_Layer` SHALL 保持 `EZZZAnimLocomotionState` 现有取值 `None` / `NotMoving` / `Conduit` / `EnterMove` / `Moving` 的语义与数量不变，`Moving_SubStateMachine` 的内部状态不并入该枚举，且在 `Moving_State` 整个驻留期间（含处于 `TurnBack_State` 期间）该枚举保持 `Moving`。
7. IF 在 `Moving_State` 驻留的第 1 帧出现指向 `TurnBack_State` 的进入请求, THEN THE `Moving_SubStateMachine` SHALL 保持处于 `WalkRun_State` 并忽略该请求，直到 `WalkRun_State` 至少完整更新 1 帧后才允许进入 `TurnBack_State`。
8. WHEN `Locomotion_StateMachine` 离开 `Moving_State`, THE `Moving_SubStateMachine` SHALL 丢弃本次驻留的内部状态，并在下一次进入 `Moving_State` 时重新以 `WalkRun_State` 为入口状态，不沿用上一次驻留的内部状态残留。

### Requirement 2: WalkRun 单状态与共用 BlendSpace

**User Story:** 作为动画程序员，我想让 Walk 与 Run 共用同一个 BlendSpace 并由 Y 参数插值，以便消除走跑之间的状态切换突变。

#### Acceptance Criteria

1. WHILE `Moving_SubStateMachine` 处于 `WalkRun_State`, THE `WalkRun_State` SHALL 采样唯一的 `WalkRun_BlendSpace`（同时参与混合的 BlendSpace 资产数量恒为 `1`），并以 `GaitBlendY` 作为其 Y 轴输入，Y 轴输入取值恒等于当帧 `GaitBlendY` 且落在 `[0.0, 1.0]` 闭区间内。
2. THE `ZZZ_Animation_Layer` SHALL 通过 `UZZZAnimInstance::GetBlendSpaceByKey` 以单一编译期常量 key 从 `FZZZAnimSet::BlendSpaces` 查询 `WalkRun_BlendSpace` 资产；该 key SHALL 不随 `MovingGait`、`GaitBlendY`、`Snapshot_Gait` 或 `Moving_SubStateMachine` 的当前状态变化，且该查询 SHALL 为只读，不新增、不改写、不移除 `FZZZAnimSet::BlendSpaces` 中的任何条目。
3. IF `FZZZAnimSet::BlendSpaces` 中不存在该 key 对应的资产, THEN THE `ZZZ_Animation_Layer` SHALL 返回空资产指针，并同时满足以下四项：`Moving_SubStateMachine` 保持在 `WalkRun_State` 不因资产缺失而切换状态；`ZZZAnimStateMemory` 中 `MovingGait`、`WalkHoldSeconds`、`SprintTriggerPending` 的取值保持不变；`GaitBlendY` 仍按 Requirement 7 定义的插值规则推进且计算结果恒落在 `[0.0, 1.0]` 闭区间；输出一条指明该 key 在 `FZZZAnimSet::BlendSpaces` 中缺失的诊断信息，且在 `Locomotion_StateMachine` 的同一次 `Moving_State` 驻留期间该诊断信息至多输出一次。
4. WHEN `MovingGait` 在 `WalkRun_State` 持续期间从 `Walk` 变为 `Run`, THE `Moving_SubStateMachine` SHALL 保持在 `WalkRun_State` 内，不触发状态切换、不重新执行 `WalkRun_State` 的 `On Entry`、不重置 `GaitBlendY` 为 `0.0`，且不中断当前 `WalkRun_BlendSpace` 的采样。
5. THE `WalkRun_State` SHALL 对 `GaitBlendY` 在 `[0.0, 1.0]` 闭区间内的任意取值给出确定的 `WalkRun_BlendSpace` 采样结果，用于表达 walk ↔ run 之间的全部中间表现；THE `WalkRun_State` SHALL NOT 为 walk ↔ run 之间的切换新增独立过渡动画序列、独立过渡状态或独立过渡通知。
6. WHEN `Moving_SubStateMachine` 进入 `WalkRun_State`, THE `ZZZ_Animation_Layer` SHALL 执行一次 `WalkRun_BlendSpace` 查询，并在 `Locomotion_StateMachine` 的该次 `Moving_State` 驻留期间沿用同一资产引用，不因 `MovingGait` 变化而重新选择其他资产。
7. WHILE `Moving_SubStateMachine` 处于 `WalkRun_State` 且 `MovingGait` 在相邻两帧之间发生变化, THE `GaitBlendY` SHALL 在相邻两帧之间的变化量绝对值不超过 `GaitBlendInterpSpeed` 与 `Frame_Delta_Seconds` 之积；WHERE Requirement 4 第 2 条或 Requirement 7 第 8 条定义的直接置值情形成立, THE `GaitBlendY` SHALL 允许单帧直接达到目标值。

### Requirement 3: Moving 内部有效步态语义

**User Story:** 作为动画程序员，我想让 `Moving` 内部步态与实时输入步态解耦，以便 Run 只由约定的两种来源产生，速度波动不会改变步态。

#### Acceptance Criteria

1. THE `ZZZAnimStateMemory` SHALL 提供 `MovingGait` 跨帧字段，其取值域恰为 `EMovementGait::Walk` 与 `EMovementGait::Run` 两个值，默认值为 `EMovementGait::Walk`，并以 `BlueprintReadOnly` 暴露给 AnimGraph 读取。
2. WHILE `Locomotion_StateMachine` 处于 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 只在以下三处写入 `MovingGait`：Requirement 4 定义的 `Sprint_Entry_Path` 进入初始化、Requirement 4 定义的 `Normal_Entry_Path` 进入初始化、Requirement 5 定义的 Walk 持续时长达到 `Effective_WalkToRunThreshold` 的升级；并且每次 `Context_Refresh` 中对 `MovingGait` 至多写入一次。
3. WHILE `MovingGait` 为 `Walk` 且 `Snapshot_Gait` 为 `EMovementGait::Run` 或 `EMovementGait::Sprint`, THE `MovingGait` SHALL 保持 `Walk`、`GaitBlendY` 的目标值 SHALL 保持 `0.0`，直到满足 Requirement 4 或 Requirement 5 定义的升级条件。
4. WHILE `Locomotion_StateMachine` 处于 `Moving_State` 的同一次驻留期间（自该次进入 `Moving_State` 的 `On Entry` 起，至离开 `Moving_State` 为止）, THE `MovingGait` SHALL 至多发生一次从 `Walk` 到 `Run` 的单向变化，且在该次驻留期间不从 `Run` 回落到 `Walk`；该单向约束的作用范围限定在该次驻留期间，不跨越 `Moving_State` 之外。
5. WHEN `Locomotion_StateMachine` 再次进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 按 Requirement 4 定义的进入路径规则独立重新计算 `MovingGait` 的初始取值，不沿用上一次驻留的残留取值；WHERE 独立计算结果与上一次驻留取值相同, THE `MovingGait` SHALL 允许取相同值。
6. THE `MovingGait` SHALL 作为 `ZZZAnimStateMemory` 的动画层跨帧记忆存在，不写回 `FRuntimeData` 或 `FAnimRuntimeData`；THE `ZZZ_Locomotion_Decisions` SHALL 只读取 `MovingGait`，不修改该字段。
7. IF `Locomotion_StateMachine` 进入 `Moving_State` 时既不能判定为 `Sprint_Entry_Path` 也不能判定为 `Normal_Entry_Path`, THEN THE `ZZZ_Locomotion_Events` SHALL 将 `MovingGait` 初始化为 `EMovementGait::Walk`、`GaitBlendY` 置为 `0.0`，并保持 `SprintTriggerPending` 的取值不变。
8. IF `MovingGait` 被读取到 `EMovementGait::Walk` 与 `EMovementGait::Run` 之外的取值, THEN THE `ZZZ_Locomotion_Events` SHALL 将该字段纠正为 `EMovementGait::Walk` 并按 `Walk` 参与后续判定，且不向该字段写入取值域之外的值。

### Requirement 4: Run 触发来源一（闪避后经 Conduit 进入）

**User Story:** 作为动画程序员，我想让闪避后直连的移动进入时即为 Run，以便闪避接跑的手感立即成立。

#### Acceptance Criteria

1. WHEN `Locomotion_StateMachine` 经 `Sprint_Entry_Path` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 在该次进入对应的 `On Entry` 中将 `MovingGait` 初始化为 `EMovementGait::Run`，并对同一进入事件只执行一次该初始化。
2. WHEN `Locomotion_StateMachine` 经 `Sprint_Entry_Path` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 将 `GaitBlendY` 直接置为 `1.0`，使该次进入后第一帧读取到的 `GaitBlendY` 与 `1.0` 之差的绝对值不超过 `0.001`，不经过按 `Frame_Delta_Seconds` 的推进过程。
3. WHEN `Locomotion_StateMachine` 经 `Sprint_Entry_Path` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 将 `WalkHoldSeconds` 置为 `0.0`。
4. THE `ZZZ_Locomotion_Decisions` SHALL 保持 `Conduit_To_Moving_Sprint()` 的判定条件为 `SprintTriggerPending` 为真这一唯一条件，SHALL NOT 读取 `FZZZAnimSnapshot::VelocityLength`、`Snapshot_Gait`、`FRuntimeData::CurrentSpeed` 或 `FRuntimeData::GaitThresholds`，并保持该函数为 `const` 且不修改任何记忆字段。
5. WHEN `Locomotion_StateMachine` 经 `Normal_Entry_Path` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 将 `MovingGait` 初始化为 `EMovementGait::Walk`。
6. WHEN `Locomotion_StateMachine` 经 `Normal_Entry_Path` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 将 `GaitBlendY` 置为 `0.0`。
7. WHEN `Locomotion_StateMachine` 经 `Normal_Entry_Path` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 将 `WalkHoldSeconds` 置为 `0.0`。
8. IF `Locomotion_StateMachine` 经 `Sprint_Entry_Path` 进入 `Moving_State` 时 `FZZZAnimSnapshot::bShouldMove` 为假, THEN THE `ZZZ_Locomotion_Events` SHALL 仍按本需求第 1 至第 3 条完成初始化，并由 Requirement 6 第 4 条在后续 `Context_Refresh` 中处理 `WalkHoldSeconds` 的重置。

### Requirement 5: Run 触发来源二（Walk 持续超过阈值）

**User Story:** 作为动画程序员，我想让持续行走超过阈值时长后自动升为 Run，以便长距离移动自然过渡到跑步。

#### Acceptance Criteria

1. WHEN 某次 `Context_Refresh` 在完成 Requirement 6 定义的 `WalkHoldSeconds` 推进之后满足 `MovingGait` 为 `Walk` 且 `WalkHoldSeconds` 大于或等于 `Effective_WalkToRunThreshold`, THE `ZZZ_Locomotion_Events` SHALL 在该次 `Context_Refresh` 内将 `MovingGait` 置为 `EMovementGait::Run`，且每次 `Context_Refresh` 至多执行一次该置值。
2. WHEN `MovingGait` 因 Walk 持续时长达到 `Effective_WalkToRunThreshold` 而变为 `Run`, THE `ZZZ_Locomotion_Events` SHALL 在该帧将 `WalkHoldSeconds` 置为 `0.0`，并在其后 `MovingGait` 保持 `Run` 的每一帧使 `WalkHoldSeconds` 的推进量为 `0.0` 秒。
3. WHEN `MovingGait` 因 Walk 持续时长达到 `Effective_WalkToRunThreshold` 而变为 `Run`, WHERE `GaitBlendInterpSpeed` 大于 `0.0`, THE `ZZZ_Animation_Layer` SHALL 以该帧的 `GaitBlendY` 取值为插值起点、按 Requirement 7 定义的规则向 `1.0` 收敛，不在该变更帧把 `GaitBlendY` 直接跳变为 `1.0`，并在与 `1.0` 之差的绝对值小于或等于 `0.001` 时结束收敛。
4. THE `ZZZ_Locomotion_Decisions` SHALL 提供一个 `const` 判定函数，返回 `MovingGait` 为 `Walk` 且 `WalkHoldSeconds` 大于或等于 `Effective_WalkToRunThreshold` 的合取结果；该函数 SHALL 只读取 `MovingGait`、`WalkHoldSeconds` 与 `WalkToRunHoldSeconds`，SHALL NOT 修改 `MovingGait`、`WalkHoldSeconds`、`GaitBlendY` 或 `SprintTriggerPending`，并使同一帧内的重复调用返回一致结果。
5. WHILE `MovingGait` 为 `Run`, THE `ZZZ_Locomotion_Events` SHALL 保持 `MovingGait` 为 `Run`、`GaitBlendY` 目标值保持 `1.0`、`WalkHoldSeconds` 保持 `0.0`，且不重置当前 `GaitBlendY`、不重新起算插值、不改写 `SprintTriggerPending`。
6. THE `ZZZ_Locomotion_Events` SHALL 只在 Requirement 4 或 Requirement 5 定义的触发来源成立时把 `MovingGait` 置为 `Run`，两个来源共享 `MovingGait` 为 `Run` 这一唯一结果表示，且不存在第三种置为 `Run` 的途径。
7. WHILE `Moving_SubStateMachine` 处于 `TurnBack_State` 且 `MovingGait` 为 `Walk` 且 `WalkHoldSeconds` 大于或等于 `Effective_WalkToRunThreshold`, THE `ZZZ_Locomotion_Events` SHALL 按本需求第 1 至第 3 条将 `MovingGait` 置为 `Run` 并将 `WalkHoldSeconds` 置为 `0.0`，且不因处于 `TurnBack_State` 而延后该升级。
8. IF `MovingGait` 为 `Run` 且 `WalkHoldSeconds` 大于 `0.0`, THEN THE `ZZZ_Locomotion_Events` SHALL 将 `WalkHoldSeconds` 置为 `0.0`，并且不重复触发本需求定义的升级效果。

### Requirement 6: Walk 持续计时的推进与重置

**User Story:** 作为动画程序员，我想让 Walk 计时的起点、推进与重置条件完全确定，以便 5 秒阈值可复现验证。

#### Acceptance Criteria

1. WHILE `Locomotion_StateMachine` 处于 `Moving_State`、`Moving_SubStateMachine` 处于 `WalkRun_State`、`MovingGait` 为 `Walk` 且 `FZZZAnimSnapshot::bShouldMove` 为真, THE `ZZZ_Locomotion_Events` SHALL 以 `Frame_Delta_Seconds` 累加 `WalkHoldSeconds`，其中 `Frame_Delta_Seconds` 取 `Context_Refresh` 传入的帧间隔秒数并先钳制到 `[0.0, 0.1]` 闭区间。
2. THE `ZZZ_Locomotion_Events` SHALL 在每次 `Context_Refresh` 中对 `WalkHoldSeconds` 至多推进一次 `Frame_Delta_Seconds`。
3. WHILE `Moving_SubStateMachine` 处于 `TurnBack_State`, THE `ZZZ_Locomotion_Events` SHALL 暂停累加 `WalkHoldSeconds`，并在该字段取值处于 `[0.0, 3600.0]` 闭区间内的任意情形下保留其已累计取值而不清零。
4. WHILE `Locomotion_StateMachine` 处于 `Moving_State` 且 `FZZZAnimSnapshot::bShouldMove` 为假, THE `ZZZ_Locomotion_Events` SHALL 将 `WalkHoldSeconds` 置为 `0.0`；WHEN `FZZZAnimSnapshot::bShouldMove` 由假恢复为真, THE `ZZZ_Locomotion_Events` SHALL 从 `0.0` 重新起算 `WalkHoldSeconds`。
5. WHEN `Locomotion_StateMachine` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 在该次进入的 `On Entry` 中将 `WalkHoldSeconds` 置为 `0.0` 作为计时起点，且该动作对 `Sprint_Entry_Path` 与 `Normal_Entry_Path` 两条进入路径均适用。
6. WHILE `Locomotion_StateMachine` 处于 `NotMoving`、`Conduit` 或 `EnterMove`, THE `ZZZ_Locomotion_Events` SHALL 保持 `WalkHoldSeconds` 为 `0.0`。
7. THE `WalkHoldSeconds` SHALL 恒落在 `[0.0, 3600.0]` 闭区间内，超出上界时钳制为 `3600.0`，并在 `MovingGait` 为 `Run` 期间保持 `0.0`。
8. IF `Context_Refresh` 传入的帧间隔秒数为负值或非有限数值, THEN THE `ZZZ_Locomotion_Events` SHALL 不推进 `WalkHoldSeconds`，保持其当前取值不变，并输出一条指明该帧间隔取值无效的诊断信息。
9. WHILE `MovingGait` 为 `Walk` 且累计推进量处于 `[0.0, Effective_WalkToRunThreshold)` 区间, THE `MovingGait` SHALL 保持 `Walk`；WHEN 累计推进量首次达到或超过 `Effective_WalkToRunThreshold`, THE `MovingGait` SHALL 在此后 `0.1` 秒内变为 `Run`。

### Requirement 7: BlendSpace Y 参数的驱动来源与平滑

**User Story:** 作为动画程序员，我想让 Y 参数由离散步态目标值经固定速率插值驱动，以便既没有走跑生硬跳变，也没有速度抖动传导到中间值。

#### Acceptance Criteria

1. THE `GaitBlendY` SHALL 以 `MovingGait` 为唯一目标值来源：`MovingGait` 为 `Walk` 时目标值为 `0.0`，`MovingGait` 为 `Run` 时目标值为 `1.0`。
2. THE `GaitBlendY` SHALL NOT 由 `FZZZAnimSnapshot::VelocityLength`、`FRuntimeData::CurrentSpeed`、`FRuntimeData::GaitThresholds` 或 `Snapshot_Gait` 直接映射。
3. WHILE `GaitBlendY` 与其目标值之差的绝对值大于 `0.001`, THE `ZZZ_Locomotion_Events` SHALL 在每次 `Context_Refresh` 中对 `GaitBlendY` 至多推进一次：以 `GaitBlendInterpSpeed` 为速率、按 `Frame_Delta_Seconds` 把 `GaitBlendY` 向目标值推进，本帧变化量的绝对值不超过 `|目标值 − 本帧起始值|`，且推进后不越过目标值。
4. THE `ZZZ_Locomotion_Events` SHALL 在每次 `Context_Refresh` 推进之前，把目标值与 `GaitBlendY` 的本帧起始值分别钳制到 `[0.0, 1.0]` 闭区间，并使推进后的 `GaitBlendY` 仍落在 `[0.0, 1.0]` 闭区间内。
5. WHEN `GaitBlendY` 与目标值之差的绝对值小于或等于 `0.001`, THE `ZZZ_Locomotion_Events` SHALL 将 `GaitBlendY` 置为目标值并结束本次插值，且在该次 `Context_Refresh` 内不再对 `GaitBlendY` 产生进一步变化。
6. WHILE `MovingGait` 在连续多帧内保持不变且 `Frame_Delta_Seconds` 大于 `0.0`, THE `GaitBlendY` SHALL 使相邻两帧的变化量符号一致或为零，不出现相邻帧之间的反向变化，也不出现越过目标值后的回摆。
7. THE `ZZZ_Animation_Layer` SHALL 以 `BlueprintReadOnly` 的跨帧记忆字段把 `GaitBlendY` 暴露给 AnimGraph 读取，该字段初始值为 `0.0`，且 AnimGraph 的读取不改写该字段。
8. IF `GaitBlendInterpSpeed` 配置为小于或等于 `0.0`, THEN THE `ZZZ_Locomotion_Events` SHALL 在该次 `Context_Refresh` 中将 `GaitBlendY` 直接置为钳制后的目标值，不执行按 `Frame_Delta_Seconds` 的推进。
9. WHILE `Locomotion_StateMachine` 处于 `NotMoving`、`Conduit` 或 `EnterMove`, THE `ZZZ_Locomotion_Events` SHALL 保持 `GaitBlendY` 为 `0.0`。
10. IF `Frame_Delta_Seconds` 小于或等于 `0.0`, THEN THE `ZZZ_Locomotion_Events` SHALL 保持 `GaitBlendY` 本帧取值不变，不执行任何推进。
11. IF `Context_Refresh` 传入的帧间隔秒数或 `GaitBlendInterpSpeed` 为非有限数值, THEN THE `ZZZ_Locomotion_Events` SHALL 将 `GaitBlendY` 置为钳制后的目标值，并保持该值落在 `[0.0, 1.0]` 闭区间内。

### Requirement 8: 冲刺开关的产生、锁存与消费边界

**User Story:** 作为动画程序员，我想让冲刺开关只在闪避进入移动这条路上被消费，以便一次触发只生效一次且边界可验证。

#### Acceptance Criteria

1. THE `FLocomotionIntentProcessor` SHALL 保持 `SprintTriggerPulse` 为上升沿单帧脉冲：当解析步态等于 `EMovementGait::Sprint` 且上一帧解析步态不等于 `EMovementGait::Sprint` 时取真，其余各帧取假。
2. WHILE 解析步态连续多帧保持 `EMovementGait::Sprint`, THE `FLocomotionIntentProcessor` SHALL 只在该连续区间的第 1 帧产生一次 `SprintTriggerPulse` 为真，其后各帧保持为假。
3. THE `SprintTriggerPending` SHALL 以假作为初始取值。
4. WHEN `Context_Refresh` 观察到 `FZZZAnimSnapshot::bSprintTrigger` 为真, THE `UZZZAnimInstance` SHALL 在向 `ZZZ_Locomotion_Decisions` 与 `ZZZ_Locomotion_Events` 注入上下文之前将 `SprintTriggerPending` 置为真，每次 `Context_Refresh` 至多执行一次该置值；WHERE `SprintTriggerPending` 已为真, THE 该置值 SHALL 按幂等处理且不改变取值。
5. THE `SprintTriggerPending` SHALL NOT 因帧数流逝或时长流逝自动置假，不设置超时与衰减。
6. WHEN `Locomotion_StateMachine` 经 `Sprint_Entry_Path` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 在该状态的 `On Entry` 中将 `SprintTriggerPending` 置为假，并对同一次进入只执行一次该置假。
7. THE `ZZZ_Locomotion_Decisions` SHALL 只读取 `SprintTriggerPending` 用于过渡判定，并保持不修改该字段。
8. WHILE 同一次 `SprintTriggerPulse` 已被 `Sprint_Entry_Path` 消费, THE `ZZZ_Animation_Layer` SHALL 保持 `SprintTriggerPending` 为假，直到 `FLocomotionIntentProcessor` 产生下一次上升沿脉冲。
9. THE `Sprint_Entry_Path` SHALL 是本功能范围内唯一将 `SprintTriggerPending` 从真置为假的路径；经 `Normal_Entry_Path` 进入 `Moving_State`、进入或退出 `TurnBack_State`、以及驻留于 `NotMoving`、`Conduit`、`EnterMove` 均 SHALL NOT 改变 `SprintTriggerPending` 的取值。

### Requirement 9: EnterMove 到 Moving 不消费开关

**User Story:** 作为动画程序员，我想让起步路径完全不接触冲刺开关，以便两条进入路径的职责互不干扰。

#### Acceptance Criteria

1. WHEN `Locomotion_StateMachine` 经 `Normal_Entry_Path` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 不对 `SprintTriggerPending` 执行任何写入，使该次进入前后在同一次 `Context_Refresh` 中观察到的 `SprintTriggerPending` 取值相等。
2. THE `ZZZ_Locomotion_Decisions` SHALL 保持 `Conduit_To_EnterMove()` 的判定条件为 `SprintTriggerPending` 为假，该函数 SHALL 为 `const` 且不产生副作用，且 `SprintTriggerPending` 为假 SHALL 是该过渡成立的必要条件。
3. IF `Locomotion_StateMachine` 经 `Normal_Entry_Path` 进入 `Moving_State` 时 `SprintTriggerPending` 仍为真, THEN THE `ZZZ_Locomotion_Events` SHALL 将 `MovingGait` 初始化为 `EMovementGait::Walk`、`GaitBlendY` 置为 `0.0`、`WalkHoldSeconds` 置为 `0.0`，并保留 `SprintTriggerPending` 为真。
4. WHEN `Locomotion_StateMachine` 经 `Normal_Entry_Path` 进入 `Moving_State`, THE `ZZZ_Locomotion_Events` SHALL 在 `SprintTriggerPending` 为真与为假两种情形下得到相同的 `MovingGait`、`GaitBlendY` 与 `WalkHoldSeconds` 初始化结果。
5. THE `ZZZ_Animation_Layer` SHALL 保持 `Conduit_To_EnterMove()` 与 `Conduit_To_Moving_Sprint()` 的判定结果互补：`SprintTriggerPending` 为假时前者为真且后者为假，为真时前者为假且后者为真，且两者在同一帧内不同时为真。
6. WHILE `Locomotion_StateMachine` 驻留于 `EnterMove`, THE `ZZZ_Locomotion_Events` SHALL NOT 将 `SprintTriggerPending` 置为假。
7. IF `Locomotion_StateMachine` 驻留于 `EnterMove` 期间观察到新的 `SprintTriggerPulse` 为真, THEN THE `UZZZAnimInstance` SHALL 按 Requirement 8 第 4 条将 `SprintTriggerPending` 置为真，并保留该取值直到经 `Sprint_Entry_Path` 进入 `Moving_State` 时被消费。

### Requirement 10: TurnBack 与步态、计时、开关的交互

**User Story:** 作为动画程序员，我想让转身期间的步态与计时处理明确，以便转身前后的走跑表现保持连续。

#### Acceptance Criteria

1. WHEN `Moving_SubStateMachine` 进入 `TurnBack_State`, THE `ZZZ_Locomotion_Events` SHALL 在该状态的 `On Entry` 中不写入 `MovingGait`、`GaitBlendY` 与 `WalkHoldSeconds`。
2. WHEN `Moving_SubStateMachine` 从 `TurnBack_State` 返回 `WalkRun_State`, THE `ZZZ_Locomotion_Events` SHALL 保持 `MovingGait` 与 `WalkHoldSeconds` 的取值不变，并在 Requirement 6 第 1 条的全部条件同时成立时恢复计时累加；该恢复动作仅在目标状态为 `WalkRun_State` 时适用。
3. WHILE `Moving_SubStateMachine` 处于 `TurnBack_State`, THE `ZZZ_Locomotion_Events` SHALL 不消费 `SprintTriggerPending`、不将其置为真；Requirement 8 第 4 条定义的脉冲锁存 SHALL 照常生效，并且是该期间唯一允许改变 `SprintTriggerPending` 的途径。
4. WHILE `Moving_SubStateMachine` 处于 `TurnBack_State`, THE `ZZZ_Locomotion_Events` SHALL 继续按 Requirement 7 的插值规则推进 `GaitBlendY` 向 `MovingGait` 对应目标值收敛，每次 `Context_Refresh` 至多推进一次，并使结果恒落在 `[0.0, 1.0]` 闭区间内。
5. WHEN `Locomotion_StateMachine` 在 `Moving_SubStateMachine` 处于 `TurnBack_State` 期间离开 `Moving_State`, THE `Moving_SubStateMachine` SHALL 不残留 `TurnBack_State`，并按 Requirement 1 第 8 条、Requirement 3 第 5 条、Requirement 4 第 1 至第 7 条与 Requirement 6 第 5 条在下一次进入 `Moving_State` 时重新初始化 `MovingGait`、`WalkHoldSeconds` 与 `GaitBlendY`。
6. THE 本需求定义的交互契约 SHALL 对 `TurnBack_State` 的任意进入时机与任意退出时机成立，`TurnBack_State` 自身的进入条件与退出条件由后续功能定义。
7. IF `Moving_SubStateMachine` 处于 `TurnBack_State` 且 `FZZZAnimSnapshot::bShouldMove` 为假, THEN THE `ZZZ_Locomotion_Events` SHALL 按 Requirement 6 第 4 条将 `WalkHoldSeconds` 置为 `0.0`，该重置优先于本需求第 2 条的取值保留。
8. IF `Moving_SubStateMachine` 处于 `TurnBack_State` 且 `MovingGait` 为 `Walk` 且 `WalkHoldSeconds` 大于或等于 `Effective_WalkToRunThreshold`, THEN THE `ZZZ_Locomotion_Events` SHALL 按 Requirement 5 第 7 条将 `MovingGait` 置为 `Run` 并将 `WalkHoldSeconds` 置为 `0.0`。

### Requirement 11: 配置项与容错

**User Story:** 作为技术美术，我想在细节面板调整时长阈值与插值速率，以便不改 C++ 就能调手感。

#### Acceptance Criteria

1. THE `FZZZAnimTuning` SHALL 提供 `WalkToRunHoldSeconds` 配置字段，单位为秒，默认值为 `5.0`，有效取值区间为 `[0.1, 60.0]` 闭区间，并以 `EditAnywhere` 暴露给 AnimBP 细节面板。
2. THE `FZZZAnimTuning` SHALL 提供 `GaitBlendInterpSpeed` 配置字段，单位为 1/秒，默认值为 `6.0`，有效取值区间为 `[0.1, 50.0]` 闭区间，并以 `EditAnywhere` 暴露给 AnimBP 细节面板。
3. IF `WalkToRunHoldSeconds` 配置为小于或等于 `0.0` 或为非有限数值, THEN THE `ZZZ_Locomotion_Events` SHALL 使用默认值 `5.0` 秒作为 `Effective_WalkToRunThreshold`，并保持 `FZZZAnimTuning` 中该配置字段的存储取值不被改写。
4. THE `ZZZ_Animation_Layer` SHALL 保持 `FZZZAnimTuning` 现有字段 `LoopBlendIn`（默认 `0.1` 秒）与 `OneShotBlendOut`（默认 `0.15` 秒）的名称、默认值与语义不变。
5. THE `ZZZ_Animation_Layer` SHALL 保持 `FRuntimeData::GaitThresholds` 的现有语义为逻辑侧速度阈值，且不将其作为 `WalkToRunHoldSeconds`、`GaitBlendInterpSpeed` 或 `GaitBlendY` 的输入。
6. IF `WalkToRunHoldSeconds` 大于 `60.0` 或 `GaitBlendInterpSpeed` 大于 `50.0`, THEN THE `ZZZ_Locomotion_Events` SHALL 把该配置值钳制到对应区间上限作为本次计算取值，并保持 `FZZZAnimTuning` 中该配置字段的存储取值不被改写。
7. IF `GaitBlendInterpSpeed` 为非有限数值, THEN THE `ZZZ_Locomotion_Events` SHALL 按 Requirement 7 第 8 条的处理方式将 `GaitBlendY` 直接置为目标值。
8. WHEN `FZZZAnimTuning` 的 `WalkToRunHoldSeconds` 或 `GaitBlendInterpSpeed` 在运行期间被修改, THE `ZZZ_Locomotion_Events` SHALL 自下一次 `Context_Refresh` 起使用修改后的取值，并保持 `MovingGait`、`WalkHoldSeconds` 与 `GaitBlendY` 的当前取值不被重置。

### Requirement 12: 分层职责与最小修改边界

**User Story:** 作为项目维护者，我想让新增逻辑严格落在既有分层内，以便动画层职责保持单一且可维护。

#### Acceptance Criteria

1. THE 新增的过渡判定逻辑 SHALL 全部实现在 `ZZZ_Locomotion_Decisions` 中，其每个新增判定函数声明为 `const`、返回 `bool`、只读取 `ZZZAnimSnapshot` 与 `ZZZAnimStateMemory` 的字段，并且不写入 `ZZZAnimStateMemory`、`FZZZAnimSnapshot`、`FRuntimeData` 或 `FAnimRuntimeData` 的任何字段。
2. THE 新增的记忆写入逻辑 SHALL 全部实现在 `ZZZ_Locomotion_Events` 中，覆盖且仅覆盖以下四项写入：`MovingGait` 初始化、`WalkHoldSeconds` 推进与重置、`GaitBlendY` 插值以及 `SprintTriggerPending` 消费。
3. THE `UZZZAnimInstance` SHALL 只提供 AnimBP 可调用的 `UFUNCTION` 转发与 `Context_Refresh` 调度；其每个新增转发函数的函数体 SHALL 只把调用委托给 `ZZZ_Locomotion_Decisions` 或 `ZZZ_Locomotion_Events` 的对应函数并返回其结果，不在 `UZZZAnimInstance` 内实现本功能的判定分支或记忆字段赋值。
4. THE 供 AnimBP `Can Enter Transition` 使用的新增转发函数 SHALL 声明为 `BlueprintPure`、带 `BlueprintThreadSafe` 元数据、归入 `Cond|Locomotion` 分类，并委托给 `ZZZ_Locomotion_Decisions` 的 `const` 判定函数。
5. THE 供 AnimBP `On Entry` 使用的新增转发函数 SHALL 声明为 `BlueprintCallable`、不带 `BlueprintThreadSafe` 元数据、归入 `Event|Locomotion` 分类，并委托给 `ZZZ_Locomotion_Events` 的对应事件函数。
6. THE `FLocomotionIntentProcessor` SHALL 保持为 `AnimData.Gait`、`AnimData.bShouldMove`、`AnimData.bSprintTrigger` 的唯一写入方；`FGYGOStateManager` SHALL 保持为 `AnimData.CurrentState` 的唯一写入方；`FMotionDriver` SHALL 保持为 `AnimData.VelocityLength` 的唯一写入方；本功能新增代码 SHALL 不向上述五个字段写入任何取值。
7. THE `ABaseCharacter` SHALL 只调度管线时序，且 SHALL 不直接写入 `AnimData.Gait`、`AnimData.bShouldMove`、`AnimData.bSprintTrigger`、`AnimData.CurrentState`、`AnimData.VelocityLength` 与 `FRuntimeData::GaitThresholds` 中的任何字段。
8. THE feature SHALL 保持 `FIntentPipeline` 现有公开成员函数的名称、参数列表、返回类型与调用顺序不变，且不新增、不删除、不重命名其公开成员函数与公开数据成员。
9. THE feature SHALL 不修改 `UNTEAnimInstance` 与 `Animation/Decisions` 模块中的任何源文件，包括不在其中新增、删除或重命名声明与实现。
10. THE feature SHALL 使本功能的每个判定条件在整个代码库中恰有一处实现函数，并使 `MovingGait`、`WalkHoldSeconds`、`GaitBlendY`、`SprintTriggerPending` 各自恰有一处存储位置且该位置位于 `ZZZAnimStateMemory`，不新增镜像副本、重复判定函数或旧动画层中的并行实现。
11. THE `ZZZ_Locomotion_Events` SHALL 是 `MovingGait`、`WalkHoldSeconds`、`GaitBlendY` 的唯一写入方；`SprintTriggerPending` 的写入方 SHALL 只有两处：`Context_Refresh` 中把该字段置为真的锁存步骤，以及 `ZZZ_Locomotion_Events` 中把该字段置为假的消费步骤。
12. IF AnimBP 在本帧 `Context_Refresh` 尚未执行、或 `ZZZ_Locomotion_Decisions` 与 `ZZZ_Locomotion_Events` 所需的上下文不可用时调用本功能的新增转发函数, THEN THE `UZZZAnimInstance` SHALL 使判定类转发函数返回假、使事件类转发函数不执行任何写入，并保持 `ZZZAnimStateMemory` 的全部字段取值不变。

### Requirement 13: 环境诊断与验证判定

**User Story:** 作为开发者，我想区分 Unreal 环境索引问题与业务代码错误，以便不因缺少 include path 而错误否定正确的实现。

#### Acceptance Criteria

1. IF `Unreal_Environment_Diagnostic` 在本功能范围内、且已按既有 ZZZ 源文件相同方式包含 Unreal 基础头文件的源文件中报告 `CoreMinimal.h`、`UFUNCTION`、`UPROPERTY` 或 `TMap` 未解析, THEN THE 验证流程 SHALL 将该报告归类为环境与工具链诊断，直到具备项目上下文的 Unreal 编译给出相反结论。
2. WHEN 一条验证结果被归类为环境与工具链诊断, THE 验证报告 SHALL 记录以下三项：该结果的分类归属、缺失的 include path 或 Unreal 索引上下文名称、产生该报告的源文件名；并且不仅凭该报告判定业务逻辑存在 C++ 语法缺陷。
3. WHEN 具备项目上下文的 Unreal 编译在改动的 ZZZ 文件中报告声明、类型或实现错误, THE 验证流程 SHALL 将该结果归类为业务代码缺陷，并要求修正后重新编译且改动文件的错误数量为 `0` 才视为通过。
4. THE 功能验证 SHALL 在进入 `Moving_State` 后首次 `Context_Refresh` 完成时采样，覆盖两条进入路径的初始步态用例：经 `Sprint_Entry_Path` 进入得到 `MovingGait` 为 `Run` 且 `GaitBlendY` 与 `1.0` 之差的绝对值不超过 `0.001`；经 `Normal_Entry_Path` 进入得到 `MovingGait` 为 `Walk` 且 `GaitBlendY` 与 `0.0` 之差的绝对值不超过 `0.001`。
5. THE 功能验证 SHALL 在 `WalkToRunHoldSeconds` 取默认值 `5.0`、`FZZZAnimSnapshot::bShouldMove` 持续为真且每帧 `Frame_Delta_Seconds` 不大于 `0.1` 秒的前提下覆盖 Walk 计时用例：累计 `4.9` 秒（允许 `0.01` 秒误差）时 `MovingGait` 仍为 `Walk`；累计达到 `5.0` 秒时 `MovingGait` 为 `Run`。
6. THE 功能验证 SHALL 在进入 `Moving_State` 后首次 `Context_Refresh` 完成时采样，覆盖开关消费边界用例：`SprintTriggerPending` 为真时经 `Sprint_Entry_Path` 进入后该标记为假；`SprintTriggerPending` 为真时经 `Normal_Entry_Path` 进入后该标记保持为真。
7. THE 功能验证 SHALL 覆盖速度解耦用例：在 `Snapshot_Gait` 为 `Run` 或 `Sprint`、`MovingGait` 为 `Walk` 且 `WalkHoldSeconds` 小于 `Effective_WalkToRunThreshold` 的条件下，于至少 `1.0` 秒且至少 `10` 次 `Context_Refresh` 的观察窗口内，`GaitBlendY` 与 `0.0` 之差的绝对值始终不超过 `0.001`。
8. THE 功能验证 SHALL 在本需求第 4 至第 7 条的全部用例均得到期望结果、且第 3 条定义的编译错误数量为 `0` 时判定为通过，任一用例结果与期望不一致时判定为失败。
9. IF 具备项目上下文的 Unreal 编译无法执行, THEN THE 验证流程 SHALL 将验证结论标记为未验证而非通过，并保留已采集的用例结果。
