# 需求文档：Intent Pipeline（意图管线）

## 简介

意图管线（Intent Pipeline）是 GGYGO 管线架构的第三阶段，负责将 InputPipeline 已处理好的 InputData 翻译为 RuntimeData 中的语义化意图和动画参数。该系统分为两个子阶段：IntentProcessors（读 InputData → 写 RuntimeData 意图）和 ParameterProcessors（读 RuntimeData 意图 → 写 RuntimeData 参数），严格遵循单向数据流和单一写入者原则。

## 术语表

- **IntentPipeline**: 意图管线主类，持有所有处理器实例，提供统一的执行入口
- **IIntentProcessor**: 意图处理器接口，定义读取 InputData 写入 RuntimeData 意图的统一协议
- **IParameterProcessor**: 参数处理器接口，定义读取 RuntimeData 意图写入 RuntimeData 动画参数的统一协议
- **ViewRotationProcessor**: 视角旋转处理器，将鼠标/摇杆增量转换为 ControlRotation
- **LocomotionIntentProcessor**: 移动意图处理器，将移动输入转换为世界空间移动方向
- **JumpIntentProcessor**: 跳跃意图处理器，将跳跃输入翻译为跳跃意图
- **AttackIntentProcessor**: 攻击意图处理器，将攻击输入翻译为攻击意图
- **DodgeIntentProcessor**: 闪避意图处理器，将闪避输入翻译为闪避意图
- **MovementParameterProcessor**: 移动参数处理器，将移动意图转换为动画混合参数
- **RootMotionParameterProcessor**: Root Motion 参数处理器，从骨骼网格体提取 Root Motion 数据
- **InputData**: 输入数据容器，由 InputPipeline 写入，IntentProcessors 只读
- **RuntimeData**: 运行时黑板，管线中所有系统的数据交换中心
- **InputPipeline**: 输入管线（阶段二已实现），唯一写入 InputData 的系统
- **BaseCharacter**: 所有角色的基类，管线时序分发中心
- **ControlRotation**: 控制器旋转，由 ViewRotationProcessor 写入，LocomotionIntentProcessor 读取
- **DesiredWorldMoveDir**: 世界空间移动方向向量，由 LocomotionIntentProcessor 写入
- **SmoothDamp**: 平滑阻尼插值，用于 AnimBlendX/Y 的平滑过渡
- **ConsumeRootMotion**: UE5 引擎方法，提取并清空当前帧的 Root Motion 数据

## 需求

### 需求 1：意图处理器接口定义

**用户故事：** 作为开发者，我希望有统一的意图处理器接口，以便所有意图处理器遵循相同的调用协议，实现可扩展的管线架构。

#### 验收标准

1. THE IIntentProcessor 接口 SHALL 定义纯虚函数 `Process(const FInputData& Input, FRuntimeData& Data)`，接受只读的 InputData 引用和可写的 RuntimeData 引用
2. THE IParameterProcessor 接口 SHALL 定义纯虚函数 `Process(FRuntimeData& Data, float DeltaTime)`，接受可写的 RuntimeData 引用和帧间隔参数
3. THE IIntentProcessor 接口 SHALL 提供虚析构函数，确保通过基类指针安全销毁派生类实例
4. THE IParameterProcessor 接口 SHALL 提供虚析构函数，确保通过基类指针安全销毁派生类实例

### 需求 2：视角旋转处理

**用户故事：** 作为玩家，我希望鼠标/摇杆输入能转换为视角旋转，以便控制角色的观察方向。

#### 验收标准

1. WHEN InputData.CurrentFrame.Look 包含非零视角增量时, THE ViewRotationProcessor SHALL 将增量应用到 Owner 的控制器旋转（通过 AddControllerYawInput 和 AddControllerPitchInput）
2. WHEN 视角增量应用完成后, THE ViewRotationProcessor SHALL 从 Owner->GetControlRotation() 读取最终旋转并写入 RuntimeData.ControlRotation
3. WHEN 视角增量应用完成后, THE ViewRotationProcessor SHALL 将 ControlRotation.Yaw 写入 RuntimeData.ViewYaw，将 ControlRotation.Pitch 写入 RuntimeData.ViewPitch
4. IF Owner 指针为空, THEN THE ViewRotationProcessor SHALL 跳过处理并安全返回，不产生任何副作用
5. THE ViewRotationProcessor SHALL 在 Init 阶段接收 ACharacter 指针注入，运行时不可变

### 需求 3：移动意图处理

**用户故事：** 作为玩家，我希望 WASD/摇杆输入能转换为世界空间的移动方向，以便角色朝摄像机相对方向移动。

#### 验收标准

1. WHEN InputData.CurrentFrame.Move 为非零向量时, THE LocomotionIntentProcessor SHALL 结合 RuntimeData.ControlRotation.Yaw 将输入从摄像机空间转换为世界空间方向，写入 RuntimeData.DesiredWorldMoveDir
2. WHEN InputData.CurrentFrame.Move 为非零向量时, THE LocomotionIntentProcessor SHALL 确保 RuntimeData.DesiredWorldMoveDir 是单位向量且 Z 分量为零
3. WHEN InputData.CurrentFrame.Move 接近零向量时, THE LocomotionIntentProcessor SHALL 将 RuntimeData.DesiredWorldMoveDir 设为零向量
4. THE LocomotionIntentProcessor SHALL 将 InputData.CurrentFrame.bSprintHeld 的值写入 RuntimeData.bWantsToSprint
5. THE LocomotionIntentProcessor SHALL 在 ViewRotationProcessor 之后执行，以确保读取到当前帧的 ControlRotation

### 需求 4：动作意图处理（跳跃、攻击、闪避）

**用户故事：** 作为玩家，我希望按下动作键后在缓冲窗口内意图被正确识别，以便操作手感流畅不丢输入。

#### 验收标准

1. WHEN InputData.CurrentFrame.IsJumpPressed() 返回 true 时, THE JumpIntentProcessor SHALL 将 RuntimeData.bWantsToJump 设为 true
2. WHEN InputData.CurrentFrame.IsJumpPressed() 返回 false 时, THE JumpIntentProcessor SHALL 保持 RuntimeData.bWantsToJump 不变
3. WHEN InputData.CurrentFrame.IsAttackPressed() 返回 true 时, THE AttackIntentProcessor SHALL 将 RuntimeData.bWantsToAttack 设为 true
4. WHEN InputData.CurrentFrame.IsAttackPressed() 返回 false 时, THE AttackIntentProcessor SHALL 保持 RuntimeData.bWantsToAttack 不变
5. WHEN InputData.CurrentFrame.IsDodgePressed() 返回 true 时, THE DodgeIntentProcessor SHALL 将 RuntimeData.bWantsToDodge 设为 true
6. WHEN InputData.CurrentFrame.IsDodgePressed() 返回 false 时, THE DodgeIntentProcessor SHALL 保持 RuntimeData.bWantsToDodge 不变

### 需求 5：移动参数计算

**用户故事：** 作为开发者，我希望移动意图能转换为平滑的动画混合参数，以便动画蓝图驱动 Blend Space 实现流畅的移动动画。

#### 验收标准

1. WHEN RuntimeData.DesiredWorldMoveDir 为非零向量时, THE MovementParameterProcessor SHALL 结合 RuntimeData.ControlRotation 计算角色本地空间的移动角度，写入 RuntimeData.MoveAngle
2. WHEN RuntimeData.DesiredWorldMoveDir 为零向量时, THE MovementParameterProcessor SHALL 将 RuntimeData.MoveAngle 设为 0
3. THE MovementParameterProcessor SHALL 确保 RuntimeData.MoveAngle 的值在 [-180, 180] 范围内
4. THE MovementParameterProcessor SHALL 使用 FInterpTo 平滑插值计算 RuntimeData.AnimBlendX 和 RuntimeData.AnimBlendY，避免动画突变
5. WHEN 无移动输入时, THE MovementParameterProcessor SHALL 使 AnimBlendX 和 AnimBlendY 平滑趋向零
6. WHEN 有移动输入时, THE MovementParameterProcessor SHALL 使 AnimBlendX 和 AnimBlendY 平滑趋向目标值（本地空间的左右和前后分量）

### 需求 6：Root Motion 数据提取

**用户故事：** 作为开发者，我希望每帧从骨骼网格体提取 Root Motion 数据，以便 MotionDriver 在后续阶段使用 Root Motion 驱动角色位移。

#### 验收标准

1. THE RootMotionParameterProcessor SHALL 每帧调用 Mesh->ConsumeRootMotion() 提取当前帧的 Root Motion 数据
2. WHEN ConsumeRootMotion() 返回有效的 Root Motion 数据时, THE RootMotionParameterProcessor SHALL 将位移转换为世界空间向量写入 RuntimeData.RootMotionDelta，并将 RuntimeData.bHasRootMotion 设为 true
3. WHEN ConsumeRootMotion() 返回无 Root Motion 数据时, THE RootMotionParameterProcessor SHALL 将 RuntimeData.RootMotionDelta 设为零向量，将 RuntimeData.bHasRootMotion 设为 false
4. IF Mesh 指针为空, THEN THE RootMotionParameterProcessor SHALL 将 RuntimeData.bHasRootMotion 设为 false，将 RuntimeData.RootMotionDelta 设为零向量，安全返回
5. THE RootMotionParameterProcessor SHALL 在 Init 阶段接收 USkeletalMeshComponent 指针注入，运行时不可变

### 需求 7：IntentPipeline 容器管理

**用户故事：** 作为开发者，我希望有一个统一的管线容器管理所有处理器的生命周期和执行顺序，以便 BaseCharacter 只需调用两个方法即可完成意图和参数处理。

#### 验收标准

1. WHEN Init 被调用时, THE IntentPipeline SHALL 创建 5 个意图处理器实例，按固定顺序为 ViewRotationProcessor、LocomotionIntentProcessor、JumpIntentProcessor、AttackIntentProcessor、DodgeIntentProcessor
2. WHEN Init 被调用时, THE IntentPipeline SHALL 创建 2 个参数处理器实例，按固定顺序为 MovementParameterProcessor、RootMotionParameterProcessor
3. WHEN Init 被调用时, THE IntentPipeline SHALL 将 ACharacter 指针注入 ViewRotationProcessor，将 USkeletalMeshComponent 指针注入 RootMotionParameterProcessor
4. WHEN ProcessIntents 被调用时, THE IntentPipeline SHALL 按注册顺序依次调用每个意图处理器的 Process 方法
5. WHEN ProcessParameters 被调用时, THE IntentPipeline SHALL 按注册顺序依次调用每个参数处理器的 Process 方法
6. THE IntentPipeline SHALL 使用 TUniquePtr 管理所有处理器实例的生命周期，不暴露运行时重排接口

### 需求 8：上游依赖 InputPipeline 数据契约

**用户故事：** 作为开发者，我希望意图管线明确依赖 InputPipeline 已处理的数据，以便保证意图处理器读取的是经过防抖缓冲和按键缓冲后的干净数据，而非硬件原始输入。

#### 验收标准

1. THE IntentPipeline SHALL 在 InputPipeline.Process() 之后执行（BaseCharacter::Tick 第 3、4 步），确保读取的 InputData 是当前帧已处理的数据
2. THE IntentPipeline 的所有 IntentProcessor SHALL 只读 InputData，不修改 InputData 的任何字段（InputPipeline 是唯一写入者）
3. THE ViewRotationProcessor SHALL 读取 InputData.CurrentFrame.Look（由 InputPipeline 处理后的视角增量），不直接读取 Enhanced Input 原始数据
4. THE LocomotionIntentProcessor SHALL 读取 InputData.CurrentFrame.Move（由 InputPipeline 防抖处理后的移动向量），不直接读取 Enhanced Input 原始数据
5. THE JumpIntentProcessor、AttackIntentProcessor、DodgeIntentProcessor SHALL 通过 InputData.CurrentFrame.IsXxxPressed() 查询缓冲窗口状态（由 InputPipeline 维护的 150ms 缓冲计时器），不自行实现缓冲逻辑

### 需求 9：管线执行时序与数据流约束

**用户故事：** 作为开发者，我希望管线严格遵循执行时序和数据流约束，以便保证数据一致性和系统正确性。

#### 验收标准

1. THE RuntimeData 的每个字段 SHALL 在一帧内只被一个处理器写入，遵循单一写入者原则
2. WHEN 帧末 ResetFrameIntents() 被调用时, THE RuntimeData SHALL 将 bWantsToJump、bWantsToAttack、bWantsToDodge、bWantsToSprint 全部清零
3. THE ViewRotationProcessor SHALL 在 LocomotionIntentProcessor 之前执行，因为后者依赖前者写入的 ControlRotation
4. THE MovementParameterProcessor SHALL 在所有 IntentProcessor 之后执行，因为它依赖 DesiredWorldMoveDir 和 ControlRotation

### 需求 10：BaseCharacter 集成

**用户故事：** 作为开发者，我希望 IntentPipeline 能无缝集成到 BaseCharacter 的 Tick 时序中，以便与已有的 InputPipeline 和未来的管线阶段协同工作。

#### 验收标准

1. THE BaseCharacter SHALL 在构造函数中创建 IntentPipeline 实例（TUniquePtr）
2. WHEN BeginPlay 被调用时, THE BaseCharacter SHALL 调用 IntentPipeline->Init(this, GetMesh()) 完成初始化
3. WHEN Tick 被调用时, THE BaseCharacter SHALL 在 InputPipeline->Process(DeltaTime) 之后调用 IntentPipeline->ProcessIntents(*InputData, *RuntimeData)
4. WHEN Tick 被调用时, THE BaseCharacter SHALL 在 ProcessIntents 之后调用 IntentPipeline->ProcessParameters(*RuntimeData, DeltaTime)
5. WHEN Tick 被调用时, THE BaseCharacter SHALL 在所有管线处理完成后调用 RuntimeData->ResetFrameIntents() 清零帧级意图

### 需求 11：错误处理与安全性

**用户故事：** 作为开发者，我希望所有处理器在异常情况下安全运行，以便系统不会因空指针或无效数据而崩溃。

#### 验收标准

1. WHEN 所有处理器接收零值或空输入时, THE IntentPipeline 的每个处理器 SHALL 安全处理而不产生崩溃或未定义行为
2. IF ViewRotationProcessor 的 Owner 指针为空, THEN THE ViewRotationProcessor SHALL 跳过处理，RuntimeData.ControlRotation 保持上一帧的值
3. IF RootMotionParameterProcessor 的 Mesh 指针为空, THEN THE RootMotionParameterProcessor SHALL 写入 bHasRootMotion = false 和 RootMotionDelta = 零向量
4. THE IntentPipeline 的所有处理器 SHALL 为纯 C++ 类，不暴露给蓝图，不可被外部修改
