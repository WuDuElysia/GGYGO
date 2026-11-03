/** @file GGYGOSignedFieldData.cpp
 *  @brief 将原GenerateDynamicData结果随原Niagara生命周期归还，不复制或推进模拟。
 */
#include "GGYGOSignedFieldData.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "Materials/MaterialInterface.h"
#include "NiagaraDataSet.h"

bool ValidateGGYGOSignedFieldDynamicParameters(uint32 RequiredComponents, uint32 NativeValidComponents,
	TConstArrayView<FNiagaraRendererVariableInfo> Variables, int32 FirstParameterIndex,
	const FNiagaraDataBuffer& Particles, FString& OutReason)
{
	if ((RequiredComponents & ~NativeValidComponents) != 0)
	{
		OutReason = TEXT("原Niagara编译channel mask未保留必需DP分量");
		return false;
	}
	for (int32 Parameter = 0; Parameter < 4; ++Parameter)
	{
		const uint32 Components = (RequiredComponents >> (Parameter * 4)) & 15u;
		if (!Components) { continue; }
		const int32 VariableIndex = FirstParameterIndex + Parameter;
		if (!Variables.IsValidIndex(VariableIndex))
		{
			OutReason = FString::Printf(TEXT("原VF layout缺少必需DP%d"), Parameter);
			return false;
		}
		const FNiagaraRendererVariableInfo& Variable = Variables[VariableIndex];
		const int32 Offset = Variable.GetRawDatasetOffset();
		const uint32 Stride = Variable.IsHalfType() ? Particles.GetHalfStride() : Particles.GetFloatStride();
		const uint32 ScalarBytes = Variable.IsHalfType() ? sizeof(FFloat16) : sizeof(float);
		const uint64 BufferBytes = Variable.IsHalfType() ? Particles.GetHalfBuffer().Num() : Particles.GetFloatBuffer().Num();
		for (int32 Component = 0; Component < 4; ++Component)
		{
			if ((Components & (1u << Component)) == 0) { continue; }
			// 共享同一原变量的layout项可合法ShouldUpload=false；数据仍由原项统一上传。
			if (Offset == INDEX_NONE || Variable.GetRawGPUOffset() == INDEX_NONE
				|| Variable.GetNumComponents() <= Component
				|| uint64(Stride) < uint64(Particles.GetNumInstances()) * ScalarBytes
				|| uint64(Offset + Component) * Stride + uint64(Particles.GetNumInstances()) * ScalarBytes > BufferBytes)
			{
				OutReason = FString::Printf(TEXT("当前原CPU buffer/VF绑定缺少必需DP%d.%d"), Parameter, Component);
				return false;
			}
		}
	}
	OutReason.Reset();
	return true;
}

FGGYGOSignedFieldDynamicData::FGGYGOSignedFieldDynamicData(const FNiagaraEmitterInstance* Emitter,
	TUniquePtr<FNiagaraDynamicDataBase> InNativeData, TConstArrayView<UMaterialInterface*> Materials)
	: FNiagaraDynamicDataBase(Emitter), NativeData(MoveTemp(InNativeData))
{
	check(NativeData);
	// 基类构造会取引用；实际帧数据只由原生对象保活，避免形成第二份数据权威。
	CPUParticleData = nullptr;
	ComputeDataBufferInterface = nullptr;
	SetMaterialRelevance(NativeData->GetMaterialRelevance());
	MaterialProxies.Reserve(Materials.Num());
	for (UMaterialInterface* Material : Materials)
	{
		MaterialProxies.Add(Material ? Material->GetRenderProxy() : nullptr);
	}
}

void FGGYGOSignedFieldDynamicData::ApplyMaterialOverride(int32 MaterialIndex, UMaterialInterface* Material)
{
	// 原Niagara对空override或越界索引不替换材质，保持同一原生暂态语义。
	if (!Material || !MaterialProxies.IsValidIndex(MaterialIndex)) { return; }
	NativeData->ApplyMaterialOverride(MaterialIndex, Material);
	MaterialProxies[MaterialIndex] = Material->GetRenderProxy();
}
#endif
