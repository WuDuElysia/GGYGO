# Kevin DemonBattle：战斗源数据审计

> 当前为只读源审计及用途建议，尚未创建本轮Montage/伤害窗口。所有用途分类是设计建议，不是恢复出的原游戏技能配置。

## 可复现方式

运行 AAADocs/Scripts/audit_bh3_kevin_combat_source.py（普通Python3，无需UE）；只读扫描79配对JSON/FBX和anim_settings，输出 Saved/Codex/bh3_kevin_combat_source_evidence.json 与 AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Action_Manifest.json。脚本复用通用FBX解析器，不修改源文件。

## 关键结论

- 79份JSON与总索引递归扫描，没有events/notify/damage/collider/trigger/HitWindow/activation/visibility等事件或判定字段。它们提供Unity root motion与loop参数，不含控制器状态图、技能脚本、碰撞体尺寸、受害者配对或打击数。结论限于本次导出，不能推断原游戏没有这些数据。
- 79份FBX检查：动画属性只出现Lcl Translation、Lcl Rotation、Lcl Scaling；未见事件节点或相关自定义属性。75份含动画曲线，4份空片段仍无可恢复的HitBox/武器显隐信息。
- HitBox、CounterHitBox、Weapon、Weapon_Effect、LanceThrowAttach在全部79份FBX中都没有本地动画轨道。它们能继承父骨运动，但没有开闭判定信号。
- 模型Weapon网格唯一Skin Cluster连接Bip001 Prop1（UE命名Bip001-Prop1）；3064权重点。Prop1在64份FBX有轨道、60份有可测变化，是武器路径候选。Weapon是根下网格占位，不应作为相同起止Socket。
- BOSS_411顶层根在全部FBX无动画轨道；Bip001有74份轨道（67份变化），名为Root的兄弟辅助节点有71份轨道（47份变化）。直接开启UE Root Motion不能自动把Bip001位移变成胶囊位移。

## 首批近战候选与位移证据

下列均60fps。Z是源FBX Y-up坐标中的地面轴，不是UE竖直轴；数值为Bip001本地厘米坐标。T/R变化是运动证据，不是HitWindow。

| 动作 | FBX时长s | Bip001源Z首→末(cm) | Prop1证据与建议 |
| --- | ---: | --- | --- |
| Ice_Attack_01 | 2.016667 | 0→142.0486 | T/R轨道；优先预览并人工标定，尚无窗口 |
| Ice_Attack_02 | 1.850000 | 47.3050→176.0425 | T/R轨道，Prop1局部平移跨度较大；需确认刺击/离手语义 |
| Fire_Attack_01 | 2.850000 | 0→857.5513 | T/R轨道；长距离动作，先预览，不默认近战伤害 |
| Fire_Attack_02 | 4.216667 | 0→1869.8297 | T/R轨道；长距离动作，先预览，不默认近战伤害 |

源applyRootMotion=false并不意味着序列没有整体运动。四条都需Movement/Combat确定胶囊与网格的位移接缝；本轮不改源序列、不编写新移动框架。

## 分段、循环与窗口来源

- 源没有Montage Section、Main/AS/BS顺序或可组合技能定义。攻击族仅按名称提出候选分组；独立片段先独立准备，不自动拼接完整技能。
- Fire_Attack_03_Loop的loopTime=false；四条ThrowSkill_DragLoop均false。Fire_Attack_04_Down_Loop=true而Down_Loop_Spline=false。不能以Loop后缀决定无限循环。
- Fly_Loop、Air_Wait、Down_Loop等是1帧级姿势；ThrowFall_Y/ThrowBlowFall_Y的JSON和FBX键时间为0，仅表示保持姿势素材，不是完整坠落动作。
- StandBy等15条有效片段loopTime=true；另4条空片段也标true，但未生成序列。源loopBlend/keepOriginalPosition/RootT/RootQ等完整摘要保留在evidence。
- JSON有75份rootMotionCurves，4空片段为null。RootT保留Unity来源尺度，FBX位移已烘焙100倍，不能把两者相加或再次乘100。
- 准确伤害窗口来源当前缺失。后续只给目视验证的挥击添加manual_candidate窗口，明确人工帧区间与Socket证据；远程、召唤、投技保持disabled。
- 同族Bip001骨系末帧→首帧本地T/R/S误差已记录family_seam_rank_evidence；旋转只做欧拉分量环绕，属于连续性线索，不是已验证接段契约。

## 全部79索引用途建议（75有效+4空片段）

| 源片段 | 秒(JSON/FBX键) | FPS | 源loop | 建议用途 | 族 |
| --- | --- | ---: | --- | --- | --- |
| StandBy | 2.1667/2.1833 | 60 | true | sequence_state：用于待机/移动/眩晕持续状态；默认不建攻击Montage | StandBy |
| Force_Kill_ThrowSkill_AS | 3.5833/3.6000 | 60 | false | paired_montage：抓取/处决候选；需对齐受害者与取消策略 | Force_Kill_ThrowSkill |
| Force_Kill_ThrowSkill_BS | 4.1667/4.1833 | 60 | false | paired_montage：抓取/处决候选；需对齐受害者与取消策略 | Force_Kill_ThrowSkill |
| Be_Executed_AS | 3.5500/3.5667 | 60 | false | paired_montage：被处决配对表现；不能当Boss主动伤害动作 | Be_Executed |
| Be_Executed | 8.0000/8.0167 | 60 | false | paired_montage：被处决配对表现；不能当Boss主动伤害动作 | Be_Executed |
| Fly_Loop | 0.0167/0.0333 | 60 | true | sequence_state：用于待机/移动/眩晕持续状态；默认不建攻击Montage | Fly_Loop |
| Fire_Execute_Wing_Defence_BS | 0.5000/0.5167 | 60 | false | section_family：防御阶段候选，循环显式退出；无默认伤害 | Fire_Execute_Wing_Defence |
| Fire_Execute_Wing_Defence_Loop | 2.0000/2.0167 | 60 | true | section_family：防御阶段候选，循环显式退出；无默认伤害 | Fire_Execute_Wing_Defence |
| Fire_Execute_Wing_Defence_AS | 2.0000/2.0167 | 60 | false | section_family：防御阶段候选，循环显式退出；无默认伤害 | Fire_Execute_Wing_Defence |
| Counter | 1.1667/1.1833 | 60 | false | single_montage：反击候选；判定窗口待预览/人工标定 | Counter |
| Wing_Defence_Break(80-200) | 4.9167/4.9333 | 60 | false | single_montage：防御/破防表现候选；CounterHitBox运动不等于有效判定 | Wing_Defence |
| Move_L_BS | 0.5667/0.5833 | 60 | false | sequence_state：移动起止素材；BS/AS先后需预览确认 | Move_L |
| Move_L_Loop | 1.0667/1.0833 | 60 | true | sequence_state：用于待机/移动/眩晕持续状态；默认不建攻击Montage | Move_L |
| Move_L_AS | 0.6667/0.6833 | 60 | false | sequence_state：移动起止素材；BS/AS先后需预览确认 | Move_L |
| Move_R_BS | 0.5667/0.5833 | 60 | false | sequence_state：移动起止素材；BS/AS先后需预览确认 | Move_R |
| Move_R_Loop | 1.0667/1.0833 | 60 | true | sequence_state：用于待机/移动/眩晕持续状态；默认不建攻击Montage | Move_R |
| Move_R_AS | 0.6667/0.6833 | 60 | false | sequence_state：移动起止素材；BS/AS先后需预览确认 | Move_R |
| Fire_Attack_01 | 2.8333/2.8500 | 60 | false | single_montage：主动攻击候选；仅建立待标定窗口，不捏造源判定 | Fire_Attack_01 |
| Ice_Attack_02 | 1.8333/1.8500 | 60 | false | single_montage：主动攻击候选；仅建立待标定窗口，不捏造源判定 | Ice_Attack_02 |
| Fire_Attack_02 | 4.2000/4.2167 | 60 | false | single_montage：主动攻击候选；仅建立待标定窗口，不捏造源判定 | Fire_Attack_02 |
| Ice_Attack_01 | 2.0000/2.0167 | 60 | false | single_montage：主动攻击候选；仅建立待标定窗口，不捏造源判定 | Ice_Attack_01 |
| Wing_Defence_BS | 0.5000/0.5167 | 60 | false | section_family：防御/破防表现候选；CounterHitBox运动不等于有效判定 | Wing_Defence |
| Wing_Defence_Loop | 2.0000/2.0167 | 60 | true | section_family：防御/破防表现候选；CounterHitBox运动不等于有效判定 | Wing_Defence |
| Wing_Defence_ThrowSkill | 1.5500/1.5667 | 60 | false | paired_montage：抓取候选；动作与受害者配对未确认 | Wing_ThrowSkill |
| Wing_Defence_ThrowSkill_BS | 2.0000/2.0167 | 60 | false | paired_montage：抓取候选；动作与受害者配对未确认 | Wing_ThrowSkill |
| Wing_ThrowSkill_AS | 3.4500/3.4667 | 60 | false | paired_montage：抓取候选；动作与受害者配对未确认 | Wing_ThrowSkill |
| Dash_B | 1.2500/1.2667 | 60 | false | single_montage：无伤害通知；位移由玩法另定 | Dash_B |
| Dash_F | 1.0500/1.0667 | 60 | false | single_montage：无伤害通知；位移由玩法另定 | Dash_F |
| Fire_Attack_03_Loop | 1.1000/1.1167 | 60 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fire_Attack_03 |
| Fire_Attack_03 | 3.2167/3.2333 | 60 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fire_Attack_03 |
| Fire_Attack_04_BS | 1.6167/1.6333 | 60 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fire_Attack_04 |
| Fire_Attack_04_Air_Wait | 0.0167/0.0333 | 60 | true | section_family：空中/下落/蓄力保持阶段；不得默认全段伤害 | Fire_Attack_04 |
| Fire_Attack_04_Down_Loop | 0.0167/0.0333 | 60 | true | section_family：空中/下落/蓄力保持阶段；不得默认全段伤害 | Fire_Attack_04 |
| Fire_Attack_04_Down_AS | 2.4333/2.4500 | 60 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fire_Attack_04 |
| Fire_Attack_04_Down_Loop_Spline | 0.0167/0.0333 | 60 | false | section_family：空中/下落/蓄力保持阶段；不得默认全段伤害 | Fire_Attack_04 |
| ThrowUp_02_Y | 0.4333/0.4500 | 60 | false | sequence_state：受击/抛飞/倒地恢复，不作为攻击判定源 | ThrowUp_02_Y |
| ThrowFall_Y | 0.0000/0.0000 | 60 | true | sequence_state：受击/抛飞/倒地恢复，不作为攻击判定源 | ThrowFall_Y |
| StandUp | 2.6833/2.7000 | 60 | false | single_montage：受击/抛飞/倒地恢复，不作为攻击判定源 | StandUp |
| Fire_Attack_04 | 5.1667/5.1833 | 60 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fire_Attack_04 |
| Fire_Attack_03_Loop_End | 2.2667/2.2833 | 60 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fire_Attack_03 |
| Ice_Attack_03_BS | 0.9167/0.9333 | 60 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Ice_Attack_03 |
| Ice_Attack_03_Loop | 0.2500/0.2667 | 60 | true | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Ice_Attack_03 |
| Ice_Attack_03_AS | 0.8333/0.8500 | 60 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Ice_Attack_03 |
| Wing_Defence_Simple | 3.1667/3.1833 | 60 | false | single_montage：防御/破防表现候选；CounterHitBox运动不等于有效判定 | Wing_Defence |
| Ice_Attack_04 | 2.1667/2.1833 | 60 | false | single_montage：主动攻击候选；仅建立待标定窗口，不捏造源判定 | Ice_Attack_04 |
| Ice_Attack_05 | 2.0000/2.0167 | 60 | false | single_montage：主动攻击候选；仅建立待标定窗口，不捏造源判定 | Ice_Attack_05 |
| Fly_Attack_01 | 3.9167/3.9333 | 60 | false | single_montage：主动攻击候选；仅建立待标定窗口，不捏造源判定 | Fly_Attack_01 |
| Fly_Attack_02 | 3.4167/3.4333 | 60 | false | single_montage：主动攻击候选；仅建立待标定窗口，不捏造源判定 | Fly_Attack_02 |
| Fly_Attack_03_AS | 1.0000/1.0333 | 30 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fly_Attack_03 |
| Fly_Attack_03_Summon | 1.0000/1.0333 | 30 | true | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fly_Attack_03 |
| Fly_Attack_03_Between | 1.0833/1.1000 | 30 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fly_Attack_03 |
| Fly_Attack_03_Shoot | 1.0000/1.0333 | 30 | true | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fly_Attack_03 |
| Fly_Attack_03_BS | 0.7500/0.7667 | 30 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fly_Attack_03 |
| Fire_Attack_04_Charge | 0.3333/0.3500 | 60 | true | section_family：空中/下落/蓄力保持阶段；不得默认全段伤害 | Fire_Attack_04 |
| Fire_Attack_04_ChargeEnd | 2.4667/2.4833 | 60 | false | section_family：攻击族分段候选；次序/伤害类型需预览确认 | Fire_Attack_04 |
| Fly_Evade | 1.2500/1.2667 | 60 | false | single_montage：无伤害通知；位移由玩法另定 | Fly_Evade |
| Stun | 2.0000/2.0167 | 60 | true | sequence_state：用于待机/移动/眩晕持续状态；默认不建攻击Montage | Stun |
| Hit_L | 1.2833/1.3000 | 60 | false | single_montage：受击/抛飞/倒地恢复，不作为攻击判定源 | Hit_L |
| Hit_H_F | 1.4167/1.4333 | 60 | false | single_montage：受击/抛飞/倒地恢复，不作为攻击判定源 | Hit_H_F |
| Hit_H_B | 1.4167/1.4333 | 60 | false | single_montage：受击/抛飞/倒地恢复，不作为攻击判定源 | Hit_H_B |
| Hit_Throw | 0.4167/0.4333 | 60 | false | single_montage：受击/抛飞/倒地恢复，不作为攻击判定源 | Hit_Throw |
| ThrowBlowFall_Y | 0.0000/0.0000 | 60 | true | sequence_state：受击/抛飞/倒地恢复，不作为攻击判定源 | ThrowBlowFall_Y |
| ThrowDown | 0.1333/0.1500 | 60 | false | single_montage：受击/抛飞/倒地恢复，不作为攻击判定源 | ThrowDown |
| ThrowUp_01_Y | 0.4333/0.4500 | 60 | false | sequence_state：受击/抛飞/倒地恢复，不作为攻击判定源 | ThrowUp_01_Y |
| ThrowBlow_Y | 0.6000/0.6167 | 60 | false | sequence_state：受击/抛飞/倒地恢复，不作为攻击判定源 | ThrowBlow_Y |
| KnockDown | 0.1333/0.1500 | 60 | false | single_montage：受击/抛飞/倒地恢复，不作为攻击判定源 | KnockDown |
| ThrowBlowEnd_Y | 0.0167/0.0333 | 60 | false | sequence_state：受击/抛飞/倒地恢复，不作为攻击判定源 | ThrowBlowEnd_Y |
| ThrowSkill_DragLoop_Idle | 0.0333/0.0500 | 60 | false | sequence_pose：极短拖拽方向姿势素材；名称Loop不等于源loopTime | ThrowSkill_DragLoop |
| ThrowSkill_DragLoop_Down | 0.0167/0.0333 | 60 | false | sequence_pose：极短拖拽方向姿势素材；名称Loop不等于源loopTime | ThrowSkill_DragLoop |
| ThrowSkill_DragLoop_Mid | 0.0667/0.0833 | 60 | false | sequence_pose：极短拖拽方向姿势素材；名称Loop不等于源loopTime | ThrowSkill_DragLoop |
| ThrowSkill_DragLoop_Up | 0.1000/0.1167 | 60 | false | sequence_pose：极短拖拽方向姿势素材；名称Loop不等于源loopTime | ThrowSkill_DragLoop |
| Die | 1.3333/1.3500 | 60 | false | single_montage：单次死亡表现；末姿保持由玩法控制 | Die |
| Fire_Execute_Defence_01 | 0.5500/0.5667 | 60 | false | single_montage：防御/处决反应候选；无源伤害时间 | Fire_Execute_Defence |
| Fire_Execute_Defence_02 | 0.5500/0.5667 | 60 | false | single_montage：防御/处决反应候选；无源伤害时间 | Fire_Execute_Defence |
| Fire_Execute_BS_Test | 0.6500/0.6667 | 60 | false | defer：源名含Test，先隔离，不默认接战斗 | Fire_Execute_BS_Test |
| Add_HitBox | 0.0167/空 | 60 | true | skip：源FBX无曲线；不能恢复HitBox开关或武器显隐语义 | Add_HitBox |
| Normal_HitBox | 0.0167/空 | 60 | true | skip：源FBX无曲线；不能恢复HitBox开关或武器显隐语义 | Normal_HitBox |
| No_Weapon | 0.0167/空 | 60 | true | skip：源FBX无曲线；不能恢复HitBox开关或武器显隐语义 | No_Weapon |
| Have_Weapon | 0.0167/空 | 60 | true | skip：源FBX无曲线；不能恢复HitBox开关或武器显隐语义 | Have_Weapon |

用途计数：24 single_montage、24 section_family（先独立片段，不拼接）、7 paired_montage（只准备，配对玩法未实现）、15 sequence_state、4 sequence_pose、1 defer、4 skip。55条可准备独立Montage，20条有效片段保留状态/姿势/测试用途。

## 当前边界

DefaultSlot、现有GameplayEventWindow HitWindowBegin/End；伤害窗口顺序且不重叠。源证据清单仍保持空窗口；人工配置独立保存在 `BH3_Kevin_Combat_Montage_Config.json`，审计脚本不会覆盖它。

编辑器生成器 `Source/GGYGOEditor/Private/KevinCombatAssetBuilder.cpp` 已编码、待统一编译执行：55独立Montage、武器section刚性权重/PCA端点与StandBy→DefaultSlot→OutputPose的独立ABP。未修改原序列、玩家资产或主关卡，未运行UE游戏关卡。

### 人工预览证据（不是源游戏窗口）

- Ice01查看20/30/45/48/51/55/65/80帧，48帧横出、51–55转入收势；manual_candidate=45–55帧（0.75–0.916667秒）。
- Ice02查看0/8/15/21/30/45帧，Prop1驱动剑离手扫出再收回；manual_candidate=8–24帧（0.133333–0.4秒），24帧边界是21与30帧观察间的人工估计。骨骼动画离手运动不等于实现独立弹体生命周期、追踪或碰撞。
- Fire01查看80帧姿态；Fire01/02的大幅位移结论依据FBX审计，继续无伤害窗口。
- 两条Ice将引用Movement的Derived原地序列；原动画预览不能代替派生动画、胶囊运动与命中判定的联合验收。
