# 动画资产生产工具安全契约（A1–A5）

本模块没有执行生成器或保存动画生产资产。统筹最新完整链接成功（5个动作，3.05秒），UE冷启动新DLL后，先单独执行 RootMotionBakeLifecycle 与 KeyLightLifecycle，2/2通过；随后全10项GGYGO自动化10/10通过，零errors/warnings。Animation三项安全测试均通过，RootMotion加强断言通过。以下自动化结果不代表真实生产资产生成或玩法验收完成。

## A1：RootMotionBakeModifier 的变更所有权

`URootMotionBakeModifier`在引擎保存的 applied modifier 实例中序列化本次曲线写前/写后快照、载体骨轨写前/写后变换。只分析、低于阈值、未启用对应写入的应用不会获得任何曲线/骨轨的撤销权。

- 已有曲线只改 keys，保留 flags、颜色、注释和曲线属性；撤销恢复原 keys。新建曲线在仍符合写后基线时才移除。
- 骨轨撤销恢复写前位移/旋转/缩放；正常重应用先撤销上次写入，再从原始轨迹计算，不会在归零轨迹上丢掉位移曲线。
- 撤销先检查全部写后基线，发现人工修改则不恢复任何字段，并通过引擎监视的 `LogAnimation` 报错。
- 手动指定骨骼不存在时停止；不再悄悄选择另一根骨。曲线名必须非空且互异。
- 旧版本已应用实例没有可恢复快照：旧 verify-only 撤销无操作；旧破坏性应用拒绝恢复，应从源或备份恢复后重新应用。

### 引擎两种入口的区别

UE5.8 `ApplyToAnimationSequence`重应用：引擎在旧实例的 Revert 和新实例的 Apply 周围有日志监视与事务。冲突报错后整次重应用回滚，旧 applied snapshot 保留。

UE5.8 `RevertFromAnimationSequence`显式撤销：引擎先移除 applied 实例，执行 Revert 后将其回收，**没有上述失败回滚**。冲突检查能保留当前人工资产内容，但无法保留该实例的自动撤销资格；此时必须从原始来源/备份恢复或人工处理，不能再依赖 modifier 快照。不要将“拒绝覆盖”解释成“显式撤销失败后快照仍在”。低层写入 API 在显式撤销中若失败，也不能承诺跨字段原子恢复。

## A2：KevinCombatAssetBuilder 只创建缺失资产

metadata 是来源记录，不是永久覆盖授权。已有自有且干净的 Montage、ABP、Socket 只读核验；未知所有者、脏包和不匹配契约都报错并保留。

- Montage：核验骨架、Slot、独立完整片段、停止关系与 GameplayEventWindow 起止；不重建 Section/Notify，不覆盖人工混合值和其他表现 Notify。配置与人工窗口不一致时报告差异，由作者决定如何修改。
- ABP：已有图只检查骨架、已编译状态与配置 Slot 的存在，不重新编译或删节点；这个静态检查不证明 Slot 在实际有效输出链上。缺失 ABP 才创建 StandBy→Slot→Output 三节点初版。
- Socket：已有完整自有端点保留位置，只检查父骨和非退化线段；部分缺失则停止，不自动修复半组。只有两端均不存在时才根据 UE 武器几何生成。
- 报告区分 `success`、`status=existing_preserved/created/validation_failed`、`saved_this_run`。验证成功不代表本次保存，也不代表运行验收。

## A3：KevinMotionAssetBuilder 保护已有派生产物

先只读核验所有输出的实际类型、metadata、脏包和磁盘包存在性；源序列脏包也拒绝。已有序列逐轨/逐帧对比计算出的原地姿态，已有位移曲线检查 key 数、时间、值与线性插值；Profile 检查曲线引用、时长和 `ValidateMotion`。

任何生成基线差异均保留资产并报告失败。通过核验后只创建缺失的派生 AS/Curve/Profile，仅保存本次新建对象；保留作者的 Profile 调参及派生序列上无关表现数据。已有 Profile 缺少其 Curve 时拒绝自动重接。

没有自动覆盖/修复模式。部分保存失败可能留下已保存的部分产物与未保存的新对象；报告失败，先检查并明确处理这些对象，再重试，不通过 SaveAll 强行完成。

## A4–A5：Python 批处理缓存与保存门槛

`bake_anim_rootmotion_curves.py`的缓存 schema=2：成功项绑定源记录、脚本 SHA256、曲线配置及目标包 `.uasset/.uexp/.ubulk` 的磁盘指纹。旧的片段名缓存失效；源/脚本/配置变化、重导入、包丢失均重新处理。失败和缺失每次可以重试，按上次尝试时间排序避免首批失败长期阻塞其他片段。

编辑器脏包不会烘焙或夹带保存。保存失败留下的脏对象也须先明确保存/丢弃，再允许重试。报告只把当前源与磁盘指纹匹配的成功项计入 `done`；失败/缺失/待处理均使 `complete=false`。

导入和烘焙均检查 `save_loaded_asset` 返回值，并检查磁盘 `.uasset` 存在；返回 false 不会标完成。导入脚本在保存成功前使用 `importing_not_saved`，既有资产若脏或只有内存对象则拒绝只读跳过。真实 UE 重载回读仍属于后续验收；本批离线 stub 测试不替代该验收。

## 回归与结果

已执行：

```text
python -B -m unittest discover -s AAADocs/Scripts/tests -p test_animation_asset_safety.py -v
```

8/8 通过：保存 false→失败→重试成功；缺失重试；源/脚本/配置/重导入/sidecar 变化失效；旧缓存失效；脏包保护；失败不阻塞新片段；保存 true 但无磁盘包拒绝；导入保存结果检查。全部使用 fake Unreal API 和临时目录，没有加载 UE。

统筹完整构建、冷启动执行后的结果：

- `GGYGO.Editor.Animation.RootMotionBakeLifecycle`：修复后冷启动复测通过、无错误警告；包含正常恢复/重应用、verify-only、冲突内容保护及两种入口的快照生命周期断言。
- `GGYGO.Editor.Animation.KevinPreserveAuthoredGraph`：通过、无警告；已有手工节点、表现 Notify 和混合值不变，包不变脏。
- `GGYGO.Editor.Animation.KevinMotionOutputGuard`：通过、无警告；类型、脏包、未持久化对象保护。

### RootMotionBakeLifecycle 测试修复（已复测通过）

本机 UE5.8 `AutomationTest.cpp` 的 `FAutomationTestMessageFilter` 会把匹配预期的原始错误降级成 Verbose；`AnimationModifier.cpp` 的回滚过滤器只认 Error。因此原测试的无类别前缀 pattern 改变了被测回滚行为，日志出现 `LogAnimation: Verbose`，普通内容断言不足以证明旧快照被保留。另一个问题是 `ExpectedMessages` 为 TSet，按 pattern 判等；重复注册会替换并清零计数。

修复只改测试：一次注册包含 `LogAnimation:` 前缀的完整自动化事件，精确要求两次错误。GWarn 的原始正文不匹配该前缀，保留 Error 给 Modifier 回滚过滤器；自动化 OutputDevice 添加类别前缀后才匹配预期。补充冲突时骨轨与生成曲线不变的断言；没有使用无限次数、广泛日志抑制或修改生产 Modifier。

统筹已重新完整链接、冷启动并通过单项及全套自动化复测。真实生产资产只读/创建缺失、重载回读及游戏命中/取消仍待验收；显式Revert冲突时引擎移除applied snapshot的限制保持不变。
