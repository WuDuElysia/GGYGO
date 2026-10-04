# 04B4 A5：作用域只读阶段查询

日期：2026-10-01（Asia/Shanghai）。Animation 运行时组长直接执行，`gpt-6.1-sol / xhigh`，不开代理。

## 当前状态与 A5-V1 两记录预检

当前：第36次完整 `GGYGOEditor Win64 Development` 构建已 Succeeded，A5 查询及新五个 StageQuery 叶在新运行时 DLL 上实际全部 Success、每叶 0 Error/Warning。原65路径保留并继续 Success，正常报告共70 Success。V1 两记录已完成证据同步并冻结停写，Guard h/cpp、专项 cpp、types/Base 等自身源码继续冻结；不授 ASC/Task 权限，不表示生产 AnimClass 已迁移。

排程 J4/A5-V1 已获统筹授权，唯一结果为当前编译/动态证据同步。精确可写范围仅本文件与 `AAADocs/Modules/Animation/Module_Repair_04B4_A5_Stage_Query_Test.md` 两份既有记录。顺序：核对两记录/自身保护基线 → 登记本预检 → 标记原 I/Q 未编译声明为所属历史阶段并保留正文 → 追加36实际证据及局限 → 历史逆向核对/保护实算 → 两记录 hash 交回并停写。

| V1 开始记录 | 开始 SHA256（历史基线，不是更新后的 hash） |
| --- | --- |
| Module_Repair_04B4_A5_Stage_Query.md | `0F0C4FD50BFFF25071D3D167E34474A742BAC932DE59202FA40646C12CEA19B7` |
| Module_Repair_04B4_A5_Stage_Query_Test.md | `48F999AA9CB51A2083190D4BD854A84684CFF6EFC20A888A300579EF2EB38350` |

非目标：不写 source/test、types/Base、旧04B4两记录、11记录、Obsidian/Canvas、资产、第三文件；不运行 UE/构建/Git，不建代理。只读依赖为36报告/构建及原日志、35旧路径集合、原 I/Q 全文与冻结自身文件。K4-I1 ASC、P1-T1 新测试属于其它当前租约，不能声称所有 source 或旧 ASC 快照当前不变。248源/14保护只作为统筹36运行窗口的历史证据。

验收：当前/历史明确；原静态与基线内容可逆恢复；报告/hash/70与原65集合/五叶结果及耗时/49Error与2Warning分列准确；阶段查询不扩权，旧 P1 失败不被新五叶覆盖。需要第三文件、修改源码或证据不符时停止交回。冻结交回后两记录无续写权。

以下原 I 阶段授权、静态结果和交回边界属于历史；36及V1实际状态见本节与末尾追加段。

## 原 I 阶段授权、目标与先后顺序（历史）

统筹已接受 A5-Stage-Readonly 协议核对，只开放 **A5-Stage-I** 三文件独占租约。单一目标：从现有最内 caller scope 提供即时原生阶段及 Complete 封存状态观察，供后续 ASC 契约消费；不实现 ASC 归属裁决或 Task 播放状态。

精确可写文件：

1. `Source/GGYGO/Animation/Runtime/GGYGOMontageGuardAnimInstance.h`
2. `Source/GGYGO/Animation/Runtime/GGYGOMontageGuardAnimInstance.cpp`
3. 新 `AAADocs/Modules/Animation/Module_Repair_04B4_A5_Stage_Query.md`（写入前确认不存在）

顺序：登记本预检/基线 → 仅追加公开声明/对应定义 → API/差异/副作用静态审查 → 冻结源码 → 仅补本记录证据 → 三文件 hash 交回并停止。I 阶段交回时状态（历史）：源码/API 静态冻结完成，本记录证据已封存；三文件停止写入，未编译/未动态验证。

## 责任、共享契约与只读依赖

- Animation 唯一持有原 AnimInstance 的 `ScopeChain` 及 scope 私有 `Result.NativeStage`/`bSealed`；查询不改变它们。
- ASC 保留唯一原生 Montage 记录来源契约及真实受控 Super/来源发布窗口。新查询不能证明哪条 Local/Rep/GA 写回完成。
- Task 只持自身资源来源；环境 scope 的 CallId/CreatedInstanceId 不能充当 Task 来源。A5 不输出这些字段。
- 只读依赖：冻结 A1 的 `EGGYGOMontagePlayGuardNativeStage` 与 Identity；A4 `IsMontagePlayGuardIdentityCurrent`；现有 scope 登记/析构/Complete 及原生返回屏障。
- 依赖门禁：A1/A4/现有链契约冻结 → A5 查询冻结 → 消费者/专项另行授权；所有可能参与构建的源码作者均明确冻结后由统筹编译。

## 精确基线与保护范围

| 文件 | A5 前 SHA256 |
| --- | --- |
| Guard h | `6BD6A6DC686074608213F5DF567957D1F10A2D5DBB537BD8C70E0687BA910766` |
| Guard cpp | `2357E96AF6F312FE2C691A09C79988DC10A6FC578B48AF96604CE1D5D9621995` |
| A1 `GGYGOMontagePlayGuard.h` | `ACAEA0FD27ED2F474C8BC107886860BD7DADE72F452902A748B7F8AFE4E3855A` |
| Base h | `010DDC81E74AA20BCFC0741F85D77E1BD4554A4728252195A20116D59625E614` |
| Base cpp | `5923F245885CA98B4E19F260BA2DC079BF965FC259A78F7BE41BE9885A94BF6B` |
| `Module_Repair_04B4_Animation_Steps.md` | `F8A4C6AC4CFDA29B12E7A28F2DE8BC143E525DAD4FC56832BD005ACCAA1B309B` |
| `Module_Repair_04B4_Animation_Validation.md` | `0C021A5EB0408BCEE83DBA96F8158AF302549E569C781F575E087D3122C1426E` |

11 两记录当前归资产组长 C28-C，04B4 原两记录亦冻结，本步均不写入。禁止测试/消费者/图文/资产/UE/构建/Git/代理；不改 A1/A4/native 屏障、结果优先级、Scope 生命周期或无 Guard 兼容路径；不增加字段/map/counter/代际/定时器或 ASC/GA 依赖。不因本接口扩大 K3/A17/GA 终止/B0 边界。

## 已追加接口与判定

```cpp
bool TryGetCurrentMontagePlayGuardStage(
    const UObject* CallerIdentity,
    EGGYGOMontagePlayGuardNativeStage& OutNativeStage,
    bool& bOutCompleted) const;
```

普通 C++ 公共 const 方法，仅 game thread，不新增 UFUNCTION/属性。入口先把输出设为 `(NotEntered, false)`。null coordinator、空链、无有效最内注册 scope、原 coordinator 弱身份不匹配或原生命周期不匹配时明确返回 false；不回查更外层祖先。可复用 A4 只读身份查询，不调用 `IsCallerContextCurrent` 或其它外部谓词，不 Refresh/推进代次，不日志。

成功时只复制当前最内 scope 的 `Result.NativeStage` 与 `bSealed`，返回 true。唯一阶段来源是现有 scope，不新增存储或阶段裁决。A4 只检查原实例/生命周期/owner/已发行 CallId 范围，不证明 Accepted、当前实例存活、ASC/GA 权限。

## 验收断言与停止点

以下为静态/后续专项应覆盖的契约；本步不运行测试：

- 任意失败路径均保留入口重置输出；成功前不能输出旧/父 scope 的阶段。
- A→B 嵌套时只观察 B；B 正常或失败退出后现有析构恢复 A。coordinator 不匹配即不可用，不回查 A。
- 未执行/原生 Executing/原生 Returned 的三阶段照实读取；Complete 前后 bOutCompleted 来自已有封存位，不由 Outcome/返回值猜测。
- 已初始化但合法无 owner 的 A4 语义保持；失效 lifecycle/owner/原实例/发行范围返回不可用，不推进代次。
- 不访问 CreatedInstanceId、Montage 活动性、Local/Rep/GA 或 Task 缓存；不更改原播放次数、成功传播、清理时序或任何字段。
- 从修改后文件移除新增声明注释块/定义块，必须恢复原 Guard 两文件的逐字文本/hash；A1/Base/原04B4两记录保护 hash 保持。

如需第四文件、改变已有接口/权限/结果裁决或扩大状态归属，立即停止交回。静态冻结与记录收尾后停写，专项、编译和消费者另授租约。

## 借用与权限边界

输出是当前 game-thread 读取点的副本；跨外调后必须重新查询，不能把旧副本当当前窗口。`Returned` 不表示 ASC Super 已完成；`Completed` 不表示 ASC 已发布来源。ASC 的真实受控调用/来源发布窗口仍由 ASC 契约表达，查询不建立第二权威状态。

false 是“查询不可用”，输出重置也不是“播放空闲”或旧 Task 有权清理。环境 scope 身份不可成为 Task 来源；本 API 不输出 Identity。自然混出来源清空及精确资源/GA 权限由各自已确认契约处理，不用一次请求进入或一次阶段查询代替归属判定。

## 实施与验证结果（I 阶段历史静态证据）

唯一源码变化为公共 const 查询的声明/注释与对应定义。先 Reset 输出，再断言 game thread；null coordinator/空链、无 scope/私有状态、未注册/原 guard 不符、原 coordinator 弱引用不符、A4 原生命周期查询失败均直接 false。成功只复制现有最内 `Result.NativeStage` 与 `bSealed`。无祖先回查、外部有效性谓词、刷新/写入、日志或新增字段。A4 函数体及其合法无 owner/停止实例语义完全保持。

静态15项均 true：唯一声明/定义块、移除新增块后原 h/cpp 整文 hash 相同、输出入口 Reset、game-thread 契约、null/空链拒绝、live scope/注册/guard 检查、只取一次 Last 且无循环/索引回查、弱 coordinator 比较、A4 只读复用、原阶段与封存位复制、无外部回调/Refresh/日志/Super、无 CallId/CreatedInstanceId 输出或实例事实、无状态写入/链增删/计数递增。这里只验证源码路径与接口，未运行边界测试。

| 源码静态路径 | 结论 |
| --- | --- |
| 不可用（所有失败分支） | OutNativeStage=NotEntered、bOutCompleted=false；返回 false，不能以重置值当成功阶段 |
| 当前最内 scope 存在但 coordinator 不符 | false，绝不回查具有匹配 coordinator 的祖先 |
| 当前最内 scope 原实例/代次/owner/发行范围失效 | A4 纯查询 false，输出保持 Reset；没有推进代次 |
| Scope 当前阶段为 Executing/Returned 等 | 直接复制已有阶段，没有从 Outcome 或返回值推算 |
| Complete 前 / 后，仍注册且生命周期当前 | 直接复制 false / true 的已有 bSealed；不是 ASC Super/来源发布状态 |
| 正常或失败 B 析构退出 | 恢复 A 由原 UnregisterScope/ScopeChain 机制负责，A5 没有增加恢复或裁决路径 |

冻结源码 SHA256：

- Guard h：`1682C43887168825FFB977915FDF7C2C1B28A5FB3F9B5629420B8C5155D068F9`
- Guard cpp：`4A67D9DDB893E66054E9F95F32D6DEE787719BC9660CB889B6C056135C3AE950`
- 移除新增声明块后 h：`6BD6A6DC686074608213F5DF567957D1F10A2D5DBB537BD8C70E0687BA910766`，等于基线
- 移除新增定义块后 cpp：`2357E96AF6F312FE2C691A09C79988DC10A6FC578B48AF96604CE1D5D9621995`，等于基线

A1、Base h/cpp、原04B4两记录已重新核对，均保持本记录基线表 SHA256。11 两记录没有写入，归 C28-C 独占。本步骤未运行测试、UE/UHT/UBT/编译、资产或 Git，没有接入消费者；旧严格 P1/Guarded Started/RateLease 未修改，不能由静态检查推导新接口已运行或 B4/K3/A17 已关闭。

项目架构核对：复用现有唯一 scope 链/A4 生命周期观察，不新增权威状态、执行链、循环依赖、内部可写访问或清理责任。已只读定位 Obsidian `计划蓝图.md` 的 Animation 入口并核对 `Animation/结构.md`；该模块笔记窗口由现有资产组长持有，本步图文冻结。待统筹独立文档窗口补充本接口的即时副本/生命周期拒绝及权限边界，不提前画成 ASC 来源消费者已完成。本新记录保留本步实际状态与待同步项。

I 阶段原始交回声明（历史）：最终 A5-Stage-I 三文件均静态冻结并停写。统筹后续只读 Stage-Q 预检单独交回，不在本记录或源码追加测试工作；Stage-Q 未授权写入。任何后续构建须统筹先收齐所有源码作者冻结确认。

## A5-V1：第36次实际编译与五叶结果

本节为2026-10-01统筹36门禁之后的证据追加。I/Q 当轮静态交回中的“未编译/未运行”保持历史事实；当前 A5 查询及 Q 专项已编译并有以下有限真实结果。V1 仅写两记录，没有再运行 UE/构建或改源码。

### 构建与正常报告

- 统筹独占完整 `GGYGOEditor Win64 Development` 构建 Succeeded，7 actions，94.44秒；UBA80.76秒。UHT7.822312秒、0 generated files written；实际链接 `UnrealEditor-GGYGO.dll`，不声称本次重链接 GGYGOEditor DLL。只读核对 `Saved/Logs/ModuleRepairBuildGate_20261001_36.log`。
- 新DLL正常报告 `Saved/AutomationReports/ModuleRepairGate_20261001_36/index.json`：时间 `2026.10.01-12.23.19` UTC＝北京时间2026-10-01 20:23:19；70 Success，succeededWithWarnings/failed/notRun/inProcess均0，总耗时 `0.8348187208175659` 秒。
- 报告实算 SHA256：`9C28CF4DB61E8909EF2908CD24479810738FC29E845921B4E249DCE3A3508E46`。只读比较第35次65个完整路径与36次70个路径：旧路径删除0、旧65全部仍Success，新增集合精确为下列五叶。

路径前缀 `GGYGO.Animation.MontageGuard.StageQuery.`；每叶实际 entries=[]、errors=0、warnings=0：

| 叶 | 实际状态 | 实际耗时（秒） |
| --- | --- | --- |
| AcceptedNested | Success | 0.009342800825834274 |
| DifferentCoordinator | Success | 0.00940990075469017 |
| FailedNested | Success | 0.010901901870965958 |
| Lifecycle | Success | 0.008245401084423065 |
| SingleCall | Success | 0.008881699293851852 |

正常70报告与原日志不能混为“全日志零诊断”。只读实算 `Saved/Logs/GGYGO_ModuleRepairGate_20261001_36.log`：49 Error＝启动Smoke的LogAutomationTest13＋Damage严格拒绝的LogGGYGOAbilitySystem34＋RootMotionBake既有预期LogAnimation2；2 Warning＝LogDerivedDataCache1＋Python枚举重名1。上述Error/Warning不是新五叶的entries，五叶各自0 Error/Warning。旧严格P1失败与独立诊断历史保留，新正常70不取代它们。

统筹36运行窗口已确认248源/14保护保持、未保存资产、两次UE进程均退出；这是该已关闭窗口的历史证据。本次V1期间K4-I1 ASC和P1-T1测试另有租约，不把旧ASC快照或全248源码冒称当前不变；V1只对以下自身冻结文件重新实算。

### V1 自身保护与历史保持

以下10项在V1开始和交回时实算保持；没有写入它们：

| 自身保护文件（源码相对Source/GGYGO） | SHA256 |
| --- | --- |
| Animation/Runtime/GGYGOMontagePlayGuard.h | `ACAEA0FD27ED2F474C8BC107886860BD7DADE72F452902A748B7F8AFE4E3855A` |
| Animation/Runtime/GGYGOMontageGuardAnimInstance.h | `1682C43887168825FFB977915FDF7C2C1B28A5FB3F9B5629420B8C5155D068F9` |
| Animation/Runtime/GGYGOMontageGuardAnimInstance.cpp | `4A67D9DDB893E66054E9F95F32D6DEE787719BC9660CB889B6C056135C3AE950` |
| Animation/Runtime/GGYGOAnimInstanceBase.h | `010DDC81E74AA20BCFC0741F85D77E1BD4554A4728252195A20116D59625E614` |
| Animation/Runtime/GGYGOAnimInstanceBase.cpp | `5923F245885CA98B4E19F260BA2DC079BF965FC259A78F7BE41BE9885A94BF6B` |
| Animation/Tests/GGYGOMontagePlayGuardStageTest.cpp | `6847EC3F96137EE0AD50E69DD5B39BB164476D6B63BF4ECE5E3213117589B3FB` |
| AbilitySystem/Tests/GGYGOMontageTaskTestTypes.h | `BEC4C9B7F4C50BD4448011EAFAB79EB5E5335E57246064583E12E7216D2847A4` |
| AbilitySystem/Tests/GGYGOMontageTaskLifecycleTest.cpp | `39E71D2DEFF7B98197B88B30C36652A108976E31CCB0EAACC41B1502B5681567` |
| AAADocs/Modules/Animation/Module_Repair_04B4_Animation_Steps.md（项目根） | `F8A4C6AC4CFDA29B12E7A28F2DE8BC143E525DAD4FC56832BD005ACCAA1B309B` |
| AAADocs/Modules/Animation/Module_Repair_04B4_Animation_Validation.md（项目根） | `0C021A5EB0408BCEE83DBA96F8158AF302549E569C781F575E087D3122C1426E` |

V1只插入当前/预检和追加本节，对原阶段标题、状态标签与交回声明加历史标记；逆向移除这两新增段并恢复有限标签后，应完整逐字恢复本记录开始文本及 `0F0C4FD5…`。Q记录同样核对，不删除或改写原静态证据、旧基线表与失败边界。两更新记录最终hash另交；Q历史表中的旧I hash是Q开始快照，不是V1更新后的当前保护结果。

### 有限证明与权限局限

五叶实际证明真Scope/Started/返回/Complete/析构、同coordinator最内成功与零长度原生失败、不同coordinator不能越过最内拒绝Scope、公开生命周期旧Scope不可复活及查询谓词/公开Result不变。查询仍只读取即时最内阶段/封存；Returned不证明ASC Super完成，Completed不证明来源发布，查询成功或Reset都不授Task/GA资源清理权。

没有接入新的ASC/Task来源消费者，也没有完成生产AnimClass/蓝图资产迁移。此专项不覆盖原始P1全部写回风险、绑定事务/GA取消结束、联机/预测/proxy、fractional/simulated播放、代次耗尽、无owner专门场景或Started内销毁/换owner的原生安全；这些不因五叶Success而关闭。自身保护源码/旧04记录保持，本租约没有Obsidian/Canvas写权；A5架构图文由统筹另授权同步。

V1 实际历史核对：逆向移除两个新增段并恢复有限历史标签后，I原完整5189字符、Q原完整7441字符分别与开始内存快照逐字一致；自身10项保护实算全部吻合。未改原静态断言、基线表或原失败边界。

V1两记录已完成当前事实、历史可逆保持与自身保护核对，冻结并停止写入；最终全文/hash交回统筹。无source/test/第三文件/UE/构建/Git/代理或自动后续授权。
