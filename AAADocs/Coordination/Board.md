# 需求看板

统筹维护需求列表；所有人自己维护占用表。规则见 [TaskWorkflow](../Rules/TaskWorkflow.md)。

**2026-11-11 交接**：Kiro 这一批到此结束，剩余工作交给 Codex，先读 [Codex 交接](Handover_Codex.md)。证据文件在 `.agents/` 和 `Saved/` 下，只在本机，不入库。

## 需求

每个需求一行。详情只写在需求记录里，这里不复制。

| 需求 | 负责人 | 状态 | 需求记录 |
| --- | --- | --- | --- |
| 普攻第一段主弧与冷首击 | Kiro | 已完成：共享网格角点错位重导入后主弧连续可见；未预热首击等资源就绪后出刀，FX 同帧可见（[主弧证据](../../.agents/tasks/requirements-closeout/evidence/I01.md)、[冷首击证据](../../.agents/tasks/requirements-closeout/evidence/I02.md)） | [normal01_first_strike](../需求文档/normal01_first_strike.md) |
| 普攻连段生产冒烟与活尾 | Codex（待统筹指定） | 需用户：攻击接续点之前的按下要不要存起来留到下一段？A 接受现状并改 spec 措辞，B 另立需求接回预输入。冒烟 22／24 通过，2 例按约定保留失败（[证据](../../.agents/tasks/requirements-closeout/evidence/I08.md)） | [normal01_first_strike](../需求文档/normal01_first_strike.md) |
| 走跑与转身：生产镜头侧倾和取景 | Codex（待统筹指定） | 需用户：起步／停步各有一次骨盆单帧跳变，A 接受，B 另开动画修复？20° 档侧倾按骨盆算达标（19.8°）、按头部算超出（22.7°），按哪个算？60° 档、纯方向键换向、TurnBack 已通过；取景已选 A（[证据](../../.agents/tasks/requirements-closeout/evidence/I04.md)） | [walkrun_turnback_production_camera](../需求文档/walkrun_turnback_production_camera.md) |
| 普攻第三段音效 | FX 原会话（Codex，随玩家视听返修） | 返修受阻：已排除两份声音素材导串或旧缓存失配；原解包咨询已结束，尚无已证声音调用载体。两份素材待用户辨认具体多余声音，原选用条件和时点仍缺；当前无解包任务在途。未改 Notify 或用户手改资产，声音语义及听感未验收 | [normal03_audio](../需求文档/normal03_audio.md) |
| 特效与音效接线（普攻、技能、冲刺、转身） | FX 原会话（Codex） | 攻击 FX 本批完成并分仓 push：挂点入口缺陷已修复，统筹复核、共享增量构建、10 项相关回归和 D3D12 普攻／强化技能冒烟通过；自有 UE／UBT 已退出。外观后续由用户调，音效／Rush／LeftShift 待定保持，独立挂点真实联机／Cook 未验，整体需求不签完成。[修复提交](https://github.com/WuDuElysia/GGYGO_Source/commit/73c671a) | [fx_audio_wiring](../需求文档/fx_audio_wiring.md) |
| 改键页面迁共享 UMG（蓝图分层 B06） | Kiro | 已完成：生产 Controller 使用 `WBP_KeySettings`，真实前台两轮 PIE 走通改键、冲突、恢复默认、存档读回、关页不卡键（[证据](../../.agents/tasks/requirements-closeout/evidence/I03.md)） | [blueprint_layering_followups](../需求文档/blueprint_layering_followups.md)、[审查明细](Blueprint_Layering_Audit.md) |
| 死亡自动替补迁共享蓝图（蓝图分层 B08） | Kiro | 已完成：C++ 只发布死亡事实，`BP_PlayerState` 请求替补；联机死亡自动换人、后台死亡不切换、无人存活不假成功三类断言通过（[集中 RHI 回执](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Integrated_R1/return.json)） | [blueprint_layering_followups](../需求文档/blueprint_layering_followups.md)、[审查明细](Blueprint_Layering_Audit.md) |
| 蓝图分层 Q02～Q05 资产图读回 | System 原会话（Codex） | 已完成并 push：四项保存图、配置和直接引用审查通过，未新增分层问题；特殊技能／过渡授予和移动 FX 配置边界已记，运行视听未验。[审查提交](https://github.com/WuDuElysia/GGYGO/commit/2d07708) | [blueprint_layering_followups](../需求文档/blueprint_layering_followups.md) |
| 角色受光与阴影（倒下帧条纹、换人拖影、正背对照） | Kiro | 已完成：条纹是 VSM 缓存残影，`BP_PC_Pyrios` Mesh `BoundsScale` 设为 11、对象阴影宽度除回倍率后修掉，联机客户端倒下帧无条纹；拖影是换人相机跳变的运动模糊。`BP_PC_Pyrios` 依赖地图里唯一带 `GGYGO.KeyLight` Tag 的平行光，原验证地图为 `L_Movement_Test`（[证据](../../.agents/tasks/requirements-closeout/evidence/I10.md)）；11-13 Kevin P3 的唯一主灯、投影和环境补光已另行读回及看图核收 | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「角色受光与阴影」 |
| Kevin Boss 完整组装 | BossAI 原会话（Codex） | 单机组装、P3 照明、禁互踩和最小真实联机已通过：同一 Editor 双端经 IpNetDriver 复制，三招动作／FX、两名玩家血量与命中 Cue、贴身 AirChain01 环境落地及结束清理通过；本批无生产修改，自有 UE 已退出。独立进程、完整网络矩阵／联机死亡、Cook／性能／设备试听未验，原视听还原缺口保持。[联机验证](https://github.com/WuDuElysia/GGYGO/commit/c9409e9)、[落地修复](https://github.com/WuDuElysia/GGYGO_Source/commit/0616e3f)、[照明交付](https://github.com/WuDuElysia/GGYGO/commit/28fb375) | [kevin_boss_assembly](../需求文档/kevin_boss_assembly.md) |
| 最小联机：纠正重放与特效晚加入 | AbilitySystem 原会话（Codex） | 已完成并分仓 push：最终编译、17 项回归、六场景及活尾专项通过，统筹已核活窗、重获与活尾实拍；Movement／FX 评审无阻塞，自有 UE／UBT 已退出。Cook、性能、物理输入设备、完整网络矩阵和代理独立 RMS 导入未验。[交付提交](https://github.com/WuDuElysia/GGYGO/commit/32ab282) | [minimal_multiplayer](../需求文档/minimal_multiplayer.md) |
| 消息路由失效监听清理与 SyncMarker 工具归位 | System 原会话（Codex） | 已完成并分仓 push：编译、3 项相关自动化及 Python 绑定通过，Messages／Animation 差分评审无阻塞；Cook 和历史蓝图包重载未验。[实现提交](https://github.com/WuDuElysia/GGYGO/commit/6d4fb73) | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「消息路由与 SyncMarker 工具」 |
| PIE 退出输入映射清理 | Input 原会话（Codex） | 验收完成、本地已提交，待本批远端推送授权：两轮生产 PIE 中三份映射各移除一次，原输入对象仍匹配，最终全空；无生产修改，自有 UE 已退出。NullRHI 不代验视觉、设备、联机或 Cook。[验证记录提交](https://github.com/WuDuElysia/GGYGO/commit/1d168d8)、[Input 笔记](https://github.com/WuDuElysia/Lyra_Learn_note/commit/98896eb) | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「PIE 退出输入映射清理」 |
| CR-R7 剩余候选盘点 | AbilitySystem 原会话（Codex） | 已完成并分仓 push：修复同 Spec 嵌套 Try 借用输入重试来源，编译和六项回归通过，统筹／Input 消费侧评审无阻塞；优化与延期玩法保留。[实现提交](https://github.com/WuDuElysia/GGYGO_Source/commit/7acd129) | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)、[修复清单](Module_Audit_Repair_Ledger.md) |
| 死亡结束后的 Pawn 处理改由蓝图决定 | Character 原会话（Codex） | 已完成并分仓 push：三份共享模板、四份既有蓝图接线；编译和 10 项回归通过，含 D3D12 联机死亡替补，Teams 接口评审无阻塞；独立进程、Cook 未验。[实现提交](https://github.com/WuDuElysia/GGYGO/commit/42d42aa) | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「死亡结束后的 Pawn 处理」 |
| 动画层去掉 ZZZ 兼容层 | Codex（待统筹指定） | 未开始，等走跑起停跳变的用户回答 | [zzz_anim_compat_layer_removal](../需求文档/zzz_anim_compat_layer_removal.md) |
| 各 spec 勾选状态回写 | AbilitySystem 原会话（Codex） | 已完成并 push：七份 spec 与需求状态表已按现有证据回写并核收，未覆盖、原失败和用户待定项保持；用户明确授权后两笔文档提交已推送 origin/main，无 UE／构建在途。[交付提交](https://github.com/WuDuElysia/GGYGO/commit/a87d2aa) | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md) |
| 激活生命周期：Editor 动画测试组补齐 | Animation 资产生产原会话（Codex） | 验收完成、本地已提交，待本批远端推送授权：完整 `GGYGO.Editor.Animation` 9／9 通过，Requirement 9.2 与任务 8 缺口已补齐；无生产修改，自有 UE 正常退出。启动诊断、原失败及其它未覆盖边界保持。[验证记录提交](https://github.com/WuDuElysia/GGYGO/commit/2d0f642) | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)、[规格](../../.kiro/specs/abilitysystem-activation-lifecycle/tasks.md) |
| HealthSet：死亡两端一致性与单机表现 | AbilitySystem 原会话（Codex） | 死亡专项通过并本地提交，未推送：增量构建和两项 D3D12 测试通过，原死者双端数值／广播及单机、双端死亡前后段已看图核收，自有 UE 已退出。Requirement 5.3 仍部分完成；原负责人继续核现有 Combat 命中入口及受击／破韧表现接线，不重做死亡专项，不推定新增动作。[测试提交](https://github.com/WuDuElysia/GGYGO_Source/commit/7408f98)、[验收记录](https://github.com/WuDuElysia/GGYGO/commit/07d0963) | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)、[规格](../../.kiro/specs/abilitysystem-healthset-repnotify/tasks.md) |
| 输入请求：组占用排队与截止 | Input 原会话（Codex） | 验收完成、本地已分仓提交，未推送：共享构建成功，四项机制＋两项 D3D12 生产输入链 PIE 全通过，原截止前一次重试、过期零激活及重按正控成立，自有 UE 已退出。PIE 使用临时占组夹具；预输入、设备／失焦及默认多能力玩法未签完成。[测试提交](https://github.com/WuDuElysia/GGYGO_Source/commit/a7a2534)、[验收记录](https://github.com/WuDuElysia/GGYGO/commit/29b260b)、[Input 笔记](https://github.com/WuDuElysia/Lyra_Learn_note/commit/4c8d33a) | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)、[规格](../../.kiro/specs/abilitysystem-input-request/tasks.md) |
| 旧 ZZZ 动画 spec 残余任务 | Kiro | 已完成：用户 11-10 决定不管，三个旧 spec 关闭 | [zzz_legacy_anim_spec_closeout](../需求文档/zzz_legacy_anim_spec_closeout.md) |

## 占用表

开工前登记，做完删除。只登记会和别人冲突的东西：要改的文件／目录、要写的共享资产、正在进行的构建。

| 负责人 | 需求 | 占用内容 | 开始时间 |
| --- | --- | --- | --- |
