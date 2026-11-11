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
| 普攻第三段音效 | Codex（待统筹指定） | 需用户：在 PIE 里试听第三段技能声和命中声，两种都行、换技能声、换命中声还是时点不对？自动化取证已通过（[证据](../../.agents/tasks/requirements-closeout/evidence/I06.md)） | [normal03_audio](../需求文档/normal03_audio.md) |
| 特效与音效接线（普攻、技能、冲刺、转身） | Codex（待统筹指定） | 未开始：盘点表未写，Normal02／Normal03 和两个技能未实拍，冲刺和转身未接 | [fx_audio_wiring](../需求文档/fx_audio_wiring.md) |
| 改键页面迁共享 UMG（蓝图分层 B06） | Kiro | 已完成：生产 Controller 使用 `WBP_KeySettings`，真实前台两轮 PIE 走通改键、冲突、恢复默认、存档读回、关页不卡键（[证据](../../.agents/tasks/requirements-closeout/evidence/I03.md)） | [blueprint_layering_followups](../需求文档/blueprint_layering_followups.md)、[审查明细](Blueprint_Layering_Audit.md) |
| 死亡自动替补迁共享蓝图（蓝图分层 B08） | Kiro | 已完成：C++ 只发布死亡事实，`BP_PlayerState` 请求替补；联机死亡自动换人、后台死亡不切换、无人存活不假成功三类断言通过（[集中 RHI 回执](../../Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Integrated_R1/return.json)） | [blueprint_layering_followups](../需求文档/blueprint_layering_followups.md)、[审查明细](Blueprint_Layering_Audit.md) |
| 蓝图分层 Q02～Q05 资产图读回 | Codex（待统筹指定） | 未开始 | [blueprint_layering_followups](../需求文档/blueprint_layering_followups.md) |
| 角色受光与阴影（倒下帧条纹、换人拖影、正背对照） | Kiro | 已完成：条纹是 VSM 缓存残影，`BP_PC_Pyrios` Mesh `BoundsScale` 设为 11、对象阴影宽度除回倍率后修掉，联机客户端倒下帧无条纹；拖影是换人相机跳变的运动模糊。`BP_PC_Pyrios` 依赖地图里唯一带 `GGYGO.KeyLight` Tag 的平行光，目前只有 `L_Movement_Test` 有（[证据](../../.agents/tasks/requirements-closeout/evidence/I10.md)） | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「角色受光与阴影」 |
| Kevin Boss 完整组装 | Codex（待统筹指定） | 未开始制作：源码和脚本已写好未提交；第一个验收点是特效剩余 35 包 | [kevin_boss_assembly](../需求文档/kevin_boss_assembly.md) |
| 最小联机：纠正重放与特效晚加入 | Codex（待统筹指定） | 未通过：双端因内存不足从未跑通；相关源码未提交 | [minimal_multiplayer](../需求文档/minimal_multiplayer.md) |
| 消息路由失效监听清理与 SyncMarker 工具归位 | System 原会话（Codex） | 已完成并分仓 push：编译、3 项相关自动化及 Python 绑定通过，Messages／Animation 差分评审无阻塞；Cook 和历史蓝图包重载未验。[实现提交](https://github.com/WuDuElysia/GGYGO/commit/6d4fb73) | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「消息路由与 SyncMarker 工具」 |
| CR-R7 剩余候选盘点 | Codex（待统筹指定） | 未开始 | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)、[修复清单](Module_Audit_Repair_Ledger.md) |
| 死亡结束后的 Pawn 处理改由蓝图决定 | Codex（待统筹指定） | 未开始（用户 11-10 选 B） | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md)「未完成项」 |
| 动画层去掉 ZZZ 兼容层 | Codex（待统筹指定） | 未开始，等走跑起停跳变的用户回答 | [zzz_anim_compat_layer_removal](../需求文档/zzz_anim_compat_layer_removal.md) |
| 各 spec 勾选状态回写 | Codex（待统筹指定） | 未开始，等最小联机完成 | [refactor_and_squad_switch](../需求文档/refactor_and_squad_switch.md) |
| 旧 ZZZ 动画 spec 残余任务 | Kiro | 已完成：用户 11-10 决定不管，三个旧 spec 关闭 | [zzz_legacy_anim_spec_closeout](../需求文档/zzz_legacy_anim_spec_closeout.md) |

## 占用表

开工前登记，做完删除。只登记会和别人冲突的东西：要改的文件／目录、要写的共享资产、正在进行的构建。

| 负责人 | 需求 | 占用内容 | 开始时间 |
| --- | --- | --- | --- |
