# 模块会话路由

用于主会话分发任务，避免重复创建同名长期模块会话。项目目录：`F:\ue_project\GGYGO`；Host：`local`。尚未登记的模块须先查找既有会话，不能直接视为不存在。

| 模块 | 保留会话标题 | 唯一派发 threadId |
| --- | --- | --- |
| Camera | GGYGO｜Camera 模块 | `01a0e5b5-4490-7881-b890-15d19208ca68` |
| AbilitySystem 通用基础 | GGYGO｜AbilitySystem 模块 | `01a0e5b5-1b3a-7783-a667-e8e38d7a72fb` |
| Input | GGYGO｜Input 模块 | `01a0e5b5-276c-7ea0-b469-4797f5059e2b` |
| Character 装配与生命周期 | GGYGO｜Character 模块 | `01a0e5b5-36b6-7c81-b10f-f10d5758423d` |
| Animation 运行时 | GGYGO｜Animation 模块 | `01a0e5b5-766b-7ac0-9edf-254f3964f543` |
| Animation 资产生产 | GGYGO｜动画模块 | `01a0ebeb-4283-79b1-8ecc-9edae131297b` |
| Movement | GGYGO｜Movement 模块 | `01a0e5b5-83e6-70b3-9e67-c9e8547586a4` |
| Teams | GGYGO｜Teams 模块 | `01a0e5b5-910c-71e3-a75c-b17c22fea33e` |
| GameFeature | GGYGO｜GameFeature 模块 | `01a0e5b5-9dc9-7b32-8aaa-3316137b0cc9` |
| BossAI | GGYGO｜BossAI 模块 | `01a0e5b5-d01a-7210-8b91-ac4716a8b07e` |
| Combatants | GGYGO｜Combatants 模块 | `01a0e5b5-de0e-7692-85ad-5e642f1e9d28` |
| System | GGYGO｜System 模块 | `01a0e5b5-eb47-7970-ba89-4b5f90919296` |
| Combat 命中查询 | GGYGO｜Combat 模块 | `01a0e5b5-f763-78c1-86c8-fa760a9f2100` |
| Combat 玩家动作/GA 集成 | GGYGO｜战斗模块 | `01a0ebc0-8780-7f92-86d0-2f028f08f147` |
| Physics | GGYGO｜Physics 模块 | `01a0e5b6-24d1-7823-80c7-9579172807aa` |
| Messages | GGYGO｜Messages 模块 | `01a0e5b6-3230-7032-8acd-b36e97cc52ef` |
| 地编与测试场景工具 | GGYGO｜地编模块 | `01a0eb96-b42e-7563-8880-1fb91b7f90e1` |
| Character 渲染子模块 | 还原角色渲染管线 | `01a0d21a-84e2-7f00-808d-1618fa4dd2b8` |
| 资源解包（独立工具工作线） | GGYGO｜资源解包组长 | `01a0ed0f-fcd8-7b02-bb03-5bc01e0e2977` |
| Audio 音效 | GGYGO｜Audio 音效模块 | `01a10014-f4d3-7f91-a84f-da95248c8fc3` |
| FX 特效表现 | GGYGO｜FX 特效模块 | `01a10c8b-2eb6-7d53-880e-a5c7f6caeda7` |

以上是既有会话路由，不是允许同时修改共享文件。Animation 与 Combat 的两个入口按运行时/资产、查询/动作子职责区分；需要共享接口变更时由统筹指定一个写入批次。全模块修复期间以 `Module_Audit_Repair_Ledger.md` 的租约为准，未收到批次授权的会话保持只读。

2026-10-05用户批准跨模块牵头制：每个需求由一个既有组长汇总相关模块方案、收敛接口分歧并交付整条链路，参与组长保持自己的实现和文件所有权。当前GAS生命周期由AbilitySystem牵头（参与战斗/BossAI/Input夹具），移动首次同步由Movement牵头（参与Input/Hero）。允许该需求范围内的组长沟通，以主会话真实用户批准为授权依据；不以会话转发代替授权、不跨模块抢写、不创建子代理。检查点按完整可运行链路设置，统筹批量构建/必要冒烟及最终验收，不逐小步骤开构建门禁。

## 组长直接执行（模型与Fast默认更新于2026-10-04）

资源解包组长是用户明确新设的独立工作线，实际工具范围为 `F:\AnimeStudio`，只用 CLI，不用 GUI。首次任务：调查 ZZZ 的 Pyrios/Pyrois 特效和音效能否发现、关联与导出，优先复用既有导出/索引，必要时仅独立目录小样本验证。该会话不取得 GGYGO 运行时修复文件或 UE/资产导入权限，不受无关运行时批次等待限制，也不得覆盖既有导出。是否可提取、是否能在 UE 还原表现分别报告，不能把调查派发写成资源已导出。组长可按下列规则拆分明确任务；后续解包需求复用此会话。

历史设置事实：2026-10-03此前向原19个长期组长逐一发送 `gpt-6.1-sol / ultra`，19次成功，保留当时实施记录。本轮用户提供协作规则指定 `gpt-6.1-sol / xhigh`，后续任务派发显式遵循xhigh，不冒称又批量修改了未派发会话。新增Audio和FX已显式使用xhigh；路由现为21个。模型设置不扩大租约、不恢复子代理。

2026-10-05用户明确新建「GGYGO｜FX 特效模块」，在既有GGYGO项目原目录长期接手特效表现；首轮仅完整阅读`AAADocs/Modules/Character/Rendering/ZZZ_FX_Handoff.md`及相关只读上下文，交回管线、现状、缺口与下一步建议，无源码/脚本/资产/笔记写权，不操作UE/PIE/build/Git。角色Toon与既有身体渲染仍由Character渲染组长负责，原始解包由资源解包组长负责，Animation/GA/Combat的时序、生命周期和命中职责不迁移给FX；后续实现按实际需求协调唯一文件作者与公共窗口。该会话已创建，不等于文档全部事实已核实或特效实战已验收。

历史统一设置（2026-10-03，用户“全部会话开fast和xhigh”）：对以上20个长期模块会话逐一调用派发接口，显式`gpt-6.1-sol / xhigh`，20次成功。本机`C:/Users/Kaven/.codex/config.toml`曾保存默认`service_tier="fast"`、`model_reasoning_effort="xhigh"`及`[features].fast_mode=true`，当时回读一致，本机Codex只读解析返回`fast_mode stable true`。现有派发接口没有逐会话Fast字段，未核实会话自己的Fast覆盖项，不能据此宣称全部正在运行的请求已切Fast；统筹当前请求也未强制重启。后续派发保持模型与xhigh，任务、原租约、冻结/只读边界及取消子代理约定不变。证据：`Saved/ValidationRecords/AllModuleChats_Fast_Xhigh_20261003_Result.json`。

最新设置（2026-10-04，用户“fast模式都关一下”）：本机 `C:/Users/Kaven/.codex/config.toml` 已回读 `service_tier="default"`、`[features].fast_mode=false`，Codex只读解析为 `fast_mode stable false`；模型与 `xhigh` 保持不变。已向路由20个长期组长逐一发送关闭Fast通知，20次成功，覆盖此前开启约定。通知接口没有逐会话service-tier字段，未证明各会话已有覆盖项或运行中请求即时改变；不强制重启，不把通知成功冒称实际请求档位核验。原任务、精确租约、统一编译/UE窗口与无子代理规则不变。证据：`Saved/ValidationRecords/AllModuleChats_FastOff_20261004_Result.json`。

Audio一文件步骤已交回冻结（2026-10-03）：`AAADocs/Modules/Audio/Audio_Contract.md` 已保存，统筹全文核对/hash接受，SHA256 `12C4100B43C1F46F2C21D25CD3AEB52CC6AEC8C62EB098840E68E9F145DB2F6B`。负责配置／播放资源／自身清理，不重复Notify时序、Combat命中或GAS生命周期；来源已包含Pyrois映射及Kevin Bank位置，精确帧未知。SoundWave／Montage Notify仅计划，未导入或UE验证；本一文件写权已关闭，后续资产由统筹门禁。

取消临时子任务/子代理机制，覆盖旧的 `gpt-5.6-sol` 组长与 `gpt-6-luna / max` 铺量方案。分析、拆分、实现、测试、审查和局部笔记由组长直接完成，不再创建或唤醒实现子代理，也不另建临时实现会话。已有代理先停止、确认不再写入并交回实际改动后由组长接管原租约；保留历史和改动，不推倒已验证实现。

2026-10-05最新协作约定：统筹理解需求并按模块分发，协调跨模块依赖/文件冲突和验收；组长自主决定模块内技术方案、拆分、实现、自审和验证，不再逐方法/逐内部步骤申请统筹审批。已有文件归属、唯一写入者及共享接口冻结继续有效，1～4文件仅作内部拆分参考，不作机械许可门槛。完整需求开发并完成约定测试后集中同步架构笔记；普通预检/交接不再默认新建JSON或重复哈希快照。取消子代理、模型/Fast设置及统一编译/UE/Git门禁不变；已有优化继续，未分配任务的会话不自行开工。具体规则见`AGENTS.md`与`Module_Repair_Parallel_Schedule.md`。

## Camera 重复会话整理（2026-09-29）

- 保留会话已有鼠标视角接线、CameraMode 蓝图资产、PawnData 引用及 PIE 验证历史。
- 重复会话 `01a0ec02-73ec-79b2-80d9-7cce0dcc314f` 仅做了跑动转向/镜头侧移只读评审，没有代码或资产改动。评审摘要与待办转交保留会话后归档，原始历史不删除；不再向重复项派发任务。
- 该效果仍等待用户提供视频/图片并确认细节。候选方案不是批准实现：Movement 管权威转向，Camera 只读转向信息并计算镜头侧移；不得因会话整理而开始实现。
- 最新源码、资产和架构笔记优先于历史聊天里的旧配置与旧验证结论。
