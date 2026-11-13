# Implementation Plan: abilitysystem-healthset-repnotify

## Overview

整改第 7 步，先验证后决定。执行规则与命令同第 1 步，输出目录为 `Saved/Kiro/abilitysystem-healthset-repnotify/`。按顺序在第 6 步验收后执行（两步都会改 ASC 文件，同一文件只有一个写入者）。

状态（2026-11-13）：复现定案为 Requirement 2.2（保留分类帧），属性反算已迁出 ASC；相关自动化通过。真实 RHI 最小联机已检查扣血、MaxHealth 持续下调及破韧的两端数值／广播；原死者的 Health／DeathState／死亡广播配对与死亡前后段实拍已补齐。单机生产 GE 的扣血／破韧数值和广播通过，采样帧仍为站立，不能由此签受击／破韧动作和命中 FX；Requirement 5.3 的这些表现边界保持未验。

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
  - [x] 真实 RHI 的扣血／上限／破韧复制：`Saved/Codex/CharacterDeathPolicy_20261111/rhi2.log` 的 `ListenServerClientRequest` 为 Success，明确记录两端 ASC／HealthComponent 数值与广播一致，覆盖同一生命阶段；不再仅限 Test_R19 的 NullRHI 结果。
  - [x] 原死者死亡两端配对：`GGYGO.AbilitySystem.HealthAcceptance.ListenServer` 通过。原 Pawn 按 NetGUID 与 PlayerId 配对，Health 100→90→0、Poise 100→0；两端 HealthChanged 两次，PoiseChanged、PoiseBroken、OutOfHealth、DeathStarted、DeathFinished 各一次。DeathState 按 NotDead→DeathStarted→DeathFinished 推进，完成广播时原 HealthComponent／持久 ASC 均为零，观察者不改绑替补。
  - [x] 单机死亡与双端死亡可见：`HealthAcceptance.Standalone` 与上述联机项在 D3D12 自然 Draw 采样，已逐图查看。落地后的原角色无遮挡，死亡 Montage 前段及 75% 以后跪伏姿态可见；两端实际 ViewTarget 和视口机位均核对。只用临时诊断相机和测试玩家位置，不改生产镜头／角色资产。
  - [~] 单机受击／破韧表现：经共享 `GE_Damage_SetByCaller → DamageExecution → HealthSet → HealthComponent` 的数值和广播已核，扣血／破韧采样帧仍站立、无活动 Montage。本测试没有 Combat 命中／Cue 入口，不能据此验收独立受击／破韧动作、命中 FX 或音效；这些表现保持未验。
  - 实际复制顺序：客户端先收到 DeathStarted，此回调的 Health／ASC 仍为 90；同帧随后收到 Health=0 与 OutOfHealth，之后两端以零血完成死亡。DeathState 与 ASC 属性来自不同复制对象，本结果证明阶段及最终值收敛，不声明跨对象回调同序或同步到达。
  - 验证证据：2026-11-13 [小增量构建](../../../Saved/Codex/HealthAcceptance_20261113/capture_build.log)通过；[原生报告](../../../Saved/Codex/HealthAcceptance_20261113/Run_2/Report/index.json)两项 Success、零测试错误，[运行日志](../../../Saved/Codex/HealthAcceptance_20261113/Run_2/editor.log)及 [PNG](../../../Saved/Codex/HealthAcceptance_20261113/Run_2/Captures/)保留，自有 Editor 退出码 0。联机四条／单机两条警告（渲染 CVar、远端 Camera cache 写入拒绝、原 Pawn 输入路由退役）与启动前 13 条 Condition failed 未屏蔽。`Run_1` 的数值结果保留，初始落地、遮挡与过早采样的画面不作视觉通过依据。独立进程、网络扰动、Cook／性能／物理设备未验。
  - _Requirements: 4.1-4.4, 5.1-5.3_

- [x] 5. 更新活动记录
  - _Requirements: 5.4_
