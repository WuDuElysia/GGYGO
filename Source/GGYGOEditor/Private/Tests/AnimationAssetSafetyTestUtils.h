#pragma once
#if WITH_DEV_AUTOMATION_TESTS
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "ReferenceSkeleton.h"
#include "Engine/SkeletalMesh.h"
#include "UObject/Package.h"

namespace AnimationAssetSafetyTests
{
inline UPackage* Package()
{
	return CreatePackage(*(TEXT("/Temp/AnimationAssetSafety_") + FGuid::NewGuid().ToString(EGuidFormats::Digits)));
}
inline UAnimSequence* Sequence(UPackage* Outer)
{
	USkeleton* Skeleton = NewObject<USkeleton>(Outer);
	USkeletalMesh* Mesh = NewObject<USkeletalMesh>(Outer);
	FReferenceSkeleton ReferenceSkeleton;
	{
		// The modifier rebuilds Final bones on destruction, before the mesh copy.
		FReferenceSkeletonModifier Ref(ReferenceSkeleton, Skeleton);
		Ref.Add(FMeshBoneInfo(TEXT("root"), TEXT("root"), INDEX_NONE), FTransform::Identity);
	}
	if (ReferenceSkeleton.GetRawBoneNum() != 1 || ReferenceSkeleton.GetNum() != 1)
	{
		UE_LOG(LogTemp, Error, TEXT("Animation safety fixture: reference skeleton was not finalized."));
		return nullptr;
	}
	Mesh->SetRefSkeleton(ReferenceSkeleton);
	Mesh->SetSkeleton(Skeleton);
	// Merge initializes both the reference skeleton and BoneTree through the engine API.
	if (!Skeleton->MergeAllBonesToBoneTree(Mesh, false)
		|| Skeleton->GetReferenceSkeleton().GetRawBoneNum() != 1
		|| Skeleton->GetReferenceSkeleton().GetNum() != 1
		|| Skeleton->GetReferenceSkeleton().FindBoneIndex(TEXT("root")) != 0
		|| !Skeleton->IsCompatibleMesh(Mesh))
	{
		UE_LOG(LogTemp, Error, TEXT("Animation safety fixture: Skeleton/BoneTree initialization failed."));
		return nullptr;
	}
	UAnimSequence* Asset = NewObject<UAnimSequence>(Outer);
	Asset->SetSkeleton(Skeleton);
	auto& Controller = Asset->GetController();
	Controller.InitializeModel();
	Controller.SetFrameRate(FFrameRate(1, 1), false);
	Controller.SetNumberOfFrames(FFrameNumber(1), false);
	if (!Controller.AddBoneCurve(TEXT("root"), false)
		|| !Controller.SetBoneTrackKeys(TEXT("root"),
		TArray<FVector>{FVector::ZeroVector, FVector(100, 0, 0)},
		TArray<FQuat>{FQuat::Identity, FQuat::Identity},
		TArray<FVector>{FVector::OneVector, FVector::OneVector}, false))
	{
		UE_LOG(LogTemp, Error, TEXT("Animation safety fixture: root track creation failed."));
		return nullptr;
	}
	Controller.NotifyPopulated();
	TArray<FTransform> Keys;
	Asset->GetDataModel()->GetBoneTrackTransforms(TEXT("root"), Keys);
	if (Keys.Num() != 2)
	{
		UE_LOG(LogTemp, Error, TEXT("Animation safety fixture: expected two root keys, found %d."), Keys.Num());
		return nullptr;
	}
	return Asset;
}
}
#endif
