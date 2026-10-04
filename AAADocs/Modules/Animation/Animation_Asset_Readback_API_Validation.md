# 10-11-ReadAPI-R0 / M1：动画 Python 读取接缝

日期：2026-09-30。组长直接实施；R0修正既有 Python 读取器，M1同步实际读取证据，不创建 C++ 框架或修改资产。

当前：R0／M1及下述R1／T1为历史阶段记录，保留其原验证边界。2026-10-03统筹使用既有已编译读取器完成七源完整RichCurve Snapshot及正式保存的默认场景→GameMode→Experience→PawnData根只读回读；正式MovementSet七个Profile引用均为空。新单Profile作者未编译／调用，Profile创建、保存、正式接线、Run与联机未验；读取完成不等于资产迁移或新源码整链完成。

## R0授权范围与基线（历史）

唯一可写文件：

- `AAADocs/Scripts/audit_locomotion_motion_profiles.py`，接管基线 SHA256：`0DAB620CF6688B344E0B979A2F1C798188493DE3FFDE1C34EC0A3599CA2ADE0F`。
- 新 `AAADocs/Scripts/tests/test_locomotion_readback_api.py`。
- 本验证记录。

R0历史保护基线：`AAADocs/Modules/Movement/Locomotion_Motion_Profile_Migration.json`，SHA256：`743DF05805F998B5B722D38980B678E659A87E1FBC3BFA587CDD21E11FDC29FE`。R0实施时未运行脚本 main 或重写报告；后由统筹第25次实际读取更新，当前SHA256见M1。其他源码、脚本、测试、笔记及所有资产冻结；UE、构建、Git 均由统筹安排。

## R0原子步骤、依赖与停止点（历史）

| 步骤 | 唯一结果 / 文件 | 验收断言 | 当前状态与停止点 |
| --- | --- | --- | --- |
| R0-A | 既有脚本使用本机公开 API | 显式加载模块后只选 AnimationLibrary；失败可定位；不猜库/枚举/方法；无非法 keys 成功指纹 | 已实现并静态审查；源码冻结 |
| R0-T | 新 fake-Unreal 专项 | 调用顺序、所有失败门槛、指纹稳定与覆盖边界、离线原行为 | 专项23/23、全量离线68/68通过；测试冻结 |
| R0-V | 本记录 | 基线/实际 diff/测试结果/最终文件与保护报告 hash 可复核 | 已完成；三文件交回后停止写入 |

顺序：本机 API 与范围已由统筹确认 → R0-A → R0-T → R0-V。只读依赖为本机 UE5.8 原生 API、当前实际迁移报告及既有离线行为；没有新的运行时权威或跨模块接口。

## 接缝与证据边界

本机 `F:/UE_5.8/Engine/Source/Editor/AnimationBlueprintLibrary/Public/AnimationBlueprintLibrary.h` 第65行声明 `ScriptName="AnimationLibrary"`；第89、456、598行分别公开 `GetAnimationCurveNames`、`GetFloatKeys`、`GetSequenceLength`。`PyCore.cpp` 的 `load_module` 加载指定模块并导入 Python 符号。读取器已使用 `unreal.load_module("AnimationBlueprintLibrary")`、`unreal.AnimationLibrary`、`unreal.RawCurveTrackTypes.RCT_FLOAT` 及上述三个方法。模块加载返回 None，因此只记录调用完成，并独立检查符号/枚举/方法是否存在。

`curvePayloadSha256` 保持原算法：实际对象路径及四条必需曲线的 time/value 数组。它不包含时长、RichCurve 插值/切线/权重/外推、原骨轨或图引脚；不能直接授权迁移或线性重建。时长单独读取并检查，原报告 schema、七 Profile、路径与资产文件 SHA 算法保持。

本步骤不读取完整 RichCurve、骨轨或图，不处理 Profile 创建/引用迁移、BS轴名修改、ABP接线/父类/拓扑、运动偏移；这些须后续独立授权。本机公开接口的源码核对不是 UE 动态读回成功。

## 结果

### 实际差异

与已保存的接管基线逐行比较，既有脚本为 **+133 / -86**，仅三个 diff hunk：`-15,6 +15,7`、`-510,119 +511,161`、`-646,13 +689,17`。实际统一 diff 已在本任务工具输出中交回，未调用 Git。

- 第18行新增 `math`；第514行新增唯一 API 解析函数，每批七条动画只加载一次模块。
- 第550行替换 keys 解析：只接受原生 `(times, values)`，拒绝空数组、数量不等、非数值/非有限值、越界时间、重复/倒序时间；没有对象键、库、枚举或方法猜测分支。
- 第583行读回函数先检查接口，读取正且有限的时长，再读必需曲线与 keys；失败保留对象路径、状态及错误/缺失曲线信息，不输出成功指纹。新增覆盖说明及 `migrationAuthorized=false`。
- 第684行批量读回复用本批接口结果，新增 `animationReadAPI` 和 `animationCurveReadbackComplete`；一条失败即不能宣称七条全部完成。
- 新专项测试文件完整新增；本记录完整新增。原脚本读取函数之前除 `math` 外、`_static_source_evidence` 起至文件末尾逐段一致。离线分支、schema1、七 Profile、对象路径、资产文件 SHA、time/value 指纹序列化与 main 均保留。

### 离线验证

Python：`C:/Users/Kaven/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`，均使用 `-B`。

| 验证 | 命令/边界 | 结果 |
| --- | --- | --- |
| 新专项 | `-m unittest discover -s AAADocs/Scripts/tests -p test_locomotion_readback_api.py -v` | 23/23通过 |
| 既有 fake/临时目录回归与新专项 | `-m unittest discover -s AAADocs/Scripts/tests -p 'test_*.py' -v` | 68/68通过（原45 + 新23） |
| AST | 对既有脚本及新专项各执行 `ast.parse` | 2/2通过 |
| 基线边界 | 内存中的原始文本与当前文本比较 | 除授权读取块及 `math` 导入外一致 |
| R0历史报告保护 | R0执行前后 SHA256 | 当时均为 `743DF05805F998B5B722D38980B678E659A87E1FBC3BFA587CDD21E11FDC29FE`；后续统筹更新见M1 |

新专项覆盖实际 ScriptName/模块调用顺序、缺模块加载 API/加载异常/库/精确枚举/各方法、资产加载失败、非法时长、names 异常/缺失曲线、keys 异常/形状/空/数量/数值/时间、原 hash 稳定及 value 变化、覆盖边界、七条批量一次加载和局部失败、离线报告契约。测试不调用 audit main；临时报告只在内存中构建，报告写入函数设为失败哨兵。既有测试的写入范围为 fake API 与临时目录。

### 冻结交回

| 文件 | 最终 SHA256 |
| --- | --- |
| `AAADocs/Scripts/audit_locomotion_motion_profiles.py` | `E87A57C6855595259A16427D40C8B85613BD5096E68EE33DC3C363E4E59CFAD8` |
| `AAADocs/Scripts/tests/test_locomotion_readback_api.py` | `2BD90B1D65F23B38DE6731DC8026B36F9D4EB2D4BB872C59A9A6428973F8FE42` |

本记录自身最终 SHA256 由交回消息提供，避免写入自引用 hash。R0交回时未执行 UE 动态验证、未运行 audit main，报告保持第22次结果；该等待点已由统筹第25次独占只读窗口完成，见M1。fake失败门槛与真实成功读取是不同证据，不视为生产资产迁移验收。

R0架构核对：仅改离线审计工具的读取入口，无新增运行时状态、调度器、模块依赖或写资产链；API 结果仅限本批读取，局部 keys 仅限该动画读取，不跨批缓存。RichCurve/骨轨/图的证据缺口仍保留。R0局部文档租约仅含本记录，架构全局入口与其它笔记继续由统筹独占；工具实现冻结不代表资产迁移实施完成。

## 10-11-ReadAPI-M1：第25次真实读取证据同步

### 拆分预检与租约

唯一职责为Animation资产审计证据维护；没有共享代码/接口变更。统筹已冻结脚本与测试并授权以下两文档。只读依赖为实际报告、Readback25日志及统筹14资产/配置前后hash证据；非目标为重新运行main/UE/构建/Git、改报告/脚本/测试/源码/Obsidian/资产、创建读取框架或迁移。

| 原子步骤 | 唯一结果 / 精确文件 | 验收断言与停止点 |
| --- | --- | --- |
| M1-W | `AAADocs/Architecture/Interactions/Locomotion_AnimBP_Wiring_Audit.md` 当前与历史证据区分 | 当前为25次七动画keys/时长成功，22次api_unavailable只作历史；保留null/缺包/轴名/图缺口及实际警告；完成即冻结 |
| M1-V | `AAADocs/Modules/Animation/Animation_Asset_Readback_API_Validation.md` 记录实际门禁与边界 | 报告/日志/hash可定位，明确time/value覆盖与不可迁移边界；核对两文档小diff及保护hash后冻结交回 |

顺序：读取与核对证据 → M1-W → M1-V → 两文档小diff/hash交回。两文件唯一写入者为本组长；报告更新唯一写入者仍是统筹。本次接管hash：Wiring=`7E0B92F9C1A8C3504BE1B08ADEE35281EB85BB42D08DEA83C32F7DA74368E72D`，本记录=`C81BE6F777B1582D07FF6D4B84093F1B2936BF59FD458E99E9A803E74F6C42A0`。

### 实际读取结果

- 报告：`AAADocs/Modules/Movement/Locomotion_Motion_Profile_Migration.json`，当前SHA256=`1D7F2CB333AC2A3523C01B3346068948ABF0CBAB4A0A69F259B7465B931B9C66`；schema1，unreal_python，`animationCurveReadbackComplete=true`，`packageWritesMade=false` / `assetMigrationWritesMadeByThisBatch=false`。
- 日志：`Saved/Logs/GGYGO_LocomotionReadback_20260930_25.log`，SHA256=`78FF4387D227EF865B30BDC592CAD15917AC45675170150664019A4CE3CD5766`。10:51:49 UTC实际执行成功，commandlet result0并退出；统筹记录PID35124 / exit0已退出。
- `animationReadAPI.status=ready`，实际模块AnimationBlueprintLibrary、库unreal.AnimationLibrary、枚举RawCurveTrackTypes.RCT_FLOAT与get_animation_curve_names/get_float_keys/get_sequence_length全部成功；七项均AnimSequence、requiredCurvesPresent=true、curveReadStatus=fingerprinted。

七动画当前原生keys数量如下；时长是报告原始数值，单独读取并检查，不参与旧time/value hash。

| 源动画短名 | durationSeconds | Speed keys | DirX keys | DirY keys | Yaw keys |
| --- | ---: | ---: | ---: | ---: | ---: |
| Walk_Start | 1.4166666269302368 | 86 | 86 | 2 | 2 |
| Walk_Loop | 0.6499999761581421 | 40 | 2 | 2 | 2 |
| Run_Loop | 0.4166666567325592 | 26 | 2 | 2 | 2 |
| Walk_Start_End | 4.349999904632568 | 262 | 262 | 2 | 2 |
| Walk_End | 5.616666793823242 | 338 | 338 | 2 | 2 |
| Run_End | 5.116666793823242 | 308 | 308 | 2 | 2 |
| TurnBack | 2.383333444595337 | 144 | 144 | 2 | 144 |

日志第2049行实际汇总 **0 error / 2 warning**：第1185/2046行DDC路径写入失败、第1821/2047行GGYGOAbilityGroupRule Python重名。成功退出不消除这两条警告，常规59项自动化的零警告记录也不替代本窗口记录。统筹前后核对14资产/配置hash均不变；本M1只读取该交回证据，没有再次操作UE或保存资产。

### 保留的缺口与冻结边界

第25次确认MovementSet七字段仍null、七建议Profile包仍缺失、BlendSpace1D有效第0轴仍GaitBlendY（0..1，Walk=0 / Run=1），ABP CDO AnimSet映射已读而状态图/引脚未读。报告中的静态图说明不是实际图证据；axis_label读取错误仍保留，实际轴来自blend_parameters。`PendingUEAssetWindow`、missingItems=7和未迁移状态保持。

time/value指纹包含实际对象路径、必需曲线名、keyTimes/keyValues；不包含duration、RichCurve插值、切线、切线权重、pre/post外推、骨轨、图引脚。七项覆盖均migrationAuthorized=false。manifest样本与原生keys的载荷/数量不同，导出JSON未带原uasset修订指纹；未执行完整曲线语义/来源一致性比较，不以keys成功或两种hash的相同/不同猜测源相等。当前证据不能授权线性重建、创建Profile或资产迁移。

R0脚本和测试的最终hash仍分别为 `E87A57C6855595259A16427D40C8B85613BD5096E68EE33DC3C363E4E59CFAD8` / `2BD90B1D65F23B38DE6731DC8026B36F9D4EB2D4BB872C59A9A6428973F8FE42`。M1未改任何实现；只核对两文档小diff与保护hash，交回即冻结停止，不自动开展完整RichCurve/骨轨/Graph C++读取框架。最终两文档hash由交回消息提供。

## 10-11-RichCurve-R1：当前DataModel完整曲线读取

### 拆分预检与基线

统筹已接受只读预检并授权本原子步骤三文件：新 `Source/GGYGOEditor/Public/GGYGOAnimationCurveReadLibrary.h`、新 `Source/GGYGOEditor/Private/GGYGOAnimationCurveReadLibrary.cpp` 和本记录。两个源码文件接管时不存在；本记录接管SHA256=`E9A63DD632CF97132A193AA6FFC414DB234E189DB32FDAEE19DB3C9751F6D290`，R0/M1原前缀保持。文件唯一写入者为本组长，与Movement S2文件范围互斥。

唯一结果：一个Editor `UBlueprintFunctionLibrary::ReadFloatCurves` 接缝，输入已有AnimSequence和调用方曲线名，返回按输入顺序的完整FFloatCurve值副本、源正有限时长及明确错误。新接口先按下述契约冻结，再实施；不新增业务配置、源状态所有权或运行时依赖。

| 原子步骤 | 精确文件 / 唯一输出 | 只读依赖 / 非目标 | 验收断言 / 停止点 |
| --- | --- | --- | --- |
| R1-S | 新Library.h/.cpp，公开声明与读取实现 | 现有Engine类型、公开DataModel、GGYGOEditor既有依赖；不改Build.cs/旧工具/运行时/脚本/测试/资产 | 完整副本与时长；失败先清输出，无部分成功；仅查询已有模型；源码静态审查后冻结 |
| R1-V | 本记录，仅追加R1 | R0/M1、实际Report25及本机API只读；不写另一文档/报告/Obsidian | 原前缀一致、完整diff与保护hash可审查、三hash交回；之后停止写入 |

顺序：授权/范围与基线 → R1-S → R1-V；T1专项另步。UE、UHT、UBT、Git、资产操作和代理均未授权。保护基线：Build.cs=`6476DA680D9A318BFE814DBB8C43D76F2C4C9E060B52F564A86DBDD1393FF163`；另一M1文档=`40A35ED3C74860E93C4BB7866CA5F05AE643792408E57F04B4AC7AADB0480046`；Report25=`1D7F2CB333AC2A3523C01B3346068948ABF0CBAB4A0A69F259B7465B931B9C66`；脚本/测试及旧Bake/Builder/Editor测试的完整基线保存在本任务工具输出中。

### 冻结契约与本机证据

`ReadFloatCurves(const UAnimSequence* Source, const TArray<FName>& CurveNames, TArray<FFloatCurve>& OutCurves, double& OutDurationSeconds, FString& OutError)` 返回bool。所有输出先清空（时长0仅为失败清空态）；成功才提交局部Candidate，错误含对象路径及曲线/键索引/字段。空或无效Source、缺已有Model、空names、None/重复names、缺曲线、非正/非有限时长、非有限数值或本机未知枚举明确失败，无日志替代、部分结果、缓存、加载、Controller、模型创建、Modify、事务或保存。

查询：`UAnimSequenceBase::GetDataModel`（本机AnimSequenceBase.h:243，cpp:1391直接返回已有接口）；`IAnimationDataModel::FindFloatCurve`（IAnimationDataModel.h:280，缺失nullptr），使用CurveIdentifier.h定义的FName+RCT_Float标识。避免缺失时checkf的GetFloatCurve。时长来自Source->GetPlayLength，与已验证的AnimationLibrary.get_sequence_length同源。Build.cs已有公开Engine依赖，无需变更。

复制整个FFloatCurve，保留名称、flags及完整FloatCurve；不构建time/value新keys，不SetKeys或自动切线。keys全部九字段与DefaultValue、Pre/PostInfinityExtrap均原样保留。合法负/零值、任意有限key时间、空曲线、原生RCIM_None/RCTM_None/RCCE_None和RCTM_SmartAuto都允许；MAX_flt默认哨兵原样保留。读取器不承担Speed、方向、Loop、时间覆盖或Profile适用性规则，交由下游验证。

本契约仅为当前公开DataModel的FRichCurve快照：Sequencer模型FindFloatCurve返回LegacyCurveData；本机AnimSequencerHelpers转换复制keys/前后外推，但没有赋Channel DefaultValue，不能冒称底层Channel或原资产字节一致。源模型是权威，结果只在该次调用中复制，调用方持有独立值；没有第二套权威缓存。

### 实施与静态交回

R1-S已实现并静态读回审查，R1-V已完成。新header完整新增32行，声明一个BlueprintCallable静态函数；新cpp完整新增207行：本机四种枚举的19个真实case、完整数值检查、已有模型查询及完整值复制。完整新增文件内容与本记录追加差异已在任务工具输出中交回；未使用Git。

| 静态断言 | 结果与代码位置 |
| --- | --- |
| 单一接口与依赖 | header:25仅一个UFUNCTION；仅Editor新类，Build.cs不变 |
| 全部真实枚举 | cpp:11/25/40/54四组本机case，含RCIM_None/RCTM_None/RCCE_None/RCTM_SmartAuto |
| 完整数值检查 | cpp:70检查DefaultValue、前后外推及每键六数值/三枚举；空keys自然通过，无负值/时间范围/覆盖/业务约束 |
| 失败先清结果 | cpp:145–147先Reset曲线、置时长0、Reset错误；所有失败位于成功提交之前 |
| 仅现有模型 | cpp:177 GetDataModel直接查询；cpp:192 FindFloatCurve，缺失nullptr即报错，无GetFloatCurve断言路径 |
| 完整复制与输入顺序 | cpp:202 Candidate.Add(*Curve)复制整个FFloatCurve；cpp:204–206全部成功才提交曲线/时长并返回true |
| 源隔离与清理 | 无源修改、加载、Controller、SetKeys、自动切线、日志替代、保存、事务或静态状态；候选失败即随局部作用域释放 |
| R0/M1前缀 | 与接管原文本逐字符前缀比较完全一致，仅追加R1 |
| 保护文件 | 13个只读文件SHA256与接管基线全部一致（Build.cs、旧Bake/Builder/Editor测试、脚本/专项、另一M1文档和Report25） |

源码冻结hash：header=`1F3506F4DC22789ED7C0BF7A5EB19B2FF6D273DFBC9C964796EC0DDE5978131D`；cpp=`959CFAE102D4513BD3ADFC2652D600D2BB933BAFBA0255DFD3EE00E89E9FDD96`。本记录最终hash由交回消息提供。

静态检查不代表UHT/编译或真实调用通过；本轮没有执行UE、UHT、UBT、Git或T1测试。第26次门禁发生在本新接口实施前，不作为其验证。Python包装返回形状、源内存/脏标记不变及真实资产数据仍待统筹验证。T1必须逐字段比较九个key字段与DefaultValue/前后外推，并比较名称/flags及独立副本；不能只用本机FRichCurve::operator==（遗漏DefaultValue）或FRichCurveKey::operator==（遗漏权重且非Cubic忽略切线）。

架构核对：新Editor读取接口仅依赖已有Engine类型，未改模块依赖或创建新权威/执行链；请求名由调用方提供，返回值没有源指针或跨调用寿命。实现与本记录冻结交回后停止写入；T1和真实窗口另行租约，骨轨/Graph/底层Channel/Profile迁移仍不在本步骤内。Obsidian及全局入口由统筹独占，不在本轮写入范围。

## 10-11-RichCurve-T1：完整快照与失败清空专项

### 拆分预检与基线

统筹接受零写入预检并授权C12两文件：新 `Source/GGYGOEditor/Private/Tests/AnimationCurveReadbackTests.cpp` 与本记录（仅追加T1）。新测试接管时不存在；本记录接管SHA256=`E6D09AC459F05447C5A44D8C0566561377CF2B2ACE2850002130A550CEF896BA`，原R0/M1/R1前缀保持。单入口目标为 `GGYGO.Editor.Animation.FloatCurveReadback`，唯一结果是当前公开DataModel完整快照、失败清空和源权威曲线/时长/dirty不变的有限契约。

| 原子步骤 | 精确文件 / 唯一目标 | 只读依赖 / 非目标 | 验收断言 / 停止点 |
| --- | --- | --- | --- |
| T1-S | 新AnimationCurveReadbackTests.cpp，一个专项入口及少量局部helper | R1接口/实现、现有SafetyTestUtils、本机Controller；不改生产/旧测试/Build.cs/脚本/资产 | 公开API真实夹具与实际Model前置；逐字段完整副本、顺序/独立性、全部输入失败清空及源状态保持；静态交回后冻结 |
| T1-V | 本记录，仅追加预检/静态结果 | Gate27、原记录与报告只读；不写全局或Obsidian | 前缀及保护hash保持，全diff/两hash交回；之后等待统筹编译运行 |

顺序：范围/基线 → T1-S → T1-V → 冻结交回。R1 h/cpp、SafetyTestUtils、旧RootMotion测试、Build.cs、审计脚本/专项、另一M1文档与Report25共9个保护文件hash已登记，未扩大租约。当前禁止UE/编译/Git/资产/Obsidian/代理；第27次已编译R1并常规60/60，但不包含本新专项，不作为T1行为证明。

夹具采用现有Sequence(Package())及唯一临时包，标记Transient；只通过公开Controller的AddCurve/SetCurveKeys/SetCurveFlags/SetCurveAttributes设置源。Controller会重算切线及时间转帧，所有案例先断言实际Model：加权Cubic的非零切线/权重及非线性内点、空曲线/MAX_flt、范围外有限时间/负值/零、原生模式与flags均真实存在。比较该实际快照，不将输入数组当已验证源；前置失败即停止，不常量替代。

失败矩阵为nullSource、空names、None、重复names、缺曲线及先valid后missing；每次预填旧结果并要求false/清空/时长0/具体错误。成功逐项比较9键字段、DefaultValue、前后外推、名称/flags与输入顺序；独立输出副本可修改，源仍保持。clean/dirty前置只设置本测试拥有的临时包，调用后读取并比较；不在断言前重置状态。源未变仅指公开权威曲线内容、PlayLength及package dirty，不声称全部物理内存字节不变。

缺Model使用只读引擎AnimSequence CDO候选，先断言其有效且GetDataModel=nullptr，不改CDO。公开Controller没有DefaultValue setter；自定义默认/非有限字段/未知枚举完整失败矩阵仍未验，不通过const_cast、源Model内部写入或额外UCLASS框架伪造。T1完成后仅静态交回，动态门禁由统筹安排。

### 实施与静态交回

T1-S与T1-V已完成静态审查。新测试291行，只有一个Automation入口和三个局部helper：完整字段比较、实际源快照、源语义状态保持。比较使用逐字段精确值，而非遗漏默认值/权重的原生operator==；按名称核对全部源曲线，不把派生缓存的地址或顺序当权威状态。

| 已写入的断言 | 代码位置与静态核对 |
| --- | --- |
| 完整快照 | 测试:12–40，名称/flags、DefaultValue、Pre/Post与每键九字段全部显式比较；key数量先检查再索引 |
| 真实夹具前置 | 测试:88–169，复用只读SafetyTestUtils，公开Controller构造四条曲线，再从实际Model复制并断言；实际加权Cubic内点须有限且非线性 |
| 顺序及独立副本 | 测试:171–235，重排请求包含空曲线、范围外时间和加权曲线；改输出的key值/权重、默认值、外推、名称/flags后检查源并重新读取 |
| clean/dirty与失败清空 | 测试:191–233，两种包状态分别覆盖null、空names、None、重复、missing、valid后missing；旧曲线/时长/错误预填，失败要求清空且有定位错误，每次比较源内容/时长/dirty |
| 原生合法模式 | 测试:236–281，4种插值、5种切线、4种权重、6种外推，共19次模式请求；每次先断言实际Model模式再调用读取器。插值探针使用WeightedNone，符合本机Linear正常化路径 |
| 缺Model | 测试:283–288，只读原生CDO须实际有效且没有Model，之后检查失败清空；未创建或修补CDO模型 |
| 写入与保护边界 | 无const_cast、GetMutableDefault、源私有Model写入、加载/保存/Modify或日志吞错；所有Controller写入和dirty预置只针对本测试拥有的临时源；9个保护文件hash与接管基线全部一致 |
| 原记录前缀 | 与接管原文本逐字符前缀比较完全一致，R0/M1/R1没有改动；完整新增测试与本记录追加diff已在任务工具输出交回 |

若所有前置通过，已写矩阵将调用读取器36次：两种dirty状态各2次成功/6次失败，19次模式成功及1次缺Model失败。这是代码静态计数，不是测试运行结果。前置或断言失败立即停止；不得放宽断言、改为常量夹具或绕过公开源接口来获得通过。

测试冻结SHA256=`2C63D8BBBE6E0FD5D77F50B23E96F61219C824C6B8217E6908B0142E51E0DCF3`。本记录最终hash由交回消息提供。R1 header/cpp仍为 `1F3506F4DC22789ED7C0BF7A5EB19B2FF6D273DFBC9C964796EC0DDE5978131D` / `959CFAE102D4513BD3ADFC2652D600D2BB933BAFBA0255DFD3EE00E89E9FDD96`；现有SafetyTestUtils仍为 `F6D97EC834540FA522F92569EA12E8F50A160347B89FD640E210673C311136C4`，Report25仍为 `1D7F2CB333AC2A3523C01B3346068948ABF0CBAB4A0A69F259B7465B931B9C66`。

本轮仅完成源码/文档静态核对，没有UE、UHT、UBT、Git或Automation执行；专项尚未编译或运行，第27次常规60/60不能替代本专项。已写失败矩阵仅为上述六类输入及缺Model；非null无效对象、非法时长、自定义DefaultValue、非有限数值和未知枚举的真实源构造/失败分支仍未覆盖，不宣称全部生产失败分支已验。底层Channel、原资产字节、骨轨、Graph、Python包装和Profile适用性继续在本租约之外。

架构核对：测试只依赖既有Editor读取接口与Engine公开Controller/Model；快照是单次断言用值副本，没有新模块依赖、权威状态、执行链或跨测试缓存。临时夹具交由UObject生命周期回收，无保存/长期句柄。两文件静态交回后冻结停止；编译、专项与回归由统筹另行安排，Obsidian及全局入口仍由统筹独占。

## 2026-10-03：统筹七源完整Snapshot及正式默认根只读窗口

统筹独占此只读UE窗口；20组长最新回合均已completed，源码写入者为零。只调用已有已编译Snapshot读取器及Engine公开反射接口；新单Profile作者与本批未编译生产改动没有运行。读取脚本SHA256=`D979895D095403370E61809F064BC81F625FAA478C405B70CFC0F740A37C0E36`，原迁移报告未覆盖，新报告存入Saved/ValidationRecords。

实际过程保留失败，不以成功重跑抹除：R0受限环境因无可写DDC节点在Python前退出（exit 3）；普通Windows环境R1因未暴露的SystemLibrary.break_soft_object_path入口退出（exit -1）；仅修正统筹Saved runner，改用已核实的SoftObjectPath／SoftClassPath.to_tuple()反射入口，R2完成（exit 0）。不改项目缓存设置、不替换配置、不启动PIE。R2日志仍有DDC写入警告和既有Python类型重名警告；旧axis_label字段读取错误原样保留，实际BlendSpace参数另由blend_parameters读取，不宣称日志全无警告。

正式保存默认根由实际配置读取，不按资产名称猜测：`/Game/Map/Untitled.Untitled` → 无地图GameMode override／前缀／LocalMapOptions，因此采用显式INI `BP_GameMode_C` → CDO.GetExperience() `DA_Experience_Default` → SquadMembers[0] `DA_Pawn_Pyrios`。PawnData实际引用`DA_Movement_Default`、`DA_InputConfig_Default`、`BP_PC_Pyrios_C`，Mesh CDO引用`ABP_Pyrios_C`。WalkStart／WalkLoop／RunLoop／StartStop／WalkStop／RunStop／TurnBack七个Profile引用全部null，逐项诊断可见。这只证明保存的默认Squad配置，不证明实际玩家Roster、PIE／URL覆盖或网络选择。

七源四曲线RootMotion_Speed／DirX／DirY／Yaw完整读取；Snapshot包含Duration、Name／Flags／DefaultValue／Pre／Post及有序keys的六个浮点／三个原生模式字段。逐项float32→binary64精度及JSON数值回读核对通过，各七源.uasset读取前／后／最终SHA256一致。下表键数依次为Speed／DirX／DirY／Yaw，完整值及指纹保留在独立报告，不把旧time／value摘要当作完整Snapshot证据。

| 源动画后缀 | 实际Duration（秒） | 四曲线键数 |
| --- | --- | --- |
| Walk_Start | 1.4166666269302368 | 86 / 86 / 2 / 2 |
| Walk_Loop | 0.6499999761581421 | 40 / 2 / 2 / 2 |
| Run_Loop | 0.4166666567325592 | 26 / 2 / 2 / 2 |
| Walk_Start_End | 4.349999904632568 | 262 / 262 / 2 / 2 |
| Walk_End | 5.616666793823242 | 338 / 338 / 2 / 2 |
| Run_End | 5.116666793823242 | 308 / 308 / 2 / 2 |
| TurnBack | 2.383333444595337 | 144 / 144 / 2 / 144 |

ABP AnimSet实际引用Movement七源与`BS_Pyrios_WalkRun`；BlendSpace为1D，X轴显示名仍为`GaitBlendY`，范围0～1，Walk_Loop位于0、Run_Loop位于1，RateScale均为1。此次没有读取Graph／状态机／引脚，也没有更名或重接资产；不能据此确认生产WalkRunBlendAlpha已接通。

证据：`Saved/ValidationRecords/LocomotionAssetReadback_20261003_Result.json`（SHA256 `6F0EB881B3B5F4DAF7503E8914B94DD26906626270A20EC031E3DCFB014DD20B`）；完整值`LocomotionAssetReadback_20261003_Pawn00.json`（`159C5B59079F6D88860A07C2E3699755435F6EAEF0B9F1828D55735F46A345A2`）；R2日志`Saved/Logs/LocomotionAssetReadback_20261003_R2.log`（`D9B115AF63A334146B52341537ED0E1563A00C2CD6F88BD219F2049816A3C29C`）；有限独立核对与两次失败见`LocomotionAssetReadback_20261003_RootAcceptance.json`及R1_Result。

读取前后dirty content／map集合均为空；264个已登记源码与45个列明保护文件hash保持。保护集合不是全部加载依赖：PawnData／InputConfig的DA目录文件不在该45项磁盘基线内，不能冒称所有加载包逐一磁盘证明；七源哈希和全部dirty集合核对分别记录。无资产创建／Modify／Save／Profile作者调用，无UE／UBT残留进程，无新编译、Automation或Git写入。

有限验收仅为七源完整读取与保存默认根配置回读。骨轨、底层Channel、原始磁盘RichCurve语义、ABP接线、Profile可用性、创建／保存／冷读、运行时Run及联机均未因此通过。下一步仍需当前共享接口／调用方适配完成并统一编译，才可运行新作者与生产链；不使用旧DLL冒认新源码可执行，不追加严格矩阵。
