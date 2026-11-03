# Requirements Document

## Introduction

本 spec 是整改的第 5 步，总索引见 [活动记录](../../../AAADocs/需求文档/refactor_and_squad_switch.md)，对应问题 3、4。

现状：ASC 绑定到 Pawn 要经过七层：
1. PawnExtension 发起 Host 请求；
2. CombatantState 处理请求，并按条件选择三个 Try 入口之一；
3. ASC 执行事务、提交 Context 序号、签发发布回执；
4. 发布通知；
5. PawnExtension 安装本地资源并发出 Ready；
6. Hero、CMC、Health 各自用一份约 240 行的订阅样板接收。

与此同时，原生的 InitAbilityActorInfo／ClearActorInfo 覆盖仍作为"Legacy 写入"入口存在。

目标：
- 按 Lyra 的做法收敛：CombatantState 负责把自己的 ASC 绑到当前 Avatar Pawn；
- PawnExtension 广播"ASC 就绪／释放"，消费方用同一个订阅类型接收；
- 删除事务、回执、身份操作和失败初始化清理协议；
- 同时完成 ASC 的剩余拆分：输入缓冲和分段输入路由改为 ASC 私有的普通 C++ 协作者。

换人前提：用户已确认允许多人同时在场。每个 CharacterSlot 有自己的 ASC 和 Avatar，换人不重新绑定 ASC，只换控制权（第 6 步实现续放）。

依赖：第 4 步 abilitysystem-activation-lifecycle 已验收。

## Glossary

- **Host**：`AGGYGOCombatantState` 及其子类 CharacterSlot、BossState，持有 ASC 与 Avatar 引用。
- **Avatar_Binding**：把 Host 的 ASC 的 ActorInfo 设为 (Host, AvatarPawn)，以及解除绑定。
- **ASC_Ready_Notice**：PawnExtension 在其 Pawn 成为某 ASC 的 Avatar 后广播的就绪通知，携带 ASC 与本次绑定的资源句柄。
- **ASC_Released_Notice**：解除绑定时的释放通知，携带同一资源句柄。
- **Local_ASC_Subscription**：PawnExtension 提供的订阅类型，封装 RegisterAndCall、即时回放、退订和"当前资源"查询，供 Hero、CMC、Health 共用。
- **Binding_Protocol**：将被删除的绑定协议：
  - `FGGYGOAvatarBindingPublicationReceipt`、`FGGYGOAvatarBindingProtocol` 的事务部分；
  - ASC 中的 IdentityOperation、ActualSnapshot、FailedInitCleanup、NativeWriteBusy、PublicationRecord；
  - TryExecute／TryBootstrap／TryReplaceRevoked 三个入口；
  - Host 的步骤历史 `FGGYGOAvatarBindingHostResult::Steps`；
  - Legacy 写入拒绝逻辑。
- **Input_Buffer**：ASC 的能力输入请求、边沿、重试与 ProcessAbilityInput 逻辑。
- **Step_Input_Router**：ASC 的分段输入 TargetData 路由与 Initial 路由。

## Requirements

### Requirement 1: 单一的本地 ASC 订阅

**User Story:** 作为组件作者，我希望订阅"本 Pawn 的 ASC 就绪／释放"只需要几行代码，各组件不再各写一份样板。

#### Acceptance Criteria

1. THE PawnExtension SHALL 提供 Local_ASC_Subscription，接口为：订阅（注册时若已就绪立即回放一次 ASC_Ready_Notice）、退订、查询当前就绪的 ASC 与资源句柄。
2. THE HeroComponent、CMC、HealthComponent SHALL 改用 Local_ASC_Subscription，删除各自的 FLocalAbilitySystemSubscription／FAbilitySystemResource 样板。
3. WHEN 收到 ASC_Ready_Notice 的资源与已消费的相同, THE 消费方 SHALL 不做任何事（重复就绪）。
4. WHEN 收到 ASC_Released_Notice, THE 消费方 SHALL 只在资源与已消费的相同时清理。
5. WHILE 订阅回放或通知分发进行中, IF 消费方在回调里退订或重新订阅, THEN THE Local_ASC_Subscription SHALL 保证不向已退订的订阅者继续分发，也不丢失新订阅者的回放。

### Requirement 2: Lyra 式绑定流程

**User Story:** 作为角色作者，我希望 ASC 绑到 Pawn 的流程一眼能读懂：解绑旧的、绑新的、广播。

#### Acceptance Criteria

1. WHEN Host 在权威端调用 AttachAvatar(NewPawn) 或客户端收到 OnRep_AvatarPawn, THE Host SHALL 按顺序执行：
   1. 若 ASC 当前 Avatar 不是 NewPawn，先释放旧 Avatar；
   2. 对 NewPawn 调用 ASC->InitAbilityActorInfo(Host, NewPawn)；
   3. 让 NewPawn 的 PawnExtension 广播 ASC_Ready_Notice。
2. WHEN 释放 Avatar, THE Host SHALL 依次：
   1. 取消该 ASC 上的活动能力；
   2. 清空能力输入；
   3. 移除 Avatar 相关的 GameplayCue；
   4. 让旧 Pawn 的 PawnExtension 广播 ASC_Released_Notice；
   5. ClearActorInfo 或改绑到新 Avatar。
3. WHEN Pawn 的 Controller 变化, THE PawnExtension SHALL 调用 ASC->RefreshAbilityActorInfo，SHALL NOT 经过 Host 请求。
4. IF 绑定过程中经回调（OnAvatarSet、BP 事件）再次请求同一 Host 的绑定, THEN THE Host SHALL 拒绝嵌套请求并诊断一次。
5. THE Host SHALL 只在当前 Avatar 已失效（销毁或 EndPlay）时处理延迟到达的解绑，不处理已被替换的旧 Pawn。
6. THE Host SHALL 直接返回绑定结果（成功、拒绝原因），调用方 SHALL NOT 遍历步骤历史。

### Requirement 3: 删除绑定协议

#### Acceptance Criteria

1. THE ASC SHALL 删除全部 Binding_Protocol；InitAbilityActorInfo、ClearActorInfo、RefreshAbilityActorInfo 覆盖只保留：Avatar 变化时清空能力输入、Avatar 相关的 Montage 播放状态复位。
2. THE `FGGYGOAvatarBindingContext` 的消费方（CMC、FX 移动来源身份、Initial 路由等）SHALL 改用 PawnExtension 的资源句柄或 ASC 当前 ActorInfo；开工重核列出全部消费方。
3. THE CombatantState SHALL 删除 InitializeAvatarBinding／ReleaseAvatarBinding／RefreshAvatarBinding 的事务实现与 FindClearCommit，改为 Requirement 2 的流程。
4. THE IGGYGOAvatarBindingHostInterface SHALL 收敛为 PawnExtension 实际需要的最小接口（取得 Host 的 ASC），开工重核其消费方。

### Requirement 4: ASC 剩余拆分

**User Story:** 作为能力系统作者，我希望 ASC 只承担 GAS 原生职责与组准入，输入缓冲和分段输入路由各自成为可单独阅读的协作者。

#### Acceptance Criteria

1. THE ASC SHALL 把 Input_Buffer 移入私有协作者 `FGGYGOAbilityInputBuffer`（普通 C++ 类型，ASC 成员）；ProcessAbilityInput 仍是 ASC 公开方法，内部委托给该协作者。
2. THE ASC SHALL 把 Step_Input_Router 移入私有协作者 `FGGYGOAbilityStepInputRouter`；原生 RPC 覆盖（ServerSetReplicatedTargetData／Cancelled）留在 ASC，内部委托。
3. THE 协作者 SHALL NOT 持有自己的 Tick、计时器或帧调度，只在 ASC 调用时执行。
4. THE ASC SHALL 保留组准入与 TagRelationshipMapping 逻辑。
5. THE 属性反算（TryCalculateNumericAttributeBaseForCurrentValue）留给第 7 步迁移，本 spec 不动。

### Requirement 5: 多人同时在场的前提

#### Acceptance Criteria

1. THE 绑定流程 SHALL 只依赖"每个 Host 的 ASC 绑定其自己的 Avatar"，SHALL NOT 假设场上只有一个已绑定 Avatar。
2. WHEN 换人, THE 系统 SHALL NOT 解绑或重新绑定任一 Host 的 ASC，只改变 Controller 的 Possess 对象；PawnExtension 按 Requirement 2.3 刷新 ActorInfo。

### Requirement 6: 不回退的行为

#### Acceptance Criteria

1. THE 系统 SHALL 保持玩家出生、死亡、重生、Boss 出场的 ASC 绑定与 Hero 输入、镜头、移动集、生命值初始化顺序不变。
2. THE 系统 SHALL 保持旧 Avatar 的输入、能力、Cue、FX 不会延续到新 Avatar。
3. THE 系统 SHALL 保持客户端在 OnRep_AvatarPawn 与 PlayerState 复制后完成同样的就绪流程。
4. THE 系统 SHALL 保持死亡状态投影到 ASC 的现有行为（Combatants.DeathProjection）。

### Requirement 7: 验收

#### Acceptance Criteria

1. WHEN 本 spec 全部任务完成, THE 作者 SHALL 编译 GGYGOEditor 并通过。
2. THE 作者 SHALL 运行并通过以下测试：
   - GGYGO.Combatants
   - GGYGO.AbilitySystem（ActorInfoTransaction 改写为绑定流程测试）
   - GGYGO.Teams
   - GGYGO.BossAI.Encounter
   - GGYGO.Input
   - GGYGO.Movement.Locomotion
3. THE 作者 SHALL 在 PIE 中验证：出生后可移动与攻击；死亡与重生；Boss 出场后出招；编队内切换角色后新角色可操作，旧角色能力按当前规则处理。
4. THE 作者 SHALL 做最小联机验证：客户端出生、移动、攻击正常；客户端切换角色后服务器与其他客户端看到正确的角色。
5. WHEN 验收通过, THE 作者 SHALL 更新活动记录。
