/** @file GGYGONiagaraMaterialBindings.h
 *  @brief 沿实际 Renderer 槽位与最终对象参数解析材质；不创建 Niagara 实例。
 */
#pragma once

#include "CoreMinimal.h"
#include "Materials/MaterialInterface.h"

class UNiagaraSystem;
class UMaterialInterface;
struct FNiagaraParameterStore;
class FVertexFactoryType;

struct FGGYGONiagaraMaterialBinding
{
	UMaterialInterface* Material = nullptr;
	const FVertexFactoryType* VertexFactory = nullptr;
	EMaterialUsage Usage = MATUSAGE_MAX;
	bool bDecal = false;
	FString Source;
};

bool ResolveGGYGONiagaraMaterialBindings(UNiagaraSystem& System, const FNiagaraParameterStore* ComponentOverrides,
	const TMap<FName, TObjectPtr<UObject>>* ExplicitOverrides, TArray<FGGYGONiagaraMaterialBinding>& OutBindings,
	bool& bPendingAssets, FString& OutError);
