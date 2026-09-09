// Copyright Epic Games, Inc. All Rights Reserved.

#include "RootMotionBakeModifier.h"

#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimCurveTypes.h"
#include "AnimationBlueprintLibrary.h"

DEFINE_LOG_CATEGORY_STATIC(LogRootMotionBake, Log, All);

namespace
{
	// 单根骨骼轨道的位移统计
	struct FTrackStat
	{
		FName Name;
		int32 NumPosKeys = 0;
		float NetHorizontal = 0.f;   // 末-首 水平净位移
		float PathHorizontal = 0.f;  // 逐帧累计水平路程
	};

	float Horizontal(const FVector3f& A, const FVector3f& B)
	{
		return FMath::Sqrt(FMath::Square(A.X - B.X) + FMath::Square(A.Y - B.Y));
	}
}

void URootMotionBakeModifier::OnApply_Implementation(UAnimSequence* AnimationSequence)
{
	if (!AnimationSequence)
	{
		UE_LOG(LogRootMotionBake, Error, TEXT("AnimationSequence 为空。"));
		return;
	}

	const IAnimationDataModel* Model = AnimationSequence->GetDataModel();
	if (!Model)
	{
		UE_LOG(LogRootMotionBake, Error, TEXT("[%s] 拿不到 DataModel。"), *AnimationSequence->GetName());
		return;
	}

	const FString AssetName = AnimationSequence->GetName();
	const int32 NumKeys = Model->GetNumberOfKeys();
	const float Length = AnimationSequence->GetPlayLength();

	// 读取全部骨骼动画轨道（C++ 直接访问数据模型，不走 Python 读不到的 GetRawTrackData）
	TArrayView<const FBoneAnimationTrack> Tracks = Model->GetBoneAnimationTracks();
	if (Tracks.Num() == 0)
	{
		UE_LOG(LogRootMotionBake, Error,
			TEXT("[%s] 数据模型骨骼轨道为空 —— C++ 也读不到源数据(属于 case b)，此路不通。"),
			*AssetName);
		return;
	}

	// 统计每根轨道位移
	TArray<FTrackStat> Stats;
	Stats.Reserve(Tracks.Num());
	for (const FBoneAnimationTrack& Track : Tracks)
	{
		const TArray<FVector3f>& Pos = Track.InternalTrackData.PosKeys;
		FTrackStat S;
		S.Name = Track.Name;
		S.NumPosKeys = Pos.Num();
		if (Pos.Num() >= 2)
		{
			S.NetHorizontal = Horizontal(Pos.Last(), Pos[0]);
			float Path = 0.f;
			for (int32 i = 1; i < Pos.Num(); ++i)
			{
				Path += Horizontal(Pos[i], Pos[i - 1]);
			}
			S.PathHorizontal = Path;
		}
		Stats.Add(S);
	}

	// 找载体：优先手动指定，否则取水平净位移最大者
	int32 CarrierIdx = INDEX_NONE;
	if (!OverrideMotionBone.IsNone())
	{
		CarrierIdx = Stats.IndexOfByPredicate([this](const FTrackStat& S) { return S.Name == OverrideMotionBone; });
		if (CarrierIdx == INDEX_NONE)
		{
			UE_LOG(LogRootMotionBake, Warning, TEXT("[%s] 未找到指定骨骼 %s，回退自动选择。"),
				*AssetName, *OverrideMotionBone.ToString());
		}
	}
	if (CarrierIdx == INDEX_NONE)
	{
		float Best = -1.f;
		for (int32 i = 0; i < Stats.Num(); ++i)
		{
			if (Stats[i].NetHorizontal > Best)
			{
				Best = Stats[i].NetHorizontal;
				CarrierIdx = i;
			}
		}
	}

	const FTrackStat& Carrier = Stats[CarrierIdx];

	UE_LOG(LogRootMotionBake, Log,
		TEXT("==== [%s] 帧键=%d 时长=%.3f 轨道=%d 载体=%s(键=%d 净水平=%.1f 路程=%.1f) ===="),
		*AssetName, NumKeys, Length, Tracks.Num(),
		*Carrier.Name.ToString(), Carrier.NumPosKeys, Carrier.NetHorizontal, Carrier.PathHorizontal);

	// 打印位移最大的前若干轨道，便于确认载体是否正确
	{
		TArray<FTrackStat> Sorted = Stats;
		Sorted.Sort([](const FTrackStat& A, const FTrackStat& B) { return A.NetHorizontal > B.NetHorizontal; });
		const int32 TopN = FMath::Min(10, Sorted.Num());
		UE_LOG(LogRootMotionBake, Log, TEXT("  -- 水平净位移前 %d --"), TopN);
		for (int32 i = 0; i < TopN; ++i)
		{
			UE_LOG(LogRootMotionBake, Log, TEXT("    %-26s 键=%d 净水平=%.2f 路程=%.2f"),
				*Sorted[i].Name.ToString(), Sorted[i].NumPosKeys, Sorted[i].NetHorizontal, Sorted[i].PathHorizontal);
		}
	}

	if (bVerifyOnly)
	{
		UE_LOG(LogRootMotionBake, Log, TEXT("  -> bVerifyOnly=true：仅分析，不修改。"));
		return;
	}

	if (Carrier.NetHorizontal < MinNetDisplacement)
	{
		UE_LOG(LogRootMotionBake, Log, TEXT("  -> 净位移<%.1f，视为原地动画，跳过。"), MinNetDisplacement);
		return;
	}

	// 取载体原始轨道键
	const FBoneAnimationTrack& CarrierTrack = Tracks[CarrierIdx];
	const TArray<FVector3f>& Pos = CarrierTrack.InternalTrackData.PosKeys;
	const TArray<FQuat4f>& Rot = CarrierTrack.InternalTrackData.RotKeys;
	const TArray<FVector3f>& Scale = CarrierTrack.InternalTrackData.ScaleKeys;
	const int32 N = Pos.Num();
	if (N < 2)
	{
		UE_LOG(LogRootMotionBake, Warning, TEXT("  -> 载体位移键<2，跳过。"));
		return;
	}

	const float Dt = (N > 1) ? (Length / (N - 1)) : 0.f;
	const FVector3f P0 = Pos[0];

	IAnimationDataController& Controller = AnimationSequence->GetController();
	Controller.OpenBracket(FText::FromString(TEXT("RootMotion Bake & Strip")));

	// 1) 烘焙曲线（相对首帧）
	if (bBakeCurves)
	{
		TArray<float> Times, ValX, ValY, ValDist, ValSpeed;
		Times.Reserve(N); ValX.Reserve(N); ValY.Reserve(N); ValDist.Reserve(N); ValSpeed.Reserve(N);
		float Acc = 0.f;
		for (int32 i = 0; i < N; ++i)
		{
			Times.Add(i * Dt);
			ValX.Add(Pos[i].X - P0.X);
			ValY.Add(Pos[i].Y - P0.Y);
			if (i > 0)
			{
				const float Step = Horizontal(Pos[i], Pos[i - 1]);
				Acc += Step;
				ValSpeed.Add(Dt > 0.f ? Step / Dt : 0.f);
			}
			else
			{
				ValSpeed.Add(0.f);
			}
			ValDist.Add(Acc);
		}

		auto WriteCurve = [AnimationSequence](FName Name, const TArray<float>& Times2, const TArray<float>& Vals)
		{
			if (UAnimationBlueprintLibrary::DoesCurveExist(AnimationSequence, Name, ERawCurveTrackTypes::RCT_Float))
			{
				UAnimationBlueprintLibrary::RemoveCurve(AnimationSequence, Name);
			}
			UAnimationBlueprintLibrary::AddCurve(AnimationSequence, Name, ERawCurveTrackTypes::RCT_Float, false);
			UAnimationBlueprintLibrary::AddFloatCurveKeys(AnimationSequence, Name, Times2, Vals);
		};

		WriteCurve(CurvePosX, Times, ValX);
		WriteCurve(CurvePosY, Times, ValY);
		WriteCurve(CurveDist, Times, ValDist);
		WriteCurve(CurveSpeed, Times, ValSpeed);
		UE_LOG(LogRootMotionBake, Log, TEXT("  -> 已烘焙曲线 %s/%s/%s/%s"),
			*CurvePosX.ToString(), *CurvePosY.ToString(), *CurveDist.ToString(), *CurveSpeed.ToString());
	}

	// 2) 移除水平位移（冻结到首帧，保留竖直与旋转）
	if (bStripMotion)
	{
		TArray<FVector3f> NewPos;
		NewPos.Reserve(N);
		for (int32 i = 0; i < N; ++i)
		{
			const float Z = bKeepVertical ? Pos[i].Z : P0.Z;
			NewPos.Add(FVector3f(P0.X, P0.Y, Z));
		}
		Controller.SetBoneTrackKeys(Carrier.Name, NewPos, Rot, Scale);
		UE_LOG(LogRootMotionBake, Log, TEXT("  -> 已冻结 %s 水平位移(原地化)。"), *Carrier.Name.ToString());
	}

	Controller.CloseBracket();
	UE_LOG(LogRootMotionBake, Log, TEXT("  -> 完成。请检查动画后保存资产。"));
}

void URootMotionBakeModifier::OnRevert_Implementation(UAnimSequence* AnimationSequence)
{
	if (!AnimationSequence)
	{
		return;
	}

	// 只能撤销新增曲线；被移除的骨骼位移无法在此恢复，请用版本控制回退。
	for (const FName& Name : { CurvePosX, CurvePosY, CurveDist, CurveSpeed })
	{
		if (UAnimationBlueprintLibrary::DoesCurveExist(AnimationSequence, Name, ERawCurveTrackTypes::RCT_Float))
		{
			UAnimationBlueprintLibrary::RemoveCurve(AnimationSequence, Name);
		}
	}
	UE_LOG(LogRootMotionBake, Log, TEXT("[%s] 已移除烘焙曲线。骨骼位移不可自动恢复，请用版本控制回退。"),
		*AnimationSequence->GetName());
}
