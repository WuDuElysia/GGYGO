/** @file GGYGOSignedFieldMeshPass.cpp
 *  @brief 使用公开mesh-pass入口累加两路float4，角色来自实际shader map的互斥编译证书。
 */
#include "GGYGOSignedFieldMeshPass.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGODistortionFieldComponent.h"
#include "Niagara/GGYGOSignedFieldVertexFactory.h"
#include "DataDrivenShaderPlatformInfo.h"
#include "MaterialShader.h"
#include "Materials/MaterialRenderProxy.h"
#include "MaterialShared.h"
#include "MeshMaterialShader.h"
#include "MeshPassProcessor.inl"
#include "RenderGraphBuilder.h"
#include "SceneInterface.h"
#include "SceneRendererInterface.h"
#include "SceneTexturesConfig.h"
#include "SceneUniformBuffer.h"
#include "ShaderParameterStruct.h"

namespace
{
bool IsFieldMaterial(const FMaterialShaderParameters& Parameters)
{
	return Parameters.MaterialShaderTags.Contains(FName(TEXT("SignedDistortionField")));
}

uint32 RequiredMaterialSlots(const FMaterialShaderParameters& Parameters)
{
	uint32 Slots = 0;
	for (uint32 Parameter = 0; Parameter < 4; ++Parameter)
	{
		if (Parameters.MaterialShaderTags.Contains(FName(*FString::Printf(TEXT("GGYGOSignedField.RequiresDP%u"), Parameter))))
		{
			Slots |= 1u << Parameter;
		}
	}
	return Slots;
}

void SetMaterialStreamEnvironment(const FMaterialShaderPermutationParameters& Parameters,
	FShaderCompilerEnvironment& Environment)
{
	Environment.SetDefine(TEXT("GGYGO_REQUIRED_DP_SLOTS"), RequiredMaterialSlots(Parameters.MaterialParameters));
}

bool IsFieldFactory(const FVertexFactoryType* Factory)
{
	return Factory == &FGGYGOSignedFieldMeshVertexFactory::StaticType
		|| Factory == &FGGYGOSignedFieldSpriteVertexFactory::StaticType
		|| Factory == &FGGYGOSignedFieldCameraPositionVertexFactory::StaticType;
}

class FGGYGOSignedFieldRolePS final : public FMaterialShader
{
public:
	DECLARE_SHADER_TYPE(FGGYGOSignedFieldRolePS, Material);
	class FIsField : SHADER_PERMUTATION_BOOL("GGYGO_COMPILED_FIELD_ROLE");
	class FRequiredSlots : SHADER_PERMUTATION_INT("GGYGO_REQUIRED_DP_SLOTS", 16);
	using FPermutationDomain = TShaderPermutationDomain<FIsField, FRequiredSlots>;
	FGGYGOSignedFieldRolePS() = default;
	FGGYGOSignedFieldRolePS(const ShaderMetaType::CompiledShaderInitializerType& Initializer)
		: FMaterialShader(Initializer) {}
	static bool ShouldCompilePermutation(const FMaterialShaderPermutationParameters& Parameters)
	{
		return !IsMobilePlatform(Parameters.Platform)
			&& Parameters.MaterialParameters.MaterialDomain == MD_Surface
			&& FPermutationDomain(Parameters.PermutationId).Get<FIsField>() == IsFieldMaterial(Parameters.MaterialParameters)
			&& FPermutationDomain(Parameters.PermutationId).Get<FRequiredSlots>() == RequiredMaterialSlots(Parameters.MaterialParameters);
	}
};
IMPLEMENT_MATERIAL_SHADER_TYPE(, FGGYGOSignedFieldRolePS,
	TEXT("/GGYGORendering/Private/GGYGOSignedFieldRole.usf"), TEXT("MainPS"), SF_Pixel);

class FGGYGOSignedFieldVS final : public FMeshMaterialShader
{
public:
	DECLARE_SHADER_TYPE(FGGYGOSignedFieldVS, MeshMaterial);
	FGGYGOSignedFieldVS() = default;
	FGGYGOSignedFieldVS(const ShaderMetaType::CompiledShaderInitializerType& Initializer)
		: FMeshMaterialShader(Initializer) {}
	static bool ShouldCompilePermutation(const FMeshMaterialShaderPermutationParameters& Parameters)
	{
		return !IsMobilePlatform(Parameters.Platform) && IsFieldFactory(Parameters.VertexFactoryType)
			&& IsFieldMaterial(Parameters.MaterialParameters)
			&& Parameters.MaterialParameters.MaterialDomain == MD_Surface;
	}
	static void ModifyCompilationEnvironment(const FMaterialShaderPermutationParameters& Parameters,
		FShaderCompilerEnvironment& Environment)
	{
		FMeshMaterialShader::ModifyCompilationEnvironment(Parameters, Environment);
		SetMaterialStreamEnvironment(Parameters, Environment);
	}
};

class FGGYGOSignedFieldPS final : public FMeshMaterialShader
{
public:
	DECLARE_SHADER_TYPE(FGGYGOSignedFieldPS, MeshMaterial);
	class FFloat32 : SHADER_PERMUTATION_BOOL("GGYGO_FIELD_FLOAT32_TARGETS");
	using FPermutationDomain = TShaderPermutationDomain<FFloat32>;
	FGGYGOSignedFieldPS() = default;
	FGGYGOSignedFieldPS(const ShaderMetaType::CompiledShaderInitializerType& Initializer)
		: FMeshMaterialShader(Initializer) {}
	static bool ShouldCompilePermutation(const FMeshMaterialShaderPermutationParameters& Parameters)
	{
		return FGGYGOSignedFieldVS::ShouldCompilePermutation(Parameters);
	}
	static void ModifyCompilationEnvironment(const FMaterialShaderPermutationParameters& Parameters,
		FShaderCompilerEnvironment& Environment)
	{
		FMeshMaterialShader::ModifyCompilationEnvironment(Parameters, Environment);
		SetMaterialStreamEnvironment(Parameters, Environment);
		const EPixelFormat Format = FPermutationDomain(Parameters.PermutationId).Get<FFloat32>()
			? PF_A32B32G32R32F : PF_FloatRGBA;
		Environment.SetRenderTargetOutputFormat(0, Format);
		Environment.SetRenderTargetOutputFormat(1, Format);
	}
};
IMPLEMENT_MATERIAL_SHADER_TYPE(, FGGYGOSignedFieldVS,
	TEXT("/GGYGORendering/Private/GGYGOSignedFieldAccumulate.usf"), TEXT("MainVS"), SF_Vertex);
IMPLEMENT_MATERIAL_SHADER_TYPE(, FGGYGOSignedFieldPS,
	TEXT("/GGYGORendering/Private/GGYGOSignedFieldAccumulate.usf"), TEXT("MainPS"), SF_Pixel);

BEGIN_GLOBAL_SHADER_PARAMETER_STRUCT(FGGYGOSignedFieldPassUniformParameters, )
	SHADER_PARAMETER_STRUCT(FSceneTextureUniformParameters, SceneTextures)
END_GLOBAL_SHADER_PARAMETER_STRUCT()
IMPLEMENT_STATIC_UNIFORM_BUFFER_STRUCT(FGGYGOSignedFieldPassUniformParameters, "GGYGOSignedFieldPass", SceneTextures);

BEGIN_SHADER_PARAMETER_STRUCT(FGGYGOSignedFieldPassParameters, )
	SHADER_PARAMETER_STRUCT_INCLUDE(FViewShaderParameters, View)
	SHADER_PARAMETER_RDG_UNIFORM_BUFFER(FSceneUniformParameters, Scene)
	SHADER_PARAMETER_RDG_UNIFORM_BUFFER(FGGYGOSignedFieldPassUniformParameters, Pass)
	RENDER_TARGET_BINDING_SLOTS()
END_SHADER_PARAMETER_STRUCT()

EGGYGODistortionMaterialRole ReadCompiledRole(const FMaterialShaderMap* Map, FString& OutReason,
	uint32* OutRequiredSlots = nullptr)
{
	const bool bMapPresent = Map != nullptr;
	const bool bFinalized = Map && Map->IsCompilationFinalized();
	const bool bCompiledSuccessfully = Map && Map->CompiledSuccessfully();
	const bool bValidForRendering = Map && Map->IsValidForRendering(false);
	// ODSC 冻结快照的过程标记可为 false；调用方线程完整性及下列实际 shader 证书仍须通过。
	if (!bMapPresent || !bValidForRendering)
	{
		OutReason = FString::Printf(TEXT("原实际 shader map 缺失/不可渲染：Map=%d Finalized=%d CompiledSuccessfully=%d ValidForRendering=%d"),
			bMapPresent, bFinalized, bCompiledSuccessfully, bValidForRendering);
		return EGGYGODistortionMaterialRole::Unavailable;
	}
	FGGYGOSignedFieldRolePS::FPermutationDomain Normal, Field;
	Normal.Set<FGGYGOSignedFieldRolePS::FIsField>(false);
	Normal.Set<FGGYGOSignedFieldRolePS::FRequiredSlots>(0);
	Field.Set<FGGYGOSignedFieldRolePS::FIsField>(true);
	const bool bNormal = Map->GetShader<FGGYGOSignedFieldRolePS>(Normal).IsValid();
	uint32 FieldCertificates = 0, RequiredSlots = 0;
	for (uint32 Slots = 0; Slots < 16; ++Slots)
	{
		Field.Set<FGGYGOSignedFieldRolePS::FRequiredSlots>(Slots);
		if (Map->GetShader<FGGYGOSignedFieldRolePS>(Field).IsValid())
		{
			++FieldCertificates;
			RequiredSlots = Slots;
		}
	}
	if (FieldCertificates > 1)
	{
		OutReason = TEXT("实际map含相互冲突的field DP-slot编译合同");
		return EGGYGODistortionMaterialRole::Invalid;
	}
	const bool bField = FieldCertificates == 1;
	if (bNormal == bField)
	{
		OutReason = bNormal ? TEXT("实际map同时含互斥field角色") : TEXT("实际map缺少field角色编译证书");
		return bNormal ? EGGYGODistortionMaterialRole::Invalid : EGGYGODistortionMaterialRole::Unavailable;
	}
	OutReason.Reset();
	bool bHasCompletePair = false;
	for (const FVertexFactoryType* Factory : { &FGGYGOSignedFieldMeshVertexFactory::StaticType,
		&FGGYGOSignedFieldSpriteVertexFactory::StaticType, &FGGYGOSignedFieldCameraPositionVertexFactory::StaticType })
	{
		const FMeshMaterialShaderMap* MeshMap = Map->GetMeshShaderMap(Factory);
		if (!MeshMap || !MeshMap->HasShader(&FGGYGOSignedFieldVS::GetStaticType(), 0)) { continue; }
		FGGYGOSignedFieldPS::FPermutationDomain Half, Full;
		Half.Set<FGGYGOSignedFieldPS::FFloat32>(false);
		Full.Set<FGGYGOSignedFieldPS::FFloat32>(true);
		bHasCompletePair |= MeshMap->HasShader(&FGGYGOSignedFieldPS::GetStaticType(), Half.ToDimensionValueId())
			&& MeshMap->HasShader(&FGGYGOSignedFieldPS::GetStaticType(), Full.ToDimensionValueId());
	}
	if (bField && !bHasCompletePair)
	{
		OutReason = TEXT("实际map声明双场但缺少任一支持VF的完整VS/两精度PS");
		return EGGYGODistortionMaterialRole::Unavailable;
	}
	if (!bField && bHasCompletePair)
	{
		OutReason = TEXT("实际map的NoCustom证书与field shader互相矛盾");
		return EGGYGODistortionMaterialRole::Invalid;
	}
	if (OutRequiredSlots) { *OutRequiredSlots = RequiredSlots; }
	return bField ? EGGYGODistortionMaterialRole::DualSignedField : EGGYGODistortionMaterialRole::NoCustomField;
}

struct FPreparedDraw
{
	FGGYGOSignedFieldDraw Draw;
	const FMaterial* Material = nullptr;
	TMeshProcessorShaders<FGGYGOSignedFieldVS, FGGYGOSignedFieldPS> Shaders;
};

class FGGYGOSignedFieldMeshProcessor final : public FMeshPassProcessor
{
public:
	FGGYGOSignedFieldMeshProcessor(const FSceneView& View, FMeshPassDrawListContext* Context)
		: FMeshPassProcessor(EMeshPass::Num, View.Family->Scene->GetRenderScene(),
			View.GetFeatureLevel(), &View, Context)
	{
		State.SetBlendState(TStaticBlendState<
			CW_RGBA, BO_Add, BF_One, BF_One, BO_Add, BF_One, BF_One,
			CW_RGBA, BO_Add, BF_One, BF_One, BO_Add, BF_One, BF_One>::GetRHI());
		State.SetDepthStencilState(TStaticDepthStencilState<false, CF_DepthNearOrEqual>::GetRHI());
		State.SetDepthStencilAccess(FExclusiveDepthStencil::DepthRead_StencilNop);
	}
	virtual void AddMeshBatch(const FMeshBatch&, uint64, const FPrimitiveSceneProxy*, int32) override
	{
		checkNoEntry(); // 本processor只接收完成严格预检的同Graph批次。
	}
	void AddPrepared(const FPreparedDraw& Draw)
	{
		const FMeshBatch& Mesh = *Draw.Draw.Mesh;
		FMeshMaterialShaderElementData Data;
		Data.InitializeMeshMaterialData(ViewIfDynamicMeshCommand, Draw.Draw.Primitive, Mesh, INDEX_NONE, false);
		const FMeshDrawingPolicyOverrideSettings Overrides = ComputeMeshOverrideSettings(Mesh);
		BuildMeshDrawCommands(Mesh, ~uint64(0), Draw.Draw.Primitive, *Mesh.MaterialRenderProxy,
			*Draw.Material, State, Draw.Shaders, ComputeMeshFillMode(*Draw.Material, Overrides),
			ComputeMeshCullMode(*Draw.Material, Overrides),
			CalculateMeshStaticSortKey(Draw.Shaders.VertexShader, Draw.Shaders.PixelShader),
			EMeshPassFeatures::Default, Data);
	}
private:
	FMeshPassProcessorRenderState State;
};
}

EGGYGODistortionMaterialRole QueryGGYGOSignedFieldCompiledRole_GameThread(
	const FMaterial& Material, FString& OutReason)
{
	check(IsInGameThread());
	if (!Material.IsGameThreadShaderMapComplete())
	{
		OutReason = TEXT("原材质当前平台shader map不完整");
		return EGGYGODistortionMaterialRole::Unavailable;
	}
	return ReadCompiledRole(Material.GetGameThreadShaderMap(), OutReason);
}

bool AccumulateGGYGOSignedFields(FRDGBuilder& GraphBuilder, const FSceneView& View,
	TRDGUniformBufferRef<FSceneTextureUniformParameters> SceneTextures,
	FRDGTextureRef Depth, FIntRect ViewRect, const FGGYGODistortionViewPolicy& Policy,
	TConstArrayView<FGGYGOSignedFieldDraw> Draws, FGGYGOSignedFieldTextures& OutTextures, FString& OutReason)
{
	OutTextures = {};
	if (!SceneTextures || !Depth || !View.Family || !View.Family->Scene || View.IsInstancedStereo()
		|| Depth->Desc.Dimension != ETextureDimension::Texture2D || Depth->Desc.NumSamples != 1
		|| ViewRect.IsEmpty() || ViewRect.Min.X < 0 || ViewRect.Min.Y < 0
		|| ViewRect.Max.X > Depth->Desc.Extent.X || ViewRect.Max.Y > Depth->Desc.Extent.Y
		|| (Policy.Format != PF_FloatRGBA && Policy.Format != PF_A32B32G32R32F))
	{
		OutReason = TEXT("双场需要明确float RGBA格式、原单视图2D深度及有效ViewRect；不猜资源/降采样");
		return false;
	}
	if (Draws.IsEmpty()) { OutReason.Reset(); return true; } // 原粒子可见集为空，两张null表示无场，无假绘制。
	TArray<FPreparedDraw>* Prepared = GraphBuilder.AllocObject<TArray<FPreparedDraw>>();
	Prepared->Reserve(Draws.Num());
	FGGYGOSignedFieldPS::FPermutationDomain Precision;
	Precision.Set<FGGYGOSignedFieldPS::FFloat32>(Policy.Format == PF_A32B32G32R32F);
	for (const FGGYGOSignedFieldDraw& Draw : Draws)
	{
		const FMeshBatch* Mesh = Draw.Mesh;
		if (!Mesh || !Draw.Primitive || !Mesh->MaterialRenderProxy || !Mesh->VertexFactory
			|| !IsFieldFactory(Mesh->VertexFactory->GetType()) || Mesh->Elements.IsEmpty())
		{
			OutReason = TEXT("原批次/primitive/field VF输入无效");
			return false;
		}
		const FMaterial* Material = Mesh->MaterialRenderProxy->GetMaterialNoFallback(View.GetFeatureLevel());
		uint32 CompiledRequiredSlots = 0;
		if (!Material || !Material->IsRenderingThreadShaderMapComplete()
			|| ReadCompiledRole(Material->GetRenderingThreadShaderMap(), OutReason, &CompiledRequiredSlots) != EGGYGODistortionMaterialRole::DualSignedField)
		{
			if (OutReason.IsEmpty()) { OutReason = TEXT("实际field材质尚未就绪，未使用fallback"); }
			return false;
		}
		if (CompiledRequiredSlots != Draw.RequiredDynamicParameterSlots)
		{
			OutReason = TEXT("实际编译field材质的DP-slot合同与原renderer帧输入不一致");
			return false;
		}
		FPreparedDraw& Entry = Prepared->AddDefaulted_GetRef();
		Entry.Draw = Draw;
		Entry.Material = Material;
		Entry.Shaders.VertexShader = Material->GetShader<FGGYGOSignedFieldVS>(Mesh->VertexFactory->GetType(), 0, false);
		Entry.Shaders.PixelShader = Material->GetShader<FGGYGOSignedFieldPS>(Mesh->VertexFactory->GetType(), Precision, false);
		if (!Entry.Shaders.VertexShader.IsValid() || !Entry.Shaders.PixelShader.IsValid())
		{
			OutReason = TEXT("实际field VF/精度缺少完整VS与双MRT PS，不提交部分场");
			return false;
		}
	}
	const FRDGTextureDesc Desc = FRDGTextureDesc::Create2D(Depth->Desc.Extent, Policy.Format,
		FClearValueBinding::Transparent, TexCreate_RenderTargetable | TexCreate_ShaderResource);
	OutTextures.Default = GraphBuilder.CreateTexture(Desc, TEXT("GGYGO.SignedField.Default"));
	OutTextures.Overlay = GraphBuilder.CreateTexture(Desc, TEXT("GGYGO.SignedField.Overlay"));
	auto* Uniform = GraphBuilder.AllocParameters<FGGYGOSignedFieldPassUniformParameters>();
	Uniform->SceneTextures = *SceneTextures->GetContents();
	auto* Pass = GraphBuilder.AllocParameters<FGGYGOSignedFieldPassParameters>();
	Pass->View.View = View.ViewUniformBuffer;
	Pass->View.InstancedView = View.GetInstancedViewUniformBuffer();
	Pass->Scene = GetSceneUniformBufferRef(GraphBuilder, View);
	Pass->Pass = GraphBuilder.CreateUniformBuffer(Uniform);
	Pass->RenderTargets[0] = FRenderTargetBinding(OutTextures.Default, ERenderTargetLoadAction::EClear);
	Pass->RenderTargets[1] = FRenderTargetBinding(OutTextures.Overlay, ERenderTargetLoadAction::EClear);
	Pass->RenderTargets.DepthStencil = FDepthStencilBinding(Depth, ERenderTargetLoadAction::ELoad,
		ERenderTargetLoadAction::ENoAction, FExclusiveDepthStencil::DepthRead_StencilNop);
	AddDrawDynamicMeshPass(GraphBuilder, RDG_EVENT_NAME("GGYGO Signed RGBA Fields"), Pass, View, ViewRect,
		[Prepared, &View](FDynamicPassMeshDrawListContext* Context)
	{
		FGGYGOSignedFieldMeshProcessor Processor(View, Context);
		for (const FPreparedDraw& Draw : *Prepared) { Processor.AddPrepared(Draw); }
	}, true);
	OutReason.Reset();
	return true;
}
#endif
