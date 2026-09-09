---
name: zzz-anime-assets-cli
description: 当任务涉及 Zenless Zone Zero（ZZZ）模型、骨骼、AnimationClip、动画、材质或其他美术资产的解包、导出、转换、筛选和完整性核对时，优先调用 F:\AnimeStudio 中已编译的 AnimeStudio.CLI；适用于 ZZZ Live/测试版本资源、动画导出、FBX 导出前置处理，以及导入 Unreal 后的源资产对照。
compatibility: 'Windows；需要访问 F:\AnimeStudio、目标 ZZZ Blocks 目录和 .NET 9 运行环境。'
metadata:
  version: '1.0'
  cli: 'F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe'
---

# ZZZ 美术资产解包与动画导出

## 触发条件

当用户要求处理以下任一内容时使用本 skill：

- ZZZ 角色、骨骼、模型、`AnimationClip`、动画、材质或相关 Unity 资产的解包/导出；
- 从 ZZZ 游戏 `Blocks` 构建或加载 Asset Map/CAB Map；
- 查找某个角色或动画并导出为 `.anim`、`.fbx`、纹理或其他可比较格式；
- 判断“原始 ZZZ 资源 → AnimeStudio 导出 → Unreal 导入”过程中是否丢失骨骼轨道、曲线、根节点、时长或其他动画数据。

普通的已导出 FBX 离线分析可以继续使用项目中的 Python 分析脚本，但不能用它们代替 ZZZ 原始 Unity 资产的解包；原始 ZZZ 资产操作必须优先走 AnimeStudio.CLI。

## 固定工具与依赖

已验证可执行文件：

```text
F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe
```

调用前检查：

1. CLI 文件存在，并先运行 `AnimeStudio.CLI.exe --help` 确认可执行。
2. 同级 `x64` 目录及 ACL/ZZZ 相关原生 DLL 存在；当前版本的 ZZZ 动画 ACL 解压依赖该目录。
3. 不把输出写入游戏安装目录；默认使用：
   - Asset Map：`F:\AnimeStudio\AssetMaps`
   - 导出结果：`F:\AnimeStudio\Exports`
4. 不修改原始 FBX、游戏 `Blocks`、原始 `.uasset` 或项目 `Content/**`，除非用户明确要求。

如果 CLI 或依赖不存在，必须明确报告阻塞原因；不能静默切换到不等价的旧工具或自行猜测替代命令。

## CLI 参数约定

当前已验证的命令行参数包括：

- 必需位置参数：`<input_path> <output_path>`；
- `--game ZZZ`、`--game ZZZ_CB1`、`--game ZZZ_CB2`：按资源版本选择，不能无确认地混用；
- `--types AnimationClip`：筛选动画资源；
- `--names <regex>`：按资源名正则筛选；
- `--containers <regex>`：按容器路径正则筛选；
- `--export_type Convert|Dump|JSON|Raw`：选择转换、文本转储、JSON 或原始导出；
- `--group_assets ByType|ByContainer|BySource|None`：选择输出分组；
- `--map_op Both|AssetMap|CABMap|None`、`--map_type MessagePack|JSON|XML`、`--map_name <name>`：构建映射或处理映射相关流程。

命令示例（执行前将占位路径、版本和筛选条件替换为已确认值）：

```powershell
$Cli = 'F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe'
& $Cli --help

# 为指定 ZZZ Blocks 构建 Asset Map + CAB Map；输出不写入游戏目录
& $Cli 'F:\ZenlessZoneZero Game\ZenlessZoneZero_Data\StreamingAssets\Blocks' `
    'F:\AnimeStudio\AssetMaps' `
    --game ZZZ --map_op Both --map_type MessagePack --map_name zzz_live

# 对已确认的输入资源/资源目录筛选 AnimationClip 并转换导出
& $Cli '<已确认的输入路径>' 'F:\AnimeStudio\Exports' `
    --game ZZZ --types AnimationClip --names '<动画名正则>' `
    --export_type Convert --group_assets ByType
```

大型 ZZZ 资源必须遵循“先建图、再按需加载/筛选”的流程。若输入路径、游戏版本、Asset Map/CAB Map 状态或目标资源名不明确，先检查并询问，不要直接扫描整个游戏目录或导出大量无关资产。

## 动画完整性核对流程

当需要判断 UE 中动画是否还是原始动画时，按以下顺序记录证据：

1. 使用 AnimeStudio.CLI 导出原始 `AnimationClip`，保留原始资源名、容器路径、游戏版本和 CLI 参数。
2. 检查导出的动画数据是否含有：时长、采样率/关键帧范围、骨骼层级、根节点/`Root`/`Bone_Root`/`Bip001` 轨道、位移/旋转曲线、动画曲线和事件/信号信息。
3. 使用 UE MCP 的 AssetTools 搜索目标 `/Game` 资产，读取资产 class、tags、依赖和对象属性；使用 SkeletalMeshTools 核对骨架层级和动画绑定的 Skeleton。
4. 对同名或对应的 `AnimSequence` 逐项比较：时长、骨架、骨骼轨道数量/名称、根级轨道、曲线数量/名称、关键帧范围和导入设置。仅凭预览画面相似不能判定“没有缺失”。
5. 如果 UE MCP 无法直接读取某一项，明确记录为“未验证”，不要把“工具没有暴露字段”说成“资产没有该数据”。
6. 将差异分成三类：
   - 解包阶段丢失：CLI 导出的 `.anim`/FBX 已经缺失；
   - FBX/中间转换阶段丢失：CLI 导出仍有，导入文件没有；
   - Unreal 导入或 AnimBP 表现阶段问题：资产数据存在，但 Skeleton、导入设置、Root Motion、曲线压缩或 AnimGraph 使用方式不同。

## ZZZ TurnBack 特别规则

对 Pyrios `TurnBack` 等动画，必须分别核对：

- 外部 `Root` 是否存在 `Lcl Rotation Y` 与 `Lcl Translation Z`；
- `Bone_Root → Bip001` 是否为实际视觉骨架链；
- `Bip001` 是否带根级旋转/位移；
- 动画是否仍包含完整的前段 pivot 和后段跑出位移；
- Unreal 中使用的是否为正确 Skeleton，以及动画是否被重定向、压缩或固定根骨骼。

不要因为 UE 中 `Bone_Root` yaw 为 0，就断言源动画没有转身；也不要因为外部 `Root` 有 yaw，就直接认为控制它会旋转角色骨架。

## 汇报要求

每次调用 CLI 或核对资产时，报告：

- 实际使用的 CLI 路径和 `--game` 版本；
- 输入、输出、映射状态和关键筛选参数；
- 成功导出的文件/资产数量；
- 已确认保留的数据、缺失的数据和仍未验证的项目；
- 若失败，给出原始错误，不隐藏 CLI 或 UE MCP 输出。

结论必须区分“已由 CLI/UE MCP 实测确认”“根据结构推断”和“尚未验证”。
