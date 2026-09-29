# BH3 Stage 导出目录清点

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
