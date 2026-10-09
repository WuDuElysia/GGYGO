---
inclusion: manual
---

# Lyra 只读参考

仅在比较 Lyra 的具体设计时使用，不作为每次编辑的前置阅读。

- 完整工程：F:/ue_project/LyraStarterGame，只读。
- Gameplay：Source/LyraGame；Editor：Source/LyraEditor；插件：Plugins。
- GGYGO/Lyra/ 是旧局部片段，不是完整权威副本。

用 rg 按问题定位实际接口；常用入口是 LyraAbilitySystemComponent、LyraAbilitySet、LyraGameplayAbility、LyraPawnExtensionComponent、LyraHeroComponent、LyraCharacterMovementComponent、LyraCameraMode 和 LyraExperienceManagerComponent，无需加载完整目录／类索引。

Lyra 是联网射击范式。借用前核实状态归属、复制／预测需求及真实插件依赖；不要把 Experience、Inventory、GameFeature 或消息总线作为动作项目的默认必需层。
