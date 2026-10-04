# 07E2-B0-G2：ASC 失败入口 final 契约

更新：2026-10-02。统筹接受精确预检并授予两文件窄租约；组长直接完成唯一 final 改动与静态核对，两文件冻结交回。本步只封闭 ASC C++ 失败入口，复用 GA 既有薄业务扩展；尚未编译/动态，来源凭证尚未实现，旧34严格红测不关闭。

## 1. 唯一目标与精确文件

- 唯一目标：ASC NotifyAbilityFailed 保持原三参数、protected、非 const，只追加 override final；失败来源归属、retry 判定及路由继续留在 ASC 原函数体。
- 精确写入：Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h；本新 AAADocs/Modules/AbilitySystem/Module_Repair_07E2_B0_FailureEntrypoint.md。记录写前不存在。ASC.cpp 是只读依赖，不扩第三文件。
- 唯一作者：AbilitySystem 长期组长 gpt-6.1-sol / xhigh，直接 apply_patch，不创建代理或临时会话。
- 非目标：来源评估凭证/InputBridge、真实 Busy、K4 执行器/Notice、K3 终止/Task、网络协议、GA/业务/BP/测试/资产、Obsidian/Canvas、UE/构建/Git。

## 2. 基线与只读依赖

| 文件 | Bytes | SHA256 |
| --- | ---: | --- |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h | 24344 | 36CFFA8C5157EF421D2DF41613890D613EE9008DD7A34116BD1107E2361D89AD |
| Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp（只读） | 71158 | 5225429C07A0D9E020B1D2E7D3682A1C12597496BAA1DC873D2BCDC7C3DCD794 |

- 只读依赖：原 Notify 函数体、GA OnAbilityFailedToActivate/NativeOnAbilityFailedToActivate/ScriptOnAbilityFailedToActivate、现有客户端 RPC、AGENTS/排程/台账、已定位的 Obsidian AbilitySystem 结构。Source/Plugins 没有派生 Notify C++ 覆写，不需要迁移现有代码或 BP 事件。
- 保存原头完整文本及基线 hash；保护其它249个 Source 清单项及 G1/B0/I0/I1/I2a 记录与 AGENTS，另保护116个 uasset/umap。
- 统筹告知 Gate40 启动被 UBT 默认用户日志目录的沙箱访问拒绝，尚未编译、无新 DLL；不能视为 G1/G2 构建通过。第39次正常73 Success不证明本 final 改动，旧34来源红测仍开放。

## 3. 固定接口、责任与顺序

- 唯一声明改动：virtual void NotifyAbilityFailed(const FGameplayAbilitySpecHandle Handle, UGameplayAbility* Ability, const FGameplayTagContainer& FailureReason) override final。
- 薄业务扩展复用 GA 既有 protected virtual void NativeOnAbilityFailedToActivate(const FGameplayTagContainer& FailedReason) const；保持其可覆写和随后 ScriptOnAbilityFailedToActivate 调用。不增加 ASC 业务虚 helper、反馈广播或第二表现权威。
- 原执行顺序完整保持：捕获/屏蔽 retry 上下文 → Super 失败委托 → 原 retry 判定/广播 → 本地 HandleAbilityFailed 或原客户端 RPC。远端原 RPC 接收链同样进入 GA Native→Script；final 不代表远端反馈已同步完成。
- 核心执行体不改、不搬到可绕过的虚方法；不制造来源证明或改变原失败/成功值。当前无派生 Notify 覆写，因此 final 只约束未来 C++ 扩展，现有运行行为保持，无需等待来源接口才能实施。
- 先登记记录 → 唯一头声明追加 final → 全文/逆向/保护/格式核对 → 两文件冻结交回；来源协议和图文同步各另门禁。

## 4. 验收、清理与停止点

- 完整逆向：实际头只移除这一声明新追加的 final，逐字符恢复原整文；所有其它声明、状态、includes、K4 Receipt/API 和 GA G1 保持。cpp 与全部保护源码/记录/资产 hash 不变。
- 格式为 UTF-8 无 BOM、LF、末尾换行、无行尾空白。没有新增资源、状态、计时或清理责任；无循环依赖、第二失败来源/组权威或反馈执行链。
- Obsidian 后续需同步 ASC Notify final、复用 GA Native 扩展及来源仍开放状态；统筹冻结图文，本步仅记录交接，不宣称全部笔记已同步。
- 本步未修复外层 retry 误借给内层 raw 的因果缺口，不调整旧34严格断言；生产来源预检/实现与专项测试另阶段。
- 最后实际两 hash 及逆向/保护结果交回即停止写入，不运行 UE/构建/Git，不续来源代码或其它文件。

## 5. 实际证据

- 写入顺序已完成：先创建本记录，再仅在 ASC.h 的原 NotifyAbilityFailed 三参数声明追加 final；头增加6 bytes，行数仍492。没有第三文件生产写入，cpp 函数体完整保持。
- 实际头为24350 bytes，SHA256 `51D3EEA90F69A87424425C4373872AFD839FEFAD48EE73EAFAA4C0A51FC69275`。用原整文做这一处精确替换后与实际全文一致；从实际头移除唯一新增 final 后，精确恢复原整文及基线 36CFFA8C…。
- 其它249个 Source 清单项及 G1/B0/I0/I1/I2a 记录、AGENTS 逐项 bytes/hash 保持，清单无新增/移除；116个 uasset/umap 逐项保持。ASC.cpp 保持71158 bytes/5225429C…，GA G1 与所有严格测试保持。
- 两文件 UTF-8 无 BOM、LF、末尾换行、无行尾空白。没有新增资源/状态/清理责任、跨模块依赖、虚 helper、反馈广播或业务 fallback；既有 GA Native→Script 与 RPC 链完整保留。
- 本步未运行 UE/构建/Git/测试/代理，G1/G2 尚未由新构建验证，旧34来源红测保持开放。统筹将接管合并构建；来源协议仍只有只读预检，Obsidian 后续同步需求保留。
- 最后两文件完整读回和实际 hash 交回后明确冻结，不再写入；本记录最终 hash 随冻结消息提供。
