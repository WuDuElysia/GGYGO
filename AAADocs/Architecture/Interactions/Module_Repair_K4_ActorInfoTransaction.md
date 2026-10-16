# ActorInfo 事务、发布凭据与原来源清理

本页说明当前接口职责、来源权限和清理结果。已结束的实施、租约、构建及失败过程见[历史原文](Module_Repair_K4_ActorInfoTransaction_History_20261016.md)；历史中的“当前”按原记录时点理解。

## 职责与资源归属

| 所有者 | 唯一职责与资源 | 对外边界 |
| --- | --- | --- |
| `UGGYGOAbilitySystemComponent` | 执行原生 ActorInfo 调用，认证实际来源，提供事务、发布和清理入口 | 事务提交、Host 公布、本地 Ready 分别表达，互不替代 |
| ASC 独占的 `FGGYGOAvatarBindingProtocol` | 保存绑定/操作身份、Context、提交来源、失败 Init 证明、native Busy 和发布记录 | 私有资源；不执行 ActorInfo 写入、不保存调用方查询、不调度业务 |
| `AGGYGOCombatantState` / Host | 选择 Avatar，持有原请求、公布及清理作用域，显式选择 ClearMode | 通过 ASC 接口处理原来源，归还自身资源 |
| PawnExtension 与 Health/Base/Hero 等消费者 | 本地关联、Ready/Closing/Released 订阅及各自资源 | 只消费、撤销匹配的原资源；本地关联不签发 ASC 权限 |

Context 中的 Binding 和 LastActorInfoWrite 身份由 ASC 签发；相同 Pawn 或 ActorInfo 指针不足以认证同一次资源。来源快照由外层资源限定寿命，不能作为另一套绑定或 Ready 状态。

源码入口：[ASC 公共接口](../../../Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h)、[私有协议](../../../Source/GGYGO/AbilitySystem/Private/GGYGOAvatarBindingProtocol.h)、[Host 消费者](../../../Source/GGYGO/Combatants/GGYGOCombatantState.cpp)。身份值定义见[绑定契约](Module_Repair_K4_AvatarBindingIdentity.md)。

## 事务与发布接口

| 接口 / 值 | 输入 → 作用 → 输出或副作用 |
| --- | --- |
| `GetAvatarBindingContext` / `CheckAvatarBindingIdentity` / `CheckAvatarBindingContext` | 原 ASC 身份或 Context → 读取/核对原工作来源 → 值或明确 Outcome/Reason；工作查询要求 Current/live |
| `TryExecuteAvatarActorInfoTransaction` | 精确 Context、明确 Kind/ClearMode、必需的同步纯调用方查询 → 认证原操作并执行原生 Init/Clear/Refresh → Result；仅实际提交才有 PublicationReceipt |
| `TryBootstrapAvatarActorInfoTransaction` | Unissued 且完整空 Context → 显式首次准入 → 原事务结果；不与普通入口互作失败替代 |
| `TryReplaceRevokedAvatarActorInfoTransaction` | 精确 Revoked Context → 显式替换准入 → 原事务结果 |
| `InvalidateAvatarBinding` | 精确已提交 Context 与明确原因 → 撤销匹配工作/发布权限 → 保留原已提交清理来源；不写 ActorInfo |
| `IsAvatarBindingNativeWriteBusy` | 当前 ASC → 读取真实 native 调用栈窗口 → Busy 状态；请求不自动排队或重试 |
| `FGGYGOAvatarBindingPublicationReceipt::TryGetCommittedEvidence` | 原 Receipt 与独立栈输出 → 清输出后复制原 Result/Notice → 历史提交事实；不授予当前执行、发布或 Ready 权限 |
| `PublishAvatarBindingNotice` | 原 Receipt 与必需同步纯查询 → 核当前匹配 Proof/Context 并消费单次发布义务 → 原结果与发布状态；失败不回滚既成提交 |
| `IsAvatarBindingNoticeDispatching` | 原 Receipt → 核真实 Dispatching Proof → 派发资格；Pending 或历史副本不具该资格 |
| `IsAvatarBindingPublicationContextCurrent` | 原 Context → 核当前 Dispatching 或成功 Consumed 发布 → 当前发布来源资格，不是全局 Ready |
| `OnAvatarBindingNotice` | 调用方注册自己的监听 → ASC 派发 const Receipt/Notice → 接收者持有并精确移除自身句柄 |

ASC 是 Receipt 私有不可变 Proof 的创建者。副本只延续原历史载荷的读取寿命；后继接管、原来源失效或发布关闭后，旧副本不能发布或清理后继。Init/Refresh 的 After 与 Clear 的 Before/Released 语义分别保留，owner-only Init 不等于 Clear。

调用方纯查询只在同步栈内使用。外调返回后重新认证原操作、实际来源和调用方作用域；旧栈退出仅释放自己的原操作/发布资源，不撤销后继。Host 公布和本地 Ready 由各自拥有者完成，ASC 的 `bCommitted` 只说明原事务提交。

## 原归属取消与 Cue 清理

| 接口 | 输入、执行范围与结果 |
| --- | --- |
| `TryCancelAvatarBindingAbilities(Expected, WithTags, WithoutTags, Query)` | 精确原 Context、显式 Tag 筛选和必需同步纯清理查询；null WithTags 不筛选，非 null 空 WithTags 匹配零。共用原 Operation/native Busy，执行限定原来源的原生取消。Succeeded 表示同步返回且原归属仍匹配，不证明不可取消或 WaitingToExecute 的能力均已结束 |
| `TryRemoveAvatarBindingGameplayCues(Expected, Query)` | 精确原 Context 与独立清理作用域；沿原生 Cue 移除规则执行。Succeeded 不充当延期 Notify、异步表现或网络清空屏障 |

两接口消费已提交清理来源，只关闭匹配发布许可，不提交新 Binding/ActorInfo，也不创建 Receipt/Notice。业务 Tag 选择归调用方；原生同步返回不替代调用方对后续步骤的来源重检。

## 18. 原来源清理契约

### 18.1 唯一归属、顺序和接口边界

ASC 提供实际 ActorInfo 来源认证，私有协议保存唯一来源证明；Host 持有清理所需的原请求作用域，消费者归还自己的原资源。

| 来源 / 动作 | 输入与权限 | 结果边界 |
| --- | --- | --- |
| 工作绑定查询 | 原 Current/live 身份、完整 Context 和实际来源 | 只核工作资格；撤销后的清理来源不提供新工作权限 |
| 已提交来源清理查询 | 原 Binding/LastWrite Issuer、精确 Context、原 allocation 与完整提交快照；Current 或 Revoked | 只认证匹配的已提交来源，不执行、不提交、不签发 Ready 或发布 |
| Cancel / Cue remove / typed Clear | `MatchCommittedCleanupContext` 与原调用方清理查询 | 同步执行原动作；typed Clear 保留实际提交及 Released 凭据语义 |
| 失败 Init 原写入清理 | 原失败 Operation、已保存 WrittenActual 和独立清理查询 | 只消费失败写入并物理 Clear；原 Init 仍失败，无新 Commit/Receipt/Notice/Ready |

已提交清理来源与未提交失败写入证明属于不同资源。原 Context 不替代失败 Operation，原 Ready 不替代独立清理作用域。通知按既有 native 窗口退出与来源认证规则运行，未建立第二套执行器、身份或帧调度。

### 18.2 Destroy 已提交来源契约

```cpp
EGGYGOAvatarBindingOutcome CheckAvatarBindingCleanupContext(
    const FGGYGOAvatarBindingContext& Expected,
    EGGYGOAvatarBindingReason& OutReason) const;
```

- 纯游戏线程查询，共同认证原 Issuer、Context、LastWrite、allocation 和完整实际字段；端点相同不足以通过。逻辑撤销可保留原提交来源，工作查询仍要求 Current/live。
- `WorkingBinding` 与 `CommittedCleanup` 分开。后者允许仍合法分配、正在 Destroy 的原 Owner/Avatar；无效或析构中的 ASC、失效必需来源、allocation 或字段变化明确拒绝。查询不调用或保存外部谓词，不写状态或广播。
- Cancel、Cue remove、typed Clear 使用同一原提交来源。实际写入前退休旧来源；准入 legacy Init/Clear/Refresh 也通过既有失效入口退休。Busy 或未实际写入的拒绝不把后继认作原来源。
- 新 Init/Refresh/Bootstrap/Replace 仍按工作准入认证。ClearMode 由调用方显式提供：PreserveOwner 遇关闭的 Owner/组件宿主返回 LifecycleClosed，关闭来源使用 ClearActorInfo；ASC 不在拒绝后自动换模式。

### 18.3 失败 native Init：证明签发与保留

```cpp
FGGYGOAvatarBindingResult TryCleanupFailedAvatarActorInfoInit(
    const FGGYGOAvatarBindingOperationIdentity& OriginalOperation,
    TFunction<bool()> IsOriginalCallerCurrent);
```

1. common typed 执行器复用原 Operation、Before 与 native Busy。普通/Bootstrap/Replace 的 Init 在完整 `Super::InitAbilityActorInfo` 返回后、后续调用方查询或提交前捕获候选；预写入失败或未完整返回不构成认证写入。
2. 候选要求仍为 Busy 内同一 pending Operation/Issuer、Kind Init 和原 allocation，实际 ASC/Owner/Avatar 与请求匹配，缓存与真实字段匹配。WrittenActual 保留 allocation、弱端点、缓存、Tag 与实际 Anim 来源；这不等于工作就绪。
3. 不可变 `FFailedAvatarActorInfoInitCleanupProof` 保存 OriginalOperation、Before、WrittenActual。私有协议仅在完整 native Init 已返回、未提交且原元数据/allocation/全字段仍匹配时保留该证明；成功提交不保留失败证明。
4. 无法保留认证来源时原 Init 继续失败，并诊断 ASC、Operation、端点及失败原因。接口不重新猜来源、回滚或签发成功。
5. 后继真实 typed/准入 legacy 写入退休原失败证明；拒绝或预写入失败不替换原资源。allocation 强引用用于防地址复用，Actor 仍弱引用；消费、后继写入或 ASC 销毁释放证明，调用方闭包不被保存。

### 18.4 失败证明消费与 native Clear 后置条件

1. 入口只比较已保存的 WrittenActual，不重新捕获签发原来源。缺查询、原 Operation/Issuer 无效、ASC 无效、Busy/活动操作、缺精确证明或已有后继提交/写入均明确失败；Owner 的工作生命周期关闭不替代原清理来源判定。
2. 精确匹配原 Proof、Operation、Before、allocation 和实际字段。调用方查询在单一 native 写窗口中同步执行，查询前后核原资源；调用方持有独立有效的清理作用域。
3. 先关闭 Before 的匹配发布许可，消费失败证明，退休已提交来源及 Montage 来源，再调用一次 `Super::ClearActorInfo`。证明在 native 回调前消费，后续失败不重新签发。
4. Clear 后及再次调用查询前后，核原 ASC、Before、没有新失败证明/活动操作，以及从 WrittenActual 导出的精确后置快照。Owner/Avatar/PlayerController/Mesh/Movement、ASC cached Owner/Avatar 和实际 GetAnimInstance 应清空；GAS 原 ActorInfo::AnimInstance 字段及 Tag 按原生保留，allocation 与其余字段仍匹配。
5. 成功为 Succeeded/None，保留原 Operation/Before，`bCommitted=false`、CommittedContext 空。原 Init 仍失败；物理 Clear 不等于绑定恢复、提交、发布或 Ready。native 已 Clear 后查询/后置检查失败，证明仍已消费，不回滚或重新授予权限。

### 18.5 验证与证据边界

原清理步骤回执的验收等级仍为 `finite_static_accepted_uncompiled`：[Destroy 原回执](../../../Saved/ValidationRecords/ASCDestroyCleanup_20261003_RootAcceptance.json)、[失败 Init 原回执](../../../Saved/ValidationRecords/ASCFailedInitCleanup_20261003_RootAcceptance.json)。它们只证明各自原基线与原阅读范围，不是当前源码身份或完整生产链验收。原 hash、作者证据/统筹独立核对的区别及未运行记录保留在[第18节历史原文](Module_Repair_K4_ActorInfoTransaction_History_20261016.md#18-2026-10-03-原来源清理两源码步骤有限静态接受)。

本页整理仅核对必要源码接口、消费位置、原文保全与链接；未执行 UHT、构建、专项、UE、资产或联机验证。已有 Gate、局部 Cancel/Cue 成功及当前调用声明均不升级上述有限状态。

### 18.6 调用方与未验边界

- 当前 Host 源码已分别调用 `CheckAvatarBindingCleanupContext` 和 `TryCleanupFailedAvatarActorInfoInit(Initialized.Operation, FailedInitCleanupScope)`；Clear 显式按原 Host/Owner 关闭状态选择 ClearActorInfo 或 PreserveOwner。原“Host 固定 PreserveOwner、失败 Init 尚未接线”的阶段结论仅留历史。本页的调用链核对不证明运行时路径通过。
- Extension 的本地 Closing/Released、Host 公布与 ASC 发布、GA/Task 资源的完整 Destroy/失败 Init 接续仍需对应集成证据；清理来源查询成功不表示 Ready 或整链完成。
- 来源观察限于项目已接入的 typed/legacy 入口。未知 qualified native 绕过的 ABA、ActorInfo 子类额外字段不在已证明范围。
- 原 R0 与 Montage 严格失败、未运行专项及资产/联机边界仍按历史原证据保存，本次整理不关闭或重分类。后继验证由统筹协调共享窗口，不能借普通回归推导未验契约通过。

## 历史导航

[历史文件](Module_Repair_K4_ActorInfoTransaction_History_20261016.md)逐字节保存整理前全文；其中第1～17节含已结束的定义、实施、失败、租约和 Gate，第18节含原始清理契约及有限静态回执。历史记录不授予当前写权或当前来源权限。

- [第1～17节原过程入口](Module_Repair_K4_ActorInfoTransaction_History_20261016.md#1-唯一目标归属和精确租约)
- [第18节原始清理契约、原 hash 与未验边界](Module_Repair_K4_ActorInfoTransaction_History_20261016.md#18-2026-10-03-原来源清理两源码步骤有限静态接受)
