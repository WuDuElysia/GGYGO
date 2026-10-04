# K4-I1 ASC 绑定身份底层

## 当前状态（2026-10-03）

Destroy 已提交来源清理与失败 native Init 原写入清理两个 ASC 源码原子步骤均已由统筹接受并冻结，状态仅为 `finite_static_accepted_uncompiled`；本轮未编译/UHT，未运行专项或 UE 冒烟。当前契约见第6节及[事务记录第18节](Module_Repair_K4_ActorInfoTransaction.md)。

`CheckAvatarBindingCleanupContext` 只认证精确已提交来源，允许其逻辑撤销后的清理；旧工作身份/Context 查询继续要求 Current 和合法工作生命周期。失败 Init 尚未提交的原写入另由不可变证明和 `TryCleanupFailedAvatarActorInfoInit` 消费，不能借旧 Context 认证。清理成功不证明工作绑定、Ready 或新发布许可。

Host 仍使用旧工作查询及固定 PreserveOwner，失败 Init 分支尚未接新清理入口；完整 Destroy/失败 Init 调用链未关闭。R0 第36次严格案例 2 Fail/12 错误保留，不能由本次静态验收改写为通过。两记录同步不代表 Obsidian/Canvas、全局进度或整个模块验收完成。

## 2026-10-03 两份既有记录同步预检

- 唯一目标：将统筹已接受并冻结的 Destroy 已提交来源清理、失败 native Init 原写入清理两个源码原子步骤同步到本记录及事务记录；只关闭这两份局部 Markdown 的契约/状态同步。
- 唯一写入者：AbilitySystem 长期组长本人（本会话 `01a0e5b5-1b3a-7783-a667-e8e38d7a72fb`，gpt-6.1-sol / xhigh）；统筹已关闭源码写权限，仅授权下表两文件。无子代理。
- 冻结接口：已提交来源查询 `CheckAvatarBindingCleanupContext`；失败 Init 来源消费 `TryCleanupFailedAvatarActorInfoInit`。本步不重新定义接口或更改状态归属。

| 精确写入文件 | 写前 Bytes | 写前 SHA256 |
| --- | ---: | --- |
| 本记录 Module_Repair_K4_AvatarBindingIdentity.md | 10261 | `950172FFFE2625632A6D368CC7C95627F145D5748E86C365CC50680094F4B31A` |
| [Module_Repair_K4_ActorInfoTransaction.md](Module_Repair_K4_ActorInfoTransaction.md) | 98118 | `805DC75952CF171D6AED78723B70EAD59CCDAC34C294DD66441E95F2E18B3FF6` |

- 只读依赖：[两文件租约基线](../../../Saved/ValidationRecords/ASCCleanupRecords_20261003_LeaseBefore.json)、[Destroy 统筹验收](../../../Saved/ValidationRecords/ASCDestroyCleanup_20261003_RootAcceptance.json)、[失败 Init 统筹验收](../../../Saved/ValidationRecords/ASCFailedInitCleanup_20261003_RootAcceptance.json)、已冻结 [ASC 头](../../../Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h)/[实现](../../../Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp)及共享绑定类型。
- 顺序：核验写前 hash → 在本记录登记精确租约 → 两记录增加当前状态与契约、标明旧正文的历史阶段 → 保存回读、链接/历史/格式核对 → 返回两 hash 并冻结。每步唯一结果分别为范围可审查、当前契约可读、保存证据可核对；不自动进入调用方迁移。
- 非目标：源码、测试、夹具、Host/Extension/Teams/Input/Montage、B0/K3、Obsidian/Canvas、全局入口、Saved、资产、构建/UHT/UE/Git及新增文档写入。全局进度与架构笔记仍由统筹另租约同步，本步不冒称已完成。
- 验收断言：两项源码仅写 `finite_static_accepted_uncompiled`；清理权限与工作绑定/Ready/发布分开；Host 旧工作查询、固定 PreserveOwner 和失败 Init 分支未迁移；原正文可逆向恢复写前字节/hash，原 R0 失败及未运行事实完整保留；新增相对链接可解析。
- 停止点：仅两文件保存、回读、hash 交回后冻结。发现需要第三文件、生产/测试修正或新业务决策时停止交回，不自行扩租约。

## 历史记录（原第1～5节）

以下原“更新”及第1～5节保持写前原文，描述 I1 当时的实现、租约、失败与未运行事实；其中“未接 native”“撤销释放快照”等属于该阶段，当前语义以本记录第6节和事务记录第18节为准。历史 hash 为当时文件版本，不是当前源码或文档 hash。

更新：2026-10-01。当前I1三文件已按统筹接受的API完成底层实现和静态核对，冻结交回；I0两文件保持冻结。新增助手未接native/调用方，未编译或动态验收，R0仍未修复。

## 1. 单目标、责任和精确范围

- 唯一目标：在项目ASC内实现唯一绑定/操作序号源、已提交身份及实际ActorInfo只读证明、纯核对和精确撤销。组长本人gpt-6.1-sol / xhigh直接实施，不创建或唤醒代理。
- 精确写入：Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h；同名.cpp；本新增记录AAADocs/Architecture/Interactions/Module_Repair_K4_AvatarBindingIdentity.md。新增记录写前不存在；只用apply_patch。
- I0类型头及记录、Host/Extension/GA/Task/消费者/旧测试/旧记录/Obsidian/资产/Git冻结；不存在第四文件租约。现有Init/Clear/Refresh/PlayMontageWithGuard/GA入口保持完整，不接native窗口、Busy或通知。
- 第36次正常70 Success不证明本步；R0新DLL两个真实合法后继案例2 Fail/12错误保持为问题证据。I1不修复其旧Detach收尾或同Pawn ABA运行链。

## 2. 只读依赖和精确基线

只读依赖为I0类型、现有ASC/GAS ActorInfo及其初始化/缓存字段、根AGENTS、路由/排程/台账、已冻结A5查询。未进行全链调查。头只新增I0 include、必要前置声明、身份API和值/私有状态；cpp只新增必要include和身份助手，原代码全文保持。

| 文件 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 16499 | E9AEB8AE04165D05DA8C6C18EB07B18F5C7DCB6D8A4AE0702B1D117845BC95E5 |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 49656 | 4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF |
| Source/GGYGO/AbilitySystem/GGYGOAvatarBindingTypes.h | 6351 | 2E2ACF92C2820480421C6C78AAA0F8348F6BCCF0D8474595A342BD61677343FF |
| AAADocs/Architecture/Interactions/Module_Repair_K4_AvatarBindingTypes.md | 8969 | 34979ED3D6A89FDB17B6C93A890446F83A8AC3093615C2181D49AB0CD6FBE913 |
| AAADocs/Modules/AbilitySystem/Module_Repair_07E2_B0_Diagnostic.md | 11961 | 3FA72B5BAD40E65A2A7DFF6D420A6EA39EC30FEB38F22EE37A1115E931115AAB |
| AAADocs/Coordination/Module_Repair_Parallel_Schedule.md | 79167 | 0A9B0953B8E7D57286EF2B5D1CC7CE643F42804E2FF2AA4733B05EAEDEE34D26 |
| AAADocs/Coordination/Module_Audit_Repair_Ledger.md | 56676 | FC28F8E93BB314AA4486DF31AB335AB2E0FB549C6A1969495B0F0F1C8C82E74A |
| AGENTS.md | 10850 | 95DBB36A46ACBBB686C72D79B50ADB8D02F45B27ABEBB489F024E4723097F0D4 |

工具会话中保存原ASC h/cpp整文及以上hash，并保存除本步ASC h/cpp以外247个既有Source文件的path/bytes/hash。后续合法P1-T仅新cpp可以并行，不许可改动该既有集合；若出现新增文件须按统筹实际精确租约区分，不冒称其它作者的合法写入由本步完成。

## 3. 冻结契约和原子顺序

1. 先登记本预检/基线；添加身份API、单序号源、提交快照和唯一操作凭据；再静态核对并补证据；三文件冻结交回。
2. 全部新增API/助手只在游戏线程调用，使用check(IsInGameThread())约束；所有OutReason/OutOperation/OutContext入口复位，输出须为独立栈值，不能别名ASC内部状态。失败不泄漏候选身份/快照，不操作后继槽。
3. GetAvatarBindingContext返回最后提交的值，撤销后保留身份供精确比较，不证明当前有效。CheckIdentity/CheckContext只读，不调用谓词、不广播、不懒签发/修复/撤销；Context另核对LastActorInfoWrite。
4. 实际证明保持原ActorInfo allocation存活，捕获ActorInfo ASC/Owner/Avatar/PlayerController/Mesh/Movement/原AnimInstance字段/Tag、实际GetAnimInstance及ASC cached Owner/Avatar/Tag。弱字段保留索引/序号，不把expired解释为显式null；必需对象另检存活，可空字段保留其真实语义。快照不写回或选Avatar。
5. 私有显式Admission为Invalid、MatchCurrentContext、BootstrapNeverCommitted、ReplaceRevokedContext。普通默认空Context拒绝。Bootstrap仅Kind Init、从未提交Context、无活动凭据、ActorInfo已分配、Owner/Avatar请求合法、必需谓词存在；不调用/保存谓词，其真实执行及外调后重检由未来完整入口负责。Bootstrap不采用当前指针直接假定已运行native。
6. ReplaceRevokedContext仅显式Init/Clear且精确匹配最后撤销Context；Refresh/Cancel/Cue不能复活它。身份预留只证明底层槽成立，未授权Host选择、新生命周期或native写入。
7. Binding和Operation共用单调uint64序号，0非法，MAX可签发一次，下一次SerialExhausted，失败序号不回收。Init/Clear提交以本操作序号更新Binding和LastWrite；Refresh只更新LastWrite；Cancel/Cue仅完成槽不改Context，不证明延期GA结束。
8. Context撤销只撤销精确已提交记录，不能因后继操作引用它就撤销该操作；操作撤销必须精确匹配Operation identity。Bootstrap无Context时仍可精确撤销其操作。None/未定义或非撤销用途Reason拒绝，不能伪造成功；撤销幂等且释放匹配快照。

## 4. 验收断言、非目标和停止点

- 原ASC整文保留：移除本步新增include/声明/定义/私有状态后，精确恢复原h/cpp字节内容；不改旧函数、原签名、输入/GAS/播放/GA执行路径。I0及247个既有保护源逐项保持。
- 静态核对默认非法、显式Bootstrap、撤销后不能Bootstrap、同Issuer/不同Issuer/Serial0、null与expired、Refresh Binding稳定/LastWrite更新、正规签发A→B→A旧身份失效、序号耗尽/失败不回收、旧槽不清后继、纯查询不变状态/无外调、非法撤销Reason与所有输出复位。
- 持有allocation只用于只读证明；撤销/失败/完成释放匹配快照。没有第二Avatar/播放权威、队列、时钟、跨模块依赖或资产状态。
- 本步不接native入口，旧入口真实ABA/Destroy/重入绕过仍未关闭；不宣称能观测未接链的A→B→A。ActorInfo子类额外字段不在本基类证明内；真实执行方仍需其专项条件。
- 本步已按I0定位并只读复核Obsidian计划蓝图/AbilitySystem结构；新增接口尚未列入该类清单，底层也未接运行链。不写统筹冻结的Obsidian/Canvas，新增接口及实施状态须由统筹另行文档阶段同步；本步不声称架构笔记已全部同步或事务已实现。
- 测试/编译/动态/笔记分阶段。需要第四文件、I0变化、native窗口或跨模块调用方时停止。本步不UE/构建/Git/代理/资产操作；静态证据交回后停写，不进入I2。

## 5. 实际证据

- 写入顺序已执行：先创建本记录登记预检/范围/基线，再添加ASC头四个块（I0 include、必要前置声明、public API、private值/助手/状态），cpp只新增三个必要include和末尾身份定义块；全部apply_patch，未写第四文件。
- ASC h初步静态冻结为21762 bytes/SHA256 `8C0FF34E4593F4F445174A329988467E949421679CA04087EEBE73F1763656AF`，相对基线仅新增104行；cpp为69669 bytes/SHA256 `3753A550C7E9FAC032E049E5A2C9C69342F3EFD1AB92E9F2B8FCF304147014AE`，仅新增561行。工具会话以原整文和本步新增块构造预期文本，h/cpp均逐字符完全一致；从实际全文移除各新增块，精确恢复两份原完整文本，零原行改写/删除。因此旧Init/Clear/Refresh/PlayMontageWithGuard、所有原GA/输入/组仲裁执行入口和签名完整保持。
- 新增12个ASC成员定义逐个有游戏线程check。所有OutReason/OutOperation/OutContext/Snapshot入口复位；默认/非法Admission、非法Kind/ClearMode、缺失谓词、失效Owner/Avatar、序号耗尽和旧操作路径均不泄漏候选输出。占用身份槽返回NativeWriteBusy只描述底层槽冲突，不证明native窗口实现。
- 新代码没有Super/native绑定/播放/Cancel/Cue调用，没有Broadcast，没有IsRequestContextCurrent调用，私有凭据也没有TFunction成员；只检查谓词存在。未来完整执行入口仍必须执行谓词/外调重检和权威准入，private预留/提交true不是公开绑定成功。
- 实际字段核对覆盖原allocation及全部已登记字段/实际Anim/ASC缓存和Tag，使用HasSameIndexAndSerialNumber保留弱身份。完整清空与owner-only状态按显式字段校验；原AnimInstance字段仅作证明，native Clear不清此字段，不能拿其残留冒充当前实际Anim。合法null与expired弱Avatar分支不同。
- Context撤销释放当前证明、不关闭引用它的待完成槽；非法撤销Reason直接拒绝。操作撤销/提交/完成先比准确Operation identity，旧操作不清新槽；匹配的提交失败释放该槽且撤销仍匹配的原ActorInfo证明，避免失败后的字段回到原指针就恢复旧权限。序号单源/0无效/MAX防回绕/失败不回收均有静态分支；Bootstrap从未提交/显式模式、ReplaceRevoked仅Init/Clear、Refresh不能复活与LastWrite分责一致。
- 247个既有保护Source逐项path/bytes/hash保持，包括I0、Host/Extension/GA/Task、旧测试与A5/P1已冻结源码。I0独立记录、B0诊断记录、AGENTS保持。排程/台账由统筹并行治理更新，本会话未写且未冒称其hash保持；复核本步仍只三文件，P1-T1仅其新增测试cpp/记录获独立租约。
- 尚无新增助手调用方；全Source搜索仅声明/定义及本组内部调用。I1使ASC头包含I0，因此后续构建将接触I0，但本轮没有编译，不能回写第36次已编译I0。没有运行UE/构建/Git/测试/代理，未改资产/笔记/旧记录。
- 以上为静态定义/分支/原代码保持证据，不是动态Bootstrap/耗尽/ABA/原生回调或完整生命周期验证。新身份没有接入Init/Clear/Refresh/Actor EndPlay；未中介的A→B→A、ASC撤销/就绪与完整消费链仍开放，R0第36次2 Fail/12错误不改变。真实专项须另租约后由统筹安排门禁。
- 三文件在本轮最后全文/格式/hash读回后均明确冻结。记录最终hash随交回消息提供；停止写入，不进入I2，不自行追加记录或修改笔记。

## 6. 2026-10-03 当前清理来源契约

### 6.1 已提交来源、工作权限与失效

```cpp
EGGYGOAvatarBindingOutcome CheckAvatarBindingCleanupContext(
    const FGGYGOAvatarBindingContext& Expected,
    EGGYGOAvatarBindingReason& OutReason) const;
```

- ASC 仍唯一签发绑定/操作身份并执行 GAS ActorInfo；本查询仅游戏线程纯核对，无谓词、广播、身份签发、修复或状态修改。必须匹配 Binding 与 LastActorInfoWrite 的原 Issuer、ASC 当前记录的精确 Context、仍实际持有的原 ActorInfo allocation 及完整字段快照。
- 只有 Current/Revoked 且实际保存已提交快照的来源可以认证。快照同时比较 ActorInfo ASC/Owner/Avatar/PlayerController/Mesh/Movement/原 AnimInstance/Tag、实际 GetAnimInstance、ASC 缓存 Owner/Avatar/Tag；弱引用按原索引/序号区分失效与显式 null，不因端点指针相同跳过 LastWrite 或 allocation。
- 单个既有 `AvatarBindingActorInfoSnapshot` 在逻辑撤销时保留，唯一用途增加精确清理来源；原工作查询继续 Current/live 规则，Revoked 不能启动新工作。私有 WorkingBinding/CommittedCleanup 验证目的分别处理工作生命周期和清理生命周期，清理可接受仍合法分配、正在 Destroy 的原 Owner/Avatar，不能接受无效/析构中的 ASC、失效必需对象或已变化字段。
- 真正 typed ActorInfo 写入在进入 native 写前退休旧已提交快照；准入的 legacy Init/Clear/Refresh 通过既有失效入口退休它，即使 Owner/Avatar 相同也如此。Busy/拒绝且没有真实写入的调用不退休来源。逻辑撤销不等于实际写入，历史 Context 不能从新 ActorInfo 重新推断清理权限。
- 仅 Cancel、Cue remove、Clear 三类动作使用私有 `MatchCommittedCleanupContext` 准入。请求者仍须提供原调用方资源作用域查询，ASC 在原 native 窗口内核对；新 Init/Refresh/Bootstrap/Replace 的工作准入没有因此放宽。Clear 中 ClearAbilityInput 监听者返回后、真实写入前增加原操作/调用方重检；未增第二执行器或全局调度窗口。
- ASC 组件宿主关闭时，新 Init/Refresh 工作被拒绝，Clear 不重新打开宿主生命周期。显式 PreserveOwner 遇关闭 Owner 或组件宿主返回 LifecycleClosed；调用方必须明确选择 ClearActorInfo，ASC 不自动换模式。Typed Clear 仍遵循既有 I2 提交/Released 凭据契约；清理来源查询本身不产生提交、Ready 或发布权限。

### 6.2 未提交的失败 Init 来源

失败 native Init 已经真实写入、随后调用方/提交核对失败时，旧已提交 Context 已不拥有该写入。新增私有不可变 `FFailedAvatarActorInfoInitCleanupProof` 只保存原 Operation、Before 与返回时的 WrittenActual；没有第二绑定状态、序号、队列、计时器或请求闭包。

证明在同一 typed Init 的完整 Super 调用返回后、后续调用方查询/提交之前捕获，覆盖普通、Bootstrap、Replace 的 Init 路径；只在未提交的失败返回保留且必须仍精确匹配原场景。成功提交不保留该失败证明。清理入口只比较已记录的原证明，禁止在清理时重新捕获当前来源；必须携带失败结果的原 Operation，并提供独立有效的原清理资源作用域查询。完整捕获、消费、后置条件与失败边界见[事务记录第18节](Module_Repair_K4_ActorInfoTransaction.md)。

该证明只保持原 ActorInfo allocation 以防地址复用；Actor 端点仍为弱引用，不保存调用方闭包。后继真实 typed/legacy ActorInfo 写入、清理消费或 ASC 销毁释放它。与已提交快照的来源/生命周期分开，不竞争 Context 权威；无法认证的失败仍明确失败并提供可定位诊断。

### 6.3 验收与剩余边界

- [Destroy 统筹验收](../../../Saved/ValidationRecords/ASCDestroyCleanup_20261003_RootAcceptance.json)接受声明、快照目的、清理查询、撤销/退休、Reserve/Recheck/Commit、typed/legacy 写和 Cancel/Cue 路径的有限静态证据，独立 hash/范围 diff 核对通过；28 个 Montage/Input 方法保持是作者证据，统筹未逐个独立比较。
- [失败 Init 统筹验收](../../../Saved/ValidationRecords/ASCFailedInitCleanup_20261003_RootAcceptance.json)接受原证明捕获/校验/保留/退休/消费及 common Init 流程的有限静态证据，独立 hash/范围 diff 核对通过；整文逆向恢复、28 个方法及第一原子步骤保持、UE native Clear 后置条件逐项对照仍标明为作者证据。
- 当前两个源码步骤都仅 `finite_static_accepted_uncompiled`；最新冻结源码 bytes/hash 见事务记录第18节。验收 JSON 的“后续原子步骤/文档待同步”属于各自保存时刻，原 JSON 本轮只读且完整保留。
- Host 旧工作查询/固定 PreserveOwner、CombatantState 失败 Init 分支未迁移，Extension/Ready/发布消费链、测试/统一编译/专项/动态/资产/联机及架构笔记同步仍独立开放。不能以局部来源认证代替完整 Destroy 或原 R0 严格复现验收。
- 本次两记录仅新增当前说明与历史边界，不改原第1～5节。按预检保存回读、逆向恢复原字节/hash、核对新增链接和 UTF-8/LF；最终两文档 bytes/hash 随交回报告提供，不在文档内自指。交回后两文档冻结，不进入调用方、测试或笔记阶段。
