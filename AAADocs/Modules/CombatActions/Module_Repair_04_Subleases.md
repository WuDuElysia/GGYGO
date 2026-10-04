# 第04批文件子租约

## 第19次门禁记录同步与 Task 候选（2026-09-30，当前仅记录授权）

统筹接收 StartedPositive 静态交回后，已完成第19次完整构建及新 DLL 常规回归。组长 `gpt-6.1-sol / xhigh` 本次仅可写本文件与 `AAADocs/Modules/CombatActions/Module_Repair_04_Validation.md`，核对实际报告/日志后同步记录并冻结；所有生产/测试源码、资产、Obsidian 和全局文件均无写入授权，不运行 UE/构建/Git/代理。

- 实际门禁：第19次完整构建 Succeeded，4 actions、10.68 秒；`ModuleRepairGate_20260930_19/index.json` 于 06:18:16 UTC 记录 51 Success、其余状态全 0、0.46889397501945496 秒，UE exit0。StartedSuccessorPreservation 实际 Success、0 errors/warnings；不同资产准确 A/B ID 0/1，同资产 2/3；两场景 Started 各 1、Call 1/2、Generation 2/2、A Superseded/三种返回 0、B Accepted/三种返回 1、B 0.650/SuccessorStart 及 28 字段保持。
- 历史门禁：第18次在 Messages 新诊断 API 处编译失败，21.38 秒，未成功链接/运行；下文实现时“未编译/运行”属于第19次之前的历史静态状态。原生 P1 最新独立证据仍为第17次 1 Fail/16 errors/0 warnings，不能用本次 Guarded Success 改写原生兼容风险或关闭全部 B4。
- 源码仍冻结：Task H `6C75E4233254776D98BE6371F57EDF60724E453E8275B5BF7691749AB59185B3`、CPP `506AAFB79129EED88485BF8185284CA13781CCE21F6796F907C334F1E1B1D02D`；测试 H/CPP 保持下文 StartedPositive 冻结哈希。
- 已接受的只读 Task 候选：Guard 路径唯一消费 ASC typed 栈上结果/Animation identity，不参与旧 attempt/map/资产扫描裁决；Task 仅提供纯活性附加查询并持原资源句柄/只读身份。Accepted 仍需独立准确实例与 ASC/GA 权限证明；Superseded 不清后继；已结束 Task 的补清理仅用栈上准确 CreatedId。
- 候选顺序与精确文件（**全部未获实现租约**）：T1 为 Task `.h/.cpp` 加 04 两记录（4文件）；T2 为新 `Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskGuardedLifecycleTest.cpp`、新 `GGYGOMontageTaskGuardedTestTypes.h` 加 04 两记录（4文件）；T3 无后继 owner end、T4 同 GA 再激活、T5 Avatar 更换分别只候选该新测试 CPP 加 04 两记录（各3文件）。T1 先冻结契约并实现审查，后续专项逐步交回运行；共享文件串行换手，不并行写同文件。每步唯一目标、资源清理及断言见验证记录。
- 用户待决定：自然混出后无活动索引、准确 ASC 归属证据不足时，选保留归属至 GAEnd，或保持原混出清空时机并新增准确 ASC 归属查询。统筹已提出具体场景问题，尚无答复；不先实施任一选择、不扩大共享接口。
- 已确定的候选边界：Guard Anim 配普通 native ASC 显式拒绝并取消，不回退播放；目标仍是项目 ASC。非 Guard 旧兼容 map 当前保留，不宣称整体删除；完全移除另步证明。原生 P1、RateLease、StartedPositive 原文保持，生产 Task 尚未迁移。

状态：仅两记录已同步第19次实际证据和只读候选，冻结交回并停止写入。T1–T5 与自然混出接口/行为均未开放。

## 04B4-StartedPositive：真实 Guarded Started 正向测试（2026-09-30，实施授权已结束、实际通过）

统筹第17次完整构建成功及常规 49/49 Success 后授权；原生 P1 独立复验仍为 1 Fail、16 errors、0 warnings，两个场景前置均通过。组长 `gpt-6.1-sol / xhigh` 直接实施，无代理。本块优先于下文历史范围。

- 唯一目标：新增普通自动化 `GGYGO.AbilitySystem.MontageGuard.StartedSuccessorPreservation`；两个独立场景通过 ASC 公开 typed 入口在真实 Started 内 End A → 激活/播放 B，验证 A Superseded/0、B Accepted/正返回及后继保持。
- 精确可写文件：`Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskTestTypes.h`、`Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskLifecycleTest.cpp`、本文件及 `AAADocs/Modules/CombatActions/Module_Repair_04_Validation.md`。其余文件只读。
- 基线 SHA256：测试 H `BEE7E1BB0BC57B4920C07AF5AC289B71896D0F3DABC380559F6E64E3CA37DC0D`；测试 CPP `E9928040626D331EAD174214E371922E0FCDC57B2ABB26A5EB695FA6BB437ABC`。原文本已在工具会话保存，保留所有既有未提交变更。
- 职责与冻结接口：Animation 唯一拥有 native 返回屏障/调用身份；ASC 唯一拥有完整 GAS scope/能力上下文；测试仅持栈上结果、真实 Started 计数/准确 ID 及只读快照。只读依赖为已冻结 A1/A2/A3/A4、ASC typed 入口和 UE 5.8 动画/GAS API，不新增生产接口或状态权威。
- 原子顺序：登记预检 → 头部新增空的具体 Guard 测试子类 → CPP 新用例复用独立真实夹具并仅在本场景替换瞬态 Mesh AnimClass → 静态审查、实际差异及 SHA256 → 两记录同步 → 四文件冻结交回。两场景按顺序分别建 World；共享生产契约不写入。
- 验收断言：真实 A/B Started 各一次，A 已建立活跃实例且结束后才激活 B；两调用均经过公开 `PlayMontageWithGuard`、空 AdditionalQuery；结果栈上，A/B identity 与真实准确实例 ID 一致且不同，generation 非零相等、CallId 非零递增，A 指向 B superseding call；A4 只作身份查询，另查准确 B 实例、活动资产 ID、IsPlaying 和 SuccessorStart/0.65；B 返回与 A 外栈返回间不推进动画，严格比较既有 28 个 Local/Rep/GA/实例字段，两场景都执行。
- 清理责任：观察者先解绑、未消费的激活 action 清空；只按原 Anim 的捕获 ID 清理本场景实例，准确 ASC 所有权吻合时通过 CurrentMontageStop 清理 GAS，否则仅停止原准确实例；结束两 GA 后由夹具/World RAII 释放。清理发生在结果观测之后。
- 非目标：原生 P1 的注册/flag/红断言/初始化、旧 RateLease 和 after-Super/manual-instance 夹具、ASC/Guard/Task/生产资产、完整重入/失效/网络矩阵、Obsidian/全局文件。禁止 UE、构建、Git、新线程或代理。
- 停止点：任何前置失败仍为真实 Fail，不 expected-error/skip；若需改生产接口立即停止。本步仅静态冻结，运行证据由统筹提供，不能宣称 B4 全部关闭。

状态：两测试源码完成静态审查后持续冻结。H 新增 8 行、CPP 新增 304 行，零删除/零改写，移除新增内容后逐字节恢复原基线；原生 P1/RateLease 全部内容保留。H SHA256 `BEC4C9B7F4C50BD4448011EAFAB79EB5E5335E57246064583E12E7216D2847A4`；CPP `39E71D2DEFF7B98197B88B30C36652A108976E31CCB0EAACC41B1502B5681567`。实施交回时未编译/运行是历史状态；第19次已完整构建并实际 Success、0 errors/warnings，两个有限 Started 场景通过。实际差异、清理路径、28字段及阶段边界见验证记录。本次只更新两记录，没有生产/测试/资产/全局/Obsidian写入或 UE/构建/Git/代理操作；Task 未迁移，B4 不宣称全部关闭。

## 04B4-ASC：受保护播放入口（2026-09-30，历史源码授权与冻结）

统筹第16次完整构建成功（6 actions、20.22 秒）及常规 48/48 Success 后开放。组长 `gpt-6.1-sol / high` 直接实施，无代理。当前授权优先于下文历史范围。

- 唯一目标：新增普通 `PlayMontage` override 与 C++ `PlayMontageWithGuard(..., OutResult, AdditionalQuery)`；所有登记 scope 的协调身份固定原 ASC，完整唯一 `Super::PlayMontage` 调用受同一 A1 scope 保护，结果仅复制到调用方输出，不增加最近结果、map 或第二激活代次。
- 唯一源码：`Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h`、`.cpp`。
- 唯一记录：本文件及 `AAADocs/Modules/CombatActions/Module_Repair_04_Validation.md`。
- 基线 SHA256：H `5C96A8DE131E35582F79FDE5F87757991A39B5C24E94CBA99FDB01FE3C9EF3C6`；CPP `3CA7B55AC368B332CC1645E375FBCF2E3A049818EC35265A15E7C7FF4EA092E5`。原始文本已在工具会话内保存用于实际差异复核，不创建工作区备份文件。
- 只读依赖：已冻结 A1/A2/A3/A4、UE 5.8 ActorInfo/Spec/能力原生 End/Cancel 委托、当前 Task/P1/输入仲裁。A1 SHA256 `ACAEA0FD27ED2F474C8BC107886860BD7DADE72F452902A748B7F8AFE4E3855A` 已复核；A4 公开只读查询已核对，不修改共享契约。
- 原子顺序：登记预检 → 头部接口冻结于本次实现 → CPP 栈上原激活结束/取消观测与原上下文查询 → 完整 Super scope 消费 → 实际差异、接口/委托清理核对 → 两记录同步 → 四文件冻结交回。
- 验收断言：有效 B 不要求已结束祖先 A 活跃；成功后继使 A 保持 Superseded，ASC 不覆盖 A1 裁决；失败子调用不建立成功接管；原 ASC/ActorInfo/Owner/Avatar/Mesh/Anim/Ability/Spec 均保持捕获身份，本次 End/Cancel 后不可因同实例重激活恢复有效；每次查询重查 Spec，不持裸 Spec/实例跨回调；查询不广播/日志/调用 ShouldBroadcast。
- 兼容策略：原 Anim 非 Guard 的普通入口仅唯一 Super，明确无 B4 保证；受保护入口非 Guard 明确 Unsupported/0，不执行 Super、不失败回退。不新增兼容开关。
- 非目标：Task/P1/所有测试、Base/Guard、ASC 输入/仲裁/绑定语义、生产资产/Obsidian/全局文件、UE/GAS 库；禁止构建、UE、Git、代理。生产 Task 保持原消费者，不能因当前步骤完成宣称 B4 已修复。
- 停止点：四文件静态审查冻结交回统筹；新增入口未实际编译/运行前不冒称通过。若需要修改冻结共享接口或生产父类，先停止交回。

状态：两个 ASC 源码完成静态审查后持续冻结。实际文本差异只有新增（H 16 行、CPP 144 行），原 ASC 行零删除/零改写；End/Cancel 句柄逐次移除、guard 先析构、观测随后释放，结果仅栈上副本。H SHA256 `E9AEB8AE04165D05DA8C6C18EB07B18F5C7DCB6D8A4AE0702B1D117845BC95E5`；CPP `4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF`。实施交回时尚未构建/运行，之后第17次已完整编译、第19次通过两个有限 Guarded Started 场景；Task 仍未消费 typed 输出，资产未迁移，B4 未全部关闭。详细接口与边界见验证记录。

## 04-P1：真实 Started 诊断红测试（2026-09-30 已运行、源码继续冻结）

统筹在 `ModuleRepairGate_20260930_13` 完整构建及 47/47 回归完成后授权。组长以 `gpt-6.1-sol / high` 直接实施，不启用代理；下列新租约优先于本文历史临时子任务说明。

- 唯一结果：真实 `OnMontageStarted` 内 End A → 激活并成功播放 B；以 B 返回时的只读快照为基准，严格断言 A 外栈返回后 Local/Rep/GA/Section/准确实例不被覆盖。保留原始代码上的预期失败，不反转断言、不用 `AddExpectedError` 把后继错误变成通过。
- 原实现唯一源码范围（已结束写入、继续冻结）：`Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskLifecycleTest.cpp`、`Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskTestTypes.h`。
- 本次结果登记仅可写记录：`AAADocs/Modules/CombatActions/Module_Repair_04_Subleases.md`、`AAADocs/Modules/CombatActions/Module_Repair_04_Validation.md`；完成后再冻结交回。
- 前置基线 SHA256 已复核相同：CPP `A10218B6AB1D4FB9F4D26EBF517A4DF9CC7E902314C947EDCA8910D97DC62D80`；H `B31DF5980E38F8DA3C21BA1AA5361B5B02D72BA29AADF2C3BAFF7487CD47EFF2`。
- 只读依赖：当前项目 ASC/Task/测试能力、UE 5.8 GAS 与 AnimInstance/Montage API、排程/台账。测试 ASC 只读复制 protected 记录，不提供 setter、播放覆写或快照恢复。
- 原子顺序：基线/租约复核 → 两测试文件增加独立诊断夹具及 complex 枚举 → 静态核对/局部记录 → 四文件冻结交回。保留原 RateLease 测试全部实现和断言。
- 隔离：注册 `ProjectDiagnostics.B4.MontageStartedReentry.LocalRepGaSectionInstance`；只有进程显式 `-GGYGOB4ReentryDiagnostic` 才枚举。无开关不产生测试用例或跳过成功；常规 `GGYGO` 名称筛选不选择本项。
- 验收：独立 Authority World/两 GA；不同资产、同资产不同 Section 两场景；真实 Started 已建立 A 实例，B 激活/播放/基准有效必须先通过；全字段比较汇总，场景不因第一条结果断言失败而停止。
- 非目标：任何生产 ASC/Task/BaseGA/Hero/Animation 接口或实现、UE/GAS 库、资产、Obsidian/全局文件、预测/双端网络完整矩阵。禁止构建、UE、Git 操作。
- 用户已批准 Animation 薄安全父类的有限候选：实例建立后的 Started 内立即接续，拒绝实例未建立时混出回调嵌套。此候选尚未实现，P1 也不证明其有效或关闭 B4。
- 停止点：实现及静态审查冻结后交回统筹显式运行；没有实际运行日志不能声称复现或红测成立。

状态：统筹 `ModuleRepairBuildGate_20260930_14.log` 完整构建 Succeeded（6 actions、14.31 秒）；`ModuleRepairGate_20260930_14/index.json` 常规 47/47、0 warning/error，未枚举 P1。`ModuleRepairB4Diagnostic_20260930_14/index.json` 显式诊断为 **1 Fail、16 errors、0 warnings**，无 Prerequisite 错误；不同资产 7 条、同资产不同 Section 9 条后继保持失败，真实 Started 各 1，A/B 实例不同，同资产准确 B 实例 0.65→0.20、SuccessorStart→OuterStart。**进程 exit0 不是诊断成功**。组长只读核对报告/日志后仅更新两记录，记录现已冻结交回；P1 真实复现目标完成，B4 产品缺口仍未修复。

复核确认源码仍为原冻结 SHA256：CPP `E9928040626D331EAD174214E371922E0FCDC57B2ABB26A5EB695FA6BB437ABC`；H `BEE7E1BB0BC57B4920C07AF5AC289B71896D0F3DABC380559F6E64E3CA37DC0D`。新增部分移除后两文件逐字节恢复原基线哈希，旧 RateLease 内容完整保留；详细错误字段与原始证据见验证记录。Animation 现独占 A1 共享声明三文件租约，04 不抢改接口/消费者。本次没有源码/测试/资产/Obsidian写入、构建、UE、Git或代理操作；两源码继续冻结，未拓宽租约。

组长：`01a0ebc0-8780-7f92-86d0-2f028f08f147`。统筹已授权 B1–B4/B8–B9；禁止 UE/MCP、构建、Git 提交、资产写入。所有既有未提交改动保留。以下路径相对 `F:/ue_project/GGYGO/`；子任务不得再委派。模型统一 `gpt-6-luna` / `max`。

排程更新：按 `Module_Repair_Parallel_Schedule.md`，第13与14a批可在互斥范围并行。本表文件子租约不变；第04批不写 HealthSet/Messages、Boss ActionSet/AIController/BT Task，全部源码工作线冻结后由统筹构建。

## 冻结的共享接口方案

- B1/B2：PlayerCombo 本地单调激活代次，所有同步外调返回点验证捕获代次；End 清理先于 Super，旧栈不得清新激活。
- B3：Montage Task 新增 `static bool ResolvePlayRate(const UAnimMontage*, float RequestedRate, float& OutTaskPlayRate, float& OutEffectivePlayRate)`；TaskPlayRate 只应用一次全局缩放，Effective 再乘 Montage RateScale。工厂保存计算结果；公开 `float GetEffectivePlayRate() const`，供 Combo watchdog 读取同一次播放快照。无效配置取消而非返回悬挂任务。
- B4：Task 保存原 Character/AnimInstance/ASC/播放实例；缩放以 token 取得/释放，替换接管继承原始基线，旧 token 不恢复。自然混出和一切释放路径统一清理；EndTask 即释放租约，即使 Montage 继续播放。原 Avatar 的清理不触碰新 Avatar。
- B9：ASC 新 RPC `ClientCorrectAbilityState(FGameplayAbilitySpecHandle AbilityHandle, FPredictionKey ActivationKey, const FGameplayAbilityTargetDataHandle& Correction)`；仅校验 Spec/活跃实例/预测键后调用基类 `virtual void ReceiveAbilityCorrection(const FGameplayAbilityTargetDataHandle& Correction)`（默认无操作）。Combo 自持类型化 `FGGYGOComboCorrectionData : FGameplayAbilityTargetData`，解释现有业务字段，校验结构类型/范围。使用 GAS 原有 TargetData 序列化，不增加事件总线。
- B8：复用原 ASC 组规则；SingleInstance 准入同时检查优先级和 CanBeCanceled，取消执行后复核；不得在 PreActivate 的 Spec ActiveCount 尚未递增时 End。基类进入业务/BP前终检不一致并退出；结束摘除不得移除回调中新激活的组登记。Camera代码原样保留。

## 子租约

### task_motion（`/root/task_motion`）— 已冻结交回，组长复核通过

目标 B3/B4。唯一可写文件：

- `Source/GGYGO/AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.h`
- `Source/GGYGO/AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.cpp`
- `Source/GGYGO/AbilitySystem/Tasks/GGYGORootMotionScaleLease.h`（如需轻量私有辅助）
- `Source/GGYGO/AbilitySystem/Tasks/GGYGORootMotionScaleLease.cpp`（如需）
- `Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskLifecycleTest.cpp`
- `Source/GGYGO/AbilitySystem/Tests/GGYGOMontageTaskTestTypes.h`（如需反射夹具）

只读依赖：Engine GAS/Animation、PlayerCombo、BossMelee、ASC、AGENTS/台账。验收：有效速率快照；原值恢复、同值不同owner、替换、Avatar变化、EndTask不停Montage；无当前ActorInfo反查误清；静态检查。不得写GA/ASC头文件。

交回：代理停止全部六文件写入，真实 Ready 播放/同步结束/嵌套后继、非 1 全局速率及精确实例单元测试已落盘，重复夹具与旧测试 hook 调用已删除。组长完成格式、实际 API 和静态核查；未编译/运行。临时子任务已结束，无可归档身份。

第三次统一自动化返修：测试在共享合成 Montage 夹具初始化阶段失败。代理确认 UE 5.8 构造器已有唯一 `DefaultSlot`，移除重复追加，复用默认轨并添加真实 `UAnimComposite` segment；保留真实 Mesh/AnimInstance/ASC/播放断言。仅测试 `.cpp` 变化，现已冻结，await rerun。

第四次统一自动化返修：产品 Task 断言未报告失败；剩余错误为 CVar 隐式恢复 Constructor 优先级、抽象 `UObject` ensure 和瞬态 Mesh 无 render data。代理改为显式保存/恢复值与原 SetBy、具体测试 UObject owner、只读引擎 SkeletalCube；仅两个测试文件变化，现已冻结，await rerun。

### combo_lifecycle（`/root/combo_lifecycle`）— 已冻结交回，组长复核通过

目标 B1/B2及消费B3/B9。唯一可写文件：

- `Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.h`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOPlayerComboAbility.cpp`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOComboCorrection.h`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOComboCorrection.cpp`
- `Source/GGYGO/AbilitySystem/Tests/GGYGOPlayerComboLifecycleTest.cpp`
- `Source/GGYGO/AbilitySystem/Tests/GGYGOPlayerComboLifecycleTestTypes.h`

只读依赖：Task新速率接口、ASC新RPC、基类新接收虚函数、已有窗口类型/测试。验收：Activate/Commit/Ready同步结束重激活旧栈退出，结束前清理；窗口与伤害业务不变；纠正载荷类型与边界、旧revision；静态检查。不修改共享GA/ASC/Task头。

交回：六文件实际实现和两项自动化源码已复核，静态检查通过，均未编译/运行。临时子任务已结束；无可归档会话身份，不声称已归档。真实 Ready 测试不覆盖任意 Montage/Section 的引擎内部重入写回或网络运行。

第三次统一自动化返修：两项测试共用的合成 Montage 夹具在产品逻辑前失败，根因同为重复追加构造器已有的 `DefaultSlot`。代理复用默认轨并加入真实 `UAnimComposite` segment，保留 Character、Mesh、AnimInstance、ASC、Trace 及后续生命周期断言；仅测试 `.cpp` 变化，现已冻结，await rerun。

第四次统一自动化返修：两项 Combo 测试功能均通过，但共报告 6 条瞬态 Mesh 无 render data warning。代理只读加载引擎 SkeletalCube 并使用其真实 render data/Skeleton，从 reference skeleton 取真实骨名供 Trace；不修改或保存引擎资产。两个测试文件已冻结，await rerun。

### asc_admission（`/root/asc_admission`）— 自动化返修已冻结交回，组长复核通过

目标 B8/B9共享接口。唯一可写文件：

- `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h`
- `Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp`
- `Source/GGYGO/AbilitySystem/Groups/GGYGOAbilityGroupTypes.h`
- `Source/GGYGO/AbilitySystem/Tests/GGYGOAbilityAdmissionTest.cpp`
- `Source/GGYGO/AbilitySystem/Tests/GGYGOAbilityAdmissionTestTypes.h`

只读依赖：引擎PreActivate/End时序、Combo现有协议及本共享接口。验收：不可取消单实例拒绝、可取消替换、取消重入、Queued/Coexist回归；通用纠正Spec/实例/key过滤；ASC不含PlayerCombo引用。不得修改Camera函数内容或Combo文件。

交回：runtime与两个测试已落盘，临时子任务确认停止写入；静态 diff/尾空白/API核对通过。新增 `Admission.GroupLifecycle`、`Admission.CorrectionRpc` 尚未编译或运行。组长可在本记录交回后修正这些文件；仍不得自行构建。临时子任务无独立可归档会话身份，不声称已归档。

统筹复核追加已完成：组长接管两个测试文件，补充 `Admission.InvalidPredictionKeyReentry` 的真实 PreActivate→Activate→End 重入场景，并按 UE 5.8 修正结束委托字段为 `AbilityThatEnded`；新增测试未编译/运行。运行时代码仍冻结，临时子代理未重启。

统一完整 C++ 构建通过后，`Admission.GroupLifecycle` 在同 Spec PerExecution 递归场景报告预期活动实例 1、实际 0。首次返修把组准入拆为 Notify 阶段登记预留和 ActiveCount 递增后的 `FinalizeAbilityGroupAdmission`，但第三次统一自动化仍得到相同最终失败。统筹再次授权原代理写 ASC/项目 GA 四个 runtime 文件及 Admission 测试；代理把准入身份改为 GA 实例内非零 attempt generation 栈，Finalize/Reject/Consume/Complete 均按捕获 generation 定位，并补充 B/C 实例与 ActiveCount 中间诊断。原最终断言未改；五文件已静态检查并再次冻结，await rerun。

第四次统一自动化证明 C 在嵌套 Try 返回前已 End，但日志没有 End 参数或裁决原因；可读源码与运行结果不一致。代理未猜测修改 runtime。组长接管后只在 Admission 测试派生类增加 Activate-Super 前后和 End 入口观测，记录实例、ActiveCount、IsActive、ReplicateEnd 与 bWasCancelled；原最终 1/1/1 断言保留。两测试文件冻结，await rerun。

第五次统一自动化 sample 确认 B/C 都以 ReplicateEnd=1、Cancelled=1 走项目 admission reject，形成双向淘汰。统筹重新授权后，代理把 attempt sequence 改为 ASC 跨实例统一分配，并在 Finalize 先按现有冲突谓词定向处理 pending：较新拒绝较旧，旧 resolver 恢复后先识别自身已拒绝退出；settled 能力仍走原取消/复核链。六个 Admission 文件静态冻结，原 1/1/1 断言与观测保留，await rerun。

## 组长保留唯一所有权

- 本子租约清单及 `AAADocs/Modules/CombatActions/Module_Repair_04_Validation.md`。
- `Source/GGYGO/AI/Boss/Abilities/GGYGOBossMeleeAbility.cpp`：仅共享速率消费。
- 获准的局部 AbilitySystem 文档、玩家普攻计划及相关Canvas，待源码接口冻结后更新。

最终状态：三个临时子任务均已结束并交回；组长已完成 MontageTask/Combo 夹具及 Admission 全局 sequence、定向 pending 裁决、权威组登记终检的静态门禁，源码冻结。最终完整 C++ 构建成功，`Admission.GroupLifecycle` 单项 1/1 及统一自动化 38/38 通过，0 warning、0 error；未执行 Git 提交。完整验收和已知引擎缺口见验证交接文档。
