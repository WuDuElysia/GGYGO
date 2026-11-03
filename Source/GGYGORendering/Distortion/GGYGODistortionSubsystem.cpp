/** @file GGYGODistortionSubsystem.cpp
 *  @brief 由原 World 生命周期维护唯一配置和源登记，按 family 冻结材质及配置。
 */
#include "GGYGODistortionSubsystem.h"

#include "GGYGODistortionFieldComponent.h"
#include "GGYGODistortionProfile.h"
#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGODistortionViewExtension.h"
#include "GGYGOSignedFieldFamily.h"
#include "Components/PrimitiveComponent.h"
#include "Materials/MaterialInterface.h"
#endif
#include "Engine/World.h"

DEFINE_LOG_CATEGORY_STATIC(LogGGYGODistortion, Log, All);

bool UGGYGODistortionSubsystem::DoesSupportWorldType(EWorldType::Type WorldType) const
{
#if GGYGO_WITH_DISTORTION_FIELD
	return WorldType == EWorldType::Game || WorldType == EWorldType::PIE
		|| WorldType == EWorldType::Editor || WorldType == EWorldType::EditorPreview;
#else
	return false;
#endif
}

void UGGYGODistortionSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
#if GGYGO_WITH_DISTORTION_FIELD
	if (GetWorld()->GetNetMode() != NM_DedicatedServer)
	{
		ViewExtension = FSceneViewExtensions::NewExtension<FGGYGODistortionViewExtension>(this);
		bAcceptSources = true;
	}
#endif
}

void UGGYGODistortionSubsystem::Deinitialize()
{
	bAcceptSources = false;
	Sources.Reset();
	LastFailure.Reset();
	if (ViewExtension)
	{
#if GGYGO_WITH_DISTORTION_FIELD
		ViewExtension->DetachSubsystem();
#endif
		ViewExtension.Reset();
	}
	// 已提交 family 持有独立 snapshot；不会回读此 World 或注销后的组件。
	Super::Deinitialize();
}

bool UGGYGODistortionSubsystem::RegisterSource(UGGYGODistortionFieldComponent& Source, FString& OutReason)
{
	check(IsInGameThread());
#if !GGYGO_WITH_DISTORTION_FIELD
	OutReason = TEXT("本构建已显式关闭Distortion Field后端，不接收source登记");
	return false;
#else
	if (!bAcceptSources || Source.GetWorld() != GetWorld())
	{
		OutReason = TEXT("World 已停止接收 source 或 World 身份不符");
		return false;
	}
	UPrimitiveComponent* Primitive;
	TArray<UMaterialInterface*> Materials;
	if (!Source.ResolveFieldInputs(Primitive, Materials, OutReason))
	{
		return false;
	}
	for (const TWeakObjectPtr<UGGYGODistortionFieldComponent>& Entry : Sources)
	{
		const UGGYGODistortionFieldComponent* Existing = Entry.Get();
		if (Existing && Existing != &Source && Existing->Profile != Source.Profile)
		{
			OutReason = TEXT("同一 World 的 source 必须显式选择同一个公共 Profile");
			return false;
		}
	}
	Sources.AddUnique(&Source);
	LastFailure.Reset();
	OutReason.Reset();
	return true;
#endif
}

void UGGYGODistortionSubsystem::UnregisterSource(const UGGYGODistortionFieldComponent& Source)
{
	check(IsInGameThread());
	const int32 Removed = Sources.RemoveAll([&Source](const TWeakObjectPtr<UGGYGODistortionFieldComponent>& Entry)
	{
		return !Entry.IsValid() || Entry.Get() == &Source;
	});
	if (Removed > 0)
	{
		LastFailure.Reset();
	}
}

TSharedPtr<const FGGYGOSignedFieldSnapshot, ESPMode::ThreadSafe> UGGYGODistortionSubsystem::CreateFamilySnapshot()
{
	check(IsInGameThread());
#if GGYGO_WITH_DISTORTION_FIELD
	if (!bAcceptSources || Sources.IsEmpty())
	{
		return nullptr;
	}
	TArray<UMaterialInterface*> Materials;
	TArray<FGGYGOSignedFieldSource> RenderSources;
	UGGYGODistortionProfile* CommonProfile = nullptr;
	FString Failure;
	// 虚调用可能撤销原登记；遍历原列表副本，并在返回后检查该 source 仍被本 World 持有。
	const auto OriginalSources = Sources;
	for (const TWeakObjectPtr<UGGYGODistortionFieldComponent>& Entry : OriginalSources)
	{
		UGGYGODistortionFieldComponent* Source = Entry.Get();
		if (!Source)
		{
			continue;
		}
		if (Source->GetWorld() != GetWorld())
		{
			ReportFailure(TEXT("已登记的 source 不再属于原 World"));
			return nullptr;
		}
		UPrimitiveComponent* Primitive;
		TArray<UMaterialInterface*> SourceMaterials;
		if (!Source->ResolveFieldInputs(Primitive, SourceMaterials, Failure))
		{
			ReportFailure(Source->GetPathName() + TEXT(": ") + Failure);
			return nullptr;
		}
		if (!bAcceptSources || !Entry.IsValid() || !Sources.Contains(Entry))
		{
			ReportFailure(TEXT("冻结输入时原 source 登记已归还"));
			return nullptr;
		}
		if (CommonProfile && CommonProfile != Source->Profile)
		{
			ReportFailure(TEXT("World 内出现互相冲突的公共 Profile"));
			return nullptr;
		}
		CommonProfile = Source->Profile;
		FGGYGOSignedFieldSource& RenderSource = RenderSources.AddDefaulted_GetRef();
		RenderSource.Primitive = Primitive->GetPrimitiveSceneId();
		for (UMaterialInterface* Material : SourceMaterials)
		{
			Materials.AddUnique(Material);
			RenderSource.Materials.Add(Material->GetRenderProxy());
		}
	}
	if (!CommonProfile || Materials.IsEmpty())
	{
		// 全部 weak sources 自然消失是原生命周期结束。
		Sources.RemoveAll([](const TWeakObjectPtr<UGGYGODistortionFieldComponent>& Entry) { return !Entry.IsValid(); });
		return nullptr;
	}
	TOptional<FGGYGODistortionViewPolicy> Policy;
	FGGYGODistortionViewPolicy Candidate;
	if (!CommonProfile->TryBuildPolicy(Candidate, Failure))
	{
		Failure = CommonProfile->GetPathName() + TEXT(": ") + Failure;
		ReportFailure(Failure);
		// 已知原 proxy 仍发布为预期 field，阻止其跟随普通颜色 fallback。
		return MakeGGYGOSignedFieldSnapshot(MoveTemp(Policy), MoveTemp(RenderSources), Materials, Failure);
	}
	Policy.Emplace(MoveTemp(Candidate));
	LastFailure.Reset();
	return MakeGGYGOSignedFieldSnapshot(MoveTemp(Policy), MoveTemp(RenderSources), Materials, FString());
#else
	return nullptr;
#endif
}

void UGGYGODistortionSubsystem::ReportFailure(const FString& Failure)
{
	if (Failure != LastFailure)
	{
		UE_LOG(LogGGYGODistortion, Warning, TEXT("%s 未发布 field：%s"), *GetPathNameSafe(GetWorld()), *Failure);
		LastFailure = Failure;
	}
}
