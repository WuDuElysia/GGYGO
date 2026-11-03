/** @file GGYGOSignedFieldVertexFactory.cpp
 *  @brief 用公开Niagara uniform和绑定接口建立项目VF类型，保原材质输入协议。
 */
#include "GGYGOSignedFieldVertexFactory.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "MeshDrawShaderBindings.h"
#include "MeshMaterialShader.h"
#include "NiagaraVertexFactory.h"
#include "ShaderCompilerCore.h"

class FGGYGOSignedFieldMeshParameters final : public FNiagaraVertexFactoryShaderParametersBase
{
	DECLARE_TYPE_LAYOUT(FGGYGOSignedFieldMeshParameters, NonVirtual);
public:
	void GetElementShaderBindings(const FSceneInterface* Scene, const FSceneView* View,
		const FMeshMaterialShader* Shader, EVertexInputStreamType StreamType,
		ERHIFeatureLevel::Type FeatureLevel, const FVertexFactory* Factory,
		const FMeshBatchElement& Element, FMeshDrawSingleShaderBindings& Bindings,
		FVertexInputStreamArray& Streams) const
	{
		FNiagaraVertexFactoryShaderParametersBase::GetElementShaderBindings(
			Scene, View, Shader, StreamType, FeatureLevel, Factory, Element, Bindings, Streams);
		const auto* MeshFactory = static_cast<const FNiagaraMeshVertexFactory*>(Factory);
		Bindings.Add(Shader->GetUniformBufferParameter<FNiagaraMeshUniformParameters>(),
			MeshFactory->GetUniformBuffer());
	}
};
IMPLEMENT_TYPE_LAYOUT(FGGYGOSignedFieldMeshParameters);

class FGGYGOSignedFieldSpriteParametersVS final : public FNiagaraVertexFactoryShaderParametersBase
{
	DECLARE_TYPE_LAYOUT(FGGYGOSignedFieldSpriteParametersVS, NonVirtual);
public:
	void GetElementShaderBindings(const FSceneInterface* Scene, const FSceneView* View,
		const FMeshMaterialShader* Shader, EVertexInputStreamType StreamType,
		ERHIFeatureLevel::Type FeatureLevel, const FVertexFactory* Factory,
		const FMeshBatchElement& Element, FMeshDrawSingleShaderBindings& Bindings,
		FVertexInputStreamArray& Streams) const
	{
		FNiagaraVertexFactoryShaderParametersBase::GetElementShaderBindings(
			Scene, View, Shader, StreamType, FeatureLevel, Factory, Element, Bindings, Streams);
		const auto* SpriteFactory = static_cast<const FNiagaraSpriteVertexFactory*>(Factory);
		Bindings.Add(Shader->GetUniformBufferParameter<FNiagaraSpriteUniformParameters>(),
			SpriteFactory->GetSpriteUniformBuffer());
		Bindings.Add(Shader->GetUniformBufferParameter<FNiagaraSpriteVFLooseParameters>(),
			SpriteFactory->GetLooseParameterUniformBuffer());
	}
};
IMPLEMENT_TYPE_LAYOUT(FGGYGOSignedFieldSpriteParametersVS);

class FGGYGOSignedFieldSpriteParametersPS final : public FNiagaraVertexFactoryShaderParametersBase
{
	DECLARE_TYPE_LAYOUT(FGGYGOSignedFieldSpriteParametersPS, NonVirtual);
public:
	void GetElementShaderBindings(const FSceneInterface* Scene, const FSceneView* View,
		const FMeshMaterialShader* Shader, EVertexInputStreamType StreamType,
		ERHIFeatureLevel::Type FeatureLevel, const FVertexFactory* Factory,
		const FMeshBatchElement& Element, FMeshDrawSingleShaderBindings& Bindings,
		FVertexInputStreamArray& Streams) const
	{
		FNiagaraVertexFactoryShaderParametersBase::GetElementShaderBindings(
			Scene, View, Shader, StreamType, FeatureLevel, Factory, Element, Bindings, Streams);
		const auto* SpriteFactory = static_cast<const FNiagaraSpriteVertexFactory*>(Factory);
		Bindings.Add(Shader->GetUniformBufferParameter<FNiagaraSpriteUniformParameters>(),
			SpriteFactory->GetSpriteUniformBuffer());
	}
};
IMPLEMENT_TYPE_LAYOUT(FGGYGOSignedFieldSpriteParametersPS);

void FGGYGOSignedFieldMeshVertexFactory::ModifyCompilationEnvironment(
	const FVertexFactoryShaderPermutationParameters& Parameters, FShaderCompilerEnvironment& Environment)
{
	FNiagaraMeshVertexFactory::ModifyCompilationEnvironment(Parameters, Environment);
	// 本类型明确使用CPU Niagara数据及原Primitive uniform；不更改引擎原VF能力。
	Environment.SetDefine(TEXT("NIAGARA_MESH_WITH_GPU_SCENE"), 0);
	Environment.SetDefine(TEXT("VF_SUPPORTS_PRIMITIVE_SCENE_DATA"), 0);
	Environment.SetDefine(TEXT("VF_REQUIRES_PER_INSTANCE_CUSTOM_DATA"), 0);
	Environment.SetDefine(TEXT("USE_INSTANCE_CULLING"), 0);
}

void FGGYGOSignedFieldMeshVertexFactory::GetPSOPrecacheVertexFetchElements(
	EVertexInputStreamType StreamType, FVertexDeclarationElementList& Elements)
{
	FNiagaraMeshVertexFactory::GetPSOPrecacheVertexFetchElements(StreamType, Elements);
	Elements.RemoveAll([](const FVertexElement& Element) { return Element.AttributeIndex == 13; });
}

IMPLEMENT_VERTEX_FACTORY_PARAMETER_TYPE(FGGYGOSignedFieldMeshVertexFactory, SF_Vertex, FGGYGOSignedFieldMeshParameters);
IMPLEMENT_VERTEX_FACTORY_PARAMETER_TYPE(FGGYGOSignedFieldMeshVertexFactory, SF_Pixel, FGGYGOSignedFieldMeshParameters);
IMPLEMENT_VERTEX_FACTORY_TYPE(FGGYGOSignedFieldMeshVertexFactory,
	"/Plugin/FX/Niagara/Private/NiagaraMeshVertexFactory.ush",
	EVertexFactoryFlags::UsedWithMaterials | EVertexFactoryFlags::SupportsDynamicLighting
	| EVertexFactoryFlags::SupportsManualVertexFetch | EVertexFactoryFlags::SupportsPSOPrecaching);

IMPLEMENT_VERTEX_FACTORY_PARAMETER_TYPE(FGGYGOSignedFieldSpriteVertexFactory, SF_Vertex, FGGYGOSignedFieldSpriteParametersVS);
IMPLEMENT_VERTEX_FACTORY_PARAMETER_TYPE(FGGYGOSignedFieldSpriteVertexFactory, SF_Pixel, FGGYGOSignedFieldSpriteParametersPS);
IMPLEMENT_VERTEX_FACTORY_TYPE(FGGYGOSignedFieldSpriteVertexFactory,
	"/Plugin/FX/Niagara/Private/NiagaraSpriteVertexFactory.ush",
	EVertexFactoryFlags::UsedWithMaterials | EVertexFactoryFlags::SupportsDynamicLighting);

IMPLEMENT_VERTEX_FACTORY_PARAMETER_TYPE(FGGYGOSignedFieldCameraPositionVertexFactory, SF_Vertex, FGGYGOSignedFieldSpriteParametersVS);
IMPLEMENT_VERTEX_FACTORY_PARAMETER_TYPE(FGGYGOSignedFieldCameraPositionVertexFactory, SF_Pixel, FGGYGOSignedFieldSpriteParametersPS);
IMPLEMENT_VERTEX_FACTORY_TYPE(FGGYGOSignedFieldCameraPositionVertexFactory,
	"/GGYGORendering/Private/GGYGOSignedFieldCameraPositionVertexFactory.ush",
	EVertexFactoryFlags::UsedWithMaterials | EVertexFactoryFlags::SupportsDynamicLighting);
#endif
