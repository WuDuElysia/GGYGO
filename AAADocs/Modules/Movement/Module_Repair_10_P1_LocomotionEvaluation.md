# C32 / P1-I：无状态 Locomotion 区间求值

日期：2026-10-02（北京时间）。当前状态：C38生产已编译，C38-T1新ColdAndRearm及旧AuthorityAndMapping经统筹Gate48新DLL确认Success/零诊断，普通81 Success/其它0；该门禁不包含真实FAILED恢复。C38-T2按独占两文件租约先登记预检、后追加唯一FailedRequestRecovery叶并完成有限静态核对，现交回冻结；保留两条生产Error及实际Automation Fail，只验严格诊断匹配，本批尚未新编译/运行。统筹已完成15篇Obsidian文档、6图/158链接/5锚点有限静态同步，未声明原生UI已验；本批图文/全局入口由统筹维护。首次W/Run、物理Source、Hero/MoveData、RMS真实模拟区间、正式七Profile/AnimBP/BlendSpace及网络仍开放；gadge占位，原TurnBack业务/曲线保持。下文历史按原时点保留，最新有限状态以末尾C38-T2为准。

## 授权与唯一目标

统筹已接受 P1 API，并登记 `Module_Repair_Parallel_Schedule.md` 的 C32 精确租约。用户已确认无状态数学拆分，以及运行失败终止当前请求、同 held 不重试、真实松开重按/新动作重新准入，坏配置不能绕过准入；本步骤只实现数学底层，不实现请求生命周期。

唯一写入者：Movement 长期组长，直接执行，不创建代理。仅授权以下三份新文件；入口已核对三者均不存在：

1. `Source/GGYGO/Character/Data/GGYGOLocomotionEvaluation.h`
2. `Source/GGYGO/Character/Data/GGYGOLocomotionEvaluation.cpp`
3. `AAADocs/Modules/Movement/Module_Repair_10_P1_LocomotionEvaluation.md`

唯一结果：建立无状态的单资产区间结果包装与双 Loop 共享混合、缩放及合成结果检查。它是待接入的数学接口，不是第二个 Profile 求值器或 Movement 状态来源。

非目标：CMC、RMS、已有测试、10 Subleases/Validation、Obsidian、资产、UE、构建、Git。纯测试 P1-T 和首次 RMS 装配 P2 是独立后续步骤，本租约不自动覆盖。

## 模块、依赖与责任

- 所属：Movement 的 `Character/Data` 数学底层。
- 依赖方向：Evaluation → 现有 `GGYGOLocomotionMotionProfile`、`GGYGOMovementTypes` 与引擎基础数学/UObject 有效性接口。没有 CMC、Animation、GAS、具体角色或招式依赖。
- `Profile::EvaluateInterval` 继续独占单资产曲线读取与资产合法性校验；helper 不调用 `ValidateProfile`，不逐项复制键、切线、外推或曲线校验。
- helper 校验自身输入、双 Loop 角色、区间映射/除法的运算安全，以及合成和缩放结果。指针只在当前调用中借用，不持有或缓存。
- CMC 仍独占段选择、执行状态、Profile 时间、循环相位与提交。helper 的 `EndCyclePosition` 仅为返回数据，没有引用写入、计时器或状态推进。
- helper 不输出日志。失败详情由调用方在真实请求/对象生命周期中诊断；本步骤不实现调用方日志或重试。

## 已冻结的数学接口契约

普通 C++ 值类型：

- `FGGYGOLocomotionEvaluationResult`：原始 `Sample`、`ScaledSpeed`、`ScaledVelocity`。
- `FGGYGOWalkRunEvaluationResult`：上述 `Motion` 与未回绕的 `EndCyclePosition`。

函数：

- `GGYGOLocomotionEvaluation::EvaluateSingleInterval(Profile, StartTime, EndTime, RootMotionScale, OutResult, OutError)`。
- `GGYGOLocomotionEvaluation::EvaluateWalkRunInterval(WalkProfile, RunProfile, StartCyclePosition, AcceptedIntervalSeconds, BlendAlpha, RootMotionScale, OutResult, OutError)`。

约束：

1. 单资产只调用现有 `EvaluateInterval`；原始样本与缩放样本分开，Scale 不缩放 Yaw。
2. 双侧均必须是有效且 `bLoop=true` 的 Profile；Alpha 为 0/1 也必须分别求值成功。端点原样保留对应原始样本，不因另一侧失败而救援。
3. StartCyclePosition 是非负有限的周期坐标，允许跨周期；AcceptedIntervalSeconds 是由调用方接受的非负有限秒区间。helper 不钳制 Delta，也不回绕或修改相位。
4. Alpha 必须有限且在 [0,1]；Scale 必须有限且非负。有效周期按两侧周期混合，终点为起点加区间秒数除以有效周期，再分别映射到两资产秒区间。非有限、除零或目标数值范围错误明确失败；不新增 Profile 的资产校验标准。
5. 两侧成功后混合 Speed、YawDelta、YawTotal 与 Direction；Direction 按已有规范归一化，再生成 Velocity、Angle、真实方向标志与有效周期。正原始速度无有效合成方向时失败，Scale=0 不能掩盖它。
6. 成功零速、零速配零方向、极小正速与零 Scale 都合法。`HasUsableSpeed` 的阈值语义保持独立，不能用作成功资格。
7. ScaledSpeed 使用现有 float Speed×Scale 数值契约；结果非有限时失败，不饱和、不替换固定速度。ScaledVelocity 从有效方向及该缩放速度生成，所有输出成员必须有限。
8. 入口清空全部 OutResult 与旧 Error；局部候选全部成功才赋值。失败输出完整复位，返回 false；合法零返回 true，保留真实成功来源标志。
9. Error 包含操作、失败字段/侧、Profile 路径与输入/映射区间。原生失败保留完整字段、键索引和原因；不以空值、捕获异常或其它业务结果回落。

## 原子步骤、只读依赖与停止点

| 步骤 | 精确文件 | 只读依赖 | 验收断言 | 停止点 |
|---|---|---|---|---|
| P1-I（当前） | 新 Evaluation h/cpp 与本记录，共三文件 | 实际 Character/Data 下的 Profile h/cpp、MovementTypes；旧 CMC 只作迁移对照 | 单资产委托；双侧必需；端点精确；合法零/极小/0Scale；合成/溢出明确失败；全输出原子复位；无状态/日志/缓存 | 三文件交回并冻结；未获 P1-T 租约不得创建测试 |
| P1-T（未授权） | 新 `Source/GGYGO/Character/Tests/GGYGOLocomotionEvaluationTest.cpp`，一文件 | 冻结 P1-I 与现有 Profile 纯测试夹具构造方式 | 独立纯叶验证数值、未用侧失败、方向抵消、跨周期、缩放溢出、Error 和脏输出复位；不建 World/Actor | 测试冻结后由统筹安排构建/UE，不借旧 DLL 证明新代码 |
| 后续消费者适配（未授权） | 现有 CMC h/cpp，另行独占租约 | 冻结 helper 与执行帧/失败消费契约 | 删除现有双 Loop 混合、单侧替代和重复缩放数学；传播 helper 失败，不能留下两套生产实现 | 执行/时间/请求协议冻结后才接入；当前不称兜底关闭 |

## 写入前保护基线

入口 SHA256（15 文件均为只读）：

| 文件 | SHA256 |
|---|---|
| `Source/GGYGO/Character/Data/GGYGOLocomotionMotionProfile.h` | `26FF4A2649C4ECD8141E6E86540EF2B9D232DF2A8F4E4D0EA65BA2F237943857` |
| `Source/GGYGO/Character/Data/GGYGOLocomotionMotionProfile.cpp` | `16216760DD9C573CECC1DD8E060E11B80F027BB650FF5B10DC341D71415FD5DB` |
| `Source/GGYGO/Character/Data/GGYGOMovementTypes.h` | `DAD60682D81764AD7FE58A391CD97F71BEB6129614F36A123A379BA82C03B7A6` |
| `Source/GGYGO/Character/Data/GGYGOMovementSet.h` | `D5509274F399B10BEF6CB1D2D677C87EC7923231EA1688DB0923094DD82C183D` |
| `Source/GGYGO/Character/Data/GGYGOMovementSet.cpp` | `E30485A826AF150C72CFA94D69ACF125AF188D4B8BE5F1FF38175745D5E53ABE` |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h` | `00C3B5A3E7DC963403D8D0FC5D67F361B09ABC40CA1983C20974A04DE89D0C7A` |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp` | `1AD15D3B4FCF36950B620D655B8B9414535C5B4DA65800E06D747B89287896FF` |
| `Source/GGYGO/Character/Components/GGYGOCurveRootMotionSource.h` | `DCA2DA64C9B7D06CF78711C2F3C62BA6CDDB4514FEC26543531B1CDE9BE4DBDB` |
| `Source/GGYGO/Character/Components/GGYGOCurveRootMotionSource.cpp` | `1A244710AB744496673048F1A1EDADB37E00E9B450373BE1F376140921C5EBB9` |
| `Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTest.cpp` | `59D81A4C651D43523394D9C0B58C87C82BAAF6C82282BD4BDFDC2676E5D1CDC3` |
| `Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTestTypes.h` | `78920CCD1FA1CE3D28321D7C6330235A4FC47B9768D83739F010CE706E1E09B5` |
| `Source/GGYGO/Character/Tests/GGYGOLocomotionMotionProfileTest.cpp` | `E175F594B4B0632DDF2848A069DB9DD9049CB6D0D1ECE404DA02C985BB7FAC67` |
| `Source/GGYGO/Character/Tests/GGYGOActionMotionTest.cpp` | `75ED3F333D57D08309D27E3342E60DC997A27344BFC63B2EB1D1DA85D7B3DED1` |
| `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md` | `01ABDF6D26C4D74A8F3585FB57D55B3F618D61172CA4E37F1881C8D90439AC5D` |
| `AAADocs/Modules/Movement/Module_Repair_10_Validation.md` | `48570917A8D815265FE58E855F1AFB29152F25CD600B06C4FAC8D04CD8F6BF24` |

## 实现与静态交回

先记录上述预检及15份保护基线，随后只通过 apply_patch 创建两份源码并更新本记录；没有创建测试或调用 UE/构建/Git。

两份源码最终状态：

| 文件 | 字节 / 行数 | SHA256 |
|---|---|---|
| `GGYGOLocomotionEvaluation.h` | 2465 / 64 | `B7E474D3703820EE112998C1DCC67BFB5A86D4A3C24AA816F2D36E2F55B2916A` |
| `GGYGOLocomotionEvaluation.cpp` | 12272 / 332 | `E02CA4FAE7083E36687CAFF81ECB139F8C69F1CFC125D69CF632A8A5A2F556AF` |

静态核对（文本结构与逐行审查，不是 C++ 编译或数值动态验收）：

- 两个公开声明与两个限定命名空间定义对应；单资产一次、双 Loop 两次现有 `EvaluateInterval` 调用，均接收失败结果。
- 两次 Loop 原生求值均在 Alpha 端点选择之前；端点直接复制对应完整原始样本。周期使用扩大精度加权和，保留大小悬殊周期的精确端点，避免差值抵消或 float 差值溢出。
- 单资产保留原生样本所有成员；混合结果的方向、Velocity、Angle 与方向标志从真实合成值生成，PositionDelta 保持现有 Profile 的零/false 契约。Scale 只产生独立 ScaledSpeed/ScaledVelocity。
- 两函数的公开输出赋值只有入口完整复位与末尾候选提交。原生失败、映射失败、正速无方向及缩放失败均不泄漏局部候选。
- Error 仅在失败时格式化，包含输入与可用的实际两侧映射秒区间；原生错误原样包入失败侧。局部 ErrorContext 只活在本次调用，不保存日志、历史、资源或跨帧数据。
- 没有 `ValidateProfile` 调用、键/曲线直接读取、Clamp/Fmod、速度阈值资格、日志、Tick、SetTime、RMS、World、状态机或重试。
- 源码仅依赖实际 Character/Data 的 Profile/MovementTypes。没有循环依赖、具体角色业务、外部状态写入或第二执行器；失败的局部值自然释放，无新增资源清理责任。
- 15份保护文件 SHA256 与入口全部一致；新源码及记录为 UTF-8 无 BOM、LF、末尾换行、无行尾空白。三文件最终 hash 由交回消息另列，避免本记录自引用 hash。

## 未验边界与笔记交接

- 新代码已编码但未编译/运行，P1-T 未授权。静态审查不证明 C++ 语法/链接、数值用例或原生动态消费；第35次旧 DLL 的65 Success不证明新 helper。
- 当前生产 CMC/RMS 数学与失败消费仍保持原样；七 Profile 资产未接线，AnimBP 图引脚/生产 Run、预测与代理均不因本步骤关闭。
- 实现后再次只读核对 Obsidian `计划蓝图.md`、Movement `结构.md`、`计划_移动与动作位移.md`：入口定位仍归 Movement，尚未列出新 helper。现有旧兜底表述、新 helper 的已编码但未接入状态及结构/流程图须在独立图文租约中同步。C32 明确冻结 Obsidian，本记录交回该缺口，不冒称笔记已全部同步。

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

## C37：生产求值消费与请求失败传播（原子预检）

日期：2026-10-02（北京时间）。统筹已接受有限预检并登记独占三文件租约，写前基线见 `Saved/ValidationRecords/MovementC37_LeaseBefore.json`。本段先于源码修改追加；此前 I/T1/R1/C35 的正文和实测历史保留。

| 项目 | 本步契约 |
| --- | --- |
| 唯一目标 | CMC 生产消费者调用冻结 P1 helper，候选成功后提交既有 Locomotion 状态；失败沿原执行号关闭自身 Locomotion，不继续时间、TurnBack 或 RMS 安装 |
| 精确文件 | `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h`、同目录 `.cpp`、本记录 |
| 唯一写入者 | Movement 长期组长直接执行；没有代理 |
| 职责与冻结依赖 | Profile 唯一读取/验证单资产；P1 唯一合成/缩放数学；CMC 唯一段选择、既有时钟、执行号及失败。只读 Evaluation、Profile、MovementInputTypes 和既有来源消费合同 |
| 独立性 | 不读写 ASC K4-P1、Input Controller D9 的文件或内部状态；不依赖候选 Cold/StartProof 字段 |
| 顺序 | 记录预检/基线 → 原执行归属地面门禁 → 两生产求值支替换及局部候选提交 → bool 失败向调用方传播 → GetMaxSpeed 显式模式分支 → 有限静态核对 → 追加实际证据后冻结 |
| 非目标 | 不改 Input/Hero/共享类型/资格/StartProof/MoveData、RMS、测试、资产、Obsidian；不重写 TurnBack 业务拓扑，不构建/UE/Git，不建立新求值器、跨帧候选、时钟、请求号或调度器 |
| 验收断言 | 双 Loop 任一侧失败（含 Alpha 端点未选侧）拒绝；合法零/极小正速/零 Scale 成功；失败不提交候选时间/相位/旧样本，不推进 TurnBack 或安装 RMS；只有原执行号可失败，执行号 0 不伪造 Failed、不从 Acceleration 补号；正常闲置不刷诊断，独立 GA Action/非地面保留；显式非曲线固定配置保留 |
| 失败与恢复 | 复用 FailLocomotionRequest 和自身源精确清理；原严格 neutral/Released 合同、Reset/同 held/重绑不得解锁；旧/重复/ABA 的身份门禁不改 |
| 停止点 | 仅三文件完成静态交回即停写；需要额外范围/未冻结共享接口则停止。源码未编译/未动态验证前不可记为通过或 Run 恢复 |

写前 SHA256：

- CMC.h：`043789EEAD09A5234AA1E73201D8B312D4108EA4062E8417A5FB94DF3502B861`。
- CMC.cpp：`32E1645402FC9CA00FE18EEC7E4E7F214FA5D40387EE86A103986C3BD598B92C`。
- 本记录：`BCC7F6B2D9324C70631914B88AA8615CBCA9233A1F78F83E9EA9894567BE1862`。
- Evaluation h/cpp：`B7E474D3703820EE112998C1DCC67BFB5A86D4A3C24AA816F2D36E2F55B2916A` / `E02CA4FAE7083E36687CAFF81ECB139F8C69F1CFC125D69CF632A8A5A2F556AF`。
- MovementInputTypes：`7C9C1B3FC6902BE2E99FE2FBC5B5EA5C185983772E4B1FF88C2E14C666D9AE61`；Curve RMS h/cpp：`DCA2DA64C9B7D06CF78711C2F3C62BA6CDDB4514FEC26543531B1CDE9BE4DBDB` / `1A244710AB744496673048F1A1EDADB37E00E9B450373BE1F376140921C5EBB9`。

候选只存在本次栈上，提交到现有字段后即销毁，不保有另一份权威时间或跨帧样本。首次 RMS Prepare/StartTime、实际模拟区间及完整返回提交、RMS 内部失败、网络/replay/proxy、来源生产接线和 Run 仍由后续精确步骤关闭。已有直接保护方法/注入样本夹具不证明来源执行资格，本步不改断言以维持表面通过。

### C37 实际实现与冻结交回

- CMC 已真实包含冻结 Evaluation 头。EvaluateLocomotionProfile 用 EvaluateSingleInterval；EvaluateWalkRunProfiles 用 EvaluateWalkRunInterval。原双侧 Lerp、任一单侧替代、直接忽略 EvaluateInterval 返回值及无条件时钟推进已移除，CMC 的直接资产 EvaluateInterval 调用为 0。单资产的非循环段要求 bLoop=false；WalkRun 双侧 Loop/端点依赖按 helper 冻结规则检查。
- 栈上 FLocomotionUpdateCandidate 只复制既有 gait/hold/意图/前帧事实、段/时间/相位/序列、Blend、TurnBack状态与原始样本。生产 Before 在同一个候选中 ResolveGait、选段、求值；成功才通过 CommitLocomotionCandidate 写回。失败不提交候选，因此失败帧的 WalkHoldTimer、Profile时间、CyclePhase、TurnBackElapsed、段序列及已消费Run意图均不提前改动。没有 Candidate 成员、跨帧缓存或另一份时钟。
- 现有保护方法包装沿同一候选机制，不建立另一求值/调度链。UpdateLocomotionMotion 的 bool 明确传播本次结果；TryUpdateLocomotion 同样检查来源失败及执行号0的真实地面门禁，不允许通过旧保护方法继续普通曲线执行。
- helper Error 原样传给 RejectLocomotionEvaluation；正执行号仅调用既有 FailLocomotionRequest。旧执行号失败不清后继；执行号0不调用 Fail、不赋 FAILED、不补造来源/执行号，只沿真实地面准入拒绝。原 Bind/Consume/Invalidate、严格 neutral/原Released合同、执行号递增1处及 Admitted赋值1处保持。
- Fail继续清空自身 CurveMotion、把精确自有Current/Pending Locomotion源输出置Identity并标记移除，清普通地面平面速度，不清GA Action。Before收到失败后返回，不运行随后CurveBrake、TurnBack RMS安装或提示校验；AdvanceTurnBackPhase仅在候选求值成功后调用。TurnBack入口、Yaw/方向/速度相位条件和原曲线没有重写，只把本次更新写入局部候选。
- authority/autonomous的曲线执行号0拒绝由GetMaxSpeed、Before、CalcVelocity、ApplyRootMotionToVelocity、PhysicsRotation及保护方法共同约束。去重诊断只在真实加速度/请求速度/平面速度、待执行段或自有RMS存在时发出，沿现有两种诊断状态避免重复；合法无输入闲置不刷日志。合法独立动画/注册Action源仍按既有资格豁免；Before在独立源存在时不推进Locomotion，非地面速度/物理继续交引擎。
- GetMaxSpeed只有显式 bUseCurveDrivenSpeed=false 才返回配置gait速度；曲线模式无成功来源返回0，不借固定速度业务替代。合法零、极小正速与零Scale仍由真实成功样本资格区别于失败，ForceWalk的显式速度上限保留。固定模式可不配置Profile，既有WalkRun不推进Profile时间、其它非循环段计时及正常配置速度保持。
- 未新增RPC/Tick/Timer、执行号、来源观察或具体角色业务，未修改 Input/Hero/类型/资格/StartProof/MoveData/RMS/测试/资产。全部文件修改只通过apply_patch完成。

#### 有限静态证据

- CMC.h：29658 bytes / 660行，SHA256 `DC651C5F9E9C292F8A8FEDA93443D90911DD4DDBFB089BD56FC5691CB8207374`。
- CMC.cpp：88140 bytes / 2320行，SHA256 `9D4A56DABFF315B01425D1313CABF5E49C23C67FCE807627F9915FCD4610AF72`。
- 两源码尾随空白0、冲突标记0；去除注释/字面量后的cpp大括号平衡0、最低深度0。声明/定义及所有调用点已读，不冒称通过UHT/C++编译。
- 原SavedMove/MoveData/Response定义的cpp开头（移除唯一新增Evaluation include后）、来源消费与原Fail主体、GA Action生命周期、配置绑定/Reset、RMS安装函数及response/replay整段与C37写前文本一致。这里只证明本次未改这些段，不证明其剩余缺口已关闭。
- Evaluation两源、MovementInputTypes及Curve RMS两源共5个只读保护文件，与C37预检hash逐一相同。
- 既有正文按时点保留；只更新本记录顶部当前状态、追加本C37。原顶部历史状态为：日期：2026-10-01（北京时间）。当前状态：P1-I已通过统筹第38次完整构建，新的运行时DLL中T1三叶纯数学专项Success（正常报告73 Success）；仍未接入生产消费者，Run未验。下文C32未编译/未授权等状态按原时点历史保留，当前编译与有限验收以末尾C35为准；本次两记录交回冻结。
- 只读核对Obsidian Movement结构与移动计划：结构第8行仍有缺Profile固定速度兜底，第28行仍列旧忽略失败/单侧替代缺口，未同步新helper/来源/候选及执行门禁。后续图文租约须更新职责/接口、流程Canvas、明确成功资格与失败清理，并保留RMS/replay/proxy/资产未验边界；本步遵守明确禁止范围，没有写Obsidian或其它记录。

#### 尚未验证与剩余边界

- 本次没有构建、UHT、UE、Git或运行/新增测试；Gate38三叶或Gate43普通77的历史成功不证明C37。
- 静态发现既有AuthorityAndMapping夹具用执行号0、直接保护方法/注入样本推进曲线并期待正GetMaxSpeed；新真实地面准入明确拒绝这些调用，因此存在已识别的既有回归前置冲突。本步不改、不排除、不降低原断言；如后续要验证正常曲线执行，须另租约让夹具通过已冻结的来源接口真实建立CMC请求，并保留原业务断言。未跑前不写成功。
- 尚无Hero/来源生产接线，也未消费候选Cold/StartProof。本地FAILED恢复仍是原身份Released→Neutral→新Started，不在C37提前实现冷启动；未绑定的曲线旧执行拒绝，不能声称生产Run已恢复。
- Curve RMS内部的SpeedScale/BaseYaw/方向替代、SimulationTime/MovementTickTime比例及Prepare失败、首次安装/StartTime、实际模拟区间与完整原生返回后的唯一提交仍开放。本步的栈上成功提交仍发生在Before，不等于已实现完整C36执行帧提交。
- SavedMove/MoveData/校正/replay/proxy不包含新请求/失败生命周期；失败后的表现复制、代理最终段和重放的来源边界未关闭。其它运行时配置的非法替代路径不因本步自动关闭。
- 七生产Profile、MovementSet/AnimBP/BlendSpace接线、动态/联机验收及Run仍开放。gadge/GAS占位和原TurnBack曲线未改。

**C37三文件停写冻结交回。仅完成本地生产求值消费和既有请求失败接线的源码/静态阶段；待统筹审查及统一构建，未获下一精确授权不得继续写入。**

## C37-T1：既有 AuthorityAndMapping 消费接口夹具适配（写前预检）

日期：2026-10-02（北京时间）。统筹已登记两文件独占租约，写前基线见 `Saved/ValidationRecords/MovementC37T1_LeaseBefore.json`；先追加本预检，再修改既有测试。唯一写入者为 Movement 长期组长，直接执行。

| 项目 | 本步契约 |
| --- | --- |
| 唯一目标 | 让既有 AuthorityAndMapping 正常曲线场景通过公开 Bind/Consume 建立 CMC 执行请求，保留全部原业务断言、数值和早退 |
| 精确文件 | `Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTest.cpp`、本记录 |
| 只读冻结依赖 | C37 CMC h/cpp、既有 TestTypes.h、D11 MovementInputTypes.h；不依赖未冻结的 Cold/Hero/生产接线 |
| 顺序 | 本预检 → cpp 内局部 RAII 消费协议夹具 → 首次/配置重绑后显式新请求 → 第二 CMC 独立来源 → 有限静态核对与证据 → 两文件冻结 |
| 协议 | 活的独立 UObject 为合成来源身份；公开 Bind → SessionOpened(Rearm) → NeutralConfirmed → RequestStarted(ReleasedThenPhysicalPress)；新请求前精确 RequestReleased，递增原来源事件/请求值；退出用原绑定公开 Invalidate 清理 |
| 责任边界 | 合成 Session/Request/Event 仅为测试调用数据；执行号只允许生产 Consume 发行。此夹具不证明 PlayerInput 物理输入、来源发行、Cold 或新 Mode/Proof 消费校验 |
| 非目标 | 不新增叶、不改 TestTypes/CMC/Input/共享类型/资产/全局文档/Obsidian，不写私有执行状态，不新增失败专项、ExpectedErrors、重试或排除场景；不构建/UE/Git/代理 |
| 验收断言 | 全部原断言逐语句保留；原 StartStop/RunStop/有限样本早退继续有效；重绑后先释放原请求、Neutral、新 Started，再恢复原场景设置；第二 CMC 独立来源；退出/早退释放来源绑定和强引用 |
| 停止点 | 仅两文件静态交回；若需要第三文件、共享语义或生产变更则停止。未新构建/运行前不写通过，也不称 Run 恢复 |

写前 SHA256：

- 测试 cpp：`59D81A4C651D43523394D9C0B58C87C82BAAF6C82282BD4BDFDC2676E5D1CDC3`（16888 bytes）。
- 本记录：`B64E1A272D645B0E59A6B8EB92C31A19EE5B48E53CC2AF117381FCA72A98ED01`（27472 bytes）。
- TestTypes.h：`78920CCD1FA1CE3D28321D7C6330235A4FC47B9768D83739F010CE706E1E09B5`。
- CMC h/cpp：`DC651C5F9E9C292F8A8FEDA93443D90911DD4DDBFB089BD56FC5691CB8207374` / `9D4A56DABFF315B01425D1313CABF5E49C23C67FCE807627F9915FCD4610AF72`。
- D11 MovementInputTypes.h：`913319EA218ABF67BCEE57E807201F17DC607185E85AC7EF6E6EDA44B7E35A9D`。只用已冻结字段的显式 Rearm/ReleasedThenPhysicalPress 值；不扩大 C37 的消费能力声明。

### Gate44 实测与本次适配根因

组长只读核对 `Saved/Logs/ModuleRepairBuildGate_20261002_44_UBT.log`、统筹 `Saved/ValidationRecords/ModuleRepairGate_20261002_44_Result.json` 的构建摘要及实际自动化报告。Editor构建为8 actions、Succeeded、30.82秒、exit0；这是C37生产代码的编译证据，尚不包含本次T1夹具改动。

实际报告 `Saved/AutomationReports/ModuleRepairGate_20261002_44/index.json`：SHA256 `6DAD22F6C931E984DC8D03ABA5749948E4C8823458F011DABD9EB77A4FB79E2E`，日期2026.10.02-02.04.11 UTC（北京时间10:04:11），77 Success / 1 Fail，warnings-success/notRun/inProcess均0。唯一红叶仍是 `GGYGO.Movement.Locomotion.AuthorityAndMapping`，其4条Error按原报告保留：

1. 真实生产拒绝：ExecutionRequest=0，未发行CMC执行请求。
2. 原“Stopping during WalkStart selects StartStop”值不等。
3. 原“Stopping from Run selects RunStop”值不等。
4. 原“RunStop produces a usable finite curve source sample”断言失败并早退。

根因是既有夹具未通过来源消费合同建立执行资格，却直接调用保护方法求值；C37现在拒绝这种执行号0的地面曲线调用。早退后原速度消费断言未执行，因此77成功不能作为该叶后半段证据。此次适配只补夹具前置，不放宽生产准入或原断言；真实来源发行、Hero/Cold和生产Run另有未验范围。

### C37-T1 实际改动与有限静态证据

- 只在既有cpp自动化条件内加入 `FLocomotionMovementConsumerFixture`。局部RAII对象持有独立UObject强引用、原公开绑定值及合成来源计数；无UCLASS、共享头、执行号注入、Tick/Timer或第二生产状态。两实例各对应一个CMC，互不借用绑定或来源对象。
- Bind使用当前公开BindingSerial，检查原Consumer/SourceSession身份与非零返回绑定；Opened显式Rearm，Started显式ReleasedThenPhysicalPress，其它Mode/Proof显式Invalid。每个Consume都要求Recorded且Error为空，不能把记录事实当作配置拒绝后的执行成功。
- 原StartStop场景前精确Released；原RunStop场景前新Neutral/Started再Released，并恢复原Run场景gait。配置重绑后先释放仍开的原请求，再Neutral/新Started，然后执行原样本/phase/gait/sequence设置，避免准入Reset清掉原场景前置。原叶共有9个显式StartFreshRequest调用，包含第二CMC首次准入与4次速度配置重绑。
- 成功末尾显式Close两个夹具；所有既有早退依赖RAII调用公开Invalidate原绑定，之后释放来源强引用。清理不伪造真实Released，不查询新绑定替换原身份；清理错误仍作为测试错误可见，没有ExpectedErrors、重试或静默成功。
- 本cpp修改后23005 bytes / 418行，SHA256 `813DD43C1A505A314FE9EBEF7175881BA3F5456F6D9C88B4643198E5C192CB28`。新增代码均通过apply_patch写入。
- 有限静态提取既有RunTest的64个TestTrue/TestFalse/TestEqual/TestNotNull调用，修改前后数量及完整调用文本逐项相同；原唯一叶路径和所有原数值/标签/早退保留。逆向移除本次helper/includes及11块新增场景前置/清理后，整个cpp与写前完整文本一致，证明没有修改其它原语句或历史注释。
- cpp尾随空白0、冲突标记0；去除注释/字面量后大括号平衡0、最低深度0。新增cpp中私有执行状态字段引用0、ExpectedErrors/InputKey/Tick/Timer等禁止入口0。此处仅有限静态核对，不冒称语法、链接或动态通过。
- TestTypes.h、CMC h/cpp、D11 MovementInputTypes.h共4份与写前hash完全一致；Evaluation h/cpp及Curve RMS h/cpp另4份与已冻结hash一致。未修改生产、共享定义、测试类型或第三份记录。
- 本记录只替换顶部当前状态并追加本C37-T1；C37-T1写前的整文状态行为：日期：2026-10-02（北京时间）。当前状态：C37生产消费者已编码、完成有限静态核对并交回冻结，尚未编译/运行；P1-I及T1三叶第38次构建/数学Success是此前有限证据，不能证明新消费者。来源生产接线、RMS/首次Prepare/实际模拟区间整体提交、网络/replay/proxy及Run仍开放。下文I/T1/R1/C35按原时点保留，最新状态以本C37为准。。剥除本T1新增段并恢复该顶部后须恢复写前完整hash，旧Gate44失败及I/T1/R1/C35/C37时点历史不改写。

### 冻结交回与未验范围

- 本次未构建、启动UE、运行测试、执行Git或创建代理。C37-T1已编码/完成静态交回，待统筹统一构建和原叶真实验收；Gate44的1 Fail仍为最新动态事实，未用适配源码冒称已转绿。
- 合成上游事实只验证CMC公开消费入口，既有TestTypes仍只提供业务场景设置；不证明PlayerInput真实物理发行，也不证明CMC已消费D11新Mode/Proof资格。失败专项、Cold/Hero生产接线、MoveData/replay/proxy均不在本次完成范围。
- 七Profile、MovementSet、AnimBP/WalkRun BlendSpace命名与接线、真实Run/联机尚未验收；gadge保持占位，既有TurnBack业务和曲线未改。
- 本次不改变模块职责、共享接口、生产状态归属或资产接线；Obsidian和全局进度入口按本租约冻结。C37已登记的Movement结构/流程Canvas旧描述同步缺口保留，不能标为图文全部完成。

**C37-T1两文件停写冻结交回。唯一结果是既有正常夹具的公开消费前置适配；保留原严格断言，待统一构建/动态验收。需要第三文件或生产语义变化须重新拆分授权，不自动继续后续步骤。**

## C37-T1-R1：合成身份标记具体类型修复（写前预检）

日期：2026-10-02（北京时间）。统筹Schedule10:43及 `Saved/ValidationRecords/MovementC37T1R1_LeaseBefore.json` 正式登记两文件租约；Movement长期组长直接执行，先记录本预检再改cpp。上一CMC模式消费只读预检按统筹暂停，有效结论保留，不转为实现。

| 项目 | 本步契约 |
| --- | --- |
| 唯一结果 | 纠正夹具直接实例化抽象UObject的错误，以具体transient UInputAction仅作合成协议身份标记 |
| 精确文件 | `Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTest.cpp`、本记录 |
| 先后 | 核对本地UE5.8 InputAction.h具体声明与既有EnhancedInput依赖 → 本预检 → 唯一必要include/构造表达式 → 有限逆向/原断言及保护核对 → 实测失败与未编译状态记录 → 冻结 |
| 非目标 | 不改原64断言、业务状态前置、Bind/Consume/Invalidate次序或其它helper正文；不新增测试类、来源发行/物理证明、生产/私有状态、ExpectedErrors或禁ensure；不写第三文件、不编译/UE/Git/代理 |
| 验收/停止点 | 删除唯一InputAction.h include并恢复原构造表达式，cpp必须准确恢复本租约写前整文；TStrongObjectPtr<UObject>保持，标记不作为真实Input Source。只两文件静态交回；新DLL复测前不称叶转绿 |

写前cpp：23005 bytes，SHA256 `813DD43C1A505A314FE9EBEF7175881BA3F5456F6D9C88B4643198E5C192CB28`。
写前本记录：35986 bytes，SHA256 `4D1C901F9A36A7938E503381D2EBEACCC1CFEEECB1EC5554C3D95799F1BB982A`。Gate45是这两基线时点的编译/运行证据，R1纠正尚未进入新的构建。

### Gate45 实测失败、类型依据与实际纠正

- 只读核对统筹 `Saved/ValidationRecords/ModuleRepairGate_20261002_45_Result.json` 的构建摘要和实际报告 `Saved/AutomationReports/ModuleRepairGate_20261002_45/index.json`：Editor为Succeeded、7 actions、16.36秒、exit0。报告日期2026.10.02-02.41.10 UTC（北京时间10:41:10），78 Success / 1 Fail、notRun/inProcess/succeededWithWarnings均0，总时长2.7550766468048096秒；报告SHA256 `F43CE7DE5FC4E860C60B2341208B86427FE5351CC206699B8C78F631311F71E4`。
- 唯一 `GGYGO.Movement.Locomotion.AuthorityAndMapping` 为Fail，27 Error / 3 Warning，时长1.982561469078064秒。实际条目保留LogUObjectGlobals抽象类实例化警告、LogOutputDevice Script Stack及Handled ensure。这是本夹具错误使用 `NewObject<UObject>` 的真实运行失败，不是放宽CMC生产准入或原业务断言的理由。统筹另确认Source256/9保护保持、UE已退出及全日志104 Error/8 Warning；此全树/全日志证据归统筹窗口，不称本组长本次自算。
- 已核对本机 `F:/UE_5.8/Engine/Plugins/EnhancedInput/Source/EnhancedInput/Public/InputAction.h` 第54～55行：`UCLASS(MinimalAPI, BlueprintType)` 的具体 `UInputAction : public UDataAsset`，无Abstract声明。现有 `Source/GGYGO/GGYGO.Build.cs` 第17行已包含EnhancedInput依赖；不需第三文件或模块依赖改动。
- cpp仅新增条件编译内 `#include "InputAction.h"`，构造表达式改为 `Source(NewObject<UInputAction>(InMovement, NAME_None, RF_Transient))`。具体对象只作synthetic协议身份标记，既有 `TStrongObjectPtr<UObject>` 持有/清理不变，不执行Action业务，也不冒称真实PlayerInput来源或物理发行。
- 实际cpp为23060 bytes / 419行，SHA256 `32BAACC1D5185CFA060EAE3980DF16C14DEE3DC2078CB253059A655F8DCA34D7`。内存删除唯一include、把唯一构造表达式恢复旧值后，全文及UTF-8 hash准确恢复写前 `813DD43C1A505A314FE9EBEF7175881BA3F5456F6D9C88B4643198E5C192CB28`。原RunTest全文、全部64原断言、场景前置、所有Bind/Consume/Invalidate调用及helper其它正文准确保持；尾随空白/冲突标记0。没有ExpectedErrors、禁ensure或私有状态修改。
- 本记录仅更新顶部与追加本R1，R1写前顶部历史状态为：日期：2026-10-02（北京时间）。当前状态：C37生产消费者已通过统筹Gate44 Editor构建；报告为77 Success / 1 Fail，唯一AuthorityAndMapping红叶有4条错误。C37-T1现已适配该旧夹具的公开来源消费前置，保留全部64个原业务断言，尚未新编译/运行，交回冻结。来源生产接线、RMS/首次Prepare/实际模拟区间整体提交、网络/replay/proxy、七Profile/AnimBP/BlendSpace及Run仍开放。下文I/T1/R1/C35/C37保留各原时点状态，最新有限证据以末尾C37-T1为准。。旧C37/T1及Gate44、Gate45失败均保留；剥除R1追加、恢复该行后核对原整文hash。
- CMC模式有限只读预检保留有效结论：当前CMC读取新增Mode/Proof为0处，旧事实比较未含新字段，旧请求级Duplicate需在未来精确租约核对；可限定CMC h/cpp与本P1记录三文件的候选范围。该预检按统筹暂停，窗口/去重方案未实施，不从本R1取得生产写权。

### R1 冻结交回与剩余边界

本次只有两文件apply_patch，没有构建、UE、测试运行、Git或代理。Gate45编译的是R1纠正之前的夹具；当前27 Error / 3 Warning失败仍为最新动态事实。必须由统筹新DLL复测原叶和普通全量，未运行前不能记转绿、物理Input可用或Run已恢复。

生产CMC/Input/共享类型、TestTypes、Profile/Evaluation/RMS、资产及图文保持冻结。gadge占位、TurnBack/原曲线不变；生产来源、Cold/模式消费、Hero/MoveData、RMS/网络和七Profile/AnimBP/BlendSpace仍各有后续边界。Obsidian及全局进度按租约保持，原C37图文同步缺口保留。

**C37-T1-R1两文件修复已编码、完成最小逆向静态核对并停写冻结交回；待统筹新构建/运行，不自动恢复CMC模式预检或其它迁移。**

## C38 / D11ModeConsumer：显式模式与开始证明消费（写前原子预检）

日期：2026-10-02（北京时间）。统筹Schedule11:06及 `Saved/ValidationRecords/MovementC38_LeaseBefore.json` 已登记三文件独占租约，Movement长期组长直接执行。本段先于h/cpp修改追加；与ASC C1a互斥，不消费其新API。

| 项目 | 本步契约 |
| --- | --- |
| 唯一结果 | CMC严格消费D11完整事实布局，保留原模式值及一次Cold窗口消费阶段，严格Rearm沿既有唯一执行号准入 |
| 精确文件 | `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h`、同目录 `.cpp`、本记录 |
| 只读依赖 | 冻结D11共享头/Contract，C36原绑定/来源/失败生命周期、C37生产求值，现有已显式填写Rearm/ReleasedThenPhysicalPress的consumer夹具 |
| 顺序 | 本预检 → 默认Invalid/false的最小消费派生字段 → 布局/完整payload/去重 → Cold及Rearm准入/关闭 → 原清理边界 → 有限静态/真实旧结果记录 → 三文件冻结 |
| 验收 | Opened仅Cold/Rearm且Proof Invalid，Started仅合法Proof且Mode Invalid，其它Kind两字段Invalid；同event含新字段完全相等才Duplicate、任何篡改Rejected；旧请求新event不得沿请求级Duplicate或更新水位冒成功 |
| 窗口与失败 | 仅显式合法Cold Opened开本会话一次窗口；重复Opened/Reset/失败不重开。首个合格新Started在HasAcceptedMovementSet前关闭，SourceUnresolved及精确失效关闭；Cold不解锁FAILED，ReleasedThenPhysicalPress在Cold/Rearm中均需原Neutral且无open |
| 清理与权威 | Bind/Invalidate清窗口不清FAILED；Unresolved保留原open请求到精确Released，不造释放/Neutral/执行号。仅保存消费阶段，不Claim/Consume资格、不观察键、不发Source号 |
| 非目标 | 共享Types/Source/Origin/Hero/GA/Action/RMS/TurnBack/SavedMove/MoveData/fixture/资产/Obsidian/全局及其它记录；不构建/UE/Git/代理，不引入第二来源状态、发号器、时钟、兜底或第二Start历史 |
| 停止点 | 三文件静态交回即冻结；需第四文件、新接口语义、来源状态归属或其它生命周期改动则停。Source字段发行、Hero/MoveData和Cold生产专项未接，不能称首次W/Run或网络通过 |

写前SHA256：

- CMC.h：`DC651C5F9E9C292F8A8FEDA93443D90911DD4DDBFB089BD56FC5691CB8207374`。
- CMC.cpp：`9D4A56DABFF315B01425D1313CABF5E49C23C67FCE807627F9915FCD4610AF72`。
- 本记录：`4FE8DD4BF890A45715E3E7257B2DA3A331CE14927EB8F8E09812C262C488F191`。
- D11头：`913319EA218ABF67BCEE57E807201F17DC607185E85AC7EF6E6EDA44B7E35A9D`；既有fixture：`32BAACC1D5185CFA060EAE3980DF16C14DEE3DC2078CB253059A655F8DCA34D7`。

Gate46及C37图文同步作为此前有限结果追加记录，保留C37/T1/R1各原时点历史；本C38未编译/运行前不标通过。

### Gate46 真实有限结果与图文状态

组长只读核对实际 `Saved/AutomationReports/ModuleRepairGate_20261002_46/index.json`，并引用统筹 `Saved/ValidationRecords/ModuleRepairGate_20261002_46_Result.json` / Schedule的构建及保护结果：

- Gate46 UBT Succeeded、4 actions、11.84秒；构建完成响应未返回shell exit字段，不补称exit0。这是C37/T1/R1和D11共享值的此前构建，不包含C38源码。
- 报告时间2026.10.02-02.55.33 UTC（北京时间10:55:33），79 Success；failed/succeededWithWarnings/notRun/inProcess均0，总0.782038152217865秒。报告SHA256 `D03A8B6E9F491ADC0492739C1BC9E15BCC2515424495497DF2137D09E9FB4D05`。
- 原 `GGYGO.Movement.Locomotion.AuthorityAndMapping` 实际Success、0 Error/0 Warning、entries空、0.008634399622678757秒。原业务断言保持，新具体UInputAction夹具已进入DLL并复测；Gate44的4错、Gate45的27错/3警告历史保留，没有删除失败或加ExpectedErrors。
- 统筹窗口确认原79路径、全部叶零诊断、Source256/9保护保持、UE exit0退出；全日志49 Error/2 Warning仍保留。此全树/进程/全日志证据归统筹，不称本组长本次自算，也不把叶零诊断说成全日志零诊断。
- 统筹已完成C37对应Markdown/Canvas同步及有限静态核对，未验原生UI。组长再次只读核对Obsidian Movement `结构.md`：第8行已删除缺Profile固定速度业务回落，第28行已记录C37生产求值及Gate44～46历史，第34/36/39/40行已列来源消费、Evaluation、原请求失败和速度消费职责。此前C37图文缺口已更新，旧批次“未同步”保留为其历史时点。
- 该结构第42行仍为C38之前的Neutral→Started消费阶段；本次新增Mode/Proof/Cold窗口的已编码未编译状态及流程仍待独立图文租约，不能冒称C38图文或原生UI已验收。本租约没有写Obsidian/Canvas/全局入口。

### C38 实际实现与有限静态证据

- h仅增加默认Invalid的 `ConsumedMovementInputSessionMode` 和默认false的 `bMovementInputColdStartWindowOpen`，作为原事实消费阶段；没有Input资格、设备来源、第二Start历史、请求发号或跨帧时钟。
- Consume只接受精确Kind/Mode/Proof搭配：Opened必须Cold/Rearm且Proof Invalid；Started必须有效Proof且Mode Invalid；其它Kind两字段都Invalid。显式枚举比较同时拒绝缺值及范围外值；拒绝错误包含原身份、Event、Kind、Mode、Proof，不选默认模式或业务替代。
- LastFact完整比较包含Mode及Proof；精确same-event replay在窗口/Neutral等状态判断前返回Duplicate，不再执行或重开窗口。原退休绑定的精确Invalidated同样幂等；原绑定同event篡改返回Rejected，其它旧绑定Stale，不清后继。
- 新event中旧Started RequestSerial、错误/重复Released及错误Unresolved请求均明确Stale，不走旧请求级Duplicate，不写LastFact水位。没有另存Start历史；真正新请求仍由原单调门禁准入。
- 仅有效Opened把原模式保存并打开Cold窗口；已有FAILED时Cold窗口仍关闭，Opened不清失败。同绑定重复Opened拒绝，同会话幂等Bind不重置阶段；新Bind/精确Invalidate清Mode/窗口，但不清FAILED。
- ColdPhysicalPress必须原Mode Cold、未耗尽窗口、没有已消费输入请求、无open请求且非FAILED；不要求伪造Neutral。ReleasedThenPhysicalPress在原Cold或Rearm会话均要求已消费Neutral且无open。首个合格新Started在执行号检查/发行和HasAcceptedMovementSet之前关闭窗口；之后配置失败不能再试Cold，只能按原释放/Neutral/新真实请求恢复。
- Revoke及原精确Fail路径关闭窗口；Fail的原执行号/非空原因检查仍先行，旧失败不清后继。有效SourceUnresolved复用Revoke，关闭窗口、撤销执行而保留原open输入请求，等待精确Released；未发行时不伪造FAILED/释放/Neutral/输入或执行号。原CancelOwned源精确清理主体保持。
- ResetLocomotionState、配置/ASC Reset均不碰新模式/窗口；Released/Neutral不清FAILED。既有执行号递增及Admitted赋值各仍只有1处，只有合格新Started准入。没有Claim/Consume Input资源、InputKey/键查询、C1a API或设备观察。
- CMC.h：29911 bytes / 663行，SHA256 `149005B8E39FC98B637327571861EE6632495828D18F22822A4B74F497568577`；cpp：90515 bytes / 2357行，SHA256 `9CF9ABBEA1A202D4F07B47FB1F1DFBB3FD2B496E2B9770304B246A09E669EFD4`。
- Header内存剥除唯一新增字段块后，整文准确恢复C38写前文本；cpp Bind之前和IsMovementInputRequestBlocked之后整段与写前完全一致，原CancelMovementInputLocomotion主体也完全一致。公开签名、SavedMove/MoveData/response/replay、Action/RMS/TurnBack、原生消费/运动求值及其它方法均不改。没有新循环依赖、第二执行器、内部状态外泄或额外资源。
- 两源码尾随空白/冲突标记0，去注释/字面量后大括号平衡0、最低深度0；Cold窗口唯一可打开表达式在合法Opened分支，其余五处赋false。静态核对完整payload、去重先行、关闭早于配置、旧请求不改水位、Unknown不假释放及Reset不重开。仅有限静态证据，不冒称C++编译或Cold动态专项通过。
- D11头、既有fixture/TestTypes、Evaluation h/cpp、Curve RMS h/cpp共7份保护与写前冻结hash一致；未写共享头、Source、测试或其它记录。h/cpp/本记录全部修改仅用apply_patch。
- 本记录只更新顶部当前状态并追加C38。C38写前顶部历史状态为：日期：2026-10-02（北京时间）。当前状态：C37及C37-T1已进入统筹Gate45 Editor构建（Succeeded，7 actions，16.36秒，exit0）；普通78 Success / 1 Fail，唯一AuthorityAndMapping因夹具实例化抽象UObject产生27 Error / 3 Warning。C37-T1-R1现已把合成身份标记改为具体transient UInputAction，仅必要include/构造表达式变化，全部原64断言和消费次序保持；R1尚未新编译/运行，交回冻结。CMC模式消费预检暂停，生产来源、RMS/首次Prepare/实际模拟区间整体提交、网络/replay/proxy、七Profile/AnimBP/BlendSpace及Run仍开放。下文按各原时点保留，最新有限证据以末尾C37-T1-R1为准。。剥除本C38新增段并恢复该行后须恢复写前整文hash，旧各批正文及真实失败不抹掉。

### C38 冻结交回、迁移顺序与未验范围

C38只完成CMC消费接缝的源码/静态阶段，未构建/UHT/UE/测试/Git/代理。当前Gate46 79 Success不证明新窗口、篡改、FAILED恢复或Cold专项；待所有生产作者冻结后由统筹统一构建及精确动态验证。

D11共享值已冻结/编译 → Source字段发行/原资源资格与CMC消费分别独占适配冻结 → 必要旧Invalid consumer夹具另两文件租约适配并统一验证 → Hero原资源绑定/转交 → MoveData/校正/replay后续。当前唯一consumer夹具已显式填写Rearm/ReleasedThenPhysicalPress，故本步不改；其它旧缺值不能用生产默认兼容掩盖。

Source尚未发行新字段或接资格消费，CMC将拒绝其缺值事实；Hero生产、跨Producer恢复、MoveData/代理、首次真实W及生产Run仍未接。RMS内部/首帧/实际模拟区间整体提交、七生产Profile/MovementSet/AnimBP/BlendSpace、联机和C38图文另步。gadge保持占位，既有TurnBack业务/曲线没有重写。

**C38三文件已编码、有限静态核对后停写冻结交回；未新编译/运行，不自动写Source、测试、图文或其它生命周期。需扩大范围立即重新拆分交回。**

## C38-T1：Cold/Rearm consumer 单叶（写前原子预检）

日期：2026-10-02（北京时间）。统筹Schedule11:44及 `Saved/ValidationRecords/MovementC38T1_LeaseBefore.json` 已登记两文件独占写权；Movement长期组长直接执行，先追加本预检/Gate47，再追加唯一新叶。与Input D12-A、ASC C1a-T1互斥，不消费其新实现。

| 项目 | 本步契约 |
| --- | --- |
| 唯一结果 | 新增 `GGYGO.Movement.Locomotion.InputConsumer.ColdAndRearm` 一个公开consumer协议叶，验证显式Cold/Proof、重放/单调性、耗尽及未发行Unresolved恢复 |
| 精确文件 | `Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTest.cpp`、本既有P1记录 |
| 只读依赖/前置 | 冻结C38 CMC h/cpp、D11共享值；现有真实World/Character/CMC、MakeProfile及七健康Profile；具体transient UInputAction仅作强持有合成身份标记，不证明Source物理发行 |
| 顺序 | 本预检/Gate47 → 原cpp末尾仅追加新叶 → 各消费者独立原绑定RAII → 明确Cold与Unresolved两段事实 → 真实Before样本/段/gait/只读时间观察 → 有限逆向/保护/两hash → 冻结 |
| 唯一断言范围 | Cold无Neutral首Start；缺/错Mode/Proof拒绝；同event合法Mode/Proof改值拒绝、精确Duplicate保留真实求值状态；旧Request新Event100 Stale、原event仍Duplicate、更低eventReleased Recorded；Released→Neutral后Cold再次拒绝、同原Cold会话Rearm合法；第二CMC未发行Unresolved关Cold，无Neutral Rearm拒绝、未发行Release Stale，明确Neutral后Rearm健康 |
| 清理责任 | 每消费者保原Binding及强来源；所有早退/成功都精确Invalidate后释放来源，World最后销毁；不假物理Released |
| 非目标 | 不改旧helper/旧叶/原64断言及顺序、TestTypes/生产/共享/Source/Origin/GA/资产/图文/全局，不新UCLASS或测试角色，不读/写私有执行/FAILED/窗口/水位，不ExpectedErrors、不构建/UE/Git/代理 |
| 停止点 | 删除唯一新增叶必须恢复原整cpp；只有两文件有限静态交回。需第三文件、生产探针或真实FAILED日志/其它生命周期则停止另拆；不称物理Source、首次W/Run或网络通过 |

写前：cpp 23060 bytes，SHA256 `32BAACC1D5185CFA060EAE3980DF16C14DEE3DC2078CB253059A655F8DCA34D7`；本记录52533 bytes，SHA256 `F94E24FA3DC148E1DEDCEB3C561B1C851509239B5C5F46698DF851191DC7575E`。生产C38 h/cpp冻结为 `149005B8E39FC98B637327571861EE6632495828D18F22822A4B74F497568577` / `9CF9ABBEA1A202D4F07B47FB1F1DFBB3FD2B496E2B9770304B246A09E669EFD4`。

### Gate47 已有真实结果（不覆盖本新叶）

- 统筹Gate47 Editor Succeeded、8 actions、18.04秒、exit0，已编译C38消费生产代码；不是本T1新叶构建。
- 实际 `Saved/AutomationReports/ModuleRepairGate_20261002_47/index.json` 时间2026.10.02-03.28.12 UTC（北京时间11:28:12），79 Success、其它状态全部0，总0.7823355793952942秒，报告SHA256 `9C9BEEC7DE0C90D0049A41C81FB6101BD72F0B5ED8418B0B83C9F633ED3366F0`。
- 原AuthorityAndMapping实际Success、0 Error/0 Warning、entries空、0.008976701647043228秒；原Rearm夹具及ASC六叶保持。统筹另确认全部叶零诊断、256源/9保护构建运行后保持、UE exit0退出，完整日志49 Error/2 Warning保留。该全树/进程/全日志证据归统筹，不称本组长当前自算。
- C38生产已编译及普通Rearm回归通过；Cold、篡改、旧请求水位与未发行Unresolved新专项仍未运行。旧各批失败/未验历史保留，本新叶只证明consumer合成协议，不证明物理Input、Run、FAILED真实日志生命周期或网络。

### C38-T1 实际追加与有限静态证据

- 只在原cpp末尾、既有WITH_DEV_AUTOMATION_TESTS范围内追加 `FGGYGOLocomotionInputConsumerModeTest` / `GGYGO.Movement.Locomotion.InputConsumer.ColdAndRearm` 一个叶。原includes、共享MakeProfile/线性曲线工具、FLocomotionMovementConsumerFixture、原AuthorityAndMapping全文与全部64业务断言/标签/数值/顺序逐字符保持；没有新测试角色/UCLASS、TestTypes或第三文件。
- 新叶建立真实UWorld、两份既有Character及实际CMC，配置不可变的七健康Profile；WalkStart/WalkLoop为真实常量64，RunLoop为128，停止/TurnBack为合法非循环曲线，Scale=1、Hold=2秒。两个具体transient UInputAction强引用仅作合成协议身份，CMC执行请求只经公开Consume发行。
- 首段：缺Mode的Opened、错Proof的Opened、缺Proof/错Mode的Started以及Neutral携带Proof均明确Rejected；合法Cold Opened与首个Cold Started之间没有Neutral事实，仍Recorded/清错误。Opened同event改成合法Rearm及Started同event改成合法ReleasedThenPhysicalPress均Rejected。
- 首次合法Start后仅用既有公开数值加速度前置和生产 `UpdateCharacterStateBeforeMovement(0.016f)` 求值，确认真实样本Speed=64、gait Walk、WalkStart段与正时间；不注入样本/gait/动作段/序列。精确Started replay为Duplicate且样本、段、gait、只读时间保持，观察未重启执行；不添加私有执行号getter或修改其状态。
- 旧Request1带Event100必须Stale且有诊断；原Event6仍Duplicate，随后Event7的精确Released能Recorded，直接检查旧请求没有污染消费者水位。显式Released→Neutral之后新Request2的Cold证明拒绝，原Cold会话内ReleasedThenPhysicalPress的新Request2合法，并再次由生产Before产生健康样本。
- 第二独立消费者：Cold Opened后Request0的SourceUnresolved为Recorded且必须保留明确SourceReason；没有把Recorded称为执行成功。之后Cold拒绝、无Neutral的Rearm拒绝、未发行Request1的Released为Stale；显式Neutral之后首个Request1的Rearm合法，第三次真实Before产生健康样本。
- 第二段没有FAILED/执行号注入，也没有期待执行失败日志。未发行Unresolved的公开观察范围是关Cold、不补Neutral/来源请求及可Rearm恢复；真正FAILED的配置错误/日志与恢复另步，不能用此叶冒称私有FAILED数值或全失败链已动态验证。
- 每消费者局部RAII仅保原Binding、弱消费者与强SourceMarker。所有普通早退及成功退出先公开Invalidate精确原Binding，清理错误作为真实测试错误保留，再释放强来源；两资源均先于WorldCleanup析构。没有假物理Released、Source资格、held缓存或第二执行器；无ExpectedErrors、禁ensure或错误吞掉。
- 新cpp 37001 bytes / 644行，SHA256 `676BE1EE3FFA718EB5DD7808EB4145AEBA386E2F63A6CBC7B2EE545EA2CADA2F`。内存删除唯一新增叶/RunTest块后整文准确恢复写前 `32BAACC1D5185CFA060EAE3980DF16C14DEE3DC2078CB253059A655F8DCA34D7`；唯一新增叶计数1、总声明2，旧完整cpp的准确逆向同时覆盖所有旧helper和64断言。
- 新叶有2个具体身份标记、0个抽象UObject实例化、3处真实Before健康求值调用；公开Invalidate集中在单一RAII清理点，作用于两份独立原资源。禁止的私有请求/FAILED/窗口/水位、样本/gait/段/序列注入、ExpectedErrors、InputKey/Claim等入口为0。去注释/字面量后大括号平衡0、最低深度0；cpp尾随空白/冲突标记0。这些是有限静态，不证明编译或运行。
- C38 CMC h/cpp、D11头、TestTypes、Evaluation h/cpp、Curve RMS h/cpp共8份保护hash与冻结基线一致。本批只两文件apply_patch；Input D12-A/ASC C1a-T1合法平行范围不纳入本组长全树保护声称。
- 本记录只更新顶部并追加C38-T1。写前顶部历史状态为：日期：2026-10-02（北京时间）。当前状态：C38已编码D11 Mode/Proof字段合法性、完整事件去重、一次Cold消费窗口及严格Rearm，三文件完成有限静态核对后交回冻结，尚未新编译/运行。此前Gate46已用新DLL确认原AuthorityAndMapping Success/0诊断，普通79 Success/其它0；该结果不证明本次新消费契约。C37图文已由统筹同步Markdown/Canvas有限静态（非原生UI），C38新增消费阶段仍待独立图文同步。Source新字段发行、Hero/MoveData、RMS/首帧/实际模拟区间提交、网络、七Profile/AnimBP/BlendSpace及首次W/Run仍开放。下文各批状态按原时点保留，最新有限状态以末尾C38为准。。剥除本T1新增段并恢复该行后核对原整文hash；旧各批真实失败、阶段状态、Gate47有限成功保持。

### 冻结交回及未验边界

本新叶已编码并完成有限静态交回，未构建/UHT/启动UE/运行测试/Git/代理；当前最新动态仍为Gate47原79 Success，不包含本新叶，也不预填新的总叶数或成功结果。待三个生产/测试作者明确冻结后由统筹统一构建。

本步只增加consumer合成协议验收，不改变生产职责、接口或资产接线。没有Claim/Consume Input资格或真实设备发行；Source完整字段/物理来源、Hero、跨Producer交接、MoveData/replay/proxy、RMS、正式七资产/AnimBP/BlendSpace、首次W/Run和网络不因本叶关闭。gadge仍占位、原TurnBack业务及曲线不变。

Obsidian/全局入口按租约冻结；C37图文已同步的历史和C38模式消费图文待独立租约状态保持，不冒称原生UI已验或另写笔记。真正FAILED及生产错误日志另做精确预检，不在此叶植入私有失败。

**C38-T1两文件已完成唯一新叶及有限静态核对，停写冻结交回；待统筹新DLL/真实报告验收，不自动追加矩阵、改旧断言、生产、Source、图文或其它生命周期。**

## C38-T2：真实 FAILED 恢复专项原子预检（2026-10-02）

### 授权、范围与依赖

统筹已接受既有只读预检，并登记 Schedule/Ledger 与 `Saved/ValidationRecords/MovementC38T2_LeaseBefore.json`；不重做方案研究。Movement长期组长直接执行，唯一目标为**真实已发行CMC请求求值失败后锁存、拒绝暗重试，仅精确Released→Neutral→有效新请求恢复**。基线测试cpp `676BE1EE3FFA718EB5DD7808EB4145AEBA386E2F63A6CBC7B2EE545EA2CADA2F`（37001 bytes），本记录 `38571605F23ED45CC5401925E584EA86B167AD3B9A6DEC2C952273EAD8CA538A`（62055 bytes）。

仅写两个既有文件：

- `Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTest.cpp`：追加一个 `GGYGO.Movement.Locomotion.InputConsumer.FailedRequestRecovery` 叶；旧完整helper、AuthorityAndMapping、ColdAndRearm与所有断言逐字保持。
- `AAADocs/Modules/Movement/Module_Repair_10_P1_LocomotionEvaluation.md`：先登记本预检，再记录有限静态交回及未验边界；不新建摘要。

只读依赖：已冻结CMC/C37求值候选/C38 D11 consumer、共享输入类型、Evaluation/Profile、现有TestTypes与MakeProfile；不读取或适配Input D12-B/ASC Cue新业务。状态权威仍为Input发行输入事实、CMC独占执行号/FAILED/候选提交、Profile只读曲线求值、Animation负责姿态。局部合成来源仅提供原Producer/Session/输入请求事实，数字加速度只表示移动意图，不产生执行请求、资格或第二套状态权威。

顺序为已冻结生产接口 → 本记录预检 → 单叶追加 → 原整cpp逆向及只读保护核对 → 两文件冻结 → 统筹统一构建/真实报告 → 统筹图文和全局状态同步；与ASC Cue T1文件/状态互斥。Input B已冻结，本叶无其新API依赖。

### 唯一叶与六步验收

1. 真实World/Character/既有派生CMC，预构建不可变HealthySet七Profile和BadSet（六个健康Profile共享，WalkStart独立）。公开SetMovementSet健康配置、Bind原来源、Cold Opened/Started输入请求1；真实Before取得64速度健康样本。
2. 坏WalkStart在任何绑定前用Speed键(0,1)/(1,1)、Cubic/User/WeightedNone、切线-8/+8构造；原生键/切线、ValidateProfile/配置与Eval(.1)>0、Eval(.2)<0均断言。公开切换BadSet保留已发行请求1，Before(.1)成功，再Before(.1)沿SingleInterval/SpeedCurve真实失败。清空整个样本、曲线资格/GetMaxSpeed拒绝；失败候选时间/序列/姿态不得提交，不把正常Reset归零当失败。
3. 公开修HealthySet（该入口真实执行ResetLocomotionState），同held、原Started精确重放、零加速度→恢复前向、重复配置Reset、同Session Bind仍不可重试。配置清理时间0合法，后续Before不得推进该新基线。禁止直接调用私有Reset/FAILED/执行号或新测试hook。
4. 原Binding精确Released请求1→Neutral本身仍锁存；BadSet配置下ReleasedThenPhysicalPress有效请求2再次准入，Before(.1)成功/下一Before(.1)再次真实失败。有效新请求遇到坏配置仍失败。
5. 修HealthySet后请求2仍锁存，同held不恢复；Released请求2与Neutral也不能自行执行。
6. 仅原Session有效ReleasedThenPhysicalPress请求3，通过真实Before恢复64健康样本/资格/速度。全部断言与原Binding清理成功后才输出唯一完成标记。

原Binding局部RAII先公开Invalidate、后释放强来源，World最后销毁；早退也清理。唯一生产Error两条必须保持原Severity、Consumer/Owner/Producer/Session/BadSet/Profile、InputRequest=1/2、ExecutionRequest=1/2与SingleInterval/SpeedCurve负插值原因。执行号仅由生产++分配，测试不读取/注入私有值；诊断由统筹从原始报告/日志核对。

### 真实红报告与停止点

普通Automation捕获Error的证据为Gate44原始runtime日志4492及对应叶继续运行后的4条Error；该历史为零执行号准入诊断，**不冒称本次真实FAILED已动态验证**。本叶不注册ExpectedErrors、不catch、不改日志、不过滤或排除失败场景。预期框架结果**Fail**、两个原始生产Error、零断言Error/额外诊断/Warning，以及全部阶段完成后的唯一标记；独立记录“严格诊断匹配”，不得把框架Fail改Success/普通全绿。全量GGYGO保留此红叶。

本批只做编码/有限静态/冻结，不构建、UE、Git、代理、其它测试、共享头、生产、物理输入、RMS、跨Session/Producer、网络、资产或Obsidian/全局入口写入。第三文件、生产或新生命周期契约需求立即停止并交证据；当前两文件计划能够表达完整专项。Gate48普通81 Success只验此前范围，不能证明本批、首次W/Run、联机或正式AnimBP/BlendSpace接线。

### C38-T2 已编码内容与有限静态交回

本批唯一新类/叶为 `FGGYGOLocomotionFailedRequestRecoveryTest` / `GGYGO.Movement.Locomotion.InputConsumer.FailedRequestRecovery`。真实World、既有派生Character/CMC、具体Transient UInputAction合成来源；不增加TestTypes、include或全局helper。两个不可变配置在首次绑定前完整构造，BadSet共享六个健康Profile，只独占命名的 `FailedRecoveryBadWalkStart`。坏键1/1、原生Cubic/User切线-8/+8保留、Eval(.1)=.28 / Eval(.2)=-.28及静态验证通过均先断言；所有绑定之后没有曲线写入。

六步按原方案完整编码：请求1真实健康Before → 切BadSet同请求两次.1真实失败 → 同held/修配置Reset/原Started Duplicate/零加速度及恢复/重复Reset/sameSession Bind不能再执行 → 精确Released1/Neutral单独不恢复、坏请求2两次.1再次失败 → 修配置及Released2/Neutral仍锁存 → 健康新请求3真实Before恢复64速度及资格。两个真实失败点均核对整个CurveSample默认清空、IsCurveDrivingSpeed=false/GetMaxSpeed=0，并核对候选失败时间、序列、motion、gait未提交；公开SetMovementSet合法Reset后时间0另设基线，随后blocked Before不得推进它。

新叶只使用公开Bind/Consume/SetMovementSet/Invalidate/Before、既有数字加速度setter及只读getter。没有私有FAILED/执行序号/输入窗口/水位赋值、样本/动作/gait注入、ExpectedErrors/catch/日志过滤。来源请求1/2/3与事件1～8为合成上游数据，实际执行序号仅由已冻结CMC分配。两次失败发出的原始Error必须交由统筹核对，源码/静态检查不能替代动态证据。

RAII保存原Binding/Weak CMC/Strong来源；显式Close成功后再输出标记，析构幂等，原公开Invalidate先于来源Reset，World对象更早构造故最后销毁。所有业务断言失败直接早退且清理；不因已经记录两条生产Error而中止其余业务断言。RunTest最终return true仅表示执行到末尾，框架仍须保留真实Error产生的**Fail**。

有限静态结果：

- 从当前测试整cpp剥除本批唯一完整新增块可逐字恢复原整cpp及 `676BE1EE3FFA718EB5DD7808EB4145AEBA386E2F63A6CBC7B2EE545EA2CADA2F`；旧helper/两叶/所有断言/早退/顺序/宏边界保持。总3叶，新叶1处。
- 本批新增块303行；34个断言调用点通过各阶段复用，实际执行次数不冒作测试数量；2处真实失败阶段调用、2处健康Before阶段调用、3个Started/2个Released/2个Neutral、2处public Bind。唯一完成标记1处，位于全部断言及成功Close之后。
- 花括号余额0/最低0，尾随空白0、冲突标记0；禁用私有状态/setter/ExpectedErrors/catch命中0。
- 九项只读保护：CMC h/cpp、D11类型、TestTypes、Evaluation h/cpp、CurveRMS h/cpp、既有MovementInput Consume记录均与本批写前hash相同。生产源码、接口、旧测试和曲线执行业务未改。
- 本记录只更新顶部并追加C38-T2；剥除本批新增段并恢复顶部可恢复整文原hash `38571605F23ED45CC5401925E584EA86B167AD3B9A6DEC2C952273EAD8CA538A`。历史Gate44真实红、Gate47/48有限门禁及过去“未运行”状态按原时点保留，顶部以最新实际证据修正。

### 统筹动态验收要求

作者没有构建/UE/专项运行/Git权，实际尚未运行，不预填本批报告或新增全量叶数/成功数。全部作者冻结后由统筹统一新DLL构建，单叶保留独立原始report/runtime log，再普通全量GGYGO包含该叶。预期为**Automation Fail**且本叶两个原始生产 `LogGGYGOMovement Error: Movement execution request rejected`，不将runtime自动化转述同一Error的回显重复计作新生产事件：

1. 同Consumer/Owner/Producer、Session=1、`FailedRecoveryBadSet` 与 `FailedRecoveryBadWalkStart`；InputRequest=1且ExecutionRequest=1。
2. 完全相同的原消费者/来源/Session/坏配置与Profile，InputRequest=2且ExecutionRequest=2。
3. 两条均包含SingleInterval的实际区间约[.1,.2]、SpeedCurve、`evaluated speed must be non-negative`；未降级Severity，无额外生产诊断/Warning/断言Error。
4. 所有业务阶段、请求3的真实健康sample/speed及原Binding清理成功后唯一Info：`GGYGO_FAILED_REQUEST_RECOVERY_COMPLETE`。该行携原Consumer/Owner/Producer/Session/Binding/BadSet/BadWalkStart路径、`ExpectedFailurePairs='1/1,2/2'` 与 `RecoveredInputRequest=3`；它提供核对期望，不冒称读取了私有执行号。缺标记即未走完，不接受仅两条Error。
5. 只可单独写“严格诊断匹配”；绝不能改原框架Fail为Success、注册ExpectedErrors、过滤Error/排除红叶或称普通全绿。

**C38-T2两文件已完成唯一叶及有限静态交回，现停止写入并冻结；新DLL/原始Fail报告仍待统筹验收。** 本叶是消费协议的真实求值失败恢复专项，未关闭物理Input发行/出生首次W/Run/Hero/MoveData/RMS真实模拟提交/跨Session或Producer/正式七Profile/AnimBP/WalkRun BlendSpace/网络。gadge继续占位；原TurnBack业务及曲线不重写。统筹已同步的Obsidian有限静态是Gate48范围，本次专项目录状态由统筹后续同步，全局/图文仍无本会话写权。
