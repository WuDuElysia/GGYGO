// Copyright Epic Games, Inc. All Rights Reserved.

#include "Animation/AnimSequence.h"
#include "Animation/AnimCurveTypes.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/Skeleton.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/Paths.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "UObject/UObjectGlobals.h"

DEFINE_LOG_CATEGORY_STATIC(LogTurnBackYawBake, Log, All);

namespace
{
	const FName BoneRootName(TEXT("Bone_Root"));
	const FName RootName(TEXT("Root"));
	const FName Bip001Name(TEXT("Bip001"));
	const FName RMYawName(TEXT("RM_Yaw"));

	const TArray<FName> PreservedCurveNames =
	{
		FName(TEXT("RM_PosX")),
		FName(TEXT("RM_PosY")),
		FName(TEXT("RM_Dist")),
		FName(TEXT("RM_Speed")),
		FName(TEXT("RM_VelocityDirX")),
		FName(TEXT("RM_VelocityDirY")),
		RMYawName
	};

	constexpr float CurveComparisonTolerance = 0.001f;
	constexpr float TransformComparisonTolerance = 0.01f;
	constexpr float RotationComparisonTolerance = 0.0001f;

	struct FAssetPathParts
	{
		FString PackageName;
		FString AssetName;
	};

	bool ParseObjectPath(const FString& ObjectPath, FAssetPathParts& OutParts)
	{
		if (!ObjectPath.StartsWith(TEXT("/Game/")))
		{
			return false;
		}

		const int32 DotIndex = ObjectPath.Find(TEXT("."), ESearchCase::IgnoreCase, ESearchDir::FromEnd);
		if (DotIndex != INDEX_NONE)
		{
			OutParts.PackageName = ObjectPath.Left(DotIndex);
			OutParts.AssetName = ObjectPath.Mid(DotIndex + 1);
		}
		else
		{
			OutParts.PackageName = ObjectPath;
			int32 SlashIndex = INDEX_NONE;
			if (!OutParts.PackageName.FindLastChar(TEXT('/'), SlashIndex) || SlashIndex == INDEX_NONE)
			{
				return false;
			}
			OutParts.AssetName = OutParts.PackageName.Mid(SlashIndex + 1);
		}

		return !OutParts.PackageName.IsEmpty() && !OutParts.AssetName.IsEmpty();
	}

	bool SameBoneName(const FName& A, const FName& B)
	{
		return A.ToString().Equals(B.ToString(), ESearchCase::IgnoreCase);
	}

	FName FindModelTrackName(const IAnimationDataModel* Model, const FName DesiredName)
	{
		if (!Model)
		{
			return NAME_None;
		}

		TArray<FName> TrackNames;
		Model->GetBoneTrackNames(TrackNames);
		for (const FName TrackName : TrackNames)
		{
			if (SameBoneName(TrackName, DesiredName))
			{
				return TrackName;
			}
		}
		return NAME_None;
	}

	FVector3f ToVector3f(const FVector& Value);
	FQuat4f ToQuat4f(const FQuat& Value);

	// SnapshotTracks intentionally uses the current DataModel evaluation API. The deprecated
	// GetBoneAnimationTracks() path is not reliable for this imported asset in UE 5.8.
	TArray<FBoneAnimationTrack> SnapshotTracks(const IAnimationDataModel* Model)
	{
		TArray<FBoneAnimationTrack> Result;
		if (!Model)
		{
			return Result;
		}

		TArray<FName> TrackNames;
		Model->GetBoneTrackNames(TrackNames);
		Result.Reserve(TrackNames.Num());

		const int32 NumKeys = Model->GetNumberOfKeys();
		for (const FName TrackName : TrackNames)
		{
			TArray<FTransform> EvaluatedKeys;
			Model->GetBoneTrackTransforms(TrackName, EvaluatedKeys);

			if (EvaluatedKeys.Num() != NumKeys)
			{
				UE_LOG(LogTurnBackYawBake, Warning,
					TEXT("DataModel 轨道键数与模型不一致: track=%s evaluated=%d model_keys=%d"),
					*TrackName.ToString(), EvaluatedKeys.Num(), NumKeys);
			}

			FBoneAnimationTrack& Snapshot = Result.AddDefaulted_GetRef();
			Snapshot.Name = TrackName;
			Snapshot.BoneTreeIndex = INDEX_NONE;
			Snapshot.InternalTrackData.PosKeys.Reserve(EvaluatedKeys.Num());
			Snapshot.InternalTrackData.RotKeys.Reserve(EvaluatedKeys.Num());
			Snapshot.InternalTrackData.ScaleKeys.Reserve(EvaluatedKeys.Num());

			for (const FTransform& EvaluatedKey : EvaluatedKeys)
			{
				FQuat Rotation = EvaluatedKey.GetRotation();
				Rotation.Normalize();
				Snapshot.InternalTrackData.PosKeys.Add(ToVector3f(EvaluatedKey.GetTranslation()));
				Snapshot.InternalTrackData.RotKeys.Add(ToQuat4f(Rotation));
				Snapshot.InternalTrackData.ScaleKeys.Add(ToVector3f(EvaluatedKey.GetScale3D()));
			}
		}

		return Result;
	}

	void LogBoneTrackState(const TCHAR* Stage, const IAnimationDataModel* Model)
	{
		if (!Model)
		{
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("%s model=null"), Stage);
			return;
		}

		TArray<FName> TrackNames;
		Model->GetBoneTrackNames(TrackNames);

		FString TrackNameList;
		for (int32 Index = 0; Index < TrackNames.Num(); ++Index)
		{
			if (Index > 0)
			{
				TrackNameList += TEXT(", ");
			}
			TrackNameList += TrackNames[Index].ToString();
		}

		const FName BoneRootTrackName = FindModelTrackName(Model, BoneRootName);
		const bool bBoneRootEnumerated = BoneRootTrackName != NAME_None;
		const bool bBoneRootValid = bBoneRootEnumerated
			&& Model->IsValidBoneTrackName(BoneRootTrackName);
		UE_LOG(LogTurnBackYawBake, Display,
			TEXT("%s model=%p tracks=%d num_bone_tracks=%d frames=%d keys=%d Bone_Root query=%s enumerated=%s valid=%s names=[%s]"),
			Stage,
			static_cast<const void*>(Model),
			TrackNames.Num(),
			Model->GetNumBoneTracks(),
			Model->GetNumberOfFrames(),
			Model->GetNumberOfKeys(),
			*BoneRootTrackName.ToString(),
			bBoneRootEnumerated ? TEXT("true") : TEXT("false"),
			bBoneRootValid ? TEXT("true") : TEXT("false"),
			*TrackNameList);

		if (!bBoneRootValid)
		{
			return;
		}

		TArray<FTransform> EvaluatedKeys;
		Model->GetBoneTrackTransforms(BoneRootTrackName, EvaluatedKeys);
		const int32 FirstIndex = EvaluatedKeys.Num() > 0 ? 0 : INDEX_NONE;
		const int32 MiddleIndex = EvaluatedKeys.Num() > 0 ? EvaluatedKeys.Num() / 2 : INDEX_NONE;
		const int32 LastIndex = EvaluatedKeys.Num() > 0 ? EvaluatedKeys.Num() - 1 : INDEX_NONE;
		const float FirstYaw = FirstIndex != INDEX_NONE
			? EvaluatedKeys[FirstIndex].Rotator().Yaw
			: 0.f;
		const float MiddleYaw = MiddleIndex != INDEX_NONE
			? EvaluatedKeys[MiddleIndex].Rotator().Yaw
			: 0.f;
		const float LastYaw = LastIndex != INDEX_NONE
			? EvaluatedKeys[LastIndex].Rotator().Yaw
			: 0.f;
		UE_LOG(LogTurnBackYawBake, Display,
			TEXT("%s Bone_Root evaluated query=%s evaluated_keys=%d first_yaw=%.3f middle_yaw=%.3f last_yaw=%.3f"),
			Stage,
			*BoneRootTrackName.ToString(),
			EvaluatedKeys.Num(),
			FirstYaw,
			MiddleYaw,
			LastYaw);

		if (EvaluatedKeys.Num() == 0)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("%s Bone_Root 已枚举但 GetBoneTrackTransforms 返回空数组，query=%s"),
				Stage,
				*BoneRootTrackName.ToString());
			return;
		}

		TArray<int32> SampleIndices;
		SampleIndices.AddUnique(FirstIndex);
		SampleIndices.AddUnique(MiddleIndex);
		SampleIndices.AddUnique(LastIndex);
		for (const int32 KeyIndex : SampleIndices)
		{
			FTransform Sample = EvaluatedKeys[KeyIndex];
			Sample.NormalizeRotation();
			const FVector Position = Sample.GetTranslation();
			const FQuat Rotation = Sample.GetRotation();
			const FVector Scale = Sample.GetScale3D();
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("%s Bone_Root evaluated_key[%d] pos=(%.6f, %.6f, %.6f) rot=(%.6f, %.6f, %.6f, %.6f) scale=(%.6f, %.6f, %.6f)"),
				Stage,
				KeyIndex,
				Position.X, Position.Y, Position.Z,
				Rotation.X, Rotation.Y, Rotation.Z, Rotation.W,
				Scale.X, Scale.Y, Scale.Z);
		}
	}

	void LogSkeletonBoneState(const TCHAR* Stage, const USkeleton* Skeleton)
	{
		if (!Skeleton)
		{
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("%s skeleton=null"), Stage);
			return;
		}

		const FReferenceSkeleton& ReferenceSkeleton = Skeleton->GetReferenceSkeleton();
		UE_LOG(LogTurnBackYawBake, Display,
			TEXT("%s skeleton=%s bone_count=%d"),
			Stage,
			*Skeleton->GetPathName(),
			ReferenceSkeleton.GetNum());

		const FName BoneNames[] = { BoneRootName, Bip001Name };
		for (const FName BoneName : BoneNames)
		{
			const int32 BoneIndex = ReferenceSkeleton.FindBoneIndex(BoneName);
			if (BoneIndex == INDEX_NONE)
			{
				UE_LOG(LogTurnBackYawBake, Display,
					TEXT("%s bone=%s index=INDEX_NONE"),
					Stage,
					*BoneName.ToString());
				continue;
			}

			const int32 ParentIndex = ReferenceSkeleton.GetParentIndex(BoneIndex);
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("%s bone=%s index=%d parent_index=%d parent=%s"),
				Stage,
				*BoneName.ToString(),
				BoneIndex,
				ParentIndex,
				ParentIndex != INDEX_NONE
					? *ReferenceSkeleton.GetBoneName(ParentIndex).ToString()
					: TEXT("<none>"));
		}
	}

	const FBoneAnimationTrack* FindTrack(
		const TArray<FBoneAnimationTrack>& Tracks,
		const FName TrackName)
	{
		for (const FBoneAnimationTrack& Track : Tracks)
		{
			if (SameBoneName(Track.Name, TrackName))
			{
				return &Track;
			}
		}
		return nullptr;
	}

	TMap<FName, const FBoneAnimationTrack*> BuildTrackMap(const TArray<FBoneAnimationTrack>& Tracks)
	{
		TMap<FName, const FBoneAnimationTrack*> Result;
		for (const FBoneAnimationTrack& Track : Tracks)
		{
			Result.Add(Track.Name, &Track);
		}
		return Result;
	}

	const FBoneAnimationTrack* FindTrackInMap(
		const TMap<FName, const FBoneAnimationTrack*>& TrackMap,
		const FName TrackName)
	{
		for (const TPair<FName, const FBoneAnimationTrack*>& Entry : TrackMap)
		{
			if (SameBoneName(Entry.Key, TrackName))
			{
				return Entry.Value;
			}
		}
		return nullptr;
	}

	TArray<FName> GetTrackNames(const IAnimationDataModel* Model)
	{
		TArray<FName> Names;
		if (Model)
		{
			Model->GetBoneTrackNames(Names);
		}
		return Names;
	}

	FVector ToVector(const FVector3f& Value)
	{
		return FVector(Value.X, Value.Y, Value.Z);
	}

	FQuat ToQuat(const FQuat4f& Value)
	{
		return FQuat(Value.X, Value.Y, Value.Z, Value.W);
	}

	FVector3f ToVector3f(const FVector& Value)
	{
		return FVector3f(Value.X, Value.Y, Value.Z);
	}

	FQuat4f ToQuat4f(const FQuat& Value)
	{
		return FQuat4f(Value.X, Value.Y, Value.Z, Value.W);
	}

	bool NearlyEqual(const FVector3f& A, const FVector3f& B, const float Tolerance)
	{
		return FMath::IsNearlyEqual(A.X, B.X, Tolerance)
			&& FMath::IsNearlyEqual(A.Y, B.Y, Tolerance)
			&& FMath::IsNearlyEqual(A.Z, B.Z, Tolerance);
	}

	bool NearlyEqual(const FQuat4f& A, const FQuat4f& B, const float Tolerance)
	{
		return FMath::IsNearlyEqual(A.X, B.X, Tolerance)
			&& FMath::IsNearlyEqual(A.Y, B.Y, Tolerance)
			&& FMath::IsNearlyEqual(A.Z, B.Z, Tolerance)
			&& FMath::IsNearlyEqual(A.W, B.W, Tolerance);
	}

	bool SameTrackData(const FBoneAnimationTrack& A, const FBoneAnimationTrack& B)
	{
		const FRawAnimSequenceTrack& TrackA = A.InternalTrackData;
		const FRawAnimSequenceTrack& TrackB = B.InternalTrackData;
		if (TrackA.PosKeys.Num() != TrackB.PosKeys.Num()
			|| TrackA.RotKeys.Num() != TrackB.RotKeys.Num()
			|| TrackA.ScaleKeys.Num() != TrackB.ScaleKeys.Num())
		{
			return false;
		}

		for (int32 Index = 0; Index < TrackA.PosKeys.Num(); ++Index)
		{
			if (!NearlyEqual(TrackA.PosKeys[Index], TrackB.PosKeys[Index], TransformComparisonTolerance))
			{
				return false;
			}
		}
		for (int32 Index = 0; Index < TrackA.RotKeys.Num(); ++Index)
		{
			if (!NearlyEqual(TrackA.RotKeys[Index], TrackB.RotKeys[Index], RotationComparisonTolerance)
				&& !NearlyEqual(
					FQuat4f(-TrackA.RotKeys[Index].X, -TrackA.RotKeys[Index].Y,
						-TrackA.RotKeys[Index].Z, -TrackA.RotKeys[Index].W),
					TrackB.RotKeys[Index], RotationComparisonTolerance))
			{
				return false;
			}
		}
		for (int32 Index = 0; Index < TrackA.ScaleKeys.Num(); ++Index)
		{
			if (!NearlyEqual(TrackA.ScaleKeys[Index], TrackB.ScaleKeys[Index], TransformComparisonTolerance))
			{
				return false;
			}
		}
		return true;
	}

	int32 SelectKeyIndex(const int32 NumKeys, const int32 Frame, const int32 NumFrames)
	{
		if (NumKeys <= 0)
		{
			return INDEX_NONE;
		}
		if (NumKeys == 1)
		{
			return 0;
		}
		if (NumKeys == NumFrames)
		{
			return FMath::Clamp(Frame, 0, NumKeys - 1);
		}
		return FMath::Clamp(Frame, 0, NumKeys - 1);
	}

	FTransform GetLocalTransform(
		const FReferenceSkeleton& ReferenceSkeleton,
		const TMap<FName, const FBoneAnimationTrack*>& TrackMap,
		const int32 BoneIndex,
		const int32 Frame,
		const int32 NumFrames)
	{
		const TArray<FTransform>& RefPose = ReferenceSkeleton.GetRefBonePose();
		if (!RefPose.IsValidIndex(BoneIndex))
		{
			return FTransform::Identity;
		}

		const FTransform& ReferenceTransform = RefPose[BoneIndex];
		const FBoneAnimationTrack* Track = FindTrackInMap(
			TrackMap,
			ReferenceSkeleton.GetBoneName(BoneIndex));
		if (!Track)
		{
			return ReferenceTransform;
		}

		const FRawAnimSequenceTrack& TrackData = Track->InternalTrackData;
		FVector Translation = ReferenceTransform.GetTranslation();
		FQuat Rotation = ReferenceTransform.GetRotation();
		FVector Scale = ReferenceTransform.GetScale3D();

		const int32 PositionIndex = SelectKeyIndex(TrackData.PosKeys.Num(), Frame, NumFrames);
		const int32 RotationIndex = SelectKeyIndex(TrackData.RotKeys.Num(), Frame, NumFrames);
		const int32 ScaleIndex = SelectKeyIndex(TrackData.ScaleKeys.Num(), Frame, NumFrames);
		if (PositionIndex != INDEX_NONE)
		{
			Translation = ToVector(TrackData.PosKeys[PositionIndex]);
		}
		if (RotationIndex != INDEX_NONE)
		{
			Rotation = ToQuat(TrackData.RotKeys[RotationIndex]);
			Rotation.Normalize();
		}
		if (ScaleIndex != INDEX_NONE)
		{
			Scale = ToVector(TrackData.ScaleKeys[ScaleIndex]);
		}

		return FTransform(Rotation, Translation, Scale);
	}

	void BuildParentChain(
		const FReferenceSkeleton& ReferenceSkeleton,
		const int32 BoneIndex,
		TArray<int32>& OutChain)
	{
		OutChain.Reset();
		TArray<int32> ReverseChain;
		int32 Current = ReferenceSkeleton.GetParentIndex(BoneIndex);
		int32 Guard = 0;
		while (Current != INDEX_NONE && Guard++ <= ReferenceSkeleton.GetNum())
		{
			ReverseChain.Add(Current);
			Current = ReferenceSkeleton.GetParentIndex(Current);
		}

		for (int32 Index = ReverseChain.Num() - 1; Index >= 0; --Index)
		{
			OutChain.Add(ReverseChain[Index]);
		}
	}

	FTransform GetComponentTransform(
		const FReferenceSkeleton& ReferenceSkeleton,
		const TMap<FName, const FBoneAnimationTrack*>& TrackMap,
		const int32 BoneIndex,
		const int32 Frame,
		const int32 NumFrames,
		const int32 OverrideBoneIndex = INDEX_NONE,
		const FTransform* OverrideLocalTransform = nullptr)
	{
		TArray<int32> Chain;
		BuildParentChain(ReferenceSkeleton, BoneIndex, Chain);
		Chain.Add(BoneIndex);

		FTransform ComponentTransform = FTransform::Identity;
		for (const int32 CurrentBoneIndex : Chain)
		{
			const FTransform LocalTransform =
				CurrentBoneIndex == OverrideBoneIndex && OverrideLocalTransform
				? *OverrideLocalTransform
				: GetLocalTransform(ReferenceSkeleton, TrackMap, CurrentBoneIndex, Frame, NumFrames);
			ComponentTransform = LocalTransform * ComponentTransform;
		}
		return ComponentTransform;
	}

	const FFloatCurve* FindFloatCurve(const IAnimationDataModel* Model, const FName CurveName)
	{
		if (!Model)
		{
			return nullptr;
		}
		return Model->FindFloatCurve(FAnimationCurveIdentifier(CurveName, ERawCurveTrackTypes::RCT_Float));
	}

	float EvaluateCurve(const FFloatCurve* Curve, const float Time)
	{
		return Curve ? Curve->Evaluate(Time) : 0.f;
	}

	bool ComparePreservedCurves(
		const IAnimationDataModel* SourceModel,
		const IAnimationDataModel* BakedModel,
		const int32 NumFrames,
		const float Length)
	{
		bool bSuccess = true;
		for (const FName CurveName : PreservedCurveNames)
		{
			const FFloatCurve* SourceCurve = FindFloatCurve(SourceModel, CurveName);
			const FFloatCurve* BakedCurve = FindFloatCurve(BakedModel, CurveName);
			if ((SourceCurve != nullptr) != (BakedCurve != nullptr))
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("曲线存在性改变: %s source=%s baked=%s"),
					*CurveName.ToString(), SourceCurve ? TEXT("true") : TEXT("false"),
					BakedCurve ? TEXT("true") : TEXT("false"));
				bSuccess = false;
				continue;
			}
			if (!SourceCurve)
			{
				UE_LOG(LogTurnBackYawBake, Warning, TEXT("源动画没有曲线: %s"), *CurveName.ToString());
				continue;
			}

			float MaxDifference = 0.f;
			const int32 SampleCount = FMath::Min(FMath::Max(NumFrames, 1), 32);
			for (int32 Sample = 0; Sample < SampleCount; ++Sample)
			{
				const float Alpha = SampleCount > 1 ? static_cast<float>(Sample) / (SampleCount - 1) : 0.f;
				const float Time = Length * Alpha;
				MaxDifference = FMath::Max(
					MaxDifference,
					FMath::Abs(EvaluateCurve(SourceCurve, Time) - EvaluateCurve(BakedCurve, Time)));
			}

			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("曲线保留 %s max_difference=%.6f"), *CurveName.ToString(), MaxDifference);
			if (MaxDifference > CurveComparisonTolerance)
			{
				bSuccess = false;
			}
		}
		return bSuccess;
	}

	bool CompareTrackSets(
		const TArray<FBoneAnimationTrack>& SourceTracks,
		const TArray<FBoneAnimationTrack>& BakedTracks,
		const FName TargetBoneName)
	{
		bool bSuccess = true;
		const bool bSourceHasTarget = FindTrack(SourceTracks, TargetBoneName) != nullptr;
		const bool bBakedHasTarget = FindTrack(BakedTracks, TargetBoneName) != nullptr;
		const bool bOnlyAddedTargetTrack =
			!bSourceHasTarget
			&& bBakedHasTarget
			&& BakedTracks.Num() == SourceTracks.Num() + 1;
		if (SourceTracks.Num() != BakedTracks.Num() && !bOnlyAddedTargetTrack)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("骨骼轨道数量改变: source=%d baked=%d"), SourceTracks.Num(), BakedTracks.Num());
			bSuccess = false;
		}

		for (const FBoneAnimationTrack& SourceTrack : SourceTracks)
		{
			const FBoneAnimationTrack* BakedTrack = FindTrack(BakedTracks, SourceTrack.Name);
			if (!BakedTrack)
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("修正版缺少骨骼轨道: %s"), *SourceTrack.Name.ToString());
				bSuccess = false;
				continue;
			}

			if (!SameBoneName(SourceTrack.Name, TargetBoneName)
				&& !SameTrackData(SourceTrack, *BakedTrack))
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("非目标骨骼轨道被改变: %s"), *SourceTrack.Name.ToString());
				bSuccess = false;
			}
		}
		if (bOnlyAddedTargetTrack)
		{
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("允许新增目标轨道: %s source_absent baked_present"),
				*TargetBoneName.ToString());
		}
		return bSuccess;
	}

	FTransform BuildRMYawInverseBip001Local(
		const FTransform& SourceLocal,
		const FTransform& ParentComponent,
		const float RMYaw)
	{
		const FTransform SourceComponent = SourceLocal * ParentComponent;
		FTransform CorrectedComponent = SourceComponent;

		// RM_Yaw 是绕组件空间竖直 Z 轴的累计角；在 component space 施加逆角，
		// 再换算回 Bip001 local，避免使用倾斜 Bip001 自身的局部 Yaw 轴。
		const FQuat ComponentSpaceCorrection(
			FVector::UpVector,
			FMath::DegreesToRadians(-RMYaw));
		CorrectedComponent.SetRotation(
			ComponentSpaceCorrection * SourceComponent.GetRotation());
		CorrectedComponent.SetTranslation(SourceComponent.GetTranslation());
		CorrectedComponent.SetScale3D(SourceComponent.GetScale3D());

		FTransform CorrectedLocal =
			CorrectedComponent.GetRelativeTransform(ParentComponent);
		// 补偿只改变旋转；保持 Bip001 原始 local 平移和缩放。
		CorrectedLocal.SetTranslation(SourceLocal.GetTranslation());
		CorrectedLocal.SetScale3D(SourceLocal.GetScale3D());
		CorrectedLocal.NormalizeRotation();
		return CorrectedLocal;
	}

	bool BuildRMYawInverseBip001Keys(
		const UAnimSequence* SourceAnimation,
		const IAnimationDataModel* SourceModel,
		const FReferenceSkeleton& ReferenceSkeleton,
		const TArray<FBoneAnimationTrack>& SourceTracks,
		TArray<FVector3f>& OutPositions,
		TArray<FQuat4f>& OutRotations,
		TArray<FVector3f>& OutScales)
	{
		if (!FindTrack(SourceTracks, Bip001Name))
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("源动画没有 Bip001 动画轨道；为避免改动 Bone_Root reference，停止烘焙。"));
			return false;
		}

		const int32 NumFrames = SourceModel ? SourceModel->GetNumberOfKeys() : 0;
		const float Length = SourceAnimation ? SourceAnimation->GetPlayLength() : 0.f;
		if (NumFrames <= 0 || Length <= 0.f)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("源动画关键帧或时长无效: frames=%d length=%.6f"), NumFrames, Length);
			return false;
		}

		const int32 BoneRootIndex = ReferenceSkeleton.FindBoneIndex(BoneRootName);
		const int32 ActionRootIndex = ReferenceSkeleton.FindBoneIndex(Bip001Name);
		if (BoneRootIndex == INDEX_NONE || ActionRootIndex == INDEX_NONE)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("Skeleton 中缺少 Bone_Root 或 Bip001，停止以避免修改错误骨骼。"));
			return false;
		}

		const int32 ParentIndex = ReferenceSkeleton.GetParentIndex(ActionRootIndex);
		if (ParentIndex != BoneRootIndex)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("Bip001 不是 Bone_Root 的直接子骨骼: Bip001 parent_index=%d parent=%s Bone_Root index=%d"),
				ParentIndex,
				ParentIndex != INDEX_NONE
					? *ReferenceSkeleton.GetBoneName(ParentIndex).ToString()
					: TEXT("<none>"),
				BoneRootIndex);
			return false;
		}

		const FFloatCurve* RMYawCurve = FindFloatCurve(SourceModel, RMYawName);
		if (!RMYawCurve)
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("源动画没有 RM_Yaw FloatCurve，停止以避免猜测旋转。"));
			return false;
		}

		const TMap<FName, const FBoneAnimationTrack*> TrackMap = BuildTrackMap(SourceTracks);
		UE_LOG(LogTurnBackYawBake, Display,
			TEXT("Bip001 index=%d parent_index=%d parent=%s; Bone_Root 保持不变; frames=%d length=%.6f"),
			ActionRootIndex,
			ParentIndex,
			*ReferenceSkeleton.GetBoneName(ParentIndex).ToString(),
			NumFrames,
			Length);

		OutPositions.Reserve(NumFrames);
		OutRotations.Reserve(NumFrames);
		OutScales.Reserve(NumFrames);

		FQuat PreviousRotation = FQuat::Identity;
		bool bHasPreviousRotation = false;
		float MinYaw = MAX_FLT;
		float MaxYaw = -MAX_FLT;
		float FirstActiveTime = -1.f;
		float FirstActiveYaw = 0.f;
		for (int32 Frame = 0; Frame < NumFrames; ++Frame)
		{
			const float Time = NumFrames > 1
				? Length * static_cast<float>(Frame) / static_cast<float>(NumFrames - 1)
				: 0.f;
			const float RMYaw = EvaluateCurve(RMYawCurve, Time);
			if (!FMath::IsFinite(RMYaw))
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("RM_Yaw 在 frame=%d time=%.6f 得到非有限值。"), Frame, Time);
				return false;
			}

			if (FirstActiveTime < 0.f && FMath::Abs(RMYaw) > 0.01f)
			{
				FirstActiveTime = Time;
				FirstActiveYaw = RMYaw;
			}
			MinYaw = FMath::Min(MinYaw, RMYaw);
			MaxYaw = FMath::Max(MaxYaw, RMYaw);

			const FTransform OriginalLocal = GetLocalTransform(
				ReferenceSkeleton, TrackMap, ActionRootIndex, Frame, NumFrames);
			const FTransform ParentComponent = GetComponentTransform(
				ReferenceSkeleton, TrackMap, ParentIndex, Frame, NumFrames);
			const FTransform CorrectedLocal = BuildRMYawInverseBip001Local(
				OriginalLocal,
				ParentComponent,
				RMYaw);

			if (Frame <= 10 || Frame == NumFrames / 2 || Frame == NumFrames - 1)
			{
				const FTransform SourceComponent = OriginalLocal * ParentComponent;
				const FTransform CorrectedComponent = CorrectedLocal * ParentComponent;
				UE_LOG(LogTurnBackYawBake, Display,
					TEXT("Bip001 sample frame=%d time=%.6f RM_Yaw=%.3f "
						"correction_space=component_Z source_component_yaw=%.3f corrected_component_yaw=%.3f"),
					Frame,
					Time,
					RMYaw,
					SourceComponent.Rotator().Yaw,
					CorrectedComponent.Rotator().Yaw);
			}

			FQuat CorrectedRotation = CorrectedLocal.GetRotation();
			if (bHasPreviousRotation && (PreviousRotation | CorrectedRotation) < 0.f)
			{
				CorrectedRotation = FQuat(
					-CorrectedRotation.X,
					-CorrectedRotation.Y,
					-CorrectedRotation.Z,
					-CorrectedRotation.W);
			}
			PreviousRotation = CorrectedRotation;
			bHasPreviousRotation = true;

			OutPositions.Add(ToVector3f(OriginalLocal.GetTranslation()));
			OutRotations.Add(ToQuat4f(CorrectedRotation));
			OutScales.Add(ToVector3f(OriginalLocal.GetScale3D()));
		}

		UE_LOG(LogTurnBackYawBake, Display,
			TEXT("RM_Yaw range=[%.3f, %.3f] inverse applied around component-space Z "
				"then converted to Bip001 local rotation; first_nonzero_time=%.6f "
				"first_nonzero_yaw=%.3f frames=%d"),
			MinYaw,
			MaxYaw,
			FirstActiveTime,
			FirstActiveYaw,
			NumFrames);
		return true;
	}

	bool ValidatePair(
		const UAnimSequence* SourceAnimation,
		const UAnimSequence* BakedAnimation,
		const bool bRequireCorrection)
	{
		if (!SourceAnimation || !BakedAnimation)
		{
			return false;
		}

		const IAnimationDataModel* SourceModel = SourceAnimation->GetDataModel();
		const IAnimationDataModel* BakedModel = BakedAnimation->GetDataModel();
		if (!SourceModel || !BakedModel)
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("验证时拿不到 source/baked DataModel。"));
			return false;
		}

		bool bSuccess = true;
		if (!FMath::IsNearlyEqual(
				static_cast<float>(SourceAnimation->GetPlayLength()),
				static_cast<float>(BakedAnimation->GetPlayLength()),
				TransformComparisonTolerance))
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("时长改变 source=%.6f baked=%.6f"),
				SourceAnimation->GetPlayLength(), BakedAnimation->GetPlayLength());
			bSuccess = false;
		}
		if (SourceAnimation->GetSkeleton() != BakedAnimation->GetSkeleton())
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("Skeleton 绑定改变。"));
			bSuccess = false;
		}

		const TArray<FBoneAnimationTrack> SourceTracks = SnapshotTracks(SourceModel);
		const TArray<FBoneAnimationTrack> BakedTracks = SnapshotTracks(BakedModel);
		bSuccess = CompareTrackSets(SourceTracks, BakedTracks, Bip001Name) && bSuccess;

		const FBoneAnimationTrack* SourceRootTrack = FindTrack(SourceTracks, RootName);
		const FBoneAnimationTrack* BakedRootTrack = FindTrack(BakedTracks, RootName);
		if ((SourceRootTrack != nullptr) != (BakedRootTrack != nullptr))
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("Root 轨道存在性改变。"));
			bSuccess = false;
		}
		else if (SourceRootTrack && !SameTrackData(*SourceRootTrack, *BakedRootTrack))
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("Root 轨道未保持不变。"));
			bSuccess = false;
		}
		else if (SourceRootTrack)
		{
			UE_LOG(LogTurnBackYawBake, Display, TEXT("Root 轨道保留，键数=%d"),
				SourceRootTrack->InternalTrackData.RotKeys.Num());
		}
		else
		{
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("Root 动画轨道源/目标均不存在；按原状态保留。"));
		}

		bSuccess = ComparePreservedCurves(
			SourceModel,
			BakedModel,
			SourceModel->GetNumberOfKeys(),
			SourceAnimation->GetPlayLength()) && bSuccess;

		const USkeleton* Skeleton = SourceAnimation->GetSkeleton();
		if (!Skeleton)
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("源动画没有 Skeleton。"));
			return false;
		}
		const FReferenceSkeleton& ReferenceSkeleton = Skeleton->GetReferenceSkeleton();
		const TMap<FName, const FBoneAnimationTrack*> SourceTrackMap = BuildTrackMap(SourceTracks);
		const TMap<FName, const FBoneAnimationTrack*> BakedTrackMap = BuildTrackMap(BakedTracks);
		const int32 NumFrames = SourceModel->GetNumberOfKeys();
		const float Length = SourceAnimation->GetPlayLength();
		const int32 BoneRootIndex = ReferenceSkeleton.FindBoneIndex(BoneRootName);
		const int32 ActionRootIndex = ReferenceSkeleton.FindBoneIndex(Bip001Name);
		const int32 ActionParentIndex = ActionRootIndex != INDEX_NONE
			? ReferenceSkeleton.GetParentIndex(ActionRootIndex)
			: INDEX_NONE;
		const FFloatCurve* RMYawCurve = FindFloatCurve(SourceModel, RMYawName);
		if (BoneRootIndex == INDEX_NONE
			|| ActionRootIndex == INDEX_NONE
			|| ActionParentIndex != BoneRootIndex
			|| !RMYawCurve
			|| NumFrames <= 0)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("验证缺少 Bone_Root/Bip001、Bip001 父链、RM_Yaw 或有效帧数。"));
			return false;
		}

		const FBoneAnimationTrack* SourceActionTrack = FindTrack(SourceTracks, Bip001Name);
		const FBoneAnimationTrack* BakedActionTrack = FindTrack(BakedTracks, Bip001Name);
		if (!SourceActionTrack || !BakedActionTrack)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("验证缺少 Bip001 动画轨道 source=%s baked=%s。"),
				SourceActionTrack ? TEXT("true") : TEXT("false"),
				BakedActionTrack ? TEXT("true") : TEXT("false"));
			return false;
		}

		const FBoneAnimationTrack* SourceBoneRootTrack = FindTrack(SourceTracks, BoneRootName);
		const FBoneAnimationTrack* BakedBoneRootTrack = FindTrack(BakedTracks, BoneRootName);
		if ((SourceBoneRootTrack != nullptr) != (BakedBoneRootTrack != nullptr)
			|| (SourceBoneRootTrack && !SameTrackData(*SourceBoneRootTrack, *BakedBoneRootTrack)))
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("Bone_Root 轨道没有保持不变；参考方向轨道不能被烘焙修改。"));
			return false;
		}
		UE_LOG(LogTurnBackYawBake, Display,
			TEXT("Bone_Root 轨道保持不变，Bip001 作为唯一补偿目标。"));

		const auto GetRotationErrorDegrees = [](const FQuat& A, const FQuat& B)
		{
			const float Dot = FMath::Clamp(FMath::Abs(A | B), 0.f, 1.f);
			return FMath::RadiansToDegrees(2.f * FMath::Acos(Dot));
		};

		float MaxBoneRootTranslationError = 0.f;
		float MaxBoneRootScaleError = 0.f;
		float MaxBoneRootRotationError = 0.f;
		float MaxActionTransformTranslationError = 0.f;
		float MaxActionTransformScaleError = 0.f;
		float MaxActionTransformRotationError = 0.f;
		bool bAnyNonIdentityCorrection = false;
		bool bAnyActionChange = false;
		for (int32 Frame = 0; Frame < NumFrames; ++Frame)
		{
			const float Time = NumFrames > 1
				? Length * static_cast<float>(Frame) / static_cast<float>(NumFrames - 1)
				: 0.f;
			const float RMYaw = EvaluateCurve(RMYawCurve, Time);
			if (!FMath::IsFinite(RMYaw))
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("验证时 RM_Yaw 在 frame=%d time=%.6f 得到非有限值。"), Frame, Time);
				bSuccess = false;
				break;
			}

			const FTransform SourceBoneRoot = GetComponentTransform(
				ReferenceSkeleton, SourceTrackMap, BoneRootIndex, Frame, NumFrames);
			const FTransform BakedBoneRoot = GetComponentTransform(
				ReferenceSkeleton, BakedTrackMap, BoneRootIndex, Frame, NumFrames);
			const float BoneRootTranslationError =
				(BakedBoneRoot.GetTranslation() - SourceBoneRoot.GetTranslation()).Size();
			const float BoneRootScaleError =
				(BakedBoneRoot.GetScale3D() - SourceBoneRoot.GetScale3D()).Size();
			const float BoneRootRotationError = GetRotationErrorDegrees(
				SourceBoneRoot.GetRotation(), BakedBoneRoot.GetRotation());
			MaxBoneRootTranslationError = FMath::Max(
				MaxBoneRootTranslationError, BoneRootTranslationError);
			MaxBoneRootScaleError = FMath::Max(MaxBoneRootScaleError, BoneRootScaleError);
			MaxBoneRootRotationError = FMath::Max(
				MaxBoneRootRotationError, BoneRootRotationError);

			const FTransform BakedAction = GetComponentTransform(
				ReferenceSkeleton, BakedTrackMap, ActionRootIndex, Frame, NumFrames);
			const FTransform BakedActionLocal = GetLocalTransform(
				ReferenceSkeleton, BakedTrackMap, ActionRootIndex, Frame, NumFrames);
			const FTransform SourceActionLocal = GetLocalTransform(
				ReferenceSkeleton, SourceTrackMap, ActionRootIndex, Frame, NumFrames);
			const FTransform ParentComponent = GetComponentTransform(
				ReferenceSkeleton, SourceTrackMap, ActionParentIndex, Frame, NumFrames);
			bAnyNonIdentityCorrection = bAnyNonIdentityCorrection
				|| FMath::Abs(RMYaw) > 0.01f;

			const FTransform ExpectedActionLocal = BuildRMYawInverseBip001Local(
				SourceActionLocal,
				ParentComponent,
				RMYaw);
			const FTransform ExpectedAction = ExpectedActionLocal * ParentComponent;

			const float ActionTranslationError =
				(BakedAction.GetTranslation() - ExpectedAction.GetTranslation()).Size();
			const float ActionScaleError =
				(BakedAction.GetScale3D() - ExpectedAction.GetScale3D()).Size();
			const float ActionRotationError = GetRotationErrorDegrees(
				BakedAction.GetRotation(), ExpectedAction.GetRotation());
			MaxActionTransformTranslationError = FMath::Max(
				MaxActionTransformTranslationError, ActionTranslationError);
			MaxActionTransformScaleError = FMath::Max(
				MaxActionTransformScaleError, ActionScaleError);
			MaxActionTransformRotationError = FMath::Max(
				MaxActionTransformRotationError, ActionRotationError);
			bAnyActionChange = bAnyActionChange
				|| GetRotationErrorDegrees(
					SourceActionLocal.GetRotation(), BakedActionLocal.GetRotation()) > 0.01f;

			if (BoneRootTranslationError > TransformComparisonTolerance
				|| BoneRootScaleError > TransformComparisonTolerance
				|| BoneRootRotationError > 0.05f
				|| ActionTranslationError > TransformComparisonTolerance
				|| ActionScaleError > TransformComparisonTolerance
				|| ActionRotationError > 0.05f)
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("骨骼变换验证失败 frame=%d RM_Yaw=%.3f Bone_Root[translation=%.6f scale=%.6f rotation=%.6f] Bip001Expected[translation=%.6f scale=%.6f rotation=%.6f]"),
					Frame,
					RMYaw,
					BoneRootTranslationError,
					BoneRootScaleError,
					BoneRootRotationError,
					ActionTranslationError,
					ActionScaleError,
					ActionRotationError);
				bSuccess = false;
				break;
			}
		}

		if (bRequireCorrection && bAnyNonIdentityCorrection && !bAnyActionChange)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("补偿角非零但 Bip001 没有产生任何动作旋转变化。"));
			bSuccess = false;
		}

		UE_LOG(LogTurnBackYawBake, Display,
			TEXT("Bone_Root preserved max_translation_error=%.6f max_scale_error=%.6f max_rotation_error=%.6f; "
				"Bip001 inverse RM_Yaw max_transform_error[translation=%.6f scale=%.6f rotation=%.6f]"),
			MaxBoneRootTranslationError,
			MaxBoneRootScaleError,
			MaxBoneRootRotationError,
			MaxActionTransformTranslationError,
			MaxActionTransformScaleError,
			MaxActionTransformRotationError);

		return bSuccess;
	}

	bool SameTrackPositionAndScale(const FBoneAnimationTrack& A, const FBoneAnimationTrack& B)
	{
		const FRawAnimSequenceTrack& TrackA = A.InternalTrackData;
		const FRawAnimSequenceTrack& TrackB = B.InternalTrackData;
		if (TrackA.PosKeys.Num() != TrackB.PosKeys.Num()
			|| TrackA.ScaleKeys.Num() != TrackB.ScaleKeys.Num())
		{
			return false;
		}

		for (int32 Index = 0; Index < TrackA.PosKeys.Num(); ++Index)
		{
			if (!NearlyEqual(TrackA.PosKeys[Index], TrackB.PosKeys[Index], TransformComparisonTolerance))
			{
				return false;
			}
		}
		for (int32 Index = 0; Index < TrackA.ScaleKeys.Num(); ++Index)
		{
			if (!NearlyEqual(TrackA.ScaleKeys[Index], TrackB.ScaleKeys[Index], TransformComparisonTolerance))
			{
				return false;
			}
		}
		return true;
	}

	bool ValidateExistingDestinationBaseline(
		const UAnimSequence* SourceAnimation,
		const UAnimSequence* ExistingAnimation)
	{
		if (!SourceAnimation || !ExistingAnimation)
		{
			return false;
		}

		const IAnimationDataModel* SourceModel = SourceAnimation->GetDataModel();
		const IAnimationDataModel* ExistingModel = ExistingAnimation->GetDataModel();
		if (!SourceModel || !ExistingModel)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("覆盖前基线校验失败：source/existing DataModel 为空。"));
			return false;
		}

		bool bSuccess = true;
		if (!FMath::IsNearlyEqual(
				static_cast<float>(SourceAnimation->GetPlayLength()),
				static_cast<float>(ExistingAnimation->GetPlayLength()),
				TransformComparisonTolerance))
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("覆盖前基线校验失败：时长不一致 source=%.6f existing=%.6f"),
				SourceAnimation->GetPlayLength(), ExistingAnimation->GetPlayLength());
			bSuccess = false;
		}
		if (SourceAnimation->GetSkeleton() != ExistingAnimation->GetSkeleton())
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("覆盖前基线校验失败：Skeleton 绑定不一致。"));
			bSuccess = false;
		}
		if (SourceModel->GetNumberOfKeys() != ExistingModel->GetNumberOfKeys())
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("覆盖前基线校验失败：关键帧数不一致 source=%d existing=%d"),
				SourceModel->GetNumberOfKeys(), ExistingModel->GetNumberOfKeys());
			bSuccess = false;
		}

		const TArray<FName> SourceNames = GetTrackNames(SourceModel);
		const TArray<FName> ExistingNames = GetTrackNames(ExistingModel);
		if (SourceNames.Num() != ExistingNames.Num())
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("覆盖前基线校验失败：骨骼轨道数不一致 source=%d existing=%d"),
				SourceNames.Num(), ExistingNames.Num());
			bSuccess = false;
		}
		else
		{
			for (int32 Index = 0; Index < SourceNames.Num(); ++Index)
			{
				if (!SameBoneName(SourceNames[Index], ExistingNames[Index]))
				{
					UE_LOG(LogTurnBackYawBake, Error,
						TEXT("覆盖前基线校验失败：轨道顺序/名称不一致 index=%d source=%s existing=%s"),
						Index, *SourceNames[Index].ToString(), *ExistingNames[Index].ToString());
					bSuccess = false;
					break;
				}
			}
		}

		const TArray<FBoneAnimationTrack> SourceTracks = SnapshotTracks(SourceModel);
		const TArray<FBoneAnimationTrack> ExistingTracks = SnapshotTracks(ExistingModel);
		if (SourceTracks.Num() != ExistingTracks.Num())
		{
			bSuccess = false;
		}
		for (const FBoneAnimationTrack& SourceTrack : SourceTracks)
		{
			const FBoneAnimationTrack* ExistingTrack = FindTrack(ExistingTracks, SourceTrack.Name);
			if (!ExistingTrack)
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("覆盖前基线校验失败：目标缺少轨道 %s"), *SourceTrack.Name.ToString());
				bSuccess = false;
				continue;
			}

			const bool bIsActionRoot = SameBoneName(SourceTrack.Name, Bip001Name);
			const bool bTrackMatches = bIsActionRoot
				? SameTrackPositionAndScale(SourceTrack, *ExistingTrack)
				: SameTrackData(SourceTrack, *ExistingTrack);
			if (!bTrackMatches)
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("覆盖前基线校验失败：%s 不是可安全覆盖的基线%s"),
					*SourceTrack.Name.ToString(),
					bIsActionRoot ? TEXT("；仅允许 Bip001 Rotation 不同") : TEXT(""));
				bSuccess = false;
			}
		}

		if (!ComparePreservedCurves(
				SourceModel,
				ExistingModel,
				SourceModel->GetNumberOfKeys(),
				SourceAnimation->GetPlayLength()))
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("覆盖前基线校验失败：FloatCurve/RM_* 曲线与源动画不一致。"));
			bSuccess = false;
		}

		if (bSuccess)
		{
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("覆盖前基线校验通过：Bone_Root、Root、其他轨道和曲线保持源基线；仅允许替换 Bip001 Rotation。"));
		}
		return bSuccess;
	}

	bool BakeTurnBackYaw(
		const FString& SourceObjectPath,
		const FString& DestinationObjectPath,
		const bool bAllowOverwriteExistingDestination)
	{
		UAnimSequence* SourceAnimation = LoadObject<UAnimSequence>(nullptr, *SourceObjectPath);
		if (!SourceAnimation)
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("无法加载源 AnimSequence: %s"), *SourceObjectPath);
			return false;
		}

		FAssetPathParts Destination;
		if (!ParseObjectPath(DestinationObjectPath, Destination))
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("目标必须是 /Game/.../Asset 或 /Game/.../Asset.Asset: %s"),
				*DestinationObjectPath);
			return false;
		}
		if (SourceObjectPath.Equals(DestinationObjectPath, ESearchCase::IgnoreCase))
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("源和目标不能是同一个 AnimSequence；拒绝原地破坏源动画。"));
			return false;
		}

		const FString PackageFilename = FPaths::Combine(
			FPaths::ProjectContentDir(),
			Destination.PackageName.RightChop(6) + TEXT(".uasset"));
		const bool bDestinationExists = IFileManager::Get().FileExists(*PackageFilename);
		if (bDestinationExists && !bAllowOverwriteExistingDestination)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("目标文件已存在；默认拒绝覆盖。若确认覆盖既有资产，请给命令追加 overwrite: %s"),
				*PackageFilename);
			return false;
		}

		const IAnimationDataModel* SourceModel = SourceAnimation->GetDataModel();
		USkeleton* Skeleton = SourceAnimation->GetSkeleton();
		if (!SourceModel || !Skeleton)
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("源动画缺少 DataModel 或 Skeleton。"));
			return false;
		}

		LogSkeletonBoneState(TEXT("源 Skeleton"), Skeleton);
		LogBoneTrackState(TEXT("源动画 DataModel"), SourceModel);
		const TArray<FBoneAnimationTrack> SourceTracks = SnapshotTracks(SourceModel);
		if (!FindTrack(SourceTracks, RootName))
		{
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("源动画没有 Root 动画轨道；不会人为创建 Root 轨道，只保留 RM_* 曲线。"));
		}
		if (!FindFloatCurve(SourceModel, RMYawName))
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("源动画缺少 RM_Yaw，未写入目标。"));
			return false;
		}

		UPackage* DestinationPackage = nullptr;
		UAnimSequence* BakedAnimation = nullptr;
		if (bDestinationExists)
		{
			BakedAnimation = LoadObject<UAnimSequence>(nullptr, *DestinationObjectPath);
			if (!BakedAnimation)
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("无法加载既有目标 AnimSequence，拒绝覆盖: %s"),
					*DestinationObjectPath);
				return false;
			}
			DestinationPackage = BakedAnimation->GetOutermost();
			if (!DestinationPackage
				|| !ValidateExistingDestinationBaseline(SourceAnimation, BakedAnimation))
			{
				UE_LOG(LogTurnBackYawBake, Error,
					TEXT("既有目标覆盖前基线校验失败；未调用 SetBoneTrackKeys，未保存。"));
				return false;
			}
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("进入既有目标覆盖模式：目标=%s；Bone_Root/Root/其他轨道/曲线已通过基线校验。"),
				*BakedAnimation->GetPathName());
		}
		else
		{
			DestinationPackage = CreatePackage(*Destination.PackageName);
			if (!DestinationPackage)
			{
				UE_LOG(LogTurnBackYawBake, Error, TEXT("无法创建目标 package: %s"), *Destination.PackageName);
				return false;
			}

			BakedAnimation = DuplicateObject<UAnimSequence>(
				SourceAnimation,
				DestinationPackage,
				*Destination.AssetName);
			if (!BakedAnimation)
			{
				UE_LOG(LogTurnBackYawBake, Error, TEXT("无法复制 AnimSequence。"));
				return false;
			}
			BakedAnimation->SetFlags(RF_Public | RF_Standalone);
		}

		TArray<FVector3f> NewPositions;
		TArray<FQuat4f> NewRotations;
		TArray<FVector3f> NewScales;
		if (!BuildRMYawInverseBip001Keys(
				SourceAnimation,
				SourceModel,
				Skeleton->GetReferenceSkeleton(),
				SourceTracks,
				NewPositions,
				NewRotations,
				NewScales))
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("计算 Bip001 补偿轨道失败；目标不会保存。"));
			return false;
		}

		const IAnimationDataModel* BakedModelBefore = BakedAnimation->GetDataModel();
		if (!BakedModelBefore)
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("目标 AnimSequence 缺少 DataModel。"));
			return false;
		}
		const TCHAR* DestinationStage = bDestinationExists
			? TEXT("既有目标写入前")
			: TEXT("目标副本写入前");
		LogBoneTrackState(DestinationStage, BakedModelBefore);
		FName ActionRootWriteName = FindModelTrackName(BakedModelBefore, Bip001Name);
		const bool bActionRootTrackReady = ActionRootWriteName != NAME_None
			&& BakedModelBefore->IsValidBoneTrackName(ActionRootWriteName);
		UE_LOG(LogTurnBackYawBake, Display,
			TEXT("%s Bip001 写入前 query=%s valid=%s；Bone_Root 不写入"),
			DestinationStage,
			*ActionRootWriteName.ToString(),
			bActionRootTrackReady ? TEXT("true") : TEXT("false"));

		IAnimationDataController& Controller = BakedAnimation->GetController();
		Controller.OpenBracket(FText::FromString(TEXT("Bake inverse RM_Yaw to Bip001")), false);
		if (!bActionRootTrackReady)
		{
			Controller.CloseBracket(false);
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("Bip001 轨道不存在；为保护 Bone_Root 不新增或写入错误轨道，停止烘焙。"));
			return false;
		}

		const bool bSetKeys = Controller.SetBoneTrackKeys(
			ActionRootWriteName,
			NewPositions,
			NewRotations,
			NewScales,
			false);
		Controller.CloseBracket(false);
		const IAnimationDataModel* BakedModelAfterWrite = BakedAnimation->GetDataModel();
		LogBoneTrackState(bDestinationExists ? TEXT("既有目标写入后") : TEXT("目标副本写入后"), BakedModelAfterWrite);
		if (!bSetKeys)
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("SetBoneTrackKeys(Bip001) 失败；目标不会保存。"));
			return false;
		}

		const IAnimationDataModel* BakedModel = BakedModelAfterWrite;
		const TArray<FBoneAnimationTrack> BakedTracks = SnapshotTracks(BakedModel);
		if (!CompareTrackSets(SourceTracks, BakedTracks, Bip001Name)
			|| !ComparePreservedCurves(
				SourceModel,
				BakedModel,
				SourceModel->GetNumberOfKeys(),
				SourceAnimation->GetPlayLength())
			|| !ValidatePair(SourceAnimation, BakedAnimation, true))
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("写入后内存校验失败；目标保持未保存状态。"));
			return false;
		}

		DestinationPackage->MarkPackageDirty();
		if (!bDestinationExists)
		{
			FAssetRegistryModule::AssetCreated(BakedAnimation);
		}
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SaveArgs.SaveFlags = SAVE_None;
		if (!UPackage::SavePackage(
			DestinationPackage,
			BakedAnimation,
			*PackageFilename,
			SaveArgs))
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("保存目标 package 失败: %s"), *PackageFilename);
			return false;
		}

		UE_LOG(LogTurnBackYawBake, Display,
			TEXT("完成：源=%s 目标=%s 文件=%s；写入目标轨道=Bip001；Bone_Root 未写入；模式=%s。"),
			*SourceObjectPath,
			*BakedAnimation->GetPathName(),
			*PackageFilename,
			bDestinationExists ? TEXT("overwrite") : TEXT("duplicate"));
		return true;
	}

	void HandleBakeTurnBackYawCommand(const TArray<FString>& Args)
	{
		if (Args.Num() < 2)
		{
			UE_LOG(LogTurnBackYawBake, Warning,
				TEXT("Usage: ZZZBakeTurnBackYaw <SourceAnimObjectPath> <DestinationAnimObjectPath> [overwrite]"));
			return;
		}

		const bool bHasOverwriteArgument = Args.Num() >= 3;
		const bool bAllowOverwrite = bHasOverwriteArgument
			&& Args[2].Equals(TEXT("overwrite"), ESearchCase::IgnoreCase);
		if (bHasOverwriteArgument && !bAllowOverwrite)
		{
			UE_LOG(LogTurnBackYawBake, Warning,
				TEXT("第三个参数只有明确的 overwrite 才允许覆盖已有目标；本次未执行。"));
			return;
		}

		BakeTurnBackYaw(Args[0], Args[1], bAllowOverwrite);
	}

	void HandleValidateTurnBackYawCommand(const TArray<FString>& Args)
	{
		if (Args.Num() < 2)
		{
			UE_LOG(LogTurnBackYawBake, Warning,
				TEXT("Usage: ZZZValidateTurnBackYaw <SourceAnimObjectPath> <BakedAnimObjectPath>"));
			return;
		}

		UAnimSequence* SourceAnimation = LoadObject<UAnimSequence>(nullptr, *Args[0]);
		UAnimSequence* BakedAnimation = LoadObject<UAnimSequence>(nullptr, *Args[1]);
		if (!SourceAnimation || !BakedAnimation)
		{
			UE_LOG(LogTurnBackYawBake, Error, TEXT("验证资产加载失败。"));
			return;
		}

		const bool bSuccess = ValidatePair(SourceAnimation, BakedAnimation, true);
		if (bSuccess)
		{
			UE_LOG(LogTurnBackYawBake, Display,
				TEXT("验证结果: PASS source=%s baked=%s"),
				*Args[0],
				*Args[1]);
		}
		else
		{
			UE_LOG(LogTurnBackYawBake, Error,
				TEXT("验证结果: FAIL source=%s baked=%s"),
				*Args[0],
				*Args[1]);
		}
	}

	static FAutoConsoleCommand GZZZBakeTurnBackYawCommand(
		TEXT("ZZZBakeTurnBackYaw"),
		TEXT("Duplicate an AnimSequence and bake inverse cumulative RM_Yaw into Bip001 while preserving Bone_Root; pass overwrite to explicitly update an existing destination."),
		FConsoleCommandWithArgsDelegate::CreateStatic(&HandleBakeTurnBackYawCommand));

	static FAutoConsoleCommand GZZZValidateTurnBackYawCommand(
		TEXT("ZZZValidateTurnBackYaw"),
		TEXT("Validate a baked TurnBack AnimSequence against its source without modifying assets."),
		FConsoleCommandWithArgsDelegate::CreateStatic(&HandleValidateTurnBackYawCommand));
}
