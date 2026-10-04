# Pyrios 角色渲染实现（UE 5.8）

> 当前为可编辑、可预览的近似材质，尚未达到游戏内观感。差距、已证实的接线错误及后续顺序见 [材质还原差距核查](Pyrios_Material_Fidelity_Audit.md)。

## 当前代码与资产边界

2026-09-29：统筹离线测试22/22、完整 DLL 链接/冷启动、GGYGO自动化10/10（含两项渲染测试）通过，自动化零错误零警告。BP 单字段恢复后已编译、单包保存并冷回读15项参数/三槽/描边，legacy=false、autoActivate=true、is_dirty=false；最终哈希9e093db8…05dac3，双旧备份与原baseline保留。本会话MCP真实PIE确认3个表面MID及Leader Pose描边，灯强度10/2.5/0/40/10对应输出0.65/0.325/0/1/0.65。已恢复灯强度并停止自己启动的PIE，BP/原地图未变脏、哈希未变。结束时地图查询变化及MCP可读性限制另记，未宣称原版视觉还原完成。

迁移契约与执行门禁见 [通用渲染迁移说明](Character_Render_Migration.md)。该 BP 的迁移已完成保存重开验收；真实 PIE 证据与限制见 [运行验收](Character_Render_Runtime_Verification.md)。

## 当前实现

- `UGGYGOCharacterRenderComponent` 提供通用 MID、主光传参和描边生命周期；仅消费显式 `MaterialSlots` 与 `OutlineMaterial`，不检查角色名称、不硬编码资产路径。
- `UGGYGOPyriosRenderComponent` 保留为通用组件的兼容子类；Hero 仍创建同名 `StylizedRenderComponent` 以保持旧资产身份。`bAutoConfigurePyrios` 仅供迁移读取，不再选择材质。字段/函数迁移有 CoreRedirects；该 BP 的序列化兼容性已通过保存重开核对；不外推到未审计资产。
- `RefreshMaterials()` 先释放旧绑定，只有 BeginPlay 后且组件激活才按准确槽名建立 MID。更换 Mesh/装扮前调用 `ReleaseMaterials()`，更新配置后再刷新。空配置不会自动补齐 Pyrios 材质。
- 释放只处理仍由组件持有的 MID 覆盖；同 Mesh/同槽恢复原覆盖（包括 null），换 Mesh/槽后清除自己的遗留覆盖，不把旧材质写入新模型，不覆盖第三方替换。
- 描边需要显式材质与开关，Leader Pose 跟随主 Mesh；仅有表面 MID 的槽位显示描边。
- 材质是 Unlit，Emissive 中计算 `_LightTex` 法线 RG 与蓝通道偏移、法线高度补偿后的三段明暗、Material ID 分组色、五组高光/边缘光和 MatCap。三个 MI 从原始 JSON 及项目现有贴图生成；高光采用 GGX 近似，Ramp、MatCap 混合与高光仍非原 Shader 等价实现。
- `_N/_M/_A` 贴图设为线性 BC7，避免 normal-map BC5 压缩丢失 `_N.B`，并保留 `_M.A` MatCap 遮罩。

## 光照选择

角色使用 UE 的 `DirectionalLight` 作为主光方向和颜色输入，组件每 0.1 秒更新一次。通用组件的参考强度、响应、输出系数、上限默认均为 1，角色值写在 BP；光强比求幂、乘输出系数并限幅后写入 MID 的 `SceneLightStrength`。`KeyLightTint`、`OccludedKeyLightVisibility` 也可按角色蓝图配置。MI 的静态预览默认 `SceneLightStrength=1.0`、主光方向 `(0.35, 0.25, 0.9)`。2026-10-04 起 BP 设为 `KeyLightIntensityResponse=0`、`KeyLightOutputScale=1`（`set_pyrios_light_response.py`，原 BP 备份于 `Saved/RenderLightResponseBackup/`，原哈希 `9e093db8…05dac3`）：UE 主光只提供方向与颜色，强度恒为 1，与静态预览一致。角色明暗由材质自己算，因此场景的 Lumen、Skylight、点光源和 UE 默认 Lit BRDF 不直接叠加到角色表面；环境与其他物体继续使用 UE 光照。可见性射线仍只是角色级遮挡近似。

## 表面材质实现（2026-10-04 起）

`M_Pyrois_Toon` 的 Custom 节点是 NapAvatarStandard `CharacterToonDeferred` Pass（变体 `{_NAP_SHADER_QUALITY_HIGH, _MATCAP_ON, _FX_UNCLIP_SCREEN_IMAGE_OVERRIDE_2_TONE, _FX_UNCLIP_SECONDARY_EMISSION_RIM_GLOW}`，含屏幕贴图与自发光分支）像素着色器的逐行移植，设计与伪代码见 Obsidian `Character/渲染实现.md`「表面材质：NapAvatarStandard 逐行移植」。

- 生成链：`gen_nap_avatar_hlsl.py`（离线，读 `F:/AnimeStudio/Exports/Shader/ZZZ_20260925` 的反汇编与 `.dat`）→ `nap_avatar_toon.hlsl` + `nap_avatar_toon_inputs.json` → `build_pyrios_materials.py`（UE）。重新生成 HLSL 后必须重跑 UE 构建。
- MI 参数：`pyrios_material_plan.py` 读三份 JSON；Unity `Color` 属性做 Gamma→Linear，`Vector` 原样；MatCap 打包数组按“该组有贴图则切片号=组号”重建（推断）。源材质启用双面 UV、对称 UV、叠加贴图或折射 MatCap 时直接报错。
- 场景级全局量：`AAADocs/Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json`。这些在游戏里来自运行时全局 cbuffer 和角色实体缓冲，导出数据里没有，文件里是编辑器起始值；对照游戏调色改这里。
- 阴影：原 Pass 的逐对象阴影与级联阴影换成组件的角色级 `KeyLightVisibility`；逐像素投影阴影仍缺。
- 不经过 UE 光照：Unlit 不吃 Lit BRDF、Lumen、天光、点光、SSAO、投影阴影。仍作用于角色像素的只有整屏阶段：高度雾/体积雾、Bloom、tonemapper 与调色；原游戏的 UberPost/Bloom 未移植。
- 网格 UV：骨骼网格需要 UV0/UV1/UV2（UV1 描边平滑法线，UV2 自发光）。AnimeStudio CLI 默认 `uvs` 设置不导出 UV2，导出时需临时打开，并用 `--merge_load` 同时加载模型块与三个材质所在块，否则 FBX 只有一个材质连接。重导用 `reimport_pyrios_mesh_uv.py`（Interchange，沿用资产里的导入设置）。
- 贴图 sRGB 照抄 Unity `m_ColorSpace`（`Content/Characters/Player/Pyrios/Materials/TextureSettings/`）；HDR 颜色按“gamma 底色 × 强度”换算；输出超过 1 的部分按 `HighlightBleed` 推白（近似游戏后处理）。依据见 Obsidian `Character/渲染实现.md`。
- 对照截图：`capture_pyrios_toon.py` → `AAADocs/References/Captures/PyriosToon/`，逐版文字结论在同目录 `INDEX.md`。像素统计用 `png_stats.py`。
- 顶点色：已用 SceneCapture 读回材质中的顶点色，RG=0.5、A=0，与 FBX 一致。

历史验证（2026-09-26，旧版组件）：将 Body 1/2 的预览 `MatCapGain` 从 0.22 降至 0.11，Weapon 从 0.30 降至 0.18；它与主光强度分开调节。UE MCP 重建、D3D12 材质重编译和 JSON/MI 核对通过，缩略图保存在 `Saved/PyriosLightMatCapReduced_20260926.png`。保存并关闭编辑器后，`GGYGOEditor Win64 Development` 完整构建、链接成功，重新启动加载了新组件。MCP Simulate 中临时 Pyrios 角色的运行时 MID 在主光强度 10 时 `SceneLightStrength=0.65`，改为 2.5 时为 0.325，改为 40 时上限为 1.0。模拟已停止，临时角色已删除，编辑器关卡的主光仍为 10。

`MAT_Pyrois_Body_FX01` 槽由独立的身体 FX 材质 `MI_Pyrois_Body_FX` 绘制，见下文「身体 FX」。Weapon01 JSON 的 `_Emission=0`；截图中的剑身蓝光不能只由当前静态武器材质解释，需另查 FX 和运行时驱动。游戏参考图还包含全局光照、曝光和后处理贡献。

主光选择把显式 `KeyLight` 与自动发现的弱引用缓存分开。自动模式优先复用有效缓存，失效后按对象路径排序选一盏有效 DirectionalLight；显式灯隐藏、关闭或无效时不擅自换灯。无有效灯时颜色为黑、`SceneLightStrength=0`，MatCap/环境底色/自发光仍由材质独立决定。缓存不写回配置。

## 资产与脚本

材质位于 `Content/Characters/Player/Pyrios/Materials/Generated/`：

- `M_Pyrois_Toon`、`M_Pyrois_Outline`
- `MI_Pyrois_Body_1`、`MI_Pyrois_Body_2`、`MI_Pyrois_Weapon01`

生成脚本：`AAADocs/Scripts/build_pyrios_materials.py`。场景级全局参数：`AAADocs/Assets/Pyrios/Rendering/Pyrios_Toon_Globals.json`。验证脚本：`AAADocs/Scripts/verify_pyrios_renderer.py`。两者可用 UE 的 Python 编辑器脚本插件运行。验证器默认只读；仅显式 `--compile` 才重编译并可能使包变脏。生成器先完整校验 JSON、全局参数、纹理、目标类型、槽位及脏包，再开始写入；BuildJournal 区分已尝试、已保存和未保存/失败，保存失败不报告整体成功。项目 `.gitignore` 仅放行部分自研 `Content` 路径；新生成的五个材质 `.uasset` 和被改动的 Pyrois 骨骼模型位于忽略的美术目录，已在本地编辑器保存，但跨 checkout 时需通过项目资产管线一同交付。`ABP_Pyrios` 位于 Git 白名单内。

编辑器预览绑定脚本：`AAADocs/Scripts/bind_pyrios_editor_preview.py`。三个 MI 已写入 Pyrois 骨骼模型对应的默认材质槽；`MAT_Pyrois_Body_FX01` 槽由 `build_pyrios_body_fx.py` 绑定 `MI_Pyrois_Body_FX`。`BP_PC_Pyrios` 的 Mesh 没有材质覆盖，因此骨骼模型缩略图、材质球和角色蓝图视口都能直接预览 Toon 材质，无需运行游戏。生成脚本重跑时也会执行同一绑定。

## 历史验证记录（2026-09-24～26，旧版组件）

以下保留已保存材质与旧链路的证据，不代表 2026-09-29 通用组件、迁移或生命周期测试通过。

- `GGYGOEditor Win64 Development` 编译通过。
- 完整 UE 编辑器使用 D3D12 对 `M_Pyrois_Toon` 和 `M_Pyrois_Outline` 调用 `MaterialEditingLibrary.recompile_material`，返回零编译错误。
- 验证了三个 MI、模型槽位，以及九张数据贴图的线性 BC7 设置。
- 加载 `BP_PC_Pyrios` 时确认它继承了 `StylizedRenderComponent`。`ABP_Pyrios` 的七条旧 `Locomotion_*` 过渡调用已换为 `bHasMoveInput`、`IsAnimationRunGait()` 和 `IsTurnBackCurveDriven()` 的蓝图组合，并在编辑器中编译、保存成功；角色蓝图也再次编译成功。
- 在 UE MCP 中用临时 `ACharacter`、Pyrois Mesh 和该组件进行 Simulate：运行时材质从模型原有的深色占位材质切换为生成的白灰/蓝色 Toon 材质；把临时组件描边宽度调到 3 cm 后，截图可见反面扩张描边，证明运行时描边链路生效。默认宽度仍为 0.6 cm。
- 编辑器内验证了 Pyrois 模型资产缩略图、`MI_Pyrois_Body_1` 材质球和 `BP_PC_Pyrios` 视口，均显示白灰/蓝色 Toon 材质；脚本再次检查材质编译、贴图和默认槽位接线通过。预览截图在 `Saved/PyriosMeshAssetPreview.png`、`Saved/PyriosMaterialSpherePreview.png`、`Saved/PyriosBlueprintViewport.png`。
- 对照两张游戏内截图后，修正了 Material ID 反序分组及原先手写的 MatCap 槽位。UE 重新编译通过，MI 的 MatCap 贴图与 JSON 自动核对通过。关闭 MatCap 的诊断预览显示胸甲原本有深灰底色，原先大面积偏白主要由错误的 MatCap 叠加造成；当前完整视觉仍需对照场景和剩余 Shader 路径处理。
- 2026-09-26 通过本地 UE MCP 8000 在当前 UE 5.8 编辑器运行生成和验证脚本；材质保存成功，两种主材质重新编译无错，三份 MI 的 JSON 高光/边缘光/阴影与预览校准参数核对通过。降低增益并重新打开模型资产窗口后的截图：`Saved/PyriosMCPMeshEditor_Final_20260926.png`。默认预览中银甲仍偏亮，须在目标关卡固定曝光、光色和姿态后再调。描边壳仍由运行时组件生成，编辑器静态视口只预览表面 Toon 材质。
- 动画蓝图修复前的文件备份在 `Saved/ABP_Pyrios_before_repair_20260924.uasset`。临时路径编译过的历史版本仅用于核对逻辑；最终修复是在原资产中替换七条节点，并保留其资产身份和其余状态机内容。

## 身体 FX

- 生成：`UnrealEditor-Cmd GGYGO.uproject -run=pythonscript -script=AAADocs/Scripts/build_pyrios_body_fx.py -AllowCommandletRendering`。需关闭编辑器或保证目标包未脏；可重复运行。
- 换算：`AAADocs/Scripts/pyrios_fx_plan.py` 可单独 `python` 运行，打印三层参数；源材质启用了 master 未实现的特性时报错。
- 层逻辑：`AAADocs/Scripts/fx_dissolve_mask_layer.hlsl`，对应 `Particles_Dissolve_CustomColor_Mask_Cap` 在 `_UsingNonPSR=1` 下的像素着色器。
- 叠加：Unity 端每个 FX 网格挂 `[FX04, FX01, FX02]` 三个材质画三遍；UE 在 `M_FX_DissolveMaskLayers` 内按同序做预乘 over 合成，`BlendMode=AlphaComposite`。
- 贴图寻址来自 `Content/Characters/Player/Pyrios/Materials/FXTextures/*.json`（AnimeStudio CLI `--types Texture2D --export_type JSON`，只有 `Eff_Mask_2408` 为 Clamp）。
- 2026-10-04 验证：SM6 编译通过、新进程重载无编译错误、MI 参数回读一致、网格槽位保存。未做视口/PIE 与游戏画面对照。设计与边界见 Obsidian `Character/渲染实现.md`「身体 FX」。
