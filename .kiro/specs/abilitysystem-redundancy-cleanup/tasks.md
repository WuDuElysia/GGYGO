# Implementation Plan: abilitysystem-redundancy-cleanup

## Overview

整改第 1 步，共 7 步，按 [活动记录](../../../AAADocs/需求文档/refactor_and_squad_switch.md) 的顺序执行。

执行规则（后续各步沿用）：
- 由 Kiro 在既有会话内顺序执行，不启用子代理。
- 写集、保护输入和窗口以统筹授权为准；源码／文档窗内不启动 UE、不构建、不跑测试、不做 Git。
- 实现前把写集文件的预像与身份存到 `Saved/Kiro/<spec>/Before/` 和 `before_manifest.tsv`，交回时附 unified diff（`Patches/`）与当前身份（`after_summary.tsv`）。
- 编译与测试只在统筹设定的验证窗口执行：编译前在聊天告知，检查内存、磁盘与既有新增额度。UE 只启动和正常退出 Kiro 自己的实例，日志与输出写到 `Saved/Kiro/<spec>/`。
- 不降低断言，不排除失败场景，失败日志保留。

编译命令：
`F:\UE_5.8\Engine\Build\BatchFiles\Build.bat GGYGOEditor Win64 Development -Project="F:\ue_project\GGYGO\GGYGO.uproject" -WaitMutex -NoHotReload`

测试命令：
`F:\UE_5.8\Engine\Binaries\Win64\UnrealEditor-Cmd.exe F:\ue_project\GGYGO\GGYGO.uproject -ExecCmds="Automation RunTests <过滤器>; Quit" -unattended -nullrhi -nosplash -log=<输出路径>`

证据目录：`Saved/Kiro/abilitysystem-redundancy-cleanup/`（Before/、before_manifest.tsv、Patches/、after_summary.tsv、make_patches.py）。

## Tasks

- [x] 0. 开工重核
  - 核对调用链、外调结论与测试契约，修订写回 requirements.md／design.md
  - 统筹给定基线身份，CodeConventions 原位修改；ASC.cpp 受保护不改
  - _Requirements: 1.8, 4.4_

- [x] 1. 代码规范澄清
  - 原位改写 CodeConventions 对应条款，新增"应主动退役的模式"
  - _Requirements: 1.1-1.7_

- [x] 2. PlayerCombo 预备配置（批次 1 改回原计划）
  - [x] 2.1 私有 FPreparedComboStep／FPreparedComboConfiguration；纯解析 PrepareComboSteps，ValidateComboConfiguration 只调它，错误文字不变
    - _Requirements: 2.3_
  - [x] 2.2 FindOrPrepareConfiguration：授予实例缓存成功结果、CDO 不缓存、GE 弱引用失效判定；InvalidatePreparedConfiguration 供改配置方调用
    - _Requirements: 2.1, 2.2_
  - [x] 2.3 CanActivate、失败日志、Body 共用缓存；Body 存激活快照，不在 BP 回调后复验；终止清理释放，Initialize 纳入未归还检查
    - _Requirements: 2.2, 2.4, 2.7_
  - [x] 2.4 HandleMeleeHit 改用快照的 GE 与模式，只核 Def 与伤害键冲突；删除 ValidateGGYGOComboStepDamage
    - _Requirements: 2.6_

- [x] 3. StartStep 三步化与重验删除
  - [x] 3.1 拆出 ReadStepStartInputs、ReleaseCurrentStep、BeginStep；BeginStep 读预备段数据
    - _Requirements: 2.4, 5.1, 5.2_
  - [x] 3.2 删除提前 ClearWatchdog、ReleaseTraceWindow 后、两次 NextSection 后的重验与 uint64 耗尽判断
    - _Requirements: 4.2, 5.3_
  - [x] 3.3 HandleMeleeHit 重核：已只在真实外调后重验，不改
    - _Requirements: 4.3_
  - [x] 3.4 BuildHitEffectPayload 删除两处 HasOriginalObjects 重验
    - _Requirements: 4.4, 4.5_

- [x] 4. Boss 招式与选招
  - [x] 4.1 BossMelee Commit 前一次解析配置，Commit 后只复核运行接收者
    - _Requirements: 3.1_
  - [x] 4.2 ActionSet 全表校验移到 BossState 采纳期（全部阶段）；SelectAction、Store、Consume 与两个 BT Task 不再校验（批次 1）
    - _Requirements: 3.2, 3.3_
  - [x] 4.3 Selection 坏表用例改为 ActionSetValidatedOnAdoption（批次 1）
    - _Requirements: 3.4_

- [x] 5. 过期注释
  - MontageGuardAnimInstance.h 文件头与类注释改为当前契约
  - _Requirements: 7.1, 7.3_

- [x] 6. MeleeTrace Legacy 消费者核查（需验证窗口的 Editor）
  - 在 Kiro 自己的 Editor 实例中查找 Legacy BeginTraceWindow／EndTraceWindow 的蓝图与 AnimNotify 消费者；无消费者则删除，有消费者则写明并保留
  - Editor 核查：`GGYGO.Combat.MeleeTrace.LegacyConsumerAudit`（Test_R16a，NullRHI）加载 /Game 下全部 42 个蓝图（含 AnimBP、AnimNotify、Widget），92 张图 680 个节点，按函数／委托引用与属性名核对，0 个消费者；C++ 只有安全测试使用
  - 已删除 `BeginTraceWindow`／`EndTraceWindow`、Legacy 窗口来源，以及只由 Legacy 窗口广播的 `OnMeleeHit` 与反射接收器 `GGYGOMeleeTraceTestReceiver.h`；`SafetyAndCoverage` 改用 Owned 窗口，原断言保留，Test_R16a 通过
  - 仓内另一作者的 Editor 观察脚本 `AAADocs/Scripts/observe_bh3_kevin_combat.py` 用 `get_editor_property('OnMeleeHit')` 绑定该事件（脚本自注只是 Legacy 观察，Kevin 走 Owned 窗口后本就收不到）；删除后该脚本绑定时会抛错，需原作者移除这一项
  - _Requirements: 8.2_

- [x] 7. 测试适配（批次 1）
  - 夹具改配置先失效缓存；删除激活中途改作者配置的注入；InvalidRequiredGE 改为准入期用例；生产 Error 声明为恰好一次；HitSemantics 距离专项带 GameInstance
  - PlayerCombo 夹具改走真实输入在第 2 步
  - _Requirements: 9.1-9.3, 10.4, 11.1-11.5_

- [x] 8. 检查点：编译、测试（NullRHI 部分完成）
  - 与第 2 步合批：`Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/`，Build～Build_R4 成功；Test_R1（59 例）后修复重跑至 Test_R5
  - 本步用例（PlayerCombo、HitSemantics、BossAI）除 `ActivationCommitAndEndReentry` 外全部通过；该例的裸重激活与 10-25 输入来源规则冲突，归第 4 步
  - 未验：PlayerCombo 生产冒烟 7 例与 Kevin 冒烟（真实 RHI，需另批额度）、人工 GUI、FX 联机（任务 6 已在收尾完成）
  - _Requirements: 10.1-10.4_

- [x] 9. 更新活动记录
  - 已写入现状、验证结果、未验证项与额度
  - _Requirements: 10.5_
