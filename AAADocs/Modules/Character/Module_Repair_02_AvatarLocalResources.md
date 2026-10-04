# Character：Avatar 本地资源四阶段接口

## 1. 本轮预检与唯一目标

2026-10-02：统筹授权 K4-Character-L1，基线为 [CharacterLocalAPI_LeaseBefore.json](../../../Saved/ValidationRecords/CharacterLocalAPI_LeaseBefore.json)，有效范围见[并行排程](../../Coordination/Module_Repair_Parallel_Schedule.md)。组长直接执行，无子代理。本轮只关闭 Extension 的精确本地资源框架；新接口没有生产调用，不表示 Host、Ready 或 R0 已修复。

精确三文件：

1. `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h`
2. `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp`
3. 本记录 `AAADocs/Modules/Character/Module_Repair_02_AvatarLocalResources.md`

写前核对：256 个源码和 9 个保护项均与租约基线一致，本记录不存在。Extension.h 写前 SHA256 为 `6190EB9134ECDE4735FC67C0CD564D87C3EEDAE9BC477E16ACA296368F7C96FD`；Extension.cpp 为 `E76FC4182469B76C30BB0FAE980B5DB2A6D4BD7676BA30C7741F6D24B8BC4E10`。

统筹交回 Gate49R1 编译成功、真实 `CueNativeRemovedAndBusy` 通过且 UE 已退出。此为前置证据，本会话没有执行构建或 UE；不由前批证据推导本接口已编译或动态通过。

## 2. 职责、依赖与非目标

- ASC 是 Binding、ActorInfo 事务和真实发布凭据的唯一权威；只读依赖为 [ASC 头文件](../../../Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h)、BindingTypes 和[现有 K4 交互合同](../../Architecture/Interactions/Module_Repair_K4_ActorInfoTransaction.md)。
- Host 选择并公布 Avatar、管理销毁订阅、编排事务；Extension 只保存自己的本地资源和通知消费义务，不依赖具体 Host 类。
- Health、Hero、Movement 等消费者分别拥有自己的订阅和资源；本记录没有把它们的委托或执行器转交 Extension。
- 无新 Binding 序号、ASC、帧调度器或 ActorInfo 执行链。资源句柄是本地生命周期凭据，不是 ASC 执行许可。
- 旧 Initialize、Uninitialize、Getter、RegisterAndCall 和所有其它旧函数逐字保持。新接口不调用旧初始化、配置分发或旧卸载，不操作 Cancel、Cue、输入或 ActorInfo。
- Host、消费者、ASC、旧 R0、其它测试、资产、网络、Obsidian、全局文档、Build、UE、Git 均为非目标。

## 3. 原子步骤、断言与停止点

```text
登记本预检
  -> h：本地身份 / opaque 句柄 / 结果 / 通知 / 四阶段接口
  -> cpp：仅追加本地实现，旧文本作为完整前缀保留
  -> 静态：逆向还原旧文本、真实认证顺序、精确资源清理、保护哈希
  -> 本记录补实据，交回三个哈希并冻结

之后另租约：消费者适配 -> Host + 旧入口同门禁切换
  -> 原 R0 严格复测 -> 图文
```

为什么这样写：新路径未接入时保留旧生产证据；生产切换必须同时关闭旧 Getter 和注册回放的绕过入口。改了会坏什么：首步改旧入口会先让尚未迁移的调用方失去 ASC；给新路径增加旧缓存回落又会绕过真实 Ready。

验收断言：

- 身份为原 weak ASC、Pawn 与 ASC Binding；不同 Binding 的同 Pawn 不相等，弱对象失效不丢失比较身份。
- Install 不开放 Ready；真实 Dispatching 认证先于历史 Receipt 查询。
- Withdraw 先移走原当前槽，允许 ASC 失效时清理；只修改原记录。
- Released 先消费通知标记，再外调；精确重复不广播，不清后继。
- Refresh 只更新曾真实 Ready 的同资源，不升级未 Ready 安装，不重复旧 Initialized。
- 本地结果保留原 Resource 和历史 bLocalChanged，没有 ASC Commit 承诺。
- 普通通知不持有本地 Busy 或原生 Busy，不拒绝完整原生返回后的合法续接。

停止点：本地框架静态交回即冻结；第四文件、生产迁移、共享接口或新生命周期需求立即停止。编译与动态专项由统筹另安排，不新增测试或借普通回归关闭 R0。

## 4. 数据与四阶段合同

`FGGYGOPawnASCResourceIdentity` 保存 weak ASC、weak Pawn、ASC 签发 Binding。`FGGYGOPawnASCResourceHandle` 默认为空，仅 Extension 能创建；复制保留同一原本地资源。公开身份副本可写，但不修改 opaque 记录，也不授权 ASC。

`FGGYGOPawnASCLocalResult` 字段：Outcome、Reason、原 Resource、bLocalChanged。Outcome 为 Rejected / Succeeded / Stale / Failed；Succeeded 只描述本地步骤。发生改变后因回调失效返回 Stale，bLocalChanged 仍为 true。Install 被拒绝且未创建资源时 Resource 为空；当前槽中同 Binding 重复安装返回原句柄而不重装。Withdraw 清空槽后，若同一 Context 仍通过 ASC 和生命周期校验，可创建新的 opaque 记录；它与旧句柄不同，安装不直接 Ready。

Reason 的实际分类为 None、InvalidArguments、InvalidASC、InvalidPawn、WrongExtension、LifecycleClosed、InvalidBinding、ContextMismatch、ResourceConflict、ResourceNotInstalled、ResourceNotWithdrawn、InvalidPublication、PublicationNotDispatching、ReadyNotEstablished、CallbackInvalidated。拒绝和失效有带模块、Extension、ASC、Pawn、Binding 和原因值的 Verbose 诊断；查询不刷日志。

本地记录保存不可变所属 Extension、Identity、InstallationContext，以及已认证 PublishedContext、安装/曾 Ready/Released 已消费标记。没有最后撤出身份、退役黑名单、历史表或新序号。旧记录的已撤出状态和通知义务只留在原 opaque 句柄里，不能变成拒绝后继装配的政策。

`FGGYGOPawnASCLocalNotice` 保存 Kind（Ready / Released / Refreshed）、原 Resource、PublishedContext。Released 的 PublishedContext 为空，只表示本地释放。身份消费者用自己的原资源匹配清理；注册返回精确 FDelegateHandle，移除原句柄，不用 RemoveAll 撤后继订阅。

```text
Install(ASC, Pawn, CommittedContext):
  验 ASC / Pawn / Extension 生命周期、当前 Context 与实际 Avatar
  已有不同资源 -> 明确拒绝
  当前槽已有同 Binding -> 返回原资源，不重装
  当前槽为空 -> 不因历史撤出而拒绝
  安装本地记录 -> Succeeded，未 Ready

Withdraw(Resource):
  验原句柄归本 Extension
  已撤出 -> Succeeded，无改变
  验原记录就是当前槽
  清当前槽；原记录标记已撤出 -> Succeeded

Released(Resource):
  验原记录已撤出
  Extension 已关闭 -> 仅退休原通知义务，Failed / LifecycleClosed，不广播
  已消费 -> Succeeded，无改变
  先消费原 Released
  身份通知；外调返回核对原记录
  无后继才能进入旧无参数观察通知
  后继已出现 -> Stale，保留原通知改变事实，不清后继

Ready(Resource, Receipt):
  验原已安装资源
  ASC.IsAvatarBindingNoticeDispatching(Receipt) -> 必须成功
  Receipt.TryGetCommittedEvidence -> 只读取已认证的历史
  验 Initialized / Refreshed、原 Binding / Pawn / Context
  Refreshed 且从未 Ready -> 拒绝
  消费本次原发布 Context；身份通知
  每次外调返回验原资源与真实派发凭据
  Initialized 才发旧无参数观察通知；Refreshed 不重复它
```

为什么这样写：Binding 标识 ASC 绑定，opaque 句柄标识具体本地装配记录，LastActorInfoWrite 是本次发布证据；Refresh 保留同一本地记录。改了会坏什么：仅凭历史 Receipt 或安装缓存开放 Ready 会让已关闭、已转移或未发布的资源被消费者当成可用；清理只比较 ASC/Pawn/Binding 而不匹配原 opaque 记录，也无法区分同 Context 重装的先后记录。

本轮只创建本地记录和通知框架，没有接管 PawnData、Health、Input 或 Movement 的实际资源。新的本地 Ready 查询与身份注册回放只认本地真实认证历史及 ASC 当前发布资格；旧 Getter / 旧 RegisterAndCall 此轮保持原状，禁止宣称它们已使用该门禁。

支持函数为 `GetCurrentLocalAbilitySystemResource()`、`IsLocalAbilitySystemResourceInstalled(Resource)`、`IsLocalAbilitySystemResourceReady(Resource)`、`RegisterLocalAbilitySystemNoticeAndCall(Delegate)`、`UnregisterLocalAbilitySystemNotice(Handle)`，不是第五生命周期阶段。当前槽快照只复制 opaque 句柄，不依赖 Ready/ASC 有效性，空槽返回空；副本不授 Installed/Ready 或发布权限。立即回放保留原 Resource/PublishedContext 副本；返回注册句柄只证明注册事实，回调后失效不借新 Context 重新授权。实际事件保存在 Extension 私有成员，外部只能注册/移除，不能 Broadcast。

2026-10-02 统筹同租约审查补齐 Installed 接缝：仅检查 Extension 生命周期、原 handle 等于当前槽、bInstalled、原 weak ASC/Pawn，以及现有 `CheckAvatarBindingIdentity` 与实际 Avatar；不保存新状态、不要求 Ready、不签许可。Binding 查询已经验证 ASC 当前记录和完整实际 ActorInfo，Refresh 更新 LastWrite 时同 Binding 的安装资格可继续成立。Ready 复用 Installed，再要求曾真实 Ready 和精确 PublishedContext 的当前发布资格。Host 可用 Installed 验证装配/Publish 前置；Withdraw 后的 Cancel/Cue 查询仍只能检查原资源作用域，不能改用 Installed/Ready。

Extension 生命周期与 ASC 生命周期分开：原 Extension 仍有效但 ASC 已失效时，Withdraw/本地 Released 可执行；Extension 已 BeginDestroy、FinishDestroy 或 weak 不可用时，Withdraw 只清原本地记录，Released 只退休原通知义务，返回 Failed/LifecycleClosed 和实际 bLocalChanged，不广播、不伪称观察者已获通知。广播回调后也重检 Extension 标志。旧 EndPlay 不改，生产 EndPlay 的精确接线仍是下一阶段停止点。

## 5. 后续 Host 顺序与生产门禁

```text
释放：捕获原 Context / 作用域 -> Withdraw
  -> TryCancelAvatarBindingAbilities(原 Context, 原筛选, 原纯作用域查询)
  -> 重检原归属后 ClearAbilityInput
  -> TryRemoveAvatarBindingGameplayCues(原 Context, 原纯作用域查询)
  -> ASC Clear -> Host 公布解绑 / 撤原订阅
  -> ASC Publish Released 事件桥接本地 Released

安装：ASC Try 提交 -> Install 完成 -> Host 公布 Avatar / 订阅
  -> Publish(查询安装与 Host 公布状态，不要求 Ready)
  -> 真实 Dispatching -> Ready -> 后续 GA 通知
```

为什么这样写：Cue 在 Clear 前保留旧 Avatar Removed 路由；关闭 Ready 不撤销原清理作用域。改了会坏什么：查询 Ready 或已撤缓存会让 Cancel / Cue 拒绝自己的合法清理；Publish 查询 Ready 会在 Pending 阶段形成循环前置。

正常释放前置仍保留 Owner、原 ActorInfo 分配以及已撤 Extension 缓存。普通通知时 Busy 已释放，原 R0 两例必须能在回调里当场完整接续。任一步原归属失效停止后续 ASC 操作，只清自己的本地资源，不回滚、不读取后继授权。Cancel / Cue 同步成功不保证全部能力或表现结束。

未迁移的旧无参数生产消费者仍需分模块改为身份通知，随后才能激活新生产路径。旧 R0 观察回调和严格断言保持；本接口阶段没有关闭 R0。

## 6. 实际静态证据与剩余边界

当前状态：L1-R1 已重新有限静态接受并进入 Gate50 实际完整编译；L1-Snapshot 后续经统筹 Gate51 完整编译，新 DLL 已链接。两份生产 Extension 源码继续冻结，Host/现有生命周期尚未接线。§10 的 L1-T1 一个新测试 cpp 与本记录已实现并有限静态检查通过，交回后两文件冻结；新叶未编译、未运行，统筹另安排。本地动态未验，原 R0 严格红仍未关闭。首次根静态验收撤回/纠正历史见 §7；Gate50/Snapshot 历史见 §9。本会话没有执行构建、自动化、UE、Git 或资产操作。

相对最初旧源码，完整差异仍为纯新增：h 四个 `K4-Character-L1` 标记块（include 4 行、native types 86 行、native APIs 26 行、private resources 7 行，共 123 行）；cpp 原 400 行完整保留，仅尾部追加 418 行。删除四个头标记块和 cpp 追加片段后，UTF-8 字节 SHA256 精确恢复 §1 两个写前哈希，所以所有旧函数、声明、注释和旧断言逐字保持。R1 的历史差异仅为 §7 指定的 h 3 行/cpp 5 行删除；本次 Snapshot 相对其基线只新增 h 2 行/cpp 7 行，无其它源码差异。

| 冻结源码 | Bytes | SHA256 |
| --- | ---: | --- |
| Extension.h | 13410 | `B500B53BD45B810B6CEF320F75334F06AD8E94C14BE23207CAE4FDF177994563` |
| Extension.cpp | 33185 | `46C3CDBC464B379F37EFBFD62AFECD77736F3FB05C0B9A5ED2368E34E41EF267` |

本记录的最终 SHA256 在交回消息给出，不在自身保存自指哈希。

Snapshot 交回时的有限静态核对（历史，L1-T1 新测试调用见 §10）：

- 本次对 Snapshot 基线核对 256 源：仅本会话两个 Extension 源码变化，其余 254 保持；9 个保护项逐项哈希保持。R1 当时对最初 L1 基线核对另有独立授权 Input D13 两测试源变化，是其历史证据，不混用两份基线。
- 四阶段定义各一处；Source/GGYGO 排除本两源后的新 API/查询/注册检索为零调用。
- Ready 中实际 Dispatching 调用先于唯一历史 Receipt 读取；Refresh 必须 bEverReady 且原 Binding 相同，原 Context 在每次广播返回后复核。
- Installed 只调用既有 Binding 权威查询和实际 Avatar 校验，没有 bEverReady、PublishedContext 或发布资格要求；Ready 在 Installed 之上增加自己的发布门禁。
- 新片段无 Init/Clear/Refresh/Cancel/Cue/Input 原生写调用，无事务/清理 Try 调用，无序号分配或 Busy 门闩。
- Withdraw 和 Released 只操作原 opaque 记录；Released 消费先于广播，已关闭 Extension 在广播前明确 Failed，回调后再次检查关闭标志；不以 ASC 失效阻止本地释放。
- R1 已精确删除额外历史拒绝：同 Context 在 Withdraw 后重新 Install 不再被历史状态拒绝。历史 Released 仍保留原 opaque 句柄，其清理不改写后继记录；原通知消费和回调返回门禁逐字保持。同 Context 重装及原发布凭据接续仍未动态验证，不宣称通过。
- 当前槽查询精确为游戏线程检查和副本返回，不读 Ready/ASC 生命周期，不调用旧 Getter/Installed/Ready，不修改字段或创建记录；本次逆向恢复两源码 Snapshot 写前哈希通过。
- 三文件严格 UTF-8、无 BOM、仅 LF、末尾 LF、无行尾空白；本记录 5 个 Markdown 链接目标存在。

本轮 Snapshot 的以上证据是文本、调用顺序和分支静态核对，不是本次新函数 C++ 编译或动态契约通过。此前 R1 的 Gate50 编译事实单独保留；生产接线、旧 Getter 门禁、消费者迁移、EndPlay 精确清理接线、原 R0、同 Context/凭据续接、Refresh 动态、失效 ASC/Extension 动态及网络验收均未完成。

Obsidian 同步归统筹：Gate50 后已有 8 份 Character/相邻/global 图文根同步并静态核对、原生 UI 未验；本轮新增 Snapshot 尚待统筹在源码冻结后同步。本会话仍无笔记写权，本局部记录不能替代图文或 UI 验收。

## 7. L1-R1：删除未确认撤出限制的原子预检

2026-10-02：统筹确认源码确有额外撤出限制，撤回此前静态验收，并重新授权同三文件纠正。原 L1 交回历史保留：h `2F5D985AA338B8D39C5A187384201C06FD402B10004F5EB636DCC3C22C519800`（13434 Bytes）；cpp `7DC5CC4A1B397D0504016BEC33018C88B540DB53F9694D91CFF079C41C4C5073`（33241 Bytes）；记录 `2393F9907680EA9AEF621222FE36BD50C620C5F5DCB2D35B381ACCDCFF89B3F7`（13864 Bytes）。本次写前读取与上述三哈希一致。

唯一目标：撤销实现阶段擅自加入的历史拒绝政策，恢复仅由当前槽和 ASC 现有 Context 判定安装；不新增替代状态、序号或政策。

| 精确文件 | 仅允许的源码差异 |
| --- | --- |
| `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h` | 删除 `ResourceAlreadyWithdrawn` 枚举项、`LastWithdrawnLocalAbilitySystemIdentity` 字段及其注释，共 3 行 |
| `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp` | 删除 Install 该字段的 4 行拒绝分支、Withdraw 1 行赋值，共 5 行 |
| 本既有记录 | 更新受影响合同、证据、行数、哈希和未验边界；消费者预检仅记录，不实施 |

```text
本节精确预检 -> 仅删除上述 8 行源码
  -> 逆向插回 8 行，必须恢复本次写前 h/cpp 哈希
  -> 删除全部 L1 新增块，仍必须恢复最初两旧源码哈希
  -> 更新本记录当前合同/证据 -> 三哈希交回冻结
```

为什么这样写：原 opaque 句柄已经能区分被撤出的记录与后继记录；历史身份拒绝是额外政策，不能替代发布作用域和动态验收。改了会坏什么：继续保留该限制会拒绝同一有效 Context 的合法本地重新装配；只改文档则会掩盖实际源码分支。

断言：

- 没有退役字段、对应枚举项、Install 拒绝和 Withdraw 赋值，也没有替代状态。
- 同一 Context 在 Withdraw 后仍通过原 ASC/生命周期/当前槽校验时，不再被历史状态拒绝；该结论仅是控制流静态事实。
- 原 Resource、通知消费、精确撤出、Installed/Ready/Refresh/生命周期门禁及旧函数保持原实现。
- 历史 Released 仍拿原 opaque 句柄，不能改写后继记录；同 Context 重新 Install 与发布凭据接续的动态行为未验证。

非目标：纯当前槽快照查询、本地新测试、消费者、Host、旧 Getter/RegisterAndCall、Initialize/Uninitialize、EndPlay、Hero、Health、CMC、ASC、资产、网络和其它文件；无 Build/UE/Git/Obsidian/全局文档/子代理权限。Input D13 h/cpp 的独立授权变化分别记录，不归因于本会话越界。

停止点：完成这 8 行删除、记录一致性及静态交回后立即冻结。第四文件、替代状态、接口新增或动态验收需求停止并另授租约。

R1 当时的实施/静态结果：指定 8 行已删除，源码中两个退役名称均为零；没有新增源码。逆向插回删除行精确恢复本节两个写前源码哈希，证明其余接口和实现保持；再逆向删除全部 L1 新增块，精确恢复 §1 最初旧源码哈希。当时 h 308 行、cpp 811 行，两源码交回哈希保留在 §9 的 Snapshot 写前基线；9 保护项保持。R1 交回时本会话没有编译、UE、Git、测试或资产操作；后续统筹 Gate50 编译通过见 §9。同 Context 重装及发布凭据续接仍待验证。

## 8. 下一消费者原子：只读预检，未授权实施

前置：Extension 最终合同和必要纯快照接缝先冻结。下表仅指定源文件，局部图文另阶段；不并行让新旧通知写同一消费者状态。

| 唯一负责人 | 最多 4 个精确文件 | 唯一目标与停止点 |
| --- | --- | --- |
| Character 长期组长 | `F:/ue_project/GGYGO/Source/GGYGO/Character/GGYGOCharacterBase.h`、同目录 `GGYGOCharacterBase.cpp`；`F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHealthComponent.h`、同目录 `GGYGOHealthComponent.cpp` | 准备身份通知到 Health 的桥接和原 opaque 记录/精确 HealthSet 委托清理；不改死亡业务或旧解绑入口。身份适配冻结后停止，生产启用另阶段。 |
| Movement 长期组长 | `F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h`、同目录 `GGYGOCharacterMovementComponent.cpp` | 准备身份订阅与 ASC 缓存，迟到 Released 不能清后继，Refresh 不重置原运动资源；不改 FAILED/Profile/Input 规则。适配冻结后停止。 |
| Input 长期组长 | `F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.h`、同目录 `GGYGOHeroComponent.cpp` | 准备身份订阅和原输入/重试资源释放；不再建 Session/代际，不改 Camera 或 D13 策略。适配冻结后停止。 |

所有消费者清理必须匹配原 opaque 句柄（`HasSameResource`），身份值用于诊断和绑定查询；不只比较 ASC 指针或同 Context 的身份值。旧 Get/RegisterAndCall、Initialize/Uninitialize、Controller/死亡/EndPlay 生产切换由统筹另排互斥步骤，原 R0 无参数观察者与严格断言不改。

本节预检时必要纯接缝为未授权候选，现由 §9 的独立 Snapshot 租约实现且经统筹 Gate51 编译：`FGGYGOPawnASCResourceHandle GetCurrentLocalAbilitySystemResource() const` 只复制当前本地槽，供 Host 发现尚未 Ready 的跨 ASC 安装；ASC 失效的槽也可见。`IsInstalled(Snapshot)` 再验证权威当前性。HasResource 仅证明历史存在，Installed 需要先持有句柄，不能替代发现入口。快照不签许可、不创建记录、不存新状态；Publish 作用域使用本次捕获的原句柄，不能反复读取后继快照替换授权。Host/消费者仍未迁移，本函数动态验收尚未运行。

旧调用迁移边界：Input 的 `Input/Tests/GGYGOInputTestTypes.cpp` 仍直接 `InitializeAbilitySystem(SelfASC, Pawn)` / Uninitialize；该测试 h/cpp 的 D13 独立变更并不等于本地四阶段迁移。Combatants 的 `Combatants/Tests/GGYGOCombatantBindingLifecycleTest.cpp` 仍有直接旧初始化/卸载；Health 旧直接初始化和 `GGYGOCombatantDeathProjectionTest.cpp` 夹具同样另排。各所属组长须显式迁移并保留原断言，不默默让旧 ActorInfo 写链冒充新架构验收。原 R0 两源继续冻结；生产 `GGYGOCombatantState.cpp` 及 CharacterBase 死亡解绑也在后续统一入口切换范围，均不在本消费者预检授权内。

## 9. L1-Snapshot：纯当前槽快照原子预检

2026-10-02 15:25：统筹授权原三文件，基线为 [CharacterLocalSnapshot_LeaseBefore.json](../../../Saved/ValidationRecords/CharacterLocalSnapshot_LeaseBefore.json)。写前三哈希逐项匹配：h `057F7C56F0FC40E624041E6F8EE9AA3616BA1815AE40AF41D66D22CBCF6D849E`（13238 Bytes）、cpp `C188DFE10FDDAC197421B170A6CCB6B18B3D3734D79284C84EB0FEAF23DBD2AA`（33014 Bytes）、本记录 `12ABC2E47B78026047765CFB37ED1E45025A7B095927AF0D2B7DEE2449C3F35B`（20659 Bytes）。

前置实际证据来自统筹：L1-R1 已重新有限静态接受，Gate50 完整 Editor Succeeded／8 actions／18.23 秒／exit0 并链接新 DLL；全量 82 Success／2 Fail，原 83 路径状态保持。新增 Input 原生出生首按在尚未 W 时失败，Input 正只读定位；本地四阶段没有调用，所以没有本地动态或 R0 通过证明。两次 UE 退出，256 源和 9 保护保持。统筹已同步 8 份 Character/相邻/global Obsidian 并静态核对，原生 UI 未验。本会话没有执行这些构建、运行或笔记操作，不把 Gate50 扩展为本次新快照接口已编译。

唯一目标及精确文件：

| 文件 | 本原子差异 |
| --- | --- |
| `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h` | 仅声明 `FGGYGOPawnASCResourceHandle GetCurrentLocalAbilitySystemResource() const` 及其纯查询注释 |
| `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp` | 仅定义该函数：游戏线程检查后复制 `LocalAbilitySystemResource` |
| 本既有记录 | 登记本预检、纯查询合同、实际差异/hash/证据/未验边界 |

```text
GetCurrentLocalAbilitySystemResource():
  check 游戏线程
  return 当前 opaque 槽的副本

Host 后续使用：
  原 Snapshot = 发现当前槽            // 可未 Ready，可 ASC 失效
  检查原身份 / IsInstalled(原 Snapshot)
  Publish 作用域始终核对捕获的原句柄  // 不读取后继快照换授权
```

为什么这样写：Host 尚未持有新 Pawn 的资源句柄时，不能用需要句柄的 Installed 查询发现跨 ASC 装配；Ready Getter 也会隐藏尚未 Ready 的槽。改了会坏什么：按 Ready 或 ASC 有效性筛快照会隐藏待清理记录；重复读当前槽收养后继会让旧作用域继续执行。

断言：唯一函数体只有游戏线程检查和返回槽副本；不检查 Ready/IsValid ASC、不调用旧 Getter/资格接口、不写字段/发号/认领、不创建记录或外调。空槽返回空是查询结果，不表示业务成功；非空副本只证明所观察的历史资源，Installed/Ready/发布及原生权限必须另验。逆向删除本次新增声明/定义须恢复写前三份中的两个源码哈希，再删所有 L1 新块仍恢复最初旧函数哈希。

非目标：其它四阶段、字段、状态、策略、旧函数、Host/消费者、测试、资产、网络、Build/UE/Git/Obsidian/global 文档及子代理；不继续消费者。停止点：单函数和记录静态交回后立即冻结，编译/动态与旧入口迁移另授权。

实际实施/静态结果：头新增 2 行声明/注释，cpp 在 L1 尾部新增 7 行单函数；只有 `check(IsInGameThread())` 和 `return LocalAbilitySystemResource` 两条语句。逆向删除这两段精确恢复本节写前两源码哈希；再删除全部 L1 新增块仍精确恢复最初旧源码。没有其它接口、字段、四阶段或旧函数变化。当前 h 310 行/cpp 818 行，最终源码哈希见 §6；本次基线 256 源只有本两源变化，254 源和 9 保护保持。新函数无生产/测试调用，编译和空槽/未 Ready/失效 ASC/后继快照动态均未运行；原 R0 与同 Context/凭据续接边界保持开放。三文件交回即冻结，不继续消费者。

## 10. L1-T1：真实本地生命周期单叶预检

2026-10-02：统筹 Gate51 交回后明确授权两文件，基线 [CharacterLocalLifecycleTest_LeaseBefore.json](../../../Saved/ValidationRecords/CharacterLocalLifecycleTest_LeaseBefore.json)。写前新 cpp 不存在，本记录 SHA256 为 `4E4C3D618F5CBD84B1CB32022EFE5A9EF80FA25497EC97D6FC09C262E22D108D`（25342 Bytes），与租约一致；组长直接执行，无代理。Gate51 的实际前置由统筹和保存报告提供：统一 Editor Succeeded／7 actions／22.60 秒／exit0、新 DLL；全量 82 Success／2 Fail，原 84 路径状态保持，256 源／9 保护保持且 UE 已退出。这证明 Snapshot 已编译，不证明本新叶或 R0 已通过。

唯一目标：一个真实事务／真实发布驱动的本地生命周期叶，区分当前槽、Installed 和 Ready，验证同 Context 的不同 opaque 重装、旧资源清理和精确订阅归还。精确两文件及唯一所有者：

| 文件 | Character 组长本原子责任 |
| --- | --- |
| `Source/GGYGO/Character/Tests/GGYGOPawnExtensionLocalResourcesTest.cpp` | 新建唯一 `GGYGO.Character.PawnExtension.LocalResources.LifecycleAndSameContextReinstall` 叶及其 cpp 内轻量 World／订阅清理夹具，无 UCLASS |
| 本既有记录 | 先保存本预检，再记录实际差异、静态证据、哈希和未验边界 |

只读依赖：冻结的 Extension、ASC、BindingTypes 和原 ActorInfo 事务／Combatants 轻量 World 测试；不包含旧 cpp 或修改其共享夹具。ASC 独占 ActorInfo、Binding 和 Receipt；Extension 独占本地记录；本叶只保存原句柄、真实事务结果、精确委托 token 与观察计数，均不形成新权威。与 Movement CMC 准备阶段互斥，不消费其新接口。

```text
登记本预检
  -> 真 Game World + Engine WorldContext，真实注册 ASC
  -> 普通 Pawn 动态添加唯一 Extension 并真实 RegisterComponent
  -> TryBootstrap(Init, 原 Owner/Pawn, 纯原作用域查询) 生成 C/R
  -> Install H1：槽可见，Installed=true，Ready=false
  -> Pending R 的 NotifyReady 明确拒绝；早注册无回放
  -> Publish(R, 捕获原 H1 的 Installed 查询)
       真 ASC Dispatching 回调 -> NotifyReady(H1, 派发 Receipt)
       精确重复无改变/重复通知 -> 晚注册精确回放 H1/C
  -> 外层 Publish 成功返回 -> Withdraw H1 -> 同 C Install H2
       H1/H2 身份相同、opaque 不同；H2 Installed 但未 Ready
       新注册无回放；此时历史 R 明确 PublicationNotDispatching
  -> Released(H1)：原通知先消费；旧回调仅 Withdraw 原 H1
       外层 Stale/CallbackInvalidated + 历史 bLocalChanged=true
       重复 Withdraw/Released 幂等，H2 不变
  -> 按原 token 归还订阅 -> 原 H1/H2 本地清理
  -> 原 C 的真实 Clear/PreserveOwner -> 真实 Publish -> 原 World 收尾
```

为什么这样写：安装和真实 Ready 分开，历史 Receipt 不能冒充正在派发的权限；同 Context 的两次装配靠 opaque 记录区分，旧观察回调只处理原资源。改了会坏什么：Publish 查询 Ready 会形成循环前置，清理改读当前槽会清掉 H2，模拟 Receipt／手工 Broadcast 或使用 ExpectedErrors 会掩盖真实认证与生命周期缺陷。

每个本地步骤及回调后检查原 ASC 的 Owner／Avatar／Context／ActorInfo 分配保持；真实 Bootstrap、Clear 是唯一允许变化的事务。所有结果核对 Outcome、Reason、原 Resource 和 bLocalChanged，通知核对原 opaque、Kind、PublishedContext、精确次数；主序列失败立即停，已获得的原资源和 token 仍由守卫同步清理。守卫先于捕获对象析构，WorldContext 保留至 World 销毁之后；清理只用已保存原 Context，意外失效明确诊断，不读取新 Context 继续授权。

不定义的边界：R 仍真实 Dispatching 时若撤 H1／同 C 装 H2，当前认证没有 Receipt 到某个本地 opaque 的绑定，`NotifyReady(H2,R)` 存在接受路径。本叶把 H2 安排在外层 Publish 返回后，只断言派发外历史凭据被拒绝；不据此断言活跃凭据能否授权 H2，也不加序号、黑名单或新政策。该窗口若成为验收必需项，先交统筹冻结合同。

非目标：BeginPlay／真实 GI／原 R0／Refresh／死亡／Host 生产／网络；生产 Extension、ASC、Host、Health、Hero、CMC、所有原测试及资产不写。无 Build／UE／Git／Obsidian／全局入口权限。停止点：仅本两文件实现并有限静态交回后立即冻结；需要第三文件、生产修复、新政策或编译/运行时停止并交回统筹。

### 10.1 实际实施与有限静态证据

唯一新叶已写入[本地生命周期测试 cpp](../../../Source/GGYGO/Character/Tests/GGYGOPawnExtensionLocalResourcesTest.cpp)：471 行／28797 Bytes，SHA256 `154A32998F12F7A025B628C3FEF886AD8E8A673A9E83DB2F1878E63BC62586C3`。本记录当前状态同步 Gate51 编译事实，原 Snapshot 交回统计明确作为历史，追加本租约预检和实施证据；未改原生产合同、历史失败或其它局部记录。本记录最终哈希在交回消息给出，不保存自指哈希。

实际代码顺序和断言：

- 一个 cpp 内原生轻量夹具创建真实 World／Owner／Pawn，实际注册 ASC 和唯一 Extension；无新 UCLASS、能力探针、GI、Host或帧调度器。注册、权威、ActorInfo 分配、初始空 Context／槽和未 BeginPlay 均为严格前置。
- `TryBootstrapAvatarActorInfoTransaction` 只调用一次，Context 只从真实 bCommitted 结果复制，Receipt 由实际 Try 输出；H1/H2 只从实际 Install 结果保存。精确 H1 的 ASC／Pawn／Binding 身份、同 Context 的 H1/H2 同身份不同 opaque 均有断言。
- 安装 H1/重复安装未 Ready，早注册无回放，Pending Receipt 的 NotifyReady 明确 Rejected/PublicationNotDispatching。真实 ASC 订阅桥接 Dispatching Receipt；Ready 成功且改变，派发内精确重复成功但不改变、不重复通知，晚注册精确回放 H1/C 一次，Consumed 后 H1 仍 Ready。
- 外层 Init Publish 返回后才 Withdraw H1／同 C Install H2；H2 Installed、未 Ready，新注册不回放，H1 历史仍存在但 Installed/Ready 始终关闭。派发外历史 Receipt 通知 H2 明确拒绝；没有活跃同 Receipt 的政策断言或替代黑名单。
- 原 Released 的身份通知携 H1和严格空 PublishedContext，早观察回调先消费自身一次标记，再重复 Withdraw 通知携带的原 H1；每次回调前后核对 H2。Released 外层精确 Stale/CallbackInvalidated、历史改变为 true；重复 Withdraw/Released 成功且无改变，三个观察者均仅获一次原 Released，Ready次数分别 1/1/0。
- 主序列每个相关外调后立即检查回调失败标记并停；槽、Installed、Ready、原 ASC cached/native Owner/Avatar、完整 Context、原 ActorInfo 分配、native Busy关闭及旧 cache仍空均有实际断言。没有 ExpectedErrors、断言降级、手工 Broadcast、legacy 原生 Init/Clear/Refresh调用或私有资源/Proof赋值。
- 所有借用的观察计数、句柄、Context及检查 lambda均先于清理守卫声明。精确原 token移除后再释放 H2，原三个观察者计数保持；失败守卫先移除原订阅，再按保存的 H2/H1顺序做本地清理，避免旧未消费义务误判仍有后继，不读取当前槽收养资源。
- 收尾使用保存的原 C执行真实 `Clear/PreserveOwner`（唯一 TryExecute），失效则明确断言失败且不收养其它 Context；真实 Clear Publish后复核原 Owner／ActorInfo分配、空 Avatar、实际 Clear Context和 Busy关闭，原 ASC观察次数保持一次。World最后销毁，Engine WorldContext随后销毁；只清本测试新建 package的 dirty flag。

有限静态结果：单叶计数 1；剔除注释/字符串后的括号匹配通过；禁止调用/赋值检索为零；守卫与捕获顺序、H2重装晚于外层 Init Publish的文本顺序通过。实际调用数为 Bootstrap 1、TryExecute 1、Publish 2、Install 3、NotifyReady 4、NotifyReleased 4、精确本地注册 3；这是静态计数，不能替代运行次数和动态通过。

写前保存的 256 源码与结束快照比较：新增仅本 cpp，当前 257 源；旧文件无删除，254 个原源码哈希保持，另两份已登记的 Movement CMC h/cpp发生该组独立租约变化，不归因于 Character 本叶。Extension.h/cpp仍分别为 §6 的 `B500B53B…`／`46C3CDBC…`，ASC/Binding、Host和所有原测试保持；9 个保护项逐项哈希保持。两份授权文件严格 UTF-8、无 BOM、仅 LF、末尾 LF、无行尾空白；本记录新增链接目标实际存在。

架构核对：新增依赖仅测试读取既有 Extension/ASC及已声明 Engine/Core模块；不改 Build.cs或共享头，不产生循环依赖。夹具只保存本次获得的原资源/订阅/结果，没有 Binding/Ready的第二权威或执行器；失败路径与正常路径共用精确原资源清理，旧生产接口和资产接线保持。

当前仅称“有限静态检查通过，编译待统筹验证”。新叶编译、动态成功/失败、World注册诊断和严格清理都未运行。BeginPlay／Refresh／失效 ASC/Extension／活跃同 Receipt授权／原 R0／Host与消费者生产切换／死亡／网络继续开放；不能用 Gate51或本静态检查关闭它们。Obsidian及全局入口仍由统筹按阶段维护，本会话零写入。两文件交回后立即冻结，不继续消费者适配或测试扩展。

## 11. Host 请求接口定义：三文件预检

2026-10-03：统筹验收完整候选 `01a0fff7-0ca1-7ca0-90e4-0ea15f32bc42` 后明确授权本步骤；基线为 [CharacterHostInterfaceDefinition_LeaseBefore.json](../../../Saved/ValidationRecords/CharacterHostInterfaceDefinition_LeaseBefore.json)，租约已登记于排程和 Ledger。唯一写入者为 Character 长期会话 `01a0e5b5-36b6-7c81-b10f-f10d5758423d`，组长直接执行。本节在创建源码前登记。

写前核对：两新源均不存在；本记录为 `721526EE125E8D2C9CECB944EF79717933DBA7F26AC00941D862F6DB4B7BB127`／35197 Bytes。六份只读依赖逐项匹配基线：Extension h/cpp、ASC 头、BindingTypes、原 AbilitySourceInterface h/cpp；没有共享上游变化。Input 独占 Hero h/cpp及交互合同，双方文件不重叠。

唯一目标：冻结 native 请求、请求栈上的真实步骤历史和无状态纯虚 UInterface；本步骤只定义端口，后续实现由新租约承担。

| 精确文件 | 本步骤产出 |
| --- | --- |
| `Source/GGYGO/Character/Interfaces/GGYGOAvatarBindingHostInterface.h` | 原操作／原因／端点／Context／opaque H 请求，真实步骤载荷及默认拒绝结果，纯虚 `RequestAvatarBinding` |
| `Source/GGYGO/Character/Interfaces/GGYGOAvatarBindingHostInterface.cpp` | 生成代码和接口包装构造函数 |
| 本既有记录 | 预检、批准合同、有限静态证据及待验边界 |

职责及依赖：Character 维护端口，CombatantState 后续实现，Slot／BossState 继承；ASC 独占 ActorInfo／Binding／真实发布凭据，Host 独占选择和发布编排，Extension 独占本地资源及通知义务，消费者各自清理自己的资源。头文件复用 Extension 已有值类型，不新增另一套 Binding／Ready 状态。Extension 头不反向包含本端口，后续 cpp 路由依赖端口，不引入具体 Host 或循环依赖。

```text
登记本预检 → 原样写入冻结候选 → 必要有限静态检查 → 交回并冻结
  → 统筹另授 Host 实现／Extension 路由／消费者生产接线租约
  → 生产批次全部冻结后，统筹安排编译和必要冒烟

请求调用方（后续实现）：
  原 Host Release(原端点、原 Context、原 H) → 核对 → 新 Host Initialize(空 H)
  新绑定失败 → 只清本次仍归自身的部分装配 → 保持未绑定，不自动恢复旧 Host
```

已批准的端口合同：

- Initialize 必须携空 `ExpectedResource` 和明确目标 Pawn；`ExpectedContext` 为原 ASC 值，只有真实从未提交的 Bootstrap 准入允许空 Context。Host 验证原端点及选择权限；目标已有其它 Host 资源时明确拒绝，不隐式移交。
- Release／Refresh 携精确原 H及原 Context。Release 可以按历史 H完成必要本地清理，Context 失效后停止原生操作；Refresh 要求原资源仍属于当前装配，不能把从未 Ready 的安装升级。
- `Steps` 按本请求实际步骤返回顺序追加，真实拒绝／Busy／失败也保留。ASC 步骤仅填 `ASCResult`，本地步骤仅填 `LocalResult`，实际 void `ClearAbilityInput` 返回仅填 `InputClear`（原 Context／H）；未执行的步骤不出现，未使用的 optional 为空。嵌套请求分别保存自己的栈结果。
- 默认请求为 Invalid／空端点／空 Context／空 H；默认结果为 Rejected／InvalidRequest／空历史。现有 `bCommitted`、`bLocalChanged` 只保留在真实步骤结果中，不新增顶层当前绑定或 Ready 标记。失败后实际 Clear 等清理追加历史，不能覆盖原提交事实或把原失败改为成功。
- Succeeded 只描述本请求完成或经验证的幂等结果。正常接续替换原作用域时返回 Stale／CallerInvalidated 并保留历史；Busy 只来自真实未完成原生窗口，不因观察 Ready／Released而拒绝，不排队。普通回调可立即完成完整新绑定，原 R0 DifferentPawn／SamePawn 行为合同保留。
- 调用同步限定游戏线程；实现方入口复制请求，每次外调后复核原 Context／H，失败清理保留合法回调后继。端口自身不持有状态、注册句柄、计时器、资源或执行器；历史结果不能充当当前权限。

为什么这样写：请求携原身份，栈历史保留失败前的实际提交及后续清理结果，既能定位失败也不会产生第二个权威。改了会坏什么：改读当前 H会收养或清除后继；只保留最后结果会丢失实际提交；把历史持久化为当前权限会与 ASC／Extension 状态竞争。

验收限于与冻结候选一致、默认拒绝／空历史、载荷对应关系、generated 头最后、cpp 仅生成代码及构造、无生产调用，以及六份共享依赖哈希保持。非目标为请求处理、Host／Extension／消费者生产切换、测试新增或迁移、资产、网络、Build／UE／Git／Obsidian／全局文档及子代理。用户本轮要求保留重构功能范围，仅编译和必要冒烟，不新增严格回归矩阵；未运行证据保持可见。需要第四文件、共享上游变化或新政策立即停止；三文件静态交回后冻结。

### 11.1 实物与有限静态交回

已原样落盘冻结候选的两个 C++ 代码块：

| 实物 | 行数／Bytes | SHA256 |
| --- | --- | --- |
| [Host 接口头](../../../Source/GGYGO/Character/Interfaces/GGYGOAvatarBindingHostInterface.h) | 113／2969 | `B658148B2E17CECD2A598FFBE4BE0B7964655833F4283822955ABBED24336316` |
| [Host 接口 cpp](../../../Source/GGYGO/Character/Interfaces/GGYGOAvatarBindingHostInterface.cpp) | 9／294 | `EB22E540948719D8D7EB4432EDD3C2F2CE78052B6D62E2ADCF2E45B56A86E143` |

有限静态检查通过：从租约 JSON 提取两份候选，统一换行及末尾 LF后与实物全文逐字比较一致；native 枚举／结构及纯虚签名、默认 Invalid请求／Rejected结果／空历史、三个 unset optional载荷均保持候选。generated 头是头文件最后一个 include；cpp仅两个 include和包装构造，无请求处理。项目源码检索 `RequestAvatarBinding`／`GGYGOAvatarBindingHostInterface` 仅命中本两文件，没有生产调用、实现或 Extension 头反向包含。

六份共享依赖哈希全部保持。与基线的 257 份旧源比较，255 份保持，仅并行 Input租约的 Hero h/cpp变化；本步骤仅新增上述两源，无删除。按基线同一 `.h/.cpp/.cs` 范围当前共259源，既有 `Source/GGYGO/README.md` 不计为源码新增。三份授权文件严格 UTF-8、无 BOM、仅 LF、末尾 LF且无行尾空白；新增三个 Markdown链接目标均存在。本记录仅追加本原子预检和交回证据，最终哈希随消息交回，不写自指哈希。

架构核对：端口没有持久成员、资源所有权、注册、Tick或执行器；只复用现有 ASC／Extension值类型，未引入具体 Host依赖或第二状态。清理责任及真实发布权限由后续实现遵循 §11合同，本定义没有执行清理或改变生命周期。未修改旧生产代码、既有测试、Build.cs、资产或全局文档。

本步骤只关闭“Host接口定义已落盘并有限静态交回”。UHT／编译／冒烟未运行；Host实现、Extension路由、消费者生产切换及跨Host显式移交仍待后续租约，未声称 R0或整个Host功能完成。按本轮验证政策不新增测试、不运行严格回归；已有严格复现及历史证据保留。Obsidian及全局状态同步由统筹负责，本会话零写入。三文件交回即冻结，等待后续授权。

## 12. Extension 生产请求与 Ready 读取：三文件预检

2026-10-03：统筹已接受并冻结 Host生产路由，随后明确授权本步骤；基线 [CharacterExtensionHostConsumer_LeaseBefore.json](../../../Saved/ValidationRecords/CharacterExtensionHostConsumer_LeaseBefore.json)，唯一写入者仍为 Character长期会话。写前本 h/cpp／记录分别匹配 `B500B53B…`／`46C3CDBC…`／`1ED78F56…`。Host h/cpp实际为 `86F7C6CEA874DB25AD5073EFEF5367DCC4464CB630E1997D883D20D1C4280903`／`10E4FE163FC93616EBBD47D823549AF288F608F8562AC795689644FE9BC54800`，接口定义两源和 BindingTypes保持冻结哈希。本节先登记，再修改源码。

唯一目标和精确范围：

| 文件 | 本步骤唯一差异 |
| --- | --- |
| `Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h` | 保留三 void／Blueprint Getter签名；Getter外置，删除旧 ASC缓存，仅增加本组件生命周期准入位并更新合同 |
| 同目录 `GGYGOPawnExtensionComponent.cpp` | 原入口路由 Host请求；原 H Ready Getter／Initialized回放；关闭后仍处理原本地释放义务；移除旧原生执行和入口广播 |
| 本记录 | 预检、有限静态证据、实物哈希及剩余消费链 |

依赖顺序：已冻结 Host／接口／ASC Avatar事务 → 本步骤 → Health原资源准备 → Base／Hero真实消费接线 → 全部冻结后统筹统一编译和必要冒烟。CMC E1保持冻结；同一新 DLL／新 World启用完整生产链，中途不启动半链。ASC目前独立输入租约可能修改整文件，Avatar事务／Try／Publish及全 Clear原无回调退休合同保持只读；不把输入租约的整文件哈希变化当作本步骤失败。

原端点来源已确认：Host拥有 ASC默认子对象，Request校验组件 `GetOwner()==this`。Release／Refresh从原 H的 ASC组件 Owner捕获 Host，Context只从原资源的 PublishedContext或未发布 InstallationContext读取，不重读可变 ActorInfo Owner／当前 Context。端口仅在 cpp包含，不修改共享签名或本地记录模型。

```text
Initialize：原 Host／ASC／Pawn／Extension + ASC原 Context + 空 H → Host请求
Release：一次捕获原 H + 原记录 Context + 原组件 Owner → Host请求
  端口不可调用 → 仅 Withdraw原 H／退休原 Released义务 → 保留明确失败
Refresh：原 Ready H + 原 PublishedContext → Host请求
Getter／Initialized回放：捕获原 H → 真实 Ready查询 → 原 ASC／一次回放
每次请求返回后：仅诊断；不补广播、不清当前槽或收养后继
```

删除 Extension中的 ActorInfo Init／Clear／Refresh、Cancel、Cue和 ClearAbilityInput执行，Host负责原生编排，ASC仍唯一权威。Initialize不自动释放其它 Host装配或驱逐其它 Extension；跨Host显式旧 Release→核对→新 Init以及失败未绑定语义保持。配置协调保留 DataInitialized中的 PawnData分发，删除 Initialize退化分发。实际 Initialized／Released仍由本地通知接口发出；注册回放只认真实 Ready，Refresh不重复 Initialized。

EndPlay先关闭本组件新 Install／Ready／回放准入，再处理捕获的原 H。生命周期位仅属于组件自身，首次 PreBegin仍可安装，真实下一次原生 BeginPlay才重开；不另发 Binding或 Ready状态。Withdraw保持原 H本地清理，关闭的 Released只消费该历史义务并返回 Failed／LifecycleClosed，不能宣称通知已发送；正常回调接续不因观察期而 Busy或排队。原本地清理成功不把端口失败改为成功，Host已实际受理后的原生失败由它的真实历史描述，不追加替代清理链。

为什么这样写：原 H／Context隔离清理作用域，读取和回放都认 ASC认证的实际 Ready，移除与 Host竞争的执行链。改了会坏什么：改读当前 Context会借用后继权限；旧缓存可把 Installed当 Ready；请求尾部清槽／广播会清掉合法接续。

验收仅必要有限静态：旧原生调用／缓存和入口广播消失，三 void／BP签名及原记录模型保持，Host组件 Owner端点／原 Context／真实 Ready路由成立，关闭准入不阻止原 Withdraw且 Released失败如实记录，PawnData协调及其它非目标函数保持。需要第四文件、共享变化或新清理政策立即停。Host既有 ASC Destroy准入和 Init未commit部分写入清理停点仍开放，本步骤不解决。

非目标为 Health／Base／Hero／CMC／Teams、Host／接口类型／ASC修改、测试／夹具／严格矩阵、UE／Build／Git／资产／Obsidian／全局及子代理。Health／Hero无参数清理仍需后续原 H消费；旧 Input自有 Pawn未实现端口，既有本地专项的“旧 Getter始终空”是准备阶段断言，生产切换后尚未适配／重跑，不能沿用它们为本批通过。三文件有限交回后立即冻结，统筹安排后续租约及门禁。

### 12.1 实际实施与有限静态结果

本步骤已落盘三入口 Host请求路由、真实 Ready Getter及 Initialized回放；旧 ASC缓存字段／构造赋值、旧原生生命周期执行、入口广播与 Initialize退化配置分发已删除。现有三 void签名和 BlueprintPure Getter签名保持；Host接口仅在 cpp包含。资源记录定义整体前移，字段／构造逐字保持，没有新增 Host记录或 Binding发行状态。

| 实物 | 当前行数／Bytes | SHA256 |
| --- | --- | --- |
| [Extension.h](../../../Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h) | 305／13374 | `48AC44EFC8B37F464351D3908B8674A55A1287CE68897E3FC11A13ACAB42640C` |
| [Extension.cpp](../../../Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp) | 958／40474 | `69CFB9F418C45BFED144CF46C6EFE1868AF72D35AE3B171EE99A725C4840B112` |

实际路由和边界：

- Initialize携明确原 Host／ASC／Pawn／Extension、一次原 ASC Context和默认空 H；非法 Pawn／关闭生命周期明确拒绝，ASC／Host／接口无效明确诊断。没有隐式释放其它 Host或驱逐其它 Extension，实际原生步骤仅由 Host返回历史。
- Release只捕获一次原 H，ExpectedASC不匹配直接不执行；使用记录 PublishedContext，尚未发布时使用 InstallationContext；原 H的 ASC组件 Owner是端口来源。Host不能调用时才按保存原 H执行本地 Withdraw／Released并追加真实本地结果，整体保留原端口失败；已实际调用 Host后不另建原生失败清理链。返回尾部仅诊断，不写当前槽或广播。
- Refresh只对真实 Ready的原 H请求，Context来自该记录。失败立即停止旧配置尾部；成功仅从真实 ActorInfoRefresh步骤的 bCommitted历史读取本次提交 Context，再核对原 H仍 Ready且 PublishedContext精确匹配，才推进配置初始化。正常 Refresh不重复 Initialized，不借用嵌套后续写入的 Context。
- Getter捕获原 H后仅通过 `IsLocalAbilitySystemResourceReady`返回其 ASC；Installed和历史提交不返回 ASC。Initialized注册回放捕获原 H／PublishedContext，回调后复核，失效只诊断；实际普通 Initialized／Released广播分别仍唯一位于 NotifyReady／NotifyReleased。
- EndPlay准入位先关闭，Install／Ready／注册回放拒绝新准入；原 Withdraw仍完整保留。关闭的 NotifyReleased只消费原历史通知义务，返回 Failed／LifecycleClosed和真实 bLocalChanged，不广播。原生下一次 BeginPlay入口才重开。所有历史结果／Host是否实际被调用／配置 Context均在请求栈上，没有持久请求历史、忙锁、队列或调度器。

有限静态检查通过：三 void声明逐字保持；删除的原生调用（Init／SetAvatar／ClearActorInfo／Refresh／Cancel／RemoveAllCues／Clear输入）计数0；旧缓存字段／赋值计数0；可变 ActorInfo Owner读取0；仅 Initialize有一次 ASC当前 Context读取。FLocalResource字段及构造逐字保持，注释／字符串剔除后的括号匹配通过。Host h/cpp、接口定义 h/cpp、BindingTypes五份共享哈希保持；没有以并行 ASC输入整文件变化冒充本步骤修改。

与写前内存文本逐字核对15个非目标函数保持：GetLifetimeReplicatedProps、OnRegister、SetPawnData、OnRep_PawnData、HandlePlayerStateReplicated、SetupPlayerInputComponent、ApplyPawnDataToConsumers、CheckDefaultInitialization、CanChangeInitState、OnActorInitStateChanged、Withdraw、Installed查询、精确本地Unregister、Snapshot和Owns查询。DataInitialized配置调用仍保留，旧入口没有第二次分发。三授权文件严格 UTF-8、无 BOM、仅 LF、末尾 LF且无行尾空白；新增链接实际存在，本记录既有内容保持，最终哈希随交回消息提供。

架构核对：新增依赖为 cpp读取无状态 Host端口，无具体 CombatantState头或反向头包含；ASC／Host／Extension权威分工保持。唯一新增持久字段只描述 Extension自身生命周期准入，不发行资源身份／Ready或复制新状态；原本地资源及通知消费模型保持，原清理路径按保存 H执行，正常观察回调可立即接续。

当前只关闭“Extension生产请求路由与真实Ready读取已实现并有限静态交回”。UHT／编译／冒烟未运行；Health／Base／Hero消费链、旧 Input夹具及原准备专项尚未适配。本阶段不能证明原 R0、Host两个共享ASC清理停点、完整生产生命周期或资产／网络通过；同 Receipt活跃期授权后继的未决政策保持，不加黑名单或断言。统筹继续后续租约并在完整源码链冻结后统一编译和必要冒烟，本步骤不新增测试、不严格回归。Obsidian及全局入口由统筹维护，本会话没有写入。三文件交回后立即冻结。

## 13. Health 唯一原资源机制：三文件预检

2026-10-03：统筹接受本步骤完整预检及三个 native bool签名，明确授权 Health h/cpp与本记录；基线 [CharacterHealthOriginalResource_LeaseBefore.json](../../../Saved/ValidationRecords/CharacterHealthOriginalResource_LeaseBefore.json)。写前三文件分别匹配 `4D6CAD72C4162D6484FD9ACD5BE30F539517049D6CF673D303D23B349B365D02`、`D2B319919DABFF115C4A91D95477DD87FE1CFAE453A57F8B38A3CB6FACE106BB`、`1DBB58305825DCF37F4834B768B1B3295843427B914673C614E23E1FFE8B953F`。组长直接执行，本节先于源码实施登记。

| 精确文件 | 本步骤唯一目标 |
| --- | --- |
| `Source/GGYGO/Character/Components/GGYGOHealthComponent.h` | 三 native入口、原资源处理器参数和生命周期清理；删除旧 ASC／Set缓存 |
| 同目录 `GGYGOHealthComponent.cpp` | 唯一实际安装／五 token精确归还／原作用域复核，两个旧 BP入口立即收口 |
| 本记录 | 预检、有限静态证据、真实哈希及 Base后继边界 |

冻结 native接口（无 UFUNCTION）：`bool InitializeWithLocalAbilitySystemResource(UGGYGOPawnExtensionComponent*, const FGGYGOPawnASCResourceHandle&, const FGGYGOAvatarBindingContext&, FString&)`、同参数 `RefreshLocalAbilitySystemResource`、`bool UninitializeFromLocalAbilitySystemResource(const FGGYGOPawnASCResourceHandle&, FString&)`。bool仅为本次完成／幂等历史，OutError明确拒绝或重入失效原因，不构成当前权限。

唯一记录含原 Health／Pawn／Extension弱身份、原 H、ASC／HealthSet弱引用、认证 PublishedContext、五个原委托 token及本记录退休标记；组件只持有这一记录，删除裸缓存。DeathState仍为原死亡阶段唯一权威。五个 protected处理器携原 opaque记录和事件入口 Context；全项目已确认无外部覆盖／调用，不需第四文件。类型定义留 cpp，头只前置声明。

```text
明确原 H／Context → 验证真实 Ready、原 Pawn／Extension／ASC／HealthSet
  → 已失效旧记录按原记录退休；仍 Installed的不同 H明确冲突
  → 唯一新记录 + 五个实际返回 token
  → 原 DeathState投影 → 原 Set三次初值广播
  → 每次外调后只复核原记录／H／Set／Context；失效停止，不收养后继

Refresh：认证同 H新 Context → 更新同记录 Context → 不重装 token／不重复 UI初值
Release／EndPlay／OnUnregister：先退休原记录并摘原槽 → 五个原 token精确归还
```

委托 lambda只捕原记录，每次事件入口从该原记录复制当前经认证 Context；不在 Add时固化安装 Context，保证同 H Refresh后继续消费。旧事件／安装尾部始终核对捕获的记录指针和 Context；失败只退休本次仍归原作用域的记录，保留同 H重建或 Context刷新后的合法后继。

两个 Blueprint旧签名保留：旧 Init只能捕自身 Extension实际 Ready H及原 ASC Context，验证 InASC后调用唯一机制；旧 Uninit只捕 Health自持原记录调用精确释放。无 H、无 Ready或缺 HealthSet明确失败，不构造兼容成功／失败绑定。读值、Tag投影、GameplayEvent及自毁 GE均改读原记录；死亡状态及 GE业务规则保持。

EndPlay和OnUnregister关闭本组件新资源准入，直接退休自身原记录；原 Set有效时按五 token Remove，失效时只退休该历史义务，不寻找替代 Set。清理不 RequireReady，也不等待 Extension Released。真实注册／下一次 BeginPlay再重开自身准入。

只读依赖为 Extension／BindingTypes、ASC公开查询、HealthSet五个委托及 Base现有接线；不修改这些共享源。后继 Base typed notice单独租约：Ready精确安装、Refreshed同 H刷新、Released只释放通知 H，撤掉旧无参数生产订阅。Health本步骤立即替换实际机制，不留未使用准备层；完整链冻结后同一新 DLL／新 World统一编译和必要冒烟。

为什么这样写：同 H可能对应 Health自身重新安装的不同记录，五 token必须归原记录；事件 Context须按每次实际调用复制。改了会坏什么：RemoveAll会移除后继委托，永久捕获安装 Context会使 Refresh后委托失效，外调后读当前缓存会把旧 UI／Tag／GE作用域转给后继。

有限验收为唯一资源取代缓存、五 Add对应五精确 Remove、旧入口共用实现、原处理器参数／逐外调复核／自身结束清理、旧死亡和 GE规则保持。原无 H死亡投影夹具及严格矩阵不适配／不运行，历史成功不沿用。本步骤不写 Base／Hero／CMC／ASC／HealthSet／共享类型、测试、资产、UE／Build／Git／Obsidian／全局或子代理；第四文件、外部处理器覆盖、共享变化或死亡业务取舍即停。三文件有限交回后立即冻结。

### 13.1 实际实施与有限静态结果

2026-10-03：Health唯一原资源机制已实际替换旧缓存与委托绑定。三个 native bool入口按冻结签名实现，两个旧 Blueprint入口保留原声明并立即调用同一安装／释放机制；无真实 H、未 Ready、ASC不符或 HealthSet缺失均返回明确失败，旧 BP入口记录可定位诊断。没有保留第二套裸 ASC／Set缓存或未使用准备层。

| 实物 | 当前行数／Bytes | SHA256 |
| --- | --- | --- |
| [Health.h](../../../Source/GGYGO/Character/Components/GGYGOHealthComponent.h) | 264／13029 | `05D7CB7B1CAD0D2F8FAEA40B40750F3B87342F461599A24AF5A85D2B471CC213` |
| [Health.cpp](../../../Source/GGYGO/Character/Components/GGYGOHealthComponent.cpp) | 777／35337 | `536CEE8651BC324868971FB141DE60EBD5C448BB94FAE43A2A4DFCD3BDD4FCAF` |

实际所有权和清理：

- cpp内唯一记录保存原 Health／Pawn／Extension、H、ASC、HealthSet、认证 Context及五个真实委托 token；五个 lambda只捕该记录，在每次事件入口复制它当时经认证的 Context。Refresh验证同 H与相同原资源对象，更新同记录 Context，不重装 token或重复三次 UI初值。
- 安装与各处理器在外部 UI广播、死亡 Tag投影、GameplayEvent或自毁 GE调用后复核原记录／H／Set／Context，失效即停止。处理器及投影均先复制原记录和 Context，尾部不读取当前槽来收养后继。安装失败清理只作用于仍属于本次 Context的原记录，保留同 H重新安装的不同记录及合法 Context刷新。
- 退休先复制输入记录，标记退休并仅摘除指针相同的自身槽，复制并清空五 token后向原 Set逐个 Remove。清理不要求 Ready，不依赖 Extension Released；原 Set已失效时只退休该历史义务，不寻找替代 Set。EndPlay／OnUnregister先关闭自身准入再直接退休，实际 OnRegister／BeginPlay按原生生命周期重开。
- Getter、死亡 Tag投影、OutOfHealth事件和自毁 GE改由已验证原记录提供 ASC／Set。DeathState仍为唯一死亡阶段，HealthSet仍拥有数值和事件；没有新增伤害结算、帧调度、Binding／Ready发行、队列或竞争状态。

有限静态检查通过：五处 AddLambda对应五处精确 Remove；五处仅捕原记录及五处事件入口 Context快照；旧 AddUObject、RemoveAll和两个裸缓存声明计数均为0。两个旧 BP声明逐字保持。GetLifetimeReplicatedProps、OnRep_DeathState、StartDeath、FinishDeath与写前原文逐字一致；自毁保留原 GE资产、业务 Tag与伤害公式。注释／字符串剔除后的源码括号匹配通过。三授权文件严格 UTF-8、无 BOM、仅 LF、末尾 LF且无行尾空白；新增链接目标存在，本记录原420行历史保持。

Extension h/cpp、BindingTypes和 Host接口 h/cpp五份冻结共享哈希保持；ASC独立输入租约的整文件变化不作为本步骤修改或失败。只写授权三文件，未新增测试或执行严格矩阵，未运行 UHT／编译／UE／冒烟／资产／网络验证。

架构核对：Health只消费 Extension的实际 H／Ready与 ASC认证 Context，不发行或复制其权威状态；cpp依赖共享公开接口，没有具体 CombatantState依赖。五委托、同记录 Refresh、精确释放和自身生命周期结束具有明确唯一归属；旧 BP入口已经收口，未保留平行执行链。

本步骤关闭“Health原资源机制已实现并有限静态交回”，三授权文件交回即冻结。Base仍需后继 typed notice租约撤除无参数生产订阅，Hero／Input按独立租约推进；旧无 H死亡投影夹具和准备阶段 Getter断言尚未适配／重跑。Host两个共享 ASC停点、同 Receipt活跃期后继授权政策、历史 R0失败、完整生产生命周期和资产／网络边界仍开放，不能以本次静态通过宣称关闭。统筹在完整链冻结后统一编译和必要冒烟，并维护全局进度与 Obsidian；本会话未写这些入口。

## 14. Base typed Health消费：三文件预检

2026-10-03：统筹接受只读预检并授权 Base h/cpp与本记录。基线 [CharacterBaseTypedHealthNotice_LeaseBefore.json](../../../Saved/ValidationRecords/CharacterBaseTypedHealthNotice_LeaseBefore.json)；写前三文件分别匹配 `072B5F0B0DC3EBF7D035FC7FCB6F9277F43F45ED654E667AE966EA1663918BD1`、`341CEF7A15F0312EDF15189040C54F16C5E157F77914C0EE118E44B697937542`、`EA9FBF189CA73B1F5DD8B7D54BEF3EE14C726D4276307F6F9F450F17663855A8`。本节先于源码实施登记；此前 Health与 Extension保持冻结。

| 精确文件 | 本步骤唯一结果 |
| --- | --- |
| `Source/GGYGO/Character/GGYGOCharacterBase.h` | 私有原订阅记录、typed消费和生命周期退休接口，撤旧无参数回调声明 |
| 同目录 `GGYGOCharacterBase.cpp` | 实际 RegisterAndCall、三类通知直达冻结 Health入口、原 token精确归还 |
| 本记录 | 本预检、有限静态证据、实际哈希及未验边界 |

依赖顺序：冻结 Extension发布和 Health原资源机制 → 本原子正式消费 → Hero／Input独立租约及两既有诊断签名适配 → 全链冻结后统筹统一编译和必要冒烟。只读依赖为上述公开接口与原 Base生命周期；不改共享类型或另外建立 Ready权威。

Base唯一订阅记录只含原 Base／Extension／Health弱身份、实际 token和退休标记；自身关闭位仅控制 Actor生命周期内的订阅准入，不缓存 H／ASC／Set／Context。构造函数撤旧注册，PostInitializeComponents的 Super后核对原组件注册，再先装记录槽、弱捕原记录调用 RegisterLocalAbilitySystemNoticeAndCall。同步回放可在 token返回前退休；返回 token始终归原记录，退休时立即向原 Extension精确 Unregister。没有委托／记录持有环。

每次入口复制原订阅和整份 Notice；Ready调用 Health InitializeWithLocalAbilitySystemResource，Refreshed调用同 H Refresh入口，Released仅用通知原 H调用精确 Uninitialize，不 RequireReady或重读当前 H。Health独占实际原资源和五 token；Base返回尾部只记录本次结果，不回滚、清当前资源或补调用。

EndPlay／BeginDestroy先关闭自身准入、摘原订阅并退休，再 Super；记录析构只补归还残余原 token，不调用 Health清理。真实新 BeginPlay在 Super完成且 Actor确实重新开始后重建已关闭订阅；首次已有订阅不重复注册，普通回放／Ready／Released均不重开准入。注册失败明确诊断，无轮询或静默重试；正常观察回调允许同步完整接续，不加 Busy、排队或调度。

验收为旧注册／旧 BP调用和无参数回调归零、三类 typed路由唯一、token返回前退休／精确归还／生命周期关闭成立、无资源缓存或第二 Ready、普通接续无旧尾部清理；死亡／Controller／输入转发等非目标函数保持。Source/GGYGO未发现旧 Base protected回调外部调用／覆盖，HeroCharacter与 BossCharacter不需本次改动。发现第四文件、外部覆盖、共享不足或死亡业务取舍立即停交回。

非目标为 Health／Extension／ASC／Host／Input／Hero／CMC及共享源码、死亡与 GE业务、诊断／夹具／新测试或严格矩阵、资产／UE／Build／Git、Obsidian／全局和子代理。既有两个 Retry诊断的旧二参数 lambda与 ASC新单载荷签名不符，后继只适配现有文件；旧无 H死亡投影夹具、准备阶段 Getter空断言和 Input自有 Pawn无 Host端口为运行契约边界，本原子不改断言或伪造兼容成功。三文件有限交回后立即冻结。

### 14.1 实际实施与有限静态结果

2026-10-03：Base构造函数的两处旧注册、两旧无参数 protected声明／实现及其旧 Health BP调用已删除。PostInitializeComponents的 Super后正式建立 typed订阅；Ready／Refreshed／Released分别直接调用冻结 Health三个 native入口，没有未使用准备层或第二消费路径。

| 实物 | 当前行数／Bytes | SHA256 |
| --- | --- | --- |
| [Base.h](../../../Source/GGYGO/Character/GGYGOCharacterBase.h) | 153／6285 | `EAA835FC3870696E41F55924B1CC484FE9494A70C2FF21D811C0229DE9EC8EAC` |
| [Base.cpp](../../../Source/GGYGO/Character/GGYGOCharacterBase.cpp) | 472／18317 | `A6326155E6800D1228516848FE8F21CD5AEADA1B73F1889BC0ABBDE53012966D` |

实际原记录只有三份原对象弱身份、NoticeHandle和退休标记；lambda只弱捕该记录，组件实际装槽早于 RegisterAndCall。每次通知入口复制原订阅与整 Notice，不以 token尚未返回阻断普通消费。同步回放若使原记录退休，AcceptReturnedHandle直接向原 Extension归还刚返回的 token；正常退休先标记／摘自身原槽，再复制并清空 token并精确 Remove。析构只补相同 token义务，未持有 Health资源或形成引用环。

EndPlay／BeginDestroy先关闭自身订阅准入、摘槽退休再 Super；原 Extension即便失去 Ready仍可接受精确 Unregister。实际新 BeginPlay在 Super完成、Actor仍确实开始且自身原准入仍关闭时才重建一次；普通通知不能重开。注册失败保留明确诊断，不按帧重试、生成替代资源或清理别的生命周期。Health五委托仍只由 Health自身清理。

每类通知仅有一次对应 Health native调用；Released不查询 Ready、ActorInfo、当前 H或 Context。调用后只诊断本次失败，没有后继清理、回滚、再读当前 H或 UI／死亡表现补广播。正常回放／Ready／Released没有 Busy、队列或调度器；旧订阅注册尾部只退休原 token，并以记录指针匹配保证合法后继保留。自身关闭位只描述 Actor订阅准入，不构成第二 ASC或 Health权威。

有限静态检查通过：旧无参数回调和旧 Health BP调用均为0；正式 RegisterAndCall为1；两处精确 Unregister分别覆盖晚返回 token和通常退休；Health Initialize／Refresh／Uninitialize各1；当前 H读取为0。源码与写前完整候选逐字一致，注释／字符串剔除后的括号匹配通过。GetAbilitySystemComponent、GetGGYGOAbilitySystemComponent、GetGGYGOMovementComponent、PossessedBy、UnPossessed、OnRep_Controller、OnRep_PlayerState、SetupPlayerInputComponent、FellOutOfWorld、OnDeathStarted、OnDeathFinished、DisableMovementAndCollision、UninitAndDestroy共13个非目标函数与基线规范化换行后逐字保持；死亡动态委托及组件构造保留。Base两源统一为 LF，不把换行规范化算作业务变化。

Health h/cpp、Extension h/cpp、BindingTypes及 Host接口 h/cpp七份冻结哈希保持；未以独立 Input／ASC租约整文件变化判本步骤失败。三授权文件严格 UTF-8、无 BOM、仅 LF、末尾 LF且无行尾空白，本记录原481行历史保持，新增本地链接目标存在。只写授权三文件，未改诊断或夹具，未运行 UHT／编译／UE／冒烟／严格矩阵、资产或网络验证。

架构核对：Base仅负责组件接线与自身原订阅 token，Health仍唯一拥有数值委托和原资源，Extension／ASC仍唯一认证 H／Ready／Context。未新增具体 Host依赖、循环依赖、内部状态读取、资源缓存、重复生命周期执行链或帧调度；同步接续与自身关闭时的原订阅清理均有明确归属。

本步骤只关闭“Base typed Health正式消费已实现并有限静态交回”，三文件交回即冻结。两既有 Retry诊断签名适配、Hero／Input生产链及原运行夹具契约边界仍待独立租约；Host两个共享 ASC停点、同 Receipt活跃期政策、历史 R0失败及完整生命周期／资产／网络仍开放。完整链冻结后由统筹统一编译和必要冒烟，源码交回不能代替这些门禁；统筹维护全局及 Obsidian，本会话未写这些入口。
