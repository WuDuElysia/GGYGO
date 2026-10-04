# 全模块自查原始结论存档


## GGYGO｜动画模块（资产工具）

## 范围与结论

**结论：部分符合。**

已完整读取最新 AGENTS.md，并检查当前工作区（含未提交增量）的 Kevin 动画生成器、根运动工具、动画导入/烘焙/验证脚本、配置、Notify 接缝及实施文档。本轮未修改文件，未操作 UE、构建或运行生成器。

## 主要发现

### 1. [P1] 根运动修改器不满足撤销与重应用契约

位置：[RootMotionBakeModifier.cpp:215](/F:/ue_project/GGYGO/Source/GGYGOEditor/Private/RootMotionBakeModifier.cpp:215)，`OnRevert_Implementation`。

- **事实：**撤销无条件删除四条同名曲线，不区分 `bVerifyOnly`、`bBakeCurves`，也不恢复剥离的骨骼位移。已核对 UE 实现：重应用会先调用旧实例的 `OnRevert`。
- **影响：**仅分析后撤销也可能删除已有曲线；烘焙并剥离后再次应用，会先删曲线，再因净位移已经归零而跳过重建。
- **最小建议：**诊断入口与修改操作分开；修改器记录并恢复原始骨轨及曲线，或改为生成独立派生资产。涉及 Animation 资产工具。

### 2. [P1] 再生成会覆盖已保存的蓝图表现与 Notify 编辑

位置：[KevinCombatAssetBuilder.cpp:297](/F:/ue_project/GGYGO/Source/GGYGOEditor/Private/KevinCombatAssetBuilder.cpp:297)，`BuildAnimBP`；同文件第 138 行 `Notifies.Reset()`。

- **事实：**只检查所有权标记和脏包；已有 ABP 的全部 AnimGraph 节点仍被删除并重建，Montage 的全部 Notify 也被清空。
- **影响：**人工编辑保存后便能通过脏包检查，下一次生成会丢失修改。固定 C++ 脚手架因此持续覆盖本应由蓝图/资产维护的表现内容。
- **最小建议：**已有资产默认只读核验；更新必须检测生成基线差异，或仅更新明确由工具管理的子图/轨道。涉及 Animation。

### 3. [P1] 派生运动资产允许覆盖未保存编辑

位置：[KevinMotionAssetBuilder.cpp:73](/F:/ue_project/GGYGO/Source/GGYGOEditor/Private/KevinMotionAssetBuilder.cpp:73)，`CanWrite`；写入路径位于第 216、228、244 行。

- **事实：**准入只检查 metadata，没有检查脏包；随后复制覆盖派生序列、清空曲线并保存 Profile。
- **影响：**自有资产上的未保存修改可能被覆盖；保存 Profile 还可能夹带其他尚未准备保存的字段，资产所有权与当前编辑所有权没有区分。
- **最小建议：**写前统一检查实际类型、脏包和生成基线；仅更新工具负责的字段。涉及 Movement，Animation 消费其产物。

### 4. [P2] 烘焙进度缓存缺少失效和重试机制

位置：[bake_anim_rootmotion_curves.py:367](/F:/ue_project/GGYGO/AAADocs/Scripts/bake_anim_rootmotion_curves.py:367)，`run`。

- **事实：**按片段名称把 `done/missing/failed` 全部排除，没有源摘要、工具版本或资产重导入校验。
- **影响：**源数据变化、缺失资产补齐或失败原因修复后，重新运行仍会跳过；缓存成为与实际资产不一致的完成状态。
- **最小建议：**缓存关联源摘要与配置版本，只跳过经过核验的成功项；失败和缺失项支持重试。

### 5. [P2] 保存失败可能仍被报告为完成

位置：[bake_anim_rootmotion_curves.py:395](/F:/ue_project/GGYGO/AAADocs/Scripts/bake_anim_rootmotion_curves.py:395)、[import_bh3_kevin_demonbattle.py:218](/F:/ue_project/GGYGO/AAADocs/Scripts/import_bh3_kevin_demonbattle.py:218)。

- **事实：**忽略 `save_loaded_asset` 的布尔返回值；烘焙脚本随后记入 `done`，导入脚本按 `imported` 汇总完成状态。
- **影响：**保存返回 `false` 而未抛异常时，报告会把内存中的成功误当成持久化成功。
- **最小建议：**检查保存结果，失败保留原因；成功保存及必要回读后再标记完成。**本次未发现或断言此前实际资产已经丢失。**

## 合理设计与拆分判断

- `GGYGOEditor → GGYGO` 依赖方向清楚，未发现运行时反向依赖编辑器。
- Notify 只发送 GameplayEvent，没有重复实现伤害、位移或招式状态机。
- 源证据审计与人工窗口配置分离，符合来源和业务配置的边界。
- 派生姿态与位移曲线成对生成是合理职责；多个离线工具不等于重复运行时执行器。
- TurnBack 工具有显式覆盖入口和写前/写后验证，**无需仅因文件较长机械拆分**。将纯轨迹计算、验证与 UE 保存适度分开属于可测试性优化候选。

## 未验证边界与文档

未验证资产再生成、实际 Socket、ABP 播放、命中或取消清理。完整构建成功不能替代这些验收。

文档没有把动态验收写成已完成；但 [Kevin战斗动画实施.md:3](/F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/Kevin战斗动画实施.md:3) 仍写“待统一编译”，落后于统筹报告的构建结果。后续合并应只更新编译状态，保留资产与动态验收待完成状态。

## GGYGO｜地编模块

## 静态审查结论：部分符合

已检查当前工作区的地编创建/验证脚本、地图默认配置、GameMode 装配入口，以及未提交的 Kevin 接线/观察脚本相关边界。**发现两项工具生命周期问题，未发现所查路径新增重复的 Gameplay 执行链。**

### 主要发现

1. **[P2] 移动验证器缺少单实例约束和可靠清理。**  
   [verify_movement_test_level.py:45](F:/ue_project/GGYGO/AAADocs/Scripts/verify_movement_test_level.py:45) 的 `finish()` 先访问输入子系统，再恢复后台节流；若提前结束 PIE 导致对象失效，第一步异常会阻断恢复。第 53 行重复执行还会创建多个探针，同时注入输入、覆盖报告，并分别恢复同一个全局设置。  
   **违反点：**资源所有权、有效期和失效清理不完整。  
   **最小建议：**地编验证工具增加单实例入口、幂等停止与回调注销；输入释放、设置恢复、报告落盘分别保证异常清理。无需修改 Movement 的执行机制。

2. **[P2] 建图脚本在依赖核对完成前产生持久化结果。**  
   [create_movement_test_level.py:17](F:/ue_project/GGYGO/AAADocs/Scripts/create_movement_test_level.py:17) 先创建地图，第 76 行保存后才解引用 Experience、Roster 和 PawnData 配置。缺失引用可能让脚本在保存后失败，而再次运行又因地图已存在被拒绝。  
   **违反点：**生产工具缺少完整的前置校验和失败恢复路径。  
   **最小建议：**地编脚本在建图前核对 GameMode、Experience 及本测试要求的 PawnData 字段；报告明确区分创建、保存和配置核验结果，保留可检查的失败状态。

### 合理设计，无需拆分

- 地图通过现有 GameMode 装配玩家；[SpawnSquadForPlayer](F:/ue_project/GGYGO/Source/GGYGO/GameModes/GGYGOGameMode.cpp:190) 继续负责编队来源、出生点及 Slot/Avatar 装配，地编没有复制该逻辑。
- 验证器通过 `IA_Move` 注入请求、读取 CMC/Animation 状态，没有直接写角色位置、速度或步态。
- 地面、网格材质、灯光和出生点属于同一测试场景的创建职责；当前规模无需机械拆成多个模块。
- [默认配置](F:/ue_project/GGYGO/Config/DefaultEngine.ini:8) 仍指向 `Untitled`。Kevin 接线与验证文档明确保留运行验证待办，没有据此宣称关卡验收完成。

### 验证边界与任务状态

本次只读审查完成，未修改文件、操作 UE、重建地图或执行编译。二进制地图/蓝图内部接线未重新读取；既有 PIE 报告属于历史证据，不能覆盖当前未提交代码的运行结果。

用户“现在 MCP 开了”触发的是独立连通性检查，结果为本地端口连接被拒绝；**不影响上述静态审查结论。**

我检查了：`unreal_mcp` 配置已启用，但 `http://127.0.0.1:8000/mcp` 目前返回“连接被拒绝”，还没连通。

请确认 UE 中的 MCP 服务已启动，并监听 **8000 端口**。


这是修复前审计证据，不代表当前修复状态。当前状态以 Module_Audit_Repair_Ledger.md 为准。不会因后续修复回写篡改原始结论。

## GGYGO｜AbilitySystem 模块

会话：01a0e5b5-1b3a-7783-a667-e8e38d7a72fb

结论：**部分符合**。核心职责已有清晰归属，但通用 ASC 与具体连段业务存在反向依赖，资源清理和组仲裁还有契约缺口。

审查范围覆盖当前工作区的 ASC、组规则、Ability 基类、AbilitySet、两类 AbilityTask、Cost、EffectContext、Execution、AttributeSet 和 Cue；检查了 BossMelee、Trace 的未提交增量及玩家连段调用契约，并核对计划蓝图、AbilitySystem 笔记和六张 Canvas。以下均为静态审查发现，未作运行复现。

1. **[P2 · 问题] 能力结束会清除其他能力的相机偏移。**  
   位置：[GGYGOGameplayAbility.cpp:539](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp:539)，`ClearCameraOffset/EndAbility`；[GGYGOCameraComponent.cpp:62](F:/ue_project/GGYGO/Source/GGYGO/Camera/GGYGOCameraComponent.cpp:62)。  
   基类 `EndAbility` 无条件清偏移，CameraComponent 只保存一份偏移，没有所有者校验。能力 A 设置偏移后，共存且从未申请偏移的能力 B 结束，也会撤销 A 的效果。这违反“GA 只清理自己所持资源”的生命周期边界。最小改进是偏移申请返回所有权句柄，释放时匹配所有者；涉及 **AbilitySystem、Camera**。[结构文档第 21 行](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/AbilitySystem/结构.md:21) 将微调也描述为 SpecHandle 所有权，需要随修复同步纠正。

2. **[P2 · 问题] Montage Task 的提前结束路径遗漏根运动缩放恢复。**  
   位置：[GGYGOAbilityTask_PlayMontageAndWaitForEvent.cpp:192](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.cpp:192)，`StopPlayingMontage`。  
   `Activate` 写入角色缩放，恢复仅在 `OnMontageBlendingOut` 中执行；取消或能力提前结束时，`StopPlayingMontage` 先解绑该回调再停止动画，`OnDestroy` 没有补偿恢复。配置非 1 缩放后提前结束，可能影响后续根运动。最小改进是集中管理缩放释放，在正常混出、取消和销毁路径按播放实例所有权幂等恢复。涉及 **AbilitySystem Task、Animation/Movement 接缝**；当前两个近战调用方使用默认 1，不能据此声称已出现可见故障。

3. **[P2 · 问题] 组准入允许替换，实际取消却可能失败。**  
   位置：[GGYGOGameplayAbility.cpp:178](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp:178)，`SetCanBeCanceled`；[GGYGOAbilitySystemComponent.cpp:440](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp:440)，同组准入；[同文件:120](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp:120)，取消执行。  
   Exclusive 能力允许设为不可取消；SingleInstance 准入只比较优先级，新能力先登记，取消旧能力失败时仅记录日志。因而低优先级、不可取消的 Exclusive 与获准的新能力可能同时留在单实例组。规则判定与执行结果不一致。最小改进是明确不可取消占用者的准入政策，并让检查与取消使用同一冲突判定；涉及 **ASC、Ability 基类**。这是现有接口允许的配置缺口，未确认当前资产已触发。

4. **[P2 · 架构问题] 通用 ASC 直接依赖玩家连段具体类型和协议。**  
   位置：[GGYGOAbilitySystemComponent.h:117](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h:117)，`ClientCorrectComboStep`；[GGYGOAbilitySystemComponent.cpp:166](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp:166)。  
   ASC 声明段序、窗口等业务字段，并强转 `UGGYGOPlayerComboAbility` 调用纠正函数。连段协议变化需要修改所有角色共用的基础设施，违反通用底层不依赖具体招式业务的约束。最小拆分边界是：ASC 保留网络路由及 SpecHandle/激活键校验，连段协议和解释归专用扩展或任务，通过明确接口分发。涉及 **AbilitySystem、战斗连段**，无需拆整个 ASC。

5. **[P2 · 接口问题] 当前近战 Cue 调用没有提供表面分流所需标签。**  
   位置：[GGYGOGameplayCueNotify_HitImpact.cpp:45](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Cues/GGYGOGameplayCueNotify_HitImpact.cpp:45)；调用方为 [BossMelee.cpp:283](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp:283)、[PlayerCombo.cpp:324](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp:324)。  
   HitImpact 仅从 `AggregatedTargetTags` 选择表面效果；两处调用手工构造 Cue 参数，没有填该字段，Cue 也不从 Context 的命中材质补取标签。因此这些调用即使配置了表面效果表，也会走默认项。最小改进是统一命中参数构造契约，明确材质标签的提供方并复用；涉及 **AbilitySystem/Cue、Combat、Physics**。仅增加表现资产不能补齐此接缝。

明确无需拆分的合理设计：

- ASC 的输入缓存、组仲裁、Tag 关系都围绕 GAS 准入工作；没有发现另建帧调度器或第二份待激活队列。
- 组规则资产与 GA 自身优先级分别表达组规则和个体配置，职责合理。
- Execution 计算、HealthSet 落属性、Cue 做表现的分工成立；目前没有证据要求机械拆分 Health/Poise。
- Montage 播放与事件监听共用一个 Task 生命周期有合理依据，应先补清理契约。
- AbilitySet 的授予记录、任务句柄和窗口缓存属于必要资源记录；BossMelee 当前增量通过 CMC 句柄请求位移，超时计时器只做异常兜底。

**候选优化**：以后相机表现扩展明显增多时，可从 Ability 基类提取专用资源管理对象；当前不必仅因文件较长就拆分。

文档对玩家 P3/P4、Kevin 接线和联机仍标注待验收，没有把完整构建等同动态通过。另有旧描述需后续同步，例如 [AbilitySet.h:14](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySet.h:14) 仍称 Pawn 自持 ASC；[模块参考.md:115](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/模块参考.md:115) 称“挥刀时快照”，当前近战实际在命中回调创建 Spec。

本轮未修改文件、提交或推送，未操作 UE、构建或运行测试。已读的连段测试只覆盖窗口/缓存，Boss 新测试针对结束重入；本报告中的并发、取消恢复、Cue 表现、具体 Cost 和联机行为仍需后续专项验证。

---

## GGYGO｜Input 模块

会话：01a0e5b5-276c-7ea0-b469-4797f5059e2b

结论：**部分符合新规范**。输入、移动执行与 GAS 仲裁的主边界清晰，但绑定重入、重试状态和 ASC 生命周期存在缺口。

已完整读取 `AGENTS.md`，审查 `Source/GGYGO/Input` 全部文件、HeroComponent 输入与意图逻辑、PlayerController 帧末消费；交叉检查 ASC、PawnExtension、CharacterBase、换人流程、连段 GA，以及 Input 文档和两张 Canvas。主审文件当前无未提交改动；已检查相关 CMC 未提交增量。

以下是本轮最高价值的 5 项发现，均为代码或文档事实；运行影响尚未通过动态复现确认。

1. **[P2｜问题] Native 输入绑定不具备重入幂等性。**  
   位置：[HeroComponent.cpp:287](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp:287)、[InputComponent.h:57](F:/ue_project/GGYGO/Source/GGYGO/Input/GGYGOInputComponent.h:57)，`InitializePlayerInput` / `BindNativeAction`。初始化只移除 Ability、ForceWalk 句柄，随后重新绑定 Move、Mouse、Stick；后三者的句柄没有保存。InitState 和 [CharacterBase.cpp:136](F:/ue_project/GGYGO/Source/GGYGO/Character/GGYGOCharacterBase.cpp:136) 都可进入初始化。对同一 InputComponent 再次初始化会累积回调，造成视角增量重复、移动输入重复提交，违反资源生命周期与清理责任要求。  
   **最小建议：**统一记录本组件全部绑定句柄，并记录其所属 InputComponent；重绑前在原组件上解绑。涉及 Input、Character。

2. **[P2｜问题] 重试订阅没有跟随 ASC 的就绪、替换和失效。**  
   位置：[HeroComponent.cpp:412](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp:412)，`BindAbilityRetryDelegates`。该函数只在输入初始化末尾调用；ASC 尚未就绪时直接返回，已绑定后又只凭永久布尔值跳过。没有保存订阅来源 ASC，也没有退订和重置 `BufferedInputs` 的对应路径。[EndPlay:72](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp:72) 同样没有处理。  
   这使晚到的 ASC 可能漏订阅；同一 Hero 更换 ASC 后仍可能响应旧来源通知、却向当前 ASC 重交缓存。违反缓存来源、有效期和失效清理要求。  
   **最小建议：**接入 PawnExtension 已有的 [ASC 初始化/反初始化通知](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp:378)，保存弱 ASC 与委托句柄，失效时退订并清空重试状态。涉及 Input、Character、AbilitySystem。

3. **[P2｜问题] 激活重试会制造不存在的“持续按住”状态。**  
   位置：[HeroComponent.cpp:493](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp:493)，`HandleAbilityGroupFreed`；[ASC.cpp:147](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp:147)，`AbilityInputTagPressed`。重试通过按下接口提交，而该接口同时写入 pressed 和 held。若玩家已松键，随后组释放触发重试，held 会被重新加入，却没有配对的释放事件；`WhileInputActive` 能力可能继续尝试激活。意图请求因此改变了物理输入事实，违反状态归属要求。  
   **最小建议：**由 ASC 提供只排入待激活请求的重试入口，继续在原有 `ProcessAbilityInput` 中消费，保持 held 只受真实输入影响。涉及 Input、AbilitySystem。

4. **[P2｜问题] Pawn 输入初始化清除了整个 LocalPlayer 的映射。**  
   位置：[HeroComponent.cpp:251](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp:251)，`InitializePlayerInput`。代码执行 `ClearAllMappings()`，随后只恢复 `DefaultInputMappings`。因此其他来源注册的 UI、交互或 GameFeature IMC 会被一并移除；当前是否已有此类运行时注册者未验证。该操作超出了 Hero 对自身输入资源的管理边界。  
   **最小建议：**记录本次注册的 Subsystem 与 IMC，只增删自身负责的映射；共享 IMC 明确唯一管理者。涉及 Input，未来与 UI/GameFeature 协调。

5. **[P2｜文档问题] 输入计划仍将组排队写成普攻连段实现。**  
   位置：[计划_输入与意图.md:94](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Input/计划_输入与意图.md:94)。该段声称第二段因组占用进入 Hero 缓冲、第一段结束后重试成功。但当前活跃 Spec 的输入进入 GA，[PlayerComboAbility.cpp:184](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp:184) 管理连段请求和窗口；[Input/结构.md:3](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Input/结构.md:3) 也明确 Hero 只负责激活失败重试、GA 蓝图尚待配置。旧描述与当前实现及验收边界矛盾，容易诱导继续构建第二套连段链路。  
   **最小建议：**删除或标记旧方案，引用当前连段计划，保留 GA/ABP 接线和动态验收未完成状态。涉及 Input 文档、AbilitySystem 文档。

**明确无需拆分的合理设计：**

- `InputConfig` 管数据映射、`InputComponent` 管绑定工具，规模和职责都适当。
- PlayerController 是检索到的唯一 `ProcessAbilityInput` 调用方；无需新增 Tick 或帧调度器。
- Hero 经 `AddMovementInput`、`SetForceWalkRequested` 提交请求，CMC 持有移动与预测状态，没有在 Input 复制移动状态机。
- Hero 的激活失败缓存与 GA 的活跃连段窗口用途不同，不能仅因都有“缓存”便认定重复职责。
- 输入映射、触发器、IMC、缓冲窗口已有资产或可编辑配置入口，未发现具体角色/招式硬编码。

**候选优化：**Hero 同时承担输入会话和相机覆盖仲裁，存在独立变化方向；目前尚不足以要求立即拆类。若输入生命周期继续扩展，可优先提取绑定、订阅和清理责任，Hero 保留装配协调。

本轮未修改文件、提交或 push，未操作 UE、PIE 或构建。未验证蓝图资产当前接线、实体设备、暂停/焦点切换、重新附身及网络运行行为。已有完整构建通过不能覆盖这些边界。

---

## GGYGO｜Character 模块

会话：01a0e5b5-36b6-7c81-b10f-f10d5758423d

结论：**部分符合新规范**。Character 的主要职责划分合理，但初始化与卸载存在缺口，通用角色类仍依赖具体角色表现，部分文档与源码不一致。

范围：完整读取 `AGENTS.md`；审查 CharacterBase、HeroCharacter、PawnData、PawnExtension、Health，检查 CombatantState、Teams、GAS、Input、CMC 的相关接缝；包含当前未提交的 Movement、渲染增量。核对 Character 结构文档、计划、两张 Canvas 及实施状态。以下均为静态审查发现，未声称动态复现。

1. **[P2｜问题] Health 的死亡阶段与 ASC Tag 可能失去一致性。**  
   位置：[GGYGOHealthComponent.cpp:103](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHealthComponent.cpp:103)，`InitializeWithAbilitySystem`、`StartDeath`。  
   事实：初始化无条件清除死亡 Tag；`StartDeath` 可以在 ASC 为空时推进 `DeathState`，之后不会在 ASC 到达时补齐 Tag。若死亡复制先于外部宿主绑定，便可能出现“组件已死亡、ASC 无死亡 Tag”。这违反派生状态必须有明确同步机制的要求，可能使死亡表现与能力阻断判断不一致。最小改进：将 Tag 同步集中为依据 `DeathState` 的幂等操作，绑定 ASC 后补齐；不要重复广播死亡表现。涉及 **Character／GAS**。

2. **[P2｜问题] Avatar 已改变时，旧 Pawn 的本地清理通知被跳过。**  
   位置：[GGYGOPawnExtensionComponent.cpp:188](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp:188)，`UninitializeAbilitySystem`。  
   事实：卸载广播位于“ASC 当前 Avatar 仍是本 Pawn”的条件内；条件不成立时只清空 PawnExtension 指针。Health 的解绑和 [CMC 的 ASC 缓存清理](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:449)依赖该广播，因此这条分支会留下旧订阅或缓存。它违反缓存失效与清理责任要求。最小改进：分开“清理共享 ASC”和“撤销本地绑定”；后者应覆盖所有已绑定路径，同时防止旧 Health 清掉新 Avatar 的 Tag。涉及 **Character／Combatants／Movement**。

3. **[P2｜问题] 输入初始化错误地假定 PawnData 到达就意味着 ASC 已绑定。**  
   位置：[GGYGOHeroComponent.cpp:305](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp:305)、[同文件:412](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp:412)，`InitializePlayerInput`、`BindAbilityRetryDelegates`。  
   事实：InitState 守卫没有等待 ASC；重试委托仅在输入初始化时尝试绑定，ASC 为空便返回，没有订阅 ASC 就绪通知来补绑。成功后又只用一个布尔值记录，未随 ASC 卸载重置。客户端先得到 PawnData／输入组件、后得到宿主绑定时，能力输入重试可能一直缺失；重新绑定 ASC 时也可能沿用旧状态。最小改进：让这些委托跟随 PawnExtension 的 ASC 初始化／卸载事件成对绑定、解绑，并记录实际绑定对象。涉及 **Character／Input**，由 Input 会话合并处理。

4. **[P2｜问题] 通用 HeroCharacter 默认装配 Pyrios 专用表现组件。**  
   位置：[GGYGOHeroCharacter.cpp:26](F:/ue_project/GGYGO/Source/GGYGO/Character/GGYGOHeroCharacter.cpp:26)。  
   事实：所有 HeroCharacter 都创建 `UGGYGOPyriosRenderComponent`，再由该组件识别模型名称决定是否应用。通用玩家角色因此直接依赖具体角色表现，违反“角色差异通过配置、组合或扩展点提供”的规则。最小改进：将专用组件装配移到 Pyrios 蓝图或专用派生类；若需要共享机制，再由渲染模块提供通用组件和配置。涉及 **Character／渲染**，本轮未审查渲染算法。

5. **[P2｜文档问题] Character 文档包含过期的当前事实和初始化因果描述。**  
   位置：[计划_角色与组件.md:228](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Character/计划_角色与组件.md:228)、[同文件:240](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Character/计划_角色与组件.md:240)、[初始化 Canvas:46](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Character/GGYGO_流程_角色初始化.canvas:46)。  
   事实：文档称 HealthComponent 持有破韧状态，实际只转发事件；仍将 `AnimationStateFrame` 写成目标，当前已有通用帧和兼容适配；流程图把 Health 绑定放在 InitState 推进步骤，实际由 ASC 初始化广播触发。它们会误导状态所有权和时序判断。最小改进：同步上述事实，并明确 InitState 与 ASC 绑定是需要协调的两条路径。涉及 **Character／Animation**。实施状态明确记录 `GA_Death` 为占位、死亡及 DS 验收待完成，未发现这部分被写成已验收。

明确无需拆分的设计：CharacterBase 作为组件装配与生命周期转发入口、PawnExtension 统一协调外部 ASC、PawnData 聚合静态配置，以及 HealthSet 管数值／HealthComponent 管流程与事件，均有清晰边界；没有必要机械拆文件或引入第二套调度器。HeroComponent 的输入与相机覆盖是否进一步拆分属于**候选优化**，目前不能仅凭职责数量判定必须拆。

验证边界：两张 Canvas 的 JSON、ID 唯一性和边引用检查通过。本轮没有修改文件、提交、推送、操作 UE、构建或运行测试；蓝图实际死亡接线、复制乱序、Avatar 更替和输入恢复仍需后续动态验收。已有完整构建通过不能替代这些验收。

---

## GGYGO｜Camera 模块

会话：01a0e5b5-4490-7881-b890-15d19208ca68

结论：**部分符合**。Camera 的模块边界和配置分层基本合理，但能力镜头资源的所有权、Avatar 更替清理及最终位置碰撞存在缺口。

审查范围：Camera 全部六个源码文件，Hero 模式覆盖、GA CameraOffset 接缝、PawnExtension/ASC 的 Avatar 生命周期，以及 Camera 文档和四张 Canvas。已检查当前工作区与未提交增量；Camera、Hero、GA 基类本轮没有未提交改动，邻接的 Boss GA 增量仍调用基类激活与结束入口。

1. **P1｜无关能力结束会撤销当前 CameraOffset。**  
   [GGYGOGameplayAbility.cpp:539](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp:539) 的 `ClearCameraOffset` 不检查申请者，`EndAbility` 在第 552 行无条件调用它；[GGYGOCameraComponent.cpp:62](F:/ue_project/GGYGO/Source/GGYGO/Camera/GGYGOCameraComponent.cpp:62) 的偏移槽也不记录所有者。因此 A 正在使用偏移时，即使 B 从未申请镜头，B 结束仍会使 A 的偏移回落。这违反“GA 只清理自己持有资源”的约束。最小建议：保留现有单槽策略，增加申请令牌和匹配撤销，GA 保存自己取得的令牌。涉及 **AbilitySystem、Camera**。

2. **P2｜跨 Avatar 存活的能力没有可靠的镜头释放对象。**  
   [GGYGOPawnExtensionComponent.cpp:194](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp:194) 明确保留 `SurvivesDeath` 能力；但 [GGYGOGameplayAbility.cpp:517](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp:517) 撤销模式时重新查询当前 Avatar，`OnPawnAvatarSet`（第 439 行）也只转发蓝图事件。[GGYGOHeroComponent.cpp:72](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp:72) 仅在 EndPlay 整体清空覆盖。若旧 Pawn 保留、能力跨 Avatar 继续运行，旧覆盖可能遗留，结束时又操作新 Avatar 的相机。缺失的是资源绑定对象及失效时机。最小建议：申请时保存原接收组件的弱引用与令牌，在 Avatar 解绑时明确释放；跨 Avatar 是否重新申请另定策略。涉及 **Character、AbilitySystem、Camera**，该触发场景未动态复现。

3. **P2｜碰撞约束没有覆盖最终镜头位置。**  
   [GGYGOCameraMode_ThirdPerson.cpp:58](F:/ue_project/GGYGO/Source/GGYGO/Camera/GGYGOCameraMode_ThirdPerson.cpp:58) 对单个模式位置球扫；之后 [GGYGOCameraMode.cpp:37](F:/ue_project/GGYGO/Source/GGYGO/Camera/GGYGOCameraMode.cpp:37) 混合位置，[GGYGOCameraComponent.cpp:104](F:/ue_project/GGYGO/Source/GGYGO/Camera/GGYGOCameraComponent.cpp:104) 再加局部偏移，最终输出不再校验。位置偏移可把已避障的镜头推回墙内，两个安全机位之间的混合位置也未必安全。安全校验的责任范围因此不完整。最小建议：由 Camera 明确统一的最终位置碰撞入口，让混合与位置微调纳入同一约束；避免各 GA 各自补球扫。涉及 **Camera**，贴墙与切模式表现未实测。

4. **P3｜两处 Canvas 把未接通的行为描述为当前实现。**  
   [结构 Canvas:11](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/GGYGO_结构_相机.canvas:11) 写“Avatar 切换时清空”，当前清栈调用只见 Hero EndPlay；[流程 Canvas:86](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/GGYGO_流程_相机.canvas:86) 写“委托返回空类即走 Super”，实际 [GGYGOCameraComponent.cpp:53](F:/ue_project/GGYGO/Source/GGYGO/Camera/GGYGOCameraComponent.cpp:53) 只是跳过 Push，已有栈仍继续求值。会误导生命周期与兜底验收。最小建议：按当前行为修正文档，将缺少的切换清理明确列为缺口。手柄、遮挡测试和跑动侧移的暂停状态在实施记录中区分正确。

**目前无需拆分的设计：**

- Hero 覆盖列表负责能力所有权，CameraModeStack 负责画面混合，两者没有重复权威状态。
- Component、Mode、ThirdPerson、Stack 分工明确；Mode 与 Stack 同文件不足以构成拆分理由。
- Camera 通过委托取得模式类，没有反向依赖 Hero/GAS，也没有新增帧调度器。
- C++ 保存通用求值算法，可调参数通过 Class Defaults/PawnData 提供，未发现具体角色业务硬编码。

候选优化与已确认问题分开：同帧多次取视图的重复推进、复用模式缓存的重置策略、替换 Offset 时的过渡连续性，值得后续验证，但本轮不认定为已发生故障。

本轮未操作 UE、构建或运行测试，也未修改任何文件。未重新检查蓝图内部图表和运行时资产值；未验证网络预测、并发能力、Avatar 切换及碰撞场景。已有完整 Editor 构建通过不覆盖这些动态边界。

---

## GGYGO｜Animation 模块

会话：01a0e5b5-766b-7ac0-9edf-254f3964f543

审查范围：`Animation/Runtime`、`zzzAnim`、语义帧与表现记忆、Pyrios 动画接缝，以及相关 Movement 未提交增量和架构笔记。已完整读取当前 AGENTS.md。

**结论：部分符合。** 语义抓帧、玩法权威与表现层的基本分工清楚；仍有以下 4 项实际缺口。

1. **[P1｜问题] 移动权威仍依赖当前动画求值，运行时依赖环未解除。**  
   [CMC::SampleAnimCurves](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:374) 从 AnimInstance 采样曲线，供速度和 TurnBack 相位使用；[StateCapture::Capture](F:/ue_project/GGYGO/Source/GGYGO/Animation/Runtime/GGYGOAnimationStateCapture.cpp:53) 又把 CMC 结果送回 AnimBP。修改表现资产、混合或动画求值条件仍可能改变胶囊运动，违反权威执行与表现职责分离。未提交的 ActionMotion 增量只在该动作有效期间暂停反读，尚未覆盖普通走跑与转身。最小改进方向：由 Movement 持有可独立采样的转身/刹停数据及时钟，Animation 消费动作事实。涉及 **Movement、Animation**；属于已知迁移债务，需要统筹实施。

2. **[P2｜问题] 起步早停窗口在 C++ 中另行计时，不能可靠代表动画进度。**  
   [AdvanceStopSelection](F:/ue_project/GGYGO/Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.cpp:17) 根据移动输入边沿启动窗口，每帧累加；[窗口常量](F:/ue_project/GGYGO/Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionRules.h:30) 硬编码为 **0.3 秒**，并直接映射 Stop 分支索引。它不知道 EnterMove 是否实际进入、播放速率或是否被打断，且未使用快照中的接地/禁移状态。换动画或调整拓扑后，Stop 选择可能与正在播放的阶段失配，违反常改表现时序优先由蓝图/资产拥有的规则。建议把窗口与 Stop 选择交给实际动画状态时间；保留通用插值计算即可。涉及 **Animation**。

3. **[P2｜问题] 表现记忆缺少重新初始化时的失效清理。**  
   [NativeInitializeAnimation](F:/ue_project/GGYGO/Source/GGYGO/Animation/Runtime/GGYGOAnimInstanceBase.cpp:9) 只刷新 Owner 与语义帧；[UZZZAnimInstance](F:/ue_project/GGYGO/Source/GGYGO/Animation/zzzAnim/ZZZAnimInstance.h:73) 只覆盖 Update，没有重置 `StateMemory` 和 [LocomotionEvents 的跨帧状态](F:/ue_project/GGYGO/Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.h:61)。同一实例重新初始化，或 Owner 在连续有输入时切换，可能继承旧混合目标、Stop 分支和起步窗口。违反派生缓存须明确有效期和失效清理的要求。建议提供统一重置入口，在初始化及 Owner 改变时清理，并补充“旧状态→重新初始化→首次移动”的测试。涉及 **Animation**；触发场景尚未动态验证。

4. **[P3｜问题] 架构笔记中的早停时长与当前源码矛盾。**  
   源码上述常量为 **0.3 秒**；[动画计划](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/计划_动画与表现层.md:467) 与 [实施状态](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/计划_实施状态.md:196) 仍写 **0.5 秒**，会误导调参与验收，应同步当前值并继续标明待迁移。除此之外，所查 Animation 文档明确把 Anim-C 剩余项、Locomotion 拆环、玩家普攻接线和动态验收列为未完成，没有据构建通过宣称整体完成。

明确无需拆分的设计：`StateCapture` 集中读取 CMC/ASC、薄 `AnimInstanceBase` 发布只读帧、纯兼容 Snapshot 适配均合理；`GaitBlendY` 是表现插值缓存，不是第二套权威步态；Animation 仅读取转身相位，且查询明确排除 RunOut。无需为这些直接调用增加事件总线，也无需按文件长度继续拆类。

**候选优化：** `AnimSet` 的 FName 查表目前缺少资源完整性校验，可在资产配置边界增加缺键、空引用和骨架兼容检查；本轮没有证据表明现有 Pyrios 配表缺失，因此不列为已发生故障。

本轮仅静态读取，未修改文件、构建、操作 UE 或运行 PIE。当前 ABP 二进制可核到语义查询、表现字段和资源引用，但不能据名表证明逐 Pin 接线；重初始化、打断恢复、TurnBack 重入及联机行为仍需专项验证。现有自动化测试主要覆盖快照字段映射，不能代替这些生命周期验收。

---

## GGYGO｜Movement 模块

会话：01a0e5b5-83e6-70b3-9e67-c9e8547586a4

## 范围与结论

已完整读取 `AGENTS.md`，审查当前工作区（含未提交增量）的 CMC、SavedMove、MovementSet、曲线采样器、两类 RMS、ActionMotionProfile、测试及相关 GA/动画接口和文档。

**结论：部分符合。** 新动作曲线通道职责清晰；旧 locomotion 仍有表现反向驱动运动、配置与清理不一致的问题。本轮未修改文件、操作 UE 或构建。

## 主要发现

### 1. P1：旧曲线链仍形成运行时反馈环

**证据：** [CMC::SampleAnimCurves](/F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:374)、[Sampler::Sample](/F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOAnimCurveSampler.cpp:81)、[AnimationStateCapture](/F:/ue_project/GGYGO/Source/GGYGO/Animation/Runtime/GGYGOAnimationStateCapture.cpp:53)。

- CMC 读取最终 AnimInstance 的混合曲线，动画又根据 CMC 的步态/转身状态选择姿态。
- [UpdateCurveBrake](/F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:909) 将“无输入且曲线有速度”直接认作刹停，没有确认曲线所属动作。
- **影响：** 带相同曲线的攻击或混合过渡可能驱动旧刹停通道；服务器不求值动画时也无法取得同源运动数据。新 ActionMotion 通道只隔离显式申请它的动作。
- **建议：** Movement 与 Animation 先明确旧曲线的合法来源和生命周期，再规划短动作向独立 Profile 迁移。不能仅通过扩大服务器速度上限解决权威来源问题。

### 2. P2：关闭曲线驱动后，TurnBack 仍可接管旋转

**证据：** [UpdateTurnBack](/F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:953)、[PhysicsRotation](/F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:783)。

- `bUseCurveDrivenSpeed=false` 会关闭曲线速度及旧 RMS，却没有阻止 TurnBack 相位进入。
- `PhysicsRotation` 只检查转身相位，仍会绕过普通旋转；没有有效转角曲线时可一直等到超时。
- **影响：** 配置选择固定速度后，角色仍可能发生曲线转向或暂时无法正常转向。
- **建议：** Movement 统一曲线转身的启用判据，覆盖进入、保持、退出和旋转消费，避免各入口分别解释同一配置。

### 3. P2：MovementSet 切换的恢复契约不完整

**证据：** [SetMovementSet / ResetLocomotionState](/F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:460)、[ApplyMovementSetToComponent](/F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:488)。

- 重置仅清步态及输入记忆，没有清 TurnBack 相位、旧 RMS 和曲线基线。转身期间更换配置，旧源可能继续使用创建时缓存的缩放。
- 接口[声明 nullptr 恢复引擎默认值](/F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h:196)，实现却直接返回，保留上一套加速度、摩擦和旋转参数。
- **影响：** 当前资产引用与实际执行参数可能不一致，存在跨配置残留。
- **建议：** 明确一次配置切换应结束哪些 locomotion 资源，并统一默认参数恢复规则。显式 GA 动作仍按其 Handle 所有权处理，避免误清其他模块资源。

### 4. P3：CMC 包含具体 BlendSpace 的轴布局约定

**证据：** [GetLocalVelocityBlend](/F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:1114)。

- 函数因动画资产采用“X 右、Y 前”而交换 UE 局部轴。
- **影响：** 更换动画资产布局需要影响运动接口，表现配置进入通用运动底层。
- **建议：** CMC 发布标准局部速度/方向；轴交换放入 Animation 映射层或 AnimBP。属于小范围职责迁移，不需要新增执行组件。

## 合理设计与候选拆分

- **两类 RMS 无需强行合并。** 旧 RMS 消费当前帧速度/方向，由转身相位或零速结束；新 RMS 消费独立累计曲线，持有有限时间并由 Handle 管理。输入和生命周期确有区别。
- **SavedMove、复制标志和采样基线不是第二套权威状态。** 它们分别服务重演、远端表现和差分，现有用途可以解释。
- **新通道边界合理：** Profile 配置轨迹，RMS 唯一推进动作时间，CMC 管执行/清理，GA 持有 Handle；运行时没有 Kevin 招式分支。
- **CMC 拆分属于候选优化。** 若继续扩展旧 TurnBack，可提取无独立 Tick 的相位解算单元；CMC 继续拥有状态、预测和 RMS 挂卸。当前不应按文件长度机械拆组件。

## 未验证边界

本轮为静态审查，未复现上述动态现象。统一 Editor 构建通过不代表测试、Kevin 派生资产、碰撞或联机已验收。Movement 文档没有把这些写成已完成，但“待构建”状态已滞后，需要根会话统一更新。

---

## GGYGO｜Teams 模块

会话：01a0e5b5-910c-71e3-a75c-b17c22fea33e

结论：**部分符合**。Teams 的状态分层及与 Combatants/BossState 的归属基本合理，但客户端规则初始化、失败回收和切人清理尚有缺口。

本轮完整读取了 `AGENTS.md`，审查 Teams 全部源码、GameMode 装配、Player 保存与附身入口、Combatants/BossState，以及 PawnExtension、ASC 和相关输入链；核对了 Teams 笔记、两张 Canvas 和实施状态。依据当前工作区文件，包含相关未提交代码；Teams 本身没有未提交增量。全程只读，未构建、运行 UE、修改或提交文件。

1. **[P1｜问题] 客户端 Slot 没有应用能力规则配置。**  
   [GGYGOCharacterSlot.cpp:41](F:/ue_project/GGYGO/Source/GGYGO/Teams/GGYGOCharacterSlot.cpp:41) 的 `InitializeForPawnData` 仅服务器执行，其中注入组规则与 Tag 关系表；[GGYGOCharacterSlot.h:72](F:/ue_project/GGYGO/Source/GGYGO/Teams/GGYGOCharacterSlot.h:72) 的 PawnData 只有复制，没有 OnRep 应用入口。ASC 两个配置字段也不复制，缺配置时分别使用默认组规则和空关系表。配置偏离默认值时，客户端预测与服务器会使用不同规则，违反规则唯一且一致的要求。  
   **最小修正：**由 Slot 提供幂等配置应用函数，服务器初始化及 PawnData OnRep 共用；能力授予仍仅服务器执行。涉及 Teams、AbilitySystem。

2. **[P2｜问题] 装配失败及队伍结束缺少明确回收责任。**  
   [GGYGOGameMode.cpp:277](F:/ue_project/GGYGO/Source/GGYGO/GameModes/GGYGOGameMode.cpp:277) 在 Pawn 生成失败后直接 `continue`，此前创建并授予能力的 Slot 没有销毁；[GGYGOSquadComponent.cpp:153](F:/ue_project/GGYGO/Source/GGYGO/Teams/GGYGOSquadComponent.cpp:153) 超限拒绝登记也不返回结果供生成方回滚。当前 GameMode、PlayerState、Squad 未提供队伍销毁链。  
   这使生成方与持有方的资源交接不完整，失败路径可留下未登记的 ASC 宿主；断线后的完整回收也没有项目侧保证。**最小修正：**登记返回成功状态，装配失败回滚 Slot/Pawn，并明确唯一的队伍销毁入口。涉及 GameModes、Teams、Player，宿主解绑复用 Combatants。

3. **[P2｜问题] 切人保留持久状态的同时，也保留了旧输入与运行中的能力。**  
   [GGYGOSquadComponent.cpp:287](F:/ue_project/GGYGO/Source/GGYGO/Teams/GGYGOSquadComponent.cpp:287) 的 `DeactivateSlot` 只隐藏、关闭碰撞和移动；解除附身走 [PawnExtension.cpp:220](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp:220)，只刷新 ActorInfo。旧 ASC 的 held 输入不会清空，而 [PlayerController.cpp:36](F:/ue_project/GGYGO/Source/GGYGO/Player/GGYGOPlayerController.cpp:36) 随后只消费新角色的输入。  
   因而在按住能力键时切人，旧输入可能残留至切回；运行中的任务也没有统一退场处理契约。持久 GE 与当前操作资源的生命周期混在了一起。**最小修正：**建立出战退出通知，由输入层清除旧缓存，由 GA 按明确策略取消或保留能力并释放自身资源。涉及 Teams、Character/Input、AbilitySystem；无需销毁 ASC 或清除冷却。

4. **[P2｜架构问题] 保存层存在 Teams ↔ Player 的具体类型回依赖。**  
   [GGYGOLocalPlayer.cpp:11](F:/ue_project/GGYGO/Source/GGYGO/Player/GGYGOLocalPlayer.cpp:11) 创建并缓存 Teams 的 Presets；反向的 [GGYGOSquadPresets.cpp:58](F:/ue_project/GGYGO/Source/GGYGO/Teams/GGYGOSquadPresets.cpp:58) 又转换为具体 `UGGYGOLocalPlayer`，取回自己。  
   这是逻辑模块间的依赖环，虽不是 Build.cs 模块环，却把存档模型与玩家装配入口绑在一起，不利于独立测试。**最小修正：**将 `GetForPlayerController` 便利入口移到 Player 层，Presets 保留数据编辑、解析及基于引擎 `ULocalPlayer` 的加载接口。属于局部职责迁移，无需新增管理器。

5. **[P2｜文档问题] 部分“当前契约”仍与实现矛盾。**  
   [队伍计划:318](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/计划_队伍与装配.md:318) 仍写先登记 Slot、再生成 Pawn，而当前登记会立即尝试附身，实际代码在绑定 Pawn 后才登记；[计划:283](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/计划_队伍与装配.md:283) 声称保留的 `PawnExtension::GrantAbilitySets` 已不存在。  
   [计划:120](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/计划_队伍与装配.md:120) 还把“属性只给自己”归因于 Mixed，但当前 [HealthSet.cpp:38](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Attributes/GGYGOHealthSet.cpp:38) 明确使用 `COND_None`。这些描述会误导后续装配与网络设计。**最小修正：**按当前实现校正文档和相关注释，历史迁移步骤明确标为历史；无需因此修改合理的属性复制策略。

明确无需拆分的设计：

- `Presets → Roster → Slots` 分别代表跨局配置、本局意图和运行时对象，不是重复权威状态。
- Combatants 统一拥有 ASC、基础属性集与 Avatar 绑定；CharacterSlot 和 BossState 保留各自配置及授予策略，未发现两套重复的宿主执行器。
- Squad 当前承担名单、出战索引和切换协调，尚无证据需要大拆类。上述回收与退场契约应先补齐。
- Teams 未发现具体角色、Boss 或招式硬编码，也没有新增帧调度器。`bAbilitiesGranted` 与一次性 PawnData 守卫存在冗余，属于低优先级整理候选。

未验证边界：未执行切人、断线、生成失败、异步保存失败及 Dedicated Server 测试；客户端跨 Actor 复制到达顺序和出战通知完整性仍需专项验证。现有测试文件未见 Teams 专项覆盖。文档明确注明联机未验收，这点没有冒充完成；既有构建通过和单机装配日志也不能覆盖上述边界。

---

## GGYGO｜GameFeature 模块

会话：01a0e5b5-9dc9-7b32-8aaa-3316137b0cc9

本次结论：**部分符合**。数据与运行状态的分工基本清楚，主要缺口在装配失败清理、重复进入保护和 GameFeature 生命周期收尾。

审查范围覆盖 `GameModes` 全部四个源码文件，并交叉检查 Teams、CombatantState、PawnData、PlayerState、AssetManager、插件配置及 GameFeature 文档和两张 Canvas。已核对主仓库与源码子仓库的未提交状态；主审目录没有未提交改动，判断依据是当前磁盘源码。

1. **[P2｜问题] 装配失败或登记被拒绝后，已生成的对象没有回收。**  
   位置：[GGYGOGameMode.cpp:277](F:/ue_project/GGYGO/Source/GGYGO/GameModes/GGYGOGameMode.cpp:277)，`SpawnSquadForPlayer`；相关接口：[GGYGOSquadComponent.cpp:153](F:/ue_project/GGYGO/Source/GGYGO/Teams/GGYGOSquadComponent.cpp:153)。  
   Slot 已创建并授予能力，Pawn 生成失败后直接 `continue`；默认编队直接参与生成，超过容量时 `RegisterSlot` 仅拒绝登记，GameMode 没有获取结果或销毁多余 Slot/Pawn。**未登记对象仍可能留在世界中，超额 Pawn 也不会进入正常待命隐藏流程。**这违反资源生命周期与失败清理要求。  
   最小建议：通过 Teams 的统一规则校验装配名单；登记接口返回结果，由创建方回收未成功交付的对象。涉及 **GameModes、Teams**。

2. **[P2｜问题] 防重复装配只覆盖插件回调路径，没有覆盖共同入口。**  
   位置：[GGYGOGameMode.cpp:168](F:/ue_project/GGYGO/Source/GGYGO/GameModes/GGYGOGameMode.cpp:168)，`HandleStartingNewPlayer_Implementation`；[GGYGOGameMode.cpp:190](F:/ue_project/GGYGO/Source/GGYGO/GameModes/GGYGOGameMode.cpp:190)，`SpawnSquadForPlayer`。  
   `SpawnSquadForPendingPlayers` 会检查 `IsSquadAssembled()`，直接进入路径却没有同样的保护。**同一 Controller 再次进入该入口时，会重新创建 Slot/Pawn**；Teams 只按对象指针去重，无法识别这批新对象对应的重复成员。  
   最小建议：把既有装配结果检查放进共同入口，复用 Teams 的权威状态，不另建 GameMode 队伍状态。涉及 **GameModes、Teams**；本轮未动态触发重复调用。

3. **[P2｜实现缺口] 插件激活请求缺少与本局生命周期配对的释放责任。**  
   位置：[GGYGOGameMode.cpp:83](F:/ue_project/GGYGO/Source/GGYGO/GameModes/GGYGOGameMode.cpp:83)，`ActivateGameFeatures`；[GGYGOGameMode.h:106](F:/ue_project/GGYGO/Source/GGYGO/GameModes/GGYGOGameMode.h:106)。  
   当前只保存待完成计数，没有本局申请的插件集合、释放入口或结束阶段保护；项目源码也未找到对应的停用/卸载调用。`CreateUObject` 的对象绑定不能代替插件资源释放契约。**因此现有代码不足以保证本局结束后释放本局的插件使用权。**这不满足资源归属和清理路径要求。  
   最小建议：正式接入内容插件前，明确激活使用权的持有者、结束时释放方式及多世界共享规则，避免直接无条件停用其他世界仍使用的插件。涉及 **GameFeature、GameModes**。当前项目未发现角色 GameFeature 插件，此项属于现有激活接口的缺口，未证明当前玩法已发生残留。

4. **[P3｜文档问题] Canvas 描述了源码不存在的玩家等待队列。**  
   位置：[GGYGO_流程_GameFeature.canvas:36](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/GameFeature/GGYGO_流程_GameFeature.canvas:36)；对应源码：[GGYGOGameMode.cpp:142](F:/ue_project/GGYGO/Source/GGYGO/GameModes/GGYGOGameMode.cpp:142)。  
   图中写“暂存玩家”“Controller 排队”，实际实现直接返回，完成后遍历当前世界的 Controller。计划文档还在[第 57 行](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/GameFeature/计划_GameFeature.md:57)写“先补激活等待”，而后文和源码已存在等待逻辑。容易误导后续增加第二份等待状态。  
   最小建议：统一描述为“延后装配，完成后扫描当前玩家”，并明确“基础激活等待已实现，完整插件化未实现”。两张 Canvas 的 JSON、ID 唯一性和边引用检查通过。

**拆分评估与候选优化：**GameMode 当前同时承接插件异步生命周期和玩家队伍创建，两者具有不同的失败与清理边界。后续补完整插件生命周期时，适合将其收敛到独立协调对象，GameMode 保留启动与玩家进入编排；这是候选拆分，不是本轮批准实施的架构变更。“加载失败仍放行”是源码和计划明确的现有策略，不能直接判为错误；引入必需插件时，再区分必需项与可选项。

**明确无需拆分的合理设计：**

- Experience 默认名单、玩家 Roster、跨局 Presets、实际 Slots 分属不同生命周期，不是重复权威状态。
- GameMode 通过 `InitializeForPawnData`、`AttachAvatar`、`RegisterSlot` 协作，没有直接写另一模块的内部字段。
- Experience 保持纯配置，角色差异交给 PawnData/AbilitySet；主审代码未发现具体 Boss 或招式硬编码、第二套帧调度器，也未发现指回 GameModes 的依赖环。

**未验证边界：**本轮未修改文件、构建、操作 UE 或启动 PIE；未检查二进制资产内部接线。未验证插件激活失败、切关释放、多世界共享、重复进入和异常装配的动态表现。已有构建通过不等于这些路径验收通过；角色插件、项目自定义 GameFeature Actions、完整 Experience 加载与客户端就绪协调仍不能视为已实现。

---

## GGYGO｜BossAI 模块

会话：01a0e5b5-d01a-7210-8b91-ac4716a8b07e

结论：**部分符合**。现有职责划分合理，未发现本次主审范围内另建冷却系统、伤害执行链或帧调度器；主要缺口集中在生命周期收尾、选招边界与配置校验。

已完整读取项目 `AGENTS.md`，审查 BossState、Encounter、AIController、Definition/ActionSet、两个 BT Task，并检查 CombatantState、PawnExtension、GAS 接口及 BossMelee 未提交增量的职责接缝；同时核对 BossAI 笔记、四张 Canvas 和实施状态。本轮未修改文件、操作 UE、构建或提交。

1. **[P2｜问题] Encounter 缺少成功生成后的销毁责任。**  
   位置：[GGYGOBossEncounter.cpp:57](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/GGYGOBossEncounter.cpp:57)、[GGYGOBossEncounter.h:40](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/GGYGOBossEncounter.h:40)，`SpawnBoss` / 生命周期声明。  
   事实：失败分支会销毁已生成对象；成功后仅保存 State、Controller、Avatar 引用，没有 `EndPlay` 或统一撤场接口。设置 Actor Owner 不等于自动级联销毁。运行时单独移除 Encounter 时，这些对象可能继续存在。  
   这违反资源清理责任必须明确的约束。最小改进：由 Encounter 提供幂等撤场路径，按顺序停止 Brain、通过宿主接口解除 Avatar、释放所创建对象；若需要对象继续存活，则显式转交所有权。涉及 **BossAI、Combatants**。

2. **[P2｜问题] 动态权重可以进入无法自行恢复的零权重状态。**  
   位置：[GGYGOBossAIController.cpp:47](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/GGYGOBossAIController.cpp:47)，`RecordActionSelection`；[BTTask_GGYGOChooseBossAction.cpp:118](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/BehaviorTree/BTTask_GGYGOChooseBossAction.cpp:118)。  
   事实：选中动作后持续乘 `RepeatPenalty`，只有选中其他动作才获得恢复；零权重直接被排除，无候选时不更新权重。单动作配置将 `RepeatPenalty` 设为允许值 0 后，只能选择一次。默认 0.35 连乘也存在浮点下溢：独立单精度算术核对在第 99 次归零，具体 UE 触发次数未实测。  
   这暴露了派生决策状态缺少恢复规则的问题，可能造成 GAS 已允许激活但 AI 永久停招。最小改进：明确“全部合格候选权重为零”的恢复策略，或校验并拒绝无法恢复的配置；恢复仍归决策层，无需增加计时器。涉及 **BossAI**。

3. **[P2｜配置防护缺口] ActionTag 唯一性未被代码保证，选择结果可能无法准确传给执行任务。**  
   位置：[GGYGOBossActionSet.cpp:6](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/GGYGOBossActionSet.cpp:6)，`FindAction`；[BTTask_GGYGOChooseBossAction.cpp:144](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/BehaviorTree/BTTask_GGYGOChooseBossAction.cpp:144)；[BTTask_GGYGOActivateAbility.cpp:52](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/BehaviorTree/BTTask_GGYGOActivateAbility.cpp:52)。  
   事实：选择任务遍历所有动作行，却只输出 Tag；激活任务按 Tag 取第一条。ActionSet 没有重复键校验。若两行共用 Tag、配置不同 Ability 或筛选条件，第二行通过筛选后仍可能激活第一行，权重缓存也会共用同一键。**未证实当前资产已包含重复项。**  
   这违反接口输入必须可确定解析及配置安全校验的要求。最小改进：在 ActionSet 编辑器校验及运行时装配入口拒绝重复 Tag，并校验 Tag 与 Ability 的匹配关系。涉及 **BossAI、AbilitySystem 接口**。

4. **[P3｜文档问题] 汇总实施状态与模块笔记不同步。**  
   位置：[计划_实施状态.md:27](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/计划_实施状态.md:27)、[计划_Kevin_DemonBattle战斗接入.md:86](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/BossAI/计划_Kevin_DemonBattle战斗接入.md:86)。  
   前者仍写“正在编码、完整构建尚未完成验证”，后者已写“完整构建通过、自动化测试待运行”。此外汇总的“A–C 已完成”仍附有死亡、Brain 暂停和联机验收缺口。建议统一为“基础实现及既有单机竖切完成，专项验收未全部完成”，并更新构建状态。涉及 **根会话汇总、BossAI/Combat 文档**。BossAI 换形态图已明确标注目标设计，没有把完整事务冒充已实现。

**无需拆分的合理设计：**

- BossState 持有持久 ASC 与 Form/Phase，Encounter 装配，Controller 持有 Brain 和决策权重，当前边界清楚。
- 两个 BT Task 分别负责选择与 GAS 激活等待；结束委托、同步结束和 Abort 解绑已有处理。Abort 不强制取消 GA 符合现有契约。
- Definition/ActionSet 保存配置；BossMelee 通过 Controller 停止寻路、通过 CMC 句柄请求位移，未在 AI 侧复制执行机制。
- Controller 现有权重逻辑规模有限，暂不需要独立组件。未来策略显著扩展时再抽出可独立验证的选择策略，属于候选优化。

**未验证边界：**未回读本轮修改的 `BB_Boss_Test.uasset` 内部接线；未运行 BT 暂停恢复、撤场、联机或自动化测试。BossMelee 具体执行由战斗会话主审。完整 Editor 构建通过不代表这些动态验收通过。

---

## GGYGO｜Combatants 模块

会话：01a0e5b5-de0e-7692-85ad-5e642f1e9d28

结论：**部分符合**。持久 ASC、基础属性和玩家/Boss 业务的分层合理；主要缺口在客户端配置恢复、宿主交接及销毁清理。

范围：已完整读取最新 `AGENTS.md`，检查当前工作区的 CombatantState、CharacterSlot、BossState、PawnExtension，以及 GameMode/BossEncounter 装配、CharacterBase 清理、ASC 配置和 CMC 订阅链；核对相关未提交 CMC 增量、模块笔记及 Canvas。以下是静态代码审查结论。

1. **[P1，问题] ASC 规则配置只在服务器注入，客户端没有恢复路径。**  
   [GGYGOCharacterSlot.cpp:43](F:/ue_project/GGYGO/Source/GGYGO/Teams/GGYGOCharacterSlot.cpp:43) 拒绝客户端初始化，69–70 行设置两张规则表；BossState 同样处理。两张表在 [GGYGOAbilitySystemComponent.h:245](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h:245) 仅为普通 `UPROPERTY`，Slot 的 PawnData 复制也没有 OnRep 分发。全源码检索未发现其他注入路径。客户端因此采用默认组规则，并跳过 Tag 关系扩展，可能与服务器的预测激活、阻断和取消判定不同，违反规则来源一致的要求。最小建议：由宿主提供幂等配置应用函数，在服务器初始化和客户端配置复制到达时共用。涉及 **Teams、BossAI、AbilitySystem**。

2. **[P2，问题] 同一 Pawn 被另一宿主接管后，旧宿主仍能解绑新宿主的 ASC。**  
   [CombatantState::AttachAvatar:80](F:/ue_project/GGYGO/Source/GGYGO/Combatants/GGYGOCombatantState.cpp:80) 只检查 PawnExtension 是否存在；[PawnExtension::InitializeAbilitySystem:140](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp:140) 换 ASC 时清旧 ASC，却不清旧宿主的 `AvatarPawn`。随后旧宿主调用 [DetachAvatar:121](F:/ue_project/GGYGO/Source/GGYGO/Combatants/GGYGOCombatantState.cpp:121)，会直接解绑该 PawnExtension 当前持有的新 ASC。这样两个宿主同时声明同一 Avatar，破坏唯一归属。最小建议：明确禁止跨宿主抢占并返回失败；若需要迁移，则先完成旧宿主解绑，并在清理前核对 ASC 身份。涉及 **Combatants、Character**；当前装配正常路径未见主动这样调用，属于接口边界缺陷。

3. **[P2，问题] 宿主先结束生命周期时，缺少对存活 Pawn 的解绑通知。**  
   [GGYGOCombatantState.h:62](F:/ue_project/GGYGO/Source/GGYGO/Combatants/GGYGOCombatantState.h:62) 没有 `EndPlay` 清理，现有销毁监听仅覆盖 **Avatar 被销毁**。PawnExtension、Health 和 CMC 的缓存清理由显式反初始化广播驱动，例如 [GGYGOCharacterMovementComponent.cpp:449](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp:449)。若宿主先销毁而 Pawn 仍存活，这条通知链没有入口，不满足缓存失效和资源清理责任。最小建议：增加宿主结束时的幂等解绑，核对绑定身份后通知 PawnExtension，并移除 Avatar 委托；客户端也需要本地清理路径。涉及 **Combatants、Character**；触发后的运行表现尚未验证。

4. **[P3，问题] 旧说明仍引导使用已废弃的双入口装配。**  
   [README.md:120](F:/ue_project/GGYGO/Source/GGYGO/README.md:120) 仍写 `InitializeAbilitySystem + Slot->SetAvatar`；[PawnExtension.h:119](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h:119) 仍宣称解绑会回收授予的能力，实际代码明确保留宿主能力。前者容易重新引入多个绑定写入点，后者会误导生命周期使用者。最小建议：统一为 `AttachAvatar` 契约并修正能力保留说明。Obsidian 已明确标注完整换形态事务待实现，没有发现把它写成已完成；阶段 A/B 的“已完成”总述宜进一步注明实现与动态验收边界。

5. **[P3，候选加固，非已发生问题] 基础属性唯一性目前依赖资产填写约定。**  
   [CombatantState.cpp:31](F:/ue_project/GGYGO/Source/GGYGO/Combatants/GGYGOCombatantState.cpp:31) 创建基础属性；[AbilitySet.cpp:104](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySet.cpp:104) 对配置的属性类直接创建新实例，没有重复类型检查。笔记已要求基础属性不再填写到 `GrantedAttributes`，本轮未发现违反该约定的实际资产证据。建议后续在资产校验或授予入口拒绝重复基础属性类，防止产生第二份属性状态。涉及 **AbilitySystem、Combatants**。

**无需拆分的合理设计：** CombatantState 保持最小宿主职责，未耦合具体角色、玩家输入或 Boss 招式；Slot/BossState 通过继承复用绑定机制，各自负责配置和授予策略。PawnExtension 的本地 ASC 缓存与 InitState 协调不构成第二套战斗状态机；当前也没有证据要求把这几个类继续拆小。Boss 的 Form/Phase 字段与 ASC Tag 由同一函数同步，目前属于权威状态及其投影。

**未验证边界：** 未操作 UE、构建或运行测试，也未读取蓝图内部接线。联机乱序复制、宿主先销毁、跨宿主接管、冷却/GE 跨 Avatar 保留均未动态复现；既有完整构建通过不覆盖这些验收。本轮未修改文件、提交或推送。

---

## GGYGO｜System 模块

会话：01a0e5b5-eb47-7970-ba89-4b5f90919296

结论：**部分符合**。System 的职责划分总体清楚，无需大规模拆分；主要问题在共享资产加载契约、异常配置处理和文档准确性。

审查范围：已完整读取项目 `AGENTS.md`，检查 System 全部 6 个源码文件、当前未提交差异、相关配置、共享资产调用点及 System 笔记/Canvas。System 增量仅为 Ice01/Ice02 两个原生标签的声明和注册。

1. **P2｜错误配置时另建 AssetManager，脱离引擎管理生命周期。**  
   位置：[GGYGOAssetManager.cpp:37](F:/ue_project/GGYGO/Source/GGYGO/System/GGYGOAssetManager.cpp:37)，`Get()`。类型转换失败后创建并 Root 一个兜底 Manager，但没有替换 `GEngine->AssetManager`，也没有执行其 `StartInitialLoading()`。因此引擎资产索引与项目共享资产访问可能分属两个实例，违背执行机制唯一归属；软路径加载即使成功，也不能证明 PrimaryAsset 索引初始化完整。当前配置正确，尚未观察到实际触发。最小建议：提供可空的项目 Manager 获取接口，配置不符时明确返回不可用，保留编辑器继续运行的能力。涉及 **System**。

2. **P2｜预加载未覆盖共享 GE，文档却保证运行时命中缓存。**  
   位置：[GGYGOAssetManager.cpp:55](F:/ue_project/GGYGO/Source/GGYGO/System/GGYGOAssetManager.cpp:55)、[GGYGOGameData.h:59](F:/ue_project/GGYGO/Source/GGYGO/System/GGYGOGameData.h:59)、[GGYGOHealthComponent.cpp:366](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHealthComponent.cpp:366)。启动时加载 GameData；三个 GE 仍是软类引用，没有显式预载。自毁入口仍执行 `LoadSynchronous()`，冷启动且无其他引用预载时可能现场加载或失败，与[结构.md:11](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/System/结构.md:11)的保证不符。最小建议：明确预载范围；若要求共享 GE 运行时就绪，由 System 统一预载、持有并验证。另需纠正 cpp 第 89 行注释：`LoadPrimaryAssetsWithType` 不设置 AlwaysCook，Cook 规则来自配置。涉及 **System、Character**。

3. **P3｜共享伤害资产的实际消费方式与说明不一致。**  
   位置：[GGYGOGameData.h:55](F:/ue_project/GGYGO/Source/GGYGO/System/GGYGOGameData.h:55)。注释称所有伤害来源共用该 GE，但当前玩家连段和 Boss 近战分别使用自己的 `DamageEffect`：[玩家连段:64](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.h:64)、[Boss 近战:68](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.h:68)。检索未发现共享 Damage/Heal 字段的 C++ 消费点。这是**契约与文档偏差**，尚不能认定存在重复伤害执行链。最小建议：明确“全局默认＋能力覆盖”或“各能力自行配置”的实际约定，同步字段说明与笔记。涉及 **System、AbilitySystem、BossAI**。

4. **P3｜底层日志反向依赖 GAS，独立性描述失真。**  
   位置：[GGYGOAssetManager.cpp:7](F:/ue_project/GGYGO/Source/GGYGO/System/GGYGOAssetManager.cpp:7)。共享资产管理依赖 `AbilitySystem/GGYGOAbilitySystemLog.h`，而[模块参考.md:42](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/模块参考.md:42)称 System 不依赖其他模块。属于职责目录层面的反向依赖，未发现 UBT 模块循环或业务状态泄漏。最小建议：使用 System 自有或公共日志类别。涉及 **System、AbilitySystem**。

明确无需拆分的设计：

- GameplayTags 集中注册属于共享词汇。Ice01/Ice02 没有引入具体招式判断、调度或角色依赖；按业务继续分组只是候选维护优化。
- AssetManager 管加载与缓存，GameData 管可配置引用，职责已经分开；进程级强引用缓存具有合理生命周期。
- System 未持有角色权威状态、计时器或第二套战斗执行链。旧移动状态标签及弃用免疫标签的保留，不能单独作为重复状态机的证据。

未验证边界：未操作 UE、构建、运行 PIE 或检查资产内部字段；未验证打包、冷加载耗时、错误配置恢复与并发调用。现有完整 Editor 构建通过不代表这些动态场景通过。实施状态明确将 Kevin 增量标为未验收，本轮没有发现其被写成动态验收完成。全程只读，未修改、提交或推送。

---

## GGYGO｜Combat 模块

会话：01a0e5b5-f763-78c1-86c8-fa760a9f2100

审查范围：Combat 全部运行时代码与测试，包含未提交的 Trace 修改及新增测试；只读核对了 BossMelee、PlayerCombo 的接入、下游伤害上下文，以及 Combat 笔记、两张 Canvas 和总状态文档。已完整读取当前 `AGENTS.md`。

**结论：部分符合。** Trace 的职责基本清晰，没有混入伤害计算、能力生命周期或具体角色业务。以下是值得优先处理的发现，未发现需要拆分整个组件的依据。

1. **P2｜问题：命中输出缺少下游需要的物理材质。**  
   [GGYGOMeleeTraceComponent.cpp:123](F:/ue_project/GGYGO/Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.cpp:123) 的 `PerformTrace()` 未设置 `bReturnPhysicalMaterial`；本地 UE 源码确认该查询参数默认是 `false`。而 [GGYGOGameplayEffectContext.cpp:66](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOGameplayEffectContext.cpp:66) 从 `HitResult.PhysMaterial` 取材质，[GGYGODamageExecution.cpp:106](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Executions/GGYGODamageExecution.cpp:106) 据此执行材质衰减。  
   这使 Combat→GAS 的数据契约不完整：即使目标配置了材质，该查询也未请求返回。最小修改是启用材质返回，并用配置物理材质的碰撞目标验证输出；材质解释和伤害规则继续归 Physics/GAS。

2. **P2｜问题：组件自身生命周期缺少窗口失效清理。**  
   [GGYGOMeleeTraceComponent.cpp:54](F:/ue_project/GGYGO/Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.cpp:54) 的 `EndTraceWindow()` 能清理代次、基线、去重和 Tick，但组件没有在 `OnUnregister`、`EndPlay` 或停用入口调用它。引擎基类也不会清除这些自定义字段。  
   因而组件注销后重新注册，或停用后恢复时，可能保留旧窗口和旧坐标，继续跨越失效期间扫掠。这违反派生缓存须明确失效清理的规则。最小修改是让组件生命周期复用窗口关闭路径，并补一次注销／恢复用例。现有两种 GA 的正常结束路径已主动关闭，**本项不代表已观察到当前攻击结束后残留命中**。

3. **P3｜问题：日志引入了目录层的反向依赖。**  
   [GGYGOMeleeTraceComponent.cpp:6](F:/ue_project/GGYGO/Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.cpp:6) 新增对 `AbilitySystem/GGYGOAbilitySystemLog.h` 的依赖；同时 [GGYGOPlayerComboAbility.cpp:11](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp:11) 依赖 Combat。  
   这是仅由日志造成的架构依赖回环，当前都在同一个 UE 模块内，不是链接模块循环，但会削弱“GAS 消费通用 Combat”的依赖方向。最小修改是使用 Combat 自有日志类别，或已有的公共底层日志入口。

4. **P2｜问题：总参考页仍保留与源码矛盾的实现描述。**  
   [模块参考.md:499](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/模块参考.md:499) 仍写“分 4 段”“隧穿消失”；当前实现已按长度／半径分段，并明确保留大角度旋转误差。另有 [计划_实施状态.md:27](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/计划_实施状态.md:27) 仍称完整构建未验证，与根会话报告及 Combat 模块笔记不一致。  
   最小修改是同步算法描述与构建状态，保留“运行验收未完成”。Combat 自身笔记和两张 Canvas 已明确区分构建通过、测试尚待执行，没有把新增防护写成动态验收完成。

**无需拆分的合理设计：** Socket 采样、碰撞查询、窗口去重和查询重入保护共享同一窗口生命周期，留在一个小组件中合理。`WindowSerial` 是查询有效性标记，未成为第二套 GA 状态机；弱引用命中集合和上一帧端点也属于职责内缓存。伤害仍交给 GA/GE/Execution，窗口语义由动画事件提供，Socket、半径和采样预算可配置。两种 GA 均已设置并释放 Trace 对 Mesh 的 Tick 依赖。

**候选优化：** 两种 GA 重复管理 Mesh 刷新设置与采样依赖，后续新增调用者时可评估复用统一的资源管理入口；当前不足以要求大范围拆分。仅支持角色主 Mesh 是已明确的能力边界，暂不需要为尚不存在的武器形态引入抽象层。

**未验证边界：** 本轮未修改文件、构建、运行测试或操作 UE。现有 [SafetyAndCoverage 测试:71](F:/ue_project/GGYGO/Source/GGYGO/Combat/Tests/GGYGOMeleeTraceSafetyTest.cpp:71) 手动调用 Tick，武器全程静止；能覆盖静态采样密度、去重、关闭／重开保护，不能证明移动扫掠、真实动画调度或低帧率短窗口正确。阻挡目标后的多目标覆盖、材质返回、组件恢复、联机和真实资产表现仍待验证；完整 Editor 构建通过不能替代这些证据。

---

## GGYGO｜Physics 模块

会话：01a0e5b6-24d1-7823-80c7-9579172807aa

结论：**部分符合。Physics 本体职责清晰，无需拆分；主要问题在 Combat → GA → GE/Cue 的材质语义传递。**

审查范围包含 Physics 全部源码、玩家/Boss 近战实际调用链、EffectContext、DamageExecution、HitImpact Cue、相关测试和架构笔记，并纳入 BossMelee、MeleeTrace 的未提交增量。已完整读取 AGENTS.md，并对照本机 UE 5.8 源码确认接口行为。

1. **[P2｜确定问题] 近战查询未请求返回物理材质。**  
   [GGYGOMeleeTraceComponent.cpp:123](F:/ue_project/GGYGO/Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.cpp:123)，`PerformTrace` 创建查询参数后只添加忽略对象，没有设置 `bReturnPhysicalMaterial`；引擎默认值为 `false`。因此即使碰撞体配置了带 Tag 的材质，这条查询链也不会取得所需材质信息，下游衰减和表面反馈缺少输入。这是跨模块数据契约未落实。最小改进：由 **Combat** 开启材质返回，并验证真实碰撞结果中的材质；Physics 保持数据提供者职责。

2. **[P2｜确定问题] 两条近战路径绕过 Tag 注入，手动 Cue 也未携带表面 Tag。**  
   [玩家 HandleMeleeHit:315](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp:315) 与 [Boss HandleMeleeHit:273](F:/ue_project/GGYGO/Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp:273) 直接调用 `ASC::MakeOutgoingSpec`，不会调用项目 GA 的 `ApplyAbilityTagsToGameplayEffectSpec`。随后构造的 Cue 参数只填 Context、位置、法线和来源，没有填 `AggregatedTargetTags`；[HitImpact:45](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Cues/GGYGOGameplayCueNotify_HitImpact.cpp:45) 却只按该字段分流。即便修复第 1 项，当前原生链仍会选择默认反馈。最小改进：由 **AbilitySystem** 提供共享的命中语义填充入口，在 HitResult 写入后统一填充 Spec/Cue；玩家与 Boss 复用，避免各自维护材质规则。

3. **[P2｜边界缺陷] Cue 把合法的世界原点命中当成“无命中”。**  
   [GGYGOGameplayCueNotify_HitImpact.cpp:52](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Cues/GGYGOGameplayCueNotify_HitImpact.cpp:52) 用 `Location.IsNearlyZero()` 决定回退到目标位置。命中点位于原点附近时，粒子和声音会移到目标 Actor 位置。该实现用数值猜测有效性，丢失了 HitResult 已提供的明确语义。最小改进：**AbilitySystem/Cue** 优先检查 Context 中是否存在 HitResult，并读取其 `ImpactPoint`；无命中路径另行定义位置有效性。

4. **[P2｜潜在缺陷，当前未发现启用者] 距离衰减计算没有使用命中位置。**  
   [GGYGODamageExecution.cpp:114](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Executions/GGYGODamageExecution.cpp:114) 计算 `Context.Origin` 到 EffectCauser 的距离；本机引擎 `AddHitResult` 默认把 Origin 设置为 `HitResult.TraceStart`。因此该值是查询起点到来源的距离，无法表达接口约定的来源到目标距离。以后接入距离衰减来源时会产生错误倍率。最小改进：由 **AbilitySystem** 明确距离定义，使用命中点与来源位置计算。当前 `Source/Plugins` 检索未发现 `IGGYGOAbilitySourceInterface` 的具体实现者，不能据此断言现有近战伤害已算错。

5. **[P3｜文档缺口] “待配资产”的说明不足以表达现有代码接线缺口。**  
   [计划_实施状态.md:51](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/计划_实施状态.md:51) 将相关工作描述为代码接口已准备、剩余编辑器配置；[Physics 结构图:56](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Physics/GGYGO_结构_Physics.canvas:56) 已提示 Boss 绕过注入，但未覆盖玩家同类问题及查询缺少材质返回。影响是后续容易把“资产配置完成”误当作链路完成。最小改进：由 **Physics/AbilitySystem/Combat** 补齐“待修接线、待配资产、待动态验收”的边界。现有文档明确保留了物理材质待配置状态，并非全部误写为已完成。

明确无需拆分的合理设计：

- 材质类只持有 `Tags`，没有 Tick、伤害规则或角色分支，保持现状合理。
- Combat 查询并去重、GA 施加 GE、Execution 写元属性、HealthSet 结算，权威职责基本清晰。
- EffectContext 深拷贝 HitResult、以弱引用保存来源；Trace 结束时清理窗口状态，并通过序号中止回调取消后的旧查询，属于合理生命周期设计。
- Cue 的表面映射、粒子和声音由资产配置，无需为不同表面新增 C++ 子类。共享语义填充是局部复用建议，不需要另建 Physics 子系统。

本轮仅做静态只读审查，未修改文件、提交、推送、构建或操作 UE。未验证材质资产接线、胶囊与骨骼碰撞实际命中对象、客户端 Cue 复制及动态表现；已有 Trace 测试主要覆盖采样、去重和取消，未覆盖上述材质链路。完整 Editor 构建通过不能替代这些动态验收。

---

## GGYGO｜Messages 模块

会话：01a0e5b6-3230-7032-8acd-b36e97cc52ef

本次结论：**部分符合**。Messages 保持了轻量、单向观察的结构；当前 C++ 未发现订阅消息后反向修改 ASC、重复维护权威状态或新增调度器。主要问题在消息语义、发布时间和文档准确性。

审查范围：已完整读取 `AGENTS.md`，检查当前工作区的 Messages 载荷、HealthSet 与能力失败广播、GameplayMessageRouter 的分发和清理、项目源码中的订阅点，以及 Messages 文档、Canvas 和状态入口。核对了主仓库与源码嵌套仓库的未提交增量；未发现这些增量新增 GameplayMessage 发布或订阅。

1. **[P2｜确定问题] `PoiseBreak` 实际表示每次正削韧，偏离“破韧”契约。**  
   位置：[GGYGOHealthSet.cpp:195](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Attributes/GGYGOHealthSet.cpp:195)，`PostGameplayEffectExecute`。只要 `Magnitude > 0` 就发送 `Message_PoiseBreak`，扣韧发生在第 209 行；真正的归零边沿另在第 243 行判定。例如韧性从 100 降到 90，也会收到“破韧”消息。订阅者若要获得真实破韧结果，就必须重复判断规则，违反规则唯一归属与明确事件语义的要求。最小建议：由 HealthSet 的既有破韧边沿发布该消息；若需要逐次削韧反馈，另定义对应语义。涉及 **AbilitySystem、System、Messages**。

2. **[P2｜确定问题] “已发生结果”的消息在属性更新前同步送达。**  
   位置：[GGYGOHealthSet.cpp:167](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Attributes/GGYGOHealthSet.cpp:167)，`PostGameplayEffectExecute`；路由在 [GameplayMessageSubsystem.cpp:107](F:/ue_project/GGYGO/Plugins/GameplayMessageRouter/Source/GameplayMessageRuntime/Private/GameFramework/GameplayMessageSubsystem.cpp:107) 直接执行回调。Damage 广播后才 `SetHealth`，Poise 广播后才 `SetPoise`；遵守只读规则的观察者仍会读到旧值。与[计划蓝图.md:33](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/计划蓝图.md:33) 的“结算后广播”及载荷“已发生事件”契约冲突。最小建议：预先保存原始幅度和上下文，在本次属性更新、元属性清零后发布，并明确与属性委托的顺序。涉及 **AbilitySystem、Messages**。

3. **[P2｜确定文档问题] 将属性复制通知混同为 GameplayMessage 客户端路径。**  
   位置：[GGYGOVerbMessage.h:20](F:/ue_project/GGYGO/Source/GGYGO/Messages/GGYGOVerbMessage.h:20)、[Messages/结构.md:5](F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Messages/结构.md:5)。两处都描述客户端复制路径下消息来源不完整；实际 [GGYGOHealthSet.cpp:44](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Attributes/GGYGOHealthSet.cpp:44) 的 `OnRep_Health` 和第 73 行的 `OnRep_Poise` 只广播属性委托，没有构造 `FGGYGOVerbMessage`。路由自身也没有网络转发。这会让接入者误以为客户端已具备逐次伤害消息。最小建议：明确当前本地广播范围、RepNotify 委托与消息通道的区别，将客户端消息交付标为待设计/验证。文档和 Canvas 中 UI／音频／统计订阅也应标明是约定还是已接线：源码检索未找到项目 C++ 消费者，蓝图接线本轮未验证。涉及 **Messages、AbilitySystem、后续表现消费者**。

明确无需拆分的合理设计：

- `FGGYGOVerbMessage` 只有数据字段，没有计时器、缓存或执行器，无需增加消息管理类。
- 通用 Verb 载荷放在 Messages，能力失败专用载荷留在 AbilitySystem，职责归属合理。
- HealthSet 持有属性与破韧边沿，消息层只传递事实，这个依赖方向合理。
- 失败文本和 Montage 通过 `EditDefaultsOnly` 映射配置，未在消息底层硬编码角色业务。
- 路由已有弱引用回调、显式注销、异步节点销毁注销及子系统清理。**候选完善项**是补充订阅者取消和载荷保存契约；目前没有证据证明项目消费者存在泄漏，不列为确定缺陷。

未验证边界：未操作 UE、PIE 或构建，未检查蓝图事件图及动态订阅清理；未验证联机交付、Avatar 更换后的表现定位或回调重入。已有完整构建通过不能替代这些动态验收。本轮没有修改文件、提交或推送。

---

## GGYGO｜战斗模块

会话：01a0ebc0-8780-7f92-86d0-2f028f08f147

## 范围与结论

已完整读取 `AGENTS.md`，只读检查当前源码及 Kevin 未提交增量：PlayerCombo、BossMelee、输入/窗口状态、Montage Task、ASC 纠正入口、相关测试和实施文档。

**结论：部分符合。** 职责划分和资产配置方向清楚，但生命周期恢复与通用层依赖仍有问题。本轮未修改文件、运行测试或操作 UE。

## 最高价值发现

### 1. [P1｜问题] 玩家结束清理发生在同步广播之后

位置：[GGYGOPlayerComboAbility.cpp:356](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp:356)，`EndAbility`。

- **事实：** 调用 `Super::EndAbility` 后，才恢复 Mesh 设置、清空 MontageTask、ActiveMesh、TraceComponent 和 CurrentStep；父类会同步广播能力结束。
- **影响：** 回调中若重新激活同一实例，旧结束流程会清掉新动作状态；启动其他动作时也可能覆盖其 Mesh 设置。不符合资源生命周期与恢复责任要求。
- **最小建议：** 参考本次 BossMelee，在父类广播前完成全部自有资源清理，广播后不再写实例成员；补玩家实际 GAS 重入测试。涉及战斗执行、AbilitySystem。

### 2. [P1｜问题] 玩家激活未处理蓝图同步结束

位置：[GGYGOPlayerComboAbility.cpp:95](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp:95)，`ActivateAbility`。

- **事实：** `Super::ActivateAbility` 会进入蓝图激活事件；返回后直接重置 `bCleaningUp` 并继续提交、修改 Mesh、创建任务，没有检查能力是否已结束。本次 BossMelee 已有该检查。
- **影响：** GA 蓝图在激活事件中立即取消或结束时，原生流程仍可能重新建立资源，造成结束后的残留。不符合蓝图扩展点与原生生命周期的一致性要求。
- **最小建议：** 激活状态初始化放在回调前，回调后确认本次激活仍有效再继续；覆盖蓝图立即结束/取消场景。涉及战斗执行。

### 3. [P2｜问题] 玩家看门狗与实际 Montage 使用不同时间尺度

位置：[GGYGOPlayerComboAbility.cpp:165](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp:165)，`StartStep`。

- **事实：** 超时只除以 `Step.PlayRate`；共享 Task 会应用全局能力速率缩放，引擎播放还乘 Montage `RateScale`。
- **影响：** 调慢 Montage 后，正常播放也可能被判超时取消，兜底计时器实际改变了动作生命周期。
- **最小建议：** 统一有效速率来源，校验有限正值后计算剩余时长；避免两处各自维护速率规则。涉及战斗执行、Montage Task。

### 4. [P2｜问题] Montage Task 的临时 RootMotion 缩放缺少完整释放路径

位置：[GGYGOAbilityTask_PlayMontageAndWaitForEvent.cpp:218](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.cpp:218)，`StopPlayingMontage`。

- **事实：** 激活时设置 Character 缩放；恢复仅在混出回调中执行。主动停止先解绑混出回调，因此取消/任务结束路径会跳过恢复；自然混出也固定写回 `1`，没有保存原值。
- **影响：** 使用非默认缩放的调用方可能遗留角色状态，影响后续动作。不符合“临时资源由取得者释放”的要求。当前两类近战使用默认值，尚不能据此认定 Kevin 已出现该故障。
- **最小建议：** 在 Task 内统一取得/释放缩放，覆盖正常、取消、结束及替换路径，并校验所有权。涉及 AbilitySystem、Animation/Movement 接口。

### 5. [P2｜架构问题] 通用 ASC 直接依赖玩家连段具体实现

位置：[GGYGOAbilitySystemComponent.cpp:171](F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp:171)，`ClientCorrectComboStep_Implementation`。

- **事实：** 通用 ASC 包含 PlayerCombo 头文件，直接向具体类转换并调用其纠正函数；RPC 参数也承载连段内部语义。
- **影响：** 具体动作协议进入通用能力宿主，后续其他动作纠正容易继续向 ASC 添加分支，违反通用基础设施与动作实现的依赖边界。
- **最小建议：** ASC 保留网络传输及 Spec/预测键校验，将协议解释交给明确的接收接口或专属能力任务。由 AbilitySystem 主审合并方案，无需立即建设通用消息框架。

## 合理设计与无需拆分项

- **PlayerCombo 与 BossMelee 应继续分开：** 前者有输入预测/连段纠正，后者负责服务器动作执行，变化原因不同。
- `WaitComboInput` 管传输、窗口状态管请求有效期、GA 管推进；这些不是重复缓存。
- Boss GA 只持有 CMC 动作句柄；CMC 执行位移，Notify 发布窗口，Trace 查询命中，GE/Execution 结算，职责合理。
- Montage、窗口、伤害、Socket、动作连接和 Profile 保持资产配置；未发现 Kevin 招式分支硬编码进入运行时 C++。
- 两类 GA 的伤害组装有重复，可作为后续小型复用候选；目前不足以要求引入统一攻击框架。

## 未验证边界

以上为静态代码发现，未做运行复现。既有窗口测试仅覆盖纯状态逻辑，不能证明上述生命周期和网络路径正确。Kevin 文档明确区分“构建通过”与“动态验收未执行”，本次未发现将整套玩法写成已验收完成。

---

## 还原角色渲染管线

会话：01a0d21a-84e2-7f00-808d-1618fa4dd2b8

结论：**部分符合新规范**。已完整读取 `AGENTS.md`，审查了当前工作区及未提交增量中的渲染组件、Hero 挂载、Pyrios 材质生成/绑定/验证脚本、校准 JSON、Kevin 材质准备脚本及相关计划笔记。发现以下 5 项实际问题：

1. **[P2] 换装刷新会恢复过期材质，缺少所有权检查。**  
   [GGYGOPyriosRenderComponent.cpp:83](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPyriosRenderComponent.cpp:83) 的 `RefreshMaterials()` 首先按旧索引恢复 `OriginalMaterials`，随后才读取当前模型；`EndPlay()` 第 52 行同样直接恢复。缓存没有记录模型身份、槽位身份或本组件安装的 MID。调用者按接口注释“换 Mesh 后刷新”时，旧材质可能覆盖新模型或其他表现系统刚设置的材质，违反派生缓存的有效期与所有权规则。最小改进是记录“模型、槽位、原材质、本组件 MID”，仅在身份匹配且当前材质仍归本组件所有时恢复，并提供明确的换装前释放入口。涉及 Character 渲染及换装接入方。

2. **[P2] 通用角色底层仍包含 Pyrios 专用业务。**  
   [GGYGOPyriosRenderComponent.cpp:16](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPyriosRenderComponent.cpp:16) 硬编码资源目录和槽位名称匹配；第 75 行按模型名称识别角色，第 123 行默认加载 Pyrios 描边材质。该组件又在 [GGYGOHeroCharacter.cpp:26](F:/ue_project/GGYGO/Source/GGYGO/Character/GGYGOHeroCharacter.cpp:26) 成为所有 Hero 的默认组件。已有 `MaterialSlots` 和光照配置是合理方向，但角色识别、资源选择仍侵入通用机制。最小改进是将这些默认值移入 Pyrios 蓝图或渲染配置资产，让通用组件只消费配置、管理 MID 与描边生命周期。

3. **[P2] 主光配置与自动发现缓存混用，缺少失效规则。**  
   [GGYGOPyriosRenderComponent.cpp:150](F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPyriosRenderComponent.cpp:150) 的 `UpdateLighting()` 把自动发现结果写回公开的 `KeyLight`，之后仅以非空判断复用；没有检查 Actor 有效性及灯光组件是否可见。关闭灯光可见性但保留强度时，角色仍按其强度着色；销毁、卸载或更换主光也没有明确的重新解析路径。最小改进是区分显式配置与弱引用缓存，定义有效性、失效清理及重新选择条件，并明确灯光关闭后的输出策略。涉及渲染与场景光照接口。

4. **[P2] 标为“只读”的验证脚本实际修改编辑器资产状态。**  
   [verify_pyrios_renderer.py:16](F:/ue_project/GGYGO/AAADocs/Scripts/verify_pyrios_renderer.py:16) 会重编译材质。本机 UE 源码 [MaterialEditingLibrary.cpp:997](F:/UE_5.8/Engine/Source/Editor/MaterialEditor/Private/MaterialEditingLibrary.cpp:997) 明确执行 `PostEditChange()`、`MarkPackageDirty()`，并更新子实例参数。调用者进行只读核验时会得到新的脏资产，检查和修改的职责混在一起。最小改进是默认只回读资源与参数，将重编译设为显式验证步骤。此次也确认 UE 5.8 的该接口确实返回错误数组，**不能把现有错误数组判断本身列为缺陷**。

5. **[P2] Pyrios 生成器在完整预检前修改并保存已有资产。**  
   [build_pyrios_materials.py:369](F:/ue_project/GGYGO/AAADocs/Scripts/build_pyrios_materials.py:369) 先修改贴图、重建并保存主材质，随后 `set_instance()` 第 262 行才读取各材质 JSON；缺失贴图检查也发生在实例修改过程中。源 JSON、MatCap 贴图或模型槽位不完整时，会留下部分更新的资产组合。最小改进是先完整解析三份 JSON、校准配置、纹理引用和目标槽位，再进入写入阶段；明确报告失败时已修改的资产。Kevin 脚本已有源文件及 Mesh 槽位预检，可借鉴其阶段边界。

**无需强行拆分的设计：** 材质负责着色公式、组件生产主光参数的边界合理；描边 Mesh 与表面 MID 共用角色生命周期，目前不必拆成独立模块。现有组件 Tick 没有建立第二套游戏调度器，也未发现它写入 ASC、CMC 或战斗内部状态。Kevin 的独立准备脚本可以保留角色专用槽位表，当前无需为一次素材导入建立通用框架。

**候选优化：** 后续继续扩展着色算法时，可将 HLSL 算法与 UE 图构建分开维护；频繁调整 Kevin 预览时，再将槽位调参移入配置。二者目前不是必须立即拆分的问题。

文档总体明确区分“可预览”“光照近似”和“原作视觉还原”，未发现将视觉还原写成已完成；但“换 Mesh 后直接刷新”的说明需要随第 1 项修正。本轮未操作 UE、运行脚本、构建或修改任何文件；未验证二进制资产当前接线、换装/灯光销毁行为、Cook 及最终画面。此前构建和截图不替代这些动态验收。
