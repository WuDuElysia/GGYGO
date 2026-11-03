/** @file GGYGOSignedFieldData.h
 *  @brief 原Niagara动态数据的所有权封装，附带同次生成的真实材质proxy。
 */
#pragma once

#include "CoreMinimal.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "NiagaraRenderer.h"

/** 只消费原编译layout和该帧CPU buffer；必需DP分量缺流时拒绝，不让native默认值掩盖来源。 */
bool ValidateGGYGOSignedFieldDynamicParameters(uint32 RequiredComponents, uint32 NativeValidComponents,
	TConstArrayView<FNiagaraRendererVariableInfo> Variables, int32 FirstParameterIndex,
	const FNiagaraDataBuffer& Particles, FString& OutReason);

/** 原系统通过SetDynamicData_RenderThread替换并销毁；不跨帧另存Emitter或模拟状态。 */
struct FGGYGOSignedFieldDynamicData final : public FNiagaraDynamicDataBase
{
	FGGYGOSignedFieldDynamicData(const FNiagaraEmitterInstance* Emitter,
		TUniquePtr<FNiagaraDynamicDataBase> InNativeData,
		TConstArrayView<UMaterialInterface*> Materials);
	virtual void ApplyMaterialOverride(int32 MaterialIndex, UMaterialInterface* Material) override;

	// NativeData唯一持有原CPU buffer引用及原参数快照；本封装只消费公开接口。
	TUniquePtr<FNiagaraDynamicDataBase> NativeData;
	TArray<FMaterialRenderProxy*> MaterialProxies;
};
#endif
