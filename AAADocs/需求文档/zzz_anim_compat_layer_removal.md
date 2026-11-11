# 动画层去掉 ZZZ 兼容层

状态：未开始，交给 Codex。开工依赖用户对走跑起停单帧跳变的回答（见 [walkrun_turnback_production_camera](walkrun_turnback_production_camera.md)），因为两项都要改 `ABP_Pyrios`。

## 目标

把 `ABP_Pyrios` 的父类从 ZZZ 兼容层换成项目自己命名的角色动画实例，ABP 直接读 Animation 模块发布的 AnimationStateFrame，删掉旧的快照转换和没人消费的属性。走跑、起停、TurnBack 和侧倾的表现不变。

## 方案要点

- 现状：`Source/GGYGO/Animation/zzzAnim` 共 15 个文件。`UZZZAnimInstance`（继承 `UGGYGOAnimInstanceBase`）是 `ABP_Pyrios` 的父类。每帧链路是：基类发布的 AnimationStateFrame → 旧快照适配器转成 `FZZZAnimSnapshot` → `FZZZLocomotionEvents` 写进 `FZZZAnimStateMemory`（GaitBlendY、StopValue 整数）→ AnimGraph 读取。头文件自己写明 `AnimBlendX/Y`、`AnimCurveVelocity*`、`ActualVelocity*`、`bTurnBackRunOut` 没有 AnimGraph 节点消费。`ABP_Kevin_DemonBattle` 不继承它。
- 做法：
  1. 只读读回 `ABP_Pyrios` 的实际消费面：过渡、状态图、StopValue／GaitBlendY／`GetSeqByKey`／侧倾属性。
  2. 新建项目命名的角色动画实例，让 ABP 直接读 AnimationStateFrame 的走跑混合和停止类型；删掉旧快照适配器、LocomotionEvents、StateMemory 和无消费属性。
  3. 用 CoreRedirects 改名，只重绑 `ABP_Pyrios` 这一个共享资产，编译保存。
  4. 更新 `GGYGOAnimationLifecycleTest`、`StateFrameTest`，回归走跑、起停、TurnBack 和侧倾。生产机位场景复用 `Saved/Kiro/requirements-closeout/I04/prod_camera_run.py`（只在本机），读数和走跑记录里的结果对比。
- 不动：注释里说明源资产来自 ZZZ 的部分，以及编辑器控制台命令名。
- 动画状态仍由 Animation 模块持有，CMC 仍是唯一位移权威；本项不改侧倾和起停的计算方式。

## 当前状态

未开始，没有任何改动。

## 未完成项

1. 上面做法的 1～4 步。
2. 顺带补走跑记录里没覆盖的场景：实体鼠标连续转动、左转和走路档侧倾。
3. 如果用户对起停跳变选了"另开动画修复"，那个修复也改 `ABP_Pyrios` 的过渡，和本项写同一个共享资产，两项要排先后或由同一负责人做。
4. 用户偏好里"ZZZ 动画层 spec 使用 zzz- 前缀"这条若不再适用，交付时提示用户。

## 验收标准

- `Source/GGYGO/Animation/zzzAnim` 目录删除；`ABP_Pyrios` 编译无警告。
- 动画相关自动化测试通过。
- 生产机位下走跑两档侧倾、纯方向键换向、起停和 TurnBack 的读数与走跑记录一致，附连续画面。
