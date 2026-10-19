# Audio 配置与资源生命周期契约

本文维护职责、组件生命周期、来源与验收规则。当前任务、作者、依赖、写集和共享窗口只看 [有效排程](../../Coordination/Module_Repair_Parallel_Schedule.md)；本文不授予执行权限。完整父保护集合与实际写集有交集时，先完成作者协调和正常归还。

## 职责与接口边界

| 所有者 | 输入 → 作用 → 输出或清理责任 |
| --- | --- |
| Animation / Montage / Notify | 已确认动作与配置 → 决定触发点、Mesh / Socket、窗口 → 在真实时机发起表现 |
| Combat / Physics | 同一次命中与表面语义 → 查询、去重和命中分配 → HitResult / 表面 Tag 交原 Cue 入口 |
| GAS / GA / GE | 原能力及资源身份 → 管能力与持续 Cue 生命周期 → 结束、取消、换 Pawn 时移除自己持有的 Cue |
| Audio 配置与 Cue 表现 | 明确声音引用、变体与播放参数 → 选择及播放声音 → 仅释放自己的 AudioComponent / 播放资源 |

Audio 不建动作时钟、命中查询、网络协议、第二套 Cue 路由或帧调度，不读写其它模块内部状态。常改声音、组合、附着、衰减与并发放 UE 资产和蓝图。

一次性动作声使用原生 `AnimNotify_PlaySound`。一次性命中声沿既有 [UGGYGOGameplayCueNotify_HitImpact](../../../Source/GGYGO/AbilitySystem/Cues/GGYGOGameplayCueNotify_HitImpact.cpp) 的 `PlaySoundAtLocation` 入口；招式选声由原调用方和 Cue 所有者收敛。缺失映射不得以通用 `DefaultEffect` 偷换；已有显式正常配置模式须按真实用途核对，不据此一概判非法。

## 来源、配置与保存

| 来源或工具 | 消费入口与边界 |
| --- | --- |
| Pyrios / Pyrois 发布素材 | [源 manifest](F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model/Audio/manifest.json) 定位动作；各动作 `mapping.json` 与实际 WAV 定事件、来源和缺口。[导入计划](../../../Saved/ValidationPlans/PyriosAudio_20261010.json) 是目标身份清单，不是原 cue 时间线 |
| Kevin DemonBattle 发布素材 | [源 manifest](F:/AnimeStudio/Exports/BH3/Animator/Kevin/05_BOSS_411_DemonBattle/Audio/manifest.json)、各真实动作 mapping；整体资产入口见 [导入核对](../../Assets/BH3/BH3_Kevin_DemonBattle_Import.md) |
| Pyrios 导入与既有 Notify 工具 | [全量导入](../../Scripts/import_pyrios_audio.py)、[固定 Normal_01 导入](../../Scripts/import_pyrois_normal01_skill_audio.py)、[Normal_01 Notify](../../Scripts/wire_pyrios_normal01_sound_notify.py)；固定目标、原输入身份与既有 guard 不因本文整理改变 |
| Kevin 导入工具 | [import_bh3_kevin_demonbattle_audio.py](../../Scripts/import_bh3_kevin_demonbattle_audio.py)；明确 action / target 集合及 editor / commandlet 宿主，不自动覆盖或跳过已有目标 |

Pyrios 包沿 `/Game/Characters/Player/Pyrios/Audio/<动作名去前缀>/`，既有 Normal_01 留在 `Normal01/`；Kevin 沿既有角色目录。新增 Cue 沿已有 `/Game/GameplayCues/` 扫描路径。Content 放 UE 包，源数据与脚本留既有来源／文档目录。

名称关联只能证明候选关系；角色 Switch、媒体图、动画 cue、命中分配、混音分别取证。事件数字后缀不自行当执行顺序，动画目录的 `Loop` 不自行当音频无限循环。未发布映射不等于原游戏无声。详例见历史的 [来源证据等级](Audio_Contract_History_20261013.md#来源证据等级) 与 [Ex Loop 证据](Audio_Contract_History_20261013.md#ex-loop-发布-wav-是循环渲染不是循环体)。控制元数据、源指针或文件名不扩大原读取授权。

源 WAV 的 `source_sha256` / `source_wav_sha256` 均指整份 WAV 文件字节 hash；未另算的 PCM payload hash 不冒称已算。配置引用须明确到实际资源，音量、音高、Follow、AttachName、预览衰减、循环／停止政策与时点分别声明。项目诊断参数与原游戏证据分开；历史已保存参数不自动迁移到另一动作。

导入只写明确新增目标：验证来源／格式／属性，关闭自动 Cue 与附带节点，禁止覆盖且先 `save=False`，唯一正确输出才精确保存。保护源、已有资产及入口 dirty 集合；不 SaveAll、不清除其它脏包、不自动回滚失败产物。只读模式禁止修改或保存。实际原生导入／保存／加载回调后重核必需输入，缓存仅在本次调用有效。

必需来源、引用、触发点或 API 无效，明确拒绝／等待真实就绪／中止并定位，不改用另一动作或声音。只走公开合法接口；如采样率使用 searchable AssetRegistry tag，导入来源使用原生 AssetImportData 子对象。protected 字段不可读须保留未知，不能用静态默认值充当动态测量。

## 播放资源与退出责任

| 情形 | 生命周期与实际退出契约 |
| --- | --- |
| 一次性动作声 | Notify 在真实时机触发，声音自然结束；没有 GA 可停止句柄时，不承诺取消 Montage 即截断 |
| 一次性命中声 | HitImpact 的一次性播放自然结束，不用于循环或要求取消即停的声音 |
| 持续声／取消即停 | GA / GE 持原 Cue 生命周期，Cue 持自身 AudioComponent；优先引擎 `AGameplayCueNotify_Looping`，按实际实现验证，不用一次性声替代 |
| 完成／取消／换 Pawn | 上游结束旧能力或 Avatar 的原持续 Cue；不继承旧播放资源，不清理后继 Cue |
| Removed／回收／EndPlay | Cue 只停／淡出并释放自身资源，清理幂等；不能仅依赖 NotifyEnd |

`AnimNotify_PlaySound` 的 one-shot 检查和 `SpawnSoundAttached` 默认 AutoDestroy 属引擎源码政策；实际创建、播放、完成与销毁仍需运行观察。原注册位、AutoDestroy 动态值、Finished 回调及 GC 未读到时分别留未知。

观察按实际 World / Pawn / primary Mesh / 精确 Sound 取证，记录动作前基线、实际 IsPlaying / PlayState / 参数和后续组件状态。新候选出现区间不是创建时刻；脱离 Mesh、离开 Owner 组件集合、对象失效分别记录，不把消失推成自然结束、Notify 源关联或 GC 完成。只读观察器不另 Play / Stop、替换时点或持 UObject 跨帧；有限观察由真实宿主管调用及自身回调清理。

## 验收层与设备试听

| 验收层 | 必要事实 | 不能代替 |
| --- | --- | --- |
| 来源／静态 | 明确来源身份、证据等级与未知项 | cue 时间、运行或选声正确 |
| 资产保存／Cold | 精确包保存，独立进程加载与属性／引用读回，实际包身份和 dirty／保护差集 | 发声、动作消费或自然退出 |
| 编译／专项 | 同版 DLL 及该专项真实结果 | 资产保存、PIE、设备或网络 |
| 动作运行 | 真实输入／ASC／GA／Montage 消费与该声音组件的原 Owner / Mesh / Sound / Playing | 原 cue、选声、自然释放原因或联机 |
| 设备播放／人工听感 | 实际输出端点、源匹配及真人听到／质量反馈 | 技能中用声正确、原混音／时序或联机 |

设备试听每次现场读默认端点、mute 与音量，不沿用旧设备值，不擅改默认设备或音量。获得授权的临时取消静音在 finally 恢复本次入口实际状态；用户较新的状态不能被旧记录覆盖。只控制自己启动的播放、录制及资源。

源匹配需要实际宿主 PID 在正确端点的播放会话、受控基线、明确源模板及对应录制证据；录音非零或组件 Playing 单独不证明目标声音可听。引擎 Submix 与设备回环分别核收。Submix 若因静默自动禁用而未追加帧，不用主机墙钟直接推 WAV 样本索引；顺序匹配不能冒称墙钟静默基线已验。

跨进程交接等实际 JSON／信号／正常退出，PermissionError 仅在原截止时间内有界等待并保留错误。子宿主正常退出、父 launcher、比较程序的结果分别记录，不用 `readback.success` 代进程退出或把父失败改成全链通过。停止录制、恢复设备、释放自有组件／回调和归还窗口均须真实回执。

机器源匹配与“能听到”不等于选声通过；真人后续异常反馈保留并覆盖早先正常质量判断。需技能上下文辨认时，先由原动作所有者接真实消费链。仅获准的隔离诊断逐个明确 SW、显示候选名及“非原时序、未还原”；Impact 试听不代真命中，项目诊断点不改写原 cue 未知。

## 历史证据导航

- [整理前完整契约](Audio_Contract_History_20261013.md)：保留 Kevin／Pyrios 素材、候选清单、旧参数及各导入、Notify、Cold、正式 GA、R1–R3 失败证据；旧“当前”只指当时，不作为执行门禁。
- [Normal_01 真实导入及后续证据](Audio_Contract_History_20261013.md#已完成的真实导入证据)：手动组件、Notify 预览与正式 GA 观察分别核收，不互相替代。
- R4 按需追溯：[机器归还](../../../Saved/Codex/PyriosAudio_Audition_20261013_R4/verification_return.json)、[原比较失败](../../../Saved/Codex/PyriosAudio_Audition_20261013_R4/output_readback.json)、[人工反馈](../../../Saved/Codex/PyriosAudio_Audition_20261013_R4/hearing_confirmation.json)。本入口不复制历史设备值，不把局部成功升成整需求完成。

完整需求及约定验证完成后集中同步受影响模块／Obsidian与准确已验文件的 Git 交付。过程中只更新有效任务入口和必要交接，不重抄历史或逐步重画图。
