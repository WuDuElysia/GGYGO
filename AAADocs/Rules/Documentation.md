# 文档与上下文

写文档、同步 Obsidian、读历史或控制上下文时读本文。

## 写法

- 文档写给第一次读的人看：用完整句子和普通说法，不用内部批次代号（R5、N3、Cold 之类）代替说明。必须提到某次运行时，写清它验证了什么。
- 一个需求一份记录，放在 `需求文档/`。只写这几项：目标、方案要点、当前状态、未完成项、验收标准。新信息原位更新，不追加日记。
- 不写哈希、字节数、身份链、保护记录或逐步过程；这些要么在 Git 里，要么不需要。
- 不新建摘要、索引或人工 JSON。JSON 只用于脚本真正会读的配置和数据。

## 放置

- `AAADocs/进度总览.md` 由统筹维护，只做索引。AAADocs 根目录只留 README 和进度总览。
- 目录分工：

| 目录 | 内容 |
| --- | --- |
| `Rules` | 协作、代码与交付规则 |
| `Coordination` | 看板、会话路由、修复清单 |
| `Architecture/Interactions` | 跨模块接口 |
| `Modules` | 模块专项记录 |
| `Assets` | 素材盘点与配置 |
| `Scripts`、`References`、`需求文档` | 脚本、参考资料、需求，各归原目录 |

- Content 只放 UE 包；源 JSON、导出设置和脚本留在素材或文档目录。资产目录沿既有的角色／场景层级扩展，不为单次任务另建平行目录。

## Obsidian

- 根目录 `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划`。每个模块的 `结构.md` 是该模块职责、接口和关键约束的长期说明，跨模块负责人改代码前先读它。
- 需求验收后只更新受影响的模块和必要入口。维护文档／Canvas 时用 [obsidian-canvas-diagram](../../.kiro/skills/obsidian-canvas-diagram/SKILL.md)。
- 源码／资产变化尚未验证时，不把计划改成"已实现"。

## 读取与上下文

- 续接工作先看需求记录和当前代码，不读历史文件。只有当前判断确实依赖某个旧决定时，才去查那一段。
- 不为小修改重读全项目；源码只读受影响的调用链。
- 读聊天记录只取最近的结论，不全文回传后再摘要。read_thread 要在工具层先筛最终回执，默认不输出推理、命令和工具记录；wait_threads 复用增量 cursor。
- 已载入且未变化的规则不反复读；首次进入、上下文压缩后或规则变化时再读。

## 参考资料

- Lyra 方案比较：[lyra-reference](../../.kiro/steering/lyra-reference.md)。完整副本 `F:/ue_project/LyraStarterGame` 只读，不用项目里的旧局部副本作权威。
- ZZZ 解包／导出／源资产对照：[zzz-anime-assets-cli](../../.kiro/skills/zzz-anime-assets-cli/SKILL.md)，优先 AnimeStudio CLI，不用 GUI 替代。
