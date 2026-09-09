# Requirements Document

## Introduction

本功能对 ZZZ 动画层（`Source/GGYGO/{Public,Private}/Animation/zzzAnim/`）执行一次**纯结构重构**，目标是消除目录组织、命名语义与依赖方向上的混乱，同时严格保持运行期行为不变。

范围限定在 `Animation/zzzAnim/` 目录内的文件组织、类型划分与内部依赖关系。本功能不新增游戏机制、不修改走跑步态的任何判定规则或数值语义、不触碰 `Content` 下的任何资产、不改动 `FIntentPipeline` 与 `FRuntimeData`。

重构包含四项结构改动与三项清理：

**结构改动**：按职责把文件重组为 `Data/` `Capture/` `Locomotion/` 三个子目录；把 `CombatConfig.h` 拆成 `ZZZAnimSet.h` 与 `ZZZAnimTuning.h`；引入 `FZZZAnimReadContext` / `FZZZAnimWriteContext` 聚合上下文指针；抽出无状态 `ZZZLocomotionRules` 作为判定规则与配置解析的唯一实现处，并解除 `ZZZ_Locomotion_Events` 对 `ZZZ_Locomotion_Decisions` 的反向依赖。

**清理**：统一 `LogZZZAnim` 日志类别定义；修正 `ZZZAnimSnapshot.h` 中指向不存在文件与已删除 NTE 层的过期注释；删除 NTE 动画层删除后残留的空目录。

由于用户明确要求编译由本地执行，本功能的全部验证均为静态检查，不包含运行 Unreal 编译、Automation 测试或构建脚本的步骤。

## Glossary

- **ZZZ_Animation_Layer**：以 `UZZZAnimInstance` 为 C++ 决策载体、ZZZ AnimBP 为蓝图消费端的动画层，源码位于 `Animation/zzzAnim/`。
- **ZZZ_Locomotion_Decisions**：`FZZZLocomotionDecisions`，只读判断过渡条件的模块，其全部判定函数为 `const` 且不产生副作用。
- **ZZZ_Locomotion_Events**：`FZZZLocomotionEvents`，处理 AnimBP `On Entry` 事件与跨帧记忆写入的模块，是 `MovingGait`、`WalkHoldSeconds`、`GaitBlendY` 的唯一写入方。
- **ZZZ_Locomotion_Rules**：本功能新增的 `ZZZLocomotionRules` 命名空间，承载无状态纯函数形式的判定规则与配置解析，无副作用、不持有上下文。
- **Read_Context**：本功能新增的 `FZZZAnimReadContext`，聚合 `const FZZZAnimSnapshot*`、`const FZZZAnimTuning*`、`const FZZZAnimStateMemory*` 三个只读指针。
- **Write_Context**：本功能新增的 `FZZZAnimWriteContext`，聚合 `const FZZZAnimSnapshot*`、`const FZZZAnimTuning*`、可写 `FZZZAnimStateMemory*`，并提供降级为 `Read_Context` 的转换。
- **Context_Refresh**：`UZZZAnimInstance::RefreshDecisionContext(float)` 每帧一次的上下文刷新流程，负责抓取快照、锁存冲刺脉冲、注入上下文、推进跨帧记忆。
- **Reflected_Signature**：参与 Unreal 反射的对外契约，包含 `UFUNCTION` 的函数名、参数列表、返回类型、反射说明符与 `Category`，以及 `UPROPERTY` 的字段名、类型、默认值、反射说明符、`Category` 与 `meta` 钳制。
- **Phase_One**：重构的第一阶段，只做文件移动、拆分、include 修正、注释与日志清理，不改动任何逻辑语句。
- **Phase_Two**：重构的第二阶段，引入 `Read_Context` / `Write_Context` 与 `ZZZ_Locomotion_Rules`，并解除反向依赖。
- **Behavioral_Equivalence**：给定相同的快照序列、配置取值与帧间隔序列，重构前后 `MovingGait`、`WalkHoldSeconds`、`GaitBlendY`、`bSprintTriggerPending` 四个记忆字段的逐帧取值完全一致。
- **Static_Verification**：不执行编译、测试或构建，仅通过文件存在性检查、文本检索、签名逐项比对完成的验证方式。
- **Unreal_Environment_Diagnostic**：因 Unreal Header Tool、模块 include path 或编辑器索引未加载 Unreal 头文件而产生的诊断信息，例如 `CoreMinimal.h`、`UFUNCTION`、`UPROPERTY`、`TMap` 未识别。

## Requirements

### Requirement 1: 目录结构按职责重组

**User Story:** 作为项目维护者，我想让 ZZZ 动画层的目录反映职责分层，以便从目录名就能定位代码归属。

#### Acceptance Criteria

1. THE `ZZZ_Animation_Layer` SHALL 在 `Public/Animation/zzzAnim/` 与 `Private/Animation/zzzAnim/` 下建立 `Data/`、`Capture/`、`Locomotion/` 三个子目录，其中 `Data/` 只存放数据类型定义、`Capture/` 只存放快照抓取实现、`Locomotion/` 只存放 Locomotion 的规则、判定与事件实现。
2. THE `ZZZ_Animation_Layer` SHALL 保持顶层目录名为 `zzzAnim` 不变，且 SHALL NOT 重命名 `Animation/` 与 `zzzAnim/` 这两级路径。
3. THE `Data/` 子目录 SHALL 包含且仅包含以下七个头文件：`ZZZAnimEnums.h`、`ZZZAnimSet.h`、`ZZZAnimTuning.h`、`ZZZAnimKeys.h`、`ZZZAnimSnapshot.h`、`ZZZAnimStateMemory.h`、`ZZZAnimContext.h`。
4. THE `Capture/` 子目录 SHALL 包含 `ZZZAnimSnapshotCapture.h`（位于 `Public/`）与 `ZZZAnimSnapshotCapture.cpp`（位于 `Private/`）。
5. THE `Locomotion/` 子目录 SHALL 包含 `ZZZLocomotionRules`、`ZZZLocomotionDecisions`、`ZZZLocomotionEvents` 三组头文件与实现文件，头文件位于 `Public/`、实现文件位于 `Private/`。
6. THE `ZZZAnimInstance.h` 与 `ZZZAnimInstance.cpp` SHALL 保留在 `zzzAnim/` 顶层，不移入任何子目录。
7. WHEN 重构完成, THE `ZZZ_Animation_Layer` SHALL 不存在 `CombatDecisions/` 与 `CombatEvents/` 目录；WHERE 这两个目录在文件移出后成为空目录, THE 重构 SHALL 将其删除。
8. WHEN 重构完成, THE 代码库 SHALL 不存在 `Public/Animation/Decisions/` 与 `Private/Animation/Decisions/` 目录，这两个目录是旧 NTE 动画层删除后的空目录残留。

### Requirement 2: 消除命名与内容不符

**User Story:** 作为项目维护者，我想让文件名与其内容一致，以便按名称检索时不被误导。

#### Acceptance Criteria

1. WHEN 重构完成, THE 代码库 SHALL 不存在名为 `CombatConfig.h` 的文件，其内容按类型归属拆分到 `Data/ZZZAnimSet.h` 与 `Data/ZZZAnimTuning.h`。
2. THE `Data/ZZZAnimSet.h` SHALL 包含且仅包含 `FZZZAnimSet` 的定义；THE `Data/ZZZAnimTuning.h` SHALL 包含且仅包含 `FZZZAnimTuning` 的定义。
3. THE `Data/ZZZAnimEnums.h` SHALL 包含 `EZZZAnimLocomotionState` 与 `EZZZAnimMovingSubState` 两个枚举定义；THE `Data/ZZZAnimStateMemory.h` SHALL 包含 `FZZZAnimStateMemory` 的定义且不再重复定义这两个枚举。
4. WHEN 重构完成, THE `ZZZ_Animation_Layer` 的任何源文件 SHALL NOT 以 `Combat` 作为文件名前缀或目录名前缀。
5. THE 重构 SHALL 使 `Locomotion/` 下每个文件的名称与其承载的职责对应：`ZZZLocomotionRules` 承载无状态规则、`ZZZLocomotionDecisions` 承载只读判定、`ZZZLocomotionEvents` 承载记忆写入事件。
6. THE 重构 SHALL NOT 重命名任何 C++ 类型标识符，包括 `FZZZAnimSet`、`FZZZAnimTuning`、`FZZZAnimSnapshot`、`FZZZAnimStateMemory`、`EZZZAnimLocomotionState`、`EZZZAnimMovingSubState`、`FZZZAnimSnapshotCapture`、`FZZZLocomotionDecisions`、`FZZZLocomotionEvents` 与 `UZZZAnimInstance`。

### Requirement 3: 反射类型拆分与 UHT 完备性

**User Story:** 作为动画程序员，我想让拆分后的反射头文件仍能被 UHT 正确处理，以便蓝图与已保存资产的数据绑定不断裂。

#### Acceptance Criteria

1. THE `Data/ZZZAnimEnums.h`、`Data/ZZZAnimSet.h`、`Data/ZZZAnimTuning.h`、`Data/ZZZAnimStateMemory.h` 中每一个文件 SHALL 包含与自身文件名对应的 `.generated.h`，且该 include SHALL 是该文件的最后一条 include 语句。
2. THE `Data/ZZZAnimSnapshot.h`、`Data/ZZZAnimContext.h`、`Data/ZZZAnimKeys.h`、`Locomotion/ZZZLocomotionRules.h` SHALL NOT 包含任何 `.generated.h`，因为这些文件不定义参与反射的类型。
3. THE 重构 SHALL 保持 `EZZZAnimLocomotionState` 的枚举成员顺序为 `None`、`NotMoving`、`Conduit`、`EnterMove`、`Moving`，且保持每个成员的 `UMETA(DisplayName)` 中文显示名不变。
4. THE 重构 SHALL 保持 `EZZZAnimMovingSubState` 的枚举成员顺序为 `None`、`WalkRun`、`TurnBack`，且保持每个成员的 `UMETA(DisplayName)` 中文显示名不变。
5. THE 重构 SHALL 保持两个枚举的 `UENUM(BlueprintType)` 说明符与 `uint8` 底层类型不变。
6. THE 重构 SHALL 保持 `FZZZAnimSet` 与 `FZZZAnimTuning` 的 `USTRUCT(BlueprintType)` 说明符与 `GENERATED_BODY()` 宏不变。
7. IF 拆分后任一头文件缺少必要的类型前向声明或 include, THEN THE 重构 SHALL 在该文件中补齐，且补齐范围 SHALL 限于该文件实际使用到的类型。

### Requirement 4: 上下文聚合与读写权限分离

**User Story:** 作为动画程序员，我想让上下文以结构体形式注入且读写权限由类型保证，以便新增上下文字段时不必修改函数签名，只读约束也不再只靠注释。

#### Acceptance Criteria

1. THE `Data/ZZZAnimContext.h` SHALL 定义 `FZZZAnimReadContext`，其成员为 `const FZZZAnimSnapshot* Snap`、`const FZZZAnimTuning* Tuning`、`const FZZZAnimStateMemory* Memory`，三者默认值均为 `nullptr`。
2. THE `Data/ZZZAnimContext.h` SHALL 定义 `FZZZAnimWriteContext`，其成员为 `const FZZZAnimSnapshot* Snap`、`const FZZZAnimTuning* Tuning`、`FZZZAnimStateMemory* Memory`，三者默认值均为 `nullptr`。
3. THE `FZZZAnimReadContext` 与 `FZZZAnimWriteContext` SHALL 各自提供 `bool IsValid() const`，当且仅当三个指针成员全部非空时返回真。
4. THE `FZZZAnimWriteContext` SHALL 提供转换函数，返回以自身三个指针构造的 `FZZZAnimReadContext`，使可写上下文能降级为只读视图。
5. THE `FZZZAnimReadContext` 与 `FZZZAnimWriteContext` SHALL 为纯 C++ 结构体，不带 `USTRUCT` 说明符、不参与反射、不持有所指对象的生命周期。
6. THE `ZZZ_Locomotion_Decisions` SHALL 以 `FZZZAnimReadContext` 作为唯一上下文成员，其 `SetContext` SHALL 接收单个 `const FZZZAnimReadContext&` 参数，替代重构前的三个独立指针参数。
7. THE `ZZZ_Locomotion_Events` SHALL 以 `FZZZAnimWriteContext` 作为唯一上下文成员，其 `SetContext` SHALL 接收单个 `const FZZZAnimWriteContext&` 参数。
8. THE `ZZZ_Locomotion_Decisions` SHALL 通过 `FZZZAnimReadContext` 访问 `FZZZAnimStateMemory`，使编译器阻止其对该结构的任何写入。
9. THE `Context_Refresh` SHALL 构造一份 `FZZZAnimWriteContext`，以其降级视图注入 `ZZZ_Locomotion_Decisions`、以其自身注入 `ZZZ_Locomotion_Events`，且这两次注入之间 SHALL NOT 存在先后顺序上的功能依赖。
10. THE 重构 SHALL NOT 把 `ZZZ_Locomotion_Decisions` 各判定函数与 `ZZZ_Locomotion_Events::AdvanceMovingGait` 中原有的指针空值检查统一替换为 `IsValid()`，各函数 SHALL 保持其重构前实际检查的指针集合不变。

### Requirement 5: 规则层唯一实现与依赖方向

**User Story:** 作为动画程序员，我想让判定规则与配置解析只有一处实现，以便修改阈值语义时不会漏改。

#### Acceptance Criteria

1. THE `Locomotion/ZZZLocomotionRules.h` SHALL 定义 `ZZZLocomotionRules` 命名空间，其中每个函数 SHALL 为无状态纯函数：不持有上下文成员、不产生副作用、不写入任何字段，且对相同输入返回相同结果。
2. THE `ZZZ_Locomotion_Rules` SHALL 提供解析生效 Walk 升 Run 阈值的函数，其规则为：传入的 `FZZZAnimTuning` 指针为空、或 `WalkToRunHoldSeconds` 为非有限数值、或该值小于或等于 `0.0` 时返回 `5.0`；否则返回该值与 `60.0` 中的较小者。
3. THE `ZZZ_Locomotion_Rules` SHALL 提供解析生效 `GaitBlendY` 插值速率的函数，其规则为：传入的 `FZZZAnimTuning` 指针为空时返回 `6.0`；`GaitBlendInterpSpeed` 为非有限数值或小于或等于 `0.0` 时返回 `0.0`；否则返回该值与 `50.0` 中的较小者。
4. THE `ZZZ_Locomotion_Rules` SHALL 提供判断 Walk 是否达到升 Run 条件的纯值函数，其参数为当前有效步态、累计行走时长与生效阈值，返回步态等于 `EMovementGait::Walk` 且累计行走时长大于或等于生效阈值的合取结果。
5. THE 解析函数 SHALL NOT 改写 `FZZZAnimTuning` 中任何配置字段的存储取值。
6. WHEN 重构完成, THE `ZZZ_Locomotion_Events` SHALL NOT 声明或定义任何私有的阈值解析或插值速率解析函数，此类解析 SHALL 全部委托给 `ZZZ_Locomotion_Rules`。
7. WHEN 重构完成, THE `ZZZ_Locomotion_Decisions` 中判断 Walk 升 Run 的函数 SHALL 通过调用 `ZZZ_Locomotion_Rules` 完成阈值解析与条件判定，SHALL NOT 在函数体内重复实现阈值容错规则。
8. WHEN 重构完成, THE `ZZZ_Locomotion_Events` SHALL NOT 持有指向 `ZZZ_Locomotion_Decisions` 的成员、参数或任何形式的引用，且其头文件与实现文件 SHALL NOT include `ZZZLocomotionDecisions.h`。
9. THE 重构 SHALL 使数值常量 `5.0`（默认阈值）、`60.0`（阈值上限）、`6.0`（默认插值速率）、`50.0`（插值速率上限）、`3600.0`（行走时长上界）、`0.1`（帧间隔上界）、`0.001`（插值吸附容差）各自在 `ZZZ_Animation_Layer` 中恰有一处定义，且该定义位于 `Locomotion/ZZZLocomotionRules.h`。
10. THE `ZZZ_Locomotion_Rules` SHALL NOT include `ZZZLocomotionDecisions.h`、`ZZZLocomotionEvents.h` 或 `ZZZAnimInstance.h`，使依赖方向保持为规则层被判定层与事件层依赖的单向关系。

### Requirement 6: 日志类别统一

**User Story:** 作为开发者，我想让 ZZZ 动画层的日志类别只有一处定义，以便统一控制输出级别。

#### Acceptance Criteria

1. THE `zzzAnim/ZZZAnimLog.h` SHALL 以 `DECLARE_LOG_CATEGORY_EXTERN` 声明名为 `LogZZZAnim` 的日志类别，其默认级别为 `Log`、编译期最大级别为 `All`。
2. THE `zzzAnim/ZZZAnimLog.cpp` SHALL 以 `DEFINE_LOG_CATEGORY` 定义 `LogZZZAnim`，且该定义 SHALL 是整个代码库中唯一的 `LogZZZAnim` 定义。
3. WHEN 重构完成, THE `ZZZAnimInstance.cpp` 与 `ZZZLocomotionEvents.cpp` SHALL NOT 包含 `DEFINE_LOG_CATEGORY_STATIC(LogZZZAnim, ...)`，改为 include `ZZZAnimLog.h`。
4. THE 重构 SHALL 保持所有 `UE_LOG` 调用点的日志类别名 `LogZZZAnim`、日志级别与消息文本格式完全不变。
5. THE 重构 SHALL 保持 `ZZZ_Locomotion_Events` 中无效帧间隔诊断的节流行为不变：在一次 `Moving` 驻留期间至多输出一次，并在离开 `Moving` 时复位节流标记。
6. THE 重构 SHALL 保持 `UZZZAnimInstance` 中 BlendSpace key 缺失诊断的节流行为不变：在一次 `Moving` 驻留期间至多输出一次。

### Requirement 7: 过期注释与残留清理

**User Story:** 作为项目维护者，我想让注释描述与实际代码一致，以便新人不被过期信息误导。

#### Acceptance Criteria

1. THE `Data/ZZZAnimSnapshot.h` 的文件注释 SHALL NOT 引用不存在的文件名 `CombatSnapshotCapture.cpp`，SHALL 改为引用实际的 `Capture/ZZZAnimSnapshotCapture.cpp`。
2. THE `Data/ZZZAnimSnapshot.h` 中 `Gait` 字段的来源注释 SHALL NOT 引用已删除的 NTE 动画层路径 `AnimRuntimeData.NTE.Gait`，SHALL 改为实际读取的 `AnimRuntimeData.Gait`。
3. THE 重构 SHALL 检查 `ZZZ_Animation_Layer` 全部源文件中对 `UNTEAnimInstance`、`Animation/Decisions`、`LocomotionConfig`、`FAnimSnapshot` 的注释引用，并将确认过期的引用移除或修正。
4. THE 重构 SHALL 更新 `.kiro/steering/user-preferences.md` 中对 ZZZ 动画层源码路径的描述，使其与重构后的子目录结构一致。
5. THE 重构 SHALL 保持所有注释使用中文，与既有 ZZZ 源文件的注释语言一致。
6. THE 重构 SHALL NOT 删除描述设计意图、取值域约束或唯一写入方的注释，此类注释 SHALL 随其所属声明一并迁移到新文件。

### Requirement 8: 运行期行为等价

**User Story:** 作为动画程序员，我想让重构后的走跑行为与重构前逐帧一致，以便确认这次改动不引入回归。

#### Acceptance Criteria

1. GIVEN 相同的快照序列、相同的 `FZZZAnimTuning` 配置取值与相同的帧间隔序列, THE 重构后的 `ZZZ_Animation_Layer` SHALL 产生与重构前完全一致的 `MovingGait`、`WalkHoldSeconds`、`GaitBlendY`、`bSprintTriggerPending` 逐帧取值。
2. THE 重构 SHALL 保持 `ZZZ_Locomotion_Events::AdvanceMovingGait` 的执行顺序不变：上下文校验、顶层状态门控、步态取值域纠正、帧间隔校验、帧间隔钳制、行走时长推进与重置、跨阈升级、`GaitBlendY` 插值。
3. THE 重构 SHALL 保持帧间隔钳制区间为 `[0.0, 0.1]`、`WalkHoldSeconds` 取值域为 `[0.0, 3600.0]`、`GaitBlendY` 取值域为 `[0.0, 1.0]`、插值吸附容差为 `0.001`。
4. THE 重构 SHALL 保持 `GaitBlendY` 使用恒定速率插值，其单帧变化量上界为生效插值速率与钳制后帧间隔之积，且不越过目标值。
5. THE 重构 SHALL 保持两条 `Moving` 进入路径的初始化结果不变：经 `Conduit` 进入得到步态 `Run`、`GaitBlendY` 为 `1.0`、行走时长为 `0.0` 并消费冲刺锁存；经其他路径进入得到步态 `Walk`、`GaitBlendY` 为 `0.0`、行走时长为 `0.0` 且不改写冲刺锁存。
6. THE 重构 SHALL 保持 `bSprintTriggerPending` 的置真位置唯一且位于 `Context_Refresh`，置假位置唯一且位于 `ZZZ_Locomotion_Events` 的冲刺消费函数。
7. THE 重构 SHALL 保持非有限帧间隔与负帧间隔的处理分支不变：非有限时不推进计时并将 `GaitBlendY` 置为目标值，为负时不推进计时且保持 `GaitBlendY` 不变，两者均输出节流后的诊断信息。
8. WHERE `FZZZAnimTuning` 指针为空且 `ZZZ_Locomotion_Events` 执行跨阈升级判定, THE 重构后行为 SHALL 允许与重构前不同：重构前不发生升级，重构后按默认阈值 `5.0` 秒参与判定。THE 该差异 SHALL 被记录为显式设计决策，理由是 `UZZZAnimInstance` 始终注入其成员配置对象的地址，该路径在正常运行中不可达，且新行为与 `AdvanceMovingGait` 其余部分「配置缺失时使用默认值」的容错原则一致。
9. THE 重构 SHALL NOT 改变除本需求第 8 条所述情形之外的任何行为分支。

### Requirement 9: 反射签名与蓝图兼容

**User Story:** 作为动画程序员，我想让 AnimBP 侧零改动，以便重构后不必重新绑定任何蓝图节点。

#### Acceptance Criteria

1. THE 重构 SHALL 保持 `UZZZAnimInstance` 全部 `UFUNCTION` 的 `Reflected_Signature` 不变，涵盖以下十个函数：`Locomotion_NotMoving_To_Conduit`、`Locomotion_Conduit_To_EnterMove`、`Locomotion_Conduit_To_Moving_Sprint`、`Locomotion_Moving_Walk_To_Run_ByHold`、`MarkLocomotionStateEntered`、`ConsumeSprintTrigger`、`Locomotion_OnEnter_Moving`、`Locomotion_OnEnter_MovingSubState`、`GetSeqByKey`、`GetBlendSpaceByKey`。
2. THE 四个判定类 `UFUNCTION` SHALL 保持 `BlueprintPure` 说明符、`BlueprintThreadSafe` 元数据、`Cond|Locomotion` 分类与 `const` 修饰不变。
3. THE 四个事件类 `UFUNCTION` SHALL 保持 `BlueprintCallable` 说明符、`Event|Locomotion` 分类不变，且 SHALL NOT 新增 `BlueprintThreadSafe` 元数据。
4. THE 两个查询类 `UFUNCTION` SHALL 保持 `BlueprintPure` 说明符、`BlueprintThreadSafe` 元数据、`Query|AnimSet` 分类与 `const` 修饰不变。
5. THE 重构 SHALL 保持 `UZZZAnimInstance` 全部 `UPROPERTY` 的 `Reflected_Signature` 不变，涵盖 `Out_WalkRunBlendSpace`、`AnimSet`、`Tuning`、`StateMemory` 四个属性。
6. THE 重构 SHALL 保持 `FZZZAnimStateMemory` 六个字段的名称、类型、默认值、`BlueprintReadOnly` 说明符与 `Locomotion` 分类不变，涵盖 `PreviousState`、`EnteredGait`、`bSprintTriggerPending`、`MovingGait`、`WalkHoldSeconds`、`GaitBlendY`。
7. THE 重构 SHALL 保持 `FZZZAnimTuning` 四个字段的名称、默认值、分类与 `meta` 钳制不变：`LoopBlendIn` 默认 `0.1`、`OneShotBlendOut` 默认 `0.15`、`WalkToRunHoldSeconds` 默认 `5.0` 且钳制 `[0.1, 60.0]`、`GaitBlendInterpSpeed` 默认 `6.0` 且钳制 `[0.1, 50.0]`。
8. THE 重构 SHALL 保持 `FZZZAnimSet` 两个字段 `Sequences` 与 `BlendSpaces` 的名称、`TMap` 键值类型、`EditAnywhere` 与 `BlueprintReadOnly` 说明符及 `Locomotion` 分类不变。
9. THE 重构 SHALL NOT 新增、删除或重命名任何 `UFUNCTION` 与 `UPROPERTY`。
10. THE 重构 SHALL 保持 `UZZZAnimInstance::PipelineDrive(float)` 的签名不变，并保持其与 `NativeUpdateAnimation` 之间通过管线驱动标记避免重复刷新的关系不变。
11. THE 重构 SHALL 保持 `UZZZAnimInstance` 继承自 `UAnimInstance` 且带 `GGYGO_API` 导出宏与 `UCLASS()` 说明符不变。

### Requirement 10: 资产、逻辑管线与外部调用点不受影响

**User Story:** 作为项目维护者，我想让重构的影响面严格限制在 ZZZ 动画层源码内，以便回滚时不牵连其他系统。

#### Acceptance Criteria

1. THE 重构 SHALL NOT 修改、移动、重命名或删除 `Content` 目录下的任何 `.uasset` 文件、AnimBP 或动画资源。
2. THE 重构 SHALL NOT 修改 `FIntentPipeline`、`FInputPipeline`、`FArbiterPipeline`、`FMotionDriver`、`FGYGOStateManager` 的任何源文件。
3. THE 重构 SHALL NOT 修改 `FRuntimeData` 与 `FAnimRuntimeData` 的字段定义、默认值或访问方式。
4. THE 重构 SHALL 保持 `FZZZAnimSnapshotCapture::Capture` 的数据来源映射不变，包括从 `AnimData` 读取的字段集合与从 `ABaseCharacter` 读取的字段集合。
5. THE 重构 SHALL 保持 `FZZZAnimSnapshot` 七个字段的名称、类型与默认值不变，涵盖 `Gait`、`bShouldMove`、`bSprintTrigger`、`CurrentState`、`VelocityLength`、`bGrounded`、`bBlockMove`。
6. THE `ABaseCharacter::Tick` SHALL 保持在逻辑管线全部完成之后调用 `UZZZAnimInstance::PipelineDrive(DeltaTime)` 的既有时序不变。
7. WHERE `ZZZAnimInstance.h` 保留在原路径, THE `BaseCharacter.cpp` SHALL NOT 需要任何修改；IF 实际需要调整, THEN 该修改 SHALL 限于 include 路径，不得改动调用语句或其所处位置。
8. THE 重构 SHALL NOT 修改 `AnimSyncMarkerTools.h` 与 `AnimSyncMarkerTools.cpp`。
9. IF `GGYGO.Build.cs` 中的 include 路径配置因新增子目录或旧目录删除而失效, THEN THE 重构 SHALL 更新该配置，且更新范围 SHALL 限于路径条目本身，不改动模块依赖列表。

### Requirement 11: 分阶段实施

**User Story:** 作为开发者，我想让重构分成两个可独立验证的阶段，以便本地编译报错时能快速定位问题归属。

#### Acceptance Criteria

1. THE 重构 SHALL 划分为 `Phase_One` 与 `Phase_Two` 两个阶段，且 `Phase_Two` 的全部改动 SHALL 在 `Phase_One` 完成之后开始。
2. THE `Phase_One` SHALL 只包含以下类型的改动：文件移动、文件拆分、include 路径修正、注释修正、日志类别统一、空目录删除。
3. THE `Phase_One` SHALL NOT 改动任何函数签名、任何控制流语句、任何数值常量或任何字段声明。
4. THE `Phase_Two` SHALL 包含引入 `Read_Context` 与 `Write_Context`、抽出 `ZZZ_Locomotion_Rules`、解除 `ZZZ_Locomotion_Events` 对 `ZZZ_Locomotion_Decisions` 的依赖这三项改动。
5. WHEN `Phase_One` 完成, THE `ZZZ_Animation_Layer` SHALL 处于逻辑与重构前完全相同的状态，使该阶段可独立通过本地编译验证。
6. THE 实施计划 SHALL 在 `Phase_One` 与 `Phase_Two` 之间设置一个供本地编译的检查点。

### Requirement 12: 静态验证与编译边界

**User Story:** 作为开发者，我想让重构任务只做静态检查、把编译留给我本地执行，以便我掌控编译时机。

#### Acceptance Criteria

1. THE 重构的验证流程 SHALL NOT 执行 Unreal 编译命令、Automation 测试命令或任何构建脚本，包括 `Build.bat`、`UnrealBuildTool`、`UnrealEditor-Cmd` 与 `RunUAT`。
2. THE 重构的验证流程 SHALL 以 `Static_Verification` 为唯一验证手段，包含文件存在性检查、目录内容检查、文本检索与签名逐项比对。
3. THE `Static_Verification` SHALL 检索 `CombatConfig.h`、`CombatDecisions/`、`CombatEvents/` 三个旧路径标识在源码中的引用，并要求结果数量为 `0`。
4. THE `Static_Verification` SHALL 按 Requirement 9 列举的十个 `UFUNCTION` 与四个 `UPROPERTY` 逐项比对 `Reflected_Signature`，任一项不一致时判定为失败。
5. THE `Static_Verification` SHALL 按 Requirement 9 第 6 至第 8 条逐项比对 `FZZZAnimStateMemory`、`FZZZAnimTuning`、`FZZZAnimSet` 的字段名、类型、默认值与 `meta` 钳制。
6. THE `Static_Verification` SHALL 检索 Requirement 5 第 9 条列举的七个数值常量，确认每个常量在 `ZZZ_Animation_Layer` 中的定义处数量为 `1` 且位于 `Locomotion/ZZZLocomotionRules.h`。
7. THE `Static_Verification` SHALL 检索 `ZZZLocomotionEvents.h` 与 `ZZZLocomotionEvents.cpp` 中对 `FZZZLocomotionDecisions` 的引用，并要求结果数量为 `0`。
8. THE `Static_Verification` SHALL 检索 `DEFINE_LOG_CATEGORY` 与 `DEFINE_LOG_CATEGORY_STATIC`，确认 `LogZZZAnim` 的定义处数量为 `1` 且位于 `ZZZAnimLog.cpp`。
9. THE `Static_Verification` SHALL 确认 `Content` 目录下无任何文件发生变更。
10. THE `Static_Verification` SHALL 确认每个含 `USTRUCT` 或 `UENUM` 的新头文件都包含对应的 `.generated.h` 且该 include 位于文件最后一条 include 位置。
11. IF `Unreal_Environment_Diagnostic` 在重构涉及的源文件中报告 `CoreMinimal.h`、`UFUNCTION`、`UPROPERTY` 或 `TMap` 未解析, THEN THE 验证流程 SHALL 将该报告归类为环境与工具链诊断，并记录分类归属、缺失的 include path 上下文名称与源文件名，不据此判定业务代码存在缺陷。
12. WHEN 全部 `Static_Verification` 项目通过, THE 验证结论 SHALL 标记为「静态检查通过，编译待本地验证」，SHALL NOT 标记为「通过」。
13. THE 重构 SHALL 在交付说明中提示本地编译前清理 `Intermediate/Build` 目录，因为旧 NTE 动画层删除后该目录仍残留陈旧的 UHT 生成产物与目标文件。
