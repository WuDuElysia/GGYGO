# 第 07 批 Input：稳定接口与待验入口

更新：2026-10-13。旧租约、逐轮过程及已结束门禁已迁入[历史正文](Module_Repair_07_Subleases_History_20261013.md#迁移前原文)；本次仅整理文档，整批需求与运行验收仍未完成。

## 当前入口

- 有效范围、依赖与共享窗口：[有效排程的 Input 行](../../Coordination/Module_Repair_Parallel_Schedule.md#当前事实作者与必要前置)。源码、DLL、工具及资产的冻结由当轮窗口管理。
- 稳定跨模块接口：[移动输入来源共享契约](../../Architecture/Interactions/Module_Repair_MovementInput_Contract.md)。Native 来源与 CMC 准入／执行的职责以该契约为准。
- 第 07 批旧验证及失败：[Input 验证记录（截至 2026-10-01）](Module_Repair_07_Validation.md)。它记录当时状态，后继实现与验收须沿当前排程核收。

## 稳定必要契约

- Hero 持有本地输入会话、注册与绑定资源；绑定由记录的原 InputComponent 幂等释放。来源及 CMC 保持各自权威，退役原会话不能清理后继会话。接口见 [Hero](../../../Source/GGYGO/Character/Components/GGYGOHeroComponent.h) 与 [InputComponent](../../../Source/GGYGO/Input/GGYGOInputComponent.h)。
- ASC 接收、仲裁能力输入请求；`ReceiveAbilityInputRequest` 固定首次匹配 Spec、原 Owner／Avatar／World 及绝对截止；`EndAbilityInputRequest` 按原身份结束；`QueueAbilityInputRetry` 只移交精确原请求，不伪造 held 或输入事件。有效身份、截止和清理由 [ASC 公开接口](../../../Source/GGYGO/AbilitySystem/GGYGOAbilitySystemComponent.h) 与[请求数据类型](../../../Source/GGYGO/AbilitySystem/GGYGOAbilityInputRequestTypes.h)定义，不沿用历史双参数 Tag 签名。
- retry 不续期，`WhileInputActive` 仍要求真实 held；清输入或原绑定退役后的请求不得借后继来源复活。唯一帧末消费仍是 [PlayerController](../../../Source/GGYGO/Player/GGYGOPlayerController.cpp) 的 `PostProcessInput → ProcessAbilityInput`，不另设 Tick、帧调度或直接激活旁路。
- E＝Special、R＝ExSpecial、F＝Rush 是三个独立 Boolean 入口。Input 写三 IA、`DA_InputConfig_Default`、`IMC_Default` 及所属 native Tag；Combat 写三 GA 与 AbilitySet。自然结束是待运行验收边界，组合、取消或表现扩围须另行决定。

## 未完成验收与有效依赖

- **Pyrios E／R／F：**[P2 正式归还](../../../Saved/Codex/PyriosSkillInputs_20261013_P2/return.json)证明 CS 隔离工程五包保存、独立 Cold 及完整保护正常归还，原生产未升级；Combat A1 已消费。真实 owning PC／设备按键、实际技能入口与自然结束仍未验，依当前排程接续，不能用保存／Cold 代运行或联机验收。[P1 失败及窗口内脚本漂移](../../../Saved/Codex/PyriosSkillInputs_20261013_P1/return.json)继续保留。
- **第 07 批旧验收接续：**旧记录中的第 17 次身份红诊断、阻断复活未复现、设备／BeginPlay／网络未验均保留，后继关闭状态须由真实专项报告核收。两条验收方向继续保留：无精确来源不得借 ASC 未就绪时已结束 tap；同 Spec 多 Tag 的 held 为 OR，Generic Pressed 仅首来源、Released 仅末来源并保持真实事件顺序。现行源码已存在身份化请求 API，本次未审查后继动态报告，不能将旧“仅值类型／未实现”描述当成当前实现状态。
- **历史待办未关闭记录：**专项与身份／多来源／阻断验收、`IMC_Default`／`IMC_MouseLook` 的 `CountRegistrations` 资产迁移和 `BP_PlayerController` 旧注册路径核对、07G 局部图文同步仍有原待办记录，见[历史未授任务](Module_Repair_07_Subleases_History_20261013.md#历史未授任务截至2026-10-01)。实现及验收状态以现行源码、当前排程和后继证据为准；历史租约不授权现在开工。

## 历史与失败证据

[完整迁移前原文](Module_Repair_07_Subleases_History_20261013.md#迁移前原文)保留 A／B／C／D、07E0／R1、07E1、07E2-V 的租约、断言、逐轮交接、失败及原禁止范围。07E2-V／Movement C22 旧门禁不再作为当前开工入口；验证原件及失败产物保留原路径。
