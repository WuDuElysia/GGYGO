/** @file GGYGOSignedFieldFamily.cpp
 *  @brief family配置及原Graph寿命内的mesh批次所有权，不新增时钟或世界登记表。
 */
#include "GGYGOSignedFieldFamily.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "Async/Async.h"
#include "Materials/MaterialInterface.h"
#include "MeshBatch.h"
#include "PrimitiveSceneProxy.h"
#include "RenderGraphBuilder.h"

const TCHAR* FGGYGOSignedFieldFamily::GSubclassIdentifier = TEXT("GGYGO.SignedFieldFamily");

FGGYGOSignedFieldSnapshot::FGGYGOSignedFieldSnapshot(TOptional<FGGYGODistortionViewPolicy> InPolicy,
	TArray<FGGYGOSignedFieldSource> InSources, const TArray<UMaterialInterface*>& InMaterials,
	FString InFailure)
	: Policy(MoveTemp(InPolicy)), Failure(MoveTemp(InFailure)), Sources(MoveTemp(InSources))
{
	check(IsInGameThread());
	for (UMaterialInterface* Material : InMaterials) { Materials.Emplace(Material); }
}

bool FGGYGOSignedFieldSnapshot::Accepts(const FPrimitiveSceneProxy& Primitive,
	const FMaterialRenderProxy* Material) const
{
	for (const FGGYGOSignedFieldSource& Source : Sources)
	{
		if (Source.Primitive == Primitive.GetPrimitiveComponentId() && Source.Materials.Contains(Material))
		{
			return true;
		}
	}
	return false;
}

TSharedPtr<const FGGYGOSignedFieldSnapshot, ESPMode::ThreadSafe> MakeGGYGOSignedFieldSnapshot(
	TOptional<FGGYGODistortionViewPolicy> Policy, TArray<FGGYGOSignedFieldSource> Sources,
	const TArray<UMaterialInterface*>& Materials, FString Failure)
{
	check(IsInGameThread());
	return MakeShareable(new FGGYGOSignedFieldSnapshot(MoveTemp(Policy), MoveTemp(Sources), Materials,
		MoveTemp(Failure)), [](FGGYGOSignedFieldSnapshot* Snapshot)
	{
		if (IsInGameThread()) { delete Snapshot; }
		else { AsyncTask(ENamedThreads::GameThread, [Snapshot]() { delete Snapshot; }); }
	});
}

void FGGYGOSignedFieldFamily::InitializeOnce(
	TSharedRef<const FGGYGOSignedFieldSnapshot, ESPMode::ThreadSafe> InSnapshot)
{
	check(IsInGameThread());
	if (!Snapshot) { Snapshot = MoveTemp(InSnapshot); }
}

const FGGYGODistortionViewPolicy* FGGYGOSignedFieldFamily::GetPolicy() const
{
	return Snapshot && Snapshot->Policy.IsSet() ? &Snapshot->Policy.GetValue() : nullptr;
}

void FGGYGOSignedFieldFamily::BeginView(FRDGBuilder& GraphBuilder, const FSceneView& View) const
{
	check(IsInRenderingThread());
	bool bNeedsReturnCallback = true;
	{
		FScopeLock Lock(&Mutex);
		for (const auto& Existing : Views)
		{
			if (Existing.Value.Graph == &GraphBuilder) { bNeedsReturnCallback = false; break; }
		}
		FViewDraws& Entry = Views.FindOrAdd(&View);
		checkf(!Entry.Graph || Entry.Graph == &GraphBuilder, TEXT("同一实际View不能同时归属两个field Graph"));
		Entry.Graph = &GraphBuilder;
	}
	// 原生Graph归还即释放本轮记录；不按帧号猜寿命，不复用前一帧collector资源。
	if (bNeedsReturnCallback)
	{
		GraphBuilder.AddPostExecuteCallback([FamilyData = AsShared(), Graph = &GraphBuilder]()
		{
			FamilyData->ReturnGraph(Graph);
		});
	}
}

bool FGGYGOSignedFieldFamily::Submit(const FSceneView& View, const FPrimitiveSceneProxy& Primitive,
	const FMeshBatch& Mesh, uint32 RequiredComponents, FString& OutReason) const
{
	if (!Snapshot || !Snapshot->Accepts(Primitive, Mesh.MaterialRenderProxy))
	{
		OutReason = TEXT("当前family没有原primitive与实际field材质的登记");
		return false;
	}
	FScopeLock Lock(&Mutex);
	FViewDraws* Entry = Views.Find(&View);
	if (!Entry || !Entry->Graph || Entry->bConsumed)
	{
		OutReason = TEXT("原View尚未进入Graph或已完成本轮field消费");
		return false;
	}
	if (!Entry->Failure.IsEmpty()) { OutReason = Entry->Failure; return false; }
	Entry->Draws.Add({ &Mesh, &Primitive, GetGGYGOSignedFieldDynamicParameterSlots(RequiredComponents) });
	OutReason.Reset();
	return true;
}

void FGGYGOSignedFieldFamily::RejectVisibleViews(const TArray<const FSceneView*>& InViews,
	uint32 VisibilityMap, const FString& Reason) const
{
	FScopeLock Lock(&Mutex);
	for (int32 Index = 0; Index < InViews.Num(); ++Index)
	{
		if ((VisibilityMap & (1u << Index)) == 0 || InViews[Index]->GetDynamicMeshElementsShadowCullFrustum()) { continue; }
		if (FViewDraws* Entry = Views.Find(InViews[Index]); Entry && !Entry->bConsumed)
		{
			if (Entry->Failure.IsEmpty()) { Entry->Failure = Reason; }
			Entry->Draws.Reset();
		}
	}
}

bool FGGYGOSignedFieldFamily::Accumulate(FRDGBuilder& GraphBuilder, const FSceneView& View,
	TRDGUniformBufferRef<FSceneTextureUniformParameters> SceneTextures, FRDGTextureRef Depth,
	FIntRect ViewRect, FGGYGOSignedFieldTextures& OutTextures, FString& OutReason) const
{
	OutTextures = {};
	if (!Snapshot || !Snapshot->Policy.IsSet())
	{
		OutReason = Snapshot ? Snapshot->Failure : TEXT("family未冻结配置");
		return false;
	}
	TArray<FGGYGOSignedFieldDraw> Draws;
	{
		FScopeLock Lock(&Mutex);
		FViewDraws* Entry = Views.Find(&View);
		if (!Entry || Entry->Graph != &GraphBuilder || Entry->bConsumed)
		{
			OutReason = TEXT("field消费者必须使用原View/Graph且只消费一次");
			return false;
		}
		Entry->bConsumed = true;
		if (!Entry->Failure.IsEmpty()) { OutReason = Entry->Failure; return false; }
		Draws = MoveTemp(Entry->Draws);
	}
	return AccumulateGGYGOSignedFields(GraphBuilder, View, SceneTextures, Depth, ViewRect,
		Snapshot->Policy.GetValue(), Draws, OutTextures, OutReason);
}

void FGGYGOSignedFieldFamily::ReturnGraph(const FRDGBuilder* Graph) const
{
	FScopeLock Lock(&Mutex);
	for (auto Iterator = Views.CreateIterator(); Iterator; ++Iterator)
	{
		if (Iterator.Value().Graph == Graph) { Iterator.RemoveCurrent(); }
	}
}
#endif
