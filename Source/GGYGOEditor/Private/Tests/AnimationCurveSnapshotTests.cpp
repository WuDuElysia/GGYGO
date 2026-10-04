// Copyright Epic Games, Inc. All Rights Reserved.

#if WITH_DEV_AUTOMATION_TESTS
#include "GGYGOAnimationCurveSnapshotLibrary.h"
#include "GGYGOAnimationCurveReadLibrary.h"
#include "AnimationAssetSafetyTestUtils.h"
#include "Animation/AnimData/CurveIdentifier.h"
#include "Misc/AutomationTest.h"
#include "UObject/Class.h"
#include "UObject/UnrealType.h"
#include <type_traits>

namespace
{
	struct FExpectedSnapshotField
	{
		const TCHAR* Name;
		FFieldClass* PropertyClass;
		UScriptStruct* ArrayElement = nullptr;
	};

	bool CheckFields(FAutomationTestBase& Test, UScriptStruct* Struct, const TArray<FExpectedSnapshotField>& Fields)
	{
		if (!Test.TestNotNull(TEXT("Actual reflected snapshot struct"), Struct)) { return false; }
		int32 Count = 0;
		for (TFieldIterator<FProperty> It(Struct); It; ++It) { ++Count; }
		bool bOK = Test.TestEqual(Struct->GetName() + TEXT(".FieldCount"), Count, Fields.Num());
		for (const FExpectedSnapshotField& Expected : Fields)
		{
			const FString Label = Struct->GetName() + TEXT(".") + Expected.Name;
			const FProperty* Field = FindFProperty<FProperty>(Struct, Expected.Name);
			if (!Test.TestNotNull(Label + TEXT(".Present"), Field)) { return false; }
			bOK &= Test.TestTrue(Label + TEXT(".ExactPropertyClass"), Field->GetClass() == Expected.PropertyClass);
			bOK &= Test.TestTrue(Label + TEXT(".PublicVisibleReadOnly"), Field->HasAllPropertyFlags(
				CPF_NativeAccessSpecifierPublic | CPF_BlueprintVisible | CPF_BlueprintReadOnly));
			bOK &= Test.TestFalse(Label + TEXT(".NotProtectedOrPrivate"), Field->HasAnyPropertyFlags(
				CPF_NativeAccessSpecifierProtected | CPF_NativeAccessSpecifierPrivate));
			if (Expected.ArrayElement)
			{
				const FArrayProperty* Array = CastField<FArrayProperty>(Field);
				if (!Test.TestNotNull(Label + TEXT(".Array"), Array)) { return false; }
				const FStructProperty* Inner = CastField<FStructProperty>(Array->Inner);
				if (!Test.TestNotNull(Label + TEXT(".StructElement"), Inner)) { return false; }
				bOK &= Test.TestTrue(Label + TEXT(".ExactElementStruct"), Inner->Struct == Expected.ArrayElement);
			}
		}
		return bOK;
	}

	template <typename T>
	bool CheckBits(FAutomationTestBase& Test, const FString& Label, const T& Actual, const T& Expected)
	{
		static_assert(std::is_same_v<T, float> || std::is_same_v<T, double>, "Only scalar floating values are compared.");
		return Test.TestTrue(Label, FMemory::Memcmp(&Actual, &Expected, sizeof(T)) == 0);
	}

	int32 ModeValue(int32 Mode) { return Mode; }
	template <typename T>
	int32 ModeValue(TEnumAsByte<T> Mode) { return static_cast<int32>(Mode.GetValue()); }

	template <typename TKey>
	bool CheckKey(FAutomationTestBase& Test, const FString& Label, const TKey& Actual, const FRichCurveKey& Expected)
	{
		bool bOK = CheckBits(Test, Label + TEXT(".Time"), Actual.Time, Expected.Time);
		bOK &= CheckBits(Test, Label + TEXT(".Value"), Actual.Value, Expected.Value);
		bOK &= CheckBits(Test, Label + TEXT(".ArriveTangent"), Actual.ArriveTangent, Expected.ArriveTangent);
		bOK &= CheckBits(Test, Label + TEXT(".LeaveTangent"), Actual.LeaveTangent, Expected.LeaveTangent);
		bOK &= CheckBits(Test, Label + TEXT(".ArriveTangentWeight"), Actual.ArriveTangentWeight, Expected.ArriveTangentWeight);
		bOK &= CheckBits(Test, Label + TEXT(".LeaveTangentWeight"), Actual.LeaveTangentWeight, Expected.LeaveTangentWeight);
		bOK &= Test.TestEqual(Label + TEXT(".InterpMode"), ModeValue(Actual.InterpMode), ModeValue(Expected.InterpMode));
		bOK &= Test.TestEqual(Label + TEXT(".TangentMode"), ModeValue(Actual.TangentMode), ModeValue(Expected.TangentMode));
		bOK &= Test.TestEqual(Label + TEXT(".TangentWeightMode"), ModeValue(Actual.TangentWeightMode), ModeValue(Expected.TangentWeightMode));
		return bOK;
	}

	template <typename TKey>
	bool CheckKeys(FAutomationTestBase& Test, const FString& Label, const TArray<TKey>& Actual, const TArray<FRichCurveKey>& Expected)
	{
		if (!Test.TestEqual(Label + TEXT(".KeyCount"), Actual.Num(), Expected.Num())) { return false; }
		bool bOK = true;
		for (int32 Index = 0; Index < Actual.Num(); ++Index)
		{
			bOK &= CheckKey(Test, Label + FString::Printf(TEXT(".Keys[%d]"), Index), Actual[Index], Expected[Index]);
		}
		return bOK;
	}

	bool CheckCurve(FAutomationTestBase& Test, const FString& Label, const FGGYGOFloatCurveSnapshot& Actual, const FFloatCurve& Expected)
	{
		bool bOK = Test.TestEqual(Label + TEXT(".Name"), Actual.Name, Expected.GetName());
		bOK &= Test.TestEqual(Label + TEXT(".Flags"), Actual.Flags, Expected.GetCurveTypeFlags());
		bOK &= CheckBits(Test, Label + TEXT(".DefaultValue"), Actual.DefaultValue, Expected.FloatCurve.DefaultValue);
		bOK &= Test.TestEqual(Label + TEXT(".PreInfinityExtrap"), Actual.PreInfinityExtrap, ModeValue(Expected.FloatCurve.PreInfinityExtrap));
		bOK &= Test.TestEqual(Label + TEXT(".PostInfinityExtrap"), Actual.PostInfinityExtrap, ModeValue(Expected.FloatCurve.PostInfinityExtrap));
		bOK &= CheckKeys(Test, Label, Actual.Keys, Expected.FloatCurve.GetConstRefOfKeys());
		return bOK;
	}

	bool CheckNativeCurve(FAutomationTestBase& Test, const FString& Label, const FFloatCurve& Actual, const FFloatCurve& Expected)
	{
		bool bOK = Test.TestEqual(Label + TEXT(".Name"), Actual.GetName(), Expected.GetName());
		bOK &= Test.TestEqual(Label + TEXT(".Flags"), Actual.GetCurveTypeFlags(), Expected.GetCurveTypeFlags());
		bOK &= CheckBits(Test, Label + TEXT(".DefaultValue"), Actual.FloatCurve.DefaultValue, Expected.FloatCurve.DefaultValue);
		bOK &= Test.TestEqual(Label + TEXT(".PreInfinityExtrap"), ModeValue(Actual.FloatCurve.PreInfinityExtrap), ModeValue(Expected.FloatCurve.PreInfinityExtrap));
		bOK &= Test.TestEqual(Label + TEXT(".PostInfinityExtrap"), ModeValue(Actual.FloatCurve.PostInfinityExtrap), ModeValue(Expected.FloatCurve.PostInfinityExtrap));
		bOK &= CheckKeys(Test, Label, Actual.FloatCurve.GetConstRefOfKeys(), Expected.FloatCurve.GetConstRefOfKeys());
		return bOK;
	}

	struct FSnapshotSourceState
	{
		const IAnimationDataModel* Model = nullptr;
		TArray<FFloatCurve> Curves;
		double Duration = 0.0;
		bool bDirty = false;
	};

	FSnapshotSourceState CaptureSource(const UAnimSequence* Source)
	{
		// Only the non-null owned fixture is captured, including during null-input cases.
		FSnapshotSourceState State;
		State.Model = Source->GetDataModel();
		if (State.Model) { State.Curves = State.Model->GetFloatCurves(); }
		State.Duration = static_cast<double>(Source->GetPlayLength());
		State.bDirty = Source->GetPackage()->IsDirty();
		return State;
	}

	bool CheckSourceUnchanged(FAutomationTestBase& Test, const FString& Label, const UAnimSequence* Source, const FSnapshotSourceState& Before)
	{
		const FSnapshotSourceState After = CaptureSource(Source);
		bool bOK = Test.TestTrue(Label + TEXT(".SameModel"), After.Model == Before.Model);
		bOK &= CheckBits(Test, Label + TEXT(".Duration"), After.Duration, Before.Duration);
		bOK &= Test.TestEqual(Label + TEXT(".Dirty"), After.bDirty, Before.bDirty);
		bOK &= Test.TestEqual(Label + TEXT(".CurveCount"), After.Curves.Num(), Before.Curves.Num());
		// Observe public curve content by name, not cache addresses/order or object memory bytes.
		for (const FFloatCurve& Expected : Before.Curves)
		{
			const FFloatCurve* Actual = After.Curves.FindByPredicate([&Expected](const FFloatCurve& Curve) { return Curve.GetName() == Expected.GetName(); });
			if (!Test.TestNotNull(Label + TEXT(".CurvePresent"), Actual)) { return false; }
			bOK &= CheckNativeCurve(Test, Label + TEXT(".") + Expected.GetName().ToString(), *Actual, Expected);
		}
		return bOK;
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FAnimationCurveSnapshotTest, "GGYGO.Editor.Animation.FloatCurveSnapshot",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FAnimationCurveSnapshotTest::RunTest(const FString& Parameters)
{
	// Family 1: inspect actual generated reflection, not the header text or a substitute struct.
	if (!CheckFields(*this, FGGYGOFloatCurveKeySnapshot::StaticStruct(), {
		{TEXT("Time"), FFloatProperty::StaticClass()}, {TEXT("Value"), FFloatProperty::StaticClass()},
		{TEXT("ArriveTangent"), FFloatProperty::StaticClass()}, {TEXT("LeaveTangent"), FFloatProperty::StaticClass()},
		{TEXT("ArriveTangentWeight"), FFloatProperty::StaticClass()}, {TEXT("LeaveTangentWeight"), FFloatProperty::StaticClass()},
		{TEXT("InterpMode"), FIntProperty::StaticClass()}, {TEXT("TangentMode"), FIntProperty::StaticClass()},
		{TEXT("TangentWeightMode"), FIntProperty::StaticClass()}})
		|| !CheckFields(*this, FGGYGOFloatCurveSnapshot::StaticStruct(), {
			{TEXT("Name"), FNameProperty::StaticClass()}, {TEXT("Flags"), FIntProperty::StaticClass()},
			{TEXT("DefaultValue"), FFloatProperty::StaticClass()}, {TEXT("PreInfinityExtrap"), FIntProperty::StaticClass()},
			{TEXT("PostInfinityExtrap"), FIntProperty::StaticClass()},
			{TEXT("Keys"), FArrayProperty::StaticClass(), FGGYGOFloatCurveKeySnapshot::StaticStruct()}})
		|| !CheckFields(*this, FGGYGOFloatCurveReadResult::StaticStruct(), {
			{TEXT("bSucceeded"), FBoolProperty::StaticClass()},
			{TEXT("Curves"), FArrayProperty::StaticClass(), FGGYGOFloatCurveSnapshot::StaticStruct()},
			{TEXT("DurationSeconds"), FDoubleProperty::StaticClass()}, {TEXT("Error"), FStrProperty::StaticClass()}})) { return false; }
	const UFunction* Function = UGGYGOAnimationCurveSnapshotLibrary::StaticClass()->FindFunctionByName(
		GET_FUNCTION_NAME_CHECKED(UGGYGOAnimationCurveSnapshotLibrary, ReadFloatCurveSnapshot));
	if (!TestNotNull(TEXT("Actual snapshot UFunction"), Function)) { return false; }
	const FStructProperty* Return = CastField<FStructProperty>(Function->GetReturnProperty());
	if (!TestNotNull(TEXT("Actual return is a Struct property"), Return)
		|| !TestTrue(TEXT("Exact result return struct"), Return->Struct == FGGYGOFloatCurveReadResult::StaticStruct())
		|| !TestTrue(TEXT("Actual callable static function"), Function->HasAllFunctionFlags(FUNC_BlueprintCallable | FUNC_Static))) { return false; }

	UPackage* Package = AnimationAssetSafetyTests::Package();
	if (!TestNotNull(TEXT("Owned temporary package"), Package)) { return false; }
	Package->SetFlags(RF_Transient);
	UAnimSequence* Source = AnimationAssetSafetyTests::Sequence(Package);
	if (!TestNotNull(TEXT("Real animation fixture"), Source)) { return false; }
	Source->SetFlags(RF_Transient);
	const IAnimationDataModel* Model = Source->GetDataModel();
	if (!TestNotNull(TEXT("Existing real DataModel"), Model)
		|| !TestTrue(TEXT("Actual finite positive source duration"), FMath::IsFinite(Source->GetPlayLength()) && Source->GetPlayLength() > 0.f)) { return false; }
	const FFrameRate ActualFrameRate = Model->GetFrameRate();
	if (!TestEqual(TEXT("Actual fixture frame rate numerator"), ActualFrameRate.Numerator, 1)
		|| !TestEqual(TEXT("Actual fixture frame rate denominator"), ActualFrameRate.Denominator, 1)) { return false; }
	IAnimationDataController& Controller = Source->GetController();
	const FName WeightedName(TEXT("SnapshotWeighted")), EmptyName(TEXT("SnapshotEmpty"));
	const FName OutsideName(TEXT("SnapshotOutside")), ProbeName(TEXT("SnapshotModeProbe"));
	const FName MissingName(TEXT("SnapshotMissing"));
	auto FindCurve = [Model](FName Name) { return Model->FindFloatCurve(FAnimationCurveIdentifier(Name, ERawCurveTrackTypes::RCT_Float)); };
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
	const TArray<FRichCurveKey> OutsideKeys = {FRichCurveKey(-1.f, -5.f), FRichCurveKey(2.f, 0.f)};
	TArray<FRichCurveKey> ExpectedOutsideKeys = OutsideKeys;
	// UE5.8 AnimationData generates a linear Channel tangent, then converts it back to RichCurve.
	// Derive both conversions from the fixed fixture input/rate, never the observed Model or DTO.
	const FFrameRate ExpectedOutsideRate(1, 1);
	const FFrameNumber OutsideFirstFrame = ExpectedOutsideRate.AsFrameTime(OutsideKeys[0].Time).RoundToFrame();
	const FFrameNumber OutsideLastFrame = ExpectedOutsideRate.AsFrameTime(OutsideKeys[1].Time).RoundToFrame();
	const int32 OutsideFrameDelta = OutsideLastFrame.Value - OutsideFirstFrame.Value;
	const double OutsideChannelTimeDelta = FMath::Max<double>(KINDA_SMALL_NUMBER, OutsideFrameDelta);
	const float OutsideChannelLeaveTangent = static_cast<float>(
		(OutsideKeys[1].Value - OutsideKeys[0].Value) / OutsideChannelTimeDelta);
	const double OutsideSecondsDelta = ExpectedOutsideRate.AsSeconds(OutsideLastFrame) - ExpectedOutsideRate.AsSeconds(OutsideFirstFrame);
	const double OutsideBackRatio = OutsideFrameDelta / OutsideSecondsDelta;
	ExpectedOutsideKeys[0].LeaveTangent = static_cast<float>(OutsideChannelLeaveTangent * OutsideBackRatio);
	const int32 WeightedFlags = AACF_Editable | AACF_Disabled;
	if (!AddCurve(WeightedName, WeightedKeys, WeightedFlags, RCCE_CycleWithOffset, RCCE_Linear)
		|| !AddCurve(EmptyName, {}, AACF_NONE, RCCE_None, RCCE_None)
		|| !AddCurve(OutsideName, OutsideKeys, AACF_Editable, RCCE_Oscillate, RCCE_Constant)
		|| !AddCurve(ProbeName, WeightedKeys, AACF_Editable, RCCE_Constant, RCCE_Constant)) { return false; }

	// Controller input is not the oracle: require actual Model values before any reader call.
	auto CheckFixture = [&](FName Name, const TArray<FRichCurveKey>& Keys, int32 Flags, ERichCurveExtrapolation Pre, ERichCurveExtrapolation Post)
	{
		const FFloatCurve* Curve = FindCurve(Name);
		if (!TestNotNull(TEXT("Actual fixture curve"), Curve)) { return false; }
		bool bOK = TestEqual(TEXT("Actual fixture name"), Curve->GetName(), Name);
		bOK &= TestEqual(TEXT("Actual fixture flags"), Curve->GetCurveTypeFlags(), Flags);
		bOK &= TestEqual(TEXT("Actual fixture pre mode"), ModeValue(Curve->FloatCurve.PreInfinityExtrap), static_cast<int32>(Pre));
		bOK &= TestEqual(TEXT("Actual fixture post mode"), ModeValue(Curve->FloatCurve.PostInfinityExtrap), static_cast<int32>(Post));
		bOK &= CheckKeys(*this, Name.ToString() + TEXT(".ActualFixture"), Curve->FloatCurve.GetConstRefOfKeys(), Keys);
		bOK &= TestTrue(TEXT("Actual unset default sentinel"), Curve->FloatCurve.DefaultValue == MAX_flt);
		return bOK;
	};
	if (!CheckFixture(WeightedName, WeightedKeys, WeightedFlags, RCCE_CycleWithOffset, RCCE_Linear)
		|| !CheckFixture(EmptyName, {}, AACF_NONE, RCCE_None, RCCE_None)
		|| !CheckFixture(OutsideName, ExpectedOutsideKeys, AACF_Editable, RCCE_Oscillate, RCCE_Constant)
		|| !CheckFixture(ProbeName, WeightedKeys, AACF_Editable, RCCE_Constant, RCCE_Constant)
		|| !TestTrue(TEXT("Actual outside-range fixture"), OutsideKeys[0].Time < 0.f && OutsideKeys[1].Time > Source->GetPlayLength())
		|| !TestNull(TEXT("Missing curve is really absent"), FindCurve(MissingName))) { return false; }

	int32 SnapshotCalls = 0, NativeFailureCalls = 0;
	auto ReadSuccess = [&](const FString& Label, const TArray<FName>& Names, FGGYGOFloatCurveReadResult& Result)
	{
		const FSnapshotSourceState Before = CaptureSource(Source);
		++SnapshotCalls;
		Result = UGGYGOAnimationCurveSnapshotLibrary::ReadFloatCurveSnapshot(Source, Names);
		bool bOK = TestTrue(Label + TEXT(".Succeeded"), Result.bSucceeded);
		bOK &= TestTrue(Label + TEXT(".ErrorEmpty"), Result.Error.IsEmpty());
		bOK &= CheckBits(*this, Label + TEXT(".DurationExact"), Result.DurationSeconds, Before.Duration);
		bOK &= CheckSourceUnchanged(*this, Label + TEXT(".Source"), Source, Before);
		if (!TestEqual(Label + TEXT(".RequestedCount"), Result.Curves.Num(), Names.Num())) { return false; }
		for (int32 Index = 0; Index < Names.Num(); ++Index)
		{
			const FFloatCurve* Expected = Before.Curves.FindByPredicate([&Names, Index](const FFloatCurve& Curve) { return Curve.GetName() == Names[Index]; });
			if (!TestNotNull(Label + TEXT(".RealExpectedCurve"), Expected)) { return false; }
			bOK &= CheckCurve(*this, Label + FString::Printf(TEXT(".Output[%d]"), Index), Result.Curves[Index], *Expected);
		}
		return bOK;
	};
	auto ReadFailure = [&](const FString& Label, const UAnimSequence* Input, const TArray<FName>& Names, const FString& Cause, FGGYGOFloatCurveReadResult& Result)
	{
		const FSnapshotSourceState BeforeOracle = CaptureSource(Source);
		TArray<FFloatCurve> NativeOutput;
		double NativeDuration = -99.0;
		FString NativeError(TEXT("stale oracle error"));
		++NativeFailureCalls;
		const bool bNative = UGGYGOAnimationCurveReadLibrary::ReadFloatCurves(Input, Names, NativeOutput, NativeDuration, NativeError);
		bool bOK = TestFalse(Label + TEXT(".RealR1Failed"), bNative);
		bOK &= TestTrue(Label + TEXT(".RealR1LocatedError"), !NativeError.IsEmpty() && NativeError.Contains(Cause));
		bOK &= TestEqual(Label + TEXT(".RealR1Empty"), NativeOutput.Num(), 0);
		bOK &= TestTrue(Label + TEXT(".RealR1ZeroDuration"), NativeDuration == 0.0);
		bOK &= CheckSourceUnchanged(*this, Label + TEXT(".AfterR1"), Source, BeforeOracle);
		if (!bOK) { return false; }
		const FSnapshotSourceState BeforeSnapshot = CaptureSource(Source);
		++SnapshotCalls;
		Result = UGGYGOAnimationCurveSnapshotLibrary::ReadFloatCurveSnapshot(Input, Names);
		bOK &= TestFalse(Label + TEXT(".Failed"), Result.bSucceeded);
		bOK &= TestEqual(Label + TEXT(".Empty"), Result.Curves.Num(), 0);
		bOK &= TestTrue(Label + TEXT(".ZeroDuration"), Result.DurationSeconds == 0.0);
		bOK &= TestEqual(Label + TEXT(".OriginalR1Error"), Result.Error, NativeError);
		if (Input) { bOK &= TestTrue(Label + TEXT(".SourcePath"), Result.Error.Contains(Input->GetPathName())); }
		bOK &= CheckSourceUnchanged(*this, Label + TEXT(".AfterSnapshot"), Source, BeforeSnapshot);
		return bOK;
	};
	const TArray<FName> ReorderedNames = {EmptyName, OutsideName, WeightedName};
	for (bool bDirty : {false, true})
	{
		// Families 2/3: preset only the owned package; never reset dirty between call and observation.
		Package->SetDirtyFlag(bDirty);
		if (!TestEqual(TEXT("Actual dirty precondition"), Package->IsDirty(), bDirty)) { return false; }
		const FString State = bDirty ? TEXT("Dirty") : TEXT("Clean");
		FGGYGOFloatCurveReadResult Result;
		if (!ReadSuccess(State + TEXT(".Reordered"), ReorderedNames, Result)) { return false; }
		const FSnapshotSourceState BeforeOutputEdit = CaptureSource(Source);
		FGGYGOFloatCurveSnapshot& Copy = Result.Curves.Last();
		if (!TestEqual(TEXT("Owned DTO has two weighted keys"), Copy.Keys.Num(), 2)) { return false; }
		Copy.Keys[0].Value += 100.f;
		Copy.Keys[0].LeaveTangentWeight += 0.5f;
		Copy.DefaultValue = 13.f;
		Copy.PreInfinityExtrap = static_cast<int32>(RCCE_None);
		Copy.PostInfinityExtrap = static_cast<int32>(RCCE_None);
		Copy.Name = FName(TEXT("EditedSnapshotCopy"));
		Copy.Flags = AACF_NONE;
		Result.DurationSeconds = -7.0;
		Result.Error = TEXT("edited DTO error");
		Result.bSucceeded = false;
		if (!CheckSourceUnchanged(*this, State + TEXT(".IndependentDTO"), Source, BeforeOutputEdit)
			|| !ReadSuccess(State + TEXT(".FreshRead"), ReorderedNames, Result)
			|| !ReadFailure(State + TEXT(".NullSource"), nullptr, {WeightedName}, TEXT("Source is null or invalid"), Result)
			|| !ReadFailure(State + TEXT(".LateMissing"), Source, {WeightedName, MissingName}, MissingName.ToString(), Result)) { return false; }
	}

	// Family 4: retain the original T1's three separately proven native combinations.
	auto ReadMode = [&](ERichCurveInterpMode Interp, ERichCurveTangentMode Tangent)
	{
		TArray<FRichCurveKey> Keys = WeightedKeys;
		for (FRichCurveKey& Key : Keys)
		{
			Key.InterpMode = Interp;
			Key.TangentMode = Tangent;
			Key.TangentWeightMode = RCTWM_WeightedNone;
		}
		const FAnimationCurveIdentifier Id(ProbeName, ERawCurveTrackTypes::RCT_Float);
		if (!TestTrue(TEXT("Public native mode keys"), Controller.SetCurveKeys(Id, Keys, false))
			|| !CheckFixture(ProbeName, Keys, AACF_Editable, RCCE_Constant, RCCE_Constant)) { return false; }
		FGGYGOFloatCurveReadResult Result;
		return ReadSuccess(FString::Printf(TEXT("NativeMode[%d,%d]"), Interp, Tangent), {ProbeName}, Result);
	};
	if (!ReadMode(RCIM_None, RCTM_Break)
		|| !ReadMode(RCIM_Cubic, RCTM_None)
		|| !ReadMode(RCIM_Cubic, RCTM_SmartAuto)) { return false; }
	return TestEqual(TEXT("Exactly eleven Snapshot calls"), SnapshotCalls, 11)
		&& TestEqual(TEXT("Exactly four direct R1 failure oracle calls"), NativeFailureCalls, 4);
}
#endif
