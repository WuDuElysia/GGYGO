# 全模块自查修复执行清单

## CR-20261014：业务代码冗余、模块职责与防御收口

状态：真人将过往冗余整理修复交给既有Kiro代码审查会话（Opus5.5／high）。首批十一Source逻辑范围及受影响契约已收敛，原Source／资产仍无写权；当前授新Saved/Codex/CR_20261015_KiroDraft_R1内受控镜像与补丁草稿，先核完整父／动态写集交空，原输入持续冻结，主线不导入／编译草稿。只接受源码草稿及必要静态／离线证据，真正应用／Target／PIE待业务保护正常归还后另授窗口。原模块作者提供接口与必要失败依据，Kiro直接实施／自审，根负责窗口／核收，不复制实现。玩法新增项继续由根统筹原模块。两轮规范复核及最小条款已写入[CodeConventions](../Architecture/CodeConventions.md)并归档；源码整改仍未落入生产，不新建会话或第二排程，不阻塞主线。共享资源仅按[当前排程](Module_Repair_Parallel_Schedule.md)协调。

当前可审查产物：[Kiro r1补丁](../../Saved/Codex/CR_20261015_KiroDraft_R1/CR_20261015_KiroDraft_R1_r1.patch)（35631B／A3D3D720…08D912）、[原输入与往返身份](../../Saved/Codex/CR_20261015_KiroDraft_R1/input_manifest_r1.json)。根实核11条身份（10既有源及1未创建测试），原/base/work/新apply_check_verified_r1均无差、补丁10文件实际变更、与N1完整父交集空；仅在全新Saved副本apply-check/apply为0、roundtrip为0。旧CRLF失败补丁及旧校验目录保留，相对递归删除命令已拒绝，安全重试无删除。新测试候选因需生产测试入口已由Kiro撤回；UHT／完整Target／叶／PIE未做，未应用真实Source，功能与语义尚不据此验收。后继应用前必须核原输入仍同并安排必要实际验证，原范围／契约不因草稿减少行数而自动通过。

评审依据：Kiro评审会话`01a138f5-b16c-7781-b8f2-003f2878f94a`，最终回执turn`01a13917-7fcc-7e43-9637-ac11ab2b34bf`的“来自Kiro”；仅按需读该最终回执，不搬过程全文。X1～X7及A／M／P／C／AN／F／B／T项均为待核结论，行数／词频／ASCII资产名字表0命中及启发式无调用方不证明可安全删除；未细读区域不作为已确认根因。

目标：在保留真实玩法、CMC／GAS权威与必要生命周期保护的前提下，由Kiro深入检查并解决晦涩、绕行的主流程与重复机制、迁移残留、职责混杂及无依据的重复防御；按语义命名、连续步骤、lambda捕获与具名步骤、契约注释改善受影响代码。解释原先为何这样写、真实解决过什么问题、为何逐步膨胀，以及现有审核为何未及时拦住。不得按行数或lambda数量机械改写，也不得以一枚布尔量／原生SpecHandle代替尚未证明等价的不同资源寿命。

当前首批：Kiro最终范围回执turn `01a1398d-7854-7ff1-bb6b-cdeb8c034890`。拟去三处ClearAbilityInput后的重复复核须核中间写入／谓词依赖；非反射无消费者的CancelInputActivatedAbilities／ClearLocalAvatarBinding／旧AnimCurveSampler及过期注释可按准确写集移交。原九源中BT直接删除全量校验方案已撤回：BossAI实核Actions公开可写，ClearValue可同步触发observer，将BaseWeight改NaN会漏过现<=0检查；仅静态可达反例，未动态复现。保原整表无效即拒绝，等价收敛另由Kiro分析。CR状态由根维护，所有项仍未写入／未授Source窗；资产保护归还后按准确文件冻结换手，必要叶不重跑历史全量矩阵。

现行规范已由原审查会话补齐可读性，并强调同栈去重须核中间写入与谓词依赖；根已读取实际条文。首批之后的深入可读性整改仍由Kiro收敛具体写集，完整主流程／生命周期合同与原严格复现保持，不新增逐步报告或第二任务记录。

最新拟扩围R-A：编队存档／LocalPlayer读取主流程，新增对应首次读取、缓存命中、次级玩家拒绝、坏档拒绝叶。Kiro已读取新规范并消费BossAI合同（completed job `cdeadc81-d10b-4f18-a9bb-84ffac8a5724`）；BT直接删校验及ChooseBossAction三次校验候选已撤回，不需BossAI冻结整改文件。明确列举首批八源加R-A三源共十一Source路径，CR状态文档仍由根维护，不按报数放行未列文件。尚无Source写权，原Player／Teams参与合同及文件冻结；构建／必要叶随完整保护正常归还后安排，R-B／R-C待合同或主线写集让出。

### 用户七项答复与当前边界

| 项 | 用户原话／对应事项 | 已确认或仍待收敛 |
| --- | --- | --- |
| 1 | “暂时没有，后续可能加”／GameFeature插件 | 当前无近期真实插件需求，停止扩展预留框架；不据此自动整条删除。保留／退役范围按实际消费者与未来兼容成本收敛。 |
| 2 | “允许”／持续GE改当前Health／Poise | 保留该功能，不采用禁止持续修改当前值来删HealthSet链的方案；可整理反算与属性层职责。 |
| 3 | “每段伤害不一样”；追加确认“应影响：攻击力乘各段独立倍率” | 采用角色攻击力×每段独立倍率，攻击Buff须影响每段。旧绝对值／角色攻击力配置先实读再迁移，不以示例100猜实际基数，不擅自填默认倍率。 |
| 4 | “看情况”／按键来源证明改锁存 | 原qualified Held／先释放再按下语义保持。原Input作者列重绑、焦点／设备切换、多键源的实际差异；等价技术简化自主，行为变化再问用户。 |
| 5 | “不懂”；追加确认“保留等待，只简化重复机制” | 首次游戏视图继续等待真实相机模式成功就绪，不引入初始化默认镜头过渡。精简重复机制／纯段校验，不删真实返栈保护；切Pawn重新就绪政策单独核，不冒称现闸门已覆盖。 |
| 6 | “要”／其它客户端看普攻FX | 明确要求远端可见；核GA／Montage／Cue实际生产链，验owner与另一客户端时机、挂点、停止／去重，不以本地Task运行证明远端。 |
| 7 | “可以”／Montage时间线统一 | 同意收敛单一信号机制；原攻击点、移动MainEnd独立许可、自然结束和作者时间语义保持。通道与资产兼容由公共Task、Animation／Combat牵头核实后迁移，不直接改当前在途资产。 |

### 分项及验收

| 分项 | 原牵头／范围 | 必要交付与当前状态 |
| --- | --- | --- |
| CR-20261014-R1 原因追溯及规范 | 根统筹；原 Kiro 代码审查会话、AbilitySystem、Character／Combatants、Input、Camera | 规范复核及最小修订完成：外调按可达性；新增持久机制说明基线缺口；先保等价外部契约再迁内部断言；现有自审／验收核必要性与旧入口收尾。剩余原因核查只读：原输入第17次失败、原End与Task清理时序、partial Init及不同寿命身份须逐项对应，替代推断仍待验证，不以“当时要求严格”代原因。 |
| R2 局部重复与工具职责 | Kiro执行，原模块接口参与；复用下方CR-1014-T1／B1～B6 | 保留准确消费者／反射引用，收敛同次纯路径重复检查、共用真实相同寿命资源；Sync Marker迁Editor并处理类路径兼容。先收敛首批确证冗余写集，未授实现窗。 |
| R3 绑定／激活／订阅 | Kiro执行，AbilitySystem／Character／Combatants／Input／Movement提供原合同；X1／X2／X6 | 比较原生ActorInfo、Spec／PredictionKey与原资源合同；服务端无预测键、连续再激活、原终止回调重入、partial Init、外部ASC／Avatar换绑等真实边界须证明。不同寿命不可机械合并。只读原因先行。 |
| R4 退役与预留 | Kiro执行，原模块提供消费者；X4／X5、迁移接口及Tag／治疗链 | 真实C++、BP／Montage／配置／序列化引用核实后再迁移、删除；保留持续GE功能及仍被资产使用Tag，不按扫描0命中直接删。未实施。 |
| R5 属性与伤害 | AbilitySystem／Combat动作／BossAI | 保留持续GE；用户已确认攻击力×每段独立倍率。玩家与Boss仍写绝对SetByCaller.Damage，倍率尚未生产接入；每次命中建Spec时机保留。[六Source草稿](../../Saved/Codex/DamageSegmentMultiplier_20261016_Draft_R1/inputs.json)已冻结，Root核19输入及apply-check通过，[静态结果归档](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-16-r5独立段倍率草稿冻结)；未应用／编译／运行。Pyrios PawnData所引AbilitySet的effects为空，未发现已配初始化GE漏消费的证据；DefaultStartingData／活动初始化GE、真实攻击力、各段倍率及Boss当前CDO仍待实际读回。下一步核配置并迁移玩家／Boss写键及最终Spec应用前校验，不用旧Damage20或Base／Current=0／0推导倍率。普通GE_Damage_SetByCaller与自毁GE_SelfDestruct分立，旧绝对伤害及独立削韧语义保留。实际Source／资产／UE／构建仍无写权，后继按共享窗口串行。 |
| R6 输入与相机 | Input／Camera，Character参与；X7／C1 | 相机等待真实模式就绪已确认保留，精简重复机制。输入仍按具体等价／差异收敛，原语义保持；真实外调后的必要核验与无外调重复分开。 |
| R7 表现与时间线 | FX／公共Task／Animation／Combat；F1／AN2 | 单一时间线消费权威、原窗口行为、owner／远端FX实际一致及生命周期清理；与当前独立打断／最小联机统一验收，不另立第二调度。未实施。 |

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

2026-10-08复杂度整改已完成约定有限门禁，旧交接、租约和逐批门禁已迁[历史正文](Module_Audit_Repair_Ledger_History_20261016.md)。当前写权只查[排程](Module_Repair_Parallel_Schedule.md)，不从历史恢复。

历史未勾选项、失败、正式资产／网络／Cook未验边界原样保留；需消费时按下列原编号定位并核当前源码／资产，不据旧勾选状态推断现状：

- V组：[V1](Module_Audit_Repair_Ledger_History_20261016.md#issue-v1)、[V2](Module_Audit_Repair_Ledger_History_20261016.md#issue-v2)
- A组：[A1](Module_Audit_Repair_Ledger_History_20261016.md#issue-a1)、[A2](Module_Audit_Repair_Ledger_History_20261016.md#issue-a2)、[A3](Module_Audit_Repair_Ledger_History_20261016.md#issue-a3)、[A4](Module_Audit_Repair_Ledger_History_20261016.md#issue-a4)、[A5](Module_Audit_Repair_Ledger_History_20261016.md#issue-a5)、[A6](Module_Audit_Repair_Ledger_History_20261016.md#issue-a6)、[A7](Module_Audit_Repair_Ledger_History_20261016.md#issue-a7)、[A8](Module_Audit_Repair_Ledger_History_20261016.md#issue-a8)、[A9](Module_Audit_Repair_Ledger_History_20261016.md#issue-a9)
- B组：[B1](Module_Audit_Repair_Ledger_History_20261016.md#issue-b1)、[B2](Module_Audit_Repair_Ledger_History_20261016.md#issue-b2)、[B3](Module_Audit_Repair_Ledger_History_20261016.md#issue-b3)、[B4](Module_Audit_Repair_Ledger_History_20261016.md#issue-b4)、[B5](Module_Audit_Repair_Ledger_History_20261016.md#issue-b5)、[B6](Module_Audit_Repair_Ledger_History_20261016.md#issue-b6)、[B7](Module_Audit_Repair_Ledger_History_20261016.md#issue-b7)、[B8](Module_Audit_Repair_Ledger_History_20261016.md#issue-b8)、[B9](Module_Audit_Repair_Ledger_History_20261016.md#issue-b9)
- C组：[C1](Module_Audit_Repair_Ledger_History_20261016.md#issue-c1)、[C2](Module_Audit_Repair_Ledger_History_20261016.md#issue-c2)、[C3](Module_Audit_Repair_Ledger_History_20261016.md#issue-c3)、[C4](Module_Audit_Repair_Ledger_History_20261016.md#issue-c4)、[C5](Module_Audit_Repair_Ledger_History_20261016.md#issue-c5)、[C6](Module_Audit_Repair_Ledger_History_20261016.md#issue-c6)、[C7](Module_Audit_Repair_Ledger_History_20261016.md#issue-c7)、[C8](Module_Audit_Repair_Ledger_History_20261016.md#issue-c8)、[C9](Module_Audit_Repair_Ledger_History_20261016.md#issue-c9)、[C10](Module_Audit_Repair_Ledger_History_20261016.md#issue-c10)、[C11](Module_Audit_Repair_Ledger_History_20261016.md#issue-c11)、[C12](Module_Audit_Repair_Ledger_History_20261016.md#issue-c12)、[C13](Module_Audit_Repair_Ledger_History_20261016.md#issue-c13)、[C14](Module_Audit_Repair_Ledger_History_20261016.md#issue-c14)、[C15](Module_Audit_Repair_Ledger_History_20261016.md#issue-c15)
- D组：[D1](Module_Audit_Repair_Ledger_History_20261016.md#issue-d1)、[D2](Module_Audit_Repair_Ledger_History_20261016.md#issue-d2)、[D3](Module_Audit_Repair_Ledger_History_20261016.md#issue-d3)、[D4](Module_Audit_Repair_Ledger_History_20261016.md#issue-d4)、[D5](Module_Audit_Repair_Ledger_History_20261016.md#issue-d5)、[D6](Module_Audit_Repair_Ledger_History_20261016.md#issue-d6)、[D7](Module_Audit_Repair_Ledger_History_20261016.md#issue-d7)、[D8](Module_Audit_Repair_Ledger_History_20261016.md#issue-d8)、[D9](Module_Audit_Repair_Ledger_History_20261016.md#issue-d9)
- E组：[E1](Module_Audit_Repair_Ledger_History_20261016.md#issue-e1)、[E2](Module_Audit_Repair_Ledger_History_20261016.md#issue-e2)、[E3](Module_Audit_Repair_Ledger_History_20261016.md#issue-e3)、[E4](Module_Audit_Repair_Ledger_History_20261016.md#issue-e4)、[E5](Module_Audit_Repair_Ledger_History_20261016.md#issue-e5)、[E6](Module_Audit_Repair_Ledger_History_20261016.md#issue-e6)、[E7](Module_Audit_Repair_Ledger_History_20261016.md#issue-e7)、[E8](Module_Audit_Repair_Ledger_History_20261016.md#issue-e8)、[E9](Module_Audit_Repair_Ledger_History_20261016.md#issue-e9)、[E10](Module_Audit_Repair_Ledger_History_20261016.md#issue-e10)、[E11](Module_Audit_Repair_Ledger_History_20261016.md#issue-e11)、[E12](Module_Audit_Repair_Ledger_History_20261016.md#issue-e12)、[E13](Module_Audit_Repair_Ledger_History_20261016.md#issue-e13)、[E14](Module_Audit_Repair_Ledger_History_20261016.md#issue-e14)、[E15](Module_Audit_Repair_Ledger_History_20261016.md#issue-e15)

其它未编号边界（Boss必需BT、HitImpact正式接线等）保留在[原明确问题](Module_Audit_Repair_Ledger_History_20261016.md#全部明确问题共享问题合并编号为稳定追踪键)。稳定协作与交付规则仅维护在[AGENTS.md](../../AGENTS.md)及[CodeConventions](../Architecture/CodeConventions.md)，不在清单重抄。
