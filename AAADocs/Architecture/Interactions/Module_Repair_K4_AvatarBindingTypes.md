# K4-I0 Avatar Binding 中性值类型

更新：2026-10-01。当前两文件已按统筹全文接受的 I0 草稿落地并完成静态核对，冻结交回。身份签发、Busy、绑定事务和消费者迁移均未实施；头未接入 TU，不声称编译或动态验证。

## 1. 目标、唯一写入者和精确范围

- 统筹已全文接受 I0 头草稿，授权 AbilitySystem 长期组长本人以 gpt-6.1-sol / xhigh 直接完成，不创建或唤醒代理。
- 唯一目标：落地已冻结的绑定/操作/上下文/请求/结果/通知值类型，供后续串行 ASC 接入；本步不执行任何绑定或签发身份。
- 精确写入文件：`Source/GGYGO/AbilitySystem/GGYGOAvatarBindingTypes.h`（新增）和本记录 `AAADocs/Architecture/Interactions/Module_Repair_K4_AvatarBindingTypes.md`（新增）。写前 Test-Path 均为 false，仅用 apply_patch。
- P1-I 纯移动数学与 A5-Q 阶段专项由其原组长独占，与本步文件互斥；全部源码作者明确冻结前不开构建/UE。本授权不授 I1 或共享 ASC h/cpp 写权。

## 2. 依赖、基线和执行顺序

只读依赖为根 AGENTS、路由、排程/台账、当前 ASC/GA、Host/PawnExtension 和 A5 已冻结阶段查询。头本身只包含 CoreTypes、TFunction、弱对象指针定义及 AActor/项目 ASC 前置声明，不 include GAS、Host、Character 或 Animation 实现。

### 2.1 共享源码基线

| 只读文件 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 16499 | E9AEB8AE04165D05DA8C6C18EB07B18F5C7DCB6D8A4AE0702B1D117845BC95E5 |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp | 49656 | 4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF |
| Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h | 17436 | BEE74DC34ED2C8636192894E964FB73779C17A50E43F4B810B21911CDF58DF51 |
| Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp | 27862 | 5BA07252DE4112F44ADCD142EE43F5E8470662A3AC2AC1A28C2E187C31BD117D |
| Source/GGYGO/Combatants/GGYGOCombatantState.h | 4370 | A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF |
| Source/GGYGO/Combatants/GGYGOCombatantState.cpp | 8950 | 6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84 |
| Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h | 8651 | 6190EB9134ECDE4735FC67C0CD564D87C3EEDAE9BC477E16ACA296368F7C96FD |
| Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp | 14285 | E76FC4182469B76C30BB0FAE980B5DB2A6D4BD7676BA30C7741F6D24B8BC4E10 |

同时在工具会话中保存了 245 个既有 Source 文件的 path/bytes/SHA256 基线。清单排除本步新头及其他合法并行工作线的精确三个新源：`Character/Data/GGYGOLocomotionEvaluation.h/.cpp`、`Animation/Tests/GGYGOMontagePlayGuardStageTest.cpp`；不把其他作者的授权写入计为本步保护失效。按 `rg --files Source | Sort-Object` 顺序，将规范化斜杠路径、bytes、大写 hash 以 `path|bytes|hash` 拼接，每行 LF、末行 LF、UTF-8 无 BOM，清单 SHA256 为 `8CCB679BCE37B5D5FFBEC8C56D9DE9CCF16D71CE9F26A6DD942370FD3DD37981`。

### 2.2 只读治理依赖基线

| 文件 | Bytes | SHA256 |
| --- | ---: | --- |
| AAADocs/Coordination/Module_Repair_Parallel_Schedule.md | 77059 | 7E99F13F2B3E52B402F1B44D9681D2DA6E62E1C57A5F084C19FA39ABEF432510 |
| AAADocs/Coordination/Module_Audit_Repair_Ledger.md | 57623 | 95E5321DEF02686ED789F3F2DE2DA7F6D2B6A6BA2B9E69031FD47346D980A0B5 |
| AAADocs/Modules/AbilitySystem/Module_Repair_07E2_B0_Diagnostic.md | 11961 | 3FA72B5BAD40E65A2A7DFF6D420A6EA39EC30FEB38F22EE37A1115E931115AAB |
| AAADocs/Coordination/Module_Conversation_Routing.md | 5120 | FD460226094928EC3E444A87CBCC55A7B1D7E2915C0F79CCA38BDF0C006C8E04 |
| AGENTS.md | 10850 | 95DBB36A46ACBBB686C72D79B50ADB8D02F45B27ABEBB489F024E4723097F0D4 |

全局排程/台账仍属统筹，以上是本步读取时基线，不限制统筹自己的治理更新。

顺序：本记录先登记预检与基线 → 新头精确落地已接受草稿 → 全文/枚举/默认值/值比较/依赖静态核对 → 既有保护比对 → 补实际头 hash 和证据 → 两文件明确冻结交回。记录自身最终 hash 在最后写入后计算并随交回消息提供，避免自引用 hash。

## 3. 验收断言

- 五类枚举、六个 struct 的字段/默认值和 inline 值比较与统筹已接受草稿逐字一致；无 UCLASS/USTRUCT、UFUNCTION、generated include、counter/map/clock、调度器或执行器。
- Binding 与 Operation 为不同类型；同 Issuer 使用 HasSameIndexAndSerialNumber，Serial0 和显式空 Issuer 不匹配；失效 Issuer 仍可比较保留的弱身份，不能当成存活或当前权属证明。
- Context 区分 Binding 和 LastActorInfoWrite，且两者须同 Issuer。Init/Clear 新 Binding、Refresh 仅新 LastWrite，单一不复用序号源及耗尽拒绝都只是未来 ASC 契约，本步没有序号分配实现。
- 默认请求 Kind=Invalid、ClearMode=None、空谓词；默认结果 Rejected/InvalidRequest。缺失谓词由未来 ASC 在 native 前明确拒绝，不自动成功。
- IsRequestContextCurrent 精确为 TFunction<bool()>，只同步借用、不存入 ASC 长期状态或排队；闭包不延长引用捕获的生命周期，调用者以存活至同步调用返回的栈值提供请求。true 不证明权威，未来 ASC 每次外调后重检原操作、上下文、真实字段和生命周期。
- Init 的显式 null Avatar 是选择的 owner-only 模式；已失效但非显式空的弱 Avatar 必须由未来 ASC 明确拒绝，不能解引用为 null 后偷换成该正常模式。
- 结果/notice 是副本。bCommitted 仅记录本操作 Init/Clear/Refresh 的提交历史，通知中后继可令最终结果 Stale；Cancel/Cue 返回不证明原生延期 GA 已完成。
- 不接任何 TU/ASC/调用方，不编译/运行；不能把“类型文件已落地”写成“已编译”“身份签发已实现”或“绑定根因已关闭”。

## 4. 非目标、架构核对和停止点

- 共享 ASC、Host、Extension、消费者、Task、GA 终止、旧测试/记录、B0、Obsidian、资产、Git 均冻结。用户另批准的同实例 End 返回前 Busy/返回后带来源通知不进入 I0。
- 新类型只比较值身份，不持 ActorInfo、播放实例、权威 Avatar、原生状态或业务规则；没有新增循环依赖、第二播放代际或执行链。序号签发/失效、Busy、原生入口与通知生命周期仍等待 I1 以后独立租约。
- 已只读核对 Obsidian 的 `计划蓝图.md` 和 AbilitySystem `结构.md`；本步未改变既有运行流程或接线，Obsidian 由统筹冻结，未写笔记/Canvas。后续集成及类型清单/流程同步须按统筹文档阶段办理，不能写成已运行。
- 需要第三文件、改变已接受草稿或扩大执行范围时立即停止交回。两文件静态冻结后停止写入，不自动进入 I1、测试、构建、UE 或笔记阶段。

## 5. 实际证据

- 先以 apply_patch 新建本记录登记精确范围/基线/验收/停止点，再以 apply_patch 新建类型头；没有写入第三文件。头全文与工具会话保留的已接受草稿逐字符一致，224行/6351 bytes/SHA256 `2E2ACF92C2820480421C6C78AAA0F8348F6BCCF0D8474595A342BD61677343FF`。
- 静态读回为五类 enum class、六个 struct、约定四个 Core include 和两个前置声明。去注释后无 UCLASS/USTRUCT/UFUNCTION/GENERATED_BODY、容器/计时器或执行器声明；字段、默认值、同 Issuer 弱身份比较与 Serial0 不匹配均与已接受文本一致。
- 头为 UTF-8 无 BOM、LF、末行 LF、无行尾空白。对 Source 搜索该新头名称并排除新头自身，无引用命中（rg exit1）；没有接入 TU/ASC/调用方，也未新增运行状态。
- 245个既有 Source 文件逐项 path/bytes/hash 与本步基线完全一致；受控排除项保持为两条合法并行线的精确三个新源及本步新头。清单 SHA256 仍为 `8CCB679BCE37B5D5FFBEC8C56D9DE9CCF16D71CE9F26A6DD942370FD3DD37981`；包括共享 ASC、GA、Host、Extension、冻结 A5 查询及旧 B0 测试源码均未变。
- B0独立记录、路由和AGENTS hash保持。统筹独占的排程/台账在读取期间有并行治理更新，未冒称保持旧hash；排程复核仍明确 K4-I0 仅本步两文件、I1/ASC不授权。本会话没有写这两份全局记录。
- 已做职责核对：值类型不签发身份、不决定 Avatar、不持播放代际，也不执行谓词或原生调用。显式null与失效弱Avatar的区分、缺失谓词拒绝、外调后重检和End完成通知仍为未来执行方必须验证的契约，不因本头注释存在就计作实现。
- 未运行UE、构建、Git、代理或动态测试，未改资产/Obsidian/旧记录。静态验收只关闭I0定义，不能关闭绑定/播放/终止根因。头和记录在本轮最终格式/hash读回后均明确冻结；记录最终hash只随交回消息提供，不再自行追加。
