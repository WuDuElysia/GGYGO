# 移动输入来源共享契约

当前能力输入范围（2026-10-04）：能力以实际 EnhancedInput Action 回调及原绑定/会话为来源，保留 Injected、Chord、Combo 和 Completed/Canceled→Released；Movement 的真实 Release→新 Press 合同不变。A 已由统筹接受冻结并进入 Gate57 统一构建成功；native lifecycle 单叶不代表 Hero 生产验收。B1 typed H 消费与原作用域清理已交回冻结；末节 `Input-Hero-SourceCMC-B2` 登记本次已保存的原输入作用域→Source→CMC 生产装配及有限静态证据，B1/B2 尚未新编译/生产冒烟。以下各批次更新、停止及验证记录均保留交回时的历史状态，不能以旧能力全硬件证明分析阻塞已纠正的 Action 消费，也不能把准备/局部成功视为当前整链完成。

更新：2026-10-03（北京时间）。本记录只维护移动输入来源契约及分阶段证据。D7资格资源及D8～D10宿主/真实创建/PostInit登记/默认类已编译；原R0最新Gate42仍2 Fail/12 errors。用户批准显式冷启动首个真实Press、失败/重绑/失效后真实Release再Press，V2-Q出生证明停止历史保留。Gate48的D11/C38/D12-A及81 Success保留，ColdAndRearm仅为合成消费者证据。D12-B原资源/Claim/Mode/Proof/实际Request提交后且Started前Consume/生命周期退休已进入统筹Gate49R1新DLL：完整Editor Succeeded，8 actions/18.07秒/exit0，原81叶Success保持、新真实Cue叶Success；Movement FAILED专项保留Fail/2条production Error且断言/请求3恢复成立，独立与全量诊断匹配。这不证明真实Input出生/首W。D13真实出生专项在Gate50独立与全量均首个latent CheckCold失败，尚未Begin/Attach/W。D14诊断已进入Gate51新DLL，独立0 Success/1 Fail：实际首退为引擎CleanupGameViewport因原Viewport为空而移除LP，帧601Reason=PlayerRemoved/Qualification=Unavailable，并非夹具清理、Flush或消费。D15仅为Native夹具建立真实隐藏SWindow/SViewport/CreateViewport关联、非零尺寸、引擎注册及World销毁前对称释放；默认旧无窗口路径、全部生产资格、原出生/Cold/数字/10秒/全局归还断言保持，有限静态证据完成、三文件冻结。D15在Gate52五个runtime unity TU和lib完成，但DLL链接因21项Slate/SlateCore符号失败（exit6/24.50秒），此前“不需Build.cs”判断错误。D15-L已进入Gate53新DLL，完整构建Succeeded（8 actions/18.67秒/exit0），全量83 Success/2 Fail、原84叶状态保持。NullRHI在真实OS窗口前置失败；真实渲染的窗口/前置/跨帧Cold保持成立，但原10秒没有实际重建通知仍Fail。预先PIE由原Automation StopTests在Worker进入叶前结束，不能提供等待期间的游戏帧。D16已进入统筹Gate54新runtime DLL（完整构建Succeeded、4 actions/28.22秒/exit0）；真实渲染独立首按State Success/0 errors/5 warnings，原实际重建通知、Cold首W、Released/Neutral/第二Press新请求及Global清理断言通过。普通全量85路径为82无警告成功/2带警告成功/1 Fail，仅原首按Fail→Success，其余84状态保持；来源/收尾警告与原FAILED生产Error保留。此证据来自私有原生夹具公开数字输入，不代表物理硬件、正式Hero、Run或网络。Input-Hero-IdentityPrepare现新增Hero原身份订阅/opaque Resource/派生输入关联准备，全部旧生产方法保持、无新生产调用；有限静态证据完成并冻结，尚未编译或动态验收，不清实际Input/IMC/Camera或ASC输入。首次Begin前flush仍退休Cold，仅保留经认证的同Producer原weak归属用于真实释放再按Rearm；跨Producer缺可靠交接继续拒绝。Hero/MoveData生产接线、正式Hero首次W动态验收、异常恢复矩阵、正式Run/资产/联机、跨Producer交接及dummy取舍仍开放，不以专项代码或普通回归冒称根因关闭。

Input Hero技能原请求适配A本轮触发租约停止点：既有能力动作回调不能证明原物理来源及真实释放，未实施Hero源码迁移；仅记录有限只读证据并冻结。完整结论及后继契约建议见文末“Input-Hero-AbilityRequestConsumerA / 原来源停止点”。

Input-RawObservationSeparation已完成PlayerInput内部原生事实与Movement参与/恢复义务分离：唯一raw表及原生序列保留，Movement屏障不再改写raw；真实Flush单独记录原生缺口。有限静态证据见文末交回，尚未编译/UE；能力观察端口及Hero A/B仍未实施。

Input-RetryDiagnosticSignature已完成两现有诊断的OneParam原载荷签名适配，仅读取原Tag/deadline，原正文与断言保持；未编译/运行，旧-1预期及Hero/夹具/真实来源运行合同仍未迁移。

下文预检与交回证据按批次保留；其中“当前/未来/未接入”描述该批冻结时的状态，最新实现与未验证边界以上述更新及Input-Hero-IdentityPrepare交回为准，不能把后续接线倒填成较早批次的验证结果。

## V1 原子预检与精确租约

| 项目 | 约束 |
| --- | --- |
| 唯一写入者 | Input长期组长，gpt-6.1-sol / xhigh，直接执行，无代理 |
| 精确文件 | 新增`F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOMovementInputTypes.h`、新增`F:\ue_project\GGYGO\AAADocs\Architecture\Interactions\Module_Repair_MovementInput_Contract.md`；统筹ledger/schedule已登记 |
| 唯一结果 | 冻结SessionIdentity、输入RequestIdentity、ConsumerBindingId、Fact、七Kind及双参数事实委托的普通中性值定义 |
| 模块/依赖 | Input定义来源数据；PlayerInput未来生产来源事实，Hero管理绑定资源及转交，CMC管理事实消费、执行和失败门禁。共享头只依赖Core/弱对象引用/Delegate，不依赖ASC、Hero、CMC或Profile具体类型 |
| 先后 | 核对租约与不存在目标→保存保护基线→本记录登记预检→添加共享头→静态字段/默认/比较/委托/范围核对→记录证据及外部最终hash→两文件冻结交回；随后生产者及CMC按互斥租约接续 |
| 只读依赖 | 既有Hero输入会话、PlayerController原生输入入口、CMC与C36只读契约、EnhancedPlayerInput原生InputKey/Flush/输入栈扩展点；既有输入身份头仅核对，不能复用ASC技能来源 |
| 非目标 | 无USTRUCT/UHT、发号器、运行容器、来源held或执行状态、有效性判定、消费实现、网络序列化、RPC/Tick；不写Hero/CMC/ASC/Config/测试/旧07和10记录/Obsidian/资产/全局记录 |
| 验收 | 仅约定四个struct、七值enum和TwoParams Delegate；默认0/Invalid/NAME_None；身份比较弱对象索引/序列号和对应发行序列；Binding与Fact分参；无实际包含点/运行修复或编译声称，保护范围保持 |
| 停止点 | 需要其它文件、运行机制或未冻结字段即停止交回；静态核对完成立即冻结，不执行UE/构建/Git或代理操作 |
| 当前状态 | 已核对租约及两个目标原先均不存在，预检先登记后完成94行共享头与本记录，静态核对完成，两文件冻结；未接入真实TU、未编译或运行 |

## V1 静态冻结证据

- 新头只有四个普通struct、一个七值enum及一个TwoParams Delegate；三个身份各有==/!=，原生产者/消费者弱身份使用HasSameIndexAndSerialNumber，Binding还比较原SourceSession。四个序列字段默认0，Kind默认Invalid，Reason默认NAME_None；不新增IsValid/运行有效性接口。
- 委托参数顺序为`const FGGYGOMovementInputConsumerBindingId&`、`const FGGYGOMovementInputFact&`，原绑定与事实分参；没有单参数旧版。CMC消费结果枚举和生产者/消费者方法都未放入共享头。
- 共享头直接包含CoreMinimal、Delegates/Delegate、WeakObjectPtrTemplates，UObject显式前置声明；无ASC/CMC/Hero/Profile具体类型依赖，无USTRUCT/生成头、运行容器、Get/IsValid、发号、Tick或网络序列化。
- 本步只有这两文件apply_patch。Source/GGYGO中rg可见h/cpp/cs清单230→231，新增仅本共享头；统筹另授权的AbilitySystem ASC h/cpp、GA.cpp三文件为合法并行范围，不归V1。排除该三文件后227个既有源码hash保持，Hero/CMC/PlayerController/旧Input和测试均保持；18个Config/旧07和10记录/Obsidian保护文件hash保持。
- 已读共享头全文及本记录修改内容；两文件尾随空白/冲突标记均0。头SHA256：`7C9C1B3FC6902BE2E99FE2FBC5B5EA5C185983772E4B1FF88C2E14C666D9AE61`；本记录最终hash通过外部交回，不在文件内写自身hash。
- 共享头包含点为0，四个值结构和事实enum仅在本头出现；没有真实TU或运行证据。本层未执行构建/UHT/UE/Git/代理，不能将类型冻结称为移动失败恢复、来源认证或网络已修复。
- 架构核对：新增仅中性值副本及委托类型，无循环依赖、第二事实/执行状态、内部状态读取或资源清理机制；运行资源与清理责任在后续PlayerInput/Hero/CMC阶段分别验收。Obsidian禁止范围保持，图文同步边界如下登记。

## 状态与身份唯一归属

| 所有者 | 唯一职责 |
| --- | --- |
| 项目PlayerInput生产者 | 原始来源证明、SessionSerial、输入RequestSerial、EventSerial；作为原生输入处理的薄适配，不决定移动成功/失败 |
| Input OriginResource | 原LocalPlayer生命周期证据、同步原生创建票据/精确构造登记、一次初始资格及认领Session；不持有物理来源、不发行来源号。D8 LocalPlayer只保有并转发生命周期，D9 Controller只包围原生创建及原票据清理，D10 PlayerInput只在原范围Record自身；Source资格认领/消费尚未接入 |
| Hero | 原Pawn/Controller/PlayerInput/Action/InputComponent/CMC绑定资源、身份副本与转交；保留现有AddMovementInput，不维护移动失败状态或计时器 |
| CMC | ConsumerBindingSerial、C36执行RequestSerial、事实消费、执行与失败准入、SavedMove/校正/重放；输入请求编号和执行请求编号分属不同身份 |

- 三个来源发行序列由同一原PlayerInput单调分配，不随松键、重绑或换Hero重置、不回绕；0为未分配，耗尽明确拒绝。CMC独立发行其绑定与执行序列，不能借用输入发行值。
- 会话身份为原生产者弱对象身份和SessionSerial。请求身份加输入RequestSerial。消费绑定身份为原CMC弱对象身份、ConsumerBindingSerial及原SourceSession。
- 弱身份采用`HasSameIndexAndSerialNumber`保留失效对象的原身份，禁止通过Get()或普通弱指针==归并两个失效对象。值相等不证明当前对象、会话、请求或绑定仍有效。
- 会话级事实的RequestSerial可为0；RequestStarted/RequestReleased要求真实已分配的请求身份。EventSerial为生产者观察顺序，不能以相等World time区分事件。
- 共享头不保存按键集合、neutral状态、运行缓存、Profile或失败状态，也不声明消费结果。`Recorded/Duplicate/Stale/Rejected`由CMC定义；Recorded仅表示事实已消费，不表示允许执行或移动成功。

## 分阶段精确接口（PlayerInput P1已声明/实现，调用链未接入）

### PlayerInput生产者

```cpp
bool BeginMovementInputSession(APawn* Pawn, UInputComponent* Component, const UInputAction* Action,
    FGGYGOMovementInputSessionIdentity& OutSession, FString& OutError);
bool AttachMovementInputReceiver(const FGGYGOMovementInputSessionIdentity& Session,
    const FGGYGOMovementInputConsumerBindingId& Binding,
    FGGYGOMovementInputFactDelegate Receiver, FString& OutError);
void EndMovementInputSession(const FGGYGOMovementInputSessionIdentity& Session, FName Reason);
bool GetMovementInputRequest(const FGGYGOMovementInputSessionIdentity& Session,
    FGGYGOMovementInputRequestIdentity& OutRequest, FString& OutError) const;
```

- `FString& OutError`为必需参数，无缺省；成功清错误，失败清空对应OutSession/OutRequest并输出可定位原因。Attach失败不安装新接收者。End只关闭匹配会话，幂等，不伪造物理Released。
- 建立顺序：Begin准备身份→CMC Bind→Attach后发布事实。建立期间来源变更须明确失败并清理原token/绑定，不丢弃事实后补造新请求。
- 原绑定值在注册及在途回调中冻结；委托同时携带Binding与Fact。旧回调不得查询当前绑定并给自身换身份；旧清理不能摘除后继接收者。

### CMC消费者（唯一实现者为Movement组长）

```cpp
bool BindMovementInputSession(const FGGYGOMovementInputSessionIdentity& Session,
    uint64 ExpectedConsumerBindingSerial,
    FGGYGOMovementInputConsumerBindingId& OutBinding, FString& OutError);
EGGYGOMovementInputConsumeResult ConsumeMovementInputFact(
    const FGGYGOMovementInputConsumerBindingId& Binding,
    const FGGYGOMovementInputFact& Fact, FString& OutError);
```

- ExpectedConsumerBindingSerial精确匹配消费者当前契约，陈旧调用拒绝；绑定发行者为原CMC。Bind失败清OutBinding并给错误，不能把“新绑定”用于旧回调。
- Consume结果由CMC独立定义为`Recorded/Duplicate/Stale/Rejected`，不放共享头。Binding/SourceSession、请求与事件生命周期校验归消费者；事实记录和移动准入分别判定。

## 来源neutral、聚合与失效合同

- 数字来源由有效路由中的设备/键、非模拟真实Pressed/Released及连续可信观察证明；Repeat、Action Started/Triggered/Completed/Canceled、轴合成零和零Acceleration不能代替物理边沿。
- 所有实际来源均确认中立才是neutral。W/S抵消仍有实际按住来源；同一请求内任一来源仍按住则保持原请求，最后来源真实释放才Released。确认neutral后首个真实按下才发新请求号，方向变化不换号，保留真实事件顺序。
- 初始快照须具有真实neutral基线及随后连续可观测、无flush/缺口的前提；否则为Unknown。P1不使用空GetKeyState或默认零作为基线，数字来源必须已有真实释放，轴来源必须已有完整真实分量。轴沿原生逐键非零/零语义，不新增固定阈值，不重复执行Modifier/Trigger。无法证明时SourceUnresolved及Reason必填，拒绝关联启动/恢复并去重诊断。
- 映射失效/重建、输入栈屏蔽、Controller或输入对象更换、flush/EndPlay使原会话失效；不宣称物理释放。保留尚未确认真实释放的来源记录，持续按W在重绑/flush后归零、repeat或恢复Action触发时不能重新发号；真实释放确认neutral后再按才是新请求。
- 来源不足的诊断包含Input模块、Pawn/Controller/PlayerInput/Action/映射和原因，按来源生命周期去重；不每帧刷屏，不无限静默重试，也不执行替代业务。

## 网络、验证和架构笔记边界

- 用户已批准扩展现有CMC MoveData的会话/请求来源字段，由Movement独占后续实施；不增加RPC/第二帧调度器。服务端校验上报序列及生命周期，不声称能够证明远端物理按键。
- SavedMove与校正/replay须保存、消费原来源边界，重放不调用Hero补造按键，不重发输入或执行请求号；具体网络和消费实现仍未完成。
- V1共享头已由新PlayerInput头包含，PlayerInput.cpp为待编译的模块源码；尚无编译/UHT证据，本步不单独构建。既有PlayerController实际创建接入待P2独立授权，接口冻结后CMC/Hero互斥适配。所有生产源码冻结后由统筹统一构建和严格验证。
- 原严格Input17身份诊断不因本类型交付关闭，移动失败恢复/预测/远端及受影响调用链尚未验证。
- 已只读核对计划蓝图与Input/Movement结构。后续图文须补PlayerInput来源权威、Hero资源接线、CMC绑定/消费/执行身份区别、真实来源及网络边界；本租约禁止Obsidian写入，本文只登记类型已定义与运行链未接入的分阶段状态，局部图文由统筹后续安排。

## 生产者P1预检（2026-10-02 三文件已授权）

| 项目 | 约束 |
| --- | --- |
| 唯一目标/所有者 | Input组长在真实UEnhancedPlayerInput扩展点实现移动来源认证及上述生产者接口；仅来源与绑定生命周期，不执行移动 |
| 精确可写文件 | 新增`F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOPlayerInput.h`、新增`F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOPlayerInput.cpp`、更新`F:\ue_project\GGYGO\AAADocs\Architecture\Interactions\Module_Repair_MovementInput_Contract.md`，三文件；统筹正式授权，源码已实现，有限静态核对后冻结 |
| 前置/只读依赖 | 本V1值类型冻结；原生InputKey/FlushPressedKeys/输入栈求值与阻断扩展点、实际Enhanced映射视图、原Pawn/Controller/输入资源生命周期；CMC只依赖共享数据，不要求Input包含具体CMC/Hero |
| 实现边界 | 同一原PlayerInput认证自身发行会话/请求/event，当前注册路由复核原Pawn/Controller/Component/Action；接收者保存原Binding与原SourceSession。原生输入流程继续Super，使用其扩展点，不另设Tick/dispatcher |
| neutral与清理 | 真实来源证明和未确认释放记录只有一处归属；失效后仍held不重发号，flush/模拟Released不冒充释放。Begin/Attach失败无残余新资源；会话匹配关闭，先摘除旧资源，保护同步重入后继，序列不回绕 |
| 非目标 | 既有PlayerController实际创建接入、Hero绑定、CMC消费/失败门禁、网络序列化、资产/Config/测试/旧07和10记录/Obsidian；本步不声称运行链已经使用新类型 |
| 验收断言 | 自身发行来源唯一；同帧真实释放→重按顺序保留；多键最后释放/首个新按下聚合；映射重绑/flush/零轴/持续repeat不补造请求；不可证明轴neutral明确失败，不新增阈值；绑定ABA与旧回调身份隔离；失败清输出，清理幂等 |
| 停止点 | 原生公共扩展点不足以证明来源、需要新中立语义或其它文件/业务状态/Config/资产就停交回。生产者静态冻结后顺接P2，仅PlayerController.cpp与本记录候选两文件核对创建类型；蓝图Override不兼容单独报告 |

P1先登记本预检后实施。轴来源沿原生EnhancedPlayerInput逐键RawKeyValue的非零/零语义（非Action合成值）：仅非模拟真实单样本可更新证明，配对轴必须已观察所有分量；不执行Modifier/Trigger，不发明摇杆阈值。缺分量、非有限或合并样本无法证明时拒绝关联并诊断，不补造neutral。持续held记录跨End/重绑/flush保留，真实释放后才解除。

P1范围内未接PlayerController/Hero/CMC实际调用，P2仍待独立顺序授权；本步不运行UE/构建/Git/代理，不为准备接口另开构建轮次。

## P1 实现依据、静态证据及停止边界

### 原生扩展点与唯一归属

- 新`UGGYGOPlayerInput`继承UEnhancedPlayerInput，覆盖公开`InputKey(const FInputKeyEventArgs&)`、FlushPressedKeys、BeginDestroy和原生输入栈EvaluateInputDelegates/EvaluateBlockedInputComponent；每个覆盖保留一次对应Super。旧参数final重载没有覆盖。InputKey先保存原会话、逐设备观察真实来源，完成原生Super后才发布来源事实；不根据Super返回值认证来源。
- SessionSerial/输入RequestSerial/EventSerial只有本PlayerInput分配，0未分配，MAX_uint64耗尽诊断并拒绝，不重置/回绕。ObservationRevision仅用于Begin/Attach期间观测变化检测，不是第二请求号、计时器或帧调度。
- Begin只准备原Pawn/Controller/PlayerInput/LocalPlayer子系统/Component/Axis2D Action实际映射身份；Attach核对原Session、有效Consumer/非零Binding、原SourceSession及Delegate，再发布Opened和明确的neutral/Unresolved。建立过程中真实观测变化及Opened回调重入变化均拒绝，清理匹配原会话；重复Attach不会替换既有接收者。所有成功清OutError，失败清OutSession/OutRequest或匹配准备资源。
- 实际映射只保存键和各层Modifier/Trigger数量及弱对象身份，随调用复核，不持有映射数组引用、不读取或再执行Modifier/Trigger状态。路由变化拒绝查询并关闭原会话；另由原生LocalPlayer子系统ControlMappingsRebuiltDelegate在其广播边界关闭原会话，即使键和对象比较相同。该通知为原生帧末广播，未声称能提前获知内部尚未广播的重建。
- 同头内`UGGYGOMovementInputRouteObserver`只持有一个原会话身份的弱生命周期订阅，监听原子系统重建、原Pawn Controller更换和EndPlay；不持有来源held/请求/执行状态。End先detach订阅、接收者和原资源，再调用外部接收者。已复制的旧观察回调仍携带旧Session，不查询新Binding，不关闭后继。

### 初始neutral及flush缺口：明确未关闭

- `ReadSourceProof`现已取消空GetKeyState/默认零证明分支：映射键未出现于PhysicalSources就Unknown，无论数字或轴。UPlayerInput构造/清表时可能尚未收到一个已经按住的键；原生PlayerInput.cpp首个Repeat补Pressed逻辑也明确描述跨关卡/新Controller/flush时缺少初始Pressed的情况。因此“从本对象创建起未收到Pressed”不证明物理已松键。
- 数字neutral只来自有效设备、非模拟真实Released，且之后没有证明缺口；首次Pressed若没有完整neutral基线不补造RequestStarted。所有映射来源必须证明neutral；含尚未观察过的W/A/S/D或未报告过完整零分量的Gamepad映射时，初始关联明确拒绝，不能把此状态称为正常首按可用。公共InputKey/键状态入口未提供先前未观察来源的物理中立证明，本轮不展开新设备协议/默认成功；该生产前置须统筹后续决定，P2创建类本身不能关闭它。
- Flush先把所有已记录来源标为InputFlushedObservationGap，清除轴观察分量证明，保留数字held与原RawValue，再关闭原Session并执行Super；模拟Released不清PhysicalSources、不清held，不解除Unknown。真实Repeat不能解除缺口或发行新请求；数字须真实释放、轴须完整新样本后才可再确认neutral。普通End/重绑保留连续来源记录，只有Producer销毁释放记录。
- 摇杆仅使用有效设备、有限、单样本的真实标量事件，按原生配对X/Y/Z维护已观察掩码；独立标量映射和配对向量分别记录。缺分量、NumSamples非1、非有限、直接不完整向量或设备不明为Unresolved，不选死区/阈值，不用Action零、W/S抵消或Acceleration零判断释放。原生分量事件顺序不是硬件原子向量/远端物理认证。

### 事实顺序、重入与静态路径核对

- 同一已证明请求首个真实来源按下发行RequestStarted，任一来源仍held保持同号，最后真实释放发行RequestReleased，再NeutralConfirmed；同帧下一真实按下发行新RequestSerial/EventSerial，独立于World time。
- Released与Neutral两份原Binding/Delegate/Fact先按顺序保存到本生产者的同步发送缓冲，再调用接收者。接收者在Released中重入真实按下时，新Started只能附在既有Neutral之后；缓冲沿原调用栈同步清空，不新增Tick、Timer、异步dispatcher或第二帧执行链。它只保存原事实副本，不成为第二held/request权威。
- 旧Session在回调中结束/重建时，旧排队事实及Invalidated均保留原Binding/SourceSession；消费者自行判定Stale，生产者不会改戳后继身份。End(old)精确匹配且幂等；Receiver/Consumer在发送前失效则诊断并关闭匹配会话，不冒充成功送达。SourceUnresolved撤销Get/执行关联，但保留已发行的ActiveRequestSerial及单次Unresolved标记，不伪造Released；即使后来来源暂时重新可证明held，该原请求也不能恢复Get。真实全部neutral后发原ID的Released→Neutral，再允许后续新Started；会话先失效则用原ID的Invalidated终止，匹配CMC保留open请求的生命周期。
- 有限静态走查覆盖：单键释放→重按、W/S抵消/多键最后释放、跨End/flush持续held与Repeat、配对分量缺失/合并样本、Begin到Attach及Opened回调观测变化、Released回调重入、旧观察/旧清理ABA、销毁及计数耗尽。以上为源码路径复核，未执行动态测试或证明实际UE行为。
- 两新源码尾随空白/冲突标记均0；共享头SHA256保持`7C9C1B3FC6902BE2E99FE2FBC5B5EA5C185983772E4B1FF88C2E14C666D9AE61`，Hero/PlayerController/DefaultInput保护核对不变。本轮只写本三文件，未执行UE、构建/UHT、Git或代理操作；未修改并行CMC/ASC实现或测试。
- 架构核对：Input仅来源认证/订阅及原事实发送，未依赖CMC/ASC/Hero或Profile业务，未新增移动执行/失败状态、循环依赖、计时器或内部状态写入。来源缓存寿命为原PlayerInput、会话资源精确清理；原Input17红、移动失败恢复、Run、网络、资产及消费者七Kind动态验收仍开放。Obsidian图文因本租约禁止写入未同步，待统筹安排Input来源权威/生命周期/初始neutral缺口及接口接线更新。

### 冷启动正常路径的实际停止点与推荐取舍

- 具体场景：新PlayerInput的PhysicalSources为空，实际IA_Move有W/A/S/D及Gamepad2D映射。第一次真实W Pressed只证明W当前held，A/S/D未观察、摇杆分量未观察仍Unknown，不能发行第一个请求。按现冻结“全来源neutral后才首按”的准入，确实会要求其它映射来源先获得真实释放/完整零样本，未连接设备可能永远没有这些事件；不是可用的正常冷启动链。
- 原生公共InputKey只提供已收到事件，GetKeyState缺项/零受构造及flush影响，映射视图列可能路由，不是当前设备全部物理状态的完整证明。仅把映射改名为“实际来源”并删除未观察项，不能补足可能已held但尚未报告的来源证明。本轮不另开设备协议或第三权威，停止新增范围写入，保留当前明确拒绝的产物；冷启动未验收，P2不能替代此决策。
- 一个推荐取舍，需统筹向用户确认后修改已冻结准入：明确区分冷启动首个请求与失败/flush后的恢复；冷启动允许首个真实、非Repeat的物理Pressed开启首个请求，不额外宣称全来源已Neutral，聚合其实际观察到的来源；后续失败/flush仍保留已有held/Unknown与原请求身份，必须真实释放证明后才能恢复。这样不伪造neutral且能正常首按，但改变“首次Started必须先有全来源NeutralConfirmed”的消费者合同及可证明范围，需要Input/CMC共同修订并覆盖冷启动、重绑、失败恢复和未连接摇杆。当前实现未采用该取舍。

P1三文件在上述静态核对后冻结交回，冷启动准入决策未解决；下一步等待统筹接收，P2仍需独立授权。不得以本实现记录推定初始neutral前置、生产链或严格诊断已经关闭。

## V2-Q 精确预检与资格来源停止点（2026-10-02）

以下为本轮授权预检，覆盖上文P1交回时的待决状态；用户已批准冷启动取舍，但本步不发行该开始证明，也不改聚合规则。

| 项目 | 约束 |
| --- | --- |
| 唯一目标/所有者 | Input长期组长直接闭合LocalPlayer初次资格登记、一次认领/消费/永久退休及Producer交接阻断快照；没有代理 |
| 精确租约 | `F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOPlayerInput.h`、同目录`GGYGOPlayerInput.cpp`、本既有Contract，共3文件 |
| 只读依赖 | 原生PlayerController.SetPlayer/InitInputSystem、PlayerInput.PostInitProperties、LocalPlayer原Controller关系/变化通知；既有P1资源与弱身份、CMC消费合同、Gate41统筹证据 |
| 依赖顺序 | 确认可证明的初次创建许可→登记一次资格资源→原准备会话认领→真实请求发行时消费→失败/End/flush/路由及Controller失效退休→旧Producer先封闭并交出阻断快照→后继唯一观察；本轮先登记预检，再允许源码实现 |
| 最小候选资源 | 原LocalPlayer/初次Controller/Producer弱身份、一次资格状态、精确认领Session、转交期间原/后继弱身份和冻结阻断快照；默认不可用，认领不是请求成功，消费必须依真实已发行请求；只有Input维护，不另发来源号 |
| 阻断快照 | 仅原移动来源已知held或Unknown及原设备/键/分量/原因；旧观察者失去写权后才能移动快照。交接回调先封闭旧权，再核对原后继身份，不可给在途旧回调改戳；原LocalPlayer失效回收资源，不能可靠转交就明确拒绝 |
| 非目标 | 共享头、StartProof字段/发行、ReadSourceProof及实际来源聚合、CMC/Hero/Controller/测试/配置/资产/Obsidian、UE/构建/UHT/Git；不自动执行V2-S/P2 |
| 验收断言 | 首次原生创建有明确许可来源；CDO/缺LocalPlayer/晚接入不能授予；同LocalPlayer换Producer不重授；Begin/Attach失败、End、flush、来源/路由失效、Controller改变永久退休；真实请求前不能消费；旧回调不清后继；只有一个物理观察权威 |
| 停止点 | 需要第4生产文件、改变共享签名/新生命周期权威，或3文件不能证明资格来源就保留产物、记录具体证据并停写，不用注册表缺项/空PlayerInput默认授权 |
| 本轮实际结果 | 仅本记录写入预检与停止证据；PlayerInput h/cpp及共享头保持P1冻结版本，未添加资格注册表、交接机制或虚假正常创建判定，未执行构建/UE/Git/代理 |

### 为什么3文件内的PostInitProperties不能证明资格出生

1. UE5.8 `F:\UE_5.8\Engine\Source\Runtime\Engine\Private\PlayerController.cpp`的SetPlayer先把`Player = InPlayer`及`InPlayer->PlayerController = this`写入，再对LocalPlayer调用InitInputSystem。原Controller关系此时已被替换，PostInitProperties不能由当前互指恢复之前的Controller历史。
2. 同文件InitInputSystem在PlayerInput为空时执行`PlayerInput = NewObject<UPlayerInput>(this, OverrideClass ? OverrideClass : DefaultClass)`。新对象的PostInitProperties发生在该赋值完成之前；正常首次创建和具有相同Outer/LocalPlayer/配置类、尚未填回槽位的晚接入NewObject，在此钩子里都有空PlayerInput和相同互指关系。
3. `F:\UE_5.8\Engine\Source\Runtime\Engine\Private\UserInterface\PlayerInput.cpp`的PostInitProperties仅调用Super及ForceRebuildingKeyMaps(true)，没有原生创建许可、旧Controller参数或“LocalPlayer第一次输入系统”的令牌。公开GetOverridePlayerInputClass只能证明当前期望类型，不能证明实际调用来自InitInputSystem或配置从何时生效。
4. 资格注册表在首次遇到本类之前没有来源历史；“没有条目”既可能是正常初次，也可能是旧普通EnhancedPlayerInput/Controller使用之后首次接入本类。把缺项当Available，会重现禁止的隐式资格兜底。认领后再检查`Controller->PlayerInput == this`也不能修复，因为两条路径都能填回同一槽位。

CDO/空LocalPlayer/显然已有PlayerInput可直接拒绝，但上述剩余两条路径仍不可区分，因此没有把部分结构检查冒称首次原生创建认证，也没有先堆交接代码再掩盖这个根前提。

### 推荐下一接缝（未实施，待统筹决定范围）

由Input唯一维护资格及转交资源，创建流程的既有所有者提供显式出生证据：在实际原生输入系统创建范围预约原LocalPlayer/Controller的单次创建许可，PostInitProperties只能认领该许可；许可无默认值、出范围即封闭，Begin/Attach不补发。初次许可还须来自覆盖LocalPlayer初次创建/首次Controller输入建立的明确生命周期边界，不能仅在较晚首次遇到本类时凭注册表缺项发放。Controller/LocalPlayer生命周期所有者只提交出生及失效证据，不持有来源held或发行请求，资格权威仍是Input。

该接缝需要超出当前三文件的创建侧接入，建议统筹先冻结出生证据的责任与精确入口，再分“Input许可接口→创建方接入→本V2-Q资格/快照实现”互斥原子步骤；每步1～4文件，不自行扩租约。本记录不是新共享签名，也未指定未经核查的创建侧文件为已获授权。

本轮停止新增写入并交回：资格来源未闭合，资格/阻断快照均未实现；旧P1来源机制和冷启动不可用状态保留。Gate41的B0成功不替代本边界，也不能作为本次资格运行证据。

## D7 / V2-OriginResource 原子预检（2026-10-02）

统筹Gate42窗口结束后明确授权本步；上述V2-Q源码继续冻结，不恢复PostInitProperties猜测。下面先登记预检，再实施底层资源；既有宿主与构造登记接线尚未实施。

| 项目 | 本步冻结约束 |
| --- | --- |
| 唯一目标/所有者 | Input长期组长本人闭合LocalPlayer真实Added/Removed、同步原生创建票据及初次资格认领/消费/不可恢复退休；无代理 |
| 精确文件 | 新增`F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOMovementInputOriginResource.h`、同目录`.cpp`，更新本既有Contract，共3文件；两新文件核对原先不存在，Contract基线`1BF922D05F056B4D38E2D829721D2AA0F7C9BC6A30A8D0D3B1CFB4B805CC2909` |
| 先后/接缝 | 本记录预检→实现资源→有限静态核对及保护hash→三文件冻结；后续既有GGYGOLocalPlayer转发真实生命周期、Controller包围Super::InitInputSystem、项目PlayerInput在票据内PostInitProperties精确登记，分别另授，不由本步补建/接线 |
| 私有资源 | 默认Unavailable；原LP/Controller/登记Producer弱身份、一次资格阶段/认领Session/退休原因，一个同步创建范围和精确构造对象、单调资源票据序列。票据0未分配，范围失败不可恢复，不发行来源或执行号 |
| 创建证明 | Begin保存明确配置类及原Controller的空输入槽位；Record只在该票据内记录刚构造的精确对象，第二对象或替换使范围失败；Complete必须匹配Record、实际返回对象和原生已赋回槽位，缺Record明确失败。Begin/返回字段形状不授出生 |
| 清理 | Close用于栈退出/Abort，按原资源弱身份及票据序列清当前范围，不依赖Controller/LP仍有效；已关闭票据幂等，旧票据不关后继。Removed/销毁先封闭许可，消除Busy，不等待某帧 |
| 资格与查询 | 真实Added完成后才能记录候选；存在旧Controller、重复Added、当前未登记Controller通知、既有未登记PlayerInput、创建失败或更换均退休。Claim仅认领精确Session，Consume仅由原Producer真实发行请求后调用，不能把Begin/Attach算成功。强类型查询Unavailable/Cold/Rearm只表达资源资格，Rearm不证明物理释放、不准入移动，不能暗中把失败改模式 |
| 非目标 | 不改PlayerInput/LocalPlayer/Controller、共享来源头、CMC/Hero/GAS/测试/图文/资产/配置；无物理held/Unknown、来源请求计数/StartProof、冻结快照/观察权交接、动作时钟、Tick/调度器/全局注册表/Provider框架；无UE/构建/Git |
| 验收断言 | 默认及缺登记不可用；只有完整出生证据可Cold；正常重复原生Init不补出生；第二对象/替换/关系变化拒绝；认领不消费、真实请求消费一次；退休/Removed/销毁不可恢复；Close无残余Busy且ABA隔离；成功清错误/失败清输出；没有第二物理或执行权威 |
| 停止点 | 需要第4文件、物理快照才能完成资格函数、改变原状态归属或增加另一生命周期实现即停止给证据；不得添加无定义stub或伪成功。本步无调用方时Complete缺Record必失败 |

只读查询的Cold要求有效生命周期、精确登记的当前Producer及Available/Claimed资格；Rearm要求同样的登记与当前关系，但资格已经Consumed/Retired，只表明冷启动永久不可用；未初始化、Removed、未登记、当前范围尚未完成、对象失效或关系不符为Unavailable。后续调用方必须显式处理这三个结果。

## D7 实现、有限静态证据与冻结边界

### 已实现的资源契约

- 新`UGGYGOMovementInputOriginResource`为Input层Transient UObject，Outer必须是原LocalPlayer；默认Unavailable，非模板且真实Added的前后Controller身份均明确为空才设置候选Available。此前Added/构造的无效尝试、晚接入、重复Added、Removed和销毁不能重授。宿主未来须仅在真实Added创建并用UPROPERTY保有同一资源，Removed后保留退休对象，不能Getter懒建或重新NewObject恢复资格；当前宿主尚未接线。
- `BeginNativeCreation`只接纳当前原生互指Controller、明确具体PlayerInput类及空原生槽位，保存原Controller/配置弱身份和非零资源序列；不据此授予Producer。已完整登记的同一对象、同一配置重复Init明确返回成功/NeedsCreation=false/Ticket=0，表示无需创建；既有未登记对象拒绝，不能据空注册或返回字段补出生。票据序列单调且MAX拒绝，独立于Source/Request/Event及CMC编号。
- `RecordNativeCreatedProducer`在当前同步范围内、原Controller的PostInit登记精确构造对象，首次登记时原生槽位必须仍空；同对象重复登记幂等，第二对象、配置/Outer不符、已填槽位才首次登记、登记后替换或丢失原对象使范围永久失败。当前范围的Controller通知也检查已登记对象/替换。旧/外来Controller的Begin或Record被明确拒绝，不污染后继范围；当前Controller在无范围中登记则永久退休初始资格。
- `CompleteNativeCreation`核对原票据、实际Record、原构造弱身份、配置、当前LP/Controller关系及已赋回原生槽位；没有Record明确失败，普通未实现登记钩子的PlayerInput不会凭类名或字段形状获得资格。成功只登记原Producer并关闭范围，不把Retired/Consumed改回Available；所有本范围失败完成先关闭，再记录保留原范围上下文的诊断。
- `CloseNativeCreation`仅按原Resource弱索引/序列和精确CreationSerial清理，不要求Actor/LocalPlayer仍有效。关闭后的原票据再次Close幂等，旧票据不能清除后继；缺诊断原因也先安全终止原范围再明确失败。Removed/销毁会立即封闭许可和当前范围，销毁保留一次Super。调用方未来必须用原栈票据保证Super早退/Abort/关系丢失路径Close，不能在退出时查询当前票据替代原身份。
- `ClaimInitialQualification`认领原Producer实际分配的非零Session，精确同Session重复认领幂等，换Session认领永久退休；认领不代表请求发行或移动成功。`ConsumeInitialQualification`只接受已认领原Session的实际非零Request，消费一次后只可Rearm；没有输入观察或请求发行逻辑。`RetireInitialQualification`只允许精确原登记Producer退休，旧对象不能退休后继。未来Source须在Begin/Attach失败、End、flush、来源/路由失效时显式退休；当前P1尚未调用这些资源接口。
- `GetQualification`只读且强类型返回Unavailable/Cold/Rearm，语义采用上述冻结定义；Rearm不是实际已松键、neutral或移动准入，也不是错误时的成功模式。资格资源不拥有Source当前会话真值，只保留已认领身份；来源连续性、held/Unknown和未来交接仍属Source范围，不能用本资源替代其校验。

### 静态核对结果

- 全文走查已覆盖：默认/模板/晚Added/重复Added/Removed/销毁，完整登记成功与正常重复Init，缺登记/第二对象/替换/原关系丢失，Claim与Consume区分/消费一次/永久退休，以及原票据在Actor失效和后继已打开时的Close幂等/ABA隔离。这是源码路径复核，没有动态结果。
- 新h为105行，cpp为437行；25个方法声明/定义对应无差集，花括号净差0，两源码尾随空白/冲突标记0，Super::BeginDestroy一次，LastCreationSerial仅一个递增点。原生`GetLocalPlayer() const`、PlayerInput槽位及弱身份API按本地UE5.8头核对；未运行编译器或UHT，未证明编译成功。
- 源码SHA256：h为`038AFF4BC6B82AD6E2DE71C42955301D5E4FC5111AF9E7A14A7A69E6CA312EDB`；cpp为`F18A2C44EB6B44489B3A9C641C9E9C8A9FF9D71A5AF6A6E500EC909C07EE9F9F`。本记录最终hash在外部交回，避免写自身hash。
- 本轮10个保护文件hash均保持：P1 PlayerInput h/cpp、共享MovementInputTypes、LocalPlayer h/cpp、PlayerController h/cpp、Hero h/cpp和DefaultInput.ini。合法并行ASC实现/测试不作“全项目未变”声称。本轮只修改上述3文件，无UE/构建/UHT/Git/代理、配置或资产操作。
- 依赖仅Core/UObject、共享来源值和原生LocalPlayer/PlayerController/PlayerInput；没有具体项目Player类反向依赖、Hero/CMC/GAS、全局注册表、Provider、Tick、计时器、物理来源集合、StartProof或来源/执行发行器。资格权威和栈范围清理均归本资源，未新增第二物理或执行状态机。

### 未实施与后续顺序

本步三文件冻结交回，未扩大租约。后续先由统筹授权既有LocalPlayer薄宿主，再授权Controller包围真实Super::InitInputSystem及原栈Close、项目PlayerInput在PostInit精确Record；各阶段完成后才能验证出生链。当前没有调用方，Complete缺Record必失败，本资源尚未成为实际输入流程的一部分。

阻断快照/观察权交接、Source认领/消费/异常退休接入、V2-S开始证明与聚合、Hero/CMC模式及网络适配仍是独立未实施边界；不得因本底层资源冻结宣称V2-Q整体、冷启动或失败恢复已关闭。Obsidian四个Input图文由统筹独占，本租约禁止写入；本记录交回已实现范围、调用链缺口及未编译证据供其同步，不重复修改图文或全局排程。


## D7 统筹Gate43实际编译与剩余边界（2026-10-02）

- 两新源最终hash保持038AFF4B…／F18A2C44…；完整Editor日志Succeeded，8动作38.65秒，UHT5 generated及新运行时DLL。底层已真实编译，但未接任何LocalPlayer/Controller/PostInit调用，不能宣称冷启动可用。
- 同批77项普通回归通过，新增四项是ASC ActorInfo事务专项，不能借它们当Input资格动态测试。原73保持，全叶0错误/警告；运行全日志仍49 Error／2 Warning，原日志和report保留。
- UE前后256源及本次9保护hash保持、UE已退出；持久证据见Saved/ValidationRecords/ModuleRepairGate_20261002_43_BeforeAutomation.json及_Result.json。生产输入、物理交接/StartProof/Hero/CMC/网络仍未实施。
- 下一LocalPlayer薄宿主仅零写入预检。真实Added／原Controller证据、Removed保留退休资源和只读Getter先冻结；Controller创建范围及PostInit登记后续独立实施，不从缺登记/普通77成功补资格。

## D8 / LocalPlayer薄宿主原子预检（2026-10-02）

统筹完成Gate43、UE退出并接受只读预检后，明确授权本步；先登记本预检，再改源码。上述“零写入预检”为Gate43结束时的历史状态，本步不改D7许可政策。

| 项目 | 唯一目标与冻结范围 |
| --- | --- |
| 目标/责任 | 既有GGYGOLocalPlayer强引用同一Input OriginResource并转发真实生命周期；资格、票据和物理来源规则继续分别归D7资源/未来Source，宿主不建新资格状态 |
| 精确文件 | `F:\ue_project\GGYGO\Source\GGYGO\Player\GGYGOLocalPlayer.h`、同目录`.cpp`及本既有Contract，共3文件；基线依次为`BA29CD973E5855A3A043A6D28BD149E0E493E4CF29CBFF2B371D6EC4CEEF8BA0`、`1A5FF1DFEA377551C27B2FDF386F564008207021375EE53767E7DECDB4D028DA`、`6D4D0DFF55CEB53526685AE3BC5BCCE51E138E9C7E72B40A0A0B28CB3AEB1486`；保留统筹新增D7 Gate43证据，不覆盖旧版本 |
| 共享接口/只读依赖 | D7两源038AFF4B…/F18A2C44…冻结；仅用既有Initialize/Removed/Controller通知接口。原生LocalPlayer两Added、Removed、Received、Spawn及GI创建/PC.SetPlayer时序已只读核对 |
| 实施顺序 | 本记录预检→宿主UPROPERTY和cpp纯读Getter→两真实Added捕获原Controller弱身份、创建/捕获原资源、各调用对应Super一次、返回后仅Initialize原资源→Removed/BeginDestroy在Super前退休且保留对象→Received先通知原资源再Super、Spawn捕获原资源并在Super后通知实际Controller→有限静态/保护hash→三文件冻结 |
| 初始化/清理断言 | 资源仅真实Added创建，首次新建资源在Super期间默认Unavailable；模板/非法宿主或非法已有资源明确诊断，不替换/补发；Getter不创建，Removed/销毁不清指针，重复/重入Added复用原对象，不NewObject重授。返回阶段只处理入栈原资源，不从Getter收养回调新状态 |
| 初次时序 | Native Added结束后才Spawn；SetPlayer互指→InitInputSystem→Received。后续完整Begin→PostInit Record→Complete必须在Received前完成，精确登记通知才不退休；本步无创建/Record接线，当前无范围/未登记通知仍退休，不跳过通知维持Cold |
| 本步非目标 | OriginResource/Controller/PlayerInput/共享头/Hero/CMC/GAS/测试/Config/资产/图文及构建/UE/Git/代理；不改既有SquadPresets缓存，不实现观察交接/StartProof/联机政策 |
| 验收/停止点 | 两Added各Super一次、Removed/Destroy通知早于Super、Received早于外部广播、Spawn原结果/错误保持；依赖无循环、无第二资格/来源/执行状态，保护10文件保持。需第4文件、接口或新资格状态即停；客户端dummy初始化/重绑取舍待用户决策，本步只保留当前退休行为，网络冷启动未关闭 |

仅新增宿主原资源强引用与原生钩子；Getter方法体放cpp，避免前置声明下TObjectPtr的内联转换。资源创建与初始化失败由宿主/D7给明确原因，不能让原生Spawn成功被误读为资格成功。初始化返回阶段捕获原对象，回调Removed造成的退休由D7重复/不可用门禁保留；不能换对象恢复许可。

## D8 实现证据与冻结交回

- `MovementInputOriginResource`为既有LocalPlayer的Transient UPROPERTY强引用；唯一NewObject/赋值点只在两个真实Added调用的私有Prepare中。模板/非法宿主、失效/模板/错误Outer的既有资源明确诊断，不换对象。Getter为cpp纯读返回，没有创建、初始化、资格或请求修改；既有SquadPresets方法体及缓存属性保持原样。
- 两Added各先保存原Controller弱身份，再创建/捕获原资源弱身份，调用各自对应Super一次，随后仅以入栈原资源完成Initialize，不查询当前Getter替换原对象。首次资源在Super期间无生命周期资格；晚Added按原弱身份及返回后Controller拒绝，重复Added由D7永久退休；Super回调Removed先退休同一对象，返回Initialize不能重授。原资源在回调中失效则明确失败，不收养后继。重复/重入Added没有新分配/清空路径；以上仅源码路径复核，未执行重入专项。
- Removed及BeginDestroy在各自Super前对原资源调用终止清理，保留UPROPERTY不置空；无需先发生PlayerRemoved才能在销毁时封闭生命周期。已终止资源复用并拒绝恢复。资源失效时合法幂等清理不执行替代业务，也不会创建新对象。
- Received在Super前向入栈原资源转发NewController；原生Super随后广播事件并通知子系统。Spawn在Super前捕获原资源身份，Super后向该原资源转发实际PlayerController，覆盖原生客户端dummy直接赋值路径；返回原bSpawned、沿用原OutError，没有把Native Spawn成功变成资格成功。缺失原资源明确诊断，不能Getter懒建；没有跳过未登记通知来保住Cold。
- 当前Controller/PlayerInput尚未包围/登记实际构造。D8运行时首次无范围或未登记通知按D7退休资格；完整冷启动需后续Begin→PostInit Record→Complete在Received之前完成，并用新的真实LocalPlayer验证。dummy目前同样退休；其作为初始化还是重绑的用户取舍未决，网络冷启动未关闭，Rearm只表示资格状态。
- 有限静态核对：h为76行、cpp为150行；11个方法声明/定义无差集，两个Added及Removed/Received/Spawn/BeginDestroy分别对应Super一次。唯一Origin NewObject/赋值各1、清空/Reset为0，Getter只有定义无内部调用，花括号净差/尾随空白/冲突标记均0；未运行构建/UHT/UE/自动化，不能用Gate43验证本批新宿主。
- 源码SHA256：h为`C09E76643E1A467D19D6DA54A89519F87F83F090A4DDF3BC7198228B2629F1D2`，cpp为`4DCDD4E984A7539A09BD67E7A59B7D717DE205040EB534610314D8DB30E0CFB9`。Contract最终hash外部交回，不写自身hash。
- 本步10保护hash均保持：D7 OriginResource h/cpp、P1 PlayerInput h/cpp、共享类型、PlayerController h/cpp、Hero h/cpp和DefaultInput.ini。本轮apply_patch只写租约3文件，无Git/UE/构建/代理/资产/Config操作；合法并行范围不归本证据，未声称全项目未变。
- 架构核对：项目LocalPlayer依赖Input资源，Input资源仅依赖原生Engine LocalPlayer而不反向包含项目宿主，无循环依赖。宿主没有资格阶段、来源/请求发行、物理held/Unknown、观察权、Tick/计时器、CMC/GAS执行或第二调度器；原资源保有/返回及清理责任可定位。图文由统筹独占，本步禁止写Obsidian，交回宿主已接/出生链未接及网络政策未决供其同步。

D8三文件在有限静态核对后冻结停写。后续Controller原生范围/PostInit登记及Source资格调用须分别另授；本阶段不冒称V2-Q整体、首次W、真实释放恢复或联机验收完成。

## D9 / Controller原生创建范围原子预检（2026-10-02）

统筹接受D8并核对原生入口后，明确授权本步；本记录先补预检再写源码。正式范围与基线见Parallel_Schedule的D9节及`Saved/ValidationRecords/InputControllerD9_LeaseBefore.json`，不恢复其它文件写权。

| 项目 | 本步唯一结果与约束 |
| --- | --- |
| 精确3文件 | `F:\ue_project\GGYGO\Source\GGYGO\Player\GGYGOPlayerController.h`、同目录`.cpp`、本既有Contract；基线分别`B6C08F16C45E03DB5306EF4AEE462AA0BBA92731CF3107FB6E6F1A8BA3FE185D`、`DD9BD38A3E626AAC27BD992630C6F626241F2A772543D0084F61F47B7C0037EA`、`F19AB924FA2A480A3A4B4466EF5949E550AE686237AB46EBCAC5184DA832D150` |
| 责任/冻结接口 | Controller唯一执行原生InitInputSystem；Input D7唯一持有资格/精确构造票据，D8唯一保有资源，Source后续唯一Record及来源发行。D7/D8接口和政策冻结，不引入共享签名 |
| 新执行契约 | Controller私有Idle/Running/Rejected仅管理原生创建执行；Running覆盖整个Init及每次Super（含已有对象/无LP），内层明确Busy、不Super/不排队、不毒化外层。非暂态拒绝锁存至Actor结束，首次诊断说明纠正依赖后须重新创建Controller，Tick不重复实际尝试；不拥有资格/held/请求/物理恢复状态 |
| 原生依据/配置 | InitInputSystem仅空PlayerInput选Override→InputSettings默认类；已有对象不重选。GetDefaultPlayerInputClass非法时回基础UPlayerInput，因此本步直接验证原默认软类引用已有效，不Load/替换/调用兜底。TickActor允许Player为空时Init，并在PlayerInput空时重复调用，故需要上述执行拒绝锁存 |
| 步骤 | 预检→公开InitInputSystem覆盖与私有执行阶段→配置读取/校验→原LP/资源/配置/对象弱身份捕获→本地Begin→原Ticket栈清理→Super一次→复核原关系/真实配置/对象→Complete；已有精确登记NeedsCreation=false不Complete零票据，无LP合法路径不请求资格→有限静态/保护hash→3文件冻结 |
| 生命周期/失败 | 所有退出只Close入栈原资源/原票据，不查询后继；资源已销毁由D7自身清理。拒绝不得清除/替换原生PlayerInput；已有登记返回失配只退休原Producer，不能影响后继。缺Record明确MissingConstructionWitness，原生对象已创建不表示本地资格成功 |
| 非目标 | PlayerInput PostInit/配置切换、D7/D8/共享头/Hero/CMC/测试/资产/图文/ASC消费与调试主体；无来源编号/资格发行、Tick/计时器/第二输入状态或调度、物理交接/StartProof/网络改策；无Build/UE/Git/代理 |
| 验收/停止点 | Super仅正常原生路径一次，Busy/Rejected不调用；配置无效拒绝且无兜底，已登记对象不重选类；原票据早退/关系变化/销毁可关闭，内层不毒化外层，拒绝后不自动重试。需第4文件或共享接口即停。实际默认Enhanced及无PostInit登记保持，不能称首次W或完整E2修复 |

用户批准的首次真实Pressed与失败/重绑/来源失效后真实释放再按保持；执行阶段不能判定物理释放，也不能用Rejected→Idle自动恢复。dummy初始化/重绑问题仍未获得新的答案，本步不作网络特判。

## D9 实现证据、生命周期复核与冻结交回

- Controller新增公开`InitInputSystem`覆盖；私有Idle/Running/Rejected只管理本Actor的原生创建执行。入口Rejected直接返回，不再次查配置/Begin/Super；入口Running去重诊断Busy后返回，不访问D7票据、不调用Super/排队、不改变正常外层阶段。正常返回的活Actor仅Running→Idle，活Actor的非暂态拒绝→Rejected；拒绝诊断明确纠正依赖后须重新创建Controller，无自动恢复入口。Busy布尔仅诊断抑制，不是资格或输入状态。
- 空原生槽位沿原配置选择Override或默认类，不改配置、不NewObject/清空/替换slot。TSubclassOf返回配置副本先读其原类引用并校验，避免错误基类Override被Get转空后暗中选择默认模式。默认字段在UE5.8为C++ private、公开反射config软类属性；通过FSoftClassProperty检查Config标志与PlayerInput MetaClass后读取其真实软引用，要求已有效并且是具体PlayerInput类。属性契约缺失、未加载/非法均明确拒绝；不调用会回基础类的GetDefaultPlayerInputClass，不加载另一类或补成功。已有有效对象使用实际类，不重新查询Override/default选择。
- 捕获原Controller/Player/LocalPlayer/World/已有Input弱身份及配置副本；本地路径必须由原项目LocalPlayer纯读Getter提供有效、原Outer的资源，不能懒建。Begin后立即保存原Ticket/原资源弱身份并安装作用域Close，再执行一次Super；返回核对原Actor/World/Player/LP/input/class、实际配置和原宿主资源。新本地对象只有精确Record才能Complete；已登记NeedsCreation=false不Complete/Close零票据，只复核原登记是否仍可用。已有对象失配只退休原Producer身份，D7拒绝旧对象影响后继。
- 无LocalPlayer（包括原生Tick的Player为空）为合法原生路径，不要求资格资源、不请求或授出生，但新建仍须有效原配置。完整Super以及其SetupInputComponent等外调始终被同一Running范围覆盖；返回换到另一个LP/Player/input不收养后继。缺宿主/资源、Begin拒绝、配置失效、身份变化或Complete失败均有本地拒绝结果；原生对象存在不意味着资格成功，不删该对象。
- 所有已获票据的退出只对保存的原Resource/原Ticket调用Close；Complete已关闭时重复Close幂等，旧票据不关后继，资源自身销毁则D7终止清理。统筹指出的失效Actor返回问题已修正：Reject与退出恢复只在原弱Actor有效且未销毁时写其执行阶段，弱Actor失效/销毁不再写字段或恢复Idle；日志使用入栈Controller路径及原弱资源/配置副本，不为诊断查询新资源。Actor已终止无需Rejected阻止Tick，票据清理独立继续。
- 当前实际配置仍EnhancedPlayerInput，项目Source没有PostInit登记。正常本地Super后仍走D7的MissingConstructionWitness明确失败和本ActorRejected；不得因类名、Outer或槽位填回授出生。下一步需分别授权项目PlayerInput在范围内Record及实际配置切换；本批没有Source资格认领/消费/物理恢复/开始证明，首次W及完整E2未关闭，dummy政策保持。
- 有限静态：h93行、cpp457行，新增Init声明/定义各1；原生Super一次、Begin/Complete/Close各1、两个作用域清理；花括号/圆括号净差0，尾随空白/冲突标记0。剥除字符串/注释后原生slot与Override配置赋值0、NewObject/加载/默认兜底Getter调用0；阶段Running/Rejected/Idle各一个赋值点，Rejected没有恢复路径。静态路径覆盖Busy不毒化、拒绝后无实际重试、无LP/已有登记、新建缺Record、关系变化/销毁与原票据清理；未运行这些动态专项。
- 源码SHA256：h为`BE23FE4BF4B1BE190F3A4D7DAA0C2F901DEDA95585423BF1C001AE4DBF188BCC`，cpp为`585B5DF1979D7C00D746C82B6D43649A4F778EDA8EEFDDB4D7445BB4846D1911`。Contract最终hash外部交回，不在文件内写自身hash。
- 原ASC Getter/PostProcessInput及全部编队调试/Shipping主体与租约前原文逐字比较保持；10保护hash保持：D7/D8两对源、P1 PlayerInput两源、共享类型、Hero两源及DefaultInput.ini。只修改本3文件；无Build/UHT/UE/Git/代理、Config/资产/Obsidian操作，合法并行范围不归本证据。Gate43不能验证本D9代码。
- 架构核对：Controller执行入口依赖Input资格资源和Player宿主；资源没有反向项目Controller依赖，无循环。配置副本/弱身份/原票据仅栈范围有效；执行阶段归Controller，资格归D7，原生对象仍由Super创建，来源held/请求及后续StartProof仍归Source；无第二输入状态机、请求发行、物理恢复、Timer/Tick或调度。全局/图文由统筹独占，本记录交回原生范围已接、出生Record/配置及输入恢复未接的实际状态供其同步。

D9三文件完成有限静态核对并冻结停写；未编译/运行，不用旧DLL或普通回归冒称新创建契约已经验证。额外源码/共享接口/配置/资产须另授。

## D10 / PostInit登记与实际默认类原子预检（2026-10-02）

统筹正式授权本四文件，Schedule已登记，写前hash见`Saved/ValidationRecords/InputPostInitD10_LeaseBefore.json`；先登记本预检再写源码，不修改并行Movement消费者范围。

| 项目 | 本步唯一契约 |
| --- | --- |
| 精确4文件 | `F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOPlayerInput.h`、同目录`.cpp`、`F:\ue_project\GGYGO\Config\DefaultInput.ini`、本既有Contract；基线依次`A2EDA810876ACF983CDD0EBB8A7011C286F04FD86571E2D165DABAFE8D2906A8`、`CC2DD75512A8F189ABBB5B632AB79FE33DD71C3212978F7727D1953331C4447B`、`9A88C4DF45EBF3D75BE37338C36C1856B9E61B40C1D46E225647DE89D8B9D58D`、`C5AADFC7B87261F48E1501BEE4274D340737066DB41E621F075EB3EAD649D3DB` |
| 唯一结果/所有者 | 现有UGGYGOPlayerInput的PostInitProperties在D9已打开的D7原创建范围内登记精确自身；默认类切`/Script/GGYGO.GGYGOPlayerInput`。Input负责登记，D9负责Complete/Close，D7资格唯一；不改名或发行来源号 |
| 冻结接口/顺序 | 新增PostInitProperties覆盖；入栈保存原Producer/Controller/LP/资源弱身份与安全路径→Super一次→非模板原关系重验→Record原资源。原生NewObject的PostInit在PlayerInput槽位赋回之前；Record不以空槽位/返回形状补授权。随后由D9核对实际槽位与原登记并Complete |
| 合法与失败 | CDO/模板保留Super且不登记；有效Controller的无LP原生路径不要求资源/不授资格。本地缺宿主/原资源、关系失效或Record拒绝明确诊断，不收养后继；Producer失效后仅用安全路径诊断，不再写字段。Producer不查询/发行/关闭Ticket，不创建资源 |
| 依赖方向 | Producer→Input生命周期薄宿主Getter→D7资格资源，仅取原资源；不读Teams/Squad/Player业务状态。底层资源仍只依赖原生Engine对象，无项目Player反向依赖/Provider/注册表 |
| 配置/夹具边界 | 仅DefaultPlayerInputClass一项改为现有类型，原Override优先保持，未登记Override仍明确失败。旧Input夹具自行NewObject基础ULocalPlayer并覆盖Init创建UEnhancedPlayerInput，不读取本配置/不经过D9，不算出生链验收；实际BP Override待统筹资产窗口 |
| 非目标 | D7/D8/D9/共享头/物理来源/资格Claim与Consume/StartProof/Hero/CMC/MoveData/测试/蓝图资产/dummy政策/图文/Build/UE/Git/代理；保持P1所有既有来源与会话算法 |
| 验收/停止点 | PostInit声明/定义及Super/Record各一次；原身份保存先于Super；仅真实非模板、有效本地原关系Record；默认配置唯一键/准确类路径；失败不伪成功，来源主体/12保护hash保持。4文件不可再拆：声明、实现和默认配置共同接通同一出生接缝，Contract记录边界。需第五文件、改名、共享接口或BP资产即停 |

首次真实Pressed及失败/重绑/失效后真实释放再按仍为已批准的后续来源合同；本步只登记出生，不消费Cold、不发StartProof、不宣称正常首按或物理恢复已实现。联机dummy语义继续待决。

## D10 实现证据与四文件冻结交回

- 现有`UGGYGOPlayerInput`新增公开`PostInitProperties`覆盖。在Super前捕获原Producer/Controller/LocalPlayer/OriginResource弱身份及对象/类路径；原资源只从原项目LocalPlayer的纯读Getter取得，不创建、不替换、不查询票据。Super恰调用一次；模板/CDO调用Super后退出，不登记。有效原Controller的明确无LP路径保留原生行为、不请求资格；失效Controller、变化的原LP/Outer和缺失原宿主/资源均明确诊断，不能把关系失败当成无LP正常路径。
- Super返回后只处理入栈原对象，重验Controller有效且未销毁、原Outer、原LP弱索引/序列、原生LP/Controller互指及原资源身份/Outer；不采用回调换入的宿主或资源。通过后仅向原资源调用一次`RecordNativeCreatedProducer`，D7继续校验当前同步范围、精确配置类、首登记时空原生槽位及同对象幂等；D9随后核对赋回的实际对象并Complete/Close。Source不发行/读取/关闭Ticket，不拥有资格阶段，不把Record成功称为资格消费或输入请求成功。
- 拒绝复用既有去重诊断入口，含原对象、实际类、Controller、LP、资源路径和原因；Producer已失效时只使用入栈安全字符串，不访问其字段。原Controller/LP/资源失效或被替换不能从当前值补授权。未登记Override仍由D7/D9的MissingConstructionWitness等契约明确拒绝；本批没有兜底类、资源懒建、资格补发、重试或清除PlayerInput路径。
- `Config/DefaultInput.ini`唯一`DefaultPlayerInputClass`改为`/Script/GGYGO.GGYGOPlayerInput`，已有类名和Override优先顺序保持，其它配置逐字保持。旧Input夹具显式创建基础ULocalPlayer并覆盖InitInputSystem直接NewObject UEnhancedPlayerInput，不经过D8/D9或本默认配置；不修改夹具，不以旧自动化通过证明本批出生链。蓝图Override实际接线须统筹后续资产窗口核查，本步未读取/迁移资产。
- 有限静态核对：h139行、cpp824行、ini101行；PostInit声明/定义各1，方法内Super/Record各1，Begin/Complete/Close/Claim/Consume/来源发行/NewObject/Tick/计时调用0；方法去注释/字符串后的花括号及圆括号净差0，三文件尾随空白/冲突标记0。剥除唯一新方法与3个include后cpp、剥除新声明/注释后h均与租约前全文一致；反转唯一默认配置键后ini全文一致，P1全部物理来源/会话/路由/观察交接主体未变。
- 源码与配置SHA256：h为`630782D0FE8CA63E1F890CA17E04F1103CCA5C70EC77340DB614E4DFF7C534D9`，cpp为`DF9A39E902E9A03D093EBD29586680E46DBFDA6C1FEE9364CB79F0002B67BA42`，ini为`B430D43698C2AA1760596C83DD9F4E81F92F998C8C1BD489B84CF59A4930E9A5`；Contract最终hash外部交回，不在自身写hash。
- 12保护hash保持：D7/D8/D9三对源码、共享类型、Hero两源、DefaultEngine.ini及InputTestTypes两源。只写本四文件，未执行Build/UHT/UE/Git/代理或测试/资产/Obsidian写入；并行Movement C37另有独占范围，不属于本保护证据，未声称全项目未变。Gate43只证明D7，不能验证本D8～D10新接线；上述失败、重入、替换、销毁路径只作源码复核，尚未运行动态专项。
- 架构核对：Source经Input生命周期薄宿主Getter取得原资格资源，不读取Teams/Squad或其它Player业务内部状态；资源仅依赖原生Engine对象，无项目Player反向依赖/新循环。Source新增只有同步栈弱快照及出生见证，持久状态和请求发行主体保持，资格仍唯一归D7，创建执行/原票据清理仍归D9；无第二输入/移动执行链、调度器或新持久缓存。全局入口和Obsidian图文由统筹独占，本交回供其同步Source PostInit登记/默认类已接及完整出生链未编译、物理开始证明未接的边界。

D10四文件完成有限静态核对后冻结停写。本批仅关闭PostInit登记与默认类接缝；Source Claim/Consume、阻断快照/观察权交接、StartProof发行、消费者模式适配、正常首次Pressed、真实释放恢复及dummy联机政策继续未完成。编译、原严格R0复现与出生专项由统筹排队，需第五文件或其它接口/资产时另授，不以本交回标记整个根因关闭。

## D11-Types / 模式与开始证明值原子预检（2026-10-02）

统筹接受D11只读预检后，仅授权共享值两文件；写前hash见`Saved/ValidationRecords/InputD11Types_LeaseBefore.json`，Schedule已登记。本预检先于共享头修改，D10及其它生产范围继续冻结。

| 项目 | 唯一结果与约束 |
| --- | --- |
| 精确2文件/基线 | `F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOMovementInputTypes.h`为`7C9C1B3FC6902BE2E99FE2FBC5B5EA5C185983772E4B1FF88C2E14C666D9AE61`；本既有Contract为`CC3447503DD1FE0BE96CFC5F23B50CE4280910D1140ADFA34BCD32320061205D` |
| 唯一所有者/责任 | Input组长直接定义中性SessionMode与StartProof枚举及Fact值字段；Input资源仍唯一拥有出生资格，Source仍唯一拥有物理来源/请求发行，CMC仍唯一消费及执行，不改任何状态归属 |
| 冻结值合同 | Mode为Invalid=0/Cold/Rearm，仅SessionOpened允许有效值；Proof为Invalid=0/ColdPhysicalPress/ReleasedThenPhysicalPress，仅RequestStarted允许有效值。其它Kind对应新增字段必须Invalid；无缺值默认成功或兼容替代 |
| 原内容保持 | 原三身份结构、比较方法、Fact Request/EventSerial/Kind/Reason字段、七Kind及其数值、TwoParams委托、include及依赖保持；只追加两个普通enum和两个Invalid默认字段，无校验函数/执行/持久状态 |
| 依赖/顺序 | 核对两基线与16保护hash→本预检→追加值及字段→有限静态/内存逆向保持核对→补目标消费者合同与未适配边界→两文件冻结；后续Source/CMC分别另授，Hero/MoveData更后阶段 |
| 非目标 | D7～D10出生侧、Source生产h/cpp、CMC/Hero/MoveData、资格Claim/Consume、聚合/观察交接、测试/资产/图文、Build/UHT/UE/Git/代理、dummy政策；不以普通回归替代开始证明专项 |
| 验收/停止点 | 新enum各1、字段各1且默认Invalid，原头剥除新增块后准确恢复基线，16保护保持；无新模块依赖/状态/兜底。同Event更换新字段须拒绝的消费者要求只作目标记录，本步不实施。需第三文件、语义新取舍或兜底即停 |

统筹Gate44实际结果仅作为已完成前置：完整Editor Succeeded、8 actions、30.82秒；普通77 Success/1 Fail（Movement旧无执行号夹具，实际4 errors为无执行号拒绝、StartStop/RunStop比较及RunStop样本；后续正速度断言因early return未执行），新Publish叶Success，256源/9保护保持、UE退出。此处于D12-A按统筹实际报告纠正原“严格正速度断言”概括，保留Gate44失败历史。该窗口覆盖D8～D10编译，不覆盖本D11新值，更不证明Input完整出生/冷启动动态验收或原严格R0已经修复。

## D11-Types 冻结值与未来接线合同

本节值定义已写入共享头；以下有效性、去重及生命周期规则是后续Source/CMC必须适配的合同，本批不新增验证函数或运行调用。默认Invalid不是旧模式、初次成功或恢复成功。

| 值/字段 | 定义与合法用途 |
| --- | --- |
| `EGGYGOMovementInputSessionMode` | `Invalid=0, Cold=1, Rearm=2`；Fact的`SessionMode`默认Invalid。只有SessionOpened可携带Cold/Rearm，RequestStarted及其它Kind必须Invalid |
| `EGGYGOMovementInputStartProof` | `Invalid=0, ColdPhysicalPress=1, ReleasedThenPhysicalPress=2`；Fact的`StartProof`默认Invalid。只有RequestStarted可携带有效证明，SessionOpened及其它Kind必须Invalid |
| 其它既有值 | 原三身份结构与弱身份比较、Request/EventSerial/Kind/Reason、七Kind（Invalid0、Opened1、Neutral2、Started3、Released4、Invalidated5、Unresolved6）及TwoParams委托原文保持，不新增编号/身份发行者 |

- `Cold`仅为原资源资格经明确查询并由原Session认领后的会话模式副本，不证明Neutral或已有请求。`ColdPhysicalPress`只用于其一次初次真实、非模拟、有效设备、实际映射的Pressed；Repeat、旧held、空键状态或未触碰映射不能补成Press或Neutral。Cold初按不要求把未观察A/S/D/未连接摇杆伪造为Neutral；出现真实证明缺口时明确失效/退休，不能改用Cold或其它业务。
- `Rearm`仅说明初次资格已不可用，不证明已松键。`ReleasedThenPhysicalPress`要求当前观察连续性范围内实际参与/阻断来源真实释放、确认Neutral后再发生真实Pressed；轴沿已确认完整真实零分量再非零的既有语义，不造阈值或默认零。Held、Repeat、Action值归零、flush、End或配置重绑均不能充当真实释放。
- Claim只认领已发行的原Session，不消费资格、不发行请求。Source真实发行首个非零Request后才对原资源Consume，且必须先于外部Started回调；序列不回绕/不复用。Begin/Attach失败、End、flush、来源/路由失效退休原资格，不对后继资源补发。原资格消费失败应明确终止关联，不自动切Rearm恢复；资源/Source原有唯一状态归属不变。
- CMC后续须校验新增枚举范围及Kind/字段搭配：Opened缺Mode、Started缺Proof、其它Kind带有效新增值均Rejected；同EventSerial对Request/Kind/Reason相同但Mode或Proof不同也须Rejected，完全相同才按既有Duplicate合同处理。事实副本及旧Binding身份不能改戳，不能借Cold重开已发行/未释放/执行失败的原请求。
- CMC后续在Opened消费原模式；Cold窗口仅能接纳一次Cold证明，消费Started或SourceUnresolved后撤销窗口。ReleasedThenPhysicalPress仍要求已消费真实Neutral且没有未释放来源请求；Neutral不清执行失败，Recorded不表示移动成功。CMC只保存消费阶段与值副本，不读物理按键、认领/消费Input资源或变成第二出生资格权威。
- 跨Producer阻断快照与观察权交接未完成。缺可靠原来源交接证据的恢复必须明确拒绝，不能把新Producer空记录、缺快照或资源Rearm当作物理已释放；本批没有新交接接口，也不改dummy旧退休政策。

当前生产边界：Source仍未查询/Claim/Consume原资格，也未填写Mode/Proof；其既有初次全映射Neutral前置、实际来源聚合和GetRequest仍待后续改造。CMC仍只比较旧Fact字段，并要求Started前已消费Neutral，没有实现上述Mode/Proof校验或Cold窗口。Hero/MoveData未接，旧夹具/普通回归不证明这套协议可用；本共享值交付不能标正常首次W、真实释放恢复或整个移动根因完成。

## D11-Types 有限静态证据与两文件冻结交回

- 共享头114行，只追加两个uint8普通enum和Fact末尾两个默认Invalid字段；新enum定义各1、新字段/Invalid初始化各1。原四struct、六个身份比较方法、七Kind及数值、全部原字段/委托/include保持；无USTRUCT/UFUNCTION、校验函数、执行/held/资格状态、容器、请求发行、Tick/计时器或模块新依赖。
- 内存剥除唯一枚举块及字段/注释块，原头全文准确保持，UTF-8字节SHA256恢复租约前`7C9C1B3FC6902BE2E99FE2FBC5B5EA5C185983772E4B1FF88C2E14C666D9AE61`；没有逆写磁盘。去注释花括号净差0，头尾随空白/冲突标记0。新头SHA256为`913319EA218ABF67BCEE57E807201F17DC607185E85AC7EF6E6EDA44B7E35A9D`；Contract最终hash外部交回，不在自身写hash。
- 写前/写后16保护hash保持：D7/D8/D9三对源码、Source两源、Hero两源、CMC两源、DefaultInput.ini/DefaultEngine.ini及InputTestTypes两源。合法其它工作线不属本证据，未声称全项目未变；D10出生登记/默认配置及Source原物理主体未写。Gate44是改本共享头之前的历史编译，不能覆盖D11字段；本批未运行Build/UHT/UE/测试/Git/代理，未写资产或Obsidian。
- 架构核对：新增仅输入事实的中性值，不增加资源/持久权威或第二执行链；无循环依赖、业务内部状态读取及清理责任变化。全局进度/Obsidian由统筹独占，交回新Mode/Proof值已定义、Source/CMC/Hero未适配及未编译边界供其同步，不修改图文。

D11-Types两文件完成有限静态核对后冻结停写；需第三文件、合同新取舍或业务兜底即交回。后续消费者及Source分别另授，不以定义完成冒称协议已生产接通、完整出生动态验收或根因关闭。

## D12-A / 实际参与来源与释放屏障原子预检（2026-10-02）

统筹接受Producer物理记录与Session资格的两生命周期拆分，只授权A；B须A冻结验收后另授同三文件。租约见Schedule 11:44及`Saved/ValidationRecords/InputD12A_LeaseBefore.json`，本预检及上述Gate44准确失败边界先于源码修改。

| 项目 | 本步唯一结果与约束 |
| --- | --- |
| 精确3文件/基线 | `F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOPlayerInput.h`为`630782D0FE8CA63E1F890CA17E04F1103CCA5C70EC77340DB614E4DFF7C534D9`；同目录cpp为`DF9A39E902E9A03D093EBD29586680E46DBFDA6C1FEE9364CB79F0002B67BA42`；本Contract为`9510F431E1CB91FC2BADC4F315F60B12E5628A05622514BB9D68447C53D63141` |
| 唯一所有者/结果 | Source在既有PhysicalSources原键/设备记录内标记真实参与及必须真实释放的屏障；同一聚合服务事实更新与GetRequest。不建第二物理集合/状态机或执行门禁，出生资格及CMC执行状态保持 |
| 输入/输出/依赖 | 输入为原生InputKey真实观察、当前冻结映射及原Session；输出为该次观察的前后聚合与真实held边沿快照、既有请求事实及可定位阻断诊断。只读D11值/C38消费、D7～D10与既有Source公开接口，不接资格或新字段 |
| 参与规则 | 未触碰映射不参加且不假Neutral，空参与无证明。Begin收纳已有真实映射记录，已held/未证实要求真实释放；每次观察只纳入当前映射或保留原参与阻断。旧映射消失不得抛弃held/未知/屏障，只有原键/设备真实Released或完整真零轴证明可解除；已释放且不再映射的旧参与才可退出聚合，物理记录不删除 |
| 屏障/清理 | End/flush/路由失效标记既有原始记录待真实释放，保留RawValue/down/未知及原身份，清轴观察分量有效期；屏障前Neutral不能恢复。未参与记录不计入聚合，但后来被映射收纳时不能沿用其旧Neutral。正常Session清理不Reset物理表，只有Producer真实销毁结束其记录生命周期 |
| 本观察合同 | Super前捕获原Session、当前观察Revision、前后聚合及真实held边沿；返回重验原Session/route与同一Revision，不借后继或后来观察。真实Pressed须非旧down/未证实/屏障，Repeat/模拟/DoubleClick不升级为本次首发边沿；轴须完整真实Neutral→非零，不补默认值 |
| 顺序/非目标 | 本预检→h元数据/私有观察值→cpp参与/屏障/原观察关联→有限静态/保护hash→证据及三hash冻结。无Mode/Proof发行、Claim/Consume/资源Retire，D12-B仍独立；Origin/Types/出生PostInit/CMC/Hero/MoveData/测试/资产/dummy/跨Producer转交、Obsidian/全局入口、Build/UHT/UE/Git/代理均冻结 |
| 验收/停止点 | 未参与不制造Neutral，空集合Unknown；已held/未知/缺轴/非法设备阻断保留，End/重绑/映射删除不绕过；真实原来源释放才解除；同观察前后值原样关联，重入不污染后继；Get复用聚合，公开接口/出生方法保持，15保护hash保持。需第四文件、共享接口/状态归属或转交机制即停 |

统筹Gate47实际前置：完整Editor Succeeded，8 actions/18.04秒/exit0；新DLL普通79 Success、其它计数0、全部叶0 errors/warnings，256源/9保护保持、UE exit0退出；完整日志49 Error/2 Warning保留。C38严格Mode/Proof消费已编译且旧Rearm夹具保持，新Cold专项未运行；此门禁发生在D12-A修改前，不覆盖本批物理聚合/屏障。用户再次批准显式冷启动首个真实Press、异常/重绑/失效后真实Release再Press；A仅准备物理证明，Source新字段与资格接线仍由B关闭，不把当前普通回归写成首按完成。

## D12-A 实现证据与三文件冻结交回

- `FPhysicalSource`原Key/Device/RawValue/down/分量/不可证明记录中仅增加两个元数据：实际参与标记、必须真实释放的屏障。`ReadSourceProof`只扫描实际参与记录，任一非法设备、未证实、屏障或缺轴分量返回Unknown；没有参与者也是Unknown，不能从映射目录/默认零构造Neutral。所有参与者有真实完整证明且无人held才返回Neutral；held聚合仍按原生逐键非零语义，GetRequest复用此唯一聚合，不另建状态机。
- Begin仅收纳已有真实映射记录，已held/未知/原屏障明确要求真实释放，不能把会话前held改成新Press。观察时当前映射纳入真实原Key/Device；映射移除后的参与held/未知/屏障继续保留。只有有效原设备数字Released或全部有效真实零轴才能清原屏障；已经真实释放且不再映射的旧参与可退出聚合，记录本身仍保留，退出后空集合保持Unknown、不补Neutral。不同设备的释放不清原未知设备记录，无法定位的设备阻断不猜测迁移。
- End在原Session精确匹配后、外调Invalidated前建立屏障；flush在Super/End外调前统一建立屏障，End在已有flush范围不重复标记。保留原RawValue/down及Key/Device，清旧轴分量有效期并标记待真实释放；未参与旧记录以后被映射收纳也不能沿用屏障前Neutral。真实完整非零轴不能清待释放屏障，必须完整真零；数字Pressed/Repeat、模拟释放、配置重绑/映射删除也不能清。正常End不删除物理表，唯一Reset仍是Producer真实BeginDestroy结束其记录生命期。
- 私有`FPhysicalObservation`仅保存本调用的Revision、前后聚合及真实held边沿，Super前完成捕获；不持有物理记录指针/映射数组引用。有效真实Pressed能记录候选边沿，不伪造其之前为Neutral；旧down/未知/屏障、Repeat、DoubleClick及模拟不能升级为本次Press边沿。轴候选要求原真实完整Neutral→非零。InputKey同时捕获原Producer弱身份与安全路径，Super一次后只访问仍有效且未终止的原Producer，失效时仅用入栈路径诊断、不再读写其字段。返回只更新原Session及精确同Revision，并复核原route；后继Session不处理，同Session发生后来观察则明确诊断、结束原Session且不采用最新观察。原请求已失去来源证明时仍保留原ID等待真实释放，不因暂时重新held恢复Get。
- 本批未接B：Attach/Publish仍未填写Mode/Proof、没有资源Claim/Consume/Retire，出生PostInit及公开接口保持。空参与的Cold等待策略、首个真实Pressed发行及资源消费顺序仍须B实施；当前旧Attach会发布默认Invalid模式/证明，不能与已严格C38消费称为生产协议已接通，首次W/物理恢复未关闭。跨Producer无转交证据仍未实现，不从本Producer空记录授Cold/Rearm成功。
- 有限源码路径复核覆盖：初始空参与及未触碰映射；会话前held；缺轴分量/非法设备/Repeat缺原Press；End/flush后旧Neutral与完整真零；旧映射blocker持有/真实释放退出；Super内旧Session结束/后继建立和同Session后来观察。以上为静态路径证据，没有运行这些动态场景或降低旧断言。
- h153行、cpp933行。私有变更仅物理两个标记、栈观察值及三个辅助方法/观察签名；完整内存逆向替换八个目标方法并剥除三个辅助方法后cpp准确恢复写前原文，h剥除物理元数据/栈值及恢复私有声明后准确恢复写前原文。公开h、PostInit、GetRequest方法体、Publish/同步事实队列、其它原方法及include逐字保持。InputKey/Flush各Super一次，修订序列先于本观察消费，花括号/圆括号净差、尾随空白/冲突标记均0；物理表只有销毁Reset一次，无Remove/Empty，新增Mode/Proof赋值和Claim/Consume/Retire调用均0。
- 源码SHA256：h为`687F0966EB45B8504D719DF789F032A9278343350368BDD9684670D431251390`，cpp为`92F73F97F7EE7F1F4D136543A60846AC29B8D0E4C596CAD713867B97629130BF`；Contract最终hash外部交回，不写自身hash。15保护hash保持：D7/D8/D9三对源码、D11共享头、Hero两源、C38 CMC两源、DefaultInput.ini/DefaultEngine.ini及InputTestTypes两源；两条合法测试工作线不属本证据，未声称全项目未变。
- 架构核对：Source仍唯一保有原始物理观察、请求/事件编号；元数据与原记录同生命周期、观察值只在同步栈有效，无第二事实集合/执行门禁、计时/调度器或新模块依赖。旧Session清理只作用匹配原Session，事实副本仍携原Binding，B资源及CMC执行权保持独立。仅写本三文件，未Build/UHT/UE/测试/Git/代理/资产/Obsidian；全局进度及图文由统筹独占，本记录交回A已实现/未编译、B未接及已知设备/跨Producer边界供其同步。

D12-A有限静态核对后三文件冻结停写，未编译/动态验收。A只关闭实际参与聚合与释放屏障，不把资格/首个Started发行的B生命周期合并；须统筹审查后另授B。任何第四文件、共享接口/状态归属或转交机制需要均立即交回，原严格Input/R0、正常首按、恢复、正式Run/网络验收继续开放。

## D12-B / 原资格到实际Started发行原子预检（2026-10-02）

统筹接受A并完成Gate48后仅授权本B三文件，排程12:38与`Saved/ValidationRecords/InputD12B_LeaseBefore.json`已登记；本预检先于源码修改。Source仍只发行物理事实并清自有资源，CMC独占执行准入/FAILED，不合并生命周期权威。

| 项目 | 唯一目标与约束 |
| --- | --- |
| 精确3文件/基线 | `F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOPlayerInput.h`5778 bytes/`687F0966EB45B8504D719DF789F032A9278343350368BDD9684670D431251390`；同目录cpp34091 bytes/`92F73F97F7EE7F1F4D136543A60846AC29B8D0E4C596CAD713867B97629130BF`；本Contract79919 bytes/`593D81AC3F8ED180DFD391721F85C91385CFED7E7210ED1CED72591181D3188B` |
| 唯一结果/所有者 | 原OriginResource资格接到实际Session和Started；Source仅保留原资源弱句柄、Opened模式只读副本及本Session未消费Claim资源义务，资格实际状态始终由D7查询/认领/消费/退休；A物理记录与CMC执行权保持 |
| 只读依赖/门禁 | 冻结D7三态查询/Claim/Consume/Retire、D8纯读Getter、D9/D10真实登记、D11 Mode/Proof及C38严格消费；A参与/屏障/原观察关联不替换。没有新共享签名或跨Producer接口 |
| 来源/资格 | 首次只能用精确已登记Producer的Cold捕获原资源及本Producer观察归属；未捕获原归属的新Producer遇Rearm明确拒绝缺转交证据，不猜Cold。后续同Producer只用原弱资源并核对原关系，不收养Getter后继。真实非零Session仅Cold Claim，失败退休原资格并清匹配会话，不作请求成功 |
| 字段/初次 | Opened明确Cold/Rearm且Proof Invalid；Started明确有效Proof且Mode Invalid；其它双Invalid。原观察增加是否已有实际参与者和真实数字Pressed候选的栈副本，空参与等待不发布Unresolved/不假Neutral；已held/真实缺口关闭Cold，Repeat/模拟/旧down不能首发 |
| 发行/消费 | 先准备非零Request/Event及原Binding/Receiver/事实副本，实际提交Request但保持不可查询的提交暂态，再Consume原尚claimedCold资格（首请求用ReleasedThen证明也消费），成功后才外调Started。失败退休并终止，不发Started、不复用号、不换Mode重试；原对象/会话/绑定变化不收养后继 |
| 清理/顺序 | End/flush/destroy/来源或route失效在外调前退休捕获原资源和精确Producer；缓存尚未建立的生命周期入口捕获入栈宿主资源，只有退休前D7对精确已登记Producer仍明确返回Cold才保留原weak归属，再立即退休，不Claim/Consume/保留Cold。首次Begin前flush/早退后的同Producer可用原weak及真实释放再按Rearm；未证明归属的新Producer不得收养Rearm。旧清理不摘后继；真实Released→Neutral→新Press保留。外部事实回调后以原弱Producer继续，销毁终止后不写字段或恢复调度标志 |
| 步骤/非目标 | 预检→原资源/模式/Claim义务与栈观察提示→Begin/Attach→准备/提交/Consume/原事实发布→End/flush/destroy及回调隔离→有限自查/保护→三文件冻结。Origin/Types/出生PostInit/CMC/Hero/MoveData/测试/网络/dummy/资产/全局/Obsidian/Build/UE/Git/代理均不写，不加第二执行门禁或业务兜底 |
| 断言/停止点 | 正常首Press不依赖未触碰映射；实际未知阻断退休而非转模式；Claim无请求、Consume位于实际发行后及外调前；失败不泄漏Started/复用序号；后继ABA及释放队列原身份保持；跨Producer无交接拒绝。需第四文件/共享合同变化立即停止交回 |

Gate48真实前置：完整Editor Succeeded，6 actions/16.16秒/exit0；新DLL81 Success/其它0、原79保持，新ColdAndRearm及真实Cancel叶Success，256源/9保护稳定、UE exit0退出，完整日志49 Error/2 Warning保留。A已编译但物理Source/完整出生及首次W仍未动态验收；ColdAndRearm是合成消费者证据，不是本B实际请求发行/资源消费或Hero生产接线证据。本B与ASC Cue互斥并行，无对方新API依赖，冻结前不编译。

## D12-B 实现证据与三文件冻结交回

- Source只增加原OriginResource弱句柄、Opened模式副本及本Session待消费Claim义务；资格唯一权威仍为D7。首次Begin仅在D7对精确已登记Producer明确返回Cold时保存原资源，之后始终重验原Controller/LocalPlayer/资源弱身份，不采纳后继。实际非零Session发行后才Claim；原资源返回Rearm时仅选Rearm，没有Claim或资格补发。未捕获原归属的新Producer遇Rearm明确拒绝缺观察权交接，不以空物理表推断恢复。出生PostInit及D7～D11接口未改。
- 首次Begin前Flush/早退自查已修正：退休入口先保存入栈原资源，只有尚未保存归属且D7明确返回精确Producer的Cold才保留该原weak，然后立即Retire。此保存不Claim、不Consume、不保留Cold、也不证明Neutral；同一Producer随后可以进入Rearm，仍须真实Released/完整真零确认Neutral再真实Press。原已保存资源失效时不查询替代；原生创建槽位尚未赋回本对象的合法初始化Flush不捕获资源，不污染D9尚在进行的出生登记。销毁时D7以弱索引/序列校验原Producer退休，弱Get已无效也不误退休后继。
- Attach的Opened明确填Cold/Rearm，Proof Invalid；空实际参与表只等待首个来源，不发布Unresolved、不造Neutral。实际已held/未知/非法设备/缺分量发布原SourceUnresolved并退休Cold。栈观察仅增加“之前是否已有参与者”和真实数字Pressed候选；非模拟、有效设备、实际映射、无旧down/未知/屏障且聚合可证明Held的真实Pressed可作ColdPhysicalPress。Repeat、DoubleClick、模拟、会话前held、未触碰映射和不完整轴不能替代；轴仍要求完整真零后非零的ReleasedThenPhysicalPress。
- 新私有IssuePhysicalRequest准备原Binding/Receiver及Started事实，先发行非零Request/Event，再把原Request实际提交为Active（提交暂态Get仍被阻断），然后对原待消费Claim调用Consume，成功并复核原对象/Session/Binding/资源/route后才把原事实加入既有同步队列、外调Started。首个请求若走ReleasedThenPhysicalPress仍消费未退休的原Claim。消费失败/资源失效/发行或提交关系变化结束精确原Session并退休，不发布Started、不复用Request/Event、不改Mode重试。Started只填有效Proof、Mode Invalid；其它事实双Invalid，泛用Publish不能发行Started。
- End先核对精确原Session再退休原资源、建立A屏障、拆原Observer/Binding并清会话；旧End不能触及后继。flush在Super/外调前退休和建立屏障；destroy在真实生命周期终点清原物理表/资源句柄。正常队列外调后重新获取原弱Producer，过期立即停止，不恢复失效对象字段；销毁终止队列先整体移动到栈副本再外调，事实保留原Binding/Receiver/Event。Released→Neutral仍在外调前成批入队，不借后来观察/后继事实改写原身份。SourceUnresolved保留原Request等待真实释放，不因又held恢复Get。
- 有限静态路径复核覆盖：空参与Cold首次数字Press；已有真实Neutral的首请求消费；会话前held/Repeat/非法设备/缺轴；同ProducerEnd/flush/首次Begin前flush及真实释放恢复；真实缺口退休后ReleasedThen证明；跨Producer缺交接拒绝；Consume失败无Started/号不复用；旧Session/Binding与原观察Revision重入隔离、原资源失效及销毁终止交付。以上均为源码路径核对，未运行这些动态场景，未降低原严格断言。
- h168行、cpp1256行；原方法变化精确为ValidateCurrentRoute、Begin、Attach、Publish、DeliverPendingFacts、End、Observe、Update、Flush、BeginDestroy，另加6个私有辅助方法。内存恢复这10个方法并剥除6个新增方法后cpp全文准确还原D12-A；h剥除1个前向声明、6个私有方法、2个观察提示及原资源/模式/Claim义务私有字段后全文准确还原A。公开接口、PostInit、InputKey、GetRequest、ReadRoute及A的ReadSourceProof/Describe/IsMapped/Adopt/Establish逐字保持；Observe剥除2行提示后与A一致。花括号/圆括号净差、尾随空白/冲突标记均0。Claim/Consume/Retire实际调用各1，原weak仅认证Cold的Begin/退休入口赋值2处、销毁Reset1处；PhysicalSources仍只有销毁Reset1处，无Remove/Empty。Request/Event发行→实际提交→Consume→原队列→Started外调静态顺序成立。
- 源码Bytes/SHA256：h 6739 bytes，`6310E2ECDA8AABEDF208F480B448D2836A525A6E75617A02D7111B6DDA6F5F97`；cpp 47644 bytes，`A649AA68CDE2A284AAB98E4972B2EA2A7BE11ADA9C56D406294F214761C19F58`。Contract最终Bytes/hash外部交回，不在自身记录hash。写前/写后15保护hash全部保持：D7/D8/D9三对源码、D11共享头、Hero两源、C38 CMC两源、DefaultInput.ini/DefaultEngine.ini及InputTestTypes两源。合法ASC并行线不属本证据，未声称全项目未变。
- 架构核对：资格状态及出生票据只属D7，Source只保存原资源义务与模式快照并唯一发行物理事实/编号，CMC独占执行准入/FAILED；没有第二资格权威、物理集合、帧调度器/计时器、循环依赖或新的Player业务内部读取。资源弱句柄保存至Producer生命周期结束，各Session义务在退休/消费清理，Observer/Binding/会话仍按原End清理。本批仅写授权三文件；未Build/UHT/UE/测试/Git/代理/资产/网络/dummy/Obsidian。全局进度和4个Input Obsidian文件由统筹独占，交回本实现及未验证边界供其同步。

D12-B有限静态核对后三文件冻结停写。Gate48证明A已编译与合成消费者通过，不覆盖B实际发行/消费或完整出生动态链；本B编译、实际默认/Override出生、首次W、Held/缺口/flush/重绑恢复、消费失败及回调失效专项仍未运行。Hero/MoveData生产接线、原严格Input/R0复现、正式Run/资产/联机及跨Producer可靠交接、dummy政策仍开放，不把Source接线称为移动根因全部关闭。需要第四文件/共享合同或状态归属变化立即交回。

## D13 / 原生出生与首个公开数字请求专项预检（2026-10-02）

统筹接受最终只读候选并正式登记本三文件租约，基线为`Saved/ValidationRecords/InputD13NativeBirth_LeaseBefore.json`；本预检先于测试源码修改。唯一新增叶为`GGYGO.Input.MovementOrigin.NativeBirthFirstDigitalPress`，Input长期组长直接执行，不新建代理/框架/资格权威。

| 项目 | 唯一结果与约束 |
| --- | --- |
| 精确3文件/基线 | `F:\ue_project\GGYGO\Source\GGYGO\Input\Tests\GGYGOInputTestTypes.h`5271 bytes/`8576301BDDABF505D5DECAA6E15EBE8717DCB4F031E6C4B82889DA8E28FF6454`；同目录cpp19481 bytes/`CF89CE4DD8E970DB255899E6750BD161DD3D3EAA5FFCBDFA0A1E11C83FA04878`；本Contract90439 bytes/`49D974B657625F20D296AFB81E986CF108B7D6025C5682A65DD2B12A9A28058E` |
| 所有者/唯一目标 | 在既有私有GI/World/Viewport夹具中增加显式原生路径，验证真实项目LP出生及D9/D10默认Source首请求的公开契约。夹具只保存构造选择、通知观察及消费事实副本，不模拟资格阶段/Source编号或CMC执行 |
| 冻结接口/依赖 | D7资格API、D8/D9/D10出生、D12-B Source、共享Fact及Hero生产默认注册均只读；Character L1只增加自身局部API，旧Extension函数逐字冻结，本专项不用其新API。旧夹具默认基础LP/直接增强Input路径及唯一LocalSessionReady叶、全部旧断言保持 |
| 出生顺序 | 原生GI CreateLocalPlayer(false)使用实际Engine配置项目LP→原生AddLocalPlayer及D8 PlayerAdded→原空槽位测试Controller选择仅Super InitInputSystem→SetPlayer触发D9/原生默认项目类NewObject/D10 PostInit/D9 Complete与Close→正常Possess/第一次Setup/Hero默认AddMappingContext；不手工调用资格接口、生产NewObject或清槽位，不用旧模式兜底 |
| 映射/时序 | 不强制立即重建/修改默认重建选项/提前安装映射/手工Broadcast；普通Rebuild由引擎实际帧执行并产生真实通知。既有测试Hero仅观察自己原subsystem的通知；标准Automation latent最多10秒等待实际通知与真实四键映射。每个可定位初始步骤及等待阶段严格检查Cold，发生退休立即失败，不等真实释放后再将首按判绿 |
| 唯一事实断言 | 生产Begin/Attach返回原Session；Opened Cold且没有伪Neutral/Unresolved。未触碰A/S/D的公开InputKey W Pressed→Started ColdPhysicalPress；callback内原资格已Rearm、Get返回实际同号。W Released→原Released→Neutral；再Press发行更大号ReleasedThenPhysicalPress；End→原Invalidated，原清理后资源Unavailable。其它Kind新字段均Invalid，原Binding/Event/Session不改戳 |
| 清理/失败 | RAII先撤自己原通知观察，再End精确原Session，最后夹具清LP/Controller/World/Viewport；失败/超时同样清理，既有全局World/Viewport不替换。引擎窗口没有真实重建帧时10秒超时明确交回，不手动Tick全局/改参数/假通知。实际首次合法步骤退休Cold则交回具体阶段，不扩生产范围 |
| 顺序/非目标/停止 | 预检→测试声明/显式模式/真实通知观察→既有夹具新路径/原步骤检查→唯一latent叶及清理→有限静态/20租约保护→三hash冻结。生产/配置/CMC/Hero适配/MoveData/其它叶/Flush-Rebind矩阵/资产/dummy/网络/Build/UHT/UE/Git/Obsidian/全局/代理均不写；需第四文件/生产接口/行为取舍立即停 |

前置Gate49R1：完整Editor Succeeded，8 actions/18.07秒/exit0，D12-B已进入新DLL，原81叶保持Success；新真实Cue叶Success。Movement FAILED专项保留Fail/2条production Error且断言和请求3恢复成立，独立/全量诊断匹配。这些结果不证明本D13出生/公开首按、实体键盘、Hero生产接线、正式Run或网络；本轮只实现专项，不运行Build/UE。

## D13 实现证据与三文件冻结交回

- 既有FGGYGOInputTestFixture增加显式InitializeNativeMovementOrigin入口，使用同一私有Standalone GI/World/Viewport和同一测试Controller/Pawn，默认旧路径不变。原生路径调用GI的CreateLocalPlayer(UserId, Error, false)，严格验证实际Engine配置类为项目LP、真实PlayerAdded前后尚无Controller且原Resource由其持有；不直接创建资源/Source。Controller在原槽位为空且Override为空时明确选Native，其InitInputSystem只Super并立即返回，失败不转到旧NewObject。SetPlayer实际触发D9/Engine默认项目类NewObject/D10 PostInit/D9 Complete与Close；之后严格确认Cold及实际默认类，不能从返回形状补出生。
- 新路径的自有Axis2D资产定义W/A/S/D，安装仍由正常Possess/PawnClientRestart的第一次SetupPlayerInputComponent→Hero InitializePlayerInput→默认AddMappingContext执行。只有Possess尚未建组件才调用公开PawnClientRestart；原生路径在ASC初始化后直接返回，不做旧夹具为ASC补订阅所用的第二次手工Hero初始化。SetPlayer返回、Possess/first Setup、必要Restart、夹具就绪及每次等待均严格查原Cold；任一步退休/失效立即失败，不能先释放/再认领让首按判绿。
- 既有测试Hero只增加原subsystem弱句柄及实际通知计数/首通知时间，AddDynamic绑定真实ControlMappingsRebuiltDelegate，回调只记录原通知，撤观察后旧复制回调不再记数。没有手工Broadcast、改变默认重建选项、提前Add、强制立即重建或私有重建入口。标准IAutomationLatentCommand等待原实际通知，截止10秒；同时校验原Cold、Observer/route。没有真实帧时明确超时，晚于截止的首通知也拒绝；不主动Tick全局/World或新建帧调度器。实际通知后验证原Source真实四键映射，缺失立即失败，不补映射。
- 唯一新增叶GGYGO.Input.MovementOrigin.NativeBirthFirstDigitalPress：由生产Begin/Attach得到真实非零Session，只有测试自己的实际ConsumerBinding编号；从未注入私有资格/Session/Mode/Request。首按前严格只有Opened Cold且Proof Invalid，无Neutral/Unresolved/请求；仅向公开InputKey注入有效测试设备、无simulated标志的W Pressed，A/S/D无输入事件。实际Started须ColdPhysicalPress且非零；callback内原资源已Rearm、Get可查询准确同号，Started Mode Invalid。随后同设备公开Released必须按原号Released→Neutral，Get旧请求失败；再Pressed发行更大号、同Session、ReleasedThenPhysicalPress，不能重复使用Cold证明。Claim/Consume的独立内部阶段不通过测试接口暴露，验证生产Begin/首请求链、回调前可见结果及原冻结D7/D12-B顺序，不能仅凭Cold查询宣称Claim。
- 正常精确事实序列为Opened→Started1→Released1→Neutral→Started2→Invalidated；每个事实callback核对原Binding/Session/非零Event，普通/终止事实的Mode/Proof都Invalid，最终逐项严格检查Event递增。RAII Probe先撤自己的原通知观察、End精确原Session，再调用原Fixture Shutdown；正常/中途失败/超时均走同一幂等清理，lambda只借同步Probe生命期，End先解绑后销毁夹具，没有强引用环。清理后原Resource Unavailable、LP子系统/GI/WorldContext归还，GWorld/全局Viewport保持；普通Release/End不被测试当成出生资格重新授权。
- 有限静态证据：h182行、cpp793行。原方法变化仅测试Controller InitInputSystem、Fixture Initialize/Shutdown；新增7个夹具辅助方法、一个Probe/latent实现及一个叶，h仅对应声明/构造选择和通知观察元数据。内存剥除Native分支后旧InitInputSystem/Initialize/Shutdown各准确还原原全文；其它原方法包括旧LocalSessionReady完整方法体逐字保持。剥除新增Scope/方法/include/FState字段并恢复上述3方法后cpp全文准确还原写前，h剥除新增块也准确还原；旧/新叶注册字符串各1。去注释/字符串后花括号/圆括号净差0，尾随空白/冲突标记0。测试中Claim/Consume/Retire及所有出生Ticket/Record接口调用0，强制/私有Rebuild、手动Tick、CreateSimulated和Broadcast调用0，没有新的UCLASS或生产入口。
- 源码Bytes/SHA256：h 6439 bytes/`6AC84B073797498A6252D5906A7ED6140002AAE103582A833AFD2AF0FB52AA9B`；cpp39871 bytes/`AC9702613C9E5441D91CE81651FC8AFB604FA917FDAFF810730B6ED8275393DC`。Contract最终Bytes/hash外部交回，不在自身写hash。租约20保护全部保持：用户偏好、3个资产、5个Config、D12-B Source两源、D7两源、D11共享头、D8/D9四源及Hero两源；并行Character L1两源不属本hash保持证据，其旧函数冻结由统筹安排，不用其新API。
- 架构核对：构造选择只决定夹具明确模式，通知计数/时间和Facts仅为原同步来源的测试观察，生命周期由本Probe/Fixture持有，均不成为生产资格/物理/执行权威。没有第二出生框架、资格状态机、来源发号器、执行门禁、循环依赖或业务兜底。只写授权3文件，未Build/UHT/UE/执行测试/Git/代理/资产/网络/dummy/Obsidian/全局入口；统筹独占进度和Input图文同步，本记录明确交回专项已实现、未编译/未运行及边界。

D13有限静态核对后三文件冻结停写。引擎Editor执行窗口是否提供真实重建帧、实际默认类出生、首次公开数字请求/资格消费顺序、释放再按及所有清理断言均未运行，不能预判Success；Cold实际退休或10秒无通知必须保留失败并交回具体阶段，不能降断言/改选项。InputKey注入不代表实体键盘、PIE、正常进入游戏的完整资产时序、Hero/CMC生产接线、正式Run、联机或移动根因关闭；Flush/Rebind/异常矩阵、跨Producer交接、dummy政策与既有严格Input/R0复现继续开放。

## D14 / 首次跨帧失效定位证据原子预检（2026-10-02）

统筹15:32登记证据租约，基线`Saved/ValidationRecords/InputD14NativeLossDiagnostics_LeaseBefore.json`；仅授权以下3文件，先记录本预检再写源码，不实施行为修复。

| 项目 | 唯一结果及边界 |
| --- | --- |
| 精确3文件/基线 | `F:\ue_project\GGYGO\Source\GGYGO\Input\Tests\GGYGOInputTestTypes.cpp`39871 bytes/`AC9702613C9E5441D91CE81651FC8AFB604FA917FDAFF810730B6ED8275393DC`；`F:\ue_project\GGYGO\Source\GGYGO\Input\GGYGOMovementInputOriginResource.cpp`18469 bytes/`F18A2C44EB6B44489B3A9C641C9E9C8A9FF9D71A5AF6A6E500EC909C07EE9F9F`；本Contract100242 bytes/`C951C28CB1389E274DEA00131472463D09C5D7961286ED0714D6A7ABBB192A5F` |
| 唯一结果/所有权 | 定位第一次资格失效属于实际退休还是原关系/寿命失效，并关联首次入口。D7状态及原写入顺序不改；测试只保存原weak诊断快照，不新增强引用、资格阶段、生命周期、策略或公开API |
| 输入/输出 | 初始化完成及原CheckCold失败前记录原weak有效性/flags、实际GetQualification、LP-PC/原Input槽/原subsystem路线、WorldContext、实际重建通知计数和GFrameCounter。仅Verbose纯日志，原Error/Warning和断言保持，不从阶段标签猜通知未到 |
| 唯一退休证据 | 只在既有SealInitialQualification的FirstRetirementReason空分支捕获原原因/阶段/登记/创建范围/生命周期纯值；完成原Reason及Stage写入后保存实际AfterStage，再输出首次Verbose及调用栈。复用原记录识别首次，不新增标志/计时器/每帧日志；栈格式化及输出后不再访问对象字段 |
| 冻结/并发 | 原Test h、Origin h、Source两源、D8/D9四源、Hero两源、共享头、Engine/Input配置共13依赖及九项目保护只读。Character另授当前槽纯Getter两源，旧及L1 R1方法冻结，本批不调用其新API，不声明对其全文件hash保持 |
| 顺序/非目标/停止 | 预检→测试原weak采集/有限快照→Origin唯一首退日志→有限静态/保护→源码hash和三文件冻结。不得改检查顺序/条件、latent期限/返回、默认注册/Setup/Rebuild选项、业务或状态写入；不补Cold、释放再认领、手工Tick/假通知/强制重建。第四文件/更多生产插桩/强引用/行为需求立即停；无Build/UHT/UE/Git/资产/Obsidian/全局/代理权限 |

### 两次Gate50真实红与当前已知/未知

- Gate50完整Editor实际Succeeded，8 actions/18.23秒/exit0，D13及Character L1 R1进入新DLL。独立`Saved/AutomationReports/InputD13NativeBirth_20261002_50/index.json`为0 Success/1 Fail，0.08698040246963501秒，1 Error/1 Warning；全量`Saved/AutomationReports/ModuleRepairGate_20261002_50/index.json`为82 Success/2 Fail，其中同一NativeBirthFirstDigitalPress叶0.06360580027103424秒，1 Error/1 Warning，同样的首个latent CheckCold错误和清理Warning。另一Fail不属于本定位原子，不改其断言。
- 两次错误均精确Stage=waiting for actual first rebuild notification；独立Producer在/Temp/Untitled_1，全量在/Temp/Untitled_110，Resource均为原项目LP持有的MovementInputOriginResource。初始化内Cold检查已通过，首个Update失败，尚未Begin/Attach或注入W，也不是10秒超时。独立日志帧599初始化、600清理，仅证明跨过一帧，不证明输入模块已实际重建。
- CheckCold将Producer/Resource无效与Qualification非Cold合并报错，未给实际枚举/flags/关系或通知计数；其调用位于通知检查之前，阶段文字不能当作“通知未到”证据。D7的Unavailable可由生命周期/登记/Controller-LP互指/原Input槽或创建范围失效导致；Rearm才代表原阶段Consumed/Retired，不把两者混称退休。
- 清理Warning是原弱PlayerInput无效或原subsystem查询不再返回它，出现在夹具自己销毁Controller/LP/World之前；单纯Flush且原关系仍完整不足以解释该Warning。现有日志没有首次退休入口或精确关系快照，不能认定Flush、GC、Controller销毁或缺游戏帧为真实原因。本批先补证据，保留两次失败，正确修复须诊断后另授。

### D14实现、有限静态证据与冻结交回

- 测试仅在本文件增加普通弱诊断值（weak身份及初始化路径），不新增UCLASS/公开接口。原LP、GI、Producer、Resource、PC、Pawn、subsystem和World身份只在成功初始化结束前采集一次，不在跨帧刷新为继任对象。原CheckCold仍在原位置执行一次，保存原结果后记录初始化完成快照；原失败条件/错误文字保持，失败快照在原AddError及Update清理前输出。等待Update、10秒期限、通知注册/真实计数/首时间、原生Setup、数字断言、清理及所有其它原方法逐字不变。
- 快照仅在LogGGYGONativeBirthDiagnostics Verbose启用时读取：原weak的Null/Valid/Stale、实际可解析对象的ObjectFlags/InternalFlags及FlagsKnown、实际GetQualification、LP.PC/PC.LP/PC.PlayerInput/原subsystem.PlayerInput/LP.OriginResource/Resource.Outer/Producer.Outer与原weak身份是否同一、实际Engine WorldContext及GI当前context是否同一、原观察者的实际重建通知计数/首时间、GFrameCounter。正常weak Get才读取关系；GetEvenIfUnreachable只经index/serial解析后读flags，不读取无效对象的路由；无法读取明确标为NotReadable/NotQueried，flags未知时FlagsKnown=0，不能把数值0当成已知flags。所有输出参数先采集为局部值，UE_LOG后不再读UObject字段。
- Origin只改既有SealInitialQualification：在原FirstRetirementReason.IsNone分支且原LogGGYGOMovementInputOrigin Verbose启用时捕获Frame/Reason/BeforeStage/原登记weak有效性与stale/创建范围/Claim编号/生命周期值，随后仍先写FirstRetirementReason=Reason，再按原Consumed判断写Retired。原写入完成后保存实际AfterStage，然后格式化调用栈并输出一次Verbose，栈格式化与UE_LOG后没有对象字段访问。阶段数值按既有枚举为0 Unavailable、1 Available、2 Claimed、3 Consumed、4 Retired；不从条件推算AfterStage。没有新生产持久标志、计时器、资格策略、授权或每帧日志。原Reason为空的语义和Consumed不被改写的语义保持，首次识别复用原记录。
- 有限静态：测试cpp907行，Origin cpp462行。内存移除新增include/category、弱诊断值/字段和快照方法，并恢复Probe.Initialize/CheckCold的诊断增量后，测试cpp全文准确还原D14写前；Origin移除两include并恢复唯一Seal方法后全文准确还原写前。因此原latent Update、RunDigitalAssertions、Cleanup、旧叶和其它生产函数保持。强引用声明16→16、Reset调用25→25、Pin调用0、AddError调用10→10；两源码去注释/字符串后花括号与圆括号净差各0，尾随空白和冲突标记0；新增日志仅2处Verbose，无新Error/Warning。原FirstRetirementReason/Stage写入内容、先后及守卫逐字保持。
- 13冻结依赖与9项目保护条目全部SHA256保持（Engine/Input配置各重复一次，共20唯一文件）；Test h保持6439 bytes/`6AC84B073797498A6252D5906A7ED6140002AAE103582A833AFD2AF0FB52AA9B`。Character另授两源不属于本全文hash保持证明，本批没有使用新槽Getter或修改其文件。
- 源码冻结SHA256：测试cpp46752 bytes/`4C51DCB78D2DB1893F6EBA1231AF8140AF6F6ABF9E77AF7438E94B8C3448F29B`；Origin cpp20454 bytes/`8D804B875D11D7F377B3A574FFA53904A38E34D6C786AFC01766F31CD79E38EF`。本Contract最终hash由交回时外部计算，不将自身hash递归写入。
- 架构核对：新增信息仅为弱观察及日志局部值，不形成生产资格/物理Held/发号/执行权威，无强引用环、第二调度器、循环依赖、公开内部状态或业务兜底；清理路径与原断言保持。只写租约3文件，无Build/UHT/UE/测试执行/Git/资产/Obsidian/全局入口/代理；统筹独占进度及Input图文同步。本批为证据实现，不是行为修复，不将Gate50已编译/已失败倒写成D14已验证。

统筹复现须在原生出生之前启用两个Verbose类别，例如启动参数`-LogCmds="LogGGYGONativeBirthDiagnostics Verbose,LogGGYGOMovementInputOrigin Verbose"`，再运行原独立叶及全量严格场景，关联初始化快照、首个失败快照和首次Seal栈的帧/原身份。后开的日志不会补发已记录的首次原因；清理后的首退日志必须与失败前快照区分，不能把清理入口冒认为失效根因。D14未编译/未运行，仍须保留Gate50两次真实红；实际Unavailable/Rearm、flags/关系变化、首次入口及引擎实际通知计数尚无运行结论。诊断后正确修复须另授，禁止补Cold、释放再认领、手工Tick、假通知、强制重建或降断言。有限核对后三文件冻结停写，等待统筹统一编译与原问题复现。

## D15 / Native真实隐藏窗口生命周期原子预检（2026-10-02）

统筹接受只读候选并授权基线`Saved/ValidationRecords/InputD15NativeViewport_LeaseBefore.json`对应三文件；先登记本预检再写源码。唯一目标是原Native夹具具有实际窗口、Viewport及清理责任，不改生产Cold政策。

| 项目 | 本步契约 |
| --- | --- |
| 唯一所有者/精确3文件 | Input长期组长直接执行，无代理；TestTypes.h 6439 bytes/`6AC84B073797498A6252D5906A7ED6140002AAE103582A833AFD2AF0FB52AA9B`；TestTypes.cpp 46752 bytes/`4C51DCB78D2DB1893F6EBA1231AF8140AF6F6ABF9E77AF7438E94B8C3448F29B`；本Contract109487 bytes/`99B9BA449F287B4B4F66CD5D56444B75DC12A4EA37E89579E1CC437149859D16`。路径分别为Source/GGYGO/Input/Tests/GGYGOInputTestTypes.h、同目录cpp、AAADocs/Architecture/Interactions/Module_Repair_MovementInput_Contract.md |
| 职责/输入输出 | 现有FState唯一持有自有SWindow、SViewport及FSceneViewport共享资源；Native分支在原Viewport.Init后、LP创建前建立实际隐藏原生窗口、CreateViewport关联/非零尺寸并RegisterViewport。引擎管理自己的注册引用，夹具负责精确Unregister及释放；不新增PC/Source强引用、生产状态或公开接口 |
| 顺序 | 基线及预检→Native创建和失败清理→h只修实际说明→有限静态及保护→证据和三文件冻结。旧无窗口默认分支保持；原出生、Hero首次安装、数字/Cold/10秒/全局World-Viewport归还断言保持 |
| 清理唯一责任 | 保留Probe原End、夹具Hero/LP/Controller释放；World销毁前注销SceneViewport，释放以执行原生Destroy/RemoveAssociation，再销毁自有隐藏窗口、释放Widget。初始化失败走同一幂等清理，客户端/World尚有效时断开关联，无窗口/注册/渲染引用遗留 |
| 只读依赖/互斥 | 生产Origin两源、Source两源、LP/PC四源、Hero两源、共享Types及Engine/Input配置冻结；Build.cs无租约，Engine公共依赖已有Slate/SlateCore。14冻结依赖与9保护条目共21唯一文件写前hash保持；Character与Movement另授范围不参与、不声明对其并行文件全文hash保持 |
| 非目标/停止点 | 不写第四文件/Build.cs，不改CleanupGameViewport、生产资格/物理Held、过滤标志、WorldType、重建选项、手工Tick/Broadcast/Immediate rebuild或断言。不伪造指针、不强化PC/Source生命期；任何需扩范围/PIE驱动/UE操作立即停止交回。无Build/UHT/UE/Git/资产/Obsidian/全局入口/其它会话/代理权限 |

### 已复核Gate51原因及游戏帧边界

Gate51独立实际新DLL为0 Success/1 Fail、1 Error/1 Warning、1.2887299060821533秒，尚未Begin/Attach/W。实际日志InputD14NativeDiagnostics_20261002_51_Runtime.log帧600原关系均有效/Cold/真实Rebuild0；帧601失败前首次Seal Reason=PlayerRemoved、LifecycleActive=0、RegisteredPC stale，栈为NotifyPlayerRemoved→项目LP.PlayerRemoved→UGameInstance.RemoveLocalPlayer→UGameInstance.CleanupGameViewport→UEngine.CleanupGameViewport→UEditorEngine.Tick。随后Qualification=Unavailable、PC stale、subsystem.PlayerInput=null，Source/Resource/GI/World仍有效。首退并非夹具清理、Flush或资格消费。GameInstance.cpp1242按Player.ViewportClient存在而Viewport为空移除LP，EditorEngine1777每帧执行该清理。本步修正真实Viewport前置条件，保留原问题失败证据。

已读UE5.8当前CreateViewport→FSceneViewport.Create→SetViewportClient/AddAssociation和析构Destroy/RemoveAssociation；SetViewport/SetViewportFrame旧setter已弃用且本步禁止。RegisterViewport/UnregisterViewport成对管理引擎实际注册，SWindow经AddWindow(false)创建隐藏原生窗口，尺寸/关联/OS句柄无效明确失败，不当作已建立。Engine.Build.cs公共依赖已含Slate/SlateCore，不扩Build.cs。

普通非PIE Editor在EditorEngine1958/2219传ViewportsOnly或TimeOnly；EnhancedInputModule继承IsTickableInEditor=false、World=null，因此FTickableGameObject门禁不会给该模块游戏帧。真实PIE分支2174及GameEngine1973提供LEVELTICK_All，模块Tick298才执行实际Rebuild和通知。本步不编写PIE驱动框架；统筹在全部源码冻结后安排真实PIE运行原EditorContext叶，不改过滤标志隐藏原红。窗口建好不代表专项Success，正式Run/网络/实体设备不属于本轮。

### D15实现、生命周期与有限静态交回

- Test h仅修正测试Viewport说明：显式Native模式拥有真实隐藏窗口，已有Player focus/layout通知抑制保持；声明/成员/方法体/生成接口全部不变。cpp仅增加WITH_DEV_AUTOMATION_TESTS内四个Slate/SceneViewport include、既有FState内三个共享资源、Initialize的Native创建块、Shutdown的对称释放块及旧无窗口说明更新，无新UCLASS/公开方法。
- 在原Viewport.Init后、LP创建前，严格确认实际Slate与renderer，再创建自有SViewport及64×64固定配置的SWindow，AddWindow(false)且FocusWhenFirstShown(false)。真实native window/OS句柄无效或窗口非隐藏直接失败；CreateViewport按当前Engine接口设置实际Slate interface及AddAssociation，不直接填Viewport、不用Deprecated setter。SetViewportSize后严格核对客户端返回的SceneViewport、Widget、Window均为本夹具对象、实际GetSizeXY精确64×64，再RegisterViewport，之后进入逐字保持的原LP/PC/Source出生流程。64×64为明确测试配置，不是错误触发的替代速度/动作/业务模式。
- 既有FState唯一持有NativeWindow、NativeViewportWidget、NativeSceneViewport；引擎Register持有其正常渲染注册引用，SceneViewport通过Engine规定的client关系持有ViewportClient，不新增PC/Source强引用。Widget的interface及SceneViewport的Widget关系按Engine弱引用契约，无新强引用环或生产生命期权威。
- Probe原撤观察/End及Fixture原Hero/Pawn/LP/Controller清理不变。原LocalPlayer.Reset后、World.DestroyWorld前，若本SceneViewport已创建则精确UnregisterViewport再Reset；析构执行Destroy→RemoveAssociation、清客户端Viewport并释放/等待渲染资源。随后DestroyWindowImmediately仅请求本自有Window并执行原生窗口销毁，再Reset窗口与Widget，最后执行原World/context/Viewport/audio清理。初始化失败在注册前也走同一Shutdown，Engine Unregister对未登记对象原生幂等；没有另建清理器/事件或替代LP，所有新资源被部分成功状态覆盖，第二次Shutdown新句柄已空。
- 有限静态：h182行、cpp969行。h恢复唯一注释即全文准确还原D15写前；cpp移除四include块、三FState资源、新Native创建/清理块并恢复唯一说明即全文准确还原写前，证明其它函数、原Initialize出生/默认旧分支、原Shutdown执行、D13 Probe/数字断言/latent期限与返回、D14诊断均保持。强引用声明16→16、Pin调用0；Reset25→28，仅多三自有Slate资源释放；CreateViewport/Engine Register/Unregister各1，Deprecated setter0。创建/注册在原LP前，注销/释放在原World销毁前；去注释/字符串后h/cpp括号净差0，尾随空白/冲突标记0。默认旧路径不创建窗口，清理只面对三个空共享句柄。
- 14冻结依赖与9保护条目共21唯一文件SHA256全部保持，包括Origin cpp Gate51诊断20454 bytes/`8D804B875D11D7F377B3A574FFA53904A38E34D6C786AFC01766F31CD79E38EF`及Build.cs2614 bytes/`677F99C4CB6EE8FA3EB9B55A2A95AE12766E72B69C7CE474D5F7F914EE0E1A06`。不写Build.cs，不使用Character新接口，不参与Movement或Character并行范围。
- 源码冻结：Test h6487 bytes/`D66C8C3875F7796896B9F5FC72F533087485AD3086987908132F5F5795C1C85F`；cpp49824 bytes/`D8CF46750B15CD83B2ED043A4C27530FA512575C8929AFD95963DFFCCF46B72C`。本Contract最终SHA256交回时从外部计算，不递归写自身hash。
- 架构核对：只修夹具缺失的真实Viewport前置条件及自有资源生命周期；没有生产资格重授、PC强保活、第二帧调度器、状态机、循环依赖、内部状态公开或业务兜底。没有更改CleanupGameViewport、过滤标志、WorldType、Cold/数字/10秒/原全局World-Viewport归还断言，未手工Tick/Broadcast/Immediate rebuild。只写租约三文件，无Build/UHT/UE/测试执行/Git/资产/Obsidian/全局入口/其它会话/代理操作；进度及Input图文由统筹独占同步。

D15有限静态后已冻结停写，未编译/未运行。统筹须在所有源码作者冻结后统一构建，并在实际原生窗口可用、真实PIE提供LEVELTICK_All的环境运行原EditorContext专项：验证原LP/PC跨真实帧仍有效Cold、实际重建通知在原10秒期限内到达、原数字序列及资格消费/释放再按成立，所有新窗口/引擎注册/关联与原GI/World/context/audio资源归还。普通非PIE Editor若继续无实际通知，保留原10秒失败，不让窗口创建替代游戏帧。Gate50及Gate51原失败证据继续保留；本步不代表正式Run、网络、实体设备、资产接线或移动根因关闭。任何第四文件/PIE驱动/额外生命周期或生产契约需求先停止交回。

## D15-L / 显式Slate链接依赖补齐预检（2026-10-02）

统筹依据Gate52真实链接失败授权本两文件原子，先登记预检再修改规则；原D15窗口实现及全部h/cpp继续冻结。

| 项目 | 约束 |
| --- | --- |
| 精确两文件/基线 | Source/GGYGO/GGYGO.Build.cs 2614 bytes/`677F99C4CB6EE8FA3EB9B55A2A95AE12766E72B69C7CE474D5F7F914EE0E1A06`；本Contract118987 bytes/`20AD3C3F13FD680558D9730E200D0728D1032823A3FD7DF0F33FDAD0BFB955C4` |
| 唯一目标/归属 | GGYGO直接使用SWindow/SViewport/FSlateApplication，项目模块显式声明private Slate/SlateCore链接依赖；只是已冻结测试窗口实现的模块依赖补齐，无新业务或引擎修改 |
| 顺序/验收 | 原记录预检→既有PrivateDependencyModuleNames.AddRange加入两模块→核对无重复/无条件化、其余规则保持→记录实际增删/两hash/未验→两文件冻结。真正链接成功由统筹新编号统一重编证明，本步不等待编译 |
| 非目标/停止点 | 不修改任何h/cpp、Fixture、Cold/数字/10秒/清理断言、UE/GAS、配置/资产、其他模块、全局/Obsidian/Git；不Build/UE、不代理、不重做首个真实Press或补资格。第三文件、条件化或新模块/构建抽象需求立即停止交回 |

Gate52日志`Saved/Logs/ModuleRepairBuildGate_20261002_52_UBT.log` SHA256=`FAFF613C4F33633A283D4CFB92BE55625483D653995A9FC506B9BD8838936A3E`。五个runtime unity TU编译完成、lib成功，DLL链接LNK2019及LNK1120共21个Slate/SlateCore未解析符号，Result=Failed(OtherCompilationError)、exit6、24.50秒；未生成本轮成功的新DLL。统筹与Input组长此前把Engine公共依赖的编译可见性当成项目直接链接保证，判断错误；D15“不需Build.cs”的结论由此纠正，原失败保留，不将编译TU/lib成功记成DLL构建通过。直接使用的模块须显式声明。使用无条件private依赖，不猜测editor-only等比WITH_DEV_AUTOMATION_TESTS更窄的条件，以免非Editor Development保留链接缺口。

### D15-L实现、有限静态与冻结交回

- 既有PrivateDependencyModuleNames.AddRange中无条件新增Slate及SlateCore各一次，增加一行说明；移除已过时的两行“Uncomment Slate”模板注释。规则文件准确+3/-2行、净+1行，不改其它依赖、AutomationController的原Editor门禁、Iris或任何Target条件。
- 内存移除新增三行并恢复原两行注释后，Build.cs全文准确还原写前；Slate/SlateCore各唯一一项，未新增条件、新模块或抽象。显式private依赖匹配当前cpp直接使用的模块，不修改公共接口或增加生产循环依赖。原h/cpp及D15窗口、D14诊断全部未写，Test h、Test cpp、Origin cpp分别保持`D66C8C3875F7796896B9F5FC72F533087485AD3086987908132F5F5795C1C85F`、`D8CF46750B15CD83B2ED043A4C27530FA512575C8929AFD95963DFFCCF46B72C`、`8D804B875D11D7F377B3A574FFA53904A38E34D6C786AFC01766F31CD79E38EF`。
- Build.cs2624 bytes/SHA256=`CB7C58EB6D5BBE7ADD60696816E4E3EBB1F418301B100D068AF09E9B81516151`；Contract最终hash从外部计算。文档仅更新最新状态与追加本预检/根因/证据，D15历史批次原错误结论保留并由Gate52明确纠正，未隐藏失败。
- 只写授权两文件，未Build/UE/Git/配置/资产/其它模块/全局/Obsidian/代理，未修改Cold政策或重复实现首个真实Press。两文件有限核对后立即冻结停写，不等待编译、不继续其它修复。Gate52失败保留；规则补齐未重编，链接成功须统筹下一编号统一构建证明，真实PIE出生/实际重建/数字/生命周期验收仍未运行，本步不预判通过。

## D16 / 原首按叶自有真实InProcess PIE生命周期预检（2026-10-02）

统筹登记`Saved/ValidationRecords/InputD16OwnedPIE_LeaseBefore.json`并授权唯一三文件；Input长期组长直接完成，不使用代理，先记本预检再实现。唯一目标是原叶自动化准备后真实游戏帧环境，不改冷启动/异常恢复规则。

| 项目 | 唯一结果及边界 |
| --- | --- |
| 精确三文件/基线 | Source/GGYGO/Input/Tests/GGYGOInputTestTypes.cpp49824 bytes/`D8CF46750B15CD83B2ED043A4C27530FA512575C8929AFD95963DFFCCF46B72C`；Source/GGYGO/GGYGO.Build.cs2624 bytes/`CB7C58EB6D5BBE7ADD60696816E4E3EBB1F418301B100D068AF09E9B81516151`；本Contract122878 bytes/`DF53FBD46F255ECD673815216FA1FAAADBB1D3219C644D293235F4B2F5136387` |
| 职责/依赖 | 引擎唯一驱动真实PIE与游戏帧。新测试作用域仅持有瞬态启动设置、原生请求复制设置身份、自有ContextHandle/World/GI弱观察、原Probe/等待及自有委托句柄。UnrealEd直接private依赖仅editor-target，新调用WITH_EDITOR保护，已有Slate/其它依赖保持；14依赖+九保护共21唯一文件写前hash保持 |
| 明确配置/归属 | 启动前显式正常配置为InProcess真实PIE、单Standalone实例、GameModeOverride=AGameModeBase；不改保存地图/生产资产，不因坏Profile切模式。拒绝已有/排队/正在建立的PIE，不从任意game world推断自有ready；观察真实PostPIEStarted及准确Context/World/GI和就绪 |
| 顺序/期限 | 原记录→作用域与RunTest外层编排→editor依赖→静态/保护→diff/hash/未验→冻结。准备完成后原生RequestPlaySession，真实就绪后创建原Probe并原样Initialize/等待。启动及结束各独立10秒；原重建10秒截止、Fixture/Probe/等待主体、Cold/digital/global清理断言、路径/flags冻结 |
| 清理/失败 | 原Probe清理后仅结束自有PIE，有限等Context消失及外层Global归还；失败/提前终止/替换/超时/中途退出均明确Fail，撤自有事件、取消准确自有排队或结束准确自有会话。不得结束继任/外来会话；不能原生精确表达清理时停交回 |
| 验收/非目标/停止 | 真实PIE等待期间存活，原subsystem真实通知及原数字/清理断言通过才成立。无Build/UE/Git/配置/资产/其它模块/全局/Obsidian/代理权限；禁止手工Tick/Broadcast/Immediate重建、引擎/bKeepPIEOpen/框架状态/WorldType手写、补资格或降断言。第四文件、资产/生产接口或额外框架机制需求立即停止 |

Gate53 D15-L实际新DLL构建Succeeded，8 actions/18.67秒/exit0；全量83 Success/2 Fail，原84状态保持。NullRHI在OS窗口前置Fail1 Error/0 Warning，尚未LP；SlateApplication2043只有CanEverRender才创建真实原生窗。真实渲染独立通过窗口及全部前置、原Cold跨帧保持，11.4258108秒后原10秒无真实重建通知Fail，首退只来自Probe清理；报告`0D3F45076D11F26AD3B988904E030DB6F94BE0CD7C84F139A081A6B24F75EB33`、日志`76268BC0AF3B8929AD823344B70416591E1E725DC4D67C19AF24BE5A342064C0`。

预先PIE运行报告`D606005CEC621DA43C5ABCC1C60A83C3C75424096A8AAA7B1C9920FEE74E53B6`、日志`354FA62BC1346104D1A7D484DED809A4097F51A894CD23D56B76461A5C8D8C5F`：PIE在Worker进原叶前结束，仍10秒无通知Fail。源码为AutomationCommandline409先StopTests→AutomationControllerManager483–485在bKeepPIEOpen=false时RequestEndPlayMap→EditorEngine2463/2507执行EndPlayMap；随后Worker699→StartTestByName→PrepForAutomationTests→InternalStartTest→原RunTest。CB_PreAutomationTesting只关闭源码控制。预先存在过PIE不证明等待期间有游戏帧，本步不改框架清理政策。

真实PIE LEVELTICK_All让EnhancedInputModule原生Tick遍历所有LocalPlayer子系统（包括原Fixture）并实际重建/通知，不手工驱动。已有正式WalkStartProfile缺失仍为资产未迁移，不因本测试隔离配置宣称修复；首W/Run/网络仍未闭合。

## D16 / 三文件实现、有限静态证据及冻结交回（2026-10-02）

- 状态：三文件实现和本记录完成，Input组长冻结停写；未Build/UHT/UE/Git或派代理。Gate53仍是上一版动态结果，D16尚无新DLL或运行证据，原Fail没有被改为通过。
- Test cpp新增WITH_EDITOR局部作用域`FRunNativeMovementOriginWithOwnedPIE`及所需editor头；原叶RunTest只排入该作用域。原测试路径/EditorContext|EngineFilter保持，非editor明确Error，不走旧夹具或伪造成功。
- 作用域Start拒绝已有/排队/建立中PIE与现存PIE Context。瞬态私有ULevelEditorPlaySettings启动前选择单Standalone/同进程/无单独server、真实PlayInEditor及AGameModeBase；原生RequestPlaySession复制配置后的实际设置对象身份用于归属核对。此配置是明确正常测试模式，不是生产Profile失败后的替代，不写CDO/SaveConfig/正式地图/资产。
- 真实PreBeginPIE必须对应准确排队设置；真实PostPIEStarted必须对应准确原生session、非Simulate、唯一PIE Context与有效World/GI。随后逐次确认同ContextHandle、同World/GI及Editor.PlayWorld，不从其它game world或名称推断身份；ActorsInitialized/BeginPlay/准确GameModeBase/GameState MatchStarted后才原样Initialize Probe。
- 启动10秒截止先于ready接受检查。Running仅调用原`FWaitForNativeMovementOriginRebuild::Update`，其原10秒截止、实际Notify计数/时间、Cold、数字Release/Press和所有原清理断言不变；PIE真实游戏帧及EnhancedInput原生模块执行属于引擎。
- 正常完成先原Probe清理，再准确自有RequestEndPlayMap，独立结束10秒内观察session/Context消失与外层Global World/Viewport恢复。丢弃latent command或结束超时会明确Fail并通过准确自有EndPlayMap同步释放；超时不因随后清理成功变成业务成功。尚排队的请求只按实际复制设置身份CancelRequestPlaySession。
- 提前结束、启动取消、Context/World/GI替换、启动/结束超时均有Input.OwnedPIETest阶段/Context/对象诊断；不结束继任或外来会话。存在外来Context时拒绝全局PIE结束并保留失败、残留断言；清理若无EditorEngine也明确失败，不把缺失依赖当作已归还。
- 四个真实引擎观察句柄PreBeginPIE/PostPIEStarted/EndPIE/CancelPIE在正常结束及析构路径均Remove并Reset。新持有的editor/settings/world/GI为weak观察；唯一新增Strong只用于启动配置的短期保活，不强持LP/PC/Source/Origin。外层World/Viewport原始指针仅作归还相等性观察。
- 有限静态核对：Test cpp准确+353/-3行、969→1319行，移除新增include/作用域并恢复唯一RunTest后全文准确还原写前；原Fixture、FNativeMovementOriginProbe、原Wait主体、其它叶保持。Strong出现16→17且唯一新增为editor启动设置；新增4观察/4移除，手工Tick/Broadcast、WorldType赋值、新UCLASS/公开头及Source pin均0；括号/花括号平衡，cpp尾随空白及冲突标记0。
- Build.cs仅既有Target.bBuildEditor块新增说明和private UnrealEd各一行，准确+2/-0、72→74行；WITH_EDITOR保护匹配新代码。移除两行全文准确还原写前，原Slate/SlateCore和其它规则保持。尾随空白仍为写前两行，无新增；没有将UnrealEd加到Game/Shipping目标。
- 最终源码证据：Test cpp61954 bytes/SHA256=`EAFCFF1D3F6C48726638674B9AA3A47AF86B4D886D09A2284B2CD2367D7D225E`；Build.cs2751 bytes/SHA256=`0ABDF68D6C0420AD8339782E73FC70D817885C1AB4C221E9E2A84270707FFAF6`。Contract最终字节/diff/hash从外部交回，不在文档内写自身hash。
- 保护证据：14冻结依赖加九项目保护共21唯一文件，写前/写后SHA256及已记录字节全部保持；其中Test h=`D66C8C3875F7796896B9F5FC72F533087485AD3086987908132F5F5795C1C85F`，Origin cpp=`8D804B875D11D7F377B3A574FFA53904A38E34D6C786AFC01766F31CD79E38EF`。只写授权三文件，无生产接口/资格/策略/配置/资产改动。
- 架构核对：新增仅原专项测试资源作用域，原自动化latent调度和引擎游戏帧唯一；原Probe继续唯一负责夹具/来源生命周期，PIE作用域负责自有原生请求/会话与观察者，没有重复来源事实、生产执行器或跨模块循环依赖。未新增业务兜底、第二套帧调度器或框架状态修改，不改bKeepPIEOpen。
- 待统筹：统一构建验证UnrealEd直接链接及WITH_EDITOR API，再用真实渲染运行原叶，保留原严格失败复现和原10秒通知/Cold/数字/清理断言，并验证启动失败/提前结束/超时/丢弃路径与无PIE/global泄漏；全量回归、正式WalkStartProfile资产缺口、首W/Run/联机仍独立未闭合。全局进度/Obsidian由统筹接收本测试环境流程变化后同步，本三文件租约禁止组长写入这些入口。

## Input-Hero-IdentityPrepare / 三文件原子预检（2026-10-03）

统筹已接受澄清预检并在排程/ledger登记唯一Input组长租约；写前读取`Saved/ValidationRecords/InputHeroIdentityPreparation_LeaseBefore.json`，三文件hash/bytes、Hero两源完整规范化文本、257源码及九保护hash全部匹配。组长直接执行，本批模型/档位沿租约gpt-6.1-sol/xhigh，不使用代理。

| 项目 | 唯一结果与边界 |
| --- | --- |
| 精确文件/基线 | Hero.h9990 bytes/`AF921B89AA8F665D6F8EF9ED2AF9A5D576AE8252AEC650D072DEEB4D24F5CC91`；Hero.cpp31875 bytes/`FEC79B605C4B58A9EEABAC595A4CE53FFC4BC01D55A143535516D2B5B1EACD81`；本Contract132331 bytes/`62447F2CEAFEF34F4B3DBA075614284D9CDF0A7D39485B88FB65B7526FB6B8A8`。完整源码路径为Source/GGYGO/Character/Components/GGYGOHeroComponent.h/.cpp，本记录路径保持 |
| 唯一目标/职责 | Hero新增原Extension订阅准备记录：真实NoticeHandle、原Pawn/Extension弱身份、已消费原opaque Resource及可空原InputSessionGeneration/InputComponent派生关联。L1唯一管理Resource/Ready/发布，ASC唯一Binding和输入权威；新记录不拥有实际输入/IMC/Camera，不发行任何新序号 |
| 冻结方法 | PrepareLocalAbilitySystemSubscription(Extension, OutError)、GetReadyLocalAbilitySystemComponent() const、ReleaseLocalAbilitySystemSubscription()、ConsumeLocalAbilitySystemNotice(ExpectedSubscription, Notice)、AssociateInputSessionWithLocalResource(ExpectedResource, ExpectedInputSessionGeneration, OutError)，签名按已交回预检不变 |
| 顺序/依赖 | 本预检→h仅include/声明→cpp尾部原记录与五方法→有限逆向/调用/清理/保护核对→本记录实际证据和外部hash→三文件冻结。只读L1 Resource/Notice/RegisterAndCall/Unregister/Ready及ASC现有publication查询；无新跨模块签名 |
| 同步/身份契约 | RegisterAndCall前发布原记录，回调捕获原记录；原栈持有晚返回Handle责任，原记录退役后只还原Handle。Ready认证原Resource/Binding/真实PublishedContext和L1查询，注册成功不证明Ready；不同opaque即同ASC/Pawn也不替换收养，同Resource Refresh/重复Ready不重装 |
| 清理准确边界 | 匹配Released只摘原已消费Resource及派生输入关联；同一Notice订阅仍由原记录持有直至显式退休。退休先封本记录再归还其NoticeHandle，正常/迟到返回/析构均幂等。两路径绝不调用ReleasePlayerInput/UnbindAbilityRetryDelegates/ClearAbilityInput，不清实际Input/IMC/Camera，也不改变InputSessionGeneration；返回成功不证明真实输入已清 |
| 保持/非目标 | 所有旧生产方法全文保持，新增方法无既有生产调用；不接BeginPlay/EndPlay/InitState/装配/ASC retry/Input/Camera，不动Source/CMC/ASC/Extension/Host及共享权威。无测试/Build/UHT/UE/Git/引擎/GAS库/资产/网络/Saved/全局/Obsidian写权 |
| 验收/停止 | 核对原记录先发布、晚Handle独占、原Resource/关联匹配、Refresh无副作用、退休幂等、零真实清理及整源逆向保持。第四文件/新权威/新政策/共享签名即停止；有限交回后冻结。生产清理需原Resource/Binding+input generation精确权限，Host/Character/各消费者同新DLL/新World门禁另授，Movement E1未编译不能运行半链 |

本批是准备接口实现，新增方法尚不证明生产Ready/Released接线、真实输入清理或首次W。Gate54已有原生出生公开数字输入专项成功保持为其原验证边界，不覆盖本批未编译代码；生产Source→CMC装配、正式Hero/资产/Run/网络继续开放。

## Input-Hero-IdentityPrepare / 实现、有限静态证据及冻结交回（2026-10-03）

- 三文件准备实现完成并冻结；新增五方法均仅准备/派生查询/关联，未接旧BeginPlay/EndPlay/InitState/Initialize/Release/ASC retry/Input/Camera生产路径。本批未编译、未动态验收、无新测试文件，不把Gate54原DLL结果当作本批代码通过。
- 新原记录只保存const Extension/Pawn弱身份、实际NoticeHandle、原Resource、可空AssociatedInputSessionGeneration/原InputComponent弱身份和bRetired资源寿命标记。Resource由Extension原opaque句柄持有，不复制或新建Ready/Binding/输入held/执行状态；实际bind/IMC及InputSessionGeneration仍在旧Hero唯一归属中。
- Prepare写入原记录后才调用真实RegisterLocalAbilitySystemNoticeAndCall，弱委托捕获原Hero和原记录，栈强记录覆盖同步回放与Handle返回窗口。AcceptReturnedHandle只交给原记录，已退役时精确注销该晚Handle；后继已安装时不调用无参清理后继。Prepare成功只证明原订阅仍有效，不证明有Resource/Ready或输入装配完成。
- Ready核对真实L1原Resource Ready、原Pawn/Extension/ASC、Binding及当前PublishedContext才消费；已占另一opaque即同ASC/Pawn也明确拒绝。Refreshed必须已经消费同opaque，重复Ready和Refresh都不改变关联/输入代数，不重装映射；没有从当前槽Getter推断或收养资源。
- 匹配Released先清原已消费Resource及派生input generation/component关联，保留同一原Notice订阅直到显式退役；旧/异Resource不改记录。Release准备入口先摘Hero的原订阅槽，再Retire只封本记录/归还其Handle；析构同样幂等。失效ASC/Pawn不阻止匹配历史Released的本地关联清理，失效Extension不冒称真实输入已清。
- Getter每次查询同一原Resource当前L1 Ready和原Owner身份；无Resource/未Ready/过期/退休/结束中的Hero返回空，仅表示无当前来源。Associate只核对原Resource和现有InputSessionGeneration/InputComponent及既有输入会话查询后保存派生关联；同一代数不得换原组件，过时代数/异opaque明确失败。它不发代数、不保存实际绑定句柄、也不授真实输入清理权。
- 有限静态：Hero.h准确+30/-0、229→259行；Hero.cpp准确+303/-0、843→1146行。删除唯一新增include/forward/declarations/实现标记块及新增分隔空行后，两源原始全文和租约规范化全文均精确恢复写前；所以全部旧生产方法、成员和调用点保持。
- 五冻结方法每个定义一处，原Hero全文中五方法调用均0；新块真实Register调用1处，Unregister仅正常退役/晚Handle归还两处。新块调用ReleasePlayerInput/UnbindAbilityRetryDelegates/ClearAbilityInput/InitializePlayerInput/BindAbilityRetryDelegates/IMC/Camera/Tick/Broadcast均0，对旧InputSessionGeneration/Component/Subsystem/PlayerInput/bind/mapping/ASC/Camera字段写入0；无UCLASS/USTRUCT/新公共共享协议。去注释/字面值后花括号与圆括号余额及最低余额均0，两源尾随空白/冲突标记0。
- 源码最终证据：Hero.h11489 bytes/SHA256=`65A14EDE292C9355FF357837D46A4760F44E8F077A5B9015FFFEC126059EDE06`；Hero.cpp45519 bytes/SHA256=`8CCA5796C37A39D843A63A9DAE8C37C80319F2ACCD31F76ED8D02AFCD569149C`。Contract最终bytes/diff/hash外部交回，不写自身hash。257源码与九保护写后只有授权Hero两源变化，其余255源码及九保护hash全部保持；无新增/删除源码文件。
- 架构核对：记录寿命与本地Resource消费分开，Handle和晚返回各只有原记录负责；没有原资源权威竞争、循环依赖、另发Binding/Ready事实、业务兜底或自动重试。资源清理只处理准备记录，真实输入、IMC、Camera和ASC输入清理未闭合，也未绕入已知旧整ASC.ClearAbilityInput路径。
- 后续门禁：旧EndPlay尚不调用新Release，生产身份消费/真实装配及原Resource/Binding+inputgeneration清理权限须另租约；Host/Character及各消费者需同新DLL/新World单链启用，不热迁移双订阅。同步回放退休/替换、晚Handle、不同opaque同ASC/Pawn、匹配/旧Released、Refresh及真实EndPlay动态断言均待统筹专项，不能由静态分支证明替代。
- 组长只写授权三文件；没有Build/UHT/UE/Git/Saved/测试/资产/引擎/其它模块/全局/Obsidian/代理操作。全局及Obsidian入口的准备状态同步交由统筹按其独占范围完成；此处交回新增准备类/接口和未启用边界，不自行扩大租约。


## Input-Hero-AbilityRequestConsumerA / 原来源停止点（2026-10-03）

### 授权步骤与写前登记

| 项目 | 本轮边界 |
| --- | --- |
| 唯一写入者与基线 | Input长期组长直接执行，无代理；统筹已接受A/B拆分，仅授权A。基线为 `Saved/ValidationRecords/InputHeroAbilityRequestConsumerA_LeaseBefore.json`；本记录登记先于任何源码修改 |
| 精确三文件 | `Source/GGYGO/Character/Components/GGYGOHeroComponent.h`、同名cpp及本记录；没有第四文件写权 |
| 唯一目标 | 首次真实Trigger先保存原观测及固定deadline；未Ready、Receive拒绝或非法InputBufferWindow也锁存无ID。持续Trigger、晚Ready或订阅重绑不补发；真实release仅End原ID Released，取消/解绑/失效仅逐原ID Invalidated；retry仅完整原ID/Tag/deadline，删除Hero全ClearASC |
| 模块与依赖 | Input拥有原物理观测与会话绑定来源；Hero只持原ASC发行ID、观测和有限retry资源；ASC独占held/Queued与既有Process消费。只消费冻结Receive/End/Queue、普通值类型及OneParam通知；ASC独立运行时写入不要求整文件hash保持 |
| 顺序与断言 | 核对三文件基线及租约→本记录登记原来源核对→能证明原观察/真实释放后才实施A→有限签名、失败锁存、原ID清理及重入检查→hash与未验证边界交回→冻结；不能证明原来源时在源码写前停止 |
| 非目标与停止 | B typed H/Source→CMC、IMC/Camera迁移、两旧诊断及夹具另租约；共享Producer、第四文件、新held/Ready权威、UE/Build/Git/资产/外部笔记/全局/Saved/测试矩阵/代理均无授权。原来源不可证明、共享接口变化或职责重复立即停止 |

### 已确认的阻断证据

- 三文件实物hash与租约完全一致。核对来源是当前项目源码与本机UE5.8源码，没有使用旧DLL运行结果，也没有要求ASC并行实现停止或保持hash。
- Hero能力回调 `Input_AbilityInputTagPressed/Released(FGameplayTag)`（h:147/150、cpp:587/612）只收到Tag。既有 `UGGYGOInputComponent::BindAbilityActions`（h:73～94）逐配置Action绑定Triggered/Completed，但传入的载荷只有Action.InputTag；InputConfig的AbilityInputActions数组没有禁止两个不同Action使用同Tag。旧 `TMap<FGameplayTag, double>`（Hero.h:217/219）因此不能作为原Observe身份：Action A先触发、Action B同Tag后触发、A完成时按Tag移除会误结束B仍持有的来源。
- Hero.cpp:396～403另把Canceled绑定到同一Released入口，注释称取消是真实release。UE `InputTriggers.h:30～55`明确定义事件为Action触发状态转换：Canceled是Ongoing→None，Completed是Triggered→None。它们不携带真实原Key/Device释放证据；本轮不得继续把Canceled伪造为ASC Released。
- 本机引擎反例可从源码直接推导：`F:/UE_5.8/Engine/Plugins/EnhancedInput/Source/EnhancedInput/Private/InputTriggers.cpp:160～164`中Pressed仅在本帧Actuated且上帧不Actuated时返回Triggered；同一键持续按住的下一帧返回None。`EnhancedPlayerInput.cpp:120～174`将Triggered→None映射到Completed。所以Completed不能普遍证明真实按键已释放；这是一条静态契约反例，未运行专项。
- 可在Hero租约内改用 `FInputActionInstance` 或显式Action载荷来区分不同Action，但仍不能获得完整物理证明。`InputAction.h:207～277`只保存SourceAction、动作触发状态/计时与所有映射的合并值；GetValue在非Triggered时归零，归零不能证明原物理源释放。`EnhancedInputComponent.h:23～33`的原生Action委托也没有Key/Device或真实释放标识。该修改只解决Action身份，无法关闭本次“真实release才End Released”契约。
- 既有 `UGGYGOPlayerInput::InputKey`（cpp:1164）确实观察原Key/Device，排除Simulated/Flush并在Super之后发布事实；`FlushPressedKeys`（cpp:1194）保留真实释放义务。其当前公开Session/Receiver协议只用于Movement，Begin限定Axis2D单Movement Action（cpp:210～219），原物理表为私有且没有能力动作观测端口。Hero不能直接读私表、借Movement Session作技能来源或自行再建原物理held表；扩Producer共享文件超出本步租约。

### 实际产物、后继建议与冻结

- 实际只更新本记录：写前边界、停止证据和未完成项。Hero.h/cpp零改动，原身份订阅准备块及全部旧生产结构保持；A没有部分启用。首次失败锁存、非法Window拒绝、完整ID retry、取消Invalidated与移除全ASC.ClearAbilityInput均尚未编码，不能标为完成。
- 停止原因属于输入来源契约缺口：当前动作事件缺原Observe身份及真实Release证明。Tag或动作当前值不能补证明，普通编译/冒烟也不能使错误的事件语义成立。冻结共享ASC接口已能表达原ID的接收和清理，本停点不要求改ASC权威/API。
- 建议统筹先安排一个有限只读预检，冻结技能输入观测的原来源/寿命/真实释放接缝：优先复用PlayerInput既有原Key/Device观察，明确Action聚合与触发器、模拟/Flush/映射失效的语义，只向Hero交付原观测身份及事实，不增加held执行器或帧调度器。具体接口、值字段、文件范围和是否需来源职责拆分须预检后确认；本轮没有批准或实施新的Producer方案。
- 后继原观测接口冻结并完成Producer后，再续租A三文件；B同文件装配、两诊断及必要夹具依次另租约。本次停止不能用Tag→ID适配、强制限制资产、Completed当release或Hero自行轮询来绕过，也不改原已批准目标/验证政策。
- 有限自查只核对实际接口/调用点、UE事件语义反例、原私有Source边界、两个Hero整文件hash与既有Contract历史精确保持。未Build/UHT/UE/动态/严格矩阵，无其它写入；外部笔记及全局状态由统筹按独占范围登记本停止点。Gate54历史证据保持原范围，旧消费者仍需整体迁移后统一编译和必要冒烟。
- 本记录及Hero两源交回后明确冻结；源码写权关闭，等待统筹的来源契约决定和后继租约。最终三文件hash/bytes在交回中提供，不在本记录写自身hash。


## Input-RawObservationSeparation / 三文件内部职责分离预检（2026-10-03）

| 项目 | 本步授权与写前登记 |
| --- | --- |
| 唯一作者/基线 | Input长期组长直接执行，gpt-6.1-sol / xhigh，无代理。基线 `Saved/ValidationRecords/InputRawObservationSeparation_LeaseBefore.json`；三实物hash已核对，先登记再写源码 |
| 精确三文件 | `Source/GGYGO/Input/GGYGOPlayerInput.h`、同名cpp及本记录；能力Action/注入语义仍待决定，未获得任何能力端口或Hero写权 |
| 唯一目标/归属 | PlayerInput仅有一份原生Key/Device表与ObservationRevision；原生观察保存raw/分量完整性/真实缺口及真实释放序列。Movement参与与恢复记录仅引用原Key/Device及序列，不复制raw/held。Movement End/Adopt只改自己的义务，不改原生事实 |
| 顺序/依赖 | 原生事实与Movement义务声明→原生观察/Movement投影分开→本地Barrier/Adopt/Read/Describe迁移→Flush明确原生缺口→有限自查/原范围保护→交回冻结。只读Movement值协议、OriginResource、CMC、UE InputKey/Flush/映射/输入栈 |
| 恢复断言 | 数字义务需边界后的原真实Released；模拟轴义务需全部必要原生分量都在边界后真实归零。原生表记录分量观察序列与完整归零证明，Movement只比较原释放证明，不自行缓存轴值/held/分量mask；模拟/重复/缺口不能补证明 |
| 保持/非目标 | Movement公开签名/事实Kind/Cold/FAILED/原资格及原会话精确清理保持；无新发号时钟/调度/重试/伪Released。无能力观察端口、Hero/ASC/CMC/Origin/共享值修改、第四文件、测试矩阵/夹具/UE/Build/Git/资产/Obsidian/全局/Saved写入 |
| 验收/停止 | 核对唯一raw与序列、纯Movement屏障零raw写、真实原生缺口保留、原源释放及重入权限；只修改约定私有数据/方法和相关原调用点。公共合同/Cold政策、原恢复义务不能保持或第四文件即停止；有限静态不是编译/动态通过 |


## Input-RawObservationSeparation / 实现、有限静态证据及冻结交回（2026-10-03）

- 授权三文件实现完成并冻结。只有PlayerInput私有观察/恢复实现变化，无能力公开端口、新Action规则或Hero迁移；本批未Build/UHT/UE/动态验收，不把Gate54原DLL成功用于证明新代码。
- 唯一FPhysicalSource表仍持原Key/Device、raw数字/轴值及原生完整性；新增原生缺口序列、真实释放完成序列、释放证明起始序列和各轴分量观察序列，全部取自唯一ObservationRevision，没有新计数器或时钟。数字释放的证明起止均为原IE_Released事件；完整轴归零的证明起始是所有必要分量观察序列的最小值。
- FMovementSourceObligation只保存原Key/Device引用值、派生参与标记、可空ReleaseAfterObservationRevision和原因，不保存raw/held/轴mask。屏障捕获原观察边界，只有原释放证明的起始序列严格晚于边界才满足恢复；因此轴不能用边界前一个分量的旧零值配上边界后另一个分量归零补证明。已满足记录的旧原因仅历史，查询不将它当当前缺口。
- EstablishMovementReleaseBarrier与Adopt仅只读原生表并修改Movement义务；Movement End、Begin拒绝及原资格退休沿原入口调用该屏障，不再写raw值、bUnproven、ObservedAxes或原生原因。旧未映射参与源仍保留义务到原真实释放；后映射的原源不能借屏障前neutral恢复。
- ObservePhysicalInput现在只观察原生事实与不可证明原因，完全不读取Movement映射/参与/恢复；同步FNativePhysicalObservation仅保存本次原Key/Device及真实边沿/释放的事实副本。ProjectMovementObservation按原映射与自身义务派生既有Before/After/边沿，不另持物理held。InputKey仍在Super之前记录原事实，Super之后只用原会话/原观察复核并交付，旧重入不能采用后来的观察。
- Flush在原资源退休后单独调用InvalidatePhysicalInputObservations，真实原生连续性缺口会重置原分量完整性并记录原因，但保留历史raw level；随后登记Movement义务、结束原会话，再走原Super Flush。模拟Key输入仍不分配原生观察或清释放义务。真实缺失边沿、未知设备、非法/合并轴样本和不完整向量仍拒绝证明；Producer销毁归还Movement后同时清其义务与唯一raw表。
- 有限静态：h 168→207行（+43/-4）；cpp 1256→1374行（+181/-63）。逆向13个准确修改块后两源原始全文精确恢复写前，公开/原生override声明除必要include外保持；PostInit、ReadRoute、ValidateCurrentRoute、Capture/Validate/Retire Origin、Begin、Attach、Issue、Publish、Deliver、End、GetRequest、UpdateRequest、Evaluate/Blocked共16原方法全文保持。
- 静态权威/语法核对：raw表1处、ObservationRevision计数器1处；旧混合bMovementParticipant/bRequiresRealRelease字段0处；Native观察中的Movement引用0、Barrier/Adopt/Projection原生字段写入0、恢复记录raw/held/轴mask字段0；原生缺口入口仅真实Flush调用1处。去注释/字面值后两源花括号/圆括号/方括号最终与最低余额均0，尾随空白及冲突标记0。
- 只作有限序列公式核对：数字真释放序列须晚于边界；2D归零只更新一个分量时最小证明序列仍可在边界前，全部分量更新后才通过。该核对不是运行真实Source/CMC或专项，不增加测试/夹具/严格矩阵；原生产动态断言留给统筹同新DLL统一编译与必要UE冒烟。
- 范围保护：本轮261份h/cpp/cs清单无新增/删除，仅授权PlayerInput两源hash变化，其余259源码保持。h 8303 bytes/SHA256=`6C059975EC4C309CFFB5F8328349F23C4849AD6A3B15E5B1D94E970047A3CC15`；cpp 52979 bytes/SHA256=`1CAEF4F94D9662C086DCAC71471C005EC19536D275A6C15D942938B396141DF1`。Contract新增登记/状态及证据，历史按原文保留，最终hash外部交回不写自身hash；其它模块/测试/资产/配置/全局/Obsidian/Saved/代理零写入。
- 架构核对：原生观察、Movement资格/恢复、CMC执行仍各有唯一归属；本步只分开内部输入与派生义务，没有循环依赖、内部状态对外端口、第二held/执行器/调度/自动重试或伪Released。内部生存期仍属于原PlayerInput，原会话匹配、先摘再外调及后继保护沿原机制保持。
- 未完成项：新代码尚未编译/动态；能力Action聚合/注入证明语义仍待用户决定，能力来源接口、Hero A完整原请求消费、B typed H/Source→CMC及旧诊断均须后继冻结合同和租约。全局/外部图文由统筹按其独占范围同步本实际状态，本轮不扩大写权；三文件交回后立即冻结。


## Input-RetryDiagnosticSignature / 两现有诊断纯签名预检（2026-10-03）

| 项目 | 本步授权与写前登记 |
| --- | --- |
| 唯一作者/基线 | Input长期组长直接执行，gpt-6.1-sol / xhigh，无代理；基线 `Saved/ValidationRecords/InputRetryDiagnosticSignature_LeaseBefore.json`。三实物hash已核对，先登记后改cpp |
| 精确三文件 | `Source/GGYGO/Input/Tests/GGYGOInputRetryIdentityDiagnostic.cpp`、`Source/GGYGO/AbilitySystem/Tests/GGYGOInputActivationOriginDiagnostic.cpp`及本记录 |
| 唯一目标/依赖 | 消费已冻结ASC OneParam `const FGGYGOAbilityInputRetryRequest&`通知；保留各原捕获列表，仅替换lambda形参，函数开头从原载荷提取const Tag/Deadline局部值。两cpp已有直接ASC.h，值类型与NoAbilityInputRetryDeadline均可见，无新增include |
| 保持/非目标 | 原回调正文、观察存储、阶段/计数、deadline、重入/Raw Try/失败反馈、清理、启动标志/路径及全部断言保持；不造ID/请求，不改旧-1断言，不触Hero/生产/共享接口/夹具/测试矩阵及第四文件 |
| 验收/停止 | 逆向各一处形参与两行提取后两cpp原始全文精确恢复；核对OneParam签名与值提取、原断言保持及有限语法。需要正文/断言/生产变化或第四文件即停；不运行UE/UHT/Build/Git，不写外部笔记/全局/Saved/代理 |
| 未关闭边界 | 两诊断无旧Tag/Queue调用，但Hero仍有旧Pressed/Released、二参数retry委托及二参数Queue编译阻点。旧NoDeadline预期、原夹具及人工Completed来源运行合同未迁移；本步不能宣称完整链可编译或诊断通过 |


## Input-RetryDiagnosticSignature / 两cpp有限证据及冻结交回（2026-10-03）

- 两现有诊断各只改一处lambda形参为 `const FGGYGOAbilityInputRetryRequest& OriginalRequest`，函数开头新增const Tag/Deadline两行，只读取原InputTag/OriginalDeadline。两原捕获列表、原回调正文及其它全文保持，无新增include；不读取/构造/替换ID，不发行请求或改变任何deadline。
- Input RetryIdentity cpp 324→326行（+3/-1），16180 bytes/SHA256=`77763FEC93B5790F1CD87AF6E13191FAD2DA328A413D347A3224545E05889BB9`；ASC ActivationOrigin cpp 370→372行（+3/-1），18788 bytes/SHA256=`F043FE9370A6C22D75D29B40D21DAE4CE6D2C8D089EEBDEC52C7645CF6F4E492`。各逆向形参和两行提取后，原始全文精确恢复写前，故全部断言、计数/观察、重入/Raw Try/反馈、清理、测试路径/启动标志及Probe实现保持。
- 有限静态：每cpp新OneParam形参1处、旧二参数形参0处；值类型由已有直接ASC.h包含，冻结委托完全匹配该const引用签名。两诊断自身旧Pressed/Released/Queue调用0处；去注释/字面值后花括号/圆括号最终与最低余额均0，尾随空白0。只核对代码签名及原文保持，没有Build/UHT/UE/动态测试或新增夹具/矩阵。
- 未关闭边界原样保留：两诊断初始NoAbilityInputRetryDeadline=-1预期与新有限原截止合同不同，不能通过改断言或把原载荷改回哨兵掩盖；旧夹具Host/人工Completed真实来源及Hero A/B尚未迁移。Hero仍有已移除的Pressed/Released调用、旧二参数通知和二参数Queue编译阻点；本步不宣称完整调用链可编译、诊断成功或根因关闭。
- 本步只写授权两cpp及本记录，既有Contract历史按原文保持，无第四文件/生产/共享/测试夹具/资产/外部笔记/全局/Saved/代理写入；全局及外部图文同步由统筹按独占范围处理。实际三hash交回后源码和本记录立即冻结，后继运行合同及生产迁移需另租约；Contract最终hash外部交回，不写自身hash。

## Input-Hero-ActionConsumerA / 范围纠正、冻结接缝与写前预检（2026-10-04）

统筹接受 Input 与 ASC 的有限零写入审计，明确能力来源是实际 EnhancedInput Action 事件，用户未禁止原生 Injected/Chord/Combo。“首次真实 Triggered”用于排除 GroupFreed 伪造 Pressed 和无来源失败借 Tag 建请求；不能扩为所有触发配置的纯硬件因果证明。此前 Hero A 因完整物理证明缺口停止、能力注入语义待用户决定的分析保留为历史，本次范围纠正取代该能力阻点；Movement 原始观察、Cold/Rearm、真实释放恢复、原失败及两诊断的既有红/未运行边界不受此纠正影响。

| 项目 | 本次有限原子 |
| --- | --- |
| 唯一结果/归属 | 原 Action 绑定来源→ASC 原请求的完整生产消费链。Hero 仅拥有原绑定、Action 观察关联、发行 ID 值及有限 retry 资源；ASC 独占 held/queued、Spec 聚合、输入边沿与 Process 执行；Movement 物理恢复独立 |
| 精确三文件/基线 | `Source/GGYGO/Character/Components/GGYGOHeroComponent.h`、同名 cpp、本记录。基线 `Saved/ValidationRecords/InputHeroActionConsumerA_20261004_LeaseBefore.json`；写前 hash 分别 `65A14EDE292C9355FF357837D46A4760F44E8F077A5B9015FFFEC126059EDE06`、`8CCA5796C37A39D843A63A9DAE8C37C80319F2ACCD31F76ED8D02AFCD569149C`、`0248BBAF0784648A8881FD1B0669F4A973EC3E55BC0299A189E754063681DF92`，实读一致；Input 长期组长直接实施，无代理 |
| 已冻结接口 | 原生 `BindActionInstanceLambda` 交付 FInputActionInstance/SourceAction；绑定捕原 Action/Tag/组件/PlayerInput/既有 InputSessionGeneration。ASC `Receive(Tag,PreviousIdentity,OriginalDeadline)`、`End(Identity,EndKind)`、`Queue(OriginalRetryRequest)` 及 OneParam retry 通知保持只读 |
| 冻结语义 | 首 Triggered 先锁存原 Action 观察与固定 deadline；未 Ready、Receive 拒绝或非法窗口仍锁存无 ID，不晚补。连续 Triggered 只传原 ID，Stale/Rejected 不改为空身份重新发行。同 Tag 不同 Action 独立；Completed 和 Canceled 均 Released 原 ID，保留 07D 行为；绑定/会话/ASC 失效仅 Invalidated 自身原 ID |
| 生命周期/清理 | Action 观察寿命独立于 ASC 订阅；订阅重绑不清首次失败锁存。先摘原资源/待处理快照，再外调原 ASC 清理；已 Released tap 只在原窗内保留精确关联，原窗过期不释放仍处于 Action 周期的请求。源身份/Tag/deadline 全匹配才缓存及 Queue，不猜当前 Tag 来源、不解析 -1、不全 ClearASC |
| 拆分预检/顺序 | 本记录登记→两 Hero 源迁移实际 Ability 绑定及接收/结束/retry/清理→有限源码回读与保护块逆向核对→本记录追加实际证据→三 hash 交回冻结。上述调用点共同关闭一个原请求合同，不能分成可运行的 Tag/ID 混合链；只替换既有输入关联，不新增执行器或拆分无关相机职责 |
| 只读依赖/非目标 | ASC 普通值类型、当前订阅/Ready 查询、原 InputConfig 与 EnhancedInput 实例委托。B typed H/Source→CMC、IMC/Camera 迁移、InputComponent、ASC/Producer/Movement、测试/资产/UE/Build/Git、外部笔记/全局/Saved 均无写权；架构计划由统筹独占范围同步 |
| 验收断言/停止 | 首失败锁存、不续期/不自动补发；原 SourceAction 与绑定会话匹配；多 Action 不借 Tag 互清；完整原 retry；GroupFreed 只有 Queue；晚返回 ID/旧回调/旧清理不触及后继；无全 Clear 或第二 held/时钟。第四文件、共享签名变化或可见语义取舍即停止该接缝交回；纯技术细节直接处理。有限静态不代表编译/必要冒烟通过 |

当前状态：Hero A 三文件生产消费迁移已保存并完成下列有限静态核对，交回即冻结；未 Build/UHT/UE/冒烟。A 源码产出不代表 B 装配、旧诊断、生产资产或整 Input 已完成。

### Input-Hero-ActionConsumerA / 实际产物与有限证据

- Hero 直接使用三个原生实例事件委托，捕获原 Action/Tag/组件/PlayerInput/既有输入会话代次，回调核对实际 SourceAction。绑定插入顺序保持旧实现：逐 Action Triggered/Completed，之后统一追加全部 Canceled；避免改变同帧多来源的原生回调顺序。没有修改 Trigger、Modifier、Injected/Chord/Combo 配置或 Action 派发时机，没有硬件反射适配/能力 Producer 层。
- 私有 FAbilityActionBinding 拥有实际绑定来源及当前 Action 观察；FAbilityInputObservation 只保存原关联、固定请求值和自身资源寿命。首次 Triggered 先安装观察再调用 Receive，非法/负/非有限窗口或无有效 World 明确 Error、未 Ready 明确 Warning，均保留无 ID 锁存；没有窗口 clamp/零时长成功回落。连续 Triggered 无 ID 直接拒绝补发，有 ID 只校验原 PreviousIdentity/Tag/deadline；Stale/Rejected 退休原关联并保留本 Action 的锁存，不将返回空身份作为新输入。
- ASC 是唯一发行者；Hero 只在第一次成功 Receive 后写一次原 Identity。Receive 返回前若原 Hero/绑定/观察/ASC 已失效，晚返回 ID 仅交回原 ASC Invalidated，不采用后继。SourceASC 比较使用原 weak 身份；失败来源查找仅按完整 Identity，再核原 Tag/deadline，没有按 Tag 或“近期截止”推断源。
- Completed/Canceled 均在核对原绑定后先摘本周期观察，再向原 ASC End(Released)。仍在原窗口的已结束关联供精确 OnInputTriggered retry；窗口过期只移除已结束关联/缓冲，活动 Action 观察不按截止松开或重发。Released 返回失败不会被报成正常释放，仅精确 Invalidated 归还原资源；生命周期失效从不伪造 Released。
- ASC-only 解绑先摘原 ASC/两个原句柄，再退休它发行的原 ID；未发行 ID 的当前 Action 观察继续保留，订阅晚就绪/重绑不能补发。原绑定退出在 ASC 外调前标记退休；原 request/缓冲快照在任何 End 外调前移除，后继不被旧清理触及。订阅清理返回后另核原输入代次、预期订阅代次及空槽，防止同 ASC/同输入代次的后继订阅被旧安装覆盖；沿用既有两个代次，不新增分配器或帧时钟。
- OneParam retry 只读取完整原请求的值副本；缺 ID、非法截止、来源不属于本 Hero、Tag/deadline 不匹配、过期或阻断均不缓存、不借旧 tap、不建新窗口。同 Tag 不同 Action 的原观察/请求独立；缓冲按 Identity 去重，ASC 独占同 Spec 多来源 held OR 与首按/末释放边沿。GroupFreed 先移走自身有限快照，仅 Queue 原请求，下一轮重新取得原 weak Hero/ASC/两代次；没有 Pressed/TryActivateAbility 旁路。
- 已删除 Hero 的 AbilityInputTagPressed/Released、二参数 Queue/通知、Tag deadline 两映射/哨兵解析和全 ASC.ClearAbilityInput。新生产源码 Receive 调用点 1、Queue 调用点 1，原 Identity 赋值点 1；结束仅原 ID。没有新增 Tick/Timer、物理 held 表、Spec 规则或执行器；依赖仍为 Input→ASC/EnhancedInput，没有反向依赖、循环或内部状态泄漏。
- 保存回读：Hero.h 11750 bytes/253 行，SHA256=`552CEF5B12EA2FF682AC2498A3421CDCD4BD6A4EBDDAC66DA885A578F8F25CE9`；Hero.cpp 58124 bytes/1401 行，SHA256=`6DFD57C26B704352C6C4C3ADEA66E44770BEE0794B341FAE1BD2C39416D90D1E`。按全部修改块逐一逆向，两份完整源码文本精确还原写前基线；去注释/字面值后花括号、圆括号、方括号最终及最低余额均 0，尾随空白 0。
- 14 个原方法全文保持：BeginPlay、EndPlay、HandleAbilitySystemUninitialized、三项 CameraMode 方法、Move/ForceWalk 两项/Look 两项、HasValidPlayerInputSession/GetInputSessionAbilitySystem/IsInputSessionAbilitySystemCurrent。Hero h/cpp 的 typed H 身份准备块及全部实现尾部逐字保持，尚未接生产；Initialize/Release 的 IMC、Native、Camera 逻辑保持，仅替换本 A 的能力绑定和原请求退休接缝。旧无来源 Tag Hero 回调没有其它源码调用者；InputComponent 公共模板、ASC 公共签名和 Producer 均未修改。
- 本 Contract 除顶部当前范围纠正和本节追加外，全部历史文本精确保持；原 Movement Cold/Rearm/真实释放、已知失败和此前停止事实均保留。只读回核 PlayerInput h/cpp hash 仍为 `6C059975EC4C309CFFB5F8328349F23C4849AD6A3B15E5B1D94E970047A3CC15`/`1CAEF4F94D9662C086DCAC71471C005EC19536D275A6C15D942938B396141DF1`。
- 已只读核对 Obsidian 计划蓝图定位 Input：Input/结构.md 当前仍记“能力物理周期端口未实现/Action来源未实现”，这两项须由统筹按其独占文档范围同步为本 A 的 Action 回调原请求消费已源码保存、未编译/冒烟；结构/流程 Canvas 应反映 Action 绑定→原观察/ID→ASC Receive/End/Queue，不再以能力全硬件证明作阻点。此租约禁止外部笔记写入，未越权保存；B typed H/Source→CMC、IMC/Camera、生产 Hero 首移动和资产/网络边界仍开放。
- 未运行编译/UHT、UE/必要冒烟或诊断；未新增测试/严格矩阵，未修改旧断言、NoDeadline 预期或旧私有 Host/人工事件夹具。Hero 旧接口引用已静态移除，不据此声称 Build56 后继构建成功；旧红需统筹冻结全链后以新 DLL 验证。本轮仅授权三文件保存，无第四文件、Saved/全局/外部笔记、资产、Git 或子代理写入；源码和本记录交回后冻结。

## Input-Hero-LocalIdentityB1 / 授权预检与生产接入（2026-10-04）

统筹接受先前只读拆分后，明确授予 Hero h/cpp 与本 Contract 三文件唯一写权；纯技术预检已足够，直接实施，不等待形式过目。B1 仅闭合 typed H→既有能力订阅及原作用域失效清理；身份发布与实际移动装配拆成不同批次，Source→CMC/B2 不属于本次写权。

| 项目 | 本次有限原子 |
| --- | --- |
| 唯一结果/归属 | Hero 消费 Extension 已认证的 opaque H、实际 publication Context 与原 binding 身份，关联已有输入会话并持有自己两项 ASC 通知订阅；Host/ASC 仍唯一负责 ActorInfo/binding/publication，Extension 唯一拥有本地 H，Source/CMC 各自的事实/执行归属不变 |
| 精确三文件/写前 | `Source/GGYGO/Character/Components/GGYGOHeroComponent.h`、同名 cpp、本记录。写前 SHA256 分别 `552CEF5B12EA2FF682AC2498A3421CDCD4BD6A4EBDDAC66DA885A578F8F25CE9`、`6DFD57C26B704352C6C4C3ADEA66E44770BEE0794B341FAE1BD2C39416D90D1E`、`BE97718761B978C8CFCCCF48588A92015927261808E3E10B2A2F63B77BE1E294`，实际一致；Input 长期组长直接完成，无子代理 |
| 冻结只读接口 | Extension RegisterLocalAbilitySystemNoticeAndCall/Unregister、IsLocalAbilitySystemResourceReady、H.HasSameResource/GetIdentity；ASC 原 Context 当前性及 A 的 Receive/End/Queue/两项通知；Source Begin/Attach/End/GetRequest 与 CMC Bind/Consume/Invalidate/GetBindingSerial 未改 |
| 顺序 | 激活既有 typed 注册并保持原记录先安装→Ready 关联已经存在的输入并绑定既有能力重试；输入晚就绪由原 Initialize 尾部补齐关联→Released 先捕原关联、撤销 H，再按原作用域清理→有限源码静态核对→本记录实证→三文件交回冻结；B2 实际装配及统筹 Build/同 Entry 冒烟另批 |
| 非目标 | 不创建/重建输入，不改 InitState 业务、IMC 配置/资产、Source→CMC、物理释放/Cold/Rearm/FAILED、Profile/固定速度/Run、网络、Host/ASC/Extension/Source/CMC 源码、测试矩阵、UE/Build/Git、全局/外部图文/Saved |
| 验收断言/停止 | 原 H/记录/两代次和 weak 来源必须匹配；不同 H 即使同 ASC/Pawn 也不得借用；Released 在 weak ASC/Pawn 失效后仍可撤销且不能伪造 Released 输入；同步回放/迟到句柄只归原记录；同 H Refreshed 不重建；旧清理重入不清后继；A 首失败锁存/原 ID/原期限/结束/retry 保持。第四文件、新共享接口、输入重建或真实可见业务政策选择即冻结交回，不自动扩权 |

### Input-Hero-LocalIdentityB1 / 实际产物与有限证据

- BeginPlay 已使用既有 Prepare typed 注册，移除 Hero 的两项无参数 initialized/uninitialized 订阅及基于当前 ASC/Pawn 指针的反初始化猜测。保留原记录先安装、同步 Ready 回放、原 weak Hero/记录捕获、迟到返回句柄归原记录与原 Extension 归还；Prepare 失败明确 Error，不改用旧 Getter 或默认业务。Prepare/GetReady 的原身份校验正文保持，GetReady 每次询问原 H 的真实 Ready，不缓存 Ready 权限。
- Ready 完成 H/真实 PublishedContext/binding 校验后，仅对当前已有、有效的原输入会话调用既有 Bind；输入尚未建立是合法暂态，保存认证 H 并由原 Initialize 尾部关联，没有新增 Timer/Tick/等待队列或输入重建。Refreshed 仍要求同 H，并在调用关联/绑定前直接返回；原输入/订阅代次、实际绑定、IMC、Action 请求 ID/期限均不重置。
- FAbilityRetryBinding 是既有两项 ASC 订阅的不可变来源值：原记录 weak、原 H、原输入组件 weak、既有 InputSessionGeneration/AbilityInputSubscriptionGeneration；不拥有新计数器、Ready bool、held/queued 或执行状态。实际句柄仍在原唯一两个槽中。两通知闭包捕获原 Binding，Getter 与回调共同核原记录/opaque H/关联/两代次/实际 Ready；原 ASC 指针相同不再足以复用订阅。解绑先摘原槽及 Binding，再精确退休原 ASC 发行的自身 ID；ASC-only 解绑仍保留未发行 ID 的原 Action 首失败锁存。
- Released 分支先于 Pawn/ASC 生存及 Ready 查询：确认原 opaque H 后，捕获原输入代次/组件 weak 身份及原订阅，先撤销 H/派生关联，再释放匹配的原输入。weak 对象失效不妨碍值身份撤销；旧 H 或旧记录不进入当前清理。没有关联当前输入时，只允许清理仍匹配原 H/记录的原能力订阅，不能借当前输入槽扩为全会话清理。
- 原 ReleasePlayerInput 先清派生关联，再沿用原资源快照/句柄/IMC 计数清理。既有 ForceWalk=false 归还前移至摘除本地原资源之后、首次 ASC 外调之前；只读确认 CMC setter 为本地状态写入，未修改 CMC 或 ForceWalk 规则，避免原清理在重入后覆盖后继请求。原 Subsystem/PlayerInput、CountRegistrations 与原 priority 来源资格检查及警告全文保持；统筹实测 StopPIE 原 Subsystem 失效诊断仍是未关闭边界，不加隐式移除/资格兜底。
- Released 的相机后置清理重新取得 weak Hero，要求原记录仍在、H 未出现后继、释放后的既有输入代次匹配且输入/ASC/订阅槽仍空，并核既有相机请求代次未出现新覆盖；才清原覆盖并调用现有相机复位。旧 ASC/IMC 清理回调产生后继时不再进入该调用。EndPlay 先封口，退休原 typed 通知与其原 ASC 订阅，再释放原实际输入及现有相机资源；未新增第二输入/相机状态机或权限来源。
- A 的 Action 来源/原请求处理未改变：21 个保护方法全文一致，包括三个 CameraMode API、Move/ForceWalk/Look、Action 校验/失效、Triggered/Completed/Canceled 共用的结束处理、原 ID 查询、输入会话检查/代次检查、过期处理、完整 Buffer/GroupFreed→Queue，以及 Prepare/GetReady。三事件实际绑定及插入次序不变；Receive 调用点 1、Queue 1、原 Identity 赋值点 1；旧无参数通知/旧 Extension Getter/全 ASC Clear 引用均 0，Source 装配调用及新增 Tick/Timer 均 0。没有新增反向依赖、共享签名、第二 held/事实来源或循环。
- 保存回读：Hero.h 11867 bytes/255 行，SHA256=`82D2D897F0013A87CF805D08D7BBAD687CF0B479A732989BE1931D2C864EBC78`；Hero.cpp 63075 bytes/1492 行，SHA256=`F0C744D665D3EF29F6ADB181C717D6F7A78158F57E8A246A2E1D9B91D6A0BC4F`。全部改动块逐步逆向精确恢复两份写前完整文本；去注释/字面值后花括号/圆括号/方括号最终与最低余额均 0，尾随空白 0。Source h/cpp 只读 hash 仍为 `6C059975EC4C309CFFB5F8328349F23C4849AD6A3B15E5B1D94E970047A3CC15`/`1CAEF4F94D9662C086DCAC71471C005EC19536D275A6C15D942938B396141DF1`。
- 本轮没有 Build/UHT、UE/同 Entry 冒烟、Git、专项/诊断运行或测试矩阵写入。统筹交接的 Gate57 编译成功及 native lifecycle 单叶 Success 属于本 B1 保存前证据，不能证明 B1 或 Hero 生产链成功；旧严格失败、Host 实测失败、正式首移动/Run/网络边界保留，不能用局部静态或历史叶通过标整模块完成。
- 已核对 Obsidian Input 结构与图文同步责任：本次会改变 typed 准备无调用→生产身份消费、原 H/订阅/清理流程及 B1 实施状态；统筹明确外部四图文待源码冻结另授，本轮未越权写入。统筹本轮独占补充的两 IMC CountRegistrations 单包保存与旧注册拒绝消失事实须保留；其 Input/结构.md `9DB09F142E8A1DF149BA105028F960A9F38A5904C0B535422513DF020B4F1994`、结构 Canvas `358A9EA18CAEA5EC2320D2977B24CA7AE934D3B758313D5A5E481E38C1E63AAD` 是已登记统筹变化，不是本作者保护损坏。Input→Source→CMC/B2、Ready 后实际输入重建/普通接续与生产动态验收仍开放；不把本 B1 的已有会话关联当作已装配或已恢复。
- 本记录仅更新顶部当前状态及追加本节，全部历史内容保持；不新增重复过程文档，不写全局入口、外部图文、Saved 或第四文件。三文件交回即全部停写冻结，最终 Contract hash 由外部交回，不写自身 hash。

## Input-Hero-SourceCMC-B2 / 授权预检与实际装配（2026-10-04）

统筹接受 B2 只读拆分并正式授予 Hero h/cpp 与本记录三文件唯一写权，基线为 `Saved/ValidationRecords/InputSourceCMC_B2_20261004_LeaseBefore.json`。Source 实际为既有 UGGYGOPlayerInput；错误的 PlayerInputSessionSource 定位已纠正，不新增该类、物理事实或请求发行器。无参数动态 ControlMappingsRebuiltDelegate 由薄通知资源捕原不可变输入上下文，旧复制回调不能查询后继作用域。

| 项目 | 本次有限原子 |
| --- | --- |
| 唯一结果/归属 | 原 Hero 输入作用域→现有 Source→现有 CMC 的生产装配。Hero 仅持通知、Session/Binding 句柄及诊断缓存；Source 独占原观察/资格/发号/释放义务，CMC 独占绑定、事实消费、准入、FAILED 与执行 |
| 精确三文件/写前 | Hero.h `82D2D897F0013A87CF805D08D7BBAD687CF0B479A732989BE1931D2C864EBC78`；Hero.cpp `F0C744D665D3EF29F6ADB181C717D6F7A78158F57E8A246A2E1D9B91D6A0BC4F`；本记录 `F33CFFD54A6CD9A10F441AECF5B856AFDD8E297D9A1E64C88E95E0E6A53E78CE`。与统筹 LeaseBefore 实读一致，Input 长期组长直接实施，无子代理 |
| 冻结接口 | Source Begin/Attach/End/GetRequest，CMC GetBindingSerial/Bind/Consume/Invalidate，普通 Types、Extension typed H 与 ASC A 原 ID/期限/通知合同只读；没有增加或修改共享签名 |
| 顺序/资源责任 | 全部依赖先验→原薄映射注册先于实际 IMC Add→真实 native Rebuild 且本作用域各 Add 注册已登记→捕原 CMC serial→Source Begin→CMC Bind→固定原 Session/Binding→Attach 同步回放；Begin 返回的准备 token 立即由原栈/作用域拥有以覆盖 Bind 重入，尚不声称接收者安装成功 |
| 清理 | 先摘 Hero 当前资源槽、封原注册与作用域，再归还原 ForceWalk 请求，然后才 End 原 Source/Invalidate 原 CMC。资源内部原 Session/Binding 在任何外调前摘除；原 ID/绑定清理不得换为后继。Attach/Begin/Bind/协议消费失败可定位并退休自身资源，不假报移动成功 |
| 验收/停止 | 真实重建后才装配；旧复制通知/原 Action/组件/输入代次/原 Fact 与 Request 来源匹配；首个真实 Press、同请求持续、真实 Released/Neutral、第二 Press 新号及 FAILED 保持待动态。第四文件、新共享契约或 Cold/Rearm/恢复可见行为选择即停交；不自动扩严格矩阵 |
| 非目标 | Camera/ForceWalk/Busy/身份规则、Run/Profile/固定速度、网络/MoveData、Producer/CMC/Types/Extension/GAS/GM、IMC 资产、测试/引擎/UE/Build/Git、Saved/Obsidian/全局文件无写权；Teams 独占 GM 线不冲突 |

### Input-Hero-SourceCMC-B2 / 实际产物与有限证据

- 新 FGGYGOHeroMovementInputScope 保存不可变原 Pawn/InputComponent/PlayerInput Source/Subsystem/CMC/MoveAction、既有输入代次及预期实际 IMC 注册项数；可变部分只为自身 Session/Binding/通知资源、退休标记与有限诊断缓存，不持物理 held/neutral、请求编号发行、Ready 权限或执行/FAILED 状态。CMC 取实际 Pawn 的 CharacterMovement，与可选 ForceWalk 的原清理指针分开，没有新增 ForceWalk 归还对象。
- Initialize 在任何绑定/IMC Add 前明确校验真实 UGGYGOPlayerInput、GGYGO CMC 及 Axis2D MoveAction，失败 Error 含 Pawn/InputConfig/Action/来源/原因。没有 Enhanced-only、默认 Source、默认动作或速度回落。DefaultInput.ini:97 原默认类仍为 `/Script/GGYGO.GGYGOPlayerInput`；资格资源仍由原 LocalPlayer 原生创建 Host/Source 链提供，Hero 不 NewObject Producer/Origin、不补 Cold/Claim/Neutral，也没有新增 ASC Ready→移动准入门禁。
- 薄 UGGYGOHeroMovementMappingObserver 位于同一 Hero h/cpp，通过 Hero UPROPERTY 保有；每个实际输入作用域新建一次并保存原 weak Hero/Subsystem 与原作用域，不将该对象重用于后继。Detach 先清原槽再精确 RemoveDynamic；BeginDestroy 幂等 Detach。复制中的旧通知要么持原上下文，要么因原记录封口被拒绝，不查询新记录为自身换戳。真实通知前没有 Begin；原 Add 同步外部回调可以触发 native Rebuild，因此另核本作用域实际登记数与预期数，部分 Add 期间不提前消费 Cold。
- 真实 Rebuild 清理原资源后重新核原输入作用域及空资源槽，再捕 CMC serial 进行 Begin→Bind→保存→Attach。准备 token 在 Begin 成功后立即归原作用域，Bind/Attach 迟到返回或重入时用原栈保存的 Session/Binding 归还；旧 Begin/Bind 失败不能退休同作用域中已经替换的后继资源。只有新的真实重建或显式新输入生命周期可装配，不在 Triggered、Tick/Timer 中反复 Begin 或静默重试。
- Attach receiver 捕原 weak CMC、原 Binding 与原 Session，校验收到的 Binding/Fact.Request.Session 后直交 `ConsumeMovementInputFact`。SessionOpened 的 Cold/Rearm 及 RequestStarted proof 原样由 Source 提供；Hero 不选择默认模式或发号。协议 Rejected/Stale 只退休仍匹配原 Session/Binding 的自身资源；旧 terminal fact 仍交原 CMC，由其唯一绑定校验保护后继。Recorded 即使携带配置/执行失败，仍保留 CMC 原 FAILED 请求与 Source 真实释放链，不把它当成成功执行或重建另一请求。
- 原 Move Triggered 插入位置仍最先，改用实例委托捕原 Action/组件/输入作用域，核真实 SourceAction 和原 input generation；取原 Session 的 GetMovementInputRequest，要求非零请求及相同 Session，并核原 CMC binding serial。Source 未装配/请求不可证明时按原作用域去重诊断并拒绝值投影，不借当前 Tag/ASC/后继来源。方向仍按当前 ControlRotation.Yaw 的原两个 AddMovementInput 投影；Value.IsNearlyZero 只跳过该值，真实释放/Neutral/W-S 抵消仍完全由 Source 处理。
- ReleasePlayerInput 已先摘当前 Scope/Observer、封原注册与资源，保持 B1 既有 ForceWalk=false 位于任何 Source/CMC/ASC 外调之前。Source/CMC 清理也可能重入：结束后另核原输入代次、ASC 订阅代次及原 AbilityRetryBinding，才解绑原 ASC；不会因新清理入口而摘除后继能力订阅。原原生绑定句柄及 IMC CountRegistrations/原 Subsystem/PlayerInput/priority 归还正文保持；StopPIE 来源失效警告未兜底消除。
- 有限保护核对 34 个原方法全文保持：BeginPlay/EndPlay/OnRegister、三 CameraMode、四 InitState、ForceWalk/Look、A Action 校验/失效/Triggered/结束/查询/缓冲/Queue、B1 typed 订阅/Ready/Released/Refreshed/关联及 ASC getter/订阅等。Move 外部调用检索仅剩本 Hero 声明、原实例闭包与实现，没有跨文件旧值签名调用者；Native Look/ForceWalk 和 A 绑定、事件次序正文保持。
- 保存回读：Hero.h 13059 bytes/284 行，SHA256=`8C1DFEBD89EEEAB96A4E68EDDF166DDF17F27433BC115EE8194A8AC7597091DC`；Hero.cpp 79666 bytes/1828 行，SHA256=`B4926513139BE1C0C48F034BAF119C88D2562F13C39CF098FE8DEB39AA72C66C`。全部修改块逐步逆向精确恢复两份 B1 写前完整文本；去注释/字面值后三类括号最终及最低余额均 0，尾随空白 0。Source Begin/Attach/End/GetRequest 与 CMC Bind/Consume/Invalidate 各调用点 1，新增 Tick/Timer 0；没有第二帧调度、物理来源表、发号器、权威状态或反向依赖。
- LeaseBefore 六项只读保护实读完全匹配：PlayerInput h/cpp、CMC h/cpp、Extension h、DefaultInput.ini。没有 Source/CMC/Types/Extension/GAS/GM/网络/Profile/Run/资产/测试/引擎写入。编译/UHT/UE/同 Entry 冒烟/真实硬件/专项矩阵/Git 均未运行；未修改既有失败断言或以静态核对生成动态成功，旧严格失败和 Host/Movement/生产资产/联机边界仍可见。
- 原 Source 主动暂停/Flush/Controller/栈/映射失效按现有事实失效原 CMC；Hero 没有用轴零/加速度零伪造 Released，也没有新增恢复轮询或触发时补 Begin。暂停/Flush 等恢复入口、普通 Ready/Released 后实际输入重建、正式首移动/Profile/Run/网络动态验收仍未关闭。源码装配保存不等于完整生产输入/移动模块完成。
- 本 Contract 仅更新顶部当前状态并追加本节，全部历史保持；本三文件租约禁止外部图文/全局写入。Obsidian Input 结构/流程需由统筹在后续互斥图文租约同步原通知→Begin/Bind/Attach、事实→CMC 和 GetRequest→原值投影，继续保留已登记两 IMC CountRegistrations 资产事实及所有未运行/失败边界。本轮未写笔记/Saved/测试/第四文件；三文件交回即停写冻结，最终 Contract hash 外部交回，不写自身 hash。
