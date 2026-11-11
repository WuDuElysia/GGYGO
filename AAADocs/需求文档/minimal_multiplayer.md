# 最小联机：纠正重放与特效晚加入

状态：六个正常场景及活尾专项均完成；源码编译、17 项脚本回归、D3D12 双端数值断言和要求的客户端画面检查通过。Movement 核心差分评审无阻塞，FX 活尾问题已修复并完成定点复核与运行验证。负责人为 AbilitySystem 原会话。

## 目标

在监听服务器、预测 owner 和独立观察客户端使用真实渲染的条件下，验证原激活的纠正重放、初始输入不可用、动作自然完成，以及 FX 首次相关性、闭窗首次相关性和同连接重获。

## 方案与接口

- `WaitComboInput` 收到原激活的有效 Initial 后清除原生必需远端数据等待；后续攻击为可选输入。初始不可用仍走同 Spec／ActivationKey 的可靠取消并精准归还。
- PlayerCombo 在 GA 原生取消期间关闭 Montage Task 的 native OnCancelled 回调，避免再次请求 Cancel；Task 自身失败与 BP 通知保留。
- 动作 RMS 取消时立即清零贡献，转为待移除的 Additive，保留原 LocalID 供原生匹配与清理。已有映射可跨取消状态匹配，但原配置及资源仍须一致；自然末段只在原 GA 有效且原 Task 自然完成时有限 drain，最后 XYZ／Yaw 必须实际消费。有效 Authority End 立即归还同激活的本地预测资源。
- FX 发布归 `MontageFXReplicationComponent`／`MontageFXPublicationOwner`，资源持有者关闭自身 lease。远端组件在原 Solo Tick 中持续以 BeginServerTime 求 DesiredAge；依赖就绪且实际 Controller Age 达标才显示，同帧同步原 Niagara 场景代理的渲染状态。追赶不足再次隐藏；有效活尾恢复原时间模式、清 seek 并恢复原渲染值，由原 Tick 自然结束。
- Editor 的 `PlayerActionObservation` 提供连续复制收件、原通道读回、原 World／Locomotion 只读快照和可选分页。结束时分页合并与原无参全量比对；观察不推进或替换生产执行。
- requirements 9.5 的纠正范围是 owner／Authority 的拒绝、原 basis 重放、新段、真实末段及精准退役。统筹与 Movement 确认：当前模拟代理没有独立 action RMS Apply；不为校验器扩建复制链。代理胶囊沿 ReplicatedMovement／CMC smoothing，动作姿态沿 GAS ReplicatedAnimMontage；RemoteMotionPose 只补普通 Locomotion 单 Sequence。代理 imported RMS 与单独复制帧配对保持未覆盖，不由其它链的存在代签。

## 验证入口与环境约束

入口是 `AAADocs/Scripts/run_minimal_multiplayer.ps1`、`observe_minimal_multiplayer.py`、`verify_minimal_multiplayer.py`；断言、原输入、状态通信分别位于对应的 `minimal_multiplayer_checks.py`、`minimal_multiplayer_input.py`、`minimal_multiplayer_status.py`。

运行使用自有两个 D3D12 离屏 Editor：同进程监听服务器和预测 owner，加独立观察客户端。脚本走原生产数字键装配，网络配置读回只允许 lag，FrameDelay／Bloat／Loss 为零。输出与 UserDir 隔离；启动前检查 Editor／UBT 冲突和实际物理／提交余量。不开 SaveAll，不改用户资产。

各实际 PIE World 在输入前用 `CreateForSystemAssets` 等待原三段 Combo 的 9 个 Niagara System 材质准备完成。自有 Editor 关闭 Slate UI 节流及后台 Level Editor 实时绘制，浮动 PIE 为约 640×360。以上是本需求的非冷加载夹具，不构成冷首击验收。

FX 用原 Normal03 三连的下劈／地面单元，原可见点约为 Age 0.8 秒，不延长资产或通知。截图在可见点前两原生步长预约，每张按真实 Draw 帧的实际 Age 与复制状态核验。重获使用原生进程内 `RelevantTimeout=0.05`，原通道实际关闭后恢复 cull 并 `ForceNetUpdate`；客户端独立核 Close／CleanUp、同连接同 NetGUID 的新代理和旧资源退役，不修改生产默认等待时长。

## 验证结果

证据根目录：`Saved/Codex/MinimalMultiplayer_20261111/`。各正常场景的 `checks.json` 保留数值结果，画面结论列在下表；原失败数据保留，不改写为通过。

| 场景 | 实际结果与证据 |
| --- | --- |
| 只按攻击 | `Run_03/attack_only/checks.json`：同原 Montage／Task／GA 自然结束，真实 Native 步长及最后 XYZ／Yaw 消费，资源清空。 |
| 初始输入不可用 | `Run_06/initial_unavailable/checks.json`：同激活唯一可靠取消链，无完整 TargetData、无起段 RMS，原任务及 GA 清空。 |
| 纠正重放 | `Run_28/correction/checks.json`：预测段 1 拒绝 → Mode2 原 basis 重放段 0 → 新段 1；两端原动作自然完成，原普通 WalkStop 也自然结束，最终公开资源清空。 |
| 闭窗首次相关性 | `Run_12/closed_first/checks.json`：完整空活动状态、无同键重建；客户端 PNG 已查看，无补播。 |
| 活窗首次相关性 | `Run_26/live_first/checks.json` 与 `observer/client_1.png`：同帧实际 Age 约 0.8333，目标约 0.8563；实际图可见下劈弧与地面层。 |
| 同连接重获 | `Run_31/reacquire/checks.json` 与 `observer/client.png`：旧通道实际 Close／CleanUp，新代理仍属同连接同 NetGUID；旧资源归还后新 generation 推进；同帧 Age 约 0.8333，实际图清楚显示下劈弧和地面亮光。 |
| 追赶隐藏后的活尾专项 | `Run_29/live_first/checks.json` 与 `observer/client.png`：仅降低原组件公开 seek CPU 预算，原实例 reached 后实际落后并隐藏；正常闭窗恢复原时间模式与渲染，实际尾图可见地面余光和粒子，随后自然完成与销毁。此试次单列为回归，不代替正常活窗验收。 |

最终源码编译：`build_tail_observation.log`，Succeeded。17 项相关 Python 回归、Python／PowerShell 语法及差分检查通过。全部自有 Editor 正常退出；当前无 UE／UBT 占用。

## 未验证边界

Cook、性能、物理输入设备、前台焦点切换、完整丢包／高延迟矩阵、其它角色与全部动作、生产默认相关性等待时长，以及模拟代理独立 RMS 导入执行未验。Obsidian Canvas 已检查 JSON、ID、边端点与链接，未进行原生 Obsidian 渲染检查。

## 验收标准

- 同原激活完成预测拒绝、原基准重放、新接受段与精准清理。
- 初始不可用可靠取消；独立只按攻击以原资源自然完成，不能用退出取消替代。
- 三个 FX 相关性场景都有完整数值证据和符合预期的真实客户端画面。
- 结构文档只写当前职责与接口，流程图只写实际触发、调用和结果；任务状态与验证结果留在本记录。
