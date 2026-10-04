# UE 启动 Smoke 诊断：与项目回归分开

更新：2026-09-30。统筹只读核对；不修改 UE/GAS 库、日志级别默认值或项目配置，不把未知错误当作预期自测。

## 实际现象

- Gate26 `Saved/Logs/GGYGO_ModuleRepairGate_20260930_26.log`：11:41:25.243–244 UTC，EngineInit 前 13 条 `LogAutomationTest: Error: Condition failed`。
- Gate27 同名 `_27.log`：12:38:46.741 UTC，同样 13 条；EngineInit 在12:38:46.748 UTC开始。
- 项目 Gate27 报告实际60/60 Success、全部叶 errors/warnings=0。该报告没有启动 Smoke 的结果，不能推导全日志无错误。DDC写路径和PythonGroupRule重名警告另记。

## 已核对的原生执行链

本机UE5.8源码提供以下直接证据：

1. `Runtime/Launch/Private/LaunchEngineLoop.cpp:4376`在启动期调用`FAutomationTestFramework::RunSmokeTests()`，该处不消费返回值，引擎继续初始化不表示Smoke通过。
2. `Runtime/Core/Private/Misc/AutomationTest.cpp:531`枚举SmokeFilter并执行、取StopTest结果、汇总是否全部成功；执行时暂时关闭栈采集，最后Dump全部执行信息。
3. `Runtime/Core/Public/Misc/LowLevelTestAdapter.h:130`的`CHECK`失败调用当前测试`AddError("Condition failed")`。未被预期消息匹配的Error进入结果并导致失败；不是只用于显示的故意错误。
4. `AutomationTest.cpp:1243`的Dump按测试输出结果名，再输出各事件；结果名是Log级别，而同文件默认`LogAutomationTest`为Warning，所以原日志保留Error却没有对应测试名。现有日志不能逐条确定断言归属。

## 原因候选与未闭合边界

`Runtime/Core/Tests/Experimental/UnifiedError/UnifiedErrorTests.cpp`的`CreateErrorMessage`与`CreateErrorMessageWithContext`两组Smoke有7+4个硬编码英文字符串比较；消息经本地化生成。Gate27中文启动日志实际打印“空错误”“整数-7出错”，与英文比较不一致。这是11个断言的强候选原因，不是全部13条的已验证归属；其余2条也尚未归属。

下一次统筹独占UE窗口可仅提高`LogAutomationTest`输出详细度以保留启动测试名，必要时另作英语文化独立对照；不屏蔽错误、修改原断言、改引擎或持久项目语言配置。没有实际运行前，不将候选写为根因闭合。

## 与专项预期拒绝区分

Gate27 `RootMotionBake`两条`curve changed after apply; revert refused`发生在专项内。`Source/GGYGOEditor/Private/Tests/RootMotionBakeSafetyTests.cpp:51`明确声明Exact、次数2的预期错误，报告该叶Success；不是启动13条的来源。

Camera44条拒绝由专项各自Plain/Error/Exact/1匹配，完整保留实际拒绝证据。这些有限预期不授权忽略其它错误。

上述为Gate26/27时的调查边界；当时未启动新的诊断过程，不宣称引擎Smoke已修复。

## Gate29：实际确定三个失败测试的归属

统筹在新DLL完整项目回归中，仅给本次隐藏UE进程传入 `-LogCmds="LogAutomationTest Log"`，未更改持久配置或原生断言。实际13:54:11.826–827 UTC启动日志保存以下测试名与其随后错误计数：

| 原生Smoke测试 | 实际Condition failed |
| --- | ---: |
| FUnifiedErrorTest_CreateErrorMessage | 7 |
| FUnifiedErrorTest_CreateErrorMessageWithContext | 4 |
| FStructuredLogFormatTest | 2 |

这闭合13条错误的测试级归属，不等于逐个CHECK已经映射或根因已经修复。前两组的中文本地化与英文常量比较仍是强候选；StructuredLogFormatTest包含多处格式化与本地化比较，默认消息只写Condition failed，当前未定位其中两个具体断言。System仅继续只读分析及提出独立文化对照方案；不修改Engine/GAS库、屏蔽错误或自行持久切换用户语言。

同次项目报告63/63 Success，三新增叶entries为空、全部叶errors/warnings0，报告hash `F28F002FC5710F64621ED4919EE20E06BCC8DA35C40DA83A6A20F3F004077FA7`。全日志实际21条Error中，13条属于上述真实启动失败；另8条是新Damage输入专项的6次完整预期拒绝和RootMotionBake的2次预期拒绝。44次Camera拒绝另有精确匹配。3条Warning分别为DDC写路径、PythonGroupRule重名和本次HTTP连通性请求超时，不能由项目报告0警告推导这些日志不存在。UE PID26112已exit0退出；退出码和项目报告仍不代表启动Smoke通过。

## StructuredLogFormat 本地化资源只读调查

System交回对本机 `en/Engine.locres` 与 `zh-Hans/Engine.locres` 的只读解析：该测试46个相关键中只有两项译文不同。`EmitterSubheaderText`（源码276行）英文期望 `Found 63 errors!`，中文资源格式产生 `已找到63项错误！`；`ObjectX`（318行）英文期望 `{1, 2, 3}`，中文资源格式产生 `{1,2,3}`。对应中英文资源的源字符串哈希一致，分别为 `8F417E72` 与 `83A2958E`；其余44键一致，先前TextFormat候选没有译文差异支持。

这是有实际资源支持的强候选推断，不是运行时逐断言映射。两个调用都经TestLoc在266行比较，Gate29只记录Condition failed，未保存具体比较参数。统筹可在冻结DLL和独占UE窗口以独立日志/报告运行 `-culture=en` 对照，保持本次LogAutomationTest详细级别并核对命令行language/locale；即使英文通过，也不称中文测试已经修复，不持久修改项目或引擎语言配置。

## 第30次冻结DLL的实际英文culture对照

第30次正常语言进程仍有13条启动Condition failed，项目63叶全部Success。之后独立UE进程48880仅增加 `-culture=en`，日志实际记录command-line language/locale均为en；16:53:02 UTC上述三个原生Smoke测试全部打印Success，Condition failed为0。独立项目报告 `Saved/AutomationReports/ModuleRepairSmokeCulture_20261001_30_en/index.json` 于16:53:11 UTC为63 Success，其它计数0、全部叶errors/warnings0、0.6486395597457886秒，SHA256 `E7DB3D5202AEB1F22B08F0BE596BEB39FDC746D172FD26503F72EE4F76C28F3D`；UE exit0且已退出。

全日志仍有24条Error（Damage专项22与RootMotionBake专项2）及DDC/Python重名两条Warning，不称全日志无诊断。这实证支持13条启动失败与本地化文化相关，结合中文资源与英文硬编码比较可定位原因类别；未逐CHECK采集实际参数，也没有修复中文测试或改用户语言设置，更没有修改引擎/GAS库或屏蔽原断言。
