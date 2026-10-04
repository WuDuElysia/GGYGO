# 第10批 Movement / D5 子租约

更新：2026-10-03。本地 CurveRMS 实际区间四源已编码交回冻结，统筹有限静态接受：CMC 保存原 Origin/输入，在原生实际 SimulationTime 区间唯一求值与提交；RMS 只消费结果，SavedMove 保留原输入/结果，失败只进入原当前请求门禁。旧 NetSerialize wire 字段保持，加载时清除本地 Origin/Prepared；网络导入来源仍未认证。身份消费者 E1 的编码/静态交回事实保留。上述新源尚未编译或动态验证；既有 Gate54 的82无警告成功、2带警告成功、1Fail及 FAILED 两生产 Error/请求3标记保留为历史，不证明本步。正式七 Profile 创建/接线、当前版本 Run、物理输入/正式 Hero、网络与 Obsidian 图文仍开放；Gadge 保留占位，蓝图/旧名称调查只读。最新有限状态以末尾“本地 CurveRMS 实际区间”源结果及文档 M1 为准。

### 当前状态

- 本地 CurveRMS 源原子状态为 `finite_static_accepted_uncompiled`；四个独立 hash 与冻结交回匹配，统筹范围 diff 检查 exit0。本两记录已保存回读并交回冻结；partial/zero/catchup、同帧失败/SavedMove 后继隔离、正式 Profile/Run及网络没有新运行结果。
- 以下 Build32/34/35 为历史构建/回归结果，其当时失败与范围保留，不覆盖本地 CurveRMS 新源原子。
- S2 统一校验已接入 CMC 绑定；C17 地面准入与 C19 完整类型短修已进入 Build32 实际成功构建。Build32 为 64 叶、62 Success/2 Fail，旧 ActionMotion 自然结束转向断言仍 Fail，详见末尾 C21 历史记录。
- C21/C22有限新DLL验证已由统筹接受，原21处检查及容差、纯自然清理链与独立显式owner末帧链保持；第34次旧叶继续Success。该证据早于C26，不验证本步速度资格，也不证明完整游戏/网络场景。
- 第35次完整Editor构建与新运行时DLL真实回归已覆盖C26/C29：同一既有AuthorityAndMapping叶Success，原29检查/容差与新增消费者检查保持。仅证明成功样本速度资格及消费契约；Evaluate失败/单侧Profile/无源固定速度/RMS内部替代仍须根治，七Profile引用仍null，生产Run/预测/proxy与图文未验，GA_Dodge/Gadget占位。

以下为各步骤在当时交回时的历史记录；“尚未构建”“当前排程”“CMC未接”等只描述该历史阶段，最新状态以上文及末尾本地 CurveRMS 段为准，原历史结果不改写。

## 历史原子步骤：10-StrictConfig-S2

- 授权来源：统筹核对 S2 零写入预检并确认第26次构建/Automation窗口全部退出后，2026-09-30 授权四文件；当前有效排程 C11。Movement 组长直接执行，无代理。
- 状态：先登记四文件基线再实现，已完成四文件写入与静态复核并冻结；S2 尚未构建/运行，写入权限交回。
- 唯一结果：新增纯 `ValidateMovementSet(FString& OutError) const`；编辑器 IsDataValid 只适配同一规则。16非废弃数值必须有限并满足已确认范围；曲线模式七引用必需且Loop匹配，曲线内部校验委托冻结 Profile。
- 唯一写入者：`GGYGO｜Movement 模块`，会话 `01a0e5b5-83e6-70b3-9e67-c9e8547586a4`。
- 精确文件与入口 SHA256：
  - `Source/GGYGO/Character/Data/GGYGOMovementSet.h`：`70A0A84744CBD2B53867F38F7B39B4D3D2BD8469356BA9951C99D895532AE205`，10660字节。
  - `Source/GGYGO/Character/Data/GGYGOMovementSet.cpp`：`A7172EF53E1C02BFE81F0E70B508F9C71DB9C8F9E4AEBBF95AD6C1372B652EB3`，2102字节。
  - `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md`：`BEFCB1633E805454321AAB06B0F98E202408C837E85F1E7118F46128F488CA0B`。
  - `AAADocs/Modules/Movement/Module_Repair_10_Validation.md`：`8B491548BC1064893886D970E5FEE923916D6674F183BE8AE899C58F01CAB718`。
- 只读依赖：Profile `.h/.cpp`/ValidateProfile、CMC/RMS、MovementTypes、旧 Movement/TestTypes、新 StrictEvaluation 测试、第26次实际报告及 Movement 结构 Markdown/Canvas。
- 冻结契约：false 固定模式合法并允许空 Profile；已填引用仍校验。零速、零Scale、零Blend、零TurnBack上限等已确认零值不替换为默认；废弃且无消费者的 MaxCurveDrivenSpeed 不校验。校验成功清空旧错误，失败含 MovementSet路径/字段/原因及嵌套Profile原错误，不修改对象、不记录运行状态或增加日志/缓存。
- 顺序：登记基线 → 新纯校验/编辑器适配与准确注释 → 只读静态/保护复核 → 完整四文件 diff/hash 交回并冻结。
- 非目标：现有 GetSpeedForGait、GetSanitizedWalkToRunHoldSeconds、GetProfileForMotion 的签名/实现及所有消费者保持；不接 CMC/RMS/预测、不写测试夹具、资产、Obsidian 或其它文件，不运行 UE/UBT/Git，不创建代理。
- 验收断言：16字段有限/范围、曲线模式缺引用/循环错误/内部错误返回明确失败；false本身不失败且可空引用；合法零值原样保留；success清旧错，failure无数据修补。旧 getter 全文与接口保护，不把未接入写成已接入。
- 停止点：四文件静态冻结交回；S2 未构建/运行，专项与 S3、架构图文同步须后续独立租约，不自动继续。
- 实际结果：11项非负值与5项有界值均先检查有限性；7项引用以曲线模式要求非空，两Loop=true、其余=false，已填项先检查对象/Loop再委托唯一 ValidateProfile 调用。false允许空引用且不绕过已填引用校验；OutError入口清空，失败仅写调用方错误字符串。
- 旧链保护：在内存中移除新增两函数与编辑器include，cpp完整恢复入口2102字节及 SHA256 `A7172EF53E1C02BFE81F0E70B508F9C71DB9C8F9E4AEBBF95AD6C1372B652EB3`，未实际回滚。header除注释与新增两声明/编辑器guard外原有代码一致；26组 UPROPERTY/声明/默认值/元数据逐字保留。旧构造、命名空间、三getter实现和签名均未改。
- 静态复核：16字段名/源值与7引用/Loop清单、括号/预处理、UTF-8无BOM/LF、行尾空白和成员tab缩进已核对；新接口唯一，生产运行时无调用者，只有编辑器适配调用。无UE_LOG、曲线key校验复制、对象修改、缓存或新运行状态。Profile/MovementTypes、CMC含RMS、采样器、3测试相关文件与Movement结构MD/Canvas共12个只读hash保持入口。
- 源码最终 SHA256：`.h` `D5509274F399B10BEF6CB1D2D677C87EC7923231EA1688DB0923094DD82C183D`；`.cpp` `E30485A826AF150C72CFA94D69ACF125AF188D4B8BE5F1FF38175745D5E53ABE`。两记录最终hash随完整非Git diff交回，避免自引用。
- 当前缺口：CMC仍未调用ValidateMovementSet；旧非法时间回1.5/上限截断、负速钳零、缺Profile固定速度与单Loop替代等仍存在。S2只增加纯校验和编辑器适配，不能作为运行链严格配置或Run恢复证明。第26次门禁早于S2源码写入，不覆盖S2。
- 架构核对：状态/执行仍归CMC，数值和引用规则归MovementSet，曲线内部规则归Profile，无新增循环依赖或重复生命周期。已只读核对Movement结构MD与Canvas的set/cmc节点；缺ValidateMovementSet/IsDataValid、模式与遗留缺口说明，待统筹安排独立图文租约同步。本范围明确禁止Obsidian写入，图文同步未完成，不能标整批完成。

## 已冻结专项：10-StrictConfig-S1-T1

- 授权来源：统筹核对六场景只读预检后，2026-09-30 授权三文件；第25次构建、旧叶 Automation 与 Readback25 均已退出。Movement 组长直接执行，无代理。
- 状态：三个文件已冻结并由统筹根审查接受；第26次完整构建及 StrictEvaluation 叶实际 Success，写入权限交回。
- 唯一目标：一个原生 Automation 入口验证纯 Profile `EvaluateInterval` 的明确失败、完整输出清空及合法零速成功，不改变生产规则。
- 唯一写入者：`GGYGO｜Movement 模块`，会话 `01a0e5b5-83e6-70b3-9e67-c9e8547586a4`。
- 精确文件与入口 SHA256：
  - `Source/GGYGO/Character/Tests/GGYGOLocomotionMotionProfileTest.cpp`：新增；入口确认不存在，禁止覆盖其它测试。
  - `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md`：`0741615945D68D25356E761ACE2F017FE1D9C6189D3AA312D139260CE6A5A211`。
  - `AAADocs/Modules/Movement/Module_Repair_10_Validation.md`：`C1A6EF3C66CD4A3FFEDA5A7B9B9DB8E504CAA9B74A03C64F22AE941552CF7926`。
- 只读依赖：Profile `.h/.cpp`、`GGYGOMovementTypes.h`、既有 Automation 命名/宏，以及 UE 5.8 `RichCurve.h/.cpp`、`CurveEvaluation.cpp`、`AutomationTest.h`、`UObject/StrongObjectPtr.h`。
- 冻结接口：现有 `EvaluateInterval` 与 `ValidateProfile`；Profile 入口 hash 分别为 `.h` `26FF4A2649C4ECD8141E6E86540EF2B9D232DF2A8F4E4D0EA65BA2F237943857`、`.cpp` `16216760DD9C573CECC1DD8E060E11B80F027BB650FF5B10DC341D71415FD5DB`，本步不得变化。
- 顺序：登记范围 → 新增单入口六场景 → 静态复核/记录 → 三文件完整 diff/hash 交回并冻结。
- 验收断言：负键、Cubic/User/WeightedNone 正键中点负插值、缺 Yaw、正速零方向均明确失败；合法零速零方向成功；同输出成功后倒序失败无残留。真实 `FRichCurve::Eval(0.5)` 先断言约为 -1；失败逐项检查12成员18标量，不调用 Reset 生成期望值；错误具体且覆盖旧错误，成功清除旧错误。
- 资源/生命周期：Transient Profile 由 `TStrongObjectPtr` 持有；无 World、GI、测试 UCLASS、第二框架或日志过滤。
- 非目标：生产 Profile/CMC/RMS、既有测试、资产/蓝图、Obsidian 与全局记录均冻结；不运行 UE/UBT/Git，不启动 S2–S7，不补全 RichCurve 元数据矩阵。
- 停止点：三个文件完整 diff/hash 与静态复核交回后冻结；新专项构建和实际运行由统筹安排，不以旧叶成功代替本步结果。
- 实际结果：新增220行、10692字节的 UTF-8无BOM/LF 测试文件，唯一入口 `GGYGO.Movement.Locomotion.Profile.StrictEvaluation`；六场景、五个失败调用，全部失败共用18项显式零/false断言。成功后仅为生产输出始终为零/false的 PositionDelta 与 bHasPositionDelta 加调用方哨兵，注释明确来源。
- 原生夹具：两端键值均1、时间0/1；Cubic/User/WeightedNone，首键到达/离开切线均-8、末键均+8。SetKeys 会调用 AutoSetTangents，已对照引擎 User 分支；运行时先检查切线保留及真实 Eval(0.5)≈-1，并确认 ValidateProfile 成功，未满足时直接失败停止。
- 静态复核：18项字段清单、1入口/6场景/5失败调用、括号和预处理边界、编码与行尾空白均核对；helper/入口名称在 Source 中唯一，避免 Unity 匿名命名冲突。已核对 TStrongObjectPtr 移动/解引用与原生 float/double/FVector 断言重载；零容差的原生比较允许精确零。
- 构建边界：统筹交回第25次真实 Succeeded（4 actions、13.08秒、exit0），59个既有正常叶 Success；该构建与旧叶执行均早于本测试文件创建，不是新专项结果。本组长未启动 UE/UBT/Automation/Git。
- 后续实际验证：第26次构建 Succeeded（6 actions、85.06秒、exit0）；常规60 Success、全部叶errors/warnings0。StrictEvaluation于11.41.41 UTC实际Success、0.00892530009150505秒、entries=[]；报告SHA256 `E0530DEA6486D1B042227A0E4D859BB9831FDF169B87F45781A8F6006C768BEB`，已只读核对报告及叶结果。UE PID36128 exit0且已退出；不扩大到CMC失败消费或生产资产。
- 源码保护：生产 Profile 两文件 SHA256 与入口完全一致。新增测试 SHA256 `E175F594B4B0632DDF2848A069DB9DD9049CB6D0D1ECE404DA02C985BB7FAC67`；两份记录最终 hash 另随完整非 Git diff 交回，避免自引用。
- 架构核对：T1冻结时只读检查 Movement 结构文档，接口、职责、依赖、运行流程与生产资产状态未变化；未修改 Obsidian。后续第26次仅关闭本纯求值专项验证；CMC失败消费、资产迁移与游戏内 Run 仍开放。

## 已冻结短修：10-Build24-R1

- 授权来源：统筹第24次构建失败交回后的唯一短修，2026-09-30；M1 四文档已先收口并冻结。组长直接完成，无代理。
- 状态：三文件已冻结，写入权限交回；冻结时等待统筹重建，后续第25次结果见上方 T1 构建边界。
- 唯一结果：CMC.cpp 有序 include 区仅增加 `#include "Net/UnrealNetwork.h"`，显式提供 `DOREPLIFETIME_CONDITION` 宏定义。
- 精确文件与入口 SHA256：
  - `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp`：`497D60A442FD8605AA61ED6FE3EF66EB5BBE8626EC5F5AB80DFE3B8E7BC77EF7`，55070字节，UTF-8无BOM/LF。
  - `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md`：`E1EA31A872A02B69A70499FFB7E9630FE48CBB6CA700AF37D9A87A1FB942C5F8`。
  - `AAADocs/Modules/Movement/Module_Repair_10_Validation.md`：`79041C30F66D95B1E55DA25C80E3A5F26EE3312FCAEB6AB7554003590DD9DCC9`。
- 只读依据：`Saved/Logs/ModuleRepairBuildGate_20260930_24.log` 与既有 include 区；统筹已核对 UE 宏定义。逆向删除新增行须在内存中恢复原始字节长度及 SHA256，工作区保留修复。
- 非目标/停止点：不改任何函数、规则、接口、预测、其它源码/测试/资产/图文；不运行 UE/UBT/Git，不扩展兜底或模式修复。交回三文件 hash、一行 diff 和逆向基线证明后冻结。
- 实际源码 diff 仅在 `GameFramework/Character.h` 后、`System/GGYGOGameplayTags.h` 前插入一行 Net 头，共31字节；修改后55101字节、SHA256 `A0DE24171A8188AC19308C84585837EA43464CE679FE95FD6285C01BD7E0D675`。
- 逆向保护：在内存中删除唯一新增行，恢复55070字节与入口 SHA256 `497D60A442FD8605AA61ED6FE3EF66EB5BBE8626EC5F5AB80DFE3B8E7BC77EF7`；工作区保留 include 修复，未进行实际回滚。其余源字节完整保留。
- 未验证：本组长没有运行构建/UE/Automation/Git；R1 冻结时尚待统筹重建。S2–S7、模式取舍和资产接线未启动；当前纯 Profile 测试写入与未运行边界见 T1。

## 已冻结文档步骤：10-StrictConfig-S1-M1

- 授权来源：统筹 C6，2026-09-30；Movement 组长直接完成，无代理。S1 四文件静态冻结与 hash 已由统筹接受，源码/测试写入权限已交回。
- 状态：四份文档已完成读取回和静态检查并冻结；停止在 M1。S2–S7、纯 Profile 测试仍未授权。
- 唯一结果：Movement 结构文档和结构 Canvas 同步 S1 的可选错误输出、失败 Reset、合法零值及严格纯求值；标明 CMC 的失败忽略/固定速度替代仍待 S2–S7。
- 唯一写入者：`GGYGO｜Movement 模块`，会话 `01a0e5b5-83e6-70b3-9e67-c9e8547586a4`。
- 精确路径与入口 SHA256：

| 精确文件 | 修改前 SHA256 |
| --- | --- |
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Movement/结构.md` | `4C58D1EB30E5319B8572FF581335ACDED6AA48E3C9AFA0CE0D57749E32483ADD` |
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Movement/GGYGO_结构_移动与位移.canvas` | `68D91EA1FF1E4E54920B9137851C17A4BAEBB2FB40B0FD3E12F092FFA4E489F0` |
| `F:/ue_project/GGYGO/AAADocs/Modules/Movement/Module_Repair_10_Subleases.md` | `52D9E807683678EA6DCA7885791AFEFAA5857D35DA29EA505C94D60EAE0EB7E0` |
| `F:/ue_project/GGYGO/AAADocs/Modules/Movement/Module_Repair_10_Validation.md` | `90CFE7A71F68102D0615BDEAD9BB4E1847BEEB6F8B00203B3C628296CAA45371` |

- 只读依赖：S1 Profile `.h/.cpp`、CMC 现有消费者、计划蓝图/模块参考、Movement 计划/流程图及 Input/Animation 结构文档；已完整读取结构 Canvas 全字段和项目 `.kiro/skills/obsidian-canvas-diagram/SKILL.md`。
- 验收断言：只修改 Profile 接口/正文与消费缺口状态；结构 Canvas 保留全部 ID、节点类型/矩形/颜色、边及标签，检查 JSON、端点、wikilink 和尺寸。
- 非目标：源码、测试、Movement 计划/流程图、其它图文、全局入口、资产、UE/UBT/Git 均禁止；不改 CMC 权威或算法，不自动 S2–S7。
- 实际范围：结构 MD 仅修改 Profile 行并增加纯求值/消费缺口说明；Canvas 只修改 `sampler.text`。13 节点/10 边，ID/类型/矩形/颜色及全部边/标签与入口逐字段一致；18 个 wikilink 出现、11 个目标均存在且无歧义，矩形有限且为正、无重叠。
- 尺寸边界：Profile 节点仍为 `(1100,230,410,250)`；保守文本预算约 196 px，小于 250 px。未做实时 UI 渲染，不冒称像素级验收。
- 构建交回：统筹报告第23次启动异常未编译；第24次 exit6 / Failed(OtherCompilationError)，3/6 编译 actions、25.99 秒，未链接新 DLL/未跑测试。只读日志确认错误集中于既有 CMC 的 `DOREPLIFETIME_CONDITION` 宏不可见，不作为 Profile 语义失败。M1 没有编译/UE/Git 或源码写入。

## 已冻结源码步骤：10-StrictConfig-S1

- 授权来源：统筹 C5，2026-09-30；由 Movement 组长直接执行，不创建或唤醒子代理。
- 状态：四文件静态冻结及 hash 已由统筹接受；本组长未编译/运行。第24次统一构建因既有 CMC 缺复制宏头失败，未链接/跑测试；本步纯求值语义仍待独立专项。
- 唯一结果：Locomotion Profile 纯求值明确成功/失败；合法零速度成功，负速度、非有限样本及正速度无有效方向失败，失败输出无残留。
- 唯一写入者：`GGYGO｜Movement 模块`，会话 `01a0e5b5-83e6-70b3-9e67-c9e8547586a4`。
- 精确文件：
  - `Source/GGYGO/Character/Data/GGYGOLocomotionMotionProfile.h`
  - `Source/GGYGO/Character/Data/GGYGOLocomotionMotionProfile.cpp`
  - `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md`
  - `AAADocs/Modules/Movement/Module_Repair_10_Validation.md`
- 只读依赖：`GGYGOMovementTypes.h`、CMC/现有 Movement 测试调用、UE 5.8 `RealCurve.h` / `RichCurve.h` / `Vector.h` 及 RichCurve 求值实现。
- 冻结接口：`EvaluateInterval` 末尾仅增加可选 `FString* OutError = nullptr`；保留三参数调用兼容。错误返回曲线/字段与失败性质，不写日志，不在资产中持有生命周期或诊断状态。
- 验收断言：入口清空输出/可选错误；所有失败保持空输出；循环 Yaw 原点、周期端点及相位采样各自明确失败；派生值有限，局部候选仅在成功后提交；合法单键常量、非循环时间钳制及周期浮点边界修正保留；数据校验不修改键/资源。
- 非目标：CMC/RMS/MovementSet、固定模式取舍、预测、测试、蓝图/资产、Obsidian 图文及全局入口均冻结；S2–S7 未授权。
- 门禁：不运行编译、UE、Automation 或 Git；交回完整非 Git diff、四文件 SHA256、只读调用/边界复核与未验证项后停止。
- 实际结果：入口 Reset，完整数据校验及原始求值失败均保留原因；零速度保留 0；局部 Candidate 在所有检查成功后唯一提交。无运行时日志、播放/诊断缓存或其它资产写入。
- 验证边界：仅对照 UE 5.8 类型/API、调用签名及分支作只读审查，检查括号/定义唯一性/空白；没有执行 C++ 或自动化，不代表 CMC 速度兜底、RMS 清理或生产迁移已关闭。
- 文档交接：S1 当时未获 Obsidian 写入范围；可选 OutError 与严格纯求值语义现由上方 M1 专门同步至 Movement 结构 Markdown/Canvas，计划/流程图仍冻结。

以下写入者与交接条目是 D1–D5 历史记录，不表示当前写入授权；旧临时实现者已结束，不再派发。

## 共同冻结契约

- 现有 `ABP_Pyrios` 使用 `BS_Pyrios_WalkRun`，BlendSpace1D 单轴语义统一命名为 `WalkRunBlendAlpha`，数值 `0 = Walk`、`1 = Run`。旧序列化成员 `GaitBlendY` 只在兼容边界保留，不能继续扩散为新 API 名称。
- Movement 唯一持有影响胶囊位移的步态混合、Start/Stop/TurnBack 选择、相位、阈值和模拟时间。Animation 只读 `FGGYGOAnimationStateFrame`，把语义映射为现有 AnimBP 的 `WalkRunBlendAlpha` 与 `StopValue`。
- 保留当前实际起步与 WalkRun 曲线速度包络。独立 Locomotion Profile 由真实动画曲线迁移，不能以固定 `WalkSpeed` / `RunSpeed` 冒充兼容。
- 曲线纯求值与现有 `FRootMotionSource_GGYGOCurve` 执行器分离；不新增 Tick、计时器或第三套位移执行器。
- SavedMove、NetworkMoveData 和校正回放只传最小语义/时间；服务端按自身 MovementSet/Profile 校验，不接受客户端资产、曲线或速度。
- `SetMovementSet` 切换和置空只清 Locomotion 自有状态并恢复 CMC 基线，不结束 ActionMotion/GAS 持有的资源。
- CMC 输出标准本地轴 `X = Forward`、`Y = Right`；现有动画兼容层负责换成表现轴。
- 不运行 UE、UBT、Git 写操作，不修改 `.uasset`。所有资产接线仅输出只读审计/迁移清单，等待统筹分配独占 UE 窗口。

## 写入者与精确路径

### 组长（本会话）

状态：已完成整合与静态复核，文件冻结；等待统筹构建、UE 资产窗口与动态验收。

可写：

- `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h`
- `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp`
- `Source/GGYGO/Character/Components/GGYGOAnimCurveSampler.h`
- `Source/GGYGO/Character/Components/GGYGOAnimCurveSampler.cpp`
- `Source/GGYGO/Character/Data/GGYGOMovementSet.h`
- `Source/GGYGO/Character/Data/GGYGOMovementSet.cpp`
- `Source/GGYGO/Character/Data/GGYGOMovementTypes.h`
- `Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTest.cpp`（新增）
- `Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTestTypes.h`（新增，如测试夹具确有需要）
- `Source/GGYGO/Animation/Tests/GGYGOAnimationStateFrameTest.cpp`
- `Source/GGYGO/Animation/zzzAnim/Data/ZZZAnimTuning.h`
- `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md`
- `AAADocs/Modules/Movement/Module_Repair_10_Validation.md`（新增）
- `AAADocs/Scripts/create_walkrun_blendspace.py`
- `AAADocs/Scripts/fix_blendspace_axis.py`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Movement/结构.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Movement/计划_移动与动作位移.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Movement/GGYGO_结构_移动与位移.canvas`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Movement/GGYGO_流程_移动与位移.canvas`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/结构.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/计划_动画与表现层.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/GGYGO_结构_动画与表现.canvas`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/GGYGO_流程_动画表现.canvas`

只读依赖：当前 ActionMotion 文件、引擎 5.8 CharacterMovementReplication 接口、Agent A/B/C 交回文件、生产 AnimBP/BlendSpace/动画资产。

验收：整合单一状态机、网络预测/校正、MovementSet 基线恢复、测试与局部笔记；复核所有子代理实际 diff 后冻结。

### 临时实现 A：Locomotion Profile 与现有 RMS

状态：已交回并冻结；组长已接手整合。

唯一可写：

- `Source/GGYGO/Character/Data/GGYGOLocomotionMotionProfile.h`（新增）
- `Source/GGYGO/Character/Data/GGYGOLocomotionMotionProfile.cpp`（新增）
- `Source/GGYGO/Character/Components/GGYGOCurveRootMotionSource.h`
- `Source/GGYGO/Character/Components/GGYGOCurveRootMotionSource.cpp`

只读依赖：CMC、MovementSet、MovementTypes、现有 ActionMotion Profile/RMS、`Saved/AnimRootMotion/Pyrios_RootMotion.json`。

验收：提供独立 Profile 与纯 `EvaluateInterval`；保留现有速度/方向/yaw 曲线语义；RMS 只执行 CMC 已选定的区间，不读 AnimInstance，不新增计时器或执行器。

### 临时实现 B：Animation 只读映射接缝

状态：已交回并冻结；组长已接手整合。

唯一可写：

- `Source/GGYGO/Animation/Runtime/GGYGOAnimationStateFrame.h`
- `Source/GGYGO/Animation/Runtime/GGYGOAnimationStateCapture.h`
- `Source/GGYGO/Animation/Runtime/GGYGOAnimationStateCapture.cpp`
- `Source/GGYGO/Animation/zzzAnim/Capture/ZZZAnimSnapshotCapture.cpp`
- `Source/GGYGO/Animation/zzzAnim/Data/ZZZAnimSnapshot.h`
- `Source/GGYGO/Animation/zzzAnim/Data/ZZZAnimStateMemory.h`
- `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.h`
- `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.cpp`
- `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionRules.h`
- `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionRules.cpp`
- `Source/GGYGO/Animation/zzzAnim/ZZZAnimInstance.h`
- `Source/GGYGO/Animation/zzzAnim/ZZZAnimInstance.cpp`

只读依赖：MovementTypes、CMC 公共 getter、当前 `ABP_Pyrios` 文档/字符串、历史提交 `b99248a`、`00921f7`、`538ac8c`。

验收：移除动画层 0.3 秒 Stop 计时与走跑混合推进；StateFrame 接收 Movement 的 `WalkRunBlendAlpha` 与 Stop 语义；兼容层唯一映射 `StopValue 0/1/2`，并在动画边界完成 `X=Forward/Y=Right` 到现有表现字段的轴映射。不得修改 `.uasset`。

### 临时实现 C：只读资产审计与迁移清单

状态：已交回并冻结；离线审计复跑通过。

唯一可写：

- `AAADocs/Scripts/audit_locomotion_motion_profiles.py`（新增）
- `AAADocs/Modules/Movement/Locomotion_Motion_Profile_Migration.json`（新增）
- `AAADocs/Architecture/Interactions/Locomotion_AnimBP_Wiring_Audit.md`（新增）

只读依赖：Git 历史、当前 `ABP_Pyrios` / `BS_Pyrios_WalkRun` / Movement 动画资产、现有动画与 Movement 源码、`Saved/AnimRootMotion/Pyrios_RootMotion.json`。

验收：默认只读、幂等；明确实际资产路径、曲线来源指纹、建议 Profile 名称、MovementSet 字段、现有 AnimBP 变量/状态名及待迁移接线；本批不保存或修改任何 UE 资产。

## 文件交接

- 任何临时实现者完成后先停止写入并报告实际 diff、静态验证与剩余限制。
- 组长验收并把状态改为“冻结”后，文件才能进入整合；需要改变路径范围时必须先停止原写入者再更新本清单。
- 统一构建、UE 自动化、资产回读、提交和推送均由统筹排队执行。

## 追加租约：10-StrictConfig-S2-T1（2026-09-30）

本节为最新步骤状态；此前正文保留各冻结时点的历史，不改原始字节。

- 授权来源：统筹接受五场景族预检并确认Gate27已退出后，按C13授权三文件；Movement组长直接实施，无代理。
- 状态：先登记范围与基线，唯一配置专项已写入并静态复核，三个文件冻结、写入权限交回；新专项尚未构建/运行。
- 唯一目标：一个原生Automation入口验证ValidateMovementSet/编辑器适配的冻结配置契约，覆盖16字段、七引用/Loop及原错误传递，不进入CMC/RMS执行链。
- 精确文件与入口：
  - `Source/GGYGO/Character/Tests/GGYGOMovementSetValidationTest.cpp`：新增，已确认不存在。
  - `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md`：原23927字节、SHA256 `DF8AEBBBB012760BBF1B3E10F19E51B7BEDBBEC08E250451F604E7ECEDECAE94`，仅追加本步与Gate27证据。
  - `AAADocs/Modules/Movement/Module_Repair_10_Validation.md`：原22350字节、SHA256 `6EEE7906480A55C9B1898D1890F00F2EF1B96C3D9CF730A4AEAEF0825048FBF0`，仅追加本步与Gate27证据。
- 只读依赖：MovementSet.h/.cpp、Profile.h/.cpp、现有纯Profile构造方式、原生FRichCurve/FDataValidationContext及Gate27实际报告；生产/旧测试/CMC/RMS/资产/Obsidian/全局记录禁止写入。
- 前置：NewObject公开构造+真实线性keys，TStrongObjectPtr保护；先确认各Profile与完整MovementSet有效。每次只破坏目标字段/槽，错误Loop使用独立Profile，避免共享对象提前失败；期望值来自冻结契约，不读生产私有校验表。
- 验收：有限性/范围/合法零与端点、false七空/true逐项缺引用、两模式七Loop、真实负Speed的Profile前置失败和嵌套原错误、编辑器精确同错误/0警告；每次检查17float位模式、2bool、7refs共26项保持，目标Profile错误数据保持，成功清旧error。
- 资源与非目标：纯Transient夹具，无World/GI/UCLASS/第二框架/日志过滤；不修改默认值或生产调用，不运行UE/UBT/Git、不创建代理。
- 顺序与停止：登记 → 一个专项入口/五场景族 → 静态与追加保护复核 → 三文件完整diff/hash交回并冻结；不自动S3或其它专项。
- Gate27有限证据：统筹交回完整构建Succeeded、9 actions/87.41秒/exit0、UHT6 generated；UE41896已exit0退出。本组长只读核对报告SHA256 `FB5CA102423F04E94294709BE9000D1D5515CBF07895AED20625FB4002503A05`、60 Success/其它计数0及60叶errors/warnings0。该门禁编译S2并保持旧60叶，没有本新增配置专项，消费者仍未接入。
- 实际产物：384行/19681字节、UTF-8无BOM/LF，唯一入口 `GGYGO.Movement.Locomotion.MovementSet.StrictValidation`，一个cpp内五场景族。测试SHA256 `1F3F20853F65B6037F3F162B6B9393504937186C93A96A98B0D01BC5C00BD616`；124个运行时配置检查及3个编辑器适配场景是静态推算次数，不是执行结果。
- 数值族：16字段各NaN/正Inf/负Inf、各下界错误；5有界字段各上界错误与两端成功；逐字段zero使Hold=0失败，其余15个合法zero成功。另以废弃MaxCurveDrivenSpeed=NaN确认不验证或修补。每次断言前截取当前配置，17float以Memcpy位模式比较，两个flag和七个引用逐项比较；没有整个UObject memcmp。
- 引用/Loop/委托：true逐项缺引用7例；两模式×7槽位共14错误Loop，先确认独立Profile内部曲线合法；两模式均测试真实负Speed键原错误及Profile路径传递。错误Profile检查Speed键数及每键全部9字段（6float逐位/3枚举）、Duration位模式和Loop标志保持；错误Loop标志保持。
- 根静态反馈已修正：FRichCurveKey原生相等遗漏两侧权重，且线性键不比较切线；本专项已改显式9字段比较，未增加全Profile或新曲线矩阵，26项配置检查与五族保持。
- 编辑器：有效曲线配置、非法RootMotionScale与fixed模式已填负Speed Profile三场景，真实Context.SplitIssues检查Valid/Invalid、0或恰好1错误、0警告及错误全文与运行时一致；没有过滤日志或模拟编辑器结果。
- 静态边界：字段/成员指针/冻结范围、Snapshot26项、Loop映射、单入口/五族、前置与错误断言、括号/预处理/编码/空白和Unity名称已检查；只读对照native TestEqual模板、IsDataValid父类与SplitIssues。未执行这些C++调用。两记录原始字节前缀与14个保护hash在最终冻结交回核对。
- 架构核对：只增加纯专项与局部证据，不改变接口、依赖、状态所有权或资产接线；S2接口的结构MD/Canvas同步仍属已有待办，本范围禁止Obsidian写入。新专项动态结果、CMC接入、生产迁移与Run验收仍开放，停止在T1。

## 追加租约：C14 / S3a-1 配置绑定（2026-09-30）

- 授权：统筹将S3a拆成绑定、地面物理门禁和预测适配，当前仅授权本绑定步骤；Movement组长本人执行，无代理。
- 唯一目标：`bool SetMovementSet(const UGGYGOMovementSet*, FString* OutError = nullptr)`仅接受有效非空配置；非法配置拒绝且解除旧绑定，nullptr为合法解绑、false仅表示未准入。
- 精确四文件：`Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h`、同目录`.cpp`、本记录、`AAADocs/Modules/Movement/Module_Repair_10_Validation.md`。入口SHA256依次为`C89D030540E83408C337B31C6C309F1C427B7334B40201524A2861AFA4E79544`、`A0DE24171A8188AC19308C84585837EA43464CE679FE95FD6285C01BD7E0D675`、`93517968A205CC2E53B8F2F1B24984977271E16DCF5C21AD7D9AC9CA3B90435C`、`A6CEEE27B85516BD0CA8ED46DFCAAF424EF6DBA928314C46486DEC1D97B93638`；两记录只追加。
- 只读接口/调用方：冻结的ValidateMovementSet及Profile校验；PawnExtension注入调用目前忽略返回值，新增返回/可选错误参数保持其源调用兼容；旧回归夹具缺TurnBack且原地改模式，另步适配，不在本步写入。
- 绑定责任：恢复CMC已捕获基线，清计时/曲线/步态/转身锁存及复制标记，只移除自有Brake/TurnBack RMS；不碰GA ActionMotion token/source/clock。经校验的应用字段原样写入，保留显式false及合法零。
- 准入来源/有效期：已接受配置指针为唯一派生来源，不加有效性状态机；绑定期配置/Profile/外部曲线只读，变更须重绑，不支持热编辑自动失效，不加每帧七Profile扫描。
- 验收断言：成功true且清旧OutError；非法非空false、原校验原因保持、Error含组件/Owner/配置/原因，旧绑定不继续；nullptr false、清错误且无Error；绑定清理不触及GA所有权，Apply不再钳制已验证值。
- 非目标：GetMaxSpeed/CalcVelocity/最低模拟速度/残余速度门禁、SavedMove/校正/表现getter、Evaluate/Finish/RMS替代均不改；旧测试/Profile/MovementSet/PawnExtension/ASC/资产/Obsidian/全局记录冻结。恢复基线不表示默认速度已禁止，Run未恢复验收。
- 顺序/停止：先登记收束预检 → 修改两生产文件 → 静态复核并冻结生产 → 追加验证事实 → 四文件diff/hash交回并立即停止；不运行UE/构建/Git，不自动下一步。图文同步待独立租约，本步骤不得标记完整任务完成。
- 实际状态：两生产文件静态核对后已冻结，h SHA256 `4B1DB91F2B3B74EDC953A696127FC2D2855D804141DE9DD3F0E4905AB39A0573`、cpp SHA256 `4B29EEA193387A8CF50B2A46A3A39156CA4AA63C6E5E9F1CBD87D42C947B8357`。cpp逆向仅Setter/绑定Reset/Apply及本地日志类别变化，其余源码保持；13个只读保护源码hash保持。追加记录后交回四文件，不自动继续。

## C16 / S3a-T1：旧夹具合法绑定与清样本预检（2026-10-01）

- 授权/唯一目标：统筹审查T0后保留“推进清旧样本”目的，扩展唯一测试子类入口；Movement组长本人适配既有AuthorityAndMapping，不新增专项或改生产。
- 精确四文件：`Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTest.cpp`（入口SHA256 `A3C10BC7FECFCE6711B306863B69A8D959310D0DCA22EA4A6B5E3AE7F335340A`）、同目录`GGYGOLocomotionMovementTestTypes.h`（`E10D9A2A03EA47EBD7AD46CF7DB88D4859995571889BF0896BE266CC534A1457`）、本记录（`96CC800BDB743C0271ED417CEF6BEF89362CD07ECAD294FD93CE8B85FB87B811`）、`Module_Repair_10_Validation.md`（`7F75D20C4875257FA97FC866F2E9C914141AF2714886839A6F88BF5A239FF11F`）；两记录只追加。
- 只读接口：C14 bool SetMovementSet、S2/Profile校验、CurveSample和既有测试推进/状态注入。C14生产h/cpp已根静态接受并冻结，其他生产、新测试、RMS/预测、资产、Obsidian及全局入口冻结。
- 顺序：真曲线模式在绑定前显式true并补合法非循环TurnBack → 检查真实绑定/合法null返回 → 保留Blend/StartStop/RunStop → 从实际RunStop结果检查并复制有效样本 → 独立FixedSet绑定前false、复用七个只读Profile → 重绑后注回旧样本并检查有效 → 再设Turning/输入/步态并推进 → 原清相位/无样本断言 → 显式重绑曲线配置后才注入后续测试状态。
- 验收：旧断言及期望全部保留，不统一关闭曲线；清样本由Advance而非Setter证明。子类仅新增protected CurveMotion赋值包装，无生产接口/UFUNCTION，原MakeProfile/AddLinearKeys及其他TestTypes接口保持。实际源样本前置失败即退出，不能改为零样本或弱化期望。
- 停止点：先登记预检、仅apply_patch实施、静态diff/前缀/保护hash核对、四文件冻结交回；未授权UE/构建/Git/代理，不自动S3a-2。C14图文同步及Run/蓝图验收仍待后续范围。
- 实际交回：测试cpp 166行/9117字节，SHA256 `1EA95AE61E1B832DC570A11136D7765C9119C86471824A73773118C1F0805A90`；TestTypes.h 44行/1771字节，SHA256 `78920CCD1FA1CE3D28321D7C6330235A4FC47B9768D83739F010CE706E1E09B5`。两测试文件已静态核对并冻结；原21处检查全文保持，新增8处绑定/源样本/相位前置检查，仍为一个既有Automation入口，未编译/运行。13个保护源码hash保持；两记录仅追加，四文件交回后停止。

## C17 / S3a-2：普通地面执行准入（2026-10-01）

- 授权/唯一目标：统筹接受跨native回调的单一地面准入契约，第30次构建/UE退出后，仅授权Movement组长本人实施，无代理。
- 精确四文件：CMC.h（SHA256 `4B1DB91F2B3B74EDC953A696127FC2D2855D804141DE9DD3F0E4905AB39A0573`）、CMC.cpp（`4B29EEA193387A8CF50B2A46A3A39156CA4AA63C6E5E9F1CBD87D42C947B8357`）、本记录（`B97CE4138C8C40CAD06300ED554919909D13239E059A5E5A9F1C6049C146D787`）、Module_Repair_10_Validation.md（`89B766A29345EA7800BB3138E4AA9205D5314C5E345FA72C04E7CC4A7558D507`）；两记录仅追加。
- 共享接口冻结：C14 SetMovementSet返回/校验/解绑契约保持，仅加诊断周期复位及原拒绝已诊断标记；准入只从accepted pointer派生，不把Profile求值失败揉进bool。配置/Profile/外部曲线绑定期只读约定保持。
- 实际来源依据：源码提交点仅BeginActionMotion的GGYGO.ActionCurve及自有Brake/TurnBack。独立动作按ActionCurve实际struct+实例名识别Current/Pending源，保留Finished/Marked源的native最后应用帧，不依赖仅本地token；动画按实际RootMotionParams识别，非模拟代理的真实网络RootMotion Montage只在BeforeMovement延迟封口至native提取后。未知RMS或RootMotionFromEverything设置本身不豁免。
- 调用顺序：GetMaxSpeed未准入地面返回0；GetMinAnalogSpeed不抬高地面上限；BeforeMovement停Locomotion推进、清样本并标记自有两RMS摘除，不调用带sequence增量的Reset；CalcVelocity封输入/RequestedMove/旧平面速度；native ApplyRootMotionToVelocity后再封自有RMS同帧残留；PhysicsRotation拒绝默认输入朝向。原生基座/解穿/校正、非地面动量及合法独立RootMotion保持。
- 日志契约：只在无准入且真实普通地面输入/请求速度/旧平面速度出现时每绑定周期一次Error，含模块/组件/Owner/配置状态/原因；没有请求不日志。去重flag只用于诊断，每次Set请求复位、非法非空C14 Error后标记已诊断；nullptr合法解绑无Error。无重试/等待计时、第二状态机或Tick。
- 验收：缺配置不得Super速度替代；最小模拟速度不能抬高合法0；恢复Velocity/RequestedMove/自有RMS不能产生主动地面位移或默认输入旋转；false正常模式、合法零、飞行/掉落动量、ActionCurve模拟代理及最后帧保留。无StopAll/清空RootMotionGroup/结束GA/改MovementMode，不清输入/路径状态所有者。
- 非目标/停止：Prediction/getters、Evaluate/Finish、RMS内部曲线失败替代独立待办；旧/新测试及其他生产/资产/Obsidian/全局冻结，A12/B8另线互斥。只apply_patch，静态完先冻结源码再追加证据，四文件diff/hash交回后停止；禁UE/构建/Git/代理/额外文件，不自动后续。需更改source接口或引入新权威时先停止交回。
- 来源收束：识别struct/实例名/原有priority/Override组合，ActionCurve名称及100优先级常量同时用于原提交点（只替换同值字面量）和只读识别，避免两套定义。RMS集合含未知来源时不借ActionCurve存在豁免；无配置地面先拒绝未知来源的native速度应用，防止其切Falling绕过判断，并诊断实际源名/类型。已知Brake/TurnBack继续native最后帧应用后封口；不改任何source接口/时钟/资源所有权。

- 最终入口封口（替代上条“已知Brake/TurnBack先native后封口”的中间方案）：按ApplyRootMotionToVelocity入口的未准入普通地面事实直接Enforce并返回，包含自有源Marked/Finished最后应用帧；不会先进入Super的liftoff再用已变Falling的模式判断。实际动画RootMotion/符合原提交契约的ActionCurve、有效绑定及非地面入口继续Super，不清GA、组或模式。
- 此边界依据：native ApplyRootMotionToVelocity按AppliedVelocityDelta的GetGravitySpaceZ决定SetMovementMode(Falling)；自有源当前bInLocalSpace=false、世界XY及IgnoreZAccumulate不作为任意重力方向/复制源参数均不会抬升的保证。入口拒绝无需改源内部或另存跨帧权威状态，重力轴已有速度保留。
- 实际冻结：h 569行/25142字节，SHA256 `D4F4DF1F4E01D7B87B478F291CDE547165F01430727CAA2DC48438982440573E`；cpp 1696行/61901字节，SHA256 `720B0683C479626D15D88D565420F2D0CDFBC243D42DD10FF8F25C43268DE576`。两生产文件先冻结后补记录；UTF-8无BOM/LF、无尾随空白，UPROPERTY/UFUNCTION全文保持。
- 静态范围：内存逆向撤销新增native覆写/私有识别与诊断、入口门禁、Set诊断复位/已拒绝标记、同值ActionCurve名称/priority常量及必要注释/include，准确恢复C14两SHA256；因此Prediction/getters、Evaluate/Finish、Reset/GA生命周期及其余函数保持。13个已登记保护源码hash保持，两记录入口字节前缀保持。私有借用源指针仅当次读，不保存；诊断flag仅在Set与Error处改写，不参与准入。
- 停止：本组长未运行Build31/UE/自动化/Git，未创建代理、写资产或Obsidian。C17仅静态交回，源最后帧/代理/未知混合源/普通输入及RequestedMove仍待统筹运行验收；S3b/c、预测/表现getter、图文同步、资产Run/AnimBP接线和命名迁移继续待独立范围，GA_Dodge/Gadget仍为占位。本四文件冻结交回后等待统筹审查，不自动下一步。

## C19 / Build31-R1：完整类型编译短修预检（2026-10-01）

- 授权/唯一结果：统筹登记C19并授权Movement组长直接执行；只把私有HasAcceptedMovementSet函数体移出公共头，使UObject有效性检查在MovementSet完整类型可见处编译，准入及运行规则不变。
- 精确四文件及入口SHA256：`Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h`（`D4F4DF1F4E01D7B87B478F291CDE547165F01430727CAA2DC48438982440573E`）、同目录`GGYGOCharacterMovementComponent.cpp`（`720B0683C479626D15D88D565420F2D0CDFBC243D42DD10FF8F25C43268DE576`）、本记录（`4F21F03BE92410A33BC21873B6CF913300E80800C2AF9E300A12A8E5C40C548B`）、`AAADocs/Modules/Movement/Module_Repair_10_Validation.md`（`7B2B83CD0D5FFCE90DC3BD86A0A4A46B2BF47B339EA2E7EBD027322A39FB443D`）；两记录仅追加，历史字节前缀保护。
- 所属/只读依赖：Movement本组件私有辅助；cpp已有`Character/Data/GGYGOMovementSet.h`完整类型include，公共头继续前置声明。共享接口、指针权威状态、门禁/诊断/清理、Profile/RMS/Prediction、其他模块与资产均冻结，无跨模块依赖改变或冲突文件。
- 唯一步骤/依赖顺序：登记本预检 → h仅改为`bool HasAcceptedMovementSet() const;`，cpp定义且仅`return IsValid(MovementSet.Get());` → 静态逆向恢复C17两source/hash并冻结 → 两记录追加失败与修复事实 → 四hash交回立即停止。只有编译修正这一个契约；不新增源码接口、宏、业务规则或公共头include。
- 验收断言：原签名/const/private与UPROPERTY/UFUNCTION保持；唯一函数体、完整类型在定义前可见，除这一搬移外源码字节保持；入口两记录前缀及已登记保护源码hash保持。静态核对不冒充Build32通过。
- 非目标/停止点：不修改tests/资产/Obsidian/全局记录，不运行UE/构建/Git，不创建或唤醒代理，不继续S3b/c或Run接线；需扩大范围即停止交回。统筹安排独立Build32，新DLL未链接前不得借旧DLL验收。
- 实际修复/冻结：h仅保留private/const原签名声明，cpp在已有MovementSet完整头可见处增加唯一同签名定义，函数体为`return IsValid(MovementSet.Get());`。内存逆向这两处后精确恢复入口两source SHA256，原规则/反射/include及其余字节保持；13个已登记保护源码hash保持。生产先冻结后补记录：h 569行/25110字节，SHA256 `E425B97F8EB3FE34EA501D729B469FBD0064EC8290A14A2F7C43730D4DF636B4`；cpp 1701行/62012字节，SHA256 `372A619755F745770F2DAF4ACC77FAA338B18C663C7F26388F0BE50EB238782E`。
- Build31失败事实（统筹交回）：11计划actions、UHT8.3672074秒/3 generated、总87.43秒/UBA72.42秒、exit6；三个Unity单元在CMC.h:349报IsValid类型转换C2664，未链接新运行时/Editor DLL、未跑自动化、Report31未建立；统筹核对238源码及14保护hash前后保持。本短修仅静态核对，未运行Build32/UE/构建/Git/代理，两记录C17入口字节前缀保持；四文件冻结交回后立即停止，等待统筹独立Build32，不借旧DLL称通过。

## C21 / S3a-2-R1：ActionCurve阶段资格收束预检（2026-10-01）

- 授权/唯一结果：统筹已登记C21并核对原生顺序，仅Movement组长直接修正共用HasRegisteredActionCurveSource资格；旋转与缺配置独立动作豁免使用同一判断，不为旧夹具放宽普通地面准入。
- 精确四文件及入口SHA256：`Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h`（`E425B97F8EB3FE34EA501D729B469FBD0064EC8290A14A2F7C43730D4DF636B4`）、同目录`GGYGOCharacterMovementComponent.cpp`（`372A619755F745770F2DAF4ACC77FAA338B18C663C7F26388F0BE50EB238782E`）、本记录（`7653E416AB39D20A7392D59D4791BC7334FED447BA7EB29103A7AEC944B6671D`）、`AAADocs/Modules/Movement/Module_Repair_10_Validation.md`（`BC07845A303A5779FFF506740AF84A0DF422F2911AB5911FF006F153541CD887`）；两记录仅追加保护历史前缀。
- 所属/冻结接口：Movement仅派生读取既有RMS状态；type/name/100 priority/Override身份、local token、accepted pointer、所有调用方与源接口保持。Pending须未Finished且未Marked；Current未结束继续接受，已Finished/Marked仅Prepared且CurrentRootMotion.HasOverrideVelocity有效时保留最后应用帧。没有新权威状态、资源、时钟或dispatcher。
- 顺序与依赖：本预检 → cpp仅改资格函数及h契约注释 → 撤销这两处精确恢复C19 source/hash、保护hash/格式/diff核对并冻结 → 两记录追加事实 → 四hash交回停止。C22合法配置及原生阶段夹具适配须本步冻结根接受后另授；A15/C20异模块互斥线不涉及本状态或四文件。
- 验收断言/原生依据：未准备且已取消/结束Pending无资格；自然结束Current Prepared+有效native Override保留最后帧且不依赖local token；无accepted且无合法独立来源的普通请求仍拒绝。UE5.8 RootMotionSource.cpp:1346/1419清理Current/Pending，1445/1449移入Current，1608/1610实际Prepare并设Prepared，1638/1641设Override；CMC.cpp:2852 Cleanup→2874 Before→2941 Prepare→3046 Rotation。不以注册数组存在或group Override单独作为动作来源。
- 非目标/停止：tests（含GGYGOActionMotionTest.cpp）、资产、Obsidian、全局记录、未知RMS/GA/非地面/求值/预测/getters全部冻结；禁UE/构建/Git/代理。若发现预检外native应用分支需改变契约，停止说明，不自行扩scope；当前步骤仅静态交回，不称C17/C21动态或Run通过。
- 实际实现/冻结：仅h资格契约注释及cpp HasRegisteredActionCurveSource函数变化。Pending只用未Finished/Marked的原身份来源；Current用同一live判断，或Prepared且原生group HasOverrideVelocity的原身份来源。group bool为本次局部读取，两个立即执行的predicate无保存/调度；没有成员状态、token或源资源写入。原身份检查、本地token及两个消费者全文保持，缺配置且仅已结束Pending时不再得到普通地面豁免。
- 静态交回：撤销唯一注释/函数变化精确恢复C19 h `E425B97F8EB3FE34EA501D729B469FBD0064EC8290A14A2F7C43730D4DF636B4`、cpp `372A619755F745770F2DAF4ACC77FAA338B18C663C7F26388F0BE50EB238782E`；14个Movement已登记保护源码（含旧ActionMotion测试）hash保持，两记录C19入口字节前缀保持。生产已先冻结：h 569行/25145字节，SHA256 `E6862BDB5F2C40B5987452B177AEE8E65F40C9C05A88938740282C93204523F6`；cpp 1711行/62589字节，SHA256 `EB0D09B3A88547FB252DD0E2E5575A52DA579B0DEAD30047D4F4D2BA21C9940D`。源码UTF-8无BOM/LF、最终换行/无尾随空白，声明/反射/include保持。
- 限制/停止：C21未编译或动态验证。Build32真实编译了C19/C17但旧ActionMotion自然结束转向断言失败；合法配置与native阶段夹具适配C22仍未授权，不能用本步宣称旧断言通过。Current/代理最后帧、取消Pending无豁免及正常地面拒绝待统筹门禁；其余S3b/c、预测/getters、图文与资产Run缺口保持。两记录补齐后四文件冻结交回，等待根审查，不自动C22或运行UE/构建/Git/代理。

## C22 / S3a-T2：旧ActionMotion夹具原生阶段适配预检（2026-10-01）

- 授权/唯一结果：统筹独立逆向接受并冻结C21后，按同作者串行交接授权旧TimingAndOwnership夹具适配。仍一个既有Automation入口，保留原积分、入口、自然结束释放、旧token与下一动作断言，验证真实最后应用帧和取消Pending无配置拒绝。
- 精确三文件及入口SHA256：`Source/GGYGO/Character/Tests/GGYGOActionMotionTest.cpp`（`BBFD34485BD0E4F001BD972DAD55E8A062E43054075F044B7F179EC3FE8E39E8`）、本记录（`D24E2AB3E40E5600E7C99E89732557D6182513B570A839C3360F12F68071848C`）、`AAADocs/Modules/Movement/Module_Repair_10_Validation.md`（`8356E8045B2C4C33078A13CD96C90C4BBF6F9B19039C2A4C4D1F598D5ED53407`）；两记录只追加。C21生产h `E6862BDB5F2C40B5987452B177AEE8E65F40C9C05A88938740282C93204523F6`、cpp `EB0D09B3A88547FB252DD0E2E5575A52DA579B0DEAD30047D4F4D2BA21C9940D`及sharedTestTypes等全部冻结。
- 配置/职责：测试显式构造正常false固定模式MovementSet，RotationYawRate=360与原夹具一致；按真实校验创建完整非循环TurnBack（Duration=1及四条有限线性曲线），严格TestTrue绑定成功。false模式允许其余Profile留空，已赋值TurnBack必须校验通过；不把错误配置转为固定业务或伪造绑定成功。
- 取消Pending场景：原First取消后观察真实Marked且未Prepared/Pending状态；合法nullptr解绑，给真实RequestedMove及旧平面速度，经公开ApplyRootMotionToVelocity/CalcVelocity/PhysicsRotation要求速度清零、朝向不变，并只期待一次完整Plain/Error/Exact诊断。随后显式成功重绑合法配置，保留原新token/旧token断言；不直接写状态flag或调用私有资格函数。
- 原生步骤/依赖：捕获实际Second源 → Group Cleanup移除取消First → Before → Group Prepare(Profile Duration)令Second自然Prepared+Finished并建立native Override → 公共ApplyRootMotionToVelocity验证真实末段积分 → 原自然结束可观察断言 → 公共EndActionMotion(Second)做真实owner清理、无本地token时同帧PhysicsRotation仍锁朝向 → 下一move Group Cleanup→原Before→Group Prepare→Apply→原Request/PhysicsRotation严格恢复旋转 → 原下一动作可启动断言。End发生在应用与Rotation之间，native阶段相对顺序不变；不手写RMS状态/时间或添加生命周期/时钟。
- 验收/非目标/停止：原每个断言调用与期望全文保持，Standalone Source两速率积分整段不变；新增检查均针对真实生产入口/native结果。先冻结测试，再补两记录并交三hash/完整diff；禁生产、TestTypes、其它source、资产、Obsidian/全局写入及UE/构建/Git/代理。若需新增protected访问/helper文件、不同native顺序或超三文件，先停止交回；本步不标通过，统筹统一Build33。
- 统筹验收保真收束（替代上条原生步骤中Second显式End的中间方案）：Second纯native自然Prepare到期→应用/末帧朝向检查→下一move Cleanup→Before自动CleanupFinishedActionMotion→Prepare/Apply→原转向释放与下一动作断言，全链不显式End(Second)。Prepared+Finished+Marked且显式owner清理的末帧锁朝向另用同一World内独立真实ACharacter/CMC夹具，绑定同一只读合法配置，Begin返回真实handle并经Cleanup→Before→Prepare→Apply后公开End该handle再Rotation；不代替自然自动清理证明，不修改native相对顺序、任何状态flag或时钟，不新增类型/helper文件。原三文件租约保持，源码仍未运行；旧中间FEBD89FE…冻结声明已撤回，待本修正静态再冻结。
- 实际冻结：旧测试cpp 221行/14022字节，SHA256 `75ED3F333D57D08309D27E3342E60DC997A27344BFC63B2EB1D1DA85D7B3DED1`。原21个Test调用/期望全文保持，现45处检查（新增24处，不是45测试叶或通过结果），仍一个既有入口；原Standalone Source两速率积分段逐字保持。仅两include、合法配置、取消Pending公开入口及两个区分的真实native生命周期场景变化，内存逆向精确恢复原`BBFD34485BD0E4F001BD972DAD55E8A062E43054075F044B7F179EC3FE8E39E8`。
- 保真/保护：Second纯自然链无显式End，原Yaw>1与真实Begin非INDEX_NONE断言仍由下一move Cleanup→Before自动owner收束证明；独立EndedCharacter/EndedMove只复用只读配置/动作资产，真实公开End返回handle后检查Prepared+Finished+Marked末帧，与自然链完全分开。未写任何RMS时间/status/group数组或private状态，无新UCLASS/SharedTestTypes/生产接口，原natural积分/旧token等检查保持。15个Movement保护源码（含C21 h/cpp、sharedTestTypes）hash保持，两记录C21入口前缀保持；UTF-8无BOM/LF、最终换行/无尾随空白。
- 停止/未验证：测试源码先冻结后补两记录；未编译/运行C22，合法绑定、一次精确拒绝、末帧两场景与自然自动清理仍待根统一Build33真实运行。未操作UE/构建/Git/代理、资产、Obsidian或全局记录，不将本静态断言数称测试通过；三文件冻结交回后立即停止。
- 收尾追加授权/历史保护：统筹要求在原三文件租约内修正两记录顶端过期当前状态，并将S2段落标为历史；因此本次除C22末尾追加外，仅改顶端状态/标题并增加历史说明，原S2至C21结果正文保持。将这些顶端改动在内存中逆向后，两记录原C21入口字节前缀及hash仍可精确恢复；不再把实际磁盘前缀称为未变。测试与全部生产源码在统筹开始Build33前已冻结，记录收尾不等待33结果，不写其它文件；最终三文件hash随静态交回，之后停止写入。
- 随后Build33有限动态证据（统筹执行/交回，本组长只读核对报告与构建日志）：Editor Succeeded，10 actions/33.74秒/UBA29.06秒/exit0，真实链接新运行时及Editor DLL。`Saved/AutomationReports/ModuleRepairGate_20261001_33/index.json` SHA256 `624287915CDBC1C3E7D7D4857FF9E50973EE15D6D8374F1439CF46365B5EA4E3`，07:51:34 UTC（15:51:34北京时间），65叶64 Success/1 Fail、其它状态0、总0.8156763911247253秒；C22 TimingAndOwnership Success/0.009702898561954498秒/entries=[]/0错误警告，旧AuthorityAndMapping同为Success/0.009144198149442673秒/entries=[]/0错误警告。唯一Fail为Animation.FloatCurveSnapshot的真实Model Outside首键LeaveTangent夹具前置，与Movement无关，本范围不修改该文件。
- Build33边界/最终停止：统筹交回UE41716 exit0已退出，240源码与14保护hash保持，真实日志verbosity为51 Error/2 Warning；不能称整个批次全绿。Input17未重跑，生产Run/资产/AnimBP、预测/proxy与S3b/c仍未关闭。本组长没有执行UE/构建/Git/代理，收到结果后仅按原租约更新本两记录，测试75ED3F33…与C21生产源码继续冻结；三文件最终hash交回后立即停止写入，不自动下一步。

## C26 / S3b-I1：成功曲线速度资格预检（2026-10-01）

- 授权/唯一目标：统筹已接受零写入预检，确认第34/R3窗口全部结束后正式授权四文件；台账与并行排程C26一致。Movement组长直接执行，先登记后实现。本步修正成功来源资格与速度大小混淆：真实成功样本的合法0、极小正速及零RootMotionScale不能被GetMaxSpeed当作不可用而换成固定gait，不称全部隐式兜底已删。
- 精确四文件/入口SHA256：`Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp`（`EB0D09B3A88547FB252DD0E2E5575A52DA579B0DEAD30047D4F4D2BA21C9940D`，只改GetScaledCurveSpeed、IsCurveDrivingSpeed、GetMaxSpeed三个函数体）；同目录`.h`（`E6862BDB5F2C40B5987452B177AEE8E65F40C9C05A88938740282C93204523F6`，只改两getter现有契约注释，不改声明/成员/UHT）；本记录（`B4CDB58D7CA5F3BB53613557D1717683E67CB1DC9384B78503BAFDA0B6996667`）；`AAADocs/Modules/Movement/Module_Repair_10_Validation.md`（`981F393684748A07702DE010324A06372A9EF39E4E1A178E586955C6C41357A3`）。两记录可更新顶端当前状态并追加本步事实，原历史正文保持。
- 根因/职责与冻结契约：Profile纯求值成功后才写bHasCurveSource=true，合法0不清此标志；CurveMotion由CMC既有Locomotion入口持有，getter派生读取。本步资格同时要求accepted配置、显式曲线模式、无本地活动Action、成功来源及Speed/RootMotionScale/乘积有限非负，不以任何正数阈值判成功。数值读取只返回真实乘积，ForceWalk仅取WalkSpeed上界；显式false固定模式保持。无新状态/缓存/时钟、第二执行器、来源猜测、每帧诊断或跨模块接口。
- 只读依赖/保护：MovementSet纯校验和getters、Profile EvaluateInterval、MovementTypes的bHasCurveSource/HasUsableSpeed、CMC其余全部函数、Action/Brake/TurnBack RMS与引擎原生Calc/Apply/优先顺序、旧测试及SharedTestTypes、既有Movement结构MD/Canvas。14个Movement保护源码入口hash保持，旧ActionMotion为75ED3F33…；原生Anim RM优先，Action100、TurnBack20、Brake10以及无Anim/Override才调用普通Calc的路径保持。HasUsableSpeed继续表达现有制动/RMS结束判据，本步不改它。
- 验收断言：成功零速资格true且MaxSpeed=0；成功极小正值不被阈值吞掉；正常非零值按Scale相乘；合法Scale=0保留零；ForceWalk只限上界并保留零；显式false仍按原ResolvedGait固定速度；失败来源或非有限/负值/非有限乘积资格false，不能当正常零成功。独立Action/Anim RM的注册、应用、末帧、清理、转向及native优先顺序全部保持；本步只静态核对，不写或运行专项。
- 顺序/停止点：本预检与基线 → 仅三函数体和两注释 → 完整非Git diff/内存逆向精确恢复入口两source、其它函数/接口及保护hash核对并冻结 → 两记录补实际结果与剩余依赖 → 四hash交回后立即停止。正确契约若需要新状态/接口或超范围架构，停止交回证据/方案/影响供用户决定，不用特判强行完成。禁测试、其它源码/记录、Obsidian/资产写入及UE/构建/Git/代理，不自动续步。
- 必须后续根治的依赖：单Profile忽略EvaluateInterval返回值并继续推进时间；WalkRun必需两侧有一侧失败仍采用另一侧；无成功来源仍可落固定gait；GetScaled数值0不能独立代表成功。这些当前后果保持登记，后续须明确失败传播、阶段中止/资源清理与诊断契约，再按依赖原子实施；不得把本成功样本修正写成严格配置整体合规。预测/proxy、RMS内部方向/退场替代、旧数值getters、资产/AnimBP/Run和生产图文同步仍未关闭。
- 实际实现/生产冻结：GetScaledCurveSpeed先查询唯一IsCurveDrivingSpeed资格，再直接返回Speed*RootMotionScale，不钳制替代；IsCurveDrivingSpeed按accepted配置、曲线模式、无本地活动Action、bHasCurveSource和有限非负Speed/Scale/乘积返回bool；GetMaxSpeed按该bool选曲线来源，ForceWalk仍仅原Min上界。正常false模式、普通地面无配置、CantMove/非地面/native路径和固定gait分支保持。h只改262/392两条原注释，生产签名/反射/成员保持。先冻结源码：cpp 1722行/62767字节，SHA256 `1AD15D3B4FCF36950B620D655B8B9414535C5B4DA65800E06D747B89287896FF`；h 569行/25228字节，SHA256 `00C3B5A3E7DC963403D8D0FC5D67F361B09ABC40CA1983C20974A04DE89D0C7A`。
- 静态保护/架构：完整diff及函数依赖已核对，IsCurveDrivingSpeed不调用GetScaledCurveSpeed，GetScaled与GetMax只读同一资格，无递归或第二状态。内存逆向仅三函数体精确恢复入口cpp `EB0D09B3A88547FB252DD0E2E5575A52DA579B0DEAD30047D4F4D2BA21C9940D`；逆向两注释恢复h `E6862BDB5F2C40B5987452B177AEE8E65F40C9C05A88938740282C93204523F6`。其余函数/状态/清理/Action/原生优先级全文保持，14保护源码含旧测试与SharedTestTypes hash保持；UTF-8无BOM/LF、最终换行/无尾随空白。没有新增循环依赖、跨模块读写、资源、缓存、计时或执行器；资格从既有成功样本派生，现有架构能表达本契约，无需以特判或来源猜测扩展。
- 图文与后续边界：已只读按计划蓝图定位Movement结构/计划/流程Canvas及Animation曲线流程。Movement文档仍把Profile未接线与显式false一起描述成固定速度兜底，缺本步合法零值资格与C14/C17运行状态；Animation曲线Canvas仍描述旧Tick→SampleAnimCurves链，须后续按当前Profile唯一来源整体同步。本租约明确禁止Obsidian/资产/全局记录写入，因此未同步，不标笔记完成；相关Markdown/Canvas由统筹另步授权。源码冻结后仅补本两记录，未UE/构建/专项/Git/代理；第34/R3旧结果不覆盖C26，四hash交回后立即停止，不自动续步。

## C29 / S3b-T1：成功速度消费者专项预检（2026-10-01）

- 授权/唯一目标：统筹已核对并接受C29零写入预检，台账/排程三文件租约一致；仅在既有AuthorityAndMapping同一叶内验证C26成功来源资格与真实GetMaxSpeed消费。组长直接完成，先登记基线/范围/契约再写；保持原29处检查/期望/容差，不新增用例叶或放宽断言。
- 精确三文件/入口SHA256：`Source/GGYGO/Character/Tests/GGYGOLocomotionMovementTest.cpp`（`1EA95AE61E1B832DC570A11136D7765C9119C86471824A73773118C1F0805A90`，仅原全部检查之后新增隔离段）；本记录（`73C535614B0D575E943D61DA8FD065ABAC1C59632E0B2237947421D7C9C8498D`）；`AAADocs/Modules/Movement/Module_Repair_10_Validation.md`（`F07502276A97F3797400F09878019A76C17A558BD1D044A28B38B7D37356AF4D`）。两记录只更新顶端当前阶段并追加本步事实，原历史正文保持。C26生产cpp `1AD15D3B…`/h `00C3B5A3…`、ActionMotion `75ED3F33…`、TestTypes `78920CCD…`及其它源码全部冻结。
- 前置/隔离与清理：原全部29检查之后，在同一原World内Spawn另一个既有AGGYGOLocomotionTestCharacter及其真实内建CMC；原角色、状态、资产与用例流程不修改。复用MakeProfile、公开SetTestCurveMotion/SetTestGait及真实SetMovementSet，各配置的模式、Scale和七合法引用均在绑定前完成，绑定后重新注入本夹具的真实求值样本/gait。ForceWalk检查后公开清除；原World RAII清理两个角色/CMC，新增资产只属于独立夹具，样本为局部值。不新增测试头/生产接口/UCLASS、时钟、状态或执行器。
- 严格断言：真实合法Evaluate成功且bHasCurveSource后才注入；曲线0资格true/MaxSpeed精确0；1/32768经Scale2为1/16384，仍小于旧阈值且精确保留；128经Scale2为256；合法零Scale返回0；ForceWalk只把正常样本上界限为64、零仍0；显式false配置Walk64/Run512且资格false。0/极小样本HasUsableSpeed仍false，证明共享Brake/RMS阈值保持。数值用严格相等，不用默认浮点容差掩盖极小值。
- 失败边界：复用真实合法Profile以非法区间求值产生明确false/错误/无来源输出，再注入仅检查资格false；真实成功128样本与已合法绑定MAX_flt Scale的乘积溢出，仅检查有限操作数/非有限乘积及资格false。不把当前fixed退回当正常成功，也不期待尚未修复GetMaxSpeed失败阻断；不写来源flag或ExpectedErrors来假造/隐藏失败。
- 只读依赖/非目标：C26三个getter、Profile纯求值/校验、MovementSet绑定/统一校验、既有TestTypes接缝与MakeProfile、共享HasUsableSpeed。生产、ActionMotion、测试头/其它tests、资产/Obsidian/全局记录冻结；没有UE/构建/Git/代理权限。Evaluate完整错误传播、阶段/资源失败清理、原生Action/Anim RM、预测/proxy、图文、七Profile和Run接线均不由此关闭。
- 顺序/停止点：本记录与三基线 → 仅cpp原检查后新增隔离段 → 原29调用全文/容差、单入口、配置前置/真实求值/严格数值与保护hash/完整diff核对，内存删除新增段精确恢复入口cpp并冻结 → 两记录补未编译/未专项事实 → 三hash交回后立即停止。需要测试头/生产接口或扩大范围即停止说明，不为范围改变架构；不自动UE/构建、后续源码或图文。
- 实际测试冻结：仅原全部检查之后增加119行隔离段，cpp 285行/16888字节，SHA256 `59D81A4C651D43523394D9C0B58C87C82BAAF6C82282BD4BDFDC2676E5D1CDC3`。原29处检查/期望/容差及整个原helper/角色构造/流程逐字保持，现64处检查只新增35处前置/结果，仍一个既有叶，不是64个测试或通过数。内存删除唯一新增段精确恢复入口9117字节/`1EA95AE61E1B832DC570A11136D7765C9119C86471824A73773118C1F0805A90`。
- 真实接线与断言：独立SpeedCharacter/SpeedMove使用原World与既有类型，正常配置Walk64/Run512/Scale2，三个真实Profile分别常量0、1/32768、128；其余四引用只读复用原合法Profile。所有正常/零Scale/false/MAX_flt配置在首次绑定前完成，共五处严格真实绑定；三个成功Evaluate及bHasCurveSource/精确原速前置后才注入，四处实际Evaluate包含真实倒序区间失败。精确数值通过实际公开GetMaxSpeed比较，ForceWalk上界64及零、显式fixed Walk64/Run512、零Scale均按方案；零/极小HasUsableSpeed仍false。失败样本来自对原成功输出的真实失败覆盖，真实有限MAX_flt与128乘积溢出，均仅断言资格false，没有失败路径GetMaxSpeed成功/阻断期望。
- 保护/架构/停止：15项Movement保护源码（含C26生产、ActionMotion、TestTypes/纯求值/校验测试）hash保持；完整diff只有新增隔离段，UTF-8无BOM/LF、最终换行/无尾随空白。未新增helper文件/UCLASS/生产接口/成员/时钟/诊断过滤或ExpectedErrors，样本来源flag未手写；原角色/资产不改，ForceWalk公开清除，World原RAII统一清理。测试cpp先冻结后仅补两记录，顶端当前状态更新，原历史正文保持；未编译/未专项，不运行UE/构建/Git/代理。C26完整失败传播/生产Run/七Profile/图文与资产仍开放；三hash交回后停止写入，不自动续步。

## C30 / S3b-T1-V1：第35次有限真实证据同步（2026-10-01）

- 授权/范围/基线：统筹实际接受C29三文件全文/hash及原29检查后，仅授权本记录和10 Validation两文件更新当前状态并追加35有限事实。入口本记录SHA256 `33E1F3A46BADFB2705ED084A2E18AE74A99030CE4622B27838BBD2BF386FB1B7`、Validation `7ABAE0D81EAF679F24F2AEC8B02DCFC329A9F65A8E83CBBC38652B9F8F4816C0`；所有历史正文保留，禁止source/tests/资产/Obsidian/全局记录写入。本步只有证据同步，不改变架构/执行或给新生产权限。
- 实际第35次（统筹执行，本组长只读核对构建日志与报告）：完整GGYGOEditor Succeeded，6 actions/34.99秒/UBA32.04秒/exit0，实际链接新运行时DLL；本次没有新UHT或Editor DLL重链接证明。`Saved/AutomationReports/ModuleRepairGate_20261001_35/index.json` SHA256 `F2DFBCF244512B11EB669D29DFAAD2C21310103E9D9EDA74D098B5ED8A1718A6`，2026-10-01 09:37:52 UTC（北京17:37:52），65 Success/其它计数0，总0.7469504475593567秒，所有叶errors/warnings0。AuthorityAndMapping实际Success/0.00962350144982338秒/entries=[]，ActionMotion Success/0.010235998779535294秒，C20 Success/0.008245799690485秒；64检查仍是原同一个AuthorityAndMapping叶，不是新增64叶。
- 日志/保护与有限结论：统筹交回原始49 Error为Smoke13+Damage预期34+Bake预期2，2 Warning为DDC路径与Python枚举重名，不称全日志无诊断。UE40532 exit0已退出，242源码/14保护在构建与回归保持，没有保存资产。C29测试 `59D81A4C…`、C26生产 `1AD15D3B…`/`00C3B5A3…`与原29检查保持；本门禁仅验证成功来源资格/速度消费者及旧回归，不关闭完整失败传播、原生物理/预测/proxy、七Profile仍null的生产配置、资产/AnimBP/Run接线或图文同步。
- 停止/顺序：两记录顶端与本追加段静态核对、原历史保护和两最终hash交回后明确冻结；本组长不UE/构建/Git/代理、不写源码/资产/Obsidian。冻结之后才执行已登记C31整体失败传播零写入预检，届时只有可决策整体方案/原子拆分，无生产写权，不从C30或本记录自动实施。

## Movement 身份消费者 A：准备实现原子预检（2026-10-02）

### 授权与精确范围

统筹接受已交回零写入预检；Gate51完整Editor Succeeded（7 actions/22.60秒/exit0）、新DLL普通82 Success/2 Fail、84原路径与256源/九保护保持、两次UE已退出。Character纯槽快照已编译，仍无生产新调用/本地动态证据；FAILED真实红叶的两条Error及请求3标记保持。上述由统筹执行，不能扩大为本批准备实现已验证。

独占范围与写前基线 `Saved/ValidationRecords/MovementIdentityConsumerPrepare_LeaseBefore.json` 三项实际匹配：

| 唯一可写文件 | SHA256 | 唯一结果 |
| --- | --- | --- |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h` | `149005B8E39FC98B637327571861EE6632495828D18F22822A4B74F497568577` | 只添加隔离准备方法、局部订阅记录前置类型/成员，既有声明/字段保持 |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp` | `9CF9ABBEA1A202D4F07B47FB1F1DFBB3FD2B496E2B9770304B246A09E669EFD4` | 只添加订阅资源与Ready/Released/Refreshed消费、纯派生ASC查询、原句柄清理，全部旧方法全文保持 |
| 本既有记录 | `AD484ED9C92CB74FBB475DAC9693409A7F61BA5450FA50B90D4F90352BC661FD` | 先预检后记录静态/实际hash/冻结及未启用边界，不新建摘要 |

所有工作由Movement长期组长直接执行。与Character新本地资源测试cpp/原记录互斥，不消费其新测试或改共享实现；Input D15只读。12项只读保护按写前hash采集：Extension h/cpp、ASC h/cpp/AvatarBindingTypes、旧MovementTest cpp/TestTypes、D11输入类型、Evaluation h/cpp、CurveRMS h/cpp。不声明并行全树保持。

### 职责、依赖与唯一状态

ASC独占Binding/ActorInfo/发布认证；Extension独占安装/撤回/真实Ready及opaque资源。CMC仅持自己的局部订阅资源：原Extension弱身份、真实FDelegateHandle、消费的原opaque资源和幂等退休标志；局部记录地址只区分委托所有权，不发Binding号、不构成Ready/移动执行权威。现有AbilitySystemComponent仍是原资源派生缓存，Tag仍由ASC持有；不增加Tag缓存、Ready bool、Context历史、计时器或调度器。

现有CMC并无GameplayTag事件委托，CantMove仅直接查缓存ASC；迁移对象是两条返回void且无对应Remove接口的Extension无参数订阅。只读依赖为已冻结/编译的L1 RegisterLocalAbilitySystemNoticeAndCall/Unregister、opaque HasSameResource/GetIdentity、IsLocalAbilitySystemResourceReady及ASC IsAvatarBindingPublicationContextCurrent。CMC准备不调用当前槽快照或旧Getter，不借当前槽收养后继。header只前置声明Extension/Notice，局部记录内容在cpp，避免新增Header循环依赖。

先后顺序：本预检 → 隔离新增块 → 原整h/cpp逆向及12保护核对 → 本记录有限静态/hash → 三文件冻结；后续专项、Host/Character旧入口与消费者迁移、生产E单链启用、统一新DLL新World、局部图文均另授。Ready在发布后消费，不要求Host等待CMC来产生Ready，依赖方向不循环。

### 消费与清理验收断言

- Ready复制原Notice/Resource/PublishedContext；核对原订阅仍属CMC、原Extension及OwnerPawn、原opaque当前Ready、Binding与实际PublishedContext一致且ASC当前发布认证通过。同opaque重复Ready不Reset；不同opaque即使ASC/Pawn/Binding相同，也是真正不同本地资源，单次重置既有Locomotion边界。
- Refreshed只消费已经持有的同opaque资源/原ASC和当前Context。不得重置时钟/序列/Blend/TurnBack/运动资源、清失败或用Refresh建立另一资源；迟到旧Context即使资源R仍Ready也拒绝。
- Released不要求原资源仍Ready/ASC存活；只按HasSameResource匹配原R，先清自己的派生缓存和资源，再执行既有本地Reset。迟到R不能清S，不读取当前槽替换原授权、不取消ASC能力/Cue/ActorInfo。资源释放后订阅可等待同Extension后续真实Ready。
- Prepare在RegisterAndCall之前公布原局部订阅记录；弱CMC/原Extension和原记录栈副本跨同步回调保持。返回句柄仅归仍原有的记录；旧记录退休/CMC关闭/来源改变时，迟到句柄只向原Extension精确注销，不能覆盖后继句柄。返回值表示真实订阅结果，不把正在返回的句柄或失效回放冒作Ready。
- 退休先封闭原局部记录，清原消费资源/派生缓存，随后精确注销自己的句柄；所有外调后的旧尾栈不得写后继。重复清理幂等；来源弱对象已失效时只清自身记录，不解引用旧对象。原订阅资源RAII不延长ASC/Pawn/Extension生命。
- 派生Getter每次核对原订阅/Resource/Owner/Ready及原ASC匹配缓存，再返回只读查询对象；返回空只表示无当前ASC来源，不新增移动准入规则。现有IsMovementBlockedByTag全文保持，A阶段不调用此Getter。
- 剥除所有新增标记块必须恢复写前整h/cpp原hash；尤其BeginPlay、EndPlay、CacheAbilitySystemComponent、IsMovementBlockedByTag及FAILED/Profile/Input/RMS/Action/SavedMove全文保持。旧测试/断言及只读共享源保持。

### 非目标与停止点

A仅准备，无生产调用点、模式开关、双订阅或业务兜底；不修改旧注册/Tag路径，不用RemoveAll热切换。未来E须新World单链切换，并先满足Host/旧Getter及各消费者迁移门禁；现有void注册不提供旧实例精确热移除，若要求热迁移即停并另审共享接口。

无测试、Build/UE/Git、资产、Obsidian/全局、其它会话或代理权限。不扩FAILED/Profile/Source/输入/RMS/Action/网络/Host/Hero/Health矩阵。第四文件、政策/共享接口/状态归属变化立即停止交证据。完成新增实现及有限静态/hash后明确冻结，不把准备代码冒称生产启用、首次W/Run或联机通过。

### A 实施结果与有限静态证据

新增块均由 `Movement-LocalASC-A` begin/end注释明确标记。h只增加SharedPointer include、Extension/Notice前置声明、三个protected准备/清理/const查询方法、一个private消费方法及private订阅记录指针；新增27行。cpp尾部只追加257行，不插入或替换任何旧函数。准备入口 `PrepareLocalAbilitySystemSubscription(Extension, OutError)` 和纯查询 `const UGGYGOAbilitySystemComponent* GetReadyLocalAbilitySystemComponent() const` 在全cpp各只有定义1处，没有既有生产调用点；清理/消费只在新增块互相调用。

局部 `FLocalAbilitySystemSubscription` 禁止复制，持原Extension弱身份/真实NoticeHandle/消费原opaque Resource及仅管理清理的bRetired。委托捕获弱CMC、弱订阅记录，原记录在注册调用栈强保留；不强持ASC/Pawn/Extension、不产生新的Binding/Ready状态。同步回放先于返回句柄时仍只操作原记录；退休记录不接收句柄，直接向其原Extension精确注销。正常退休先标记、清原资源/自己的缓存并撤CMC槽，随后仅移除原句柄；迟到返回栈在组件/来源/槽改变时不能清或覆盖后继。无Source/输入Session迁移。

- Ready：原资源、原Extension/Owner Pawn、Extension真实Ready、Notice.PublishedContext的Binding以及ASC当前实际发布Context均检查。同opaque重复Ready只核对已有ASC、不写缓存/不Reset；不同opaque才更新唯一派生缓存并调用一次既有Reset。
- Refreshed：已消费同opaque、同ASC且当前Context才消费，整个分支没有缓存替换或Reset调用。不会为未持有资源补Ready、存Context/Tag/时钟副本；旧Notice Context不能借当前R的Ready通过。
- Released：分支在Ready/ASC/Pawn存活检查之前，仅按原HasSameResource匹配；清自己派生缓存/原Resource后既有Reset。晚到R与当前S不匹配时显式Verbose诊断并返回，不触及S；不清订阅，可接同原Extension后续真实Ready。
- const Getter：只从所持原资源核对Owner、Ready及原ASC与现有缓存一致，返回const ASC或无当前来源；不写缓存/自动认领后继、不日志刷帧。A尚未接CantMove，原无ASC暂态语义和所有移动门禁未改。
- 错误/清理：Prepare失败返回非空模块/消费者/Owner/Extension/原因字符串；订阅成立不冒称Ready。通知拒绝的Verbose含原ASC/Pawn/Binding/Kind及原因，未动生产FAILED Error严重级别。失效来源只释放自己的资源/句柄记录，注销不解引用已失效对象，无Cancel/GE/Cue/ActorInfo调用。

静态有限证据：

1. 剥除三个h新增标记块（含各自新增分隔空行），完整恢复原h `149005B8E39FC98B637327571861EE6632495828D18F22822A4B74F497568577`。剥除cpp尾部唯一新增块及分隔空行，完整恢复原cpp `9CF9ABBEA1A202D4F07B47FB1F1DFBB3FD2B496E2B9770304B246A09E669EFD4`。所以所有旧方法、成员/接口、BeginPlay/EndPlay/Cache/Tag和FAILED/Profile/Input/RMS/Action/SavedMove全文保持；未在磁盘逆写。
2. 新cpp花括号余额0/最低0，两个源码尾随空白0/冲突标记0。注册1处；精确注销2处分别为正常退役和退休后的迟到返回句柄；opaque匹配3处。没有当前槽快照、旧Getter/旧注册、RemoveAll、发布/安装/撤出、GameplayTag注册、序号分配或直接运动业务状态赋值。
3. Reset仅三个本地资源边界：订阅退休且确实持有原消费资源、匹配Released、不同opaque Ready。Refresh/重复Ready分支零Reset；原Reset函数全文保持，不清FAILED/输入执行资格、不操作GA Action。
4. 上述12项只读保护前后hash全部相同；Character并行新测试及它的局部记录不纳入本批保护，不声明全树变化只属于本批。
5. 源码最终h：690行/31166 bytes，SHA256 `77C06C96539C6EB89CC454A29EBB5E006E0907DC491019634671F7552FA52732`；cpp：2615行/101902 bytes，SHA256 `FB9AB747AB1704CDA7F380F70A9CBE87C869D4617DBC586F431C33420EBF8788`。本记录最终hash在交回消息提供，避免自引用。

### 冻结交回与剩余启用边界

本批三文件只做准备实现与有限静态；没有新构建/UHT、测试或UE动态证据，不用Gate51旧DLL证明本新增实现。实际动态须统筹在全部源码作者明确冻结后另编号构建。本记录只更新顶部并追加A，原历史阶段/真实红/有限成功按原时点保留；剥除A并恢复写前顶部可恢复原整文 `AD484ED9C92CB74FBB475DAC9693409A7F61BA5450FA50B90D4F90352BC661FD`。

A没有接现有BeginPlay/EndPlay/Cache/Tag，旧两条无参数生产订阅仍存在，旧代码尚未获得本准备清理的行为；不声称已解决旧生产订阅泄漏或迟到无参数回调。旧void注册没有精确移除接口，未来E必须新DLL/新World单链替换，不能运行中双订阅、RemoveAll或模式开关。Host/Character旧入口/Getter及其它消费者迁移门禁、真实适配专项（含同步注册/原资源/Refresh/晚Released/EndPlay）和局部Markdown/Canvas均另阶段，不自动追加测试或启用。

Obsidian/全局入口由统筹独占，本批无写权；既有Gate51范围图文同步与本批准备状态分开。首次W/Run、Input原生窗口/Hero→CMC、正式七Profile/AnimBP/WalkRun BlendSpace、RMS真实模拟、网络、R0/Montage等仍开放，gadge仅占位，原TurnBack业务/曲线保持。

**Movement身份消费者A三文件已完成准备实现与有限静态交回，现停止写入并冻结。** 没有第四文件、共享接口/政策/状态归属改动；后续生产E、测试、图文及构建均等待独立授权。

## Movement 身份消费者 E1：生产调用单链切换原子预检（2026-10-03）

### 授权、唯一目标与文件基线

统筹接受E零写入预检，逐段核对A与旧Cache/Tag/EndPlay后，仅授权下列三文件独占编码。授权记录为 `Saved/ValidationRecords/MovementIdentityConsumerE1_LeaseBefore.json`，三项写前实测hash/字节均一致。最近Gate54为统筹执行的既有源码证据；E1尚未进入该DLL，不把旧门禁写成本批验证。Movement长期组长直接实施，无代理。

| 唯一可写文件 | 写前 SHA256 / 字节 | 唯一修改 |
| --- | --- | --- |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h` | `77C06C96539C6EB89CC454A29EBB5E006E0907DC491019634671F7552FA52732` / 31166 | Cache、现有ASC派生缓存、Prepare的三处相关注释 |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp` | `FB9AB747AB1704CDA7F380F70A9CBE87C869D4617DBC586F431C33420EBF8788` / 101902 | 仅CacheAbilitySystemComponent、IsMovementBlockedByTag、EndPlay三个方法体 |
| 本既有记录 | `0A2020BFC1FCA646EE41E3FB3C696AAF596631F64AC17FAAB80E1D1E1A9D9BD2` / 81056 | 先预检，后实际diff/hash/静态/冻结与未运行边界 |

本步骤唯一目标：以原Owner的原Extension一次Prepare替换旧无参数双订阅，将CantMove查询改为现有const Ready Getter，并在EndPlay先精确释放自身原身份订阅。沿用既有接口、A消费实现和现有AbilitySystemComponent派生缓存；不新增字段、状态、方法、模式或执行准入。

### 职责、依赖、顺序与运行门禁

ASC仍唯一拥有Binding、ActorInfo、实际发布Context和Tag；Extension仍唯一拥有本地opaque资源的安装、真实Ready与撤回。CMC仅消费自己的订阅及原资源，Ready/Refreshed/Released检查全部委托已冻结A方法，既有Locomotion Reset和输入生命周期责任不另建。

只读依赖：现有A Prepare/Release/const Getter/Consume及局部资源记录；Extension L1 RegisterAndCall/Unregister、HasSameResource/GetIdentity、IsLocalAbilitySystemResourceReady；ASC实际Context认证；原Input绑定/失效、FAILED、Profile/RMS/Action及网络链。写前另采集12项保护：Extension h/cpp、ASC h/cpp/AvatarBindingTypes、MovementTest cpp/TestTypes、D11输入类型、Evaluation h/cpp、CurveRMS h/cpp；只核对这些文件，不声明并行全树保持。

依赖顺序：本预检登记 → 三处h注释与三个cpp方法体 → 完整逆向证明及保护hash → 本记录结果 → 三文件冻结交回。生产运行另由统筹排程：Host/Character真实Install/Publish、其它消费者单链迁移完成并全员冻结 → 同一新DLL/新World门禁 → 接线专项及原严格回归。当前Host/Character旧生产入口尚未向本地身份资源发布Ready；提前运行CMC切换将缺真实来源，故编码不等于生产已启用。本步不独立构建/运行、不热迁移、不保留双订阅、不加RemoveAll或模式开关。

### 精确改动与验收断言

- Cache保留现有签名及BeginPlay调用：由GetOwner查原Extension一次，只调用一次现有Prepare。必需前置缺失或Prepare失败用已有完整错误字符串一次Error诊断，包含Movement、Consumer、Owner、Extension与原因；没有轮询、自动重试、固定速度、额外FAILED门禁或直接写派生缓存。成功仅说明订阅成立，未Ready是合法暂态。
- Tag保留现有签名及Restriction_CantMove规则：调用既有const Ready Getter，存在真实当前ASC才查其Tag。无Ready仍按原无ASC暂态返回false，不能被当成建立输入请求、运动资格或另一来源；不新增Tag缓存/委托/移动门禁。
- EndPlay入口先调用Release，随后原Input失效块及Super逐字保留。仅退休CMC自身原身份资源和真实DelegateHandle，幂等，不借当前槽清后继。
- A三个方法、Consume和局部订阅资源记录逐字保持。因此同opaque重复Ready/合法Refresh不Reset，旧Context拒绝，Released按原资源精确匹配而不要求Ready，晚R不能清S，返回迟到句柄只注销原来源的自身Handle。这些是既有静态契约，本步不冒称新增动态验证。
- 对新方法体作内存逆向替换须精确恢复整cpp写前hash；还原三处h注释须恢复整h写前hash。BeginPlay、其它方法/字段/签名、Source/Input/FAILED两生产Error及请求3、Profile/RMS/Action/TurnBack/网络全文保持；既有测试/断言与共享源保持。

### 非目标、停止点与文档边界

不增加测试或改变红叶、期待诊断、过滤规则及既有数字/容差；不改Host/Character/Hero/Health、GAS库、资产、Profile绑定、AnimBP/WalkRun/命名、TurnBack业务/曲线或Gadget占位。第四文件、共享签名、政策/状态归属变化立即停止，不扩大租约。

本步仅生产调用编码与有限静态，不Build/UE/Git、不写Saved或Obsidian/全局入口。实现冻结后才交回实际diff、三个hash和完整逆向证明；所有动态、正式Run、物理输入/正式Hero、资产和网络验收仍未完成。受影响Obsidian/全局实施状态由统筹另授同步，本租约禁止直接写入，不能标图文或整个模块完成。

### E1 实际差异与有限静态结果

实际修改限于上述三个方法体及三处注释，没有新增声明、成员、接口或文件：

- `CacheAbilitySystemComponent`：原31行方法改为12行，删除旧两条无参数委托及回调内重新寻找Extension/读旧Getter/写ASC缓存/Reset；由原Owner查Extension一次，调用既有Prepare一次。失败仅 `UE_LOG(LogGGYGOMovement, Error, TEXT("%s"), *Error)`，原Prepare提供模块/Consumer/Owner/Extension/原因；没有新错误替代、等待重试、模式或业务门禁。订阅成功仍可能未Ready，由原Extension真实身份通知推进。
- `IsMovementBlockedByTag`：原7行改为6行，局部 `const UGGYGOAbilitySystemComponent* ASC = GetReadyLocalAbilitySystemComponent();` 后查询原Restriction_CantMove。未Ready返回false保留原未绑定Tag查询暂态；不会产生输入请求、曲线资格、Ready或默认速度。
- `EndPlay`：原9行改为11行，只在原方法体开头添加Release及分隔空行；后续原Input失效块和Super逐字保持。
- h仍690行，仅Cache说明、现有AbilitySystemComponent缓存说明、Prepare说明各替换一条注释；A及既有全部声明/字段/元数据保持。cpp原2615行现2597行，净减少18行，A尾部257行实现逐字保持。

完整源码在内存中逆向还原，没有磁盘回滚：

1. 还原三条h注释，整h精确恢复31166 bytes及写前 `77C06C96539C6EB89CC454A29EBB5E006E0907DC491019634671F7552FA52732`；还原三个cpp方法体，整cpp精确恢复101902 bytes及 `FB9AB747AB1704CDA7F380F70A9CBE87C869D4617DBC586F431C33420EBF8788`。所以BeginPlay、A三个方法/Consume/局部资源记录、其余全部旧方法、Input/FAILED/Profile/RMS/Action/TurnBack/SavedMove/网络全文保持，不以抽样代替完整保护。
2. 全cpp Prepare名称2处（定义1、Cache调用1）；const Ready Getter名称2处（定义1、Tag调用1）。旧Initialized/Uninitialized无参数注册、旧Extension ASC Getter均0处；Cache原Extension查找1次、Prepare1次、失败日志1处且无直接缓存赋值；EndPlay首句Release，剥除两新增行后原Input/Super整体相同。没有双订阅、RemoveAll、槽快照、重试、默认速度或新门禁。
3. 上述12项只读保护写前/写后hash逐项相同，包含原MovementTest `07B9D4C350F00795F0359783ECF148460F65A67D15273049FD806178D3FE43DB`。没有新增测试、ExpectedErrors/诊断过滤、断言弱化或FAILED/Error严重级别修改；保留原请求1/1、2/2与请求3标记源码，不冒称本批再次动态复现。
4. 两源码均UTF-8无BOM/LF、最终换行，尾随空白及冲突标记0。h最终31251 bytes，SHA256 `55324CF3099F6C53A91FCBD5F692DDED01A51B30782E6468766F2224C75BFCB2`；cpp最终101014 bytes，SHA256 `3E705A5DA5410CB5159595480EF95D18BC65488F7DE3E310994C0994F1493C71`。本记录最终hash在冻结交回提供，避免自引用。

### E1 冻结、架构核对与剩余边界

CMC消费链源码已单链切换，运行环境尚未切换。原Extension/资源身份、真实Ready/Context、派生缓存与精确Handle职责沿用A，无新增循环依赖、重复状态/执行链、外部内部状态写入或另一帧调度；Subscription成立不是Ready，不把合法未Ready变成新的业务拒绝状态。来源失效/原资源撤回、后继保护及精确清理继续由冻结A承担，EndPlay现显式进入该清理。

本步未执行Build/UHT、UE、Automation、Git或资产操作，未写Saved、Obsidian或全局入口。Gate54是写前实际门禁，不能证明E1新源码编译/动态正确；Host/Character生产发布、其它消费者、同一新DLL/新World以及原资源Ready/Refresh/晚Released/EndPlay专项仍待统筹。物理键盘、正式Hero→CMC、七Profile配置、AnimBP/WalkRun BlendSpace与生产Run、RMS真实模拟、R0/Montage和网络仍开放。Gadget保持占位，原TurnBack业务/曲线未改。

本记录仅更新顶部并追加E1，原历史结果保留；剥除E1段并恢复写前顶部须恢复原81056 bytes及 `0A2020BFC1FCA646EE41E3FB3C696AAF596631F64AC17FAAB80E1D1E1A9D9BD2`。Obsidian模块结构/流程和全局实施入口的同步仍未完成，须统筹另授租约，本步不标图文或整个Movement完成。

**Movement身份消费者E1三文件已完成授权编码与有限静态，现交回冻结并停止写入。** 第四文件、共享签名、政策/状态归属未改；编译、生产激活与专项验收没有完成，不自动扩展后续步骤。

## 本地 CurveRMS 实际区间：两记录文档原子 M1（2026-10-03）

### 写前登记、唯一目标与精确范围

状态：两记录已保存回读并交回冻结；四个源码继续冻结。本步唯一目标是把已交回的本地 CurveRMS 实际区间实现、统筹有限静态接受及未验证边界同步到既有两份 Movement 记录，不改变源码契约或运行权限。

- 授权来源：统筹已有限静态接受源 turn `01a101fa-6515-7f91-9d21-88d0b153facc` 和交回 turn `01a10225-ec0c-7991-a8c8-f3d0f27151f5`，本步只开放以下两记录。接受证据：`Saved/ValidationRecords/MovementActualInterval_20261003_RootAcceptance.json`；文档写前基线：`Saved/ValidationRecords/MovementActualIntervalRecords_20261003_LeaseBefore.json`。
- 唯一写入者：Movement 长期组长，会话 `01a0e5b5-83e6-70b3-9e67-c9e8547586a4`；直接完成，不创建或唤醒子代理。

| 唯一可写文件 | 写前 SHA256 | 唯一结果 |
| --- | --- | --- |
| `AAADocs/Modules/Movement/Module_Repair_10_Subleases.md` | `3004A78EF4D94AF1C966DF7DDBEBB87078AD82509564243D32E945210882C69D` | 登记本原子，更新当前入口并追加源实现、范围、静态证据及停止边界 |
| `AAADocs/Modules/Movement/Module_Repair_10_Validation.md` | `D40D80B2385C32699FC4542921AE14640528B6551B850BE1D8B98B96AEA8BC8C` | 更新当前验证状态并追加有限接受与未运行断言；历史结果保持 |

只读依赖：上述两个证据 JSON、已冻结 CMC h/cpp 与 CurveRMS h/cpp、既有两记录历史正文及此前已交回的有限源码/蓝图调查证据。CMC 仍唯一拥有请求准入、候选求值与胶囊移动执行；RMS 只消费原 CMC 的 Prepared 结果，Animation 只消费语义帧。文档不新增共享接口、状态归属、跨模块依赖或执行机制。

顺序：两记录及四源入口 hash 匹配 → 本写前登记 → 更新当前入口与本地源结果 → 同步 Validation → 保存回读与历史正文/证据路径核对 → 两记录 hash 交回冻结。验收断言：当前状态区分编码、静态接受、编译、动态、资产与网络；准确记录旧 wire 字段保持但加载清除本地 Origin；保留旧失败和诊断，不伪装复测；蓝图/命名调查与源运行证据分开；四源 hash 保持。

非目标：四源、Profile/Evaluation/Input/Hero/ASC、测试/夹具、其它记录、Saved 证据、Obsidian、全局入口、资产与引擎均无写权；不执行矩阵、Build/UHT、UE、Automation 或 Git，不新增测试/消费者准备层。第四文件或需要修改源契约即停止交回。本步保存回读后交回两 hash 并关闭写权；Obsidian 四份图文须下一独立租约，不能标已同步或整个 Movement 完成。

### 已冻结源原子的实际结果

统筹接受状态为 `finite_static_accepted_uncompiled`，接受时间 `2026-10-03 14:29:50 UTC`。接受记录独立匹配下列四 hash，并核对 RMS h/cpp 全文、CMC 原 Origin/实际区间/Prepared 唯一提交/Stage、SavedMove/Before 回放、挂载/退役及回放出口；范围 diff 检查 exit0。这是有限源码静态接受，没有新 UHT、DLL、World 或运行通过结果。

| 已冻结源码 | 当前 SHA256 |
| --- | --- |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h` | `8D0F6905717A33B2726BE431C47421283B442D29522B12ADF0513A7AF7E0C086` |
| `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.cpp` | `8DD4D4FA60E9D3CD514C351D8E1F80F3ED836F9BF05DADE13CF3370286131D5B` |
| `Source/GGYGO/Character/Components/GGYGOCurveRootMotionSource.h` | `F5638524D87BAA9FD56DDF947A198DE1FC7434251195BE6F8413A5A7ABDC4081` |
| `Source/GGYGO/Character/Components/GGYGOCurveRootMotionSource.cpp` | `5F113DA3D6EA757D13CAD9AF15529258A590EADC9CFF992B2F018D2DAA76DEB7` |

实际调用契约（行号对应上述冻结源码）：

- `StageLocomotionCurveRootMotion`（CMC.cpp:1630）保存所选候选与原移动输入，签发弱原 CMC/MovementSet、Binding、InputRequest、执行序号、片段类型/序列、时间锚点、原 yaw/Scale 的 Origin。`ApplyCurveRootMotionSource`（2633）只复用同一 Origin 的有效源；同名其它有效资源明确拒绝，不用名称/LocalID认证来源。
- `PrepareLocomotionCurveRootMotion`（1820）从原生 Source.GetTime、实际 SimulationTime/MovementTickTime 映射 Profile 区间，由原 CMC 调用既有 EvaluateSingleInterval。Before 不提前把整帧区间结果当原生结果；原生 partial/zero/catchup 时间可进入该接口。输出保留既有端点速度采样并乘实际 sim/tick 比例，**不声称精确位移积分**；原生区间推进 TurnBackElapsed，不在此使用普通帧的时间上限截断。
- `ConsumeLocomotionCurvePrepared`（1717）在 CMC 提交完整候选，同一 Prepared 引用只消费一次。RMS `PrepareRootMotion`（RMS.cpp:62）仅向原 CMC 请求结果、安装速度/原生时间及结束标志，没有 Profile 求值或从当前 flat CurveMotion 猜测来源。旧片段自然结束不重新挂同一物理资源；正常末帧动量、离地清理、独立 Action/动画 Root Motion 优先级与原生碰撞执行责任保持。
- `FSavedMove_GGYGO::PostUpdate`（CMC.cpp:208）保存原输入和 Prepared，并禁止合并相关 move；`PrepMoveFor`（230）在原生 Super 之前安装回放上下文。`BeginLocomotionCurveReplay`（1748）核对原 CMC/输入/tick、当前 accepted 配置、结果及 SavedRootMotion 的 Current/Pending 来源。原生重算或保留的原 Prepared 在 Before 正式消费；没有原准备区间时不制造整帧模拟，也不再次推进回放计时。
- `HasCurrentLocomotionCurveOrigin`（1589）要求同一原引用、issuer/Binding/InputRequest/执行序号及当前绑定/准入。`ReportLocomotionCurveRootMotionFailure`（1600）只进入该原当前请求的既有 `FailLocomotionRequest`（868），其原方法体保持。FAILED 不被历史候选恢复；旧/无法证明来源的贡献退场，不借当前请求失败后继。`RetireLocomotionCurveRootMotion`（1609）精确退休原 Origin 的 Current/Pending 源；Reset、EndPlay 和回放结束清理本 CMC 的上下文/派生引用。
- RMS `Clone` 保留原共享引用；Matches/UpdateStateFrom 拒绝本地 Origin 不匹配。`NetSerialize`（RMS.cpp:125）仍使用原基类及 BaseYaw/SpeedScale/bEndOnZeroSpeed wire 字段，**加载时额外清除本地 Origin、Prepared 和诊断节流状态**。只认证本地签发来源；网络导入没有可证明 Origin，明确拒绝，不能据 wire 保持宣称联机兼容/校正已完成。

### 用户补充与只读调查的独立边界

用户实际要求称为“Gadge”的能力先占位，后续集体接入 GAS 时再说明，并优先核对蓝图/既有实现及名称。既有 GA_Dodge/Gadget 占位状态保持，本源原子没有新增 GAS 调用方或改能力业务。

已交回调查为当前磁盘 ABP 序列化图/引脚、已有资产回读及旧 Git 的只读核对：WalkRun 单个 BlendSpace 的 X 接 StateMemory.GaitBlendY，Entry 进入 WalkRun；TurnBack/Stop 既有分支仍在；规范语义名 WalkRunBlendAlpha，旧 GaitBlendY 只在序列化兼容边界保留，BlendSpace 旧轴显示名尚未保存修正。历史走跑样本不证明当前四源可运行。这些只读结论没有资产保存、新 UE 编译/冒烟或扩大源范围，不替代上述源码交回与运行验收；正式七 Profile 仍未创建/完成引用接线。

### 验收状态、架构核对与停止点

CMC 继续唯一拥有请求准入、候选提交和胶囊执行；Origin/输入/Prepared 是原请求的资源身份与有限派生快照，弱 owner/config 不延长角色或资产生命周期。RMS 不新增求值/帧调度器，失败委托既有 CMC 门禁，不创建第二个 FAILED 权威状态；清理覆盖原源退役、Reset、EndPlay 与回放作用域。统筹有限静态接受没有发现需本两记录原子改写的职责或共享接口。

| 验收层 | 本源原子的实际状态 |
| --- | --- |
| 四源编码/有限静态 | 已交回冻结，统筹有限接受、四 hash 匹配、范围 diff exit0 |
| UHT/编译 | 未执行，没有新 DLL 证明 |
| partial/zero/catchup、同帧失败、SavedMove/后继隔离 | 未动态运行，保留严格待验断言 |
| authority/proxy 匹配、校正及导入身份 | 尚未关闭；本地认证不覆盖网络导入 |
| 正式七 Profile、AnimBP/BlendSpace 保存、当前版本 Run | 未完成接线/新 UE 冒烟；只读调查不能当通过 |
| 两份局部记录 | 已保存回读；历史正文、证据链接及四源 hash 核对通过，交回冻结 |
| Obsidian 四份图文及全局入口 | 本租约无写权，须下一独立租约，不标完成 |

本步未改变测试/断言/容差、FAILED 两生产 Error/请求3标记、诊断严重级别或过滤规则；既有失败与当时证据继续留在历史正文，没有声称复测。文档仅更新入口并追加本段，源/测试/资产/其它记录不写。两记录已有限保存回读：历史正文逐字保持，两个证据 JSON/相对链接有效，四源 hash 与冻结交回一致，UTF-8 无 BOM、LF 和末尾换行保持，无冲突标记或行尾空白。最终两 hash 随交回，两记录关闭写权；不自动继续 Obsidian、编译、资产或网络步骤。
