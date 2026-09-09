# Implementation Plan: zzz-anim-structure-refactor

## Overview

按「阶段一纯搬迁 → 本地编译检查点 → 阶段二引入新类型」的顺序实施。阶段一只做文件移动、拆分、include 修正与清理，不改动任何一行逻辑；阶段二才引入 `FZZZAnimReadContext` / `FZZZAnimWriteContext` 与 `ZZZLocomotionRules`。这样一旦本地编译报错，可以立刻判断问题属于路径没接上还是逻辑改错了。

实现语言为 C++（Unreal Engine）。**本计划不包含任何编译、测试或构建步骤**——用户明确要求编译由本地执行。所有任务的验证一律采用静态检查：文件存在性核对、目录内容核对、文本检索、签名与字段逐项比对。

阶段一与阶段二之间的检查点（任务 7）需要用户在本地编译确认后才继续，这是本计划唯一的人工介入点。

## Tasks

- [x] 1. 阶段一：Data 层文件拆分与移动
  - [x] 1.1 新建 `Public/Animation/zzzAnim/Data/ZZZAnimEnums.h` 并迁入两个枚举
    - 从 `ZZZAnimStateMemory.h` 原样迁出 `EZZZAnimLocomotionState` 与 `EZZZAnimMovingSubState`，包含其上方的说明注释
    - 保持两个枚举的 `UENUM(BlueprintType)` 说明符、`uint8` 底层类型、成员顺序与每个成员的 `UMETA(DisplayName)` 中文显示名逐字不变
    - `EZZZAnimLocomotionState` 成员顺序固定为 `None` / `NotMoving` / `Conduit` / `EnterMove` / `Moving`；`EZZZAnimMovingSubState` 固定为 `None` / `WalkRun` / `TurnBack`
    - include `CoreMinimal.h`，并以 `ZZZAnimEnums.generated.h` 作为最后一条 include
    - _Requirements: 1.3, 2.3, 3.1, 3.3, 3.4, 3.5, 7.6_

  - [x] 1.2 把 `CombatConfig.h` 拆成 `Data/ZZZAnimSet.h` 与 `Data/ZZZAnimTuning.h`
    - `ZZZAnimSet.h` 只含 `FZZZAnimSet`，保留 `Sequences` 与 `BlendSpaces` 两个 `TMap` 字段的名称、键值类型、`EditAnywhere` + `BlueprintReadOnly` 说明符与 `Locomotion` 分类
    - `ZZZAnimTuning.h` 只含 `FZZZAnimTuning`，保留四个字段的名称、默认值、分类与 `meta` 钳制：`LoopBlendIn = 0.1f`、`OneShotBlendOut = 0.15f`、`WalkToRunHoldSeconds = 5.f`（`ClampMin=0.1` `ClampMax=60.0`）、`GaitBlendInterpSpeed = 6.f`（`ClampMin=0.1` `ClampMax=50.0`）
    - 两个文件各自 include 自己的 `.generated.h` 并置于最后；`ZZZAnimSet.h` 保留 `UAnimSequence` 与 `UBlendSpace` 前向声明
    - 原有字段注释随字段一并迁移，包含「面板钳制只约束输入，运行期仍按事件层容错规则解析」这类约束说明
    - 删除 `Public/Animation/zzzAnim/CombatConfig.h`
    - _Requirements: 1.3, 2.1, 2.2, 3.1, 3.6, 3.7, 7.6, 9.7, 9.8_

  - [x] 1.3 移动 `ZZZAnimKeys.h` 到 `Data/`
    - 迁至 `Public/Animation/zzzAnim/Data/ZZZAnimKeys.h`，内容与 `ZZZAnimKeys::WalkRunBlendSpace` 常量取值 `"WalkRun"` 保持不变
    - 不添加 `.generated.h`
    - _Requirements: 1.3, 3.2_

  - [x] 1.4 移动 `ZZZAnimSnapshot.h` 到 `Data/` 并修正过期注释
    - 迁至 `Public/Animation/zzzAnim/Data/ZZZAnimSnapshot.h`
    - 文件注释中的 `CombatSnapshotCapture.cpp` 改为 `Capture/ZZZAnimSnapshotCapture.cpp`
    - `Gait` 字段来源注释中的 `AnimRuntimeData.NTE.Gait` 改为 `AnimRuntimeData.Gait`
    - 保持七个字段 `Gait`、`bShouldMove`、`bSprintTrigger`、`CurrentState`、`VelocityLength`、`bGrounded`、`bBlockMove` 的名称、类型与默认值不变，且保持为不含 `GENERATED_BODY` 的纯 C++ 结构体
    - 不添加 `.generated.h`
    - _Requirements: 1.3, 3.2, 7.1, 7.2, 10.5_

  - [x] 1.5 移动 `ZZZAnimStateMemory.h` 到 `Data/` 并改为引用枚举头
    - 迁至 `Public/Animation/zzzAnim/Data/ZZZAnimStateMemory.h`，删除文件内两个枚举定义，改为 include `Data/ZZZAnimEnums.h`
    - 保持 `FZZZAnimStateMemory` 六个字段的名称、类型、默认值、`BlueprintReadOnly` 说明符与 `Locomotion` 分类不变：`PreviousState`、`EnteredGait`、`bSprintTriggerPending`、`MovingGait = EMovementGait::Walk`、`WalkHoldSeconds = 0.f`、`GaitBlendY = 0.f`
    - 保留每个字段描述取值域与唯一写入方的注释
    - 以 `ZZZAnimStateMemory.generated.h` 作为最后一条 include
    - _Requirements: 1.3, 2.3, 3.1, 7.6, 9.6_

- [x] 2. 阶段一：Capture 层移动
  - [x] 2.1 把快照抓取器移入 `Capture/`
    - `ZZZAnimSnapshotCapture.h` 迁至 `Public/Animation/zzzAnim/Capture/`，`ZZZAnimSnapshotCapture.cpp` 迁至 `Private/Animation/zzzAnim/Capture/`
    - 更新头文件中对 `ZZZAnimSnapshot.h` 的 include 为新的 `Data/` 路径
    - 保持 `FZZZAnimSnapshotCapture::Capture` 的签名与函数体逐字不变，包括从 `AnimData` 读取的五个字段与从 `ABaseCharacter` 读取的 `IsGrounded()`
    - _Requirements: 1.1, 1.4, 10.4_

- [x] 3. 阶段一：Locomotion 层移动
  - [x] 3.1 把 `ZZZLocomotionDecisions` 移入 `Locomotion/`
    - 头文件迁至 `Public/Animation/zzzAnim/Locomotion/`，实现文件迁至 `Private/Animation/zzzAnim/Locomotion/`
    - 更新实现文件中对快照、记忆、配置三个头文件的 include 为新路径（`Data/ZZZAnimSnapshot.h`、`Data/ZZZAnimStateMemory.h`、`Data/ZZZAnimTuning.h`）
    - 本任务不改动 `SetContext` 签名、不改动四个判定函数的任何语句
    - 删除空目录 `Public/Animation/zzzAnim/CombatDecisions/` 与 `Private/Animation/zzzAnim/CombatDecisions/`
    - _Requirements: 1.1, 1.5, 1.7, 2.4, 2.5, 11.3_

  - [x] 3.2 把 `ZZZLocomotionEvents` 移入 `Locomotion/`
    - 头文件迁至 `Public/Animation/zzzAnim/Locomotion/`，实现文件迁至 `Private/Animation/zzzAnim/Locomotion/`
    - 更新 include 为新路径，此阶段仍保留对 `Locomotion/ZZZLocomotionDecisions.h` 的 include（解除依赖在任务 9.3 完成）
    - 本任务不改动 `SetContext` 签名、不改动 `AdvanceMovingGait` 与 `AdvanceGaitBlendY` 的任何语句、不删除私有解析函数
    - 删除空目录 `Public/Animation/zzzAnim/CombatEvents/` 与 `Private/Animation/zzzAnim/CombatEvents/`
    - _Requirements: 1.1, 1.5, 1.7, 2.4, 2.5, 11.3_

- [x] 4. 阶段一：日志类别统一
  - [x] 4.1 新增 `ZZZAnimLog.h` / `ZZZAnimLog.cpp` 并替换两处静态定义
    - `Public/Animation/zzzAnim/ZZZAnimLog.h` 以 `DECLARE_LOG_CATEGORY_EXTERN(LogZZZAnim, Log, All)` 声明
    - `Private/Animation/zzzAnim/ZZZAnimLog.cpp` 以 `DEFINE_LOG_CATEGORY(LogZZZAnim)` 定义，作为代码库中唯一定义处
    - 从 `ZZZAnimInstance.cpp` 与 `Locomotion/ZZZLocomotionEvents.cpp` 各删除一处 `DEFINE_LOG_CATEGORY_STATIC(LogZZZAnim, Log, All)`，改为 include `ZZZAnimLog.h`
    - 所有 `UE_LOG` 调用点的类别名、日志级别与消息文本格式保持逐字不变
    - 保持两处诊断节流行为不变：Events 的无效帧间隔诊断按 `Moving` 驻留节流并在离开时复位，AnimInstance 的 BlendSpace key 缺失诊断按 `Moving` 驻留节流
    - _Requirements: 6.1, 6.2, 6.3, 6.4, 6.5, 6.6_

- [x] 5. 阶段一：include 修正与外围核对
  - [x] 5.1 更新 `ZZZAnimInstance.h` / `.cpp` 的 include 路径
    - 头文件中把 `CombatConfig.h` 替换为 `Data/ZZZAnimSet.h` 与 `Data/ZZZAnimTuning.h`，把快照、抓取器、记忆、判定、事件的 include 全部改为新的 `Data/` `Capture/` `Locomotion/` 路径
    - 实现文件中把 `ZZZAnimKeys.h` 改为 `Data/ZZZAnimKeys.h`，并 include `ZZZAnimLog.h`
    - 保持类声明、成员顺序、全部十个 `UFUNCTION` 与四个 `UPROPERTY` 的反射签名、`PipelineDrive(float)` 签名逐字不变
    - 保持 `RefreshDecisionContext(float)` 的函数体在本阶段不变
    - _Requirements: 2.4, 9.1, 9.2, 9.3, 9.4, 9.5, 9.10, 9.11, 11.3_

  - [x] 5.2 核对外部调用点与模块配置
    - 确认 `Private/BaseCharacter.cpp` 无需修改：`Animation/zzzAnim/ZZZAnimInstance.h` 路径未变、`ZAI->PipelineDrive(DeltaTime)` 调用及其在管线末尾的位置不变
    - 检查 `GGYGO.Build.cs` 的 `PrivateIncludePaths` 等路径条目，若存在因 NTE 测试文件删除而失效的条目或需要补充的新子目录条目则更新，改动范围限于路径条目本身
    - 不修改模块依赖列表，不修改 `AnimSyncMarkerTools.h` / `.cpp`
    - _Requirements: 10.6, 10.7, 10.8, 10.9_

  - [x] 5.3 删除 NTE 残留空目录
    - 删除 `Public/Animation/Decisions/` 与 `Private/Animation/Decisions/` 两个空目录
    - 确认删除后 `Animation/` 下只剩 `AnimSyncMarkerTools` 与 `zzzAnim/`
    - _Requirements: 1.8_

- [x] 6. 阶段一静态验证
  - [x] 6.1 执行阶段一的静态检查项
    - 检索 `CombatConfig.h`、`CombatDecisions/`、`CombatEvents/` 在源码中的引用，要求结果数量为 `0`
    - 核对 `Data/` 下存在且仅存在六个头文件（`ZZZAnimContext.h` 属阶段二，此时尚未创建）
    - 核对 `Capture/` 与 `Locomotion/` 的文件构成符合设计的目录结构
    - 检索 `DEFINE_LOG_CATEGORY` 与 `DEFINE_LOG_CATEGORY_STATIC`，确认 `LogZZZAnim` 定义处数量为 `1` 且位于 `ZZZAnimLog.cpp`
    - 核对每个含 `USTRUCT` 或 `UENUM` 的新头文件都以对应 `.generated.h` 作为最后一条 include
    - 按设计文档的反射签名清单逐项比对十个 `UFUNCTION`、四个 `UPROPERTY` 以及三个结构体的字段
    - 确认 `Content` 目录无任何文件变更
    - 按 Requirement 12.11 把编辑器报告的 `CoreMinimal.h` / `UFUNCTION` / `UPROPERTY` / `TMap` 未解析归类为环境诊断并记录，不据此判定失败
    - 结论表述为「静态检查通过，编译待本地验证」
    - _Requirements: 11.2, 11.3, 11.5, 12.1, 12.2, 12.3, 12.4, 12.5, 12.8, 12.9, 12.10, 12.11, 12.12_

- [x] 7. Checkpoint - 阶段一本地编译
  - 阶段一只做文件搬迁与清理，逻辑与重构前完全一致，此时应可独立编译通过
  - 请在本地执行编译验证；编译前建议清理 `Intermediate/Build`，因为旧 NTE 动画层删除后该目录仍残留陈旧的 UHT 生成产物与目标文件
  - 确认编译通过后再继续阶段二；若报错请提供错误信息，此时问题必定落在 include 路径或 UHT 生成产物上，与逻辑无关
  - _Requirements: 11.5, 11.6, 12.13_

- [x] 8. 阶段二：上下文聚合
  - [x] 8.1 新增 `Data/ZZZAnimContext.h`
    - 定义 `FZZZAnimReadContext`，成员为 `const FZZZAnimSnapshot* Snap`、`const FZZZAnimTuning* Tuning`、`const FZZZAnimStateMemory* Memory`，默认值均为 `nullptr`
    - 定义 `FZZZAnimWriteContext`，成员为 `const FZZZAnimSnapshot* Snap`、`const FZZZAnimTuning* Tuning`、`FZZZAnimStateMemory* Memory`，默认值均为 `nullptr`
    - 两者各提供 `bool IsValid() const`，当且仅当三个指针全部非空时返回真
    - `FZZZAnimWriteContext` 提供转换函数返回以自身三指针构造的 `FZZZAnimReadContext`
    - 均为纯 C++ 结构体，不带 `USTRUCT`、不 include `.generated.h`、不拥有所指对象生命周期，仅用前向声明引入三个类型
    - _Requirements: 1.3, 3.2, 4.1, 4.2, 4.3, 4.4, 4.5_

  - [x] 8.2 `FZZZLocomotionDecisions` 改用只读上下文
    - `SetContext` 改为接收单个 `const FZZZAnimReadContext&`，以 `FZZZAnimReadContext` 成员替换原有三个独立指针成员
    - 四个判定函数的名称、参数、返回类型与 `const` 修饰保持不变，函数体内指针访问改为经上下文成员访问
    - 各函数保持其重构前实际检查的指针集合不变：`NotMoving_To_Conduit` 只检查快照指针，两个 Conduit 判定只检查记忆指针，`Moving_Walk_To_Run_ByHold` 检查三个指针，不统一改用 `IsValid()`
    - 通过只读上下文访问记忆结构，使编译器阻止任何写入
    - _Requirements: 4.6, 4.8, 4.10, 8.9, 9.1, 9.2_

  - [x] 8.3 `FZZZLocomotionEvents` 改用可写上下文
    - `SetContext` 改为接收单个 `const FZZZAnimWriteContext&`，以 `FZZZAnimWriteContext` 成员替换原有指针成员
    - 保留 `LastEnteredState`、`CurrentSubState`、`bInvalidDeltaReported` 三个私有状态成员
    - 五个公开函数与两个私有辅助函数的名称、参数、返回类型保持不变，函数体内指针访问改为经上下文成员访问
    - `AdvanceMovingGait` 保持其原有的两指针检查（快照与记忆），不改用 `IsValid()`，以保证配置指针为空时仍按默认值继续推进
    - 保持 `AdvanceMovingGait` 的八步执行顺序、帧间隔分支、诊断节流与数值区间行为逐帧不变
    - _Requirements: 4.7, 4.10, 8.2, 8.3, 8.7, 8.9_

  - [x] 8.4 `UZZZAnimInstance` 构造并分发上下文
    - `RefreshDecisionContext(float)` 内构造一份 `FZZZAnimWriteContext`，以其降级视图注入判定层、以其自身注入事件层
    - 保持固定顺序：抓取快照 → 锁存冲刺脉冲 → 注入上下文 → 调用 `AdvanceMovingGait(DeltaSeconds)`
    - 保持 `bSprintTriggerPending` 置真为唯一实现处
    - 两次注入之间不得存在功能上的先后依赖
    - 不改动任何 `UFUNCTION` 与 `UPROPERTY`，不改动 `PipelineDrive(float)` 签名
    - _Requirements: 4.9, 8.6, 9.9, 9.10_

- [x] 9. 阶段二：抽出无状态规则层
  - [x] 9.1 新增 `Locomotion/ZZZLocomotionRules.h` / `.cpp`
    - 定义 `ZZZLocomotionRules` 命名空间，全部函数为无状态纯函数，不持有上下文、无副作用、对相同输入返回相同结果
    - 集中定义七个数值常量：默认阈值 `5.0`、阈值上限 `60.0`、默认插值速率 `6.0`、插值速率上限 `50.0`、行走时长上界 `3600.0`、帧间隔上界 `0.1`、插值吸附容差 `0.001`
    - 实现阈值解析：配置指针为空、值非有限或小于等于 `0.0` 时返回 `5.0`，否则返回该值与 `60.0` 的较小者
    - 实现插值速率解析：配置指针为空时返回 `6.0`，值非有限或小于等于 `0.0` 时返回 `0.0`，否则返回该值与 `50.0` 的较小者
    - 实现 Walk 升 Run 的纯值判定，参数为有效步态、累计行走时长与生效阈值
    - 实现步态取值域校验与 `GaitBlendY` 目标值推导两个辅助函数
    - 全部解析函数不改写配置字段的存储取值；本文件不 include 判定层、事件层或 AnimInstance 头文件，不 include `.generated.h`
    - _Requirements: 1.5, 3.2, 5.1, 5.2, 5.3, 5.4, 5.5, 5.9, 5.10_

  - [x] 9.2 `FZZZLocomotionDecisions` 改调规则层
    - `Moving_Walk_To_Run_ByHold` 改为调用规则层完成阈值解析与条件判定，删除函数体内重复实现的阈值容错规则
    - 保持三指针空值检查在函数级别，使配置指针为空时该函数仍返回假，与重构前行为一致
    - 保持函数名、`const` 修饰与返回类型不变
    - _Requirements: 5.7, 8.9, 9.2_

  - [x] 9.3 `FZZZLocomotionEvents` 改调规则层并解除反向依赖
    - 删除私有的阈值解析与插值速率解析函数，改为调用规则层
    - 删除指向 `FZZZLocomotionDecisions` 的成员与 `SetContext` 中对应参数，删除对 `ZZZLocomotionDecisions.h` 的 include
    - `AdvanceMovingGait` 的跨阈升级步骤改为经规则层判定，保持其位于行走时长推进之后、`GaitBlendY` 插值之前
    - `AdvanceGaitBlendY` 改用规则层的常量与目标值推导，保持恒定速率插值、单帧变化量上界、不越过目标值与吸附容差行为不变
    - 按 Requirement 8.8 接受配置指针为空时的升级行为差异，并在实现注释中标注该差异为显式设计决策
    - _Requirements: 5.6, 5.8, 8.2, 8.3, 8.4, 8.8_

- [x] 10. 阶段二：文档与注释收尾
  - [x] 10.1 清理过期引用并同步 steering
    - 检查 ZZZ 动画层全部源文件中对 `UNTEAnimInstance`、`Animation/Decisions`、`LocomotionConfig`、`FAnimSnapshot` 的注释引用，移除或修正已确认过期的部分
    - 更新 `.kiro/steering/user-preferences.md` 中对 ZZZ 动画层源码路径的描述，使其与 `Data/` `Capture/` `Locomotion/` 的新结构一致
    - 保持所有注释使用中文，不删除描述设计意图、取值域约束或唯一写入方的注释
    - _Requirements: 7.3, 7.4, 7.5, 7.6_

- [x] 11. 阶段二静态验证
  - [x] 11.1 执行阶段二的静态检查项
    - 检索七个数值常量，确认每个在 ZZZ 动画层中的定义处数量为 `1` 且位于 `Locomotion/ZZZLocomotionRules.h`
    - 检索 `ZZZLocomotionEvents.h` 与 `ZZZLocomotionEvents.cpp` 中对 `FZZZLocomotionDecisions` 的引用，要求结果数量为 `0`
    - 确认 `Data/` 下存在全部七个头文件，`Locomotion/` 下存在三组头文件与实现文件
    - 再次按设计文档的反射签名清单逐项比对十个 `UFUNCTION`、四个 `UPROPERTY` 与三个结构体字段，确认与阶段一验证结果一致
    - 核对 `AdvanceMovingGait` 的执行顺序、各分支的指针检查集合与数值区间与设计描述一致
    - 确认 `Content` 目录无任何文件变更
    - 结论表述为「静态检查通过，编译待本地验证」
    - _Requirements: 12.1, 12.2, 12.4, 12.5, 12.6, 12.7, 12.9, 12.12_

  - [ ]* 11.2 编写重构等价性属性测试（需本地运行）
    - **Property: 重构前后记忆字段逐帧等价** — 给定相同的快照序列、配置取值与帧间隔序列，`MovingGait`、`WalkHoldSeconds`、`GaitBlendY`、`bSprintTriggerPending` 的逐帧取值与重构前完全一致
    - 覆盖边界输入：帧间隔取 `{负值, 0, NaN, +Inf, -Inf, 0.0001, 0.1, 0.5}`；`GaitBlendY` 起始值取 `{-1, 0, 0.0005, 0.5, 0.9995, 1, 2}`；`WalkHoldSeconds` 起始值取 `{0, 阈值-0.001, 阈值, 3599.99, 3600, 100000}`；`WalkToRunHoldSeconds` 取 `{NaN, -1, 0, 0.05, 5, 60, 61}`；`GaitBlendInterpSpeed` 取 `{NaN, -1, 0, 0.05, 6, 50, 51}`；`MovingGait` 含取值域外强转值
    - 基于 `FRandomStream` 实现确定性生成器，迭代次数不少于 `100`，固定种子起步并在失败信息中打印种子与该次输入
    - 本任务为可选项：编写测试文件本身不需要编译，但**运行**该测试需要用户在本地执行，本计划不代为运行
    - **Validates: Requirements 8.1, 8.2, 8.3, 8.4, 8.5, 8.6, 8.7**

- [x] 12. Final checkpoint - 阶段二本地编译与交付说明
  - 请在本地执行编译验证；若阶段一已编译通过，此处的报错范围应限于上下文聚合与规则层抽取涉及的文件
  - 交付说明需包含：完整的文件映射表、反射签名核对结果、Requirement 8.8 所述配置指针为空时的行为差异记录、以及本地编译前清理 `Intermediate/Build` 的提示
  - 静态检查结论一律表述为「静态检查通过，编译待本地验证」，不表述为「通过」
  - _Requirements: 12.12, 12.13_

## Notes

- 带 `*` 的子任务为可选项，跳过后仍可得到完整的重构结果，但会失去重构前后行为等价的自动验证
- 本计划**不含任何编译、测试或构建步骤**。任务 7 与任务 12 是两个人工检查点，需要用户在本地执行编译后确认
- 阶段一（任务 1 至 6）严格不改动任何函数签名、控制流语句、数值常量与字段声明，因此该阶段结束时逻辑与重构前完全一致
- 阶段二（任务 8 至 11）才引入 `FZZZAnimReadContext` / `FZZZAnimWriteContext` 与 `ZZZLocomotionRules`
- 任务 8.2、8.3 刻意**不把各函数的指针空值检查统一改成 `IsValid()`**：`AdvanceMovingGait` 原本只检查两个指针，配置指针为空时靠默认值继续推进；统一后会把该情形从「用默认值继续」变成「直接返回」，属于行为变化
- 任务 9.2 与 9.3 都调用同一个规则层实现，这是 Requirement 5「每个判定条件恰有一处实现」的直接落点；重构前该规则在判定层与事件层各写了一遍
- Requirement 8.8 记录的行为差异是本次重构唯一被接受的行为变化，正常运行路径不可达，因为 AnimInstance 始终注入其成员配置对象的地址
- 反射签名清单位于设计文档，任务 6.1 与 11.1 两次核对都以该清单为依据

## Task Dependency Graph

```json
{
  "waves": [
    { "id": 0, "tasks": ["1.1", "1.3", "1.4"] },
    { "id": 1, "tasks": ["1.2", "1.5"] },
    { "id": 2, "tasks": ["2.1", "3.1"] },
    { "id": 3, "tasks": ["3.2", "4.1"] },
    { "id": 4, "tasks": ["5.1"] },
    { "id": 5, "tasks": ["5.2", "5.3"] },
    { "id": 6, "tasks": ["6.1"] },
    { "id": 7, "tasks": ["7"] },
    { "id": 8, "tasks": ["8.1"] },
    { "id": 9, "tasks": ["8.2", "8.3"] },
    { "id": 10, "tasks": ["8.4"] },
    { "id": 11, "tasks": ["9.1"] },
    { "id": 12, "tasks": ["9.2", "9.3"] },
    { "id": 13, "tasks": ["10.1"] },
    { "id": 14, "tasks": ["11.1", "11.2"] },
    { "id": 15, "tasks": ["12"] }
  ]
}
```
