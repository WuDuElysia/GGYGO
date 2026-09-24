# Pyrios 材质还原差距核查（2026-09-24）

## 对照输入

- 游戏截图：`References/Pyrios_Game_Reference_01.png`、`References/Pyrios_Game_Reference_02.png`。第二张适合检查主体装甲，第一张适合检查能量爆发和后处理。
- 原始数据：`F:/AnimeStudio/Exports/Animator/Avatar_Male_Size03_Pyrois_Model/Materials/MAT_Pyrois_*.json`、同目录 PNG，以及 `F:/AnimeStudio/Exports/Shader/miHoYo_Character_NapAvatarStandard.shader`。项目 `Content/Characters/Player/Pyrios/Materials/` 内的 Body_1 JSON 与原导出文件 SHA-256 相同：`599609426FC1AD57F7898875C8B447C2EED064D1FBE8D9617692EBFC2FC1F326`。
- UE 对照：`Saved/PyriosMeshTierFixedFocused.png` 为当前模型资产视口；`Saved/PyriosMeshNoMatcapFocused.png` 为仅在内存中临时关闭 MatCap 的诊断画面，随后已从 JSON 重新生成并恢复。

## 结论

上一版只读取了 JSON 的四张主体贴图、五组浅/暗色和少量标量，主光照用一个固定 `smoothstep` 两色带代替原 Shader。MatCap 的贴图与强度曾由脚本手写，而非按 JSON 层位接线。因此上一版是 **风格近似**，不能称为原材质等价还原。Unity 导出格式本身不是主因：JSON 和贴图保留了逐材质参数，导出的 Shader 也可供核查。JSON 不包含运行中的全局灯光、阴影、曝光、LUT 和后处理，单独复刻材质仍无法复制游戏截图。

## 已确认的差距与修正

| 项目 | 证据 | 当前处理 |
| --- | --- | --- |
| 材质 ID 顺序 | `_OtherDataTex.R` 主要值为 `255/179/129`，对应原 Shader 的 `4 - floor(R*5)` 分组；上一版按从小到大选 `ShallowColor1..5`。 | 已按反序修正五组浅/暗色。 |
| MatCap 槽位 | Body_1 JSON 使用第 2/4 槽，Body_2 使用第 1/2/4 槽，Weapon01 使用第 2/3/5 槽；上一版只放两张手选贴图，并以手写 0.05～0.4 强度叠加。 | 五槽现在从 JSON 读取纹理、Tint、ColorBurst、AlphaBurst 和 BlendMode；仅对相应材质 ID 组启用。混合公式仍待逐变体核对。 |
| MatCap 遮罩 | 三张 `_M` 图的 Alpha 均为 1；将它作为遮罩再把多个 MatCap 加到整个人体会抬白所有区域。临时禁用 MatCap 后，UE 胸甲立刻恢复为深灰。 | 去掉全身叠加；保留 JSON `_UseMatCapMask` 开关。 |
| 编辑器 MatCap 方向 | 上一版用运行时组件写入的 CameraRight/Up；静态材质球没有实时相机向量。 | 材质内改用世界法线转 View 空间，静态预览可随视角变化。 |
| Diffuse 阴影 | 现有 HLSL 把 `_LightTex.B` 缩放成小偏移，以 `smoothstep(0.32,0.48)` 做两色混合；原 Shader 包含法线高度补偿、三区域 Ramp、顶点遮罩、间接光和逐组阴影参数。 | 尚未等价实现，是主体平面感和对比不足的主要剩余原因。 |
| 高光/边缘光 | 现有高光是单一 `pow(N·H,40)`，边缘光是单一白光 Fresnel；JSON 有五组高光与亮面/暗面边缘光参数。 | 尚未按组移植。 |
| 场景与特效 | 原图是冷蓝夜景，亮银边和暗蓝主体共存，中心有强烈能量光与 Bloom；当前资产编辑器使用日间预览，材质采用 Unlit/Emissive，默认白色主光，`Body_FX01` 溶解/能量材质尚未移植。 | 需要用固定曝光的参考场景分别校准材质、光照和后处理；材质球只用于检查接线。 |

## 后续还原顺序

1. 以导出 Shader 的实际启用变体核查 Material ID、Ramp、MatCap 混合与五组镜面参数，不把已有注释文档当作最终实现依据。
2. 在固定相机、姿态、曝光和蓝色主光的 UE 对照场景中复拍；先对比无 MatCap 的 Albedo/Ramp，再逐组打开 MatCap 与高光。
3. 移植 `Body_FX01` 的能量/溶解路径及中心发光，最后调 Bloom、描边和场景调色。

当前 `M_Pyrois_Toon` 已通过 UE 编译，三份 MI 的 MatCap 贴图接线与 JSON 自动核对通过；视觉相似度仍不足，不标记为完成还原。
