# Pyrios 动作资源分类

> 路径: `Content/Characters/Player/Pyrios/`  
> 总计: **101** 个动作文件

---

## 一、移动动作 (Locomotion) — 12 个

| 动作名称 | 说明 |
|---------|------|
| `Idle_Loop` | 待机循环 |
| `Idle_AFK` | 久置待机触发 |
| `Idle_AFK_Loop` | 久置待机循环 |
| `Walk_Start` | 走路开始 |
| `Walk_Loop` | 走路循环 |
| `Walk_End` | 走路结束 |
| `Walk_Start_End` | 走路启动→停止（短程） |
| `Run_Loop` | 跑步循环 |
| `Run_End` | 跑步结束 |
| `TurnBack` | 转身 |
| `Evade_Front_01` | 前闪避 |
| `Evade_Back_01` | 后闪避 |

---

## 二、战斗动作 (Combat) — 52 个

### 2.1 普攻 (Normal Attack)

| 动作名称 | 说明 |
|---------|------|
| `Attack_Normal_01` / `_End` | 普攻第1段 |
| `Attack_Normal_02` / `_End` | 普攻第2段 |
| `Attack_Normal_03` / `_End` | 普攻第3段 |
| `Attack_Normal_Enhance_01` / `_End` | 强化普攻第1段 |
| `Attack_Normal_Enhance_02` / `_End` | 强化普攻第2段 |
| `Attack_Normal_Enhance_03` / `_End` | 强化普攻第3段 |
| `Attack_Normal_Enhance_04` / `_End` | 强化普攻第4段 |

### 2.2 特殊攻击 (Special Attack)

| 动作名称 | 说明 |
|---------|------|
| `Attack_Special_01` / `_End` | 特殊攻击 |
| `Attack_ExSpecial_01` / `_End` | 强化特殊攻击 |
| `Attack_Rush_01` / `_End` | 突进攻击 |
| `Attack_Counter_01` / `_End` | 反击 |

### 2.3 招架 / 援护 (Parry & Aid)

| 动作名称 | 说明 |
|---------|------|
| `Attack_ParryAid_Start` | 招架援护开始 |
| `Attack_ParryAid_L` / `_End` | 轻招架援护 |
| `Attack_ParryAid_H` / `_End` | 重招架援护 |
| `Attack_AssaultAid` / `_End` | 突击援护 |

### 2.4 切人攻击 (SwitchIn Attack)

| 动作名称 | 说明 |
|---------|------|
| `SwitchIn_Attack` / `_End` | 切人攻击 |
| `SwitchIn_Attack_01` / `_End` | 切人攻击01 |
| `SwitchIn_Attack_Ex_01` | 切人攻击强化01 |
| `SwitchIn_Attack_Ex_02` / `_End` | 切人攻击强化02 |
| `SwitchIn_Attack_Ex_03` / `_End` | 切人攻击强化03 |
| `SwitchIn_Attack_Ex_04` / `_End` | 切人攻击强化04 |
| `SwitchIn_Attack_Ex_Start` | 切人攻击强化开始 |

### 2.5 终结技 (QTE)

| 动作名称 | 说明 |
|---------|------|
| `ExQTE_Start_01` / `_Start` | 终结技1 |
| `ExQTE_Start_02` | 终结技2 |
| `ExQTE_Start_03` | 终结技3 |
| `ExQTE_Start_04` | 终结技4 |

### 2.6 受击 (Hit Reaction)

| 动作名称 | 说明 |
|---------|------|
| `Hit_H_Front` | 重受击（前） |
| `Hit_H_Back` | 重受击（后） |
| `Hit_L_Front` | 轻受击（前） |
| `Hit_L_Back` | 轻受击（后） |
| `HitFly_Front` | 击飞（前） |
| `HitFly_Back` | 击飞（后） |
| `Hit_Shake` | 受击抖动 |
| `ReflectBullet_Loop` | 弹反循环 |

---

## 三、特殊情况 (Special) — 37 个

### 3.1 换人（非攻击）

| 动作名称 | 说明 |
|---------|------|
| `SwitchIn_Normal` | 普通入场 |
| `SwitchOut_Normal` | 普通离场 |

### 3.2 滑索 (ZipLine)

| 动作名称 | 说明 |
|---------|------|
| `ZipLine_Enter_Start` | 滑索进入开始 |
| `ZipLine_Enter_Loop` | 滑索进入循环 |
| `ZipLine_Enter_End` | 滑索进入结束 |
| `ZipLine_Middle_Loop` | 滑索中段循环 |
| `ZipLine_Change` | 滑索转向 |
| `ZipLine_Back` | 滑索后退 |
| `ZipLine_Exit` | 滑索退出 |
| `ZipLine_Fall` | 滑索坠落 |
| `ZipLine_HitFly` | 滑索被击飞 |

### 3.3 生死 / 复活

| 动作名称 | 说明 |
|---------|------|
| `Death` | 死亡 |
| `Revive_01` | 复活阶段1 |
| `Revive_02` | 复活阶段2 |
| `Revive_03` | 复活阶段3 |
| `Revive_04` | 复活阶段4 |

### 3.4 UI 界面展示

| 动作名称 | 说明 |
|---------|------|
| `UI_CharSel_Start` | 角色选择-入场 |
| `UI_CharSel_Loop` | 角色选择-循环 |
| `UI_Equipment` | 装备界面 |
| `UI_Detail` | 详情界面 |
| `UI_Skill` | 技能界面 |
| `UI_EtoD` / `UI_DtoE` | 界面切换过渡 |
| `UI_StoD` / `UI_DtoS` | 界面切换过渡 |
| `UI_EtoS` / `UI_StoE` | 界面切换过渡 |

### 3.5 画廊 / 好感度表情 (Gallery)

| 动作名称 | 说明 |
|---------|------|
| `Gal_Idle` | 画廊待机 |
| `Gal_Think_Start` / `_Loop` / `_End` | 思考 |
| `Gal_Angry_Start` / `_Loop` / `_End` | 生气 |
| `Gal_Sad_Start` / `_Loop` / `_End` | 悲伤 |
| `Gal_Surprise_Start` / `_Loop` / `_End` | 惊讶 |

### 3.6 主城待机 (Main City)

| 动作名称 | 说明 |
|---------|------|
| `MC_Stand_Idle01_Loop` | 主城站立待机 |
| `MC_Stand_Think_Loop` | 主城思考待机 |

### 3.7 其他

| 动作名称 | 说明 |
|---------|------|
| `QuestStart` | 任务开始 |

---

## 四、总结

| 分类 | 数量 |
|------|------|
| 移动动作 | 12 |
| 战斗动作 | 52 |
| 特殊情况 | 37 |
| **合计** | **101** |
