# 07E2-B0-Origin：单次 Can 评估与输入失败来源

更新：2026-10-02。输入 Try→final Can→final Notify已实现、冻结并通过Gate41完整Editor与原34严格诊断，旧测试一字不改。下文保留生产及B0-Doc历史，实际门禁见末节；完整E2、K4/K3及网络未完成。

## 原子目标与范围

- 唯一作者为 AbilitySystem 长期组长 gpt-6.1-sol/xhigh，直接 apply_patch；不创建代理。
- 精确文件：Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h/.cpp、Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp、本记录（实施时位于 AAADocs 根目录；冻结后由统筹迁入 AAADocs/Modules/AbilitySystem/Module_Repair_07E2_B0_EvaluationOrigin.md，写前不存在）。
- ASC 唯一拥有来源序号、同步评估栈、输入一次认领许可和单个待消费结果。GA/CDO 不存来源状态；弱对象/短期快照不成为第二 Avatar 或物理输入权威。
- 不含 E2 完整输入身份/held 聚合、网络协议、Busy、K4/K3、测试/其它记录/Obsidian/资产/UE/构建/Git。

## 基线与只读依据

| 文件 | Bytes | SHA256 |
| --- | ---: | --- |
| ASC.h | 24350 | 51D3EEA90F69A87424425C4373872AFD839FEFAD48EE73EAFAA4C0A51FC69275 |
| ASC.cpp | 71158 | 5225429C07A0D9E020B1D2E7D3682A1C12597496BAA1DC873D2BCDC7C3DCD794 |
| GA.cpp | 28341 | D166E350129E7356DE3528C57DB65CE3D16659FF1F7244EC15427D27AED5B4CD |

- 保存三源完整原文，保护其它247个 Source 清单项、G1/G2/B0/I0/I1/I2a记录和AGENTS，另保护116个 uasset/umap。
- 普通输入 Try 无 TriggerEvent；Can 前只读 locality/role/Spec 检查已核对，Source/Plugins 无 locality 查询覆写，原生实现没有业务回调。Can false 后原生紧接 Notify；Queued tag 已存在，不进入空 tags 的默认 tag 初始化支路。若出现未证明 Can 前外调，停止并交证据，不扩架构。

## 必保协议与断言

- 实际 AbilityInputTagPressed 的 Tag 随 pressed handle 缓存本次消费快照；InitialPress 明确使用既有 NoDeadline 哨兵，由 Hero 建有限截止。FiniteRetry 保留原 Tag/deadline；禁止从失败时任意 SpecTag 推断来源。多 Tag 取本次第一实际事件，未实现完整 E2 聚合。
- 正式输入 Try 武装一次许可，首层 Can 在 Super/BP/Cost/Additional 前认领；每层独立身份和结果，内层 raw 没有外层来源。CanByHandle 使用 QueryOnly，查询不产生可发布输入来源。
- Can 在返回前封闭结果；Notify 在首个外调前精确取走并一次消费，失败原因先复制以隔离原生共享容器的重入修改。无来源/已消费/查询/过期/错对象结果不发 retry，原 GAS 委托及 GA Native→Script/既有 RPC 保留。
- 新评估/查询使旧待消费证明失效；输入调用结束清理自己的未消费结果，销毁/ClearInput/Avatar变化使来源失效。精确清理不恢复已认领许可、不清后继；无定时器或历史表。
- 旧34整个测试保持：真实首按 notice1/NoDeadline，control retry1/原有限截止，nested 内层retry0/外层retry1；内外原生失败和GA反馈各1、同Handle/Primary及原截止不变。仍不得用编译代替专项结论。

## 验收与停止点

- 全文差异仅批准的来源桥接点/私有状态与助手，原 core 检查顺序及 G1 Additional 保持；替换新增/修改块的内存逆向精确恢复三源基线，K4/组/播放/其它 GA 函数和保护项保持。
- 检查输出复位、默认无来源、每层栈/序号无回绕、完整 RAII 退出/精确消费、查询与失败回调重入、首按及有限 retry 分支；不运行编译/测试。
- Obsidian 来源流程/接口状态由后续互斥文档阶段同步，本记录交接需求，不冒称已同步。
- 四文件静态证据及 hash 交回后明确冻结；不续其它文件或运行 UE/构建/Git。

## 实际证据

- 2026-10-02：生产来源桥接完成，三源全文与登记修改块逐一吻合；在内存移除助手并逆向替换修改块后，三源逐字恢复上表基线。原 core 顺序、G1 Additional、K4、组、播放及其它 GA 函数不变。三源 UTF-8 无 BOM、LF、末尾换行、无行尾空白。
- 实际差异：ASC 私有来源类型/RAII/序号与评估栈；CanByHandle 查询隔离；实际 press Tag 快照；每次原生 Try 的短作用域；ClearInput 失效；Notify 精确消费；文件末尾来源助手。GA.cpp 仅包裹原 final Can 主体，完成结果后返回。
- 首层认领先于原 core 的全部外调；原生 Can 前拒绝时，Notify 也先耗尽匹配输入许可，回调不能重用。失败 tags 在首个外调前复制；取证后才调用 Super，精确对象/Handle/父层/输入序号及当前 Spec、Owner、Avatar、Revision 校验通过后才发布。Raw/QueryOnly 无可发布输入证明，析构不恢复许可或旧结果。
- 首按保留实际 Tag 与 NoDeadline=-1；有限 retry 逐字段沿用原请求。本轮没有增加 SpecTag 猜测、替代成功、第二状态机、计时器、帧调度器或网络协议。press 来源缓存仅为本次事件派生数据；完整多 Tag/held 聚合仍属后续 E2。
- 最后保护检查：116 个资产未变，原其它247个 Source 中246项未变；Kevin Builder 默认路径、AGENTS及六份迁移记录的变化已由统筹核对为并行授权更新，新增 MovementInputTypes.h 属独立 Input 租约。本组未写入这些文件，不据此声称全工作区无差异。
- 旧34两份测试保持原文，本组未修改或运行测试。本轮未构建、未运行 UE、未执行 Git；编译与旧34完整专项由统筹统一门禁确认，不能将本静态结论记为动态通过。

| 冻结源码 | Bytes | SHA256 |
| --- | ---: | --- |
| ASC.h | 27946 | 9A6F21ECE2CAB34FB244EFAD89A72F21C58104B350AFB1DCB164FC33CAA105F0 |
| ASC.cpp | 82174 | F7F9059A92CD505A72A945DB4ED64B0CB0516D406A6F01784756B778D0AAB9DF |
| GA.cpp | 28746 | 5210AEC84711DCE4C85ECD6DE0E767F28DD0C6A5C6A3F4D5D42B9C100450DAE8 |

- 停止点：生产四文件已冻结，统筹核对三源与原严格测试哈希后静态接受，并迁移本记录到 Modules/AbilitySystem（移位时内容哈希保持）。尚未编译或严格复测，原失败仍开放。Obsidian 局部结构文档及主结构/流程图已由下述 B0-Doc 阶段同步；根全局入口仍由统筹维护。E2 完整输入身份/held 聚合、网络、Busy、K4/K3不在生产来源实现范围。

以上为生产冻结时点的边界；随后Gate41结果见末节，不能将历史未复测当作当前结论。

## B0-Doc：局部结构与流程同步（2026-10-02）

统筹接受零写入预检后，授权 AbilitySystem 长期组长直接完成以下四文件；没有代理、新记录或源码写入。

- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/AbilitySystem/结构.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/AbilitySystem/GGYGO_结构_AbilitySystem.canvas`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/AbilitySystem/GGYGO_流程_AbilitySystem.canvas`
- `F:/ue_project/GGYGO/AAADocs/Modules/AbilitySystem/Module_Repair_07E2_B0_EvaluationOrigin.md`

唯一结果：局部笔记接通冻结源码的 final Can → 原核心检查 → `CanActivateAbilityAdditional` → 本层结果封闭，以及 final Notify 先消费来源再外调。ASC 独占来源状态，GA/CDO 无来源状态；InitialPress 使用真实 press Tag/明确 -1，Hero 对照自己的已记录请求取得有限截止；FiniteRetry 保留原 Tag/截止。QueryOnly 与嵌套 raw 无输入重试证明，原 GAS/GA Native→Script 反馈及客户端原路由保留。ClearInput/revision、弱对象、Owner/Avatar 与使用时有效性检查的边界可见，没有新增 Core 接口或第二意图权威。

| 图 | 实际差异与保留 |
| --- | --- |
| 主结构 | 仍为10节点/9边，节点及边 ID 全部保留，边未改。仅 nav/asc/ga/contract 正文更新；asc 高390→540、ga 高330→490、contract 高320→390。为容纳正文沿原两列局部下移 set y730→920、attr y830→1070、effect y1040→1210、contract y1390→1570；set/attr/effect 正文保持。原 ga/attr 20px重叠消除，无全图重排或助手节点。 |
| 主流程 | 仍为8节点/7边，节点及边 ID 全部保留。仅 nav/request/check/fail 正文更新；request 高230→370、check 高230→400，fail y756→700且高230→490。仅 e2/e4/e7 标签更新，实际组释放回流为 Hero::HandleAbilityGroupFreed → QueueAbilityInputRetry。装配、成功激活、结束及伤害节点保持。 |

保存后已重读 MD 与两图，全文符合登记替换；结构.md 的玩家普攻及第12批历史尾段逐字保持。两图 JSON 可解析、ID唯一/保留、端点有效、边标签非空且符合实际调用；27项文件内去重的 wikilink 目标均唯一解析到既有文件，没有新增目标。全部节点矩形无重叠，变更节点按宽度估算正文高度均在容量内；这是静态容量/布局检查，没有 Obsidian 屏幕渲染证明。

三生产源最终 SHA 与生产冻结表一致，旧严格34两份测试 SHA 仍为 `1BC9B5CFF1EE396649D062EA1945FE453E84DDA50B60D9D3BE5A1E4D328B9A4B` / `69016178DE25929D03947667BCCBF639B871B93406F008B6608825628A99D7CD`。本图文阶段未构建、未运行测试/UE、未执行 Git；静态笔记同步不能关闭原严格失败。完整 E2 held/身份、K4 执行/通知、Task 来源迁移、Busy 门禁、网络及资产验收仍未完成。Input、其它子图、根全局笔记与进度入口均不在本租约，后两者由统筹唯一维护。

## Gate41：统筹实际门禁（2026-10-02）

- 全部源码明确冻结后，完整GGYGOEditor构建Succeeded／exit0，10 actions／92.91秒，UBA82.37秒、UHT8.0478291秒并写4个generated文件；运行时及Editor DLL均链接。构建日志：`Saved/Logs/ModuleRepairBuildGate_20261002_41.log`。
- 新DLL普通报告`Saved/AutomationReports/ModuleRepairGate_20261002_41/index.json`：2026.10.01-18.14.29 UTC，73 Success，其它计数0，0.9159062504768372秒，SHA256 `B151070C7E4F7E659AB8CA9E55B18BA4CB2C257FCE31C555CECB5A392BCFDD70`；原73路径保持，全部叶errors/warnings0。
- 原B0显式诊断`Saved/AutomationReports/ModuleRepair07E2_B0_Origin_20261002_41/index.json`：2026.10.01-18.15.45 UTC，1 Success，其它计数0，0.015511199831962585秒，SHA256 `D39638FC2D67C64F9BDABA90AFB30B3C6DD861BA430C162E7809A984AEBDDE59`。实际Info：handle=3、rawCalls=1、innerNative=1、outerNative=1、innerRetry=0、outerRetry=1、originalDeadline=0.34999999403953552；旧完整首按／有限retry／嵌套断言和GA反馈全部通过，没有降低或删除断言。
- 252源和14保护文件在构建及两次UE运行前后hash保持，UE退出／进程0，未保存资产。CLI使用了不合适的绝对`-log=`形式，预期运行日志没有生成；结论以结构化报告及构建日志为据，不声称全日志零诊断，后续使用正确的`-AbsLog=`。
- 原34内层来源借用失败已关闭；历史失败报告保留。R0、完整Input身份及Montage严格红未复测，完整E2 held/身份、K4/Task/Busy、网络与资产验收不由本结果关闭。统筹仅同步本记录及B0局部状态，生产源保持冻结，不执行Git。

停止点：四文件完成静态核对后交回最终哈希并冻结，不续源码、其它图文或动态门禁。

## 07E2-Runtime：ASC 原输入请求与聚合消费（2026-10-03）

统筹已接受有限预检并冻结Receive／End(Released或Invalidated)／Queue及精确原请求通知，基线Saved/ValidationRecords/ASCInputRequestRuntime_LeaseBefore.json。本步唯一作者AbilitySystem长期组长，gpt-6.1-sol/xhigh直接实施，无子代理。只有以下四文件写权；旧Hero和两诊断适配另租约，全部消费方冻结前不统一构建。本步无UE/Build/Git/资产/外部笔记/全局写权。

| 原子步骤 | 精确文件 | 唯一结果、验收和停止点 |
| --- | --- | --- |
| 共享值/API与ASC输入生命周期 | Source/GGYGO/AbilitySystem/GGYGOAbilityInputRequestTypes.h；GGYGOAbilitySystemComponent.h/.cpp；本记录 | 完整空Previous才发ID，固定原Tag/deadline/Owner/Avatar/World及首次Spec集合；按ID接收、Released、Invalidated及证明过的Queued入队。原有序输入缓存由既有Process唯一消费，Spec held OR、首按/末真实释放；最后Invalidated清派生InputPressed且无伪释放。有限整文/逆向/接口及清理核对后四hash冻结交回；第五文件、共享契约无法表达或需要网络/新政策即停。 |

先本节登记→普通返回值及API→同一ASC请求权威/有序边沿/现有帧消费/B0载荷→有限源码核对→证据与四hash冻结。四文件属于同一输入请求生命周期，不跨独立状态所有权。源码接口冻结后Hero消费→既有诊断签名/契约适配→统筹统一编译与必要UE冒烟；不新增严格矩阵/夹具。

请求身份复用07E2原ASC弱身份/revision/serial；运行记录唯一在ASC，Hero后续只持原ID/原deadline。deadline仅retry窗口，不定时松开held。Released不延长原截止、保留原有限tap；Invalidated只撤原请求关联，不依赖Ready或未过期截止、不增加全局revision、不清后继、不伪造Released。已记录真实边沿与其来源授权分开，边沿保持真实先后，退休不能伪造新边沿。全Clear仍无外调的全局退休，清全部原请求/派生标记/待消费证明，不增加通知/自动重试/恢复。

B0 final Can/Notify、一次认领和首个外调前消费机制保留；真实Try前冻结精确请求载荷，Super后逐原来源重验，Raw/QueryOnly无来源；不回扫后授予Spec，不从Tag/截止猜ID。旧Tag入口移除，旧调用方须显式迁移，不新增兼容发行或Tag到身份映射。AvatarBinding/Try/Publish/C1a/C1b/Guard接口和函数体全部冻结只读，GA/Task/Montage、Hero/Input/CMC/诊断、Host/Extension只读。

写前三源码SHA256分别8E795C5A85A546A8D489DE66D7F0B5A3C89B0A31F479ED286DE3F611D4134DAE、7A1FEDD04CBBA92C7B931238B0EDF4B1073AE3447FAF34F2C5BC0A02BD22EEA6、57CD3A4AE6282BDFE3246C9076AE3C0BFEC36031517F1D99F9D4C88E55D6EECA；本记录写前6C96F5B52F1DB093BE991615D43AF9F0EA48D1510A6C63C0D1090C0BFB851809。历史门禁保留，不能以旧DLL证明本输入迁移。Obsidian及全局同步由统筹后续互斥阶段处理，本组仅交回实际边界。

### 本步实际证据

已实现并有限核对，四文件冻结交回。本步关闭共享输入契约的源码阶段，Hero/两诊断消费、编译及UE冒烟尚未完成，不称完整07E2闭合。

| 冻结源码 | Bytes | SHA256 |
| --- | ---: | --- |
| GGYGOAbilityInputRequestTypes.h | 2477 | E13DD23557629B97C1103BE00B7AFBE53F11B4F78D9ED26B086FC0AF354D9DD8 |
| GGYGOAbilitySystemComponent.h | 34896 | A8736E9A28AF40DFFC3F73004782D79F1A19529F45FBD307CA44530C1F9FFF4B |
| GGYGOAbilitySystemComponent.cpp | 136142 | D3DE2BF2C24840DAE9C57907F4E7A4897623E917ACB591E573E8AF44B78E620F |

共享值头原50行两值类型保持精确前缀，只追加Outcome/Reason/EndKind及默认Rejected/InvalidRequest/空Identity的结果。三个API及OneParam原请求委托与批准签名一致。Accepted/AlreadyApplied仅证明输入缓存接收/同请求重复操作；Rejected/Stale身份空，带明确Reason及ASC/原来源/Tag/revision/serial/deadline诊断。重复Invalidated若原行已退役返回Stale/UnknownRequest且无作用，不保留无限墓碑或替代成功。

Receive只有serial0/revision0/原weak显式空的完整Previous才发行ID，发号器独立且全ASC寿命不重置、不回绕。第一次固定Tag/deadline及原Owner/Avatar/World和当时精确匹配的Spec集合；非空Previous只能验证原行，不能重新发行、刷新截止或吸纳后授予Spec。零窗口可接真实首按，retry要求Now严格小于原截止；已held的原行过期仍可重复验证，只有真实Released/Invalidated结束held。

ASC私有请求表是唯一请求/held权威；原InputHeldSpecHandles改为私有派生缓存，不接受外部改写。按原请求serial稳定重建Spec OR，保持原首次Spec次序；Pressed/Released两分裂句柄缓存及Tag press来源缓存移除，改为同一Process消费的有序聚合事实。第二来源仅加入尚未消费的聚合首按载荷、不再造Generic Pressed；最后真实release才缓存Released。边沿调用的原AbilitySpecInputPressed/Released函数体一字不改。

End Released不依赖未过期截止，退原held而保留原有限tap；Invalidated不要求旧Ready/当前ActorInfo/未过期窗口，按原ASC/revision/serial只退原行、自己的待消费press贡献和retry关联。仍有其它有效held来源则保持Spec标记；最后来源Invalidated明确清Spec.InputPressed，不创建Released。已经记录的真实Release历史继续按原Actor/World/revision验证和排序消费，不能把资源退休改造成真实松开。Released行只保留到原deadline及必要的在途/未消费真实边沿结束，held不因deadline退休。

Process实际外调前冻结首按/held/retry的ID和原Spec关系，retry只看真实Queued关联的原Spec子集，不扫ActivatableAbilities补新Spec。每Spec本批最多一次Try；真实再次按下若碰到已消费次数且Spec已不活跃，将本Spec后续原边沿按顺序留回原缓存，并排在回调新增事实之前，不丢新按下、不新建Tick/Timer/dispatcher。回调创建的后继来源/边沿不由旧批覆写；整体Clear、原Actor/World变化或对象失效结束旧消费。首按只向已经活跃的Spec送Generic Pressed，不对刚由同一事件激活的实例重复送按下；retry不写held/InputPressed/Generic事件。

Queued许可按原请求与具体原Spec记录；Queue完整核对ID/Tag/原截止、上下文、实际Spec及B0关联，按ID去重，WhileInputActive还要求该原来源held。实际Try前消费旧Queued许可，防止没有新证明的后续尝试继续复用；B0私有原Try载荷承接这份已经消费的许可。只有真实final Can→final Notify取证后的Queued失败才重新登记原Spec许可并发布精确Request。首个外调前一次消费、final入口、评估/查询栈及不恢复许可的RAII均保留；Super返回后逐原来源重验，某ID退休不借同Tag新ID或清其它原ID。成功只清参与本Try的原ID重试关联。Raw/QueryOnly以及held普通持续尝试没有可发布输入证明；原失败Native→Script/客户端反馈路由不传输入ID、不新增网络协议。

全Clear仍是无业务外调的全局退休：清原请求/有序边沿/retry/派生held、原输入许可与待消费结果，并清所涉及Spec的派生InputPressed；不发送Released、广播新通知、恢复来源或自动重试。revision耗尽明确诊断且禁止新接收，消费也不继续旧MAX快照；身份不回绕。AvatarBinding/Try/Publish/C1a/C1b/Guard及原调用全Clear的边界没有改动。

有限静态通过：三源码全文等于登记替换构造的预期；逆向新类型/输入声明/状态和cpp输入块后完整恢复写前三源，证明所有未授权Avatar/Guard/组/其它源码块完整保留。旧07E2值头保持原完整前缀；GA两源、Hero两源、B0原两测试逐项Bytes/SHA保持既有冻结值。严格UTF-8、无BOM、仅LF及末尾LF通过。原Tag入口/Tag->ID映射及旧缓存已移除；deadline只在Receive赋原值，没有Min合并或续期。原生Core的ScopeExit语法、TArray移动Append、TMap GetKeys及Weak构造已只读核对，不把这一点冒称编译。

本步未UE/Build/Git/资产/外部笔记/全局写入，未新增或修改测试/夹具。旧Hero仍调用已移除的Tag签名，两诊断仍订阅双参数委托，当前源码链尚不具备统一编译条件；必须依后继独占租约完成调用方适配，再统一构建与必要冒烟。旧NoDeadline断言须按新原请求有限截止契约适配，来源/嵌套raw/旧请求污染断言及历史失败证据保留，不能靠取消失败场景关闭问题。Obsidian需同步ASC原ID、固定Spec/World、OR与边沿、B0精确数组载荷及Hero不再按Tag找近期截止的待迁移状态，由统筹另阶段唯一写入。正式Hero/Host整链、资产/网络、原R0/Montage等边界继续开放。记录最终Bytes/SHA在交回外部报告，不自指。

## 07E2-Edge：Pressed 原边沿来源修正（2026-10-03）

统筹接受有限根因预检并授权两文件，基线Saved/ValidationRecords/ASCPressedEdgeSourceCorrection_LeaseBefore.json。唯一作者AbilitySystem长期组长直接执行，无子代理。只写Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp的ProcessAbilityInput方法体与本既有记录；公共头/类型、其它ASC函数、Hero/诊断冻结，Health与GF是独立租约，不要求其整文件保持。无UE/Build/Git/资产/Obsidian/全局写权，不新增测试/夹具/严格矩阵。

| 原子步骤 | 唯一结果与依赖 | 验收断言、非目标和停止点 |
| --- | --- | --- |
| Process原边沿来源隔离＋本记录 | 原有序Edges和各Edge.Sources已冻结；先登记→首次外调前按Edge索引冻结原请求副本→按当前Edge消费→有限范围/逆向核对→两hash冻结交回 | Press A→Release A→Press B的首段只取A，B只能由后续原Edge消费；同一Edge多来源全部保留。每Spec本批一次Try、真实后续边沿延后保持。公共API、其它函数/消费者不改；第三文件、新政策或共享契约不足立即停交回。 |

根因属于实现错误：旧InitialSources按Spec Handle合并整个Edges数组，把尚未消费的后续Pressed来源混入第一段Try。OnInputTriggered可将已Released A和未来B一起送B0；WhileInputActive可排除A却借未来held B激活；成功清理也对混入B执行许可/pending retry清理（当时是否非空另取决于真实已有许可）。同一聚合Edge.Sources的并行来源OR是合法集合，跨独立边沿合并不是。上一轮有限静态通过仅证明登记修改/保护范围，没有发现此语义错误，不能据此前静态关闭这一消费契约。

本修正只收窄首按载荷到实际当前边沿，不改变身份发行、真实Release/Invalidated、Queued证明及成功清理规则。首按/held/retry关系仍在第一次实际外调前冻结；后续回调仍逐原ID重验，不能把实时后继收养进旧载荷。Hero原来源停止点、诊断签名迁移、编译与必要冒烟仍另租约；Obsidian/全局实际状态由统筹接续同步。

### 本修正实际证据

已完成本租约实现与有限静态核对，交回两文件冻结。源码仅ProcessAbilityInput方法体变化：InitialSourcesByEdge按原Edges索引分配；首次外调前从该Edge.Sources冻结Request副本；消费该Edge时使用同索引载荷，取消跨Edge的Spec合并。空载荷仍由既有TryOnce拒绝，不触发替代来源。

| 有限核对 | 实际结果与边界 |
| --- | --- |
| 精确写入范围 | CPP全文等于授权方法替换的预期文本；逆向还原等于租约基线，签名、方法前后及其它ASC函数完全一致。本记录保留全部原文，仅追加预检与本节证据。 |
| 原边沿来源 | Press A→Release A→Press B的首段载荷只冻结A；OnInputTriggered重验不会纳入B，WhileInputActive若A已释放则旧Try无有效来源，也不会借B；B由自身后续Edge决定。A成功/Queued证明只接收A的CurrentSources，不会据本首段关联或清理未来B。此为源码核对结论，严格原场景尚未动态运行。 |
| 同Edge并行来源 | 仍逐该Edge.Sources冻结所有原ID，仅按原Identity去重；后续仍逐原ID重验，合法多来源OR保持。 |
| 既有执行约束 | CanContinue/HasSupersedingInput、Attempted、本批一次Try、DeferredHandles/DeferredEdges与ON_SCOPE_EXIT、Queued许可消费、B0 Origin、成功清理、retry/held尾段均保持原文；无第二调度器、权威状态或公共接口。 |
| 保护与编码 | ASC公共头与InputRequestTypes字节数/哈希和基线一致；两写入文件及保护文件严格UTF-8无BOM、LF、末尾换行。Health/GF独立写入不纳入整文件哈希断言。 |

源码实际交回：Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp，136232 bytes，SHA256 B839A9752DD41D947AF2E134946D168A670EFE96A3AF871DF63AE2544A0B903D。本记录实际最终bytes/hash在交回消息列示，避免自引用哈希。

本修正未编译/UHT/运行，未新增测试或夹具；源码静态契约已修正，严格复现与必要UE冒烟仍未验收。Hero原来源停止点、两处诊断签名迁移、统一编译、运行验收及Obsidian/全局实施状态同步仍由统筹按后续租约接续，不能标记整个07E2完成。
