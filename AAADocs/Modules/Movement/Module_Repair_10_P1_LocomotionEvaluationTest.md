# C33 / P1-T1：Locomotion Evaluation 三项纯契约测试

日期：2026-10-01（北京时间）。当前状态：C34命名隔离后，第38次完整构建Succeeded，新运行时DLL中T1三叶Success（正常报告73 Success）；原I/T1/R1静态及37失败历史保留，当前结果以末尾C35为准。未接生产，Run未验，T2/P2未授权；本次两记录交回冻结。

## 授权、职责与唯一结果

统筹全文接受六契约预检后，只授权 T1 三个叶及以下两份新文件；入口核对两文件均不存在。Movement 长期组长直接执行，不创建代理。

- `Source/GGYGO/Character/Tests/GGYGOLocomotionEvaluationTest.cpp`
- `AAADocs/Modules/Movement/Module_Repair_10_P1_LocomotionEvaluationTest.md`

唯一结果：用真实 Profile/RichCurve 验证冻结 Evaluation 的单资产原始/缩放结果、双侧必需的端点，以及共享相位和跨周期 Yaw。测试不是生产状态、曲线求值器或执行器。

非目标：DirectionAndLegalZero、NumericAdmission、完整 Atomic/Cubic、P2、生产/helper/Profile 接口、旧测试、10 两份旧记录、图文、资产、测试钩子、World/Actor、UE、构建、Git。不会借本范围扩大到其余三个契约。

依赖方向：新测试 → 冻结 Evaluation/Profile/MovementTypes → 引擎基础曲线与 UObject。现有 ProfileTest 仅只读参考夹具，不 include 其 cpp。与 K4-I1 的共享 ASC h/cpp 没有文件或状态交集；这里只保护下表九份文件，不声明并行窗口全源码 hash 保持。

## 原子步骤

| 唯一目标 | 精确文件 | 只读依赖 | 验收断言 | 停止点 |
|---|---|---|---|---|
| T1 三个纯契约叶 | 上述新测试 cpp 与本记录，共两文件 | Evaluation h/cpp、Profile h/cpp、MovementTypes.h、既有 ProfileTest.cpp、P1-I 记录；10 旧记录保护 | 真实夹具；全部成员覆盖；端点两侧必需；精确周期端点；独立跨周期数值；失败完整 Reset 与旧 Error 替换 | 两文件静态审查/hash 交回并停写，由统筹待全部作者冻结后安排新构建/UE |

顺序：本记录预检/hash → 三叶测试实现 → 仅两文件静态核对与记录 → 交回冻结。构建或运行失败须按实际证据另行交接，不自行修改生产或其它测试。

## 夹具与验收

真实 `NewObject<UGGYGOLocomotionMotionProfile>(GetTransientPackage())`，以 `TStrongObjectPtr` 保持调用期生命周期。直接设置 Duration/bLoop 与四份 FRuntimeFloatCurve，显式 Linear 多键或原生允许的单键常量。不创建 World/Actor，不新增测试生产入口。

统一名称前缀：`GGYGO.Movement.Locomotion.Evaluation.`。

| 叶 | 计划验收 |
|---|---|
| `SingleInterval.RawAndScaled` | 非 Loop Duration=1，Speed=8/+X，Yaw 0→40；区间[0.25,0.5]。Scale=2 时原始 Speed=8、YawTotal=20、YawDelta=10，缩放 Speed/Velocity=16/+X；Scale=0 只清缩放结果。完整原始样本与原生区间结果逐成员一致，脏输出全部覆盖且旧 Error 清空。一次缺 Yaw 的原生委托失败验证全部 Reset 与旧 Error 替换。 |
| `WalkRun.RequiredEndpoints` | 两侧周期 `2^80` 与 `2^-10` 及交换次序，Alpha=0/1；起点0.25、选中周期的1/4秒，终点精确0.5，ClipLength 精确等于选中周期，完整 Sample 等于原生端点。对未用侧分别设置空指针、非 Loop、缺 Yaw、负 Speed 第二 key，两端仍失败；检查完整 Reset、失败侧/字段/原因与旧 Error 替换。 |
| `WalkRun.SharedPhaseYaw` | Walk Duration=2、Speed 4→20、Yaw 0→80/+X；Run Duration=4、Speed 8→72、Yaw 0→160/+Y。起点0.75、接受区间6.25秒、Alpha=0.25、Scale=2。独立期望周期2.5、终点3.25、Speed=12、YawTotal=325、YawDelta=250；方向(3,1,0)/√10、Angle≈18.4349488°、ScaledSpeed=24。全部成员检查，PositionDelta=0/false。 |

共用检查逐项覆盖 Sample 的五个 float、三向量九分量、四标志，以及 ScaledSpeed/ScaledVelocity 和 EndCyclePosition。Motion 共22个标量/标志检查，WalkRun 共23个；脏值明确覆盖每个成员，不以 memcmp 或只查 Speed 代替。精确零/端点/Speed/Yaw 使用零容差；跨周期方向/速度仅使用1e-6分量容差、Angle使用1e-4度容差。独立期望为固定数值，不复制 helper 的相位混合算法。

## 写入前保护基线

九份只读保护文件的入口 SHA256：

| 文件 | SHA256 |
|---|---|
| `Source/GGYGO/Character/Data/GGYGOLocomotionEvaluation.h` | `B7E474D3703820EE112998C1DCC67BFB5A86D4A3C24AA816F2D36E2F55B2916A` |
| `Source/GGYGO/Character/Data/GGYGOLocomotionEvaluation.cpp` | `E02CA4FAE7083E36687CAFF81ECB139F8C69F1CFC125D69CF632A8A5A2F556AF` |
| `Source/GGYGO/Character/Data/GGYGOLocomotionMotionProfile.h` | `26FF4A2649C4ECD8141E6E86540EF2B9D232DF2A8F4E4D0EA65BA2F237943857` |
| `Source/GGYGO/Character/Data/GGYGOLocomotionMotionProfile.cpp` | `16216760DD9C573CECC1DD8E060E11B80F027BB650FF5B10DC341D71415FD5DB` |
| `Source/GGYGO/Character/Data/GGYGOMovementTypes.h` | `DAD60682D81764AD7FE58A391CD97F71BEB6129614F36A123A379BA82C03B7A6` |
| `Source/GGYGO/Character/Tests/GGYGOLocomotionMotionProfileTest.cpp` | `E175F594B4B0632DDF2848A069DB9DD9049CB6D0D1ECE404DA02C985BB7FAC67` |
| `AAADocs/Modules/Movement/Module_Repair_10_P1_LocomotionEvaluation.md` | `E934A75C77DDC7944CA4025C25DF9A7ABEAF58E1EF3E387AD727AEA3533DD465` |
| `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md` | `01ABDF6D26C4D74A8F3585FB57D55B3F618D61172CA4E37F1881C8D90439AC5D` |
| `AAADocs/Modules/Movement/Module_Repair_10_Validation.md` | `48570917A8D815265FE58E855F1AFB29152F25CD600B06C4FAC8D04CD8F6BF24` |

## 实现与静态交回

- 仅通过 apply_patch 先创建本记录，再创建授权测试 cpp，最后更新本记录；没有其它文件写入，没有调用 UE/构建/Git或创建代理。
- 原T1静态交回时的新测试 cpp：17401字节、356行，SHA256 `159249D3580E04627D697ADD340452B8B8B53E9ECA840C1FAA70F8DF360EB1AF`。原独立记录SHA256为 `2092F8FC4F32067FB4DFDCD9300ECFE1D2CD48ACFF8D74ECFC96A59645C6A9D7`；以下保留当时静态证据，C34修后结果另列。两文件最终 hash 由交回消息另列，避免记录自引用。
- 实际只注册上述三个具名叶，均为 EditorContext/EngineFilter，放在 WITH_DEV_AUTOMATION_TESTS 下；未注册后三个契约。
- 源码场景计数：Single 2次成功尺度/1次缺Yaw失败；Endpoints 两种周期次序×两端点共4次成功、四种坏未用侧×两端点共8次失败；SharedPhase 1次成功。共7个成功/9个失败期望场景、16次 helper 调用；这是源码静态展开，不是执行次数或测试结果。
- 完整逐成员检查与脏值构造覆盖全部12个 Sample 成员、两个缩放成员及 WalkRun 终点；向量按XYZ分别检查。每个预期 helper 失败均接入完整 Reset 与非空/替换旧 Error 检查，意外失败的成功用例也检查该失败契约。
- 单资产既对比原生完整 Sample，又核对固定期望 8/20/10 与16或0的缩放；端点对比原生完整选中样本、精确终点0.5与选中周期。SharedPhase 的期望写成固定数字、方向/速度分量，未调用 BlendScalar、归一化或 helper 私有算法作 oracle。
- 坏未用侧错误检查包括失败侧字段、原因、实际对象路径，以及适用的原生字段/key和两侧映射秒区间；非 Loop/空引用在映射之前失败，不虚构其映射区间。完整 NativeError/Cubic 矩阵仍留后续 Atomic 契约。
- 实际使用真实 Profile/FRichCurve，单键代表常量，Linear 双键覆盖 Duration；局部 TStrongObjectPtr 随测试结束释放，没有持久资源、状态机、计时器、跨模块状态或测试生产接口。
- 九份保护文件 SHA256 与入口全部一致；新 cpp 为UTF-8无BOM、LF、末尾换行、无行尾空白。仅核对本租约保护集合，不据此声明并行 K4-I1 的全部源码保持。
- 已逐行静态审查新 cpp，核对 AutomationTest 的实际 float/double/值类型重载；未进行 C++ 编译、链接或数学动态执行。

## 未验边界与图文交接

- 三叶已编码并进入第37次统一构建，但该构建失败、未生成新DLL，三叶未运行，不能记录为通过；第36次结果不能证明在该窗口之后创建的 T1 测试。C34短修后仍须等待全部源码作者冻结，由统筹安排新编号完整构建/UE门禁。
- P1-I 仍无生产消费者；生产 Run、七 Profile、AnimBP 图引脚、CMC/RMS 失败链、首次 Prepare、重放与代理保持开放。
- 实现后只读核对 Obsidian `计划蓝图.md`、Movement `结构.md`、`计划_移动与动作位移.md`：模块定位仍为Movement，尚未列出 Evaluation、新测试或C33。图文明确不在 C33 范围；新数学底层/专项状态须在独立图文租约中同步，本记录只交回实施事实与未验边界，不冒称 Obsidian 已同步。

## C34 / P1-T1-R1：unity命名隔离预检

第37次实际日志 `Saved/Logs/ModuleRepairBuildGate_20261001_37.log` 已只读核对：旧 ProfileTest.cpp:88 的局部 PreviousError 隐藏新测试cpp:14匿名namespace的同名常量，报唯一C4459，Failed (OtherCompilationError)、UBA41.41秒、总45.45秒。统筹门禁记录为7计划动作止于4编译、exit6；未链接新DLL、未运行UE、未建立37报告，249源码/14保护前后保持及UE0是统筹本次核对证据，不充作本组长短修后的全量hash结果。

根因：unity把多个cpp合成同一翻译单元，匿名namespace的辅助符号进入共同查找范围。修正归新测试辅助符号所有者，不改旧测试的合法局部名称或构建诊断规则。

唯一写入范围仍为本记录与 `Source/GGYGO/Character/Tests/GGYGOLocomotionEvaluationTest.cpp` 两文件。修前cpp SHA256为 `159249D3580E04627D697ADD340452B8B8B53E9ECA840C1FAA70F8DF360EB1AF`，修前记录为 `2092F8FC4F32067FB4DFDCD9300ECFE1D2CD48ACFF8D74ECFC96A59645C6A9D7`。

| 唯一目标 | 精确改动 | 只读依赖与非目标 | 验收断言 | 停止点 |
|---|---|---|---|---|
| 隔离新文件全部辅助常量/函数 | 原辅助namespace改为专用 `GGYGOLocomotionEvaluationT1`；只在三个RunTest函数体内部引用它；记录真实失败及修复 | 旧测试/生产只读；不改三叶类名/注册路径、夹具/曲线、调用参数/次数、断言、helper/Profile/CMC/RMS/ASC、10旧记录、Obsidian、资产、Build.cs、unity/告警设置或引擎 | 无全局using；剥除仅命名隔离差异，完整恢复修前cpp SHA256；三叶与完整测试语义保持；受保护文件不变 | 两文件实际diff/hash与逆向证据交回，明确停写，待统筹新构建；不自动T2 |

先登记本预检与修前hash，再只实施上述命名隔离。本组长未运行编译/UE/Git，未创建代理；R1尚无新构建或运行结果。

### R1实际交回与逆向证据

- cpp实际17567字节、359行，SHA256 `C9B813F49BFA6A57AD455A63F8D5CD28D4AA0C1E006B92E1E5DBBC0727EA78B3`。完整源码差异只有四处：辅助namespace命名、三个RunTest体开头各增加一条局部using；无全局using。
- 只在内存中把专用namespace恢复为匿名namespace、移除三条局部using，重建的完整UTF-8源码SHA256精确等于修前 `159249D3580E04627D697ADD340452B8B8B53E9ECA840C1FAA70F8DF360EB1AF`；未写恢复文件。因此原三叶类名、注册路径、夹具/曲线、调用参数/次数、全部原断言与容差均原样保留。
- 三条using经文本定位全部位于三个RunTest函数体内。所有辅助常量/函数在独立 `GGYGOLocomotionEvaluationT1` 命名空间中，不向unity其它测试的查找范围注入符号；不依赖关闭unity或修改警告设置。
- 原九份保护文件hash与T1入口一致，包括旧ProfileTest、生产Evaluation/Profile/Types和旧记录。只修改授权两文件；不把这一局部核对表述为全249源码或14保护的R1后全量核对。
- 两文件保持UTF-8无BOM、LF、末尾换行与无行尾空白；cpp已静态核对完整diff及逆向hash。辅助命名改变不改变模块职责、公开接口、状态归属、执行链或资源生命周期；原图文待同步缺口保留，不扩大图文范围。
- 本记录保留原T1范围、入口hash及静态证据，并同步37真实失败。最终两文件hash和完整差异由交回消息提供，记录不保存自己的最终hash。

**停止点：两文件已停写冻结，等待统筹新编号完整构建及实际UE报告。第37次仍是失败，R1尚未编译/运行；没有新测试通过证据，不自动T2，不关闭生产Run或原失败传播边界。**

## C35 / P1-V2：第38次验证证据同步

### 两文件窄预检与写入前基线

日期：2026-10-01。统筹登记C35两份既有独立记录的文档租约，唯一写入者Movement长期组长，直接执行。先在两文件登记本预检/基线，再更新顶部当前状态并追加第38次证据；不改原I/T1/R1正文或37真实失败历史。

| 唯一结果 | 精确文件 | 只读依赖 | 非目标 | 验收与停止点 |
|---|---|---|---|---|
| 同步真实编译、三叶有限契约Success及未接生产边界 | `AAADocs/Modules/Movement/Module_Repair_10_P1_LocomotionEvaluation.md`、`AAADocs/Modules/Movement/Module_Repair_10_P1_LocomotionEvaluationTest.md` | 冻结helper/Testcpp，统筹38构建日志/报告/排程及36旧路径 | 不写源码、旧10记录、Obsidian、第三文件或资产；不跑UE/构建/Git，不创建代理，不实施T2/P2 | 两整文剥除仅C35新增段并恢复原顶部行后，恢复各原完整hash；源码保护不变；实际两hash/未验项交回即停写 |

两记录入口SHA256：

| 文件 | SHA256 |
|---|---|
| `AAADocs/Modules/Movement/Module_Repair_10_P1_LocomotionEvaluation.md` | `E934A75C77DDC7944CA4025C25DF9A7ABEAF58E1EF3E387AD727AEA3533DD465` |
| `AAADocs/Modules/Movement/Module_Repair_10_P1_LocomotionEvaluationTest.md` | `8C1E2E9C6BA8BA108684160CE230D6CBECF1A87D369254466E7F39A1E19FDC12` |

本步骤自算保护集合仅为以下三份源码及两份旧记录；统筹38窗口的249源码/14保护证据另外归属，不混作本组长全树实算。

| 文件 | SHA256 |
|---|---|
| `Source/GGYGO/Character/Data/GGYGOLocomotionEvaluation.h` | `B7E474D3703820EE112998C1DCC67BFB5A86D4A3C24AA816F2D36E2F55B2916A` |
| `Source/GGYGO/Character/Data/GGYGOLocomotionEvaluation.cpp` | `E02CA4FAE7083E36687CAFF81ECB139F8C69F1CFC125D69CF632A8A5A2F556AF` |
| `Source/GGYGO/Character/Tests/GGYGOLocomotionEvaluationTest.cpp` | `C9B813F49BFA6A57AD455A63F8D5CD28D4AA0C1E006B92E1E5DBBC0727EA78B3` |
| `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md` | `01ABDF6D26C4D74A8F3585FB57D55B3F618D61172CA4E37F1881C8D90439AC5D` |
| `AAADocs/Modules/Movement/Module_Repair_10_Validation.md` | `48570917A8D815265FE58E855F1AFB29152F25CD600B06C4FAC8D04CD8F6BF24` |

已先在两文件完成本预检/基线登记，再按以下实际38证据更新顶部与尾部。原模块职责、数学接口、状态归属和执行流程不因本步骤改变。

### 第38次实际构建与三叶结果

组长只读核对 `Saved/Logs/ModuleRepairBuildGate_20261001_38.log`：实际4 actions，编译Module.GGYGO.3.cpp、链接UnrealEditor-GGYGO.lib/新的运行时UnrealEditor-GGYGO.dll，Result Succeeded，总13.16秒、UBA12.05秒。统筹38窗口确认exit0，本次无新UHT或Editor模块DLL重链；不把运行时DLL链接扩大成这两项新构建证据。

实际报告：`Saved/AutomationReports/ModuleRepairGate_20261001_38/index.json`。报告时间2026-10-01 13:37:57 UTC = 北京时间21:37:57；SHA256 `6D27694D8437373D857AF964900719168D1613B9D890AB7A1F808E253E14C1A1`。

- 73 Success；succeededWithWarnings/failed/notRun/inProcess全部0；总时长0.8906704187393188秒。
- 组长逐项核对73叶均Success、errors/warnings总和0。与36报告直接比较，旧70路径无删除，仅新增下表三路径；未以旧DLL代替新测试证据。

| 实际叶路径 | 状态 | 时长（秒） | errors / warnings | entries |
|---|---|---|---|---|
| `GGYGO.Movement.Locomotion.Evaluation.SingleInterval.RawAndScaled` | Success | 0.008366599678993225 | 0 / 0 | `[]` |
| `GGYGO.Movement.Locomotion.Evaluation.WalkRun.RequiredEndpoints` | Success | 0.008213300257921219 | 0 / 0 | `[]` |
| `GGYGO.Movement.Locomotion.Evaluation.WalkRun.SharedPhaseYaw` | Success | 0.010227702558040619 | 0 / 0 | `[]` |

通过范围：单资产完整原始/缩放结果与Scale=0、双侧含端点必需及坏未用侧明确失败/完整Reset、极悬殊周期端点、共享相位与多周期Yaw的独立数值。原三叶路径/全部断言与夹具保持；C34的unity命名隔离已进入新的完整成功构建及真实三叶运行。第37次C4459失败仍是历史事实，未删除或改写。

### 原日志诊断与证据归属

组长只读计数 `Saved/Logs/GGYGO_ModuleRepairGate_20261001_38.log`：49条Error，类别分别LogAutomationTest 13、LogGGYGOAbilitySystem 34、LogAnimation 2；按统筹38窗口分类对应启动Smoke13、Damage预期34、Bake预期2。另有3条Warning：DDC路径写入失败、Python枚举同名、HTTP探测超时。因此报告三叶/73正常叶零错误警告，不等于全日志无诊断。

统筹38窗口实际确认249源码/14保护在构建及UE期间保持、UE exit0已退出、UE0且无资产保存。此处引用统筹窗口证据，不称本组长当前实算全树或进程；本步骤只重新保护自身三份冻结源码及上表两份旧记录。36窗口248源码/14保护仅为其历史窗口，不混作38或本步骤计数。R0/Input/B0/原生P1严格诊断本次未重跑，73正常叶Success不能关闭其它已知红。

### 当前未验边界、历史与停止点

- 仅P1-I编译和T1前三个数学契约获得本次证据；DirectionAndLegalZero、NumericAdmission、完整Atomic/Cubic尚未新增或运行，不把前三叶成功写成六契约完成。
- helper尚无生产消费者。CMC/RMS旧数学及失败消费未迁移；统一提交/首次Prepare/重放/代理、失败终止当前请求及真实新请求准入未实施。七Profile/AnimBP图引脚/生产Run仍开放；无资产保存，不称Run已恢复。
- 本次只同步实施/验证状态，没有改变模块职责、公开接口、状态权威、依赖方向或执行生命周期。Obsidian和旧10记录明确冻结，原图文待同步缺口保留，等待独立图文租约。
- 原I/T1/R1的预检/静态/未验表述为各原时点历史，当前编译与有限三叶状态以本C35段及顶部为准。两文仅替换原顶部当前状态行并追加本C35段，整文历史可逆核对；没有修改原37失败或其它历史正文。

**C35两记录交回并停写冻结；源码/旧记录/第三文件/图文/资产保持冻结。不运行新UE/构建/Git，不创建代理，不自动实施T2/P2。最终两hash、整文历史逆向与源码保护结果随交回消息列出。**
