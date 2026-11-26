# 特效与音效接线：普攻、技能、冲刺和转身

状态：**攻击 FX 的本批实现、编译和单机运行验证已完成；挂点入口评审缺陷已修复，统筹复核及受影响集成通过。整体音效／闪避需求仍未完成。** 用户于 2026-11-12 允许按参考重建缺失攻击 FX，随后明确接受少量外观差异，要求先完成整体和代码，挂点细调由用户后续在蓝图操作。原调用缺源的部分标为项目配置，不冒称原版调用表已恢复；不再追加第三段本体显隐制作。

## 目标

- 将有明确用途的 FX 接入角色动作，完成资源准备、播放、附着、自然结束与打断清理。
- 具体角色的时序、挂点、外观保留在蓝图／Niagara／材质资产中；C++ 提供通用机制。
- 逐动作分清已接线、未接线和原版未知项。Normal01 已认可的效果、用户其它手改和未保存工作保持。
- 本次攻击 FX 追加范围不扩展音效、E／R／F 输入、延期闪避 GA／CMC、命中或伤害规则。

## 方案要点

- **离线制作代码**：`zzz_fx_*` 消费原网格、纹理、材质和曲线，制作 UE 资产。`prepare_pyrios_attack_phases.py` 消费 [Pyrios_Attack_Phases.json](../Assets/Pyrios/FX/Pyrios_Attack_Phases.json)，用阶段局部 `System.Age` 和源内部 Delay 编排可见阶段；粒子自身 Age 和寿命保留。Normal03 后半段沿用 [Pyrios_Normal03_Phases.json](../Assets/Pyrios/FX/Pyrios_Normal03_Phases.json)。这些脚本不承担游戏运行时的第二套调度。
- **运行时代码**：`FGGYGONiagaraEffectUnit::ResolveAttachment` 统一解析单元挂点／相对变换，本地 Task 创建与 Montage FX 发布消费同一结果。默认继承原动作配置；独立覆盖只接受 Attached。动作入场与窗口消费共用 `ValidateFXSocketsOnMesh`：全部单元覆盖时忽略未使用的默认挂点，有继承单元时仍检查默认挂点，World 始终检查动作起点；创建／发布前拒绝实际使用的无效挂点或变换。沿用原 GA、Task、Publication 与资源关闭链，没有新增角色专用 C++、Tick 或管理器。
- **投影贴花**：原 `GGYGOProjectedDecalRenderer` 在引擎重建代理、首次 PostTick 尚未发生时，沿同一 GT 准备方法提交当前真实粒子数据；同时补齐 Native Decal Renderer 初始化。数据仍须匹配原实例、当前缓冲、年龄和材质，缺项明确失败。此早期修正随本次代码交付，已有最终编译及 Normal02 地面可见性证据；未单独覆盖所有代理重建场景。
- **生产接线**：`wire_pyrios_attack_phases.py` 只替换三动作的 FX 单元，并同步 `BP_PC_Pyrios.AbilityInputRenderSystems`。具体挂点保存在 GA，正常闭窗使用 `DeactivateDetachKeepWorld`，打断使用 `DestroyImmediately`；发布记录携带解析后的单元变换。
- **准备入口**：生产 Pawn 的原资源门准备全部实际引用系统；Pending 时仍拒绝本次按下，不缓存或补发输入。测试也等待这条原链，不额外预热或绕过准入。
- **源缺项**：ExSpecial 五根的已知静态资源与曲线已恢复；八个 Mesh 的未知尾部仍未解释，宿主 Mono 类型缺完整 TypeTree。除已查明的金色武器层外，原动作 caller、准确时点和移除条件仍未知；当前阶段配置依据参考姿态、武器轨迹及源曲线制作。
- 制作和取证依赖本机 `Saved/Codex/FXRestoration_20261022_F1`、`Saved/Codex/FXProduction_20261026_R1` 与本需求的源缓存。它们及被忽略的角色素材仍是本机依赖；仓库脚本不代表无素材的全新检出可以独立重建。

### 蓝图挂点入口

打开对应 `GA_Pyrios_Attack_*` 的 **Class Defaults → Combo Steps → FX**。Combo 的第 0／1／2 项分别为三段普攻，Special／ExSpecial 使用第 0 项。

- `Space=Attached` 时，FX 上的 `SocketName`、`LocalTransform` 是整组默认值。
- 要单独移动一层，在 `SystemUnits` 对应项启用 `OverrideAttachment`，填写该项的 `SocketName` 和 `LocalTransform`。此变换**替换**整组默认值；空挂点表示角色 Mesh 根。平移单位为 cm，旋转为度。
- ExSpecial 金色武器层当前挂 `Ctr_Weapon_A_01`。原地面层仍用 Mesh 根；Normal02 的场地表现沿用 −64 cm。可见刀带直接从实际角色 Mesh 取武器骨世界坐标，独立于这一偏移。
- 修改已有单元挂点不需改 C++。新增 Niagara 系统引用时同步角色 `AbilityInputRenderSystems`；调整阶段时点在 Niagara／上述配置中处理，生命周期仍由原 Montage FX 窗口管理。

## 当前状态

| 动作 | 已完成 | 仍保留的边界 |
| --- | --- | --- |
| Normal01 | 原正式组合、声音与命中 Cue 保持；沿用已完成的主弧及冷首击验证 | 本批未重复制作 |
| Normal02 | 地面投影相对 Z=−64 cm 已保存，中心约 2.15 cm；原尺寸保持。生产输入、地面可见贡献及三段清理已验证 | 原版精确触发帧、完整形态等价未证 |
| Normal03 | 7 个正式单元，前半段残影／刀光分阶段，后半段下劈和地面爆发保留；自然结束与取消通过 | 本体仍显示，残影／扰动的外观有差异；按用户最新要求留待视觉调整，不加本体显隐逻辑 |
| Special01 | 2 个正式单元，按三次实际挥刀配置阶段；自然结束／取消／清理通过，当前项目命中窗实跑 3 次命中 | 默认 PawnData 未授予，E／R／F 仍延期；原版时点及声音选用未知 |
| ExSpecial01 | 8 个正式单元：补齐前四斩与末段刃波，保留旧 06／07 及金色武器层；自然结束／取消／清理通过，实跑 4 次命中 | 旧 06／07 造成末段横跨画面的暗色长条，隔离实拍已定位；挂点和外观留作后续调整。原声音与整体视觉等价未证 |
| Rush | 已有 `NS_Pyrios_Rush_MainComposition_291964a4dd84` 素材，尚无生产引用 | 当前移动表现无 Rush 攻击入口；不把它当普通 Sprint 接入，不新增 GA／输入 |
| 冲刺／前后闪避 | 已核用户入口 `L_Movement_Test + LeftShift`。真实输入仍为 `IA_Sprint`，站立／移动两次均未激活 GA、Montage 或 Niagara | 当前授予的空图 `GA_Dodge / InputTag.Dodge` 与 Sprint 不匹配；恢复真正闪避的玩法选择仍待原答复，候选 FX 未擅自接入 |
| TurnBack | 按用户选择，进入 Turning 播第一段 Foley 一次；连续两次入场均只播一次，停止与原生释放通过 | 第二段未接；原版时点、准确 FX 来源及联机纠正／重放未验 |

- 三动作共制作 **16 个系统／337 个发射器**，全部编译保存且无 Niagara 编译警告。ExSpecial 缺失的五根包含 42 个源发射器，已进入当前正式组合。角色准备列表为 **19 个系统**。
- 修复 ExSpecial 末段场材质漏开 Niagara Mesh 用途的问题，通用制作器与准确 Master 均已更新；16 个系统通过原生材质准备。20 个既有 FX 网格的角点位置／UV0／alpha 修复已保存；新增 ExSpecial 八个网格的同类读回也全部吻合。
- 两技能命中窗沿用用户已确认的项目配置和原武器去重链。Special：0.1333～0.25、0.4333～0.55、0.7667～0.9 秒。ExSpecial：0～0.05、0.2～0.2833、0.4～0.5、0.55～0.65、0.85～0.9667、1.2667～1.4833 秒。这些不是原版命中帧。
- TurnBack 由角色 Blueprint 订阅原 `OnCharacterMovementUpdated`，读取 CMC `GetTurnBackPhase()` 的 Turning 入场边沿播放一次，离开后复位。声音附着 Mesh 并自然销毁；ABP 未修改，未增加移动状态或 Tick。
- 三招原声音调用条件尚未恢复。缓存录像只有逐帧图、没有原 MP4 音轨；AnimeStudio 行为／Animator 数据未提供完整声音调用表。`EvadeAid_Start/End` 属于闪避支援，不能作为普通 Sprint 来源。声音返修详见 [normal03_audio](normal03_audio.md)。

### 已完成验证

以下本机证据统一位于 `Saved/Codex/PyriosActionFX_20261111/`：

| 范围 | 结果与证据 |
| --- | --- |
| 最终编译 | `attack_fx_final_build.log`：GGYGOEditor Win64 Development 成功 |
| 原生自动化 | `CodeValidation_20261112/Report/index.json`：8 项 FX 配置／发布回归均成功；其中 2 项既有夹具带残余 lease teardown 警告，诊断保留 |
| 挂点入口补修 | `AttachmentEntryFix_20261112/build.log` 编译成功；`Report/index.json` 的 10 项入口／窗口／配置／发布回归通过。新增用例经真实 PlayerInput→Hero→ASC 入口覆盖 Attached 全覆盖、有继承者、World 无效起点及有效起点四种情况；拒绝诊断保留。`Runtime_Special/run.json` 进一步验证实际窗口：坏默认挂点＋两个覆盖单元正常创建，5 张实拍、3 次命中、自然结束及全 FX 清理通过；`restored.json` 确认临时配置恢复且未保存 |
| 统筹集成 | `RootIntegration_20261112/build.log`：共享工作树增量构建成功，目标已是最新；`Report/index.json`：10 项相关回归成功，保留两项既有清理警告。`Runtime/run.json`：D3D12 普攻和 ExSpecial 两场冒烟通过，本次命中分别为 3／5 次，实际 FX 创建、自然结束及全部清理通过；7 张截图落盘，已查看普攻地面层和强化技能武器发光画面。临时授予恢复、PIE 结束后关闭自有 Editor，无生产资产保存；此轮不补签逐层视觉等价或独立挂点联机 |
| Python | 本批变换链 13 项、原 Shader 22 项、Renderer 9 项通过；纹理整数读取／稀疏 UV 的 3 项针对性检查也通过（`CodeValidation_20261112/source_import_checks.log`）。见 `VisualSourceAudit_R1/*regression.log` 与 `AttackPhasePreparation_20261112/particle_renderer_regression_r2.log` |
| 资产制作及接线 | `AttackPhaseAuthor_20261112/result.json`、`AttackPhaseWiring_20261112_R3/wiring.json`：16 系统完成，Normal03／Special／ExSpecial 为 7／2／8 单元；`final_readback.json` 确认运行后磁盘接线保持 |
| 自然结束 | `AttackPhaseRuntime_Natural_R1/run.json`：Combo／Special／ExSpecial 均通过；51 张实拍，命中分别 2／3／4 次，原 GA 自然结束且 FX 全部清理 |
| 取消 | `AttackPhaseRuntime_Cancel_R1/run.json`：三个场景均通过；原 GA Cancel 后当前段 FX 立即释放，最终全 FX 清理；20 张实拍。Combo 取消后自然视口已核验，见下节 |
| 武器跟随 | 上述自然运行中 ExSpecial 金色层 32 次有效附着采样均吻合 `Ctr_Weapon_A_01`；此前完整尾段观察也已看到余光消失 |
| 可见性诊断 | `AttackPhaseRuntime_Side_R1/` 可见新斩击弧，方向吻合武器轨迹；`AttackPhaseRuntime_FrontOnly_R2/` 隔离旧 06／07 后末段暗长条消失，恢复原配置且未保存诊断修改 |
| 几何 | `Mesh_Repair_R1/mesh_checks.json` 与 `ExSpecialFrontMeshAudit_20261112/result.json`：既有 20 个和新增 8 个网格角点检查通过 |

技能测试在自有 Editor 内临时授予，经真实 InputKey→Process／ASC 入口激活，结束后恢复且不保存临时授予。诊断机位与 MotionBlur 设置已恢复，自有 UE／UBT 均退出。代码自审覆盖默认继承、独立覆盖、本地创建、发布记录及原关闭链；具体招式仍由资产决定。

### 连段取消画面

`AttackPhaseRuntime_Cancel_R1/Combo/observations.json` 与 `frames.jsonl` 已覆盖真实取消前后。第三段（step=2）在 0.25735 秒、frame 55323 经原 `GameplayAbility.CancelAbility` 取消；7 个当前段系统均在该帧记录 `TerminalDispatched / Abort`，取消返回后当前段组件为空，原 GA 完整退出且 `original_exit_cancelled=true`。frame 55324 起的采样及最终清理均无 FX。

已查看[取消前画面](../../Saved/Codex/PyriosActionFX_20261111/AttackPhaseRuntime_Cancel_R1/Combo/008_2_0.213.png)和[取消后画面](../../Saved/Codex/PyriosActionFX_20261111/AttackPhaseRuntime_Cancel_R1/Combo/009_2_0.257.png)：前者弧光／残影仍在，后者已消失。观察脚本在 Slate post-tick 内先申请截帧、再调用取消；截帧接口只订阅原游戏 viewport 的自然渲染回调。第 009 张虽在取消当帧申请，实际 `render_frame=55324`，晚于取消；第 008 张实际渲染帧为 55323，发生在该帧 post-tick 取消前。两张 PNG 均完成写入和读回校验，不能按文件名中的请求时刻把第 009 张归为取消前画面。原运行日志为 `AttackPhaseAuthor_20261112/editor.log` 的 Combo 取消场景结果。

该结果验证当前段的 Abort 清除；正常闭窗的 `DeactivateDetachKeepWorld` 尾迹仍按原自然结束证据验收，不要求早前已正常结束的尾迹随当前段一同立即消失，也不据这组图补签正常活尾。本次仅复核既有图、观察记录与截帧实现，无代码／资产修改、UE 重跑或新增构建。发布 spec 的 Requirement 5.3 仍因 TurnBack 烟雾来源未定而保持部分完成。

## 未完成项

- 按用户最新决定，挂点细调、Normal03 本体／残影差异及 ExSpecial 旧层外观交后续蓝图／资产调整。当前实拍不等于原版逐层或逐像素等价。
- 原声音选用条件、空挥／命中实际听感仍未验收；本批没有用猜测改声音 Notify。Rush 和 LeftShift 的玩法／生产入口沿原待定项处理。
- 本批单元独立挂点的真实联机、Cook、性能和物理输入设备未验；现有发布回归不替代这些结论。
- 普攻 GA 二进制仍混有用户先前未提交改动，保留本机成果，不将其整体提交；相关 FX 重接脚本和配置入库。被忽略的角色素材不强制入库。

## 验收标准

- **本批已满足**：实际引用和资源准备完整；阶段 FX 在真实角色动作中运行；每层附着可在蓝图配置；自然结束及取消清理通过；编译和直接相关回归通过。可见差异与未知来源明确记录。
- **整体仍待满足**：音频实际内容与空挥／命中触发对应且无重复；Rush／闪避按用户确定的入口接入；需要宣称原版等价的部分有原来源和对照证据。用户接受小幅视觉差异不代表这些独立问题已解决。


## 2026-11-25 战斗表现与急转

5.9 副本的普攻前两段沿 Montage 原有 FX 窗口生成刀带。刀柄取当前角色 Mesh 上的 Ctr_Weapon_A_02。刀尖按 LOD0 最外端刃面顶点在 Ctr_Weapon_B_05 下的局部坐标随姿态变换，该顶点对末骨的蒙皮权重为 99.84%。刀带按这两端的位置、距离和方向生成，已采样的轨迹留在世界空间。一段保留 0.14 秒，二段保留 0.205 秒，主刀先消退，外弦后消退。前两段关闭漂出的锥形烟团。第二段另外关闭模糊烟、自由散点、碎块和重复的代理拖尾，接地投影与签名扭曲场各自保留。特殊技沿用暖金色[笔触纹理](../Assets/Pyrios/FX/T_Pyrios_Emberglow_Stroke.png)。实战对照看了[佩洛伊斯演示第 2 P，1 分 04 秒起](https://www.bilibili.com/video/BV1sGEy6mEKe/?p=2&t=64)。五个既有命中 Cue 使用独立接触星屑并保留命中音效。两份闪避资产是候选表现，独立闪避输入仍待玩法确定。

5.9 副本用正式攻击键在 D3D12 PIE 打完三段，各命中一次，动作自然收尾，记录到音效播放，FX 组件正常释放。二段挥刀至 0.088 秒时，将 Niagara 最新刀带两端与同帧角色刀柄、LOD0 蒙皮刀尖对照，两端误差均小于 0.01 厘米。侧面实拍可见外侧亮线和内层笔触，原先飞出画面的蓝灰烟团已移除。特殊技和强化特殊技沿用本批暖色材质实测，各命中 3 次和 5 次。[二段慢放](../../Saved/Codex/PyriosBladeReview/Pyrios_Normal02.webp) · [三连日志](../../Saved/Codex/PyriosBladeReview/side.log) · [特殊技日志](../../Saved/Codex/PyriosBladeReview/play.log)

三段普攻采用单独绘制的[棱纹贴图](../Assets/Pyrios/FX/T_Pyrios_PrismInlay.png)。一段以冰青外刃带出靛紫刀面。二段沿同一条武器轨迹错峰展开紫金外弦，外刃的一个历史采样短暂折光。第三段前三刀各生成一个独立的菱形切面。先从实际武器采样入刃与出刃的位置，在两次采样之间落痕；参考录像中的平斩、斜劈和上挑确定切面方向。亮刃沿行刀方向显现，斩痕留在世界坐标中整道退去。刀面、外侧亮刃和高光遮罩直接采样 Normal03 已导入的原图 `Eff_MeleeTrail_239`、`Eff_MeleeTrail_089_LYX_01`、`Eff_MeleeTrail_116_YZ_06`。三刀的切面全长约 6.99、6.48、5.37 米。刃腹保留靛蓝色和原图明暗，两端收尖。切面外的折射层跟随同一把刀的显影、位置及退光，使用原 Distor 层的扰动图 `Eff_Noise_098` 和形状遮罩 `Eff_MeleeTrail_244`，按刀线的屏幕投影方向采样背景。前三刀以后，转身横扫继续按刀根与实际刀尖逐帧生成闭合刀带。砸地沿用原冲击窗口。地面查询命中后，[岩面裂纹](../Assets/Pyrios/FX/T_Pyrios_SlamFracture.png) 从交点向外撕开，两个方向的投影跨度分别扩大为原来的 2.57 和 2.39 倍。十块有厚度的断板在同一地面法向上翘起、回落，五块飞石和原有尘环接续冲击，亮缝冷却后留下暗裂。断板只参与渲染。

本地原版实录 8.57–8.85 秒可见第一刀伸至画面边缘、后两刀交错，角色附近的地板线随残像扭曲。局部折射的范围、强度和三刀尺寸为画面对照重建。UE 5.9 D3D12 单机使用正式攻击键，玩家视角和侧面均拍到三刀依次出现、落点保持固定、后续横扫与砸地衔接，两轮均三段命中并自然结束。单独停在同一蒙太奇姿态，关闭、恢复折射后，切面附近的地面与影子边缘出现可复现的偏移。编译与实拍覆盖本地单机桌面渲染，联机与打包未测。[原版动作演示](https://www.bilibili.com/video/BV1sGEy6mEKe/?p=2&t=64) · [三刀分帧](../../Saved/Codex/PyriosBladeReview/Pyrios_SpaceCuts.jpg) · [前后版本实机对照](../../Saved/Codex/PyriosBladeReview/Pyrios_SpaceCuts.mp4) · [同姿态折射对照](../../Saved/Codex/PyriosBladeReview/Pyrios_SpaceCut_Refraction.jpg)

D3D12 独立 PIE 以正式普攻输入实拍。三段各命中一次，动作自然结束，FX 正常释放。二段在 0.148 秒的粒子读回中有一个折光标记。此次覆盖单机运行和侧面视觉。联机、Cook 和性能未复测。[原速录像](../../Saved/Codex/PyriosBladeReview/Pyrios_Prism_Combo.mp4) · [慢放](../../Saved/Codex/PyriosBladeReview/Pyrios_Prism_Combo.webp) · [运行日志](../../Saved/Codex/PyriosBladeReview/prism.log)

UE 5.9 D3D12 单机用侧面和斜侧面各打完一次三连，每段各命中一次，自然收招，特效正常释放。第三段抽查 33 帧刀带前缘，其中 13 帧还与实际蒙皮刀尖顶点比对，最大偏差 0.018 厘米。实拍可见刃面厚度、转身后的贴刀余光以及砸地留在原处的裂纹。联机、Cook 和性能未复测。[双机位慢放](../../Saved/Codex/PyriosBladeReview/Pyrios_BladeVolume.mp4) · [侧面日志](../../Saved/Codex/PyriosBladeReview/bevel_side.log) · [斜侧日志](../../Saved/Codex/PyriosBladeReview/bevel_angle.log)

UE 5.9 D3D12 单机在玩家视角和侧面各从正式攻击键打完三连，每轮三段均命中、自然收招且特效正常释放。实拍与 Niagara 粒子读回确认冲击位置固定，断板随冲击抬升回落。联机、Cook 与性能未复测。[玩家视角与侧面录像](../../Saved/Codex/PyriosBladeReview/Pyrios_GroundBreak.mp4) · [砸地分解图](../../Saved/Codex/PyriosBladeReview/Pyrios_GroundBreak_side.jpg)

CMC 已经转向时，角色骨盆仍大幅反拧。本次只编辑 TurnBack 的 Bip001 旋转轨。原位移和转向曲线、刹步及首尾跑姿均保留。144 个源采样中最大修正 65.5°，修后髋部相对起始朝向最多 30°。月坑环站连续反向输入两次，均经过 Turning、Braking、RunOut 后回到跑步。

月坑环站 D3D12 实机通过实际攻击键打出第一刀。测试场景中的普攻整套、特殊技、强化特殊技均观察到伤害、音效、Niagara、自然收尾与特效释放。两项特殊技走既有的内存临时授予。首轮曾因原首击扭曲材质的着色器不可用而拒绝攻击，重编实际依赖的母版及实例后，在新进程确认 Ready。本轮未复验联机或打包。

本地证据见[战斗实拍](../../Saved/Codex/PyriosCombatArt/Pyrios_Combat.jpg)和[急转实拍](../../Saved/Codex/PyriosCombatArt/turn.png)，同目录的 player_pass.log 和 combat.log 记录了验证结果。角色素材沿用仓库现有忽略范围。持有原素材的副本可在独立编辑器执行[制作脚本](../Scripts/refine_pyrios_combat.py)。
