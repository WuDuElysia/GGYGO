# Requirements Document

## Introduction

本 spec 是整改的第 2 步，总索引见 [活动记录](../../../AAADocs/需求文档/refactor_and_squad_switch.md)，对应问题 7：能力输入请求在 HeroComponent 与 ASC 两边各记一套账，ASC 内部又有三重失效。目标是：Hero 只记每个输入动作当前的请求身份，ASC 只用"Revision 递增 + 清空记录"一种方式让请求失效。玩家可感知的输入行为保持不变。

依赖：第 1 步 abilitysystem-redundancy-cleanup 已验收。本地 ASC 订阅结构（FLocalAbilitySystemSubscription）留给第 5 步 combatants-avatar-binding 处理，本 spec 不改。

## Glossary

- **Input_Session**：Hero 上一次 InputComponent 绑定的寿命，含映射、绑定句柄和各输入动作的绑定。对应现有 `FPlayerInputSession`。
- **Action_Binding**：Input_Session 内一个能力输入动作的绑定。对应现有 `FAbilityActionBinding`。
- **Request_Identity**：ASC 签发的输入请求身份 `FGGYGOAbilityInputRequestIdentity{SourceASC, InputRevision, RequestSerial}`。
- **Request_Record**：ASC 内对一个 Request_Identity 的记录：输入 Tag、缓冲截止时间、移动输入评价令牌、匹配的 Spec、是否按住、可重试的 Spec、排队序号。
- **Input_Revision**：ASC 的输入版本号。ActorInfo 的 Avatar 变化、ClearActorInfo、输入被阻断时递增，并清空全部 Request_Record。
- **Buffered_Retry**：缓冲窗口内，能力因组占用等原因激活失败后排队、组释放时重试的现有机制。
- **Qualified_Held**：现有"按住"语义，以及"先释放再按下才算新请求"的规则（修复清单决定 #4）。

## Requirements

### Requirement 1: Hero 只记当前请求身份

**User Story:** 作为输入作者，我希望 Hero 只保存每个输入动作当前那次按下对应的请求身份，不再维护观察记录、关联记录等多层寿命对象。

#### Acceptance Criteria

1. THE Action_Binding SHALL 直接保存当前按下的 Request_Identity、缓冲截止时间、移动输入评价令牌和"动作已结束"标志；THE HeroComponent SHALL 删除 `FAbilityInputObservation`。
2. THE Input_Session SHALL 直接保存其关联的 ASC 资源句柄；THE HeroComponent SHALL 删除 `FAbilityInputAssociation`。
3. WHEN 输入动作首次 Triggered, THE HeroComponent SHALL 调用一次 ReceiveAbilityInputRequest 并在成功时保存返回的 Request_Identity；后续同一次按住的 Triggered SHALL 以该身份调用 Receive，结果不一致时结束该身份。
4. WHEN 输入动作 Completed 或 Canceled, THE HeroComponent SHALL 以 Released 结束当前 Request_Identity。
5. WHEN Input_Session 退役或其关联的 ASC 资源变化, THE HeroComponent SHALL 一次性请求 ASC 结束本 Input_Session 签发的全部请求，SHALL NOT 自行保存已结束但未过期的请求列表。
6. THE HeroComponent SHALL 删除 ReceiveAbilityInputRequest／EndAbilityInputRequest 返回后对 Hero、Binding、Session、Association 的重验，前提是开工重核确认这两个 ASC 函数仍只改 ASC 内部表与 `Spec->InputPressed`、不包含外调（本条由第 1 步收窄时移入）；保留对两者返回结果本身的处理。

### Requirement 2: ASC 单一失效方式

**User Story:** 作为能力系统作者，我希望输入请求只靠一种机制失效，避免同一事实被检查三遍。

#### Acceptance Criteria

1. THE Request_Record SHALL NOT 保存 Owner、Avatar、World 的弱引用快照；请求是否有效只由 Input_Revision 和记录是否存在决定。
2. WHEN ProcessAbilityInput 开始处理, THE ASC SHALL 核对一次当前 ActorInfo 的 Owner、Avatar、World 是否可用；不可用时清空输入并返回。WHEN 处理过程中发生外调（原生 Try、AbilitySpecInputPressed／Released）, THE ASC SHALL 只在外调返回后核对 Input_Revision 是否变化。
3. THE ASC SHALL 用具名谓词替代带三个 bool 参数的 IsAbilityInputRequestCurrent，每个谓词只表达一个事实：记录有效、仍按住、仍可重试、未过截止时间。
4. THE ASC SHALL 删除 RevisionExhausted、SerialExhausted 返回原因和排队序号用尽后的重排逻辑。
5. THE ASC SHALL 提供按来源结束请求的入口（供 Requirement 1.5 使用），Request_Record 记录其来源 Input_Session 的标识。
6. THE ASC SHALL 删除没有生产与测试消费者的公开 QueueAbilityInputRetry 包装；开工重核确认它不是 UFUNCTION。

### Requirement 3: 结果与诊断

#### Acceptance Criteria

1. THE `EGGYGOAbilityInputRequestOutcome` SHALL 只保留 Hero 实际分支的结果：Accepted、AlreadyApplied、Rejected、Stale。
2. THE `EGGYGOAbilityInputRequestReason` SHALL 只保留仍可能产生的原因，用于诊断，不作为分支依据。
3. WHEN 请求被拒绝, THE HeroComponent SHALL 按输入动作和原因各诊断一次，SHALL NOT 每帧重复。

### Requirement 4: 不回退的行为

#### Acceptance Criteria

1. THE 系统 SHALL 保持缓冲窗口内的按下在能力因组占用失败后排队，组释放时重试一次；超过截止时间的不再重试。
2. THE 系统 SHALL 保持 Qualified_Held：按住期间不重复产生新请求；先释放再按下才算新请求。
3. THE 系统 SHALL 保持 ProcessAbilityInput 是 ASC 输入的唯一消费者，且在 PlayerController PostProcessInput 中调用。
4. THE 系统 SHALL 保持移动输入评价令牌随请求传递，分段起始方向（StepInput、Initial 路由）行为不变。
5. THE 系统 SHALL 保持输入被阻断（Gameplay.AbilityInputBlocked）时清空全部输入。
6. THE 系统 SHALL 保持 WhileInputActive 能力在按住期间每帧尝试激活的现有行为。

### Requirement 5: 验收

#### Acceptance Criteria

1. WHEN 本 spec 全部任务完成, THE 作者 SHALL 编译 GGYGOEditor 并通过。
2. THE 作者 SHALL 运行并通过 GGYGO.Input、GGYGO.AbilitySystem.PlayerCombo、GGYGO.AbilitySystem.Admission。
3. THE 作者 SHALL 在 PIE 中验证：连段缓冲输入在下一段生效；能力被占用时缓冲按下在释放后生效；超过缓冲窗口的按下不生效；按住不重复触发。
4. THE 作者 SHALL 在活动记录中注明真实键盘／手柄设备手感需用户试玩确认。
5. WHEN 验收通过, THE 作者 SHALL 更新活动记录。
