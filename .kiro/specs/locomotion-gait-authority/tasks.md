# Implementation Plan: locomotion-gait-authority

## Overview

实现语言为 C++（Unreal Engine），与设计文档一致。**本计划不包含任何编译、测试或构建步骤**——用户明确要求编译由本地执行。所有任务的验证一律采用静态检查：文件存在性核对、目录内容核对、文本检索、签名与字段逐项比对。任务 3 与任务 7 是两个人工编译检查点，任务 4 与任务 8 是两个必须由用户在 Unreal 编辑器中执行的蓝图操作节点。

### 阶段划分与依赖理由

核心约束是 Sprint 引用清理与最终速度上限缓存的一致性。已静态核实的引用分布（检索范围 `Source/GGYGO/**`）：

- `EMovementGait::Sprint` 的引用恰有两处文件：`LocomotionIntentProcessor.cpp`（步态赋值与 `bSprintTrigger` 上升沿）与 `MotionDriver.cpp`（两处 `switch`）。**动画层不引用该枚举值**，`ZZZLocomotionRules::IsValidMovingGait` 只做 `Walk` / `Run` 正向校验。
- 动画层对 Sprint 的依赖是**字段级**的：`FAnimRuntimeData::bSprintTrigger` → `FZZZAnimSnapshot::bSprintTrigger` → `FZZZAnimStateMemory::bSprintTriggerPending` → `ConsumeSprintTrigger` / `Conduit_To_Moving_Sprint`。这条链路必须整条一次性移除，否则抓取语句或消费函数会指向已删字段。

据此确定五个阶段：

| 阶段 | 内容 | 结束时的自洽性 |
| --- | --- | --- |
| 一（任务 1） | 逻辑侧只做新增：`FGaitAuthorityProcessor`、`LogGait`、`WalkToRunHoldSeconds`、`bDodgeRunPending`、`FIntentPipeline::ProcessGait` 与 `Tick` 第 3.5 步调用点 | 可编译。`Resolved_Gait` 此时**被两处写入**（旧 `FLocomotionIntentProcessor` 与新 `FGaitAuthorityProcessor`），这是刻意接受的临时状态，见 Notes |
| 二（任务 2） | 从 `FLocomotionIntentProcessor` 移除四级优先级、三处步态赋值、`PreviousGait`、`[GAIT]` 日志 | 可编译。逻辑侧只剩一个写入方；`Sprint` 枚举值此时已无逻辑侧引用 |
| 三（任务 5） | Sprint 链路清理（枚举值、触发字段、动画分流函数）+ MotionDriver 使用 `WalkSpeedCap` / `RunSpeedCap` 两档 + Conduit 分流改依据 `Snapshot_Gait` | 可编译 |
| 四（任务 6） | 动画层步态与计时收缩（`StateMemory` 最终仅保留 `GaitBlendY`、`Tuning` 收缩、`ZZZLocomotionRules` 收缩、`Events` 改造、旧状态入口记忆与 `Moving_Walk_To_Run_ByHold` 移除） | 可编译 |
| 五（任务 9） | 静态验证：设计「静态检查项清单」A 至 F 六组 | — |

阶段三与阶段四**刻意不合并**：阶段三的清理对象是 Sprint 链路与 Conduit 分流依据，阶段四的清理对象是动画状态记忆、GaitBlendY 与计时；两者触及的字段集合不相交（Sprint 触发字段对动画状态/步态/计时字段），拆开可以让 checkpoint 失败时的排查范围减半。同时把 `Conduit_To_Moving_Sprint` → `Conduit_To_Moving_Direct` 的改名与改判定放进阶段三，是为了让蓝图只需改绑一次，避免「阶段三删函数、阶段四加函数」造成两次改绑。

阶段四内部（任务 6.1 至 6.6）触及的文件互相引用：动画状态记忆收缩与旧计时字段移除会同时打断状态入口记忆、`SanitizeMovingGait`、`ShouldWalkUpgradeToRun` 的调用点、`Moving_Walk_To_Run_ByHold` 与 `AdvanceMovingGait`，因此该阶段的六个子任务必须全部完成后才构成可编译状态，中间态不可编译是预期的。

蓝图侧改动的位置由「先解绑、再编译 C++、最后重绑」的顺序决定：任务 4 的解绑放在阶段三之前（此时被移除的 `UFUNCTION` 与 `StateMemory` 字段在 C++ 侧仍然存在，蓝图可正常打开并逐条摘除引用）；任务 8 的重绑放在阶段四编译通过之后（新增的 `Locomotion_Conduit_To_Moving_Direct` 已可见）。

## Tasks

- [x] 1. 阶段一：逻辑侧步态决策者新增（只新增，不删除）
  - [x] 1.1 新增 `LogGait` 日志类别（映射表 N3、N4）
    - `Public/Pipeline/Gait/GaitLog.h` 以 `DECLARE_LOG_CATEGORY_EXTERN(LogGait, Log, All);` 声明
    - `Private/Pipeline/Gait/GaitLog.cpp` 以 `DEFINE_LOG_CATEGORY(LogGait);` 定义，作为代码库中唯一定义处
    - 与 `LogZZZAnim` 同构：只声明一次、只定义一次；本 spec 逻辑侧的全部诊断走该类别
    - 不修改 `GGYGO.Build.cs`：新路径 `Public/Pipeline/Gait/` 沿用既有 `Public/Pipeline/**` 的相对包含形式 `#include "Pipeline/Gait/GaitLog.h"`
    - _Requirements: 2.9, 4.7, 4.8, 9.3_

  - [x] 1.2 新增两个数据契约字段（映射表 M2、M3 的新增部分）
    - `Public/Movement/MovementConfig.h` 加 `float WalkToRunHoldSeconds = 5.f;`，标注 `UPROPERTY(EditAnywhere, BlueprintReadWrite, Category = "Gait", meta = (ClampMin = "0.1", ClampMax = "60.0"))`，注释说明「面板钳制只约束输入，运行期按 `Gait_Authority` 的回退规则解析」
    - 本任务不动 `SprintSpeed` 与 `SprintMultiplier`，两者按 Requirement 14.7 保留声明以避免数据资产迁移
    - `Public/Data/Logic/RuntimeData.h` 加 `bool bDodgeRunPending = false;`，注释标注：语义为「最近一次闪避从触发到结束全程存在方向输入且该次闪避已结束」、唯一读取方与唯一置假方为 `FGaitAuthorityProcessor`、写入方由后续闪避 spec 提供
    - **不**把 `bDodgeRunPending` 加入 `ResetFrameIntents()`；该函数主体在本任务中一字不动，仍只清零 `bWantsToAttack` 与 `bWantsToDodge`
    - _Requirements: 4.6, 7.1, 7.2, 7.3, 7.8, 14.7_

  - [x] 1.3 新增 `FGaitAuthorityProcessor` 头文件（映射表 N1）
    - 创建 `Public/Pipeline/Gait/GaitAuthorityProcessor.h`，按设计的类声明落地；**不**实现 `IIntentProcessor` 或 `IParameterProcessor`（两个接口都无法同时传入 `FInputData` 与 `DeltaTime`），由 `FIntentPipeline` 以具名成员持有
    - 公开成员：`void Init(ACharacter* InOwner)` 与 `void Process(const FInputData& InputData, FRuntimeData& RuntimeData, float DeltaTime)`
    - 私有成员函数：`ResolveEffectiveThreshold()`、`ResolveFrameDelta()`、`ResolveFrameGait()`、`UpdateWalkHoldTimer()`、`ShouldUpgradeToRun()`
    - 跨帧成员：`TWeakObjectPtr<ABaseCharacter> Owner`、`float WalkHoldTimer = 0.0f`
    - 边沿基线成员，其初值即 Requirement 3.7 定义的首帧基线：`PreviousResolvedGait = EMovementGait::None`、`bPreviousMoveInputPresent = false`、`bPreviousBlockMove = false`、`PreviousCurrentState = ECharacterStateType::Idle`
    - 诊断节流标记：`bInvalidDeltaReported`、`bThresholdFallbackReported`、`bThresholdClampReported`、`bMissingOwnerReported`
    - 阈值常量在逻辑侧**重新声明**，不复用 `ZZZLocomotionRules`：`DefaultWalkToRunHoldSeconds = 5.0f`、`MaxWalkToRunHoldSeconds = 60.0f`、`MaxWalkHoldSeconds = 3600.0f`、`MaxClampedDelta = 0.1f`。理由写入注释：Requirement 10.4 要求把这些常量从动画层规则层移除，逻辑侧不应对动画层头文件产生新的依赖方向
    - `WalkHoldTimer` 注释标注其为 `Walk_Hold_Timer`、跨帧保持、恒落在 `[0, 3600]`、不进 `FRuntimeData`、不参与 `ResetFrameIntents()`
    - _Requirements: 5.9, 5.10, 3.7, 10.4, 9.5_

  - [x] 1.4 实现 `FGaitAuthorityProcessor` 的帧内七步（映射表 N2）
    - 创建 `Private/Pipeline/Gait/GaitAuthorityProcessor.cpp`
    - `Init` 缓存 `Owner`；阈值读取沿用 `FMotionDriver::Init` 的既有方式，即 `ABaseCharacter::GetCharacterConfig()` → `MovementConfig.WalkToRunHoldSeconds`
    - `Process` 内按**固定七步顺序**落地：① 采样本帧四项判定输入与三条边沿 → ② `ResolveFrameDelta` 帧间隔解析 → ③ `ResolveFrameGait` 基线步态 → ④ `UpdateWalkHoldTimer` 先归零再推进 → ⑤ `ShouldUpgradeToRun` 升级判定 → ⑥ 单次写入 `ResolvedGait` 与 `AnimData.Gait` → ⑦ 更新边沿基线成员
    - 步骤 ③ 到 ⑤ **全程只操作局部变量 `FrameGait`**，直到步骤 ⑥ 才落盘，以保证每帧对 `Resolved_Gait` 至多写入一次、同帧多次读取取值相同
    - 五级优先级链按顺序实现：1）`bBlockMove` 为真 → `Gait_None` 且该帧不产生任何 `Walk` 写入；2）`Move_Input_Present` 为假 → `Gait_None` 并把 `bDodgeRunPending` 置假；3）`bDodgeRunPending` 为真 → `Run`、计时归零、契约置假；4）上一帧为 `Run` 且未发生「离开 `Moving`」边沿 → `Run`；5）其余 → `Walk`
    - 第 4 条采用**边沿**判定 `bLeftMovingState = (PreviousCurrentState == Moving && CurrentState != Moving)` 而非电平判定，理由写入注释：Requirement 6.6 的触发条件本身是边沿；改成电平判定会使闪避契约在 `CurrentState` 尚未切到 `Moving` 的那一帧被打回 `Walk`，与 Requirement 6.8 把闪避列为 6.4 / 6.6 显式例外的意图相悖
    - `UpdateWalkHoldTimer` 的六条归零条件：Z1 `Move_Input_Present` 为假；Z2 `bBlockMove` 为真；Z3 `CurrentState` 不为 `Moving`；Z4 本帧 `FrameGait` 为 `Run`；Z5 `Move_Input_Present` 假→真边沿；Z6 `bBlockMove` 真→假边沿。多条同时成立只归零一次，结果与仅一条成立时相同
    - Z5 与 Z6 的必要性写入注释：Z1 至 Z4 全为电平条件，若方向输入重新出现而 `CurrentState` 恰好仍停留在 `Moving`（输入短暂中断而状态机未回落），仅靠电平条件不会归零，会把上一次移动的累计量带入本次移动
    - **帧间隔无效时 Requirement 9.3 优先于全部归零条件**：该帧跳过整个计时阶段，既不归零也不推进，`Walk_Hold_Timer` 保持不变；基线步态解析与升级判定照常执行（升级使用未变的计时值）。该裁决与其理由（帧间隔无效是不可信输入，此时任何计时写入都是基于不可信上下文的状态变更）写入 `UpdateWalkHoldTimer` 的函数注释
    - `ShouldUpgradeToRun` 条件为 `FrameGait == Walk && bMoveInputPresent && !bBlockMove && WalkHoldTimer >= ResolveEffectiveThreshold()`；阈值在此处**每帧重新求值**；升级成立时把 `FrameGait` 置 `Run` 并把 `WalkHoldTimer` 归零
    - `ResolveEffectiveThreshold` 的分段映射：有限值且落在 `(0.0, 60.0]` → 取原值，**不施加下界钳制**；有限值且大于 `60.0` → `60.0` 并输出节流诊断；小于或等于 `0.0` 或非有限 → `5.0` 并输出节流诊断；`Owner` 或 `CharConfig` 不可达 → `5.0` 并输出一次性诊断。三种情形一律不改写 `FMovementConfig` 的存储取值
    - `WalkHoldTimer` 的区间自愈：非有限时推进前置 `0.0`；结果上越取 `3600.0`、下越取 `0.0`
    - 全部诊断走 `LogGait`，级别 `Warning`，按驻留节流并在条件恢复正常时复位标记
    - 保持不读取任何速度类字段或 `FMotionDriver` 的 `WalkSpeedCap` / `RunSpeedCap`（`CurrentSpeed`、`AnimSpeed`、`RootMotionDelta`、`bHasRootMotion`、`VelocityLength`、`Velocity2DLength`），只使用 `FInputData::CurrentFrame::Move` 的 `IsNearlyZero()` 布尔性质，与该向量的幅度大小无关
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.7, 2.2, 2.5, 3.1, 3.2, 3.3, 3.4, 3.5, 3.6, 3.7, 3.8, 3.9, 4.1, 4.2, 4.3, 4.4, 4.5, 4.7, 4.8, 4.9, 4.10, 5.1, 5.2, 5.3, 5.4, 5.5, 5.6, 5.7, 5.8, 5.11, 5.12, 6.1, 6.2, 6.3, 6.4, 6.5, 6.6, 6.7, 6.8, 7.4, 7.5, 7.6, 8.1, 8.2, 8.3, 8.4, 9.2, 9.3_

  - [x] 1.5 `FIntentPipeline` 增设步态阶段与 Gait 阶段看门狗（映射表 M5、M6）
    - `Public/Pipeline/IntentPipeline.h` **纯新增**公开成员函数 `void ProcessGait(const FInputData& InputData, FRuntimeData& RuntimeData, float DeltaTime);`
    - 新增私有成员 `FGaitAuthorityProcessor GaitAuthority;`、`uint64 LastGaitFrameCounter = 0;`、`bool bGaitStageMissReported = false;`；`GaitAuthority` **不**进 `IntentProcessors` 或 `ParameterProcessors` 数组
    - 既有三个公开成员函数 `Init`、`ProcessIntents`、`ProcessParameters` 的名称与签名逐字不动，既有处理器的创建与注册顺序一字不动
    - `Private/Pipeline/IntentPipeline.cpp` 的 `Init` 内新增 `GaitAuthority.Init(InOwner)`
    - `ProcessGait` 委派给 `GaitAuthority.Process(...)` 并记录 `LastGaitFrameCounter = GFrameCounter`
    - `ProcessParameters` **入口处**执行 Gait 阶段看门狗：`LastGaitFrameCounter != GFrameCounter` 时输出一条节流 `LogGait` 诊断，指明本帧步态解析未执行；**不做补偿写入**，因为 `Resolved_Gait`、`Anim_Gait_Channel` 与 `WalkHoldTimer` 在管线中没有其他写入方，未执行帧上三者自然保持上一帧取值
    - _Requirements: 2.9, 9.1, 9.5, 9.6_

  - [x] 1.6 `ABaseCharacter::Tick` 接入第 3.5 步（映射表 M9）
    - `Private/BaseCharacter.cpp` 在第 3 步 `IntentPipeline->ProcessIntents(...)` 之后、第 4 步 `IntentPipeline->ProcessParameters(...)` 之前插入 `IntentPipeline->ProcessGait(*InputData, *RuntimeData, DeltaTime);`
    - 更新 `Tick` 内的时序注释，把新阶段标为「3.5 步态决策：Gait_Authority 单次写入 ResolvedGait 与 AnimData.Gait」，并注明该位置早于第 6 步 `MotionDriver->Process` 与第 7 步 `PipelineDrive`
    - `ABaseCharacter` 只调度：本任务不引入对 `ResolvedGait`、`AnimData.Gait`、`WalkHoldTimer` 的任何赋值语句
    - _Requirements: 2.6, 2.7, 2.8, 9.1, 9.4_

- [x] 2. 阶段二：逻辑侧旧步态规则移除
  - [x] 2.1 `FLocomotionIntentProcessor` 收缩为方向处理器（映射表 M7、M8）
    - `Public/Pipeline/Intents/LocomotionIntentProcessor.h` 删除私有成员 `PreviousGait`，删除 `StateMachine/CharacterStateType.h` 包含
    - `Private/Pipeline/Intents/LocomotionIntentProcessor.cpp` 删除四级步态优先级（`bForceWalkHeld` → `Walk`、`bSprintHeld` → `Sprint`、`CurrentSpeed >= 旧 RuntimeData 速度阈值镜像的 Walk 档` → `Run`、摇杆幅度 `>= 0.5` → `Run`）
    - 删除对 `RuntimeData.ResolvedGait`、`RuntimeData.AnimData.Gait`、`RuntimeData.AnimData.bSprintTrigger` 的全部赋值语句，删除 `bSprintTrigger` 的上升沿计算
    - 删除 `[GAIT]` 前缀的 `LogTemp` 日志
    - 保留 `DesiredWorldMoveDir` 的计算与清零、`AnimData.bShouldMove` 的写入
    - 文件头注释整体重写，删除 `Sprint`、`CurrentSpeed`、摇杆幅度预测相关描述
    - 本任务完成后 `Resolved_Gait` 与 `Anim_Gait_Channel` 在 `Source/GGYGO/**` 内只剩 `FGaitAuthorityProcessor` 一个写入方（字段声明处的默认初始化不计入）
    - _Requirements: 2.1, 8.5, 14.3, 14.6_

  - [x] 2.2 修正 `FRuntimeData` 的步态相关注释（映射表 M3 的注释部分）
    - `Public/Data/Logic/RuntimeData.h` 中 `ResolvedGait` 的写入方注释由 `LocomotionIntentProcessor` 改为 `FGaitAuthorityProcessor`，读取方描述去掉 `NTEAnim` 的 `Sprint` 相关文字
    - `CurrentSpeed` 的注释去掉「`LocomotionIntentProcessor` 步态解析 读取」，改为仅 `FMotionDriver` 与调试读取
    - `FMotionDriver` 的速度上限来源说明改为私有 `WalkSpeedCap` / `RunSpeedCap`，分别来自 `MovementConfig.WalkSpeed` / `.RunSpeed`，且不参与步态判定
    - `bWantsToDodge` 的注释补充其与 `bDodgeRunPending` 互不替代
    - 本任务只改注释，不动任何字段声明与函数体
    - _Requirements: 8.1, 8.7, 7.8_

- [x] 3. Checkpoint - 阶段一与阶段二本地编译
  - 请在本地执行编译验证。此时旧 Sprint 枚举、RuntimeData 速度阈值镜像与动画层的全部 Sprint 字段仍然存在，代码应自洽可编译
  - 预期报错范围：新增文件的包含路径、`FIntentPipeline` 新成员、`Tick` 新调用点、`LocomotionIntentProcessor` 删除后的残留引用
  - 运行期预期表现：起步为 `Walk`，持续移动 5 秒升 `Run`，松手回 `Gait_None`。动画层此时仍在用自己的 `MovingGait` 走一套并行升级，因此 `GaitBlendY` 的表现尚不完全由逻辑侧决定，属预期中间态
  - 确认编译通过后再继续；若报错请提供错误信息
  - _Requirements: 17.3_

- [ ] 4. 蓝图侧解绑（需用户在 Unreal 编辑器中手动操作，Kiro 无法执行）
  - [x] 4.1 解除 ZZZ AnimBP 对将被移除符号的全部引用
    - **本任务不是代码任务**，需用户打开 ZZZ AnimBP 逐条摘除引用。此时被移除的符号在 C++ 侧仍存在，蓝图可正常打开
    - 解除三个 `UFUNCTION` 的绑定：`Locomotion_Conduit_To_Moving_Sprint()`（`Conduit → Moving` 直接进入路径的 `Can Enter Transition`，任务 8.1 会改绑到新函数）、`Locomotion_Moving_Walk_To_Run_ByHold()`（`Moving` 内 `Walk → Run` 过渡的 `Can Enter Transition`，该过渡整体删除）、`ConsumeSprintTrigger()`（`Moving` Sprint 直接进入路径状态的 `On Entry` 节点，直接删除该节点）
    - 删除 `StateMemory` 字段的全部 `Get` 节点：动画状态、进入步态、移动计时与 Sprint 触发记忆字段；`GaitBlendY` 到 `WalkRun` BlendSpace `Y` 轴的连线保持不变
    - 解绑后这些过渡条件返回假，AnimBP 的走跑升级表现会暂时失效，直到任务 6 完成后由 `GaitBlendY` 在 BlendSpace 内承担。此为预期中间态
    - _Requirements: 10.1, 10.3, 11.10, 13.1, 14.4, 14.5_

- [ ] 5. 阶段三：Sprint 链路清理与 Conduit 分流改造
  - [x] 5.1 移除 `Sprint` 枚举值并核对 MotionDriver 两档速度缓存（映射表 M1、M3 删除部分、M10、M11）
    - `Public/StateMachine/CharacterStateType.h` 删除 `EMovementGait::Sprint`。该值位于枚举末位，删除后 `None` / `Walk` / `Run` 的声明顺序与底层 `uint8` 数值（0 / 1 / 2）均不变，既有资产与蓝图对 `Walk` / `Run` 的引用不发生数值偏移
    - `Public/Data/Logic/RuntimeData.h` 保持不声明 `FGaitThresholds`；速度上限由任务 9.6 已落地的 `FMotionDriver::WalkSpeedCap` / `RunSpeedCap` 缓存承载
    - `Private/Drivers/MotionDriver.cpp` 的 `Init` 保持从 `MovementConfig.WalkSpeed` / `.RunSpeed` 初始化两个私有缓存；`DefaultMaxWalkSpeed` 缓存与 `SetRootMotionMode(ERootMotionMode::IgnoreRootMotion)` 保持不变
    - `Process` 的 `switch` 收缩为两档：`bBlockMove` 为真 → `MaxWalkSpeed = 0.f`；否则 `ResolvedGait == Walk` → `WalkSpeedCap`，其余取值 → `RunSpeedCap`
    - `ProcessLocomotion` 的 `SpeedCap` 同样收缩为两档缓存
    - `bHasRootMotion` 分支、`ProcessRootMotionMovement`、`AddMovementInput` 路径、`UpdateRuntimeData` 的四个写入字段全部不动
    - `Public/BaseCharacter.h` 中 `GetResolvedGait()` 的注释去掉 `Sprint` 字样
    - 本任务完成后代码库中不存在以 `EMovementGait::Sprint` 为条件的分支
    - _Requirements: 1.1, 14.1, 14.2, 14.8, 15.1, 15.2, 15.3, 15.4, 15.5, 15.6, 16.3_

  - [x] 5.2 移除 `bSprintTrigger` 数据链路（映射表 M4、M12、M13）
    - `Public/Data/Anim/AnimRuntimeData.h` 删除 `bool bSprintTrigger`；修正 `Gait` 的注释：写入方改为 `FGaitAuthorityProcessor`，取值域标注为 `None` / `Walk` / `Run`
    - 保持 `bShouldMove`、`CurrentState`、`VelocityLength`、`Velocity2DLength`、`LastInputDirectionAngle` 不变
    - `Public/Animation/zzzAnim/Data/ZZZAnimSnapshot.h` 删除 `bool bSprintTrigger`；修正 `Gait` 的注释，标注其为动画层步态判定与 `GaitBlendY` 目标值的唯一来源、取值域为 `None` / `Walk` / `Run`
    - 保持 `bShouldMove`、`CurrentState`、`VelocityLength`、`bGrounded`、`bBlockMove` 的名称与语义不变
    - `Private/Animation/zzzAnim/Capture/ZZZAnimSnapshotCapture.cpp` 删除 `OutSnap.bSprintTrigger = AnimData.bSprintTrigger;`；`OutSnap.Gait = AnimData.Gait;` 保持为 `Snapshot_Gait` 的唯一写入语句
    - _Requirements: 13.3, 13.4, 13.5, 14.3_

  - [x] 5.3 移除 `bSprintTriggerPending` 锁存与消费链路（映射表 M14 的 Sprint 部分、M19 的 Sprint 部分、M20 的 Sprint 部分）
    - `Public/Animation/zzzAnim/Data/ZZZAnimStateMemory.h` 删除 `bool bSprintTriggerPending` 及其注释
    - `Public/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.h` 与对应 `.cpp` 删除 `ConsumeSprintTrigger()` 的声明与实现
    - `Public/Animation/zzzAnim/ZZZAnimInstance.h` 与对应 `.cpp` 删除 `UFUNCTION ConsumeSprintTrigger()` 的声明与实现
    - `RefreshDecisionContext(float)` 删除 `bSprintTriggerPending` 的锁存段（原本按快照的单帧脉冲置真），保持其余固定顺序不变：抓取快照 → 注入上下文 → 推进
    - 更新类注释中「事件职责」清单，移除「`ConsumeSprintTrigger`：转发冲刺触发消费」一行
    - _Requirements: 14.4, 14.5_

  - [x] 5.4 Conduit 分流改依据 `Snapshot_Gait`（映射表 M18 的 Conduit 部分、M20 的 Conduit 部分）
    - `Public/Animation/zzzAnim/Locomotion/ZZZLocomotionDecisions.h` 与对应 `.cpp` 把 `Conduit_To_Moving_Sprint()` 改名为 `Conduit_To_Moving_Direct()`，实现改为 `return Context.Snap && Context.Snap->Gait == EMovementGait::Run;`
    - `Conduit_To_EnterMove()` 名称不变、判定改为 `return !Context.Snap || Context.Snap->Gait != EMovementGait::Run;`
    - 两条判定的**互补性**要在注释中给出证明：设 `P = (Context.Snap != nullptr && Context.Snap->Gait == Run)`，前者返回 `P`，后者返回 `!P`，同一帧恰有一条为真；上下文缺失时确定性地落到起步路径
    - 该互补性是相对现状的**修复**：现状两条判定都带 `Context.Memory &&` 前缀，`Memory` 为空时两条同时为假，存在无出口帧。注释中标注这一点
    - 两条判定均声明为 `const`、只读取 `FZZZAnimSnapshot`、不修改 `FZZZAnimStateMemory` 的任何字段
    - `NotMoving_To_Conduit()` 的函数体逐字不动
    - `Public/Animation/zzzAnim/ZZZAnimInstance.h` 与对应 `.cpp` 把 `UFUNCTION Locomotion_Conduit_To_Moving_Sprint()` 改名为 `Locomotion_Conduit_To_Moving_Direct()` 并更新其注释（依据由「有待处理的冲刺触发」改为「本帧步态已是 Run」）；`Locomotion_Conduit_To_EnterMove()` 名称与签名不变，只更新注释描述其新依据
    - _Requirements: 12.1, 12.2, 12.3, 12.4, 12.5, 12.6, 12.9, 14.5_

- [ ] 6. 阶段四：动画层步态与计时收缩
  - [x] 6.1 `FZZZAnimStateMemory` 收缩为最终单字段（映射表 M14 的剩余部分）
    - 删除动画状态、进入步态、Sprint 触发与移动计时记忆字段及其注释
    - **本任务完成后的字段集合恰为一个字段：** `GaitBlendY`（`float`，默认 `0.f`，`BlueprintReadOnly`，取值域 `[0, 1]`，唯一写入方 `FZZZLocomotionEvents`）；不再保留 `PreviousState`
    - 移除 `#include "StateMachine/CharacterStateType.h"`；`Data/ZZZAnimEnums.h` 的包含保留
    - `Animation/zzzAnim/**` 下唯一的 `EMovementGait` 成员字段仍是 `FZZZAnimSnapshot::Gait`；入口初始化与 Moving 驻留分别由 `Snapshot_Gait` 与 `Snapshot_CurrentState` 提供依据
    - _Requirements: 2.3, 10.1, 10.8, 11.10, 13.1, 13.2_

  - [x] 6.2 `FZZZAnimTuning` 移除阈值字段（映射表 M15）
    - `Public/Animation/zzzAnim/Data/ZZZAnimTuning.h` 删除 `WalkToRunHoldSeconds` 及其 `meta` 钳制，使阈值配置只存在于逻辑侧 `FMovementConfig`
    - 保留 `GaitBlendInterpSpeed`（默认 `6.f`，`ClampMin = 0.1`、`ClampMax = 50.0`，`EditAnywhere`）、`LoopBlendIn`、`OneShotBlendOut` 的名称、默认值、分类与钳制不变
    - _Requirements: 11.7, 11.8_

  - [x] 6.3 `ZZZLocomotionRules` 收缩（映射表 M16、M17）
    - 头文件与实现文件删除六项：`ShouldWalkUpgradeToRun`、`IsValidMovingGait`、`ResolveWalkToRunThreshold`、`DefaultWalkToRunHoldSeconds`、`MaxWalkToRunHoldSeconds`、`MaxWalkHoldSeconds`
    - 保留六项：`ResolveGaitBlendTarget`、`ResolveGaitBlendInterpSpeed`、`DefaultGaitBlendInterpSpeed`、`MaxGaitBlendInterpSpeed`、`MaxClampedDelta`、`GaitBlendSnapTolerance`
    - `ResolveGaitBlendTarget` 的入参改名为 `InSnapshotGait`，语义由 `MovingGait` 改为 `Snapshot_Gait`；实现保持**正向 `Run` 判定**：`return InSnapshotGait == EMovementGait::Run ? 1.0f : 0.0f;`
    - 注释中说明 `IsValidMovingGait` 移除后的**容错承载**：容错由 `ResolveGaitBlendTarget` 的正向 `Run` 判定天然承载——只有 `Run` 映射到 `1.0`，`Walk`、`Gait_None` 与任何非法取值都落到 `0.0`，即「按 `Walk` 参与后续判定」；不需要任何取值域校验函数，也不写回 `Snapshot_Gait`
    - 保持全部函数为无状态纯函数、不 include 判定层与事件层头文件、不 include `.generated.h`
    - _Requirements: 1.6, 10.4, 10.5, 11.1_

  - [x] 6.4 `FZZZLocomotionDecisions` 移除 Walk 升 Run 判定（映射表 M18 的剩余部分）
    - 头文件与实现文件删除 `Moving_Walk_To_Run_ByHold()` 的声明与实现（其内部对 `ResolveWalkToRunThreshold`、`ShouldWalkUpgradeToRun`、`MovingGait`、`WalkHoldSeconds` 的引用随之消失）
    - 收缩后判定集合恰为三条：`NotMoving_To_Conduit()`、`Conduit_To_Moving_Direct()`、`Conduit_To_EnterMove()`
    - 更新类注释，删除「Moving 内 Walk 持续时长达到生效阈值」相关描述
    - _Requirements: 10.2, 10.3_

  - [x] 6.5 `FZZZLocomotionEvents` 改造为 `GaitBlendY` 推进器（映射表 M19）
    - 删除 `SanitizeMovingGait()`（其对 `IsValidMovingGait` 与 `MovingGait` 的引用随之消失）
    - `AdvanceMovingGait(float)` **改名**为 `AdvanceGaitBlend(float DeltaSeconds)`，注释改为「每帧推进 `GaitBlendY` 向 `Snapshot_Gait` 对应目标值收敛」。该函数不是 `UFUNCTION`，蓝图侧无引用，改名不产生资产改动
    - 新增私有跨帧成员 `float LastGaitBlendTarget = 0.0f;`，注释标注其为「上一帧解析出的目标值，`Snapshot_Gait` 为 `Gait_None` 时沿用它继续收敛」。它**不进** `FZZZAnimStateMemory`：该结构体最终仅保留 `GaitBlendY`，且 AnimGraph 不需要读取目标值
    - 新增私有 `float ResolveTargetFromSnapshot() const`：`Snapshot_Gait` 为 `Gait_None` 时返回 `LastGaitBlendTarget`，否则返回 `ZZZLocomotionRules::ResolveGaitBlendTarget(Context.Snap->Gait)`
    - 新增私有 `void ReportInvalidSnapshotGaitIfNeeded()` 与节流标记 `bInvalidSnapshotGaitReported`：`Snapshot_Gait` 落在 `{None, Walk, Run}` 之外时按驻留节流输出至多一条 `LogZZZAnim` `Warning` 诊断，**不改写源值**（`Snap` 在 `FZZZAnimWriteContext` 中本就是 `const FZZZAnimSnapshot*`，改写在类型层面即不可能）。注释标注该检查定位为廉价护栏：`Sprint` 移除后 `EMovementGait` 只剩三个取值，越域只可能来自内存损坏或非法强转
    - `AdvanceGaitBlend` 的执行顺序：空指针检查（`Snap` 与 `Memory`）→ **非 `Moving` 驻留优先复位** → 非法取值诊断 → 目标值解析并写入 `LastGaitBlendTarget` → 帧间隔分支 → `AdvanceGaitBlendY`
    - **Requirement 11.9 优先于 11.2**：`!Context.Snap || Context.Snap->CurrentState != ECharacterStateType::Moving`（覆盖快照缺失及非 Moving 状态）时，把 `GaitBlendY` **与** `LastGaitBlendTarget` 一并置 `0.0`、复位 `CurrentSubState` 与帧间隔诊断标记，并直接结束本帧，不进入目标值解析与插值。理由写入注释：一并归零使 Requirement 11.2 的「沿用上一帧目标值」在下一次 `Snapshot_CurrentState == Moving` 时从 `Walk` 目标起算，与「Walk 是唯一起始步态」一致；该规则顺带覆盖 `EnterMove` 驻留期的 `GaitBlendY` 为 `0.0`，与入口初始化一致
    - `AdvanceGaitBlendY` 改为接收目标值参数 `AdvanceGaitBlendY(float Target, float ClampedDelta)`，插值主体沿用现状：速率小于或等于 `0.0` 或非有限时直接置目标值；差值绝对值不大于 `GaitBlendSnapTolerance` 时吸附目标；否则 `FMath::FInterpConstantTo` 后钳制到 `[0, 1]`，不越过目标值
    - 帧间隔分支保持现状语义：非有限时置目标值并输出节流诊断；负值时不改变 `GaitBlendY` 并输出节流诊断；否则钳制到 `[0, MaxClampedDelta]` 后推进
    - `EnterMoving()` 收缩为只初始化 `GaitBlendY` 与 `LastGaitBlendTarget`：`Snapshot_Gait == Run` 时取 `1.0`，其余步态或快照缺失取 `0.0`（直接进入与起步路径由本帧快照步态区分）
    - 删除状态入口记忆更新函数及其转发；`MarkMovingSubStateEntered` 与 `CurrentSubState` 若保留，仅作为子状态记录、无判定读取方；`EZZZAnimMovingSubState` 的取值集合与语义不变
    - 保持 `FZZZLocomotionEvents` 为 `GaitBlendY` 的唯一写入方，且不写回 `FRuntimeData`、`FAnimRuntimeData` 与 `FZZZAnimSnapshot` 的任何字段
    - 上下文仍需三个指针：`Snap` 提供 `Snapshot_Gait` 与 `Snapshot_CurrentState`，`Tuning` 提供 `GaitBlendInterpSpeed`，`Memory` 仅提供 `GaitBlendY`；`FZZZAnimWriteContext` / `FZZZAnimReadContext` 的结构、`IsValid()` 与 `ToRead()` 全部不动
    - _Requirements: 1.6, 2.4, 10.2, 10.6, 10.7, 11.1, 11.2, 11.3, 11.4, 11.5, 11.6, 11.9, 12.7, 12.8, 13.2_

  - [x] 6.6 `UZZZAnimInstance` 收尾（映射表 M20 的剩余部分）
    - 删除 `UFUNCTION Locomotion_Moving_Walk_To_Run_ByHold()` 的声明与实现
    - `RefreshDecisionContext(float)` 内的 `LocomotionEvents.AdvanceMovingGait(DeltaSeconds)` 改为 `LocomotionEvents.AdvanceGaitBlend(DeltaSeconds)`
    - 保持 `PipelineDrive(float)` 的签名不变，保持 `RefreshDecisionContext` 内「抓取快照 → 注入上下文（判定层用降级只读视图、事件层用可写上下文）→ 推进」的固定顺序
    - 更新类注释的判定与事件职责清单，使其与收缩后的三条 Conduit / NotMoving 判定一致
    - 核对收缩后 `UFUNCTION` 集合：旧 Sprint/Walk 升级函数与状态入口记忆转发已移除，`Locomotion_Conduit_To_Moving_Direct` 已新增，其余保持不变
    - _Requirements: 10.3, 12.2, 14.5_

- [x] 7. Checkpoint - 阶段三与阶段四本地编译
  - 请在本地执行编译验证；编译前建议清理 `Intermediate/Build`，因为枚举值与多个 `USTRUCT` 字段被移除后该目录会残留陈旧的 UHT 生成产物
  - 预期报错范围限于阶段三与阶段四触及的文件；若出现 `Sprint`、`MovingGait`、`WalkHoldSeconds`、`EnteredGait`、`bSprintTrigger*` 的残留引用报错，说明有引用点未被任务 5 与任务 6 覆盖，需回到对应子任务补齐
  - 打开 ZZZ AnimBP 时若报告失效节点，说明任务 4.1 的解绑未完全覆盖；此时按报告逐条删除即可
  - 确认编译通过后再继续任务 8 的蓝图重绑
  - _Requirements: 17.3_

- [ ] 8. 蓝图与数据资产侧重绑（需用户在 Unreal 编辑器中手动操作，Kiro 无法执行）
  - [-] 8.1 重新绑定新增函数并复核语义变更项
    - **本任务不是代码任务**，需用户在 ZZZ AnimBP 中操作
    - 把 `Conduit → Moving`（直接进入路径）的 `Can Enter Transition` 绑定到新函数 `Locomotion_Conduit_To_Moving_Direct()`
    - 复核语义变更项，无需改绑但需确认行为：`Locomotion_Conduit_To_EnterMove()`（依据改为「`Snapshot_Gait` 不为 `Run`」）、`Locomotion_OnEnter_Moving()`（依据 `Snapshot_Gait == Run` 初始化 `GaitBlendY` 与目标值）、`Locomotion_OnEnter_MovingSubState(EnteringSubState)`（若保留，签名不变且 `CurrentSubState` 当前无判定读取方）
    - 确认 `Locomotion_NotMoving_To_Conduit()` 无变更
    - _Requirements: 12.2, 12.4, 12.9, 13.2_

  - [x] 8.2 拓扑复核与数据资产配置
    - **本任务不是代码任务**，需用户在编辑器中操作
    - 复核 `Conduit` 直接进入路径的目标状态：若 AnimBP 中存在独立的 Sprint 状态节点（设计中的待确认假设 2），删除该节点并把 `Conduit` 的直接进入过渡指向 `Moving` 顶层状态
    - 复核 `Moving` 内的 `Walk` / `Run` 子状态：若存在按步态分裂的两个子状态，改为单一 `WalkRun` 子状态加 BlendSpace 混合，走跑过渡表现由 `GaitBlendY` 承担
    - `EnterMove` 出口保持现状；进入 `Moving` 后 `GaitBlendY` 由 `0.0` 起按 `Snapshot_Gait` 收敛
    - 确认 AnimBP 细节面板「Tuning / Gait」分组下 `WalkToRunHoldSeconds` 项已消失，资产上的残留值由反射系统忽略
    - 在 `DA_Kuhara`、`DA_Miyabi` 等 `UCharConfigData` 实例上确认新增字段 `MovementConfig → Gait → WalkToRunHoldSeconds` 取默认值 `5.0`，按角色需要调整；`SprintSpeed` / `SprintMultiplier` 保留但已无读取方
    - _Requirements: 4.6, 11.8, 11.10, 12.7, 12.8, 14.7_

- [x] 9. 阶段五：静态验证
  - [x] 9.1 执行设计「静态检查项清单」A 至 F 六组（约 40 项）
    - 检索范围统一限定 `Source/GGYGO/**`；`.kiro/specs` 只作为判定依据来源，不纳入代码检索范围
    - **A 组（唯一写入方与单一数据源，9 项）**：`ResolvedGait` 与 `AnimData.Gait` 的赋值点仅在 `GaitAuthorityProcessor.cpp` 与各自字段默认初始化处；`FZZZAnimSnapshot::Gait` 仅在 `ZZZAnimSnapshotCapture.cpp`；`GaitBlendY` 仅在 `ZZZLocomotionEvents.cpp`；`Animation/zzzAnim/**` 中 `EMovementGait` 成员字段仅 `FZZZAnimSnapshot::Gait`；`Animation/zzzAnim/**` 对 `FRuntimeData` / `FAnimRuntimeData` 的写入为零；`BaseCharacter.cpp` / `.h` 中对三个步态量的赋值为零；Walk 升 Run 判定与闪避契约消费各恰一处且同在 `GaitAuthorityProcessor.cpp`；`bDodgeRunPending` 的读取点与置假点仅 `GaitAuthorityProcessor.cpp` 且无置真点
    - **B 组（Sprint 清理，7 项）**：`EMovementGait::Sprint` 声明与引用为零且 `None` / `Walk` / `Run` 顺序与数值不变；`FRuntimeData` 不再声明 `FGaitThresholds`，且 `MotionDriver::Init` 不再同步旧 Sprint 速度字段；`bSprintTrigger` 三处为零；`bSprintTriggerPending` 与锁存段为零；`ConsumeSprintTrigger` / `Conduit_To_Moving_Sprint` 与两个转发 `UFUNCTION` 为零；`bSprintHeld` / `bForceWalkHeld` / `SetSprintHeld` / `IA_Sprint` 全部保留且步态解析中零引用；`SprintSpeed` / `SprintMultiplier` 声明保留且读取点为零
    - **C 组（动画层收缩，10 项）**：`FZZZAnimStateMemory` 字段恰为 `GaitBlendY` 且不存在状态/进入步态/计时/Sprint 触发记忆；`ZZZLocomotionRules` 的 6 项已移除、6 项保留与 Requirement 10.4 清单逐项一致；`ResolveGaitBlendTarget` 入参语义为 `Snapshot_Gait` 且实现为正向 `Run` 判定；`Moving_Walk_To_Run_ByHold` 与其转发为零；`FZZZAnimTuning` 无 `WalkToRunHoldSeconds` 且 `GaitBlendInterpSpeed` 为默认 `6.0` / 区间 `[0.1, 50.0]` / `EditAnywhere`；两个动画枚举取值集合与改动前逐项相同；`NotMoving_To_Conduit()` 函数体逐字相同；Moving 驻留判断使用 `Snapshot_CurrentState == Logic_Moving_State`；两条 Conduit 判定均为 `const`、只读 `Snap`、逻辑互补；`GaitBlendY` 标注为 `BlueprintReadOnly`
    - **D 组（时序与接口稳定性，6 项）**：`ABaseCharacter::Tick` 中 `ProcessGait` 位于 `ProcessIntents` 之后、`ProcessParameters` 之前，且早于 `MotionDriver->Process` 与 `PipelineDrive`；`FIntentPipeline` 既有三个公开成员函数名称与签名逐字不变且处理器注册顺序不变；两个处理器接口签名不变；`FGaitAuthorityProcessor::Process` 内语句顺序为「帧间隔解析 → 基线步态 → 归零 → 推进 → 升级 → 单次落盘 → 基线更新」；`Speed_Sourced_Field` 各字段在 `GaitAuthorityProcessor.cpp` 与动画层步态判定路径中的读取点为零；`ResetFrameIntents()` 仅清零 `bWantsToAttack` / `bWantsToDodge` 且不含 `bDodgeRunPending`
    - **E 组（范围边界，9 项）**：`RootMotionParameterProcessor.cpp` 无改动；`AnimSpeed` / `RootMotionDelta` / `bHasRootMotion` 声明与取值无改动；`MotionDriver` 的 `bHasRootMotion` 分支与 `ProcessRootMotionMovement` 无改动；`ECharacterStateType` 取值集合无改动且无 `Dodging`；`GGYGOTags` 的 `State::Dodging` / `Ability::Dodge` 定义无改动且无写入方；`DodgeIntentProcessor` 无改动；`FGASArbiter` 读取的 Tag 集合与写入的 `bBlock*` 字段无改动；`UNTEAnimInstance` 与 `Animation/Decisions/**` 无改动；改动文件集合与设计「文件级改动映射表」逐项一致且无表外文件
    - **F 组（单元级例证核对，7 项）**：`MaxWalkSpeed` 穷举 `{None, Walk, Run} × {bBlockMove 真, 假}` 六组映射（阻止时为 `0.0`，Walk 使用 `WalkSpeedCap`，其余使用 `RunSpeedCap`）；`ProcessLocomotion` 的 `SpeedCap` 三组步态映射同样核对两个缓存；`EnterMoving()` 的入口初始化（`Snapshot_Gait == Run` → `1.0`，其他步态或快照缺失 → `0.0`，误差不超过 `0.001`）；`FMovementConfig::WalkToRunHoldSeconds` 声明为默认 `5.0` / `ClampMin = 0.1` / `ClampMax = 60.0` / `EditAnywhere`；`FRuntimeData` 与 `FAnimRuntimeData` 的步态字段初值均为 `Gait_None`；`bDodgeRunPending` 初值为假且置真后调用 `ResetFrameIntents()` 仍为真；`MotionDriver::Init` 核对 `WalkSpeedCap` / `RunSpeedCap` 配置初始化，并保留 `DefaultMaxWalkSpeed` 缓存与 `SetRootMotionMode(IgnoreRootMotion)`
    - **环境诊断归类**：若某文件已按既有源文件相同方式包含 Unreal 基础头文件而诊断仍报告 `CoreMinimal.h`、`UFUNCTION` 或 `UPROPERTY` 未解析，归类为环境与工具链诊断，不据此判定失败；记录分类归属、缺失的 include path 或索引上下文名称、产生该报告的源文件名。新增文件位于 `Public/Pipeline/Gait/`，沿用既有 `Public/Pipeline/**` 的相对包含形式，不需要修改 `GGYGO.Build.cs`
    - 确认 `Content` 目录无由本计划的代码任务产生的文件变更（任务 4 与任务 8 由用户在编辑器中执行，其资产改动不在本项核对范围）
    - 结论表述为「静态检查通过，编译待本地验证」；若具备项目上下文的编译无法执行，把结论标记为未验证并保留已采集的用例结果
    - _Requirements: 17.1, 17.2, 17.3, 17.10_

  - [x] 9.6 最终收敛：移除 RuntimeData 步态阈值镜像与动画状态记忆链路
    - **本任务是最终架构收敛点**：完成后 `FZZZAnimStateMemory` 的最终字段集合只有 `GaitBlendY`，不存在 `PreviousState`、`LastEnteredState` 或 `MarkStateEntered` 链路；后续文档、静态检查与实现不得再把这些符号作为依据
    - **本任务是可执行的 C++ 代码清理任务**；代码检索与引用核对统一限于 `Source/GGYGO/**`，不得读取或修改 `Content/**`，也不得把 Content 资产作为实现依据
    - 确认 `FRuntimeData::FGaitThresholds` 已整体移除，RuntimeData 不再承载步态阈值镜像；`FMotionDriver` 的私有 `WalkSpeedCap` / `RunSpeedCap` 已由 `MovementConfig.WalkSpeed` / `.RunSpeed` 初始化，并由 `Process` 与 `ProcessLocomotion` 使用
    - 删除动画状态入口记忆函数、成员及其相关注释链路，仅保留 `FZZZAnimStateMemory::GaitBlendY`
    - 修改 `FZZZLocomotionEvents::EnterMoving`：依据 `Snapshot Gait == Run` 初始化 `GaitBlendY` 与 `LastGaitBlendTarget`；修改 `AdvanceGaitBlend`：依据 `Snapshot CurrentState == Moving` 判断是否处于 Moving，非 Moving 时执行现有的 GaitBlendY/目标值复位语义
    - 删除 `UZZZAnimInstance` 中仅服务于动画状态入口记忆的声明、实现及相关注释链路；同步清理仅服务于该链路的引用，保留其余动画状态、快照步态和 GaitBlendY 职责
    - 完成代码变更后更新 `.kiro/specs/locomotion-gait-authority/implementation-overview.md`，准确记录新的速度上限来源、动画状态记忆收缩和 Moving 判定依据；随后仅基于 `Source/GGYGO/**` 进行一次静态核对，检查删除符号、缓存初始化/使用点及注释引用是否一致
    - 不执行编译或测试；由用户在本地执行编译/测试，并将本地结果作为后续验证依据
    - _Requirements: 1.6, 10.1, 10.8, 11.1, 11.9, 13.1, 13.2, 14.3, 17.3_

  - [ ]* 9.2 编写 `FGaitAuthorityProcessor` 的属性测试（需本地运行）
    - **Property 1: 步态取值域不变式** — **Validates: Requirements 1.2, 1.3, 1.7**
    - **Property 2: 步态双字段同帧一致** — **Validates: Requirements 1.4, 2.8**
    - **Property 3: 起始步态优先级链的帧级模型等价** — **Validates: Requirements 3.1, 3.2, 3.3, 3.6, 3.8, 3.9, 6.3, 6.4, 6.7, 6.8, 7.4, 7.5**
    - **Property 4: Run 单向性** — **Validates: Requirements 3.4, 4.3, 6.1, 6.2, 6.5, 6.6**
    - **Property 5: Walk_Hold_Timer 区间与增量不变式** — **Validates: Requirements 5.1, 5.2, 5.7, 9.2, 9.3**
    - **Property 6: Walk_Hold_Timer 归零条件充要** — **Validates: Requirements 3.5, 5.3, 5.4, 5.5, 5.6, 5.8, 5.12**
    - **Property 7: 跨阈即时升级** — **Validates: Requirements 4.1, 4.2, 4.4, 4.5**
    - **Property 8: 阈值解析的分段映射与配置只读** — **Validates: Requirements 4.7, 4.8, 4.9, 4.10**
    - **Property 9: 速度解耦与解析确定性** — **Validates: Requirements 2.2, 8.1, 8.2, 8.3, 8.4, 8.6, 8.7, 17.9**
    - **Property 10: 闪避契约不因时间流逝失效** — **Validates: Requirements 7.6**
    - 载体为 Unreal Automation（`IMPLEMENT_SIMPLE_AUTOMATION_TEST`）配合 `FRandomStream` 确定性生成器，每条属性不少于 `100` 次迭代，注释标签格式为 `Feature: locomotion-gait-authority, Property {number}: {property_text}`
    - 边界输入覆盖：帧间隔取 `{负值, 0, NaN, +Inf, -Inf, 0.0001, 0.1, 0.5}`；`WalkToRunHoldSeconds` 取 `{NaN, ±Inf, -1, 0, 0.05, 5, 60, 61}`；`Walk_Hold_Timer` 起始值取 `{0, 阈值-0.001, 阈值, 3599.99, 3600, 100000}`；四项判定输入穷举含冲突组合（阻止与闪避契约同时为真、闪避契约与无方向输入同时成立）
    - `Owner` 为空时阈值走默认回退路径，因此逻辑侧属性可在无 `UWorld` 的环境下驱动
    - 本任务为可选项：**编写测试文件本身不需要编译，但运行该测试需要用户在本地执行，本计划不代为运行**
    - _Requirements: 17.4, 17.5, 17.6, 17.7, 17.8, 17.9_

  - [ ]* 9.3 编写 `ZZZLocomotionRules` 的属性测试（需本地运行）
    - **Property 11: GaitBlendY 目标值映射与非法取值容错** — **Validates: Requirements 1.6, 10.5, 11.1**
    - 输入覆盖 `uint8` 强制转换得到的全部 `Snapshot_Gait` 取值，含取值域之外的值；核对调用前后 `FZZZAnimSnapshot::Gait` 不被改写
    - `ZZZLocomotionRules` 为无状态纯函数，可直接驱动
    - 本任务为可选项：**编写测试文件本身不需要编译，但运行该测试需要用户在本地执行，本计划不代为运行**
    - _Requirements: 17.3_

  - [ ]* 9.4 编写 `FZZZLocomotionEvents` 的属性测试（需本地运行）
    - **Property 12: GaitBlendY 的区间、单帧上界与吸附** — **Validates: Requirements 4.11, 11.3, 11.4, 11.5, 11.6**
    - **Property 13: Gait_None 帧沿用上一帧目标值** — **Validates: Requirements 11.2**
    - **Property 14: 非 Moving 驻留与 Moving 入口的 GaitBlendY 规则**（`Snapshot_CurrentState` 非 `Moving` 时归零；`EnterMoving()` 按 `Snapshot_Gait == Run` 初始化为 `1.0`，其他步态或快照缺失初始化为 `0.0`；该规则优先于 Property 13 的目标值沿用规则）— **Validates: Requirements 11.9, 13.2**
    - 边界输入覆盖：插值速率取 `{NaN, ±Inf, -1, 0, 0.05, 6, 50, 51}`；`GaitBlendY` 起始值取 `{-1, 0, 0.0005, 0.5, 0.9995, 1, 2}`；帧间隔取 `{负值, 0, NaN, ±Inf, 0.0001, 0.1, 0.5}`；`Snapshot_CurrentState` 覆盖 `Moving` 与非 `Moving` 的任意排列，`Snapshot_Gait` 覆盖 `None` / `Walk` / `Run` 及非法值
    - 三个上下文结构体均可栈上构造，无需 `UWorld`
    - 本任务为可选项：**编写测试文件本身不需要编译，但运行该测试需要用户在本地执行，本计划不代为运行**
    - _Requirements: 17.3_

  - [ ]* 9.5 编写 `FZZZLocomotionDecisions` 的属性测试（需本地运行）
    - **Property 15: Conduit 分流判定互补** — **Validates: Requirements 12.2, 12.3, 12.4, 12.5**
    - 输入覆盖 `uint8` 强制转换得到的全部 `Snapshot_Gait` 取值与任意上下文有效性组合（含 `Snap` 为空指针）；核对两次调用前后 `FZZZAnimStateMemory` 的任何字段不发生变化
    - 本任务为可选项：**编写测试文件本身不需要编译，但运行该测试需要用户在本地执行，本计划不代为运行**
    - _Requirements: 17.3_

- [x] 10. Final checkpoint - 交付说明
  - 交付说明需包含：完整的文件映射表核对结果（4 个新增文件、20 个修改条目）、静态检查项 A 至 F 六组的逐项结论、Requirement 17.4 至 17.9 六个验证用例（U1 至 U6）的采集结果
  - 需显式记录两项设计已知取舍：`CurrentState` 的一帧观察延迟（`Walk` 计时起点比方向输入晚一帧，阈值达成的墙钟时刻最多晚 `0.1` 秒；U2 的判定基准取 `Walk_Hold_Timer` 累计值而非墙钟时长）、帧间隔无效时 Requirement 9.3 优先于全部归零条件
  - 需记录阶段一刻意接受的临时双写入方状态已在阶段二消除
  - 静态检查结论一律表述为「静态检查通过，编译待本地验证」，不表述为「编译通过」
  - _Requirements: 17.3, 17.10_


- [x] 11.1 新增 `Moving/EnterMove → Stop` 停止输入判定
  - 在 `FZZZLocomotionDecisions` 增加纯只读 `ShouldStopMoving()`：仅在上下文存在且 `Context.Snap->bShouldMove == false` 时返回 `true`，上下文缺失返回 `false`；不读取速度、`CurrentState`、`Gait` 或 `StateMemory`
  - 在 `UZZZAnimInstance` 增加 `BlueprintPure`、`BlueprintThreadSafe` 的 `Locomotion_ShouldStopMoving()`，直接转发到 `LocomotionDecisions.ShouldStopMoving()`
  - 注释与过渡函数清单明确该判定同时用于 `Moving → Stop` 和 `EnterMove → Stop`，不是速度为零判断，也不负责 `EnterMove → Moving` 的动画完成判断
  - `implementation-overview.md` 记录蓝图两条 Stop 过渡连接到 `Locomotion_ShouldStopMoving()`；`EnterMove → Moving` 仍由 AnimBP 的 `Time Remaining (ratio) <= 0` 直接处理
  - 仅完成 `Source/GGYGO/**` 静态核对，不执行编译或测试

- [x] 11.2 拆分 Moving/EnterMove → Stop 的 Blueprint 接口
  - 从 `UZZZAnimInstance` 删除单一的 `Locomotion_ShouldStopMoving()` UFUNCTION 及实现
  - 新增独立的 `BlueprintPure` + `BlueprintThreadSafe` 函数 `Locomotion_Moving_To_Stop()` 与 `Locomotion_EnterMove_To_Stop()`；两个函数都直接转发同一个 `LocomotionDecisions.ShouldStopMoving()` 底层判定
  - 保留 `FZZZLocomotionDecisions::ShouldStopMoving() const` 作为唯一停止逻辑：仅在 `Context.Snap` 存在且 `Context.Snap->bShouldMove == false` 时返回 true，上下文缺失返回 false，不读取速度、`CurrentState`、`Gait` 或 `StateMemory`
  - 更新 `ZZZLocomotionDecisions` / `ZZZAnimInstance` 类注释与过渡函数清单，说明两个 Blueprint 入口共享同一底层判定；`EnterMove → Moving` 仍由 AnimBP 的 `Time Remaining (ratio) <= 0` 直接处理
  - 仅完成 `Source/GGYGO/**` 静态核对，不执行编译或测试

## Notes

### 可选任务

- 带 `*` 的子任务（9.2 至 9.5）为可选项。设计已明确：工程内当前不存在测试源文件，属性测试的实现与执行不在本 spec 范围内，16 条属性表作为后续测试 spec 的直接输入。跳过后仍可得到完整的功能改造结果，但会失去 16 条属性的自动验证。
- 16 条属性按被测单元聚合为 4 个可选任务而非 16 个独立任务：4 个被测单元（`FGaitAuthorityProcessor`、`ZZZLocomotionRules`、`FZZZLocomotionEvents`、`FZZZLocomotionDecisions`）各自需要独立的测试夹具与生成器，按单元聚合可复用夹具；每条属性在任务内仍以独立条目列出属性号与其验证的需求条款。

### Checkpoint 的性质

- 任务 3 与任务 7 是**人工编译检查点**，不是代码任务。本计划不含任何编译、测试或构建步骤，编译一律由用户在本地执行。
- 任务 4 与任务 8 是**用户手动的编辑器操作节点**，Kiro 无法执行。任务 4 必须在阶段三之前完成（此时被移除的符号在 C++ 侧仍存在，蓝图可正常打开并逐条摘除引用）；任务 8 必须在任务 7 编译通过之后完成（新增的 `Locomotion_Conduit_To_Moving_Direct` 此时才可见）。
- 任务 9.1 的结论按 Requirement 17.3 只能写「静态检查通过，编译待本地验证」，不能写「编译通过」。

### 刻意接受的临时状态

- **阶段一的双写入方**：任务 1 完成后，`Resolved_Gait` 与 `Anim_Gait_Channel` 同时被旧 `FLocomotionIntentProcessor`（Tick 第 3 步）与新 `FGaitAuthorityProcessor`（Tick 第 3.5 步）写入。由于 `ProcessGait` 在 `ProcessIntents` 之后执行，落盘的最终取值来自新决策者，因此运行期步态行为已符合新规则。这个临时状态刻意存在，目的是让阶段一不删除任何东西，从而把「新增代码能否编译」与「删除旧规则是否有残留引用」两类问题分离到两个检查点上排查。该状态在任务 2.1 完成后消除，此后 Requirement 2.1 的唯一写入方约束才成立。
- **阶段一的 `bSprintTrigger` 残留脉冲**：阶段一期间 `FLocomotionIntentProcessor` 仍按 `PreviousGait != Sprint` 写 `AnimData.bSprintTrigger`，因此按住 Shift 仍可能触发一次动画层的 Sprint 分流。该残留在任务 2.1 删除赋值语句后消失，在任务 5.2 与 5.3 移除字段后彻底清理。
- **任务 4 解绑后的表现缺口**：蓝图解绑完成到任务 6 完成之间，`Moving` 内的 `Walk → Run` 过渡条件返回假，走跑升级表现暂时失效。任务 6 完成后该表现由 `GaitBlendY` 在 `WalkRun` BlendSpace 内承担。
- **阶段四内部的不可编译中间态**：任务 6.1 移除 `MovingGait` / `WalkHoldSeconds` 会同时打断 6.3 至 6.6 的现有引用，因此任务 6.1 至 6.6 必须全部完成后才构成可编译状态。这是该阶段的固有性质，不设中间检查点。

### 其他

- 阈值常量（`5.0` / `60.0` / `3600.0` / `0.1`）在逻辑侧 `FGaitAuthorityProcessor` 内**重新声明**，不从 `ZZZLocomotionRules` 复用：Requirement 10.4 要求把这些常量从动画层规则层移除，且逻辑侧不应对动画层头文件产生新的依赖方向。
- `LastGaitBlendTarget` 放在 `FZZZLocomotionEvents` 的私有成员而非 `FZZZAnimStateMemory`：后者最终只保留 `GaitBlendY`，且 AnimGraph 不需要读取目标值。
- 每个子任务都引用了具体的需求条款号（`_Requirements: X.Y_`），任务 9.1 的六组静态检查项以设计文档的「静态检查项清单」为唯一判定依据。
- 代码检索范围统一限定 `Source/GGYGO/**`；`.kiro/specs` 只用于读取需求、设计与任务文档。

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.2"] },
    { "id": 1, "tasks": ["1.3"] },
    { "id": 2, "tasks": ["1.4"] },
    { "id": 3, "tasks": ["1.5"] },
    { "id": 4, "tasks": ["1.6"] },
    { "id": 5, "tasks": ["2.1"] },
    { "id": 6, "tasks": ["2.2"] },
    { "id": 7, "tasks": ["3"] },
    { "id": 8, "tasks": ["4.1"] },
    { "id": 9, "tasks": ["5.1"] },
    { "id": 10, "tasks": ["5.2"] },
    { "id": 11, "tasks": ["5.3"] },
    { "id": 12, "tasks": ["5.4"] },
    { "id": 13, "tasks": ["6.1"] },
    { "id": 14, "tasks": ["6.2", "6.3"] },
    { "id": 15, "tasks": ["6.4"] },
    { "id": 16, "tasks": ["6.5"] },
    { "id": 17, "tasks": ["6.6"] },
    { "id": 18, "tasks": ["7"] },
    { "id": 19, "tasks": ["8.1", "8.2"] },
    { "id": 20, "tasks": ["9.1"] },
    { "id": 21, "tasks": ["9.2", "9.3", "9.4", "9.5"] },
    { "id": 22, "tasks": ["9.6"] },
    { "id": 23, "tasks": ["10"] },
    { "id": 24, "tasks": ["11.1"] },
    { "id": 25, "tasks": ["11.2"] },
  ]
}
```
