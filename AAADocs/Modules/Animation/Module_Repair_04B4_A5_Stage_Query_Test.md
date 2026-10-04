# 04B4 A5 Stage-Q：真实作用域阶段专项

日期：2026-10-01（Asia/Shanghai）。Animation 运行时组长直接执行，`gpt-6.1-sol / xhigh`，不开代理。

## 当前状态与 A5-V1 两记录预检

当前：第36次完整 `GGYGOEditor Win64 Development` 构建已 Succeeded，本记录五个 StageQuery 叶在新运行时 DLL 上实际全部 Success、每叶 entries=[]/0 Error/Warning。原65路径保留并继续 Success，正常报告共70 Success。V1 两记录已完成证据同步并冻结停写，Q专项cpp与Animation Guard/types/Base自身文件继续冻结；本专项只证明有限阶段契约，不授 ASC/Task 权限或生产 AnimClass 迁移完成状态。

排程 J4/A5-V1 已获统筹授权，唯一结果为两记录同步36实际证据。精确可写范围仅 `AAADocs/Modules/Animation/Module_Repair_04B4_A5_Stage_Query.md` 与本文件。开始 SHA256 分别为 `0F0C4FD50BFFF25071D3D167E34474A742BAC932DE59202FA40646C12CEA19B7` / `48F999AA9CB51A2083190D4BD854A84684CFF6EFC20A888A300579EF2EB38350`，是历史基线，最终更新后另交 hash。先登记本预检/基线，再标记所属历史、追加36证据，核对原历史可逆保持及自身保护，交回后停写。

验收：原夹具/断言/静态证据和旧 P1 失败边界保留；当前编译及五叶实跑状态准确，report/hash/逐叶耗时/原日志分类不混淆。Q 历史表中的旧 I 记录 hash 不改写为新 hash，也不冒称 V1 两记录更新后仍属当前保护结果。K4-I1 ASC、P1-T1 新测试另有写入者；248源/14保护仅属统筹36窗口历史稳定证据，不作当前全局源码不变声明。

只读依赖为原 I/Q 全文、自身 Guard h/cpp、Q cpp、types/Base、36报告/构建及原日志、35旧路径集合。禁止 source/test/Obsidian/旧04B4记录/11记录/第三文件/资产/UE/构建/Git/代理。需第三文件、修改生产或真实证据不符即停止交回；两记录冻结后无续写权。

以下原 Q 阶段预检、基线及未编译交回均为历史；当前36实际结果见本节与末尾追加段。

## 原 Q 阶段授权与原子步骤预检（历史）

统筹接受并冻结 A5-Stage-I 后，排程 J3 单独授权以下两个新文件；开始时均不存在：

1. `Source/GGYGO/Animation/Tests/GGYGOMontagePlayGuardStageTest.cpp`
2. `AAADocs/Modules/Animation/Module_Repair_04B4_A5_Stage_Query_Test.md`

唯一目标：通过真实公开 Scope、原生 `Montage_Play` / Started、Complete、析构及动画生命周期，验证 A5 即时只读阶段查询。Animation 仍独占 ScopeChain/阶段/封存及原生实例观察；本步只有自动化夹具和断言，不新增生产权威状态、执行器或 ASC 来源协议。

依赖顺序：A1/A4/A5-I 已冻结 → 本记录登记预检/保护基线 → 新测试 cpp 实现 → 静态核对并冻结 cpp → 本记录补实际证据 → 两 hash 交回并停写。Q 阶段交回时状态（历史）：五个自动化叶源码已实现并静态冻结，本记录证据已封存；两文件停止写入，未编译/未运行。

只读依赖：`AbilitySystem/Tests/GGYGOMontageTaskTestTypes.h` 的具体 Guard 派生类、真实 Started 一次性观察器及 ASC 类型；其现有实现 cpp；A1 Scope/Result 和 A4/A5 公开 const 查询。旧匿名命名空间夹具不能跨 TU 使用，新夹具只用公开 API 建立真实 World/Character/Mesh/Skeleton/Montage/ASC，不移动或改写旧测试。统筹已核对本机 UE 5.8 `AnimInstance.cpp:2757`，`GetPlayLength()>0` 是原生入口前置；零长度有效 Montage 可真实进入 Super 返回 0，没有 Started。

非目标：不改旧 P1/StartedPositive/RateLease/types、生产/API、A5-I 或原04B4记录、11记录、Obsidian/Canvas、资产、Build.cs；不写 ASC/Task/GA 播放状态，不调用 ASC 的受控播放再人为套第二 Scope，不测试 ASC Super 写回或资源归属。禁止 UE/构建/Git/代理；统一构建由统筹收齐冻结确认后执行。

## 验收断言、清理与停止点

- 单次真实 Scope：构造 NotEntered/false → 真实 Started Executing/false → 原生返回、Complete 前 Returned/false → Complete 后 Returned/true → 析构后 false 且输出 Reset。
- 同 coordinator A→B：A 的真实 Started 内构造并播放 B；B 返回/Complete 时最内查询显示 B 的 Returned，而 A 仍 Executing；B 析构后恢复 A Executing。成功 B 通过实际 Complete 发布接管，失败 B 不发布。
- 不同 coordinator 最内 B：真实注册但依契约拒绝原生准入的 B 不允许 A 查询越过；B 自身仍能观察 NotEntered/封存位；析构后恢复 A。绝不要求不同 coordinator 的拒绝 B 产生 Started。
- 失败 B：非空真实 Montage、相同有效 Skeleton/slot/group，显式长度 0；CanExecute 必须 true，实际 Montage_Play 返回 0，stage 必须 Returned，Started 次数 0，Complete Failed，父 SupersedingCallId 0 且父真实实例仍存活/活动；不能用 Complete(0) 伪造原生失败。
- 不可用查询使用预置 Returned/true，覆盖无 Scope、null、错 coordinator、失效生命周期；输出必须 NotEntered/false。
- 每次查询前后有效性谓词调用计数不变、公开 Scope Result 不变；不调用外部谓词，不刷新生命周期，不以成功查询推导 Accepted/ASC/GA/Task 权限。
- 原生返回后通过公开动画生命周期入口反初始化/初始化；旧 Scope 不可复活，Complete 为 LifecycleInvalid；退出旧 Scope 后新真实 Scope 可播放，发行身份来自生产注册，不能手写代次/CallId。
- 观察器解绑、Scope 按词法析构；回调捕获/对象活到 Scope 退出；不在 Started 内销毁或重初始化实例；WorldContext 保留到 World 销毁后移除。夹具独占世界，清理只通过公开 Montage/lifecycle 接口。

停止点：实际 Skeleton/slot/group/Guard/ActorInfo/Started/原生失败前置不成立即明确失败并保留证据；不 ExpectedError、不 Skip 成功、不改阶段/封存位/身份、不替换失败场景。需要第三文件或改变生产契约时停止交回。源码冻结后本记录仅补证据，交回即全部停写。

## 保护基线（SHA256，Q 开始时历史快照）

| 冻结文件 | 开始 SHA256 |
| --- | --- |
| Animation/Runtime/GGYGOMontagePlayGuard.h | `ACAEA0FD27ED2F474C8BC107886860BD7DADE72F452902A748B7F8AFE4E3855A` |
| Animation/Runtime/GGYGOMontageGuardAnimInstance.h | `1682C43887168825FFB977915FDF7C2C1B28A5FB3F9B5629420B8C5155D068F9` |
| Animation/Runtime/GGYGOMontageGuardAnimInstance.cpp | `4A67D9DDB893E66054E9F95F32D6DEE787719BC9660CB889B6C056135C3AE950` |
| AbilitySystem/Tests/GGYGOMontageTaskTestTypes.h | `BEC4C9B7F4C50BD4448011EAFAB79EB5E5335E57246064583E12E7216D2847A4` |
| AbilitySystem/Tests/GGYGOMontageTaskLifecycleTest.cpp | `39E71D2DEFF7B98197B88B30C36652A108976E31CCB0EAACC41B1502B5681567` |
| AbilitySystem/GGYGOAbilitySystemComponent.h | `E9AEB8AE04165D05DA8C6C18EB07B18F5C7DCB6D8A4AE0702B1D117845BC95E5` |
| AbilitySystem/GGYGOAbilitySystemComponent.cpp | `4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF` |
| AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.h | `6C75E4233254776D98BE6371F57EDF60724E453E8275B5BF7691749AB59185B3` |
| AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.cpp | `506AAFB79129EED88485BF8185284CA13781CCE21F6796F907C334F1E1B1D02D` |
| AAADocs/Modules/Animation/Module_Repair_04B4_A5_Stage_Query.md | `0F0C4FD50BFFF25071D3D167E34474A742BAC932DE59202FA40646C12CEA19B7` |
| AAADocs/Modules/Animation/Module_Repair_04B4_Animation_Steps.md | `F8A4C6AC4CFDA29B12E7A28F2DE8BC143E525DAD4FC56832BD005ACCAA1B309B` |
| AAADocs/Modules/Animation/Module_Repair_04B4_Animation_Validation.md | `0C021A5EB0408BCEE83DBA96F8158AF302549E569C781F575E087D3122C1426E` |

源码路径均相对 `Source/GGYGO/`；AAADocs 路径相对项目根。11 两记录/图文属其它租约，本步不写或声称其 hash 恒定。

## 已实现的五个叶与精确前置

公共路径前缀为 `GGYGO.Animation.MontageGuard.StageQuery.`，使用 `EditorContext | EngineFilter`：

| 叶 | 实际源码断言与前置 |
| --- | --- |
| SingleCall | 注册真 Scope；CanExecute true；一次真实原生正返回/Started，Started 必须看到活动且播放中的原生实例。依次查询 NotEntered/false、Executing/false、Returned/false、Returned/true、析构后 false/Reset；同时检查 null/错 coordinator、重复查询及外部谓词暂为 false 时查询仍只观察动画 Scope。Complete 前恢复正常测试谓词，最终 Accepted/实际发行 instance ID 与 Started ID 相同、精确实例仍播放。 |
| AcceptedNested | A 真实 Started 且存在活动实例后进入同 coordinator/同有效 group 的不同资产 B。B CanExecute true/真实正返回/Started 一次；B 构造 NotEntered、返回 Returned、封存 Returned/true，而 A 的公开 NativeStage 仍 Executing。B Complete Accepted 后 A 的 SupersedingCallId 等于 B 实际发行 CallId；B 析构恢复查询 A Executing，A 最终 Superseded/返回0，全部 Scope 析构后 Reset。 |
| FailedNested | 同一真实 A 前置；B 使用非空、同 skeleton/slot/group 且显式 GetPlayLength=0 的真实 Montage。B CanExecute true 后实际 Montage_Play；必须返回0、Started0、Returned/false，Complete Failed/Returned/true、CreatedInstanceId=INDEX_NONE。A 不发布接管、原实例仍活动播放，B 析构恢复 A Executing；A 最终 Accepted/正返回、SupersedingCallId0。不能用原生前准入拒绝充当此测试的成功。 |
| DifferentCoordinator | A 真实 Started/活动实例后注册不同实际 ASC coordinator 的 B；CallId 由生产登记且不同于 A。B CanExecute 必须 false，Outcome Unsupported，未执行原生；查询 A 在 B 未封存与封存期间都不可用/Reset，B 自身可观察 NotEntered/false 和 NotEntered/true。无实例创建或接管，A 实例不受影响，B 析构恢复 A Executing，A 最终 Accepted。 |
| Lifecycle | 真实旧 Scope CanExecute/正返回/Started一次及 Returned 后，先让观察器 RAII 解绑，再调用完整公开 UninitializeAnimation/InitializeAnimation。旧 Scope 在反初始化、重新初始化及 Complete 后都不可用/Reset，结果 LifecycleInvalid。旧 Scope 析构后新 Scope 重走 SingleCall 的严格真实播放链，实际发行代次不同、CallId 更大且不复用。没有手写身份或在 Started 内破坏原生栈。 |

新夹具使用 `/Engine/EngineMeshes/SkeletalCube.SkeletalCube` 的真实渲染数据/骨骼，要求 CompatibleMesh、注册 Mesh、生产 Guard 具体类/原 owner、两个真实已 Register/InitActorInfo 的 ASC、有效正长度 segment/default slot/同 group、明确 1 秒正常 Montage 与 0 秒失败 Montage。所有前置均用失败断言并返回 false；没有资产或成功替代路径，也没有跳过叶。Test 不给予 ASC 的 Local/Rep/GA 状态写入权限；实际播放只经 Scope.CanExecute → Guard 公共 Montage_Play → Complete，未调用 ASC PlayMontageWithGuard 后再套一个外层 Scope。

统一 CheckStage 每次先设 `(Returned,true)` 哨兵；查询后逐项检查 Available、Stage、Completed、外部谓词调用计数、Scope 公开完整 Result 的逐字段不变。副作用计数仅为夹具诊断；查询不会执行该计数谓词。Result/Identity 只读取或完整复制公开结果；没有写 NativeStage/bSealed/代次/CallId/CreatedInstanceId、内部链或原生 MontageInstances。原生实例指针只在两个只读 helper 内立即解引用并返回 ID/bool，不跨外调保存。

清理顺序：Started 公共观察器本身在运行 action 前解绑，外层 FStartedObservation 再按词法 RAII 解绑；失败无 Started 时也在 Complete/Scope 退出前解绑。测试场景 Scope 全部退出后夹具先解绑两个观察器，再对独占且 owner/mesh 仍匹配的实例使用公共 Montage_Stop/UninitializeAnimation；StrongObjectPtr 持有 Guard/coordinator/观察器/Montage。夹具先于 World 销毁，World 先 DestroyWorld 再 DestroyWorldContext，没有 Tick/Timer 或测试第二执行器。

## 静态验证与冻结证据（Q 阶段历史）

完整源码人工复核及 PowerShell 静态15项均 true：五个独立叶、准确冻结 types include、无 Scope 私有/身份字段写、无 ExpectedError/Skip/Task hook/ASC 受控播放、仅五处公开原生播放调用点、输出双哨兵、每次查询检查谓词与 Result、真实零长度失败分支、最内 B/不同 coordinator 禁止祖先回查断言、子退出恢复真实 Executing A、完整公开生命周期/旧不可复活、观察器 RAII、WorldContext 删除顺序、12 项保护 hash 保持、去注释/字符串后的括号栈平衡。

源码静态冻结 SHA256：`6847EC3F96137EE0AD50E69DD5B39BB164476D6B63BF4ECE5E3213117589B3FB`。

本记录基线表 12 项均再次实算吻合，包括原 A5-I 三文件、A1、旧 types/P1/StartedPositive/RateLease 所在测试 cpp、生产 ASC/Task 及原04B4两记录；没有扩大文件租约。静态文本/括号核对不能证明 C++ 编译或动态断言通过。本步没有 UE/UHT/UBT/构建、自动化实跑、Git、资产保存或代理操作；五个叶的动态结果及 Engine 生命周期/Started/零长度严格前置仍待统筹统一门禁。前置若失败，保留真实失败交回，不降低断言或替换场景。

架构核对：仅新增测试，不改 Animation/GAS 权威状态与依赖方向，不新增生产执行链、调度器或内部可写接口；清理归夹具独占 World 与公开引擎生命周期。已只读核对 Obsidian 计划蓝图的 Animation 路由和结构入口；图文在本租约冻结，A5 API 与本五叶“源码已实现/尚未验证”的状态待统筹独立文档窗口同步，不提前标成消费者/动态验收完成。

Q 阶段原始交回声明（历史）：最终两文件已冻结并停止写入；任何后续源码修正须新租约，编译/动态结果及证据记录须统筹门禁。A5-Stage-I 三文件继续保持原冻结。

## A5-V1：第36次实际五叶证据与局限

本节追加统筹2026-10-01第36次门禁；原Q当轮“未编译/未运行”是保留的历史静态交回。当前五叶已编译并真实运行成功。V1只有两记录写入，没有重新运行UE/构建、修改夹具或降低断言。

- 完整 `GGYGOEditor Win64 Development` Succeeded，7 actions/94.44秒/UBA80.76秒；UHT7.822312秒、0 generated files written；本次只重链接运行时 `UnrealEditor-GGYGO.dll`。只读构建日志：`Saved/Logs/ModuleRepairBuildGate_20261001_36.log`。
- 正常报告：`Saved/AutomationReports/ModuleRepairGate_20261001_36/index.json`，生成时间2026-10-01 12:23:19 UTC＝北京时间20:23:19，70 Success，其它状态计数0，总耗时 `0.8348187208175659` 秒。
- 实算报告SHA256：`9C28CF4DB61E8909EF2908CD24479810738FC29E845921B4E249DCE3A3508E46`。与第35次集合比较：原65完整路径删除0且全部仍Success，唯一新增为下表五叶。

以下完整路径均带 `GGYGO.Animation.MontageGuard.StageQuery.` 前缀，每叶entries=[]/errors=0/warnings=0：

| 叶 | 实际状态 | 实际耗时（秒） |
| --- | --- | --- |
| AcceptedNested | Success | 0.009342800825834274 |
| DifferentCoordinator | Success | 0.00940990075469017 |
| FailedNested | Success | 0.010901901870965958 |
| Lifecycle | Success | 0.008245401084423065 |
| SingleCall | Success | 0.008881699293851852 |

五叶严格断言保持原源码与前置：单次注册/真实Started/Returned/Complete/析构；B成功最内观察和实际接管；零长度B准入成功、实际原生0/Started0/Returned/Failed、不接管且A实例存活；异coordinator最内拒绝Scope阻止A回查；原生返回后完整公开生命周期失效、新Scope使用实际新发行身份。每次查询的外部谓词计数与公开Result不变，输出失败Reset，没有ExpectedError/Skip或手改Stage。

原日志 `Saved/Logs/GGYGO_ModuleRepairGate_20261001_36.log` 实算49 Error＝启动Smoke的LogAutomationTest13＋Damage严格拒绝LogGGYGOAbilitySystem34＋Bake既有预期LogAnimation2；2 Warning＝DDC1＋Python枚举重名1。不能把正常70或五叶0 Error/Warning写成全日志无诊断；旧P1严格失败及其它独立诊断历史保留，不由正常报告覆盖。

统筹确认36运行窗口248源/14保护保持、无资产保存、两UE均退出，此处仅记录已关闭窗口历史。V1期间K4-I1 ASC与P1-T1测试另有授权，不声明全局当前source或旧ASC快照不变。V1自身10项保护和完整hash见同目录I记录的“V1 自身保护与历史保持”表，包含A1/Guard两文件/Base两文件/Qcpp/types/旧专项cpp/原04B4两记录，开始及交回重新实算保持。两份V1授权记录不列为不变文件；原Q保护基线表完整保留，尤其旧I记录hash仍是历史快照。

原Q完整文本仅增加当前/预检与本证据段，并对原标题/状态/交回声明加历史标记；逆向去除新增段并恢复有限标签须逐字恢复开始文本与 `48F999AA…`。旧夹具/断言/静态证据/原12项历史基线不变；当前已编译/五叶实际结果与旧历史明确分开，最终新hash单独交回。

有限边界保持：本报告证明专用真实夹具的阶段/封存/最内查询/失败传播与生命周期观察，不证明ASC Super写回完成、来源已发布或Task/GA有清理权限。生产AnimClass/资产未迁移、消费者未接入；原P1全部写回风险、绑定/GA结束、网络预测/proxy、fractional/simulated、代次耗尽/无owner专门验证、Started内销毁/换owner的原生安全不因此完成。自身冻结文件保持，本租约未开放source/test、旧04记录、Obsidian/Canvas；A5图文另由统筹授权。

V1 实际历史核对：逆向去除新增两段并恢复有限历史标签后，Q原7441字符及I原5189字符与开始完整内存快照逐字一致；自身10项保护实算全部吻合，旧基线表/静态前置/断言/失败边界保留。

V1两记录已完成历史保持/自身保护/报告事实核对，冻结并全部停止写入；最终全文/hash交回统筹。无第三文件、source/test、UE/构建/Git/代理或自动后续权限。
