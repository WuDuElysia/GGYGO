# Locomotion Profile 与 AnimBP 接线审计

状态：`PendingUEAssetWindow`（生产迁移尚未执行）。2026-09-30 第25次只读 UE 窗口已实际读取七个源动画的四条 RootMotion 曲线 keys 与正有限时长，没有修改或保存 `.uasset`。第22次结果保留为历史。

## 证据边界

- 当前磁盘资产路径可离线检查：`ABP_Pyrios`、`BS_Pyrios_WalkRun`、候选 `DA_Movement_Default` 和七个源动画都由审计脚本校验文件存在性并计算源文件 SHA-256。
- 实际 UE 回读确认 `BS_Pyrios_WalkRun` 为 `BlendSpace1D`；有效第0轴显示名仍是 `GaitBlendY`，范围0..1、grid_num=1；Walk_Loop位于X=0、Run_Loop位于X=1，二者rateScale=1。规范轴名 `WalkRunBlendAlpha` 尚未保存。`axis_label`属性不存在的读取错误不影响实际 `blend_parameters` 成功读回；另外两轴不是1D资产的有效输入轴。
- 实际 `ABP_Pyrios_C` CDO的 `AnimSet.blend_spaces["walkRun"]` 已指向该BlendSpace；sequences的IdleLoop、WalkStart、WalkStartEnd、WalkEnd、RunEnd、TurnBack六键均读回现有源动画。状态图及引脚尚未读取，CDO映射正确不证明图内连线正确。
- 实际 `DA_Movement_Default` 七个Profile字段均成功读取且为null；七个建议Profile磁盘包尚不存在。这是实际未接线，不再是离线推测。
- 第25次实际 `unreal.AnimationLibrary` 模块/符号/API 均为ready，七源AnimSequence的 `RootMotion_Speed/DirX/DirY/Yaw` 均为fingerprinted，`animationCurveReadbackComplete=true`。时长单独读取，均正且有限；指纹仅覆盖实际对象路径、必需曲线名和time/value，不包含duration、RichCurve插值/切线/权重/外推、骨轨或图引脚，`migrationAuthorized=false`。
- `Saved/AnimRootMotion/Pyrios_RootMotion.json` 含七个片段的曲线样本。脚本分别计算当前 `.uasset` 文件指纹、导出曲线样本指纹与UE keys指纹；载荷结构及样本/key数量不同，不能直接用这些hash证明或否定源语义一致。导出 JSON 没有原始 `.uasset` 指纹；本次keys读取成功不证明源修订版相等，完整语义/来源一致性尚未核对，不能据此线性重建或迁移。

当前只读窗口证据：`Saved/Logs/GGYGO_LocomotionReadback_20260930_25.log`，实际unreal_python；10:51:49 UTC脚本成功，统筹记录UE PID35124 / exit0已退出。报告SHA256为 `1D7F2CB333AC2A3523C01B3346068948ABF0CBAB4A0A69F259B7465B931B9C66`。静态failedChecks=none且missingItems=7，不代表迁移完成。日志汇总实际0 error / 2 warning：DDC路径写入失败与 `GGYGOAbilityGroupRule` Python重名；不将常规自动化的零警告记录套用到此窗口。统筹前后核验10个目标资产、BP_PC_Pyrios、BB_Boss_Test、uproject和无关steering共14个磁盘SHA256全部不变。详细读取门禁见 `AAADocs/Modules/Animation/Animation_Asset_Readback_API_Validation.md`。

历史第22次窗口：`Saved/Logs/GGYGO_LocomotionReadback_20260930_22.log`，UE PID40072 / exit0已退出，09:21:08 UTC成功，旧报告SHA256为 `743DF05805F998B5B722D38980B678E659A87E1FBC3BFA587CDD21E11FDC29FE`。当时七个AnimSequence加载成功，但旧读取器未解析到所需库符号，全部为api_unavailable；该结果不证明曲线不存在，且已被第25次实际keys读回取代。历史DDC/Python重名警告及14项hash不变记录保留。

## WalkRun BlendSpace

当前 `WalkRun` 使用 `BlendSpace1D` 单轴：`0 = Walk`，`1 = Run`；第25次实际回读再次确认类型、样本和范围。轴的规范名称为 `WalkRunBlendAlpha`，生产资产实际仍为 `GaitBlendY`，待独立迁移修正；旧兼容字段不作为新 API 名称扩散。

历史创建脚本声明 AnimSet BlendSpace 键为 `walkRun`，在 X=0 放 `Avatar_Male_Size03_Pyrois_Ani_Walk_Loop`，在 X=1 放 `Avatar_Male_Size03_Pyrois_Ani_Run_Loop`；当前CDO与两个样本已回读相符。轴修正脚本的目标显示名为 `WalkRunBlendAlpha`，并不证明生产资产已经修正；当前图引脚仍待读取。

资产路径：

- AnimBP：`/Game/BP/Anim/ABP_Pyrios`
- BlendSpace：`/Game/Characters/Player/Pyrios/Animation/Movement/BS_Pyrios_WalkRun`
- 候选 MovementSet：`/Game/System/DA_Movement_Default`

## StopValue 与动画源

| StopValue | Movement 语义 | MovementSet 属性 | 当前源动画 |
| ---: | --- | --- | --- |
| 0 | `StartStop` | `StartStopProfile` | `Avatar_Male_Size03_Pyrois_Ani_Walk_Start_End` |
| 1 | `WalkStop` | `WalkStopProfile` | `Avatar_Male_Size03_Pyrois_Ani_Walk_End` |
| 2 | `RunStop` | `RunStopProfile` | `Avatar_Male_Size03_Pyrois_Ani_Run_End` |

该数值映射与 `ZZZLocomotionRules::ResolveStopValue` 一致。上表的动画源来自资产整理脚本里的 Stop 注释；AnimBP Stop Select 的图引脚仍待 UE 回读。

## 七个 Profile 建议

Profile 类按单个动作片段保存曲线；建议资产放在 `Animation/Movement/Profiles/`，使用 `DA_LocomotionMotionProfile_Pyrios_<动作>` 命名。MovementSet对应字段存在且第25次实际七项仍为null；建议包尚不存在，资产引用值尚未写入。

| MovementSet 属性 | 建议 Profile 资产名 | 源动画 |
| --- | --- | --- |
| `WalkStartProfile` | `DA_LocomotionMotionProfile_Pyrios_WalkStart` | `Avatar_Male_Size03_Pyrois_Ani_Walk_Start` |
| `WalkLoopProfile` | `DA_LocomotionMotionProfile_Pyrios_WalkLoop` | `Avatar_Male_Size03_Pyrois_Ani_Walk_Loop` |
| `RunLoopProfile` | `DA_LocomotionMotionProfile_Pyrios_RunLoop` | `Avatar_Male_Size03_Pyrois_Ani_Run_Loop` |
| `StartStopProfile` | `DA_LocomotionMotionProfile_Pyrios_StartStop` | `Avatar_Male_Size03_Pyrois_Ani_Walk_Start_End` |
| `WalkStopProfile` | `DA_LocomotionMotionProfile_Pyrios_WalkStop` | `Avatar_Male_Size03_Pyrois_Ani_Walk_End` |
| `RunStopProfile` | `DA_LocomotionMotionProfile_Pyrios_RunStop` | `Avatar_Male_Size03_Pyrois_Ani_Run_End` |
| `TurnBackProfile` | `DA_LocomotionMotionProfile_Pyrios_TurnBack` | `Avatar_Male_Size03_Pyrois_Ani_TurnBack` |

每个 Profile 的候选曲线来源：`RootMotion_Speed` → `SpeedCurve`、`RootMotion_DirX` → `DirectionXCurve`、`RootMotion_DirY` → `DirectionYCurve`、`RootMotion_Yaw` → `YawCurve`。第25次已读取源时长与keys；Loop周期/端点语义及完整RichCurve仍未核对，不能用keys指纹补出插值、切线、权重或外推。

## ABP 现状与迁移接线

当前 C++ 注释记录的嵌套状态机名为 `MainStateMachine`、`MainGroundState`、`LocomotionState`；Locomotion 状态名为 `NotMoving`、`EnterMove`、`Moving`、`Stop`，并有一个 `Conduit`；Moving 内层状态为 `WalkRun`、`TurnBack`。记录的变量包括 `AnimationState.bHasMoveInput`、`StateMemory.GaitBlendY`、`StateMemory.StopValue`。状态图与变量说明仍来自源码注释/迁移脚本；第25次已再次读取ABP CDO的AnimSet映射，但没有读取状态图与引脚。

后续接线仍待独立授权与 UE 验收：

1. 已只读确认 `ABP_Pyrios` 的 `AnimSet.blend_spaces["walkRun"]` 实际指向当前 `BS_Pyrios_WalkRun`，0/1两个样本正确；仍需独立修正轴显示名为 `WalkRunBlendAlpha` 并冷回读。
2. 将 Movement 只读语义帧的 `WalkRunBlendAlpha` 接到 WalkRun BlendSpace1D X 输入；保留 `GaitBlendY` 仅作旧蓝图序列化兼容。
3. 确认 Stop Select 按 `StopValue` 选择 StartStop/WalkStop/RunStop，并分别引用表中的实际源动画。
4. 完整原曲线语义及来源一致性核对通过并获独立迁移授权后，才可创建七个建议 Profile、填写曲线/时长/来源证据并接入 `/Game/System/DA_Movement_Default` 对应属性；第25次time/value指纹不能授权线性重建或该写入。
5. 回读 `ABP_Pyrios`、BlendSpace、MovementSet 和 Profile CDO；记录实际对象路径、字段、样本、曲线与指纹。完成前状态保持 `PendingUEAssetWindow`。

## 运行审计

历史审计入口（会更新报告；当前M1只允许读证据，不执行）：

```powershell
& 'C:/Users/Kaven/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe' 'AAADocs/Scripts/audit_locomotion_motion_profiles.py'
```

UE Editor Python 中可执行同一脚本。两种模式都只写入或更新 `AAADocs/Modules/Movement/Locomotion_Motion_Profile_Migration.json`，且只有内容变化时才重写该报告；脚本不调用 UE 的保存 API。

本次 `10-11-ReadAPI-M1` 仅同步本审计及读取验证记录；报告、脚本、测试、源码、Obsidian和资产均冻结。两文档交回后停止写入，不自动新增完整RichCurve/骨轨/Graph读取框架或执行迁移。

相关证据：`create_walkrun_blendspace.py`、`fix_blendspace_axis.py`、`organize_movement_assets.py`、`ZZZAnimInstance.h`、`ZZZAnimStateMemory.h`、`ZZZLocomotionRules.cpp`、`GGYGOMovementSet.h` 与 `Saved/AnimRootMotion/Pyrios_RootMotion.json`。
