---
name: sync-ggygo-readme
description: Keep Source/GGYGO/README.md synchronized with every file change under Source/GGYGO/. Use when creating, modifying, deleting, renaming, or reviewing GGYGO source files, build configuration, runtime architecture, pipeline stages, components, or ZZZ animation integration.
---

# GGYGO Architecture README Maintainer

## Objective

Keep `Source/GGYGO/README.md` synchronized with the actual GGYGO source tree and runtime architecture. README 只保留稳定的项目架构总述、实际文件索引、所有权/数据流/时序、class/struct/字段/函数说明以及当前已确认的未接线边界。

## README 内容边界

允许写入 README 的内容：

- 稳定的项目架构、Unreal 对象与纯 C++ 边界、所有权和唯一 Tick/帧时序；
- 实际存在的文件、目录、class、struct、字段、函数、接口、调用关系和数据权威；
- 当前源码已经确认的空实现、未接线能力、兼容入口和安全边界；
- 会影响后续代码定位的稳定数据流和模块职责。

禁止写入 README 的内容：

- `### YYYY-MM-DD：...` 形式的日期变更记录；
- 某次任务的进度、临时决策、工作日志或计划路线；
- 本地编译/诊断结果、验证状态或一次性环境限制；
- 与源码无关的审查过程和重复的维护规则。

验证结果、任务进度和临时环境限制只在当前任务汇报中说明；README 维护规则只保留在本 skill 中。

## Required workflow

对于任何会创建、修改、删除、移动或重命名 `Source/GGYGO/**` 文件的编码任务，必须按以下顺序执行，不得跳过 README 定位步骤。

### 编码前：先用 README 定位修改范围

1. **先读取 `Source/GGYGO/README.md`**，使用实际文件树、模块职责、类/struct 清单和函数说明确认本次需求对应的文件、模块和现有函数；不能只根据文件名、未落地设计、`.kiro/specs`、AAADocs 或旧 NTE 代码推测修改位置。
2. 读取 README 定位到的源码文件，以及其直接相关的声明、实现、调用方和数据 Model；如果 README 没有对应条目，先把它视为“新文件/新符号或文档缺口”，再通过 `Source/GGYGO/**` 的实际源码确认，不得静默假定其存在。
3. 在开始编辑前明确本次受影响的文件路径、class/struct、字段、函数和架构关系，并判断 README 中哪些章节需要同步更新。

### 编码后：按文件和函数同步 README

4. **同一任务内完成代码和 README 更新**。每个实际发生变化的文件都必须重新检查 README：
   - 新增文件：补充 Public/Private 文件树、文件职责、所属模块、对象边界和对应实现/声明关系。
   - 删除、移动或重命名文件：移除旧路径，更新新路径、引用、模块说明和文件职责。
   - 修改已有文件：只要文件职责、模块关系、所有权、依赖、调用关系或运行时行为发生变化，就更新对应文件说明；不能因为函数签名未变而跳过。
5. 每个实际发生变化的 class、struct、字段或函数都必须同步说明：
   - 新增、删除或重命名：更新符号清单、字段说明、函数清单和调用关系。
   - 修改函数实现：更新该函数的功能含义、输入/输出、读写数据、调用/被调用关系、副作用、边界条件，以及是否仍为 TODO/空实现/未接线。
   - 修改字段或数据流：更新数据权威、唯一写入方、读取方和相关时序章节。
6. 如果改动涉及 Unreal 对象与纯 C++ 边界、组件所有权、初始化顺序、唯一 Tick、Pipeline 阶段顺序、RuntimeData/ZZZAnim 写入权威、Public/Private 接口或未实现状态，必须同步更新对应架构章节，而不是只改文件列表。
7. 不在 README 中添加日期变更记录、任务进度、临时验证日志或环境限制；只把最终源码已经确认且会影响架构理解的事实合并到对应的稳定章节、文件说明、符号说明、函数说明、数据权威或时序章节中。
8. 代码和 README 更新后，重新核对实际路径、符号、声明/定义、引用、所有权、函数说明和阶段顺序；只有 README 与最终源码一致后，才能报告任务完成。

A README-only edit does not require another README update, but it must still preserve the actual source index, stable architecture sections, and file/class/struct/function explanations. Do not add a change log or validation log.

## GGYGO-specific invariants

- `UGGYGOCharacterRuntimeComponent` may own pure C++ runtime objects, but those objects remain non-UObject and must not gain independent `TickComponent` scheduling.
- `ABaseCharacter::Tick` or its single runtime-host entry remains the only authoritative frame scheduler.
- Preserve the documented order: `Arbiter → Input → Intent → Gait → Parameters → StateManager → MotionDriver → ZZZAnim → Reset`, unless the task explicitly changes the architecture and updates the README first.
- Preserve the BeginPlay dependency order around `InitGEGlobals`, `ASC->InitAbilityActorInfo`, pipeline initialization, `FGYGOStateManager::Init`, and `InitASC`.
- Preserve the single-writer rule for `FRuntimeData` and `RuntimeData.ZZZAnim` fields.
- Do not use old NTE `UNTEAnimInstance` or `Animation/Decisions/` as the implementation basis for new ZZZ functionality.

## Validation checklist

Before completing a task that changes `Source/GGYGO/`:

- Confirm every changed source path exists.
- Confirm new symbols have matching declarations/definitions and include paths.
- Search references under `Source/GGYGO/**` for moved or renamed members.
- Check for stale direct access to migrated runtime members.
- Run diagnostics for changed C++ files when available.
- Run the narrowest available build or static validation; if UE compilation is unavailable, report `静态检查通过，编译待本地验证` rather than claiming compilation success.
- Re-read the affected README sections and verify the stable architecture, file index, symbol/function explanations, data authority, and timing remain consistent; do not add a dated change log or validation status to README.
