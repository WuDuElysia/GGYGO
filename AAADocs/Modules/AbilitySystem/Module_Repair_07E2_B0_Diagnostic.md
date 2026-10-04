# 07E2-B0-D：同 Spec 嵌套 raw 激活来源严格诊断

更新：2026-10-01。唯一写入者为 AbilitySystem 长期组长；本次独占三文件由统筹在第33统一窗口完成并退出 UE 后授权。预检先于源码创建登记；新诊断实现及静态审查完成，三文件冻结交回，未构建或运行。

## 原子预检与租约

| 项目 | 本步骤契约 |
| --- | --- |
| 唯一目标 | 真实输入 retry 的外层 CheckCost 内嵌套同 Spec raw TryActivateAbility；证明内层 Queued 失败不得借用外层输入来源 |
| 精确三文件 | `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGOInputActivationOriginTestTypes.h`；`F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGOInputActivationOriginDiagnostic.cpp`；本记录 `F:/ue_project/GGYGO/AAADocs/Modules/AbilitySystem/Module_Repair_07E2_B0_Diagnostic.md` |
| 写入前存在性 | 已实际 Test-Path：上述三文件均不存在；不存在同名产物覆盖 |
| 模块与职责 | AbilitySystem 诊断观察原生 GAS 失败与输入 retry 关联；CheckCost 仅测试派生扩展，生产能力检查/组仲裁/帧调度不改变 |
| 已冻结接口 | 当前 ASC Tag/截止双参数委托及 Queue 行为只读；07E2-V 值类型、Hero、GA、原诊断和 Fixture 均不接入或迁移 |
| 只读依赖 | GGYGOInputTestTypes.h/.cpp 的真实 Fixture；GGYGOAbilityAdmissionTestTypes.h 与 GGYGOAbilityAdmissionTest.cpp 的 Queued 探针/组配置；ASC、GA、Hero、PawnExtension、InputComponent、PC；本机 UE 原生 CanActivate/Notify 调用顺序 |
| 非目标 | 不修生产来源；不设 CanActivate final；不改 Engine/GAS 库、API、V header、原诊断、Fixture、07两记录、Montage、资产或 Obsidian；不扩设备/BeginPlay/网络/多来源矩阵 |
| 依赖顺序 | 本记录预检与基线 → 新 TestTypes 声明 → 新 cpp 探针及严格单项 → 静态全文/基线核对 → 三文件冻结交回 → 统筹另编号构建/诊断 |
| 启动隔离 | 基础名 ProjectDiagnostics.Input.ActivationOrigin，单子项 NestedSameSpecRawTry；仅 -GGYGOInputActivationOriginDiagnostic 枚举，RunTest 复核开关和案例，不返回跳过成功 |
| 停止点 | 真实输入/Queued/retry/CheckCost/同 Spec 实例/原窗口任一前置不能成立；需要额外文件、API或模拟替代；发现保护文件变化或租约冲突；均停止交回，不扩大范围 |
| 执行门禁 | 不派代理、不启动会话，不执行 UE/构建/Git；构建及红测统筹另行安排 |

## 真实时序与验收断言

1. 复用真实 LocalPlayer/Hero/Input 绑定及 PC PostProcessInput，先正向激活控制 Spec；Completed、结束并移除控制。
2. 给自有 ASC 显式 SingleInstanceQueued 配置，激活无输入 Tag 的占位 Spec；真实 Triggered → Hero → PC 使原请求真实 Queued，Hero 记录原缓冲。
3. 占位真实结束触发 GroupFreed，Hero 通过已有入口移交 retry；占位随后重新激活。先做一次不武装的真实 retry，公开通知给出原有限 deadline；这作为后续严格相等校验的独立基线，不读取 Hero 窗口/缓冲。再真实结束占位触发第二次 GroupFreed 并重新占位，仅到此处武装新探针；期间不新按下、不 Tick、不续期。
4. 外层 CheckCost 先解除武装，再对 ActorInfo 原 ASC 调用同 Handle 的 raw TryActivateAbility。局部 RAII 标记仅划分测试观察，内层不再重入；内外继续真实父类检查，失败标签仅由现有组仲裁产生。
5. 断言 raw 调用完成且返回 false、内外 CheckCost 同 Handle/同 ASC/同 PrimaryInstance、原生 Queued 失败各1、GA 原生失败反馈各1、业务激活0。
6. 严格要求内层输入 retry 通知0，外层合法 retry 通知1且原有限截止保持；不得将拒绝全部通知作为成功。只从公开通知及本测试局部观察取证，不读写生产私有缓冲。
7. 所有提前退出均由 RAII 摘除测试委托、解除探针武装、ReleasePlayerInput、结束/移除自有 Spec、清自有组配置并 Shutdown 自有 Fixture。
8. 不手工写 FailureTag、不直接 Queue、不 Tick、不使用 ExpectedError，不把诊断预期失败写成动态已复现。

## 只读保护基线

- 写入前已实际计算：Source/GGYGO 现有全部 222 文件及冻结07两记录，共 224 文件。
- 排序清单摘要：`A264825E2B66CABE52F8C90B2AFA8802BFD21902A550FB1E546DEE3DD8434135`。
- 摘要格式：rg --files Source/GGYGO 排序后追加07两记录，路径分隔符规范化为 /；每行相对路径 + TAB + SHA256，以 LF 连接且无末尾 LF，UTF-8 SHA256。新建两测试源码不纳入旧文件保护清单。
- 下表保存20个直接依赖的独立 SHA256；冻结前须逐一核对旧清单全部224项，而非仅比较总数。资产/Obsidian 未授权写入，本步骤不声称对其全库 hash 验证。

| 保护文件（根 F:/ue_project/GGYGO） | SHA256 |
| --- | --- |
| `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h` | `E9AEB8AE04165D05DA8C6C18EB07B18F5C7DCB6D8A4AE0702B1D117845BC95E5` |
| `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.cpp` | `4025C7E6A3D36C988B49E7B8271F90940CF13E5A7948BA36B614ECFEAE2CAAAF` |
| `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h` | `BEE74DC34ED2C8636192894E964FB73779C17A50E43F4B810B21911CDF58DF51` |
| `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp` | `5BA07252DE4112F44ADCD142EE43F5E8470662A3AC2AC1A28C2E187C31BD117D` |
| `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/GGYGOAbilityInputRequestTypes.h` | `8E795C5A85A546A8D489DE66D7F0B5A3C89B0A31F479ED286DE3F611D4134DAE` |
| `F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.h` | `AF921B89AA8F665D6F8EF9ED2AF9A5D576AE8252AEC650D072DEEB4D24F5CC91` |
| `F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp` | `FEC79B605C4B58A9EEABAC595A4CE53FFC4BC01D55A143535516D2B5B1EACD81` |
| `F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.h` | `6190EB9134ECDE4735FC67C0CD564D87C3EEDAE9BC477E16ACA296368F7C96FD` |
| `F:/ue_project/GGYGO/Source/GGYGO/Character/Components/GGYGOPawnExtensionComponent.cpp` | `E76FC4182469B76C30BB0FAE980B5DB2A6D4BD7676BA30C7741F6D24B8BC4E10` |
| `F:/ue_project/GGYGO/Source/GGYGO/Player/GGYGOPlayerController.h` | `B6C08F16C45E03DB5306EF4AEE462AA0BBA92731CF3107FB6E6F1A8BA3FE185D` |
| `F:/ue_project/GGYGO/Source/GGYGO/Player/GGYGOPlayerController.cpp` | `DD9BD38A3E626AAC27BD992630C6F626241F2A772543D0084F61F47B7C0037EA` |
| `F:/ue_project/GGYGO/Source/GGYGO/Input/GGYGOInputComponent.h` | `63A9A27A96F882B014D6A9C0EE03B9E572703143DE237A74C46DB27E328A1CC2` |
| `F:/ue_project/GGYGO/Source/GGYGO/Input/GGYGOInputComponent.cpp` | `FFA2B7F2EB1F9955EF6AF151EE7BAC08FA75FEFB2E048484837BA80FD04C76CA` |
| `F:/ue_project/GGYGO/Source/GGYGO/Input/Tests/GGYGOInputTestTypes.h` | `8576301BDDABF505D5DECAA6E15EBE8717DCB4F031E6C4B82889DA8E28FF6454` |
| `F:/ue_project/GGYGO/Source/GGYGO/Input/Tests/GGYGOInputTestTypes.cpp` | `CF89CE4DD8E970DB255899E6750BD161DD3D3EAA5FFCBDFA0A1E11C83FA04878` |
| `F:/ue_project/GGYGO/Source/GGYGO/Input/Tests/GGYGOInputRetryIdentityDiagnostic.cpp` | `C7D77AD2EB2B4B1C361D682AC4A391CF1747ED71E34A286D734B158EC0DD500D` |
| `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGOAbilityAdmissionTestTypes.h` | `A5E16C95B563E44EFDFA3733AFBBCFC19D4DD3BA66AC6DEF7499C1434E54D8AF` |
| `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGOAbilityAdmissionTest.cpp` | `CFEA5CEF5558EF5C8BC61378C883DEFE7A57207ED9DD6D649DF9289303CC73E6` |
| `F:/ue_project/GGYGO/AAADocs/Modules/Input/Module_Repair_07_Subleases.md` | `6CA6CD2C9FB0BA987BFDD5ED524766400EAAC50A5DD5689D5BB20305D06D2A10` |
| `F:/ue_project/GGYGO/AAADocs/Modules/Input/Module_Repair_07_Validation.md` | `BC082C81C1AB4BC724D2E05C3CD8668A49E5AA7E09935E5D5EB3F63F8EC123DF` |

## 状态与未完成项

- 预检已先登记；两测试源码实现完成，只有一个显式开关隔离的 complex 单项。测试探针继承既有 Queued 能力；只在武装 CheckCost 调用一次原 ASC 的 raw Try，局部 RAII 标记分类原生通知、输入通知和 GA 反馈。
- 本步骤只新增测试和本记录，不改变生产模块职责、接口或实施状态。架构计划/Canvas 保持冻结，不把未运行诊断写成修复已实现。
- 静态预期：现 Scope/Handle 会被内层 raw 失败借用；尚无编译或动态证据。
- 更完整的 CanActivate 覆写边界、来源修复、多 Tag 与阻断、设备/BeginPlay/网络均不由本诊断关闭。

## 静态冻结交回

- 新 TestTypes 共49行，新 cpp 共370行；仅一个 complex 注册及一个子项，无开关时不枚举，RunTest 复核开关/参数。
- 已实际读取新三文件全文并复核：同 Handle/原 ASC/同 PrimaryInstance、原生内外 Queued 各1、原生 GA 反馈各1、业务激活0、内层 retry 严格0、外层合法1/原截止严格相等。结果均为代码中的断言，尚非运行结果。
- 为独立取得原截止，正式武装前增加一次未武装真实 retry 正向前置；不新增物理按下，未直接 Queue、Tick、读写 Hero 私有窗口或缓冲。
- 核对本机 UE：ShouldIgnoreCosts、GetInstancingPolicy、CheckCost、失败反馈与 Automation 参数签名存在；TGuardValue 正确定义于 Templates/UnrealTemplate.h，已使用该原生头。未使用 Engine 改动或 CanActivate final。
- 三文件逐行扫描：trailing whitespace 0、冲突标记0。两源码搜索 ExpectedError、直接 Queue、Tick、手工 FailureTag Add/Append、私有 buffer/physical deadline、V header 引入均0。
- 旧保护清单逐项复算224项：变动0、遗漏0、额外旧文件0，清单摘要仍为 `A264825E2B66CABE52F8C90B2AFA8802BFD21902A550FB1E546DEE3DD8434135`。只新增租约内两源码及本记录。
- 清理核对：场景 RAII 首先解除武装并摘测试三委托；随后 ReleasePlayerInput、结束/移除自有 Spec、清自有组配置、归还强引用与 Fixture。观察存储早于场景构造，晚于场景析构；raw 标记由 TGuardValue 恢复。
- 架构核对：没有新增生产状态、执行器、帧调度、循环依赖或跨模块内部读写。测试观察仅属于自有实例。已只读核对计划蓝图及 Input/AbilitySystem 结构、计划_实施状态；生产流程未变，无 Canvas 内容变化。全局计划_实施状态第24段“B0诊断尚未实现”须由统筹改为“诊断实现/静态冻结、尚未编译运行”；本步骤无 Obsidian 写入权限。
- 本组长停止写入三文件。不执行 UE、构建、Git、代理；编译/UHT与独立红测由统筹另编号，预期失败不能提前记为已动态复现。

| 冻结源码 | SHA256 |
| --- | --- |
| `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGOInputActivationOriginTestTypes.h` | `1BC9B5CFF1EE396649D062EA1945FE453E84DDA50B60D9D3BE5A1E4D328B9A4B` |
| `F:/ue_project/GGYGO/Source/GGYGO/AbilitySystem/Tests/GGYGOInputActivationOriginDiagnostic.cpp` | `69016178DE25929D03947667BCCBF639B871B93406F008B6608825628A99D7CD` |

本记录最终 SHA256 随三文件交回；不在自身正文嵌入自引用 hash。

## 统筹独立诊断命令（未执行）

```powershell
& 'F:\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe' 'F:\ue_project\GGYGO\GGYGO.uproject' -Unattended -NoSplash -NoSound -NullRHI -NoP4 -NoTurnkey -GGYGOInputActivationOriginDiagnostic '-ExecCmds=Automation RunTests ^ProjectDiagnostics.Input.ActivationOrigin.NestedSameSpecRawTry$' '-TestExit=Automation Test Queue Empty' '-ReportExportPath=F:/ue_project/GGYGO/Saved/AutomationReports/ModuleRepair07E2_B0_Origin' -log=GGYGO_ModuleRepair07E2_B0_Origin.log
```

前置失败仅表示诊断未成立；严格结果真实 Fail 如实保留，不以 UE exit0、ExpectedError 或跳过成功掩盖。没有开关时仅普通回归，不能称此单项已验证。
