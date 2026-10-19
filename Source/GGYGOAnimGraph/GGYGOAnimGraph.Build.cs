/** @file GGYGOAnimGraph.Build.cs @brief 动画蓝图编译节点的依赖边界。 */
using UnrealBuildTool;

public class GGYGOAnimGraph : ModuleRules
{
	public GGYGOAnimGraph(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicDependencyModuleNames.AddRange(new string[]
		{
			"Core", "CoreUObject", "Engine", "GGYGO", "AnimGraph", "BlueprintGraph"
		});
		PrivateDependencyModuleNames.Add("UnrealEd");
	}
}
