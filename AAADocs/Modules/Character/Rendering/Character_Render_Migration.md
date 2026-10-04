# 通用角色渲染迁移与验收

## 当前状态（2026-09-29）

2026-09-29：统筹离线测试22/22、完整 DLL 链接/冷启动、GGYGO自动化10/10（含两项渲染测试）通过，自动化零错误零警告。BP 单字段恢复后已编译、单包保存并冷回读15项参数/三槽/描边，legacy=false、autoActivate=true、is_dirty=false；最终哈希9e093db8…05dac3，双旧备份与原baseline保留。本会话MCP真实PIE确认3个表面MID及Leader Pose描边，灯强度10/2.5/0/40/10对应输出0.65/0.325/0/1/0.65。已恢复灯强度并停止自己启动的PIE，BP/原地图未变脏、哈希未变。结束时地图查询变化及MCP可读性限制另记，未宣称原版视觉还原完成。

本说明只记录已确认的门禁。统筹独占 UE 的冷启动、迁移和自动化执行；当前源码、脚本、配置冻结。本批不重建材质，不改变视觉校准，不保存无关资产。

## 职责与兼容契约

- `UGGYGOCharacterRenderComponent`：显式槽位绑定、MID 所有权、受控主光、可选描边与清理。角色差异由 BP/材料资产配置，不含角色名判断或 LoadObject 默认资产回退。
- `UGGYGOPyriosRenderComponent`：继承通用类，保留 `/Script/GGYGO.GGYGOPyriosRenderComponent` 序列化路径。`AGGYGOHeroCharacter` 继续创建名为 `StylizedRenderComponent` 的旧子类；不在未验收前替换子对象身份。
- `bAutoConfigurePyrios` 保留可序列化属性，迁移写 false；不再参与运行时资产选择。`FGGYGOCharacterRenderSlot` 反射名保留，DefaultEngine.ini 为移动的属性和 RefreshMaterials 函数提供 CoreRedirects。重定向已编译不代表旧 BP 已通过加载/保存验证。
- `RefreshMaterials()` 仅在 BeginPlay 后且激活时建立绑定。Mesh/装扮提供方负责先 Release、更新 Mesh/配置、再 Refresh。空配置不安装 MID；Tick 检测 Mesh/槽位失效时释放并等待显式刷新。
- 原覆盖保存自 OverrideMaterials，null 表示使用模型默认材质。释放只操作仍等于已安装 MID 的槽；原 Mesh/槽相同则恢复原覆盖，不同则清除自身遗留覆盖；第三方写入保留。EndPlay、OnUnregister、Deactivate 均释放自身资源。
- KeyLight 是显式配置，ResolvedKeyLight 是 transient 弱缓存。自动模式保留有效缓存，失效后按对象路径排序选择有效灯；显式不可用时不擅自回退。无有效灯输出黑色与零 SceneLightStrength；环境底色、MatCap、自发光仍独立。

## 已采集旧基线

文件：`Saved/Codex/character_render_legacy_baseline.json`。旧 DLL 下只读审计结果 complete=true、errors=[]，dirty_before/dirty_after 均为空。

唯一发现的旧类 Blueprint 使用者：`/Game/BP/Character/Player/BP_PC_Pyrios`。组件为 `Default__BP_PC_Pyrios_C:StylizedRenderComponent`，类为上述旧路径；引用方包含 `/Game/Characters/Player/Pyrios/DA/DA_Pawn_Pyrios`。

目标 uasset SHA-256：`71cef23fe0a5f2191beb1f096f670f68c1b304e0715e2a98e1a8d011ba4207fc`。旧基线 MaterialSlots 为空、OutlineMaterial 为空、bAutoConfigurePyrios=true；这代表旧代码回退曾负责配置，不能在新代码中继续假定材质会自动接上。

| 配置 | 通用 C++ 默认 | Pyrios 旧基线，迁移时保留 |
| --- | --- | --- |
| ReferenceKeyLightIntensity | 1 | 10 |
| KeyLightIntensityResponse | 1 | 0.5 |
| KeyLightOutputScale | 1 | 0.65 |
| MaxKeyLightStrength | 1 | 1 |
| bEnableOutline / OutlineWidth | false / 0.5 | true / 0.6 |
| KeyLight / KeyLightTint | null / 白色 | null / 白色 |
| LightingUpdateInterval | 0.1 | 0.1 |
| bTraceKeyLightOcclusion / OccludedKeyLightVisibility | true / 0.35 | true / 0.35 |

## 原始迁移步骤（历史流程；最终结果见文末）

工具：`AAADocs/Scripts/migrate_pyrios_render_component.py`；角色映射：`AAADocs/Assets/Pyrios/Rendering/Pyrios_Render_Migration.json`。

1. 完整构建后冷启动加载新 DLL，确保反射存在 `GGYGOCharacterRenderComponent`。先确认目标 BP 没有用户未保存修改。
2. 在 UE Python 中运行脚本默认模式：只做 preflight，不改目标资产/CDO；会创建未注册的瞬态组件探针，对全部待写属性执行 setter/readback 以核验已加载 DLL 的写入契约。要求完整旧基线、单个已映射使用者、组件类与对象路径保留、材质存在、槽名唯一、目标 uasset 哈希未变。仅允许可证明来自旧 native 默认值的继承变化；不能覆盖未知调参。
3. preflight 通过后，统筹按既有授权以 `--apply` 运行。脚本先在 `Saved/Codex/RenderMigrationBackup/` 备份并核对哈希，再写目标 BP 的组件默认值。已有显式槽位优先；仅旧自动配置开启时补入 Body_1、Body_2、Weapon01 三槽，保留已有描边引用或补入配置引用。
4. 设置 bAutoConfigurePyrios=false、auto_activate=true；编译目标 BP，回读编译后的 CDO 配置，再检查保存返回值。任何失败都不得报告完成；可能保留目标脏包，先诊断再恢复，不能用 SaveAll 掩盖。
5. 日志 `PYRIOS_RENDER_MIGRATION_SAVED_RELOAD_REQUIRED` 仅表示保存成功。关闭并重开后再次运行默认模式，预期 `PYRIOS_RENDER_MIGRATION_ALREADY_CONFIGURED`，确认参数持久化且重复执行无改动。未重开回读不能认定迁移完成。
6. 两项 `GGYGO.Rendering.MaterialOwnership`、`GGYGO.Rendering.KeyLightLifecycle` 最新复测 Success、零错误零警告；此前 warning 及修复见下节。迁移后仍需检查真实 BP 的运行 MID、关闭/恢复灯光、换 Mesh、停用/销毁、描边及第三方覆盖不被还原覆盖。自动化编译通过不能替代运行结果。

这份工具针对已审计 Pyrios 目标，不自动迁移其他 Blueprint。出现额外旧类使用者或多模板时，须先制定其映射。模型默认 MI 已保存，因此静态表面预览可以继续存在；它不能证明运行组件已经配置正确。

## 生产工具门禁

- `verify_pyrios_renderer.py` 默认只读；`--compile` 显式重编译可能使材质包变脏，不自动保存。
- `build_pyrios_materials.py` 使用 `pyrios_material_plan.py`，在资产修改前验证完整源 JSON、有限数值、已知校准项、所需纹理、目标类型、槽位和脏包。BuildJournal 列明 attempted/保存/未保存与失败；工具不是全资产事务，失败后可能部分完成。
- 9 项离线回归已通过，6 份相关脚本 AST 检查通过；真实源纯读取计划包含 3 份材质和 16 项纹理引用。以上不等于生成器本次已在 UE 执行。
- 旧基线审计与两项渲染 C++ 自动化已执行，最新复测均为 Success、零错误零警告；迁移器首次只读 preflight 已通过；apply 在旧标志写入处失败，尚未编译/保存。重建器未执行。

## 视觉边界

表面仍是 Unlit/Emissive 的 Toon 近似。静态预览使用 MI 基准光，组件动态主光/描边需要 BeginPlay；编辑器实时场景光同步、公共 MPC、逐像素 Toon 阴影和多点光接入均未实现。本次安全与职责整改不提高原 Shader 的公式还原程度。历史截图与材质证据见 [实现说明](Pyrios_Renderer_Implementation.md) 和 [差距审计](Pyrios_Material_Fidelity_Audit.md)。

## KeyLightLifecycle 历史警告与已通过复验（2026-09-29）

首次冷启动时，两项渲染自动化均返回 Success。KeyLightLifecycle 同时记录 1 条 `LogSpawn: UWorld::DestroyActor: World has no context!`，目标为测试临时 World 的 `DirectionalLight_1`。首次结果不能表述为“零警告通过”；后续修复后的复测已为零警告。

修正前只读核查：夹具调用 `UWorld::CreateWorld(EWorldType::Game, false, ...)`，未向 GEngine 注册 FWorldContext；执行 `Second->Destroy()` 时进入 Engine/Private/LevelActor.cpp 的无 context 警告分支。该分支之后继续移除 Actor、注销组件并标记垃圾，没有在这里提前返回失败。因此它不推翻已通过的灯光失效/恢复断言，但暴露了夹具未完整模拟 Game World 生命周期。

已在随后明确授权的单文件窗口修正 `GGYGOCharacterRenderTest.cpp`：先校验 GEngine，再注册测试专用 WorldContext；RAII 先 DestroyWorld，后移除 context，并仅清除 CreateWorld 为本夹具新建包的脏标记。原 Second->Destroy() 与全部原断言保留，未将 warning 注册成预期结果，未改生产代码。源码已冻结、差异格式检查及随后 NoLink 编译通过；最新 DLL 完整链接并冷启动后复测通过，未再出现该 warning。当前无网络驱动，此测试也不验证网络销毁通知。

统筹首次迁移只读预检通过，随后 apply 写旧标志失败，尚未编译/保存。预检时 content 脏包为空，maps 中有自动化临时包 `/Temp/Untitled_1`、`/Temp/Untitled_4`。本次夹具修正只清理将来由自身创建的包，不扫描或清除当前编辑器的其他 World/脏包；实际无新增脏包仍待重启复测。

## 首次 apply 失败与最小修复（2026-09-29）

实际 apply 已建立备份并修改目标组件的通用属性与槽位，随后写 `bAutoConfigurePyrios=false` 报 protected and cannot be set；尚未进入 Blueprint compile/save。失败当时统筹核对磁盘仍为旧基线 SHA-256；用户随后保存，当前磁盘已变更，详见下节恢复边界。

根因已按本机 UE 5.8 源码核对：PyWrapperObject::SetEditorProperty → PyUtil::SetPropertyValue → PropertyAccessUtil::CanSetPropertyValue 要求 CPF_Edit / CPF_BlueprintVisible / CPF_BlueprintAssignable 至少一个。C++ public 与只有 meta 的 UPROPERTY 不提供这些权限。

修复限定为旧兼容类属性、迁移脚本及其离线测试：旧标志改为 EditAnywhere/AdvancedDisplay，保留原名称、默认值和序列化，不加 CPF_Deprecated，不赋予运行时作用。迁移预检新增未注册、外层为 transient package 的临时组件，对全部计划写入值执行 set_editor_property 与回读；旧 DLL 或写权限失败会在目标 Modify/备份/资产写入之前被拒绝。原始 CDO 与目标 BP 不用于探针。显式 KeyLight 引用若无法载入也提前拒绝，避免误变成自动选灯。

`test_render_migration.py` 的 5 项离线测试通过：受保护属性写入在目标修改前失败；预检不改目标；模拟保存值重新载入后幂等；部分失败不保存且拒绝脏包重试；全部值已匹配但脏包仍拒绝。加上此前 9 项工具测试，现有离线证据为 9+5（本次新跑 5）；mock 回读不等同于真实 UE 冷加载验证。

**原未保存前提下的重试策略（用户已保存，当前不直接适用）**：由统筹对仅此次产生的目标内存改动选择不保存、正常关闭，禁止 SaveAll；确认磁盘哈希仍匹配旧基线与备份。构建修复后的 DLL 并冷启动，确认目标干净；重新默认 preflight，应包含瞬态属性写入探针；通过后再 --apply。备份已存在时必须再次匹配旧哈希，不能覆盖备份。保存成功后再次冷启动执行默认模式，确认 ALREADY_CONFIGURED。失败后不在部分配置的内存上继续重试，不清理无关资产或用户 World。

统筹随后复跑 tests 目录共 22 项离线回归全部通过（包含本次迁移 5 项及其他工具测试，不把 22 项全部计为渲染测试）。源码/脚本已冻结交回；本会话未构建、未操作 UE、未修改资产。统筹已完成本短修 NoLink 编译（2 个动作、16.72 秒）；随后最新 DLL 完整链接成功（3.05 秒）并冷启动，单独修复测试及全量 GGYGO 10/10 均通过、零错误零警告；随后真实迁移恢复与冷回读已通过，详见下节。

## 用户保存版恢复过程（已完成保存重开验收）

用户确认保存后 UE 正常退出。已只读核对三份文件：原始备份 35,492 字节、SHA-256 `71cef23fe0a5f2191beb1f096f670f68c1b304e0715e2a98e1a8d011ba4207fc`；用户保存版备份与恢复前资产均为 37,209 字节、SHA-256 `741751e8b89a1a453ccb17071610823e3db2d32dacd555739041887e87a1ec0a`。两份备份分别保存在 RenderMigrationBackup，不回滚覆盖用户版本，不替换 legacy_baseline 的原哈希。

统筹冷加载只读核对确认：用户保存版 BP 的 13 项通用属性与 desired 完全匹配、MaterialSlots 三槽完全匹配、autoActivate=true；当时仅 bAutoConfigurePyrios=true 尚未完成。无需增加接受任意漂移的脚本分支，也不重写已正确保存的属性和槽位。

统筹已按短资产租约执行恢复：写前再次核对用户保存版哈希、完整配置和目标脏包为空；只将一个无运行时效果的 legacy 标志置 false，compile 后复核全部配置，单包 save，再冷启动回读。保留两份备份、原始 baseline 及首次失败审计；任一核对不一致则停止，不回滚用户版本。恢复时 autoActivate 已为 true，无需写入。

最终状态可由原迁移脚本的 ALREADY_CONFIGURED 分支只读验证，不修改 baseline。统筹已完成单字段补写、warnings_as_errors=true 编译、单包保存和正常重开；冷读15项参数/三槽/描边/autoActivate一致，legacy=false、is_dirty=false。零警告结果也不独立证明临时脏包清空，脏包清单需另外读取。

## 最终结果与真实 PIE

最终资产 SHA-256：`9e093db87659b1a05281f000a97017f4141521e11b93e38f6e92a9dd8705dac3`。本会话MCP再读配置及磁盘哈希一致；本批没有另改baseline或备份。真实游戏生成BP的3个MID、描边接线和主光关闭/恢复/限幅已验证，结果与退出边界见 [运行验收记录](Character_Render_Runtime_Verification.md)。迁移成功不等于原版视觉还原完成。
