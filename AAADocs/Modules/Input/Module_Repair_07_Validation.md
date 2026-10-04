# 第 07 批 Input 验证记录

更新：2026-10-01。07E1统筹第17次实际独立身份诊断1 Fail/2 Error/0 Warning，旧请求污染已复现，严格源码及生产保持冻结。本步07E2-V仅共享普通值类型header与两记录，原子预检先登记于子租约；未接入真实TU，不声称已编译或修复。未创建代理、未自行构建或运行UE/Git。

## 07E2-V 当前值类型静态门禁

- 统筹ledger/schedule已登记唯一Input组长三文件租约；新增`F:\ue_project\GGYGO\Source\GGYGO\AbilitySystem\GGYGOAbilityInputRequestTypes.h`及本批两记录。ASC组件/Hero/Fixture/Admission/旧诊断/资产/Obsidian/其它源码冻结，Movement C22仅互斥测试文件另有租约。
- 本步仅声明Identity（原ASC弱引用、revision、serial）及RetryRequest（Tag、Identity、原deadline）。serial0未分配、revision0合法；IsAssigned不等于运行有效；弱来源按对象索引/序列号比较，不能用Get()返回值识别原来源；默认-1无效，不借近期同Tag截止。
- 已保存221个rg可见源码文件及8个记录/笔记/报告的SHA256基线；新header在预检时不存在。预检先登记后添加类型并完成静态核对，三文件交回冻结；本层不进行编译或运行验证。
- 两用户方向与PreviousIdentity/首次接收Spec/多来源聚合均尚未实现；本步无发号、运行容器、Spec集合、共享签名或新调度器。Obsidian已有07G差异继续保留，新类型/API状态须后续获租约时同步，不能提前写成生产已使用。

### 07E2-V 静态结果及保护基线

- 新header 50行，普通struct数量2、直接include数量3，ASC仅前置声明；IsAssigned函数体仅serial!=0，revision0默认合法，deadline默认-1.0。Identity ==逐一比较原弱引用对象索引/序列号、revision、serial，!=取其反；两个失效来源不会仅因都返回null而相等。本机UE5.8 WeakObjectPtrTemplates.h:274同类型HasSameIndexAndSerialNumber只访问WeakPtr，不构造或解析ASC，静态路径不依赖完整ASC类型。
- 去除注释后的静态源码中，无USTRUCT/GENERATED_BODY/UCLASS、容器、Tick、Queue/TryActivate或Get/IsValid调用。项目内该header包含点为0；两个值类型仅在本header出现。没有真实TU实例化/完整编译证据，不能借第17/32次历史构建声称本header已编译。
- 源码清单221→222，新增仅本header；原221个文件中唯一同期变化是独立Movement C22的`Source/GGYGO/Character/Tests/GGYGOActionMotionTest.cpp`。排除该合法并行文件后，220个既有源码的逐文件SHA256均保持，包括ASC输入/仲裁/Montage整文件、Hero、InputComponent、Fixture、Admission、旧诊断及Build.cs。第17次原始报告与计划蓝图/Input目录共5个Obsidian文件hash保持。
- header全文、两记录当前门禁与修改段已审查；三文件尾随空白/冲突标记检查均0，未使用Git检查。header SHA256：`8E795C5A85A546A8D489DE66D7F0B5A3C89B0A31F479ED286DE3F611D4134DAE`；两记录最终hash通过外部交回，本文件不写入自身hash。
- 架构核对：只新增无对象所有权的值副本，无循环依赖、第二权威状态/调度器、内部状态泄漏或资源清理缺口。ASC身份分配/失效校验、真实Tag/Spec关系、Hero复制、失败数组、事件顺序及清理均未接入；07G笔记同步仍受统筹显式冻结，本步只登记新类型未接入与既有图文差异，不写Obsidian。

| 保护源码（本步前后相同） | SHA256 |
| --- | --- |
| ASC.h | `E9AEB8AE04165D05DA8C6C18EB07B18F5C7DCB6D8A4AE0702B1D117845BC95E5` |
| ASC.cpp | `4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF` |
| Hero.h | `AF921B89AA8F665D6F8EF9ED2AF9A5D576AE8252AEC650D072DEEB4D24F5CC91` |
| Hero.cpp | `FEC79B605C4B58A9EEABAC595A4CE53FFC4BC01D55A143535516D2B5B1EACD81` |
| InputComponent.h | `63A9A27A96F882B014D6A9C0EE03B9E572703143DE237A74C46DB27E328A1CC2` |
| Fixture.h | `8576301BDDABF505D5DECAA6E15EBE8717DCB4F031E6C4B82889DA8E28FF6454` |
| Fixture.cpp | `CF89CE4DD8E970DB255899E6750BD161DD3D3EAA5FFCBDFA0A1E11C83FA04878` |
| Admission TestTypes.h | `A5E16C95B563E44EFDFA3733AFBBCFC19D4DD3BA66AC6DEF7499C1434E54D8AF` |
| Admission Test.cpp | `CFEA5CEF5558EF5C8BC61378C883DEFE7A57207ED9DD6D649DF9289303CC73E6` |
| Identity Diagnostic.cpp | `C7D77AD2EB2B4B1C361D682AC4A391CF1747ED71E34A286D734B158EC0DD500D` |

## 07E1 当前身份诊断门禁

- 已读取第16次实际`Saved/AutomationReports/ModuleRepairGate_20260930_16/index.json`及构建日志：2026-09-30 12:22:01（北京时间），48 Success、0 succeededWithWarnings/failed/notRun/inProcess，总0.42834693193435669秒。LocalSessionReady Success，0.010495498776435852秒、entries空、warnings/errors0；全部来源→普通激活→释放→Shutdown断言已执行。它不验证身份/阻断、设备/BeginPlay/网络。
- 07E1三文件范围及先后/清理/停止点见子租约。唯一诊断严格验证旧retry失败公开回调内真实Completed→Triggered的相等时间请求；仅显式ProjectDiagnostics枚举，不ExpectedError、不设计生产requestID。
- 观察Spec必须在重入新press及旧失败返回后才授予：它不在新press当时的Spec集合内。最后真实PC消费中，原请求合法新press激活为配套断言；观察Spec收到Queued失败且通知携带旧显式deadline，才是旧Tag retry污染的可观察证据，不能把普通新press优先消费误写为复现。
- 统筹第17次完整构建Succeeded（6 actions/20.77秒），普通回归49/49 Success；实际独立报告`Saved/AutomationReports/ModuleRepairInputIdentityDiagnostic_20260930_17/index.json`记录于2026.09.30-05.07.20 UTC（北京时间13:07:20），1 Fail/2 Error/0 Warning，0.07691299915313721秒。仅源码292/294两条严格0期望实际为1；全部来源、控制激活、Queued、一次重入、相等时间/有限截止、合法新press配套断言通过。Info：`oldTime=0 newTime=0 oldDeadline=0.34999999403953552 reentry=1 lateFailures=1 lateNotices=1`。旧请求污染已真实复现，未修；阻断另步仍未复现。ASC/Hero/诊断对本步冻结，只开放07E2-V值类型。

### 07E1 实现、静态证据及当时运行交接（历史）

- 新增`Source/GGYGO/Input/Tests/GGYGOInputRetryIdentityDiagnostic.cpp`，324行；复用E0-R1 Fixture、Admission QueuedTestAbility、TestGroupConfig，没有新增头/UCLASS。占位Spec无Light输入Tag；原请求和后授予观察Spec共享Light Tag但各持真实PrimaryInstance。先用同类控制Spec证明真实Triggered→PC→GAS激活，再Completed、结束并移除控制Spec，使正式时序只有三个自有Spec。
- 初始真实物理press得到Queued失败及NoAbilityInputRetryDeadline哨兵；实际结束占位触发GroupFreed移交Hero缓冲，再重新占位，使已排入旧retry真实失败。仅在原生Super AbilityFailedCallbacks且真实失败实例为原请求时执行一次真实Completed→Triggered，不递归消费。回调返回后观察旧显式截止，严格断言有限/未过期、World time完全相等、新press尚未被旧消费快照激活；同一Hero/未改窗口的冻结Now+Window公式据公开旧截止推导新截止相等，不反射或读取私有来源/缓冲。
- 后授予观察Spec后，再真实结束占位并消费。合法新press原请求激活一次、仍活跃且无失败是配套断言；严格核心期望为观察Spec真实失败次数0、显式retry通知数量0、激活次数0。若存在观察失败，额外要求它是真实Queued原因、每次有一条公开通知且deadline严格等于旧deadline；这些证据断言不反转最后的0期望。Info记录oldTime/newTime/oldDeadline/reentry/lateFailures/lateNotices。当前代码静态预计旧通知可重新缓冲而使核心断言红，但实际结果必须由统筹报告证明。
- 清理守卫早于所有授予/测试委托建立，并在观测对象之后声明；析构先按句柄Remove三个测试委托，再Hero Release，再Finish/Clear自有Spec、断开自有组配置，最后Fixture Shutdown。控制Spec提前正常移除；所有提前返回和红结果走同一守卫，不会在能力结束时保留悬空lambda或Hero重试订阅。
- 已逐段审查源码和本机UE5.8.1原生GiveAbility/CanActivate失败/Super通知：InstancedPerActor在授予时创建独立实例，失败使用PrimaryInstance，委托签名为const UGameplayAbility*。所有时间/截止比较使用严格==，没有Automation浮点默认容差；没有ExpectedError、直接Queue、Tick、时间写入、私有缓冲读写或生产修改。只有一个complex注册，基础名`ProjectDiagnostics.Input.RetryIdentity`加子项名形成精确诊断路径；不开显式开关时零枚举，RunTest另行复核开关/参数，不产生跳过成功。
- ASC输入/仲裁15个函数块的前后SHA256一致（包括两个IsActivationBlockedByGroup重载）；ProcessAbilityInput `DEA0168FB7ACD0C30685C6088B744264E23E138FA8A998587469E489EE2A1CE7`、NotifyAbilityFailed `87BA4D13E2341D45975814CBE9C23ABAA29CD0AA8D16F9AAC5D97B422A6F8967`。Combat并行修改Montage入口，故不以ASC整文件哈希变化断言输入契约被改变。
- 新cpp SHA256 `C7D77AD2EB2B4B1C361D682AC4A391CF1747ED71E34A286D734B158EC0DD500D`。Fixture h `8576301BDDABF505D5DECAA6E15EBE8717DCB4F031E6C4B82889DA8E28FF6454`、cpp `CF89CE4DD8E970DB255899E6750BD161DD3D3EAA5FFCBDFA0A1E11C83FA04878`；Admission h `A5E16C95B563E44EFDFA3733AFBBCFC19D4DD3BA66AC6DEF7499C1434E54D8AF`、cpp `CFEA5CEF5558EF5C8BC61378C883DEFE7A57207ED9DD6D649DF9289303CC73E6`，均与接管时一致。InputComponent/Hero原冻结哈希也相同。三文件逐行尾随空白/冲突标记均0；本步没有执行Git命令、UHT/UBT或UE。
- 架构核对：新增仅独立诊断、对象/句柄清理和局部观测，不新增生产权威状态、调度器、循环依赖或接口。只读核对计划蓝图与Input结构；本轮未引入生产架构变化，既有07G图文差异仍待单独授权，未写Obsidian/全局入口。

统筹在全部源码线冻结并完成完整构建后，沿用第16次命令参数执行以下独立诊断（本会话未执行）：

```powershell
& 'F:\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'F:\ue_project\GGYGO\GGYGO.uproject' -Unattended -NoSplash -NoSound -NullRHI -NoP4 -NoTurnkey -GGYGOInputRetryIdentityDiagnostic '-ExecCmds=Automation RunTests ^ProjectDiagnostics.Input.RetryIdentity.SameTimeReentrantPhysicalRequest$' '-TestExit=Automation Test Queue Empty' '-ReportExportPath=F:/ue_project/GGYGO/Saved/AutomationReports/ModuleRepair07E1_Identity' -log=GGYGO_ModuleRepair07E1_Identity.log
```

- 普通回归沿用`Automation RunTests GGYGO`且不带该开关；诊断独立报告，不合并/反转为普通回归成功。
- 先核对来源/控制/真实Queued/旧retry/一次重入/同时间/有限截止/后授予实例等全部前置，再判断两条严格0结果及合法新press配套断言。前置失败仅表示诊断未成立；全部结果成功时记录未复现，不能冒称红；真实严格Fail如实保留，UE exit0不等于测试通过。阻断与生产身份方案继续未开放。

## 前置门禁

- 第 05 批 Camera 已通过完整构建和三组专项自动化；Hero 的 `HandleAbilitySystemUninitialized` 是唯一 PawnExtension 解绑协调入口，第 07 批后续只能扩展该入口。
- 第 06 批 Combatants 已通过完整 `GGYGOEditor Win64 Development` 构建；`ModuleRepairGate_20260930_11` 中五项 Combatants 自动化全部成功、0 warning/error。PawnExtension 的 ExpectedASC 门禁和本地解绑广播可作为只读依赖。
- PlayerController 的 `PostProcessInput` 仍是唯一输入帧末消费入口。

## 07E0 当前夹具门禁

### 第15次实际失败与R1预检

- 已读实际 `Saved/AutomationReports/ModuleRepairGate_20260930_15/index.json` 及 `Saved/Logs/GGYGO_ModuleRepairGate_20260930_15.log`。单项 `GGYGO.Input.Fixture.LocalSessionReady` 为Fail，0.076361805秒，1 warning/1 error：EnhancedInput无有效PlayerInput无法加载user settings；原cpp line171的“subsystem returns controller input”不相等，初始化提前返回，后续断言尚未执行。报告时间2026-09-30 11:50:28（北京时间）；UE进程exit0不等于测试通过。原47项保持Success。
- UE根目录Build.version为5.8.1。原生GetPlayerInput调用LP->GetPlayerController(GetWorld())；UPlayer在非空World时遍历该World的Controller列表。SetPlayer写LP/PC并创建PlayerInput并不等于Controller已在此列表中。
- 原夹具的Standalone World没有InitializeActorsForPlay，AActor::PostActorConstruction因此跳过InitializeComponents/PostInitializeComponents；AController原生PostInitializeComponents中的World AddController未发生。随后ReceivedPlayerController同步通知EnhancedInput时，World过滤查找为空，解释警告及相等断言失败。
- R1唯一修复：在自有World先执行公开原生InitializeActorsForPlay，保留不BeginPlay、不SuperGI；Controller Spawn完成原生PostInitializeComponents后再SetPlayer，再严格核对Actor/World查询/PlayerInput来源。三文件租约，不改Subsystem/Hero/头/生产或预期错误规则，复跑由统筹执行。

### 07E0-R1 实现与静态冻结

- 唯一源码增量为cpp初始化段的20行：自有World InitializeActorsForPlay(FURL())先于Viewport/LocalPlayer创建；断言AreActorsInitialized且HasBegunPlay为false；Controller Spawn后断言IsActorInitialized，SetPlayer后断言LocalPlayer按本World查得本PC，再执行原Subsystem返回本PC PlayerInput的相等断言。未放宽原来源、激活、释放或Shutdown断言。
- 补充核对警告时序：本机EnhancedInput LocalPlayer subsystem没有Initialize覆盖，ULocalPlayer::PlayerAdded只是初始化真实SubsystemCollection。UserSettings加载在EnhancedInput::PlayerControllerChanged中；原生SetPlayer先连接PC/LP、标记本地并调用InitInputSystem，再ReceivedPlayer通知LocalPlayer及各子系统。因此保留AddLocalPlayer在SetPlayer前，先确保PC的PostInitializeComponents已原生登记即可同时补齐警告与来源断言的共同前置，无需先SetPlayer后创建collection。
- 副作用只读审查：Game World CreateWorld默认Navigation/AI为关闭，IsNavigationRebuilt在Navigation为空时为true；空World无GameMode/GameState，PC InitPlayerState不创建PlayerState。PC原生PostInitializeComponents可创建CameraManager等World-owned Actor，既有DestroyWorld负责清理。World原生Actor初始化会通知真实World委托、注册组件/流送，并可能刷新引擎Console自动补全；保留该原生生命周期，没有手工AddController、广播或全局CVar/Settings修改。新增HasBegunPlay断言严格约束本夹具；未声称动态副作用验证通过。
- 新增调用需要的FURL由现有World.h包含的EngineBaseTypes.h定义；原生InitializeActorsForPlay/AreActorsInitialized/HasBegunPlay及Actor IsActorInitialized均为公开API。无需改header、Build.cs或生产接口，失败仍回到既有RAII清理。
- R1 cpp冻结SHA256：`CF89CE4DD8E970DB255899E6750BD161DD3D3EAA5FFCBDFA0A1E11C83FA04878`。header仍为`8576301BDDABF505D5DECAA6E15EBE8717DCB4F031E6C4B82889DA8E28FF6454`；Input h、ASC h/cpp、Hero h/cpp与下方E0冻结时五个哈希相同。未改其他测试或注册新项。
- 增量范围证明：仅在内存中移除R1新增的三个片段，得到恰好减少20行的原文，SHA256重新等于原E0的`031D22D39506E89082ABF2A1698224E1E318C2605ADC59B63ED30C48F15E5E74`；未写回还原文件。由此确认没有覆盖原夹具其它实现或既有未提交变更。
- R1当时静态检查：cpp在嵌套源码仓库no-index whitespace检查无输出、exit1（新文件差异）；两个记录根仓库diff --check无输出、exit0；三文件trailing whitespace/conflict markers均为0。后续第16次实际构建及来源/普通激活/释放/Shutdown全部Success、warnings/errors0，详见本页当前门禁；第15次Fail保持真实历史。

### 原07E0范围与历史静态证据

- 唯一注册项：`GGYGO.Input.Fixture.LocalSessionReady`。只关闭真实本地会话来源及清理前置，不关闭 Input 行为矩阵。
- 授权新增 `Input/Tests/GGYGOInputTestTypes.h/.cpp`，附带本批两个记录；生产接口和既有测试保持冻结。先登记预检，再实现与静态审查，运行交由统筹。
- 身份混淆静态路径：ASC 保存旧 retry 后，GAS `AbilityFailedCallbacks` 可重入同 Tag release/press；请求不提高输入/订阅代次，若新旧 deadline 相同，Hero 相等校验不能区分身份。普通 pressed 已进入快照时有新请求优先保护，不能仅凭截止相等声称复现。
- 阻断复活静态路径：ASC Clear 未使 Hero 意图同步失效，阻断期没有 Hero 回调时，解除后原截止内 GroupFreed 可能重新提交。与身份缺口分开，均未执行复现，本步不实现这些测试或修复。

### 07E0 初始实现与静态核查（历史）

- 新增 `Source/GGYGO/Input/Tests/GGYGOInputTestTypes.h/.cpp`；只注册一项 `GGYGO.Input.Fixture.LocalSessionReady`，位于 cpp 的 WITH_DEV_AUTOMATION_TESTS 内。一个 RAII owner 持有自身上下文/强配置资源及 World 所有的 Actor，初始化任一布尔前置失败后仍由同一路径清理。
- 测试 GI 使用原生 InitializeStandalone 建立自身真实 WorldContext/World，公开 Init override 不调用通用服务；Shutdown 只 Remove 自身 LocalPlayers 和断开自身 protected WorldContext，不调用会清其它实例网络委托的 Super。没有安装/恢复/Unbind 全局网络委托，无无条件旧快照覆盖问题。
- Viewport 原生 Init 建立真实 World/GI 来源；测试 override 的 Added/Removed UI 通知不调用全局 Slate 焦点/布局，GI 仍真实调用 LocalPlayer PlayerAdded/PlayerRemoved。查阅 Engine SwapPlatformUserId/SwapControllerId，交换范围只限新 LocalPlayer 所在 GI；未操作其它实例 LocalPlayer。
- Controller SetPlayer/本地标记和 Possess/PawnClientRestart 走原生入口；测试 InputSystem override 仅创建自己的 EnhancedPlayerInput 和 project InputComponent。Pawn 通过真实 PawnExtension SetPawnData/InitializeAbilitySystem、Hero InitializePlayerInput 建立会话和两个原 ASC 订阅，未手工广播 initialized、未访问或替换 Hero 私有有效性。
- 一个普通 OnInputTriggered、无 GroupTag 的最小 GA 只观测每实例激活次数。单项测试执行实际 Triggered 绑定 Clone/Execute，并调用真实项目 PC PostProcessInput，确认绑定经过 Hero 来源门禁和 ASC 普通输入消费到达探针；不建 retry/阻断/截止/身份/资源重入矩阵。
- 单项断言源码覆盖自身 World/GI/Viewport/LP/SubSystem/PlayerInput/Controller/Pawn/ASC 身份，实际注册和订阅；Release 归还绑定、IMC、两个 ASC 订阅，真实反初始化清 PawnExtension cache/ASC Avatar；Shutdown 后自身 LocalPlayer 数量为 0、LP 子系统反初始化、GI/Engine Context 摘除、全局 GWorld/GameViewport 读回不变。以上是尚待运行的断言，不写成通过。
- 按本机 UE5.8 原生实现核对 RAII：WorldContext 必须仍以 World 可查找才能 DestroyWorldContext；由该引擎入口 SetCurrentWorld(nullptr) 清 Viewport 的外部引用，不能提前置空导致 lookup 失配。原生 Viewport Init 即使 false 也可申请音频，ConditionalBeginDestroy 调用真实 BeginDestroy 立即 Reset 其自有音频句柄；World 自有句柄由 DestroyWorld 清理。无窗口、GC sweep 或生产资产保存。
- 最小夹具不启动 GI 通用 subsystem collection、BeginPlay 或 InitState；不声称覆盖 Hero BeginPlay RegisterAndCall、真实输入设备/Trigger 求值、暂停、PIE/网络或音频动态无泄漏。上述生命周期如需扩展夹具须再授权。
- 已读两源码全文，检查真实 API/所有权/清理和新增 include；新文件未跟踪，源码嵌套仓库普通 diff 不包含它们，采用 no-index whitespace 检查及四文件逐行扫描。构建/UHT 和实际单项运行只由统筹执行。
- 最终静态证据：两个新源码分别 `git diff --no-index --check -- NUL <path>` 无输出、退出码 1（新文件与 NUL 有差异，不是 whitespace 错误）；两个记录的根仓库 `git diff --check` 退出码 0、无输出；四文件逐行扫描 trailing whitespace/conflict markers 均为 0。新增单项注册数量为 1，没有身份/阻断用例或手工 initialized 广播。
- E0 冻结 SHA256：header `8576301BDDABF505D5DECAA6E15EBE8717DCB4F031E6C4B82889DA8E28FF6454`；cpp `031D22D39506E89082ABF2A1698224E1E318C2605ADC59B63ED30C48F15E5E74`。最后核对原生 Viewport/LocalPlayer 的 Within=Engine，二者均以 Engine 为 Outer，仅由夹具自身 context/强引用持有，不更换全局 Viewport。A/B/D 五个生产文件 SHA256 与既有冻结值完全相同（Input h `63A9A27A96F882B0`、ASC h `5C96A8DE131E3558`、ASC cpp `3CA7B55AC368B332C`、Hero h `AF921B89AA8F665D`、Hero cpp `FEC79B605C4B58A9E` 前缀）。
- 架构核对：新增内容仅为测试对象构造、观测和 RAII；没有生产循环依赖、新调度器、第二输入事实、私有缓存暴露或生产资产接线。已只读核对计划蓝图/Input 结构；本轮没有新的生产架构变化，既有 G 图文差异仍待其精确授权，未写 Obsidian/全局入口。

## 本层实际实现

### 07A

- `BindNativeAction` 新增末尾可选 `TArray<uint32>* BindHandles = nullptr`，成功绑定时把 GetHandle 追加到调用方数组，与已有 Ability 批量绑定共享 RemoveBinds 释放契约。
- 只在成功创建绑定时登记句柄；缺失可选动作不登记。
- 不改变 InputConfig 查找、TriggerEvent 选择或 `RemoveBinds` 清理语义。

### 07B

- 新增独立 retry 请求及 OriginalDeadline 传播，仍由 `ProcessAbilityInput` 统一收集和激活。
- retry 不写物理 pressed / held / released，不写 `Spec.InputPressed`，不向已激活能力发送 `AbilitySpecInputPressed`。
- `OnInputTriggered` 可消费未过期 retry；`WhileInputActive` 仅在真实 held 仍存在时纳入激活。
- retry 再失败向意图层回传原截止时间，不把失败时刻当成新起点。
- 输入阻断、`ClearAbilityInput` 和缓存消费有明确清理路径，不新增 Tick 或第二执行器。
- 同 Tag 请求合并取较早截止；快照消费时按当前 Spec 精确匹配。每个 Spec 在统一循环最多尝试一次，retry 成功消费同 Tag 意图。
- 物理 pressed 与 retry 重合时真实按下作为新请求优先；只有 held 重合时沿用 retry 原截止。物理请求失败的 `-1.0` 哨兵必须由后续 Hero 从物理请求时间解析。
- 原物理 pressed/released 和 retry 在入口取快照，回调产生的新事件保留到下一次消费。输入代次仅用于失效检查；Avatar 更换/Clear/阻断使旧快照失效，无第二套物理状态。retry 弱 Avatar 不持有宿主生命周期。
- 同步失败先保存 retry 来源，再隔离 Super/委托重入上下文；自动失败不把当前时间写成新截止。

### 07C

- 新增公开 BlueprintCallable `ReleasePlayerInput()`；重复 Initialize 或换 Component 必须先释放记录的原输入会话。EndPlay 复用原 HandleAbilitySystemUninitialized，由该唯一协调器调用 Release；普通输入退出不重置 Camera 或伪造 PawnExtension 解绑。
- 一份 InputSessionBindHandles 收集全部成功 Native/Ability 绑定；Move、Mouse、Stick、ForceWalk 的 Triggered/Completed/Canceled 都传入 A 的输出数组。Release 使用原 Component 的 RemoveBinds，不在新 Component 上解绑旧句柄。
- 输入会话弱记录原 Subsystem、EnhancedPlayerInput 和可选 ForceWalk 的原 CMC。ForceWalk 按下/松开继续使用 CMC 权威 SetForceWalkRequested；退出恢复原 CMC，没有配置该输入时不借退出重置其它 CMC 请求。
- IMC 先全量去重并验证 CountRegistrations/已有优先级；模式未迁移或优先级冲突时诊断并拒绝整次初始化。相同优先级仍实际 Add 自己的计数；记录创建优先级，Release 配对自己的一次 Remove，不借 HasMappingContext 复用别人的资源。
- InputConfig、输入组件类型、必需 Move/Mouse Action、底层 EnhancedPlayerInput 都在新资源建立前校验；旧会话已释放，失败不会留下半注册。没有 ClearAllMappings、运行时 TrackingMode 写入、remove/readd 改优先级。
- 会话记录在 Remove 前摘除并失效；Add 按本机引擎“先计数后广播”顺序登记，再用会话代次阻止同步 Release/后继 Initialize 后的旧流程继续。每项 Add 前复核来源和优先级，后继会话不被旧清理覆盖。
- C 冻结时 Release 清 BufferedInputs 并保留 D 的唯一接缝，未改旧 retry 订阅/单参数签名；D 下节现已完成该接缝。C 静态结论本身不代表完整 ASC 生命周期或动态通过。

### 07D

- 已改为 BufferAbilityInput(FGameplayTag, double OriginalDeadline) 和匹配 B 的双参数弱 Lambda；原 bool 由原 ASC 弱引用及两个委托句柄替代。
- BeginPlay 注册 initialized RegisterAndCall；uninitialized 仍只使用原协调器。Bind 同时要求有效本地输入资源、当前 LocalPlayer/PlayerInput、PawnExtension ASC 缓存及本 Pawn Avatar；C 的 Initialize 结束也尝试订阅，两种就绪顺序均有入口。
- 回调捕获原 ASC、输入会话代次和订阅代次，旧订阅摘除立即失效。绑定切换前后重新读取 PawnExtension/来源身份，晚就绪的初次绑定保留此前真实触发来源，换旧订阅时清理其来源/缓冲。
- Release 先摘除 C 记录，再摘除原 ASC/委托/来源/缓冲；只按句柄解除自己的原订阅。原 ASC 仍以本 Pawn 为 Avatar、会话代次未变且没有后继同 ASC 绑定时才 ClearAbilityInput，不能清新 Avatar 的物理/重试状态。
- 无参数旧 uninitialized 通知遇到已重建的有效本地绑定，或刚建立且没有旧 ASC 订阅的等待会话时保留后继；EndPlay 禁止再次初始化并强制清理。05 Camera 清理及请求代次代码保持原状，没有第二解绑协调器。
- 首次实际 Triggered 记录绝对截止，连续 Triggered 不覆盖；活动来源即使已过期也保留到真实 release/会话失效，避免 held 每帧失败重建窗口。来源只是请求时间缓存，不参与 ASC held/策略判定。
- Completed/Canceled 在同一 release 回调中移除活动来源；原窗内 release 来源快照支持同帧 press+release 后的初次失败解析。新按下移除同 Tag 旧快照/缓冲并开启新截止；Released 快照和缓冲在现有事件中惰性清过期，窗口为零/非有限配置不能建立可重试请求。
- -1 哨兵必须查到当前物理来源，缺来源/过期均拒绝；显式 retry 截止必须精确匹配本会话当前来源，旧失败不覆盖同 Tag 后来的新请求；同 Tag 缓冲合并取较早截止，失败不会重算 Now+Window。
- GroupFreed 移出 Hero 缓冲快照后只调用 QueueAbilityInputRetry；前后检查 ASC 与两种代次。请求由原 ASC 下一次 ProcessAbilityInput 消费；入队失败的无效/阻断/过期请求不保留。OnInputTriggered 可以在 release 后原窗内重试；WhileInputActive 的真实 held 仍只由 ASC 检查。
- Ability 的 Canceled 绑定新增在 Hero，成功句柄纳入 C 的同一数组；A 的 Completed 和 Triggered 绑定未改。未改 ASC/InputComponent/PawnExtension/PC/Teams，没有直接 TryActivateAbility、重试 AbilityInputTagPressed、Tick 或 Timer。

## 静态审查与冻结证据

- 代理清单仅有组长；两个旧代理 interrupt 均返回 `not_found`。未取得完成报告，未重新唤醒或声称归档。
- 接管时 InputComponent.h 无 diff，ASC 两文件保留前批修改；组长仅向这三个授权源码文件增量写入 A/B，未覆盖 04 的准入/通用纠正/结束重入实现。两个批次记录文件已同步。
- 已阅读三个文件的实际工作区 diff。ASC 相对 HEAD 的 diff 同时含前批既有修改，不能把整个 diff 的统计记为本批新增量；本批新增范围为 Native 输出、retry 数据/接口、输入快照与失效清理、失败截止回传及相应接口注释。
- `Source/GGYGO` 是独立 Git 仓库。已在该目录执行 `git diff --check -- Input/GGYGOInputComponent.h AbilitySystem/GGYGOAbilitySystemComponent.h AbilitySystem/GGYGOAbilitySystemComponent.cpp`，退出码 0、无输出。根仓库对子目录内部路径的空 diff 不能作为源码证据。
- 最后一次源码 diff --check 在接口注释收尾后仍为退出码 0；本批两份记录的尾随空白均为 0、无合并冲突标记。
- 查阅本机 UE 5.8 的 EnhancedInputComponent.h，确认 BindAction 返回事件绑定引用及 uint32 GetHandle；查阅 Templates/UnrealTemplate.h 确认 TGuardValue；GenericPlatformMath.h 确认 double IsFinite；GameplayAbilitySpecHandle.h 确认默认无效句柄和 TMap 哈希支持。已修正检查中发现的 GuardValue include 路径。
- 查阅 GAS InternalTryActivateAbility/NotifyAbilityFailed，queued CanActivate 失败同步进入本组件通知；deadline 上下文仅在统一尝试调用栈内保存，不新增异步激活机制。
- 源码逐段审查：retry 入队/收集未写 pressed/held/released 或 Spec.InputPressed；InputPressed 写入和输入事件只在原物理阶段；WhileInputActive 在收集和实际尝试前均复核真实 held；失败回传直接使用 FailedRetry.OriginalDeadline；Clear 同时清三阶段与 retry 并失效快照；Avatar 弱引用/代次清理具备入口。
- 架构核对：未增加 Hero/具体角色/PlayerCombo 依赖、循环依赖、Tick、第二帧调度器或组排队事实；重试只借现有 ProcessAbilityInput/TryActivateAbility 链。PC 的 PostProcessInput 和 04 NotifyAbilityEnded 清理/广播次序保持现状。暂停/焦点策略未在本层修改。
- A/B 静态冻结已获统筹认可，保持只读；没有活动临时代理，不冒称旧代理已归档。

### 07C 静态核查（当时冻结证据）

- 已逐段审查 Hero 两文件实际 diff，保留 05 Camera 既有改动。新内容仅为输入会话来源/句柄/IMC、公开释放、前置验证、唯一协调器接线与 ForceWalk 原 CMC 恢复；D 的 BindAbilityRetryDelegates/BufferAbilityInput/HandleAbilityGroupFreed 实现与签名未改。
- 在 Source/GGYGO 仓库执行 `git diff --check -- Character/Components/GGYGOHeroComponent.h Character/Components/GGYGOHeroComponent.cpp`：退出码 0、无输出。
- 冻结前再次 diff --check 仍为退出码 0；两份记录尾随空白为 0、无冲突标记。C 最终 SHA256 前缀：Hero.h `1424BBE01254B020`，Hero.cpp `69C377B4F1972E2E`。
- 查阅 UE5.8 InputMappingContext.h：CountRegistrations 为原生模式；EnhancedInputSubsystemInterface.h/.cpp：GetPlayerInput、HasMappingContext 的优先级重载、Add/Remove 计数及默认 FModifyContextOptions；EnhancedInputSubsystems.cpp：LocalPlayer Add/Remove 在底层操作后同步广播。因此本层不设第二套计数，也不注册第二个 PawnExtension 协调器。
- 输入初始化只 Add，不 Remove/重建他人映射；Release 只按记录的本会话资源操作，失效来源/被替换优先级/改变模式有诊断。弱引用不延长对象生命周期；会话代次只处理初始化回调失效；无 Tick、循环依赖、其它模块内部写入或新的 ForceWalk 权威状态。
- 核对 A/B 冻结源码哈希前缀仍为 `63A9A27A96F882B0`（InputComponent.h）、`5C96A8DE131E3558`（ASC.h）、`3CA7B55AC368B332C`（ASC.cpp），与 A/B 冻结收尾一致；C 未写这三文件。
- C 当时冻结已获统筹认可；Hero 文件此后只按 D 精确范围扩展。未构建或操作 UE。

### 07D 静态核查

- 已审查 Hero 两文件新增订阅/物理来源/缓冲/Queue 代码及差异。实际 HEAD diff 仍包含 05/C 既有改动，不能把统计全记为 D；C 的原 Component/SubSystem/IMC/ForceWalk 所有权路径保留，Camera 覆盖及单调请求代次未重写。
- 查阅本机 UE5.8 DelegateSignatureImpl.inl，确认 AddWeakLambda 返回 FDelegateHandle；PawnExtension 的 RegisterAndCall 会补发已有 ASC，uninitialized 在移除本地 ASC 缓存后广播；B 的双参数失败、NoAbilityInputRetryDeadline、Queue/Clear 和策略判定保持只读。
- Source/GGYGO 中搜索旧 bAbilityRetryDelegatesBound、BufferedAtTime、单参数 BufferAbilityInput 调用无残留。Hero 的 AbilityInputTagPressed 只在真实按下回调出现；重试方法只 Queue，未新增 TryActivateAbility。
- 原截止写入只有首次真实 Triggered 的 Now+Window；失败路径直接解析已有来源或接收原截止，合并只取较早值。活动来源不会因过期/held 轮询删除重建；release 后只保存有限来源而不伪造 held；所有来源/缓冲在会话/订阅退出摘除。
- 在 Source/GGYGO 仓库对 Hero 两文件执行 diff --check，退出码 0、无输出；本层为静态核查，未运行 UHT/UBT/UE。A/B 冻结文件 SHA256 未变化，未扩写共享接口。
- 最终 Hero.h SHA256 为 `AF921B89AA8F665D6F8EF9ED2AF9A5D576AE8252AEC650D072DEEB4D24F5CC91`，Hero.cpp 为 `FEC79B605C4B58A9EEABAC595A4CE53FFC4BC01D55A143535516D2B5B1EACD81`。记录尾随空白 0、无冲突标记；两源码最终 diff --check 仍为退出码 0。
- D 四文件冻结，E/F/G 未启动；统一构建只能由统筹在各源码线全部冻结后安排。

## 未验证及后续门禁

- 原单参数委托阻塞已消除；统筹第14/15/16次完整构建已覆盖冻结A/B/C/D。初始07E0第15次来源单项Fail；R1第16次实际Success、普通回归48/48成功。07E1第17次已实际1 Fail/2 Error，身份污染未修，后续门禁未重跑该独立诊断；不据普通回归或值类型声明推导身份/阻断及全部Input行为已验证。
- 本会话未执行 UHT、UBT/完整构建、UE 自动化、PIE、联机或专服验证。
- 尚未修改或保存任何 `.uasset`。
- 尚未执行 Git add/commit/push/reset 等写操作。
- C/D 已落地资源会话、ASC 订阅/清理、物理来源原截止和 Queue 移交；专项运行仍待统筹。WhileInputActive 的每帧 held 失败哨兵现在解析为原物理截止，不作为新物理请求；真正新按下的旧快照/失败隔离仍需动态覆盖。
- 07E/F 仍需验证 released OnInputTriggered、released WhileInputActive、不伪造活跃输入事件、过期/非有限时间、重复 Tag、同步 Clear/换 Avatar 与失败不续期等专项断言。
- C 的重复 Initialize/换 Component/幂等释放、多个持有者 IMC 计数与优先级冲突、失败前置校验、ForceWalk 恢复和 Add/Remove 回调重入仅静态审查，专项测试尚待后续授权，不能写成动态通过。
- D 的 ASC 晚就绪、旧 ASC 更换/新 Avatar 保护、解绑广播后继会话、同 ASC 重订阅旧回调失效、同帧 tap、持续 Triggered/held 不续期、新按下隔离、Canceled、零窗口及无来源哨兵仅静态审查；生产资产/PIE/联机行为没有验证。
- `IMC_Default`/`IMC_MouseLook` 的 CountRegistrations 生产资产迁移及 BP_PlayerController 旧注册路径仍待统筹；本层未回读/保存资产，不推断当前资产已符合模式。只要任一配置 IMC 仍非 CountRegistrations，C 的明确行为就是诊断并拒绝创建整次输入会话，不能声称生产输入已可用。
- 若原 Subsystem 后续已绑定另一 EnhancedPlayerInput，释放不能通过该 Subsystem 修改旧对象计数；当前诊断并停止旧 IMC 归还，防止误减新来源。模式/优先级被外部替换同样跳过；残余旧来源生命周期需动态验收。原生计数不提供持有者 token，所有持有者必须遵守配对 Add/Remove，外部 ClearAllMappings 后同优先级重建无法凭优先级识别，不能声称防住所有破坏性外部操作。
- 已按计划蓝图定位并只读核对 Input/结构.md、计划_输入与意图.md 及两张 Input Canvas。旧计划仍写“重走 AbilityInputTagPressed”和“失败刷新时间戳”，结构 Canvas 仍列 BufferAbilityInput(Tag)，需在 07G 改为独立 retry/双参数/原物理截止并标明实现和集成状态。最新租约明确禁止本层写 Obsidian，故只登记差异；全局模块参考/实施状态/入口仍由统筹管理。
- C/D 后续图文还需补 ReleasePlayerInput、原资源会话、CountRegistrations/优先级门禁、唯一协调器、initialized 补发、原 ASC/句柄与两种代次、物理来源原截止和独立 Queue 链。源码实现可标明已静态冻结，生产资产/构建/动态仍应标未完成；G 未获授权，本层未改 Obsidian。

以上07E0-R1来源单项已实际通过第16次门禁；07E1第17次严格红诊断已证明该场景的旧请求污染，尚未修复。生产输入/夹具/Admission/旧诊断保持只读，本步仅07E2-V值类型三文件；运行契约/其它E/F/G未获本步授权。统一构建、自动化和后续授权由统筹安排。
