# Kevin DemonBattle 运行验证

当前需求与未完成项以 [Kevin Boss 完整组装](../../../需求文档/kevin_boss_assembly.md) 为准。本文记录实际验证入口和证据边界，替代早期仅 Ice01／Ice02 直接请求 GA 的隔离方案。

## 正式入口

- 地图：`/Game/Map/BH3/L_KevinBoss_P3`，D3D12、单玩家 PIE。
- Encounter 使用正式 Definition、State、Controller、PawnData、AbilitySet 和两阶段行为树；Boss 由 BT 选招，经 GAS、Montage 作者窗、CMC 和 Combat 执行。
- 玩家通过原 LocalPlayer／Controller／Pawn 输入装配提交 W／S／D／LeftMouseButton。观察脚本不直接激活 Boss，不写生命，不开 GodMode，不移动或强制落地 Boss。
- 脚本：本机 `Saved/Codex/KevinBossAssembly_20261111/battle_host.py`。输出为同目录各次运行的 `editor.log`、实际 game viewport PNG 和 Master WAV。日志中的活动特效／声音实例只证明运行事实，画面和听感分别核验。

## 已取得证据

以下路径均相对 `Saved/Codex/KevinBossAssembly_20261111/`。

| 范围 | 结果与证据 |
| --- | --- |
| BossAI／Combat／CMC | `Battle_R1/editor.log` 的 15 项 BossAI 自动化通过；`Battle_R2/editor.log` 的范围／弹体命中查询和 ActionMotion TimingAndOwnership 通过。 |
| 动画与作者图 | `Animation_Read/editor.log` 的原生轨迹、姿态、Montage 窗口及声音引用读回通过，KevinMotionOutputGuard／KevinPreserveAuthoredGraph 两项通过。 |
| Focus 与转向 | Controller 恢复原生 AAIController Tick，使用 BT Focus→ControlRotation→CMC 原生转向。`Build_FocusStandalone/build.log` 编译通过；`Focus_Standalone/editor.log` 跨引擎帧两次换向的 NativeFocusRotation 回归通过。 |
| P3 场景 | `Scene_Read/editor.log` 独立读回通过；实际导航投影、双方完整路径和 9 个空中净空采样通过，初始双方间距 18 m。 |
| 完整交战 | `Battle_R6/editor.log` 覆盖 Counter、Ice01～05、Fire01～03、AirChain01／02 共 11 个选招入口。Boss 从 1200 HP 经 50% 阶段切换至死亡；玩家以真实普攻完成战斗，结束剩余 2 HP。 |
| 空中收尾 | 两条 AirChain 均完成 Flying 释放、CMC 原生重力、真实 Landed 及 LandingRecovery 后返回地面选招。`Battle_R5/081_falling_hold.png`、`107_falling_hold.png` 可见 Fly_Loop 末帧全身等待姿态；没有补写 Z 或合成下降。 |
| 死亡清理 | R6 DeathFinished 后 Avatar 销毁，再观察 5 秒，Boss 弹体、持续声音及活动 Kevin Niagara 均无残留。 |
| 声音与画面采集 | R6 录得 15 种实际播放的 Kevin SoundCue 实例、237 秒 Master WAV，以及 145 张完整 viewport 读回；部分主要特效受玩家特效及运动模糊遮挡，不能据实例计数判定全部可见。 |

## 受影响复验

- **Dash_F 追击已通过**：R6 发现原 MoveTo 因缺少普通移动曲线执行请求被 CMC 拒绝，用户选择完整 Dash_F 分段接近。无伤害 GA、冷却 GE、两阶段动作池及不含 MoveTo 的 BT 已制作，`Build_DashF/build.log` 编译、`DashF_Create/editor.log` 保存、`DashF_Read/editor.log` 独立读回 47 包通过。`Battle_R7_DashF/editor.log` 前两段对静止玩家各水平移动约 711.145 cm，与原片段 711.144 cm 对应，距离 18 m→10.89 m→3.78 m，双方生命不变；随后正常攻击，共记录 11 次 Dash_F，无旧 CMC 拒绝。玩家约 65 秒阵亡，Boss 走真实目标死亡取消，未签本轮胜利。
- **地面旋转修复**：R8 实图复现 IceWarning 竖起。UE Python 原生构造读回证明位置参数顺序造成 Pitch／Yaw 错位，改具名 `pitch/yaw/roll`；保存 9 个子蓝图，`Rotation_Read/editor.log` 独立验证 37 包。R9 的 `027_NS_Kevin_IceWarning_14030df00bfc_030.png` 和 `030_NS_Kevin_IceGroundBreak_c6025809cf08.png` 已确认水平预警圆和破环。R9 玩家阵亡，未签完整胜利。
- **火系与空中复拍**：`Visual_Fire_Air/editor.log` 在同一正式场景暂停 BT，通过已有 GAS 授予依次请求 Fire01～03、AirChain01／02；五项均完成且等到真实落地，52 张 PNG 读回、13 种实际 SoundCue、63.637 秒 Master WAV。已核对 `019_NS_Kevin_FireGroundBreak_697aabbd5128_030.png` 的水平火环、`005_NS_Kevin_FireWeaponTrail_8504586aacf1.png` 的刀光、`004_NS_Kevin_FireCharge_cd10c72ba158_030.png` 的蓄力、`036_NS_Kevin_AerialGather_8eb7275a5a2e_030.png` 的聚集碎片、`038_NS_Kevin_IceStrike_23f0e5ab6080.png`／`042_NS_Kevin_FireStrike_d5999ef92921.png` 的冰火爆发及 `039_NS_Kevin_IceProjectile_e1d0bb948cd1_030.png` 的弹体尾迹。
- 专项取景使用临时诊断 CameraActor 并关闭运动模糊，不保存生产相机／渲染配置，不写生命、不开 GodMode、不移动角色或强制落地。专项 GAS 请求只证明相应执行和表现，不作为自动选招或完整战斗证据。

## 未覆盖边界

- 本文证据不覆盖 Kevin 独立进程联机、Dedicated Server、Cook、性能验收或真实音频设备试听。
- 旧隔离方案里的逐动作窗口外零伤害、逐时点中断及不可见服务端骨骼更新矩阵，没有因完整战斗通过而自动获得覆盖。
- 声音配置中的同 Boss 动作候选仍是项目映射；原版事件归属与时点未知的项保留原标签。

## 核心评审后的定向验证

`Build_ReviewFix/build.log` 增量编译成功；`Review_Query/editor.log` 的 AreaAndProjectile 与 TouchThenBlock 两项通过，后者经生产弹体入口验证同段／跨段同 Actor 先 Touch 后 Block：仅一次命中，阻挡仍销毁弹体。物理阻挡独立输出，伤害去重不变。

本批 GE 制作／验证库及材质实例资源读回库连同结果结构迁入 GGYGOEditor。`Review_Editor_Read/editor.log` 验证四个 Editor 反射类型、GA／AI 47 包与 FX 43 包独立只读回，未保存资产。原 Content 包未检出旧类型序列化引用，未新增运行时兼容。没有重复跑未受影响的全战斗。

构建／运行针对当前完整工作树，包含其它工作线未提交改动；不代表选择性提交后的干净 HEAD 已单独构建。Editor 启动原有 `LogAutomationTest: Condition failed` 诊断仍在完整日志中，不冒称全日志零错误；上述专项各有独立成功结论。
