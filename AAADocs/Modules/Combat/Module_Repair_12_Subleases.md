# 第 12 批 Combat 文件子租约

更新时间：2026-09-30

本文件登记第 12 批 E1–E6 的唯一写入者。2026-09-30 起执行原子任务门禁：每项只有一个结果、一个精确文件集合和一个停止点；实现、测试、文档不得打包成同一子任务。批次冻结前不得把同一文件交给第二个写入者；需要换手时，原写入者先停止并报告实际 diff、验证与未完成项。

| 原子任务 | 写入者 | 精确可写文件 | 单一结果 | 非目标 | 依赖 | 断言 | 停止点 | 状态 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 12-A1 SharedBuilder | Combat 组长 `/root` | `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h`、`Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp` | 共享构造 Context、可选 Spec 与 Cue | 不提交伤害，不决定 Player/Boss 数值 | 已冻结的 EffectContext、ASC/GAS 原生 Spec/Cue API、Physics Tag 类型 | AddHit 后 AddOrigin；目标 Tag 用 const 集合追加；表面 Tag 最后追加；GE 无效仍有 Cue | 接口与实现落盘后冻结，转独立静态审查 | 已冻结，静态审查通过 |
| 12-A2 PlayerCaller | Combat 组长 `/root` | `Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp` | Player 命中改走 SharedBuilder | 不改连段状态机、Trace 或结算 | 12-A1 接口已落盘；现有 ComboStep 数值与权限门禁 | 命中回调时 Avatar 位置为 Origin；只填 SetByCaller；GE 拒绝不吞 Cue | 单文件调用点落盘后冻结 | 已冻结，静态审查通过 |
| 12-A3 BossCaller | Combat 组长 `/root` | `Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp` | Boss 命中改走 SharedBuilder | 不改 Boss 选招、Montage 生命周期或位移 | 12-A1 接口已落盘；现有 Boss 数值与权限门禁 | 与 Player 使用同一构造责任；只填 SetByCaller；碰撞 Cue 独立 | 单文件调用点落盘后冻结 | 已冻结，静态审查通过 |
| 12-B1 TraceRuntime | 临时子代理 `trace_lifecycle` | `Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.h`、`Source/GGYGO/Combat/HitDetection/GGYGOMeleeTraceComponent.cpp` | Trace 返回物理材质并统一生命周期清理 | 不改 GA、GAS、碰撞通道配置或伤害 | ActorComponent 生命周期与现有单窗口状态 | 查询请求 PhysicalMaterial；Deactivate/OnUnregister/EndPlay 幂等清端点、baseline、去重、Tick；无 AbilitySystem 日志依赖 | 两个运行时文件落盘并静态检索后冻结 | 已冻结，组长已审查 |
| 12-B2 TraceTest | 临时子代理 `trace_lifecycle` | `Source/GGYGO/Combat/Tests/GGYGOMeleeTraceSafetyTest.cpp`、`Source/GGYGO/Combat/Tests/GGYGOMeleeTraceTestReceiver.h` | 覆盖 PhysicalMaterial 与停用/注销清理 | 不直接模拟脆弱 EndPlay 世界销毁，不改运行时 | 已冻结的 12-B1 公共接口；既有合成骨架/碰撞夹具 | 返回材质指针；Deactivate/OnUnregister 清状态且重复调用安全 | 两个测试文件落盘后冻结；不运行 UE/UBT | 已冻结，待统筹运行 |
| 12-C1 EffectContext | 临时子代理 `hit_semantics` | `Source/GGYGO/AbilitySystem/GGYGOGameplayEffectContext.h`、`Source/GGYGO/AbilitySystem/GGYGOGameplayEffectContext.cpp` | Duplicate 保留 Origin，提供 Origin→HitPoint 距离 | 不改网络协议或能力来源所有权 | 引擎 FGameplayEffectContext 拷贝与 HitResult 语义 | HitResult 深拷贝后恢复显式 Origin；缺 Origin/Hit 时距离 0 | 两个 Context 文件落盘并静态检索后冻结 | 已冻结，组长已审查 |
| 12-C2 DistanceExecution | 临时子代理 `hit_semantics` | `Source/GGYGO/AbilitySystem/Executions/GGYGODamageExecution.cpp` | 距离衰减改读 Context 距离 | 不改属性捕获、免疫或元属性结算 | 已冻结的 12-C1 距离查询；既有 AbilitySource 接口 | 不读取 EffectCauser 当前位置；仍只写 HealthSet 元属性 | 单文件落盘并静态检索后冻结 | 已冻结，组长已审查 |
| 12-C3 HitCue | Combat 组长 `/root`（子代理已冻结并交回） | `Source/GGYGO/AbilitySystem/Cues/GGYGOGameplayCueNotify_HitImpact.h`、`Source/GGYGO/AbilitySystem/Cues/GGYGOGameplayCueNotify_HitImpact.cpp` | 用显式 HitResult 存在性解析位置 | 不改 Cue 资产配置或表面映射顺序 | FGameplayCueParameters.EffectContext 与目标位置 | 零坐标 HitResult 合法；无 HitResult 回退 Target；注释覆盖有/无 GE 共享载荷 | 仅修正交回后的源码注释并再次冻结 | 已冻结，静态审查通过 |
| 12-C4 HitSemanticsTest | 临时子代理 `hit_semantics` | `Source/GGYGO/AbilitySystem/Tests/GGYGOHitSemanticsTest.cpp`、`Source/GGYGO/AbilitySystem/Tests/GGYGOHitSemanticsTestTypes.h` | 第12批自有能力夹具覆盖 Context/Cue/Builder 语义 | 不改生产 API，不复用或抢写04 Admission 测试类型 | 12-A1、12-C1、12-C3 已冻结接口；测试世界和 ASC 原生授予 API | protected wrapper 经实际测试子类调用；有 GE 与无 GE 都保留 owned+surface Tag | 两个测试文件落盘、仅静态核对后冻结 | 已冻结，静态审查通过；待统筹运行 |
| 12-D1 AbilitySystem结构文档 | Combat 组长 `/root` | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/AbilitySystem/结构.md` | 记录共享载荷与距离/Cue职责 | 不改全局实施状态 | 12-A1/A2/A3、12-C1/C2/C3 最终源码 | 描述与最终源码一致并标未构建 | 单文件落盘后冻结 | 已冻结，一致性检查通过 |
| 12-D2 AbilitySystem结构Canvas | Combat 组长 `/root` | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/AbilitySystem/GGYGO_结构_AbilitySystem.canvas` | 更新命中类关系 | 不改其他 Canvas | 12-D1 术语与最终接口名 | JSON、节点与边引用有效 | 单文件落盘后冻结 | 已冻结，JSON/引用校验通过 |
| 12-D3 伤害流程Canvas | Combat 组长 `/root` | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/AbilitySystem/GGYGO_流程_伤害结算.canvas` | 更新命中到结算/表现流程 | 不改结构文档 | 12-A1/A2/A3 与 12-C1/C2/C3 运行顺序 | Cue 分支独立于 GE；Origin→HitPoint | 单文件落盘后冻结 | 已冻结，JSON/引用校验通过 |
| 12-D4 Combat结构文档 | Combat 组长 `/root` | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Combat/结构.md` | 记录 Trace runtime 生命周期 | 不改测试代码或全局状态 | 12-B1/B2 最终源码与测试边界 | 物理材质、幂等清理、日志边界与验证状态准确 | 单文件落盘后冻结 | 已冻结，一致性检查通过 |
| 12-D5 Combat结构Canvas | Combat 组长 `/root` | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Combat/GGYGO_结构_Combat.canvas` | 更新 Trace 结构接口 | 不改流程 Canvas | 12-B1 与 12-D4 术语 | JSON、节点与边引用有效 | 单文件落盘后冻结 | 已冻结，JSON/引用校验通过 |
| 12-D6 Combat流程Canvas | Combat 组长 `/root` | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Combat/GGYGO_流程_Combat.canvas` | 更新 Trace 运行流程 | 不改结构 Canvas | 12-B1 生命周期与 12-A caller 交接 | 生命周期入口与共享载荷交接准确 | 单文件落盘后冻结 | 已冻结，JSON/引用校验通过 |
| 12-D7 Physics结构文档 | Combat 组长 `/root` | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Physics/结构.md` | 记录物理材质语义路径 | 不改 Physics 资产 | 12-B1 查询与 12-A1 Tag 注入 | Trace 请求、Builder 双路注入准确 | 单文件落盘后冻结 | 已冻结，一致性检查通过 |
| 12-D8 Physics结构Canvas | Combat 组长 `/root` | `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Physics/GGYGO_结构_Physics.canvas` | 更新材质语义图 | 不改文档或资产 | 12-D7 术语与最终接口名 | JSON、节点与边引用有效 | 单文件落盘后冻结 | 已冻结，JSON/引用校验通过 |

## 冻结与集成约束

- 临时子代理不得修改表外文件，不得操作 UE、构建、Git、提交或资产。
- 共享构造接口仅由 12-A1 写入；Caller 只消费，12-B 与 12-C 不猜测或改写该接口。
- 已同时落盘的 12-A1/A2/A3 停在当前最小安全点，按三个原子项分别静态审查；任一修正只重新开放对应文件行。
- 每个原子项完成后先冻结自己的文件，由 Combat 组长复核实际 diff 后再更新状态；测试与文档不能替生产实现标完成。
- 全部源码写入者冻结后，只向统筹交付静态检查和专项测试建议；统一 UHT、完整构建、自动化、UE 与 Git 仍由统筹执行。

## 12-E4-T1：载荷 Spec / Context / 目标捕获专项

2026-09-30 统筹已接受阶段预检并明确授权本步骤；组长直接执行，不创建代理。上表旧代理及范围是历史记录，不构成当前派发权限。

| 阶段 | 精确文件 | 唯一结果与停止点 | 当前状态 |
| --- | --- | --- | --- |
| 契约登记 | 本文件 | 登记三文件范围、基线、断言与非目标后进入实现 | 已登记 |
| 测试实现 | `Source/GGYGO/AbilitySystem/Tests/GGYGOHitSemanticsTest.cpp` | 仅追加普通 Editor 叶 `GGYGO.AbilitySystem.HitSemantics.PayloadSpecContextAndTargetCapture` 及必要 scope guard/include；静态审查后冻结 | 本步骤冻结；统筹第22轮构建通过、新叶 Success，详见 Validation 第8.4节 |
| 验证记录 | `AAADocs/Modules/Combat/Module_Repair_12_Validation.md`、本文件 | 源码冻结后记录实际 hash、旧全文保持与未运行边界，随即交回 | 已记录，随本次交接冻结 |

- cpp 起始 SHA256：`4A373D6D48B93574BD5CAED6571D9B1A3C41C58274A9ABD9D49041DE2C2F15D8`；共享 types 头起始 SHA256：`5566A3BC969EBDF27457143909D081FE8B115758D4DC0B6F51B8C448D68496FF`。
- 只读依赖：现有真实 World/WorldContext、已注册并初始化的 ASC、真实 GiveAbility/TryActivateAbility 与窄化能力 wrapper；已冻结的 Builder、项目 EffectContext、引擎 Spec/公开目标应用回调。无需新反射类型或额外文件。
- 严格前置：World/context、ASC 注册与权威、Owner/Avatar、授予句柄与激活实例、项目 Context 类型均有效。
- 构造阶段：实际 Spec 的 SpecTags/聚合 Tags 含 Surface；Cue 含 Owned+Surface；Spec 的目标 Owned 必须由原生目标应用捕获，不能手工灌入或要求 Builder 提前生成。
- 三份 Context：Payload/Spec/Cue 指向同一项目对象；显式 Origin、Hit 目标/点/法线/物材身份正确；修改输入 Hit 不污染载荷。
- 应用阶段：SourceASC 应用空基础 Instant GE，通过 Target 公开 `OnGameplayEffectAppliedDelegateToSelf` 的真实副本观察 Owned ActorTags、Surface SpecTags 与二者聚合；回调一次、来源正确、Context 保持。Instant 成功检查 `WasSuccessfullyApplied()`，不以持久句柄 `IsValid()` 判断。
- Duplicate：Context 与 HitResult 地址独立，原内容及材质对象身份保持；只改副本不能污染原三 Context。回调内复制 Spec，scope guard 在 GA 结束/World 销毁前解绑，材质强引用覆盖全部断言。
- 非目标：旧三叶/helper 全文、types 头、所有生产接口与其它测试保持；不做 E6 移动/Execution、EndPlay、真实 Player/Boss、Obsidian/资产/全局记录；不改 GE CDO、不屏蔽日志、不修生产使测试绿。
- 构建、UE、Git 仍由统筹安排；需要新类型、接口或第四文件时立即停止交回，不扩大范围。

### 本步骤冻结证据

- 最终 cpp SHA256：`05254281C0D624F56B827062CB3F99887754DDC162AF4AF7ABC360F2CD4B643D`。源文件仅增加 `Misc/ScopeExit.h` 与独立测试块（197 行，含分隔空行）。
- 只读逆向去掉该 include 和新测试块后，与实施前原文件全文精确一致；重建 SHA256 回到 `4A373D6D48B93574BD5CAED6571D9B1A3C41C58274A9ABD9D49041DE2C2F15D8`。既有 World/ASC/Finish helper 与两项 HitSemantics 叶未改。
- 原第三叶所在 MeleeTrace 测试 cpp、共享 types 头及 Builder/Context 生产 h/cpp 均与本步骤开始时 hash 相同；未修改表外文件。
- 新测试实际读取构造 Spec 与回调内复制的应用 Spec；未手工写 CapturedTargetTags。公开回调 scope guard 在 FinishAbility 与 World RAII 前析构；物材强引用覆盖输入修改、应用和 Duplicate 断言。
- 本步骤交回时已核对 UE 5.8.1 的公开 API 和同步调用链，当时未运行编译/链接、UE、自动化、Git、资产保存或代理，尚无 Success/Fail。随后统筹第22轮实际构建/加载并运行本叶为 Success，见 Validation 第8.4节；该后续结果不覆盖12-E6-T1。

## 12-E6-T1：实际 Execution 距离快照专项

2026-09-30 统筹接受只读预检并明确批准以下四文件。组长直接完成；生产接口、旧测试及其它图文保持冻结，统一构建/自动化由统筹安排。

| 阶段 | 精确文件 | 唯一结果 | 非目标 / 只读依赖 | 验收断言与停止点 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 契约登记 | 本文件 | 固定四文件范围及原始全文/hash | 不授予其它范围 | 基线保存后进入测试类型 | 已登记 |
| 测试类型 | `Source/GGYGO/AbilitySystem/Tests/GGYGOHitSemanticsTestTypes.h` | 追加 AbilitySource 观察 UObject 与生产 DamageExecution Instant GE | 不修改原能力 wrapper，不替代 Execution；只读 Source 接口、生产 Execution | UObject 合法反射及 Outer、GE 唯一 Execution 为生产类；静态审查后冻结 | 保持冻结；统筹第25轮完整构建通过 |
| 独立测试叶 | `Source/GGYGO/AbilitySystem/Tests/GGYGOHitSemanticsTest.cpp` | 追加 `GGYGO.AbilitySystem.HitSemantics.DistanceExecutionUsesOriginSnapshotAfterCauserMove` | 旧 helper/三个叶全文保持；只读 SharedBuilder、Context、ASC、CombatSet、HealthSet | 实际移动距离 5→13，同一 Spec 两次真实应用，来源仅收到 [5,5]、Health 100→86→72、Damage 清零；静态审查后冻结 | 保持冻结；统筹第25轮本叶实际Success，详见Validation第9.4节 |
| 验证记录 | `AAADocs/Modules/Combat/Module_Repair_12_Validation.md`、本文件 | 源码冻结后记录 Gate22、静态证据、四 hash 与未运行边界 | 不写 Obsidian/全局记录，不用旧门禁冒称新叶成功 | 记录完成交回，四文件停止写入 | 已记录，随本次交接冻结 |

- 起始 SHA256：cpp `05254281C0D624F56B827062CB3F99887754DDC162AF4AF7ABC360F2CD4B643D`；types `5566A3BC969EBDF27457143909D081FE8B115758D4DC0B6F51B8C448D68496FF`；Subleases `704934D52BAA5C6776F5976B7A05CB3DF2D2B268B02E938D300B8569FB9075D4`；Validation `9A8A6CD9B8FC13EF166AE866A21B8E7B30089821EDA8F3A5ECB04C8E6AC8E6FA`。四文件原始字节全文已在本会话内存保存，便于只读逆向核对。
- 依赖顺序：契约 → 测试类型 → 独立叶 → 源码冻结 → 记录。无需修改任何生产接口；SourceObject 必须经真实 GiveAbility Spec → GA MakeEffectContext → Context AbilitySource 接入。
- 强前置：World/context、双方 ASC 注册/权威/Owner/Avatar/Actor 发现路径、项目 Context 工厂、真实授予/激活、属性集 Actor Outer/ASC 归属/初始化、生产 Execution 捕获定义、Instant GE 配置均严格有效；失败立即停止后续业务断言。
- SourceActor 自有 SceneRoot 设 Movable 并注册，严格检查 SetRootComponent/SetActorLocation 返回、Actor/Root 坐标与实际变化。初始 `(10,20,30)`，Hit `(13,24,30)`，移动到 `(13,24,43)`；显式距离 5，移动后当前位置距离 13。
- 来源对象以 SourceActor 为 Outer，并由强引用覆盖全部使用；只记录生产 GetDistanceAttenuation 的调用参数，返回 `1 / (1 + Distance)`。GE 只配置一项生产 `UGGYGODamageExecution`，不手调 getter/Execution、不复制结算、不改 CDO。84 来自真正源 CombatSet 捕获，无 SetByCaller 覆盖。
- 两次公开目标应用回调复制实际 Spec，并检查来源 ASC、同一 Context、EffectCauser、AbilitySource、Origin 标志/值及 Hit；Instant 成功检查 WasSuccessfullyApplied，不要求持久有效句柄。
- RAII：解绑本叶观察 → GA End → ClearAbility → 移除本叶属性集 → 强引用退出 → 已有 World RAII。Root/ASC 为 Actor 自有组件；无持久 GE 资源。不引入另一套伤害状态或执行器。
- 非目标：真实 Player/Boss、EndPlay、消息、生产资产、PIE/联机、旧 rootless 断言、Obsidian/Canvas、全局状态及生产修复。需要第五文件、新接口或生产 fix 时立即冻结交回，不扩大范围。

### 12-E6-T1 冻结证据

- 最终 cpp SHA256：`25568066A9A881325237EA34D2F56B7A910C80F4E16E85ECB26BFC9757323E25`；types SHA256：`DEB5DB58F3DE17833084DBE8F9F56E106C4C7CF0473A58C2EE04C570D4628C21`。cpp 仅新增三条 include 与独立测试块，共211行；types 仅新增三条 include 与两个独立测试类型，共43行。
- 在内存中只读移除新增区间/include，恢复字节 Base64 与实施前保存的原始字节逐字节一致。恢复 SHA256 分别为 `05254281C0D624F56B827062CB3F99887754DDC162AF4AF7ABC360F2CD4B643D`、`5566A3BC969EBDF27457143909D081FE8B115758D4DC0B6F51B8C448D68496FF`；旧三个叶/helper/原能力 wrapper 完整保持。
- 静态核对公开 SourceObject 授予、项目 Context factory、生产 capture 定义、真实 Native Apply/Execution/HealthSet 路径及清理顺序。新叶没有直接调用衰减 getter、Execution 或 Context 距离 helper，没有 SetByCaller 写入、ExpectedError/日志抑制、CDO 运行时改写或业务 fallback。
- 测试中的来源公式是明确选择的夹具配置；World、接口、属性集、捕获、Root、移动、授予和应用失败均有命名断言并立即停止后续业务验证，符合最新“禁止隐式业务兜底”约束。
- 源码、两记录在12-E6-T1交回时冻结，当时尚未UHT/编译/链接、加载或执行；Gate22不涵盖本叶。随后统筹第25轮完整构建及本叶实际运行通过，见下方12-E6-V1与Validation第9.4节。组长未操作UE/构建/Git/资产/代理；记录最终hash由交回消息提供，避免文档自身hash循环。

## 12-E6-V1：第25轮有限距离 Execution 证据同步

2026-09-30 统筹明确仅授权两份记录；组长直接完成。唯一目标是登记已真实完成的第25轮构建/自动化及本叶有限契约，不实施下一源码步骤或兜底修复。

| 文件 | 唯一结果 | 只读依赖 / 非目标 | 验收与停止点 | 状态 |
| --- | --- | --- | --- | --- |
| 本文件 | 登记V1范围、历史/当前状态及证据交接 | 已冻结的测试pair与Gate25原始报告；全部源码/测试/Obsidian/资产只读 | 与报告及Validation一致，交回hash后冻结 | 已核对并冻结 |
| `AAADocs/Modules/Combat/Module_Repair_12_Validation.md` | 更新当前状态并追加第9.4节真实门禁 | 不覆盖旧历史，不把有限合成链路扩大为生产验收 | 新叶Success/耗时/entries、构建、59项计数、UE退出与开放项准确，交回即停止 | 已同步并冻结 |

- 两记录起始SHA256：Subleases `A1293836485E273725C1C5C6C1B7B2C8EE2652993D760C1536A9706E07069CEE`；Validation `966DB29A5D5518DAE297B2B2A8EC9566F8DF9E910DF246E4991757590795B526`。
- 顺序：只读核对Gate25原始证据及冻结源码hash → 登记两文件契约 → 更新Validation → 一致性核对/交回hash → 两记录冻结。
- 测试pair仍为cpp `25568066A9A881325237EA34D2F56B7A910C80F4E16E85ECB26BFC9757323E25`、types `DEB5DB58F3DE17833084DBE8F9F56E106C4C7CF0473A58C2EE04C570D4628C21`。本步骤不修改它们，不改变原断言或生产实现。
- 第25轮完整构建Succeeded，4 actions、13.08秒；常规报告59/59 Success，0 failed/succeededWithWarnings/notRun/inProcess、所有用例errors/warnings0。新距离叶Success，0.009482499212026596秒、entries为空；UE日志59 tests performed、RequestExitWithStatus退出码0。详见Validation第9.4节。
- 仍开放真实Player/Boss调用者、EndPlay、生产资产、PIE/网络；原rootless旧断言局限、图文漂移及三项业务替代候选均不在V1修复范围。禁止UE/构建/Git/代理/资产操作；需要第三文件或新结论时停止交回。
- 两记录已完成一致性核对并冻结。只读按fullTestPath比对Gate22与Gate25：旧55项缺失0、非Success或errors/warnings非零0。所有未提交改动与历史保留；本步没有源码写入或生产/兜底修复，最终两hash交回后停止。

## 12-StrictCapture-I：伤害 Execution 两项基础输入拒绝契约

2026-09-30 统筹接受零写入预检并明确批准以下三文件，由组长直接实现。唯一目标是闭合BaseDamage/BasePoiseDamage所选来源缺失或非法时的明确诊断与本Execution无新增输出，不传播整个GE/GA应用失败。

| 阶段 | 精确文件 | 唯一结果 | 只读依赖 / 非目标 | 验收断言与停止点 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 契约登记 | 本文件 | 固定三文件范围、基线和保护段 | 不开放其它范围 | 保存原始字节并登记后进入实现 | 已登记 |
| 生产实现 | `Source/GGYGO/AbilitySystem/Executions/GGYGODamageExecution.cpp` | 两项各自解析明确SetByCaller或必需capture，任一失败诊断并不新增Modifier | 原生Spec公开map/capture、既有GAS日志；不改constructor/statics、衰减/Context/公式/Health输出尾部 | 有键有限非负含零则覆盖且不要求capture；非法覆盖不回捕获；无键必须capture成功且有限；两项全通过才进入旧尾部；静态审查后冻结 | 已静态审查并冻结；未编译/运行 |
| 验证记录 | `AAADocs/Modules/Combat/Module_Repair_12_Validation.md`、本文件 | 记录实际差异、保护证据、架构核对与未运行边界 | 测试另步，源码/头/测试/Obsidian/Canvas/资产继续只读 | 最终三hash交回即冻结停止 | 已同步并冻结 |

- 三文件起始SHA256：cpp `77A64CCF63F735A7138B6F57FC636807A83DFB324DF563B3116CF6239195F4A1`；Subleases `F5D1F42813D79E5ECC82EDD2F4A47866964F8C030454DE3ACF7D8547F0FC5936`；Validation `FCF5E5923949E02BD4681899D86271F7D80D03A458F0026AF689AC0552CDFF64`。原始字节全文已存本会话内存，供只读逆向核对。
- 执行顺序：契约 → 单cpp实现 → 完整差异/逆向与保护段核对 → 源码冻结 → 两记录同步 → 三文件冻结交回。无新公共接口、状态、缓存或执行器。
- 每项按`Spec.SetByCallerTagMagnitudes.Find`判断存在性。有键必须有限且非负，零合法；不调用该项capture。显式负值/NaN/Inf失败且不回capture。无键必须实际AttemptCalculateCapturedAttributeMagnitude为true且值有限；缺失不能以初始0冒充成功。有限负capture沿用原最终非负公式，不新增CombatSet值域规则。
- 两项均解析成功后才进入既有衰减与输出；任一失败，本Execution不新增任何Modifier，也不Reset/清除调用方既有输出。每次拒绝复用LogGGYGOAbilitySystem输出一条含Execution/GE/Source与Target ASC/字段/来源/原因/值的诊断；没有Tick日志或持久抑制缓存。
- native Execute为void且输出无应用失败标志，本步只能承诺诊断及无新增Modifier，GE句柄仍可能成功；不冒称GE/GA已拒绝，不改HealthSet/GA/Cue或条件效果行为。
- 保护constructor/statics与原衰减/Context/公式/Health输出尾部，GGYGODamageExecution.h及全部测试不改。未获授衰减非法数值、乘积溢出、其它业务替代和Movement/Editor读取不在本步。
- 第26轮完整构建及60项通过是新增实现前门禁，不涵盖本步；专项测试另步。禁止UE/UBT/Git/资产/Obsidian/代理；需第四文件、新接口或扩大生产契约时立即冻结交回。

### 12-StrictCapture-I 冻结证据

- cpp最终SHA256 `96074463D24F206EF6E49CC27746BFD3B117E0510D083B7AC38EFEAD16FF6134`。完整差异仅两include与基础输入区间20→64行，净增加46行。新增结果只为本次调用的栈上派生值，日志字符串仅拒绝时构造；没有新公共接口、持久状态/执行器或额外清理生命周期。
- 内存中只读删除两新include、将新区间换回保存的原20行后，原始字节Base64逐字节一致，恢复SHA256 `77A64CCF63F735A7138B6F57FC636807A83DFB324DF563B3116CF6239195F4A1`。前保护段SHA256 `AB5536DEB4BE0489EEA6E168B7357DBFB3CDF9152EB2B897DF983A74B7EA0A7B`；距离/材质衰减注释起至EOF尾段SHA256 `65F2D3B56BC00E276D1252D5DC445EC218526857B1468E8D2B7C58E4CA748C69`；两段均精确保持。
- Execution头与旧HitSemantics测试pair hash保持，未加入测试或诊断夹具。已只读核对公开map/capture API、日志类别及架构职责；输入失败图文分支待另步精确租约同步，本步Obsidian/Canvas继续冻结。保护范围与未关闭项见Validation第10节。
- 新实现未UHT/编译/链接、加载或运行；第26轮60/60只属于此前版本。后续测试另步，三文件现在冻结并交回最终hash，不自动实施下一步，不操作UE/构建/Git/资产/代理。

## 12-StrictCapture-T / B6：基础输入真实原生专项

2026-09-30 统筹接受零写入预检，明确授权以下三文件。组长直接完成；两份记录只追加，原文完整保留。全部生产、旧测试、头文件、资产、Obsidian/Canvas、全局入口继续冻结。

| 原子步骤 | 精确文件 | 唯一结果 | 只读依赖与非目标 | 验收断言 / 停止点 | 状态 |
| --- | --- | --- | --- | --- | --- |
| 契约登记 | 本文件 | 固定 B6 三文件范围和八场景族 | 不扩大租约；记录原文只追加 | 原始字节保存后进入新 cpp | 已登记 |
| 单专项 | `Source/GGYGO/AbilitySystem/Tests/GGYGODamageExecutionStrictInputTest.cpp`（新文件） | 一个 Editor 叶通过真实 World/ASC/Spec/native ExecutionParams/公开 Execute 检查 T1a 六族契约 | 复用只读 `UGGYGOHitDistanceTestEffect`；不新增 UCLASS，不改生产、旧测试或 types | 严格前置、精确 Error、输入及输出保持；静态审查后冻结。需第四文件或生产修复时停止交回 | T1a 已落盘；未编译/运行 |
| 记录与交回 | 本文件、`AAADocs/Modules/Combat/Module_Repair_12_Validation.md` | 追加 Gate27 边界、B6 证据与最终三 hash | UE/构建/Git/资产/代理由统筹管控；图文仍只读 | 原记录字节前缀、生产/旧测试 hash 保持后全部冻结 | 待源码冻结 |

- 起始：新 cpp 不存在；Subleases SHA256 `4137EC03573D95CDDC89B04DAB48390E3BDA01118EAA11160578DB01F8664659`；Validation SHA256 `1DB2EDDB33D8CEBC58498AC7F1EB01642E5736801124AA5EEA95968DACDAAC1B`。两记录原始字节已保存，最终只读核对全部原文前缀保持。
- 顺序：契约 → 单 cpp 夹具和参数化叶 → 原生 API/差异/保护核对 → 源码冻结 → 两记录追加 → 三文件交回。没有共享接口变更或调用方适配。
- 八场景族：正常双捕获及真实应用一次；无 CombatSet 的双明确覆盖；捕获零/覆盖零；双向混合来源；双向有限负捕获；双向缺必需捕获；双向负/NaN/Inf 明确覆盖且正常捕获可供回退；双向真实 NaN/Inf 捕获。预期结果为常量，不复制生产 resolver。
- 属性集 Actor Outer、ASC 注册/权威/Owner/Avatar、Actor 发现、项目 Context 工厂、Instant 单生产 Execution、无普通 Modifier/Cue/scoped modifier、源 snapshot capture 定义均须真实有效。非有限值经公开 Init 在注册和聚合器创建前设置，实际原生 getter 必须成功且返回非有限；不能用 mock、const_cast 或强改 Spec 捕获内容。
- 每个拒绝子例分别使用独立夹具检查空输出和预填 Healing sentinel 保持；相关 Spec 定义/Context/来源/等级/层数、SetByCaller 键和值 bit、capture getter 结果及 tag 语义保持。NaN 按值位核对，不复制全部 Spec 内部缓存。
- 预期日志在前置成立后才登记完整 `LogGGYGOAbilitySystem: ...` 文本，`Plain / Error / Exact / 1`；每次调用的路径独立，避免原生 expected-message set 合并重复键。RAII 原生日志观察器另核对原始 category、Error severity、全文及恰好一次，不屏蔽日志。
- 正常双捕获只实际 Apply 一次，断言 Health 100→88、Poise 50→46、meta 消费为零。拒绝分支仅承诺本 Execution 无新增输出，不宣称 native GE/GA 应用失败。
- 清理：移除日志观察器 → params/output/Spec 析构 → 移除本夹具属性集/强引用退出 → Actor 自有 ASC 随 World 销毁并移除 WorldContext；不全局重置 GE 句柄表。
- Gate27 已实际构建生产 StrictCapture-I（9 actions、87.41 秒），原 60 项 Success；新 B6 叶未包含，不能以该门禁证明新矩阵。构建和运行等待统筹统一安排。

### B6 颗粒度调整：T1a 实际范围

统筹在实施期间要求先形成可审查源码，将本步收束为原第1～6场景族；原第7非法覆盖、第8非有限捕获改为接续原子步骤。以上八族为初始预检，公开 Init 非有限捕获 API 结论保留，但未写成 T1a 已实施或已验证。

- T1a 实际11子例：正常双捕获、无 CombatSet 双明确覆盖、双捕获零/双覆盖零、双向混合来源、双向有限负捕获、双向缺必需捕获以及双缺捕获。3个拒绝子例各用独立空/预填夹具，共14次公开生产 Execute；正常例另有一次真实 Apply 断言。
- 非法明确覆盖（负/NaN/Inf）与真实非有限捕获尚未加入源码，需统筹接续授权后追加此同一叶；本步不宣称这两族关闭，也不把有效捕获等同于有限性专项证明。

### B6-T1a 冻结交回证据

- 新cpp已静态审查并冻结：424行，SHA256 `95504F83DA0A939F8A7C897D2B26AEA3E497A79343A9D425C7764E0F694FCA87`。一个 Editor 叶、11子例、14次公开生产Execute、正常例一次公开Apply；仅前六族，未UHT/编译/链接、加载或运行。
- 实际拒绝的三个子例各独立空/预填输出；真实无CombatSet及native getter失败、完整Plain/Error/Exact/1诊断、原始类别/严重级别/恰好一次观察、相关public Spec与值位保持均已写入。未改日志抑制、未const_cast、未创建代理、未调用UE/构建/Git/资产操作。
- 生产cpp/头及旧测试pair保持基线hash：`96074463D24F206EF6E49CC27746BFD3B117E0510D083B7AC38EFEAD16FF6134` / `3B5C8EC85C7AE338DF60BAD94D3D6A2B005FD601AEC97E4B8BF7DE49A3389B86` / `25568066A9A881325237EA34D2F56B7A910C80F4E16E85ECB26BFC9757323E25` / `DEB5DB58F3DE17833084DBE8F9F56E106C4C7CF0473A58C2EE04C570D4628C21`。
- Subleases原25037字节、Validation原36286字节前缀与各内存保存Base64精确一致；只追加本步范围、颗粒度调整、Gate27与证据。未改旧记录或全局/Obsidian/Canvas。
- 本步三文件现在冻结。非法覆盖和非有限capture为明确未完成接续项；等待统筹静态审查、统一构建/自动化及接续授权，不自动进入下一步骤。最终两记录hash随三文件交回消息给出，避免在自身内容内写自指hash。

## B7 / 12-StrictCapture-T1b：非法明确覆盖不回退 capture

统筹接受 T1a 实际 Gate29 后明确授权本原子步骤；组长本人直接执行。顺序为契约登记 → 同一 cpp 追加第7族 → cpp差异/逆向/保护核对并冻结 → 两记录追加 → 三hash交回并停止。

| 原子步骤 | 精确文件 | 唯一结果 | 只读依赖 / 非目标 | 验收断言与停止点 |
| --- | --- | --- | --- | --- |
| 测试扩展 | `Source/GGYGO/AbilitySystem/Tests/GGYGODamageExecutionStrictInputTest.cpp` | 两字段各负3/NaN/+Inf/-Inf明确覆盖，共8例 | 原helper、第1～6族断言、生产、旧types/E6、反射头均冻结；不加入第8族 | 源CombatSet12/4且两native capture成功；每例空/预填各一次，完整Exact Error1、输出和Spec保持。仅必要limits include/常量/8case；需helper改动或第四文件时停止交回 |
| 局部记录 | 本文件、`AAADocs/Modules/Combat/Module_Repair_12_Validation.md` | 追加Gate29旧T1a实际结果和本步证据 | 两记录原文完整保留；Obsidian/Canvas/资产/全局入口冻结 | 不把Gate29写成新增第7族已运行；三hash交回停止 |

- 起始cpp SHA256 `95504F83DA0A939F8A7C897D2B26AEA3E497A79343A9D425C7764E0F694FCA87`；Subleases `7C148DB252137C5FA9650AF7B72D094DBF8371023BBA9646A1E82579A9B0FD67`；Validation `1F6B3C24A9E9FC64A4B1FEBF421F22AB0220925575B1EF1AFF9A0C0C59909DA8`。三文件原字节已保存，旧cpp可内存逆向精确恢复，记录只追加。
- 第7族直接复用既有真实fixture/helper及严格断言，不修改生命周期或生产接口。正常capture可供潜在错误回退，拒绝必须保持整个输出；另一字段保留真实有效capture。无mock、const_cast、日志隐藏或生产fix。
- 第8族真实非有限capture、真实Player/Boss/GA调用者、正式资产/PIE/联机/专服等仍不在本步。构建/UE/Git/资产/代理均不调用；如违反范围立即冻结。

### B7 / T1b 冻结交回

- cpp冻结SHA256 `6DBF89F3E703767330683C58DF8B1CF91DDB028861B7F63D2CFFA8DE2CAC7FAB`；仅limits include、2常量、8case及范围注释/末行逗号，净增13行至437行。只读内存逆向恢复原始字节精确一致，回到 `95504F83DA0A939F8A7C897D2B26AEA3E497A79343A9D425C7764E0F694FCA87`，helper/第1～6族严格断言保持。
- 新8例两字段各-3/NaN/+Inf/-Inf，真实CombatSet与native captures12/4有效，空/预填各一次新增16次Execute；完整Exact Error1、全部输出保持和public Spec/value bits保持复用原严格helper。未编译/运行，不能以Gate29旧T1a Success替代。
- Gate29实际5 actions/15.87秒，63/63 Success；T1a叶0.061809998005628586秒、entries空、errors/warnings0，实际6条capture失败拒绝。统筹确认新DLL及UE26112退出；本组长只读原报告/日志。
- 两记录只追加；原31054/44343字节prefix与各保存原文Base64精确一致。生产cpp/头及旧HitSemantics cpp/types保持本步基线hash，没有第四文件或公共接口/生命周期变化。
- 三文件交回最终hash后立即冻结。第8族、真实调用者、正式资产/动态场景和图文同步等仍未关闭，详见Validation第12节；不自动实施下一步。

## B8 / 12-StrictCapture-T1c：真实非有限capture拒绝

2026-10-01 统筹接受零写入预检并正式授权唯一三文件。顺序：本文件契约/基线登记 → cpp最小适配及六例 → 静态差异/逆向保护并冻结源码 → 两记录追加 → 三hash交回停止。

| 原子步骤 | 精确文件 | 唯一结果 | 非目标 / 只读依赖 | 验收与停止点 |
| --- | --- | --- | --- | --- |
| 第8族专项 | `Source/GGYGO/AbilitySystem/Tests/GGYGODamageExecutionStrictInputTest.cpp` | 两字段各NaN/+Inf/-Inf真实capture，无SBC，另一输入正常12/4 | 原前七族case、生产/旧types/E6/接口冻结；仅两处初始化/捕获NaN比较适配，额外真实非有限前置及六case | 每例空/预填各一次，getter true且非有限、另项正常；完整CapturedAttribute/non-finite Error1、输出及public Spec/value bits保持。原生清洗/拒绝时前置原样失败，需额外文件/类型/生产修复即停止 |
| 局部记录 | 本文件、`AAADocs/Modules/Combat/Module_Repair_12_Validation.md` | 追加Gate30旧T1b结果与T1c静态证据 | 原文只追加；Obsidian/Canvas/资产/全局入口冻结 | 不把旧门禁写成新第8族已运行；交三hash冻结 |

- 起始cpp `6DBF89F3E703767330683C58DF8B1CF91DDB028861B7F63D2CFFA8DE2CAC7FAB`；Subleases `22370A6FE01A7569EDE61C3EA3B59E605F600D7C7D60A09B68FBA122434996C8`；Validation `D337C6CD12B7153B029B0E637EF9EDAE17F36D8B393F01CC1299B89370A03A97`。三文件原始字节已保存；两记录原34253/48075字节最终prefix核对。
- 源属性由真实CombatSet公开Init在注册和aggregator创建前初始化，后续仅实际MakeOutgoingSpec/native捕获/Execute。没有手工修改Spec捕获缓存、伪造getter、const_cast、新类型或绕过执行链。有限值和±Inf原严格比较保持，只有预期NaN使用IsNaN；不能接受finite或缺capture。
- 状态归属仍为CombatSet源属性、GAS真实snapshot、生产Execution结算、HealthSet落地；既有RAII保持。禁止UE/构建/Git/代理/资产/Obsidian/全局入口，不自动其它矩阵。

### B8 / T1c 冻结交回

- cpp SHA256 `4D62D94FB6FD28DB99C3A28B9C62028AFF6A91CAB54E8D5A93EA1C32CE2DA594`；四处差异24新增/5删除，净增19行至456行。仅两处NaN比较适配、真实非有限额外前置、范围注释/末行逗号及六case；完整diff见Validation13.3。只读逐hunk逆向恢复原始字节精确一致及起始 `6DBF89F3E703767330683C58DF8B1CF91DDB028861B7F63D2CFFA8DE2CAC7FAB`。
- 新六例空/预填新增12次Execute；实际getter必须true且非有限、另项正常且无SBC，再要求CapturedAttribute/non-finite完整Exact Error1、输出/public Spec/value bits保持。前七族case和其它严格断言、生产及既有RAII保持。新第8族未编译/运行，不能以Gate30旧T1b通过替代。
- Gate30真实7 actions/43.46秒、63/63 Success，旧T1b叶0.05470239743590355秒、entries空/0errorwarning，日志实际22条拒绝；报告65A1C9387911E0A4B64C04236C7B8F46525D8266D0878B93EA267B56E0BEBD23。统筹确认13源码hash保持及三个UE窗口退出，本组长只读证据。
- 原34253/48075字节记录prefix精确保留，只追加本步和Gate30；生产cpp/头与旧HitSemantics cpp/types保持本步起始hash。没有新反射类型/生产接口/资产/UE/构建/Git/代理或图文写入。
- 三文件交回hash后立即冻结。累计八族仅代表已编写；真实调用者、EndPlay/消息/资产/网络、其它数值风险和图文同步仍开放，详见Validation13.2，不自动下一步。
