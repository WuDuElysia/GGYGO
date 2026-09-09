# Requirements Document

## Introduction

本功能把步态解析权收归逻辑侧，成为唯一决策者。

当前是双轨状态：逻辑侧 `FLocomotionIntentProcessor` 每帧用「Ctrl 强制 Walk > Shift 强制 Sprint > `CurrentSpeed >= 旧 RuntimeData 速度阈值镜像的 Walk 档` 判 Run > 摇杆幅度 `>= 0.5` 预测 Run」四级优先级算一套步态；动画侧 `FZZZLocomotionEvents` 又用 `FZZZAnimStateMemory::MovingGait` 与 `WalkHoldSeconds` 自己维护一套 Walk→Run 升级与 5 秒计时。两套规则并存，且逻辑侧读取的 `CurrentSpeed` 由同一 Tick 更后面的 `FMotionDriver` 写入，实际读到上一帧速度，形成「步态 → 动画 → 速度 → 步态」的隐式环路。

本功能后的步态规则只有三条：Walk 是正常情况下移动的唯一起始方式；Walk 连续保持 5 秒后平滑升为 Run；闪避区间全程存在方向输入时，闪避结束后直接进入 Run。步态取值收敛为 Walk 与 Run 两种，Sprint 从步态链路移除。逻辑侧只输出离散步态，`GaitBlendY` 的插值表现继续留在动画层。

范围覆盖逻辑管线侧的步态决策（`Pipeline/Intents/`、`Pipeline/Parameters/`、`Data/Logic/RuntimeData.h`、`Data/Anim/AnimRuntimeData.h`、`StateMachine/CharacterStateType.h`）、`FMotionDriver` 的最小配套改动，以及动画层 `Animation/zzzAnim/` 的职责收缩。闪避进 Run 在本功能中只定义数据契约与读取方，写入方由后续闪避系统 spec 提供。

## Glossary

- **Gait_Authority**：逻辑侧步态决策者。指逻辑管线中承担步态解析职责的处理器，是 `FRuntimeData::ResolvedGait` 与 `FAnimRuntimeData::Gait` 的唯一写入方。本文档不锁定其具体类名与所在管线阶段。
- **Resolved_Gait**：`FRuntimeData::ResolvedGait`，逻辑侧步态决策结果的唯一存储位置。
- **Anim_Gait_Channel**：`FAnimRuntimeData::Gait`，`Resolved_Gait` 面向动画层的投影字段，经 `FZZZAnimSnapshotCapture` 抓取为 `FZZZAnimSnapshot::Gait`。
- **Snapshot_Gait**：`FZZZAnimSnapshot::Gait`，动画层读取到的本帧步态，是动画层 Moving 期间步态的唯一来源。
- **Movement_Gait_Domain**：移动步态取值域，恰为 `EMovementGait::Walk` 与 `EMovementGait::Run` 两个值。
- **Gait_None**：`EMovementGait::None`，表示当前不存在移动步态（无方向输入或被阻止移动），不属于 `Movement_Gait_Domain`。
- **Move_Input_Present**：本帧存在方向输入，判定为 `FInputData::CurrentFrame::Move` 的 `IsNearlyZero()` 返回假。
- **Walk_Hold_Timer**：逻辑侧 Walk 保持计时（秒），累计 `Resolved_Gait` 为 `Walk` 且满足推进条件的连续时长，取值域为 `[0.0, 3600.0]` 闭区间。
- **Walk_To_Run_Hold_Seconds**：Walk 自动升 Run 的时长阈值（秒），默认值 `5.0`。
- **Effective_Walk_To_Run_Threshold**：本次判定实际生效的阈值（秒）。配置值为有限值且落在 `(0.0, 60.0]` 区间时取该配置值本身，不施加下界钳制；配置值为有限值且大于 `60.0` 时取 `60.0`；配置值小于或等于 `0.0` 或为非有限数值时取默认值 `5.0`。
- **Logic_Frame_Delta_Seconds**：`Gait_Authority` 本帧使用的帧间隔（秒），参与计时前先钳制到 `[0.0, 0.1]` 闭区间。
- **Dodge_Run_Contract**：闪避进 Run 契约。由 `FRuntimeData` 的一个布尔跨帧锁存字段 `bDodgeRunPending` 承载，为真表示最近一次闪避从触发时刻到闪避结束全程存在方向输入且该次闪避已结束。
- **Dodge_Run_Producer**：`Dodge_Run_Contract` 的写入方。本功能范围之外，由后续闪避系统提供。
- **Gait_Consumer**：动画层步态消费者。指 `Animation/zzzAnim/` 下读取 `Snapshot_Gait` 的决策与事件模块，不产生自有步态取值。
- **Gait_Blend_Y**：`FZZZAnimStateMemory::GaitBlendY`，`WalkRun` BlendSpace 的 Y 轴输入，取值域为 `[0.0, 1.0]` 闭区间。
- **Gait_Blend_Interp_Speed**：`FZZZAnimTuning::GaitBlendInterpSpeed`，`Gait_Blend_Y` 向目标值收敛的速率（1/秒）。
- **Conduit_Branch**：`EZZZAnimLocomotionState::Conduit` 的分流判定，即在进入 `Moving` 之前决定走「直接进 Run」还是「经 `EnterMove` 起步」。
- **Locomotion_StateMachine**：ZZZ AnimBP 的 Locomotion 顶层状态机，状态集合为 `NotMoving` / `Conduit` / `EnterMove` / `Moving`。
- **Logic_Moving_State**：逻辑状态 `ECharacterStateType::Moving`，由 `FGYGOStateManager` 写入 `FRuntimeData::CurrentState`。
- **Speed_Sourced_Field**：由运动或根运动链路写入的速度类字段集合，包含 `FRuntimeData::CurrentSpeed`、`FRuntimeData::AnimSpeed`、`FRuntimeData::RootMotionDelta`、`FRuntimeData::bHasRootMotion`、`FAnimRuntimeData::VelocityLength`、`FAnimRuntimeData::Velocity2DLength`、`FZZZAnimSnapshot::VelocityLength`；`FMotionDriver::WalkSpeedCap` 与 `RunSpeedCap` 属于速度上限缓存，不属于步态判定输入。
- **Unreal_Environment_Diagnostic**：因 Unreal Header Tool、模块 include path 或编辑器索引未加载 Unreal 头文件而产生的诊断信息，例如 `CoreMinimal.h`、`UFUNCTION`、`UPROPERTY` 未识别。

## 默认假设（评审需确认）

以下条目已写入下方需求，评审时确认或修改即可：

1. `Walk_Hold_Timer` 归零条件：无方向输入、`bBlockMove` 为真、逻辑状态离开 `Logic_Moving_State`、`Resolved_Gait` 已为 `Run`（见 Requirement 5）。
2. Run 出口：移动过程中 Run 不回落到 Walk；只有停止移动后重新起步才从 Walk 开始（见 Requirement 6）。
3. `Walk_To_Run_Hold_Seconds` 的配置归属迁到逻辑侧 `FMovementConfig`，动画层 `FZZZAnimTuning::WalkToRunHoldSeconds` 移除；`Gait_Blend_Interp_Speed` 留在动画层 `FZZZAnimTuning`（见 Requirement 4、Requirement 11）。
4. `Snapshot_Gait` 为 `Gait_None` 时，`Gait_Blend_Y` 沿用上一帧目标值，避免松手瞬间由 Run 目标跌向 Walk 目标（见 Requirement 11）。
5. `FInputData::CurrentFrame` 的 `bForceWalkHeld` 与 `bSprintHeld` 字段、`APlayerCharacter` 的 `IA_Sprint` 绑定、`FInputPipeline::SetSprintHeld` 全部保留，仅步态解析不再读取（见 Requirement 14）。
6. `FMovementConfig::SprintSpeed` 与 `FMovementConfig::SprintMultiplier` 保留声明以避免数据资产迁移，本功能后不存在读取方（见 Requirement 14）。
7. `FZZZAnimStateMemory::EnteredGait` 移除，因其在 C++ 侧没有任何读取方（见 Requirement 13）。

## Requirements

### Requirement 1: 步态取值域收敛为 Walk 与 Run

**User Story:** 作为逻辑程序员，我想让步态只有 Walk 与 Run 两种取值，以便步态链路上不再存在无人负责的第三档。

#### Acceptance Criteria

1. THE `EMovementGait` SHALL 恰好包含 `None`、`Walk`、`Run` 三个取值，其中 `Movement_Gait_Domain` 为 `Walk` 与 `Run`，`Gait_None` 表示不存在移动步态；移除 `Sprint` 之后 `None`、`Walk`、`Run` 的声明顺序与各自的底层 `uint8` 数值与移除前保持相同，使既有资产与蓝图中对 `Walk` 与 `Run` 的引用不发生数值偏移。
2. WHILE `Move_Input_Present` 为真且 `FRuntimeData::bBlockMove` 为假, THE `Gait_Authority` SHALL 使 `Resolved_Gait` 取值落在 `Movement_Gait_Domain` 内。
3. WHILE `Move_Input_Present` 为假或 `FRuntimeData::bBlockMove` 为真, THE `Gait_Authority` SHALL 将 `Resolved_Gait` 置为 `Gait_None`。
4. THE `Gait_Authority` SHALL 使 `Anim_Gait_Channel` 在每帧写入完成后恒等于同帧 `Resolved_Gait`，且两者之间的跨帧延迟为 `0` 帧。
5. THE `Gait_Authority` SHALL 在每帧对 `Resolved_Gait` 至多写入一次，并使同一帧内对 `Resolved_Gait` 的任意两次及以上读取返回相同取值。
6. IF `Gait_Consumer` 读取到的 `Snapshot_Gait` 落在 `None`、`Walk`、`Run` 之外, THEN THE `Gait_Consumer` SHALL 按 `Walk` 参与后续判定、保持 `Snapshot_Gait` 的源值不被改写，并在该帧输出至多一条指明该取值非法的诊断信息。
7. THE `Gait_Authority` SHALL 使 `Resolved_Gait` 与 `Anim_Gait_Channel` 的初始取值为 `Gait_None`。

### Requirement 2: 逻辑侧唯一步态决策者

**User Story:** 作为项目维护者，我想让步态只有一个决策者，以便规则改动只需要改一处。

#### Acceptance Criteria

1. THE `Gait_Authority` SHALL 是 `Resolved_Gait` 与 `Anim_Gait_Channel` 在 `Source/GGYGO/**` 范围内的唯一写入方，其中字段声明处的默认初始化不计入写入方。
2. THE `Gait_Authority` SHALL 只依据 `Move_Input_Present`、`FRuntimeData::CurrentState`、`FRuntimeData::bBlockMove`、`Dodge_Run_Contract` 这四项判定输入解析步态；`Logic_Frame_Delta_Seconds` 只作为 `Walk_Hold_Timer` 的推进量参与、`Effective_Walk_To_Run_Threshold` 只作为 `Walk_Hold_Timer` 的比较阈值参与，两者不构成额外判定输入。
3. THE `Gait_Consumer` SHALL 以 `Snapshot_Gait` 作为 Moving 期间步态的唯一来源；`Animation/zzzAnim/` 下除 `FZZZAnimSnapshot::Gait` 之外不存在任何 `EMovementGait` 类型的成员字段，也不存在以其他类型表示步态取值的锁存字段。
4. THE `Gait_Consumer` SHALL 只读取 `Snapshot_Gait`，并保持不写回 `FRuntimeData`、`FAnimRuntimeData` 与 `FZZZAnimSnapshot` 的任何字段。
5. THE feature SHALL 使 Walk 升 Run 判定与闪避进 Run 判定各自恰有一处实现，且两处实现均位于 `Gait_Authority` 所在编译单元内。
6. THE `ABaseCharacter` SHALL 只调度管线时序，其任何成员函数中不存在对 `Resolved_Gait`、`Anim_Gait_Channel` 与 `Walk_Hold_Timer` 的赋值语句。
7. THE `Gait_Authority` SHALL 在 `ABaseCharacter::Tick` 中 `FMotionDriver::Process` 执行之前完成本帧 `Resolved_Gait` 的写入，使 `FMotionDriver` 同一帧读取到的取值与 `Gait_Authority` 本帧写入取值相同，不存在跨帧滞后。
8. THE `Gait_Authority` SHALL 在 `UZZZAnimInstance::PipelineDrive` 执行之前完成本帧 `Anim_Gait_Channel` 的写入，使该帧 `Snapshot_Gait` 等于同帧 `Resolved_Gait`。
9. IF `Gait_Authority` 在某帧未被执行, THEN THE feature SHALL 使该帧 `Resolved_Gait`、`Anim_Gait_Channel` 与 `Walk_Hold_Timer` 保持上一帧取值不变，并输出一条指明本帧步态解析未执行的诊断信息。

### Requirement 3: Walk 作为唯一起始步态

**User Story:** 作为玩家，我想让正常起步一定是走，以便移动的起始手感稳定一致。

#### Acceptance Criteria

1. WHEN `Move_Input_Present` 由假变为真且 `FRuntimeData::bBlockMove` 为假且 `Dodge_Run_Contract` 为假, THE `Gait_Authority` SHALL 将 `Resolved_Gait` 置为 `Walk`。
2. IF 上一逻辑帧 `Resolved_Gait` 为 `Gait_None` 且本帧 `Move_Input_Present` 为真且本帧 `FRuntimeData::bBlockMove` 为假且 `Dodge_Run_Contract` 为假, THEN THE `Gait_Authority` SHALL 使本帧 `Resolved_Gait` 为 `Walk`。
3. WHEN `FRuntimeData::CurrentState` 由其他状态变为 `Logic_Moving_State` 且 `FRuntimeData::bBlockMove` 为假且 `Dodge_Run_Contract` 为假, THE `Gait_Authority` SHALL 使 `Gait_Authority` 首次观察到该状态取值的那一逻辑帧的 `Resolved_Gait` 为 `Walk`。
4. THE `Gait_Authority` SHALL 只在 Requirement 4 定义的 Walk 保持升级与 Requirement 7 定义的闪避契约消费两种情形下把 `Resolved_Gait` 置为 `Run`。
5. WHEN `Move_Input_Present` 由假变为真, THE `Gait_Authority` SHALL 在本帧计时推进之前将 `Walk_Hold_Timer` 置为 `0.0` 作为本次移动的计时起点，使本次移动起始帧结束时 `Walk_Hold_Timer` 不大于 `0.1` 秒。
6. WHILE `FRuntimeData::bBlockMove` 为真, THE `Gait_Authority` SHALL 将 `Resolved_Gait` 置为 `Gait_None`、将 `Walk_Hold_Timer` 置为 `0.0`，且该帧不产生任何对 `Resolved_Gait` 的 `Walk` 写入。
7. THE `Gait_Authority` SHALL 以「上一逻辑帧在同一判定点记录的取值」作为本需求各条边沿判定的基线；在 `Gait_Authority` 本次运行首帧，基线取 `Move_Input_Present` 为假、`Resolved_Gait` 为 `Gait_None`、`Walk_Hold_Timer` 为 `0.0`。
8. WHEN `FRuntimeData::bBlockMove` 由真变为假且该帧 `Move_Input_Present` 为真且 `Dodge_Run_Contract` 为假, THE `Gait_Authority` SHALL 将 `Resolved_Gait` 置为 `Walk` 并使 `Walk_Hold_Timer` 从 `0.0` 重新起算。
9. THE `Gait_Authority` SHALL 按固定优先级解析起始步态：`FRuntimeData::bBlockMove` 为真时优先级最高并按本需求第 6 条处理，其次 `Dodge_Run_Contract` 为真时按 Requirement 7 第 4 条处理，两者均不成立时按本需求第 1 至第 3 条默认置为 `Walk`。

### Requirement 4: Walk 连续保持 5 秒升 Run

**User Story:** 作为玩家，我想让持续走够 5 秒后自动转为跑，以便长距离移动不需要额外操作。

#### Acceptance Criteria

1. WHEN 某帧在完成 Requirement 5 定义的计时推进之后满足 `Resolved_Gait` 为 `Walk` 且 `Move_Input_Present` 为真且 `FRuntimeData::bBlockMove` 为假且 `Walk_Hold_Timer` 大于或等于 `Effective_Walk_To_Run_Threshold`, THE `Gait_Authority` SHALL 在该帧将 `Resolved_Gait` 置为 `Run`。
2. WHEN `Resolved_Gait` 因 Walk 保持时长达到 `Effective_Walk_To_Run_Threshold` 而变为 `Run`, THE `Gait_Authority` SHALL 在同一帧将 `Walk_Hold_Timer` 置为 `0.0`。
3. THE `Gait_Authority` SHALL 在每帧至多执行一次本需求第 1 条定义的升级。
4. WHILE `Resolved_Gait` 为 `Walk` 且 `Walk_Hold_Timer` 落在 `[0.0, Effective_Walk_To_Run_Threshold)` 区间, THE `Gait_Authority` SHALL 保持 `Resolved_Gait` 为 `Walk`。
5. WHEN `Walk_Hold_Timer` 的累计推进量首次达到或超过 `Effective_Walk_To_Run_Threshold`, THE `Gait_Authority` SHALL 在该次推进所在帧内完成把 `Resolved_Gait` 置为 `Run` 的写入，使达到阈值与 `Resolved_Gait` 变为 `Run` 之间不存在额外中间帧。
6. THE `FMovementConfig` SHALL 提供 `Walk_To_Run_Hold_Seconds` 配置字段，单位为秒，默认值为 `5.0`，对细节面板输入施加 `[0.1, 60.0]` 闭区间的取值限制，并以 `EditAnywhere` 暴露给数据资产细节面板；该输入限制与本需求第 7、8 条定义的运行期回退规则相互独立。
7. IF `Walk_To_Run_Hold_Seconds` 配置为小于或等于 `0.0` 或为非有限数值, THEN THE `Gait_Authority` SHALL 取默认值 `5.0` 秒作为 `Effective_Walk_To_Run_Threshold`、保持 `FMovementConfig` 中该配置字段的存储取值不被改写，并输出一条指明该配置取值非法且已回退到 `5.0` 秒的诊断信息。
8. IF `Walk_To_Run_Hold_Seconds` 配置大于 `60.0`, THEN THE `Gait_Authority` SHALL 取 `60.0` 秒作为 `Effective_Walk_To_Run_Threshold`、保持 `FMovementConfig` 中该配置字段的存储取值不被改写，并输出一条指明该配置取值超过上界且已钳制到 `60.0` 秒的诊断信息。
9. WHILE `Walk_To_Run_Hold_Seconds` 为有限值且落在 `(0.0, 60.0]` 区间, THE `Gait_Authority` SHALL 取该配置值本身作为 `Effective_Walk_To_Run_Threshold`，不施加下界钳制。
10. THE `Gait_Authority` SHALL 在每帧执行本需求第 1 条定义的升级判定之前重新求值 `Effective_Walk_To_Run_Threshold`，使运行期对 `Walk_To_Run_Hold_Seconds` 的修改自下一帧判定起生效。
11. WHEN `Resolved_Gait` 由 `Walk` 变为 `Run`, THE `Gait_Consumer` SHALL 按 Requirement 11 定义的插值规则使 `Gait_Blend_Y` 由该帧起始取值向 `1.0` 收敛；除 Requirement 11 第 6 条定义的插值速率无效情形外，收敛期间任意单帧的 `Gait_Blend_Y` 变化量不超过 `Gait_Blend_Interp_Speed` 与该帧钳制后帧间隔之积。

### Requirement 5: Walk 保持计时的推进与归零

**User Story:** 作为逻辑程序员，我想让 Walk 计时的推进与归零条件完全确定，以便 5 秒阈值可复现验证。

#### Acceptance Criteria

1. WHILE `Resolved_Gait` 为 `Walk` 且 `Move_Input_Present` 为真且 `FRuntimeData::bBlockMove` 为假且 `FRuntimeData::CurrentState` 为 `Logic_Moving_State`, THE `Gait_Authority` SHALL 在本帧完成本需求第 3 至第 6 条归零判定之后以 `Logic_Frame_Delta_Seconds` 累加 `Walk_Hold_Timer`。
2. THE `Gait_Authority` SHALL 使每帧对 `Walk_Hold_Timer` 的写入序列恰为至多一次归零与至多一次推进，且单帧累计增量不超过 `Logic_Frame_Delta_Seconds`。
3. IF `Move_Input_Present` 为假, THEN THE `Gait_Authority` SHALL 将 `Walk_Hold_Timer` 置为 `0.0` 并跳过本需求第 1 条定义的推进。
4. IF `FRuntimeData::bBlockMove` 为真, THEN THE `Gait_Authority` SHALL 将 `Walk_Hold_Timer` 置为 `0.0` 并跳过本需求第 1 条定义的推进。
5. IF `FRuntimeData::CurrentState` 不为 `Logic_Moving_State`, THEN THE `Gait_Authority` SHALL 将 `Walk_Hold_Timer` 置为 `0.0` 并跳过本需求第 1 条定义的推进。
6. WHILE `Resolved_Gait` 为 `Run`, THE `Gait_Authority` SHALL 保持 `Walk_Hold_Timer` 为 `0.0` 并在该帧跳过本需求第 1 条定义的推进。
7. THE `Walk_Hold_Timer` SHALL 初始取值为 `0.0` 并恒落在 `[0.0, 3600.0]` 闭区间内，计算结果大于 `3600.0` 时取 `3600.0`，小于 `0.0` 时取 `0.0`。
8. WHEN 本需求第 3 至第 6 条定义的归零条件在某帧全部不成立且在其前一帧至少有一条成立, THE `Gait_Authority` SHALL 使该帧 `Walk_Hold_Timer` 由 `0.0` 起累加一次 `Logic_Frame_Delta_Seconds`，并保持归零前的累计量不被恢复。
9. THE `Walk_Hold_Timer` SHALL 作为 `Gait_Authority` 的跨帧成员存放在逻辑侧，跨帧保持取值，且不在帧末意图重置流程中被清零。
10. THE feature SHALL 使 `FZZZAnimStateMemory`、`FAnimRuntimeData` 与 `FZZZAnimSnapshot` 中不存在与 `Walk_Hold_Timer` 并行的 Walk 保持计时字段。
11. THE `Gait_Authority` SHALL 在每帧按固定顺序求值：先判定本需求第 3 至第 6 条的归零条件，再执行本需求第 1 条定义的推进，最后由 Requirement 4 第 1 条读取推进后的 `Walk_Hold_Timer` 判定升级。
12. IF 本需求第 3 至第 6 条中有两条或以上归零条件在同一帧同时成立, THEN THE `Gait_Authority` SHALL 只将 `Walk_Hold_Timer` 置为 `0.0` 一次，且该帧 `Walk_Hold_Timer` 结果与仅其中一条成立时相同。

### Requirement 6: Run 不回落与 Run 出口

**User Story:** 作为玩家，我想让跑起来之后不会自己变回走，以便持续移动的表现稳定。

#### Acceptance Criteria

1. WHILE `Resolved_Gait` 为 `Run` 且 `Move_Input_Present` 为真且 `FRuntimeData::bBlockMove` 为假且 `FRuntimeData::CurrentState` 为 `Logic_Moving_State`, THE `Gait_Authority` SHALL 在连续满足上述条件且累计不超过 `3600.0` 秒的任意观察窗口内保持 `Resolved_Gait` 为 `Run`，不将其改写为 `Walk`。
2. WHILE `Resolved_Gait` 为 `Run` 且本需求第 1 条的前置条件持续成立, THE `Gait_Authority` SHALL 在方向输入发生任意角度变化（含 `180` 度反向）、输入幅度在 `(0.0, 1.0]` 内任意取值、朝向发生任意变化的情况下保持 `Resolved_Gait` 为 `Run`。
3. WHEN `Move_Input_Present` 由真变为假, THE `Gait_Authority` SHALL 在同一帧将 `Resolved_Gait` 置为 `Gait_None` 并将 `Walk_Hold_Timer` 置为 `0.0`。
4. WHEN `Resolved_Gait` 由 `Gait_None` 再次进入 `Movement_Gait_Domain` 且 `Dodge_Run_Contract` 为假, THE `Gait_Authority` SHALL 使该次取值为 `Walk`，且该结果与停留在 `Gait_None` 的持续帧数无关，停留最少 `1` 帧时亦成立。
5. WHILE `Move_Input_Present` 连续为真, THE `Gait_Authority` SHALL 使 `Resolved_Gait` 在该区间内至多发生一次取值变化且变化方向恒为由 `Walk` 到 `Run`，使从 `Run` 到 `Walk` 的取值变化只经由 `Gait_None` 发生。
6. WHEN `FRuntimeData::CurrentState` 由 `Logic_Moving_State` 变为其他状态且 `Dodge_Run_Contract` 为假, THE `Gait_Authority` SHALL 将 `Walk_Hold_Timer` 置为 `0.0`，并使下一次进入 `Logic_Moving_State` 时按 Requirement 3 重新从 `Walk` 起算，不沿用上一次的 `Run` 取值。
7. WHEN `FRuntimeData::bBlockMove` 由假变为真, THE `Gait_Authority` SHALL 在同一帧将 `Resolved_Gait` 置为 `Gait_None` 并将 `Walk_Hold_Timer` 置为 `0.0`。
8. WHILE `Dodge_Run_Contract` 为真, THE `Gait_Authority` SHALL 按 Requirement 7 第 4 条处理该帧步态，作为本需求第 4 条与第 6 条 Walk 起算约束的显式例外。

### Requirement 7: 闪避进 Run 数据契约

**User Story:** 作为逻辑程序员，我想先把闪避进 Run 的数据契约定下来，以便闪避系统落地后直接接入而不必再改步态规则。

#### Acceptance Criteria

1. THE `FRuntimeData` SHALL 提供 `Dodge_Run_Contract` 布尔跨帧字段 `bDodgeRunPending`，初始取值为假，并且不在帧末 `ResetFrameIntents()` 中被清零。
2. THE `Dodge_Run_Contract` SHALL 以「最近一次闪避从触发时刻到闪避结束全程存在方向输入，且该次闪避已结束」为其取真的语义。
3. THE `Gait_Authority` SHALL 是 `Dodge_Run_Contract` 在本功能范围内的唯一读取方与唯一置假方。
4. WHEN `Dodge_Run_Contract` 为真且 `Move_Input_Present` 为真且 `FRuntimeData::bBlockMove` 为假, THE `Gait_Authority` SHALL 在该帧将 `Resolved_Gait` 置为 `Run`、将 `Walk_Hold_Timer` 置为 `0.0`，并将 `Dodge_Run_Contract` 置为假。
5. IF `Dodge_Run_Contract` 为真且 `Move_Input_Present` 为假, THEN THE `Gait_Authority` SHALL 将 `Dodge_Run_Contract` 置为假并将 `Resolved_Gait` 置为 `Gait_None`。
6. THE `Dodge_Run_Contract` SHALL 不因帧数流逝或时长流逝自动置假，其置假只由本需求第 4 条与第 5 条定义的消费动作产生。
7. WHILE 本功能范围内不存在 `Dodge_Run_Producer`, THE `Dodge_Run_Contract` SHALL 在运行期恒为假，使 `Resolved_Gait` 的起始取值恒为 `Walk`。
8. THE feature SHALL 保持 `FRuntimeData::bWantsToDodge` 的现有语义为帧级意图并继续在帧末清零，且 `Dodge_Run_Contract` 与该字段互不替代。

### Requirement 8: 步态解析与速度解耦

**User Story:** 作为逻辑程序员，我想让步态解析不读取速度，以便消除「步态 → 动画 → 速度 → 步态」的环路和跨帧隐式依赖。

#### Acceptance Criteria

1. THE `Gait_Authority` SHALL 保持不读取 `Speed_Sourced_Field` 中的任何字段。
2. THE `Gait_Authority` SHALL 只使用 `FInputData::CurrentFrame::Move` 是否近似为零这一布尔性质，并保持步态解析结果与该向量的幅度大小无关。
3. WHILE 输入序列与状态序列相同, THE `Gait_Authority` SHALL 对相同的 `Move_Input_Present` 序列、`FRuntimeData::CurrentState` 序列、`FRuntimeData::bBlockMove` 序列、`Dodge_Run_Contract` 序列与 `Logic_Frame_Delta_Seconds` 序列产生相同的 `Resolved_Gait` 序列。
4. THE `Gait_Authority` SHALL 使本帧 `Resolved_Gait` 只依赖本帧输入与自身跨帧计时，不依赖同一 Tick 中在其之后执行的处理器写入的字段。
5. THE feature SHALL 移除 `Ctrl` 强制 Walk、`Shift` 强制 Sprint、`CurrentSpeed >= 旧 RuntimeData 速度阈值镜像的 Walk 档` 判 Run、摇杆幅度 `>= 0.5` 预测 Run 这四条现有步态判定规则，使其在步态解析中不再生效。
6. THE `Gait_Consumer` SHALL 保持不以 `Speed_Sourced_Field` 中的任何字段作为步态判定或 `Gait_Blend_Y` 的输入。
7. THE feature SHALL 使 `FMotionDriver::WalkSpeedCap` 与 `FMotionDriver::RunSpeedCap` 分别由 `FMovementConfig::WalkSpeed` 与 `FMovementConfig::RunSpeed` 初始化并用于速度上限设置，且两个缓存不参与步态判定。

### Requirement 9: 帧间隔供给与时序约束

**User Story:** 作为逻辑程序员，我想让步态计时拿到确定的帧间隔，以便 5 秒阈值在逻辑侧成立且时序可验证。

#### Acceptance Criteria

1. THE feature SHALL 使 `Gait_Authority` 在每帧获得该帧帧间隔作为 `Logic_Frame_Delta_Seconds` 的来源。
2. THE `Gait_Authority` SHALL 在参与计时之前把帧间隔钳制到 `[0.0, 0.1]` 闭区间得到 `Logic_Frame_Delta_Seconds`。
3. IF 本帧帧间隔为负值或为非有限数值, THEN THE `Gait_Authority` SHALL 保持 `Walk_Hold_Timer` 当前取值不变，并输出一条指明该帧间隔取值无效的诊断信息。
4. THE feature SHALL 使 Requirement 2 第 7 条定义的时序约束在帧间隔供给方式确定之后仍然成立。
5. THE feature SHALL 保持 `FIntentPipeline` 现有公开成员函数的名称与调用顺序语义不变，且不删除、不重命名其公开成员函数。
6. THE requirements SHALL 不锁定帧间隔的传递方式，帧间隔经参数阶段处理器供给还是经意图接口补充由设计阶段选择。

### Requirement 10: 动画层职责收缩为步态消费者

**User Story:** 作为动画程序员，我想让动画层只消费逻辑侧步态，以便动画层不再重复实现一套步态规则。

#### Acceptance Criteria

1. THE feature SHALL 移除 `FZZZAnimStateMemory::MovingGait` 与 `FZZZAnimStateMemory::WalkHoldSeconds` 两个字段。
2. THE feature SHALL 使 `FZZZLocomotionEvents` 不再承担 Walk 到 Run 的升级判定与 Walk 保持计时推进职责。
3. THE feature SHALL 移除 `FZZZLocomotionDecisions::Moving_Walk_To_Run_ByHold()` 与 `UZZZAnimInstance::Locomotion_Moving_Walk_To_Run_ByHold()`，并在 ZZZ AnimBP 中解除对该转发函数的引用。
4. THE feature SHALL 移除 `ZZZLocomotionRules` 中的 `ShouldWalkUpgradeToRun`、`IsValidMovingGait`、`ResolveWalkToRunThreshold`、`DefaultWalkToRunHoldSeconds`、`MaxWalkToRunHoldSeconds`、`MaxWalkHoldSeconds`，并保留 `ResolveGaitBlendTarget`、`ResolveGaitBlendInterpSpeed`、`DefaultGaitBlendInterpSpeed`、`MaxGaitBlendInterpSpeed`、`MaxClampedDelta`、`GaitBlendSnapTolerance`。
5. THE `ZZZLocomotionRules::ResolveGaitBlendTarget` SHALL 以 `Snapshot_Gait` 作为其输入来源，`Run` 对应目标值 `1.0`，`Walk` 对应目标值 `0.0`。
6. THE `FZZZLocomotionEvents` SHALL 保持为 `Gait_Blend_Y` 的唯一写入方。
7. THE feature SHALL 保持 `EZZZAnimLocomotionState` 与 `EZZZAnimMovingSubState` 的取值集合与语义不变。
8. THE feature SHALL 使 `FZZZAnimStateMemory` 最终只保留 `GaitBlendY`；动画层不得依赖 `PreviousState`、`LastEnteredState` 或 `MarkStateEntered` 判断状态入口或 Moving 驻留。

### Requirement 11: GaitBlendY 插值表现留在动画层

**User Story:** 作为动画程序员，我想让走跑之间的插值仍由动画层负责，以便离散步态切换在表现上保持平滑。

#### Acceptance Criteria

1. THE `Gait_Blend_Y` SHALL 以 `Snapshot_Gait` 为唯一目标值来源：`Walk` 对应目标值 `0.0`，`Run` 对应目标值 `1.0`。
2. WHILE `Snapshot_Gait` 为 `Gait_None`, THE `FZZZLocomotionEvents` SHALL 沿用上一帧的 `Gait_Blend_Y` 目标值继续收敛。
3. WHILE `Gait_Blend_Y` 与其目标值之差的绝对值大于 `0.001`, THE `FZZZLocomotionEvents` SHALL 在每帧至多推进一次 `Gait_Blend_Y`：以 `Gait_Blend_Interp_Speed` 为速率按钳制后的帧间隔向目标值推进，且推进后不越过目标值。
4. WHEN `Gait_Blend_Y` 与目标值之差的绝对值小于或等于 `0.001`, THE `FZZZLocomotionEvents` SHALL 将 `Gait_Blend_Y` 置为目标值并结束本次插值。
5. THE `FZZZLocomotionEvents` SHALL 使 `Gait_Blend_Y` 恒落在 `[0.0, 1.0]` 闭区间内。
6. IF `Gait_Blend_Interp_Speed` 为小于或等于 `0.0` 或为非有限数值, THEN THE `FZZZLocomotionEvents` SHALL 将 `Gait_Blend_Y` 直接置为钳制后的目标值。
7. THE `FZZZAnimTuning` SHALL 保留 `GaitBlendInterpSpeed` 配置字段，默认值为 `6.0`，有效取值区间为 `[0.1, 50.0]` 闭区间，并以 `EditAnywhere` 暴露给 AnimBP 细节面板。
8. THE `FZZZAnimTuning` SHALL 移除 `WalkToRunHoldSeconds` 配置字段，使阈值配置只存在于 Requirement 4 第 6 条定义的逻辑侧位置。
9. WHILE `Locomotion_StateMachine` 处于 `NotMoving`, THE `FZZZLocomotionEvents` SHALL 将 `Gait_Blend_Y` 置为 `0.0`。
10. THE `Gait_Blend_Y` SHALL 以 `BlueprintReadOnly` 暴露给 AnimGraph 读取，且 AnimGraph 的读取不改写该字段。

### Requirement 12: Conduit 分流语义变更

**User Story:** 作为动画程序员，我想让 Conduit 按「是否直接进 Run」分流，以便闪避进 Run 的进入路径与起步路径保持区分。

#### Acceptance Criteria

1. THE `Locomotion_StateMachine` SHALL 保留 `Conduit` 状态，并保持其为进入 `Moving` 之前的分流点。
2. THE `Conduit_Branch` SHALL 以「本帧 `Snapshot_Gait` 是否为 `Run`」作为分流依据，取代现有以 `bSprintTriggerPending` 为依据的判定。
3. WHEN `Snapshot_Gait` 为 `Run`, THE `Conduit_Branch` SHALL 分流到直接进入 `Moving` 的路径。
4. WHEN `Snapshot_Gait` 为 `Walk` 或 `Gait_None`, THE `Conduit_Branch` SHALL 分流到经 `EnterMove` 起步的路径。
5. THE `Conduit_Branch` 的两条判定 SHALL 保持互补：同一帧内恰有一条为真。
6. THE `Conduit_Branch` 的判定函数 SHALL 声明为 `const`、只读取 `FZZZAnimSnapshot`、保持不修改 `FZZZAnimStateMemory` 的任何字段。
7. WHEN `Locomotion_StateMachine` 经直接进入路径进入 `Moving`, THE `FZZZLocomotionEvents` SHALL 将 `Gait_Blend_Y` 置为 `1.0`，使该次进入后首帧读取到的 `Gait_Blend_Y` 与 `1.0` 之差的绝对值不超过 `0.001`。
8. WHEN `Locomotion_StateMachine` 经 `EnterMove` 路径进入 `Moving`, THE `FZZZLocomotionEvents` SHALL 将 `Gait_Blend_Y` 置为 `0.0`。
9. THE feature SHALL 保持 `FZZZLocomotionDecisions::NotMoving_To_Conduit()` 的现有判定条件不变。

### Requirement 13: 动画状态记忆与快照步态字段的去留

**User Story:** 作为项目维护者，我想清掉没有读取方的锁存字段，以便动画层记忆只保留真正在用的数据。

#### Acceptance Criteria

1. THE feature SHALL 移除 `FZZZAnimStateMemory::EnteredGait` 字段。
2. THE `FZZZAnimStateMemory` SHALL 最终只保留 `GaitBlendY`；THE `FZZZLocomotionEvents::EnterMoving` SHALL 依据 `FZZZAnimSnapshot::Gait` 是否为 `Run` 初始化 `GaitBlendY` 与其目标值，且 `AdvanceGaitBlend` SHALL 依据 `FZZZAnimSnapshot::CurrentState` 是否为 `Moving` 判断 Moving 驻留；动画状态记忆不得通过 `PreviousState`、`LastEnteredState` 或 `MarkStateEntered` 参与上述逻辑。
3. THE `FZZZAnimSnapshot::Gait` SHALL 保留，并成为动画层步态判定与 `Gait_Blend_Y` 目标值的唯一来源。
4. THE `FZZZAnimSnapshotCapture` SHALL 保持 `FZZZAnimSnapshot::Gait` 由 `Anim_Gait_Channel` 直读抓取，并保持为该字段的唯一写入方。
5. THE feature SHALL 保持 `FZZZAnimSnapshot` 其余字段 `bShouldMove`、`CurrentState`、`VelocityLength`、`bGrounded`、`bBlockMove` 的名称与语义不变。

### Requirement 14: Sprint 在步态链路上的清理范围

**User Story:** 作为项目维护者，我想让 Sprint 从步态链路上彻底移除，以便不留下没有触发路径的分支。

#### Acceptance Criteria

1. THE feature SHALL 移除 `EMovementGait::Sprint` 枚举值。
2. THE feature SHALL 移除 `FRuntimeData::FGaitThresholds::Sprint` 字段，并移除 `FMotionDriver::Init` 中对该字段的同步。
3. THE feature SHALL 移除 `FAnimRuntimeData::bSprintTrigger` 与 `FZZZAnimSnapshot::bSprintTrigger` 字段，以及 `FZZZAnimSnapshotCapture` 中对应的抓取语句。
4. THE feature SHALL 移除 `FZZZAnimStateMemory::bSprintTriggerPending` 字段，以及 `UZZZAnimInstance::RefreshDecisionContext` 中对该字段的锁存步骤。
5. THE feature SHALL 移除 `FZZZLocomotionEvents::ConsumeSprintTrigger()`、`UZZZAnimInstance::ConsumeSprintTrigger()`、`FZZZLocomotionDecisions::Conduit_To_Moving_Sprint()`、`UZZZAnimInstance::Locomotion_Conduit_To_Moving_Sprint()`，并在 ZZZ AnimBP 中解除对相关转发函数的引用。
6. THE feature SHALL 保留 `FProcessedInput::bSprintHeld` 与 `FProcessedInput::bForceWalkHeld` 字段、`FInputPipeline::SetSprintHeld` 以及 `APlayerCharacter` 的 `IA_Sprint` 绑定，并使步态解析不读取这两个字段。
7. THE feature SHALL 保留 `FMovementConfig::SprintSpeed` 与 `FMovementConfig::SprintMultiplier` 的声明，并使本功能完成后这两个字段不存在读取方。
8. THE feature SHALL 使代码库中不存在以 `EMovementGait::Sprint` 为条件的分支。

### Requirement 15: MotionDriver 最小配套改动

**User Story:** 作为逻辑程序员，我想让 MotionDriver 的步态档位直接使用其私有速度上限缓存，以便 RuntimeData 不再承担速度阈值镜像职责。

#### Acceptance Criteria

1. THE `FMotionDriver::Process` SHALL 按两档设置 `MaxWalkSpeed`：`Resolved_Gait` 为 `Walk` 时取私有缓存 `FMotionDriver::WalkSpeedCap`，其余取值时取私有缓存 `FMotionDriver::RunSpeedCap`；两个缓存分别由 `FMovementConfig::WalkSpeed` 与 `FMovementConfig::RunSpeed` 初始化。
2. THE `FMotionDriver::ProcessLocomotion` SHALL 按两档设置速度上限：`Resolved_Gait` 为 `Walk` 时取私有缓存 `FMotionDriver::WalkSpeedCap`，其余取值时取私有缓存 `FMotionDriver::RunSpeedCap`；两个缓存分别由 `FMovementConfig::WalkSpeed` 与 `FMovementConfig::RunSpeed` 初始化。
3. WHILE `FRuntimeData::bBlockMove` 为真, THE `FMotionDriver` SHALL 将 `MaxWalkSpeed` 置为 `0.0`。
4. THE feature SHALL 保持 `FMotionDriver::UpdateRuntimeData` 现有写入字段 `CurrentSpeed`、`AnimData.VelocityLength`、`bIsMoving`、`MoveAngle` 的语义与写入方不变。
5. THE feature SHALL 保持 `FMotionDriver` 现有的 `AddMovementInput` 移动路径不变。
6. THE feature SHALL 保持 `FMotionDriver::Init` 中除旧 Sprint 配置同步清理之外的现有行为不变，包含 `WalkSpeedCap` / `RunSpeedCap` 的配置初始化、`MaxWalkSpeed` 默认值缓存与 `SetRootMotionMode(ERootMotionMode::IgnoreRootMotion)`。

### Requirement 16: 范围边界与排除项

**User Story:** 作为项目维护者，我想让本功能的边界明确，以便后续 spec 有清晰的接续点。

#### Acceptance Criteria

1. THE feature SHALL 保持 `FRootMotionParameterProcessor::Process` 的现有实现不变，即恒将 `AnimSpeed` 置为 `0.0`、`RootMotionDelta` 置为零向量、`bHasRootMotion` 置为假。
2. THE feature SHALL 保持 `FRuntimeData::AnimSpeed`、`FRuntimeData::RootMotionDelta`、`FRuntimeData::bHasRootMotion` 三个字段的声明与现有取值不变，其死代码清理留给后续 spec。
3. THE feature SHALL 保持 `FMotionDriver` 中 `bHasRootMotion` 分支与 `ProcessRootMotionMovement` 的现有实现不变，root motion 提取链路与速度来源改造留给后续 spec。
4. THE feature SHALL 保持 `ECharacterStateType` 的取值集合不变，不新增 `Dodging` 状态。
5. THE feature SHALL 保持 `GGYGOTags` 中 `State::Dodging` 与 `Ability::Dodge` 的定义不变，且不提供这两个 Tag 的写入方。
6. THE feature SHALL 保持 `FDodgeIntentProcessor` 的现有实现不变，闪避系统本身留给后续 spec。
7. THE feature SHALL 保持 `FGASArbiter` 现有读取的 Tag 集合与写入的 `bBlock*` 字段不变。
8. THE feature SHALL 保持 `UNTEAnimInstance` 与 `Animation/Decisions/` 模块中的源文件不变。
9. THE feature SHALL 不引入转向规则、`TurnBack` 拓扑改造、输入缓冲改造与 Sprint 步态的替代机制。

### Requirement 17: 验证判定与环境诊断

**User Story:** 作为开发者，我想区分环境索引问题与业务代码缺陷，以便验证结论准确。

#### Acceptance Criteria

1. IF `Unreal_Environment_Diagnostic` 在本功能范围内、且已按既有源文件相同方式包含 Unreal 基础头文件的文件中报告 `CoreMinimal.h`、`UFUNCTION` 或 `UPROPERTY` 未解析, THEN THE 验证流程 SHALL 将该报告归类为环境与工具链诊断。
2. WHEN 一条验证结果被归类为环境与工具链诊断, THE 验证报告 SHALL 记录该结果的分类归属、缺失的 include path 或索引上下文名称、产生该报告的源文件名。
3. THE 验证流程 SHALL 在本地编译执行之前将结论记录为「静态检查通过，编译待本地验证」。
4. THE 功能验证 SHALL 覆盖起始步态用例：`Dodge_Run_Contract` 为假、`Move_Input_Present` 由假变为真后首帧 `Resolved_Gait` 为 `Walk`。
5. THE 功能验证 SHALL 在 `Walk_To_Run_Hold_Seconds` 取默认值 `5.0`、`Move_Input_Present` 持续为真且每帧帧间隔不大于 `0.1` 秒的前提下覆盖计时用例：累计 `4.9` 秒（允许 `0.01` 秒误差）时 `Resolved_Gait` 为 `Walk`；累计达到 `5.0` 秒时 `Resolved_Gait` 为 `Run`。
6. THE 功能验证 SHALL 覆盖计时归零用例：`Move_Input_Present` 为假、`bBlockMove` 为真、`CurrentState` 不为 `Logic_Moving_State` 三种条件各自成立时 `Walk_Hold_Timer` 为 `0.0`。
7. THE 功能验证 SHALL 覆盖 Run 不回落用例：在 `Resolved_Gait` 为 `Run`、`Move_Input_Present` 持续为真的至少 `2.0` 秒且至少 `20` 帧的观察窗口内 `Resolved_Gait` 恒为 `Run`。
8. THE 功能验证 SHALL 覆盖闪避契约用例：`Dodge_Run_Contract` 置为真且 `Move_Input_Present` 为真时，该帧 `Resolved_Gait` 为 `Run` 且 `Dodge_Run_Contract` 为假。
9. THE 功能验证 SHALL 覆盖速度解耦用例：在 `FRuntimeData::CurrentSpeed` 取 `0.0` 到 `600.0` 之间任意取值的条件下，`Resolved_Gait` 只随 Requirement 2 第 2 条定义的四项输入变化。
10. IF 具备项目上下文的 Unreal 编译无法执行, THEN THE 验证流程 SHALL 将验证结论标记为未验证，并保留已采集的用例结果。
