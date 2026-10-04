# Character 渲染：冷回读与真实 PIE 验收（2026-09-29）

## 资产门禁（统筹执行）

统筹通过 ObjectTools 单独将旧标志置 false → Blueprint compile（warnings_as_errors=true）→ 单包 save，确认全部脏包为空后正常重开。PID 25008 的冷回读确认 15 项参数、三槽、OutlineMaterial、autoActivate 一致，legacy=false，is_dirty=false。

最终 BP SHA-256：`9e093db87659b1a05281f000a97017f4141521e11b93e38f6e92a9dd8705dac3`。原始 `71cef23f…4207fc` 与用户保存版 `741751e8…a1ec0a` 两份备份保留，原 legacy_baseline 不变；完整哈希链见 [迁移说明](Character_Render_Migration.md)。

本会话随后用 MCP 再读 BP CDO：旧标志 false、三槽及描边引用正确、bAutoActivate=true，参考光强10/响应0.5/输出0.65/上限1，描边宽度约0.6。BP 与原关卡均不脏，磁盘哈希与最终值一致。

## PIE 范围与对象

- 启动前：IsPIERunning=false，当前地图 `/Game/Map/Untitled`。由本会话启动标准 InViewPort PIE、预热2秒；未另放角色、未改变 GameMode/关卡/资产。
- 真实游戏生成对象：`/Game/Map/UEDPIE_0_Untitled.Untitled:PersistentLevel.BP_PC_Pyrios_C_0`。
- 只在该 PIE World 副本的 DirectionalLight.LightComponent0 修改强度；结束前恢复10。未修改 Editor World 灯、资产/CDO，未显式 compile/save。
- 这是迁移后机制验收，不是 ZZZ 原版视觉等价或同场景调色验收。

## 运行接线证据

| 检查 | MCP 实际读取 |
| --- | --- |
| 主 Mesh | CharacterMesh0 使用 Avatar_Male_Size03_Pyrois_Model |
| 表面槽0 | MID_MI_Pyrois_Body_0，父 MI_Pyrois_Body_1 |
| 表面槽1 | MID_MI_Pyrois_Body_1，父 MI_Pyrois_Body_2 |
| FX 槽2 | override=None，保持模型默认 |
| 表面槽3 | MID_MI_Pyrois_Weapon01_0，父 MI_Pyrois_Weapon01 |
| 描边组件 | 运行时 SkeletalMeshComponent_0，同一 Mesh，LeaderPoseComponent=CharacterMesh0，castShadow=false |
| 描边四槽 | 父 M_Pyrois_Outline，OutlineWidth≈0.6，OutlineOpacity=[1,1,0,1] |
| 配置/更新 | bAutoActivate=true，TickInterval≈0.1；KeyLight 始终 None，自动发现未写回显式配置 |
| 基准光向 | KeyLightDirectionWS=(-0.5,0.5,0.70710677)，KeyLightColor=白色，Visibility=1 |

MCP 的 ObjectTools 不提供 bIsActive、dynamicMaterials、outlineMesh 私有状态，本次尝试读取产生“could not be read”工具警告。表面与描边改由 Actor 组件列表、Mesh 覆盖和 MID 参数独立核对；创建成功且后续参数自动更新，证明 BeginPlay/光照 Tick 链路在运行，不把 bAutoActivate 默认值冒充直接读到了 IsActive()。未改变组件激活状态或调用 Deactivate/Refresh。

## 三个表面 MID 的主光响应

全部三个 MID 的结果一致：

| PIE 主灯强度 | SceneLightStrength | KeyLightColor |
| --- | --- | --- |
| 初始10 | 0.649999976 | 白色 |
| 2.5 | 0.324999988 | 白色 |
| 0 | 0 | 黑色 |
| 40 | 1 | 白色 |
| 恢复10 | 0.649999976 | 白色 |

结果符合 `min(1, 0.65 * sqrt(intensity / 10))`，灯关闭时没有合成白色主光。自动灯关闭后恢复可重新发现；此 PIE 没有另测显式灯、换 Mesh/第三方覆盖或遮挡体。显式灯选择与 Mesh/第三方覆盖所有权沿用此前两项渲染自动化证据；遮挡体不属于该证据覆盖范围。本次 Visibility 一直为1。

## 退出与保护检查

仅调用一次 StopPIE 停止本会话启动的 PIE；返回后 IsPIERunning=false，最后再次检查仍为false。后续 find_actors(Pyrios) 最终为空。Editor World 的原 Untitled 主灯仍为10/白色；原地图与 BP is_dirty=false；BP 磁盘哈希仍为 `9e093db8…05dac3`。未通过清脏包、SaveAll 或清理其他 World 达成这些结果。

停止后存在一项独立观察：get_current_level 报 `/Game/Map/L_Movement_Test`；首次角色查询短暂返回该地图的 UEDPIE_0 角色，随后再次查询为空。本会话没有调用 load_level、地图替换或第二次 Start/Stop；原因未确认，交统筹核对。不把原地图已恢复或其他 World 清理归为本次已验证结果，也不擅自切回关卡。

结束后仅验证无活动 PIE、活动场景无 Pyrios 和 Editor 资产未被污染；无法通过本次 MCP 逐项读取已销毁组件的 MaterialBindings/弱缓存。因此不把停止 PIE 等同于对所有内部 Release 分支的新测试，内部所有权与灯缓存证据沿用已通过自动化。

## 日志和视觉边界

此前完整 DLL 冷启动后的 GGYGO 10/10 自动化零错误零警告，是统筹独立测试结果。本次 MCP 属性 schema 查询产生 LogJson 委托类型提示，读取私有字段产生 LogScript 警告；不能称本次整个编辑器日志零警告。相关 Pyrios/Render 错误过滤未返回生产渲染错误，但这不是全项目日志清零审计。

CaptureViewport 未生成截图（工具要求缺省 captureTransform 参数）；未继续操作相机或截图参数。描边仅核对组件和材质接线，未做像素级外观判定。银甲亮度、精确 MatCap/Ramp、逐像素阴影、Body_FX01 与剑光仍不属于本次验收完成项。
