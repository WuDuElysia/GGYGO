# 第05批 Camera 文件子租约

> 本轮 `05-M1-Structure` 四文件已冻结交回，当前无继续写入权限；生产和测试冻结。以下初始临时代理范围保留历史，当前执行者为长期组长 `gpt-6.1-sol / xhigh`，不得创建或唤醒代理。

组长：`01a0e5b5-4490-7881-b890-15d19208ca68`。范围为 B5–B7；禁止 UE/MCP、UBT/构建、Git 写操作、生产资产写入，以及 Movement、HealthSet/Messages、Boss 决策文件。所有路径相对 `F:/ue_project/GGYGO/`，已有未提交修改必须保留。临时实现者固定使用 `gpt-6-luna` / `max`，不得再委派。

## 冻结接口与语义

### B5：CameraOffset 单槽 token

- `FGGYGOCameraOffsetHandle` 定义在 `Camera/GGYGOCameraMode.h`，无效值为 0；由 CameraComponent 单调发放，计数器不因 Reset、Avatar 解绑或 EndPlay 归零。耗尽后拒绝新请求，不回绕复用。
- `UGGYGOCameraComponent::SetCameraOffset(const FGGYGOCameraOffset&) -> FGGYGOCameraOffsetHandle` 每次调用都替换单槽并返回新 token；保持现有 alpha 连续性，不恢复被覆盖的旧 Offset。
- `UGGYGOCameraComponent::ClearCameraOffset(FGGYGOCameraOffsetHandle) -> bool` 只允许当前 token 撤销；过期、无效及重复释放均无副作用。
- `ResetCameraRuntimeState()` 立即清活动模式、Offset 与穿墙恢复状态，但不重置 token 计数器。

### B6：原接收者与模式请求代次

- `UGGYGOHeroComponent::SetAbilityCameraMode(Class, SpecHandle) -> uint64` 返回单调 request generation；0 无效。`ClearAbilityCameraMode(SpecHandle, Generation) -> bool` 必须同时匹配，旧释放不能清后继请求。
- GA 保存申请时的 `TWeakObjectPtr<UGGYGOCameraComponent> + FGGYGOCameraOffsetHandle`，以及 `TWeakObjectPtr<UGGYGOHeroComponent> + SpecHandle + request generation`。显式替换先释放自己仍持有的旧请求；结束清理先于 `Super::EndAbility`，不按当前 Avatar 重新查找接收者。
- Avatar 更换及 `SurvivesDeath` 不自动把旧镜头请求重放到新 Avatar。Hero 在 BeginPlay 仅向 PawnExtension 注册一个 `HandleAbilitySystemUninitialized` 协调入口；该入口清模式覆盖并调用 CameraComponent Reset。07 只能扩展同一入口做输入清理，不新增同 UObject 的第二个解绑订阅。
- PawnExtension 的 C4“本地解绑始终广播”归 06，当前已经实现：匹配本地缓存先清缓存再广播，共享 ASC 清理仍受 Avatar 匹配条件限制。05 不修改 PawnExtension，也不复制第二条解绑通道；第22次新叶只验证正常无输入会话集成，Avatar 失配分支仍未全面证明。

### B7：最终位置唯一碰撞

- `UGGYGOCameraMode` 每帧输出独立 `FGGYGOCameraPenetrationRequest`；`UGGYGOCameraModeStack::EvaluateStack` 同时输出混合后的 View 与按实际可见贡献聚合的请求。
- 聚合只计入贡献严格大于 0 的模式。任一参与模式请求穿墙保护即启用；Pivot 按这些请求的实际贡献归一化加权，ProbeRadius 取最大有限非负值。
- RecoverySpeed 的 0 明确定义为“立即恢复”。存在正值时取最小正值（最慢有效恢复）；所有参与请求均为 0 时聚合结果为 0。非法/非有限参数按安全值处理，不继承数组遍历顺序。
- 最终管线固定为 `Mode Desired -> Stack Blend -> Offset -> CameraComponent ResolvePenetration -> View Output`。ThirdPerson 只产出期望位置和请求，移除自身 sweep 与恢复状态；保留现有蓝图属性名、默认值和 Class Defaults 兼容。
- CameraComponent 使用 `ECC_Camera`，忽略 TargetActor；半径大于零走一次 sphere sweep，半径为零走一次 line trace。遮挡收近立即，解除后按聚合速度恢复；无请求、Reset、空/退化路径重置恢复比例。

## 精确子租约

### `camera_core`（`/root/camera_core`，状态：定点安全复核已冻结，临时代理已结束）

唯一可写：

- `Source/GGYGO/Camera/GGYGOCameraMode.h`
- `Source/GGYGO/Camera/GGYGOCameraMode.cpp`
- `Source/GGYGO/Camera/GGYGOCameraMode_ThirdPerson.h`
- `Source/GGYGO/Camera/GGYGOCameraMode_ThirdPerson.cpp`
- `Source/GGYGO/Camera/GGYGOCameraComponent.h`
- `Source/GGYGO/Camera/GGYGOCameraComponent.cpp`

验收：实现上述 token、请求聚合与最终碰撞；不改 GA、Hero、测试、文档；不运行构建或 UE。

### `camera_seams`（`/root/camera_seams`，状态：已冻结，临时代理已结束）

唯一可写：

- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.h`
- `Source/GGYGO/AbilitySystem/Abilities/GGYGOGameplayAbility.cpp`
- `Source/GGYGO/Character/Components/GGYGOHeroComponent.h`
- `Source/GGYGO/Character/Components/GGYGOHeroComponent.cpp`

只读依赖：冻结后的 Camera 接口、04 Validation、PawnExtension 初始化/解绑委托。验收：保留 04 的组准入、纠正和生命周期修改；实现原接收者清理、generation 与唯一解绑协调入口；不修改 PawnExtension 或 Input 后续清理。

### `camera_tests`（`/root/camera_tests`，状态：已冻结，临时代理已结束）

唯一可写：

- `Source/GGYGO/Camera/Tests/GGYGOCameraLifecycleTestTypes.h`（新增）
- `Source/GGYGO/Camera/Tests/GGYGOCameraLifecycleTest.cpp`（新增）

只读依赖：冻结接口及现有测试夹具。验收：覆盖 Offset token 替换/迟到/重复释放与 Reset 后不复用，Hero generation，GA 原接收者/Avatar 更换不重放，实际贡献聚合的 radius/recovery/zero 语义，以及真实测试 World 中 Offset 后最终碰撞。只登记测试，不声称已编译或通过。

### 组长独占（状态：已冻结，等待统筹统一门禁）

- `AAADocs/Modules/Camera/Module_Repair_05_Subleases.md`
- `AAADocs/Modules/Camera/Module_Repair_05_Validation.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/结构.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/模式栈实现.md`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/GGYGO_结构_相机.canvas`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/GGYGO_流程_相机.canvas`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/GGYGO_流程_相机覆盖恢复.canvas`
- `F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/GGYGO_流程_相机模式求值.canvas`

组长在源码与测试冻结后更新局部笔记、复核全部 diff 和静态门禁。全局 `模块参考.md`、`计划_实施状态.md`、计划蓝图、台账和并行排程由统筹独占，本批只在 Validation 交回更新建议。

## 05-B6-T1 原子登记（2026-09-30，最新有效范围）

状态：统筹已确认只读预检并授权下列四文件；组长已直接完成新增单叶与静态核对，源码及两记录冻结交回，终止本步写入。新叶未编译、未运行。上文临时代理与旧批次范围仅为历史，不授权重新创建代理或扩大写入。

- 唯一目标：新增 `GGYGO.Camera.RealUninitializeAndSurvivingAbilityEnd`，通过真实 GI/World/ComponentManager、Actor/组件 BeginPlay、外置 ASC 宿主 Attach/Detach 与 PawnExtension 广播，验证普通 GA 取消、真实资产标签 SurvivesDeath GA 存活、旧相机请求清空、新 Avatar 不重放以及旧真实 EndAbility 不清新请求。
- 唯一写入者：Camera 长期组长 `01a0e5b5-4490-7881-b890-15d19208ca68`，直接实施，不派发代理。
- 精确文件：`Source/GGYGO/Camera/Tests/GGYGOCameraLifecycleTest.cpp`、`Source/GGYGO/Camera/Tests/GGYGOCameraLifecycleTestTypes.h`、`AAADocs/Modules/Camera/Module_Repair_05_Subleases.md`、`AAADocs/Modules/Camera/Module_Repair_05_Validation.md`。
- 源码基线 SHA256：cpp `29A03E31D810F6AC75EB29D0B01313B8912DFDB12CF36D70B3F9366AADCAFB9B`；h `B4B4F4EF963588E5FA7C987386E9D044F5E10617B359FFADCC30CB4DC9C19794`。
- 只读依赖：冻结 CombatantState Attach/Detach、PawnExtension Initialize/Uninitialize/单订阅广播、Hero 输入保护和镜头仲裁、BaseGA 镜头申请/EndAbility、Camera Reset；已有 Engine/ModularGameplay/GAS 模块依赖足够，Build.cs 冻结。
- 先后顺序：登记/基线 → 独立夹具与单叶 → 静态核对/冻结 → 两记录交回；UHT/构建/自动化由统筹另行统一安排。
- 验收断言：初始化/注册/InitState/镜头委托前置严格；使用构造时 AssetTag 和实际 Give/TryActivate/EndAbility；真实 Detach 后旧模式栈与 Offset 归零、Owner 保持；切换后新能力的模式/Offset 在旧能力结束前后保持。
- 清理责任：各失败出口由夹具 RAII 先结束 GA、解绑、销毁已 BeginPlay Actor，保持 GI/组件管理器有效，随后 GI Shutdown、World/WorldContext 清理；保存并恢复 GI 涉及的三项全局 Net 加密委托。
- 非目标：有效输入会话/旧广播后继/IMC 重入、死亡 GE/Health、完整 B6、B5 无请求矩阵、B7 矩阵、PIE/网络/资产；旧三个测试、旧 helper/类型正文保持，只允许新增 include、protected Offset 只读观察及预检内独立夹具/helper/单叶。
- 停止点：前置无法成立或需新增生产接口/扩大文件范围即停止交回；严格失败保持。源码冻结后立即交回，不自行 UE/MCP、构建、Git 或图文/资产写入。

### 05-B6-T1 冻结交回

- cpp 冻结 SHA256：`D8A48FEE28B9B32A1E2F8CDFFFE3759CCCB5315A28507EABC7679AFB835B0E36`；h：`5213508433C1CFEDCA4E56B889C8BACD50A8E477A1B7C0505E749E26CDCE831E`。
- 新增位置：cpp include、128–147 独立构造、735–991 独立夹具/helper/单叶（869 注册）；h 两 include、84–87 protected Offset 只读观察、146–186 三个独立类型。旧 cpp 707 行/h 138 行的内容经移除明确新增片段后精确恢复登记基线 SHA256。
- 静态结果：新注册名唯一、总计四叶；四文件尾随空白 0、保留 LF/无 BOM；cpp/h 去除注释与字面量后的括号栈无错误/无剩余；generated include 仍是 h 最后 include。15 个 Camera/BaseGA/Hero/PawnExtension/CombatantState/Build.cs 生产依赖 SHA256 前后相同。
- RAII 与 Net 三委托保存/恢复已源码核对；所有前置与业务断言仍须统筹实际门禁证明，未用编译或历史三叶成功代替新增叶结果。
- 本步实际仅写上述四文件；不修改生产、旧叶/helper 正文、其它测试、图文或资产，不调用 UE/MCP、构建、Git，不创建/唤醒代理。后续修改须由统筹新授权。

## 05-M1-Structure 原子登记（2026-09-30）

状态：Camera 长期组长已直接完成结构 MD/Canvas 同步及静态验收，四文件冻结交回，终止本步写入。生产/测试/其它图文仍冻结；未派发代理。

- 唯一目标：同步 Camera 当前结构、B5–B7 资源与最终碰撞接口、已实现 C4/07 唯一 Hero 协调入口及第22次正常无输入解绑的有限证明；修正结构文档/图中的旧实施状态，保留未验证边界。
- 精确四文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/结构.md`、`Camera/GGYGO_结构_相机.canvas`、`AAADocs/Modules/Camera/Module_Repair_05_Subleases.md`、`AAADocs/Modules/Camera/Module_Repair_05_Validation.md`。唯一写入者为 Camera 长期组长 `01a0e5b5-4490-7881-b890-15d19208ca68`。
- 基线 SHA256：结构 MD `E645B56B0F11DB57DB8E9C7A0E1F86563C37C3B703F6EEBD80FBC3AC539856DD`；结构 Canvas `301A7805FA1657D913D317D87D23BA43B0A28D858A62D9ACF384344155AAAAF2`；本记录 `46E09CAF0E5F937DC1E2D771A0BBCE66088906DD1315AFA784A2FF892279F36F`；Validation `093145D5884EF6E6F255DF80DEF6737B44FDD0DFD96E9DB16299C3FC93BF033A`。
- 只读依赖：冻结 Camera/BaseGA/Hero/PawnExtension/CombatantState 与测试源码、Build22/Gate22 原始报告、计划蓝图/模块参考和相邻模块文档。17 个源码/测试/Build.cs 文件与三流程 Canvas/模式栈实现 MD 共21文件保护哈希已捕获。
- 先后顺序：登记预检/基线 → 配套结构 MD → 保留14节点/14边及ID/端点/几何/颜色的结构图文本和标签同步 → JSON/引用/布局/容量/链接/读回/保护哈希检查 → 两记录冻结交回。
- 验收断言：GA 原接收者/Spec+generation/token，Hero 单一协调器及输入 guard/EndPlay 区别，C4 本地广播与共享 ASC Avatar 条件分开，Stack View+Request 聚合及 Component 有效请求时最终一次查询都与源码一致；第22次四 Camera 叶 Success 只证明各自范围，不关闭完整 B6。
- 非目标：生产/测试/资产、三流程图/模式栈实现 MD、其它模块及全局入口；后继输入 guard/IMC 重入、Avatar 失配 C4 分支、死亡 GE、完整 B6、生产贴墙/资产/PIE/联机不得写成全面证明。既有资产与2026-09-28 PIE记录保留历史属性。
- 停止点：若需要改变已冻结接口、扩大图文范围或新增独立图，则停止交回准确建议；本步完成 JSON/链接/矩形/读回与保护哈希后四文件冻结，禁止 UE/MCP、构建、Git 或代理。

### 05-M1-Structure 冻结交回

- 结构 MD SHA256：`0F589811A9AD6846490D29E14C36BCDEB1C4A57292186A48BF72EAF48D6214AD`；结构 Canvas：`389E448DC1790D6F14AFEBEE186E4A7F08D653B28CA62B6F429E81A78ADA282D`。
- 实际只更新结构 MD、结构 Canvas 和两记录；结构图更新11节点正文/6边标签，新增/删除节点和边均0。原14节点/14边的ID、类型、顺序、坐标/宽高、颜色、边端点/方向等非正文/非标签字段与基线逐项相同。
- JSON/ID/端点/非空标签、24处链接/10个实际文件目标及本页3个节标题锚点、矩形不重叠、保存读回均通过。静态容量估算无溢出，含标题字体估算最小余量10px；这是静态估算，不冒称 Obsidian UI 验收。
- 21个保护文件（17源码/测试/Build.cs，三流程Canvas、模式栈实现MD）前后哈希一致。第22次55/55与四Camera叶的0错误/警告已实读补充；本步未运行新的构建/自动化。
- 未开放的覆盖恢复图 `unbind` 与模式栈实现“每帧至多/非法dt不推进alpha”说明的准确后续建议见 Validation；本步不越界修改。后续仍需统筹新授权。

## 05-B5-StrictInput-I 原子登记（2026-09-30）

状态：统筹已接受零写入预检并授权下列四文件；Camera 长期组长已直接完成生产短修及静态复核，四文件冻结交回，终止本步写入。未创建或唤醒代理，未开放 T/D1/D2。

- 唯一目标：SetCameraOffset 在发号和任何成员写入前拒绝非法请求并给出可定位 Error；合法请求保持既有单槽替换和 alpha 连续语义。
- 唯一写入者：Camera 长期组长 `01a0e5b5-4490-7881-b890-15d19208ca68`。
- 精确四文件：`F:/ue_project/GGYGO/Source/GGYGO/Camera/GGYGOCameraComponent.h`、`F:/ue_project/GGYGO/Source/GGYGO/Camera/GGYGOCameraComponent.cpp`、`F:/ue_project/GGYGO/AAADocs/Modules/Camera/Module_Repair_05_Subleases.md`、`F:/ue_project/GGYGO/AAADocs/Modules/Camera/Module_Repair_05_Validation.md`。
- 入口 SHA256：h `03766BA6C8A2BE637C5D333E38CEC8EC48B1209B83C88C572171362B9B1F2295`；cpp `03D053CEE7FE5F400661689041912A0EE854617DD3D04760AD06C3D21E6B7928`；本记录 `6B9BA22D6D9FC5C69A41E2E6D68EEABE7355E80FFDB1B7810645ECC33AD95489`；Validation `4B18E0594B75D4FCD05D3C09BC01DDCF4CB9778EF6AAD8E5B34DEA097750540E`。
- 冻结契约：依次检查 LocationOffset.X/Y/Z、FieldOfViewDelta、BlendInTime、BlendOutTime；数值须有限，时间还须非负。非法请求返回 Invalid，保持入口 Offset、active、alpha、旧 token、发号计数器；合法零时间/全零 Offset 正常接受。合法输入的 token 耗尽另行拒绝，不作为配置失败。
- 诊断契约：cpp 本地静态 Camera category；每个被拒绝的显式申请只执行一条 Error，含 Component/Owner 路径、首个非法字段及 non-finite/negative 原因；耗尽使用 HandleSequence/token-exhausted。无 Tick 日志、缓存、重试、catch 或替代值。
- 只读依赖：Offset/Handle 定义、BaseGA 调用前 Clear 与保存有效 handle 的消费者、既有四 Camera 叶/types、Hero/PawnExtension/CombatantState/Build.cs、Camera 局部 MD/Canvas；共21保护文件已捕获哈希。GA 主动 Clear 发生在 Setter 前，本步骤不承诺恢复该动作。
- 顺序：登记/基线 → h 契约与 cpp 前置拒绝 → 完整实际 diff/合法路径及保护字节静态核对 → 两记录补充证据 → 四 hash 冻结交回；不自动进入测试或文档步骤。
- 验收断言：所有非法输入和耗尽出口都早于发号/成员写；合法单槽赋值、有效 token 和 alpha 保持行为不变；方法外代码及其它生产/测试/图文逐字节保持。
- 非目标：GA 替换事务、测试及 types、其它生产/模块/资产/笔记；不修改碰撞/FOV 投影安全保护、空 mode 正常配置，不运行 UE/UBT/构建/Git。第25次旧测试成功不证明本短修。
- 停止点：若需跨模块修改、扩大范围或改变既有结果接口，立即停止交回；本步静态核对完成即冻结四文件。旧非法归零断言由后续独立 T 步骤处理。

### 05-B5-StrictInput-I 冻结交回

- 实际只更新 h 的 SetCameraOffset 契约注释、cpp 的 Logging/LogMacros include/本地静态 LogGGYGOCamera 与 SetCameraOffset，以及两记录的本节追加。
- cpp:78–138 为新入口，XYZ/FOV/时间校验早于128行发号和130–132行成员提交；非法请求与合法输入耗尽分别单条 Error/Invalid 返回，均没有成员写入。合法提交保持原代码，alpha 不重置。
- 精确保持：用基线方法恢复新方法并移除新增 include/category 后，cpp 逐字节重建入口基线；h 恢复该契约注释后也逐字节重建入口基线。移除旧非法字段归零段后的合法提交尾部与当前尾部完全相同。
- 21保护文件哈希与入口一致，包含其余Camera生产/测试、GA/Hero/PawnExtension/CombatantState/Build.cs、Camera六份MD/Canvas。两记录新增本节之前的原字节前缀分别精确恢复登记hash，没有改写历史。
- 静态结果：cpp/h 括号栈无错误/无剩余；四文件 LF/无BOM/尾随空白0；本地诊断只在入口两个互斥拒绝分支，无方法外/逐帧日志、缓存、重试或结果框架。诊断使用首个字段及原因；Owner可空，路径安全输出。
- 生产冻结 SHA256：h `E490E16D6DAB94161E5904C08BBC0B451D674E6903AC39C75FD56EE046370D04`；cpp `7C3551D8AB4F7AAF990FDB142BE89E133A09CF7B0F043738D8B2FB877177CA15`。两记录最终hash随交回提供。
- 未编译、未运行；旧测试保留非法归零/可释放断言，下一独立T仍必需。第25次59/59是修改前证据。本步不运行UE/MCP/UBT/构建/Git，不改资产或笔记，四文件停止写入。

## 05-B5-StrictInput-T 原子登记（2026-09-30）

状态：统筹接受生产I的实际diff及逆向hash并保持生产冻结；组长已直接完成下列三文件内专项及静态核对，三文件冻结交回，终止本步写入。未创建或唤醒代理，未开放D1/D2或运行门禁。

- 唯一结果：替换OffsetOwnership旧非法归零区段，验证严格拒绝、旧状态/所有权/发号保持及合法零值；其它测试全文保持。
- 精确三文件：`F:/ue_project/GGYGO/Source/GGYGO/Camera/Tests/GGYGOCameraLifecycleTest.cpp`、`F:/ue_project/GGYGO/AAADocs/Modules/Camera/Module_Repair_05_Subleases.md`、`F:/ue_project/GGYGO/AAADocs/Modules/Camera/Module_Repair_05_Validation.md`。唯一写入者为Camera长期组长 `01a0e5b5-4490-7881-b890-15d19208ca68`。
- 入口SHA256：测试cpp `D8A48FEE28B9B32A1E2F8CDFFFE3759CCCB5315A28507EABC7679AFB835B0E36`；本记录 `1E8C5CE4833B683B494254E1E815FB5D7BA6D520137B76E1D67C0A8973286ED2`；Validation `412302B068A1683E1B9E82C2A6988907C83E08922E356BEFA77F6E9415F6423F`。
- 源码写入边界：只替换入口cpp旧343–379行，从InvalidOffset声明到该叶return前；原return/闭括号及其前229–342行、helper/include/另三叶全文保持。局部数组/lambda只在本区段；types及所有生产只读。
- 只读依赖：冻结SetCameraOffset前置校验/精确日志格式、Offset/Handle和protected只读访问器、已有World/Pawn装配及View helper、native AddExpectedMessagePlain匹配机制。22个受保护生产/types/局部图文文件已捕获哈希。
- 矩阵：XYZ各NaN/±Inf、FOV各NaN/±Inf、BlendIn/Out各NaN/±Inf/负值，共20个独立字段案例；保留原两组混合非法值，共22案例，分别在活动和已Clear回落状态覆盖。每个案例/状态使用独立Pawn/Camera路径，44次拒绝各以Plain/Error/Exact/次数1匹配，避免重复同文本首次匹配积累问题。
- 验收断言：拒绝Invalid、全部Offset/active/alpha保持；活动旧token可精确释放一次，已释放token不复活；下一合法token=上一合法+1；合法零时间/全零Offset接受、视图有限。原非法DeltaTime、所有权/Reset和旧三叶断言不放松。耗尽仅静态，不注入私有状态。
- 顺序：登记/基线 → 局部区段实现 → 完整实际diff、全文逆向重建入口hash、22保护hash及诊断/矩阵静态核对 → 两记录证据 → 三hash冻结交回。
- 非目标与停止点：不修改生产/types/其它测试/资产/笔记，不新建全局测试框架；不执行UE/MCP/UBT/构建/Git。前置或范围无法成立立即交回；静态完成即冻结，动态门禁由统筹安排，不自动进入D1/D2。

### 05-B5-StrictInput-T 冻结交回

- 实际仅替换测试cpp旧343–379行；新局部区段343–567行，BEGIN/END标记343/566，原return及之后全文保持。注册仍为四叶，没有新增include/helper/类型/全局框架。
- 20独立非法字段与原2混合案例配置保持，在两状态循环中共有44次预期拒绝；每次独立Pawn/Camera，合法旧请求进入alpha0.5，回落状态先Clear并推进至0.375。全部Offset字段及active/alpha在拒绝和无效释放前后检查，浮点保持检查显式容差0，Location逐分量精确比较。
- 每次用AddExpectedMessagePlain(Error/Exact/1)登记完整对象路径/字段/原因，矩阵字段与冻结生产日志一致，无regex/Contains/无限或负次数。活动旧token释放成功一次、回落旧token不复活、原回落继续，以及下一合法token+1、零时间立即进入/退出、全零Offset接受/精确释放都有断言。混合原案例继续检查正负非有限dt下View有限且保持。
- 全文逆向：以入口旧区段替换新标记区段，在内存UTF8编码后SHA256精确恢复 `D8A48FEE28B9B32A1E2F8CDFFFE3759CCCB5315A28507EABC7679AFB835B0E36`；由此保护该叶此前所有权/Reset/非法dt断言、include/helper及其它三叶全文。22保护文件前后hash一致，types仍 `5213508433C1CFEDCA4E56B889C8BACD50A8E477A1B7C0505E749E26CDCE831E`。
- 测试cpp冻结SHA256 `542646F1D6E3B621C221B3E43D65FA1CC9379AE756686F0492B613F9269323F6`；两记录最终hash随交回。三文件LF/无BOM/尾随空白0；完整实际diff/读回及括号栈核对通过，两记录原字节前缀保持入口hash。
- 本I/T未编译、未运行，44是配置的预期拒绝数量，不是运行通过数量。I上节旧非法断言未修改是I交回时历史，现仅由本T区段更新；第25次仍为修改前旧版本。耗尽未动态覆盖，无私有注入；生产/图文/资产冻结，三文件停止写入，不自动D1/D2。

## 05-B5-StrictInput-D1 原子登记（2026-09-30）

状态：统筹交回第26次实际构建/回归并独立授权下列三文件；Camera长期组长已直接完成实现说明与两记录同步及静态验收，三文件冻结交回，终止本步写入。未创建或唤醒代理，生产/tests/types及其它笔记继续冻结，未开放D2。

- 唯一结果：模式栈实现说明同步严格Offset拒绝及第26次有限证明，并准确区分SafeDt/零BlendTime、每次视图拉取查询与Hero guard/EndPlay边界。
- 精确三文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/模式栈实现.md`、`F:/ue_project/GGYGO/AAADocs/Modules/Camera/Module_Repair_05_Subleases.md`、`F:/ue_project/GGYGO/AAADocs/Modules/Camera/Module_Repair_05_Validation.md`。唯一写入者Camera长期组长 `01a0e5b5-4490-7881-b890-15d19208ca68`。
- 入口SHA256：模式栈MD `2AD5D5B75EC65FE57EF3B668C80AA67EDDB30BC454E85F1F01119B09D11E4C07`；本记录 `EC2C4A339544E1802256F617C9ADABF7530B1E336CDF3BB5276F59ACAF107DF6`；Validation `00C1E76F3C70D61BE7F2CAFD2E11EA5FDC7408187EFDAB08FC14C7706AA90978`。
- 只读依赖：计划蓝图/模块参考Camera节、AbilitySystem计划、Camera结构与四Canvas、相邻AbilitySystem/Input/Combatants结构、冻结Camera/GA/Hero源码与T、Build26/Gate26报告和实际日志。遵循项目Obsidian技能；22生产/测试/types/其它Camera笔记保护hash已捕获。
- 验收事实：XYZ/FOV有限，两时间有限非负，首字段顺序和单条Error/Invalid/入口状态保持与源码一致；合法零值、耗尽仅静态、GA调用前Clear不恢复。第26次OffsetOwnership/44诊断只证明该矩阵，不能关闭完整Camera或其它非法配置路径。
- 顺序：登记/基线 → 保留有效Stack/碰撞正文并替换Offset旧归零文、补有限验证与待审查项 → 实际diff/链接锚点/事实/读回及保护字节核对 → 两记录证据 → 三hash冻结交回。
- 非目标与停止点：不改结构.md、任何Canvas、其它模块或全局入口、生产/tests/types/资产，不运行UE/MCP/构建/Git/代理；其它自动替代只列待审查缺口。完成静态核对即冻结，不自动D2。

### 05-B5-StrictInput-D1 冻结交回

- 模式栈MD已替换非法Offset归零/仍发token说明，补首字段/原因/Invalid/入口原子保持、合法零值、耗尽静态及GA调用前Clear边界；正时间SafeDt0不推进与合法零时间立即到目标alpha分开，每帧一次查询改为每次视图拉取最多一种查询，末尾补Hero guard/正常清理/EndPlay及结构页锚点。
- 第26次新DLL完整构建与OffsetOwnership实际Success/44拒绝已写入，四Camera叶保持各自有限证明；I/T旧“未编译/未运行”保留历史并由新证据补充。其它Stack/碰撞请求归零及Mode非法混合配置替代只列待审查，没有写成已整改或整个Camera无兜底。
- 实际MD diff已完整核对；实例池/Push规则、可见贡献公式、合法请求聚合规则、单槽撤销与模式→栈→Offset→碰撞→输出顺序保留。6处wikilink对应4个实际目标，2结构页节锚点有效，保存读回/事实核对通过；没有修改任何Canvas，节点/边增删0。
- 22个生产/tests/types/结构MD/四Canvas保护hash前后一致；两记录D1之前原字节前缀保持入口hash。三文件LF/无BOM/尾随空白0。模式栈MD冻结SHA256 `F12EB3BFAF92B483305DF01E5DD4E786BF3CE19CBC1F86AABE89B837C93C21EF`；两记录最终hash随交回。
- 本步只同步文档，没有运行新构建/自动化/UE/MCP/Git或代理，不改资产或全局入口；结构页/Canvas本轮同步仍待D2及后续独立范围。三文件停止写入，不自动继续。

## 05-B5-StrictInput-D2：严格 Offset 结构图文同步（A7）

- 状态：统筹接受零写入预检并授权精确四文件，Camera组长直接实施；本节只登记D2，不恢复D1或生产/测试写入权限。
- 唯一结果：将已冻结严格Offset接口与Gate26有限证明同步到结构Markdown和结构Canvas，保持静态类/接口关系，不复制模式栈详细算法或展开运行流程。
- 精确写入范围：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/结构.md`、同目录`GGYGO_结构_相机.canvas`、`AAADocs/Modules/Camera/Module_Repair_05_Subleases.md`、`AAADocs/Modules/Camera/Module_Repair_05_Validation.md`。两记录只追加D2，原有证据字节不改。
- 依赖顺序与所有权：I接口冻结 → T严格专项冻结 → Gate26新DLL实际门禁 → D1实现说明冻结 → D2结构配套同步 → 静态核对后四文件冻结。CameraComponent唯一拥有Offset单槽/token/alpha与最终碰撞恢复状态，GA只持有原接收者凭证，Hero/Stack原有职责与接口不变；全局入口由统筹独占。
- 图内精确范围：仅`ga`、`component`、`contract`三节点正文；14节点/14边、全部ID/边标签/端点/顺序/坐标/尺寸/颜色保持。正文保留关键接口的输入、校验/返回、调用方原子性边界与有限验证；详细实现使用既有模式栈MD锚点链接。
- MD精确范围：每次拉取至多一种查询、Offset字段/句柄契约、GA先Clear再Set、当前验证节和接口表；保留第22次历史，补第26次44拒绝/合法零值与开放边界，修正D1已做但仍写待同步的状态。第27次只作既有四Camera叶保持记录，不扩大证明。
- 入口SHA256：结构MD `0F589811A9AD6846490D29E14C36BCDEB1C4A57292186A48BF72EAF48D6214AD`；结构Canvas `389E448DC1790D6F14AFEBEE186E4A7F08D653B28CA62B6F429E81A78ADA282D`；本记录 `E80EB4051B1E143A09E3F4BC80CFB802EC99D9C9CE417BB1238C57A39FCB8D7B`（26972字节）；验证记录 `E118B7F0A8907554EDF66432527577976897E4F1605AAA7556E2531A1222F464`（36832字节）。
- 只读保护：22个文件，包括Camera生产/tests/types及`.gitkeep`、GA/Hero/PawnExtension/CombatantState h/cpp、Build.cs、D1模式栈MD和三流程Canvas；D1 MD冻结hash `F12EB3BFAF92B483305DF01E5DD4E786BF3CE19CBC1F86AABE89B837C93C21EF`。计划蓝图/模块参考及相邻模块结构只读。
- 验收断言：Set先完整校验再发号，首字段Error/Invalid与入口状态保持；合法零时间/全零Offset/有限负FOV接受，GA已Clear的资源不恢复；Gate26为20+2案例×活动/回落两状态的有限44拒绝，耗尽仅静态，完整B5/B6/B7、Input/IMC/Avatar失配/死亡GE/资产网络及其它自动替代保持开放。
- 检查与停止点：完整实际diff、保存读回、JSON/ID/端点/标签/链接/锚点、矩形与三正文静态容量、22保护hash及两记录原字节前缀核对后四文件冻结交回。静态容量不是Obsidian屏幕验收；不运行源码/测试/UE/MCP/构建/Git/资产/代理操作，不扩大到其它图文或自动下一步。

### 05-B5-StrictInput-D2 静态验收与冻结交回

- 唯一结果完成：结构MD已同步严格Offset输入/发号前校验/Error/Invalid/入口保持、合法零与有限负FOV、GA先Clear边界；保留Gate22历史、补Gate26核心44拒绝及Gate27保持，D1不再写成待同步。其它自动替代以现有模式栈MD链接列开放边界。
- Canvas只改ga/component/contract三正文，0节点/边增删；14节点/14边、全部ID/端点/标签/顺序/坐标/尺寸/颜色及所有非正文属性保持。将三正文在内存中恢复后完整Canvas原文精确等于入口版本。
- 实际完整diff及保存读回核对通过；结构MD88行、Canvas258行。配套26处wikilink解析到10个实际文件，5处锚点引用有效；JSON/全28个ID唯一/端点/标签通过、0矩形重叠。三正文按现有尺寸静态估计余量ga23px/component29px/contract98px，没有重排；不是屏幕验收。
- 22个保护文件保持入口hash，D1 MD仍为F12EB3BF…；两记录D2前26972/36832字节前缀精确保持E80EB405…/E118B7F0…，历史未改写。四文件LF/无BOM/尾随空白0。
- 结构MD冻结SHA256 `A19BA8197EACC856611347424E63E4433F4970E776232BEBDFA5BF20FAAED28E`；结构Canvas冻结SHA256 `062EA06505B68D54DB5EF378118EE6D6000B3B7AF253306A3DC8F6DCDFF1D0DC`；两记录最终hash随交回。
- 架构核对：只同步已存在的接口、唯一状态/执行者与有限验证，没有新增依赖/类/权威状态/执行链/调度器/清理职责。完整B5/B6/B7、Input/IMC/Avatar失配/死亡GE/资产网络、耗尽动态及其它非法配置拒绝仍未闭环；三流程Canvas后续同步保持独立范围。
- 状态：四文件冻结交回，终止本步写入；本D2未运行UE/MCP/构建/自动化/Git/资产/代理操作，未修改其它图文或生产/tests/types，不自动下一步。

## D3-R：本地解绑、Hero guard与条件清理流程同步（A10）

- 状态：统筹接受D3零写入拆分预检，仅授权A10/D3-R三文件；Camera组长本人先登记本租约，再改图并验收冻结，随后追加两记录的实际结果。
- 唯一结果：将既有PawnExtension本地解绑通知→Hero唯一协调入口的条件清理契约画清楚，拆出guard命中返回、ReleaseInput/条件Reset及EndPlay独立触发；不把Reset画成同步默认模式恢复，不把所有实现分支冒称动态已验。
- 精确文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/GGYGO_流程_相机覆盖恢复.canvas`、`AAADocs/Modules/Camera/Module_Repair_05_Subleases.md`、`AAADocs/Modules/Camera/Module_Repair_05_Validation.md`。两记录只追加D3-R，保留原字节历史；不授权D3-E/M/Nav。
- 归属与依赖：PawnExtension独占本地ASC缓存/ExpectedASC校验与本地广播；共享ASC清理受Pawn/Avatar身份条件限制；Hero独占唯一guard/输入与模式清理协调，CameraComponent独占运行状态Reset，GA保存原接收者凭证。相关源码/I/T/D1/D2已冻结，本步只说明接口与事件，不新增跨模块实现或第二清理入口。
- 原图保护：保留原9节点的全部ID/位置/尺寸/颜色/非正文属性，仅nav/unbind正文修改；原10条边ID保留，e1–e9全部属性不变。e10保留目标restore，来源改release-reset、目标侧改bottom，并限定正常解绑且模式委托仍绑定时下一次拉取重选。
- 新增精确范围：hero-guard(470,1070,420×290,颜色3)、release-reset(470,1430,420×245,颜色4)、endplay(0,1430,420×245,颜色3)、evidence(0,1735,890×200,颜色6)；e11本地匹配广播→Hero、e12 guard未命中/EndPlay→清理、e13 EndPlay设置ending并解绑模式委托→同一Handler。拟稿13节点/13边，无其它节点/边增删。
- 入口SHA256：流程Canvas `E5FB34F80C9BB7E69CFD31B41CCD6162F718A34ADD7D54585F9DB8CF37204BD1`（4699字节）；本记录 `8D26C5651B0D7420127D4EFADCAD5A35C9EE9CB45F80C539F97BC4F0D9A78D11`（31875字节）；验证记录 `D2BC8C38FBE88A7D496F90A4A3F2F0AF18A12E2016FB1C7C729D73A61F11FE3E`（42645字节）。
- 只读保护：其余23个基线文件，包括D1模式栈MD、D2结构MD/结构图、主流程/模式求值图、Camera生产/tests/types及.gitkeep、GA/Hero/PawnExtension/CombatantState h/cpp和Build.cs；全局入口、其它模块及资产无写入权限。
- 验收断言：缓存空/ExpectedASC失配不广播，匹配先清本地缓存；共享ASC仅Pawn/Avatar身份匹配时清理，失配仍本地广播；Hero guard命中同时跳过输入与Camera清理，否则ReleaseInput→清覆盖→有Camera时Reset；EndPlay绕过guard且不沿e10恢复默认，正常解绑只在委托仍绑定的下次视图拉取重选。
- 证据与停止点：Gate22/26/27及第29次四Camera叶保持只证明各自有限场景，解绑仍仅正常无输入，guard/IMC重入/Avatar失配/死亡GE/完整B6开放。按Canvas技能检查完整实际diff/readback/保留原文、JSON/ID/端点/链接/矩形/容量、23保护hash和两记录历史前缀，图冻结后追加记录并交三hash，终止写入。不运行UE/MCP/构建/自动化/Git/资产/代理，不自动其它图文。

### D3-R 静态结果与冻结交回

- 图已按A10冻结：13节点/13边，只改原nav/unbind正文和e10指定字段，新增hero-guard/release-reset/endplay/evidence及e11–e13。原9节点所有非正文元数据、原10边ID、e1–e9完整对象和7个非目标原节点正文保持；无删除/重排。
- 条件链与冻结源码一致：本地缓存/ExpectedASC匹配才清缓存并通知；共享ASC副作用另受Pawn/Avatar身份条件限制；Hero guard命中同时保留输入/镜头，正常清理先ReleaseInput再清覆盖、有Camera时Reset；EndPlay独立进入同一Handler并绕过guard，清理后不走默认恢复。e10只表示正常解绑且委托仍绑定的下一次拉取重选。
- 完整实际图diff与保存读回已核对；去掉4新节点/3新边、恢复nav/unbind/e10后，序列化原文逐字节精确等于入口Canvas（E5FB34F8…），其余原文保持。JSON/全26个ID唯一/端点/非空标签通过，矩形重叠0。
- 图内5处wikilink对应3个实际目标；3次锚点引用对应2个不同标题，全部有效。6个修改/新增正文静态容量余量nav46/unbind76/hero-guard100/release-reset55/endplay103/evidence58px；没有调整原节点尺寸，静态检查不是Obsidian屏幕验收。
- 第29次报告已实读：63 Success、Camera四叶各Success/errors=0/warnings=0/entries=[]，真实解绑叶0.01511560007929802秒，Offset叶0.02135850116610527秒；运行日志44条唯一拒绝。这是保持证据，guard/IMC同步重入、Avatar失配/死亡GE与完整B6仍开放，不据成功扩大证明。
- 23个只读保护hash保持，包括主/求值图、D1/D2图文、Camera源码/tests/types、GA/Hero/PawnExtension/CombatantState与Build.cs。两记录A10前31875/42645字节历史前缀保持入口hash，未改写D1/D2及旧门禁证据。
- Canvas冻结SHA256 `2CE7A4CF2B482060819422DBC7B275581CB87A375C0E38EEC64CCFBDA250307F`，240行/6966字节；两记录最终hash随交回。三文件LF/无BOM/尾随空白0，原有状态/依赖/执行者/清理责任未变，没有新增架构或业务替代。
- 状态：D3-R三文件冻结交回，终止本步写入；未运行UE/MCP/构建/自动化/Git/资产/代理，未写其它MD/Canvas/source/tests；D3-E/M/Nav与MD状态收尾仍须独立租约，不自动继续。

### D3-R 交回终检：并行A9只读依赖变化

- 上节23保护hash保持是图冻结时已完成的实际检查。图冻结后、两记录交回终检时发现CombatantState h/cpp变化；已只读核对排程A9/06-L1-I及06子租约，该两文件由Combatants组长在独立精确范围实现宿主生命周期绑定准入，Camera没有写入。
- 终检其余21个文件仍保持A10入口hash，包括PawnExtension/Hero/GA与全部Camera源码/tests、D1/D2图文及主/求值图。CombatantState观测hash分别为h `A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF`、cpp `6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84`；这是并行写入的只读快照，不冒称对方已冻结。
- 当前ClearLocalAvatarBinding仍调用PawnExtension::UninitializeAbilitySystem(本宿主ASC)，ExpectedASC/本地通知/共享ASC条件接口保持，Hero与PawnExtension文件未变，本图契约不受私有准入实现影响。Gate29是A9改动前的历史门禁，不证明新A9准入行为；Camera不构建或验证对方改动。
- 本图hash保持2CE7A4CF…，两记录只追加本终检说明，原历史字节保持。D3-R三个自有文件冻结交回；并行A9变化单列，不把终检描述成全部23文件均未变，不扩展任何写入租约。

## D3-E：单次相机求值与已接受Offset消费流程同步（A11）

- 状态：统筹接受D3-R静态冻结，正式授权A11三文件；2026-10-01 Camera组长本人先登记基线与五块文字范围，随后用Canvas技能/apply_patch改图，验收冻结后追加两记录。
- 唯一结果：说明单次GetCameraView→Stack→Mode求值、已接受Offset消费与最终碰撞的真实接口/参数、合法零语义及Gate29有限证据；不增加申请接口、替代业务、调度器或结构职责。
- 精确写入文件：`F:/Obsidian/Doc/lyra学习笔记/GGYGO架构规划/Camera/GGYGO_流程_相机模式求值.canvas`、`AAADocs/Modules/Camera/Module_Repair_05_Subleases.md`、`AAADocs/Modules/Camera/Module_Repair_05_Validation.md`。两记录只追加D3-E，原文历史保持。
- 精确五块：nav只补数据边/求值先后、有限Gate29及现有MD边界链接；pull说明每次拉取SafeDt/Push与空栈返回、无帧号去重；update说明UpdateCameraMode清请求→UpdateView→权重与合法零时间；offset说明UpdateCameraOffsetAlpha→ApplyCameraOffset、消费既有单槽而非此处Set、Error/Invalid入口保持及GA先Clear/合法时间；collision说明最终有效路径至多一种查询、合法Radius/Recovery零值与跳过查询的安全分支。
- 图保护：13节点/12边、全部ID/顺序/布局/尺寸/颜色/类型/非正文属性和12边完整内容保持，仅nav/pull/update/offset/collision五个text修改。pool/contribution/bottom/prune/blend/write/fallback/aggregate八正文保持，不新增或删除节点/边。
- 依赖与归属：I/T、D1/D2与D3-R冻结；Component持有单槽token/alpha与唯一最终碰撞恢复比例，Stack拥有实例池/活动栈及View/Request贡献混合，Mode输出期望View/请求，Hero仲裁类，GA保存原接收者凭证；不扩展任何跨模块接口。
- 入口SHA256：模式求值Canvas `B7AA83BE79BE435BE2826CF9A4EF619157979AB9D0956DE0C9682E8FB3C823EB`（6964字节）；本记录 `A6B411ED8E7EF51EA71F9667CEF8E26E17D47619678DE28D6402C0EA2146CCB4`（38734字节）；验证记录 `EAF14D8EC68ED4EDB8D6884E883273C7814410A4E366676C25BAE2C8B53BA2CF`（49884字节）。
- 只读范围：另外23个基线文件，包括主流程/覆盖恢复/D1/D2/结构图文、Camera生产/tests/types及.gitkeep、GA/Hero/PawnExtension/CombatantState h/cpp与Build.cs；本次重新采用已冻结A9当前hash，不把前步授权并行变化算成Camera写入。Movement两旧测试/10记录不属于本基线或写入范围，全局入口/资产冻结。
- 验收断言：求值先完整输出View/Request再消费Offset；非法Set Error/Invalid不改入口，GA调用前Clear不恢复；合法alpha正时间SafeDt0不推进、合法零时间立即完成；有贡献启用请求的合法Radius0=line、Recovery0=立即恢复；有效World/Target/非退化路径每次拉取最多一种ECC_Camera查询，同帧重复拉取没有去重承诺。其它非法Mode/请求参数自动替代只列待审查。
- 停止点：实际完整diff/保存读回/五正文逆向还原、JSON/ID/端点/链接/锚点/矩形/容量静态、23保护hash与两记录旧字节前缀核对后交三hash冻结停止；不是屏幕或动态全验。不运行UE/MCP/构建/自动化/Git/资产/代理，不写其它图文/source/tests，不自动D3-M/Nav。

### D3-E 静态结果与冻结交回

- 唯一结果完成：只修改nav/pull/update/offset/collision五正文；13节点/12边、所有非正文元数据/ID/顺序/布局/尺寸/颜色及12条边完整内容保持，八个非目标正文保持，无节点/边增删。
- 与实际代码核对：EvaluateStack先UpdateStack→BlendStack→BlendPenetrationRequests完整输出View/Request，再UpdateCameraOffsetAlpha→ApplyCameraOffset→ResolveCameraPenetration；入栈/混合/聚合的既有贡献规则保留。合法零混合时间与合法零Offset时间可在SafeDt0时立即完成；合法alpha/正时间SafeDt0不推进。Radius0=line、Recovery0=立即恢复只按明确合法配置解释，其它非法参数自动替代仍待审查。
- 完整实际diff和保存读回通过，五正文在内存替回后完整Canvas原文精确等于入口B7AA83BE…；五行沿用原6空格缩进，格式没有隐藏变化。JSON/25个ID唯一/端点/标签通过，矩形重叠0；5处链接/3个物理目标/2个不同锚点有效。
- 正文静态容量余量nav32/pull64/update55/offset31/collision85px；未重排或扩大，未做屏幕验收。图冻结SHA256 `E8E9045FF228D9D84F22A37B1530F1CF6EF0CD10875C5F55DB5422B979F8537F`，232行/7634字节，LF/无BOM/尾随空白0。
- Gate29实际四Camera叶Success/errors=0/warnings=0/entries=[]、44条唯一Offset拒绝已实读；该报告是2026-09-30历史，不是本D3-E新门禁，也不证明A9新准入或全Camera/资产网络。耗尽仅静态、真实解绑仅正常无输入、完整B5/B6/B7及其它自动替代保持开放。
- 23个当前基线保护hash保持，包括已冻结A9 h/cpp；主/覆盖/结构/D1D2及Camera源码/tests未写。Movement并行两旧测试/10记录不属于本基线，不称整个工作区未变化。两记录A11前38734/49884字节原前缀保持A6B411ED…/EAF14D8E…，只追加D3-E。
- 架构核对：既有Component/Stack/Mode/GA/Hero状态与接口归属保持，无新增循环依赖、权威状态、执行链、清理机制或第二调度器。三文件冻结交回、终止写入；两记录最终hash随交回，未运行UE/MCP/构建/自动化/Git/资产/代理，不自动D3-M/Nav或MD状态收尾。

## A13 / D3-M 主流程精确文字同步租约（2026-10-01，北京时间）

- 依据：统筹正式A13三文件授权及当前Parallel Schedule第80行；A11/D3-E已接受冻结。既有05长期组长直接执行，不创建/唤醒代理或临时会话。
- 唯一目标：主流程按当前Camera实现描述每次视角拉取、严格Offset申请与已接受槽消费、合法零值、最终碰撞及空栈Super提前return。职责归属保持：UE触发视角拉取，Component组织管线/持有Offset与最终解析，Stack输出View/Request，Mode提供姿态与请求，GA持请求资源，Hero协调解绑；不新增执行器或第二帧调度。
- 精确写入文件仅三个：
  - `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\GGYGO_流程_相机.canvas`，入口5564字节，SHA256 `14D0A3F21A0678CFA9E6A6B030DC4117A7AD3CAAAA774D30CA64EEC568B971CF`。
  - `F:\ue_project\GGYGO\AAADocs\Modules\Camera\Module_Repair_05_Subleases.md`，入口44268字节，SHA256 `92E2E975B2EF0F491FD7B5499F6E8D102B892D5494B9C6A0BB9D480386924975`。
  - `F:\ue_project\GGYGO\AAADocs\Modules\Camera\Module_Repair_05_Validation.md`，入口54870字节，SHA256 `0EF66A73471834EE668ACA2D69C92D87D2EFAB56B0A7F3D7D9E1BDD58AAA746D`。
- 原子顺序：先本记录登记基线/范围→仅主流程Canvas七正文及一边标签→静态核对并冻结图→追加两记录结果→最终前缀/hash核对后冻结停止。三文件属于一个流程契约及其租约/验证证据，生产、测试、其它图文分阶段且本步不写。
- Canvas文字范围：仅nav、engine、push、offset、collision、empty、output；look-input、choose、evaluate正文不动。仅e7标签从“Super::GetCameraView 兜底”改为“Super直接输出DesiredView到引擎并return”；e7仍empty.right→output.left，output表示引擎接收视图并明确两条互斥路径，不把Super分支引到项目写回动作。
- 必须保持：原10节点/9边、全部ID/顺序/位置/尺寸/颜色/其它属性、全部边端点与边侧、其它八边完整内容、原JSON缩进与文件格式。无需新节点或端点变化；若事实要求新增/改端点则停止交统筹，不扩大租约。
- 验收断言：同帧多次GetCameraView各按SafeDeltaTime推进，无帧号去重；空Class不清旧栈，只有空活动栈调用Super后直接return。SetCameraOffset严格申请：X/Y/Z/FOV有限、In/Out有限非负，非法Error/Invalid且入口槽/alpha/token/计数保持；GA申请前Clear不恢复已释放旧资源。主图运行管线只消费已接受槽；合法alpha/正时间SafeDt0不推进，合法零时间SafeDt0可立即到目标。最终View FOV钳5–170与Set输入拒绝是不同阶段；有效碰撞Request/World/Target/路径时每次拉取至多一种ECC_Camera查询，合法Radius0 line/Recovery0立即恢复。
- 空栈验收：恢复比例置1，同一SafeDt交UCameraComponent::GetCameraView后return，跳过项目Mode/Offset/Resolve及最终组件/Controller写回。正常模式路径才写组件/DesiredView，且只有有效Pawn Controller时同步ControlRotation。
- 只读依赖：实际Component/Stack/Mode/GA/Hero/PawnExtension/CombatantState、既有Camera测试与Build.cs、D1/D2/D3-R/D3-E及Gate30报告；下面23个保护文件按本步入口实读快照，包含A9当前冻结版本，历史A9快照不冒充当前。
- `F:\ue_project\GGYGO\Source\GGYGO\Camera\.gitkeep`：0字节，SHA256 `E3B0C44298FC1C149AFBF4C8996FB92427AE41E4649B934CA495991B7852B855`。
- `F:\ue_project\GGYGO\Source\GGYGO\Camera\GGYGOCameraComponent.cpp`：10950字节，SHA256 `7C3551D8AB4F7AAF990FDB142BE89E133A09CF7B0F043738D8B2FB877177CA15`。
- `F:\ue_project\GGYGO\Source\GGYGO\Camera\GGYGOCameraComponent.h`：4938字节，SHA256 `E490E16D6DAB94161E5904C08BBC0B451D674E6903AC39C75FD56EE046370D04`。
- `F:\ue_project\GGYGO\Source\GGYGO\Camera\GGYGOCameraMode_ThirdPerson.cpp`：1548字节，SHA256 `FF6B13912B0122D182E1ECA94305E3808E87A14B866F0495808CB4FCBD41F65D`。
- `F:\ue_project\GGYGO\Source\GGYGO\Camera\GGYGOCameraMode_ThirdPerson.h`：2301字节，SHA256 `ECE8FAC22D89DC8075F80CBA9182B5E179CC8FF1F479CAD2FF6F87592474CC84`。
- `F:\ue_project\GGYGO\Source\GGYGO\Camera\GGYGOCameraMode.cpp`：11853字节，SHA256 `9212068AFB28CAB564DE506E0BD87CBEB09D91B93C0D44A4496F65FA50905AF2`。
- `F:\ue_project\GGYGO\Source\GGYGO\Camera\GGYGOCameraMode.h`：10967字节，SHA256 `C1FAE5C8D31C47C4119BECAD94829F12D3D8F4A448DCE080E094949331CFCFD1`。
- `F:\ue_project\GGYGO\Source\GGYGO\Camera\Tests\GGYGOCameraLifecycleTest.cpp`：66078字节，SHA256 `542646F1D6E3B621C221B3E43D65FA1CC9379AE756686F0492B613F9269323F6`。
- `F:\ue_project\GGYGO\Source\GGYGO\Camera\Tests\GGYGOCameraLifecycleTestTypes.h`：6085字节，SHA256 `5213508433C1CFEDCA4E56B889C8BACD50A8E477A1B7C0505E749E26CDCE831E`。
- `F:\ue_project\GGYGO\Source\GGYGO\AbilitySystem\Abilities\GGYGOGameplayAbility.h`：17436字节，SHA256 `BEE74DC34ED2C8636192894E964FB73779C17A50E43F4B810B21911CDF58DF51`。
- `F:\ue_project\GGYGO\Source\GGYGO\AbilitySystem\Abilities\GGYGOGameplayAbility.cpp`：27862字节，SHA256 `5BA07252DE4112F44ADCD142EE43F5E8470662A3AC2AC1A28C2E187C31BD117D`。
- `F:\ue_project\GGYGO\Source\GGYGO\Character\Components\GGYGOHeroComponent.h`：9990字节，SHA256 `AF921B89AA8F665D6F8EF9ED2AF9A5D576AE8252AEC650D072DEEB4D24F5CC91`。
- `F:\ue_project\GGYGO\Source\GGYGO\Character\Components\GGYGOHeroComponent.cpp`：31875字节，SHA256 `FEC79B605C4B58A9EEABAC595A4CE53FFC4BC01D55A143535516D2B5B1EACD81`。
- `F:\ue_project\GGYGO\Source\GGYGO\Character\Components\GGYGOPawnExtensionComponent.h`：8651字节，SHA256 `6190EB9134ECDE4735FC67C0CD564D87C3EEDAE9BC477E16ACA296368F7C96FD`。
- `F:\ue_project\GGYGO\Source\GGYGO\Character\Components\GGYGOPawnExtensionComponent.cpp`：14285字节，SHA256 `E76FC4182469B76C30BB0FAE980B5DB2A6D4BD7676BA30C7741F6D24B8BC4E10`。
- `F:\ue_project\GGYGO\Source\GGYGO\Combatants\GGYGOCombatantState.h`：4370字节，SHA256 `A83D67A5C6FC68C788DD3A386A0A5B587F2B319F80AEAB91F3F7DD1BC48C34EF`。
- `F:\ue_project\GGYGO\Source\GGYGO\Combatants\GGYGOCombatantState.cpp`：8950字节，SHA256 `6B53885E047F9FCAEFCFA9C37D3FAEFA1E4ED0C352726B1835694FCFA59D4E84`。
- `F:\ue_project\GGYGO\Source\GGYGO\GGYGO.Build.cs`：2614字节，SHA256 `677F99C4CB6EE8FA3EB9B55A2A95AE12766E72B69C7CE474D5F7F914EE0E1A06`。
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\模式栈实现.md`：9797字节，SHA256 `F12EB3BFAF92B483305DF01E5DD4E786BF3CE19CBC1F86AABE89B837C93C21EF`。
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\结构.md`：15897字节，SHA256 `A19BA8197EACC856611347424E63E4433F4970E776232BEBDFA5BF20FAAED28E`。
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\GGYGO_结构_相机.canvas`：9149字节，SHA256 `062EA06505B68D54DB5EF378118EE6D6000B3B7AF253306A3DC8F6DCDFF1D0DC`。
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\GGYGO_流程_相机模式求值.canvas`：7634字节，SHA256 `E8E9045FF228D9D84F22A37B1530F1CF6EF0CD10875C5F55DB5422B979F8537F`。
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\GGYGO_流程_相机覆盖恢复.canvas`：6966字节，SHA256 `2CE7A4CF2B482060819422DBC7B275581CB87A375C0E38EEC64CCFBDA250307F`。
- Gate30有限入口证据：`F:\ue_project\GGYGO\Saved\AutomationReports\ModuleRepairGate_20261001_30\index.json` SHA256 `65A1C9387911E0A4B64C04236C7B8F46525D8266D0878B93EA267B56E0BEBD23`，2026.09.30-16.48.53 UTC=2026-10-01 00:48:53北京时间，63 Success/failed0；四Camera叶Success、各errors/warnings0、entries=[]。Nav只写四Camera叶有限结果，不称全日志零诊断、完整矩阵或资产/网络闭环。
- 非目标与开放边界：不修改source/tests/资产/其它MD或Canvas/全局入口，不运行UE/MCP/构建/自动化/Git，不自动Nav MD收尾。A12/B8/C17等授权并行范围不纳入本保护快照，不声称整个工作区未变。耗尽仅静态、真实解绑仅正常无输入，Input/IMC重入、Avatar失配/死亡GE、完整B5/B6/B7、生产ViewTarget/资产/网络及其它自动替代仍开放；保留look-input/choose资产文字不等于本步重新读资产或验收设备接线。
- 检查与停止点：实际diff/逆向原文精确恢复、JSON/唯一ID/端点/非空标签、物理wikilink/锚点、零矩形重叠、静态容量与LF/无BOM/无尾随空白、23保护hash及两记录历史前缀。容量只作静态估计，不宣告Obsidian屏幕验收。完成后仅三文件冻结交回，等待后续明确租约。

### D3-M 静态结果与冻结交回

- 唯一结果完成：七正文nav/engine/push/offset/collision/empty/output与e7标签，未增删节点/边。原10节点/9边、19个唯一ID、顺序及全部非正文属性/布局/尺寸/颜色保持；look-input/choose/evaluate三个非目标正文保持，e7仅标签变化，其端点/边侧与其它八边完整内容保持。
- 空栈语义按Component.cpp:279–325实读核对：入口SafeDeltaTime→UpdateCameraModes→只有活动栈空才恢复比例1、Super(SafeDt, DesiredView)后return；跳过项目Mode/Offset/Resolve及组件/Controller写回。e7“Super直接输出DesiredView到引擎并return”指向引擎接收视图终点，output明确模式与Super两条互斥路径，不误导Super复用项目写回。无需端点或新节点。
- 模式路径保持EvaluateStack完整输出View/Request→UpdateAlpha→ApplyOffset→Resolve→有效Pawn Controller可写ControlRotation→组件/DesiredView写回；同帧多次拉取各按传入dt求值，没有新帧号去重/调度器。
- Set是申请阶段，主图Offset步骤消费已接受单槽；非法Set诊断Error/Invalid且入口保持，具体字段顺序与GA先Clear/不恢复资源由已有Offset契约链接说明。合法alpha/正时间SafeDt0不推进，合法零时间SafeDt0可立即到目标；alpha>0且Offset非近零才实际施加并钳最终View FOV 5–170，不代替Set拒绝；Component.cpp:178–192实读确认。有效Request/World/Target/路径每次拉取至多一次ECC_Camera查询，合法Radius0 line/Recovery0立即恢复与错误替代路径分别记录。
- 保存读回完整原文等于预期；七正文/e7标签在内存逆向替回后精确等于入口版本14D0A3F2…，保留原6空格属性缩进，无其它格式diff。初次无序hunk申请未通过定位且图hash仍为入口，随后按原行序完成；失败申请未产生局部写入。
- JSON/ID/端点/非空标签通过；矩形重叠0。8处wikilink到5个物理目标、两处不同标题锚点实读存在。七正文静态容量余量nav27/engine64/push113/offset36/collision56/empty30/output54px，最小27px；未调整布局/尺寸，未做Obsidian屏幕验收。
- 图最终冻结SHA256 `D0DE3816A7B1DCA308AE46BA278FCCDE6D4C9A8CE6EB458A668F1A5CBF2EEDD1`，178行/6162字节，LF/末尾LF/无BOM/CR0/尾随空白0。23个当前保护hash全部保持，含A9当前冻结版本；A12/B8/C17授权并行范围排除，检查不代表整个工作区未变。
- Gate30只作为既有四Camera叶Success/errors=0/warnings=0/entries=[]的有限历史证据，报告实际63 Success/failed0，2026-10-01 00:48:53北京时间；未运行新门禁，报告测试0错误不等于全日志0诊断。耗尽、无输入之外真实解绑、Input/IMC重入/Avatar失配/死亡GE、完整B5/B6/B7、其它自动替代与资产/网络继续开放，不推导A12真实Destroy新专项结果。
- 两记录原44268/54870字节前缀保持入口92E2E975…/0EF66A73…，只追加本D3-M登记/验收。架构核对没有新增依赖/权威状态/执行链/清理责任或调度器；图文仅纠正既有运行流程与验收边界。
- 本三文件冻结停止写入，最终两记录hash随交回；source/tests/其它局部图文/全局入口/资产继续冻结。本步未运行UE/MCP/构建/自动化/Git/资产/代理，不自动Nav MD或其它状态收尾。

## A14 / D3-Nav 局部MD同步状态收尾租约（2026-10-01，北京时间）

- 授权依据：统筹已实读两MD入口与三旧分句，接受零写入预检并正式开放A14；当前Parallel Schedule第82行确认精确四文件。原A13/D3-M保持历史冻结，不能据历史租约扩写。05长期组长直接执行，不创建/唤醒代理或临时会话。
- 唯一文档契约：两份局部MD不再把已静态接受并冻结的D2/D3图文描述为仍待同步；只修正当前同步状态，保持历史门禁、接口算法与所有未验证/待审查边界。两MD属于同一导航状态契约，两记录用于租约与验收证据，四文件无需跨职责扩拆。
- 精确写入文件与入口基线：
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\结构.md`：15897字节，SHA256 `A19BA8197EACC856611347424E63E4433F4970E776232BEBDFA5BF20FAAED28E`。
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\模式栈实现.md`：9797字节，SHA256 `F12EB3BFAF92B483305DF01E5DD4E786BF3CE19CBC1F86AABE89B837C93C21EF`。
- `F:\ue_project\GGYGO\AAADocs\Modules\Camera\Module_Repair_05_Subleases.md`：56167字节，SHA256 `8A0B3878FCB58F448601262078CADEA84A56268E049B168E9FFBA8F8C2D3D351`。
- `F:\ue_project\GGYGO\AAADocs\Modules\Camera\Module_Repair_05_Validation.md`：61559字节，SHA256 `FB51D40A364B7F4B4367824DD0D6AC9FA3DF00CC61E81EB950B34BEF45F8AEBB`。
- 精确文字范围（固定三处分句，无整段重写）：
1. `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\结构.md`第72行段内，只替换下列分句，其余原文保持。
   - 旧：三个流程Canvas仍待独立同步：[[GGYGO_流程_相机覆盖恢复.canvas|覆盖恢复流程]] 的 `unbind` 仍有等待06/无条件Reset旧说明，主流程及模式求值图的Offset节点仍有旧清洗说明；结构配套更新不代表这些流程图已同步。
   - 新：三个流程Canvas已按各自租约完成文字同步并经统筹静态接受冻结：[[GGYGO_流程_相机覆盖恢复.canvas|覆盖恢复流程]]、[[GGYGO_流程_相机模式求值.canvas|模式求值流程]] 与 [[GGYGO_流程_相机.canvas|主流程]]。这里只更新图文同步状态；耗尽、Input/IMC重入、完整B5/B6/B7、其它自动替代及资产/网络仍保留上列开放边界。
2. `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\模式栈实现.md`第60行段内，只替换下列分句，其余原文保持。
   - 旧：该图旧无条件 Reset/等待06说明仍待单独同步。
   - 新：该图已按D3-R同步唯一协调入口、后继 guard、正常清理与 EndPlay 分支，并经统筹静态接受冻结；真实解绑叶仍仅证明正常无输入会话路径。
3. `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\模式栈实现.md`第68行段内，只替换下列分句，其余原文保持。
   - 旧：结构页及四Canvas的本轮证据/文字同步尚须独立授权，不由本文更新宣告全部同步。
   - 新：D2结构页/结构图及D3覆盖恢复、模式求值、主流程图已分别按授权完成文字同步并经统筹静态接受冻结；这里只确认静态图文同步，不新增动态验收，也不关闭其它自动替代或资产/网络边界。
- 必须保留：结构页第72行段的前两句；实现说明第60/68行段所有非目标分句；其它全文、标题、接口/算法表、Gate22/26/27历史数据、I/T有限证明、耗尽/GA前Clear/Input重入/完整B5/B6/B7及其它自动替代/资产网络开放边界。记录只追加，Subleases前56167字节和Validation前61559字节对应上列入口hash须精确保持。
- 四Canvas只读保护基线：
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\GGYGO_结构_相机.canvas`：9149字节，SHA256 `062EA06505B68D54DB5EF378118EE6D6000B3B7AF253306A3DC8F6DCDFF1D0DC`。
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\GGYGO_流程_相机覆盖恢复.canvas`：6966字节，SHA256 `2CE7A4CF2B482060819422DBC7B275581CB87A375C0E38EEC64CCFBDA250307F`。
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\GGYGO_流程_相机模式求值.canvas`：7634字节，SHA256 `E8E9045FF228D9D84F22A37B1530F1CF6EF0CD10875C5F55DB5422B979F8537F`。
- `F:\Obsidian\Doc\lyra学习笔记\GGYGO架构规划\Camera\GGYGO_流程_相机.canvas`：6162字节，SHA256 `D0DE3816A7B1DCA308AE46BA278FCCDE6D4C9A8CE6EB458A668F1A5CBF2EEDD1`。
- 依赖与顺序：D2/D3-R/D3-E/D3-M已由统筹静态接受冻结→本记录先登记→两MD三分句精确替换→实际保存读回/链接及锚点/内存逆向原文/四Canvas保护hash→两记录追加结果→四文件最终hash交回并停止。共享接口无变化、状态和生命周期归属不变；源码/tests/图文的既有冻结保持，本步无实现或测试阶段。
- 验收断言：三旧分句仅各一次替换，候选全文链接21处/物理目标10个/锚点3处均有效；新增导航链接仅模式求值与主流程两处，覆盖恢复既有链接保留。内存逆向替回三分句须精确恢复两MD入口原文；四Canvas hash保持；文件LF/无BOM/无CR/尾随空白0并保存读回完整；记录历史前缀保持。
- 非目标：不写source/tests/Canvas/其它MD/全局入口/资产，不运行UE/MCP/构建/自动化/Git/代理；不新增动态或屏幕验收，不推导A12真实Destroy验证结果，不把Camera全面合规、其它自动替代整改或资产网络标为完成，不自动下一整改。
- 停止点：完成本四文件实际diff/引用/逆向/前缀/hash核对后冻结交回；若旧分句、链接或保护hash不符合入口则停止说明，不扩大范围或自行修其它文件。

### D3-Nav 静态结果与冻结交回

- 唯一契约完成：两局部MD仅三处分句替换，结构页第72行段前两句、实现说明第60/68行所有非目标分句保持；Gate22/26/27历史证据、接口算法与其它待审查/未验证边界均保持。文字只将D2/D3图文状态改为按授权完成、统筹静态接受冻结。
- 完整实际diff与保存读回精确等于预检候选全文；内存逆向替回三分句后两MD原文精确恢复入口A19BA819…/F12EB3BF…，没有无关正文、标题、换行或格式变化。
- 两MD共21处wikilink，10个实际物理目标存在，三个标题锚点“已验证与待审查边界”“解绑协调与后继保护”“当前实现与验证边界”实读有效。新增只为结构页模式求值/主流程两处导航引用，不新建目标文件或改其它链接。
- 结构MD冻结88行/16026字节，SHA256 `7558F6EA132FB58EE413CD6228DA0D71D7A45A837EEB70CAFA7F734AF06B6A7B`；模式栈实现MD冻结75行/10061字节，SHA256 `4B20EC5839F27207D96EDB9F7A090D70EAAAA7577B7A9F8656E1A81E84F3CB5A`。两文及记录读回LF/末尾LF/无BOM/CR0/尾随空白0；本步没有新增屏幕或动态验收。
- 四Canvas入口保护hash保持，结构/覆盖恢复/模式求值/主流程均未写。本检查只覆盖本租约目标与四图，不声称整个工作区未变。
- 两记录前56167/61559字节历史前缀精确保持8A0B3878…/FB51D40A…，只追加本A14登记/验收，不改A13及其它历史。最终两记录hash随交回。
- 有限证明边界保持：耗尽仅静态、真实解绑仅正常无输入，Input/IMC重入、Avatar失配/死亡GE、完整B5/B6/B7、其它非法参数自动替代与资产/网络仍开放；不从图文同步推导A12真实Destroy结果或Camera全面合规。
- 架构核对：未引入依赖/接口/权威状态/执行链/清理责任/帧调度变化，没有扩大跨模块写入。唯一差异为当前图文同步状态与既有冻结事实对齐。
- 本四文件冻结停止写入；未运行UE/MCP/构建/自动化/Git/资产/代理，不自动下一整改。后续需统筹明确新租约。
