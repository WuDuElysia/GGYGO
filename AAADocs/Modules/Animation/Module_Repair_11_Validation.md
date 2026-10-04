# 第11批 Animation / D6 验证记录

更新：2026-10-01。当前状态（C37图文）：结构MD77行、主结构图20节点/17边完成并先冻结；旧16节点12边全部JSON值/正文/几何/颜色/ID及原文本完整保持，MD/图整文逆向SHA256通过。39链接/18目标/5锚点、新4节点余量76～156px/0矩形重叠及43限定保护/14资产配置通过。原12节点保守容量不足与原生视觉未验保留；Canvas受审查Shell写入事实待根复核，不再重写，A5消费者/AnimClass/P1/网络未闭合。

以下截止NavM2全部历史及失败/只读偏差证据原样保留；最新C37验证及实际编辑权限见文末。C37仅图文步骤，38构建/73正常Success为统筹事实、37失败仍保留，无新增UE/动态/生产权限验收。四文件记录完成后全部停写；后续人工编辑仅apply_patch，曲线/流程/计划/Editor/源码/资产/全局冻结。

## 范围与结论

本批修复 AnimInstance 在初始化、反初始化和运行时 Owner 更换时可能保留旧 Pawn 表现状态的问题，并复核批次 10 的 D5 兼容映射边界。Movement 继续是步态、走跑混合、停止动作、TurnBack 和胶囊位移的唯一权威；Animation 只抓取只读帧并维护表现侧生命周期。生产实现没有新增 Tick、计时器、第二套状态机、Movement 写入、资产访问或跨模块反向依赖；测试专用 CMC 只为构造可区分的输入帧写入受控字段。

实际改动：

- `UGGYGOAnimInstanceBase` 增加 `NativeUninitializeAnimation`、集中 `ResetAnimationLifecycleState`、派生 `OnAnimationLifecycleReset` Hook 和弱 Owner 失效识别。
- `UZZZAnimInstance` 通过 Hook 清除 Memory、Snapshot、无所有权上下文及全部公开派生表现字段。
- `FZZZLocomotionEvents` 增加幂等 `Reset`，不改变批次 10 的无状态映射。
- 新增 `GGYGO.Animation.Lifecycle.ResetCallbacks`、`OwnerChangeAndD5Compatibility`、`LocomotionEventsReset` 三项专用 Automation Test 源码及 transient 测试类型。
- 测试 World 夹具显式创建 `FWorldContext`，在 Actor/World 清理结束后才注销 Context，避免弱 Owner 失效场景通过 `Destroy()` 触发无 Context 警告。
- 同步更新 Animation 的结构文档、实施计划、结构 Canvas 和流程 Canvas，并纠正旧图中“CMC 仍反读 AnimInstance 曲线”的过期描述。

## 冻结设计

- 基类使用单一幂等复位入口，依次清除 Owner、通用状态帧、调试帧，再调用派生复位 Hook。
- 初始化先执行引擎基类初始化，再复位并绑定当前 Owner，随后抓取首帧。
- 更新时先检测 Owner 身份或旧弱引用失效；变化时先复位，再绑定新 Owner，随后抓取当前帧。
- 反初始化复位全部运行时状态，并继续调用引擎基类反初始化。
- ZZZ Hook 清除 Memory、Snapshot、Locomotion 当前帧指针上下文及公开派生字段；保留 AnimSet 与 Tuning 配置。
- Capture 当前为无状态纯抓取对象，没有需要复位的缓存。

## 自动化源码矩阵

| 场景 | 预期 | 源码覆盖 |
|---|---|---|
| 新建夹具与空 Owner 初始化 | 通用帧、调试帧、Snapshot、Memory、公开表现字段均为安全默认值 | `ResetCallbacks` |
| 重复 Initialize | 每次先清旧状态，不保留上一次 Memory、速度、Tag、步态或 TurnBack | `ResetCallbacks` |
| `A -> nullptr` | Owner 变空的同一更新帧清除全部旧表现状态与无所有权上下文 | `OwnerChangeAndD5Compatibility` |
| `nullptr -> B` | 首帧只来自 B；不得混入 A 的状态 | `OwnerChangeAndD5Compatibility` |
| `A -> B` | 同一更新帧先清 A，再抓取 B | `OwnerChangeAndD5Compatibility` |
| 有效 Owner 弱引用失效后变空 | 即使两个 `Get()` 结果都为空，也按生命周期变化复位 | `OwnerChangeAndD5Compatibility` |
| 重复 Uninitialize | 幂等，不恢复或残留任何运行时表现状态 | `ResetCallbacks` |
| D5 兼容映射与轴边界 | `WalkRunBlendAlpha -> GaitBlendY`；Stop 语义映射为 `0/1/2`；标准轴只在快照边界交换 | `OwnerChangeAndD5Compatibility` |
| Events 上下文复位 | Reset 后旧 Snapshot 不再写入旧 Memory | `LocomotionEventsReset` |

测试夹具继承真实 `UZZZAnimInstance`，以 transient `USkeletalMeshComponent` 为 Outer，并覆盖 `TryGetPawnOwner` 控制 A/null/B。测试直接调用 `NativeInitializeAnimation`、`NativeUpdateAnimation`、`NativeUninitializeAnimation`；`UAnimInstance::InitializeAnimation()` 所含的 SkeletalMesh/Proxy 初始化链不在本夹具覆盖范围内。

## D5 表现残余复核

- `StateMemory.GaitBlendY` 与 `StateMemory.StopValue` 继续作为当前生产 `ABP_Pyrios` 的序列化兼容字段；未删除、重命名或扩散为新权威 API。
- 当前映射仍是 `WalkRunBlendAlpha -> GaitBlendY` 与 `StartStop/WalkStop/RunStop -> 0/1/2`。`X=Forward/Y=Right` 的标准轴只在旧 Snapshot 边界交换成现有表现轴。
- `AnimBlend*`、`ActualVelocity*`、曲线调试字段和 `bTurnBackRunOut` 仍是当前未被 AnimGraph 消费的兼容/调试暴露面；本批只保证它们跨 Owner 复位，不做生产蓝图清理。
- `FZZZAnimWriteContext::Tuning` 仍是旧上下文的未消费成员；当前 `MapMovementState` 只检查并使用 Snapshot/Memory。本批不为这一未使用残余扩大重构范围，后续兼容层清理时一并处理。
- `AAADocs/Architecture/Interactions/Locomotion_AnimBP_Wiring_Audit.md` 仍为 `PendingUEAssetWindow`。BlendSpace 轴名、Stop Select、七份 Profile 和 MovementSet 引用必须等独占 UE 窗口回读，不能因本次源码复核标记为已接线。

## 架构核对

- 状态唯一：步态、WalkRun 混合、Stop、TurnBack 与胶囊位移仍由 Movement 持有；Animation 只维护表现快照和兼容字段。
- 依赖方向：生产代码只从 Pawn/CMC/ASC 抓取只读事实，没有 Animation 到 Movement 的写入；测试夹具对 CMC 的写入仅存在于测试类型。
- 清理责任：基类私有 Reset 统一覆盖三个生命周期入口，派生 Hook 只清派生表现状态；`LocomotionEvents::Reset` 清除不拥有的指针上下文。
- 状态泄漏：`bHadCharacterOwner` 明确区分“从未绑定空 Owner”和“旧有效弱引用已经失效”，覆盖 `A -> nullptr -> B` 与直接 `A -> B`。
- 执行机制：没有新增 Tick、Timer、帧调度器、状态机或缓存；`FGGYGOAnimationStateCapture` 保持无状态。

## 静态验证

- [x] 核对所有运行时字段进入集中复位链。
- [x] 核对 `AnimSet`、`Tuning` 配置字段未被复位。
- [x] 核对 Owner 失效到空值通过 `bHadCharacterOwner && !CharacterOwner.IsValid()` 识别，不依赖仅比较两个空指针。
- [x] 核对 ZZZ 的 `LocomotionEvents` Reset 后不保留上一帧指针。
- [x] `rg` 核对生产实现没有新增 Tick、Timer、Movement 写入或资产访问；测试 CMC 写入仅用于夹具输入。
- [x] 核对专用测试覆盖上述矩阵，且控制 Owner、种入脏状态的辅助只存在于测试类型。
- [x] 核对 Animation 局部 Markdown、结构 Canvas、流程 Canvas 与代码一致；过期的 CMC 反读描述已修正。
- [x] PowerShell `ConvertFrom-Json` 校验两个 Canvas：结构图 16 节点/12 边，流程图 14 节点/11 边；节点/边 ID 唯一且 0 个悬空端点。
- [x] 扫描四份局部文档/Canvas 的 Wiki 链接；均可按路径或笔记名解析。
- [x] 扫描批次 11 文件，无尾随空白或冲突标记；临时实现 A 的 `git diff --check` 仅报告既有 CRLF/LF 转换提示，无 whitespace error。
- [x] 统一构建回传的测试编译错误已收敛：将 `ExpectedVelocity.Size2D()` 显式转换为 `float` 后再与 `Frame.HorizontalSpeed` 比较，消除 `FAutomationTestBase::TestEqual` 重载歧义。
- [x] 核对测试 World teardown 顺序：创建 World 后登记 Context；局部 AnimInstance/Mesh 先析构；显式 Actor `Destroy()` 与 `World->DestroyWorld(false)` 均发生在 Context 存活期间；最后注销 Context。

## 统一构建回传

- 2026-09-29 统筹运行统一完整构建，UHT 已通过。
- 首次 C++ 编译在 `GGYGOAnimationLifecycleTest.cpp` 的 horizontal speed 断言失败：`Frame.HorizontalSpeed` 为 `float`，UE5 LWC 下 `FVector::Size2D()` 返回 `double`，`TestEqual` 无法选择同类型重载。
- 显式 `float` 修复后，统筹已运行统一自动化，说明该编译错误已跨过。
- `GGYGO.Animation.Lifecycle.OwnerChangeAndD5Compatibility` 执行成功，但记录警告：`UWorld::DestroyActor: World has no context`。根因是 transient World 未登记到 `GEngine`，测试中显式销毁 OwnerA 时缺少有效 `FWorldContext`。
- 本次测试清理为夹具登记独占 World Context，并保持到 Actor/World teardown 完成后再注销；没有屏蔽日志或忽略警告，没有修改生产动画生命周期代码。
- Context 修复后的自动化尚未由统筹重跑，因此当前不能标记为无警告通过。

## 未执行门禁

- Context 生命周期修复后的统一自动化尚未重跑；当前证据是修复前测试成功但带上述 teardown 警告。
- 未覆盖 `UAnimInstance::InitializeAnimation()` 的完整 SkeletalMesh/Proxy 初始化链；专用测试只调用真实 Native 生命周期回调。
- 未回读或保存生产 AnimBP、BlendSpace、动画、Movement Profile 等 `.uasset`。
- 未执行 Git 提交或推送。

这些动态门禁与资产回读继续由统筹在源码全部冻结后统一安排。

## C18 / R2-I1 预检登记（2026-10-01）

统筹已接受薄 DTO 预检，授权 Animation 资产组长直接实施，禁止子代理。四文件范围是新增 `Source/GGYGOEditor/Public/GGYGOAnimationCurveSnapshotLibrary.h`、新增 `Source/GGYGOEditor/Private/GGYGOAnimationCurveSnapshotLibrary.cpp`，及本记录 / `Module_Repair_11_Subleases.md` 仅追加。两个源码开始时不存在；Subleases 原 5448 bytes / SHA256 `86A69DB0C5CE13AEAA0535E1161B7DB0698779589D6CB4570ADB84C82A261B07`，本记录原 8982 bytes / SHA256 `510EF2F6C667A6D85D5431189A166C1BB284C781B3BE503FA214873EE262788B`。历史 D6 记录保持，当前追加不刷新历史动态状态。

### 原问题证据与证明边界

- 只读复核实际 `Saved/AnimationCurveReadback/ReadFloatCurves_Python_20260930_R2.json`：`status=failed`、`complete=false`、脚本 exitCode=1；R1 成功 tuple 返回 4 条 `FloatCurve` 和原 double 时长，首个 `RootMotion_Speed.CurveName` 读取因 protected 权限失败，未发布快照。
- 同报告的 null-source 返回 None，原生 OutError 未在 Python 返回值中可见；这明确要求单一结果结构包含成功与错误信息。
- 报告五阶段 dirty 集合均为空、14 保护 hashes 保持；这是旧探针的实际证据，不代表新 DTO 已验证。报告 UTC `2026-09-30T16:50:56` 对应本地 2026-10-01 00:50:56。
- 统筹第29次 R1/T1 及第30次构建/新 DLL 自动化成功只证明此前接口；本次源码尚未编译、运行或经 Python 回读。

### 冻结字段与验收断言

- Key DTO：六个 `float`（Time、Value、ArriveTangent、LeaveTangent、ArriveTangentWeight、LeaveTangentWeight），三个 `int32`（InterpMode、TangentMode、TangentWeightMode）。六数原样复制，三个原生模式 `.GetValue()` 后转 int32，保留 Hidden None，不定义第二套模式/有效性规则。
- Curve DTO：`FName Name`、`int32 Flags`、`float DefaultValue`、`int32 PreInfinityExtrap/PostInfinityExtrap`、Key DTO 数组；名称、flags、默认值、外推和全部 keys 按 R1 原顺序复制。
- Result DTO：`bool bSucceeded`、Curve DTO 数组、`double DurationSeconds`、`FString Error`；统一单个 `FGGYGOFloatCurveReadResult` 返回。失败 false、空数组、0 时长、原 R1 Error；只在全部映射完成后提交成功。
- 三类 `USTRUCT(BlueprintType)` 与全部 public `BlueprintReadOnly` 字段；唯一 `BlueprintCallable ReadFloatCurveSnapshot(Source, CurveNames)`。实际 Python 属性可读性仍是后续门禁，不能由 metadata 静态推定为通过。
- 路径仅 `Python → SnapshotLibrary → R1 → DataModel`；每次只调用一次 R1，读取/校验/错误继续 R1 唯一权威。DTO 不直接访问源、模型或执行资产加载/修改，不添加状态、句柄、缓存、求值或业务替代。

### 分阶段与只读保护

预检登记 → I1-S 两源码直接映射与静态审查 → 两源码 SHA256 冻结 → I1-V 两记录仅追加实际结果 → 四文件交回。第三源码、共享接口修改、额外验证职责或无法按此边界完成时停止；不自行扩租约。构建/UHT/UBT、UE、脚本执行、Git、测试/新探针、资产和 Obsidian 写入均不在本轮授权内。

只读基线：R1 header `1F3506F4DC22789ED7C0BF7A5EB19B2FF6D273DFBC9C964796EC0DDE5978131D`；R1 cpp `959CFAE102D4513BD3ADFC2652D600D2BB933BAFBA0255DFD3EE00E89E9FDD96`；T1 `2C63D8BBBE6E0FD5D77F50B23E96F61219C824C6B8217E6908B0142E51E0DCF3`；Build.cs `6476DA680D9A318BFE814DBB8C43D76F2C4C9E060B52F564A86DBDD1393FF163`；旧 R2 脚本 `6A062C46E7CBD9D26C0083550D25AE84A073E4AA5558948293A4EC0F4497C7D3`；旧 R2 报告 `02AD2D1C3B995911C8A62B2A610642BFDD9A151AD0C4EB666E2F681BBCD1F19B`。交回时再次核对。

## C18 / R2-I1 静态交回（2026-10-01 01:26 +08:00）

### I1-S 实际结果与源码冻结

- 新 header 115 行，cpp 55 行；逐行复核三个导出 BlueprintType 结构、19 个 public BlueprintReadOnly 字段、一个 BlueprintCallable 函数及单一结构返回，没有 bool 主返回/out 参数。
- cpp 第15行仅一次调用冻结 R1；第17行原样转移 Error，失败第20行直接返回默认 false / 空 Curves / double 0。成功路径按原顺序复制全部曲线和 keys；六个 key float 与 DefaultValue 直接赋值，五个原生枚举 `.GetValue()` 后转 int32，Name/Flags 和 double 时长直接复制。第51–53行在所有循环结束后才提交 Curves / DurationSeconds / bSucceeded。
- 对照本地 UE5.8 的 AnimCurveTypes.h、RichCurve.h、RealCurve.h 核对原生 accessor 与字段类型；Build.cs 已有 Core/CoreUObject/Engine，无新增依赖。Source 仅传入 R1，本层没有解引用、Model/Controller 查询、加载/保存、求值/重建、钳制/默认替代、日志或第二套校验。仓内新结构/函数名仅出现于这两个新增源码。
- 源码在 I1-V 文档阶段前完成静态审查并冻结：header SHA256 `FBC50BC68D61B5E8FB7E8C7C890664D1858BEB26E3070A6A6D6F42496D74ED0E`；cpp SHA256 `163E24B67FEAFEABBE0B29C7D7B49A6FBC56B4D7E96112193956B22BFAF89490`。本结论是静态候选实现，不是编译/UHT/实际 Python 验证。

### 资源、状态与清理责任核对

R1 的 NativeCurves / NativeError、DTO CandidateCurves 均为函数局部值，生命周期止于调用结束；成功结果由值语义移交调用者，失败没有部分 DTO 泄漏。内部 key const reference 指向 R1 返回的本地 FFloatCurve 副本，未进入返回结构。没有 UObject/Source/DataModel 指针、KeyHandle、view、静态缓存、订阅、任务或帧调度器；没有额外资源释放义务。调用者负责结果值的普通生命周期及需要时再次显式读取，结果不竞争任何资产/Movement 权威状态。依赖方向保持 Editor 内 SnapshotLibrary → ReadLibrary，无新增运行时反向依赖、循环依赖或跨模块内部状态访问。

### 只读保护文件核对（本轮实际 hashes）

以下 13 项均与 C18 开始前基线一致；R1/T1/旧夹具、Build.cs、旧探针/报告和 Report25 保持冻结，没有以新接口覆盖旧失败证据。

| 保护文件 | SHA256 |
|---|---|
| `Source/GGYGOEditor/Public/GGYGOAnimationCurveReadLibrary.h` | `1F3506F4DC22789ED7C0BF7A5EB19B2FF6D273DFBC9C964796EC0DDE5978131D` |
| `Source/GGYGOEditor/Private/GGYGOAnimationCurveReadLibrary.cpp` | `959CFAE102D4513BD3ADFC2652D600D2BB933BAFBA0255DFD3EE00E89E9FDD96` |
| `Source/GGYGOEditor/Private/Tests/AnimationCurveReadbackTests.cpp` | `2C63D8BBBE6E0FD5D77F50B23E96F61219C824C6B8217E6908B0142E51E0DCF3` |
| `Source/GGYGOEditor/Private/Tests/AnimationAssetSafetyTestUtils.h` | `F6D97EC834540FA522F92569EA12E8F50A160347B89FD640E210673C311136C4` |
| `Source/GGYGOEditor/Private/Tests/RootMotionBakeSafetyTests.cpp` | `11A906C57BFD76AB2A2882F8C879967D1158299E32300F617758AF416F9B2889` |
| `Source/GGYGOEditor/GGYGOEditor.Build.cs` | `6476DA680D9A318BFE814DBB8C43D76F2C4C9E060B52F564A86DBDD1393FF163` |
| `AAADocs/Scripts/probe_animation_float_curve_readback.py` | `6A062C46E7CBD9D26C0083550D25AE84A073E4AA5558948293A4EC0F4497C7D3` |
| `Saved/AnimationCurveReadback/ReadFloatCurves_Python_20260930_R2.json` | `02AD2D1C3B995911C8A62B2A610642BFDD9A151AD0C4EB666E2F681BBCD1F19B` |
| `AAADocs/Modules/Animation/Animation_Asset_Readback_API_Validation.md` | `327E517456E41AC37B86D9BC12DA1ACA50D6895AF621938679D0EAC46EEABD93` |
| `AAADocs/Scripts/audit_locomotion_motion_profiles.py` | `E87A57C6855595259A16427D40C8B85613BD5096E68EE33DC3C363E4E59CFAD8` |
| `AAADocs/Scripts/tests/test_locomotion_readback_api.py` | `2BD90B1D65F23B38DE6731DC8026B36F9D4EB2D4BB872C59A9A6428973F8FE42` |
| `AAADocs/Modules/Movement/Locomotion_Motion_Profile_Migration.json` | `1D7F2CB333AC2A3523C01B3346068948ABF0CBAB4A0A69F259B7465B931B9C66` |
| `AAADocs/Architecture/Interactions/Locomotion_AnimBP_Wiring_Audit.md` | `40A35ED3C74860E93C4BB7866CA5F05AE643792408E57F04B4AC7AADB0480046` |

另逐项核对旧 R2 报告登记的 14 项资产/配置，实际全部一致，delta=[]；这是文件 hash 保护核对，没有运行 UE 或获得本次 dirty 状态动态证据。

| 保护资产/配置 | SHA256 |
|---|---|
| `Content/BP/Anim/ABP_Pyrios.uasset` | `48EE112C9E9BDA3EC22317F0D3A55C9545D19E36B17193AFD7859C0657E26359` |
| `Content/Characters/Player/Pyrios/Animation/Movement/BS_Pyrios_WalkRun.uasset` | `7B76721AD1BCC79B5FF03473C5098478369B3B901408CB55D69B87AC1294922E` |
| `Content/System/DA_Movement_Default.uasset` | `7943CDC3A9F761386EEB08E4D9785E4B98121CAB5D5FA45C4AE7A5ED8A01F678` |
| `Content/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Walk_Start.uasset` | `A0F957803207E8BB53DB0CD2333F19E183B60BEFB4E3DA747B432CFA5952818D` |
| `Content/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Walk_Loop.uasset` | `CA56C5DF7F1F1B7282780610E5F9BCB0C28E203086A603D9F3AC02FE80D936BA` |
| `Content/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Run_Loop.uasset` | `922D51C476D9C93A4F5733FAF5E3E977F5B37D934DE85A007622AC3730CA3E88` |
| `Content/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Walk_Start_End.uasset` | `4059B9A4615C9E4E4D4A3CE4E610D32B1754DD0EAF25FBBA730E9D395FB91976` |
| `Content/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Walk_End.uasset` | `1DE5B73B22B0553E18823F9012BEEB4011CA730614032DA9DCDF3EC3A0B99227` |
| `Content/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Run_End.uasset` | `48076290557F12E8A849C061BEAFDF5B93FD178A93263C744C30B8CEE66BB93A` |
| `Content/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_TurnBack.uasset` | `71C3B14549CD17FA337B61AEED0B8311D600C7E4592A66101839BD5D0186FD41` |
| `Content/BP/Character/Player/BP_PC_Pyrios.uasset` | `9E093DB87659B1A05281F000A97017F4141521E11B93E38F6E92A9DD8705DAC3` |
| `Content/AI/Boss/Test/BB_Boss_Test.uasset` | `B2A8400764133041F09A162B0F9BE72337FDD9D8BA635C558BF4D323B77A5660` |
| `GGYGO.uproject` | `D9B86F0FA9F462929AEF5E70737F0A219206D505B9663DB6ACD34E6AF897E174` |
| `.kiro/steering/user-preferences.md` | `6C49C81EB7B61A8DB3071A8738264B899A14C35E59B657F07D11DCD0D44AEB45` |

预检追加后，按字节核对 Subleases 原前5448 bytes / Validation 原前8982 bytes 的 SHA256，均等于本节前所登记基线，历史记录未改写；最终四文件交回读取再核对前缀及源码冻结 hashes。

### 未执行门禁与架构笔记差异

- 未执行构建/UHT/UBT、UE、测试或脚本；未修改/执行旧探针，没有新增测试、新 probe 或生产资产操作，没有 Git 或子代理。19 个字段的实际 Python 可读性、失败结构/error 的真实反射返回、原 float/double/Hidden None/完整 key 往返一致性，均需统筹在后续专项/新探针验证。不能声称完整曲线回读已通过，也不能续扫七动画。
- R1/T1 的 custom Default、非有限值、未知枚举、非正时长与非 null 无效对象真实源夹具缺口仍保留；本 DTO 不承担新校验，也不关闭这些历史未验证项。只表示 R1 当前公开 DataModel 的约定曲线语义字段，不证明底层 Channel/磁盘字节、KeyHandle、Color/Comment、骨骼或 Graph 等价。
- 已按计划蓝图只读核对 `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/` 的 Animation 入口、结构及曲线说明：尚未登记 R1/本次 SnapshotLibrary Editor 接口；`Animation/曲线处理.md` 保留旧 sampler/CMC 说明。C18 明确冻结 Obsidian，故本轮没有更新笔记/Canvas，也不声称架构笔记同步完成。
- 待统筹分配文档阶段范围后，将 Editor 单次值读取及候选/验证状态同步到 `Animation/结构.md`、`Animation/曲线处理.md`、`Animation/GGYGO_结构_动画曲线.canvas` 及必要接口计划；既有 Movement 流程差异仍由 Movement/统筹处理，不能在 Animation 租约下抢写或将运行时接线写成已完成。

I1-S 已冻结，I1-V 交回记录仅追加；最终读取、差异和四 SHA256 随交回提供。四文件交回后停止写入，后续动态与笔记门禁由统筹排程。

## C20 / R2-I1-T1 预检登记（2026-10-01）

统筹已授权三文件：新增 `Source/GGYGOEditor/Private/Tests/AnimationCurveSnapshotTests.cpp`，及11的 Subleases/Validation 仅追加。测试开始时不存在；Subleases 原11731 bytes / SHA256 `F17756CA793E713711ECAE8C7704C5DE4B36AAFAA95F5EDA642CCE9F707D89F3`；Validation 原21052 bytes / SHA256 `9F22F19E5EE72848401F5043C819A7B1E5B6B7029A7A473197103DE0ED1474C5`。生产/R1/共享夹具/旧测试/Build.cs/探针/资产/Obsidian 均冻结；无代理、UE、编译、脚本或 Git 权限。

只读核对实际 C18 源码及原 T1：Snapshot h `FBC50BC68D61B5E8FB7E8C7C890664D1858BEB26E3070A6A6D6F42496D74ED0E`、cpp `163E24B67FEAFEABBE0B29C7D7B49A6FBC56B4D7E96112193956B22BFAF89490`；R1 h `1F3506F4DC22789ED7C0BF7A5EB19B2FF6D273DFBC9C964796EC0DDE5978131D`、cpp `959CFAE102D4513BD3ADFC2652D600D2BB933BAFBA0255DFD3EE00E89E9FDD96`；原 T1 `2C63D8BBBE6E0FD5D77F50B23E96F61219C824C6B8217E6908B0142E51E0DCF3`；共享夹具 `F6D97EC834540FA522F92569EA12E8F50A160347B89FD640E210673C311136C4`；Build.cs `6476DA680D9A318BFE814DBB8C43D76F2C4C9E060B52F564A86DBDD1393FF163`；旧 R2 脚本/报告仍为 `6A062C46E7CBD9D26C0083550D25AE84A073E4AA5558948293A4EC0F4497C7D3` / `02AD2D1C3B995911C8A62B2A610642BFDD9A151AD0C4EB666E2F681BBCD1F19B`。

本次单叶 `GGYGO.Editor.Animation.FloatCurveSnapshot`，冻结四族：19个实际反射字段/返回Struct；clean/dirty完整值与独立副本；null/late-missing失败原Error；None/SmartAuto三代表模式。完整前置成立后预计11 Snapshot +4直接R1错误对照，不重复R1的19模式矩阵、不复制validator。float/double逐标量位模式比较，名称flags/default/prepost/Keys/时长与请求顺序按真实Model精确核对。所有Controller输入必须先在真实Model确认；任何缺失/改写都真实失败，不默认填充或修改Model绕过。

统筹回传：C18已第31次UHT及第32次完整成功链接，原FloatCurveReadback第32次Success；第32次总体62 Success /2 Fail，因此不称全模块通过。这些证据不证明新Snapshot专项/Python实读。当前阶段只有静态实施，按“预检 → 一个新cpp → 源码冻结 → 两记录追加”交回，动态仍等统筹统一门禁。已知 custom Default/非法数据真实源夹具、Python实读、生产资产与架构图文同步缺口仍保留。

## C20 / R2-I1-T1 静态交回（2026-10-01 15:06 +08:00）

### 冻结结果与四族断言

新增 `Source/GGYGOEditor/Private/Tests/AnimationCurveSnapshotTests.cpp` 333行，SHA256 `3EA70519D60CC14ED87EF75B40DC57E4BF5B20FB144A58C26D72C28BDF129C4D`；已在记录追加阶段前完成静态审查并冻结。`WITH_DEV_AUTOMATION_TESTS` 内仅一个 `IMPLEMENT_SIMPLE_AUTOMATION_TEST`，新叶 `GGYGO.Editor.Animation.FloatCurveSnapshot`。这只是已编写/静态检查，不是运行成功。

| 族 | 已编写的真实前置与断言 | 完整路径 Snapshot /直接R1次数 |
|---|---|---|
| 反射 | 实际 StaticStruct/FindFProperty，9/6/4字段计数；19精确类型及Public/BlueprintVisible/ReadOnly，排除Protected/Private；Keys/Curves元素Struct；真实UFunction Return FStructProperty及精确Result类型/Callable/Static | 0 /0 |
| 成功/独立副本 | 真实Controller建weighted/empty/outside/probe四曲线；所有九key输入位模式、name/flags/prepost/默认MAX_flt先在真实Model确认；clean/dirty各乱序读及副本修改后重读，Result/所有曲线/全部keys精确一致，修改DTO各类字段不改源 | 4 /0 |
| 失败 | clean/dirty各null及有效后缺失；同输入R1必须先真实false/空/0/非空定位Error；观察源保持后再Snapshot；false/空/0及Error全文等于R1，late错误含源路径。两调用之间不重置dirty | 4 /4 |
| 原生代表模式 | 三个原T1组合：RCIM_None+Break、Cubic+RCTM_None、Cubic+SmartAuto，均WeightedNone；SetCurveKeys后真实Model全key字段、flags/prepost/default严格确认，再读DTO精确比较及源保持 | 3 /0 |

静态总数11 Snapshot +4直接R1对照：两个成功入口各在clean/dirty一次共4，两个失败入口各在clean/dirty一次共4，三个模式共3；叶末显式断言计数11/4。若前置或断言失败，计数不宣称达到此数，立即返回失败。本步没有动态计数证据，也不通过测试钩子证明DTO内部一次R1调用；内部次数仍为已冻结源码的静态结论。

比较助手只读真实原生值：六key float、DefaultValue和double Duration以逐标量 `FMemory::Memcmp` 比较位模式，模板用标准 `std::is_same_v` 限于float/double；三个key及两外推模式比较原生int32，Name/Flags和请求顺序逐项检查。没有容差、Eval采样、替代默认、本地伪读取函数或复制validator。源状态包含同一Model指针、按名称检查的全部公开曲线内容、play length、dirty；不比较缓存顺序、全对象字节或底层Channel。

### 用到的本地原生 API 依据（只读）

| 来源 | 核对依据 |
|---|---|
| `Source/GGYGOEditor/Private/Tests/AnimationAssetSafetyTestUtils.h:13,17` | 原 Package()/Sequence()：真实Skeleton/BoneTree/AnimSequence及Controller初始化；临时对象，不加载生产资产。原T1的四曲线和三代表模式构造方式保持 |
| `F:/UE_5.8/Engine/Source/Runtime/Engine/Classes/Animation/AnimData/IAnimationDataController.h:480,491` | SetCurveKeys/SetCurveAttributes真实bool；AddCurve/SetCurveFlags沿用现T1，所有调用结果检查 |
| `F:/UE_5.8/Engine/Plugins/Animation/AnimationData/Source/AnimationData/Private/AnimSequencerController.cpp:1317,3415` | 实际Sequencer SetCurveKeys更新RichCurve及Control Channel；没有绕过Controller修改Model |
| `F:/UE_5.8/Engine/Plugins/Animation/AnimationData/Source/AnimationData/Private/AnimSequencerHelpers.cpp:186,218` | 六key数值及三模式的双向转换；原夹具1fps/整数时间避免off-frame重采样。仍由真实Model前置判定结果，不靠推断跳过 |
| `F:/UE_5.8/Engine/Source/Runtime/CoreUObject/Public/UObject/UnrealType.h:1288,1299,7394` | HasAny/HasAllPropertyFlags、FindFProperty/TFieldIterator/CastField；反射来自实际Struct |
| `F:/UE_5.8/Engine/Source/Runtime/CoreUObject/Public/UObject/ObjectMacros.h:436,438,486` | BlueprintVisible/ReadOnly及NativeAccessSpecifierPublic标记；测试还排除Protected/Private |
| `F:/UE_5.8/Engine/Source/Runtime/CoreUObject/Public/UObject/Class.h:2683,2722` | GetReturnProperty/HasAllFunctionFlags；Engine Class.cpp也有同类组合flags调用 |
| `Intermediate/Build/Win64/UnrealEditor/Inc/GGYGOEditor/UHT/GGYGOAnimationCurveSnapshotLibrary.gen.cpp` | 仅只读对照C18已有生成代码：公开字段flags `0x0010000000000014`，Duration为Double、模式Int、返回为Result Struct；不把生成代码阅读冒称新增测试运行或Python实读 |

### 文件保护、资源与架构核对

- 本轮实际核对C18两source、R1两source、原T1、共享夹具、Build.cs、旧Python脚本/报告，共9项SHA256全部保持预检基线；没有共享文件换手。旧R2登记14项资产/配置逐项hash保持，完整值仍见C18表，没有本次UE dirty动态证据。
- 预检追加后原Subleases前11731 bytes / Validation前21052 bytes hashes保持；最终三文件交回读取再次检查前缀与冻结source，差异及三hash在交回输出提供。以上D6/C18内容未改写，31/32历史证据按时间追加而非倒改。
- 样本及状态均为同步RunTest局部值；Model指针仅在测试期间只读观察，未向生产暴露或持久化。临时Package/Sequence及原夹具附属对象遵循既有GC生命周期，没有AddToRoot、强制GC、World/Timer/订阅/新清理责任。没有新增生产校验权威、循环依赖、缓存或执行链。
- 已按计划蓝图重新只读核对Animation架构入口，笔记仍未登记Snapshot接口或本专项。C20禁止Obsidian写入，故不称同步完成；保留C18所列Animation结构/曲线说明/Canvas及专项状态的统筹后续文档阶段，不抢写Movement或全局入口。

### 未覆盖及后续门禁

本步没有编译/UHT/UE/测试/Python/脚本执行、Git或代理。实际反射检查及Controller严格位模式前置尚待运行；不采用旧DLL/R1通过作为新叶证明。第32次总体62 Success/2 Fail仍保持。Python public字段可读、失败返回可见与完整曲线回读另需新probe；原19模式准入矩阵由原R1专项承担，新层只验证代表数值映射。custom Default/非有限/未知enum/非正时长/非null无效对象及无Model等其它失败路径不在新叶重测，不关闭旧真实源夹具缺口。不证明底层Channel/磁盘、骨轨/Graph、七生产资产接线、迁移、PIE/网络或全模块完成。

T1-S已冻结，T1-V仅追加并交回，三文件全部停止写入；后续编译和实际新叶运行由统筹统一安排。真实前置不满足时真实失败并交回，禁止默认填充、放宽或修改租约外共享实现。

## C27 / 11-R3-V1 事实同步预检登记（2026-10-01）

统筹仅授权本记录与 `AAADocs/Modules/Animation/Module_Repair_11_Subleases.md`，由Animation资产组长直接更新顶部当前状态并追加已发生证据。C27开始时Subleases为16321 bytes / SHA256 `A374C6DB4057F1F74DC4B9C618F7CE4852F4EBCAD454E25AAEEE772FC1F34C4C`，本记录为30048 bytes / SHA256 `0A27CED65F81CD06F88E873CB0D0CDA6A4236BF382C2B9815389F57D3DF10815`；历史正文不改写。

本步骤唯一结果、P→V→F顺序、精确文件、只读依赖、非目标、验收断言与停止点已登记于Subleases同名C27节：先登记基线，再同步34/C20/R3实际事实及根因边界，最后全文/历史/保护hash复核并冻结。R1/DTO/C24测试/共享夹具/C25脚本和全部报告、资产保持冻结；无UE/构建/Git/子代理，不扩大到Obsidian或全局入口。公开Model/DTO及单源通过不关闭Channel/磁盘、其它源、骨轨/图、七Profile迁移与生产Run；B0独立诊断失败继续保留。

## C27 / 11-R3-V1 真实验收证据（2026-10-01）

### 根因、决定与历史保留

- 原R2-P实际失败报告仍为 `02AD2D1C3B995911C8A62B2A610642BFDD9A151AD0C4EB666E2F681BBCD1F19B`：CurveName protected导致完整字段读取失败，null-source的bool/out返回转为None使原Error不可见，`complete=false` / 脚本exitCode1。根因是原反射接口未可靠表达Python调用方需要的完整曲线值和失败诊断。已确认的C18方案为三个公开只读值结构、单一Result返回，复用R1的读取/校验/错误；不退回key-only，不添加查询权威、求值、业务默认或另一能力。
- 第33次已成功构建新DLL，但C20实际Fail / 1 Error / 0 Warning / 0.06141979992389679秒，失败在 `SnapshotOutside.ActualFixture.Keys[0].LeaveTangent`（当时cpp第67行），未进入完整11/4矩阵。原报告 `Saved/AutomationReports/ModuleRepairGate_20261001_33/index.json` SHA256 `624287915CDBC1C3E7D7D4857FF9E50973EE15D6D8374F1439CF46365B5EA4E3`，历史失败未覆盖。
- C24根因属于测试的原生值预期：双参FRichCurveKey构造为Linear/Auto、零切线；实际AnimationData的Controller→Channel转换为Linear首键生成出切线，并在Model重建时转换回来。1/1帧率、(-1,-5)/(2,0)对应float32(5/3)，不能把构造时0当最终Model预期。C24严格断言真实Model帧率分子/分母为1，原输入不改，独立ExpectedOutsideKeys仅首键LeaveTangent按原生double除法→float及回写比例计算；不读取DTO或Model观测值生成预期，不改其它字段、位比较、dirty、副本、失败或计数。
- 原生依据继续是本地UE5.8 `AnimSequencerController.cpp:1339,3440` → `AnimSequencerHelpers.cpp:138,218` → `AnimSequencerDataModel.cpp:1015`，33日志实际加载AnimationData。C24三处修改经统筹内存逆向恢复旧测试整文件hash `3EA70519D60CC14ED87EF75B40DC57E4BF5B20FB144A58C26D72C28BDF129C4D`；最终349行/hash `B1360B36C27492BB8205962CDF5D3E8446CDB862943761246E85454B6DDA9BAA` 后冻结。
- C23新探针静态基线为448行/hash `704EAFD82BC7F9DD8DC0D327E6FFE0D72E08999127A3D62EE48AD865C4E6BDC9`。33实际失败时没有运行R3。C25只改docstring及runPrerequisite两处门禁为“统筹确认的最新新DLL+同版C20实际Success”，内存逆向精确恢复C23整文件hash；最终 `5D1FE34066612A44F1071B28ACF37B90E8109BF499A9CFF31ADA0838EC0D0ECD`，其余文字/执行逻辑不变，静态AST/compile-only通过后冻结。上述静态检查没有被写成Python实读证明。

### 第34次完整构建与C20真实专项

实际运行由统筹独占完成，本组只读复核原报告、构建日志与冻结源码hash。`Saved/Logs/ModuleRepairBuildGate_20261001_34.log` 实际10 actions，包含AnimationCurveSnapshotTests.cpp编译及运行时/Editor DLL链接，Result Succeeded / 29.34秒 / UBA 26.05秒；统筹回传exit0。

| 证据 | 第34次实际结果 |
|---|---|
| 常规报告 | `Saved/AutomationReports/ModuleRepairGate_20261001_34/index.json`；SHA256 `BCF9F4E34000DF97FF65640FB0DB9F954D8AEDAD8A4F598939D55723D3557E88` |
| 时间/总量 | 北京时间2026-10-01 16:31:45（08:31:45 UTC）；65 Success，failed/succeededWithWarnings/notRun/inProcess均0，总0.73139739036560059秒；旧65路径保持，无增删（统筹回传） |
| C20叶 | `GGYGO.Editor.Animation.FloatCurveSnapshot`；Success，0 Error / 0 Warning / entries空，0.00861389935016632秒 |
| D6既有叶 | `LocomotionEventsReset`、`OwnerChangeAndD5Compatibility`、`ResetCallbacks` 均Success / 0 Error / 0 Warning / entries空；完整SkeletalMesh/Proxy初始化仍不由这些Native回调测试证明 |

| C20族 | 本次实际闭合的断言 | Snapshot / 直接R1 |
|---|---|---|
| 反射 | 3结构9/6/4共19实际字段、精确类型和公开只读flags，嵌套数组Struct，真实UFunction的单一Result返回 | 0 / 0 |
| 成功/独立副本 | 真实1/1帧率与weighted/empty/outside/probe完整Model前置；clean/dirty各乱序读和修改副本后重读，完整字段/数值位、请求顺序、源内容/Model/时长/dirty保持 | 4 / 0 |
| 失败 | clean/dirty各null和valid-then-missing；同输入真实R1错误全文与false/空/0，两次调用分别检查源不变，不重置dirty掩盖变化 | 4 / 4 |
| 代表原生模式 | RCIM_None+Break、Cubic+RCTM_None、Cubic+SmartAuto，均WeightedNone；真实Model全字段前置及DTO精确比较 | 3 / 0 |

叶末11 Snapshot / 4直接R1计数实际通过；本次覆盖四族完整路径。DTO内部一次R1调用仍是冻结源码的静态核对，以上11/4不作为内部调用仪表。常规65叶通过与原始全日志区分：统筹回传常规日志49条实际Error（启动Smoke13、Damage预期34、Bake预期2）及2 Warning；不写全日志0。

### R3新DLL单源Python真实读回

统筹在同版C20Success且前序UE退出后独占运行已冻结C25脚本；未执行旧R2或扩扫其它源。原报告 `Saved/AnimationCurveReadback/ReadFloatCurveSnapshot_Python_20261001_R3.json` SHA256 `FECD2B9B4D5C36BB8E50982C0462C79ED22DE5DCDC904FE5A8D948919B2FFCEA`，report.scriptSHA256等于C25最终hash。报告窗口北京时间16:35:12.566160–16:35:13.135390（原UTC08:35:12.566160–08:35:13.135390），`status=walk_start_complete`、`complete=true`、脚本exitCode0；统筹回传UE exit0。

固定源：`/Game/Characters/Player/Pyrios/Animation/Movement/Avatar_Male_Size03_Pyrois_Ani_Walk_Start`。实际恰好两次 `GGYGOAnimationCurveSnapshotLibrary.read_float_curve_snapshot`：

1. null-source得到真实 `GGYGOFloatCurveReadResult`，`succeeded=false`、curves空、duration_seconds为正零，原Error全文 `ReadFloatCurves[<null-or-invalid>]: Source is null or invalid.` 可读。
2. Walk_Start得到同一Result类型，`succeeded=true`、Error空、duration_seconds为原值 `1.4166666269302368`，四条曲线按请求顺序读取所有公开属性。

| 曲线 | 完整key数 | flags / pre / post | DefaultValue |
|---|---:|---|---|
| RootMotion_Speed | 86 | 4 / 4 / 4 | 3.4028234663852886e+38（MAX_flt） |
| RootMotion_DirX | 86 | 4 / 4 / 4 | 同一原生哨兵值 |
| RootMotion_DirY | 2 | 4 / 4 / 4 | 同一原生哨兵值 |
| RootMotion_Yaw | 2 | 4 / 4 / 4 | 同一原生哨兵值 |

合计176 keys。实际public getter为Result `succeeded/error/duration_seconds/curves`；Curve `name/flags/default_value/pre_infinity_extrap/post_infinity_extrap/keys`；Key六float及三个int32模式共九字段。名称由真实Name转文字，模式为原生int32，不靠别名/对象字符串解析/默认替代；所有key均读取，MAX_flt不替换或Eval。fieldReads实际1616（两Result共8、四Curve共24、176×9共1584），numericProof实际1062（176×6、四Default、两Result时长）；原float32无损提升、double保留，JSON往返逐binary64位比较并包含零符号位，`jsonRoundtrip.verified=true`。

8个guard阶段全部实际operationAttempted=true：load_module、resolve_api、null_snapshot_call、read_null_result、load_asset、snapshot_call、read_complete_fields、json_roundtrip。每阶段14 hashes与冻结基线一致，protectedDeltaBefore/protectedDelta均空，dirty content/maps前后空、delta空；最终14 hashes/initialDirty/finalDirty亦一致，异常字段未产生。无Controller/Model二次Python读取、骨骼/图访问或资产保存；该Python步骤的源对齐证明依赖C20独立原生Model专项。

日志 `Saved/Logs/GGYGO_AnimationCurveSnapshot_Python_20261001_R3.log` 按实际日志verbosity核对为0 Error / 2 Warning，分类为LogDerivedDataCache写路径和LogPython重名。尾部LogInit **Display**转述这两条告警，不能重复计为4次Warning；告警未屏蔽或写成已修复。统筹回传UE39308（常规）、43312（独立诊断）、13868（R3）各exit0且已退出，242源码与14保护在全部窗口保持。

### 本次记录保护、架构核对与剩余门禁

- C27预检先追加，原Subleases前16321 bytes / Validation前30048 bytes SHA256逐字节保持。随后唯一变化为顶部当前状态/历史说明及文末C27追加；旧D6/C18/C20正文、旧R2失败和33失败保留。最终全文、顶部逆向历史核对及两记录hash随交回提供，原基线已登记，不写自引用hash。
- 本组记录步只读核对14份冻结源码/夹具/Build.cs/脚本/旧新报告，最后复核与开始基线一致；原R1/DTO源码、原测试及共享夹具不改。R3报告本身的14项资产/配置guard与统筹242源码窗口保护分别记录，不把本组14份文件hash称为自行复测242源码。
- 责任与生命周期保持：R1唯一读取/校验/错误，DTO只交付调用者拥有的同步值副本，Python仅调用公开接口与记录证据；无新增权威状态、缓存、帧调度器、循环依赖、跨模块写入或资源订阅。C24测试预期为局部独立值，不修改Model；C27仅两记录，没有新清理责任。
- 有限结论：独立原生Model→DTO四族及Walk_Start完整公开DTO→Python→JSON单源已通过。Channel/磁盘等价、KeyHandle/Color/Comment、骨轨、ABP/BlendSpace图、其余六源完整字段、Profile创建/引用迁移、PIE/网络或生产Run仍未由这些证据证明。当前七Profile仍null，本探针未重新读取其引用；其余六源旧time/value指纹不升级为完整字段证明。custom Default、非有限/未知模式、非正时长、非null无效对象/无Model等历史真实源夹具缺口仍保留。
- 据统筹独立诊断回传，B0严格嵌套来源诊断仍Fail / 1 Error / 0 Warning（严格内层通知实际1、期望0）；本组不复测或修改其源码/记录。常规65Success不能标记全模块绿色或根因全部关闭。
- 已按计划蓝图只读核对Animation架构入口；R1/Snapshot Editor接口、C20/R3新验证状态及曲线说明/结构流程Canvas的差异仍待同步。C27无Obsidian写权；下一局部结构/流程Markdown+Canvas必须另行预检精确文件与共享入口归属，不能以本记录完成声称架构笔记全部同步。
- 本步骤未运行UE/构建/脚本、未创建或改写报告、未保存资产、未Git或创建代理；两记录完成事实同步后停止写入并交回统筹，不自动继续源码、图文或迁移。

## C28-A / 11-Curve-M1-A Markdown事实同步与静态验收（2026-10-01）

### 预检、根因与实际改动

统筹正式授权的四文件、开始hash、唯一契约、非目标、只读依赖、P→M→V顺序、验收断言及停止点已先登记Subleases同名节。C27两记录仅串行换手；先追加P时，原Subleases完整22715 bytes前缀hash实际保持，然后进入两MD写入。根因属于文档事实漂移：旧曲线说明/子图把TickComponent→Sampler→AnimInstance.GetCurveValue当当前链，并把已存在Profile当尚未实现；本步纠正事实，没有实现或重定义架构。

| 实际文件 | 实际diff / 冻结状态 |
|---|---|
| `Animation/曲线处理.md` | 原24行/3299 bytes，改为97行/13047 bytes；重写当前运行时契约、纯求值输出、模拟/预测/原生RMS链和失败后果，保留旧Sampler历史及简要Editor边界；SHA256 `CA0DB46AC8E7BDC0B5B6383331AF04BD8FC4D2A21B52B354FCF97E70CD870757` |
| `Animation/结构.md` | 原39行/5670 bytes，改为55行/9301 bytes；更新曲线导航阶段状态、跨模块接口表与实施/Editor接缝；现有战斗资产说明、Animation类表、ABP接线与生命周期正文保持；SHA256 `FE5CD15F517159B463E7F818B8CAF8837811FB320B57632D69E9F5F2D189183D` |
| `AAADocs/Modules/Animation/Module_Repair_11_Subleases.md` / 本记录 | 顶部两段当前状态/历史说明及末尾C28-A登记/证据；原D6/C18/C20/C27历史正文和失败证据保持，最终两hash随交回提供，不写自引用hash |

### 冻结源码事实及断言核对

- `UGGYGOLocomotionMotionProfile::EvaluateInterval(t0,t1,out,error)`：t0/t1有限非负且t1≥t0，入口Reset样本并清可选Error，每次ValidateProfile；非循环两端Clamp，循环Speed/Direction相位采样、Yaw按周期增量解绕。成功完整提交并true/可选Error空，Speed≥0且正速须有效方向，Velocity/Angle/Yaw等有限，bHasCurveSource=true，合法零速有效，bHasPositionDelta=false；失败false/完整Reset/可选字段原因，无日志或替代Profile。
- CMC在原生移动模拟中持有并推进运动语义、LocomotionMotionTime、WalkRunCyclePhase/BlendAlpha与CurveMotion。WalkRun以共相位乘双侧Duration求值，双成功插值；当前失败/单侧分支照实写出。TickComponent仅Action清理+Super，无SampleAnimCurves调用；旧Cfg_ClipLength判来源、位置/Yaw帧差分没有被保留为当前执行机制。
- 原生 `FRootMotionSource_GGYGOCurve::PrepareRootMotion` 只读取当前样本，安装时BaseYaw决定局部到世界方向；转身入口Yaw与刹停首次安装朝向分别说明。刹停低/零速Finished与保留退场动量、转身留场零速度、离地/Z保护和原生清理是生命周期机制，未写成Profile错误处理成功。Source时间不成为第二Profile播放时钟。
- `FSavedMove_GGYGO::SetMoveFor/PrepMoveFor` 实际保存/恢复语义和时钟基线，没有CurveMotion字段；校正Response清样本并设置权威重演门禁，重演重新求值。采用实际实现，不采信RMS头“恢复CurveMotion”的旧注释；该生产注释未在本租约改动。
- `FGGYGOAnimationStateCapture::Capture` 无跨帧缓存，先Reset后只读Pawn/CMC/ASC；CurveMotion读取用于DebugFrame，StateFrame交付表现语义；不选择Profile、不推进时钟或执行胶囊位移。
- C26冻结cpp `1AD15D3B4FCF36950B620D655B8B9414535C5B4DA65800E06D747B89287896FF` / h `00C3B5A3E7DC963403D8D0FC5D67F361B09ABC40CA1983C20974A04DE89D0C7A` 已实际只读核对。三getter以已接受配置/曲线模式/成功来源及有限非负Speed、Scale、乘积判断资格，活动Action不参与；合法零/极小正/零Scale仍有资格，HasUsableSpeed正速阈值仍仅为刹停/RMS幅值判断。未编译/专项，C27第34次历史构建不作为后续C26动态证明。
- R1/DTO方向与同步值副本责任保持：GGYGOEditor公开Model→R1→DTO，DTO每次调用R1一次；仅简要链接根维护的模块参考实际C20/R3证据与单源限定，没有把Editor链接成CMC运行时输入或详细第二生命周期。

### 全文、链接、保护及历史保留

- 两MD全文读回并逐项与冻结生产契约核对；23处Wiki链接/20个唯一目标全部解析，无缺文件、歧义文件或缺锚点。两个新增 `曲线处理#6. 当前失败消费缺口与实施状态` / `#7. 历史Sampler与Editor读回边界` 可定位；既有Movement方案及动画计划仅作方案导航，不用其旧实施状态证明当前事实。
- 48项限定保护hash在MD修改后均与本步开始一致：C27原14份（R1/DTO、Editor原测试/夹具/Build.cs、两探针及旧新报告）；15份生产依赖（Profile h/cpp、MovementSet h/cpp、MovementTypes h、CMC h/cpp、CurveRMS h/cpp、Sampler h/cpp、StateCapture h/cpp、AnimInstanceBase h/cpp）；14项旧资产/配置；曲线/主Animation四Canvas与动画计划共5份。最终交回再次复核该集合；没有以此声称覆盖其他写入者的C29测试或全242源码。
- 两曲线Canvas仍为结构 `00E704EDA0004E318AF0495C872938D53AC60BD5ECC872232C5937FBDF5099BC`、流程 `82C1D18FCAA97241006D56768D7584C2A341A59F4EF25412A4C9B53B759F9DD8`，保持旧字节；没有Canvas JSON/节点/布局改动。两MD明确B/C待授权，不将A标为全图文完成；动画计划历史状态及详细Editor三图文仍待后续租约，全局入口由统筹维护。
- 两记录截取C28-A之前内容并恢复顶部原两段，可逆向恢复C27冻结整文件；最终全文/历史逆向/hash核对随交回提供。原D6/C18/C20/C27正文、旧R2/33失败、已发生34/C20/R3证据及B0严格诊断失败均保留；无冲突标记或新增行尾空白。

### 架构核对、剩余边界与冻结

本步仅文档事实纠正；唯一权威和依赖方向不变，无新代码、业务默认、循环依赖、状态/执行链、缓存或资源订阅，没有新增清理责任。未修改源码/test/script/report/资产/配置、Movement笔记、全局入口、主Canvas、两曲线Canvas或动画计划；未UE/UBT/构建/Git/脚本执行/代理。

完整失败传播仍开放：EvaluateLocomotionProfile忽略false/不接Error而推进时间；WalkRun单侧成功替代，双失败进入求值后仍推进相位；缺失/非法Profile可被IsCurrentMotionFinished当完成；曲线无资格的GetMaxSpeed仍可能返回固定步态；RMS正速缺方向仍改前向。未把理想拒绝/中止画成已实现，也未以C26成功零资格局部修正关闭这些根因。

七Profile引用既有证据仍null，本次未重新加载/迁移；ABP图、其余六源完整公开字段、Channel/磁盘、骨轨、Profile接线、Dedicated Server/PIE/网络和生产Run仍未验收。C29只写测试/10记录的实施归其他作者，本步未读取/执行其夹具，不声称新测试或门禁通过。四文件完成静态交回后冻结停写；B/C、Editor详细图文和任何架构修正均须后续独立授权。

## C28-A / 11-Curve-M1-A 第35次门禁有限事实补充（2026-10-01）

### 同范围续更与证据来源

统筹明确只续更C28-A原四文件当前事实；首轮已冻结hash实际一致，记录于Subleases本补充节，不重置预检/扩大范围。两MD把当前“C26未编译/专项”改为35有限实证；两记录仅顶部状态/历史说明及本节追加。之前C28-A首次静态交回、D6/C18/C20/C27、34与旧失败完整保留，未验证状态属于各自当时阶段。

本组实际只读核对35原报告、构建日志及原始运行日志；UBT/UE退出、窗口242源码/14保护和断言覆盖范围由统筹回传，不读取C29源码夹具，也不自行执行UE或构建。

| 第35次证据 | 已发生结果 |
|---|---|
| 完整Editor构建 | `Saved/Logs/ModuleRepairBuildGate_20261001_35.log`；Succeeded / 6 actions / 34.99秒 / UBA32.04秒；新 `UnrealEditor-GGYGO.dll` 实际链接；exit0由统筹回传。日志SHA256 `F4300D7EA2C0F6F2BE01BA99281B94B5D24BB5CA2379FB4C81CB98F2E94EE625` |
| 项目报告 | `Saved/AutomationReports/ModuleRepairGate_20261001_35/index.json`；SHA256 `F2DFBCF244512B11EB669D29DFAAD2C21310103E9D9EDA74D098B5ED8A1718A6`；原09:37:52 UTC=北京时间2026-10-01 17:37:52；65 Success，failed/succeededWithWarnings/notRun/inProcess均0，总0.7469504475593567秒 |
| C26/C29消费者 | `GGYGO.Movement.Locomotion.AuthorityAndMapping`：Success / 0.00962350144982338秒 / 0 Error / 0 Warning / entries空 |
| ActionMotion | `GGYGO.Movement.ActionMotion.TimingAndOwnership`：Success / 0.010235998779535294秒 / 0 Error / 0 Warning / entries空 |
| C20 | `GGYGO.Editor.Animation.FloatCurveSnapshot`：Success / 0.008245799690485秒 / 0 Error / 0 Warning / entries空 |
| 原始日志 | `Saved/Logs/GGYGO_ModuleRepairGate_20261001_35.log` SHA256 `83775DAAA7A204935596F6D60C1E5EF029AAE964C03658016CD2E2F538351AA2`；按真实severity实际49 Error（AutomationTest13、GGYGOAbilitySystem34、Animation2）/2 Warning（DDC/Python各1），Display转述不重复计数。统筹说明原因同34（启动Smoke、伤害/Bake预期日志）；不称全日志干净或已修复这些日志 |
| 统筹窗口保护/退出 | UE40532 exit0且已退出，无保存资产；242源码/14保护保持。此为统筹回传，与本组限定hash复核分开 |

### 有限结论、Markdown状态与未关闭边界

C26成功来源资格不以正速阈值判定已由新运行时DLL及严格消费者专项有限验证。合法零速度、极小正速度、零Scale资格与GetMaxSpeed/ForceWalk、显式fixed模式通过；失败/溢出场景只验证资格拒绝。没有将“资格false”写成整体拒绝/中止/错误传播成功，也没有把GetMaxSpeed固定步态分支当已移除。HasUsableSpeed仍是刹停/RMS幅值判断。

本次两MD仅替换当前C26/C29验证状态、追加35有限报告来源与RMS内部非有限消费边界，Profile纯求值/CMC时钟/预测/RMS/Animation/Editor职责不变；无架构或接口重定义。曲线MD当前99行/14198 bytes/SHA256 `2128D728E8A5988E07D7B3CA46D41D28FDAFADF1D16F7A2DEA66341424874B13`；结构MD当前55行/9531 bytes/SHA256 `5B77F4ABA5F765A1D738DA974E9787CC3D7CC87A804A52E80D7900E364034F8A`；前次两MD旧hash保留为首次冻结证据。

仍未关闭：EvaluateLocomotionProfile忽略false/错误而推进时间；WalkRun单侧替代与双失败进入求值后推进相位；非法/缺Profile当完成；失败或非法样本落到固定步态速度；RMS正速缺方向前向替代及内部非有限乘积/方向/追帧比例消费的拒绝/诊断契约。七Profile既有引用证据仍null，ABP图/其余六源完整读回/Channel磁盘/骨轨/Profile迁移、Dedicated Server/PIE/网络和生产Run未由本次消费者专项证明；B0旧严格诊断Fail仍保留。

### 静态核对与再次冻结

最终全文/链接及保护核对随交回提供：两MD23处Wiki链接/20唯一目标保持；原48项限定保护hash与首次C28-A及本次开始保持，另复核35报告/构建日志/原始日志3项。两曲线Canvas原字节/hash不变，B/C和详细Editor子图尚未授权，不因本补充标记全图文同步。

两记录截取本第35次补充前内容并还原顶部原两段，可逆向恢复首次C28-A冻结整文件SHA256 `A3CC9523D490401B1A853DDCBB65023B7455C2BA9225A97BCAC48910B6B297A3` / `B26B0649F4293613988E9B543A13BA8533B4D38418ABD973B838FD53AF73F9A6`；历史正文/失败不改。四最终hash随交回，不写自引用hash。无新增状态/执行链、循环依赖、缓存、资源或清理责任；没有源码/test/script/report/资产/Movement笔记/全局入口/主图写入，没有UE/构建/Git/脚本执行/代理。四文件完成同范围事实续更后再次冻结停写，不自动进入B/C。

## C28-B / 11-Curve-M1-B 结构图静态验收与冻结（2026-10-01）

### 预检、实际范围与冻结顺序

统筹接受A后仅授权结构Canvas与11两记录。Subleases先登记三精确文件、开始hash、唯一契约/非目标/只读依赖/断言/停止点；原32934 bytes前缀hash实际保持，再制作图。复用已接受A/B/C方案及冻结生产事实，无长篇重复调查或接口重定义。结构图全文/JSON/链接/布局核对通过后已在本会话明确冻结，再更新两记录；图冻结后没有继续写图。

结构Canvas原170行/5234 bytes、10节点/8边，改为180行/11483 bytes、10节点/9边；最终SHA256 `6EC0EDF8F33EC54794E7A5718DE5AF5B6424BC1A84FEA7EAE8D687B5AD8775AB`。两记录仅顶部状态/历史说明与B登记/本节追加，原历史不改，最终两hash随交回提供，不写自引用hash。

### 实际图文差异与源码契约核对

| 节点 / 边 | 当前结构事实及实际修改 |
|---|---|
| asset / e1、e9 | 原烘焙动画节点改为实际MovementSet模式/七Profile引用与ValidateMovementSet(bool/Error)；e1持有Profile，新增e9为CMC持有校验成功的MovementSet。显式fixed可空Profile与曲线依赖失效的后果分开；SetMovementSet拒绝保持未接纳，不写成默认Walk/Run配置。 |
| profile / e8、e3 | 从底部“未实现目标”移到输入层，计划色3→数据色4；实际Profile数据、ValidateProfile及EvaluateInterval(t0,t1,out,error)输入、Clamp/循环Yaw解绕、true完整值/false Reset/可选Error、合法零与正速方向约束均明确。e8 CMC调用，e3返回OutSample由CMC接收，资产无播放时钟/日志/缓存。 |
| cmc / e4、e5 | 实际唯一语义/单次时间/WalkRun相位混合/Sequence及CurveMotion，移动模拟选择/求值、SetMovementSet、三getter/Yaw及RMS安装/移除/准入清理。e4 CMC owns并写当前样本；e5安装/移除自有原生Source。无Tick→Sampler或第二调度器。 |
| motion / e6 | 规范类型FGGYGOLocomotionCurveSample及字段/PositionDelta=false；成功来源含合法零值，HasUsableSpeed仅幅值阈值。e6只读数据由RMS经CMC.GetCurveMotion消费，样本无独立状态/时钟权威。 |
| rms | 只执行当前样本，PrepareRootMotion输入当前数据与安装BaseYaw/Scale/策略，输出Direction×缩放Speed的世界速度；安装基准、零/低速退场/留场、离地/Z与原生清理说明。Source时间/追帧比例不成为Profile时钟，NetSerialize仅该Source字段；内部方向替代/非有限消费仍开放。 |
| saved / e7 | 实际SetMoveFor/PostUpdate/PrepMoveFor语义/时间基线与权威校正门禁，恢复后CMC再求值，不存CurveMotion。e7保留ID，显式双向箭头/三行标签表示保存/恢复数据基线，不表示另一个播放器或权威。 |
| anim / e2 | 原“AnimInstance供CMC反读”改为游戏线程StateCapture只读Pawn/CMC/ASC，StateFrame/DebugFrame输出与表现清理。e2改为Capture对CMC只读查询依赖；ASC真实模块链接在节点中，Animation不反馈移动。 |
| sampler | 移入底部历史区，保留Sample/ResetBaseline旧工具与兼容别名说明；无任何边连入当前运行时，历史Cfg/差分/隐式替代不作为Profile成功契约。 |
| contract / nav | 35有限消费者通过与当前未关闭源码后果、七Profile/运行边界；当前结构、待C流程/导航MD/计划和独立Editor候选分别明确，无Editor→CMC运行时箭头。 |

全部10节点ID及既有8边ID保留，唯一新增e9；节点顺序保持，9节点颜色不变。原三列相对关系继续使用，Profile输入层/Sampler历史区重排及节点宽高/间距增加用于稳定接口与正文容量，未机械拆节点/新建文件。节点以职责和唯一状态归属组织；接口中简写参数与完整输入输出链接到A已冻结Markdown。

### 静态JSON、布局、链接与保护核对

- 实际文件可解析；10个text节点+9边共19 IDs唯一，无重复。所有端点存在，from/toSide合法，每条边有持有/调用/返回/只读消费/基线往返标签；预测fromEnd/toEnd均arrow，其余方向由fromNode→toNode明确。历史sampler关联边数0，无Editor运行时输入节点/边。
- 节点矩形两两无重叠、宽高正且坐标有限。以正文18px/行高30、标题27px/行高38、左右/上下28px保守计算自动换行与空行容量：nav214/280、asset486/580、anim440/640、sampler500/610、motion576/720、cmc772/900、rms502/750、saved546/830、profile606/780、contract562/930（估算正文需要/节点高度，px）。余量66–368px；不是Obsidian原生渲染证据，主题/缩放和原生视觉验收未运行。
- 14处Wiki/11唯一目标全部解析，含Animation曲线2/4/5/6/7节锚点、Animation/Movement/AbilitySystem结构及流程/计划入口，无缺文件/歧义/缺锚点。流程/计划明确待同步或方案历史，不用旧实施字句证明当前事实。
- 52项限定保护hash在制图后保持：前步51项去掉本目标结构Canvas，再加入A两MD；包含其余3Canvas/动画计划、15生产依赖、R1/DTO与Editor原测试/夹具/Build.cs、两探针/旧新报告及35日志、14资产/配置。A两MD当前hash `2128D728E8A5988E07D7B3CA46D41D28FDAFADF1D16F7A2DEA66341424874B13` / `5B77F4ABA5F765A1D738DA974E9787CC3D7CC87A804A52E80D7900E364034F8A` 保持；旧流程Canvas `82C1D18FCAA97241006D56768D7584C2A341A59F4EF25412A4C9B53B759F9DD8` 保持，未自称保护全部242源码。
- 两记录截取B之前内容并恢复顶部原两段，可逆向恢复A第35次冻结整文件hash `B53B76F2F7608F3A4F6FD3CC452CBF1B61A7DE46DBC73E875E6C1EE3A85E29BC` / `07A80FFBDC024AA666C108BAAA197D0BE126554A960F41A7C023943D5CE7391E`；最终全文/历史逆向/保护及三hash随交回复核。D6/C18/C20/C27/C28-A/35及旧失败保留，无新增冲突标记/行尾空白。

### 未验项、架构核对与停止

本步仅当前结构事实纠正，没有源码/test/scripts/reports/资产/配置、A两MD、流程/主/其它Canvas、动画计划、Movement笔记或全局入口写入；没有UE/构建/Git/脚本执行/代理或Obsidian原生渲染/动态运行。既有状态/依赖/清理责任不变，无新循环依赖、重复状态/执行链、缓存或资源订阅；配置、求值、执行和表现责任分开，返回值/只读样本未变成第二事实来源。

35真实消费者仍仅有限证明成功零/极小正/零Scale资格、GetMaxSpeed/ForceWalk与显式fixed模式，失败/溢出仅资格拒绝；求值false被忽略/失败时间推进、单侧Loop替代、非法段完成、GetMaxSpeed固定分支、RMS方向/非有限内部消费未关闭。七Profile既有引用仍null，ABP/资产/Profile迁移、Dedicated Server/PIE/网络、生产Run及B0严格诊断仍未完成。没有把理想统一拒绝/中止画为当前实现。

C流程、A两MD原“B待同步”的阶段导航字句、动画计划和详细Editor子图仍需后续独立租约。图及记录明确剩余差异，不能以B完成称全部图文同步；本步不能越权改这些文件。三文件交回后全部冻结停写，不自动C/导航MD/Editor。

## C28-C / 11-Curve-M1-C 流程图静态验证与冻结（2026-10-01）

### 1. 范围、执行次序与唯一产物

仅写授权流程Canvas、Subleases、Validation三文件；先预检，图完成并冻结后才同步两记录。A两MD、B结构图、主图/计划及生产/测试/资产保持保护；未UE/构建/Git/脚本/代理，未增加子图或第4文件。源码契约复核以冻结生产实现及UE5.8原生CMC为依据，未读取第10批记录。只读范围偏差：一次rg目标误设为Source/GGYGO目录，包含Character/Tests，不能保留未读取C22/C29测试源码的保证；后续已恢复精确生产文件检索，测试未修改或运行，也未把该检索当新增测试验收。

流程Canvas：498行 / 22853 bytes；25节点 / 30边；SHA256 `E5C4E8CDA7165F72D1FDA89C214C2F6DCD60021A1284F20919F3FDBACBAC184A`。实际行diff（不使用Git，LCS）：+388/-68（178→498行）。 原10节点/9边ID和10节点颜色全部保留；15新增节点/21新增边把Action、准入、单段/WalkRun结果、RMS门禁、早期累积、普通/Override物理、After、重演与抓帧展开在同一既有链和只读入口中，无新状态所有者或帧调度器。原10类式节点已改为触发者/方法/参数/产物/分支，不再以旧SampleAnimCurves→帧差分画成当前执行。

### 2. 源码与执行顺序核对

| 冻结只读依据 | 图中契约/后果 |
|---|---|
| CMC SetMovementSet，613～652；ResetLocomotionState，654～674 | 输入InMovementSet/可选OutError，撤旧绑定/恢复组件基线/复位后验证；非法非空false并诊断，nullptr合法解绑false/清错误/无报错；配置状态边不表示每move重新装配 |
| CMC Before，913～960 | CleanupFinishedActionMotion；活动Action清样本后Super返回；未接纳配置清自有Source并按实际Montage提取时机延后最终准入；非Proxy ResolveGait→UpdateLocomotion→Brake→Hint，TurnRMS函数自身排除Proxy后Super |
| CMC共相位，1122～1190；单段1192～1212；选择/转身1313～1365 | WalkRun存在侧条件求值、双成功混合/单侧复制/双失败Reset、进入结果段仍推进共相位；模式/双空/小周期早返不推进。单段忽略bool/OutError，Reset后仍推进段时间，TurnBack调用处仍AdvancePhase |
| UE5.8 PerformMovement，2846/2852/2874/2918/2941/2992/3034/3042/3044/3046 | 早期快照后清无效RMS；Before→有门禁Prepare→早期Override速度累积→StartNewPhysics→After→条件PhysicsRotation。Prepare门禁包括早期快照、非clientUpdating/非serverIgnore，不能由“Before安装Source”推定必同move准备 |
| UE5.8 PhysWalking，5714/5716/5720；CMC GetMaxSpeed，736～768 | 无AnimRM/Override且非ledge跳过时CalcVelocity并查询上限，再ApplyRootMotionToVelocity；普通无RMS仍执行。合格曲线Speed×Scale含成功零/极小正/0Scale，ForceWalk上界；显式fixed独立，曲线错误转固定步态仍为缺口；结果提交不等于挂RMS |
| CMC PhysicsRotation，1405～1445；Source更新1506～1583 | Action/地面准入优先；非Proxy转身读取YawDelta，当前非有限置0、非近零扫掠转角后返回。Brake/TurnBack按既有条件可选安装/移除，固定入口BaseYaw/Scale，不把GetMaxSpeed资格当RMS内部安全证明 |
| 已冻结A/B生产契约 | SavedMove只保存/恢复起始语义/时间/共相位，不存样本，校正后复用同CMC链；Animation独立更新时Reset再Capture，数据关联边不规定与本move的相对Tick顺序、不反写CMC。旧Sampler仅历史，Editor R1/DTO工具独立 |

23条关键主线、分支、返回和入口关联逐一存在；普通及Override物理均在完整StartNewPhysics返回/HasValidData后接After，再接条件旋转。Proxy仅描述源码回调分支，未将权威PerformMovement顺序冒称Proxy原生运行证明。Physics子步沿用当前样本，不另建Profile时钟；所有Profile提交不强制经RMS。

### 3. 静态结构、链接、布局与保护证据

- 全文回读与提交JSON文本相同；25节点/30边ID唯一，所有端点/side有效、30边标签非空、节点坐标有限/尺寸正数；关键路径检查0失败，节点矩形0重叠。
- Wiki链接9处/5真实唯一目标：Animation曲线说明、B结构Canvas、Movement结构、Animation结构、AbilitySystem结构；“5. 预测恢复与Animation只读Capture”和“6. 当前失败消费缺口与实施状态”两锚点逐字存在，无新增失效链接。
- 正文静态容量按CJK18px/Latin10.8px、正文30px行高、标题27/15px与38px行高、空行16px、56px内边距估算：25节点余量106～114px，整图范围3880×5570。未在Obsidian原生渲染；字体差异、连线路由及边标签可读性没有视觉实证，本项仅为正文/几何静态核对。
- 52保护项全部哈希不变，含A两MD、B结构Canvas、主图/计划、冻结生产源码、Editor/R1/DTO及既有脚本/报告/日志、14资产配置。保护检查不冒称重新复核全242源码或动态资产运行。
- 两记录仅顶部两段和本C预检/证据追加；D6/C18/C20/C27/C28-A/35/C28-B历史正文、失败证据保持。最终以截去C追加并恢复B顶部两段的方式复原原字节，基线分别为39979 bytes / `EF8F3CA95A08CDB7C51EE7AABC99FD48A73D76FCE86AC4C67BC1E774E53F1A65`、60741 bytes / `93AAD124ABCFE509369F617FFFF8A653F5DCA1F09C85AE93AE22E8BA9588F6E6`；实际逆向/hash结果随三文件交回。

### 4. 限定验收与未完成项

第35次完整构建Succeeded/exit0，统一65项Success/其它0及AuthorityAndMapping有限消费者实证仍以既有报告为准；失败/溢出仅资格拒绝，没有完整失败传播证明。原始49 Error/2 Warning保留，未将局部entries为空扩写成整日志干净；本步没有新增UE或动态运行。

图如实保留当前求值false/错误忽略、单侧Loop替代、失败仍计时/相位推进、非法Profile当段完成、曲线错误固定速度消费，以及RMS方向/非有限内部消费和非有限Yaw置0边界。既有七Profile引用null、ABP/资产迁移、首次Source安装同move Prepare、Proxy/DS/PIE/网络及生产Run未动态验收。A两MD阶段导航旧字句、主图/动画计划/Editor细图尚待独立租约；不以本C完成宣称整体失败关闭或全部图文同步。

图先冻结，两记录完成全读/历史还原/保护复核后，三文件一并冻结停写，交回统筹；不自动修改导航MD或Editor细图。

## C28-NavM / 两Markdown导航阶段静态核对（2026-10-01）

### 1. 唯一改动与冻结顺序

统筹已独立全文接受A/B/C；本步只纠正两MD导航/实施状态，按预检→MD最小修改→全文/链接/事实核对→先冻结MD→记录顶部/追加执行。未新建或修改A5 Guard、Movement helper、源码/测试/脚本/资产/配置、Canvas或第10批记录；没有UE/构建/Git/代理操作。两Canvas内部nav留给独立NavC，主图/计划/Editor另阶段。

| 文件 | 唯一改变行与含义 | 冻结结果 / 实际diff |
|---|---|---|
| `Animation/曲线处理.md` | 3/5/89：A/B/C静态接受、当前B/C图入口与后续NavC/计划/主图/Editor边界；移除旧B/C待同步/两图仍旧执行链导航 | 99行 / 14486 bytes；+3/-3；SHA256 `7AF891EED02B76C91C7DEC08512BD197AE780E748F009CD249B03BDF688011FF` |
| `Animation/结构.md` | 9/11/49：主图待独立同步、曲线B/C静态接受及NavC/视觉/失败链边界；移除旧Sampler作为当前图依据 | 55行 / 9757 bytes；+3/-3；SHA256 `68AC9EB01AA827C1AFFDABA0EB0F0DE663BADDFA0C2D27C9443EFA9997455AE2` |

所有其它行逐字不变，行数未变；仅6处预定导航/阶段行差异，类、参数、算法、状态唯一归属、接口/生产源码和报告事实未修改。旧Sampler历史说明保留，未新增执行入口、缓存、生命周期、共享接口或循环依赖。新导航明确A/B/C是静态接受，完整失败/RMS消费、七Profile/资产/网络/生产Run及Obsidian原生视觉仍未完成。

### 2. 链接、保护与历史核对

- 全文回读与预定文本相同；既有Wiki目标/锚点序列逐字不变，无新增链接；23处链接、18唯一真实目标、4标题锚点核对通过。简写`计划_玩家普攻连段`唯一匹配`AbilitySystem/计划_玩家普攻连段.md`；仅查存在性/所需标题，未改目标。
- 两MD旧“待同步结构图/流程图、待C28-B/C同步、两张图仍旧Sampler执行链”当前导航已清除；仍保留计划/主图/Editor与Canvas内nav后续边界。当前算法/接口描述未扩写，未引入A5 Guard接口或Movement helper。
- 非租约51项哈希不变，包含B结构/C流程Canvas、Animation主图/计划、冻结生产与Editor/R1/DTO、既有脚本/报告/日志和14资产配置。两Canvas仅哈希保护，未编辑或开展原生渲染；本步未读取生产/测试源码或第10批两记录。
- NavM记录写入前，Subleases完整C基线48187 bytes仍为精确前缀，仅后接本预检；Validation完整C基线67311 bytes保持。两记录后续只改顶部两段/追加NavM，原D6/C18/C20/C27/A/35/B/C全部历史正文和失败证据保持，特别保留C一次rg目录误含测试范围的偏差，不能以NavM的只读合规覆盖该历史。
- 最终逆向还原方式：截去首次NavM追加，恢复C基线顶部两段，以UTF8无BOM字节计算；应为Subleases `2B109FC5130461523D7FCA94BB5770CD6A2A4FED77DE5ADBFE13C8182E3D2E7A` /48187 bytes和Validation `E751D0B702184B122602C7FEE4C2B8D27FEEC618B422C48F4A6186E2BCFC689A` /67311 bytes。实际四文件diff/hash及逆向结果随交回提供。

### 3. 验收边界与停止

本步仅关闭两Markdown导航与阶段状态一致性；第35次完整构建/65项Success及AuthorityAndMapping有限消费者证据保持，没有新动态验收。原始49 Error/2 Warning仍是历史事实，完整失败传播/RMS内部消费、七Profile既有null/ABP迁移、首次安装Source同move准备、Proxy/DS/PIE/网络/生产Run以及原生视觉均未关闭。

两MD已先冻结；两记录完成全读/实际diff/历史逆向/hash/保护复核后，四文件冻结交回并停止写入。Canvas nav、Animation主图/计划/Editor及A5 Guard/Movement helper/其消费者各须另租约，不自动开工。

## C28-NavC / 两Canvas导航单字段静态验证（2026-10-01）

### 1. 范围、唯一差异与先行冻结

NavM已获统筹独立接受，两MD冻结；本步只写精确授权两Canvas的nav.text及11两记录。顺序为小预检/基线→只nav文本→JSON/链接/反向/保护→先冻结两图→记录顶部/追加→四文件交回停止。未新建图/接口、修改A5 Guard/Movement helper或其消费者，未写第五文件/MD/其它图/源码/测试/资产/脚本/全局/第10批记录，没有UE/构建/Git/代理操作。

| Canvas | nav当前结果与静态核对 | 冻结结果 / 实际diff |
|---|---|---|
| `Animation/GGYGO_结构_动画曲线.canvas` | 当前结构/流程及配套说明入口；清旧C28-B/C待同步历史，保留计划/主图/Editor与失败/动态/视觉边界；10节点/9边 | 180行 / 11539 bytes；第6行+1/-1；SHA256 `A916088F11139C18281D6BE6EF362D575B8F3A184A10C0DCC6AC34CBB13D823F` |
| `Animation/GGYGO_流程_动画曲线处理.canvas` | 当前结构/流程入口；清旧C28-C/MD待授权历史，保留已有主线/独立入口及完整失败/动态/视觉边界；25节点/30边 | 498行 / 22932 bytes；第6行+1/-1；SHA256 `B19459608D9356D0EF1A2AB8914E37DFD37EFB3FDA13855F6FE742253EF7CC7B` |

每图只有id=nav的text变化；其余全部JSON对象/数组顺序、节点/边/ID、coords/size/color、其它正文/算法/方法/参数/接口均完整相同。nav链接允许别名更新，但完整目标及锚点序列逐字相同；没有用文档导航加入新执行链或状态归属。

### 2. 反向全文、链接、容量及保护证据

- 全文回读与预定仅nav替换文本相同。将当前nav JSON文本反替开始原nav，完整原JSON文本逐字恢复；UTF8无BOM字节SHA256实际为结构 `6EC0EDF8F33EC54794E7A5718DE5AF5B6424BC1A84FEA7EAE8D687B5AD8775AB` /11483 bytes、流程 `E5C4E8CDA7165F72D1FDA89C214C2F6DCD60021A1284F20919F3FDBACBAC184A` /22853 bytes，两项通过。
- JSON节点/边ID唯一；全部端点/side/非空标签/有限坐标与正尺寸有效；节点矩形0重叠。原B/C已接受的结构/执行链未重写，本步仅导航，不新增源码/算法验证。
- 两图Wiki共23处、7不同文件目标、8标题锚点引用（6不同目标+标题），存在性及所需标题全部通过；完整目标/锚点顺序保持。别名只清理nav阶段标记；其它节点链接文字也完全保持。
- 导航节点坐标/尺寸/颜色保持：结构2540×280，流程3860×320。按CJK18px/Latin10.8px、正文30px、标题27/15px与38px、空行16px及56px内边距估算，两nav正文各214px，余量66/106px。原生字体/连线路由/边标签/完整Obsidian渲染没有视觉实证，不把几何静态通过称视觉验收。
- 51非租约保护项哈希不变，包含NavM两MD、其它主图/计划、冻结生产/Editor/R1/DTO、既有脚本/报告/日志和14资产配置；不冒称全242源码重验。NavC没有读取生产/测试源码或第10批记录，没有UE/构建/Git/代理/脚本/资产运行。
- 记录V前，Subleases完整NavM基线54140-byte为精确原前缀，仅后接本预检；Validation70985-byte完整基线不变。V仅顶部两段/追加NavC，所有旧D6/C18/C20/C27/A/35/B/C/NavM历史、失败及C读范围偏差保持。
- 记录最终逆向：截去首次NavC追加并恢复NavM顶部两段，应精确复原Subleases `494504F0417166E56FC901FC1F57818E8E483270EC0FE7F901BA36998A18E46E` /54140 bytes及Validation `C9F19A4A92615C7B37ADF01500FE4B698B27CC930CB1A7E221F423B5500BDBAC` /70985 bytes；实际逆向/hash及四文件diff随交回提供。

### 3. 剩余边界与停止点

本步只关闭图nav的过时阶段标记与入口状态；当前结构/流程与配套说明仅静态可用。NavM两MD保持冻结，其“内部nav待独立NavC”阶段原句本步未改写，与现NavC完成状态存在文字差异，不能标记所有导航已同步；需统筹另租约交接。主图/动画计划/详细Editor图文、完整求值失败传播/RMS内部消费、七Profile既有null/资产接线、首次Source安装同move Prepare、Proxy/DS/PIE/网络/生产Run及Obsidian原生视觉继续开放。35有限消费者/65 Success与原49 Error/2 Warning日志事实保持，没有新增动态验收。

两图已先冻结；记录全读/实际diff/历史逆向/保护核对后，四文件全部冻结交回停写。Editor/计划/主图/A5 Guard/Movement helper及其消费者须另租约，不自动执行。

## C28-NavM2 / 两MD句级状态收束静态验证（2026-10-01）

### 1. 精确改动与MD先冻结

仅第一步NavM2四文件授权；两MD原89/49行内指定NavC待处理短句改为“内部导航已完成静态核对”，所有其它字句完整保持。按预检/基线→只两句→全文/引用/边界/逆向/限定保护→先冻结MD→记录顶部/追加执行。第二步A5结构契约未授权，没有Canvas/接口/算法/第5文件或源码/资产操作。

| 文件 | 唯一差异 | 冻结结果 / 实际diff |
|---|---|---|
| `Animation/曲线处理.md` | 原89行仅“留待独立NavC交接”阶段句收束 | 99行 / 14470 bytes；+1/-1；SHA256 `25E635C50F0F37076C00C322768F53616DA0FEC934D11CB447E6206B70D7C124` |
| `Animation/结构.md` | 原49行仅“交独立NavC处理”阶段句收束 | 55行 / 9744 bytes；+1/-1；SHA256 `BD73B8536B0F55109BEDB37F5BB8F6B4539A181F3BC84A4F08AB9B4FB89E6102` |

其它正文、源码事实、接口/算法/报告说明以及每行非目标片段均逐字相同，行数未变；没有借导航修改Guard或Movement契约。主图/计划/Editor、完整失败/RMS消费、七Profile/资产网络/生产Run及原生视觉边界保留，本步没有新增动态或整体完成结论。

### 2. 全文逆向、引用与限定保护

- 实际全文与预定两短句替换相同；替回原短句精确恢复整份MD文本。UTF8无BOM字节实际SHA256分别恢复`7AF891EED02B76C91C7DEC08512BD197AE780E748F009CD249B03BDF688011FF` /14486 bytes、`68AC9EB01AA827C1AFFDABA0EB0F0DE663BADDFA0C2D27C9443EFA9997455AE2` /9757 bytes，均通过。
- 两MD23处Wiki链接/18真实目标/4锚点有效，完整目标+锚点序列逐字不变；旧NavC待处理短句已清除，没有新增引用或改变目标。
- 40本会话非租约保护及其中14资产配置哈希不变，范围仅本会话文档/图、Animation/Editor既有保护与脚本/证据。其它模块生产/测试范围被排除；K4-I1/P1-T1正在独立源码写入，不能将本项写成全部源码稳定、统一冻结或全242重验。
- 第36次窗口结束的排程通知只作为当前门禁上下文，本步不新增第36次构建/自动化/生产验证结论。未UE/构建/资产/Git/代理/脚本运行，未读取生产/测试正文或第10批记录。
- V前Subleases完整NavC60909-byte基线是精确前缀，后面仅本预检；Validation75439-byte完整基线保持。V只顶部两段和NavM2追加，截至NavC的全部历史、失败、C只读范围偏差与NavC当时MD未解冻差异说明完整保持。
- 最终记录逆向：截去首次NavM2追加、恢复NavC顶部两段，UTF8字节应为Subleases `C5F704EAF27F67E51B2FB6FC64E780F13C32374022E8F3D9775C8C6B9DA4B1D0` /60909 bytes、Validation `28D0C44802E9783143B0AB215A827A32A614FDB37812EC88D6079BD8DED0C8DA` /75439 bytes；实际逆向/hash与四diff随交回。

### 3. 停止与未验边界

两MD已先冻结；两记录完成全读/历史整文逆向/限定保护后，四文件冻结交回停写。NavC待处理阶段差异本步收束，但主图/计划/Editor、完整失败传播/RMS内部安全、七Profile既有null/资产接线、Proxy/DS/PIE/网络/生产Run及Obsidian原生视觉仍未验收。35有限消费者与49 Error/2 Warning事实保持，未新增动态验收。

A5结构第二步、Movement helper图文及其它生产/消费者工作须独立授权，不自动执行。

## C37 / Animation Montage Guard主结构验证范围登记（2026-10-01）

实现前已登记两记录；本步唯一目标、精确四文件与全部基线见同批Subleases的C37原子范围。当前仅P，尚未完成MD/图实现与验证，不能写作已通过。

- 基线：结构MD `BD73B8536B0F55109BEDB37F5BB8F6B4539A181F3BC84A4F08AB9B4FB89E6102` /9744 bytes；主结构Canvas `DECA4D2EF83090ED24DD59621C9CBEA41C86E316BB0106C66BE53B1D99B35107` /10073 bytes；Subleases `7A7AE170DFEE8B09603D93A66BD42BBCF39AAA81AA6E4F85A4030A5F3D7B9106` /66534 bytes；本Validation `3AC26FC2E33A0487A00A9FC72762D466D86E4CC2D928BC376CD7B36EAC918A30` /78875 bytes。
- 原图16节点/12边所有内容保留；仅预检四新节点与五新边。MD仅两类行、Base继承及“Montage播放Guard的静态契约”小节。A5查询只读面板，无Query→ASC/Task完成消费边。
- 生产/测试/UE/构建/资产/Git/代理/其它图文均不在写权；43限定保护含14资产配置，不报告全源码冻结。38门禁仅统筹事实，37失败保留；消费者/AnimClass迁移、严格P1/网络/原生视觉开放。
- 计划断言：全文精确回读、ID/端点/矩形/容量/新增链接锚点、MD与原图整文逆向及两记录历史逆向；先冻结MD/图再写验证结果。若有第五文件或旧图/接口变更需求，停止交回。

## C37 / Guard主结构静态验证、权限事实及冻结（2026-10-01）

### 1. 实际产物与唯一契约

P先登记两记录，MD/图实现与Q完成后先冻结，再V写验证。Guard/借用Scope/Base/ASC/Task的静态职责、关键查询与权限边界为唯一结果；没有源码/消费者/资产实现。

| 产物 | 实际结果 | SHA256 / 行diff |
|---|---|---|
| `Animation/结构.md` | 77行 / 14128 bytes；仅两类行、Base继承、独立“Montage播放Guard的静态契约” | `C600C8D2A47BC3CE09CD01FC193B6A6B46F2A280823A7B97716C1F32B16A6C24`；+23/-1 |
| `Animation/GGYGO_结构_动画与表现.canvas` | 343行 / 14638 bytes；20节点/17边；预检4节点位置尺寸与5边原ID/方向/语义相同 | `0AD6FD15FF06B7289053E0AFE17E8E2A7E685ABC018C80EA68FCBEC84C3AAFC0`；+81/-0 |

旧16节点/12边全部JSON值、正文、几何、颜色、ID、顺序、标签和StateFrame链逐项精确相等。新query节点为接口说明面板，不是新对象/执行器；没有Query→ASC/Task已接生产边。实际API为GameThread最内层Scope的登记/身份检查，失败Reset、即时副本外调后重查；无祖先回查/外部谓词/刷新/新状态。Returned不等于ASC整个Super完成、Completed不等于来源发布，查询可用/不可用均非Task/GA资源权限；Scope栈存储与Guard借用登记/GAS状态/Task资源所有权分开。

### 2. JSON、链接、容量与完整逆向

- 全文回读与限定修改预期相同；所有20节点/17边ID唯一、端点/side/标签/有限坐标正尺寸有效，矩形0重叠；新增4节点/5边与预检定义完整一致。
- 39处Wiki链接、18真实文件目标、5锚点引用通过；新增4链接复用Animation结构/AbilitySystem结构，两个新增Guard锚点引用指向实际新小节。旧MD18链接与旧图17链接文字原样保持。
- 新节点保守容量余量：montage_guard86px、montage_scope76px、montage_guard_query156px、montage_callers126px；尺寸420/440/550/490不变。估算使用CJK18px/Latin10.8px、正文30px、标题27/15px/38px、空行16px与56px内边距。
- 旧基线12节点同模型出现负余量：source147、capture7、frame42、base67、abp104、compat127、data12、combo_sources52、combo_montages52、combo_notify52、combo_slot_gate62、bh3_import44px。旧布局/正文是根明确保护范围，本步未修改；这些仅保守估算，不是原生渲染实测。全图字体/实际折行/连线路由/边标签/Obsidian原生视觉未验，不能标记全图容量或视觉通过。
- MD逆向删两新增类行/静态小节并还原Base行，原全文逐字相同，UTF8实际 `BD73B8536B0F55109BEDB37F5BB8F6B4539A181F3BC84A4F08AB9B4FB89E6102` /9744 bytes通过。
- 原图混合CRLF/LF保持；删除仅新增节点/边的插入文本，原完整JSON文本逐字恢复，实际 `DECA4D2EF83090ED24DD59621C9CBEA41C86E316BB0106C66BE53B1D99B35107` /10073 bytes通过。没有把解析值相等冒称原raw字节相等，两项分别实际验证。

### 3. 实际编辑方法、权限与根最新约束

MD/记录使用apply_patch。图在写前因标准重序列化会改变原混合换行而停止该方案；默认Shell原文追加被拒时图仍原DECA4D2E…。后来require_escalated受审查调用成功（exit0）写入该已授权Canvas的预检4节点5边，实际0AD6FD15…、无BOM，未改ACL/只读属性。

根后续明确人工追加必须apply_patch，已写则保留实际、不回滚/重写并交权限证据审查。本图在该指令到达前已写且完成冻结/逆向核对，随后未再写此路径；现如实交回实际方法，不能隐去Shell或记成apply_patch写图。后续人工编辑仅apply_patch；合规工具也拒绝时交回候选和阻塞，不改用Shell/Python替代或无限重试。根已允许未来仅机械换行差异单列验收，但本次实际未标准化原换行且raw逆向真实通过。

### 4. 限定保护、历史和未验边界

43本会话限定保护（含14资产配置、冻结Guard/Scope与既有Animation/Editor证据）哈希不变；不报告全源码稳定或全242重验。其它MD/图/曲线/流程/计划/Editor/Movementhelper/源码/资产/全局未写，没有UE/构建/Git/代理/资产/项目脚本运行，也未读取测试正文或第10批记录。

38构建/新运行时DLL/73正常Success及旧70含A5五叶保持仅统筹接受事实；37失败/未新DLL或运行保留。生产A5查询消费者、AnimClass资产迁移、严格P1/网络、完整播放/Task资源权限链及原生视觉未关闭，未新增动态验收。

V前两记录完整NavM2基线分别66534/78875 bytes是精确原前缀，只后接P登记；V仅顶部两段及C37追加，原整历史/失败及C读范围偏差保持。最终截去首次C37追加、恢复NavM2顶部两段，须复原Subleases `7A7AE170DFEE8B09603D93A66BD42BBCF39AAA81AA6E4F85A4030A5F3D7B9106` /66534 bytes、Validation `3AC26FC2E33A0487A00A9FC72762D466D86E4CC2D928BC376CD7B36EAC918A30` /78875 bytes，实际逆向/hash随四文件交回。

两个产物已先冻结；两记录完成最终全读/历史整文逆向/限定保护后，四文件全部冻结停写，交根审查实际编辑方式，不自动后续。
