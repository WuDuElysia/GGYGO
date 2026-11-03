// 通用场渲染机制；角色与招式配置由资产及原 FX 生命周期提供。
using UnrealBuildTool;

public class GGYGORendering : ModuleRules
{
	public GGYGORendering(ReadOnlyTargetRules Target) : base(Target)
	{
		PCHUsage = PCHUsageMode.UseExplicitOrSharedPCHs;
		PublicIncludePaths.Add(ModuleDirectory);
		// 标准项目通过公开BeforeDOF接口接入；能力由此构建声明明确开启。
		PublicDefinitions.Add("GGYGO_WITH_DISTORTION_FIELD=1");
		// 公共field类型直接暴露RHI引用/RenderGraph前向类型。
		PublicDependencyModuleNames.AddRange(new[] { "Core", "CoreUObject", "Engine", "Niagara", "NiagaraCore", "RHI", "RenderCore" });
		PrivateDependencyModuleNames.AddRange(new[] { "Renderer", "NiagaraVertexFactories" });
	}
}
