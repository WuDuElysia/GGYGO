# 移动输入来源契约

更新：2026-10-16。本文维护当前源码可见的稳定接口、所有权、清理与未闭合边界；执行窗口和验证进度以[当前排程](../../Coordination/Module_Repair_Parallel_Schedule.md)为准。本次仅整理文档，不新增实现、构建或运行结论。

D7～B2 等旧预检、租约、门禁、失败和分批交回已整份按原字节保全至[历史原文](Module_Repair_MovementInput_Contract_History_20261016.md)。历史中的“未来／未接入／未编译／已完成”均指对应批次，不作为当前授权或后继验收结论；旧锚点见[历史导航](#历史导航)。

## 状态与身份唯一归属

| 所有者 | 事实与责任 | 不同寿命的边界 |
| --- | --- | --- |
| PlayerInput Source | 原生可观察的设备／键 raw 事实、连续性缺口及 Movement 参与／释放义务；发行 SessionSerial、输入 RequestSerial、EventSerial | raw 与释放义务分离；会话退休不冒充真实释放，也不清掉尚欠释放的来源 |
| Input OriginResource／原生 Host | 原 LocalPlayer 生命周期、Controller 原生创建票据和精确 PostInit 登记；一次 Cold 资格、认领及消费 | Cold／Rearm 是初始资格，不是 Held、Neutral、Ready 或移动准入 |
| Hero | 原 Pawn／Source／Action／InputComponent／Subsystem／CMC 的装配、绑定、IMC 注册及订阅资源；原事实直交 CMC，原值按 camera-relative 投影 | 不发行输入／执行请求，不持有第二份物理 Held 或 FAILED 状态，不建立另一帧调度 |
| CMC | 消费绑定、输入事实记录、owner 同步、执行 RequestSerial、准入／FAILED、SavedMove／校正／重放及 qualified intent | 输入 Held 与执行已准入分开；Recorded 不表示移动成功 |
| GA／公共 Task | 作者点许可、原激活／段／Task／Montage／MotionHandle 的生命周期及合法终止 | 消费原 CMC qualified intent，不以输入值或能力结束布尔量替代原资源事实 |

[来源值类型](../../../Source/GGYGO/Input/GGYGOMovementInputTypes.h)只携带中性身份与事实，不持有运行容器或执行状态。Session 是原 Producer 弱身份＋SessionSerial；Request 再加输入 RequestSerial；Binding 是原 Consumer 弱身份＋ConsumerBindingSerial＋原 SourceSession。EventSerial 保持发行顺序，不能用相等 World time 替代。

同一发行者的序号不因释放、重绑或换 Hero 而重置或回绕，0 表示未分配；耗尽明确拒绝。失效弱对象仍按 index／serial 保留原身份，不能把两个 Get()==nullptr 当同一资源。身份相等也不证明对象或请求当前有效。

## 当前跨模块接口

当前声明见 [PlayerInput](../../../Source/GGYGO/Input/GGYGOPlayerInput.h)、[OriginResource](../../../Source/GGYGO/Input/GGYGOMovementInputOriginResource.h)和 [CMC](../../../Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h)，当前装配调用见 [Hero](../../../Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp)。

| 真实入口 | 输入 → 作用 → 输出／副作用 |
| --- | --- |
| Source.BeginMovementInputSession | 原 Pawn／InputComponent／Axis2D MoveAction → 核原 Host／路线、捕实际映射、认领 Cold 或选择原 Rearm → 准备原 Session；此时未安装 receiver |
| CMC.BindMovementInputSession | 原 Session、ExpectedConsumerBindingSerial → 核并发行本 CMC 的原消费绑定 → OutBinding／错误；不能替旧调用认领新绑定 |
| Source.AttachMovementInputReceiver | 原 Session／Binding／双参数事实委托 → 安装唯一原 receiver，再同步发布 SessionOpened 和已有来源事实 → 成功或明确清理失败 |
| Source.QueryMovementInputRequest | 原 Session → 核当前路线、原 receiver、参与源证明及已发行请求 → Held／NotHeld／AwaitingPhysicalProof／Unavailable；只有 Held 输出原非零 Request |
| Source.GetMovementInputRequest | 同一原查询的 bool 兼容入口 → 仅 Held 为 true；不能把其 false 一律解释为 Released |
| CMC.ConsumeMovementInputFact | 原 Binding＋Fact → 核来源、Mode／Proof、事件顺序及请求生命周期 → Recorded／Duplicate／Stale／Rejected；执行与失败另判 |
| CMC.TryAdmitInitialMovementInputRequest | 原 owner 同步 observer／Ready notice、Binding、Request → 原 CMC 首请求准入 → 保留真实准入或失败结果，不造新输入 |
| CMC.QueryQualifiedMovementIntent | 原 owner scope → 核原来源、同请求、owner 同步及执行准入 → Qualified／NotHeld／AwaitingPhysicalProof／WaitingForAdmission／ExecutionFailed／Unavailable |
| Source.EndMovementInputSession／CMC.InvalidateMovementInputSession | 原 Session／Binding 和原因 → 精确退役自己的原资源并发布失效 → 幂等清理，不伪造物理 Released |

Source 的 OutError 为可定位诊断，准备／查询失败清对应输出。七个 FactKind 值中 Invalid 为未赋值，其余为 SessionOpened、NeutralConfirmed、RequestStarted、RequestReleased、SessionInvalidated、SourceUnresolved。会话级事实可无 RequestSerial，开始／释放事实必须对应已发行请求。只有 SessionOpened 携带 Cold／Rearm；只有 RequestStarted 携带 ColdPhysicalPress／ReleasedThenPhysicalPress，不填默认成功模式。

## 来源neutral、聚合与失效合同

- 来源按原设备／键记录。有效非模拟原生数字 Press／Release、完整轴分量和连续性决定证明；Repeat、Action Started／Triggered／Completed／Canceled、合成轴零和零 Acceleration 均不能代替真实边沿。当前软件 PC.InputKey 可进入该观察路径，但不因此证明实体键盘、OS 焦点或设备试听。
- 不从空 GetKeyState、默认零或“刚建对象”补造 Neutral。Cold 只允许原一次资格内实际新数字 Press；Rearm 须先有原参与源的真实完整释放／Neutral，再由真实 held edge 发新请求。模拟输入、未知设备、缺边沿或不完整／合并轴样本不能解除义务。
- 参与源全部可证明且均中立才为 Neutral；任一参与源未知则不能声称 Held 或 Released。在证明有效的同一请求内，任一来源仍按住就保留原请求，最后来源真实释放才关闭。方向变化、W／S 合成抵消不自行换号或释放；轴沿原生 raw 非零／零语义，不复制 Modifier／Trigger 或引入固定阈值。
- 来源不足发 SourceUnresolved 并保留原因；AwaitingPhysicalProof 不是 NotHeld。初生等待、输入失效和真正 Released 分开，禁止以轴值、速度、submitted／handled 或 Ready 对象装配代替证明。
- 映射重建／失效、原 Controller／输入对象更换、暂停、输入栈移除／屏蔽、Flush／EndPlay 会退役原会话。原键的释放义务保留，旧映射移除也不能抹掉其未完成释放。Flush 单独记录 native observation gap，不把安全归零当真实 keyup。
- 来源／CMC 的 FAILED、不可证明及尚未准入保持真实结果；不能用重建请求、重新 pin、反复 Press 或默认来源把失败变成功。诊断按原资源生命周期去重，包含模块、原对象／动作／路线及原因。

## 原装配调用链与清理

1. 原 LocalPlayer 生命周期提供 OriginResource；Controller 在原 InitInputSystem 范围围住 native 创建，PlayerInput.PostInitProperties 精确登记自身，完成后只对原注册提供一次资格。
2. Hero 的真实 ControlMappingsRebuilt 通知或新输入生命周期沿原作用域装配：归还原资源 → Source Begin → CMC Bind → 保存原 Session／Binding → 原 owner 同步订阅 → Attach。部分 IMC Add 期间不提前消费 Cold；不在 Triggered、Tick／Timer 中循环补 Begin。
3. Attach 可能同步回放；原资源必须先保存。Fact 委托携带固定 Binding＋Fact，原样交原 CMC；拒绝／陈旧只退役仍匹配的自身资源，旧 terminal fact 不得换戳或清理后继。
4. 原 Move Triggered 核实际 Action／原输入作用域，查询原 Source Request 后，继续按 ControlRotation.Yaw 做既有 camera-relative AddMovementInput，由 CMC 唯一执行。值近零仅跳过值投影，不推导释放。
5. Source 的待发事实按同一调用栈有序交付，真实 Release／Neutral 先签发再允许 receiver 重入新 Press；它不是延迟帧队列。真实外调返栈按实际可能变化的原资源重取核验，同栈纯查询段复用已验证输入。
6. ReleasePlayerInput 先摘原 Scope／Observer 和注册槽、封原资源，并在 Source／CMC／ASC 外调前归还本次 ForceWalk 请求；再用原句柄、原 Subsystem／PlayerInput、原 priority 和 CountRegistrations 归还自己的绑定／IMC 注册。旧清理不得操作重入后建立的后继资源，不用 ClearAllMappings。
7. 输入与 ASC 关联、订阅和 finite retry 属于各自原资源寿命，见 [Input 活动入口](../../Modules/Input/Module_Repair_07_Subleases.md)。ASC 唯一在 PostProcessInput 消费，清理使用原请求身份；原移动来源不能借 ASC Tag 或后继关联复活。

## 网络、验证和架构笔记边界

源码已存在 CMC 来源／owner 同步、预测与 qualified intent 接口。SavedMove／MoveData／校正保留各自来源和执行边界；历史重放不能生成新输入许可，不由 Hero 重发按键或请求号，服务端序列校验也不证明远端实体按键。网络实现及验收由 Movement 原作者负责，具体运行状态只索引[当前排程](../../Coordination/Module_Repair_Parallel_Schedule.md)。

当前源码接线不等于生产运行完成；编译、夹具、资产 Cold、Ready 对象、自然帧、真实设备和联机分别核收。软件操作另见[原装配 P1](../../../Saved/Codex/PlayerInputOperations_20261014_P1/README.md)，不扩其设备或权限合同。

### 保留的未闭合边界

- 正式 Hero 首次真实移动／W、qualified Held、持续同请求、真实释放及第二 Press 新号，仍须对应生产入口和原资源证据，不能用 D16 夹具成功推广验收。
- 暂停／Flush、映射与输入栈变化、Controller／输入对象更换后的真实释放再按与恢复；FAILED 保持及失败后的合法新请求，继续按实际场景核验，不做隐式恢复。
- 普通 Ready／Released 后实际输入重建、同 H Refreshed 不重建、旧回调／清理不串入后继，以及 StopPIE 原 Subsystem 失效诊断的闭合状态，须有原作者的对应运行回执。
- 历史 Host／夹具前置、WalkStartProfile／正式 Run 等资产与执行缺口，以及旧诊断 -1 deadline 预期与有限原期限的差异，保留原说明；不能由文档整理认定已修复或仍可用旧断言验收新合同。
- 原 Gate42／50／51／52／53 等失败与后继分层结果、D16 的受限成功、第17次输入身份污染红诊断全部保全。是否由后继同范围证据关闭只认原正式回执，本轮不改变失败、断言或未知状态；输入身份失败入口见[原验证记录](../../Modules/Input/Module_Repair_07_Validation.md)。
- 真硬件、真实焦点／设备切换与丢失事件、正式 Profile／Run、远端／listen／SimulatedProxy／网络回放及完整业务验收，分别保留未验边界，不借普通回归、软件键或数值结果填完成。
- 受影响的 Obsidian Input／Movement 图文同步仍由统筹另行安排；本轮不写外部笔记。CR 冗余整改只索引[唯一修复条目](../../Coordination/Module_Audit_Repair_Ledger.md)，不由本次归档授予 Source 写权。

旧预检中的分批“尚未实现／编译／接入”保持原文；上文只陈述本轮核到的当前接口存在和调用链，不回填较早批次验证。任何尚无充分后继回执的未知项继续保留。

## 历史导航

下列旧标题锚点保持可达，点击对应链接进入原文。历史租约／停止点只描述当时范围，不授权现在执行。

<a id="移动输入来源共享契约"></a>
- [移动输入来源共享契约](Module_Repair_MovementInput_Contract_History_20261016.md#移动输入来源共享契约)

<a id="v1-原子预检与精确租约"></a>
- [V1 原子预检与精确租约](Module_Repair_MovementInput_Contract_History_20261016.md#v1-原子预检与精确租约)

<a id="v1-静态冻结证据"></a>
- [V1 静态冻结证据](Module_Repair_MovementInput_Contract_History_20261016.md#v1-静态冻结证据)

<a id="分阶段精确接口playerinput-p1已声明实现调用链未接入"></a>
- [分阶段精确接口（PlayerInput P1已声明/实现，调用链未接入）](Module_Repair_MovementInput_Contract_History_20261016.md#分阶段精确接口playerinput-p1已声明实现调用链未接入)

<a id="playerinput生产者"></a>
- [PlayerInput生产者](Module_Repair_MovementInput_Contract_History_20261016.md#playerinput生产者)

<a id="cmc消费者唯一实现者为movement组长"></a>
- [CMC消费者（唯一实现者为Movement组长）](Module_Repair_MovementInput_Contract_History_20261016.md#cmc消费者唯一实现者为movement组长)

<a id="生产者p1预检2026-10-02-三文件已授权"></a>
- [生产者P1预检（2026-10-02 三文件已授权）](Module_Repair_MovementInput_Contract_History_20261016.md#生产者p1预检2026-10-02-三文件已授权)

<a id="p1-实现依据静态证据及停止边界"></a>
- [P1 实现依据、静态证据及停止边界](Module_Repair_MovementInput_Contract_History_20261016.md#p1-实现依据静态证据及停止边界)

<a id="原生扩展点与唯一归属"></a>
- [原生扩展点与唯一归属](Module_Repair_MovementInput_Contract_History_20261016.md#原生扩展点与唯一归属)

<a id="初始neutral及flush缺口明确未关闭"></a>
- [初始neutral及flush缺口：明确未关闭](Module_Repair_MovementInput_Contract_History_20261016.md#初始neutral及flush缺口明确未关闭)

<a id="事实顺序重入与静态路径核对"></a>
- [事实顺序、重入与静态路径核对](Module_Repair_MovementInput_Contract_History_20261016.md#事实顺序重入与静态路径核对)

<a id="冷启动正常路径的实际停止点与推荐取舍"></a>
- [冷启动正常路径的实际停止点与推荐取舍](Module_Repair_MovementInput_Contract_History_20261016.md#冷启动正常路径的实际停止点与推荐取舍)

<a id="v2-q-精确预检与资格来源停止点2026-10-02"></a>
- [V2-Q 精确预检与资格来源停止点（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#v2-q-精确预检与资格来源停止点2026-10-02)

<a id="为什么3文件内的postinitproperties不能证明资格出生"></a>
- [为什么3文件内的PostInitProperties不能证明资格出生](Module_Repair_MovementInput_Contract_History_20261016.md#为什么3文件内的postinitproperties不能证明资格出生)

<a id="推荐下一接缝未实施待统筹决定范围"></a>
- [推荐下一接缝（未实施，待统筹决定范围）](Module_Repair_MovementInput_Contract_History_20261016.md#推荐下一接缝未实施待统筹决定范围)

<a id="d7--v2-originresource-原子预检2026-10-02"></a>
- [D7 / V2-OriginResource 原子预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d7--v2-originresource-原子预检2026-10-02)

<a id="d7-实现有限静态证据与冻结边界"></a>
- [D7 实现、有限静态证据与冻结边界](Module_Repair_MovementInput_Contract_History_20261016.md#d7-实现有限静态证据与冻结边界)

<a id="已实现的资源契约"></a>
- [已实现的资源契约](Module_Repair_MovementInput_Contract_History_20261016.md#已实现的资源契约)

<a id="静态核对结果"></a>
- [静态核对结果](Module_Repair_MovementInput_Contract_History_20261016.md#静态核对结果)

<a id="未实施与后续顺序"></a>
- [未实施与后续顺序](Module_Repair_MovementInput_Contract_History_20261016.md#未实施与后续顺序)

<a id="d7-统筹gate43实际编译与剩余边界2026-10-02"></a>
- [D7 统筹Gate43实际编译与剩余边界（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d7-统筹gate43实际编译与剩余边界2026-10-02)

<a id="d8--localplayer薄宿主原子预检2026-10-02"></a>
- [D8 / LocalPlayer薄宿主原子预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d8--localplayer薄宿主原子预检2026-10-02)

<a id="d8-实现证据与冻结交回"></a>
- [D8 实现证据与冻结交回](Module_Repair_MovementInput_Contract_History_20261016.md#d8-实现证据与冻结交回)

<a id="d9--controller原生创建范围原子预检2026-10-02"></a>
- [D9 / Controller原生创建范围原子预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d9--controller原生创建范围原子预检2026-10-02)

<a id="d9-实现证据生命周期复核与冻结交回"></a>
- [D9 实现证据、生命周期复核与冻结交回](Module_Repair_MovementInput_Contract_History_20261016.md#d9-实现证据生命周期复核与冻结交回)

<a id="d10--postinit登记与实际默认类原子预检2026-10-02"></a>
- [D10 / PostInit登记与实际默认类原子预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d10--postinit登记与实际默认类原子预检2026-10-02)

<a id="d10-实现证据与四文件冻结交回"></a>
- [D10 实现证据与四文件冻结交回](Module_Repair_MovementInput_Contract_History_20261016.md#d10-实现证据与四文件冻结交回)

<a id="d11-types--模式与开始证明值原子预检2026-10-02"></a>
- [D11-Types / 模式与开始证明值原子预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d11-types--模式与开始证明值原子预检2026-10-02)

<a id="d11-types-冻结值与未来接线合同"></a>
- [D11-Types 冻结值与未来接线合同](Module_Repair_MovementInput_Contract_History_20261016.md#d11-types-冻结值与未来接线合同)

<a id="d11-types-有限静态证据与两文件冻结交回"></a>
- [D11-Types 有限静态证据与两文件冻结交回](Module_Repair_MovementInput_Contract_History_20261016.md#d11-types-有限静态证据与两文件冻结交回)

<a id="d12-a--实际参与来源与释放屏障原子预检2026-10-02"></a>
- [D12-A / 实际参与来源与释放屏障原子预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d12-a--实际参与来源与释放屏障原子预检2026-10-02)

<a id="d12-a-实现证据与三文件冻结交回"></a>
- [D12-A 实现证据与三文件冻结交回](Module_Repair_MovementInput_Contract_History_20261016.md#d12-a-实现证据与三文件冻结交回)

<a id="d12-b--原资格到实际started发行原子预检2026-10-02"></a>
- [D12-B / 原资格到实际Started发行原子预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d12-b--原资格到实际started发行原子预检2026-10-02)

<a id="d12-b-实现证据与三文件冻结交回"></a>
- [D12-B 实现证据与三文件冻结交回](Module_Repair_MovementInput_Contract_History_20261016.md#d12-b-实现证据与三文件冻结交回)

<a id="d13--原生出生与首个公开数字请求专项预检2026-10-02"></a>
- [D13 / 原生出生与首个公开数字请求专项预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d13--原生出生与首个公开数字请求专项预检2026-10-02)

<a id="d13-实现证据与三文件冻结交回"></a>
- [D13 实现证据与三文件冻结交回](Module_Repair_MovementInput_Contract_History_20261016.md#d13-实现证据与三文件冻结交回)

<a id="d14--首次跨帧失效定位证据原子预检2026-10-02"></a>
- [D14 / 首次跨帧失效定位证据原子预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d14--首次跨帧失效定位证据原子预检2026-10-02)

<a id="两次gate50真实红与当前已知未知"></a>
- [两次Gate50真实红与当前已知/未知](Module_Repair_MovementInput_Contract_History_20261016.md#两次gate50真实红与当前已知未知)

<a id="d14实现有限静态证据与冻结交回"></a>
- [D14实现、有限静态证据与冻结交回](Module_Repair_MovementInput_Contract_History_20261016.md#d14实现有限静态证据与冻结交回)

<a id="d15--native真实隐藏窗口生命周期原子预检2026-10-02"></a>
- [D15 / Native真实隐藏窗口生命周期原子预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d15--native真实隐藏窗口生命周期原子预检2026-10-02)

<a id="已复核gate51原因及游戏帧边界"></a>
- [已复核Gate51原因及游戏帧边界](Module_Repair_MovementInput_Contract_History_20261016.md#已复核gate51原因及游戏帧边界)

<a id="d15实现生命周期与有限静态交回"></a>
- [D15实现、生命周期与有限静态交回](Module_Repair_MovementInput_Contract_History_20261016.md#d15实现生命周期与有限静态交回)

<a id="d15-l--显式slate链接依赖补齐预检2026-10-02"></a>
- [D15-L / 显式Slate链接依赖补齐预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d15-l--显式slate链接依赖补齐预检2026-10-02)

<a id="d15-l实现有限静态与冻结交回"></a>
- [D15-L实现、有限静态与冻结交回](Module_Repair_MovementInput_Contract_History_20261016.md#d15-l实现有限静态与冻结交回)

<a id="d16--原首按叶自有真实inprocess-pie生命周期预检2026-10-02"></a>
- [D16 / 原首按叶自有真实InProcess PIE生命周期预检（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d16--原首按叶自有真实inprocess-pie生命周期预检2026-10-02)

<a id="d16--三文件实现有限静态证据及冻结交回2026-10-02"></a>
- [D16 / 三文件实现、有限静态证据及冻结交回（2026-10-02）](Module_Repair_MovementInput_Contract_History_20261016.md#d16--三文件实现有限静态证据及冻结交回2026-10-02)

<a id="input-hero-identityprepare--三文件原子预检2026-10-03"></a>
- [Input-Hero-IdentityPrepare / 三文件原子预检（2026-10-03）](Module_Repair_MovementInput_Contract_History_20261016.md#input-hero-identityprepare--三文件原子预检2026-10-03)

<a id="input-hero-identityprepare--实现有限静态证据及冻结交回2026-10-03"></a>
- [Input-Hero-IdentityPrepare / 实现、有限静态证据及冻结交回（2026-10-03）](Module_Repair_MovementInput_Contract_History_20261016.md#input-hero-identityprepare--实现有限静态证据及冻结交回2026-10-03)

<a id="input-hero-abilityrequestconsumera--原来源停止点2026-10-03"></a>
- [Input-Hero-AbilityRequestConsumerA / 原来源停止点（2026-10-03）](Module_Repair_MovementInput_Contract_History_20261016.md#input-hero-abilityrequestconsumera--原来源停止点2026-10-03)

<a id="授权步骤与写前登记"></a>
- [授权步骤与写前登记](Module_Repair_MovementInput_Contract_History_20261016.md#授权步骤与写前登记)

<a id="已确认的阻断证据"></a>
- [已确认的阻断证据](Module_Repair_MovementInput_Contract_History_20261016.md#已确认的阻断证据)

<a id="实际产物后继建议与冻结"></a>
- [实际产物、后继建议与冻结](Module_Repair_MovementInput_Contract_History_20261016.md#实际产物后继建议与冻结)

<a id="input-rawobservationseparation--三文件内部职责分离预检2026-10-03"></a>
- [Input-RawObservationSeparation / 三文件内部职责分离预检（2026-10-03）](Module_Repair_MovementInput_Contract_History_20261016.md#input-rawobservationseparation--三文件内部职责分离预检2026-10-03)

<a id="input-rawobservationseparation--实现有限静态证据及冻结交回2026-10-03"></a>
- [Input-RawObservationSeparation / 实现、有限静态证据及冻结交回（2026-10-03）](Module_Repair_MovementInput_Contract_History_20261016.md#input-rawobservationseparation--实现有限静态证据及冻结交回2026-10-03)

<a id="input-retrydiagnosticsignature--两现有诊断纯签名预检2026-10-03"></a>
- [Input-RetryDiagnosticSignature / 两现有诊断纯签名预检（2026-10-03）](Module_Repair_MovementInput_Contract_History_20261016.md#input-retrydiagnosticsignature--两现有诊断纯签名预检2026-10-03)

<a id="input-retrydiagnosticsignature--两cpp有限证据及冻结交回2026-10-03"></a>
- [Input-RetryDiagnosticSignature / 两cpp有限证据及冻结交回（2026-10-03）](Module_Repair_MovementInput_Contract_History_20261016.md#input-retrydiagnosticsignature--两cpp有限证据及冻结交回2026-10-03)

<a id="input-hero-actionconsumera--范围纠正冻结接缝与写前预检2026-10-04"></a>
- [Input-Hero-ActionConsumerA / 范围纠正、冻结接缝与写前预检（2026-10-04）](Module_Repair_MovementInput_Contract_History_20261016.md#input-hero-actionconsumera--范围纠正冻结接缝与写前预检2026-10-04)

<a id="input-hero-actionconsumera--实际产物与有限证据"></a>
- [Input-Hero-ActionConsumerA / 实际产物与有限证据](Module_Repair_MovementInput_Contract_History_20261016.md#input-hero-actionconsumera--实际产物与有限证据)

<a id="input-hero-localidentityb1--授权预检与生产接入2026-10-04"></a>
- [Input-Hero-LocalIdentityB1 / 授权预检与生产接入（2026-10-04）](Module_Repair_MovementInput_Contract_History_20261016.md#input-hero-localidentityb1--授权预检与生产接入2026-10-04)

<a id="input-hero-localidentityb1--实际产物与有限证据"></a>
- [Input-Hero-LocalIdentityB1 / 实际产物与有限证据](Module_Repair_MovementInput_Contract_History_20261016.md#input-hero-localidentityb1--实际产物与有限证据)

<a id="input-hero-sourcecmc-b2--授权预检与实际装配2026-10-04"></a>
- [Input-Hero-SourceCMC-B2 / 授权预检与实际装配（2026-10-04）](Module_Repair_MovementInput_Contract_History_20261016.md#input-hero-sourcecmc-b2--授权预检与实际装配2026-10-04)

<a id="input-hero-sourcecmc-b2--实际产物与有限证据"></a>
- [Input-Hero-SourceCMC-B2 / 实际产物与有限证据](Module_Repair_MovementInput_Contract_History_20261016.md#input-hero-sourcecmc-b2--实际产物与有限证据)
