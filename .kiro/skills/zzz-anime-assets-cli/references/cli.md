# CLI 调用参考

已验证程序在 SKILL.md 指定目录；同级 x64 原生 DLL 包含 ZZZ ACL 解压依赖。先确认路径／版本／依赖及真实 --help；工具升级后重新核参数。

## 参数

- 位置参数：<input_path> <output_path>。
- --game ZZZ／ZZZ_CB1／ZZZ_CB2：按确认资源版本，不无故混用。
- --types AnimationClip、--names <regex>、--containers <regex>：按目标筛选。
- --export_type Convert|Dump|JSON|Raw；--group_assets ByType|ByContainer|BySource|None。
- --map_op Both|AssetMap|CABMap|None；--map_type MessagePack|JSON|XML；--map_name <name>。

默认映射输出 F:/AnimeStudio/AssetMaps，导出 F:/AnimeStudio/Exports。先复用有效映射再按需加载；只有映射缺失／版本改变才重建。输入路径不明先查现有目录和记录，真实歧义才问用户，不盲扫全游戏。

示例仅作参数组合，执行前替换确认路径／版本／筛选；不要把占位符直接运行：

```powershell
$taskCli = 'F:/AnimeStudio/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe'
& $taskCli '<输入>' '<输出>' --game ZZZ --types AnimationClip --names '<目标正则>' --export_type Convert --group_assets ByType
```

保留实际资源名、容器、版本及命令来源。输出只写授权目标，原数据只读；失败保留原错误，不能用“进程结束”代替导出成功。BH3 的格式／游戏选项不从本 ZZZ 说明推断。
