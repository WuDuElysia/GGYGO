// Copyright Epic Games, Inc. All Rights Reserved.

#include "GGYGOAnimationCurveReadLibrary.h"

#include "Animation/AnimSequence.h"
#include "Animation/AnimData/CurveIdentifier.h"
#include "Animation/AnimData/IAnimationDataModel.h"

namespace
{
	bool IsRecognized(ERichCurveInterpMode Mode)
	{
		switch (Mode)
		{
		case RCIM_Linear:
		case RCIM_Constant:
		case RCIM_Cubic:
		case RCIM_None:
			return true;
		default:
			return false;
		}
	}

	bool IsRecognized(ERichCurveTangentMode Mode)
	{
		switch (Mode)
		{
		case RCTM_Auto:
		case RCTM_User:
		case RCTM_Break:
		case RCTM_None:
		case RCTM_SmartAuto:
			return true;
		default:
			return false;
		}
	}

	bool IsRecognized(ERichCurveTangentWeightMode Mode)
	{
		switch (Mode)
		{
		case RCTWM_WeightedNone:
		case RCTWM_WeightedArrive:
		case RCTWM_WeightedLeave:
		case RCTWM_WeightedBoth:
			return true;
		default:
			return false;
		}
	}

	bool IsRecognized(ERichCurveExtrapolation Mode)
	{
		switch (Mode)
		{
		case RCCE_Cycle:
		case RCCE_CycleWithOffset:
		case RCCE_Oscillate:
		case RCCE_Linear:
		case RCCE_Constant:
		case RCCE_None:
			return true;
		default:
			return false;
		}
	}

	bool ValidateCurveSnapshot(const FFloatCurve& Curve, FString& OutError)
	{
		const FRichCurve& RichCurve = Curve.FloatCurve;
		const FString Prefix = FString::Printf(TEXT("Curve '%s'"), *Curve.GetName().ToString());
		// MAX_flt is the engine's unset-default sentinel and is finite; preserve it.
		if (!FMath::IsFinite(RichCurve.DefaultValue))
		{
			OutError = Prefix + TEXT(".DefaultValue is non-finite.");
			return false;
		}
		if (!IsRecognized(RichCurve.PreInfinityExtrap.GetValue()))
		{
			OutError = Prefix + FString::Printf(TEXT(".PreInfinityExtrap has unrecognized enum value %d."),
				static_cast<int32>(RichCurve.PreInfinityExtrap.GetValue()));
			return false;
		}
		if (!IsRecognized(RichCurve.PostInfinityExtrap.GetValue()))
		{
			OutError = Prefix + FString::Printf(TEXT(".PostInfinityExtrap has unrecognized enum value %d."),
				static_cast<int32>(RichCurve.PostInfinityExtrap.GetValue()));
			return false;
		}

		const TArray<FRichCurveKey>& Keys = RichCurve.GetConstRefOfKeys();
		for (int32 Index = 0; Index < Keys.Num(); ++Index)
		{
			const FRichCurveKey& Key = Keys[Index];
			const FString KeyPrefix = Prefix + FString::Printf(TEXT(".Keys[%d]"), Index);
			const TPair<const TCHAR*, float> NumericFields[] =
			{
				{TEXT("Time"), Key.Time},
				{TEXT("Value"), Key.Value},
				{TEXT("ArriveTangent"), Key.ArriveTangent},
				{TEXT("LeaveTangent"), Key.LeaveTangent},
				{TEXT("ArriveTangentWeight"), Key.ArriveTangentWeight},
				{TEXT("LeaveTangentWeight"), Key.LeaveTangentWeight},
			};
			for (const auto& Field : NumericFields)
			{
				if (!FMath::IsFinite(Field.Value))
				{
					OutError = KeyPrefix + FString::Printf(TEXT(".%s is non-finite."), Field.Key);
					return false;
				}
			}
			if (!IsRecognized(Key.InterpMode.GetValue()))
			{
				OutError = KeyPrefix + FString::Printf(TEXT(".InterpMode has unrecognized enum value %d."),
					static_cast<int32>(Key.InterpMode.GetValue()));
				return false;
			}
			if (!IsRecognized(Key.TangentMode.GetValue()))
			{
				OutError = KeyPrefix + FString::Printf(TEXT(".TangentMode has unrecognized enum value %d."),
					static_cast<int32>(Key.TangentMode.GetValue()));
				return false;
			}
			if (!IsRecognized(Key.TangentWeightMode.GetValue()))
			{
				OutError = KeyPrefix + FString::Printf(TEXT(".TangentWeightMode has unrecognized enum value %d."),
					static_cast<int32>(Key.TangentWeightMode.GetValue()));
				return false;
			}
		}
		return true;
	}
}

bool UGGYGOAnimationCurveReadLibrary::ReadFloatCurves(
	const UAnimSequence* Source,
	const TArray<FName>& CurveNames,
	TArray<FFloatCurve>& OutCurves,
	double& OutDurationSeconds,
	FString& OutError)
{
	OutCurves.Reset();
	OutDurationSeconds = 0.0;
	OutError.Reset();
	const bool bValidSource = IsValid(Source);
	const FString SourcePath = bValidSource ? Source->GetPathName() : TEXT("<null-or-invalid>");
	auto Fail = [&OutError, &SourcePath](const FString& Detail)
	{
		OutError = FString::Printf(TEXT("ReadFloatCurves[%s]: %s"), *SourcePath, *Detail);
		return false;
	};
	if (!bValidSource)
	{
		return Fail(TEXT("Source is null or invalid."));
	}
	if (CurveNames.IsEmpty())
	{
		return Fail(TEXT("CurveNames is empty."));
	}
	TSet<FName> SeenNames;
	for (int32 Index = 0; Index < CurveNames.Num(); ++Index)
	{
		const FName Name = CurveNames[Index];
		if (Name.IsNone())
		{
			return Fail(FString::Printf(TEXT("CurveNames[%d] is None."), Index));
		}
		if (SeenNames.Contains(Name))
		{
			return Fail(FString::Printf(TEXT("CurveNames[%d] duplicates '%s'."), Index, *Name.ToString()));
		}
		SeenNames.Add(Name);
	}
	const IAnimationDataModel* Model = Source->GetDataModel();
	if (!Model)
	{
		return Fail(TEXT("Source has no existing DataModel."));
	}
	const double Duration = static_cast<double>(Source->GetPlayLength());
	if (!FMath::IsFinite(Duration) || Duration <= 0.0)
	{
		return Fail(TEXT("Source.PlayLength must be finite and positive."));
	}

	TArray<FFloatCurve> Candidate;
	Candidate.Reserve(CurveNames.Num());
	for (const FName Name : CurveNames)
	{
		const FFloatCurve* Curve = Model->FindFloatCurve(FAnimationCurveIdentifier(Name, ERawCurveTrackTypes::RCT_Float));
		if (!Curve)
		{
			return Fail(FString::Printf(TEXT("Curve '%s' is missing from the current DataModel."), *Name.ToString()));
		}
		FString CurveError;
		if (!ValidateCurveSnapshot(*Curve, CurveError))
		{
			return Fail(CurveError);
		}
		Candidate.Add(*Curve);
	}
	OutCurves = MoveTemp(Candidate);
	OutDurationSeconds = Duration;
	return true;
}
