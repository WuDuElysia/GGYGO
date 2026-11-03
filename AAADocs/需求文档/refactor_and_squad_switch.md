# 代码整改（CR-R7 扩展）与换人续放：活动记录

更新：2026-11-03。本页是这一批的唯一活动记录，保存用户决定、目标、未完成项和验收标准，执行者为 Kiro（Claude Opus 5.5）。共享窗口、写入者和构建排期仍以[当前排程](../Coordination/Module_Repair_Parallel_Schedule.md)为准，本页不分配窗口；请统筹在[修复清单 CR-R7](../Coordination/Module_Audit_Repair_Ledger.md#cr-20261014-r7)原条目中索引本页，不另复制正文。续接时以本页为准，不依赖旧聊天。

## 现状

- 第 1 步 abilitysystem-redundancy-cleanup、第 2 步 abilitysystem-input-request、首击 B：源码完成，批次 1 已集中编译并跑 NullRHI 测试（结果见下）。
- 未验：PlayerCombo 生产冒烟 7 例与 Kevin 冒烟（需真实 RHI＋L_Movement_Test，不在已批额度内）、人工 PIE、FX 联机。首击 B 的端到端效果需要这些冒烟或人工 PIE 确认。第 1 步任务 6（Legacy 消费者）已在收尾完成。
- 第 3 步 fx-montage-publication-ownership：源码完成并过 NullRHI 测试（见下节）；Editor 蓝图子类核对已在收尾完成（没有蓝图子类）；FX 的 PIE 单机与最小联机未验（要看画面）。
- 第 4 步 abilitysystem-activation-lifecycle：源码完成并过 NullRHI 测试（见下节）；PIE 单机、最小联机与 N3 纠正重放未验。
- 第 5 步 combatants-avatar-binding：源码完成并过 NullRHI 测试（见下节）；PIE 单机与最小联机未验。
- 第 6 步 teams-squad-switch-linger：源码完成并过 NullRHI 测试（见下节）；收尾修正待命碰撞复制、待命骨架更新与换人相机准入，测试编队的 NullRHI 监听服务器 PIE 全部通过（Test_R22，无生产 Error）；换人键按用户 11-03 决定做成可配置的上一个／下一个，默认 Z／C（Test_R23 通过）；三项玩法取舍待用户；进退场动作资产缺省时跳过。
- 第 7 步 abilitysystem-healthset-repnotify：复现完成，保留分类帧（技术决定，已定案）；反算已迁出 ASC；NullRHI 测试通过；联机数值与广播一致性在收尾的监听服务器 PIE 中核对（见「收尾」）。
- 收尾（Root 续派，2026-11-03；之后用户授权 Kiro 直接完成剩余整改与 Git）：Legacy 消费者 Editor 核查与删除、宿主蓝图子类核查、待命碰撞复制修正、开发期切人入口、监听服务器＋1 客户端 NullRHI PIE、两处跨模块生产 Error 修正、Kevin 观察脚本消费者更新已完成；终态、问题处理与剩余验收见「收尾」节。
- Obsidian：受影响模块的结构笔记、Canvas 与 `模块参考.md` 已按当前源码改写（AbilitySystem、Animation、BossAI、Camera、Character、Combat、Combatants、GameFeature、Input、Messages、Movement、Teams）；`计划_*.md` 作为历史未改。Canvas 均通过 JSON／ID／边引用核验，改动笔记的 wikilink 锚点均存在，格式与换行按前像保持；未在 Obsidian 中目视检查。前像与脚本在 `Saved/Kiro/abilitysystem-healthset-repnotify/ObsidianBefore/`（manifest.tsv）及同目录 `obsidian_*.py`。Obsidian 仓未提交。
- 2026-11-03 Root 交接：子仓 index 中 ASC.cpp 的原作者暂存 blob adf1d663 已不在 index（现为 HEAD blob a608f263，index 无暂存，原因未明）。原 index 与原暂存内容已由 Root 留证于 `Saved/Kiro/abilitysystem-input-request/OriginalStaged/`；测试保护自 Test_R13 起以当前 index（SHA256 60B1E9AC…）接续，最终 Git 交付由 Root 单独核收。
- 第 1 步首个验证窗（`Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R1/`）：构建成功；Test_R3（NullRHI，39 例）14 通过；Test_R4（真实 RHI）因着色器缓存写入触线停止，并使额度超出约 29.6MiB。当时的失败已在批次 1 中按原因修复或归类，过程细节见该目录各 `return.json`。

## 批次 1（已编译、已测 NullRHI）

1. PlayerCombo 预备配置：授予实例在首次准入时解析段声明与伤害 GE／模式，只缓存成功结果。
   - CDO 上的纯查询（如 `CanActivateAbilityByHandle`）每次解析、不缓存：CDO 跨 PIE 存活，缓存会在编辑器改 Montage/GE 后给出旧结果。
   - 实例随授予创建、随移除销毁，所以不另挂 OnRemoveAbility／PostEditChangeProperty；运行期改配置的子类调 `InvalidatePreparedConfiguration()`，且只在未激活时改。必需 GE 类卸载或被新版本替换时缓存视为失效。
   - CanActivate、失败日志、Body 共用这份配置；Body 取快照，命中只核对返回 Spec 的 Def 是否为预备 GE 的 CDO，以及伤害键冲突。
   - 已知后果：PIE 运行中修改所引用的 Montage/GE，需要重新授予（重开 PIE）才生效。
2. ActionSet：BossState 采纳 Definition 时校验全部阶段的 ActionSet，有坏表就拒绝采纳；SelectAction 与 BT 不再整表校验。
3. BossMelee：保留每次激活一次 Resolve，不缓存。与原计划不同，理由是缓存收益可忽略。
4. 第 2 步（详见该 spec 的 tasks／design）：
   - ASC：请求记录不再存 Owner/Avatar/World，只靠 Revision＋记录存在判断有效；ProcessAbilityInput 入口查一次 ActorInfo，外调后只核 Revision；具名谓词取代三布尔参数；删除用尽分支与排队重排；删除公开 QueueAbilityInputRetry；新增 EndAbilityInputRequestsFromSource；InitAbilityActorInfo 的 Owner 变化也清空输入。
   - Hero：删除 Observation 与 Association 两层对象，动作绑定直接保存当前请求，会话直接保存关联资源；会话退役或关联变化时按来源一次结束全部请求；Hero 侧拒绝每个动作每种原因只报一次。
5. 首击 B（用户 11-03 选定）：移动来源尚无物理证明时（聚焦或出生后还没碰移动键），攻击按角色当前朝向立即起段，不再等待移动键。
   - `UGGYGOPlayerInput::ValidateStepStartInputReadiness` 把 AwaitingPhysicalProof 记为零轴的 Completed 事实；WaitComboInput 的 TargetData 与 CMC 段首事实校验接受该状态。
   - 移动执行仍只接受 Held；没有把该状态改记为 NotHeld，以免事实失真。
6. 测试：
   - 授予后改配置的 helper 先让缓存失效；删除激活中途改作者配置的注入；InvalidRequiredGE 改为在实际请求的准入被拒（预期日志恰好一次）后恢复合法 GE 走正常命中。
   - TraceShape.InvalidConfiguration、RequiredTreeRejectsInvalidRoot 的生产 Error 声明为恰好一次的预期；HitSemantics 距离专项改用带 GameInstance 的世界；Selection 坏表用例改为 `ActionSetValidatedOnAdoption`。
   - 新增 `GGYGO.AbilitySystem.InputRequest.EndRequestsFromSource`。
   - PlayerCombo 夹具改走真实输入：复用 Input 夹具（私有 GI、项目 LocalPlayer／PC／`UGGYGOPlayerInput`、Hero、Host ASC），攻击动作映射到 J 键，按键经 `PlayerInput::InputKey` 与 PC 原生输入帧（`TickPlayerInput`）进入 Hero → ASC `ProcessAbilityInput`。
     - 编辑器非 PIE 时 EnhancedInput 模块不逐帧 Tick，夹具同步完成它的帧末两步：立即重建映射，再由子系统入口广播重建完成。
     - Avatar 的 Mesh／AnimInstance 在 Host 绑定前组装：绑定提交的 ActorInfo 快照包含实际 AnimInstance，绑定后再换会让 Hero 看到 ASC 未就绪。
     - 测试 Pawn 补 `IAbilitySystemInterface`（与生产 CharacterBase 一样经 PawnExtension 取 ASC），命中窗 Notify 才能找到接收者；倍率用例改用 Host 自带的 CombatSet。
     - 准入拒绝用例（TraceShape 非法、非法必需 GE）仍直接调受控 Try，因为它们验证的是准入本身。
7. 证据：前像、差分与当前身份在 `Saved/Kiro/abilitysystem-redundancy-cleanup/` 与 `Saved/Kiro/abilitysystem-input-request/`（各自 `Before/`、`before_manifest.tsv`、`Patches/`、`after_summary.tsv`）。

### 批次 1 验证（`Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/`，NullRHI）

- 构建：Build、Build_R2、Build_R3、Build_R4 均成功，保护完整。
- Test_R1 跑受影响的 59 例：43 通过，16 失败。按失败原因修复后：Test_R2（21 例）、Test_R3（16 例）、Test_R5（20 例）。Test_R5：19 通过，1 失败，保护完整，5824 个句柄释放。
- Test_R4 被宿主进程中断：UE 未启动（无 host.json、return.json）。离线按该窗 before.json 复核，1083 件哈希输入、4741 件 Content、11 件 Trace 差集为 0，没有多出的 Trace，见 `Test_R4/interrupt_check.json`。不补写它的退出或保护结果；同一组用例由 Test_R5 重跑。
- 59 例当前结论：56 通过，3 例未通过：
  - `PlayerCombo.ActivationCommitAndEndReentry`：第 3 子例在 Montage Ready 回调里 End 后用裸 `TryActivateAbility` 重激活，后继的 Initial 请求没有输入 edge，按 10-25 的来源规则被拒（原 edge 已被原激活消费）；第 4、5 子例（End 广播内、ScopeLock 延期 End 后重激活）同类，因第 3 子例先返回而未执行。测试期望与现行来源规则冲突，归第 4 步（任务 2.2 改 Initial 路由、任务 7 改钩子测试）。
  - `Admission.GroupLifecycle`：reason=14（NativeEndNotObserved），2026-10-05 的 ModuleRepairGate 报告里已失败，早于本批，归第 4 步。
  - `Input.MovementOrigin.NativeBirthFirstDigitalPress`：需要原生 OS 窗口，NullRHI 下不可用，属环境限制。
- Test_R1 之后只改了测试文件（Input 测试夹具、PlayerCombo 测试、新增的来源退役测试）；夹具的其它使用者（Input.Fixture、PawnExtension、SquadSwitch 3 例）已在 Test_R5 重跑通过。

## 第 3 步（已编译、已测 NullRHI）

- FX 发布的关闭只由 lease 持有者执行：PlayerCombo 的段资源（`ReleaseFX`）与 LocomotionFX 组件（来源退役、Released／Closing 通知、注销）。删除 ASC 的 15 个退休包装、退休输出栈与"关闭已失效来源"的扫描，删除 CombatantState 两处 FX 派发。
- 新增 `UGGYGOMontageFXReplicationComponent`，挂在 CombatantState 上，持有复制状态、终止多播和发行者，提供 `PublishMontageFX`／`PublishLocomotionFX`；ASC 不再实现 FX 宿主接口。找不到宿主时发布方明确拒绝并诊断。
- 原生清理被拒（ScopeLock 等）时，`UGGYGOPlayerComboAbility::OnRemoveAbility` 按 Abort 归还 FX lease；宿主注销时仍未关闭的 lease 按 Abort 关闭并报告一次。
- GA 的退休激活参数链保留到第 4 步，已无 FX 消费者。实现差异与重核结论见该 spec 的 design.md。
- 验证：Build_R5 成功；Test_R6（74 例）71 通过。未通过 3 例都不是本步引入：GroupLifecycle、ActivationCommitAndEndReentry（第 4 步）；`Movement.Locomotion.InputConsumer.FailedRequestRecovery` 的行为断言全部完成，但生产 Error 日志未声明为预期，2026-10-02 的 ModuleRepairGate 报告里已失败（当时 2 条，现在 3 条，新增的一条是 CMC 来源准入拒绝），属 Movement 模块，本整改不修改。

## 第 4 步（已编译、已测 NullRHI）

- 激活身份：GA 在原生 PreActivate 的 `ASC::NotifyAbilityActivated` 签发 `FActivationProof{ASC, Ability, Spec, ActivationKey, Allocation, Serial}`，在 `ASC::NotifyAbilityEnded` 的原生广播之前退役，广播内重激活得到新身份。`IsActivationCurrent`＝同一身份、仍 Active、未进入结束清理。
- 结束：`EndAbility` 覆盖在正式结束时先调 `CleanupAbilityResourcesForTermination`（含相机接管归还），再调原生 End；删除 `CancelAbility` 覆盖。`RequestAbilityEnd／Cancel` 只返回 Accepted／NotCurrent／NotCancelable；原生 ScopeLock 期间请求延后执行，执行时重核原激活，不结束后继。
- 删除终止状态机（GA 约 1100 行、ASC 约 1150 行）：受控 Try、终止完成发布 `OnAbilityTerminationCompleted`、评估令牌、原生清理 scope、`*ForTest` 钩子、换人取消预留、`FinalizeAbilityGroupAdmission` 测试日志。
- 输入：`ProcessAbilityInput` 每次 Try 安装当前输入尝试，同 Spec 的第一次激活或失败通知认领；只有失败且带 GroupQueued 时排队重试。Initial 路由与分段输入改用激活身份与"结束清理期间"。
- BT 与 Editor 观察改订阅原生 `OnAbilityEnded`，按 Spec 匹配，处理 Try 内同步结束。
- Montage：ASC 只留 `PlayAbilityMontage` 一个入口（原生 `PlayMontage` 覆盖转到它），只支持 Guard AnimInstance；播放身份为 Guard 实例＋Local PlayInstanceId＋所属激活，`IsPlaybackCurrent` 另要求 Local 播放仍在该 AnimInstance 上（Avatar 换后 PlayInstanceId 会从头计数）。删除 Legacy 分支与 Simulated／OnRep 等仅为旧所有权记账的覆盖。Task 只保存播放身份，派发谓词不再查 ASC 所有权。
- 段寿命：PlayerCombo 段资源释放先解绑 Task 原生回调，回调只核所属段资源。BossMelee 改用共享 `FGGYGOMontageActionResources`（新增 Trace 窗口、`BeginProfileMotion`、`ArmFixedWatchdog`），自身只留 Mesh Tick 与 Tick 前置依赖。CMC 合并不带 Facing 的 `BeginMontageActionMotion`。
- 重核结论：两个生产动画蓝图都继承 Guard（ABP_Pyrios、ABP_Kevin_DemonBattle），故删除 Legacy；MontageGuard 没有只为 ASC 证明服务的部分，未改。
- 验证（`Verify_R2/`）：Build_R6～R10；Test_R9（90 例）89 通过，Test_R10（Boss 迁移后 38 例）全部通过。批次 1 遗留的 GroupLifecycle、ActivationCommitAndEndReentry 已通过（后者第 3、4 子例改为"没有自己输入来源的后继被明确拒绝且不残留"，第 5 子例改为 ScopeLock 内两次请求只结束一次）。未通过 1 例不归本步：`Camera.ModeOwnershipAndAvatarReceiver` 报 `unbound-required-arbiter`，相机 arbiter 委托只在 HeroComponent BeginPlay 绑定，相关代码与测试未改。Test_R8 因测试自身在结束广播内无限重入崩溃，已修测试守卫后由 Test_R9 重跑。
- 证据：`Saved/Kiro/abilitysystem-activation-lifecycle/`（`Before/`、`before_manifest.tsv`、`Patches/`、`after_summary.tsv`、各编辑脚本）。

## 第 5 步（已编译、已测 NullRHI）

- 绑定流程（Lyra 式）：`AGGYGOCombatantState::BindAvatar` 释放旧 Avatar（取消能力，保留 `Ability.Behavior.SurvivesDeath`；清输入；移除全部 Cue；ActorInfo 回到 Owner-only，宿主关闭时 `ClearActorInfo`；旧 Pawn 广播 Released），再 `InitAbilityActorInfo(宿主, 新 Pawn)` 并由新 Pawn 的 PawnExtension 广播 Ready。服务器经 `AttachAvatar`，客户端经 `OnRep_AvatarPawn`；绑定进行中的再次请求返回 `Reentrant` 并诊断。`AttachAvatar` 直接返回 `EGGYGOAvatarBindResult`。宿主订阅 Avatar 的 `OnEndPlay`／`OnDestroyed`，只释放仍是当前绑定的 Pawn。
- 删除绑定协议：ASC 的 Context／身份操作／实际快照／失败 Init 清理／发布记录／原生写窗口与三个 Try 入口，`GGYGOAvatarBindingTypes.h`、`GGYGOActorInfoSource.h`、`Private/GGYGOAvatarBindingProtocol.*`，宿主的步骤历史与 `FindClearCommit`。宿主接口只剩 `ReleaseAvatarBinding(ExpectedAvatar)`（死亡销毁前由 PawnExtension 请求）。`InitAbilityActorInfo`／`ClearActorInfo` 覆盖只保留清输入。
- 本地订阅：PawnExtension 提供 `FGGYGOLocalASCSubscription`（订阅时回放 Ready、重复 Ready 不回调、Released 只给已消费同一资源的订阅、分发中退订／重订安全）。Hero、CMC、Health、LocomotionFX 改用它；Health 自己订阅，`CharacterBase` 的转发样板删除。`HandleControllerChanged` 直接 `RefreshAbilityActorInfo`。
- Context 消费方：FX 移动来源身份改为 CMC 来源证明＋发布时的 ASC；Squad 换人请求改用 PawnExtension 资源句柄；分段输入来源去掉 BindingContext；换人退出改为核对期望 Avatar。
- ASC 拆分：输入缓冲 `FGGYGOAbilityInputBuffer` 与分段输入路由 `FGGYGOAbilityStepInputRouter`（`AbilitySystem/Private/`），ASC 保留公开入口与两处 TargetData RPC 覆盖并委托；ASC.cpp 由 4347 行降到约 1350 行。
- 与 requirements 的差异（理由见该 spec design.md「实现差异」）：Released 在解除 ActorInfo 之后广播（与旧行为、Lyra 一致；按 Req 2.2 字面顺序时 Boss Encounter 两例回归）；宿主接口收敛为"请求释放"而非"取得 ASC"；中间 PIE 检查未做。
- 测试：删除 ActorInfoTransaction 9 例、PawnExtension.LocalResources、BindingSuccessor 诊断（它断言在 Released 回调中接管成功，与嵌套拒绝相反）；新增 `AbilitySystem.AvatarBinding.*` 3 例、`Character.PawnExtension.LocalASCSubscription`；`Combatants.Binding` 改为 3 例外部契约；其余测试调用点改名。共享测试世界改为 `InitializeActorsForPlay`，否则 Actor 的动态委托不会执行。
- 验证（`Verify_R2/`）：Build_R11 一次通过；Test_R11（111 例）暴露释放顺序问题，修正后 Build_R12、Test_R12：108 通过，3 例为既有失败（`Camera.ModeOwnershipAndAvatarReceiver`、`Input.MovementOrigin.NativeBirthFirstDigitalPress`、`Locomotion.InputConsumer.FailedRequestRecovery`，失败内容与 Test_R9／Test_R6 相同）；3 例带警告，与 Test_R9 相同。
- 证据：`Saved/Kiro/combatants-avatar-binding/`（`Before/`、`before_manifest.tsv`、`Patches/`、`after_summary.tsv`、`progress.md`、各编辑脚本）。第 3～5 步的 `make_patches.py` 对后续删除的文件按空内容出 diff，摘要标 `deleted=True`。

## 第 6 步（已编译、已测 NullRHI）

- 能力接口：GA 基类 `OnAvatarSwitchOut(FGGYGOSwitchContext)`（BlueprintNativeEvent，默认读 AvatarExitPolicy：Cancel→取消，ContinueInBackground→留场）、`OnOwnerControlLost`／`OnOwnerControlRegained`（蓝图事件，另有原生钩子）。现有 7 个 GA 资产仍为默认 Cancel，上线后行为与旧版一致，直到设计者把具体技能改为 ContinueInBackground 或在蓝图里覆盖决定。
- Squad 状态机（服务器）：Benched／Active／Lingering／Exiting，订阅各槽位 ASC 的 OnAbilityEnded 推进。切换顺序：取得全部决定（Cancel 决定的能力不可取消时整次拒绝）→ 登记续放、取消其余 → 补发按住输入的真实释放 → OnOwnerControlLost → 退役 Hero 输入、UnPossess → Possess 新队员（镜头随原生 ViewTarget）→ 待命队员显示并发 `Event.Squad.SwitchIn`；留场／退场中的队员取消退场、解除 OffField，仍有续放时加 `State.SwitchReturnPending` 并发 OnOwnerControlRegained → 旧队员加 OffField，有续放则留场，否则发 `Event.Squad.SwitchOut`，等被激活的退场能力结束后隐藏。
- 留场：可见、有碰撞；打开 `bRunPhysicsWithNoController` 让技能位移与重力继续；OffField 为复制的 `State.OffField`＋仅服务器的 `Gameplay.Damage.Immunity`，MeleeTrace 跳过 OffField 目标。没有制作 GE_OffField 资产。
- ReturnPending：只拦输入缓冲发起的新激活，事件触发（受击、死亡）不受影响；被拦的按下在缓冲窗口内登记重试，标签移除后的下一帧输入消费时重试一次。CMC 的 locomotion 阻止同样读该标签。
- 网络：新增 `ServerRequestSwitchToSlot`（Reliable，WithValidation 只查序号范围）。项目中仍没有接到切换的输入或蓝图调用，需要在角色／PC 蓝图里接线。
- 新增 `UGGYGOSquadTransitionAbility`（配置 Montage，由对应 GameplayEvent 触发，播完结束；蓝图实现 ActivateAbility 时由蓝图接管；默认 ServerInitiated）。删除 ASC 的换人退出旧实现（TryExit／CheckExited／退出 scope 等）。
- 测试：SquadSwitch 改为 6 例（Cancel 取消与状态保留、不可取消拒绝、续放留场后退场且留场免伤而结算照常、切回留场队员与缓冲按下、三人场景、退场中切回取消退场）。
- 验证（`Verify_R2/`）：Build_R13 一次通过；Test_R13（114 例）109 通过，3 例为既有失败（同第 5 步），2 例是夹具环境问题（未开局世界中 CMC 不订阅 ASC；无消息路由时 Damage 结算报投递失败），改测试后 Test_R14 通过。
- 待用户（Root 已转问）：ReturnPending 不拦已在运行的续放能力的按键；不可取消的 Cancel 决定整次拒绝换人；首位入场也发 SwitchIn。正式切换按键已定（见「收尾」）。PIE 与最小联机已在收尾用测试编队完成（NullRHI）；进退场 GA 资产缺省时按既定规则跳过。
- 证据：`Saved/Kiro/teams-squad-switch-linger/`（`Before/`、`before_manifest.tsv`、`Patches/`、`after_summary.tsv`、`progress.md`）。

## 第 7 步（已编译、已测 NullRHI）

- 复现：`GGYGO.AbilitySystem.HealthRepro.CurrentVersusLyra` 在同一夹具上对比现行实现与测试专用的 Lyra 做法（服务器在 PostGameplayEffectExecute 按 GE 幅度广播，客户端 OnRep 按 Old／New 广播），场景为普通伤害、治疗、破韧、致死、持续 GE 下调 MaxHealth、持续 GE 下改当前 Health，客户端为模拟接收。
- 结果：五个场景两边一致；持续 GE 下调 MaxHealth 时，Lyra 做法在服务器（含 listen 主机）不广播 MaxHealthChanged，HealthComponent 的 OnMaxHealthChanged 及其 UI／蓝图收不到。客户端六个场景都一致。日志：`Saved/Kiro/abilitysystem-healthset-repnotify/Repro_R14/`。
- 决定：按 Requirement 2.2 保留分类帧，差异写入 HealthSet.h 文件头。曾列出的简化（服务器保持 PostAttributeChange 广播，客户端只在 OnRep 广播并删去 RepNotifyFrame／NetReceiveFrame）不采用：没有回卷、重入与客户端上限投影的等价证明，现行实现在复现与联机中结果正确。按 Root 11-03 指示作为技术决定定案，不交用户。
- 反算迁出：`GGYGOAttributeBase::CalculateBaseForCurrent`（`AbilitySystem/Attributes/GGYGOAttributeBaseCalculation.*`），逻辑与失败分类不变；ASC 删除 `TryCalculateNumericAttributeBaseForCurrentValue`。
- 重核：没有客户端预测伤害（PlayerCombo 只在权威端开命中窗，BossMelee 激活要求权威）。
- 验证：Build_R14、Build_R15 通过；Test_R14（HealthMessage 15、DamageExecution、DeathProjection 2、HealthRepro、SquadSwitch 2，共 21 例）全部通过；Test_R15 复现改为回归断言后通过。联机核对见「收尾」（Test_R19 生命阶段）；死亡未联机验证。
- 证据：`Saved/Kiro/abilitysystem-healthset-repnotify/`。

## 收尾（2026-11-03，Root 续派）

改动（前像与 diff：`Saved/Kiro/closeout-20261103/`）：
- MeleeTrace：Editor 核查无消费者后删除 `BeginTraceWindow`／`EndTraceWindow`、Legacy 窗口来源、只由它广播的 `OnMeleeHit` 及 `GGYGOMeleeTraceTestReceiver.h`；`SafetyAndCoverage` 改用 Owned 窗口，原断言保留；新增 `GGYGO.Combat.MeleeTrace.LegacyConsumerAudit`。
- FX：新增 `GGYGO.FX.MontagePublication.HostSubclassAudit`。
- 待命碰撞复制：引擎的整体碰撞开关不复制，客户端会保留待命队员的胶囊。新增 `AGGYGOCharacterBase::SetReplicatedActorEnableCollision`（复制属性＋OnRep），Squad 的进场／待命改用它。
- 开发期切人入口：PlayerController Exec `GGYGOSwitchToSlot N`，走 `ServerRequestSwitchToSlot`。
- 正式换人键（用户 11-03：留设置接口，默认 Z 上一个、C 下一个）：换人输入归 Controller，不随 Hero 输入会话在换人中途退役。`AGGYGOPlayerController` 新增 `SquadSwitchInputMapping`／`SwitchToPreviousMemberAction`／`SwitchToNextMemberAction`／优先级四个 EditDefaultsOnly 配置，本地 Controller 建好 InputComponent 后按 Started 绑定、注册 IMC，EndPlay 归还本 Controller 那一份；三项都不配表示不提供换人键，只配一部分报 Error 不安装。按键发 `UGGYGOSquadComponent::ServerRequestSwitchToAdjacentSlot(±1)`，服务器按权威出战序号循环跳过死亡／无实体位置，来源 PlayerRequest；`SwitchToNextSlot`／`SwitchToPreviousSlot` 与它共用 `SwitchToAdjacentSlot`。资产（`AAADocs/Scripts/wire_squad_switch_inputs.py`，Asset_R23b）：`IA_SwitchCharacter_Prev`／`IA_SwitchCharacter_Next`（Boolean，PlayerMappableKeySettings 名 `SwitchCharacterPrevious`／`SwitchCharacterNext`，分类“队伍”），`IMC_Squad`（CountRegistrations，Z→上一个、C→下一个），`BP_PlayerController` CDO 接这三项。改键：改 `IMC_Squad`；玩家改键界面尚未做，届时需打开 Enhanced Input 的 `bEnableUserSettings` 并注册 IMC，按上述 PlayerMappable 名改键。`InputTag.SwitchCharacter.Next／Prev` 两个 Tag 仍未使用。
- 联机测试 `GGYGO.Teams.SquadSwitch.ListenServerClientRequest`，夹具新增持续下调 MaxHealth 的 GE 与 HealthComponent 观察器。
- 待命骨架更新：Squad 的 `DeactivateSlot` 置 Mesh `bNoSkeletonUpdate=true`，`ActivateSlot` 恢复（服务器端）。不关组件 Tick：开局登记早于 BeginPlay，注册时按 `bStartWithTickEnabled` 会重新打开。出战顺序是先 Possess 完成初始化再恢复，CMC／PawnExtension 语义不变。联机测试在就绪与再次切入两处断言该开关。
- 换人相机准入：`AGGYGOPlayerCameraManager::ActivateCameraEvaluation` 在 Running 时，若请求来源是准入 Controller 当前附身的 Pawn，按首次准入同一流程重新校验、选 ViewTarget 并求值一次，替换准入来源；其它来源仍以 `already-activated-for-another-original-source` 拒绝。
- `AAADocs/Scripts/observe_bh3_kevin_combat.py`：从原前像（23714B，E6355678…）最小更新，删去 `on_hit` 与 `OnMeleeHit` 绑定，改写限制说明，保留 `is_tracing` 与 Health 绑定；新文件 23391B，SHA256 `0B599750BCAA78AC5CAFEEE7AF748703CADDB4824CA673F5307F50C2A04246AC`。`restore_bh3_stage_environment.py` 的 P3 运行时 `standby_sha` 须传这个新值。只做了语法编译检查，未在 Editor 中运行。

验证（`Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/`）：
- Build_R16～R19 全部成功，只有既有的 C4996 警告。
- Test_R16a（NullRHI，54 例：MeleeTrace 与 Combo、PlayerCombo 15、HitSemantics 4、BossAI Melee／Encounter 9、SquadSwitch 6、FX 7、Combatants 6、AvatarBinding 3、PawnExtension 1，含两项 Editor 核查）全部通过。Legacy 核查加载 42 个蓝图、92 张图、680 个节点，0 个消费者；宿主核查列出 CombatantState 的 9 个子类，没有蓝图子类，全部带 FX 复制组件。
- Test_R17（L_Movement_Test）：SquadSwitch 私有 6 例通过。
- Test_R19（L_Movement_Test，NullRHI 同进程监听服务器＋1 客户端，测试编队为 Experience 首位 Pyrios 的两份实例，PostLogin 写 Roster）：行为断言全部通过——生产装配；客户端 RPC 切人；留场可见、有碰撞；OffField 复制、免疫不复制；ReturnPending 复制与解除；待命隐藏且无碰撞；切到待命队员后客户端控制且 ViewTarget 跟随；服务器施加伤害 10、持续 GE 下调 MaxHealth 20、削韧至 0 后两端属性与 HealthComponent 数值及广播一致（持续 GE 下调上限时服务器也广播）。Automation 结果为 Fail，原因是下述问题 1、2 的 3 条生产 Error，未过滤。Test_R16b、R17、R18 是该测试的前几轮（PIE 会话身份读取与结束方式在 R18 修正）。
- Build_R20～R22 成功。Test_R20（L_Movement_Test，15 例：Camera 7、PawnExtension 1、SquadSwitch 7）：相机 Error 消失；13 例通过，`Camera.ModeOwnershipAndAvatarReceiver` 为既有失败（8 条与 Test_R12 相同），联机测试剩 1 条 WalkRunLean（主机第二名队员；当时用关闭 Mesh Tick，被 BeginPlay 注册重新打开）。改用 `bNoSkeletonUpdate` 后 Test_R21 的 SquadSwitch 7 例全部通过；加入骨架更新断言后 Test_R22 的 7 例全部通过，无生产 Error。UnrealEditor-GGYGO.dll 7864320B，SHA256 0694DEBD…。
- 换人键：Build_R23 成功；Asset_R23b（pythonscript commandlet，只放开 BP_PlayerController 写入、只允许三个新包）创建并读回映射、可改键名与 CDO 引用，保存 4 包，无其它脏包（Asset_R23 因执行脚本自身路径改名在启动前被保护拒绝，UE 未启动）。Test_R23 的 SquadSwitch 7 例全部通过，联机测试中客户端经 PlayerInput 真实按 Z 切回、按 C 切到待命队员；Test_R23b 回归 Test_R16a 清单全部通过；Test_R23c 的 Input／Locomotion 输入 4 例中 2 例为既有失败（NativeBirthFirstDigitalPress 需真实窗口，FailedRequestRecovery 3 条未声明的生产 Error），内容与先前一致。

发现的问题与处理：
1. 已修（待命骨架更新，见上）：服务器上从未被附身的待命队员，PawnExtension 在权威端等 Controller，停在 Spawned，CMC 没有 MovementSet；隐藏的 Pawn 仍在更新动画，ABP_Pyrios 的 WalkRunLean 报 `required accepted MovementSet is missing outside the original initialization window`。选 Teams 侧让待命队员停骨架更新，不改 Character／Movement 的初始化语义。
2. 已修（换人相机准入，见上）：客户端切到新队员时，管理器已为第一名队员处于 Running，以 `already-activated-for-another-original-source` 拒绝并报 Error。
3. 已修：`observe_bh3_kevin_combat.py` 绑定已删除的 `OnMeleeHit`。
4. NullRHI 下角色渲染报 R32f 深度格式不支持：属运行环境，测试中声明为预期，不是缺陷。

终态：
- Test_R16a～R22 的 UE 实例均正常退出（UE 退出码 0），无残留进程；每窗的保护输入与 UBT Trace 文件按原身份归还（`protection_success=true`）。
- Git（用户 11-03：提交方式由 Kiro 定）：本批与他人先前未提交的改动交织（子仓 19、父仓 2 个文件三方冲突，且依赖他人未跟踪的 FX 文件），只提交本批无法编译。按作者分三段提交，工具与报告在 `Saved/Kiro/closeout-20261103/stage_git/`（`commit_stages.py`、`report_apply.json`）：
  - A 基线：子仓中他人的全部未提交源码（40 个文件）；父仓只含他人的代码与工程配置（GGYGOEditor、GGYGORendering、Shaders、uproject、Config，57 个文件）。本批改过的文件在 A 中取开工前前像。A 未单独编译。
  - B 第一阶段：第一阶段交接时保存的 blob（`stage1_git/stage1_blobs.tsv`）。
  - C 收尾续修与换人键：当前工作树中的本批文件；子仓末阶段树与当前工作树一致（Build_R23 所编译的源码）。
  - 父仓中他人的资产、文档、脚本改动与 `AGENTS.md`、`进度总览.md` 不提交，仍留在工作树。父仓非代码文件若开工前已有他人改动，只提交本批差异。`observe_bh3_kevin_combat.py` 的修正依附在原作者未提交的版本上（HEAD 中没有被删的绑定），因此不提交，修正留在工作树，需原作者提交其版本时一并带上。
  - Obsidian 两段（第一阶段、收尾续修）；3 个开工前已有他人改动的文件只提交本批差异。
- 源码已冻结，各 spec 的 `after_summary.tsv` 已按 Build_R23 时的文件刷新。

剩余验收（未运行，不签通过）：
- 真实 RHI 与画面：PlayerCombo 生产冒烟 7 例与 Kevin 冒烟、FX 单机与晚加入、TurnBack、Boss 出场与 BT 连续出招、留场的 Montage／位移／FX 表现、相机画面。建议最小范围：一次真实 RHI Editor 会话跑现有 PlayerCombo 生产冒烟 7 例，再由用户人工 PIE 看 FX 与换人画面；预计新增约 32MiB 驱动缓存、约 5MB 着色器缓存与约 2MB 测试输出，共约 40MB，当前余量可容纳，用途需用户批准。
- 联机未覆盖：客户端移动与攻击（需真实输入）、预测连段的纠正重放、死亡与重生、LocalPredicted 续放能力在 UnPossess 后的预测键行为、FX 晚加入。
- 业务缺口：玩家改键界面（换人键已有 PlayerMappable 名，见「收尾」）；进退场 GA 与 Montage（缺省跳过）；需要留场的技能把 AvatarExitPolicy 改为 ContinueInBackground（现有 7 个 GA 都是 Cancel）。
- 既有失败（与本批无关，未修）：`Camera.ModeOwnershipAndAvatarReceiver`、`Input.MovementOrigin.NativeBirthFirstDigitalPress`、`Movement.Locomotion.InputConsumer.FailedRequestRecovery`。

## 额度

- 用户 11-03 批准新增 96MiB，第 5 步后再追加 64MiB：总额度 2315255808B（2GiB＋167772160B）。
- 当前实测（Test_R15 后）：7 根内 2134734765B（峰值 2134757086B）＋域外累计 52157420B＋R1 预留 42987054B；余 85376569B（约 81.4MiB）。第 6、7 步共用约 6.4MiB，没有做 Editor 资产制作。
- Obsidian 步骤之后：`Saved/Kiro` 内新增／改写的前像与脚本共 888297B（按整文件计上界），无构建或测试；余约 84.5MB（约 80.6MiB）。
- 收尾（Test_R19 后）：7 根内 2141176586B（峰值 2141199534B）＋域外累计 52702280B＋R1 预留 42987054B；余 78389888B（约 74.8MiB）。收尾 4 次构建、5 次测试与证据共用约 6.1MB。
- 收尾续（Test_R22 后）：7 根内 2150935216B（峰值 2150957029B）＋域外累计 52766412B＋R1 预留 42987054B；余 68567126B（约 65.4MiB）。Build_R20～R22 与 Test_R20～R22 共用约 9.8MB。
- 换人键（Test_R23c 后）：7 根内 2156766739B（峰值 2156789664B）＋域外累计约 52.9MB＋R1 预留 42987054B；余约 62.6MB（约 59.7MiB）。
- 历史（Test_R12 后）：7 根内 2128963922B（峰值 2128975634B）＋域外累计 51253859B＋R1 预留 42987054B；按新额度余 92050973B（约 87.8MiB）。
  - 第 5 步 Build_R11 新增文件触发 10 个 unity 文件重编，7 根内增加约 27.4MB；之后增量构建约 0.2MB、每次 NullRHI 测试约 1.3MB。追加的 64MiB 用于第 6、7 步的构建、测试与第 6 步 Editor（NullRHI）资产制作。
  - 域外累计＝Verify_R1 Test_R4 后的 50645591B＋源码／文档正增上界（`Verify_R2/outside_since_r4_after_t12.json`）＋Verify_R2 第 1～3 步各窗 240000B＋第 4、5 步各窗实测正增。
  - Build_R7 的 `outside_growth.json` 记 215MB，是 Build_R6 链接失败删除两个 pdb 后重建（before 为空）；与 R6 前尺寸比两者都变小，净增按 0 计。
  - Verify_R1 Test_R4 的域外正增主要是 NVIDIA 驱动缓存的两个 16MiB `.nvph` 文件；驱动缓存是共享缓存，不删除。
- 真实 RHI 不在本额度内：首次可能再增加约 32MiB 驱动缓存和约 5MB 着色器缓存，需另批。

## 用户决定（2026-11-02）

1. 时机：统筹转达的较新指示取代原"等当前批次交付"：「当前最小点完成之后，需要先让kiro完成他那边的任务再执行后续的，因为代码要大整理一次」。各步的写集与窗口由统筹授权。
2. 编译与受影响测试由 Kiro 自行执行，但只在统筹设定的验证窗口内；每次编译前在聊天告知，并检查内存、磁盘与既有新增额度。测试用 UE 也由 Kiro 自行启动和正常退出，只处理自己启动的实例。
3. 换人功能保留，允许多人同时在场，具体行为见下节。
4. 全部整改完成后，更新 Obsidian（F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划）中受影响的模块笔记。

## 换人续放（新行为）

第 6 步之前的实现与目标相反（已按下述目标改写，实现见第 6 步）：
- SwitchToSlot 在交出控制前调用 TryExitAbilitiesForAvatarSwitch，取消旧角色的能力。GA 的 AvatarExitPolicy 默认为 Cancel，7 个 GA 资产都没有改这项配置。
- DeactivateSlot 会立即隐藏旧角色、关闭碰撞、停住并 DisableMovement。

目标行为：
- **换出时，每个能力自己决定取消还是放完。**
  - GA 基类提供可在蓝图覆盖的事件 OnAvatarSwitchOut(Context)，返回本次的处理方式；默认实现读 AvatarExitPolicy。
  - Context 至少包含目标槽位和切换来源。
  - 换出时向旧角色补发一次真实的输入释放，并发出"失去控制"通知；切回时发出"重新获得控制"通知。长按蓄力等情况由蓝图处理。
- **留场角色不能受击。** 留场指已经被换下、仍在放技能的角色。
  - 给它挂离场标签：近战检测跳过它，伤害 GE 因该标签被拒绝。
  - 保留地面和场景碰撞，保证技能位移正常。
  - 它放出的技能照常命中、照常结算伤害。
- **可以切回留场角色，也可以切到第三个角色**，多人同时在场。
- **切回仍在留场的角色时：**
  - 控制权和镜头立即交给它；
  - 它的新技能和移动输入要等技能放完后才生效，现有输入缓冲窗口照常起作用；
  - 去掉它的离场标签，恢复可受击；
  - 不播进场动作，取消它尚未开始的退场；
  - 被换下的角色按同样规则处理：有技能就先放完再退场，期间不能受击。
- **进场和退场动作**由 GameplayEvent 触发的进场 GA、退场 GA 承载。
  - Montage、时长、能否被打断、进场位置都由各角色的 GA 和 Montage 决定；没有授予这两个 GA 时直接跳过。
  - 流程：
    1. 旧角色的续放能力结束（没有续放能力就立即进入下一步）；
    2. 旧角色执行退场 GA，结束后隐藏并停用移动；
    3. 新角色先显示，再执行进场 GA。控制权在切换开始时交接。
- 实现放在第 6 步 teams-squad-switch-linger。

## 执行方式与 Spec 索引

用户决定（2026-11-02）：
- 拆成 7 个 Kiro Spec，由 Kiro 在本会话内按顺序执行，不启用子代理；
- Kiro 自己编译、跑测试，也自己启动和正常退出测试用 UE 实例，不碰用户的编辑器。

每个 spec 实现冻结后，在统筹设定的验证窗口编译、测试，通过后才进入下一个；进度以各 spec 的 tasks.md 勾选状态为准。

| 顺序 | Spec | 内容（问题编号） | 状态 |
| --- | --- | --- | --- |
| 1 | [abilitysystem-redundancy-cleanup](../../.kiro/specs/abilitysystem-redundancy-cleanup/tasks.md) | 规范澄清；6；5 的 PlayerCombo 重验与 StartStep 部分；10 的过期注释；11 的 MeleeTrace 部分 | 源码完成，NullRHI 已测（见现状）；任务 6 已完成（见收尾）；生产冒烟未验 |
| 2 | [abilitysystem-input-request](../../.kiro/specs/abilitysystem-input-request/tasks.md) | 7；5 的 Hero 重验（自第 1 步移入）；首击 B | 源码完成，NullRHI 已测（见现状）；生产冒烟与 PIE 未验 |
| 3 | [fx-montage-publication-ownership](../../.kiro/specs/fx-montage-publication-ownership/tasks.md) | 2 | 源码完成，NullRHI 已测（见现状）；Editor 蓝图核对已完成（见收尾）；FX 的 PIE、联机未验 |
| 4 | [abilitysystem-activation-lifecycle](../../.kiro/specs/abilitysystem-activation-lifecycle/tasks.md) | 1；8；5 的段寿命部分；10 的 GA 与 ASC 部分；9；11 的 CMC 部分（后三项自第 1 步移入） | 源码完成，NullRHI 已测（见第 4 步）；PIE、联机、N3 纠正重放未验 |
| 5 | [combatants-avatar-binding](../../.kiro/specs/combatants-avatar-binding/tasks.md) | 3；4 | 源码完成，NullRHI 已测（见第 5 步）；NullRHI 监听服务器 PIE 覆盖出生与换人（见收尾）；移动、攻击、死亡与重生未验 |
| 6 | [teams-squad-switch-linger](../../.kiro/specs/teams-squad-switch-linger/tasks.md) | 换人续放（新行为） | 源码完成，NullRHI 已测；监听服务器 PIE 全部通过（Test_R22／R23）；换人键默认 Z／C 已接；三项玩法取舍待用户；进退场资产缺省跳过 |
| 7 | [abilitysystem-healthset-repnotify](../../.kiro/specs/abilitysystem-healthset-repnotify/tasks.md) | 12；3 的属性反算部分 | 复现完成，保留分类帧（已定案）；反算已迁出；NullRHI 已测；联机伤害／上限／破韧一致（见收尾）；死亡联机未验 |

顺序说明：FX 关闭（第 3 步）排在激活/终止状态机（第 4 步）之前。这样第 4 步重写激活与终止时，不需要再维护 FX 关闭义务。

全部完成后：
- 更新 Obsidian 受影响的模块笔记；
- Git 提交由统筹协调：父工程和 Source/GGYGO 子仓分别提交，只 stage 已验收的文件。

各 spec 的 design 依据 2026-11-02 的静态审核，第一项任务都是按当时的源码重新核对。

## 问题清单

依据 2026-11-02 的静态审核，行号是当时的版本，开工时按当前源码重新核对。

1. **GA／ASC 自建激活与终止状态机，与 GAS 原生寿命并行。**
   - 位置：GGYGOGameplayAbility.cpp:34-972、GGYGOGameplayAbility.h:719-752、GGYGOAbilitySystemComponent.cpp:1476-1805 与 4270-4560。
   - 原生 EndAbility／CancelAbility 已在 ScopeLock 期间延迟执行（UE_5.8 GameplayAbility.cpp:745-748、806-809）。
   - 完成通知只有 BTTask_GGYGOActivateAbility.cpp:153-202 在用，改用原生 OnAbilityEnded。
   - 保留：
     - GA 内一个整数激活序号，因为 ServerOnly 能力的预测键为 0；
     - 旧激活的迟到回调不能作用到后继激活；
     - BT Abort 不强制取消正在执行的能力。
2. **FX 关闭义务层层携带，外加事后扫描兜底。**
   - 位置：ASC.h:1176-1190 的 15 个 *WithRetirementOutput 包装；ASC.cpp:799-823 与 1020-1046 的扫描。
   - lease 只由持有者关闭（MontageActionResources.cpp:266-296 的 ReleaseFX）。
   - MontageFXState 的复制迁到 FX 自己的组件；移动特效不再经过 ASC（ASC.cpp:932-988）。
   - 保留：晚加入／重获相关性时的剩余 FX 与 Age seek；结束窗口不补播；Normal／Abort 两种停止方式；专服也要关闭发布。
3. **拆分 ASC。**
   - 输入缓冲（ASC.cpp:1857-2949）改为 ASC 私有协作者。
   - FX、绑定、播放见问题 2、4、8。
   - 属性反算保留（修复清单决定 #2）。
4. **绑定链与三份订阅样板。**
   - 位置：CombatantState.cpp:69-101、291、479-769，到 ASC.cpp:5001-5541。
   - 三份本地 ASC 订阅合并为 PawnExtension 提供的一个订阅类型：
     - Hero.cpp:99-148、1773-2011；
     - CMC.cpp:5664-5905；
     - Health.cpp:23-39、113-436。
   - 三个 Try 入口合一；去掉从步骤历史回捞提交结果；按换人续放需求去掉"换人前退出能力"。
5. **没有外调的重复核验。**
   - 位置：Hero.cpp:1561-1588、1642-1659；PlayerCombo.cpp:1657-1664、1889-1891；Montage 回调的四层认证。
   - 改为以 Task 寿命作为段寿命；StartStep 拆成"读运行输入 → 释放旧段 → 起新段"三步。
   - PlayerCombo 部分已在第 1 步实现，Hero 部分在第 2 步实现，均已过 NullRHI 测试。
6. **静态配置在运行期反复全量校验。**
   - 位置：PlayerCombo.cpp:675、745-747、754-757、828、约 1597-1653、2519、约 2533-2570。
   - 批次 1 改为授予实例首次准入时解析、只缓存成功结果的预备配置，Body 取快照，StartStep 只读它；命中时只核返回 Spec 的 Def 与伤害键冲突（见批次 1 第 1 项）。
   - 起草时设想的"Builder 蓝图扩展只能写 SetByCaller 和 Tag"未纳入第 1 步：保留的命中时检查已覆盖扩展替换 Def 的情形；限制扩展写权会改变蓝图接口行为，需要时再交用户决定。
7. **输入请求的 Hero／ASC 双账本与三重失效。**
   - 位置：Hero 的五层寿命对象；ASC.cpp:1894-1928、2075-2076、2578、2641-2662、2923-2947。
   - 保留：缓冲窗口内被组阻塞后的排队重试；qualified Held；先释放再按下（决定 #4）；ProcessAbilityInput 作为唯一消费者。
8. **Montage 播放五层包装、三套身份。**
   - 位置：Task.cpp 约 843、911、1128-1130；ASC.cpp:569-654、1059、1285-1453；GA 终止时捕获播放所有权（GA.cpp:200、601）。
   - 合并为 MontageInstanceId 加激活序号。
   - Legacy 分支（ASC.cpp:1291-1298）先在 Editor 里核实 ABP 父类再退役。
9. **玩家和 Boss 两套 Montage 动作资源。**
   - Boss 改用 FGGYGOMontageActionResources（BossMeleeAbility.cpp:33-66、248-330、740-760）。
   - 保留 Mesh Tick 的保存与恢复。
   - 移入第 4 步：该步重写共享资源与 Boss 的身份／回调模型；Boss 测试依赖其 protected 接口与精确日志。第 1 步只把 Boss 配置收敛为每次激活解析一次；ActionSet 全表校验改在 BossState 采纳 Definition 时做一次。
10. **主流程里的测试钩子与过期注释。**
    - 位置：GA.cpp:1698-1816；ASC.cpp:3207-3374；MontageGuardAnimInstance.h:15。
    - MontageGuard 注释已在第 1 步改写；GA 钩子与 ASC 组准入测试日志在第 4 步处理。
11. **低影响的转发。**
    - CMC.cpp:2046-2430 中两参的 BeginMontageActionMotion 与带 Facing 版本合一：移入第 4 步。
    - MeleeTrace 的 Legacy Begin/EndTraceWindow（.h:116-121）先在 Editor 核实蓝图和 Notify 是否在用，再退役：第 1 步任务 6，需验证窗口。
12. **HealthSet 的 RepNotify 分类帧**（HealthSet.cpp:43-217、994-1166）。
    - 先做客户端受击与 MaxHealth 下降的最小复现，再决定是否改用 Lyra 做法。

## 规范澄清

第 1 步已原位写入 [CodeConventions](../Architecture/CodeConventions.md)：外调正向清单、后置检查举证、ABA 原生寿命与身份合并、预备配置、计数耗尽、结果枚举、"应主动退役的模式"。预备配置写为"有明确来源、寿命和清理点"，PlayerCombo 采用授予实例寿命（批次 1 第 1 项）。

## 必须保留的设计

- 技能段首方向经 TargetData 和 CMC SavedMove 上报，纠正重放时复用原 basis。
- Montage FX 复制状态与 Age seek。
- 输入缓冲窗口、组阻塞后的排队重试、qualified Held 与释放屏障。
- 属性反算写 Current；Montage 完成与位移完成两个独立事实。
- CMC 作为唯一位移权威。
- 在真实外调之后的重验。

## 验收标准

- **每批**：
  - 受影响的模块编译通过；
  - 保留 ABA 外部契约测试：旧回调不作用到后继，旧调用栈不清理后继资源；
  - 内部 serial／receipt／phase 断言随对应机制一起删改；
  - 不降低断言，不排除失败场景，失败证据保留。
- **运行**：
  - 普攻三段、技能、TurnBack、Boss 招式、FX 晚加入照常；
  - 换人续放各条逐项验证；
  - 最小联机：Authority 与远端 SimulatedProxy 按同一 PlayerState 配对，双方可见。
- **文档**：Obsidian 只更新受影响模块，源码或资产尚未验证的内容不写成"已实现"。
