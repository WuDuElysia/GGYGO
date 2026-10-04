# 第 07 批 Input 文件子租约

更新：2026-10-01。07E1第17次真实身份诊断为1 Fail/2 Error/0 Warning，旧请求污染已复现，严格断言与生产继续冻结。07E2-V已按统筹三文件租约完成普通值类型头及两记录，静态核对完成并交回冻结；预检先登记，组长直接执行，无代理。类型声明不代表身份隔离或用户两条行为已修复。

## 已批准接口契约

- Hero 持有本地输入会话资源；所有 Native / Ability 绑定必须交回句柄，后续由记录的原 InputComponent 幂等释放。
- ASC 唯一持有 pressed / held / released 物理输入事实。独立 retry 请求只能排入现有 `ProcessAbilityInput`，不得写 held、`Spec.InputPressed` 或向活跃能力发送输入事件。
- retry 保留原物理请求的绝对截止时间；自动失败不得延长期限。`OnInputTriggered` 可在松键后于窗口内重试，`WhileInputActive` 必须仍有真实 held。
- PlayerController 继续是唯一帧末输入消费驱动，不新增 Tick、第二帧调度器或直接激活旁路。
- Hero 复用现有 `HandleAbilitySystemUninitialized` 作为唯一 PawnExtension 解绑协调入口；不得注册第二条 uninitialized 清理通道。
- 当前生产输入接口、07E0-R1夹具和07E1诊断全部冻结；仅下面的07E2-V三文件值类型租约有效，不扩生产接口、阻断矩阵、资产迁移或Obsidian。ASC组件h/cpp不在本步租约内；当前互斥源码线为Movement C22测试适配。

## 当前已授权原子任务

| 子任务 | 唯一写入者 | 精确可写文件 | 唯一结果 | 非目标 | 只读依赖 | 验收断言 | 停止点 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 07A InputComponent 句柄接口 | Input 长期组长 | `Source/GGYGO/Input/GGYGOInputComponent.h` | Native 与 Ability 绑定均可把成功创建的句柄交回调用方 | Hero 生命周期、IMC、ASC、测试、文档、资产 | InputConfig、Enhanced Input API、Hero 当前调用只读 | 成功绑定才追加有效句柄；可选缺失动作不产生伪句柄；既有 `RemoveBinds` 幂等语义不变 | 头文件实现与静态自查完成后冻结；若确需 `.cpp` 必须停止并申请扩租 | 已获统筹静态冻结认可；保持只读 |
| 07B ASC 独立 retry 接口 | Input 长期组长 | `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h`、`.cpp` | retry 携带 OriginalDeadline 进入现有帧末处理且不伪造物理输入 | Hero、PlayerCombo、GA 基类、PlayerController、PawnExtension、测试、文档、资产 | ActivationPolicy、04 已冻结的组准入/结束重入、PlayerController 只读 | retry 不写 pressed/held/released 或 `Spec.InputPressed`；活跃能力不收 retry 输入事件；OnInputTriggered 支持未过期请求；WhileInputActive 仍需真实 held；再失败保留原截止时间；Clear/阻断清 retry；同帧 Tag 去重 | 两文件实现与静态自查完成后冻结 | 已获统筹静态冻结认可；第14构建已覆盖，Input 专项未运行 |
| 07C Hero 输入会话 | Input 长期组长 | `Source/GGYGO/Character/Components/GGYGOHeroComponent.h`、`.cpp` | 记录原输入资源并通过公开 ReleasePlayerInput 幂等归还自己的句柄和 IMC 注册 | D retry 委托/截止适配、ASC/InputComponent、PawnExtension/PC/Teams、测试、资产、Obsidian | A 句柄输出、05 唯一解绑协调器、UE5.8 EnhancedInput CountRegistrations/HasMappingContext API | 重复初始化先释放原会话；关键配置/类型和全部 IMC 前置校验；Native/Ability/ForceWalk 全部收句柄；没有 ClearAllMappings/共享资产写入；同优先级 IMC 必须自己 Add 一次；冲突不覆盖；ForceWalk 恢复；唯一协调入口调用 Release | 两文件静态审查及记录完成后冻结，不构建、不进入 D | 已获统筹静态冻结认可；D 扩展其既定会话接缝 |
| 07D ASC 订阅与截止适配 | Input 长期组长 | `Source/GGYGO/Character/Components/GGYGOHeroComponent.h`、`.cpp`；本批两个记录 | 跟随有效本地会话管理原 ASC 委托和有限 retry 缓冲，消除双参数接口不兼容 | 不改 A/B/PawnExtension/PC/Teams/测试/资产/Obsidian，不构建、不派代理 | PawnExtension RegisterAndCall/唯一现有解绑入口、A/C 绑定会话、B 双参数失败与 QueueAbilityInputRetry/ClearAbilityInput | 弱原 ASC+委托句柄；晚就绪可订阅；先摘除再清理且保护新 Avatar/后继会话；首次真实 Triggered 起算、持续 Triggered/held 失败不续期；无来源哨兵不新建窗口；释放后 OnInputTriggered 原窗可重试；GroupFreed 只 Queue；同 Tag 去重 | 实际 diff/静态审查及四文件记录完成即冻结；接口不足交回，不进入 E/F/G | 已获统筹静态冻结认可；第14构建已覆盖，Input 专项未运行 |

### 07E2-V 共享输入请求值类型原子预检与租约（2026-10-01 当前授权）

| 项目 | 精确约束 |
| --- | --- |
| 唯一写入者/精确文件 | Input长期组长；新增`F:\ue_project\GGYGO\Source\GGYGO\AbilitySystem\GGYGOAbilityInputRequestTypes.h`、`F:\ue_project\GGYGO\AAADocs\Modules\Input\Module_Repair_07_Subleases.md`、`F:\ue_project\GGYGO\AAADocs\Modules\Input\Module_Repair_07_Validation.md`；仅三文件，由统筹ledger/schedule登记 |
| 模块/归属 | AbilitySystem定义共享输入请求数据，ASC是未来身份分配及真实来源的唯一权威；Hero只持身份副本、来源窗口和原deadline。本步不创建任何运行状态 |
| 唯一结果/先冻结字段 | 普通C++ `FGGYGOAbilityInputRequestIdentity { TWeakObjectPtr<UGGYGOAbilitySystemComponent> SourceASC; uint64 InputRevision=0; uint64 RequestSerial=0; }`；`FGGYGOAbilityInputRetryRequest { FGameplayTag InputTag; FGGYGOAbilityInputRequestIdentity Identity; double OriginalDeadline=-1.0; }` |
| 值操作契约 | Identity仅inline IsAssigned及==/!=；IsAssigned仅检查serial!=0，revision0合法且不证明运行有效。比较原弱引用本身的对象索引/序列号、revision、serial，不解析Get()，不能令两个失效来源因都返回null而相等。RetryRequest无运行校验或续期操作，默认-1无效，不得借近期同Tag截止 |
| 只读依赖 | ASC/Hero现有输入及清理接口、07E0-R1 Fixture、07E1诊断、Admission类型、UE5.8 CoreMinimal/GameplayTagContainer/WeakObjectPtrTemplates；统筹ledger/schedule与第17次原始报告 |
| 依赖/先后 | ASC只读审查与统筹字段冻结已完成→本预检登记→新header值类型→静态全文及完整范围核对→两记录收尾→三个最终hash冻结交回；真实TU接入/API迁移须另步授权，统一构建由统筹排队 |
| 非目标 | 无USTRUCT/UHT、发号器、运行容器、Tag/Spec集合、dispatcher、API签名或生产行为；不改ASC/Hero/PC/PawnExtension/诊断/Fixture/Admission/Build.cs、资产、Obsidian及全局记录 |
| 验收断言 | 只有两普通值类型和约定字段/值操作；ASC前置声明，CoreMinimal、GameplayTagContainer及WeakObjectPtrTemplates直接包含；serial0未分配、revision0合法；弱引用身份比较不依赖对象存活；无生产包含点、无行为修复或编译声称；范围仅上述三文件，保护基线保持 |
| 清理/架构 | 值副本不持有对象生命期、不持有委托/资源/容器，无独立执行或清理机制；运行失效、Clear/Avatar清理和事件聚合仍由后续ASC/Hero步骤审查，不在值类型中实现 |
| 停止点 | 需要其它文件、完整ASC类型、运行容器/校验/接口选择即停止交回；静态核对和三个hash完成后冻结，不构建、不操作UE/Git、不派代理 |
| 当前状态 | 预检先登记后完成50行header与两记录，三文件静态核对完成并冻结；新header唯一新增，221个原源码中排除独立C22后220个均保持，5个Obsidian文件/第17次报告保持；未接入真实TU、未编译或运行 |

- 最终值类型只有Identity的三个字段、IsAssigned及==/!=，RetryRequest的三个字段；没有USTRUCT/运行容器/有效性判定。比较使用原生`TWeakObjectPtr::HasSameIndexAndSerialNumber`：UE5.8弱指针普通==会令两个无效来源相等，此处直接比较原对象身份，再比较revision/serial，且不需要完整ASC类型。
- header SHA256：`8E795C5A85A546A8D489DE66D7F0B5A3C89B0A31F479ED286DE3F611D4134DAE`。全文、直接依赖、字段/操作和范围已核对，三文件尾随空白/冲突标记均0；两个记录最终hash在外部交回，避免将文件自身hash写入本文件。
- 范围证据：本步只有上述三文件apply_patch；源码清单从221到222，新增仅本header，原源码唯一同期变化是有独立租约的`Source/GGYGO/Character/Tests/GGYGOActionMotionTest.cpp`，不归本步。ASC/Hero/InputComponent/Fixture/Admission/诊断/Build.cs等其余220个源码逐文件hash保持；原第17次报告与5个Obsidian文件也保持。后续接口、动态门禁和图文同步仍单独授权。

- 用户两条已确认方向保留但未实现：无精确输入来源的Queued失败拒绝借ASC未就绪时已结束tap；同Spec多Tag held为OR，Generic Pressed仅首个来源、Released仅最后来源，须保留真实事件顺序。
- 下一阶段仅候选：PreviousIdentity续传防Clear后持续Triggered重新发号、首次真实接收的Spec集合固定、单Spec激活一次/失败来源数组在激活前冻结、晚授予不补造旧输入。精确签名、接收/消费/Hero/诊断适配及嵌套同Spec失败关联仍需分别预检授权；无法精确证明来源时拒绝关联，不自行兜底。

### 07E1 身份红诊断原子预检与租约（2026-09-30 历史冻结）

| 项目 | 精确约束 |
| --- | --- |
| 唯一写入者/文件 | Input长期组长；新增`Source/GGYGO/Input/Tests/GGYGOInputRetryIdentityDiagnostic.cpp`、`AAADocs/Modules/Input/Module_Repair_07_Subleases.md`、`AAADocs/Modules/Input/Module_Repair_07_Validation.md`，仅三文件，无代理 |
| 唯一结果 | 严格证明/否证在途旧retry Queued失败的Super公开回调内同Tag、同World time、同deadline的Completed→Triggered不能混入新物理请求 |
| 只读依赖 | 冻结07E0-R1真实Fixture；Admission QueuedTestAbility实例计数/FinishForTest、TestGroupConfig SetRuleForTest；ASC物理句柄快照/retry/NotifyAbilityFailed/GroupFreed及Hero来源/缓冲；原生GAS AbilityFailedCallbacks |
| 最小复用 | 一个新cpp，不新增头/UCLASS。同一既有Queued GA类的占位、原请求、后授予观察三个Spec各有真实独立PrimaryInstance；既有瞬态组配置设Attack→SingleInstanceQueued；不改既有测试类型 |
| 先后顺序 | 登记租约→核对冻结输入/仲裁契约→合法绑定控制探针→真实Queued失败/GroupFreed旧retry→再次占位→Super失败回调内真实release/press→回调返回后授予观察Spec→真实组释放/PC消费→严格观测→静态冻结；动态运行由统筹安排 |
| 验收断言 | 初始Queued原因/实例/组计数真实；同World time且有限未过期原deadline；回调一次、真实绑定各一次；合法新press原请求激活一次；后授予且未被新press命中的观察Spec失败次数/旧deadline通知均应为0，保持严格红；全部提前返回按序清理 |
| 枚举隔离 | `ProjectDiagnostics.Input.RetryIdentity.SameTimeReentrantPhysicalRequest`仅在`-GGYGOInputRetryIdentityDiagnostic`枚举；RunTest复核开关/案例；不ExpectedError，不混入普通GGYGO回归 |
| 清理责任 | 本cpp仅持有测试委托句柄、自己的Spec/瞬态配置及观测快照；先解除测试委托与Hero会话，再结束/移除自有能力，最后Fixture RAII Shutdown；不复制生产输入权威状态 |
| 非目标 | 阻断复现、生产修复/requestID方案、设备/BeginPlay/网络、资产/图文/全局记录；不Tick、不直接Queue、不读Hero私有缓冲、不放宽断言，不改Fixture/ASC/Hero/Admission类型/Build.cs |
| 停止点 | 原生前置或真实实例身份不成立、输入/仲裁只读契约变化、需扩大文件即停止交回；三文件静态审查后冻结交回diff/hash/命令/未动态验证状态；禁止UE/构建/Git写/代理 |
| 当前状态 | 已先登记精确三文件租约并静态冻结；统筹第17次完整构建和真实独立诊断已执行，1 Fail/2 Error/0 Warning，旧请求污染已复现，当前无继续写入租约 |

- 实际增量：新cpp共324行，只有一个complex注册，基础名`ProjectDiagnostics.Input.RetryIdentity`、子项及参数`SameTimeReentrantPhysicalRequest`；显式开关在枚举及RunTest双重校验。复用既有三Spec类型和组配置，没有新增头/UCLASS或改冻结Fixture/生产接口。
- 静态收尾：已读新源码全文；三文件尾随空白/冲突标记均0。原生GAS失败委托参数为const UGameplayAbility*，实现对应真实实例身份；时间及deadline用TestTrue的严格==，避免Automation浮点默认容差。ASC输入/仲裁15个函数块（含两个组查询重载）前后摘要一致；并行Montage入口的整文件变化不记为本步改动。
- 新cpp SHA256：`C7D77AD2EB2B4B1C361D682AC4A391CF1747ED71E34A286D734B158EC0DD500D`。真实Fixture h/cpp和Admission h/cpp哈希与接管时一致；详细哈希/严格断言/统筹运行命令见验证记录。以上为当时静态交接；第17次实际红诊断证据已补录，源码严格断言不变，本会话不运行UE/构建/Git/代理，不进入阻断或生产修复。

### 07E0-R1 来源修复预检（历史冻结）

| 项目 | 精确约束 |
| --- | --- |
| 唯一写入者/文件 | Input 长期组长；`Source/GGYGO/Input/Tests/GGYGOInputTestTypes.cpp`、本批 `Module_Repair_07_Subleases.md`、`Module_Repair_07_Validation.md`；header/生产源码冻结，无代理 |
| 唯一结果 | 修正自有World Actor初始化先于Controller创建/SetPlayer的原生生命周期，使EnhancedInput按World查询到真实PC及其PlayerInput |
| 只读依赖 | 本机UE5.8.1 UPlayer::GetPlayerController(World)、AActor::PostActorConstruction、AController::PostInitializeComponents/AddController、UWorld::InitializeActorsForPlay、PC SetPlayer/ReceivedPlayer、LocalPlayer ReceivedPlayerController、EnhancedInput PlayerControllerChanged/GetPlayerInput；第15次实际报告/日志 |
| 根因 | 自有World未执行InitializeActorsForPlay，Spawn未路由Actor PostInitializeComponents；Controller未进入World列表。SetPlayer虽已创建本PC PlayerInput，EnhancedInput的World过滤查询仍返回nullptr，真实ReceivedPlayerController通知遂产生user-settings警告 |
| 顺序 | 记录预检 → 只读检查原生InitializeActorsForPlay副作用/通知顺序 → 自有World原生Actor初始化 → Spawn PC/真实SetPlayer →严格来源门禁→静态审查记录冻结 |
| 验收断言 | 保留现有全部来源/清理/激活断言；新增World AreActorsInitialized、PC IsActorInitialized及LocalPlayer按World查询到本PC的前置，之后原Subsystem返回实际PC PlayerInput仍须相等；不吞警告 |
| 非目标 | 不改变Subsystem返回值/Hero私有有效性，不手工AddController补列表或广播initialized，不用SuperGI，不修改头/生产/其它测试/图文/资产；不构建、UE、Git写或代理 |
| 停止点 | 原生前置不能安全成立、或需要header/生产改动即停止交回；三文件静态审查后冻结，复跑由统筹安排，不进入身份/阻断矩阵 |
| 状态 | 第16次完整构建及真实来源/普通激活/释放/Shutdown单项Success，warnings/errors0；保持冻结 |

- R1实施：World原生InitializeActorsForPlay先于Viewport/LocalPlayer/Controller创建；Spawn后检查PC IsActorInitialized，SetPlayer后检查LocalPlayer的World过滤查询，再保留原Subsystem PlayerInput相等断言。未改AddLocalPlayer顺序：本机EnhancedInput LocalPlayer subsystem未覆盖Initialize，PlayerAdded仅创建真实collection；UserSettings加载由SetPlayer→ReceivedPlayerController→PlayerControllerChanged触发，此时PC已经原生登记且InitInputSystem已创建其PlayerInput。
- 原生副作用核对：Game型CreateWorld默认不创建Navigation/AI，空World没有GameMode/GameState，InitPlayerState没有额外PlayerState业务；PC原生PostInitializeComponents可创建CameraManager等自有World Actor，由既有DestroyWorld清理。InitializeActorsForPlay保留真实World初始化委托、组件/流送登记及可能的引擎Console自动补全刷新；未手工广播、改全局CVar/Settings或屏蔽警告。第16次已验证本单项来源/普通激活/释放/Shutdown，未由此推导设备/BeginPlay/网络或全部外部副作用。
- cpp R1冻结SHA256：`CF89CE4DD8E970DB255899E6750BD161DD3D3EAA5FFCBDFA0A1E11C83FA04878`；header及A/B/D五个生产文件与原冻结值相同。仅注册原单项，身份/阻断矩阵未开启。

### 07E0 初始夹具预检与历史冻结

| 项目 | 精确约束 |
| --- | --- |
| 唯一写入者 | Input 长期组长；无子代理 |
| 精确可写文件 | `Source/GGYGO/Input/Tests/GGYGOInputTestTypes.h`、`Source/GGYGO/Input/Tests/GGYGOInputTestTypes.cpp`（新增）；`AAADocs/Modules/Input/Module_Repair_07_Subleases.md`、`AAADocs/Modules/Input/Module_Repair_07_Validation.md`（本批记录） |
| 唯一结果 | 自有临时 World/GameInstance/Viewport/LocalPlayer、真实 EnhancedInput 子系统/PlayerInput、Controller/Pawn/PawnExtension/Hero 会话及成对 RAII 清理；仅注册 `GGYGO.Input.Fixture.LocalSessionReady` |
| 共享接口与状态归属 | A/B/C/D 全部只读冻结；引擎持有本地输入及注册状态，Hero 持有会话资源，ASC 持有物理输入，PC 保留唯一生产消费入口。夹具仅拥有对象生命周期和只读访问器，不复制私有会话有效性或输入状态 |
| 只读依赖 | UE5.8 GameInstance/World/Viewport/LocalPlayer/PlayerController 公共生命周期、EnhancedInput 绑定 Clone/Execute 与 CountRegistrations；项目 InputConfig/PawnData、PawnExtension 真实 initialized 入口、Hero Initialize/Release、PC PostProcessInput、GAS 普通输入激活 |
| 顺序 | 本记录登记 → 私有上下文与 RAII → 最小瞬态配置、Controller/Pawn/探针 GA → 真实 PawnExtension InitializeAbilitySystem 与 Hero InitializePlayerInput → 输入来源及清理断言 → 静态审查及记录冻结；初始 BeginPlay 设想经隔离核对收敛为本步所需的公开最小来源链，BeginPlay/InitState 不在此门禁 |
| 验收断言 | 每个来源属于夹具自身上下文；Pawn 本地受控，子系统回读实际 PlayerInput；项目真实 ASC 接入后 Hero 实际持有两个订阅；一条实际 Ability 绑定经过真实 PC 消费到达探针 GA；Release/解绑后无夹具绑定、IMC、Hero ASC 订阅，最终移除自己的 LocalPlayer/上下文 |
| 最小扩展点 | 测试 GI 的公开 Init/Shutdown 只管理自身上下文和 LocalPlayers，不启动通用 GI 服务或安装/清空全局网络委托；Viewport 运行原生 Init，但公开 PlayerAdded/Removed 通知不操作窗口焦点/布局；Controller 显式创建自有 EnhancedPlayerInput/InputComponent并包装真实 PostProcessInput；Hero 只配置自身 IMC；瞬态 IMC 构造设 protected TrackingMode；单个无组探针 GA 计数只随实例存在；真实绑定 Clone/Execute 仅持有调用内快照 |
| 非目标 | request identity、block、retry、deadline、held、订阅重入和资源矩阵；不写生产源码/既有夹具/Build.cs/资产/Obsidian/全局台账，不操作 UE、构建、Git 写或代理 |
| 停止点 | 任一真实前置不成立即记录并交回，不绕过私有有效性、不手工广播 initialized、不扩文件范围。源码/记录静态审查后冻结，由统筹统一 UHT/构建/运行 |
| 当前状态 | 初始四文件静态冻结；第15构建通过、单项来源前置Fail，后续仅按上方R1三文件范围修复；不进入身份/阻断步骤 |

- 隔离核对结果：原生 GI Init 会安装三个全局网络委托，Shutdown 会无条件 Unbind 其中两个；本步完全避开这些通用服务，故没有旧绑定恢复代码，也不会覆盖同步回调中的外部后继绑定。未初始化的 GI subsystem collection 没有清理票据；Timer/Latent managers 按 UObject 自身生命周期释放。
- LocalPlayer 的 PlayerAdded/PlayerRemoved 仍通过真实 GI AddLocalPlayer/RemoveLocalPlayer 成对执行，EnhancedInput 子系统由引擎初始化/反初始化；Engine 的用户/Controller ID 交换只遍历该 LocalPlayer 所在 GI，本实例只有一个自有 LocalPlayer。Viewport 的空通知仅跳过与来源无关的 UI 焦点/布局，不替代 PlayerAdded。
- Viewport 原生 Init 在本机 UE5.8 即使传 false 也可能申请音频句柄；退出先释放 Hero/ASC，再移除自有 LocalPlayer/Controller，销毁自有 World 与 Context（由引擎清外部 World 引用），最后 Detach/ConditionalBeginDestroy 归还 Viewport 音频。全局 GWorld/GameViewport 不赋值，测试保留读回断言。
- 仅验证公开初始化形成的输入会话，未调用 BeginPlay、启动 GI InitState 协调服务或验证 RegisterAndCall 晚就绪；相关夹具扩展须后续单独授权，不能以本步替代生命周期专项。

### 07D 实施预检

- 归属：Hero 仅持有会话订阅句柄、请求来源截止及待重试意图；ASC 唯一持有 pressed/held/released 并执行策略判定，PC 唯一消费帧调度；CMC/Camera 保持前批权威。
- 顺序：已冻结 A/B/C → Hero 订阅与释放接缝 → 物理来源/双参数缓冲 → Queue 交接 → 静态审查/记录冻结。唯一写入者为组长，四文件范围互斥，无子代理。
- 原 ASC 弱引用与两个 FDelegateHandle 替代 bool；BeginPlay 注册 initialized RegisterAndCall，uninitialized 继续只用既有协调器。有效本地输入来源/当前 PawnExtension ASC/Avatar/会话代次均匹配才订阅或处理回调；初始化晚于输入时无需 Tick 轮询。
- Release 在 C 记录摘除后、其它有回调资源释放前，摘除 ASC 订阅和全部来源/缓冲；从原 ASC 只移除自己的句柄，仍以本 Pawn 为 Avatar 且没有后继同 ASC 会话时才 Clear。绑定更换前后也复核来源和代次。
- 来源缓存不是 held 权威：活动物理请求 Tag 只保存首次触发截止，重复 Triggered 不覆盖；真实释放把该截止移至有限的释放来源快照，新按下删除旧快照/缓冲并开启新请求。释放来源仅供同帧按下+释放后的失败哨兵解析，绝不用于 WhileInputActive 激活判定；过期在现有输入/失败/组释放事件中清理，无新 Tick/Timer。
- BufferAbilityInput(Tag, OriginalDeadline) 使用原来源解析 -1，缺来源或过期拒绝；自动 retry 截止必须匹配本会话当前请求来源并原样保存，不以失败时间起算，不覆盖后来同 Tag 的物理请求。
- GroupFreed 移交有限缓冲至 QueueAbilityInputRetry，成功接收后移出 Hero 意图；再次失败才能按原截止重新缓冲。只入现有输入消费链，无 AbilityInputTagPressed/TryActivateAbility 重试旁路。
- Ability 取消事件复用现有真实 release 回调，并把 Canceled 句柄追加至 C 的会话数组；Completed 保持 A 的原绑定，InputComponent 冻结。这样取消不会遗留来源或 ASC held；无需改共享接口。
- 验收只记录本层静态证据；原 IMC 生产迁移、C 异常来源清理边界、构建/动态与 E/F/G 保持待办。任何必要的新共享接口缺口都停止交回。

### 07C 实施预检

- 职责：Hero 持有输入绑定与 IMC 注册资源；EnhancedInput 持有原生注册计数；CMC 持有 ForceWalk 请求。Camera 的覆盖与代次保持原实现，不通过普通输入退出伪造 PawnExtension 解绑。
- 顺序：A/B 冻结 → C 释放入口及会话资源 → 原 Initialize 前置验证/绑定/注册 → 静态审查冻结 → D 单独授权。没有共享文件并行写入者。
- 冻结 C 接口：公开 `ReleasePlayerInput()`；重复 Initialize、原 Component 更换、EndPlay 和现有 HandleAbilitySystemUninitialized 都复用同一个释放入口。该入口作为 D 后续追加原 ASC 委托/缓冲清理的唯一会话结束接缝。
- 当前引擎事实：CountRegistrations 已存在时只加计数，不改变原优先级；HasMappingContext(Mapping, OutPriority) 可读取现有优先级。相同优先级仍实际 Add，才能持有一份自己的注册；不把别人的已有映射记为自己的。不同优先级或非 CountRegistrations 在资源建立前诊断并拒绝整次初始化；不 remove/readd 改优先级，不在运行时改 TrackingMode。
- 验收：保存原 InputComponent/SubSystem/PlayerInput 来源、实际句柄、去重后的本会话 IMC 及创建优先级；释放先摘除会话资源记录再做有回调的 Remove，重复退出无第二次 decrement。初始化代次只使同步回调中的旧初始化失效，不成为第二套输入状态。
- 若 Subsystem 后续已指向不同 EnhancedPlayerInput，不向新输入对象归还旧 IMC；明确诊断来源失效。该检查防止原 LocalPlayer 子系统仍存活时误减新 Controller 的注册。

## 已冻结接口与后续接缝

- 07A：`BindNativeAction(..., bool bLogIfNotFound, TArray<uint32>* BindHandles = nullptr)`。旧调用仍可编译；后续 Hero 必须传入会话句柄数组。只在找到 Action 并完成 BindAction 后追加实际 GetHandle。Ability 原有句柄收集和 InputComponent.cpp 的 RemoveBinds 均未改动。
- 07B：`bool QueueAbilityInputRetry(const FGameplayTag&, double OriginalDeadline)`。截止使用 World::GetTimeSeconds 时间域，返回 true 仅表示移交到下一次输入消费。无效/非有限/过期截止、无有效 Avatar、输入阻断拒绝入队；同 Tag 请求取较早截止，旧失效请求先清理。
- 07B：`OnAbilityInputRetryable(InputTag, OriginalDeadline)` 改为双参数。同步 retry 的 queued 失败回传原截止；非 retry 失败使用 `NoAbilityInputRetryDeadline = -1.0`。Hero 后续须以原物理请求时间解析此哨兵，不能以失败时刻起算；没有物理请求时不得建立缓冲。
- 物理 pressed 与 retry 同帧匹配一个 Spec 时，真实 pressed 作为新请求优先，失败通知使用哨兵；只有 held 重合时保留 retry 原截止。同一输入消费中每个 Spec 只尝试一次；同 Tag retry 成功后消费该意图，较早失败回调提交的同 Tag 旧请求会清理。
- retry 在入口取快照，回调中新请求留待下次消费。Clear/输入阻断清请求并提高输入代次；InitAbilityActorInfo 的 Avatar 更换也清输入。请求弱 Avatar 与代次在消费/失败通知前复核；失败通知的 Super/委托重入不能继承外层 retry 上下文。
- A/B 冻结时的过渡接缝：Hero 原单参数 BufferAbilityInput/订阅与新委托不兼容。07D 已改为双参数并绑定匹配签名的弱 Lambda，已静态消除这个已知阻塞；本会话未构建，不能据此声称编译通过。
- WhileInputActive 原有每帧真实 held 轮询也可能产生非 retry 失败哨兵；Hero 必须始终解析为本次物理按下的原截止，不能因每帧轮询或再次失败而续期。这是 07D 必须保留的验收接缝。
- 实际检查和未验证边界见 `Module_Repair_07_Validation.md`。A/B 三个源码文件保持冻结；C 的会话机制保留；D 已完成静态冻结；E/F/G 仍未授权，不自动开工。

### 07C 冻结实现

- Hero 公开 BlueprintCallable `ReleasePlayerInput()`；记录原 InputComponent、原 LocalPlayer Subsystem、原 EnhancedPlayerInput 和可选 ForceWalk 的原 CMC，均为弱引用；所有 Native/Ability/ForceWalk 句柄收进一份会话数组。
- 先释放旧会话，再校验 InputConfig、组件类型、必需 Move/Mouse Action、EnhancedPlayerInput、全部去重的 IMC 模式/优先级。任何前置失败都不会新建半份资源；Stick/ForceWalk 仍可选。
- 同优先级 CountRegistrations 映射无论是否已有其它持有者，都实际 Add 一次并记录本会话创建优先级；不同优先级/非 CountRegistrations 拒绝整次初始化并诊断。不改模式，不 ClearAllMappings，不 remove/readd 夺取优先级。
- 引擎先增加计数再同步广播 Added，因此 Add 前登记本次资源，广播中的 Release 能正确归还已增加的那一份。初始化代次检查防止回调结束后旧初始化继续执行；每次 Add 前复核来源/模式/优先级。
- Release 先 MoveTemp 摘除句柄/IMC 并清会话引用/BufferedInputs，再从原 InputComponent 解绑、恢复原 CMC 的 ForceWalk、从原输入来源逐项 Remove 自己的计数。重复退出无第二次归还；Remove 回调新建的后继会话不被旧清理覆盖。
- 原 Subsystem 已指向其它 PlayerInput、Mapping 模式变化或优先级替换时明确诊断并跳过不再可确认的旧注册；不向新来源减计数。旧来源仍存活时的残余计数只能由其自身生命周期处理，不能声称该异常路径已完整释放。
- C 阶段 HandleAbilitySystemUninitialized 只追加对 ReleasePlayerInput 的调用，旧 retry 保持原状；D 现已在同一摘除点补齐原 ASC 委托/输入清理，详见下节。05 Camera 的复位、覆盖和单调代次保留；普通 Teams 退出直接调用 Release，不伪造 PawnExtension 解绑。

### 07D 冻结实现

- 原 ASC 弱引用、Retryable/GroupFreed 两个委托句柄替代 bool。BeginPlay 仅新增 initialized RegisterAndCall，uninitialized 仍为原唯一 HandleAbilitySystemUninitialized。输入先就绪与 ASC 先就绪两种顺序均有既有入口连接；无 Tick 轮询。
- 有效本地会话检查原 Component/SubSystem/PlayerInput、当前 LocalPlayer 和本地控制；ASC 再检查当前 PawnExtension 缓存及 Avatar。弱 Lambda 捕获原 ASC、InputSessionGeneration 和独立 SubscriptionGeneration；解绑立即使旧在途回调失效，订阅代次不干预 C 的 IMC 初始化代次。
- Release 先摘除 C 资源，再由 UnbindAbilityRetryDelegates 摘除 ASC/句柄和所有来源/缓冲；移除原 ASC 上自己的订阅，仍以本 Pawn 为 Avatar 且未被后继会话接管时才 Clear 输入。C 的原句柄/IMC/ForceWalk 清理继续用本地旧快照，后续回调建立的新会话不被覆盖。
- 无参数旧 uninitialized 广播若在其它订阅者重建有效本地会话后才到达，当前已重新绑定、或新输入尚等待晚就绪 ASC 且没有旧订阅时保留后继；EndPlay 标记阻止复活并强制走清理。未新增第二解绑入口，Camera 清理代码及请求代次保持。
- 首次真实 Triggered 保存 `World::GetTimeSeconds() + InputBufferWindow`；重复 Triggered 和 WhileInputActive 的每帧失败沿用原来源，不刷新窗口。Completed/Canceled 移除活动来源，仅在原窗内保留 release 来源供延迟失败解析；真实新触发删除同 Tag 旧 release 来源/缓冲并新建截止。
- 来源缓存只解析截止，不能决定 held 或激活策略。无来源/过期的 -1 失败不建缓冲；自动 retry 的截止须精确匹配当前来源，拒绝旧请求覆盖后来同 Tag 请求。同 Tag 缓冲合并取较早截止。
- GroupFreed 只把快照移交 QueueAbilityInputRetry；原窗内 released OnInputTriggered 可再次匹配，WhileInputActive 仍在 ASC 中要求真实 held。入队前后检查原 ASC/两种代次，失败/阻断/失效请求丢弃，不添加直接激活旁路。
- 源码双参数签名及 Lambda 参数已对应 B，旧 bool/BufferedAtTime/单参数调用均无残留。原生产资产迁移、C 异常来源限制及所有动态验证继续保留；四文件已冻结。

## 原代理交接记录

- `input_bind_handles`、`input_retry_asc` 的历史派发保留；最新代理清单仅有组长，两个 interrupt 请求均返回 `not_found`，没有可继续写入的活动代理，也未重新唤醒或创建代理。
- 未取得两个原代理的完成报告，不能声称其完成或已归档。磁盘核对：InputComponent.h 无工作区 diff；ASC 两文件仍为前批既有修改，未发现新 retry 队列、OriginalDeadline 或新增绑定句柄接口。
- 已保留全部既有改动。组长接管后重新核对当前文件再实施，仅持有上述 A/B 源码范围与本批两个记录文件。

## 尚未授权任务

- 除已冻结07E0-R1及07E1身份诊断外的07E/F专项测试；身份污染已有第17次实际红证据，阻断复活仍未获本步授权或复现。
- 07E2运行身份分配、来源/Spec关系、共享API、消费聚合、Hero与诊断适配；本步仅值类型，不能将上述候选当已冻结接口或已实现行为。
- 07G Input 局部 Markdown / Canvas。
- `IMC_Default`、`IMC_MouseLook` 的 `CountRegistrations` 资产迁移及 `BP_PlayerController` 旧注册路径核对。

以上任务均需统筹单独授权；A/B/C 静态冻结不自动开放后续范围。

## 禁止范围

- 当前长期组长仅持07E2-V新值类型header及本批两个记录租约；07E1诊断、07E0-R1夹具h/cpp、A/B/C/D、PawnExtension/PC/Teams、Admission/其他既有测试、资产、Obsidian、Build.cs、全局台账和排程全部只读；不得构建、操作UE、执行任何Git操作或创建/唤醒代理。
- 临时代理不得修改 HeroComponent、PlayerController、PawnExtension、PlayerCombo、GA 基类、Teams/Slot/Squad、测试、Obsidian、生产资产、Build.cs、全局台账或并行排程。
- 临时代理不得操作 UE、运行 UBT/构建、执行 Git 写操作或再派发写入者。
- 现有未提交改动全部保留。发现需求超出精确文件范围时立即停止并交回组长。
