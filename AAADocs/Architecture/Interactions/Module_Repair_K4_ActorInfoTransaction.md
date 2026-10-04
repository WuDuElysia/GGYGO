# K4-I2 ActorInfo 事务与发布凭据契约

## 当前状态（2026-10-03）

本记录当前追加第18节：Destroy 已提交来源清理与失败 native Init 原写入清理两个 ASC 源码步骤已获统筹 `finite_static_accepted_uncompiled` 并冻结。本轮未编译/UHT、未运行专项或 UE 冒烟；不把历史 Gate 或已有测试叶视为这两个新步骤的验收。

`CheckAvatarBindingCleanupContext` 与失败 Init 清理入口使用不同来源。前者核对已提交 Context 的精确 cleanup 快照；后者仅消费原失败 Operation 的返回时实际写入证明，不提交绑定、不创建 Receipt/Notice/Ready。工作查询、既有成功事务与发布契约继续按各自规则执行。

Host 旧工作查询与固定 PreserveOwner、CombatantState 失败 Init 分支未迁移；完整调用链尚未关闭。R0 第36次 2 Fail/12 错误及各历史阶段未运行证据原样保留。本文档写权限仅见[两文件同步预检](Module_Repair_K4_AvatarBindingIdentity.md)，不含源码/测试/全局入口/Obsidian/Canvas。

## 历史记录（原第1～17节）

以下原“更新”及第1～17节完整保留各自阶段的定义、实施、失败、租约和验证证据；“当前”“本次”“尚未实现”等按所在节的阶段理解。原顶部 Publish 未实现属于 I2b 当时状态，后续 P1/C1 等进展见对应历史节；本轮清理来源最新状态以第18节为准。历史 hash、Gate 和未运行事实不冒充本轮结果。

更新：2026-10-02。第1～6节保留 K4-I2a-API 定义、历史读取和声明阶段的当时状态与证据；第7节记录本次 K4-I2b。三 Try 真实执行、native Busy、必需旧入口保护和运行 Receipt 创建已实现并完成静态核对，三文件交回冻结；本次未编译或动态验收。Publish、旧通知与调用方迁移仍未实现，Gate41 只证明本次写前基础。

## 1. 唯一目标、归属和精确租约

- 唯一目标：冻结非反射 FGGYGOAvatarBindingPublicationReceipt 的不可变历史证据资源值与五个事务入口声明，关闭 Result-only 发布不能恢复原 Kind/Before 端点的契约缺口。此阶段不签发运行凭据，不关闭完整绑定根因。
- 唯一写入者为 AbilitySystem 长期组长本人，gpt-6.1-sol / xhigh；仅 apply_patch，不创建或唤醒代理。
- 精确文件：Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h；同名.cpp；本新增 AAADocs/Architecture/Interactions/Module_Repair_K4_ActorInfoTransaction.md。写前已核验本记录不存在。
- 三文件是一个跨 TU 资源值契约：头提供签名及不透明值，cpp 隐藏 Proof 完整布局并实现副本读取，独立记录登记基线和验收。定义与读取不可拆成互不一致的接口；生产执行、专项测试及 Obsidian/Canvas 分阶段另门禁。
- ASC 继续唯一负责 GAS/ActorInfo 执行和已有身份签发；Host 选择并发布 Avatar，Extension 持有绑定句柄/缓存，消费者清理自己的精确资源。本值只持有 ASC 创建的历史证明，没有第二 Avatar 决策或执行链。

## 2. 基线和只读依赖

| 文件 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 21762 | 8C0FF34E4593F4F445174A329988467E949421679CA04087EEBE73F1763656AF |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 69669 | 3753A550C7E9FAC032E049E5A2C9C69342F3EFD1AB92E9F2B8FCF304147014AE |
| Source/GGYGO/AbilitySystem/GGYGOAvatarBindingTypes.h | 6351 | 2E2ACF92C2820480421C6C78AAA0F8348F6BCCF0D8474595A342BD61677343FF |
| AAADocs/Architecture/Interactions/Module_Repair_K4_AvatarBindingTypes.md | 8969 | 34979ED3D6A89FDB17B6C93A890446F83A8AC3093615C2181D49AB0CD6FBE913 |
| AAADocs/Architecture/Interactions/Module_Repair_K4_AvatarBindingIdentity.md | 10161 | 89EDCA4786E52AA00659FADF7D658B1A2D2A56493CB8F1A4F80E496CD8FCC988 |

- 只读依赖：冻结 I0/I1、当前 ASC/GAS 类型与 SharedPointer 实现、AGENTS、路由/排程/台账、Obsidian 计划蓝图和 AbilitySystem 结构/计划。SharedPointer include 在 generated.h 之前；不透明嵌套 Proof 在 cpp 定义，接口没有 USTRUCT/UFUNCTION/UPROPERTY。
- 已保存两份 ASC 完整原文以及除该 h/cpp 外的 248 个现有 Source 文件 path/bytes/hash，另保护 I0/I1/B0 记录与 AGENTS。统筹全局排程/台账及其它独立租约由各自所有者维护，不能把其合法更新算作本步写入。
- 第38次完整构建已覆盖 I0/I1，正常73 Success；没有本步新增值/声明的编译或动态证据。第36次 R0 两个严格后继案例 2 Fail/12 错误仍开放，本步不改其测试或旧运行路径。

## 3. 资源值与历史副本读取

- Receipt 默认 Proof 为空。值可复制，副本共享 TSharedPtr<const FCommitPublicationProof>；无公开填充构造、setter、Proof 访问器或外部 factory，仅 friend ASC 能创建并装入 Proof。
- 私有不可变 Proof 保存原 Kind、Before Context/Owner/Avatar、CommitResult 和准确 Notice。身份来自已有 Operation/Context，不额外增加 Issuer、Serial、计数器、Map、ActorInfo allocation 所有权、请求谓词、裸栈引用或 Actor 强所有权。
- bool TryGetCommittedEvidence(FGGYGOAvatarBindingResult& OutResult, FGGYGOAvatarBindingNotice& OutNotice) const 在入口完整复位两个独立调用方输出；游戏线程读取。空值返回 false，Result 为默认 Rejected/InvalidRequest、bCommitted=false、全部身份默认空，Notice 为默认 Invalid 和空字段。
- 非空只复制不可变 CommitResult/Notice 后返回 true；true 只表示历史副本存在，不证明 ASC 存活、当前绑定、发布许可、通知成功或全局 Ready。查询不核对当前状态、不发身份、不执行谓词、不改存储证明；读取的可写副本不能反向改动 Proof，也不能作为 Publish 入参。
- Proof 是沿同步调用链保留的历史资源，最后一个 Receipt 副本释放时销毁；弱端点可失效，仍保留原弱身份。此阶段没有运行创建点，旧路径不会自动制造非空 Receipt。

## 4. 五个声明及后续目标契约

K4-I2a-API 当时仅声明以下 API，无定义、占位 stub 或调用。当前三个 Try 和 Busy 查询已在 K4-I2b 定义，见第7节；Publish 仍只有声明，调用方尚未迁移。

```cpp
FGGYGOAvatarBindingResult TryExecuteAvatarActorInfoTransaction(
    const FGGYGOAvatarBindingRequest& Request,
    FGGYGOAvatarBindingPublicationReceipt& OutPublication);
FGGYGOAvatarBindingResult TryBootstrapAvatarActorInfoTransaction(
    const FGGYGOAvatarBindingRequest& Request,
    FGGYGOAvatarBindingPublicationReceipt& OutPublication);
FGGYGOAvatarBindingResult TryReplaceRevokedAvatarActorInfoTransaction(
    const FGGYGOAvatarBindingRequest& Request,
    FGGYGOAvatarBindingPublicationReceipt& OutPublication);
bool IsAvatarBindingNativeWriteBusy() const;
FGGYGOAvatarBindingResult PublishAvatarBindingNotice(
    const FGGYGOAvatarBindingPublicationReceipt& Publication,
    TFunction<bool()> IsPublicationContextCurrent);
```

以下保留 K4-I2a-API 接受的后续执行/通知合同；各项当前落地范围以第7节为准：

- 顺序：冻结 I0/I1 → 本 API/Proof 值 → Execute/native 窗口 → Notice/精确去重 → 旧 native 适配 → Host/Extension 有类型结果与发布迁移 → 专项测试/实际门禁 → 图文同步；统筹按精确文件另授权，不从本记录推导继续写权。
- Execute 入口先清空 OutPublication；只有本操作真正提交后才能返回非空。原 Kind/Before Context/弱 Owner/Avatar 在 Reserve 后、Super 前复制，I1 Commit 成功后建立不可变 Proof；不从已清空 ActiveOperation 或当前 After 指针反推原种类/端点。
- Kind 映射：Init 为 Initialized，Owner/Avatar 为 After；Clear 为 Released，端点为原 Before，包括 PreserveOwner；Refresh 为 Refreshed，端点为 After。owner-only Init 与 Clear/PreserveOwner 即使最终 Owner 非空、Avatar 空，也按原 Kind 保持不同语义。
- native Busy 由未来真实栈窗口覆盖整个不可中断 Super 和返回核对；I1 身份槽不是该窗口。项目可控外调后及 Super 返回后重检；窗口在普通通知前关闭，通知内允许合法后继，无自动排队、重试或隐式成功。
- 调用方拿到 Commit Result 与 Receipt 后先完成 Host/Extension 对外发布，再调用 Publish；ASC 单独 Commit 不能表示全局 Ready。发布谓词必需、纯查询、只在同步栈内使用，不保留闭包。
- ASC 未来只保留一个当前 Receipt 引用及 Pending/Dispatching/Consumed 状态，不建历史表/队列/第二 Avatar 权威。空或异 issuer 拒绝；真实但被后继取代的旧 Proof 返回 Stale，bCommitted 保留 true，通知/OnSpawn 不运行。
- 当前 Proof 指针及 Context/LastWrite 必须精确吻合；Dispatching/Consumed 拒绝重复。外调前标记 Dispatching，每次项目外调后重检；B 接管后 A 不改 B 的发布状态、清 B 的凭据或续跑 A OnSpawn。
- 成功、失效、取代只释放 ASC 自己的匹配引用；旧栈副本仍能返回其历史已提交证据。发布前失败只失效精确自己的 Proof，不自动 Clear/回滚 native/重放；没有新身份来源。

## 5. 非目标、验收断言和停止点

- 非目标：真实 native 执行器/Busy 栈窗口、ASC 当前 Receipt 槽及 Pending 状态、通知 delegate/Broadcast/OnPawnAvatarSet/OnSpawn、旧 void/复制/ProcessEvent 接缝、Host/Extension/GA/Task/Montage/Input/B0、测试夹具、资产、UE、构建、Git。全部旧函数体、状态机和公开旧接口完整保留；I0/I1 独立记录不写。
- 验收：全文检查新值默认空/私有 const Proof/唯一 friend/共享复制/端点弱引用/输出完整 Reset；五个 API 只有声明且全 Source 无调用/定义；无 factory、MakeShared、新序号源、状态槽、Map、native/广播调用、业务 stub 或谓词保留。
- 原代码保护：从实际 h/cpp 移除本步新增 include/Receipt 类/API 声明/Proof 与读取定义后，精确恢复两份原完整文本；全部既有保护 Source 与冻结记录 hash 保持。UTF-8 无 BOM、LF、末尾换行、无行尾空白。
- 架构核对：只新增来源明确且自动释放的历史证据值；无循环依赖、第二绑定权威、重复执行器或内部可变状态泄露。仍存在旧 void 路径无法返回 Busy/失败且调用方继续广播、旧 Detach 收尾破坏后继的问题；本 API 声明阶段不关闭这些风险。
- 已只读核对 Obsidian 定位及 AbilitySystem 类清单：I1 与本步新接口尚未同步。统筹明确冻结其它图文，本步只把新增值/接口、声明阶段与未迁移边界交给后续互斥文档阶段，不宣称全部笔记同步。
- 静态证据写入本记录后三文件冻结交回实际 hash 与未编译边界；停止写入，未经统筹验收不续 Execute/Notice。遇第四文件、I0 变更或跨模块生命周期扩展立即停止。

## 6. 实际静态证据

- 实际顺序：先创建本记录登记已接受预检/精确租约/基线，再 apply_patch 添加头的 SharedPointer include、Receipt 值和五个 API 声明；cpp 只在末尾添加私有 Proof 完整定义及 TryGetCommittedEvidence。第一次 cpp 上下文匹配失败时两源 hash 仍与基线一致，修正上下文后整体写入；没有部分旧代码修改或第四文件写入。
- ASC h 最终 24344 bytes/492 行，SHA256 `36CFFA8C5157EF421D2DF41613890D613EE9008DD7A34116BD1107E2361D89AD`，相对基线仅增加56行；cpp 最终 71158 bytes/1824 行，SHA256 `5225429C07A0D9E020B1D2E7D3682A1C12597496BAA1DC873D2BCDC7C3DCD794`，仅增加46行。
- 用已保存原整文和新增块构造预期 h/cpp，与实际全文逐字符完全一致；从实际头移除三个新增块、从 cpp 移除末尾新增块后，精确恢复原 h/cpp 完整文本。因此全部旧函数体/公开接口、I1 private 状态/身份助手、Init/Clear/Refresh/PlayMontageWithGuard/输入/GA/组仲裁执行链完整保留。
- 空值分支静态全文核对：默认 ctor 保持空 shared Proof；读取先赋完整默认 Result 和 Notice，再作游戏线程 check/Proof 有效性检查。空值直接 false，没有赋 Succeeded/None、bCommitted 或任何身份；非空路径仅复制 Proof 两项历史值并返回 true，无 ASC/弱 Actor Resolve/当前 Context 核对或状态修改。这是代码分支审查，未运行 C++ 用例。
- 外部不能构造 Proof 的静态证据：nested 类型与 shared 成员均 private，仅 ASC friend；无公开填充构造、setter、factory、原始 Proof 返回或继承接缝（Receipt 为 final）。Proof 六项字段全部 const，参数虽按 const 引用输入，但成员按值复制；仅 Actor 弱引用、原 Context/Result/Notice，未持有谓词、裸栈引用或 ActorInfo allocation。
- 全 Source 搜索五个未来 API 仅各一处头声明，无定义和调用；Receipt 查询只有一处声明、一处定义，无业务调用/运行 Proof 创建点。新增块没有 MakeShared/new、身份计数器、ASC 状态槽、Map、native/Super/Broadcast/OnSpawn 或 TFunction 成员；没有占位业务结果。
- 静态跨 TU/反射边界核对：SharedPointer 显式 include 在唯一 generated.h 之前，generated.h 仍为头最后 include；普通非反射 Receipt 与 private 嵌套 Proof 分别位于头/cpp，只有副本读取有定义。隐式值复制共享 const Proof、引用计数归零释放；本轮没有 UHT/编译确认，五个未定义声明不得提前调用。
- 248 个既有保护 Source 的 path/bytes/hash 逐项保持，Source 清单没有新增/移除；I0 头/记录、I1 记录、B0 记录与 AGENTS 均保持。全局排程/台账及 Obsidian 没有由本会话写入。三文件均 UTF-8 无 BOM、LF、末尾换行、无行尾空白。
- 架构责任核对通过静态定义边界：历史 Proof 来源唯一、只读输出无回写权限，复制资源无强 Actor 环或新执行权威；真实发布槽/Busy/失效与后继去重没有落地。旧 void 调用及 R0 已知失败完整保留，不能以本接口阶段声称根因修复。
- 未运行 UE、构建、Git、自动化或代理，未修改资产/其它记录/图文。最后全文/格式/保护核对后明确冻结三文件，记录实际最终 hash 随交回消息提供；停止写入，未经根验及新租约不进入 Execute/Notice。

## 7. K4-I2b：真实 ActorInfo 执行与必需旧入口保护

更新：2026-10-02。Gate41 已由统筹完成：普通73与原严格 B0均成功；这不是本 I2b 的编译或动态证据。统筹接受短预检后授权本原子直接实施，先登记以下基线与断言，完成后静态冻结交回。

### 7.1 单目标、三文件与基线

唯一写入者为 AbilitySystem 长期组长本人 gpt-6.1-sol/xhigh，仅 apply_patch，无代理。精确三文件为 Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h、同名.cpp及本既有记录；不新建记录。

| 写前文件 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 27946 | 9A6F21ECE2CAB34FB244EFAD89A72F21C58104B350AFB1DCB164FC33CAA105F0 |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 82174 | F7F9059A92CD505A72A945DB4ED64B0CB0516D406A6F01784756B778D0AAB9DF |
| AAADocs/Architecture/Interactions/Module_Repair_K4_ActorInfoTransaction.md | 12888 | B12F123998AB8880130F10ADD0DEC88E6F6C4ABA9605955ACAA2AE24AEFCBFA7 |

唯一目标：三 Try* 真实 I1 准入→限定 Super→调用方/原操作重检→Commit→原 Kind/Before 不可变 Receipt；真实 Busy 与旧 Init/Clear/项目类型 Refresh 拒绝、窗口外失效同一步闭合。身份/操作序号仍归 I1；ASC 唯一持有 native 窗口和一个当前 Receipt 资源引用，无第二绑定权威、队列或长期谓词。

### 7.2 精确契约与验收

- 三个公开 Try 入口完整复位独立 OutPublication，明确只接 Init/Clear/Refresh；普通、never-committed Bootstrap、精确 Revoked replacement 复用 I1 的不同 Admission。Cancel/Cue 等 Kind 明确拒绝，不能伪装 ActorInfo 成功。
- Reserve 后、Super 前复制本操作 Kind/Before 弱端点及预期端点；绑定谓词必需、同步调用且不保留。Busy 覆盖限定 Super 完整栈、返回谓词/操作/字段/生命周期重检及提交；窗口内的新 Try 或旧入口在 Super 前拒绝，不自动排队。
- 旧虚 Init/Clear 与项目同名 Refresh 的每次自身 Super 同样处于真实 Busy；窗口外写入前精确撤销活动操作、Context和待发布引用，即使字段相同也不恢复旧证明。旧入口不签发 Receipt；ClearInput 沿 ASC 原权威入口失效，B0 私有来源机制不改。
- Refresh 是非虚基类方法的项目遮蔽入口，当前唯一项目调用静态类型为项目 ASC。任意基类指针/限定基类 Refresh 不在保障内；不改 UE，不宣称全 UE 调用已拦截。
- Init/Clear 提交新 Binding/LastWrite；Refresh 保留 Binding、更新 LastWrite。Clear PreserveOwner 走原生 Init(owner,null)，ClearActorInfo 走原生 Clear；Released 保留 Before 端点，不能从 After 反推 Kind。只有 Commit 成功才建立不可变 Proof及非空 OutPublication。
- 失败输出无成功 Proof，按真实原因返回 Rejected/Busy/Stale/Failed。清理只针对自己的 Operation/Context/Receipt；旧栈不清后继，已提交历史副本可保留，native 写入失败不自动回滚或改用另一种操作。
- 静态核对三入口/窗口门禁、每次项目外调后复核、输出复位、各 Kind 路由与历史端点、RAII所有退出、耗尽沿原序号、无 Publisher/GA Ready/OnSpawn 新调用；逐块逆向恢复源基线并保护 I0、GA、B0严格测试、Host/Extension。

### 7.3 非目标与停止点

Publish 仍只有声明，不新增委托/广播/去重执行；Host/Extension、GA/Task、Cancel/Cue执行器、共享 Types、测试、资产、Obsidian与全局入口均冻结。新 Try 不走旧 Init 的项目 GA通知/OnSpawn；旧通知生产迁移留后续 Publish/Host 阶段，本步不关闭 R0、完整身份/资源生命周期或任意基类 Refresh 绕行。需要迁移旧通知才能保证本步 native 执行安全时，停止具体报告，不自行扩架构。

生产实现与静态证据完成后三文件停写交回最终哈希；未授权构建、UE、Git、测试或代理，实际编译/专项及局部图文另由统筹门禁安排。

### 7.4 实际静态证据

- 实际顺序：先在本既有记录登记统筹接受的预检、三文件基线及停止点，再 apply_patch 完成生产实现。最终头只修改执行阶段注释、增加旧 Clear/项目 Refresh 声明和私有窗口/执行助手/当前 Receipt 引用；cpp 只改旧 Init 保护、增加旧 Clear/Refresh、在两个精确失效点释放匹配引用、更新 Proof 注释并在 EOF 增加执行助手。未增加第四文件。
- 保存基线整文与精确新增/替换块，逐字符构造预期头/cpp，与实际全文完全一致；从实际源码逆向移除新增块、恢复替换块后，精确还原两份基线。头624行，cpp2553行；原 B0 输入来源/重试、GA仲裁、Montage及其它 ASC 函数体没有额外修改。原旧 Init 的完整 OnPawnAvatarSet/OnSpawn 块逐字符保留在 native 窗口关闭之后。
- 七处限定 native Super 调用均静态核对处于自身 RAII 窗口：旧 Init/Clear/Refresh 各一处；新执行的 Init、Clear/PreserveOwner、Clear/ClearActorInfo、Refresh 各一处。三个旧入口和新执行在 Busy 时均先拒绝再返回，不进入 Super；旧拒绝日志含 AbilitySystem、ASC路径、入口、当前 Owner/Avatar 和准确原因。旧入口窗口外写入前只撤销当时活动操作、Context与匹配当前 Proof，不签发身份或 Receipt；同字段写入也不能继续使用旧证明。
- 窗口由唯一 bool 表示，与 I1 活动操作槽分开；序号仍只有 I1 原来源，无第二调度、native序号、队列或重试。RAII 所有退出只按本操作精确 ID 失效，Commit 已清槽时为幂等空操作；真正进入的窗口最后释放 Busy。弱 ASC 的 GetEvenIfUnreachable 仅用于仍分配但生命周期已关闭对象的元数据清理，不授予执行权或强持有对象；执行前后另检查 ASC、端点及销毁状态。
- 三个公开入口及公共执行器先完整复位独立 OutPublication；仅 Init/Clear/Refresh进入 Reserve，不支持的 Cancel/Cue明确返回默认 Rejected/InvalidRequest。普通/Bootstrap/Revoked replacement 保持 I1 既有不同准入；ClearMode逐项分支，无非法模式改走另一路的兜底。
- Reserve 后、Commit前复制原 Kind、Before Context/弱 Owner/Avatar及期望 After；必需 IsRequestContextCurrent 只借用同步 Request，调用前后核对原操作、上下文、生命周期，Super 返回后再次调用并核对，Commit 再验证 After allocation及实际 ActorInfo字段。Before 检查捕获原实际字段，不把 never-committed 的合法初始化暂态误当已就绪绑定。没有保存谓词或制造 Host-ready 条件。
- 只有 Commit 成功才标记 Succeeded/None、bCommitted=true并 MakeShared 私有不可变 Proof；Init/Refresh Notice 使用 After，Clear/Released使用保留的 Before弱端点，Owner-only Init与PreserveOwner Clear仍按原 Kind区分。ASC只保存一个当前共享资源引用；历史调用栈副本可继续读取，不证明当前绑定或发布成功。精确 Context失效、原操作失败和旧写入只释放匹配自己的当前引用，不能清后继。
- Source/Plugins 当前搜索结果：三个 Try各有声明和定义，无业务调用；Publish仅一处声明，无定义或调用。当前唯一项目 Refresh调用仍为 PawnExtension.cpp:237，其成员静态类型为项目ASC；UE5.8 基类 Refresh非虚，本项目入口为同名遮蔽，任意基类类型或限定基类 Refresh不受此保护。未修改引擎或 ActorInfo分配类型。
- 最终全文/逆向/格式与保护核对全部通过。九个冻结文件的 path/bytes/hash均保持：Types、GA h/cpp、B0 TestTypes/严格Diagnostic、CombatantState h/cpp、PawnExtension h/cpp。三个租约文件为UTF-8无BOM、LF、末尾换行、无行尾空白；Proof完整定义位于所有执行助手之前，generated.h仍为最后include。没有本会话写入全局入口、Obsidian或其它记录。

| 本次源码冻结 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 29819 | 775FB4B7659208A18F3274D67655D7427323CC6817A06FD9846659DEE826AFE9 |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 97767 | 28D487DBFC4A27020A15A707AA99F6D56A625CA4CF1971091B6185F2FC4C1B3E |

- 架构静态核对：ASC仍是唯一 ActorInfo执行/身份来源，Receipt为不可变历史资源，无循环依赖、第二 Avatar权威、可变内部状态泄露或新增强Actor所有权。新 Try没有项目 GA通知、OnSpawn、Broadcast或Publish调用；旧通知迁移未纳入本步。当前资源失效清理闭合，完整发布去重/后继接管与 Host/Extension资源生命周期尚未关闭。
- 未运行构建、UE、Git、自动化、C++用例或代理；Gate41普通73及原严格B0成功仅为写前基础，不能作为本I2b证据。R0仍开放；Publish、GA/Task/Host/Extension迁移、专项动态验收及局部 Obsidian/Canvas同步等待统筹另门禁。实现与记录最后核对后三文件停止写入，记录本身最终hash随交回消息提供，不进入下一阶段。

## 7.5 统筹复核：执行重检必须保持原准入状态

统筹在编译前独立审查发现具体缺口并授权同 I2b 租约修正：原执行 Recheck 在 Before已签发时只检查同Context，I1 Commit对Init/Clear也仅检查同Context；显式 InvalidateAvatarBinding将其改为Revoked但按既有契约保留活动Operation，调用方谓词仍true时，普通Init/Clear可能错误继续Commit。该缺口成立，首次冻结已解除，仅为关闭此项重新写入。

- 唯一目标：真实执行的Recheck按原Admission同时验证ASC自己的权威IdentityState和精确Context；普通必须Current，替换必须精确Revoked，Bootstrap必须Unissued且Before/当前Context均为空。同步纯谓词不得替代ASC权限检查。
- 精确生产文件与结果：只替换GGYGOAbilitySystemComponent.cpp中RecheckAvatarBindingExecutionOperation的准入检查；已有本记录登记证据，ASC.h保持首次冻结字节。只读依赖为I1准入/显式撤销/Commit/精确Operation失效和Types；不改共享接口。
- 先后顺序：本节登记预检→cpp单函数准入分支→静态失败/幂等替换路径核对→记录实际hash→冻结。非目标：I1序号/第二epoch、Publish、B0/严格测试、Host/Extension、其它源码、资产、UE、构建、Git、代理与图文。
- 验收断言：Match的Current→Revoked即使Context/端点不变、谓词true也返回Stale/OperationInvalidated，无Commit/Proof；Replace的Revoked重复精确Context失效保持Revoked，准入不被错拒；Bootstrap只接受Unissued与两份完整空Context。所有路径保留原操作精确清理，无后继清理或新身份来源。遇第四文件或需修改其它生命周期即停止。
- 本次审查前基线：ASC.h 29819 bytes/`775FB4B7659208A18F3274D67655D7427323CC6817A06FD9846659DEE826AFE9`；cpp 96783 bytes/`4EF65535CD33E2410B6F15638262E10EA1F8A546DED23600C71BB6139B0426D7`；本记录22251 bytes/`CD59B6CD40C766B150B302464F949AC75754ED7C706961AF903E1A604A16EEA7`。

- 实际修正：只将Recheck原“已签发则同Context、否则Unissued”的判断替换为原Admission的穷尽switch。Match要求Current且同Context；Replace要求Revoked且同Context；Bootstrap要求Unissued，Before/当前两份Context的Binding/LastWrite Serial均0、Issuer均显式空；Invalid/未知Admission拒绝。没有修改I1 Commit、显式失效或精确Operation清理接口，没有增加epoch、状态源、计数器或测试。
- 失败路径静态追踪：Match已经Reserve后，native回调或同步查询中显式撤销Before，仍保留原Operation且Context相同；后续Recheck先命中非Current返回false，Reason保持OperationInvalidated。Execute返回Stale、bCommitted=false、空OutPublication；无法到达Commit/MakeShared。RAII只精确失效本Operation，不回滚native，不触碰后继。该检查在谓词前后和Super后均执行，不依赖调用方false。
- 合法替换路径静态追踪：Replace原准入就是Revoked；同Context再次InvalidateAvatarBinding仍保持Revoked并保留原Operation，新的精确Revoked分支继续通过，不把幂等撤销误判为第二次变化。若原Operation被明确失效或Context被后继取代，前置操作ID/Context检查仍拒绝。Bootstrap不靠无效Context之间的相等运算，明确检查两份完整空值。
- 最终cpp97767 bytes/2553行，SHA256 `28D487DBFC4A27020A15A707AA99F6D56A625CA4CF1971091B6185F2FC4C1B3E`；相对审查前仅此Recheck块修改，逆向恢复该块精确得到首次冻结全文。再移除I2b已登记增改块，仍精确恢复本阶段写前基线；ASC.h保持29819 bytes及原hash，九个保护文件path/bytes/hash保持。
- 全文预期、准入三分支、同步调用顺序、失败无Proof、原Operation清理、无新增项目通知/Publish以及UTF-8无BOM/LF/末尾换行/无行尾空白静态核对通过。本节记录实际证据后再次冻结原三文件并交回最终hash；未编译、运行C++用例、UE、Git或代理，B0/Publish/Host和其它源码均未扩授权。


## 8. 统筹实际Gate42门禁（2026-10-02）

本节覆盖上文静态冻结时的“尚未编译”，不修改或删除历史证据。统筹独占构建／UE窗口，所有生产写入者均冻结；Input／Character仅只读预检。

- 完整GGYGOEditor构建Succeeded／exit0，7 actions、108.38秒，UBA93.28秒；UHT10.0367172秒、0 generated files。新运行时DLL链接，Editor DLL本次无须重链。构建日志：Saved/Logs/ModuleRepairBuildGate_20261002_42_UBT.log。
- 首轮普通UE在测试前因沙箱限制导致原生Zen／DDC没有可写节点，exit1且无index.json；失败日志Saved/Logs/ModuleRepairGate_20261002_42_Runtime.log保留。未改业务配置或用速度／动作替代，正常缓存权限重跑R1。
- 普通报告Saved/AutomationReports/ModuleRepairGate_20261002_42_R1/index.json于19.37.20 UTC为73 Success、其它计数0、1.265173077583313秒；SHA256 DDA0B4EA59C7797C21B80FD045922A864A68391EED0D953252E3F2F9DA8EB02A。原Gate41全部73路径保持，所有叶errors／warnings0，UE exit0。
- B0原严格报告Saved/AutomationReports/ModuleRepair07E2_B0_Origin_20261002_42/index.json于19.41.29 UTC为1 Success、其它0、0.01745789870619774秒；SHA256 C6F19F3E81F9417C1D143011DA72D6106552E436CD3BDD9DE62F39689B2ECFA2。innerRetry0、outerRetry1、原有限deadline0.34999999403953552，原测试未改，UE exit0。
- 原R0报告Saved/AutomationReports/ModuleRepairCombatantBindingSuccessor_20261002_42/index.json于19.43.51 UTC为2 Fail／12 errors／0 warnings、0.14825600385665894秒；SHA256 A3C1746BA7F7A37BF9E72EA87653358FEEAFC54319B297A7B17CAAE54E17CFD6。DifferentPawn8与SamePawn4条错误消息逐项与第36次相同；两例真实回调接管成功前置保持，旧Detach收尾仍破坏后继。UE exit0不代表测试通过，不关闭R0。
- 完整普通运行日志仍有49 Error＝13启动Smoke Condition failed＋34伤害专项预期拒绝＋2烘焙预期诊断；2 Warning为DDC路径写入及Python枚举同名。B0日志有13启动Error／2 Warning；不能把叶零错误称为全日志零诊断。AbsLog已正确生成，不重述Gate41日志未生成为本次状态。
- 源码h775FB4B7…／cpp28D487DB…实际哈希与组长交回吻合；Gate42前后252源及14保护资产／配置全部保持，全部UE已退出／UE0，没有保存项目资产。统筹实际全文审查新增执行／旧入口／Receipt与Admission撤销分支；逆向恢复整文是组长已交证据，统筹本次不冒称另行独立逆向。
- 这次只证明真实编译及旧回归保持，尚无直接调用三Try的独立事务专项；Publish仍仅声明、Host／Extension／GA／Task未迁移，不能据普通73关换绑／Ready或输入完整E2。K4局部结构MD／两主Canvas已由统筹同步：结构12节点10边，流程9节点7边，35链接16目标及JSON／ID／端点／标签／矩形／静态容量有效；原生UI未验。下一T1仅待精确三文件租约，生产保持冻结。

## 9. K4-I2b-T1：真实 ActorInfo 事务专项

更新：2026-10-02。统筹接受四叶预检并授权精确三文件；本组长先登记本节，生产ASC及其它源码冻结，Input并行仅互斥OriginResource文件。本节保留第8节Gate42全部实际证据，不用旧F2基线覆盖。

### 9.1 单目标、文件与基线

- 唯一目标：直接调用三Try验证真实native执行、精确撤销、Busy及不可变Receipt；四叶只关闭I2b事务执行证据，不关闭R0、Publish、Host/Extension或完整Ready迁移。唯一写入者为AbilitySystem长期组长本人，gpt-6.1-sol/xhigh，仅apply_patch，无代理。
- 精确三文件：新增Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTestTypes.h、同目录GGYGOAvatarActorInfoTransactionTest.cpp，更新本既有记录。两新增路径写前均不存在；记录写前29297 bytes，SHA256 `D5FE0DB5390E4AB8B8FF521F3D2D12885C26887ED7D6973B8280BFD4168812C8`。
- 只读冻结依赖：ASC.h `775FB4B7659208A18F3274D67655D7427323CC6817A06FD9846659DEE826AFE9`、cpp `28D487DBFC4A27020A15A707AA99F6D56A625CA4CF1971091B6185F2FC4C1B3E`，I0 Types、GA、原B0、Host/Extension及UE5.8原生Init→OnAvatarSet；已保存上述11文件path/bytes/hash。临时World构建/销毁参照现有Admission测试，使用独立命名空间，不改旧夹具/Build。
- h只定义一个InstancedPerActor薄GA和实例内单次钩子；cpp保留正常OnAvatarSet Super，通过真实GiveAbility获得实例且授予后武装。执行和权限仍由生产ASC/native掌握；观察数据只属于测试，没有私有状态写入、伪造Proof或第二绑定源。

### 9.2 四叶、断言与顺序

- NativeLifecycleAndHistory：真实Bootstrap→Init/Refresh/Clear，含两ClearMode与owner-only Init；断言实际ActorInfo/cached Owner/Avatar、Binding/LastWrite、准确Notice Kind/Before/端点和旧Receipt历史。
- RevokedReplacementAndOutputReset：撤销同Context后普通Try拒绝、完整清空预填Receipt；显式替换成功，原生回调对既有Revoked同Context再次撤销仍幂等；空Receipt读取完整复位独立Result/Notice。
- NativeRevocationBlocksOrdinaryCommit：真实OnAvatarSet内撤销Before，纯查询仍true，外层Stale/OperationInvalidated、bCommitted=false/无Proof，native完整返回且Busy释放，随后显式替换成功。
- NativeBusyWindow：真实OnAvatarSet内新Try返回Busy/NativeWriteBusy，无签发/Proof；原外层完整提交并关闭窗口后新请求正常成功。每叶保留实际回调/原Spec/原ASC的前置断言，不以纯身份模拟替代真实执行。
- 请求谓词仅同步读取调用方存活标记与弱对象，无撤销/重入/计数。单次钩子在调用前解除，所有提前返回由RAII先解除钩子、移除Spec再销毁World；不BeginPlay、不tick、不自动排队。
- 顺序：登记本节→新增h与cpp→静态全文/接口/UHT边界/清理核对→记录实际hash→三文件停写。测试执行另由统筹统一门禁；本阶段只作静态审查，四叶结果不预先标为通过。

### 9.3 非目标与停止点

没有生产、旧测试、共享Types、Publish、Host/Extension、Build、资产、Obsidian或全局文档写权；UE/构建/Git均归统筹。类型化拒绝不用ExpectedError，本步不添加日志豁免或把原R0红反转。遇第四文件、需生产修正、非原生钩子才能覆盖或额外生命周期立即停并交回，不自行修生产。

### 9.4 实际静态证据

- 实际顺序：核验统筹交接的新D5FE0DB5基线及两路径不存在，先追加本节预检，再apply_patch新增h/cpp，完成真实Refresh字段变化与钩子清理静态审查后补本证据。第1～8节和Gate42原文逐字符保留；没有第四文件写入，也未用旧F2恢复覆盖统筹记录。
- 两个新增源与保存在内存的预期全文逐字符一致。h为30行，cpp为549行；generated.h为头最后include，UE_INLINE_GENERATED_CPP_BY_NAME与头basename一致。一个非业务Transient UGameplayAbility测试类的构造/钩子定义在WITH_DEV_AUTOMATION_TESTS外，四叶和临时World在保护内；测试助手处于专属GGYGOAvatarActorInfoTransactionTests命名空间，全Source搜索未发现同名其它助手/钩子。
- 实际注册四叶均为GGYGO.AbilitySystem.ActorInfoTransaction前缀：NativeLifecycleAndHistory、RevokedReplacementAndOutputReset、NativeRevocationBlocksOrdinaryCommit、NativeBusyWindow。cpp有2处Bootstrap、10处普通Try、2处显式替换Try直接调用；没有旧Init/Clear/Refresh入口、Publish、ASC子类或私有状态访问、伪造Proof、ExpectedError、降低日志诊断或修改原测试。
- 薄GA设置InstancedPerActor；真实GiveAbility后核对合法Handle、原Spec、非CDO主实例和未武装计数0，再武装实例内单次delegate。OnAvatarSet先执行正常Super，将钩子移出并解除后才执行；真实回调观察ActorInfo allocation/ASC、Spec/主实例、已写入新Avatar与native Busy。所有回调故障会形成断言失败，不以普通GAS回归替代该前置。
- NativeLifecycleAndHistory包含owner-only Bootstrap、正常Init、Refresh、PreserveOwner Clear、同字段owner-only Init和ClearActorInfo。每次断言实际ActorInfo及cached Owner/Avatar、准确Notice/Before/端点、当前Context可校验、Operation/LastWrite来源、Init/Clear新Binding或Refresh保留Binding，返回时Busy关闭。Refresh前给Avatar新增并注册一个合法临时空Mesh组件，先断言旧ActorInfo缓存为空，再断言native Refresh发现准确新Mesh；没有为断言替换ActorInfo allocation或写入其字段，不需要资产/动画播放。
- Receipt历史断言逐项覆盖Result的Outcome/Reason/bCommitted/Operation/Before/CommittedContext及Notice的Kind/Operation/Before/After/弱端点；在后继写入和显式撤销后仍读取原历史。读取副本被清空后再次读取原Proof证据不变。失败用真实旧Receipt预填独立OutPublication，之后读取必须false且完整复位Result/Notice全部默认字段，没有手工构造非空Proof。
- 两种撤销路径分为独立叶：RevokedReplacementAndOutputReset先普通Try拒绝且native字段未改，再在显式替换的真实回调中重复撤销同Revoked Context，纯查询保持true，替换仍提交；NativeRevocationBlocksOrdinaryCommit在普通Init真实回调中撤销Current Before，纯查询仍true，必须Stale/OperationInvalidated、bCommitted=false、无新Context/Proof。native字段已完成写B但原Context仍Revoked，窗口关闭后显式替换C成功，失败Operation不复用。
- NativeBusyWindow在真实OnAvatarSet内请求C，必须Busy/NativeWriteBusy、空Operation/Before/CommittedContext、无Proof；拒绝后外层窗口仍Busy，外层B真实提交。返回后新请求C成功，原回调不重放，下一Operation serial恰好为外层+1，证明此Busy请求没有消费身份或创建等待操作。
- 唯一请求谓词只读取借用的调用方scope标记、弱ASC/Owner与Owner销毁状态，没有撤销、重入、广播、清理、计数或保存执行权。观察声明先于Fixture；RAII所有提前退出都先关闭调用方scope、解除实例钩子，再移除自有Spec并销毁World，World context保持到组件/Actor销毁之后。没有BeginPlay、tick、等待或自动重试。
- 源全文、四叶枚举、输出复位分支、原生钩子顺序、纯查询、UHT边界、命名空间/分隔符/宏保护及清理路径静态核对通过。11个保护文件path/bytes/hash保持，其中生产ASC仍h775FB4B7…/cpp28D487DB…；B0、GA、Types、Host/Extension均未写入。本节完成后最后核对三个租约文件的UTF-8无BOM/LF/末尾换行/无行尾空白并冻结。

| 新增源静态冻结 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTestTypes.h | 997 | 35C5C2A1A8E511E056B1BDEF7A3E454DC3EEB739CD4DC8A753940E04C410A001 |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTest.cpp | 33439 | 4F7CF9BAB96A680859415D97E89BC782F08B63D3DA7C1805199C86A1C2580FDA |

- 架构核对：夹具只观察生产ASC负责的事务和身份；native钩子为一次性真实GAS回调，不能变成另一执行器或绑定权威。没有新增跨模块依赖、循环所有权、长期静态钩子/状态表或资源清理缺口。测试类只属新专项，不改变任何生产接口/逻辑。
- 本阶段尚未编译或运行四叶，静态通过不等于动态成功；第8节Gate42只覆盖写前生产和旧回归。原R0保持2Fail/12错误及严格成功前置，Publish/Host/Extension/Ready迁移仍开放。本会话未运行UE、构建、Git、资产、自动化或代理，也未写Obsidian/全局入口；三文件最终hash随交回提供，冻结后等待统筹实际门禁。


## 10. 统筹实际Gate43：四叶事务专项通过（2026-10-02）

- Gate43完整GGYGOEditor日志Result: Succeeded，8 actions、38.65秒、UBA27.98秒；UHT7.0314607秒、5 generated files，新运行时DLL链接，Editor DLL无须重链。原构建进程句柄接续时已不存在，shell exit code未留存，不补称exit0；成功依据实际UBT日志。
- 实际报告Saved/AutomationReports/ModuleRepairGate_20261002_43/index.json于2026.10.01-23.46.23 UTC为77 Success，其它计数0，总0.8336034417152405秒；SHA256 AF57C5C393AC1A07EDA6962D7C845BCBEEC83E067BC3E5544289EC89814D8A2D。旧Gate42全部73路径／状态保持，仅新增四叶，所有77叶errors/warnings0。
- 新四叶NativeBusyWindow、NativeLifecycleAndHistory、NativeRevocationBlocksOrdinaryCommit、RevokedReplacementAndOutputReset全部Success，分别0.00999000295996666、0.006535399705171585、0.009868700057268143、0.009494099766016006秒，entries空。这是真实给Spec及native钩子断言，不是纯身份模拟。
- 原始日志Saved/Logs/ModuleRepairGate_20261002_43_Runtime.log保留49 Error（启动Smoke13、Damage预期34、Bake预期2）及2 Warning（DDC路径、Python枚举重名），SHA256 08B12914EE218D21483B13FA4AD064E8453ABCDB9F1EB085C802F5A37C1919A5；不能把叶零诊断称为全日志零诊断。
- UE实际请求RequestExitWithStatus(1,0,...)并已退出，进程0、无资产保存。构建前原252源／原14保护保持，仅四授权新源；接续时实际六个新源／ASC hash吻合、所有Source修改时间早于成功构建。UE前后持久证据另捕获256源及9保护，全部hash与清单保持；原会话完整构建前hash清单未持久化，不冒称再次比过丢失的全列表。Saved/ValidationRecords/ModuleRepairGate_20261002_43_BeforeAutomation.json及_Result.json保存本次可复核原始证据。
- 本步有限验收关闭I2b原生事务执行证据；Publish未定义、Host/Extension/Ready/GA/Task仍未迁移。R0最近Gate42仍2 Fail/12错误，Montage严格红与完整E2保留，本次未复测，不削弱原断言。D7资格资源只有编译证明，没有出生链／来源／真实W或失败恢复专项。

## 11. K4-P1：ASC 当前凭据发布认证

更新：2026-10-02。统筹接受P1/C1分责，仅授权本P1四文件；C1、旧通知迁移、Host/Extension/GA/Task与专项夹具均冻结。先登记本节短预检与签名，再由AbilitySystem长期组长本人gpt-6.1-sol/xhigh直接apply_patch实施；无代理、UE、构建或Git操作。

### 11.1 唯一目标、四文件基线与冻结签名

唯一目标：定义已有Publish，认证ASC当前真实Proof/Context/实际ActorInfo及调用方发布资格，以唯一发布记录完成一次事件和逐项GA通知。资源与发布许可归ASC，Host/Extension只通过已冻结参数和只读查询协作；历史Receipt不等于当前发布许可或全局Ready。

| 写前文件 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 29819 | 775FB4B7659208A18F3274D67655D7427323CC6817A06FD9846659DEE826AFE9 |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 97767 | 28D487DBFC4A27020A15A707AA99F6D56A625CA4CF1971091B6185F2FC4C1B3E |
| Source/GGYGO/AbilitySystem/GGYGOAvatarBindingTypes.h | 6351 | 2E2ACF92C2820480421C6C78AAA0F8348F6BCCF0D8474595A342BD61677343FF |
| 本既有ActorInfoTransaction记录 | 40338 | 2FBBB772950B82B25A808FFA52FEE11C6C0E0A465C20DB53E308FDE682E250EB |

写前确认第10节Gate43实际证据存在，完整保存当前四文件整文及10保护文件path/bytes/hash；不按旧5F版本恢复或覆盖。只读依赖为I0/I1/I2b、已Gate43成功的四叶、UE5.8原生Event/GAS Spec/WeakPointer实现及Character/Combatants既有候选；不导入其内部状态或具体类。

冻结公开签名：

```cpp
FGGYGOAvatarBindingResult PublishAvatarBindingNotice(
    const FGGYGOAvatarBindingPublicationReceipt& Publication,
    TFunction<bool()> IsPublicationContextCurrent);
bool IsAvatarBindingNoticeDispatching(
    const FGGYGOAvatarBindingPublicationReceipt& Publication) const;
bool IsAvatarBindingPublicationContextCurrent(
    const FGGYGOAvatarBindingContext& Expected) const;
class FGGYGOAvatarBindingNoticeEvent; // native subscriber view; only friend ASC can Broadcast
FGGYGOAvatarBindingNoticeEvent& OnAvatarBindingNotice();
```

新增InvalidPublication、PublicationInProgress、PublicationAlreadyConsumed原因，追加在原enum末尾保留已有数值；普通发布重入不用NativeWriteBusy。Event只有ASC能Broadcast，公开Getter只提供订阅；消费者仍须核对原本地资源身份。

UE5.8 Core/Delegates/Delegate.h:221的UE_PRIVATE_DECLARE_EVENT实际为public TMulticastDelegate派生，原生注释明确不再强制OwningType限制；因此优先宏不能满足本次唯一广播契约。采用等价私有TMulticastDelegate封装，公开Add/Remove及只读订阅查询，Broadcast仅friend ASC可访问；保持事件名、Getter和两const引用参数，不改共享职责或扩大文件。

### 11.2 单一状态与断言

- 一个ASC私有发布记录保存当前Receipt、来源Context和None/Pending/Dispatching/Consumed/Closed阶段；Consumed仅代表完整成功，失败/撤销为Closed，没有许可。消费释放精确自己的强引用，只留必要Context/阶段元数据；I1仍为唯一绑定/操作身份来源，无新epoch、历史表、请求闭包或第二绑定状态。
- 成功Commit安装Pending；两公开认证查询不把Pending/Closed当成功。派发认证须真实正在派发的Proof指针精确匹配；Context查询须Dispatching或成功Consumed且与I1实际当前Context/LastWrite/字段/生命周期吻合，只表示发布资格。
- Publish独立保留原Receipt/Notice/Result历史副本，校验来源、Context/LastWrite、实际ActorInfo、生命周期和必需纯查询。标Dispatching后才普通事件；各可能外调前后重检。重复/重入明确拒绝；失效只关闭匹配自己的许可，不自动Clear、回滚或重放。
- 事件阶段不持native Busy。B在普通通知中合法接管后，A返回原历史bCommitted=true与Stale；A的栈清理不得写B阶段、清B引用、读取B Context重新授权或继续A的GA通知。
- GA触发严格保留旧Init语义：原Kind为Init、After为有效Pawn且原BeforeAvatar弱身份不同才逐项OnPawnAvatarSet/OnSpawn。Before弱身份已在Reserve后、Super前复制并存入不可变Proof，足以可靠表达该策略；不从当前After反推首次出生。Refresh/Clear/owner-only Init及同Pawn重复Init不走首次出生分支。新Publish不调用无逐项重检的整块旧OnSpawn helper。
- 纯发布查询只同步借用，不保存；每次调用前后重检ASC自己权威状态。Snapshot仅临时Spec Handle/弱能力候选，不持有跨回调容器引用或授予新的执行权限。RAII关闭失败的精确自己的Pending/Dispatching许可，Consumed及后继不被清理。
- 非目标：C1取消/Cue、Host/Extension安装撤出与Getter/注册迁移、旧Init/OnGive旧通知链、GA/Task内部续写、测试/资产/全局/Obsidian。整个Ready/旧路径及R0不因P1局部完成关闭。

### 11.3 顺序与停止点

登记本节→四文件公开/私有合同与实现→有限静态重检/清理/历史保护→本记录实际证据→四文件冻结交回hash；专项夹具及动态另步。必须保留原旧Init/旧通知、I2b四叶、B0/GA/Host/Extension保护；若触发策略不能由既有Proof表达，或需改变旧行为、C1/第五文件/其它生命周期，则立即停并给具体证据，不扩大范围。

### 11.4 实际静态证据

2026-10-02：P1首次源码定义与有限静态复核完成，四文件曾停写交回统筹；以下hash与证据为首次冻结历史，Root后续实例归属审查修正见11.5。本P1未编译、未运行专项或动态验收。第10节Gate43只覆盖此前I2b/T1，不能证明新增Publisher或认证查询通过。

| 冻结源码 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 33031 | FF9F98BA9C3F8693BE65B6C46724E85043B2AA0B8DC7F9EFBE1E88E4A8BFE8B8 |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 110734 | 836623E0E7D558B0E74BB10F10B1473EE94CFC7D0283109FF2B978C9C59B6D46 |
| Source/GGYGO/AbilitySystem/GGYGOAvatarBindingTypes.h | 6506 | 31C616359B895B11EF4E72430DD34C138AD06DD1CA933563991DD3AADA649143 |

本记录最终Bytes/hash随交回另报，避免自引用hash。三源码实际完整文本均与精确预期一致；分别逆向移除本次6/3/1个精确修改块后，恢复11.1对应完整写前文本。记录第1～10节与统筹Gate43完整写前前缀逐字保持，不覆盖旧证据。

有限静态核对结果：

- 真实私有Proof要求成功Commit历史、同ASC弱Issuer、Operation与Committed.LastActorInfoWrite、Notice.Before/After及原Kind吻合。执行资格继续调用I1当前Context/完整ActorInfo字段快照/生命周期核对；空凭据和其它Issuer拒绝，历史不能自授权。
- 当前记录只有一份Receipt与来源Context/阶段。Pending与Closed不获得认证；Dispatching要求当前精确Proof，成功Consumed仅留发布来源元数据。已消费与真实派发中分别返回PublicationAlreadyConsumed/PublicationInProgress；不清外层派发，不把普通回调重入误报NativeWriteBusy。
- 必需调用方纯查询为同步栈参数，无成员保存；每次查询前后核对原ASC存活与自己发布资格。事件、各OnPawnAvatarSet、各TryActivateAbilityOnSpawn前后重检；事件前设Dispatching，事件阶段没有native写窗口。合法B接续后，A保留历史bCommitted并以Stale结束；失败作用域只关闭原精确Proof/Context，不能清B或读取B重新授权。
- OnPawnAvatarSet只持临时弱实例快照，OnSpawn只持Spec Handle候选并每项重取Spec、复制本次Spec后调用CDO helper；不跨回调保留容器引用，不使用旧整块TryActivateAbilitiesOnSpawn。已移除Spec/失效弱实例属于真实资源消失，不能替代为另一能力。原Kind与不可变BeforeAvatar身份足以表达新Pawn策略，无未决同Pawn触发契约。
- 本地UE5.8原生文件已核对：Delegate.h的事件宏不限制广播；DelegateSignatureImpl.inl/MulticastDelegateBase.h确实提供封装公开的Add、AddLambda、AddWeakLambda、AddUObject、AddSP、AddStatic、Remove、RemoveAll、IsBound与IsBoundToObject；GetAbilityInstances只复制已有两实例数组。封装私有继承且不可复制，没有公开Broadcast/Clear或基类转换。
- 10保护文件path/Bytes/SHA256全部与写前相同：I2b/T1两文件、GGYGOGameplayAbility两文件、B0原严格两文件、CombatantState两文件、PawnExtension两文件。旧Init/原Native通知链、I2b主体及B0整体保持，不因Publisher新增定义就声称生产接线迁移。
- 架构核对：没有新增循环依赖、Issuer/Serial/epoch、历史表、保留请求闭包、Host/Ready权威或帧调度；发布记录是已提交资源的派发/消费元数据。失败只撤自己的派发许可，I1撤销和后继实际写入继续关闭对应旧记录；生命周期失败可值返回，RAII的GetEvenIfUnreachable仅用于原资源元数据清理。

验证边界与后续停止点：

- 编译/UHT、空/伪造/过期/重复Receipt、查询失效、事件与两类GA回调内B接续/销毁/撤销、Consumed后实际字段变化、完整资源删除与客户端/联机行为均待独立夹具和统一门禁；上述是源码静态判断，不是运行断言已通过。
- C1 Cancel/Cue、Host公布/订阅、Extension安装/撤出/Getter/注册与GA/Task内部续写仍未迁移；原R0最近Gate42保持2 Fail/12错误，不能关闭整个换绑问题。基类非虚Refresh绕行限制保持。
- 已只读核对Obsidian的AbilitySystem/结构.md、结构/流程Canvas及入口状态；两图Receipt/流程段仍有“Publish目前仅声明”，需统筹在接管冻结源码后按事实改为“已定义、未编译/专项、调用方未接”，并补两认证查询/ASC唯一事件与阶段。结构.md和全局实施状态同步同一有限边界；本四文件租约不抢写统筹持有的图文/进度总览。

### 11.5 P1-R1：原Spec与实例成员资格审查修正

2026-10-02统筹Root实际审查后明确授权，仅重新开放ASC.cpp和本既有记录；ASC.h/Types.h及10保护文件继续冻结。无Build、UE、测试运行、Git、GA/Host/Extension/资产/图文写入。P1首次冻结hash保留历史；本节结果优先描述当前版本。

唯一目标与根因：原OnPawn候选仅存弱实例，前项回调在同一Context内移除后项Spec时，后项UObject仍活不能证明技能资源仍被授予；绑定Context与原实例资源归属必须分别核对。ASC已有ActivatableAbilities和原生SpecHandle为唯一授予来源，不新增持久表、状态或发号，不改变新Pawn触发策略。

| 修正前文件 | Bytes | SHA256 |
| --- | ---: | --- |
| ASC.cpp | 110734 | 836623E0E7D558B0E74BB10F10B1473EE94CFC7D0283109FF2B978C9C59B6D46 |
| 本记录 | 50351 | 427FCCB15D49A1B683AF144954E2193079F9ED9BA21F05B927482945CC096660 |

只读原生证据：AbilitySystemComponent.h:1116的FindAbilitySpecFromHandle默认EConsiderPending::PendingRemove；Abilities.cpp:495的ClearAbility在list锁中标记PendingRemove=true/排移除，未锁时实际撤出；:923的查找仅当显式None时排除待移除项且不包含PendingAdd；GameplayAbilitySpec.h:281的GetAbilityInstances为两原生实例数组的值复制。

步骤顺序：本节登记→唯一OnPawn候选/逐项查验块→整文逆向/保护核对→本节实据→两文件再次冻结。候选只持原SpecHandle+弱实例；每项原Context/纯查询重检成功后，以显式EConsiderPending::None重查原Spec并核对该原实例仍在其实际实例数组中，合法移除/待移除/实例脱离均跳过，不能借另一Spec继续。临时Spec指针与数组不跨通知调用；通知后原重检保留。

Root追加同租约原生证据后，授权OnSpawn每项查原Spec也显式EConsiderPending::None，排除待移除资源；正常Spec的OnSpawn触发策略和逐项重检保持。非目标与停止点：旧legacy链、Proof/阶段/公开接口、GA内部和第5文件均不修改。若需要这些改动则停止交回；本步静态断言是同Context移除后项Spec不能因弱实例活性继续OnPawn、两类通知均排除PendingRemove、原Spec仍持有原实例才调用、无新状态/外调锁。动态专项后续独立门禁，不能由本次源码审查称已运行。

实际修正与冻结证据：两处原资源调用已修正，仅ASC.cpp和本记录变化，停写交回统筹。本P1-R1未编译/UHT、未运行专项或动态验收，PendingRemove、同Context移除/实例脱离及正常通知仍需真实回调夹具验证。

- 修正后ASC.cpp为111433 Bytes，SHA256 `82124834E933DD0415612B02895441A834F96F73AE8338E9530FE0EBB551AEF9`；本记录最终hash随交回另报。实际完整cpp与精确预期一致，逆向撤销本步两个修改块完整恢复836623E0…的首次冻结文本；除OnPawn候选/逐项资格和OnSpawn查找参数/说明外，旧legacy链、Publisher的Context/纯查询前后重检、新Pawn策略和其它执行体保持。
- 当前OnPawn先Recheck，再取原弱实例；原Handle显式None只定位实际已授予且非PendingRemove的Spec，其值复制实例列表必须包含该原实例。未查到、PendingRemove、原实例已经脱离或弱实例失效都跳过该原资源；普通保留成员才调用，不查别的Spec或其它实例。成员核对的临时Spec指针与数组在外调前结束作用域。
- OnSpawn每项同样显式None，不将被原生list锁延期撤销的Spec当作现有授予；正常查到后原CDO helper、Spec复制、前后Recheck及顺序保持。未新增能力激活兜底、锁、持久候选、Issuer/Serial、状态或公开接口。
- ASC.h和Types.h完整文本/Bytes/hash分别保持FF9F98BA…和31C61635…；10保护文件path/Bytes/hash全保持首次冻结。本记录只更新11.4的“首次冻结历史”说明并追加11.5，统筹第1～10节原证据完整保留。
- 静态路径核对：同Context前项实际ClearAbility使后项原Handle查无Spec；锁中ClearAbility使原Spec.PendingRemove=true，显式None拒绝；保留原Spec但原实例脱离时Contains=false。三者均在OnPawn前continue。该推演没有执行UE，也不代表动态场景已通过。

## 12. K4-P1-T1：一次发布与真实后继首叶

2026-10-02统筹接受有限预检并授权下列三文件，写前整文/hash匹配Saved/ValidationRecords/K4P1T1_LeaseBefore.json。AbilitySystem长期组长直接apply_patch实施；无代理、构建、UE、Git或生产写入。本节尚未运行，不以Gate43旧DLL证明Publisher。

| 精确文件 | 写前Bytes | 写前SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTestTypes.h | 997 | 35C5C2A1A8E511E056B1BDEF7A3E454DC3EEB739CD4DC8A753940E04C410A001 |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTest.cpp | 33439 | 4F7CF9BAB96A680859415D97E89BC782F08B63D3DA7C1805199C86A1C2580FDA |
| 本既有交互记录 | 54739 | BA5E46AA22D4DAE75B2C4A4B3259020D4844487F71DFC7446818F1DAC441D881 |

唯一结果：只新增GGYGO.AbilitySystem.ActorInfoTransaction.PublicationExactOnceAndSuccessor一叶，验证原Receipt最多一次派发、Dispatching期间合法真实B接续令A停止后续GA通知，且A栈清理不清B发布资源。ASC继续是生产绑定/发布唯一权威；探针只记录OnPawnAvatarSet次数与弱Avatar，没有第二执行器或权限。

只读依赖：冻结P1/R1三生产源、UGGYGOGameplayAbility默认OnInputTriggered/InstancedPerActor、原生GiveAbility/Init与既有FFixture/Request/CheckActual/CheckCommit/CheckHistory。复用真实World/ASC，只在新叶生成两个真实Pawn；旧探针、原四叶、原夹具及失败断言保持，不将原CheckFailure改成接受历史已提交。

断言路径：真实GiveAbility→Bootstrap A得到Pending（两个认证查询均false、GA零通知）→Publish A事件真实Dispatching且native Busy=false→递归原Receipt得到Busy/PublicationInProgress、历史Committed仍true且无再派发→事件里按原A Context真实Init B成功但不发布→A返回Stale/ExpectedContextMismatch且原Operation/Before/CommittedContext/bCommitted历史保持，GA仍零通知、B实际Context/端点保持→A退出后Publish B成功且只通知Pawn B一次→B重发Rejected/PublicationAlreadyConsumed、A重发Stale，计数与B成功Consumed认证保持。

纯调用方查询只读原作用域与弱ASC/Owner/Pawn存活，始终真实有效，不主动关闭A来制造Stale，不调用本来拒绝Pending的ASC发布认证作为调用方准入。只绑定一个真实事件接收者，观察Before/After/Receipt；不依赖多播顺序、不直接Broadcast、不注入私有状态。所有发布失败独立精确检查历史bCommitted=true，不添加ExpectedErrors。

步骤顺序：本节预检→追加薄GA声明/定义→复用夹具并追加新叶/局部RAII→完整文本/原四叶逆向与保护核对→本节实据→三文件冻结。局部RAII先退事件，再清本叶Spec；捕获数据声明先于清理守卫，活至退订完成，原World/context清理保持。

非目标与停止点：R1移除/PendingRemove专项、OnSpawn激活、销毁、联机、C1、Host/Extension及原严格诊断不在首叶。需第四文件、生产改动、修改旧夹具/旧叶断言或放宽任何失败，则立即停止交回。不安排UE/构建；编译与动态由统筹待Input D10/Movement C37及本线全冻结后门禁。

实际静态与冻结证据：首叶及薄探针已追加，有限静态核对完成，三文件停写交回统筹。尚未编译/UHT、未运行；第43次旧结果不覆盖本叶和P1/R1。

| 当前专项源码 | Bytes | SHA256 |
| --- | ---: | --- |
| GGYGOAvatarActorInfoTransactionTestTypes.h | 1696 | 0547895431CF4D434B64C733AEDB5949C111772CE1916777AB714188A0B86844 |
| GGYGOAvatarActorInfoTransactionTest.cpp | 45843 | CC310CC758A5EB3B92C2444C2CF6CDAEE5C4BE5B7344307E5FCB02DDE9F5A890 |

- 头文件仅新增GGYGOGameplayAbility include与薄探针；cpp仅新增Pawn include、该探针构造/回调定义和一个叶。两源码实际完整文本与精确预期一致；逆向删除这些精确块后，分别完整恢复35C5C2A1…与4F7CF9BA…写前整文。原四叶、FFixture/Request/全部检查函数和旧native探针保持，注册叶数仅4→5，没有改旧失败条件。
- 新探针通过真实GiveAbility/FindAbilitySpecFromHandle(None)取得真实InstancedPerActor主实例；严格要求默认OnInputTriggered和通知数0。Bootstrap/Init与Publish均调用生产公开入口，无ActorInfo复制替身或私有Proof/阶段写入。
- 同一个事件接收者按真实Notice.After的原Context识别A/B；A Dispatching递归同Receipt只允许Busy/PublicationInProgress，并检查外层派发资格保持。重复A进入事件会记录失败后立即返回，防回归导致无限测试递归，不把重复事件接受为正常。
- A事件真实Commit B后，A调用方查询仍true；A退出必须Stale/ExpectedContextMismatch、历史bCommitted仍true且原三身份值保持、GA计数0。随后独立Publish B必须成功，GA计数1且记录B弱身份；B重复必须PublicationAlreadyConsumed、A旧重发必须ExpectedContextMismatch，事件/GA次数与B成功Consumed资格保持。历史Receipt继续CheckHistory与最初Commit一致。
- 局部资源守卫在所有实际事件捕获数据之后声明，各早退路径先Remove事件句柄再ClearAbility本叶Handle，Fixture的World/context仍存活；不保存回调容器指针。先Commit B、等A完整返回后再Publish B，直接观察后继Pending资源没有被A作用域清理。
- 11保护文件path/Bytes/hash与本步写前一致：ASC三生产源、GGYGOGameplayAbility两源、B0严格两源、CombatantState两源、PawnExtension两源。本记录完整保留§1～11前缀，只追加§12。Obsidian当前结构文档已只读核对为P1/R1已定义、未编译/生产未接；本叶新增与门禁事实由统筹同步，未抢写图文或进度入口。
- 未增加ExpectedErrors、生产路径兜底、计时/帧调度、权限或GA业务；本叶仍不证明R1资源移除/PendingRemove、OnSpawn激活、销毁、Host/Extension、联机。原R0与Montage严格失败继续可见，必须等新DLL实际运行本叶才能称本发布契约动态通过。本记录最终hash随交回另报。

## 13. K4-R1-T2：PendingRemove原授予通知归属

2026-10-02：统筹接受单叶预检，按10:20排程及Saved/ValidationRecords/K4R1T2_LeaseBefore.json明确授权以下三文件。先登记，再由长期组长直接apply_patch实施；生产/旧五叶断言/原严格诊断冻结，无Build、UE、Git、代理或图文写入。

统筹交回Gate44：完整Editor Succeeded，8 actions/30.82秒/exit0；普通77 Success/1 Fail，唯一失败为Movement旧无来源夹具。P1-T1 PublicationExactOnceAndSuccessor真实Success，entries/errors/warnings均0，旧四ActorInfo叶保持；256源码/9保护运行前后hash保持、UE已退出。本结果证明首叶有限发布契约，不证明本T2或Host/Ready迁移。此前§12“未运行”为首叶冻结时历史，本次动态状态以此段为准。

| 精确文件 | 写前Bytes | 写前SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTestTypes.h | 1696 | 0547895431CF4D434B64C733AEDB5949C111772CE1916777AB714188A0B86844 |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTest.cpp | 45843 | CC310CC758A5EB3B92C2444C2CF6CDAEE5C4BE5B7344307E5FCB02DDE9F5A890 |
| 本既有交互记录 | 60894 | 71EA5D4D49EC787EE417148D6094D2EE7BC7B9550F039EF9FC5F8AA8310EC78C |

唯一结果：新增GGYGO.AbilitySystem.ActorInfoTransaction.PublicationPendingRemoveOwnership一叶。在Publisher已捕获候选后的真实OnPawn回调里Clear后项原Spec，证明其弱实例仍活、原Spec已PendingRemove时不能获通知；原生延期的新Handle在旧移除清理后及下一合法绑定中保持。不新增业务/权限/私有状态。

只读原生证据：GameplayAbilitySpec.h:351公开FScopedAbilityListLock；GameplayAbilityTypes.cpp:371/377负责原生增减锁；Abilities.cpp:518–523的ClearAbility锁内标记PendingRemove并排原Handle，:923查找默认包含PendingRemove而None排除。无锁移除的OnRemoveAbility:681会MarkAbilityAsGarbage，不能替代“弱实例仍有效”的前置。DecrementAbilityListLock:899–918按原生pending adds再removes处理，不写数组或PendingRemove模拟状态。

事件顺序与断言：复用FFixture真实World/ASC，两个Pawn、First/Target两个真实GiveAbility主实例（默认OnInputTriggered），只读检查原生列表先后→Bootstrap A→First Arm一次hook→公开FScopedAbilityListLock覆盖Publish A→候选已捕获后First真实OnPawn Clear Target，严格确认Target弱活、含PendingRemove查询仍为原实例、只读PendingRemove=true、None查无，Context/纯谓词保持→同回调GiveAbility后继新Handle，None未可见→Publish完整返回锁内First=1/活Target=0且Succeeded/Consumed→解锁原Target Handle撤出，First和后继新Handle为实际当前授予、后继通知0→真实Init/Publish B，First累计2、后继1、两者弱Avatar=B且授予/Context保持。

薄探针仅追加可Arm/Disarm的一次OnPawn hook；记录次数/弱Avatar及Super调用顺序保持。Hook在Execute前Move/Unbind，捕获只存本叶栈数据。局部RAII声明在全部捕获数据之后，先Disarm，再按本叶原Handle清Spec；内层列表锁先释放，捕获及Fixture/World后销毁。无事件顺序猜测、私有Spec注入、ExpectedErrors或失效弱目标替代。

原子顺序：本节登记→薄hook→唯一新叶→整文逆向/旧五叶及11保护核对→本节实据→三hash交回冻结。停止点：弱Target前置不满足、需要第四文件/生产改动/旧断言变化则失败交回，不把立即Garbage的实例当存活，也不扩大矩阵。

非目标：直接无锁移除/实例脱离其它分支、OnSpawn激活、GC/销毁/联机、Host/Extension/全局Ready、C1a Cancel/Cue均不在本租约。本T2未编译、未运行；源码静态判断不等同动态验收。

实际静态与冻结证据：hook及单叶实现完成，有限静态核对通过，三文件停写交回统筹；本T2未编译/UHT、未运行，不能由Gate44首叶成功推导本叶通过。

| 当前专项源码 | Bytes | SHA256 |
| --- | ---: | --- |
| GGYGOAvatarActorInfoTransactionTestTypes.h | 1935 | 24F725D662CC4EC48C3E463F9B744B0C6896F81285C5616774C70C1DF7416C60 |
| GGYGOAvatarActorInfoTransactionTest.cpp | 58025 | 16557A1EC837BDDFA01D4AA14194CF6BFB6DE764FB681607F42875AFC6251801 |

- 头文件只新增普通hook委托、Arm/Disarm与私有hook字段；cpp新增GameplayAbilitySpec显式include、hook setter/清理及回调的Move/Unbind/Execute块，追加唯一新叶。两源码实际全文与精确预期一致；逆向撤销三个头块、两个cpp接缝块及新叶后完整恢复05478954…与CC310CC7…写前版本。五个旧叶、FFixture/Request/旧检查函数及旧native探针保持，注册叶仅5→6。
- 新叶真实Give两个不同Handle及不同InstancedPerActor主实例，严格要求OnInputTriggered，使用const原生list getter确认First/Target实际先后。调用生产Bootstrap和Publish后，只有First的真实OnPawn hook能触发原ClearAbility；HookCalls必须1，不用手动调用OnPawn替代生产通知。
- PendingRemove由原ClearAbility产生；测试只通过const Spec读取该字段。锁内严格要求Target.Get非空、含PendingRemove查询保留原Spec/原Primary、None查询为空、原Context Succeeded/None及纯查询仍true；Publish返回必须成功且活Target通知0。若原生前置不成立直接失败早退，不接受Garbage实例或伪造撤销。
- 同一hook真实Give后继，严格要求新Handle有效且不同于两个旧Handle、None尚不可见。解锁后旧Target含PendingRemove查询也为空，First仍活且精确成员保持，后继成为真实实例且通知0。B真实Init/Publish成功后First累计2/后继1、两弱Avatar精确为B、两个当前Handle仍对应原实例、旧Target未重现，B发布资格和两个Receipt历史保持。
- RAII持原Handle和原First弱实例，先Disarm后按原Handle清理；handle/capture栈变量声明先于守卫。原生列表锁局部声明在守卫之后，各早退先退锁执行原生延期变更，再由守卫清本叶资源，Fixture/World最后销毁。OneShot在执行前移出并Unbind，下一B通知不得重放hook（HookCalls仍1）。
- 本记录完整保留§1～12写前前缀，仅新增§13；11保护文件path/Bytes/hash全保持（ASC三生产源、GGYGOGameplayAbility两源、B0严格两源、CombatantState两源、PawnExtension两源）。没有ExpectedErrors、私有状态注入、生产改动或图文/进度入口写入。本记录最终hash随交回另报。
- 静态审查确认此叶能区分“弱实例仍活”与“原授予仍可获通知”；回退为弱活性判断或默认包含PendingRemove查询会触发Target零通知断言失败。此为源码路径判断，尚未执行该回归。直接无锁移除/其它实例成员变化、OnSpawn激活、GC/销毁/联机及Host/Ready仍开放；C1a仍仅有限预检，不因本租约实施。

## 14. K4-C1a：原Context限定的同步取消接缝

2026-10-02：统筹接受有限预检，按11:00排程及Saved/ValidationRecords/K4C1a_LeaseBefore.json授ASC.h/cpp与本既有记录唯一三文件写权。先登记本节，再代码、有限静态与冻结交回；Types、旧六叶、R0、GA/Task/Host/Extension、Cue、输入、资产、Obsidian/全局入口保持冻结，无Build/UE/Git/代理。

### 14.1 Gate45/46有限实测与写前范围

统筹交回Gate45：完整Editor Succeeded，7 actions/16.36秒；PublicationPendingRemoveOwnership真实Success、entries/errors/warnings均0，原五ActorInfo叶保持。普通78 Success/1 Fail，Movement夹具NewObject抽象UObject ensure导致失败，另线修复；256源码/9保护保持、UE已退出。此证据证明§13锁内PendingRemove/原弱实例通知与后继授予有限契约，不能关闭OnSpawn、其它移除/销毁/网络或Host/Ready迁移。§13未运行为交回时历史。

统筹交回Gate46：UBT Succeeded，4 actions/11.84秒；完成响应没有shell exit字段，不补称构建exit0。2026-10-02 02:55:33 UTC（北京时间10:55:33）普通79 Success/其它0，全部叶errors/warnings为0，原79路径保持，Movement旧叶恢复Success、ASC六叶保持。报告SHA256为D03A8B6E9F491ADC0492739C1BC9E15BCC2515424495497DF2137D09E9FB4D05（本轮租约记录）；256源码/9保护保持，UE exit0并退出，完整日志49 Error/2 Warning保留，不称全日志零诊断。Gate46不覆盖随后新增C1a。

| 精确文件 | 写前Bytes | 写前SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 33031 | FF9F98BA9C3F8693BE65B6C46724E85043B2AA0B8DC7F9EFBE1E88E4A8BFE8B8 |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 111433 | 82124834E933DD0415612B02895441A834F96F73AE8338E9530FE0EBB551AEF9 |
| 本既有交互记录 | 67867 | 3B9B2147CB8167E8F0D2A2E77104736E259CB3CB6637AC36B8FCA89DFC99B28C |

### 14.2 单一接口、顺序与冻结语义

```cpp
FGGYGOAvatarBindingResult TryCancelAvatarBindingAbilities(
    const FGGYGOAvatarBindingContext& Expected,
    const FGameplayTagContainer* WithTags,
    const FGameplayTagContainer* WithoutTags,
    TFunction<bool()> IsOriginalCallerCurrent);
```

无默认参数。原Context和必需同步纯查询由原Caller明确提供；临时读取当前Context不等于旧Host授权。With/Without业务数据留调用方，包括SurvivesDeath；ASC不硬编码Tag或选择另一取消策略。

唯一结果：复用I1 MatchCurrentContext的Cancel Reserve/Complete、现有FScopedAvatarBindingNativeWrite和一次限定Super::CancelAbilities。不另造GA活动权威、候选执行器、队列/调度/持久状态，不改ActorInfo、Binding、LastWrite或已冻结执行/发布方法，不签Receipt/Notice。

- 先仅校验查询存在性与Busy；标签值和指针null语义在任何外调前独立栈复制。nullptr With不筛选、非空空With匹配零，Without保持原生排除语义；不以空值错误回落改变模式。
- 内部局部Request固定Kind=CancelAbilities、Expected=原Expected、Owner/Avatar为空、ClearMode=None，并同步借用原查询。Reserve后保留原Operation/Before，进入同一native scope；只在scope内调用外部query，前后验证原weak ASC/生命周期、原operation、原Context及完整实际字段。
- 入场重检成功才Release匹配原Context的发布许可，不撤Binding。纯Caller查询验证原清理资源/作用域，不能用正在关闭的Ready资格作为取消许可。
- 一次限定Super::CancelAbilities及原生列表锁析构、返回重检、TryComplete都在native Busy scope内。新绑定/取消重入明确Busy，不排队；范围完整返回后才可合法后继。
- Succeeded/None仅表示原生调用同步返回且原归属仍有效；bCommitted=false、CommittedContext为空，Result仅保留原Operation/Before。不可取消或WaitingToExecute不被证明全部GA已End。采用完整原生调用边界，不重写成撤销立即逐项中断。
- 撤销/失效返回明确Stale/Failed，只清匹配原operation，不追加输入、Clear、Cue、Montage，不回滚取消或读取后继续权。现有Discard的撤Binding分支只适用于ActorInfo Kind；Cancel退出仅退自身operation，因此无需改共享RAII或新增状态。

只读证据：旧Extension:202原调用为CancelAbilities(nullptr,SurvivesDeath筛选)；UE5.8 Abilities.cpp:1329的完整原生列表锁/标签筛选，GameplayAbility.cpp:745–749的原生WaitingToExecute；I1已有Cancel Reserve/Complete，Discard:1751限定ActorInfo Kind，现有scope覆盖原operation精确退出。

### 14.3 验收、步骤与停止点

登记本节→仅头声明/尾部实现→整文逆向与11保护/旧流程核对→本节实据→三hash明确冻结。后续独立专项验证旧Context/空query不进入原生、null/空With区别与筛选快照、真实取消回调内Busy、返回后合法接续、撤销/生命周期失效、成功不写绑定且原生延期不冒称End。本步不添加或运行测试。

第四文件/Types、GA/Task/Host、Cue、输入/资产、原生逐项中断或新状态依赖均立即停止交回。原R0/Montage严格红、延期GA/Task内部资源归属、完整换绑/Ready/网络仍开放。C1a实现冻结后须由统筹另安排编译及专项，不从Gate46旧DLL推导完成。

### 14.4 实际静态与冻结证据

C1a已实现并冻结，仅本轮三文件。头文件新增12行声明/契约，cpp只在原EOF追加95行单方法；原头文本删除该声明块后逐字符等于写前，原cpp为完整精确前缀，删除追加方法后逐字符等于写前。现有ActorInfo executor、Publisher、I1/RAII和旧调用链全未改。§1–13及§14预检正文保留，本节替换原待补证据行。

| 冻结源码 | Bytes | SHA256 |
| --- | ---: | --- |
| ASC.h | 33717 | 15CA50AFD32EBA69B9CC24E9CE58D0F2D59ABFE3316F57DFB1C602BEB68578BC |
| ASC.cpp | 115131 | 5D91AEA7F3BB362C29E07056E61CF785152458E5A07EDD28E31CEE417960435C |

有限静态核对全部通过：两源码整文等于事先构造的预期文本且逆向恢复写前；11保护文件逐项Bytes/SHA256等于本轮基线；三文件严格UTF-8解码、无BOM、仅LF且末尾LF。记录最终Bytes/SHA256随冻结交回在外部报告，避免自指hash。

逐分支核对：空query仅判断存在性即Rejected/MissingContextQuery；Busy先拒绝；标签值和两指针presence先于scope/query复制，原生调用只取副本/原null模式。Request为栈局部，Kind固定Cancel，默认空Owner/Avatar和Clear=None已经Types只读复核；TFunction仅移入该局部且不留成员。唯一query调用点位于NativeWrite已Entered之后，其前后均以原weak ASC检查I1 operation/入场/完整实际快照，再Check原Before Context/实际字段/生命周期，query false明确RequestContextExpired。查询纯度和原Caller资源归属仍属调用方契约，不从当前Ready反推。

唯一限定Super::CancelAbilities，之前只Release原Context发布许可；之后在同一scope重检并Complete原operation。原I1 Discard仅ActorInfo Kind允许撤Binding，Cancel失效析构只清自己的operation；未新增任何状态/执行器或改变共享清理。Result默认bCommitted=false、CommittedContext为空已核Types；新方法没有赋值两字段、Commit/签Receipt/Notice、取后继Context、替代取消、逐项循环或额外输入/Cue/Montage/ActorInfo清理。

此处是静态实现交回，C1a未编译、未新增/运行专项。Gate46为变更前证据；后续由统筹安排C1a编译与§14.3专项，随后才允许Host迁移。原R0严格失败、K3延期GA/Task内部归属、生产Host/Ready、完整换绑和网络边界继续开放；现有六叶不冒称C1a验收，Obsidian/全局入口同步由统筹下一阶段维护。

## 15. K4-C1a-T1：真实取消、空筛选与native Busy单叶

2026-10-02：统筹接受只读预检，按11:44排程及Saved/ValidationRecords/K4C1aT1_LeaseBefore.json授本既有测试h/cpp与本记录唯一三文件写权。顺序为本节预检/Gate47→普通探针和唯一叶→有限静态→三hash冻结；与Input D12-A/Movement C38-T1互斥并行，全部作者冻结前不Build。生产ASC/Types、GA/Task/Host/Extension、R0、旧六叶/FFixture/探针、资产/Obsidian/全局入口保持冻结；无Build/UE/Git/代理。

### 15.1 Gate47有限实测及写前文件

统筹实际Gate47：完整Editor Succeeded，8 actions/18.04秒/exit0；新DLL普通79 Success/其它0，全部叶errors/warnings为0，原79路径与六ActorInfo叶保持。256源/9保护保持，UE exit0并退出；完整日志49 Error/2 Warning保留。此Gate编译了§14 C1a生产入口，但普通回归没有真实Cancel新叶，不等于取消动态验收。§14未编译为当时交回历史，本T1仍未编译/运行。

| 精确文件 | 写前Bytes | 写前SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTestTypes.h | 1935 | 24F725D662CC4EC48C3E463F9B744B0C6896F81285C5616774C70C1DF7416C60 |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTest.cpp | 58025 | 16557A1EC837BDDFA01D4AA14194CF6BFB6DE764FB681607F42875AFC6251801 |
| 本既有K4记录 | 75735 | 6771E832913E3E8D80050FC8CFBF83F9B45746BC9719EC92887D33C5962ACCC1 |

### 15.2 原子范围、调用链与严格断言

唯一叶为GGYGO.AbilitySystem.ActorInfoTransaction.CancelNativeFilteringAndBusy。h仅追加UGGYGOAvatarBindingCancelTestAbility普通UGameplayAbility构造声明；cpp新增构造（InstancedPerActor/ServerOnly）与该叶。使用原生默认无蓝图Activate空分支形成无业务活跃实例，不覆盖Activate/Cancel/End，不持有私有状态或制造回调；通过真实GiveAbility/TryActivateAbility及公开Cancelled/EndedWithData委托观察原生生命周期。

复用FFixture真实World/Owner/ASC和A/B Actor。先Give普通探针并确认非CDO及原Handle/primary instance，再Bootstrap/Publish A取得完整Context验证与发布资格，随后真实TryActivate要求Spec/实例均Active。非null空With调用C1a须Succeeded/None且Cancel/End零次、实例仍Active；原Before/Operation证据完整但bCommitted=false/CommittedContext为空，原Binding/LastWrite/完整ActorInfo保持，Busy=false，匹配发布资格关闭且Notice不增。

随后同一活跃实例/原Context，以null With调用C1a。真实Cancelled委托内观察Busy，并请求typed Init B：必须Busy/NativeWriteBusy、无Operation、空Receipt、原A ActorInfo/Context保持；真实EndedWithData要求原实例/Handle/bWasCancelled匹配、Busy保持。query只检查原Caller资源/作用域，不主动重入、不借Ready发布资格。原生完整返回后两个回调各一次、实例与Spec不Active，Succeeded仍不Commit/改Context/发Notice，Busy已释放。

回放原A Receipt必须Stale/OperationInvalidated、历史Commit保留且不重发Notice；随后B真实Init/Publish成功，证明原operation退出且合法接续。保留A/B Receipt历史检查，不将本叶即时End推广为不可取消或WaitingToExecute全部结束保证。

清理：捕获数据/Handle/纯Query先声明，随后局部RAII持原弱实例和委托Handle；析构先退Cancelled/Ended/Notice，再Clear原授予Handle，FFixture最后销毁World。原生End自动清End委托不影响幂等Remove；所有早退同顺序，清能力时没有栈捕获回调。原六叶、检查函数、FFixture/旧探针逐字符不改，逆向删新增三块必须恢复写前源码；11保护文件只读hash核对。

非目标/停止点：撤销/延期、非空With/Without和筛选快照变更、GC/网络、生产迁移、R0/Montage修复及图文/全局更新另步。激活/真实回调前置不成立严格失败，禁ExpectedErrors、私有状态注入或降低断言；需第四文件、生产修正或旧叶变化立即停止交回。

### 15.3 实际静态与冻结证据

普通探针及单叶已实现并停写交回。源码只新增10行UCLASS声明、7行构造及217行单叶；测试注册6→7。无任何旧探针方法、FFixture/Request、检查函数、六叶或生产改动。三文件实读整文等于事先构造的精确预期；删头尾新增class与cpp构造/单叶三块后逐字符恢复写前，两旧源码哈希因此完整还原。§1～14完整保留，仅追加§15并在本节补证据。

| 冻结专项源码 | Bytes | SHA256 |
| --- | ---: | --- |
| GGYGOAvatarActorInfoTransactionTestTypes.h | 2276 | A2485F98A499CCC083570A7468C0D654CD25615D90C65498BE3E53EADE96D14A |
| GGYGOAvatarActorInfoTransactionTest.cpp | 72136 | B3563AB10CFC61B8952DED5BB95642C9F0FD13242490D257C780F7431FDDBD67 |

有限静态核对全部通过：真实Give/TryActivate，原Handle/primary instance与Spec/实例活动读数；两取消调用精确分别为空With地址/null With，Without均null；唯一嵌套绑定只在真实Cancelled委托，真实EndedWithData检查原Handle/实例、bWasCancelled与Busy。Query来自原Request纯谓词，未加入手动重入；未override Activate/Cancel/End、直接Broadcast或注入活动状态。空With和nullWith分别严格要求0/1次Cancel/End，取消两Result都不Commit/改原Context/ActorInfo/发Notice，操作身份各自签发且不同。

旧Receipt重放明确Stale/OperationInvalidated并保留原Commit历史，之后B真实Init/Publish成功及资格保持；完整native返回后才接续。上述是新叶断言与源码路径审查，尚非实际执行通过。无论正常或早退，全部被捕获变量先于资源守卫；先Remove Cancelled/Ended/Notice委托，再Clear原Handle，FFixture/World后销毁。已自动清空的原生End委托允许幂等Remove，未引用后继Handle清理。

11保护文件逐项path/Bytes/SHA256均等于本轮基线（ASC.h/cpp/Types、GA.h/cpp、B0严格两源、CombatantState两源、PawnExtension两源）。三文件严格UTF-8、无BOM、仅LF和末尾LF；本记录最终Bytes/SHA256在冻结报告外部交回，无自指hash。没有ExpectedErrors、私有状态注入、第四文件、Build/UE/Git/代理/Obsidian或全局入口写入。

本T1未编译/UHT、未运行。Gate47只确认此前C1a生产编译和原六叶普通回归；下一步由统筹等待其它作者冻结后安排构建与新叶专项。撤销/延期、非空With/Without及快照变更、GC/网络仍另步；原R0/Montage严格红、生产Host/Ready迁移和K3内部资源归属未关闭，不能从本叶源码或未来局部成功推导全模块完成。

## 16. K4-C1b：原Context限定的同步Cue清理接缝

2026-10-02：统筹接受有限只读预检，按12:38排程及Saved/ValidationRecords/K4C1b_LeaseBefore.json授ASC.h/cpp与本既有记录唯一三文件租约。先本节/Gate48→薄入口→有限静态/保护→三hash冻结，与Input D12-B互斥且无新增API依赖。Types、GA/Task/Host/Extension、业务Tag、容器/队列、全部测试/R0、资产/网络、Obsidian/全局入口冻结；无Build/UE/Git/代理。

### 16.1 Gate48实际有限证据与写前范围

统筹实际Gate48：完整Editor Succeeded，6 actions/16.16秒/exit0；普通81 Success/其它0，原79路径保持。CancelNativeFilteringAndBusy及ColdAndRearm两新叶真实Success且errors/warnings均0；256源/9保护保持，UE exit0退出。完整日志49 Error/2 Warning保留，不称全日志零诊断。此Gate覆盖§15真实Cancel/空与null With/native Busy/返回后接续单叶，§15未运行是当时交回历史；不覆盖C1b、其它取消矩阵、异步/网络或整个Host/Ready。

| 精确文件 | 写前Bytes | 写前SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 33717 | 15CA50AFD32EBA69B9CC24E9CE58D0F2D59ABFE3316F57DFB1C602BEB68578BC |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 115131 | 5D91AEA7F3BB362C29E07056E61CF785152458E5A07EDD28E31CEE417960435C |
| 本既有K4记录 | 82439 | AD1EE5A042C77FA5FF85F040A3A4130EDDA342975A6A2409121B0CEE7DDDD8DD |

### 16.2 可复核根因、原生范围与返回契约

旧Extension.cpp:181–219先撤本地缓存，仅一次Avatar比较，随后Cancel/Input/Cue/ActorInfo清理没有外调返回重检；旧栈可能借后继实际字段继续。新入口补已有I1 RemoveGameplayCues执行接缝，原清理资源作用域由Caller证明，ASC唯一管操作/绑定身份和原生执行；不在本步迁移调用方。

UE5.8 AbilitySystemComponent.cpp:1639快照ActiveGameplayCues中的Tag，再逐Tag RemoveGameplayCue；只沿Active容器，不调用FActiveGameplayCueContainer::RemoveAllCues或清Minimal容器。:1627保持authority/prediction准入。GameplayCueInterface.cpp:336 RemoveCue更新TagMap并Invoke Removed后才RemoveAt/MarkArrayDirty/ForceReplication，:408 PredictiveRemove按原生预测标记/Removed而非直接清数组。TagMap可触发标签委托；ASC.cpp:1503读取当前ActorInfo Avatar路由，Manager:141/193及CueSet:292之后允许原生/蓝图外调和缺失Notify延期加载，Manager:337/379保留原弱Target的pending事件。同步返回不证明全部容器为空、表现已End或复制完成。逐Cue身份/原生容器同Tag重入变更、延期及复制隔离不能由外层scope凭空保证。

```cpp
FGGYGOAvatarBindingResult TryRemoveAvatarBindingGameplayCues(
    const FGGYGOAvatarBindingContext& Expected,
    TFunction<bool()> IsOriginalCallerCurrent);
```

无默认参数。先仅检查query存在性和Busy，局部Request固定Kind=RemoveGameplayCues、原Expected、默认空Owner/Avatar/Clear=None；复用MatchCurrentContext Reserve/Complete和FScopedAvatarBindingNativeWrite，不新增状态/执行器/业务Tag。保留原Operation/Before与weak ASC；scope内query前后及native返回后分别核对原ASC生命周期、Operation、Context、完整实际ActorInfo。局部纯检查只调用既有I1/Context校验，不抽象无关执行机制或修改Cancel。

入场重检成功才关闭匹配原Context发布许可，不撤Binding。一次限定Super::RemoveAllGameplayCues完整返回、重检、Complete均在同一Busy；保持原生Active Tag快照、容器/TagMap/Removed顺序，不加逐Cue循环/中断/强制全清。Succeeded/None只证明原归属有效时同步返回；bCommitted=false、CommittedContext空、无Receipt/Notice。撤销/失效明确Stale/Failed，RAII仅退自己的Remove操作，不回滚Cue、追加ActorInfo/Input清理或读取后继许可。I1 Discard撤Binding分支只适用于ActorInfo Kind，既有Remove Complete无需共享接口变更。

### 16.3 Caller续接、验收和停止点

query只证明尚未消费的原清理资源/同步作用域，不能要求Ready或匹配已先撤出的Extension本地ASC缓存；Closing不等于失去自己的清理资源。需要给旧Avatar路由Removed时，Caller必须在ActorInfo Clear前调用；不能获取Clear后的owner-only当前Context冒充旧资源授权。Cancel成功不构成全部GA End屏障；Cue成功同样不构成全部表现结束屏障。

完整native返回/重检/Complete后Busy释放，不延长到普通Released通知或后继Ready/绑定。仅关闭自己的发布许可不关闭I1 Binding，合法Clear/Released及B接续继续沿既有契约，尚未迁移的Host仍需另阶段实现/验收。

本步有限静态要求：头仅新声明、cpp仅尾部单入口，逆向精确恢复写前；全部现有executor/Publisher/Cancel及11保护保持，无成员/容器/队列/Tag/第二身份源。未来专项另租约验证空query/旧Context不入原生、真实Removed内Busy重入拒绝、返回后原Context/ActorInfo保持及合法B接续、精确撤销失败不清后继；此处不添测试矩阵。

需第四文件、逐Cue世代身份、强制全容器/客户端移除、异步/复制新归属或共享架构取舍立即停止，先提出完整方案及用户决策；不以补丁/业务兜底扩大本步。R0/Montage严格红、GA/Task内部资源、Host/Ready、资产/网络与图文全局同步仍开放。

### 16.4 实际静态与冻结证据

薄入口已实现并冻结，仅本轮三文件。头新增9行契约/声明；cpp仅在原EOF追加73行单入口，局部Request/原weak/值证据与两个纯校验闭包借用既有I1、Context校验和RAII，没有Cue候选执行器、容器、队列、成员状态或第二身份源。Cancel、ActorInfo executor、Publisher及共享Reserve/Complete/Scope全部逐字符保留。

| 冻结源码 | Bytes | SHA256 |
| --- | ---: | --- |
| ASC.h | 34240 | 7A1FEDD04CBBA92C7B931238B0EDF4B1073AE3447FAF34F2C5BC0A02BD22EEA6 |
| ASC.cpp | 118128 | 57CD3A4AE6282BDFE3246C9076AE3C0BFEC36031517F1D99F9D4C88E55D6EECA |

有限静态全部通过：三文件整文等于事先构造的预期文本；头删新声明块完整恢复15CA50AF…写前原文，cpp旧全文为精确前缀、删尾部方法完整恢复5D91AEA7…；记录§1～15完整保留，仅新增本节。11保护文件逐项path/Bytes/SHA256保持（Types、现有7叶两测试源、GA两源、B0严格两源、CombatantState两源、PawnExtension两源）；严格UTF-8、无BOM、仅LF且末尾LF通过。记录最终Bytes/SHA256在冻结交回外部报告，不自指。

逐分支核对：空query在Reserve前Rejected/MissingContextQuery，Busy先拒绝；唯一query调用点在NativeWrite已Entered之后，CheckOriginal前后两次以原weak ASC检查存活，再调既有Operation/实际快照与原Before Context/生命周期校验。query false明确RequestContextExpired；Request固定RemoveGameplayCues/MatchCurrentContext与默认空Owner/Avatar/Clear=None，不依赖Ready或Extension字段，不保留TFunction。

唯一限定Super::RemoveAllGameplayCues前只Release匹配原Before的发布许可；完整native返回后重检及TryComplete仍在同一scope。Result仅写原Operation/Before与Succeeded/None，不赋bCommitted/CommittedContext、不签Receipt/Notice、不取后继Context、不撤Binding、不追加Cancel/Input/ActorInfo动作；既有Remove失败RAII按原Operation退出，不改共享清理或回滚Cue。原生Tag快照、authority/prediction、TagMap/Removed/RemoveAt及延期路由均由原生唯一链继续处理。

本C1b未编译、未新增或运行专项；Gate48属于写前生产及§15单叶证据，不能推导本入口动态成功。后续由统筹安排编译与精确专项，普通Released/Ready接续及Caller原清理资源查询待Host迁移验证；逐Cue身份/同Tag容器重入、Minimal/全容器、异步/复制隔离仍未关闭。原R0/Montage严格红、GA/Task资源、生产调用方、资产/网络与Obsidian/全局同步继续开放。无第四文件、测试、Build/UE/Git/代理或全局写入。

## 17. K4-C1b-T1：真实native Notify Removed与Busy单叶

2026-10-02：统筹按13:02排程及Saved/ValidationRecords/K4C1bT1_LeaseBefore.json授既有ActorInfoTransaction测试h/cpp和本记录唯一三文件。先本节→Native Static Notify探针/专用Tag与唯一CueNativeRemovedAndBusy叶→有限静态/三hash冻结。与Input D12-B互斥并行，全作者冻结前不Build；原C1b生产和其它源码、旧七叶/FFixture/探针、R0、资产/Host/网络、Obsidian/全局入口保持冻结，无Build/UE/Git/代理。本T1尚未编译/运行，最近动态仍§16 Gate48；C1b生产也未编译，不能从Cancel专项推导Cue成功。

| 精确文件 | 写前Bytes | 写前SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTestTypes.h | 2276 | A2485F98A499CCC083570A7468C0D654CD25615D90C65498BE3E53EADE96D14A |
| Source/GGYGO/AbilitySystem/Tests/GGYGOAvatarActorInfoTransactionTest.cpp | 72136 | B3563AB10CFC61B8952DED5BB95642C9F0FD13242490D257C780F7431FDDBD67 |
| 本既有K4记录 | 90601 | 1AECF9D29F94E67320E38D05D29623AB9CBD863F1594F66F190D9445C99B83C8 |

唯一结果：新增GGYGO.AbilitySystem.ActorInfoTransaction.CueNativeRemovedAndBusy一叶。h追加原生UGameplayCueNotify_Static子类，只观察真实WhileActive_Implementation与OnRemove_Implementation并提供一次Removed hook；cpp增加必要公开include、具唯一前缀的native测试Tag、探针方法与单叶。Ctor保持原生IsOverride=true；不覆盖Manager/ASC执行、手动调用Removed/Broadcast或注入Cue数组/LoadedClass。

只读证据：UE5.8 Manager.h:241公开GetRuntimeCueSet，CueSet.h:61/64公开AddCues/RemoveCuesByTags。AddCues通过FGameplayCueReferencePair接受Tag/原生已加载class soft path；CueSet.cpp:292后ResolveObject可直取native class。ASC.cpp:1555真正Add并WhileActive，RemoveCue:336真正TagMap/Removed/RemoveAt；Static Notify.cpp:65–89原生Handle切换到WhileActive/OnRemove，Manager/GetWorld与抑制规则仍真实执行。无需生产资产或新增测试文件。

流程：复用真实FFixture；Bootstrap A保留实际旧Context，再Refresh/Publish取得当前A（Binding相同、LastWrite不同）。Manager/CueSet/原生class path可用、不抑制目标、专用Tag无直接既有配置且无子Tag才注册自己的映射；保存其它数据Tag/path/LoadedClass/父配置及有效路由的语义快照，数组索引/次序不作业务身份。ASC Add须触发真实WhileActive、原native类被路由且自己的TagCount=1。缺query必须Rejected/MissingContextQuery，真实旧Context必须Stale/ExpectedContextMismatch，两者无Operation且Removed/TagCount保持，不进入有效清理。

当前A C1b真实OnRemove内要求原Target、OriginalTag/MatchedTag及原参数匹配、Busy=true；typed Init B严格Busy/NativeWriteBusy、无Operation/Receipt，原完整ActorInfo保持。query沿原Request纯资源作用域，不主动重入或要求Ready。完整返回要求Succeeded/None、原Operation/Before、bCommitted=false/CommittedContext空，Context/完整ActorInfo不改、Busy=false、Removed增量恰好1、不发Notice/原发布许可关闭；随后B真实Init/Publish成功。自己的TagCount=0只是本叶单Cue观察，不证明全容器、表现或异步/复制完成。

清理：全部捕获/基线先于局部RAII；先Disarm原Notify hook/Remove原Notice，再经原ASC RemoveGameplayCue清自己的专用Tag，经原CueSet RemoveCuesByTags清自己的注册，最后FFixture/World销毁。正常显式Close与早退析构共用幂等路径；注册须真正匹配自己的Tag/path才由本资源持有，冲突不抢覆盖。Close核对其它数据和有效路由语义保持，不回填数组/LoadedClass、不清全库/换Manager/改配置或保存资产。原七叶/FFixture/检查函数/旧探针逐字符保持，逆向删新增块恢复写前源码，11保护只读核对。

停止点：Manager/CueSet/路径不可用、抑制/Tag冲突、原生WhileActive或Removed不到达都严格失败，不ExpectedErrors、Tag回调替代或放低断言；需要第四文件、生产修正或配置重置立即停交回。撤销/同Tag重入/延期/复制、Host/Ready、R0/Montage及Obsidian/全局同步另阶段。

### 17.1 实际静态与冻结证据

单叶与探针已实现并冻结，仅本轮三文件。h新增1个公开include及31行独有原生Static Notify类/委托；cpp新增5个公开include、37行探针方法、专用native Tag及308行唯一CueNativeRemovedAndBusy叶。沿继承的native HandleGameplayCue分派观察真实WhileActive_Implementation/OnRemove_Implementation，没有替换Manager、手动Removed/Tag回调、ExpectedErrors、LoadedClass注入或生产改动。

| 冻结测试源码 | Bytes | SHA256 |
| --- | ---: | --- |
| GGYGOAvatarActorInfoTransactionTestTypes.h | 3760 | 5756585199B9C0D5E1EDC48B479987D8987F977DD3BC44204106CA48BE9EE8C3 |
| GGYGOAvatarActorInfoTransactionTest.cpp | 91951 | 17D5F377B1ECA533975D62EB4A3E2E6125B4F1788899CDEE31BAA716A8B3D92F |

有限静态全部通过：三文件整文符合事先构造的预期文本；逆向删除新增块后h/cpp完整恢复A2485F98…/B3563AB1…写前原文，旧7叶、FFixture、检查函数和既有探针逐字符保留，注册数7→8且只新增本叶。11保护文件逐项path/Bytes/SHA256保持，含原C1b生产、共享Types、GA、B0严格测试、CombatantState及PawnExtension。严格UTF-8、无BOM、仅LF及末尾LF通过。项目源码rg命中归一化Windows路径分隔符后，仅本租约两测试源包含新增Tag/委托/叶名称；前次误报属于检查路径格式，未改源码或降低断言。记录§1～16完整保留，最终记录Bytes/SHA256在交回外部报告，不自指。

逐分支核对：通过公开GetRuntimeCueSet/AddCues注册专用Tag和已加载native class path，实际ASC AddGameplayCue必须到达真实WhileActive；旧Context来自真实Bootstrap→Refresh，缺query与旧Context要求无Operation/Removed且本Cue计数不变。真实OnRemove一次hook核对原Target/Tag/参数、Busy和完整ActorInfo；typed Init B严格Busy/NativeWriteBusy，Receipt清空且无Notice。完整native返回要求原Before/Operation、无Commit、原Context/ActorInfo保持、Busy释放及匹配发布许可关闭；随后真实B Init/Publish和历史证据继续有效。本Cue计数归零只作局部观察。

清理与配置静态核对：所有捕获存储先于RAII；一次hook在执行前移出并Unbind，Close先退原Notify hook和Notice，再清自己的Cue。自己的直接映射仅在Tag/path唯一匹配时经公开RemoveCuesByTags撤出，不抢清外来配置。正常显式Close与早退析构共用幂等路径，均核对其它Tag/path/LoadedClass指针/父配置及有效路由的排序语义快照，非法索引严格失败；按原生RemoveSwap允许索引/顺序改变，不写回Cue数组、不清全库。Fixture/World最后销毁，无第二权威状态或执行链。

以上均为源码与有限静态证据；本T1及新增UCLASS未编译/UHT，专项未运行，原C1b生产仍待本轮编译。最近已知动态仍写前Gate48，不能推导本Cue叶通过；由统筹在全部源码作者冻结后安排统一编译和精确专项。需要生产修正、第四文件或配置重置仍停止交回。全容器/同Tag重入、撤销/延期/复制、Host/Ready、GA/Task资源、R0/Montage严格红与资产/网络、Obsidian/全局入口继续开放。无Build/UE/Git、代理或租约外写入。

## 18. 2026-10-03 原来源清理：两源码步骤有限静态接受

### 18.1 唯一归属、顺序和接口边界

ASC 唯一拥有原 ActorInfo 写入、绑定/操作身份、native Busy 与清理来源证明；Host 继续负责 Avatar 选择及自身请求/发布生命周期，消费者清理自己的资源。两源码原子步骤先冻结“已提交来源可清理”的契约，再冻结“失败 Init 原写入可消费”的契约；本轮仅同步这两份既有记录，精确文件、基线、非目标、验收和停止点见[同步预检](Module_Repair_K4_AvatarBindingIdentity.md)。

| 来源/动作 | 输入与权限 | 结果边界 |
| --- | --- | --- |
| 工作绑定查询 | 原 Current/live 身份与完整 Context/快照 | 工作查询规则保持；不能将撤销后的清理来源提升为工作权限 |
| 已提交来源清理查询 | 原 Binding/LastWrite Issuer、精确 Context、原 allocation 与完整提交快照；Current 或 Revoked | 只证明此刻匹配原已提交来源；无执行、提交、Ready 或发布 |
| Cancel / Cue remove / typed Clear | 私有 MatchCommittedCleanupContext，仅对应三类动作，原调用方作用域查询 | 仍由既有同步执行入口负责；typed Clear 保持既有 I2 提交及 Released 凭据语义 |
| 失败 Init 原写入清理 | 失败结果的原 Operation、已保存原 WrittenActual、独立原清理作用域查询 | 只消费原失败写入并物理 Clear；不提交、不生成 Receipt/Notice/Ready |

原 Ready/Released 通知仍在既有 native 窗口退出后的规则下运行，普通后继语义保持；没有把全部通知合并进新的全局 Busy 或另建帧调度器。两种来源证明都是 ASC 私有资源，与 Context 唯一权威和调用方资源句柄分责。

### 18.2 Destroy 已提交来源契约

公开游戏线程纯查询：

```cpp
EGGYGOAvatarBindingOutcome CheckAvatarBindingCleanupContext(
    const FGGYGOAvatarBindingContext& Expected,
    EGGYGOAvatarBindingReason& OutReason) const;
```

- exact 原 Issuer/Context/LastWrite/allocation/完整字段共同认证；仅端点相同不足。当前保存的提交快照可在逻辑撤销后保留为清理来源，旧工作查询仍拒绝 Revoked 或关闭工作生命周期。
- WorkingBinding/CommittedCleanup 私有验证目的区分工作准入和原对象清理。仍合法分配、正在 Destroy 的原 Owner/Avatar 可清理；无效/析构中的 ASC、失效必需对象、原 allocation/字段改变均明确拒绝。cleanup 查询不调用/保存谓词、不修复、不签发新身份或广播。
- Cancel、Cue remove、Clear 三类只通过 MatchCommittedCleanupContext 进入。所有调用方查询仍在原 native 窗口，外调前后重检原操作；ClearAbilityInput 监听者返回后、真正写入前再次重检。
- 真正 typed ActorInfo 写入前退休旧提交来源，准入 legacy Init/Clear/Refresh 经既有失效入口退休，即使端点不变；Busy/拒绝不退休。旧提交 Context 不能认证后来失败 Init 的未提交写入。
- 新 Init/Refresh/Bootstrap/Replace 的工作生命周期不放宽；组件宿主关闭后 Clear 不重新打开它。PreserveOwner 遇关闭 Owner/组件宿主返回 LifecycleClosed，调用方须明确选 ClearActorInfo；没有自动换模式或业务成功兜底。Host 目前仍固定 PreserveOwner，所以完整 Destroy 链尚未闭合。

### 18.3 失败 native Init：证明签发与保留

公开入口（未改共享 Types）：

```cpp
FGGYGOAvatarBindingResult TryCleanupFailedAvatarActorInfoInit(
    const FGGYGOAvatarBindingOperationIdentity& OriginalOperation,
    TFunction<bool()> IsOriginalCallerCurrent);
```

1. common typed 执行器复用既有 Operation、Before 和 native Busy，覆盖普通/Bootstrap/Replace 中 Kind=Init。完整 qualified Super::InitAbilityActorInfo 返回后，在后续原调用方查询或提交之前捕获栈上候选；不能把预写入失败或没有完整返回的 native 调用视为已认证写入。
2. 捕获必须仍为 Busy 内同一个原 pending Operation/Issuer、Kind Init、同一原 ActorInfo allocation，实际 ASC/Owner/Avatar 与原请求匹配，缓存 Owner/Avatar 与真实字段匹配；WrittenActual 保存完整原 allocation、弱字段/缓存/Tag/实际 Anim 身份。依赖字段非法可能正是提交失败原因，认证原写入不等于工作就绪。
3. 私有不可变 `FFailedAvatarActorInfoInitCleanupProof` 仅保存 OriginalOperation、Before、WrittenActual；`TSharedPtr<const ...>` 成员只在完整 native Init 已返回、未提交且失败时保留，并重检此刻原 Context 元数据/原 allocation/全字段仍匹配。成功提交不保留失败证明。
4. 失败且不能保留认证来源时，原结果继续失败；单次诊断含模块、ASC、Operation、Owner/Avatar 和失败/证明原因。没有成功兜底、重新猜来源、无限重试、回滚或另一套绑定状态。
5. 后继实际 typed/准入 legacy ActorInfo 写入退休旧失败证明；拒绝/预写入失败不替换原实际写入资源。ActorInfo allocation 强引用仅防地址复用，Actor 引用仍弱；消费、后继写入或 ASC 销毁释放证明，不保存调用方查询闭包。

### 18.4 失败证明消费与 native Clear 后置条件

1. 入口不重新捕获/签发原来源，只以当前实际快照比较已保存 WrittenActual。缺查询、无效原 Operation/Issuer、无效/析构中的 ASC、Busy/活动操作、没有精确原证明或已有较新提交/写入均明确失败；原 Owner 工作生命周期关闭不作为清理就绪门槛。
2. 必须精确匹配成员中的原 Proof、Operation、Before 元数据、allocation 和全部实际字段；原 caller query 仅在既有单一 native 写窗口中同步调用，查询前后均重检原场景。调用方须持有独立有效的原清理资源作用域，不能用全局 Ready 作为这个来源查询。
3. 关闭原 Before 的匹配发布许可，退休成员证明及已提交快照、既有 Montage 来源后，才调用一次 qualified Super::ClearActorInfo。证明先消费再进 native，避免回调重入再次消费；后续失败不重新签发。未新建执行器、队列、计时器或身份序号。
4. native Clear 后及再次调用原 caller query 前后，验证原 ASC、原 Before 元数据、无新失败证明/活动操作和完整清空后置条件：Owner/Avatar/PlayerController/Mesh/Movement、ASC cached Owner/Avatar 与实际 GetAnimInstance 清空；GAS 原 ActorInfo::AnimInstance 字段及 Tag 保留，不能要求引擎未清的字段变空。allocation 及其余字段与原证明导出的后置快照精确相同。
5. 成功清理结果为 Succeeded/None，携带原 Operation/Before，`bCommitted=false`、CommittedContext 空；原 Init 失败仍然失败。此成功仅表示原写入已物理 Clear，不是绑定恢复、提交、Receipt、Notice、Ready 或发布完成。native 已 Clear 后 caller query/后置检查失败则返回失败，原证明仍已消费，不回滚或重新授予清理权限。

来源观察仍限于本项目已接入的 typed/legacy 入口；不宣称已经证明未知 qualified native 绕过的 ABA 或 ActorInfo 子类全部额外字段。没有用当前指针、旧 Context 或工作 Ready 补造失败写入来源。

### 18.5 冻结源码、验收来源与历史保护

当前两原子步骤之后的源码（本轮只读）：

| 冻结源码 | Bytes | SHA256 |
| --- | ---: | --- |
| [GGYGOAbilitySystemComponent.h](../../../Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h) | 40271 | `40535C42E7CE32E08EBC64F2F1A06317BDC2E61FB1FEE4B71CA243CFAC5D6053` |
| [GGYGOAbilitySystemComponent.cpp](../../../Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp) | 171437 | `CAD19824EBCB3527E3A43051ADBECD7DA31D8DD33D6B941C014C219A7101199F` |

- [Destroy 统筹验收](../../../Saved/ValidationRecords/ASCDestroyCleanup_20261003_RootAcceptance.json)：统筹阅读变更声明、快照目的/cleanup 查询、撤销/退休、Reserve/Recheck/Commit、typed/legacy 写及 Cancel/Cue，独立 hash 匹配该原子步骤中间冻结 h `71B46FAC…`/cpp `B76EE426…`，范围 diff 检查 exit 0；28 个 Montage/Input 方法逐个保持仅为作者证据，rootIndependentlyComparedAll28=false。
- [失败 Init 统筹验收](../../../Saved/ValidationRecords/ASCFailedInitCleanup_20261003_RootAcceptance.json)：统筹阅读 public/private Proof 及完整捕获/校验/保留/退休/消费、common Init 流程、legacy 退休/Context 比较，独立当前 hash 和范围 diff exit 0。全源码逆向恢复第二租约基线、28 个 Montage/Input 方法及第一原子步骤保持、UE native Clear 后置条件精确比较为作者证据，不能冒称统筹独立逐项完成。
- 两源码步骤状态均为 `finite_static_accepted_uncompiled`，本轮无 UHT/Build/UE/专项/Git。旧第1～17节、R0 严格失败和未运行说明保留原字节，新增历史边界只解释其时点；验收 JSON 原件只读，其 documentationPending 等字段保留保存当时事实。
- 本轮文档验收限定：两文件回读、UTF-8 无 BOM/LF/末尾 LF、新增链接存在、逆向仅删本轮插入块可恢复两写前 SHA256。最终文档 bytes/hash 随交回报告提供；没有新 Saved 证据文件或第三份摘要。保存核对并交回后两文档冻结。

### 18.6 仍开放的生产/验证边界

- Host 旧工作查询和固定 PreserveOwner 尚未迁移；CombatantState 失败 Init 分支尚未携带失败结果的原 Operation 调用新入口，独立原清理作用域查询也未接线。不得把已提交 Context 当作失败 Init 证明，也不得因清理查询成功转回 Ready。未来调用方适配需独立精确租约。
- Extension/Ready/Released/发布与 GA/Task 资源链的完整 Destroy、失败 Init 生产路径仍须集成核对。两源码原子步骤只关闭 ASC 内来源契约，未关闭完整根因。
- 统一编译须由统筹在全部可能进入构建的源码写入者冻结后安排；本轮验证仅统一编译及必要 UE 冒烟，不新增严格矩阵。原问题严格案例、断言和失败证据继续保留，未运行的专项与受影响调用链另记为未验，不能借历史 Gate/普通回归/局部 Cue 或 Cancel 通过推导新契约成功。原 R0 第36次 2 Fail/12 错误和 Montage 严格红保留，相关专项/资产/联机状态不升级。
- Obsidian 相关结构/接口/流程/实施状态与 Canvas、全局进度入口仍由统筹按后续租约同步。本轮只完成两份局部记录同步，不修改全局文档、源码或任何资产，不自动进入下一步骤。
