# BH3 导出素材清单与本次导入范围

清点日期：2026-09-29。来源：`F:\AnimeStudio\Exports\BH3`。本次只导入 `Animator/Kevin/05_BOSS_411_DemonBattle`，其他角色形态及 Stage 仅清点。源文件保持原样。

## 全目录概况

共 **931 个文件**：320 FBX、424 JSON、187 PNG。`Animator` 下 792 个文件；`Stage` 下 139 个文件。角色分组名称来自导出目录，具体游戏内阶段含义尚未做原游戏对照。

| 目录 | 内容与用途 | 动画片段数 | 文件数 | 大小（MiB） |
| --- | --- | ---: | ---: | ---: |
| `Animator/Kevin/01_NPC_Kevin` | `NPC_Kevin`，NPC 模型与配套动画 | 1 | 19 | 3.66 |
| `Animator/Kevin/02_NPC_Kevin_GodWar` | `NPC_Kevin_GodWar`，另一套 NPC 模型 | 1 | 18 | 3.61 |
| `Animator/Kevin/03_Kevin_Human` | `Avatar_Fake_Kevin_Human`，Human 模型与动作集 | 43 | 109 | 112.64 |
| `Animator/Kevin/04_Kevin_Demon` | `Avatar_Fake_Kevin_Demon`，Demon 模型与动作集 | 47 | 120 | 201.65 |
| `Animator/Kevin/05_BOSS_411_DemonBattle` | `BOSS_411`，本次导入的魔化战斗 Boss | 79 | 184 | 368.11 |
| `Animator/Kevin/06_BOSS_451_Salvation` | `BOSS_451`，Salvation 命名的 Boss 形态与动作集 | 109 | 235 | 551.80 |
| `Animator/Kevin/07_BOSS_452_Human` | `BOSS_452`，Human 命名的 Boss 形态与动作集 | 30 | 82 | 47.47 |
| `Animator/Kevin/08_BOSS_411_Island` | 411 Island 模型及材质贴图；本包无动画 FBX/动画总览 | 0 | 25 | 5.56 |
| `Stage/Stage_KevinBoss_P1` | P1 场景包：1 FBX、73 PNG、40 材质 JSON | — | 114 | 42.75 |
| `Stage/Stage_KevinBoss_P3` | P3 场景包：1 FBX、14 PNG、10 材质 JSON | — | 25 | 14.47 |

动画数来自各包 `anim_settings.json.clipCount` 与 FBX 数量核对；索引数不保证每个文件有可播放轨道。源 JSON 的骨骼数不等同于最终 UE 导入后的骨骼数。场景几何与材质说明见 [BH3_Stage_Inventory.md](BH3_Stage_Inventory.md)（地编模块清点报告）。

Stage 的 FBX 是保留层级与摆放变换的多网格场景：P1 有 77 个网格，主要为建筑、道具与天空；P3 有 97 个网格，主要为球体、岩石与天空。未检出蒙皮 Boss 本体，也不是可直接装入 UE Landscape 的高度图。P1 的 14 个 Collision 节点均无实体几何；P3 有两个真实碰撞候选网格。原 shader、实际灯光及玩法组件不完整，后续导场景还需重建材质、灯光与碰撞。

## DemonBattle 包内内容

- `BOSS_411.fbx`：模型 FBX（约 2.20 MiB）。
- `anim/`：79 个动画 FBX 与逐片段 JSON，包含待机、冲刺/横移、冰系/火系/飞行攻击、翼防御、受击、倒地、处决、投技以及武器/HitBox 辅助片段。名称仅说明源文件用途线索，不能直接作为已实现的战斗规则。
- `anim_settings.json`：模型、Avatar、动画索引；记录 `scaleFactorBakedIntoFbx=100`、源骨架 358 骨、根运动骨 `Bip001`、`applyRootMotion=false`。导入先验证尺度，避免重复放大 100 倍。
- 16 个 PNG：身体、脸、头发、眼睛、翼与武器颜色/遮罩及辅助纹理。Lightmap 名称来自原始着色器，不能直接视作 UE 烘焙光照或法线。
- `Materials/`：8 个材质 JSON（Body01、Body02、Eye、Face、Hair、Wing、Wings_Blue、Weapon_Blade），作为材质槽和纹理参数映射依据；不是可直接导入的 UE Material。

`BOS_411_Ani_Counter` 和 `BOSS_340_Ani_Stun` 虽然名称不同，仍列在本包动画索引中；按实际骨架与轨道兼容性检查，不仅凭文件名前缀排除。

## UE 目录与导入契约

```text
/Game/Characters/Boss/Kevin/DemonBattle/
  Mesh/       独立 SkeletalMesh、Skeleton（本次未创建 PhysicsAsset）
  Animation/  本包动画；保留可追溯的源名称
  Materials/  本包基础预览材质与实例
  Textures/   本包材质所需纹理
```

模型/动画共用本 Boss 独立骨架。先导模型与代表片段确认尺度、朝向、层级、姿势，再批量导入其余片段。材质 JSON 由脚本解析映射为基础可见材质；此阶段不等同原游戏着色器复原。

## 当前实施状态

模型与动画已保存：`Mesh/SK_Kevin_DemonBattle`、`Mesh/SK_Kevin_DemonBattle_Skeleton` 和 `Animation/` 下 75 条 AnimSequence。实际 Skeleton 有 491 个层级节点；导入比例 1，无重复放大。StandBy 已在 Persona 检查人物、翼和武器姿势，未逐条视觉验收全部动作。

79 条索引中的 `Add_HitBox`、`Normal_HitBox`、`No_Weapon`、`Have_Weapon` 四条源 FBX 无 AnimationCurve，仅骨架与空 Take；未生成动画，不是骨架不兼容，也不制造占位片段。Counter 与 Stun 虽然命名前缀不同，均成功导入。动画细节见 [BH3_Kevin_DemonBattle_Import.md](BH3_Kevin_DemonBattle_Import.md)。

材质已保存并绑定：`Textures/` 下 16 张贴图、`Materials/Preview/` 下 3 个基础主材质、`Materials/` 下 8 个材质实例，8 槽一一对应，共计 **104 个 UE 资产**。颜色图使用 sRGB；LightMap/FaceMap/SP 等数据纹理保留为线性数据，不误接为 UE 光照图或法线。

独立模型预览已确认身体、翼、武器与贴图可见；无光照和 Lit 两种模式均已检查。Lit 预览可见基础光照与投影，截图在 `Saved/Codex/bh3_kevin_material_preview_lit.png`；这是基础材质预览，不是原游戏 Toon Shader/特效还原。动画只读核验 `Saved/Codex/bh3_demonbattle_verification.json` 确认 75 动画共用 491 节点骨架、104 资产可枚举。未逐条视觉验收所有动作。

项目现有 `.gitignore` 排除 `Content/Characters` 美术资产；本次保留该外部资产管线约定。导入脚本和说明纳入 Git，本机保存的 `.uasset` 不等于已随 Git 分发；其他机器复现需要同一来源文件及导入脚本。

本任务交付素材资产与文档，不创建 Boss AI 行为、不替换主场景或玩家、不把动画曲线自动接入 CMC。地形与其余七套角色包均不导入。
