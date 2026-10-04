# 第09批 GameFeature：验证与未完成项

更新：2026-09-30。09-G0-0 保留历史证据；最新 09-G0-1 见文末。

## 原基线与实际差异

- Build.cs 原 SHA-256：`FD4A48A575CEF3B1E9DFE6E12411AC9654F5C1C781D2332928F5C4BCE7F9BC61`。
- 写入前复读未变；两份09记录原不存在，本轮新建。
- Build.cs 冻结 SHA-256：`677F99C4CB6EE8FA3EB9B55A2A95AE12766E72B69C7CE474D5F7F914EE0E1A06`。
- 按当前磁盘全文比对，唯一增量为以下两行，位于 PrivateDependencyModuleNames 的 Json 后：

```diff
+            // GameFeature 依赖分类：IPluginManager / IPlugin 的公开接口来自 Projects。
+            "Projects",
```

上述 diff 以空格展示缩进；实际文件保持原有 tab 风格。删除新增两行后，完整文本与本步原基线相同，未覆盖或重置任何已有磁盘变更。

## 已实际执行的静态核对

| 核对项 | 结果 / 证据 |
| --- | --- |
| 显式依赖必要性 | Projects 公开头 `Interfaces/IPluginManager.h:667` 声明 `static PROJECTS_API IPluginManager& Get()`；真实 FindPlugin/IPlugin 接口归 Projects。 |
| 不能依赖私有传递 | 本机 GameFeatures.Build.cs 的 Projects 位于 PrivateDependencyModuleNames；GGYGO 原直接依赖列表没有 Projects。 |
| Private/Public 与重复 | 去除注释后解析所有 DependencyModuleNames 调用；Projects Private=1、Public=0，无重复依赖。 |
| 保护已有内容 | 保存前基线与读回全文比对：仅新增指定两行；既有列表、Editor 条件与 SetupIrisSupport 完全保留。 |
| 依赖层级 | 新增 GGYGO → Projects；Projects 公开依赖 Core/Json，部分 Editor 目标私有依赖 DesktopPlatform。DesktopPlatform 私有依赖 Core/ApplicationCore/Json。 |
| 循环边界 | 对本机 Engine/Source 的 *.Build.cs 检索未发现 GGYGO 引用；所查 Projects 及直接依赖不反向依赖 GGYGO，未新增项目静态循环。 |
| 文件与权限 | 仅本步三文件写入；其它源码、测试、配置、资产、全局入口及四份 Obsidian 策略文档保持冻结。 |

验证方法：PowerShell 只读快照/哈希、primary 源码读取、rg 检索及内存中的全文/依赖比对。不使用 Git diff，不执行 UBT 或 UE。完整构建和链接仍待统筹安排。

## 已确认的 native API 限制（不是本步实现）

- 编译默认 lifetime control=true；运行时值须后续准入核对。InitAndRegister 的 true 不保证 handle 有效，必须检查 IsValid。
- AddOrUpdateReference 返回 void；不能伪造原生成功回执。Loaded 保留必须覆盖实际已加载依赖，不能只依赖根的 TrackDependencies。
- 激活包装器在项目回调前登记 Active；Release 回调可同步/异步，动态关闭 CVar 可跳过引用移除，不能以回调 true 宣称安全回收。
- 普通插件/GFP 仍须用实际 IPlugin 与引擎路径判据核对；URL 失败不等于普通插件，IsActive 不等于项目所有权。

## 未验证、未实现与停止点

本步没有生命周期调用方：Retention、GI/session/GameMode 接线、外部借用、迟到回调清理、双 PIE/切图/依赖保留均未实现或动态验收。已有第19次构建与51/51是本次改动前的统筹门禁，不能证明新增依赖已编译。

C15 保持未关闭。普通 C++ 会话及薄 UGameInstanceSubsystem 仍为候选；最终范围保留外部借用，不新增全局协调器、项目使用人数或第二套调度器。

状态：09-G0-0 三文件静态核对完成、冻结交回；等待统筹审查及另行安排构建/后续授权。未运行 UE、构建、Git，未创建代理。

## 09-G0-1：实施前基线与验收范围

- h/cpp 在本轮开始均不存在；本轮将新建，不覆盖既有源码。
- Subleases 原 SHA-256：`ECC2767DE4A85AAA1A53E4F8EE452092E34AFCA9D5174F516B46F90F064B8AB0`。
- Validation 原 SHA-256：`4E784A8BA9EB2ECB2726CA4464AA8D72135BAE95690DF8FB8B4A55B14E6B9E9D`。
- 冻结 Build.cs：`677F99C4CB6EE8FA3EB9B55A2A95AE12766E72B69C7CE474D5F7F914EE0E1A06`；本轮只读。
- 统筹第20次完整构建 Succeeded（6 actions、30.58s）；常规51/51 Success，测试0 warning/error，06.56.28 UTC、0.446151853s，UE exit0且已退出。已覆盖 G0-0 Projects，发生在本核心新增前，不证明 G0-1 行为或编译。
- 已读本机 ReleaseAndUnregister：Reset 回调可早于 Unregister/UniqueId.Invalidate；handle 析构会再次调用 Release。实现必须在原调用返回前保活，避免同步用户回调导致析构重入。
- 稳定状态只接受 GetPluginState 恰为 Loaded/Active；不使用 IsGameFeaturePluginLoaded 的 >=Loaded 作为任意过渡/错误态证明。
- 后续静态核对：公开 API/类型存在、集合整批校验、每次提交前后复核、部分提交不弃置资源、重复与重入 completion、动态 CVar/退出失败语义、析构独立诊断、native 唯一状态权威及四文件范围。
- 当前状态：h/cpp 已实现、静态审查及读回完成；四文件冻结交回。未运行本核心构建、测试或 UE。已有四份策略文档继续冻结。

### 本步实际源码与接口

| 接口 | 输入 / 输出与失败语义 |
| --- | --- |
| TryCreate | 非空 OwnerLabel；game thread、非退出、lifetime enabled、InitAndRegister 后有效 GUID；失败返回 null 和 OutError。 |
| RetainAlreadyLoaded | 调用方已证明身份/依赖闭包/所有权的 URL 集合；检查非空和去重，整批稳定 Loaded/Active 后才提交。每次 native void 调用前后及整批结束均复核。Rejected=未提交；Interrupted=中途异常、本次可能已提交；Submitted=全部调用提交且所查前提保持，无 native ack。 |
| ReleaseOwnedReferences | 每个 completion 最多一次。Pending=重复请求即时结束，不登记等待观察者；Completed 的重复重放原结果。Released=原生 true 且调用返回/handle invalid/所查前提保持；Failed=原生 false；Unconfirmed=动态关闭/退出/错误回调线程等不能证实清理；RejectedWrongThread=本次无资源修改。 |

### 已执行静态审查（不等于编译或行为测试）

| 核对项 | 结果 |
| --- | --- |
| 本机类型/API | 已读 StateHandle/ReferenceController 的公开声明及完整 Release/Reset/RemoveReferences 顺序；ArrayView::IsEmpty、ThreadSafe TSharedFromThis/MakeShareable、AsyncTask(TUniqueFunction) 均在本机公开头存在。 |
| 词法与定义 | h/cpp 括号配对核对通过；三种实际入口均有定义，无后续未实现 API 声明/空桩。 |
| Loaded 登记 | None 选项、逐 URL Loaded,false；状态仅精确 Loaded/Active，无 >=Loaded 误判。完整集合检查先于首个 Add，引用登记前/后及结束均复核。 |
| 所有权与部分失败 | NumSubmittedURLs 仅每次返回结果；部分登记不自动释放，handle 仍归本资源。身份/完整闭包/管理权作为显式未完成准入前提，无 IsActive 所有权推断。 |
| 同步最后引用释放 | Release 入口先持有共享自身；closing/native-start 标记先于 native；同步回调只存原结果，调用返回后再 Finish/用户 completion，避免 Unregister 前析构再入。 |
| 异步及重入 | native lambda 强持有共享资源；终态在移出用户 completion 前存妥；重复 Pending 不增 observer/第二 native，完成重复仅重放原结果。 |
| 析构 | 无 AsShared/SharedThis/裸 this 捕获；移动成员 handle，native callback 只复制 Label/执行前提。通常已 invalid 的 handle 不再启动 native，engine exit 跳过仍报告未确认。 |
| 异常线程 | API 使用 game thread；ThreadSafe 仅内存保活。异常 completion/最终析构采用 Core 既有 game-thread 单次投递，不创建项目调度器。 |
| 失败真实性 | 动态 CVar 关闭/native 退出/handle invalid 不报告成功；原生 false 的终态不可重试旧 invalid handle；析构无法确认时独立日志。无裸加载/激活/停用/卸载或 minimum 查询伪 ack。 |
| 架构与范围 | header 无插件状态/URL集合/使用人数缓存，无 UObject/GI/帧调度器。仅两新源码引用本类，零生产接线；Build.cs 及四份策略文档保持冻结。 |

源码冻结 SHA-256：

- h：`43F305F0D8DB0F5BF09A6F3637558975F5904C0889E13AEB129B5BCCB5CD2A3D`（96行）。
- cpp：`ED1AF8DD5EEB0E91B107668D3E75BC97E982AD1ED0F061E0FDC94AE2421D6028`（364行）。

### 未完成与停止点

- 第20次只覆盖 G0-0，G0-1 尚待统筹完整构建和后续专项；静态配对/模式核对不证明 C++ 编译、真实插件转换、同步/异步/重入或退出行为已动态通过。
- lifecycle control 动态切换始终不受支持；原生 disabled Reset 的 true 可跳过引用移除，不能修补为假成功或裸转换。
- 本类释放由未来宿主决定时机，尚无同 GI 跨地图保留保证；外部借用、依赖解析/分类、Active/session/迟到回调、GI/GameMode及测试未实现。
- 四份局部图文按本轮明确约束保持冻结；新增未接入核心类/接口信息待后续局部文档租约同步。当前装配流程与候选宿主描述未被接线改变。
- 四文件静态冻结交回即停止；不自动实施下一步，不运行 UE/构建/Git，不创建代理，C15 保持未关闭。

## 09-G0-1-R1：创建/Retain 子系统可用性短修

- cpp 原 SHA-256：`ED1AF8DD5EEB0E91B107668D3E75BC97E982AD1ED0F061E0FDC94AE2421D6028`。
- Subleases 原 SHA-256：`C0FAEEDFF601299C31D3222B591ECE80E56C6F9C2E131AE2CE0CBA792318EF0E`。
- Validation 原 SHA-256：`E968F2B18657FEE09644121C18EF5EEFDCE3CD3CF0CBFC9BD6C62E4136D03092`。
- 已复读 primary API：GameFeaturesSubsystem.h:478 的 Get 无空值保护；Engine/Engine.h:3847 的 GetEngineSubsystem 返回指针。
- 将仅添加准入可用性检查，并用检查所得公开指针执行 GetPluginState。CheckNativeExecution 原线程/退出/CVar 顺序及 Release/析构全文须保持。
- 本轮并不修复任意在途基础设施拆除：原生 Release/handle 析构可能继续访问其子系统，未来宿主必须在 GameFeatures/Engine 合法存活期间先退役资源。
- 当前为已登记预检，待短修与读回；未编译/动态验收，header及既有六项保护哈希保持原值，C15 未关闭。

### R1 实际静态证据与冻结结果

- 新 helper 先检查 GEngine，再通过公开 GetEngineSubsystem<UGameFeaturesSubsystem>() 取得当次可空指针；两种缺失分别返回错误，不存成员缓存。
- TryCreate 在 native 初始化前/后均执行可用性检查；CheckRetainPrerequisites 保持原线程/退出/CVar/关闭/handle检查，再检查实际子系统。CheckStableLoadedState 独立取得并检查指针后才调用 GetPluginState，仍只接受精确 Loaded/Active。
- 全文比对：CheckNativeExecution 原函数一致；从 ReleaseOwnedReferences 到文件末（所有释放/完成/析构代码）一致；三个 public 接口由冻结 header 保持，完成语义未改。
- 当前 cpp 不再调用 UGameFeaturesSubsystem::Get；差异仅准入/查询 +25/-4 行，385行。源码 SHA-256：`0274A5B7E401F220FCF37CAF5A32ABCDE316E61FBCBB4063E478AE3706CDCB20`。
- h、Build.cs 与四份保护策略文档读回复核原哈希；两09记录的短修前全文作为前缀保留，不覆盖历史。三文件已读回、静态冻结交回。
- 本核对是源代码/公开 API/差异与哈希审查，不是编译、缺失引擎动态夹具或生命周期测试。G0-1/R1 仍待统筹完整构建及后续专项。
- 可用性检查只保护当次创建/Retain/查询；检查不能修复在已有引用期间任意基础设施提前销毁时 native Release/handle 析构仍访问其子系统的路径。未来宿主必须先在合法 Engine/GameFeatures 存活期间退役资源；不承诺支持任意在途拆除，不扩大架构。
- R1 三文件冻结后停止；无 UE/构建/Git/测试/资产/图文/全局记录写入或代理操作，C15 保持未关闭。

## 09-G0-2：实现前基线与验证边界

- 新 resolver h/cpp 原不存在；h 数据契约先于 cpp 冻结。两记录本节前全文保留。
- Subleases 原 SHA-256：`ECAB1B57B42E1173034A60B90860FB8E1E7F94954B3BB55E9FA5DCD12F9B78B3`；Validation 原 SHA-256：`640CBE10A21CA319498176F33CA85C4A936C76B8B5972B623035A0FD4A7875FC`。
- 已保存 Source/Config 与四份局部 GF 图文共236个只读保护哈希；Retention h/cpp、Build.cs、GameMode 为重点全文冻结依赖。
- native GetPolicy h697 含 ensure + CastChecked；GetDetails cpp3214 会访问内部 policy。传实际 const policy 引用不消除整个调用窗口要求。
- 初始化证据：Engine cpp2403 初始化子系统、2512 初始化对象；AssetManager cpp4219 广播；GameFeatures cpp793 标初始化、794 Init、796 Details、799 PostInit。Engine/GI 正常顺序和子系统关闭不能由指针存在替代；AssetManager IsInitialized 仅检查指针；SkipAssetScan 跳过广播；集合关闭期间可能仍查询到已关闭实例。
- API 风险：ParsePluginURL cpp1166/1185 对未知协议或错误路径 ensure；先检查 file 协议、options和路径格式再调用，不能把畸形 URL 当普通插件。FGameFeaturePluginReferenceDetails 的名称在本机可为 FString/FUtf8String，采用 native 相同的 FString 转换。
- 受限候选只证明本次观察的元数据/来源声明。私有 native handle 成员、实际运行依赖图、借用有效保护、完整 Loaded floor 和生产释放资格均没有公共证据。
- 统筹第21次已编译 G0-1/R1，常规52/52；不是本新增解析器的编译/动态证明，也没有真实 GFP 专项。本步骤不自行构建或运行。
- 待核对：全部 enabled 边包含 false、default policy 错误与成功空值区分、原生映射/安装路径/实际描述交叉、显式来源完整性、周期路径、Rejected无部分候选、纯值输出、无policy/就绪缓存或生命周期调用、保护哈希与两记录前缀。
- 当前状态：数据契约冻结，cpp 待实现。四份 GF 图文按明确租约继续冻结；新增未接入解析接口信息待后续局部文档步骤同步。

### G0-2 已执行静态审查与冻结结果

| 核对 | 实际结果及边界 |
| --- | --- |
| 本机公共API | Subsystem h569/683/757、ProjectPolicies h150、Settings h27、Projects IPluginManager/GetDescriptor、Json TryGet/Deserialize、Core路径/数组/集合及FSoftClassPath(UClass*)已核对。PluginName转换与native cpp4397一致，兼容本机FString/FUtf8String宏。 |
| 合法生命期 | resolver零GetPolicy、IsInitialized/IsPluginAllowed探针、bPolicyReady或私有flag；只有公开观察拒绝。头明确实际policy引用取得与整个同步合法窗口需未来唯一调用方审查；无生产调用方证明、无任意阶段安全保证。 |
| file身份 | 协议/options/路径先检查，避免把已知畸形URL送入native Parse ensure；文件必须存在，canonical名称及descriptor basename一致，安装路径/policy/native URL一致。 |
| 元数据完整性 | 原始文件在GetDetails之前保守检错；actual Projects全表与文件一致；enabled表与actual native Details数量/名字/Activate一致，重复或类型/集合冲突拒绝。该证据限于本次依赖元数据，不证明私有运行图或变化中的外部文件。 |
| 完整enabled闭包 | 每条enabled边实际ResolvePluginDependency，无ShouldActivate=true筛选；false边同样进入GFP候选。policy错误即拒绝（不因optional放行），HasValue检查后才GetValue；空URL有原生成功及已安装非GFP复核证据，非空必须native映射一致。 |
| 明确来源 | 每GFP节点需Managed/Borrowed声明；未知enum、OwnerLabel冲突、缺失或未使用项拒绝，相同声明去重。标签不证明保护；BorrowedPluginNamesRequiringProtection明确保留未解决项。 |
| 候选出口 | 当次双向身份/URL表、显式栈与Visiting检测冲突/循环；push前复制frame值，避免Stack重分配引用失效。所有拒绝重建空候选，唯一末尾成功出口；结束再核对native映射。 |
| 架构/范围 | header无engine/policy/GI成员或资源句柄；cpp无插件状态查询、加载/激活/停用/卸载/引用/调度API，只有原生元数据查询。两源码之外零调用点，现有依赖和Controller权威未改。 |
| 静态方法 | 全文词法括号、public入口/定义、结果控制分支/API及临时值生命周期审查通过；创建后h全文冻结，两记录旧全文仍为前缀。这不是C++编译、单元测试或真实GFP动态验收。 |
| 禁止隐式兜底 | 配置其它policy而native回落默认仍拒绝；malformed初态/已声明布尔字段/缺失源/URL失败不隐藏为成功或普通插件。可选字段缺省仅采用既有native元数据契约；本解析器不执行任何业务替代。 |

源码冻结：

- h（108行）：`ABAEE1D1F8D34EC2A72143053C54832334F567A34661F365F794B1AB4AC9D119`。
- cpp（601行）：`5A438054BA6367863DACB858D07582C45E92E92417E748CEED078A4D8C6957DD`。

保护核对：

- Retention h/cpp、Build.cs、GameMode h/cpp及四份GF局部图文均与本轮原哈希相同。
- 本轮广域只读Source/Config快照另观测到HitSemanticsTest cpp/types.h变化及EncounterBehaviorTreeTest cpp/types.h新增，排程分别属于B3/E2独立租约；本会话没有写入它们，不将并行变化冒称为本步差异或全项目不变。
- 仅新resolver h/cpp及两09记录写入。h创建后无再改；两记录历史全文保留，新增证据不覆盖G0-0/G0-1/R1。四份图文仍受明确冻结约束，待后续局部文档租约同步新增普通接口及未接入状态。

停止与未完成：

- 四文件静态冻结交回；下一统一构建由统筹安排。本解析器尚未编译，没有实际合法调用窗口、真实GFP/外部借用/转换行为专项。
- 实际native handle/ref成员与运行依赖图不可公开枚举；候选元数据/来源声明不能证明native ownership、完整Loaded保留、借用有效保护、GI/Active/inflight安全或释放许可。
- 本步没有调用方/宿主/引用登记或生命周期动作，仍须后续独立契约、接线和真实GFP验证，C15未关闭。
- 未运行UE/构建/Git，未写测试/配置/资产/其它源码或图文，未创建代理。最新用户禁止隐式业务兜底已核对；现有可疑替代另在交回后只读列给统筹，不扩大本步。

## 09-G1 Loaded 加载与保留：实施前登记（2026-10-03）

- 四文件授权及停止点见 Module_Repair_09_Subleases.md 的 09-G1；基线 Saved/ValidationRecords/GameFeatureLoadedLoading_LeaseBefore.json。
- 当前 h/cpp 与统筹基线一致：43F305F0D8DB0F5BF09A6F3637558975F5904C0889E13AEB129B5BCCB5CD2A3D / 0274A5B7E401F220FCF37CAF5A32ABCDE316E61FBCBB4063E478AE3706CDCB20。两记录只追加历史，不覆盖旧失败或未运行状态。
- 已核对 native Controller cpp636–661：Load 回调先添加 Loaded（即使 Result 为错误），再执行项目完成。Subsystem cpp1661–1716 的多 URL 共享上下文在析构时发布结果，不足以证明每个原生回调实际执行。实现采用 Controller cpp636–645 单 URL 接口，以当批 PendingURLs 逐项实际回调为完成依据；不采用析构汇总或结果占位符当完成证据。
- 原 handle 使用 None-options，因此闭包每 GFP 均须显式传入；不能依赖原生 root 收集把全部 false 依赖提升至 Loaded。
- 新入口的 caller 前提仍是完整闭包/显式托管和完整合法 policy 窗口。GetAvailableGameFeaturesSubsystem 只能拒绝已观察到的不可用，不能证明 policy 就绪；本步零 GetPolicy/就绪缓存。
- 验证仅有限源码/API/调用栈/所有权复核，未运行 C++ 编译或 UE。GI/Active/生产装配/借用保护尚未接入，C15 不关闭；最新七份 Obsidian 同步为统筹已完成的旧核心事实，本步没有图文写权。

### 09-G1 有限实现复核与冻结证据

| 项目 | 实际核对与边界 |
| --- | --- |
| API/唯一句柄 | 新 LoadAndRetainValidatedManagedClosure 输入按值复制至当批自有集合，空集合/空白 URL/空回调拒绝，重复 URL 去重；仍仅原 None-options StateHandle，无新增 handle 或插件来源猜测。 |
| 真实完成依据 | 采用 Controller::LoadGameFeaturePlugin(handle, URL, options, UGameFeatureStateHandleLoadComplete) 单 URL接口；每 URL 在发出前加入 PendingURLs，只在实际回调移除。不以 native 多 URL 上下文析构、占位结果或等待时间当完成。 |
| 同步与重入 | 整批先加入 PendingLoads；bNativeCallReturned 在提交循环结束后设置，所有已发 PendingURLs 清空才 Finish。用户通知前标 bPublished/移除批记录/取走原通知；用户回调后的释放再次读取当前记录，容纳重入的新批或 Close。 |
| 错误与状态观察 | HasError/无 success value 始终 Failed，保留 URL/原错误/OptionalErrorText；闭合、错线程回调或可用性/稳定态失效 Interrupted。Loaded 只在全部提交真实完成成功，且所有 URL 当前为 Loaded/Active 及前提复核通过时发布；不是 per-handle ack 或生产装配成功。 |
| 关闭/句柄顺序 | 首次 Close 先拒绝新准入；循环停止尚未发出的 URL，已发项等待实际完成。StartNativeReleaseIfReady 以 PendingLoads 非空拒绝注销，释放沿用原原生调用返回/handle invalidation/终态缓存契约；等待加载时重复释放也不能替换原通知。 |
| 线程/保活 | 所有资源状态仅 GT 修改，wrong-thread 准入在原线程明确拒绝且无改动；异常 native off-thread completion 只通过现有 Core GT 队列转交并报告未确认。原生委托/栈共享引用保活，无 GI/World 裸引用、Tick/Timer/新队列或调度循环。 |
| 旧核心保持 | 可用性三个 helper、构造/TryCreate/CheckRetainPrerequisites/RetainAlreadyLoaded/OnNativeReleaseCompleted/FinishReleaseIfReady/析构，共十个旧方法体按统一换行全文比较一致。原释放入口只增加准入关闭、首通知保护和加载排空门禁；实际原生释放尾段继续复用。 |
| 范围与架构 | 四文件租约内修改；来源与完整 policy 窗口仍由未来唯一准入方证明，零 GetPolicy/ready cache。只持有自己临时输入/完成记录，Controller 仍是引用和插件状态唯一权威；无第二使用人数事实、状态机或循环依赖。 |

源码冻结（未编译）：

- h（140行）：2536E283875E735EF3D62EA25FC1291426DAC7CC1B31DECAC1E5FD58B9A065A3。
- cpp（602行）：8B43A72913244C03FE07D24937421189B9FCBAB68313D2279768A9010A9C1054。

保护与剩余项：

- 两记录的租约前历史全文按统一换行保留，仅追加 09-G1。Resolver、GameMode、Experience、Build.cs、Config 与四份 GF Obsidian 核对保持；广域 Source 观察到 Combatants h 的独立租约变化，本会话没有写它或据此声称全项目不变。
- 已核对 Obsidian 两 MD 与两 Canvas：需要增加本加载入口、逐项 pending/停止未发请求的关闭流程，并将 Retention 新增部分明确标为已编码未编译；旧核心第21次编译证据只属于旧版本。当前笔记“全部四源码与Gate54一致”需随本新版本修订。该图文同步由统筹另租约负责，本原子禁止修改。
- 新接口全 Source 仅声明/定义，无生产调用；GI、配置、Active、GameMode 真实装配与外部借用保护没有实现。旧空名 skip、缺 URL skip、激活失败仍 spawn 证据继续保留，C15 开放。
- 未运行 Build/UE/Git，未写测试、配置、资产、Obsidian 或全局文件，无子代理。有限静态复核不是编译或动态证明；后续仅统筹的编译与必要 UE 冒烟，不恢复严格测试矩阵。
- 缺失 native 回调不能视作完成，仍保留未完成请求；正常 native 生命周期以外的拆除/动态关闭 CVar 不保证资源释放，不能据此报告成功。未来宿主仍须管理 Active 与 Loaded 租期释放顺序。
- 四文件冻结交回，等待统筹审查和后续互斥租约。

## 09-G2 GI Loaded 薄宿主：实施前登记（2026-10-03）

- 精确授权与停止点见 Module_Repair_09_Subleases.md 的 09-G2；基线 Saved/ValidationRecords/GameFeatureGILoadedOwner_LeaseBefore.json。两新目标尚不存在，两记录与统筹基线一致；历史前缀保留。
- 只读核心：Resolver h/cpp ABAEE1D1F8D34EC2A72143053C54832334F567A34661F365F794B1AB4AC9D119 / 5A438054BA6367863DACB858D07582C45E92E92417E748CEED078A4D8C6957DD；Retention h/cpp 2536E283875E735EF3D62EA25FC1291426DAC7CC1B31DECAC1E5FD58B9A065A3 / 8B43A72913244C03FE07D24937421189B9FCBAB68313D2279768A9010A9C1054。
- 合法同步窗口：GameEngine.cpp1232 完整 UEngine::Init 先于1265–1267 GI 创建/InitializeStandalone；UnrealEngine.cpp3831–3833 无 SkipAssetScan 时 StartInitialLoading，AssetManager.cpp4219 created broadcast 驱动 GameFeaturesSubsystem.cpp793–799 初始化/详情/PostInit。EditorEngine.cpp979 完成 Engine 初始化后正常 PlayLevel.cpp3015 才创建 PIE GI，GameInstance.cpp364 初始化 GI subsystems。
- 正常关闭：GameEngine.cpp1358 BeginTearingDown、1373 EndPlay、1377 GI Shutdown，1396 才 Super::PreExit/Engine subsystems deinit；PIE PlayLevel.cpp725 BeginTearingDown、897 EndPlay、899 GI Shutdown。World 拆除/当前 Context 变化与 owner closing 用于拒绝准入及迟到成功，不作为 native policy Ready flag。
- 本步必须实际调用既有 Resolver 与 Loaded 核心，但仍没有 Experience/GameMode/Active Session 生产调用；空/缺来源不能转换为正常 Loaded，借用保护未实现须拒绝。pending 租期和后续 Active 租期共享同一 ordinary owner，不建立引用计数权威或调度器。
- 仅有限源码/生命周期/范围自查；未编译、未运行 UE，不加夹具或矩阵。Obsidian 四份图文受本步明确零写权约束，完成前只读核对并交回待同步项。

### 09-G2 有限实现复核与冻结证据

| 核对 | 实际结果与边界 |
| --- | --- |
| native ABI | PrepareManagedLoadedClosure 的 Input 按值、完成可同步；FLoadedLease 是 const 普通租期 shared pointer，成功时已构造完成。租期仅返回 copied root view 和原 World/GI admission bool，无 handle/Retention/Release 暴露，无 Blueprint load/release UFUNCTION。 |
| GI 生命周期 | Game/PIE GI 原生 collection 自动实例化 final 子系统，Initialize 仅一次 owner/Retention factory。重复初始化/失败不创建第二资源或自动重试；Deinitialize 仅关闭准入并 Reset 宿主持有，未直接调用 Release。 |
| 资源唯一/持有图 | GI -> ordinary owner -> 原 Retention；original lease -> 同 owner；native pending completion -> 原租期。GI 结束后 lease 保活，最后 owner 在 GT 调既有 ReleaseOwnedReferences；非 GT 最后归还可见失败，由原 core 析构转交既有 GT cleanup。共享内存引用不是插件使用人数权威。 |
| 真实 Loaded 桥接 | Resolver 的 ResolvedCandidate 还须全部显式托管、borrowed list 为空、root node 全存在及 owner/World 准入复核；之后一处原 LoadAndRetainValidatedManagedClosure 接全 Nodes URL。没有 Active 调用、原生新句柄或裸 load 降级替代。 |
| policy 窗口 | 一处同步 GetPolicy，以登记的正常 GameEngine/EditorEngine -> AssetManager/Policy -> GI 次序为前提，公共兼容性/Context 校验只拒绝不匹配。World 当前/注册/所属 GI、拆除/退出/SkipAssetScan 均在 policy 读取前检错；manual/RPC、动态 reload、重入和 changing metadata 不支持。 |
| provider 范围 | 在 policy 获取前要求 exact 已审查 UGGYGOAssetManager 且 HasCompletedSharedAssetPreload 为真；System h/cpp 保持只读，StartInitialLoading cpp75–90 的 Super 调用及公共 getter 语义已实读。只读取其已有启动尝试完成，不依赖 GameData/共享 GE 成功，不复制为 GF Ready flag；System 无反向 GameFeature/GameModes 引用，未新增循环依赖。 |
| 关闭与迟到 | completion 捕获 lease/value label，原 World 与 GI 仅 weak。关闭、World 替换/拆除/失效后的 Loaded -> Interrupted + 空租期，原错误/失败保留；IsAdmissionOpenFor 不承诺 Active/plugin Ready，旧租期不能交给新 World。 |
| 范围与运行 | 无 Tick/Timer/task queue/使用人数或插件状态缓存。静态复核不是 C++/UHT 编译或 UE 证明，未写测试或矩阵，无 Build/UE/Git/资产/Obsidian/全局/代理权限使用。 |

源码冻结（未编译）：

- h（80行）：134A3A56C19FB952BB103463177AFE9C80BE99167D8C4EE629E8235EFEC9AE08。
- cpp（347行）：136A2E6C2F968C5DB20CC9C7E1690121D999B686053EC3F059745766371E72B2。

保护与剩余项：

- 两记录写前历史 prefix chars/UTF-8 SHA256 与本轮基线一致，未覆盖 G0/G1 的失败/编译边界。Retention/Resolver 四源码、GameMode/Experience、System AssetManager、Build.cs/Config 与四份 GF 图文保持。
- Source 只新增本 h/cpp；同期观察 ASC h/cpp、AbilityInputRequestTypes h 与 PawnExtension h/cpp 五份其它作者变化，未触碰或纳入本步差异，不声称全项目不变。它们不属于本步只读依赖。
- GI 生命周期/Loaded 桥接与原租期已编码；尚无 Prepare 的 Experience/GameMode 调用方，显式来源资产配置、Active 会话及其实际退场接线未实现；原 GameMode empty-name skip、URL missing skip、activation failure still spawn 仍未修复。Borrowed 明确拒绝而非保护完成，C15 开放。
- 只读核对 Obsidian 后须交统筹同步：GI 薄宿主由“候选未实施”改为“已编码未编译未被场景调用”；补普通 owner/租期节点、跨地图持有与 closing/last-lease release 流程、显式来源/Borrowed 准入及原 World late-success Interrupted；G1 新入口及旧版本编译证据仍须同步。当前旧四源码/Gate54等文字不能覆盖新版本。本会话无外部笔记写权。
- 未来 Session 必须先构造自身再调用，并把成功的原租期持到自己的 Active/pending 清理结束，不能把 bool admission 或 Loaded snapshot当作 Active 成功。此契约尚无消费实现，整体“只停用、不卸载”未验收。
- 当前四文件冻结停止；不新增严格矩阵/夹具，统一编译及必要 UE 冒烟由统筹安排。任意不受支持的基础设施拆除、动态 CVar/元数据/模块变动仍不承诺清理；失败不冒称完成。

## 09-G3 Experience 显式来源配置：实施前登记（2026-10-03）

- 授权/精确范围/停止点见 Module_Repair_09_Subleases.md 的 09-G3。基线 Saved/ValidationRecords/GameFeatureExperienceSourceConfig_LeaseBefore.json；四文件当前哈希均与基线一致，历史全文保留，仅追加本阶段。
- Experience h 基线 4368DB088940607E2451CB4E94B4772AFA8E5531D8B8CC00CBFFA2A6061872C5；cpp 3FCD0C9646295740CDEECCDBD47EEEAC6A48D36269C0D7FD9EBB22ECFB9DF442。
- 两记录基线 SHA256：Subleases 2700E4C7870BB9AAE36C01C925A88F6A9AA2C54C2FC40A8EF13F17442275B078；Validation 7425B6ECDDD7BD3C7D8C8AA8D27AE2BD979BBC45CE8341275916E4927DEA71C2。
- 形状校验必须可独立于原生上下文同步完成；空/缺来源不得成为默认托管，失败输出不能残留部分配置。配置值 enum 与 Resolver enum 逐项显式映射，不使用 ordinal cast。
- IsDataValid 仅复用新增配置校验，原容量、空 PawnData 与 PawnClass 检查保持全文；编辑期 Valid 不证明已安装闭包/URL/加载/Active/Borrowed 保护。
- 已只读核对计划蓝图及 GameFeature 两 MD/两 Canvas；GI/G1 图文已经由统筹更新。此步新增 Experience 字段/接口及未迁移资产事实须在后续统筹图文租约同步，本步没有外部笔记写权。
- 本阶段仅有限静态自查；未 Build/UE/UHT/Git，零测试夹具/矩阵/资产写入。Active 会话及 GameMode 门禁未实施，C15 未关闭。

### 09-G3 有限静态复核与冻结证据

- 全文/反射接口：generated include 仍为末尾 include；enum uint8/BlueprintType、USTRUCT GENERATED_BODY 与三字段、数组反射入口存在；原生 bool/const/FInput 引用/TArray<FString> 引用签名与冻结候选一致，无 UFUNCTION/GI 依赖。反射实际可用性未 UHT 验证。
- 形状路径源码审查：两数组空 -> true/空 Candidate；只声明无根 -> 错误；非法名字/来源/owner 与冲突 -> OutErrors 非空/false；缺合法根声明 -> 根字段/原索引错误。输出先清空、只在唯一成功末尾移动 Candidate，因此失败无部分输入。完全相同重复按首项稳定去重，源数组不修改；每个 enum 分支显式映射 native enum，无猜测或 ordinal 映射。
- 原有规则保护：旧 GameFeaturesToEnable 的 UPROPERTY+TArray<FString> 逐字存在；Squad 头文件字段起至末尾、cpp 原容量校验起至末尾，以及构造函数均与租前统一换行全文相同。IsDataValid 只增加一次新函数消费；原 Squad 失败继续执行并报告，不被 GF 失败短路。
- 调用和职责：全 Source rg 只有新函数声明/定义及 IsDataValid 调用。无 Native 加载/激活/引用/Prepare/AsyncTask/GetWorld 执行；无新增持久 Ready/计数/缓存/计时器。运行资源清理责任为零，配置成功不代表 GI Loaded/Active 或 Borrow 准入。
- 范围：本轮保护快照中 Retention/Resolver/GI/GameMode 八源码及 GF 两 MD/两 Canvas 全部保持哈希；两记录租前历史为原样前缀，只追加本阶段。有限范围核对不声明并行其它模块或全仓库不变。

源码冻结（未编译）：

- Experience h（121行）：4AB8158B413BB779C0EC4D386E156AA70F383F0C4CEBC4DB4F825D8B09E80070。
- Experience cpp（203行）：8BB6F3F333A48EA3A5DD16CF658D4078C246B7BEE65194CB502594F595FC3826。

实际未验及剩余范围：

- 没有编译/UHT/UE/插件加载/联机证据，不创建新专项夹具或矩阵；有限静态路径审查不能写成运行断言通过。旧版本编译证据不覆盖本新增反射字段和函数。
- 资产序列化名/类型保持，未读写或迁移任何 uasset；旧非空 roots 但来源空的资产会在新形状校验失败，需要统筹 UE 窗口补完整闭包显式来源。根已声明但依赖缺声明、未使用声明或 URL 错误仍交冻结 GI/Resolver 拒绝。
- 正常无 GF 模式是合法配置结果，未来场景消费应显式处理；当前 GI 非空闭包接口不改，GameMode 仍旧裸激活/计数/失败仍装配。原 World Active/pending 与持 lease 清理未实现，全部上层门禁与 C15 开放。
- 已只读核对架构计划：统筹后续同步 Experience 配置入口、形状 Valid 非准入、未迁移资产和无 GF 正常模式至 GameFeature 结构/计划/两图；本步遵守冻结，不修改 Obsidian 或全局进度。
- 四文件已冻结交回，后继源码/资产/文档/构建均需统筹另排租约，不授自动扩范围。

## 09-G4-0 原租期不可变激活 URL 集合：实施前登记（2026-10-03）

- 精确租约/顺序/断言/停止点见 Module_Repair_09_Subleases.md 的 09-G4-0。授权基线 TechnicalAutonomyBatch_20261003_LeaseBefore.json；四文件当前哈希均匹配，只追加局部历史记录。
- GI h/cpp 基线：134A3A56C19FB952BB103463177AFE9C80BE99167D8C4EE629E8235EFEC9AE08 / 136A2E6C2F968C5DB20CC9C7E1690121D999B686053EC3F059745766371E72B2。
- 两记录基线：Subleases 16A6DF2D2DB4108058E350EE9C286FE58B030B5C89EEE83428C8DFFC485FE562；Validation 45EFB81C9BB39C83DC7DCAF21310F48AD69ED9E675D473D8B7B2A28DDB115604。
- 根因只读证据：ReferenceController.cpp250-254 对已存在依赖升高需求后 continue，未把节点重新入 DFS；同文件607-616 单 URL Activate wrapper 在实际完成时仍会登记引用，错误也不例外。当前未运行动态复现，不把新请求集合等同于已经解决生产 Active 清理。
- 有限静态保护快照：Retention/Resolver/Experience/GameMode 八源码、native ReferenceController cpp、GF 两 MD/两 Canvas，共13文件。其它 ASC/Movement 独立任务不纳入“全仓库不变”声明。
- 保留原准备链：所有来源全 Managed/无 Borrow；当前 exact AssetManager/合法 Policy 同步窗口；原 Nodes URL 全量 Loaded 输入；原 World/closing/迟到成功 Interrupted；last-lease 释放机制。新增只读值生成不建立第二套验证权限、插件状态或执行器。
- 外部笔记已由统筹同步至09-G3；本步只读核对后交回 lease getter、true可达集合、静态根因边界及未消费事实，源码消费者/Obsidian 待后续独立阶段。
- 不运行 Build/UHT/UE/Git，零测试矩阵/资产/引擎/全局/代理写权；仅有限静态核对，不冒称动态断言通过。

### 09-G4-0 有限静态复核与冻结证据

- 接口与内存：GetActivationPluginURLs 返回 TConstArrayView<FString>，实际返回 private const TArray；构造接收按值数组后移动保存，private ctor 只有本 GI 一处 new 调用。原 Root getter 及 weak World/shared owner 保持。Closure 节点指针只在函数局部 map 中有效，不逃逸；输出只复制字符串。
- 值选择源码审查：pending 初始包含全部根；只在父节点匹配且 bShouldActivate 为 true 时追加依赖；Visited 检查在展开前，false边不将节点标为已访问，所以后见 true 路径仍会展开子树。全部根先按输入顺序进入结果，多路径节点/URL 去重；当前名字复制后再追加，未保留可失效数组引用。
- 针对原静态例的手工循环推导：R根，R->A(true)、R->B(false)、B->C(false)、A->C(true)、C->D(true)，新选择值为R/A/C/D，B仍属于原全量Loaded集合；多根若含B，则B自身进入激活集合。这是源码路径推导，没有执行夹具或UE，不标为动态通过。
- 失败路径源码审查：OutURLs/OutError先清空；所有节点名称/URL非空且唯一、所有GF边两端存在且边URL非空/匹配；根未在Nodes中或请求集合空拒绝。唯一成功末尾才移动 Candidate，错误由原 RejectPreparation 携 GI/World label 和对象/URL原因返回，未调用 Loaded，也不回落根集合。
- 原路径保护：移除新增 helper/getter、const字段对应构造参数和准备链纯值调用后，cpp统一换行全文与租前逐字一致。原CheckGameInstanceContext、owner/lease准入、Initialize/Deinitialize、Root getter、来源/Borrowed拒绝、Policy读取、全Nodes Loaded调用及迟到/last-lease清理保持；没有改变G1 core或引擎语义。
- 新增 helper 无 GetPolicy/GetPluginState/Native引用/Load/World/Async 读取或调用。Source检索 getter仅声明/定义，本地生成仅定义及本GI一次消费；未把共享值合同写成Active生产实现。
- 原两记录统一换行历史前缀逐字保持。保护快照13项（八源码/native Controller cpp/GF四图文）全部哈希保持；只报告本精确范围，未断言并行ASC/Movement或全仓库未变。

源码冻结（未新编译）：

- GI h（89行）：3690CFF79035E8BA859D3CE3F8A820F502B706B7F8DF16FA927008FE7A496EB2。
- GI cpp（434行）：9F54E07DF48CBB3C6D8C16AD1AAB43C473979120F903942538A82482FC905310。

未验与后继边界：

- 未运行UHT/C++编译/UE/Native激活/原生问题动态复现/联机/资产迁移；没有创建脚本、测试夹具或严格矩阵，有限静态审查不代替这些证据。旧GI/配置/Loaded版本编译状态不被本增量提升。
- 不可变值本身不登记Active需求，不证明实际Active或完整清理。下一会话必须在原租期有效且原World准入开放时用完整集合登记自己的原生Active需求；先保存会话再请求，等待真实pending及调用返回，撤自身Active后归还lease。GameMode/Teams真实成功装配门禁另租约。
- Native Controller缺口仍为静态根因证据；本步没有改引擎、限制复杂图或扩大Borrowed准入。根+true边可达集合来自已验证Closure，完整false依赖保留在原Loaded链，C15和整体生产策略开放。
- 已只读核对计划蓝图与09-G3现有GF图文；新 getter/集合/静态根因及已编码未编译无消费状态交统筹后续Obsidian阶段，不抢写冻结外部笔记/全局进度。
- 当前四文件冻结交回；仅共享值合同完成，源码消费、图文、编译、必要UE冒烟各自保留独立状态。

## 09-G4-1 原 World 薄 Active 会话：实施前登记（2026-10-03）

- 精确范围/顺序/断言/停止点见Subleases的09-G4-1。两新目标不存在；两记录基线EABD0BD4459E847CB91AEE0770578C324F2E024ADF4080B07C4FC4FE194668F6 / 249AF791FAE315D0D11E6F3DFF23F7BDD122ADE184ED761AC3365984C90F05B3，写前一致。
- 当前GI只读h/cpp为3690CFF79035E8BA859D3CE3F8A820F502B706B7F8DF16FA927008FE7A496EB2 / 9F54E07DF48CBB3C6D8C16AD1AAB43C473979120F903942538A82482FC905310；两个view为不可变请求值，Loaded lease并非Active。
- Native真实接口：InitAndRegister(Label,None)须bool及GUID均有效；AddOrUpdateReference(handle,url,Active,false)为void；Controller单URLLoadAndActivate(...,UGameFeatureStateHandleLoadComplete)；ReleaseAndUnregister(TFunction<void(bool)>)。原wrapper607-616在用户回调前登记Active，即便native失败仍登记。
- 有限清理依据：Controller RemoveReferences cpp418起先RemoveRefAndRequiresDowngrading，再发降级并返回bool结果；StateHandle Release先Reset后Unregister/Invalidate。因此回调可能先于调用返回/注销，失败可能是降级失败，不能视为成功；缺失服务/动态lifetime变化超出正常合同，保留未确认资源诊断。
- 本轮保护快照为冻结十源码、Native Controller cpp、GF四图文共15项；无其它模块写入，不声称全仓库不变。
- 静态核对只覆盖已授权资源契约；未新编译/UHT/UE/动态复现/联机，不创建测试矩阵或夹具。GF图文已同步G4-0，本资源/执行链/未消费状态待统筹后续图文阶段。

### 09-G4-1 有限静态复核与冻结证据

- 原生ABI/责任：一个InitAndRegister(None)调用点且检查bool/GUID；一处GI Prepare；一处完整激活集合AddOrUpdateReference(Active,false)；一处单URL逐根LoadAndActivate。副本字符串/原结果仅为本任务证据，Source无第二闭包/policy读取，Native仍唯一状态与引用权威。
- 同步路径手工审查：bPreparingLoaded/bPrepareCallReturned在GI前设置；bActivationDispatchReturned覆盖整个初始化/登记/根调用批次；PendingRoots在每个实际Native调用前登记、真实回调移除。同步首个回调看见派发未返回，不能提前Ready或Release；异步原函数返回后继续由实际pending控制。没有Native数组聚合析构当作完成。
- 成功/失败手工审查：Loaded无lease、非法view/未实际Active拒绝；根错误保留GetError/OptionalErrorText，Failed不会被Interrupted覆盖。实际Ready前再读原World/lease准入；原World/GI关闭或替换抑制通知并清自身需求，零根配置拒绝，无法把空输出伪装GF成功。
- 清理手工审查：Close先关闭/撤观察者；真实工作和调用排空后仅Release自己的GUID。Release原生回调和返回分别记录，句柄注销且guard保持后才归还lease；false产生Failed，其它使用者保持Active不构成失败，无全局Inactive断言。终态先于lease.Reset保存，防重入重复释放。
- 生命周期/析构：正常Ready/Closed/Failed清自有保活；Pending无真实回调不假完成。Unconfirmed保留尚未确认资源，析构将同一move-only GUID/lease转独立记录；源Session析构无AsShared/裸this，记录无World/GI读取，回调或最后析构仅一次使用Core现有GT队列。异常引擎拆除/动态CVar/丢失回调下可能持有至进程结束，不能冒称无泄漏/清理成功。
- 观察者/线程：外部Completion须弱绑定并匹配原Session/World。错误线程Start/Close拒绝且不变资源；实际Native异常off-GT完成复制数据后GT处理并标Interrupted/Unconfirmed，GT外不读World/GI或改资源。IsReadyFor GT外返回false，当前Native状态查询不刷日志、不Tick。
- 新类全Source检索仅新h/cpp，尚无GameMode实例化；实际机制已消费GI/两个view，并含真实Native激活/清理。未来消费者完整顺序及Teams交接见Subleases，不保留空准备层。
- 15项保护hash保持（GI/core/Resolver/Experience/GameMode十源、Native Controller、GF四图文）；两记录租前历史统一换行前缀逐字保持。本会话仅四文件写入，不对并发其它作者/全仓库做无变化声明。

源码冻结（未编译）：

- Session h（110行）：EBD29C5F036F2D368F1C5C8B34EE07B85C0074A0022031E0B9E0A996F7ED1CF7。
- Session cpp（544行）：E251C08A0ACAA4CB89E119462219DB8D44C25AE7A33557C00E39A327515924EA。

未验与后继：

- 未UHT/编译/UE/插件真实激活、退出/切图、复杂依赖动态复现、资产迁移、独立PIE Action隔离或联机。无测试夹具/严格矩阵，有限静态审查不替代这些证据；目前不存在实际运行Session的GameMode调用点。
- Native服务寿命仅沿用冻结正常GI合同；Engine exit/提前拆除、动态lifetime control或真实回调缺失不能保证退役。显式Pending/Unconfirmed和资源保留可见，异常占用需统筹运行窗口定位，未加入默认动作、另一资源或成功结果。
- C15 Borrowed仍拒绝；Native Action世界过滤政策保持原生，未用会话weak身份冒称独立PIE动作隔离已证明。整体生产链/策略没有完成百分比或完成标记。
- 下一租约GameMode h/cpp加原两记录需Teams交接：先保存Session再Start；所有生成入口读原Session IsReadyFor；失败/无配置不放行；合法无GF模式只在配置转换true后判定；EndPlay Close后撤调用方持有。GI/core/Session冻结作为只读接口。
- 已核对G4-0现有Obsidian；统筹后续同步Session结构/流程、真实pending/双返回门禁、原资源持有/未确认边界和已编码未编译无GameMode消费状态。当前四文件冻结交回，外部笔记/全局进度/构建各自另排，无本会话写入。


## 09-G4-2 GameMode实际消费原Session：有限静态证据（2026-10-04）

- 授权与范围：统筹接受01a10283-33d8-7bb3-aea8-94885cf3a7e2预检并直接授四文件，基线Saved/ValidationRecords/GameFeatureGameModeConsumer_20261004_LeaseBefore.json。生产实现先于本验证记录；完整原子／断言与停止点见Subleases的09-G4-2。无实现子代理。
- 根因保留：旧GameMode按每根先增后发，首根同步完成可在后继未发时归零；错误解析跳过、native失败也递减后spawn。旧链与反例保留于租前源码／历史证据，不降低成功条件；本源移除该计数和裸执行链，复用冻结Session的整批返回、真实pending及完整Active资格。
- 配置／失败静态路径：父级ErrorMessage／缺Experience／失效原World-GI／转换false明确拒绝；成功两空才无GF，唯一bConfiguredNoGameFeatures=true赋值。非空TryCreate空不切无GF；唯一真实Start前GameFeatureSession已保存。同步Session失败经共享诊断复制回ErrorMessage；异步只写自有诊断值并封闭原调用方，无栈引用。
- 观察者静态路径：Start lambda仅WeakGameMode／WeakWorld／WeakSession／StartupError按值捕获；先pin原Session、再核原World／实际AuthGameMode／GI当前World与字段同身份。Rejected／Failed／Interrupted不spawn；Ready再AreGameFeaturesReady查IsReadyFor。旧GM／旧World／不同Session直接忽略，不Reset新会话。
- 入口／重入静态路径：Ready补装配和HandleStartingNewPlayer都经同一资格；Controller快照为当前列表的局部TWeakObjectPtr数组，弱Controller已失效／在销毁／World不同跳过。每个外部Spawn前后再读弱原GM／World并核原Session，失效即终止后续分发；已进入三个Spawn内部的执行不在本步撤销或回滚范围。
- EndPlay静态路径：GT关准入／配置资格→MoveTemp原Session→Close→Super；本GM字段在潜在同步Close重入前已空。未调用GI Prepare／Deinitialize／ReleaseOwnedReferences或native global API；实际根pending／Active先于租期归还仍由冻结Session执行，异常Pending／Unconfirmed可能保留到进程结束的原边界不变。
- 只读native签名核对：本机UE World.cpp显示AuthorityGameMode赋值先于InitializeActorsForPlay的InitGame；World.h的FConstPlayerControllerIterator为TArray<TWeakObjectPtr<APlayerController>>::TConstIterator，当前局部快照不保强Controller／等待名单。未改引擎。
- 源码保护：完整SpawnSquadForPlayer／SpawnSquadSlot／SpawnSquadMember及后缀与租前逐字相同；构造和TryApplySavedRoster前缀扣除显式include后逐字相同。Session／GI／Experience六源码与GF N3四图文共10hash保持；只报告该精确范围，不断言全仓库或并行其他文档不变。
- 文本／调用面：h/cpp保存全文回读；尾部空白0、冲突标记0；旧count／native裸激活入口／GetPolicy／GI直接释放／新增Timer-Async调度0；真实Start一处，native资格Session.IsReadyFor一处共用。检查是有限静态审查，未执行测试或运行这些断言。

源码冻结（尚未新编译／UHT／UE）：

- GameMode h（94行）：A82D61CDA84FAD8E821A17B4E32D27DC498072C772BC4D0C4E76F10A4A713311。
- GameMode cpp（535行）：B17F75D06AB3B2FAFF1C594D8F55ADE18BE1933BA045B65CFDEF35EEE5942906。

未验与交接：

- 历史Build55失败、UHT写33；Build56机械错误已消除但Hero旧三调用仍失败，运行时未链接／未UE。两次均先于本GameMode源码增量，不构成本消费者或Session运行验收；未新跑编译／冒烟／严格矩阵／资产／联机，不改历史失败。
- 本步仅真实启动消费、外层成功门禁和EndPlay自身Close。三个Spawn内部重入／部分生成及Teams创建责任交付／回收／选择／切人保持原样；Borrowed／C15拒绝原边界不扩。
- 后继由统筹安排有限源码审查、同任务GF图文／Source README事实同步、统一编译及必要UE冒烟；本四文件全部冻结后才能交Teams GameMode写权。不补第五文件，不改冻结共享接口，不写Obsidian／全局／资产／Git／引擎。


### 09-G4-2 BeginPlay前Destroy入口：根复核后实际补齐（2026-10-04）

- 根因证据（仅只读）：本机UE5.8 Actor.cpp的RouteEndPlay要求bActorInitialized且ActorHasBegunPlay==HasBegunPlay才调用EndPlay；AActor::Destroyed先RouteEndPlay再ReceiveDestroyed／OnDestroyed，LevelActor.cpp的原生Destroy仍调用ThisActor->Destroyed。InitGame已取得Session时，BeginPlay前原生Destroy不能靠原EndPlay-only消费者或未来GC及时撤Active。
- 在原同四文件授权内补Destroyed及唯一私有CloseGameFeatureSession；两个Engine hook在Super前调用同一消费者。未添加第二资源状态或修改Session／GI接口。前段仅EndPlay的完整性描述及94／535行源码hash为补充前历史，当前以本段97／554行版本为准。
- 有限路径核对：BeginPlay前Destroyed→消费者关准入／撤正常NoGF→move自有Session→Close→Super；已BeginPlay的Super::Destroyed→RouteEndPlay→本EndPlay→同消费者面对空成员→Super::EndPlay。外部Close发生前已移出资源，后续不Reset后继；仅有一份自有Session关闭实现，两个hook各一处消费者调用，无新增字段。
- 保存回读及范围：新关闭区域以前的实际消费／失败门禁／弱观察者／局部Controller代码完整相等，三个Spawn与后缀完整相等；h除两个方法声明／注释外保持。共同消费者内关准入先于Move、Move先于Close；两个Super均在自己的关闭消费之后；错GT均先拒绝，未新增native／GI释放入口或调度。
- 当前源码冻结：h（97行）5D536A2E58E6490EA4EF2B93616FB62B7A36B98A7893CC9B816E9F260EA7A56C；cpp（554行）0D498F0B06B74BD247D67533D7FFE9079C8C4A1EBBF3BE5A9FD1252E89D42551。两记录已有历史全文前缀保持，10只读保护保持；最终四hash由交回报告提供。无第五文件。
- 未运行BeginPlay前Destroy的UE复现或动态断言，本段是原生源码与调用次序的有限静态核对；未新编译／UHT／UE／Git／严格矩阵。Teams内部装配／部分生成、借用／C15、真实GF资产、跨图／PIE动作隔离／联机仍未验；统筹同任务后继图文同步与必要统一编译／冒烟继续待安排。
- 原四份全部重新冻结，交统筹最终有限验收；不扩大预检、引擎／冻结共享头、资产、外部笔记或实现代理范围。
