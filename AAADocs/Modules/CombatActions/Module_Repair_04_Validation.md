# 第04批验证与交接

## 04B4-StartedPositive 真实受保护 Started（2026-09-30，第19次实际通过、源码冻结）

本步最初由 `gpt-6.1-sol / xhigh` 组长直接实施，无代理；当时授权为两测试源码及 04 两记录。静态交回后源码持续冻结，统筹完成第19次完整构建与实际运行。本次仅授权两份 04 记录同步真实证据和已接受的只读 Task 候选；没有任何源码、测试、资产、Obsidian 或全局文件写入授权。下列第17次是前置历史门禁，当前正向用例验收以第19次实际报告为准。

### 前置门禁与独立原生红测试

- `Saved/Logs/ModuleRepairBuildGate_20260930_17.log`：完整构建 Succeeded，6 actions、20.77 秒，已编译 ASC 受保护入口。
- `Saved/AutomationReports/ModuleRepairGate_20260930_17/index.json`：2026-09-30 05:05:42 UTC，49 Success、0 failed/succeededWithWarnings/notRun/inProcess，0.441153 秒，UE exit0。常规回归未包含本次新增用例，不能证明 Started 保护成立。
- `Saved/AutomationReports/ModuleRepairB4Diagnostic_20260930_17/index.json`：05:23:33 UTC，原生 P1 为 1 Fail、16 errors、0 warnings，0.072188 秒，两个场景前置均通过；进程 exit0 不改变测试 Fail。原生兼容路径的后继写回风险仍存在。

### 第18/19次实际构建与第19次正向结果（组长只读核对）

| 门禁 | 原始证据（相对项目根目录） | 实际结果 |
| --- | --- | --- |
| 第18次历史构建 | `Saved/Logs/ModuleRepairBuildGate_20260930_18.log` | Messages 新诊断中的 GetAttributeSubobject/GetNumGameplayEffects API 处编译失败，Result: Failed (OtherCompilationError)，21.38 秒；未成功链接/运行，不能作为新增测试通过证据 |
| 第19次完整构建 | `Saved/Logs/ModuleRepairBuildGate_20260930_19.log` | GGYGOEditor Win64 Development，4 actions，包含链接 UnrealEditor-GGYGO.dll，Result: Succeeded，10.68 秒 |
| 第19次新 DLL 常规回归 | `Saved/AutomationReports/ModuleRepairGate_20260930_19/index.json`、`Saved/Logs/GGYGO_ModuleRepairGate_20260930_19.log` | 报告时间 2026-09-30 06:18:16 UTC（北京时间 14:18:16），51 Success，failed/succeededWithWarnings/notRun/inProcess 全 0，0.46889397501945496 秒，UE exit0；ProjectDiagnostics.B4 枚举数 0 |
| StartedPositive 专项 | 同一第19次报告中的 `GGYGO.AbilitySystem.MontageGuard.StartedSuccessorPreservation` | 实际 Success，0 errors、0 warnings，0.01734289899468422 秒；两场景前置、typed 结果与全部后继保持断言通过 |

| 场景 | 真实 Started / 观察与结果 ID | Guard 结果 | B 返回 → A 外栈返回 |
| --- | --- | --- | --- |
| DifferentAssets | A/B Started 1/1；ObservedID 与 CreatedID 均 0/1 | Call 1/2、Generation 2/2；A Superseded、B Accepted；NativeStage 均 Returned；Superseding 2/0；public/native/caller 返回均 A=0、B=1 | Local/Rep 仍为 B 资产，owner 仍 B；LocalID/RepID 均 1→1；RepSection 3→3；准确 B Position 0.650→0.650、Section SuccessorStart→SuccessorStart；28 字段通过 |
| SameAssetDifferentSection | A/B Started 1/1；ObservedID 与 CreatedID 均 2/3 | Call 1/2、Generation 2/2；A Superseded、B Accepted；NativeStage 均 Returned；Superseding 2/0；public/native/caller 返回均 A=0、B=1 | Local/Rep 保持同资产，owner 仍 B；LocalID/RepID 均 1→1；RepSection 3→3；准确 B Position 0.650→0.650、Section SuccessorStart→SuccessorStart；28 字段通过 |

原始日志数值 Outcome 3/1 对应 Superseded/Accepted，Stage 2/2 对应 Returned/Returned；日志明确 Test Completed. Result={Success}。这是有限真实 Guarded Started 入口的实际通过证据。原生 P1 最新独立证据仍为第17次真实 Fail，未被本次常规回归选择；不得把 Guarded Success 覆盖原生兼容风险。当前 Task 仍未消费 typed 输出/identity，未迁移生产资产，B4 未全部关闭。两 UE 退出由统筹确认，本组长没有启动或操作 UE。

### 唯一新增测试契约

- 普通 simple 自动化：`GGYGO.AbilitySystem.MontageGuard.StartedSuccessorPreservation`，EditorContext | EngineFilter，无 opt-in flag、skip 或 expected-error。`DifferentAssets` 与 `SameAssetDifferentSection` 分别构造独立 World/Authority Character/真实 Mesh、两 Spec/两 GA，第一场景失败仍执行第二场景。
- 头部仅新增 Guard include 和空的具体 `UGGYGOGuardedMontageStartedTestAnimInstance`；不覆写播放或任何 native 生命周期。CPP 复用既有独立真实 Started 夹具，在本场景初始化后、任何激活/播放前，仅对瞬态 Mesh 调用 `SetAnimInstanceClass` 并重读实际 AnimInstance。原 P1 初始化函数不改、不加 mode flag，不调用 NativeInitialize、不制造 generation。
- 已核对本机 UE 5.8：`SetAnimInstanceClass` 通过 Clear/InitAnim/InitializeAnimScriptInstance/InitializeAnimation 进入 native 初始化；ActorInfo::GetAnimInstance 从当前 Mesh 动态读取。前置严格核对 Guard 类/IsInitialized、注册 Mesh、Owner/Avatar、ASC ActorInfo 的同一实际 AnimInstance、Authority/Rep 记录路径、资产关系及同组/不同 Section。
- A/B 均从 ASC 公开 `PlayMontageWithGuard` 进入，OutResult 为本函数栈变量，AdditionalQuery 为空。真实 A Started 记录准确 ID/活跃与 IsPlaying，先 End A，再重装一次性 B Started 观察者并 TryActivate B；B Started 仅记录准确 ID/活跃，不再播放或结束。每个实例指针均只在无外调的小作用域内读值，不跨 End/激活/Stop 回调保存。
- B 公开调用返回后立即按 `ResultB.Identity.CreatedInstanceId` 捕获只读 Baseline；A 外栈返回后仍按同一准确 ID 取 After。两次读取间没有 World Tick、动画推进、延后执行或快照恢复，不以资产指针查到的实例代替 B identity。
- 严格前置包括真实 Started A/B 各一次、A 结束后才激活 B、B Accepted/有限正返回、准确 B ID 与 Started ID 相同且不同于 A、准确实例存活/活跃/IsPlaying、活动资产 lookup ID 一致、Local/GA/Rep 正确及 SuccessorStart/0.65/1.25。前置失败为真实 Fail，并明确不构成后继保持证明，安全停止字段比较并清理。
- 有效基准后汇总 typed 结果断言：A Superseded，公开/native/caller 均 0；B Accepted、native/caller 均有限正值且等于公开返回；两 NativeStage Returned；A SupersedingCallId 指向 B，B 为 0；两 CallId 非零递增、generation 非零相等、OriginalAnim 相同；CreatedId 与真实 Started ID 匹配且互不相同。A 的结果不作为前置过滤，错误会作为契约失败完整报告。
- A4 对两份 identity 只作原生命周期/已发身份查询；另独立按 B ID 查询准确资产、活跃/IsPlaying、活动资产 ID、Section/Position。A4 不替代实例存活或 ASC/GA 所有权证明。
- 每个场景严格比较 28 个后继字段：Local 资产/owner/PlayInstanceId（3）；A/B GA CurrentMontage 与 active（4）；Rep 资产/PlayInstanceId/Section/Position/Rate/IsStopped/NextSectionID/SlotName/BlendTime/BlendOutTime/PlayCount/三个复制标志（14）；准确 B 存在、ID、活动资产 ID、active、Position、Section、Rate（7）。另显式要求 After 仍处 SuccessorStart/0.65 且 IsPlaying。日志记录结果 outcome/stage、CallId/generation/CreatedId/接管 ID/三种返回及 B-return → A-return 快照。

### 清理及架构核对

- call-local RAII 在全部观测/断言之后运行，失败路径也执行；先 Disarm 观察者，清空两 GA 未消费的 K2 action，避免栈引用被后续回调调用。
- 只操作捕获的原 Guard、原 Mesh/Avatar 和本场景准确创建/Started ID。每次直接 Stop 前重读原对象/归属/初始化，准确 ID 与资产匹配才停止；每次 Stop 后不再解引用实例指针。BlendOut 从本 Montage 的 args/mode/profile 构造，清理 blend time 为 0。
- 原 ASC ActorInfo 的 Owner/Avatar/Mesh/Anim、当前资产/能力、A4 身份及准确活动实例 ID 均吻合 B 时，通过 `CurrentMontageStop(0)` 清理 GAS 复制链；否则不按资产指针停止 ASC 当前播放，仅清理仍属于本场景的原准确实例。随后结束 A/B，夹具/World RAII 完成销毁。部分初始化失败时尚未安装动作或播放，由原夹具/World 析构清理。
- 未创建 Task/scale token、guard scope、map、代次计数或第二执行器；typed scope/身份全部由已冻结生产 Animation/ASC 生成。测试只持本次观察与快照，沿用 GA/GAS 原执行与清理入口，没有跨模块内部状态 setter、循环依赖或业务资产接线。

### 静态证据、冻结身份与运行边界

- 实际差异：工具会话内保存开工原文后，逐行 LCS 比较 H 新增 8 行、CPP 新增 304 行，零删除/零改写；恢复保留行后与原文本逐字节相同。原生 P1 全部注册/flag/初始化/红断言及 RateLease/after-Super/manual-instance 夹具完整保留，既有未提交变更未丢弃。没有 Git 操作或工作区备份文件。
- 静态检查：两源码零尾空白、词法括号平衡、generated include 为最后 include；新增部分仅两个公开 typed play、两个空 AdditionalQuery、28 个后继比较；无 AddExpectedError、旧播放 hook/手工实例、新 scope、NativeInitialize 直调或播放覆写。核对本机 IsInitialized、ActorInfo、准确实例、FAlphaBlendArgs/Stop/CurrentMontageStop API。
- 冻结 SHA256：测试 H `BEC4C9B7F4C50BD4448011EAFAB79EB5E5335E57246064583E12E7216D2847A4`；测试 CPP `39E71D2DEFF7B98197B88B30C36652A108976E31CCB0EAACC41B1502B5681567`。
- 只读依赖哈希保持：ASC H `E9AEB8AE04165D05DA8C6C18EB07B18F5C7DCB6D8A4AE0702B1D117845BC95E5`、CPP `4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF`；A1 `ACAEA0FD27ED2F474C8BC107886860BD7DADE72F452902A748B7F8AFE4E3855A`；Guard H `6BD6A6DC686074608213F5DF567957D1F10A2D5DBB537BD8C70E0687BA910766`、CPP `2357E96AF6F312FE2C691A09C79988DC10A6FC578B48AF96604CE1D5D9621995`。
- 历史静态交回时新增正向用例尚未编译/运行，第18次构建失败也未产生运行证据；**第19次现已完整构建并实际 Success、0 errors/warnings**。两测试源码哈希保持原冻结身份。原生 P1 仍独立选择/flag 复验，不能混为正向成功；当前通过只证明上述两个有限 Started 契约。
- 非目标仍为实例建立前拒绝、post-write 失效/多层与网络矩阵、FractionalLoops/Simulated、生产 Task typed/A4 消费及 Kevin ABP 父类迁移。未写生产源码/资产、Obsidian 或全局文件，未操作 UE/构建/Git/代理；本授权窗口仅登记 04 局部状态，架构笔记的后续同步待单独授权。B4 不宣称全部关闭。

原四文件实施交回已结束，两个测试源码持续冻结；本次仅同步两记录后再次冻结。普通正向运行入口 `GGYGO.AbilitySystem.MontageGuard.StartedSuccessorPreservation` 已由统筹实测通过。

## Task 消费拆分预检（只读候选已接受，T1–T5 均未获实现租约）

### 当前职责、输入输出与冻结依赖

- 当前旧 Task 全局 FMontagePlayAttemptMap/FScopedMontagePlayAttempt 按 AnimInstance/Task 发 token，任何嵌套尝试即标记全部祖先 Superseded，不等子播放成功；不识别 Montage group、原 ASC coordinator 或动画 generation，裸 ASC 子调用也不进入 map。返回后另扫描唯一新实例。它与 Animation 成功后继裁决不同；候选 Guard 分支只消费已冻结 ASC typed 结果/Animation identity，不再参与旧机制。
- 生产实现候选输入为原 Task/Ability/ASC、Avatar/Mesh/Anim 及播放配置；输出为栈上 FGGYGOMontagePlayGuardResult。scope 和 coordinator 唯一归 ASC，identity/结果优先级唯一归 Animation。Task 只持本次资源句柄和 Accepted 后的只读 identity，现有 MontageInstanceId 如保留仅为 CreatedInstanceId 的派生资源索引；不新建 scope、map、播放计数、激活代次或最近结果缓存。
- 额外查询仅纯读弱 Task 存在、未 bEndingTask/Finished、仍为捕获任务上下文，不调用可能记录 warning 的 ShouldBroadcastAbilityTaskDelegates，不重复 ASC 权限裁决。ASC 本次 End/Cancel 锁存防止零预测键/同 GA 再激活复活旧调用，Task 终止状态防止旧任务再采纳；A4 不代表能力激活身份。
- Accepted 候选还须证明原 identity 当前、准确 CreatedId 的资产/活跃/IsPlaying、活动资产 lookup ID 相同及 ASC/GA 当前归属吻合，之后才保存只读身份、绑定自己的准确实例委托和获取 scale token。A4 不替代实例存活或权限。
- Superseded 候选不扫描、不停止 B、不获取资源、不改写 Animation 裁决；已结束 Task 不广播，活 Task 按取消语义结束。其它未接纳结果不绑定/获取资源、不失败回退；没有 CreatedId 不停任何实例，存在 CreatedId 仍需独立原资源清理证据。
- Guard Anim 配普通 native ASC 是显式不支持组合，已接受候选为播放前拒绝并取消、不回退，目标仍是项目 ASC。非 Guard 原生入口及旧兼容 map 当前保留；不能宣称全项目零旧机制或原生 B4 风险消失，整体删除须另步证明或生产资产迁移门禁。

### 清理责任与失效边界（候选，尚未实现）

- 工作有效性与释放原资源权限分开。Task 结束后仍可移除原 Ability/ASC 的本次句柄、原准确实例上 GetUObject==本 Task 的委托和原 Character 的本次 scale token；不能清公共委托、通过新 ActorInfo反查原资源，或停资产指针查到的后继。
- UE UAbilityTask::OnDestroy 会清空 Ability。播放外调中 Task 已结束、成员 ID 尚未取得时，补清理必须消费栈上原 identity/准确 CreatedId 和捕获的原对象，不把输出绑定到已结束对象成员，不再扫描“唯一新实例”。所有实例指针外调后重新解析。
- ASC 停播须独立证明原 ActorInfo/Owner/Avatar/Mesh/Anim、当前能力/资产、准确活动 ID；证据不足不调用 CurrentMontageStop/ClearAnimatingAbility。Avatar 已更换时只清仍归原 Avatar 的准确实例/句柄/scale，不影响新 Avatar。原 generation/owner 失效不能靠旧 ID 猜测新权限；A4 未观测的 Owner/Avatar A→B→A 仍不承诺完全检测。
- 同 GA End→再激活、自然混出、结束/取消/普通 EndTask 和播放期间 owner end 的资源路径须分别验证。scale lease 沿用原 token helper：仅最新 token 恢复原 baseline，旧 A 释放不覆盖 B；不把 scale token 当成播放 identity。

### 用户待决定的自然混出行为（统筹已提问、尚无答复）

现有 IsCurrentASCPlaybackInstance(..., true) 在无活动索引时允许清归属。UE 原生 Stop 先移除活动索引，再触发/排队混出；同 GA、同资产后继也停止时，资产/能力指针与 A4 无法证明 ASC 记录属于旧 A。冻结接口未提供准确关联，Task 不能自建第二关联表补洞。

- 选择一：证据不足时保留归属至 GAEnd；仍释放本 Task 的 scale、发送有效混出通知，但不 ClearAnimatingAbility。会改变原提前清空时机。
- 选择二：保持原混出清空时机，另设计准确 ASC 归属查询；须重新预检并明确共享接口唯一所有者/租约。

两种选择均未实施，未扩大 ASC/Guard 接口。收到用户决定及统筹新的精确实现授权之前，T1 不开工。

### 原子步骤候选、断言与停止点

以下路径相对项目根目录。R 精确指本文件及 `AAADocs/Modules/CombatActions/Module_Repair_04_Subleases.md`；G1 为新 `Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskGuardedLifecycleTest.cpp`，G2 为新 `Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskGuardedTestTypes.h`。G1/G2 尚未创建；新夹具可复用冻结的测试能力/空 Guard/Started 观察类型，不移动或改写既有 P1/RateLease/StartedPositive 原文。

| 候选 | 唯一目标与精确写入候选 | 验收断言 / 输出 / 停止点 |
| --- | --- | --- |
| T1 | Task Guard 消费及本次资源归属；`Source/GGYGO/AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.h`、同名 `.cpp`、R，共4文件 | 单次公开 typed 调用与纯 Task 查询；准确 identity 采纳/清理；旧 A 不停/清 B；非 Guard 兼容原行为保留；无新 scope/map/counter。输入为冻结 ASC/Guard/scale 接口和已决定行为，输出仅 Task 两源码及局部记录；静态审查冻结交回，需改共享接口立即停止 |
| T2 | 真实 Started 后继 Task 资源保持；G1、G2、R，共4文件 | 两 GA，不同资产/同资产不同 Section；真实 Ready，B 的准确实例/Section/ASC/GA、事件监听与 scale 在 A 返回后保持。T1 接口先冻结；仅测试输出，交回统筹运行，不修生产或重写旧用例 |
| T3 | 无后继同步 owner end；G1、R，共3文件 | stop=true 只停准确 A，stop=false 保留原动画；均结束 Task、无委托/scale 泄漏、不恢复已结束 GA。复用已冻结 T2 夹具，专项冻结交回，不扩其它生命周期 |
| T4 | 同 GA End→再激活；G1、R，共3文件 | 旧 Task 不复活；新 Task 的准确 ID、监听、scale、GA 状态保持。复用冻结接口/夹具，专项冻结交回，不引入激活计数或修改 GA |
| T5 | 已采纳 Task 的 Avatar 更换清理；G1、R，共3文件 | 取消旧 Task仅清原资源；新 Avatar 的 B 实例/监听/scale/ActorInfo 保持。复用冻结接口/夹具，专项冻结交回，不迁移生产资产或扩大原生生命周期矩阵 |

依赖图：第19次完整构建/StartedPositive 实际通过（已满足）→ 用户自然混出决定/候选契约冻结/统筹精确实现租约（未满足）→ T1 → T2 → T3/T4/T5 分步审查运行。各步共享文件串行换手，不并行写同文件，源码冻结后统一编译由统筹执行。生产实现与测试不混为同一步。

非目标统一为 ASC/Guard/GA 改造、旧三项测试改写、Kevin 生产 ABP 父类迁移、完整拒绝/失效/预测网络矩阵、Obsidian/全局入口；自然混出选择二若需 ASC 接口另开预检，不从本表推导授权。Task 只读基线 H `6C75E4233254776D98BE6371F57EDF60724E453E8275B5BF7691749AB59185B3`、CPP `506AAFB79129EED88485BF8185284CA13781CCE21F6796F907C334F1E1B1D02D`。

本次两记录同步完成后冻结，T1–T5 均未开始。未运行 UE/构建/Git/代理，未写源码、测试、资产、Obsidian 或全局文件。

## 04B4-ASC 受保护入口（2026-09-30，历史静态交回，已于第17次编译）

统筹在第16次完整构建成功（6 actions、20.22 秒）及常规 48/48 Success 后开放 ASC 两源码和 04 两记录，当时由 `gpt-6.1-sol / high` 组长直接实施，无代理。以下实现/静态检查描述保留当时交回状态；第16次是新增源码前置，之后第17次已完整编译，第19次有限 Guarded Started 实际通过见上，不把历史“未运行”当成当前事实。

### 实现及接口

- 唯一实现文件：`Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h`、`.cpp`。新增公开 C++ `PlayMontageWithGuard(InAnimatingAbility, ActivationInfo, Montage, Rate, Section, StartTime, OutResult, TFunction<bool()> AdditionalQuery)`，没有 UFUNCTION、外部 coordinator 参数、兼容开关或结果缓存。
- 普通 `PlayMontage` override 读取原 AnimInstance：Guard 路径调用同一受保护入口；非 Guard 路径仅唯一调用原生 Super，保持原返回值和原风险，不承诺顶层/嵌套 B4 保护。受保护入口非 Guard 由 A1 得到 Unsupported，CanExecute=false、Complete(0)，不执行 Super、不失败回退；原 Anim 已缺失则保留 A1 LifecycleInvalid。
- Request.CallerIdentity 固定为捕获的原 ASC；AdditionalQuery 只是额外纯查询。普通入口传空额外查询，不把不同 Task 当成不同 coordinator。
- `FGGYGOMontagePlayGuardScope` 位于调用栈，顺序为 Construct → CanExecute → 完整唯一 Super::PlayMontage → Complete → 复制 GetResult → 析构。scope 涵盖 GAS 的 Local/GA/Section/Rep/预测绑定，不拆出或复制引擎执行器。
- OutResult 每次覆盖为本次封存结果副本，只有 Accepted 暴露正的 caller return；其他 Outcome 返回 0。ASC 不重写 A1 的 Outcome、identity 或 SupersedingCallId；已结束 A 的有效 B 由自身上下文接纳，成功 B 对 A 的 Superseded 裁决不被 ASC 的 AEnded 状态覆盖。

### 原上下文及本次激活观测

- 保留原 ActorInfo 的共享分配身份，并分别捕获原 ASC、Owner、Avatar、Mesh、Anim、能力实例、Spec handle 和传入的激活预测键；不只比较可被原地改写的 ActorInfo 指针。
- 每次纯查询重读当前 ActorInfo 与原字段，检查 Mesh/Anim 的原 Avatar 归属、能力活跃/实例化、CurrentActorInfo/Spec handle/激活键。额外查询先于取 Spec 指针；随后重新 FindAbilitySpecFromHandle，检查 Spec 存在、有能力、未 PendingRemove、活跃且仍含原实例，不保存 Spec 指针跨回调。
- 预测键只是额外上下文校验，不能单独识别零键的同实例重激活。栈上 `FScopedMontageAbilityLifetime` 绑定原能力 EndWithData/Cancel，End 还核对原实例和 handle；本次结束/取消后锁存无效，即使原实例马上重新活跃也不复活旧调用。
- 观测对象不可复制/移动，先于 guard 构造、晚于 guard 析构；每条返回路径按原弱能力对象 Remove 本次两个句柄。没有清空能力公共委托，也不持有新激活的状态。原能力已经销毁或已清空 End 委托时，清理安全退出。
- 查询不广播、记录日志、播放、变更所有权或调用 ShouldBroadcastAbilityTaskDelegates；没有帧调度、timer、map、持久 activation counter 或 ASC last-result。

### 静态审查及冻结身份

- 开工基线：H `5C96A8DE131E35582F79FDE5F87757991A39B5C24E94CBA99FDB01FE3C9EF3C6`，CPP `3CA7B55AC368B332CC1645E375FBCF2E3A049818EC35265A15E7C7FF4EA092E5`。
- 实际差异以工具会话中保留的原文本与当前文本逐行 LCS 比较：H 新增 16 行、CPP 新增 144 行，原行零删除/零改写。输入、重试、组仲裁、ActorInfo 绑定及其余既有未提交改动完整保留；没有运行 Git diff/写操作或创建备份文件。
- 核对本机 UE 5.8 的 PlayMontage override 签名、FAbilityEndedData 两字段、原生委托绑定/移除、实例化 getter 前置、预测键比较、const ActorInfo/Anim/Mesh 查询以及临时 Spec 的实例列表查询。核对 A1 全调用 scope/结果副本和 A4 公开身份查询；不改共享接口，A4 当前无需在 ASC 再建身份状态。
- 新增源码行尾空白、词法括号、generated include 顺序及禁用路径静态检查完成。历史交回时组长未本地构建/运行 UE，独立真实 Started 尚待授权；后续实际构建/运行由统筹执行，第19次真实结果见上。
- 源码冻结 SHA256：H `E9AEB8AE04165D05DA8C6C18EB07B18F5C7DCB6D8A4AE0702B1D117845BC95E5`；CPP `4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF`。
- 当时只读共享依赖：A1 `ACAEA0FD27ED2F474C8BC107886860BD7DADE72F452902A748B7F8AFE4E3855A`；A4 H `6BD6A6DC686074608213F5DF567957D1F10A2D5DBB537BD8C70E0687BA910766`、CPP `2357E96AF6F312FE2C691A09C79988DC10A6FC578B48AF96604CE1D5D9621995`。当时 P1 两测试尚无新增正向内容；后续仅追加独立 StartedPositive，原 P1 文本完整保留，当前两测试文件哈希见本文件顶部冻结记录。

### 阶段限制与架构核对

- 本次只关闭 ASC 消费源码原子步。Task 生产代码仍是旧消费者，其全局 FScopedMontagePlayAttempt 尚未撤除，也没有接入新 typed 输出或 A4 identity 查询；不能据此宣称 Task 已迁移或 B4 已修复。
- 普通入口在 Guard Anim 上开始受守卫有限规则约束；非 Guard Task 因仍调用普通入口而保持原生兼容，未全局切换到严格受保护入口。Kevin 生产 ABP 父类迁移未执行，不用兼容开关、第二 Task 执行链绕过阶段门禁。
- A2 同组/同 coordinator、拒绝不同组活跃实例、拒绝 scoped bStopAll=false、Precreation/PostWrite 拒绝等限制原样保留。FractionalLoops 私有 GAS 入口和 Simulated 独立路径未覆写，预测/双端网络完整矩阵不在本步。
- Complete 不回滚 GAS 写入；任意绕过 Guard Super 的派生播放实现、post-write 任意上下文失效，以及未被生命周期或上下文查询观测的 Owner/Avatar A→B→A 变化，不能冒称已全面阻止。A4 只读身份查询也不证明权限或 engine instance 存活。
- 模块归属保持 Animation 管 native 返回屏障/生命周期/调用链，ASC 管 GAS 入口/能力上下文，GA 保持能力生命权威；本次结束布尔仅是单次调用的原生事件证据，不是第二激活状态机。没有修改 GAS 动画状态、播放实例、scale token、资产或其他模块。
- 本轮禁止 Obsidian/全局文件写入；阶段状态记于本记录，后续图文与生产接线由对应授权窗口同步，不把有限候选写成完成。

当时四文件静态完成后冻结交回，后续第17次构建与第19次有限专项已由统筹执行；ASC 两源码继续冻结，当前没有 Task、测试或资产接入实现授权。

## 04-P1 真实 OnMontageStarted 诊断（2026-09-30，真实红测已核对、记录冻结交回）

统筹在新完整构建成功（25.49s）、`ModuleRepairGate_20260930_13` 常规 GGYGO 47/47 成功、0 测试 warning/failed、UE exit0 后授权 P1。该门禁发生于本次诊断新增之前，不是 P1 的构建或运行证据。本次由长期组长 `gpt-6.1-sol / high` 直接完成，无代理。

### 统筹实际构建与运行结果（组长只读核对）

| 门禁 | 原始证据（相对项目根目录） | 实际结果 |
| --- | --- | --- |
| 完整构建 | `Saved/Logs/ModuleRepairBuildGate_20260930_14.log` | `GGYGOEditor Win64 Development`、6 actions，`Result: Succeeded`，14.31 秒；包含新增 P1 源码 |
| 常规 GGYGO 回归 | `Saved/AutomationReports/ModuleRepairGate_20260930_14/index.json`、`Saved/Logs/GGYGO_ModuleRepairGate_20260930_14.log` | 47/47 Success，0 warning/error，0.421443 秒；报告时间 2026-09-30 02:54:52 UTC（北京时间 10:54:52）；报告无 ProjectDiagnostics 项，P1 未被常规回归枚举，进程 exit0 |
| 显式 B4 诊断 | `Saved/AutomationReports/ModuleRepairB4Diagnostic_20260930_14/index.json`、`Saved/Logs/GGYGO_ModuleRepairB4Diagnostic_20260930_14.log` | 唯一诊断 `Fail`，0 Success、16 errors、0 warnings，0.120586 秒；报告时间 2026-09-30 02:56:03 UTC（北京时间 10:56:03）；进程 exit0 **不等于测试成功** |

组长逐项核对 JSON 与日志：16 errors 全是后继保持断言，`Prerequisite` 错误为零；两个场景均已进入前置门禁后的比较，真实 Started 各为 1，A/B 播放返回均为 1.000、实例 ID 不同。结果证明当前生产代码下 B4 的真实同步写回缺口成立，P1 复现目标完成；缺口尚未修复，不将预期红作为产品通过。

- `DifferentAssets`：A/B 实例 ID 为 0/1。7 项失败为 `Local.AnimMontage`、`Local.AnimatingAbility`、`Local.PlayInstanceId`、`GA.A.CurrentMontage`、`Rep.Animation`、`Rep.PlayInstanceId`、`Rep.IsStopped`。B 返回时 Local/Rep 为 B 资产、owner 为 B，A 返回后变为 A 资产/owner，Local 与 Rep ID 均从 1 变 2；准确 B 实例的位置/Section 保持 0.650/SuccessorStart，不能把记录覆盖误写成该场景的位置失败。
- `SameAssetDifferentSection`：A/B 实例 ID 为 2/3。9 项失败为 `Local.AnimatingAbility`、`Local.PlayInstanceId`、`GA.A.CurrentMontage`、`Rep.PlayInstanceId`、`Rep.SectionIdToPlay`、`Rep.Position`、`Rep.NextSectionID`、`Instance.Position`、`Instance.Section`。Local owner 从 B 变 A，Local/Rep ID 均从 1 变 2，RepSection 从 3 变 2；捕获 ID 的准确 B 实例位置从 **0.650 变 0.200**，Section 从 **SuccessorStart 变 OuterStart**。
- 诊断日志明确 `Test Completed. Result={Fail}`、队列完成 1 test；随后 `RequestExitWithStatus(1, 0, ...)` 只表示进程按 TestExit 退出。报告 Fail 与 16 errors 为诊断验收依据，不能以 exit0 覆盖。
- 复核时两测试源码 SHA256 与原冻结身份一致。本次不修改源码/测试/资产/Obsidian，只更新两份 04 局部记录；没有自行构建、运行 UE、Git 操作或代理。

### 已实现的唯一测试契约

- 两源码文件新增 test-only 只读 ASC 派生类和真实 Started 的一次性 UObject 动态委托观察者；观察者先解绑，再执行 End A → TryActivate B。ASC 只复制 Local/Rep 记录，没有 setter、播放覆写或恢复快照。
- 使用独立临时 Game World、Authority Character、只读 SkeletalCube 的真实 render data/Skeleton、原生 `UAnimInstance`、两份 Spec/两 GA 实例和合成 Montage。不使用现有 after-Super hook 或手工构造 Montage instance。
- 一个 complex 诊断用例运行两个隔离场景：`DifferentAssets`；`SameAssetDifferentSection`。场景布尔值显式传入夹具初始化，没有默认值。OuterStart=0.2、SuccessorStart=0.65；A/B 请求速率分别 0.75/1.25，Montage 长度为 1。
- A 的真实 Started 回调中确认已建立活跃实例，结束 A 后激活 B。B 的 ASC PlayMontage 返回后立即捕获只读基准；A 外层激活返回后按捕获的 B instance ID 准确读回。两观测之间没有 World Tick、动画推进、异步排程或恢复操作。
- 前置条件单独汇总：Authority/复制记录路径、原生 AnimInstance、资产/Section 关系、A Started 一次与真实活跃实例、A 已结束、B 接纳与正播放返回、B 新 instance ID/活动资产身份、Local/GA/Rep、0.65 位置/SuccessorStart/1.25 速率均正确。前置失败明确报告不能作为 B4 写回证据。
- 前置有效后，每个场景汇总 28 个严格比较：Local 资产/owner/PlayInstanceId；A/B GA CurrentMontage 与活跃状态；Rep 资产/PlayInstanceId/SectionIdToPlay/Position/PlayRate/IsStopped/NextSectionID/SlotName/BlendTime/BlendOutTime/PlayCount/三个复制标志；B 精确实例是否仍存在、ID/活动资产 ID/活跃/位置/Section/速率。第一条结果失败不会截断后续比较或第二场景。
- 原始生产代码上预期这些后继保持断言失败；没有反转断言、`AddExpectedError`、NegativeFilter 或失败转绿。A 外层 Duration 仅记录，不要求其正值，避免把未来正确的被取代返回强制判失败。

### 枚举隔离与统筹运行交接

最终枚举名：`ProjectDiagnostics.B4.MontageStartedReentry.LocalRepGaSectionInstance`。complex 的基础名为 `ProjectDiagnostics.B4.MontageStartedReentry`，子项名及参数为 `LocalRepGaSectionInstance`；已核对 UE 5.8 `GenerateTestNames` 的拼接规则，不重复完整名称。

- 只有启动参数 `-GGYGOB4ReentryDiagnostic` 存在时，`GetTests` 才提供唯一用例；无参数为零枚举，不进入 RunTest，也不生成跳过成功。
- 常规 `GGYGO` 测试名筛选不匹配该显示名。统筹已启动带开关的进程并显式运行唯一诊断；组长本次只读核对，不自行执行 UE 命令。后续复验仍使用独立选择 `Automation RunTests ^ProjectDiagnostics.B4.MontageStartedReentry.LocalRepGaSectionInstance$`。
- 运行应分别核对两个场景前置成功，再检查严格结果失败及 B-return → A-return 记录。若前置失败，先返修夹具；若严格结果全通过，不冒称已复现，核对真实调用顺序。红结果须保留为真实失败。
- 统筹已完成本次完整构建，并分别留存常规回归与显式诊断报告；P1 真实红测成立。后续新增源码须再次全部冻结后由统筹构建，不借 P1 完成继续写生产实现。

### 静态证据、范围及冻结身份

- 新增部分移除后重算 UTF-8/LF SHA256，两份旧文件与批准基线逐字节相同：CPP `A10218B6AB1D4FB9F4D26EBF517A4DF9CC7E902314C947EDCA8910D97DC62D80`，H `B31DF5980E38F8DA3C21BA1AA5361B5B02D72BA29AADF2C3BAFF7487CD47EFF2`。原 `RateLeaseAndLifecycle` 实现、既有 hook 与全部断言完整保留。
- 完成词法括号/行尾空白、generated include 顺序、动态委托签名/解绑、初始化调用参数、complex 命名/枚举、析构清理顺序及本地 UE 5.8 API 核对。静态过程中统筹指出的遗漏场景参数已修正，未以默认参数掩盖同资产场景。
- 两源码冻结 SHA256：CPP `E9928040626D331EAD174214E371922E0FCDC57B2ABB26A5EB695FA6BB437ABC`；H `BEE7E1BB0BC57B4920C07AF5AC289B71896D0F3DABC380559F6E64E3CA37DC0D`。
- 本次只写 `Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskLifecycleTest.cpp`、`GGYGOMontageTaskTestTypes.h` 以及本验证记录、`Module_Repair_04_Subleases.md`，四文件完成后冻结。没有构建、UE、Git、资产或其他文件写入。
- 架构核对：GAS/Animation 的状态与执行器保持唯一，测试仅持有同步只读快照和短期委托句柄；观察者解绑先于嵌套播放，RAII 在 World 销毁前解绑并结束两 GA；不新增生产状态、帧调度器、跨模块接口或循环依赖。
- 用户已批准薄 Animation 安全父类、实例建立后 Started 内立即接续及拒绝实例未建立前混出嵌套的有限候选进入验证；候选行为仍未实现/验证。Animation 已获 A1 共享声明三文件租约，其接口归 Animation 唯一所有；04 当前仅更新两记录，不改接口或 ASC/Task 消费者。P1 不覆盖预测拒绝、双端网络、FractionalLoops/Simulated、第三方直接播放或生产 AnimClass 迁移，不能据此关闭 B4。Obsidian 与全局入口本轮禁止写入；本记录交回当前诊断状态，后续由对应授权门禁同步。

记录更新完成后两记录冻结交回；两源码继续冻结，无新增实现权限。以下为 P1 之前的历史验证与交接，不能覆盖上节最新构建、常规回归及真实诊断失败。

状态：统筹最终完整 C++ 构建成功；`Admission.GroupLifecycle` 单项 1/1 成功，随后统一自动化 38/38 全部成功，0 warning、0 error。单项诊断曾确认 C(18) 正确拒绝较旧 B(17)，旧 post-cancel 复核从 Spec 实例列表误命中已注销组登记、仍处于 GAS 结束广播栈的 A(sequence 0)；`HasActiveAbilityMatching` 改为只遍历 ASC 权威 `ActiveAbilitiesByGroup` 后，C 保持活跃、B 安全退出，严格唯一实例/ActiveCount/组登记断言通过。尚未执行 PIE。B4 仍有下述引擎内部嵌套播放写回缺口，不标记整体闭环。

## GroupLifecycle 自动化返修（权威组登记终检已通过）

- 第二次统一运行证明，首次把最终裁决移到 ActiveCount 递增后的时序修复仍不足以解决同 Spec PerExecution 递归。门禁日志只留下最终活动实例为 0，未记录 B/C 的中间身份与计数。
- `NotifyAbilityActivated` 现在只开始 attempt 并登记 `ActiveAbilitiesByGroup` 预留，不在 GAS 递增本次 `Spec.ActiveCount` 前取消或结束任何实例。
- ASC 为每次 PreActivate 分配跨实例唯一、非零单调递增的 admission sequence；GA 实例只保存由 ASC 分配的 attempt 记录。`FinalizeAbilityGroupAdmission`、拒绝标记、拒绝消费和完成清理全部按捕获 sequence 定位，不再借 PredictionKey 识别同步 attempt。
- `GroupLifecycle` 增加 B/C 实例捕获和中间证据：A 结束回调入口 ActiveCount 应为 1，C 的 Try 返回后 B/C 应为 2，C 在回调内及外层 B 返回后仍须活跃、有效并留在 Spec 实例列表。原最终断言保持为唯一活动实例、`Spec.ActiveCount == 1`、组登记为 1，未削弱期望。
- 返修只改 ASC/项目 GA 四个 runtime 文件和 Admission 测试；已完成签名、lambda capture、旧准入字段、行尾空白和范围内交叉引用静态检查；按租约未本地构建或运行 UE。

第四次统一运行进一步证明：A 结束回调入口 ActiveCount 为 1，但 C 的嵌套 Try 返回时已经降为 1，C 已不活跃；外层返回后 C 被移出 Spec，最终 ActiveCount/组登记均为 0。UE 5.8 的 PerExecution `NotifyAbilityEnded` 在广播后才移除具体结束实例，因此这次递减发生在 C 自己的 Try 内，不是外层 B 返回后的清理。现有源码静态推演无法唯一证明 C 是准入 Reject 还是其他 Cancel 路径，本轮未猜测修改 runtime；测试派生能力新增 Activate 调用 Super 前后与 End 进入前的实例、ActiveCount、IsActive、ReplicateEnd、bWasCancelled 观测，下一门禁可区分项目准入拒绝（replicate+cancel）、取消路径和引擎/Spec 清理。原严格断言全部保留。

第五次统一运行给出顺序证据：B Activate 前 ActiveCount=2；C Activate 前 ActiveCount=2；C 以 ReplicateEnd=1、Cancelled=1 结束；随后 B 也以同样参数结束。两者都进入项目 GA 的 admission reject 分支，形成双向淘汰。原因是旧 generation 在每个 GA 实例内各自从 1 开始，B/C 无法比较跨实例先后。最终修复把 sequence 分配收回 ASC；Finalize 先用现有冲突谓词处理 pending 竞争者，较新的 sequence 只拒绝较旧者，遇到较新竞争者则拒绝当前旧尝试，再把 settled 能力交给原取消/复核路径。B 返回后先识别自身已拒绝并退出，不能反向淘汰 C；未新增第二状态机。

第六次统一运行证明全局 sequence 修复已编译，但结果仍为 37/38。随后加入 `WITH_DEV_AUTOMATION_TESTS` 裁决原因观测并单跑 `Admission.GroupLifecycle`：C sequence 18 正确执行 `reject-other` B sequence 17，取消后 C 未被拒绝；post-cancel 的 `HasActiveAbilityMatching` 却命中 A sequence 0。A 已在项目 `NotifyAbilityEnded` 调用 GAS Super 前从 `ActiveAbilitiesByGroup` 注销，但 UE 的 Spec 实例列表要到结束广播完成后才移除，旧终检因此把结束中的 A 当成竞争者。产品修复将该终检改为只遍历 `ActiveAbilitiesByGroup` 中有效、active、未 rejected 的已登记实例，并继续复用同一取消谓词；`IsActivationBlockedByGroup` 终检和全部严格断言保留。

## 合成 Montage 测试夹具返修（第五次统一自动化已通过）

- `UAnimMontage` 在 UE 5.8 构造时已经带有唯一 `DefaultSlot`。两个夹具再次追加同名 Slot track，导致轨道数为 2，均在进入产品生命周期断言前返回 false；这是测试基础设施问题，没有证据指向 Montage Task 或 Combo 产品逻辑。
- MontageTask 和 PlayerCombo 夹具现在复用构造器提供的唯一轨道，并加入带相同 Skeleton、正长度的真实 `UAnimComposite` segment；前置条件改为公开 `IsValidSlot`、唯一 segment、Skeleton 身份、有限正长度和 segment 边界检查。Combo 还保留 Main < End < Montage length 检查。
- Character、注册后的 Mesh、AnimInstance、ASC、Trace 以及后续真实 `ReadyForActivation`/播放/生命周期断言均保留。生产 Task、Combo、测试 Types 和资产均未修改。

第四次统一运行已越过此前初始化失败。MontageTask 的产品断言没有报告失败，但测试夹具还存在三项问题：隐式恢复 `AbilitySystem.GlobalAbilityScale` 被 UE 5.8 拒绝替换 Constructor 优先级；`NewObject<UObject>` 触发 abstract ensure；瞬态 SkeletalMesh 无 render data 产生动画警告。随后用显式 `Set(Value, 原 SetBy)` 成对恢复值与优先级，以具体测试 UObject 作为 lease owner，并只读加载 `/Engine/EngineMeshes/SkeletalCube.SkeletalCube` 的真实 Skeleton/render data。Combo 两项同样改用该资产，并从 reference skeleton 取两根真实骨名供 Trace，不修改或保存引擎资产。所有真实 AnimInstance/Montage/ASC/Trace 断言保留；第五次统一自动化已验证通过。

## 首次统一构建反馈（历史，后续已修复）

- UHT 已通过，说明本批新增反射类型和生成头阶段未报错。
- C++ 编译失败一：`GGYGOMontageTaskLifecycleTest.cpp:63` 与 `GGYGOPlayerComboLifecycleTest.cpp:101` 在测试派生类外展开 `GET_FUNCTION_NAME_CHECKED(UGameplayAbility, K2_ActivateAbility)`，访问了 UE 5.8 中受保护的成员。修复限定为测试派生类内部的静态函数名 helper，不改生产能力接口。
- C++ 编译失败二：`GGYGOPlayerComboLifecycleTest.cpp:486/516` 使用 UE 5.8 不提供的 `TNumericLimits<float>::QuietNaN/Infinity`。修复限定为 `<limits>` 的 `std::numeric_limits<float>::quiet_NaN()/infinity()`。
- 这次失败发生在测试代码编译阶段，不能据此宣称生产代码已完成 C++ 编译或链接；修复后仍须由统筹重跑完整构建。组长不在本退回任务中自行构建或运行 UE。
- 退回修复结果：两个测试派生能力各自新增静态函数名 helper，将受保护成员检查宏移入派生类成员上下文，`ProcessEvent` 继续按精确 `FName` 比较；PlayerCombo 测试已改用标准库非有限值，并包含 `<limits>`。四个测试文件已做范围内符号、行尾空白、词法括号及 generated include 顺序检查；没有修改生产代码。结果仅表示编译错误源已静态修正，完整构建仍是待执行门禁。

## 第二次统一构建反馈（历史，后续已修复）

- UHT 与全部 C++ 编译均已通过；首次退回的受保护成员和 `TNumericLimits` 编译错误已消失。
- 唯一链接错误为 `GGYGOMontageTaskLifecycleTest.cpp` 的测试夹具调用 `UAnimMontage::HasValidSlotSetup()`；该 helper 在当前 UE 5.8 模块边界未导出，产生 `LNK2019`。
- 修复限定在该测试 `.cpp`：移除未导出 helper 调用，改用已公开的 Slot track、Anim track/segment 数据或公开接口验证合成 Montage 的测试前提，保留播放长度、Section 和后续真实播放断言。生产代码及测试 Types 均不修改。
- 第二次构建仍未完成最终链接，因而不能标记完整构建成功；静态修复冻结后由统筹复链。
- 退回修复结果：已移除 `HasValidSlotSetup()`，改为公开数据断言 `SlotAnimTracks.Num() == 1` 且唯一轨道 `SlotName == DefaultSlot`；播放长度、Main/End Section 以及后续 `ReadyForActivation` 的真实 Montage 播放断言保持不变。范围内搜索确认不再引用未导出 helper，行尾空白检查通过。结果待统筹复链确认。

## 第三次统一构建反馈（历史，后续已修复）

- 全部 C++ 编译再次通过；链接唯一失败为 `GGYGOPlayerComboLifecycleTest.cpp:197` 仍调用未导出的 `UAnimMontage::HasValidSlotSetup()`。
- 已按同一公开契约改为断言 `SlotAnimTracks.Num() == 1` 且唯一轨道名为 `DefaultSlot`，保留 PlayLength、Main/End Section 和后续真实 Montage 播放断言。
- 已按统筹要求执行 `rg -n 'HasValidSlotSetup\(' Source/GGYGO Source/GGYGOEditor`，项目级结果为零残留；目标文件行尾空白与范围内 diff check 无报错。第三次构建仍未完成链接，最终成功需统筹复链确认。

## 完整构建与第三次统一自动化反馈

- 上述链接返修后，统筹完整 C++ 构建已成功。
- `Admission.InvalidPredictionKeyReentry` 与 `Admission.CorrectionRpc` 在本轮通过；`Admission.GroupLifecycle` 仍在最终唯一实例断言失败，现由 attempt generation 与新增中间诊断继续定位和修复。
- `MontageTask.RateLeaseAndLifecycle`、`PlayerCombo.ActivationCommitAndEndReentry`、`PlayerCombo.TypedCorrectionPayload` 均在共享夹具初始化首断言失败；重复 `DefaultSlot` 根因及真实 segment 修复已静态冻结。
- 当前三类修复尚未重新编译或运行，Validation 状态统一为“await rerun”。

## 第二轮完整构建与第四次统一自动化反馈

- 第二轮完整 C++ 构建成功；38 项自动化为 34 成功、2 成功但带警告、2 失败。
- Camera、Animation 和 PlayerCombo 功能断言通过；PlayerCombo 两项的 6 条 warning 均为测试 Mesh 无 render data，夹具已改用引擎 SkeletalCube。
- `MontageTask.RateLeaseAndLifecycle` 的错误来自 CVar 恢复优先级和抽象 UObject ensure，另带相同 Mesh warning；三项夹具修复已冻结。
- `Admission.GroupLifecycle` 仍失败，新增仅测试生命周期观测待下一门禁给出 C 的精确 End 参数；runtime 未继续猜测修改。

## 第六次完整构建、统一自动化与单项诊断反馈

- 完整 C++ 构建成功；38 项自动化为 37 成功、0 warning、1 失败。
- MontageTask、PlayerCombo、Camera、Animation 及其他模块全部通过，说明真实 Mesh/CVar/具体 owner 夹具修复已闭环。
- `Admission.GroupLifecycle` 经单项诊断确认 sequence 方向正确；旧失败来自 post-cancel 扫描 Spec 实例而误命中已注销组登记的结束中 A。终检改以 `ActiveAbilitiesByGroup` 为权威后，单项 1/1 及完整 38/38 均通过，0 warning、0 error。

## 本批门禁

1. 子任务冻结后组长逐文件审查实际差异，核对共享签名及精确子租约；不覆盖原有 Kevin 与其他模块未提交改动。
2. B1/B2：本地激活代次覆盖 Super/Commit/Ready 的同步结束重激活；End 先通过引擎有效性/锁门禁，再清旧资源，Super 广播后不写实例。测试必须保留原有连段窗口语义。
3. B3：工厂实际使用的播放率快照供 watchdog 消费；缩放不重复，异常数值拒绝。
4. B4：原 Character/AnimInstance/ASC/播放实例身份固定，缩放 token 控制释放；覆盖同值不同owner、接管/旧释放、Avatar变化、EndTask保留Montage；无依当前ActorInfo误清新Avatar。
5. B8：不可取消 SingleInstance 占用者不能被优先级绕过；取消执行与准入一致，考虑同步回调重新占用；不在 Spec ActiveCount 尚未增加时提前 End；组结束通知不得摘掉新激活登记。
6. B9：ASC 仅提供通用可靠传输，Spec/实例/预测键过滤仍在 ASC；Combo 负责载荷类型、范围和 Revision；ASC 不引用具体 PlayerCombo 类型。
7. 静态门禁：diff whitespace、生成头/include、接口交叉引用、测试注册名、临时 World RAII及文件范围。没有运行的 C++ 测试明确标为待统筹执行。
8. 局部文档和 Canvas 在接口冻结后同步，校验 JSON/ID/边/链接；根目录全局状态由统筹维护。

## 当前文件所有者

详细名单与状态见 `AAADocs/Modules/CombatActions/Module_Repair_04_Subleases.md`。临时实现使用 `gpt-6-luna / max`：`/root/task_motion`、`/root/combo_lifecycle`、`/root/asc_admission`。

## 已核对的引擎边界

- UE 5.8 `UGameplayAbility::PreActivate` 在 `NotifyAbilityActivated` 和 Tag 取消回调之后才增加 `Spec.ActiveCount`；拒绝标记由基类正式 `ActivateAbility` 入口消费，不能在 Notify 内提前 End。
- `UGameplayAbility::EndAbility` 先检查 `IsEndAbilityValid`，ScopeLock 时延后执行；派生清理必须遵守此顺序。ASC 的 Super NotifyEnded 先减少 ActiveCount，再广播可重激活回调；旧组记录先摘除，组空通知在 Super 返回且仍空时发出。
- ASC `PlayMontage` 内部调用 AnimInstance 后才更新其动画记录；同步回调可能已结束任务。任务返回后必须再次检查自身生命周期及播放身份。
- ASC `CurrentMontageStop` 读取当前 ActorInfo；Avatar 改变后不得用它停止旧实例。当前身份完全匹配时保留 ASC 的停止/复制路径，其他情况仅处理捕获的旧实例。
- 本项目除通用 Montage Task 外未检索到 `SetAnimRootMotionTranslationScale` 写入者；资源接管仍按 token 身份判断，不使用浮点值相等判定所有权。
- `WaitComboInput::Activate` 可同步分发已缓存的复制输入，因此输入 Task 的 Ready 返回点也需要激活代次校验。

## 已确认的限制（不能标成已修复）

- UE 5.8 `ASC::PlayMontageInternal` 先执行 `AnimInstance::Montage_Play` 的同步回调，之后才写 `LocalAnimMontageInfo`、Ability CurrentMontage、复制记录及旧 Section。若回调结束旧激活并嵌套播放新的 Montage，外层引擎栈仍可能覆盖后继播放记录/位置；其预测拒绝绑定也按旧 Montage 建立。
- Task 层本轮仅用短期播放尝试 token 防止旧任务接管或停止嵌套后继实例，并处理无后继的同步结束；不能阻止引擎内部 post-Play 写回。复现入口：在原 AnimInstance 的 `Montage_PlayInternal` 返回前/OnMontageStarted 回调中结束 GA，并启动另一 Montage 或不同 Section 的新激活，再检查 ASC 当前 Montage/后继位置。需要统筹后续确定引擎/ASC 接缝方案；本批不复制 Montage 执行器、不增加延迟播放调度器。
- 固定速率契约为 RequestedRate × 非 Shipping 全局 Ability scaler × Montage RateScale；运行中改速及组件 GlobalAnimRateScale 不在本批 watchdog 契约内。
- 播放尝试 token 只识别本项目通用 Montage Task 的嵌套播放；直接调用引擎/其他 Task 的播放不受该身份保护。当前非测试 C++ 检索只有此通用 Task 调用 `PlayMontage`，不能据此推断全部蓝图或第三方资产已验证。

## Boss 播放率接缝

组长仅修改 BossMelee 的速率消费：Commit 前调用共享 `ResolvePlayRate` 预检，Commit 后创建实际 Montage Task；ActionMotion 与 watchdog 改读该 Task 的 `GetEffectivePlayRate` 快照，并检查时长有限性。没有修改 Boss 选招、CMC 或资产。BossAI 局部目录现属14a写入租约，本项接缝说明供统筹/该目录所有者同步，04不抢写。

## 局部文档检查（已完成）

已更新 AbilitySystem `结构.md`、`计划_AbilitySystem.md`、`计划_玩家普攻连段.md` 及五张相关 Canvas，保留历史基线证据，并记录最终完整构建及统一自动化 38/38、0 warning、0 error 结果。

已执行离线 JSON/节点与边 ID/边引用/链接目标检查：五图共 42 节点、37 边、27 处链接，全部通过。修改沿用原节点 ID、边与布局；不涉及全局入口或其他模块文档。

## 未进入范围

Camera B5–B7、Trace/伤害 E 批、CMC/玩家攻击位移策略、PawnExtension、输入重试策略、生产资产、资产生成器、全局架构入口；本批不得将其未解决问题写成已修复。

## 新增自动化清单（当前复验状态）

| 注册名 | 主要验收范围 |
| --- | --- |
| `GGYGO.AbilitySystem.Admission.GroupLifecycle` | 单项 1/1 及最终完整 38/38 通过，0 warning、0 error；C 保持活跃、B 安全退出，唯一实例/ActiveCount/组登记严格断言通过 |
| `GGYGO.AbilitySystem.Admission.InvalidPredictionKeyReentry` | 第三次统一运行通过；覆盖真实 GAS PreActivate→Activate、零 ActiveCount 拒绝和无效预测键重入 |
| `GGYGO.AbilitySystem.Admission.CorrectionRpc` | 第三次统一运行通过；覆盖 Spec/key/实例过滤、TargetData 分发、默认 no-op 与非项目能力 |
| `GGYGO.AbilitySystem.PlayerCombo.ActivationCommitAndEndReentry` | 第五次统一运行通过，0 warning |
| `GGYGO.AbilitySystem.PlayerCombo.TypedCorrectionPayload` | 第五次统一运行通过，0 warning |
| `GGYGO.AbilitySystem.MontageTask.RateLeaseAndLifecycle` | 第五次统一运行通过，0 warning |

测试使用临时 World/原生能力及合成 Mesh/Skeleton/Montage，不修改生产资产。上述模拟不替代真实动画资产、网络 RPC 传输、Dedicated Server/双端 PIE 验收。字段 NetSerialize 内存往返也不等于已验证网络包映射。

最终静态复核：精确子租约 20 个 C++ 文件的 diff whitespace、全文件尾空白、词法括号平衡、generated include 顺序、重复测试夹具及旧 API 引用检查通过（包含新增未跟踪文件）。六个注册名已核对。已对照本地 UE 5.8 纠正 `FAbilityEndedData::AbilityThatEnded` 字段，并复核 `PreActivate`/`CallActivateAbility`、ScopeLock、CVar 与 Montage API；ASC 无 Combo 类型依赖。最终完整 C++ 构建与 38/38 自动化通过。

架构核对：组仲裁与传输仍归 ASC，业务载荷和连段生命周期归 Combo；Montage Task 只持有播放身份/速率快照与缩放资源 token，不新增帧调度器或位移执行链。基类 Camera 实现未改。B4的引擎接缝风险按上节保留，需后续方案确认与真实联机验收。

交接：三个 luna/max 临时子任务均已停止写入并结束，无独立归档身份。MontageTask/Combo 夹具、Admission 全局 sequence、pending 定向裁决、权威组登记终检和 test-only 裁决观测已冻结，全部严格断言保留；最终完整 C++ 构建与 38/38 自动化均通过，0 warning、0 error。全局入口及 BossAI 速率接缝说明仍由统筹/对应目录所有者同步，本批未写其他模块源码目录。
