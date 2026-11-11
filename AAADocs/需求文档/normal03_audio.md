# 普攻第三段音效：技能声与命中声

状态：自动化取证已通过；听感等用户试听。

## 目标

- 普攻第三段的技能声（攻击主体开始时播放）和命中声（只在真实打中时播放）分别取得证据：开始／停止事件、录音包络有信号、总输出没被静音；空挥时没有命中声。
- 好不好听、时点对不对、要不要换候选样本，由用户试听决定。

## 方案要点

- 技能声 `SW_Pyrios_Skill_Attack_Normal_03_1` 由 `AM_Pyrios_Attack_Normal_03` 主体开始处的 PlaySound 播放。
- 命中声 `SW_Pyrios_Impact_Attack_Normal_03_1` 由命中 Cue `/Game/GameplayCues/GCN_Pyrios_Hit_Normal03` 的 `DefaultEffect.ImpactSound` 播放，只在真实命中时触发。
- Normal02、Normal03、Special、ExSpecial 每类暂用第 1 份候选样本，其余候选保留可切换。
- 自动化运行不带 `-NoSound`，并设 `au.DisableAppVolume 1`、`bThrottleCPUWhenNotForeground=False`，避免窗口不在前台时声音被静音。
- 测试地图用 `L_Movement_Test`。`L_KevinBoss_P1` 没有 `Tag=GGYGO.KeyLight` 的主灯，Normal03 的场景材质特效会按约定拒绝，第三段打不出来。

## 当前状态

证据：`.agents/tasks/requirements-closeout/evidence/I06.md`，运行目录 `Saved/Kiro/requirements-closeout/I06/Run_R3`、`Run_R4`（两次结果一致）。本项没有改源码或资产。

- 打中：技能声在第三段主体开始后约 28～32 ms 开始，播放约 1.2 s；命中声在真实命中后约 16～21 ms 开始，播放约 1.1 s。两路播放 ID 不同，包络全为正，总输出非静音。
- 空挥：技能声照常；没有任何命中声。
- 画面：能看到的特效都属于技能路，即角色身上 Normal03 的七个 Niagara 单元（前方三个蓝色残影、烟雾竖条、地面碎片）。命中 Cue 只配了声音，粒子项为空，命中时不生成任何特效。诊断目标在生产镜头下被角色挡住。
- 验证级别：已编译（无源码改动）、已测试（打中 13 项、空挥 9 项判定全过）、已在 UE 里运行；不涉及联机。真实声卡是否出声、人耳听感没有被自动化验证。

## 未完成项

1. **需用户试听**：在 `L_Movement_Test` 的 PIE 里连按三次左键打出第三段，空挥一次、打到目标一次，然后选：
   - A：两种声音都可以；
   - B：技能声要换（当前用第 1 份候选）；
   - C：命中声要换；
   - D：时点不对（说明早了还是晚了）。
2. 按反馈在 Montage 或 Cue 里换样本，换后请用户复听。
3. 第三段打中时要不要有只在命中时出现的特效，归[特效与音效接线](fx_audio_wiring.md)，由用户决定：A 保持现状；B 给命中 Cue 配粒子（可试 `NS_Eff_Pyrois_Attack_Normal_03_02_Hit_Ghost`，原版是否这样用未知，只能算替代配置）。

## 验收标准

- 同一个第三段内，技能声在主体开始附近、命中声在真实命中附近开始；两路包络有信号，总输出非静音；空挥没有命中声。（已满足）
- 写明真实声卡和听感没有被自动化验证。（已写明）
- 用户给出试听结论；换了样本的话，用户复听确认。
