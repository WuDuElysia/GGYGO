// Copyright Epic Games, Inc. All Rights Reserved.

using System.IO;
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
			"Engine",
			"InputCore",               // Input 桥接的公开 FKey 参数。
			"GameplayTags",            // Boss 制作接口的公开 FGameplayTag 参数。
			"Niagara",                 // 批量作者入口公开的 FNiagaraTypeDefinition。
			"NiagaraEditor",           // 公开作者输入复用原 FNiagaraExt_StackInputValue。
			// 编辑器编译入口的公开基类；不进入 GGYGO 运行时模块。
			"ToolsetRegistry"
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
			"EnhancedInput",           // Input 桥接直接核 EnhancedPlayerInput。
			"GameplayAbilities",       // Combat ActionObservation 的 GAS 直接依赖。
			"GameplayTasks",           // Pose Observation 公开 KnownTasks 迭代器的直接链接依赖。
			"Json",                       // Kevin 动作清单与生成配置
			"KismetCompiler",             // 生成后编译 ABP
			"RHI",                        // GPU staging readback 与原表面格式转换
			"RenderCore",                 // 原渲染命令队列，不阻塞 GT 等待 GPU
			"ImageWrapper",               // 后台 PNG 编码；GT 入场只核模块已预载
			"UnrealEd"
		});

		// 同帧测试读取此版本的 FViewInfo 私有布局，其传递头也使用 Renderer/Internal。
		string rendererDirectory = Path.Combine(EngineDirectory, "Source", "Runtime", "Renderer");
		string rendererPrivate = Path.Combine(rendererDirectory, "Private");
		string rendererInternal = Path.Combine(rendererDirectory, "Internal");
		bool useNativeMeshProbe = Target.Platform == UnrealTargetPlatform.Win64
			&& Target.Version.MajorVersion == 5 && Target.Version.MinorVersion == 8
			&& Target.Version.PatchVersion == 1 && Target.Version.Changelist == 56057345
			&& File.Exists(Path.Combine(rendererPrivate, "SceneRendering.h"))
			&& File.Exists(Path.Combine(rendererInternal, "TranslucentPassResource.h"));
		PrivateDefinitions.Add($"GGYGO_WITH_NATIVE_MESH_PROBE={(useNativeMeshProbe ? 1 : 0)}");
		if (useNativeMeshProbe)
		{
			PrivateIncludePaths.Add(rendererPrivate);
			PrivateIncludePaths.Add(rendererInternal);
			PrivateDependencyModuleNames.Add("Renderer");
		}
	}
}
