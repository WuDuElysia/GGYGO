# GGYGO 代码规范

本文档整理自现有代码风格，用于保持项目代码一致性。

---

## 一、注释规范（强制 Doxygen 风格）

### 1.1 文件头注释

每个 `.h` 和 `.cpp` 文件开头必须有：

```cpp
/**
 * @file FileName.h
 * @brief 一句话描述这个文件是干什么的
 *
 * 详细说明（可选，多行）。
 */
```

示例（单行 brief）：
```cpp
/**
 * @file InputPipeline.cpp
 * @brief 输入管线实现
 */
```

示例（带详细说明）：
```cpp
/**
 * @file RuntimeData.h
 * @brief 运行时黑板 - 全局帧级共享数据中枢
 * 
 * 所有子系统通过 RuntimeData 共享数据，不直接互相引用。
 * 每个字段只有一个系统写入，多个系统读取。
 * 帧级意图在帧末由 ResetFrameIntents() 清零。
 */
```

### 1.2 类/结构体注释

```cpp
/**
 * 运行时黑板
 * 管线中所有系统的数据交换中心
 */
struct FRuntimeData
{
```

```cpp
/**
 * 后处理输入数据
 * 经过防抖缓冲和动作按键缓冲后的输入状态
 */
struct FProcessedInput
{
```

### 1.3 函数注释

```cpp
/**
 * 每帧调用，处理输入
 * 在 BaseCharacter::Tick 的第 2 步调用
 * @param DeltaTime 帧间隔
 */
void Process(float DeltaTime);
```

```cpp
/**
 * 初始化所有处理器，注入外部依赖
 * @param InOwner 角色指针（ViewRotationProcessor 需要）
 * @param InMesh  骨骼网格体（RootMotionParameterProcessor 需要）
 */
void Init(ACharacter* InOwner, USkeletalMeshComponent* InMesh);
```

带 @return 的：
```cpp
/**
 * 尝试切换到目标状态
 * @return 是否切换成功
 */
bool TryTransitionTo(ECharacterStateType NewState, FRuntimeData& RuntimeData);
```

### 1.4 成员变量注释

```cpp
/** 移动输入原始值（WASD / 左摇杆） */
FVector2D MoveInput = FVector2D::ZeroVector;

/** 输入数据容器（不拥有，由 BaseCharacter 管理生命周期） */
FInputData& InputData;
```

### 1.5 行内注释

用 `//`，放在代码上方或同行的右侧：
```cpp
// 1. 推进双缓冲
InputData.AdvanceFrame();
```

### 1.6 函数内部块注释

用 `//`，放在逻辑块上方：
```cpp
// 约束 Health 在 0 ~ MaxHealth 之间
void ClampHealth(float& NewValue);
```

### 1.7 分隔线（section 分隔）

```cpp
// ============================================================
// 输入状态（由 InputPipeline 写入）
// ============================================================
```

### 1.8 TODO 标记

```cpp
// TODO: 阶段五做完 MotionDriver 后删除以下代码
// TODO: 阶段六仲裁管线完成后启用
```

### 1.9 注释必须准确描述当前代码（强制）

**原则：注释描述的是"这段代码现在在做什么"，而不是"它以前是什么样的"或"它将来会变成什么"。**

#### 错误示例（不要这样写）

```cpp
/**
 * ★ 数据驱动（v2 升级）：
 *   - 动画资产：优先从 UCharConfigData 读取，回退到自身 EditAnywhere 属性
 *   - 混合时间：每对状态转换独立控制（Config.PerStateBlendOverrides），
 *     替代旧版全局固定 0.2s          ← ❌ "替代旧版"是在讲历史，读者不需要知道
 *   - 新增 InAir/Attack/Dodge/HitStun/Stunned/Dead 共 11 态完整支持  ← ❌ "新增"暗示以前没有
 */
```

问题：
- 提到 `v2 升级`、`旧版`、`新增` — 这些都是**版本历史信息**，不是当前代码行为的描述
- 新来读代码的人不知道 v1 长什么样，这些注释对他没有帮助
- 代码重构后这些注释会变得过时但没人去更新

#### 正确示例（应该这样写）

```cpp
/**
 * @file GGYGOAnimInstance.cpp
 * @brief Config 驱动动画实例实现
 *
 * 动画播放策略：
 *   循环动画（Idle/RunLoop/InAir/Stunned）：启动时预创建 UAnimMontage 缓存复用
 *   非循环动画（RunStart/RunEnd/Attack/Dodge/HitStun/Dead）：动态 Montage 播一次
 *
 * 数据来源优先级：
 *   1. UCharConfigData（角色 DataAsset，11 态完整映射 + 独立混合时间）
 *   2. AnimInstance 自身 EditAnywhere 属性（4 基础状态，向后兼容）
 *   3. 默认值（LegacyBlendDuration = 0.2s）
 */
```

#### 具体规则

| 规则 | 说明 | 示例 |
|------|------|------|
| **不写版本号** | 注释里不要出现 v1/v2/升级/旧版/新增/重构 等词汇 | 用"Config 驱动"代替"v2 升级后的 Config 驱动" |
| **不写变更历史** | 代码变更记录放 Git commit 和文档，不放注释 | 删除"原来是用 xxx，现在改成 yyy" |
| **描述当前行为** | 注释回答"这段代码现在做什么"，不回答"它经历了什么" | 写"从 Config 读取混合时间"代替"替代了原来的固定 0.2s" |
| **文件头 @brief 只写功能** | 不写迭代历史 | 用"数据驱动的动画播放系统"代替"v2: 从硬编码改为数据驱动" |
| **删除过时注释** | 重构代码时同步清理引用旧逻辑的注释 | 如果一个 if 分支被删了，对应的"兼容旧版xxx"注释也要删 |

#### 唯一例外

只有一种情况允许提到"以前"：**TODO/FIXME 标记中说明需要删除的遗留代码**：

```cpp
// TODO: 以下硬编码路径将在全部角色迁移到 Config 后删除
if (!CachedConfig) { /* ... */ }
```

---

## 二、命名规范

### 2.1 类型前缀

| 前缀 | 类型 | 示例 |
|------|------|------|
| `F` | 纯 C++ 结构体 / 类 | `FRuntimeData`, `FInputPipeline` |
| `U` | UObject 子类 | `UGGYGOAttributeSet` |
| `A` | Actor 子类 | `ABaseCharacter`, `APlayerCharacter` |
| `I` | 接口类 | `IIntentProcessor`, `IParameterProcessor` |
| `E` | 枚举 | `ECharacterStateType` |
| `T` | 模板 / 容器 | `TArray`, `TUniquePtr`, `TMap` |

### 2.2 大小写

| 类型 | 风格 | 示例 |
|------|------|------|
| 类名 / 结构体名 | PascalCase | `FInputPipeline`, `FRuntimeData` |
| 函数 / 方法 | PascalCase | `Process()`, `SetMoveInput()`, `ResetFrameIntents()` |
| 成员变量 | PascalCase（无前缀） | `CurrentFrame`, `DesiredWorldMoveDir` |
| 布尔变量 | `b` + PascalCase | `bWantsToJump`, `bHasRootMotion`, `bIsMoving` |
| 局部变量 | PascalCase | `Forward`, `WorldDir`, `RootMotion` |
| 参数 | `In`/`Out` + PascalCase | `InInputData`, `InOwner`, `DeltaTime` |
| 常量 | `k` 或全大写（UE 风格） | `ActionBufferTime`（static constexpr） |

### 2.3 文件名

- 文件名 = 类名（去掉前缀）
- 例如：`FInputPipeline` → `InputPipeline.h` / `InputPipeline.cpp`

---

## 三、代码结构

### 3.1 `#include` 顺序

```cpp
// 1. 本文件对应的头文件
#include "Pipeline/InputPipeline.h"

// 2. 项目内部头文件（按目录分组）
#include "Pipeline/Intents/ViewRotationProcessor.h"
#include "Pipeline/Parameters/MovementParameterProcessor.h"
#include "Data/InputData.h"
#include "Data/RuntimeData.h"

// 3. 引擎头文件
#include "GameFramework/Character.h"
#include "Components/SkeletalMeshComponent.h"
```

路径写法：使用 `"Public/xxx"` 风格（不带 `Public/` 前缀，因为 IncludePath 已配置）。

### 3.2 头文件结构

```cpp
/**
 * @file Xxx.h
 * @brief xxx
 */

#pragma once                           // 只用 #pragma once

#include "CoreMinimal.h"              // 必须第一个
// ... 其他 include ...

// 前向声明（减少编译依赖）
class ACharacter;
struct FRuntimeData;
enum class ECharacterStateType : uint8;

// 类定义
class FMyClass
{
public:
    // 构造/析构
    // 公共方法
    // 公共成员（几乎没有，尽量用 private）

private:
    // 私有成员
};
```

### 3.3 类内成员的排列顺序

1. `public` 方法（构造 → Init → 核心逻辑 → 访问器）
2. `private` 方法
3. `private` 成员

分组用注释分隔线：
```cpp
public:
    void Init(...);
    void Process(float DeltaTime);

    // ============================================================
    // 数据写入接口
    // ============================================================

    void SetXxx(...);

private:
    // ============================================================
    // 内部状态
    // ============================================================
```

### 3.4 `.cpp` 文件结构

```cpp
/**
 * @file Xxx.cpp
 * @brief xxx 实现
 */

#include "Xxx.h"                      // 对应头文件
// ... 其他 include ...

// 构造函数实现（简短的可直接在 .h 里写）
FMyClass::FMyClass() ...

// 方法实现（按头文件中声明的顺序）
void FMyClass::Init(...) ...
```

---

## 四、纯 C++ 类 vs UObject 的约定

### 4.1 纯 C++ 类（`F` 前缀）

- 不需要反射、不需要蓝图访问 → 用纯 C++ 类
- 在 BaseCharacter 里用 `TUniquePtr<T>` 持有
- 依赖的外部对象（ACharacter、USkeletalMeshComponent）通过 Init() 注入原始指针
- 不拥有 UObject（只管用不管生命周期，GC 管理）

示例：
```cpp
// BaseCharacter.h
TUniquePtr<FInputPipeline> InputPipeline;

// 构造函数里
InputPipeline = MakeUnique<FInputPipeline>(*InputData);

// UObject 注入用原始指针
void Init(ACharacter* InOwner, USkeletalMeshComponent* InMesh);
```

### 4.2 UObject 子类（`U` 前缀）

- ASC、AttributeSet、Ability 等
- 用 `CreateDefaultSubobject<>()` 在构造函数里创建
- 成员变量必须标记 `UPROPERTY()` 防止被 GC 回收
- 不暴露给纯 C++ 管线的内部类（只暴露接口引用的）

---

## 五、接口规范

```cpp
/**
 * @file IIntentProcessor.h
 * @brief 意图处理器接口
 */
#pragma once

#include "CoreMinimal.h"

class FInputData;
struct FRuntimeData;

class IIntentProcessor
{
public:
    virtual ~IIntentProcessor() = default;

    /**
     * 每帧处理意图
     * @param InputData  输入数据（只读，由 InputPipeline 写入）
     * @param RuntimeData 运行时黑板（写入意图字段）
     */
    virtual void Process(const FInputData& InputData, FRuntimeData& RuntimeData) = 0;
};
```

关键点：
- 接口类名以 `I` 开头
- 虚析构用 `= default`
- 只声明纯虚函数（`= 0`）
- 不要放数据成员
- 前向声明依赖，不 include 具体结构体头文件（在接口这里只是声明用，实际 include 放在 `.cpp` 里）

---

## 六、模板方法 vs 接口

状态机中有一些行为是固定的（PerformTransition、IsTransitionAllowed），
另一些是变化的（状态的 Enter/Update/Exit）。

| 固定的 → | 在基类/主类里实现 |
| 变化的 → | 虚函数，子类重写 |

```cpp
// 状态机主类（FCharacterStateMachine）：处理固定的转换逻辑
void PerformTransition(...);
bool IsTransitionAllowed(...) const;

// 状态基类（FCharacterState）：声明虚函数
virtual void Enter(FRuntimeData& RuntimeData);
virtual void Update(float DeltaTime, FRuntimeData& RuntimeData, FCharacterStateMachine& SM);
virtual void Exit(FRuntimeData& RuntimeData);

// 具体状态：重写
void FIdleState::Update(float DeltaTime, FRuntimeData& RuntimeData, FCharacterStateMachine& SM) override;
```

---

## 七、错误处理

当前阶段不抛异常，用静默返回：
```cpp
if (!InputData) return;
if (!Owner) return;
if (!ASC) return;
```

---

## 八、目录结构约定

```
Source/GGYGO/
├── Public/
│   ├── Data/                    # struct，纯数据，无逻辑
│   ├── Pipeline/                # 管线主类和接口
│   │   ├── Interfaces/          # IIntentProcessor, IParameterProcessor 等
│   │   ├── Intents/             # 意图处理器
│   │   └── Parameters/          # 参数处理器
│   ├── StateMachine/            # 状态机
│   │   └── States/              # 具体状态
│   ├── Drivers/                 # 驱动层（未来）
│   ├── Movement/                # 旧版移动系统（临时）
│   ├── Attributes/              # GAS 属性
│   ├── Abilities/               # GAS 技能
│   └── Camera/                  # 摄像机
├── Private/
│   └── （镜像目录结构）
```

`Public` 和 `Private` 目录结构镜像一致。

---

## 九、检查清单

写代码前自查：

- [ ] 文件头有 `@file` `@brief` 注释
- [ ] 每个类/结构体有注释
- [ ] 每个 public 函数有 `@param` 注释
- [ ] 每个成员变量有注释
- [ ] 类名前缀正确（F/U/A/I/E）
- [ ] 布尔变量以 `b` 开头
- [ ] include 顺序：自己 → 项目 → 引擎
- [ ] 用 `TUniquePtr` 持有纯 C++ 对象
- [ ] 用原始指针引用 UObject（不拥有）
- [ ] 虚函数有 `override`
- [ ] Section 用了分隔线
- [ ] 构造函数里空代码块不要干放着（要么有用，要么让编译器默认生成）
- [ ] **注释描述当前代码行为，不含版本号/变更历史/新旧对比（见 1.9）**
