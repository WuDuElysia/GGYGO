# Kevin Ice01 / Ice02 隔离动态验证

状态：统一完整 `GGYGOEditor Win64 Development` 构建由根会话报告成功，UHT 与两个 DLL 链接通过；本方案与观察脚本尚未在 UE 执行。统一 UE 操作由根会话负责。

## 1. 前置门槛

1. 顺序执行 Movement 派生原地动画/Profile builder → Animation Socket/Montage/ABP builder → Combat Wiring 只读预检 → `--apply` → 再次只读预检。保留各工具报告及已有资产差异。
2. 原生自动化：`GGYGO.Combat.MeleeTrace.SafetyAndCoverage`、`GGYGO.BossAI.Melee.EndReentry`，回归 `GGYGO.Combat.Combo.WindowAndBuffer`。Movement 测试由其模块提供。报告实际通过/失败，构建成功不代替测试成功。
3. 只在独立临时关卡/PIE 做验证，不改主关卡或旧 `/Game/AI/Boss/Test`。地面应可行走，保证 CMC 已落地，避免 `BeginActionMotion` 因 Falling 拒绝。每个用例可重启 PIE 得到干净状态。
4. 在该关卡放置一个 `GGYGOBossEncounter`，BossDefinition 指向新 Kevin Definition；检查生成的 State、Controller 与 Avatar 指向一致，Owner ASC/Avatar 完成初始化。Definition 的 BT 保持空；本轮以 ASC 直接请求已授予的具体 GA 类。
5. 目标必须有绑定成功的 ASC 与 HealthComponent，健康值足够、无无敌/GodMode/自动回血，碰撞响应兼容 `ECC_Pawn`。可用第二个新 Kevin Encounter 作为被动目标，BT 为空且不触发其能力；不必修改旧 Test 目标。
6. 空旷位置先播放一次，只观察 Socket 轨迹确定目标固定位置。目标放在实际剑轨迹覆盖范围，验收期间保持静止，不每帧跟随武器。Ice02 是 Prop1 驱动离手剑，不是独立弹体。

## 2. 只读观察入口

导入 `AAADocs/Scripts/observe_bh3_kevin_combat.py`，导入本身不执行 UE 操作。先从当前服务器 PIE 获得 `source_avatar` 与 `target_avatar` 对象，再调用：

```python
observer = module.start(source_avatar, target_avatar, label='Ice01_contact', seconds=8.0)
# source_state 为该 Encounter.get_boss_state()；ability_class 为新 GA BP.generated_class()
asc = source_state.get_ggygo_ability_system_component()
activated = asc.try_activate_ability_by_class(ability_class, False)
```

上述 Python 方法名按当前 UFUNCTION 推导，首次执行需确认反射可用性；如果失败，记录实际错误并修脚本，不绕过 GAS 发伤害。观察器通过真实 `OnMeleeHit`、`OnHealthChanged` 委托记录事件，用 Slate 回调记录时序快照；回调仅观察，不拥有攻击时序。8 秒到期自动解绑，也可显式 `observer.stop()`。

输出：`Saved/Codex/kevin_combat_observe_<label>_<UTC>.json`。记录 Montage 路径/位置、Trace 开关、CMC 动作状态、双方位置、目标生命、Mesh Tick/URO，以及伤害变化时的即时 Trace 状态。Slate 采样可能漏掉短窗口，精确边界应依据同步命中/生命委托及原生日志；观察器不会自动将样本判为整套验收通过。

## 3. 最小动态用例

| 用例 | 执行 | 必需证据 |
| --- | --- | --- |
| Ice01 正常完成 | 固定接触目标；只激活 Ice01 一次，等待 Montage 完成再多等至少 0.5 秒 | 激活成功；播放正确 Montage；候选窗口 45→55/60 秒；命中/血量事件在真实窗口内，同目标同窗口仅一次；最终 Trace 关闭、动作位移结束、Mesh Tick/URO 恢复 |
| Ice02 正常完成 | 固定接触目标；激活 Ice02 一次 | 同上，候选窗口 8→24/60 秒；击中来自 Prop1 动画轨迹，不宣称弹体生命周期 |
| 窗口外零伤害 | 目标位于剑轨迹范围，观察起手、收招与结束后静置 | HealthChanged 不得在 Trace 关闭时产生该动作伤害；无延迟命中。未覆盖短窗口的 Slate 样本不能单独证明零伤害 |
| 下一次动作可再命中 | 相同目标、完整结束后再次激活同一 GA | 新实例周期/窗口可再伤一次；区分“第二次攻击”与“单次重复命中” |
| 起手中断 | 在窗口开始前标记 `observer.mark('cancel_requested')`，停止该活动 Montage，令共享任务走真实中断回调 | 零伤害；Trace 与动作句柄清理；Mesh 设置恢复；可以再次激活。停止 Montage 是中断路径证据，不代替所有 GAS 取消路径 |
| 窗口内中断 | 在已经看到开窗/首个命中后停止该活动 Montage，至少再观察 0.5 秒 | 中断后不再命中、无额外血量下降，动作位移不继续；下一次 GA 可以正常激活 |
| 不可见仍更新 | 摄像机移开 Boss，让服务端 Mesh 不被渲染，再激活同一 GA | 动作期 AlwaysTickPoseAndRefreshBones/URO=false；有骨骼驱动真实命中与伤害，结束恢复最初值；不等于已完成独立 Dedicated Server 验收 |

Montage 中断可通过当前 Mesh AnimInstance 的 `montage_stop(0.0, exact_montage)`；必须传实际活动的精确 Montage，不停止其他角色动画。记录请求时刻，核对后续 Task Interrupted → GA EndAbility。独立 GAS 直接取消与死亡取消如本轮工具无法驱动，明确列为未验证，不伪称覆盖。

## 4. 位移与伤害解释

- 使用派生原地动画及 CMC MotionProfile；移动由 CMC/RMS 执行。GA 开始后记录位移起终点和有效速率，平地无阻挡时与 Profile 的累计位移经过 Mesh 朝向/缩放后的结果对比；碰墙另属 Movement 用例。不得通过 Actor 每帧 SetLocation 制造位移证据。
- 伤害期望先读实际 GA BP 配置。当前暂定 Damage=20、PoiseDamage=10；GE SetByCaller 仍经过 Execution/HealthSet。若有衰减、免疫或残血钳制，记录原因，不仅按“出现命中日志”宣称结算成功。
- 每轮用例记录地图、PIE 实例/权限、GA 类、Montage/Profile 路径、目标初始/最终血量、命中计数、最终 Trace/Motion 状态和观察报告。用例未实际执行保持待验收。
- 结束观察先解绑，再停止 PIE；不保存被测运行时变化。自动选招、Target 服务、联机、群战过滤、其他动作执行器及原游戏 HitBox 还原均不由此轮手动近战用例证明。
