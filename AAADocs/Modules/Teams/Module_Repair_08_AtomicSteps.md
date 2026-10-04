# 08 Teams 原子步骤与文件范围

## 当前唯一有效范围：08-M2b-Flow（2026-09-30，已完成冻结）

- 已核对有效排程G4和统筹明确授权。唯一写入者为Teams长期组长`01a0e5b5-910c-71e3-a75c-b17c22fea33e`，`gpt-6.1-sol / xhigh`直接完成，无代理。
- 精确四文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/GGYGO_流程_队伍与装配.canvas`、同目录`计划_队伍与装配.md`、本文件、`AAADocs/Modules/Teams/Module_Repair_08_Validation.md`。唯一结果是实际装配/拒绝/未接边界的流程与计划9.0同步。
- 08-01～05a2源码保持冻结；M1/R1与M2a根审查已接受。结构MD、结构Canvas、全部源码/测试/资产/Config/global不在本步写入范围；旧步骤中的“当前/最新/已授权”仅表示当时历史，不可推导现有租约。
- 第21次完整构建与常规52回归不增加Teams专项、蓝图/PIE/网络验收。构建/UE/Git禁止；完成本步即四文件停止写入，Nav提示清理及生产接线必须独立授权。
- 状态：本步图文同步及静态核对完成，唯一四文件已停止写入并冻结交回；本步详细预检/基线与结果见文末。首屏范围覆盖以下所有旧范围，没有自动接续租约。

## 第14次后历史租约与门禁（保留证据，不再授权）

- 唯一写入者：Teams 长期组长，`01a0e5b5-910c-71e3-a75c-b17c22fea33e`；组长直接执行，不创建或唤醒子代理。
- 当时08-01～04源码均冻结并已进入第14次成功完整构建；该历史轮只授权两份记录同步证据与 **08-05只读预检**。
- 当时精确可写为本文件及`AAADocs/Modules/Teams/Module_Repair_08_Validation.md`；该历史轮没有源码、测试、资产或Obsidian写入授权。
- 当时08-05至08-15生产实现未授权。该轮预检完成后冻结两份记录，不自动接续源码。
- 该历史轮不改调用方、测试、Config、资产或 Obsidian；不构建、不操作 UE、不执行 Git，不创建或唤醒代理。
- 当时其他三条源码线由统筹分别授权；08生产源码保持冻结。文件互斥不替代接口与状态依赖门禁。

历史门禁证据：`Saved/Logs/ModuleRepairBuildGate_20260930_14.log` 为 Succeeded、14.31s、6 actions；`Saved/AutomationReports/ModuleRepairGate_20260930_14/index.json` 为 47 succeeded、0 succeededWithWarnings/failed/notRun、0.4214428365s，exit 0 由统筹通报。该历史轮仅只读核对日志/报告，不重新执行；没有Teams容量/登记专用行为用例，不能据此关闭C10～C14。

## 状态与接口归属（冻结职责目标，未实施缺口见当前预检）

| 所有者 | 唯一职责 |
| --- | --- |
| Teams/Squad | 名单、成员接收、活动索引、显式接收资源的清理责任 |
| GameMode | 组织装配、生成成员、回滚尚未交付 Squad 的对象 |
| ASC/GA | 能力退出判定与取消；GA 清理自身持有资源 |
| Hero/Input | 输入会话与绑定释放；ASC 唯一持有能力输入状态 |
| LocalPlayer | 保存对象取得与缓存；保存模型不依赖具体 LocalPlayer |

### 08-01 已接受静态冻结的接口

头文件：`Source/GGYGO/Teams/GGYGOSquadTypes.h`。

```cpp
namespace GGYGOSquad
{
constexpr bool IsMemberCountWithinCapacity(int32 MemberCount);
}
```

- 唯一结果：供 Presets、Roster、Experience 后续复用的无状态容量判断。
- 返回 `MemberCount >= 0 && MemberCount <= GGYGO_MAX_SQUAD_SIZE`，既有宏仍为 4。
- 参数为 `int32` 数量；0 通过容量判断，是否允许空名单由各调用方决定。
- 只读依赖：原有 `CoreMinimal.h` 的 `int32` 与原有上限宏。
- 不读取、解析、截断或修改名单，不记录第二容量状态，不输出日志或触发回调。
- 验收断言：负数 false；0、1、4 true；5 与正数极值 false；不涉及计数加减，无算术溢出路径。
- 停止点：单头静态检查与边界说明完成即冻结，不适配任何调用方，不进入 08-02。

### 08-02 历史授权的保存容量契约（已冻结）

- 唯一结果：保存模型的 Set、Resolve、PostLoad 都按原始成员数量拒绝超限，不截断原始数据。
- 精确生产文件：`Source/GGYGO/Teams/GGYGOSquadPresets.h`、`Source/GGYGO/Teams/GGYGOSquadPresets.cpp`；附带本批两份记录。
- 只读依赖：08-01 的 `GGYGOSquad::IsMemberCountWithinCapacity(int32)`、原上限宏、既有 AssetManager/SaveGame API。
- SetPresetMembers：先检查索引与 NewMembers.Num()，超限 false 且原 Members 不变；容量通过后才赋值。
- ResolvePresetRoster：保留 OutRoster.Reset() 与 int32 返回接口；先检查保存的 Members.Num()，再取得 AssetManager 并解析 Id。超限诊断并返回 0，不加载或过滤任何 Id，不修改存档。
- HandlePostLoad：仅诊断超限并保留 Members；原有 Super 调用与 ActivePresetIndex 越界修正不改。
- 验收断言：0 与 4 的既有写入/解析路径保留；5（含无效 Id）拒绝；非法写入不覆盖原数据；解析失败输出为空；PostLoad 不截断；存档字段与版本 1 不变；未知 Id/资产部分解析分支不变。
- 非目标：Squad、GameMode、LocalPlayer、PlayerController、GA/ASC、共享头、测试、Config/资产/Obsidian；不改变空名单业务，不解除 LocalPlayer 依赖。
- 停止点：完成两生产文件和本批记录的静态审查即冻结交回，不开始 08-03 或测试。
- 尚未闭合：Resolve 的 0 仍与无有效成员共用返回值；08-07 调用迁移必须检查原始保存容量，区分非法保存与缺省选择，禁止非法保存回退默认名单。本层不扩展返回接口或改调用方。
- 交回时结果：三处已使用冻结 01 的校验；Set 先拒绝后赋值，Resolve 在资产访问前拒绝，PostLoad 只诊断；头注释同步，存档字段/版本/公开签名及 Id 部分解析保持。统筹已接受静态冻结，并通报后续完整构建成功；本层没有专项运行结果。

### 08-03 历史授权的 Roster 原子接收预检（已冻结）

- 唯一结果：SetRoster 完成所有验证并构造局部候选名单后，才一次替换权威 Roster；失败保持原 Roster。
- 所属模块与状态：Teams/Squad 仍唯一持有本局 Roster；局部候选数组仅在调用期间存在，不是第二权威状态。
- 精确生产文件：`Source/GGYGO/Teams/GGYGOSquadComponent.h`、`Source/GGYGO/Teams/GGYGOSquadComponent.cpp`；附带本批两份记录。
- 只读依赖：冻结 01 容量函数与上限宏、冻结 02 保存契约、PawnData 类型、现有 Slot/ASC；不改这些文件或接口。
- 顺序：保留 Owner/Authority 和已装配拒绝 → 保留 0 输入拒绝 → 校验原始 InRoster.Num() → 构造临时名单并跳过 null → 全 null 拒绝 → 一次提交 Roster。
- 验收断言：非 Authority/无 Owner/已装配/空输入拒绝且原名单不变；原始 5 个元素即使含 null 也整体拒绝；1～4 个元素且至少一个非 null 成功，保留顺序与原有重复项策略；全 null 拒绝并保留原名单；无截断及失败前 Reset。
- 非目标：RegisterSlot、切人、销毁、复制配置、GameMode/Experience/Player/GA/ASC/Hero、测试、配置/资产/Obsidian；不改变 PawnData 有效性或去重规则。
- 停止点：两文件实际差异、边界、局部数组清理和依赖静态审查完成后更新记录并冻结交回，不构建/UE/Git，不开始 08-04/05。
- 当前结果：原始容量在 null 过滤前校验；CandidateRoster 收集完成且非空才 MoveTemp 提交；所有 false 路径不修改 Roster。与执行前快照比对，cpp 的 SetRoster 外内容完全一致，h 仅改该函数注释；01/02 三个冻结文件哈希未变。统筹已接受静态冻结，第 14 次完整构建已通过；本模块专项未运行。

### 08-04 历史授权的 Experience 容量接线预检（已冻结）

- 唯一结果：编辑器 IsDataValid 使用冻结公共容量函数检查原始 SquadMembers.Num()，与 03 的超限拒绝语义一致。
- 所属模块/职责：Experience 定义负责自身默认名单的编辑器配置诊断；容量规则仍唯一归 Teams 公共函数，不增状态。
- 精确生产文件：`Source/GGYGO/GameModes/GGYGOExperienceDefinition.cpp`；附带本批两份记录。
- 只读依赖：01 的 IsMemberCountWithinCapacity 与上限宏、03 SetRoster 拒绝契约、PawnData/PawnClass；Experience 头与装载接口不改。
- 顺序：保留父类结果组合 → 原始数量公共校验，超限 AddError 并 Invalid → 原 null/PawnClass 遍历诊断 → 原结果返回。
- 验收断言：0/4 不因容量报错，5 即使含 null 也 Invalid；null 与缺 PawnClass 检查保持；不修改 SquadMembers/资产；无运行时截断说明；WITH_EDITOR 边界、LOCTEXT key、父类结果组合及其他实现不变。
- 非目标：默认空名单业务、运行时装载/插件/ExperienceManager、头文件、Squad/RegisterSlot/切人/销毁、Player/GA/ASC、测试、Config/资产/Obsidian；不构建/UE/Git。
- 停止点：最小单生产文件差异与两份记录静态核对完成后，三文件冻结交回，不进入 05 或测试。
- 当前结果：仅生产文件第 28/30/33 三行改变，分别为共享校验调用、拒绝语义注释及错误文本；与实施前完整快照按三行替换比对一致，其他内容不变。01/03 冻结哈希保持；源码冻结且第 14 次完整构建已通过，本模块专项未运行。

### 08-05 历史只读深化预检（当时生产实现未授权）

#### 当时事实与副作用（05只读预检基线，非当前源码）

- `GGYGOSquadComponent.h:97` 的 RegisterSlot 仍为单参数 void；cpp:140 只检查 null、组件 Owner Authority、重复指针和 Slots 已满。没有 Slot 世界/宿主/PawnData/ASC/Pawn 关联校验，也没有创建责任记录或接收回执。
- Slots.Add 后先 DeactivateSlot，再在 ActiveSlotIndex 为 INDEX_NONE 时调用 SwitchToSlot(0)，返回值被忽略。新成员会被隐藏、关碰撞、停止并禁用移动；首位激活涉及索引、显示/碰撞/移动、Possess 及 OnActiveCharacterChanged 广播，存在同步重入和销毁机会。
- SwitchToSlot 对无 Avatar、死亡和找不到 Controller 会 false；PC.Possess 后没有验证实际附身结果却会广播并 true。只要索引仍 NONE，每次登记都尝试位置 0，不保证找到后来登记的可出战成员。这些切人缺口不由登记布尔返回顺带修复。
- GameMode.cpp:288 是当前检索到的唯一 C++ 调用点；它在 Slot.InitializeForPawnData、Pawn.SetPawnData、Slot.AttachAvatar 后登记，忽略登记结果。蓝图节点调用未审计，不能据 C++ 检索断言不存在蓝图消费者；头注释的“登记后才生成 Pawn”与真实顺序不符，后续应同步。

#### 布尔接收与提交点（待统筹冻结）

- true 必须表示本次成员及契约约定的创建责任已经由 Squad 接收；它不保证 Pawn 成为出战位或 Possess 成功。false 只能用于尚未提交的拒绝，GameMode 才可据此回收本次未交付对象。
- 所有身份/容量/责任校验在写入前完成；Slots 与显式创建责任需在 Deactivate/Switch/Possess/广播之前一起提交。回调后不能因激活失败把 true 改 false，否则 GameMode 与 Squad 会同时回收已交付对象。
- 幂等限于同一 Squad 已接收的同一 Slot 和同一原始创建责任；重复请求不追加成员/责任、不重复隐藏/激活/广播，在满容量时同一请求仍应成功。责任不匹配、其他 Squad 接收或追加新 Pawn 责任不能伪装成重复请求。
- 已清理/终止的 Squad 不由重复登记恢复资源；GameMode 保留本次提交结果，不能根据当前 Avatar、附身或 Actor 有效性重新推导资源是否曾交付。不新增第二套成员/切人状态。
- 第一次登记自动激活的行为保留为独立的提交后尝试；死亡成员或无可出战位的策略、真正 Possess 成功判定与失败控制恢复留待后续装配/切人步骤冻结。

#### 新接收请求的身份条件

| 关系 | 现有只读接口与应冻结断言 |
| --- | --- |
| Squad / PlayerState / Controller | 组件 Owner 是该玩家 PlayerState，且 PlayerState.GetSquadComponent 等于本组件；Controller 与 PlayerState 相互对应，对象存活且同 World；本入口仅 Authority |
| Slot / Controller | Slot 有效、非销毁中、同 World；Slot.GetOwner 等于该 Controller 只证明连接归属，不能证明由本装配流程创建或允许 Squad 销毁 |
| Slot / PawnData | GetPawnData 非空；但它在 AbilitySet 授予前已赋值，不能证明授予流程完成。既有 bAbilitiesGranted 到循环末才 true，且没有公开只读完成查询 |
| Slot / ASC | GetGGYGOAbilitySystemComponent 非空，ASC OwnerActor 等于 Slot；只读取公开 getter，不写 ActorInfo 或授予资源 |
| Slot / Pawn / ASC | 接收创建 Pawn 的身份必须是请求携带的原始生成对象，并等于 Slot.GetAvatarPawn 与 ASC.GetAvatarActor；Pawn 同 World，类型可供现有 Squad 激活，不能抢占另一 Controller 的 Pawn |
| PawnExtension / ASC / PawnData | PawnExtension 存在，缓存 ASC 与 Slot ASC 相同，GetPawnData 与 Slot PawnData 相同；不要求尚未 Possess 的 Pawn 已到 GameplayReady，否则会拒绝正常装配顺序 |

AttachAvatar 为 void，06 已提供 GetAvatarPawn/ASC/PawnExtension 的读回接口，因此绑定是否成功可以读回核对，无须擅改 Combatant 接口；Attach 的 Initialize 广播后还须重检对象与身份，不能仅相信调用发生过。

#### 创建责任与接口缺口——到此交回，不自行选型

1. **接收结果接口**：需冻结 RegisterSlot 的 bool 语义及蓝图输出兼容；现有 UFUNCTION 只表达 Slot，不能同时承诺显式创建责任已交付。
2. **创建责任接口**：需明确哪个入口由 GameMode 显式交付其创建的 Slot 与原始 Pawn，以及借用对象是否允许登记、借用时哪些对象不归 Squad 销毁。候选是专用 C++ 创建成员接收入口或显式责任参数，由统筹选择；本轮不定名、不新增通用转交框架。
3. **责任记录归属**：Squad 唯一持有原始创建对象清理记录，独立于当前 Avatar 关联；记录不能在以后清理时临时从 Owner/Avatar 补算。GameMode 只清未交付对象，06 负责绑定清理，GA 负责自身资源。
4. **初始化完成查询**：现有公开 GetPawnData 不足。如要求登记端验证完成，候选只读 getter 基于 Slot 既有 PawnData/bAbilitiesGranted，不增状态；候选文件为 `Source/GGYGO/Teams/GGYGOCharacterSlot.h`，超出原 05 的 SquadComponent 两文件范围，须统筹另行冻结/授权。也可由统筹明确可信创建入口的完成前置契约；本轮不选择替代方案。
5. **跨 Squad 唯一接收**：当前 Slot 没有接收 Squad 标记，单靠 Owner/本地 Slots.Contains 不能排除另一 Squad 已接收。现有 PlayerState.GetSquadComponent 可配合 Controller.GetPlayerState 的对应关系，限定为该玩家当前唯一 Squad；需先冻结此限制及可信创建入口，不自行给 Slot 或全局新增租约状态。

容量候选复用 01，先处理合法重复请求再检查新增容量；现有数量必须合法且小于上限。新登记 false 保持 Slots/责任/ActiveIndex/控制关系不变，不截断。具体接口和权限尚未闭合，冻结这些前置契约前，不能直接按原 05 两文件候选实施全部接收契约。

补充运行时缺口：GameMode 选择 Experience 默认名单后直接生成，不经 SetRoster，也没有生成前的原始数量校验；04 是编辑器校验。后续 GameMode 装配步骤须单独登记共享容量门禁，不能把登记满额拒绝视为生成前校验完成，更不能借 05 越租约改 GameMode。

唯一产物为本预检和门禁记录；非目标是所有生产实现/测试/资产/图文。只读调查完成即冻结两记录，将未冻结契约交回统筹，不启动 05 源码。

### 后续需冻结的契约

- 超限名单拒绝并保留原数据；保存解析先检查原始成员数量，不能解析后过滤到上限内或截断。
- RegisterSlot 的 bool 表示已接收资源，不表示 Possess 成功；重复登记幂等，拒绝后责任留给请求者。
- 创建责任仅在登记成功后交接；与当前 Avatar 关联分开，不按 Actor.Owner 推断。
- GA 默认退出取消，Continue 必须显式配置；不可取消占用在副作用前拒绝切人。普通切人保留 Slot ASC、GE、CD 与 Avatar。
- 输入释放消费 07 的公开 ReleasePlayerInput 契约，待 ASC 与 Hero 会话全链冻结；不伪造 ASC 反初始化。
- 取消回调或 Possess 失败可以保留/恢复控制关系，但已取消 GA 不能承诺恢复；冻结退出接口时明确这个失败结果。

## 全部候选顺序

下表路径以仓库根目录为基准；`.h/.cpp`表示两个精确同名文件。依赖栏中纯数字指本批原子步骤，其他批次明确带“批”字。第14次时08-01～04生产源码已冻结并构建通过，仅授权两记录和05只读预检，05～15生产实现当时未授权。下表保留历史候选步骤与停止点，不授予当前写入权限。

| 步骤 / 唯一结果 | 精确候选文件 | 前置与只读接口 | 非目标 | 验收断言与停止点 |
| --- | --- | --- | --- | --- |
| 08-01 公共容量判断 | `Source/GGYGO/Teams/GGYGOSquadTypes.h` | 原有上限宏、CoreMinimal | 名单策略、调用方、测试 | 数量 0～4 通过，负数与超限拒绝；本层完成即冻结 |
| 08-02 保存名单超限拒绝 | `Source/GGYGO/Teams/GGYGOSquadPresets.h/.cpp` | 01；只读 AssetManager、SaveGame 基类 | 存档字段/版本、未知资产部分解析策略 | SetPresetMembers、Resolve、PostLoad 不截断；超限保留原数据；契约完成即停 |
| 08-03 Roster 原子接收 | `Source/GGYGO/Teams/GGYGOSquadComponent.h/.cpp` | 01；只读 PawnData | 登记、切人 | 先验证再替换，失败不清空原名单；完成接收契约即停 |
| 08-04 Experience 容量规则复用 | `Source/GGYGO/GameModes/GGYGOExperienceDefinition.cpp` | 01；只读 SquadTypes | Experience 装载、插件激活 | 编辑器容量校验与共享规则一致；不再声称截断超额成员；完成即停 |
| 08-05 成员接收契约 | `Source/GGYGO/Teams/GGYGOSquadComponent.h/.cpp` | 03、06批；只读 Slot/Pawn/ASC 关联 | GA 退出、批量销毁 | bool 表示接收，宿主/初始化/关联有效，重复登记幂等，责任交接一次；保留首次登记自动激活；完成即停 |
| 08-06 保存对象取得入口 | `Source/GGYGO/Player/GGYGOLocalPlayer.h/.cpp` | 只读引擎 LocalPlayerSaveGame | 移除旧调用、第二缓存 | 使用原缓存，错误 LocalPlayer 类型明确失败；新增入口完成即停 |
| 08-07 保存调用方迁移 | `Source/GGYGO/GameModes/GGYGOGameMode.cpp`、`Source/GGYGO/Player/GGYGOPlayerController.cpp` | 02、06；只读新保存入口 | 输入处理、插件生命周期 | 两个调用方迁移；拒绝保存不报告成功；非法保存不能回退默认名单；适配完成即停 |
| 08-08 移除保存模型反向依赖 | `Source/GGYGO/Teams/GGYGOSquadPresets.h/.cpp` | 07；只读 LocalPlayer 新入口 | 保存格式、蓝图资产 | 旧接口无调用后移除，保存模型不 include 具体 LocalPlayer；完成即停 |
| 08-09 装配入口幂等 | `Source/GGYGO/GameModes/GGYGOGameMode.h/.cpp` | 05、07；只读 PlayerState/Squad | GameFeature 计数、常驻第二装配状态 | 空玩家/非权威/已装配/同步重入安全；名单快照、回调后身份复核、守卫全路径释放；完成即停 |
| 08-10 失败成员回滚 | `Source/GGYGO/GameModes/GGYGOGameMode.h/.cpp` | 05、09；只读 06批 Attach/Detach | 回滚成功成员、代替 Combatant 清理 | Pawn 失败/缺 Extension/绑定失败/登记拒绝均回收未交付对象；全失败不报成功；完成即停 |
| 08-11 GA 退出策略数据 | `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h` | 只读 04批生命周期、05批相机资源契约 | 按 OnSpawn/SurvivesDeath 推断、未证明必要的资产迁移 | 默认 Cancel，Continue 显式选择，无新执行器；数据契约完成即停 |
| 08-12 ASC 退出判定与执行 | `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h/.cpp` | 11、07批 ASC 全链冻结、04批；只读 GA 实例 | 控制转移、替 GA 清理运动/命中/相机 | 不可取消先拒绝；覆盖活动实例/admission/非项目 GA；取消回调重入复核；07批未冻结即停止 |
| 08-13 切人适配 | `Source/GGYGO/Teams/GGYGOSquadComponent.h/.cpp` | 12、07批 Hero 会话全链冻结、06批 | DetachAvatar、重建 ASC、强制 EndAbility | 退出获准并完成必要取消后转移控制；失败/重入有结果；旧输入/retry 释放，ASC/GE/CD 保留；公开释放契约缺失即交回 07批 |
| 08-14 Squad 唯一清理 | `Source/GGYGO/Teams/GGYGOSquadComponent.h/.cpp` | 05、13；只读 06批 ExpectedASC 清理 | 资源转移业务、按 Owner/当前 Avatar 猜责任 | 先取出并清空责任记录；幂等；仅清自身接收资源；EndPlay 同入口且保护新宿主；完成即停 |
| 08-15 Logout 接入 | `Source/GGYGO/GameModes/GGYGOGameMode.h/.cpp` | 14；只读 PlayerState/Squad | 第二销毁链、插件释放、PlayerState 改造 | Logout 与 Component EndPlay 复用幂等清理；完成即停 |

依赖顺序：`01 → 02/03/04`；`03 → 05`；`06 → 07 → 08`；`02/05/07 → 09 → 10`；`11 + 07批ASC冻结 → 12`；`12 + 07批Hero会话冻结 → 13 → 14 → 15`。

01～10 不依赖 07 的新能力输入接口，但只允许逐步获得租约后执行；11 是单独的共享 GA 数据契约候选。12～15 必须等待 07 ASC 与 Hero 输入会话全链冻结，不能仅凭文件不重叠开工。同名文件的各步串行交接；GameMode 冻结后再交给 09 批。

## 历史候选测试与图文阶段（当时未授权，非当前租约）

生产接口冻结后单独分配：

| 步骤 | 精确新建候选文件 | 验收范围 / 停止点 |
| --- | --- | --- |
| 容量与保存测试 | `Source/GGYGO/Tests/GGYGOSquadCapacityTests.cpp` | 不截断、不覆盖、非法保存不回退；不借测试扩大生产写范围 |
| 装配与清理测试 | `Source/GGYGO/Tests/GGYGOSquadLifecycleTests.cpp`、`Source/GGYGO/Tests/GGYGOSquadLifecycleTestTypes.h` | 重入、失败点回滚、部分成功、幂等清理、新宿主保护；需要生产注入点时先重新分配 |
| 切人与持久状态测试 | `Source/GGYGO/Tests/GGYGOSquadSwitchTests.cpp`、`Source/GGYGO/Tests/GGYGOSquadSwitchTestTypes.h` | 不可取消、Continue、取消重入、输入释放、ASC/GE/CD 保留；不操作 UE/构建 |
| 局部 Markdown | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/结构.md`、`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/计划_队伍与装配.md` | 实现冻结后同步真实接口与已知限制，不标记运行通过 |
| 局部 Canvas | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/GGYGO_结构_队伍与装配.canvas`、`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/GGYGO_流程_队伍与装配.canvas` | Markdown 冻结后按技能检查 JSON、节点/边及链接 |

全局入口、路由、租约台账与实施状态由统筹独占。编译、自动化、PIE/联机分别记录，不因源码交回就标记全部完成。

## 08-05a1 追加预检（2026-09-30，历史授权，已冻结）

前文各轮范围作为历史保留；该轮当时仅授权`Source/GGYGO/Teams/GGYGOCharacterSlot.h`及本批两记录，由Teams组长直接执行。

- 唯一目标：新增 C++ 纯查询 `bool IsPawnDataInitializationComplete() const`，返回 `PawnData != nullptr && bAbilitiesGranted`。
- 只读依赖：既有 PawnData/bAbilitiesGranted 与 cpp 原授予流程。无新状态/复制/UFUNCTION；只表示服务器原授予循环完成，不保证所有 GA/GE 有效或客户端 Ready。
- 非目标：改 cpp、GAS/Squad/GameMode/LocalPlayer、05a2 接收/清理、测试、资产/Obsidian；不构建/UE/Git/代理。
- 断言：未设置 PawnData 或授予未完成为 false；现有服务器流程结束为 true；空 AbilitySets 循环完成也可 true；字段与流程不变。
- 顺序与停止点：本预检登记 → 单头查询 → 对比实际差异和 cpp 内容/哈希 → 三文件冻结交回。05a2 及 GameMode 仍候选，统一清理链冻结后才接 GameMode。
- 当前状态：查询已实现并静态核对；实际内容比对确认头文件只新增查询及说明，cpp 逐字和哈希未变。三文件现冻结交回，等待统筹复核；本步未构建或运行，到此停止。

## 08-05a2 追加拆分预检（2026-09-30，历史授权，已冻结）

- 该历史轮唯一写入者为Teams组长，`gpt-6.1-sol / xhigh`直接执行；当时只可写SquadComponent.h/.cpp和本批两记录，共四文件。
- 基线 SHA256：SquadComponent.h `02C437BC068612A9F55CBCACA98C6C7CEE2A2AD97B6D4124858A73E14AB54D3B`；cpp `7A14DBCD80EF0A332797CA8EBD85439BE7296749C8FDE463145ED1EE08263D75`；AtomicSteps `DD1DEB7B1C2802E2F6E2EDB50ADC5E79B5175CC7EA14A4ED34008FC349E54AB4`；Validation `BEBC486D905A589266F70ACAA6C1335518B9FDDE92002F4B2391214DF3793F51`。源码完整快照已在会话内保留，保护既有未提交改动。
- 唯一目标/归属：Squad 冻结借用成员接收与显式创建责任接收，Slots 仍是唯一成员名单；私有原始 Slot/Pawn 弱身份对只记录清理责任，不记录活动状态或当前 Avatar。
- 共享接口：既有 BlueprintCallable RegisterSlot(Slot) 改 bool，只登记借用；新增 private C++ RegisterCreatedSlot(Slot, APawn* OriginalCreatedPawn)，仅 friend AGGYGOGameMode，无 GameMode include。05a1 查询与06宿主/PawnExtension公开读回接口均只读。
- 依赖/顺序：权限与实际 PlayerState 唯一 Squad → 合法重复 → 新请求初始化/容量/世界/ASC与Avatar/PawnExtension/PawnData/连接身份 → 同步提交 Slots 与创建记录 → 现有 Deactivate/首次 Switch 尝试。合法重复不重放；自动激活前只读复核当前上下文和首位绑定，回调后不撤销接收结果。
- 断言：普通重复 true、不升级责任；创建入口对已借用成员 false；同 Slot/同原 Pawn 创建重复 true，不依赖当前 Avatar；不同原 Pawn false。新请求 false 不改名单/记录/控制；提交后 true 不因激活或 Possess 失败改变。弱身份用 HasSameIndexAndSerialNumber，不比较失效 Get() 的 nullptr。
- 非目标：GameMode/Slot/ASC/GA/Hero/LocalPlayer、切人策略、DestroySquad/EndPlay、测试/配置/资产/Obsidian及全局入口；不构建/UE/Git/代理，不引入业务转交框架。
- 停止点：本轮预检登记后仅实施两个生产文件；实际差异、API、状态唯一、失败/回调重入及弱身份静态审查后，四文件冻结交回，不接下一步骤。
- 清理门禁：统一清理消费者尚未落地，本步不关闭 C13；清理链冻结前，真实 GameMode 不调用创建入口。当前 GameMode 原 RegisterSlot 调用仍是借用接线，不交付创建责任；生成失败/超限及旧接线回收缺口仍待后续步骤。
- 验证基线：05a1 已第16次编译；统筹通报第19次完整构建 Succeeded、4 actions/10.68s、常规51/51，UE进程均退出。此结果不覆盖待实现的05a2或新增返回pin兼容；生产蓝图回读/编译与专项测试待单独授权。
- 当前状态：已实现并静态核对，现四文件冻结交回待统筹复核，本步未UHT/构建/运行。cpp除三项公开接口include和登记块外逐字保持；h仅登记注释/返回签名、GameMode前置声明、显式WeakObjectPtrTemplates include与private接收实现定义增加，其他字段/API不变。到此停止写入。
- 实际接口已落实：RegisterSlot(Slot)为borrowed bool；RegisterCreatedSlot(Slot,OriginalCreatedPawn)为private非UFUNCTION，仅friend GameMode。CreatedSlotResources弱身份对不复制、不保存当前Avatar或活动状态；同原始Pawn也不允许被第二份创建责任接收。
- 内部拆分均为同一接收契约：GetRegistrationController只读权限/唯一宿主，HasValidSlotBinding只读初始化/关联，RegisterSlotInternal共用验证/提交；没有新的执行生命周期、帧调度器或状态机。

## 08-M1-MD 拆分预检与基线（2026-09-30，历史G3授权，已冻结）

- 唯一写入者：Teams 长期组长，直接完成，无子代理。唯一目标是同步 Teams 实际类/关键跨模块接口及当前实施状态，不改变任何运行行为。
- 精确四文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/结构.md`、同目录 `计划_队伍与装配.md`、本记录、`AAADocs/Modules/Teams/Module_Repair_08_Validation.md`。源码、测试、资产、配置、全局入口及两 Canvas 均冻结；Canvas 留待独立 M2 租约。
- 四文件基线 SHA256：结构 `0C67FB2456FFE734551622DED20308677FC13FFD1263979A480FD0026006B8F8`；计划 `A0BEAF37E2DA5B836925C1869A0CC3EBE7A2F98151FBE86E7D8F64E51B4433CF`；AtomicSteps `D1299EFFB163982021243EE6300D33C7301D1384A87834B5966DC807BCF3CB62`；Validation `2DE1CD0F2A79336F6B5A9E834254FB84A98480D73C2D894018CB11FD18670F11`。
- 所属与依赖：Teams 负责容量词汇、Presets/Roster/Slots 与登记责任；PlayerState 是唯一队伍宿主，GameMode 是装配请求者；Combatants/PawnExtension 管 ASC/Avatar 绑定，Input/GAS 管输入与 GA 生命周期。只引用公开接口，不重定义其他模块状态或执行链。
- 冻结契约：08-01～04 容量/保存拒绝/Roster 原子替换/Experience 校验；05a1 服务器原授予完成纯查询；05a2 借用 bool、private 创建接收及原始弱身份责任。真实 GameMode 未迁移，统一清理未接，不关闭 C13。
- 顺序：登记本预检/基线 → 只读计划蓝图、项目 Obsidian 技能、实际代码、当前 MD 与两 Canvas/直接相邻接口 → 同步两 MD → 记录第20次有限证据 → 读回、差异和链接核对 → 四文件冻结交回。
- 验收断言：接口写清输入、作用、输出与权限；合法重复/禁止借用升级/Avatar 替换后原始创建身份/提交后激活失败不退责任均准确；第20次编译及既有51回归与专项/蓝图/PIE/网络区分；既有有效设计及跨模块链接保留。
- 停止点：四文件文档审查结束即冻结，不接源码、清理、GameMode、专项、Canvas 或任何 UE/构建/Git 操作。若 Obsidian 写入被权限阻止，保留可交回结果并报告，不绕过。
- 统筹新证据：第20次完整构建 Succeeded，6 actions/30.58s；常规51/51，报告时刻 `2026-09-30 06:56:28 UTC`、耗时 `0.446151853s`，0测试warning/error，UE exit0且已退出；实际生成反射含 RegisterSlot bool ReturnValue 与原 Slot 输入，private RegisterCreatedSlot 不反射。此证据不证明已有蓝图兼容或登记专项。
- 当前状态：08-M1-MD 四文件文档同步和静态核对已完成，现冻结交回；此前05a2“本步未构建”保留为当时历史，不再作为当前门禁结论。本轮没有构建/UE/Git或代理操作，到此停止。

### 08-M1-MD 唯一结果与停止交回

- `Teams/结构.md` 已同步实际类与状态归属、容量/保存/Roster/Experience接口、05a1纯完成查询、05a2两个接收入口和弱原始创建责任；写清输入、权限、输出与失败边界。
- `Teams/计划_队伍与装配.md` 新增9.0当前实施/门禁，保留Lyra布局与设计背景；校正PlayerState/Squad持有层次、Controller Owner、唯一宿主绑定、现有SwitchToSlot流程与阶段二登记顺序，原迁移1～4步和资产/验收指导保留为背景。
- 明确GameMode仍借用且忽略bool、非法保存仍可能回落默认、默认生成前容量/失败回滚、新取得入口、切人GA退出/输入释放、统一清理/Logout未实现；真实创建交付未接，C13未关闭。文档没有扩展共享接口或实施任何待办。
- 第20次构建日志、常规51报告、生成RegisterSlot参数及退出日志已只读核对；保留专项/蓝图/PIE/网络未验，过程及路径见Validation末节。
- 两MD共23处wikilink、13个目标全部存在；旧链接目标保留，9.1/9.2设计理由、迁移1～4步及原资产/验证指导逐字保持。两Canvas合法JSON、9节点/7边与8节点/6边、ID/端点有效，哈希未变；图内语义仍待M2，不能据此标记同步完成。
- 核对的15份相关生产h/cpp与两Canvas哈希未变。本会话没有写入全局入口；全局`计划_实施状态.md`期间发生并发变化，已记录前后hash而不回写/还原。
- **唯一四文件均停止写入并冻结交回；不自动接续M2、源码、测试、GameMode或清理。**

## 08-M1-MD-R1 复制语义短修预检（2026-09-30，历史授权，已冻结）

- 唯一结果：纠正Teams计划内把ASC Mixed解释为属性仅owner收件人的错误，区分Actor相关性、GE信息复制模式、AttributeSet属性复制条件；不改变复制策略或架构。
- 唯一写入者：Teams长期组长直接完成，无代理。精确三文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/计划_队伍与装配.md`、本记录、`AAADocs/Modules/Teams/Module_Repair_08_Validation.md`。
- 基线SHA256：计划`555C757A0C9809624F9B96EB6034F6B161F93F1590D881960218077E05A61487`；AtomicSteps`7A99FC4511FF6F77A4DE0B3F787B38846BED3D5250706CA30004EC894C8B4D4A`；Validation`F762CAB7132B8AD132D09B476FEE6D64DDB6E0BB10C7A65F7F0F844606CF40A7`。实际全文快照已保留。
- 只读primary依据：项目HealthSet.cpp:351～354为Health/MaxHealth/Poise/MaxPoise的COND_None；CombatSet.cpp:26～28为三基础量COND_OwnerOnly；本机UE5.8 AbilitySystemComponent.h:79～89定义EGameplayEffectReplicationMode，仅描述GE信息模式；Slot.cpp:23/30保留AlwaysRelevant/Mixed现状。
- 顺序：预检/基线 → primary源码与全文同类误说定位 → 仅9.3约束4、9.4复制说明、9.6迁移对应段校正 → 差异/来源/链接/只读文件hash核对 → 三文件冻结交回。
- 非目标：结构MD、两Canvas、源码/测试/资产/配置/全局入口，网络优化、队伍ASC或任何新需求；不UE/构建/Git/代理。既有设计理由及其他历史保持。
- 验收断言：计划不再声称Mixed决定属性owner-only；明确健康四量在相关Actor上依自身COND_None、Combat基础三量依自身COND_OwnerOnly；保留bAlwaysRelevant/Mixed实际设置，注明无网络动态验收。
- 停止点：三个文档文件核对完成即停止写入；不自动接M2或任何生产步骤。当前预检与短修已完成，三文件冻结交回。

### 08-M1-MD-R1 唯一结果与验收

- 仅替换计划9.3约束4、9.4第2～3项、9.6第1步复制说明三个强相关文本块；计划全文与基线应用这三处精确替换后的结果完全一致，其他架构理由和历史不变。
- 明确Actor相关性决定Actor/组件能否被客户端接收，ASC模式决定GE完整/最小信息，AttributeSet条件决定各属性收件。Health四量自身COND_None，Combat三基础量自身COND_OwnerOnly；保留当前AlwaysRelevant/Mixed及BossState Minimal。
- 原9处wikilink逐字保持；无新链接。结构MD、两Canvas及五份primary源文件共8项保护hash不变；没有源码复制策略/网络优化/队伍ASC需求改动。
- primary路径、准确行号、完整读回与未做网络动态验收已追加Validation。计划最终SHA256为`1ED12F4F8125CA694155E7BCF31164F4E5FFDCC0FD01A1AFE046370B4D1BC0F2`。
- **唯一三文件均停止写入并冻结交回；无UE/构建/Git/代理，不自动接续M2或任何生产步骤。**

## 08-M2a 静态结构图同步预检（2026-09-30，历史G3授权，已冻结）

- 唯一目标：Teams静态结构Canvas与结构MD同步已冻结08-01～05a2的职责、持有/继承、关键接口与当前缺口；完整时序和流程图留待M2b。
- 唯一写入者：Teams长期组长直接完成，无代理。精确四文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Teams/结构.md`、同目录`GGYGO_结构_队伍与装配.canvas`、本记录、`AAADocs/Modules/Teams/Module_Repair_08_Validation.md`。
- 基线SHA256：结构MD`35D4E7E429C69869C51E060F52E84108AC4700CEB71B7046509EE3EAA410F9E4`；结构图`8F5D4423508085F17C6A2F0EB7B2776D95BBA0FB0CB07A858CEF4E62D90C59FA`；AtomicSteps`BA5FCB4EC77C2A08E4C7BD8B9313E8428774C73769EC2B918F77C8D4694C3AF8`；Validation`AE469911DBE633443EEC82CC311CF6259E0417876100D8064011843A910837EE`。四份全文快照已保留。
- 冻结契约/依赖：Presets提供保存意图，容量词汇无状态；Squad唯一Slots/出战索引，原始弱资源对只记责任；Slot配置/查询经Combatants/PawnExtension/ASC公开接口协作；PlayerState持有唯一队伍，GameMode当前仍借用登记并忽略bool。创建交付/统一清理未接，C13不关闭。
- 顺序：租约、预检/基线 → 实际API/旧图/MD/技能只读核对 → 保留原9节点/7边ID与可复用颜色布局，按职责补容量/私有责任节点 → 同步结构MD状态 → JSON/ID/端点/标签/矩形/正文容量估算/链接/差异 → 四文件冻结。
- 验收：图内写接口输入、作用、输出/权限与实际跨模块链接，标清借用/private创建责任、不随Avatar迁移；只画静态关系，不塞整套运行流程。正文容量仅静态估算，不声称实际UI已验。
- 非目标：计划MD、流程Canvas、全部源码/测试/资产/配置/global、M2b与其他生产步骤；不UE/构建/Git/代理，也不接触统筹正在运行的独立Health诊断进程。
- 当前门禁：统筹通报第21次完整Succeeded，6 actions/32.23s；常规52/52 Success（07:50:12 UTC，0.457340658s，全叶errors/warnings0，UE exit0且已退出）。没有新增Teams专项，不扩大登记/蓝图/PIE/网络验证结论。
- 停止点：结构图与MD逐项核对后四文件停止写入，M2b需独立授权。当前预检、实施与静态核对已完成，四文件冻结交回。

### 08-M2a 唯一结果与验收交回

- 静态结构图由9节点/7边同步为11节点/10边；原9节点、7边ID和原节点颜色全部保留。新增capacity与created两个职责节点，以及Presets/Squad容量调用、Squad持有弱原始责任三条边；e4校正为Slot→CombatantState继承。
- 保留左侧保存、中间唯一队伍/控制器、右侧宿主/Avatar层次，中央列适度右移/加宽并调整高度，为容量与私有责任留空间。contract改为GameMode/Experience静态请求者与配置说明，不再塞完整装配时序。
- 图内明确Presets输入/超限拒绝、SetRoster原子替换、05a1纯完成查询、RegisterSlot bool借用/private friend创建入口、唯一Slots/弱原Slot+Pawn责任、Avatar替换不迁移、提交后激活失败不反交；GameMode仍借用且忽略bool，创建交付/统一清理未接，C13保持未关闭。
- 结构MD仅更新结构/流程状态与第21次有限门禁证据；API正文与此前有效设计保留。明确结构图已同步、流程仍待M2b，并指向计划及本批验证记录，不提前宣称流程同步。
- JSON、所有ID、端点、标签、节点矩形、正文静态容量及25处wikilink/12目标已核对；计划锚点与外部验证记录目标有效。模型最小正文余量32px，所有inline代码宽度估算可容纳；不代表真实UI/曲线渲染验收。
- 15份相关生产h/cpp、计划MD与流程Canvas共17项保护hash未变；第21次日志/52报告只读核对，无新增Teams专项，UE/独立Health诊断均未操作。
- 结构MD最终SHA256：`D994BFCA6560B3A18A8E9B7DA409EC70D7725D89E0DAC3180B262CD5C72FD6E5`；结构图：`2075062B2FA09545181DA3CBC0C1ED05861C0DD37A8FB58B18895458F5BAFAFF`。
- **唯一四文件均停止写入并冻结交回，不自动接续M2b或任何生产/专项步骤。**

## 08-M2b-Flow 拆分预检与基线（2026-09-30，当前唯一G4授权）

- 唯一目标与四文件范围见首屏；Teams组长直接完成。图同步当前实际路径、真实返回/产物、拒绝及明确未接目标；不把文档同步写成生产实施。
- 基线SHA256：流程Canvas`AA808F7DC1C8D2ADF9EAE6E668BF910DB0745A9F8DCB5C345C2C2DD0089941C3`；计划MD`1ED12F4F8125CA694155E7BCF31164F4E5FFDCC0FD01A1AFE046370B4D1BC0F2`；AtomicSteps`B75B1694DAC5F8D6BEDF8255CB05B4301AE2E0F55156A3C064664A1BD24411E6`；Validation`15BDAF3C35A8E034A9039E2B27DFD9D1EEEC08760C19D3E17A4979A31747ABB4`。实际全文快照已保留；结构MD/结构Canvas与相关生产/复制声明设只读保护。
- 冻结输入：01共享容量、02保存整体拒绝/0语义、03Roster原子替换、04编辑期默认容量、05a1完成纯查询、05a2借用bool/private创建及弱责任。GameMode仍旧接线，不读完成查询、忽略借用bool；生成前默认容量/半成品回滚/真实创建交付/清理未接。
- 顺序：租约/基线/本预检 → 实际GameMode/Presets/Slot/Squad装配与Switch源码只读回读 → 保留旧8节点/6边ID、增少量拒绝/准入节点 → 计划9.0按实际结构/流程状态同步 → JSON/引用/标签/矩形/静态容量/链接/保存读回与差异 → 四文件冻结停止。
- 原子结果：流程仅同步当前行为与缺口；计划仅9.0状态/有限证据；本记录首屏和旧授权标题明确历史，保留结论/证据；Validation登记实际静态验证与未验边界。
- 验收：保存超限0不加载但当前仍错误回落默认；Slot查询只由新登记验证读取；PawnData/Attach后借用bool被忽略；拒绝前Squad不变而GameMode无回滚；true非Possess保证；Switch顺序准确，不每次重InitActorInfo；GA退出/不可取消/Input release/回调事务未实施。三层复制事实保持。
- 非目标：结构MD、结构Canvas、源码/测试/资产/Config/global、Nav提示清理或任何新接口/更多文件；不UE/构建/Git/代理。52既有门禁不是Teams专项或网络证据。
- 停止点：四文件检查后立即冻结，不自动接Nav或生产/专项。预检、图文同步与静态核对已完成，四文件冻结交回。

### 08-M2b-Flow 唯一结果与停止交回

- 流程图由8节点/6边同步为11节点/12边；原节点/边ID及原节点颜色全部保留。新增saved-refusal、receive-checks、assembly-refusal三个节点与六条分支边；e3接实际RegisterSlot准入，e5左向待命说明，e6明确未实施远程上报。
- 主链按真实触发、三级名单、两阶段生成、借用接收、提交/自动激活、SwitchToSlot控制顺序组织。PawnExtension缺失时不保证SetPawnData；Slot完成查询不是GameMode的新接线，只由新接收验证读取。
- 拒绝节点写清原始保存>4返回0且加载前拒绝、原数据保留，但GameMode仍错误回落非空默认；登记提交前false不改Squad，而GameMode忽略bool且半成品无回滚。true只说明成员接收；私有创建入口已存在但真实交付/清理未接。C13保持未关闭。
- 原有长期Slot/ASC与复制约束保留为独立说明：Actor相关性、GE信息模式、各属性COND分别负责；Mixed不决定属性收件，健康四量COND_None、Combat基础三量COND_OwnerOnly。GA退出/不可取消准入/Input release/完整回调事务、运行默认容量和统一终止回收明确未实施。
- 计划仅9.0改动：纯查询实际读取者、第20次历史/第21次最新有限门禁及结构/流程已同步状态；9.0前导与9.1以后逐字不变，原9处计划链接全部保留。结构MD/Canvas中的旧“待M2b”Nav提示本步只读，需后续独立授权。
- 首屏已替换过时第14次当前权限；旧授权标题/范围改为历史且保留结论和门禁证据，不再推导活跃源码或Obsidian租约。本步预检、实现与验证分阶段记录，没有扩大范围。
- 保存后完整读回与期望JSON/计划精确替换结果一致；11节点/12边全局ID、端点、侧向、标签有效，无矩形重叠。流程/计划19处wikilink、11个目标及计划/实施锚点有效；正文保守估算最小余量46px，inline代码宽度通过。仅静态容量，未打开UI/实测Bezier连线或标签。
- 20项保护hash前后不变：15份相关生产h/cpp、结构MD/结构Canvas、HealthSet/CombatSet与原生ASC声明。流程最终SHA256：`75550CC5DC89673F796EB75FF5FA88BEA1D33534BFE2990A7C4DA3FE6DCE4D4E`；计划：`13CAC5D8916BF3D654675CEADE6E6963F7014CD778AC571FBB53AE646F5572A9`。保护结构MD：`D994BFCA6560B3A18A8E9B7DA409EC70D7725D89E0DAC3180B262CD5C72FD6E5`；结构Canvas：`2075062B2FA09545181DA3CBC0C1ED05861C0DD37A8FB58B18895458F5BAFAFF`。
- 第21次构建/52既有回归只读复核，未增加Teams专项/蓝图/PIE/网络证据。无源码/测试/资产/Config/global写入、UE/构建/Git或代理操作。
- **08-M2b-Flow唯一四文件均停止写入并冻结交回；两记录最终hash见交回消息。Nav、生产接线、清理与专项均未接续。**

## A8 / 08-Include-R1 单一结果预检（2026-09-30，统筹极小短修授权）

- 唯一写入者：Teams长期组长直接执行，gpt-6.1-sol / xhigh，无代理；已核对当前Parallel Schedule的A8租约。本节为新的精确范围，前文各轮冻结结论保留为历史。
- 唯一结果：GameMode.cpp直接包含已调用的UGGYGOPawnExtensionComponent完整类型头，消除对Unity分组/间接include的依赖；不改变运行行为、模块职责或共享API。
- 精确三文件：Source/GGYGO/GameModes/GGYGOGameMode.cpp、AAADocs/Modules/Teams/Module_Repair_08_AtomicSteps.md、AAADocs/Modules/Teams/Module_Repair_08_Validation.md。生产只新增一行 `#include "Character/Components/GGYGOPawnExtensionComponent.h"`；两记录旧原文/原字节前缀全部保留，只追加。
- 基线SHA256及字节数：GameMode.cpp `D69653AE7961F10BD184F9FC909CFDD893F5679B7619DD03E3A4276EBFB03032` / 12937；AtomicSteps `3CA157AB562082EFE02116641101E6D6AD289D7515A542A21FD6941A5152765D` / 45277；Validation `1AABCFB0F67092F3745EB5FA4BD5F2268B4EDE8FB2A9D26DEB92C18E79A30594` / 50977。GameMode.h保护 `52F82A24169F6B53C67076FF7467AFA17EA31AC1880421369A897DB178709F33`，PawnExtension.h保护 `6190EB9134ECDE4735FC67C0CD564D87C3EEDAE9BC477E16ACA296368F7C96FD`。
- 只读依赖：现有PawnExtension.h公开FindPawnExtensionComponent/SetPawnData、当前GameMode.cpp373/375实际调用、Build28日志。只是补足已有Character依赖的直接声明，不新增模块依赖或生命周期。
- 已回读Saved/Logs/ModuleRepairBuildGate_20260930_28.log：Result Failed (OtherCompilationError)，总54.17秒，UBA51.67秒；基线GameMode.cpp373/375两条C2027、一条C3861。新增测试源码分组暴露旧间接include缺口。实际exit6、session18496结束、未运行UE/自动化且未链接新运行时/Editor DLL由统筹通报；不能据已有编译动作称专项通过。
- 顺序：先追加本预检 → 唯一生产include行 → 删除该新增行的整文件逆向hash/字节核对 → 两记录追加实际失败、短修与未重建事实 → 三hash及旧记录prefix证据交回 → 立即冻结，由统筹安排Build29。
- 验收断言：原源文件UTF8无BOM/LF保持；新增行唯一；逆向删除该行精确恢复原12937字节及D69653AE…；API调用/其他代码字节保持；GameMode.h/PawnExtension.h保护hash不变；记录prefix SHA256等于各自原整文件hash。
- 非目标：TryApplySavedRoster、装配/回收/业务兜底、所有头/测试/Content/Obsidian/global、其他三个新专项、UE/UBT/自动化/Git/代理。无架构或资产接线信息变化，不空改Obsidian。
- 停止点：单行与追加记录静态核对后立即停止三文件写入；未重新构建，不能宣称Build28失败已被新构建推翻，不接续08-05b或任何生产步骤。当前预检先登记，生产尚未写入。

### A8 / 08-Include-R1 唯一结果与冻结交回

- 生产仅新增第8行 `#include "Character/Components/GGYGOPawnExtensionComponent.h"`，放在既有Character直接includes处；新增62字节，文件现12999字节。没有修改调用、分支、接口或业务兜底。
- 保存后完整读回与基线插入唯一一行的期望全文完全相同；从实际字节移除新增行，与原12937字节逐字节相等，整文件逆向SHA256恢复 `D69653AE7961F10BD184F9FC909CFDD893F5679B7619DD03E3A4276EBFB03032`。
- GameMode.cpp最终SHA256：`3D961C1FA423A0430ED1E031F82057354516F0FCEEA1BD7C9EB552DDBE2D615F`。GameMode.h及PawnExtension.h保护hash保持基线值；既有模块/生命周期/清理责任及资产接线无变化，没有新增状态/执行链/循环依赖。
- 两记录仅尾部追加；旧AtomicSteps前45277字节SHA256仍 `3CA157AB562082EFE02116641101E6D6AD289D7515A542A21FD6941A5152765D`，旧Validation前50977字节SHA256仍 `1AABCFB0F67092F3745EB5FA4BD5F2268B4EDE8FB2A9D26DEB92C18E79A30594`。最终prefix证据及三hash在交回消息提供，前文全部历史结论保留。
- Build28实际失败、exit6/54.17秒/UBA51.67秒及373/375三条类型错误保留；短修尚未重新构建，不声称失败已被新门禁推翻。未运行UE/自动化/UBT/Git，未修改三个新专项或任何其它文件。
- **A8/08-Include-R1唯一三文件已停止写入并冻结交回；由统筹统一安排Build29，不接续装配/回收/业务兜底、08-05b或其它步骤。**


## 08-NativeCreatedTermination / 08-05b 实际终止消费者预检（2026-10-04，最新四文件租约）

本节覆盖前文所有历史“当前／许可”范围。唯一作者为 Teams 长期组长 01a0e5b5-910c-71e3-a75c-b17c22fea33e，gpt-6.1-sol / xhigh，直接执行，无子代理。
- 唯一目标：真实 native DestroySquad、EndPlay、OnComponentDestroyed 共用一个终止消费者，关闭本组件准入，精确消费已接收的原创建 Actor 责任。
- 精确文件：Source/GGYGO/Teams/GGYGOSquadComponent.h、同名 cpp、本 AtomicSteps 与 AAADocs/Modules/Teams/Module_Repair_08_Validation.md；不新增文件。
- 基线：Squad.h 0CB4297352E498015BCE6D550D64B2F470CFB3D51B9894046091E2E7C71261A5（9395 bytes）；Squad.cpp 8D94EB2E25BCEC4F9520537D79B3E6EC58CF0750E08283448B1A0FFE36062854（13268）；AtomicSteps A563C97C14D926EC2CEB124631AE742420BB1160D28E86F0C3854D8DFBC2EBD6（49752）；Validation E7683ACFE8DE21E59F93E2240ABD55C779C746EF01112D93C4C76EBD27A2116A（54239）。
- 前置已核对：Saved/ValidationRecords/CombatantsHostLifecycleH3_20261004_RootAcceptance.json；Host Destroyed 与 EndPlay 在 Super 前共用原清理链，覆盖未 BeginPlay 与 owner-only。其两源冻结且 hash 与统筹凭据一致；H3 未新编译/UE。
- 职责：Slots 唯一成员事实；CreatedSlotResources 唯一原创建 Actor 责任。Teams 只调用精确原 Actor Destroy；Host/Extension/ASC 自管绑定与能力资源，Teams 不捕获 H/Context、不认证 ASC、不调 RequestAvatarBinding/Clear/Detach/Hero 清理。
- 顺序：本预检登记 → 关闭准入并移出原弱责任、清 Roster/Slots/ActiveSlotIndex → 原 PS/Controller/Squad/Slot/Pawn 关系仍对应才首次 UnPossess → 空出战通知最多一次 → 逐原 Slot Destroy，再原 CreatedPawn Destroy → 保留被拒绝的存活责任／最终不能保留时明确诊断 → 有限源码核对、保存回读、记录与四文件冻结。
- 不变量：借用 Actor 不 Destroy；不用 Owner 或当前 Avatar 推算创建责任；原生接受/已经销毁/进入销毁只说明已移交原生，不冒称物理清理全部完成；已移交单项不重复请求；拒绝残余只供后续明确入口或生命周期调用，不自动重试、不 Tick。
- 外调重入：只有当前栈取得移动出的责任；重入只记录最终组件销毁意图，不再消费。任何 Actor 回调后重取原弱对象；旧登记/切人/表现栈在终止或自身失效后停止尾写、表现副作用与 Possess；已提交登记仍 true。
- 有限验收：真实三入口共用；外调前成员为空；原 Actor 弱身份消费与独立残余保持；首次控制/通知；重入/终止旧栈停步；普通容量/名单/正常切人规则保持；无第二名单、绑定清理器、时钟、来源或执行器。
- 只读依赖：冻结 Host H1/H2/H3、ASC、Extension、Slot/PlayerState/Controller 与原生生命周期；路由/台账/排程/统筹基线；Teams 架构笔记仅核对。
- 非目标：GameMode 创建交付、部分 Spawn 回收与 Logout；GA/输入/切人玩法；名册来源、保存策略；共享源/接口、测试/严格矩阵、资产、网络协议、Engine、Saved、外部 Obsidian/Root 全局；无 Build/UE/Git。
- 停止点：第五文件、未冻结接口或业务取舍立即停止相关接缝；四文件有限检查后冻结，不自动接续 GameMode 或图文。源码完成不关闭 C13；外部图文信息变化另由统筹租约接续。



### 08-NativeCreatedTermination 实际结果与冻结（2026-10-04）

- 实际四文件范围保持：Squad h/cpp 与两份既有记录；没有创建准备文件或测试。public native 非反射 void DestroySquad、protected EndPlay/OnComponentDestroyed 均调用 private ConsumeCreatedSlotResources；不是无人调用的助手层。
- 消费者在首次外调前关闭本实例准入、MoveTemp 原 CreatedSlotResources、清空 Roster/Slots/ActiveSlotIndex。原控制快照只用于原 PS/Controller/Squad/Slot/Pawn 的 Authority/World/Owner/双向 Possess 关系核对；关系不成立跳过 UnPossess，不影响原资源消费。空通知只在首次入口且组件仍有效时发一次。
- 回收每项仅用原弱 Slot/Pawn 身份调用 Actor::Destroy。Host H3 独占原绑定终止，覆盖 Destroyed/EndPlay 与未 BeginPlay；Teams 没有 H/Context、RequestAvatarBinding、Clear/Detach 或 Hero 清理调用。
- 已移交原生销毁或已经退出的单项从责任中退休；只保留拒绝的存活原身份，部分配对中的已移交字段清空，避免 BeginPlay 延迟接受后因另一项失败而重复 Destroy。后续回调让先前拒绝对象退出时仅退休原身份，不再请求。没有第二份常驻名单/责任表或自动重试。
- 重入只提升最终组件销毁标记；外层栈独占移动出的责任，Actor Destroy 闭包不捕获 this。外调后重取原弱对象；组件仍有效则把残余移回既有 CreatedSlotResources，最终不能继续持有时对每个存活残余明确 Error。原生接受不是物理/绑定/GA 清理全部成功。
- SetRoster/GetRegistrationController/切人/复制通知加入终止边界；登记提交前的完整接收体保持，提交后 Deactivate/自动激活的旧栈在终止或组件失效后停止但仍返回 true。切人/表现原外调间使用原弱对象与终止检查，不在终止后重写 ActiveSlotIndex、继续表现或 Possess；有效正常路径沿用原顺序，不新增 GA/输入/玩法政策。
- 有限实际源码核对：三入口同消费者、退状态先于外调、唯一 Actor Destroy 调用点按原 Slot→原 Pawn；9 个既有方法全文保持；SetRoster 移除新增入口 guard 精确恢复原方法，GetRegistrationController 移除终止条件精确恢复；RegisterSlotInternal 在默认待命标记之前的整个接收/容量/责任提交段逐字保持。
- 两源 UTF8 无 BOM、LF、末尾 LF、无行尾空白。最终 Squad.h SHA256 7799357DCA5B1B3A01E2D3EF4CFB709C1EE9F8BD05A550C6145294C92738AACD / 10616 bytes；Squad.cpp 0B9C8C960D925907FBC582E5DD78019CC0F869CE8C59D66EE5F4903CB451CD91 / 23833 bytes。
- 历史保护：AtomicSteps 原前 49752 bytes SHA256 A563C97C14D926EC2CEB124631AE742420BB1160D28E86F0C3854D8DFBC2EBD6；Validation 原前 54239 bytes E7683ACFE8DE21E59F93E2240ABD55C779C746EF01112D93C4C76EBD27A2116A。两记录只尾部追加本预检与实际结果。
- 架构核对：终止准入/重入/最终通知三标记只属于本组件生命周期，不替代 Slots 装配事实；原创建责任仍唯一；表现检查只读原对象/当前 Avatar 对应，无 ASC 凭据或第二执行器、循环依赖、Tick。回收/名单/切人均依赖本组件既有状态，本次没有引入另一模块职责或机械拆文件。
- Obsidian 已只读核对计划蓝图和 Teams 结构/计划，确认终止接口/实际状态与旧清理调用说明需要同步；本租约明确禁止外部图文写入，已留交接项，须统筹后继四图文租约。当前源码步骤完成不冒称整个任务/图文/模块完成。
- 未运行 UHT、编译、UE、测试/矩阵、资产、网络或 Git；未写 GameMode/共享接口/Host/ASC/Hero/GA/Engine/Saved/Root 全局。GameMode 仍未交付创建责任，部分 Spawn 回收/Logout 与完整切人退出另步，C13 保持开放。
- **本四文件源码/局部记录完成有限核对并停止写入，冻结交回；没有下一批自动许可。** 最终两记录 hash 由交回消息提供。


## 08-GameModeCreator-B 记录拆分预检（2026-10-04，仅两记录租约）

本节为创建者 A 已完成后的记录步骤 B，覆盖前文历史许可描述，不重新取得源码写权。唯一作者：Teams 长期组长 01a0e5b5-910c-71e3-a75c-b17c22fea33e；沿 gpt-6.1-sol / xhigh、Fast 默认关闭约定直接执行，无子代理。

- 唯一目标：尾部记录创建者 A 的原资源捕获、准备、交付及未交付失败回收源码事实，区分作者有限证据、统筹有限接受、未编译/运行和剩余边界。不是本步重新实施 A。
- 精确文件：本 AtomicSteps 与 AAADocs/Modules/Teams/Module_Repair_08_Validation.md。唯一写入者为本会话；不新增摘要或第五文件。
- 写入前基线：AtomicSteps 57288 bytes / DD0717E4A7C67049963AE8A964CCDF2130FD220F365F0F9C6065114C17C4465B；Validation 62064 bytes / 4D0386B045DF31F2F4A5BE09FEFBA40E4034BEFDDB15EB43D8E6BD05F33D3E4C。保持旧字节，只追加。
- 只读依赖：已冻结 GameMode h/cpp、Squad 创建接收/终止契约、Slot 完成查询、Host/Extension 原资源接口；Saved/ValidationRecords/TeamsGameModeCreatorA_20261004_RootAcceptance.json。两 GameMode hash 与该收据独立列值匹配。
- 共享接口不变：private friend RegisterCreatedSlot 的 false=未接收、true=已提交原创建责任；不保证激活/Possess。Squad 仍唯一消费已交付原 Actor，Host 唯一协调绑定关闭，ASC 执行事务。GameMode 只拥有尚未交付的真实生成对象，不捕获 H/Context 或执行绑定清理。
- 先后顺序：核本两记录基线与 A/root 收据 → 两记录均追加本预检 → AtomicSteps 追加 A 唯一结果/停止点 → Validation 追加作者/统筹证据及未验证项 → 有限保存读回、历史前缀/最终 hash → 两记录冻结。
- 原子记录输入/输出：A 的两源真实产出及冻结 hash为输入，追加的可审查事实和验证边界为输出；不生成新的生产行为或运行证据。
- 非目标：所有源码、共享接口、测试/严格矩阵、资产、Saved、Obsidian、全局入口；名单非法默认、ChooseStart Identity、Logout/fullSwap 或其它玩法政策；无 UHT/Build/UE/Git。
- 验收断言：原 57288/62064 字节前缀 hash 保持；追加顺序为预检后结果；记录内容区分原责任三阶段、交付 bool 的历史事实、原生接受与物理清理；两源继续冻结；C13 不关闭，Gate57 不包含本版 A，未编译/运行可见。
- 停止点：有限两记录核对后停止写入并冻结；只读提出后继 Teams 四图文精确范围，未经下一租约不写外部图文、不接续源码/运行。原失败与旧门禁保留为历史。

### 08-GameModeCreator-A 实际源码结果与步骤 B 交回（2026-10-04）

- A 的实际写入范围仅 Source/GGYGO/GameModes/GGYGOGameMode.h、.cpp；已完成并冻结。h 6082 bytes / 69A9197A10F8E84169A0D5C6979D75844D342400920445056ABB82F519D34969；cpp 36740 / C8EB059A68948684A9FB8821EF26D296D0D672E2070182B9731CB8B8AEB722B9。本 B 不改源码。
- 三类寿命明确分开：生成/交付中的原 Actor 仅由本次同步栈持有；true 交付后仅归 Squad 的既有 CreatedSlotResources；原生拒绝且仍活的未交付原身份才保留在 GameMode UntransferredSquadActors。后者不保存名单、出战位、当前 Avatar、绑定 H/Context 或完成/Ready 状态，不与 Squad 竞争同一义务。
- 原资格：本次 Context 固定原 GameMode/World/GF Session/Controller/PlayerState/唯一 Squad/Experience 弱身份与 Session只读引用，复用既有 GF 资格及 Squad 只读登记上下文。输入 PawnData 复制为本次弱身份快照，不跨后续外调持有 Roster 容器引用；同 Controller 的同步重入保护由原栈退出退休，不作为装配状态。
- 两个 Spawn 用 native CustomPreSpawnInitialization 在全局 pre-spawn/项目回调前记录实际原 Actor，不在钩子中外调或清理。原生返回后重检原对象/资格；即使 Spawn 返回空也保留已捕获身份。先完成全部 Slot，再生成各 Pawn，正常两阶段顺序保持。
- SpawnSquadSlot/SpawnSquadMember 为 native准备 bool，false 仍在 OutActors 暴露原产物，不能把阶段成功当作责任交付或所有GA/GE/客户端Ready。Slot读回原PawnData与原初始化完成查询；Pawn缺原Extension、PawnClass无效或原注入读回失败明确拒绝，不返回替代Pawn，不把缺组件表现为正常成功。
- 原 Slot->AttachAvatar 仍是 Host 唯一绑定入口；GameMode不抄Squad准入规则、不持H/Context，也不直接写/清ActorInfo。外调后原身份/资格失效停止旧栈，未交付原物仍由同步栈收尾。
- 真正交付点已从忽略 bool 的借用 RegisterSlot 改为 private friend RegisterCreatedSlot(实际原Slot, 实际原Pawn)。调用前将原对移出 Creator 可清理集合，交付期间仅原同步栈等待返回；GameMode重入关闭不消费这对。返回后先消费 bool：true 立即退休 Creator责任，即使回调已终止对象；false 仍由 Creator请求原对象销毁。之后才重检当前资格，不按成员数、存活、当前Avatar或Owner反推历史交付，不反交、不借用兜底、不回滚已交付成员。
- 未交付消费只有一个 Actor.Destroy调用点，按原Slot后原Pawn。原生接受/原对象失效/已销毁中逐字段退休请求义务；拒绝且仍活保留精确原字段和模块/Creator/原Controller/PawnData/资源/原因诊断。当前请求遇拒绝停止，后续同PC请求遇存活残留拒绝新生成；无Tick、自动重试或第二绑定执行器。
- GameMode Destroyed/EndPlay 保持既有GF Close先行，弱重取原Creator后调用同一残留消费者，再Super。残留移到唯一局部栈后外调，重入只记最终意图，已退休字段不重复请求；最终仍无法移交原生的原对象明确Error；Creator已不可用、无法继续保留原义务时也明确诊断，不伪造保留或物理清理成功。已交付成员只能由Squad既有终止消费者请求销毁，Host依原生生命周期唯一关闭原绑定。
- 作者有限证据：10个既有方法全文保持，包括构造、InitGame、InitializeGameFeatureSession、IsGameFeatureCallerContextCurrent、AreGameFeaturesReady、CanAssembleForGameFeatureContext、SpawnSquadForPendingPlayers、HandleStartingNewPlayer_Implementation、CloseGameFeatureSession和TryApplySavedRoster；无关头部逆向恢复原文。两生命周期方法除原弱捕获/残留调用外保持；旧GF与外层派发、名单来源逻辑、StartSpot为空->Identity政策未改变。两源保存读回一致、UTF8无BOM/LF/末尾LF/无尾空白；A交回时9份列明只读源码/记录和4份冻结Obsidian hash保持。以上是作者证据，不冒称root独立证明全部字节。
- 统筹独立两hash匹配并有限源码/原生Squad bool合同审查接受：Saved/ValidationRecords/TeamsGameModeCreatorA_20261004_RootAcceptance.json，状态 finite_static_accepted_not_whole_Teams_complete。收据分别列root有限审查及authorOnlyEvidence；不是完整动态验收或对每个旧方法的独立前缀证明。
- **本版A尚未UHT/编译/UE；Gate57两个DLL不含此版。** 原ActorInfo原生生命周期单叶Success属于原门禁，不证明Teams正式创建链。统一编译和必要UE冒烟由统筹安排；历史Build55/56、原严格失败和未验证资产/网络保留，不扩矩阵。
- 剩余：名单非法保存回落/默认运行容量、ChooseStart Identity、整队成功与完整创建政策、Logout、完整切人GAS/输入链及正式资产/网络仍开放；未交付失败回收已有源码不能等同整队事务完成，C13不关闭。B不修改这些政策。
- 架构核对：装配事实仍唯一归Squad Slots；创建栈、同PC请求保护、拒绝原Actor台账只属于GameMode自己的生成责任生命周期，交付前后责任互斥；没有循环依赖、第二Roster/Ready权威、绑定清理链、帧调度或隐式业务成功。两源中的准备/交付/回收共同关闭一条原责任契约，未按任意行数拆分无关职责。
- 当前Obsidian四图文仍为A前的冻结事实，包含“GameMode仍借用/未交付/半成品未回收”等待更新描述。本B仅只读列后继精确段落/节点/边范围，不能冒称同步已完成；四文件需统筹独占租约。
- 本B仅尾部追加预检与结果；旧AtomicSteps前57288 bytes及Validation前62064 bytes保持原hash。最终字节前缀证据与两记录最终hash交回消息提供。
- **两记录完成有限保存读回后停止写入并冻结；GameMode两源继续冻结。** 不接续源码/Obsidian/测试/资产/Saved/全局/UE/Build/Git；没有下一步自动许可。


### 步骤 B 收束追加：Gate58 实际失败（2026-10-04）

- 上述 A 交回及 root 接受时“未编译”的记录保持原文，属于当时历史；后续统筹已尝试 Gate58，Saved/ValidationRecords/ModuleRepairGate_20261004_58_Result.json 实际为 Failed (OtherCompilationError)、exitCode 6，8 actions / 26.4s。
- 两处门禁错误：Camera 旧测试 GGYGOCameraLifecycleTestTypes.h:97 仍调用已撤去的 HandleAbilitySystemUninitialized（C3861）；Hero GGYGOHeroComponent.cpp:621 局部 Character 遮蔽 line 577 同名变量（C4456）。本 B 不修改两模块；Hero 后续机械修复冻结仅为统筹通知，不改写 Gate58 失败结果。
- 收据 sourceChanged=[]、protectionChanged=[]（统筹列明 45 保护）、DLLChanged=false、smokeRun=false；没有本版 A 的成功统一编译、新 DLL 或运行证据。既有失败、C13 及资产/网络未验继续保留。
- 本次仅追加本事实，有限核两记录保存读回、原历史与本 B 已交回全文前缀、hash；不扩大审计或严格矩阵。核对后两记录立即冻结；后继四图文另等精确租约。
