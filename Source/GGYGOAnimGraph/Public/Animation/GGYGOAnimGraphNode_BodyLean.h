/**
 * @file GGYGOAnimGraphNode_BodyLean.h
 * @brief 整身倾身节点的编辑器配置与骨链编译校验
 */
#pragma once

#include "CoreMinimal.h"
#include "AnimGraphNode_SkeletalControlBase.h"
#include "Animation/Nodes/GGYGOAnimNode_BodyLean.h"
#include "GGYGOAnimGraphNode_BodyLean.generated.h"

UCLASS()
class GGYGOANIMGRAPH_API UGGYGOAnimGraphNode_BodyLean : public UAnimGraphNode_SkeletalControlBase
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, Category = "Settings")
	FGGYGOAnimNode_BodyLean Node;

	virtual FText GetNodeTitle(ENodeTitleType::Type TitleType) const override;
	virtual FText GetTooltipText() const override;
	virtual void ValidateAnimNodeDuringCompilation(USkeleton* ForSkeleton, FCompilerResultsLog& MessageLog) override;
	virtual const FAnimNode_SkeletalControlBase* GetNode() const override { return &Node; }

protected:
	virtual FText GetControllerDescription() const override;
};
