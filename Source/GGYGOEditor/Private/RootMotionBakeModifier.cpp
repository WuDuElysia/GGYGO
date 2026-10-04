// Copyright Epic Games, Inc. All Rights Reserved.

#include "RootMotionBakeModifier.h"

#include "Animation/AnimSequence.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimCurveTypes.h"
#include "Animation/AnimTypes.h"
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

	SnapshotVersion = 1;
	CurveChanges.Reset();
	ChangedBone = NAME_None;
	BoneBefore.Reset();
	BoneAfter.Reset();

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
	TArray<FBoneAnimationTrack> Tracks;
	TArray<FName> TrackNames;
	Model->GetBoneTrackNames(TrackNames);
	for (FName Name : TrackNames)
	{
		TArray<FTransform> Keys;
		Model->GetBoneTrackTransforms(Name, Keys);
		FBoneAnimationTrack& Track = Tracks.AddDefaulted_GetRef();
		Track.Name = Name;
		for (const FTransform& Key : Keys)
		{
			Track.InternalTrackData.PosKeys.Add(FVector3f(Key.GetTranslation()));
			Track.InternalTrackData.RotKeys.Add(FQuat4f(Key.GetRotation()));
			Track.InternalTrackData.ScaleKeys.Add(FVector3f(Key.GetScale3D()));
		}
	}
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
			UE_LOG(LogRootMotionBake, Warning, TEXT("[%s] 未找到指定骨骼 %s，停止以免修改错误轨道。"),
				*AssetName, *OverrideMotionBone.ToString());
			return;
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

	if (bBakeCurves)
	{
		TSet<FName> Names { CurvePosX, CurvePosY, CurveDist, CurveSpeed };
		if (Names.Num() != 4 || Names.Contains(NAME_None))
		{
			UE_LOG(LogAnimation, Error, TEXT("RootMotionBake: curve names must be nonempty and distinct."));
			return;
		}
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

		auto WriteCurve = [this, Model, &Controller](FName Name, const TArray<float>& Times2, const TArray<float>& Vals)
		{
			const FAnimationCurveIdentifier Id(Name, ERawCurveTrackTypes::RCT_Float);
			FRootMotionBakeCurveChange Change;
			if (const FFloatCurve* Existing = Model->FindFloatCurve(Id))
			{
				Change.bExisted = true;
				Change.Before = *Existing;
			}
			else if (!Controller.AddCurve(Id))
			{
				UE_LOG(LogAnimation, Error, TEXT("RootMotionBake: cannot create curve %s"), *Name.ToString());
				return;
			}
			TArray<FRichCurveKey> Keys;
			for (int32 Index = 0; Index < Times2.Num(); ++Index)
			{
				FRichCurveKey& Key = Keys.Emplace_GetRef(Times2[Index], Vals[Index]);
				Key.InterpMode = RCIM_Linear;
			}
			if (!Controller.SetCurveKeys(Id, Keys))
				UE_LOG(LogAnimation, Error, TEXT("RootMotionBake: cannot write curve %s"), *Name.ToString());
			if (const FFloatCurve* Written = Model->FindFloatCurve(Id))
			{
				Change.After = *Written;
				CurveChanges.Add(MoveTemp(Change));
			}
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
		Model->GetBoneTrackTransforms(Carrier.Name, BoneBefore);
		if (Controller.SetBoneTrackKeys(Carrier.Name, NewPos, Rot, Scale))
		{
			ChangedBone = Carrier.Name;
			Model->GetBoneTrackTransforms(ChangedBone, BoneAfter);
		}
		else
		{
			UE_LOG(LogAnimation, Error, TEXT("RootMotionBake: cannot write bone track"));
		}
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

	if (SnapshotVersion == 0)
	{
		// Old verify-only applications never owned any data. Old destructive applications
		// have no recoverable baseline; fail so the engine rolls back the entire reapply.
		if (!bVerifyOnly)
			UE_LOG(LogAnimation, Error, TEXT("RootMotionBake: legacy application has no snapshot; restore from source before reapply."));
		return;
	}
	const IAnimationDataModel* Model = AnimationSequence->GetDataModel();
	if (!Model) return;
	// Validate ALL owned changes before touching anything. Never erase later edits.
	for (const auto& Change : CurveChanges)
	{
		const FFloatCurve* Current = Model->FindFloatCurve(FAnimationCurveIdentifier(Change.After.GetName(), ERawCurveTrackTypes::RCT_Float));
		if (!Current || !FFloatCurve::StaticStruct()->CompareScriptStruct(Current, &Change.After, 0))
		{
			UE_LOG(LogAnimation, Error, TEXT("RootMotionBake: curve changed after apply; revert refused."));
			return;
		}
	}
	if (!ChangedBone.IsNone())
	{
		TArray<FTransform> Current;
		Model->GetBoneTrackTransforms(ChangedBone, Current);
		bool bMatches = Current.Num() == BoneAfter.Num();
		for (int32 Index = 0; bMatches && Index < Current.Num(); ++Index)
			bMatches = Current[Index].Equals(BoneAfter[Index], 0.000001);
		if (!bMatches)
		{
			UE_LOG(LogAnimation, Error, TEXT("RootMotionBake: bone changed after apply; revert refused."));
			return;
		}
	}
	IAnimationDataController& Controller = AnimationSequence->GetController();
	Controller.OpenBracket(FText::FromString(TEXT("Restore root motion bake snapshot")));
	bool bAllRestored = true;
	for (const auto& Change : CurveChanges)
	{
		const FAnimationCurveIdentifier Id(Change.After.GetName(), ERawCurveTrackTypes::RCT_Float);
		// Apply changed only keys on existing curves, retaining flags/color/attributes.
		const bool bRestored = Change.bExisted
			? Controller.SetCurveKeys(Id, Change.Before.FloatCurve.GetConstRefOfKeys())
			: Controller.RemoveCurve(Id);
		bAllRestored &= bRestored;
		if (!bRestored) UE_LOG(LogAnimation, Error, TEXT("RootMotionBake: failed restoring curve"));
	}
	if (!ChangedBone.IsNone())
	{
		TArray<FVector> Positions, Scales;
		TArray<FQuat> Rotations;
		for (const FTransform& Key : BoneBefore)
		{
			Positions.Add(Key.GetTranslation()); Rotations.Add(Key.GetRotation()); Scales.Add(Key.GetScale3D());
		}
		if (!Controller.SetBoneTrackKeys(ChangedBone, Positions, Rotations, Scales))
		{
			bAllRestored = false;
			UE_LOG(LogAnimation, Error, TEXT("RootMotionBake: failed restoring bone"));
		}
	}
	Controller.CloseBracket();
	if (bAllRestored)
	{
		CurveChanges.Reset(); ChangedBone = NAME_None; BoneBefore.Reset(); BoneAfter.Reset();
	}
}
