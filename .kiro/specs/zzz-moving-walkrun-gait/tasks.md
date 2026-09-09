# Implementation Plan: zzz-moving-walkrun-gait

## Overview

按「数据层 → 判定层 → 事件层 → 转发层 → 调用点」的顺序增量落地，每一步都在既有 ZZZ 动画层文件内做加法，不触碰旧 NTE 动画层。

事件层是本功能的核心，拆成三段推进：先做配置解析与取值域纠正这类无副作用的基础函数，再做两个进入事件，最后做每帧推进函数 `AdvanceMovingGait`。这样 `AdvanceMovingGait` 落地时它依赖的所有子步骤都已可用，且每段完成后都能立刻用属性测试验证。

转发层（`UZZZAnimInstance`）与调用点（`ABaseCharacter`）放在事件层之后，因为 `PipelineDrive` 的签名变更需要 `AdvanceMovingGait` 已存在才能完成接线。

实现语言为 C++（Unreal Engine），测试沿用 `Source/GGYGO/Private/Tests/` 的 UE Automation + `FRandomStream` 脚手架。AnimBP 拓扑与资产配置无法由代码完成，集中在最后一节作为编辑器人工操作清单。

## Tasks

- [x] 1. 数据层与配置层落地
  - [x] 1.1 在 `ZZZAnimStateMemory.h` 新增子状态枚举与三个跨帧记忆字段
    - 新增 `UENUM(BlueprintType) enum class EZZZAnimMovingSubState : uint8`，取值 `None` / `WalkRun` / `TurnBack`，各带 `UMETA(DisplayName=...)` 中文显示名
    - 在 `FZZZAnimStateMemory` 内新增 `EMovementGait MovingGait = EMovementGait::Walk`、`float WalkHoldSeconds = 0.f`、`float GaitBlendY = 0.f`，三者均为 `UPROPERTY(BlueprintReadOnly, Category = "Locomotion")`
    - 保持 `EZZZAnimLocomotionState` 的取值与语义不变，子状态枚举不并入该枚举
    - 保持既有 `PreviousState` / `EnteredGait` / `bSprintTriggerPending` 三个字段不变
    - 每个新增字段的注释注明取值域与唯一写入方
    - _Requirements: 1.6, 3.1, 3.6, 6.7, 7.7, 12.10_

  - [x] 1.2 在 `CombatConfig.h` 的 `FZZZAnimTuning` 新增两个配置字段
    - 新增 `float WalkToRunHoldSeconds = 5.f`，`UPROPERTY(EditAnywhere, Category = "Gait", meta = (ClampMin = "0.1", ClampMax = "60.0"))`
    - 新增 `float GaitBlendInterpSpeed = 6.f`，`UPROPERTY(EditAnywhere, Category = "Gait", meta = (ClampMin = "0.1", ClampMax = "50.0"))`
    - 保持既有 `LoopBlendIn`（`0.1`）与 `OneShotBlendOut`（`0.15`）的名称、默认值与语义不变
    - 注释说明面板钳制只约束输入，运行期仍按事件层的容错规则解析
    - _Requirements: 11.1, 11.2, 11.4_

  - [x] 1.3 新增 `Public/Animation/zzzAnim/ZZZAnimKeys.h` 定义 BlendSpace key 常量
    - 新建 `namespace ZZZAnimKeys`，内含 `inline const FName WalkRunBlendSpace = FName(TEXT("WalkRun"));`
    - 单一编译期常量，注释注明该 key 不随 `MovingGait`、`GaitBlendY`、`Snapshot_Gait` 或 `Moving` 子状态变化
    - _Requirements: 2.2_

  - [x]* 1.4 新增 `Private/Tests/ZZZAnimTestGenerators.h` 属性测试生成器
    - 基于 `FRandomStream` 实现确定性生成器：`RandZZZSnapshot`、`RandZZZStateMemory`、`RandZZZTuning`、`RandDeltaSeconds`、`RandMovingSubState`、`RandOutOfDomainGait`、`RandFrameSequence`
    - 生成器须覆盖设计「边界覆盖清单」的全部取值：帧间隔 `{负值, 0, NaN, +Inf, -Inf, 0.0001, 0.1, 0.5}`；`GaitBlendY` 起始值 `{-1, 0, 0.0005, 0.5, 0.9995, 1, 2}`；`WalkHoldSeconds` 起始值 `{0, 阈值-0.001, 阈值, 3599.99, 3600, 100000}`；`WalkToRunHoldSeconds` `{NaN, -1, 0, 0.05, 5, 60, 61, 1e9}`；`GaitBlendInterpSpeed` `{NaN, -1, 0, 0.05, 6, 50, 51}`；`MovingGait` 含 `None` / `Sprint` 与取值域外强转值；`Snapshot_Gait` 全取值；`Moving` 子状态全取值含 `None`
    - 不修改、不复用依赖旧 NTE 快照类型的 `AnimTestGenerators.h`
    - _Requirements: 13.4, 13.5, 13.6, 13.7_

- [x] 2. `FZZZLocomotionDecisions` 上下文扩展与新增判定
  - [x] 2.1 扩展 `SetContext` 并实现 `Moving_Walk_To_Run_ByHold()`
    - `SetContext` 签名增加 `const FZZZAnimTuning* InTuning`，新增同名 `const` 私有成员，只读不拥有生命周期
    - 实现 `bool Moving_Walk_To_Run_ByHold() const`：返回 `MovingGait == Walk && WalkHoldSeconds >= Effective_WalkToRunThreshold` 的合取；阈值解析规则与事件层保持一致（非有限或 `<= 0` 取 `5.0`，否则钳到 `60.0` 上限）
    - 该函数只读 `MovingGait`、`WalkHoldSeconds`、`WalkToRunHoldSeconds`，不读 `VelocityLength`、`Snapshot_Gait`、`FRuntimeData`，不写任何字段
    - 上下文指针为空时返回假
    - `NotMoving_To_Conduit()` / `Conduit_To_EnterMove()` / `Conduit_To_Moving_Sprint()` 三个既有判定的实现保持原样不动
    - _Requirements: 4.4, 5.4, 9.2, 9.5, 12.1_

  - [x]* 2.2 为 Property 2 写属性测试：两个 Conduit 判定互补且只依赖冲刺开关
    - **Property 2: 两个 Conduit 判定互补且只依赖冲刺开关**
    - 文件 `Private/Tests/ZZZMovingWalkRunGaitPropertyTest.cpp`，迭代次数不少于 `100`，固定种子起步并在失败信息中打印种子与该次输入
    - 测试头部注释：`// Feature: zzz-moving-walkrun-gait, Property 2: ...`
    - **Validates: Requirements 4.4, 8.7, 9.2, 9.5, 12.1**

- [x] 3. `FZZZLocomotionEvents` 基础：上下文扩展、配置解析与取值域纠正
  - [x] 3.1 扩展 `SetContext` 并实现三个私有辅助函数
    - `SetContext` 签名增加 `const FZZZAnimTuning* InTuning`，新增同名 `const` 私有成员
    - 新增私有成员 `EZZZAnimMovingSubState CurrentSubState = EZZZAnimMovingSubState::None` 与 `bool bInvalidDeltaReported = false`
    - `ResolveWalkToRunThreshold()`：`Tuning` 为空或配置非有限或 `<= 0` → `5.0`；否则 `Min(配置值, 60.0)`；不改写配置存储值
    - `ResolveGaitBlendInterpSpeed()`：`Tuning` 为空 → `6.0`；配置非有限或 `<= 0` → 返回 `<= 0` 表示「直接置目标」；否则 `Min(配置值, 50.0)`；不改写配置存储值
    - `SanitizeMovingGait()`：`MovingGait` 落在 `{Walk, Run}` 之外时纠正为 `Walk`，输出 `LogZZZAnim` Warning
    - _Requirements: 3.8, 11.3, 11.6, 11.7, 11.8_

  - [x]* 3.2 为 Property 10 写属性测试：配置解析容错且不改写配置存储值
    - **Property 10: 配置解析容错且不改写配置存储值**
    - 覆盖 `NaN` / `±Inf` / 负值 / `0` / 超上限，并断言帧序列中途改配置后下一帧起生效且三个记忆字段不被重置
    - **Validates: Requirements 11.3, 11.6, 11.7, 11.8, 7.8**

  - [x]* 3.3 为 Property 9 写属性测试：MovingGait 取值域自纠正
    - **Property 9: MovingGait 取值域自纠正**
    - 覆盖 `None`、`Sprint` 与取值域外强转值，断言推进一帧后为 `Walk` 且本帧后续判定按 `Walk` 执行
    - **Validates: Requirements 3.1, 3.8**

- [x] 4. `FZZZLocomotionEvents` 进入事件
  - [x] 4.1 实现 `EnterMoving()` 与 `MarkMovingSubStateEntered()`
    - `EnterMoving()` 按 `Memory->PreviousState` 推导来路：`Conduit` → `MovingGait = Run`、`GaitBlendY = 1.0`、`WalkHoldSeconds = 0.0`，并调用既有 `ConsumeSprintTrigger()` 置假 `bSprintTriggerPending`
    - `PreviousState == EnterMove` 与其他兜底情形 → `MovingGait = Walk`、`GaitBlendY = 0.0`、`WalkHoldSeconds = 0.0`，不写 `bSprintTriggerPending`
    - 两条路径的 `GaitBlendY` 均为直接置值，不走插值；同一进入事件重复调用结果与调用一次相同
    - `MarkMovingSubStateEntered(EnteringSubState)` 只写私有 `CurrentSubState`，不写 `MovingGait`、`GaitBlendY`、`WalkHoldSeconds`、`bSprintTriggerPending`
    - 上下文指针为空时两个事件直接返回，不写任何字段
    - 置假 `bSprintTriggerPending` 只通过调用既有 `ConsumeSprintTrigger()` 完成，不新增第二处消费实现
    - _Requirements: 3.5, 3.7, 4.1, 4.2, 4.3, 4.5, 4.6, 4.7, 4.8, 6.5, 8.6, 9.1, 9.3, 9.4, 10.1, 12.11_

  - [x]* 4.2 为 Property 1 写属性测试：进入 Moving 的初始化结果只由来路决定
    - **Property 1: 进入 Moving 的初始化结果只由来路决定**
    - 覆盖任意起始记忆、任意快照（含 `bShouldMove` 为假）与任意配置，并断言重复调用幂等
    - **Validates: Requirements 1.8, 3.5, 3.7, 4.1, 4.2, 4.3, 4.5, 4.6, 4.7, 4.8, 6.5, 8.6, 9.1, 9.3, 9.4, 10.5**

  - [x]* 4.3 为 Property 3 写属性测试：冲刺开关只被 Sprint 进入路径置假
    - **Property 3: 冲刺开关只被 Sprint 进入路径置假**
    - 用随机序列组合脉冲锁存、帧间隔推进、Normal 路径进入与子状态进入，断言锁存幂等且不存在其他由真变假的调用
    - **Validates: Requirements 8.3, 8.4, 8.5, 8.8, 8.9, 9.6, 9.7, 10.3**

- [x] 5. `FZZZLocomotionEvents` 每帧推进 `AdvanceMovingGait`
  - [x] 5.1 实现门控、帧间隔校验与 `WalkHoldSeconds` 推进/重置
    - 执行序前 5 步：上下文校验为空直接返回 → 顶层状态门控（`LastEnteredState != Moving` 时 `WalkHoldSeconds = 0`、`GaitBlendY = 0`、`CurrentSubState = None`、复位 `bInvalidDeltaReported` 后返回）→ `SanitizeMovingGait()` → 帧间隔校验 → `ClampedDelta = Clamp(DeltaSeconds, 0, 0.1)`
    - 帧间隔非有限：输出 `LogZZZAnim` Warning（注明取值）、不推进计时、`GaitBlendY` 置为钳制后目标值后返回；帧间隔为负：输出 Warning、不推进计时、`GaitBlendY` 保持不变后返回；诊断以「一次 `Moving` 驻留」为窗口节流
    - `WalkHoldSeconds` 推进/重置：`!bShouldMove` → `0`；`MovingGait == Run` → `0`；子状态为 `WalkRun` → `+= ClampedDelta` 并上钳 `3600`；子状态为 `TurnBack` → 保持不变
    - 每次调用对 `WalkHoldSeconds` 至多推进一次，结果恒落在 `[0.0, 3600.0]`
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.6, 6.7, 6.8, 7.9, 10.2, 10.7, 12.12_

  - [x]* 5.2 为 Property 4 写属性测试：WalkHoldSeconds 的门控推进与区间不变式
    - **Property 4: WalkHoldSeconds 的门控推进与区间不变式**
    - **Validates: Requirements 5.5, 5.8, 6.1, 6.2, 6.3, 6.4, 6.7, 10.1, 10.2, 10.7**

  - [x]* 5.3 为 Property 5 写属性测试：非 Moving 顶层状态下计时与混合值归零
    - **Property 5: 非 Moving 顶层状态下计时与混合值归零**
    - **Validates: Requirements 6.6, 7.9**

  - [x] 5.4 实现跨阈升级步骤
    - 在 `WalkHoldSeconds` 推进之后调用 `FZZZLocomotionDecisions::Moving_Walk_To_Run_ByHold()`（复用唯一一处判定实现，不在事件层重写条件）
    - 判定成立且 `MovingGait == Walk` → `MovingGait = Run`、`WalkHoldSeconds = 0`；本帧不改动 `GaitBlendY`，留给插值步骤以本帧起始值为起点向 `1.0` 收敛
    - 每次调用至多执行一次该置值；同一次 `Moving` 驻留内不从 `Run` 回落 `Walk`；处于 `TurnBack` 子状态时同样执行升级不延后
    - `MovingGait == Run` 且 `WalkHoldSeconds > 0` 时置 `0` 且不重复触发升级效果
    - _Requirements: 3.2, 3.4, 5.1, 5.2, 5.5, 5.6, 5.7, 5.8, 6.9, 10.8, 12.10_

  - [x]* 5.5 为 Property 6 写属性测试：Walk 持续达阈值后单向升 Run
    - **Property 6: Walk 持续达阈值后单向升 Run**
    - 断言首次达阈后 `0.1` 秒内变为 `Run`、同帧 `WalkHoldSeconds` 归零、整个序列内 `MovingGait` 变化次数不超过 `1`
    - **Validates: Requirements 2.4, 3.2, 3.4, 5.1, 5.2, 5.6, 5.7, 6.9, 10.8**

  - [x] 5.6 实现 `AdvanceGaitBlendY()` 恒速插值
    - `Target = (MovingGait == Run) ? 1.0 : 0.0`；`Current = Clamp(GaitBlendY, 0, 1)`；`Speed = ResolveGaitBlendInterpSpeed()`
    - `Speed <= 0` → 直接置 `Target` 返回（优先于 `ClampedDelta <= 0` 分支）；`ClampedDelta <= 0` → 置 `Current` 返回；`|Target - Current| <= 0.001` → 置 `Target` 返回
    - 否则 `GaitBlendY = Clamp(FMath::FInterpConstantTo(Current, Target, ClampedDelta, Speed), 0, 1)`，随后若 `|Target - GaitBlendY| <= 0.001` 则吸附为 `Target`
    - 用 `FInterpConstantTo` 而非 `FInterpTo`，保证单帧变化量上界为 `Speed × ClampedDelta`、不越过目标、逐帧单调
    - 每次调用至多推进一次，结果恒落在 `[0.0, 1.0]`，不因上游非有限数值污染成 `NaN`
    - _Requirements: 1.5, 2.1, 2.7, 5.3, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8, 7.10, 7.11, 10.4, 10.6_

  - [x]* 5.7 为 Property 8 写属性测试：GaitBlendY 插值有界、不越目标、单调、可收敛
    - **Property 8: GaitBlendY 插值有界、不越目标、单调、可收敛**
    - **Validates: Requirements 1.5, 2.1, 2.7, 5.3, 7.3, 7.4, 7.5, 7.6, 10.4, 10.6**

  - [x]* 5.8 为 Property 7 写属性测试：有效步态与实时输入步态、速度解耦
    - **Property 7: 有效步态与实时输入步态、速度解耦**
    - 覆盖 `Snapshot_Gait ∈ {Run, Sprint}` 与任意 `VelocityLength`（含负值与极大值），并断言固定 `MovingGait` 时改变速度类字段不改变 `GaitBlendY` 的逐帧轨迹
    - **Validates: Requirements 3.3, 5.6, 7.1, 7.2**

  - [x]* 5.9 为 Property 11 写属性测试：退化帧间隔不破坏记忆一致性
    - **Property 11: 退化帧间隔不破坏记忆一致性**
    - **Validates: Requirements 6.8, 7.10, 7.11**

  - [x]* 5.10 为 Property 12 写属性测试：上下文不可用时安全降级
    - **Property 12: 上下文不可用时安全降级**
    - 覆盖未注入上下文情形下调用全部新增判定、事件与推进函数
    - **Validates: Requirements 12.12**

- [x] 6. Checkpoint - 事件层与判定层完成
  - Ensure all tests pass, ask the user if questions arise.

- [x] 7. `UZZZAnimInstance` 转发、调度与输出变量
  - [x] 7.1 帧间隔透传与推进调度接线
    - `PipelineDrive(float DeltaSeconds)` 与 `RefreshDecisionContext(float DeltaSeconds)` 签名由无参改为带帧间隔；`NativeUpdateAnimation` 的调用点同步传入 `DeltaSeconds`
    - `RefreshDecisionContext` 内顺序固定为：抓取快照 → 锁存 `bSprintTrigger` 为 `bSprintTriggerPending`（幂等、每帧至多一次）→ 向 `Decisions` 与 `Events` 注入含 `&Tuning` 的上下文 → 调用 `Events.AdvanceMovingGait(DeltaSeconds)`
    - 锁存步骤保持为 `bSprintTriggerPending` 置真的唯一实现处
    - _Requirements: 8.4, 9.7, 12.3, 12.11_

  - [x] 7.2 新增 `UFUNCTION` 转发与 `Out_WalkRunBlendSpace`
    - `Locomotion_Moving_Walk_To_Run_ByHold()`：`BlueprintPure` + `meta = (BlueprintThreadSafe)` + `Category = "Cond|Locomotion"`，函数体只委托给 Decisions 并返回结果
    - `Locomotion_OnEnter_Moving()`：`BlueprintCallable` + `Category = "Event|Locomotion"`（不带 `BlueprintThreadSafe`），只委托给 `Events.EnterMoving()`
    - `Locomotion_OnEnter_MovingSubState(EZZZAnimMovingSubState EnteringSubState)`：`BlueprintCallable` + `Category = "Event|Locomotion"`，委托给 `Events.MarkMovingSubStateEntered()`；当参数为 `WalkRun` 时执行一次 `GetBlendSpaceByKey(ZZZAnimKeys::WalkRunBlendSpace)` 并缓存到 `Out_WalkRunBlendSpace`
    - 新增 `UPROPERTY(BlueprintReadOnly, Category = "Out") TObjectPtr<UBlendSpace> Out_WalkRunBlendSpace;`
    - key 缺失时缓存空指针、不切状态、三个记忆字段不变，输出 `LogZZZAnim` Warning 注明 key 名与缺失位置，每次 `Moving` 驻留至多一次
    - 每个转发函数体只有一行委托，不含判定分支与记忆字段赋值
    - _Requirements: 2.2, 2.3, 2.6, 12.3, 12.4, 12.5_

  - [x]* 7.3 为 Property 13 写属性测试：BlendSpace 单 key 只读查询与缺失容错
    - **Property 13: BlendSpace 单 key 只读查询与缺失容错**
    - 断言查询前后 `FZZZAnimSet::BlendSpaces` 的条目集合与取值不变，key 缺失时 `GaitBlendY` 仍按 Property 8 规则推进
    - **Validates: Requirements 2.2, 2.3, 2.6**

- [x] 8. 调用点接线与既有行为回归
  - [x] 8.1 在 `Private/BaseCharacter.cpp` 补齐 `PipelineDrive` 参数
    - 将 `ZAI->PipelineDrive()` 改为 `ZAI->PipelineDrive(DeltaTime)`，保持在逻辑管线全部完成之后调用的既有时序
    - 同一行上方的 `UNTEAnimInstance::PipelineDrive()` 调用保持不变
    - 不在此处写入 `AnimData` 的任何字段，也不写入 `FRuntimeData::GaitThresholds`
    - _Requirements: 12.7, 12.9_

  - [x]* 8.2 为 Property 14 写属性测试：冲刺脉冲为上升沿单帧脉冲（既有行为回归）
    - **Property 14: 冲刺脉冲为上升沿单帧脉冲（既有行为回归）**
    - 只做只读回归验证，不修改 `FLocomotionIntentProcessor`
    - **Validates: Requirements 8.1, 8.2**

- [x] 9. 验收用例示例测试
  - [x]* 9.1 写示例测试覆盖四组验收用例与默认值断言
    - 文件 `Private/Tests/ZZZMovingWalkRunGaitExampleTest.cpp`
    - 两条进入路径初值：Sprint 路径得 `MovingGait == Run` 且 `|GaitBlendY - 1.0| <= 0.001`；Normal 路径得 `MovingGait == Walk` 且 `|GaitBlendY - 0.0| <= 0.001`
    - Walk 计时：`WalkToRunHoldSeconds = 5.0`、`bShouldMove` 恒真、每帧 `<= 0.1` 秒时，累计 `4.9` 秒（容许 `0.01` 秒误差）仍为 `Walk`，累计达 `5.0` 秒为 `Run`
    - 开关消费边界：`bSprintTriggerPending` 为真时经 Sprint 路径进入后为假、经 Normal 路径进入后保持为真
    - 速度解耦：`Snapshot_Gait` 为 `Run` 或 `Sprint`、`MovingGait` 为 `Walk` 且未达阈值时，至少 `1.0` 秒且至少 `10` 帧的窗口内 `|GaitBlendY - 0.0| <= 0.001`
    - 默认值断言：`MovingGait == Walk`、`GaitBlendY == 0.0`、`WalkHoldSeconds == 0.0`、`WalkToRunHoldSeconds == 5.0`、`GaitBlendInterpSpeed == 6.0`、`LoopBlendIn == 0.1`、`OneShotBlendOut == 0.15`
    - _Requirements: 13.4, 13.5, 13.6, 13.7, 13.8_

- [x] 10. Final checkpoint - 编译与全量测试
  - Ensure all tests pass, ask the user if questions arise.
  - 按 Requirement 13.1–13.3 区分诊断归属：编辑器索引报告的 `CoreMinimal.h` / `UFUNCTION` / `UPROPERTY` / `TMap` 未解析归类为环境与工具链诊断并记录分类、缺失 include path 与源文件名；只有具备项目上下文的 Unreal 编译报错才算业务缺陷，改动文件错误数须为 `0`
  - 无法执行项目编译时，结论标记为「未验证」而非「通过」，并保留已采集的用例结果（Requirement 13.9）

- [ ] 11. ZZZ AnimBP 编辑器人工落地（无法由代码完成）
  - 本节全部为编辑器手工操作，需在 UE 编辑器中打开 ZZZ AnimBP 逐项完成，完成后按 Requirement 13.8 记录冒烟检查结果
  - 在 `Moving` 状态内部新建 `Moving_SubStateMachine`，Entry 指向 `WalkRun_State`，状态集合恰为 `WalkRun_State` 与 `TurnBack_State` 两个，不含第三个状态与嵌套子状态机（Requirement 1.1、1.2）
  - 子状态机节点的 `Skip First Update Transition` 保持开启，用于满足驻留第 1 帧抑制 `TurnBack` 的要求（Requirement 1.7）
  - `TurnBack_State` 只保留 `WalkRun_State → TurnBack_State` 与 `TurnBack_State → WalkRun_State` 两条边，进入与退出条件留空由后续功能定义（Requirement 1.3、10.6）
  - `Moving` 状态的 `On Entry` 按固定顺序调用：先 `MarkLocomotionStateEntered(Moving)`，再 `Locomotion_OnEnter_Moving()`（顺序决定来路判定是否成立，不可交换）
  - `WalkRun_State` 的 `On Entry` 调用 `Locomotion_OnEnter_MovingSubState(WalkRun)`；`TurnBack_State` 的 `On Entry` 调用 `Locomotion_OnEnter_MovingSubState(TurnBack)`
  - `WalkRun_State` 的 AnimGraph 放单个 BlendSpace Player：资产引脚绑 `Out_WalkRunBlendSpace`，Y 轴引脚绑 `StateMemory.GaitBlendY`（Requirement 2.1）
  - 在 `AnimSet.BlendSpaces` 细节面板增加条目 key `WalkRun`，指向走跑混合资产（例如 `BS_Miyabi_Move`）
  - 不为 walk ↔ run 新增过渡状态、过渡动画序列或过渡通知（Requirement 2.5）
  - 冒烟检查代码结构类标准：新增判定函数均为 `const`、反射标记符合 Requirement 12.4/12.5、四个记忆字段各只有一处存储位置、`FIntentPipeline` 公开接口 diff 为空、`UNTEAnimInstance` 与 `Animation/Decisions/` 无改动（Requirement 12.8、12.9、12.10）

## Notes

- 带 `*` 的子任务为可选项，跳过后仍可得到可运行实现，但会失去 14 条正确性属性与验收用例的自动验证
- 属性测试全部落在 `Private/Tests/ZZZMovingWalkRunGaitPropertyTest.cpp`，每条属性一个独立测试、迭代不少于 `100` 次、固定种子起步，断言失败信息中打印种子与该次迭代输入以保证反例可复现
- 任务 11 是编辑器人工操作，无法由代码代劳；在它完成之前 C++ 侧逻辑虽可编译与测试，但 AnimBP 里看不到走跑混合表现
- 事件层三段（任务 3、4、5）刻意分开，`AdvanceMovingGait` 的执行序顺序即语义，实现时不要调整第 6 步（计时推进）与第 7 步（跨阈升级）的先后
- 任务 5.4 复用任务 2.1 的判定函数而非重写条件，这是 Requirement 12.10「每个判定条件恰有一处实现」的直接约束

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2", "1.3"] },
    { "id": 1, "tasks": ["1.4", "2.1"] },
    { "id": 2, "tasks": ["3.1", "2.2"] },
    { "id": 3, "tasks": ["4.1"] },
    { "id": 4, "tasks": ["5.1", "4.2"] },
    { "id": 5, "tasks": ["5.4", "3.3"] },
    { "id": 6, "tasks": ["5.6", "4.3"] },
    { "id": 7, "tasks": ["7.1", "3.2"] },
    { "id": 8, "tasks": ["7.2", "5.2"] },
    { "id": 9, "tasks": ["8.1", "5.3"] },
    { "id": 10, "tasks": ["5.5"] },
    { "id": 11, "tasks": ["5.7"] },
    { "id": 12, "tasks": ["5.8"] },
    { "id": 13, "tasks": ["5.9"] },
    { "id": 14, "tasks": ["5.10"] },
    { "id": 15, "tasks": ["7.3"] },
    { "id": 16, "tasks": ["8.2"] },
    { "id": 17, "tasks": ["9.1"] }
  ]
}
```
