# 全模块自查修复执行清单

## CR-20261014：业务代码冗余、模块职责与防御收口

状态：2026-10-28。已停止Kiro调用，由Root按现行CodeConventions审核、原模块作者实现。当前42件源码已通过R8标准完整Target和原18项严格验证（18成功、0错误／0警告），R14进一步通过生产普攻两轮数值、自然结束、首投影及资源／完整保护归还。真实设备、其余视觉／音频、受影响联机及下表未应用整改仍待，CR未全部完成；当前窗口与准确机器证据只见[活动排程](Module_Repair_Parallel_Schedule.md)。

已应用产物：[r1补丁](../../Saved/Codex/CR_20261015_KiroDraft_R1/CR_20261015_KiroDraft_R1_r1.patch)及[应用身份](../../Saved/Codex/CR_20261015_KiroDraft_R1/input_manifest_r1.json)保持冻结；后继已应用源码以R8／当前软件集合为准。旧R5／R6／R7准备与失败已迁[历史](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-21-cr入口过期阶段状态迁出)，不再用旧14／18结果覆盖R8事实；下表保留各职责未完成项。

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
| R3 绑定／激活／订阅 | Root审核，AbilitySystem牵头，Character／Combatants／Input／Movement按职责实现；X1／X2／X6 | R3-1／R3-2及NativeWrite已过R8构建；两绑定叶R8本轮严格0E／0W，partial Init物理清理／原失败／后继隔离的原强断言保持。激活Serial及Context寿命保持；R3-3尚未授Hero写窗，按当前优先级接续，不以旧等待阻塞生产。准确本轮报告及共享权限只见活动排程。 |
| R4 退役与预留 | Root审核，Input及原模块实现／核消费者；X4／X5、迁移接口及Tag／治疗链 | 四Source退役包装／既有QueryMovementInputRequest及夹具IMC归还顺序已过R8构建；出生叶原首按／四Query／清理断言R8本轮严格0E／0W。其余退役未实施，须核真实C++／BP／Montage／配置／序列化消费者；持续GE及有消费者Tag保留。真实设备／生产首闸仍未验。 |
| R5 属性与伤害 | AbilitySystem／Combat动作／BossAI | 攻击力×各段独立倍率已独立核收：基础10、倍率1／2／3，R14实际10／20／30及Buff20／40／60，六真实阻挡命中／六Spec、两GA／Task／CMC自然结束及原资源／目标／全父归还通过。绝对模式／持续GE原合同保留；本次无SourceInterface衰减1仅按实际当前分支推导，未冒称私有执行局部值或其它分支已测。设备／视觉／联机见本批剩余验收；[完整结果及旧过程](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-r14生产数值首投影与观察归还通过)按需查询。 |
| R6 输入与相机 | Input／Camera，Character参与；X7／C1 | 首CameraMode闸门及输入出生叶已过R8；R14同原玩家／真实Pyrios模式首自然Draw与完整投影已证，观察未写首次确认，订阅已归还。首次确认精确写端仍未捕获；设备／焦点切换、生产物理输入与其它镜头情景未验，不以当前单人观察扩称完成。准确当前权限只见活动排程。 |
| R7 表现与时间线 | Root审核，FX牵头，AS／公共Task／Animation／Combat／Character参与；F1／AN2 | typed窗口／公开Payload／可靠Terminal等已过R8构建及原FX／NamedNotify基础叶。R14真实反射、首投影、原FX source／owner_registration及1175条完整有界记录、原view／订阅归还已证。Controller Age／性能、晚加入／重获相关性剩余进度、动作特效画面仍待；五Montage／两GA配置按实际受影响入口核，不将本次单人观察扩为网络或视觉验收。原GAS／CMC及尾粒子合同保持，已结束过程见排程历史。 |

交付标准：每个采纳项有当前准确代码／资产依据、原失效与最小复现、保留／删除保护的理由；按独立变化原因和寿命收敛，实际构建／受影响运行／必要联机分别验证。因需求歧义等待只阻相关项。完整已验需求按当次交付归档；未实现／未知／失败保留，不把候选记录或源码瘦身当完成。

### CR-20261014-R7

2026-10-28 用户追加全模块 C++／蓝图职责和冗余防御复查，原21组长回执已收齐。2026-11-02 用户将顺序改为当前最小点完成后先完成Kiro任务；Kiro已确认该指令取代“旧批次完整验收提交后”的前提。新7步方案与换人续放只在[代码整改活动记录](../需求文档/refactor_and_squad_switch.md)维护，不在本节复制正文。Root仍独占本节及共享排程，实际授权以[当前窗口](Module_Repair_Parallel_Schedule.md)为准：本轮仅移交第1步收窄源码／文档写集给原Kiro会话，其余作者冻结；旧业务验收暂停但未取消，候选问题不自动取得写权。

复查范围：

- 检查当前生产调用链中的机制与业务归属。C++保留通用机制、权限、生命周期及必要接口；角色差异、招式组合、表现流程、Montage／FX／Audio编排、动画窗口、运动侧倾与姿态策略、曲线及参数应由BP／ABP／Montage／配置资产组织。不能只把参数暴露给蓝图，实际角色流程仍硬编码在C++；也不把GAS／CMC／网络权威、底层渲染／转换算法机械搬到蓝图。区分运行时业务与编辑器资产制作工具。
- 检查职责混杂、重复接口与转发层、重复状态／缓存／调度、历史迁移残留、重复全量校验，以及无实际失效依据的防御、重试和兜底。沿实际调用链判断，保留真实输入、外调、异步、网络及资源清理边界的必要保护，不按判空数量或行数裁剪。
- 各模块核当前源码及真实BP／资产消费者；无读取条件的资产行为明确未核实，不用C++检索无引用断言无人使用。原有已确认行为保持，跨模块由实际状态拥有者牵头，按最小接口提出迁移／收敛方案。

交回要求：每模块一次给出已查范围及主要结论；按共性归并，优先列最多5项高价值问题。每项含绝对路径／行或函数、实际调用依据、影响、推荐归属及最小迁移／合并／退役方案；需迁入BP者明确应由哪个现有BP／ABP／Montage／配置承载、C++留下何种通用接口。确认缺陷与候选优化、必要保留及未核实边界分开。发现阻断当前主线的真实缺陷仅单独标明，由Root协调，不自行扩改。无问题亦列覆盖范围和保留依据。

复查状态：21／21原模块已交完整只读回执，Root已按实际拥有者归并入下表；Audio首轮政策确认未算审查，补交结论后才核收。所有结论为静态／既有资产读回证据，整改、编译及运行未实施。原会话保留完整路径／行和保留依据，未覆盖或变更模型设置。

当前权限：只读本模块及必要调用者／接口、已有资产读回与导出。不得改源码／BP／资产／配置／共享文档，不新增独立报告、Canvas、任务JSON、全库快照／扫描，不启动UE、编译、测试或Raw导出，不调用Kiro或创建临时会话／子代理。后续整改按完整可集成批次分配唯一写入者，集中实现与配置、编译和受影响验证；相同问题与本清单既有条目合并，不另复制任务正文。

| 原模块 | 本轮复查状态 |
| --- | --- |
| Camera | 已交只读回执：GA Offset失败替换先撤旧、稳定模式完整校验重复、仅写镜像／旧说明；通用层硬约束Walk增益弱于Run属角色策略。机位/FOV等已有Camera BP保存，需保投影准入和所有权。 |
| AbilitySystem 通用基础 | 已交只读回执：角色流程迁BP前需窄选择／owned请求接口；命中扣Cost与当前Owned命中链不衔接（资产启用未核实）；同栈重复校验／无消费者工厂可收敛。与动作、BossAI及既有R3/R5合并，通用权威和清理保留。 |
| Input | 已交只读回执：通用装配强制MouseLook策略、同栈重复路由校验、无消费原生查询和Hero职责候选；与既有B3/R4合并，保设备事实、唯一ASC消费及释放屏障。手柄独立配置非当前故障，资产消费者另核。 |
| Character 装配与生命周期 | 已交只读回执：DeathFinished固定回收／隐藏策略与外部决策契约冲突（需后续玩法确认）、旧ASC-only BP手动装配接口残留、virtual Health handler双层校验条件收敛；保Native装配／权限／精确订阅与资源关闭责任，原Pyrios渲染类仅兼容壳。 |
| Animation 运行时 | 已交只读回执：侧倾camera事实接口与曲线选择／求值策略耦合，迁现有ABP UpdateMovingLean；旧ZZZ Snap/Context/StateMemory逐帧派生链与C++ Stop节点索引收口，真实ABP消费先迁；Marker重复归既有T1。保骨链/Slot/同源时间及远端凭据机制。 |
| Animation 资产生产 | 已交只读回执：Marker多入口写入／部分解析合并既有T1；点Notify与State通用准入、Lean历史迁移与当前制作耦合可收敛。已核编排在GA/Montage/ABP资产，State迁时未生产保存边界保持，不把工具角色路径当运行时硬编码。 |
| Movement | 已交只读回执：升跑保持／起停与TurnBack策略同速度来源开关耦合，可由MovementSet显式承载、角色BP选择；CMC保确定性预测执行。重复曲线／源绑定校验、Dodge占位及兼容入口核退役；同Physics／Animation归并，不机械搬状态机或姿态权威。 |
| Teams | 已交只读回执：无出战位时Next/Previous漏查候选、调试编队拒绝后仍保存；复制到齐通知缺口待联机核实；无消费原生入口及重复保护可收敛。现有角色配置已由PawnData／AbilitySet／Experience承载。 |
| GameFeature | 已交只读回执：旧Loaded入口／无消费者输出、重复闭包与GameMode准入校验、空配置提前注册资源；插件选择已由Experience资产承载，无当前主线阻断。原会话保留具体路径／行及必要生命周期保护依据，待Root合并分项。 |
| BossAI | 已交只读回执：同次选招全表校验重复；Boss在BP Spec扩展后覆盖伤害输入（实际BP覆盖未核实）。由AbilitySystem牵头收口Builder扩展顺序，角色参数保留在既有GA BP，机制不机械迁移。 |
| Combatants | 已交只读回执：Host同步本地发布经自订阅绕行、调用方遍历步骤历史取提交结果、Health同H初始化重复校验；与AbilitySystem／Character和既有R3合并，保不同寿命身份及真实外调保护。 |
| System | 已交只读回执：旧单包／Cold SUPPORT_PIN过期（当前多包Author不受影响）；持锁阶段重复重建／哈希软件证据、无消费者非反射查询、配置注释残留。运行时核心未见角色流程硬编码，后续先核Cold实际入口，不以本审查扩当前前置。 |
| Combat 命中查询 | 已交只读回执：同帧控制点／资源全链重复读取、同寿命派生状态副本可收敛；每招Shape／窗口已由GA配置及Montage承载，无已证当前主线阻断，反射旧接口先核BP消费者。 |
| Combat 玩家动作/GA 集成 | 已交只读回执：旧预输入缓存／配置／测试契约残留、显式GE同栈重复校验、玩家/Boss Montage资源持有机制重复；合并既有B1/B2/B5。GA段序、倍率、窗口及Cue已有资产配置，保双完成事实、权威与原资源清理。 |
| Physics | 已交只读回执：CMC固定组织步态／TurnBack选择，camera侧倾策略混入执行层；单源重复绑定校验、旧Locomotion Profile与未消费Move phase可收敛。由Animation／Movement牵头BP/ABP策略迁移，保预测决定、原生区间、网络配对及Action Profile。 |
| Messages | 已交只读回执：父通道失效监听注销用错通道（生产触发未核实）、属性委托契约注释与GAS重入链冲突、无消费者返回／残留状态；真实不同寿命保护保留，待Root与实际拥有者合并。 |
| 地编与测试场景工具 | 已交只读回执：旧制作入口PIE禁入不全、场景生成器未接主灯Tag、异常清理后凭据丢失及只读API前置过宽；无已证当前主线阻断，整改延期。 |
| Character 渲染子模块 | 已交只读回执：通用材质／Mesh制作诊断挂在Decal类型属职责候选，固定Profile策略每ViewFamily重建为未测优化候选；渲染机制保C++/shader，角色差异由BP/MI/组件/Profile承载，World共用Profile不可按角色复制绕权威。 |
| 资源解包（独立工具工作线） | 已交只读回执：CLI失败退出码与跳过混同、动画来源／Override／筛选重复且不一致、输入旁分片半成品可能复用、非法显式配置静默默认；Wwise执行器重复为优化候选。无BP迁移职责，存量产物影响未核实。 |
| Audio 音效 | 已补交完整只读回执：Cue预载／角色预热职责重复与说明冲突、公共Flesh Tag由空测试Cue承接（Boss实际覆盖未核）、父Burst与自定义HitImpact双播放链候选。Pyrios五独立Tag当前不受旧路由影响，选声/组合/时点继续由Cue BP/Montage配置，原版及设备听感未验。 |
| FX 特效表现 | 已交只读回执：播放合同公共校验口径不一致、同次配置重复解析FX窗口、平移／旋转时重复写相同bounds；现行角色编排已有ComboStep.FX／Montage／Cue承载，未证角色名硬编码。保GAS/发布仲裁/远端Age恢复与尾粒子生命周期。 |

当前交付后的整批收口方向：

Kiro 11-05 余项 spec 的 D 批次先核实际缺陷与独立写集。候选为 ASC 组准入测试日志（A1）、相邻换人后置检查（A3）、Sync Marker 工具归位（E1）、ZZZ 适配映射（E2）、GameplayMessageRouter 清除失效监听（E3）。E3 已由 I22 完成修复和真实自动化回归：父 Tag 的失效监听按原列表清理，子监听连续两次可收到，且不重复诊断失效父监听；当前实现及日志见 [消息路由与 SyncMarker 工具](../需求文档/refactor_and_squad_switch.md#消息路由与-syncmarker-工具)。A2/B1–B3 等 AbilitySystem／FX 写集交付；C1 等自然收尾与预测纠正验收；C2 等 Input／Character 写集交付；D1 需受控 Editor 资产窗；F1 死亡回收待玩法决定。独立项也先核真实保护交集，已验证阶段不为整理候选重开。

- 侧倾表现由Animation牵头，曲线选择／求值及角色启用策略迁现有ABP；移动选择由Movement牵头，在MovementSet／角色BP明确策略，Physics保认证事实、确定性预测及唯一执行。不得新增BP Tick、表现时钟，或在历史重放中重选当前输入。
- 角色GA/BP编排缺口由AbilitySystem牵头提供窄接口，Combat／BossAI保持现有段序、窗口与参数资产；同步收敛Builder扩展顺序、同次窗口解析与共用资源持有机制，保权威及独立生命周期。
- Camera、Input、Character分别收口角色策略硬约束和契约；DeathFinished是否必然回收Pawn等真实玩法歧义，待实施时给具体场景请用户决定。本轮不臆定新死亡资产或扩展手柄需求。
- 重复配置／几何／路由校验、镜像状态和旧入口按真实拥有者与既有R2/R3/R4/B1～B6归并；静态确认缺陷与未启用／未实测风险分开，不能为精简删除真实重入、网络、清理和反射资产保护。
- Editor Marker、制作诊断、宿主与CLI职责分别由原工具作者集中整理；旧工具或非当前生产消费者问题不作为主线新前置。角色差异不应藏在C++，通用渲染、转换、GAS／CMC机制也不机械搬BP。

审查过程与完整回执仅留原会话；本节保留当前问题、归属与未核边界。当前完整需求交付后再统一分配源码／资产写入批次、实现配置、集中编译与受影响验证；整改真正验收且保护归还后再归档，不以本次复查完成代整改完成。


### 剩余候选核对

此前用户决定：Sync Marker 归入编辑器工具整理，其余影响不大时先记录。下表按当前源码逐项核对；优化建议保持待定，已完成的共享资源与重复检查整理不重做。完整 BP／资产消费者未在本次盘点中重新审查。

确认并修复的运行缺陷为 CR-1111-D1；增量编译及六项相关自动化通过。其它条目的证据和状态分别列明，不将优化候选当作已发生的运行故障。

| 编号／所属 | 评审事实与准确入口 | 建议、优先级与后续触发 |
| --- | --- | --- |
| CR-1014-T1／Animation 编辑器工具 | [SyncMarkerImporter.cpp](../../Source/GGYGOEditor/Private/SyncMarkerImporter.cpp) 的模块迁移、反射入口与旧类路径兼容已由 I22 完成。批量／单文件仍各自清空并写 Marker，缺排序和缓存刷新；[AnimSyncMarkerTools.cpp](../../Source/GGYGO/Animation/AnimSyncMarkerTools.cpp) 有排序／刷新，但不等长数组取 Min；JSON 解析器会跳过坏条目后接受剩余数据。 | 保留工具整理事项：完整校验后原子写入、失败保持原 Marker、复用唯一写入实现；随后再迁余下工具。源码确认数据丢失风险，未重现现有资产受损。沿用户原决定单独处理，不重做 I22，不扩大本次 GAS 修复。 |
| CR-1014-B1／Combat 动作 | [ComboTypes](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOComboTypes.h) 的 Store／Consume／ExpiresAt 与 [旧纯测试](../../Source/GGYGO/AbilitySystem/Tests/GGYGOComboWindowTest.cpp) 仍在；生产 PlayerCombo 不调用这些缓存方法，InputBufferSeconds 无读取点。PendingRequestId 及窗口开闭仍有业务和纠正读写。 | 待用户确定预输入玩法后整理。可退役无生产消费者的普通方法并迁移测试；不能连同窗口字段、反射配置和网络载荷直接删掉。不恢复旧预输入。 |
| CR-1014-B2／Combat 动作、BossAI | [PlayerCombo::FStepMotionResources](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp) 与 [BossMelee::FOriginalMeleeResources](../../Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp) 当前均继承 [MontageActionResources](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOMontageActionResources.h)，共用 Task、位移、Watchdog 及释放机制。Boss 额外持有原 Mesh 与 Tick 前置依赖等自身义务。 | 已由 activation-lifecycle 完成，关闭此重复维护候选；本次只核现状，不改 Kevin 在途实现。不同 GA 的配置、接续及 Mesh 生命周期继续由各自拥有。 |
| CR-1014-B3／Input | [HeroComponent](../../Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp) 同时承担 InitState／相机协调、绑定与输入会话、移动装配和能力输入观察；PlayerInput 持设备事实，ASC 持请求及重试。未发现第二输入消费权威。 | 低优先级优化建议。需要整理时将绑定／会话资源移到 Hero 私有普通 C++ 协作者；不新增组件、Tick 或输入队列。本次不实施。 |
| CR-1014-B4／Animation | [ZZZLocomotionEvents](../../Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.cpp) 持 Context 仅映射 GaitBlendY 与 StopValue；Context::IsValid 要求未设置的 Tuning，但生产没有调用该判定，映射也不消费 Tuning。 | 维护建议，归既有 ZZZ 兼容层移除需求。保留 AnimBP 序列化字段和真实映射，等动画行为决定后一起处理；不列为已触发故障。 |
| CR-1014-B5／AbilitySystem、BossAI | [PlayerCombo::ValidateDamageEffectDependency](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp) 校验显式类及 Abstract／Deprecated／NewerVersionExists；[BossMelee::ResolveMeleeConfiguration](../../Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp) 依 RequiresDamage 检查非空。未发现现有坏 GE 触发故障。 | 中低优先级优化建议：共用纯 GE 类校验，各 GA 保留必需伤害或无伤害的正常模式。Kevin 作者在途，本次只读，不新增隐式默认 GE。 |
| CR-1014-B6／Combat 动作 | [PlayerCombo::InitializeAbilityActivation／CleanupAbilityResourcesForTermination](../../Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp) 当前均直接检查 StepMotionResources，已去掉同资源四 getter 的重复 OR；InputTask／Trace／Mesh／注册和 Initial 路由检查仍在。 | 已完成，关闭此静态重复候选。本次不重复改源码；当前工作树增量编译通过。连段与联机验收仍见各自需求。 |
| CR-1111-D1／AbilitySystem 输入重试 | 原诊断保留两条失败：内层 raw Try 的 retry 通知期望 0 实际 1，外层合法通知期望 1 实际 0；日志 `Saved/Kiro/requirements-closeout/I08/Diag_R1/Editor/editor.log`。根因：InputBuffer 只按同 Spec 第一次结果认领来源，CheckCost 内的 raw Try 先失败，抢走外层许可。 | 已修复并自验。沿原生 Can 调用／返栈记录同步层级，输入 Try 保存进入层级；仅自身 Can 可读输入来源，仅返至原层级的结果可认领。保留原生入口、失败反馈顺序、请求和截止，不加调度器或激活身份。原断言未改，原诊断及另外五项回归全部通过；[构建](../../Saved/Codex/I23_20261111/build.log)、[测试](../../Saved/Codex/I23_20261111/editor.log)。生产实机与联机未验。 |
| 旧候选 A1／ASC 组准入测试日志 | [FinalizeAbilityGroupAdmission](../../Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp) 已无测试日志块，activation-lifecycle 已迁移为外部结果断言；当前 GroupLifecycle 回归通过。 | 已完成，不重做。其它诊断日志不因名称相似一并删除。 |
| 旧候选 A3／换人后置检查 | [SwitchToSlot](../../Source/GGYGO/Teams/GGYGOSquadComponent.cpp) 的取消、输入释放、控制权回调、Possess、Tag／表现切换和最终广播后仍校验原布局；这些入口可能执行外部回调。 | 必要保护保留；此次未确认必须修改的独立缺陷。ReturnToLingeringMember 回归通过，不扩大为换人重构。 |

必要保留：外调／原生返栈后的原身份核验、先摘资源后释放、网络权限、幂等清理、合法异步等待、自然混出最后位移区间及远端 Held 节点消费证明。ASC／Task／CMC 身份事实寿命不同，不因本次精简候选合并。仅B6随本轮原Combat两源窗口顺手收敛，其余候选仍未授新实现窗口；后续只沿[当前排程](Module_Repair_Parallel_Schedule.md)及原模块作者安排，不作为当前姿态／移动／Slot／独立打断验收的新增前置。

## 历史修复编号与未验边界

2026-10-08整改的完整编号索引、旧交接及未勾选／失败／正式资产／网络／Cook边界已迁[历史索引](Module_Audit_Repair_Ledger_History_20261016.md#2026-10-19-活动历史索引迁出)。历史未验不因归档完成或取消，消费时核当前源码／资产；当前写权只查活动排程，不恢复旧租约。稳定规则只见AGENTS.md及CodeConventions。
