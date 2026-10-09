---
name: zzz-anime-assets-cli
description: 用 AnimeStudio CLI 解包／导出 ZZZ 资源，或核对源资产到 UE 的数据损失。
metadata:
  version: '1.1'
  environment: 'Windows；需要访问 F:\AnimeStudio、目标 ZZZ Blocks 目录和 .NET 9 运行环境。'
  cli: 'F:\AnimeStudio\AnimeStudio\AnimeStudio.CLI\bin\Release\net9.0-windows\AnimeStudio.CLI.exe'
---

# ZZZ 资源 CLI

唯一已验证 CLI：F:/AnimeStudio/AnimeStudio/AnimeStudio.CLI/bin/Release/net9.0-windows/AnimeStudio.CLI.exe。

- 原始 Unity／Blocks 解包优先此 CLI，不用 GUI 或普通 FBX 脚本冒充解包。已导出 FBX 可用现有离线解析器分析。
- 确认游戏版本、输入、已建 Asset/CAB Map 和具体目标后按需筛选；不为一个角色默认扫描／导出全库。不修改游戏安装目录或覆盖既有源／UE 包。
- CLI／原生 ACL 依赖缺失时明确报告，不偷偷换旧工具。只在初次使用或工具／环境变化时核 --help，不在每次读取既有导出物时再启动 CLI。
- 实际调用前读 [references/cli.md](references/cli.md)；动画／曲线／UE 导入损失核对时读 [references/animation-checks.md](references/animation-checks.md)。普通素材盘点无需动画全矩阵。
- 交回实际输入／筛选／输出及来源、已确认差异和未验证项；引用真实日志／现有记录，不每次新造报告。工具不暴露字段不代表数据缺失；原骨架／曲线与运行时消费是不同问题。
