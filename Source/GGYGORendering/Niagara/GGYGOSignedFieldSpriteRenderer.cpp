/** @file GGYGOSignedFieldSpriteRenderer.cpp
 *  @brief 保留原Sprite模拟、动态数据及全部变量绑定，不向普通颜色pass提交field。
 */
#include "GGYGOSignedFieldSpriteRenderer.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGOSignedFieldCollector.h"
#include "GGYGOSignedFieldData.h"
#include "GGYGOSignedFieldVertexFactory.h"
#include "Distortion/GGYGOSignedFieldFamily.h"
#include "NiagaraSceneProxy.h"
#include "NiagaraDataSet.h"
#include "NiagaraRendererSprites.h"

DEFINE_LOG_CATEGORY_STATIC(LogGGYGOSignedFieldSprite, Log, All);

namespace
{
/** 只持有原UB引用和项目VF，原粒子buffer、排序及indirect args仍属原Niagara帧。 */
class FSpriteFactoryResource final : public FOneFrameResource
{
public:
	FSpriteFactoryResource(ERHIFeatureLevel::Type FeatureLevel, bool bCameraPosition)
	{
		if (bCameraPosition) { Factory = MakeUnique<FGGYGOSignedFieldCameraPositionVertexFactory>(FeatureLevel); }
		else { Factory = MakeUnique<FGGYGOSignedFieldSpriteVertexFactory>(FeatureLevel); }
	}
	virtual ~FSpriteFactoryResource() override { Factory->ReleaseResource(); }
	TUniquePtr<FNiagaraSpriteVertexFactory> Factory;
};
}

/** 不登记为系统renderer，避免原final ray tracing提交另一路几何；原动态数据始终由owner封装持有。 */
class FGGYGOSignedFieldSpriteInputs final : public FNiagaraRendererSprites
{
public:
	FGGYGOSignedFieldSpriteInputs(ERHIFeatureLevel::Type FeatureLevel,
		const UGGYGOSignedFieldSpriteRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter)
		: FNiagaraRendererSprites(FeatureLevel, Properties, Emitter) {}

	TConstArrayView<UMaterialInterface*> GetMaterials_GameThread() const
	{
		check(IsInGameThread() || IsInParallelGameThread());
		return MakeArrayView(BaseMaterials_GT);
	}

	void Collect(const TArray<const FSceneView*>& Views, const FSceneViewFamily& Family,
		uint32 VisibilityMap, FMeshElementCollector& Collector, const FNiagaraSceneProxy* Primitive,
		FNiagaraDynamicDataBase* Frame)
	{
		// native Sprite未公开带Frame参数的几何helper；在本自有辅助对象的protected接缝
		// 临时借用原生对象。并行view串行借用，离开调用即还原，不调用SetDynamicData取得所有权。
		FScopeLock Lock(&CollectionMutex);
		check(!DynamicDataRender);
		TGuardValue<FNiagaraDynamicDataBase*> BorrowFrame(DynamicDataRender, Frame);
		FNiagaraRendererSprites::GetDynamicMeshElements(Views, Family, VisibilityMap, Collector, Primitive);
	}
private:
	FCriticalSection CollectionMutex;
};

FGGYGOSignedFieldSpriteRenderer::FGGYGOSignedFieldSpriteRenderer(ERHIFeatureLevel::Type InFeatureLevel,
	const UGGYGOSignedFieldSpriteRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter)
	: FNiagaraRenderer(InFeatureLevel, Properties, Emitter),
	Inputs(MakeUnique<FGGYGOSignedFieldSpriteInputs>(InFeatureLevel, Properties, Emitter)), Basis(Properties->FieldBasis),
	SourceName(Properties->GetPathName()), FieldLayout(&Properties->RendererLayoutWithoutCustomSort),
	RequiredComponents(uint32(Properties->FieldStreams.RequiredDynamicParameterComponents)),
	NativeValidComponents(Properties->MaterialParamValidMask)
{
	bRendersInSecondaryDepthPass = false;
}

FGGYGOSignedFieldSpriteRenderer::~FGGYGOSignedFieldSpriteRenderer() = default;

void FGGYGOSignedFieldSpriteRenderer::Initialize(const UNiagaraRendererProperties* Properties,
	const FNiagaraEmitterInstance* Emitter, const FNiagaraSystemInstanceController& Controller)
{
	Inputs->Initialize(Properties, Emitter, Controller);
}

FNiagaraDynamicDataBase* FGGYGOSignedFieldSpriteRenderer::GenerateDynamicData(const FNiagaraSceneProxy* Primitive,
	const UNiagaraRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter) const
{
	TUniquePtr<FNiagaraDynamicDataBase> Native(Inputs->GenerateDynamicData(Primitive, Properties, Emitter));
	return Native ? new FGGYGOSignedFieldDynamicData(Emitter, MoveTemp(Native), Inputs->GetMaterials_GameThread()) : nullptr;
}

void FGGYGOSignedFieldSpriteRenderer::CreateRenderThreadResources(FRHICommandListBase& RHICmdList)
{
	Inputs->CreateRenderThreadResources(RHICmdList);
}

void FGGYGOSignedFieldSpriteRenderer::ReleaseRenderThreadResources() { Inputs->ReleaseRenderThreadResources(); }

void FGGYGOSignedFieldSpriteRenderer::GetUsedMaterials(TArray<UMaterialInterface*>& Materials, bool bDebug)
{
	Inputs->GetUsedMaterials(Materials, bDebug);
}

void FGGYGOSignedFieldSpriteRenderer::GetDynamicMeshElements(const TArray<const FSceneView*>& Views,
	const FSceneViewFamily& Family, uint32 VisibilityMap, FMeshElementCollector& Collector,
	const FNiagaraSceneProxy* Primitive) const
{
	if (!HasDynamicData()) { return; } // 原系统完成/失活时的合法空帧。
	const FGGYGOSignedFieldFamily* Fields = Family.GetExtentionData<FGGYGOSignedFieldFamily>();
	if (!Fields)
	{
		ReportFailure(TEXT("原family没有冻结field登记；不转为普通颜色"));
		return;
	}
	auto Reject = [&](const FString& Reason)
	{
		Fields->RejectVisibleViews(Views, VisibilityMap, Reason);
		ReportFailure(Reason);
	};
	const auto* Data = static_cast<const FGGYGOSignedFieldDynamicData*>(GetDynamicData());
	// NativeData仍是原生Sprite类型；通过公开接口取同一被保活的CPU帧，不读取其私有布局。
	const FNiagaraDataBuffer* Particles = Data->NativeData->GetParticleDataToRender(Collector.GetRHICommandList());
	if (!Particles || Particles->GetNumInstances() == 0) { return; }
	FString Reason;
	if (!ValidateGGYGOSignedFieldDynamicParameters(RequiredComponents, NativeValidComponents,
		FieldLayout->GetVFVariables_RenderThread(), ENiagaraSpriteVFLayout::MaterialParam0, *Particles, Reason))
	{
		Reject(Reason);
		return;
	}
	FGGYGOSignedFieldCollector& NativeMeshes = Collector.AllocateOneFrameResource<FGGYGOSignedFieldCollector>(
		FeatureLevel, Views, Collector, *Primitive);
	// 这是本renderer收到的唯一原生GDME调用，不重新模拟或从SVE再次收集场景。
	Inputs->Collect(Views, Family, VisibilityMap, NativeMeshes.GetCollector(), Primitive, Data->NativeData.Get());
	NativeMeshes.Finish();
	for (int32 ViewIndex = 0; ViewIndex < Views.Num(); ++ViewIndex)
	{
		if ((VisibilityMap & (1u << ViewIndex)) == 0
			|| Views[ViewIndex]->GetDynamicMeshElementsShadowCullFrustum()) { continue; }
		for (const FMeshBatchAndRelevance& Native : NativeMeshes.GetMeshes(ViewIndex))
		{
			if (!Native.Mesh || !Native.Mesh->VertexFactory
				|| Native.Mesh->VertexFactory->GetType() != &FNiagaraSpriteVertexFactory::StaticType)
			{
				Reject(TEXT("原Sprite收集产生了不受支持的VF类型"));
				return;
			}
			const auto* NativeFactory = static_cast<const FNiagaraSpriteVertexFactory*>(Native.Mesh->VertexFactory);
			if (NativeFactory->GetCutoutParameters() != 0 || !NativeFactory->GetSpriteUniformBuffer()
				|| !NativeFactory->GetLooseParameterUniformBuffer())
			{
				Reject(TEXT("原完整quad/实际Sprite uniform尚未就绪，不生成替代几何"));
				return;
			}
			FSpriteFactoryResource& Resource = Collector.AllocateOneFrameResource<FSpriteFactoryResource>(
				FeatureLevel, Basis == EGGYGOSignedFieldSpriteBasis::CameraPositionWithViewRoll);
			Resource.Factory->InitResource(Collector.GetRHICommandList());
			Resource.Factory->SetSpriteUniformBuffer(FNiagaraSpriteUniformBufferRef(NativeFactory->GetSpriteUniformBuffer()));
			Resource.Factory->SetLooseParameterUniformBuffer(NativeFactory->GetLooseParameterUniformBuffer());
			Resource.Factory->SetFacingMode(NativeFactory->GetFacingMode());
			Resource.Factory->SetAlignmentMode(NativeFactory->GetAlignmentMode());
			FMeshBatch& Mesh = Collector.AllocateMesh();
			Mesh = *Native.Mesh;
			Mesh.VertexFactory = Resource.Factory.Get();
			if (!Fields->Submit(*Views[ViewIndex], *Primitive, Mesh, RequiredComponents, Reason))
			{
				Reject(Reason);
				return;
			}
		}
	}
}

void FGGYGOSignedFieldSpriteRenderer::ReportFailure(const FString& Reason) const
{
	FScopeLock Lock(&FailureMutex);
	if (Reason != LastFailure)
	{
		UE_LOG(LogGGYGOSignedFieldSprite, Warning, TEXT("%s 未提交field：%s"), *SourceName, *Reason);
		LastFailure = Reason;
	}
}
#endif
