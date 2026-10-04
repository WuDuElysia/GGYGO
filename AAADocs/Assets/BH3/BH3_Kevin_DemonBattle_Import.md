# BH3 Kevin DemonBattle 导入核对

## 结果（2026-09-29，UE 5.8）

- 先清点 BH3 全目录：931 文件，320 FBX / 424 JSON / 187 PNG。只导入 `F:/AnimeStudio/Exports/BH3/Animator/Kevin/05_BOSS_411_DemonBattle`。
- 目标 `/Game/Characters/Boss/Kevin/DemonBattle/`，本模块写入 `Mesh/` 和 `Animation/`。
- 已保存 1 SkeletalMesh、1 独立 Skeleton、75 AnimSequence，共 77 资产。75/75 含曲线动画成功；79 条源索引中 4 条没有动画曲线，未生成动画。
- 模型 `Mesh/SK_Kevin_DemonBattle`，Skeleton `Mesh/SK_Kevin_DemonBattle_Skeleton`，动画 `Animation/AS_<源clip名>`。
- `BOS_411_Ani_Counter` 与 `BOSS_340_Ani_Stun` 已按完整层级匹配并成功导入；没有按名称过滤。非法字符确定性替换为下划线，审计无命名碰撞。

## 骨架、尺度与样片

源 FBX 7300，Y-up，UnitScaleFactor=1cm，导出已烘焙100倍。导入统一比例1、坐标转换开启、单位转换开启、ForceFrontXAxis=false、额外平移旋转为零。源文件只读，未执行 Pyrios 去根、重定向或骨架复用。

模型有484个非网格Model与7个网格；79动画以LimbNode保留网格名，491节点名称/父子层级与模型一致。UE Skeleton回读491节点，根BOSS_411，Bip001和名为Root的辅助节点均在其下。JSON Avatar骨数358是来源元数据，不能作为实际导入骨数。

Mesh参考包围盒约399.56×460.36×335.91cm，包含武器和翼部。StandBy Persona预览人物直立、武器/翼部完整，没有明显蒙皮爆开；玩法前向尚未验收。

StandBy以60fps导入，132键、131帧区间、2.1833334s。JSON stopTime=2.1666667s，FBX原始Take多一帧，保留原导出范围。Fly_Attack_03_AS/Summon/Between/Shoot/BS按来源30fps导入，其余按60fps。每条动画回读同一Skeleton、正时长、enable_root_motion=false、force_root_lock=false。Unity loopTime仅保存在BH3.SourceLoopTime元数据中，未生成状态机循环接线。

## 源空片段

| 源clip | 结果 |
| --- | --- |
| BOSS_411_Ani_Add_HitBox | 无AnimationCurve，1秒空Take；未生成AnimSequence |
| BOSS_411_Ani_Normal_HitBox | 同上 |
| BOSS_411_Ani_No_Weapon | 同上 |
| BOSS_411_Ani_Have_Weapon | 同上 |

初次UE批量返回4个导入失败（未找到网格或动画轨道）；原始报告保留。最终报告结合源审计归类source_empty，脚本已补充空曲线预检。没有合成动作、修改原FBX或把此问题归为骨架不兼容。

## 渲染接线契约

| 槽序号 | 实际材质槽名 |
| --- | --- |
| 0 | BOSS_411_Weapon_Blade_Material |
| 1 | BOSS_411_Material_Face |
| 2 | BOSS_411_Material_Eye |
| 3 | BOSS_411_Material_Hair |
| 4 | BOSS_411_Material_Wing |
| 5 | BOSS_411_Material_Body02 |
| 6 | BOSS_411_Material_Wings_Blue |
| 7 | BOSS_411_Material_Body01 |

导入阶段关闭材质/贴图自动导入，保留8槽。Materials、Textures及后续材质接线交给渲染模块。本轮动画预览不需PhysicsAsset，因此未创建；没有BossAI、ABP、Montage或主关卡接线。

## 脚本与报告

脚本 `AAADocs/Scripts/import_bh3_kevin_demonbattle.py`：

```text
python import_bh3_kevin_demonbattle.py --stage audit
py "F:/ue_project/GGYGO/AAADocs/Scripts/import_bh3_kevin_demonbattle.py" --stage smoke
py "F:/ue_project/GGYGO/AAADocs/Scripts/import_bh3_kevin_demonbattle.py" --stage all
```

后两条在独占编辑器时段、底部Cmd执行；先核对smoke预览再all。脚本使用FbxFactory，临时关闭Interchange FBX并在finally恢复原值。已有资产必须匹配BH3.ImportOwner与来源SHA256（动画同时匹配Skeleton）、没有未保存修改且有磁盘包才只读跳过，未知资产停止，不覆盖。保存返回值和磁盘包存在性都通过才标 imported；保存失败不能计为完成。整批重复执行尚未另跑一轮；StandBy在原 all 阶段已通过旧版已有资产分支。A5 新保护只做离线测试，尚未重跑 UE 导入；见 `AAADocs/Modules/Animation/Animation_Asset_Production_Safety.md`。

运行报告位于项目`Saved/Codex/`：

- `bh3_demonbattle_source_audit.json`：全目录统计、骨架层级、单位、源哈希、79条映射。
- `bh3_demonbattle_smoke_report.json`：模型+StandBy成功。
- `bh3_demonbattle_all_report.json`：原始批量执行，74新增/1已存验证/4源空失败。
- `bh3_demonbattle_final_report.json`：保留原始失败信息并分类4项source_empty；importable_complete=true，index_fully_imported=false。
- `bh3_demonbattle_verification.json`：独立只读核验已执行；75 条动画共用本包 Skeleton、491 层级节点，材质导入后全目录为 104 资产。

UE日志`Saved/Logs/GGYGO.log`：08:21:46模型导入，08:21:49样片保存，08:25:23批量结束（日志时间UTC）。模型存在缺失平滑组与部分bind pose信息提示，UE报告重建绑定姿势成功。75动画仅StandBy进行了视觉预览；其余逐条视觉、材质质量、物理和玩法表现仍未验收。

架构说明与三张 Animation Canvas、根导航/状态及总览入口已同步。Content/Characters 依照现有美术资产管线处于 Git 忽略范围；本次提交脚本与说明，104 个 `.uasset` 保存在本机，不随普通 Git 提交分发。
