/** @file GGYGOAnimationPoseObservationSubsystem.cpp @brief 记录自然 finalize、物理结果与原生源姿态，不驱动被观察对象。 */
#include "GGYGOAnimationPoseObservationSubsystem.h"
#include "GGYGOPlayerActionObservation.h"

#include "Animation/Runtime/GGYGOAnimInstanceBase.h"
#include "Character/Components/GGYGOCharacterMovementComponent.h"
#include "Abilities/GameplayAbility.h"
#include "AbilitySystemComponent.h"
#include "AbilitySystemGlobals.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AnimNode_AssetPlayerBase.h"
#include "Animation/AnimSequence.h"
#include "Animation/AttributesRuntime.h"
#include "BonePose.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/Engine.h"
#include "Engine/EngineTypes.h"
#include "Engine/NetDriver.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
#include "GameplayAbilitySpec.h"
#include "GameplayTagContainer.h"
#include "GameplayTask.h"
#include "GameplayTaskOwnerInterface.h"
#include "GameplayTasksComponent.h"
#include "HAL/PlatformTime.h"
#include "ProfilingDebugging/CpuProfilerTrace.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/UnrealType.h"

namespace GGYGOAnimationObservation
{
	TSharedPtr<FJsonObject> Transform(const FTransform& Value)
	{
		TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
		const FVector T = Value.GetTranslation();
		const FQuat Q = Value.GetRotation();
		const FVector S = Value.GetScale3D();
		Result->SetArrayField(TEXT("translation"), {MakeShared<FJsonValueNumber>(T.X), MakeShared<FJsonValueNumber>(T.Y), MakeShared<FJsonValueNumber>(T.Z)});
		Result->SetArrayField(TEXT("rotation"), {MakeShared<FJsonValueNumber>(Q.X), MakeShared<FJsonValueNumber>(Q.Y), MakeShared<FJsonValueNumber>(Q.Z), MakeShared<FJsonValueNumber>(Q.W)});
		Result->SetArrayField(TEXT("scale"), {MakeShared<FJsonValueNumber>(S.X), MakeShared<FJsonValueNumber>(S.Y), MakeShared<FJsonValueNumber>(S.Z)});
		return Result;
	}

	void SetSerial(const TSharedPtr<FJsonObject>& Object, const TCHAR* Name, uint64 Serial)
	{
		// JSON number 的常见 double 消费器不能准确承载全部 uint64。
		Object->SetStringField(Name, FString::Printf(TEXT("%llu"), Serial));
	}

	TSharedPtr<FJsonObject> NativeActionMotion(const FGGYGOActionMotionNativeObservation& Observation)
	{
		TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
		Result->SetNumberField(TEXT("status"), static_cast<uint8>(Observation.Status));
		Result->SetStringField(TEXT("diagnostic"), Observation.Diagnostic);
		const bool bAvailable = Observation.Status == EGGYGOActionMotionNativeObservationStatus::Available
			|| Observation.Status == EGGYGOActionMotionNativeObservationStatus::NoActionSource;
		Result->SetBoolField(TEXT("available"), bAvailable);
		// 不可用时不把默认时间、Identity 或空列表写成一次有效观察。
		if (!bAvailable) { return Result; }
		SetSerial(Result, TEXT("frame"), Observation.Frame);
		Result->SetNumberField(TEXT("world_time_seconds"), Observation.WorldTimeSeconds);
		Result->SetStringField(TEXT("world"), Observation.WorldPath);
		Result->SetStringField(TEXT("character"), Observation.CharacterPath);
		Result->SetStringField(TEXT("movement"), Observation.MovementPath);
		Result->SetNumberField(TEXT("local_role"), Observation.LocalRole);
		TArray<TSharedPtr<FJsonValue>> ActiveSources;
		TArray<TSharedPtr<FJsonValue>> PendingSources;
		for (const FGGYGOActionMotionNativeSourceObservation& Source : Observation.Sources)
		{
			TArray<TSharedPtr<FJsonValue>>& Sources = Source.Container == EGGYGOActionMotionNativeSourceContainer::Active
				? ActiveSources : PendingSources;
			Sources.Add(MakeShared<FJsonValueObject>(GGYGOPlayerActionObservation::NativeActionSource(Source)));
		}
		Result->SetArrayField(TEXT("active_sources"), ActiveSources);
		Result->SetArrayField(TEXT("pending_sources"), PendingSources);
		return Result;
	}

	TSharedPtr<FJsonObject> NetworkDriverLive(const UWorld& World)
	{
		TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
		SetSerial(Result, TEXT("live_frame"), GFrameCounter);
		Result->SetNumberField(TEXT("live_platform_seconds"), FPlatformTime::Seconds());
		Result->SetBoolField(TEXT("available"), false);
		Result->SetBoolField(TEXT("net_test_enabled"), DO_ENABLE_NET_TEST != 0);
		Result->SetStringField(TEXT("world"), World.GetPathName());
		Result->SetNumberField(TEXT("world_object_id"), World.GetUniqueID());
		const UNetDriver* Driver = World.GetNetDriver();
		if (!World.IsGameWorld() || !IsValid(Driver) || Driver->HasAnyFlags(RF_BeginDestroyed | RF_FinishDestroyed))
		{
			Result->SetStringField(TEXT("diagnostic"), TEXT("Original game World has no live primary NetDriver; incoming simulation settings are unavailable"));
			return Result;
		}
		Result->SetStringField(TEXT("driver"), Driver->GetPathName());
		Result->SetNumberField(TEXT("driver_object_id"), Driver->GetUniqueID());
		Result->SetStringField(TEXT("driver_name"), Driver->NetDriverName.ToString());
		Result->SetStringField(TEXT("driver_world"), GetPathNameSafe(Driver->GetWorld()));
		if (Driver->GetWorld() != &World)
		{
			Result->SetStringField(TEXT("diagnostic"), TEXT("Primary NetDriver does not belong to the original World"));
			return Result;
		}
		const bool bNamedDriverMatches = GEngine && !Driver->NetDriverName.IsNone()
			&& GEngine->FindNamedNetDriver(&World, Driver->NetDriverName) == Driver;
		Result->SetBoolField(TEXT("named_driver_matches"), bNamedDriverMatches);
		if (!bNamedDriverMatches)
		{
			Result->SetStringField(TEXT("diagnostic"), TEXT("Original World/NetDriverName does not resolve to this primary NetDriver; named command scope is unavailable"));
			return Result;
		}
#if DO_ENABLE_NET_TEST
		const FPacketSimulationSettings& Settings = Driver->PacketSimulationSettings;
		if (Settings.PktIncomingLagMin < 0 || Settings.PktIncomingLagMax < Settings.PktIncomingLagMin
			|| Settings.PktIncomingLoss < 0 || Settings.PktIncomingLoss > 100
			|| Settings.PktIncomingFrameDelay < 0 || Settings.PktIncomingBufferBloatInMS < 0)
		{
			Result->SetStringField(TEXT("diagnostic"), FString::Printf(TEXT("Invalid incoming simulation settings: Min=%d Max=%d Loss=%d FrameDelay=%d BufferBloatInMS=%d"),
				Settings.PktIncomingLagMin, Settings.PktIncomingLagMax, Settings.PktIncomingLoss,
				Settings.PktIncomingFrameDelay, Settings.PktIncomingBufferBloatInMS));
			return Result;
		}
		Result->SetBoolField(TEXT("available"), true);
		Result->SetStringField(TEXT("diagnostic"), TEXT(""));
		// 只读当前主 Driver 的公开配置，不检查或操作 connection 的延迟队列。
		Result->SetStringField(TEXT("scope"), TEXT("World primary NetDriver public incoming packet simulation settings at live_frame; not connection or delayed-packet queue state"));
		Result->SetNumberField(TEXT("incoming_lag_min_ms"), Settings.PktIncomingLagMin);
		Result->SetNumberField(TEXT("incoming_lag_max_ms"), Settings.PktIncomingLagMax);
		Result->SetNumberField(TEXT("incoming_loss_percent"), Settings.PktIncomingLoss);
		Result->SetNumberField(TEXT("incoming_frame_delay"), Settings.PktIncomingFrameDelay);
		Result->SetNumberField(TEXT("incoming_buffer_bloat_ms"), Settings.PktIncomingBufferBloatInMS);
#else
		Result->SetStringField(TEXT("diagnostic"), TEXT("DO_ENABLE_NET_TEST is disabled; incoming simulation settings are unavailable"));
#endif
		return Result;
	}

	TSharedPtr<FJsonObject> AbilitySystemLive(const ACharacter& Character)
	{
		TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
		SetSerial(Result, TEXT("live_frame"), GFrameCounter);
		Result->SetBoolField(TEXT("available"), false);
		Result->SetStringField(TEXT("pawn"), Character.GetPathName());
		Result->SetNumberField(TEXT("pawn_object_id"), Character.GetUniqueID());
		const ENetRole LocalRole = Character.GetLocalRole();
		const bool bLocallyControlled = Character.IsLocallyControlled();
		Result->SetNumberField(TEXT("local_role"), static_cast<uint8>(LocalRole));
		Result->SetBoolField(TEXT("locally_controlled"), bLocallyControlled);
		const UWorld* World = Character.GetWorld();
		Result->SetStringField(TEXT("world"), GetPathNameSafe(World));
		// 仅使用原 Pawn 的 ASC 接口，不搜索组件或猜测外部宿主。
		const UAbilitySystemComponent* ASC = UAbilitySystemGlobals::GetAbilitySystemComponentFromActor(&Character, false);
		if (!IsValid(ASC) || ASC->IsBeingDestroyed())
		{
			Result->SetStringField(TEXT("diagnostic"), TEXT("Original Pawn interface has no live ASC; task counts are unavailable"));
			return Result;
		}
		Result->SetStringField(TEXT("ability_system"), ASC->GetPathName());
		Result->SetNumberField(TEXT("ability_system_object_id"), ASC->GetUniqueID());
		Result->SetStringField(TEXT("owner_actor"), GetPathNameSafe(ASC->GetOwnerActor()));
		Result->SetStringField(TEXT("avatar_actor"), GetPathNameSafe(ASC->GetAvatarActor()));
		Result->SetStringField(TEXT("ability_system_world"), GetPathNameSafe(ASC->GetWorld()));
		if (!IsValid(World) || !World->IsGameWorld() || Character.IsActorBeingDestroyed()
			|| ASC->GetWorld() != World || ASC->GetAvatarActor() != &Character)
		{
			Result->SetStringField(TEXT("diagnostic"), TEXT("Original ASC World/Avatar does not match the observed Pawn scope; task counts are unavailable"));
			return Result;
		}
		// ActivatableAbilities 只对 Authority/Owner 可见；Sim 的空列表不是零资源证明。
		if (LocalRole != ROLE_Authority && (LocalRole != ROLE_AutonomousProxy || !bLocallyControlled))
		{
			Result->SetStringField(TEXT("diagnostic"), TEXT("ASC public spec/task observation requires Authority or the locally controlled AutonomousProxy; this role cannot certify empty lists"));
			return Result;
		}
		Result->SetBoolField(TEXT("available"), true);
		Result->SetStringField(TEXT("diagnostic"), TEXT(""));
		Result->SetStringField(TEXT("scope"), TEXT("Owner/Authority ASC public KnownTasks and activatable spec instances at live_frame; excludes private Ability.ActiveTasks and tasks not registered with this ASC"));
		TArray<TSharedPtr<FJsonValue>> Specs;
		TMap<const IGameplayTaskOwnerInterface*, TArray<TSharedPtr<FJsonValue>>> InstanceOwners;
		int32 UnreadInstances = 0;
		for (const FGameplayAbilitySpec& Spec : ASC->GetActivatableAbilities())
		{
			TSharedPtr<FJsonObject> SpecRow = MakeShared<FJsonObject>();
			const FString Handle = Spec.Handle.ToString();
			SpecRow->SetStringField(TEXT("spec_handle"), Handle);
			SpecRow->SetStringField(TEXT("ability"), GetPathNameSafe(Spec.Ability.Get()));
			SpecRow->SetBoolField(TEXT("active"), Spec.IsActive());
			TArray<TSharedPtr<FJsonValue>> Instances;
			for (const UGameplayAbility* Instance : Spec.GetAbilityInstances())
			{
				if (!IsValid(Instance)) { ++UnreadInstances; continue; }
				TSharedPtr<FJsonObject> InstanceRow = MakeShared<FJsonObject>();
				InstanceRow->SetStringField(TEXT("spec_handle"), Handle);
				InstanceRow->SetStringField(TEXT("instance"), Instance->GetPathName());
				InstanceRow->SetNumberField(TEXT("instance_object_id"), Instance->GetUniqueID());
				InstanceRow->SetStringField(TEXT("instance_class"), Instance->GetClass()->GetPathName());
				InstanceRow->SetBoolField(TEXT("active"), Instance->IsActive());
				TSharedPtr<FJsonValue> Value = MakeShared<FJsonValueObject>(InstanceRow);
				Instances.Add(Value);
				InstanceOwners.FindOrAdd(static_cast<const IGameplayTaskOwnerInterface*>(Instance)).Add(Value);
			}
			SpecRow->SetArrayField(TEXT("instances"), Instances);
			Specs.Add(MakeShared<FJsonValueObject>(SpecRow));
		}
		Result->SetArrayField(TEXT("specs"), Specs);
		Result->SetNumberField(TEXT("unread_ability_instance_count"), UnreadInstances);
		TSet<const UGameplayTask*> SeenTasks;
		TArray<TSharedPtr<FJsonValue>> Tasks;
		int32 UnreadTasks = 0;
		for (auto TaskIt = ASC->GetKnownTaskIterator(); TaskIt; ++TaskIt)
		{
			const UGameplayTask* Task = (*TaskIt).Get();
			if (!IsValid(Task)) { ++UnreadTasks; continue; }
			if (SeenTasks.Contains(Task)) { continue; }
			SeenTasks.Add(Task);
			TSharedPtr<FJsonObject> TaskRow = MakeShared<FJsonObject>();
			TaskRow->SetStringField(TEXT("task"), Task->GetPathName());
			TaskRow->SetNumberField(TEXT("task_object_id"), Task->GetUniqueID());
			TaskRow->SetStringField(TEXT("task_class"), Task->GetClass()->GetPathName());
			TaskRow->SetNumberField(TEXT("state"), static_cast<uint8>(Task->GetState()));
			TaskRow->SetBoolField(TEXT("finished"), Task->IsFinished());
			const IGameplayTaskOwnerInterface* Owner = Task->GetTaskOwner();
			TaskRow->SetBoolField(TEXT("has_task_owner"), Owner != nullptr);
			// 按真实接口指针匹配实例；Transient Outer 不承担能力归属证明。
			TArray<TSharedPtr<FJsonValue>> OwnerMatches;
			if (const auto* Matches = InstanceOwners.Find(Owner)) { OwnerMatches = *Matches; }
			TaskRow->SetArrayField(TEXT("owner_matches"), OwnerMatches);
			Tasks.Add(MakeShared<FJsonValueObject>(TaskRow));
		}
		Result->SetNumberField(TEXT("known_task_count"), SeenTasks.Num());
		Result->SetNumberField(TEXT("unread_known_task_count"), UnreadTasks);
		Result->SetArrayField(TEXT("known_tasks"), Tasks);
		TSharedPtr<FJsonObject> TagCounts = MakeShared<FJsonObject>();
		const FGameplayTagContainer Tags = ASC->GetOwnedGameplayTags().GetGameplayTagParents();
		for (const FGameplayTag Tag : Tags)
		{
			TagCounts->SetNumberField(Tag.ToString(), ASC->GetTagCount(Tag));
		}
		Result->SetObjectField(TEXT("tag_counts"), TagCounts);
		return Result;
	}

	TSharedPtr<FJsonObject> CameraTurn(const FGGYGOLocomotionSteeringSnapshot& Captured)
	{
		TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
		Result->SetNumberField(TEXT("status"), static_cast<uint8>(Captured.CameraTurnStatus));
		Result->SetStringField(TEXT("diagnostic"), Captured.CameraTurnDiagnostic);
		Result->SetBoolField(TEXT("remote"), Captured.bCameraTurnRemote);
		const bool bAvailable = Captured.CameraTurnStatus == EGGYGOLocomotionSteeringStatus::Valid;
		Result->SetBoolField(TEXT("available"), bAvailable);
		// Initial/NA/Invalid 只导出资格；不把默认余角或步态对写成真实零观测。
		if (!bAvailable) { return Result; }
		Result->SetNumberField(TEXT("demand_degrees"), Captured.CameraTurnDemandDegrees);
		Result->SetNumberField(TEXT("control_yaw_delta_degrees"), Captured.CameraControlYawDeltaDegrees);
		Result->SetNumberField(TEXT("gait"), static_cast<uint8>(Captured.CameraTurnGait));
		Result->SetNumberField(TEXT("walk_run_blend_alpha"), Captured.CameraTurnWalkRunBlendAlpha);
		Result->SetStringField(TEXT("original_movement"), GetPathNameSafe(Captured.OriginalMovement.Get()));
		Result->SetStringField(TEXT("original_character"), GetPathNameSafe(Captured.OriginalCharacter.Get()));
		Result->SetStringField(TEXT("original_updated_component"), GetPathNameSafe(Captured.OriginalUpdatedComponent.Get()));
		if (Captured.bCameraTurnRemote)
		{
			Result->SetNumberField(TEXT("publisher_epoch"), Captured.CameraTurnPublisherEpoch);
			Result->SetNumberField(TEXT("publication_serial"), Captured.CameraTurnPublicationSerial);
			// 样本键与本端接受帧都允许真实零；后者不是本机完成区间的证明。
			Result->SetNumberField(TEXT("native_sample_key"), Captured.CameraTurnNativeSampleKey);
			SetSerial(Result, TEXT("accepted_local_frame"), Captured.CameraTurnAcceptedLocalFrame);
		}
		else
		{
			SetSerial(Result, TEXT("source_epoch"), Captured.SourceEpoch);
			SetSerial(Result, TEXT("completed_interval_serial"), Captured.CompletedIntervalSerial);
			SetSerial(Result, TEXT("completed_frame"), Captured.CompletedFrame);
			Result->SetNumberField(TEXT("native_delta_seconds"), Captured.NativeDeltaSeconds);
		}
		return Result;
	}

	TSharedPtr<FJsonObject> Motion(const FGGYGOMotionExecutionSnapshot& Snapshot)
	{
		TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
		Result->SetNumberField(TEXT("status"), static_cast<uint8>(Snapshot.Status));
		Result->SetNumberField(TEXT("source_kind"), static_cast<uint8>(Snapshot.SourceKind));
		Result->SetNumberField(TEXT("rotation_mode"), static_cast<uint8>(Snapshot.RotationMode));
		Result->SetNumberField(TEXT("motion_type"), static_cast<uint8>(Snapshot.MotionType));
		Result->SetNumberField(TEXT("turn_back_phase"), static_cast<uint8>(Snapshot.TurnBackPhase));
		Result->SetNumberField(TEXT("end_reason"), static_cast<uint8>(Snapshot.EndReason));
		Result->SetStringField(TEXT("original_movement"), GetPathNameSafe(Snapshot.OriginalMovement.Get()));
		Result->SetStringField(TEXT("original_character"), GetPathNameSafe(Snapshot.OriginalCharacter.Get()));
		Result->SetStringField(TEXT("original_updated_component"), GetPathNameSafe(Snapshot.OriginalUpdatedComponent.Get()));
		SetSerial(Result, TEXT("request_serial"), Snapshot.ExecutionRequestSerial);
		SetSerial(Result, TEXT("completed_interval_serial"), Snapshot.CompletedIntervalSerial);
		SetSerial(Result, TEXT("completed_frame"), Snapshot.CompletedFrame);
		Result->SetNumberField(TEXT("motion_sequence"), Snapshot.MotionSequence);
		Result->SetNumberField(TEXT("action_handle"), Snapshot.ActionHandle);
		Result->SetNumberField(TEXT("native_delta_seconds"), Snapshot.NativeDeltaSeconds);
		Result->SetBoolField(TEXT("has_native_source_interval"), Snapshot.bHasNativeSourceInterval);
		Result->SetNumberField(TEXT("native_start_seconds"), Snapshot.NativeStartSeconds);
		Result->SetNumberField(TEXT("native_end_seconds"), Snapshot.NativeEndSeconds);
		Result->SetNumberField(TEXT("motion_start_seconds"), Snapshot.MotionStartSeconds);
		Result->SetNumberField(TEXT("motion_end_seconds"), Snapshot.MotionEndSeconds);
		Result->SetBoolField(TEXT("has_single_sequence_time"), Snapshot.bHasSingleSequenceTime);
		Result->SetStringField(TEXT("sequence"), GetPathNameSafe(Snapshot.OriginalSequence.Get()));
		Result->SetNumberField(TEXT("sequence_start_seconds"), Snapshot.SequenceStartSeconds);
		Result->SetNumberField(TEXT("sequence_end_seconds"), Snapshot.SequenceEndSeconds);
		Result->SetNumberField(TEXT("requested_yaw_delta_degrees"), Snapshot.RequestedYawDeltaDegrees);
		Result->SetBoolField(TEXT("curve_yaw_applied"), Snapshot.bCurveYawApplied);
		Result->SetObjectField(TEXT("actual_before"), Transform(FTransform(Snapshot.RotationBefore, Snapshot.LocationBefore)));
		Result->SetObjectField(TEXT("actual_after"), Transform(FTransform(Snapshot.RotationAfter, Snapshot.LocationAfter)));
		Result->SetStringField(TEXT("world_velocity"), Snapshot.WorldVelocity.ToString());
		Result->SetBoolField(TEXT("native_source_finished"), Snapshot.bNativeSourceFinished);
		Result->SetBoolField(TEXT("ended"), Snapshot.bEnded);
		Result->SetStringField(TEXT("diagnostic"), Snapshot.Diagnostic);
		TArray<TSharedPtr<FJsonValue>> Intervals;
		for (const FGGYGOActionMotionSourceInterval& Interval : Snapshot.SourceIntervals)
		{
			TSharedPtr<FJsonObject> Item = MakeShared<FJsonObject>();
			Item->SetNumberField(TEXT("binding_segment_index"), Interval.BindingSegmentIndex);
			Item->SetNumberField(TEXT("loop_index"), Interval.LoopIndex);
			Item->SetNumberField(TEXT("montage_start_seconds"), Interval.MontageStartSeconds);
			Item->SetNumberField(TEXT("montage_end_seconds"), Interval.MontageEndSeconds);
			Item->SetNumberField(TEXT("sequence_start_seconds"), Interval.SequenceStartSeconds);
			Item->SetNumberField(TEXT("sequence_end_seconds"), Interval.SequenceEndSeconds);
			Item->SetNumberField(TEXT("source_seconds_per_montage_second"), Interval.SourceSecondsPerMontageSecond);
			Intervals.Add(MakeShared<FJsonValueObject>(Item));
		}
		Result->SetArrayField(TEXT("source_intervals"), Intervals);
		return Result;
	}

	TSharedPtr<FJsonObject> SourcePose(UGGYGOAnimInstanceBase& Anim, USkeletalMeshComponent& Mesh,
		const TArray<FName>& BoneNames, bool bExtractRootMotion)
	{
		TRACE_CPUPROFILER_EVENT_SCOPE(GGYGOAnimationObservation_SourcePose);
		TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
		const FGGYGOAnimationMotionFrame& MotionFrame = Anim.GetAnimationStateFrame().MotionExecution;
		const FGGYGOAnimationRemotePoseFrame& Remote = Anim.GetRemoteMotionPoseFrame();
		Result->SetStringField(TEXT("scope"), TEXT("Standalone nonlooping SingleSequence bone pose at the Animation captured pose time (LocalExecution completed endpoint, or AuthorityReplicatedPose sample time in its TimeDomain) with current required bones and native root-lock extraction choice; no root-motion attributes, final blending or clock advancement"));
		// 两种来源分列：远端姿态不是本机执行事实，本机完成区间也不是远端显示姿态。
		Result->SetStringField(TEXT("pose_source"), Remote.bRemote ? TEXT("AuthorityReplicatedPose") : TEXT("LocalExecution"));
		UAnimSequence* Sequence = nullptr;
		double SequenceSeconds = 0.;
		if (Remote.bRemote)
		{
			Result->SetNumberField(TEXT("remote_time_domain"), Remote.TimeDomain);
			if (!Remote.bHasPose)
			{
				Result->SetStringField(TEXT("status"), TEXT("NotApplicable"));
				return Result;
			}
			Sequence = Remote.Sequence;
			SequenceSeconds = Remote.SequenceSeconds;
		}
		else
		{
			if (MotionFrame.Status != EGGYGOMotionExecutionStatus::Valid || !MotionFrame.bHasSingleSequenceTime)
			{
				Result->SetStringField(TEXT("status"), TEXT("NotApplicable"));
				return Result;
			}
			Sequence = MotionFrame.SingleSequence;
			SequenceSeconds = MotionFrame.SequenceEndSeconds;
		}
		const FBoneContainer& Bones = Anim.GetRequiredBones();
		if (!Sequence || !Bones.IsValid() || Sequence->GetSkeleton() != Bones.GetSkeletonAsset()
			|| Sequence->IsValidAdditive() || !FMath::IsFinite(SequenceSeconds)
			|| SequenceSeconds < 0. || SequenceSeconds > Sequence->GetPlayLength())
		{
			Result->SetStringField(TEXT("status"), TEXT("Failed"));
			Result->SetStringField(TEXT("diagnostic"), TEXT("Captured sequence, required-bone skeleton, nonadditive pose or endpoint is invalid; no substituted pose"));
			return Result;
		}
		FMemMark Mark(FMemStack::Get());
		FCompactPose Pose;
		Pose.SetBoneContainer(&Bones);
		Pose.ResetToRefPose();
		FBlendedCurve Curve;
		Curve.InitFrom(Bones);
		UE::Anim::FStackAttributeContainer Attributes;
		FAnimationPoseData PoseData(Pose, Curve, Attributes);
		Sequence->GetAnimationPose(PoseData, FAnimExtractContext(SequenceSeconds, bExtractRootMotion));
		FCSPose<FCompactPose> ComponentPose;
		ComponentPose.InitPose(MoveTemp(Pose));
		TSharedPtr<FJsonObject> BoneTransforms = MakeShared<FJsonObject>();
		for (FName Name : BoneNames)
		{
			const FCompactPoseBoneIndex Index = Bones.MakeCompactPoseIndex(FMeshPoseBoneIndex(Mesh.GetBoneIndex(Name)));
			if (!ComponentPose.GetPose().IsValidIndex(Index))
			{
				Result->SetStringField(TEXT("status"), TEXT("Failed"));
				Result->SetStringField(TEXT("diagnostic"), FString::Printf(TEXT("Required bone unavailable in sampled pose: %s"), *Name.ToString()));
				return Result;
			}
			const FTransform& BoneTransform = ComponentPose.GetComponentSpaceTransform(Index);
			if (BoneTransform.ContainsNaN())
			{
				Result->SetStringField(TEXT("status"), TEXT("Failed"));
				Result->SetStringField(TEXT("diagnostic"), FString::Printf(TEXT("Sampled source bone is nonfinite: %s"), *Name.ToString()));
				return Result;
			}
			BoneTransforms->SetObjectField(Name.ToString(), Transform(BoneTransform));
		}
		Result->SetStringField(TEXT("status"), TEXT("Sampled"));
		Result->SetStringField(TEXT("sequence"), GetPathNameSafe(Sequence));
		Result->SetNumberField(TEXT("sequence_seconds"), SequenceSeconds);
		Result->SetBoolField(TEXT("extract_root_motion"), bExtractRootMotion);
		Result->SetObjectField(TEXT("component_space_bones"), BoneTransforms);
		return Result;
	}
}

void UGGYGOAnimationPoseObservationSubsystem::Initialize(FSubsystemCollectionBase& Collection)
{
	Super::Initialize(Collection);
	EndPIEHandle = FEditorDelegates::EndPIE.AddUObject(this, &ThisClass::OnEndPIE);
}

void UGGYGOAnimationPoseObservationSubsystem::Deinitialize()
{
	if (FinalizedHandle.IsValid())
	{
		ReleaseObservation(TEXT("Deinitialized"));
	}
	FEditorDelegates::EndPIE.Remove(EndPIEHandle);
	EndPIEHandle.Reset();
	Super::Deinitialize();
}

bool UGGYGOAnimationPoseObservationSubsystem::BeginObservation(USkeletalMeshComponent* Mesh,
	const TArray<FName>& BoneNames, int32 MaxRecords, FString& OutDiagnostic)
{
	check(IsInGameThread());
	OutDiagnostic.Reset();
	ACharacter* Character = Mesh ? Cast<ACharacter>(Mesh->GetOwner()) : nullptr;
	UGGYGOAnimInstanceBase* Anim = Mesh ? Cast<UGGYGOAnimInstanceBase>(Mesh->GetAnimInstance()) : nullptr;
	UGGYGOCharacterMovementComponent* Movement = Character ? Cast<UGGYGOCharacterMovementComponent>(Character->GetCharacterMovement()) : nullptr;
	if (FinalizedHandle.IsValid() || !Mesh || !Mesh->GetWorld() || !Mesh->GetWorld()->IsGameWorld()
		|| !Mesh->GetSkeletalMeshAsset() || !Character || Character->GetMesh() != Mesh || !Anim || !Movement
		|| BoneNames.IsEmpty() || MaxRecords < 1 || MaxRecords > 4096)
	{
		OutDiagnostic = TEXT("[Animation.PoseObservation] Requires idle observer, original game-world Character Mesh/Anim/CMC, named bones and bounded capacity 1..4096.");
		return false;
	}
	TSet<FName> UniqueBones;
	for (FName Name : BoneNames)
	{
		if (Name.IsNone() || UniqueBones.Contains(Name) || Mesh->GetBoneIndex(Name) == INDEX_NONE)
		{
			OutDiagnostic = FString::Printf(TEXT("[Animation.PoseObservation] Mesh=%s invalid, repeated or missing bone=%s."), *Mesh->GetPathName(), *Name.ToString());
			return false;
		}
		UniqueBones.Add(Name);
	}
	ObservedMesh = Mesh;
	ObservedMeshAsset = Mesh->GetSkeletalMeshAsset();
	ObservedAnim = Anim;
	ObservedCharacter = Character;
	ObservedMovement = Movement;
	ObservedBoneNames = BoneNames;
	MeshPath = Mesh->GetPathName();
	RecordLimit = MaxRecords;
	Records.Reset();
	StopReason = TEXT("WaitingForNativeFinalize");
	FinalizedHandle = Mesh->RegisterOnBoneTransformsFinalizedDelegate(FOnBoneTransformsFinalizedMultiCast::FDelegate::CreateUObject(this, &ThisClass::OnBoneTransformsFinalized));
	if (!FinalizedHandle.IsValid())
	{
		OutDiagnostic = TEXT("[Animation.PoseObservation] Native Mesh finalize delegate registration failed.");
		ReleaseObservation(OutDiagnostic);
		return false;
	}
	return true;
}

void UGGYGOAnimationPoseObservationSubsystem::OnBoneTransformsFinalized()
{
	check(IsInGameThread());
	TRACE_CPUPROFILER_EVENT_SCOPE(GGYGOAnimationObservation_Finalize);
	USkeletalMeshComponent* Mesh = ObservedMesh.Get();
	UGGYGOAnimInstanceBase* Anim = ObservedAnim.Get();
	ACharacter* Character = ObservedCharacter.Get();
	UGGYGOCharacterMovementComponent* Movement = ObservedMovement.Get();
	if (!Mesh || !Anim || !Character || !Movement || Mesh->GetAnimInstance() != Anim
		|| Mesh->GetSkeletalMeshAsset() != ObservedMeshAsset.Get() || Mesh->GetOwner() != Character
		|| Character->GetMesh() != Mesh || Character->GetCharacterMovement() != Movement
		|| !Mesh->GetWorld() || !Mesh->GetWorld()->IsGameWorld())
	{
		ReleaseObservation(TEXT("OriginalIdentityInvalidated"));
		return;
	}
	TSharedPtr<FJsonObject> Record = MakeShared<FJsonObject>();
	Record->SetStringField(TEXT("phase"), TEXT("Mesh.BoneTransformsFinalized"));
	GGYGOAnimationObservation::SetSerial(Record, TEXT("observed_frame"), GFrameCounter);
	Record->SetStringField(TEXT("anim_instance"), Anim->GetPathName());
	Record->SetStringField(TEXT("character"), Character->GetPathName());
	Record->SetStringField(TEXT("movement"), Movement->GetPathName());
	Record->SetObjectField(TEXT("ability_system_live"), GGYGOAnimationObservation::AbilitySystemLive(*Character));
	Record->SetObjectField(TEXT("network_driver_live"), GGYGOAnimationObservation::NetworkDriverLive(*Mesh->GetWorld()));
	Record->SetNumberField(TEXT("root_motion_mode"), static_cast<uint8>(Anim->RootMotionMode));
	Record->SetBoolField(TEXT("mesh_is_playing_root_motion"), Mesh->IsPlayingRootMotion());
	Record->SetBoolField(TEXT("root_motion_from_everything"), Mesh->IsPlayingRootMotionFromEverything());
	Record->SetBoolField(TEXT("use_update_rate_optimizations"), Mesh->ShouldUseUpdateRateOptimizations());
	if (const FAnimUpdateRateParameters* Params = Mesh->AnimUpdateRateParams)
	{
		Record->SetBoolField(TEXT("skip_update"), Params->ShouldSkipUpdate());
		Record->SetBoolField(TEXT("skip_evaluation"), Params->ShouldSkipEvaluation());
		Record->SetBoolField(TEXT("interpolate_skipped_frames"), Params->ShouldInterpolateSkippedFrames());
	}
	Record->SetObjectField(TEXT("actor_world"), GGYGOAnimationObservation::Transform(Character->GetActorTransform()));
	Record->SetObjectField(TEXT("capsule_world"), GGYGOAnimationObservation::Transform(Character->GetCapsuleComponent()->GetComponentTransform()));
	Record->SetObjectField(TEXT("mesh_world"), GGYGOAnimationObservation::Transform(Mesh->GetComponentTransform()));
	int16 UpdateCounter = INDEX_NONE;
	int16 EvaluationCounter = INDEX_NONE;
	bool bExtractRootMotion = false;
	Anim->GetNativePoseEvaluationFacts(UpdateCounter, EvaluationCounter, bExtractRootMotion);
	Record->SetNumberField(TEXT("native_update_counter"), UpdateCounter);
	Record->SetNumberField(TEXT("native_evaluation_counter"), EvaluationCounter);
	Record->SetBoolField(TEXT("native_extract_root_motion"), bExtractRootMotion);
	const FGGYGOAnimationStateFrame& CapturedFrame = Anim->GetAnimationStateFrame();
	FString StateText;
	FGGYGOAnimationStateFrame::StaticStruct()->ExportText(StateText, &CapturedFrame, nullptr, Anim, PPF_IncludeTransient, nullptr);
	Record->SetStringField(TEXT("animation_captured_frame"), StateText);
	Record->SetObjectField(TEXT("movement_camera_turn"), GGYGOAnimationObservation::CameraTurn(CapturedFrame.LocomotionSteering));
	// 图本帧实际消费的远端姿态视图（与 animation_captured_frame 同次 GT 抓取）；server 键与本机帧分列。
	FString RemoteText;
	FGGYGOAnimationRemotePoseFrame::StaticStruct()->ExportText(RemoteText, &Anim->GetRemoteMotionPoseFrame(), nullptr, Anim, PPF_IncludeTransient, nullptr);
	Record->SetStringField(TEXT("animation_remote_pose"), RemoteText);
	// 只在此调用栈借用 CMC 已验证的事实，绝不把 binding/RMS 资源存进 observer。
	Record->SetObjectField(TEXT("movement_completed_interval"), GGYGOAnimationObservation::Motion(Movement->GetMotionExecutionSnapshot()));
	// 当前原 RMS 与完成区间分别记录；Finalize 帧不证明 owner 输入评价或源已实际贡献。
	Record->SetObjectField(TEXT("movement_action_native"), GGYGOAnimationObservation::NativeActionMotion(Movement->GetActionMotionNativeObservation()));
	TSharedPtr<FJsonObject> FinalBones = MakeShared<FJsonObject>();
	const TArray<FTransform>& ComponentTransforms = Mesh->GetComponentSpaceTransforms();
	for (FName Name : ObservedBoneNames)
	{
		const int32 Index = Mesh->GetBoneIndex(Name);
		if (!ComponentTransforms.IsValidIndex(Index) || ComponentTransforms[Index].ContainsNaN())
		{
			ReleaseObservation(FString::Printf(TEXT("FinalizedBoneUnavailableOrNonfinite:%s"), *Name.ToString()));
			return;
		}
		FinalBones->SetObjectField(Name.ToString(), GGYGOAnimationObservation::Transform(ComponentTransforms[Index]));
	}
	Record->SetObjectField(TEXT("final_component_space_bones"), FinalBones);
	TArray<TSharedPtr<FJsonValue>> Players;
	for (TFieldIterator<FStructProperty> It(Anim->GetClass()); It; ++It)
	{
		if (!It->Struct->IsChildOf(FAnimNode_AssetPlayerBase::StaticStruct()))
		{
			continue;
		}
		const FAnimNode_AssetPlayerBase* Player = It->ContainerPtrToValuePtr<FAnimNode_AssetPlayerBase>(Anim);
		TSharedPtr<FJsonObject> Item = MakeShared<FJsonObject>();
		Item->SetStringField(TEXT("property"), It->GetName());
		Item->SetStringField(TEXT("node_type"), It->Struct->GetPathName());
		Item->SetStringField(TEXT("asset"), GetPathNameSafe(Player->GetAnimAsset()));
		Item->SetNumberField(TEXT("accumulated_or_explicit_seconds"), Player->GetAccumulatedTime());
		Item->SetNumberField(TEXT("asset_seconds"), Player->GetCurrentAssetTime());
		Item->SetNumberField(TEXT("cached_blend_weight"), Player->GetCachedBlendWeight());
		Item->SetBoolField(TEXT("looping"), Player->IsLooping());
		Players.Add(MakeShared<FJsonValueObject>(Item));
	}
	Record->SetStringField(TEXT("player_scope"), TEXT("Native cached node values; weight alone does not prove participation in this evaluation"));
	Record->SetArrayField(TEXT("asset_players"), Players);
	Record->SetObjectField(TEXT("captured_source_pose"), GGYGOAnimationObservation::SourcePose(*Anim, *Mesh, ObservedBoneNames, bExtractRootMotion));
	Records.Add(Record);
	StopReason = TEXT("Observing");
	if (Records.Num() >= RecordLimit)
	{
		ReleaseObservation(TEXT("RecordLimitReached"));
	}
}

void UGGYGOAnimationPoseObservationSubsystem::ReleaseObservation(const FString& Reason)
{
	if (USkeletalMeshComponent* Mesh = ObservedMesh.Get(); Mesh && FinalizedHandle.IsValid())
	{
		Mesh->UnregisterOnBoneTransformsFinalizedDelegate(FinalizedHandle);
	}
	FinalizedHandle.Reset();
	ObservedMesh.Reset();
	ObservedMeshAsset.Reset();
	ObservedAnim.Reset();
	ObservedCharacter.Reset();
	ObservedMovement.Reset();
	ObservedBoneNames.Reset();
	StopReason = Reason;
}

void UGGYGOAnimationPoseObservationSubsystem::StopObservation()
{
	check(IsInGameThread());
	if (FinalizedHandle.IsValid())
	{
		ReleaseObservation(TEXT("StoppedByCaller"));
	}
}

void UGGYGOAnimationPoseObservationSubsystem::OnEndPIE(bool bSimulating)
{
	if (FinalizedHandle.IsValid())
	{
		ReleaseObservation(TEXT("EndPIE"));
	}
}

FString UGGYGOAnimationPoseObservationSubsystem::GetObservationJson(int32 FirstRecordIndex, int32 MaxRecordCount) const
{
	check(IsInGameThread());
	const int32 TotalRecordCount = Records.Num();
	const bool bValidRange = FirstRecordIndex >= 0 && FirstRecordIndex <= TotalRecordCount && MaxRecordCount >= -1;
	TSharedPtr<FJsonObject> Result = MakeShared<FJsonObject>();
	Result->SetStringField(TEXT("mesh"), MeshPath);
	Result->SetBoolField(TEXT("active"), FinalizedHandle.IsValid());
	Result->SetStringField(TEXT("stop_reason"), StopReason);
	Result->SetNumberField(TEXT("record_limit"), RecordLimit);
	Result->SetStringField(TEXT("scope"), TEXT("Read-only natural Mesh finalize observations; no runtime or visual acceptance verdict"));
	Result->SetNumberField(TEXT("record_count"), TotalRecordCount);
	Result->SetNumberField(TEXT("records_start_index"), FirstRecordIndex);
	Result->SetBoolField(TEXT("read_success"), bValidRange);
	TArray<TSharedPtr<FJsonValue>> Values;
	if (bValidRange)
	{
		const int32 AvailableCount = TotalRecordCount - FirstRecordIndex;
		const int32 ReturnCount = MaxRecordCount == -1 ? AvailableCount : FMath::Min(MaxRecordCount, AvailableCount);
		Values.Reserve(ReturnCount);
		for (int32 Offset = 0; Offset < ReturnCount; ++Offset)
		{
			Values.Add(MakeShared<FJsonValueObject>(Records[FirstRecordIndex + Offset]));
		}
	}
	else
	{
		Result->SetStringField(TEXT("diagnostic"), FString::Printf(
			TEXT("[Animation.PoseObservation] Mesh=%s 记录范围无效：FirstRecordIndex=%d MaxRecordCount=%d RecordCount=%d。"),
			*MeshPath, FirstRecordIndex, MaxRecordCount, TotalRecordCount));
	}
	Result->SetArrayField(TEXT("records"), Values);
	FString Json;
	{
		TRACE_CPUPROFILER_EVENT_SCOPE(GGYGOAnimationObservation_Serialize);
		FJsonSerializer::Serialize(Result.ToSharedRef(), TJsonWriterFactory<>::Create(&Json));
	}
	return Json;
}
