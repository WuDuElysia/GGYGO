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
			"AnimationModifiers",        // UAnimationModifier
			"AnimationBlueprintLibrary", // UAnimationBlueprintLibrary（曲线读写）
			"AnimationDataController",   // IAnimationDataController
			"AssetRegistry",              // 注册新建的测试 AnimSequence
			"UnrealEd"
		});
	}
}
