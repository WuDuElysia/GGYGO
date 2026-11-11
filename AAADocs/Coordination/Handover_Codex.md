# 交接给 Codex（2026-11-12）

Kiro 的需求收尾批次到此结束。下面是已完成的内容、等用户决定的三项、剩余工作，以及工作树里没有提交的文件。

## 新工作流

先读根目录 [AGENTS.md](../../AGENTS.md) 和 [Rules/TaskWorkflow.md](../Rules/TaskWorkflow.md)。要点：

- 一个需求一个负责人，从读代码、实现、编译、测试做到交付，跨模块也不拆给多人。
- 负责人自己做增量编译和相关自动化测试，不等集中窗口；同一工作树同一时间只跑一个 UBT 构建。
- 开工前在 [Board.md](Board.md) 的占用表登记要改的文件、共享资产或构建，做完删掉。只有同一文件、同一共享资产（地图、Skeleton、Master 材质等）、同时构建才算冲突。
- 不再做冻结、前像／后像、哈希身份、保护集合、租约、预算核算和回执 JSON。文件变化以 Git diff 为准，证据只留日志或截图路径加一句结论。
- 默认不发消息，只在真实阻塞、需要别人决定、交付时发；交付回执格式见 TaskWorkflow。
- 不覆盖用户未保存的工作，不 SaveAll；只启停自己的 UE 实例。

### 运行环境提示

- 构建：`& 'F:/UE_5.8/Engine/Build/BatchFiles/Build.bat' GGYGOEditor Win64 Development -Project='F:/ue_project/GGYGO/GGYGO.uproject' -WaitMutex -NoHotReloadFromIDE`。
- 真实 RHI 运行：`UnrealEditor.exe GGYGO.uproject /Game/Map/L_Movement_Test -d3d12 -UserDir=<证据目录>/Editor -AbsLog=... -ExecCmds="py <脚本>"` 或 `"Automation RunTests <名>;SoftQuit"`。`-ExecutePythonScript` 会在脚本结束后退出编辑器，逐帧观察脚本只能用 `-ExecCmds=py`。
- 需要前台焦点的场景（改键页、声音）不加 `-unattended`，在我方 Editor 进程里用 Win32 API 把窗口置前；声音取证加 `au.DisableAppVolume 1`，并把 `bThrottleCPUWhenNotForeground` 设为 False。可复用 `Saved/Kiro/requirements-closeout/I03/observe_key_settings.py`、`I06/host.py`。
- 机器内存 31.8 GiB，单个 Editor 起步约需 11 GiB。单项新增数据超过 1 GiB 先问用户。
- 原版未知的 cue、时点、挂点保持未知，不用替代素材冒称还原。E／R／F 输入保持延期；Dodge GA／CMC 不恢复；斗篷只读暂挂。
- 本批的逐项证据在 `.agents/tasks/requirements-closeout/`（`checklist.md`、`evidence/I*.md`），运行目录在 `Saved/Kiro/requirements-closeout/`，两处都只在本机，不入库。

## 本批已完成

普攻第一段主弧修好了（共享网格 `FXMD_DAO_001_ced427b6fbbf` 角点 UV／顶点色错位，按角点展开的 FBX 原位重导入），未预热的第一刀会等渲染资源就绪后再出刀且特效同帧可见，见 [normal01_first_strike](../需求文档/normal01_first_strike.md)。改键页面迁到共享 UMG 并在真实前台走通全部操作，出战队员死亡后的自动替补改由共享 `BP_PlayerState` 发起，见 [blueprint_layering_followups](../需求文档/blueprint_layering_followups.md)。角色倒下时地面的放射条纹（VSM 缓存残影）修掉了，换人拖影确认是相机跳变的运动模糊，见 [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「角色受光与阴影」。普攻第三段的技能声和命中声分别完成了自动化取证，见 [normal03_audio](../需求文档/normal03_audio.md)。另外用户已决定：生产镜头保持近景（脚被截掉可以接受）；三个旧 ZZZ 动画 spec 直接关闭（[zzz_legacy_anim_spec_closeout](../需求文档/zzz_legacy_anim_spec_closeout.md)）。

注意：重导入的网格 `/Game/Characters/Shared/FX/ZZZ/Meshes/FXMD_DAO_001_ced427b6fbbf` 在 `.gitignore` 忽略的素材目录里，不在 Git 中，修复只存在于本机；原包备份在 `Saved/Kiro/requirements-closeout/I01/Backup/`，重导入工具是 `Saved/Kiro/requirements-closeout/I01/fix_dao_mesh.py`。同理，`BP_PC_Pyrios` 的 `BoundsScale` 修复依赖的物理资产和骨骼网格也是本地导入资产。

## 等用户决定的三项

这三项的自动化部分都已通过，只差用户的选择。用户回答后由指定的负责人接着做。

1. **起步／停步的骨盆单帧跳变**（[walkrun_turnback_production_camera](../需求文档/walkrun_turnback_production_camera.md)）。WalkStart 结尾骨盆单帧移动约 10.7～10.9 cm（平跑每帧不到 1 cm），RunStop 入口 4～10 cm，逐帧图 `Saved/Kiro/requirements-closeout/I04/Run_R7/start_pop_consecutive.png`。
   - A：接受现状。
   - B：另开动画修复，在 ABP_Pyrios 里定位那条约 0.01 s 的过渡，改成 0.1～0.2 s 惯性化或相位匹配；起停观感会变，要重拍验收。
   - 附带问：RunStop 开头几帧的前冲（`Run_End` 根运动自带）接受不接受。
2. **普攻第三段音效试听**（[normal03_audio](../需求文档/normal03_audio.md)）。在 `L_Movement_Test` 的 PIE 里打出第三段，空挥一次、打中一次。
   - A：两种声音都可以；B：技能声要换；C：命中声要换；D：时点不对（早了还是晚了）。
3. **普攻连段的预输入**（[normal01_first_strike](../需求文档/normal01_first_strike.md)）。spec 5.3 写"连段缓冲输入在下一段生效"，当前只接受攻击接续点（Normal01 在 0.275 s）之后的按下，之前的按下直接被拒。
   - A：接受现状，改 spec 5.3 措辞后勾选 `.kiro/specs/abilitysystem-input-request/tasks.md` 任务 5；手感不变。
   - B：另立需求接回预输入；手感会变，要重跑普攻冒烟。

不阻塞、可顺带问用户的小问题：改键页按钮字号和面板透明度要不要改；第三段打中时要不要加只在命中时出现的特效（只能用替代素材）；着色器 DDC 真冷首击要不要做（数据远超 1 GiB）；正背对照里胸口光球、手臂发光、头发和斗篷颜色与原图的差异要不要另开需求。

## 剩余工作

按收尾清单顺序列出，括号里是清单编号和依赖。建议的开工顺序：先做三个小项（I22、I24、I14），再做特效线（I11→I12→I13），Kevin（I15 起）和最小联机（I20 起）是两条独立的大线，可以并行，但都要先确认内存够用；I26 最后做。

| 编号 | 一句话目标 | 当前真实状态 | 建议第一步 | 需求记录 |
| --- | --- | --- | --- | --- |
| I11 | 逐动作盘点特效／音效接线，Normal02、Normal03 真实渲染实拍确认各层可见 | 未开始（上一轮开工后无任何改动即停）。14 个 NS 中 13 个被普攻 GA 引用，Rush NS 没人用；Normal03 没正式实拍 | 写盘点表；同时用 `Saved/Kiro/requirements-closeout/I01/Scan_R1/scan.json` 看图确认其它网格角点错位的影响 | [fx_audio_wiring](../需求文档/fx_audio_wiring.md) |
| I12（依赖 I11） | Special01、ExSpecial01 用测试直接激活，验证动作、特效、声音、命中、自然结束 | 两个 GA、Montage 已接好，从没运行过；E／R／F 延期 | 写一个通过 ASC 直接激活的自动化叶，不改生产输入 | [fx_audio_wiring](../需求文档/fx_audio_wiring.md) |
| I13（依赖 I11） | Rush、冲刺、TurnBack 的特效和声音接到现有移动表现链 | 都没有确认接线 | 查 LocomotionFX 组件和 `PublishLocomotionFX` 能接哪些；Rush 只能靠新 GA／输入触发的话交用户决定 | [fx_audio_wiring](../需求文档/fx_audio_wiring.md) |
| I14 | 蓝图分层 Q02～Q05 资产图只读读回 | 源码侧复读过，资产图没打开过 | 用 Editor Python 只读读回四项，结论写进审查文档 | [blueprint_layering_followups](../需求文档/blueprint_layering_followups.md) |
| I15 | Kevin（一）：特效剩余 35 包（22 NS＋13 命中 Cue） | 上次制作在比对第一个材质实例时把父材质继承值当成覆盖而中止，没保存 | 改成只比对实际开启的覆盖位，再跑 `AAADocs/Scripts/build_bh3_kevin_fx.py`。**这是 Kevin 的第一个独立验收点**：35 包落盘、Niagara 编译无错、读回正确、有参考／原创对照表 | [kevin_boss_assembly](../需求文档/kevin_boss_assembly.md) |
| I16（依赖 I15） | Kevin（二）：26 份派生原地动画、ABP、Montage、窗口标签 | Editor 制作源码已写，包没做 | 运行动画制作入口并读回根轨迹 | 同上 |
| I17（依赖 I16） | Kevin（三）：3 模板＋15 技能＋死亡 GA、State／BTS／BT／Definition，两阶段 50% 切换；关闭 Q01 | 19 个目标包磁盘上都没有 | 跑 `wire_kevin_boss_abilities.py`／`wire_bh3_kevin_combat.py` | 同上 |
| I18（依赖 I17） | Kevin（四）：`L_KevinBoss_P3` 可交战装配 | 场景脚本和导航 Agent 配置已写，地图没保存 | 跑 `configure_kevin_boss_p3.py`，只保存 P3 | 同上 |
| I19（依赖 I18） | Kevin（五）：真实 RHI 打一场完整战斗到 Boss 死亡 | 没有任何运行证据 | 实战录关键帧和声音事件 | 同上 |
| I20 | 最小联机（一）：双端起步、预测被拒后的纠正重放、只按攻击自然结束 | 双端从没跑通（上次客户端提交内存不足）。旧实测双端约需物理 14.8 GiB、提交 24.1 GiB，当前空闲约 15.5 GiB | 关掉其它我方 UE，先测内存再起双端。**第一个独立验收点**：纠正重放和只按攻击两个试次的日志；内存确实不够时标阻塞并写实测数字 | [minimal_multiplayer](../需求文档/minimal_multiplayer.md) |
| I21（依赖 I20） | 最小联机（二）：特效晚加入、闭窗后加入、重获相关性 | 只见过同一键的最终状态，没见过画面 | 在 I20 的双端环境里依次跑三个试次，截客户端视口 | 同上 |
| I22 | 消息路由父 Tag 失效监听清理；SyncMarker 工具迁到 GGYGOEditor | 两处都确认未修 | `GameplayMessageSubsystem.cpp` 第 100 行改成用当前遍历的 Tag 删除，加回归测试；SyncMarker 先查 BP／资产引用再迁并加 CoreRedirects | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「当前状态」 |
| I23（依赖 I22） | CR-R7 剩余候选逐项核对，小缺陷直接修，优化交用户 | 台账候选未逐项核；新登记 CR-1111-D1（`NestedSameSpecRawTry` 诊断失败，日志 `Saved/Kiro/requirements-closeout/I08/Diag_R1/Editor/editor.log`） | 按[修复清单](Module_Audit_Repair_Ledger.md)出候选状态表 | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md) |
| I24 | 死亡结束后的 Pawn 去留改由共享角色蓝图决定（用户选 B） | `AGGYGOCharacterBase::OnDeathFinished` 仍固定下一帧 `UninitAndDestroy` | C++ 保留死亡结束广播、下一帧时序和权限检查，把去留交给蓝图；生产蓝图配成等价的下一帧销毁，未配置时报错。销毁必须晚于自动替补所在的那次广播。回归 SquadSwitch 8 例和联机死亡自动换人 | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「当前状态」 |
| I27（依赖 I04 的用户回答） | 去掉 ZZZ 动画兼容层，改为项目自己的角色动画实例 | 见下节 | 先只读读回 ABP_Pyrios 的实际消费面 | 本文「去掉 ZZZ 动画兼容层」 |
| I26（依赖 I08、I10、I20、I21） | 各 spec 的 tasks.md 勾选状态回写 | 多个检查点未回写 | 等依赖完成后统一回写，同步整改记录的状态表 | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md) |

### 去掉 ZZZ 动画兼容层

- 现状：`Source/GGYGO/Animation/zzzAnim` 共 15 个文件，`UZZZAnimInstance`（继承 `UGGYGOAnimInstanceBase`）是 `ABP_Pyrios` 的父类。每帧链路是：基类发布的 AnimationStateFrame → 旧快照适配器转成 `FZZZAnimSnapshot` → `FZZZLocomotionEvents` 写进 `FZZZAnimStateMemory`（GaitBlendY、StopValue 整数）→ AnimGraph 读取。头文件自己写明 `AnimBlendX/Y`、`AnimCurveVelocity*`、`ActualVelocity*`、`bTurnBackRunOut` 没有 AnimGraph 节点消费。`ABP_Kevin_DemonBattle` 不继承它。
- 做法：
  1. 只读读回 ABP_Pyrios 的实际消费面（过渡、状态图、StopValue／GaitBlendY／`GetSeqByKey`／侧倾属性）。
  2. 新建项目命名的角色动画实例，让 ABP 直接读 AnimationStateFrame 的走跑混合和停止类型；删掉旧快照适配器、LocomotionEvents、StateMemory 和无消费属性。
  3. 用 CoreRedirects 改名，只重绑 ABP_Pyrios 这一个共享资产，编译保存。
  4. 更新 `GGYGOAnimationLifecycleTest`、`StateFrameTest`，回归走跑、起停、TurnBack 和侧倾，复用 `Saved/Kiro/requirements-closeout/I04/prod_camera_run.py` 的生产机位场景，读数和 I04 对比。
- 不动：注释里说明源资产来自 ZZZ 的部分，以及编辑器控制台命令名。
- 验收：zzzAnim 目录删除；ABP 编译无警告；测试通过；生产机位读数与 I04 一致。用户偏好里"ZZZ 动画层 spec 使用 zzz- 前缀"这条若不再适用，交付时提示用户。
- 若用户对起停跳变选了 B，修复会改 ABP_Pyrios 的过渡，和本项写同一个共享资产，两项要排先后或由同一负责人做。

## 没有提交的文件

本批只提交了规则文档整理、过时文档删除，以及有本批验证证据的源码、资产、脚本和文档。下面这些仍在工作树里，**不要删除**；负责对应需求的人验证后自己提交。归属是收尾时读 diff 和修改时间判断的，没有作者登记，拿不准就先问用户。

注意：已提交的 HEAD 快照没有单独编译过，本批的编译和测试针对的是完整工作树（含下列未提交改动）。不要只拿 HEAD 去构建或判断回归。

### 父仓 `F:/ue_project/GGYGO`

- **用户的改动，不得删除或提交**：`AAADocs/Modules/CombatActions/Module_Repair_04_Subleases.md`（4 行 Combo／FX 内容）。
- **Kevin Boss**（源码已编译，包没做，没有运行证据）：
  - `Config/DefaultEngine.ini`（KevinBoss 导航 Agent）、`Config/DefaultGame.ini`（Kevin Cue 路径）、`Config/Tags/BH3_Kevin_AudioTags.ini`、`Config/Tags/KevinBossAnimationTags.ini`、`Config/Tags/KevinBossTags.ini`；
  - `AAADocs/Assets/BH3/KevinDemonBattle/` 下 `BH3_Kevin_Combat_Action_Manifest.json`、`BH3_Kevin_Combat_Montage_Config.json`、`BH3_Kevin_Combat_Wiring_Config.json`（修改）和 `BH3_Kevin_Ability_Config.json`、`BH3_Kevin_Audio_Config.json`、`BH3_Kevin_FX_Config.json`、`BH3_Kevin_P3_Scene_Config.json`（新增）；
  - `AAADocs/Scripts/` 下 `audit_kevin_action_motion.py`、`wire_bh3_kevin_combat.py`（修改）和 `audit_kevin_skill_poses.py`、`build_bh3_kevin_audio.py`、`build_bh3_kevin_fx.py`、`build_kevin_skill_animation.py`、`configure_kevin_boss_p3.py`、`plan_bh3_kevin_audio.py`、`wire_kevin_boss_abilities.py`（新增）；
  - `Source/GGYGOEditor/Private/KevinCombatAssetBuilder.cpp`、`KevinMotionAssetBuilder.cpp`（修改），`KevinBossAnimBlueprintAuthor.h/.cpp`、`GGYGOBossAbilityGraphLibrary.cpp`、`GGYGOBossCombatAssetLibrary.cpp`、`Public/GGYGOBossAbilityGraphLibrary.h`、`Public/GGYGOBossCombatAssetLibrary.h`（新增）；
  - `Source/GGYGORendering/Niagara/GGYGOProjectedDecalRendererProperties.h/.cpp`：新增 Kevin 特效制作用的材质实例资源读回接口，.cpp 里还混有投影贴花渲染器初始化的改动。
- **最小联机**（无联机运行证据）：`Source/GGYGOEditor/Private/GGYGOPlayerActionObservation.cpp`、`Public/GGYGOPlayerActionObservation.h`（特效晚加入观察入口）。
- **投影贴花渲染器**（Normal02 同帧投影修正，早期批次，本批没有单独验收）：`Source/GGYGORendering/Niagara/GGYGOProjectedDecalRenderer.h/.cpp`。
- **早期特效／材质批次**（10-24～11-02，本批没有验证，归特效与音效接线盘点）：
  - `AAADocs/Scripts/` 下修改的 `build_nap_avatar_simple_materials.py`、`build_pyrios_ghost_fx.py`、`build_pyrios_materials.py`、`capture_pyrios_fx.py`、`capture_pyrios_toon.py`、`gen_nap_avatar_hlsl.py`、`nap_avatar_simple_material_plan.py`、`nap_avatar_toon.hlsl`、`nap_avatar_toon_inputs.json`、`pyrios_material_plan.py`、`verify_pyrios_renderer.py`、`wire_pyrios_locomotion_pose.py`、`wire_pyrios_normal01_fx_window.py`、`wire_pyrios_skill_actions.py`、`zzz_fx_asset_session.py`、`zzz_fx_build.py`、`zzz_fx_import_assets.py`、`zzz_fx_material.py`、`zzz_fx_material_ue.py`、`zzz_fx_native_shader.py`、`zzz_fx_niagara.py`、`zzz_fx_niagara_ue.py`、`zzz_fx_particle_motion.py`、`zzz_fx_particle_renderer.py`、`zzz_fx_particle_uv.py`、`zzz_mesh_fbx.py`；
  - `AAADocs/Scripts/` 下新增的 `build_projected_fx_materials.py`、`configure_ggygo_level_key_light.py`、`gen_nap_avatar_simple_hlsl.py`、`gen_projected_fx_hlsl.py`、`nap_avatar_simple_programs.json`、`projected_fx_material_plan.py`、`projected_fx_programs.json`、`wire_pyrios_runtime_key_light.py`、`tests/test_zzz_fx_transform_chain.py`，以及 `RenderingOverlay/` 整个目录（17 个文件，引擎／UBT 覆层稿）；
  - `AAADocs/Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json`（修改）、`Pyrios_ProjectedFX_Rendering.json`、`Pyrios_Simple_Rendering.json`（新增）；
  - `AAADocs/Assets/Pyrios/FX/Converted/` 下 13 个新增 FBX。
- **归属不明的资产**（11-04 之前就被改过、一直没提交；本批运行用到了它们，但没核对改了什么）：`Content/BP/Anim/ABP_Pyrios.uasset`、`Content/Characters/Player/Pyrios/Abilities/GA_Pyrios_Attack_Combo.uasset`、`Content/Characters/Player/Pyrios/Animation/Attack/AM_Pyrios_Attack_Normal_01.uasset`、`AM_Pyrios_Attack_Normal_02.uasset`、`AM_Pyrios_Attack_Normal_03.uasset`、`Content/Map/L_Movement_Test.umap`、`Content/Map/Untitled.umap`、`Content/AI/Boss/Test/BB_Boss_Test.uasset`、`BT_Boss_Test.uasset`，以及新增的 `DA_AbilitySet_Diagnostic_TargetVitals.uasset`、`DA_Boss_Diagnostic_TargetVitals.uasset`、`DA_Pawn_Diagnostic_TargetVitals.uasset`（普攻第三段音效取证用它们当诊断目标）。
- **与本批无关的他人改动**：`AAADocs/Scripts/anim_rootmotion_extract.py`（11-10 被别人改过）、`.codex/config.toml`（Codex 工具配置）。
- **本机工作文件**：`.agents/tasks/requirements-closeout/` 下的清单、证据、脚本和报告，不入库。
- `Source/GGYGO` 显示为已修改，是因为子仓工作树还有下面的未提交改动；子仓指针已提交到本批的子仓提交。

### 子仓 `F:/ue_project/GGYGO/Source/GGYGO`

- **Kevin Boss**：`AI/Boss/` 下 12 个修改文件（`Abilities/GGYGOBossMeleeAbility.h/.cpp`、`GGYGOBossAIController.h/.cpp`、`GGYGOBossCharacter.h/.cpp`、`GGYGOBossDefinition.h/.cpp`、`GGYGOBossEncounter.cpp`、`GGYGOBossState.h/.cpp`、`Tests/GGYGOBossMeleeEndReentryTest.cpp`）和 11 个新增文件（`Abilities/GGYGOBossAbilityAssetConfiguration.h/.cpp`、`GGYGOBossAttackAbility.h/.cpp`、`GGYGOBossAudioActor.h/.cpp`、`GGYGOBossDeathAbility.h/.cpp`、`GGYGOBossProjectile.h/.cpp`、`Tests/GGYGOBossCombatDecisionTest.cpp`）；`Combat/HitDetection/GGYGOCombatHitQuery.h/.cpp`、`Combat/Tests/GGYGOCombatHitQueryTest.cpp`；`Character/Components/GGYGOCharacterMovementComponent.h` 和 `.cpp` 里的飞行模式借用部分（同一个 .cpp 里再附身移动的 owner-sync 修正已提交）。
- **Kevin 与最小联机混在一起**：`Character/Components/GGYGOActionCurveRootMotionSource.h/.cpp`、`GGYGOActionMotionExecution.cpp`（飞行模式下允许动作位移、自然混出末段判定、根运动源跨取消状态匹配）。
- **最小联机**：`AbilitySystem/Abilities/GGYGOGameplayAbility.cpp`、`GGYGOPlayerComboAbility.cpp`、`AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.h/.cpp`、`GGYGOAbilityTask_WaitComboInput.cpp`、`FX/Components/GGYGOMontageFXReplicationComponent.h/.cpp`、`FX/GGYGOMontageFXPublication.h/.cpp`。

### Obsidian 仓 `F:/Obsidian/Doc/lyra学习笔记`

- `GGYGO架构规划/AbilitySystem/` 下 `结构.md`、`GGYGO_结构_AbilitySystem.canvas`、`GGYGO_结构_玩家普攻连段.canvas`、`GGYGO_流程_AbilitySystem.canvas`：11-09 被别人改写过措辞，没核对，没提交。
