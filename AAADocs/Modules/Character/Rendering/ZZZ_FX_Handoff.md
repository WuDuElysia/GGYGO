# ZZZ / Pyrios FX 当前交接

当前需求、共享窗口和原作者安排以[当前排程](../../../Coordination/Module_Repair_Parallel_Schedule.md#当前窗口与关键路径)为准。本页保留必要契约、未完成项和证据入口；已结束过程及旧租约移至[历史原文](ZZZ_FX_Handoff_History_20261013.md)，不据历史命令操作当前工程。后续交付覆盖当前结论与入口，已结束过程及时归档。

## 当前任务与未完成项

目标为 Special、ExSpecial、Rush、三普攻及现有冲刺闪避／TurnBack 的可定位 FX，还原到角色及动作中。斗篷上沿固定缺口仍只读暂挂，由 Character Rendering 牵头；延期 Dodge GA／CMC 不恢复。本批完整还原未完成。

| 工作线 | 已有证据及当前缺口 |
| --- | --- |
| 斗篷布料 | 历史源对象／槽位和 FBX 核对未定位明确漏项，不能证明当前 UE 蒙皮、覆盖或深度等价；缺口根因与同姿态复现仍未验，见[身体 FX 历史证据](ZZZ_FX_Handoff_History_20261013.md#14-身体-fx历史生成检查通过斗篷缺口仍开放) |
| Normal01 | 七层历史系统有编译／保存／Cold／有限生产叶证据；源八层中的 `Main_Distor` 未恢复。当前时序属 `project_test`，原 cue、完整源及原游戏同帧视觉未验，见[有限检查点](ZZZ_FX_Handoff_History_20261013.md#normal01-有限生产链检查点2026-10-09) |
| Normal03_02 残影 | 原九失败包及保全仍保留；R5 同九资源 Recovery 只认资源读回，Cold／GPU／可见图／动作未验。R7 仅有旧 A2 宿主离线适配，不代当前宿主准入或后继 Gameplay |
| Special Decal | 两缓存7924B及唯一Material5652B均已实际读回；真实Material数据通过离线严格适配，正式consumer仍未应用。默认Mesh、Shader正文及四非空Texture的完整消费链仍缺；不由静态值证明cue／fade／stop |
| 其它动作／Back03 | 触发帧、段序／Main/End／Hit 分配、挂点、TRS、Follow、Age、Fade、Stop 的真实来源仍缺；Back03 历史修正后实际烟雾可见性仍未闭合。已有包或离线计划不代动作还原 |

## 稳定契约

- GA 管动作生命周期；Animation 管姿态／窗口，Combat 管原 Task 身份及命中，FX Task 管自有组件、Niagara 管模拟／绘制。不得用新 Tick、动画时钟或第二套调度竞争权威状态。
- 数值取自真实导出。完整 prefab 任一启用可见分支或必要源／消费者无效，整批预检失败、资产零写入；不能省略分支冒称完整还原。明确选定子树的 `NS_PREVIEW` 保留祖先变换，并标明父 prefab、原时序与动作未验。
- 未知项明确保留未知；不猜 Notify 帧／socket，不拿 HitWindow、Clip 长度或音频名称关联代 cue，不用默认 Mesh、替代效果或未读脚本补闭包。元数据、正文解析、编译、保存、Cold、画面及动作分别验收。
- 角色／FX 材质使用 Unlit。身体 FX 保持独立槽与三层合成职责；源／UE 深度和屏幕 UV 等价尚未确认，不把 soft-fade 候选当斗篷已证根因。
- 取消、自然结束、切步、切角色及 PIE 退出须按原身份释放自有实例、委托和持有资源；源码接线或资源图不能替代整链清理与运行验收。

## 最小来源缺口

Special 节点为 `Eff_Pyrois_Attack_Special_01_05_Decal/root (1)/decal`。既有解析输出已证 PS 的 `looping=false`、`playOnAwake=true`、`prewarm=false`、`lengthInSec=0.10000000149011612`、`stopAction=0`；`startDelay` 为 state0、scalar/minScalar 均 0，`startLifetime` 为 state0、scalar `0.6000000238418579`、minScalar `5`。这些仅为静态 PS 参数，不填 Notify、动作 Stop 或宿主回收时刻。最小生命周期前置为源宿主创建／启用触发、动态 TRS／Follow，以及正常结束／取消时源 Stop-release 对应的对象和字段，仍 unknown。

已读 PSR 的 `m_Mesh` 为 `fileID=6`、`pathID="10202"`；[Catalog 993312222](F:/AnimeStudio/Exports/ZZZ/Pyrois_SkillFX_Evidence/Catalog/993312222.json) 的 external6 指向 `unity default resources`，source／block 为 null，目标文件及对象身份未定位。不能按编号猜 Cube／Plane／Quad；已有源 CAB 中未找到该 PID 也不定位外部默认资源。

同 Catalog 的 external7 映射 Material 至 `1304474969 / CAB-48fb2c6b91d0e82477fd602c79359f71 / "-6558761215025503264"`。[Material Catalog](F:/AnimeStudio/Exports/ZZZ/Pyrois_SkillFX_Evidence/Catalog/1304474969.json) 的 `files[231]` 为 class21、5652B。v3 已按 Core `pathID==0 || fileID<0` 输出精确 `IsNull`，合法空引用不进入 external 表；这不证明实际 Material、Shader、贴图或运行依赖闭包已读。

唯一Material的[实际输出](F:/AnimeStudio/_work/pyrois_special_decal_material_prepare_20261013/Exports/Read_20261016_R1/worker.stdout.json)已核收（SHA`5BD64A7AB236DF5804A48A214450813B23CA4CFF7A749AA0D05299022EA7F71F`），5652B完整解析、原98160句柄exit0、[保护回执](F:/AnimeStudio/_work/pyrois_special_decal_material_prepare_20261013/Runtime/logs/MaterialRead_20261016_R1/after.json)前后公共／动态／runtime差集0。真实171float／19color／9Texture槽经冻结投影适配无损消费（624290），原数据不改、真实plan未调用；queue3000、三个关键词及`_OpaquenessFadeByScript=1`仅静态字段。Shader引用PID`3236134733678291145`；非空仅`_BumpMap/1739144626348892680`、`_DissolveTex/623606353444750246`、`_MainTex/8075034578055661614`、`_MaskMap/-8879785284717540773`，按该输出externals取CAB，不复读源块。

现存Shader输出已定位为`Assets/132714511/CAB-91fe6c8dbdab2dbcc8fe53cb669f78b3/Shader/3236134733678291145.{native.json,shader}`（均在`Pyrois_SkillFX_Evidence`下）：真实name=`miHoYo/Particles/Particles_Decal`，126 Properties，唯一Pass=`TransparentHalfResDecal`，Cull Front／ZTest Greater／ZWrite Off，实际HalfRes四因子1／5／7／0。旧文本流式投影可保留blob关键词：D3D11 VP2／FP3840；指定标签条件下VP空标签与FP global三材质词／local空各1候选，位于154／9507行，disassembly hash分别`a40afa16a4c322`／`d7fdbec172180b22`，Resource按Converter顺序回联native VP0/blob0、FP18/blob20。未闭合DXBC字节或原运行选择；832个FP超集不能当同一变体。该FP候选666条asm中四材质槽均有采样指令，但只认候选程序事实；其它场景深度／法线／阴影／GBuffer／环境与LUT依赖不取默认。

实际consumer三阻断已核：`material.pick_pass`拒绝HalfResDecal（dce638）；`native_shader.render_state:93`拒cull1／ztest5；`select_native`把完整材质词当作各stage local，按现存候选标签两stage均匹配0（37b7a3），而只读`inspect_program_candidates`已区分各候选声明，不能把审计投影当运行选型。另native JSON已有buffer slots4/5/6：`g_vLightListGlobal/g_vLayeredOffsetsBuffer/_EnvLightDatas`；旧disassembly的stride为4／4／52及5条结构化读取，Converter遗漏m_BufferParams绑定输出，T解析仅cb/tex/smp、无buffer类别，当前翻译器也无该structured-load与cube-array消费支持。最小后继离线保真写集候选为Resource的`ShaderConverter.cs`绑定输出＋FX的`zzz_dxbc_hlsl.py`绑定解析；Pass／执行关键词及decal环境须另行收敛，不能只加白名单或套相近Pass。本轮不改码、不造新audit/wrapper/报告。

四份已存Texture native.json已逐一核SHA及消费字段（1e2539）：Bump为512×2048／mip12／ColorSpace0，Dissolve为256²／mip9／ColorSpace1，Main和Mask均512×2048／mip12／ColorSpace1；全部format25／Filter1／Aniso1／MipBias0。已知旧WrapMode(U)依次0／1／0／0，V/W被原parser丢弃；现consumer复制U/V不证明原V，不补值。resS声明均offset0、size依次1398160／87408／1398160／1398160，pixel／texturedata未读。四精确引用的像素解码准备可独立推进，不以Shader实际采样作前置；实际PNG导出仍须独立窗，导出／绑定／采样分列。缺V/W的最小读取范围由Resource按既有精确缓存头定位，尚未授权新正文。保持R3／P20／P21及业务保护，无Source／资产／UE／构建写窗。

Material v3 的属性数组不能直接传入现有 `zzz_fx_material.material_value`：合成消费已复现真实属性被误认缺失、转取 Shader 默认值。消费前须将三类属性按 `name` 转为字典，保持颜色 `r/g/b/a`，将 Tiling／Offset 的 `x/y` 改为 `X/Y`，Texture 指针保留 `m_FileID`、完整十进制字符串 `m_PathID` 和精确 `IsNull`。同类重复名、缺必需字段、非有限数值或矛盾空引用拒绝；真实空数组才转空字典。约定映射的合成消费已核数值、UV 和指针精度，真实 Material.plan 未调用，Shader 名称／Properties 及 cue 不推断。

自有新 Saved 的[离线适配原型](../../../../Saved/Codex/PyriosMaterialConsumerAdapter_20261014/adapter.py)只接收显式 `result.material`，不读文件或依赖；[合成消费探针](../../../../Saved/Codex/PyriosMaterialConsumerAdapter_20261014/probe.py)通过原 `material_value` 与构建入口的隔离 AST，已核源值、UV、完整 Int64、合法空引用／Shader 默认和18项拒绝。实际 `plan`／Shader/native 未调用，无新源正文读取，旧 consumer 文件未改。此为正式接线准备，不认生产修复。

正式两脚本的[离线补丁](../../../../Saved/Codex/PyriosMaterialConsumerSourcePatch_20261014/material-input.patch)已准备（SHA`f7e08682c3afbbf44b465efb05935ef2dc13e22078bb50facd5edfb10d85c25e`）：复用已核严格适配到唯一`material_input`，接入`build.material_plan`、`build.inspect_source_programs`两处Shader PID查询之前及`material.plan`的JSON读取后。[准确前后身份](../../../../Saved/Codex/PyriosMaterialConsumerSourcePatch_20261014/source_identity.json)与[必要检查](../../../../Saved/Codex/PyriosMaterialConsumerSourcePatch_20261014/check_result.json)已交统筹；7组／18拒绝及`git apply --check`通过，正式0应用，旧字典／仅Shader头、合法空Shader／默认／native分支保留，未知Cue／TRS／Follow／Stop未改。旧Scripts仍冻结，原FX作者待统筹同波次应用；Rendering表面材质走独立`pyrios_material_plan.py`，其它源未获FX写权。

[Special 音频 mapping](F:/AnimeStudio/Exports/ZZZ/Avatar_Male_Size03_Pyrois_Model/Audio/Avatar_Male_Size03_Pyrois_Ani_Attack_Special_01/mapping.json) 只提供名称关联，不含 Notify timing。Mono 的 `WinError5` 和未读正文边界保留。R2 一次外读仍待原真人，不继承给 Material／Mono／Shader／Clip／外 stream；已消费的两 `.dat` 不重读。

Normal01 缺层准确入口为 [I307](F:/AnimeStudio/Exports/ZZZ/Pyrois_SkillFX/Raw/3077361824/fx_index.json) 的 `Eff_Pyrois_Attack_Normal_01_01_Trail/root/Trail/rot/Main_Distor`，Catalog `3077361824/files[139] / CAB-c174039fb56f184426cf7cb22563b8a3`。GO `"-5299499679591739929"`、Transform `"-1426497381650600290"`；PS `"-4851021293888173413"`（class198、start23504／7804B）、PSR `"2502405610036890719"`（class199、start75128／312B）、Mono `"-3750547025713878578"`（class114、start32024／272B）均已按元数据核对。

该节点五层静态`pos/rot/scale`链齐全；源根`pos.z=4.778565883636475`不作为角色局部偏移。内部`root/Trail/rot`旋转曲线现已读回，根实例绑定、动态Follow及停止业务仍未解。prefab根有九个Mono和一个Animation，`root/Trail/rot`各一个Mono；根Animation及公共Mono标准头已读，其余字段／控制职责仍未明，叶272B不作cue／生命周期来源，也不据静态父子关系选择socket。八类代表节点的索引／Catalog身份仍只认候选，不证明动作选用了相应prefab；TurnBack名称匹配0只覆盖已有两个索引及原manifest，不推断游戏无FX。

八类代表根另按 Catalog 的 `(scriptID, oldTypeHash)` 核出五组共同 Mono 类型；`typeID` 只在各 CAB 内使用，不能跨文件当脚本身份。共同类型用于收敛下一读取候选，Script 名称、enabled／正文及控制职责仍 unknown，不能按字节数或共同出现推定 cue／Follow／Stop。

[84B读取证据](F:/AnimeStudio/_work/pyrois_source_read_prepare_20261014/Runs/Read_01/diagnostic.json)已实际核收，SHA256 `A52FB4A86F4909E7C90E640F59DA77AB948766471926257CD8754A33DA1C5A50`：根 Animation56B、根 Mono 标准头28B各单次打开／读取，exit0、stderr0；完整共享父保护差集为空，runtime及缓存身份不变。Animation采用布局A完整消耗，默认与唯一Clip均为`fileID=11/PID="8995184058150946407"`；两个组件GO均为`fileID=0/PID="-8525558595298345743"`，Mono头Script为`fileID=0/PID="-5782287170244253598"`。Animation的enabled=1／playAutomatically=true及Mono原始enabledByte=1仅认静态字段；cue／挂点／动态TRS／Follow／Stop仍unknown。Mono余下96B、叶272B和引用正文未读，不重复84B读取。

真实 Script 引用已联结同CAB的 class115／type0／start4096／104B；Clip引用另按[Catalog3817944121](F:/AnimeStudio/Exports/ZZZ/Pyrois_SkillFX_Evidence/Catalog/3817944121.json)核为`files[41] / CAB-87f04295dea13afff46f39458be59dca`、class74／type1／start4272／2892B。两目标Raw缓存仅文件属性核对为存在且大小匹配，正文均未读。旧diagnostic的外部未联结记录保持原样。

[104B实读证据](F:/AnimeStudio/_work/pyrois_reference_read_prepare_20261014/Script_Read_01/diagnostic.json)已核收，SHA256`9D941FA453E22C0307DA4EE083A97BEDC05923CC4EF31766E8E67566070B10A7`：各open/read一次，exit0／6.172s／stderr0，完整消耗；AM独立Cold新完整24组前后无差，runtime及缓存身份不变。原始name/class均为`MonoEffectPluginFollow`、namespace=`MoleMole`、assembly=`Logic.dll`；PropertiesHash`438f2807504e8913dbe22599a4f7790d`与根Mono组件类型哈希一致。只证明类型身份，未加载assembly或引用，Follow／role／cue／挂点／Stop仍unknown；组件余96B未读，不重复104B读取。[当时读取方案](F:/AnimeStudio/_work/pyrois_reference_read_prepare_20261014/read_plan.md)保留为冻结执行输入，不以其旧准备状态替代该实读收据。

[2892B实读证据](F:/AnimeStudio/_work/pyrois_clip_read_prepare_20261014/Clip_Read_01/diagnostic.json)已核收，SHA`D16E3E1BF997FCAB01D8619203A01C0727B3ED897853DC0E57498ACD857E69FB`：单open/read、完整消耗、exit0／6.485s／stderr0，runtime／缓存不变，S1当前25组前后空；S1失败after=false／normalExit=false／UEexit=-1原样保留，不由本次child成功替代。实际名`Eff_Pyrois_Attack_Normal_01_Trail`、legacy=true／compressed=false／sample60／wrap0；仅一条`root/Trail/rot`四元数旋转曲线、11键、0至`0.1666666716337204`，pre/post均2、weightedMode均0。其它曲线／Events／genericBindings／pptrMappings为空，StreamData为空0／0，ACL两blob为空，外流／引用／codec读取0。`m_MuscleClip.m_StopTime=1.0`不作为该键范围或动作总时长，不重复2892B读取。

曲线目标Transform为`"4026277479175883537"`，其子节点含Main_Distor；索引静态旋转等于曲线末帧而非首帧。既有`zzz_fx_niagara.node_chain`隔离AST按`System.Age`实际消费11键，生成动画链且目标rot无切变（工具证据3fe04f）；没有新时钟，未做UE／Niagara编译／生产接线或范围外wrap验证。现有七层是否已绑定同一原Clip仍须按实际生产输入核对。下一外观最小候选为Main_Distor PSR312B的真实render／Material／Mesh，PS7804B后继；资源原作者准备准确范围／支持，余96B不读以猜Follow，外部cue／挂点／生命周期仍unknown。

[Main_Distor PSR312B方案](F:/AnimeStudio/_work/pyrois_main_distor_psr_prepare_20261014/read_plan.md)已核，SHA`1ffc0237ff5be1c317f1396ed4165846fb9a7f0b2b1cf6125c2f760c87b82e0b`；static.freeze SHA`e1e82da494013573c97c6d5c6a6d88b8bd286ab3324d27edae1a60ffa3f50124`／4549文件，[静态证据](F:/AnimeStudio/_work/pyrois_main_distor_psr_prepare_20261014/static.self_test.json)4＋1项／312B夹具A／8.172s／exit0／stderr0。对象class199／type3／start75128／312B与GO`"-5299499679591739929"`匹配；仅拟单次标准A/B全消费、精确PPtr及该Catalog元数据，不读引用或猜默认Mesh形状。Core无独立完整PSR构造器不冒称支持。实际312B仍0／范围窗口未授／fresh父false；当轮使用统筹交回的V3完整after（输出路径仍名Execution_V2），不与writer并读或沿S1／AM旧基线豁免差异。PS7804B、余96B不加入本次范围。

## 验证与权限入口

| 入口 | 可支持的结论 |
| --- | --- |
| [原九包失败](../../../../Saved/Codex/PyriosGhostNative_20261012_R3/Build_failure.json)、[失败保全](../../../../Saved/Codex/PyriosGhostNative_20261012_R3/Failure_preserve.json) | 保留原失败，不改绿或删除 |
| [R5 Recovery](../../../../Saved/Codex/PyriosGhostNative_20261012_R5/Recovery.json)、[正常归还](../../../../Saved/Codex/PyriosGhostNative_20261012_R5/Return_check.json) | 同九资源只读读回；无新保存，不代 Cold／Visual／动作 |
| [R7 离线入口](../../../../Saved/Codex/PyriosGhostNative_20261013_R7_A2/prepare_manifest.py) | 仅旧 A2 适配及离线门槛；后继需核当前真实构建、包差集和完整父保护，不用旧 DLL 冒验新源码 |
| [两缓存读取入口](../../../../Saved/Codex/PyriosSpecialDecal_ReadRequest_20261013/read_cached_components.py)、[已有解析输出](C:/Users/Kaven/.kiro/sessions/0c76a6d5f3ba0b72/sess_d4e92672-ac10-41f2-ab6c-547306fbebe7/tool-outputs/execute_pwsh-56c5d163.txt) | 一次两组件解析，脚本／默认 Mesh／材质闭包未完成；入口不授权重跑 |
| [Material v3 冻结](F:/AnimeStudio/_work/pyrois_special_decal_material_prepare_20261013/Runtime/freeze.v3.json) | 历史软件支持／26项合成记录；实际单次读取以本页5652B输出及Root归还为准，不复启旧入口 |
| [准确权限与旧失败](../../../Coordination/Module_Repair_Parallel_Schedule_History_20261013.md) | 查询具体旧失败及已授范围，历史租约不授权现在开工 |

当前宿主及窗口由统筹按排程协调，不接用户 MCP／LiveCoding。原 Source、DLL、输入、资产及已冻工具保持；真正写集先与完整父保护求交，重叠只等相关保护正常归还。实际入场仍须 fresh 用户 Editor／未保存工作及正常审批；不 kill、不 SaveAll、不 discard，也不换路径／工具绕过 OS 或真实外读拒绝。

当前可独立继续的是已授元数据与离线原因定位。新正文读取按具体来源和范围决定；真实 cue／默认 Mesh／材质来源先交最小缺口，资源存在或消息送达不算还原完成。历史 CLI／MCP 命令及库存仅在[历史页](ZZZ_FX_Handoff_History_20261013.md)保留，当前不据其新开窗口或重建旧包。
