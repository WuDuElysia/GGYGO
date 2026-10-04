# 第15批 System 验证与交接

日期：2026-09-30。实读第22次完整构建Succeeded（5 actions/22.16秒）及08.50.07 UTC报告55/55 Success，全部叶errors/warnings0；T2c1b新叶Success（0.010829798877239227秒、entries=[]），T2a/T2b/T2c1继续Success。此前T2c1b未编译/运行是静态交回历史。现仅授15-M2-Evidence四文档：System结构MD/Canvas及本批AtomicSteps/Validation，已先登记后完成最小证据同步，16项静态校验通过，四文件冻结停止；源码/types/其它测试/图文/global/资产及UE/构建/Git/代理只读或禁止操作，不扩GC/GA-GE/其它生命周期/共享预载选择/Cook结论。

## 15-A（历史记录）

状态：本层源码和记录已冻结交回，静态审查完成。精确范围与断言见 `Module_Repair_15_AtomicSteps.md`。本层不表示第15批整体完成。

基线核对：项目Source/Plugins脚本、C++及配置检索中，`UGGYGOAssetManager::Get()`唯一生产调用位于 `Source/GGYGO/System/GGYGOGameData.cpp`；AssetManager内部定义不算外部调用。未发现其他项目生产消费者。GameData本身保持已有可空返回类型。

已确认接口边界：项目只查询 `GEngine->AssetManager`，不接管引擎初始化。引擎 `F:/UE_5.8/Engine/Source/Runtime/Engine/Private/UnrealEngine.cpp` 的 `UEngine::InitializeObjectReferences` 在AssetManagerClassName无法解析时可先Fatal；本修复不能保证任意无效类路径都能启动。项目TryGet处理引擎/Manager未就绪及真实Manager类型不符。

## 15-A验证分层（历史记录）

- 当前允许：源码及调用点只读检索、三文件差异审查、架构静态审查、授权记录。
- 当前未执行：UHT、C++编译/链接、UE自动化、错误配置动态回归、PIE、Cook、生产资产回读。
- 不引用前批构建或自动化结果证明15-A通过。

## 15-A实际变更与静态结果（历史记录）

仅修改三份授权生产文件并新增两份授权记录；本轮没有使用Git命令。

| 文件 | 实际变更 |
| --- | --- |
| `Source/GGYGO/System/GGYGOAssetManager.h` | 移除项目类的引用返回Get声明，改为`static UGGYGOAssetManager* TryGet()`；说明未就绪/类型不符的可空契约及引擎初始化Fatal边界 |
| `Source/GGYGO/System/GGYGOAssetManager.cpp` | TryGet检查GEngine和引擎持有的Manager；成功只返回Cast所得实际实例；失败记录区分就绪与类型的诊断并返回空。删除FallbackManager/NewObject/AddToRoot；显式包含Engine/Engine.h；全部AssetManager诊断改用DEFINE_LOG_CATEGORY_STATIC定义的LogGGYGOSystem |
| `Source/GGYGO/System/GGYGOGameData.cpp` | 唯一生产直接调用改为TryGet并判空；获取失败传播nullptr；已有GetGameData加载逻辑保持 |
| `AAADocs/Modules/System/Module_Repair_15_AtomicSteps.md` | 登记A精确范围、状态、断言、停止点及未授权后续候选 |
| `AAADocs/Modules/System/Module_Repair_15_Validation.md` | 登记实际变更、已执行静态检查、未验证边界及待同步笔记 |

已执行检查：

- `rg`交叉引用Source、Plugins及AAADocs脚本/C++/头文件：生产代码只有TryGet定义与GameData.cpp调用，没有残留的项目`UGGYGOAssetManager::Get()`调用；配置的旧Get说明作为H待办保留。TryGet非UFUNCTION，不涉及新增蓝图调用接口。
- 三份源码逐行读回与补丁差异审查：StartInitialLoading/GetGameData/LoadGameDataOfClass的执行、缓存和锁保持原实现，仅加载警告的日志类别变化。
- PowerShell只读结构断言10项全部为true：可空声明/定义、就绪守卫、实际实例Cast、无兜底/Root、文件内日志、无GAS日志依赖、GameData判空、无旧调用、原加载语句保留。此检查不是编译、单元测试或动态验证。
- 架构静态核对：没有新增权威状态、缓存、执行链、调度器或清理责任；不再创建第二Manager；System的AssetManager不引入AbilitySystem日志头。保留所有其他模块既有修改和System GameplayTags增量。
- 只读核对Obsidian计划蓝图及System结构/Canvas：旧Get/兜底描述确认需要更新，按本层禁写约束登记待办。

15-A冻结交接：三生产文件与两记录文件停止写入；随后统筹仅重新开放15-B四份System源码及两份记录。C–H/T1–T3/M1–M2仍需单独授权。

## 15-B实际变更与冻结API

精确范围：`Source/GGYGO/System/GGYGOAssetManager.h`、`Source/GGYGO/System/GGYGOAssetManager.cpp`、`Source/GGYGO/System/GGYGOGameData.h`、`Source/GGYGO/System/GGYGOGameData.cpp`及本批两份记录。没有扩大租约。

- Manager删除仅供内部使用的通用LoadGameDataOfClass、按类Map和锁，替换为GameData及三项GE的四个UPROPERTY(Transient)强引用；没有新增配置或手动Root。GameData原三项软类字段名称、类型、属性标记保留，仍为唯一GE配置来源。
- StartInitialLoading检查游戏线程及重复/重入，先执行Super建立索引，再同步预载GameData与三项GE。GameData成功后，各GE独立尝试；整个尝试结束才发布可读结果。失败不重试、不阻断其余GE。
- 移除LoadPrimaryAssetsWithType及“运行调用保证AlwaysCook”的错误说明。Cook包含由配置/资产管理规则决定，本层没有修改或验证Cook配置。
- TryGet增加游戏线程运行检查，保留A的引擎实际实例、可空、无兜底契约。无效AssetManagerClassName仍可能在引擎初始化先Fatal。

Manager冻结接口（全部为C++接口，非UFUNCTION）：

| 接口 | 契约 |
| --- | --- |
| `GetGameData() const` | 返回预载数据或nullptr，不加载 |
| `GetSharedDamageGameplayEffect() const` / `GetSharedHealGameplayEffect() const` / `GetSharedSelfDestructGameplayEffect() const` | 返回对应强引用快照的TSubclassOf或空值，不解析覆盖/默认 |
| `GetGameDataLoadState() const` / `GetSharedDamageLoadState() const` / `GetSharedHealLoadState() const` / `GetSharedSelfDestructLoadState() const` | 返回逐项EGGYGOSharedAssetLoadState；不可读时统一NotReady |
| `HasCompletedSharedAssetPreload() const` | 表示整次尝试已发布，可能含失败，不等于所有资产可用 |

GameData的`Get()`和新增三个同名静态共享GE getter只判空并转发Manager，没有缓存/加载/解析策略。仅限游戏线程；错线程诊断并返回空/NotReady/false，且先于读取快照状态。启动加载期间同样不可读，防止回调消费部分快照。快照和失败结果随Manager生命周期保持，配置修改需重新启动，无运行刷新入口。

| 启动条件 | GameData结果 | 各GE结果 |
| --- | --- | --- |
| 整次预载未完成或错线程 | getter空 / NotReady | getter空 / NotReady |
| GameData路径为空 | NotConfigured | DependencyUnavailable（无法读取GE配置） |
| GameData加载或类型校验失败 | LoadFailed | DependencyUnavailable |
| GameData成功，某GE路径为空 | Ready | 该项NotConfigured，其他项继续尝试 |
| GameData成功，某GE加载或类型校验失败 | Ready | 该项LoadFailed，其他项继续尝试 |
| GameData成功，某GE成功 | Ready | 该项Ready并持有强引用 |

## 15-B实际验证与未验证边界（历史记录）

- 四文件启动前内容保存在只读内存基线；实现后逐行读回，并使用基线差异审查，没有使用Git。确认A的实际实例获取契约保留、原GE序列化字段和配置不变。本层所有写入仅用apply_patch且限上述六文件，GameplayTags和其他模块改动未触碰。
- `rg`复核所有现有消费者：通用LoadGameDataOfClass/Map无外部生产消费者；GameData.Get唯一既有外部使用为Health的自毁路径。新增GE getter尚未接消费者；现有Health软引用LoadSynchronous留待C，不声称全项目运行路径已无同步加载。
- 只读核对UE 5.8的`CoreUObject/Public/UObject/SoftObjectPtr.h`：TSoftObjectPtr.LoadSynchronous使用Cast校验数据类型；TSoftClassPtr.LoadSynchronous校验UGameplayEffect继承关系。`Templates/SubclassOf.h`内部为TObjectPtr<UClass>；结合UPROPERTY声明提供GC追踪。项目Build.cs已依赖GameplayAbilities，无新增构建依赖。
- 基于读回源码执行15项结构断言，全部true：父类先于预载；同步加载仅启动及其GE专用helper两处；三项GE独立调用；一次启动且末尾发布；三处线程运行检查；getter无加载；九项读取统一门禁；四项UPROPERTY强引用；五种状态齐全；GameData不可用时三项依赖状态；旧缓存/锁/类型批量加载移除；三GE字段不变；GameData四项纯转发；A无兜底契约；无项目GAS日志耦合。这是源码检查，不是编译或自动化测试。
- 架构核对：System只依赖引擎/GAS通用类型，不依赖具体GA/角色/Health内部状态；Manager独占预载结果与资源宿主，GameData只配置；无循环依赖、第二调度器、计时器或运行重试。资源由Manager的GC引用生命周期管理，不增加异步句柄或额外清理链。
- 没有执行UHT、C++编译/链接、UE、PIE、GC动态回归、自动化、Cook或资产回读。T1与配置/GC实测仍需后续授权，不引用前批验证证明本层通过。

15-B冻结交接：四份System源码与两份记录停止写入。统筹随后实际读回四源码，接受静态冻结并确认Source/GGYGO diff --check无错误（统筹执行，本会话没有运行Git）；不表示运行/GC/Cook通过。当前四份System源码只读，统筹仅重新开放C两份HealthComponent及本批两记录。GA适配继续等待12门禁。第15批整体、专项测试及文档闭环没有标记完成。

## 15-C自毁消费结果与静态验证（历史记录）

精确范围：`Source/GGYGO/Character/Components/GGYGOHealthComponent.h`、`Source/GGYGO/Character/Components/GGYGOHealthComponent.cpp`及本批两份记录；06已冻结交接。先登记职责、只读接口、验收与停止点再修改源码，全程组长直接执行，无子代理。

- cpp仅修改取值注释、空覆盖取值块与缺失诊断三处。`SelfDestructEffectOverride`非空优先，只有空值进入`UGGYGOGameData::GetSharedSelfDestructGameplayEffect()`；不再通过GameData软字段LoadSynchronous取GE。
- 无共享快照时，诊断明确Manager/预载未就绪、配置缺失或加载失败，并在MakeEffectContext之前返回；不施加自毁GE、不重试、不直接写Health。System启动诊断与Manager逐项状态仍是详细来源，本组件不维护第二份状态或缓存。
- h仅修正全局管理与覆盖说明，补充预载不可用时返回的契约；字段名、类型、UPROPERTY、所有函数声明均不变。

| 消费条件 | 取值与执行路径（静态审查） |
| --- | --- |
| 非空覆盖，共享就绪或不可用 | 使用覆盖，不访问共享getter |
| 空覆盖，共享Ready | 使用预载GE，进入原Spec/Tag/SetByCaller/Apply链 |
| 空覆盖，共享不可用 | 记录Error并返回，未创建Context/Spec、未施加GE |

读回源码与启动前内存基线比较，8项断言全部true：cpp恰为批准的三项文本替换；h去除注释后的代码逐字相同；覆盖优先且共享getter只在空分支；缺失在Context前返回；整份cpp无同步加载或GameData软字段读取；既有死亡与绑定门禁早于取值；从MakeEffectContext至函数结束的执行/Tag/SetByCaller代码逐字相同；无第二缓存或直接属性写入。检查不等于编译、单元测试或动态回归。

06边界：ApplyDeathStateToAbilitySystem的Owner/ASC/Avatar身份门禁、StartDeath/FinishDeath幂等及OnRep单调处理，与所有绑定/解绑和事件代码均逐字保持。交接基线的DamageSelfDestruct自身只有DeathState和ASC检查，没有Authority/Avatar检查；本轮仅获取值接缝授权，未新增权限或身份规则，也不声称自毁Authority/重入动态验证已通过。现有Spec/SetByCaller/动态Tag及ASC→GE→HealthSet结算链完整保留。

架构核对：调用已有System公开getter，不读取Manager私有状态；依赖方向维持Health→System、Health→ASC/HealthSet，System不反向依赖Health；资源宿主仍为Manager，Health只持临时选定类值，未新增GC资源、句柄、清理责任、循环依赖、计时器或执行链。15-B四源码SHA256与冻结结果全部一致，未改其他Character、GA/BaseGA/ASC/AbilitySet/HealthSet、标签、配置或资产。

未执行UHT、编译、UE、自动化、PIE、联机、Cook及资产回读，也未操作Git。后续应动态覆盖非空覆盖/空覆盖Ready/空覆盖不可用及既有死亡链；06旧门禁不替代本接缝验证。冻结交接：两份HealthComponent源码与本批两记录停止写入，不进入D/G/H或测试，GA接缝继续等待12。

## 第13次统筹门禁（历史，D实施前）

统筹于本次派发确认完整构建Succeeded、25.49秒；本会话只读回查`Saved/Logs/ModuleRepairBuildGate_20260930_13.log`第173–174行，与该结论一致。只读解析`Saved/AutomationReports/ModuleRepairGate_20260930_13/index.json`确认succeeded=47、succeededWithWarnings=0、failed=0、notRun=0，reportCreatedOn为2026.09.30-02.28.30；统筹确认Trace材质已绿且12释放共享默认接缝。

该门禁包含15-A/B/C增量的编译，但没有本批预载、GC、自毁消费或共享选择专项测试，不能标E12–E15全部通过，也不替代PIE/联机/Cook或上述权限边界。此前各阶段“未执行”指本会话当层执行情况；新门禁由统筹执行，不包含此后新增15-D代码。E/F仍需单独精确租约。

## 15-D冻结接口与静态验证（历史记录）

精确范围：`Source/GGYGO/System/GGYGOGameData.h`、`Source/GGYGO/System/GGYGOGameData.cpp`与本批两记录。生产写入前已登记预检，本会话直接执行，无子代理。

冻结公开C++接口（非UFUNCTION、bool无默认实参）：

```cpp
static TSubclassOf<UGameplayEffect> ResolveDamageGameplayEffect(
    TSubclassOf<UGameplayEffect> EffectOverride, bool bUseSharedWhenUnset);
static TSubclassOf<UGameplayEffect> ResolveHealGameplayEffect(
    TSubclassOf<UGameplayEffect> EffectOverride, bool bUseSharedWhenUnset);
```

调用方明确传bool，配置开关默认false兼容旧空覆盖语义；接口不替调用方启用共享。返回GE类值，不创建Spec或施加效果，不加载/重试/缓存。共享读取继续遵循B游戏线程、启动完成及可空契约；覆盖路径不访问Manager。缺失由调用方按业务处理，详细预载诊断仍归Manager，不新增第二份结果状态。

| 覆盖 | opt-in | 共享快照 | 返回值与读取路径（静态审查） |
| --- | --- | --- | --- |
| 非空 | false或true | 任意 | 原覆盖；不访问共享getter |
| 空 | false | 任意 | 空；不访问共享getter |
| 空 | true | 对应GE Ready | 对应共享getter结果 |
| 空 | true | 未就绪/配置缺失/加载失败/Manager不可用 | 空；无加载或重试 |

实际差异：cpp仅在原文件末尾追加两项解析函数，已有构造、Get及三个共享getter逐字保持；h新增两项声明/契约注释并修正顶部职责说明，三项软字段及UPROPERTY序列化声明逐字保持。Manager、Health、GA、ASC、AbilitySet、测试、配置和资产未改。

读回与启动前内存基线差异审查完成；8项结构断言均true：签名/返回一致且bool无默认实参；两函数完整覆盖优先/显式bool分支；只新增两函数；既有cpp完整保持；三项软字段与属性声明保持；h除新API/说明外保持；新增实现无加载/状态/执行或依赖；公开说明默认false与缺失边界。此为静态源码检查，不是专项测试。

Source/Plugins交叉引用仅命中两份GameData的新增声明/定义，没有命名冲突或消费者；E/F GA仍直接使用各自DamageEffect。架构审查：选择机制只有值输入、值输出、对应已有getter依赖，无角色业务、额外权威状态/资源/清理责任、循环依赖、调度器或第二执行链。无需通用选择框架或治疗GA。

没有执行D的UHT/编译、UE、自动化、PIE、Cook或Git。四授权文件及公开命名/参数/返回契约已冻结；停止于此，不进入E/F/G/H或测试。后续E/F可基于本接口申请租约，既有BaseGA BuildHitEffectPayload继续唯一构造命中载荷。

## 15-E玩家命中消费与静态验证（历史记录）

前置：统筹实际审查D两新增函数、header契约、默认实参及旧getter/软字段，确认diff check通过并接受静态冻结。本会话未执行Git；D/GameData、Manager及Health均只读。仅获得PlayerComboAbility.h/.cpp和本批两记录租约，先登记预检再直接实施，无子代理。

实际变化：

- h保留原DamageEffect名字、类型和属性声明；新增`UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "GGYGO|Combo") bool bUseSharedDamageEffectWhenUnset = false`及覆盖/缺失说明。未编辑任何GA资产，旧空覆盖不会因新增属性自动启用共享。
- cpp显式包含GameData与GameplayEffect头；仅在HandleMeleeHit已有门禁通过后调用`ResolveDamageGameplayEffect(DamageEffect, bUseSharedDamageEffectWhenUnset)`，用局部const TSubclassOf保存本次取值并传给原BuildHitEffectPayload，不建立激活期或跨帧缓存。
- 仅空覆盖+开关true+解析空时记录Warning；不提前返回、不取消GA、不选择其他GE。继续原Builder无GE载荷/Cue路径。默认false的旧演示空值不新增此诊断；非空覆盖不依赖共享可用性。

| DamageEffect | 开关 | 共享 | 静态路径 |
| --- | --- | --- | --- |
| 非空 | false或true | 任意 | 使用原覆盖，由原Builder构造/施加；保留Cue |
| 空 | false（默认） | 任意 | 空GE、无伤害Spec，保留原Builder/Cue，不读共享 |
| 空 | true | Ready | 本次读取共享类，走原Builder/伤害/削韧/Cue链 |
| 空 | true | 不可用 | Warning，仍空GE走原Builder/Cue，无替代GE或直接属性写入 |

Cue仍遵守既有TargetASC/SourceAvatar、Builder上下文成功及HitCueTag有效门禁；“保留Cue”不意味着忽略这些既有条件。只读BaseGA BuildHitEffectPayload确认空GE仍构造EffectContext和CueParameters，只有非空类才MakeOutgoingSpec；此Builder没有修改或复制。

实际差异与基线读回审查完成，10项结构断言均true：cpp恰为两个include及命中选择/诊断/实参变更；h仅新增配置及注释；新字段蓝图可配置默认false；原DamageEffect声明保持；Resolve只命中一次且显式传原配置；结果局部const无成员缓存；缺失诊断不中断Builder；Spec伤害/Poise/Cue分支逐字保持；End清理逐字保持；新增取值块无加载/状态/第二执行机制。连段配置校验、激活、窗口、输入、Montage、预测、代次/身份/重入及End之前/之后的所有非目标代码保持基线。

交叉引用确认玩家唯一消费点改用D接口，新增开关只在声明及该命中取值/诊断使用；Boss仍未适配。架构核对：GA→System公开选择接口，无System→GA反向依赖；Manager仍唯一资源宿主，GA只增加自己的配置开关及栈帧类值，不新增缓存、计时器、权威状态、清理责任或结算链。原12/04 Builder、ASC、Task、Hero、Boss/AbilitySet及资产均未修改。

本层没有执行UHT/编译、UE、自动化、PIE、联机、Cook或Git；47项旧门禁不包含新D/E增量，也不能证明选择矩阵或新属性序列化通过。后续T3需动态覆盖上表及旧空覆盖Cue兼容，构建/UE由统筹安排。冻结交接：两生产文件与两记录全部停止写入，不进入F/G或测试。

## 第14次统筹门禁（F实施前）

统筹确认完整构建Succeeded、14.31秒，常规47/47、测试0 warning/error及UE exit0。本会话只读回查`Saved/Logs/ModuleRepairBuildGate_20260930_14.log`第145–146行，以及`Saved/AutomationReports/ModuleRepairGate_20260930_14/index.json`：succeeded=47、succeededWithWarnings=0、failed=0、notRun=0，reportCreatedOn=2026.09.30-02.54.52，与统筹报告一致。本会话未执行构建或UE。

该门禁实际编译A–E（含D/E），但共享预载/GC/覆盖选择专项用例尚未实施；47常规回归不关闭这些行为验证，也不证明新F接缝。D/E此前“未构建”属当层历史记录，本门禁补充后续构建事实，不将F或E12–E15整体标通过。

## 15-F Boss兼容消费与静态验证

精确范围：`Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.h`、`Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp`及本批两记录。写源码前登记预检，直接实施、无子代理；D/Manager、Health、PlayerCombo、BaseGA/ASC/Task和其它Boss文件均只读。

- h保留原DamageEffect名字、类型及属性；新增`UPROPERTY(EditDefaultsOnly, BlueprintReadOnly, Category = "GGYGO|Boss Melee") bool bUseSharedDamageEffectWhenUnset = false`和契约注释。未改任何蓝图资产，新开关不会自动启用共享。
- ValidateMeleeConfiguration局部解析`ResolveDamageGameplayEffect(DamageEffect, bUseSharedDamageEffectWhenUnset)`，原!DamageEffect检查改为!ResolvedDamageEffect，更新同一错误说明。原Montage/Socket/有限值/半径/播放率/ActionMotion校验全部保持；IsDataValid及ActivateAbility原调用仍复用此函数。
- HandleMeleeHit在原活动/清理/混出/Trace/Authority/目标ASC/Avatar门禁后用完全相同D参数解析局部const类值；空则Error并返回，不调用Builder或执行无GE Cue路径。非空才传入原BuildHitEffectPayload，保持Spec/SetByCaller/施加/Cue链。

| DamageEffect | opt-in | 共享 | 静态校验与命中路径 |
| --- | --- | --- | --- |
| 非空 | false或true | 任意 | 原覆盖优先；GE项有效，满足其它校验后正常原链 |
| 空 | false（默认） | 任意 | 校验失败；意外命中回调也诊断返回 |
| 空 | true | Ready | GE项有效，满足其它校验后共享非空类走原链 |
| 空 | true | 未就绪/缺失/加载失败/Manager不可用 | 校验失败；命中诊断返回，无其它GE回退或无伤害成功 |

校验与命中使用同一冻结选择规则，不建立跨帧类缓存。表中GE项有效不绕过14a其它配置、活动或权限门禁；原非空类创建Spec失败后的Cue行为未改，新增缺失返回只处理解析为空的契约。

实际读回与启动前内存基线差异审查完成，11项源码断言全部true：cpp恰为两include和两消费接缝；h仅增加配置及注释；新开关蓝图可配置默认false；原DamageEffect声明保持；两处同一D参数；校验要求解析非空并保留其它规则；命中缺失在Builder前返回；局部const无成员缓存；Activate/End/事件/动作位移/播放率/预测段逐字保持；原Spec伤害/Poise/Cue尾部逐字保持；新增块无加载/计时/直接属性执行。这是静态检查，不是选择矩阵运行测试。

交叉引用确认新增开关只用于声明及两处选择参数；不写D配置或GameData软字段。架构核对：Boss GA→System公开无状态选择机制，无System反向业务依赖；Manager独占共享GC资源，CMC/Animation/Combat/BossAI状态所有权不变；未新增缓存、清理责任、执行器、计时器或循环依赖。未修改选招、原预测策略、ActionMotion句柄或清理与Montage任务生命周期。

未执行F的UHT/构建、UE、自动化、PIE、联机、Cook或Git。T3仍需动态覆盖校验/命中一致矩阵及旧空值拒绝边界；本次不进入G/H或测试。两生产文件与两记录已冻结交回。

## 15-G只读预检证据与方案边界（历史；随后仅G1获授权）

统筹已实际审查F字段/接缝/调用块与静态diff，接受冻结，记录H/CPP哈希前缀4794A1C4/E3B5AE93；未提供新构建结论。当前只写本批两记录，没有修改AbilitySet或其它生产文件。原子候选G1/G2精确范围、非目标、断言及停止点见AtomicSteps。

### 当前实现与问题

- AbilitySet.h/.cpp没有IsDataValid覆盖或属性类冲突谓词。GiveToAbilitySystem只先check ASC及Authority，再对每项检查IsValid(TSubclassOf)，直接NewObject(GetOwner, Class)→AddAttributeSetSubobject→记录NewSet；没有Outer有效性、抽象类或SpawnedAttributes冲突门禁。
- TakeFromAbilitySystem按本次GrantedAttributeSets指针移除；必须保持这份所有权语义，不把既有基础实例或其它资产实例放入该数组。能力与GE阶段在属性阶段之后独立运行，原单项错误continue支持部分成功，不做整个资产事务回滚。
- Combatants/GGYGOCombatantState.cpp第28–33行创建ASC、HealthSet和CombatSet默认子对象；两基础Set早于Avatar并由ASC初始化发现。Slots/BossState调用AbilitySet授予，重复基础属性确有运行冲突来源。项目UGGYGOAttributeSet只提供便利接口，没有属性字段；HealthSet与CombatSet各声明不同GAS字段，应共存。

### 本机UE5.8源码证据（只读）

根：`F:/UE_5.8/Engine/Plugins/Runtime/GameplayAbilities/Source/GameplayAbilities/`。

| 源码 / 已核验位置 | 结论 |
| --- | --- |
| `Private/AbilitySystemComponent.cpp:132–141` | GetAttributeSubobject逐项找首个Set->IsA(AttributeClass)，不是精确类唯一或继承歧义检测 |
| `Public/AttributeSet.h:99–103`；`Private/AbilitySystemComponent.cpp:171–183` | FGameplayAttribute的查找类来自字段声明Owner；读取经该类找实例，继承字段不会自动改成最末派生类 |
| `Private/GameplayEffect.cpp:3993` | 写基础属性同样先按Attribute声明类找Set，因此歧义影响读写权威存储 |
| `Private/AttributeSet.cpp:412–420`；`Public/AttributeSet.h:190–191` | 已有公开GetAttributesFromSetClass，按引擎支持类型枚举FGameplayAttribute，无需项目反射框架 |
| `CoreUObject/Public/UObject/UnrealType.h:7143,7210`（引擎Runtime根） | TFieldIterator默认IncludeSuper，故上述枚举包含继承字段 |
| `Private/AttributeSet.cpp:223–242,531–534` | 支持FGameplayAttributeData（含派生结构）及浮点属性；属性相等按字段引用身份，不按名称。应复用引擎规则，不用全部FNumericProperty或自行构造非法属性（后者会ensure） |
| `Private/AbilitySystemComponent.cpp:3200–3215`；`Public/AbilitySystemComponent.h:164–167` | AddSpawnedAttribute仅验证对象并按指针去重；同类不同对象均能加入。AddAttributeSetSubobject直接返回输入，不能把返回值当登记成功证据 |
| `Private/AttributeSet.cpp:476–483` | GetOwningActor将Outer CastChecked为AActor，属性实例Outer须有效Actor |
| `Private/AbilitySystemComponent.cpp:2115–2118` | IsOwnerActorAuthoritative只读bCachedIsNetSimulated，不能代替有效Owner/Outer检查 |

### 建议共享冲突谓词（待批准）

合法类先经单独有效性/可实例化检查。文件内helper对A/B按以下次序判定：同类或任一继承另一→冲突；否则分别用GetAttributesFromSetClass取得当前继承属性列表，用FGameplayAttribute相等判定任一字段交集→冲突；其它→不冲突。仅临时数组，不创建对象、读实例值、按名映射或保存缓存。编辑IsDataValid和运行授予均用此helper及同一类有效性规则。

| 类关系 | 建议结果 | 理由/取舍 |
| --- | --- | --- |
| 同类两实例 | 冲突 | 按类查找首匹配，重复存储 |
| 父与子、祖先与后代（任意顺序） | 冲突 | 父类GetSet/属性寻址可命中两实例；即使空父类也保持此明确继承准入约束 |
| 两Sibling继承同一带Health等属性基类 | 冲突 | 同一声明字段在两对象中有两份存储，属性交集可识别，不能只比较IsChildOf双方 |
| Sibling共享基类仅含无GAS属性的便利接口，各有独立属性 | 允许 | 没有属性交集，不因公共祖先误拒绝；调用方应查具体类，空基类GetSet仍是引擎首匹配，不新增空基类唯一性承诺 |
| 项目HealthSet与CombatSet | 允许 | 共同UGGYGOAttributeSet无属性，两列表无同一字段 |
| 不同类各自声明同名属性 | 无其它关系/交集则允许 | 属性声明Owner/字段身份不同，名字相同不足以认定同一存储 |
| 共享祖先声明legacy float/double或FGameplayAttributeData派生结构 | 冲突 | 使用引擎支持枚举，不漏legacy属性，也不把非浮点int/普通结构误当属性 |
| 仅共享UAttributeSet/UObject根 | 允许 | 根的存在不是冲突条件；本机UAttributeSet没有GAS支持属性字段 |

Sibling无需新增复杂规则：引擎已有枚举/相等API覆盖继承字段。若产品希望允许共用Health声明的多个Sibling，现有GAS按Owner类首匹配不足以保证唯一权威，需单独寻址架构方案，不在本轮静默放行。

### 编辑与运行候选接线

G1：h添加WITH_EDITOR IsDataValid，cpp添加文件内helper与编辑实现。调用Super；逐项报告空/无效/抽象属性类，合法项与前项按同谓词成对比较，包含索引/类/关系或共享字段诊断；有问题Invalid，无问题且Super不Invalid返回Valid。不在编辑器授予对象，不装载世界或替换ASC；单资产校验不能证明跨资产/宿主安全。

G2：保留Authority及原三阶段顺序。属性循环逐项先验证类、当时Actor Outer有效且非销毁中，再检查实时GetSpawnedAttributes的类关系/属性交集，已有前序新授予及跨资产/宿主都纳入。冲突只Error/continue，不创建、借用或记回收句柄；不GetOrCreate、不移除既有项。NewObject后重验NewSet/Outer/Owner身份及实时冲突，避免构造期间失效；挂接后确认新指针确在ASC列表，再仅记录本次NewSet。空列表项跳过；非空既有实例的类仍参与冲突，不自行清理失效项或抢占存储。合法不相关项继续，能力/GE阶段保持原处理，不借本轮改成全资产回滚或依赖过滤。

Outer失效导致属性项不能创建，不据此声称能力/GE阶段或整体宿主生命周期已验证；这些原阶段与宿主归属不在G2扩改。未挂接且无其它引用的新失败对象交GC，不手动回收其它来源资源。

### 验证与停止边界

本轮只执行本机源码/调用点/Obsidian现状只读核对，没有修改任何生产、测试、资产、Config或Obsidian，没有执行构建、UE、Git或代理。上述矩阵是源码推导的拟采用规则，尚未实现/编译/动态测试。后续T2至少覆盖同资产重复、跨资产、基础Set已有、双向父子、带属性Sibling、空基类Sibling合法、legacy浮点、不相关Set、无效Outer/类、客户端及回收所有权；必须验证拒绝项不进入Handles、合法新增能移除、既有基础项保持。

两份预检记录冻结交回，等待统筹分别批准G1/G2；不因完成预检自动获得源码写入权。

## 15-G1共用谓词与编辑校验（静态冻结）

统筹接受G只读预检后，仅开放`Source/GGYGO/AbilitySystem/GGYGOAbilitySet.h`、`Source/GGYGO/AbilitySystem/GGYGOAbilitySet.cpp`及本批两记录。写源码前登记本步预检，直接执行无代理；G2运行准入未授权。

cpp文件内冻结的共用接口：

```cpp
bool IsValidAttributeSetClass(UClass* SetClass);
bool IsGrantableAttributeSetClass(UClass* SetClass);
bool HaveAttributeSetClassConflict(UClass* FirstClass, UClass* SecondClass, FString& OutReason);
```

- 类型门禁IsValidAttributeSetClass只要求IsValid且继承UAttributeSet，abstract类仍能参与存储冲突；新授予资格IsGrantableAttributeSetClass在类型门禁之上拒绝CLASS_Abstract。冲突helper先清OutReason，再只按类型门禁早退；无效或非AttributeSet类型返回false交调用方单独诊断，不借新建资格忽略已有存储。
- 有效类同类→true；双向父子/祖先后代→true；否则用公开GetAttributesFromSetClass取得两组继承属性，TArray.Contains调用FGameplayAttribute实际字段相等，有交集→true并输出声明类/字段原因，无交集→false。属性名只用于诊断，不用于判重。没有公共祖先拒绝、手写反射枚举、长期缓存或实例值读取。
- helper处于匿名namespace、普通非编辑构建也保留定义，标记maybe_unused应对G1非编辑版本尚无调用；后续G2可在同cpp复用，不新增模块间API。
- h仅WITH_EDITOR前置声明Context及覆盖IsDataValid；cpp仅编辑版本包含Misc/DataValidation并定义校验。校验先Super，再遍历GrantedAttributes，单项无效/空/抽象报索引与类，合法项与所有前项按共用谓词比较，每个冲突对均报双索引/类/原因，不因首错漏报其余。存在问题或Super Invalid则Invalid，否则Valid。没有扩展GA/GE校验。

| 编辑配置 | 实际源码判定（静态审查，未运行） |
| --- | --- |
| 空属性数组，Super非Invalid | Valid |
| 任意空/无效/抽象类 | Invalid并定位该索引 |
| 同类、双向父子/祖先后代 | Invalid并定位冲突对 |
| 共享同一声明属性的Sibling | Invalid并报告共享字段，不漏继承Health存储 |
| HealthSet/CombatSet或共享空便利基类但属性独立 | 无冲突；无其它问题时Valid |
| 不同类独立声明同名属性 | 无其它关系/字段交集则无冲突 |
| 共享legacy浮点或FGameplayAttributeData派生结构字段 | 随引擎支持枚举识别冲突 |
| 任意配置，Super返回Invalid | 仍Invalid |

实际差异读回并与启动前内存基线比较，12项断言全部true：删除新增块后原cpp/h逐字保持；Give完整保持；GrantedHandles/Take/构造完整保持；类门禁有效/派生/抽象；同类/双向父子优先；枚举/字段相等复用引擎；仅临时数组无公共祖先拒绝；声明/实现/include编辑守卫；全部项与前项成对并诊断；Super Invalid保持且仅属性数组；新增块无实例化/加载/授予/回收。这是源码检查，不是编译或专项用例。

只读再次核对本机UE5.8 AttributeSet.h公开GetAttributesFromSetClass签名、GetAttributeSetClass声明Owner及AttributeSet.cpp operator==字段引用相等；G预检已核对枚举默认IncludeSuper及IsSupportedProperty，不复制支持类型分类。新增依赖仅编辑DataValidation标准头，项目原有GAS依赖不变。

架构/清理核对：编辑校验只读数据与类元信息，输出Context诊断，不持有权威状态、资源句柄或生命周期；不依赖宿主/具体Health类/Boss业务，不新增循环依赖、调度器、执行链或清理义务。所有序列化属性及原授予/客户端Authority/部分成功/回收代码逐字保持；当前运行路径仍可能重复创建属性实例，不能把本次编辑校验当作G2运行拒绝或跨资产安全已完成。

未执行UHT/构建、UE、自动化、编辑器真实数据验证、PIE、Cook或Git；前47项常规门禁不包含此后新增G1。四授权文件与helper名字/参数/返回契约冻结，不进入G2/H/T。后续G2先读取本实现，T2分别验证编辑规则和运行准入/回收所有权，均需独立租约。

### G1类型与新建资格更正

统筹复核指出初版HaveAttributeSetClassConflict使用IsGrantableAttributeSetClass会把abstract类型排除，不能保证G2对已有非空存储进行完整类比较。按同一G1四文件租约更正：新增IsValidAttributeSetClass，IsGrantable复用它并单独排除abstract；冲突helper仅复用IsValidAttributeSetClass。未以“正常新建少见”作为忽略已有类的依据。

| 输入 | 类型资格 | 新建资格 | 更正后冲突判断 |
| --- | --- | --- | --- |
| 有效abstract AttributeSet类型 | true | false | 仍参与同类、双向父子与实际字段交集比较 |
| 有效非abstract AttributeSet类型 | true | true | 同一比较规则 |
| 空/失效类或非AttributeSet类型 | false | false | 早退，调用方单独诊断 |

编辑当前项仍通过IsGrantable单独拒绝abstract，未改IsDataValid代码；如果前项abstract且当前项合法，共用谓词可补报关系冲突，但该资产已因abstract配置为Invalid。Give/Handles/Take均未变化，G2仍未接入。

更正后源码与G1初次冻结基线比较，6项补充断言全true：cpp只拆分类型门禁并更正冲突早退；h保持；类型门禁不含abstract；新授予资格仍拒绝abstract；冲突helper不再调用新授予门禁或过滤abstract；全部编辑/运行授予/回收代码逐字保持。初次12项检查是更正前结构记录，本次补齐类型/新建语义分离，不当作动态行为证明。无构建、UE、Git、测试或其它写入；四文件再次冻结交回。

## 第15次统筹门禁补充（F/G1编译事实）

统筹实际diff审查接受G1最终abstract类型比较更正及F。只读核对`Saved/Logs/ModuleRepairBuildGate_20260930_15.log`第104、173–174行：完整构建Succeeded，6 actions、22.10秒，覆盖F/G1及其它冻结工作线。`Saved/AutomationReports/ModuleRepairGate_20260930_15/index.json`：reportCreatedOn=2026.09.30-03.50.28 UTC，47 succeeded、1 failed、0 succeededWithWarnings/notRun/inProcess。原47项均Success；唯一新增失败为`GGYGO.Input.Fixture.LocalSessionReady`，含PlayerInput来源警告与Subsystem返回不等，不能把总报告写成全通过。本会话没有执行构建或UE。

此门禁只补充F/G1实际编译事实；常规47项未覆盖本批共享预载/GC/覆盖选择/属性冲突与回收专项。Input前置失败不作为System行为证明。G2是在该门禁之后实施，未被此次构建覆盖。

## 15-G2运行属性准入（静态冻结）

统筹仅开放`Source/GGYGO/AbilitySystem/GGYGOAbilitySet.cpp`及本批AtomicSteps/Validation，共三文件。写源码前已登记原子预检；单cpp直接实施，无代理。header及G1三个helper、编辑IsDataValid保持冻结；其它源码、测试、资产、Obsidian及H/T/M未开放。

### 实际接线与所有权

- 新增标准`GameFramework/Actor.h` include，生产差异仅属性授予循环。原函数入口check/缓存Authority早退保持；每项新配置再用G1 IsGrantableAttributeSetClass拒绝空、失效、非AttributeSet或abstract类，Error定位资产/索引/类并continue。
- 本项取得当时ASC GetOwner作为`GrantOwner`。局部只读IsGrantContextValid同时要求ASC IsValid、非IsBeingDestroyed、IsOwnerActorAuthoritative，Actor IsValid、非IsActorBeingDestroyed、HasAuthority且ASC GetOwner仍等于原Actor。NewObject前检查；构造后再检查同一契约、NewSet有效及GetOuter等于原Actor，不接受构造期间宿主换手/失效。
- 局部HasStorageConflict每次调用直接遍历当前GetSpawnedAttributes，不缓存数组/类结论。所有非空ExistingSet用其GetClass与新类调用冻结HaveAttributeSetClassConflict；不对ExistingSet使用IsValid/IsGrantable或abstract过滤，不清理列表。仅跳过空指针。命中首个同类/双向继承/实际声明字段交集冲突即定位已有实例/类/原因并continue。
- 冲突检查在NewObject之前和构造之后、Add之前分别调用，故构造中新加入的存储也纳入第二次读取。前序本轮合法新增、前次/其它AbilitySet及宿主基础实例均来自同一ASC权威列表。Health/Combat等无关系且字段独立的类可共存，继承同一属性声明的Sibling被拒绝；既有abstract类型仍参与比较。
- NewObject只使用原Actor Outer与已验新类；构造后失败或新冲突时不挂接、不记录，新未登记对象由GC处理。AddAttributeSetSubobject仅执行一次，不借其返回值断言成功；随后重新读取列表并Contains(NewSet)，未实际登记则Error/continue，登记后且OutGrantedHandles非空才AddAttributeSet(NewSet)。既有指针绝不写入本次句柄。
- 共六个属性失败分支均continue；合法后项以及原第二阶段GA、第三阶段GE仍独立继续。没有全资产事务、GA/GE依赖过滤、借用/GetOrCreate/引用计数/Root、既有对象移除或新增宿主权威状态。GrantedHandles及Take逐字保持，回收仍按本次记录的新对象指针执行。

### 实际静态边界审查

| 边界 | 本次源码结论（未运行） |
| --- | --- |
| 空/无效/abstract新类 | NewObject前跳过，不挂接、不记句柄 |
| ASC失效/销毁中/非权威，Actor空/失效/销毁中/非权威 | 本项构造前跳过；构造后变化则不Add |
| 构造期间ASC Owner变为其它Actor或NewSet Outer不是原Actor | 原Actor身份复核失败，不Add、不记句柄 |
| 同资产重复、跨资产重复、已有基础Set | 实时列表同类冲突，拒绝本项，既有对象保留 |
| 父子任意顺序、共享继承字段Sibling/legacy浮点 | 复用G1双向继承/引擎字段交集拒绝，不另建判据 |
| abstract标记的有效已有存储类 | 非空实例仍参与G1类型比较，不能因新建资格被忽略 |
| 独立Health/Combat、空便利基类且字段独立Sibling | G1无冲突时继续新建；公共祖先本身不拒绝 |
| 构造中新出现冲突项 | 第二次实时列表读取拒绝本次NewSet挂接 |
| 空列表项、非空标记失效的既有实例 | 空跳过；非空仍取类比较，不擅自清理/抢占 |
| Add返回NewSet但列表不含它 | 不把返回值当成功，不记录本次句柄 |
| OutGrantedHandles为空 | 合法新实例仍按旧语义挂接，不新增回收容器 |
| 属性项失败/部分合法 | 仅continue该项；GA/GE原处理与部分成功语义保持 |
| 客户端 | 原缓存Authority早退保持；属性新准入另要求Actor实际HasAuthority |

以G1最终冻结时保存的实际文件内容为基线读回比较，12项静态断言全部true：cpp仅Actor include及属性循环变化；header不变；helper/编辑/Handles/Take/构造/入口不变；新类门禁在New前；ASC及原Actor有效/销毁/双权限/身份条件完整；同一上下文复核分别在New前后；所有非空既有类参与且无abstract资格过滤；两次实时冲突检查分列New前及New后Add前；NewSet及Outer验证；实际Contains在Add后、Handles前且唯一只记录NewSet；六失败continue且无循环提前return；新增循环无借用/移除/Root/加载/静态缓存/事务。实际逐段差异与整段比对确认GA/GE尾部逐字不动。这是静态源码检查，未执行测试。

本机UE5.8只读API复核：ActorComponent.h:520公开IsBeingDestroyed，Actor.h:1938/2152提供HasAuthority/IsActorBeingDestroyed；ASC.h:164–167的AddAttributeSetSubobject仍返回输入，cpp:3200–3217的AddSpawnedAttribute做对象有效性/指针去重、复制子对象登记、列表添加与dirty，cpp:3265–3268的GetSpawnedAttributes只读当前列表。Add前完成构造后的权限/Outer/实时冲突检查，Add后验证实际指针登记；本步不把挂接返回值或此前数组当证据。

架构核对：AbilitySet只消费ASC公开列表及登记入口，ASC唯一持有存储列表，Actor唯一提供Outer生命周期；本地lambda与局部元信息不成为第二份权威状态。G1同一谓词供编辑及运行使用，未重复反射/属性规则，未依赖具体角色或建立循环依赖。拒绝项不转移既有存储的回收责任；未登记新对象无新增强引用，保持GC清理。原GA/GE阶段与整个宿主销毁/生命周期未扩改；属性拒绝不表示整个AbilitySet无副作用或全有全无。

未执行G2编译/UHT、UE、自动化、PIE、联机、Cook或Git；第15次构建不含本次G2。T2仍需分别验证编辑配置及运行同/跨资产、基础Set、父子/Sibling/legacy、合法项、无效宿主/构造变化、客户端、部分成功与回收所有权。三授权文件已完成本层实现、实际diff/API/边界审查并冻结交回，不进入H/T/M。

## 第16次统筹门禁补充（G2编译事实）

G2实际cpp diff及原生AddSpawnedAttribute实现已由统筹审查接受，所有生产源码保持冻结。本会话只读核对`Saved/Logs/ModuleRepairBuildGate_20260930_16.log`第81、146–147行：完整构建Succeeded，6 actions、20.22秒。`Saved/AutomationReports/ModuleRepairGate_20260930_16/index.json`：reportCreatedOn=2026.09.30-04.22.01 UTC，48 succeeded、0 succeededWithWarnings/failed/notRun/inProcess，总0.42834693193435669秒；统筹报告0 warning/error、UE exit0。本会话没有执行构建或UE。

该门禁覆盖G2编译及原有48项常规回归，不含尚未创建的属性专项。G2前节“未构建”是当层冻结时历史事实，由此节补充后续编译结果；不将同/跨资产、继承属性、回收、Outer变化或客户端行为标为专项通过。本次T2-0头文件在Gate16之后新建，未进入该门禁。

## 15-T2-0共享测试类型（历史静态冻结，第17次后续见末节）

统筹接受T2最小拆分，只开放新`Source/GGYGO/AbilitySystem/Tests/GGYGOAbilitySetAttributeSafetyTestTypes.h`及本批AtomicSteps/Validation，共三文件。写头前已登记极简预检；单头直接定义，无代理。没有创建测试cpp或自动化注册，生产头/cpp均只读。

### 冻结类型及API

| 类型（均前缀GGYGOAbilitySetAttributeSafety） | 输入/输出与边界 |
| --- | --- |
| `UGGYGOAbilitySetAttributeSafetyTestAsset` | 派生真实AbilitySet；`SetAttributeClassesForTest(const TArray<TSubclassOf<UAttributeSet>>& SetClasses)`只重置/填充本对象继承的GrantedAttributes，不写GA/GE配置，不覆盖IsDataValid/Give/Take |
| `FGGYGOAbilitySetAttributeSafetyHandlesView` | 普通C++派生真实GrantedHandles；`GetAttributeSetCountForTest() const`和`const UAttributeSet* GetAttributeSetForTest(int32 Index) const`只读取继承记录，索引无效返回null；无成员状态、可写数组引用或新增所有权容器 |
| `UGGYGOAbilitySetAttributeSafetySharedSet` | 非抽象UAttributeSet，唯一声明UPROPERTY FGameplayAttributeData SharedValue；可作为同类重复及父子矩阵父类 |
| `UGGYGOAbilitySetAttributeSafetySharedSiblingA/B` | 两个具体子类，无新字段；真实UClass继承同一SharedValue，供共享声明字段siblings冲突 |
| `UGGYGOAbilitySetAttributeSafetyEmptyBase` | 具体共同祖先，无属性字段 |
| `UGGYGOAbilitySetAttributeSafetyIndependentA/B` | 派生EmptyBase，各自UPROPERTY声明IndependentAValue/IndependentBValue；字段声明Owner不同，供空共同祖先独立存储合法矩阵 |
| `UGGYGOAbilitySetAttributeSafetyAbstractSet` | UCLASS(Abstract, Transient)，仅供类配置诊断，后续夹具不能NewObject此类；null配置由空TSubclassOf表达 |
| `AGGYGOAbilitySetAttributeSafetyTestHost` | 具体Transient CombatantState子类，inline构造只Super(ObjectInitializer)；默认ASC/HealthSet/CombatSet及初始化/清理由生产父类提供，不替换、不补第二套宿主状态 |

头仅include生产AbilitySet及CombatantState，generated.h为最后include；9个UCLASS均配GENERATED_BODY，3个矩阵字段使用现成FGameplayAttributeData反射结构。反射类型不置于WITH_DEV_AUTOMATION_TESTS/WITH_EDITOR条件中，遵循项目现有测试类型头模式。所有手写构造及方法在头内完整定义，空子类构造由UHT正常生成，不预留需要测试cpp链接的函数；普通Handles视图不添加USTRUCT/UPROPERTY反射入口。测试类仅在本模块使用，未修改Build.cs或生产API。

实际读回静态审查12项断言全true：生产AbilitySet与CombatantState四文件逐字保持；测试cpp仍不存在；generated.h最后include；9个UCLASS/GENERATED_BODY配对；无反射条件包装；配置仅GrantedAttributes；Handles视图只读/无状态；Shared两siblings继承同一字段；EmptyBase无字段且Independent两siblings各有独立声明；abstract标记与具体宿主继承正确；所有手写函数inline自足；无授予/回收调用、构造钩子、Rename、SwapRoles、World/新对象创建、注册、静态缓存或其它状态。全项目类名检索无重名；已核对生产protected数组可由本类派生访问、TObjectPtr.Get只读返回const指针，以及本机UE5.8 AttributeSet.h的FGameplayAttributeData为带默认零初始化的反射结构。

这是API/UHT规则静态审查，没有实际运行UHT或编译，不能标记新头已生成/链接成功，也不证明任何配置或运行矩阵行为。本层不创建测试世界、计时器、执行器或资源句柄，类型没有独立清理义务；后续T2b的世界和授予资源需在该步单独建立与清理。矩阵字段仅提供类元信息/存储形状，没有复制生产冲突规则或读取其它模块内部状态，无生产职责/依赖方向变化。

三授权文件静态冻结交回；T2a将只读本头验证IsDataValid，T2b另行验证准入及本次记录，T2c生命周期/角色夹具分步另授。构造后Rename钩子、SwapRoles及真实client前置均未加入；本地角色夹具不能标为客户端通过。未执行UE/UHT/构建/测试/Git/代理，未写Obsidian/资产或其它源码，不进入T2a/b/c。

## 15-T2a编辑属性配置专项（历史静态冻结，当时未运行，第17次后续见末节）

统筹实际读回T2-0共享头/生产保护边界并核对SHA256=`8C3FF93CF84D8A11E92A3AEEDA0DC69D93D6C5158B0A3F41C58B87806C10FC07`后接受类型冻结；头尚未实际UHT。随后仅开放新`Source/GGYGO/AbilitySystem/Tests/GGYGOAbilitySetAttributeSafetyTest.cpp`及本批AtomicSteps/Validation，共三文件。写测试前登记预检；共享头和G1/G2生产严格只读，未增加类型或生产可见性。

注册名：`GGYGO.AbilitySystem.AbilitySet.AttributeConfigValidation`；类`FGGYGOAbilitySetAttributeConfigValidationTest`，EditorContext/EngineFilter，测试主体及其依赖在`WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR`门禁内。cpp正常include只读共享头及`UE_INLINE_GENERATED_CPP_BY_NAME(GGYGOAbilitySetAttributeSafetyTestTypes)`，配合后续UHT生成，不以条件宏隐藏反射类型。

### 真实API与严格断言

每个案例只NewObject瞬态TestAsset并以局部TStrongObjectPtr保活，调用既有配置入口；建立独立公共FDataValidationContext并实际执行Asset->IsDataValid。通过GetNumErrors/GetNumWarnings及SplitIssues取得真实计数与错误/警告；断言结果枚举、计数一致、零非预期警告，并用TestEqual比较每条完整诊断文本。期望文本包含具体配置索引、实际类名及关系/字段原因，错误数量严格固定，不以字符串非空/Contains/通配ExpectedError代替。期望错误只作为比对数据，不发日志、不调用AddExpectedError抑制失败。

| 案例 | 配置 / 预期结果 | 完整错误的关键索引与原因 |
| --- | --- | --- |
| Empty | 空数组，Valid、0错误 | 无 |
| SingleConcrete | SharedSet单项，Valid、0错误 | 无 |
| NullAtIndex1 | IndependentA、null、IndependentB，Invalid、1错误 | GrantedAttributes[1]，None，空/无效/抽象诊断 |
| AbstractAtIndex2 | IndependentA、IndependentB、AbstractSet，Invalid、1错误 | GrantedAttributes[2]，实际AbstractSet类名，同一非法类诊断 |
| TwoInvalidIndices | IndependentA、null、IndependentB、AbstractSet，Invalid、2错误 | 顺序为[1] null与[3] abstract，不能首错后漏报 |
| DuplicateAtIndices1And2 | IndependentA、SharedSet、SharedSet，Invalid、1错误 | [1]与[2]、同类重复 |
| ParentThenChild | SharedSet、SharedSiblingA，Invalid、1错误 | [0]父与[1]子，继承查找不唯一 |
| ChildThenParent | SharedSiblingA、SharedSet，Invalid、1错误 | [0]子与[1]父，双向同一继承规则 |
| SharedSiblingIndices0And2 | SharedSiblingA、IndependentA、SharedSiblingB，Invalid、1错误 | [0]与[2]，共享声明字段SharedSet.SharedValue，不把中间独立项当冲突 |
| EmptyAncestorIndependentSiblings | IndependentA、IndependentB，Valid、0错误 | 共同EmptyBase本身不拒绝独立字段 |
| ProductionHealthAndCombat | 真实HealthSet、CombatSet类配置，Valid、0错误 | 公共便利基类无存储，不构造这两个实例 |

以上为已编码期望，不是实际运行结果。11例全部使用`bPassed &= ValidateCase`执行并累计，各例内部断言也累计，不以第一处失败短路余下配置。缺失错误由数量不等严格失败，额外错误同样失败；现有生产若真实不满足期望，统筹运行会保留失败，未改生产或降级期望。测试没有自行枚举字段/调用冲突helper或复制生产判据，只输入冻结矩阵并观察公开校验行为。

### 实际差异、静态审查与边界

完整新增cpp已逐段读回；共享头与AbilitySet.h/.cpp对实施前实际基线逐字保持，共享头SHA256仍为上述冻结值。12项静态断言全true：只读三文件不变；正常inline generated cpp接线；唯一Editor注册及主体守卫；每例瞬态资产与独立Context；实际IsDataValid/公共计数与SplitIssues；结果/完整计数/诊断严格匹配；11例包含四类合法配置；null/abstract具体非零索引及双非法项；同类及双向父子；siblings跨间隔索引与声明字段原因；断言累计无ExpectedError/非空/通配抑制；无运行授予/回收或第二套冲突规则。

只读核对本机UE5.8 DataValidation.h:65/120–124公开Context默认构造、计数与SplitIssues；AutomationTest.h提供FString/int32/通用计数的TestEqual及FString TestNotNull；Array.h:879支持initializer_list，SubclassOf.h:33支持UClass*，故配置列表使用公开类型转换。头在真实构建时仍需UHT生成；本次没有运行编译/链接，静态API读回不替代编译事实。

没有创建World/ASC/宿主或属性实例，只持有测试资产及局部诊断数据；局部强引用随每例结束释放，未Root、GC执行、缓存、计时器或新增清理链。生产状态唯一性/依赖方向不变，未使用反射开洞、friend、全局测试权威状态或真实资产；编辑专项不能证明跨资产、基础存储运行拒绝、Handles归属、Take、Outer变化或客户端。

三授权文件已完成本层实现、完整新增diff/API/范围审查并静态冻结交回，未执行UHT/编译、UE、自动化、PIE、Cook、Git或代理；未写Obsidian/资产/其它源码，不进入T2b/c。Gate16发生在T2-0/T2a创建前，不覆盖新类型/本测试；统筹将统一运行真实专项，当前运行结果为未运行。

## 15-M1 System局部文档（历史静态冻结，本轮证据更新见末节）

统筹逐行接受T2a实际cpp与冻结hash后，生产/测试源码继续冻结等待统一门禁。仅开放四文档：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/System/结构.md`、同目录`GGYGO_结构_System.canvas`及本批AtomicSteps/Validation。先登记预检，应用项目`.kiro/skills/obsidian-canvas-diagram/SKILL.md`；只读计划蓝图、模块参考、实施状态、相邻AbilitySystem/BossAI结构及实际System/消费者代码。

Markdown已按职责、启动/读取接口、状态、显式GE选择、消费者、配置/Cook与验证分节重写。关键接口含输入/前提、作用及输出：TryGet只返回实际Manager或空；父类索引后一次GameData+三GE同步预载；四项UPROPERTY强宿主；完成标记只表示整次尝试可读，非全部成功；五状态及GameData缺失导致三GE未尝试准确；getter和GameData转发只读、不加载/重试。补充ResolveDamage/Heal的覆盖优先、空false空、空true才读取共享及共享仍可空；PlayerCombo在原门禁/Builder成功/CueTag有效时保留无GE Cue，Boss解析缺失在Builder前拒绝无GE/Cue，Health自毁覆盖优先/共享仍空不结算。只写C++开关初始化false，不声称生产蓝图实际值已回读。

结构图保留六个原节点ID：nav、tags、manager、data、consumers、contract；保留上方类节点及列布局，按接口内容增大卡片，第二行移到y=760，底部契约卡移到y=1240避免重叠。新增`load-states`（逐项状态读取）和`selection`（GameData无状态选择）两节点，仍为text类型及原色义；图当前8节点、6边，不放完整函数源码。图内getter/选择接口均有输入、作用、可空输出及生命周期门禁，跨模块消费者链接真实结构。

边更正：保留e1/e2/e3 ID，分别表达Tag直接消费、Manager启动加载/读取软配置、选择空+true调用共享getter；新增e5消费者调用ResolveDamageGameplayEffect、e6GameData调用TryGet并转发Manager、e7Manager输出完成标记/逐项状态。删除原e4 tags→manager“启动注册/全局访问”：实际AssetManager无Tags注册/调用依赖，GGYGOGameplayTags.cpp通过UE_DEFINE_GAMEPLAY_TAG向UGameplayTagsManager注册，保留该边会伪造项目Manager参与链。数据加载与getter反向调用使用不同标签，不将图的输出边解释为模块依赖。

保存后实际读回JSON及全文，12项检查全部true：JSON解析；节点+边ID唯一；边端点存在；每边标签非空且逐条与源码语义核对；text类型/已知颜色；原六节点ID保留；无e4；所有节点矩形无重叠；正文按CJK/ASCII宽度与24px行距估算有容量余量；四份System源码及T2-0/T2a两文件逐字保持；保存图与目标对象完全相等；10个wikilink目标存在且在架构目录唯一解析。容量检查为静态估算，未打开Obsidian进行屏幕渲染验证，不将此项描述为UI截图验收。

10个链接为System结构图、System/结构、计划蓝图、Input/结构、AbilitySystem/结构、BossAI/结构、Character/结构、GameFeature/结构、计划_实施状态、模块参考；其中BossAI/Character为新增明确消费者接缝，未修改这些目标文件。只读核对BossAI当前结构已包含15F解析及缺失边界，保留跨图引用，由其唯一所有者维护。

Gate16构建与48/48常规成功证据已在图/MD同步：6 actions/20.22秒，04.22.01 UTC、0.428347秒、无报告warning/error、UE exit0。仍明确GC/逐项失败/GE选择、实际蓝图开关、Cook和属性运行安全专项未验；T2-0/T2a只经静态审查，尚未真实UHT/编译/运行。文档同步没有提升源码/专项状态，也没有描绘资产接线已生效。

四授权文件完成实际差异/代码事实/图文契约/JSON/布局/链接与读回审查后冻结交回。未修改源码、测试、配置、资产或其它Obsidian/全局入口；未运行UE/UHT/构建/Git/代理，不自动进入T2b。M1仅关闭System局部图文缺口，不关闭本批所有验证或跨模块笔记。

## 笔记与后续限制

A–D阶段登记的System旧Get兜底、按类加载、软字段/新选择接口及自毁消费者图文缺口，已由本M1在授权的System结构MD/Canvas同步；全局模块参考/实施状态仍由统筹核对，配置注释留待H，未写这些文件。

M2仍需同步AbilitySystem局部的玩家默认false开关/共享缺失无GE Cue、G1新建资格与存储类型资格分离、G2原Actor/实时冲突/只拒绝单项/实际登记后记录句柄，以及T2-0/T2a尚未编译运行的区别。BossAI结构已由独立文档所有者更新15F接缝，主流程/计划等后续由统筹排程；本M1只链接，不扩写。各项当前后果与专项未验保持，不能据文档或常规回归提前关闭。

PlayerCombo与BossMelee均已消费D选择机制；保留12共享BuildHitEffectPayload及其原GE/Cue结算链。F/G1/G2已实际编译，属性专项尚未运行；T2-0类型头及T2a编辑测试cpp已静态冻结、未编译，T2b/c运行/生命周期专项和资产迁移未实施。未修改GameplayTags既有增量、其他模块改动、配置或资产。

## 第17次真实门禁补充（后于T2-0/T2a/M1历史冻结）

实际读回`Saved/Logs/ModuleRepairBuildGate_20260930_17.log`：完整构建Succeeded，统筹6 actions，20.77秒。`Saved/AutomationReports/ModuleRepairGate_20260930_17/index.json`报告时间2026.09.30-05.05.42 UTC，49 Success、succeededWithWarnings/failed/notRun/inProcess均0，总时长0.4411526918411255秒。`GGYGO.AbilitySystem.AbilitySet.AttributeConfigValidation`实际Success，执行时间05.05.41 UTC、0.00794370099902153秒，entries为空、warnings/errors均0；测试源码含11个实际配置案例。

因此T2-0新类型已进入实际UHT/编译，T2a编辑矩阵实际成功。上文各层未编译/未运行为当时历史，不覆盖这次后续事实。此门禁不含尚未实现的T2b Give准入或T2c Take/部分成功/构造重入/角色专项，也不证明共享预载/GC。M1 MD/Canvas保持冻结；第17次新证据图文同步仍由统筹独立交接。

## 15-T2b运行准入与本批句柄（历史静态冻结，当时未编译/运行，第19次后续见末节）

统筹根审查接受只读预检，仅授既有`Source/GGYGO/AbilitySystem/Tests/GGYGOAbilitySetAttributeSafetyTest.cpp`及本批AtomicSteps/Validation三文件。精确范围、0–5原子顺序与停止点已在AtomicSteps登记，System组长直接完成。共享测试头及全部生产只读；既有T2a正文和11案例须完整保持，其它测试线夹具不触碰。

已用隔离真实Game World/Context、现有具体TestHost及生产默认ASC；注册和公开Actor生命周期仅补真实缺失，先严格断言原宿主Authority、ASC注册/初始化/Owner与实际Health/Combat默认存储恰两个。默认属性必须由原生ASC InitializeComponent发现，不手工Add/GetOrCreate，不伪造权限。四案例族仅合法独立新增、同资产再次Give、跨资产重复、Health/Combat基础存储冲突；对实际完整列表、指针、类/Outer与各批Handles数量/对象独立严格断言。此处“已用”指测试实现，真实运行仍未执行。

拒绝日志在调用前由已知资产、类、索引和已有对象生成完整字面期望，Exact、非正则、明确次数1；不以日志代替状态。资产强引用及两批句柄持有到清理，原始观察指针/快照只在World存活期间使用。RAII对有效权威ASC先Take已授资源，再销毁World，最后销毁WorldContext；中途失败不旁路清理，teardown不记作回收验证。

### 本步实际差异与断言

已按登记顺序逐步实现并完整读回381行cpp，较原113行仅新增268行、0删除：4个运行夹具include；文件内普通RAII夹具、列表/句柄/新增对象观察断言及完整日志期望；独立Editor测试`GGYGO.AbilitySystem.AbilitySet.AttributeRuntimeAdmissionAndNewHandles`。既有`AttributeConfigValidation`注册/整个RunTest函数及11案例、两个诊断helper按换行归一比较全文保持；未修改生成实现宏或构建保护。

- 每案例独立World；创建Context后真实SpawnActor。注册失败在PostInitialize前Fail；仅在Actor尚未初始化时补公开PreInitialize/InitializeComponents/PostInitialize，组件是否真正Initialize必须成功断言，不直接设置任何初始化/权限状态。
- 准入前实际基础列表数量2、Health/Combat有效且不同、精确类、列表成员、Actor Outer和RF_DefaultSubObject严格断言；ASC组件Owner/ActorInfo Owner均为原宿主，无Avatar且缓存Authority成立。任一前置失败直接返回false，经栈上夹具析构清理。
- 合法Give后从实时SpawnedAttributes与基础快照差集确定唯一新增，检查精确类、原Actor Outer、非默认子对象及公开GetAttributeSet返回同指针；实际列表恰为原两个基础指针加该新增，第一批Handles恰含新增、第二批空。新增身份不从Handles倒推。
- 同资产再次Give和不同资产Give分别保留首次新增及其Handles；各第二批0且实际完整列表逐指针不变。Health/Combat各一次基础冲突调用后，两批均0、实际列表逐指针仍为原两基础对象。无无效项后继续授予、回滚或构造重入案例。
- 四次已知拒绝分别在调用前登记完整消息（资产/索引0/请求类/已有对象/已有类/固定同类原因），`Error, Exact, 1, false`；断言消息不会匹配这些完整期望。日志仅验证对应拒绝诊断，状态/归属由独立计数与指针断言验证。

### 寿命、清理与API自审

World由CreateWorld原生Root/Context持有；Host由实际World持有，默认ASC/基础子对象由Host持有，新增Set在实际ASC SpawnedAttributes中持有。测试不额外Root、强制GC、装配默认Set或改角色。两个配置资产使用TStrongObjectPtr并保持到夹具析构体完成；两批Handles同属夹具，在任何Give后提前返回时仍有效。观察快照/原始指针只在World存活期间读，销毁后只销毁容器。

析构先检查ASC/Host有效且未销毁、同Owner与两者权威，再以第二批→第一批顺序公开Take作清理；无有效上下文时不调用Take，隔离World仍销毁。随后DestroyWorld(false)，Context保持到引擎世界清理结束后再移除，只清自身World包dirty标记。未断言Take后的属性列表、重复Take或GC，不把清理调用描述为T2c1通过。

实际UE5.8源码/API已核对：AActor公开RegisterAllComponents/InitializeComponents与Pre/PostInitialize，注册组件初始化只针对bWantsInitialize且尚未初始化；原生ASC OnRegister创建ActorInfo/缓存角色、InitializeComponent发现宿主默认属性对象；项目PostInitialize建立原Owner/null Avatar。UGGYGOAbilitySystemComponent公共GetSpawnedAttributes/GetAttributeSet、强引用Reset、WorldContext查询/销毁及完整Exact非正则期望API均存在。没有使用测试派生可变权威状态、生产保护字段或私有接口。

### 静态审查与交回边界

15项静态检查全部true：T2a注册/完整函数保持；11案例保留；两诊断helper保持；13个共享头/生产/M1只读hash保持；仅三租约文件变化；四独立夹具前置；四已知拒绝期望；完整Exact/次数1/非正则；双资产强引用与双批句柄归夹具；Take→World→Context清理顺序；无默认挂接/角色ActorInfo伪造/GC/BeginPlay/新反射类型；原保护宏/生成实现保持；实际列表与Handles独立精确断言；新增身份来自实时列表差集；无行尾空白。上述为静态检查，不是自动化运行结果。

cpp SHA256=`F79D6323B8411F2ABD3D7BDE54184B34B1A77AD3F76F68E96AB473AAEAEE0ACA`；共享头仍为`8C3FF93CF84D8A11E92A3AEEDA0DC69D93D6C5158B0A3F41C58B87806C10FC07`。完成源码实际差异/API/范围/析构及中途失败路径审查，三文件静态冻结交回，由统筹统一构建/实测。第17次发生在本cpp新增T2b前，不覆盖本步新测试编译或任何Give运行。

架构核对：生产模块职责/依赖/接口不变；夹具只拥有隔离World、资产和授予句柄，不新增生产状态机、资源权威或执行链。已只读核对计划蓝图与System局部笔记；本轮禁止图文写入，新增测试实施状态记入两记录，Gate17图文证据仍由统筹独立交接。未UE/UHT/构建/自动化执行/Git/代理；未写共享头/任何生产、其它测试线、Obsidian/资产/配置。T2c1/2/3仍未授权，行为不满足时保留严格Fail，不扩写生产或放宽断言。

## 第18/19次实际门禁补充（后于T2b历史静态冻结）

第18次`Saved/Logs/ModuleRepairBuildGate_20260930_18.log`实际完整Failed (OtherCompilationError)，21.38秒，统筹记录exit1。Health迟到创建诊断使用一处protected `GetAttributeSubobject`及三处不存在的`GetNumGameplayEffects`；日志含对应C2248/C2039及派生TestEqual错误。该次未完成新DLL链接与本批自动化，不能因单个action编译而声称T2b已通过。原Messages组长四处公开API短修后，由统筹编号19重新完整构建；本System会话未修改该线夹具。

第19次`Saved/Logs/ModuleRepairBuildGate_20260930_19.log`实际Succeeded，统筹4 actions，10.68秒。`Saved/AutomationReports/ModuleRepairGate_20260930_19/index.json`报告时间2026.09.30-06.18.16 UTC，51 Success、failed/succeededWithWarnings/notRun/inProcess均0，全部叶warnings/errors合计均0，总时长0.46889397501945496秒；统筹记录UE exit0。

| 实际测试叶 | 结果 / 执行时间UTC / 耗时 | 已核对源码覆盖 |
| --- | --- | --- |
| `GGYGO.AbilitySystem.AbilitySet.AttributeConfigValidation` | Success；06.18.15；0.007494896650314331秒；entries空、warnings/errors0 | 11个实际IsDataValid配置案例，保留严格索引/完整诊断与数量断言 |
| `GGYGO.AbilitySystem.AbilitySet.AttributeRuntimeAdmissionAndNewHandles` | Success；06.18.15；0.016042698174715042秒；entries空、warnings/errors0 | 四个独立真实Game World案例族：合法独立新增、同资产再次Give、跨资产重复、Health/Combat基础存储冲突；严格前置/实际列表/指针/Outer/Handles归属及完整拒绝日志 |

当前结论：T2-0已实际UHT/编译；T2a于17已成功并于19复验，T2b于19首次实际通过。Take仅资源teardown，不证明回收、重复Take或GC。未把51/51扩为共享预载逐项失败/GC/覆盖选择、生产蓝图值、Cook、部分失败继续授予/构造重入/非Authority/真实联网client已验。51是项目常规测试叶总数，不是属性专项案例数。

## 15-M1-Evidence局部证据同步（局部静态冻结；全量源码保持异常交回）

精确四文件及E0→E1→E2→E3依赖/验收/停止点已先在AtomicSteps登记。System组长直接执行，只更新System结构MD验证段、Canvas contract验证文字及本批两记录；先读项目Obsidian技能、计划导航、现有图文/链接、实际日志/JSON与两属性测试源码，冻结225个Source文件hash。旧静态交回证据标为当时历史，不删除历史事实。

预检限制：只改contract末两行，保留8节点/6边、全部ID/标签/布局尺寸及TryGet/预载/五状态/GE选择接口；容量不足先停止说明。已按E0→E1→E2顺序写入，再完成E3实际差异/读回审查；四文件局部静态冻结交回，源码保持异常另行登记，不执行UE/构建/Git/代理，不扩入T2c/T1/T3/M2或全局笔记。

### 实际图文差异与验证边界

System结构MD仅替换验证段的旧第16次/未编译状态与证据引用，加入第17/18/19次实际证据和两属性叶有限成功，前文类职责、TryGet/一次预载/强引用/五状态/显式选择/消费者接口及原配置/Cook文字前缀全文保持。第18次完整Failed保留历史，不以旧DLL或单个编译action充当本批通过。未把51/51解释为51个属性案例，也未提升Take/回收或其它专项状态。

Canvas只改contract末两行，当前显示Gate19完整成功、T2-0已UHT/编译、T2a11编辑案例及T2b四独立真实World案例族有限成功，Take仅teardown；明确共享预载逐项失败/GC/覆盖选择、生产蓝图值/Cook、回收/部分失败/构造重入/非Authority/真实client未验。其前四行资源/配置/职责边界保持；不在图中堆17/18次变更历史，历史证据见MD/本记录。

### 实际读回与静态QA

14项图文/内容/保留检查全部true：JSON与原根字段；8节点/6边ID唯一并保持；所有边端点有效；六条非空标签及整条边数据保持；仅contract文字变化；contract前四行/其它节点接口正文保持；全部位置/尺寸/type/color保持；矩形无重叠；所有节点静态文字容量有余量；17处既有wikilink、10个不同目标均存在且唯一解析；MD接口及原配置/Cook前缀保持；MD/图均明确T2a/T2b有限通过和Take仅清理；全部未验边界保持；保存读回无行尾空白。

布局不变，无新增/删除节点、边或wikilink。10个目标仍为System结构图、System/结构、计划蓝图、Input/结构、AbilitySystem/结构、BossAI/结构、Character/结构、GameFeature/结构、计划_实施状态、模块参考。当前contract采用保守宽度1534px、CJK16px/ASCII8.5px、标题34px/正文24px及48px上下留量估算，共6行202px/290px余88px；全图常规容量估算亦有余量。容量是静态估算，未打开Obsidian作屏幕渲染，不声称截图验收。

### 源码快照异常与交接

全量225个Source文件保持检查实际false，未列入上述14项通过检查：路径/数量无新增或删除，224个哈希保持，其中220个.h/.cpp全部保持；System生产文件及T2b cpp/共享类型头均保持。cpp SHA256仍`F79D6323B8411F2ABD3D7BDE54184B34B1A77AD3F76F68E96AB473AAEAEE0ACA`，共享头仍`8C3FF93CF84D8A11E92A3AEEDA0DC69D93D6C5158B0A3F41C58B87806C10FC07`。

只读期间`Source/GGYGO/GGYGO.Build.cs`哈希由`FD4A48A575CEF3B1E9DFE6E12411AC9654F5C1C781D2332928F5C4BCE7F9BC61`变为`677F99C4CB6EE8FA3EB9B55A2A95AE12766E72B69C7CE474D5F7F914EE0E1A06`；读回LastWriteTimeUtc为2026-09-30T06:29:21.0262441Z。本会话只通过apply_patch修改四授权文档，没有写入该脚本或任何源码；无法由这两次哈希确定变化来源，不推断19次历史构建覆盖当前脚本。交统筹核对该变化，本步不回滚、不扩写、不重跑构建。

四文件局部图文证据已完成实际读回/差异/图文语义/JSON/引用/布局/容量审查并冻结交回；该源码快照异常作为尚待统筹核对项保留，不写成全部QA通过。仅修改四租约文档；未UE/UHT/构建/自动化执行/Git/代理，未改源码/测试/配置/资产、其它Obsidian/全局入口。生产架构与接口无本步变更，T2c/T1/T3/M2未进入；停止写入。

## 统筹后续确认及第20次真实门禁（后于M1-Evidence历史交回）

统筹已确认Build.cs的FD4A48A…→677F99C…变化属于授权GameFeature09-G0-0，唯一两行Private Projects及用途注释；Teams Squad h/cpp也属独立授权线。M1-Evidence四文件随后根审查通过：8节点/6边、图本身7处/7目标、MD+图17处/10目标链接有效，contract静态202/290px；不是UI截图。上节当时来源未确认的快照记录保留历史，不再作为当前未知写入。并行期间只核对本会话不得越界、相关只读依赖与System/Test冻结hash，不要求其它授权源码保持。

实际读回`Saved/Logs/ModuleRepairBuildGate_20260930_20.log`完整Succeeded，统筹6 actions、30.58秒。`Saved/AutomationReports/ModuleRepairGate_20260930_20/index.json`时间2026.09.30-06.56.28 UTC，51 Success、failed/succeededWithWarnings/notRun/inProcess均0，所有叶warnings/errors合计0，总时长0.44615185260772705秒；统筹记录UE exit0且已退出。T2a/T2b两叶继续Success、entries空、warnings/errors0。该次在T2c1新增前，只复验既有配置/准入；此前Take仍只teardown。

## 15-T2c1属性Take归属及重复Take（静态冻结，未编译/运行）

根审查接受只读预检，仅授既有属性安全测试cpp及本批两记录三文件；先完成C0登记、实际全文与hash基线。只追加叶`GGYGO.AbilitySystem.AbilitySet.AttributeTakeOwnershipAndRepeatedTake`，原T2a11案例/T2b四World族、所有helper/Fixture/注册必须全文保持，共享头与生产只读。与GF09-G0-1新h/cpp互斥且无逻辑依赖；不写其它线或M1图文。

现有Fixture、IndependentA/B、两资产与两属性Handles足够，无新类型/接口/注入接缝。顺序和精确断言见AtomicSteps C0–C2；B新增必须由实时列表相对Give A后快照差集取得。每阶段前后确认有效原Host/ASC权限和Owner，列表及查询仍准确指向原Health/Combat和存活批次；Take第一批注销A并清空第一批属性Handles，重复调用不碰B/基础，Take第二批最终恰回原两基础、两批0。

局部强引用先于Fixture声明，保活对象仅取公开实际SpawnedAttributes与观察指针同一实例，Fixture先析构完成原Take→World→Context路径后再释放引用。前置/行为不符严格Fail并return，不能静默略过或ExpectedError抑制。注销不是GC销毁；GA/GE句柄、本次无配置的其它资源不予验证结论。

已依C0→C1→C2完成独立测试与静态审查并冻结，实际编译/运行仍未执行，由统筹统一门禁。T2c1b部分失败继续Give及构造/Owner/非权威/client/GC/共享预载/GE选择未授权，不UE/构建/Git/代理，不修改生产让测试绿。

### 实际新增与严格状态断言

cpp在原endif前仅追加120行、0删除（381→501行）；一个普通Editor测试叶`GGYGO.AbilitySystem.AbilitySet.AttributeTakeOwnershipAndRepeatedTake`，无新反射类型/头文件/include。原381行中的全部测试/helper/Fixture/注册及编译保护内容经换行归一比较保持；T2a11例与T2b四World族未改。新增函数只有局部观察引用、期望快照和两个无状态检查lambda，不建立生产权威或执行机制。

初始及各阶段CheckState先确认原Host/ASC有效、未销毁、登记/初始化、同World、组件Owner/ActorInfo Owner及两者Authority；每次后续Give/Take前再次CheckContext。前置/行为失败均已有Test失败记录后return false，不能无声跳过。阶段独立读实际全部SpawnedAttributes、两批属性Handles及Health/Combat/A/B四个公开GetAttributeSet查询；每个应存活对象还验证有效、精确类、原Host Outer和默认子对象标志。

| 阶段 | 实际完整有序列表 | 第一批 / 第二批属性记录 | 公开A / B查询 |
| --- | --- | --- | --- |
| 初始 | 原Health/Combat基础两指针 | 0 / 0 | 空 / 空 |
| Give A | 基础+A | 恰A / 0 | A / 空 |
| Give B | 基础+A+B | 恰A / 恰B | A / B |
| Take第一批 | 基础+B | 0 / 恰B | 空 / B |
| 重复Take第一批 | 同上一列表逐指针保持 | 0 / 恰B | 空 / B |
| Take第二批 | 恰原基础两指针 | 0 / 0 | 空 / 空 |

A先用原CheckSingleRuntimeGrant确认实时新增，再从公开实际列表取相同非const实例保活；B单独计算Give A后快照与实时列表差集，必须恰一个有效新增，并验证A/B指针不同。B不调用仅适用于第一批的旧helper；所有期望指针身份不从Handles推导，句柄是独立受检结果。无ExpectedError/ExpectedMessage或其它错误清除/抑制。

### 强引用、早退与API审查

KeepA/KeepB强引用在Fixture之前声明，后续快照/局部lambda均先于Fixture析构释放；Fixture析构先执行原第二批→第一批Take清理，然后World销毁、最后Context移除，KeepB/KeepA最后释放。因此成功及任何早退时，已保活A/B均覆盖整个原RAII清理期间。引用仅保持观察寿命，不补造注册/Owner/权限，不证明注销时GC销毁或所有GA/GE资源回收。

已核对公共Give/Take、GetSpawnedAttributes非const元素读取/GetAttributeSet查询、StrongObjectPtr初始化/Reset、原Fixture生命期。生产Take权威路径按记录指针RemoveSpawnedAttribute后Reset属性数组；原生RemoveSingle保留其它元素相对顺序，清理仅移除对象所含属性聚合器。本步不调用protected GetAttributeSubobject、不const_cast、不反射开洞/新注册、不强制GC/改角色/构造注入，无新增生产接缝。

### 实际静态检查与冻结

初次16项检查全部true，当时13只读依赖/M1 hash保持。最终复核HealthSet.h/.cpp出现变化，已实际核对当前Parallel Schedule的M2行：授权13E8-P1同步RepNotify阶段/来源资格/宏Scope清理，明确保留原初值/公开访问接口，并与T2c1准入/Take互斥且无未冻结接口依赖。当前构造初始化和公开属性接口已只读核对，本测试不调用RepNotify、施加GE或写数值。本会话未写这两个文件，其哈希不再作为冻结保持门禁；该线仍需由统筹收齐冻结后统一构建。

最终按有效租约重核16项全部true：既有cpp前缀全文保持；11编辑/四准入案例保留；11仍冻结依赖/M1 hash保持且两HealthSet文件识别为授权并行；本会话实际仅写三租约文件；唯一新普通Editor注册；双强引用先于Fixture；A保活来自实际列表；B来自实时差集而非记录；SingleGrant只用于A一次；两Give后三Take顺序；六严格状态均失败早退；上下文确认真实登记/原Owner/Authority；完整列表/双批/类/Outer/默认标志/四查询独立核对；Take保护B并最终双批清空恢复基础；无错误抑制/反射/权限伪造/私有接口/GC/新挂接；无行尾空白。上述为静态范围和实现审查，不是用例运行结果；不冒称最终全部13只读文件hash相同，也不要求GF其它已授权文件保持。

cpp SHA256=`EFAD6815D87544FE7E675CBE791D8A5803360EB415B0B02123B58A85622F37C3`；共享头仍`8C3FF93CF84D8A11E92A3AEEDA0DC69D93D6C5158B0A3F41C58B87806C10FC07`。三文件实际读回/diff/API及资源/早退审查完成，静态冻结立即交回，由统筹构建/运行。第20次在本新增前，只证明T2a/T2b复验，不能提升本Take契约。

已核对冻结System MD/Canvas仍将Take回收列未验，与本步未运行一致，无生产职责/类接口/依赖变化，不空改图文。未写共享头/生产、其它测试线、Obsidian/资产/配置/全局；未UE/UHT/构建/自动化执行/Git/代理，不要求GF09-G0-1其它授权文件保持。本步不验证GA/GE Handles、GC、部分失败后继续Give、构造/Owner/非权威/client或共享预载/选择；冻结后停止写入。

## 第21次实际门禁补充（后于T2c1历史静态冻结）

实际读回`Saved/Logs/ModuleRepairBuildGate_20260930_21.log`为Succeeded、6 actions、32.23秒；常规`Saved/AutomationReports/ModuleRepairGate_20260930_21/index.json`时间2026.09.30-07.50.12 UTC，52 Success，failed/succeededWithWarnings/notRun/inProcess均0，总时长0.45734065771102905秒，52叶errors/warnings合计均0。T2a/T2b/T2c1三个属性叶全部Success且entries=[]；T2c1时长0.005006399005651474秒。统筹确认UE27888 exit0并已退出；本会话只读报告，没有自行构建或运行。

因此上文T2c1未编译/运行是当时历史：当前普通两批Give/Take归属和重复Take契约已实际通过；本次门禁不含尚未追加的T2c1b部分失败继续Give，不证明GC、GA/GE句柄或其它生命周期/网络/构造/共享预载。M1-Evidence图文仍冻结，证据同步需要独立文档租约，本轮不扩写。

## 15-T2c1b部分失败继续Give与本批新增归属（历史静态冻结；第22次后续见末节）

本轮根审查接受预检，当前排程H4明确仅授权既有属性安全测试cpp及本批AtomicSteps/Validation三文件，由System组长直接执行，无代理。基线cpp SHA256=`EFAD6815D87544FE7E675CBE791D8A5803360EB415B0B02123B58A85622F37C3`（501行），两记录基线分别`0856D35A40F08D39D0253FCEFF8FC0B29D760B34B6B872344B3087594C2F82DD`/`4F37A712BFCF972E5DEC574F38143E53F443D134E601F439A5CC4946942D2AD6`；实际全文/13冻结依赖当前hash已保存。旧三个叶、全部helper/Fixture/注册须全文保持，索引0日志helper不改。

唯一候选叶`GGYGO.AbilitySystem.AbilitySet.AttributePartialFailureContinuesAndNewHandles`：单资产[A,原基础Health同类冲突,B]一次真实Give，索引1拒绝后继续B；实际列表相对基线差集识别A/B，完整列表/四查询/两批句柄独立精确核对，再公开Take本批恢复原基础。对象身份不能从Handles倒推，不用仅适用于一个新增对象的CheckSingleRuntimeGrant。现有types/API/Fixture足够，无新生产接缝。

C0→C1→C2精确文件/非目标/验收及停止点见AtomicSteps本节：先登记两记录，再仅追加cpp，静态冻结源码后登记两记录证据并立即交回；执行门禁由统筹负责。写入前登记时新测试未实施；当前已完成追加和静态审查，尚未编译/运行。所有权限/Owner/真实登记前置与早退RAII严格，A/B强引用先于Fixture声明，原Take→World→Context后最后释放，不证明注销时对象GC销毁。

预期日志仅一条索引1完整同类冲突诊断，含当前资产、原Health实例/类，Error/Exact/1/false；已读UE原生Exact非正则完整匹配与准确次数API，缺失或多次命中失败，其它错误不清除/降级/放宽。存活对象exact pointer/class/Host Outer/DefaultSubobject、基础Health/Combat与四公开lookup、FirstHandles[A,B]/Second0及Take后双批0独立核对。

生产/types/其它测试及图文/资产/配置/全局只读，13依赖采用当前已授权P1冻结版本；本测试不触发OnRep、数值写入/GE。非目标null/abstract拒绝分支、GC、GA/GE资源、构造/Owner/Outer、非Authority/client及其它专项，不UE/MCP/构建/Git/代理。需要新类型/文件/接口则停止交回，不修生产或断言让测试绿。

### 实际新增与静态冻结证据

C0先登记真实证据、契约与基线后完成C1。cpp仅追加112行、0删除（501→613行），位置501–612，注册macro502、RunTest506，最终endif613。实际新增唯一普通Editor注册`GGYGO.AbilitySystem.AbilitySet.AttributePartialFailureContinuesAndNewHandles`，无新类型/include/生产接缝；第21次门禁在本新增前，不能证明该叶编译/运行。

内存中仅移除新增区间，按UTF-8字节重新SHA256得到`EFAD6815D87544FE7E675CBE791D8A5803360EB415B0B02123B58A85622F37C3`，与本轮原cpp精确相同；未改写磁盘恢复文件。旧三个测试/全部helper/Fixture/注册及编译保护逐字节保持，索引0Expected helper未改也未用于本新叶。

| 阶段 | 完整实际列表 / 四公开查询 | 属性记录 |
| --- | --- | --- |
| BeforePartialGive | 原Health/Combat两指针；基础查询准确，A/B空 | First0 / Second0 |
| AfterPartialGive | 原基础+A+B；基础查询仍原指针，A/B查询准确 | First恰[A,B] / Second0 |
| AfterTakePartialBatch | 恰原基础；基础查询保持，A/B空 | First0 / Second0 |

一次资产配置[IndependentA,原Health同类冲突,IndependentB]，仅一次真实Give及一次本批Take。Give后先用实际列表相对基线差集得到恰两个有效对象，强引用保活实际非const实例，完整状态再验证A/B顺序/exact class/不同指针/原Host Outer/非DefaultSubobject；句柄独立对照，不用于推断对象身份。Health/Combat每个阶段准确类/指针/Outer/default标志与四查询保持，已有Health不记录不借用不注销。

ExpectedRejection完整包含当前FirstAsset名、索引1、Health类、原Health实例名/类、同类冲突原因；只调用一次`AddExpectedMessage(..., Error, Exact, 1, false)`。已读原生Exact非正则匹配与正次数严格相等实现，框架会对未出现/多次出现给出失败；本测试没有ClearErrors/ExpectedMessages清除、宽松匹配或抑制其它日志。故意冲突仍按生产原路径报Error，未修生产或放宽断言。

KeepA/KeepB声明先于Fixture；NewSets数量/有效性严格检查后才Reset引用。所有局部快照/lambda先销毁，Fixture先沿原第二批→第一批Take、World→Context清理，引用最后释放。初始化、Give前/后、Take前/后均严格核对有效未销毁、原World/Owner/ActorInfo Owner、真实登记初始化及Authority；错误记录后严格早退，不静默跳过，不用反射/const_cast/权限或挂接补造。

### 最终静态审查

17项静态检查全true：原前缀/内存恢复原hash；112追加0删除；旧三注册/T2a11例及T2b四World族/T2c1全文保持；13冻结依赖hash保持；唯一普通Editor注册且无新types/includes；单资产A/Health/B；一Give后一Take；索引1准确唯一完整Expected Error/Exact/1/false；强引用先于Fixture；实际列表差集恰两且先验证有效；无Handles身份倒推/SingleGrant/索引0Expected helper调用；完整有序列表/双批准确记录；四查询及exact class/Outer/default标志；原Owner/Authority/生命周期前置；三个严格状态及最终基础/双批清空；无错误清除/宽松匹配/反射/新挂接/角色/GC/GE；无行尾空白。这些是静态范围及实现检查，不是自动化运行结果。

cpp SHA256=`8B6D97561FAF922C75BF961893C3A0AD339C6DFDCB94EA8F21FE6208C19615FD`；types仍`8C3FF93CF84D8A11E92A3AEEDA0DC69D93D6C5158B0A3F41C58B87806C10FC07`。源码冻结后仅补齐两记录，三文件实际读回/diff/API/RAII/清理与架构检查完成并冻结交回，立即停止写入，由统筹统一构建/运行。所有生产/其它测试/图文/资产/配置/全局保持本会话只读，不要求其它合法工作线保持；未UE/MCP/UHT/构建/自动化执行/Git/代理。

架构核对：生产权限/授予/注销与ASC登记唯一归属未变，无新增循环依赖、第二状态/执行链或内部写入；观察快照/强引用仅本Fixture生命周期，清理仍原RAII。已核对System局部图文冻结状态；普通Take第21次与新增T2c1b未验事实记入两记录，图文证据更新需统筹另行文档租约。未覆盖null/abstract拒绝分支、GC、GA/GE句柄、构造/Owner/Outer、非Authority/client、OnRep/数值/GE/共享预载/选择等，不能标第15批全部完成。

## 第22次实际门禁补充（后于T2c1b静态冻结）

实读`Saved/Logs/ModuleRepairBuildGate_20260930_22.log`：5 actions，已链接UnrealEditor-GGYGO.dll，Result Succeeded，22.16秒；统筹记录exit0。常规`Saved/AutomationReports/ModuleRepairGate_20260930_22/index.json`为2026.09.30-08.50.07 UTC，55 Success、failed/succeededWithWarnings/notRun/inProcess均0，总时长0.4920242428779602秒，55叶errors/warnings合计0。四属性叶全部Success、entries=[]、errors/warnings0：ConfigValidation 0.00784119963645935秒；RuntimeAdmissionAndNewHandles 0.010071299970149994秒；TakeOwnershipAndRepeatedTake 0.009607397019863129秒；PartialFailureContinuesAndNewHandles 0.010829798877239227秒。统筹确认常规UE46824 exit0已退出；独立Health诊断不扩大本模块证明，本会话没有构建/运行UE或自动化。

再次实读第21次Build/Report，普通Take叶Success（0.005006399005651474秒、entries=[]、错误警告0）；第22次旧三叶继续通过。此前T2c1b未编译/运行为当时历史，当前只证明固定单资产[A,原Health冲突,B]一次Give/Take契约：中间项准确拒绝、B继续、实际列表/四查询/两批记录证明只记录注销新A/B且基础保持。不是所有部分失败/构造/角色/GC/GA-GE/共享预载/选择或Cook通过。

## 15-M2-Evidence局部证据同步（静态冻结；保留写前预检）

精确四文件与E0→E1→E2→E3门禁见AtomicSteps本节。先保存实际全文/hash并登记，再写System结构MD/Canvas，遵循项目`.kiro/skills/obsidian-canvas-diagram/SKILL.md`。只改当前验证状态与证据引用；图只改contract末段，8节点/6边及全部ID/标签/坐标/尺寸/颜色保持，无新链接。当前17处MD+图wikilink/10唯一目标实际存在，12冻结源码hash基线保存，测试cpp仍8B6D9756…，类型/生产无修改权限。

验收：21普通Take与22部分失败叶实际Success/零错误警告/空entries，准确对应冻结测试范围；JSON解析、全局ID唯一/端点存在、边标签语义及矩形不重叠、contract静态容量、全部links且无新增链接、正文/接口前缀保持、四文件读回及源码hash保持。静态容量不冒称Obsidian屏幕验收，不操作UE/MCP或UI；容量问题先精简详情入MD，不动矩形。

生产职责/状态/执行链不改；构造/OwnerOuter、非Authority/client、GC、GA-GE资源、共享预载逐项失败/覆盖选择、蓝图值、Cook仍未验，不把55项目叶等同专项案例数。历史报告保留，global由统筹独占，旧部分失败未验文字需另行同步。写前登记时图文未写；随后完成E1/E2/E3并四文件冻结停止，不进入其它专项/新源码/代理。

### M2-Evidence实际最小同步

System MD仅在验证段更新最新22构建/55叶证据、普通Take/repeatedTake21（22复验）及固定中间Health冲突继续B/只记录注销新A/B22；64→67行、+7/-4，前文生产职责/类/接口/权限/资源/一次预载/五状态/显式bool选择/消费者与配置前三条全文保持。原17/18失败/19成功事实和数字仍保留，当前Take仅teardown/部分失败未验误述已清除；强引用只是观察寿命、注销不是GC、55为项目叶总数等边界明确。

Canvas只替换contract末两行并精简重分为三行，raw JSON仅1行替换（134行不变）；contract前四逻辑行、其它7节点、6边、ID/label/type/坐标/矩形尺寸/颜色保持，无新增导航或接口。JSON解析合法、全局14个ID唯一、边端点存在、全部标签非空且原语义不变、所有矩形不重叠。按标题22/body16px、行32/24px及横留白48/竖留白32px静态估算contract208/290px，余82px；没有操作Obsidian/UI或截图，不把静态容量冒称视觉验收。

MD+Canvas仍17处wikilink/10唯一实际目标，顺序与目标全文保持，实际Test-Path均存在，新增0；无新增/移动文件或跨模块写入。16项JSON/范围/接口保持/证据边界/链接/容量/读回/无行尾空白及源码保护检查全true。12冻结相关源码/types/test hash全部保持，测试cpp仍`8B6D97561FAF922C75BF961893C3A0AD339C6DFDCB94EA8F21FE6208C19615FD`，共享头仍8C3FF93C…，本会话未写任何源码/其它测试/配置/资产/全局。

System MD SHA256=`B70C8CBEF7482CD9AC0992240E53B897D2F420246C015372BAAD968E6E06B6BC`；Canvas SHA256=`297FEE349E83B7EDE2407C5B6F8AA6755743B7E6397C11197233457EA8B07DDD`。四文件已实际读回、差异/接口事实/JSON/矩形/容量/链接与范围校验完成，冻结并立即停止，不接新源码/专项。GC销毁/GA-GE资源、null/abstract等其它运行拒绝、构造OwnerOuter、非Authority/client、共享预载逐项失败/覆盖选择、生产蓝图值/Cook仍未验证；不关闭第15批全部缺口。独立Health诊断成功不改变本模块覆盖范围。

全局入口统筹独占：实际只读模块参考仍记部分失败专项进行中，计划_实施状态仍写该叶未编译/运行及旧租约，交统筹依据22同步，不在本四文件授权范围写入；历史测试报告保持原件。生产模块职责/状态唯一归属/依赖方向/清理责任无变化，本轮只补有限实证状态，无新增循环依赖/第二执行器/泄漏内部状态。未UE/MCP/UHT/构建/自动化执行/Git/代理，无新授权后续动作。
