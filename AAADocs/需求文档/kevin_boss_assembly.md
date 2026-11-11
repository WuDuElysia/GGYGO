# Kevin DemonBattle Boss 完整组装与视听制作

状态：未完成，交给 Codex。源码和制作脚本已写好并随工作树编译，约 134 个资产包还没制作，没有任何交战运行证据。第一个独立验收点是特效剩余 35 包。

## 目标与用户决定

- 把 Kevin DemonBattle 从素材和少量试招接线组装成可实际交战的 Boss：技能、动画、选招／阶段、位移、命中、特效和音效形成完整链路。
- 战斗调参由本项目设计（用户 2026-11-05 决定）：完整 DemonBattle 单形态、两阶段，暂定 50% 血量切换递进技能池；血量、伤害、冷却、权重和阶段都做成数据可调，不冒称原版参数。初版数值由负责人结合当前玩家能力自定。
- 动画和音效优先还原真实来源。特效允许参考原效果图适配创作，也允许完全原创，不用逐项审批，但要区分参考来源、实际改编和未知项。
- 只用现有 DemonBattle 形态，不引入其他 Kevin 形态、玩家 E／R／F、全员失败／复活系统或引擎修改。

## 交付范围

1. 按真实片段梳理可用技能、移动、待机、防御／反击、阶段／演出、死亡等用途，逐个说明已组装、辅助片段、缺配对或缺来源不启用。不按 AS／BS／Loop 名称机械拼招。
2. Kevin 的顶层行为、阶段策略、选招／连招组合、具体技能流程和表现由蓝图、BT、Montage、Niagara、材质图和数据资产完成；C++ 只提供通用机制和接口。BossAI 经既有 GAS 入口选招，形成真实的战斗循环，不停在测试脚本直接激活。
3. 按真实动作定前摇、有效段、收招和可中断点。Animation 管姿态和窗口，CMC 唯一执行胶囊位移；导出根轨迹与派生原地动画匹配，避免双重位移。远程、范围、召唤、投技不一律伪装成近战扫掠。
4. Combat 查询和去重，GA／GE／Execution／AttributeSet 结算。正常结束、取消、死亡和目标失效时归还本技能资源。
5. 每个启用的技能有适配动画的特效和声音；特效有统一的 Boss 视觉语言、危险提示和强弱层次，保留真实挂点、朝向、Follow／Stop 和清理语义。
6. 音效接挥击、命中、蓄力／爆发、循环、脚步等。没有原调用时点或原声时标"未知／候选"，不把替代声冒称原版；缺口只阻塞对应声音。
7. 在独立场景 `/Game/Map/BH3/L_KevinBoss_P3` 通过正式 Encounter 入口制作可交战场景：有玩家目标、血量、命中，Boss 正常结束和死亡后清理干净。不改其他地图和用户未保存的关卡。

## 方案要点与约束

- 多段地空轨迹按完整技能保留，不把各段独立当落地技能，也不静默清零 Z。飞行段用 CMC 的 `AcquireFlyingMovementMode`／`ReleaseFlyingMovementMode` 借用和归还 Flying 模式，原曲线结束后交给 CMC 原生重力，等真实 Landed 再回地面池或播落地表现；不固定下降速度，不伪造落地。`LandingRecovery` Montage（Main 2.45 s，Impact 0～0.35 s）只作表现，不代替真实 Landed。
- 共享 Kevin Skeleton／ABP／Montage 只能有一个写入者，串行制作；特效、音效、动画、GA、BT 包互不冲突的可以并行。
- 制作脚本和配置：
  - 特效：`AAADocs/Scripts/build_bh3_kevin_fx.py`，配置 `AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_FX_Config.json`（22 个 NS、8 个材质、13 个命中 Cue，共 43 包）。
  - 音效：`AAADocs/Scripts/build_bh3_kevin_audio.py`、`plan_bh3_kevin_audio.py`，配置 `BH3_Kevin_Audio_Config.json`，标签 `Config/Tags/BH3_Kevin_AudioTags.ini`。
  - 动画：`AAADocs/Scripts/build_kevin_skill_animation.py`，Editor 源 `KevinMotionAssetBuilder.cpp`、`KevinCombatAssetBuilder.cpp`、`KevinBossAnimBlueprintAuthor.*`，标签 `Config/Tags/KevinBossAnimationTags.ini`。
  - GA／AI：`AAADocs/Scripts/wire_kevin_boss_abilities.py`、`wire_bh3_kevin_combat.py`，Editor 源 `GGYGOBossAbilityGraphLibrary.*`、`GGYGOBossCombatAssetLibrary.*`，配置 `BH3_Kevin_Ability_Config.json`，标签 `Config/Tags/KevinBossTags.ini`。
  - 场景：`AAADocs/Scripts/configure_kevin_boss_p3.py`，配置 `BH3_Kevin_P3_Scene_Config.json`，`Config/DefaultEngine.ini` 的 KevinBoss 导航 Agent（半径 60、高 250，Default 保持第 0 项）。
- 资料入口：[导入核对](../Assets/BH3/BH3_Kevin_DemonBattle_Import.md)、[动作与职责契约](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Implementation.md)、[动作清单](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Action_Manifest.json)、[制作配置](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Wiring_Config.json)、[原验证入口](../Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Runtime_Verification.md)。

## 当前状态

- `/Game/Characters/Boss/Kevin/DemonBattle/` 现有 222 个包：Animation 78、Audio 101（原导入 46 个加上已保存的 55 个声音包）、FX 8 个材质、Abilities 1 个等。`Abilities/Templates` 不存在。
- 已保存的 55 个声音包和 8 个特效材质只读复用，不重做。
- 上一次特效制作在比对第一个材质实例时，把父材质继承值误判成覆盖而中止，没有保存任何包。修正方法：只比对实际开启的覆盖位。
- BossAI（选招、Definition、State、Controller、Encounter）、Boss GA（Attack、Death、Projectile、AudioActor、资产配置）、Combat 范围／弹体命中查询、CMC 飞行模式借用、Kevin Editor 制作源码都在工作树里并随整个工作树编译，但没有任何交战运行证据，所以没有提交 Git，清单见 [Codex 交接](../Coordination/Handover_Codex.md)。
- 没有任何战斗、画面、声音、导航或联机运行证据。

## 未完成项（按依赖顺序）

1. **特效 35 包（第一个独立验收点）**：22 个 NS 和 13 个命中 Cue。按修正后的比对方式跑特效制作脚本，Niagara 编译完成后只读读回，写参考／原创对照表。
2. **动画**：26 份派生原地动画（源约 82.5 MiB）、ABP、Montage 和窗口标签。核根轨迹与原地动画一致。
3. **GA 与 AI**：3 个共享模板（`BP_GA_BossGroundFlow_KVB`、`BP_GA_BossFlightFlow_KVB`、`BP_GA_BossDeathFlow_KVB`）、15 个技能、死亡 GA，以及 State／BTS／BT／Definition 等共 35 包；两阶段在 50% 血量切换。同时关闭蓝图分层审查的 Q01。
4. **P3 场景**：装配 NavMesh、PlayerStart、Encounter，只保存 `L_KevinBoss_P3`。
5. **实战验收**：在 P3 里打一场完整战斗到 Boss 死亡，两阶段切换可见，主要技能有画面和声音证据，死亡后清理干净。
6. 验收后同步受影响模块的 Obsidian 笔记，提交源码和资产。

## 验收标准

- 特效：35 个包落盘，Niagara 编译无错，读回引用正确；对照表区分参考改编和原创。
- 动画：包落盘并编译，Montage 窗口和标签读回正确，派生动画根位移为 0 且与原轨迹对应。
- GA 与 AI：35 包落盘编译通过；模板图的事件和关键连线读回正确；Definition 的阶段池和授予引用正确。
- 场景：P3 保存后 NavMesh 覆盖战斗区，PlayerStart 和 Encounter 引用正确，其他地图没改。
- 实战：Boss 能完成至少一次完整战斗循环到死亡，两阶段切换可见，主要技能有画面和声音证据，死亡后没有残留。
