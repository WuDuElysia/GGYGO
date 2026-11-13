# 代码整改（CR-R7 扩展）与换人续放

更新：2026-11-12。需求状态和占用以[看板](../Coordination/Board.md)为准，剩余工作已交给 Codex，见 [Codex 交接](../Coordination/Handover_Codex.md)。过程历史以 Git 为准。

## 目标

- 去掉 GA／ASC 里与 GAS 原生寿命并行的自建机制、没有外调的重复核验和层层携带的关闭义务，玩家可感知的行为不变。共 12 个问题，拆成 7 个 spec 依次做完。
- 换人续放：换下的角色可以把技能放完再退场，多人可同时在场。
- 换人相关的玩法：死亡自动换人、换人冷却、换人键和键盘改键。

## 用户决定（仍有效）

- 11-02：换人功能保留，允许多人同时在场。
- 11-03：首击不等移动键，移动来源还没有物理按键证明时按角色当前朝向立即起段；换人键默认 Z 上一个、C 下一个，可改键。
- 11-04：
  - 切回时续放能力照常收键；不可取消的能力改为留场放完，不再拒绝换人；开局第一名队员不发 SwitchIn。
  - 玩家换人冷却 0.5 秒（整队共用，只限玩家请求，从替换在场队员的换人成功起算）。
  - 出战队员倒下动作播完后自动切到下一个存活队员，倒下期间不能手动切；全员倒下时保持现状。
  - 7 个 GA 维持换下即取消；进退场资产以后做（缺省时跳过）；换人不配手柄键；做键盘改键界面。
- 11-10：死亡结束后的 Pawn 去留改由共享角色蓝图决定（选 B，已实现并验证，见下文）。
- 技术决定（已定案）：HealthSet 保留分类帧。原因是 Lyra 做法在服务器（含 listen 主机）上，持续 GE 下调 MaxHealth 时不广播 MaxHealthChanged。

## 方案要点

按 spec 列出留下来的接口和约束，细节见各 spec 的 design.md。

| 顺序 | Spec | 要点 |
| --- | --- | --- |
| 1 | [abilitysystem-redundancy-cleanup](../../.kiro/specs/abilitysystem-redundancy-cleanup/tasks.md) | PlayerCombo 的段声明和伤害 GE 在授予实例首次准入时解析，只缓存成功结果；CDO 上的纯查询每次解析、不缓存。运行期改配置的子类调 `InvalidatePreparedConfiguration()`。后果：PIE 中改所引用的 Montage／GE 要重开 PIE 才生效。BossState 采纳 Definition 时一次校验全部阶段的 ActionSet。MeleeTrace 的 Legacy 窗口和 `OnMeleeHit` 已删除。 |
| 2 | [abilitysystem-input-request](../../.kiro/specs/abilitysystem-input-request/tasks.md) | ASC 的请求记录只靠 Revision 加记录是否存在判断有效；新增 `EndAbilityInputRequestsFromSource`，Hero 会话退役或关联变化时按来源一次结束全部请求。首击不等移动键（见用户决定）。 |
| 3 | [fx-montage-publication-ownership](../../.kiro/specs/fx-montage-publication-ownership/tasks.md) | FX 发布只由 lease 持有者关闭。`UGGYGOMontageFXReplicationComponent` 挂在 CombatantState 上，提供 `PublishMontageFX`／`PublishLocomotionFX`；ASC 不再是 FX 宿主。找不到宿主时发布方明确拒绝。 |
| 4 | [abilitysystem-activation-lifecycle](../../.kiro/specs/abilitysystem-activation-lifecycle/tasks.md) | GA 在原生 PreActivate 签发 `FActivationProof`，原生结束广播前退役；`IsActivationCurrent` 判断同一激活。`EndAbility` 先做 `CleanupAbilityResourcesForTermination` 再走原生 End；`RequestAbilityEnd／Cancel` 返回 Accepted／NotCurrent／NotCancelable，ScopeLock 期间延后且执行时重核原激活。BT 和 Editor 观察订阅原生 `OnAbilityEnded`。Montage 只经 `PlayAbilityMontage`，只支持 Guard AnimInstance。BossMelee 改用共享 `FGGYGOMontageActionResources`。 |
| 5 | [combatants-avatar-binding](../../.kiro/specs/combatants-avatar-binding/tasks.md) | `AGGYGOCombatantState::BindAvatar` 先释放旧 Avatar 再 `InitAbilityActorInfo`；Released 在解除 ActorInfo 之后广播（与 Lyra 一致）。本地 ASC 订阅统一为 PawnExtension 的 `FGGYGOLocalASCSubscription`。ASC 拆出输入缓冲 `FGGYGOAbilityInputBuffer` 和分段输入路由 `FGGYGOAbilityStepInputRouter`。 |
| 6 | [teams-squad-switch-linger](../../.kiro/specs/teams-squad-switch-linger/tasks.md) | 见下面「换人续放」。 |
| 7 | [abilitysystem-healthset-repnotify](../../.kiro/specs/abilitysystem-healthset-repnotify/tasks.md) | 保留分类帧（见用户决定）；属性反算迁到 `GGYGOAttributeBase::CalculateBaseForCurrent`，ASC 不再提供反算入口。 |

规范澄清已写入 [CodeConventions](../Rules/CodeConventions.md)：外调正向清单、后置检查举证、原生寿命与身份合并、预备配置要有明确来源／寿命／清理点。

### 换人续放

- 能力接口：GA 基类 `OnAvatarSwitchOut(FGGYGOSwitchContext)`（BlueprintNativeEvent，默认读 `AvatarExitPolicy`：Cancel 取消，ContinueInBackground 留场）；`OnOwnerControlLost`／`OnOwnerControlRegained` 蓝图事件。
- Squad（服务器）状态：Benched／Active／Lingering／Exiting。留场队员可见、有碰撞，打开 `bRunPhysicsWithNoController` 让技能位移继续；挂复制的 `State.OffField` 和仅服务器的 `Gameplay.Damage.Immunity`，MeleeTrace 跳过它，它放出的技能照常结算。切回留场队员时挂 `State.SwitchReturnPending`，只拦输入缓冲发起的新激活，被拦的按下在缓冲窗口内重试一次。
- 网络入口：`ServerRequestSwitchToSlot`、`ServerRequestSwitchToAdjacentSlot(±1)`（服务器按权威出战序号循环，跳过死亡和无实体位置）。
- 待命队员：`AGGYGOCharacterBase::SetReplicatedActorEnableCollision` 复制碰撞开关；Mesh `bNoSkeletonUpdate=true` 停骨架更新，不关组件 Tick。
- 相机：`AGGYGOPlayerCameraManager` 在 Running 时接受当前附身 Pawn 的重新准入；ViewTarget 换到尚未准入的 GG 相机时暂停发布，等它 Ready。
- 换人键归 Controller（`SquadSwitchInputMapping`、`SwitchToPreviousMemberAction`、`SwitchToNextMemberAction` 和优先级），不随 Hero 输入会话退役；三项都不配表示不提供换人键，只配一部分报 Error。
- 冷却：`SwitchCooldownSeconds`（`DefaultGame.ini` 中 0.5），`GetSwitchCooldownRemaining()` 只读。
- 死亡：C++ `UGGYGODeathAbility`（Event.Death 触发、ServerInitiated）；Pyrios 用 `GA_Pyrios_Death`＋`AM_Pyrios_Death`。死亡自动替补由共享 `BP_PlayerState` 发起：C++ 只发布 `OnActiveMemberDeathFinished(Slot, Avatar)`，蓝图在同一次广播里调 `RequestNextAfterActiveMemberDeath`（蓝图分层 B08，见[蓝图分层收尾](blueprint_layering_followups.md)）。
- 改键：生产 Controller 用共享 UMG `WBP_KeySettings`（蓝图分层 B06）；`IMC_Default` 的 WASD、Shift、Ctrl、空格、鼠标左键和 `IMC_Squad` 可改键。
- 进退场：`UGGYGOSquadTransitionAbility` 由 GameplayEvent 触发，播配置的 Montage；没有授予时跳过。

### 必须保留的设计

- 技能段首方向经 TargetData 和 CMC SavedMove 上报，纠正重放时复用原 basis。
- Montage FX 复制状态与 Age seek；晚加入／重获相关性时补剩余 FX，结束窗口不补播。
- 输入缓冲窗口、组阻塞后的排队重试、qualified Held 与释放屏障。
- 属性反算写 Current；Montage 完成与位移完成是两个独立事实。
- CMC 是唯一位移权威；在真实外调之后才重验。

## 当前状态

- 7 步源码全部完成并已编译，相关自动化已有通过记录（含 SquadSwitch 8 例、HealthSet 复现回归）；各报告中的原失败保留，完整验收范围见下表，不能合写为七份 spec 全部验收。
- 真实 RHI 已验证：
  - 普攻生产冒烟 24 项中 22 项通过，2 例 PoseFailure 按约定保留失败（见 [normal01_first_strike](normal01_first_strike.md)）。
  - 联机（监听服务器＋1 客户端）换人：客户端 RPC 和 Z／C 按键换人、冷却、改键生效、再次附身后双端都能移动、普攻激活、死亡自动换人、生命／上限／破韧复制一致。
  - 改键页面和死亡自动替补（蓝图分层 B06、B08）已完成，见[蓝图分层收尾](blueprint_layering_followups.md)。
  - 独立进程最小联机已完成：原动作自然收尾、纠正重放、Initial 取消、FX 首次活动相关性／闭窗首次相关性／同连接重获，以及活尾实拍。最终编译与 17 项相关回归通过，边界和证据见[最小联机](minimal_multiplayer.md)。
  - 角色受光与阴影已完成，见下节。
- 原统筹待修问题里已关闭的：再次附身后客户端不能移动（CMC owner-sync 修正）；Locomotion 输入测试留住测试世界；冷会话首击因 FX 材质未就绪失败（首击等资源就绪）；角色阴影捕获在 PIE 结束时留住世界；倒下画面的阴影条纹。
- 七份 spec 的勾选和下表按当前交付记录回写；首次回写只读取既有证据，后续补齐的 PIE 退出与 Editor 动画组验证分别见下节。部分完成与未覆盖项分别保留。

| Spec | 已完成范围 | 未完成或未覆盖 |
| --- | --- | --- |
| 1 冗余清理 | 源码、消费者核查及约定自动化完成；普攻生产冒烟与 Kevin 单机战斗已跑 | 冒烟两项 PoseFailure 的原 Fail 按约定保留；实体设备与完整网络矩阵不在已验范围 |
| 2 输入请求 | 源码及相关回归完成；组占用后一次重试及过原截止不重试新增四项机制＋两项生产输入链 PIE 通过，既有冒烟、改键及嵌套来源证据保持 | 任务 5 保留未勾：预输入待用户决定；实体设备／焦点丢失未覆盖。PIE 使用临时占组夹具，不代表默认授予新增第二个玩家能力 |
| 3 FX 发布 | 发布所有权与相关回归完成；普攻出现／自然清理、最小联机及活尾已验 | 任务 6 部分完成：TurnBack 准确烟雾来源未确定，真实打断 Abort 画面未验；用户视听返修由原需求跟进 |
| 4 激活生命周期 | 源码、核心回归、基本动作链、纠正重放与最小联机已交付；完整 Editor 动画组 9／9 通过，任务 8 验收缺口已补齐 | 玩法／镜头待定项与原失败保留；本轮仅补 NullRHI 自动化，不新增 Cook／完整网络矩阵或视觉验收 |
| 5 Avatar 绑定 | 绑定回归、真实 RHI 出生／移动／攻击／重新附身／死亡替补及 Boss 单机出场已验 | 任务 6 部分完成：项目没有复活流程；独立第三端观察换人未覆盖，普攻／FX 观察端结果不代签换人 |
| 6 换人续放 | 约定测试编队范围内的编译、自动化与真实 RHI 联机已验；共享 UMG 改键和蓝图死亡替补已交付 | 两份 Pyrios 实例与夹具续放 GA 不代验生产续放技能配置；进退场资产缺省按决定跳过，实体设备手感未验 |
| 7 HealthSet | 保留分类帧已定案；反算迁移、回归及真实 RHI 扣血／上限／破韧的双端数值和广播已验 | 任务 4 部分完成：死亡替补已验，但死者的双端 Health／DeathState／死亡广播未逐边沿配对；单机受击／破韧／死亡表现缺完整专项证据 |

### 输入请求组占用与截止（本批验收完成）

2026-11-13 共享增量构建通过，四项机制测试与两项 D3D12 PIE 全部 Success，零测试错误。机制测试覆盖一次唤醒只消费一次、再次 Queued 失败保留原请求身份／截止，以及组释放前和消费前超过原截止均不激活；释放重按正控通过。证据：[构建日志](../../Saved/Codex/HealthAcceptance_20261113/shared_build.log)、[测试报告](../../Saved/Codex/InputQueuedDeadline_20261113/Run_R1/Automation/index.json)、[运行日志](../../Saved/Codex/InputQueuedDeadline_20261113/Run_R1/editor.log)。本批只增加测试与记录，未发现需修改的生产缺陷。

PIE 保留默认 Pyrios、普攻输入与 Queued 组规则，仅临时授予无输入 Tag 的 GAS 占用夹具。左键经生产 `PC.InputKey → Hero → PostProcessInput → ASC`：截止前的原请求只入场一次并自然结束；过期后释放组仍零激活，释放重按才正常入场。Editor 正常退出，测试中一条 `r.MotionVectorSimulation` 引擎警告和启动阶段 13 条 `Condition failed` 保留。这是生产输入链的受控占组证据，不签默认多能力玩法、E／R／F、连段预输入、实体设备／外部失焦、联机、Cook 或视听验收；完整边界见 [input-request 任务 5](../../.kiro/specs/abilitysystem-input-request/tasks.md)。

### PIE 退出输入映射清理（已完成）

旧项已由现有归还链解决，本次未发现需要新增修复的生产缺陷。`UGGYGOLocalPlayer::PlayerRemoved` 在子系统反初始化前通知映射拥有者；`AGGYGOPlayerController::Destroyed` 在原生清空 PlayerInput 前通知。Controller 归还 `IMC_Squad`，Hero 归还自身的 `IMC_Default`／`IMC_MouseLook`，均先摘除本次注册及订阅，再向原输入对象移除自己的计数。Controller 蓝图不再重复注册 Hero 的两份映射；没有使用 `ClearAllMappings` 或关闭诊断。

2026-11-13 在生产 `L_Movement_Test`／`BP_PC_Pyrios` 上完成两轮单客户端 PIE 启停：每轮先确认三个映射实际应用，再在三个原生移除回调中通过既有只读装配桥核对原 PC／PlayerInput，并核对原 LocalPlayer 子系统仍有效；每次对应映射已移除，最终三项均不再应用。两轮均完整退出，Editor 正常退出，未出现旧泄漏 Warning。证据：[运行日志](../../Saved/Codex/InputMappingCleanup_20261113/editor.log)、[观察结果](../../Saved/Codex/InputMappingCleanup_20261113/observations.json)；观察脚本及三次 Python 接口适配失败保留在同目录。

本次只增加退出验证和文档，不改生产代码或资产，不重复编译。验证使用 NullRHI，不代验画面、实体输入、独立进程联机或 Cook；最新 Kevin 双端日志无旧 Warning 仅作旁证。日志中的启动阶段 `Condition failed` 和两轮 NullRHI 的 R32f 不支持错误原样保留，不声称整宿主零错误或渲染通过。

### 激活生命周期的 Editor 动画组（已完成）

完整过滤器 `GGYGO.Editor.Animation` 已于 2026-11-13 在自有 NullRHI Editor 中运行，[原生报告](../../Saved/Codex/ActivationLifecycle_EditorAnimation_20261113/Automation/index.json)记录 9 项 Success、零错误／警告／未运行，[运行日志](../../Saved/Codex/ActivationLifecycle_EditorAnimation_20261113/editor.log)记录正常退出，进程退出码 0。测试只修改自建 `/Temp` 动画、Skeleton、Montage／ABP 及独立 Saved JSON 样本，不保存项目资产；本轮无生产源码修改，复用现有 DLL。启动阶段仍有 13 条 `LogAutomationTest: Error: Condition failed`，发生在测试开始前，来源未在本需求排查，不能把本组通过解释为整个启动日志无错误。

### 角色受光与阴影（已完成）

结论：倒下和转身时地面的放射条纹是 VSM 缓存残影，已修；换人瞬间的拖影是换人时相机跳变造成的运动模糊，属正常表现；换人稳定后的阴影参数和单机一致。证据 `.agents/tasks/requirements-closeout/evidence/I10.md`（只在本机）。

- 原因：Pyrios Mesh 的包围盒由物理资产算出，只覆盖躯干；武器、斗篷、小腿在动画中远超出去。VSM 按图元包围盒决定哪些缓存页要重画，包围盒外的旧姿态阴影留在地面形成条纹。
- 改动和接口：
  - `BP_PC_Pyrios` 的 Mesh `BoundsScale` 为 11（写入脚本 `AAADocs/Scripts/set_pyrios_mesh_bounds_scale.py`）。整段倒下 Montage 所需倍率最大约 9.5，11 留约 16% 余量。物理资产和骨骼网格是本地导入资产、不入库，所以不改它们。
  - `FGGYGOCharacterShadowCapture`：对象阴影宽度 `ObjectWidth = 2 × (SphereRadius / BoundsScale + ObjectMarginCm)`，扩大包围盒不会稀释对象阴影图分辨率；`BoundsScale <= 0` 时宽度为 0，被原有校验拒绝。
  - 联机测试 `GGYGO.Teams.SquadSwitch.ListenServerClientRequest` 在真实 RHI 且给了 `-GGYGOCaptureDir` 时，死亡自动换人后加取稳定帧和关运动模糊帧，结束时恢复 `r.MotionBlurQuality`。
- 仍有效的约束：
  - 新增动作如果让武器或斗篷伸得更远，要重新逐帧跟踪所需倍率；以后若把物理资产入库，可以加不参与碰撞的包围体，再把倍率降回去。
  - `BP_PC_Pyrios` 在 BeginPlay 按 Actor Tag `GGYGO.KeyLight` 找本 World 里唯一的 DirectionalLight 作为角色主灯，找不到就停用角色灯宿主并打印"主灯绑定拒绝"。`L_Movement_Test` 和后续交付的 `L_KevinBoss_P3` 均已核对唯一主灯；P3 照明与投影证据见 [Kevin 交付](kevin_boss_assembly.md)，不扩推其它地图。
- 验证级别：已编译；已测试（`GGYGO.Rendering` 4 例、`GGYGO.Teams.SquadSwitch` 8 例）；已在 UE 里运行（真实 D3D12 单机正背机位）；已联机验证（客户端倒下帧地面无条纹，稳定帧对象阴影宽度与单机一致）。
- 未做：`BoundsScale` 11 的 GPU／VSM 开销没测；修后单机倒下没有单独重拍。
- 正背对照里与原图 `AAADocs/Assets/Pyrios/Rendering/References/20261009_Pyrios_*.png` 的差异不属于阴影问题，是否另开需求由用户决定：胸口光球偏暗、蓝色手臂发光偏弱、背面头发偏灰紫偏亮、斗篷没有蓝色渐变且金色细线显示为橙红（斗篷只读暂挂）。

## 死亡结束后的 Pawn 处理

- HealthComponent 仍唯一持有死亡阶段并广播 `OnDeathFinished`。CharacterBase 保留原生 `SetTimerForNextTick`，下一帧才调用 `K2_HandleDeathFinished()`；自动替补仍在原死亡广播内同步完成。没有新增死亡状态、计时器协议或替补策略。
- `K2_HandleDeathFinished()` 返回 true 表示蓝图已处理，可以选择保留 Pawn；未覆盖或返回 false 会输出含 Pawn 路径的 Error，不执行默认销毁。`UninitAndDestroy()` 是供蓝图选择的受保护清理原语：各端仅释放本 Pawn 仍持有的 ASC 关联并隐藏，服务器另行解除控制并沿用 0.1 秒 LifeSpan。选销毁的执行时点仍晚于死亡结束及自动替补广播。
- `/Game/BP/Character/BP_Character`、`BP_HeroCharacter`、`BP_BossCharacter` 分别继承三个原生角色分支，图中显式调用 `UninitAndDestroy` 后返回 true。既有 `BP_Enemy`／`BP_BaseCharacter`、`BP_PC_Pyrios`、`BP_Boss_Test` 分别继承对应共享模板；对象原有组件、变量和业务图保持。后续角色应继承相应模板，或明确覆盖死亡处理图。制作／读回入口为 [wire_character_death_policy.py](../Scripts/wire_character_death_policy.py)。
- 已编译，10 项相关回归通过：两项 `GGYGO.Character.DeathPolicy` 验证广播期间不清理、下一帧选择、显式保留、未配置诊断、客户端不发起销毁和生产 Pyrios 蓝图入口；`GGYGO.Teams.SquadSwitch` 七项单机与一项 D3D12 listen-server 用例通过，含死亡自动替补、后台死亡不切换和无人存活不假成功。
- Teams 原会话已评审本次接口差分和受影响调用链，确认同栈替补、下一帧蓝图处理、ASC 原 Avatar 释放边界及客户端权限保持，未发现阻塞问题。
- 证据：[初次构建](../../Saved/Codex/CharacterDeathPolicy_20261111/build.log)、[夹具修复后的共同增量构建](../../Saved/Codex/I22_20261111/build.log)、[单机七项与首轮专项夹具失败](../../Saved/Codex/CharacterDeathPolicy_20261111/tests.log)、[专项两项及 D3D12 联机通过](../../Saved/Codex/CharacterDeathPolicy_20261111/rhi2.log)、[全部共享图与继承的保存后冷读回](../../Saved/Codex/CharacterDeathPolicy_20261111/final_readback.log)。专项夹具修复仅补 `InitializeActorsForPlay`，不放宽断言。NullRHI 联机在攻击步骤因必需渲染资源不可用超时，未把它当作联机通过；D3D12 已走通完整用例。
- 未验证独立进程客户端、Cook／打包，以及选择保留 Pawn 后的复活玩法。原有启动阶段 `LogAutomationTest: Error: Condition failed` 不属于这些专项叶，日志保留，未在本需求排查。

## 消息路由与 SyncMarker 工具

- 消息路由在遍历父 Tag 时，按当前 Tag 删除类型已失效的监听并输出该 Tag，保留每通道独立编号及原生弱引用机制。不会把父监听的编号拿到子通道删除，子通道和有效父监听可继续接收广播。
- `SyncMarkerImporter.h/.cpp` 已迁入 `Source/GGYGOEditor/Public`／`Private`，导出为 `GGYGOEDITOR_API`。类名、两项反射函数、参数、默认值和 `SyncMarkerImport` 控制台命令保持；只修改并标脏动画，保存由调用方负责。未新增运行时到编辑器的依赖。
- `Config/DefaultEngine.ini` 的单条 ClassRedirects 将 `/Script/GGYGO.SyncMarkerImporter` 重定向到 `/Script/GGYGOEditor.SyncMarkerImporter`。迁移前核对 Source／Config／脚本及 Content／项目 Plugins 内 4812 个资产包的 UTF-8／UTF-16 类名和函数引用，未找到消费者。Python 仍使用 `unreal.SyncMarkerImporter`；显式裸字符串 `LoadClass` 不应用 ClassRedirects，应使用新模块路径或先解析软类引用。
- 已编译、已在 UE NullRHI 中测试。消息回归 `GGYGO.Messages.Router.ExpiredParentListener` 验证失效类型仅诊断一次、子监听连续收消息和父级 ExactMatch／PartialMatch 行为。`GGYGO.Editor.Animation.SyncMarkerImporter` 两项验证 Class import 所用的原生重定向、软引用、蓝图成员函数解析、单文件与控制台批量导入及标脏；真实 Editor Python 核实两个绑定入口。
- Messages 与 Animation 原会话已分别评审受影响差分，未发现阻塞问题；本次迁移保持原函数签名和导入行为。
- 证据为 [增量构建](../../Saved/Codex/I22_20261111/build.log)、[消息回归及首轮夹具失败](../../Saved/Codex/I22_20261111/editor.log)、[SyncMarker 修正夹具后的两项通过及 Python 读回](../../Saved/Codex/I22_20261111/Rerun/editor.log)。首轮误用了 `RF_Transient` 动画和绕过 CoreRedirects 的裸类加载／文本成员导入；修正夹具后只复验失败两项，未改断言所保护的标脏和函数可用行为。
- 未验证 Cook／打包及历史蓝图包的重新加载（未发现实际引用包）。启动日志中的 13 条 `LogAutomationTest: Error: Condition failed` 发生在专项测试开始前，原样保留，来源未在本需求排查；三个专项叶自身均为 Success、无 error／warning。Marker 排序、缓存刷新、完整 JSON 校验与 `AnimSyncMarkerTools` 归位仍属于 [CR-1014-T1](../Coordination/Module_Audit_Repair_Ledger.md)，本次模块迁移不关闭这些候选。

## 剩余候选盘点与嵌套输入来源

- I23 盘点完成，逐项结论见[修复清单](../Coordination/Module_Audit_Repair_Ledger.md#剩余候选核对)。Boss／玩家共享 Montage 资源、重复 getter 检查及 ASC 测试日志已完成，关闭对应旧候选。Hero 职责拆分、GE 校验统一保持优化建议；Marker 工具整理、旧预输入和 ZZZ 兼容层沿既有决定处理。
- CR-1111-D1 已修复：CheckCost 内同 Spec 的 raw Try 失败曾先认领外层输入来源。InputBuffer 现在记录同步 Can 层级，并将原生结果与输入 Try 的进入层级对应；内层原生失败及 GA 反馈照常，外层原请求仍获得一次合法重试通知和原截止。没有改变原生 Try、调度或玩法策略。
- 改动仅为 `GGYGOAbilityInputBuffer.h/.cpp` 与 `GGYGOGameplayAbility.cpp` 的 Can 范围；保留 GA 文件中最小联机的既有诊断改动。原两条失败断言和原日志保留，诊断测试源未改。
- `GGYGOEditor Win64 Development` 增量编译通过；独立 NullRHI Editor 的六项自动化全部通过、每项无 error／warning：原嵌套来源诊断、失败回调释放占用者、同一时刻重入物理请求、组准入、按来源退休请求、切回留场成员。证据：[构建日志](../../Saved/Codex/I23_20261111/build.log)、[运行日志](../../Saved/Codex/I23_20261111/editor.log)、[自动化报告](../../Saved/Codex/I23_20261111/Automation/index.json)。
- 统筹与 Input 消费侧差分评审均无阻塞：同步 Can 层级和一次消费保持原来源、截止与清理隔离。Can 内 raw Try 成功分支没有独立专项证据；未做本修复的生产实机输入、联机和 Cook 验证，不改变其它需求的未完成状态。退出时 MCP 服务有 socket 收尾错误，Editor 进程正常退出 0，专项自动化结果未受影响。

## 未完成项

交给 Codex，顺序和第一步见 [Codex 交接](../Coordination/Handover_Codex.md)。

1. 七份 spec 的剩余验收与待定项见上表；预输入、起停跳变和镜头衡量口径仍等原问题的用户决定。勾选回写已完成，不代表这些项目已验收。
2. 原统筹待修问题里还开着的：
   - `AAADocs/Scripts/wire_pyrios_skill_inputs.py` 对 `IMC_Default` 的基线因加了可改键名而失效，脚本会拒绝运行，等 E／R／F 输入线恢复时更新。
   - 业务缺口：公共 `GA_Death` 仍是空图；全员倒下后没有失败／复活流程；进退场 GA／Montage 缺省跳过；需要留场的技能由用户以后把 `AvatarExitPolicy` 改为 ContinueInBackground。
   - 引擎退出阶段偶发 `FVirtualTextureBuiltData::GetTileOffset` 越界断言，只记录。

## 验收标准

- 受影响模块编译通过；保留"旧回调不作用到后继、旧调用栈不清理后继资源"的外部契约测试；不降低断言、不排除失败场景。
- 普攻三段、技能、TurnBack、Boss 招式、FX 晚加入照常；换人续放各条逐项验证。
- 最小联机：Authority 与远端 SimulatedProxy 按同一 PlayerState 配对，双方可见（见 [minimal_multiplayer](minimal_multiplayer.md)）。
- Obsidian 只更新受影响模块，源码或资产尚未验证的内容不写成"已实现"。
