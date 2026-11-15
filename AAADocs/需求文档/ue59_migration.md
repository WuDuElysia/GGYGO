# UE 5.9 副本迁移

## 目标

保留原 UE 5.8 工程，在独立副本中完成 UE 5.9 源码、插件、脚本和资产适配，验证现有可玩战斗闭环。System 原会话端到端负责，统筹负责必要接口评审和推送。

## 方案要点

- 副本为 `F:/ue_project/GGYGO_UE59`；实际引擎为 `F:/UE5.9/UE_5.9`，UE 5.9.0、Changelist 60351404、Release-5.9。只向副本写迁移实现，原工程仅维护本需求记录和看板。
- 副本包含复制时已落盘的未提交工作、忽略的本地 Content、World Partition 外部包和四个项目插件；父子仓均独立，没有共享 Git 对象、资产硬链接或目录联接。已授权的初始副本约 11.6 GiB，旧 Binaries／Intermediate／DDC／Saved 和外部原始解包库未复制。
- 父子仓都在 `codex/ue59-migration` 提交；只提交迁移差分，保留其它用户改动。父仓 `Source/GGYGO` gitlink 按统筹决定承接复制时已经提交的源码基线 `a3716a6e` 并指向本次新子仓提交；不回退或重拣父仓旧引用 `0616e3f7` 与该基线的既有差异。推送由统筹处理。
- 唯一记录为原工程本文件；副本同名文档只同步，不维护第二套进度。原工程及 Obsidian 的 5.8 说明不因独立迁移支线而改成已切换。
- 保持原玩法、蓝图／C++ 分工和资源准入期限。旧的受击、预输入、音效、闪避和动画待定项仍按原需求处理；角色互相阻挡但不能互踩的已定规则保持。不改引擎，不以默认材质、关闭功能或降低断言代替兼容。
- 不 SaveAll，不覆盖用户未保存工作，不扩大素材 Git 跟踪范围。66 个目标 Niagara 原本均被 Git 忽略，本次只在副本逐包转换保存，保留其本地素材属性。
- 已验收的运行载体是本机完整副本；迁移分支保存源码、脚本和文档差分，本地素材及复制时的既有未提交工作继续保留在副本中。远端分支不包含全部可运行素材。

## 当前状态

- **源码与工具适配完成**：EngineAssociation／IncludeOrderVersion 切到 5.9；制作和运行脚本指向实际副本与引擎。GameFeature 删除 5.9 已移除的 lifetime-control 开关查询，保留原生 handle、GT、退出阶段及结果校验；Sprite 使用 `CutoutMode`；Editor 接入全局 ToolsetRegistry 和拆分后的 ToolsetRegistryEditor；私有渲染取证匹配实际 5.9.0 版本。MCP 客户端使用 `describe_toolsets` 与 `PythonScriptingTools.execute_python`，实际接口及 Cutout 写入已验证。
- **资产转换完成**：70 个蓝图／动画蓝图、66 个 Niagara、32 个目标材质／实例首次检查通过；补齐实际引用的 598 个材质／实例编译，均有有效当前 D3D12 ShaderMap。66 个 Niagara 完成编译后逐包保存为 5.9；新进程不再出现原批次的旧 Niagara 编译数据不匹配诊断。
- **玩家运行与换人联机通过**：转换后新进程四项原测试全部 Success，覆盖普攻连段、自然结束、移动／攻击取消、Normal01 特效生命周期、客户端输入、换人、致死伤害和死亡自动换人。首次准备约 21.6 秒 Ready，满足原 30 秒截止。2 项带告警，包含 CMC 帧耗时迭代上限、旧 owner 响应拒绝及退场通知；未隐藏或降低断言。另有死亡蓝图配置、逐单元挂点和四项 Rendering 检查通过。
- **Kevin 正式战斗与死亡清理通过**：P3 原 Encounter／BT／GAS 与原玩家数字输入完成两阶段交战，原普攻把生命从 1200 打到 0；约 202 秒死亡结束并移除 Boss，之后玩家能力／位移归还，Boss 特效和音频资源为空。查看了冰／火特效、角色阴影及死亡前后截图，清理画面无 Boss 或残留阴影；本结论来自正式战斗，不依赖直接致死或销毁夹具。
- **Kevin 最小联机通过**：单 Editor、Listen Server＋Client、真实 D3D12，Ice03／Fire02／AirChain01 三招均完成，客户端有对应 Montage 和 11 类 Kevin 特效组件的实际观察；两端技能资源为空，Encounter 销毁后两端 Boss 均为空。贴身夹具观察到 9 次 Falling 胶囊接触、0 次角色 Landed，末态两端 Walking；本次只复验该联机场景，不扩展为其它接触场景均已覆盖。12 张客户端截图保存／读回成功并已抽查。
- **统筹核收及分仓推送完成（2026-11-15）**：核对迁移差分、编译与资产结果、四项运行测试，以及玩家死亡替补、Kevin 阶段／死亡清理和客户端特效截图；GameFeature 原会话对两处开关查询删除的一次静态评审无阻塞，非空受管生命周期仍未运行。父仓[迁移提交](https://github.com/WuDuElysia/GGYGO/commit/22566e2b9ab2198046f3b01668c2fc335e112a60)与子仓[接口适配提交](https://github.com/WuDuElysia/GGYGO_Source/commit/d1c19e504aeb4bd5b1d6afd7e11911f0a72366f1)均已推送各自的 `codex/ue59-migration` 分支。原 main 未切换，无 UE／UBT 在途。
- **原工程保留**：仍关联 `5.8`，未用 5.9 打开。原 `F:/UE_5.8` 安装已不存在，Launcher 只登记 5.9；如需运行原工程，须恢复可用 5.8 引擎，本次不自动重装。

以下路径除初始复制证据外均相对副本：

| 证据 | 结论 |
| --- | --- |
| `Saved/Codex/UE59Migration_20261113/copy_result.json`（原工程） | 独立副本与本地资产复制验证通过。 |
| `Saved/Codex/UE59Migration_20261115/Build03.log` | Editor 编译 Succeeded；Build01／Build02 保留实际接口失败。 |
| 同目录 `AssetLoad01/assets.json`、`shader_maps.json`、`tool_api.json` | 目标资产、ShaderMap、工具接口及 Cutout 实测通过。 |
| 同目录 `DependencyLoad02/dependencies.json`、`AssetConvert03/dependencies.json` | 66 个 Niagara、598 个材质依赖有效；66 个 Niagara 转换保存完成。 |
| 同目录 `Runtime03/editor.log`、`Runtime03/Report/index.json`、`Runtime03/Captures` | 转换后四项运行／联机检查通过，死亡前后画面已查看。 |
| `Saved/Codex/KevinFinalBattle/UE59_Battle02/editor.log`、`199_death_finished.png`、`200_cleanup.png` | 正式两阶段交战、死亡及资源／画面清理通过。 |
| `Saved/Codex/UE59Migration_20261115/KevinNetwork01` | 三招联机、两端资源清理及 Encounter 销毁复制通过；观察记录与 12 张客户端截图齐备。 |

失败记录仍保留：`Runtime01` 的四项资源 Pending 超时、`UE59_Battle01` 的共享材质 60 秒超时，以及 `Runtime02` 的首次输入超时，均在依赖补编译和 Niagara 转换后由 `Runtime03`／正式战斗新结果覆盖。中文环境的引擎 UnifiedError 两项及 StructuredLogFormat 启动断言、ToolsetRegistry 英文错误字符串断言，在 `Runtime02` 临时英文进程全部通过，确认本地化预期不一致；中文启动诊断仍存在，未修改引擎或过滤日志。

## 未完成项

- 完整 Cook／打包、独立进程网络及网络扰动矩阵、设备、性能和音频主观听评未验证。本次现有 Experience 为 NoGF，非空受管 GameFeature 加载／释放路径未作运行验收。

## 验收标准

- Editor 编译通过；必要蓝图、动画图、Niagara 与材质可加载、编译；缺失依赖明确报出。
- 真实渲染下验证玩家普攻连段、取消、换人和死亡清理，Kevin 正式交战与死亡清理，P3 灯光、角色阴影及相关特效。
- 复测迁移影响的最小联机链路，编译、资产、运行、视觉和联机各自记录证据；不扩大为完整 Cook／设备／网络／性能矩阵。
- 保留原工程及本地素材，不覆盖未保存工作，不 SaveAll；提交只含本次迁移差分，交付列出剩余限制。
