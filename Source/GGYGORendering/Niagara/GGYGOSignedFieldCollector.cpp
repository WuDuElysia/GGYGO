/** @file GGYGOSignedFieldCollector.cpp
 *  @brief 使用公开protected初始化接口建立自有收集上下文，不读原collector内部数组。
 */
#include "GGYGOSignedFieldCollector.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "PrimitiveSceneProxy.h"

class FGGYGOSignedFieldCollector::FCollector final : public FMeshElementCollector
{
public:
	struct FViewMeshes
	{
		TArray<FMeshBatchAndRelevance, SceneRenderingAllocator> Meshes;
		FSimpleElementCollector SimpleElements;
	};
	FCollector(ERHIFeatureLevel::Type FeatureLevel, FSceneRenderingBulkObjectAllocator& Resources,
		const TArray<const FSceneView*>& Views, FMeshElementCollector& Original,
		const FPrimitiveSceneProxy& Primitive)
		: FMeshElementCollector(FeatureLevel, Resources)
	{
		// 共享原生并发动态buffer；本collector的Finish仅提交材质/GPUScene记录，
		// buffer仍由原生收集context在全部任务归还后统一Commit。
		Start(Original.GetRHICommandList(), Original.GetDynamicVertexBuffer(),
			Original.GetDynamicIndexBuffer(), Original.GetDynamicReadBuffer());
		SetPrimitive(&Primitive, FHitProxyId());
		for (const FSceneView* View : Views)
		{
			TUniquePtr<FViewMeshes> Storage = MakeUnique<FViewMeshes>();
			AddViewMeshArrays(View, &Storage->Meshes, &Storage->SimpleElements, nullptr);
			ViewMeshes.Add(MoveTemp(Storage));
		}
	}
	void FinishCollection()
	{
		check(!bFinished);
		Finish();
		bFinished = true;
	}
	TConstArrayView<FMeshBatchAndRelevance> GetMeshes(int32 ViewIndex) const
	{
		check(bFinished);
		return MakeArrayView(ViewMeshes[ViewIndex]->Meshes);
	}
private:
	TArray<TUniquePtr<FViewMeshes>> ViewMeshes;
	bool bFinished = false;
};

FGGYGOSignedFieldCollector::FGGYGOSignedFieldCollector(ERHIFeatureLevel::Type FeatureLevel,
	const TArray<const FSceneView*>& Views, FMeshElementCollector& Original,
	const FPrimitiveSceneProxy& Primitive)
	: Collector(MakeUnique<FCollector>(FeatureLevel, Resources, Views, Original, Primitive))
{
}

FGGYGOSignedFieldCollector::~FGGYGOSignedFieldCollector() = default;

FMeshElementCollector& FGGYGOSignedFieldCollector::GetCollector() { return *Collector; }
void FGGYGOSignedFieldCollector::Finish() { Collector->FinishCollection(); }
TConstArrayView<FMeshBatchAndRelevance> FGGYGOSignedFieldCollector::GetMeshes(int32 ViewIndex) const
{
	return Collector->GetMeshes(ViewIndex);
}
#endif
