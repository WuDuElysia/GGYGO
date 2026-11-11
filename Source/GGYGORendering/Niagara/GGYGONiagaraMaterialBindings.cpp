/** @file GGYGONiagaraMaterialBindings.cpp
 *  @brief 原 Niagara Mesh/Sprite/Ribbon/Decal 材质槽及对象覆盖解析。
 */
#include "Niagara/GGYGONiagaraMaterialBindings.h"

#include "Engine/StaticMesh.h"
#include "Materials/MaterialInstanceConstant.h"
#include "Materials/MaterialInterface.h"
#include "Niagara/GGYGOProjectedDecalRendererProperties.h"
#include "NiagaraDecalRendererProperties.h"
#include "NiagaraEmitter.h"
#include "NiagaraLightRendererProperties.h"
#include "NiagaraMeshRendererProperties.h"
#include "NiagaraParameterStore.h"
#include "NiagaraRibbonRendererProperties.h"
#include "NiagaraSpriteRendererProperties.h"
#include "NiagaraSystem.h"
#include "StaticMeshResources.h"

namespace
{
	struct FObjectBindings
	{
		const FNiagaraParameterStore& Defaults;
		const FNiagaraParameterStore* ComponentOverrides;
		const TMap<FName, TObjectPtr<UObject>>* ExplicitOverrides;

		UObject* Resolve(const FNiagaraVariableBase& Parameter, FString& Error) const
		{
			if (!Parameter.IsValid()) { return nullptr; }
			if (!Parameter.GetType().IsUObject())
			{
				Error = TEXT("最终绑定不是 UObject 参数：") + Parameter.GetName().ToString();
				return nullptr;
			}
			if (ExplicitOverrides)
			{
				if (const TObjectPtr<UObject>* Object = ExplicitOverrides->Find(Parameter.GetName()))
				{
					if (!IsValid(Object->Get())) { Error = TEXT("显式对象覆盖为空：") + Parameter.GetName().ToString(); }
					return Object->Get();
				}
			}
			for (const FNiagaraParameterStore* Store : { ComponentOverrides, &Defaults })
			{
				if (!Store) { continue; }
				if (const int32* Offset = Store->FindParameterOffset(Parameter))
				{
					UObject* Object = Store->GetUObject(*Offset);
					if (!IsValid(Object)) { Error = TEXT("已声明对象绑定尚未解析：") + Parameter.GetName().ToString(); }
					return Object;
				}
			}
			Error = TEXT("最终参数中缺少对象绑定：") + Parameter.GetName().ToString();
			return nullptr;
		}
	};

	bool ResolveMesh(const UNiagaraMeshRendererProperties& Renderer, const FObjectBindings& Objects,
		TArray<UMaterialInterface*>& Materials, bool& bPendingAssets, FString& Error)
	{
		// 动态 mesh array 需要实际实例/DI 输出；未激活准备阶段不取静态列表冒充其结果。
		if (Renderer.MeshesBinding.ResolvedParameter.IsValid())
		{
			Error = TEXT("动态 Meshes 数据接口未解析，不能用静态 Meshes 代替：")
				+ Renderer.MeshesBinding.ResolvedParameter.GetName().ToString();
			return false;
		}
		Renderer.ForEachMesh(nullptr, [](int32) {}, [&](const FNiagaraMeshRendererMeshProperties& Slot)
		{
			if (!Error.IsEmpty()) { return; }
			UStaticMesh* Mesh = Slot.Mesh;
			if (Slot.MeshParameterBinding.ResolvedParameter.IsValid())
			{
				Mesh = Cast<UStaticMesh>(Objects.Resolve(Slot.MeshParameterBinding.ResolvedParameter, Error));
			}
			if (!IsValid(Mesh))
			{
				if (Error.IsEmpty()) { Error = TEXT("实际 Mesh 槽为空或不是 StaticMesh"); }
				return;
			}
#if WITH_EDITOR
			if (Mesh->IsCompiling()) { bPendingAssets = true; return; }
#endif
			const FStaticMeshRenderData* RenderData = Mesh->GetRenderData();
			if (!RenderData) { Error = TEXT("实际 Mesh 缺少 RenderData：") + Mesh->GetPathName(); return; }
			// 原 FNiagaraRenderableStaticMesh 仅消费任一 LOD/Section 用到的槽，保留其原索引。
			TArray<int32> UsedSlots;
			for (const FStaticMeshLODResources& LOD : RenderData->LODResources)
			{
				for (const FStaticMeshSection& Section : LOD.Sections)
				{
					if (Section.MaterialIndex >= 0) { UsedSlots.AddUnique(Section.MaterialIndex); }
				}
			}
			UsedSlots.Sort();
			if (UsedSlots.IsEmpty()) { Error = TEXT("实际 Mesh 没有 Section 材质槽：") + Mesh->GetPathName(); return; }
			for (int32 Index : UsedSlots)
			{
				UMaterialInterface* Material = Mesh->GetMaterial(Index);
				// 原生先为有 Section 的空槽放默认材质再覆盖。此处直接解析最终覆盖，不借默认材质。
				if (Renderer.bOverrideMaterials && Renderer.OverrideMaterials.IsValidIndex(Index))
				{
					const FNiagaraMeshMaterialOverride& Override = Renderer.OverrideMaterials[Index];
					if (Override.UserParamBinding.Parameter.IsValid())
					{
						Material = Cast<UMaterialInterface>(Objects.Resolve(Override.UserParamBinding.Parameter, Error));
						if (!Material && Error.IsEmpty()) { Error = TEXT("材质对象绑定类型不符"); }
					}
					else if (Override.ExplicitMat) { Material = Override.ExplicitMat; }
				}
				if (!Error.IsEmpty()) { return; }
				for (const FNiagaraMeshMICOverride& Override : Renderer.MICOverrideMaterials)
				{
					if (Override.OriginalMaterial == Material) { Material = Override.ReplacementMaterial; break; }
				}
				if (!Material) { Error = FString::Printf(TEXT("实际 Mesh 最终材质槽 %d 为空：%s"), Index, *Mesh->GetPathName()); return; }
				Materials.AddUnique(Material);
			}
		});
		return Error.IsEmpty();
	}

	template<typename TRenderer>
	UMaterialInterface* ResolveSingle(const TRenderer& Renderer, const FNiagaraVariableBase& Parameter,
		const FObjectBindings& Objects, FString& Error)
	{
		if (Parameter.IsValid())
		{
			UMaterialInterface* Material = Cast<UMaterialInterface>(Objects.Resolve(Parameter, Error));
			if (!Material && Error.IsEmpty()) { Error = TEXT("材质对象绑定类型不符：") + Parameter.GetName().ToString(); }
			return Material;
		}
#if WITH_EDITORONLY_DATA
		if (Renderer.MICMaterial) { return Renderer.MICMaterial; }
#endif
		return Renderer.Material;
	}
}

bool ResolveGGYGONiagaraMaterialBindings(UNiagaraSystem& System, const FNiagaraParameterStore* ComponentOverrides,
	const TMap<FName, TObjectPtr<UObject>>* ExplicitOverrides, TArray<FGGYGONiagaraMaterialBinding>& OutBindings,
	bool& bPendingAssets, FString& OutError)
{
	const FObjectBindings Objects{ System.GetExposedParameters(), ComponentOverrides, ExplicitOverrides };
	for (const FNiagaraEmitterHandle& Handle : System.GetEmitterHandles())
	{
		if (!Handle.GetIsEnabled()) { continue; }
		const FVersionedNiagaraEmitterData* Data = Handle.GetEmitterData();
		if (!Data) { OutError = TEXT("启用 Emitter 缺少版本数据：") + Handle.GetName().ToString(); return false; }
		for (const UNiagaraRendererProperties* Renderer : Data->GetRenderers())
		{
			if (!IsValid(Renderer)) { OutError = TEXT("启用 Emitter 含无效 Renderer：") + Handle.GetName().ToString(); return false; }
			if (!Renderer->GetIsEnabled()) { continue; }
			if (Renderer->IsA<UNiagaraLightRendererProperties>()) { continue; } // 原 Light 明确不消费材质。
			FGGYGONiagaraMaterialBinding Binding;
			Binding.Source = FString::Printf(TEXT("NS=%s Emitter=%s Renderer=%s"), *System.GetPathName(),
				*Handle.GetName().ToString(), *Renderer->GetPathName());
			Binding.VertexFactory = Renderer->GetVertexFactoryType();
			TArray<UMaterialInterface*> Materials;
			FString Error;
			const UNiagaraDecalRendererProperties* Decal = Cast<UNiagaraDecalRendererProperties>(Renderer);
			if (const auto* Projected = Cast<UGGYGOProjectedDecalRendererProperties>(Renderer))
			{
				Decal = Projected->NativeDecal;
				if (!IsValid(Decal)) { Error = TEXT("Projected Decal 缺少原 NativeDecal"); }
			}
			if (const auto* Mesh = Cast<UNiagaraMeshRendererProperties>(Renderer))
			{
				Binding.Usage = MATUSAGE_NiagaraMeshParticles;
				ResolveMesh(*Mesh, Objects, Materials, bPendingAssets, Error);
			}
			else if (const auto* Sprite = Cast<UNiagaraSpriteRendererProperties>(Renderer))
			{
				Binding.Usage = MATUSAGE_NiagaraSprites;
				Materials.Add(ResolveSingle(*Sprite, Sprite->MaterialUserParamBinding.Parameter, Objects, Error));
			}
			else if (const auto* Ribbon = Cast<UNiagaraRibbonRendererProperties>(Renderer))
			{
				Binding.Usage = MATUSAGE_NiagaraRibbons;
				Materials.Add(ResolveSingle(*Ribbon, Ribbon->MaterialUserParamBinding.Parameter, Objects, Error));
			}
			else if (IsValid(Decal))
			{
				Binding.bDecal = true;
				Materials.Add(ResolveSingle(*Decal, Decal->MaterialParameterBinding.ResolvedParameter, Objects, Error));
			}
			else if (Error.IsEmpty()) { Error = TEXT("本准备接口无法解析此 Renderer 的最终材质，未使用默认集合"); }
			if (Error.IsEmpty() && !Binding.bDecal && !Binding.VertexFactory) { Error = TEXT("材质 Renderer 缺少原 VertexFactory 类型"); }
			if (Error.IsEmpty() && Materials.IsEmpty() && !bPendingAssets) { Error = TEXT("材质 Renderer 没有可解析的最终材质"); }
			for (UMaterialInterface* Material : Materials)
			{
				if (!IsValid(Material)) { Error = TEXT("最终材质为空"); break; }
				Binding.Material = Material;
				OutBindings.Add(Binding);
			}
			if (!Error.IsEmpty()) { OutError = Binding.Source + TEXT("：") + Error; return false; }
		}
	}
	return true;
}
