# 蓝图分层收尾：改键页面、死亡自动替补与资产图读回

状态：改键页面（B06）和死亡自动替补（B08）都已迁到共享蓝图并验证完成；四项资产图读回还没做，交给 Codex。审查明细见 [Blueprint_Layering_Audit](../Coordination/Blueprint_Layering_Audit.md)。

## 目标

- 改键页面从 C++ Slate 迁到可编辑的共享 UMG 页面，在真实运行里走完全部操作。（已完成）
- 出战队员死亡后的自动替补由共享蓝图决定，C++ 只发布事实。（已完成）
- 补齐审查里只差资产证据的四项读回：
  - 玩家死亡和换人过渡实际授予的类、子类默认对象和 Montage，以及正常和中止的连线；
  - `ABP_Pyrios` 的停止语义、Slot、身体侧倾和倾角连接；
  - PawnData 的默认镜头模式，以及 GA 覆盖和释放镜头的链路；
  - 音频、特效、材质实际用的共享图、通知时间窗，以及 GA、Cue、组件的引用。
- Kevin 那一项随 [Kevin Boss](kevin_boss_assembly.md) 一起做。

## 方案要点

- 改键：`BP_PlayerController` 配 `KeySettingsPageClass`（`WBP_KeySettings`，行控件 `WBP_KeySettingsRow`）。C++ 保留数据操作和原生控件桥：`UGGYGOKeySettingsPage` 提供 `ReadKeyBindingRows`、`ResetKeyBindings`、`RequestKeySettingsClose` 和蓝图事件 `OnKeyBindingResult`；`UGGYGOKeyBindingSelector::BindKeyBindingRow` 负责真实选键和 KeyUp 传递。用户设置读写、`ApplySettings`／异步存档、映射重建、LocalPlayer 身份和资源释放仍在 C++。
- 死亡替补：`UGGYGOSquadComponent` 在服务器确认是当前出战队员死亡后广播 `OnActiveMemberDeathFinished(Slot, Avatar)`；共享 `BP_PlayerState` 在同一次广播里调用 `RequestNextAfterActiveMemberDeath(Slot, Avatar)`，每次死亡最多请求一次，来源仍是 DeathAutoSwitch。广播返回后没有任何请求被消费时报 Error。`BP_GameMode` 使用这个 PlayerState。
- 资产图读回只读不改；发现对象特化逻辑写在 C++ 里时，单独列为新问题。

## 当前状态

- 改键页面：在我方可见 Editor、真实 Windows 前台、两轮 PIE 里走完全部步骤。冲突提示"S 已被「后退」使用，未修改。"；选键 Escape 只取消选择；页面 Escape 关闭；W→I 后 I 能走、W 不动；`SaveGames/EnhancedInputUserSettings.sav` 写出，第二轮 PIE 读回 I；恢复默认后 W 恢复；按住 W 穿过菜单后不残留移动；PIE 结束时页面退役；没有弄脏任何包。证据 `.agents/tasks/requirements-closeout/evidence/I03.md`，运行 `Saved/Kiro/requirements-closeout/I03/Run_R6/`。没有覆盖实体键鼠和跨进程读回。
- 死亡替补：集中真实 RHI 运行中，生产共享图的联机死亡自动换人、后台队员死亡不切换、无人存活不假成功三类断言通过（`Saved/Kiro/abilitysystem-redundancy-cleanup/Verify_R2/RHI_Integrated_R1/return.json`）；之后的角色阴影修复联机回归里 SquadSwitch 8 例也全部通过。
- 四项资产图读回没做。

## 未完成项

1. 用编辑器 Python 只读读回四项资产，写结论，并更新审查文档里对应 Q02～Q05 的状态。
2. 待用户判断、不阻塞：改键页面"恢复默认""关闭"按钮字号偏大、白字浅灰底对比度低；面板半透明，角色从背后透出。
3. 评审建议、不阻塞：`CommitNativeSelection` 在 Profile 为空、Key 无效或找不到映射时静默返回；`OpenKeySettings` 在 CreateWidget 后重验失败时没有日志。可补 Unavailable 结果或诊断。

## 验收标准

- 改键：页面可见；W 改成 I 后按 I 能移动、W 不再生效；冲突提示出现；恢复默认后 W 恢复；隔离用户目录写出存档、新会话读回；关页后不卡键。（已满足）
- 死亡替补：当前出战死亡切到下一个存活队员、后台死亡不切换、无人存活不假成功。（已满足）
- 四项读回各有结论；有对象特化写在 C++ 的列为新问题，没有就关闭该项。
