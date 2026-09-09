// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "AnimationModifier.h"
#include "RootMotionBakeModifier.generated.h"

/**
 * URootMotionBakeModifier
 *
 * 针对 ZZZ 拆包动画：整体前进位移(伪 root motion)烘成曲线，并把水平位移移除做成原地动画。
 *
 * 使用方式：
 *   1. 编译后，内容浏览器选中一个或多个 AnimSequence，右键 -> 应用动画修改器(Apply Animation Modifier)
 *      -> 选择 RootMotionBakeModifier。也可在 AnimBP 的 Anim Sequence 资产上添加修改器堆栈后一键应用。
 *   2. 首次务必保持 bVerifyOnly = true：只在 Output Log 打印每根骨骼轨道的位移分析，不改动画。
 *      看日志确认能读到源数据、以及哪根骨骼承载位移。
 *   3. 确认无误并做好版本控制后，把 bVerifyOnly 设为 false 再应用，执行烘焙 + 移除。
 *
 * 注意：移除位移是破坏性修改。OnRevert 只能移除新增曲线，无法恢复被移除的骨骼位移，
 *       请依赖版本控制/资产备份回退。
 */
UCLASS()
class GGYGOEDITOR_API URootMotionBakeModifier : public UAnimationModifier
{
	GENERATED_BODY()

public:
	/** 仅分析并打印，不修改动画。首次应用请保持勾选。 */
	UPROPERTY(EditAnywhere, Category = "RootMotion")
	bool bVerifyOnly = true;

	/** 净水平位移小于该值视为原地动画，跳过处理（cm）。 */
	UPROPERTY(EditAnywhere, Category = "RootMotion")
	float MinNetDisplacement = 20.f;

	/** 冻结水平位移时是否保留竖直(Z)分量（保留骨盆起伏）。 */
	UPROPERTY(EditAnywhere, Category = "RootMotion")
	bool bKeepVertical = true;

	/** 是否烘焙曲线。 */
	UPROPERTY(EditAnywhere, Category = "RootMotion")
	bool bBakeCurves = true;

	/** 是否移除水平位移做成原地动画。 */
	UPROPERTY(EditAnywhere, Category = "RootMotion")
	bool bStripMotion = true;

	/** 手动指定载体骨骼名；留空则自动选水平净位移最大的骨骼。 */
	UPROPERTY(EditAnywhere, Category = "RootMotion")
	FName OverrideMotionBone = NAME_None;

	UPROPERTY(EditAnywhere, Category = "RootMotion|Curves")
	FName CurvePosX = "RM_PosX";

	UPROPERTY(EditAnywhere, Category = "RootMotion|Curves")
	FName CurvePosY = "RM_PosY";

	UPROPERTY(EditAnywhere, Category = "RootMotion|Curves")
	FName CurveDist = "RM_Dist";

	UPROPERTY(EditAnywhere, Category = "RootMotion|Curves")
	FName CurveSpeed = "RM_Speed";

	virtual void OnApply_Implementation(UAnimSequence* AnimationSequence) override;
	virtual void OnRevert_Implementation(UAnimSequence* AnimationSequence) override;
};
