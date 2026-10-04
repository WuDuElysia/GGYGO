# 第10批 Movement / D5 验证记录

更新：2026-10-03
当前状态：本地 CurveRMS 实际区间四源已交回冻结并获统筹 `finite_static_accepted_uncompiled` 有限接受，四 hash 独立匹配、范围 diff 检查 exit0；尚未新 UHT/编译或动态运行。CMC 在原生实际区间求值/提交，RMS 消费原 Prepared，SavedMove 保存原输入/结果，失败只消费原当前请求；NetSerialize 原 wire 字段保持但加载清除本地 Origin/Prepared，导入身份与 authority/proxy 匹配/校正尚未关闭。E1 编码/有限静态事实和 C30/第35次历史65叶Success保留，旧门禁不覆盖本步；FAILED 历史红叶、两生产 Error及请求3标记没有复测或改为通过。正式七 Profile 仍未完成创建/引用接线，当前版本 Run/物理输入/正式 Hero、资产/联机与 Obsidian 图文未验；Gadge及既有 GA_Dodge/Gadget 保留占位，蓝图/旧命名调查单列为只读证据。本两记录已保存回读并交回冻结。

以下各节保留当时交回的历史结果与验证边界；“尚未构建”“生产调用尚未接入”等只描述对应历史阶段，最新状态以上文及末尾本地 CurveRMS 段为准，原历史结果不改写。

## 历史阶段 10-StrictConfig-S2：MovementSet 统一纯校验

- 按统筹 C11 四文件租约，先记录基线，再直接修改 MovementSet.h/.cpp 与10 Subleases/Validation，无代理。只新增 `ValidateMovementSet(FString& OutError) const` 与编辑器 `IsDataValid` 薄适配，以及准确的源码注释；没有修改旧getters/消费者接口或实现。
- 统一校验对以下16个非废弃数值先检查有限性，再按同一字段规则检查范围；合法零值保持原值，不用默认数值替换失败配置：

| 字段 | 已编码范围 |
| --- | --- |
| WalkSpeed / RunSpeed / StartStopSelectionSeconds / RotationYawRate / MaxAcceleration / BrakingDecelerationWalking / GroundFriction / RootMotionScale / TurnBackYawSettleDegrees / TurnBackRunOutMinSpeed / TurnBackDurationSeconds | >=0 |
| WalkToRunHoldSeconds | [0.1,60] |
| WalkRunBlendInterpSpeed | [0,50] |
| TurnBackReverseInputDotThreshold | [-1,1] |
| TurnBackMinYawDegrees | [0,180] |
| TurnBackRunOutForwardThreshold | [0,1] |

- 废弃且无消费者的 MaxCurveDrivenSpeed 不参与自定义校验。零Blend仍为显式立即切换，零TurnBackDuration仍为既有立即截止；数值校验不执行这些业务，也不改变阈值、默认值或字段元数据。
- 曲线模式要求 WalkStartProfile、WalkLoopProfile、RunLoopProfile、StartStopProfile、WalkStopProfile、RunStopProfile、TurnBackProfile 七项齐全；两Loop为true，其余五项为false。非空引用检查原生IsValid与Loop，然后委托冻结的 `ValidateProfile`；不复制Duration/keys/切线/曲线覆盖规则。
- `bUseCurveDrivenSpeed=false` 本身合法并允许引用为空；已填项仍检查对象、Loop与内部数据，未把显式固定模式移除或与缺配置替代路径混为一谈。
- 入口清空OutError；失败为 `MovementSet '<path>': <field>: <reason>`，内部失败再保留 `Profile '<path>': <原错误>`。非有限、非负要求、区间越界、缺必需引用、无效对象和Loop不匹配各有具体原因。成功返回true且旧错误为空；没有对象修改、日志、播放/诊断状态或缓存。编辑器只调用同一接口并AddError，保留父级Invalid，不增加第二套规则。
- 源码头部已删除为缺Profile固定速度兜底辩护的旧说明，明确新纯校验与尚未接入的CMC；getters注释忠实标明非法时间回1.5/上限60截断与负速钳零仍是待移除路径。原成员tab注释/声明风格保持。

### 静态保护与未验证边界

- cpp在内存中移除新增验证/编辑器函数与编辑器include后，完整字节恢复2102及原SHA256 `A7172EF53E1C02BFE81F0E70B508F9C71DB9C8F9E4AEBBF95AD6C1372B652EB3`；磁盘保留新增代码，未回滚。此证据覆盖旧构造、Defaults命名空间、GetSpeedForGait、GetSanitizedWalkToRunHoldSeconds与GetProfileForMotion的全部原代码。
- header去掉注释和新增两声明/编辑器guard后，旧代码一致；26组UPROPERTY/字段声明/默认值/元数据逐字一致，三getter原声明保持。只读Profile两文件、MovementTypes、CMC/RMS、Sampler两文件、旧Movement/TestTypes、新Profile测试及结构MD/Canvas共12个hash未变。
- 静态扫描16字段名/源值、7引用/Loop映射、唯一内部Profile委托、唯一声明/定义与编辑器调用；括号/预处理、UTF-8无BOM/LF、行尾空白及成员缩进通过。已对照原生IsValid(const UObject*)与同模块IsDataValid写法。此扫描不是C++执行或动态测试，没有运行UE/UBT/Automation/Git。
- 最终源码SHA256：h=`D5509274F399B10BEF6CB1D2D677C87EC7923231EA1688DB0923094DD82C183D`；cpp=`E30485A826AF150C72CFA94D69ACF125AF188D4B8BE5F1FF38175745D5E53ABE`。完整四文件非Git diff与记录hash随冻结交回；S2尚未编译或专项运行，第26次门禁早于S2写入。
- 生产调用尚未接入：旧CMC仍可能用非法阈值替换、负速钳零、缺Profile固定速度、单Loop替代和缺配置当完成。后续CMC绑定必须复用本统一接口，再移除旧替代路径；失败生命周期与运行消费由后续租约确定，S2未关闭这些缺口。
- 架构复核：数值/引用规则归MovementSet、Profile内部曲线规则仍归Profile，CMC继续唯一持有步态/相位/时钟/执行，未新增循环依赖或状态链。已只读检查Movement结构MD与Canvas的set/cmc节点；新接口、显式模式及遗留消费边界须后续同步。本四文件租约明确禁止Obsidian写入，图文同步尚未完成；未扩范围或把未接入写成已实现。
- 停止在四文件静态冻结，写入权限交回；不自动S3、专项或资产操作。

## 第26次统筹实际门禁：T1已验证，S2未覆盖

统筹交回完整 GGYGOEditor 构建 Succeeded：6 actions、85.06秒、exit0（UBA77.94秒）。实际报告 `Saved/AutomationReports/ModuleRepairGate_20260930_26/index.json` SHA256为 `E0530DEA6486D1B042227A0E4D859BB9831FDF169B87F45781A8F6006C768BEB`；本组长只读核对hash、顶层60 Success/其它计数0及StrictEvaluation叶：11.41.41 UTC、Success、0.00892530009150505秒、entries=[]、errors/warnings0。统筹确认全部叶errors/warnings0、旧59保持，UE PID36128 exit0且已退出。Input/原生P1/独立Health未重跑；该门禁早于S2新增，不证明S2校验/CMC消费/生产资产或游戏内Run。

## 10-StrictConfig-S1-T1：纯 Profile 六场景专项

- 统筹核对预检后授权三文件：新增 `Source/GGYGO/Character/Tests/GGYGOLocomotionMotionProfileTest.cpp`（入口不存在）、10 Subleases、10 Validation；先登记范围，再由 Movement 组长直接写入并静态复核，无代理。
- 唯一原生入口：`GGYGO.Movement.Locomotion.Profile.StrictEvaluation`，`IMPLEMENT_SIMPLE_AUTOMATION_TEST`，`EditorContext | EngineFilter`，受 `WITH_DEV_AUTOMATION_TESTS` 保护。Transient Profile 由 TStrongObjectPtr 跨全部断言持有，作用域结束释放；无 World/GI/UCLASS/第二框架、日志过滤或假成功。

| 代表场景 | 实际夹具与验收断言 |
| --- | --- |
| 负 Speed 键 | 两端值-1；明确失败，错误含 `SpeedCurve.Keys[0].Value` 与非负要求 |
| 正键产生负插值 | 时间0/1、值1/1，Cubic/User/WeightedNone；首键两侧切线-8、末键两侧+8。先断言 SetKeys 后切线保留、原生 Eval(0.5)≈-1、ValidateProfile 成功，再断言求值失败及 `SpeedCurve`/evaluated speed 非负原因 |
| 缺 Yaw 曲线 | 其余曲线合法，仅清空 Yaw keys；失败含 `YawCurve` 与至少一个 key 要求 |
| 正速零方向 | Speed=10，两个方向曲线均0；明确失败，错误含两方向字段及正速必须有有效方向 |
| 合法零速零方向 | Speed/DirectionX/DirectionY均0，Yaw线性0→40；[0.25,0.5]成功，Speed/Velocity/Direction/角度为0，YawTotal=20/YawDelta=10、ClipLength=1、bHasCurveSource=true、其余flag=false，旧错误清空 |
| 同输出成功→倒序失败 | 先以Speed=10、Direction=(0,1)、bLoop=true在[0.25,0.5]成功，检查非零速度/Yaw/角度和true flags；同一Sample再以[0.75,0.25]调用，失败含EndTime与不得早于StartTime原因，全部字段清空 |

- 每个失败调用前 Sample 有非默认值；逐项检查5个float、3个FVector的9个分量及4个bool，共12成员18标量精确归零/false。期望值为字面量，未调用 Sample.Reset 生成期望。成功→失败场景仅额外预填当前生产者始终输出零/false的 PositionDelta 与 bHasPositionDelta，明确标为调用方哨兵。
- 五个失败调用均预填旧错误，断言失败返回、非空新错误、旧文字消失、字段/原因正确；两个成功调用断言清除旧错误。负插值夹具的真实 Eval 或验证前置未满足时专项直接失败，不把其它失败当作该分支通过。
- 静态核对本机 UE 5.8 FRichCurve::SetKeys/AutoSetTangents、无权重 Cubic Eval、TStrongObjectPtr 构造/移动/解引用、Automation float/double/FVector重载及零容差比较；没有执行这些 C++ 调用。静态扫描确认1入口/6场景/5失败调用/18 reset断言、括号和预处理边界、UTF-8无BOM/LF、无行尾空白，辅助函数与入口名称在 Source 中唯一。
- 新测试220行、10692字节，SHA256 `E175F594B4B0632DDF2848A069DB9DD9049CB6D0D1ECE404DA02C985BB7FAC67`。生产 Profile `.h/.cpp` SHA256 分别仍为 `26FF4A2649C4ECD8141E6E86540EF2B9D232DF2A8F4E4D0EA65BA2F237943857` / `16216760DD9C573CECC1DD8E060E11B80F027BB650FF5B10DC341D71415FD5DB`；生产代码未改。
- T1冻结时的有限验证：第25次真实构建 Succeeded、4 actions、13.08秒、exit0，59个既有正常叶 Success；该门禁早于本测试新增，当时专项尚未构建/运行。后续第26次真实专项Success见上方门禁记录，本组长没有自行运行UE/UBT/Automation/Git。
- 完成前只读核对 Movement 结构文档：未新增接口、权威状态、依赖或执行链，Profile/CMC消费缺口与生产资产状态未变，专项待统筹实际结果的边界仍一致；没有 Obsidian 信息变更。本步只写三个授权文件，完整非 Git diff/hash 交回并冻结；不自动 S2–S7，不声称游戏内 Run 已恢复。

## 10-Build24-R1：复制宏直接头文件

- 在 M1 四文档先完成并冻结后执行统筹唯一三文件租约：CMC.cpp 与10 Subleases/Validation。
- 唯一生产改动：在既有有序 include 区 `GameFramework/Character.h` 后增加 `#include "Net/UnrealNetwork.h"`，提供复制宏直接声明；没有修改函数、状态、规则、接口、预测或其它源码/测试/资产。
- 修改前 SHA256 `497D60A442FD8605AA61ED6FE3EF66EB5BBE8626EC5F5AB80DFE3B8E7BC77EF7`，55070字节；修改后 SHA256 `A0DE24171A8188AC19308C84585837EA43464CE679FE95FD6285C01BD7E0D675`，55101字节。差值仅新增行的31字节，UTF-8无BOM/LF保留。
- 已在内存中逆向删除唯一新增行：55070字节、SHA256 精确恢复修改前基线；工作区保留该行。此证明覆盖所有其它源码字节，未做磁盘回滚或 Git 操作。
- 三文件冻结并交回最终 hash/一行 diff；本组长未编译、未运行 UE/Automation，R1 冻结时等待统筹重建，后续第25次成功见上方 T1 记录；不将第24次宏错误当作 Profile 语义失败。
- M1 的结构 MD/Canvas 未在 R1 再改；S2–S7、显式固定模式取舍与生产资产迁移继续未授权。纯 Profile 专项另按 T1 三文件租约实施，尚未构建/运行。

## 10-StrictConfig-S1-M1：结构文档同步

- 仅写 Movement `结构.md`、`GGYGO_结构_移动与位移.canvas` 及本批 Subleases/Validation。入口四 hash 和精确路径见 Subleases 当前 M1 条目。
- 已读取项目 `obsidian-canvas-diagram` skill、结构 Canvas 全字段/布局及只读相邻上下文，对照冻结的 Profile 源码。结构 MD 只更新 Profile 接口行和纯求值/消费边界；Canvas 只改 `sampler` 节点正文。
- 同步可选第四参数 `FString* OutError = nullptr`、入口清空输出、合法零速度、负数/非有限/正速度无方向失败、局部候选成功提交；每次全量 `ValidateProfile`，纯且无状态/缓存/日志。
- 当前 CMC 忽略失败/固定速度或单 Loop 替代等仍标为未修，生产资产接线仍待窗口；没有修改 CMC 权威、其它类/接口、算法、计划/流程图或其它图文。
- 保存后 JSON 解析成功：13 节点/10 边、共23个 ID 唯一、端点全部存在。逐字段比较仅 `sampler.text` 改变；其余节点字段和全部边/标签与入口完全一致，标签仍描述既有真实接口关系。
- Markdown/Canvas 共18个 wikilink 出现，11个不同目标均存在、唯一解析；未新增链接。节点矩形有限、宽高为正、无重叠；Profile 节点保留 `(1100,230,410,250)`，保守换行预算约196 px。未做实时 UI 渲染。
- 未写源码/测试/资产，未运行 UE/UBT/Git；四文档冻结，完整本步 diff 范围及四 hash 交回。纯 Profile 自动化与 S2–S7 未获授权。

## 统筹构建交回（2026-09-30）

第23次受限 UBT 启动异常，未编译。第24次完整构建实际 exit6、`Failed(OtherCompilationError)`，计划6个 actions 仅执行3个 Compile，25.99秒，未链接新 DLL、未跑测试。本组长仅只读核对 `Saved/Logs/ModuleRepairBuildGate_20260930_24.log`：CMC.cpp415–419 五处 `DOREPLIFETIME_CONDITION` 宏不可见，其派生类型错误来自同一缺失宏头，不作为 Profile 语义失败或专项结果。修复另按统筹唯一短修租约执行。

## 10-StrictConfig-S1：严格纯求值

授权与范围见 `Module_Repair_10_Subleases.md` 当前 S1 条目，实际只写四个已存在文件：Profile `.h/.cpp`、10 Subleases、10 Validation。由 Movement 组长直接完成，未创建/唤醒子代理。

### 已实现契约

- `EvaluateInterval(StartTime, EndTime, OutSample, FString* OutError = nullptr)` 保留三参数调用兼容。入口同时清空 OutSample 和可选错误，失败返回曲线/字段及失败性质，不在资产中写日志或持有诊断状态。
- 删除 `EvaluateFinite` 的非有限数替换 0；删除负速度 `Max(..., 0)`。合法零速度成功并保留 0，负速度/非有限样本/正速度无有效归一化方向失败。
- 循环 Yaw 的原点、周期端点、StartTime/EndTime 相位采样分别检查；任何采样失败传递原错误，展开后超出 float 范围或区间差非有限同样失败。
- 原始方向分量、归一化 Direction、Velocity、Yaw 与 DirectionAngle 均受有限性检查。局部 Candidate 仅在全部检查成功后提交；失败没有半份样本残留。
- `ValidateProfile` 为纯校验：键时间严格递增；Time/Value/Tangent 有限；SpeedCurve 键非负；插值、切线模式、权重模式及外推枚举必须为 UE 5.8 已声明值；启用的到达/离开权重必须有限且非负。未启用的权重不参与检查或求值。
- 合法单键常量、非循环时间钳制以及周期浮点边界修正保留，未修补曲线键、改来源资源或增加播放状态。每次区间求值调用同一个纯数据校验，S1 没有增加跨帧有效性缓存。

### 只读调用与边界复核

对照本机 UE 5.8 `RealCurve.h`、`RichCurve.h`、`EnumAsByte.h`、`Vector.h` 及 RichCurve 求值接口。以下是源码分支审查结果，不是 UE 执行结果：

| 边界 | 已核对的源码路径 |
| --- | --- |
| 合法零速度、零方向 | 不触发正速度方向校验；Candidate 保留 Speed=0、Velocity=0、bHasCurveSource=true |
| 负键值或插值后的负速度 | 分别在 SpeedCurve 数据校验及求值结果校验失败；不钳成 0 |
| 键/启用权重/求值出现 NaN 或 Inf | 返回具体字段/曲线错误，OutSample 仍为入口 Reset 结果 |
| 正速度且方向为零或低于可归一化门限 | 返回 DirectionXCurve/DirectionYCurve 错误；不改为前向 |
| 非循环超出尾部的合法时间 | 钳到 Duration；不删除合法端点采样 |
| 单键常量、零长度合法区间 | 数据校验保留常量曲线，StartTime=EndTime 允许求值 |
| 循环精确周期/跨周期与浮点边界 | 保留周期拆分和累计 Yaw 展开，各原始采样值必须成功 |
| Yaw 差分溢出、派生方向/速度/角度非有限 | 成功提交前返回失败，不保留部分 Candidate |
| 非有限/负时间、逆序区间或非法 Duration | 返回参数/Duration 错误，既有样本与既有错误在入口清空 |

- 搜索 Source 下所有调用：CMC 的 Walk/Run Loop 两处、非 WalkRun 一处及现有测试一处仍是三参数调用；声明的默认第四参数保持源代码调用兼容。没有修改这些消费者，也未通过编译证明兼容。
- Profile 两文件括号/预处理块、定义唯一性及行尾空白已做只读核对；源码不再包含 `EvaluateFinite`、`FMath::Max(RawSpeed...)`，没有新增 `UE_LOG`、Tick、Timer、依赖或 UObject/资源写操作。
- 本轮完整四文件 diff 通过内存中修改前快照与修改后文本生成并交回；未执行 Git。
- 生产文件 SHA256：`.h` = `26FF4A2649C4ECD8141E6E86540EF2B9D232DF2A8F4E4D0EA65BA2F237943857`；`.cpp` = `16216760DD9C573CECC1DD8E060E11B80F027BB650FF5B10DC341D71415FD5DB`。两份记录的最终 hash 在本轮冻结输出交回，避免记录自引用 hash。

### 本轮未执行与仍开放项

- 未编译、未启动 UE、未运行 Automation/PIE；未新增或修改测试、蓝图、资产、CMC、RMS、MovementSet、网络/预测或 Gadget/GAS。
- CMC 尚会回固定速度/复制单 Loop/把缺 Profile 当完成，且非 WalkRun 调用仍忽略求值失败并推进时间；RMS 的缺方向前向替代等也未在 S1 修改。不能将 Profile 纯求值收口写成整个移动链已严格配置，或游戏内 Run 已验证。
- `bUseCurveDrivenSpeed=false` 的显式模式取舍未决且未修改；先前预检的候选不作为已批准方案。
- 七份生产 Profile 仍待当前曲线/时长/指纹回读与独占资产窗口。Curve API 未回读成功不等于曲线不存在；旧导出不是当前生产曲线证据。
- S1 当时未获 Obsidian 写入范围；现由 M1 单独同步 Movement 结构 Markdown/Canvas，计划/流程图仍冻结。历史统一构建证据的全局措辞由统筹维护。
- 停止点：四文件冻结，交统筹根审查；S2–S7 未授权，不自动继续。

## D1–D5 历史记录（2026-09-29）

以下构建/自动化措辞描述当时记录，不表示 S1 已验证；其中固定速度兜底为当前仍待删除的缺口，不是新增授权或已确认模式。

## 范围与结论

- 未新增或修改 Gadget/GAS 占位，本批只处理 Movement 权威 Locomotion 与 Animation 只读接缝。
- Git 历史确认 `WalkRun` 早已有 `BS_Pyrios_WalkRun` BlendSpace1D，旧提交也已实现过走跑切换与 TurnBack。当前实现复用这套表现拓扑，没有另建 Walk/Run 状态机。
- `UGGYGOCharacterMovementComponent` 唯一持有 Gait、`WalkRunBlendAlpha`、Start/Stop/TurnBack 选择、Profile 时间、预测和校正恢复。
- `UGGYGOLocomotionMotionProfile::EvaluateInterval` 以纯函数求值 Speed / DirectionX / DirectionY / Yaw；CMC 运行链不再读取 `AnimInstance::GetCurveValue`，也没有新增 Tick、Timer 或位移执行器。
- AnimationStateFrame 新增 `WalkRunBlendAlpha` 与 `StopMotionType`。ZZZ 兼容层只做 `WalkRunBlendAlpha → GaitBlendY` 和 `StartStop/WalkStop/RunStop → StopValue 0/1/2`，不再持有走跑插值或早停计时。
- CMC 公共轴统一为 UE 局部 `X=Forward, Y=Right`；现有动画快照适配层负责旧表现轴交换。
- `SetMovementSet` 切换/置空会恢复组件基线并清理 Locomotion 自有 Brake/TurnBack 源，不结束 ActionMotion 资源。
- SavedMove 保存动作段、时间与相位；自定义 MoveData 只传最小语义提示，服务端按自己的 MovementSet/Profile 重算；Correction Response 返回权威基线供未确认 move 重放。

## 命名与蓝图现状

- 公开语义统一使用 `WalkRunBlendAlpha`，范围 `0=Walk, 1=Run`。
- `GaitBlendY` 只因 `ABP_Pyrios` 已序列化该字段而保留；蓝图显示名为 `Walk Run Blend Alpha`，不得用于新 C++ API、Profile 或 BlendSpace 轴名。当前 `BS_Pyrios_WalkRun.uasset` 的离线字符串仍只有旧名，规范轴名需要在 UE 窗口保存并回读。
- 停止语义使用强类型 `EGGYGOStopMotionType`；`StopValue` 仅是现有 AnimBP Select 的兼容索引。
- `create_walkrun_blendspace.py` 与 `fix_blendspace_axis.py` 已统一轴名，并将创建路径统一为当前资产目录 `/Game/Characters/Player/Pyrios/Animation/Movement`。
- 不需要重画 AnimBP 的 Walk/Run 状态拓扑：继续使用一张 WalkRun BlendSpace1D。需要在 UE 窗口回读其 X 输入和 Stop Select 接线。

## 只读资产审计

`AAADocs/Scripts/audit_locomotion_motion_profiles.py` 离线复跑结果：

```text
[LocomotionAudit] writeMode=unchanged-report packageWritesMade=false
[LocomotionAudit] status=PendingUEAssetWindow profiles=7 missingItems=7 failedChecks=none
```

报告：

- `AAADocs/Modules/Movement/Locomotion_Motion_Profile_Migration.json`
- `AAADocs/Architecture/Interactions/Locomotion_AnimBP_Wiring_Audit.md`

待独占 UE 资产窗口：

1. 创建 WalkStart、WalkLoop、RunLoop、StartStop、WalkStop、RunStop、TurnBack 七份 Locomotion Profile，并回读源曲线/时长/指纹。
2. 将七份 Profile 写入 `/Game/System/DA_Movement_Default`。
3. 回读 `ABP_Pyrios` 的 `AnimSet.blend_spaces["walkRun"]`、WalkRun X 输入和 Stop Select 0/1/2。
4. 回读 `BS_Pyrios_WalkRun` 的类型、0/1 样本、轴范围与 `WalkRunBlendAlpha` 显示名。

完成以上资产接线前，源码会走固定 Walk/Run 速度兜底；不能据此宣称游戏内已经恢复原曲线包络。

## 静态验证

- 对照 UE 5.8 `CharacterMovementReplication.h` 核对自定义 MoveData / MoveResponse 的覆写签名与容器安装接口。
- `git diff --check`：通过；仅报告两个既有 ZZZ 文件的 CRLF/LF 归一化提醒。
- Python `py_compile`：三个 Locomotion 审计/迁移脚本通过。
- 四张修改后的 Canvas 均通过 JSON 解析；节点/边 ID 无重复，边端点全部存在，边标签无空值。
- 源码搜索：CMC/Animation 当前链没有 `GetAnimInstance`、`GetCurveValue`、`AdvanceGaitBlend`、`SetTimer` 或 `FTimer`；CMC 仅保留自身既有 Tick，用于 ActionMotion 资源清理。
- 自动化覆盖集中在一个 Movement 用例和现有 Animation 兼容用例，验证 MovementSet 恢复、WalkRun 混合、停止选择、曲线关闭、标准轴、Move 合并/权威重放、Profile 循环求值和 0/1/2 映射；未增加第二套测试框架。

## 本批未执行

- 未运行 UBT/Editor/Game 构建。
- 未启动 UE、未保存 `.uasset`、未运行 UE Automation 或网络 PIE。
- 未做 Dedicated Server、模拟代理、低帧率校正和视觉脚滑动态验收。

这些步骤受当前统一构建与 UE 独占窗口约束，后续由统筹在所有源码写入者冻结后排队执行。

## 追加验证：10-StrictConfig-S2-T1（2026-09-30）

本节为最新步骤与Gate27证据；原22350字节保留此前冻结时点，入口SHA256 `6EEE7906480A55C9B1898D1890F00F2EF1B96C3D9CF730A4AEAEF0825048FBF0`，不改原正文。Subleases亦保留原23927字节/`DF8AEBBBB012760BBF1B3E10F19E51B7BEDBBEC08E250451F604E7ECEDECAE94`，只追加本步。

### 已写入专项，尚未构建/运行

- 按C13三文件租约，先追加原子范围，再新增 `Source/GGYGO/Character/Tests/GGYGOMovementSetValidationTest.cpp`；生产/旧测试/CMC/RMS/预测/Content/Obsidian及全局记录未写，无代理/UE/UBT/Git操作。
- 单一原生入口 `GGYGO.Movement.Locomotion.MovementSet.StrictValidation`，EditorContext|EngineFilter，WITH_DEV_AUTOMATION_TESTS保护；编辑器族另受WITH_EDITOR保护。NewObject公开字段构造真实Profile/FRichCurve，Set与全部Profile使用TStrongObjectPtr，正向基线先验证，未知夹具失败直接停。没有World/GI/UCLASS、第二框架或日志过滤。

| 五个场景族 | 已写断言 |
| --- | --- |
| 数值有限/范围/零 | 16字段逐项NaN、正Inf、负Inf及低于下界；5有界字段上界越界和两端有效。11非负字段zero成功，4有界字段zero亦合法，Hold=0失败；废弃速度上界NaN保持有效且未修补 |
| 显式模式/七引用 | true完整配置成功，false七空引用成功；true逐项清空目标槽，其余六项有效，错误必须指出该槽及必需原因 |
| 七槽Loop | false/true两模式各七例，独立反Loop Profile先通过自身数据校验，再检查槽名、实际Profile路径、期望true/false及错误Loop标志保持；不修改共享基线Profile |
| 原Profile错误 | 实际两端Speed=-1先通过原生ValidateProfile确认负键失败；两模式均赋予WalkStart槽，错误保持MovementSet/槽/Profile路径与完整原错误，Speed keys/Duration/Loop保持 |
| 编辑器薄适配 | 有效、非法RootMotionScale、fixed模式已填非法Profile三例；SplitIssues结果恰好0或1错误、0警告，Invalid错误全文等于已检查的运行时错误，正常为Valid |

- 参数期望从冻结公开契约独立声明，不从生产私有规则数组生成。每次配置校验前快照当前已注入值，检查返回结果与诊断后再作夹具恢复；失败不因测试恢复而被掩盖，成功旧error为空，失败旧文字消失并含具体路径/字段/原因。
- 所有配置检查对17float（含废弃字段）用FMemory::Memcpy取uint32位模式，NaN/Inf也逐位比较；2bool及7TObjectPtr引用逐项比较，共26属性，没有对UObject内存或padding整体比较。错误Profile显式比较键数与每键9字段：Time/Value/ArriveTangent/LeaveTangent/ArriveTangentWeight/LeaveTangentWeight逐位，InterpMode/TangentMode/TangentWeightMode逐枚举；Duration位模式与Loop另查。Loop错误场景检查目标错误flag保持。
- 已按根反馈消除原生FRichCurveKey部分相等的盲区：原生比较不含权重且线性键省略切线，不能作为全部Keys保持证据；当前直接检查9字段，不扩为全Profile/新矩阵。
- 一个cpp五族静态推算124次运行时配置检查（95预期失败/29预期成功），以及3次编辑器适配调用；不是124个Automation叶，也不是已经执行的结果。384行、19681字节，UTF-8无BOM/LF；SHA256 `1F3F20853F65B6037F3F162B6B9393504937186C93A96A98B0D01BC5C00BD616`。
- 静态复核16字段/指针/范围与7槽/Loop、17+2+7快照、键数/9键字段、唯一入口/五族、原生前置、调用路径、括号/预处理及编码/空白；已对照TestEqual泛型、TEnumAsByte::GetValue与原生UObject::IsDataValid/Context.SplitIssues。仅源码/API核对，未编译或执行新专项；完整三文件非Git diff与最终hash交回后冻结，不自动S3。
- 最终保护：两份记录原始字节前缀恢复各入口hash；MovementSet.h/.cpp、Profile.h/.cpp、MovementTypes、CMC含RMS、Sampler.h/.cpp、旧Movement/TestTypes、新S1 Profile测试及结构MD/Canvas共14个hash保持。架构/接口/执行/资产状态未变；S2结构图文同步仍待原独立租约，不能因本测试写完关闭CMC消费、生产迁移或Run验收。

### Gate27实际有限证据

统筹交回完整GGYGOEditor构建Succeeded：9 actions、87.41秒、exit0、UHT6 generated；报告于12.38.59 UTC为60/60 Success、0.6495425105秒，UE41896 exit0且已退出。本组长只读核对 `Saved/AutomationReports/ModuleRepairGate_20260930_27/index.json` 的SHA256 `FB5CA102423F04E94294709BE9000D1D5515CBF07895AED20625FB4002503A05`、60成功/其它顶层计数0及全部60叶errors/warnings0。S2已编译，原60叶保持；该门禁发生在本配置专项新增前，没有新专项结果，消费者仍未接入。此步不扩大Input/原生P1/独立Health或资产动态验证范围。

## C14 / S3a-1 配置绑定：静态交回（2026-09-30）

- 实现范围：CMC.h/.cpp的SetMovementSet、Apply、绑定Reset及必要注释/本地日志类别；两个生产文件已先冻结，再追加本记录。返回接口为bool及可选OutError，保持现有单参数调用源兼容，不新增蓝图反射接口。
- 返回/诊断：入口清OutError，解除旧指针、恢复基线并清自有Locomotion；nullptr合法解绑返回false、无Error。有效非空配置调用ValidateMovementSet一次，成功才保存指针/应用参数/返回true；失败原原因写OutError并以LogGGYGOMovement/Error输出组件、Owner、配置路径、原因。失效UObject明确拒绝，不调用其校验器。
- 清理/应用：绑定Reset补清转身输入锁存及复制标记，保留普通ResetTurnBack自然结束时的锁存语义；只移除Brake/TurnBack两个自有RMS。GA token/source/clock和结束函数未触及。加速、地面制动、摩擦及Yaw速率已通过配置校验后原样写入，不再二次钳制；显式false与合法零仍由冻结校验契约接受。
- 静态证据：cpp撤销三个授权函数和日志类别后逐字恢复入口；setter校验单调用、Apply无FMath钳制、仅两个自有source移除、无ActionMotion所有权或全局硬停操作均通过源码核对。13个保护源码hash保持（配置/Profile/Types、两RMS、PawnExtension、旧Movement/TestTypes、S1/S2专项）；完整diff交回。未编译/运行本绑定逻辑，源码核对不等同动态断言。
- 有效期/架构：准入只由已接受指针派生，无新增有效性状态机、帧调度器、跨模块依赖或每帧七Profile扫描。绑定期配置/Profile/外部曲线只读，变更须重绑，热编辑自动失效不支持。结构MD/Canvas接口与流程同步待独立租约，Obsidian及全局记录本步禁止写入。
- 未关闭：GetMaxSpeed/地面物理门禁、SavedMove/校正/getter、Evaluate/Finish/RMS替代保持旧行为；速度兜底未删，Run与资产蓝图接线未验。旧AuthorityAndMapping缺TurnBack并原地改模式，须独立适配，不能用Gate29旧通过证明本实现通过。
- Gate29有限历史：统筹交回新DLL常规63/63 Success，MovementSet.StrictValidation叶Success、0 errors/warnings、entries空、0.007742800秒，九source hash保持、UE26112已退出。它验证先前配置专项，不含本次新增绑定实现；本组长本步未运行UE/构建/Git/代理。
- 冻结生产SHA256：h `4B1DB91F2B3B74EDC953A696127FC2D2855D804141DE9DD3F0E4905AB39A0573`；cpp `4B29EEA193387A8CF50B2A46A3A39156CA4AA63C6E5E9F1CBD87D42C947B8357`。两记录仅追加、入口字节前缀保持，最终四hash另交回；停止于S3a-1。

## C16 / S3a-T1：既有夹具绑定时序适配（2026-10-01）

- 唯一范围：原AuthorityAndMapping cpp、原TestTypes.h及两记录；统筹明确授权保留推进清旧样本目的并开放仅测试子类赋值包装。仅apply_patch写入，无生产、资产或笔记修改，无UE/构建/Git/代理操作。
- 合法配置：FirstSet首次绑定前显式true，补MakeProfile(false,500,0,180)的非循环TurnBack；原六Profile与MakeProfile/AddLinearKeys全文保持。原绑定/解绑/重绑调用检查真实bool结果，非法前置立即退出；合法nullptr返回false仍执行原基线恢复断言。
- 模式与旧样本：RunStop实际推进之后先要求HasUsableSpeed且Speed有限，再复制其完整CurveMotion。独立FixedSet绑定前false、复用相同七个有效只读Profile，不改已接受的FirstSet。固定绑定完成后通过SetTestCurveMotion注回旧结果，再注入Turning/输入/Run；Advance前检查样本仍有效且相位仍Turning，然后保留原清相位/无曲线源断言。绑定清理不能替代此次推进的清样本证明，样本前置失败立即退出，无零样本替代。
- 测试边界：TestTypes只增加一个非反射public包装，赋值其继承的protected CurveMotion；无生产接口/UFUNCTION、新状态机或曲线求值替身。完成fixed场景后显式重绑FirstSet，再执行原后续轴/预测/loop状态注入。
- 静态证据：原21处TestNotNull/TestTrue/TestFalse/TestEqual调用及全部期望逐字保持，当前29处检查仅新增5次绑定结果和3次源样本/相位前置；不是29个测试叶或已通过的结果。轴映射、SavedMove组合、权威replay与循环speed/yaw整段逐字保持；TestTypes撤销两新增行后逐字恢复入口；七引用匹配、模式绑定前设置、注回/前置/推进/恢复顺序与唯一Automation入口均核对通过。
- 保护/冻结：13个只读源码hash保持，包括C14 CMC两文件、S2/Profile/Types、两RMS、S1/S2专项和PawnExtension两文件。两测试文件UTF-8无BOM/LF，cpp166行/9117字节、h44行/1771字节，已先冻结再记录；SHA256分别`1EA95AE61E1B832DC570A11136D7765C9119C86471824A73773118C1F0805A90`、`78920CCD1FA1CE3D28321D7C6330235A4FC47B9768D83739F010CE706E1E09B5`。两记录原始字节前缀保持，完整四文件diff与最终hash交回。
- 未验证/停止：本适配未编译/运行，未实际证明RunStop源样本前置或推进清理通过；不能用Gate29代替。C14及本夹具的新DLL验收、地面速度门禁、预测整改、资产/蓝图与Run仍未完成；C14图文同步待独立范围，本次仅测试适配无生产信息变化。四文件冻结交回后停止，不自动S3a-2。

## C17 / S3a-2：普通地面执行准入静态交回（2026-10-01）

- 唯一四文件：CMC.h/.cpp及两记录；仅apply_patch写入，生产先静态冻结、再追加证据。本次没有新增或修改测试、运行UE/构建/自动化/Git、唤醒代理、保存资产或写Obsidian。
- 准入与执行：accepted MovementSet指针唯一派生权限；Walking/NavWalking未准入GetMaxSpeed为0，不再Super固定速度回落；地面GetMinAnalogSpeed=min(native最低值,本模块上限)，不抬高已解算的合法0。BeforeMovement不推进Locomotion、清派生样本并仅标记自有Brake/TurnBack移除，不每帧Reset/增sequence。CalcVelocity拒绝普通输入、RequestedMove及旧平面速度；PhysicsRotation拒绝默认输入朝向；不改其请求所有者状态、原生基座/校正/解穿入口或非地面动量。
- 来源与最后帧：实际已提取动画RootMotion走native优先路径；ActionCurve按原提交struct/实例名/100优先级/Override识别Current及Pending，不以本地token或Finished/Marked过滤掉代理/最后应用帧。未知RMS包括混合集合不借ActionCurve存在获得豁免；非模拟代理正在播放的真实网络RootMotion Montage只使Before延迟判断至native提取后的Calc/Apply，RootMotionFromEverything设置本身不构成成功或豁免。BeginActionMotion仅两处同值名称/priority字面量换常量，资源生命周期不变。
- 入口抬升边界：最终ApplyRootMotionToVelocity对入口未准入普通地面直接Enforce后返回，覆盖自有Brake/TurnBack最后应用及未知来源；先拒绝再允许native改变模式，不依赖Super后IsMovingOnGround。native CMC.cpp:4511以后原生应用会按GetGravitySpaceZ(AppliedVelocityDelta)及liftoff阈值切Falling；自有源当前世界XY、bInLocalSpace=false和IgnoreZAccumulate不用于宣称所有重力方向/复制参数都绝不抬升。有效配置、实际独立RootMotion及非地面入口保持Super，未修改任何源接口/曲线失败替代、GA、组清理或MovementMode。
- 诊断周期：首次无准入普通地面输入、RequestedVelocity、旧平面速度或未知RMS请求输出一次Error，含模块/组件/Owner/配置状态/实际未知源名及类型/原因；无请求的未绑定暂态不输出。私有flag仅诊断：初始false，每次Set复位；C14非法非空原Error后标记true避免重复泛化，nullptr合法解绑无Error。无重试/等待、计时器、帧调度器或与accepted pointer竞争的状态；源指针只在调用内借用。
- 静态证据：内存逆向精确恢复C14 h `4B1DB91F2B3B74EDC953A696127FC2D2855D804141DE9DD3F0E4905AB39A0573`、cpp `4B29EEA193387A8CF50B2A46A3A39156CA4AA63C6E5E9F1CBD87D42C947B8357`；完整源码diff核对通过，授权函数/新增私有辅助/include/常量/注释以外逐字保持。13个已登记保护源码hash保持；UPROPERTY/UFUNCTION保持，UTF-8无BOM/LF、最终换行/无尾随空白；两个记录入口字节前缀保持。权限无诊断flag、无逐move Reset/七Profile扫描、入口拒绝在Super前、保留重力轴且无新GA/模式/组/输入所有权写入均已静态核对，不等同运行结果。
- 架构核对：新增辅助均属Movement本组件，读取既有源注册契约及native RootMotion，不新增跨模块接口/循环依赖、执行时钟或重复状态机。无新增资源，诊断随Set开启新周期；原两Locomotion源与GA独立资源清理路径保持。配置/Profile/外部曲线仍为绑定期只读，变更须显式重绑。
- 生产冻结：h 569行/25142字节，SHA256 `D4F4DF1F4E01D7B87B478F291CDE547165F01430727CAA2DC48438982440573E`；cpp 1696行/61901字节，SHA256 `720B0683C479626D15D88D565420F2D0CDFBC243D42DD10FF8F25C43268DE576`。两记录只追加；最终四hash随交回，不继续生产写入。
- Gate30有限历史（统筹交回，非本组长本次运行）：GGYGOEditor Succeeded，7 actions/43.46秒/UHT5/exit0；63/63 Success、各叶0诊断，AuthorityAndMapping 0.0092460997402668秒且entries空。报告SHA256 `65A1C9387911E0A4B64C04236C7B8F46525D8266D0878B93EA267B56E0BEBD23`，16:48:53 UTC，UE36796/48980/48880均已退出。此证据验证C14+C16，不验证C17；Build31尚未运行。
- 未关闭/停止：C17动态输入/RequestedMove/残余速度/普通旋转、proxy及ActionCurve/native montage最后帧、未知混合来源仍待统筹门禁。Profile合法零的旧GetMaxSpeed判定、求值失败/Finish/RMS替代（S3b/c）、预测/表现getter仍未整改；MovementSet.h旧“CMC未接校验”注释及C14/C17结构MD/Canvas同步待独立租约，本轮冻结范围禁止写入。七Profile实际资产引用缺口、AnimBP引脚/BlendSpace命名迁移及Run实机表现仍未验收，GA_Dodge/Gadget保留占位。四文件冻结交回，不自动后续，不标记完整任务完成。

## C19 / Build31-R1：完整类型编译短修静态交回（2026-10-01）

- Build31真实失败（统筹交回，非本组长运行）：完整Editor构建11计划actions，UHT8.3672074秒/3 generated，总87.43秒/UBA72.42秒、exit6；三个Unity单元因CMC.h:349内联HasAcceptedMovementSet只见MovementSet前置声明，IsValid参数到const UObject*转换报C2664。未链接新运行时/Editor DLL，未跑自动化，Report31未建立；统筹238源码及14保护hash前后保持。这取代C17记录当时“Build31尚未运行”的历史状态，不代表C17运行通过。
- 唯一修复：公共头仅将HasAcceptedMovementSet内联体改为原private/const签名声明；cpp利用原有GGYGOMovementSet.h完整类型include定义同一函数，唯一语句`return IsValid(MovementSet.Get());`。没有在公共头加配置全头、改变签名/宏/准入或门禁/清理/诊断规则，也未改tests、资产、Obsidian或全局记录。
- 静态证据/架构：完整两source diff只有声明与函数体搬移；内存逆向后h SHA256精确恢复`D4F4DF1F4E01D7B87B478F291CDE547165F01430727CAA2DC48438982440573E`、cpp恢复`720B0683C479626D15D88D565420F2D0CDFBC243D42DD10FF8F25C43268DE576`。13个已登记保护源码hash保持，函数唯一且完整类型include在定义前；UTF-8无BOM/LF、最终换行/无尾随空白。无新增状态/资源、循环依赖、接口或生命周期变动；两记录原C17入口字节前缀保持。
- 生产已冻结：h 569行/25110字节，SHA256 `E425B97F8EB3FE34EA501D729B469FBD0064EC8290A14A2F7C43730D4DF636B4`；cpp 1701行/62012字节，SHA256 `372A619755F745770F2DAF4ACC77FAA338B18C663C7F26388F0BE50EB238782E`。生产冻结后才补失败/修复记录，两记录只追加，最终四hash随交回。
- 未验证/停止：本组长未运行UE/构建/Git/代理；Build32待统筹独立安排，静态修复不冒称编译或运行通过，不借旧DLL验收。C17动态边界、S3b/c、预测/getters、图文同步及资产/AnimBP/Run缺口保持未关闭，GA_Dodge/Gadget继续占位。本四文件冻结交回后立即停止，不自动下一步。

## C21 / S3a-2-R1：ActionCurve阶段资格静态交回（2026-10-01）

- Build32有限事实（统筹交回）：GGYGOEditor真实Succeeded，7 actions/41.25秒/UBA38.31秒/exit0并链接新运行时和Editor DLL；报告14:40:13北京时间为64叶62 Success/2 Fail，SHA256 `DFCE3543D4F570EB551BE3EC744589EB875671844635365DB37B077D2E0ABBFC`。Movement旧AuthorityAndMapping Success，但ActionMotion.TimingAndOwnership自然结束释放转向一处断言Fail；UE23112 exit0已退出，统筹238源码及14保护hash保持。C19已实际编译，C17只有旧回归部分证据，此报告不验证后写C21，也不关闭Run/资产/网络边界。
- 根因与范围：旧夹具未SetMovementSet，直接把未Prepare的Pending源时间推至Duration并调用Before/RequestDirectMove/PhysicsRotation，未走native Cleanup/Prepare/Apply；同时原共用资格不区分Pending结束与Current最后应用帧。统筹仅授权CMC.h/.cpp及10两记录四文件，C22配置前置与真实原生阶段夹具适配另步，旧测试及资产未写。
- 唯一实现：原struct/实例名/100 priority/Override身份保持。Pending仅未Finished且未Marked可接受；Current未结束可接受，已结束/Marked仅其Prepared与原生group HasOverrideVelocity同时成立可接受。身份仍是每个源自己的检查，group bool或数组存在单独不能提供豁免；native最后帧无local token也可保留。两个既有消费者HasIndependentGroundRootMotion/PhysicsRotation及本地token全文保持，因此同一资格同时收紧缺配置豁免与转向冻结；无accepted且仅已结束Pending的普通请求继续被拒绝。
- 实际native依据：`F:/UE_5.8/Engine/Source/Runtime/Engine/Private/GameFramework/RootMotionSource.cpp` 1346/1353/1419/1424清理Current和Pending的Finished/Marked；1445/1449将Pending转入Current，1608/1610实际Prepare并设Prepared，1638/1641设group Override。1321–1323的HasOverrideVelocity直接返回该native bool；1687–1696累积Current最高优先级Override，不在累积时排除Finished/Marked，故Prepare中结束的Current仍是最后应用帧。`.../Private/Components/CharacterMovementComponent.cpp` 2852 Cleanup→2874 Before→2941 Prepare→3034物理应用→3046 Rotation；native Prepared语义见RootMotionSource.h:47–48。无需新增应用时钟或第二事实来源，未发现需要扩大本契约的分支。
- 静态证据/架构：完整两source diff只含h一条资格注释与cpp唯一资格函数；内存逆向精确恢复C19 h `E425B97F8EB3FE34EA501D729B469FBD0064EC8290A14A2F7C43730D4DF636B4`、cpp `372A619755F745770F2DAF4ACC77FAA338B18C663C7F26388F0BE50EB238782E`。14个Movement已登记保护源码（含旧ActionMotion测试）hash保持；函数内仅native bool局部快照及立即执行predicate，无成员/资源/状态写入、跨模块接口或依赖改变。反射/声明/include、未知RMS/GA/非地面/求值/预测/getters全文保持；UTF-8无BOM/LF、最终换行/无尾随空白，两记录C19入口字节前缀保持。此证据为源码核对，未运行动态专项。
- 生产已先冻结：h 569行/25145字节，SHA256 `E6862BDB5F2C40B5987452B177AEE8E65F40C9C05A88938740282C93204523F6`；cpp 1711行/62589字节，SHA256 `EB0D09B3A88547FB252DD0E2E5575A52DA579B0DEAD30047D4F4D2BA21C9940D`。随后两记录仅追加，最终四hash随交回。
- 未验证/停止：C21未编译/UE/自动化，未实际证明Pending取消、Current Prepared+Finished/Marked最后帧、proxy及无配置普通输入/RequestedMove旋转/位移；C22未授权/未写，不弱化或宣称旧自然结束/旧token/下一动作断言通过。S3b/c、预测/getters、既有图文同步和资产/AnimBP/Run缺口仍待独立范围，GA_Dodge/Gadget占位。四文件冻结交回根审查后停止，不自动C22、不运行UE/构建/Git/代理；Obsidian及全局记录本轮禁止写入。

## C22 / S3a-T2：既有ActionMotion夹具静态交回（2026-10-01）

- 授权/范围：根独立逆向接受并冻结C21后，仅旧GGYGOActionMotionTest.cpp及10两记录三文件适配，仍一个既有TimingAndOwnership入口。只apply_patch写入，C21生产、sharedTestTypes、所有其它源码、资产/Obsidian/全局记录冻结；没有UE/构建/Git/代理操作。
- 合法配置：真实NewObject MovementSet在绑定前显式false、RotationYawRate=360；创建非循环Duration=1 TurnBack及四条覆盖[0,1]有限线性曲线，Speed500→0、DirX1、DirY0、Yaw0→180。false正常模式按现Validate允许其余Profile留空，但赋值TurnBack必须通过真实校验。初次绑定、取消场景后重绑及独立owner夹具绑定均严格TestTrue真实Set结果，不伪造成功或将缺曲线错误改成fixed业务。
- 未准备取消Pending：原First经公开End取消后，观察其仍在Pending/Marked且未Prepared；公开Set(nullptr)合法解绑并严格确认false/null配置与无native Override。真实RequestDirectMove并给旧平面速度，经公开ApplyRootMotionToVelocity→CalcVelocity→PhysicsRotation检查速度清零/RequestedMove拒绝/朝向不变，源仍在Pending说明没有用清组替代拒绝。唯一预期日志为完整组件/Owner路径、unbound/None来源/原原因的Plain/Error/Exact/1，非regex；多个入口应只有一次真实周期诊断，没有直接写诊断或RMS flag。
- 纯自然过期场景：Second保留原新token/旧token断言，捕获真实Pending源；native Group Cleanup移除取消First→Before→Group Prepare(Profile Duration)得到Current/Prepared/Finished及native Override→公开Apply验证Mesh2尺度下完整区间200cm积分→原无GA timer自然过期可观察断言→同帧Request/PhysicsRotation仍保持入口朝向。下一move 0.1秒依次Group Cleanup→Before自动CleanupFinishedActionMotion→Group Prepare→Apply→原Request/PhysicsRotation，保留原Yaw>1恢复与真实下一Begin非INDEX_NONE断言。全自然链没有显式End(Second)，源时钟和结束flag均由native Prepare推进，自动owner清理不能被显式GA清理替代。
- 显式owner清理独立场景：另Spawn真实ACharacter及其独立CMC，绑定同一只读合法配置，Mesh尺度显式1；真实Begin取得handle、实际源经Group Cleanup→Before→Prepare得到Prepared+Finished→Apply验证100cm积分。随后仅该独立CMC公开End真实handle，观察Current Prepared+Finished+Marked及native Override仍在，再Request/PhysicsRotation严格保持先前朝向。此场景检查已释放owner的准备末帧资格，完全独立于Second自然自动清理；没有fake UObject、protected helper或新的状态/时间写入。不是网络proxy或位置碰撞全流程验证。
- 静态证据：原21处TestNotNull/TestTrue/TestFalse/TestEqual调用及期望逐字保持，当前45处检查仅新增24处场景前置/结果，并非45测试叶或通过数。原两速率Standalone积分整段保持；内存逆向新增include/配置/取消场景/native尾段后准确恢复原cpp SHA256 `BBFD34485BD0E4F001BD972DAD55E8A062E43054075F044B7F179EC3FE8E39E8`。完整cpp diff及两条native相对顺序、自然链无End(Second)、无手写SetTime/status/组数组均核对；15个Movement保护源码（含C21 h/cpp、sharedTestTypes）hash保持，UTF-8无BOM/LF、最终换行/无尾随空白，两记录C21入口前缀保持。
- 原生/API依据与架构：RMS Group公开Cleanup/Prepare（Engine RootMotionSource.h:801/809），真实Prep设Prepared/Override（RootMotionSource.cpp:1608/1610/1641），原生CMC的2852 Cleanup→2874 Before→2941 Prepare→3034物理应用→3046 Rotation。公开RequestDirectMove（CMC.cpp:4024/4038）产生实际请求状态，ComputeOrientToMovementRotation:6611–6613使用该请求转向；CMC项目Apply/Calc/PhysicsRotation公开覆写，无新增访问API。两个测试角色各自拥有CMC/源生命周期，配置/动作资产只读共享，World原RAII统一清理；不新增生产状态机、资源接口、时钟或依赖。
- 冻结/未验证：测试cpp已先冻结，221行/14022字节，SHA256 `75ED3F333D57D08309D27E3342E60DC997A27344BFC63B2EB1D1DA85D7B3DED1`；先前FEBD89FE…显式End混入自然链的中间版本已撤回修正，没有编译/运行该版本。两记录仅追加，最终三hash随交回。C21+C22尚待统筹Build33新DLL实际编译/运行，本组长未运行UE/构建/自动化/Git/代理，不能用Build32旧失败或静态核对称新断言通过。S3b/c、预测/getters、既有图文与资产/AnimBP/Run缺口保持未关闭，GA_Dodge/Gadget占位；三文件冻结交回后停止，不自动后续。
- 顶端状态收尾与停止：统筹在本三文件原租约内追加要求更新顶端过期状态、标明S2历史；只修正顶端状态/标题并增加历史说明，S2至C21原结果正文保持。本轮实际磁盘前缀已变化，C22前缀保护证据改为内存逆向这些明确顶端改动后精确恢复原C21入口前缀hash，不冒称磁盘字节未变。测试/生产源码在统筹Build33开始前已冻结，本次仅记录收尾、不等待33结果；最终三文件hash随交回，完成后立即停止写入。当前编译/运行仍仅统筹执行，本记录没有33通过结果。
- 随后Build33实际验证（统筹执行/交回，已只读核对build日志与报告）：完整Editor Succeeded，10 actions/33.74秒/UBA29.06秒/exit0；新运行时/Editor DLL均真实链接。报告`Saved/AutomationReports/ModuleRepairGate_20261001_33/index.json` SHA256 `624287915CDBC1C3E7D7D4857FF9E50973EE15D6D8374F1439CF46365B5EA4E3`，2026-10-01 07:51:34 UTC（15:51:34北京时间），65叶64 Success/1 Fail，其它状态0，总0.8156763911247253秒。`GGYGO.Movement.ActionMotion.TimingAndOwnership`实际Success/0.009702898561954498秒/entries=[]/errors=0/warnings=0；`GGYGO.Movement.Locomotion.AuthorityAndMapping`实际Success/0.009144198149442673秒/entries=[]/errors=0/warnings=0。该新DLL叶执行覆盖本C22实际绑定、取消Pending拒绝与两条独立末帧/自然自动清理检查，不依赖Build32旧报告。
- 唯一失败与验证边界：`GGYGO.Editor.Animation.FloatCurveSnapshot` Fail，`AnimationCurveSnapshotTests.cpp:67`为`SnapshotOutside.ActualFixture.Keys[0].LeaveTangent`真实Model夹具前置错误（errors=1/warnings=0），与Movement无关，本范围不修。统筹交回UE41716 exit0已退出、240源码/14保护hash保持；真实日志verbosity 51 Error/2 Warning，整体并非全绿，不能把叶entries=[]推广为全日志无诊断。Input17未重跑，网络proxy/预测、位置碰撞全流程、生产资产/AnimBP/Run及S3b/c未完成。收到33结果后只更新本两记录，测试75ED3F33…与C21生产源码仍冻结；最终三hash交回后停止写入，不运行UE/构建/Git/代理或自动继续。

## C26 / S3b-I1：成功曲线速度资格静态交回（2026-10-01）

- 前置门禁与授权：统筹交回第34 Editor Succeeded/10 actions/29.34秒/UBA26.05秒，普通65叶全Success，C22/AuthorityAndMapping/C20保持Success；R3仅Walk_Start完整公开DTO四曲线86/86/2/2键与精度实读通过，不证明七Profile/资产/Run。UE39308/43312/13868各exit0已退出，统筹242源码/14保护保持。本结果早于C26写入，不是本步编译或专项。台账/排程C26实际核对后，在10 Subleases登记唯一目标、四文件范围/入口hash、依赖、验收及停止点，再写生产；其它源码/测试/资产/Obsidian/全局记录冻结。
- 可复核根因：Profile纯求值成功在候选数据完整校验后写bHasCurveSource=true，包括合法零速；失败返回false并清空输出。旧GetScaled用HasUsableSpeed正速阈值过滤，旧IsCurveDrivingSpeed再按正数阈值判资格，GetMaxSpeed因此把真实成功0/极小正值/零Scale结果换成固定gait。本步拆开成功资格与数值幅度，是实现契约修正；复用既有成功标志与CMC状态，无需新增状态或改变权威归属。WalkRun单侧替代仍会令bHasCurveSource表述某侧成功而非两侧契约成功，不能把本步称完整失败传播修复。
- 逐函数实际变化：IsCurveDrivingSpeed拒绝活动本地Action、无accepted配置、显式false模式、无成功来源、非有限/负Speed或Scale、非有限/负乘积；合法0与极小非负值不受阈值过滤。GetScaledCurveSpeed先查询该资格，成功返回真实Speed*Scale，不用Max钳制；无资格时其数值0仍须配合bool，不成为成功结果。GetMaxSpeed保留CantMove/非地面/无配置入口及原fixed分支，按资格选曲线分支，ForceWalk继续只用原Min上界。header仅更新IsCurveDrivingSpeed/GetScaledCurveSpeed两条契约注释，声明/UFUNCTION/成员/其它函数不变；未改共享HasUsableSpeed及Brake/RMS结束语义。
- 验收边界（静态，未专项）：真实成功0及Scale=0满足资格并返回0；极小正值与正常非零值保留真实乘积；ForceWalk只限上界不把0换成WalkSpeed；显式false资格false且原固定gait行为保持；非法数值/失败来源资格false，不当正常0成功。GetScaled调用IsCurveDrivingSpeed，后者不反调，GetMax同用该资格，无循环。Action/Anim RM原生优先顺序、source生命周期、注册/取消/自然末帧/旋转及预测/动画API全文保持；现有C22/AuthorityAndMapping测试未改，仍须新DLL后验证受影响调用链，不能用静态条件称运行通过。
- 完整静态证据与生产冻结：cpp diff仅三getter函数体，逆向后完整恢复入口62589字节/SHA256 `EB0D09B3A88547FB252DD0E2E5575A52DA579B0DEAD30047D4F4D2BA21C9940D`；h diff仅原262/392两注释，逆向恢复25145字节/`E6862BDB5F2C40B5987452B177AEE8E65F40C9C05A88938740282C93204523F6`。其余声明/反射/状态/函数/生命周期全文保持，14个Movement保护源码含C22旧测试及SharedTestTypes hash保持；UTF-8无BOM/LF、最终换行/无尾随空白。生产已先冻结：cpp 1722行/62767字节 SHA256 `1AD15D3B4FCF36950B620D655B8B9414535C5B4DA65800E06D747B89287896FF`；h 569行/25228字节 SHA256 `00C3B5A3E7DC963403D8D0FC5D67F361B09ABC40CA1983C20974A04DE89D0C7A`，随后只补两记录，最终四hash随交回。
- 架构与必须后续的根因链：CurveMotion仍由CMC既有Locomotion模拟入口产出，Profile保持纯求值/校验，getter只派生读，不新增循环依赖、资源、缓存、时钟、执行器或清理责任。EvaluateLocomotionProfile仍忽略返回值并推进时间；EvaluateWalkRunProfiles仍可能一侧失败取另一侧；GetMaxSpeed无成功来源仍可取固定gait。这些现有失败后果必须下一独立契约根治，明确传播真实错误、阶段拒绝/中止、现有资源清理及一次可定位诊断；不能允许错误伪装正常0或借本步豁免业务兜底。RMS方向/退场内部替代、旧getters非法数值、预测/proxy/完整资产动画接线也未关闭，不自行扩接口或状态所有权。
- 计划核对/未验证/停止：已只读核对计划蓝图与Movement结构、计划、移动流程Canvas及Animation曲线Canvas。旧Profile缺失固定速度说明、运行准入/零值资格状态及Animation旧Tick采样链仍需整体同步；本租约禁止Obsidian/资产/全局写入，图文未完成，须统筹后续独立范围。C26未编译/未专项，测试/生产Run/资产迁移未证明；本组长未运行UE/构建/Git/代理。原历史正文保留，记录顶端更新当前阶段；四文件冻结交回后立即停止，不自动续步。

## C29 / S3b-T1：成功速度消费者专项静态交回（2026-10-01）

- 授权与范围：统筹已接受三文件预检，实际台账/排程C29确认后先在10 Subleases登记唯一契约、精确三文件/入口hash、依赖/前置/严格断言/停止点，再写测试。仅LocomotionMovementTest.cpp原全部检查之后新增隔离段及本两记录；生产、TestTypes、ActionMotion、其它tests、资产/Obsidian/全局记录冻结，不新增用例叶。
- 原问题严格复现：合法零源、极小正速及零Scale必须有成功来源资格，不能因正数阈值改用固定gait。独立配置Walk64/Run512提供明显不同的固定速度；真实Profile常量0、1/32768及128，经EvaluateInterval成功且bHasCurveSource/原速严格确认后，公开SetTestCurveMotion并设本夹具gait，再实际IsCurveDrivingSpeed/GetMaxSpeed检查。使用直接精确相等而非默认浮点容差，极小输出必须精确1/16384，正常输出256；零/极小HasUsableSpeed仍false，未弱化共享Brake/RMS结束语义。
- 正常配置与隔离：所有配置均在绑定前完成，曲线配置七有效引用/正确Loop；ZeroScale=0、false固定模式和MAX_flt有限Scale的独立配置共用只读合法Profile。共五处真实SetMovementSet严格TestTrue，绑定清理后重新注入本夹具样本/gait。ForceWalk真时正常上界64、零仍0，随后公开清除并验证；显式fixed资格false，Walk/Run分别精确64/512，不以缺失/失败触发替代。新增角色/内建CMC在原所有检查之后，原角色/资产/流程不写；原World RAII销毁两个角色/组件，局部样本值及Transient配置沿原生命周期处理，无新增状态或执行器。
- 失败边界严格保留：对已成功128输出调用真实倒序区间Evaluate，要求false且实际错误非空/来源清空，再注入仅检查IsCurveDrivingSpeed=false。MAX_flt Scale在绑定前配置且真实合法绑定，128成功样本产生实际有限操作数/非有限乘积，资格必须false。两失败场景均不调用GetMaxSpeed来期待尚未实现的失败阻断，不把当前fixed退回视为合法成功；没有手写bHasCurveSource、RMS时间/flag或ExpectedErrors/日志过滤。
- 静态证据与测试冻结：完整cpp diff只有原全部检查后119行新增段；内存删除该段精确恢复原166行/9117字节及入口SHA256 `1EA95AE61E1B832DC570A11136D7765C9119C86471824A73773118C1F0805A90`。原29处Test调用/期望/容差、helper/角色构造及原流程全文保持；当前64检查仅新增35处前置/结果，仍一个既有AuthorityAndMapping叶，不能当通过数。三个成功与一个失败真实Evaluate、五真实绑定及精确消费/配置前置/ForceWalk清除已静态核对；UTF-8无BOM/LF、最终换行/无尾随空白。测试先冻结：285行/16888字节，SHA256 `59D81A4C651D43523394D9C0B58C87C82BAAF6C82282BD4BDFDC2676E5D1CDC3`，随后仅补记录，最终三hash随交回。
- 保护与架构核对：15项Movement保护源码hash保持，C26生产cpp `1AD15D3B4FCF36950B620D655B8B9414535C5B4DA65800E06D747B89287896FF`/h `00C3B5A3E7DC963403D8D0FC5D67F361B09ABC40CA1983C20974A04DE89D0C7A`、ActionMotion `75ED3F33…`、TestTypes `78920CCD…`均不变。无需新测试头/生产API/UCLASS，复用公开既有接缝，只隔离样本消费；不增加跨模块依赖、循环、缓存、时钟、资源或调度器，不改变原资源清理。不是完整Locomotion求值推进、native物理/Action末帧、网络预测/proxy、资产或AnimBP/Run动态证明。
- 根因后续与图文/停止：完整Evaluate失败传播仍须冻结成功/正常无需求/失败结果及有效期、WalkRun两侧必需契约、失败后的阶段推进/消费者阻断/诊断与自有资源清理；忽略失败、借另一侧Profile、无源固定速度以及RMS内部替代尚未修复，不能用本成功资格专项关闭。已只读核对Movement移动测试关卡说明，其历史PIE/曲线跑速证据不验证本C26/C29；C26已登记的结构/计划/Canvas同步缺口保持。本租约禁止Obsidian/资产写入，图文未同步，生产Run/七Profile未完成。C26/C29未编译/未专项，本组长未UE/构建/Git/代理；三文件冻结交回后立即停止，不自动续步。

## C30 / S3b-T1-V1：第35次新DLL有限动态验收（2026-10-01）

- 授权/保护：统筹已实际全文/hash接受C29，原29检查保持，测试SHA256 `59D81A4C651D43523394D9C0B58C87C82BAAF6C82282BD4BDFDC2676E5D1CDC3`冻结。仅本两记录可同步当前状态/追加证据，原历史正文及失败链保留；所有source/tests/资产/Obsidian/全局记录继续冻结，不借记录授权新实现。
- 实际构建（统筹执行，已只读核对日志）：完整GGYGOEditor Succeeded，6 actions/34.99秒/UBA32.04秒/exit0；真实链接新运行时DLL，本次日志没有新UHT或Editor DLL重链接，不能扩大证明范围。本结果晚于C26/C29写入，与第34次旧DLL结果分开。
- 实际报告（已只读核对）：`Saved/AutomationReports/ModuleRepairGate_20261001_35/index.json` SHA256 `F2DFBCF244512B11EB669D29DFAAD2C21310103E9D9EDA74D098B5ED8A1718A6`，reportCreatedOn=2026.10.01-09.37.52 UTC（北京17:37:52），65 Success/其它计数0，总0.7469504475593567秒；所有叶errors/warnings0，路径与34保持（统筹核对）。AuthorityAndMapping Success/0.00962350144982338秒/entries=[]，ActionMotion Success/0.010235998779535294秒，C20 FloatCurveSnapshot Success/0.008245799690485秒，三个叶均0错误警告。C29新增35处检查实际随原29处运行，64检查仍属一个既有叶。
- 已关闭的有限契约：真实合法Profile成功样本0、极小正速及合法Scale0均不被速度阈值当失败换成固定gait；正常128*2、ForceWalk上界64/零、显式false Walk64/Run512及失败输出/溢出资格false通过实际IsCurveDrivingSpeed/GetMaxSpeed消费断言。原29检查、ActionMotion旧末帧/所有权回归及共享HasUsableSpeed判据保持。不由此证明失败时GetMaxSpeed阻断，因为C29明确没有为未修路径设置该期望。
- 真实诊断与保护边界（统筹交回）：原始49 Error=Smoke13+Damage预期34+Bake预期2，2 Warning为DDC路径和Python枚举重名；报告叶0诊断不等于全日志无诊断。UE40532 exit0已退出，242源码和14保护在构建/回归保持，没有保存资产；本组长未运行UE/构建/Git/代理。七Profile生产引用仍null，完整失败传播/单侧或固定替代/RMS内部方向和非法数值、真实物理/联机预测/proxy、资产/AnimBP/Run及图文同步仍未验，不把本消费者Success当根因全关闭。
- 两记录冻结与后续：仅顶端当前状态及本追加段变化，历史失败/未运行边界保留为当时事实；最终两hash随交回后停止写入。随后按统筹已登记C31只做整体失败传播零写入预检，先明确来源/有效期/失败时钟及唯一消费、职责拆分与需用户决策的架构/共享接口影响；没有生产/测试/资产/Obsidian/全局写权，不自动实施。

## 本地 CurveRMS 实际区间：有限源码接受与记录 M1（2026-10-03）

### 授权、证据与源码版本

统筹仅授权本 Validation 与 `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md` 两份既有记录；文档 M1 写前已在 Subleases 登记唯一目标、精确文件、基线、只读依赖、顺序、断言和停止点。入口 hash 为本文件 `D40D80B2385C32699FC4542921AE14640528B6551B850BE1D8B98B96AEA8BC8C`、Subleases `3004A78EF4D94AF1C966DF7DDBEBB87078AD82509564243D32E945210882C69D`，与 [文档租约基线](../../../Saved/ValidationRecords/MovementActualIntervalRecords_20261003_LeaseBefore.json) 实际一致。所有源/测试、其它记录、Saved、资产、引擎、Obsidian 和全局入口继续冻结，本步不执行 Build/UHT、UE、Automation、Git、矩阵或子代理。

[统筹有限接受证据](../../../Saved/ValidationRecords/MovementActualInterval_20261003_RootAcceptance.json) 记录 sourceTurnId=`01a101fa-6515-7f91-9d21-88d0b153facc`、handoffTurnId=`01a10225-ec0c-7991-a8c8-f3d0f27151f5`、rootAcceptance=`finite_static_accepted_uncompiled`、ownerExplicitlyFrozen=true，acceptedAt=`2026-10-03 14:29:50 UTC`。四源码完整 hash 见 Subleases 本地 CurveRMS 段；该 JSON 独立匹配相同版本。统筹回读 RMS h/cpp 全文及 CMC Origin/实际区间/Prepared 提交/Stage、SavedMove/Before、挂载/退役和回放出口，scopedDiffCheckExitCode=0。

### 已实现且有限静态接受的契约

| 契约 | 实际实现与静态证据 | 动态状态 |
| --- | --- | --- |
| 原 Origin/请求 | Stage 保存原候选与输入，Origin 含原 issuer、Binding/InputRequest、执行序号、配置与片段/时间锚点；HasCurrent 同时核对同一引用与当前资格，挂载不凭名称/LocalID认领其它源 | 未运行身份/后继场景 |
| 实际原生区间 | CMC Prepare 使用 Source.GetTime、SimulationTime、MovementTickTime 及固定锚点，在实际区间调用既有纯求值；TurnBack 时间按实际模拟推进 | partial/zero/catchup 未运行 |
| 速度/唯一提交 | 沿用端点速度样本及实际 sim/tick 比例，非精确位移积分；CMC Consume 同一 Prepared 引用一次，RMS 只安装返回速度/原生时间与结束标志，没有 Profile 求值 | 同帧提交/应用未运行 |
| 原 SavedMove | PostUpdate 保存原输入/Prepared，相关 move 不合并；PrepMoveFor 在 native Super 前安装上下文，校验 SavedRootMotion Current/Pending 来源；Before 消费原准备结果，不再推进一次整帧时钟 | 原生重算/保留结果、后继隔离未运行 |
| 原 FAILED/退场 | Report 只向匹配原当前序号进入既有失败入口；失败方法体保持，FAILED 不被回放恢复；Retire 精确原 Origin，旧贡献不会被认作后继成功结果 | 同帧失败拦截及后继保护未运行 |
| 执行与清理 | 原 CMC/原生碰撞仍执行胶囊位移，独立 Action/动画 Root Motion 优先级和正常末帧动量/结束语义保持；Reset/EndPlay/回放结束清理原资源与派生上下文 | 清理、离地、独立根运动交互未运行 |

本记录的“接受”指上述版本的有限源码核对，不是编译或专项通过。原非 RMS 路径、跨模块迁移及完整失败传播不能由这一个源原子自动标完成；用户要求保留的旧 TurnBack 业务/资产曲线没有在本步另造一套。

### NetSerialize 与未关闭网络边界

原 NetSerialize 基类及 BaseYaw/SpeedScale/bEndOnZeroSpeed wire 字段保持；加载时清除本地 Origin、Prepared 与诊断节流状态。Clone 保留本地原共享引用，Matches/UpdateStateFrom 对本地 Origin 不匹配返回拒绝；源 Prepare 对缺失/不匹配本地 issuer 明确诊断并退场。**当前只有本地签发来源可认证，网络导入没有可证明 Origin。** wire 未增加字段不等于已证明原生网络匹配、重放、服务器校正或 proxy 兼容；完整 authority/proxy 网络链继续开放，不通过名称、LocalID或当前对象猜测填入原授权。

### 历史失败、资产与用户补充

- 原 C30/第35次65叶Success只覆盖当时成功速度消费者及旧回归；Gate54 的82无警告成功、2带警告成功、1Fail为写前历史，不能套用到这四源。FAILED 两生产 Error、请求3标记、旧失败/容差和诊断记录保留，没有重跑、排除场景、弱化断言、降低日志级别或增加过滤来宣布通过。
- 正式七 Profile 的创建/引用接线没有完成，既有回读的 null 引用及源码与资产分阶段状态继续可见；当前版本 Run、正式 Hero/物理输入与生产资产没有新 UE 冒烟证据。源静态接受不能证明这些缺口已关闭。
- 用户实际要求“Gadge”先占位、后续集中接 GAS 再说明，并优先查看蓝图/旧实现与名称。已交回的是只读调查：当前磁盘 ABP 图/引脚中 GaitBlendY 接 WalkRun BlendSpace X、Entry 进入 WalkRun，TurnBack/Stop 既有分支仍在；规范 WalkRunBlendAlpha 与旧序列化兼容字段分开，旧轴显示名尚未保存修正。既有 GA_Dodge/Gadget 占位未接新 GAS 调用方。没有保存/改名资产或新 UE 运行，这些结论与源原子证据分开。

### 本文档原子的验收与停止点

文档 M1 只更新两记录当前入口并追加本地源结果/验证边界，原历史正文逐字保持。两记录已有限保存回读：两基线历史段一致，接受 JSON/租约链接有效，四源 hash 与冻结交回一致，UTF-8 无 BOM、LF 和末尾换行保持，无冲突标记或行尾空白；最终两 hash 随交回并冻结。无新编译、动态或资产结果，不声称完整 Movement/Run/网络完成。

Obsidian 四份结构/计划/Canvas 及全局入口未在本租约更新。按项目同步要求保留为明确未完成项，由统筹下一独立租约安排；本步已关闭两记录写权，不自动继续图文、源码、测试、UE、Git或资产操作。
