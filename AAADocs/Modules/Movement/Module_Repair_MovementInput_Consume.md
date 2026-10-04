# 移动输入来源：CMC 本地消费

日期：2026-10-02（北京时间）。当前状态：三文件实现及静态核对完成，停写冻结交回；未编译、未运行，Producer/Hero接线、完整C36、网络/replay仍开放，不代表生产 Run 恢复。

## 原子预检与租约

| 项目 | 范围 |
| --- | --- |
| 唯一目标 | 实现 CMC Bind/Consume/Invalidate、来源请求到唯一执行请求的映射，以及本地失败准入门禁 |
| 唯一写入者 | Movement 长期组长直接执行；无代理 |
| 精确文件 | `Source/GGYGO/Character/Components/GGYGOCharacterMovementComponent.h`、同目录 `.cpp`、本记录 |
| 冻结接口 | `Source/GGYGO/Input/GGYGOMovementInputTypes.h`，SHA256 `7C9C1B3FC6902BE2E99FE2FBC5B5EA5C185983772E4B1FF88C2E14C666D9AE61`；SessionIdentity/RequestIdentity/ConsumerBindingId、七 Kind、TwoParams |
| 职责/依赖 | PlayerInput 唯一认证来源并发行 Session/Request/Event；Hero 后续管理绑定并转交；CMC 只消费中性事实，独立发行 ConsumerBindingSerial/执行请求序列，仍独占 gait/clock/failure |
| 只读依赖 | AGENTS、Coordination 当前排程/清单、共享契约、既有 Hero、原生 CMC/RMS、P1；不读写 Input 私有来源状态 |
| 顺序 | 保存基线→本记录登记预检→两 CMC 实现真实接口和门禁→静态范围/生命周期核对→登记差异与未验边界→三文件冻结 |
| 非目标 | 不改 Input/Hero/共享头、RMS、MoveData、SavedMove/replay、测试、资产、其它记录、Obsidian；不实现所有 C36 执行帧 |
| 验收断言 | ExpectedSerial 精确匹配；旧/重复/ABA 不发新执行号、不清后继；七 Kind 生命周期检查；真实新来源请求映射一次仍校验配置；释放/失效/重绑/Reset/解禁/零加速度不解锁失败；独立 Action/动画 RootMotion 保留 |
| 停止点 | 完成三文件静态交回即冻结；需要未冻结接口或额外文件则停止；不运行 UE/编译/Git，不新增记录轮次 |

## 实现前基线

- CMC.h：25228 bytes，SHA256 `00C3B5A3E7DC963403D8D0FC5D67F361B09ABC40CA1983C20974A04DE89D0C7A`。
- CMC.cpp：62767 bytes，SHA256 `1AD15D3B4FCF36950B620D655B8B9414535C5B4DA65800E06D747B89287896FF`。
- 两 RMS 文件继续冻结：h `DCA2DA64C9B7D06CF78711C2F3C62BA6CDDB4514FEC26543531B1CDE9BE4DBDB`；cpp `1A244710AB744496673048F1A1EDADB37E00E9B450373BE1F376140921C5EBB9`。

## 必须保持的边界

- Recorded 只确认事实消费，绝不表示执行准入成功。输入来源编号不复用为 CMC 执行请求编号。
- 绑定只授予通知资格。只有新的 RequestStarted 能建立新的本地执行请求；NeutralConfirmed、释放、失效及配置 Reset 都不能解除失败。
- 消费绑定使用原对象弱身份和发行代次；失效对象仍用 HasSameIndexAndSerialNumber 比较来源，不归并为空指针。
- 新来源接口一旦绑定，解绑/失效不能回到旧 Acceleration 推断请求路径。尚未接入新来源的旧调用链保持未迁移状态，不能称根因关闭。
- Profile 运行失败、首帧 RMS Prepare、最终执行提交、网络/重放/代理仍由后续 C36 精确步骤完成；本步不把旧曲线链写成已修复。
- 图文按本租约冻结。实现后只读核对 Obsidian，并交回需要同步的接口/状态信息，不冒称已同步。

## 实际实现与接口

- CMC.h 首次真实包含冻结共享头；`EGGYGOMovementInputConsumeResult`由CMC定义为Recorded/Duplicate/Stale/Rejected，非蓝图业务成功结果。
- 已实现`GetMovementInputBindingSerial()`、`BindMovementInputSession(Session, ExpectedSerial, OutBinding, FString&)`、`ConsumeMovementInputFact(Binding, Fact, FString&)`。成功Bind清错误；失败清OutBinding、输出组件/来源/代次/原因，不改变现有授权。
- 已实现`InvalidateMovementInputSession(Binding, FName Reason, FString&)`，用于匹配来源事实及Hero后续Attach失败/资源回收。原绑定已关闭时幂等；错误绑定或缺少原因拒绝，不清后继。封闭授权并推进消费代次后才清理；EndPlay和原Producer弱对象失效均使用此入口。
- CMC独立单调发行绑定及执行序列，检查耗尽，不回绕。新的输入请求编号只用于来源/生命周期核对；本地执行请求号只有RequestStarted一处递增。
- 同一活会话的重复Bind不重新发号、不重置消费水位；陈旧ExpectedSerial、退休会话、同Producer旧Session均明确拒绝。绑定身份包含原CMC弱对象、消费代次和原SourceSession，全部使用冻结的弱身份比较。
- EventSerial必须非零并晚于消费水位；同事件同内容Duplicate，同事件不同内容Rejected，旧事件Stale。旧输入RequestStarted/Release/带请求的Unresolved不创建执行号、不撤销当前请求。接受的旧请求事实只保留事件水位，不修改执行和资源。
- RequestStarted先校验生命周期，才取消匹配旧Locomotion、映射新执行号并检查已接纳MovementSet；没有配置时记录事实但立即调用唯一`FailLocomotionRequest`并保留具体错误。Recorded不表示准入成功。
- 新执行重置表现段时保留已有ForceWalk和下一次直接Run意图。配置/ASC Reset、EndAction、重绑、零Acceleration、解禁不清失败状态；`RequestRunOnNextMove`本身也不解除失败。

## 七Kind消费生命周期

| 事实 | 实际规则 |
| --- | --- |
| Invalid | Rejected；未知enum值也拒绝 |
| SessionOpened | 匹配活绑定、请求号0且此前未Opened；只记录会话打开 |
| NeutralConfirmed | 会话已Opened且没有未Released请求，才记录neutral消费阶段；不准入、不清FAILED |
| RequestStarted | 请求号非零且新；必须已消费neutral、没有未Released请求。冲突Start先Rejected，不更新水位、执行号或资源 |
| RequestReleased | 精确当前请求；关闭请求消费阶段并撤销neutral证明。健康请求转Released以允许Stop尾段，FAILED/Revoked不解除；重复释放幂等 |
| SessionInvalidated | 原会话匹配，Reason非空；可在Producer弱对象已失效时按原身份回收，关闭授权，不宣称物理释放 |
| SourceUnresolved | 会话已Opened、Reason非空；带请求时必须匹配当前请求。撤执行授权、清neutral消费证明，但保留未Released阶段及原请求身份，不冒充Released |

`bMovementInputSessionOpened`、`bMovementInputNeutralConsumed`、`bMovementInputRequestOpen`仅是已消费事实的必要派生阶段，不观察设备/键，不推断物理held，不另发来源号。Producer仍是物理事实唯一权威。统筹实际审查指出的“无neutral直接Start／活动请求未释放即可更大Start”已修正：检查在Revoke、执行号递增及Reset之前。Unknown后须原ID真实Released→NeutralConfirmed→新Started，不能为迁就Producer旧清空行为放行。

## 失败门禁与资源责任

- 只有新的合规RequestStarted可把执行请求置Admitted；绑定、neutral、release、invalidate、Reset均不能设置该状态。失败在唯一入口锁存并一次诊断，旧执行号失败通知不作用于后继。
- 已接入来源接口的CMC在授权失效、未有合规请求或FAILED/Revoked时，普通地面GetMaxSpeed/CalcVelocity/ApplyRootMotionToVelocity/Before/PhysicsRotation共用门禁；拒绝期间不推进既有Locomotion求值。HasMoveInput只用Acceleration求方向/幅度意图，不以其零值生成来源请求或解锁。
- 匹配撤销清空自有曲线样本，并对Current/Pending内符合既有type/name/priority/Override契约的自有Brake/TurnBack写有限Identity输出、标记移除；原生本帧累计不会自动跳过Marked，不能只标记。普通地面只清平面Velocity，已有非有限Velocity做明确零安全清理；不修改Acceleration。
- 原生动画RootMotion和已有ActionCurve保持独立准入，撤销不释放Action token、不中止Action源。晚到旧事实在身份检查阶段退出，不能清后继RMS。
- ConsumerBindingSerial一旦非零，失效后仍非零，不能回到旧加速度推断链。完全尚未绑定新接口的旧调用链尚未迁移，本步没有把该缺口标完成。

## 静态证据与冻结

- CMC.h：27736 bytes/623行，SHA256 `043789EEAD09A5234AA1E73201D8B312D4108EA4062E8417A5FB94DF3502B861`。
- CMC.cpp：79503 bytes/2112行，SHA256 `32E1645402FC9CA00FE18EEC7E4E7F214FA5D40387EE86A103986C3BD598B92C`。
- 只读核对确认执行号递增1处、Admitted赋值1处、neutral消费true赋值1处；新来源区块不写Acceleration、没有Profile时间/周期/TurnBack时间的直接赋值。新真实请求沿既有Reset初始化自己的段；失败/撤销不推进这些时钟。
- 原cpp开头至BeginPlay前的SavedMove、MoveData和response整段与实现前逐字符相同；未迁移网络/replay。共享头hash及两RMS hash与上述保护基线相同。
- 两源码尾随空白和冲突标记0；去除注释/字面量后的cpp大括号平衡0、最低深度0。完整静态阅读核对正常、失败、旧/重复通知、绑定ABA、序列耗尽及EndPlay清理；这些是静态证据，不是运行测试。
- 架构核对：只依赖中性Input数据，不包含具体PlayerInput/Hero类型、不读其内部状态；没有新增Tick、RPC或调度器、Profile时钟、来源发号器。CMC消费与执行各有唯一序列，弱来源不延长对象寿命。
- 只读核对Obsidian计划蓝图Movement入口、Movement结构与移动计划：尚未列出新消费接口及来源证明阶段，结构第8行仍有旧固定速度兜底描述。PlayerInput→Hero→CMC接线、消费/执行编号区别及各未实施边界须由后续图文租约同步；本步按明确禁止范围未写Obsidian。

## 剩余边界

- 尚无Producer/Hero生产接线，未验证真实按键、same-held、重绑、Unknown恢复或故障日志的动态行为；没有新增测试、执行编译/UHT/UE/Git。
- 新来源不等于完整C36关闭：P1生产求值/运行失败传播、首次安装/StartTime/Prepare、原生early累计、完整返回唯一Commit、proxy仍待各精确租约；旧Profile失败回固定速度链仍是已知缺口。
- 网络仍须在用户批准的既有MoveData里传递来源生命周期，由服务端校验上报序列并建立自身执行对应，不声称证明远端物理按键。SavedMove/校正/replay尚未捕获来源边界；重放当前活来源的行为不能被本地静态消费证明。
- 三文件已停写冻结。交回本记录外部hash、两源码hash、静态结果和未验项；等待统筹审查及下一精确授权，不自行继续实现。
