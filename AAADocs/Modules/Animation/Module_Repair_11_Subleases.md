# 第11批 Animation / D6 子租约

更新：2026-10-01。当前状态（C37图文）：Animation结构MD与主结构Canvas完成薄Guard/Scope/Base/ASC/Task静态契约并先冻结；新增4节点5边，旧16/12全部值与原文本保持，MD/图反向整文原SHA256通过。39链接/18目标/5锚点、新节点容量及43限定保护（含14资产配置）通过；旧12节点保守容量不足/原生视觉未验。Canvas已用受审查Shell追加，编辑方式事实交根审查，不再重写。查询消费者/生产AnimClass、严格P1/网络仍开放，四文件交回停写。

以下截止NavM2的D6/C18/C20/C27/A/35/B/C/NavM/NavC/NavM2历史、失败及C只读偏差全部保持。最新C37图文/编辑方式证据见文末；C37文档步骤不等于第37次构建，38门禁仅统筹事实，37失败保留。静态产物不关闭播放/Task权限/资产迁移或原生视觉，历史不授新写权，不自动后续或代理。

## 共同冻结契约

- `UGGYGOAnimInstanceBase` 是通用动画生命周期入口；初始化、反初始化和运行时 Owner 变化必须走同一个幂等复位入口。
- 基类复位 `CharacterOwner`、`AnimationState`、`AnimationDebug`。`FGGYGOAnimationStateCapture` 当前无跨帧缓存，不为它新增伪缓存或第二套状态。
- 基类提供受保护的派生复位 Hook，统一入口先复位基类状态再调用 Hook，避免派生类漏调 `Super`。
- `UZZZAnimInstance` 的 Hook 复位 `StateMemory`、`Snap`、`LocomotionEvents` 当前帧上下文和全部公开派生表现字段；配置 `AnimSet`、`Tuning` 不属于运行时状态，不复位。
- Owner 变化必须覆盖 `A -> nullptr -> B`、弱引用失效后仍返回空 Owner、重复初始化与重复反初始化；变化帧先清旧状态，再从新 Owner 抓取，不允许泄漏旧 Pawn 的 Tag、步态、速度或 TurnBack。
- Animation 仅消费 Movement 发布的只读 `FGGYGOAnimationStateFrame`。保持 `WalkRunBlendAlpha`、`StopMotionType`、标准本地轴 `X = Forward / Y = Right` 以及旧表现轴适配契约，不新增 Tick、计时器、位移执行器或向 Movement 的反馈。
- D5 仅复核兼容映射：`GaitBlendY`、`StopValue` 等旧字段仍是生产 AnimBP 的序列化边界。本批不重构生产 AnimBP，不删除字段，不修改 `.uasset`、Profile 或接线。
- 自动化使用真实 `UZZZAnimInstance` 派生的测试夹具，通过覆盖 `TryGetPawnOwner` 控制 Owner，并直接调用原生生命周期回调；不向生产代码增加测试后门。
- 不运行 UE、MCP、UBT/构建，不执行 Git 提交或推送。统一构建、动态自动化、生产资产回读和提交由统筹排队。

## 写入者与精确路径

### 组长（本会话）

状态：已完成并冻结；方案、子租约、代码审查、整合静态验证与局部笔记一致性均已交付，动态门禁待统筹。

唯一可写：

- `AAADocs/Modules/Animation/Module_Repair_11_Subleases.md`
- `AAADocs/Modules/Animation/Module_Repair_11_Validation.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/结构.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/计划_动画与表现层.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/GGYGO_结构_动画与表现.canvas`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/GGYGO_流程_动画表现.canvas`

只读依赖：批次 10 冻结文件与验证记录、临时实现 A/B 的交回文件、Animation 其余源码、生产 AnimBP/BlendSpace/动画资产。

验收：核对实际改动没有扩展状态权威或资产范围；静态检查生命周期顺序、所有字段默认值、测试覆盖和 Canvas JSON/引用；记录未运行的动态门禁后冻结本批文件。

### 临时实现 A：运行时生命周期复位链

状态：已交回并冻结；组长已复核集中复位顺序、字段覆盖和批次 10 映射边界。

唯一可写：

- `Source/GGYGO/Animation/Runtime/GGYGOAnimInstanceBase.h`
- `Source/GGYGO/Animation/Runtime/GGYGOAnimInstanceBase.cpp`
- `Source/GGYGO/Animation/zzzAnim/ZZZAnimInstance.h`
- `Source/GGYGO/Animation/zzzAnim/ZZZAnimInstance.cpp`
- `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.h`
- `Source/GGYGO/Animation/zzzAnim/Locomotion/ZZZLocomotionEvents.cpp`

只读依赖：`GGYGOAnimationStateFrame`、`GGYGOAnimationStateCapture`、`GGYGOAnimationDebugFrame`、ZZZ Snapshot/Memory/Context/Capture/Rules、批次 10 验证记录。

验收：基类集中入口覆盖 Initialize、Uninitialize、Owner 变化；基类先清自身再调用派生 Hook；Owner 失效到空值也能识别；ZZZ 清除全部运行时表现数据和无所有权上下文；保留批次 10 映射与配置；不修改范围外文件。

### 临时实现 B：Animation 生命周期自动化夹具

状态：已交回并冻结；组长已复核测试夹具、生命周期矩阵、D5 映射与测试配置链接边界。

唯一可写：

- `Source/GGYGO/Animation/Tests/GGYGOAnimationLifecycleTestTypes.h`（新增）
- `Source/GGYGO/Animation/Tests/GGYGOAnimationLifecycleTest.cpp`（新增）

只读依赖：临时实现 A 的冻结接口、Animation Runtime/ZZZ 公共与受保护接口、现有 Automation Test 与 transient world 夹具范式。

验收：测试安全默认值、重复 Initialize/Uninitialize、`A -> nullptr -> B`、Owner 变化帧不泄漏公共派生字段/Memory/Snapshot/上下文；夹具只存在于测试文件，不修改生产类，不依赖生产资产。

## 文件交接

- 临时实现者只能修改其唯一可写路径；如需新增或改动其他文件，先停止并报告，不自行扩租约。
- 完成后停止写入，报告实际文件、静态验证与未验证边界。组长复核并将状态改为“已交回并冻结”后，文件才进入整合。
- 两个临时实现的写入集合互不相交。实现 B 可只读跟随实现 A 已明确的接口名，但不得改运行时文件；接口若有变化，由组长先冻结 A 再通知 B 调整。
- 生产资产、全局台账、并行排程、统一构建、UE 自动化、Git 提交与推送均不在本批会话的写入权限内。

## C18 / R2-I1 拆分预检（2026-10-01，统筹已授权）

本节追加当前授权，不改写以上 D6 历史，不恢复临时子代理机制。Animation 资产组长直接实现；当前唯一目标是为冻结 R1 提供公开反射的完整曲线语义值副本。所属模块为 GGYGOEditor，依赖方向冻结为 `Python → SnapshotLibrary → R1 ReadLibrary → 当前公开 DataModel`。R1 继续唯一负责读取、校验和错误；本层每次恰好调用一次 `ReadFloatCurves`，不直接访问 Source/DataModel，不另建查询或校验链。

### 唯一写入范围与基线

| 文件 | C18 开始基线 | 唯一写入者 / 阶段 |
|---|---|---|
| `Source/GGYGOEditor/Public/GGYGOAnimationCurveSnapshotLibrary.h` | 不存在，新增 | Animation 资产组长 / I1-S |
| `Source/GGYGOEditor/Private/GGYGOAnimationCurveSnapshotLibrary.cpp` | 不存在，新增 | Animation 资产组长 / I1-S |
| `AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 5448 bytes；SHA256 `86A69DB0C5CE13AEAA0535E1161B7DB0698779589D6CB4570ADB84C82A261B07` | Animation 资产组长 / 预检、I1-V 仅追加 |
| `AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 8982 bytes；SHA256 `510EF2F6C667A6D85D5431189A166C1BB284C781B3BE503FA214873EE262788B` | Animation 资产组长 / 预检、I1-V 仅追加 |

### 已冻结的三层 DTO 契约

三类均为导出的 `USTRUCT(BlueprintType)`，字段均在 `public` 下标记 `UPROPERTY(BlueprintReadOnly)`；这里只确认候选元数据，不提前声称实际 Python 字段可读。

| 结构 | 字段与精确类型 | 来源 |
|---|---|---|
| `FGGYGOFloatCurveKeySnapshot` | `float Time, Value, ArriveTangent, LeaveTangent, ArriveTangentWeight, LeaveTangentWeight`；`int32 InterpMode, TangentMode, TangentWeightMode` | `FRichCurveKey` 六个 float 直接赋值；三个 `TEnumAsByte` 通过 `.GetValue()` 后 `static_cast<int32>` 原值复制 |
| `FGGYGOFloatCurveSnapshot` | `FName Name`；`int32 Flags`；`float DefaultValue`；`int32 PreInfinityExtrap, PostInfinityExtrap`；`TArray<FGGYGOFloatCurveKeySnapshot> Keys` | R1 曲线的名称、flags、RichCurve 默认值、两侧外推及原顺序的全部 keys |
| `FGGYGOFloatCurveReadResult` | `bool bSucceeded`；`TArray<FGGYGOFloatCurveSnapshot> Curves`；`double DurationSeconds`；`FString Error` | 单一函数返回值；成功完整提交，失败 false / 空曲线 / 0 时长 / 原 R1 Error |

唯一新增函数：`UGGYGOAnimationCurveSnapshotLibrary::ReadFloatCurveSnapshot(const UAnimSequence* Source, const TArray<FName>& CurveNames)`，`BlueprintCallable`，返回 `FGGYGOFloatCurveReadResult`，没有 bool 主返回配 out 参数。Hidden 的原生 `RCIM_None` / `RCTM_None` 在 Python 枚举导出中不可用，因此使用各字段所属原生枚举的 int32 数值，不做枚举名称、重编号或默认替代；模式是否合法仍由 R1 判定。float / double 精度、顺序及 MAX_flt 均保持。

### 原子步骤、依赖与停止点

1. **预检登记（本节及 Validation 追加）**：关闭文件范围、字段和责任归属；只读依赖为冻结 R1/T1、UE 原生曲线类型及 Python 转换实现、旧 R2 报告、租约登记和架构导航。验收为四文件范围明确且没有重复查询/状态权威。完成后进入 I1-S。
2. **I1-S（仅两个新源码）**：关闭单一结果及完整值映射契约。验收为 R1 调用恰好一次、全部字段直接赋值、仅全量成功后发布、失败原错误可见、没有 source/model/view/handle/cache；静态审查后记录 SHA256 并冻结源码。
3. **I1-V（仅两个记录追加）**：关闭静态交回证据。依赖 I1-S 已冻结；验收为源码和保护文件 hashes、原记录字节前缀保持、差异与清理责任完整，明确编译/反射/Python/资产回读未执行。完成后四文件全部停止写入，交回统筹。

非目标：R1/T1/旧探针与报告、Engine/GAS 权限、Build.cs、运行时 Animation/Movement、测试夹具、骨骼/Graph/KeyHandle/编辑器元数据/底层 Channel 或磁盘字节、生产资产、Obsidian/全局笔记、构建、UE、脚本执行与 Git。不得加载/修改/保存资产、求值/重建/自动切线/重采样曲线，或增加资源、状态机、计时器、日志兜底。返回数组为调用者拥有的独立值副本，仅表示该次读取；后续资产变化须明确再调用，没有自动刷新或执行权。

停止条件：需要第三个源码、改共享接口/校验规则、扩大文件范围或发现无法在本契约内解决的架构问题时，停止并报告；不自行扩大租约。动态门禁及专项/新探针由统筹另步授权，不能拿此前 R1/T1 或第30次门禁证明新 DTO。

### C18 阶段交回（2026-10-01 01:26 +08:00）

- I1-S：两个新源码已完成静态审查并冻结。header 115 行 / SHA256 `FBC50BC68D61B5E8FB7E8C7C890664D1858BEB26E3070A6A6D6F42496D74ED0E`；cpp 55 行 / SHA256 `163E24B67FEAFEABBE0B29C7D7B49A6FBC56B4D7E96112193956B22BFAF89490`。三个 DTO / 19 个公开只读属性 / 一个单结果函数，cpp 仅一次 R1 调用；原生字段、模式数值、顺序与精度直接复制，完整映射后才提交成功。
- I1-V：本记录与 Validation 仅追加实际静态证据，源码未继续写入。R1/T1/旧夹具、Build.cs、旧探针/报告、旧审计/测试和 Report25 共13项、旧 R2 的14项资产/配置，实际 hash 均保持；完整值列于 Validation。预检追加后原记录字节前缀 hashes 均保持，最终交回再次读取核对。
- 清理责任：R1 原生数组、候选数组与错误均为调用局部值；结果为调用者拥有的独立值副本，不含对象/模型引用、句柄、缓存或任务。无新增需要解绑的资源，没有第二事实来源或运行时执行入口。
- 未验证：本次没有编译/UHT/UE/Python/脚本或测试；公开 metadata 仅为可读候选，不能标记 Python 完整曲线回读成功。后续专项、新 probe、资产动态、统一构建与 Obsidian 同步仍须统筹独立租约；详细边界见 Validation。本轮不得继续扩展。
- 四文件停止写入并交回统筹；最终文件 hashes 与完整追加差异随交回读取提供。以上 D6 历史授权及状态保持历史，不创建或唤醒临时代理。

## C20 / R2-I1-T1 专项预检与授权（2026-10-01）

统筹已接受零写入预检并登记 C20。Animation 资产组长直接实现，唯一目标为冻结 Snapshot 接口的独立 Editor 专项；不恢复子代理。只允许以下三文件，以上 D6/C18 内容保持历史：

| 文件 | 开始基线 | 原子阶段 |
|---|---|---|
| `Source/GGYGOEditor/Private/Tests/AnimationCurveSnapshotTests.cpp` | 不存在，新增 | T1-S 唯一测试源码 |
| `AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 11731 bytes；SHA256 `F17756CA793E713711ECAE8C7704C5DE4B36AAFAA95F5EDA642CCE9F707D89F3` | 预检、T1-V 仅追加 |
| `AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 21052 bytes；SHA256 `9F22F19E5EE72848401F5043C819A7B1E5B6B7029A7A473197103DE0ED1474C5` | 预检、T1-V 仅追加 |

顺序：两记录登记契约/基线 → T1-S 一个 cpp 实现并静态审查、hash 冻结 → T1-V 两记录仅追加证据 → 三文件交回停写。无生产或共享接口改动前置。只读依赖：SnapshotLibrary h/cpp、R1 h/cpp、原 AnimationCurveReadbackTests.cpp、AnimationAssetSafetyTestUtils.h、Build.cs，以及 UE Controller/DataModel/反射类型。

唯一新叶 `GGYGO.Editor.Animation.FloatCurveSnapshot`；四族及完整前置成立后的调用数量冻结为：

1. 反射：三结构 9/6/4 共19字段，精确属性类型、公开/BlueprintVisible/BlueprintReadOnly、数组嵌套结构和函数实际返回 Struct。
2. 成功/独立副本：clean/dirty 各乱序读与修改 DTO 后重读，共4 Snapshot；精确比较完整曲线/九 key 字段、float/double 数值位模式、源公开内容/时长/model/dirty 保持。
3. 失败：clean/dirty 各 null-source 和 valid-then-missing，共4 Snapshot +4 同输入真实 R1 失败对照；false/空/0/Error 全文一致，两个真实调用之间分别观察源不变，不手工重置 dirty。
4. 原生代表模式：复用原 T1 已用组合验证 RCIM_None、RCTM_None、RCTM_SmartAuto，共3 Snapshot；Controller 写入后先核对真实 Model 全字段，再读 DTO。原 R1 的19模式矩阵不重复，本层无模式分支。

夹具直接复用现有 Package()/Sequence()，新增曲线只通过真实 Controller；断言助手仅捕获/比较公开内容，不复制生产 validator，不伪造读取函数或填默认。标量位模式检查只比较独立 float/double，不比较整个对象字节；结果及源不变断言不代表 Channel/磁盘/骨轨/Graph 等价。临时对象沿用既有 GC 生命周期，无 AddToRoot、强制 GC、世界或额外资源句柄。

停止点：真实 API/夹具/反射前置不足、Controller 改写必需字段、需要修改共享头/生产/原测试/其它文件时立即停止交回，不放宽断言、不构造假 Model。非目标为 UE/构建/Git、Python 新旧探针、七生产资产/Graph/迁移、Obsidian、其它记录和子代理。未经统筹安排不得动态运行；T1-S/T1-V 仅记录静态未验证。

### C20 静态交回（2026-10-01 15:06 +08:00）

- T1-S：新增专项 cpp 333 行，一个 `GGYGO.Editor.Animation.FloatCurveSnapshot` 叶；已静态审查并在 T1-V 前冻结，SHA256 `3EA70519D60CC14ED87EF75B40DC57E4BF5B20FB144A58C26D72C28BDF129C4D`。原生 API、UHT 生成字段/返回类型只读对照依据列于 Validation，没有修改生成文件或生产接口。
- 四族全部已编写；完整通过路径静态计数为成功4+模式3+失败4=11 Snapshot，失败对照4 R1。两种 dirty、完整字段/数值位模式、请求顺序、副本修改、源公开内容/Model/时长/dirty 及失败原错误均设断言；计数在叶末明确检查，前置失败立即返回，不假称实际执行。
- T1-V：仅追加两记录；C20 前字节前缀11731/21052 bytes 及受保护源码/夹具/Build.cs/旧探针报告保持，14生产资产/配置 hash 逐项一致。最终三文件差异/hash与前缀复核随交回读取输出。
- 未运行：新增 cpp 没有编译/UHT/UE 自动化/Python 实读。31/32历史 C18 编译证据与原 R1 Success 不证明新叶；32总体62 Success/2 Fail状态保持。真实夹具若不满足新严格前置，后续门禁真实失败停止，不放宽或抢改共享头。
- 架构/清理：只有同步测试局部值和临时 Package 对象，复用原夹具GC生命周期；没有第二生产校验链、执行入口、持久缓存或资源/世界订阅。Obsidian依租约保持冻结，C18接口及新增专项状态同步仍留统筹文档阶段。
- 三文件全部交回停写；后续统一构建/运行须统筹安排。无其它写入、UE、Git或代理。

## C27 / 11-R3-V1 唯一事实同步预检（2026-10-01）

统筹已在全局台账/排程登记 C27；本组长直接完成两记录事实同步。唯一目标是将第34次完整构建、C20完整专项及R3单源Python真实读回的已发生证据写入当前状态与追加段，保留旧失败和未覆盖边界，不恢复子代理。

| 精确文件 | C27开始基线 | 唯一写入者 |
|---|---|---|
| `AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 16321 bytes；SHA256 `A374C6DB4057F1F74DC4B9C618F7CE4852F4EBCAD454E25AAEEE772FC1F34C4C` | Animation资产组长，仅顶部状态与C27追加 |
| `AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 30048 bytes；SHA256 `0A27CED65F81CD06F88E873CB0D0CDA6A4236BF382C2B9815389F57D3DF10815` | Animation资产组长，仅顶部状态与C27追加 |

职责/依赖：本步骤属于Animation资产验收记录；冻结的读取方向继续为 `Python → SnapshotLibrary → R1 → 当前公开DataModel`。R1、DTO、C24测试、共享夹具及C25脚本不换手；只读使用33/34报告、R3原JSON/日志、旧R2失败证据和统筹进程退出/源码保护回传。与Movement C26源码/10记录互斥，无共享状态或写入文件。

顺序与唯一结果：P登记两文件范围/基线 → V更新顶部当前状态并追加真实证据/根因/剩余边界 → F全文及历史保留核对、只读保护hash复核、两记录hash交回并冻结。每步都只写上述两文件，P完成前不改当前状态；V不运行验证，F不续开源码或资产工作。

验收：34报告实际65 Success且C20四族11 Snapshot/4直接R1完整通过；R3恰好两调用、四条完整曲线/176键、公开字段/数值位/完整错误及8阶段和最终14保护/dirty保持；报告hash可定位。原R2失败、33夹具失败与所有D6/C18/C20历史正文保留，历史“未运行/待验”由顶部明确为当时状态。限定为当前公开Model/DTO和Walk_Start，不宣称Channel/磁盘、骨轨/ABP图、其余六源、Profile迁移、生产Run或全模块完成；七Profile仍null，独立B0诊断Fail及笔记差异保留。

非目标/停止点：源码、测试、共享夹具、脚本、报告、资产、Obsidian、其它记录及全局入口全部只读；不执行UE/UBT/构建/Git或代理。发现基线/证据不匹配、第三文件需求、职责/接口变化或写入冲突即停止交回。局部结构/流程Markdown与Canvas须另行预检和授权，本步骤不得称架构笔记全部同步。

### C27 实际事实同步与冻结交回（2026-10-01）

- 第34次统筹完整Editor构建实际 `Succeeded`，10 actions / 29.34秒 / UBA 26.05秒 / exit0，编译C24专项并链接新运行时/Editor DLL。常规报告北京时间16:31:45（08:31:45 UTC）实际65叶全部Success，其它计数0，总0.73139739036560059秒，旧65路径无增删；`Saved/AutomationReports/ModuleRepairGate_20261001_34/index.json` SHA256 `BCF9F4E34000DF97FF65640FB0DB9F954D8AEDAD8A4F598939D55723D3557E88`。
- C20 `GGYGO.Editor.Animation.FloatCurveSnapshot` 实际Success，0 Error / 0 Warning / entries空，0.00861389935016632秒。真实1/1帧率与Outside原生前置成立，四族及末尾11 Snapshot / 4直接R1计数完整通过；19实际反射字段、完整值/原生模式/数值位、clean/dirty、独立副本及原失败全文均保留。C24测试349行，SHA256 `B1360B36C27492BB8205962CDF5D3E8446CDB862943761246E85454B6DDA9BAA`。
- 原33的 `SnapshotOutside.ActualFixture.Keys[0].LeaveTangent` 位比较前置失败保留；C24只修正独立原生预期，保留原Linear/Auto输入，以Channel的double除法→float及回写比例计算首键LeaveTangent（float32 5/3）。R1/DTO/共享夹具未改，没有容差或由DTO/实际Model反推预期。原R2 protected字段/None失败也保留，根因与33的夹具预期问题分别记录于Validation。
- C25脚本448行，SHA256 `5D1FE34066612A44F1071B28ACF37B90E8109BF499A9CFF31ADA0838EC0D0ECD`；统筹已静态接受两处最新构建/同版C20门禁文字，随后实际R3新DLL只读运行通过。报告 `Saved/AnimationCurveReadback/ReadFloatCurveSnapshot_Python_20261001_R3.json` SHA256 `FECD2B9B4D5C36BB8E50982C0462C79ED22DE5DCDC904FE5A8D948919B2FFCEA`，北京时间16:35:12.566160–16:35:13.135390，`complete=true` / `status=walk_start_complete` / 脚本exitCode0。
- R3恰好两次Snapshot：null为false/空曲线/+0并保留原R1错误全文；Walk_Start四条曲线86/86/2/2 keys共176，duration 1.4166666269302368，全部固定公开字段可读，1062 numericProof / 1616 fieldReads。MAX_flt默认哨兵数值原样保留；JSON按binary64位比较，包括零符号位。8阶段和最终14保护hash、dirty content/maps全部保持，无资产保存。
- R3日志实际verbosity为0 Error / 2 Warning（DDC写路径、Python重名）；结尾LogInit Display转述不重复算作4次Warning。常规65叶通过不关闭独立B0严格来源诊断Fail；统筹回传三个UE PID39308/43312/13868均exit0并退出，242源码及14保护在其窗口保持。本组只读核对报告/日志/冻结文件，没有运行UE/构建/脚本或Git。
- 本步先追加预检，原16321/30048 bytes前缀SHA256保持；随后只替换顶部当前状态、增加历史说明并追加C27事实。历史D6/C18/C20及旧失败均保留；最终全文、历史逆向核对与两记录SHA256随交回提供。两记录完成本步同步后停止写入，其余范围不解冻。
- 有限闭合：当前公开DataModel→DTO的独立专项及Walk_Start完整公开DTO→Python→JSON单源传输已通过。底层Channel/磁盘等价、骨轨、ABP/BlendSpace图、其余六源完整字段、七Profile创建/引用迁移、生产Run、PIE/网络及既有非法真实源夹具缺口仍开放；七Profile仍null。Obsidian结构/流程Markdown与Canvas尚未同步本接口和新状态，后续须单独预检精确范围，不把C27记录当成笔记全部同步。

## C28-A / 11-Curve-M1-A 拆分预检与授权（2026-10-01）

统筹接受C28三阶段方案并正式授权本原子步骤；Animation资产组长直接执行。唯一结果为纠正当前Locomotion曲线运行时契约的两份Markdown，保留历史/未验证/未完成边界；不是实现新架构。C27两记录已冻结并由统筹串行交回，本步仅登记、更新顶部当前状态及追加证据，不改D6/C18/C20/C27历史。

| 精确文件 | C28-A开始基线 | 本步范围 / 唯一写入者 |
|---|---|---|
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/曲线处理.md` | 3299 bytes / 24行；SHA256 `87A39B997D9B42A0933154E5D1A5109D2FCE3B10D1D7A0D47DBB216F795F389D` | 当前曲线契约全文纠正 / Animation资产组长 |
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/结构.md` | 5670 bytes / 39行；SHA256 `A7A323C50AF9477E311A387B2E13C812491EED6F1224EF6981BD22485A4D7B98` | 曲线接口、Editor边界与图文阶段状态 / 同一组长 |
| `AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 22715 bytes / 176行；SHA256 `7851201CCD2836A69186CC5F35E9EAE01C2C501A5D31EE7A4F6C80DD3C582035` | 本节预检、顶部当前状态及末尾追加 / 同一组长 |
| `AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 41780 bytes / 301行；SHA256 `836329895895A27CFD497D42747A5F364AFF8FA9C8EC8A32EC36E85FC1D28105` | 顶部当前状态及C28-A实际静态证据追加 / 同一组长 |

### 唯一运行时契约与责任

依赖方向为 `已接受MovementSet → 独立Locomotion Profile → CMC移动模拟求值/当前样本 → CMC速度/朝向与原生RMS执行`；Animation从Pawn/CMC/ASC只读Capture事实。Profile的 `EvaluateInterval(t0,t1,out,error)` 是无播放状态的纯求值：成功提交完整样本（合法零速仍有来源），失败输出Reset并可返回字段原因；非循环Clamp、循环相位和Yaw按周期解绕。CMC唯一持有运动语义、单次段时间、WalkRun共相位/混合及当前CurveMotion；SavedMove恢复语义/时钟基线后由CMC重演求值，不保存CurveMotion。RMS仅消费当前样本，以安装时BaseYaw转换方向，挂载/移除由CMC与原生RMS生命周期负责；其引擎Source时间不是第二Profile播放器。

旧Sampler的GetCurveValue、Cfg_ClipLength来源标记及跨帧位置/Yaw差分只写历史/遗留工具，无当前CMC调用。C26三个getter源码已由原作者冻结并获统筹逆向接受：cpp `1AD15D3B4FCF36950B620D655B8B9414535C5B4DA65800E06D747B89287896FF`、h `00C3B5A3E7DC963403D8D0FC5D67F361B09ABC40CA1983C20974A04DE89D0C7A`。成功资格不以正速阈值判定；未编译/专项，完整失败传播未关闭。写明当前忽略求值失败/推进时间、单Loop替代、固定速度消费及RMS缺方向替代的源码后果，不把理想拒绝当已实现。R1/DTO仅为GGYGOEditor独立只读同步值副本接缝，详细作者工具图文另阶段候选。

### 原子顺序、只读依赖、断言与停止点

1. **P登记**：先追加本节，核对四文件基线及保护范围；原两记录完整字节前缀保持，再进入M。
2. **M纠正文档**：仅上述两MD，关闭运行时事实矛盾；不改Animation生命周期/战斗资产正文。两张曲线Canvas保持原字节并标明B/C待同步，不以MD完成声称全图完成。
3. **V核对交回**：仅两记录更新顶部状态/追加实际差异、全文/链接/保护/历史保留及未验边界；四文件hash交回后全部停止写入，不自动执行B/C或Editor图文。

只读依赖：已冻结的MovementSet/Locomotion Profile/MovementTypes、CMC三getter及求值/预测、CurveRMS、遗留Sampler、AnimationStateCapture；本地UE5.8原生PerformMovement/RMS顺序；R1/DTO四生产源码、已发生C20/R3证据；计划蓝图、Animation主/曲线图、动画计划、Movement结构与模块参考导航。实际SavedMove源码优先于RMS头旧注释。C29测试cpp与10记录属于其他写入者，不读取/使用其夹具结果，也不声称其构建或运行已发生。

验收断言：接口输入/成功失败输出/状态唯一归属准确；WalkRun共相位和Yaw解绕不写成动画帧差分；速度来源资格与数值大小分开；失败当前后果及合法固定配置分别可定位；SavedMove恢复语义/时钟再求值；Animation不反写Movement；Editor不成为运行时输入；链接目标/锚点真实存在；两记录历史除顶部状态/历史说明外逐字节保持；保护文件hash保持。未新增循环依赖、状态/执行链或清理责任。

非目标：任何源码/test/script/report/资产/配置、Movement笔记、全局入口、主Canvas、两曲线Canvas、动画计划；不UE/构建/脚本执行/Git/代理。发现基线或保护异常、需第五文件/改共享接口/实质改变已确认架构/资产迁移时停止交回供统筹和用户决定。本步仅当前事实纠正；B、C及Editor子图均须另授权。

### C28-A 实际静态交回与冻结（2026-10-01）

- P先登记四文件精确范围；Subleases原22715 bytes完整前缀实际SHA256保持 `7851201CCD2836A69186CC5F35E9EAE01C2C501A5D31EE7A4F6C80DD3C582035`，随后才改两MD。两记录最终仅顶部当前状态/历史说明与C28-A追加，D6/C18/C20/C27历史正文及失败证据不改。
- M已纠正整个旧当前链路：Profile纯区间求值/Clamp与循环Yaw解绕、CMC唯一语义/时间/样本、WalkRun共相位双侧插值、RMS当前样本与安装朝向、SavedMove恢复语义/时钟再求值、Animation只读Capture；旧Sampler/Cfg来源/跨帧差分归入历史，Editor R1/DTO仅简要独立接缝。实际diff没有修改既有战斗资产或Animation生命周期正文。
- 两MD冻结结果：曲线处理.md 97行 / 13047 bytes / SHA256 `CA0DB46AC8E7BDC0B5B6383331AF04BD8FC4D2A21B52B354FCF97E70CD870757`；结构.md 55行 / 9301 bytes / SHA256 `FE5CD15F517159B463E7F818B8CAF8837811FB320B57632D69E9F5F2D189183D`。完整接口/当前失败后果与未验边界见Validation本步节。
- 全文与23处Wiki链接（20个唯一目标，含两个新增曲线节锚点）核对通过。48项限定保护分为C27原14份源码/夹具/Build.cs/脚本/报告、15份运行时生产依赖、14项资产/配置及5份Canvas/动画计划，hash均保持；不称自行保护或复测全242源码。
- 两曲线Canvas保持原SHA256 `00E704EDA0004E318AF0495C872938D53AC60BD5ECC872232C5937FBDF5099BC` / `82C1D18FCAA97241006D56768D7584C2A341A59F4EF25412A4C9B53B759F9DD8`。两MD明确它们仍含旧执行链、B/C待同步；动画计划和详细Editor图文未同步，根独占模块参考已由统筹维护，本步不抢写。
- 未运行UE/构建/Git/代理/脚本或C29夹具；C26静态资格修正不升级为运行Success。当前失败后固定速度消费、单侧Loop替代、失败推进/无效段完成及RMS方向替代仍开放，七Profile引用既有证据仍null，生产/网络动态待验。本步不改变已确认架构或状态所有权，无新循环依赖、执行链或清理责任。
- 四文件hash、实际差异、历史逆向及保护核对随最终交回提供；本原子步骤完成后全部停止写入，不自动进入B/C或Editor子图。需要实质架构修正仍先交统筹与用户决策。

## C28-A / 11-Curve-M1-A 第35次门禁有限事实补充（2026-10-01）

统筹在C28-A首次冻结后回传实际第35次门禁，明确仅续更原四文件当前事实，不扩大租约、不重做预检。此前四文件hash为Subleases `A3CC9523D490401B1A853DDCBB65023B7455C2BA9225A97BCAC48910B6B297A3`、Validation `B26B0649F4293613988E9B543A13BA8533B4D38418ABD973B838FD53AF73F9A6`、曲线MD `CA0DB46AC8E7BDC0B5B6383331AF04BD8FC4D2A21B52B354FCF97E70CD870757`、结构MD `FE5CD15F517159B463E7F818B8CAF8837811FB320B57632D69E9F5F2D189183D`，开始实际核对一致；原首次交回的未编译/专项状态保留为历史。

- 本组只读核对35原报告与构建/原始日志；构建实际6 actions / Succeeded / 34.99秒 / UBA32.04秒，新运行时DLL已链接，exit0由统筹回传。报告 `Saved/AutomationReports/ModuleRepairGate_20261001_35/index.json` SHA256 `F2DFBCF244512B11EB669D29DFAAD2C21310103E9D9EDA74D098B5ED8A1718A6`，北京时间17:37:52（原09:37:52 UTC），65 Success/其它0/总0.7469504475593567秒。
- `GGYGO.Movement.Locomotion.AuthorityAndMapping` 实际Success / 0.00962350144982338秒 / entries空 / 0 Error / 0 Warning。据统筹严格消费者断言范围，有限证明合法零/极小正速/零Scale资格与GetMaxSpeed/ForceWalk、显式fixed模式；失败/溢出只证明资格拒绝，不证明完整失败传播。ActionMotion与C20仍Success；实际时长及日志证据列于Validation。
- 当前两MD已将C26状态改为35有限实证，并补RMS内部方向/非有限消费未关闭；原子步骤仍只纠正已发生事实。曲线MD 99行/14198 bytes/SHA256 `2128D728E8A5988E07D7B3CA46D41D28FDAFADF1D16F7A2DEA66341424874B13`；结构MD 55行/9531 bytes/SHA256 `5B77F4ABA5F765A1D738DA974E9787CC3D7CC87A804A52E80D7900E364034F8A`。两记录仅顶部两段及本节追加，前次C28-A和D6/C18/C20/C27正文保持。
- 原始35日志实际49 Error/2 Warning（AutomationTest13、AbilitySystem34、Animation2；DDC/Python各1），尾部Display转述不重复计数；不能称全日志干净。统筹回传UE40532 exit0且已退出、242源码/14保护保持。本组仅复核限定保护集合和原报告，不自称独立验证全部242源码。
- 最终全文、23处链接/锚点、原48项保护及35报告/构建/原始日志3项保护、历史逆向和四hash随交回核对；原两曲线Canvas继续原字节，B/C和Editor子图尚未授权。不写源码/test/script/report/资产/Movement笔记/全局入口/主图，不运行UE/构建/Git/脚本或代理。
- 求值失败被忽略、WalkRun单侧替代、失败推进时间/非法Profile完成、固定步态失败消费、RMS方向替代/非有限内部消费、七Profile引用null及资产/网络/生产Run仍开放，B0历史严格诊断Fail保留。四文件续更完成后再次冻结交回，不自动进入B/C。

## C28-B / 11-Curve-M1-B 结构图原子步骤登记（2026-10-01）

统筹已接受A并登记B，Animation资产组长直接执行；复用已接受C28-A/B/C预检，不重新扩展调查。唯一结果是将旧动画曲线结构Canvas纠正为冻结运行时的类/数据/接口与状态归属，保留35有限通过和失败消费边界，不修改架构或执行实现。

| 精确文件 | C28-B开始基线 | 唯一写入者 / 本步范围 |
|---|---|---|
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/GGYGO_结构_动画曲线.canvas` | 170行 / 5234 bytes；10节点/8边；SHA256 `00E704EDA0004E318AF0495C872938D53AC60BD5ECC872232C5937FBDF5099BC` | Animation资产组长 / 当前结构事实、关键接口、真实链接与必要排版 |
| `AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 226行 / 32934 bytes；SHA256 `B53B76F2F7608F3A4F6FD3CC452CBF1B61A7DE46DBC73E875E6C1EE3A85E29BC` | 同一组长 / 先登记本节，随后仅顶部两段与B证据追加 |
| `AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 370行 / 53598 bytes；SHA256 `07A80FFBDC024AA666C108BAAA197D0BE126554A960F41A7C023943D5CE7391E` | 同一组长 / 结构图冻结后仅顶部两段与B证据追加 |

唯一契约：MovementSet明确固定/曲线模式并持有七Profile引用；Profile纯EvaluateInterval(t0,t1,out,error)返回完整成功样本或false/Reset/可选原因；CMC owns语义、唯一模拟时钟及CurveMotion，负责配置接纳、三getter及RMS安装/移除。Sample来源资格与HasUsableSpeed幅值分开；RMS只读当前样本、固定安装BaseYaw执行，Source时间不是第二Profile播放器；SavedMove保存/恢复语义/时间基线再由CMC重演求值，不持有CurveMotion；Animation Capture只读CMC/ASC事实，旧Sampler只作历史且无当前CMC调用。R1/DTO编辑器作者工具不接入运行时链，详细Editor子图未授权。

顺序：P在本节登记三文件范围/基线 → G仅制作结构Canvas并完成JSON/接口/链接/容量/无重叠检查，先明确冻结图 → V仅两记录更新顶部当前/追加实际证据 → 三hash交回全部停写。A两MD、C流程图与导航MD状态不在本步解冻，不以B完成声称全图文同步。

只读依赖：A两MD冻结版；MovementSet/Profile/MovementTypes、CMC配置/三getter/求值/预测、CurveRMS、Sampler、StateCapture/AnimInstanceBase、UE5.8原生移动/RMS顺序；R1/DTO边界；35报告/日志及统筹门禁回传；架构导航、Movement/ASC结构、原主图/流程图。已冻结证据直接复用，不读取C29源码夹具或重跑门禁。

布局方案与理由：复用全部10个节点ID及8个既有边ID，继续采用原三列层次。将Profile从底部“未实现目标”移到输入区，将Sampler移入底部独立历史区；增加节点宽高/行间距使输入输出、清理与失败边界可读，保留其余节点的相对列与可用颜色。Profile由计划色3改为数据色4，其余9节点颜色保持。重连旧反读边为配置持有/纯求值调用/返回/只读消费，增加一条CMC持有已接受MovementSet边；预测往返标签只表达语义/时钟快照，不创建第二权威。不新建节点或第四文件。

验收断言：JSON可解析，节点/边ID整体唯一、端点/方向有效且每边有明确类型标签；接口说明输入、作用、输出和状态/清理边界；节点正文以保守字号/换行估算留足容量，无矩形重叠；所有Wiki目标/锚点存在；当前链无Sampler/GetCurveValue或Editor→CMC箭头；SavedMove无样本权威；成功零资格与幅值阈值分开；35仅有限消费者通过，失败忽略/单侧替代/失败推进/GetMax固定分支/RMS内部方向与非有限消费仍开放。保护hash保持，原两记录除顶部两段与追加外历史逐字节保持。

非目标与停止点：不改A两MD、流程/主/其它Canvas、动画计划、Movement笔记、全局入口、源码/test/scripts/reports/资产/配置；不UE/构建/Git/脚本执行/代理。需第四文件、新架构/共享接口/状态归属或无法容纳的独立生命周期时停止交回供统筹/用户决定，不自动C/导航MD/Editor子图。图冻结后才补记录，记录完成后三文件全部停止写入。

### C28-B 实际结构图冻结与交回（2026-10-01）

- P先登记精确三文件及基线，Subleases原32934 bytes完整前缀实际hash `B53B76F2F7608F3A4F6FD3CC452CBF1B61A7DE46DBC73E875E6C1EE3A85E29BC` 保持；随后仅制作本结构Canvas。G全文/JSON/静态契约与链接核对后已明确先冻结图，再进入两记录V；没有继续改图或自动C。
- 结构图当前180行/11483 bytes、10节点/9边，SHA256 `6EC0EDF8F33EC54794E7A5718DE5AF5B6424BC1A84FEA7EAE8D687B5AD8775AB`。原10节点ID、8边ID全部保留，仅新增e9配置持有；9节点颜色不变，profile由旧计划色3改为数据色4。保留三列相对关系，Profile移到输入层，Sampler移入无运行边的历史区；增宽高/间距容纳输入输出与失败/清理说明，无新节点或第四文件。
- 当前结构为MovementSet明确模式/七引用 → Profile纯区间求值 → CMC唯一语义/模拟时间/CurveMotion → 速度/Yaw和原生RMS执行；SavedMove保存/恢复语义与时钟再求值，Animation Capture只读CMC/ASC。边明确持有、调用、返回、只读数据与预测基线往返；旧Sampler无当前调用，Editor无运行时输入边。各节点关键接口/输出/清理及当前失败后果见Validation本步节。
- JSON/ID/端点/侧向/箭头/全边标签通过；节点矩形无重叠。以正文18px/行高30、标题27px/行高38、内边距28px保守估算，10节点剩余高度66–368px；这是静态容量检查，未执行Obsidian原生主题/缩放视觉验收。14处Wiki/11唯一目标含锚点及Movement/ASC跨模块链接通过。
- 52项限定保护hash保持：前步51项集合去除本次目标结构Canvas，加A两MD；含其余Canvas/动画计划、生产依赖、旧新报告/日志/脚本、资产配置。流程图仍旧hash `82C1D18FCAA97241006D56768D7584C2A341A59F4EF25412A4C9B53B759F9DD8`；A两MD保持 `2128D728E8A5988E07D7B3CA46D41D28FDAFADF1D16F7A2DEA66341424874B13` / `5B77F4ABA5F765A1D738DA974E9787CC3D7CC87A804A52E80D7900E364034F8A`。A中“结构B待同步”的阶段字句仍待导航MD租约，本图/记录已明确该差异，不越权修正或称全图文完成。
- 两记录仅顶部两段与B登记/证据追加，D6/C18/C20/C27/C28-A及35历史保持；最终历史逆向/hash核对随交回提供。源码/架构/状态归属不改，无新增循环依赖、缓存、执行链或资源清理责任。
- 35仅成功零/极小正/零Scale资格与消费者有限通过；求值失败忽略、单侧Loop替代、失败计时/非法段完成、固定步态失败消费、RMS内部方向与非有限消费、七Profile引用null及资产/网络/生产Run仍开放。未UE/构建/Git/脚本/代理，原生Canvas渲染也未验。三hash/实际diff/检查交回后停写，不自动C/导航MD/Editor子图。

## C28-C / 11-Curve-M1-C 流程图原子步骤登记（2026-10-01）

统筹接受并冻结B后，仅授权C流程Canvas与11两记录；Animation资产组长直接执行。复用已接受方案和冻结契约，本步唯一结果为按真实触发者/接口/参数/产物/分支纠正旧Sampler反读流程，不实现新架构或改代码。

| 精确文件 | C28-C开始基线 | 唯一写入者 / 范围 |
|---|---|---|
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/GGYGO_流程_动画曲线处理.canvas` | 178行 / 5313 bytes；10节点/9边；SHA256 `82C1D18FCAA97241006D56768D7584C2A341A59F4EF25412A4C9B53B759F9DD8` | Animation资产组长 / 当前真实模拟流程与必要分支排版 |
| `AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 258行 / 39979 bytes；SHA256 `EF8F3CA95A08CDB7C51EE7AABC99FD48A73D76FCE86AC4C67BC1E774E53F1A65` | 同一组长 / 先登记，再仅顶部两段及C追加 |
| `AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 410行 / 60741 bytes；SHA256 `93AAD124ABCFE509369F617FFFF8A653F5DCA1F09C85AE93AE22E8BA9588F6E6` | 同一组长 / 流程先冻结后仅顶部两段及C追加 |

唯一流程契约：显式配置装配/切换SetMovementSet形成接纳状态，不伪装每步配置写入；UE权威/自主PerformMovement每move走BeforeMovement分支、CMC语义/单段或WalkRun共相位纯求值与当前失败结果、可选RMS安装/消费、原生早期速度累积、StartNewPhysics内普通/Override速度物理、AfterMovement再PhysicsRotation。Profile提交不必经RMS；无RMS普通曲线/显式fixed路径要独立。SavedMove恢复语义/时钟后重演同链；Animation在独立更新时机只读当时事实，数据连线不强制它在move末执行。

分支须按当前源码：Action仅跳过Locomotion并继续既有原生执行；未接纳配置清样本/自有RMS并准入保护，NetworkedMontage的最终判定可延后到CalcVelocity/ApplyRootMotionToVelocity；SimulatedProxy本地角色分支与独立引擎路径不升级为动态证明。WalkRun两侧分别求值，双成功混合、单成功替代、双失败Reset且已进入求值后仍推进相位；单段忽略false仍推进时间/转身语义；缺失/非法Profile完成、GetMax固定分支和RMS内部失败仍开放。理想统一拒绝未实施，不画成当前路径。

原生顺序只读依据：UE5.8 CharacterMovementComponent.cpp 2874 Before、2941 Prepare、2992早期AccumulateOverrideRootMotionVelocity、3034 StartNewPhysics、3042 After、3046 PhysicsRotation；PhysWalking5716 CalcVelocity/5720 ApplyRootMotionToVelocity以及本项目准入重写。Prepare使用移动早期bHasRootMotionSources快照且受clientUpdating/serverIgnore门禁；跳过Prepare不伪造“无Source”。其余原生前后置/碰撞流程按范围简述，保持必要权限/生命周期检查。

顺序：P登记本节/基线 → G仅流程图制作，JSON/接口/分支/原生顺序/链接/静态布局容量核对并明确先冻结图 → V仅更新两记录顶部与C证据 → 三hash交回停写。复用10旧节点ID及9旧边ID/可用颜色与输入→求值→消费层次；必要新增节点用于区分当前分支、回调/物理先后和观察/重演入口，不按类名机械拆分，不新建文件或独立子图。

只读依赖：A两MD、B结构图冻结版；MovementSet/Profile/Sample、CMC准入/Before/选择/求值/三getter/RMS/PhysicsRotation/预测、CurveRMS、Animation Capture及UE5.8上述原生顺序；35有限报告/日志、导航/相关模块结构。无需重复读C29源码或重跑门禁。所有共享接口与生产资产保持原归属。

验收：JSON可解析、节点/边ID唯一、端点侧向/方向/分支标签有效；节点动作/输入/输出可读、无矩形重叠且保守容量留余量；全部Wiki目标/锚点存在；Normal和RMS为可选物理路径，Prepare→早期累积→StartPhysics→After→Rotation顺序实际；当前失败后果可定位，重演复用唯一时钟，Animation只读关系不冒充调度；旧Sampler/Editor无当前执行链；35有限Success与proxy/七Profile/网络/生产Run未验分开；保护hash/记录历史保持。

非目标/停止点：B结构图、A两MD/导航MD、主/其它Canvas/计划、Movement笔记、全局入口、Editor详细图文、源码/test/scripts/reports/资产/配置全部冻结；不UE/构建/Git/脚本执行/代理。需第四文件、独立新子图、架构/状态/接口改变或不能在同一实际CMC模拟/观察范围表达时停交统筹/用户决定，不自行扩权。流程冻结后才补记录，C结束不自动导航MD/Editor。

## C28-C / 11-Curve-M1-C 流程图冻结与记录交回（2026-10-01）

- P→G→V已按依赖执行：先追加精确三文件预检（原Subleases的39979-byte前缀哈希仍为`EF8F3CA95A08CDB7C51EE7AABC99FD48A73D76FCE86AC4C67BC1E774E53F1A65`），再写/核对/冻结流程Canvas，随后才改两记录顶部与追加证据。图冻结后不再编辑；三文件交回后停止写入，等待统筹独立复核。
- 唯一图产物：`Animation/GGYGO_流程_动画曲线处理.canvas`，498行 / 22853 bytes；25节点 / 30边；SHA256 `E5C4E8CDA7165F72D1FDA89C214C2F6DCD60021A1284F20919F3FDBACBAC184A`。实际行diff（不使用Git，LCS）：+388/-68（178→498行）。 原10节点ID、9边ID及10节点颜色均保留；新增15节点/21边只是展开原有分支、原生阶段和独立数据入口，未新建子图、文件、执行机制或生命周期。相对列布局与颜色语义复用，并按正文扩充为3880×5570范围。
- 契约闭合于文档表达：SetMovementSet显式状态输入；Before按Action/未接纳配置/普通/Proxy代码分支；非WalkRun单区间和WalkRun共相位双条件调用分别返回；样本合流、可选Brake/TurnBack Source、普通/AnimRM-Override速度物理、After再条件PhysicsRotation；SavedMove起始语义恢复与独立Animation只读关联。方法/参数/产物/当前失败后果和时钟归属均写明。
- 原生顺序只读对照UE5.8：2846快照→2852清无效RMS→2874 Before→2918门禁/2941 Prepare→2992早期Override累积→3034 StartNewPhysics→3042 After→3044/3046条件PhysicsRotation；PhysWalking 5714/5716/5720分别为普通速度条件/CalcVelocity/ApplyRootMotionToVelocity。首次安装Source不保证同move Prepare；无RMS普通路径和结果提交不强制RMS。
- JSON全文回读一致；25唯一节点/30唯一边，端点/side/非空分支标签/有限正尺寸通过，23条关键执行/返回/入口关联检查通过；9处Wiki链接、5唯一真实目标和2标题锚点均通过。25正文按CJK18px/Latin10.8px、30px行高及标题/空行/56px内边距保守估算，余量106～114px；节点矩形0重叠。Obsidian原生字体、连线绕行及完整视觉渲染未验证，不能将静态几何记为视觉验收。
- A两MD、B结构Canvas、主图/计划、冻结生产源码、Editor/R1/DTO、14资产配置及既有脚本/报告/日志共52保护项回读哈希未变。未写第4文件，未读第10批记录，未执行UE/构建/Git/脚本/代理。只读范围偏差：一次rg把目标设为Source/GGYGO目录，误含Character/Tests，不能保留未读取C22/C29测试源码的保证；后续已恢复精确生产文件检索，测试未修改或运行，也未把该检索当新增测试验收。原历史主体保持，最终逆向复原B基线及三文件实际diff/hash随交回提供。
- 第35次事实不扩大：完整构建Succeeded/exit0，65项Success/其余0；AuthorityAndMapping只证明成功零/极小正/0Scale资格及GetMaxSpeed/ForceWalk、显式fixed消费者，失败/溢出只证明资格拒绝；原始日志49 Error/2 Warning历史证据保留。本步未新增动态验收。
- 单段忽略false/错误信息且仍计时、WalkRun单侧替代/双失败相位推进、非法Profile视为段完成、曲线失败转固定步态、RMS方向/非有限内部消费及当前非有限Yaw置0仍开放；七Profile既有引用null，ABP/迁移/Proxy/DS/PIE/网络/生产Run未验。A两MD历史“B/C待同步”导航及主图/动画计划/Editor细图未越权修改，后续独立租约处理。

## C28-NavM / 两Markdown导航与阶段状态原子步骤登记（2026-10-01）

统筹已独立全文接受A/B/C，其中B结构Canvas、C流程Canvas冻结。本次仅授权四文件，由Animation资产组长直接执行，唯一结果为清除两Markdown中“B/C待同步、两曲线Canvas仍是旧Sampler链”的过时导航/实施状态；不修改算法、接口或源码事实。

| 精确文件 | NavM开始基线 | 唯一写入者 / 写入范围 |
|---|---|---|
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/曲线处理.md` | 99行 / 14198 bytes；SHA256 `2128D728E8A5988E07D7B3CA46D41D28FDAFADF1D16F7A2DEA66341424874B13` | Animation资产组长；必要导航/实施状态段 |
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/结构.md` | 55行 / 9531 bytes；SHA256 `5B77F4ABA5F765A1D738DA974E9787CC3D7CC87A804A52E80D7900E364034F8A` | Animation资产组长；必要导航/实施状态段 |
| `F:/ue_project/GGYGO/AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 293行 / 48187 bytes；SHA256 `2B109FC5130461523D7FCA94BB5770CD6A2A4FED77DE5ADBFE13C8182E3D2E7A` | Animation资产组长；本预检、顶部状态与NavM证据追加 |
| `F:/ue_project/GGYGO/AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 448行 / 67311 bytes；SHA256 `E751D0B702184B122602C7FEE4C2B8D27FEEC618B422C48F4A6186E2BCFC689A` | Animation资产组长；顶部状态与NavM证据追加 |

### 拆分预检与停止点

- 职责：Animation说明入口的导航和已完成阶段记录；状态权威仍为冻结生产实现、报告及统筹已接受的A/B/C范围。无共享接口/状态所有权变更，依赖已冻结；不新增A5 Guard接口或Movement helper，两者实现/消费者必须另租约。
- 顺序：P登记基线/精确范围→M最小修改两MD（本文导航/结构导航及阶段状态）→Q全文回读/既有链接与锚点/源事实未变检查→F冻结两MD→V仅两记录顶部及NavM追加→四文件实际hash/diff/历史还原交回并停写。一个步骤只关闭导航/阶段契约，不捆绑图/Editor/代码修复。
- M目标：A Markdown、B结构与C流程仅已获统筹静态接受；图文可交叉核对当前运行契约，完整失败传播/RMS内部消费、七Profile/资产/网络/生产Run及原生视觉均未验收。保留动画计划/主图/Editor细图待后续；两Canvas自身nav旧字句交给独立NavC，不能写第5文件。
- 只读依赖：本四文件全文及已冻结A/B/C与既有验证证据；链接核验仅阅读指向目标的存在性/标题，不读写第10批两记录，不读生产/测试源码，也不执行脚本、UE/构建/Git或代理。两Canvas仅保护哈希，不打开写入。
- 验收断言：两MD旧“B/C待同步/旧链当现行依据”导航清除；新状态不把静态接受扩为动态/原生视觉/失败闭合。只改预定导航/阶段行，所有类/算法/接口/报告事实正文逐字不变；原Wiki目标/锚点有效；51项既有非租约保护哈希不变。
- 记录规则：两记录只顶部两段和本NavM登记/证据追加，原D6/C18/C20/C27/C28-A/35/B/C历史、失败证据与C的只读范围偏差原样保持。逆向删除NavM并恢复顶部应精确回到本开始基线。
- 停止点：MD冻结后不再编辑；出现第5文件、新源码事实/A5 Guard/Movement helper/Canvas导航或独立生命周期需求即停止交回，不扩权。最终四文件冻结交回，不自动NavC或Editor后续。

## C28-NavM / 导航状态冻结与四文件交回（2026-10-01）

- 依序完成P→M→Q→F→V：精确四文件预检登记后，两MD各只修改3行（曲线处理3/5/89；结构9/11/49），全文/链接/边界检查通过并先冻结，才改两记录顶部两段及NavM证据。四文件交回后停写，不自动NavC/Editor；不写第5文件。
- 冻结MD：`Animation/曲线处理.md` 99行 / 14486 bytes，SHA256 `7AF891EED02B76C91C7DEC08512BD197AE780E748F009CD249B03BDF688011FF`，实际LCS diff +3/-3；`Animation/结构.md` 55行 / 9757 bytes，SHA256 `68AC9EB01AA827C1AFFDABA0EB0F0DE663BADDFA0C2D27C9443EFA9997455AE2`，实际diff +3/-3。只清除A阶段旧“B/C待同步、两图仍旧Sampler现行链”的导航，改为已获统筹静态接受；不改算法/接口/sourcefacts。
- 原Wiki引用目标/锚点序列逐字不变，23处链接/18唯一目标/4锚点全部有效；`计划_玩家普攻连段` 以Obsidian唯一文件名定位到`AbilitySystem/计划_玩家普攻连段.md`，未改其链接或正文。两MD仅预定行差异，其余类/接口/算法/报告/历史Sampler和Editor边界正文逐字保留，0新增链接。
- 两Canvas仅保护，B `6EC0EDF8F33EC54794E7A5718DE5AF5B6424BC1A84FEA7EAE8D687B5AD8775AB`、C `E5C4E8CDA7165F72D1FDA89C214C2F6DCD60021A1284F20919F3FDBACBAC184A` 未变；图内部nav旧阶段字句交独立NavC。A/B/C静态接受可对照当前契约，不把其变为原生视觉/动态/失败闭合证明。Animation主图/计划/详细Editor图文仍待后续租约。
- 本步非租约51项保护哈希保持（C的52项去除本次两MD写权、加入冻结C流程图）；不冒称全242源码重新复核。没有读取生产/测试源码或第10批两记录，没有UE/构建/Git/脚本/代理或资产操作，未新增A5 Guard/Movement helper接口。源码、状态唯一性、依赖/执行链/清理责任不变。
- 两记录仅顶部两段和NavM登记/证据追加；截至C的全部历史与一次rg误含Character/Tests的偏差说明保持，不能由本步未读测试替C改写历史。最终逆向截去NavM并恢复C顶部两段须复原48187-byte `2B109FC5130461523D7FCA94BB5770CD6A2A4FED77DE5ADBFE13C8182E3D2E7A` 与67311-byte `E751D0B702184B122602C7FEE4C2B8D27FEEC618B422C48F4A6186E2BCFC689A`。
- 第35次有限消费者与49 Error/2 Warning原日志事实均保持；完整求值失败传播、RMS内部消费、七Profile既有null/资产接线、Proxy/DS/PIE/网络/生产Run和Obsidian原生视觉未新增验收。四文件hash/实际diff/历史还原及保护核对交回统筹，最终写入结束。

## C28-NavC / 两曲线Canvas导航节点原子步骤登记（2026-10-01）

统筹已独立接受NavM四文件并冻结两MD；本步独立授权以下四文件，由Animation资产组长直接执行。唯一结果为两图nav节点正文清除旧B/C/NavM待同步/C28步骤历史标记，提供当前结构/流程及配套说明入口；不是新图、新架构或代码修复。

| 精确文件 | NavC开始基线 | 唯一写入者 / 范围 |
|---|---|---|
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/GGYGO_结构_动画曲线.canvas` | 180行 / 11483 bytes；SHA256 `6EC0EDF8F33EC54794E7A5718DE5AF5B6424BC1A84FEA7EAE8D687B5AD8775AB` | Animation资产组长；仅id=nav的text |
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/GGYGO_流程_动画曲线处理.canvas` | 498行 / 22853 bytes；SHA256 `E5C4E8CDA7165F72D1FDA89C214C2F6DCD60021A1284F20919F3FDBACBAC184A` | Animation资产组长；仅id=nav的text |
| `F:/ue_project/GGYGO/AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 324行 / 54140 bytes；SHA256 `494504F0417166E56FC901FC1F57818E8E483270EC0FE7F901BA36998A18E46E` | Animation资产组长；本预检、顶部状态及NavC追加 |
| `F:/ue_project/GGYGO/AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 475行 / 70985 bytes；SHA256 `C9F19A4A92615C7B37ADF01500FE4B698B27CC930CB1A7E221F423B5500BDBAC` | Animation资产组长；顶部状态及NavC追加 |

### 拆分预检、验收和停止点

- 边界：Animation图的入口导航/当前静态可用状态。共享接口/算法/状态归属已冻结，不改变依赖方向或生命周期；不新增A5 Guard、Movement helper或消费者接口，不新建图。
- 顺序：P小预检/四基线及51非租约保护登记→N只替换两nav.text→Q JSON/链接/正文容量/反向文本与SHA256/保护→F先冻结两图→V两记录顶部及NavC追加→四文件实际hash/diff/历史还原交回停写。
- N输入/输出：冻结两图JSON及已接受NavM阶段状态；输出当前结构/流程和配套说明的静态入口。去掉nav变更历史，保留Animation主图/计划/Editor、完整失败链/RMS消费、资产网络/生产Run和原生视觉开放边界，不将静态可用称动态验收。
- 精确约束：只id=nav.text；其余全部节点/边/ID/coords/size/color/算法/接口/链接目标与锚点完整保持，别名仅nav允许更新。每图替回原nav.text应逐字恢复完整JSON及开始SHA256（B6EC0EDF8…、CE5C4E8CD…），不用重新序列化其它内容。
- 只读：本四文件与已冻结证据；链接仅验证既有目标存在/所需标题，两MD不写入，不读生产/测试源码或第10批记录。其它图/MD/源/测试/脚本/资产/全局/UE/构建/Git/代理冻结；禁止第5文件。
- 验收：单一nav.text差异、JSON唯一ID/端点/方向标签/尺寸有效、既有Wiki目标+锚点完整相同/有效；固定nav矩形下正文静态容量可容纳。51保护哈希不变；未进行Obsidian原生字体/连线路由视觉运行，不扩大已有视觉结论。
- 记录：两记录只顶部两段/本NavC登记及证据追加，截至NavM历史与C偏差全部保持；最终逆向删除NavC/恢复顶部精确回到54140/70985-byte基线。Q失败先修本nav文本；需要改尺寸/边/其它node/接口或第5文件即停止交回，不扩权。
- F后两图停写，V完成四文件一并冻结交回；不自动Editor/主图/计划/A5/helper后续。原子步骤只关闭导航状态，不把剩余失败/资产/网络误标完成。

## C28-NavC / 两图导航冻结与四文件交回（2026-10-01）

- P→N→Q→F→V执行：精确四文件预检及基线登记后，只替换两图id=nav的text；JSON/链接/反向全文与哈希/保护通过，先冻结两图后才改两记录顶部两段与NavC追加。四文件交回后停止写入，不修改第五文件或自动后续。
- 结构图：180行 / 11539 bytes；10节点/9边；实际diff +1/-1（第6行）；SHA256 `A916088F11139C18281D6BE6EF362D575B8F3A184A10C0DCC6AC34CBB13D823F`。流程图：498行 / 22932 bytes；25节点/30边；实际diff +1/-1（第6行）；SHA256 `B19459608D9356D0EF1A2AB8914E37DFD37EFB3FDA13855F6FE742253EF7CC7B`。
- 唯一变化为nav.text：移除C28-B/C步骤标题、流程“C待同步”、配套MD“待授权”与本步变更历史；链接别名改为当前结构/流程，原完整目标+锚点不变。保留结构数据/调用边含义及权威/自主移动主线说明、独立配置/重演/Animation入口，不改算法或接口。主图/计划/Editor、完整失败/RMS消费、资产网络/生产Run及原生视觉仍开放。
- 单字段和反向证据：每图只有nav.text不同，其余所有节点/边/ID/顺序/coords/size/color/文本/参数完整保持；反替原nav后，完整JSON文本逐字相同，UTF8无BOM原字节及SHA256精确恢复B `6EC0EDF8F33EC54794E7A5718DE5AF5B6424BC1A84FEA7EAE8D687B5AD8775AB` /11483 bytes、C `E5C4E8CDA7165F72D1FDA89C214C2F6DCD60021A1284F20919F3FDBACBAC184A` /22853 bytes。
- JSON/唯一ID/端点/side/非空标签/有限坐标正尺寸通过，节点矩形0重叠；23Wiki链接、7唯一文件目标、8锚点引用（6不同标题）全有效，原目标+锚点序列逐字保留。nav几何固定2540×280、3860×320，正文保守估算各214px，余量66/106px；仅静态容量，Obsidian字体/连线路由原生视觉未验证。
- 51非租约保护哈希保持（NavM保护中去除本次两Canvas，加入冻结两MD）；NavM两MD `7AF891EED02B76C91C7DEC08512BD197AE780E748F009CD249B03BDF688011FF`、`68AC9EB01AA827C1AFFDABA0EB0F0DE663BADDFA0C2D27C9443EFA9997455AE2` 不变。未读生产/测试源码或第10批记录，未执行脚本/UE/构建/Git/代理，未写源码/资产/A5 Guard/Movement helper或新图。
- 两记录除顶部两段及本NavC预检/证据，截止NavM全部历史与C只读范围偏差完整保持；最终逆向截去NavC/恢复顶部应复原Subleases54140 bytes / `494504F0417166E56FC901FC1F57818E8E483270EC0FE7F901BA36998A18E46E` 和Validation70985 bytes / `C9F19A4A92615C7B37ADF01500FE4B698B27CC930CB1A7E221F423B5500BDBAC`，实际结果随交回。
- NavM两MD保持冻结，其中“Canvas内部nav待独立NavC”阶段原句未在本步改写，与本NavC完成状态存在阶段文字差异；不能因此称所有导航状态已同步，后续由统筹另租约交接。
- 第35次65项Success及有限消费者、原日志49 Error/2 Warning历史事实不扩写；完整失败传播/RMS内部消费、七Profile既有null/资产迁移/接线、Proxy/DS/PIE/网络/生产Run及原生视觉未新增验收。未新增状态/接口/执行链/依赖循环或清理责任。四hash/实际diff/逆向证据与保护核对交回统筹，全部写入结束。

## C28-NavM2 / 两MD过期NavC阶段句收束预检（2026-10-01）

统筹已接受NavC并冻结两曲线图；本步只授权第一步NavM2，Animation资产组长直接执行。唯一结果是清除两MD原89/49行内“内部导航待NavC”的过期阶段句，保留其它正文/Wiki目标锚点及主图/计划/Editor/失败/资产网络/原生视觉未验边界。A5结构契约第二步未授权。

| 精确文件 | NavM2开始基线 | 唯一写入者 / 范围 |
|---|---|---|
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/曲线处理.md` | 99行 / 14486 bytes；SHA256 `7AF891EED02B76C91C7DEC08512BD197AE780E748F009CD249B03BDF688011FF` | Animation资产组长；仅原89行NavC阶段句 |
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/结构.md` | 55行 / 9757 bytes；SHA256 `68AC9EB01AA827C1AFFDABA0EB0F0DE663BADDFA0C2D27C9443EFA9997455AE2` | Animation资产组长；仅原49行NavC阶段句 |
| `F:/ue_project/GGYGO/AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 358行 / 60909 bytes；SHA256 `C5F704EAF27F67E51B2FB6FC64E780F13C32374022E8F3D9775C8C6B9DA4B1D0` | Animation资产组长；本预检、顶部两段及NavM2追加 |
| `F:/ue_project/GGYGO/AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 504行 / 75439 bytes；SHA256 `28D0C44802E9783143B0AB215A827A32A614FDB37812EC88D6079BD8DED0C8DA` | Animation资产组长；顶部两段及NavM2追加 |

- 依赖/顺序：A/B/C、NavM、NavC已统筹静态接受且冻结→P登记精确四基线及限定保护→M只两句→Q全文其它行/段不变、Wiki目标锚点/边界/逆向检查→F先冻结两MD→V仅两记录顶部及追加→四实际diff/hash、整文逆向交回停写。
- 唯一契约为导航阶段状态，不改模块职责、算法、接口、数据来源或状态所有权。保留其它所有正文；不添加A5 Guard/Movement helper，不改Canvas、不写第5文件、不执行未授权第二步。
- 只读依赖为本四文件与既有冻结接受证据；链接只查存在/所需标题，不读生产/专项/第10批源码记录，不运行脚本/UE/构建/Git/资产或代理。
- 36窗口已结束，K4-I1/P1-T1正在独立源码写入。本步仅核对本会话40项非租约保护（含14资产配置），排除其它模块生产/测试范围；不得据此声称全部源码稳定、全242重验或动态窗口已通过。本轮不重新编译、不操作UE。
- 验收：两MD各仅原89/49行预定NavC句替换，其它字句逐字保持，旧“待NavC”去除且不新增完成整个失败链/生产/视觉的表述；Wiki完整目标+锚点序列不变且有效；MD反替两句可精确恢复原整文/字节SHA256；40限定保护及14资产配置保持。
- 两记录只顶部两段及本NavM2登记/证据，截止NavC全部历史、失败证据与C只读范围偏差完整保留；逆向截去NavM2/恢复顶部须回到60909/75439-byte基线。
- 停止点：MD冻结后不再写；若需算法/接口/Canvas/第5文件或A5第二步则停止交回，不扩权。两记录完成后四文件一并冻结停写，不自动后续。

## C28-NavM2 / 两句收束冻结与四文件交回（2026-10-01）

- P→M→Q→F→V完成：登记精确四基线及限定保护后，曲线处理原89行“内部导航旧阶段字句留待独立NavC交接”和结构原49行“内部导航旧阶段字句交独立NavC处理”各只替为“内部导航已完成静态核对”；其它所有字句及Wiki目标/锚点保持，先冻结MD后才更新两记录顶部两段及NavM2追加。
- 冻结MD：`Animation/曲线处理.md` 99行 / 14470 bytes，实际diff +1/-1，SHA256 `25E635C50F0F37076C00C322768F53616DA0FEC934D11CB447E6206B70D7C124`；`Animation/结构.md` 55行 / 9744 bytes，实际diff +1/-1，SHA256 `BD73B8536B0F55109BEDB37F5BB8F6B4539A181F3BC84A4F08AB9B4FB89E6102`。没有清理其它历史句或改源码事实/算法/接口，A5结构第二步未授权。
- 全文回读与预定仅短句替换相同；逐字反替两短句可恢复原完整MD，UTF8无BOM字节实际为14486 bytes / `7AF891EED02B76C91C7DEC08512BD197AE780E748F009CD249B03BDF688011FF`、9757 bytes / `68AC9EB01AA827C1AFFDABA0EB0F0DE663BADDFA0C2D27C9443EFA9997455AE2`，两项通过。23Wiki/18目标/4锚点有效，完整引用序列不变。
- 主图/计划/Editor、完整失败/RMS内部消费、七Profile/资产迁移/网络/生产Run及原生视觉未验边界逐字保留；只关闭NavC完成后两MD的阶段句差异。两曲线Canvas仍冻结A916088F…/B1945960…，未改图/第五文件。
- 本步40本会话非租约保护哈希不变，包含14资产配置；范围为本会话冻结文档/图、Animation/Editor既有保护与脚本/证据，不含其它模块源码及测试。K4-I1/P1-T1独立源码正在写入，36窗口已结束，不声称全源码稳定或全242重验；没有UE/构建/资产/Git/代理/脚本运行，不读生产/测试正文或第10批记录。
- 两记录只顶部两段与本NavM2预检/证据，截止NavC整历史、失败和C范围偏差保持。逆向截去NavM2/恢复NavC顶部，应精确复原60909-byte `C5F704EAF27F67E51B2FB6FC64E780F13C32374022E8F3D9775C8C6B9DA4B1D0` 与75439-byte `28D0C44802E9783143B0AB215A827A32A614FDB37812EC88D6079BD8DED0C8DA`；最终实际逆向及四diff/hash随交回。
- 第35次有限消费者/65 Success、原49 Error/2 Warning等历史事实保持；没有为第36次或K4/P1新增运行结论。四文件全部冻结停写，不执行A5结构第二步，不自动Editor/主图/计划/Movement helper或其它后续。

## C37 / Animation Montage Guard主结构原子范围登记（2026-10-01）

统筹已接受四文件窄预检并登记排程C37，授权Animation资产组长直接执行。C37是图文原子步骤，不是第37次构建；唯一契约为薄Montage Guard、borrowed Scope、Base/ASC/Task静态职责及只读查询/生命周期/权限边界，不补生产消费者或改代码。

| 精确文件 | C37开始基线 | 唯一写入者 / 范围 |
|---|---|---|
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/结构.md` | 55行 / 9744 bytes；SHA256 `BD73B8536B0F55109BEDB37F5BB8F6B4539A181F3BC84A4F08AB9B4FB89E6102` | Animation资产组长；类表两行、Base真实继承、静态Guard小节 |
| `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Animation/GGYGO_结构_动画与表现.canvas` | 262行 / 10073 bytes；SHA256 `DECA4D2EF83090ED24DD59621C9CBEA41C86E316BB0106C66BE53B1D99B35107` | Animation资产组长；仅右侧新增预检4节点/5边 |
| `F:/ue_project/GGYGO/AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` | 387行 / 66534 bytes；SHA256 `7A7AE170DFEE8B09603D93A66BD42BBCF39AAA81AA6E4F85A4030A5F3D7B9106` | Animation资产组长；原子登记、顶部两段及验证追加 |
| `F:/ue_project/GGYGO/AAADocs/Modules/Animation/Module_Repair_11_Validation.md` | 532行 / 78875 bytes；SHA256 `3AC26FC2E33A0487A00A9FC72762D466D86E4CC2D928BC376CD7B36EAC918A30` | Animation资产组长；原子登记、顶部两段及验证追加 |

- 依赖已冻结：Guard/Scope实际定义、Base继承、ASC整个Super作用域已有接线、Task现有PlayMontage入口与相邻AbilitySystem结构只读职责。共享算法/接口/状态所有权不变；A5查询消费者与生产AnimClass迁移未完成，严格P1/网络保留开放。
- 顺序P→M/G→Q→F→V：先在两记录登记原子范围/基线；MD仅类表Guard/Scope两行与Base继承、曲线实施状态前静态契约；图仅预检4新节点/5边→JSON/ID端点/矩形/容量/新增链接与锚点/整文逆向/限定保护→先冻结MD/图→两记录顶部/追加验证→四实际hash/证据/未验边界交回停写。
- 图既有16节点/12边全部正文/ID/顺序/coords/size/color/标签与StateFrame链完整保留；不改nav或任何旧节点。新增montage_guard(1760,560,800×420)、montage_scope(1760,1120,800×440)、montage_guard_query(2720,560,860×550)、montage_callers(1760,1740,800×490)，原预检颜色/正文语义；query为公开方法说明面板，非新持状态对象/执行器。
- 新边固定为guard_base_inherit（Base→Guard真实继承）、guard_scope_registration（Scope→原Guard借用登记/注销）、guard_caller_scope（ASC调用栈→Scope）、guard_scope_result（Scope结果副本→ASC边界，不授Task权限）、guard_query_contract（Guard→只读说明面板）。不添加未实现Query→ASC/Task生产消费边，不把整个播放流程塞入类节点，不新建图。
- MD须明确TryGetCurrentMontagePlayGuardStage(CallerIdentity,OutNativeStage,bOutCompleted) const：GameThread、仅最内Scope/登记与身份匹配、失败Reset、即时副本外调后重查；查询无祖先回查/外部谓词/生命周期刷新/新状态。Returned不等于ASC Super完成、Completed不等于来源发布；true/false均不授Task/GA资源权限。
- Scope存储由Caller栈持有，Guard仅借用登记；原生命周期失效不清链释放旧Scope，析构只注销原实例自身登记，不停止新Owner或迁移GAS权威。Request原有纯上下文谓词与本查询不调用外部谓词分开，不能误写整个Guard没有Caller查询。
- 验收：MD除指定Base行/新增两行与小节外逐字保持，反向可恢复整文；旧图抽除4节点/5边可精确恢复完整原JSON及SHA256。所有ID端点/side/标签/几何有效、旧/新矩形无重叠、新正文容量与锚点通过。Obsidian原生字体/连线路由未验，不称视觉或完整播放验证。
- 保护仅本会话43项非租约范围及其中14资产配置，含冻结Guard/Scope与既有Animation/Editor保护；不声称全源码稳定或全242重验。曲线MD/两Canvas、主流程/计划/Editor/Movementhelper/其它源码/资产/全局冻结；不读取测试正文或第10批记录，不UE/构建/Git/代理/项目脚本运行。
- 第38次完整构建Succeeded/4actions/13.16秒、新运行时DLL/73正常Success与旧70含A5五叶保持仅按统筹已接受事实记录；第37次构建失败/未新DLL或运行保留历史，不据此关闭ASC/Task查询消费者、生产AnimClass、严格P1/网络/资产迁移或完整失败链。
- 停止点：需要第五文件、改旧图/曲线或生产接口、写入未冻结依赖时停止交回。F后MD/图不再编辑；V只两记录顶部两段和C37登记/验证追加，截止NavM2全部历史及C偏差保持；四文件交回后明确停写，不自动后续。

## C37 / Guard主结构产物冻结及实际编辑方式交回（2026-10-01）

- P已先登记两记录，再实现MD/图；Q完成后先冻结两个产物，才执行V顶部两段及追加。MD仅新增Guard/Scope类表两行、Base真实继承及曲线实施状态前静态契约；旧StateFrame/曲线算法正文不改。图只右侧4预检节点/5边，无Query→ASC/Task未实现消费边，也无新对象/执行器。
- 冻结MD：77行 / 14128 bytes，SHA256 `C600C8D2A47BC3CE09CD01FC193B6A6B46F2A280823A7B97716C1F32B16A6C24`，实际行diff +23/-1。主结构Canvas：343行 / 14638 bytes、20节点/17边，SHA256 `0AD6FD15FF06B7289053E0AFE17E8E2A7E685ABC018C80EA68FCBEC84C3AAFC0`，实际行diff +81/-0。旧16节点/12边全部JSON值/正文/几何/颜色/ID/顺序/标签及StateFrame链保持。
- 逆向实际：MD删两新增类行/静态小节、还原Base行后，整文UTF8原SHA256 `BD73B8536B0F55109BEDB37F5BB8F6B4539A181F3BC84A4F08AB9B4FB89E6102` /9744 bytes；图删仅新增节点/边的原文本插入片段，精确恢复混合CRLF/LF原完整JSON文本及 `DECA4D2EF83090ED24DD59621C9CBEA41C86E316BB0106C66BE53B1D99B35107` /10073 bytes。两项实际SHA256通过，不只比较解析值。
- 全部20/17 ID唯一、端点/side/标签/有限坐标正尺寸通过、矩形0重叠；39Wiki链接/18文件目标/5锚点引用有效，其中新增4链接、Guard静态契约标题锚点存在。旧MD18链接/旧图17链接原样保留。新4节点保守正文余量86/76/156/126px。
- 旧12节点在同一保守字号/内边距模型下有7～147px负余量，属原基线正文容量边界；本租约明确保持旧布局/正文，不予扩大修改。Obsidian原生字体/实际折行/连线路由未验，不能称全图容量或原生视觉通过。后续若要修旧节点需独立范围/视觉核对，本步没有第5文件需求。
- 实际编辑方式与权限：MD和两记录人工修改均apply_patch。主结构Canvas标准JSON重序列化无法保留原混合换行，未据此写入；尝试原文追加的默认Shell路径拒写，原图仍DECA4D2E…。随后以require_escalated受审查调用向已授权Canvas追加预检4节点5边，执行exit0，产物为0AD6FD15…；未修改ACL/只读属性。根随后要求人工编辑仅apply_patch，并明确已写产物保留不回滚/重写；本图已经冻结，交回该事实与权限执行证据供根审查，之后没有同路径第二写法。
- 原文追加仅为保存原JSON字节的实际方法，不构成以后绕过编辑工具或审批的许可。遵循根最新约束，后续人工编辑仅apply_patch；若合规工具拒绝，保留候选/阻塞证据交回，不无限重试。该图实际删除追加片段确实恢复原raw SHA，未冒称机械标准化结果可恢复原字节。
- 43本会话限定保护哈希不变（含14资产配置与冻结Guard/Scope）；不称全源码稳定/全242重验。曲线MD/两曲线图、主流程/计划/Editor/其它模块与全局不写；未UE/构建/Git/代理/资产/项目脚本运行，不读测试正文或第10批记录。
- 38完整构建Succeeded/4 actions/13.16秒、新运行时DLL/73正常Success、旧70含A5五叶保持仅按统筹接受事实记录，未自行运行/核对新报告。37失败及未新DLL/运行保留历史；不关闭生产查询消费者/AnimClass迁移、严格P1/网络、Task权限/来源或完整失败链。
- 两记录除顶部两段和C37登记/验证外截止NavM2整历史及C偏差保持；最终逆向截去C37并还原顶部，须回到66534-byte `7A7AE170DFEE8B09603D93A66BD42BBCF39AAA81AA6E4F85A4030A5F3D7B9106` 与78875-byte `3AC26FC2E33A0487A00A9FC72762D466D86E4CC2D928BC376CD7B36EAC918A30`。四实际hash/证据/未验边界交回后全部停写，不自动后续。
