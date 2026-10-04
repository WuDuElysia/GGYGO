# Pyrios FBX 动画解读

> 数据源：`F:\AnimeStudio\Exports\Animator\Avatar_Male_Size03_Pyrois_Model\Avatar_Male_Size03_Pyrois_Model.fbx`
> 解析工具：`AAADocs/Scripts/fbx_bin_reader.py`（自研纯 Python 二进制 FBX 解析器）+ `fbx_anim_extract.py`（按 take 抽取骨骼轨道）
> 本文档为逆向资产的动画结构解读，不修改任何资产。

---

## 0. 结论速览（TurnBack 相关）

- TurnBack 的源文件里确实有一条 `Root.Lcl Rotation Y: 0° → -180°`，但 `Root` 是与 `Bone_Root` 同级的外部 Null，不是角色骨架的父节点；直接控制它不会直接旋转 UE 里的角色骨架。
- 真正的骨架链是 `Bone_Root → Bip001 → Bip001 Pelvis`。`Bone_Root` 自身恒定为 0，但 `Bip001` 同时带有 TurnBack 的根级位移和约 180° 的相对旋转，所以视觉转身实际落在骨架根级姿势上。
- 全 182 个动画里，`Root` 外部参考轨道只有 3 个 take 带整体 yaw：`TurnBack (-180°)`、`HitFly_Back (+180°)`、`ZipLine_Back (-180°)`；它们可作为原始 root-motion 时序参考，不能直接当作 UE 骨架 Transform 的控制目标。
- 之前运行时日志查 `Bone_Root` 恒为 0 并不能说明动画没有转身；它只说明 UE 骨架根节点没有直接旋转，实际旋转在 `Bip001` 的根级动画姿势中。
- 当前管线的正确拆分是：`RM_Yaw`（可选）只提供原始转身的时间权重；代码根据最终输入方向计算 Actor 的真实目标 yaw；AnimBP 或 In-Place 测试副本负责消除 `Bip001` 已烤入的固定转身姿势。

---

## 1. 文件与骨架概况

| 项目 | 值 |
|---|---|
| FBX 版本 | 7400（二进制，Kaydara） |
| 导出器 | FBX SDK 2020.3.7 |
| 文件大小 | ~333 MB（单文件含全部动画） |
| 动画 take 数 | **182** |
| Model 节点 | 177（5 Null + 163 LimbNode + 9 Mesh） |
| AnimationCurve | 162,894 |

### 关键节点语义（重要）

| 节点 | 类型 | 作用 |
|---|---|---|
| `Root` | Null | **外部 root-motion 参考节点**：位移（`Lcl Translation Z` = 前进轴）+ 源转身时序（`Lcl Rotation Y` = yaw）；与骨架 `Bone_Root` 同级，不直接控制角色骨架 |
| `Bone_Root` | Null | **真正的 UE 骨架根节点**，本身基本恒 0 |
| `Loc_Character` | Null | `Bone_Root` 下的外部演出定位节点，仅部分入场/演出动画带大位移 |
| `Bip001` | LimbNode | `Bone_Root` 下的实际 Biped 骨架根级节点；TurnBack 的视觉根级旋转/位移轨道落在这里 |
| `Bip001 Pelvis` | LimbNode | 骨盆，固定轴偏移（-90,-90,0） |

> 单位换算佐证：`Run_Loop` 的外部参考轨道 `Root.tZ = 4.2` / 时长 `0.417s` ≈ **10 m/s ≈ 1007 cm/s**，与运行时日志中 run 速度 ~1050 cm/s 吻合。`Bip001` 也带有对应的根级位移轨道，因此导入 UE 后不能只处理外部 `Root`；要么在资产侧制作 `Bip001` In-Place 副本，要么在 AnimBP 对骨架根姿势做抵消。

---

## 2. Root Motion 总览

绝大多数动画是**原地播放**（`Root` 位移/旋转全 0），位移交给 gameplay。只有以下动画自带 root motion：

### 2.1 带整体旋转（yaw）的动画（全部 3 个）

| 动画 | 时长(s) | Root.rY | 说明 |
|---|---|---|---|
| `Ani_TurnBack` | 2.38 | **-180°** | 急停转身，root motion 转身 |
| `Ani_HitFly_Back` | 4.98 | **+180°** | 向后击飞，转身倒地 |
| `Ani_ZipLine_Back` | 1.42 | **-180°** | 索道回身 |

### 2.2 带明显前进位移（`Root.tZ`，单位米）的动画（节选）

| 动画 | 时长(s) | Root.tZ | 类型 |
|---|---|---|---|
| `Ani_Attack_Normal_03` | 1.40 | 18.9 | 前冲攻击 |
| `Ani_Attack_Rush_01` | 1.13 | 16.2 | 突进 |
| `Ani_Attack_AssaultAid` | 1.35 | 15.6 | 强攻支援 |
| `Ani_Attack_ExSpecial_01` | 2.35 | 15.6 | EX 特殊 |
| `Ani_ZipLine_Fall` | 0.62 | 14.8 | 索道下落 |
| `Ani_Attack_Special_01` | 2.02 | 11.4 | 特殊攻击 |
| `Ani_Attack_Normal_Enhance_01` | 1.27 | 11.3 | 强化普攻 |
| `Ani_Evade_Front_01` | 6.18 | 10.6 | 前闪 |
| `Ani_Walk_Start` | 1.42 | 9.6 | 起步 |
| `Ani_Evade_Back_01` | 5.05 | -6.7 | 后闪（负=后退） |
| `Ani_Walk_Loop` | 0.65 | 4.8 | 走循环（≈7.4 m/s） |
| `Ani_Run_Loop` | 0.42 | 4.2 | 跑循环（≈10 m/s） |

> `_End` 收招/回位类动画的 `Root.tZ` 基本为 0，属原地播放。

### 2.3 `Loc_Character` 位移（入场演出专用）

| 动画 | Loc.tX |
|---|---|
| `Ani_SwitchIn_Attack_01` | -16.4 |
| `Ani_SwitchIn_Attack` | -10.7 |
| `Ani_SwitchIn_Attack_01_End` | -5.1 |

---

## 3. TurnBack 深度解剖

TurnBack 时长 2.38s（约 72 帧 @30fps）。`Root` 节点随时间采样：

| t(归一化) | Root.rotY | Root.transZ |
|---|---|---|
| 0.00 | 0.00 | -0.00 |
| 0.06 | -82.90 | 1.76 |
| 0.13 | -178.56 | 3.77 |
| 0.19 | **-180.00** | 5.67 |
| 0.25 | -180.00 | 6.21 |
| 0.38 | -180.00 | 6.82（前进峰值） |
| 0.50 | -180.00 | 4.03 |
| 0.63 | -180.00 | -0.48（越过 0） |
| 0.88 | -180.00 | -6.71 |
| 0.94 | -180.00 | -8.27 |

### 结构解读（两段式）

- **第一段（t≈0 → 0.19，约前 0.45s）**：yaw 在极短时间内从 0 快速转到 -180° 并锁死；同时 `transZ` 上冲（旧方向的刹车/踩步惯性）。这是"急停 + 快速 pivot"。
- **第二段（t≈0.19 → 1.0）**：yaw 保持 -180°，`transZ` 回落并转负——在已转身的 `Root` 局部帧里，这代表**朝新方向加速跑出**。

即：转身量由 root motion 前置在头 0.45s 内完成，其余是朝新方向跑出的位移。

### 当前的双重旋转风险

当前 `MotionDriver::Init` 全局使用 `SetRootMotionMode(IgnoreRootMotion)`，引擎不会自动消费外部 `Root` 的旋转；`RootMotionParameterProcessor` 也只是读取资产中已经存在的 `RM_Yaw` 曲线，不会在运行时从 FBX 的 `Root.Lcl Rotation Y` 自动生成骨架姿势控制。

- `Root` 是外部参考节点，清掉或控制它不等于清掉骨架姿势；
- `Bip001` 的根级旋转仍会随原始 TurnBack 播放；
- `ApplyTurnBackRuntimeRotation` 在 `Released` 阶段把 Actor 追踪到当前输入 yaw；
- 如果不处理 `Bip001` 的烤入旋转，最终视觉朝向会同时受 Actor yaw 与动画姿势 yaw 影响。180° 时可能看起来像重复转回，任意角度时则会出现角度偏差或后半段反向。

因此不能只“清掉外部 Root”，也不能让动画旋转和代码旋转同时作为最终朝向来源。必须在 AnimBP 中动态抵消 `Bip001` 根级姿势，或使用 `Bip001` In-Place 副本。

---

## 4. 当前修复路径与 UE 配置

目标是把职责拆开：TurnBack 动画只提供急停、pivot 和跑出节奏；代码在 `Released` 阶段按 `DesiredWorldMoveDir` 计算实际输入目标 yaw；动画不再把固定 180° 当成最终角色转角。

### 4.1 推荐：创建 `Bip001` In-Place 测试副本

这是“代码负责最终转向”最干净的验证方式，且不需要修改原始 FBX 或原始 `.uasset`：

1. 在 Unreal 编辑器中复制 TurnBack 动画资产，命名为测试副本，例如 `TurnBack_InPlace_TEST`；原始动画保持不动。
2. 只在副本里处理真正的骨架根级 `Bip001`：固定/移除它的根级旋转，并同时固定/移除会被 gameplay 重复驱动的根级位移。不要只处理外部 `Root`，因为 `Root` 与 `Bone_Root` 同级且没有角色骨骼子节点。
3. 保留 `Bip001` 子骨骼的相对动作，把这个副本接到 `ABP_Pyrios` 的 TurnBack 状态播放。
4. 继续让现有曲线管线使用 `RM_Speed` 驱动速度、使用 `DesiredWorldMoveDir` 驱动 Released 位移方向；`RM_Yaw` 在这个副本方案中可以不接入。
5. 分别用 180°、135°、90°、-90° 等输入测试：Actor 最终 yaw 应接近输入目标，身体不应额外回转 180°，TurnBack 后半段应朝当前输入方向跑出。

如果编辑器提供 Remove Root Motion、Root Bone Lock 或类似功能，应用对象必须是导入后实际承载视觉根级动作的 `Bip001`，而不是 FBX 外部 `Root`。具体按钮名称取决于当前 UE 资产编辑器版本，所以先用副本验证结果，不要覆盖原资产。

### 4.2 保留原始动画时：AnimBP 动态抵消姿势

如果暂时不制作 In-Place 副本，则保留原始 `Bip001` 姿势，但要在 `ABP_Pyrios` 的 AnimGraph 中抵消它：

- 在 TurnBack 输出姿势之后（或最终姿势链中合适的位置）接 `Rotate Root Bone`；目标骨骼使用 `Bone_Root`，Yaw 接 `UZZZAnimInstance::TurnBackPoseYawCorrection`。
- 当前 C++ 变量的定义是 `TurnBackPoseYawCorrection = -TurnBackSourceYaw`，所以 AnimBP 不要再额外乘一次 -1。
- `TurnBackSourceYaw`/`RM_Yaw` 只是原始动画转身时序和姿势补偿参考，不是最终目标角；最终 Actor yaw 仍由 `MotionDriver` 根据实时 `DesiredWorldMoveDir` 计算。
- `RM_Yaw` 必须是资产中已有的累计曲线。当前 C++ 只调用 `GetCurveValue("RM_Yaw")` 采样，不会自动读取 FBX 的 `Root.Lcl Rotation Y`，也不会直接控制外部 `Root`。如果曲线不存在，补偿变量会保持 0。
- 由于 Pyrios 的 `Bip001` Euler 轨道与外部 `Root` 的 yaw 轨道不一定是同一坐标分解，首次接入后要在 ABP 预览和 PIE 中校验正负号与幅度；若 `-RM_Yaw` 不能完全抵消，应以 `Bip001` 实际视觉根级轨道重新烘焙补偿曲线，而不是把 Actor 再加转一次。

这条路径的核心仍是“动画姿势负责表现、代码负责最终朝向”，不能同时启用引擎 Root Motion yaw 或再叠加一段固定 180° 代码旋转。

### 4.3 `Back → WalkRun` 的蓝图过渡

C++ 已不再提供 `TurnBack_To_WalkRun` 或 `Locomotion_TurnBack_To_WalkRun`。在 AnimBP 中让 Back/TurnBack 状态以动画完整播放为主条件：使用该状态动画的 `Time Remaining (ratio) <= 0`（可留极小容差）后再转回 WalkRun。

`sig_turnback` 只负责 Frozen → Released 的“可以解冻并按输入跑出”时机，不是 Back 动画结束信号；`Released → None` 也不能单独作为 Back → WalkRun 的切换条件。若通用 Moving → Stop 过渡会抢先，给 TurnBack/Back 的完成过渡设置更高优先级，或让通用过渡排除 `MovingSubState == TurnBack`。

> 当前实现不要求把 TurnBack 的最终角度写死为 `-180°`。`RM_Yaw` 可选地提供源动画时间/补偿参考；实际目标角由输入方向实时决定。



---

## 5. 分类动画目录（body `Ani_` 全量）

时长单位秒。RM 列：`tZ`=前进位移(米)，`rY`=yaw(度)，空=原地。

### 5.1 Locomotion（移动）

| 动画 | 时长 | RM |
|---|---|---|
| `Ani_Walk_Start` | 1.42 | tZ 9.6 |
| `Ani_Walk_Loop` | 0.65 | tZ 4.8（≈7.4 m/s） |
| `Ani_Walk_End` | 5.62 | tZ 3.3 |
| `Ani_Walk_Start_End` | 4.35 | tZ 0.2 |
| `Ani_Run_Loop` | 0.42 | tZ 4.2（≈10 m/s） |
| `Ani_Run_End` | 5.12 | tZ 4.5 |
| `Ani_TurnBack` | 2.38 | **rY -180** + tZ 曲线 |
| `Ani_Idle_Loop` | 4.02 | 原地 |
| `Ani_Idle_AFK` / `_AFK_Loop` | 4.52 / 5.35 | 原地 |
| `Ani_MC_Stand_Idle01_Loop` | 8.02 | 原地 |
| `Ani_MC_Stand_Think_Loop` | 4.02 | 原地 |

### 5.2 Attack（攻击，均含前冲 tZ，`_End` 为收招）

| 动画 | 时长 | tZ |
|---|---|---|
| `Ani_Attack_Normal_01 / _02 / _03` | 1.68 / 1.35 / 1.40 | 3.5 / 6.1 / 18.9 |
| `Ani_Attack_Normal_Enhance_01~04` | 1.2~1.7 | 11.3 / 6.2 / 3.0 / 2.7 |
| `Ani_Attack_Rush_01` | 1.13 | 16.2 |
| `Ani_Attack_AssaultAid` | 1.35 | 15.6 |
| `Ani_Attack_Special_01` | 2.02 | 11.4 |
| `Ani_Attack_ExSpecial_01` | 2.35 | 15.6 |
| `Ani_Attack_Counter_01` | 1.35 | 6.5 |
| `Ani_Attack_ParryAid_L / _H / _Start` | 0.68 / 1.02 / 5.35 | 0.4 / -3.7 / 3.3 |
| `Ani_ReflectBullet_Loop` | 0.42 | 4.2 |

### 5.3 Hit / Death（受击/死亡）

| 动画 | 时长 | RM |
|---|---|---|
| `Ani_Hit_L_Front / _Back` | 5.02 | tZ ±0.7 |
| `Ani_Hit_H_Front / _Back` | 4.75 / 4.35 | tZ -1.5 / 2.4 |
| `Ani_Hit_Shake` | 0.43 | 原地 |
| `Ani_HitFly_Front` | 4.98 | tZ -9.0 |
| `Ani_HitFly_Back` | 4.98 | **rY +180** + tZ -9.1 |
| `Ani_Death` | 5.02 | 原地 |
| `Ani_Revive_01~04` | 1.02 | 原地 |

### 5.4 Evade（闪避）

| 动画 | 时长 | tZ |
|---|---|---|
| `Ani_Evade_Front_01` | 6.18 | 10.6 |
| `Ani_Evade_Back_01` | 5.05 | -6.7 |

### 5.5 ZipLine（索道）

| 动画 | 时长 | RM |
|---|---|---|
| `Ani_ZipLine_Enter_Start / _Loop / _End` | 0.35 / 0.75 / 0.78 | 起步 tZ 1.7 |
| `Ani_ZipLine_Middle_Loop` | 0.32 | 原地 |
| `Ani_ZipLine_Change` | 2.12 | 原地 |
| `Ani_ZipLine_Fall` | 0.62 | tZ 14.8 |
| `Ani_ZipLine_HitFly` | 0.72 | tZ -3.9 |
| `Ani_ZipLine_Back` | 1.42 | **rY -180** + tZ -10.0 |
| `Ani_ZipLine_Exit` | 2.82 | tZ 3.6 |

### 5.6 SwitchIn / SwitchOut（上下场）

| 动画 | 时长 | RM |
|---|---|---|
| `Ani_SwitchIn_Normal` | 5.28 | tZ 4.5 |
| `Ani_SwitchOut_Normal` | 0.80 | tZ -3.4 |
| `Ani_SwitchIn_Attack / _01` | 3.52 | Loc.tX -10.7 / -16.4 |
| `Ani_SwitchIn_Attack_Ex_01~04 / _Start / _End` | 1.6~6.0 | 多数原地，Ex_03 tZ 7.8 |

### 5.7 ExQTE / QuestStart（连携/剧情起手）

| 动画 | 时长 |
|---|---|
| `Ani_ExQTE_Start_01~04`（+ `_01_Start`） | 4.02 |
| `Ani_QuestStart` | 8.18 |

### 5.8 UI / Gal（界面立绘 / 演出表情）

- UI：`Ani_UI_CharSel_Start/_Loop`、`Ani_UI_Detail`、`Ani_UI_Skill`、`Ani_UI_Equipment`，及状态互切 `StoD/StoE/DtoS/DtoE/EtoS/EtoD` 等，均 3~4s、原地。
- Gal：`Ani_Gal_Idle`、`Ani_Gal_Angry/Sad/Surprise/Think` 的 `Start/Loop/End` 三段，3~4s、原地。

### 5.9 Camera / Effect（非骨骼）

- `Cam_*`（10 个）：相机动画，无骨骼 root motion。
- `Eff_Pyrois_*`（约 60 个）：特效轨道（Trail/Hit/Flash/BG/MeleeTrail 等），多数无 `Root` 采样或极短。
- `InLevelRoleHud*` / `PyroisPanel*` / `TL_C30_16_*`：UI/时间线专用。

---

## 6. 与现有代码管线的对接状态

| 当前实现 | 作用与使用方式 |
|---|---|
| `RootMotionParameterProcessor` | 读取 `RM_PosX`、`RM_PosY`、`RM_Dist`、`RM_Speed`，并可选读取资产中已有的累计 `RM_Yaw`；`RM_Yaw` 只写入 `AnimCurveYaw/AnimCurveYawDelta`，不会自动从 FBX 外部 `Root` 生成，也不会直接旋转 Actor。 |
| `MotionDriver::Init` 全局 `IgnoreRootMotion` | 防止引擎 Root Motion 与自研曲线位移叠加；当前 TurnBack 仍走代码驱动的 Actor 朝向。 |
| `ApplyTurnBackRuntimeRotation` | 仅在 `Released` 阶段用 `DesiredWorldMoveDir.Rotation().Yaw` 作为实时目标，通过 `FixedTurn` 追踪；不再写死 `180°`，也不把 `RM_Yaw` 当最终角度。 |
| `UZZZAnimInstance::TurnBackPoseYawCorrection` | 供 `ABP_Pyrios` 的 `Rotate Root Bone` 使用，当前值为 `-TurnBackSourceYaw`；只用于保留原始动画时抵消姿势，使用 `Bip001` In-Place 副本时可不接。 |
| `ZZZLocomotionDecisions` | 已删除 `TurnBack_To_WalkRun` / `Locomotion_TurnBack_To_WalkRun`；Back → WalkRun 的完整动画播放条件由 AnimBP 的 `Time Remaining (ratio)` 负责。 |
| `TurnBackPhaseProcessor` | `sig_turnback` 只负责 Frozen → Released 的解冻时机；它不是 Back 动画结束信号。 |
| `HitFly_Back` / `ZipLine_Back` | FBX 中同样带外部 Root yaw，但当前 Source 只为 TurnBack 提供实时输入重定向；不能因为存在 `RM_Yaw` 字段就认为这两个动画已经自动接入同一套最终转向逻辑。 |

资产结构上要始终区分：外部 `Root` 只作为源动画参考，`Bone_Root → Bip001` 才是角色视觉骨架链。要实现“代码独占最终转向”，优先验证 `Bip001` In-Place 副本；若保留原动画，则在 AnimBP 用 `TurnBackPoseYawCorrection` 抵消其根级姿势。

> 核心原则：**动画提供时序，代码按实时输入决定最终 Actor yaw，AnimBP/副本消除 `Bip001` 烤入旋转；三者不能把同一段转身重复叠加。**

---

## 附：复现方法

```bash
cd AAADocs/Scripts
# 全部 take 概览（结构/计数/清单）
python fbx_bin_reader.py <fbx> overview
# 单个 take 关键节点轨道
python fbx_anim_extract.py <fbx> take TurnBack
# 全量 root motion 目录（过滤 Ani_）
python fbx_anim_extract.py <fbx> catalog Ani_
# 某 take 指定节点随时间采样
python fbx_anim_extract.py <fbx> trace TurnBack Root
```
