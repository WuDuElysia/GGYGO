/** @file GGYGOSignedFieldMeshRenderer.h
 *  @brief 由原Niagara调度驱动的CPU Mesh双场renderer，公开native helper只准备原帧输入。
 */
#pragma once

#include "CoreMinimal.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "NiagaraRenderer.h"

class UGGYGOSignedFieldMeshRendererProperties;
class FGGYGOSignedFieldMeshInputs;

class FGGYGOSignedFieldMeshRenderer final : public FNiagaraRenderer
{
public:
	FGGYGOSignedFieldMeshRenderer(ERHIFeatureLevel::Type FeatureLevel,
		const UGGYGOSignedFieldMeshRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter);
	virtual ~FGGYGOSignedFieldMeshRenderer() override;
	virtual void Initialize(const UNiagaraRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter,
		const FNiagaraSystemInstanceController& Controller) override;
	virtual FNiagaraDynamicDataBase* GenerateDynamicData(const FNiagaraSceneProxy* Primitive,
		const UNiagaraRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter) const override;
	virtual void GetDynamicMeshElements(const TArray<const FSceneView*>& Views,
		const FSceneViewFamily& Family, uint32 VisibilityMap, FMeshElementCollector& Collector,
		const FNiagaraSceneProxy* Primitive) const override;
	virtual void GetUsedMaterials(TArray<UMaterialInterface*>& Materials, bool bDebug) override;
	virtual void ReleaseRenderThreadResources() override;
private:
	TUniquePtr<FGGYGOSignedFieldMeshInputs> Inputs;
	bool bInputsReady = false;
};
#endif
