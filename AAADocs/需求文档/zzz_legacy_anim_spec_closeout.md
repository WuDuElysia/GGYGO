# 旧 ZZZ 动画 spec 残余任务处理

状态：已完成。用户 2026-11-10 决定不再处理，三个旧 spec 关闭。

## 目标

决定三个旧 ZZZ 动画 spec 里还没勾的任务是关闭还是补做：

- `locomotion-gait-authority`：任务 4、5、6、8，以及可选属性测试 9.2～9.5；
- `zzz-moving-walkrun-gait`：任务 11（编辑器手工落地）；
- `zzz-anim-structure-refactor`：可选属性测试 11.2。

## 结论

- 这些任务的操作对象是旧 ZZZ AnimBP，生产已改用 `ABP_Pyrios`。用户决定不管，三个 spec 按现状关闭，不再补做。
- 去掉 ZZZ 动画兼容层（`Source/GGYGO/Animation/zzzAnim`，`UZZZAnimInstance` 仍是 `ABP_Pyrios` 的父类）是另一项需求，已交给 Codex，见 [Codex 交接](../Coordination/Handover_Codex.md)。

## 验收标准

三个 spec 的未勾项按用户选择处理完。（已满足：关闭）
