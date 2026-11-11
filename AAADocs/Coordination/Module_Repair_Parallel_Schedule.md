> 已由 [Board.md](Board.md) 取代，仅作历史参考。

# 全模块修复：当前任务与共享排程

更新：2026-11-02。本页是唯一项目排程，兼原 RHI 批活动记录；独立新增需求只索引其唯一记录，维护当前写入者、依赖与共享窗口。原作者见[路由](Module_Conversation_Routing.md)，稳定规则见[AGENTS.md](../../AGENTS.md)。

## 当前窗口与关键路径

11-09 真人明确先完成约定批次的全部开发和生产接线，再集中编译与验证。独立模块复用原会话并行，开发期间只开必要制作窗口，修复后只复验受影响范围。回执只报结果、真实阻塞和必要决定，无关哈希无需生成、核对或汇报。

B06／B08 生产蓝图已保存，[集中构建](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/Build_Integrated_R2/return.json)通过。[集中真实 RHI](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Integrated_R1/return.json) 5／5，正常退出并归还保护。同进程 InputConsumer 后联机 PIE 正常起退，生产 GameMode／PlayerState、客户端改换人键、再附身后双端各移动 658.8 cm、死亡自动换人通过。原 B06 设置页面改键／持久化未覆盖。倒下者入画，阴影仍有放射条纹；Normal01 生产首击断言通过，主弧实拍与活尾仍待。姿态 R2 启动前取消，[首次构建失败](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/Build_Integrated_R1/return.json)和原运行失败保留。

R6 共用 Cold 已通过 N3 十六包与 Normal03 三引用读回，Editor、保护与 Trace 正常归还。R6 Normal03 因未取得前台焦点，尚未进入播放或录音，原失败及两个观察子进程 exit 1 均保留。原 Audio 已交回[后台引擎声部／Master 入口](../../Saved/Codex/AudioRestoration_20261022_A1/NormalComboAudio_R1/Runtime_20261109_Normal03Engine_R1/README.md)，原生生产输入链与声音断言继续使用，实体播放和听感另待实际前台。该入口离线核验通过，当前绑定 R6；本轮源码批次冻结并完成构建后，再统一更新同版绑定及运行。当前余约 136 MiB。[Cold 回执](../../Saved/Codex/FXProduction_20261026_R1/ColdRead_20261102_R1/Run_R6_Integrated_N3Audio/return.json) [声音回执](../../Saved/Codex/AudioRestoration_20261022_A1/NormalComboAudio_R1/Runtime_20261109_Normal03Voice_R6/return.json) [已结束窗口及失败](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-r6-预热与声音前台窗归还)。

旧版软件绑定失败和关闭证据见[历史](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-b06-续窗旧阶段归还)。[R3 实际运行](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/B06_Integrated_Acceptance/SlateResume_R3/return.json)通过 R5 保护和启动，Windows 未给原 Editor 真实前台，等候到期后正常退出并归还。仍无页面、改键、读盘或恢复默认结果。

[双档姿态 R5](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_LeanTargets_R5/return.json)在 R4 软件及同版 ABP Cold 上通过 2／2，两次自然帧侧倾读数约 19.49°、44.06°。原诊断机位两张实拍已看，腿脚完整入画；生产机位的连续画面、GPU 精确同姿态、实体设备与联机仍未覆盖。姿态 gzip 保原采样，Editor 正常退出，保护、Trace 和缓存归还。[20° 图](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_LeanTargets_R5/WalkRunLean20/Draw_0002.png) [60° 图](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_LeanTargets_R5/WalkRunLean60/Draw_0002.png)。[R4 未进入 PIE 的失败](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_LeanTargets_R4/return.json)保留。该窗结算余约 61 MiB，当前余额见 R5 构建闭窗。

本批已批总额 6274002896 B。11-09 真人再次追加 128 MiB，用于 Normal01 集中构建、材质编译及实拍和 N3 共用 Cold、Normal03 音效。沿原 R1 基线和预留，双端按原内存门准入。[P3 Cold R2 失败与归还](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-p3-cold-r2-失败归还)。

Normal01 R6 诊断预热后用例 1／1、exit 0，保护归还。三原 Niagara Mesh VF map 已完整；实拍仍未确认参考主弧。首样为生成后约 9.7 ms，源参数和材质转换未发现直接错误，需采自然寿命内少量同帧画面定位。生产冷首击仍缺实际资源就绪接线。[R6 回执](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Normal01_RTMaterial_R6/return.json) [原实拍](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Normal01_RTMaterial_R6/Editor/Saved/FXCaptures/normal01__normal01_production_viewport.png) [R3～R6 原过程与失败](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-r6-预热与声音前台窗归还)。

### 本轮开发与接线批次

原 FX 牵头完成 Normal01 表现定位所需的自然相位采样和生产冷首击资源准备，Rendering、Character、Input、AbilitySystem 直接收敛实际接口。仅修已确认的材质未就绪和已证缺失的观察，具体资源选择及业务流程放共享 BP／资产，通用异步机制沿原生命周期。各作者完整实现、自审后冻结，Root 合并构建，再做必要资产制作与集中验证。

| 原作者 | 本轮独占范围与交付 |
| --- | --- |
| Rendering | NiagaraMaterialPreparation.h/.cpp、NiagaraMaterialBindings.h/.cpp 与原 MeshDrawTestProbe 两文件已自审冻结。实际 Renderer／最终材质、原平台资源与 RT 读回决定 Ready；原编译通知推进，取消与 World 退出归还，三相位观察保原 Family。无引擎改动，待集中构建与实拍。 |
| AbilitySystem | GGYGOPlayerComboLifecycleTest.cpp 已自审冻结。最多三份自然相位样本，保原实例与断言，补 RGBA、DP0～2 及匹配 Draw；首次真实按下前等待生产资源就绪，非消费输入观察保留。待集中编译及运行。 |
| Character | HeroComponent.cpp、PawnExtensionComponent.h/.cpp、PawnData.h 及 wire_pawn_input_resource_preparation.py 已自审冻结。Pawn 持有原 Rendering 请求；首沿锁存后按配置 Tag 准入，Pending 不补发 held。制作／读回入口已交 System，BP 与 PawnData 二包尚待集中制作。 |
| Input | 只读契约已与 Character 核收，无需 Controller／Input 写入。资源门置于 Hero 首沿锁存后、ASC Receive 前，Ready 不重放旧按下，原释放与退役语义继续保留。 |
| FX | 四份 Task／NiagaraComponent 源码与 capture_pyrios_normal01_phases.py、prepare_pyrios_normal01_resources.py 已自审冻结。组件最终材质安装后、原 Super::Activate 前等待准备，原取消／退役摘请求；具体资源取生产配置。待合批验证。 |
| Audio | 新 Normal03 引擎取证目录，完成原生产三击及声部／Master 后台入口，原前台视听结果另验。 |
| System | 原 N3 Reader 两处绑定已修复并冻结。独占新增 Build_Integrated_R7、BlueprintAuthoring_R7 与 System/Integrated_R7 的集中构建、两包制作、真实发布及后继绑定准备，先消费各作者接口，源码冻结前不固定最终身份。制作窗复用原 BlueprintAuthoringReturn，只开放 BP_PC_Pyrios 与 DA_Pawn_Pyrios；Root 运行后才能生成对应真实发布／Cold 绑定。 |

[R9 集中构建](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/Build_Integrated_R9/return.json)及[两包制作 R9](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/BlueprintAuthoring_R9/return.json)已通过，原蓝图流程与配置读回正常。[同版 Cold R7](../../Saved/Codex/FXProduction_20261026_R1/ColdRead_20261102_R1/Run_R7_Integrated_N3Audio/return.json)通过十六包、新二包接线及三音频引用，exit 0、1579 保护及 Trace 归还。根内峰值 4648991844 B，域外保守累计 1495241105 B，扣原预留约余 82.76 MiB。Root 已启动 Integrated_R7/Normal01 单叶三相位实拍窗，源码及其完整父输入冻结。System 同时仅写 audio_base.py、Audio/prepare.py 与 Audio 下七份待生成运行文件，修旧 Reader 绑定并实际完成准备/PreflightOnly；Root 已核这9路径与 Normal01 完整父交集为0。音效尚未运行、画面未核，Git 未交付。[原构建和制作失败](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-r7至r9构建与r8制作失败)保留；Cold 首次准入漏原读回依赖已修，Audio 首次准备旧 Reader 身份失败亦保留。

### 2026-11-05 蓝图分层全项目审查（用户指定独立会话）

复审结论见 [Blueprint_Layering_Audit.md](Blueprint_Layering_Audit.md)。B06／B08 源码与生产接线均已落盘。B06 的两份 WBP 和生产 BP_PlayerController 已保存读回，保原 IMC，页面运行待验。B08 的生产 BP_PlayerState 同栈用原 Slot／Avatar 请求替补，BP_GameMode 使用新 PlayerState。出战死亡的生产联机链、后台死亡和无存活候选的原机制断言均通过。五包已清洁交还，[共同制作窗](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/BlueprintAuthoring_R1/return.json)正常退出并归还保护。B08 两包后像与回执一致，BP_GameMode 前像等于父仓 HEAD，BP_PlayerState 是新包；Teams 联机测试含同批其他改动，统一交付时按验证范围选入。其余七项无需强制迁移，B04 源码旧命中已消除；Q01～Q05 待约定的生产图或运行证据。

### 2026-11-05 Kevin Boss 完整组装（新增并行）

用户追加完整技能／动画／特效／音效组装，FX 允许参考适配或自由创作。唯一需求与验收记录：[KVB-20261105-01](../需求文档/kevin_boss_assembly.md)。原 BossAI 牵头，原 Combat GA／命中查询、Animation 资产、资源解包、FX、Audio 按该记录独占写集并行；先消费现有 159 包和真实动作，不复制现有 239MB 素材或全库解包。R53_FXLive_R4 原窗已资源门失败、正常退出并核归还（995 父，ADBD914C），不盲重试；Boss 专属离线源码／脚本／文档与完整父求交零差才可写；共享 ASC／CMC／Rendering 仍冻结。Root 已按实测资源划出全组共用 32MiB 离线制作子额；不得各自构建、加载新 DLL 或另起 UE，由 Root 安排必要资产制作，整批配置完集中验证。不恢复玩家 E／R／F 或其他延期玩法。

Kevin 已保存并保留 55 个声音包与 8 个材质包，余 134 个包尚待制作。上一制作窗已正常退出并归还保护，原 FX 的 MI 比较修正及 Cold 等待入口已交回冻结；下一窗需绑定届时实际发布。26 份派生动画源约 82.5 MiB，制作与缓存增量仍需计入本批，原已提出的 256 MiB 追加待确认。完整制作、战斗／视听／联机及交付仍未验收。具体写集、配置与验收只维护在 [Kevin 唯一需求记录](../需求文档/kevin_boss_assembly.md)。[已结束准备过程](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-kevin-制作前置归并)。

### 2026-11-04 真实 RHI 后续修复（当前有效）

Slot 对照已验收为生产 A 保留普通 `ActionPoseSlot`，Mesh 不迁移。N3 当前生产源码与原宿主均冻结；本轮仅重绑后续受影响实际复验。既定最小联机待验四项：原预测被拒后的 Mode2 原 basis 纠正重放与新段；活窗远端首次获相关性须见实际 FX 画面；闭窗首次加入须核完整复制快照且同键未创建；重获须证同连接原 ActorChannel 退出、新 Proxy 与剩余 FX。原 R6 预算拒绝未起 UE，四项无运行通过回执。

N3 [R6 绑定](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/Build_Integrated_R6/n3_software_binding_R6.json)已消费顶部真实同版 Cold，原 Reader 软件和冷载实际通过。System 已核新旧 Reader 契约，仅修原 entry pin 的两处 Reader 绑定；原入口与准备器离线通过，真实联机仍未运行。旧 R4 绑定保留。沿原双端 D3D12、生产图及 SDK／Trace／Remote 保护，先空 Editor World，再串行加载地图，B→A 开试次。逐端启动门为物理 11 GiB／提交 19 GiB，开试 6 GiB／12 GiB，运行 4 GiB／8 GiB。R59 起 A 后 B 提交余量不足，A 正常退出并归还；生产地图及四项均未运行。按该窗实测，双端起步宜有物理约 14.77 GiB、提交约 24.11 GiB。R6 音效归还后实测物理约 14.01 GiB、提交约 20.59 GiB，未重启双端。[R59 失败与归还](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-n3-r59-双端资源门未通过归还)。

本批总额、原 R1 基线与预留保持，余量按顶部末次归还和开窗现盘为准；P8 旧域外缺项仍冻结。N3 R54 同键终态已见，实际可见 FX 待证。每端 Pose 8 MiB，玩家 E／R／F 延期。[原 N3 R58 归还](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-n3-r58-同版-cold-归还)。

用户 11-05 要求由原 Kiro 核剩余优化并出 spec，本统筹接续执行。原任务 52150292 已完成，只交方案。N0/N1/N5 落 [激活生命周期](../../.kiro/specs/abilitysystem-activation-lifecycle/tasks.md)，N2～N4 落 [FX 发布](../../.kiro/specs/fx-montage-publication-ownership/tasks.md)，单机 V1～V4 落 [输入](../../.kiro/specs/abilitysystem-input-request/tasks.md)，V5 落 [换人](../../.kiro/specs/teams-squad-switch-linger/tasks.md)。V6 继续保引擎失败原证；D 残余按 [CR-R7](Module_Audit_Repair_Ledger.md#cr-20261014-r7) 核写集，G 按实证差分交付。

V4 已按 Build_R53 核收生产菜单改键／读盘／恢复默认及跨菜单 held barrier，[V4i](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_KeySettings_V4i/return.json)／[V4h](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_KeySettings_V4h/return.json) 均正常退出并归还保护。实体设备、外部失焦与设备断连仍待验；Input 三源及 GGYGO.Build.cs 保持冻结，B06 迁移后复用这些场景。用户已授权在批准总额内按实测物理内存划分验证子额。[已结束过程](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-05-v4-改键验证过程)。

用户已将本批验证额度再追加 1GiB（1073741824B），总额 3489660928B。原 R1 基线和 42987054B 预留保持，此前 4MiB 方案已取代。`RHI_R41` 复用 Build_R41 单跑 NewPress，1 例失败：未触及 Stage 9 新时限，原 Normal01（实例 0）等待取消期间出现 AttackRequest=1，生产 GA 进入 Normal02（实例 1），原播放身份失配；尚未发 W。实证同一 PlayerInput 会话首击 EdgeEvaluation=1，续段 EdgeEvaluation=60，排除首击同边沿重放；缺原视口松键／Action 事件，来源未定。全局退出仍触发原 VT 断言、exit 3，5837 保护归还。根内 2281628515B、域外保守累计 75405769B，余 1089639590B。

AbilitySystem 仅 `GGYGOPlayerComboLifecycleTest.cpp`（295313B／5C0A592C → 300831B／C5FFFEF6）透传取证已静态自审冻结。NewPress 原叶记录夹具提交、原视口键事件、原 Attack Action Triggered／Completed／Canceled，按原身份及帧对齐，不拦输入、不改生产逻辑或验收断言。Build_R42 exit 0、保护归还。`RHI_R42` 单例 1／1、0 Error、编辑器 exit 0、5837 保护归还；Normal01／02／03 均在各自原 End 窗内由新 W 取消并恢复资源。R41 的额外攻击未复现，根因仍未知，不据此改 Input 或签掉 VT 原失败。根内 2286657154B、域外保守累计 75784593B，扣原预留后余 1084232127B。无共享宿主在途，源码／资产／引擎／Git 冻结；改键菜单的打开与画面见上方 R42b，实际改键及持久化未重测；预测纠正重放、FX 晚加入、地面阴影和活尾覆盖仍分别待证。

阶段已核收：Normal01 真实 RHI 单叶通过且同原实例采三图，三探针均早自然退休，活尾仍未覆盖；Normal02 同帧投影旧错误在两原叶均未再现，Interruption 通过，NewPress 最终按上方 R42 核收。两 PoseFailure 真实清理及后继激活断言通过，Automation 仍因注入故障的原生 Error 为 Fail，保留原结果；VirtualTexture 全局退出断言仍未结案。中间构建／失败、额度变化及图像身份已迁[过程历史](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-04-r39-至-r41-首击和投影验证过程)。

用户已将 Kiro 交回的待修项与剩余验收交由本统筹推进。Kiro 已完成七项整改、接线和阶段推送，最后活动记录提交 `01d5948`，实际任务已结束。R35c／R35d 原进程退出，分别归还 5836 个保护句柄，保护通过。详细现象、已确定玩法、失败及原图见[原活动条目「收尾续二」](../需求文档/refactor_and_squad_switch.md#收尾续二用户-11-04-决定kiro-恢复写权后落实)。[原执行阶段授权与写窗](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-03-kiro-执行阶段交接历史)随已交回过程保留。

Build_R36 单动作构建 exit 6，`GGYGODistortionFieldComponent.cpp` 调用 protected ShaderMap getter 报 C2248，保护已归还。Rendering 改用公开接口并重新冻结，Build_R37 编译成功、保护通过。R37 根内末次 2221554609B，原域外 199209627B 逐路径核对后，扣除 R36 失败时由 UBT 移除且 R37 同路径重建的两份既有 PDB 原体量 198361088B，实际新增计 848539B，R36 域外 9778B 另计。沿原 R1、总额 2382364672B 和预留继续集中验证，源码冻结。相关验证覆盖冷启动生产首击与 FX、客户端再附身移动、含测试夹具的 PIE 正常退出、倒下取景与阴影、改键界面及可复现的预测纠正和 FX 晚加入。资产保存、引擎和 Git 窗仍关闭。

| 原作者 | 本轮任务与独占写集 |
| --- | --- |
| Movement | 修再次附身 owner-sync 拒绝及 InputConsumer 夹具世界泄漏。仅 CMC 及其移动所有权相关实现、`GGYGOLocomotionMovementTest*` 必要测试夹具；共享 Animation 绑定只读。 |
| FX（冷启动牵头） | 冷启动真实材质与 Niagara 就绪、取消及失败传播。仅 `Source/GGYGO/FX` 受影响运行链；Rendering 提供其所有的就绪事实，涉及 GA 仅确认接口与交回差异。 |
| Rendering | 四源已静态自审冻结：`Source/GGYGORendering` 的 `GGYGOCharacterShadowCapture.*` 与 `GGYGODistortionFieldComponent.*`。同步归还 Capture／RT 引用，FX 消费 `PrepareMaterialFieldRole` 的真实 Pending／Ready／失败；Build_R37 已编译，R38 未再现 SceneCapture 世界泄漏。原图对照中，[R38 倒下帧](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_R38/Captures/05_member1_dying.png)已拍到角色，但地面仍见放射条纹；[R38 换人帧](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_R38/Captures/06_member2_after_death_switch.png)有明显拖影，不能判断换人稳定后阴影。后续用同客户端换人稳定帧与同帧投影证据区分来源。前像和差分见 `Saved/Kiro/abilitysystem-redundancy-cleanup/Before/Rendering_R35_20261104`。 |
| Input（清理牵头） | 按实际 LocalPlayer 生命周期释放 IMC；仅 `Source/GGYGO/Input` 及 `Player/GGYGOPlayerController.*` 中映射所有权路径。追加 `Player/GGYGOLocalPlayer.h/.cpp` 的 PlayerRemoved 退役契约，保留既有输入来源退役顺序。接 Movement 证据，修普通退役错误重立已有可信中立的释放门槛，保持 Flush／无证明／按住跨界的真实释放要求。与 Character 收敛，不写 Hero；Pyrios 旧脚本确实拒绝当前正式 IMC_Default（期望 5152A4C5，实测 41C034BA）；还要求原 15 映射且 E／R／F 为空。P2 的 18 映射回执来自 CS 副本，不能作当前正式包读回。后续先由原作者对照正式映射及改键设置，再决定基线；本次只读，E／R／F 继续延期。 |
| Character | `GGYGOHeroComponent.cpp` 退役订阅与原会话 IMC 归还已冻结，前像 CFAB0948、现态 59343FCF。与 Input 的正式 LocalPlayer 退役入口一并复验，尚未编译。 |
| Camera | 已对照 R35d 原图与调用链，空差分冻结。05 缺少截图同帧客户端 Dying、Pawn、ViewTarget 与实际 POV，集中复验补自然 Draw 同帧证据后再判断是 Camera 缺陷还是镜头玩法取舍。 |
| Teams | 仅 `Teams/Tests/GGYGOSquadSwitchTest.cpp` 现有联机复现补再附身后真实 W 位移断言、倒下截图同帧证据和原场景清理。保持生产玩法、资产和已有断言。 |
| AbilitySystem | 仅 `AbilitySystem/Tests/GGYGOPlayerComboLifecycleTest.cpp` 既有生产冒烟入口及 FXReady 等待证据。保留原失败断言，区分冷首击实际输入与 Niagara 在发输入前未就绪；不改 GA 或替换生产路径。 |

集中复验已消费 Build_R37。`Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_R36a` 冷首击发键并启动 GA，生产普通 Objects MI 在双场实例的全材质校验被误要求完整 field ShaderMap，测试失败。`RHI_R36b` NativeBirth 与两个 InputConsumer 均通过，同宿主成功进入联机 PIE，再附身 W 位移服务端／客户端均 641.3 cm；联机叶记录三条同因 FX Error，测试失败。原 SceneCapture PIE 世界泄漏未复现，仍有 IMC_Default／IMC_MouseLook 告警，IMC_Squad 告警本轮未出现。05 客户端实际 Dying、Pawn 与 ViewTarget 同一角色且入画，地面条纹仍可见。两窗测试后退出重现 VirtualTexture 引擎断言，exit 3，保护均通过且已归还。

后继窄修仅开放 FX 的 `GGYGOFXNiagaraComponent.cpp` 实际材质分流，以及 Input／Character 原互斥映射所有权写集处理剩余两条告警。Rendering 对 FX 契约和阴影只读，Movement／Teams／Camera／AbilitySystem 保持冻结。冻结交回后复用 Build_R37 执行路径，仅复验受影响场景；引擎不写，保留退出崩溃证据及其验收限制。

Input 已从正式 BP 编译字节码核证客户端额外两次注册。`Asset_R36` 因 Python 不公开 NodeGuid 在预检拒绝，未保存。`Asset_R36b` 只保存 `Content/BP/GamePlay/BP_PlayerController.uasset`（47316B／AAF2333F → 38597B／32CE2D99），编译 BS_UP_TO_DATE，图差分核同且 CDO 改键清单与 IMC_Squad 保持，原 UE 正常退并归还 5837 保护。FX 和 Input／Character 窄修已冻结，Build_R38 通过且保护归还。

`RHI_R38` 6／11：联机换人整例通过，旧 Pawn 再附身双端位移各 674.4 cm，三条原 IMC 告警与 SceneCapture 世界泄漏未复现；NativeBirth、两个 InputConsumer、两项 Held 冒烟通过。旧 Objects MI ShaderMap 拒绝已消失。仍失败五例：Normal02 两例同帧投影 payload 缺失；Normal01 原粒子／End 尾证据不足；两例 PoseFailure 的精确失败及清理证明未过。合跑中观察脚本先绑定前一个 PIE World 而失效，Normal01 画面尚未获取；下次仅该叶使用此观察入口。所有用例已报告，编辑器全局退出仍触发原 VirtualTexture 断言（exit 3），5838 保护归还。点时根内 2246311542B、域外累计 73467217B，原总额扣除预留后余 19598859B。统筹已提出追加 32MiB，未授权前不开超出预算的复验窗。

R38 Normal02 已核项目投影 Renderer 工厂仅构造而遗漏 UE 原生 `Initialize`；该调用负责填充 `BaseMaterials_GT`，原同帧发布因此缺必要材质。Rendering 已恢复调用并由 FX 互审，唯一 `Source/GGYGORendering/Niagara/GGYGOProjectedDecalRendererProperties.cpp`（23054B／1DFBCE5B → 23180B／5EC1BAB0）已核收冻结，前像与差分在 `Saved/Kiro/abilitysystem-redundancy-cleanup/Before/Rendering_R38_20261104`，保留原同帧约束及真实失败，待集中编译和原两叶复验。Renderer 重建时序是否构成独立缺陷待运行证据。

AbilitySystem 已核 R38 两 PoseFailure 的合法 `Accepted` 回执在行尾为 `Outcome=0`，旧夹具漏认；Normal01 三次采到原粒子，缺原实例 End 和脱挂／Inactive，旧夹具遇退休提前退出。仅 `Source/GGYGO/AbilitySystem/Tests/GGYGOPlayerComboLifecycleTest.cpp`（286713B／5673C46D → 292135B／FFD049D9）静态自审并冻结，分别采原 GA 与 ASC 退役回执、自然结束／作者 End／脱挂及 Inactive；保留尾段断言和生产 Error，GA 未改。Normal02 与三例夹具已在 `Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/Build_R39` 一次增量构建通过，原进程 exit 0、保护已归还；根内 2246898484B、域外本窗 41115B，保守合计余 18899718B。按已提出的追加 32MiB 等用户决定后复验原五例，Normal01 单叶采图。已通过的移动／Input／Teams 不重复修。无构建／UE 在途，资产／引擎／Git 窗关闭。

已明确后做的进退场资产与暂停的 E／R／F 仍按原决定。公共死亡、全员倒下后的流程和引擎退出断言保持原证据，涉及玩法或引擎选择时单独处理。三个仓已推送的阶段历史保留，整体验收尚未关闭。

[R6真实容量失败／保护归还](../../Saved/Codex/TurnBackRepair_20261021_R1/N3Integration_20261023_R1/Data_R36_ComboFX_R6/root_guard_failure.json)3334B／926B99B5：原guard30448／出生134380853884427920原句柄exit1，首个Current为2263893735B＞2087830028B软线，gen1／pid未发布／未ready，未创建UE或执行B先standby计划；980父／Config／Trace零差。R5后段原姿态留证204216134B已实际写完；旧1770末代不能代表这些新增，R6正确拒绝，不重用旧Run／清闩锁。

[R78无损归档](../../Saved/Codex/FXProduction_20261026_R1/ClosedWindowSnapshots_20261102_R78/index.json)已完成：仅R5原姿态证据＋四份已闭窗Editor派生ShaderDebug共5件217045662B，压缩29726152B／26F0774D、索引4860B／32A2D1F5，逐件解码完整SHA核同后迁出原件，净减187314650B；完整1120父／物理交集0、前后父／Config／Trace零差。原R5失败／budget／pending／结果及当前Cold原件保持，历史原字节可恢复。没有新Current或UE；2GiB／原R1表／7根／资源门不变，归档不签下一窗容量通过。

当前Source全部冻结：guard21167B／B5822C43、entry21067B／657CBA28、control97D69934、launch2A0361BB、counter8A67868C。Source准备507112B＜512KiB、剩17176B；仅日志补故障后RM归属观测已静态核收，Native RM未执行，发布拒绝主体及R2首因仍未知，不称根因修复。[R5失败／986父归还](../../Saved/Codex/TurnBackRepair_20261021_R1/N3Integration_20261023_R1/Data_R36_ComboFX_R5/root_guard_failure.json)及[R77归档](../../Saved/Codex/FXProduction_20261026_R1/ClosedWindowSnapshots_20261102_R77/index.json)维持原证据；双端SDK／Native／缓存禁写曾通过，完整业务／视听／设备及联机仍未验，无新C++编译。

已过最小契约：[R107](../../Saved/Codex/FXProduction_20261026_R1/Production_R107/return.json)完整701 Native生产核验／原16保存；[R3 Cold](../../Saved/Codex/FXProduction_20261026_R1/ColdRead_20261102_R1/Run_R3/return.json)三GA／五Montage／14NS身份及材质／BP／两灯图读回通过，16当前后像831597B保持，原UE正常退出、保护归还。P3 reader F865CCE8／manifest F21B0466／provider pin2CB44D57的实际Cold消费已过；host D325211D仅修公有begin_release合法终态，ending／finished不重写，restoration_failed明确交Root恢复，原guard/control/launch其余接口保持。运行／画面／听感／设备／最小联机仍未验，Normal01线性作者失败仍仅诊断，不造ABP／seven资格。

P3本地画面入口仍旧R8／ABP Cold_R4并与P10全等绑定，原147记录16处漂移及P3/P10未完成边界保留，不以N3移签。完整需求未验收、不归档或停跟进。编译前仍先通知用户；本轮没有新编译。

Root统一构建、软件发布及集中验收，不代模块实现。当前FX B108642B／07412EC6、A44766B／9D688137、U274512B／EC08687F、P205577B／AAE8B5C5及原Leaf50501B／4DFA9A46冻结；Rendering四源及System／Character当前身份见下表。222 Master＋222 MI（含静态复用MI）按真实EditorWorld完成并严格核ShaderMap，原13字段／失败传播及field角色／证书／VF完整条件保留；原701目录、33成员、338层／6缓存及16包范围不扩。独立NS每单元≤32 emitter，原层顺序、实际跨层依赖及Normal03双失真路径保持，既有非确定性不改为固定seed或回放协议。用户要求编译前通知并复核当时余量；单动作／不复制工程或引擎，原2GiB基线保持。Runtime_R35／R105等旧软件和准入仅对应已闭窗，失败及源修正过程已迁[历史](Module_Repair_Parallel_Schedule_History_20261013.md)，不成为新的执行授权。

正常回执并集701包＝444材质／实例＋242导入＋1 Profile＋14个NS：Normal01／Normal02／Rush三小NS、Normal03七单元197层、Special两单元40层、ExSpecial两单元58层，总338 emitter保持。Native制作／核收已齐，原16包最终接线与R3持久Cold已过，后继只做必要集中运行验收；完整画面／原声时点／设备与最小联机仍未验。不重做成员准备或既存导入，源脚本／原作证据的未恢复边界保持。

当前Host91699B／A40C58ED与launch34889B／833F4DBB已冻结，Cold适配仅沿既有调用链，原Author／单ABP Cold分支保持；旧Host身份及各失败／修正见历史，不当作新窗当前pin。batch_readonly_sources的正常／失败原来源及原包族／Native核收规则保持。R5表达式及R14完整准备、原33成员计划／338层不重做，不扩R7广泛整改。

分批载荷使用business.fx_batch的dependencies／system／profile／integration，沿原P.load_saved_preparation→leaf._fx_inputs→B.asset_batch_catalog消费保存准备；只重绑五份当前authoring_changes.after，原R14正文、33成员、338层及原始前像不变。实际701目录＝400通用材质＋44原生recipe＋1 Profile＋14 NS＋242导入；Normal03为32×6＋5，Special为32＋8，ExSpecial为32＋26，原3小NS保持。不重跑成员producer或准备包，不重导已保留导入；早期恢复／制作过程见[正常来源R43](../../Saved/Codex/FXProduction_20261026_R1/Production_R43/return.json)及既有历史，不作为新的开窗授权。

Ribbon传输修复三源已完成并冻结：真实VP的同值原生payload承担5个标量，其余11／14／19标量紧凑传输；保留全部有效分量、原公式及插值语义，未改renderer／引擎。原TEXCOORD冲突见[R28历史](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-28-r28数值修复实跑通过与dxc错误归还)。R32已完成原失败7e42b566材质并保存；另外两份与全部动作、GPU画面仍未齐，不签整批Shader修复通过。

制作继续消费已核收的[R14保存准备](../../Saved/Codex/FXProduction_20261026_R1/Preparation_20261028_R14/return.json.gz)，六实际gzip消费者／33成员／338层保持。8项selector采用已定项目配置，原stage／MPB未证；原6件机器输入5026065B、历史累计34360854B及34MiB内部子限余1290730B保持。目标数按当前701独立单元目录，不重置原累计基线；已结束保护和执行过程只留原回执及历史。

真人FX新增总额为2GiB（2147483648B）；原R1累计基线、42987054B预留及34MiB准备子限不变。域外16666566B＝原15902111B＋八份源码正增17016B＋R31产物正增417792B＋Emitter修复正增1421B＋无VM诊断B/U及项目cpp/h正增4013B＋R32产物正增56320B＋R101 Rendering四源正增6053B＋FX B正增2412B＋R33产品正增77824B＋R102两cpp正增566B＋R34产品正增9728B＋本轮三源正增4642B＋R35产品正增81920B＋R104 helper源正增1141B＋WorldContext三源正增6807B＋R36产物正增76800B，当前执行根软线2087830028B；后继产物按实际继续并计；P正增179B及前像／patch在Saved根内计，不重复作域外。后继产物按实际正增计入，不以删除旧数据重置基线，到线停止、不自动扩额。最近[R75归档](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-02-cold生产合同修正核收与r75归档)只迁出已完整恢复归还Cold R2的frozen／dependencies及Editor／Before共53件10303543B；当前Cold实际准备父164路径／物理交集0，逐件解码核同后净减9975945B。R2失败Leaf／window／before／恢复归还与Trace、R107保存成果及108当前输入保原件；前序R73／R74按历史定位。原2GiB与累计基线不变，前一R67大失败读回迁出保留原字节／未知结论，详见历史，不代容量或需求验收。

R8／ABP B6AFA948 本地 TurnBack 两个数值叶通过，ABP 与现盘一致。Phase2 原自然帧 84→85：同一请求序列 6 的源秒 0.140907→0.170814，显示侧倾 0.104186°→0°；整段 82 个连续完成区间累计 −180.000153°，至源尾 2.383333s 自然完成。Retrigger 后继新序列独立跑满，旧句柄拒绝。R2 原走跑未覆盖、保护归还；对照图的同 GPU 姿态与实体设备仍待。[Phase2](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261026_R2/TurnBackPhase2/ProviderVerified.json) [Retrigger](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261026_R2/TurnBackRetrigger/ProviderVerified.json) [R2 外层回执](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261026_R2/return.json)。后继 [R3 镜头侧倾及走跑混合](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261026_R3/return.json)本地通过。R45 起停行为见下方当前证据；真实设备、生产镜头起停衔接、联机及完整技能视听仍待。[已结束 Cold／控制过程](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-26-完整cold-r4与已结束保护入口修正)按需读取，具体身份／当前写集只见下表。

当前唯一统筹为“GGYGO｜2026-10-12需求统筹”`01a1347b-ccee-7081-a783-0c3127b3dd48`，独占共享排程维护权。用户直接交需求，统筹协调原21组长并自主决定归档；不依赖 Dot。旧根已归档。本批需求与验收仍未完成。 原有ggygo跟进已按真人恢复目标同步为ACTIVE，仅携本页当前条目，健康在途保持安静，不另建排程维护者。

UE／工程整树复制路线已取消并清理；后继只用现有工程就地增量构建，按实际依赖保护，不继承无关旧工程／PCH缓存。[历史证据](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-22-整树复制取消与清理)按需查。

开发与派发节奏按[协作规则](../../AGENTS.md#决策与协作)和[验证规则](../../AGENTS.md#验证与交付)：围绕当前需求主线，尽量一次向组长派发完整批次，实现／配置齐备后统一编译、统一测试；审查与风险相称，不新增无依据的防御或逐段审批，不扩无关重构支线。移动／姿态、独立打断与三Normal音效已进入集中验证批次；完整FX／视觉线继续实现，未运行项如实保留。

音频项目接线政策：技能声在Main开始、命中声只在真实命中时播放，参数留Montage可调；Normal02／Normal03及Special／ExSpecial每类暂用第1份，其余保留可切换。原版cue／组合／时点及Rush映射仍待，不将临时选声签为原作还原。

真人最新统一决定：剩余粒子朝向／运动、选灯、渲染阶段及低分辨率合成，均由统筹与原作者采用可调UE移植配置，替代旧同类待答项；保留全部层、Normal03两独立路径及原始数据，接齐后集中对照原图校正。Root收口为公开BeforeDOF、首接FullRes AlphaComposite及显式BP／配置选灯；未知原版参数不冒称已还原。缺失素材仍未完成，不在授权内替代。表面阴影先用可调小规格：256²对象＋四级512²、R32f无mip，输出4.25MiB，已知含独立深度12.75MiB／角色，额外SceneTextures峰值未实测；原204MiB例案取消，不分配旧规格。全程不复制工程、UE或构建树，不新增大体积输出。

E／R／F 运行仍延期。现盘 Special01／ExSpecial01 两 GA 与两 Montage 均匹配 R55 Cold。两技能各一段，攻击／移动打断均 Disabled，分别有两路 FX 单元、Main 首个 PlaySound Notify 与各自命中 CueTag。Rush 的 NS 27A05443 匹配现盘，未被这三份生产 GA 引用。旧接线脚本指定的三份 `IA_Attack_*` 目标包均缺；`DA_InputConfig_Default` 仍 D9AF148E，正式 `IMC_Default` 现盘 41C034BA，恢复输入前须原生读回映射与改键注册名。技能运行、实际听感和画面仍待。[R55 Cold 叶](../../Saved/Codex/FXProduction_20261026_R1/ColdRead_20261102_R1/Run_R55_KevinBuildR5/Leaf/readback.json)

跨需求索引：[CR-20261014业务冗余／职责收口](Module_Audit_Repair_Ledger.md)。21／21原模块只读回执保留在[CR-R7](Module_Audit_Repair_Ledger.md#cr-20261014-r7)，本次用户指定Kiro顺序整理的范围及计划只见[整改活动记录](../需求文档/refactor_and_squad_switch.md)，时序与实际写权以上方当前窗口为准。其余候选问题不自动扩入本次写集，旧“整批交付后整改／停止Kiro”不作为本次前置。

已通过项不扩跑历史矩阵，后继软件仅验证受影响链路及原问题。

最小联机须以真实Authority与远端SimulatedProxy的同PlayerState/GetPawn／发布键配对验收；晚加入及重获相关性须显示仍有效的剩余FX，结束窗口不补播。旧 N3_R4 在 epoch 81CFEE4C 的真实 `Movement` 例双端配对同段 11 个发布样本、双方到结束，Authority 可见区间累计 −180.000153°，保护归还。原 TurnBack 源动画与现盘一致，当时角色 BP 30222669／ABP 1A3F4719 与现版 3951B625／B6AFA948 有差；当前远端移动沿原 `Movement` 例核同段配对与自然完成，四个预测／FX 试次仍分列。已用原 Reader 离线核对 Build_R5／epoch 5AEDFDC1、同版 Cold 0CC54A71、四个模块及该例 27 个生产包文件，现版角色 BP／ABP 身份一致；下一窗复用该 Cold，双端实际运行仍待。设备与生产视口保持待验。[Authority](../../Saved/Codex/TurnBackRepair_20261021_R1/N3Integration_20261023_R1/Run_R4_20261024/result_listen_owner.json) [SimulatedProxy](../../Saved/Codex/TurnBackRepair_20261021_R1/N3Integration_20261023_R1/Run_R4_20261024/result_simulated_observer.json)

Resource Core关键字保留已构建、准确消费待核；Utility BUF／HLSL Native接线仍待Build／Publish／ABI及单Shader消费；[原失败边界](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-21-source43隔离input专项与同软件cold闭合)。原三远端正常推送授权保持，仅交已验文件；[上次三仓检查点](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-21-三仓已验收提交正常推送通过)已归档。

| 唯一写入者 | 当前任务／真实写集 | 当前边界与入口 |
| --- | --- | --- |
| Movement | 原P8起停73467B／05F61AC2已自审冻结：短按早停／停止途中重按／完整新Hold，Root实核45共享函数AST保持。[P8 pin](../../Saved/Codex/MovementProductionScenario_20261016_P8/provider_pin.json) B825CF19、P3 entry 36787F35 已 Root 绑定 R45 与真实单 ABP Cold，原两份 pin 保 `RuntimeSoftware_R45/P8BindingBefore`。原准备器离线核 67 项和四切点。System 已交回 `ProductionValidation_20261105_R45` 三件启动脚本并冻结。正式 manifest 8572AEA8，原 67 项输入和四切点离线通过。Root 单 Editor 窗软线 3279355314B，直接只读持有同版单 ABP 的三个 Registry 缓存文件。[R45 起停行为回执](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261105_R45/WalkRunStartStop/ProviderVerified.json) 九项通过，四张真实 RHI 诊断机位图均已核见完整人物，保留 Lumen 容量告警，未签生产镜头／GPU 同姿态／物理设备／联机。原 PID 42044 正常退出 exit 0，PIE 世界已退。[外层失败](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261105_R45/launcher_failure.json) 报共享 UE／构建／8001 未归还，原因未定位，当前复查为空。System 实核原 holder 已退、123 项父输入／12 项项目 Config／三缓存无差；失败快照未落共享 PID 或监听明细，首检命中未知。Root 保留两处 Trace 后像，按原锁回写并核全 11 项内容、时间、属性，见[离线归还](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261105_R45/offline_trace_return.json)。原失败保持，原域外 12 根起点仅在已退进程内存，实际正增与综合峰值未知。最后七根样本峰 2783959149B，距当窗软线 495396165B，仅样本余量。原函数对更早的 N3 快照与当前点时算得 3 路径正增 16486B，间隔包含其他窗口，不能充当 P8 上界。C／F 卷 USN 日志读取均拒绝；C 卷当前最早 USN 0xF464D0000 已超过 P8 退出后点测的 NextUsn 0xF45FC29A0，原范围已滚出保留区。旧余额冻结。后继另需可靠上界或用户明确独立额度，仍使用原 R1 七根及预留。P9已冻73111B／2C229D83，R3原走跑14检查／500samples通过；原1D0F前像保留，沿原P10→P9→P3适配镜头／双曲线／TurnBack；Root最终pin camera_yaw_input_units=5.0。N3 当前 provider122480B／FDA50EE5 已冻，Held reject_replay、Initial 不可提供和同连接重获布防的运行证据各按顶部窗口 | 真具名NET两lag设置及五incoming实际读回；非零FrameDelay／Bloat／Loss拒绝。预测1→服务器拒绝→Mode2原basis重放0→新段1须真日志／资源证据，窗口未见即Uncovered，无新事实／RMS／私队列空证明；未运行 |
| FX真正分批（牵头） | B108642／07412EC6已交回、自审互审并由Root核全文件实际patch，写权关闭；A44766／9D688137、U274512／EC08687F、P205577／AAE8B5C5及Leaf50501／4DFA9A46核原像，701目录／配方不改 | R101本窗701 Native已完成；本轮B补222 Master＋222 MI三路真实World编译完成，在原同步预算边界前保全13字段、后严格核Ready／原身份／错误。R33 UHT／编译已过；R107本窗701资源、三GA field与原16包接线／保存实际通过，原16包R3独立持久化Cold已过，运行视听仍待；原8个无VM诊断调用已由R101实际消费 |
| AbilitySystem | Initial不可提供／原Reliable TargetDataCancelled与精准清理已由R8构建；原五源停写，AS／Task仍唯一拥有输入请求和生命周期 | 同原activation的合法终止、未提交Initial与后继隔离保留；真实owner失败／Authority任务及Tag清理仍待N3，不以构建签运行 |
| System真正分批 | 项目Native薄桥已完成并关闭写权：cpp158105／A534E1D4、h35498／91FC7B92；准确157289／74C273D0及34459／C5C89E02前像、cpp1236B／3F8BA652和h1983B／69794334补丁保留于Before/CompileDiagnostics_20261102_R1/System。Root实核差分仅新增ReadSystemCompileDiagnostics和FGGYGONiagaraCompileDiagnostics，原方法保持 | GT有效原对象、默认Context直接公开getter，不创建VM／等待／请求编译；完整CompileState、SystemPath和全部Context错误保留，bSucceeded仅读成功。FX已取得wire契约，R32 UHT／构建通过，无VM getter已由R101完整701核验实际消费，整需求运行／视觉仍未验；构建不代真实运行 本轮AnimationGraphEditorLibrary.cpp19826B／5B33AF4C、h12082B／AF6DC4D0已核收冻结；普通K2注释双桥与Character互审无阻断，原动画接口字节保持，R35 UHT／构建已过，R104新Read及字段已过，R105Write及字段已实际消费；Cast及整图仍未过。 WorldContext桥最终cpp25267B／58EA4D9A、h12717B／9EEB6E7E已核收冻结，源正增6076B；准确19826B／5B33AF4C及12082B／AF6DC4D0、6177B／64DDE707与1327B／40BA23F7 patch保Before/BlueprintWorldContext_20261102_R1/System。复用既有EditResult，原动画／注释方法保持；写权关闭，R36 UHT／构建及R107真实导出／隐藏Context连接和图保存已过；R3独立Cold持久读回已过；真实BeginPlay仍待。 |
| System运行Cold消费 | P3 reader 当前 92900B／B331D536，准确前像和差分见原 P3 `ImplementationHistory/BuildLedgerGzip_20261105_R1`。旧 N3 provider pin 2CB44D57 与 entry 5D8A9B64 保留历史，当前重绑依顶部活动窗。 | Root实际原软件／Cold消费通过，25＋6静态record零差集；仅真实16包资格，旧ABP／seven保持，P3 entry／P10独立未完成。实际DATA／启动与运行仍待，不以离线消费签运行 |
| System独立Cold | Host91699B／A40C58ED＋launch34889B／833F4DBB已Root核收冻结；准确89837B／06C67E7B、33819B／1D507E63及13416B／06C3BD45、7044B／740C59D0 patch保ColdRead_20261102_R1/System/Before。新control9387B／D4BA6573、leaf18474B／E034DD81、preparer8698B／1DF51871，输入181388B／8C872F6E；全部Source写权关闭 | 108明确输入／51根／16只读包，预期只投影R107稳定最终数据；三GA13个实际NS引用、Rush另存第14包，磁盘比target_postimages，不用保存前SHA、临时MID／RT／写前空Tag或无Notify旧快照。主图Tag按真实apply＋原已保存外部灯核，Normal GA级GE不猜。R3实际完整Cold通过且保护全归还；Normal生产门／两技能线性门及原完整时间轴保持，Runtime／视觉仍待；资产／C++／业务冻结 |
| Rendering | R102两cpp最终1DFBCE5B／83BF9D3A已冻，Root实核完整patch；准确前像52460B＋10036B patch留原Before/MaterialInterfaceCompilation_20261102_R1/Rendering，源正增6053B | 新Complete按实际MaterialInterface／World平台完成并返完整13字段；原Read逐字保持，field Query仅细化Map flags／全部errors，角色／证书／VF不变。R33 UHT／构建及R102实际13字段已过，R103本窗资源Ready／field已过，R3选定生产Master／三MI持久Cold已过，运行／视觉仍待；R15／R43旧Read证据不移签新增接口 |
| Rendering表面同作者 | 原身体188输入／257表达式、小规格Capture及四灯／FX灯合同冻结；surface_lighting_author39701B／B99ED3AE新增公开真实Trace=False模式预期，原witness及旧函数AST保持 | 实际Master仍186输入，R107四包已保存、R3主材质／三MI参数核同；原prepare_master→configure_batch→Character模板入口已实际消费。新增CPU预期不证明无遮挡／RT阴影GPU；原图／实际峰值／Spawn仍待 |
| Rendering入口同作者 | F2政策1964B／B2FFC8A4、纯preparer5394B／01C7FEC3、Profile薄作者6866B／627248B3已冻结，已被R32实际消费；旧Stage仅历史 | 复用原create-only Session／Factory／反射读回及Native ValidateConfiguration，保存归Root；实际Python包装／新资产／GPU仍待集中制作。Master213／165仅原recipe候选，未改命名／默认，实际目录按当前701包／14个NS单元 |
| Rendering联机同作者 | 当前 host DFEB1FF5、manifest 9FD6D0A4 已冻结，旧快照见原 N3 历史。与 System 直收同版 `fx_cold` 合同，Movement 新布防和 Editor 原连接观察按顶部写窗接入。 | Initial0按真实运输／basis／native推进；接收前活跃资格、真正Mode2及后续新段／旧资源清理分核。窄route_verified不升级整体通过，末例依同软件／包／Cold两正向实际记录；尚未import／UE／运行，Root最终绑定 |
| Rendering投影同作者 | 仅AAADocs/Scripts/projected_fx_material_plan.py复用既有material_input统一真实x/y输入；已冻28838B／5B7E5252，原前像28644B／7C6F9547保留 | 原raw身份／stage／参数不变、不补默认；其它F2源及N3两Py保持各自冻结，实际同批消费待下一完整准备，无producer／UE／Build／测试 |
| Rendering生成材质同作者 | Simple20690B／0E183C8E、Projected16305B／02163E84已冻；与U共用原生属性／Custom一次批写，输入／附加输出在接线前组齐，真实只读及编译读回保持 | R15／R16已实际制作44份组件／投影材质，失败后原字节归档；不能签完整FX／GPU等价，后继沿原create-only生产链，不另建恢复协议 |
| Character装配 | helper28132B／CDEE2F60已核收冻结，准确27401B／69CA146F及2374B／163C0F3A patch保Before/BlueprintWorldContext_20261102_R1/Character，源正增731B；仅prepare两hunk，其他顶层定义与既有继承模板链保持 | 两个原WorldContext kwargs均传原Actor Self的实际Node／Pin到新桥，仅消费succeeded/error；普通参数继续原严格_pin。双方实读源／patch互审完成；R107实际新导出／Editor图编译／BP保存已过；R3持久Cold已过；真实Spawn／客户端仍待Root，无作者执行权 |
| 地编 | [关卡主灯helper](../Scripts/configure_ggygo_level_key_light.py)已冻结，无新资产窗 | R107已实际配置并保存指定外部灯包及两地图，保dirty／拒PIE，无地图重建或SaveAll；R3两地图主灯Tag持久Cold已过，运行可见仍待 |
| Combat动作分批接线 | 五件已最终冻结，全部写权关闭：leaf50501／4DFA9A46、WindowFXTypes3883／5F85DD9E、Resources.h5552／14615761、cpp26775／92CE8152、原probe287435／8A90D5E2；准确前像／patch见[原交回入口](../../Saved/Codex/FXProduction_20261026_R1/Before/IndependentSystems_20261101_R1/Combat)。PlayerCombo／ComboTypes无本轮差分，输入／伤害保持 | Leaf精确覆盖真实单元目录，原16修改包不扩。共用原Task／ticket，逐单元lease；probe实读原Task+component的自然完成事实，保逐unit原生帧、真实退出及实际Tail覆盖，未观测不能签成功。最终接口已与FX互核，无待补；待统一构建与运行验收 |
| Physics | 原八源的Hero投影→SavedMove→NativeMove→同完成候选RemoteRecord已R8构建；Move wire v3／Response v2须同批二进制，停写 | 无第二RPC／Tick／Gait权威，不伪本地完成，合法远端key／acceptedframe可零；纯键不新增侧倾／gait健康混合／实际远端消费仍待本批运行 |
| Input | 原四源真实CompletedFrame／Serial及Hero投影receipt已R8构建，停写；PostProcessInput仍唯一ASC消费 | AddMovementInput及原方向控制、物理释放／后继隔离不改；receipt不冒实际执行，设备和新软件输入／远端消费仍未验 |
| Animation运行时 | lean原生机制／原Observer同捕获camera、公开ASC任务及NetDriver只读facet已R8构建；唯一逐源JSON与Combat共享，均停写 | Owner／Authority有效性与Sim不可用区分；五incoming实读不证明私有队列空，骨骼及新ABP／网络画面仍待生产配置和验证 |
| Animation资产 | State迁时三源已冻：h11092B／58CAB3BE、cpp29151B／C4A0ED8A、窗口Py48058B／17EC8BE8；精确旧原像已存。保Guid／原State／其他Notify，显式fresh relocations才改实际Main区间；ABP B6及姿态wire保持 | Root已源审并核当前Normal01通知轨道／UE原生链接条件；R10编译及R107五攻击Montage迁时／原State保持已实际保存，R3完整时间轴／原State数值读回通过；原点Notify API保持，实际运行触发仍待 |
| Audio | 本轮既有export／Catalog只读核查已结束，无新增可接原组合／时点或Rush映射；五Cue／第1份／Main首接及真实命中政策保持 | 三Normal原Clip事件为空；Special／ExSpecial转换metadata缺事件字段不作原事件为空。仍缺动作／准确Clip→Wwise事件→时间／条件／组合的真实调用桥，Stop还需对象作用域；后续只消费新确证及集中听感，不重复旧扫描。无源码资产写权或UE／Raw窗 |
| Root配置 | DefaultEngine13317B／D603A095已正式保存：保VelocityOutputPass=0，新增Translucency.Velocity=1及EarlyVelocityPass=0，仅63B；原像13254B／6FBCC667在FXProduction_20261026_R1/Before/Config。AudioTags／N3 logger原配置保持 | 尚未实际CVar读回；R10真实构建已消费该配置，Runtime v3／23078D9C无配置delta，原reader已实核通过。最终pins待生产后重绑，旧local验收不移签新网络运行 |
| Resource | 完整有界只读后继已核收并收口：累计13494／65536B，父150稳定全归还；仅两授权证据4021B，PNG／Native未改。DUMPBIN与官方XED已证/6解码；12类宿主字段／方法仍unrecovered | 停于数据驱动分发，无12类绑定线索，不再延展通用跳板。原临时UE配置继续，不占UE／资产窗；只有真实宿主绑定新入口才唤醒。准确范围、工具及未完成项留[来源调查历史](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-29-宿主只读后继收口与解码缺口)和原会话 |

最新临时FX组合已由真人确认，取代旧待答组合项：按对应动作真实Main窗口播放全部候选层，包括空挥时Hit／Boom；启用Normal02_02Aura及Normal03_06AuraSmoke，两Mesh0动态拖尾采用可调UE生成。保持每段一个原Task的资源生命周期、Mesh根Attached／Identity及既准释放策略，编译单元按当前拆分方案；暂不执行缺失Unity宿主，不跨动作复用TurnBack烟雾，不新建Rush GA，不恢复延期E／R／F输入。全部接齐后集中对照原版校正，可能暂时过密，不能签为原cue／时点／挂点已还原；音频仍沿上文真实命中策略。缺失素材、身体／武器表面受光及原始证据继续保留在原入口。
### 当前集成契约

最近完成本地验收的软件为[74D7DC13](../../Saved/Codex/TurnBackRepair_20261021_R1/RuntimeSoftware_20261025_R8/software.json)，已加载生产ABP B6AFA948，Cold_R4及本地R2两TurnBack／R3走跑补验通过，窗口均正常归还。Initial取消及联机CorrectionReceive日志虽已构建，尚未在此软件完成N3；[旧软件联机历史](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-24-n3当前软件依赖收口与双端实跑归还)不移签。真实设备、起停缺口、GPU及FX网络仍待。

FX独占F1及十一件zzz脚本：build／material／niagara／native_shader／material_ue／niagara_ue／particle_renderer／particle_motion／particle_uv／import_assets／mesh_fbx，另含原作者build_pyrios_ghost_fx.py的SourceModel T/B读取；保唯一算法及旧默认。后继按实际消费核保护交集，不沿用旧904父集合。真人允许全部可见层临时首接，暂不执行缺失Unity宿主脚本，仅在明确ProjectConfigured分支放行；原逻辑继续追查，不能签完整还原。生产CPP仅准本页源码窗，包／UE未授。

后继同窗接口：Root重取既有Special／ExSpecial GA准确Native前像→Combat返回伤害配置／暂存Step数组→Animation窗口及重取F1 baseline→FX继续只改FX字段→Root唯一写回保存。每步保已存HitCueTag、前序伤害及其余非自有字段，核真实对象／dirty、preparation_complete、errors和最终差集，拒前像不符；不各自重建旧CDO数组。音频已持久化，无需重跑要求旧同PID创建收据的Audio caller；最终核Montage／Cue／Wave及HitCueTag保持。两GA不与后续Rush绑定同次创建；部分保存不等于整技能完成。

技能灯接缝：FX独占同CPU实例的真实Point灯及每NS MID/UserMaterial，向Rendering发布有来源／有效期／归还的派生灯事实，并登记外部MID。Rendering原Tick唯一采样主／四灯：主灯独立，已配置场景灯固定占槽，余槽按贡献／稳定key选同World活跃FX灯，总数最多4，策略／额度由BP配置显式开启；无活跃FX是正常空槽，源失败不当成功。原四灯算法更新自身和登记MID，真实快照未应用不算受光就绪；旧handle不释放后继。Native LightRenderer与Toon共用真实灯事实，不复制模拟或新增帧调度。Masked双draw／可调2cm外扩是UE首接，bounds包含外扩，原硬件深度／Stencil及屏幕轮廓差异仍待原图校正。

生产主灯接缝：Editor实例reference_light不能代替Spawn Pawn。模板Explicit、关卡Actor引用为空且bAutoActivate=false；既有BP BeginPlay唯一Tag／类型／World校验后赋公开KeyLight→Activate(false)，原override唯一Refresh；0／多／错类Deactivate并诊断。新加未消费的BindSceneKeyLight／空灯暂态特判已决定撤回，不增加第二入口。地图显式配置GGYGO.KeyLight，原外部灯包与当前同BP测试图同批核；Character／地编只备作者源码，Root同窗唯一保存。实际Spawn／客户端及首帧仍未验；模块直发若被旧范围拒绝，由Root转交，不等用户逐项授权。

仍被消费的已验契约：Slot保留生产A／ActionPoseSlot且不移Mesh；四缓存纹理不重复制／解码；伤害基线10／20／30。准确旧证据见[Slot](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-17-slot对照结论保留a身体基准修正)、[纹理](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-四份缓存贴图真实解码与完整保护通过)及[CR-R5](Module_Audit_Repair_Ledger.md)。纹理UE采样／材质画面、伤害设备／网络仍未验；Decal以本页当前作者条目为准，旧离线稿不作生产通过。

## 本批需求与验收

- 技能段首方向：每个技能／ComboStep真正开始时，以当时真实有效输入更新一次技能基础方向。例如第1段中途改按反向，第1段不因输入持续重定向，第2段实际开始时使用反向；保留动作自身Yaw。沿现有合法无方向语义，不用旧缓存或固定前向冒充新输入；未就绪与真正无输入须区分。同段纠正／重放不重新采样；胶囊、动画、动作位移、命中轨迹和FX使用同一新段方向，保既定最小联机的一致性。不挪攻击／移动打断点；常调策略放GA／Step配置，CMC唯一执行。已实现／编译、生产五实际段配置及独立冷读／本地真实输入与清理通过，[准确R3证据](../../Saved/Codex/ComboStepFacing_20261025_R1/Runtime/Run_R3/result.json)；设备／可见表现及真实联机纠正／重放未验，保留活动验收边界。E／R／F延期不因此解除。
- 普攻第3段（Normal03）音效／特效不全仍是当前反馈重点。[R55 同版原生读回](../../Saved/Codex/FXProduction_20261026_R1/ColdRead_20261102_R1/Run_R55_KevinBuildR5/Leaf/readback.json)核实 3 GA 五段各自命中 CueTag、5 个 Montage 各有 Main 0 秒 PlaySound（原生触发偏移 +0.0001 秒）；五 Cue 磁盘与各自保存回执一致。Normal03 有 7 个独立 NS 单元，6 个显式 DualSignedField；原 cue／时点／Stop 仍未知。R40a／R40b／R42 均以 `-NoSound` 启动。旧有声窗口 6BC14F92 见三段 Main 组件，48kHz 双声道 Master 录音 11.584s 有信号，命中 voice 与设备回环未验；旧八样本用户确认听到，但仍报异样且无技能上下文。默认 Console 端点现只读实测静音。后继用有声生产窗口分开核同一实际段的技能声与真实命中 voice，记录样本选择、试听反馈和两路可见 FX。 原 Audio 已交 Normal03 同段分离取证方案，技能声 Skill 1 3972543768／真实命中 Impact 1 1199025191；AudioInsights 按 Wave／播放 ID 记录 12s 内的源包络，拟单次 4MiB 内存尾环快照。原 Writer 还写事件定义／缓存，8MiB 是暂估。[三处原生引用实测](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/Cold_NormalAudioLinks_R1/audio_native_links.json) 75D5EB01：同版空 Editor World，原对象未预载，Normal02 技能、Normal03 技能及命中均直接解析到既定 _1 Wave；旧别名均空，零 dirty，无需重存。[关窗](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/Cold_NormalAudioLinks_R1/return.json) D65C3CC6，UE exit 0、5928 锁／11 Trace 归还；关窗落回执前按原 R1 尚余 370619448B。旧 R4 Trace 见两路各自开始／停止，原 Audio [有声离线包](../../Saved/Codex/AudioRestoration_20261022_A1/NormalComboAudio_R1/Normal03Voice_BF1A41B4_Offline_R1.zip) 160C4BD3 已核收，当前 BF1A41B4／Cue 4F5A6B64 的 manifest C40D09D4、host 42361A84、端点叶 0E819776 已按字节生成。原真实目标三击、≤12s 两路源事件、8MiB 单快照与只读 Console 会话。待独占父保护及实际浮动 PIE 窗；当前端点静音，实际播放、包络、Master 和主观听感仍分项待验。[旧有声回执](../../Saved/Codex/AudioRestoration_20261022_A1/NormalComboAudio_R1/Runtime_20261023_R4/readback_recovered.json) [旧试听反馈](../../Saved/Codex/PyriosAudio_Audition_20261013_R4/hearing_confirmation.json)。

- 生产镜头 [R3 两叶驱动结果](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_ProdDraw_R3/driver_result.json) 4C46F392。走跑 9 项及 6／6 同帧，TurnBack 78 个原连续区间累计 −180.000153° 自然结束、9／9 同帧，补齐 FirstRun／FinalRunStop／RunOut。三张实拍已核。按原 Draw 投影复算，15／15 的盆骨／双髋／双膝骨点在视口，14／15 有脚或脚趾骨点越出下缘；原生产完整腿脚、实体设备及联机待验。旧 21.35°／58.35° 为暂停后 Draw。[连续 Run 双档实拍 R1](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_LeanTargets_R1/WalkRunLeanTargets/VisualFailure.json) A661A148：原 Look 校准 157 帧 ΔYaw 12.5°／需求 12.0994°，两次目标脉冲 309／321 帧 ΔYaw 20.40058°／40.40058°，CMC 需求均 0°。20° 未命中，60° 未进入。8 张候选图仅为失败证据；临时取景已还原，生产机位未改。原 Rendering 与 Movement 正核两次发键前的真实胶囊／输入方向基底；保 ±2°、同自然帧与双档目标。现 SetupView 固定 Pawn，临时机位唯一 Draw 投影、GPU 蒙皮及实体设备待证。[R1 归还](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_LeanTargets_R1/return.json) 25095C1E，UE exit 0、141 父锁／11 Trace 归还，关窗计量余 313528346B。原外层 [退出信号检查失败](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_ProdDraw_R3/launcher_failure.json) 6101E941，缺原退出码；[离线归还](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_ProdDraw_R3/offline_trace_return.json) 3AE69894 核 138 父／139 句柄已释／三缓存／12 Config／11 Trace。System [原句柄退出差分](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261109_ProdDraw_R1/Before/shared_original_exit_handle.xz) 0D069CC0 已核收，FAC8AFA8→BC33F05E；同版本小进程已复现 WaitForExit(0) 与原 ExitCode 分歧，新候选随下一个必要窗口核真实归还。[实测与原失败](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-生产镜头-r3-三点复验与离线归还)。
- 通用且角色配置整身姿态：20°方向误差约倾20°，60°身体对地约40～50°（真人确认侧倾平面，保留原前倾／屈膝），髋／膝／双腿同帧，不以旧Spine替代。六普攻Main＋完整End原地化保姿态起伏和曲线，已验不重烘焙；角色保持已验A配置，Slot结论见上。
- TurnBack第一段位移方向锁定进入时的方向，换键不得崩溃；原运动侧倾在第一段平滑混至精确0，保留源动画前倾／屈膝。第二段切换时按当前输入跑出，动画与位移一致，后续转向受既有角速度约束。独立信号只开放再次触发资格，不决定第二段切换；开放后允许反向输入再次触发，旧信号不能开放后继。保留同源完整Yaw及真实完成区间，不重复／回摆、不另造Sequence／Profile／帧调度，不恢复退役DA，不以bEnded冒称Finished。WalkRun保持camera-relative；运动侧倾仅由镜头变化导致的转向触发，纯方向键换向不触发侧倾，WD→WA仍受角速度约束。Walk↔Run从当前显示倾角连续混向相应步态目标；用户已定Walk为Run的50%，保Run线性keys(0,0)/(20,20)/(60,45)/(90,50)/(180,55)，制作时显式展开Walk为(0,0)/(20,10)/(60,22.5)/(90,25)/(180,27.5)，不新增运行时倍率或恢复旧字段兜底。15°／30°仍仅过渡举例。双曲线及两图已真实写入生产ABP（Author R3），外围保护失败如实保留；新软件Cold_R4、镜头／纯输入分离、段内换键、D1回正／D2跑出及资格信号、走跑连续混合／反转／角速度已有本地自然帧数值通过证据，范围为 R2 的 TurnBack 两叶及 R3 的走跑／镜头侧倾；两窗 actual_visual_accepted 均为 false。R2 外层仍失败，R45 诊断机位只覆盖已记录帧。生产机位的实际连续画面、实体设备及最小远端消费仍待验。
- 原攻击事件不挪、只供下一段攻击；移动独立许可在实际 Main 结束，原生合法 Notify offset 不提前授权；许可／消费分开，qualified Held 保持。已将 R55 的三普攻双点对照[原拆点冷读](../../Saved/Codex/PlayerBridgeIntegration_20261013_R6/Project/Saved/Codex/NormalMoveNotify_20261015_N1/Attempt_R2/cold/return.json)，六个 Notify 的 GUID、对象及导出时间一致，三个移动作者点与各自 Main 末端相同。三 Montage 和 Combo GA 现盘匹配 R55 冷读 SHA，与 R42 保护记录的尺寸／时间一致。R42 三原实例均先到 Main 末端才开放移动，实际新 W 在 End 1.690157／1.354100／1.404760s 取消并归还；攻击许可分别于原事件 0.275024／0.294345／1.111460s 开放。R40b 已验 01→02→03 同激活续段，03→01 子例将攻击点移到临时 Montage 的 Main 中点，原整窗失败保留。现盘 GA／Normal03 与 R55 冷读一致，配置 03→01，原攻击点 1.111460s 到 Main 结束 1.400000s 有约 0.289s。真实 RHI 原生产 03→01 已过。原点前帧 1450 新请求 3 保同激活原 03，攻击与移动门均关闭；原点后帧 1479 于 Main 1.128096461s 接续 01，消费前移动门关闭，旧 Task 退役、新段 token 3→4／实例 2→3。5923 保护句柄与 11 Trace 归还。[原生产回执](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Normal03Authored_R1/return.json) 84053456 [构建与留证](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-normal03-原攻击点续段复验归还) [R42](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_R42/return.json) [R40b](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_R40b/return.json)。E／R／F 继续 Disabled／None 自然结束锁定。CMC 唯一胶囊权威，GAS／Combat 生命周期及结算不迁移；C++ 通用，角色组合参数在 BP／Montage／曲线／配置。
- 全部可定位FX／Audio还原并接Special／ExSpecial／Rush、三普攻、现有冲刺闪避／TurnBack；Pyrios两视觉线按原视频／原图。未知cue／time／挂点／TRS／Follow／Age／Fade／Stop／来源保持未知，不用默认frame2／替代声效／库存／静态接线冒称还原。Lyra只读，斗篷只读暂挂，延期Dodge GA／CMC不恢复。
  - 身体线：11-07 用户实看确认角色材质特效没有问题，该反馈与攻击 FX 分开记录。R45 停步诊断机位可见银甲与蓝色前臂，脚边仍有暗块。与用户正背原图的机位和受光不同，无法判定肤／甲材质、背面轮廓与阴影是否还原。R55 已核磁盘 Master／三 MI／角色 BP 与冷读身份一致，两地图 `GGYGO.KeyLight` 已读回。后继同版实际 Spawn，用生产镜头及正背对照机位核主灯实际选中、阴影 RT／遮挡与可见结果。斗篷保持只读暂挂。[正面](../Assets/Pyrios/Rendering/References/20261009_Pyrios_Front.png) [背面](../Assets/Pyrios/Rendering/References/20261009_Pyrios_Back.png) [R45 实拍](../../Saved/Codex/TurnBackRepair_20261021_R1/ProductionValidation_20261105_R45/WalkRunStartStop/WalkStop.png)
  - 攻击 FX：角色材质效果按真人反馈保留。集中真实 RHI 的 [Normal01 同帧实拍](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Integrated_R1/Editor/Saved/FXCaptures/normal01__normal01_production_viewport.png) 仍缺[原图](../Assets/Pyrios/FX/References/20261009_Normal01_Slash.png)的连续蓝白主弧，观察脚本未获活尾。Draw 1219 三个目标层各 1 粒、LOD0 驻留且有三角、无 PSO 等待；三个配置材质的 GT ShaderMap 存在但未完整，RT 提交未覆盖。[本窗观察](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Integrated_R1/Editor/editor.log#L4646)及[原 ProfileGPU](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_ProdDraw_Normal01Profile_R1/Editor/editor.log#L5354)仅覆盖各自采样。R4 已证原 Draw 三个材质各有一份 MeshBatch 和透明 Pass 候选，缺口在实际材质／fallback、对应 Pass 的 Niagara Mesh VS／PS 与命令生成。原 FX／Rendering 仅按顶部只读分析。角色 Capture 只给角色 MID 供受光，不投射地面；[倒下条纹](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Integrated_R1/Captures/05_member1_dying.png)与换人拖影需分开。随集中运行补稳定后的原机位 Draw，对照 VSM Shadow Mask 和关运动模糊诊断，保生产配置。配置材质 GT 不完整只作线索，本轮无修改。原 RenderDoc 单帧候选仍缺可用的写前量控，未应用；引擎不动；原失败及同帧证据保留。[原历史](Module_Repair_Parallel_Schedule_History_20261013.md#2026-11-09-normal01-首个双亮层-draw-归还)。

## 推进决定与理由

以下为本轮推进顺序；具体写集和共享窗口由本统筹分配，既有保护输入保持冻结。

1. 按独立需求完整实现／配置后集中验证；旧通过不重跑，只验当前软件受影响链、原问题及必要设备／视听／最小联机。CR草稿、延期E／R／F及无关引擎工作不作前置。[原生产输入入口](../../Saved/Codex/PlayerInputOperations_20261014_P1/README.md)按需查。
2. FX／两视觉线及三单步技能继续并行。完整RGBA/RGB、可调(-1,0,1)、Normal03双路、Rush全分辨率／原生阴影目标保持；公开BeforeDOF及其余表现参数已由最新统一决定解阻，按可调UE配置收口。16GiB方案取消且从未启动。所有实现／配置冻结后集中编译、制作及必要验收；[原FX交接／失败](../Modules/Character/Rendering/ZZZ_FX_Handoff.md)和[旧consumer补丁](../../Saved/Codex/PyriosMaterialConsumerSourcePatch_20261014/material-input.patch)仅作来源，不代验收。

## 交接与持续维护

原位更新当前事实及未完成项；已结束过程迁历史，稳定规则见AGENTS.md。模块历史正文6／6归档、CTX入口减量及原证据见[历史索引](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-当前入口重复状态收口)，不再作为当前前置。未完成需求、失败及仍被使用的接口保留，历史只按需读取。

## 完成交付与历史

整批尚未完成。需两视觉线、全部可定位FX／Audio动作链及真实设备试听；六源／Slot／整身／生产BP／全部Yaw和最小冒烟／联机通过；已验保存、集中受影响模块及Obsidian笔记；父工程、Source/GGYGO子仓、Obsidian独立仓准确已验文件中文commit／push成功且无本批在途。只stage已验、保用户dirty，不放宽角色／场景ignore。全部真正完成才留摘要、删除一次性跟进；任何时候不关机。

历史过程、旧规则／门禁及失败证据见[2026-10-13排程历史](Module_Repair_Parallel_Schedule_History_20261013.md)。本次优化前活动排程亦原样保留在该文件末尾；本批未完成项仍以本页为准。更早[Gate63进度历史](Module_Repair_Progress_History.md)只在需要时查询，历史不授权当前开工。
