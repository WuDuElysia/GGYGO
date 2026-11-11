# Implementation Plan: abilitysystem-healthset-repnotify

## Overview

整改第 7 步，先验证后决定。执行规则与命令同第 1 步，输出目录为 `Saved/Kiro/abilitysystem-healthset-repnotify/`。按顺序在第 6 步验收后执行（两步都会改 ASC 文件，同一文件只有一个写入者）。

状态（2026-11-03 收尾）：复现完成，走 Requirement 2.2（保留分类帧），这是技术决定、不再交用户；反算已迁出 ASC；NullRHI 测试通过；监听服务器＋1 客户端 PIE 中受击扣血、MaxHealth 持续下调、破韧的服务器与客户端数值及广播一致（Test_R19）。死亡未在联机中验证。

## Tasks

- [x] 0. 开工重核
  - Health_Consumers：HealthComponent 订阅 HealthSet 的 Health／MaxHealth／Poise 变化、OutOfHealth（服务器上要求 Spec，发 Event.Death）、PoiseBroken，再经自身动态委托给 UI／蓝图；Messages 的 Message.Damage 与 Message.PoiseBreak；死亡投影经 HealthComponent。蓝图／UI 资产上的具体绑定未在 Editor 中逐一核对。
  - HealthMessage 夹具已有客户端接收路径（SetTestNetRole、Begin／EndTestNetReceive、SimulateReplicated*）。
  - 没有客户端预测伤害：PlayerCombo 只在权威端开命中窗（GGYGOPlayerComboAbility.cpp 的 HitWindow 分支要求 HasAuthority），BossMelee 激活要求 HasAuthority。
  - _Requirements: 1.1_

- [x] 1. 最小复现
  - [x] 1.1 新增 HealthRepro 测试，记录现行实现在 6 个场景下的 Observable_Results
    - _Requirements: 1.1_
  - [x] 1.2 在测试模块内用 HealthSet 子类实现 Lyra_Approach，记录同场景结果
    - _Requirements: 1.2_
  - [x] 1.3 自动化复现已编译运行（Test_R14）；真实复制路径在监听服务器 PIE 中核对了现行实现：`GGYGO.Teams.SquadSwitch.ListenServerClientRequest` 的生命阶段（Test_R19）
    - _Requirements: 1.1, 1.3_
  - [x] 1.4 把差异写入活动记录
    - _Requirements: 1.3_

- [x] 2. 按结果执行
  - 2.1 不执行。简化后的回卷、重入和客户端上限投影缺等价证明，采用下方 2.2 保留分类帧。
    - _Requirements: 2.1_
  - [x] 2.2 不等价时：保留分类帧，补写头文件说明
    - 收尾定案（技术决定）：保留分类帧，不做"服务器 PostAttributeChange 广播、客户端只在 OnRep 广播并删去 RepNotifyFrame／NetReceiveFrame"的简化。该简化没有回卷、重入和客户端上限投影的等价证明（HealthMessage 的 RepNotify*、ClientMaxNetReceive 正是覆盖这些情形），现行实现在复现与联机中都给出正确结果，没有失效依据驱动改动
    - _Requirements: 2.2, 2.3_

- [x] 3. 迁出属性反算
  - 新建 `AbilitySystem/Attributes/GGYGOAttributeBaseCalculation.{h,cpp}`（`GGYGOAttributeBase::CalculateBaseForCurrent`），HealthSet 改用；ASC 删除原函数。CombatSet 没有反算消费方，未改。
  - _Requirements: 3.1-3.3_

- [~] 4. 检查点：编译、测试、PIE、联机
  - Build_R14、Build_R15 通过；Test_R14（21 例）、Test_R15（HealthRepro 回归断言）全部通过
  - 联机（Test_R19，NullRHI 同进程监听服务器＋1 客户端）：服务器对客户端出战队员施加即时伤害 10、持续 GE 下调 MaxHealth 20、削韧至 0；Health 不超过新上限；客户端 ASC 属性与 HealthComponent 数值等于服务器，两端 HealthChanged／MaxHealthChanged 都广播（持续 GE 下调上限时服务器也广播，即复现中 Lyra 写法缺失的那一项），服务器 PoiseBroken 广播、客户端 PoiseChanged 广播
  - 未验：死亡的联机表现；单机 PIE 的受击画面
  - _Requirements: 4.1-4.4, 5.1-5.3_

- [x] 5. 更新活动记录
  - _Requirements: 5.4_
