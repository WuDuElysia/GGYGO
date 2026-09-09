# Requirements Document

## Introduction

本功能用于现有 Unreal 项目的新版 ZZZ 动画层，确认并完善 `NotMoving → Conduit` 的移动过渡决策。目标载体是 `UZZZAnimInstance` 及其 `ZZZAnimSnapshot` 数据链路；功能不重新扩展旧 `UNTEAnimInstance`、旧 `LocomotionDecisions` 或旧 NTE 动画层。

当前源码已经形成了预期的单向数据路径：`ABaseCharacter` 的逻辑管线写入 `FRuntimeData::AnimData`，`FZZZAnimSnapshotCapture` 从 `RuntimeData->AnimData` 抓取 `FZZZAnimSnapshot`，`UZZZAnimInstance` 的 `Locomotion_NotMoving_To_Conduit()` 供 AnimBP 过渡条件调用。本功能需求将这条路径、字段语义、判定真值表和最小修改边界固定为可验证契约。

## Glossary

- **ZZZ_Animation_Layer**：以 `UZZZAnimInstance` 为 C++ 决策载体、以 ZZZ AnimBP 为蓝图消费端的新版动画层。
- **UZZZAnimInstance**：目标动画实例类，位于 `Animation/zzzAnim/`，负责抓取 ZZZ 快照并提供 AnimBP 可调用的决策函数。
- **RuntimeData**：`FRuntimeData` 运行时黑板，包含逻辑管线状态以及供动画层读取的 `AnimData` 子结构。
- **AnimData**：`FRuntimeData::AnimData` 的 `FAnimRuntimeData` 值，作为逻辑管线到 ZZZ 动画层的唯一中间数据源。
- **ZZZAnimSnapshot**：`FZZZAnimSnapshot` 只读快照；由 `ZZZAnimSnapshotCapture` 从 `AnimData` 填充，供动画决策函数读取。
- **bShouldMove**：动画帧级移动输入/移动意图标志；表示本帧是否存在非零移动意图，不表示角色当前物理速度是否仍大于零。
- **CurrentState**：`ECharacterStateType` 当前逻辑状态；本功能关注 `Moving` 与其他状态的区分。
- **Moving**：`ECharacterStateType::Moving`，表示逻辑状态机当前处于移动状态。
- **NotMoving**：ZZZ AnimBP 中等待移动输入的动画状态。
- **Conduit**：ZZZ AnimBP 中用于将过渡路由到后续移动动画状态的导管节点。
- **Locomotion_Transition_Decision**：`UZZZAnimInstance` 上供 AnimBP `Can Enter Transition` 使用的纯布尔决策函数。
- **Inertial_Velocity**：角色停止输入后仍可能存在的残留物理速度；该值不能替代本功能的移动输入/意图判定。
- **AnimBP**：Unreal Animation Blueprint；读取 `UZZZAnimInstance` 的快照决策函数并组织状态机拓扑。
- **Unreal_Environment_Diagnostic**：因 Unreal Header Tool、模块 include path 或编辑器索引未加载 Unreal 头文件而产生的诊断信息，例如 `CoreMinimal.h`、`UFUNCTION`、`UPROPERTY` 或 `TMap` 未识别。

## Requirements

### Requirement 1: ZZZ 动画层目标与决策函数

**User Story:** 作为动画程序员，我想在新版 ZZZ 动画实例中提供明确的 NotMoving 到 Conduit 决策函数，以便 ZZZ AnimBP 可以直接绑定该过渡。

#### Acceptance Criteria

1. THE `ZZZ_Animation_Layer` SHALL provide `Locomotion_NotMoving_To_Conduit()` as a `const` boolean `Locomotion_Transition_Decision` on `UZZZAnimInstance`.
2. THE `Locomotion_Transition_Decision` SHALL be exposed to AnimBP as `BlueprintPure` and SHALL be declared with `BlueprintThreadSafe` metadata.
3. THE `Locomotion_Transition_Decision` SHALL be declared in the `Cond|Locomotion` category.
4. WHEN the ZZZ AnimBP evaluates the `NotMoving → Conduit` transition, THE `AnimBP` SHALL use `UZZZAnimInstance::Locomotion_NotMoving_To_Conduit()` as the transition decision source.

### Requirement 2: RuntimeData 到 AnimData 的数据投影

**User Story:** 作为动画程序员，我想让逻辑管线在每帧完成状态更新后投影 ZZZ 动画字段，以便过渡决策使用同一帧的输入意图和逻辑状态。

#### Acceptance Criteria

1. WHEN the `ABaseCharacter` frame pipeline has completed intent processing and state update, THE `RuntimeData` SHALL project the resolved movement intent into `AnimData::bShouldMove`.
2. WHEN the `ABaseCharacter` frame pipeline has completed the current-state update, THE `RuntimeData` SHALL project the logic state into `AnimData::CurrentState`.
3. THE `AnimData::bShouldMove` SHALL represent whether `DesiredWorldMoveDir` is non-zero for the current frame, and THE `AnimData::CurrentState` SHALL represent the current `FRuntimeData::CurrentState` from the same frame.
4. WHEN the ZZZ animation snapshot is captured, THE `ZZZAnimSnapshot` SHALL copy `AnimData::bShouldMove` to `bShouldMove` and `AnimData::CurrentState` to `CurrentState` without substituting another source field.
5. WHEN no valid character or `RuntimeData` is available during capture, THE `ZZZAnimSnapshot` SHALL retain default values that evaluate the target transition as false.

### Requirement 3: bShouldMove 的输入意图语义

**User Story:** 作为动画程序员，我想让 bShouldMove 表示本帧移动输入/意图而不是惯性物理速度，以便松开输入时动画层能及时离开移动路径。

#### Acceptance Criteria

1. WHEN the current frame contains a non-zero movement input or resolved movement intent, THE `AnimData` SHALL set `bShouldMove` to true regardless of whether `Inertial_Velocity` is zero or non-zero.
2. WHEN the current frame contains no movement input or resolved movement intent, THE `AnimData` SHALL set `bShouldMove` to false regardless of whether `Inertial_Velocity` remains non-zero.
3. THE `ZZZAnimSnapshot::bShouldMove` SHALL preserve the input/intent meaning of `AnimData::bShouldMove` and SHALL NOT be derived from `VelocityLength`, `Velocity2DLength`, `CurrentSpeed`, or another physical-speed field.
4. WHEN movement input is released while residual physical speed remains, THE `Locomotion_Transition_Decision` SHALL observe `bShouldMove == false` for that frame.

### Requirement 4: NotMoving 到 Conduit 判定规则

**User Story:** 作为动画程序员，我想让过渡只在同时满足移动意图和 Moving 逻辑状态时成立，以便避免仅凭速度或单一条件误切动画状态。

#### Acceptance Criteria

1. WHEN `ZZZAnimSnapshot::bShouldMove` is true and `ZZZAnimSnapshot::CurrentState` equals `ECharacterStateType::Moving`, THE `Locomotion_Transition_Decision` SHALL return true.
2. WHEN `ZZZAnimSnapshot::bShouldMove` is false, THE `Locomotion_Transition_Decision` SHALL return false regardless of `CurrentState`.
3. WHEN `ZZZAnimSnapshot::CurrentState` is not `ECharacterStateType::Moving`, THE `Locomotion_Transition_Decision` SHALL return false regardless of `bShouldMove`.
4. THE `Locomotion_Transition_Decision` SHALL evaluate the conjunction `bShouldMove && CurrentState == ECharacterStateType::Moving` and SHALL NOT add a speed threshold, gait requirement, grounded requirement, or inertial-velocity requirement.
5. FOR ALL combinations of `bShouldMove` and `CurrentState`, THE `Locomotion_Transition_Decision` SHALL return true if and only if both required conditions are satisfied.

### Requirement 5: ZZZ 快照到 AnimBP 的消费链路

**User Story:** 作为动画程序员，我想让 AnimBP 读取由 ZZZ 快照驱动的决策结果，以便蓝图过渡不会绕过快照直接访问 Actor 或旧动画层数据。

#### Acceptance Criteria

1. WHEN the character pipeline drives the ZZZ animation instance, THE `UZZZAnimInstance` SHALL capture the latest completed-frame `RuntimeData::AnimData` into `ZZZAnimSnapshot` before AnimBP evaluates the transition.
2. THE `Locomotion_Transition_Decision` SHALL read `ZZZAnimSnapshot` values only for its decision inputs and SHALL NOT read `ABaseCharacter`, `RuntimeData`, movement components, or physical velocity directly.
3. WHEN AnimBP evaluates `NotMoving → Conduit`, THE `AnimBP` SHALL receive a deterministic boolean derived from the captured `ZZZAnimSnapshot`.
4. THE data chain SHALL remain traceable in order as `RuntimeData → AnimData → ZZZAnimSnapshot → AnimBP`, with `bShouldMove` and `CurrentState` retaining their names and meanings at each corresponding handoff.

### Requirement 6: 最小修改范围与旧 NTE 层边界

**User Story:** 作为项目维护者，我想把变更限制在新版 ZZZ 过渡链路，以便确认新功能时不重新扩展旧 NTE 动画层。

#### Acceptance Criteria

1. THE feature SHALL target `UZZZAnimInstance`, `FZZZAnimSnapshot`, `FZZZAnimSnapshotCapture`, and the existing `FRuntimeData::AnimData` projection required to satisfy the preceding requirements.
2. THE feature SHALL preserve the existing `UZZZAnimInstance` snapshot lifecycle and SHALL modify only the smallest set of declarations, projections, captures, or decision logic needed to satisfy the target transition.
3. THE feature SHALL leave `UNTEAnimInstance` unchanged for this transition.
4. THE feature SHALL leave `LocomotionDecisions` unchanged for this transition.
5. THE feature SHALL not introduce a second data source, duplicate decision function, or parallel old-layer implementation for `NotMoving → Conduit`.
6. THE feature SHALL not change unrelated locomotion transitions, animation assets, or state-machine topology beyond binding the named ZZZ transition decision where that binding is required.

### Requirement 7: Unreal 环境诊断与验证判定

**User Story:** 作为开发者，我想区分 Unreal 环境索引问题与业务代码错误，以便不会因缺少 include path 而错误否定正确的 ZZZ 需求实现。

#### Acceptance Criteria

1. WHEN `Unreal_Environment_Diagnostic` reports missing `CoreMinimal.h` or unresolved Unreal reflection/container symbols in a source file that otherwise follows the project module include conventions, THE validation process SHALL classify the report as an environment/tooling diagnostic until a project-aware Unreal compile or equivalent validation contradicts that classification.
2. WHEN a validation result is classified as an environment/tooling diagnostic, THE validation report SHALL identify the missing include path or Unreal indexing context and SHALL not label the ZZZ business predicate as a C++ syntax defect solely from that report.
3. WHEN a project-aware Unreal build or compile reports an actual declaration, type, or implementation error in the changed ZZZ files, THE validation process SHALL classify that result as a business/code defect and SHALL require correction before completion.
4. THE feature validation SHALL verify the decision truth table with representative cases covering `(bShouldMove=true, CurrentState=Moving)`, `(false, Moving)`, `(true, Idle)`, and `(false, Idle)`.
5. THE feature validation SHALL include a residual-velocity case in which `bShouldMove=false` and physical velocity is non-zero, and SHALL expect the transition decision to be false.
