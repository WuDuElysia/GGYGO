// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "AnimGraphNode_Base.h"
#include "Animation/Nodes/GGYGOAnimNode_ActionPoseSlot.h"
#include "GGYGOAnimGraphNode_ActionPoseSlot.generated.h"

UCLASS()
class GGYGOEDITOR_API UGGYGOAnimGraphNode_ActionPoseSlot : public UAnimGraphNode_Base
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, Category = "Settings")
	FGGYGOAnimNode_ActionPoseSlot Node;

	virtual FLinearColor GetNodeTitleColor() const override;
	virtual FText GetTooltipText() const override;
	virtual FText GetNodeTitle(ENodeTitleType::Type TitleType) const override;
	virtual FString GetNodeCategory() const override;
	virtual void ValidateAnimNodeDuringCompilation(USkeleton* ForSkeleton, FCompilerResultsLog& MessageLog) override;
	virtual void BakeDataDuringCompilation(FCompilerResultsLog& MessageLog) override;
	virtual void GetRequiredExtensions(TArray<TSubclassOf<UAnimBlueprintExtension>>& OutExtensions) const override;
};
