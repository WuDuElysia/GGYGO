# Requirements Document

## Introduction

本 spec 是整改的第 1 步（共 7 步，总索引见 [活动记录](../../../AAADocs/需求文档/refactor_and_squad_switch.md)），处理低风险删减：澄清代码规范；静态配置不再在运行期反复全量校验；删除没有外调的重复核验；StartStep 按业务顺序拆分；清理过期注释。对应活动记录问题 5（其中"删除无外调重验、拆分 StartStep"部分）、6、10（过期注释部分）、11（MeleeTrace 部分）。

不在本 spec 内：以 Task 寿命作为段寿命（属于 activation-lifecycle）、GA 基类的 *ForTest 钩子（随 activation-lifecycle 一并改写）、输入请求（属于 input-request）。

2026-11-02 统筹按收窄写集授权本 spec 的源码／文档窗，以下内容移出本 spec：

| 原条目 | 去向 | 原因 |
| --- | --- | --- |
| 4.1 Hero 输入返回后的重验 | 第 2 步 input-request | 同文件由第 2 步重写 Triggered／Released |
| 6 Boss 改用共享 Montage 动作资源 | 第 4 步 activation-lifecycle | 第 4 步重写共享资源结构及 Boss 的身份／回调模型；Boss 测试依赖其 protected 接口与精确日志 |
| 7.2 ASC 组准入测试日志 | 第 4 步 activation-lifecycle | ASC.cpp 在本窗口受保护，第 4 步重写激活段 |
| 8.1 CMC 两参 BeginMontageActionMotion 合并 | 第 4 步 activation-lifecycle | 与共享资源的两个 BeginMotion 重载一并收敛 |

本 spec 的编译、测试和 Editor 消费者核查（8.2）在统筹设定的验证窗口执行，本 spec 的源码窗内不启动 UE、不构建。

2026-11-02 用户让 Kiro 按原计划自主推进（批次 1）：Requirement 2（授予期预备配置）与 Requirement 3（ActionSet 采纳期校验）改回原计划，测试夹具按 Requirement 11 调整。PlayerCombo 夹具改走真实输入属于第 2 步。

## Glossary

- **Prepared_Combo_Configuration**：PlayerCombo 授予实例按当前作者配置解析一次的各段静态声明（动作源绑定、攻击／移动接续点与 Main 末端、FX 窗口声明、Montage 窗口声明）及伤害 GE（弱引用）与伤害模式。实例首次准入时解析，只缓存成功结果；寿命等于授予（实例随移除销毁）。运行期改配置的子类或夹具须在未激活时改动并调用 `InvalidatePreparedConfiguration()`；必需 GE 类卸载或被新版本替换时视为失效。CDO 上的纯查询每次解析、不缓存。
- **Activation_Snapshot**：Body 取得的 Prepared_Combo_Configuration 共享引用，本次激活内各段与命中只读它，终止清理时释放。
- **External_Call**：会执行其它代码并可能改变原资源的调用，只包括：BP／K2 事件、有外部订阅的多播委托、EndAbility／CancelAbility／EndTask、Montage Stop／BlendOut 回调、Actor 或组件销毁、RPC／OnRep，以及实际存在此类覆盖实现的虚函数。
- **Redundant_Recheck**：在两次之间没有 External_Call、也没有能改变谓词的自有写入时重复执行的同一核验。

## Requirements

### Requirement 1: 代码规范澄清

**User Story:** 作为模块作者，我希望规范明确什么情况才需要重验和签发身份，这样不会把每次调用都当成重入点。

#### Acceptance Criteria

1. THE CodeConventions SHALL 把"外调"定义为 External_Call 的正向清单，并要求每处返栈重验在注释或代码结构上能对应到其中一种。
2. THE CodeConventions SHALL 规定：保留后置检查的一方须指出会改变该谓词的那一次外调或自有写入，指不出则删除。
3. THE CodeConventions SHALL 规定 ABA 首选原生寿命（AbilityTask 随 EndAbility 结束、Task 委托随 EndTask 解绑、Timer 在清理时 Clear），只有回调能越过拥有者寿命时才签发身份；一个寿命一个身份，同一拥有者同一寿命的身份应合并。
4. THE CodeConventions SHALL 允许有明确来源、寿命和失效点的预备配置（如授予期首次准入解析、只缓存成功结果、改配置方显式失效），IsDataValid 保留完整校验，并说明这不属于"未经失效管理的跨帧 Valid 缓存"。
5. THE CodeConventions SHALL 规定 64 位单调计数不做耗尽判断，只对上网络或序列化的窄字段处理环绕。
6. THE CodeConventions SHALL 规定结果枚举只列真实消费者会分支的结果，其余原因写入诊断。
7. THE CodeConventions SHALL 在"不以瘦身名义进行的改动"之外增加"应主动退役的模式"：重复订阅样板、给原生入口再包一层、事后扫描兜底、主流程里的测试钩子与测试日志、无消费者的兼容分支、写着任务阶段的注释。
8. WHEN 修改 CodeConventions, THE 作者 SHALL 以统筹给定的基线身份为前提原位修改，保留他人已有内容，且不改动与本 Requirement 无关的条款。

### Requirement 2: PlayerCombo 预备配置

**User Story:** 作为战斗作者，我希望一次授予内连段配置只解析一次，运行期只检查真正会变的输入。

#### Acceptance Criteria

1. THE CanActivateAbilityAdditional、NativeOnAbilityFailedToActivate 与 Body SHALL 共用 `FindOrPrepareConfiguration`：命中缓存直接返回；否则依次核对伤害依赖、解析全部段、核对伤害模式，成功时（仅授予实例）写入 Prepared_Combo_Configuration。
2. THE 拒绝日志 SHALL 保持分类与文字：准入被拒时伤害依赖或模式失败报"激活失败时伤害GE依赖无效"，段配置失败报"激活失败时连段配置无效"；Body 取不到配置时分别报"提交前拒绝激活"与"提交前连段配置无效"。纯 CanActivate 查询不写日志。
3. THE ValidateComboConfiguration SHALL 只调用纯解析函数 `PrepareComboSteps`，不读写缓存，返回值与错误文字不变；IsDataValid 继续调用它并保留完整校验与报错内容。
4. THE Body SHALL NOT 在蓝图激活回调后重新校验：段、GE 及其选择字段为 EditDefaultsOnly＋BlueprintReadOnly，回调改不了。Body 把配置存为 Activation_Snapshot。
5. WHEN StartStep 起一段, THE PlayerCombo SHALL 从 Activation_Snapshot 读取该段的动作源、接续点、FX 窗口和 Montage 窗口，SHALL NOT 在运行期重新解析这些静态数据。
6. THE HandleMeleeHit SHALL 只使用 Activation_Snapshot 的 GE 与模式：GE 类已卸载或被替换时中止原激活；返回 Spec 的 Def 不是该 GE 的 CDO 时中止；保留伤害键冲突检查（AbilitySpec 的 SetByCaller 可能冲突）。SHALL NOT 再调用 GE 依赖校验或段数值校验。
7. WHEN 能力终止清理, THE PlayerCombo SHALL 释放 Activation_Snapshot；Initialize 把未释放的快照视为未归还资源。

### Requirement 3: Boss 招式与选招的运行期校验

**User Story:** 作为 BossAI 作者，我希望选招和招式执行不再每次重做全表校验。

#### Acceptance Criteria

1. THE BossMelee SHALL 在一次激活内只解析一次资产配置：Commit 前的 ResolveMeleeConfiguration 写入本次资源，Commit 后只复核运行接收者与播放速率。
2. THE BossState SHALL 在 InitializeFromDefinition 采纳定义前校验全部阶段的非空 ActionSet；任一失败则诊断并拒绝采纳（不写定义、形态与阶段标签）。
3. THE SelectAction、StoreActionSelection、ConsumeActionSelection、BTTask_GGYGOChooseBossAction、BTTask_GGYGOActivateAbility SHALL NOT 做 ActionSet 全表校验，只核对被选动作行与 Spec。编辑器另有 ActionSet::IsDataValid。
4. THE 原 SelectAction(坏表) 用例 SHALL 改为采纳期用例：坏表放在非初始阶段，断言拒绝采纳与诊断恰好一次，再以合法定义采纳成功。

### Requirement 4: 删除无外调的重复核验

**User Story:** 作为维护者，我希望主流程只在真实外调之后重验，读代码时能看清业务步骤。

#### Acceptance Criteria

1. （移入第 2 步）
2. THE PlayerCombo StartStep SHALL 删除：提前 ClearWatchdog 及其后重验（ReleaseStepMotion 已清 Watchdog）、ReleaseTraceWindow 之后的重验、两次 CurrentMontageSetNextSectionName 之后的重验（引擎实现无本地回调）、StepTokenCounter 的 uint64 耗尽判断；保留 ReleaseStepFX 与 ReleaseStepMotion 之后的重验，保留 StepSyncRevision 与 SourceRequestId 的窄字段检查。
3. THE PlayerCombo HandleMeleeHit SHALL 只在 GetAbilitySystemComponent(HitActor)、BuildHitEffectPayload、ApplyGameplayEffectSpecToTarget 等真实外调之后重验；重核确认现状已满足，不改动。
4. THE GameplayAbility BuildHitEffectPayload SHALL 删除 MakeEffectContext、ApplyAbilityTagsToGameplayEffectSpec 之后的 HasOriginalObjects 重验；保留全部 HasValidRequiredSpec 检查（测试覆盖 ApplyAbilityTags 后 Spec 失效），保留 MakeOutgoingSpec、BP_EditSpecValues 之后的检查。
5. WHEN 删除任一重验, THE 作者 SHALL 确认其不承担必要诊断；若承担诊断，则合并为一次诊断。

### Requirement 5: StartStep 按业务顺序组织

**User Story:** 作为战斗作者，我希望起段函数按"读运行输入 → 释放旧段 → 起新段"三步读下来。

#### Acceptance Criteria

1. THE PlayerCombo SHALL 把 StartStep 拆成三个具名步骤：ReadStepStartInputs（入场尝试、请求号、预备段、Facing 请求、纠正 basis、CMC、当前 Mesh 的 Socket 与 TraceShape）、ReleaseCurrentStep（Trace、FX、位移）、BeginStep（签发段令牌、创建 Task、配置窗口与通知、Ready、初始化位移、挂 Watchdog）。
2. THE StartStep SHALL 把静态配置错误移到预备配置阶段，运行期失败分支只保留：入场尝试不匹配、请求号越界、预备段或运行组件失效、输入请求缺失、纠正 basis 无效、CMC 不可用、当前 Mesh 缺 Socket 或 TraceShape 不适配、Task 工厂失败、实际速率无效、窗口／通知配置失败、Ready 后 Task 未保持活动、位移初始化失败、Watchdog 设置失败。
3. THE StartStep 的外部可观察行为 SHALL 保持不变：段序、起始 Section、Facing 策略、纠正重放复用原 basis、FX 窗口在纠正起点之后不补播。

### Requirement 6: Boss 改用共享 Montage 动作资源

移入第 4 步 activation-lifecycle（见该 spec 的 Requirement 10）。

### Requirement 7: 过期注释

#### Acceptance Criteria

1. THE MontageGuardAnimInstance.h 文件头注释 SHALL 改为描述当前契约，删除"A2"等任务阶段描述。
2. （ASC 组准入测试日志移入第 4 步）
3. WHEN 删除任何分支或机制, THE 作者 SHALL 同步删除不再成立的注释。

### Requirement 8: 低影响转发

#### Acceptance Criteria

1. （CMC 两参入口合并移入第 4 步）
2. WHEN 处理 MeleeTrace 的 Legacy BeginTraceWindow／EndTraceWindow, THE 作者 SHALL 在验证窗口的 Editor 中查找蓝图与 AnimNotify 消费者；无消费者则删除这两个 UFUNCTION 及 Legacy 窗口来源；有消费者则保留并在注释中写明消费者，不在本 spec 内迁移。文本搜索无引用不作为删除依据。
3. THE CMC 其余对 FGGYGOActionMotionExecution 的一行转发 SHALL 保留，因为 CMC 是唯一对外位移入口。

### Requirement 9: 不回退的行为

#### Acceptance Criteria

1. THE 系统 SHALL 保持普攻三段、技能、Boss 近战的段序、伤害（攻击力×段倍率、绝对值模式）、PoiseDamage、命中 Cue、FX 窗口与 Montage 窗口时点不变。
2. THE 系统 SHALL 保持 Montage 完成与位移完成两个独立事实都到达后才算一段完成。
3. THE 系统 SHALL 保持必需配置无效时明确拒绝并诊断，不以默认资源、零输出或另一能力替代。

### Requirement 10: 验收

#### Acceptance Criteria

1. WHEN 统筹设定验证窗口, THE 作者 SHALL 编译 GGYGOEditor Win64 Development 并通过；编译前在聊天告知，并检查内存、磁盘与既有新增额度。
2. THE 作者 SHALL 在一次 NullRHI 编辑器会话中运行并通过 GGYGO.AbilitySystem.PlayerCombo、GGYGO.AbilitySystem.HitSemantics、GGYGO.BossAI（实际 39 例）。Admission 与 Combat 不引用本 spec 改动的类，本轮不纳入。
3. THE NullRHI 结果 SHALL NOT 代替人工 GUI 画面、FX 联机或 Legacy 消费者核查；这三项保持未验证，Legacy 不删除。
4. IF 任一测试失败, THEN THE 作者 SHALL 保留失败日志并修复，SHALL NOT 降低断言或排除场景。
5. WHEN 验收通过, THE 作者 SHALL 在活动记录中更新本 spec 的状态与证据路径。

### Requirement 11: 测试夹具不迁就旧行为

#### Acceptance Criteria

1. WHEN 夹具在授予后修改作者配置（段、伤害 GE、所引用的临时 Montage）, THE 夹具 SHALL 只在未激活时修改，并先调用 `InvalidatePreparedConfiguration()`。
2. THE 测试 SHALL NOT 在激活中途修改作者配置：删除 TraceShape 用例的 K2 回调清 Shape 与 RuntimeHit 的 MissingMultiplier；缺失倍率由 Multiplier 用例的纯准入负例覆盖。
3. THE RuntimeHit InvalidRequiredGE SHALL 改为实际请求在准入被拒（"激活失败时伤害GE依赖无效"恰好一次），再恢复合法 GE 走正常命中。保留 ConflictingDamageKey（AbilitySpec SetByCaller）与 InvalidRequiredSpec（Builder）的运行期故障。
4. THE 生产 Error SHALL 以恰好一次的预期声明，不降级、不屏蔽：TraceShape.InvalidConfiguration 的准入拒绝、RequiredTreeRejectsInvalidRoot 的两条启动失败。
5. THE HitSemantics 距离专项 SHALL 使用带 GameInstance（含 MessageRouter）的世界，因为伤害结算会发布生命消息。
