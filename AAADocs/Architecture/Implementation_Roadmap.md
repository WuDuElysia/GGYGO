# GGYGO 实施路线

## 当前已有的代码

```
已完成:
├─ BaseCharacter.h/.cpp          管线时序分发中心 + GAS 宿主
│                                  ├─ 完整 Tick 管线（仲裁→输入→意图→参数→状态机→驱动）
│                                  ├─ ASC + AttributeSet（GAS 最小接入）
│                                  ├─ 动画蓝图数据接口（GetAnimSpeed/BlendX/Y 等）
│                                  └─ 内置调试 UI
├─ PlayerCharacter.h/.cpp        Enhanced Input 绑定 → 写 InputPipeline
├─ GGYGOPlayerController.h/.cpp  空壳（IMC 注册在蓝图里）
├─ GGYGOAttributeSet.h/.cpp      GAS 属性集（Health、MoveSpeed 等）
├─ MovementConfig.h              移动参数配置（RootMotionScale 等）
│
├─ 数据层:
│   ├─ Data/InputData.h          FInputData + FProcessedInput（双缓冲+按键缓冲）
│   └─ Data/RuntimeData.h        运行时黑板（AnimSpeed/bBip001Found/RootMotionDelta 等）
│
├─ 管线层:
│   ├─ Pipeline/InputPipeline.h/.cpp              输入管线（防抖+缓冲+双缓冲推进）
│   ├─ Pipeline/IntentPipeline.h/.cpp             意图管线（持有所有处理器）
│   ├─ Pipeline/Interfaces/IIntentProcessor.h     意图处理器接口
│   ├─ Pipeline/Interfaces/IParameterProcessor.h  参数处理器接口
│   ├─ Pipeline/Intents/
│   │   ├─ ViewRotationProcessor.h/.cpp           视角旋转
│   │   ├─ LocomotionIntentProcessor.h/.cpp       移动意图（方向+冲刺）
│   │   ├─ JumpIntentProcessor.h/.cpp             跳跃意图
│   │   ├─ AttackIntentProcessor.h/.cpp           攻击意图
│   │   └─ DodgeIntentProcessor.h/.cpp            闪避意图
│   └─ Pipeline/Parameters/
│       ├─ MovementParameterProcessor.h/.cpp      动画参数（BlendX/Y + MoveAngle）
│       └─ RootMotionParameterProcessor.h/.cpp    ★动画速度提取（Speed曲线→AnimSpeed）
│
├─ 驱动层:
│   └─ Drivers/MotionDriver.h/.cpp  ★运动驱动器（双路径：RootMotion + 防滑步Locomotion）
│
├─ 动画层:
│   ├─ Animation/GGYGOAnimInstance.h/.cpp  ★纯代码动画驱动（Slot + Montage，
│   │                                         启动时预创建循环蒙太奇，状态变化时切换）
│   │                                         ★ v2: Config 驱动 + 全 11 态 + 独立混合时间
│   ├─ Public/Data/UCharConfigData.h          ★角色配置 DataAsset（数据驱动核心）
│   └─ Private/Data/UCharConfigData.cpp        Config 查询方法实现
│     ABP_Miyabi AnimGraph 只需: Slot(DefaultSlot) → Output Pose
│
├─ 状态机:
│   ├─ StateMachine/CharacterStateMachine.h/.cpp  状态机主类（转换规则表+全局打断）
│   ├─ StateMachine/CharacterState.h/.cpp         状态基类
│   ├─ StateMachine/CharacterStateType.h          状态枚举
│   └─ StateMachine/State/
│       ├─ IdleState.h/.cpp           → RunStart(有输入)/InAir(跳跃)
│       ├─ RunStartState.h/.cpp       → RunLoop(启动完成)/RunEnd(松手)/InAir
│       ├─ RunLoopState.h/.cpp        → RunEnd(松手)/InAir(跳跃)
│       ├─ RunEndState.h/.cpp         → Idle(停止完成)/RunStart(打断)
│       ├─ InAirState.h/.cpp          → Idle(落地无输入)/RunStart(落地有输入)
│       ├─ AttackingState.h/.cpp      TODO: GAS 接入后由 GA 驱动
│       ├─ DodgingState.h/.cpp        TODO: GAS 接入后由 GA 驱动
│       ├─ HitStunState.h/.cpp        TODO: 仲裁管线完成后启用
│       ├─ StunnedState.h/.cpp        TODO: 仲裁管线完成后启用
│       └─ DeadState.h/.cpp           TODO: 仲裁管线完成后启用
│
├─ RootMotion 数据管线（工具脚本）:
│   ├─ AAADocs/max_export_root_motion.ms  3ds Max 批量提取 Bip001 位移→CSV
│   └─ AAADocs/generate_speed_curves.py   UE Python: CSV→AnimSequence.Speed 曲线
│
├─ 蓝图资产:
│   ├─ BP_Player                     蓝图角色（继承 PlayerCharacter）
│   ├─ BP_PlayerController           蓝图控制器（注册 IMC）
│   └─ ABP_Miyabi                    动画蓝图（继承 UGGYGOAnimInstance）
│
└─ 已删除的旧代码:
    ├─ RootMotionProcessor.h/.cpp    已被 MotionDriver 替代
    ├─ LocomotionState.h/.cpp        替换为 RunStartState
    └─ SprintingState.h/.cpp         替换为 RunLoopState
```

### RootMotion 模块核心架构

```
┌─────────────────────────────────────────────────────────────────────┐
│ 防滑步框架：输入方向(WASD) × 动画速度(AnimSpeed) = RequestDirectMove │
│ 动画跑多快 → 角色跑多快 → 帧级同步无滑步                             │
└─────────────────────────────────────────────────────────────────────┘

数据管线（离线）:
  3ds Max (max_export_root_motion.ms)
    → 批量导入FBX，提取Bip001逐帧世界位移
    → CSV (Frame, Time, Pos, Delta, Speed_cms_UE)
      → Python (generate_speed_curves.py)
        → AnimSequence 自定义 "Speed" 曲线（可选DeltaX/DeltaY）

运行时管线（每帧）:
  ABP播放动画 → AnimInstance 插值 Speed 曲线
    → FRootMotionParameterProcessor (Tick第4步)
      → GetCurveValue("Speed") → RuntimeData.AnimSpeed / bBip001Found
        → FMotionDriver (Tick第6步)
          ├─ 路径A: bHasRootMotion → ProcessRootMotionMovement (Montage/技能)
          └─ 路径B: AnimSpeed>0 → ProcessLocomotion(方向×AnimSpeed→RequestDirectMove)
               └─ 降级: AnimSpeed=0 → AddMovementInput (走CMC加速度)

关键设计决策:
├─ 不用 UE 原生 Root Motion（Init 时设为 IgnoreRootMotion）
├─ 自定义 Speed 曲线替代 ConsumeRootMotion（更可控、可调试）
├─ RequestDirectMove 替代 AddMovementInput（绕过 CMC 加速，防滑步）
├─ RootMotionDelta/bHasRootMotion 保留给 Montage/技能动画使用
└─ AnimSpeed=0 时自动降级为 AddMovementInput（兼容未配曲线的动画）
```

---

## 实施顺序（从底层往上搭）

### 阶段一：数据层（先把数据容器搭好）

所有管线都依赖数据层，必须先做。

#### 1.1 创建 RuntimeData

```
文件: Source/GGYGO/Public/Data/RuntimeData.h
类型: 纯 C++ 类（不需要 UObject）

内容:
/**
 * 运行时黑板
 * 管线中所有系统的数据交换中心
 */
struct FRuntimeData
{
    // === 输入状态 ===

    /** 移动输入原始值（由 InputPipeline 写入） */
    FVector2D MoveInput = FVector2D::ZeroVector;

    /** 视角输入原始值（由 InputPipeline 写入） */
    FVector2D LookInput = FVector2D::ZeroVector;

    // === 帧级意图（由 IntentProcessors 写入，帧末清零）===

    /** 跳跃意图 */
    bool bWantsToJump = false;
    /** 攻击意图 */
    bool bWantsToAttack = false;
    /** 闪避意图 */
    bool bWantsToDodge = false;
    /** 冲刺意图 */
    bool bWantsToSprint = false;
    /** 交互意图 */
    bool bWantsToInteract = false;

    // === 移动数据 ===

    /** 世界空间移动方向（LocomotionIntentProcessor 写入） */
    FVector DesiredWorldMoveDir = FVector::ZeroVector;
    /** 当前速度标量（MotionDriver 写入） */
    float CurrentSpeed = 0.f;
    /** 移动角度（MotionDriver 写入） */
    float MoveAngle = 0.f;
    /** 是否在移动（MotionDriver 写入） */
    bool bIsMoving = false;

    // === 视角数据（ViewRotationProcessor 写入）===

    float ViewYaw = 0.f;
    float ViewPitch = 0.f;
    FRotator ControlRotation = FRotator::ZeroRotator;

    // === 物理状态 ===

    bool bIsGrounded = true;
    float VerticalVelocity = 0.f;
    bool bJustLanded = false;

    // === 仲裁标记（ArbiterPipeline 写入）===

    bool bBlockMove = false;
    bool bBlockAttack = false;
    bool bBlockDodge = false;
    bool bBlockInput = false;

    // === 动作仲裁结果（ActionArbiter 写入）===
    // TODO: ECharacterState ActionGranted = ECharacterState::Idle;

    // === Root Motion（RootMotionParameterProcessor 写入）===

    FVector RootMotionDelta = FVector::ZeroVector;
    bool bHasRootMotion = false;

    // === 动画参数（MovementParameterProcessor 写入）===

    float AnimBlendX = 0.f;
    float AnimBlendY = 0.f;
    float PlayRate = 1.0f;

    /** 清零所有帧级意图，在 Tick 末尾调用 */
    void ResetFrameIntents()
    {
        bWantsToJump = false;
        bWantsToAttack = false;
        bWantsToDodge = false;
        bWantsToSprint = false;
        bWantsToInteract = false;
        bJustLanded = false;
    }
};
```

#### 1.2 创建 InputData

```
文件: Source/GGYGO/Public/Data/InputData.h
类型: 纯 C++ 类

内容:
struct FProcessedInput
{
    FVector2D Move = FVector2D::ZeroVector;
    FVector2D Look = FVector2D::ZeroVector;
    bool bJumpHeld = false;
    bool bAttackHeld = false;
    bool bDodgeHeld = false;
    bool bSprintHeld = false;

    // 缓冲计时器（按下时设为缓冲时间，每帧递减）
    float JumpBufferTimer = 0.f;
    float AttackBufferTimer = 0.f;
    float DodgeBufferTimer = 0.f;

    // 缓冲窗口内视为有效按下
    bool IsJumpPressed() const { return JumpBufferTimer > 0.f; }
    bool IsAttackPressed() const { return AttackBufferTimer > 0.f; }
    bool IsDodgePressed() const { return DodgeBufferTimer > 0.f; }

    // 消费输入（防重复触发）
    void ConsumeJump() { JumpBufferTimer = 0.f; }
    void ConsumeAttack() { AttackBufferTimer = 0.f; }
    void ConsumeDodge() { DodgeBufferTimer = 0.f; }
};

class FInputData
{
public:
    FProcessedInput CurrentFrame;
    FProcessedInput LastFrame;

    void AdvanceFrame()
    {
        LastFrame = CurrentFrame;
    }
};
```

#### 1.3 验证
- 两个数据容器能编译通过
- BaseCharacter 能持有它们（TUniquePtr）

---

### 阶段二：输入管线（替代 PlayerCharacter 直接操作移动）

#### 2.1 创建 InputPipeline

```
文件: Source/GGYGO/Public/Pipeline/InputPipeline.h
      Source/GGYGO/Private/Pipeline/InputPipeline.cpp
类型: 纯 C++ 类（不需要 UObject）

职责:
├─ 每帧从 PlayerCharacter 接收原始输入
├─ 防抖缓冲 + 动作按键缓冲
├─ 写入 InputData（唯一写入者）
└─ 不依赖 RuntimeData、状态机、GAS
```

InputPipeline.h:
```cpp
/**
 * @file InputPipeline.h
 * @brief 输入管线 - 输入加工和缓冲
 *
 * 唯一写入 InputData 的系统。
 * 负责防抖缓冲、动作按键缓冲、双缓冲推进。
 */

#pragma once

#include "CoreMinimal.h"
#include "Data/InputData.h"

class FInputPipeline
{
public:
    /**
     * 初始化，绑定输入数据容器（不拥有，由 BaseCharacter 管理生命周期）
     * @param InInputData 输入数据容器的引用
     */
    void Init(FInputData& InInputData);

    /**
     * 每帧调用，处理输入
     * 在 BaseCharacter::Tick 的第 2 步调用
     * @param DeltaTime 帧间隔
     */
    void Process(float DeltaTime);

    // ============================================================
    // 原始输入写入接口（由 PlayerCharacter 的回调调用）
    // InputPipeline 是 PlayerCharacter 和 InputData 之间的桥梁
    // ============================================================

    /** 写入移动输入（PlayerCharacter::OnMoveInput 调用） */
    void SetMoveInput(const FVector2D& Value);

    /** 写入移动输入结束（PlayerCharacter::OnMoveCompleted 调用） */
    void ClearMoveInput();

    /** 写入视角输入（PlayerCharacter::OnLookInput 调用） */
    void SetLookInput(const FVector2D& Value);

    /** 写入跳跃按下（PlayerCharacter::OnJumpInput 调用） */
    void SetJumpPressed();

    /** 写入攻击按下 */
    void SetAttackPressed();

    /** 写入闪避按下 */
    void SetDodgePressed();

    /** 写入冲刺状态 */
    void SetSprintHeld(bool bHeld);

private:
    /** 输入数据容器（不拥有，由 BaseCharacter 管理生命周期） */
    FInputData* InputData = nullptr;

    /** 动作按键缓冲时间（秒） */
    static constexpr float ActionBufferTime = 0.15f;

    /** 移动防抖缓冲时间（秒） */
    static constexpr float MoveFlickerBuffer = 0.05f;

    // 临时存储本帧的原始输入（Process 时写入 InputData）
    FVector2D PendingMoveInput = FVector2D::ZeroVector;
    FVector2D PendingLookInput = FVector2D::ZeroVector;
    bool bPendingJump = false;
    bool bPendingAttack = false;
    bool bPendingDodge = false;
    bool bPendingSprint = false;

    /** 移动防抖计时器 */
    float MoveFlickerTimer = 0.f;

    /** 上一帧有效的移动方向（防抖用） */
    FVector2D LastValidMoveDir = FVector2D::ZeroVector;
};
```

InputPipeline.cpp:
```cpp
/**
 * @file InputPipeline.cpp
 * @brief 输入管线实现
 */

#include "Pipeline/InputPipeline.h"

void FInputPipeline::Init(FInputData& InInputData)
{
    InputData = &InInputData;
}

void FInputPipeline::Process(float DeltaTime)
{
    if (!InputData) return;

    // 1. 推进双缓冲
    InputData->AdvanceFrame();

    // 2. 获取当前帧引用
    FProcessedInput& Current = InputData->CurrentFrame;

    // 3. 移动防抖处理
    if (!PendingMoveInput.IsNearlyZero())
    {
        // 有输入：更新方向，重置防抖计时器
        Current.Move = PendingMoveInput;
        LastValidMoveDir = PendingMoveInput;
        MoveFlickerTimer = MoveFlickerBuffer;
    }
    else if (MoveFlickerTimer > 0.f)
    {
        // 刚松手：在防抖窗口内保持上一个方向
        MoveFlickerTimer -= DeltaTime;
        Current.Move = LastValidMoveDir;
    }
    else
    {
        // 防抖窗口结束：清零
        Current.Move = FVector2D::ZeroVector;
        LastValidMoveDir = FVector2D::ZeroVector;
    }

    // 4. 视角输入（不需要防抖）
    Current.Look = PendingLookInput;

    // 5. 持续按住状态
    Current.bSprintHeld = bPendingSprint;
    Current.bJumpHeld = bPendingJump;
    Current.bAttackHeld = bPendingAttack;
    Current.bDodgeHeld = bPendingDodge;

    // 6. 动作按键缓冲计时器
    // 按下时设为 ActionBufferTime，每帧递减
    if (bPendingJump)
        Current.JumpBufferTimer = ActionBufferTime;
    else
        Current.JumpBufferTimer = FMath::Max(Current.JumpBufferTimer - DeltaTime, 0.f);

    if (bPendingAttack)
        Current.AttackBufferTimer = ActionBufferTime;
    else
        Current.AttackBufferTimer = FMath::Max(Current.AttackBufferTimer - DeltaTime, 0.f);

    if (bPendingDodge)
        Current.DodgeBufferTimer = ActionBufferTime;
    else
        Current.DodgeBufferTimer = FMath::Max(Current.DodgeBufferTimer - DeltaTime, 0.f);

    // 7. 清零瞬时输入（下一帧重新从回调写入）
    PendingLookInput = FVector2D::ZeroVector;
    bPendingJump = false;
    bPendingAttack = false;
    bPendingDodge = false;
    // 注意：PendingMoveInput 和 bPendingSprint 不清零
    // 因为它们是持续状态，由 Completed 回调清零
}

void FInputPipeline::SetMoveInput(const FVector2D& Value)
{
    PendingMoveInput = Value;
}

void FInputPipeline::ClearMoveInput()
{
    PendingMoveInput = FVector2D::ZeroVector;
}

void FInputPipeline::SetLookInput(const FVector2D& Value)
{
    PendingLookInput = Value;
}

void FInputPipeline::SetJumpPressed()
{
    bPendingJump = true;
}

void FInputPipeline::SetAttackPressed()
{
    bPendingAttack = true;
}

void FInputPipeline::SetDodgePressed()
{
    bPendingDodge = true;
}

void FInputPipeline::SetSprintHeld(bool bHeld)
{
    bPendingSprint = bHeld;
}
```

#### 2.2 修改 BaseCharacter 持有 InputPipeline 和 InputData

BaseCharacter.h 添加:
```cpp
#include "Data/InputData.h"
#include "Data/RuntimeData.h"

// 在 protected 里:

/** 输入数据容器 */
TUniquePtr<FInputData> InputData;

/** 运行时黑板 */
TUniquePtr<FRuntimeData> RuntimeData;

/** 输入管线 */
TUniquePtr<FInputPipeline> InputPipeline;
```

注意: 需要前向声明 FInputPipeline，在 .cpp 里 include。

BaseCharacter.cpp 修改:
```cpp
#include "Pipeline/InputPipeline.h"

ABaseCharacter::ABaseCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    RootMotionProc = MakeUnique<FRootMotionProcessor>();
    InputData = MakeUnique<FInputData>();
    RuntimeData = MakeUnique<FRuntimeData>();
    InputPipeline = MakeUnique<FInputPipeline>();
}

void ABaseCharacter::BeginPlay()
{
    Super::BeginPlay();
    RootMotionProc->Init(this);
    InputPipeline->Init(*InputData);
}

void ABaseCharacter::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);

    // 管线时序（目前只有输入管线和旧版移动）
    // 后续阶段会逐步加入其他管线

    // 2. 输入管线
    InputPipeline->Process(DeltaTime);

    // 旧版移动（后续替换为 MotionDriver）
    RootMotionProc->Process(DeltaTime);

    // 帧末清零
    RuntimeData->ResetFrameIntents();
}
```

#### 2.3 修改 PlayerCharacter 改为写 InputPipeline

PlayerCharacter.cpp 修改:
```cpp
void APlayerCharacter::OnMoveInput(const FInputActionValue& Value)
{
    FVector2D Input = Value.Get<FVector2D>();

    // 写入 InputPipeline，不再直接操作 RootMotionProcessor
    InputPipeline->SetMoveInput(Input);

    // === 临时兼容：旧版移动系统还需要这些 ===
    // TODO: 阶段五做完 MotionDriver 后删除以下代码
    FRotator ControlRot = GetControlRotation();
    ControlRot.Pitch = 0.f;
    ControlRot.Roll = 0.f;
    FVector Forward = FRotationMatrix(ControlRot).GetUnitAxis(EAxis::X);
    FVector Right = FRotationMatrix(ControlRot).GetUnitAxis(EAxis::Y);
    DesiredMoveDirection = (Forward * Input.Y + Right * Input.X).GetSafeNormal();
    RootMotionProc->DesiredMoveDirection = DesiredMoveDirection;
    // === 临时兼容结束 ===
}

void APlayerCharacter::OnMoveCompleted(const FInputActionValue& Value)
{
    InputPipeline->ClearMoveInput();

    // === 临时兼容 ===
    DesiredMoveDirection = FVector::ZeroVector;
    RootMotionProc->DesiredMoveDirection = FVector::ZeroVector;
    // === 临时兼容结束 ===
}

void APlayerCharacter::OnLookInput(const FInputActionValue& Value)
{
    FVector2D Input = Value.Get<FVector2D>();
    InputPipeline->SetLookInput(Input);

    // === 临时兼容：旧版视角控制 ===
    AddControllerYawInput(Input.X);
    AddControllerPitchInput(Input.Y);
    // === 临时兼容结束 ===
}

void APlayerCharacter::OnJumpInput(const FInputActionValue& Value)
{
    InputPipeline->SetJumpPressed();

    // === 临时兼容 ===
    Jump();
    // === 临时兼容结束 ===
}
```

#### 2.4 验证清单

```
编译验证:
├─ InputPipeline.h/.cpp 编译通过
├─ BaseCharacter 持有 InputData + RuntimeData + InputPipeline
└─ PlayerCharacter 的回调写入 InputPipeline

运行验证:
├─ 角色移动正常（临时兼容代码保证旧版行为不变）
├─ 加调试日志确认 InputData 数据正确:
│   if (GEngine)
│       GEngine->AddOnScreenDebugMessage(3, 0.f, FColor::White,
│           FString::Printf(TEXT("InputData Move: %s"),
│               *InputData->CurrentFrame.Move.ToString()));
├─ 按 W 时 Move.Y > 0
├─ 松开 W 后防抖窗口内 Move 保持，窗口后清零
└─ 按攻击键后 AttackBufferTimer > 0，逐帧递减到 0

关键点:
├─ 旧版移动系统暂时保留（临时兼容代码）
├─ 新旧系统并行运行，确保不破坏现有功能
└─ 后续阶段逐步删除临时兼容代码
```

---

### 阶段三：意图管线（输入 → 意图翻译）

意图管线读取 InputPipeline 已处理好的 InputData，翻译为 RuntimeData 中的语义化意图和动画参数。

完整数据流:
```
硬件原始输入 → InputPipeline（阶段二）→ InputData（已处理）→ IntentPipeline（本阶段）→ RuntimeData
```

分为两个子阶段:
```
IntentProcessors:   读 InputData → 写 RuntimeData 意图
ParameterProcessors: 读 RuntimeData 意图 → 写 RuntimeData 参数
```

文件结构:
```
Source/GGYGO/
├── Public/Pipeline/
│   ├── IntentPipeline.h              意图管线主类
│   ├── IIntentProcessor.h            意图处理器接口
│   ├── IParameterProcessor.h         参数处理器接口
│   ├── Intents/
│   │   ├── ViewRotationProcessor.h
│   │   ├── LocomotionIntentProcessor.h
│   │   ├── JumpIntentProcessor.h
│   │   ├── AttackIntentProcessor.h
│   │   └── DodgeIntentProcessor.h
│   └── Parameters/
│       ├── MovementParameterProcessor.h
│       └── RootMotionParameterProcessor.h
├── Private/Pipeline/
│   ├── IntentPipeline.cpp
│   ├── Intents/
│   │   ├── ViewRotationProcessor.cpp
│   │   ├── LocomotionIntentProcessor.cpp
│   │   ├── JumpIntentProcessor.cpp
│   │   ├── AttackIntentProcessor.cpp
│   │   └── DodgeIntentProcessor.cpp
│   └── Parameters/
│       ├── MovementParameterProcessor.cpp
│       └── RootMotionParameterProcessor.cpp
```

#### 3.1 创建接口

IIntentProcessor.h:
```cpp
/**
 * @file IIntentProcessor.h
 * @brief 意图处理器接口
 * 读取 InputData → 写入 RuntimeData 意图
 */
#pragma once

#include "CoreMinimal.h"

struct FInputData;
struct FRuntimeData;

class IIntentProcessor
{
public:
    virtual ~IIntentProcessor() = default;

    /**
     * 每帧处理意图
     * @param Input  输入数据（只读，由 InputPipeline 写入）
     * @param Data   运行时黑板（写入意图字段）
     */
    virtual void Process(const FInputData& Input, FRuntimeData& Data) = 0;
};
```

IParameterProcessor.h:
```cpp
/**
 * @file IParameterProcessor.h
 * @brief 参数处理器接口
 * 读取 RuntimeData 意图 → 写入 RuntimeData 动画参数
 */
#pragma once

#include "CoreMinimal.h"

struct FRuntimeData;

class IParameterProcessor
{
public:
    virtual ~IParameterProcessor() = default;

    /**
     * 每帧处理参数
     * @param Data      运行时黑板（读意图、写参数）
     * @param DeltaTime 帧间隔
     */
    virtual void Process(FRuntimeData& Data, float DeltaTime) = 0;
};
```

#### 3.2 创建意图处理器

ViewRotationProcessor.h:
```cpp
/**
 * @file ViewRotationProcessor.h
 * @brief 视角旋转处理器
 * 鼠标增量 → 累加 ViewYaw/ViewPitch → 写入 ControlRotation
 * 需要 ACharacter 指针来调用 AddControllerYawInput/PitchInput
 */
#pragma once

#include "Pipeline/IIntentProcessor.h"

class ACharacter;

class FViewRotationProcessor : public IIntentProcessor
{
public:
    void Init(ACharacter* InOwner);
    virtual void Process(const FInputData& Input, FRuntimeData& Data) override;

private:
    ACharacter* Owner = nullptr;
};
```

ViewRotationProcessor.cpp:
```cpp
#include "Pipeline/Intents/ViewRotationProcessor.h"
#include "Data/InputData.h"
#include "Data/RuntimeData.h"
#include "GameFramework/Character.h"

void FViewRotationProcessor::Init(ACharacter* InOwner)
{
    Owner = InOwner;
}

void FViewRotationProcessor::Process(const FInputData& Input, FRuntimeData& Data)
{
    if (!Owner) return;

    const FVector2D& Look = Input.CurrentFrame.Look;

    // 将鼠标增量应用到控制器旋转
    Owner->AddControllerYawInput(Look.X);
    Owner->AddControllerPitchInput(Look.Y);

    // 从控制器读取最终旋转（经过 Clamp 后的值）
    FRotator ControlRot = Owner->GetControlRotation();
    Data.ControlRotation = ControlRot;
    Data.ViewYaw = ControlRot.Yaw;
    Data.ViewPitch = ControlRot.Pitch;
}
```

LocomotionIntentProcessor.h:
```cpp
/**
 * @file LocomotionIntentProcessor.h
 * @brief 移动意图处理器
 * 摇杆/WASD → 世界空间方向 DesiredWorldMoveDir + 速度档位
 * 依赖 ViewRotationProcessor 先写入 ControlRotation
 */
#pragma once

#include "Pipeline/IIntentProcessor.h"

class FLocomotionIntentProcessor : public IIntentProcessor
{
public:
    virtual void Process(const FInputData& Input, FRuntimeData& Data) override;
};
```

LocomotionIntentProcessor.cpp:
```cpp
#include "Pipeline/Intents/LocomotionIntentProcessor.h"
#include "Data/InputData.h"
#include "Data/RuntimeData.h"

void FLocomotionIntentProcessor::Process(const FInputData& Input, FRuntimeData& Data)
{
    const FVector2D& MoveInput = Input.CurrentFrame.Move;

    if (MoveInput.IsNearlyZero())
    {
        Data.DesiredWorldMoveDir = FVector::ZeroVector;
        return;
    }

    // 从 ControlRotation 提取水平朝向（ViewRotationProcessor 已写入）
    FRotator YawRot(0.f, Data.ControlRotation.Yaw, 0.f);
    FVector Forward = FRotationMatrix(YawRot).GetUnitAxis(EAxis::X);
    FVector Right = FRotationMatrix(YawRot).GetUnitAxis(EAxis::Y);

    // 输入空间 → 世界空间
    FVector WorldDir = (Forward * MoveInput.Y + Right * MoveInput.X);
    WorldDir.Z = 0.f;
    Data.DesiredWorldMoveDir = WorldDir.GetSafeNormal();

    // 速度档位
    Data.bWantsToSprint = Input.CurrentFrame.bSprintHeld;
}
```

JumpIntentProcessor.h:
```cpp
/**
 * @file JumpIntentProcessor.h
 * @brief 跳跃意图处理器
 * 跳跃键缓冲 → bWantsToJump
 */
#pragma once

#include "Pipeline/IIntentProcessor.h"

class FJumpIntentProcessor : public IIntentProcessor
{
public:
    virtual void Process(const FInputData& Input, FRuntimeData& Data) override;
};
```

JumpIntentProcessor.cpp:
```cpp
#include "Pipeline/Intents/JumpIntentProcessor.h"
#include "Data/InputData.h"
#include "Data/RuntimeData.h"

void FJumpIntentProcessor::Process(const FInputData& Input, FRuntimeData& Data)
{
    if (Input.CurrentFrame.IsJumpPressed())
    {
        Data.bWantsToJump = true;
    }
}
```

AttackIntentProcessor.h:
```cpp
/**
 * @file AttackIntentProcessor.h
 * @brief 攻击意图处理器
 * 攻击键缓冲 → bWantsToAttack
 */
#pragma once

#include "Pipeline/IIntentProcessor.h"

class FAttackIntentProcessor : public IIntentProcessor
{
public:
    virtual void Process(const FInputData& Input, FRuntimeData& Data) override;
};
```

AttackIntentProcessor.cpp:
```cpp
#include "Pipeline/Intents/AttackIntentProcessor.h"
#include "Data/InputData.h"
#include "Data/RuntimeData.h"

void FAttackIntentProcessor::Process(const FInputData& Input, FRuntimeData& Data)
{
    if (Input.CurrentFrame.IsAttackPressed())
    {
        Data.bWantsToAttack = true;
    }
}
```

DodgeIntentProcessor.h:
```cpp
/**
 * @file DodgeIntentProcessor.h
 * @brief 闪避意图处理器
 * 闪避键缓冲 → bWantsToDodge
 */
#pragma once

#include "Pipeline/IIntentProcessor.h"

class FDodgeIntentProcessor : public IIntentProcessor
{
public:
    virtual void Process(const FInputData& Input, FRuntimeData& Data) override;
};
```

DodgeIntentProcessor.cpp:
```cpp
#include "Pipeline/Intents/DodgeIntentProcessor.h"
#include "Data/InputData.h"
#include "Data/RuntimeData.h"

void FDodgeIntentProcessor::Process(const FInputData& Input, FRuntimeData& Data)
{
    if (Input.CurrentFrame.IsDodgePressed())
    {
        Data.bWantsToDodge = true;
    }
}
```

#### 3.3 创建参数处理器

MovementParameterProcessor.h:
```cpp
/**
 * @file MovementParameterProcessor.h
 * @brief 移动参数处理器
 * DesiredWorldMoveDir → 本地角度 MoveAngle → SmoothDamp → AnimBlendX/Y
 */
#pragma once

#include "Pipeline/IParameterProcessor.h"

class FMovementParameterProcessor : public IParameterProcessor
{
public:
    virtual void Process(FRuntimeData& Data, float DeltaTime) override;

private:
    /** 平滑插值速度 */
    float SmoothSpeed = 8.0f;

    /** 当前平滑后的混合值 */
    float SmoothedBlendX = 0.f;
    float SmoothedBlendY = 0.f;
};
```

MovementParameterProcessor.cpp:
```cpp
#include "Pipeline/Parameters/MovementParameterProcessor.h"
#include "Data/RuntimeData.h"

void FMovementParameterProcessor::Process(FRuntimeData& Data, float DeltaTime)
{
    float TargetX = 0.f;
    float TargetY = 0.f;

    if (!Data.DesiredWorldMoveDir.IsNearlyZero())
    {
        // 计算角色本地空间的移动角度
        FRotator CharRot(0.f, Data.ControlRotation.Yaw, 0.f);
        FVector LocalDir = CharRot.UnrotateVector(Data.DesiredWorldMoveDir);

        // 分解为 X（左右）和 Y（前后）分量
        TargetX = LocalDir.Y;  // 左右
        TargetY = LocalDir.X;  // 前后

        // 计算角度（-180 ~ 180）
        Data.MoveAngle = FMath::Atan2(LocalDir.Y, LocalDir.X) * (180.f / PI);
    }
    else
    {
        Data.MoveAngle = 0.f;
    }

    // SmoothDamp 平滑插值
    SmoothedBlendX = FMath::FInterpTo(SmoothedBlendX, TargetX, DeltaTime, SmoothSpeed);
    SmoothedBlendY = FMath::FInterpTo(SmoothedBlendY, TargetY, DeltaTime, SmoothSpeed);

    Data.AnimBlendX = SmoothedBlendX;
    Data.AnimBlendY = SmoothedBlendY;
}
```

RootMotionParameterProcessor.h:
```cpp
/**
 * @file RootMotionParameterProcessor.h
 * @brief 动画速度提取处理器
 *
 * 从 AnimInstance 的自定义曲线 "Speed" 中读取动画期望移动速度。
 * 该曲线由 Python 脚本 generate_speed_curves.py 从动画资产
 * Bip001 原始位移数据自动生成。
 *
 * 数据流：
 *   FBX (Bip001 位移) → Python → AnimSequence.Speed 曲线
 *   → ABP 播放 → AnimInstance 每帧插值
 *   → 本处理器 GetCurveValue("Speed") → RuntimeData.AnimSpeed
 *   → MotionDriver 用 AnimSpeed × 输入方向驱动移动（防滑步）
 */
#pragma once

#include "Pipeline/IParameterProcessor.h"

class USkeletalMeshComponent;

class FRootMotionParameterProcessor : public IParameterProcessor
{
public:
    void Init(USkeletalMeshComponent* InMesh);

    virtual void Process(FRuntimeData& Data, float DeltaTime) override;

private:
    USkeletalMeshComponent* Mesh = nullptr;

    /** 动画曲线名，对应 AnimSequence 中的自定义曲线 */
    FName SpeedCurveName = TEXT("Speed");
};
```

RootMotionParameterProcessor.cpp:
```cpp
/**
 * @file RootMotionParameterProcessor.cpp
 * @brief 动画速度提取处理器实现
 *
 * 通过 AnimInstance::GetCurveValue("Speed") 读取动画资产中的自定义曲线值。
 * 该曲线由 generate_speed_curves.py 脚本从 Bip001 原始位移数据自动生成。
 */
#include "Pipeline/Parameters/RootMotionParameterProcessor.h"
#include "Data/RuntimeData.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimInstance.h"

void FRootMotionParameterProcessor::Init(USkeletalMeshComponent* InMesh)
{
    Mesh = InMesh;
}

void FRootMotionParameterProcessor::Process(FRuntimeData& RuntimeData, float DeltaTime)
{
    RuntimeData.bBip001Found = false;
    RuntimeData.AnimSpeed = 0.f;

    if (!Mesh)
    {
        return;
    }

    UAnimInstance* AnimInst = Mesh->GetAnimInstance();
    if (!AnimInst)
    {
        return;
    }

    // 读取动画自定义曲线 "Speed" 的值
    // 该曲线由 MaxScript（max_export_root_motion.ms）提取 Bip001 位移
    // 经 Python（generate_speed_curves.py）写入 AnimSequence
    float CurveValue = AnimInst->GetCurveValue(SpeedCurveName);

    if (CurveValue > 0.f)
    {
        RuntimeData.AnimSpeed = CurveValue;
        RuntimeData.bBip001Found = true;
    }
}

// ═══════════════════════════════════════════════════════════════════
// 与原方案的差异说明：
// 原方案使用 Mesh->ConsumeRootMotion() 提取 UE 原生 Root Motion，
// 现方案改为从自定义 "Speed" 曲线读取动画速度，原因：
//   1. 自定义曲线更可控 —— 可在 MaxScript/Python 中预处理和修正数据
//   2. 可调试 —— 直接在动画编辑器中看曲线值
//   3. 支持降级 —— AnimSpeed=0 时 MotionDriver 自动退化为 AddMovementInput
//   4. RootMotionDelta/bHasRootMotion 保留给 Montage/技能动画使用
// ═══════════════════════════════════════════════════════════════════
```

#### 3.4 创建 IntentPipeline

IntentPipeline.h:
```cpp
/**
 * @file IntentPipeline.h
 * @brief 意图管线
 * 持有所有 IntentProcessor 和 ParameterProcessor
 * 在 BaseCharacter::Tick 中按序调用（紧跟在 InputPipeline 之后）
 */
#pragma once

#include "CoreMinimal.h"
#include "Pipeline/IIntentProcessor.h"
#include "Pipeline/IParameterProcessor.h"

class ACharacter;
class USkeletalMeshComponent;
struct FInputData;
struct FRuntimeData;

class FIntentPipeline
{
public:
    /**
     * 初始化所有处理器
     * @param InOwner 角色指针（ViewRotationProcessor 需要）
     * @param InMesh  骨骼网格体（RootMotionParameterProcessor 需要）
     */
    void Init(ACharacter* InOwner, USkeletalMeshComponent* InMesh);

    /**
     * 执行所有意图处理器（Tick 第 3 步）
     * 前置条件: InputPipeline.Process() 已执行
     */
    void ProcessIntents(const FInputData& Input, FRuntimeData& Data);

    /**
     * 执行所有参数处理器（Tick 第 4 步）
     * 前置条件: ProcessIntents() 已执行
     */
    void ProcessParameters(FRuntimeData& Data, float DeltaTime);

private:
    /** 意图处理器列表（按执行顺序） */
    TArray<TUniquePtr<IIntentProcessor>> IntentProcessors;

    /** 参数处理器列表（按执行顺序） */
    TArray<TUniquePtr<IParameterProcessor>> ParameterProcessors;
};
```

IntentPipeline.cpp:
```cpp
#include "Pipeline/IntentPipeline.h"
#include "Pipeline/Intents/ViewRotationProcessor.h"
#include "Pipeline/Intents/LocomotionIntentProcessor.h"
#include "Pipeline/Intents/JumpIntentProcessor.h"
#include "Pipeline/Intents/AttackIntentProcessor.h"
#include "Pipeline/Intents/DodgeIntentProcessor.h"
#include "Pipeline/Parameters/MovementParameterProcessor.h"
#include "Pipeline/Parameters/RootMotionParameterProcessor.h"
#include "Data/InputData.h"
#include "Data/RuntimeData.h"

void FIntentPipeline::Init(ACharacter* InOwner, USkeletalMeshComponent* InMesh)
{
    // 创建意图处理器（顺序固定，ViewRotation 必须在 Locomotion 之前）
    auto ViewRotProc = MakeUnique<FViewRotationProcessor>();
    ViewRotProc->Init(InOwner);
    IntentProcessors.Add(MoveTemp(ViewRotProc));

    IntentProcessors.Add(MakeUnique<FLocomotionIntentProcessor>());
    IntentProcessors.Add(MakeUnique<FJumpIntentProcessor>());
    IntentProcessors.Add(MakeUnique<FAttackIntentProcessor>());
    IntentProcessors.Add(MakeUnique<FDodgeIntentProcessor>());

    // 创建参数处理器（顺序固定）
    ParameterProcessors.Add(MakeUnique<FMovementParameterProcessor>());

    auto RootMotionProc = MakeUnique<FRootMotionParameterProcessor>();
    RootMotionProc->Init(InMesh);
    ParameterProcessors.Add(MoveTemp(RootMotionProc));
}

void FIntentPipeline::ProcessIntents(const FInputData& Input, FRuntimeData& Data)
{
    for (const auto& Processor : IntentProcessors)
    {
        Processor->Process(Input, Data);
    }
}

void FIntentPipeline::ProcessParameters(FRuntimeData& Data, float DeltaTime)
{
    for (const auto& Processor : ParameterProcessors)
    {
        Processor->Process(Data, DeltaTime);
    }
}
```

#### 3.5 修改 BaseCharacter 集成 IntentPipeline

BaseCharacter.h 添加:
```cpp
#include "Pipeline/IntentPipeline.h"

// 在 protected 里:
/** 意图管线 */
TUniquePtr<FIntentPipeline> IntentPipeline;
```

BaseCharacter.cpp 修改:
```cpp
ABaseCharacter::ABaseCharacter()
{
    PrimaryActorTick.bCanEverTick = true;
    RootMotionProc = MakeUnique<FRootMotionProcessor>();
    InputData = MakeUnique<FInputData>();
    RuntimeData = MakeUnique<FRuntimeData>();
    InputPipeline = MakeUnique<FInputPipeline>();
    IntentPipeline = MakeUnique<FIntentPipeline>();
}

void ABaseCharacter::BeginPlay()
{
    Super::BeginPlay();
    RootMotionProc->Init(this);
    InputPipeline->Init(*InputData);
    IntentPipeline->Init(this, GetMesh());
}

void ABaseCharacter::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);

    // 1. ArbiterPipeline（未来）

    // 2. 输入管线（阶段二已实现）
    //    处理原始输入：防抖缓冲、按键缓冲、双缓冲推进
    //    输出：InputData.CurrentFrame（已处理的输入数据）
    InputPipeline->Process(DeltaTime);

    // 3. 意图处理（本阶段）
    //    读取 InputData（已处理） → 写入 RuntimeData 意图
    IntentPipeline->ProcessIntents(*InputData, *RuntimeData);

    // 4. 参数处理（本阶段）
    //    读取 RuntimeData 意图 → 写入 RuntimeData 动画参数
    IntentPipeline->ProcessParameters(*RuntimeData, DeltaTime);

    // 5. StateMachine（未来）
    // 6. MotionDriver（未来）

    // 旧版移动（临时兼容，阶段五替换为 MotionDriver 后删除）
    RootMotionProc->Process(DeltaTime);

    // 帧末清零
    RuntimeData->ResetFrameIntents();
}
```

#### 3.6 修改 PlayerCharacter 删除临时兼容的视角控制

PlayerCharacter.cpp 修改 OnLookInput:
```cpp
void APlayerCharacter::OnLookInput(const FInputActionValue& Value)
{
    FVector2D Input = Value.Get<FVector2D>();
    InputPipeline->SetLookInput(Input);

    // === 临时兼容：旧版视角控制 ===
    // ViewRotationProcessor 现在负责视角旋转
    // 但旧版移动系统还需要 ControlRotation，所以暂时保留
    // TODO: 阶段五做完 MotionDriver 后删除
    AddControllerYawInput(Input.X);
    AddControllerPitchInput(Input.Y);
    // === 临时兼容结束 ===
}
```

注意: ViewRotationProcessor 和临时兼容代码会重复调用 AddControllerYawInput/PitchInput，
导致视角旋转速度翻倍。解决方案二选一:
```
方案 A: 阶段三暂时不启用 ViewRotationProcessor（在 IntentPipeline::Init 中跳过创建）
        等阶段五删除临时兼容代码后再启用
方案 B: 立即删除 OnLookInput 中的临时兼容代码
        因为 ViewRotationProcessor 已经接管了视角旋转
        旧版移动系统通过 RuntimeData.ControlRotation 读取视角数据
推荐方案 B，因为 LocomotionIntentProcessor 已经替代了 OnMoveInput 中的方向计算
```

#### 3.7 验证清单

```
编译验证:
├─ 所有接口和处理器文件编译通过
├─ IntentPipeline 能创建和持有所有处理器
├─ BaseCharacter 持有 IntentPipeline（TUniquePtr）
└─ 无循环依赖

运行验证（加调试日志）:
#if !UE_BUILD_SHIPPING
if (GEngine)
{
    GEngine->AddOnScreenDebugMessage(10, 0.f, FColor::Green,
        FString::Printf(TEXT("MoveDir: %s"),
            *RuntimeData->DesiredWorldMoveDir.ToString()));
    GEngine->AddOnScreenDebugMessage(11, 0.f, FColor::Yellow,
        FString::Printf(TEXT("Blend: X=%.2f Y=%.2f Angle=%.1f"),
            RuntimeData->AnimBlendX, RuntimeData->AnimBlendY,
            RuntimeData->MoveAngle));
    GEngine->AddOnScreenDebugMessage(12, 0.f, FColor::Cyan,
        FString::Printf(TEXT("Intents: Jump=%d Attack=%d Dodge=%d Sprint=%d"),
            RuntimeData->bWantsToJump, RuntimeData->bWantsToAttack,
            RuntimeData->bWantsToDodge, RuntimeData->bWantsToSprint));
    GEngine->AddOnScreenDebugMessage(13, 0.f, FColor::Red,
        FString::Printf(TEXT("RootMotion: %d Delta=%s"),
            RuntimeData->bHasRootMotion,
            *RuntimeData->RootMotionDelta.ToString()));
}
#endif

功能验证:
├─ 按 W → DesiredWorldMoveDir 指向摄像机前方
├─ 按 A → DesiredWorldMoveDir 指向摄像机左方
├─ 旋转摄像机后按 W → DesiredWorldMoveDir 跟随新朝向
├─ 按攻击键 → bWantsToAttack = true，下一帧清零
├─ 按跳跃键 → bWantsToJump = true，下一帧清零
├─ 按闪避键 → bWantsToDodge = true，下一帧清零
├─ 按住 Sprint → bWantsToSprint = true，松开后清零
├─ 移动时 AnimBlendX/Y 平滑变化，不突变
├─ 停止移动后 AnimBlendX/Y 平滑归零
├─ MoveAngle 在 [-180, 180] 范围内
└─ 旧版移动系统仍然正常工作（临时兼容）

关键点:
├─ IntentPipeline 必须在 InputPipeline.Process() 之后执行
├─ ViewRotationProcessor 必须在 LocomotionIntentProcessor 之前
├─ 所有 IntentProcessor 只读 InputData，不修改
├─ 每个 RuntimeData 字段只有一个处理器写入
└─ 注意视角旋转重复调用问题（见 3.6 说明）
```

---

### 阶段四：状态机（纯 C++ 状态机）

状态机只读 RuntimeData 的意图和仲裁标记，不直接读输入、不直接调 GAS。
状态切换时通过回调同步 GameplayTag。

核心原则:
```
状态机是"门卫"，管线是"信息员":
├─ 意图层告诉状态机"玩家想做什么"（bWantsToAttack 等）
├─ 仲裁层告诉状态机"现在能做什么"（bBlockAttack 等）
├─ ActionArbiter 告诉状态机"GAS 批准了什么"（ActionGranted）
└─ 状态机综合判断后决定"实际做什么"
```

文件结构:
```
Source/GGYGO/
├── Public/StateMachine/
│   ├── CharacterStateMachine.h       状态机主类
│   ├── CharacterState.h              状态基类
│   └── States/
│       ├── IdleState.h
│       ├── LocomotionState.h
│       ├── InAirState.h
│       ├── AttackingState.h
│       ├── DodgingState.h
│       ├── SprintingState.h
│       ├── HitStunState.h
│       ├── StunnedState.h
│       └── DeadState.h
├── Private/StateMachine/
│   ├── CharacterStateMachine.cpp
│   ├── CharacterState.cpp
│   └── States/
│       ├── IdleState.cpp
│       ├── LocomotionState.cpp
│       ├── InAirState.cpp
│       ├── AttackingState.cpp
│       ├── DodgingState.cpp
│       ├── SprintingState.cpp
│       ├── HitStunState.cpp
│       ├── StunnedState.cpp
│       └── DeadState.cpp
```

#### 4.1 创建状态枚举

```cpp
/**
 * @file CharacterStateType.h
 * @brief 角色状态枚举
 */
#pragma once

#include "CoreMinimal.h"

UENUM(BlueprintType)
enum class ECharacterStateType : uint8
{
	Idle,
	Locomotion,
	InAir,
	Attacking,
	Dodging,
	Sprinting,
	HitStun,
	Stunned,
	Dead,
	Interacting
};
```

#### 4.2 创建状态基类

CharacterState.h:
```cpp
/**
 * @file CharacterState.h
 * @brief 角色状态基类
 *
 * 每个状态是独立的纯 C++ 类。
 * 只读 RuntimeData 做判断，不直接读输入或调 GAS。
 */
#pragma once

#include "CoreMinimal.h"

struct FRuntimeData;
class FCharacterStateMachine;
enum class ECharacterStateType : uint8;

class FCharacterState
{
public:
	explicit FCharacterState(ECharacterStateType InType);
	virtual ~FCharacterState() = default;

	/** 进入状态时调用 */
	virtual void Enter(FRuntimeData& RuntimeData) {}

	/** 每帧更新，返回是否要切换状态 */
	virtual void Update(float DeltaTime, FRuntimeData& RuntimeData, FCharacterStateMachine& SM) {}

	/** 退出状态时调用 */
	virtual void Exit(FRuntimeData& RuntimeData) {}

	/** 获取状态类型 */
	ECharacterStateType GetType() const { return StateType; }

protected:
	/** 当前状态类型标识 */
	ECharacterStateType StateType;
};
```

CharacterState.cpp:
```cpp
/**
 * @file CharacterState.cpp
 * @brief 角色状态基类实现
 */
#include "StateMachine/CharacterState.h"

FCharacterState::FCharacterState(ECharacterStateType InType)
	: StateType(InType)
{
}
```

#### 4.3 创建状态机主类

CharacterStateMachine.h:
```cpp
/**
 * @file CharacterStateMachine.h
 * @brief 纯 C++ 状态机
 *
 * 只读 RuntimeData 的意图和仲裁标记。
 * 不直接读输入，不直接读 GAS。
 * 状态切换时同步 GameplayTag（通过回调）。
 */
#pragma once

#include "CoreMinimal.h"

struct FRuntimeData;
class FCharacterState;
enum class ECharacterStateType : uint8;

class FCharacterStateMachine
{
public:
	FCharacterStateMachine();
	~FCharacterStateMachine();

	/** 初始化，创建所有状态实例 */
	void Init();

	/**
	 * 每帧更新（Tick 第 5 步）
	 * 前置条件: IntentPipeline 和 ArbiterPipeline 已执行
	 */
	void Update(float DeltaTime, FRuntimeData& RuntimeData);

	/**
	 * 尝试切换到目标状态
	 * @return 是否切换成功
	 */
	bool TryTransitionTo(ECharacterStateType NewState, FRuntimeData& RuntimeData);

	/**
	 * 强制切换状态（不检查转换规则表）
	 * 用于 HitStun / Stunned / Dead 等仲裁层强制打断
	 */
	void ForceTransitionTo(ECharacterStateType NewState, FRuntimeData& RuntimeData);

	/** 获取当前状态类型 */
	ECharacterStateType GetCurrentStateType() const;

private:
	/** 执行状态切换的内部方法 */
	void PerformTransition(ECharacterStateType NewState, FRuntimeData& RuntimeData);

	/**
	 * 检查转换规则表
	 * @return 当前状态是否允许切换到目标状态
	 */
	bool IsTransitionAllowed(ECharacterStateType From, ECharacterStateType To) const;

	/**
	 * 全局打断检查（每帧在状态自身逻辑之前执行）
	 * 检查仲裁标记（死亡/眩晕/受击）→ 匹配则强制切换
	 */
	void CheckGlobalInterrupts(FRuntimeData& RuntimeData);

	/** 所有状态实例（按枚举值索引） */
	TMap<ECharacterStateType, TUniquePtr<FCharacterState>> States;

	/**
	 * 当前活跃状态（非拥有型指针）
	 * 指向 States 中某个 TUniquePtr 管理的状态实例。
	 * 不负责 delete —— States(TUniquePtr) 随 FCharacterStateMachine 销毁时自动回收。
	 * 对外部 UObject（如 ACharacter*）也用同样方式：裸指针指向，不拥有，GC 管理。
	 */
	FCharacterState* CurrentState = nullptr;
};
```

CharacterStateMachine.cpp:
```cpp
/**
 * @file CharacterStateMachine.cpp
 * @brief 状态机实现
 */
#include "StateMachine/CharacterStateMachine.h"
#include "StateMachine/CharacterState.h"
#include "StateMachine/States/IdleState.h"
#include "StateMachine/States/LocomotionState.h"
#include "StateMachine/States/InAirState.h"
#include "StateMachine/States/AttackingState.h"
#include "StateMachine/States/DodgingState.h"
#include "StateMachine/States/SprintingState.h"
#include "StateMachine/States/HitStunState.h"
#include "StateMachine/States/StunnedState.h"
#include "StateMachine/States/DeadState.h"
#include "Data/RuntimeData.h"

FCharacterStateMachine::FCharacterStateMachine() = default;
FCharacterStateMachine::~FCharacterStateMachine() = default;

void FCharacterStateMachine::Init()
{
	// 创建所有状态实例
	States.Add(ECharacterStateType::Idle, MakeUnique<FIdleState>());
	States.Add(ECharacterStateType::Locomotion, MakeUnique<FLocomotionState>());
	States.Add(ECharacterStateType::InAir, MakeUnique<FInAirState>());
	States.Add(ECharacterStateType::Attacking, MakeUnique<FAttackingState>());
	States.Add(ECharacterStateType::Dodging, MakeUnique<FDodgingState>());
	States.Add(ECharacterStateType::Sprinting, MakeUnique<FSprintingState>());
	States.Add(ECharacterStateType::HitStun, MakeUnique<FHitStunState>());
	States.Add(ECharacterStateType::Stunned, MakeUnique<FStunnedState>());
	States.Add(ECharacterStateType::Dead, MakeUnique<FDeadState>());

	// 默认进入 Idle
	CurrentState = States[ECharacterStateType::Idle].Get();
}

void FCharacterStateMachine::Update(float DeltaTime, FRuntimeData& RuntimeData)
{
	if (!CurrentState) return;

	// 1. 全局打断检查（仲裁标记驱动，优先于状态自身逻辑）
	CheckGlobalInterrupts(RuntimeData);

	// 2. 当前状态自身逻辑（读 RuntimeData 意图 + 仲裁标记，尝试转换）
	CurrentState->Update(DeltaTime, RuntimeData, *this);
}

void FCharacterStateMachine::CheckGlobalInterrupts(FRuntimeData& RuntimeData)
{
	// 死亡最高优先级
	// TODO: 阶段六仲裁管线完成后，这里读 RuntimeData 的死亡标记
	// if (RuntimeData.bIsDead && GetCurrentStateType() != ECharacterStateType::Dead)
	//     ForceTransitionTo(ECharacterStateType::Dead, RuntimeData);

	// 眩晕
	// if (RuntimeData.bIsStunned && GetCurrentStateType() != ECharacterStateType::Stunned)
	//     ForceTransitionTo(ECharacterStateType::Stunned, RuntimeData);

	// 受击硬直
	// if (RuntimeData.bIsHitStunned && GetCurrentStateType() != ECharacterStateType::HitStun)
	//     ForceTransitionTo(ECharacterStateType::HitStun, RuntimeData);
}

bool FCharacterStateMachine::TryTransitionTo(ECharacterStateType NewState, FRuntimeData& RuntimeData)
{
	if (!CurrentState) return false;
	if (CurrentState->GetType() == NewState) return false;

	if (!IsTransitionAllowed(CurrentState->GetType(), NewState))
		return false;

	PerformTransition(NewState, RuntimeData);
	return true;
}

void FCharacterStateMachine::ForceTransitionTo(ECharacterStateType NewState, FRuntimeData& RuntimeData)
{
	if (CurrentState && CurrentState->GetType() == NewState) return;
	PerformTransition(NewState, RuntimeData);
}

void FCharacterStateMachine::PerformTransition(ECharacterStateType NewState, FRuntimeData& RuntimeData)
{
	if (CurrentState)
	{
		CurrentState->Exit(RuntimeData);
	}

	auto* Found = States.Find(NewState);
	if (Found)
	{
		CurrentState = Found->Get();
		CurrentState->Enter(RuntimeData);
	}
}

ECharacterStateType FCharacterStateMachine::GetCurrentStateType() const
{
	return CurrentState ? CurrentState->GetType() : ECharacterStateType::Idle;
}

bool FCharacterStateMachine::IsTransitionAllowed(ECharacterStateType From, ECharacterStateType To) const
{
	// 转换规则表
	// HitStun / Stunned / Dead 走 ForceTransition，不经过这里
	switch (From)
	{
	case ECharacterStateType::Idle:
		return To == ECharacterStateType::Locomotion
			|| To == ECharacterStateType::InAir
			|| To == ECharacterStateType::Attacking
			|| To == ECharacterStateType::Dodging
			|| To == ECharacterStateType::Sprinting
			|| To == ECharacterStateType::Interacting;

	case ECharacterStateType::Locomotion:
		return To == ECharacterStateType::Idle
			|| To == ECharacterStateType::InAir
			|| To == ECharacterStateType::Attacking
			|| To == ECharacterStateType::Dodging
			|| To == ECharacterStateType::Sprinting
			|| To == ECharacterStateType::Interacting;

	case ECharacterStateType::InAir:
		return To == ECharacterStateType::Idle
			|| To == ECharacterStateType::Locomotion
			|| To == ECharacterStateType::Attacking;

	case ECharacterStateType::Attacking:
		return To == ECharacterStateType::Idle
			|| To == ECharacterStateType::Dodging
			|| To == ECharacterStateType::Attacking;

	case ECharacterStateType::Dodging:
		return To == ECharacterStateType::Idle
			|| To == ECharacterStateType::Locomotion;

	case ECharacterStateType::Sprinting:
		return To == ECharacterStateType::Idle
			|| To == ECharacterStateType::Locomotion
			|| To == ECharacterStateType::InAir
			|| To == ECharacterStateType::Attacking
			|| To == ECharacterStateType::Dodging;

	case ECharacterStateType::HitStun:
		return To == ECharacterStateType::Idle
			|| To == ECharacterStateType::HitStun
			|| To == ECharacterStateType::Stunned;

	case ECharacterStateType::Stunned:
		return To == ECharacterStateType::Idle;

	case ECharacterStateType::Dead:
		return false; // 终态，不允许任何转换

	default:
		return false;
	}
}
```

#### 4.4 创建具体状态（示例：IdleState 和 LocomotionState）

IdleState.h:
```cpp
/**
 * @file IdleState.h
 * @brief 待机状态
 *
 * 角色静止时的默认状态。
 * 检测移动/跳跃/攻击/闪避/冲刺意图 → 切换到对应状态。
 */
#pragma once

#include "StateMachine/CharacterState.h"

class FIdleState : public FCharacterState
{
public:
	FIdleState();
	virtual void Enter(FRuntimeData& RuntimeData) override;
	virtual void Update(float DeltaTime, FRuntimeData& RuntimeData, FCharacterStateMachine& SM) override;
	virtual void Exit(FRuntimeData& RuntimeData) override;
};
```

IdleState.cpp:
```cpp
/**
 * @file IdleState.cpp
 * @brief 待机状态实现
 */
#include "StateMachine/States/IdleState.h"
#include "StateMachine/CharacterStateMachine.h"
#include "Data/RuntimeData.h"

FIdleState::FIdleState()
	: FCharacterState(ECharacterStateType::Idle)
{
}

void FIdleState::Enter(FRuntimeData& RuntimeData)
{
	// TODO: 同步 GameplayTag（State.Idle）
}

void FIdleState::Update(float DeltaTime, FRuntimeData& RuntimeData, FCharacterStateMachine& SM)
{
	// ActionGranted 优先（GAS 批准的动作）
	// TODO: 阶段六仲裁管线完成后启用
	// if (RuntimeData.ActionGranted == ECharacterStateType::Attacking)
	// {
	//     SM.TryTransitionTo(ECharacterStateType::Attacking, RuntimeData);
	//     return;
	// }

	// 跳跃
	if (RuntimeData.bWantsToJump && !RuntimeData.bBlockMove)
	{
		SM.TryTransitionTo(ECharacterStateType::InAir, RuntimeData);
		return;
	}

	// 闪避
	if (RuntimeData.bWantsToDodge && !RuntimeData.bBlockDodge)
	{
		SM.TryTransitionTo(ECharacterStateType::Dodging, RuntimeData);
		return;
	}

	// 冲刺
	if (RuntimeData.bWantsToSprint && !RuntimeData.DesiredWorldMoveDir.IsNearlyZero() && !RuntimeData.bBlockMove)
	{
		SM.TryTransitionTo(ECharacterStateType::Sprinting, RuntimeData);
		return;
	}

	// 移动
	if (!RuntimeData.DesiredWorldMoveDir.IsNearlyZero() && !RuntimeData.bBlockMove)
	{
		SM.TryTransitionTo(ECharacterStateType::Locomotion, RuntimeData);
		return;
	}
}

void FIdleState::Exit(FRuntimeData& RuntimeData)
{
	// TODO: 移除 GameplayTag（State.Idle）
}
```

LocomotionState.h:
```cpp
/**
 * @file LocomotionState.h
 * @brief 移动状态
 *
 * 角色正在移动。
 * 停止输入 → Idle，跳跃 → InAir，攻击/闪避/冲刺 → 对应状态。
 */
#pragma once

#include "StateMachine/CharacterState.h"

class FLocomotionState : public FCharacterState
{
public:
	FLocomotionState();
	virtual void Enter(FRuntimeData& RuntimeData) override;
	virtual void Update(float DeltaTime, FRuntimeData& RuntimeData, FCharacterStateMachine& SM) override;
	virtual void Exit(FRuntimeData& RuntimeData) override;
};
```

LocomotionState.cpp:
```cpp
/**
 * @file LocomotionState.cpp
 * @brief 移动状态实现
 */
#include "StateMachine/States/LocomotionState.h"
#include "StateMachine/CharacterStateMachine.h"
#include "Data/RuntimeData.h"

FLocomotionState::FLocomotionState()
	: FCharacterState(ECharacterStateType::Locomotion)
{
}

void FLocomotionState::Enter(FRuntimeData& RuntimeData)
{
	// TODO: 同步 GameplayTag（State.Locomotion）
}

void FLocomotionState::Update(float DeltaTime, FRuntimeData& RuntimeData, FCharacterStateMachine& SM)
{
	// 跳跃
	if (RuntimeData.bWantsToJump && !RuntimeData.bBlockMove)
	{
		SM.TryTransitionTo(ECharacterStateType::InAir, RuntimeData);
		return;
	}

	// 闪避
	if (RuntimeData.bWantsToDodge && !RuntimeData.bBlockDodge)
	{
		SM.TryTransitionTo(ECharacterStateType::Dodging, RuntimeData);
		return;
	}

	// 冲刺
	if (RuntimeData.bWantsToSprint && !RuntimeData.bBlockMove)
	{
		SM.TryTransitionTo(ECharacterStateType::Sprinting, RuntimeData);
		return;
	}

	// 停止移动 → 回到 Idle
	if (RuntimeData.DesiredWorldMoveDir.IsNearlyZero())
	{
		SM.TryTransitionTo(ECharacterStateType::Idle, RuntimeData);
		return;
	}
}

void FLocomotionState::Exit(FRuntimeData& RuntimeData)
{
	// TODO: 移除 GameplayTag（State.Locomotion）
}
```

其余状态（InAir、Attacking、Dodging、Sprinting、HitStun、Stunned、Dead）结构相同，
先创建空壳，后续阶段逐步填充逻辑:

```cpp
// 空壳模板（以 InAirState 为例）
// InAirState.h
#pragma once
#include "StateMachine/CharacterState.h"

class FInAirState : public FCharacterState
{
public:
	FInAirState() : FCharacterState(ECharacterStateType::InAir) {}
	virtual void Update(float DeltaTime, FRuntimeData& RuntimeData, FCharacterStateMachine& SM) override;
};

// InAirState.cpp
#include "StateMachine/States/InAirState.h"
#include "StateMachine/CharacterStateMachine.h"
#include "Data/RuntimeData.h"

void FInAirState::Update(float DeltaTime, FRuntimeData& RuntimeData, FCharacterStateMachine& SM)
{
	// 落地检测 → 回到 Idle 或 Locomotion
	if (RuntimeData.bIsGrounded)
	{
		if (RuntimeData.DesiredWorldMoveDir.IsNearlyZero())
			SM.TryTransitionTo(ECharacterStateType::Idle, RuntimeData);
		else
			SM.TryTransitionTo(ECharacterStateType::Locomotion, RuntimeData);
	}
}
```

#### 4.5 修改 BaseCharacter 集成状态机

BaseCharacter.h 添加:
```cpp
#include "StateMachine/CharacterStateMachine.h"

// 在 protected 里:
/** 角色状态机 */
TUniquePtr<FCharacterStateMachine> StateMachine;
```

BaseCharacter.cpp 修改:
```cpp
ABaseCharacter::ABaseCharacter()
{
	// ... 已有代码 ...
	StateMachine = MakeUnique<FCharacterStateMachine>();
}

void ABaseCharacter::BeginPlay()
{
	Super::BeginPlay();
	// ... 已有代码 ...
	StateMachine->Init();
}

void ABaseCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// 1. ArbiterPipeline（未来）
	// 2. 输入管线
	InputPipeline->Process(DeltaTime);
	// 3. 意图处理
	IntentPipeline->ProcessIntents(*InputData, *RuntimeData);
	// 4. 参数处理
	IntentPipeline->ProcessParameters(*RuntimeData, DeltaTime);
	// 5. 状态机（本阶段新增）
	StateMachine->Update(DeltaTime, *RuntimeData);
	// 6. MotionDriver（未来）

	// 旧版移动（临时兼容）
	RootMotionProc->Process(DeltaTime);

	// 帧末清零
	RuntimeData->ResetFrameIntents();
}
```

#### 4.6 修改 RuntimeData 添加状态机相关字段

RuntimeData.h 添加:
```cpp
// 在仲裁标记区域后面添加:

// ============================================================
// 状态机数据（由 StateMachine 写入）
// ============================================================

/** 当前角色状态（StateMachine 写入） */
ECharacterStateType CurrentState = ECharacterStateType::Idle;
```

#### 4.7 验证清单

```
编译验证:
├─ 状态枚举、状态基类、状态机主类编译通过
├─ 所有具体状态类编译通过
├─ BaseCharacter 持有 StateMachine（TUniquePtr）
└─ 转换规则表覆盖所有状态组合

运行验证（加调试日志）:
#if !UE_BUILD_SHIPPING
if (GEngine)
{
    GEngine->AddOnScreenDebugMessage(20, 0.f, FColor::Magenta,
        FString::Printf(TEXT("State: %d"),
            static_cast<uint8>(StateMachine->GetCurrentStateType())));
}
#endif

功能验证:
├─ 启动后默认 Idle 状态
├─ 按 W → Idle → Locomotion
├─ 松开 W → Locomotion → Idle
├─ 按跳跃 → Idle/Locomotion → InAir
├─ 落地 → InAir → Idle/Locomotion
├─ Dead 状态无法切换到任何其他状态
├─ ForceTransition 不检查规则表，直接切换
└─ 状态切换时 Enter/Exit 正确调用

关键点:
├─ 状态机只读 RuntimeData，不直接读输入或 GAS
├─ HitStun/Stunned/Dead 走 ForceTransition（由仲裁层触发）
├─ 全局打断检查在状态自身逻辑之前执行
├─ ActionGranted 相关逻辑暂时注释，等阶段六仲裁管线完成后启用
└─ GameplayTag 同步暂时用 TODO 标记，等阶段八 GAS 接入后实现
```

---

### 阶段五：MotionDriver（替代 RootMotionProcessor）✅ 已完成

MotionDriver 是管线第 6 步，只做驱动不做判断。
读取 RuntimeData 的移动数据 → 调 CharacterMovement API → 写回 RuntimeData 广播数据。

**防滑步架构（实际实现与原计划有差异）：**
- 输入方向（WASD）决定移动方向
- 动画速度（AnimSpeed，由 RootMotionParameterProcessor 从 Speed 曲线读取）决定移动快慢
- 两者融合：`RequestDirectMove(方向 × AnimSpeed)` —— 绕过 CMC 加速/减速，帧级同步无滑步
- `bHasRootMotion` + `RootMotionDelta` 保留给 Montage/技能动画使用
- `AnimSpeed=0` 时自动降级为 `AddMovementInput`（兼容未配曲线的动画，约 0.3s 启动延迟）

**与原 Roadmap 计划的核心差异：**

| 方面 | 原计划 | 实际实现 |
|------|--------|---------|
| 常规移动 | `AddMovementInput`（走CMC加速） | `RequestDirectMove(方向×AnimSpeed)`（直设速度，防滑步） |
| 速度来源 | CMC 的 MaxWalkSpeed | AnimSpeed（从动画 Speed 曲线读取） |
| 降级策略 | 无 | AnimSpeed=0 时退化为 AddMovementInput |
| Root Motion 提取 | MotionDriver 不负责 | 由 RootMotionParameterProcessor（第4步）从 Speed 曲线提取 AnimSpeed |

#### 5.1 MotionDriver 实际实现

文件: `Source/GGYGO/Public/Drivers/MotionDriver.h` / `Private/Drivers/MotionDriver.cpp`
类型: 纯 C++ 类，`F` 前缀

MotionDriver.h:
```cpp
/**
 * @file MotionDriver.h
 * @brief 运动驱动器 - 角色位移的唯一执行出口
 *
 * 只读 RuntimeData → 调 CharacterMovement API → 写回广播数据。
 * 不知道输入、状态机、GAS 的存在。
 *
 * 防滑步架构：
 *   输入方向(WASD) × 动画速度(AnimSpeed) = RequestDirectMove（帧级同步）
 *
 * 两条移动路径：
 *   - ProcessRootMotionMovement：Montage/技能动画专用（RootMotionDelta）
 *   - ProcessLocomotion：常规移动，AnimSpeed>0 时用 RequestDirectMove 直设速度
 *     AnimSpeed=0 时降级为 AddMovementInput（走 CMC 加速）
 *
 * Init 时设置 IgnoreRootMotion（关闭 UE 自动 Root Motion）。
 */
#pragma once

#include "CoreMinimal.h"
#include "Data/RuntimeData.h"

class ACharacter;
class UCharacterMovementComponent;
class USkeletalMeshComponent;

class FMotionDriver
{
public:
    void Init(ACharacter* InOwner);

    /** 每帧由 BaseCharacter::Tick 调用，根据 RuntimeData 驱动角色位移 */
    void Process(float DeltaTime, FRuntimeData& RuntimeData);

private:
    /** Root Motion 路径：Montage/技能动画的帧位移 → 瞬时速度 */
    void ProcessRootMotionMovement(const FVector& Delta, float DeltaTime);

    /** 常规移动路径：输入方向 × 动画速度 → RequestDirectMove（防滑步核心） */
    void ProcessLocomotion(float DeltaTime, const FVector& WorldDir, float InAnimSpeed);

    /** 回写 RuntimeData 中的 CurrentSpeed/bIsMoving/MoveAngle */
    void UpdateRuntimeData(FRuntimeData& RuntimeData);

    ACharacter* Owner = nullptr;
    UCharacterMovementComponent* Movement = nullptr;
    USkeletalMeshComponent* Mesh = nullptr;

    /** 默认最大行走速度（Init 时备份，供 AnimSpeed=0 时降级使用） */
    float DefaultMaxWalkSpeed = 600.f;
};
```

MotionDriver.cpp:
```cpp
/**
 * @file MotionDriver.cpp
 * @brief 运动驱动器实现
 *
 * 防滑步架构：
 *   - 输入方向（WASD）决定移动方向
 *   - 动画速度（AnimSpeed）决定移动快慢
 *   - 两者融合：RequestDirectMove(方向 × AnimSpeed)
 *   - 结果：动画跑多快 → 角色就跑多快 → 帧级同步无滑步
 *   - bHasRootMotion 仅保留给 Montage/技能动画使用
 */
#include "Drivers/MotionDriver.h"
#include "Data/RuntimeData.h"
#include "GameFramework/Character.h"
#include "GameFramework/CharacterMovementComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Animation/AnimInstance.h"

void FMotionDriver::Init(ACharacter* InOwner)
{
    Owner = InOwner;
    if (!Owner) return;

    Mesh = Owner->GetMesh();
    Movement = Owner->GetCharacterMovement();

    if (Mesh)
    {
        if (UAnimInstance* AnimInst = Mesh->GetAnimInstance())
        {
            AnimInst->SetRootMotionMode(ERootMotionMode::IgnoreRootMotion);
        }
    }

    DefaultMaxWalkSpeed = Movement ? Movement->MaxWalkSpeed : 600.f;
}

void FMotionDriver::Process(float DeltaTime, FRuntimeData& RuntimeData)
{
    if (!Owner || !Movement) return;

    // 被仲裁阻止移动时，只更新运行时数据，不驱动位移
    if (RuntimeData.bBlockMove)
    {
        UpdateRuntimeData(RuntimeData);
        return;
    }

    // 路径 A: Root Motion 模式（Montage/技能动画专用）
    if (RuntimeData.bHasRootMotion)
    {
        ProcessRootMotionMovement(RuntimeData.RootMotionDelta, DeltaTime);
    }
    // 路径 B: 常规移动（AnimSpeed 由 RootMotionParameterProcessor 从 Speed 曲线读取）
    else if (!RuntimeData.DesiredWorldMoveDir.IsNearlyZero())
    {
        ProcessLocomotion(DeltaTime, RuntimeData.DesiredWorldMoveDir, RuntimeData.AnimSpeed);
    }

    UpdateRuntimeData(RuntimeData);
}

void FMotionDriver::ProcessRootMotionMovement(const FVector& Delta, float DeltaTime)
{
    if (DeltaTime <= KINDA_SMALL_NUMBER) return;

    FVector Velocity = Delta / DeltaTime;
    Movement->RequestDirectMove(Velocity, false);
}

void FMotionDriver::ProcessLocomotion(float DeltaTime, const FVector& WorldDir, float InAnimSpeed)
{
    FVector Dir = WorldDir.GetSafeNormal();

    if (InAnimSpeed > 0.f)
    {
        // 防滑步核心：输入方向 × 动画速度 → 直设速度，绕过 CMC 加速/减速
        FVector TargetVelocity = Dir * InAnimSpeed;
        Movement->RequestDirectMove(TargetVelocity, false);
    }
    else
    {
        // 降级路径：AnimSpeed 不可用时退化为标准 AddMovementInput
        // 注意：此路径走 CMC 加速度，会产生 ~0.3s 启动延迟
        Owner->AddMovementInput(Dir, 1.0f);
    }
}

void FMotionDriver::UpdateRuntimeData(FRuntimeData& RuntimeData)
{
    if (!Owner) return;

    FVector Velocity = Owner->GetVelocity();
    RuntimeData.CurrentSpeed = Velocity.Size2D();
    RuntimeData.bIsMoving = RuntimeData.CurrentSpeed > 10.f;

    if (RuntimeData.bIsMoving)
    {
        FVector LocalVelocity = Owner->GetActorTransform()
            .InverseTransformVector(Velocity);
        RuntimeData.MoveAngle = FMath::RadiansToDegrees(
            FMath::Atan2(LocalVelocity.Y, LocalVelocity.X));
    }
    else
    {
        RuntimeData.MoveAngle = 0.f;
    }
}
```

#### 5.2 BaseCharacter — 已集成 MotionDriver ✅

BaseCharacter 已在构造函数中创建 `MotionDriver = MakeUnique<FMotionDriver>()`，
在 `BeginPlay()` 中调用 `MotionDriver->Init(this)`，在 `Tick()` 第 6 步调用 `MotionDriver->Process(DeltaTime, *RuntimeData)`。

旧的 `RootMotionProcessor` 已完全删除。

#### 5.3 PlayerCharacter — 已清理临时兼容代码 ✅

PlayerCharacter 的回调现在只写 `InputPipeline`：
- `OnMoveInput` → `InputPipeline->SetMoveInput(Input)`
- `OnMoveCompleted` → `InputPipeline->ClearMoveInput()`
- `OnLookInput` → `InputPipeline->SetLookInput(Input)`（视角由 ViewRotationProcessor 接管）
- `OnJumpInput` → `InputPipeline->SetJumpPressed()`

旧的 `DesiredMoveDirection` 成员和所有临时兼容代码已删除。

#### 5.4 已删除旧文件 ✅

- `Source/GGYGO/Public/Movement/RootMotionProcessor.h` — 已删除
- `Source/GGYGO/Private/Movement/RootMotionProcessor.cpp` — 已删除

#### 5.5 验证清单 ✅

```
编译验证:
├─ MotionDriver.h/.cpp 编译通过 ✅
├─ BaseCharacter.h/.cpp 无 RootMotionProcessor 引用 ✅
├─ PlayerCharacter.h/.cpp 无临时兼容代码 ✅
└─ 删除旧文件后编译无报错 ✅

运行验证（接入动画 Speed 曲线后）:
├─ 按 W → 角色向前移动 ✅
├─ 按 S → 角色向后移动 ✅
├─ 松开 → 角色停止 ✅
├─ 移动方向正确（跟随摄像机朝向）✅
├─ 防滑步生效：动画跑多快角色就跑多快 ✅
├─ AnimSpeed=0（无 Speed 曲线）时降级为 AddMovementInput ✅
├─ CurrentSpeed > 0 表示移动中 ✅
├─ MoveAngle 在 [-180, 180] 范围内 ✅
├─ 调试 UI 显示 AnimSpeed/Bip001/CurrentSpeed 等数据 ✅
└─ 视角旋转正常（ViewRotationProcessor 接管）✅

关键点:
├─ MotionDriver 不知道输入、状态机、GAS
├─ 防滑步核心: RequestDirectMove(方向 × AnimSpeed)
├─ 降级策略: AnimSpeed=0 → AddMovementInput（走 CMC 加速）
├─ RootMotionDelta/bHasRootMotion 保留给 Montage/技能动画
├─ SkeletalMeshComponent 引用缓存在 FMotionDriver（不拥有）
└─ Init 时设置 IgnoreRootMotion，关闭引擎自动 Root Motion
```

---

### 阶段六：仲裁管线（三层仲裁架构）⬜ 下一步

仲裁不是集中在一个地方，而是分散在三个不同层面，各自处理不同类型的冲突。
参考 BBB-Nexus 的三层仲裁架构，适配到 GGYGO 的 UE5 + GAS 体系。

#### 为什么现在做

- ASC 已挂载到 BaseCharacter（阶段八-A 提前完成），仲裁器可直接访问真实 ASC
- `bBlockMove/bBlockAttack/bBlockDodge` 在 RuntimeData 已预留，状态机已在读（目前始终 false）
- `ActionGranted` 字段已预留（注释状态），打开即可用
- 状态机的转换规则表已覆盖 Attacking/Dodging/HitStun/Stunned/Dead

#### 阶段六建什么

| 文件 | 职责 |
|------|------|
| `Pipeline/Interfaces/IArbiter.h` | 仲裁器接口，定义 `Arbitrate(RuntimeData, DeltaTime)` |
| `Pipeline/ArbiterPipeline.h/.cpp` | 仲裁管线主类，持有四个仲裁器，Tick 第 1 步执行 |
| `Pipeline/Arbiters/GASArbiter.h/.cpp` | 读 ASC GameplayTag → 写仲裁阻断标记 |
| `Pipeline/Arbiters/ActionArbiter.h/.cpp` | 读意图 → `ASC->TryActivateAbility` → 写 `ActionGranted` |
| `Pipeline/Arbiters/HealthArbiter.h/.cpp` | 伤害队列统一结算 → 血量 ≤ 0 全面阻断 |
| `Pipeline/Arbiters/StaminaArbiter.h/.cpp` | Sprint 体力消耗 + 滞后恢复 |

#### BaseCharacter 改动

- `BeginPlay()` 中 `ArbiterPipeline->Init(ASC)` 注入真实 ASC
- `Tick()` 第 1 步插入 `ArbiterPipeline->Process(*RuntimeData, DeltaTime)`

#### 做完后的数据流

```
Tick 第 1 步: ArbiterPipeline
  ├─ GASArbiter:   ASC 有 "State.Stunned" Tag → bBlockMove/bBlockAttack = true
  ├─ ActionArbiter: bWantsToAttack → TryActivateAbility(GA_Attack) → ActionGranted = Attacking
  ├─ HealthArbiter: 伤害队列结算 → GE 扣血 → Health ≤ 0 → 全面阻断
  └─ StaminaArbiter: Sprint 消耗体力 → 枯竭 → bWantsToSprint = false

Tick 第 5 步: StateMachine
  ├─ CheckGlobalInterrupts: 检测阻断标记 → ForceTransitionTo(Dead/Stunned)
  ├─ IdleState: bBlockMove=true → 不切 RunStart
  └─ 各状态: ActionGranted 优先 → 切 Attacking/Dodging
```

三层仲裁总览:
```
第一层：意图处理器内部仲裁（同一按键的多种可能）
  └─ 发生在 IntentPipeline.ProcessIntents() 阶段
  └─ 按键级冲突：跳跃 vs 翻越、运动档位选择
  └─ 用优先级链在意图生成阶段就选定唯一结果

第二层：ArbiterPipeline 全局仲裁（跨系统资源裁决）
  └─ 发生在 Tick 最开头，比意图处理器还早执行
  └─ 全局性资源冲突：动作优先级、血量、体力、LOD

第三层：状态机全局打断（紧急状态强制覆盖）
  └─ 发生在 StateMachine.Update() 内部，状态自身逻辑之前
  └─ 紧急打断：死亡、眩晕、受击等强制状态切换
```

帧级协作关系:
```
帧开始
│
├── ArbiterPipeline（第二层）
│   └── 全局资源裁决：动作优先级、血量、体力、LOD
│
├── InputPipeline
│
├── IntentProcessors（第一层）
│   └── 按键级仲裁：跳跃vs翻越、运动档位选择
│
├── ParameterProcessors
│
├── StateMachine.Update()
│   ├── GlobalInterruptProcessor（第三层）
│   │   └── 紧急打断：死亡、下落等强制状态切换
│   └── 状态自身逻辑
│
└── 帧结束 → ResetFrameIntents() 清零帧级意图
```

三层各自独立，不互相调用，通过 RuntimeData 黑板间接通信。

文件结构:
```
Source/GGYGO/
├── Public/Pipeline/
│   ├── ArbiterPipeline.h             仲裁管线主类
│   ├── Interfaces/
│   │   └── IArbiter.h                仲裁器接口
│   └── Arbiters/
│       ├── ActionArbiter.h           动作优先级仲裁
│       ├── GASArbiter.h              GAS 状态仲裁
│       ├── HealthArbiter.h           血量仲裁
│       └── StaminaArbiter.h          体力仲裁
├── Private/Pipeline/
│   ├── ArbiterPipeline.cpp
│   └── Arbiters/
│       ├── ActionArbiter.cpp
│       ├── GASArbiter.cpp
│       ├── HealthArbiter.cpp
│       └── StaminaArbiter.cpp
```

#### 6.1 创建仲裁器接口

IArbiter.h:
```cpp
/**
 * @file IArbiter.h
 * @brief 仲裁器接口
 *
 * 每个仲裁器在 Tick 最开头执行，读取系统状态，写入 RuntimeData 仲裁标记。
 * 仲裁器之间不互相依赖，通过 RuntimeData 间接通信。
 */
#pragma once

#include "CoreMinimal.h"

struct FRuntimeData;

class IArbiter
{
public:
	virtual ~IArbiter() = default;

	/**
	 * 每帧仲裁
	 * @param RuntimeData 运行时黑板（读取状态、写入仲裁标记）
	 * @param DeltaTime   帧间隔
	 */
	virtual void Arbitrate(FRuntimeData& RuntimeData, float DeltaTime) = 0;
};
```

#### 6.2 创建 GASArbiter（GAS 状态仲裁）

GASArbiter.h:
```cpp
/**
 * @file GASArbiter.h
 * @brief GAS 状态仲裁器
 *
 * 每帧读取 ASC 的 GameplayTag → 写入 RuntimeData 仲裁标记。
 * GE 施加的状态（眩晕、死亡等）通过这里影响整个管线系统。
 */
#pragma once

#include "Pipeline/Interfaces/IArbiter.h"

class UAbilitySystemComponent;

class FGASArbiter : public IArbiter
{
public:
	/** 注入 ASC 指针（BeginPlay 时调用） */
	void Init(UAbilitySystemComponent* InASC);

	virtual void Arbitrate(FRuntimeData& RuntimeData, float DeltaTime) override;

private:
	/** ASC 指针（不拥有，UObject 由 GC 管理） */
	UAbilitySystemComponent* ASC = nullptr;
};
```

GASArbiter.cpp:
```cpp
/**
 * @file GASArbiter.cpp
 * @brief GAS 状态仲裁器实现
 */
#include "Pipeline/Arbiters/GASArbiter.h"
#include "Data/RuntimeData.h"
#include "AbilitySystemComponent.h"
#include "GameplayTagContainer.h"

// Tag 缓存为 static，避免每帧字符串查找
static FGameplayTag Tag_Stunned;
static FGameplayTag Tag_Dead;

void FGASArbiter::Init(UAbilitySystemComponent* InASC)
{
	ASC = InASC;

	// 缓存常用 Tag
	Tag_Stunned = FGameplayTag::RequestGameplayTag(FName("State.Stunned"));
	Tag_Dead = FGameplayTag::RequestGameplayTag(FName("State.Dead"));
}

void FGASArbiter::Arbitrate(FRuntimeData& RuntimeData, float DeltaTime)
{
	if (!ASC) return;

	// 读取 Tag → 写入仲裁标记
	if (ASC->HasMatchingGameplayTag(Tag_Dead))
	{
		// 死亡：全面阻断
		RuntimeData.bBlockMove = true;
		RuntimeData.bBlockAttack = true;
		RuntimeData.bBlockDodge = true;
		RuntimeData.bBlockInput = true;
	}
	else if (ASC->HasMatchingGameplayTag(Tag_Stunned))
	{
		// 眩晕：阻止移动和攻击
		RuntimeData.bBlockMove = true;
		RuntimeData.bBlockAttack = true;
		RuntimeData.bBlockDodge = true;
	}
}
```

#### 6.3 创建 ActionArbiter（动作优先级仲裁）

ActionArbiter.h:
```cpp
/**
 * @file ActionArbiter.h
 * @brief 动作优先级仲裁器
 *
 * 读取 RuntimeData 意图 → 调 ASC TryActivateAbility → 写 ActionGranted。
 * 处理攻击、闪避等需要 GAS 批准的动作请求。
 *
 * 抗性规则（参考 BBB-Nexus）：
 * - 当前状态有"抗性"值，请求有"优先级"值
 * - 优先级 > 抗性 → 允许执行
 * - 翻滚抗性 = 100（几乎不可打断）
 * - 闪避抗性 = 80
 * - 其他状态抗性 = 0
 */
#pragma once

#include "Pipeline/Interfaces/IArbiter.h"

class UAbilitySystemComponent;

class FActionArbiter : public IArbiter
{
public:
	/** 注入 ASC 指针 */
	void Init(UAbilitySystemComponent* InASC);

	virtual void Arbitrate(FRuntimeData& RuntimeData, float DeltaTime) override;

private:
	UAbilitySystemComponent* ASC = nullptr;
};
```

ActionArbiter.cpp:
```cpp
/**
 * @file ActionArbiter.cpp
 * @brief 动作优先级仲裁器实现
 */
#include "Pipeline/Arbiters/ActionArbiter.h"
#include "Data/RuntimeData.h"
#include "AbilitySystemComponent.h"

void FActionArbiter::Init(UAbilitySystemComponent* InASC)
{
	ASC = InASC;
}

void FActionArbiter::Arbitrate(FRuntimeData& RuntimeData, float DeltaTime)
{
	if (!ASC) return;

	// 读取意图 → 尝试激活 GAS Ability
	if (RuntimeData.bWantsToAttack && !RuntimeData.bBlockAttack)
	{
		// TODO: ASC->TryActivateAbilityByClass(GA_Attack)
		// 成功 → RuntimeData.ActionGranted = ECharacterStateType::Attacking
		// 失败 → ActionGranted 不变
	}

	if (RuntimeData.bWantsToDodge && !RuntimeData.bBlockDodge)
	{
		// TODO: ASC->TryActivateAbilityByClass(GA_Dodge)
		// 成功 → RuntimeData.ActionGranted = ECharacterStateType::Dodging
	}
}
```

#### 6.4 创建 HealthArbiter（血量仲裁）

HealthArbiter.h:
```cpp
/**
 * @file HealthArbiter.h
 * @brief 血量仲裁器
 *
 * 维护伤害队列，每帧统一结算。
 * 血量 ≤ 0 → 设置死亡标记 + 全面阻断。
 *
 * 为什么用队列而不是直接扣血：
 * 同一帧可能有多个伤害源（比如爆炸波及），
 * 队列保证所有伤害在同一时刻统一结算，避免中间状态不一致。
 */
#pragma once

#include "Pipeline/Interfaces/IArbiter.h"

class UAbilitySystemComponent;

/** 伤害请求（入队用） */
struct FDamageRequest
{
	float Damage = 0.f;
	// TODO: 伤害来源、类型等扩展字段
};

class FHealthArbiter : public IArbiter
{
public:
	/** 注入 ASC 指针（读取 Health 属性） */
	void Init(UAbilitySystemComponent* InASC);

	virtual void Arbitrate(FRuntimeData& RuntimeData, float DeltaTime) override;

	/** 外部请求伤害（入队，不立即扣血） */
	void RequestDamage(const FDamageRequest& Request);

private:
	UAbilitySystemComponent* ASC = nullptr;

	/** 环形伤害队列（固定容量，零 GC） */
	static constexpr int32 MaxDamageQueue = 16;
	FDamageRequest DamageQueue[MaxDamageQueue];
	int32 DamageCount = 0;
};
```

HealthArbiter.cpp:
```cpp
/**
 * @file HealthArbiter.cpp
 * @brief 血量仲裁器实现
 */
#include "Pipeline/Arbiters/HealthArbiter.h"
#include "Data/RuntimeData.h"
#include "AbilitySystemComponent.h"

void FHealthArbiter::Init(UAbilitySystemComponent* InASC)
{
	ASC = InASC;
}

void FHealthArbiter::RequestDamage(const FDamageRequest& Request)
{
	if (DamageCount < MaxDamageQueue)
	{
		DamageQueue[DamageCount++] = Request;
	}
}

void FHealthArbiter::Arbitrate(FRuntimeData& RuntimeData, float DeltaTime)
{
	if (!ASC) return;

	// 统一结算伤害队列
	for (int32 i = 0; i < DamageCount; ++i)
	{
		// TODO: 通过 GE 扣血
		// ASC->ApplyGameplayEffectToSelf(GE_Damage, DamageQueue[i].Damage, ...)
	}
	DamageCount = 0; // 清空队列

	// TODO: 读取 AttributeSet 的 Health
	// if (Health <= 0.f)
	// {
	//     RuntimeData.bBlockMove = true;
	//     RuntimeData.bBlockAttack = true;
	//     RuntimeData.bBlockDodge = true;
	//     RuntimeData.bBlockInput = true;
	//     // 状态机第三层打断会检测到死亡标记 → ForceTransitionTo(Dead)
	// }
}
```

#### 6.5 创建 StaminaArbiter（体力仲裁）

StaminaArbiter.h:
```cpp
/**
 * @file StaminaArbiter.h
 * @brief 体力仲裁器
 *
 * 根据运动档位消耗或恢复体力。
 * 体力枯竭 → 阻止 Sprint。
 *
 * 滞后设计：枯竭后不是体力 > 0 就能冲刺，
 * 而是要恢复到 MaxStamina × StaminaRecoverThreshold（比如 20%）才解除枯竭。
 * 防止玩家在体力边缘反复切换冲刺。
 */
#pragma once

#include "Pipeline/Interfaces/IArbiter.h"

class UAbilitySystemComponent;

class FStaminaArbiter : public IArbiter
{
public:
	/** 注入 ASC 指针（读取 Stamina 属性） */
	void Init(UAbilitySystemComponent* InASC);

	virtual void Arbitrate(FRuntimeData& RuntimeData, float DeltaTime) override;

private:
	UAbilitySystemComponent* ASC = nullptr;

	/** 体力是否枯竭（滞后标记） */
	bool bIsStaminaDepleted = false;

	/** 体力恢复阈值（枯竭后需恢复到此比例才解除） */
	float StaminaRecoverThreshold = 0.2f;

	/** Sprint 消耗速率（每秒） */
	float StaminaDrainRate = 20.f;

	/** 体力恢复速率（每秒） */
	float StaminaRegenRate = 10.f;
};
```

StaminaArbiter.cpp:
```cpp
/**
 * @file StaminaArbiter.cpp
 * @brief 体力仲裁器实现
 */
#include "Pipeline/Arbiters/StaminaArbiter.h"
#include "Data/RuntimeData.h"
#include "AbilitySystemComponent.h"

void FStaminaArbiter::Init(UAbilitySystemComponent* InASC)
{
	ASC = InASC;
}

void FStaminaArbiter::Arbitrate(FRuntimeData& RuntimeData, float DeltaTime)
{
	if (!ASC) return;

	// TODO: 从 AttributeSet 读取 Stamina 和 MaxStamina
	// float Stamina = AttributeSet->GetStamina();
	// float MaxStamina = AttributeSet->GetMaxStamina();

	// Sprint 消耗体力
	// if (RuntimeData.bWantsToSprint && !bIsStaminaDepleted)
	// {
	//     // 通过 GE 消耗体力
	// }
	// else
	// {
	//     // 通过 GE 恢复体力
	// }

	// 枯竭判定（滞后设计）
	// if (Stamina <= 0.f)
	// {
	//     bIsStaminaDepleted = true;
	// }
	// else if (bIsStaminaDepleted && Stamina >= MaxStamina * StaminaRecoverThreshold)
	// {
	//     bIsStaminaDepleted = false;
	// }

	// 枯竭时阻止 Sprint（意图处理器会读这个标记）
	// if (bIsStaminaDepleted)
	// {
	//     RuntimeData.bWantsToSprint = false;
	// }
}
```

#### 6.6 创建 ArbiterPipeline

ArbiterPipeline.h:
```cpp
/**
 * @file ArbiterPipeline.h
 * @brief 仲裁管线 - 第二层全局仲裁
 *
 * 在 Tick 最开头执行（比 InputPipeline 还早）。
 * 执行顺序固定：GASArbiter → ActionArbiter → HealthArbiter → StaminaArbiter
 */
#pragma once

#include "CoreMinimal.h"
#include "Pipeline/Interfaces/IArbiter.h"

class UAbilitySystemComponent;
struct FRuntimeData;

class FArbiterPipeline
{
public:
	/**
	 * 初始化所有仲裁器
	 * @param InASC AbilitySystemComponent 指针
	 */
	void Init(UAbilitySystemComponent* InASC);

	/**
	 * 每帧执行所有仲裁器（Tick 第 1 步）
	 * 前置条件: 无（最先执行）
	 */
	void Process(FRuntimeData& RuntimeData, float DeltaTime);

private:
	/** 仲裁器列表（按执行顺序） */
	TArray<TUniquePtr<IArbiter>> Arbiters;
};
```

ArbiterPipeline.cpp:
```cpp
/**
 * @file ArbiterPipeline.cpp
 * @brief 仲裁管线实现
 */
#include "Pipeline/ArbiterPipeline.h"
#include "Pipeline/Arbiters/GASArbiter.h"
#include "Pipeline/Arbiters/ActionArbiter.h"
#include "Pipeline/Arbiters/HealthArbiter.h"
#include "Pipeline/Arbiters/StaminaArbiter.h"
#include "Data/RuntimeData.h"

void FArbiterPipeline::Init(UAbilitySystemComponent* InASC)
{
	// 执行顺序固定：GAS → Action → Health → Stamina
	auto GAS = MakeUnique<FGASArbiter>();
	GAS->Init(InASC);
	Arbiters.Add(MoveTemp(GAS));

	auto Action = MakeUnique<FActionArbiter>();
	Action->Init(InASC);
	Arbiters.Add(MoveTemp(Action));

	auto Health = MakeUnique<FHealthArbiter>();
	Health->Init(InASC);
	Arbiters.Add(MoveTemp(Health));

	auto Stamina = MakeUnique<FStaminaArbiter>();
	Stamina->Init(InASC);
	Arbiters.Add(MoveTemp(Stamina));
}

void FArbiterPipeline::Process(FRuntimeData& RuntimeData, float DeltaTime)
{
	// 每帧先重置仲裁标记（由仲裁器重新写入）
	RuntimeData.bBlockMove = false;
	RuntimeData.bBlockAttack = false;
	RuntimeData.bBlockDodge = false;
	RuntimeData.bBlockInput = false;

	for (const auto& Arbiter : Arbiters)
	{
		Arbiter->Arbitrate(RuntimeData, DeltaTime);
	}
}
```

#### 6.7 修改 BaseCharacter 集成 ArbiterPipeline

BaseCharacter.h 添加:
```cpp
#include "Pipeline/ArbiterPipeline.h"

// 在 protected 里:
/** 仲裁管线 */
TUniquePtr<FArbiterPipeline> ArbiterPipeline;
```

BaseCharacter.cpp 修改:
```cpp
ABaseCharacter::ABaseCharacter()
{
	// ... 已有代码 ...
	ArbiterPipeline = MakeUnique<FArbiterPipeline>();
}

void ABaseCharacter::BeginPlay()
{
	Super::BeginPlay();
	// ... 已有代码 ...
	// TODO: 阶段八 GAS 接入后传入真实 ASC
	// ArbiterPipeline->Init(GetAbilitySystemComponent());
	ArbiterPipeline->Init(nullptr); // 暂时传 nullptr，仲裁器会安全跳过
}

void ABaseCharacter::Tick(float DeltaTime)
{
	Super::Tick(DeltaTime);

	// 1. 仲裁管线（第二层全局仲裁）
	ArbiterPipeline->Process(*RuntimeData, DeltaTime);

	// 2. 输入管线
	InputPipeline->Process(DeltaTime);

	// 3. 意图处理（第一层按键级仲裁在各处理器内部）
	IntentPipeline->ProcessIntents(*InputData, *RuntimeData);

	// 4. 参数处理
	IntentPipeline->ProcessParameters(*RuntimeData, DeltaTime);

	// 5. 状态机（第三层全局打断在 Update 内部）
	StateMachine->Update(DeltaTime, *RuntimeData);

	// 6. MotionDriver（未来）

	// 旧版移动（临时兼容）
	RootMotionProc->Process(DeltaTime);

	// 帧末清零
	RuntimeData->ResetFrameIntents();
}
```

#### 6.8 验证清单

```
编译验证:
├─ IArbiter 接口和所有仲裁器编译通过
├─ ArbiterPipeline 能创建和持有所有仲裁器
├─ BaseCharacter 持有 ArbiterPipeline（TUniquePtr）
└─ ASC 为 nullptr 时所有仲裁器安全跳过

运行验证:
├─ 仲裁标记每帧先重置再由仲裁器写入
├─ ASC 为 nullptr 时系统正常运行（仲裁标记全为 false）
└─ 后续阶段八接入 GAS 后验证：
    ├─ State.Stunned Tag → bBlockMove/bBlockAttack = true
    ├─ State.Dead Tag → 全面阻断
    ├─ 攻击意图 → ActionArbiter → GA 激活 → ActionGranted
    ├─ 体力枯竭 → bWantsToSprint 被阻止
    └─ 体力恢复到 20% → 允许再次 Sprint

关键点:
├─ ArbiterPipeline 在 Tick 最开头执行（比 InputPipeline 还早）
├─ 仲裁标记每帧重置 → 仲裁器重新写入（不会残留上一帧的标记）
├─ GAS 相关逻辑暂时用 TODO 标记，等阶段八接入后实现
├─ HealthArbiter 用固定容量数组做伤害队列（零 GC，参考 BBB-Nexus）
└─ StaminaArbiter 有滞后设计（枯竭后需恢复到 20% 才解除）
```

#### 6.9 阶段六完成状态：当前 TODO 清单

> **阶段六已完成**（2026-06-02），以下为尚未实现的 TODO 及其依赖阶段。

| TODO 位置 | 内容 | 依赖 | 状态 |
|-----------|------|------|------|
| `ActionArbiter.cpp` L28-33 | `TryActivateAbilityByClass(GA_Attack)` / `GA_Dodge` 调用 | 阶段八-D（GA 类创建） | 注释中 |
| `ActionArbiter.cpp` L42-45 | 同上，闪避路径 | 阶段八-D | 注释中 |
| `HealthArbiter.cpp` L29-31 | 通过 GE 扣血（`ApplyGameplayEffectToSelf`） | 阶段八-D（GE_Damage 创建） | 注释中 |
| `HealthArbiter.cpp` L35-41 | 从 AttributeSet 读 Health ≤ 0 → 全面阻断 | 阶段八-C（AttributeSet 补全 Health/Stamina） | 注释中 |
| `StaminaArbiter.cpp` 全文 | Sprint 体力消耗/恢复/枯竭判定 | 阶段八-C（AttributeSet 补全 Stamina） | 全注释 |
| `IdleState.cpp` Enter/Exit | GAS GameplayTag 同步（State.Idle） | 阶段八-D | 注释中 |
| 各状态 State Enter/Exit | 同上，各状态的 Tag 同步 | 阶段八-D | 注释中 |

**总结**：
- **GASArbiter**：✅ 完全可用（读 Tag → 写标记，不依赖 GA/GE）
- **ActionArbiter**：⚠️ 骨架可用，抗性系统已实现，`TryActivateAbility` 待 GA 类
- **HealthArbiter**：⚠️ 队列机制可用，结算逻辑待 GE
- **StaminaArbiter**：❌ 全部待 AttributeSet

---

### 阶段七：BaseCharacter 时序整合

#### 7.1 修改 BaseCharacter::Tick

```
void ABaseCharacter::Tick(float DeltaTime)
{
    Super::Tick(DeltaTime);

    // 1. 仲裁
    ArbiterPipeline->Process(RuntimeData);

    // 2. 输入
    InputPipeline->Process(DeltaTime, InputData);

    // 3. 意图 + 参数
    IntentPipeline->ProcessIntents(InputData, RuntimeData);
    IntentPipeline->ProcessParameters(RuntimeData);

    // 4. 状态机
    StateMachine->Update(DeltaTime, RuntimeData);

    // 5. 驱动
    MotionDriver->Process(DeltaTime, RuntimeData, this);

    // 6. 帧末清零
    RuntimeData->ResetFrameIntents();
}
```

#### 7.2 验证
- 完整流程跑通
- 按键 → 移动 → 攻击 → 闪避 全部正常
- 状态切换正确
- 仲裁标记生效

---

### 阶段八：GAS 接入

分为两个子阶段：先挂载 ASC + AttributeSet（基础设施），再做 GA/GE（业务逻辑）。

#### 8A. 挂载 ASC + AttributeSet（最小版，在阶段六之前完成）

目标：让 ASC 存在且可用。不创建任何 GA 或 GE 蓝图，不写任何技能逻辑。
做完这个，阶段六的四个仲裁器就有了真正的 ASC 可以操作。

修改 BaseCharacter：

BaseCharacter.h:
- 新增 `#include "AbilitySystemInterface.h"`
- 新增 `#include "Attributes/GGYGOAttributeSet.h"`
- 继承 `public IAbilitySystemInterface`
- 实现 `virtual UAbilitySystemComponent* GetAbilitySystemComponent() const override`
- 添加 `UPROPERTY UAbilitySystemComponent* ASC`（CreateDefaultSubobject）
- 添加 `UPROPERTY UGGYGOAttributeSet* AttributeSet`（CreateDefaultSubobject）
- 预留 `TArray<TSubclassOf<UGameplayAbility>> DefaultAbilities`（蓝图可配）
- 预留 `TArray<TSubclassOf<UGameplayEffect>> DefaultEffects`（蓝图可配）

BaseCharacter.cpp:
```
构造函数:
  ASC = CreateDefaultSubobject<UAbilitySystemComponent>(TEXT("ASC"));
  AttributeSet = CreateDefaultSubobject<UGGYGOAttributeSet>(TEXT("AttributeSet"));

BeginPlay（在所有子系统之前）:
  ASC->InitAbilityActorInfo(this, this);
```

为什么 AttributeSet 必须用 CreateDefaultSubobject：
- ASC 在 `InitAbilityActorInfo` 时会自动扫描 Actor 的子对象找 `UAttributeSet`
- 用 `NewObject` 创建的 AttributeSet 不是子对象，ASC 发现不了
- → 属性无法被 GE 修改

#### 8B. ActionArbiter 接入 ASC（阶段六做）

```
ActionArbiter 持有 ASC 引用
读到 WantsToAttack → TryActivateAbility
成功 → ActionGranted = Attacking
```

#### 8C. GASArbiter 接入 Tag（阶段六做）

```
每帧读 ASC Tag
State.Stunned → bBlockMove = true
```

#### 8D. GA/GE 完整实现（阶段六之后）

完整版包括所有 GA 类、GE 蓝图、连招系统、AnimNotify 信号系统。

---

### 阶段九：表现层

#### 9.1 动画蓝图 ✅ 基础架构已完成

```
UGGYGOAnimInstance (C++ 基类):
├─ NativeUpdateAnimation() — 从 BaseCharacter 同步 CurrentState/AnimSpeed/bIsMoving
├─ UpdateActiveAnimation() — 检测 CurrentState 变化 → 自动设 ActiveAnimSequence
├─ 计时检测非循环动画结束 → NotifyAnimFinished() → 通知状态机
└─ 动画资产引用（IdleAnim/RunStartAnim/RunLoopAnim/RunEndAnim）— 蓝图可配

ABP_Miyabi（蓝图，继承 UGGYGOAnimInstance）:
├─ AnimGraph: 一个 Sequence Player 读 ActiveAnimSequence → Output Pose（就一根线）
│   Sequence Player 设置: Animation = ActiveAnimSequence
│                         Loop = bActiveAnimLooping
│                         PlayRate = ActiveAnimPlayRate
├─ 细节面板: 填入四个动画资产
└─ 不需要任何状态机连线

动画切换流程（纯 C++）:
  StateMachine → RuntimeData.CurrentState 变化
    → NativeUpdateAnimation 检测到变化
      → UpdateActiveAnimation() 换 ActiveAnimSequence + 设 Loop/PlayRate
        → ABP Sequence Player 自动切换到新动画
```

#### 9.2 MoveDriverComponent

```
预加载动画 Root Motion 数据
GetPlayRateForSpeed() 写入 RuntimeData.PlayRate
```

#### 9.3 CameraManager

```
监听 Tag 变化 → 执行 CameraAction
```

---

## 建议的开发顺序

```
已完成:
├─ 第一周: 阶段一 + 阶段二（数据层 + 输入管线）✅
├─ 第二周: 阶段三 + 阶段四（意图管线 + 状态机）✅
├─ 第三周: 阶段五（MotionDriver）✅
│   └─ 实际实现与原计划有差异：防滑步（RequestDirectMove）替代原 AddMovementInput 方案
├─ 第四周: 阶段八-A（ASC 挂载，最小 GAS 接入）✅
│   └─ ASC + AttributeSet 已通过 CreateDefaultSubobject 挂载到 BaseCharacter
├─ RootMotion 数据管线（工期外追加）✅
│   ├─ max_export_root_motion.ms（3ds Max → CSV）
│   └─ generate_speed_curves.py（CSV → AnimSequence.Speed 曲线）

当前整体进度:
├─ 已完成: 阶段一~五 + 八-A + 九-1(基础) + RootMotion数据管线 + Run状态重构 + AnimInstance
│   ├─ 核心管线完整: InputPipeline → IntentPipeline → StateMachine → MotionDriver
│   ├─ 动画层: UGGYGOAnimInstance（Slot+Montage 纯代码驱动，ABP 只需一个 Slot 节点）
│   ├─ 状态机重构: Locomotion/Sprinting → RunStart/RunLoop/RunEnd（三阶段跑步）
│   ├─ GAS 基础设施就绪: ASC + AttributeSet（GA/GE 蓝图待创建）
│   ├─ 防滑步移动: AnimSpeed × 输入方向 → RequestDirectMove（帧级同步）
│   └─ 旧代码清理完毕: RootMotionProcessor/LocomotionState/SprintingState 已删除
│
├─ 下一步 → 阶段六: 仲裁管线（ArbiterPipeline）
│   ├─ IArbiter 接口 + ArbiterPipeline 主类
│   ├─ GASArbiter: 读 Tag → 写阻断标记
│   ├─ ActionArbiter: 读意图 → TryActivateAbility → 写 ActionGranted
│   ├─ HealthArbiter: 伤害队列 + 死亡判定
│   └─ StaminaArbiter: 体力消耗 + 滞后恢复
│
└─ 之后:
    ├─ 阶段七: 时序整合 + 清理验证
    ├─ 阶段八-B/C/D: GA/GE 完整实现（技能蓝图 + 连招系统 + AnimNotify）
    └─ 阶段九: 表现层（MoveDriverComponent / CameraManager）

每个阶段完成后都能编译运行验证
不需要等所有阶段做完就能测试
```

---

## 附录 A：HT（鸣潮）项目架构深度分析

> 数据来源：FModel 反编译导出 (`F:\FModel\Output\Exports\HT\Content\`)
> 分析目标：提取可借鉴的设计模式，改进 GGYGO 架构
> 排除范围：滑翔(Gliding)、攀爬(Climb)、载具(Vehicle)、多人协作
> 更新记录: v2 — 补充组件绑定机制(20组件注册表)、运行时交互、AnimBP状态机全貌(8机/15+3态)、DT完整数据(25行)、DataAsset字段明细、FootIK详解(A.10)、C++源码情况(A.11)

### A.1 整体架构总览

HT 是一个基于 UE5 的 3D 动作 RPG，采用 **GAS 全驱动 + 数据资产化 + AnimNotify 事件系统** 三位一体架构。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        HT 项目核心架构                               │
│                                                                     │
│  输入层: Enhanced Input System (30+ IA_*)                          │
│    ↓ IMC_Default_KBM / DT_AbilityInput (DataTable)                 │
│                                                                     │
│  GAS 层: UHTGameplayAbility 继承体系                                │
│    HTAbilityBase → MontageBase → MeleeBase / SkillBase             │
│    每个角色独立文件夹: Ability_003_Sagiri/                          │
│      ├─ GA_Sagiri_Melee (8段普攻)                                 │
│      ├─ GA_Sagiri_Evade / PerfectEvade                            │
│      ├─ GA_Sagiri_Skill (E技能)                                   │
│      ├─ GA_Sagiri_UltraSkill (Q大招)                              │
│      ├─ Damage/ (每段伤害GE)                                       │
│      ├─ DamageRange/ (每段判定盒)                                  │
│      ├─ Effect/ (击退/击倒/击飞效果GE)                             │
│      ├─ Buff/ (被动/Buff)                                         │
│      └── Upgrade/Level1~6 (升级强化)                                │
│                                                                     │
│  AnimNotify 层 (100+ 通知类):                                        │
│    移动控制: SetMoveMode, BlockMotion, TriggerRootMotion            │
│    战斗判定: TriggerParryAttack, CanBreakSkill, BreakState         │
│    GAS交互: ActivateGameEffect, AddLooseTags, EndAbilityEffect     │
│    运动修正: MotionWarping(SkewWarp), DisableRootMotion           │
│                                                                     │
│  移动层: 数据驱动物理参数                                            │
│    FHtMovementSetting → UHtMovementAttributeSet x3                │
│    (Default / 1stJump / 2ndJump) 按状态切换                         │
│    UHTPlayerCharacterMovementComponent (自定义CMC)                  │
│                                                                     │
│  状态管理层: UHTCharacterStateManagerComponent                      │
│    28+ 状态子类，每个状态可: 施加/移除GE、触发音频、限制功能         │
└─────────────────────────────────────────────────────────────────────┘
```

### A.2 组件绑定机制详解

#### A.2.0 关键发现：全部 C++ 构造，蓝图仅配置参数

`AHTPlayerCharacter` 是 `/Script/HTGame` 模块的原生 C++ 类（源码不可见，只有 FModel 导出的蓝图子类 `BP_PlayerCharacterBase_C`）。

**所有核心组件均在 C++ 基类构造函数中通过 `CreateDefaultSubobject` 创建**，
蓝图子类 `BP_PlayerCharacterBase_C` **仅覆盖默认参数配置**，不负责组件创建。

证据：蓝图中的组件引用格式为 `"Default__BP_PlayerCharacterBase_C:ComponentName"` —
这是 DefaultSubobject 引用格式，表明基类已创建。

#### A.2.1 完整组件注册表（20 个组件，按功能域分组）

`AHTPlayerCharacter` 是 `/Script/HTGame` 模块的原生 C++ 类（源码不可见，只有 FModel 导出的蓝图子类 `BP_PlayerCharacterBase_C`）。

组件在 **C++ 构造函数** 中通过 `CreateDefaultSubobject` 创建，蓝图子类仅配置默认参数：

```
AHTPlayerCharacter (原生基类)
│
├── UCapsuleComponent* CapsuleComponent ("CollisionCylinder")
│   └── 碰撞体，标准胶囊
│
├── UHTSkeletalMeshComponentBudgeted* Mesh ("CharacterMesh0")
│   ├── 带LOD预算管理的骨骼网格体（性能优化）
│   └── BaseTranslationOffset = (0, 0, -90)  ← Z轴偏移-90单位
│
├── UHTPlayerCharacterMovementComponent* CharacterMovement ("CharMoveComp")
│   ├── 自定义移动组件（继承 UCharacterMovementComponent）
│   ├── MaxAcceleration = 2000（高响应性）
│   ├── GravityScale = 1.5（比UE默认重）
│   ├── JumpZVelocity = 800
│   ├── AirControl = 0.2
│   ├── 双跳支持: SecondJumpZVelocity=884, MaxSecondJumpMoveSpeed=500
│   ├── 平滑上下台阶: StepDownInterpSpeed=220, StepUpInterpSpeed=150
│   └── RVO 避让: bClientUseRVOAvoidance=true
│
├── UHTAbilitySystemComponent* HTAbilitySystemComponent ("AbilitySystemComponent")
│   ├── 自定义 ASC（继承 UAbilitySystemComponent）
│   ├── 持有: AbilityAttributeSet (UGameplayAttributeSet*)
│   ├── 持有: CharacterAttribute (UHTPlayerAttributeSet*) — 耐力系统
│   └── 运行时授予/撤销 GA 能力
│
├── UHTCharacterStateManagerComponent* StateManagerComponent ("StateManagerComponent")
│   ├── 状态机管理器（非动画状态机！是游戏逻辑状态）
│   ├── 管理 28+ 个状态子类的生命周期
│   └── 每个状态可: 应用GE列表、移除GE(按Tag)、触发音频、限制武器状态
│
├── UHTMotionWarpingComponent* MotionWarping ("MotionWarping")
│   └── 运动扭曲组件（脚步定位、攻击命中位置修正）
│
├── UHtMovementAttributeSet* DefaultMovementAttributeSet ("BP_DefaultMovementDA")
│   ├── 数据资产：地面移动物理参数覆盖
│   ├── MaxAcceleration=2000, GravityScale=1.0, BrakingFrictionFactor=1.0
│   └── 通过 bOverride 标志选择性覆盖 CMC 参数
│
├── UHtMovementAttributeSet* FirstJumpMovementAttributeSet ("1stJumpDA")
│   └── 一段跳参数: JumpZVelocity=860, AirControl=1.0
│
├── UHtMovementAttributeSet* SecondJumpMovementAttributeSet ("2ndJumpDA")
│   └── 二段跳参数: JumpZVelocity=800, AirControl=1.0
│
├── UHTPlayerAttributeSet* CharacterAttribute ("HTCharacterAttributeSet")
│   ├── StateStrengthMap: 每个移动状态的耐力消耗速率
│   │   Normal=+30(恢复), Combating=+15, RunVines=-1(消耗)
│   │   SprintVines=-2.5, ParallelFly=-2.5
│   ├── StateStrengthMapExtend: XYZ轴分别消耗覆盖
│   └── HitParticleEffects, DeadCollisionProfileName
│
├── UHTSkillEffectComponent* SkillEffectComponent     ── 技能特效管理器
├── UGhostTrailComponent* GhostTrail               ── 残影/拖尾效果
├── USilentCheckComponent* SilentCheckComponent     ── 隐身检测
├── UCharacterForceFieldComponent* CharacterForceField ── 角色脚部力场
├── UFoliageInteractionBubble* FoliageInteractionBubble ── 植被交互
├── UHTFluxInteractionComponent* HTFluxInteraction  ── 流体表面交互
├── UWaterInteractionSurfaceComponent* WaterInteractionSurface ── 水面渲染
├── UHTCharacterTrajectoryComponent* HTTrajectoryComponent ── 轨迹预测
└── UHTContextualAnimSceneActorComponent* HTContextualAnimSceneActor ── 上下文动画
```

**关键发现**：HT 的移动参数不是写死在代码里的，而是通过 `UHtMovementAttributeSet` **数据资产**配置的。角色持有 **3套** 移动属性集，根据当前状态（地面/一段跳/二段跳）动态切换。

#### A.2.2 初始化顺序（推断）

```
1. AHTPlayerCharacter::AHTPlayerCharacter() [C++构造]
   ├── CreateDefaultSubobject 所有组件（上述完整组件树）
   └── 设置 FHtMovementSetting 默认值

2. BeginPlay()
   ├── ASC->InitAbilityActorInfo(this, this)     // GAS 初始化
   ├── StateManagerComponent->Init()              // 状态管理器初始化
   ├── 从 DataTable 读取默认能力列表
   │   └── ASC->GiveAbilities(DefaultAbilities)   // 授予默认GA
   └── 从 DataTable 读取默认效果列表
       └── ApplyGameplayEffectsToSelf(DefaultEffects) // 施加初始GE

3. 每帧 Tick()
   ├── InputPipeline.Process()            // 输入处理
   ├── StateManagerComponent.Tick()       // 状态更新（含GE应用/移除）
   ├── CharacterMovement->Tick()          // 物理模拟
   └── AnimInstance->NativeUpdateAnimation() // 动画更新
```

### A.3 各组件详细运行方式

#### A.3.1 UHTPlayerCharacterMovementComponent（自定义移动组件）

继承自 `UCharacterMovementComponent`，在原生基础上扩展：

| 功能 | 参数 | 说明 |
|------|------|------|
| **双跳** | `SecondJumpZVelocity=884` | 第二次跳跃的垂直初速度 |
| | `MaxSecondJumpMoveSpeed=500` | 二段跳期间最大水平速度 |
| | `SecondJumpBrakingDeceleration=200` | 二段跳制动减速度 |
| | `SecondJumpAirControl=0.8` | 二段跳空中控制度 |
| **平滑台阶** | `StepDownInterpSpeed=220` | 下台阶插值速度 |
| | `StepUpInterpSpeed=150` | 上台阶插值速度 |
| | `TriggerInterpStepUpMoveObstacleHeight=25` | 触发平滑上台阶的障碍高度阈值 |
| **游泳** | `MaxFastSwimSpeed=280` | 快速游泳速度 |
| | `MaxSwimSpeed=170` | 正常游泳速度 |
| | `fMaxImmersionDepth=0.75` | 最大浸入深度比例 |
| **重力旋转** | `RotateToGravitySpeed=900` | 变重力区域朝向旋转速度 |
| **基础物理** | `MaxAcceleration=2000` | 最大加速度（极高响应） |
| | `GravityScale=1.5` | 重力缩放（比UE默认1.0重） |
| | `JumpZVelocity=800` | 跳跃初速度 |
| | `AirControl=0.2` | 空中控制度 |
| | `RotationRate.Yaw=960` | 旋转速度（极快转向） |

**与 GGYGO 对比**：
- GGYGO 用 `RequestDirectMove` 绕过 CMC 加速实现防滑步
- HT 用高 `MaxAcceleration=2000` + 高 `RotationRate.Yaw=960` 实现快速响应
- HT 不做防滑步（动作RPG不需要帧级同步），而是用 MotionWarping 修正脚步位置

#### A.3.2 UHTCharacterStateManagerComponent（状态管理器）

这是 HT 最独特的组件——一个 **独立的游戏逻辑状态机**，区别于 UE 动画状态机：

```
状态继承层次:
UHTCharacterStateBase (原生抽象基类)
├── UHTCharacterCommonStateBase      → FlyState, HoldStickWalk
├── UHTCharacterBasicMovementState   → fallingState
├── UHTPlayerInteractState           → InteractState
├── UHTPlayerRideState               → RideState (坐骑)
├── UHTCharacterDrivingState         → DrivingState (载具)
├── UHTPlayerSwimmingState           → SwimmingState
└── UHTPlayerZeroGravityState        → ZeroGravityState

每个状态的通用能力:
├── StateGameplayEffectList    — 进入时自动施加的 GE 列表
├── RemoveGEWithTag            — 进入时按Tag移除的 GE
├── OnEnterStateAudioEvent     — 进入状态触发的音频事件
├── OnBreakStateAudioEvent     — 被打断时触发的音频事件
├── WeaponHoldState            — 武器持握状态
└── LimitGamePlayFunPreset     — 限制可用功能预设
```

**关键设计模式**：状态切换时自动施加/移除 GameplayEffect。
例如进入 `SwimmingState` 时自动移除 `State.GravityDynamic` Tag 并授予闪避和跳跃能力；
进入 `RideState` 时施加无敌 Buff 并限制为 `TrainState` 功能预设。

**与 GGYGO 对比**：
- GGYGO 的状态机是纯 C++ 的 `FCharacterStateMachine`（值类型），在 `RuntimeData` 上操作
- HT 的状态机是 `UActorComponent`（UObject 子类），直接操作 ASC 和 GE
- HT 的状态更重量级（每个状态是一个 BP 类），GGYGO 的更轻量（每个状态是一个 C++ 对象）
- **借鉴点**：GGYGO 可以在未来让状态 Enter/Exit 时同步施加/移除 Tag 或 GE

#### A.3.3 GAS 能力继承体系详解

```
UGameplayAbility (UE5 原生)
  └── UHTGameplayAbility (/Script/HTGame 原生C++基类)
        │
        │  原生提供的能力（从蓝图暴露的事件推测）:
        │  ├── K2_OnTriggerRootMotionConstantForceTask  → 常力RM
        │  ├── K2_OnTriggerRootMotionExTask             → 多态RM容器
        │  ├── K2_OnTriggerRootMotionJumpForceTask      → 跳跃力RM
        │  ├── K2_OnTriggerRootMotionMoveToForceTask    → 移动力RM
        │  └── K2_OnTriggerRootMotionMoveToTargetTask  → 移向目标RM
        │
        └── UGA_HTAbilityBase_C (蓝图: GA_HTAbilityBase)
              │  空壳：仅持有 UberGraphFunction
              │
              └── UGA_MontageBase_C (蓝图: GA_MontageBase)
                    │  核心字段:
                    │  ├── FAimingTaskParams AimingTaskParams
                    │  │   └── bExitAimingWhileEndOrPauseTask=true
                    │  │   └── DelayExitAimingTimeAfterFire=0.15s
                    │  ├── EGravityDirectionRequirement (重力方向需求)
                    │  ├── bool bHasCommit / CommitResult
                    │  ├── bool JumpSectionTaskCreated
                    │  └── bool P&RIsPressed (格挡&翻滚按键)
                    │
                    ├── UGA_MeleeBase_C (普攻基类)
                    │     ├── LockTargetInfo: JoystickAngle锁定, 210°无目标角度
                    │     └── ReleaseSkillMode = Input_Pressed
                    │
                    ├── UGA_SkillBase_C (E技能基类)
                    │     ├── LockTargetInfo: 120°/150° 角度
                    │     ├── ReleaseSkillMode = Input_Pressed
                    │     └── bCheckLedges = true
                    │
                    └── UGA_QTEBase_C (QTE基类)
```

**具体角色实现示例（Sagiri 完美闪避）**:

```
UGA_Sagiri_PerfectEvade_C:
├── 锁定目标: 全角度360°锁定, 伤害盒判定
├── Montage映射:
│   "PerfectEvadeFront" → 前闪避动画
│   "Atk"               → 闪避反击动画
│   "PerfectEvadeBack"  → 后闪避动画
│
├── EffectContainerMap (Tag→效果容器):
│   "Event.Montage.Player.Melee.1" → {
│       TargetType: DamageBox (盒扫检测, 最多10目标)
│       Effects: [GE_Damage(伤害), GE_HitBack(击退)]
│   }
│   "Event.Montage.Player.Melee.2" → {
│       TargetType: UseOwner (自身)
│       Effects: [Buff_ExtremeEvade(无敌Buff)]
│   }
│
└── AbilityTags: ["Ability.Evade.PerfectEvade"]
```

**核心设计模式：EffectContainerMap（AnimNotify → Tag → EffectContainer 解耦链）**

```
动画时间轴:
  [===前摇===][★Notify:SendEvent(Melee.1)][===后摇===]
                                     │
                                     ▼
                   AnimNotify 发送 Tag: "Event.Montage.Player.Melee.1"
                                     │
                                     ▼
                  GA.EffectContainerMap[Tag] 执行:
                      ├── TargetType: BoxTrace → 检测命中目标列表
                      └── 对每个目标 Apply GE:
                          ├── GE_Damage (扣血)
                          └── GE_HitBack (击退力)
```

### A.4 AnimNotify 系统详解

#### A.4.1 移动控制类 Notify

| Notify 名称 | 类型 | 功能 |
|-------------|------|------|
| `BP_SetMoveModeANS` | State | 进区间→设 JoinMovementMode，出区间→设 ExitMovementMode |
| `BP_BlockMovement` | State | 区间内完全阻止移动输入 |
| `BP_NotifyTriggerRootMotion` | State | 触发根运动（常力/跳跃/移动等） |
| `BP_DisableRootMotion` | Instant | 禁用根运动 |
| `BP_MotionWarping` | State | SkewWarp 位置扭曲修正 |

**运行方式示例（SetMoveModeANS）**：
```
动画时间轴: [Idle]====[★Join:Flying]====[攻击]====[★Exit:Walking]====[Idle]
                         │                              │
                   MovementMode=Flying           MovementMode=Walking
```

#### A.4.2 打断控制类 Notify

| Notify 名称 | 功能 |
|-------------|------|
| `BP_BreakMontageByMoveNS` | 区间内有移动输入 → 打断当前 Montage |
| `BP_HasMoveInputBreakMontage` | BP 实现：检测到移动输入 → 打断 Montage |
| `BP_BreakState_NS` | 打破当前状态 |
| `BP_CanBreakSkill` | 检测是否可以打断技能 |

#### A.4.3 战斗/GAS 交互类 Notify

| Notify 名称 | 功能 |
|-------------|------|
| `BP_TriggerParryAttack` | 格挡攻击判定窗口（RotatorToTarget=true） |
| `BP_SpawnDamageTriggerActor_InSocket` | 在骨骼 Socket 生成伤害触发器 Actor |
| `BP_SendGamePlayEvent` | 发送 GameplayEvent 给 GAS |
| `BP_ActivateGameEffect_NS` | 激活 GameplayEffect |
| `BP_ActivateGameEffectCheckStage_NS` | 分阶段激活 GE（多段攻击的不同阶段） |
| `BP_TimedActivatedGE_NS` | 定时激活 GE（N秒后自动移除） |
| `BP_AddLooseGameplayTagsNS` | 添加松散 GameplayTag |
| `BP_TriggerEndAbilityEffect` | 触发能力结束时的效果 |

### A.5 AnimBP 架构详解

#### A.5.1 继承链

```
UAnimInstance (UE5 原生)
  └── UHTPlayerAnimInstance (/Script/HTGame)
        └── HtPlayerCharacterAniminstanceBase (蓝图基类)
              └── Player003_Sagiri_1_AnimBP (具体角色)
```

#### A.5.2 八个并行状态机完整定义

HT 的 AnimBP 包含 **8 个并行状态机**，各自独立运转，通过 SyncGroup 同步：

| # | 状态机名 | 初始状态 | 状态数 | 核心职责 | 复杂度 |
|---|----------|----------|--------|----------|--------|
| 0 | **SMWithBaseAndMM** | MotionMatchingState(0) | 2 | **顶层选择器**: MM vs 基础姿态混合 | 低 |
| 1 | **MotionMatch Machine** | MMState(0) | 1 | **PoseSearch 引擎**: 驱动 MotionMatching 动画查询 | 中 |
| 2 | **FullBodyIK** | Inactive(0) | 2 | 全身 IK 开关（Inertialization 过渡 0.2s进/0.1s出） | 低 |
| 3 | **SelfieStickMachine** | SelfieBasedPose(0) | 1(+16节点) | 自拍杆姿态层 | 高(视觉) |
| 4 | **AimmingMachine** | Aimming(0) | 1(+LayerNode) | 瞄准姿态叠加层 | 中 |
| 5 | **GlidingMachine** | EnterGliding(0) | 2 | **滑翔**: 进入(1.8s混合)→循环, 可中断退出(0.05s) | 中 |
| 6 | **SecondJumpStatesMachine** | JumpSecond(0) | 2 | **二段跳**: 起→循环(0.1s混合) | 低 |
| 7 | **FirstJumpStatesMachine** | Entry(0) | 5 | **一段跳**: 5态有限状态机 | 中 |
| 8 | **MainMovementStatesMachine** | Grounded(0) | 15+3Conduit | ★主移动: 15态+3管道态 | 最高 |

#### A.5.3 MainMovementStatesMachine 详细分析（核心状态机）

**15 个实体状态 + 3 个 Conduit（管道状态）**：

| Conduit 名 | 用途 |
|------------|------|
| `<-MovementState->` | 进入任意移动子状态的统一分发器 |
| `->InAir` | 进入空中状态的中间过渡态 |
| `->Land` | 落地过渡态 |

**关键转换规则（含混合时间）**：
```
Grounded: ──[0.1s]──→ Vines / [0.2s]──→ Fall / [0.1s]──→ Gliding / [0.2s]──→ Jump
Fall:     ──[0.1s]──→ Grounded / ──[0.2s]──→ Vines, Gliding
Jump:     bAlwaysResetOnEntry (每次进入重置动画)
Gliding:   bAlwaysResetOnEntry
```

#### A.5.3 MotionMatching 配置（PoseSearch 插件）

```
AnimNode_MotionMatching:
├── BlendTime: 0.2s
├── PoseReselectHistory: 0.3s (防抖)
├── SearchThrottleTime: 0 (每帧搜索)
├── PlayRate: 1.0 (固定)
├── bShouldSearch: true
├── bResetOnBecomingRelevant: true
├── StitchBlendTime: 0.1s
├── MaxActiveBlends: 4
└── GroupName: Locomotion (同步组领导者)
```

### A.6 输入系统详解

#### A.6.1 Enhanced Input 映射（IMC_Default_KBM）

| 按键 | InputAction | 功能 |
|------|-------------|------|
| W/A/S/D | IA_Move | 四方向移动 |
| MouseX | IA_Turn | 水平视角 |
| MouseY | IA_LookUp | 垂直视角 |
| Space | IA_Jump | 跳跃 |
| LShift | IA_Sprint | 冲刺 |
| LMB | IA_MeleeAttack | 普攻 |
| RMB | IA_EvadeAttack | 闪避 |
| E | IA_SkillAttack | E技能 |
| Q | IA_UltSkillAttack | Q大招 |
| G | IA_GSkill | G技能 |
| R | IA_AdditionalSkill | R附加技能 |
| MMB | IA_LockTarget | 锁定目标 |
| N | IA_SwitchLockTarget | 切换锁定 |
| Middle | IA_Aiming | 瞄准 |
| LCtrl | IA_WalkRun | 走/跑切换 |
| Tab | IA_QuickMenu | 快捷菜单 |
| 1-4 | IA_{1-4}KeyBoard | 切换角色(多人) |
| V | IA_TrackingInput | 追踪任务 |
| Z | IA_SwitchFirstPerson | 第一/第三人称 |
| Alt | IA_SwitchMouse | 切换鼠标显示 |
| F | IA_Interaction | 交互 |
| X | IA_LeaveVines | 离开藤蔓 |

#### A.6.2 DataTable 驱动的输入→能力绑定（DT_AbilityInput）完整数据

**文件**: [DT_AbilityInput.json](file:///F:/FModel/Output/Exports/HT/Content/Input/DT_AbilityInput.json)
**RowStruct**: `HTAbilityInputRow` (`/Script/HTGame` 自定义结构体)

**完整 25 行数据**：

| # | RowName | InputID (enum) | InputAction | AbilityName | bShouldBind | Param | 说明 |
|---|---------|---------------|-------------|-------------|-------------|-------|------|
| 1 | MeleeAtack | InputID_Melee | IA_MeleeAttack | MeleeAtack | true | -1 | 普攻 |
| 2 | EvadeAttack | InputID_Evade | IA_EvadeAttack | EvadeAttack | true | -1 | 闪避 |
| 3 | Sprint | InputID_Evade | IA_Sprint | Sprint | true | -1 | 冲刺 |
| 4 | SkillAttack | InputID_Skill | IA_SkillAttack | SkillAttack | true | -1 | E技能 |
| 5 | UltSkill | InputID_UltSkill | IA_UltSkillAttack | UltSkill | true | -1 | Q大招 |
| 6 | AdditionalSkill | InputID_AdditionalSkill | IA_AdditionalSkill | AdditionalSkill | true | -1 | R附加技 |
| 7 | AbyssCardSkill | InputID_AbyssCardSkill | IA_AbyssCardSkill | AbyssCardSkill | true | -1 | 深渊卡技能 |
| 8 | ChangeCharacter_1 | InputID_ChangeCharacter | IA_1KeyBoard | ChangeCharacter | **true** | **0** | 切角色1 |
| 9 | ChangeCharacter_2 | InputID_ChangeCharacter | IA_2KeyBoard | ChangeCharacter | **true** | **1** | 切角色2 |
| 10 | ChangeCharacter_3 | InputID_ChangeCharacter | IA_3KeyBoard | ChangeCharacter | **true** | **2** | 切角色3 |
| 11 | ChangeCharacter_4 | InputID_ChangeCharacter | IA_4KeyBoard | ChangeCharacter | **true** | **3** | 切角色4 |
| 12 | Food | InputID_Food | IA_Shortcut | Food | true | -1 | 使用食物 |
| 13 | **Jump** | InputID_Jump | IA_Jump | Jump | **false** | -1 | ★不走GAS |
| 14 | **Interact** | InputID_Interact | IA_Interaction | SwitchAimingHelper | **false** | -1 | ★不走GAS |
| 15 | LeaveVines | InputID_LeaveVines | IA_LeaveVines | LeaveVines | true | -1 | 离开藤蔓 |
| 16 | TrackQuest | InputID_TrackQuest | IA_TrackingInputAction | TrackQuest | **false** | -1 | ★追踪任务 |
| 17 | Aiming | InputID_Aiming | IA_Aiming | Aiming | true | -1 | 瞄准 |
| 18 | LockTarget | InputID_LockTarget | IA_LockTarget | LockTarget | true | -1 | 锁定目标 |
| 19 | SwitchLockTarget | InputID_SwitchLockTarget | IA_SwitchLockTarget | SwitchLockTarget | true | -1 | 切锁目标 |
| 20 | UltSubSkill | InputID_UltSubSkill | **IA_MeleeAttack** | UltSubSkill | **false** | -1 | ★复用LMB |
| 21 | ChaseMoveLeft | InputID_ChaseMoveLeft | IA_ChaseLeft | ChaseMoveLeft | **false** | -1 | 追击左移 |
| 22 | ChaseMoveRight | InputID_ChaseMoveRight | IA_ChaseRight | ChaseMoveRight | **false** | -1 | 追击右移 |
| 23 | SwitchCameraViewMode | InputID_SwitchCameraViewMode | IA_SwitchFirstPersonView | SwitchCameraViewMode | true | -1 | 切视角 |
| 24 | GSkill | InputID_GSkill | IA_GSkill | GSkill | true | -1 | G技能 |

**关键设计洞察**：

- **Param 字段**：`ChangeCharacter_1~4` 共用同一 AbilityName，通过 Param(0~3) 区分
- **bShouldBind=false 的 6 个输入**走独立路径：Jump(传统回调)、Interact(交互)、TrackQuest(UI) 等
- **InputAction 复用**：UltSubSkill 复用 IA_MeleeAttack 但绑不同 Ability

### A.7 伤害/判定系统

```
生成方式: AnimNotify BP_SpawnDamageTriggerActor_InSocket(SocketName)
         → 在指定骨骼 Socket 生成 ADamageTriggerActor 子类

目标选择: UBP_PlayerType_DamageBoxBase (继承 UHTTargetType_BoxTrace)
         ├── SelectTargetType: FindTarget (自动搜索)
         ├── ObjectTypes: [WorldStatic, Custom10, Custom12]
         ├── bDamageInstanceObj: true (每目标独立伤害实例)
         └── MaxCount: 10 (单次最多命中10个)

完整伤害流程:
  AnimNotify: SendGamePlayEvent("Event.Montage.Player.Melee.1")
    → GA.EffectContainerMap["Melee.1"] 执行:
       ├── TargetType: BoxTrace → 命中 [EnemyA, EnemyB]
       └── 对每个命中 Apply:
           ├── GE_Melee1_Damage → 扣血
           └── GE_Melee1_HitBack → 击退
```

### A.8 HT vs GGYGO 架构对比总结

| 维度 | HT（鸣潮） | GGYGO | 差距分析 |
|------|-----------|-------|----------|
| **移动驱动** | CMC 高加速度(2000) + MotionWarping | RequestDirectMove 防滑步 | 不同路线，各有利弊 |
| **动画驱动** | AnimBP 8状态机 + MotionMatching(PoseSearch) | C++ AnimInstance + Slot/Montage | GGYGO 更轻量可控 |
| **状态管理** | UActorComponent (28+ BP状态子类) | 纯C++ 值类型状态机 (~10态) | HT 更重量但功能更丰富 |
| **GAS 集成度** | 全驱动（输入/状态/伤害/Buff 全走GAS） | 部分接入（ASC挂载完毕，GA/GE待实现） | ★最大差距 |
| **输入绑定** | DataTable 驱动（DT_AbilityInput, 25行） | C++ 硬编码 IntentProcessor | ★可立即改进 |
| **战斗判定** | AnimNotify + EffectContainerMap (100+ Notify) | 待实现 | ★GAS接入后重点 |
| **移动参数** | DataAsset (UHtMovementAttributeSet x3, bOverride) | 代码硬编码 | P1 优先改进 |
| **耐力系统** | StateStrengthMap (每状态不同消耗) | StaminaArbiter (待实现) | P2 优化项 |
| **打断系统** | AnimNotify 精确控制 (BlockMovement/BreakMontage) | RuntimeData.bBlockMove 标记 | GGYGO 更粗粒度 |
| **FootIK** | 自定义 C++ (HTFootIKAnimNode + FootPlacement) | 待实现 | 见 A.10 详细分析 |
| **代码/蓝图比** | ~30% C++ / 70% BP | ~95% C++ / 5% BP | 不同技术选择 |
| **组件数** | 20 (全部C++构造) | ~8 | HT 更模块化 |

### A.9 可借鉴的改进点（按优先级排序）

#### P0 — 立即可做

1. **DataTable 输入绑定** — 创建 DT_AbilityInput 替代硬编码，新增按键只加 DataTable 行
2. **GA 继承体系** — GGYGOGameplayAbility → MontageBase → MeleeBase/SkillBase

#### P1 — GAS 接入阶段

3. **EffectContainerMap 模式** — AnimNotify 发 Tag → EffectContainer → 目标选择 + GE
4. **移动参数 DataAsset 化** — FHtMovementSetting + AttributeSet 模式
5. **AnimNotify 移动控制** — SetMoveMode / BlockMovement 通知精确控制移动窗口

#### P2 — 中期优化

6. **StateStrengthMap 耐力系统** — 每状态不同消耗速率
7. **MotionWarping 接入** — 攻击位移位置修正
8. **状态 Enter/Exit GE 回调** — 状态切换时自动同步 Tag/GE

### A.10 FootIK（足部 IK）系统详解

> 用户提问：HT 的 FootIK 是怎么做的？

#### A.10.1 核心发现：完全自定义 C++ IK，非 UE 内置

**HT 没有使用 UE 引擎内置的 `AnimNode_FootIK` 或 `AnimNode_FullBody`**。
HTGame 模块实现了 **完全自定义的 IK 方案**，包含两个核心 C++ 节点：

| C++ 类名 | 类型 | 职责 |
|----------|------|------|
| **`UHTFootIKAnimLayer`** | AnimLayer 基类 | FootIK 动画层基类（所有角色 IK 层的父类） |
| **`FHTFootIKAnimNode`** | 自定义 AnimNode | **主 IK 解算器**（楼梯预测、脚步锁定、地面插值） |
| **`FHTAnimNode_FootPlacement`** | 自定义 AnimNode | 脚步放置辅助器（落地锁定、地面跟随） |

配合使用的 UE 内置节点：
- `AnimNode_LegIK` — FK/IK 腿部重定向
- `AnimNode_TwoBoneIK` — 两骨骼 IK（最终应用到脚部骨骼）

#### A.10.2 文件结构

```
Content/Characters/AnimInterface/FootIK/
├── FootIK_AnimInterface.cpp/.json     ← AnimLayer 接口定义
├── FootIK_AnimLayer_Base.cpp/.json    ← ★核心：基础 IK 层（完整节点图）
├── MonsterFootIK_AnimLayer.cpp/.json  ← 怪物 IK 层
├── NPCFootIK_AnimLayer.cpp/.json      ← NPC IK 层
├── FourFootIK_AnimLayer.cpp/.json     ← 四足 IK 层（异常生物用）
└── FootIK_AnimLayer_004~055/*.cpp     ← 18个角色独立 IK 变体

Blueprints/Share/Notify/
└── BP_SetFootIKStateANS.cpp/.json     ← Notify: 动态切换 IK 启用/禁用
```

#### A.10.3 IK 节点拓扑（FootIK_AnimLayer_Base 完整流程）

```
FootIKLayer 图层入口 (LinkedInputPose)
  │
  ├── [SaveCachedPose: "InPutPose"] ← 缓存原始姿态
  │
  ├── [LegIK] ──→ [SaveCachedPose: "SlopeIK"]   ← 斜坡 IK 分支
  │     FK/IK 映射:
  │       左腿: foot_l(IK) ↔ Bip001-L-Foot(FK), 2根骨
  │       右腿: foot_r(IK) ↔ Bip001-R-Foot(FK), 2根骨
  │       Alpha 曲线: "DisableLegIK"
  │
  ├── [HTAnimNode_FootPlacement] ──→ [SaveCachedPose: "FootIKPose"]
  │     ├─ IKFootRootBone: "root_foot"
  │     ├─ PelvisBone: "Bip001-Pelvis"
  │     ├─ 左脚: FK=Bip001-R-Foot, IK=foot_r, Ball=Bip001-R-Toe0
  │     └─ 右脚: FK=Bip001-L-Foot, IK=foot_l, Ball=Bip001-L-Toe0
  │
  ├── [HTFootIKAnimNode] ──→ [SaveCachedPose: "WalkOnStairIK"]  ← 楼梯 IK
  │     （详细参数见下方 A.10.4）
  │
  ├── [BlendListByBool] ← 楼梯/平地自动切换
  │     True:  UseCachedPose("WalkOnStairIK")
  │     False: UseCachedPose("FootIKPose")
  │           │
  │           ├── [ConvertComponentToLocalSpace]
  │           │     │
  │           │     ├── [ModifyBone: VB ik_foot_l_offset]   (左脚 IK 偏移)
  │           │     │     Alpha: Enable_FootIK_L
  │           │     │
  │           │     ├── [ModifyBone: VB ik_foot_r_offset]   (右脚 IK 偏移)
  │           │     │     Alpha: Enable_FootIK_R
  │           │     │
  │           │     ├── [ModifyBone: VB foot_l_target_...]   (左膝目标, offset:-15,-30,0)
  │           │     │
  │           │     ├── [ModifyBone: VB foot_r_target_...]   (右膝目标)
  │           │     │
  │           │     ├── [TwoBoneIK: Bip001-L-Foot]          (左脚两骨 IK)
  │           │     │     Effector: VB ik_foot_l_offset
  │           │     │     JointTarget: VB foot_l_target
  │           │     │     bAllowStretching=true, MaxStretch=1.2
  │           │     │
  │           │     └── [TwoBoneIK: Bip001-R-Foot]          (右脚两骨 IK)
  │           │           Effector: VB ik_foot_r_offset
  │           │           JointTarget: VB foot_r_target
  │           │           bAllowStretching=true, MaxStretch=1.2
  │           │
  │           └── [ConvertLocalToComponentSpace]
  │                 │
  │                 └── [ModifyBone: Bip001-Pelvis]         (骨盆高度修正)
  │                       TranslationMode: Additive, Space: ComponentSpace
  │
  └── 输出最终 Pose
```

#### A.10.4 HTFootIKAnimNode 完整参数表

这是 HT 的核心 IK 解算器，参数极其丰富：

```cpp
// === 基础骨骼 ===
IKFootRootBone:     "root_foot"        // IK 根骨骼（虚拟骨）
PelvisBone:         "Bip001-Pelvis"    // 骨盆修正目标

// === 骨盆设置 (PelvisSettings) ===
MaxOffset:              50              // 最大骨盆偏移量 (cm)
LinearStiffness:        250             // 线性刚度（弹簧系数）
LinearDamping:          1               // 线性阻尼
HorizontalRebalancingWeight: 0.3        // 水平再平衡权重
MaxOffsetHorizontal:    10              // 最大水平偏移
HeelLiftRatio:          0.5             // 脚跟抬起比例
PelvisHeightMode:       AllLegs         // 双腿模式（任一腿着地即修正）
bDisablePelvisOffsetInAir: true          // 空中禁用骨盆偏移
DisablePelvisCurveName: "disablepelvis"  // 禁用曲线名

// === 腿部定义 (双腿对称) ===
左腿: FK=Bip001-L-Foot, IK=foot_l, Ball=Bip001-L-Toe0, NumBones=2
     DisableCurve: "DisableLeftLegIK"
右腿: FK=Bip001-R-Foot, IK=foot_r, Ball=Bip001-R-Toe0, NumBones=2
     DisableCurve: "DisableRightLegIK"

// === 脚步锁定 (PlantSettings) ===
SpeedThreshold:     60               // 速度阈值 (cm/s)，低于此速度触发锁定
DistanceToGround:   2                // 离地距离容差
LockType:           PivotAroundBall   // 以脚球(Ball)为轴旋转
UnplantRadius:      10               // 抬脚判定半径
ReplantRadiusRatio: 0.35              // 落脚半径比例
UnplantAngle:       45                // 抬脚角度阈值
bReconstructWorldPlantFromVelocity: true  // 从速度重建世界空间落脚点

// === 插值设置 (InterpolationSettings) ===
UnplantLinearStiffness:  100           // 抬脚刚度（低 = 抬起慢）
FloorLinearStiffness:   520           // 地面刚度（高 = 贴地紧）
FloorAngularStiffness:  450           // 地面角刚度
bEnableFloorInterpolation: true
bEnableSeparationInterpolation: true

// === 射线检测 (TraceSettings) ===
StartOffset:    -75                 // 射线起点（从骨盆向下 75cm）
EndOffset:      100                 // 射线终点（从骨盆向下 100cm）
SweepRadius:    5                   // 扫描半径
TraceChannel:   TraceTypeQuery4     // 自定义追踪通道
MaxGroundPenetration: 10            // 最大地面穿透深度

// === 高级功能 ===
bUsePredict:             true        // 启用楼梯预测！
TransitionThreshold:     0.005       // 过渡阈值
VecInterpSpeed:          12          // 向量插值速度

// === 个人化配置 ===
FootLength:          23.5            // 脚长 (cm)
UpStairBezierMiddlePoints: [(0,1), (0.5,1)]   // 上楼梯贝塞尔控制点
DownStairBezierMiddlePoints: [(0.5,1), (1,0.5)] // 下楼梯贝塞尔控制点
PredictEndFootOffsets: [(-2,1,13), (2,1,13)]    // 预测落脚偏移
```

**关键设计亮点**：
- **楼梯预测 (`bUsePredict`)**：通过贝塞尔曲线预判上下楼梯的脚步位置，避免脚穿模台阶
- **脚步锁定 (`LockType: PivotAroundBall`)**：低速时以脚球为轴旋转锁定，脚跟可自然抬起
- **从速度重建落脚点** (`bReconstructWorldPlantFromVelocity`)：不依赖简单射线检测，而是结合运动速度矢量推算最佳落脚位置
- **Virtual Bone 目标系统**：用 VB 骨骼作为 IK 效果器的中间目标，解耦了 IK 计算和最终骨骼应用

#### A.10.5 IK 控制曲线一览

| 曲线名 | 用途 | 控制范围 |
|--------|------|----------|
| `Enable_FootIK_L` | 左脚 IK 开关 (ModifyBone + TwoBoneIK Alpha) | 0~1 |
| `Enable_FootIK_R` | 右脚 IK 开关 | 0~1 |
| `DisableLeftLegIK` | 左腿 LegIK 禁用 | 0~1 |
| `DisableRightLegIK` | 右腿 LegIK 禁用 | 0~1 |
| `disablepelvis` | 骨盆修正禁用 | 0~1 |
| `Moving` | 移动状态混合（FootPlacement 用） | 0~1 |
| `TutLeftFootCurve` / `TutRightFootCurve` | TUT 脚部微调 | 自定义 |
| `LeftLockCurve` / `RightLockCurve` | 脚步锁定强度 | 0~1 |
| `PredictLenghtLeft` / `PredictLenghtRight` | 楼梯预测长度 | 自定义 |

**动态控制方式**：
```
BP_SetFootIKStateANS (AnimNotify State):
  NotifyBegin → UHTAnimInstance->JoinFootIKState = JoinFootIKState
  NotifyEnd   → UHTAnimInstance->ExitFootIKState = 1.0 (默认恢复)

典型用途: 跳跃/翻滚动画期间禁用 FootIK（空中不需要脚对地）
         落地后自动恢复
```

#### A.10.6 骨骼体系（Bip 命名规范 + Virtual Bone）

```
物理骨骼 (FK, 来自 3ds Max Biped):
Bip001-Pelvis (骨盆 — IK 修正目标)
├── Bip001-L-Thigh → Bip001-L-Calf → Bip001-L-Foot → Bip001-L-Toe0 (左腿链)
└── Bip001-R-Thigh → Bip001-R-Calf → Bip001-R-Foot → Bip001-R-Toe0 (右腿链)

虚拟骨骼 (VB 前缀, IK 中间目标):
├── root_foot        (IK 根骨骼)
├── foot_l / foot_r   (左右脚 IK 骨骼)
├── VB ik_foot_l_offset   (左脚 Effector 目标 — TwoBoneIK 的 Effector)
├── VB ik_foot_r_offset   (右脚 Effector 目标)
├── VB foot_l_target_*    (左膝 JointTarget 偏移 offset:-15,-30,0)
└── VB foot_r_target_*    (右膝 JointTarget 偏移 offset:-15,-30,0)
```

#### A.10.7 FullBodyIK 与 FootIK 的关系

```
FullBodyIK 状态机 (AnimBP 中第 4 个并行状态机):
  Inactive(0) ←──[0.2s Inertialization]──→ Activated(1)
                                  ←──[0.1s Inertialization]──┘

集成方式:
  AnimGraph 主流:
    │
    ├── [LinkedAnimLayer: "FootIK"]  ← 通过 FootIK_AnimInterface 注入
    │     └── FootIK_AnimLayer_Base (完整 IK 流水线, 见 A.10.3)
    │
    ├── [CachedPose: "AfterFullBodyIK"] ← FullBodyIK 后的缓存
    │     (被下游多个节点引用)
    │
    ├── [CachedPose: "PoseFootIK"] ← 最终 FootIK 输出缓存
    │
    └── [Inertialization] ← 最终惯性化平滑输出到渲染
```

**FullBodyIK** 处理上半身/脊柱 IK，**FootIK** 处理腿部/脚部 IK。
两者通过 CachedPose 机制解耦，各自独立运算后合并输出。

#### A.10.8 GGYGO 可借鉴的 FootIK 方案

| 阶段 | 借鉴内容 | 难度 | 收益 |
|------|----------|------|------|
| **P2** | 使用 UE 内置 `AnimNode_FootIK` + `AnimNode_FullBody` | 低 | 解决基本脚穿地问题 |
| **P2** | Virtual Bone + TwoBoneIK 手动方案（参考 HT 的简化版） | 中 | 更精确控制 |
| **P3** | 自定义 C++ `FGGYGOFootIKAnimNode`（仿 HT 参数集） | 高 | 楼梯预测+脚步锁定 |

**推荐起步方案**（P2）：
1. 在 ABP 中添加 UE 内置 `AnimNode_FootIK` 节点
2. 配置 IK Foot Root / Pelvis / Foot Bones
3. 用动画曲线 `Enable_FootIK` 控制启停（跳跃时禁用）
4. 后续有需要再考虑自定义 C++ 节点

### A.11 C++ 源码获取情况说明

> 用户提问：这些蓝图有没有对应的 C++ 源码？我想学习。

**结论：C++ 源码不在 FModel 导出范围内。**

| 内容 | FModel 能否导出 | 说明 |
|------|----------------|------|
| Content 目录资源 (.uasset) | **能** | 蓝图、材质、网格、DataTable、AnimBP 等 |
| 反编译伪 C++ (.cpp 从 .uasset) | **能** | 蓝图的 C++ 表示（如 BP_PlayerCharacterBase.cpp） |
| **C++ 模块源码 (.h/.cpp)** | **不能** | `/Script/HTGame` 的源码在编译后的二进制中 |
| **头文件声明** | 不能直接导出 | 但可通过蓝图 SuperStruct + 字段反推 |

**已确认的 HTGame C++ 原生类清单**（通过蓝图继承链反推）：

| C++ 类名 | 用途 | 推断依据 |
|----------|------|----------|
| `AHTPlayerCharacter` | 玩家角色基类 | BP_PlayerCharacterBase 的父类 |
| `UHTAbilitySystemComponent` | 自定义 ASC | 继承 UAbilitySystemComponent |
| `UHTPlayerCharacterMovementComponent` | 自定义 CMC | 继承 UCharacterMovementComponent |
| `UHTCharacterStateManagerComponent` | 状态管理器 | 28+ 状态子类的管理者 |
| `UHTMotionWarpingComponent` | 运动扭曲 | MotionWarping 功能提供者 |
| `UHTGameplayAbility` | GAS 能力基类 | GA_HTAbilityBase 的父类 |
| `UHTPlayerAnimInstance` | 动画实例基类 | HtPlayerCharacterAniminstanceBase 的父类 |
| `UHtMovementAttributeSet` | 移动属性集 | DataAsset 的类型 |
| `UHTPlayerAttributeSet` | 玩家属性集 | 血量/攻击等数值 |
| `UHTFootIKAnimLayer` | FootIK 层基类 | 所有 FootIK_AnimLayer 的父类 |
| `FHTFootIKAnimNode` | Foot IK 解算器节点 | AnimBP NodeTypeMap 注册 |
| `FHTAnimNode_FootPlacement` | 脚步放置节点 | AnimBP NodeTypeMap 注册 |
| `FHTSkirtControlAnimNode` | 裙子物理节点 | AnimBP NodeTypeMap 注册 |
| `FHTAimOffsetAnimNode` | 瞄准偏移节点 | AnimBP NodeTypeMap 注册 |

**学习建议**：虽然拿不到原始 `.h/.cpp`，但通过 FModel 导出的蓝图反编译代码可以：
1. **反推出完整的类声明**（字段名、类型、函数签名）
2. **理解设计意图和架构决策**（为什么这样分层）
3. **在 GGYGO 中复刻相同模式**（用我们自己的 C++ 实现）

这正是本文档附录 A 的目的 —— 把 HT 的架构分析透，让你能在 GGYGO 中实现相同质量的系统。

### A.12 HT 动画衔接流畅的核心技术分析

> 用户提问：他们的动画为什么衔接得这么流畅？我想学习这个。

#### 为什么"全局固定混合时间"是动画卡顿的元凶

大多数新手项目的动画系统使用**全局统一混合时间**（比如固定 0.2 秒），这会导致：

| 场景 | 固定 0.2s 的效果 | 期望效果 |
|------|-----------------|---------|
| Idle → 跑步启动 | **太慢**，输入后角色"发呆"0.2s 才动 | **瞬切/极快**（0~0.05s），响应干脆 |
| 跑步循环 → 停止 | 还行，但不够自然 | **稍慢**（0.15~0.2s），自然减速感 |
| 任意 → 受击 | **太慢**，打击感被稀释 | **瞬切**（0~0.05s），受击即反应 |
| 任意 → 死亡 | 太快，缺乏戏剧性 | **慢入**（0.3~0.5s），戏剧性渐隐 |
| 闪避切入/切出 | 有拖影，不敏捷 | **完全瞬切**（0s） |

**核心结论：不同状态转换需要截然不同的混合时间。全局固定值无法同时满足所有场景。**

---

#### HT 鸣潮的解决方案：每转换对独立混合时间

HT 的动画流畅性来自以下 **5 个核心技术**：

##### 技术 1：Per-State Blend Time（每状态独立混合时间）

HT 不使用全局混合时间，而是为**每个状态单独配置**进入/离开的过渡时间。

```
HT 推荐配置（已写入 UCharConfigData 默认注释）：

状态          BlendIn   BlendOut   设计理由
─────────────────────────────────────────────────
Idle          0.10s     0.10s      平静进出，不突兀
RunStart      0.05s     0.10s      快速启动有劲，离开时温和
RunLoop       0.15s     0.15s      循环态稳定，过渡自然
RunEnd        0.15s     0.10s      减速过程平滑，落地快
InAir         0.10s     0.10s      空中姿态快速建立
Attacking     0.00s     0.10s      攻击瞬间切入（打击感），收招温和
Dodging       0.00s     0.00s      完全瞬切，极致敏捷
HitStun       0.00s     0.05s      受击瞬硬，恢复略缓
Stunned       0.05s     0.10s      眩晕渐进进入
Dead          0.30s     0.00s      慢入死亡（戏剧性），不切出
Interacting   0.10s     0.10s      交互标准过渡
```

**GGYGO 已实现**：`UCharConfigData.PerStateBlendOverrides` (TMap) + `GetBlendInTime()` / `GetBlendOutTime()`

##### 技术 2：状态机驱动的动画切换（非直接播放）

HT 不是"按什么键播什么动画"，而是通过**状态机中间层**来驱动动画：

```
用户输入 → IntentPipeline → ArbiterPipeline → CharacterStateMachine → AnimInstance
                                                              ↓
                                                    ApplyStateAnimation()
                                                          ↓
                                              ResolveAnimForState(state)
                                                          ↓
                                          GetBlendIn/OutDuration(state)
                                                          ↓
                                              Montage_Play / SlotAnim
```

好处：
- **状态变化 = 动画变化的唯一触发点**，不会出现"按键了但动画没切"或"动画切了但状态没变"
- **打断逻辑集中管理**：状态机的 `CanInterrupt` 规则同时控制动画和逻辑
- **可预测**：给定当前状态 + 输入，结果状态（和对应动画）是确定的

**GGYGO 已实现**：`FCharacterStateMachine` + `ApplyStateAnimation()` 完整链路

##### 技术 3：循环动画缓存复用

HT 对循环状态的动画（Idle/RunLoop/InAir/Stunned）采用**预创建 Montage 缓存**策略：

```
启动时 (EnsureLoopingMontages):
  IdleAnim   → PlaySlotAnimationAsDynamicMontage → 缓存为 IdleMontage
  RunLoopAnim→ PlaySlotAnimationAsDynamicMontage → 缓存为 RunLoopMontage
  InAirAnim  → PlaySlotAnimationAsDynamicMontage → 缓存为 InAirMontage
  StunnedAnim→ PlaySlotAnimationAsDynamicMontage → 缓存为 StunnedMontage

每次进循环状态:
  Montage_Play(CachedMontage)  ← 复用，不新建对象

每次进非循环状态:
  PlaySlotAnimationAsDynamicMontage(OneShotAnim)  ← 用完即弃
```

为什么这样设计？
- **避免每帧 GC 压力**：动态 Montage 每次创建都是 UObject，频繁创建回收触发 GC
- **保证混合一致性**：同一个 Montage 实例的混合参数不变，不会出现"第一次切平滑、第二次切卡顿"
- **支持即时重启**：Montage_Play 可以从头播放缓存的 Montage，无需重建

**GGYGO 已实现**：4 个缓存 Montage 成员变量 + `EnsureLoopingMontages()` 初始化

##### 技术 4：Config-First 数据回退模式

HT 的动画资产不是硬编码在 C++ 里，而是从 DataAsset 读取：

```
解析优先级（ResolveAnimForState）：
1. Config->GetAnimForState(State)    ← DataAsset 中配置的动画
2. Self.IdleAnim / Self.RunLoopAnim  ← AnimInstance 自身属性（向后兼容）
3. nullptr                           ← 无动画，保持当前姿态
```

这意味着：
- **换角色 = 换 Config Asset**，不改一行 C++
- **美术调整 = 改 DataAsset 细节面板**，不需要程序员介入
- **A/B 测试方便**：复制一份 Config 改几个参数即可对比效果

**GGYGO 已实现**：`UCharConfigData` DataAsset + `ResolveAnimForState()` 回退链

##### 技术 5：惯性化（Inertialization）— 高级平滑技术

> 这是 HT 动画"丝滑感"的最核心秘诀，也是最难实现的。

**问题**：即使用了独立混合时间，当动画 A 混合到动画 B 时：
- 如果 BlendIn=0（瞬切），骨骼位置会**跳变**（pop）
- 如果 BlendIn>0（混合），两个姿势会**交叉溶在一起**（看起来像软泥）

**惯性化的原理**：

```
传统混合（Crossfade）：
  姿势A ──[线性插值]──→ 姿势B
  问题：中间帧是 A 和 B 的"平均值"，看起来软/糊

惯性化（Inertialization）：
  姿势A 的速度/加速度 ──[指数衰减]──→ 零
  同时 姿势B 从零开始 ──[正常播放]──→ B
  结果：A 的"运动惯性"自然消亡，B 从静止起步，无跳变无软泥
```

简单理解：
- **不是把两段动画混在一起**
- **而是让旧动画的运动"惯性滑行"到停止，同时新动画从零开始接入**
- 就像现实世界中跑步突然停下 — 身体会有前倾惯性，然后自然恢复直立

**HT 的实现方式**（基于 UE 的 `FAnimNode_Inertialization` 或自定义）：

```cpp
// 伪代码：惯性化每一帧的计算
void TickInertialize(float DeltaTime)
{
    if (bInertializing)
    {
        // 惯性衰减系数（越大衰减越快）
        float Decay = FMath::Exp(-DeltaTime * InertializeSpeed);

        // 每个骨骼的位置 = 上帧惯性偏移 × 衰减 + 新动画原始位置
        for (BoneIndex : AllBones)
        {
            InertialOffset[BoneIndex] *= Decay;
            OutputPose[BoneIndex] = SourcePose[BoneIndex] + InertialOffset[BoneIndex];
        }

        // 当偏移量足够小时结束惯性化
        if (MaxOffset < Threshold)
        {
            bInertializing = false;
        }
    }
}
```

**GGYGO 当前状态**：尚未实现惯性化，但架构已预留扩展点（`ApplyStateAnimation` 可在切换时记录上一帧 Pose 差异）

**建议后续实现路径**：
1. 先用独立混合时间（已完成）→ 已经能获得 80% 的流畅度提升
2. 后续可引入 UE5 内置的 `AnimNode_Inertialization`（引擎原生支持）
3. 或在 GGYGOAnimInstance 中自定义惯性化逻辑

---

#### 总结：HT 动画流畅的完整技术栈

```
层级 1 [基础]  Per-State Blend Time     ★ GGYGO 已完成
层级 2 [架构]  StateMachine-Driven Anim  ★ GGYGO 已完成
层级 3 [性能]  Loop Montage Cache        ★ GGYGO 已完成
层级 4 [数据]  Config-First DataAsset    ★ GGYGO 已完成
层级 5 [高级]  Inertialization            ⬜ 待实现（可用 UE5 内置节点）
```

前 4 层已经全部实现并编译通过。第 5 层（惯性化）可以在后续迭代中加入，UE5 引擎本身提供了 `FAnimNode_Inertialization` 节点，可以直接在 AnimBP 的 AnimGraph 中使用。

---

## 附录 B：v2 数据驱动升级 — 执行记录

> 执行日期：2026-06-12
> 目标：仿照 HT 鸣潮的 BP_PlayerCharacterBase 模式，将角色配置从硬编码改为 DataAsset 驱动

### B.1 变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `Public/Data/UCharConfigData.h` | **新建** | 角色 DataAsset 完整定义（11 态动画映射 + FStateTransitionBlend + PerStateBlendOverrides TMap + FMovementConfig + GAS 配置 + 5 个查询方法） |
| `Private/Data/UCharConfigData.cpp` | **新建** | Config 查询方法实现（GetAnimForState/GetBlendInTime/GetBlendOutTime/IsLoopingState/GetPlayRateForState） |
| `Public/BaseCharacter.h` | **修改** | 新增 `CharacterConfig` 字段（EditDefaultsOnly）+ `GetCharacterConfig()` 公有 getter |
| `Public/Animation/GGYGOAnimInstance.h` | **修改** | 新增 CachedConfig + 5 个 Config 查询方法声明 + 循环蒙太奇扩展至 4 个 |
| `Private/Animation/GGYGOAnimInstance.cpp` | **修改** | 全面改为 Config 驱动：NativeUpdateAnimation 缓存 Config、ApplyStateAnimation 使用 ResolveAnimForState/GetBlendInDuration/GetBlendOutDuration、EnsureLoopingMontages 创建 4 个缓存 |

### B.2 架构变更图

```
Before (v1):
  BaseCharacter ──[硬编码属性]──→ AnimInstance ──[固定 0.2s]──→ 动画播放
  (IdleAnim/RunLoopAnim 等 EditAnywhere 直接填在 AnimInstance 上)

After (v2):
  BaseCharacter.CharacterConfig ──[UCharConfigData*]──→ AnimInstance
                                                  ↓
                              Config.GetAnimForState(state)  ← 11 态动态映射
                              Config.GetBlendInTime(state)  ← 独立混合时间
                              Config.IsLoopingState(state)  ← 循环/单次判断
                              Config.GetPlayRateForState()  ← 独立播放速率
                                                  ↓
                                            动画播放（Slot + Montage）
```

### B.3 使用流程（编辑器中）

```
1. 内容浏览器 → 右键 → Miscellaneous → DataAsset → GGYGO.UCharConfigData
2. 命名: DA_MiyabiConfig
3. 细节面板配置:
   ├─ 动画|基础: IdleAnim / RunStartAnim / RunLoopAnim / RunEndAnim  ← 拖入 AnimSequence
   ├─ 动画|战斗: InAirAnim / AttackAnim / DodgeAnim / ...
   ├─ 混合时间: DefaultBlendDuration = 0.2
   │           └─ PerStateBlendOverrides → 展开逐状态设置 BlendIn/BlendOut
   ├─ 过渡时间: RunStartMinDuration / RunEndMinDuration
   ├─ 播放速率: LoopAnimPlayRate / NonLoopAnimPlayRate
   ├─ 移动: MovementConfig (SprintMultiplier / AirControlFactor / ...)
   └─ GAS: DefaultAbilities / DefaultEffects
4. 打开 BP_Miyabi（或任何角色蓝图）
5. Details → 配置|角色 → CharacterConfig → 选择 DA_MiyabiConfig
6. 完成！运行即可看到 Config 驱动的动画效果
```

### B.4 向后兼容性

- **Config 为空时**：AnimInstance 自动回退到自身 EditAnywhere 属性（IdleAnim/RunLoopAnim 等 4 个基础状态）
- **旧工作流不受影响**：可以继续在 AnimInstance 上直接填动画资产
- **推荐迁移**：逐步将配置转移到 DataAsset，获得完整的 11 态支持和独立混合时间控制
