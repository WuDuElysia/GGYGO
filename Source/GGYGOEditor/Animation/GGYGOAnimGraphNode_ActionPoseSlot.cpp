// Copyright Epic Games, Inc. All Rights Reserved.

#include "GGYGOAnimGraphNode_ActionPoseSlot.h"

#include "Animation/AnimBlueprint.h"
#include "Animation/Skeleton.h"
#include "Animation/Runtime/GGYGOMontageGuardAnimInstance.h"
#include "IAnimGraph_SequencerMixerTargetConnector.h"
#include "Kismet2/CompilerResultsLog.h"

#define LOCTEXT_NAMESPACE "GGYGOActionPoseSlot"

FLinearColor UGGYGOAnimGraphNode_ActionPoseSlot::GetNodeTitleColor() const
{
	return FLinearColor(0.3f, 0.65f, 0.85f);
}

FText UGGYGOAnimGraphNode_ActionPoseSlot::GetTooltipText() const
{
	return LOCTEXT("Tooltip", "Native Slot with component alignment and authored body translation relative to a trajectory bone. Requires fixed reference ancestors and uniform nonadditive montage blending.");
}

FText UGGYGOAnimGraphNode_ActionPoseSlot::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	if (TitleType == ENodeTitleType::MenuTitle || TitleType == ENodeTitleType::ListView)
	{
		return LOCTEXT("MenuTitle", "GGYGO Action Pose Slot");
	}
	return FText::Format(LOCTEXT("Title", "GGYGO Action Pose Slot\n{0}"), FText::FromName(Node.SlotName));
}

FString UGGYGOAnimGraphNode_ActionPoseSlot::GetNodeCategory() const
{
	return TEXT("Animation|Montage");
}

void UGGYGOAnimGraphNode_ActionPoseSlot::ValidateAnimNodeDuringCompilation(
	USkeleton* ForSkeleton, FCompilerResultsLog& MessageLog)
{
	Super::ValidateAnimNodeDuringCompilation(ForSkeleton, MessageLog);
	if (Node.SlotName.IsNone() || Node.BodyBoneName.IsNone() || Node.TrajectoryBoneName.IsNone()
		|| Node.BodyBoneName == Node.TrajectoryBoneName || Node.ComponentAlignment.ContainsNaN())
	{
		MessageLog.Error(TEXT("@@ requires an explicit slot, distinct body/trajectory bones and finite component alignment."), this);
	}
	if (!ForSkeleton || ForSkeleton->GetReferenceSkeleton().FindBoneIndex(Node.BodyBoneName) == INDEX_NONE
		|| ForSkeleton->GetReferenceSkeleton().FindBoneIndex(Node.TrajectoryBoneName) == INDEX_NONE)
	{
		MessageLog.Error(TEXT("@@ body or trajectory bone is missing from the target skeleton. Runtime RequiredBones must also retain both bones."), this);
	}
	const UAnimBlueprint* Blueprint = GetAnimBlueprint();
	const UGGYGOMontageGuardAnimInstance* ParentDefaults = Blueprint && Blueprint->ParentClass
		? Cast<UGGYGOMontageGuardAnimInstance>(Blueprint->ParentClass->GetDefaultObject()) : nullptr;
	if (!ParentDefaults)
	{
		MessageLog.Error(TEXT("@@ requires a GGYGOMontageGuardAnimInstance parent for the action pose failure contract."), this);
	}
	// The role's compiled CDO declaration is checked by the runtime provider. Its authored
	// defaults can change in this same compile, so the parent CDO is not that authority.
}

void UGGYGOAnimGraphNode_ActionPoseSlot::BakeDataDuringCompilation(FCompilerResultsLog& MessageLog)
{
	Super::BakeDataDuringCompilation(MessageLog);
	UAnimBlueprint* Blueprint = GetAnimBlueprint();
	if (!GIsCookerLoadingPackage && !IsRunningCookCommandlet() && Blueprint && Blueprint->TargetSkeleton)
	{
		Blueprint->TargetSkeleton->RegisterSlotNode(Node.SlotName);
	}
}

void UGGYGOAnimGraphNode_ActionPoseSlot::GetRequiredExtensions(
	TArray<TSubclassOf<UAnimBlueprintExtension>>& OutExtensions) const
{
	Super::GetRequiredExtensions(OutExtensions);
	if (const IAnimGraph_SequencerMixerTargetConnector* Connector = IAnimGraph_SequencerMixerTargetConnector::Get())
	{
		Connector->GetSequencerMixerTargetRequiredExtensions(OutExtensions);
	}
}

#undef LOCTEXT_NAMESPACE
