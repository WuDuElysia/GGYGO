# 04B4 Animation 原子步骤

日期：2026-09-30。Animation 长期组长直接执行；不开子代理。

## 当前授权与状态

统筹已接受 A3 两行接线与静态证据，Base 保持冻结。本次仅授权并完成 **A4 只读身份生命周期查询**：`GGYGOMontageGuardAnimInstance.h/.cpp` 与本步骤/验证两记录，共四文件，已静态复核冻结。A1/Base/旧 A2 机制保持；只新增一个公开 const 查询的声明和定义，ASC/Task 未接入。本轮不写测试/资产/Obsidian，不构建/UE/Git/代理。A3/A4 未编译/未动态验证，B4 未关闭。

## 职责与依赖

- Animation：原生播放调用的栈作用域、生命周期代次、精确动画实例身份及返回屏障。仅记录调用证据，不拥有 GAS 播放状态。
- ASC：覆盖完整 `Super::PlayMontage` 的调用方 scope、原 Caller/Avatar 有效性检查，及既有 Local/Rep/GA 写回。未来只消费 Animation 的声明接口。
- Task：能力任务生命周期、显式调用结果及原 RootMotionScale 资源租约。未来清理既有重复 attempt 登记，不能再保留第二套播放仲裁。
- Engine：仍执行原生 Montage 播放。不得新增播放执行器、帧调度器或修改引擎。

依赖顺序：真实 P1 严格红例 → A1 声明冻结 → A2 原生屏障/编译通过 → A3 继承静态冻结 → **A4 身份查询** → ASC 适配 → Task 适配 → 专项矩阵 → 文档/资产窗口。调用方未开放；共享接口如需变化先冻结调用方并交回统筹。

## 原子步骤表

| 步骤 | 唯一结果与精确文件 | 只读依赖 | 非目标 | 验收断言与停止点 |
| --- | --- | --- | --- | --- |
| A1，已静态冻结 | 新 `Source/GGYGO/Animation/Runtime/GGYGOMontagePlayGuard.h`；新 `AAADocs/Modules/Animation/Module_Repair_04B4_Animation_Steps.md`；新 `AAADocs/Modules/Animation/Module_Repair_04B4_Animation_Validation.md` | 有效 ledger/schedule；UE 5.8 AnimInstance/AnimMontage/ASC 入口；冻结 Animation 基类；P1 诊断 | 不实现任何 RAII/屏障函数；不改继承/ASC/Task/测试/Engine/资产/Obsidian；不构建/UE/Git | 无 GAS 依赖或可写权威状态；完整调用方 scope、阶段、身份、结果、清理职责明确；三文件冻结并交回 |
| A2，已静态冻结 | 新 `Source/GGYGO/Animation/Runtime/GGYGOMontageGuardAnimInstance.h`、`.cpp`；本步骤/验证两记录 | 冻结 A1、UE 5.8 protected virtual `Montage_PlayInternal`、实例集合/ID/IsActive、生命周期入口、真实 P1 顺序 | 不改 A1/现有基类/ASC/Task/测试/引擎/资产/Obsidian；不构建/UE/Git/代理；不新增全局 attempt map | 唯一原实例 scope 链与返回屏障；合法 scoped/native 路径恰好一次 Super、准入拒绝零次；原生阶段/精确 ID/代次/自身调用有效性/清理已静态复核；四文件冻结，不进入 A3 |
| A3，已静态冻结 | `Source/GGYGO/Animation/Runtime/GGYGOAnimInstanceBase.h`；本步骤/验证两记录 | 冻结 A1/A2、第15次构建；只读 Base cpp 现有 D6 与 Super 调用；Animation 笔记入口 | 不改 cpp/A1/A2/ZZZ/ASC/Task/测试/资产/Obsidian；不构建/UE/Git/代理 | 头只换直接 include 与父类；所有字段/API/元数据逐字保持；三个生命周期 Super 各一次且进入薄层；哈希冻结，无需生命周期扩改 |
| A4，已静态冻结 | `Source/GGYGO/Animation/Runtime/GGYGOMontageGuardAnimInstance.h`、`.cpp`；本步骤/验证两记录 | 冻结 A1 Identity、旧 A2 私有生命周期/owner/LastCallId、A3；已有只读 GetOwningActor | 不改 A1/Base/旧 A2 机制/消费者/测试/资产/Obsidian；不构建/UE/Git/代理 | 仅新增公开 bool const 查询；无状态副作用、无实例活动/存在要求；声明/定义移除后旧源码逐字一致；四文件静态冻结后停止 |
| ASC、Task、测试，待统筹拆分授权 | 战斗组长分别登记精确原子文件，不能由 Animation 扩租约 | A1→A2→A3→A4 冻结，ASC→Task 先后接续 | Animation 不抢写战斗文件 | ASC 完整 scope；Task 单一结果通道与只读生命周期查询；严格 P1 保持断言不降级，专项矩阵独立验收 |
| 笔记/资产，待授权 | 实现冻结后再登记具体 Markdown/Canvas/资产 | 源码/专项结果、独占资产窗口 | 不将声明或夹具写成生产生效 | 同步真实接线状态与缺口；生产 ABP 默认不迁移 |

## A1 冻结接口

1. `FGGYGOMontagePlayGuardRequest`：原 `UAnimInstance`、请求 Montage、弱引用不透明 `UObject` CallerIdentity、必需 `TFunction<bool()> IsCallerContextCurrent`。Animation 不知道具体 ASC/GA 类型；回调由调用方捕获原 Avatar/激活等上下文，必须只读、无播放/广播副作用。
2. `FGGYGOMontagePlayGuardIdentity`：原弱 AnimInstance、`uint64 LifecycleGeneration`、不复用 `uint64 CallId`、本次引擎 `int32 CreatedInstanceId`。代次和 CallId 由 guard 签发；0 为无效；实例未创建为 `INDEX_NONE`。CallId 不因生命周期重置而重用；计数耗尽必须拒绝，不能回绕。完整身份含原实例，不能单用 CallId 或 Montage 资产。
3. `EGGYGOMontagePlayGuardOutcome`：`NotExecuted / Accepted / Failed / Superseded / PrecreationRejected / PostWriteRejected / Unsupported / LifecycleInvalid`。`NotExecuted` 是尚未执行原生调用的初始状态；拒绝也未执行，但有独立最终原因。
4. `EGGYGOMontagePlayGuardNativeStage`：`NotEntered / Executing / Returned`。结果快照同时保存该阶段，避免把整个 ASC scope 错当成原生 frame。
5. Scope 声明：`FGGYGOMontagePlayGuardScope(Request&&)`、析构、`bool CanExecute()`、`const Result& Complete(float InCallerReturnValue)`、`const Result& GetResult() const`；禁止复制/移动。A1 不含函数定义；A2 在新薄类 cpp 定义，A1 不变。状态以私有不完整 `FState` 承载，不向调用方暴露可写注册或 GAS 状态。
6. Result 只提供 scope 的 const 引用；调用方在 Complete 后复制。它包含原身份、Outcome/NativeStage、成功后继 CallId、原生屏障返回值及调用方实际返回值。复制结果不是播放权威状态，不能按其资产/ID去清理后继实例。

预定调用顺序（说明契约，未接入代码）：构造 scope → 紧邻 Super 调 `CanExecute()` → 获准才调用完整 ASC `Super::PlayMontage` → `Complete(实际返回值)`，跳过时 `Complete(0)` → 复制结果 → 析构。Complete 不能仅凭调用方正返回值认定 Accepted，不能补救已发生的 GAS 写回；A2 必须在原生返回边界先屏蔽正返回。

## 重入与清理断言

- scope 覆盖 ASC 的 Local/Rep/GA 写回、Section 跳转及预测拒绝绑定，不能只包围 `UAnimInstance::Montage_Play`。
- 只按**最内层** scope 阶段判定：`NotEntered` 时重入为 `PrecreationRejected`；`Returned` 时重入为 `PostWriteRejected`，子调用不进入原生播放；更外层仍在原生执行不解除此拒绝。
- `Executing` 阶段必须先从引擎实例集合识别父调用的精确新实例；父实例尚未创建/不能可靠识别时，子调用为 `PrecreationRejected`，不能让旧栈稍后创建并覆盖它。识别后也只有后续明确支持的入口才可尝试同步重入；子调用进入/创建不等于接管。Failed、拒绝、Unsupported 或 LifecycleInvalid 子调用不能冒充成功后继；成功孙调用必须沿有效祖先链传播，不能被中间失败返回遮住。
- 精确实例 ID 从调用前后引擎实例集合识别，每次跨回调后按 ID 重新解析；不把同资产 ActiveMap 的当前值或 GAS 的 8 位计数当实例身份，不跨回调保留原始实例指针。
- guard 是原 AnimInstance 的唯一 scope 链所有者，只借用仍存活的调用方栈 scope。全流程仅 game thread；回调捕获引用必须活到 scope 析构。销毁只注销本 CallId，无额外停止播放或 GAS 回滚。
- 初始化/反初始化/owner 更换使捕获代次失效；原对象失效或 caller 回调为 false 结果为 LifecycleInvalid。代次耗尽拒绝继续注册，不复用旧值。失效不释放调用方栈对象、不让旧析构操作新 owner；Complete 重复调用返回首次封存结果，析构与完成/失效相容。
- 弱 CallerIdentity、必需回调或 guard 接入缺失不得默认为成功；缺少接入/能力为 Unsupported，失去已捕获有效上下文为 LifecycleInvalid。后续实现必须明确检查次序，不能以“请求已登记”标记 Accepted。

## 尚未承诺的范围

声明不承诺 bare `UAnimInstance`、未 scoped 直接播放、跨 coordinator 混用、不同组并存/`bStopAllMontages=false`、fractional loops 或 simulated 路径。各入口需后续明确验证，不能自动认为被 virtual ASC `PlayMontage` 覆盖。特别是 fractional loops 可绕过该入口。

不得自动迁移生产 ABP/资产或修改 Kevin 生成器。旧同资产预测拒绝按资产停止后继的风险未关闭。Started 内破坏 mesh/反初始化可导致引擎在广播返回后使用已释放实例；本声明不提供该破坏性回调的引擎安全保证。拒绝子播放也不能恢复在 scope 外已取消/已激活的 GA。

## A2 实施前预检与停止点

单一目标：定义 A1 Scope 并实现原生返回前的拒绝/失效/成功接管屏障。精确四文件见表；生产阶段只写新薄类两文件，静态复核后再封存本地两记录。只读依赖已经确认：UE 5.8 原生函数在 stop 回调之后才创建实例、Started 广播之前把实例加入集合；可用 public `MontageInstances` 与 `GetMontageInstanceForID`，实例提供 ID/asset/IsActive/IsPlaying；不以 Started 订阅排序识别实例。

- 唯一 guard 链在原 AnimInstance，借用活的 caller scope，不持有 GAS 权威状态。Scope 的私有状态仅保存 request、result、调用前 ID 快照、注册/封存信息；无全局表、Tick/Timer、第二播放机制。
- 初始化/反初始化、观测到 owner 改换推进不回绕代次并使活记录失效；保持旧注册直至各自析构，不清空链。CallId 跨代次不复用；耗尽终止 scoped 准入。仅引擎已有 NativeUpdate 及调用入口核对 owner，不新增帧调度。
- 自身上下文失效为 LifecycleInvalid；不因祖先 GA 已结束而拒绝仍有效的 B。父资格只看原动画实例/代次、最内原生阶段及可唯一识别的父新实例。父 CallerIdentity 只作 coordinator 匹配，不调用父 caller 验证回调来阻止 B。
- 统筹补充的 coordinator 契约：所有项目 ASC 播放（含通用 Task）统一以**原 ASC**作为 CallerIdentity。Task 身份/生命周期只在 caller 回调中追加弱捕获校验，不以 Task UObject 作 coordinator；不同 Task 同 ASC 不会因此被误拒，CallId 已区分每次调用。A1 头不改，消费者后续按该契约接入。
- 最内 NotEntered 或 Executing 无唯一父新实例为 PrecreationRejected；Returned 为 PostWriteRejected。请求缺少 guard/回调/资产、跨 coordinator/组、`bStopAllMontages=false`、多次原生入口或与无 scope 原生栈混用为 Unsupported。以上拒绝均不调用 Super。
- 没有 scope 的顶层普通播放保留一次引擎 Super；无 scope 嵌套于保护栈时零次 Super。没有 scope 的嵌套普通播放不承诺保护；实现将保守拒绝嵌套，不能借此声称 Fractional/Simulated 已接入。
- 合法 scoped 原生播放恰好一次 Super；跨任何回调只留 ID/弱引用。唯一识别本调用的新实例之后检查正且有限的原生返回、精确实例活动状态及自身 caller 有效性，才给 Accepted。
- 子 Complete 封存 Accepted 时，把成功 CallId 传播到所有仍在原生 Executing 的同代祖先；这些祖先返回 Superseded/0。成功孙直接传播贯穿中间层，失败中间层不能吞掉已有成功证据。接管是发生过的调用证据，后继以后结束不能使祖先恢复写回。
- 若 A 已 End 而 B 接管成功，A 为 Superseded/0；A 无成功后继且自身 caller 已失效，A 为 LifecycleInvalid/0。GA End 不推进 Animation 生命周期。Complete 仅封存，不回滚 GAS；析构只注销自身，不停止实例/清理新 owner。

验收仅静态：检查逐分支 Super 次数、最内阶段、精确 ID 从集合差集绑定、成功传播优先于祖先 caller 失效、幂等 Complete/注销、跨代次活链保留、A1/现有基类 hash 不变。接口不足或发现需改 A1/其他文件则停止交回；完成后冻结四文件，专项与编译另候统筹授权，不关闭 B4。

## A2 实际结果

新薄类两文件已完成，A1 Scope 五个公开函数在新 cpp 定义；实现内容与上述预检一致。完整结果见验证记录的拒绝表、逐路径 Super/清理断言和静态证据。未改 A1 或已冻结文件，无接口缺口需要扩租约。A2 完成时 Base 尚直接继承 `UAnimInstance`；随后第15次完整构建含 A1/A2/UHT 通过。A3 另步接入继承，项目调用方尚未创建 Scope，B4 仍开放。

## A3 实施前预检

唯一目标：现有通用 Base 在 C++ 继承链中进入已冻结薄 guard。精确三文件见表，生产阶段仅改头的两行，再静态核对并更新两记录。依赖已经冻结并构建；不改变任何调用方或生命周期实现。

- 直接 include 从 `Animation/AnimInstance.h` 换为 `Animation/Runtime/GGYGOMontageGuardAnimInstance.h`；父类从 `UAnimInstance` 换为 `UGGYGOMontageGuardAnimInstance`。原字段、API、UPROPERTY/UFUNCTION/UCLASS 元数据及其他文字逐字保持。
- 只读确认 Base cpp 的 Initialize、Uninitialize、Update 分别恰好一次 Super，无直接 `UAnimInstance::` 调用。继承切换后 Super 自然进入 guard；不追加第二次调用。
- 初始化先薄层代次更新再既有表现重置/抓帧；反初始化既有表现重置后调用薄层失效；Update 先薄层 owner 代次核对再既有表现 owner 重置/抓帧。各层清自己的派生状态，Engine 仍只执行一次，不新增调度/所有权权威。
- 不改 D6 重置 Hook、ZZZ、StateFrame/Movement、A1/A2。若发现必须改 cpp 或薄层生命周期，停止交回，不能扩租约。
- 验收：头文件基线与预期两处替换逐字相等、恰好两行差异；cpp/A1/A2 前后 hash 一致；生命周期只读调用路径通过；完成即三文件冻结，不进入消费者或资产步骤。

## A3 实际结果

头第8行改为 include `GGYGOMontageGuardAnimInstance.h`，第21行父类改为 `UGGYGOMontageGuardAnimInstance`。以修改前原字节在会话内存还原文本，只做预定两处替换，与实际结果逐字相等；仅两行差异，全部字段/API/元数据及换行保持。未产生额外基线文件。

Initialize/Uninitialize/Update 的 Base 与 Guard 层各一次 Super，无直接 `UAnimInstance::` 绕过。cpp/A1/A2 前后 hash 一致；无需生命周期修改或扩租约。源码继承现为 `UGGYGOAnimInstanceBase → UGGYGOMontageGuardAnimInstance → UAnimInstance`，ASC/Task 未消费 Scope，生产 ABP 未迁移/回读。新基类头 hash `010DDC81E74AA20BCFC0741F85D77E1BD4554A4728252195A20116D59625E614`。三文件冻结交回，仅表示 C++ 继承链接线与静态验证，不表示 B4 已修复。

## A4 实施前预检

唯一目标：给持有 A1 Identity 副本的消费者提供当前原 AnimInstance 生命周期是否仍匹配的纯查询。精确四文件见表；先登记预检，再仅增加声明/定义，静态审查后封存两记录。原两源码文本只在会话内存保留，不新增基线/测试文件。

接口为 `bool IsMontagePlayGuardIdentityCurrent(const FGGYGOMontagePlayGuardIdentity& Identity) const`，普通 C++ 公共方法，不新增 UFUNCTION/属性/字段。检查 guard 已初始化且未耗尽；原弱 AnimInstance 为 this；generation 非零且相同；`0 < CallId <= LastCallId`；捕获 owner 与当前 owner 相同且此前有效 owner 未弱失效。合法初始化时捕获/当前 owner 都为空仍可返回 true，不增加角色业务条件。

只读取已有字段、弱引用与 GetOwningActor，不 Refresh、不推进代次、不缓存、不修改 ScopeChain，不要求最新 CallId，不访问 CreatedInstanceId/MontageInstances 或播放活动性。停止/已销毁的 Montage 实例不改变该查询的生命周期判断，执行入口需另按精确 ID 重解析。返回 true 不证明 Accepted、ASC/GA 所有权或权限。

验收断言：未初始化/反初始化/耗尽/弱原实例不符、零或旧代次、零/未来 CallId 拒绝；同代已签发旧 CallId 可查；owner 仍一致或合法初始均为空可查，当前 owner 已改变或原有效 owner 弱失效拒绝；重复查询不改变状态。未观测且未经过生命周期入口的 owner A→B→A 不承诺发现。除新增块外旧 A2 源码逐字保持，A1/Base hash 不变。需要扩大 A1/机制/消费者或补状态才能满足额外语义时停止交回；本四文件完成即冻结，编译/专项另授租约。

## A4 实际结果

仅新增公共 const 声明及对应定义：检查现有生命周期就绪/耗尽标记、弱原实例、非零匹配代次、非零已发行 CallId 范围，再只读比较 owner 与有效性。无 owner 的合法原初始化不被新增角色条件拒绝。没有改 A1 契约或接入消费者，也未新增字段/缓存/实例查找。

静态14项全部通过；移除新增声明注释块与定义块后，两原文件文本的 SHA256 恢复为 A2 旧值，原机制逐字保持。A1/Base h/cpp hash 不变。Guard h 当前 hash `6BD6A6DC686074608213F5DF567957D1F10A2D5DBB537BD8C70E0687BA910766`；cpp `2357E96AF6F312FE2C691A09C79988DC10A6FC578B48AF96604CE1D5D9621995`。详细边界/副作用审查见验证记录。四文件冻结，不继续扩调查或消费者实现；源码编译、行为专项及笔记窗口仍候统筹。
