# 代码整改（CR-R7 扩展）与换人续放

更新：2026-11-11。需求状态和占用以[看板](../Coordination/Board.md)为准，剩余工作已交给 Codex，见 [Codex 交接](../Coordination/Handover_Codex.md)。过程历史以 Git 为准。

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
- 11-10：死亡结束后的 Pawn 去留改由共享角色蓝图决定（选 B，未做）。
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

规范澄清已写入 [CodeConventions](../Architecture/CodeConventions.md)：外调正向清单、后置检查举证、原生寿命与身份合并、预备配置要有明确来源／寿命／清理点。

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

- 7 步源码全部完成，已编译，NullRHI 自动化测试通过（含 SquadSwitch 8 例、HealthSet 复现回归）。
- 真实 RHI 已验证：
  - 普攻生产冒烟 24 项中 22 项通过，2 例 PoseFailure 按约定保留失败（见 [normal01_first_strike](normal01_first_strike.md)）。
  - 联机（监听服务器＋1 客户端）换人：客户端 RPC 和 Z／C 按键换人、冷却、改键生效、再次附身后双端都能移动、普攻激活、死亡自动换人、生命／上限／破韧复制一致。
  - 改键页面和死亡自动替补（蓝图分层 B06、B08）已完成，见[蓝图分层收尾](blueprint_layering_followups.md)。
  - 角色受光与阴影已完成，见下节。
- 原统筹待修问题里已关闭的：再次附身后客户端不能移动（CMC owner-sync 修正）；Locomotion 输入测试留住测试世界；冷会话首击因 FX 材质未就绪失败（首击等资源就绪）；角色阴影捕获在 PIE 结束时留住世界；倒下画面的阴影条纹。
- spec 勾选状态还没回写，见未完成项。

| Spec | 状态 |
| --- | --- |
| 1 冗余清理 | 源码完成，已测；生产冒烟已跑（同上） |
| 2 输入请求 | 源码完成，已测；任务 5 等用户决定连段预输入 |
| 3 FX 发布 | 源码完成，已测；FX 的单机 PIE 和最小联机未验 |
| 4 激活生命周期 | 源码完成，已测；纠正重放和最小联机未验 |
| 5 Avatar 绑定 | 源码完成，已测；联机出生与换人已验，复活未验（项目没有复活流程） |
| 6 换人续放 | 源码完成，已测，真实 RHI 联机已验；进退场资产缺省跳过 |
| 7 HealthSet | 已定案并测过；死亡的联机数值未单独核对 |

### 角色受光与阴影（已完成）

结论：倒下和转身时地面的放射条纹是 VSM 缓存残影，已修；换人瞬间的拖影是换人时相机跳变造成的运动模糊，属正常表现；换人稳定后的阴影参数和单机一致。证据 `.agents/tasks/requirements-closeout/evidence/I10.md`（只在本机）。

- 原因：Pyrios Mesh 的包围盒由物理资产算出，只覆盖躯干；武器、斗篷、小腿在动画中远超出去。VSM 按图元包围盒决定哪些缓存页要重画，包围盒外的旧姿态阴影留在地面形成条纹。
- 改动和接口：
  - `BP_PC_Pyrios` 的 Mesh `BoundsScale` 为 11（写入脚本 `AAADocs/Scripts/set_pyrios_mesh_bounds_scale.py`）。整段倒下 Montage 所需倍率最大约 9.5，11 留约 16% 余量。物理资产和骨骼网格是本地导入资产、不入库，所以不改它们。
  - `FGGYGOCharacterShadowCapture`：对象阴影宽度 `ObjectWidth = 2 × (SphereRadius / BoundsScale + ObjectMarginCm)`，扩大包围盒不会稀释对象阴影图分辨率；`BoundsScale <= 0` 时宽度为 0，被原有校验拒绝。
  - 联机测试 `GGYGO.Teams.SquadSwitch.ListenServerClientRequest` 在真实 RHI 且给了 `-GGYGOCaptureDir` 时，死亡自动换人后加取稳定帧和关运动模糊帧，结束时恢复 `r.MotionBlurQuality`。
- 仍有效的约束：
  - 新增动作如果让武器或斗篷伸得更远，要重新逐帧跟踪所需倍率；以后若把物理资产入库，可以加不参与碰撞的包围体，再把倍率降回去。
  - `BP_PC_Pyrios` 在 BeginPlay 按 Actor Tag `GGYGO.KeyLight` 找本 World 里唯一的 DirectionalLight 作为角色主灯，找不到就停用角色灯宿主并打印"主灯绑定拒绝"。目前只有 `L_Movement_Test` 配了这个 Tag，Kevin 两张地图没有。
- 验证级别：已编译；已测试（`GGYGO.Rendering` 4 例、`GGYGO.Teams.SquadSwitch` 8 例）；已在 UE 里运行（真实 D3D12 单机正背机位）；已联机验证（客户端倒下帧地面无条纹，稳定帧对象阴影宽度与单机一致）。
- 未做：`BoundsScale` 11 的 GPU／VSM 开销没测；修后单机倒下没有单独重拍。
- 正背对照里与原图 `AAADocs/Assets/Pyrios/Rendering/References/20261009_Pyrios_*.png` 的差异不属于阴影问题，是否另开需求由用户决定：胸口光球偏暗、蓝色手臂发光偏弱、背面头发偏灰紫偏亮、斗篷没有蓝色渐变且金色细线显示为橙红（斗篷只读暂挂）。

## 未完成项

交给 Codex，顺序和第一步见 [Codex 交接](../Coordination/Handover_Codex.md)。

1. 消息路由失效监听清理：`GameplayMessageSubsystem.cpp` 第 100 行用广播的 Channel 去删父 Tag 列表里的失效监听，应改成当前遍历的 Tag，并加回归测试。
2. SyncMarker 工具归位：`Source/GGYGO/SyncMarkerImporter.*` 迁到 GGYGOEditor，先查蓝图／资产引用，加 CoreRedirects 保持类路径兼容。
3. CR-R7 剩余候选逐项核对，按[修复清单](../Coordination/Module_Audit_Repair_Ledger.md)出状态表；含新登记的 CR-1111-D1（显式开关诊断 `ProjectDiagnostics.Input.ActivationOrigin.NestedSameSpecRawTry` 失败）。小缺陷直接修，优化交用户。
4. 死亡结束后的 Pawn 去留改由蓝图决定：`AGGYGOCharacterBase::OnDeathFinished` 现在固定下一帧 `UninitAndDestroy`。C++ 保留死亡结束广播、下一帧时序和权限检查，把去留交给共享角色蓝图；生产蓝图配成等价的下一帧销毁，未配置时明确报错。销毁必须晚于自动替补所在的那次广播。
5. 各 spec 勾选状态回写（依赖最小联机完成），同时更新上面的状态表。
6. 原统筹待修问题里还开着的：
   - PIE 结束时 Enhanced Input 报 `IMC_Squad`／`IMC_Default`／`IMC_MouseLook` "仍在应用、可能泄漏"的 Warning（LocalPlayer 子系统先于 Controller／Pawn 的 EndPlay 反初始化），本批没有复查。
   - `AAADocs/Scripts/wire_pyrios_skill_inputs.py` 对 `IMC_Default` 的基线因加了可改键名而失效，脚本会拒绝运行，等 E／R／F 输入线恢复时更新。
   - 业务缺口：公共 `GA_Death` 仍是空图；全员倒下后没有失败／复活流程；进退场 GA／Montage 缺省跳过；需要留场的技能由用户以后把 `AvatarExitPolicy` 改为 ContinueInBackground。
   - 引擎退出阶段偶发 `FVirtualTextureBuiltData::GetTileOffset` 越界断言，只记录。

## 验收标准

- 受影响模块编译通过；保留"旧回调不作用到后继、旧调用栈不清理后继资源"的外部契约测试；不降低断言、不排除失败场景。
- 普攻三段、技能、TurnBack、Boss 招式、FX 晚加入照常；换人续放各条逐项验证。
- 最小联机：Authority 与远端 SimulatedProxy 按同一 PlayerState 配对，双方可见（见 [minimal_multiplayer](minimal_multiplayer.md)）。
- Obsidian 只更新受影响模块，源码或资产尚未验证的内容不写成"已实现"。
