# 全模块修复：当前任务与共享排程

更新：2026-10-19。本页是本批唯一活动需求记录，维护目标、现状、未完成项、验收和必要依赖／证据。原作者见[路由](Module_Conversation_Routing.md)，稳定规则见[AGENTS.md](../../AGENTS.md)。

## 当前窗口与关键路径

当前唯一统筹为“GGYGO｜2026-10-12需求统筹”`01a1347b-ccee-7081-a783-0c3127b3dd48`，独占共享排程维护权。用户直接交需求，统筹协调原21组长并自主决定归档；不依赖 Dot。旧根已归档。本批需求与验收仍未完成。

真人最新排序：E／R／F及诊断音频后延，已有普攻GA成功保留；先移动偏移／走跑起停／TurnBack完整Yaw、独立打断、Slot去留。三类独立打断、连续起停、TurnBack及当前NormalA已通过相应专项；Lean60代表专项已按真人侧倾基准核收；Slot A/B已闭合并决定保留A；生产资产已迁回／保存／Cold通过，生产运行及联机仍待。Source／资产／构建／Git权限仅以当前执行窗为准，ggygo心跳仍PAUSED。


跨需求索引：[CR-20261014业务冗余／职责收口](Module_Audit_Repair_Ledger.md)。已停止Kiro调用，由Root按CodeConventions审核，原作者实现。已应用项、未应用草稿及剩余职责整改只在CR分项维护；本页只保当前集成差集、依赖及共享窗口。


已通过项不扩跑历史矩阵，后继软件仅验证受影响链路及原问题。

最小联机契约保持两Editor／三PIE World，每进程一Mesh，按实际World/Role/PlayerState/GetPawn及发布键配对；不能猜跨端同帧或缺D0首区间。真人已确认晚加入／重获相关性也须显示仍有效的剩余普攻FX及正确时间进度，已结束窗口不补播；远端协议与最小写集由FX／AS／Combat收敛，已进入当前Source批，Root按既有规范审查。Movement N3 provider已核收，Rendering网络N3入口已冻结，真实双进程run pin/连接/视口/FX仍未执行，不作为单人Slot前置。

当前执行窗：用户2026-10-19明确要求先提交Git，Root在R7完整构建／保护归还后独占阶段Git窗。此为当前需求检查点，不等同整批验收；源码及资产字节保持冻结，原18项复验、生产／视觉／设备／联机仍待，Git收尾后继续。

本次按用户要求作本地阶段检查点：源码子仓 fd9334d8c63fe7ca889ebcdf624430cb93cfc87f、笔记仓 4da4f4c4b5f41cb87ef5c90b3d3f4880ad4554f6；父工程由包含本条的commit记录承载。推送曾被自动审批以私有源码远端及载荷未明确核准为由拒绝，当前未push；不绕过审核。阶段提交后继续同R7原18项及受影响生产／联机验证，完整需求未验边界保持。

### 当前Source批：CR R3／R4／R6及R7集成

当前42件（38 Runtime＋4 Editor）已通过R7标准完整Target构建，23.65秒；原cmd129384／句柄exit0，完整起点／退出身份及保护通过，原工具会话25522终态exit0。Root实际消费本轮software，核收59产物／3模块／369源码；原18项最新仍为R5的严格14项0E／0W，R7尚未复跑。R6头引用C1083失败及全部原错误已归档保留。

当前已归还构建见[R7 after](../../Saved/Codex/CRSource42Integration_20261019_Entry_R7/Build/after.json)及[return](../../Saved/Codex/CRSource42Integration_20261019_Entry_R7/Build/return.json)：success／protection_success均true，未授权差集0，原共享进程／监听[]。当前只处理用户明确要求的阶段提交，已验源码／资产层与未验运行层继续分列。

单处include已改为实际`Camera/GGYGOCameraMode.h`，CPP及[R7五件](../../Saved/Codex/CRSource42Integration_20261019_Entry_R7/entry_pin.json)已由作者／Root核收冻结，pin SHA `07AB60918DAF9AF23F8FBBCA1C6713F753AA6BF5EE0E2BA74A2F5540332FD6E0`。Root核实42集合`567BDA1D4A65151D700C45F585845B0AA813D24E2240486CCE6350EEC8AE9B08`、准确1源码／2别名迁移、其余41字节不变及272依赖；943软件输入、340原生输入、5567＋2写集和原18项保持。本轮构建及保护已通过；阶段Git不改变源码／资产字节，不作生产／网络证明。

R7须显式承接R6失败构建父及1源码／2别名迁移，其余41一致；原18项及全部强断言保持。五重入的后两场景仍待实际到达，真实Started不冒称覆盖Guard已Returned自定义后钩，PostWriteRejected不放宽。PrepareClose纯写和GAS／CMC权威保持；首生产Draw前布防、首次确认边界、模式资格及真实FX Age／尾部／归还／销毁仍须实际Editor与生产／联机证明。

原13件差集、42集合静态核收及R6构建失败完整归还见[本阶段历史](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-source42静态核收与r6构建失败归还)。历史不恢复写权，完整需求仍未完成。

Slot-AB已验收归档：保留ActionPoseSlot及生产A，不移Mesh。普通B同Idle身体骨链抬高约63cm，当前节点仍承担必要基准修正；[完整结论与证据](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-17-slot对照结论保留a身体基准修正)按需查，不再作为其余需求前置。

缓存贴图：`F:/AnimeStudio/_work/pyrois_decal_texture_cache_decode_20261017/entry_pin.json`及旧四作者件冻结。Resource的`Texture2D.cs`已保存2017+可空V/W，原U不变，未编译；旧缓存JSON仍未知，不能冒称解码／视觉通过。后继仍须补齐Restore／Build／OS依赖、Native ABI和实际采样，将既有四份.dat及原75输入纳入保护，仅为子进程设置冻结PATH／PSModulePath。当前源码集成优先，无资源写窗；旧评估和准确身份见[整理前记录](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-活动入口过程减量)。

伤害配置与运行事实只见[CR-R5](Module_Audit_Repair_Ledger.md)：实际10／20／30及Buff20／40／60已有证据，新源码受影响生产验证尚未完成。

Decal九件离线稿位于`Saved/Codex/PyriosSpecialDecalConsumerDraft_20261017/projected/`，已冻结；R4三既有测试104／104通过，未生产应用、未C#／HLSL编译、未Cold／视觉／动作验收。缺真实渲染合同或场景provider须明确拒绝；原失败及九件清单见[整理前记录](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-活动入口过程减量)。当前无写入／运行窗。



## 本批需求与验收

- 通用且角色配置整身姿态：20°方向误差约倾20°，60°身体对地约40～50°（真人确认侧倾平面，保留原前倾／屈膝），髋／膝／双腿同帧，不以旧Spine替代。六普攻Main＋完整End原地化保姿态起伏和曲线，已验不重烘焙；角色保持已验A配置，Slot结论见上。
- TurnBack D0／D1是同一次真实SourceYaw完整反向Run轨迹的检查段：首源区间转胶囊，后续增量不重复／不回摆，末帧保全部Yaw与结束朝向；不另造Sequence／Profile／模式，不恢复退役DA。Anim播放器／CMC真实完成区间同源同帧，失败不得因bEnded冒称Finished。WalkRun仍camera-relative。远端既定SimulatedProxy／listen最小复现必须完成，不加动画时钟／无来源默认0或其它网络重构。
- 原攻击事件不挪、只供下一段攻击；移动独立许可在实际Main结束，原生合法Notify offset不提前授权；许可／消费分开，qualified Held保持。E／R／F继续Disabled／None自然结束锁定。CMC唯一胶囊权威，GAS／Combat生命周期及结算不迁移；C++通用，角色组合参数在BP／Montage／曲线／配置。
- 全部可定位FX／Audio还原并接Special／ExSpecial／Rush、三普攻、现有冲刺闪避／TurnBack；Pyrios两视觉线按原视频／原图。未知cue／time／挂点／TRS／Follow／Age／Fade／Stop／来源保持未知，不用默认frame2／替代声效／库存／静态接线冒称还原。Lyra只读，斗篷只读暂挂，延期Dodge GA／CMC不恢复。

## 当前生产与素材接口

| 原工作线 | 当前边界与下一动作 | 必要入口 |
| --- | --- | --- |
| 生产资产／输入／动作 | 八包已保存并通过独立Cold，移动／姿态／独立打断的单人专项已有结果。新42件构建及专项后，验证实际生产输入、首相机投影、自然结束和清理；E／R／F与诊断试听后延。输入提交／处理不能代替能力触发或真实设备证明。 | [原生产输入入口](../../Saved/Codex/PlayerInputOperations_20261014_P1/README.md)、[原专项与保存证据](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-当前入口重复状态收口) |
| FX／资源还原 | 九失败／Recovery仍未Cold／视觉／动作验收。静态锚点、Main_Distor TRS及Material参数已读，两consumer补丁尚未应用；外部Shader／Texture、cue／挂点／控制／生命周期仍未闭合，Clip内部旋转不证明外部cue。保持冻结，后继按实际依赖补齐并验画面。 | [FX交接](../Modules/Character/Rendering/ZZZ_FX_Handoff.md)、[两consumer补丁](../../Saved/Codex/PyriosMaterialConsumerSourcePatch_20261014/material-input.patch)、[原读取与失败](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-当前入口重复状态收口) |

## 推进决定与理由

以下为本轮推进顺序；具体写集和共享窗口由本统筹分配，既有保护输入保持冻结。

1. 当前推进生产运行／最小联机及CR剩余整改；既有专项保持，不重做已验资产作者窗口或旧矩阵，CR草稿不作本批前置。
2. E／R／F与诊断音频按真人要求后延，不阻塞前述主线；诊断结果仍标非原时序／未还原。FX／Audio还原、两视觉线及最小联机仍属完整需求，未完成项保留，不因后排归档。

## 交接与持续维护

原位更新当前事实及未完成项；已结束过程迁历史，稳定规则见AGENTS.md。模块历史正文6／6归档、CTX入口减量及原证据见[历史索引](Module_Repair_Parallel_Schedule_History_20261013.md#2026-10-19-当前入口重复状态收口)，不再作为当前前置。未完成需求、失败及仍被使用的接口保留，历史只按需读取。

## 完成交付与历史

整批尚未完成。需两视觉线、全部可定位FX／Audio动作链及真实设备试听；六源／Slot／整身／生产BP／全部Yaw和最小冒烟／联机通过；已验保存、集中受影响模块及Obsidian笔记；父工程、Source/GGYGO子仓、Obsidian独立仓准确已验文件中文commit／push成功且无本批在途。只stage已验、保用户dirty，不放宽角色／场景ignore。全部真正完成才留摘要、删除一次性跟进；任何时候不关机。

历史过程、旧规则／门禁及失败证据见[2026-10-13排程历史](Module_Repair_Parallel_Schedule_History_20261013.md)。本次优化前活动排程亦原样保留在该文件末尾；本批未完成项仍以本页为准。更早[Gate63进度历史](Module_Repair_Progress_History.md)只在需要时查询，历史不授权当前开工。
