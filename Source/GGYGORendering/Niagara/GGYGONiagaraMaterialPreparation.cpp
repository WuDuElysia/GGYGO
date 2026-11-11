/** @file GGYGONiagaraMaterialPreparation.cpp
 *  @brief 通过原引擎编译通知及一次 RT 读回完成材质准备，不驱动 Niagara 模拟。
 */
#include "Niagara/GGYGONiagaraMaterialPreparation.h"

#include "Async/Async.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "MaterialShared.h"
#include "Materials/Material.h"
#include "Niagara/GGYGONiagaraMaterialBindings.h"
#include "NiagaraComponent.h"
#include "NiagaraSystem.h"
#include "RenderingThread.h"
#include "SceneInterface.h"
#include "UObject/StrongObjectPtr.h"
#include "VertexFactory.h"
#if WITH_EDITOR
#include "AssetCompilingManager.h"
#endif

DEFINE_LOG_CATEGORY_STATIC(LogGGYGONiagaraPreparation, Log, All);

namespace
{
	constexpr float PreparationTimeoutSeconds = 60.0f;

	struct FPreparedMaterial
	{
		TWeakObjectPtr<UMaterialInterface> Owner;
		TRefCountPtr<FMaterialResource> Resource;
		TRefCountPtr<FMaterialShaderMap> ShaderMap;
		const FVertexFactoryType* VertexFactory = nullptr;
		FString Source;

		bool Matches(const FPreparedMaterial& Other) const
		{
			return Resource.GetReference() == Other.Resource.GetReference()
				&& ShaderMap.GetReference() == Other.ShaderMap.GetReference() && VertexFactory == Other.VertexFactory;
		}
		bool IsCurrent(EShaderPlatform Platform) const
		{
			UMaterialInterface* Material = Owner.Get();
			return Material && Material->GetMaterialResource(Platform) == Resource.GetReference()
				&& Resource->GetGameThreadShaderMap() == ShaderMap.GetReference()
				&& Resource->IsGameThreadShaderMapComplete();
		}
	};

	bool SameBindings(const TArray<FGGYGONiagaraMaterialBinding>& A, const TArray<FGGYGONiagaraMaterialBinding>& B)
	{
		if (A.Num() != B.Num()) { return false; }
		for (int32 Index = 0; Index < A.Num(); ++Index)
		{
			if (A[Index].Material != B[Index].Material || A[Index].VertexFactory != B[Index].VertexFactory
				|| A[Index].Source != B[Index].Source || A[Index].Usage != B[Index].Usage || A[Index].bDecal != B[Index].bDecal)
			{ return false; }
		}
		return true;
	}
}

struct FGGYGONiagaraPreparedResources
{
	// 只存本 World 已真实读过 RT 的资源/ShaderMap 身份。新请求仍重新解析全部最终绑定。
	TArray<FPreparedMaterial> Ready;
};

struct FGGYGONiagaraPreparationWork
{
	FSceneInterface* Scene = nullptr;
	EShaderPlatform Platform = SP_NumPlatforms;
	TSharedPtr<FGGYGONiagaraPreparedResources> WorldResources;
	TArray<TPair<TWeakObjectPtr<UNiagaraSystem>, FDelegateHandle>> SystemCompiledHandles;
	TArray<FGGYGONiagaraMaterialBinding> Bindings;
	TArray<FPreparedMaterial> RenderRead;
	bool bReadingRenderResources = false;
	bool bAdvancing = false;
	FString WaitingOn;
};

void UGGYGONiagaraMaterialPreparationWorld::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	Resources = MakeShared<FGGYGONiagaraPreparedResources>();
}

void UGGYGONiagaraMaterialPreparationWorld::Deinitialize()
{
	if (Resources) { Resources->Ready.Reset(); }
	Resources.Reset();
	Super::Deinitialize();
}

UGGYGONiagaraMaterialPreparation::UGGYGONiagaraMaterialPreparation(const FObjectInitializer& ObjectInitializer)
	: Super(ObjectInitializer)
{
}

UGGYGONiagaraMaterialPreparation::UGGYGONiagaraMaterialPreparation(FVTableHelper& Helper)
	: Super(Helper)
{
}

UGGYGONiagaraMaterialPreparation::~UGGYGONiagaraMaterialPreparation() = default;

UGGYGONiagaraMaterialPreparation* UGGYGONiagaraMaterialPreparation::CreateForSystems(UObject* Owner, UWorld* World,
	const TArray<FGGYGONiagaraSystemPreparation>& Systems)
{
	if (!IsValid(Owner)) { return nullptr; }
	auto* Request = NewObject<UGGYGONiagaraMaterialPreparation>(Owner);
	Request->RequestedWorld = World;
	Request->RequestedSystems = Systems;
	return Request;
}

UGGYGONiagaraMaterialPreparation* UGGYGONiagaraMaterialPreparation::CreateForSystemAssets(UObject* Owner,
	const UObject* WorldContextObject, const TArray<UNiagaraSystem*>& Systems)
{
	TArray<FGGYGONiagaraSystemPreparation> Inputs;
	Inputs.Reserve(Systems.Num());
	for (UNiagaraSystem* System : Systems) { Inputs.AddDefaulted_GetRef().System = System; }
	UWorld* World = GEngine ? GEngine->GetWorldFromContextObject(WorldContextObject, EGetWorldErrorMode::ReturnNull) : nullptr;
	return CreateForSystems(Owner, World, Inputs);
}

UGGYGONiagaraMaterialPreparation* UGGYGONiagaraMaterialPreparation::CreateForComponents(UObject* Owner,
	const TArray<UNiagaraComponent*>& Components)
{
	if (!IsValid(Owner)) { return nullptr; }
	auto* Request = NewObject<UGGYGONiagaraMaterialPreparation>(Owner);
	for (UNiagaraComponent* Component : Components) { Request->RequestedComponents.Add(Component); }
	Request->RequestedWorld = !Components.IsEmpty() && IsValid(Components[0]) ? Components[0]->GetWorld() : nullptr;
	return Request;
}

void UGGYGONiagaraMaterialPreparation::Start()
{
	check(IsInGameThread());
	const TStrongObjectPtr<ThisClass> KeepAlive(this);
	if (bStarted || State != EGGYGONiagaraMaterialPreparationState::Pending) { return; }
	bStarted = true;
	UWorld* World = RequestedWorld.Get();
	StartFrame = GFrameCounter;
	StartWorldSeconds = World ? World->GetTimeSeconds() : -1.0;
	if (!World || World->bIsTearingDown || !World->Scene || (RequestedSystems.IsEmpty() && RequestedComponents.IsEmpty()))
	{
		Finish(EGGYGONiagaraMaterialPreparationState::Failed, TEXT("材质准备需要有效原 World/Scene 及非空 NS 或组件集合"));
		return;
	}
	Work = MakeUnique<FGGYGONiagaraPreparationWork>();
	Work->Scene = World->Scene;
	Work->Platform = World->Scene->GetShaderPlatform();
	auto* WorldState = World->GetSubsystem<UGGYGONiagaraMaterialPreparationWorld>();
	if (!WorldState || !WorldState->Resources)
	{
		Finish(EGGYGONiagaraMaterialPreparationState::Failed, TEXT("原 World 材质准备服务不可用"));
		return;
	}
	Work->WorldResources = WorldState->Resources;
	WorldCleanupHandle = FWorldDelegates::OnWorldCleanup.AddUObject(this, &ThisClass::OnWorldCleanup);
	World->GetTimerManager().SetTimer(TimeoutHandle, this, &ThisClass::OnTimeout, PreparationTimeoutSeconds, false);
#if WITH_EDITOR
	// 编译管理器仍唯一推进原生工作。通知只请求重读，不从其它线程访问 UObject/资源。
	const TWeakObjectPtr<ThisClass> WeakThis(this);
	const auto Wake = [WeakThis]()
	{
		AsyncTask(ENamedThreads::GameThread, [WeakThis]() { if (auto* Request = WeakThis.Get()) { Request->Advance(); } });
	};
	AssetCompiledHandle = FAssetCompilingManager::Get().OnAssetPostCompileEvent().AddLambda(
		[Wake](const TArray<FAssetCompileData>&) { Wake(); });
	MaterialCompiledHandle = UMaterial::OnMaterialCompilationFinished().AddLambda([Wake](UMaterialInterface*) { Wake(); });
	TSet<UNiagaraSystem*> Systems;
	for (const FGGYGONiagaraSystemPreparation& Input : RequestedSystems) { if (IsValid(Input.System)) { Systems.Add(Input.System); } }
	for (UNiagaraComponent* Component : RequestedComponents)
	{
		if (IsValid(Component) && IsValid(Component->GetAsset())) { Systems.Add(Component->GetAsset()); }
	}
	for (UNiagaraSystem* System : Systems)
	{
		Work->SystemCompiledHandles.Emplace(System, System->OnSystemCompiled().AddLambda([Wake](UNiagaraSystem*) { Wake(); }));
	}
#endif
	Advance();
}

void UGGYGONiagaraMaterialPreparation::Advance()
{
	check(IsInGameThread());
	if (State != EGGYGONiagaraMaterialPreparationState::Pending || !Work || Work->bAdvancing || Work->bReadingRenderResources) { return; }
	const TStrongObjectPtr<ThisClass> KeepAlive(this);
	TGuardValue<bool> Advancing(Work->bAdvancing, true);
	UWorld* World = RequestedWorld.Get();
	if (!World || World->bIsTearingDown || World->Scene != Work->Scene
		|| World->Scene->GetShaderPlatform() != Work->Platform)
	{
		Finish(EGGYGONiagaraMaterialPreparationState::Cancelled, TEXT("原 World/Scene/ShaderPlatform 已改变或正在退出"));
		return;
	}

	TArray<FGGYGONiagaraMaterialBinding> Bindings;
	FString Failure;
	bool bPendingAssets = false;
	const auto Collect = [&](UNiagaraSystem* System, const FNiagaraParameterStore* Overrides,
		const TMap<FName, TObjectPtr<UObject>>* ExplicitOverrides)
	{
		if (!IsValid(System)) { Failure = TEXT("请求集合包含无效 Niagara System"); return; }
#if WITH_EDITOR
		if (System->NeedsRequestCompile()) { System->RequestCompile(false); }
		if (State != EGGYGONiagaraMaterialPreparationState::Pending) { return; }
		if (System->HasOutstandingCompilationRequests(true)) { bPendingAssets = true; Work->WaitingOn = System->GetPathName(); return; }
#endif
		if (!System->IsValid()) { Failure = TEXT("原 Niagara 系统编译结果无效：") + System->GetPathName(); return; }
		ResolveGGYGONiagaraMaterialBindings(*System, Overrides, ExplicitOverrides, Bindings, bPendingAssets, Failure);
		if (bPendingAssets) { Work->WaitingOn = System->GetPathName(); }
	};
	for (const FGGYGONiagaraSystemPreparation& Input : RequestedSystems)
	{
		Collect(Input.System, nullptr, &Input.UserObjectOverrides);
		if (State != EGGYGONiagaraMaterialPreparationState::Pending) { return; }
		if (!Failure.IsEmpty()) { break; }
	}
	for (UNiagaraComponent* Component : RequestedComponents)
	{
		if (!Failure.IsEmpty()) { break; }
		if (!IsValid(Component) || !Component->IsRegistered() || Component->GetWorld() != World)
		{
			Failure = TEXT("原 Niagara 组件已失效、注销或不属于本 World");
			break;
		}
		Collect(Component->GetAsset(), &Component->GetOverrideParameters(), nullptr);
		if (State != EGGYGONiagaraMaterialPreparationState::Pending) { return; }
	}
	if (!Failure.IsEmpty()) { Finish(EGGYGONiagaraMaterialPreparationState::Failed, MoveTemp(Failure)); return; }
	if (bPendingAssets) { return; }

	Work->Bindings = MoveTemp(Bindings);
	RetainedInputs.Reset();
	Work->RenderRead.Reset();
	bool bPendingCompilation = false;
	for (const FGGYGONiagaraMaterialBinding& Binding : Work->Bindings)
	{
		UMaterialInterface* Material = Binding.Material;
		RetainedInputs.AddUnique(Material);
		FMaterialResource* Resource = Material->GetMaterialResource(Work->Platform);
		if (!Resource || Resource->GetShaderPlatform() != Work->Platform
			|| Resource->GetMaterialDomain() != (Binding.bDecal ? MD_DeferredDecal : MD_Surface)
			|| (Binding.Usage != MATUSAGE_MAX && !Material->GetUsageByFlag(Binding.Usage)))
		{
			Finish(EGGYGONiagaraMaterialPreparationState::Failed, Binding.Source + TEXT("：原平台资源、Domain 或有效 Niagara Usage 不符，Material=") + Material->GetPathName());
			return;
		}
		// 持有原资源穿过原生返栈；不取消其它使用者的共享编译。
		const TRefCountPtr<FMaterialResource> OriginalResource(Resource);
#if WITH_EDITOR
		bool bFinished = Resource->IsCompilationFinished(); // DDC 未就绪时原生直接返回，不阻塞等待。
		if (State != EGGYGONiagaraMaterialPreparationState::Pending) { return; }
		if (Material->GetMaterialResource(Work->Platform) != Resource)
		{
			Finish(EGGYGONiagaraMaterialPreparationState::Failed, Binding.Source + TEXT("：原生编译返栈时资源被替换"));
			return;
		}
		if (!Resource->IsGameThreadShaderMapComplete())
		{
			Resource->SubmitCompileJobs_GameThread(EShaderCompileJobPriority::High);
			bFinished = Resource->IsCompilationFinished();
			if (State != EGGYGONiagaraMaterialPreparationState::Pending) { return; }
			if (Material->GetMaterialResource(Work->Platform) != Resource)
			{
				Finish(EGGYGONiagaraMaterialPreparationState::Failed, Binding.Source + TEXT("：提交编译返栈时原资源被替换"));
				return;
			}
		}
		if (!Resource->GetCompileErrors().IsEmpty())
		{
			Finish(EGGYGONiagaraMaterialPreparationState::Failed, Binding.Source + TEXT("：") + FString::Join(Resource->GetCompileErrors(), TEXT("\n")));
			return;
		}
		if (!bFinished) { bPendingCompilation = true; Work->WaitingOn = Binding.Source + TEXT(" Material=") + Material->GetPathName(); continue; }
#endif
		FMaterialShaderMap* Map = Resource->GetGameThreadShaderMap();
		if (!Resource->IsGameThreadShaderMapComplete() || !Map || !Map->GetContent() || !Map->IsValidForRendering(false)
			|| (Binding.VertexFactory && !Map->GetMeshShaderMap(Binding.VertexFactory)))
		{
			Finish(EGGYGONiagaraMaterialPreparationState::Failed,
				Binding.Source + TEXT("：原平台 ShaderMap/VF 未就绪且无可等待的原生编译；需修复资源制作或 Cook，Material=") + Material->GetPathName());
			return;
		}
		FPreparedMaterial Prepared;
		Prepared.Owner = Resource->GetMaterialInterface();
		Prepared.Resource = Resource;
		Prepared.ShaderMap = Map;
		Prepared.VertexFactory = Binding.VertexFactory;
		Prepared.Source = Binding.Source + TEXT(" Material=") + Material->GetPathName();
		RetainedInputs.AddUnique(Resource->GetMaterialInterface());
		Work->RenderRead.Add(MoveTemp(Prepared));
	}
	if (bPendingCompilation) { return; }
	TArray<FPreparedMaterial>& Cached = Work->WorldResources->Ready;
	Cached.RemoveAll([Platform = Work->Platform](const FPreparedMaterial& Item) { return !Item.IsCurrent(Platform); });
	const bool bAllCached = Work->RenderRead.ContainsByPredicate([&Cached](const FPreparedMaterial& Item)
	{
		return !Cached.ContainsByPredicate([&Item](const FPreparedMaterial& Ready) { return Ready.Matches(Item); });
	}) == false;
	if (bAllCached) { Finish(EGGYGONiagaraMaterialPreparationState::Ready, FString()); return; }

	Work->bReadingRenderResources = true;
	const TWeakObjectPtr<ThisClass> WeakThis(this);
	ENQUEUE_RENDER_COMMAND(GGYGOReadNiagaraMaterialPreparation)(
		[WeakThis, Read = Work->RenderRead](FRHICommandListImmediate&)
		{
			FString Error;
			for (const FPreparedMaterial& Item : Read)
			{
				const FMaterialShaderMap* Map = Item.Resource->GetRenderingThreadShaderMap();
				if (Map != Item.ShaderMap.GetReference() || !Item.Resource->IsRenderingThreadShaderMapComplete()
					|| !Map || !Map->GetContent() || (Item.VertexFactory && !Map->GetMeshShaderMap(Item.VertexFactory)))
				{
					Error = Item.Source + TEXT("：RT 原资源/ShaderMap/VF 尚未匹配本次 GT 就绪结果");
					break;
				}
			}
			AsyncTask(ENamedThreads::GameThread, [WeakThis, Error = MoveTemp(Error)]()
			{
				if (auto* Request = WeakThis.Get()) { Request->OnRenderResourcesRead(Error.IsEmpty(), Error); }
			});
		});
}

void UGGYGONiagaraMaterialPreparation::OnRenderResourcesRead(bool bReady, FString Reason)
{
	if (State != EGGYGONiagaraMaterialPreparationState::Pending || !Work) { return; }
	const TStrongObjectPtr<ThisClass> KeepAlive(this);
	Work->bReadingRenderResources = false;
	UWorld* World = RequestedWorld.Get();
	if (!World || World->bIsTearingDown || World->Scene != Work->Scene || World->Scene->GetShaderPlatform() != Work->Platform)
	{
		Finish(EGGYGONiagaraMaterialPreparationState::Cancelled, TEXT("RT 完成前原 World/Scene/平台已退出或改变"));
		return;
	}
	// 重读闭包及资源，不能把旧参数、旧质量或旧 ShaderMap 的 RT 结果交给后继请求。
	TArray<FGGYGONiagaraMaterialBinding> Current;
	FString Failure;
	bool bPendingAssets = false;
	for (const FGGYGONiagaraSystemPreparation& Input : RequestedSystems)
	{
		if (!IsValid(Input.System) || !ResolveGGYGONiagaraMaterialBindings(*Input.System, nullptr, &Input.UserObjectOverrides, Current, bPendingAssets, Failure))
		{ if (Failure.IsEmpty()) { Failure = TEXT("RT 返栈时原 NS 已失效"); } break; }
	}
	for (UNiagaraComponent* Component : RequestedComponents)
	{
		if (!Failure.IsEmpty()) { break; }
		if (!IsValid(Component) || !Component->IsRegistered() || Component->GetWorld() != World || !IsValid(Component->GetAsset()))
		{ Failure = TEXT("RT 返栈时原组件已失效或注销"); break; }
		if (!ResolveGGYGONiagaraMaterialBindings(*Component->GetAsset(), &Component->GetOverrideParameters(), nullptr, Current, bPendingAssets, Failure)) { break; }
	}
	if (!Failure.IsEmpty()) { Finish(EGGYGONiagaraMaterialPreparationState::Failed, MoveTemp(Failure)); return; }
	if (bPendingAssets || !SameBindings(Current, Work->Bindings)
		|| Work->RenderRead.ContainsByPredicate([this](const FPreparedMaterial& Item) { return !Item.IsCurrent(Work->Platform); }))
	{
		Finish(EGGYGONiagaraMaterialPreparationState::Failed, TEXT("RT 返栈时最终材质绑定/平台质量资源或 ShaderMap 身份已改变，请用当前配置重新准备"));
		return;
	}
	if (!bReady) { Finish(EGGYGONiagaraMaterialPreparationState::Failed, MoveTemp(Reason)); return; }
	for (const FPreparedMaterial& Item : Work->RenderRead)
	{
		if (!Work->WorldResources->Ready.ContainsByPredicate([&Item](const FPreparedMaterial& Other) { return Other.Matches(Item); }))
		{ Work->WorldResources->Ready.Add(Item); }
	}
	Finish(EGGYGONiagaraMaterialPreparationState::Ready, FString());
}

void UGGYGONiagaraMaterialPreparation::Finish(EGGYGONiagaraMaterialPreparationState NewState, FString Reason)
{
	if (State != EGGYGONiagaraMaterialPreparationState::Pending) { return; }
	State = NewState;
	Error = MoveTemp(Reason);
	// 每个请求只有一次终态，按请求寿命记一条 Verbose 时序；失败原因仍由消费者按自身契约报错。
	const UWorld* World = RequestedWorld.Get();
	UE_LOG(LogGGYGONiagaraPreparation, Verbose,
		TEXT("[Rendering/NiagaraPreparation] Request=%s Owner=%s State=%s StartFrame=%llu EndFrame=%llu StartWorldSeconds=%.6f EndWorldSeconds=%.6f Reason=%s"),
		*GetPathName(), *GetPathNameSafe(GetOuter()),
		*StaticEnum<EGGYGONiagaraMaterialPreparationState>()->GetNameStringByValue(static_cast<int64>(State)),
		static_cast<unsigned long long>(StartFrame), static_cast<unsigned long long>(GFrameCounter),
		StartWorldSeconds, World ? World->GetTimeSeconds() : -1.0, *Error);
	Detach();
	OnFinished.Broadcast(this);
}

void UGGYGONiagaraMaterialPreparation::Cancel()
{
	check(IsInGameThread());
	Finish(EGGYGONiagaraMaterialPreparationState::Cancelled, TEXT("调用方取消原材质准备请求"));
}

void UGGYGONiagaraMaterialPreparation::OnTimeout()
{
	Finish(EGGYGONiagaraMaterialPreparationState::Failed,
		FString::Printf(TEXT("原 Niagara 材质准备超过 %.0f 秒：%s；未以默认材质或 PSO 状态代替 Ready"),
			PreparationTimeoutSeconds, Work ? *Work->WaitingOn : TEXT("尚未收到原资源结果")));
}

void UGGYGONiagaraMaterialPreparation::OnWorldCleanup(UWorld* World, bool, bool)
{
	if (World == RequestedWorld.Get(true)) { Finish(EGGYGONiagaraMaterialPreparationState::Cancelled, TEXT("原 World 正在退出")); }
}

void UGGYGONiagaraMaterialPreparation::Detach()
{
	FWorldDelegates::OnWorldCleanup.Remove(WorldCleanupHandle);
	WorldCleanupHandle.Reset();
	if (UWorld* World = RequestedWorld.Get()) { World->GetTimerManager().ClearTimer(TimeoutHandle); }
#if WITH_EDITOR
	if (AssetCompiledHandle.IsValid()) { FAssetCompilingManager::Get().OnAssetPostCompileEvent().Remove(AssetCompiledHandle); }
	if (MaterialCompiledHandle.IsValid()) { UMaterial::OnMaterialCompilationFinished().Remove(MaterialCompiledHandle); }
	AssetCompiledHandle.Reset();
	MaterialCompiledHandle.Reset();
	if (Work)
	{
		for (const auto& Item : Work->SystemCompiledHandles)
		{
			if (UNiagaraSystem* System = Item.Key.Get()) { System->OnSystemCompiled().Remove(Item.Value); }
		}
		Work->SystemCompiledHandles.Reset();
	}
#endif
	RetainedInputs.Reset();
	RequestedComponents.Reset();
	if (Work)
	{
		Work->Bindings.Reset();
		Work->RenderRead.Reset();
		Work->WorldResources.Reset();
	}
	// Work 由对象释放：Finish 可在 Advance 的原生返栈中发生，不能使其作用域引用悬空。
}

void UGGYGONiagaraMaterialPreparation::BeginDestroy()
{
	if (State == EGGYGONiagaraMaterialPreparationState::Pending)
	{
		State = EGGYGONiagaraMaterialPreparationState::Cancelled;
		Error = TEXT("材质准备拥有者已释放");
	}
	Detach();
	Super::BeginDestroy();
}
