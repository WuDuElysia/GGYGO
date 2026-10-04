// Copyright Epic Games, Inc. All Rights Reserved.

#if WITH_DEV_AUTOMATION_TESTS
#include "GGYGOAnimationCurveReadLibrary.h"
#include "AnimationAssetSafetyTestUtils.h"
#include "Animation/AnimData/CurveIdentifier.h"
#include "Misc/AutomationTest.h"
#include "UObject/UObjectGlobals.h"

namespace
{
	bool CheckCurve(FAutomationTestBase& Test, const FString& Label, const FFloatCurve& Actual, const FFloatCurve& Expected)
	{
		bool bSame = Test.TestEqual(Label + TEXT(".Name"), Actual.GetName(), Expected.GetName());
		bSame &= Test.TestEqual(Label + TEXT(".Flags"), Actual.GetCurveTypeFlags(), Expected.GetCurveTypeFlags());
		const FRichCurve& A = Actual.FloatCurve;
		const FRichCurve& E = Expected.FloatCurve;
		// Explicit exact field comparisons: native curve/key equality omits defaults/weights.
		bSame &= Test.TestTrue(Label + TEXT(".DefaultValue"), A.DefaultValue == E.DefaultValue);
		bSame &= Test.TestEqual(Label + TEXT(".PreInfinityExtrap"), static_cast<int32>(A.PreInfinityExtrap.GetValue()), static_cast<int32>(E.PreInfinityExtrap.GetValue()));
		bSame &= Test.TestEqual(Label + TEXT(".PostInfinityExtrap"), static_cast<int32>(A.PostInfinityExtrap.GetValue()), static_cast<int32>(E.PostInfinityExtrap.GetValue()));
		const TArray<FRichCurveKey>& ActualKeys = A.GetConstRefOfKeys();
		const TArray<FRichCurveKey>& ExpectedKeys = E.GetConstRefOfKeys();
		if (!Test.TestEqual(Label + TEXT(".KeyCount"), ActualKeys.Num(), ExpectedKeys.Num())) { return false; }
		for (int32 Index = 0; Index < ActualKeys.Num(); ++Index)
		{
			const FRichCurveKey& AK = ActualKeys[Index];
			const FRichCurveKey& EK = ExpectedKeys[Index];
			const FString K = Label + FString::Printf(TEXT(".Keys[%d]"), Index);
			bSame &= Test.TestTrue(K + TEXT(".Time"), AK.Time == EK.Time);
			bSame &= Test.TestTrue(K + TEXT(".Value"), AK.Value == EK.Value);
			bSame &= Test.TestEqual(K + TEXT(".InterpMode"), static_cast<int32>(AK.InterpMode.GetValue()), static_cast<int32>(EK.InterpMode.GetValue()));
			bSame &= Test.TestEqual(K + TEXT(".TangentMode"), static_cast<int32>(AK.TangentMode.GetValue()), static_cast<int32>(EK.TangentMode.GetValue()));
			bSame &= Test.TestEqual(K + TEXT(".TangentWeightMode"), static_cast<int32>(AK.TangentWeightMode.GetValue()), static_cast<int32>(EK.TangentWeightMode.GetValue()));
			bSame &= Test.TestTrue(K + TEXT(".ArriveTangent"), AK.ArriveTangent == EK.ArriveTangent);
			bSame &= Test.TestTrue(K + TEXT(".LeaveTangent"), AK.LeaveTangent == EK.LeaveTangent);
			bSame &= Test.TestTrue(K + TEXT(".ArriveTangentWeight"), AK.ArriveTangentWeight == EK.ArriveTangentWeight);
			bSame &= Test.TestTrue(K + TEXT(".LeaveTangentWeight"), AK.LeaveTangentWeight == EK.LeaveTangentWeight);
		}
		return bSame;
	}

	struct FSourceSnapshot
	{
		TArray<FFloatCurve> Curves;
		double PlayLength = 0.0;
		bool bHasModel = false;
		bool bDirty = false;
	};

	FSourceSnapshot CaptureSource(const UAnimSequence* Source)
	{
		FSourceSnapshot Snapshot;
		if (Source)
		{
			const IAnimationDataModel* Model = Source->GetDataModel();
			Snapshot.bHasModel = Model != nullptr;
			if (Model) { Snapshot.Curves = Model->GetFloatCurves(); }
			Snapshot.PlayLength = static_cast<double>(Source->GetPlayLength());
			Snapshot.bDirty = Source->GetPackage()->IsDirty();
		}
		return Snapshot;
	}

	bool CheckSourceUnchanged(FAutomationTestBase& Test, const FString& Label, const UAnimSequence* Source, const FSourceSnapshot& Before)
	{
		const FSourceSnapshot After = CaptureSource(Source);
		bool bSame = Test.TestEqual(Label + TEXT(".ModelPresent"), After.bHasModel, Before.bHasModel);
		bSame &= Test.TestTrue(Label + TEXT(".PlayLength"), After.PlayLength == Before.PlayLength);
		bSame &= Test.TestEqual(Label + TEXT(".PackageDirty"), After.bDirty, Before.bDirty);
		bSame &= Test.TestEqual(Label + TEXT(".CurveCount"), After.Curves.Num(), Before.Curves.Num());
		// Compare public curve content by name, not derived cache addresses/order or raw memory bytes.
		for (const FFloatCurve& Expected : Before.Curves)
		{
			const FFloatCurve* Actual = After.Curves.FindByPredicate([&Expected](const FFloatCurve& Curve) { return Curve.GetName() == Expected.GetName(); });
			if (!Test.TestNotNull(Label + TEXT(".CurvePresent.") + Expected.GetName().ToString(), Actual)) { return false; }
			bSame &= CheckCurve(Test, Label + TEXT(".") + Expected.GetName().ToString(), *Actual, Expected);
		}
		return bSame;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FAnimationCurveReadbackTest, "GGYGO.Editor.Animation.FloatCurveReadback",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FAnimationCurveReadbackTest::RunTest(const FString& Parameters)
{
	UPackage* Package = AnimationAssetSafetyTests::Package();
	Package->SetFlags(RF_Transient);
	UAnimSequence* Source = AnimationAssetSafetyTests::Sequence(Package);
	if (!TestNotNull(TEXT("Real animation fixture"), Source)) { return false; }
	Source->SetFlags(RF_Transient);
	const IAnimationDataModel* Model = Source->GetDataModel();
	if (!TestNotNull(TEXT("Existing real DataModel"), Model)
		|| !TestTrue(TEXT("Positive finite actual source duration"), FMath::IsFinite(Source->GetPlayLength()) && Source->GetPlayLength() > 0.f)) { return false; }
	IAnimationDataController& Controller = Source->GetController();
	const FName WeightedName(TEXT("ReadbackWeighted"));
	const FName EmptyName(TEXT("ReadbackEmpty"));
	const FName OutsideName(TEXT("ReadbackOutside"));
	const FName ProbeName(TEXT("ReadbackModeProbe"));
	const FName MissingName(TEXT("ReadbackMissing"));
	auto FindCurve = [Model](FName Name)
	{
		return Model->FindFloatCurve(FAnimationCurveIdentifier(Name, ERawCurveTrackTypes::RCT_Float));
	};
	auto AddCurve = [&](FName Name, const TArray<FRichCurveKey>& Keys, int32 Flags, ERichCurveExtrapolation Pre, ERichCurveExtrapolation Post)
	{
		const FAnimationCurveIdentifier Id(Name, ERawCurveTrackTypes::RCT_Float);
		FCurveAttributes Attributes;
		Attributes.SetPreExtrapolation(Pre);
		Attributes.SetPostExtrapolation(Post);
		return TestTrue(TEXT("Public AddCurve"), Controller.AddCurve(Id, Flags, false))
			&& TestTrue(TEXT("Public SetCurveKeys"), Controller.SetCurveKeys(Id, Keys, false))
			&& TestTrue(TEXT("Public SetCurveFlags"), Controller.SetCurveFlags(Id, Flags, false))
			&& TestTrue(TEXT("Public SetCurveAttributes"), Controller.SetCurveAttributes(Id, Attributes, false));
	};
	TArray<FRichCurveKey> WeightedKeys = {FRichCurveKey(0.f, -3.f), FRichCurveKey(1.f, 4.f)};
	for (int32 Index = 0; Index < WeightedKeys.Num(); ++Index)
	{
		FRichCurveKey& Key = WeightedKeys[Index];
		Key.InterpMode = RCIM_Cubic;
		Key.TangentMode = RCTM_Break;
		Key.TangentWeightMode = RCTWM_WeightedBoth;
		Key.ArriveTangent = Index == 0 ? 1.5f : -1.25f;
		Key.LeaveTangent = Index == 0 ? 2.5f : -0.75f;
		Key.ArriveTangentWeight = Index == 0 ? 0.2f : 0.45f;
		Key.LeaveTangentWeight = Index == 0 ? 0.35f : 0.65f;
	}
	const int32 WeightedFlags = AACF_Editable | AACF_Disabled;
	if (!AddCurve(WeightedName, WeightedKeys, WeightedFlags, RCCE_CycleWithOffset, RCCE_Linear)
		|| !AddCurve(EmptyName, {}, AACF_NONE, RCCE_None, RCCE_None)
		|| !AddCurve(OutsideName, {FRichCurveKey(-1.f, -5.f), FRichCurveKey(2.f, 0.f)}, AACF_Editable, RCCE_Oscillate, RCCE_Constant)
		|| !AddCurve(ProbeName, WeightedKeys, AACF_Editable, RCCE_Constant, RCCE_Constant)) { return false; }

	// Never assume Controller preserved the input: inspect its actual public Model first.
	const FSourceSnapshot Fixture = CaptureSource(Source);
	auto FixtureCurve = [&Fixture](FName Name)
	{
		return Fixture.Curves.FindByPredicate([Name](const FFloatCurve& Curve) { return Curve.GetName() == Name; });
	};
	const FFloatCurve* Weighted = FixtureCurve(WeightedName);
	if (!TestNotNull(TEXT("Actual weighted curve"), Weighted)
		|| !TestEqual(TEXT("Actual weighted key count"), Weighted->FloatCurve.GetConstRefOfKeys().Num(), 2)
		|| !TestEqual(TEXT("Actual weighted flags"), Weighted->GetCurveTypeFlags(), WeightedFlags)) { return false; }
	for (const FRichCurveKey& Key : Weighted->FloatCurve.GetConstRefOfKeys())
	{
		if (!TestEqual(TEXT("Actual cubic mode"), static_cast<int32>(Key.InterpMode.GetValue()), static_cast<int32>(RCIM_Cubic))
			|| !TestEqual(TEXT("Actual manual tangent mode"), static_cast<int32>(Key.TangentMode.GetValue()), static_cast<int32>(RCTM_Break))
			|| !TestEqual(TEXT("Actual weighted mode"), static_cast<int32>(Key.TangentWeightMode.GetValue()), static_cast<int32>(RCTWM_WeightedBoth))
			|| !TestTrue(TEXT("Actual nonzero tangents"), Key.ArriveTangent != 0.f && Key.LeaveTangent != 0.f)
			|| !TestTrue(TEXT("Actual nonzero weights"), Key.ArriveTangentWeight > 0.f && Key.LeaveTangentWeight > 0.f)) { return false; }
	}
	const TArray<FRichCurveKey>& ActualWeightedKeys = Weighted->FloatCurve.GetConstRefOfKeys();
	if (!TestTrue(TEXT("Actual weighted endpoints"), ActualWeightedKeys[0].Time == 0.f && ActualWeightedKeys[1].Time == 1.f
		&& ActualWeightedKeys[0].Value == -3.f && ActualWeightedKeys[1].Value == 4.f)) { return false; }
	const float ActualInterior = Weighted->FloatCurve.Eval(0.25f);
	const float LinearInterior = FMath::Lerp(ActualWeightedKeys[0].Value, ActualWeightedKeys[1].Value, 0.25f);
	if (!TestTrue(TEXT("Actual weighted interior is finite and nonlinear"), FMath::IsFinite(ActualInterior)
		&& !FMath::IsNearlyEqual(ActualInterior, LinearInterior))) { return false; }
	const FFloatCurve* Empty = FixtureCurve(EmptyName);
	const FFloatCurve* Outside = FixtureCurve(OutsideName);
	if (!TestNotNull(TEXT("Actual empty curve"), Empty)
		|| !TestEqual(TEXT("Actual empty keys"), Empty->FloatCurve.GetConstRefOfKeys().Num(), 0)
		|| !TestTrue(TEXT("Actual unset default sentinel"), Empty->FloatCurve.DefaultValue == MAX_flt)
		|| !TestNotNull(TEXT("Actual outside-range curve"), Outside)
		|| !TestEqual(TEXT("Actual outside key count"), Outside->FloatCurve.GetConstRefOfKeys().Num(), 2)) { return false; }
	const TArray<FRichCurveKey>& OutsideKeys = Outside->FloatCurve.GetConstRefOfKeys();
	if (!TestTrue(TEXT("Actual negative and beyond-duration times"), OutsideKeys[0].Time < 0.f && OutsideKeys[1].Time > Source->GetPlayLength())
		|| !TestTrue(TEXT("Actual negative and zero values"), OutsideKeys[0].Value < 0.f && OutsideKeys[1].Value == 0.f)
		|| !TestNull(TEXT("Missing curve is really absent"), FindCurve(MissingName))) { return false; }

	auto ReadSuccess = [&](const FString& Label, const TArray<FName>& Names, TArray<FFloatCurve>& Output)
	{
		const FSourceSnapshot Before = CaptureSource(Source);
		Output = Before.Curves;
		double Duration = -99.0;
		FString Error(TEXT("stale error"));
		const bool bRead = UGGYGOAnimationCurveReadLibrary::ReadFloatCurves(Source, Names, Output, Duration, Error);
		bool bOK = TestTrue(Label + TEXT(".Succeeded"), bRead);
		bOK &= TestTrue(Label + TEXT(".ErrorCleared"), Error.IsEmpty());
		bOK &= TestTrue(Label + TEXT(".DurationExact"), Duration == Before.PlayLength);
		bOK &= CheckSourceUnchanged(*this, Label + TEXT(".Source"), Source, Before);
		if (!TestEqual(Label + TEXT(".OutputCount"), Output.Num(), Names.Num())) { return false; }
		for (int32 Index = 0; Index < Names.Num(); ++Index)
		{
			const FFloatCurve* Expected = Before.Curves.FindByPredicate([&Names, Index](const FFloatCurve& Curve) { return Curve.GetName() == Names[Index]; });
			if (!TestNotNull(Label + TEXT(".ExpectedCurve"), Expected)) { return false; }
			bOK &= CheckCurve(*this, Label + FString::Printf(TEXT(".Output[%d]"), Index), Output[Index], *Expected);
		}
		return bOK;
	};
	auto ReadFailure = [&](const FString& Label, const UAnimSequence* Input, const TArray<FName>& Names, const FString& ExpectedError)
	{
		const FSourceSnapshot Before = CaptureSource(Input);
		TArray<FFloatCurve> Output = {FFloatCurve()};
		double Duration = 99.0;
		FString Error(TEXT("stale error"));
		const bool bRead = UGGYGOAnimationCurveReadLibrary::ReadFloatCurves(Input, Names, Output, Duration, Error);
		bool bOK = TestFalse(Label + TEXT(".Failed"), bRead);
		bOK &= TestEqual(Label + TEXT(".CurvesCleared"), Output.Num(), 0);
		bOK &= TestTrue(Label + TEXT(".DurationCleared"), Duration == 0.0);
		bOK &= TestTrue(Label + TEXT(".LocatedError"), Error.Contains(ExpectedError) && !Error.Contains(TEXT("stale error")));
		if (Input) { bOK &= TestTrue(Label + TEXT(".ObjectPath"), Error.Contains(Input->GetPathName())); }
		bOK &= CheckSourceUnchanged(*this, Label + TEXT(".Source"), Input, Before);
		return bOK;
	};
	const TArray<FName> ReorderedNames = {EmptyName, OutsideName, ProbeName, WeightedName};
	for (bool bDirty : {false, true})
	{
		// Only our owned temporary package is preset; no reset occurs between call and assertion.
		Package->SetDirtyFlag(bDirty);
		if (!TestEqual(TEXT("Real package dirty precondition"), Package->IsDirty(), bDirty)) { return false; }
		const FString State = bDirty ? TEXT("Dirty") : TEXT("Clean");
		TArray<FFloatCurve> Output;
		if (!ReadSuccess(State + TEXT(".Reordered"), ReorderedNames, Output)) { return false; }
		const FSourceSnapshot BeforeOutputEdit = CaptureSource(Source);
		FFloatCurve& Copy = Output.Last(); // ReorderedNames put Weighted last; shape was asserted above.
		Copy.FloatCurve.Keys[0].Value += 100.f;
		Copy.FloatCurve.Keys[0].LeaveTangentWeight += 0.5f;
		Copy.FloatCurve.DefaultValue = 13.f;
		Copy.FloatCurve.PreInfinityExtrap = RCCE_None;
		Copy.FloatCurve.PostInfinityExtrap = RCCE_None;
		Copy.SetName(FName(TEXT("EditedOutputCopy")));
		Copy.SetCurveTypeFlags(AACF_NONE);
		if (!CheckSourceUnchanged(*this, State + TEXT(".IndependentOutput"), Source, BeforeOutputEdit)
			|| !ReadSuccess(State + TEXT(".FreshReadAfterOutputEdit"), ReorderedNames, Output)
			|| !ReadFailure(State + TEXT(".NullSource"), nullptr, {WeightedName}, TEXT("Source is null or invalid"))
			|| !ReadFailure(State + TEXT(".EmptyNames"), Source, {}, TEXT("CurveNames is empty"))
			|| !ReadFailure(State + TEXT(".NoneName"), Source, {NAME_None}, TEXT("CurveNames[0] is None"))
			|| !ReadFailure(State + TEXT(".DuplicateName"), Source, {WeightedName, WeightedName}, TEXT("CurveNames[1] duplicates"))
			|| !ReadFailure(State + TEXT(".MissingCurve"), Source, {MissingName}, TEXT("ReadbackMissing"))
			|| !ReadFailure(State + TEXT(".ValidThenMissing"), Source, {WeightedName, MissingName}, TEXT("ReadbackMissing"))) { return false; }
	}

	// Each recognized native mode must actually survive the public Controller before testing the reader.
	const FAnimationCurveIdentifier ProbeId(ProbeName, ERawCurveTrackTypes::RCT_Float);
	auto SetProbe = [&](ERichCurveInterpMode Interp, ERichCurveTangentMode Tangent, ERichCurveTangentWeightMode Weight,
		ERichCurveExtrapolation Pre, ERichCurveExtrapolation Post)
	{
		TArray<FRichCurveKey> Keys = WeightedKeys;
		for (FRichCurveKey& Key : Keys)
		{
			Key.InterpMode = Interp;
			Key.TangentMode = Tangent;
			Key.TangentWeightMode = Weight;
		}
		FCurveAttributes Attributes;
		Attributes.SetPreExtrapolation(Pre);
		Attributes.SetPostExtrapolation(Post);
		if (!TestTrue(TEXT("Public probe keys"), Controller.SetCurveKeys(ProbeId, Keys, false))
			|| !TestTrue(TEXT("Public probe attributes"), Controller.SetCurveAttributes(ProbeId, Attributes, false))) { return false; }
		const FFloatCurve* Probe = FindCurve(ProbeName);
		if (!TestNotNull(TEXT("Actual mode probe"), Probe)
			|| !TestEqual(TEXT("Actual mode probe count"), Probe->FloatCurve.GetConstRefOfKeys().Num(), 2)
			|| !TestEqual(TEXT("Actual pre mode"), static_cast<int32>(Probe->FloatCurve.PreInfinityExtrap.GetValue()), static_cast<int32>(Pre))
			|| !TestEqual(TEXT("Actual post mode"), static_cast<int32>(Probe->FloatCurve.PostInfinityExtrap.GetValue()), static_cast<int32>(Post))) { return false; }
		for (const FRichCurveKey& Key : Probe->FloatCurve.GetConstRefOfKeys())
		{
			if (!TestEqual(TEXT("Actual interpolation probe"), static_cast<int32>(Key.InterpMode.GetValue()), static_cast<int32>(Interp))
				|| !TestEqual(TEXT("Actual tangent probe"), static_cast<int32>(Key.TangentMode.GetValue()), static_cast<int32>(Tangent))
				|| !TestEqual(TEXT("Actual weight probe"), static_cast<int32>(Key.TangentWeightMode.GetValue()), static_cast<int32>(Weight))) { return false; }
		}
		TArray<FFloatCurve> Output;
		return ReadSuccess(FString::Printf(TEXT("NativeModes[%d,%d,%d,%d,%d]"), Interp, Tangent, Weight, Pre, Post), {ProbeName}, Output);
	};
	for (ERichCurveInterpMode Mode : {RCIM_Linear, RCIM_Constant, RCIM_Cubic, RCIM_None})
	{
		if (!SetProbe(Mode, RCTM_Break, RCTWM_WeightedNone, RCCE_Constant, RCCE_Constant)) { return false; }
	}
	for (ERichCurveTangentMode Mode : {RCTM_Auto, RCTM_User, RCTM_Break, RCTM_None, RCTM_SmartAuto})
	{
		if (!SetProbe(RCIM_Cubic, Mode, RCTWM_WeightedNone, RCCE_Constant, RCCE_Constant)) { return false; }
	}
	for (ERichCurveTangentWeightMode Mode : {RCTWM_WeightedNone, RCTWM_WeightedArrive, RCTWM_WeightedLeave, RCTWM_WeightedBoth})
	{
		if (!SetProbe(RCIM_Cubic, RCTM_Break, Mode, RCCE_Constant, RCCE_Constant)) { return false; }
	}
	for (ERichCurveExtrapolation Mode : {RCCE_Cycle, RCCE_CycleWithOffset, RCCE_Oscillate, RCCE_Linear, RCCE_Constant, RCCE_None})
	{
		if (!SetProbe(RCIM_Cubic, RCTM_Break, RCTWM_WeightedBoth, Mode, Mode)) { return false; }
	}

	// Ordinary transient sequences auto-create a Model. The native CDO is read only, never patched.
	const UAnimSequence* NoModelSource = GetDefault<UAnimSequence>();
	if (!TestTrue(TEXT("Native CDO is a valid source object"), IsValid(NoModelSource))
		|| !TestTrue(TEXT("Actual native CDO precondition"), NoModelSource->HasAnyFlags(RF_ClassDefaultObject))
		|| !TestNull(TEXT("Actual native CDO has no Model"), NoModelSource->GetDataModel())
		|| !ReadFailure(TEXT("NoModelCDO"), NoModelSource, {WeightedName}, TEXT("Source has no existing DataModel"))) { return false; }
	// Custom DefaultValue, corrupt/non-finite data and unknown enum construction need a separate public fixture contract.
	return true;
}
#endif
