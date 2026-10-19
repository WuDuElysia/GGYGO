/** @file GGYGOPlayerActionObservation.cpp @brief 消费原动作历史、退出及 FX 有限事实，不调度被观察对象。 */
#include "GGYGOPlayerActionObservation.h"

#include "AbilitySystem/Abilities/GGYGOPlayerComboAbility.h"
#include "AbilitySystem/GGYGOAbilitySystemComponent.h"
#include "AbilitySystem/Tasks/GGYGOAbilityTask_PlayMontageAndWaitForEvent.h"
#include "Character/Components/GGYGOCharacterMovementComponent.h"
#include "Animation/AnimMontage.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/World.h"
#include "FX/GGYGOMontageFXPublication.h"
#include "GameFramework/Pawn.h"
#include "NiagaraComponent.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/Package.h"

namespace GGYGOPlayerActionObservation
{
	FString RequestKind(EGGYGOAbilityTerminationRequestKind Kind)
	{
		switch (Kind)
		{
		case EGGYGOAbilityTerminationRequestKind::End: return TEXT("End");
		case EGGYGOAbilityTerminationRequestKind::Cancel: return TEXT("Cancel");
		default: return TEXT("None");
		}
	}

	TSharedPtr<FJsonObject> History(const FGGYGOPlayerComboObservationFacts& Facts)
	{
		auto Result = MakeShared<FJsonObject>();
		Result->SetBoolField(TEXT("task_natural_ended"), Facts.bTaskNaturalEnded);
		Result->SetBoolField(TEXT("ga_consumer_accepted"), Facts.bConsumerAccepted);
		Result->SetBoolField(TEXT("cmc_drain_request_returned"), Facts.bDrainRequestReturned);
		Result->SetBoolField(TEXT("cmc_drain_accepted"), Facts.bDrainAccepted);
		Result->SetBoolField(TEXT("source_current_after_drain_return"), Facts.bSourceCurrentAfterDrainReturn);
		Result->SetBoolField(TEXT("cmc_drain_completed"), Facts.bMotionCompleted);
		Result->SetBoolField(TEXT("original_cleanup_observed"), Facts.bCleanupObserved);
		Result->SetBoolField(TEXT("original_cleanup_cancelled"), Facts.bCleanupCancelled);
		Result->SetStringField(TEXT("original_cleanup_kind"), RequestKind(Facts.CleanupKind));
		Result->SetStringField(TEXT("cmc_drain_diagnostic"), Facts.DrainDiagnostic);
		return Result;
	}

	bool NaturalConsumerHistory(const FGGYGOPlayerComboObservationFacts& Facts)
	{
		return Facts.bTaskNaturalEnded && Facts.bConsumerAccepted && Facts.bDrainRequestReturned
			&& Facts.bDrainAccepted && Facts.bMotionCompleted && Facts.bCleanupObserved
			&& !Facts.bCleanupCancelled && Facts.CleanupKind == EGGYGOAbilityTerminationRequestKind::End;
	}

	FString FXKind(EGGYGOMontageFXObservationKind Kind)
	{
		switch (Kind)
		{
		case EGGYGOMontageFXObservationKind::Snapshot: return TEXT("Snapshot");
		case EGGYGOMontageFXObservationKind::Published: return TEXT("Published");
		case EGGYGOMontageFXObservationKind::TerminalDispatched: return TEXT("TerminalDispatched");
		case EGGYGOMontageFXObservationKind::TerminalReceived: return TEXT("TerminalReceived");
		case EGGYGOMontageFXObservationKind::RemoteCreated: return TEXT("RemoteCreated");
		case EGGYGOMontageFXObservationKind::ResourceChanged: return TEXT("ResourceChanged");
		case EGGYGOMontageFXObservationKind::TailTransferred: return TEXT("TailTransferred");
		case EGGYGOMontageFXObservationKind::NaturalCompleted: return TEXT("NaturalCompleted");
		case EGGYGOMontageFXObservationKind::ComponentUnregistered: return TEXT("ComponentUnregistered");
		case EGGYGOMontageFXObservationKind::ComponentDestroyed: return TEXT("ComponentDestroyed");
		case EGGYGOMontageFXObservationKind::PublisherClosed: return TEXT("PublisherClosed");
		}
		checkNoEntry();
		return TEXT("Invalid");
	}
}

struct UGGYGOPlayerActionObservation::FState
{
	FGGYGOPlayerComboObservation Observation;
	/** 仅用于精确解除／匹配本窗订阅，不用来重新解析后继。 */
	TWeakObjectPtr<UGGYGOAbilitySystemComponent> ASC;
	TWeakObjectPtr<UWorld> World;
	FDelegateHandle TerminationHandle;
	FDelegateHandle WorldCleanupHandle;
	FDelegateHandle EndPIEHandle;
	TSharedPtr<FJsonObject> Source;
	TSharedPtr<FJsonObject> LastHistory;
	TArray<TSharedPtr<FJsonValue>> Records;
	FString TrialId;
	FString StopReason;
	int32 MaxRecords = 0;
	double LastElapsedSeconds = -1.0;
	bool bActive = false;
	bool bOriginalExitCompleted = false;
	bool bExitCancelled = false;
	EGGYGOAbilityTerminationRequestKind ExitKind = EGGYGOAbilityTerminationRequestKind::None;
	bool bNaturalConsumerHistory = false;
	/** 精确原 FX view 是唯一收件资源；Runtime 只向它写值，不回调本观察对象。 */
	TSharedPtr<FGGYGOMontageFXObservation> FXWindow;
	TWeakObjectPtr<UAbilitySystemComponent> FXIssuer;
	TWeakObjectPtr<UGGYGOMontageFXPublicationOwner> FXPublisher;
	TWeakObjectPtr<AActor> FXAvatar;
	TWeakObjectPtr<USkeletalMeshComponent> FXMesh;
	TSet<TTuple<uint64, uint64>> FXKeys;
	uint64 FXRegistration = 0;
	uint32 FXIssuerId = 0;
	uint32 FXWorldId = 0;
	uint32 FXAvatarId = 0;
	uint32 FXMeshId = 0;
	bool bFX = false;
	bool bEvidenceIncomplete = false;
	FString FXDiagnostic;
};

UGGYGOPlayerActionObservation* UGGYGOPlayerActionObservation::CreateObservation()
{
	check(IsInGameThread());
	return NewObject<UGGYGOPlayerActionObservation>(GetTransientPackage(), NAME_None, RF_Transient);
}

bool UGGYGOPlayerActionObservation::BeginFXObservation(UAbilitySystemComponent* Issuer,
	APawn* Pawn, USkeletalMeshComponent* Mesh, const FString& TrialId, int32 MaxRecords, FString& OutDiagnostic)
{
	check(IsInGameThread());
	OutDiagnostic.Reset();
	if (State.IsValid() || HasAnyFlags(RF_ClassDefaultObject | RF_BeginDestroyed | RF_FinishDestroyed)
		|| !IsValid(Issuer) || !IsValid(Pawn) || !IsValid(Mesh)
		|| Issuer->HasAnyFlags(RF_ClassDefaultObject) || !IsValid(Pawn->GetWorld()) || !Pawn->GetWorld()->IsGameWorld()
		|| Mesh->GetOwner() != Pawn || Mesh->GetWorld() != Pawn->GetWorld()
		|| Issuer->GetWorld() != Pawn->GetWorld() || Issuer->GetAvatarActor() != Pawn
		|| TrialId.TrimStartAndEnd().IsEmpty() || MaxRecords < 1 || MaxRecords > 4096)
	{
		OutDiagnostic = TEXT("[FX.Observation] 须一对象一窗、原 ASC/Avatar/Mesh/World、非空 trial 及有限容量。");
		return false;
	}
	const TWeakObjectPtr<UAbilitySystemComponent> OriginalIssuer(Issuer);
	const TWeakObjectPtr<APawn> OriginalPawn(Pawn);
	const TWeakObjectPtr<USkeletalMeshComponent> OriginalMesh(Mesh);
	IGGYGOMontageFXHost* Host = Cast<IGGYGOMontageFXHost>(Issuer);
	UGGYGOMontageFXPublicationOwner* Publisher = Host ? Host->GetMontageFXPublicationOwner() : nullptr;
	if (OriginalIssuer.Get() != Issuer || OriginalPawn.Get() != Pawn || OriginalMesh.Get() != Mesh
		|| !IsValid(Publisher) || Publisher->GetRegistrationSerial() == 0
		|| Issuer->GetAvatarActor() != Pawn || Mesh->GetOwner() != Pawn || Mesh->GetWorld() != Pawn->GetWorld())
	{
		OutDiagnostic = TEXT("[FX.Observation] 原 ASC 没有实际注册的 FX publisher。");
		return false;
	}
	const auto Window = Publisher->BeginObservation(MaxRecords, OutDiagnostic);
	if (!Window.IsValid()) { return false; }
	State = MakeShared<FState>();
	State->bFX = true;
	State->bActive = true;
	State->FXWindow = Window;
	State->FXIssuer = Issuer;
	State->FXPublisher = Publisher;
	State->FXRegistration = Publisher->GetRegistrationSerial();
	State->FXIssuerId = Issuer->GetUniqueID();
	State->FXWorldId = Pawn->GetWorld()->GetUniqueID();
	State->FXAvatarId = Pawn->GetUniqueID();
	State->FXMeshId = Mesh->GetUniqueID();
	State->FXAvatar = Pawn;
	State->FXMesh = Mesh;
	State->World = Pawn->GetWorld();
	State->TrialId = TrialId;
	State->MaxRecords = MaxRecords;
	State->Source = MakeShared<FJsonObject>();
	for (const auto& Item : {TPair<const TCHAR*, UObject*>(TEXT("issuer"), Issuer),
		{TEXT("publisher"), Publisher}, {TEXT("world"), Pawn->GetWorld()}, {TEXT("pawn"), Pawn}, {TEXT("mesh"), Mesh}})
	{
		State->Source->SetStringField(Item.Key, Item.Value->GetPathName());
		State->Source->SetStringField(FString(Item.Key) + TEXT("_id"), LexToString(Item.Value->GetUniqueID()));
	}
	State->Source->SetStringField(TEXT("owner_registration"), LexToString(State->FXRegistration));
	State->Source->SetNumberField(TEXT("local_role_at_begin"), static_cast<uint8>(Pawn->GetLocalRole()));
	State->Source->SetNumberField(TEXT("net_mode"), static_cast<uint8>(Pawn->GetWorld()->GetNetMode()));
	State->Source->SetBoolField(TEXT("local_ga_required"), false);
	State->WorldCleanupHandle = FWorldDelegates::OnWorldCleanup.AddUObject(this, &ThisClass::OnWorldCleanup);
	State->EndPIEHandle = FEditorDelegates::EndPIE.AddUObject(this, &ThisClass::OnEndPIE);
	return true;
}

bool UGGYGOPlayerActionObservation::BeginObservation(UGGYGOPlayerComboAbility* Ability,
	UGGYGOAbilitySystemComponent* ASC, APawn* Pawn, USkeletalMeshComponent* Mesh, UAnimMontage* Montage,
	const FString& TrialId, int32 MaxRecords, FString& OutDiagnostic)
{
	check(IsInGameThread());
	OutDiagnostic.Reset();
	if (State.IsValid() || HasAnyFlags(RF_ClassDefaultObject | RF_BeginDestroyed | RF_FinishDestroyed)
		|| !IsValid(Ability) || Ability->HasAnyFlags(RF_ClassDefaultObject)
		|| !IsValid(ASC) || !IsValid(Pawn) || !IsValid(Mesh) || !IsValid(Montage)
		|| TrialId.TrimStartAndEnd().IsEmpty() || MaxRecords < 1 || MaxRecords > 4096)
	{
		OutDiagnostic = TEXT("[Combat.Observation] 一对象一窗；须实际实例／明确原 pin、trial 和有限容量。");
		return false;
	}
	// 不以 class／CDO 或 ActiveCount 猜原实例；同 Spec 必须是这个实际主实例且仅一个实例。
	const FGameplayAbilitySpecHandle SpecHandle = Ability->GetCurrentAbilitySpecHandle();
	const FGameplayAbilitySpec* Spec = ASC->FindAbilitySpecFromHandle(SpecHandle);
	const TArray<UGameplayAbility*> Instances = Spec ? Spec->GetAbilityInstances() : TArray<UGameplayAbility*>();
	if (!Spec || Spec->GetPrimaryInstance() != Ability || Instances.Num() != 1 || Instances[0] != Ability)
	{
		OutDiagnostic = TEXT("[Combat.Observation] 原 Spec／实际唯一实例不属于所给 ASC，拒绝歧义。");
		return false;
	}
	FGGYGOPlayerComboObservation Observation;
	FGGYGOMontageSectionSnapshot InitialSnapshot;
	FGGYGOPlayerComboObservationFacts Facts;
	if (!Ability->CaptureOriginalStepObservation(Observation, InitialSnapshot, OutDiagnostic)
		|| !Observation.ReadHistory(Facts)) { return false; }
	if (Facts.Ability.Get() != Ability || Facts.ASC.Get() != ASC || Facts.Pawn.Get() != Pawn
		|| Facts.Mesh.Get() != Mesh || Facts.Montage.Get() != Montage
		|| Facts.World.Get() != Pawn->GetWorld() || Mesh->GetWorld() != Pawn->GetWorld()
		|| !Facts.World.IsValid() || !Facts.World->IsGameWorld())
	{
		OutDiagnostic = TEXT("[Combat.Observation] 原源与实际 Pawn／Mesh／World／Montage pin 不同。");
		return false;
	}
	State = MakeShared<FState>();
	State->Observation = Observation;
	State->ASC = ASC;
	State->World = Facts.World;
	State->TrialId = TrialId;
	State->MaxRecords = MaxRecords;
	State->Source = MakeShared<FJsonObject>();
	State->Source->SetStringField(TEXT("ability"), Ability->GetPathName());
	State->Source->SetStringField(TEXT("ability_class"), Ability->GetClass()->GetPathName());
	State->Source->SetStringField(TEXT("ability_spec_handle"), SpecHandle.ToString());
	State->Source->SetStringField(TEXT("asc"), ASC->GetPathName());
	State->Source->SetStringField(TEXT("pawn"), Pawn->GetPathName());
	State->Source->SetStringField(TEXT("mesh"), Mesh->GetPathName());
	State->Source->SetStringField(TEXT("world"), Facts.World->GetPathName());
	State->Source->SetStringField(TEXT("task"), Facts.Task->GetPathName());
	State->Source->SetStringField(TEXT("montage"), Montage->GetPathName());
	State->Source->SetStringField(TEXT("cmc"), Facts.Movement->GetPathName());
	State->Source->SetStringField(TEXT("step_token"), LexToString(Facts.StepToken));
	State->Source->SetNumberField(TEXT("step_index"), Facts.StepIndex);
	State->Source->SetNumberField(TEXT("montage_instance_id"), Facts.MontageInstanceId);
	State->Source->SetNumberField(TEXT("cmc_motion_handle"), Facts.MotionHandle);
	State->Source->SetBoolField(TEXT("original_native_source_authenticated"), true);
	State->LastHistory = GGYGOPlayerActionObservation::History(Facts);
	State->bNaturalConsumerHistory = GGYGOPlayerActionObservation::NaturalConsumerHistory(Facts);
	State->bActive = true;
	State->TerminationHandle = ASC->OnAbilityTerminationCompleted().AddUObject(this,
		&ThisClass::OnOriginalTerminationCompleted);
	State->WorldCleanupHandle = FWorldDelegates::OnWorldCleanup.AddUObject(this, &ThisClass::OnWorldCleanup);
	State->EndPIEHandle = FEditorDelegates::EndPIE.AddUObject(this, &ThisClass::OnEndPIE);
	return true;
}

bool UGGYGOPlayerActionObservation::Sample(double ElapsedSeconds, FString& OutDiagnostic)
{
	check(IsInGameThread());
	OutDiagnostic.Reset();
	const auto Original = State;
	if (!Original.IsValid() || !Original->bActive || !FMath::IsFinite(ElapsedSeconds)
		|| ElapsedSeconds < 0.0 || ElapsedSeconds < Original->LastElapsedSeconds)
	{
		OutDiagnostic = TEXT("[Combat.Observation] 无活动原窗或宿主单调时间无效。");
		return false;
	}
	if (Original->bFX) { return SampleFX(ElapsedSeconds, OutDiagnostic); }
	FGGYGOPlayerComboObservationFacts Facts;
	if (!Original->Observation.ReadHistory(Facts))
	{
		OutDiagnostic = TEXT("[Combat.Observation] 原历史视图无效。");
		ReleaseObservation(TEXT("OriginalHistoryUnavailable"));
		return false;
	}
	FGGYGOMontageSectionSnapshot Snapshot;
	FString LiveDiagnostic;
	UGGYGOPlayerComboAbility* Ability = Facts.Ability.Get();
	bool bResourceSourceCurrent = false;
	const bool bLive = Ability && Ability->ReadOriginalStepObservation(Original->Observation, Snapshot, LiveDiagnostic,
		&bResourceSourceCurrent);
	if (!Ability) { LiveDiagnostic = TEXT("原 GA 已退役，仅保留原历史。"); }
	auto Record = MakeShared<FJsonObject>();
	Record->SetNumberField(TEXT("elapsed_seconds"), ElapsedSeconds);
	Record->SetBoolField(TEXT("live_original_snapshot_available"), bLive);
	Record->SetBoolField(TEXT("original_ga_resource_source_current"), bResourceSourceCurrent);
	Record->SetStringField(TEXT("live_diagnostic"), LiveDiagnostic);
	if (bLive)
	{
		Record->SetStringField(TEXT("section"), Snapshot.SectionName.ToString());
		Record->SetNumberField(TEXT("position_seconds"), Snapshot.PositionSeconds);
		Record->SetNumberField(TEXT("raw_instance_rate"), Snapshot.InstancePlayRate);
	}
	Original->LastHistory = GGYGOPlayerActionObservation::History(Facts);
	Original->bNaturalConsumerHistory = GGYGOPlayerActionObservation::NaturalConsumerHistory(Facts);
	Record->SetObjectField(TEXT("original_history"), Original->LastHistory);
	Record->SetBoolField(TEXT("original_ga_full_exit_completed"), Original->bOriginalExitCompleted);
	Original->Records.Add(MakeShared<FJsonValueObject>(Record));
	Original->LastElapsedSeconds = ElapsedSeconds;
	if (!bResourceSourceCurrent && !Facts.bCleanupObserved) { ReleaseObservation(TEXT("OriginalSourceInvalidated")); }
	else if (Original->Records.Num() >= Original->MaxRecords) { ReleaseObservation(TEXT("RecordLimitReached")); }
	return true;
}

bool UGGYGOPlayerActionObservation::AppendFXFacts(const TArray<FGGYGOMontageFXObservationFact>& Facts,
	double ElapsedSeconds, FString& OutDiagnostic)
{
	const auto Original = State;
	for (const FGGYGOMontageFXObservationFact& Fact : Facts)
	{
		if (Fact.Publisher != Original->FXPublisher || Fact.Issuer != Original->FXIssuer || Fact.World != Original->World
			|| Fact.IssuerObjectId != Original->FXIssuerId
			|| Fact.WorldObjectId != Original->FXWorldId || Fact.OwnerRegistration != Original->FXRegistration)
		{
			OutDiagnostic = TEXT("[FX.Observation] 收件事实不属于原 issuer/publisher/World/registration。");
			return false;
		}
		bool bAssociationKnown = false;
		bool bUnassociatedTerminal = false;
		if (Fact.Occurrence != 0)
		{
			const TTuple<uint64, uint64> Key(Fact.Occurrence, Fact.Generation);
			const bool bOriginalMesh = Fact.Avatar == Original->FXAvatar && Fact.Mesh == Original->FXMesh
				&& Fact.AvatarObjectId == Original->FXAvatarId && Fact.MeshObjectId == Original->FXMeshId;
			const bool bKnownReleasedKey = Original->FXKeys.Contains(Key)
				&& Fact.AvatarObjectId == 0 && Fact.MeshObjectId == 0;
			// 终结只认证原 ASC/Occurrence；记录未到或引用未映射时，保留但不归入本 Pawn 的资源键。
			bUnassociatedTerminal = Fact.bHasTerminal && Fact.AvatarObjectId == 0 && Fact.MeshObjectId == 0
				&& !bOriginalMesh && !bKnownReleasedKey;
			if (!bOriginalMesh && !bKnownReleasedKey && !bUnassociatedTerminal) { continue; }
			bAssociationKnown = bOriginalMesh || bKnownReleasedKey;
			if (bAssociationKnown) { Original->FXKeys.Add(Key); }
		}
		if (Original->Records.Num() >= Original->MaxRecords)
		{
			OutDiagnostic = TEXT("[FX.Observation] Editor 值记录容量溢出；本窗证据不完整。");
			return false;
		}
		if ((Fact.bControllerAgeValid && !FMath::IsFinite(Fact.ControllerAge))
			|| (Fact.bTargetAgeValid && !FMath::IsFinite(Fact.TargetAge))
			|| (Fact.bDesiredAgeValid && !FMath::IsFinite(Fact.DesiredAge))
			|| (Fact.bHasRecord && !FMath::IsFinite(Fact.BeginServerTime))
			|| !FMath::IsFinite(Fact.EffectiveStep) || !FMath::IsFinite(Fact.RemoteSeekDeltaSeconds)
			|| !FMath::IsFinite(Fact.RemoteMaxSimTimeSeconds))
		{
			OutDiagnostic = TEXT("[FX.Observation] 原事实的时间或配置含非有限值。");
			return false;
		}
		auto Row = MakeShared<FJsonObject>();
		Row->SetStringField(TEXT("kind"), GGYGOPlayerActionObservation::FXKind(Fact.Kind));
		Row->SetStringField(TEXT("native_event_frame"), LexToString(Fact.NativeFrame));
		Row->SetStringField(TEXT("drain_frame"), LexToString(GFrameCounter));
		Row->SetBoolField(TEXT("host_elapsed_known"), ElapsedSeconds >= 0.0);
		if (ElapsedSeconds >= 0.0) { Row->SetNumberField(TEXT("drain_host_elapsed_seconds"), ElapsedSeconds); }
		Row->SetStringField(TEXT("occurrence"), LexToString(Fact.Occurrence));
		Row->SetStringField(TEXT("generation"), LexToString(Fact.Generation));
		Row->SetStringField(TEXT("state_revision"), LexToString(Fact.StateRevision));
		Row->SetBoolField(TEXT("publisher_context_only"), Fact.Occurrence == 0);
		Row->SetBoolField(TEXT("avatar_mesh_association_known"), bAssociationKnown);
		Row->SetBoolField(TEXT("terminal_without_record_association"), bUnassociatedTerminal);
		Row->SetBoolField(TEXT("has_record"), Fact.bHasRecord);
		Row->SetBoolField(TEXT("active_record"), Fact.bActiveRecord);
		Row->SetBoolField(TEXT("has_terminal"), Fact.bHasTerminal);
		if (Fact.bHasTerminal)
		{
			Row->SetStringField(TEXT("terminal_occurrence"), LexToString(Fact.Terminal.Occurrence));
			Row->SetStringField(TEXT("close_revision"), LexToString(Fact.Terminal.CloseRevision));
			Row->SetStringField(TEXT("close_reason"), Fact.Terminal.Reason == EGGYGOMontageFXCloseReason::Normal ? TEXT("Normal") : TEXT("Abort"));
		}
		Row->SetStringField(TEXT("component"), Fact.ComponentPath);
		Row->SetStringField(TEXT("component_id"), LexToString(Fact.ComponentObjectId));
		Row->SetBoolField(TEXT("component_identity_known"), Fact.ComponentObjectId != 0);
		Row->SetStringField(TEXT("avatar"), Fact.AvatarPath);
		Row->SetStringField(TEXT("avatar_id"), LexToString(Fact.AvatarObjectId));
		Row->SetStringField(TEXT("mesh"), Fact.MeshPath);
		Row->SetStringField(TEXT("mesh_id"), LexToString(Fact.MeshObjectId));
		Row->SetStringField(TEXT("system"), Fact.SystemPath);
		Row->SetBoolField(TEXT("component_weak_valid_at_drain"), Fact.Component.IsValid());
		Row->SetStringField(TEXT("controller_id"), LexToString(Fact.ControllerId));
		Row->SetBoolField(TEXT("controller_valid"), Fact.bControllerValid);
		Row->SetBoolField(TEXT("controller_age_valid"), Fact.bControllerAgeValid);
		if (Fact.bControllerAgeValid) { Row->SetNumberField(TEXT("controller_age"), Fact.ControllerAge); }
		Row->SetBoolField(TEXT("target_age_valid"), Fact.bTargetAgeValid);
		if (Fact.bTargetAgeValid) { Row->SetNumberField(TEXT("target_age"), Fact.TargetAge); }
		Row->SetBoolField(TEXT("desired_age_valid"), Fact.bDesiredAgeValid);
		if (Fact.bDesiredAgeValid) { Row->SetNumberField(TEXT("desired_age"), Fact.DesiredAge); }
		if (Fact.bHasRecord) { Row->SetNumberField(TEXT("begin_server_time"), Fact.BeginServerTime); }
		Row->SetNumberField(TEXT("effective_step"), Fact.EffectiveStep);
		Row->SetNumberField(TEXT("remote_seek_delta_seconds"), Fact.RemoteSeekDeltaSeconds);
		Row->SetNumberField(TEXT("remote_max_sim_time_seconds"), Fact.RemoteMaxSimTimeSeconds);
		Row->SetNumberField(TEXT("actual_execution_state"), Fact.ActualExecutionState);
		Row->SetNumberField(TEXT("requested_execution_state"), Fact.RequestedExecutionState);
		Row->SetBoolField(TEXT("controller_complete"), Fact.bControllerComplete);
		Row->SetBoolField(TEXT("controller_pending_spawn"), Fact.bControllerPendingSpawn);
		Row->SetBoolField(TEXT("remote_entry"), Fact.bRemoteEntry);
		Row->SetBoolField(TEXT("reached"), Fact.bReached);
		Row->SetBoolField(TEXT("rendering_enabled"), Fact.bRenderingEnabled);
		Row->SetBoolField(TEXT("registered"), Fact.bRegistered);
		const bool bResourceStateKnown = bAssociationKnown && Fact.bRemoteEntry;
		Row->SetBoolField(TEXT("resource_state_known"), bResourceStateKnown);
		if (bResourceStateKnown)
		{
			Row->SetBoolField(TEXT("release_requested"), Fact.bReleaseRequested);
			Row->SetBoolField(TEXT("held_resource_released"), Fact.bReleased);
			Row->SetNumberField(TEXT("operations"), Fact.Operations);
		}
		const bool bComponentFactsKnown = Fact.ComponentObjectId != 0
			|| Fact.Kind == EGGYGOMontageFXObservationKind::TailTransferred
			|| Fact.Kind == EGGYGOMontageFXObservationKind::NaturalCompleted
			|| Fact.Kind == EGGYGOMontageFXObservationKind::ComponentUnregistered
			|| Fact.Kind == EGGYGOMontageFXObservationKind::ComponentDestroyed;
		Row->SetBoolField(TEXT("component_facts_known"), bComponentFactsKnown);
		if (bComponentFactsKnown)
		{
			Row->SetBoolField(TEXT("tail_transferred"), Fact.bTailTransferred);
			Row->SetBoolField(TEXT("natural_completion"), Fact.bNaturalCompletion);
			Row->SetBoolField(TEXT("component_destroyed"), Fact.bComponentDestroyed);
			Row->SetBoolField(TEXT("presentation_failed"), Fact.bFailed);
		}
		Original->Records.Add(MakeShared<FJsonValueObject>(Row));
	}
	return true;
}

bool UGGYGOPlayerActionObservation::SampleFX(double ElapsedSeconds, FString& OutDiagnostic)
{
	const auto Original = State;
	UGGYGOMontageFXPublicationOwner* Publisher = Original->FXPublisher.Get();
	UAbilitySystemComponent* Issuer = Original->FXIssuer.Get();
	USkeletalMeshComponent* Mesh = Original->FXMesh.Get();
	const bool bOriginalContext = IsValid(Issuer) && Original->World.IsValid() && Original->FXAvatar.IsValid()
		&& IsValid(Mesh) && Issuer->GetAvatarActor() == Original->FXAvatar.Get()
		&& Issuer->GetWorld() == Original->World.Get() && Mesh->GetWorld() == Original->World.Get()
		&& Mesh->GetOwner() == Original->FXAvatar.Get();
	const bool bCaptured = bOriginalContext && IsValid(Publisher) && Publisher->CaptureObservation(Original->FXWindow, OutDiagnostic);
	if (!bOriginalContext || !IsValid(Publisher))
	{
		OutDiagnostic = TEXT("[FX.Observation] 原 issuer/publisher/Avatar/Mesh/World 已退役或换源；只排空已采原事实。");
	}
	TArray<FGGYGOMontageFXObservationFact> Facts;
	FString DrainDiagnostic;
	const bool bDrained = Original->FXWindow->Drain(Facts, DrainDiagnostic);
	FString AppendDiagnostic;
	const bool bAppended = AppendFXFacts(Facts, ElapsedSeconds, AppendDiagnostic);
	Original->LastElapsedSeconds = ElapsedSeconds;
	if (!bCaptured || !bDrained || !bAppended)
	{
		Original->bEvidenceIncomplete = true;
		Original->FXDiagnostic = OutDiagnostic + TEXT(" ") + DrainDiagnostic + TEXT(" ") + AppendDiagnostic;
		OutDiagnostic = Original->FXDiagnostic;
		ReleaseObservation(TEXT("FXObservationFailed"));
		return false;
	}
	if (Original->Records.Num() >= Original->MaxRecords) { ReleaseObservation(TEXT("RecordLimitReached")); }
	return true;
}

void UGGYGOPlayerActionObservation::OnOriginalTerminationCompleted(const FGGYGOAbilityTerminationCompletedNotice& Notice)
{
	const auto Original = State;
	FGGYGOPlayerComboObservationFacts Facts;
	if (!Original.IsValid() || !Original->bActive || !Notice.HasCompletion()
		|| !Original->Observation.ReadHistory(Facts)
		|| !Notice.GetOriginal().GetOriginalActivation().HasSameActivation(Facts.Activation)) { return; }
	Original->bOriginalExitCompleted = true;
	Original->ExitKind = Notice.GetOriginal().GetRequestKind();
	Original->bExitCancelled = Notice.GetOriginal().WasCancelled();
	// 完整退出可早于原 CMC 外调返栈；保留订阅与视图，后继 Sample／Stop 读取真实返回事实。
}

void UGGYGOPlayerActionObservation::ReleaseObservation(const FString& Reason)
{
	const auto Original = State;
	if (!Original.IsValid() || !Original->bActive) { return; }
	if (Original->FXWindow.IsValid())
	{
		TArray<FGGYGOMontageFXObservationFact> Facts;
		FString Diagnostic;
		const bool bDrained = Original->FXWindow->Drain(Facts, Diagnostic);
		FString AppendDiagnostic;
		if (!AppendFXFacts(Facts, -1.0, AppendDiagnostic) || !bDrained)
		{
			Original->bEvidenceIncomplete = true;
			Original->FXDiagnostic += TEXT(" ") + Diagnostic + TEXT(" ") + AppendDiagnostic;
		}
		Original->FXWindow->Stop();
		Original->FXWindow.Reset();
		Original->FXKeys.Reset();
		Original->FXIssuer.Reset();
		Original->FXPublisher.Reset();
		Original->FXAvatar.Reset();
		Original->FXMesh.Reset();
	}
	FGGYGOPlayerComboObservationFacts Facts;
	if (Original->Observation.ReadHistory(Facts))
	{
		Original->LastHistory = GGYGOPlayerActionObservation::History(Facts);
		Original->bNaturalConsumerHistory = GGYGOPlayerActionObservation::NaturalConsumerHistory(Facts);
	}
	const auto ASC = Original->ASC;
	const auto TerminationHandle = Original->TerminationHandle;
	const auto WorldHandle = Original->WorldCleanupHandle;
	const auto EndPIEHandle = Original->EndPIEHandle;
	// 先摘除本窗状态，再解除精确自有句柄；返栈不重绑另一对象或新窗口。
	Original->bActive = false;
	Original->StopReason = Reason;
	Original->TerminationHandle.Reset();
	Original->WorldCleanupHandle.Reset();
	Original->EndPIEHandle.Reset();
	Original->Observation.Reset();
	Original->ASC.Reset();
	Original->World.Reset();
	if (ASC.IsValid() && TerminationHandle.IsValid()) { ASC->OnAbilityTerminationCompleted().Remove(TerminationHandle); }
	if (WorldHandle.IsValid()) { FWorldDelegates::OnWorldCleanup.Remove(WorldHandle); }
	if (EndPIEHandle.IsValid()) { FEditorDelegates::EndPIE.Remove(EndPIEHandle); }
}

void UGGYGOPlayerActionObservation::StopObservation()
{
	check(IsInGameThread());
	ReleaseObservation(TEXT("StoppedByCaller"));
}

void UGGYGOPlayerActionObservation::OnWorldCleanup(UWorld* World, bool bSessionEnded, bool bCleanupResources)
{
	if (State.IsValid() && State->bActive && State->World == TWeakObjectPtr<UWorld>(World))
	{
		ReleaseObservation(TEXT("OriginalWorldCleanup"));
	}
}

void UGGYGOPlayerActionObservation::OnEndPIE(bool bSimulating)
{
	ReleaseObservation(TEXT("EndPIE"));
}

void UGGYGOPlayerActionObservation::BeginDestroy()
{
	ReleaseObservation(TEXT("ObjectDestroyed"));
	Super::BeginDestroy();
}

FString UGGYGOPlayerActionObservation::GetObservationJson() const
{
	check(IsInGameThread());
	auto Result = MakeShared<FJsonObject>();
	Result->SetStringField(TEXT("schema"), TEXT("GGYGO.PlayerActionObservation/v1"));
	Result->SetBoolField(TEXT("has_window"), State.IsValid());
	Result->SetStringField(TEXT("meaning"), TEXT("仅固定原源与完成事实；软件键、姿态、音频、设备、联机另验。"));
	if (State.IsValid())
	{
		Result->SetStringField(TEXT("trial_id"), State->TrialId);
		Result->SetStringField(TEXT("observation_kind"), State->bFX ? TEXT("MontageFX") : TEXT("PlayerCombo"));
		Result->SetBoolField(TEXT("evidence_incomplete"), State->bEvidenceIncomplete);
		if (State->bFX)
		{
			Result->SetStringField(TEXT("fx_diagnostic"), State->FXDiagnostic);
			Result->SetBoolField(TEXT("fx_view_released"), !State->FXWindow.IsValid());
		}
		Result->SetBoolField(TEXT("active"), State->bActive);
		Result->SetStringField(TEXT("stop_reason"), State->StopReason);
		Result->SetNumberField(TEXT("record_limit"), State->MaxRecords);
		Result->SetNumberField(TEXT("record_count"), State->Records.Num());
		Result->SetObjectField(TEXT("original_source"), State->Source);
		if (!State->bFX)
		{
			Result->SetObjectField(TEXT("original_history"), State->LastHistory);
			Result->SetBoolField(TEXT("original_ga_full_exit_completed"), State->bOriginalExitCompleted);
			Result->SetBoolField(TEXT("original_exit_cancelled"), State->bExitCancelled);
			Result->SetStringField(TEXT("original_exit_kind"), GGYGOPlayerActionObservation::RequestKind(State->ExitKind));
			Result->SetBoolField(TEXT("natural_completion_history_complete"), State->bNaturalConsumerHistory
				&& State->bOriginalExitCompleted && !State->bExitCancelled
				&& State->ExitKind == EGGYGOAbilityTerminationRequestKind::End);
		}
		Result->SetBoolField(TEXT("subscriptions_released"), !State->TerminationHandle.IsValid()
			&& !State->WorldCleanupHandle.IsValid() && !State->EndPIEHandle.IsValid() && !State->FXWindow.IsValid());
		Result->SetArrayField(TEXT("records"), State->Records);
	}
	FString Json;
	if (!FJsonSerializer::Serialize(Result, TJsonWriterFactory<>::Create(&Json)))
	{
		return TEXT("{\"schema\":\"GGYGO.PlayerActionObservation/v1\",\"serialization_failed\":true}");
	}
	return Json;
}
