// Copyright Epic Games, Inc. All Rights Reserved.

using UnrealBuildTool;

public class GGYGOEditor : ModuleRules
{
	public GGYGOEditor(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;

		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core",
			"CoreUObject",
			"Engine"
		});

		PrivateDependencyModuleNames.AddRange(new string[]
		{
			"AIModule",
			"AnimGraph",                  // Kevin ABP 姿态节点
			"AnimGraphRuntime",           // SequencePlayer 与 Slot 运行时节点
			"AnimationModifiers",        // UAnimationModifier
			"AnimationBlueprintLibrary", // UAnimationBlueprintLibrary（曲线读写）
			"AnimationDataController",   // IAnimationDataController
			"AssetRegistry",              // 注册新建的测试 AnimSequence
			"BlueprintGraph",             // ABP 图与引脚
			"GGYGO",
			"GameplayTags",
			"Json",                       // Kevin 动作清单与生成配置
			"KismetCompiler",             // 生成后编译 ABP
			"UnrealEd"
		});
	}
}
