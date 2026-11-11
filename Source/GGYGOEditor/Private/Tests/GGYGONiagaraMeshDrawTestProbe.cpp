/**
 * @file GGYGONiagaraMeshDrawTestProbe.cpp
 * @brief 将原主视口 Draw 与 Deferred Renderer 已收集的动态批次配对。
 */

#include "GGYGONiagaraMeshDrawTestProbe.h"

#include "CoreGlobals.h"
#include "Engine/GameViewportClient.h"

#if GGYGO_WITH_NATIVE_MESH_PROBE && WITH_DEV_AUTOMATION_TESTS
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "HAL/PlatformTime.h"
#include "MaterialShared.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstanceConstant.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialRenderProxy.h"
#include "MeshBatch.h"
#include "Misc/ScopeLock.h"
#include "NiagaraComponent.h"
#include "NiagaraSystemInstanceController.h"
#include "PrimitiveSceneProxy.h"
#include "SceneInterface.h"
#include "SceneRendering.h"
#include "SceneViewExtension.h"
#include "Templates/Atomic.h"
#include "VertexFactory.h"

namespace
{
	constexpr int32 MaterialCount = 3;
	constexpr double ProbeTimeoutSeconds = 5.0;
	constexpr int32 MaxFallbackCandidates = 4;
	constexpr int32 MaxMaterialParentDepth = 16;
	constexpr int32 MaxConcurrentFamilySamples = 3;

	// 只接纳已核对 UE 实现的原生代理链，避免调用自定义材质的虚函数。
	bool IsNativeMaterialProxyChain(const UMaterialInterface& Material)
	{
		const UMaterialInterface* Parent = &Material;
		for (int32 Index = 0; Index < MaxMaterialParentDepth; ++Index)
		{
			if (!Parent)
			{
				return true;
			}
			if (!IsValid(Parent))
			{
				return false;
			}
			if (Parent->GetClass() == UMaterial::StaticClass())
			{
				return true;
			}
			if (Parent->GetClass() != UMaterialInstanceConstant::StaticClass())
			{
				return false;
			}
			Parent = static_cast<const UMaterialInstanceConstant*>(Parent)->Parent.Get();
		}
		return false;
	}

	FGGYGONiagaraMeshDrawRTProxy ReadRTMaterialProxy(const FMaterialRenderProxy& Proxy,
		ERHIFeatureLevel::Type FeatureLevel, const FVertexFactoryType* FactoryType)
	{
		FGGYGONiagaraMeshDrawRTProxy Out;
		Out.ProxyName = Proxy.GetMaterialName();
		const FMaterial* Material = Proxy.GetMaterialNoFallback(FeatureLevel);
		if (!Material)
		{
			Out.ResourceStatus = TEXT("NoMaterialFromProxy");
			return Out;
		}
		Out.BlendMode = static_cast<int32>(Material->GetBlendMode());
		Out.MaterialDomain = static_cast<int32>(Material->GetMaterialDomain());
		Out.bAfterDOF = Material->IsTranslucencyAfterDOFEnabled();
		Out.bAfterMotionBlur = Material->IsTranslucencyAfterMotionBlurEnabled();
		const FMaterialShaderMap* ShaderMap = Material->GetRenderingThreadShaderMap();
		if (!ShaderMap)
		{
			Out.ResourceStatus = TEXT("NoShaderMap");
			return Out;
		}
		Out.bShaderMapComplete = Material->IsRenderingThreadShaderMapComplete();
		if (!ShaderMap->GetContent())
		{
			Out.ResourceStatus = TEXT("NoShaderMapContent");
			return Out;
		}
		if (!FactoryType)
		{
			Out.ResourceStatus = TEXT("NoVertexFactory");
			return Out;
		}
		Out.ResourceStatus = ShaderMap->GetMeshShaderMap(FactoryType)
			? TEXT("VertexFactoryMapPresent") : TEXT("VertexFactoryMapMissing");
		return Out;
	}

	void ReadRTMaterial(const FMeshBatch& Mesh, const FSceneView& View, bool bDefaultMaterialsReady,
		FGGYGONiagaraMeshDrawRTMaterial& Out)
	{
		const ERHIFeatureLevel::Type FeatureLevel = View.GetFeatureLevel();
		const FVertexFactoryType* FactoryType = Mesh.VertexFactory ? Mesh.VertexFactory->GetType() : nullptr;
		Out.FeatureLevel = static_cast<int32>(FeatureLevel);
		Out.ShaderPlatform = static_cast<int32>(View.GetShaderPlatform());
		Out.bUseForMaterial = Mesh.bUseForMaterial;
		if (FactoryType)
		{
			Out.VertexFactoryType = FactoryType->GetFName();
			Out.bVertexFactorySupportsGPUScene = Mesh.VertexFactory->SupportsGPUScene(FeatureLevel);
		}
		Out.BatchStatus = TEXT("Read");
		Out.ShaderKeyCoverage = TEXT("UnknownKey");
		const FMaterialRenderProxy* Proxy = Mesh.MaterialRenderProxy;
		Out.Original = ReadRTMaterialProxy(*Proxy, FeatureLevel, FactoryType);

		// 原生 GetFallback 可到默认材质入口。仅在 GT 已见所有默认材质初始化后遍历。
		if (!bDefaultMaterialsReady)
		{
			Out.FallbackStatus = TEXT("DefaultMaterialsNotReady");
			return;
		}
		TArray<const FMaterialRenderProxy*, TInlineAllocator<MaxFallbackCandidates + 1>> Seen;
		Seen.Add(Proxy);
		for (int32 Index = 0; Index < MaxFallbackCandidates; ++Index)
		{
			Proxy = Proxy->GetFallback(FeatureLevel);
			if (!Proxy)
			{
				Out.FallbackStatus = TEXT("EndOfChain");
				return;
			}
			if (Seen.Contains(Proxy))
			{
				Out.FallbackStatus = TEXT("RepeatedProxy");
				return;
			}
			Seen.Add(Proxy);
			Out.FallbackCandidates.Add(ReadRTMaterialProxy(*Proxy, FeatureLevel, FactoryType));
		}
		Out.FallbackStatus = TEXT("CandidateLimitReached");
	}


	struct FNativeMeshBatchCounts
	{
		int32 Batches = 0;
		int32 Passes[EMeshPass::Num] = {};

		void Add(const FMeshPassMask& Mask)
		{
			++Batches;
			for (int32 Index = 0; Index < EMeshPass::Num; ++Index)
			{
				Passes[Index] += Mask.Get(static_cast<EMeshPass::Type>(Index));
			}
		}

		void WriteTo(FGGYGONiagaraMeshDrawBatchCounts& Out) const
		{
			Out.MeshBatches = Batches;
			for (int32 Index = 0; Index < EMeshPass::Num; ++Index)
			{
				if (Passes[Index] > 0)
				{
					Out.PassCandidates.Add(GetMeshPassName(static_cast<EMeshPass::Type>(Index)), Passes[Index]);
				}
			}
		}
	};

	struct FNativeMeshDrawSnapshot
	{
		EGGYGONiagaraMeshDrawCoverage Coverage = EGGYGONiagaraMeshDrawCoverage::Pending;
		FName Reason;
		FNativeMeshBatchCounts Materials[MaterialCount];
		FGGYGONiagaraMeshDrawRTMaterial RTMaterials[MaterialCount];
		FNativeMeshBatchCounts Unattributed;
		FIntRect UnscaledViewRect;
		FIntRect RenderViewRect;
		TArray<double> ViewProjectionMatrix;
	};

	// Renderer 将此 ViewFamily 数据复制到原 FSceneRenderer。GT 写入后只供原 RT 回调读取。
	struct FNiagaraMeshDrawFamily : ISceneViewFamilyExtentionData
	{
		static const TCHAR* GSubclassIdentifier;
		const TCHAR* GetSubclassIdentifier() const override { return GSubclassIdentifier; }

		TArray<const FGGYGONiagaraMeshDrawTestView*, TInlineAllocator<MaxConcurrentFamilySamples>> Probes;
		uint64 Frame = 0;
		int32 ViewIndex = INDEX_NONE;
	};

	const TCHAR* FNiagaraMeshDrawFamily::GSubclassIdentifier = TEXT("GGYGO.NiagaraMeshDrawTestFamily");
}

class FGGYGONiagaraMeshDrawTestView final : public FSceneViewExtensionBase
{
public:
	FGGYGONiagaraMeshDrawTestView(const FAutoRegister& Register, UWorld& InWorld, FViewport& InViewport,
		int32 InPlayerIndex, uint32 InPawnId, FPrimitiveComponentId InPrimitiveId,
		TArray<const FMaterialRenderProxy*>&& InMaterialProxies, TArray<bool>&& InNativeProxyChains, double InDeadlineSeconds)
		: FSceneViewExtensionBase(Register), Viewport(&InViewport), World(&InWorld), Scene(InWorld.Scene),
		  PlayerIndex(InPlayerIndex), PawnId(InPawnId), PrimitiveId(InPrimitiveId), MaterialProxies(MoveTemp(InMaterialProxies)),
		  NativeProxyChains(MoveTemp(InNativeProxyChains)), DeadlineSeconds(InDeadlineSeconds),
		  bDefaultMaterialsReady(UMaterialInterface::IsDefaultMaterialInitialized())
	{
	}

	bool IsActiveThisFrame_Internal(const FSceneViewExtensionContext& Context) const override
	{
		return IsInGameThread() && !bStopped.Load() && DrawFrame == GFrameCounter && Context.Viewport == Viewport && World.IsValid()
			&& Context.GetWorld() == World.Get();
	}

	void BeginRenderViewFamily(FSceneViewFamily& Family) override
	{
		if (!Family.bIsMainViewFamily || Family.RenderTarget != Viewport || Family.Scene != Scene
			|| Family.FrameCounter != DrawFrame || GFrameCounter != DrawFrame)
		{
			return;
		}
		++MainFamilyCount;
		if (MainFamilyCount != 1)
		{
			return;
		}

		int32 ViewIndex = INDEX_NONE;
		for (int32 Index = 0; Index < Family.Views.Num(); ++Index)
		{
			if (const FSceneView* View = Family.Views[Index]; View && IsOriginalPlayerView(*View))
			{
				if (ViewIndex != INDEX_NONE)
				{
					FamilyIssue = TEXT("AmbiguousPlayerView");
					return;
				}
				ViewIndex = Index;
			}
		}
		if (ViewIndex == INDEX_NONE)
		{
			FamilyIssue = TEXT("MissingPlayerView");
			return;
		}

		FNiagaraMeshDrawFamily* Tag = Family.GetOrCreateExtentionData<FNiagaraMeshDrawFamily>();
		if (Tag->Probes.Num() >= MaxConcurrentFamilySamples || Tag->Probes.Contains(this)
			|| (!Tag->Probes.IsEmpty() && (Tag->Frame != DrawFrame || Tag->ViewIndex != ViewIndex)))
		{
			FamilyIssue = TEXT("FamilySampleLimitOrIdentityMismatch");
			return;
		}
		Tag->Probes.Add(this);
		Tag->Frame = DrawFrame;
		Tag->ViewIndex = ViewIndex;
	}

	void PrePostProcessPass_RenderThread(FRDGBuilder&, const FSceneView& View, const FPostProcessingInputs&) override
	{
		const FSceneViewFamily& Family = *View.Family;
		const FNiagaraMeshDrawFamily* Tag = Family.GetExtentionData<FNiagaraMeshDrawFamily>();
		if (bStopped.Load() || !Tag || !Tag->Probes.Contains(this) || Family.FrameCounter != Tag->Frame || Family.Scene != Scene
			|| Family.RenderTarget != Viewport || !Family.bIsMainViewFamily || !Family.Views.IsValidIndex(Tag->ViewIndex)
			|| Family.Views[Tag->ViewIndex] != &View)
		{
			return;
		}

		if (bReadOnRenderThread)
		{
			FNativeMeshDrawSnapshot Duplicate;
			Duplicate.Coverage = EGGYGONiagaraMeshDrawCoverage::Uncovered;
			Duplicate.Reason = TEXT("DuplicateRenderView");
			Publish(MoveTemp(Duplicate));
			return;
		}
		bReadOnRenderThread = true;
		Publish(ReadOriginalView(View));
	}

	FNativeMeshDrawSnapshot ReadSnapshot() const
	{
		FScopeLock Lock(&SnapshotLock);
		return Snapshot;
	}

	void Stop() { bStopped.Store(true); }

	// 只在 GT 读写。RT 使用随 Family 传递的唯一 Tag。
	uint64 DrawFrame = MAX_uint64;
	int32 MainFamilyCount = 0;
	FName FamilyIssue;
	FViewport* const Viewport;

private:
	bool IsOriginalPlayerView(const FSceneView& View) const
	{
		return View.StereoPass == EStereoscopicPass::eSSP_FULL && View.PlayerIndex == PlayerIndex
			&& View.ViewActor.ActorUniqueId == PawnId && !View.bIsSceneCapture && !View.bIsReflectionCapture
			&& !View.bIsPlanarReflection && !View.CustomRenderPass && !View.GetDynamicMeshElementsShadowCullFrustum()
			&& View.UnscaledViewRect.Width() > 0 && View.UnscaledViewRect.Height() > 0;
	}

	FNativeMeshDrawSnapshot ReadOriginalView(const FSceneView& View) const
	{
		FNativeMeshDrawSnapshot Out;
		Out.Coverage = EGGYGONiagaraMeshDrawCoverage::Uncovered;
		if (FPlatformTime::Seconds() >= DeadlineSeconds)
		{
			Out.Reason = TEXT("RenderObservationTimedOut");
			return Out;
		}
		if (!View.bIsViewInfo || !IsOriginalPlayerView(View))
		{
			Out.Reason = TEXT("RenderViewIdentityMismatch");
			return Out;
		}

		// Deferred 在此回调前已完成 FinishGatherDynamicMeshElements 和 Pass relevance。
		const FViewInfo& ViewInfo = static_cast<const FViewInfo&>(View);
		Out.UnscaledViewRect = View.UnscaledViewRect;
		Out.RenderViewRect = ViewInfo.ViewRect;
		const FMatrix& ViewProjection = View.ViewMatrices.GetViewProjectionMatrix();
		for (int32 Row = 0; Row < 4; ++Row)
		{
			for (int32 Column = 0; Column < 4; ++Column)
			{
				Out.ViewProjectionMatrix.Add(ViewProjection.M[Row][Column]);
			}
		}
		const auto& Batches = ViewInfo.DynamicMeshElements;
		const auto& Masks = ViewInfo.DynamicMeshElementsPassRelevance;
		if (Batches.Num() != Masks.Num())
		{
			Out.Reason = TEXT("MeshBatchPassMaskSizeMismatch");
			return Out;
		}

		const FMeshBatch* AttributedBatches[MaterialCount] = {};
		for (int32 Index = 0; Index < Batches.Num(); ++Index)
		{
			const FMeshBatchAndRelevance& Entry = Batches[Index];
			if (!Entry.PrimitiveSceneProxy || Entry.PrimitiveSceneProxy->GetPrimitiveComponentId() != PrimitiveId)
			{
				continue;
			}
			const int32 MaterialIndex = Entry.Mesh ? MaterialProxies.IndexOfByKey(Entry.Mesh->MaterialRenderProxy) : INDEX_NONE;
			FNativeMeshBatchCounts& Counts = MaterialIndex == INDEX_NONE ? Out.Unattributed : Out.Materials[MaterialIndex];
			Counts.Add(Masks[Index]);
			if (MaterialIndex != INDEX_NONE)
			{
				AttributedBatches[MaterialIndex] = Entry.Mesh;
			}
		}

		for (int32 Index = 0; Index < MaterialCount; ++Index)
		{
			FGGYGONiagaraMeshDrawRTMaterial& RTMaterial = Out.RTMaterials[Index];
			const int32 BatchCount = Out.Materials[Index].Batches;
			if (BatchCount != 1)
			{
				RTMaterial.BatchStatus = BatchCount == 0 ? TEXT("NoAttributedBatch") : TEXT("AmbiguousAttributedBatches");
				continue;
			}
			if (!NativeProxyChains[Index])
			{
				RTMaterial.BatchStatus = TEXT("UnsupportedMaterialProxyChain");
				continue;
			}
			ReadRTMaterial(*AttributedBatches[Index], View, bDefaultMaterialsReady, RTMaterial);
		}
		Out.Coverage = EGGYGONiagaraMeshDrawCoverage::Covered;
		return Out;
	}

	void Publish(FNativeMeshDrawSnapshot&& InSnapshot)
	{
		FScopeLock Lock(&SnapshotLock);
		Snapshot = MoveTemp(InSnapshot);
	}

	TWeakObjectPtr<UWorld> World;
	const FSceneInterface* const Scene;
	const int32 PlayerIndex;
	const uint32 PawnId;
	const FPrimitiveComponentId PrimitiveId;
	const TArray<const FMaterialRenderProxy*> MaterialProxies;
	const TArray<bool> NativeProxyChains;
	const double DeadlineSeconds;
	const bool bDefaultMaterialsReady;
	TAtomic<bool> bStopped{false};
	bool bReadOnRenderThread = false;
	mutable FCriticalSection SnapshotLock;
	FNativeMeshDrawSnapshot Snapshot;
};
#endif

UGGYGONiagaraMeshDrawTestProbe* UGGYGONiagaraMeshDrawTestProbe::BeginNextDraw(ULocalPlayer* Player, APawn* ViewPawn,
	UNiagaraComponent* Component, const TArray<UMaterialInterface*>& Materials)
{
	check(IsInGameThread());
	UGGYGONiagaraMeshDrawTestProbe* Probe = NewObject<UGGYGONiagaraMeshDrawTestProbe>(GetTransientPackage());
#if GGYGO_WITH_NATIVE_MESH_PROBE && WITH_DEV_AUTOMATION_TESTS
	if (!GIsAutomationTesting)
	{
		Probe->FinishUncovered(TEXT("AutomationRequired"));
		return Probe;
	}

	UWorld* World = IsValid(Player) ? Player->GetWorld() : nullptr;
	UGameViewportClient* GameViewport = World ? World->GetGameViewport() : nullptr;
	FViewport* Viewport = IsValid(GameViewport) ? GameViewport->Viewport : nullptr;
	if (!World || !World->Scene || World->Scene->GetShadingPath() != EShadingPath::Deferred
		|| !Viewport || Player->ViewportClient != GameViewport || !IsValid(ViewPawn) || ViewPawn->GetWorld() != World)
	{
		Probe->FinishUncovered(TEXT("InvalidPlayerViewportOrScene"));
		return Probe;
	}

	if (!IsValid(Component) || !Component->IsRegistered() || Component->GetWorld() != World
		|| !Component->GetPrimitiveSceneId().IsValid())
	{
		Probe->FinishUncovered(TEXT("InvalidOriginalPrimitive"));
		return Probe;
	}
	const auto Controller = Component->GetSystemInstanceController();
	if (!Controller || !Controller->IsValid())
	{
		Probe->FinishUncovered(TEXT("MissingOriginalNiagaraInstance"));
		return Probe;
	}

	TArray<const FMaterialRenderProxy*> Proxies;
	TArray<bool> NativeProxyChains;
	if (Materials.Num() != MaterialCount)
	{
		Probe->FinishUncovered(TEXT("ThreeMaterialsRequired"));
		return Probe;
	}
	for (UMaterialInterface* Material : Materials)
	{
		const FMaterialRenderProxy* Proxy = IsValid(Material) ? Material->GetRenderProxy() : nullptr;
		if (!Proxy || Proxies.Contains(Proxy))
		{
			Probe->FinishUncovered(TEXT("InvalidOrDuplicateMaterialProxy"));
			return Probe;
		}
		Proxies.Add(Proxy);
		NativeProxyChains.Add(IsNativeMaterialProxyChain(*Material));
		Probe->ObservedMaterials.Add(Material);
	}

	const FPrimitiveComponentId PrimitiveId = Component->GetPrimitiveSceneId();
	Probe->Result.WorldObjectId = World->GetUniqueID();
	Probe->Result.ViewportIdentity = FString::Printf(TEXT("%p"), Viewport);
	Probe->Result.ComponentPath = Component->GetPathName();
	Probe->Result.PrimitiveComponentId = PrimitiveId.PrimIDValue;
	Probe->Result.NiagaraInstanceId = static_cast<int64>(Controller->GetSystemInstanceID());
	Probe->Client = GameViewport;
	Probe->ObservedComponent = Component;
	Probe->DeadlineSeconds = FPlatformTime::Seconds() + ProbeTimeoutSeconds;
	Probe->ViewExtension = FSceneViewExtensions::NewExtension<FGGYGONiagaraMeshDrawTestView>(
		*World, *Viewport, Player->GetControllerId(), ViewPawn->GetUniqueID(), PrimitiveId,
		MoveTemp(Proxies), MoveTemp(NativeProxyChains), Probe->DeadlineSeconds);
	Probe->BeginDrawHandle = GameViewport->OnBeginDraw().AddUObject(Probe, &ThisClass::OnBeginDraw);
	Probe->ViewportRenderedHandle = UGameViewportClient::OnViewportRendered().AddUObject(Probe, &ThisClass::OnViewportRendered);
#else
	Probe->FinishUncovered(TEXT("UnsupportedRendererTestBuild"));
#endif
	return Probe;
}

bool UGGYGONiagaraMeshDrawTestProbe::ConfirmOriginalDraw(UNiagaraComponent* Component)
{
	check(IsInGameThread());
#if GGYGO_WITH_NATIVE_MESH_PROBE && WITH_DEV_AUTOMATION_TESTS
	if (Result.Coverage == EGGYGONiagaraMeshDrawCoverage::Pending && !bOriginalDrawConfirmed && !bViewportRendered
		&& ViewExtension->DrawFrame == GFrameCounter && ViewExtension->MainFamilyCount == 1
		&& ViewExtension->FamilyIssue.IsNone() && HasOriginalInstance(Component))
	{
		bOriginalDrawConfirmed = true;
		return true;
	}
#endif
	return false;
}

#if GGYGO_WITH_NATIVE_MESH_PROBE && WITH_DEV_AUTOMATION_TESTS
bool UGGYGONiagaraMeshDrawTestProbe::HasOriginalInstance(UNiagaraComponent* Component) const
{
	if (!Component || Component != ObservedComponent.Get() || !Component->IsRegistered()
		|| Component->GetPrimitiveSceneId().PrimIDValue != Result.PrimitiveComponentId)
	{
		return false;
	}
	const auto Controller = Component->GetSystemInstanceController();
	return Controller && Controller->IsValid() && static_cast<int64>(Controller->GetSystemInstanceID()) == Result.NiagaraInstanceId;
}

void UGGYGONiagaraMeshDrawTestProbe::OnBeginDraw()
{
	if (FPlatformTime::Seconds() >= DeadlineSeconds)
	{
		FinishUncovered(TEXT("DrawTimedOut"));
		return;
	}

	if (Client->Viewport != ViewExtension->Viewport || !HasOriginalInstance(ObservedComponent.Get()))
	{
		FinishUncovered(TEXT("OriginalDrawTargetChanged"));
		return;
	}

	Client->OnBeginDraw().Remove(BeginDrawHandle);
	BeginDrawHandle.Reset();
	Result.FrameCounter = static_cast<int64>(GFrameCounter);
	ViewExtension->DrawFrame = GFrameCounter;
}

void UGGYGONiagaraMeshDrawTestProbe::OnViewportRendered(FViewport* Viewport)
{
	if (Viewport != ViewExtension->Viewport || Result.FrameCounter == INDEX_NONE)
	{
		return;
	}
	if (ViewExtension->DrawFrame != GFrameCounter || ViewExtension->MainFamilyCount != 1)
	{
		FinishUncovered(ViewExtension->MainFamilyCount > 1 ? TEXT("AmbiguousMainViewFamily") : TEXT("MissingSameDrawMainViewFamily"));
		return;
	}
	if (!ViewExtension->FamilyIssue.IsNone())
	{
		FinishUncovered(ViewExtension->FamilyIssue);
		return;
	}
	if (!bOriginalDrawConfirmed)
	{
		FinishUncovered(TEXT("OriginalDrawNotConfirmed"));
		return;
	}

	ViewExtension->DrawFrame = MAX_uint64;
	bViewportRendered = true;
	UGameViewportClient::OnViewportRendered().Remove(ViewportRenderedHandle);
	ViewportRenderedHandle.Reset();
}
#endif

FGGYGONiagaraMeshDrawTestResult UGGYGONiagaraMeshDrawTestProbe::Poll()
{
	check(IsInGameThread());
#if GGYGO_WITH_NATIVE_MESH_PROBE && WITH_DEV_AUTOMATION_TESTS
	if (Result.Coverage != EGGYGONiagaraMeshDrawCoverage::Pending)
	{
		return Result;
	}
	if (bViewportRendered)
	{
		const FNativeMeshDrawSnapshot Snapshot = ViewExtension->ReadSnapshot();
		if (Snapshot.Coverage == EGGYGONiagaraMeshDrawCoverage::Covered)
		{
			Result.Coverage = Snapshot.Coverage;
			Result.UnscaledViewRect = Snapshot.UnscaledViewRect;
			Result.RenderViewRect = Snapshot.RenderViewRect;
			Result.ViewProjectionMatrix = Snapshot.ViewProjectionMatrix;
			Snapshot.Unattributed.WriteTo(Result.Unattributed);
			Result.ComponentMeshBatches = Result.Unattributed.MeshBatches;
			for (int32 Index = 0; Index < MaterialCount; ++Index)
			{
				FGGYGONiagaraMeshDrawBatchCounts& Counts = Result.Materials.AddDefaulted_GetRef();
				Counts.MaterialPath = ObservedMaterials[Index]->GetPathName();
				Snapshot.Materials[Index].WriteTo(Counts);
				Counts.RTMaterial = Snapshot.RTMaterials[Index];
				Result.ComponentMeshBatches += Counts.MeshBatches;
			}
			Detach();
			return Result;
		}
		if (Snapshot.Coverage == EGGYGONiagaraMeshDrawCoverage::Uncovered)
		{
			FinishUncovered(Snapshot.Reason);
			return Result;
		}
	}
	if (FPlatformTime::Seconds() >= DeadlineSeconds)
	{
		FinishUncovered(bViewportRendered ? TEXT("MissingRenderThreadObservation")
			: Result.FrameCounter == INDEX_NONE ? TEXT("MissingViewportDrawBegin") : TEXT("MissingViewportDrawEnd"));
	}
#endif
	return Result;
}

void UGGYGONiagaraMeshDrawTestProbe::Cancel()
{
	check(IsInGameThread());
	if (Result.Coverage == EGGYGONiagaraMeshDrawCoverage::Pending)
	{
		FinishUncovered(TEXT("Cancelled"));
	}
}

void UGGYGONiagaraMeshDrawTestProbe::BeginDestroy()
{
	Detach();
	Super::BeginDestroy();
}

void UGGYGONiagaraMeshDrawTestProbe::FinishUncovered(FName Reason)
{
	Result.Coverage = EGGYGONiagaraMeshDrawCoverage::Uncovered;
	Result.Reason = Reason;
	Detach();
}

void UGGYGONiagaraMeshDrawTestProbe::Detach()
{
	if (UGameViewportClient* GameViewport = Client.Get(); GameViewport && BeginDrawHandle.IsValid())
	{
		GameViewport->OnBeginDraw().Remove(BeginDrawHandle);
	}
	if (ViewportRenderedHandle.IsValid())
	{
		UGameViewportClient::OnViewportRendered().Remove(ViewportRenderedHandle);
	}
	BeginDrawHandle.Reset();
	ViewportRenderedHandle.Reset();
#if GGYGO_WITH_NATIVE_MESH_PROBE && WITH_DEV_AUTOMATION_TESTS
	if (ViewExtension)
	{
		ViewExtension->Stop();
	}
#endif
	ViewExtension.Reset();
	ObservedMaterials.Reset();
}
