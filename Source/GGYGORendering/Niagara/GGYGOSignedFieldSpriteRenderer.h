/** @file GGYGOSignedFieldSpriteRenderer.h
 *  @brief 同一个原Niagara Sprite renderer在合法自有collector收集，输出只交当前双场。
 */
#pragma once

#include "CoreMinimal.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGOSignedFieldRendererProperties.h"
#include "NiagaraRenderer.h"

class FGGYGOSignedFieldSpriteInputs;

class FGGYGOSignedFieldSpriteRenderer final : public FNiagaraRenderer
{
public:
	FGGYGOSignedFieldSpriteRenderer(ERHIFeatureLevel::Type FeatureLevel,
		const UGGYGOSignedFieldSpriteRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter);
	virtual ~FGGYGOSignedFieldSpriteRenderer() override;
	virtual void Initialize(const UNiagaraRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter,
		const FNiagaraSystemInstanceController& Controller) override;
	virtual FNiagaraDynamicDataBase* GenerateDynamicData(const FNiagaraSceneProxy* Primitive,
		const UNiagaraRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter) const override;
	virtual void CreateRenderThreadResources(FRHICommandListBase& RHICmdList) override;
	virtual void ReleaseRenderThreadResources() override;
	virtual void GetUsedMaterials(TArray<UMaterialInterface*>& Materials, bool bDebug) override;
	virtual void GetDynamicMeshElements(const TArray<const FSceneView*>& Views,
		const FSceneViewFamily& Family, uint32 VisibilityMap, FMeshElementCollector& Collector,
		const FNiagaraSceneProxy* Primitive) const override;
private:
	void ReportFailure(const FString& Reason) const;
	TUniquePtr<FGGYGOSignedFieldSpriteInputs> Inputs;
	const EGGYGOSignedFieldSpriteBasis Basis;
	const FString SourceName;
	// 与native renderer相同的Properties寿命；只消费原Finalize发布的RT layout，不另编绑定。
	const FNiagaraRendererLayout* FieldLayout;
	const uint32 RequiredComponents;
	const uint32 NativeValidComponents;
	mutable FCriticalSection FailureMutex;
	mutable FString LastFailure;
};
#endif
