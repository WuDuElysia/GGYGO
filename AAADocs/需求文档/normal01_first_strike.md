# 普攻第一段：首击表现与资源就绪

状态：主弧画面和冷首击已完成；普攻生产冒烟已通过（两例姿态失败用例按约定保留失败）。连段预输入的行为与 spec 原文不一致，等用户决定。

## 目标

- 普攻第一段在真实渲染下出现和原图 `AAADocs/Assets/Pyrios/FX/References/20261009_Normal01_Slash.png` 一致的连续蓝白主弧。
- 玩家第一次进游戏时，第一刀不能因为特效材质或 Niagara 还没准备好而失败。
- 普攻连段的生产冒烟（首击不等移动键、连段接续、超出窗口拒绝、按住不重复）在当前构建上通过。

## 方案要点

- 资源就绪门：
  - `UGGYGOPawnData::InputTagsRequiringRenderResources` 配置哪些能力输入要等渲染资源准备好。
  - 共享 Pawn 蓝图（`BP_PC_Pyrios`）创建 Rendering 模块的 `UGGYGONiagaraMaterialPreparation` 请求，用 `UGGYGOPawnExtensionComponent::SetAbilityInputResourcePreparation` 交给 PawnExtension 持有，再 Start。
  - HeroComponent 在首次按下时调用 `AreAbilityInputResourcesReady(InputTag, OutReason)`。未 Ready 就拒绝这次按下并打一条 Warning（`RenderResourcesNotReady`），同一次按住不补发，Ready 后也不重放旧按下。
- `UGGYGOFXNiagaraComponent` 在安装最终材质之后、调用原生 `Activate` 之前等材质准备完成；取消或退役时撤销请求。
- 主弧修复放在资产配置里：共享网格 `FXMD_DAO_001_ced427b6fbbf` 用按角点展开的 FBX（`Saved/Codex/Normal01_Migration_20261010_R1/FXMD_DAO_001_SourceCorners.fbx`）原位重导入，没有改 C++ 和 NS。

## 当前状态

- 主弧：原因是该网格由 ByControlPoint FBX 导入，每个角点的 UV0 和顶点色落到了相邻顶点上，主弧被打碎成三角碎片。重导入后，未预热的真实 D3D12 实拍中 birth／middle／fade 三帧都能看到连续的白芯蓝边月牙弧。和原图的差异：生产机位更远，弧更扁更细；白芯过曝和蓝色辉光弱于原图；背景亮、对比度低；弧下沿多一条深蓝暗边。证据 `.agents/tasks/requirements-closeout/evidence/I01.md`。
- 冷首击：全新用户目录、不预热的独立 Editor 里，Pawn 资源请求约 22 帧（0.054 s）后 Ready；第一刀在 Ready 后按下，下一帧激活，同帧出现完整主弧，GA 自然结束，没有 `RenderResourcesNotReady` 拒绝。证据 `.agents/tasks/requirements-closeout/evidence/I02.md`。
- 普攻生产冒烟：`GGYGO.AbilitySystem.PlayerCombo` 23 叶加 NativeBirth 共 24 项，两次运行都是 22 Success、2 Fail，两例 Fail 是 PoseFailure（故意注入姿态失败，生产代码按约定报 Error，测试不过滤）。只改了测试夹具：所有生产叶首按前等资源 Ready。这次也在运行时证实了 Pending 分支：资源未就绪时的按下被拒，按住约 10 s 没有补发。证据 `.agents/tasks/requirements-closeout/evidence/I08.md`。
- 活尾：Normal01 只有一个 NS，8 个发射器都只在 t=0 发射一次，最晚约 1.0 s 自然完成，早于作者 FX End（1.6834 s）。当前配置里不存在"活过 End 的特效单元"这条分支。
- 验证级别：已编译、已测试、已在 UE 里运行（真实 RHI）；不涉及联机。

## 未完成项

1. **需用户决定**：spec 要求 5.3 写的是"连段缓冲输入在下一段生效"。当前 GA 只接受攻击接续点（Normal01 在 0.275 s）之后的按下，之前的按下直接被拒，不存起来（`FGGYGOComboWindowState::Store` 没有生产调用者）。
   - A：接受现状，把 5.3 改成"接续点之后的按下在下一段生效"，然后勾选 `.kiro/specs/abilitysystem-input-request/tasks.md` 任务 5。手感不变。
   - B：另立需求接回预输入，接续点前一小段时间内的按下先存起来、开门时生效。手感会变，要重跑冒烟。
2. 未覆盖、不阻塞：
   - "被其它能力占用时缓冲"在生产 PIE 里到不了（只有攻击一个能力），只有 `Admission.GroupLifecycle` 等单元层证据；"过截止时间不再重试"没有测试叶，只有代码证据。
   - 着色器 DDC 真冷没做：要用空 DDC 启动，生成的数据远超 1 GiB，做不做由用户决定。
   - 实体键鼠手感没验。
   - 准备请求失败时终态日志只有 Verbose，玩家按下时才出 Warning；可考虑由持有方在 Failed 时打一次 Error。
3. 共用 `FXMD_DAO_001_ced427b6fbbf` 的 Normal02／03、Rush、Special 画面没复拍；ZZZ FX 目录里其它网格（`FXMD_Circle_*`、`FXMD_TRAIL_*` 等）也核出同类角点错位，画面影响未确认。两项都归[特效与音效接线](fx_audio_wiring.md)。

## 验收标准

- 至少一张自然播放的实拍能看到连续蓝白主弧，和原图的差异写明。（已满足）
- 未预热进程里第一刀成功激活且特效可见，没有因材质未就绪提前结束，等待期间没有多出来的攻击。（已满足）
- 普攻冒烟在当前构建上通过，两例姿态失败按约定保留并写明原因。（已满足）
- 连段预输入按用户选择处理，input-request 任务 5 勾选。
