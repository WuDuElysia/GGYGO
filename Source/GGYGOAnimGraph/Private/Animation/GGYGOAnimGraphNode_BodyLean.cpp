/**
 * @file GGYGOAnimGraphNode_BodyLean.cpp
 * @brief 编译时拒绝缺失、重叠骨链和未配置的膝弯方向
 */
#include "Animation/GGYGOAnimGraphNode_BodyLean.h"

#include "Animation/Skeleton.h"
#include "Kismet2/CompilerResultsLog.h"

#define LOCTEXT_NAMESPACE "GGYGOBodyLean"

FText UGGYGOAnimGraphNode_BodyLean::GetControllerDescription() const
{
	return LOCTEXT("Description", "GGYGO 整身倾身");
}

FText UGGYGOAnimGraphNode_BodyLean::GetNodeTitle(ENodeTitleType::Type TitleType) const
{
	return FText::Format(LOCTEXT("Title", "GGYGO 整身倾身\n{0}"), FText::FromName(Node.Body.BoneName));
}

FText UGGYGOAnimGraphNode_BodyLean::GetTooltipText() const
{
	return LOCTEXT("Tooltip", "围绕本次输入双脚中心倾身，满权重保持源脚轨迹；最终遵循UE原生Alpha混合。仅处理骨姿态，不执行胶囊位移或世界锁脚。");
}

void UGGYGOAnimGraphNode_BodyLean::ValidateAnimNodeDuringCompilation(
	USkeleton* ForSkeleton, FCompilerResultsLog& MessageLog)
{
	Super::ValidateAnimNodeDuringCompilation(ForSkeleton, MessageLog);
	if (!ForSkeleton)
	{
		MessageLog.Error(TEXT("@@ 需要明确的目标Skeleton。"), this);
		return;
	}
	// 保留 UE 的原生加载暂态；骨链完成加载后仍须通过编译及 RequiredBones 校验。
	if (ForSkeleton->HasAnyFlags(RF_NeedPostLoad))
	{
		return;
	}
	const FReferenceSkeleton& Reference = ForSkeleton->GetReferenceSkeleton();
	const int32 BodyIndex = Reference.FindBoneIndex(Node.Body.BoneName);
	if (BodyIndex == INDEX_NONE)
	{
		MessageLog.Error(TEXT("@@ 配置Body骨在目标Skeleton中不存在。"), this);
		return;
	}
	TSet<int32> LegBones;
	const FGGYGOBodyLeanLegDefinition* Definitions[2] = { &Node.LeftLeg, &Node.RightLeg };
	for (const FGGYGOBodyLeanLegDefinition* Definition : Definitions)
	{
		if (Definition->KneeBendAxisLocal.ContainsNaN()
			|| !FMath::IsNearlyEqual(Definition->KneeBendAxisLocal.SizeSquared(), 1.0, 1.e-4))
		{
			MessageLog.Error(TEXT("@@ 每条腿必须配置髋骨局部空间的单位膝弯轴。"), this);
		}
		int32 BoneIndex = Reference.FindBoneIndex(Definition->Foot.BoneName);
		for (int32 ChainIndex = 0; ChainIndex < 3; ++ChainIndex)
		{
			if (BoneIndex == INDEX_NONE || BoneIndex == BodyIndex || LegBones.Contains(BoneIndex))
			{
				MessageLog.Error(TEXT("@@ 双腿必须是Body子树内互不重叠的完整髋/膝/脚两骨链。"), this);
				return;
			}
			LegBones.Add(BoneIndex);
			BoneIndex = Reference.GetParentIndex(BoneIndex);
		}
		while (BoneIndex != INDEX_NONE && BoneIndex != BodyIndex)
		{
			BoneIndex = Reference.GetParentIndex(BoneIndex);
		}
		if (BoneIndex != BodyIndex)
		{
			MessageLog.Error(TEXT("@@ 配置脚骨的髋骨不属于Body子树。"), this);
		}
	}
}

#undef LOCTEXT_NAMESPACE
