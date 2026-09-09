---
inclusion: auto
name: lyra-reference
description: Lyra（LyraStarterGame）参考工程的本地路径与源码目录索引。当任务需要参照 Lyra 的项目结构、GAS 实现、Character/Movement/Ability 组件、Experience/GameFeature、Input、Camera、Teams、Equipment 等做法时使用。
---

# Lyra 参考工程索引

## 本地路径（唯一权威参考副本）

- 工程根：`F:\ue_project\LyraStarterGame`
- 主 Gameplay 模块：`F:\ue_project\LyraStarterGame\Source\LyraGame`
- 编辑器模块：`F:\ue_project\LyraStarterGame\Source\LyraEditor`
- 插件：`F:\ue_project\LyraStarterGame\Plugins`

不确定 Lyra 某个类、某个目录或某种写法时，直接到上述路径检索实际源码，不要凭记忆推断。

`f:\ue_project\GGYGO\Lyra\` 下只有 `AbilitySystem` 的局部副本，是不完整的旧片段。参考 Lyra 时一律使用 `F:\ue_project\LyraStarterGame`。

## 使用约定

- Lyra 源码是**只读参考**。不修改 `F:\ue_project\LyraStarterGame` 下的任何文件。
- Lyra 不纳入 GGYGO 的代码搜索范围。GGYGO 自身的符号检索、引用核对仍只搜 `Source/GGYGO/**`；只有在明确需要"Lyra 是怎么做的"时才检索 Lyra 路径。
- Lyra 是多人在线射击范式（复制、Experience、Inventory/Weapons）。GGYGO 是动作游戏，照搬前先判断该机制是否需要网络复制、是否需要 GameFeature 插件化。

## LyraGame 顶层目录

| 目录 | 内容 |
|---|---|
| `AbilitySystem/` | GAS 核心：ASC、AbilitySet、Globals、EffectContext、CueManager、TagRelationshipMapping、GlobalAbilitySystem |
| `Animation/` | `LyraAnimInstance`（仅一个文件，Lyra 动画逻辑大部分在 AnimBP） |
| `Audio/` | 音频设置与混音 |
| `Camera/` | CameraMode 栈、CameraComponent、PlayerCameraManager |
| `Character/` | Pawn/Character、CMC、HealthComponent、HeroComponent、PawnExtensionComponent、PawnData |
| `Cosmetics/` | 角色外观部件 |
| `Development/` | 开发期设置与工具 |
| `Equipment/` | 装备定义/实例/管理组件、QuickBar |
| `Feedback/` | ContextEffects（脚步/命中特效音效）、NumberPops（伤害数字） |
| `GameFeatures/` | GameFeature Action |
| `GameModes/` | GameMode/GameState、Experience 定义与管理 |
| `Hotfix/` | 热更新 |
| `Input/` | InputConfig、InputComponent、InputModifiers、按键映射 |
| `Interaction/` | 交互接口 + 交互 Ability + AbilityTask |
| `Inventory/` | 物品定义/实例/管理组件 |
| `Messages/` | Gameplay 消息（依赖 `GameplayMessageRouter` 插件） |
| `Performance/` | 性能与画质缩放 |
| `Physics/` | 碰撞通道、带 Tag 的物理材质 |
| `Player/` | PlayerController、PlayerState、LocalPlayer、CheatManager、Spawning |
| `Replays/` | 回放 |
| `Settings/` | 用户设置 |
| `System/` | AssetManager、GameInstance、GameData、GameplayTagStack、ReplicationGraph |
| `Teams/` | 阵营接口、Subsystem、TeamInfo、显示资产 |
| `Tests/` | 自动化测试 |
| `UI/` | CommonUI 相关 |
| `Weapons/` | 武器实例、远程武器 Ability、WeaponStateComponent |

## 常查文件定位

GAS：

- `AbilitySystem/LyraAbilitySystemComponent.h/.cpp` — ASC 派生，输入按下/释放缓存、AbilityTagRelationship、`CancelAbilitiesByFunc`
- `AbilitySystem/LyraAbilitySet.h/.cpp` — 一次性授予 Ability/Effect/AttributeSet 并可整组回收（`FLyraAbilitySet_GrantedHandles`）
- `AbilitySystem/Abilities/LyraGameplayAbility.h/.cpp` — Ability 基类，激活策略（`ELyraAbilityActivationPolicy`）、Cost 插件、失败消息
- `AbilitySystem/Abilities/LyraAbilityCost.h` — 可插拔消耗策略基类
- `AbilitySystem/Attributes/LyraAttributeSet.h` — AttributeSet 基类与 `ATTRIBUTE_ACCESSORS` 宏
- `AbilitySystem/Attributes/LyraHealthSet.h/.cpp` — Health/MaxHealth + Damage/Healing 元属性 + 死亡委托
- `AbilitySystem/Attributes/LyraCombatSet.h` — BaseDamage/BaseHeal
- `AbilitySystem/Executions/LyraDamageExecution.cpp` — 伤害结算（含距离衰减、AbilitySourceInterface）
- `AbilitySystem/LyraGameplayEffectContext.h` — 自定义 EffectContext，携带 AbilitySource 与命中结果
- `AbilitySystem/LyraAbilityTagRelationshipMapping.h` — Tag 之间的阻断/取消关系表
- `AbilitySystem/LyraGlobalAbilitySystem.h` — 向全部 ASC 广播 Ability/Effect 的 WorldSubsystem
- `AbilitySystem/Phases/LyraGamePhaseSubsystem.h` — 用 Ability 表达游戏阶段

角色与组件：

- `Character/LyraCharacter.h/.cpp` — 角色本体，本身不持有 ASC，通过 PawnExtensionComponent 取
- `Character/LyraCharacterWithAbilities.h` — 直接内嵌 ASC 的变体（单机/简化场景更接近 GGYGO 现状）
- `Character/LyraPawnExtensionComponent.h/.cpp` — 组件初始化状态机（`InitState`），协调 PawnData/ASC 就绪顺序
- `Character/LyraHeroComponent.h/.cpp` — 玩家专属：输入绑定、CameraMode 选择
- `Character/LyraHealthComponent.h/.cpp` — 把 HealthSet 包装成组件级 API 与死亡流程
- `Character/LyraPawnData.h` — Pawn 定义 DataAsset（Pawn 类、AbilitySet、InputConfig、默认 CameraMode）
- `Character/LyraCharacterMovementComponent.h/.cpp` — CMC 派生

输入与相机：

- `Input/LyraInputConfig.h` — InputAction 到 GameplayTag 的映射表
- `Input/LyraInputComponent.h` — 按 Tag 批量绑定 Ability 输入
- `Camera/LyraCameraMode.h/.cpp` — CameraMode 栈与混合
- `Camera/LyraCameraMode_ThirdPerson.h/.cpp` — 第三人称模式，含穿透规避

框架：

- `GameModes/LyraExperienceDefinition.h` — Experience 定义
- `GameModes/LyraExperienceManagerComponent.h/.cpp` — Experience 加载与就绪广播
- `System/LyraAssetManager.h/.cpp` — AssetManager 派生与启动任务
- `System/GameplayTagStack.h` — Tag 计数堆栈容器
- `Teams/LyraTeamSubsystem.h/.cpp` — 阵营查询与敌我判定

## 关键插件依赖

Lyra 的组件化和消息机制依赖以下插件，照搬前必须确认 GGYGO 已启用并在 `GGYGO.Build.cs` 声明对应模块：

- `ModularGameplay`（引擎自带）— `UGameFrameworkComponentManager`、`UPawnComponent`，是 Lyra 组件扩展的基础
- `ModularGameplayActors`（Lyra 插件）— `AModularCharacter`、`AModularPlayerController` 等基类
- `GameplayMessageRouter`（Lyra 插件）— `UGameplayMessageSubsystem`
- `GameFeatures`（引擎自带）— Experience/GameFeature 插件化
- `CommonUI` / `CommonGame` / `CommonUser`（UI 与用户会话，动作单机项目通常不需要）
