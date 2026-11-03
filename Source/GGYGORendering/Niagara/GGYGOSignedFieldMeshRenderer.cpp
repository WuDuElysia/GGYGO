/** @file GGYGOSignedFieldMeshRenderer.cpp
 *  @brief 公开protected Niagara Mesh输入准备与自有VF/MeshBatch；不读取native私有动态数据布局。
 */
#include "GGYGOSignedFieldMeshRenderer.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGOSignedFieldData.h"
#include "GGYGOSignedFieldRendererProperties.h"
#include "GGYGOSignedFieldVertexFactory.h"
#include "Distortion/GGYGOSignedFieldFamily.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "NiagaraDataSet.h"
#include "NiagaraEmitterInstance.h"
#include "NiagaraGPUSortInfo.h"
#include "NiagaraRenderableMeshInterface.h"
#include "NiagaraRendererMeshes.h"
#include "NiagaraSceneProxy.h"
#include "StaticMeshResources.h"

DEFINE_LOG_CATEGORY_STATIC(LogGGYGOSignedFieldMesh, Log, All);

namespace
{
class FMeshFactoryResource final : public FOneFrameResource
{
public:
	FMeshFactoryResource(ERHIFeatureLevel::Type FeatureLevel, FNiagaraRenderableMeshPtr InMesh)
		: Factory(FeatureLevel), Mesh(MoveTemp(InMesh)) {}
	virtual ~FMeshFactoryResource() override { Factory.ReleaseResource(); }
	FGGYGOSignedFieldMeshVertexFactory Factory;
	FNiagaraRenderableMeshPtr Mesh;
};
}

/** 此对象不登记至系统，也不接收GDME/SetDynamicData；只调用公开原帧生产/输入准备。
 *  原FNiagaraRendererMeshes的final ray tracing方法因此不会把项目封装当作其私有数据。
 */
class FGGYGOSignedFieldMeshInputs final : public FNiagaraRendererMeshes
{
public:
	FGGYGOSignedFieldMeshInputs(ERHIFeatureLevel::Type FeatureLevel,
		const UGGYGOSignedFieldMeshRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter)
		: FNiagaraRendererMeshes(FeatureLevel, Properties, Emitter), SourceName(Properties->GetPathName()),
		RequiredComponents(uint32(Properties->FieldStreams.RequiredDynamicParameterComponents)),
		NativeValidComponents(Properties->MaterialParamValidMask) {}

	bool InitializeField(const UGGYGOSignedFieldMeshRendererProperties* Properties,
		const FNiagaraEmitterInstance* Emitter, const FNiagaraSystemInstanceController& Controller)
	{
		FNiagaraRendererMeshes::Initialize(Properties, Emitter, Controller);
		// 原helper按native GPUScene能力决定是否过滤；项目VF不用GPUScene，
		// 因此按同一编译数据的公开绑定恢复必需的CPU MeshIndex/visibility过滤。
		const FNiagaraDataSet& ParticleData = Emitter->GetParticleData();
		bNeedsParticleSelection = false;
		for (const FNiagaraVariableAttributeBinding* Binding : { &Properties->MeshIndexBinding, &Properties->RendererVisibilityTagBinding })
		{
			int32 FloatOffset, IntOffset, HalfOffset;
			if (!Binding->CanBindToHostParameterMap()
				&& ParticleData.GetVariableComponentOffsets(Binding->GetDataSetBindableVariable(), FloatOffset, IntOffset, HalfOffset))
			{
				bNeedsParticleSelection |= IntOffset != INDEX_NONE;
			}
		}
		FieldMeshes.Reset();
		bool bValid = true;
		uint32 SourceIndex = 0;
		Properties->ForEachMesh(Emitter->GetParentSystemInstance(),
			[this](int32 Count) { FieldMeshes.Reserve(Count); },
			[&](const FNiagaraMeshRendererMeshProperties& Source)
		{
			FNiagaraRenderableMeshPtr Mesh = Source.ResolveRenderableMesh(Emitter);
			if (!Mesh || Source.LODMode != ENiagaraMeshLODMode::LODLevel)
			{
				bValid = false;
				++SourceIndex;
				return;
			}
			FMeshData& Data = FieldMeshes.AddDefaulted_GetRef();
			Data.RenderableMesh = MoveTemp(Mesh);
			Data.SourceMeshIndex = SourceIndex++;
			Data.LODMode = Source.LODMode;
			Data.LODLevel = Source.LODLevel;
			Data.PivotOffset = FVector3f(Source.PivotOffset);
			Data.PivotOffsetSpace = Source.PivotOffsetSpace;
			Data.Scale = FVector3f(Source.Scale);
			Data.Rotation = FQuat4f(Source.Rotation.Quaternion());
			TArray<UMaterialInterface*> Materials;
			Data.RenderableMesh->GetUsedMaterials(Materials);
			Properties->ApplyMaterialOverrides(Emitter, Materials);
			for (UMaterialInterface* Material : Materials)
			{
				const int32 Index = BaseMaterials_GT.IndexOfByPredicate([Material](UMaterialInterface* Candidate)
				{
					if (Candidate == Material) { return true; }
					const UMaterialInstanceDynamic* Dynamic = Cast<UMaterialInstanceDynamic>(Candidate);
					return Dynamic && Dynamic->Parent == Material;
				});
				bValid &= Index != INDEX_NONE;
				Data.MaterialRemapTable.Add(Index);
			}
		});
		if (!bValid || FieldMeshes.IsEmpty())
		{
			ReportFailure(TEXT("原Mesh/固定LOD或实际材质remap无效；未生成替代模型/材质"));
			return false;
		}
		return true;
	}

	TConstArrayView<UMaterialInterface*> GetMaterials_GameThread() const
	{
		check(IsInGameThread() || IsInParallelGameThread());
		return MakeArrayView(BaseMaterials_GT);
	}

	void Collect(const TArray<const FSceneView*>& Views, const FSceneViewFamily& Family,
		uint32 VisibilityMap, FMeshElementCollector& Collector, const FNiagaraSceneProxy& Primitive,
		const FGGYGOSignedFieldDynamicData& Data) const
	{
		const FGGYGOSignedFieldFamily* Fields = Family.GetExtentionData<FGGYGOSignedFieldFamily>();
		if (!Fields) { ReportFailure(TEXT("原family未冻结field登记")); return; }
		auto Reject = [&](const FString& Reason)
		{
			Fields->RejectVisibleViews(Views, VisibilityMap, Reason);
			ReportFailure(Reason);
		};
		FParticleMeshRenderData Particles;
		PrepareParticleMeshRenderData(Collector.GetRHICommandList(), Particles, Family, Collector,
			Data.NativeData.Get(), &Primitive, false, ENiagaraGpuComputeTickStage::Last);
		if (!Particles.SourceParticleData) { return; }
		FString Reason;
		if (!Particles.RendererLayout || !ValidateGGYGOSignedFieldDynamicParameters(RequiredComponents,
			NativeValidComponents, Particles.RendererLayout->GetVFVariables_RenderThread(),
			ENiagaraMeshVFLayout::DynamicParam0, *Particles.SourceParticleData, Reason))
		{
			Reject(Reason.IsEmpty() ? TEXT("原Mesh VF layout尚未就绪") : Reason);
			return;
		}
		// 项目VF固定CPU手工实例数据，原SDK的native mesh GPUScene路径仍保持其自身配置。
		Particles.bUseGPUScene = false;
		Particles.bNeedsCull = bNeedsParticleSelection;
		Particles.bSortCullOnGpu = false;
		if (!CalculateMeshUsed(Collector.GetRHICommandList(), Particles)) { return; }
		PrepareParticleRenderBuffers(Collector.GetRHICommandList(), Particles, Collector.GetDynamicReadBuffer());
		for (int32 ViewIndex = 0; ViewIndex < Views.Num(); ++ViewIndex)
		{
			const FSceneView& View = *Views[ViewIndex];
			if ((VisibilityMap & (1u << ViewIndex)) == 0 || View.GetDynamicMeshElementsShadowCullFrustum()) { continue; }
			FNiagaraGPUSortInfo SortInfo;
			if (Particles.bNeedsSort || Particles.bNeedsCull)
			{
				InitializeSortInfo(Particles, Primitive, View, ViewIndex, false, SortInfo);
			}
			for (const FMeshData& Mesh : FieldMeshes)
			{
				if (Particles.bAllowFirstMeshOnly && Mesh.SourceMeshIndex > 0) { break; }
				if (Particles.MeshUsed.Num())
				{
					if (!Particles.MeshUsed.IsValidIndex(Mesh.SourceMeshIndex))
					{
						Reject(TEXT("原Mesh可见表与固定配置的source index不一致"));
						return;
					}
					if (!Particles.MeshUsed[Mesh.SourceMeshIndex]) { continue; }
				}
				INiagaraRenderableMesh::FLODModelData LOD;
				Mesh.RenderableMesh->GetLODModelData(LOD, Mesh.LODLevel);
				if (LOD.LODIndex == INDEX_NONE)
				{
					Reject(TEXT("原Mesh固定LOD尚未就绪，等待原资源，不换模型"));
					return;
				}
				FMeshFactoryResource& Resource = Collector.AllocateOneFrameResource<FMeshFactoryResource>(FeatureLevel, Mesh.RenderableMesh);
				Resource.Factory.InitResource(Collector.GetRHICommandList());
				Mesh.RenderableMesh->SetupVertexFactory(Collector.GetRHICommandList(), Resource.Factory, LOD);
				PreparePerMeshData(Particles, Resource.Factory, Primitive, Mesh);
				const uint32 Count = PerformSortAndCull(Collector.GetRHICommandList(), Particles,
					Collector.GetDynamicReadBuffer(), SortInfo, Primitive.GetComputeDispatchInterface(), View, Mesh);
				if (!Count) { continue; }
				FNiagaraMeshCommonParameters Parameters = CreateCommonShaderParams(Particles, View, Mesh, Primitive);
				Resource.Factory.SetUniformBuffer(CreateVFUniformBuffer(Particles, Parameters));
				for (const FStaticMeshSection& Section : LOD.Sections)
				{
					if (!Section.NumTriangles) { continue; }
					const int32 MaterialIndex = Mesh.MaterialRemapTable.IsValidIndex(Section.MaterialIndex)
						? int32(Mesh.MaterialRemapTable[Section.MaterialIndex]) : INDEX_NONE;
					FMaterialRenderProxy* Material = Data.MaterialProxies.IsValidIndex(MaterialIndex)
						? Data.MaterialProxies[MaterialIndex] : nullptr;
					if (!Material)
					{
						Reject(TEXT("实际Mesh section缺少原field材质，不使用默认材质"));
						return;
					}
					const uint32 CountOffset = SortInfo.CulledGPUParticleCountOffset != INDEX_NONE
						? SortInfo.CulledGPUParticleCountOffset : Particles.SourceParticleData->GetGPUInstanceCountBufferOffset();
					FMeshBatch& Batch = Collector.AllocateMesh();
					CreateMeshBatchForSection(Collector.GetRHICommandList(), Particles, Parameters, Batch,
						Resource.Factory, *Material, Primitive, Mesh, LOD, Section, View, ViewIndex,
						Count, CountOffset, false, false, false);
					if (!Fields->Submit(View, Primitive, Batch, RequiredComponents, Reason)) { Reject(Reason); return; }
				}
			}
		}
	}
private:
	void ReportFailure(const FString& Reason) const
	{
		FScopeLock Lock(&FailureMutex);
		if (Reason != LastFailure)
		{
			UE_LOG(LogGGYGOSignedFieldMesh, Warning, TEXT("%s 未提交field：%s"), *SourceName, *Reason);
			LastFailure = Reason;
		}
	}
	// 来源为同次Initialize公开Mesh配置；固定LOD/材质索引用于项目收集，不读取native私有Meshes。
	TArray<FMeshData> FieldMeshes;
	const FString SourceName;
	const uint32 RequiredComponents;
	const uint32 NativeValidComponents;
	// 同次Initialize的原编译layout派生量，原renderer重建时失效；不持有粒子选择结果。
	bool bNeedsParticleSelection = false;
	mutable FCriticalSection FailureMutex;
	mutable FString LastFailure;
};

FGGYGOSignedFieldMeshRenderer::FGGYGOSignedFieldMeshRenderer(ERHIFeatureLevel::Type InFeatureLevel,
	const UGGYGOSignedFieldMeshRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter)
	: FNiagaraRenderer(InFeatureLevel, Properties, Emitter),
	Inputs(MakeUnique<FGGYGOSignedFieldMeshInputs>(InFeatureLevel, Properties, Emitter))
{
	// 本owner只向只读主深度的field pass提交，不进入原secondary depth pass。
	// 材质初始化由Inputs唯一执行，不能另调base Initialize再生成一组native MID。
	bRendersInSecondaryDepthPass = false;
}

FGGYGOSignedFieldMeshRenderer::~FGGYGOSignedFieldMeshRenderer() = default;

void FGGYGOSignedFieldMeshRenderer::Initialize(const UNiagaraRendererProperties* Properties,
	const FNiagaraEmitterInstance* Emitter, const FNiagaraSystemInstanceController& Controller)
{
	bInputsReady = Inputs->InitializeField(CastChecked<UGGYGOSignedFieldMeshRendererProperties>(Properties), Emitter, Controller);
}

FNiagaraDynamicDataBase* FGGYGOSignedFieldMeshRenderer::GenerateDynamicData(const FNiagaraSceneProxy* Primitive,
	const UNiagaraRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter) const
{
	if (!bInputsReady) { return nullptr; }
	TUniquePtr<FNiagaraDynamicDataBase> Native(Inputs->GenerateDynamicData(Primitive, Properties, Emitter));
	return Native ? new FGGYGOSignedFieldDynamicData(Emitter, MoveTemp(Native), Inputs->GetMaterials_GameThread()) : nullptr;
}

void FGGYGOSignedFieldMeshRenderer::GetDynamicMeshElements(const TArray<const FSceneView*>& Views,
	const FSceneViewFamily& Family, uint32 VisibilityMap, FMeshElementCollector& Collector,
	const FNiagaraSceneProxy* Primitive) const
{
	if (DynamicDataRender)
	{
		Inputs->Collect(Views, Family, VisibilityMap, Collector, *Primitive,
			*static_cast<const FGGYGOSignedFieldDynamicData*>(DynamicDataRender));
	}
}

void FGGYGOSignedFieldMeshRenderer::GetUsedMaterials(TArray<UMaterialInterface*>& Materials, bool bDebug)
{
	Inputs->GetUsedMaterials(Materials, bDebug);
}

void FGGYGOSignedFieldMeshRenderer::ReleaseRenderThreadResources() { Inputs->ReleaseRenderThreadResources(); }
#endif
