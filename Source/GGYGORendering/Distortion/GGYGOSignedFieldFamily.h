/** @file GGYGOSignedFieldFamily.h
 *  @brief 公开family extension data：冻结原source配置，按实际View/Graph收集原Niagara批次。
 */
#pragma once

#include "CoreMinimal.h"
#include "GGYGODistortionRenderTypes.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGOSignedFieldMeshPass.h"
#include "PrimitiveComponentId.h"
#include "SceneView.h"
#include "UObject/StrongObjectPtr.h"

class FMaterialRenderProxy;
class UMaterialInterface;

/** 来源为一次GT登记解析；Material引用由对应Snapshot持有至所有family归还。 */
struct FGGYGOSignedFieldSource
{
	FPrimitiveComponentId Primitive;
	TSet<const FMaterialRenderProxy*> Materials;
};

class FGGYGOSignedFieldSnapshot final
{
public:
	FGGYGOSignedFieldSnapshot(TOptional<FGGYGODistortionViewPolicy> InPolicy,
		TArray<FGGYGOSignedFieldSource> InSources, const TArray<UMaterialInterface*>& InMaterials,
		FString InFailure);
	bool Accepts(const FPrimitiveSceneProxy& Primitive, const FMaterialRenderProxy* Material) const;
	const TOptional<FGGYGODistortionViewPolicy> Policy;
	const FString Failure;
private:
	const TArray<FGGYGOSignedFieldSource> Sources;
	TArray<TStrongObjectPtr<UMaterialInterface>> Materials;
};

TSharedPtr<const FGGYGOSignedFieldSnapshot, ESPMode::ThreadSafe> MakeGGYGOSignedFieldSnapshot(
	TOptional<FGGYGODistortionViewPolicy> Policy, TArray<FGGYGOSignedFieldSource> Sources,
	const TArray<UMaterialInterface*>& Materials, FString Failure);

/** 继承公开接口；收集只增写本family数据，不读取Renderer私有数组。 */
class FGGYGOSignedFieldFamily final : public ISceneViewFamilyExtentionData,
	public TSharedFromThis<FGGYGOSignedFieldFamily, ESPMode::ThreadSafe>
{
public:
	static const TCHAR* GSubclassIdentifier;
	virtual const TCHAR* GetSubclassIdentifier() const override { return GSubclassIdentifier; }
	void InitializeOnce(TSharedRef<const FGGYGOSignedFieldSnapshot, ESPMode::ThreadSafe> InSnapshot);
	const FGGYGODistortionViewPolicy* GetPolicy() const;
	void BeginView(FRDGBuilder& GraphBuilder, const FSceneView& View) const;
	bool Submit(const FSceneView& View, const FPrimitiveSceneProxy& Primitive,
		const FMeshBatch& Mesh, uint32 RequiredComponents, FString& OutReason) const;
	/** 必需的可见renderer收集失败时废弃该View整组场，防止先提交的半组几何被当作成功。 */
	void RejectVisibleViews(const TArray<const FSceneView*>& InViews, uint32 VisibilityMap,
		const FString& Reason) const;
	bool Accumulate(FRDGBuilder& GraphBuilder, const FSceneView& View,
		TRDGUniformBufferRef<FSceneTextureUniformParameters> SceneTextures, FRDGTextureRef Depth,
		FIntRect ViewRect, FGGYGOSignedFieldTextures& OutTextures, FString& OutReason) const;
private:
	struct FViewDraws
	{
		const FRDGBuilder* Graph = nullptr;
		TArray<FGGYGOSignedFieldDraw> Draws;
		FString Failure;
		bool bConsumed = false;
	};
	void ReturnGraph(const FRDGBuilder* Graph) const;

	// GT一次初始化后不改；RT并行collector只增写其实际View，原Graph回调清理。
	TSharedPtr<const FGGYGOSignedFieldSnapshot, ESPMode::ThreadSafe> Snapshot;
	mutable FCriticalSection Mutex;
	mutable TMap<const FSceneView*, FViewDraws> Views;
};
#endif
