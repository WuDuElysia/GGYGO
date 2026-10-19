# 动画资产生产工具安全契约（A1–A5）

当前 Pyrios 六源保存、恢复冷读、必要生产链与 Slot 保留条件见[本次证据](#pyrios-六源原地化与生产验证2026-10-10)。以下 A1–A5 是此前工具安全验证记录；该批没有执行生成器或保存动画生产资产。统筹最新完整链接成功（5个动作，3.05秒），UE冷启动新DLL后，先单独执行 RootMotionBakeLifecycle 与 KeyLightLifecycle，2/2通过；随后全10项GGYGO自动化10/10通过，零errors/warnings。Animation三项安全测试均通过，RootMotion加强断言通过。以下自动化结果不代表真实生产资产生成或玩法验收完成。

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

## Pyrios 六源原地化与生产验证（2026-10-10）

本轮仅修改 `/Game/Characters/Player/Pyrios/Animation/` 下 `Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_01`、`_01_End`、`_02`、`_02_End`、`_03`、`_03_End` 六件 AnimSequence；Main 与完整 End 的长度、采样率和 Montage 引用保持。唯一工具为 [normalize_pyrios_attack_pose.py](../../Scripts/normalize_pyrios_attack_pose.py)。没有重导入或再次 Apply/Revert Modifier，没有写曲线、Montage、ABP、Mesh 或 Skeleton。

### 处理机制与保护

每帧取当前 Mesh 参考 Root 的共同 CS XY 锚点 `(0,0)`，计算 `shift=(RootCS.xy−MeshRefRootCS.xy,0)`，同时从 BodyCS 与 RootCS 减去 shift，再分别经各自真实固定父链逆变换回 local。Body 的父链为 `Bone_Root → Avatar_Male_Size03_Pyrois_Model`，Root 属于 Model 下另一分支；不能把 Root 当作 Body 祖先，也不能分别扣各 clip 首帧，否则 Main／End 的绝对起点差仍存在。原 Root／Body Z、旋转和缩放及 Body−Root XYZ 相对姿态保留；曲线仍保存原胶囊轨迹，由原 CMC 链消费。

| 入口 | 输入 → 作用 → 输出／失败 |
| --- | --- |
| `audit` | fresh 干净自有宿主、准确六包、当前 Mesh 与 DLL → 原生只读采样真实整数键、半帧及独立 float 末端 → 原姿态／27 条完整公开曲线 DTO／authoring／保护基线。 |
| `apply` | 同脚本／DLL 的成功 audit 与真实父进程 exit0 回执 → 核当前磁盘及全部基线，先备份六原包，仅 controller 写 `Bip001`、`Root` 轨，逐包精确保存 → 保存清单与写后核验；失败保留实际状态，不自动回滚或 SaveAll。 |
| `cold` | 完整保存且正常退出的 producer 回执 → 独立 PID 只读重新加载六包 → 对比保存结果和原曲线／authoring。 |
| `recover-cold` | 六包已完整保存、producer 已结束但退出异常的真实回执 → 独立 PID 只读核保存数据，原样携带 producer 脚本身份／退出码 → 恢复冷读结果；不重写包或将异常改成正常。 |

曲线逐字段以 float.hex 等完整公开 DTO 对照；显示 metadata 使用公开原生 `export_text`，不宣称读取 protected Color 的精确数值。所有非目标骨 local pose 指纹、导入信息、AssetUserData、Modifier 快照、序列配置及六个保护依赖保持；武器 A/B 的真实 Body 后代关系与相对姿态分别核验。所有快照仅供本次离线保护／对比，不进入运行时权威状态。

### 实际资产与宿主结果

六源 60/1 的真实键数为 **102／200／82／302／85／393，共 1164 键**；每个视图共 2328 实样，包含每个整数键、半帧及单独的 float Sequence 末端。RAW 同时核 `bShouldRetarget=false/true` 两视图；只写真实整数键，不把末端 float 插值结果反写成键。

原→写后最大误差均为 component/source 单位：Root XY 残差 `1.9343e-11`，Z 变化 `9.9277e-5`，Body−Root 位移差 `1.2208e-4`，武器相对 Body 位移差 `1.5377e-4`；Q 角误差 `7.6269e-5°`，Scale 差 0。位置门槛为 0.0005、角度 0.001°、Scale 1e-6，原生 controller 的 float32 Euler 往返误差保留。保存后→独立冷读两套完整 RAW pose 快照完全一致；每源 **27 条曲线**的完整公开 DTO 与原 authoring 均一致。数值／骨轨证据不代替最终画面。

| 原生执行与原件 | 实际结果 |
| --- | --- |
| `Saved/Codex/PyriosAttackPose_20261010_R1_Audit/` | protected Color 访问真实失败；PID4592 exit0，零保存／零 dirty。 |
| `Saved/Codex/PyriosAttackPose_20261010_R2_Audit/` | audit 数据通过，零保存／零 dirty；PID38356 实际退出 `-1073741819 (0xC0000005)`，不记正常退出。 |
| `Saved/Codex/PyriosAttackPose_20261010_R3_Audit/` | 新 DLL fresh audit complete／success，PID3160 真实 exit0，零保存／零 dirty；作为 apply 基线。 |
| `Saved/Codex/PyriosAttackPose_20261010_R3_Apply/` | 实际六包保存、写后／保存后核验通过，errors 与 dirty 空；原包留在 `OriginalPackages/`。PID10232 实际退出 `0xC0000005`，保存事实与宿主退出失败分别保留。 |
| `Saved/Codex/PyriosAttackPose_20261010_R3_RecoverCold/` | PID33360 独立恢复冷读 complete／success、errors／saved／dirty 空，真实 exit0；producer10232 失败回执原样保留。`readback.json` SHA256 为 `3b820d9f647849bb4c671d47311f4f430776f9ce09e0df3b63e2bcf56c85478f`。 |

当前工具 429 行，SHA256 `174f027b1eb19ccd85a1b4f3657963963aba77b350562d8859e03cf3fad6d4cd`；R3 audit／apply 的419行 producer 脚本身份仍为 `7e49bc7b35eb1ed76407b3dcf9c9334bd445d12e337e4e6f61731cd5d1e6c914`。独立恢复冷读及后续运行正常退出不能证明此前退出异常根因已修复；未定位原因，没有强杀、改引擎、换 RHI 或伪造回执。

### 生产链与 Slot 条件结论

运行时作者在独立标准 Editor PID33004 只运行既有 `GGYGO.AbilitySystem.PlayerCombo.EndMovement.ProductionNativeNewPress`。`Saved/Logs/PyriosAttackPoseRuntime_20261010_R1.log:3648` 为 Result Success，3687 为 PASS／LastMovementStep=2；实际三 AM Main／End、移动取消与重置、回到 Walk／Run、01 无请求自然 End 和原生 PIE teardown 通过，原生 warnings 保留。日志 SHA256 `160ff71bd8d5fb4f2fa8885c63cd8f45aff42af321257f5f89214549bd86e6ef`。未改旧只读 Observer；978 个最终缓冲观察样本按 AM01／02／03 的 Main 为587／275／110、End 为3／2／1；End只有有限取消入口实样，不能当完整End逐帧姿态或自然03全程观察。15 秒截止按原生命周期注销，不作为自动视觉 PASS。

3695 的原生配置／源／Mesh 参考读回证明实际唯一 `FullBody` producer 与 Guard 要求保持。`ComponentAlignment=(0,0,50.8019981384)`，`MeshRefResidual=(0,2.0247645378,113.7967071533)`；当前 Normal01 的原生源 RootCS 为零。按现 cpp 的 full-action 公式，普通 Slot 与当前 corrector 仍差 **`(0,2.0247645378,62.9947090149)` component/source 单位**。它是原生读回加公式分析，未实际替换／删除 Slot 做 A/B，也不称世界高度 63 cm。六源原地化没有消除固定 Mesh 对齐和实际 Source／参考归一职责；本轮 **保留 ActionPoseSlot 与 Guard，ABP 写集为空**。

3699 真实 cleanup 为 game_world=null、owned_observer_active=false、content/maps dirty 空；运行组父 session14794 得到 exit0，fresh UE／SCW／UBT／LC／AutomationTool／CrashReportClient 全0后正式归还。运行后六源、六保护依赖、两 DLL 与恢复冷读身份一致。六包与工具冻结；此为约定资产／必要生产链／Slot 条件证据，不扩大为逐帧视觉、足底、全部混合／LOD、HID、Cook、Dedicated Server 或联机验收。

按 CodeConventions 核本工具调用链：离线工具仅拥有六包变更和本次保护证据，原 GA／CMC／Animation 权威链保持；脏包、基线／DLL／父链失效均明确失败，保护及退出回执有实际消费者，没有第二播放／帧调度、角色运行时特判或自动成功恢复。六包仍被既有 `.gitignore:76` 精确所属范围忽略，未放开素材目录；最终仅将验收六包和本需求文件交统筹集中 Git。
