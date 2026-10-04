// Copyright Epic Games, Inc. All Rights Reserved.

#include "GGYGOAnimationCurveSnapshotLibrary.h"

#include "GGYGOAnimationCurveReadLibrary.h"

FGGYGOFloatCurveReadResult UGGYGOAnimationCurveSnapshotLibrary::ReadFloatCurveSnapshot(
	const UAnimSequence* Source,
	const TArray<FName>& CurveNames)
{
	FGGYGOFloatCurveReadResult Result;
	TArray<FFloatCurve> NativeCurves;
	double NativeDurationSeconds = 0.0;
	FString NativeError;
	const bool bReadSucceeded = UGGYGOAnimationCurveReadLibrary::ReadFloatCurves(
		Source, CurveNames, NativeCurves, NativeDurationSeconds, NativeError);
	Result.Error = MoveTemp(NativeError);
	if (!bReadSucceeded)
	{
		return Result;
	}

	TArray<FGGYGOFloatCurveSnapshot> CandidateCurves;
	CandidateCurves.Reserve(NativeCurves.Num());
	for (const FFloatCurve& NativeCurve : NativeCurves)
	{
		FGGYGOFloatCurveSnapshot& Curve = CandidateCurves.AddDefaulted_GetRef();
		Curve.Name = NativeCurve.GetName();
		Curve.Flags = NativeCurve.GetCurveTypeFlags();
		Curve.DefaultValue = NativeCurve.FloatCurve.DefaultValue;
		Curve.PreInfinityExtrap = static_cast<int32>(NativeCurve.FloatCurve.PreInfinityExtrap.GetValue());
		Curve.PostInfinityExtrap = static_cast<int32>(NativeCurve.FloatCurve.PostInfinityExtrap.GetValue());

		const TArray<FRichCurveKey>& NativeKeys = NativeCurve.FloatCurve.GetConstRefOfKeys();
		Curve.Keys.Reserve(NativeKeys.Num());
		for (const FRichCurveKey& NativeKey : NativeKeys)
		{
			FGGYGOFloatCurveKeySnapshot& Key = Curve.Keys.AddDefaulted_GetRef();
			Key.Time = NativeKey.Time;
			Key.Value = NativeKey.Value;
			Key.ArriveTangent = NativeKey.ArriveTangent;
			Key.LeaveTangent = NativeKey.LeaveTangent;
			Key.ArriveTangentWeight = NativeKey.ArriveTangentWeight;
			Key.LeaveTangentWeight = NativeKey.LeaveTangentWeight;
			Key.InterpMode = static_cast<int32>(NativeKey.InterpMode.GetValue());
			Key.TangentMode = static_cast<int32>(NativeKey.TangentMode.GetValue());
			Key.TangentWeightMode = static_cast<int32>(NativeKey.TangentWeightMode.GetValue());
		}
	}

	Result.Curves = MoveTemp(CandidateCurves);
	Result.DurationSeconds = NativeDurationSeconds;
	Result.bSucceeded = true;
	return Result;
}
