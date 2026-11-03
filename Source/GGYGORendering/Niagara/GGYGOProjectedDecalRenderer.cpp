/** @file GGYGOProjectedDecalRenderer.cpp
 *  @brief 原CPU帧生产逐粒子MID，原生Decal负责投影/裁剪/受光；首错交回原FX生命周期。
 */
#include "GGYGOProjectedDecalRenderer.h"
#include "GGYGOProjectedDecalRendererProperties.h"
#include "GGYGOFXRendererFailureReceiver.h"

#include "NiagaraComponent.h"
#include "NiagaraEmitterInstance.h"
#include "NiagaraSystem.h"
#include "NiagaraSystemInstance.h"
#include "Async/Async.h"
#include "Engine/World.h"
#include "Materials/Material.h"
#include "Materials/MaterialInstance.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Misc/ScopeLock.h"
#include "RenderingThread.h"
#include "RHICommandList.h"
#include "SceneProxies/DeferredDecalProxy.h"
#include "UObject/StrongObjectPtr.h"

DEFINE_LOG_CATEGORY_STATIC(LogGGYGOProjectedDecal, Log, All);

struct FGGYGOProjectedDecalRenderer::FPayload
{
	TWeakObjectPtr<UMaterialInterface> SourceMaterial;
	TArray<TStrongObjectPtr<UMaterialInstanceDynamic>> Materials;
	TArray<uint32> ParticleIndices;
	int32 TickCount = 0;
	uint32 DataCount = 0;
	float SimulationAge = 0;
};

namespace
{
	void DispatchFailure(TWeakObjectPtr<UNiagaraComponent> Component, TWeakObjectPtr<UNiagaraSystem> System,
		uint64 InstanceId, FString Source, FString Error)
	{
		auto Report = [Component, System, InstanceId, Source = MoveTemp(Source), Error = MoveTemp(Error)]()
		{
			UNiagaraComponent* Owner = Component.Get();
			UNiagaraSystem* Asset = System.Get();
			UE_LOG(LogGGYGOProjectedDecal, Error, TEXT("[ProjectedDecal] %s instance=%llu: %s"), *Source, InstanceId, *Error);
			if (IsValid(Owner) && IsValid(Asset))
				if (auto* Receiver = Cast<IGGYGOFXRendererFailureReceiver>(Owner))
					Receiver->ReportFXRendererFailure(Asset, InstanceId, Source, Error);
		};
		if (IsInGameThread()) Report();
		else AsyncTask(ENamedThreads::GameThread, MoveTemp(Report));
	}

	// MID不能以MID为Parent；原动态覆盖仍须完整复制，不换成资产初值。
	UMaterialInterface* ResolveParent(UMaterialInterface* Source, FString& Error)
	{
		UMaterialInterface* NewParent = nullptr;
		TSet<const UMaterialInterface*> Seen;
		for (UMaterialInterface* Current = Source; Current; )
		{
			if (!IsValid(Current) || Seen.Contains(Current) || Current->HasAnyFlags(RF_NeedLoad | RF_NeedPostLoad))
			{ Error = TEXT("原投影材质父链未就绪、无效或循环"); return nullptr; }
			Seen.Add(Current);
			if (!NewParent && !Current->IsA<UMaterialInstanceDynamic>()) NewParent = Current;
			if (UMaterialInstance* Instance = Cast<UMaterialInstance>(Current))
			{ Current = Instance->Parent; continue; }
			UMaterial* Base = Cast<UMaterial>(Current);
			if (!Base || Base->MaterialDomain != MD_DeferredDecal)
			{ Error = TEXT("原投影材质必须有真实DeferredDecal父材质"); return nullptr; }
			return NewParent;
		}
		Error = TEXT("原投影材质缺父，不接受默认材质");
		return nullptr;
	}
}

FGGYGOProjectedDecalRenderer::FGGYGOProjectedDecalRenderer(ERHIFeatureLevel::Type InFeatureLevel,
	const UGGYGOProjectedDecalRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter)
	: FNiagaraRendererDecals(InFeatureLevel, Properties->NativeDecal.Get(), Emitter)
{
	if (const FNiagaraSystemInstance* Instance = Emitter ? Emitter->GetParentSystemInstance() : nullptr)
	{
		OriginalComponent = Cast<UNiagaraComponent>(Instance->GetAttachComponent());
		OriginalSystem = Instance->GetSystem();
		OriginalInstanceId = static_cast<uint64>(Instance->GetId());
	}
}

void FGGYGOProjectedDecalRenderer::ReportCreationFailure(const FNiagaraEmitterInstance* Emitter,
	const FString& SourceReference, const FString& Reason)
{
	const FNiagaraSystemInstance* Instance = Emitter ? Emitter->GetParentSystemInstance() : nullptr;
	DispatchFailure(Instance ? Cast<UNiagaraComponent>(Instance->GetAttachComponent()) : nullptr,
		Instance ? Instance->GetSystem() : nullptr, Instance ? static_cast<uint64>(Instance->GetId()) : 0,
		SourceReference, Reason);
}

FGGYGOProjectedDecalRenderer::~FGGYGOProjectedDecalRenderer()
{
	RetirePayload();
}

void FGGYGOProjectedDecalRenderer::RetirePayload() const
{
	TSharedPtr<FPayload, ESPMode::ThreadSafe> Retired;
	TSharedPtr<FPayload, ESPMode::ThreadSafe> RetiredSubmitted;
	{
		FScopeLock Guard(&PayloadLock);
		Retired = MoveTemp(Payload);
		RetiredSubmitted = MoveTemp(SubmittedPayload);
	}
	if (Retired || RetiredSubmitted)
	{
		// 原生proxy移除/材质更新在前；RT标记之后才可在GT释放最后的UObject强引用。
		ENQUEUE_RENDER_COMMAND(GGYGORetireProjectedDecalPayload)(
			[Retired = MoveTemp(Retired), RetiredSubmitted = MoveTemp(RetiredSubmitted)](FRHICommandListBase&) mutable
		{
			AsyncTask(ENamedThreads::GameThread,
				[Retired = MoveTemp(Retired), RetiredSubmitted = MoveTemp(RetiredSubmitted)]() {});
		});
	}
}

void FGGYGOProjectedDecalRenderer::ReportFailure(const FString& SourceReference, const FString& Reason) const
{
	if (bFailureReported.exchange(true)) return;
	const auto Component = OriginalComponent;
	const auto System = OriginalSystem;
	const uint64 InstanceId = OriginalInstanceId;
	const FString Source = SourceReference, Error = Reason;
	ReleaseAllDecals();
	RetirePayload();
	// 报告可同步结束原NS/销毁Renderer，返栈后不再读写this或释放后继资源。
	DispatchFailure(Component, System, InstanceId, Source, Error);
}

void FGGYGOProjectedDecalRenderer::PostSystemTick_GameThread(
	const UNiagaraRendererProperties* InProperties, const FNiagaraEmitterInstance* Emitter)
{
	check(IsInGameThread());
	if (bFailureReported.load()) return;
	const auto* Properties = Cast<UGGYGOProjectedDecalRendererProperties>(InProperties);
	FString Error;
	if (!Properties || !IsValid(Properties->NativeDecal))
	{ ReportFailure(GetPathNameSafe(Properties), TEXT("原payload属性类型或Native子对象无效")); return; }
	const UNiagaraDecalRendererProperties* Native = Properties->NativeDecal.Get();
	const FString Source = Properties->SourceReference;
	const FNiagaraSystemInstance* Instance = Emitter ? Emitter->GetParentSystemInstance() : nullptr;
	if (!Instance || !OriginalComponent.IsValid() || !OriginalSystem.IsValid()
		|| !OriginalComponent->IsRegistered() || !OriginalComponent->GetWorld()
		|| OriginalComponent->GetWorld()->bIsTearingDown || Instance->GetWorld() != OriginalComponent->GetWorld()
		|| Instance->GetAttachComponent() != OriginalComponent.Get() || Instance->GetSystem() != OriginalSystem.Get()
		|| static_cast<uint64>(Instance->GetId()) != OriginalInstanceId
		|| (Instance->GetWorld()->IsGameWorld() && !Cast<IGGYGOFXRendererFailureReceiver>(OriginalComponent.Get())))
	{ ReportFailure(Source, TEXT("原投影NS/World/System/实例或首错接收接口已失效")); return; }
	const FNiagaraDataSet& DataSet = Emitter->GetParticleData();
	const FNiagaraDataBuffer* Data = DataSet.GetCurrentData();
	if (!Data || Data->GetNumInstances() == 0
		|| !Properties->GetIsEnabled() || !Native->GetIsEnabled()
		|| !IsRendererEnabled(Properties, Emitter) || !IsRendererEnabled(Native, Emitter))
	{
		// 与Native Decal相同的真实无绘制分支；不将坏绑定/坏数据也归为此分支。
		ReleaseAllDecals();
		RetirePayload();
		return;
	}
	if (!Properties->ValidateCompiledPayloadLayout(Error))
	{ ReportFailure(Source, Error); return; }
	for (const auto& Accessor : Properties->VectorAccessors)
		if (!Accessor.IsValid() || !Accessor.GetReader(Data).IsValid())
		{ ReportFailure(Source, TEXT("原投影float4属性缺失或类型不符")); return; }
	const auto PositionReader = Native->PositionDataSetAccessor.GetReader(Data);
	const auto RotationReader = Native->DecalOrientationDataSetAccessor.GetReader(Data);
	const auto SizeReader = Native->DecalSizeDataSetAccessor.GetReader(Data);
	if (!PositionReader.IsValid() || !RotationReader.IsValid() || !SizeReader.IsValid())
	{ ReportFailure(Source, TEXT("原投影几何属性缺本次CPU数据，未采用Native默认几何")); return; }
	// 必需帧无效不能经Visible=false变成成功；源零体积可用有限零尺寸正常不画。
	for (uint32 Index = 0; Index < Data->GetNumInstances(); ++Index)
	{
		const int32 ParticleIndex = static_cast<int32>(Index);
		const FVector3f Position = PositionReader.Get(ParticleIndex);
		const FQuat4f Rotation = RotationReader.Get(ParticleIndex);
		const FVector3f Size = SizeReader.Get(ParticleIndex);
		if (Position.ContainsNaN() || Rotation.ContainsNaN() || Size.ContainsNaN()
			|| Rotation.SizeSquared() <= UE_SMALL_NUMBER)
		{ ReportFailure(Source, TEXT("原投影几何包含非有限值或退化旋转")); return; }
		for (const auto& Accessor : Properties->VectorAccessors)
			if (Accessor.GetReader(Data).Get(ParticleIndex).ContainsNaN())
			{ ReportFailure(Source, TEXT("原投影payload含非有限值，不能经不可见过滤静默跳过")); return; }
	}
	UMaterialInterface* Material = BaseMaterials_GT.Num() == 1 ? BaseMaterials_GT[0] : nullptr;
	UMaterialInterface* Parent = ResolveParent(Material, Error);
	if (!Parent) { ReportFailure(Source, Error); return; }
	FLinearColor Vector;
	for (const FName Parameter : Properties->MaterialVectorParameters)
		if (!Material->GetVectorParameterValue(FHashedMaterialParameterInfo(Parameter), Vector))
		{ ReportFailure(Source, FString::Printf(TEXT("原投影材质缺vector %s"), *Parameter.ToString())); return; }
	float Scalar;
	if (!Properties->SimulationAgeParameter.IsNone()
		&& !Material->GetScalarParameterValue(FHashedMaterialParameterInfo(Properties->SimulationAgeParameter), Scalar))
	{ ReportFailure(Source, TEXT("原投影材质缺明确Age标量")); return; }
	const float Age = Instance->GetAge();
	if (!FMath::IsFinite(Age) || Age < 0)
	{ ReportFailure(Source, TEXT("原投影实例年龄无效")); return; }
	const FNiagaraParameterStore& Parameters = Emitter->GetRendererBoundVariables();
	const bool DefaultVisible = Parameters.GetParameterValueOrDefault(
		Native->DecalVisibleBinding.GetParamMapBindableVariable(), UNiagaraDecalRendererProperties::GetDefaultDecalVisible()).GetValue();
	const int32 DefaultTag = Parameters.GetParameterValueOrDefault(
		Native->RendererVisibilityTagBinding.GetParamMapBindableVariable(), Native->RendererVisibility);
	const auto VisibleReader = Native->DecalVisibleAccessor.GetReader(DataSet);
	const auto TagReader = Native->RendererVisibilityTagAccessor.GetReader(DataSet);
	if (!VisibleReader.IsValid() || !Native->DecalSortOrderDataSetAccessor.GetReader(DataSet).IsValid())
	{ ReportFailure(Source, TEXT("原投影可见度/整数排序缺本次CPU数据，未用默认值替代")); return; }
	TSharedPtr<FPayload, ESPMode::ThreadSafe> Next = MakeShareable(new FPayload(), [](FPayload* Value)
	{
		if (IsInGameThread()) delete Value;
		else AsyncTask(ENamedThreads::GameThread, [Value]() { delete Value; });
	});
	Next->SourceMaterial = Material;
	Next->TickCount = Instance->GetTickCount();
	Next->SimulationAge = Age;
	Next->DataCount = Data->GetNumInstances();
	for (uint32 Index = 0; Index < Data->GetNumInstances(); ++Index)
		if (VisibleReader.GetSafe(Index, FNiagaraBool(DefaultVisible)).GetValue()
			&& TagReader.GetSafe(Index, DefaultTag) == Native->RendererVisibility)
			Next->ParticleIndices.Add(Index);
	if (Next->ParticleIndices.Num() > Properties->MaxMaterialInstances)
	{ ReportFailure(Source, TEXT("实际可见投影超过明确MID容量，不截断粒子")); return; }
	// 全批先验证；复用MID仍可能被Scene中的上一帧代理持有，坏值不能写入半份参数。
	TArray<TArray<FVector4f>> Values;
	Values.SetNum(Next->ParticleIndices.Num());
	for (int32 Slot = 0; Slot < Next->ParticleIndices.Num(); ++Slot)
	{
		const int32 ParticleIndex = static_cast<int32>(Next->ParticleIndices[Slot]);
		for (const auto& Accessor : Properties->VectorAccessors)
		{
			const FVector4f Value = Accessor.GetReader(Data).Get(ParticleIndex);
			Values[Slot].Add(Value);
		}
	}
	TSharedPtr<FPayload, ESPMode::ThreadSafe> Previous;
	{
		FScopeLock Guard(&PayloadLock);
		Previous = Payload;
	}
	for (int32 Slot = 0; Slot < Next->ParticleIndices.Num(); ++Slot)
	{
		UMaterialInstanceDynamic* MID = Previous && Previous->SourceMaterial.Get() == Material
			&& Previous->Materials.IsValidIndex(Slot) ? Previous->Materials[Slot].Get() : nullptr;
		if (!MID) MID = UMaterialInstanceDynamic::Create(Parent, OriginalComponent.Get());
		if (!MID) { ReportFailure(Source, TEXT("原投影私有MID创建失败")); return; }
		MID->SetFlags(RF_Transient | RF_DuplicateTransient);
		Next->Materials.Emplace(MID);
	}
	// 参数复制/创建后核原租用，原FX回调不得令此帧安装后继的资源。
	if (!OriginalComponent.IsValid() || !OriginalComponent->IsRegistered()
		|| Instance->GetSystem() != OriginalSystem.Get() || static_cast<uint64>(Instance->GetId()) != OriginalInstanceId)
	{ ReportFailure(Source, TEXT("投影payload准备期间原实例已归还")); return; }
	for (int32 Slot = 0; Slot < Next->Materials.Num(); ++Slot)
	{
		UMaterialInstanceDynamic* MID = Next->Materials[Slot].Get();
		MID->CopyMaterialUniformParameters(Material);
		for (int32 Field = 0; Field < Properties->MaterialVectorParameters.Num(); ++Field)
		{
			const FVector4f& Value = Values[Slot][Field];
			MID->SetVectorParameterValue(Properties->MaterialVectorParameters[Field], FLinearColor(Value.X, Value.Y, Value.Z, Value.W));
		}
		if (!Properties->SimulationAgeParameter.IsNone())
			MID->SetScalarParameterValue(Properties->SimulationAgeParameter, Age);
	}
	{
		FScopeLock Guard(&PayloadLock);
		Payload = MoveTemp(Next);
	}
}

FNiagaraDynamicDataBase* FGGYGOProjectedDecalRenderer::GenerateDynamicData(const FNiagaraSceneProxy* Proxy,
	const UNiagaraRendererProperties* InProperties, const FNiagaraEmitterInstance* Emitter) const
{
	if (bFailureReported.load()) return nullptr;
	const auto* Properties = Cast<UGGYGOProjectedDecalRendererProperties>(InProperties);
	const FNiagaraSystemInstance* Instance = Emitter ? Emitter->GetParentSystemInstance() : nullptr;
	const UNiagaraDecalRendererProperties* Native = Properties ? Properties->NativeDecal.Get() : nullptr;
	if (!Native || !Instance) { ReportFailure(GetPathNameSafe(Properties), TEXT("原投影Renderer/实例缺失")); return nullptr; }
	if (!Emitter->GetParticleData().GetCurrentData()
		|| Emitter->GetParticleData().GetCurrentData()->GetNumInstances() == 0
		|| !Properties->GetIsEnabled() || !Native->GetIsEnabled()
		|| !IsRendererEnabled(Properties, Emitter) || !IsRendererEnabled(Native, Emitter))
	{
		ReleaseAllDecals();
		RetirePayload();
		return nullptr;
	}
	TSharedPtr<FPayload, ESPMode::ThreadSafe> Frame;
	{
		FScopeLock Guard(&PayloadLock);
		Frame = Payload;
	}
	if (!Frame || static_cast<uint64>(Instance->GetId()) != OriginalInstanceId
		|| Instance->GetSystem() != OriginalSystem.Get() || Frame->TickCount != Instance->GetTickCount()
		|| Frame->SimulationAge != Instance->GetAge()
		|| Frame->DataCount != Emitter->GetParticleData().GetCurrentData()->GetNumInstances()
		|| BaseMaterials_GT.Num() != 1 || Frame->SourceMaterial.Get() != BaseMaterials_GT[0])
	{ ReportFailure(Properties->SourceReference, TEXT("本次Native投影缺同一原tick的真实payload，未沿用上一帧")); return nullptr; }
	// 原生路径拥有代理创建/更新/裁剪/释放；返回nullptr是Native Decal的正常接口。
	FNiagaraRendererDecals::GenerateDynamicData(Proxy, Native, Emitter);
	if (ActiveDecalProxies.Num() != Frame->Materials.Num())
	{ ReportFailure(Properties->SourceReference, TEXT("原生可见投影与同帧payload数目不一致")); return nullptr; }
	const TArray<FDeferredDecalProxy*> Proxies = ActiveDecalProxies;
	TSharedPtr<FPayload, ESPMode::ThreadSafe> PreviousSubmitted;
	{
		FScopeLock Guard(&PayloadLock);
		PreviousSubmitted = MoveTemp(SubmittedPayload);
		SubmittedPayload = Frame;
	}
	ENQUEUE_RENDER_COMMAND(GGYGOApplyProjectedDecalMaterials)(
		[Proxies, Frame = MoveTemp(Frame), PreviousSubmitted = MoveTemp(PreviousSubmitted)](FRHICommandListBase&)
	{
		for (int32 Index = 0; Index < Proxies.Num(); ++Index)
			Proxies[Index]->DecalMaterial = Frame->Materials[Index].Get();
	});
	return nullptr;
}

void FGGYGOProjectedDecalRenderer::OnSystemComplete_GameThread(const UNiagaraRendererProperties* Properties,
	const FNiagaraEmitterInstance* Emitter)
{
	check(IsInGameThread());
	ReleaseAllDecals();
	RetirePayload();
	FNiagaraRendererDecals::OnSystemComplete_GameThread(Properties, Emitter);
}

void FGGYGOProjectedDecalRenderer::DestroyRenderState_Concurrent()
{
	FNiagaraRendererDecals::DestroyRenderState_Concurrent();
	RetirePayload();
}
