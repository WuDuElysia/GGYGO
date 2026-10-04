# 04B4 Animation 验证与冻结

日期：2026-09-30。执行者：Animation 长期组长。A1/A2 原机制第15次完整构建含 UHT 通过；A3 单头继承及 A4 只读查询已静态冻结、未编译/未动态验证。ASC/Task 未接入 Scope/身份查询；**B4 未修复**。

## 当前产物与授权

当前 A4 唯一四文件范围：

- 修改 `Source/GGYGO/Animation/Runtime/GGYGOMontageGuardAnimInstance.h`，仅新增公共 const 查询声明与注释
- 修改 `Source/GGYGO/Animation/Runtime/GGYGOMontageGuardAnimInstance.cpp`，仅新增对应定义
- 更新 `AAADocs/Modules/Animation/Module_Repair_04B4_Animation_Steps.md`
- 更新 `AAADocs/Modules/Animation/Module_Repair_04B4_Animation_Validation.md`

授权来自有效 `Module_Repair_Parallel_Schedule.md` 工作线 J / 04B4-A4 与统筹明确派发。A1/Base/旧 A2 机制保持冻结；ZZZ、ASC、Task、专项、资产、Obsidian 未授权。先登记 A4 预检，再新增声明/定义及静态审查，最后封存两记录。原源码文本只保留在会话内存；未创建/唤醒代理或额外文件。

## 已存在的真实运行证据

第14次统筹门禁：`Saved/Logs/ModuleRepairBuildGate_20260930_14.log` 完整构建 Succeeded，6 actions / 14.31 秒；常规 `Saved/AutomationReports/ModuleRepairGate_20260930_14/index.json` 为 47 succeeded，0 warnings/errors，0.421443 秒，02:54:52 UTC。此门禁先于 A1，不验证新声明的编译/链接。

独立显式诊断 `Saved/AutomationReports/ModuleRepairB4Diagnostic_20260930_14/index.json`：`ProjectDiagnostics.B4.MontageStartedReentry.LocalRepGaSectionInstance` 为 **1 Fail / 16 errors / 0 warnings**，0.120586 秒，02:56:03 UTC。报告已只读回查；进程 exit 0 不能替代报告 Fail。

- DifferentAssets：真实 Started 1次；A/B 精确实例 ID 为 0/1。B 返回后 Local/Rep/owner 为 B，A 外栈返回后回到 A，Local/Rep 计数 1→2；7 个后继保持断言失败。B 的位置/Section 没有回退。
- SameAssetDifferentSection：真实 Started 1次；A/B 精确实例 ID 为 2/3。owner B→A、Local/Rep 计数 1→2、RepSection 3→2；B 精确实例位置 0.65→0.20、Section SuccessorStart→OuterStart；9 个后继保持断言失败。
- 两场景播放时长及重入前置均有效，全部16错误为严格保持比较；不能减弱测试或写成成功。P1 源码保持冻结。

第15次统筹门禁（A3 修改之前）：`Saved/Logs/ModuleRepairBuildGate_20260930_15.log` 完整构建 **Succeeded，6 actions / 22.10 秒，含 A1/A2/UHT**。常规报告 `Saved/AutomationReports/ModuleRepairGate_20260930_15/index.json` 已只读回查：47 succeeded、1 failed、0 succeededWithWarnings/notRun/inProcess，0.511767 秒，报告 03:50:28 UTC（北京时间11:50:28），UE exit0。唯一 Fail 为新增 `GGYGO.Input.Fixture.LocalSessionReady`；原47项全部 Success。该夹具失败由统筹归入独立 Input 来源短修，不能把整轮48项写为通过，也不能因此声称 A2 已接入或 B4 已修复。第15次构建不验证后续 A3 头文件修改。

## A1 历史静态复核（A1 完成时）

| 检查 | 结论 |
| --- | --- |
| 源码产物边界 | 仅新头；没有包含者、定义、执行接线、继承或 Engine 修改 |
| 依赖 | 只 Core/模板/弱引用与动画类型前置声明；无 ASC/GA/GAS 头，无具体角色类型 |
| 唯一状态归属 | 私有 scope 实现状态延期 A2；结果仅证据，无 Local/Rep/GA 状态副本，无 public 写入方法 |
| 身份 | 原 AnimInstance + lifecycle generation + 不复用 CallId + exact int32 instance ID；不能以资产/8位计数替代 |
| 阶段与返回 | 原生三阶段独立于完整 ASC scope；父精确实例尚未观察到时为 PrecreationRejected，最内层 Returned 为 PostWriteRejected；失败子调用不标记成功接管；原生返回先屏蔽、Complete 只封存 |
| 生命周期与清理 | game thread；弱原接收者；回调只读；代次失效不释放栈；析构只注销自己、不清新 owner；无指针跨回调保留 |
| 抽象范围 | 无 global attempt map/timer/第二执行链；没有实现注册器、屏障或 RAII 函数体 |
| 扩展风险 | 非 scoped / fractional / simulated / 跨 coordinator / 并存策略 / 生产 ABP 未承诺；同资产旧预测拒绝与破坏性 Started 回调仍未关闭 |

源码静态检查包含八个 Outcome、三阶段、关键签名、非复制/非移动、无内联函数体、无 GAS include。对现有 `GGYGOAnimInstanceBase.h` 执行前后 SHA256 核对：`B2D251760E2BE1E5EC41DEFA32FA8C4CFE80E5D218D57F72149FD910680F22EE`，无变化。仅证明此冻结文件未被本步骤修改，不代替全项目其他工作线的状态证明。

静态脚本九项检查全部 true（八 Outcome、无 GAS include、无 UCLASS/USTRUCT、无函数体、CanExecute 声明、Complete 声明、const GetResult、四个 deleted 复制/移动操作、基类 hash 保持）。头文件冻结 SHA256：`ACAEA0FD27ED2F474C8BC107886860BD7DADE72F452902A748B7F8AFE4E3855A`。A1 时步骤记录历史 SHA256：`A76A5A86938F92839503AC6CA9D9749F58E35529598BB7D68D0A0F9FB78C2858`，两记录在 A2 租约内已更新。

## A2 实现与拒绝分类

`UGGYGOMontageGuardAnimInstance : UAnimInstance` 是 A2 新薄类；A2 完成时未改变现有继承链，后续 A3 仅改变 Base 父类。每个实例唯一持有非拥有 ScopeChain；每个 scope 的私有 FState 保存 request/result、前置 ID 快照和注册/封存信息，没有全局 attempt 表、GAS 播放副本、额外播放器或帧调度。所有公开 scope/生命周期/播放入口断言 game thread。

| 条件 / 阶段 | 本调用结果 / 原生次数 |
| --- | --- |
| 原 AnimInstance 不存在、未初始化、原 caller/ASC 失效、caller 回调 false、代次变化/计数耗尽 | LifecycleInvalid；准入阶段零次 Super，若原生调用已经执行则屏蔽其返回为0 |
| 原实例不是新 guard、缺少回调/有效请求资产、跨 coordinator/组、活跃其他组并存、bStopAll=false、资产与 request 不同、ID 集合异常、与无 scope 原生栈混用 | Unsupported；准入零次 Super |
| 最内 scope NotEntered，或 Executing 尚不能唯一识别父新实例 | PrecreationRejected；零次 Super |
| 最内 scope Returned（即使更外层 Executing） | PostWriteRejected；零次 Super |
| 无新 scope 的直接播放进入已有保护栈 | 返回0且零次 Super，不伪造父 scope 的执行结果 |
| 完全无 scope 的普通顶层播放 | 原引擎一次 Super；无受保护结果。其同步无 scope 嵌套保守返回0 |
| 合法 scoped 原生执行但返回非正/非有限，或本调用精确实例无法识别/不再活动 | Failed/0；恰好一次 Super |
| 合法 scoped 原生正有限返回、精确实例活动/播放、自身 caller 有效 | 原生阶段暂记 Accepted 并返回原值，恰好一次 Super；Complete 再验 caller 返回及精确实例后封存并发布接管 |
| 成功子/孙已封存 Accepted，同代祖先仍 Executing | 祖先 Superseded/0；祖先已执行的唯一 Super 不重放。自身 caller 已 false 不覆盖成功接管分类 |

准入拒绝发生在 Super 之前，后置失败/失效/被接管是在已执行的一次原生调用后屏蔽返回。错误地在原生执行中或非最内层调用 Complete 为 Unsupported，封存后不会被后续原生返回修改；这是调用协议失配，不表示“零次执行”的普通准入拒绝。Result 在 Complete 后才是封存证据，未封存 Outcome/NativeStage 不作为外部播放权威事实。

统筹 coordinator 补充已落实：CallerIdentity 比较原 ASC，不比较具体 GA/Task。各 Task 的生命周期由自身 callback 的弱捕获提供。新类不包含 ASC/GA/GAS 头，不知道实际 Task 类型。父资格不执行父 caller 验证，A 在 Started 内 End 后 B 自身仍有效可准入；GA End 不失效 Animation 代次。

## A2 返回、身份与清理静态断言

| 核对项 | 实际源码结论（未运行专项） |
| --- | --- |
| Super 次数 | 两个互斥调用点：无 scope 顶层兼容分支、scoped 合法原生分支；前置拒绝直接0，不重放/恢复播放 |
| 同资产 | 前置保存全部引擎 ID，首次从请求资产的新 ID 差集要求恰好一个；绑定后仅按精确 ID 重新解析。父 ID 在 child native 之前绑定；不读 ActiveMontagesMap/按资产“当前实例”推断 |
| 回调边界 | 四处局部 FAnimMontageInstance 查询/遍历均不跨回调；Super 前后保存弱原实例、整数 ID/集合。原生返回同代时先尽可能补录 own ID，再判成功接管/自身失效 |
| End A→有效 B | 子准入只校验 B callback 与父原实例/代次/最内阶段/实例身份；不查询 A callback。B Complete Accepted 后 A 先看成功 CallId，再看 A callback，结果 Superseded/0 |
| End A、无成功后继 | A 原生返回 own callback 为 false，LifecycleInvalid/0，不写回正值；不把 GA End 当动画初始化边界 |
| 失败/拒绝子调用 | PublishAcceptedCall 只从 Complete 的 Accepted 分支调用；原生失败、正值伪造、拒绝、caller 失效或未 Complete 都不发布成功 |
| 成功孙、中间返回0 | 孙 Complete 直接传播到所有同代 Executing 祖先；中间层按已有成功 CallId 为 Superseded/0，不吞掉孙证据、不冒称自己 Accepted |
| Returned 重入 | 构造/CanExecute 都看最内父 Returned，子为 PostWriteRejected；外层 Executing 不解除门禁，子不运行 native |
| 生命周期 | initialize/uninitialize/owner 变化推进非回绕代次，使未封存活记录失效；保留链至每个原 scope 析构。CallId 不重置；耗尽拒绝 scoped 准入 |
| Complete / 析构 | Complete 仅首次封存、无 GAS 回滚；旧析构用原弱 guard/自身 scope 与 CallId 注销，不比较当前 owner、不停止实例、不清新代次注册；原对象消失只释放私有 scope 状态 |
| 状态所有权 | 引擎仍拥有 MontageInstances；ASC/GA 权威信息不复制。成功 CallId 是发生过的调用证据，后继之后结束不能恢复祖先旧写回 |

API 只读复核发现并修正：UE 5.8 `GetMontageInstanceForID` 非 const，新私有活动检查相应非 const；`TGuardValue` 实际头为 `Templates/UnrealTemplate.h`。没有使用未导出引擎 helper。

静态脚本14项全部 true：A1 hash、既有基类 hash、无 GAS include、互斥两个 Super 调用点、无清空 scope 链、无 CallId 复位、无新增执行/停止/位置/Timer、无资产“当前实例”查找或 Local/Rep 状态、实际 GuardValue 头存在、ID 查询调用方非 const、九处 game-thread 断言、不查询父 caller 回调、无持久原始实例指针、花括号平衡。逐分支人工复核如上；这些检查不代替编译或行为测试。

A2 完成时的历史冻结 SHA256（A4 只追加查询后的新 hash 见下节）：

- A2 h：`ABFF09797EF0A603F05933FF042028E8E540C3AB462108C6B12E1432B3224434`
- A2 cpp：`1FC41A9BBC1626DC03DD0D2A0E128136E8B36FE8DC0F78F94C35AB79C852BF50`
- A1 h：`ACAEA0FD27ED2F474C8BC107886860BD7DADE72F452902A748B7F8AFE4E3855A`，保持
- A2 完成时基类 h：`B2D251760E2BE1E5EC41DEFA32FA8C4CFE80E5D218D57F72149FD910680F22EE`，A3 前基线

## A3 逐字与生命周期静态验证

本次源码唯一差异：

| 行 | 修改前 | 修改后 |
| --- | --- | --- |
| 8 | `#include "Animation/AnimInstance.h"` | `#include "Animation/Runtime/GGYGOMontageGuardAnimInstance.h"` |
| 21 | `UGGYGOAnimInstanceBase : public UAnimInstance` | `UGGYGOAnimInstanceBase : public UGGYGOMontageGuardAnimInstance` |

将原头字节保存在会话内存（无额外文件），解码后只作这两处替换，与实际头全文逐字相等；差异行恰好2。全量字段、API、元数据、注释与换行均保持。六项静态检查全部 true：预期文本相等、两行差异、Base cpp hash 不变、A1 hash 不变、A2 h hash 不变、A2 cpp hash 不变。

| 生命周期 | 只读确认的调用顺序 | Base / Guard Super 次数 |
| --- | --- | --- |
| Initialize | Base Super → Guard 代次失效/Engine Super/绑定 owner → Base 既有 D6 重置/绑定 Character/抓帧 | 各1，无 Engine 直调绕过 |
| Uninitialize | Base 既有 D6 重置 → Base Super → Guard 代次失效/清 guard owner/Engine Super | 各1，无 Engine 直调绕过 |
| Update | Base Super → Guard 核对 owner 代次/Engine Super → Base 既有 Character 边界重置/抓帧 | 各1，无 Engine 直调绕过 |

三个方法体静态抽取核对通过；未新增生命周期调用或更改 cpp。Guard 的代次/调用证据和 Base 的表现派生状态各归原实现管理，无第二执行链或调度器；头仅依赖 Guard，Guard 不反向依赖 Base，无新增循环依赖。无需扩改生命周期。普通无 scope 顶层播放继承 A2 兼容路径；完整 Scope 保护仍需后续 ASC/Task 接入，不把本步当成消费者完成。

A3 完成时的冻结 SHA256：

- Base h（A3 后）：`010DDC81E74AA20BCFC0741F85D77E1BD4554A4728252195A20116D59625E614`
- Base cpp（只读，保持）：`5923F245885CA98B4E19F260BA2DC079BF965FC259A78F7BE41BE9885A94BF6B`
- A3 核对时 A1/A2 h/cpp：保持上节记录的各 SHA256；A4 之后 Guard h/cpp 仅新增查询

## A4 纯查询与边界静态验证

新增唯一接口：

```cpp
bool IsMontagePlayGuardIdentityCurrent(
    const FGGYGOMontagePlayGuardIdentity& Identity) const;
```

纯 game-thread 查询；不改变 A1 Identity/Scope/结果契约。读取 `bLifecycleReady`、`bIdentityExhausted`、弱原 AnimInstance、当前 generation、LastCallId、捕获 owner/此前有效 owner 标记与只读 `GetOwningActor()`。没有调用 Refresh/Invalidate、没有写字段或推进代次、没有访问 ScopeChain/Task 缓存/ASC/GA/实例集合。唯一局部变量是当前 owner；没有新增字段/属性/注册/委托/调度。

| 边界条件 | 源码判断（静态，未运行测试） |
| --- | --- |
| 未初始化、已 Uninitialize、身份耗尽 | false；只看现有就绪/耗尽字段 |
| 弱原 AnimInstance 无效或不是 this | false |
| generation 为0或不是当前代次 | false；已观测换代后的旧身份拒绝 |
| CallId 为0或大于 LastCallId | false |
| 本代已发行旧 CallId（不是最新） | 其余条件满足时 true，不要求等于 LastCallId |
| 捕获 owner 与当前 owner 相同，原有效 owner 仍有效 | 其余条件满足时 true |
| 合法原初始化没有 owner，捕获和当前仍均为空 | 其余条件满足时 true；不新增角色业务限制 |
| 当前 owner 改变但尚未 Refresh | false；比较当前实际 owner，不在查询中推进代次 |
| 原有效 owner 弱失效，当前也为空 | false；此前有效标记与 IsValid 防止空值相等误过 |
| 本代 Montage 已停止、原精确实例已被移除，甚至 CreatedInstanceId 为 INDEX_NONE | 不读取这些事实；生命周期条件满足仍可 true，供旧资源清理的下一层验证 |
| 未被任何生命周期入口/guard 观测到的 owner A→B→A | 不保证发现；无历史事件来源，不能在纯查询中补建缓存 |

true 只表示当前生命周期/owner 与已发行 CallId 范围匹配，不证明该调用 Accepted、仍拥有当前播放、ASC/GA/Avatar/激活权限或精确实例存在。执行入口仍须按 Identity 精确 ID 在原 AnimInstance 重新解析，并校验所属资源/能力上下文；这里不做新状态或所有权权威。

静态14项全部 true：恰好一个声明注释块和一个定义块；移除新增块后原 h/cpp SHA256 与 A2 完全相同；A1/Base h/Base cpp hash 保持；查询无 Refresh/生命周期写入或递增；无实例活性/存在查询；无 Scope/Task 缓存；不要求最新 CallId；game-thread 契约；保留合法空 owner；generation/CallId 范围条件齐全。const 方法逐句审查只有读字段、弱引用/GetOwningActor 与 bool 返回，重复查询无状态副作用。这是静态断言，不代替动态边界用例。

当前冻结 SHA256：

- Guard h（A4 后）：`6BD6A6DC686074608213F5DF567957D1F10A2D5DBB537BD8C70E0687BA910766`
- Guard cpp（A4 后）：`2357E96AF6F312FE2C691A09C79988DC10A6FC578B48AF96604CE1D5D9621995`
- 移除新增声明块后的 h：`ABFF09797EF0A603F05933FF042028E8E540C3AB462108C6B12E1432B3224434`
- 移除新增定义块后的 cpp：`1FC41A9BBC1626DC03DD0D2A0E128136E8B36FE8DC0F78F94C35AB79C852BF50`
- A1 h/Base h/Base cpp：保持前述 `ACAEA0FD...` / `010DDC81...` / `5923F245...`

## 未运行与未验证

本步骤没有运行 UHT/UBT/编译、UE、自动化、Git 或资产操作。A1/A2 原机制已由统筹第15次编译验证；A3 新继承链及 A4 新方法尚待下一次 UHT/完整构建和行为验证。仅追加 Guard h/cpp 查询块与更新本地两记录；A1/Base/旧 A2 机制/ZZZ/ASC/Task/测试、Obsidian、全局 ledger/schedule/routing 未改。没有 Guarded ASC/Task Scope 或查询消费者接入。P1 没有重跑，原严格红证据保留，A4 不能被写成 P1 已修复。

原同资产预测拒绝按资产停止后继的问题、fractional/simulated 入口、第三方直接播放、不同组并存策略、网络预测与生产 ABP 迁移仍未验。破坏 mesh/反初始化导致引擎 Started 返回后自身使用已释放实例的危险不能由返回屏障修复，不提供该引擎安全保证。caller 在 scope 外先取消 GA 的动作也不由拒绝播放自动恢复。

已按项目规则再次只读核对 Obsidian `计划蓝图.md` 的 Animation 路由及 `Animation/结构.md`。后续笔记窗口须增加 Guard/Scope/A1 契约及 `Base → Guard → UAnimInstance` 继承关系，补 A4 只读身份查询的输入/输出及边界，并写清 **A1/A2 原机制编译通过，A3/A4 静态完成未编译，ASC→Task→专项待接入/验证**；既有 D6/StateFrame/ZZZ 内部职责保持。结构/流程 Canvas 不提前画成已实现的 ASC Scope/查询消费。当前租约禁止 Obsidian 写入，同步建议交回统筹，本地两记录保存真实状态。

## 冻结与交接

A4 四文件已静态复核并冻结；A1/Base/旧 A2 机制保持。交接为纯查询声明/定义、边界/副作用审查与新增块以外逐字不变证据。没有扩改 A1 或生命周期机制；调用方/测试/资产/笔记仍须统筹授权。后续统一构建先确认所有源码写入者冻结。本交接不证明 B4、生产 ABP 迁移或动态验收完成。
