# 07E2-B0-G1：GA 原生准入入口与附加条件契约

更新：2026-10-01。统筹已接受精确预检并授予三文件窄租约；组长直接完成实现与静态核对，三文件冻结交回。当前只关闭 GA C++ final 入口与业务扩展契约，尚未编译/动态验证，不表示输入失败来源修复。

## 1. 唯一目标、职责与精确范围

- 唯一目标：CanActivateAbility 保持原五参数 const 签名并设 override final，核心准入不可由派生 C++ 覆写替代；在全部核心检查通过后调用 protected virtual const CanActivateAbilityAdditional 镜像五参数扩展点。
- GA 管能力准入入口，GAS 保留原生权限、冷却、Cost、Tag 与 BP 准入执行；ASC 仍唯一拥有组规则。扩展点仅追加业务拒绝和失败 tags，不替代原生/组规则，不搬移 core 到可省略 Super 的虚方法。
- 唯一写入者为 AbilitySystem 组长本人 gpt-6.1-sol / xhigh；仅 apply_patch，不创建或唤醒代理/临时会话。
- 精确三文件：Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h；同名.cpp；本新 AAADocs/Modules/AbilitySystem/Module_Repair_07E2_B0_NativeEntrypoints.md。记录写前已核验不存在。头、实现与独立审查记录共同关闭一个 GA 入口契约。
- 非目标：ASC Notify final/评估来源凭证/InputScope 修复、Busy、绑定/K4、K3 终止/Task、网络、新角色业务、失败 fallback、测试夹具、Obsidian/Canvas、资产、UE、构建、Git。

## 2. 原文基线与只读依赖

| 文件 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h | 17436 | BEE74DC34ED2C8636192894E964FB73779C17A50E43F4B810B21911CDF58DF51 |
| Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp | 27862 | 5BA07252DE4112F44ADCD142EE43F5E8470662A3AC2AC1A28C2E187C31BD117D |

- 只读依赖：现有 GA/GAS CanActivateAbility、项目 ASC IsActivationBlockedByGroup 与失败 tags、AGENTS/排程/台账/路由、计划蓝图与 AbilitySystem 结构。Source/Plugins 已核对无其它 Can 派生 C++ 覆写，无需本阶段跨模块迁移。
- 保存两源完整原文与 hash，保护除该 h/cpp 以外248个 Source 清单项、I0/I1/I2a/B0 独立记录和 AGENTS；另保护 Content/Plugins 116个 uasset/umap。ASC 最新 h/cpp 为 36CFFA8C…/5225429C…，保持本轮租约外冻结。
- 第39次构建已覆盖 K4-I2a-API，普通73 Success；尚无本 G1 的编译/动态证据。旧第34次 B0 严格红测 1 Fail/1 Error（内层 raw retry 通知1应0）完整保留。

## 3. 冻结签名、顺序与原子依赖

- 原入口精确签名：virtual bool CanActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const override final。
- protected 扩展点：virtual bool CanActivateAbilityAdditional(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const。可由 C++ 派生覆写，默认明确“没有附加准入条件”返回 true，不承担缺失配置/错误恢复。
- final 体保留原 ActorInfo/ASC 前置 → Super::CanActivateAbility（冷却、Cost、Tag、原 K2_CanActivateAbility）→ ASC 组判断与原 Queued/普通组失败 tags 的顺序、分支和提前 false。只有原末尾 true 改为转交同一五参数 Additional 的结果；Additional 不能使先前失败转为成功。
- 原 K2_CanActivateAbility 保留在 GAS Super 内；原 NativeOnAbilityFailedToActivate/ScriptOnAbilityFailedToActivate 及其调用顺序保持。本阶段不改 UFUNCTION/FName、BP 事件接线或失败通知链。
- 顺序：登记本预检/基线 → 头 final/扩展点与 cpp 唯一末尾接入/默认实现 → 全文/逆向/保护核对 → 冻结交回。来源凭证、ASC Notify 及测试/图文另独占阶段，不能由本记录推导继续权限。

## 4. 验收断言、清理和停止点

- 原文逆向：去除新增 Additional 声明/说明/定义，恢复唯一 final 限定和 Can 末尾 true 后，必须精确恢复两源原整文；其它函数体、接口、类成员状态、头 include 与 BP 元数据保持。
- 核心严格保持：ActorInfo 前置、Super 调用/参数、ASC 查询、OptionalRelevantTags 空值分支、两种原失败 tags 及所有提前 false 完整一致；Additional 只出现于全部核心通过后的一个调用点，默认体仅明确无附加条件 true。
- 不新增来源凭证、状态/队列/计时、强资源或清理链。无新增循环依赖/第二组权威/执行器；既有来源因果缺口仍未修复，不能以 final 阶段关闭红测。
- 格式：UTF-8 无 BOM、LF、末尾换行、无行尾空白；既有保护 Source/记录和116个资产 hash 保持。专项测试另阶段，本步不写镜像实现测试或修改严格断言。
- 已只读核对 Obsidian AbilitySystem 类清单：需要后续同步 Can 的 final 与 Additional 扩展点、G1 已实施而来源仍未接的状态。统筹冻结其它图文，本步记录交接需求，不声称架构笔记已全部同步。
- 静态结果和实际三 hash 交回后立即停写，等待根验和统一构建；不续 ASC/来源/测试/图文，不运行 UE/构建/Git。

## 5. 实际证据

- 已先创建本记录，随后仅 apply_patch 修改 GA h/cpp。头新增7行扩展点/说明且唯一 Can 声明设 override final；cpp 唯一原末尾 true 改为 Additional 调用，新增6行默认实现，其它完整代码保持。
- 实际 h 为17975 bytes/383行，SHA256 `1F7C7B6E96B9AB8D2592E952B453C5F12AB10C9A02A4316565E2AA197D622CED`；cpp 为28341 bytes/769行，SHA256 `D166E350129E7356DE3528C57DB65CE3D16659FF1F7244EC15427D27AED5B4CD`。
- 用原整文和上列唯一替换/新增构造预期，两源与实际全文逐字符一致；从实际源移除扩展点声明/定义并恢复 final 限定与唯一末尾返回后，精确恢复原两份完整文本。因此核心 ActorInfo、Super 五参数、原 BP 调用位置、组查询/null tags/两原失败 tags/提前 false 及其它所有 GA 函数体保持。
- 全 Source/Plugins 搜索：Additional 仅一声明/一默认定义/一个最终调用，无派生覆写或其它新调用；原 Can 只有项目基类定义和 final 声明。默认体明确无附加条件且只返回 true，不能恢复先前核心失败；未新增角色业务、来源凭证、成员状态、include、UFUNCTION/BP 元数据或依赖。
- 248 个既有 Source 清单项、I0/I1/I2a/B0 独立记录、AGENTS 逐项 path/bytes/hash 保持，保护清单无新增/移除；116个 uasset/umap 逐项保持。ASC/I2a、严格测试及 BP/资产均未改。
- 三文件 UTF-8 无 BOM、LF、末尾换行、无行尾空白。没有新增持有资源或清理路径；无循环依赖、第二组权威/调度/执行链，业务扩展在核心检查之后，旧来源因果缺口仍开放。
- 本轮没有 UE、构建、Git、代理或测试运行；G1尚未编译/动态验证，旧34严格红测不关闭。Obsidian 的 final/Additional 与分阶段状态待另租约同步，不声称全部笔记已更新。
- 三文件最后全文/格式/hash读回后明确冻结，记录最终hash随交回消息提供；不续 ASC Notify/来源/测试或图文。以下列出本轮两源完整生产差异（未使用 Git）。

```diff
--- Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h
+++ Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h
@@ protected 扩展点（新增）
+	/**
+	 * 仅追加业务准入条件；final 入口已完成 ActorInfo、原生/BP 和组规则检查。
+	 * 默认明确没有附加条件。派生只可追加拒绝/失败 tags，不替代核心检查，
+	 * 不用本扩展点掩盖必需配置或依赖缺失。
+	 */
+	virtual bool CanActivateAbilityAdditional(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const;
+
@@ 原 Can 声明
-	virtual bool CanActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const override;
+	virtual bool CanActivateAbility(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const override final;
--- Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp
+++ Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp
@@ Can 原末尾唯一返回
-	return true;
+	return CanActivateAbilityAdditional(Handle, ActorInfo, SourceTags, TargetTags, OptionalRelevantTags);
@@ SetCanBeCanceled 前（新增）
+bool UGGYGOGameplayAbility::CanActivateAbilityAdditional(const FGameplayAbilitySpecHandle Handle, const FGameplayAbilityActorInfo* ActorInfo, const FGameplayTagContainer* SourceTags, const FGameplayTagContainer* TargetTags, FGameplayTagContainer* OptionalRelevantTags) const
+{
+	// 明确的默认模式：没有附加准入条件；核心检查由 final 入口先完成。
+	return true;
+}
+
```
