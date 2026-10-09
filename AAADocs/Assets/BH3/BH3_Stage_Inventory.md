# BH3 Stage 导出目录清点

> 当前检查点（2026-10-09）：P1/P3 的 FBX 几何与本轮 UE 等效材质、灯光均已保存，分别完成 77 Renderer／221 槽、97 Renderer／99 槽的地图接线、独立冷读和内场取图。P1 实际图有明显过亮高光；两图的原作光照校准、探针运行时处理与可玩碰撞仍未验收。入口与证据见[本轮 P1 交付](#本轮-p1-ue-等效场景交付2026-10-09)和[本轮 P3 交付](#本轮-p3-ue-等效场景交付2026-10-09)。原清点正文及 P3 阶段记录保留当时范围和结论；其中 P1 尚未接材质的描述是历史检查点。用户已确认 P1/P3 均不是所需目标地图，仍要求完成；其他地图候选另由资源组长调查，不把现有两图改称目标地图。

清点日期：2026-09-29。范围：`F:\AnimeStudio\Exports\BH3\Stage`，递归读取全部文件；本轮仅生成本报告，未导入资产、操作 UE、修改关卡或架构笔记，未提交或推送。

## 结论与分类

目录内只有 `Stage_KevinBoss_P1`、`Stage_KevinBoss_P3` 两组场景导出。每组均为 **一个带父子层级及摆放变换的多网格 FBX，加外置 PNG 和材质 JSON**。可以确认它们是已组合的场景几何数据，而非仅有一个独立模型块；但不能称为完整可运行关卡：灯光组件、材质 shader、部分碰撞和运行逻辑没有完整保留下来。

**名称推断**：`KevinBoss`、`P1/P3` 很可能表示 Kevin Boss 战的第一/第三阶段场景；仅凭目录名无法确认对应剧情、正式关卡名称或阶段机制。P1 的网格名主要指向建筑、平台/道具与天体背景；P3 主要指向岩石、地表、球体和天空。这里没有检出带骨骼/蒙皮的 Boss 角色，不能把目录名中的 `Boss` 当成 Boss 本体证据；本结论不覆盖 Stage 之外的 BH3 导出目录。

## 文件数量与磁盘大小

大小为文件实际字节数之和，未按内容去重；MiB = 1,048,576 字节，不代表导入后的显存或运行时内存。

| 场景 | FBX | PNG | JSON | 总文件数 | 总大小 |
| --- | --- | --- | --- | --- | --- |
| `Stage_KevinBoss_P1` | 1，7,769,216 B（7.409 MiB） | 73，36,875,205 B（35.167 MiB） | 40，184,511 B（0.176 MiB） | 114 | 44,828,932 B（42.752 MiB） |
| `Stage_KevinBoss_P3` | 1，4,362,672 B（4.161 MiB） | 14，10,781,520 B（10.282 MiB） | 10，32,144 B（0.031 MiB） | 25 | 15,176,336 B（14.473 MiB） |
| 合计 | 2，12,131,888 B | 87，47,656,725 B | 50，216,655 B | 139 | 60,005,268 B（57.225 MiB） |

子目录结构均只有场景根目录和 `Materials/`：

| 目录（相对 Stage） | 内容 | 文件数 | 字节数 |
| --- | --- | --- | --- |
| `Stage_KevinBoss_P1/` 根层 | 同名 FBX、73 张 PNG | 74 | 44,644,421 |
| `Stage_KevinBoss_P1/Materials/` | 材质 JSON | 40 | 184,511 |
| `Stage_KevinBoss_P3/` 根层 | 同名 FBX、14 张 PNG | 15 | 15,144,192 |
| `Stage_KevinBoss_P3/Materials/` | 材质 JSON | 10 | 32,144 |

本范围没有其他文件类型、独立高度图格式、关卡脚本或额外动画文件。PNG 的用途仍须由材质引用判断，不能只靠扩展名认定为高度图。

## FBX 实际结构

通过项目现有 `AAADocs/Scripts/fbx_bin_reader.py` 的只读解析器检查二进制 FBX Objects、Connections、GlobalSettings 及几何数组；两份均为 **FBX 7300**。数量按 FBX 对象记录统计，重复网格尚未按内容去重。

| 检查项 | P1 | P3 |
| --- | --- | --- |
| Model | 146：77 Mesh、69 Null | 120：97 Mesh、23 Null |
| Geometry | 77 | 97 |
| 顶点总数 | 250,002 | 108,899 |
| 三角形总数 | 199,598 | 102,461 |
| UV / 法线 | 77 个 Geometry 均有 1 套 UV 和法线 | 97 个 Geometry 均有 1 套 UV 和法线 |
| FBX Material | 39 | 10 |
| Texture / Video | 各 73 | 各 14 |
| 单个 Mesh 的材质连接数 | 1～5 | 1～2 |
| Model 父子连接 | 145，唯一根 `Stage_KevinBoss_P1` | 119，唯一根 `Stage_KevinBoss_P3` |
| 有非零局部平移的 Model | 112 | 111 |
| 骨骼 / 蒙皮 | 无 LimbNode、Deformer/Skin/Cluster 记录 | 无 LimbNode、Deformer/Skin/Cluster 记录 |
| 动画 | 无 AnimationStack/Layer/Curve | 1 个 `Take 001`、1 个 `Base Layer`，无 AnimationCurve/CurveNode |
| Pose | 1 个名为 BindPose、类型为 RestPose 的记录 | 同左 |

三角形数通过 PolygonVertexIndex 的面结束标记及每面顶点数确认，所有面均为三角形。Pose 的名称不能代替骨骼或蒙皮证据；P3 的空 Take 也不能视为可播放动作。

两份 GlobalSettings 均记录 `UpAxis=1`（Y）、`FrontAxis=2`、`CoordAxis=0`，轴符号均为正；`UnitScaleFactor=1.0`、`OriginalUnitScaleFactor=1.0`。这是文件中的单位/坐标声明，尚未通过 UE 导入后的实测尺寸校准。保留层级及各节点局部变换，勿凭源工具习惯额外乘 100。

### P1：建筑、道具与天体背景组合

已检出的 Mesh 名称包括：

- 建筑组：`Stage_KevinbossP1_City_BuildingMain_01A/01B` 至 `04A/04B`、`05`～`08`，以及 `BuildingMainB01`、`BuildingMainB02_01/02`、`BuildingA_03_Base01`～`04`。
- 道具组：`PropsA*`、`PropsA*_Destroy`、`PropsA_06_Destory`（原始拼写），以及 8 个带 `PropsB_01_ShadowMesh` 的 Mesh。其“破坏状态”“专用阴影用途”属于名称推断，尚未验证视觉与运行规则。
- 天体/天空组：`Stage_Moon_Earth`、`Stage_Moon_Moon`、`Stage_Moon_Planet`、`Stage_Moon_Sky_Star`、`Stage_Moon_SkySphere` 等。可确认这些是 Mesh；具体游戏背景含义未核实。

**碰撞缺口已确认**：14 个名称含 `Collision` 的 Model 全为 Null，且没有 Geometry 挂在自身或后代，包括 `CL_Stage_KevinbossP1_Base02_Floor_Collision`、建筑墙体及 camera collision 节点。它们仅保留层级/变换，不能作为已导出的实体碰撞网格使用。

`Directional light`、`Point light*`、GI/Reflection 等也只是 Null。所有 146 个 NodeAttribute 的类型都是 Null，没有真实 FBX Light/Camera 属性对象；节点名及位置不能还原灯光颜色、强度、衰减或反射捕获。

### P3：球体、岩石组、天空与两份碰撞候选网格

97 个 Geometry 可按实际节点归为：

| 组 | Geometry 数量 | 实际证据与解释边界 |
| --- | --- | --- |
| `Stage_KevinBoss_P3_Collision`、`..._CamCollision` | 2 | 两者均为真实 Mesh，各 201 顶点、120 三角形；是否适合玩家/相机碰撞须后续验证 |
| `Stage_KevinBoss_P3_Ball` | 1 | 7,143 顶点、13,627 三角形；名称支持“球体”推断，不代表 Boss 本体 |
| `P01`～`P10` 与 `Rocks` | 88 | 每个名称重复 8 次；8 组各含 10 个 P 节点和 1 个 Rocks，有各自层级与变换 |
| `Stage_KevinBoss_P3_Nat_Sky_01 1` 及 `(1)` | 2 | 各 14,820 顶点、9,535 三角形，属于可见网格 |
| `..._Fan_BallLight_01` 及 `(1)` | 2 | 可见 Mesh，各 176 顶点、280 三角形；名称中的 Light 不等于灯光组件 |
| `Aponia_Sky_Box`、`Sky_Star` | 2 | 背景 Mesh；不能因复用名称 Aponia 改判本场景归属 |

其余 GI、Directional light、Spotlight、Reflection_Probe 等为 Null，所有 NodeAttribute 也均为 Null。两个 Collision 网格的几何确实存在，但源文件没有提供已验证的 GGYGO Pawn/Camera 碰撞配置。

## 材质、贴图与 JSON

50 份 JSON 全部成功解析，均为材质数据，具有 `m_Shader`、`m_SavedProperties`、`m_Name`、`Name`；没有独立的场景实体/脚本 JSON。`m_SavedProperties` 保留贴图槽、纹理引用、UV Scale/Offset、浮点和颜色参数，`m_Ints` 为 null。

- 两份 FBX 中的所有材质名都能找到同名 JSON。P1 为 39 个 FBX 材质 + 40 份 JSON，额外的一份是 `Stage_NewSpaceship_Fan_PropsA_Star.json`；P3 为 10 对 10。
- FBX 的 Texture/Video 文件路径均指向本场景根层的 PNG，所引用文件全部存在；Video 中没有嵌入 Content，需保留外置贴图。
- 所有 PNG 都被本组至少一份 JSON 以名字引用。两组共有的 `111111DefaultColor.png`、`111111DefaultNormal.png` 都只有 4 × 4 像素，是默认占位资源，不能代表有完整专用贴图。
- `m_Shader.Name` 全部为空，而 `IsNull=false`，只留下 FileID/PathID；按各组 PathID 分组，P1 有 6 组，P3 有 5 组。目录中没有 shader 源码，不能据参数名恢复原着色公式。
- P1 的非空贴图槽包括 `_MainTex`、`_BumpMap`、`_MaskTex`；P3 另有 `_CausticTex`、`_Normal01/02`、`_ReflectionCube`、`_ShadowTex`。JSON 还包含发光、透明裁切、剔除、反射、溶解和颜色等参数；这些是保留下来的参数值，并非 UE 材质接线。

PNG 文件头记录的尺寸如下，均为 8-bit RGBA：

| 尺寸 | P1 张数 | P3 张数 |
| --- | --- | --- |
| 4 × 4 | 2 | 2 |
| 128 × 128 | 0 | 1 |
| 512 × 512 | 50 | 2 |
| 1024 × 512 | 0 | 1 |
| 1024 × 1024 | 21 | 8 |

DA/NA/MA 文件后缀仅辅助分类；槽位关系以 JSON 为准。尤其不要把 MA 一律接成某种固定金属度/粗糙度打包图，具体通道含义未核实。

### 明确缺口与异常

| 场景 | 证据 | 当前结论 |
| --- | --- | --- |
| P1 | `Stage_NewSpaceship_Fan_PropsA_Star.json` 的 `_MainTex` 非空，Name=`Stage_NewSpaceship_Fan_PropsA_Star`，但没有同名 PNG | 本 Stage 目录内缺此贴图；该 JSON 材质也未出现在当前 FBX Material 列表，故不等于当前 FBX 有缺失贴图路径。Stage 外是否存在未查 |
| P3 | `Stage_KevinBossP3_Nat_Ground_01_LOD0.json` 的 `_ReflectionCube`：`IsNull=false`，Name 为空，FileID=4，PathID=-6988651614736466089 | 非空引用无法按名称对应文件；本目录无独立 cubemap 格式资源，反射环境数据未解决 |
| P1 | `Stage_KevinbossP1_Fan_PropsA_01_1003.json` 的 `_BumpMap` 引用 `..._1003_DA` | 文件存在，但法线槽引用 DA 后缀资源；不能直接认定缺 NA 或自动替换 |
| P3 | `Stage_KevinBossP3_Nat_Ground_03_LOD0.json` 的 `_BumpMap` 引用 `..._Ground_03_DA1` | 文件存在，后缀不是 NA；须检查通道和原 shader 约定 |
| 两组 | 每个 Geometry 只检出一套 UV，无 Model 名含 LOD，NodeAttribute 无 LODGroup 类型 | 没有检出独立第二套 UV 或 FBX LODGroup。JSON 的 `_LOD`、材质名 `_LOD0` 不足以证明有可用 LOD 链 |
| 两组 | 有层级和变换，无原游戏脚本、触发器、导航/流送数据及有效 FBX 灯光对象 | 只能确认静态场景几何导出，不能确认原关卡视觉和玩法完整 |

P1 JSON 有 175 个显式空纹理槽，P3 有 25 个；`IsNull=true` 表示原数据中槽位为空，未将其计为丢失文件。P3 所有有名字的非空 PNG 引用均能在本目录找到。

## 后续导入注意事项（尚未实施）

1. **按场景层级评估导入。** 保留父子变换和多材质槽；不要默认合成单个 Mesh，也不要按名字去重。P1 的 Props、P3 的 P01～P10/Rocks 存在同名不同节点，需用 FBX 对象 ID 和层级路径区分。
2. **先校准坐标和尺寸。** 文件声明 Y-up、单位比例 1.0；用已知长度和可控角色确认最终尺度，再判断是否需要转换。没有计算经完整 FBX 变换规则求值后的世界包围盒，尚不能给出可信的可行走面积。
3. **单独处理可行走地面和碰撞。** P1 的 Collision 空节点不具备实体几何；P3 的两个碰撞候选网格应与可见场景分开检查，验证闭合性、表面方向、Pawn 阻挡及相机探测。不能因名称存在就宣称支持落地或导航。
4. **按材质 JSON 建立引用表。** 保留原槽位、UV Scale/Offset 和参数；先解决 P3 的无名反射引用，再评估 P1 额外星空材质是否实际需要。DA1/DA 出现在 BumpMap 的情况须人工核实，透明、发光、水/反射效果也需要各自处理。
5. **天空、阴影辅助网格与场景灯光分开评估。** 大型背景网格不应自动视为可碰撞地面；灯光 Null 只能作重建位置参考。当前目录无法直接恢复原游戏的光照和后处理效果。
6. **先做独立预览与运行验收。** 导入成功不等于可玩；仍需配置 PlayerStart、GameMode/Experience、地面碰撞并在 PIE 检查落地、移动和相机。此轮没有执行任何上述导入或运行测试。

## 清点方法与验证边界

- 文件数量/大小来自递归文件枚举；全部 50 份 JSON 通过标准 JSON 解析并交叉核对纹理名字与文件存在性。
- FBX 按对象记录及 Connections 读取，解码 PolygonVertexIndex 统计面数；实际核对了 Collision 节点的直接 Geometry 和后代 Mesh，未将 Null 名称视作几何。
- PNG 尺寸来自 PNG 文件头；未逐图进行完整像素解码、通道语义验证或画面质量评估。
- 未渲染两组场景，未进行 UE 导入、材质编译、物理/导航验证；“Kevin Boss 阶段”“建筑/岩石/天空用途”等语义只在名称支持的范围内作为推断。

## 本轮 P3 UE 等效场景交付（2026-10-09）

### UE 入口与实际范围

FBX 导入后显示为 `.uasset`，不会在 Content Browser 中继续以 `.fbx` 文件显示。几何入口如下；本轮材质与灯光工作只覆盖 P3。

| 场景 | 网格目录 | 关卡与已验证范围 |
| --- | --- | --- |
| P1 | `/Game/Environments/BH3/Stage/Stage_KevinBoss_P1/StaticMeshes/`，77 个原网格 | `/Game/Map/BH3/L_KevinBoss_P1`；[几何保存报告](../../../Saved/AutomationReports/BH3_Stage_P1_Geometry_e3574626d5e64eed9070f76230ab9a18.json)确认保存与 Registry，材质、灯光和运行冒烟未完成 |
| P3 | `/Game/Environments/BH3/Stage/Stage_KevinBoss_P3/StaticMeshes/`，97 个原网格 | `/Game/Map/BH3/L_KevinBoss_P3`；[原几何保存报告](../../../Saved/AutomationReports/BH3_Stage_P3_Geometry_ac54612cec8243a0a6bdf86a5ae94f5d.json)与以下实际材质／灯光检查点共同描述当前状态 |

P3 当前包含 120 个源 Actor、导入根 Actor 与 7 个新环境 Actor，共 128 个。源 97 个 Renderer 的 99 个槽逐源身份绑定，95 个启用 Renderer 可见，2 个源停用碰撞 Renderer 按源标志隐藏。隐藏 Renderer 不代表已关闭其 Body／查询碰撞：本轮保留原导入碰撞状态，没有执行源 Collider 政策。

P3 `Textures/` 当前有 14 个 Texture2D、3 个 TextureCube，`Materials/` 有 10 个 Material。新增 5 个实际灯光组件（1 Directional、2 Point、2 Spot）和 2 个 Box Reflection Capture，挂在各自原源节点下。先保存的 2 个 Probe Cube 与 7 个环境 Actor，在后续表面材质阶段全部只读保持；本轮没有额外 SkyLight、正式相机、PlayerStart、Boss、GameMode 或 Experience 接线。

### 来源、适配与状态归属

原 FBX 只有几何与 Null 节点；后续 `F:/AnimeStudio/Exports/BH3/Stage/Stage_KevinBoss_P3/SourceSupplement` 提供了原生 Renderer、Light、ReflectionProbe、材质与 shader 证据。以 CAB／PathID 定位源身份，未用重复显示名推断引用。原无名 `_ReflectionCube` 已按真实身份解析为独立水面 Cube；即使它与另一个 Probe 的像素相同，仍保留各自来源与资产身份。

- [不可变源计划](../../../Saved/BH3StageEnvironment/P3_Source_Plan_20261008_233000.json)记录 97 Renderer／99 槽、17 纹理、10 材质、5 shader 家族、5 灯与 2 Probe，digest 为 `c63267d0124107931cc369f921d52b4d5ce15b5260b8ea5ad54e2b7ab7d2bebf`。
- [实际消费的等效配置](../../../Saved/BH3StageEnvironment/P3_UE_Equivalent_Settings_20261009_Materials_R2.json)明确选择 UE 等效表现，并保留源贴图槽、UV、参数及每张图的颜色／采样规则。Scene_Base 使用 UE Lit，Water 使用 Single Layer Water，天空与 Fog／Additive 使用各自等效图；源 RGB 单位法线不走 UE 压缩法线重建。源为空或关闭的功能仍按源语义处理，没有补另一张资源或默认动作。
- 灯光强度单位转换、局部衰减、Spot 内锥角、水面反射增益与软深度淡出等 UE 参数显式可调。它们是已选等效策略，未当作原游戏运行时数值。后续材质配置继续引用原灯光生成检查点，未重写灯光身份标签或建第二套灯光状态。
- 原父子非均匀缩放与 UE TRS 不能可靠表达全部源仿射变换。10 个受影响网格用 `SourceAffine/` 中独立修正资产表达源几何，原 97 网格与 Actor 层级／变换保持；[几何冷读](../../../Saved/BH3StageEnvironment/P3_Map_Geometry_Cold_20261009_Resume.json)验证了 585 个相关顶点。没有用 Actor 位置特判掩盖几何差异。
- UE 5.8 原生 DDS TextureFactory 拒绝压缩 DXGI 输入，故明确使用固定版本 bcdec 的受控解码适配。BC1 解码为 RGBA8，BC6H 保留 RGB half 位并补 alpha=1；6 面 × 9 mip 的 54 个子资源按源顺序保留，无色调映射、8-bit HDR 量化、旋转或重建 mip。3 Cube 的 UE Source 原生 DDS 导出逐像素通过，两个 HDR 源均保留最大值 2.2109375 和 365 个大于 1 的 RGB 分量。Source 像素一致尚不证明运行时方向、反射卷积与原作一致。固定解码器源及 MIT 许可保留在 `Saved/BH3StageEnvironment/BCDecoder_20261009/`。

离线源解析／数学与配置生成由 [bh3_stage_environment_source.py](../../Scripts/bh3_stage_environment_source.py)负责；[restore_bh3_stage_environment.py](../../Scripts/restore_bh3_stage_environment.py)执行 UE 原生导入、严格资产读回、指定地图提交及有截止的只读取图；[test_bh3_stage_environment.py](../../Scripts/test_bh3_stage_environment.py)保留原仿射失败复现和有限契约测试。原 [import_bh3_stages.py](../../Scripts/import_bh3_stages.py)保持冻结，未建立第二套通用 FBX 导入器或运行时调度器。

### 实际保存、冷读与取图证据

各轮均使用完整独立 Editor／RHI，运行结果以机器报告中的 phase 为准；Editor exit0 本身不代表脚本成功。所有下列成功窗口均已正常退出。表面阶段只创建原缺失包，不重导已保存的 Probe 或纹理；地图阶段仅保存 P3 一次，冷读和取图均 0 保存／0 新 Actor。

| 实际检查点 | 结果与证据 |
| --- | --- |
| 2 个 Probe Cube 保存／独立 Source 冷读 | [创建 R2](../../../Saved/BH3StageEnvironment/P3_Probe_Textures_Create_20261009_R2.json)与[冷读](../../../Saved/BH3StageEnvironment/P3_Probe_Textures_Cold_20261009.json)通过，2 Cube 的全部 54 子资源严格一致 |
| 5 灯／2 Probe 关卡保存／冷读 | [灯光保存 R2](../../../Saved/BH3StageEnvironment/P3_Lighting_Apply_20261009_R2.json)与[灯光冷读](../../../Saved/BH3StageEnvironment/P3_Lighting_Cold_20261009.json)通过，源挂接、姿态、颜色和显式 UE 参数读回 |
| 剩余 15 纹理保存／Source 冷读 | [表面创建](../../../Saved/BH3StageEnvironment/P3_Surface_Textures_Create_20261009.json)与[表面冷读 R2](../../../Saved/BH3StageEnvironment/P3_Surface_Textures_Cold_20261009_R2.json)通过，14 Texture2D Source 尺寸／采样／来源及水面 HDR Cube 全子资源核验 |
| 10 材质保存／独立资产冷读 | [材质 R3](../../../Saved/BH3StageEnvironment/P3_Materials_Create_20261009_R3.json)严格只读续接先存 4 个、编译并精确新存剩余 6 个；[资产冷读](../../../Saved/BH3StageEnvironment/P3_Materials_Assets_Cold_20261009.json)核 17 纹理／10 材质的实际图、HLSL、参数、源纹理、逐输入通道与最终输出 |
| 97 Renderer／99 槽保存／独立地图冷读 | [地图保存 R2](../../../Saved/BH3StageEnvironment/P3_Materials_Map_Apply_20261009_R2.json)与[地图冷读](../../../Saved/BH3StageEnvironment/P3_Materials_Map_Cold_20261009.json)通过，源可见／hidden／cast_shadow 与完整保护状态保持；PID29704／2236 均正常退出 |
| 单张内场实际画面 | [取图 R2](../../../Saved/BH3StageEnvironment/P3_Materials_Capture_20261009_R2.json)，PID14268，`capture_passed`／cleanup=[]，原 camera／selection 实读恢复，无 dirty；已人工打开下图，确认岩环、漂浮岩石、纹理、星空与发光可见 |

![P3 当前 UE 等效内场截图](F:/ue_project/GGYGO/Saved/BH3StageEnvironment/P3_Materials_Arena_View_20261009.png)

内场取景只选择真实源 model `1934927135424`，路径 `Stage_KevinBoss_P3/Stage_KevinBossP3_Fan_Stone_04/Rocks` 的原生 Actor bounds 作为观察相机依据；其他 Actor、可见性、材质和灯光保持。相机位置 cm 为 `(-35848.671619, -26769.311032, 34175.634044)`，看向 `(-387.639891, 508.405682, 3079.036991)`。未保存正式地图相机，也未假定这是源游戏镜头。此前[壳外截图](../../../Saved/BH3StageEnvironment/P3_Materials_View_20261009.png)保留；它只显示大型外壳，不能替代内场检查。

当前 P3 地图为 342185 B，SHA256 `5CCF56324720B5B011FAC20473E37FECCCB0C4802D50662493D1B2CB65782F84`。材质接线前的[精确备份](../../../Saved/BH3StageEnvironment/P3_Before_Materials_20261009.umap)保留 333361 B／SHA256 `8B678B02A4AC218F7D3E3506A4B815F6CA83C14C26A7994F18D93A315CC376C1`。独立内场 PNG 为 1286533 B／SHA256 `1CD52C8F3353EAB203537214D6E77E02994E94DB300211D084DB07DBDDC9EB49`。

### 原失败与根因收口

原失败结果保留，没有降低断言或改成成功。压缩 DDS 导入拒绝后采用上述明确格式适配；[首次表面冷读](../../../Saved/BH3StageEnvironment/P3_Surface_Textures_Cold_20261009.json)误查运行时 GPU／LOD 尺寸后，改读引擎以 Texture Source 生成的 Registry Dimensions，R2 原源尺寸严格通过。[首次材质](../../../Saved/BH3StageEnvironment/P3_Materials_Create_20261009.json)因 Python 不能读受保护 CustomInput.Input 而 0 保存；改为标准 StructBase.export_text，逐命名输入核实际 OutputIndex 和 Mask，分别处理同一贴图 RGB／A 双输入。[材质 R2](../../../Saved/BH3StageEnvironment/P3_Materials_Create_20261009_R2.json)已存 4 个后，Fog DepthFade 接线误用成员名 InOpacity；按原生公开 pin 名 Opacity 修正，R3 通过显式失败报告续接，严格核 owner／plan／源身份／实际图后只读使用 4 个旧资产。

[首次材质地图保存](../../../Saved/BH3StageEnvironment/P3_Materials_Map_Apply_20261009.json)的 99 槽内存验证通过，但 Windows Error32 阻止落盘。原主 Editor PID38784 持有 P3 文件；统筹通过 MCP 确认 P3 干净、非 PIE 后正常切到 `L_Movement_Test` 释放句柄，没有强停或丢弃用户工作。磁盘与原备份完整，失败清理 errors=[]；新编号 R2 才实际保存成功。没有绕过 UE 保存、替换文件或借首次内存结果宣称接线已保存。

### 复杂度审核与剩余边界

按 [CodeConventions](../../Architecture/CodeConventions.md) 对本次实际调用链自审：

| 审核项 | 结论 |
| --- | --- |
| 职责／依赖 | 必要保留：源解析／纯数学、原生编辑器执行、有限契约测试分开；未改运行时模块或新增循环依赖。源配置与 shader 差异通过显式输入表达 |
| 状态／提交 | 必要保留：源计划唯一描述来源，UE 资产／地图保存结果描述实际落盘；失败报告不会发布完成。局部句柄与只读快照按当前进程生命周期清理，旧灯光身份来源不被表面新配置覆盖 |
| 防御依据 | 必要保留：create-only、精确 owner／source、提交前后 dirty 与地图 SHA、外调后状态保护和全部通道核验。取图有 120 秒截止，恢复观察 camera／selection／节流并释放 callback／keepAlive |
| 迁移残留 | 已收口：GPU 代理尺寸查询、受保护字段直接访问及错误 DepthFade pin 已替换；不存在两套同时提交的材质／地图入口。显式失败续接只读复核，未知或未列出的旧包仍拒绝 |
| 业务／扩展 | 必要保留：UE 等效策略、原灯光身份与精确 Source Cube；待验证：原作 GI／曝光、动态 shader 变体、Probe 运行时卷积与方向。没有资源缺失时的默认材质／另一 Cube 兜底 |
| 测试／构建 | 30 项离线契约通过，原仿射失败与失败清理断言保留；实际 Material 编译、资产／地图冷读和单张内场 RHI 取图通过。本轮未改项目 C++／引擎源码，未做新的项目 C++ 构建／PIE／联机／Cook／性能验收 |

当前图中的粉紫大面与较亮高光是本轮 UE 等效参数下的实际表现。人工看图只证明有用视角中的主体结构和材质可见，尚未与原作逐项校准。原游戏 GI、曝光、运行时参数提供者、SSR／Stencil 等差异及 Probe 处理仍开放；不写 `restoration_complete=true`。

源停用碰撞网格与现有导入 Body／查询碰撞是不同事实。可行走地面、Pawn／相机阻挡、PlayerStart、Boss／战斗接入及移动／镜头 PIE 冒烟仍待明确政策与独立验收；P1 材质／灯光同样不由本轮 P3 成功关闭。没有扩展历史回归矩阵，也没有把素材入库称为完整可运行关卡。

## 本轮 P1 UE 等效场景交付（2026-10-09）

### UE 入口与实际范围

地图入口为 `/Game/Map/BH3/L_KevinBoss_P1`。原 FBX 已导为 `/Game/Environments/BH3/Stage/Stage_KevinBoss_P1/StaticMeshes/` 下的 77 个 StaticMesh，原网格本轮全部只读、未重导。实际 MCP `find_assets` 也分别查到 P1 的 77 个、P3 的 97 个网格；FBX 导入后显示为 `.uasset`。Registry 存在、地图接线、冷读和画面可见分别由下列证据确认。

| 项目 | 实际保存与接线 |
| --- | --- |
| 纹理 | 74 个 Texture2D、1 个 TextureCube，共 75 个；只在既有 `Textures/` 新建 |
| 材质 | 40 个 Material，覆盖全部实际源 Renderer 引用；只在既有 `Materials/` 新建 |
| 源节点与 Renderer | 146 个源节点对应 Actor，77 个 Renderer／221 个材质槽；69 个可见、8 个隐藏，含受停用父层级影响的 Renderer |
| 灯光与探针 | 1 Directional、26 Point、1 Box Reflection Capture，共 28 个新环境 Actor，挂接原源节点 |
| 地图范围 | 唯一改包为 P1 地图；146 个源 Actor、1 个既有导入根 Actor、28 个环境 Actor，共 175 个 Actor |

未新增 SkyLight、正式镜头、PlayerStart、Boss、GameMode 或 Experience。P1 无本轮仿射修正目标，原 77 网格字节及哈希保持；P3 地图也保持原已验检查点。源碰撞和原导入查询状态均未修改。

### 来源、适配与状态归属

[不可变源计划](../../../Saved/BH3StageEnvironment/P1_Source_Plan_20261009.json)的 digest 为 `062716a2227fa93535ee0a43644e5c5f73cae6759f94aec6cab3061be6391b84`。实际输入为[完整等效配置](../../../Saved/BH3StageEnvironment/P1_UE_Equivalent_Settings_20261009.json)，settings digest 为 `6315ac3584e8b9c36a38d749a52126f91408f16c0c529c1cc1788e84b86bd084`；Raw 配置不是本轮原生执行与续接输入。源解析、编辑器执行和有限测试沿用上节三件工具，未改原 FBX 导入器、项目 C++ 或引擎源码。

- 原 73 张 PNG 的 native 元数据按准确 CAB／PathID 回读，来源见 `F:/AnimeStudio/_work/bh3_stage_supplement_20261008/P1TextureMetadata_20261009/native_texture_metadata_index.json`。补充包提供额外 Star 纹理与 Reflection Probe Cube，不能用同名星空图互相替换。源空槽、失效资源和未选择的模式不会产生默认材质或替代图。
- 源 FBX 有 39 个材质定义，实际 native Renderer 使用 40 个材质。唯一明确差异是 model `1580589350160`，路径 `Stage_KevinBoss_P1/Stage_KevinbossP1_Fan_SkyBox/Stage_Moon_Sky_Star` 的槽 0：FBX 指向 `Stage_KevinbossP1_Fan_SkyStar`，native Renderer 指向 `Stage_NewSpaceship_Fan_PropsA_Star`。计划保留双身份与原 FBX 槽名，实际接线以该准确 native 指针为权威；没有泛化忽略其他身份差异。
- 6 个 shader 家族按显式 UE 等效图表达：Scene_Base 34 个、Scene_Air_LightMap_Matcap 1 个、Additive 2 个、AirEffect_SkyBox 1 个、FogEffect_Texture_Additive 1 个、FogEffect_Texture_Additive_Soft 1 个。保留源 UV、参数和非空贴图槽，差异写入配置与资产元数据；未声称原游戏 GI、动态参数提供者或完整 shader 运行时已复原。
- `Stage_KevinbossP1_Fan_PropsA_01_1003_DA` 同一源身份同时用于 MainTex 和 BumpMap。保留一个线性采样纹理，Main RGB 在材质中显式解码颜色，Bump 使用原通道，不另补一张 NA 或创建竞争副本；原游戏导入器语义仍待校准。
- Probe Cube 沿用受控 BC6H 解码适配，保留 1024 尺寸、6 面、11 mip 与全部 66 个子资源，包括 1×1 尾 mip。RGBA16F 运输保留源 half 位、补 alpha=1，不生成 mip 或量化为 8-bit；HDR 最大值 7.8671875，761809 个 RGB 分量大于 1。新 Editor 的 native Source DDS 导出全部子资源逐像素一致。此结果仍不证明 Cube 运行时方向、卷积或原作反射一致。

### 实际保存、冷读与取图证据

各轮使用独立完整 Editor／RHI、既有 DLL 和新结果路径；均已正常退出。本阶段没有新项目构建或热换 DLL。结果以机器报告的 phase 为准，首次纹理脚本失败即使进程 exit0 也仍记为失败；启动时既有 Smoke 日志错误未称为全日志无诊断。

| 实际检查点 | 结果与证据 |
| --- | --- |
| 原生预检与原图几何基线 | [预检](../../../Saved/BH3StageEnvironment/P1_Complete_Preflight_20261009.json)、[几何基线](../../../Saved/BH3StageEnvironment/P1_Geometry_Baseline_20261009.json)通过；146 源节点／147 原有 Actor、77 网格绑定，0 保存／0 新 Actor |
| 75 纹理保存 | [首次真实失败](../../../Saved/BH3StageEnvironment/P1_Textures_Create_20261009.json)保存 60 个后拒绝错误 sRGB；[R2](../../../Saved/BH3StageEnvironment/P1_Textures_Create_20261009_R2.json)严格只读核这 60 个并新存剩余 15 个，`textures_passed`，PID39648 |
| Texture2D 与 Cube 独立冷读 | [74 Texture2D](../../../Saved/BH3StageEnvironment/P1_Surface_Cold_20261009.json)、[1 Cube](../../../Saved/BH3StageEnvironment/P1_Probe_Cold_20261009.json)均通过，PID19988／38844；Cube native Source 的 66 个子资源 `source_pixels_exact=true` |
| 40 材质原生编译／115 包冷读 | [材质创建](../../../Saved/BH3StageEnvironment/P1_Materials_Create_20261009.json)40 个均编译无诊断并精确保存，PID5920；[资产冷读](../../../Saved/BH3StageEnvironment/P1_Assets_Cold_20261009.json)核 75 纹理／40 材质的实际图、HLSL、参数、逐输入通道与输出，PID34944 |
| 27 灯／1 Probe 保存／冷读 | [灯光保存](../../../Saved/BH3StageEnvironment/P1_Lighting_Apply_20261009.json)、[灯光冷读](../../../Saved/BH3StageEnvironment/P1_Lighting_Cold_20261009.json)通过，PID16156／16524；准确挂接、姿态、颜色、显式 UE 参数与原几何／碰撞保护保持 |
| 77 Renderer／221 槽地图保存／冷读 | [地图保存](../../../Saved/BH3StageEnvironment/P1_Materials_Map_Apply_20261009.json)、[整链冷读](../../../Saved/BH3StageEnvironment/P1_Environment_Cold_20261009.json)通过，PID32116／39304；69 可见／8 隐藏及 cast_shadow 按源标志，115 包、灯光／探针与完整保护状态核验 |
| 内场实际画面 | [内场取图](../../../Saved/BH3StageEnvironment/P1_Materials_Arena_View_20261009.json)，PID30204，`capture_passed`／cleanup=[]；原 camera／selection 实读恢复、无 dirty、0 保存；人工打开下图，确认圆形平台、周围装饰和天空可见，高光明显过亮 |

![P1 当前 UE 等效内场截图](F:/ue_project/GGYGO/Saved/BH3StageEnvironment/P1_Materials_Arena_View_20261009.png)

内场取景仅使用 active Scene_Base 的源 model `1580591283680`，路径 `Stage_KevinBoss_P1/Stage_KevinbossP1_Fan_PropsA_01/PropsA01` 的原生 bounds。观察相机位置 cm 为 `(-7338.154152, -16492.336381, 10825.265591)`，看向 `(3376.454933, -8250.329393, 1429.377625)`；未保存地图镜头或更改 Actor／显隐／材质。此前[全景图](../../../Saved/BH3StageEnvironment/P1_Materials_Overview_20261009.png)相机位于大型天空球外侧、主体被遮挡，原图与报告保留，不能替代内场检查。内场 PNG 为 1251516 B，SHA256 `8CFD34C1DEF36073CC0410BF7848A735ECC8B7B5D9C0784583AFF08AF3050EB9`。

当前 P1 地图为 451619 B，SHA256 `441854A6DEC87FEF56264C05B37FA5DED2F86E32FF0B988423A5AB0A65694B2B`。两次提交前的准确备份保留：[环境前](../../../Saved/BH3StageEnvironment/P1_Before_Environment_20261009.umap)，376226 B／`BC2A77C86AAB8D79916F7DA19065AD5B9B76CF4F8869F4A785C0BCF3D69ADB56`；[材质前](../../../Saved/BH3StageEnvironment/P1_Before_Materials_20261009.umap)，440555 B／`582757FFB15B1F132FE989B12A604AEDF810E2C940FEBA41434ACBE8F0383440`。原 77 网格逐文件字节／哈希未变，P3 地图仍为 342185 B／`5CCF56324720B5B011FAC20473E37FECCCB0C4802D50662493D1B2CB65782F84`。

### 原失败与根因收口

首次纹理失败对象为 `T_Stage_KevinbossP1_Fan_PropsA_02_Crystal_DA`。原 PNG 是 512×512 RGBA8；UE 自动识别为法线图，旧提交顺序先设 sRGB、后改压缩模式。引擎 `Texture.cpp` 在 Normal 压缩模式下清零 sRGB，之后切到 Default 不会自动恢复，导致严格 sRGB 读回失败。修正先提交压缩模式、再提交明确 sRGB；没有改 PNG、颜色策略或断言，没有把错误纹理当正常资源保存。

续接只消费同 plan、完整 settings、mode／failure_phase 的实际失败报告，且要求无地图保存或 Actor 创建。已记录的 60 个包逐个核 owner／plan／源身份、纹理解释标签、原生属性和 clean，全部只读；剩余 15 个仍 create-only。外来、重复、未记录的既有包及旧配置报告均拒绝。原失败与日志保留；两件工具窄修由唯一原作者完成后冻结，后续资产执行使用同一冻结版本。

### 复杂度审核与剩余边界

按 [CodeConventions](../../Architecture/CodeConventions.md) 对受影响调用链审核：

| 审核项 | 结论 |
| --- | --- |
| 职责／依赖 | 必要保留：源解析／等效配置、原生执行、有限测试沿用现有分工；未增运行时状态或模块循环依赖 |
| 状态／提交 | 必要保留：原 plan 描述唯一源事实，UE 保存描述实际资产状态；失败报告是续接证据，不代替原生读回或发布成功。两次地图保存各有准确备份 |
| 防御依据 | 必要保留：真实 Normal 自动识别失败、create-only、来源／dirty／原图保护；旧 60 包不重导或重存。观察取图沿用截止与清理契约 |
| 迁移残留 | 已收口：错误 sRGB 提交顺序原位替换，未保留双路径或成功兜底；明确失败续接之外的既有包仍拒绝 |
| 业务／扩展 | 必要保留：准确源身份、显式 UE 等效策略、源显隐与空槽；待验证：原作 GI／曝光、运行时参数、Cube 方向及 Probe 处理，没有默认资源掩盖缺口 |
| 测试／构建 | 37 项离线契约通过，保留原 sRGB 失败及非法续接断言；真实材质编译、独立资产／地图冷读和内场图通过。未做新 C++ 构建、PIE、联机、Cook 或性能验收 |

本次只关闭 P1 的等效材质／灯光／精确地图接线与有用视角可见检查点，不写 `restoration_complete=true`。明显过亮高光仍需视觉校准；可玩碰撞、合法出生点、PlayerStart／Experience、Boss 待机和战斗接入、实际 CMC 落地及镜头行为未验。

P1 补充包的 13 个 MeshCollider 中，12 个有真实网格引用，均 `m_Enabled=true` 但 `hierarchy_active=false`；GI_Volume 的另一个网格引用为空。补充包已有 12 份 CollisionMeshes OBJ，未导入 UE。保留源停用状态与为 UE 演示明确启用支撑是不同选择，不能从有 OBJ 推导当前可走，也不能把空 GI Collider 当地面。P3 同样保留上节碰撞边界：原 simple 胶囊查询未命中，complex 命中 CamCollision 只属只读几何诊断，不能代替真实 CMC 落地验收。下一可玩链须先明确支撑／Camera 政策和资产所有权，当前没有这条链的资产或工具写权。
