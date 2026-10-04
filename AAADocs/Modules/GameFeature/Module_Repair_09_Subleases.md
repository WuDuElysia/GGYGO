# 第09批 GameFeature：原子文件范围与交接

更新：2026-09-30。记录名沿用 Subleases；本批由长期 GameFeature 组长直接执行，不创建子代理或临时会话。

## 历史原子步骤：09-G0-0

- 唯一目标：为待实施 GameFeature 依赖分类所需的真实 `IPluginManager / IPlugin` 公开接口，显式补齐 GGYGO 的 Private `Projects` 构建依赖。
- 唯一写入者：GameFeature 长期组长 `01a0e5b5-9dc9-7b32-8aaa-3316137b0cc9`；执行约定 `gpt-6.1-sol / xhigh`。
- 授权来源：统筹本轮明确派发；当前排程 L2 / 09-G0-0。授权仅限下列三文件。
- 状态：三文件完成静态核对后冻结交回；未构建、未接入生命周期、C15 未关闭。

### 精确文件范围

| 文件 | 本步唯一改动 |
| --- | --- |
| `F:/ue_project/GGYGO/Source/GGYGO/GGYGO.Build.cs` | PrivateDependencyModuleNames 仅新增 Projects 及一行用途注释。 |
| `F:/ue_project/GGYGO/AAADocs/Modules/GameFeature/Module_Repair_09_Subleases.md` | 新建本步范围、预检与停止点记录。 |
| `F:/ue_project/GGYGO/AAADocs/Modules/GameFeature/Module_Repair_09_Validation.md` | 新建基线、实际差异、静态证据及未验证项。 |

### 拆分预检

- 所属职责：GameFeature 准入实现的模块构建依赖；本步不处理 URL、Owner、Async 或插件状态。
- 输入：当前磁盘 Build.cs 完整内容、本机 Projects 公开接口与 GameFeatures/Projects 模块规则。
- 输出：一条显式私有依赖和两份记录；对外接口不变，无需新增共享接口。
- 先后顺序：依赖及基线只读核对 → 两行增量 → 全文/依赖静态检查 → 两记录 → 三文件读回并冻结。
- 只读依赖：`F:/UE_5.8/Engine/Source/Runtime/Projects/Public/Interfaces/IPluginManager.h`、`F:/UE_5.8/Engine/Source/Runtime/Projects/Projects.Build.cs`、`F:/UE_5.8/Engine/Plugins/Runtime/GameFeatures/Source/GameFeatures/GameFeatures.Build.cs`；路由、审计账本、并行排程与既有 GameFeature 四份策略文档。
- Build.cs 原 SHA-256：`FD4A48A575CEF3B1E9DFE6E12411AC9654F5C1C781D2332928F5C4BCE7F9BC61`；写入前复读一致。未查询/重置 Git，按当前磁盘基线保留原有内容。

### 验收断言与非目标

- Projects 原不存在；修改后有效 Private 列表出现一次、Public 零次；无重复依赖。
- 删除新增注释与 Projects 两行，全文逐字还原原基线；既有 Public/Private 条目、Editor 条件、Iris helper 和其它文本保持。
- 依赖方向为 GGYGO → Projects 基础设施，无新增反向项目依赖；静态核对不代替完整构建。
- 不修改 Retention h/cpp、GI/session/GameMode、配置、资产、测试、引擎文件、全局记录或 Obsidian。
- 不运行 UE、构建、Git；不创建代理。

## 后续边界（未实施、未授权）

最终策略仍为只停用、不卸载：同一 GameInstance 正常运行/切图/回菜单保留原生 Loaded；对局只撤回自己的 Active，保护其他原生使用者。GameInstance 结束后清理，不保证 PIE 停止后永不卸载。

薄会话、候选 GI 保留宿主、依赖 Loaded 保留与外部借用仍未实现；外部借用属于最终 C15 范围，不能因首个内部步骤未覆盖就缩减目标。原生 Controller 仍唯一合并需求与转换状态，不新增项目使用人数或调度器。

停止点：构建依赖及两记录冻结交回。后续核心源码由统筹另授；GameMode 等待 batch08 冻结交接。本记录不授予后续写入权限。

## 当前原子步骤：09-G0-1（预检与冻结交回）

- 唯一目标：普通共享 C++ 类 FGGYGOGameFeatureRetention 的单个原生 Loaded handle 生命周期；目前零生产调用方。
- 授权：统筹明确派发及排程 L3；长期 GameFeature 组长直接执行，gpt-6.1-sol / xhigh，不创建代理。
- 精确唯一四文件：新 `Source/GGYGO/GameModes/GGYGOGameFeatureRetention.h`、`.cpp`；本文件；`AAADocs/Modules/GameFeature/Module_Repair_09_Validation.md`。Build.cs、其它生产/测试/配置/资产/Obsidian/全局记录冻结。
- 输入：OwnerLabel；后续准入已证明 GFP 身份、完整依赖闭包和项目管理所有权的 URL 集合。当前核心不证明这些前提。
- 输出：TryCreate 的共享资源或错误；RetainAlreadyLoaded 的拒绝/登记已提交/中途未完成及本次提交数；ReleaseOwnedReferences 的一次完成结果。
- 接口仅上述三种；不声明尚未实现的准入/GI/Active/session API，不以空实现冒充可用。
- 顺序：本机 native API/基线核对 → 本节及验证记录登记 → h/cpp → 静态 API、逐批校验、释放重入/析构审查 → 四文件读回/哈希 → 冻结交回。
- 只读依赖：本机 GameFeatureStateHandle、ReferenceController、GameFeaturesSubsystem 公开头和实现；Core 共享指针/Async/Misc API；排程及四份已冻结策略文档。
- 验收：输入整批先校验，仅稳定 Loaded/Active；None + AddOrUpdateReference(...Loaded,false)；每次提交前后复核；void 无 ack，部分提交资源仍归本对象。关闭/释放只涉及自身 handle，native Controller 唯一合并状态。
- 释放审查：同步/异步/重入安全，每次 completion 最多一次；重复请求给出 pending 或原终态，不重复 native。原调用返回且 handle 注销后才交付同步完成；析构不 SharedThis/捕获裸 this，不依赖 UObject。
- 非目标：依赖解析/分类、外部借用接线、Active/迟到会话回调、GI/session/GameMode/测试/资产/图文。最终同 GI Loaded 保留及明确外部借用目标不缩减，C15 不关闭。
- 停止点：仅四文件静态冻结交回，完整构建/UE/动态验收由统筹另排。本轮不运行 UE/构建/Git。
- 状态：实现及静态审查完成，四文件冻结交回；本核心未编译/动态验收。

### 本步唯一交回结果

- 新建一个非 UObject 的共享 Loaded handle 资源类，仅实现 TryCreate、RetainAlreadyLoaded、ReleaseOwnedReferences；零生产调用方。
- Retain 的 Submitted 表示 void 登记已提交，Interrupted 携带本次提交数及错误，已提交引用仍由资源持有；该数不是使用人数，也不作为成员缓存。
- Release 在 game thread 先关闭；错误线程请求不修改资源且即时返回 RejectedWrongThread。进行中的重复调用仅收到一次 Pending，完成后重复调用重放原 Released/Failed/Unconfirmed，不重复 native。
- 原生同步 completion 先记录结果，待 ReleaseAndUnregister 返回、handle 已注销后才通知用户；调用及异步期间共享引用保活。原生异常 off-thread completion 只经 Core 既有 game-thread 队列一次投递，并标未确认。
- 析构把仍有效的 native handle 移出成员，独立诊断 lambda 不捕获 this/GI/World；错误线程最终析构只将独立 cleanup 投递 Core 既有队列。没有新增帧循环、计时器、全局协调器或插件状态缓存。
- 析构/动态 lifetime disable/engine exit 清理无法确认时记录失败；不裸 API 兜底。GI 保留、依赖解析与外部借用仍待后续独立授权，C15 未关闭。
- 架构核对：现有 GameMode 裸激活链及两图仍不变；新增未接入核心类和接口需在后续局部图文租约同步，本轮按明确授权保持四份策略文档冻结。

## 当前短修：09-G0-1-R1（实施前预检）

- 唯一目标：创建/Retain 准入及实际稳定状态查询在 GEngine 或公开 GameFeaturesSubsystem 缺失时拒绝，消除该路径经 Get 的空解引用。
- 唯一三文件：`Source/GGYGO/GameModes/GGYGOGameFeatureRetention.cpp`、本记录、`AAADocs/Modules/GameFeature/Module_Repair_09_Validation.md`；h、Build.cs、其它源码/测试/配置/资产/图文/全局入口冻结。
- 输入/输出：既有三接口保持；只补可用性拒绝错误，状态查询使用当次检查所得公开指针，不缓存引擎或插件状态。
- 只读依据：本机 GameFeaturesSubsystem.h 的 Get 直接解引用 GEngine/GetEngineSubsystem；Engine.h 的 GetEngineSubsystem 公开返回可空指针；排程 L3 的明确短修授权。
- 顺序：原哈希及 native 公开 API 核对 → 两记录追加预检 → cpp 小增量 → 旧执行检查/Release/析构全文不变核对 → 三文件与保护哈希读回 → 冻结交回。
- 验收：线程/退出/CVar 原顺序不变，创建及每次 Retain/查询覆盖缺失引擎与实际子系统；不修改原生释放/同步异步 completion/CVar 语义。
- 边界：持有引用后任意子系统提前销毁不受本检查保证；未来宿主必须在合法引擎生命周期内退役资源，不扩架构或补裸 API。
- 停止点：仅三文件静态冻结；不编译/UE/测试/Git，不开代理，C15 未关闭。
- 状态：已登记，实施中。

### R1 实际交回（本短修已冻结）

- cpp 仅新增 Engine/Engine.h 与当次可空子系统查询；TryCreate 前/后及 Retain 前提拒绝缺失 GEngine/Subsystem，实际 GetPluginState 使用已检查的公开指针。
- CheckNativeExecution 的线程/退出/CVar 顺序与函数全文保持；从 ReleaseOwnedReferences 至析构的全部代码逐字保持。h/Build.cs/四份策略文档保持原哈希。
- 差异：cpp +25/-4 行；两记录仅追加 R1 预检/证据，既有 G0-0/G0-1 历史未覆盖。当前 cpp 共385行。
- 边界仍为当次准入/查询可用性；不能由此保证已持有 native 引用时任意 Engine/GameFeatures 提前拆除。未来宿主须在合法基础设施生命周期内先退役资源，native 析构路径未被本步改造。
- 三文件静态核对与读回完成，冻结交回即停止；未编译或动态验收，C15 未关闭，无其它文件/UE/构建/Git/代理操作。

## 09-G0-2：受限闭包与明确来源候选（实施前契约冻结）

- 唯一目标：一个无生产调用方的同步解析接缝，交回当前受限元数据闭包和每个 GFP 的明确来源声明；不证明资源保护或释放资格。
- 授权：统筹明确批准、并行排程 L4；GameFeature 长期组长直接完成，gpt-6.1-sol / xhigh，不启用代理。
- 精确唯一四文件：新 `Source/GGYGO/GameModes/GGYGOGameFeatureClosureResolver.h`、`.cpp`；本记录；`AAADocs/Modules/GameFeature/Module_Repair_09_Validation.md`。其它源码、Retention、Build.cs、GameMode/GI、测试、配置、资产、Obsidian、全局记录冻结。
- 所属职责/依赖方向：GGYGO 的 GameFeature 元数据准入候选 → 原生 GameFeatures policy/Subsystem 与 Projects 描述接口；Controller 继续唯一拥有引用聚合及转换。本步没有状态机、宿主或执行器。
- 已冻结接口：static ResolveClosureAndDeclaredSources(const UGameFeaturesSubsystem&, const UGameFeaturesProjectPolicies&, FInput Input)；输入按值复制根名称和来源声明；输出仅 Rejected/ResolvedCandidate 与自有字符串/数组值。每个 reached GFP 必须明确 ProjectNativeManaged 或 ExplicitExternalBorrow，借用 OwnerLabel 不是保护证明。
- 合法生命期：未来唯一调用方须取得实际当前 policy，并审查覆盖整个同步调用（包括 GetDetails 内部 policy）的合法窗口。实际原生 PolicyPostInit 栈有初始化顺序证据；其它稍后调用点另审。零 GetPolicy 获取、零引用持久化、零 bPolicyReady；公共 IsValid/Outer/Engine.IsInitialized/AssetManager 存在不构成就绪证明。
- 受限范围：精确默认 policy；已安装且已映射、无 options 的 file GFP；稳定已安装元数据。错误线程/退出/实际子系统不匹配/policy Outer或实际类不匹配/custom reader 等观察到的不兼容均拒绝。动态重载、初始化/关闭重入或任意阶段探测不受支持。
- 顺序：基线和原生 API → 冻结本数据契约及头 → cpp 解析 → API/结果边界/静态审查 → 四文件读回与保护哈希 → 冻结停止。
- 解析断言：根去重；native Details 与实际 Projects descriptor 的 enabled/Activate 逐项交叉；原始文件 Plugins 字段保守校验，防止双方宽松解析遗漏畸形数据。全部 enabled 依赖都调用实际 policy Resolve，包含 shouldActivate=false；错误（包括 optional）拒绝，成功空 URL 留非 GFP 证据，非空 URL 与 native 名称映射一致后遍历；身份/URL冲突、循环、未知或冲突来源拒绝，不发布部分候选。
- 只读依赖：GameFeaturesSubsystem/ProjectPolicies 公开头及实际实现、Engine/AssetManager/GI/SubsystemCollection 生命周期、Projects IPluginManager/IPlugin/PluginDescriptor/PluginReferenceDescriptor、Core 路径/集合和 Json API；当前路由/账本/排程、GameMode/Experience、四份冻结 GF 图文。
- 非目标：原生引用或加载/激活/停用/卸载、Loaded状态确认、GI/Active/session/inflight/World保护、外部借用保护、生产接线、测试/编译/UE/Git。候选输出不能转化为释放许可，C15 仍开放。
- 最新禁止隐式业务兜底规则：未知 URL、畸形/冲突元数据或缺失来源明确可定位拒绝；不跳过失败项、替换业务或返回成功。原生 policy 成功空 URL 是显式非 GFP 分类，不是失败回退。
- 停止点：仅四文件实现和静态证据冻结交回；任意窗口安全获取若需新框架则停交统筹，不扩大本步。实现冻结后才能另排专项及局部架构图文。

### G0-2 实际交回（实现冻结）

- 普通 static resolver 无实例/生产调用方；数据契约先冻结，h 此后全文及创建时哈希保持。输入按值复制，结果仅含自有字符串/数组。
- 观察到的不兼容拒绝：错误线程、退出、缺失实际 Engine/AssetManager/Subsystem、Subsystem身份/policy Outer及精确默认类不匹配、自定义 reader。额外拒绝非默认配置声明，防止“配置其它policy失败却被native回落为默认”进入受限候选；不新增项目policy替代。
- installed file URL 无options，先检查原生协议/路径后 Parse，安装路径/描述文件名/规范插件名/policy URL 与 native 映射交叉；禁止同一身份不同URL或不同身份共用URL。
- 原始文件检查先于 GetDetails：Name/Enabled/Activate 类型、重复名/畸形项/Plugins数组及已声明GF初态/布尔字段错误均拒绝。缺省可选Plugins/Activate及native文档规定的旧初态字段模式仅保留其原生元数据含义，本解析器不选择、替换或执行业务。
- 实际 Projects descriptor 的全部依赖与原始文件交叉，再将其全部enabled项与实际native Details逐项交叉；所有enabled项都调用当前实际policy Resolve，不以ShouldActivate过滤。error和无value结果均拒绝；success空URL经已安装非GFP身份复核留下显式排除证据；非空URL经native映射一致后遍历。
- 遍历使用当次局部数组/集合/映射，非递归且完整记录循环路径；根与相同来源去重，冲突/缺失/未使用来源拒绝。Rejected重新构造只有错误的结果，不交付部分闭包。末尾复核映射后才有唯一ResolvedCandidate出口。
- Borrowed节点单独列为保护尚待证明；包括Managed根到Borrowed依赖的路径仍仅为候选，未来生产准入须解决外部实际保护及受影响闭包隔离，不据此释放Active或降级原生状态。
- 零GetPolicy获取、私有初始化反射、长期ready/插件状态/图缓存、native引用或生命周期调用、GI/session/GameMode接线及调度器。原生GetDetails可填充其既有详情缓存；没有建立项目缓存或新增插件注册执行链。
- 架构核对：GameFeature → GameFeatures/Projects已有依赖；无反向模块依赖/第二状态权威/新宿主；所有临时值随调用退出，无原生资源清理责任。合法完整policy窗口及稳定元数据仍是未来实际调用点需审查的前提，公共观察检查不冒称初始化证明。
- 本步四文件已完成静态审查并冻结交回，未编译/运行/动态验收；Retention/Build.cs/GameMode及四份图文继续冻结。C15开放；新增未接入接口的局部图文同步由统筹后续另租约安排。

## 09-G1 Loaded 加载与保留（2026-10-03 四文件租约，已交回冻结）

- 唯一写入者：GameFeature 长期组长 01a0e5b5-9dc9-7b32-8aaa-3316137b0cc9，按用户最新 gpt-6.1-sol / ultra 直接执行；统筹基线中的旧档位不覆盖用户最新约定。
- 授权：统筹接受 01a1000e-0c8e-7230-bb6e-589c83a4f817 预检；基线 Saved/ValidationRecords/GameFeatureLoadedLoading_LeaseBefore.json。实施前仅登记，未完成或编译；实际交回状态见本节末尾。
- 精确文件：Source/GGYGO/GameModes/GGYGOGameFeatureRetention.h、.cpp；本记录及同目录 Module_Repair_09_Validation.md。无第五文件写权。
- 唯一目标：现有 Retention 的同一原生 Loaded 句柄加载显式托管的完整闭包；关闭立即拒绝新请求，已接受的原生批次完成并返回后才允许释放句柄。
- 共享契约：新增 LoadAndRetainValidatedManagedClosure(TConstArrayView<FString>, FLoadCompletion)。调用方必须先证明完整 GFP 闭包、全部显式托管来源、当前 policy 的完整合法加载窗口；现有 Resolver 的候选结果本身不提供此许可。本步不取得或缓存 policy、不承诺任意阶段安全。
- 所有权：引擎 Controller 唯一聚合插件引用与状态；本资源仍只有一个 None-options Loaded handle。每批仅持有自有 URL、原生结果与完成记录，原生委托强持资源到完成；不是插件状态或人数缓存。
- 顺序：登记与基线核对 → h/cpp 实现同句柄逐 URL 原生 Load → 有限 API/生命周期复核 → 两记录交回证据 → 四文件冻结停止。
- 验收断言：输入先复制去重且空/空白 URL 在原生调用前拒绝；开放期间全部传入 URL 均交给原生 Load（包括闭包 false 依赖）；关闭/前提失效停止尚未发出的 URL 并显式 Interrupted，已发项逐个实际回调排空；原生错误不变成成功，缺回调保持未完成；全部真实完成且状态稳定才发布 Loaded；同步回调先记结果，所有原生调用返回后发布；关闭期间重复 Release 不覆盖原通知，PendingLoads 清空前不得注销 handle；迟到或重复完成不再次发布或更新注销后的项目资源。
- 非目标：GI/session/Active/GameMode/Experience/Resolver/借用保护、配置/资产/测试/Obsidian/全局/Build/UE/Git/子代理。调用方和图文待统筹另租约同步，C15 与旧 GameMode 失败放行仍开放。
- 停止点：有限实现复核后四文件交回冻结；新策略、上游共享接口或第五文件立即交回，不自扩范围。后续调用链冻结后由统筹编译与必要 UE 冒烟，不开展严格矩阵或插件夹具。

### 09-G1 实际交回：四文件冻结

- 新入口已实现，仍由原 StateHandle（None-options）独占 Loaded 要求；无新原生句柄、宿主或插件状态事实源。ELoadStatus 区分 Rejected/Loaded/Failed/Interrupted，结果为自有 URL/错误值。
- 原生加载采用单 URL Controller 接口逐项提交，同批 PendingURLs 仅记录尚未真实回调的请求。注册批记录及每项 pending 均在调用前；同步回调不外发，所有提交调用返回且真实 pending 清空后才发布结果。
- 每次提交先复核开放/原生条件；关闭或条件失效停止未发 URL，明确 Interrupted（已有 native 错误保持 Failed）。已发项不全局取消或假完成；每项 native 原错误与附加原因保留，Loaded 还需全部实际结果成功及稳定 Loaded/Active 观察。
- 首次 Release 先关闭准入并保存原通知；原生调用未返回或任何已发项未完成时不注销 handle，重复 Release 仅一次 Pending 不替换首通知。批记录排空才走原同步/异步释放终态契约。
- 有限复核完成：原 TryCreate/RetainAlreadyLoaded、可用性 helper、原生释放完成/终态及独立析构等十个旧方法体在统一换行后保持；没有生产调用方、新测试、编译或 UE 结果。
- 源码冻结：h 2536E283875E735EF3D62EA25FC1291426DAC7CC1B31DECAC1E5FD58B9A065A3；cpp 8B43A72913244C03FE07D24937421189B9FCBAB68313D2279768A9010A9C1054。仅本四文件写入；同批 Combatants 变化属统筹并行租约。
- Obsidian 已只读核对，本步新接口/未编译状态和逐项 pending 清理尚待统筹另租约同步；本会话无图文写权。GI/显式来源配置/Active 会话/GameMode/借用保护均待后续分阶段实施，C15 和旧 GameMode 错误放行未关闭。
- 当前四文件冻结停止；后续由统筹统一编译与必要 UE 冒烟。缺失实际 native 回调保持请求未完成，不用超时或析构汇总伪造完成；基础设施拆除/动态 CVar 仍不保证清理。

## 09-G2 GI Loaded 薄宿主（2026-10-03 四文件租约，已交回冻结）

- 授权：统筹接受 01a10035-6fd5-7172-9dc8-ef830be4fc13 预检；基线 Saved/ValidationRecords/GameFeatureGILoadedOwner_LeaseBefore.json。GameFeature 组长直接执行，按用户最新 gpt-6.1-sol / ultra；实施前仅登记，无编译/运行结果。
- 精确范围：新 Source/GGYGO/GameModes/GGYGOGameFeatureSubsystem.h、.cpp；本记录及同目录 Module_Repair_09_Validation.md。Resolver/Retention 及 Experience/Session/GameMode 全部只读，无第五文件写权。
- 唯一目标：一个 GI 普通 owner 持有现有 Retention；显式完整托管输入经 Resolver 接到 Loaded 入口，以只读原 World 租期保护 pending/未来 Active，跨地图保留 Loaded，GI 结束关闭准入并撤销宿主持有，最后租期归还后释放。
- 冻结公开入口：PrepareManagedLoadedClosure(const UWorld&, FGGYGOGameFeatureClosureResolver::FInput, FPrepareCompletion)；FLoadedLease 为 TSharedPtr<const FGGYGOGameFeatureLoadedLease, ThreadSafe>，完成参数为原租期和 const Retention::FLoadResult&。租期仅 GetRootPluginURLs()/IsAdmissionOpenFor(World)，不暴露 Retention、原生 handle 或 Release；无 Blueprint 加载/释放入口。
- 唯一状态/清理：普通 owner 的 closing 仅描述本 GI 准入；GI/租期共享内存寿命不成为原生使用人数或插件权威。pending 完成闭包强持原租期，未来 Session 另须持到自身 Active/pending 清理完成；owner 最后销毁调用既有 ReleaseOwnedReferences，不捕获已结束 GI/World。
- policy 前提：仅当前正常引擎创建 Game/PIE 生命周期同步取得实际当前 policy，调用 Resolver 后不保存。Engine/AssetManager 初始加载先于 GI 初始化，GI 关闭先于 Engine subsystems 拆除；公共指针/identity 检查只拒绝不兼容，不证明 Ready。手工/RPC GI、动态重载、初始化/关闭重入与不稳定元数据不纳入契约；SkipAssetScan、错误线程/World、退出或 World 拆除明确拒绝。
- 验收：缺来源/Borrowed 在 native load 前拒绝，无默认托管或 IsActive 来源猜测；每 GFP Loaded URL 全量传入原核心；成功回调交已构造原租期，失效 World/GI 的迟到成功转 Interrupted 并交空租期；Deinitialize 不阻塞/提前释放，被 pending/未来 Active 持有的 owner 继续存活。
- 顺序：本登记 → h/cpp 普通 owner/租期与原生桥接 → 有限源码/API/范围复核 → 两记录交回 → 四文件冻结停止。非目标：显式 Experience 配置、Session/Active/GameMode 生产调用方、借用保护、测试/严格矩阵、Build/UE/Git/资产/Obsidian/全局/子代理。
- 停止点：公共契约不足、新策略或第五文件先停交回；代码冻结后由统筹统一编译和必要 UE 冒烟。C15 与旧 GameMode 错误放行保持开放；新接口/状态的图文同步另租约。

### 09-G2 实际交回：GI 宿主和原租期已编码，四文件冻结

- UGGYGOGameFeatureSubsystem 自动创建于 Game/PIE GI collection；ShouldCreateSubsystem 只选择正常 WorldType，Initialize 创建一个普通共享 owner 和原 Retention。无需自定义 GI 类或配置，未新增原生 handle。
- PrepareManagedLoadedClosure 直接调用冻结 Resolver，再要求所有 Nodes 为 ProjectNativeManaged 且无 Borrowed；完整 Nodes URL 接到原 Loaded 方法，包括 shouldActivate=false 依赖。根 URL 只作为本请求不可变快照进入只读租期。
- policy 仅同步 GetPolicy 一处，无保存、ready 缓存或私有状态探测。新增只读 System/AssetManager 依赖：限定实际 exact UGGYGOAssetManager，并读其既有 HasCompletedSharedAssetPreload 启动尝试完成快照作为额外拒绝条件；该 provider 的 StartInitialLoading 先调用 Super。其完成不代表资产成功或独立 native policy Ready，合法窗口仍来自正常 Engine/GI 真实顺序；自定义 provider/子类不在本受限路径。
- Pending completion 强持完整原租期，回调不捕获 subsystem/World/GI 裸对象；原 World 弱身份、当前 Context/拆除与 owner closing 再校验。只有 Loaded 且原准入仍开放才交付租期，其余交空租期；晚到成功转 Interrupted，原 native 失败不改成成功。
- Deinitialize 先 owner closing 后撤 GI 持有，不释放仍被租期持有的资源、不阻塞等待；最后 ordinary owner 析构才调用 Retention::ReleaseOwnedReferences。清理不读已结束 GI/World，错误线程最后归还明确诊断并由既有 Retention detached cleanup 接手，无新增调度器。
- h 80 行，SHA256 134A3A56C19FB952BB103463177AFE9C80BE99167D8C4EE629E8235EFEC9AE08；cpp 347 行，SHA256 136A2E6C2F968C5DB20CC9C7E1690121D999B686053EC3F059745766371E72B2。仅本四文件写入，核心/配置/调用方保护保持。
- 有限完整源码/API/持有图与范围自查已完成；未编译或运行 UE。核心已有 GI C++ 调用点，但 Prepare 仅声明/定义，Experience/GameMode/Active Session 尚未消费。未来 Session 必须在自身 Active/pending 释放流程完成前持有租期，本步未实现该消费链或借用保护，C15 开放。
- Obsidian 只读核对保持；GI/原租期及 G1 新入口的已编码未编译事实尚待统筹另租约同步。四文件立即冻结交回，后续统一编译及必要 UE 冒烟由统筹安排。

## 09-G3 Experience 显式来源配置：实施前登记（2026-10-03）

- 唯一写入者：GameFeature 长期组长 01a0e5b5-9dc9-7b32-8aaa-3316137b0cc9，按用户最新 gpt-6.1-sol / ultra 直接执行，不创建子代理。
- 授权：统筹接受四文件有限预检，基线 Saved/ValidationRecords/GameFeatureExperienceSourceConfig_LeaseBefore.json；排程及审计账本已登记本精确范围。四文件写前 SHA256 均与基线一致。
- 精确四文件：Source/GGYGO/GameModes/GGYGOExperienceDefinition.h、.cpp；本记录；同目录 Module_Repair_09_Validation.md。第五文件、额外所有权策略、共享契约扩展或实质兼容决定即停交回。
- 唯一目标：Experience 保存显式来源，并用原生 TryBuildGameFeatureInput(FGGYGOGameFeatureClosureResolver::FInput&, TArray<FString>&) const 同步校验形状、复制配置；失败无部分输出。现有 GameFeaturesToEnable 名称/类型/序列化与 Squad 规则保持。
- 冻结数据契约：反射 EGGYGOGameFeatureSource 的 Unspecified/ProjectNativeManaged/ExplicitExternalBorrow；FGGYGOGameFeatureSourceDeclaration 三字段 PluginName/Source/ExternalOwnerLabel；反射 GameFeatureSources 数组，来源默认 Unspecified。没有隐式 Managed、根来源继承或自动修正字符串。
- 责任与依赖：Experience -> 无状态 Resolver 的值类型；配置转换和编辑期形状校验共用同一函数。完整依赖闭包、URL、未使用声明及生产准入仍由既有 Resolver/GI 唯一负责，Borrow 配置不代表保护/准入，GI 继续拒绝 Borrowed。
- 生命周期：接口同步，无原生调用、回调、句柄、计时器、Ready 或插件状态；只有调用内派生值，无资源清理责任。失败清空 OutInput，OutErrors 提供 GameFeature 模块、Experience 路径、字段和原索引。
- 顺序：登记 -> h/cpp 配置及纯值转换 -> IsDataValid 复用 -> 有限全文/形状/原 Squad/保护范围静态核对 -> 两记录证据 -> 四文件哈希交回并冻结。
- 验收断言：两数组全空合法正常无 GF；只有来源而无根拒绝；空白/首尾空白、缺来源、未知枚举、非法 owner label、来源冲突拒绝；完全相同重复项稳定去重；失败输出为空且可定位；不产生 Native/GI/Active 执行或新权威状态。
- 只读依赖：冻结 Resolver h/cpp、GI h/cpp、Retention h/cpp、GameMode h/cpp；本轮协调记录；Obsidian 计划蓝图与 GameFeature 四份图文。
- 非目标：非空资产完整闭包声明迁移、Active 会话、GameMode/Teams 门禁、原生加载、编译/UE/Git、测试矩阵、Obsidian/全局文件。新接口暂无生产调用，旧 GameMode 失败仍装配问题不在本步关闭，C15 开放。
- 迁移与后继：旧非空根资产保留序列化，但未来调用新入口时须补完整 GFP 闭包的显式来源；本步零资产读写/保存。下一原子另租约实现原 World Active 资源，再经 Teams 冻结交接修改 GameMode 真实成功门禁。
- 登记时状态：登记完成，实施中；当前交回状态见下节。静态完成不代表编译、资产迁移、生产接线或整体策略验收。

### 09-G3 实际交回（四文件已冻结）

- 已实现反射来源枚举、三字段声明、GameFeatureSources 和同步 TryBuildGameFeatureInput；Unspecified 为存储默认且配置时拒绝。保留旧 GameFeaturesToEnable 的原 UPROPERTY/类型与 Squad 字段、校验全文；更新原“未启用内容完全不参与加载”注释，区分完整闭包 Loaded 与本局 Active。
- 校验开始清空两个输出，仅全部形状合法后移动完整 Candidate 到 OutInput。两数组全空正常成功/空输入；仅来源无根、空/首尾空白名字、缺合法根声明、Unspecified/未知枚举、Managed 非空 owner、Borrow 空/首尾空白 owner、冲突重复明确失败。相同根/声明保持首次顺序去重，不改变原配置值。
- IsDataValid 真实复用新函数；所有错误带 [GameFeature]、Experience 路径、字段和原索引。配置阶段不查询依赖/URL、不执行 Native；Borrow 值仅逐项映射，现有 GI 拒绝策略保持，标签不是保护证明。
- h 121 行，SHA256 4AB8158B413BB779C0EC4D386E156AA70F383F0C4CEBC4DB4F825D8B09E80070；cpp 203 行，SHA256 8BB6F3F333A48EA3A5DD16CF658D4078C246B7BEE65194CB502594F595FC3826。源码有限全文自查完成，未 UHT/编译/UE。
- Source 检索只有声明、定义及 IsDataValid 调用，尚无运行时场景输入消费；GI/core/GameMode 八源码和四份 GF 外部笔记哈希与本轮读前一致。两记录历史前缀保留；本会话只写授权四文件，未接触同期 Health/ASC 写入。
- 架构：新增仅配置/临时转换值，Experience -> Resolver 值定义，无 GI/World 反向依赖、生命周期、第二插件状态或执行链；原生成门禁问题没有被本步修复。
- 迁移未实施：已有非空 roots 资产在新校验下须补完整闭包来源，无自动默认/继承；编辑期形状 Valid 仍非完整闭包/加载成功。后续会话应识别合法两空配置的正常模式，不把空输入交给要求非空闭包的 GI 入口。
- 后继精确候选：另租约新 GGYGOGameFeatureSession.h/.cpp 加本两记录，实现原 World Active/pending 资源并持原 Loaded lease 到收尾；再经 Teams 冻结交接租 GameMode h/cpp 加本两记录，迁移真实装配门禁。当前未授权这些文件，C15/联机/插件生命周期验收开放。
- Obsidian 核对后交统筹待同步：Experience 新三字段来源/数组/原生接口、同一编辑期形状校验、空配置正常与旧非空资产未迁移、配置值不授 Borrow/Ready；结构和流程图只画已编码未编译的配置入口，保留 Active/GameMode 未接通。按本租约不写外部笔记或全局入口。
- 四文件立即冻结交回；无第五文件/资产/测试矩阵/Build/UE/Git/子代理写入或执行。统一编译与必要 UE 冒烟由统筹安排，整体“只停用、不卸载”没有标完成。

## 09-G4-0 原租期不可变激活 URL 集合：实施前登记（2026-10-03）

- 唯一作者：GameFeature 长期组长 01a0e5b5-9dc9-7b32-8aaa-3316137b0cc9，gpt-6.1-sol / xhigh；Fast 本机默认，不能追溯声称当前已发请求切换。无子代理。
- 授权：用户最新纯技术过目不阻塞约定及统筹接受既有四文件预检；基线 Saved/ValidationRecords/TechnicalAutonomyBatch_20261003_LeaseBefore.json，排程/审计账本已登记。四文件写前哈希与基线一致。
- 精确范围：Source/GGYGO/GameModes/GGYGOGameFeatureSubsystem.h、.cpp；本记录；同目录 Module_Repair_09_Validation.md。第五文件、新业务/兼容取舍、引擎修改或扩大生命周期即停交回。
- 唯一目标：现有 Loaded lease 新增 GetActivationPluginURLs() const 的不可变请求集合，仅来自本次已验证 Closure 值；原 GetRootPluginURLs 和 Loaded 资源/租期生命周期不变。本步只关闭共享值合同，不实现 Active 会话。
- 根因依据：本机 native CollectDependencies 对已经遇到的依赖升级需求后直接 continue，不重走子树；R 的依赖顺序 A(true)、B(false)，B->C(false)、A->C(true)、C->D(true) 时，先沿 B 走完 C/D，再沿 A 升 C，D 未跟随升级。仅为源码推导，无动态复现；不修改或重审整套引擎/Policy/Loaded 矩阵。
- 已决定纯技术方案：GI 从现有 Resolver FResult 的 Nodes/DependencyEdges 生成根与 true 边可达集合，提供给未来会话明确登记自有 Active 请求；false-only 节点继续只在既有完整 Loaded 闭包。节点若本身是根或另有 true 路径则加入；不因先见 false 路径遗漏 true 子树。
- 所有权/依赖：Resolver 继续唯一产出已验证闭包；GI 仅作调用内值选择，租期保存自有字符串快照。Native Controller 继续唯一聚合引用/转换状态。新数组不是实际 Active、Ready、人数或资源句柄，不赋予 Borrow 保护/准入。
- 精确顺序：基线核对及本登记 -> private lease 构造参数/const 值字段/只读 getter -> cpp 本地纯值生成 -> 既有全 Managed/无 Borrow 校验后、Loaded 调用前构造完整值 -> 有限静态全文与旧路径保护核对 -> 两记录证据 -> 四文件哈希冻结。
- 验收断言：全部根入集合；只沿 true 边扩展；多根/菱形路径稳定去重；节点和边 URL 非空/匹配，缺节点或 URL 拒绝且无部分输出；已解析 false 边节点仍留在原全 Nodes Loaded 输入。生成值在同步 Loaded completion 前完整构造，原成功/失败/迟到/closing/last-lease 行为不变。
- 生命周期：输入和临时索引仅活在同步调用内；private const 字符串数组随原租期销毁；view 仅在持有租期时有效。无新增回调、Native 调用、Ready 状态、计时器、帧循环或清理机制。
- 只读依赖：冻结 Resolver/Retention/Experience/GameMode h/cpp；native ReferenceController 的有限根因源码；协调基线/排程/账本；GameFeature 两 MD/两 Canvas 和计划蓝图。
- 非目标：Session/Active 句柄/执行、GameMode/Teams 接线、Borrowed C15、资产迁移、测试夹具/矩阵、Build/UHT/UE/Git、Obsidian/全局文档。旧生产问题和动态根因证明继续开放。
- 登记时为实施前状态；实际交回见下节，只交共享值合同，不能标记生产接入、编译或整体“只停用、不卸载”完成。

### 09-G4-0 实际交回（四文件已冻结）

- Loaded lease 已增加 GetActivationPluginURLs() const，返回 private const TArray 的只读 view；构造时移动自有字符串数组，Root getter/原 World/owner 持有不变。view 不授 Native Active 或 Ready，只在原租期有效期间使用。
- cpp 本地 TryBuildActivationPluginURLs 只读本次 Closure 值：先检节点名/URL/唯一名及全部 GF 边的节点/URL一致性，再从全部根只沿 true 边遍历。调用内 Visited 按节点去重，URL AddUnique；当前插件名先复制，避免追加 pending 数组导致引用失效。
- false-only 节点不入激活集合；若本身是根或另有 true 路径则纳入并继续展开。缺节点、空/不匹配 URL、异常重复节点或空根集合均明确拒绝；输出先清空，完整成功才移动 Candidate，无根集合替代或部分输出。
- 新值生成接在既有全 Managed/无 Borrow 校验和根值收集后、原最终 World 准入及原 Loaded 调用前；完整构造租期后才进入可能同步的原加载入口。原 Nodes URL 全量加载（含 false 节点）、Policy窗口、迟到/关闭/最后租期释放保持。
- h 89 行，SHA256 3690CFF79035E8BA859D3CE3F8A820F502B706B7F8DF16FA927008FE7A496EB2；cpp 434 行，SHA256 9F54E07DF48CBB3C6D8C16AD1AAB43C473979120F903942538A82482FC905310。
- 有限静态复核：移除本次本地生成函数/getter/构造参数与接线增量，cpp 统一换行全文逐字还原基线；新增函数无 Native 调用，原 Root/准入/来源/Loaded/收尾代码保持。Source 检索 getter 仅声明/定义，无场景消费；生成函数仅定义及本 GI 一处调用。
- 两记录历史前缀保持；Retention/Resolver/Experience/GameMode 八源码、native Controller cpp 和四份 GF 图文共13保护哈希与读前一致。本会话只有授权四文件写入，不声称并行其它作者/全仓库保持。
- 架构核对：同步临时节点指针/集合退出即销毁，无指针存入租期；新 const 快照仅派生请求值，生命周期随原 lease。没有新 Native 句柄、引用人数/Ready/插件状态、循环依赖、调度器或独立释放机制。
- 尚未运行 UHT/编译/UE、专项/联机/资产验收；原生 collector 问题仍是静态推导，未伪造复现。共享值只补会话输入，Session/Active flat 引用登记、GameMode门禁及 C15 未实现，整体目标未关闭。
- 后继另租约：新 Session h/cpp 加原两记录消费根/激活 view；其原 Native Active 资源与 pending 清理完成前保留 Loaded lease，根激活前按完整激活集合明确登记自己的 Active 需求。随后 Teams 冻结交接 GameMode h/cpp。无 GF 正常模式继续由成功配置结果的上层处理，原 GI 空闭包拒绝不变。
- 交统筹图文待同步：lease 新 getter/不可变激活请求值；完整 Loaded 与 true 可达 Active 请求的区别；有限静态 collector 根因、选择 flat 自有需求的后继方案；当前已编码未编译/无消费状态。两结构/流程 Canvas 只同步这些事实，不画成 Active 生产已接通。本租约不写 Obsidian/全局入口。
- 四文件立即冻结交回。无第五文件、Native新增执行、引擎/资产/测试矩阵/Build/UE/Git/全局/子代理操作；后继源码消费者、图文与统一编译/必要冒烟由统筹另排。

## 09-G4-1 原 World 薄 Active 会话：实施前登记（2026-10-03）

- 作者：原 GameFeature 长期组长，gpt-6.1-sol / xhigh；Fast 本机默认，无子代理。统筹接受有限刷新预检并登记租约；基线 Saved/ValidationRecords/GameFeatureActiveSession_20261003_LeaseBefore.json。
- 精确四文件：新 Source/GGYGO/GameModes/GGYGOGameFeatureSession.h/.cpp；本记录；Module_Repair_09_Validation.md。新源不存在，两记录写前 SHA256 与统筹基线一致。
- 唯一目标：一个普通共享 C++ 会话，完整实现 Start -> 原 GI Loaded -> 自有一个 None-options Active handle -> Ready/Close；生产机制真实调用冻结 GI/Native 接口，不写空准备层。上层 GameMode 消费另原子，不能提前标接通。
- 冻结接口：TryCreate(const UWorld&, const FString& Label, FString& Error)、一次 Start(FInput 按值, FStartCompletion)、IsReadyFor(const UWorld&) const、Close(FCloseCompletion)。Start结果Ready/Rejected/Failed/Interrupted；Close结果Closed/Failed/Unconfirmed/Pending/RejectedWrongThread。
- 责任：原 World/GI 弱身份、Loaded 原租期、自有 Active GUID、真实在途回调/调用返回与自身终态；Native Controller 唯一聚合插件状态/引用。无项目插件状态机、人数或第二调度器，request集合不证明状态。
- 顺序：本登记/基线 -> h接口与自有资源 -> cpp创建/一次Start/原GI准备 -> 完整激活集合显式Add Active(false) -> 单URL逐根激活 -> 实际资格检查 -> Close/drain/释放/独立析构清理 -> 有限静态复核 -> 两记录证据/四哈希冻结。
- 同步断言：创建方先保存完整会话再Start；GI准备调用返回、整批激活派发返回及真实pending均完成前不能Ready/释放。回调持原资源，外部通知退役后再调用，显式Close撤销旧观察者；重复Start/Close不启动第二执行链。
- 成功断言：原GI真实Loaded+原租期、全部真实根结果成功、完整GetActivationPluginURLs实际为Active、原World/lease开放；void Add仅请求登记，不当作ack。失败停未发项，已发实际排空，原native错误不被Interrupted覆盖。
- 清理断言：只释放自有handle；真实Release回调与调用返回/句柄注销后才归还lease，bool失败如实Failed；异常基础设施/回调缺失为Unconfirmed或实际pending，不伪造完成。独立析构记录持移出的同一handle/lease，原Session无裸this/AsShared析构捕获。
- 只读依赖：冻结GI/Retention/Resolver/Experience/GameMode十源码、Native公开签名和有限移除引用次序；GF两MD/两Canvas及计划蓝图。保护快照15项，不涵盖其它作者的全仓库变化。
- 非目标：GameMode/Teams/ASC/Movement/Engine写入、Borrowed政策/C15、空配置GF成功替代、资产/夹具/矩阵/Build/UHT/UE/Git、Obsidian/全局入口。纯技术细节由组长决定；第五文件/业务兼容取舍即停交回。
- 后继链：Teams冻结交接 -> GameMode h/cpp加原两记录，配置转换成功后两空明确正常模式；非空先保存Session再Start，真实Ready才装配当前玩家，EndPlay Close。记录与图文/编译/UE/资产状态分别验收。
- 登记时状态：实施前；完成后仅本资源生产机制与GI/Native桥接冻结，尚无GameMode调用，C15与整体策略开放。

### 09-G4-1 实际交回（四文件冻结）

- 新普通共享Session已完整实现TryCreate/一次Start/IsReadyFor/Close。创建只绑定原World/GI弱身份和诊断Label；Start真实消费冻结GI Prepare及两个lease view。Native Active handle只在真实Loaded后初始化一次，None-options；完整true可达集合先Add Active(false)，再逐根单URL激活。
- 成功不是void登记：真实根回调均成功且pending为空，GI准备调用及整批激活派发返回后，查询完整集合实际Active并再次确认原准入，才发布Ready。IsReadyFor继续查本操作终态/原身份/lease/原生状态，不保存插件状态。原生错误代码及可选文本保留，Failed优先于关闭/迟到Interrupted。
- Close撤销旧Start观察者、停止未发项；实际准备/根回调排空且调用返回后才原生Release。同步Release回调先记录，返回/注销后交终态并归还lease。bool false为Failed，不写Closed；原生源码显示自身引用在降级前撤回，因此正常guard下实际失败回调/注销完成后归还租期，降级失败仍明确可见。
- 自身终态在lease归还前记录，防止最后GI租期触发Native/user重入而再启动清理。重复Start拒绝；重复Close进行中仅一次Pending，终态重放且不重试Native。关闭/原场景失效抑制Start通知；外部消费者须用弱观察者及原会话身份校验。
- WorkKeepAlive只保真实未完成工作；正常Ready或完整Close终态清除。实际回调丢失不会假完成，资源/lease仍被原工作记录持有。native服务/动态lifetime异常为Unconfirmed，资源保留，最终独立清理记录也可能保留至进程结束；这是明确失败/内存占用边界，无静默重试或业务成功替代。
- 析构移动同一handle/lease到cpp独立清理记录；不AsShared、不捕获原this/World/GI。GT直接启动或一次转既有Core GT队列，记录持lease到真实Release回调+调用返回；丢失guard/GUID清理未确认时可见诊断且不提前归还。Normal/Detached两个释放入口对同一移出GUID互斥，没有第二Active执行链或句柄。
- h 110行，SHA256 EBD29C5F036F2D368F1C5C8B34EE07B85C0074A0022031E0B9E0A996F7ED1CF7；cpp 544行，SHA256 E251C08A0ACAA4CB89E119462219DB8D44C25AE7A33557C00E39A327515924EA。
- 有限全文/ABI/同步-迟到-重入/清理静态核对完成。Source范围仅新h/cpp引用该类；暂未有GameMode调用。15项只读保护与本轮基线一致，两记录历史前缀保持；没有引擎/GI/core/其它模块改写。
- 架构核对：Session只持本资源请求/回调/终态和原Loaded租期，Native唯一聚合插件状态/引用；无policy获取/闭包重建、人数、Native插件状态机、Tick/Timer/第二调度器。独立清理按最后资源生命周期拆在cpp记录中，未泄漏原生句柄或GI内部状态。
- 当前只完成资源实现及GI/Native桥接源码；未编译/UHT/UE/动态复现/资产/联机。原生插件全局Action的World过滤未在本步扩展，独立PIE Action隔离与联机保留未验。Borrowed仍由GI拒绝，C15与整体“只停用、不卸载”开放。
- 后继唯一生产消费者：Teams冻结交接后租GameMode h/cpp加原两记录；配置转换成功后两空走明确正常模式，非空先保存Session再Start，用原Session IsReadyFor控制所有装配入口，EndPlay Close/撤自身持有。旧裸激活、失败仍spawn、计数门禁仍待该原子关闭。
- 交统筹待图文同步：Session类/API、原World弱身份与一个Active GUID、flat集合登记/真实根结果/双返回门禁、关闭排空/Active先于lease、移动析构记录和未确认持有边界；G4-0 view已有Session源码消费但无GameMode调用，已编码未编译不作生产完成。当前四文件立即冻结，无第五文件/测试矩阵/夹具/Build/UE/Git/资产/Obsidian/全局/子代理操作。


## 09-G4-2 GameMode实际消费原Session：实施登记（2026-10-04）

- 统筹已接受零写入预检01a10283-33d8-7bb3-aea8-94885cf3a7e2；本纯技术接线直接实施。唯一作者为原GameFeature组长，gpt-6.1-sol／xhigh，无子代理。租约：Saved/ValidationRecords/GameFeatureGameModeConsumer_20261004_LeaseBefore.json；四文件写前hash匹配。
- 精确范围：Source/GGYGO/GameModes/GGYGOGameMode.h/.cpp、本记录、Module_Repair_09_Validation.md；GameMode为本原子独占，Teams当前无写权，四份冻结后再交接。
- 唯一目标：GameMode真实消费冻结Experience／Session／GI，闭合一次启动、原成功资格装配及EndPlay自身关闭；不建准备层或第二套插件Ready／pending。
- 冻结依赖：Experience的TryBuildGameFeatureInput；Session的TryCreate／Start／IsReadyFor／Close；GI跨图Loaded合同。GameMode→Session→GI→原生，接口与权威归属不改。
- 顺序：登记→两源码完整生产实现→有限静态核对→两记录证据→四hash冻结交回。初始化成功转换才判两空正常无GF；非空先保存完整Session再Start，真实资格只读同原World Session。
- 断言：失败空Input／空Session／缺Experience不得放行；同步失败交ErrorMessage，异步不捕获其栈引用；弱原GM／Session／World身份核验，迟到不影响新会话。当前Controller仅局部弱快照，入口与外调返回复核。
- 清理：EndPlay先关闭调用方准入，移出并Close自身Session，再Super；不释放GI保留。项目仅持本资源与本调用方的启动／关闭／正常配置选择，不拥有插件状态。
- 非目标：SpawnSquadForPlayer／SpawnSquadSlot／SpawnSquadMember三个正文、Teams创建资源与选择／切人、其它源码／引擎／资产／联机／Obsidian／全局／Build／UE／Git／夹具／严格矩阵。
- 停止点：需要第五文件、修改冻结接口或玩法兼容决定即停；三个Spawn内部重入／部分创建与Teams回收仍属后继，不能宣称本步解决。Build56实际失败只剩Hero旧三调用，未运行时链接／未UE，不作为新消费者验收。

### 09-G4-2 实际源码交回（2026-10-04，有限静态核对）

- 实际消费者已编码：InitGame一次启动；缺Experience／父级初始化错误／无效原Game／PIE World与GI准入／配置转换失败明确拒绝并交同步ErrorMessage。TryBuild成功后才判根与声明两空正常无GF；非空TryCreate→先保存完整Session→Start，源中仅一处Start。
- 删除旧PendingGameFeatureCount、裸UGameFeaturesSubsystem激活、GetPluginURLByName跳过和OnGameFeatureActivated失败仍放行；AreGameFeaturesReady仅选择已成功确认的无GF模式，或读原Session.IsReadyFor当前资格，不复制插件Ready／pending。
- 私有字段仅原Session共享持有、调用方一次启动／封闭准入及成功配置选择。临时共享FString只传同步诊断；实际接收者按值捕获弱GM／World／Session和该字符串，不捕获ErrorMessage／this栈引用，也不强持UObject。异步失败诊断一次并关闭调用方准入；Session按冻结合同自行真实排空。
- 身份门禁核GT、原有效World／当前GI、Game／PIE、实际AuthorityGameMode及同一个Session；旧World、关闭或替换拒绝，不清新会话。仅收到Ready仍须实时资格通过；若已失资格，拒绝装配并Close原资源。
- SpawnSquadForPendingPlayers仅快照当前Controller为局部弱数组，逐个调用前、外调返回后重读弱原GM／World并核Session资格；NewPlayer入口同样防旧身份。没有持久等待Roster、Timer／Tick、自动retry或新调度器。
- EndPlay GT先关闭调用方准入、撤正常配置资格，MoveTemp移出自己的Session后Close，最后Super；错线程明确拒绝、资源不变。GM不读取／释放GI内部owner或native handle，跨图Loaded仍归原GI／租期。
- 两源码已保存回读：h 94行／A82D61CDA84FAD8E821A17B4E32D27DC498072C772BC4D0C4E76F10A4A713311；cpp 535行／B17F75D06AB3B2FAFF1C594D8F55ADE18BE1933BA045B65CFDEF35EEE5942906。三个受保护Spawn及整个后缀逐字相等；原构造与Roster helper除显式include变动外逐字相等。六冻结源及GF N3四图文共10保护hash保持。
- 架构核对：GameMode→Session→GI／原生，无反向依赖、插件状态／引用人数或第二执行链；配置模式不是Active缓存。资源移出先于外部Close，实际pending由原Session保活，析构沿冻结独立清理；未新增裸UObject保活或清理机制。
- 有限证据只为源码合同与保护比较，不是编译／动态通过；未运行新UHT／Build／UE／资产／联机／严格矩阵／夹具／Git。历史Gate55／56失败不改写，最新56仅Hero旧三调用报错、未新运行时链接，发生于本增量前。
- 边界：三个Spawn内部重入／部分生成、Teams创建资源交付／统一回收、存档／默认名单选择和切人全保持旧正文，未承诺关闭。Borrowed仍由原GI拒绝，C15、实际GF资产接线、真实停用／切图／PIE Action隔离／联机仍开放。
- 本批只源消费及两局部记录；GF Obsidian／Source README仍需统筹同任务后继租约同步当前GameMode消费事实，本作者无该写权。全局进度、统一编译／必要UE冒烟、Teams文件交接由统筹安排；四文件交回即冻结，无第五文件或扩租约。


### 09-G4-2 Destroyed／EndPlay同原会话关闭补充授权（2026-10-04）

- 统筹完整回读后指出UE RouteEndPlay仅HasBegunPlay才调EndPlay，InitGame已建Session，BeginPlay前Destroy不能等GC收尾；纯技术生命周期根因在GameMode调用方入口，不改Session／GI。
- 原四文件同一作者继续独占；本次读前hash与前次冻结四份一致，统筹当前租约已补Destroyed／EndPlay。直接补override Destroyed，两入口共用唯一私有关闭消费者，Super前关准入并移出Close原Session；Super再触发EndPlay时无成员资源可重复操作。
- 不增资源状态／计数／清理器，三个Spawn正文、冻结接口、10只读保护与全部非目标保持。Native签名只读核对；本薄接缝完成后重新四份明确冻结，不编译／UE／Git／第五文件或矩阵。

### 09-G4-2 Destroyed薄接缝实际补齐（四份重新冻结）

- 新增Destroyed override；Destroyed与EndPlay均GT检查后调用唯一私有CloseGameFeatureSession，再各自Super。关闭消费者统一先bGameFeatureCallerClosed=true、撤正常无GF资格，再MoveTemp原Session并Close；外调后不Reset或读取后继成员，不增加字段／状态／清理器。
- 静态链：LevelActor原生Destroy调用Destroyed；BeginPlay前仍执行本消费者，不等GC。已BeginPlay时Super::Destroyed可RouteEndPlay回入本EndPlay，成员已移空，仅重复幂等准入封闭，不再次操作原资源。GT异常仍明确拒绝并保持资源，GI跨图Loaded不动。
- 两源码保存回读：h 97行／5D536A2E58E6490EA4EF2B93616FB62B7A36B98A7893CC9B816E9F260EA7A56C；cpp 554行／0D498F0B06B74BD247D67533D7FFE9079C8C4A1EBBF3BE5A9FD1252E89D42551。共享关闭区域以外的原消费／回调／资格／Controller代码逐字保持，三个Spawn及整个后缀逐字保持，四原私有字段无新增。
- 本条替代前段仅EndPlay作为正常销毁入口的当前完整性结论；前段源码hash与描述保留为补充前历史，不冒称BeginPlay前Destroy当时已关闭。有限检查而非运行反例，未新编译／UHT／UE／资产／联机／矩阵／Git；原未验、C15和后继图文／Teams范围不变。
- 同一原四文件重新明确冻结交回；源码在证据记录阶段冻结，后继共享GameMode写权仍须统筹交接。没有第五文件、冻结接口或引擎改动。
