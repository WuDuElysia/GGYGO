# Pyrios 角色渲染实现（UE 5.8）

## 已接入

- `UGGYGOPyriosRenderComponent` 是 `AGGYGOHeroCharacter` 的默认子组件；`BP_PC_Pyrios` 已继承到它。
- 当角色 Mesh 名称包含 `Pyrois`，组件按模型材质槽名自动载入 `Generated/MI_Pyrois_Body_1`、`MI_Pyrois_Body_2`、`MI_Pyrois_Weapon01`，创建 MID 并更新主光方向、颜色、遮挡和相机朝向。其他角色没有匹配时不修改材质。
- 可在组件的 `MaterialSlots` 中显式覆盖槽位；换装或运行时换 Mesh 后调用 `RefreshMaterials`。
- 复制一个跟随原 Mesh 姿态的 SkeletalMesh 做背面扩张描边。`Body_FX01` 没有描边；描边宽度可在组件中调整。
- 材质是 Unlit，Emissive 中计算分区明暗、`_LightTex` 法线 RG 与蓝通道偏移、Material ID 分组色、卡通高光、边缘光、两层 MatCap 和发光。三个 MI 从原始 JSON 及项目现有贴图生成。
- `_N/_M/_A` 贴图设为线性 BC7，避免 normal-map BC5 压缩丢失 `_N.B`，并保留 `_M.A` MatCap 遮罩。

## 光照选择

角色使用 UE 的 `DirectionalLight` 作为**主光方向和颜色输入**，组件每 0.1 秒更新一次。角色接收的明暗由材质自己算，因此场景的 Lumen、Skylight、点光源和 UE 默认 Lit BRDF 不直接叠加到角色表面；环境与其他物体继续使用 UE 光照。组件可用一次可见性射线做角色级的遮挡近似。

这是接近原作风格的起点，不是原版 shader 的逐像素等价移植：目前没有逐像素级联阴影、完整五层 MatCap 混合、各向异性高光和能量 FX shader。`MAT_Pyrois_Body_FX01` 属于独立粒子溶解 shader，当前保留原槽位。最终色彩还需要在实际场景中与参考图对照调节。

## 资产与脚本

材质位于 `Content/Characters/Player/Pyrios/Materials/Generated/`：

- `M_Pyrois_Toon`、`M_Pyrois_Outline`
- `MI_Pyrois_Body_1`、`MI_Pyrois_Body_2`、`MI_Pyrois_Weapon01`

生成脚本：`AAADocs/Scripts/build_pyrios_materials.py`。验证脚本：`AAADocs/Scripts/verify_pyrios_renderer.py`。两者可用 UE 的 Python 编辑器脚本插件运行。项目 `.gitignore` 仅放行部分自研 `Content` 路径；新生成的五个材质 `.uasset` 和被改动的 Pyrois 骨骼模型位于忽略的美术目录，已在本地编辑器保存，但跨 checkout 时需通过项目资产管线一同交付。`ABP_Pyrios` 位于 Git 白名单内。

编辑器预览绑定脚本：`AAADocs/Scripts/bind_pyrios_editor_preview.py`。三个 MI 已写入 Pyrois 骨骼模型对应的默认材质槽；`MAT_Pyrois_Body_FX01` 保持原状。`BP_PC_Pyrios` 的 Mesh 没有材质覆盖，因此骨骼模型缩略图、材质球和角色蓝图视口都能直接预览 Toon 材质，无需运行游戏。生成脚本重跑时也会执行同一绑定。

## 验证记录

- `GGYGOEditor Win64 Development` 编译通过。
- 完整 UE 编辑器使用 D3D12 对 `M_Pyrois_Toon` 和 `M_Pyrois_Outline` 调用 `MaterialEditingLibrary.recompile_material`，返回零编译错误。
- 验证了三个 MI、模型槽位，以及九张数据贴图的线性 BC7 设置。
- 加载 `BP_PC_Pyrios` 时确认它继承了 `StylizedRenderComponent`。`ABP_Pyrios` 的七条旧 `Locomotion_*` 过渡调用已换为 `bHasMoveInput`、`IsAnimationRunGait()` 和 `IsTurnBackCurveDriven()` 的蓝图组合，并在编辑器中编译、保存成功；角色蓝图也再次编译成功。
- 在 UE MCP 中用临时 `ACharacter`、Pyrois Mesh 和该组件进行 Simulate：运行时材质从模型原有的深色占位材质切换为生成的白灰/蓝色 Toon 材质；把临时组件描边宽度调到 3 cm 后，截图可见反面扩张描边，证明运行时描边链路生效。默认宽度仍为 0.6 cm。
- 编辑器内验证了 Pyrois 模型资产缩略图、`MI_Pyrois_Body_1` 材质球和 `BP_PC_Pyrios` 视口，均显示白灰/蓝色 Toon 材质；脚本再次检查材质编译、贴图和默认槽位接线通过。预览截图在 `Saved/PyriosMeshAssetPreview.png`、`Saved/PyriosMaterialSpherePreview.png`、`Saved/PyriosBlueprintViewport.png`。
- 当前测试关卡的天空和自动曝光让角色偏亮；色彩需要在目标关卡的曝光、后处理设定下对照参考渲染调节。描边壳仍由运行时组件生成，编辑器静态视口目前只预览表面 Toon 材质。
- 动画蓝图修复前的文件备份在 `Saved/ABP_Pyrios_before_repair_20260924.uasset`。临时路径编译过的历史版本仅用于核对逻辑；最终修复是在原资产中替换七条节点，并保留其资产身份和其余状态机内容。
