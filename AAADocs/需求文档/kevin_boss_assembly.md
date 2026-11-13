# Kevin DemonBattle Boss 完整组装与视听制作

状态：**单机组装、场地照明、全角色禁互踩和最小真实联机已交付；原版视听完整还原及下列未验证范围未签完成。** 当前入口为 `/Game/Map/BH3/L_KevinBoss_P3`。逐步制作和修复历史保留在 Git，本记录只保留现行结论、接口、证据和剩余边界。

## 目标

- 现有 DemonBattle 单形态形成可实际交战的完整链路：技能、动画、两阶段选招、位移、命中、特效、声音及死亡清理。初版战斗数值由本项目设计，50% 血量切换递进技能池，配置可调，不冒称原版参数。
- 动画和声音优先使用真实来源；特效允许参考适配或原创，须明确来源与未知项。没有原调用事实时，不推定声音的选择、时点或命中条件。
- P3 是独立正式战斗场景；不改其它地图，不引入其它 Kevin 形态、玩家 E／R／F、全员失败／复活系统或引擎修改。

## 方案要点

- BossAI 经既有 GAS 入口请求能力；具体阶段、选招和表现使用 Blueprint、BT、Montage、Niagara、材质与数据资产。GA 管生命周期，Animation 管姿态和窗口，CMC 唯一执行胶囊位移，Combat 查询／去重，GA／GE／Execution／AttributeSet 结算。
- 用户已选完整 Dash_F 分段追击：约 1.07 秒、7.1 米，无伤害，经 BT→GAS→CMC 执行，方向由原生 Focus 决定；本 Boss 已移除 MoveTo，不伪造玩家输入。
- 地空连招保留完整原轨迹。飞行通过 `AcquireFlyingMovementMode`／`ReleaseFlyingMovementMode` 借还模式，结束交回原生重力，等待真实环境 Landed；`LandingRecovery` 只做表现。用户已选取约 0.033 秒 `Fly_Loop` 的末帧全身骨骼制作静止等待姿态，原序列只读，不循环其约 186 cm 根跳变。
- Kevin 继承共享 `BP_BossCharacter`，死亡结束按共享蓝图下一帧 `K2_HandleDeathFinished → UninitAndDestroy` 处理；不复制第二套原生销毁分支。正常结束、取消、死亡和目标失效须清理本技能资源。
- 用户已定全角色互相阻挡、不能互踩：共享 `AGGYGOCharacterBase` 胶囊为 `WalkableSlope_Unwalkable`，保留 Pawn 阻挡。CMC 仅在自由 Falling、无水平速度、碰到不可走角色胶囊且原生滑动速度低于清零阈值时，按本碰撞剩余时间的重力步长立即水平扫掠，随后继续原生滑动与重力。方向优先接触法线在重力平面的投影，同轴退为角色前向／右向；动画 RootMotion 或 Override RMS 接管时不介入，无跨 move 冲量、额外 Tick 或位置直写。
- P3 主光为 2 lux、启用投影，保留原方向／颜色和其余四盏灯；原 `T_LunarCrater_Reflection_Probe_Importance2` 用于强度 0.2 的 Movable SkyLight。原反射探针、材质、碰撞、导航、出生配置和全局曝光不变。这是 UE 项目照明适配。
- 命中专用声音仅从 Combat 有效命中事实进入 GA／GAS；持续声音随原 GA 资源退役。当前 Montage 单次声音集合与命中专用集合无交集，但播放实例和录音不能证明原版声音语义或设备听感。

制作与资料入口：

| 内容 | 现行入口 |
| --- | --- |
| FX | `AAADocs/Scripts/build_bh3_kevin_fx.py`；`AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_FX_Config.json` |
| 音效 | `build_bh3_kevin_audio.py`、`plan_bh3_kevin_audio.py`；同配置目录 `BH3_Kevin_Audio_Config.json` |
| 动画 | `build_kevin_skill_animation.py`、`audit_kevin_skill_poses.py`；Editor 的 `KevinMotionAssetBuilder`、`KevinCombatAssetBuilder`、`KevinBossAnimBlueprintAuthor` |
| GA／AI | `wire_kevin_boss_abilities.py`、`wire_bh3_kevin_combat.py`；Editor 的 `GGYGOBossAbilityGraphLibrary`、`GGYGOBossCombatAssetLibrary` |
| 场景 | `configure_kevin_boss_p3.py` 的 `apply_lighting(save=True)`、`lighting_readback()`；同配置目录 `BH3_Kevin_P3_Scene_Config.json` |
| 连续战斗与死亡阴影 | `run_kevin_battle.ps1`、`observe_kevin_battle.py`、`verify_kevin_battle.py`；`-DeathShadow` 只跑死亡阴影隔离夹具 |
| 最小联机 | `run_kevin_multiplayer.ps1`、`observe_kevin_multiplayer.py`、`verify_kevin_multiplayer.py` |

表中未写目录的脚本均在 `AAADocs/Scripts/`。动作及配置详见 [导入核对](../Assets/BH3/BH3_Kevin_DemonBattle_Import.md)、[职责契约](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Implementation.md)、[动作清单](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Action_Manifest.json)、[制作配置](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Wiring_Config.json)、[运行验证](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Runtime_Verification.md)。

## 当前状态

| 范围 | 已证明的结果与证据 |
| --- | --- |
| 资产与生产接线 | 22 个 Niagara、8 个材质、13 个命中 Cue 共 43 包；55 个声音包只读复用。26 份派生动画、ABP、19 个技能 Montage 和 5 个表现 Montage 已保存。GA／AI 47 包包含无伤害 Dash_F、两阶段动作池及授予。独立读回见 `Saved/Codex/KevinBossAssembly_20261111/FX_Read_Ready/editor.log`、`Animation_Read/editor.log`、`DashF_Read/editor.log`。 |
| 场景与导航 | P3 已保存并独立读回，唯一主灯带 `GGYGO.KeyLight`，PlayerStart／Encounter 引用正确，初始间距 18 m；KevinBoss 导航实际投影、完整路径及 9 个空中净空采样通过，原支撑碰撞未改。证据见同目录 `Scene_Create_NavExport/editor.log`、`Scene_Read/editor.log`。 |
| 编译与自动化 | BossAI、Boss GA、Combat、CMC Flying 和 Editor 制作接口已编译；15 项相关回归、两项动画回归及 NativeFocusRotation 通过。Combat Touch→Block 物理阻挡已与伤害去重分离，相关两项查询回归通过。日志见同目录 `Build_DashF/build.log`、`Build_ReviewFix/build.log`、`Review_Query/editor.log`、`Review_Editor_Read/editor.log`。 |
| 正式连续单机交战 | `Saved/Codex/KevinFinalBattle_20261113/FinalBattle5/editor.log` 与 `checks.json`：同一 P3 World、正式 BT 连续执行，首两次 Dash_F 为 710.86／710.51 cm，玩家静止、双方无伤害，距离 18 m→10.89 m→3.79 m；610→590 血穿过 50% 阈值切池，11 个攻击入口均实际执行。两条 AirChain 的原 Landed 回调当栈匹配各自 GA，均命中场地、0 角色 Landed。玩家生产普攻把 Boss 1200 血打到 0，玩家剩 30 血；原 Death GA／共享蓝图完成销毁，6.96 秒游戏时间后无 Boss Avatar、FX、声音或弹体，玩家 GA 和动作位移也已结束。 |
| 追击与视听 | `Battle_R7_DashF/editor.log` 证明玩家静止时两次完整 Dash_F 使距离 18 m→10.89 m→3.78 m，双方生命不变，随后攻击。预警平面 Rotator 参数顺序已修，实际画面见 `Battle_R9_Visual`、`Visual_Fire_Air`；后者暂停 BT 后走既有 GAS，只证明对应表现和落地。 |
| 场地照明 | `Saved/Codex/KevinBossLighting_20261113/Lighting_Final/editor.log` 新进程读回通过；`001_production.png`、`002_front.png`、`003_back.png` 已看图，正式镜头、角色正背与投影可见，冰预警／火蓄力／破环在新照明下可见。 |
| 全角色禁互踩 | `Saved/Codex/CharacterNoPerch_20261113/build_final2.log` 编译通过；`EffectivePolicy/editor.log` 读回八份 CDO 及实际玩家／Kevin 的有效 Unwalkable，Pawn Profile 保留；`Collision_Final2/editor.log` 八组真实物理下落均为 0 角色 Landed、1 环境 Landed，侧向仍阻挡。49 个真实 SavedMove 的本地预测／校正重放逐帧一致。 |
| 单机贴身空连 | 同目录 `Production_Final/editor.log` 的 Ice03、Fire02、AirChain01 全部经已授予 GAS，三次环境 Landed、0 角色 Landed，结束后稳定 Walking 至少 2 秒，动作位移／FX／声音／弹体无残留；`015_AirChain01_4.0.png`、`016_cleanup.png` 已看图。 |
| 最小真实联机 | `Saved/Codex/KevinNetwork_20261113/CloseLanding/` 的原生日志、观察数据与断言证明同 Editor Listen Server＋Client 经 IpConnection／ActorChannel 实际传包。正式 BT 先执行 Dash_F／Ice02，随后暂停 BT 经已授予 GAS 请求 Ice03、Fire02、AirChain01。服务器为 Authority、Boss GA 为 ServerOnly；客户端 SimulatedProxy 有 Montage 进度及骨骼变化，无本地活动 Boss GA。 |
| 联机落地、命中与清理 | AirChain01 前只在服务器预摆主机玩家至 Boss 前方 96 cm，等复制后起招，不写 Boss／客户端位置或轨迹。自由 Falling 有 10 次角色接触、0 角色 Landed，最终落场地，两端连续 2.19 秒 Walking／环境基底；两名玩家血量最终为 44／72，两端一致。客户端冰火命中 Cue 可见，18 个远端 FX 全部销毁，Encounter Avatar 销毁复制通过。 |

上表未写完整目录的单机日志位于 `Saved/Codex/KevinBossAssembly_20261111/`。联机客户端的 `000_Ice03_0.35.png`、`004_Fire02_1.1.png`、`010_AirChain01_4.0.png`、`011_cleanup.png` 已查看；统筹另复核传包日志、断言、火刃和地面收尾图。联机批次仅新增验证脚本及文档，无生产差分。

### 连续交战与死亡阴影的证据边界

完整交战使用原玩家输入桥自动提交 W／S／D／鼠标左键，按原招式收招窗决定接近或退让，并用 ControlYaw 配合 Held W 调整普攻朝向；诊断相机和关闭运动模糊只影响本次取景。BT 全程未停，不直接激活 Boss、不写角色位置、不改生命／伤害配置，也不直接销毁代替死亡。上述输入策略有脚本干预，不能代签物理设备或人工操作体验。追击、切池时交战、两条空连、落地和死亡画面已核；`FinalBattle5/194_cleanup.png` 暴露死亡阴影残留，不能称该场原画面完全清空。

死亡阴影已定位为 Kevin 没有 PhysicsAsset 时采用静态导入包围盒，死亡末帧的真实 CPU 蒙皮表面超出其 3.27 倍；VSM 只按图元范围失效，Actor 已销毁仍留下超出部分。`Saved/Codex/KevinFinalBattle_20261113/ShadowDeath2/005_cleanup.png` 可见残影，随后仅临时关闭 VSM 缓存的 `006_cleanup_uncached.png` 残影消失。该隔离夹具暂停 BT，经已配置伤害 GE→HealthSet→原 Death GA／共享蓝图销毁，不替代前述普攻胜利。

现行配置 `mesh_bounds_scale=4` 由 `wire_bh3_kevin_combat.configure_mesh_bounds(apply=True)` 只编译保存 Kevin 蓝图的 Mesh；新制作和读回也核此值。`Saved/Codex/KevinFinalBattle_20261113/BoundsApply/editor.log` 保存成功；新进程 `Saved/Codex/KevinFinalBattle/ShadowFinal/editor.log` 读回 4，末帧表面占新包围盒范围的 0.818。`004_death_finished.png` 可见死亡姿态和正常投影，`005_cleanup.png` 在默认 VSM 缓存仍开启、销毁后 5.01 秒时已无残影，两图已核。未改死亡流程、Mesh 源资产、物理碰撞或生产全局缓存开关。此修复只有蓝图默认值和制作脚本变化，沿用当前已构建 DLL，未重复 UBT；脚本语法、完整战斗日志断言和死亡专项通过，我方 UE 已正常退出。

复现命令：`AAADocs/Scripts/run_kevin_battle.ps1 -RunName <新名称>`；结束后用 `python AAADocs/Scripts/verify_kevin_battle.py <输出目录>` 核日志，关键画面另行查看。只复核死亡阴影时增加 `-DeathShadow`，该模式不输出整场录音或逐次落地截图。原失败试次及提前 EndPIE 引起的 `HeroInputReleased` 诊断保留于 `Saved/Codex/KevinFinalBattle_20261113/`；完整战斗宿主现等待玩家能力和动作位移自然结束，最终场次无 AbilitySystem Error。启动段 13 条通用 Automation 条件失败仍单列为未归因。

### 特效来源边界

全部 22 个系统的粒子、材质形状、数量、速度和寿命均为项目创作。原武器贴图仅证明冰刃青蓝／火刃橙黄配色，原翼膜贴图仅证明青白、尖角和破碎轮廓；完整原贴图路径在 FX 配置 `references`。已启用技能有实际画面；未启用的防御、领域效果仅签资产读回。

| 系统 | 来源与创作范围 |
| --- | --- |
| Ice／Fire WeaponTrail、Charge、Strike、Warning、GroundBreak、Domain、DashWake、HitImpact | 借用原冰火配色；Ribbon、粒子、蓄力、爆发、地面预警及破环均为项目创作，预警尺寸消费实际判定几何。 |
| WingGuard、GuardBreak、AerialGather | 参考原翼膜颜色与尖角轮廓，防御／破碎／聚集效果和时序为项目创作。 |
| IceProjectile | 参考冰刃配色与轮廓，弹体碎片及 Ribbon 为原创，位移和生命周期归实际 Projectile／GA。 |
| FireWingGuard | 将翼膜尖角与火刃配色组合创作，无原版火翼防御效果证据。 |
| DeathDissipate | 无直接原效果来源，原创中性青灰碎片消散。 |

### 交付

- 已分仓推送：[单机源码](https://github.com/WuDuElysia/GGYGO_Source/commit/7b6742c)、[原接口笔记](https://github.com/WuDuElysia/Lyra_Learn_note/commit/5fa4f68)、[照明](https://github.com/WuDuElysia/GGYGO/commit/28fb375)、[禁互踩源码](https://github.com/WuDuElysia/GGYGO_Source/commit/0616e3f)、[禁互踩记录](https://github.com/WuDuElysia/GGYGO/commit/0f7883f)、[联机脚本与记录](https://github.com/WuDuElysia/GGYGO/commit/c9409e9)、[联机核收](https://github.com/WuDuElysia/GGYGO/commit/a673014)。精确文件集合以各仓提交为准。
- Character／Movement 的禁互踩核心差分评审无剩余阻塞；先前 Combat 物理阻挡问题已修并回归。联机批次没有生产接口变更。
- `Content/Characters/Boss/Kevin/DemonBattle/` 和 `Content/Environments/BH3/Stage/Stage_KevinBoss_P3/` 继续按既有忽略规则留在本机；只有已跟踪的 P3 地图随父工程提交。新 checkout 需要这些原导入及制作资产，不能仅靠 Git 还原完整运行环境。
- 未覆盖用户手改的 Pyrios Combo GA、Normal01～03 Montage 或其它未提交资产；未 SaveAll。日志、PNG、Master WAV 和运行数据在 Saved 下，不入库。

## 未完成项

- 原光度、曝光、HDR 解码、Cube 面朝向及原粒子效果未证明等价；当前照明和 FX 按已授权项目适配交付。
- 原声音选用、调用条件和精确时点仍有未知，Dash_F 使用同 Boss 候选声音 E3188014124，原映射未证实；组件播放和录音不能代替设备试听。
- 本次空闲物理内存约 13.6 GiB，低于既有双 Editor 入口要求，因此联机使用同进程双 PIE World。独立进程／跨设备、完整网络与中断矩阵、联机死亡演出、弹体飞行复制和模拟代理独立 RMS 未验；本地 49 SavedMove 重放不代替实际传包。
- Cook、性能（包括扩大 Kevin 包围盒的 VSM 开销）、物理输入设备及原生 Obsidian Canvas 渲染未验。笔记已检查 JSON、节点与链接，不用结构检查代替原生画面。
- 专项红绿日志启动段均保留 13 条通用 `LogAutomationTest: Condition failed`，尚未归因。旧跨 move 冲量污染、同轴／微小滑动失败和脚本诊断仍保留在对应证据目录；当前专项通过不表示整份日志无错。

## 验收标准

- 启用动画、GA／AI、FX 和场景配置保存并独立读回；Montage 窗口、标签和原轨迹对应，顶层业务留在可视化资产。
- P3 的 NavMesh 覆盖战斗区，PlayerStart 和 Encounter 引用正确，其他地图保持原状。
- 正式 BT／Encounter 能执行可交战循环、两阶段切换和死亡清理，普通追击消费完整原 Dash_F，主要技能取得实际画面及声音播放证据。
- 角色保持相互阻挡，不能把其它角色当成落地基底；技能回到原生重力后滑离到环境地面，资源正常退役。
- 最小联机逐项证明权威、实际传包、客户端动作／FX／命中、贴身环境落地和结束清理；同进程结果不代签独立进程或未触发场景。
- 项目创作、原版来源和未知项明确区分；原版等价、完整网络或设备听感只能由对应证据验收，不能从已有局部成功推定。
