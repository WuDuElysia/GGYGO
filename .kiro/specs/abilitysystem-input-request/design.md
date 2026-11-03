# Design Document

## Overview

收敛 Hero 与 ASC 之间的能力输入请求链。行号为 2026-11-02 版本，开工重核。

改动面：
- `Source/GGYGO/Character/Components/GGYGOHeroComponent.{h,cpp}`：输入相关结构与函数
- `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.{h,cpp}`：输入段，约 1857-2949
- `Source/GGYGO/AbilitySystem/GGYGOAbilityInputRequestTypes.h`
- 受影响测试：Input、PlayerCombo、Admission

## 现状

### Hero 侧寿命对象（HeroComponent.cpp:36-162）

```
FPlayerInputSession            InputComponent 绑定寿命
 ├─ FAbilityActionBinding      每个能力输入动作
 │   └─ FAbilityInputObservation   每次按下：Request(Tag/Deadline/Token/Identity)、Association 弱引用、bActionEnded/bInvalidated
 ├─ Observations[]             含已结束但未过期的观察，供关联退役时结束 ASC 请求
 └─ FAbilityInputAssociation   Session 与 ASC 资源的关联
FLocalAbilitySystemSubscription  PawnExtension 通知订阅（第 5 步处理）
```

每个对象都有 bRetired 和 Is*Current。

`Input_AbilityActionTriggered`（1561-1588）与 `Input_AbilityActionReleased`（1642-1659）在 ASC 调用返回后重验 Hero／Binding／Session／Association。被调的 `ReceiveAbilityInputRequest`（ASC 2039-2129，含 Prune 1976-2009）与 `EndAbilityInputRequest`（2514-2576）只改 ASC 内部表与 `Spec->InputPressed`，没有外调；重写这两个函数时一并删除这些重验（由第 1 步移入）。

### ASC 侧

- Request_Record 保存 OwnerActor、AvatarActor、World 弱引用。每次查询 `IsAbilityInputContextCurrent`（1894-1906）都要再比较一遍，而 `ClearAbilityInput`（2923-2947）在 Avatar 变化与 ClearActorInfo 时已经清空全部记录并递增 Revision。
- `IsAbilityInputRequestCurrent(Request, Handle, bRequireDeadline, bRequireQueued, bRequireHeld)`（1908-1928）。
- `ReceiveAbilityInputRequest` 有 Revision 与 Serial 用尽两个分支（2075-2076）；`RecordAbilityInputQueuedWait`（2641-2662）在 uint64 用尽时重排序号。
- 公开的 `QueueAbilityInputRetry`（2578）没有生产调用方，测试也不用。

## Architecture

### Hero 侧目标结构

```
FPlayerInputSession
  Component / Subsystem / PlayerInput / ForceWalkMovement / Generation
  BindHandles / Mappings
  ActionBindings[]: FAbilityActionBinding
      SourceAction, InputTag, SourceActionPath
      CurrentRequest: FGGYGOAbilityInputRetryRequest   // Identity、Tag、Deadline、EvaluationToken
      bPressed                                         // 本次按住是否已开始
  AssociatedResource: FGGYGOPawnASCResourceHandle      // 取代 FAbilityInputAssociation
  bRetired
```

主流程：

```
Triggered(Binding):
  if (!Binding.bPressed) { 采令牌、算截止; Binding.bPressed = true; Identity = {} }
  ASC = Session.AssociatedResource 的 ASC；没有就诊断一次后返回
  Result = ASC->ReceiveAbilityInputRequest(Tag, Binding.CurrentRequest.Identity, Deadline, Token)
  首次：成功则记 Identity
  非首次：结果不是 AlreadyApplied 或身份变化 → End(Identity, Invalidated)，清空 Identity
Completed/Canceled(Binding):
  if (Identity 已分配) ASC->EndAbilityInputRequest(Identity, Released)
  Binding.bPressed = false; Identity = {}
Session 退役 / AssociatedResource 变化:
  OldASC->EndAbilityInputRequestsFromSource(SessionKey)
```

SessionKey 取 `{Hero 弱引用, Session.Generation}`，由 ASC 写入每条 Request_Record。

### ASC 侧目标结构

- `FAbilityInputRequestRecord` 删除 `OwnerActor`、`AvatarActor`、`World`，增加 `SourceKey`。
- `ProcessAbilityInput`：入口核对一次 ActorInfo 是否可用（复用现有 CanContinue 的上下文部分），外调后只核对 Revision 是否变化。
- 具名谓词：
  - `FindLiveRequest(Identity)`：Revision 与 ASC 匹配，且记录存在、身份相等
  - `IsRequestHeld(Record)`
  - `IsRetryableFor(Record, Handle)`
  - `IsBeforeDeadline(Record)`
  - `RequestMatchesSpec(Record, Handle)`：Spec 存在、未待移除、Spec 动态 Tag 含输入 Tag
- 删除 Revision／Serial 用尽分支与排队序号重排；排队顺序仍用单调递增序号。
- 删除公开的 `QueueAbilityInputRetry`，把 `QueueAbilityInputRetryInternal` 改名为私有的 `QueueAbilityInputRetry`。
- 新增 `EndAbilityInputRequestsFromSource(const FSourceKey&)`，按 Invalidated 结束该来源的全部记录。

### 不变的部分

- 边沿（Edge）合并规则：同一 Spec 多个来源合并成一次按下，最后一个来源释放才产生一次松开。
- 失败排队（`NotifyAbilityFailed` 中记录 Queued 等待）与组释放唤醒（`WakeQueuedAbilityInputRequests`）。
- `ActiveStepInputDispatch` 与分段输入、Initial 路由。
- 输入阻断标签清空全部输入。

## Error Handling

- 关联的 ASC 未就绪时首次按下：诊断一次，本次按下不进入缓冲（与现状一致）。
- Receive 被拒：按动作与原因诊断一次，不重试。
- Released 被拒：结束该身份，诊断一次。

## Testing Strategy

- GGYGO.Input 与 PlayerCombo 测试中断言 Observation、Association 内部结构的用例，改为断言外部结果：按下产生一次激活或一次缓冲；释放产生一次 Released 边沿；会话退役后旧请求不再触发。
- 新增：会话退役后，ASC 中由该会话签发的记录全部结束，其它来源（测试用的第二来源）不受影响。
- PIE 场景见 Requirement 5.3。

## 风险

- 现有测试可能直接驱动 Observation 的边界状态（例如首次 Receive 返回后关联被退役），这些在新结构中不再存在。处理办法：保留对应的外部契约断言，删除对内部状态的断言。

## 实现记录（批次 1，源码未编译）

- 来源类型：`FGGYGOAbilityInputSourceKey{TWeakObjectPtr<const UObject> Owner, uint64 Generation}`，定义在 `GGYGOAbilityInputRequestTypes.h`。Owner 为空表示无来源；比较用 `HasSameIndexAndSerialNumber`，失效弱引用仍保留原身份。Hero 会话的 Generation 可以是 0，所以不用 Generation 判断是否设置。
- Receive 的四参重载增加默认空来源参数；三参重载复核既有身份时沿用记录里的来源。既有身份复核时来源不同视为 RequestMismatch。
- 单一失效方式补一处：`InitAbilityActorInfo` 在 Owner 或 Avatar 任一变化时清空输入（原先只看 Avatar）。
- `EndAbilityInputRequest(Released)` 不再检查 ActorInfo；ActorInfo 不可用由下一次 ProcessAbilityInput 入口统一清空。
- Hero Released：关联仍是同一 ASC 时以 Released 结束，否则以 Invalidated 结束；结束被拒时 ASC 已诊断，Hero 不再追加 Invalidated。
- Hero 侧拒绝（InvalidWorldOrBufferWindow、ASCNotReady）每个动作每种原因只记一次 Warning；ASC 侧拒绝仍由 `MakeAbilityInputRequestFailure` 每次失败记一次，按住期间首次被拒后不再请求，所以不会每帧重复。
- `InvalidateAbilityActionBinding` 只结束该动作当前请求；同一动作此前已释放、仍在缓冲期的请求随会话退役按来源结束。
- 证据：`Saved/Kiro/abilitysystem-input-request/`（Before/ 与 before_manifest.tsv 为 5 个改动文件的前像；新增测试文件 `AbilitySystem/Tests/GGYGOAbilityInputSourceRetirementTest.cpp` 无前像）。
