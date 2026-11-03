/** @file GGYGOSignedFieldCollector.h
 *  @brief 合法自有collector接收原Sprite renderer的一次原帧收集，资源归原one-frame寿命。
 */
#pragma once

#include "CoreMinimal.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "MeshElementCollector.h"
#include "SceneManagement.h"

/** 只收集无PrimitiveIdStream的Sprite批次；不借用或伪造GPUScene collector。 */
class FGGYGOSignedFieldCollector final : public FOneFrameResource
{
public:
	FGGYGOSignedFieldCollector(ERHIFeatureLevel::Type FeatureLevel,
		const TArray<const FSceneView*>& Views, FMeshElementCollector& Original,
		const FPrimitiveSceneProxy& Primitive);
	virtual ~FGGYGOSignedFieldCollector() override;
	FMeshElementCollector& GetCollector();
	void Finish();
	TConstArrayView<FMeshBatchAndRelevance> GetMeshes(int32 ViewIndex) const;
private:
	class FCollector;
	// 先声明资源allocator，后销毁Collector；VF/UMaterial代理直至原Graph执行后才归还。
	FSceneRenderingBulkObjectAllocator Resources;
	TUniquePtr<FCollector> Collector;
};
#endif
