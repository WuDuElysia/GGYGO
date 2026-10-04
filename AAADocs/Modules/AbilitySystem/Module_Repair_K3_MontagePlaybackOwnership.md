# K3：ASC 精确 Montage 播放归属

日期：2026-10-03（Asia/Shanghai）。AbilitySystem 长期组长直接执行，gpt-6.1-sol / xhigh，无子代理。

## 授权与原子预检

用户已选择项目ASC精确播放归属接口，保留原混出清空时机。统筹授权四文件，基线 `Saved/ValidationRecords/ASCMontagePlaybackOwnership_LeaseBefore.json`。ASC h/cpp入口hash分别A8736E9A…／B839A975…，两新路径不存在。AnimationRuntime两新Editor源独立并行，不纳入整树静止断言。

| 唯一目标 | ASC认证真实Local播放写入的签发、验证、纯捕获、退休及仅原归属清空 |
| --- | --- |
| 精确文件 | Source/GGYGO/AbilitySystem/GGYGOAbilityMontagePlaybackTypes.h（新）；GGYGOAbilitySystemComponent.h/.cpp；本记录（新） |
| 唯一权威 | 引擎持有Montage Instance及GAS Local/Rep/GA写入；Animation持Guard生命周期/CallId；ASC只持一份当前真实Local写入的provenance。GA/Task未来只持原资源值 |
| 冻结接口 | TryPlayMontageWithOwnership(Ability,ActivationInfo,Montage,PlayRate,StartSection,StartTimeSeconds,IsOriginalCallerCurrent)；CheckMontagePlaybackOwnership(Original) const；TryClearMontageAnimatingAbility(Original)；CaptureMontagePlaybackOwnership(OriginalAbility,OriginalSpecHandle,OriginalActivationInfo) const |
| 顺序与依赖 | 登记→值类型/ASC接口→复用完整Super/GuardScope与原写入失效接缝→有限静态/保护核对→四文件冻结。Guard A1/A4/A5、UE5.8 Local/Instance/Stop/复制入口、既有Task/严格复现只读 |
| 非目标 | GA/Task消费、终止/业务迁移；Input E2行为；销毁见证/Init失败收尾及其它三项待答决定；Host/Extension/Hero/Teams/GF；测试/新矩阵/资产/网络/Build/UE/Git/Obsidian/全局 |
| 有限验收 | 完整Super返回且Guard Accepted并真实Local/GA一致才签发；同GA同资产A/B区分；B停止不复活A；Check/Clear不依赖活动资产；失败/拒绝外层不退休已接受B；实际项目ActorInfo/Local写入退休原记录，同端点Refresh无来源改变则保留 |
| 停止点 | 第五文件、Guard/共享协议缺口、循环依赖/第二播放执行状态、无法观察的来源改变或未确认取舍立即停止交回；四文件冻结后不自动接GA/Task |

## 根因与合同边界

原生ClearAnimatingAbility只比较GA指针，8位PlayInstanceId会回绕；Task的活动资产/无活动实例分支不能认证每次播放来源。Guard已有原AnimInstance、生命周期代次、非复用CallId及实际CreatedInstanceId，但其生命周期查询不证明Accepted或ASC Local写入，也不能检测未观察的Owner A→B→A。

opaque Handle只能由ASC创建。结果携带原Guard完整证据、真实Duration、Outcome/Reason及原资源；失败不补播放Handle。ASC记录是原生写入的来源证明，不含播放活动、进度、停止政策、计时器/帧调度。停止不撤销仍属该来源的清空资格；混出仍由消费者请求原清空，成功仅沿原生GA CurrentMontage=null与Local AnimatingAbility=null语义，不Stop或延期。

签发必须在完整GAS Super及Guard Complete之后；Superseded外层不覆盖已接受内层B。未认证Local写入/ActorInfo重置须在项目可截获的真实接缝使原证明不可复活；Busy/准入拒绝及无写入失败不能凭空退休后继。原同端点Refresh若没有Local写入/OwnerAvatarMeshAnim等来源变化，保留播放证明，不用Publication/Binding修订强制延期清空。裸基类qualified写入、未观察的Owner ABA不由本契约冒称可截获。

原严格复现（同GA同Montage A→B、B停止、A晚到混出）与已有失败保留；本轮不新增/运行矩阵或夹具。首步后依次GA原播放捕获/统一终止→Task单一结果与原资源消费→统筹整链编译及必要UE冒烟，不能由首步声明或静态通过关闭生产问题。

## 实际实施与有限证据

### 首步实际产出（源码完成，生产链未完成）

四个公开入口已实现：TryPlay 返回完整 Guard 证据、真实 CallerReturnValue、Outcome/Reason 和仅成功签发的 Playback；Check 纯核对原归属；Capture 只返回原 GA／Spec／Activation 对应的已有认证记录；TryClear 只清理经 Check 验证的原资源。没有新增停止、计时、帧调度、播放活动状态或资源替代路径。

Handle 内部证明不可由调用方构造。唯一当前 provenance 使用原 ASC、GA、Spec、PredictionKey、完整 ActorInfo 来源快照、Guard 生命周期／CallId／CreatedInstanceId 与原生 Local 写入；8 位 PlayInstanceId 只用于一致性核对，不能充当播放身份。完整 qualified Super::PlayMontage、Guard Complete 和作用域退出后，Accepted 且来源、GA 与真实 Local 一致才发布。接受历史不等于认证成功；签发来源不一致有明确 Reason，失败没有 Playback。既有 PlayMontageWithGuard 的 Guard／float 合同保留。

Check／Clear 不调用 ASC 活动资产查询，也不依赖活动实例存在或 GA IsActive。Capture 的 NoOwnedPlayback 仅说明没有对应认证记录，不能解释为没有物理播放。实际 Init／Clear（含事务入口）在准入通过、真实原生写入前退休；Refresh 前后核对实际来源，同端点且 Local／来源未改变时保留证明。模拟、复制、分数循环动态 Montage 和旧 Clear 入口在真实原生调用后核对或退休，拒绝／无实际写入不能无故退休已接受后继。OnUnregister 退休本组件记录。未观察的基类 qualified 写入和 Owner ABA 仍不在保障范围。

精确 Clear 采用 qualified UGameplayAbility::SetCurrentMontage(nullptr) 与 Local.AnimatingAbility=null 两次原生字段写入。UE5.8 的 GA setter 是 virtual；若沿旧 ASC Clear 进入重写 setter 后再无条件清 Local，会允许重入后误清后继。当前项目没有 setter 重写；精确入口调用基类字段赋值，旧入口继续保留 Super 原语义。该选择不停止 Montage、不改变混出触发时机、不引入延期清理。

### 有限静态证据（不代替编译或运行）

- 四文件内容与本轮登记的预期文本逐字一致；对 h/cpp 的全部登记替换进行逆向核对，可恢复租约前全文。Input E2、准入／提交／发布规则和其它代码未发生未登记改写。
- 新 Handle 私有证明、唯一 provenance、完整 Super／Guard 顺序、Accepted 与来源／Local 一致条件、Capture 不签发、Clear 两字段语义均通过有限源码断言。
- 源码括号、冲突标记、尾随空白、严格 UTF-8 无 BOM、LF 和终止换行核对通过。这些是文本检查，尚未验证 UHT、C++ 编译或运行行为。
- 只读保护的 GGYGOMontagePlayGuard.h 与 GGYGOMontageGuardAnimInstance.h 保持原 SHA-256（ACAEA0FD…／1682C438…）。
- 原严格复现、同 GA 同资产 A→B／B 停止／A 晚到、重入、失败、ActorInfo、复制、动态 Montage、联机及资产验证均未运行。本轮未新增测试／夹具／矩阵，未执行 Build、UE 或 Git。

| 源码冻结文件 | 字节 | SHA-256 |
| --- | ---: | --- |
| GGYGOAbilityMontagePlaybackTypes.h | 2466 | FD01760E7F69D6980817AE1B754FA01B666087240D92269759D815CFA865E4E4 |
| GGYGOAbilitySystemComponent.h | 37546 | 47A0C80437C59B9BA53E2FEE24D206FF25D4EE624674BB4332EC787AFD4338FF |
| GGYGOAbilitySystemComponent.cpp | 151692 | 63D477B1EF62F311507F5881EF9BDC9A543C727D9DD771B5B5BE14263EF6ECD9 |

### 架构核对、交回及剩余边界

本步复用已有 ActorInfo 快照和 Guard 身份；依赖仍是 AbilitySystem→Animation Runtime，没有反向依赖或第二执行链。proof 只保留 weak 对象身份、来源值及 Guard 证据；组件的单份 provenance 持有 ActorInfo allocation，并在替换、真实生命周期写入、精确 Clear、Unregister 及组件销毁时释放。调用方复制的 opaque Handle 不持有 ActorInfo allocation，也不让播放保持活动。共享接口、测试、全局文件和其它模块均未写入。

四文件交回后冻结，不自动进入 GA／Task 适配。下一步仍为 GA 原播放捕获／统一终止→Task 原资源与单一结果消费→统筹统一编译及必要 UE 冒烟。现有生产调用尚未迁移，本步不能关闭 K3 根因或声明模块完成。ASC 销毁见证／Init 失败后中止与其它待决策边界维持原状态。

已只读核对 Obsidian 的计划蓝图.md 与 AbilitySystem/计划_AbilitySystem.md；后者仍记载 Montage 归属尚未实施。依据本轮四文件租约，Obsidian、全局入口和进度总览由统筹接手更新：同步为“ASC 精确接口源码首步完成；GA／Task／编译／专项／资产／联机未验收”，并更新结构.md、相关结构／流程 Canvas 和实施计划，不能写成生产问题已关闭。本轮没有更新 Canvas，交回时须保留该待办。

## 统筹后继状态（2026-10-03）：Task独立接力已冻结

以上授权、顺序与未接消费者描述保留为ASC首步交回历史。其后确认Task消费原播放Result不依赖尚待决策的GA统一终止接口，已将Task先行拆成独立两源租约。战斗组长实际turn `01a10110-81b9-72e1-8c98-89e50a8a02d1`已completed并明确冻结；统筹全文/最终hash有限静态接受，八只读依赖保持。h `52EC85F048020477A27952978EC69EE2C3E6173A0FEBE45D7131328B40739DF6`，cpp `35F04002F87D28BA36C6920C18BEF55F53C33E4D4B50D098D3589C52F5744A3E`。证据 `Saved/ValidationRecords/TaskMontageExactOwnership_20261003_Result.json`。

Task Activate实际消费ASC单一Result/原Handle/Guard，删除全局尝试表/token/新实例扫描；原实例委托携原Guard，原混出TryClear保持时机，外调中结束的原停止义务由调用栈共持，事件/取消/RootMotionScale资源只属Task。Completed仅为原实例Ended事实，不Check正常混出已退休的ASC证明，也不授结束后继GA权限；GA及Combo/Boss原生命周期认证仍另步未接。

源码未UHT/编译/UE，旧nonGuard/after-Super/手工instance ID夹具未适配，历史严格失败未复测，不新增矩阵。统一GA终止的受控激活/拒绝同调用自动Retrigger可见行为仍待用户决定，未授权四源实现；正式AnimClass、资产及联机仍开放。相关AbilitySystem四份图文、Animation结构及三个总览入口已由统筹同步保存回读；两Canvas增加两个节点/两条边，原节点几何和边拓扑保持，JSON/链接/锚点核对通过，无原生视觉验收。
