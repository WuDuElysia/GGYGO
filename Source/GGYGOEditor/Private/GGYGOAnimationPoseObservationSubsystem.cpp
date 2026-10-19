/** @file GGYGOAnimationPoseObservationSubsystem.cpp @brief 记录自然 finalize、物理结果与原生源姿态，不驱动被观察对象。 */
#include "GGYGOAnimationPoseObservationSubsystem.h"

#include "Animation/Runtime/GGYGOAnimInstanceBase.h"
#include "Character/Components/GGYGOCharacterMovementComponent.h"
#include "Animation/AnimationPoseData.h"
#include "Animation/AnimNode_AssetPlayerBase.h"
#include "Animation/AnimSequence.h"
#include "Animation/AttributesRuntime.h"
#include "BonePose.h"
#include "Components/CapsuleComponent.h"
#include "Components/SkeletalMeshComponent.h"
#include "Dom/JsonObject.h"
#include "Editor.h"
#include "Engine/EngineTypes.h"
#include "Engine/World.h"
#include "GameFramework/Character.h"
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
	FString StateText;
	FGGYGOAnimationStateFrame::StaticStruct()->ExportText(StateText, &Anim->GetAnimationStateFrame(), nullptr, Anim, PPF_IncludeTransient, nullptr);
	Record->SetStringField(TEXT("animation_captured_frame"), StateText);
	// 图本帧实际消费的远端姿态视图（与 animation_captured_frame 同次 GT 抓取）；server 键与本机帧分列。
	FString RemoteText;
	FGGYGOAnimationRemotePoseFrame::StaticStruct()->ExportText(RemoteText, &Anim->GetRemoteMotionPoseFrame(), nullptr, Anim, PPF_IncludeTransient, nullptr);
	Record->SetStringField(TEXT("animation_remote_pose"), RemoteText);
	// 只在此调用栈借用 CMC 已验证的事实，绝不把 binding/RMS 资源存进 observer。
	Record->SetObjectField(TEXT("movement_completed_interval"), GGYGOAnimationObservation::Motion(Movement->GetMotionExecutionSnapshot()));
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
