# 第15批 System 原子步骤与文件范围

日期：2026-09-30。唯一执行者：System 长期组长 `01a0e5b5-eb47-7970-ba89-4b5f90919296`，组长直接执行，无子代理。

## 当前授权

第22次完整构建Succeeded（5 actions/22.16秒、统筹exit0）及55/55常规Success，四个属性叶均Success/entries空/错误警告0；普通Take/repeatedTake21及中间Health冲突继续B/仅新增Take22已有限验证。现仅授权15-M2-Evidence：System结构MD/结构Canvas及本批AtomicSteps/Validation四文件，已先登记基线/预检，再完成局部证据同步及16项静态校验；四文件冻结立即交回；源码/types/所有测试、其它图文/global/资产/UE/构建/Git/代理冻结。图ID/边/标签/布局/颜色与生产职责/接口保持，GC/GA-GE/构造/非权威/client/共享预载选择/Cook不扩大。

## 15-A（历史冻结结果）

15-A唯一结果：`TryGet()` 可空获取引擎实际持有的项目AssetManager；失败不创建、Root或安装另一个Manager。GameData直接调用判空；AssetManager使用文件内System日志，不依赖GAS日志。

精确生产范围（项目根 `F:/ue_project/GGYGO/`）：

- `Source/GGYGO/System/GGYGOAssetManager.h`
- `Source/GGYGO/System/GGYGOAssetManager.cpp`
- `Source/GGYGO/System/GGYGOGameData.cpp`

只读依赖：引擎 `UEngine::InitializeObjectReferences`、`GEngine->AssetManager`、GameData头文件以及项目所有调用点。没有12命中执行或07/14b状态依赖。

非目标：预载实现、GameData配置字段、HealthComponent、GA/BaseGA、AbilitySet、配置、GameplayTags、测试、Obsidian；不操作UE、构建或Git。

断言：正确配置只返回实际项目实例；GEngine/Manager未就绪或类型不符返回空并诊断；不存在兜底对象及Root引用；GameData传播空值；现有加载器、缓存、启动预载行为不变。

停止点：三文件变更、全项目交叉引用及静态架构审查完成，记录证据后冻结交回。当前状态：已完成本层实现与静态审查，五个授权文件全部冻结；编译、动态回归及局部图文仍未完成。

## 15-B（历史冻结结果）

唯一结果：父类启动索引完成后，一次预载配置的GameData及Damage/Heal/SelfDestruct三项GE，Manager独占GC可追踪强引用和逐项加载结果；运行getter只读取已完成快照。

精确生产范围：`Source/GGYGO/System/GGYGOAssetManager.h`、`Source/GGYGO/System/GGYGOAssetManager.cpp`、`Source/GGYGO/System/GGYGOGameData.h`、`Source/GGYGO/System/GGYGOGameData.cpp`。

只读依赖：已冻结A接口、引擎AssetManager启动/软引用/GC机制、GameplayEffect类型、GameData现有序列化配置、现有消费者及Cook配置。共享API在本步骤冻结供C/D使用；A→B→C与B→D顺序不变。

非目标：Health、GA、AbilitySet、默认/覆盖解析、配置与资产、测试和Obsidian；不操作UE、构建或Git。不新增调度器、通用加载框架或第二份配置。

断言：所有读取仅在游戏线程且整次启动预载完成后可用；未配置、加载失败、Ready逐项区分，GameData不可用时GE报告依赖不可用；一项GE失败不阻止其他项；getter不加载/重试；强引用随Manager生命周期由GC管理；运行加载不声明设置Cook规则。

停止点：四文件实现与API静态审查、记录完成后全部冻结；编译、动态测试和文档闭环由后续授权安排。当前状态：四份源码与两份记录已完成本层静态审查并冻结交回；没有执行编译、UE、自动化或Git。

## 15-C（历史冻结结果）

唯一结果：DamageSelfDestruct保留非空SelfDestructEffectOverride优先；空覆盖只读15-B的共享自毁GE快照，缺失诊断并返回，不在运行入口加载软引用。

精确生产范围：`Source/GGYGO/Character/Components/GGYGOHealthComponent.h`、`Source/GGYGO/Character/Components/GGYGOHealthComponent.cpp`。06已冻结，统筹已交接此最小接缝。

职责与只读依赖：System负责共享预载及GC资源宿主；HealthComponent请求既有ASC的自毁GE结算，继续持有自身死亡阶段；HealthSet负责属性结算，三者不新增状态或互读内部数据。只读15-B四份System源码、06冻结实现与验证记录、GameplayEffect/ASC公开接口及标签。先后顺序B冻结→C消费→静态审查→记录冻结。

非目标：死亡、宿主/Avatar身份、权限或重入规则，Spec/SetByCaller/Tag/既有结算链，GA/BaseGA/ASC/AbilitySet/HealthSet，其它Character源码、测试、配置、资产与Obsidian；不操作UE、构建或Git。

验收断言：非空覆盖不访问共享getter；空覆盖调用UGGYGOGameData::GetSharedSelfDestructGameplayEffect；缺失在MakeEffectContext/MakeOutgoingSpec/Apply之前诊断并返回；无同步加载、第二缓存或直接Health写入；除取值与诊断块外cpp逐字等于交接基线，h只改契约注释，06死亡投影/重入代码保持。基线自毁函数只有DeathState/ASC检查，没有Authority/Avatar检查；这些未由本步骤增加，也不据此声称自毁权限验证已通过。

停止点：两源码与两记录完成静态审查后冻结交回，不进入D/G/H或测试。当前状态：两源码与两记录已完成本层实现、差异与静态审查，全部冻结；没有执行编译、UE、自动化或Git。

## 15-D（历史冻结结果）

唯一结果：冻结Damage/Heal的可复用覆盖选择接口；非空覆盖优先，空覆盖只有显式bool opt-in才读取已有共享预载getter，无隐式启用。

精确生产范围：`Source/GGYGO/System/GGYGOGameData.h`、`Source/GGYGO/System/GGYGOGameData.cpp`。

拟冻结公开契约：`static TSubclassOf<UGameplayEffect> ResolveDamageGameplayEffect(TSubclassOf<UGameplayEffect> EffectOverride, bool bUseSharedWhenUnset)`及同参数返回类型的`ResolveHealGameplayEffect`。bool没有省略默认实参，调用者必须明确传入；新增调用方配置开关默认false以保持旧空值语义。非空覆盖+任意bool返回覆盖；空+false为空且不读Manager；空+true读对应共享getter，共享不可用仍为空。此为无状态类选择机制，不施加GE、不包含具体角色业务。

职责与只读依赖：GameData提供配置及公开取值/选择机制，Manager仍唯一持有启动快照与GC强引用；选择接口只消费B getter，不写Manager或软配置。只读Manager.h/.cpp、既有Health调用、GA/BaseGA契约及12/本批门禁记录。顺序：登记预检/接口→两源码实现→差异/交叉引用/边界审查→记录冻结→后续E/F另行授权。

非目标：Manager预载、Health、GA/BaseGA/ASC/AbilitySet/HealthSet、治疗GA、测试、配置、资产及Obsidian；不改变三软字段名/类型/序列化，不加载/重试/缓存，不操作UE、构建或Git。

验收断言：两解析函数均先返回有效覆盖，再按显式bool取对应预载getter；false不读取共享，缺失返回空；既有getter和配置逐字保持；无新增状态、依赖、执行或清理链。调用方默认false兼容义写在公开注释，E/F尚未接入。

停止点：仅两源码与两记录完成静态审查后冻结交回，不进入E/F/G/H/测试。当前状态：两源码与两记录已完成实现、实际差异/交叉引用/边界静态审查，接口和四文件均冻结；D未编译或动态测试。

## 15-E（历史冻结结果）

唯一结果：玩家连段能力保留DamageEffect覆盖字段，新增蓝图配置开关bUseSharedDamageEffectWhenUnset默认false，仅在既有命中消费点调用D解析接口，兼容旧空值无伤害但保留Cue。

精确生产范围：`Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.h`、`Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp`。

准确消费点：HandleMeleeHit先经过本次激活/Authority/目标/当前段/ASC/Avatar门禁，原在BuildHitEffectPayload(TargetASC, DamageEffect, ...)直接消费类值；改为该调用前的局部const TSubclassOf，由ResolveDamageGameplayEffect(DamageEffect, bUseSharedDamageEffectWhenUnset)取得。BuildHitEffectPayload继续唯一构造载荷，Spec有效才施加伤害，随后按原逻辑发送HitCueTag。

职责与只读依赖：GA持有自身配置并请求既有GAS执行，System提供无状态类选择及唯一共享快照，Combat负责命中查询。只读D的GameData.h/.cpp、Manager、12/04 BaseGA Builder、既有连段生命周期及门禁记录。顺序D冻结/12释放→E预检→命中取值适配→静态矩阵和生命周期差异审查→记录冻结；F不包含在本租约。

非目标：连段窗口/输入/Montage/预测/重入/End生命周期，ASC/BaseGA/Builder/Task/Hero、BossMelee、AbilitySet、测试、配置、资产及Obsidian。不改名DamageEffect，不迁移GA资产，不创建跨帧缓存，不操作构建/UE/Git。

验收断言：新开关EditDefaultsOnly/BlueprintReadOnly且初始化false；非空覆盖始终优先；空+false仍无GE但保留原Cue；空+true共享缺失诊断后走同一无GE Builder/Cue路径，无其它GE回退；Resolved类值只在本次栈帧。所有清理、激活、窗口、预测与执行代码保持交接基线。

停止点：两源码与两记录静态审查完成后冻结交回，不进入F/G或测试。当前状态：两源码与两记录已完成实现、实际差异/静态矩阵/清理保持审查，全部冻结；没有执行构建、UE、自动化或Git。

## 15-F（历史冻结结果）

唯一结果：Boss近战保留DamageEffect覆盖字段，新增蓝图可配置bUseSharedDamageEffectWhenUnset默认false；配置校验与命中均用冻结D解析规则，空覆盖未opt-in及opt-in但共享缺失继续失败，不退化为无伤害成功。

精确生产范围：`Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.h`、`Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp`。

准确接缝：ValidateMeleeConfiguration原直接检查!DamageEffect，改为局部解析结果判空；既有IsDataValid及ActivateAbility仍调用该校验。HandleMeleeHit在原Active/Cleanup/Blend/Trace/Authority/TargetASC/Avatar门禁后局部解析，缺失诊断返回，成功传入唯一BuildHitEffectPayload，其余Spec/SetByCaller/Cue不变。

职责与只读依赖：Boss GA配置自身覆盖/opt-in并请求GAS；System负责无状态选择及唯一共享预载资源，CMC执行ActionMotion，Animation/Trace及BossAI职责不变。只读D GameData/Manager、12/04 BaseGA Builder、14a配置校验及本次构建记录。顺序D冻结/门禁→F预检→两接缝实现→静态矩阵/生命周期差异→记录冻结。

非目标：原14a其它校验、ActionMotion、Montage/播放率/预测/生命周期/清理/选招规则，D、PlayerCombo、BaseGA/ASC/Task、其它Boss/Combat源码、AbilitySet、测试、配置、资产及Obsidian；不改DamageEffect名/类型，不加载/重试/缓存，不操作UE、构建或Git。

验收断言：新开关EditDefaultsOnly/BlueprintReadOnly默认false；校验与命中均明确传DamageEffect及bool给同一D接口；覆盖+任意bool优先，空+false失败，空+true共享缺失失败，成功时非空GE走原Builder。只局部const类值，无成员缓存；所有非接缝代码逐字保持。

停止点：两源码与两记录静态审查后冻结交回，不进入G/H或测试。当前状态：两源码与两记录已完成实现、实际差异/静态矩阵/生命周期审查，全部冻结；F未构建或动态验证。

## 15-G只读预检（历史；随后G1/G2分别授权）

唯一目标：AbilitySet属性授予只接收无冲突的新属性存储，编辑器与运行使用同一冲突谓词；无效/冲突项拒绝但其余合法项继续，已有实例绝不成为本次回收所有权。当前仅调查与记录，不实施以下步骤。

待冻结谓词（cpp文件内共用，不新增跨模块API）：合法UAttributeSet类A/B，若同类或任一IsChildOf另一则冲突；否则调用引擎UAttributeSet::GetAttributesFromSetClass枚举两类（含继承）的GAS支持属性，按FGameplayAttribute字段身份比较，交集非空则冲突。公共祖先本身不是判据，不按属性名字判重，不自行构建反射框架或长期缓存。

证据及语义：GAS GetAttributeSubobject选择SpawnedAttributes中首个IsA声明类的实例；继承字段仍归声明基类，故同一Health基类下两个Sibling不可并存。HealthSet/CombatSet共享空UGGYGOAttributeSet基类但字段无交集，必须允许。空基类Sibling只按具体类/属性查询；泛化GetSet<空基类>的首匹配语义不升级为全局唯一约束。

建议原子顺序：G1共享谓词/编辑校验冻结→G2运行实例准入冻结→T2独立夹具授权→构建/动态门禁→M2及统筹全局文档。两个步骤同一组长顺序写同cpp，无并行写入者，避免把编辑配置生命周期与运行对象所有权一次混包。

| 候选步骤 | 唯一结果 / 精确生产文件（项目根相对） | 只读依赖 / 非目标 | 验收断言 / 停止点 |
| --- | --- | --- | --- |
| G1 | 冻结共享类冲突谓词及WITH_EDITOR IsDataValid；`Source/GGYGO/AbilitySystem/GGYGOAbilitySet.h`、`Source/GGYGO/AbilitySystem/GGYGOAbilitySet.cpp` | 引擎AttributeSet/ASC公开API、现有GrantedAttributes配置；不改运行授予/回收、宿主、ASC、属性字段、GA/GE校验或测试 | 配置中空/无效/抽象类报索引诊断，同类/父子/共享属性Sibling成对报错，独立Health/Combat合法；Super Invalid保留；同谓词不实例化/加载/缓存。两源码+15两记录静态审查后冻结，G2单独授权 |
| G2 | 每个属性项在NewObject前检查有效Actor Outer与实时SpawnedAttributes冲突；成功新增才入本次Handles；`Source/GGYGO/AbilitySystem/GGYGOAbilitySet.cpp` | G1冻结helper、ASC公开GetSpawnedAttributes/AddAttributeSetSubobject、CombatantState默认属性宿主；不改ASC/宿主、TakeFromAbilitySystem、能力/GE授予阶段或资产 | 保留Authority，单项失败continue，前序新授予与跨资产既有项同样参与冲突；不GetOrCreate/借用/Root/回收既有项；NewObject后复核Outer与实例/冲突，挂接确认后只记录NewSet；部分成功和客户端不授予保持。cpp+15两记录冻结，不自动写测试 |

G2门禁细节：现有IsOwnerActorAuthoritative是缓存网络角色判定，不证明GetOwner有效。每项使用当时GGYGOASC->GetOwner作为Actor Outer，IsValid且非销毁中才NewObject；构造后复核NewSet有效、Outer仍同一有效Actor及ASC Owner未变，并复查实时冲突，不沿用过期数组。已在SpawnedAttributes中的非空实例按其类检查（不因销毁标记擅自清理或抢占），空项不提供冲突类；实例列表唯一归ASC。AddAttributeSetSubobject返回输入指针并不证明已登记，须确认NewSet在实时列表后再记句柄。失败的新未登记对象交GC，不主动销毁或移除其它实例。

非目标：修复/清理ASC既有重复项、改变GetSet查找、基础属性授权、角色复活、宿主初始化、整个AbilitySet事务回滚、给合法GE/GA加依赖过滤、引用计数或替代执行链。拒绝属性项后，原能力/GE阶段仍独立按既有规则执行；不声称整个资产全有或全无。编辑器只能识别单资产内冲突，跨资产/宿主冲突由运行门禁兜住。

Sibling取舍：本机UE5.8已有支持属性枚举和字段比较API，可复用识别继承存储交集，无需独立复杂反射规则。若后续要允许同一继承属性的多个存储，必须先改变GAS寻址/权威归属，属于范围外架构变更，不在G实现。

预检历史停止点：只读证据、谓词矩阵和G1/G2方案已记录，两记录冻结交回，生产保持未写。统筹随后仅重新开放下述G1四文件，G2尚未授权。

## 15-G1（历史冻结结果）

唯一结果：cpp文件内冻结可供编辑及后续运行共用的类有效性/冲突谓词，并接入WITH_EDITOR IsDataValid，仅校验GrantedAttributes。

精确生产范围：`Source/GGYGO/AbilitySystem/GGYGOAbilitySet.h`、`Source/GGYGO/AbilitySystem/GGYGOAbilitySet.cpp`。共享谓词由本组长唯一写入，G2获得授权前保持冻结。

契约：新授予类要求有效、非抽象UAttributeSet；存储冲突判断只要求有效UAttributeSet类，abstract基类同样参与，不能用新建资格过滤已有存储。此类同类或父子冲突，否则引擎GetAttributesFromSetClass的继承属性实际字段交集非空冲突；空便利基类/仅共同UAttributeSet根不误拒绝。IsDataValid为每个空/无效/抽象新配置及冲突对报告索引/类/原因，保留Super Invalid，不实例化或加载。

只读依赖：已接受G预检、本机UE5.8 AttributeSet类枚举/字段相等API、IsDataValid标准入口、原配置及Give/Handles/Take。顺序预检登记→共用helper冻结及编辑接入→差异/矩阵/清理边界审查→两源码两记录冻结；后续G2须独立批准。

非目标：运行授予拒绝/Outer/SpawnedAttributes门禁、回收、宿主/ASC/Health、F/GameData/Manager、其它源码/测试、GA/GE配置校验、Config/资产/Obsidian；不构建/UE/Git，不创建代理、长期缓存或反射框架。

验收断言：实际字段身份判交集；同类/双向父子及共享Health sibling拒绝、独立Health/Combat允许；编辑诊断完整且Super Invalid不丢失；原GiveToAbilitySystem及GrantedHandles/Take完整逐字保持，序列化字段不变。停止点：四文件完成静态审查后冻结，不进入G2/H/T。当前状态：共用helper与编辑实现完成，实际差异/12项静态断言/矩阵/清理边界审查完成，两源码两记录冻结；未构建或动态验证，G2未实施。

G1更正预检：统筹指出原冲突helper用IsGrantableAttributeSetClass早退，会遗漏abstract标记的有效已有类。本轮只重新开放同一G1四文件，新增文件内IsValidAttributeSetClass类型门禁，供新建资格与冲突谓词分别消费；编辑新配置继续拒绝abstract，运行函数仍逐字保持。断言：abstract类型能进入同类/父子/字段交集判断，非法类型才早退；新建资格仍拒绝abstract，无新增实例/缓存。当前更正状态：cpp最小更正完成，6项补充静态断言全部通过，header/编辑逻辑/运行授予/回收逐字保持，四文件再次冻结；仍未构建或动态验证，不进入G2。

## 15-G2（本轮冻结结果；保留写源码前原子预检）

唯一结果：属性项仅在有效权威ASC、原有效权威Actor Outer和实时存储无冲突时新建并挂接；确认本次NewSet实际在列表后才记录其回收句柄。

精确写入文件：`Source/GGYGO/AbilitySystem/GGYGOAbilitySet.cpp`、`AAADocs/Modules/System/Module_Repair_15_AtomicSteps.md`、`AAADocs/Modules/System/Module_Repair_15_Validation.md`。唯一写入者为本System组长；header及G1三个helper保持冻结。模块职责：AbilitySet只拥有本次授予的新资源记录；ASC唯一拥有SpawnedAttributes，Actor拥有属性对象生命周期，GAS既有机制执行GA/GE。通过公开GetSpawnedAttributes/AddAttributeSetSubobject消费，不新增宿主状态。

只读依赖：G1冻结类型/新建资格/冲突谓词、本机UE5.8 Actor/ActorComponent有效性及Authority接口、ASC挂接实现、Combatants默认属性宿主、路由/台账/排程。顺序：本记录预检登记→单cpp属性循环实施→与G1冻结基线实际差异及边界审查→验证记录→三文件冻结。无并行写入同文件。

非目标：GA/GE授予阶段、GrantedHandles/Take、G1编辑逻辑与helper、ASC/Actor宿主、既有重复项清理、全资产事务/回滚、借用/引用计数/GetOrCreate、其它源码/测试/配置/资产/Obsidian；不操作UE/构建/Git/代理，不进入H/T/M。

验收断言：新配置非抽象有效AttributeSet；每项NewObject前ASC有效且非销毁、缓存Authority为真，GetOwner为有效非销毁且HasAuthority的Actor；实时非空既有存储按G1类型谓词比较，abstract已有类不被新建资格过滤，前序/跨资产/基础存储均参与；构造后同ASC/原Actor身份和权限仍有效、NewSet有效且Outer相同，再重新读取列表比较；Add后确认NewSet指针确在当前列表，只有它可写本次Handles。所有错误仅跳过该属性项，原GA/GE阶段及Handles/Take逐字保持；无缓存或其它对象移除。Add返回值不当作登记证据。

停止点：上述三文件静态审查完成即冻结交回；如需扩大接口或修改其它生命周期立即停止，不实施测试或笔记。当前状态：预检登记后已完成单cpp属性循环实施、实际diff/API/边界审查，12项静态断言全true；三文件冻结。G1 helper/编辑逻辑、header、原GA/GE阶段及Handles/Take逐字保持。第15次构建覆盖F/G1，发生在G2实施前，不证明本次G2编译或专项行为；原47项Success与新增Input前置1Fail分开记录于Validation。G2未构建/运行，T2及Obsidian同步仍待独立授权。

## 15-T2-0（历史静态冻结结果；保留写类型前极简预检，第17次后续见Validation）

唯一结果：冻结后续T2共享类型，直接使用既有protected/public边界，不改变生产反射或授予/回收接口。精确写入：`Source/GGYGO/AbilitySystem/Tests/GGYGOAbilitySetAttributeSafetyTestTypes.h`及本批AtomicSteps/Validation，共三文件，System组长唯一写入。

类型契约：测试AbilitySet派生类只提供本类GrantedAttributes配置入口；普通C++ GrantedHandles派生视图只读属性记录数量/指针；反射属性类型包含非抽象带字段父类、其两siblings、空共同祖先及两独立字段siblings、独立abstract类（null由空TSubclassOf表示）；具体CombatantState测试宿主仅继承真实基础ASC/Health/Combat机制。全部手写函数在头内定义，generated.h最后include，UCLASS/GENERATED_BODY/UPROPERTY遵循现有测试模式，不留下cpp链接函数，不添加额外状态。

只读依赖：生产AbilitySet.h/.cpp、CombatantState.h/.cpp及已有测试头模式、本机AttributeSet/FGameplayAttributeData、路由/台账/排程、第16次日志/报告。顺序：本预检→单头类型→API/UHT规则静态审查→两记录→三文件冻结。共享头供后续T2a/b只读；同测试cpp分步串行交接。

非目标：测试cpp/自动化注册或执行、IsDataValid/Give/Take生产代码、构造后Rename钩子、SwapRoles/真实客户端夹具、GA/GE业务、测试派生权威状态、其它文件/资产/Obsidian；不操作UE/构建/Git/代理，不进入T2a/b/c。

验收断言：仅新增本头，生产内容保持；配置写入仅GrantedAttributes，Handles无可写数组/指针引用入口；同类/双向父子/共享字段siblings和独立siblings关系可由实际UClass元信息表达，abstract由UCLASS标记；宿主非abstract且继承生产默认子对象机制，无替换ASC；所有手写方法定义自足、无UHT不支持条件包装/未定义函数/新模块依赖。停止点：三文件静态审查后冻结；需要其它类型或生命周期钩子则停止交回。当前状态：极简预检登记后已完成单头类型、API/UHT规则静态审查，12项静态断言全部true，三文件冻结；未运行UHT/编译或属性专项，测试cpp尚不存在。第16次Succeeded（6 actions/20.22秒）及48/48常规Success属于此前G2编译门禁，不能证明本次新头或属性专项。

统筹已接受的最小后续顺序：T2a只编辑配置矩阵→T2b只运行准入与新增Handles归属→T2c1回收/部分成功→T2c2构造后Owner/Outer变化→T2c3非Authority（真实联网客户端另设前置）。T2a/b/c各自需授权；本地SwapRoles只证明角色门禁，不冒充真实client，InitAbilityActorInfo不冒充组件GetOwner/Outer变化。

## 15-T2a（历史静态冻结结果；保留写测试前原子预检，第17次后续见Validation）

唯一结果：注册Editor属性配置专项，通过真实IsDataValid及公共FDataValidationContext断言返回值、错误数量和具体配置索引/类/原因诊断。精确写入：新`Source/GGYGO/AbilitySystem/Tests/GGYGOAbilitySetAttributeSafetyTest.cpp`及本批AtomicSteps/Validation，共三文件，System组长唯一写入；共享头及G1/G2只读。

冻结注册名：`GGYGO.AbilitySystem.AbilitySet.AttributeConfigValidation`，EditorContext/EngineFilter，主体受WITH_DEV_AUTOMATION_TESTS && WITH_EDITOR门禁。cpp正常include共享类型及其inline generated cpp，不增加反射类型。仅实例化瞬态TestAsset，TStrongObjectPtr局部保活；每个配置案例建立独立资产与Context，公共GetNumErrors/SplitIssues读取真实结果，不覆写/模拟校验。

只读依赖：T2-0类型/配置入口、生产IsDataValid及属性类、FDataValidationContext/AutomationTest公共API、现有测试注册模式。顺序：本预检→单cpp编辑矩阵实现→实际读回/只读基线/API/断言审查→两记录→三文件冻结。矩阵至少空合法、单独合法、null/abstract拒绝、同类重复、双向父子、共享继承字段siblings、空共同祖先独立siblings合法、Health/Combat合法；无效项用非零索引、冲突对用明确索引，诊断严格匹配期望内容与数量，不用非空字符串或通配ExpectedError代替。

非目标：World/ASC创建、Give/Take/Handles执行、运行准入/回收/部分成功、构造重入/客户端、新测试类型、生产可见性、其它文件/资产/Obsidian；不操作UE/UHT/构建/Git/代理，不进入T2b/c。若真实校验未满足期望，测试保留失败并报告，不同时改生产或放宽期望。

停止点：三文件静态审查后冻结交回注册名/diff/hash/未运行状态，由统筹统一构建及真实专项。当前状态：预检后已新增独立Editor测试cpp，11个真实配置案例，完整诊断/索引与数量严格断言；12项静态检查全部true，完整新增diff/API审查完成，三文件冻结。共享头SHA256保持8C3FF93CF84D8A11E92A3AEEDA0DC69D93D6C5158B0A3F41C58B87806C10FC07，AbilitySet生产h/cpp逐字保持。T2-0/T2a尚未实际UHT/编译/运行，Gate16不含本次测试；不进入T2b/c。

## 15-M1（历史冻结结果；保留写文档前原子预检，本轮证据更新见15-M1-Evidence）

唯一结果：将System结构Markdown/Canvas的旧Get兜底Manager、LoadGameDataOfClass/按类缓存描述，纠正为当前TryGet/一次启动预载/完成快照/显式GE选择事实及真实验证边界。精确写入四文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/System/结构.md`、同目录`GGYGO_结构_System.canvas`、本批AtomicSteps/Validation，System组长唯一写入；所有源码及相邻模块/全局Obsidian只读。

只读依赖：实际AssetManager/GameData h/cpp、Tags原生注册实现、PlayerCombo/BossMelee/Health消费接口、计划蓝图/模块参考/实施状态及相邻AbilitySystem/BossAI结构、Gate16证据、项目`.kiro/skills/obsidian-canvas-diagram/SKILL.md`。顺序：预检登记→Markdown契约与状态→保留既有ID更新Canvas→JSON/ID/端点/边标签/不重叠/链接/代码事实及读回审查→两记录→四文件冻结。

验收断言：TryGet限游戏线程、可空且不新建/Root/替换Manager；父类启动索引后一次GameData+3GE预载，Manager UPROPERTY独占强宿主；完成旗标不等于全成功，逐项五状态与GameData依赖失败准确；getter只读已完成快照，不加载/重试，运行配置变化需重启，Cook另配。GameData静态Get/GetShared转发，ResolveDamage/Heal(Override,显式bool)三分支与消费者玩家可空仍Cue/Boss缺失拒绝无GE/Cue准确；链接相邻实际结构，不声称蓝图默认值已回读或GC/选择专项通过。保留六原节点ID及可复用布局，必要新增状态/选择接口节点；e4 tags→manager无真实调用依赖，删除并记录理由。图/MD关键接口包含输入/作用/输出，检查每图ID/端点/非空准确标签、矩形无重叠、新链接存在并读回。

非目标：任何源码/测试/配置/资产或其它Obsidian、全局入口、T2b/c、运行验证；不操作UE/构建/Git/代理，不新增流程图或改变生产架构。已有Gate16只作编译/常规回归证据，T2-0/T2a待真实门禁。

停止点：四文件文档校验后冻结交回，停止写入，不自动接T2b或其它步骤。当前状态：预检后已完成System结构MD/Canvas同步、代码事实及接口输入/作用/输出审查；原六节点ID保留，新增状态/选择两节点与e5/e6/e7，删除无真实依赖的e4，8节点/6边。12项JSON/ID/端点/标签/矩形无重叠/静态文字容量/10链接存在/读回与六源码测试保持检查全true；四文件冻结。未做Obsidian屏幕渲染、UE/构建/专项运行或任何其它写入；Gate16常规证据与T2-0/T2a/GC/选择/资产/Cook未验边界保留。

## 步骤去向（T2b/T2c1/T2c1b有限通过，其它源码专项未授权）

以下路径相对项目根；Obsidian路径相对 `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/`。

| 步骤 | 唯一结果 / 精确候选文件 | 前置 / 只读依赖 | 非目标 / 断言 / 停止点 |
| --- | --- | --- | --- |
| H | Cook/启动配置说明；`Config/DefaultGame.ini`、`Config/DefaultEngine.ini` | A/B及配置租约 | 不改实际配置；Cook依据配置，无效类路径可能引擎先Fatal；说明核对后冻结 |
| T1 | Manager/共享资产专项测试；`Source/GGYGO/System/Tests/GGYGOSharedGameDataTest.cpp`、`GGYGOSharedGameDataTestTypes.h` | A/B/D接口冻结 | 不替换运行编辑器Manager；隔离夹具覆盖空值、逐项可用、GC和解析；静态审查冻结，执行由统筹安排 |
| T2b | 运行准入与本次Handles归属；同一测试cpp及本批两记录（3文件） | 第19次完整构建及两属性叶Success，源码冻结 | 四独立World案例族实际通过；Take仅teardown，不扩回收/部分失败/网络/重入生命周期 |
| T2c1 | 属性注销归属/属性Handles清空/重复Take；同一测试cpp及本批两记录（3文件） | 第21次完整构建与叶Success，源码冻结 | 普通两批归属/幂等已有限通过；GC/GA-GE资源等未验，本层无写入权限 |
| T2c1b | 单项冲突后继续Give及本批新增归属；同一测试cpp及本批两记录（3文件） | 第22次完整构建及叶Success，生产/types/测试冻结 | 单资产[A,已有Health冲突,B]有限契约通过；其它失败与生命周期未验，本层无源码写入权限 |
| T2c2 | 构造后Owner/Outer变化；同一测试cpp/类型头及本批两记录（4文件） | T2b冻结，单独重开生命周期类型租约 | 公开Rename真实改变动态ASC GetOwner；不迁移生产默认子对象；若公开前置不成立停止交回 |
| T2c3 | 非Authority拒绝；同一测试cpp及本批两记录（3文件） | 正常注册/初始化真实角色前置另审 | 本地角色门禁与真实NM_Client复制宿主分别验证；无真实网络前置不声称client通过，冻结 |
| T3 | GA兼容选择测试；`Source/GGYGO/AbilitySystem/Tests/GGYGOSharedDamageSelectionTest.cpp`、`GGYGOSharedDamageSelectionTestTypes.h` | E/F及12接口冻结 | 不抢改12夹具；覆盖/开关矩阵、旧空值与Cue/Boss失败、缺失诊断；静态审查冻结 |
| M2 | AbilitySystem共享配置文档；`AbilitySystem/结构.md`、`AbilitySystem/GGYGO_结构_AbilitySystem.canvas`、`AbilitySystem/GGYGO_流程_伤害结算.canvas`（Obsidian） | E/F/G冻结、12图文交接及文档租约 | 不写全局状态；保留共享命中构造及唯一结算链，记录默认/覆盖与授予约束；校验后冻结 |

依赖顺序：A→B→C；B→D→〔12门禁及交接〕→E/F；G可独立规划但需授权；各实现冻结→对应测试→局部图文。BaseGA生产文件只读，继续由既有Builder构造命中载荷。

## 15-T2b（历史静态冻结结果；保留写测试前预检，第19次后续见Validation）

统筹已接受只读预检并授三文件租约：`F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGOAbilitySetAttributeSafetyTest.cpp`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_AtomicSteps.md`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_Validation.md`。唯一执行者为本System组长，直接完成，无代理。唯一目标：真实权威默认宿主的属性准入，以及本批Handles仅记录实际新增对象。

冻结只读接口：`Source/GGYGO/AbilitySystem/Tests/GGYGOAbilitySetAttributeSafetyTestTypes.h`；生产`GGYGOAbilitySet.h/.cpp`、`GGYGOAbilitySystemComponent.h/.cpp`、`Combatants/GGYGOCombatantState.h/.cpp`、`Attributes/GGYGOHealthSet.h/.cpp`与`GGYGOCombatSet.h/.cpp`。只读依赖还包括UE5.8公开World/Actor/ASC生命周期及AutomationTest精确日志API。既有T2a函数、注册名及11案例全文保留。

顺序与原子文件范围（0–4各仅测试cpp，5仅本批两记录）：

| 步骤 | 唯一结果 | 验收断言 / 停止点 |
| --- | --- | --- |
| 0 | 隔离Game World/Context及现有测试Host夹具 | 真实SpawnActor；仅补缺失公开注册/初始化；Actor和ASC有效、已注册/初始化、原宿主权威、Owner一致；实际列表恰两默认Health/Combat，类/Outer/默认子对象标志及不同指针严格检查。任何前置失败立即Fail并经RAII清理，不补造默认对象/权限 |
| 1 | 单个合法Independent Set新增 | 实际列表精确增加1，基础列表指针不变；新增类/Outer/唯一对象正确；本批Handles恰1且指向新增对象，不含基础存储 |
| 2 | 同一资产再次Give拒绝已有同类 | 第二次使用独立Handles；完整实际列表不变，第一批记录保留，第二批0；使用调用前已知对象的完整字面拒绝日志，Exact/非正则/次数1 |
| 3 | 另一资产Give拒绝已有同类 | 不同资产指针；列表不变，前批新增/记录不变，后一批0；同样精确日志及独立状态断言 |
| 4 | Health/Combat基础存储重复分别拒绝 | 两个独立调用均无新增，基础指针不变，各批Handles0；分别匹配完整已知基础对象日志，每条恰1 |
| 5 | 三文件审查及冻结交回 | 记录实际diff/hash、API/边界/清理审查、注册名与未运行状态；共享头/生产/M1保持；静态冻结后不继续写，由统筹统一构建/实测 |

步骤依赖：预检登记→0→1→2→3→4→源码实际读回与静态审查→5。各案例使用独立World，资产强引用与两批句柄由夹具持有至teardown，观察快照仅在World存活期间使用。夹具先对有效权威ASC调用公开Take释放已授句柄，再DestroyWorld，最后移除WorldContext；Context在World销毁期间保持有效。任何中途失败均沿同一RAII清理路径。Take这里只是资源清理，不作回收/重复Take/GC专项通过证据。

非目标：T2c1回收/部分成功、T2c2构造后Outer/Owner变化、T2c3非Authority/真实客户端、GA/GE业务、新类型/接口/可见性、默认对象或权限伪造、BeginPlay/网络/GC、其它文件/图文/资产/配置/夹具；不UE/UHT/构建/自动化执行/Git/代理。若行为不满足期望，保留严格失败，不能同时改生产或放宽断言。

当前结果：先登记后依次完成0–4，新增Editor自动化`GGYGO.AbilitySystem.AbilitySet.AttributeRuntimeAdmissionAndNewHandles`，四个独立World案例族，基础冲突含两个调用。以实际列表差集确定新增对象，再独立核对完整有序列表、实际类/Outer、公开查询与Handles精确计数/指针；同资产再次Give和跨资产重复各使用独立第二批记录。四条已知拒绝日志在Give前完整Exact匹配且各次数1、非正则，不遮盖断言失败。Take仅夹具析构清理，未断言回收。

测试cpp从113行增至381行；源码差异仅新增268行、0删除，新增4个include、文件内无反射夹具/观察断言/日志期望及一个独立运行准入测试。T2a注册/函数及11案例、两个原诊断helper经换行归一全文比较保持。15项静态范围/保留/夹具/断言/日志/清理检查全部true，13个共享头/生产/M1只读文件SHA256均保持。完整源码/API/提前返回和析构路径审查完成，cpp SHA256=`F79D6323B8411F2ABD3D7BDE54184B34B1A77AD3F76F68E96AB473AAEAEE0ACA`。三文件静态冻结交回；第17次在T2b新增前，只证明既有T2-0/T2a，本步尚未编译/运行，不进入T2c或图文同步。

## 15-M1-Evidence（局部静态冻结结果；保留写图文前拆分预检）

统筹已接受T2b根审查及第19次真实结果，授权本System组长直接执行证据同步。精确范围：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/System/结构.md`、`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/System/GGYGO_结构_System.canvas`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_AtomicSteps.md`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_Validation.md`。唯一目标修正T2-0/T2a尚未UHT/编译/运行、T2b未运行的旧当前状态；不改变生产架构或接口。

冻结只读依赖：全部225个Source文件（含System四头/cpp、属性测试cpp/共享头）、第17/18/19次完整构建日志及17/19常规报告JSON、路由/台账/当前排程、计划蓝图/模块参考/实施状态及已有相邻结构链接、项目`.kiro/skills/obsidian-canvas-diagram/SKILL.md`。已实际读回报告与对应测试源码：11个ValidateCase调用、四次独立Fixture初始化及完整断言；两测试叶均Success不表示所有属性或生命周期场景通过。

| 原子步 | 唯一结果 / 精确文件 | 验收断言 / 停止点 |
| --- | --- | --- |
| E0 | 前置证据冻结 / 本批两记录登记 | 17成功49/49、18真实完整失败、19成功51/51；两叶状态/计数/空entries/警告错误与源码案例对应。信息不符先停，不推断未运行专项 |
| E1 | System结构MD验证状态修正 / `System/结构.md` | 只改验证段与证据引用；T2-0已UHT/编译，11编辑及四World族实际通过，Take仅清理；明确全部未验边界；前文TryGet/预载/五状态/GE选择与消费接口全文保持 |
| E2 | Canvas当前验证文字 / `System/GGYGO_结构_System.canvas` | 只改contract节点末两行；原8节点/6边ID、边标签、所有位置尺寸/颜色及其它正文完全保持；若容量不足停止说明，不自行调整布局 |
| E3 | 四文件QA与冻结 / 本批两记录 | 实际读回JSON/唯一ID/端点/标签/无重叠/链接/容量、局部文字差异及225源码hash；记录结果并交回四文件hash。容量为静态估算，未作Obsidian屏幕渲染；冻结后停写 |

依赖顺序：E0登记与证据读回→E1→E2→四文件实际差异/图文一致性/JSON及源码范围检查→E3。共同非目标：任何源码/测试、配置/资产/其它Obsidian/全局文件、TryGet/一次预载/五状态/GE选择接口、UE/UHT/构建/自动化执行/Git/代理；共享预载逐项失败/GC/覆盖选择、生产蓝图开关、Cook、Take回收/部分失败继续授予/构造重入/非Authority/真实client均未由51/51证明，T2c/T1/T3/M2不自动开工。

当前结果：E0先登记后完成E1/E2，MD只更新验证段/证据引用，接口及原配置/Cook文字前缀全文保持；Canvas仅contract末两行改变，未增删节点/边/链接，8节点/6边的全部ID、标签、位置/尺寸/颜色及其它正文保持。14项图文/保留/边界检查true；17处wikilink、10个唯一目标均存在且唯一解析，所有节点矩形无重叠，静态文字容量有余量；contract保守估算202px/290px余88px，无需调整尺寸。未作Obsidian屏幕渲染。

全量Source哈希保持检查未通过，不能列为全部QA通过：225个路径/数量保持，快照中224个哈希保持（含全部220个.h/.cpp及System/属性测试）；`Source/GGYGO/GGYGO.Build.cs`由`FD4A48A575CEF3B1E9DFE6E12411AC9654F5C1C781D2332928F5C4BCE7F9BC61`变为`677F99C4CB6EE8FA3EB9B55A2A95AE12766E72B69C7CE474D5F7F914EE0E1A06`，LastWriteTimeUtc=2026-09-30T06:29:21.0262441Z。本会话未写源码/Build.cs，不推断变化来源或新构建已覆盖该变化；需统筹单独核对。T2b cpp/共享头仍为F79D6323…/8C3FF93C…，第19次历史有限验证结论保持。

四文档局部证据同步/读回/实际差异审查完成并冻结交回，停止写入；全量源码保持异常随证据一并交回，不回滚或扩写该源文件。未UE/UHT/构建/自动化执行/Git/代理，未改源码/测试、配置/资产、其它Obsidian或全局入口；T2c/T1/T3/M2未进入。

## 15-T2c1（本轮静态冻结结果；保留写测试前预检）

统筹根审查接受只读预检，第20次常规UE已退出后正式授权。唯一写入者仍为System长期组长，直接执行，无代理。精确范围：`F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGOAbilitySetAttributeSafetyTest.cpp`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_AtomicSteps.md`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_Validation.md`。唯一目标：属性Take只注销本批新增对象并清空本批属性Handles，重复Take不影响宿主基础或其它批次；不验证GA/GE句柄或GC销毁。

已保存三文件实际全文及只读依赖基线，保留原未提交改动。测试cpp基线SHA256=`F79D6323B8411F2ABD3D7BDE54184B34B1A77AD3F76F68E96AB473AAEAEE0ACA`，共享头=`8C3FF93CF84D8A11E92A3AEEDA0DC69D93D6C5158B0A3F41C58B87806C10FC07`。精确只读：该共享头；生产AbilitySet.h/.cpp、ASC.h/.cpp、CombatantState.h/.cpp、HealthSet.h/.cpp、CombatSet.h/.cpp；System结构MD/Canvas。还只读UE公开World/Actor/ASC/StrongObjectPtr API及路由/当前排程/第20次报告。

| 原子阶段 | 唯一结果 / 精确文件 | 验收断言 / 停止点 |
| --- | --- | --- |
| C0 | 冻结契约与基线 / 本批两记录 | 第20次成功51/51；T2a11例、T2b四World族、所有既有helper/夹具及注册全文保持；仅新增一个普通Editor测试 |
| C1 | 属性Take归属的唯一测试契约 / 仅测试cpp追加RunTest | 复用原Fixture及独立A/B、两资产/两批记录：Give A→Give B→Take A批→重复Take A批→Take B批；每阶段实际全列表/准确类/指针/原Host Outer/public lookup/两批属性Handles严格核对。B新增来自实时列表相对Give A后快照差集，不误用仅第一批的CheckSingleRuntimeGrant |
| C2 | 静态审查与冻结交回 / 本批两记录 | 读回新增diff、旧全文保持、API/强引用析构顺序及所有早退/独立只读hash；交回注册名/三文件hash/未编译未运行状态，立即冻结停止，由统筹门禁 |

顺序：C0登记→C1→完整新增读回及只读API/范围/生命周期审查→C2。原Fixture严格真实Game World/Context、注册Host/default ASC、Authority/Owner及Health/Combat恰两默认存储前置继续生效。关键操作前、后读状态前均验证Host/ASC仍有效未销毁、登记/初始化、原Owner/Authority；不符Test失败并return false，不静默跳过或补造状态。

测试局部A/B强引用先于Fixture声明，使Fixture先析构，引用最后释放；对象来源为公开SpawnedAttributes实际对象，不从Handles倒推、不const_cast/反射/新注册制造。Give A后列表基础+A、第一批1第二批0；Give B后基础+A+B、两批各1。Take第一批后基础+B、A公开查询空、第一批0、第二批仍B；再次Take完全不变；Take第二批后恰原基础两对象、两批0且A/B查询空。基础Health/Combat与存活B的准确指针、类、Outer/default标志和公开查询均保持。

所有早退沿原Fixture析构Take第二批→第一批→DestroyWorld→销毁Context，测试观察强引用在此之后释放；注销不等于对象GC。本新测试不使用ExpectedError掩盖失败，不改旧Fixture析构或其它helper。现有类型/配置/只读Handles视图及公开Take/GetSpawnedAttributes/GetAttributeSet已足够，无缺失生产注入接缝；现视图仅观测属性句柄，GA/GE句柄回收另步。

非目标：T2c1b部分失败继续Give、构造/Outer重入/Owner换代、非Authority/client、GC/共享预载/GE选择、其它源码/测试/文档/资产/配置/全局，UE/UHT/构建/自动化执行/Git/代理。未运行前不提升Take验证状态；不改生产或断言让测试绿。

当前结果：C0先登记基线后完成C1，新增一个普通Editor叶`GGYGO.AbilitySystem.AbilitySet.AttributeTakeOwnershipAndRepeatedTake`；cpp仅在原末尾endif前追加120行、0删除（381→501行），原T2a11例、T2b四World族及全部既有helper/夹具/注册内容经换行归一全文比较保持。六状态核对：基础→Give A→Give B→Take第一批→重复Take第一批→Take第二批；两次Give/三次Take均在真实权限/原Owner前置下执行。B身份来自实时列表差集，A保活指针从公开列表匹配既有观察身份，均不从Handles倒推。

初次16项静态检查全true，当时13个只读依赖hash保持；最终复核发现HealthSet.h/.cpp已进入排程授权13E8-P1同步RepNotify阶段修复，明确保留初值/公开接口，与T2c1互斥且无未冻结接口依赖。已读回当前构造初始化/接口并确认本测试不触发RepNotify、GE或数值写入。最终范围核对按当前有效租约：11个仍冻结的共享头/生产/冻结M1图文hash保持，两个HealthSet文件只读归属该线，不能再写成全部13文件当前hash不变；GF其它租约文件同样不要求保持。按该范围重核16项检查全true，本会话实际仍仅写三租约文件。

已完整读回新RunTest、核对公开API/准确指针与类/Outer/默认标志/四查询、两批记录、先强引用后Fixture的反向析构顺序及全部严格失败早退。cpp SHA256=`EFAD6815D87544FE7E675CBE791D8A5803360EB415B0B02123B58A85622F37C3`，共享头仍8C3FF93C…；三文件静态冻结交回立即停止。第20次在新增前，不覆盖T2c1编译/运行；原Take仅teardown的动态验证边界仍保持，C2只完成静态审查，不进入其它专项。

## 15-T2c1b（历史静态冻结；第22次后续结果见末节）

统筹根审查接受只读预检，并在当前Ledger/Parallel Schedule H4登记新租约。唯一写入者为System长期组长，按本轮gpt-6.1-sol / xhigh直接执行，无代理/临时会话。精确三文件：`F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGOAbilitySetAttributeSafetyTest.cpp`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_AtomicSteps.md`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_Validation.md`。不继承历史其它权限，保留所有现有未提交内容。

唯一结果：同一资产配置[IndependentA,已有基础Health同类冲突,IndependentB]，一次真实Give的索引1拒绝后仍授予B；本批只记录新增A/B，Take只注销它们并保留原基础两对象。候选唯一普通Editor叶`GGYGO.AbilitySystem.AbilitySet.AttributePartialFailureContinuesAndNewHandles`。现有types/公开配置/两批只读Handles/Fixture足够，不需要新增类型、生产接缝或其它文件。

C0前已保存三文件实际全文：cpp 501行、SHA256=`EFAD6815D87544FE7E675CBE791D8A5803360EB415B0B02123B58A85622F37C3`；AtomicSteps=`0856D35A40F08D39D0253FCEFF8FC0B29D760B34B6B872344B3087594C2F82DD`；Validation=`4F37A712BFCF972E5DEC574F38143E53F443D134E601F439A5CC4946942D2AD6`。共享types仍`8C3FF93CF84D8A11E92A3AEEDA0DC69D93D6C5158B0A3F41C58B87806C10FC07`，旧三个注册/测试与全部helper/Fixture须全文保持。

只读依赖：共享types；生产AbilitySet/ASC/CombatantState/HealthSet/CombatSet各h/cpp；冻结System结构MD/Canvas；UE公开Give/Take/列表/查询/StrongObjectPtr与AutomationTest API。已保存上述13依赖当前hash，HealthSet采用已授权P1后冻结版本（cpp `4B9C054735166B161FEBB6376FE652411B2DF851C1DE1CC927464D3D42C1F78C`），不要求回退到P1之前，不审计其它合法互斥工作线。Fixture拥有隔离World/资产/句柄，ASC仍唯一登记权威，测试仅作有期限观察，Take仍唯一注销入口。

| 原子步骤 | 唯一结果 / 精确文件 | 非目标 / 断言 / 停止点 |
| --- | --- | --- |
| C0 | 契约/前置/基线登记 / 仅本批AtomicSteps、Validation | 不实现测试；第21次三旧叶实际Success、源码基线及公开接口可复用。登记后进入C1 |
| C1 | 独立混合Give新增归属测试 / 仅既有测试cpp追加一个注册和RunTest | 旧501行全文保持，不改helper/types/生产；严格核对三状态与唯一索引1预期日志。需新类型/接口/文件立即停止交回 |
| C2 | 静态diff/API/RAII/范围证据与冻结 / 仅本批AtomicSteps、Validation，cpp只读 | 交回追加块位置、旧全文恢复证据、注册名、三文件SHA及未编译/运行状态；三文件冻结后立即停止，统筹统一门禁 |

依赖顺序：根审查/本轮租约→C0→C1→源码静态冻结→C2→统筹构建/实测。初始真实Game World/原Host/default ASC登记初始化、原组件Owner/ActorInfo Owner/Authority、恰两基础Health/Combat继续严格前置；Give/Take前及状态读取前确认上下文，不符Test失败且return false。

精确断言：初始完整原基础列表、A/B查询空、两批0；Give后实际列表相对基础差集恰两个有效对象，按实际顺序识别A/B并核对exact class/不同指针/原Host Outer/非DefaultSubobject，不从Handles猜身份。完整有序列表必须基础+A+B，四公开查询准确，基础对象身份/类/Outer/默认标志保持；FirstHandles恰[A,B]、SecondHandles0。Take本批后恰恢复原基础列表、A/B查询空、两批0，不借用或注销已有Health。

日志仅索引1完整同类冲突文字一条，动态包含当前资产名、原Health对象名与类，用`AddExpectedMessage(Message, ELogVerbosity::Error, EAutomationExpectedMessageFlags::Exact, 1, false)`；索引0旧helper不改且不用于本测试。原生API已核对Exact非正则要求完整字符串/长度匹配，正次数要求准确一次；缺失/多次失败，不清除其它错误/ExpectedMessages，不宽松Contains/Regex或降级断言。

A/B强引用先于Fixture声明，从公开实际列表非const元素保活；快照/lambda后声明先销毁，Fixture沿原Take第二批→第一批→World→Context清理后最后释放强引用。所有错误严格早退沿原RAII，无反射/const_cast/新注册/Owner或权限补造。非目标：null/abstract拒绝分支、重复Take旧契约、GC、GA/GE资源、构造/Owner/Outer变化、非Authority/client、OnRep/数值/GE/共享预载/选择、其它测试/图文/资产/配置/全局，UE/MCP/构建/Git/代理。C0先登记，随后C1已实施、源码冻结，C2静态证据见下；新叶尚未编译/运行，不提升动态验证状态。

### T2c1b实际结果与冻结交回

cpp仅在原末尾endif前追加112行、0删除（501→613行），追加区间501–612，注册macro第502行、RunTest第506行，原endif移至613。实际唯一普通Editor叶`GGYGO.AbilitySystem.AbilitySet.AttributePartialFailureContinuesAndNewHandles`；无新类型/include/生产接口。第21次实际运行的是旧三叶，本新增不在其中。

在内存移除且仅移除本追加块后，UTF-8字节SHA256精确恢复原`EFAD6815D87544FE7E675CBE791D8A5803360EB415B0B02123B58A85622F37C3`（无磁盘回滚/写入）；原501行的三个测试、全部helper/Fixture/注册及编译保护内容逐字节保持，含索引0Expected helper。完整新RunTest读回/API/指针来源/所有早退及强引用析构审查完成，17项静态检查全true，13冻结依赖当前hash全部保持；未要求其它互斥合法租约文件保持。

一次FirstAsset配置[A,Health,B]→一次Give→实际列表差集恰两个有效不同对象→三个状态核对→一次FirstHandles Take，SecondHandles一直空。唯一索引1完整Error/Exact/1/false消息，包含真实资产/原Health身份；没有其它错误清除/放宽。完整列表、四公开查询、两批记录及每个存活对象exact class/指针/Host Outer/DefaultSubobject严格核对，A/B身份由实时列表先取得后独立验证Handles。强引用先于Fixture，所有失败沿原RAII，注销不是GC证明。

cpp SHA256=`8B6D97561FAF922C75BF961893C3A0AD339C6DFDCB94EA8F21FE6208C19615FD`；源码已冻结后仅补两记录，本会话实际只写本轮三文件。三文件完成读回/范围/架构与静态审查后冻结，立即交回统筹构建/实测；本会话未UE/MCP/UHT/构建/自动化执行/Git/代理，不继续其它步骤。测试不新增权威状态/执行链/依赖，局部快照与引用仅本Fixture寿命；System MD/Canvas仍被冻结，本轮证据仅记两记录，后续图文同步须独立租约。GC/GA-GE/构造/Owner/非权威/client/OnRep等边界保持未验。

## 15-M2-Evidence（静态冻结；保留写图文前四文件预检）

System长期组长按gpt-6.1-sol / xhigh直接执行，无代理。仅四文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/System/结构.md`、`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/System/GGYGO_结构_System.canvas`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_AtomicSteps.md`、`F:/ue_project/GGYGO/AAADocs/Modules/System/Module_Repair_15_Validation.md`。唯一目标同步已冻结普通Take/repeatedTake21及中间Health冲突继续B/只记录注销新增22的真实有限证据，清除局部当前未验误述，保留历史日志与交回时未验状态。

写前保存四文件全文及SHA256：System MD=`718B2CB4FFFAEB6A037371FD5726A1847E812C80B1EE065A5CEBAB9F6D1A2034`；Canvas=`81E8E983E1F5D07E938C2D43D52D0439C602DD9EA7EFAC8AF84BA1E8F5ADB58C`；AtomicSteps=`01CBF07AFAA927E082C2A2E1628072F2CA6F783C6217281A5A6592F6F6FD839A`；Validation=`76832C6313BF7A36EC05699C2BD359955D70EB7FD50AF8E817970686F7A4FBF2`。保护12源码当前hash（types、AbilitySet/ASC/CombatantState/HealthSet/CombatSet各h/cpp及测试cpp），测试cpp仍`8B6D97561FAF922C75BF961893C3A0AD339C6DFDCB94EA8F21FE6208C19615FD`，不写源码或其它线。

已读项目Canvas skill、计划蓝图定位System仅结构MD/Canvas，模块参考及相邻AbilitySystem/GameFeature结构/计划；核对冻结测试与21/22日志报告。图当前8节点/6边、全部text类型，contract在(0,1240)，1630×290，既有MD+图17链接出现/10目标均唯一可解析。无新增类/接口/依赖与导航需求，不新增节点/边/链接。

| 原子阶段 | 唯一结果 / 精确文件 | 非目标 / 验收 / 停止点 |
| --- | --- | --- |
| E0 | 实读证据/四文件基线/预检登记 / 仅本批AtomicSteps、Validation | 区分21普通Take与22部分失败；新叶真实Success/空entries/零错误警告对应冻结源码。数据不符停止 |
| E1 | 当前有限验证状态 / 仅System结构MD | 只更新验证末段与证据引用；生产职责/类/接口/配置前三条保持，保留17/18/19历史，不把GC等升格 |
| E2 | 精简验证边界 / 仅System结构Canvas | 只替换contract末两行，可重分行；前四行、其它7节点/6边/ID/label/矩形/颜色保持。容量不足先精简详情入MD，不重排 |
| E3 | JSON/ID/端点/标签/矩形/容量/links及回读 / 仅本批AtomicSteps、Validation，图文只读 | 记录真实diff/hash与未做UI渲染边界；源码保护hash保持，四文件冻结后立即交回，不接新专项 |

顺序E0→E1→E2→E3，图文不与源码实现混写。非目标：生产职责/接口/资产配置、构造/OwnerOuter重入、非Authority/client、GC销毁/GA-GE资源、共享预载逐项失败/覆盖选择、生产蓝图值与Cook；不UE/MCP/构建/Git/代理。global统筹独占，模块参考及计划_实施状态当前部分失败未验文字需由统筹依据22同步，不抢写。E0先登记，随后E1/E2完成，E3结果见下；四文件冻结停止。

### M2-Evidence实际结果与冻结

按E0→E1→E2→E3直接完成。System MD只更新验证末段及证据引用（64→67行，+7/-4）；职责/类/接口/预载/五状态/显式选择/消费者及配置前三条原前缀逐字保持。普通Take/repeatedTake21与部分失败固定中间Health冲突继续B/只记录注销新A/B22已有限实证，17/18/19历史保留；未把注销或55项目叶解释为GC/GA-GE/其它生命周期或预载选择/Cook通过。

Canvas仅替换contract一行JSON正文值（134行保持，+1/-1）；其前四逻辑行及其它7节点、全部6边/标签、ID/type/坐标/宽高/颜色保持，无新增节点/边/链接。静态文字按标题22/body16px、行32/24px、横留白48/竖留白32px估算208/290px，余82px；矩形无重叠，不冒称Obsidian屏幕渲染验收。

16项静态检查全部true：JSON；8节点/6边；全局ID唯一；端点有效；非空准确标签/边不变；仅contract文本变化；矩形不重叠；contract前四行保持；静态容量；17链接出现顺序保持；MD生产/接口/配置前缀保持；MD末段准确读回；GC等未验边界；17/18/19历史保持；无行尾空白；12保护源码hash保持。10唯一链接目标实际存在，新增链接0；测试cpp仍8B6D9756…，本会话实际只写四授权文档。

System MD SHA256=`B70C8CBEF7482CD9AC0992240E53B897D2F420246C015372BAAD968E6E06B6BC`；Canvas=`297FEE349E83B7EDE2407C5B6F8AA6755743B7E6397C11197233457EA8B07DDD`。四文件读回/diff/源码事实/JSON/布局/links及范围核对后冻结立即交回，不运行UE/MCP/构建/Git/代理或自动接新专项；其它图文/全局入口保持本会话只读。模块参考/计划_实施状态旧部分失败未验描述已登记统筹独占同步，不能据此扩本租约。
