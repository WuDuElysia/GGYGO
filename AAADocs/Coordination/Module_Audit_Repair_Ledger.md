# 全模块自查修复执行清单

## CR-20261014：业务代码冗余、模块职责与防御收口

状态：2026-10-19起停止Kiro调用，由Root按现行CodeConventions审查，原模块作者实现。当前42件源码单CPP include修复后已通过R7标准完整构建及保护，Root实核软件；按用户当前要求先作阶段Git检查点，原18项及生产／视觉／设备／联机未验边界保持。前一37条R5已Build／保护通过，18原专项严格14项通过；四未过项的源码修复已静态核收，运行复验待做。生产、视觉、设备及联机仍未验，CR未全部完成；唯一窗口与机器证据见[当前排程](Module_Repair_Parallel_Schedule.md)。

当前已应用产物：[r1补丁](../../Saved/Codex/CR_20261015_KiroDraft_R1/CR_20261015_KiroDraft_R1_r1.patch)及[应用身份](../../Saved/Codex/CR_20261015_KiroDraft_R1/input_manifest_r1.json)保持冻结，r1准确八改／两删及R5十Source已核；三测试日志登记修复后的构建／必要叶结果见首段，准确身份与原失败见[历史](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-17-r6日志登记修复与三叶通过)。生产PIE／联机仍未验，待实施草稿按下方分项读取。

评审依据：Kiro评审会话`01a138f5-b16c-7781-b8f2-003f2878f94a`，最终回执turn`01a13917-7fcc-7e43-9637-ac11ab2b34bf`的“来自Kiro”；仅按需读该最终回执，不搬过程全文。X1～X7及A／M／P／C／AN／F／B／T项均为待核结论，行数／词频／ASCII资产名字表0命中及启发式无调用方不证明可安全删除；未细读区域不作为已确认根因。

目标：在保留真实玩法、CMC／GAS权威与必要生命周期保护的前提下，由Root会同原作者检查并解决晦涩、绕行的主流程与重复机制、迁移残留、职责混杂及无依据的重复防御；按语义命名、连续步骤、lambda捕获与具名步骤、契约注释改善受影响代码。解释原先为何这样写、真实解决过什么问题、为何逐步膨胀，以及现有审核为何未及时拦住。不得按行数或lambda数量机械改写，也不得以一枚布尔量／原生SpecHandle代替尚未证明等价的不同资源寿命。

首批候选与准备过程已归档，见[历史原文](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-cr首批源码准备过程归档)；当前范围与未验项按下表执行，审核以[CodeConventions](../Architecture/CodeConventions.md)为准。

### 用户七项答复与当前边界

| 项 | 用户原话／对应事项 | 已确认或仍待收敛 |
| --- | --- | --- |
| 1 | “暂时没有，后续可能加”／GameFeature插件 | 当前无近期真实插件需求，停止扩展预留框架；不据此自动整条删除。保留／退役范围按实际消费者与未来兼容成本收敛。 |
| 2 | “允许”／持续GE改当前Health／Poise | 保留该功能，不采用禁止持续修改当前值来删HealthSet链的方案；可整理反算与属性层职责。 |
| 3 | “每段伤害不一样”；追加确认“应影响：攻击力乘各段独立倍率” | 采用角色攻击力×每段独立倍率，攻击Buff须影响每段。旧绝对值／角色攻击力配置先实读再迁移，不以示例100猜实际基数，不擅自填默认倍率。 |
| 4 | “看情况”／按键来源证明改锁存 | 原qualified Held／先释放再按下语义保持。原Input作者列重绑、焦点／设备切换、多键源的实际差异；等价技术简化自主，行为变化再问用户。 |
| 5 | “不懂”；追加确认“保留等待，只简化重复机制” | 首次游戏视图继续等待真实相机模式成功就绪，不引入初始化默认镜头过渡。精简重复机制／纯段校验，不删真实返栈保护；切Pawn重新就绪政策单独核，不冒称现闸门已覆盖。 |
| 6 | “要”／其它客户端看普攻FX；“需要，显示仍有效的剩余特效” | 远端可见包含晚加入／重获相关性时的在途剩余特效及实际时间进度，已结束窗口不补播；验owner与另一客户端时机、挂点、停止／去重，不以本地Task运行证明远端。 |
| 7 | “可以”／Montage时间线统一 | 同意收敛单一信号机制；原攻击点、移动MainEnd独立许可、自然结束和作者时间语义保持。通道与资产兼容由公共Task、Animation／Combat牵头核实后迁移，不直接改当前在途资产。 |

### 分项及验收

| 分项 | 原牵头／范围 | 必要交付与当前状态 |
| --- | --- | --- |
| CR-20261014-R1 原因追溯及规范 | 根统筹；原 Kiro 代码审查会话、AbilitySystem、Character／Combatants、Input、Camera | 规范复核及最小修订完成：外调按可达性；新增持久机制说明基线缺口；先保等价外部契约再迁内部断言；现有自审／验收核必要性与旧入口收尾。剩余原因核查只读：原输入第17次失败、原End与Task清理时序、partial Init及不同寿命身份须逐项对应，替代推断仍待验证，不以“当时要求严格”代原因。 |
| R2 局部重复与工具职责 | Root审核，原模块按职责实现；复用下方CR-1014-T1／B1～B6 | 保留准确消费者／反射引用，收敛同次纯路径重复检查、共用真实相同寿命资源；Sync Marker迁Editor并处理类路径兼容。首批r1十Source已应用并冻结，必要运行验证及后续职责整改仍待。 |
| R3 绑定／激活／订阅 | Root审核，AbilitySystem牵头，Character／Combatants／Input／Movement按职责实现；X1／X2／X6 | R3-1／R3-2及NativeWrite已在R5构建；partial Init实际物理清理／原失败／后继隔离断言已到达，原叶3Warning仍未达门禁。本轮仅测试预期诊断修复已静态核收冻结，未复验；激活Serial及Context寿命保持。原失败见历史；R3-3尚未授Hero写窗，按当前优先级接续，不以旧R4等待阻塞本批。 |
| R4 退役与预留 | Root审核，Input及原模块实现／核消费者；X4／X5、迁移接口及Tag／治疗链 | 四Source退役包装／改用既有QueryMovementInputRequest已过R5编译，出生叶实际执行至拆卸，仍因清理Error／Warning未过。原调用及四Query断言保留；本轮IMC归还顺序及终态诊断修复已静态核收，未复验。其余退役未实施，须核真实C++／BP／Montage／配置／序列化消费者；持续GE及有消费者Tag保留。 |
| R5 属性与伤害 | AbilitySystem／Combat动作／BossAI | 真人基础攻击10、三段倍率1／2／3，Buff作用各段。机制Source／标准Build／必要专项通过，生产八包保存与独立Cold通过，两诊断GE已准确保存；原攻击点／MainEnd移动分门、独立削韧、旧绝对模式／持续GE保持，角色仍A。R11实际两组10／20／30、Buff20／40／60、六Spec及自然结束已证，同R2正常清理／exit0及全父归还已核，原driver失败保留；后继改动受影响生产、真实设备输入／视觉／联机仍待验；自有Encounter显式AssemblyOnly的Ready及四Vitals1000已实测，真实碰撞命中／衰减仍未验。当前provider／宿主版本、准入失败与唯一执行窗仅在[活动排程](Module_Repair_Parallel_Schedule.md)维护；[八包迁回](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-17-生产八包迁回保存与独立cold)、[Buff恢复](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-17-诊断buff保存恢复与正常退出)、[Target保存及原失败](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-17-targetvitals保存与宿主同步重入)、[首轮Numeric失败](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-17-numeric首轮读回签名失败)按需查，不以保存／Cold替代运行验收。 |
| R6 输入与相机 | Input／Camera，Character参与；X7／C1 | LocalPlayer post-Super重复查询已精简并过R5编译；首个真实CameraMode确认闸门及原返栈／bProjected保护保持，PhotographyPublicationAdmission通过。真实生产首帧仍待；四件Editor观测源码已静态核收，R6构建因头引用C1083失败并完整归还，单CPP修复及R7入口已核收，待本轮完整构建／运行，未UE，不以Manager叶或PNG替代投影证据。输入出生夹具修复未放宽生产首闸，当前修后版本待复验；换Pawn／Restart及原失败字段不变。 |
| R7 表现与时间线 | Root审核，FX牵头，AS／公共Task／Animation／Combat／Character按原职责参与；F1／AN2 | typed同步窗口、真实BranchingPoint及原公开Payload、反射active状态＋可靠Terminal、单远端Niagara及原角色事实桥已接源码；四FX发布叶、NamedNotifyContract及Boss重入等基础叶在R5通过。原攻击／移动／MainEnd、GAS／CMC及缺End／混出／终止／尾粒子合同保持。八件观测源码已静态核收；新42件R6构建因头引用C1083失败并完整归还，尚未复验，准确差集及最后18项结果只见活动排程。生产首投影、真实ControllerAge、晚加入／重获相关性的剩余FX及正确进度仍须实证；五Montage／两GA的Queued／NoMerge、FX.Mode／Trace／图委托／两Remote参数待实际读回，原清单turn 01a14fbf-01c2-7502-b81f-350172f8627c。生产／视觉／联机未验，旧协议取舍按需查原回执，不恢复Kiro调用。 |

交付标准：每个采纳项有当前准确代码／资产依据、原失效与最小复现、保留／删除保护的理由；按独立变化原因和寿命收敛，实际构建／受影响运行／必要联机分别验证。因需求歧义等待只阻相关项。完整已验需求按当次交付归档；未实现／未知／失败保留，不把候选记录或源码瘦身当完成。

### 原静态延期候选（关联R2，保留原证据）

此前用户决定：Sync Marker归入编辑器工具整理，其余影响不大时先记录。下表与新Kiro评审合并在本需求唯一入口，未重复另建任务；当前未实施、未编译、未运行UE，也未核验完整BP／资产消费者。

本轮未确认需要立即中断主线修复的业务故障。下表的重复实现、职责拆分与接口退役均为维护候选；源码事实与是否造成实际故障分开。

| 编号／所属 | 评审事实与准确入口 | 建议、优先级与后续触发 |
| --- | --- | --- |
| CR-1014-T1／Animation 编辑器工具 | [SyncMarkerImporter.cpp](../../Source/GGYGO/SyncMarkerImporter.cpp) 的批量／单文件入口各自清空并写 Marker，未排序或刷新同步缓存；[AnimSyncMarkerTools.cpp](../../Source/GGYGO/Animation/AnimSyncMarkerTools.cpp) 会排序／刷新，但数组不等长时取 Min，解析器也会跳过部分无效条目。均属资产工具，不计入运行时业务职责问题。 | 下次使用或整理该工具前处理。建议两工具头／实现迁入既有 Source/GGYGOEditor/Public 与 Private，导出改用 GGYGOEDITOR_API；JSON 解析与唯一 Marker 写入实现分开，完整校验后写入、失败保持原数据。迁模块前核 Blueprint／Python 调用与 /Script/GGYGO 到 /Script/GGYGOEditor 的类路径兼容，按实际消费者保留入口或精确重定向。本轮不移动文件。 |
| CR-1014-B1／Combat 动作 | [ComboTypes::FGGYGOComboWindowState](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOComboTypes.h) 仍有 Store／Consume／ExpiresAt；[PlayerCombo::HandleInputPressed](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp) 已要求作者点后真实新请求，生产无旧缓存方法调用，InputBufferSeconds 无读取点；[旧纯测试](../../Source/GGYGO/AbilitySystem/Tests/GGYGOComboWindowTest.cpp) 仍验证预输入消费。 | 中低，延期；下次改 Combo 输入／窗口时收尾。清理无生产消费者的非反射缓存逻辑，使测试契约对应实际入口；反射查询、序列化字段及网络窗口字段先核消费者，保留历史／失败证据，不恢复旧预输入玩法。 |
| CR-1014-B2／Combat 动作、BossAI | 玩家已使用 [MontageActionResources](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOMontageActionResources.h)；[BossMelee](../../Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp) 仍单独持有 Task、CMC 句柄、完成事实、订阅与释放。存在相同机制的重复维护，尚未证明因此发生运行错误。 | 中低，延期；下次两边共同修改资源生命周期时比较并复用一致部分。Profile、超时及接续政策仍由所属 GA 决定，不强行合并能力或增加模式框架。 |
| CR-1014-B3／Input 唯一作者 | [HeroComponent](../../Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp) 同时承担 InitState／相机协调、输入绑定资源、移动装配与能力输入观察生命周期。当前拥有关系有明确来源，本轮未确认第二输入消费权威。 | 低，延期；随正常 Input 重构评估。可将绑定／会话资源整理为 Hero 私有普通 C++ 协作者；PlayerInput 继续拥有设备事实，ASC 继续唯一拥有请求与 retry 消费，不增加组件或调度器。 |
| CR-1014-B4／Animation | [ZZZLocomotionEvents](../../Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.cpp) 仅作两个字段映射，却维护 SetContext／Reset；[ZZZAnimContext](../../Source/GGYGO/Animation/zzzAnim/Data/ZZZAnimContext.h) 的 IsValid 要求 Tuning，实际生产调用未设置它且映射不消费它。IsValid 本轮未发现生产调用，不列为已触发故障。 | 低，延期；下次整理旧 ZZZ 兼容适配时改为显式引用参数的纯映射，或并入现有快照适配器。保留 AnimBP 反射字段及真实轴映射。 |
| CR-1014-B5／AbilitySystem、Combat 动作、BossAI | [PlayerCombo::ValidateDamageEffectDependency](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp) 检查显式 GE 类及 Abstract／Deprecated／NewerVersionExists；[BossMelee::ResolveMeleeConfiguration](../../Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp) 主要检查解析结果非空，规则存在差异。未确认现有坏资产或实际触发。 | 中低，延期；下次修改伤害 GE 配置／依赖解析时统一纯解析校验。各 GA 显式决定必需 GE 或允许无 GE 的正常模式，不合并两种玩法政策、不新增隐式共享兜底。 |
| CR-1014-B6／Combat 动作 | [PlayerCombo::InitializeAbilityActivation／CleanupAbilityResourcesForTermination](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp) 的资源残留条件先检查 StepMotionResources.IsValid，又检查只从该对象派生的 Task／FX／注册／watchdog；这些条件不能额外发现残留。 | 低，延期；随同文件正常修改顺手收敛表达。保留独立 InputTask／Trace／Mesh 资源检查及真实测试观察接口。 |

必要保留：外调／原生返栈后的原身份核验、先摘资源后释放、网络权限、幂等清理、合法异步等待、自然混出最后位移区间及远端 Held 节点消费证明。ASC／Task／CMC 身份事实寿命不同，不因本次精简候选合并。以上候选均未授予新实现窗口，后续只沿[当前排程](Module_Repair_Parallel_Schedule.md)及原模块作者安排；不作为当前姿态／移动／Slot／独立打断验收的新增前置。

## 历史修复编号与未验边界

2026-10-08整改的完整编号索引、旧交接及未勾选／失败／正式资产／网络／Cook边界已迁[历史索引](Module_Audit_Repair_Ledger_History_20261016.md#2026-10-19-活动历史索引迁出)。历史未验不因归档完成或取消，消费时核当前源码／资产；当前写权只查活动排程，不恢复旧租约。稳定规则只见AGENTS.md及CodeConventions。
