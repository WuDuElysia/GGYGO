#if WITH_DEV_AUTOMATION_TESTS
#include "RootMotionBakeModifier.h"
#include "AnimationAssetSafetyTestUtils.h"
#include "Misc/AutomationTest.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FRootMotionBakeSafetyTest, "GGYGO.Editor.Animation.RootMotionBakeLifecycle",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FRootMotionBakeSafetyTest::RunTest(const FString& Parameters)
{
	using namespace AnimationAssetSafetyTests;
	UE::Anim::FApplyModifiersScope Scope(UE::Anim::FApplyModifiersScope::SuppressWarningAndError);
	UAnimSequence* Asset = Sequence(Package());
	if (!TestNotNull(TEXT("Valid animation sequence fixture"), Asset)) { return false; }
	auto& Controller = Asset->GetController();
	const FAnimationCurveIdentifier Id(TEXT("RM_PosX"), ERawCurveTrackTypes::RCT_Float);
	if (!TestTrue(TEXT("Create original curve"), Controller.AddCurve(Id, AACF_DefaultCurve, false))
		|| !TestTrue(TEXT("Set original curve keys"), Controller.SetCurveKeys(Id, {FRichCurveKey(0, 7), FRichCurveKey(1, 9)}, false))) { return false; }
	auto Curve = [&]()
	{
		const FFloatCurve* Value = Asset->GetDataModel()->FindFloatCurve(Id);
		return TestNotNull(TEXT("Expected curve still exists"), Value) ? Value->Evaluate(0) : 0.f;
	};
	auto BoneEnd = [&]()
	{
		TArray<FTransform> Keys;
		if (!TestTrue(TEXT("Expected root track still exists"), Asset->GetDataModel()->IsValidBoneTrackName(TEXT("root")))) { return 0.; }
		Asset->GetDataModel()->GetBoneTrackTransforms(TEXT("root"), Keys);
		// Record a failure before returning; missing keys must never reach Last().
		return TestEqual(TEXT("Expected root track retains two keys"), Keys.Num(), 2) ? Keys.Last().GetTranslation().X : 0.;
	};
	auto* Modifier = NewObject<URootMotionBakeModifier>(Asset);
	Modifier->ApplyToAnimationSequence(Asset);
	Modifier->RevertFromAnimationSequence(Asset);
	TestEqual(TEXT("Verify-only revert keeps original curve"), Curve(), 7.f);
	TestEqual(TEXT("Verify-only revert keeps original bone"), BoneEnd(), 100.);
	Modifier->bVerifyOnly = false;
	Modifier->ApplyToAnimationSequence(Asset);
	TestEqual(TEXT("Strip wrote in-place bone"), BoneEnd(), 0.);
	Modifier->ApplyToAnimationSequence(Asset);
	TestEqual(TEXT("Reapply restores original before baking"), Curve(), 0.f);
	TestEqual(TEXT("Reapply still strips bone"), BoneEnd(), 0.);
	Modifier->RevertFromAnimationSequence(Asset);
	TestEqual(TEXT("Explicit revert restores preexisting curve"), Curve(), 7.f);
	TestEqual(TEXT("Explicit revert restores original bone"), BoneEnd(), 100.);
	TestNull(TEXT("Explicit revert removes only newly created curve"), Asset->GetDataModel()->FindFloatCurve(FAnimationCurveIdentifier(TEXT("RM_Dist"), ERawCurveTrackTypes::RCT_Float)));
	Modifier->ApplyToAnimationSequence(Asset);
	Controller.SetCurveKeys(Id, {FRichCurveKey(0, 123)}, false);
	// Match the category-prefixed automation event, NOT the raw GWarn message.
	// Matching raw text downgrades Error to Verbose before the modifier's log filter,
	// preventing its transaction rollback. Register once: duplicate patterns replace counters.
	AddExpectedError(TEXT("LogAnimation: RootMotionBake: curve changed after apply; revert refused."), EAutomationExpectedErrorFlags::Exact, 2);
	Modifier->ApplyToAnimationSequence(Asset);
	TestEqual(TEXT("Conflicting reapply rolls back and keeps hand edit"), Curve(), 123.f);
	TestTrue(TEXT("Failed reapply retains applied snapshot"), Modifier->CanRevert(Asset));
	TestEqual(TEXT("Conflicting reapply keeps stripped bone"), BoneEnd(), 0.);
	Modifier->RevertFromAnimationSequence(Asset);
	TestEqual(TEXT("Conflicting explicit revert preserves hand edit"), Curve(), 123.f);
	TestEqual(TEXT("Conflicting explicit revert leaves bone untouched"), BoneEnd(), 0.);
	TestNotNull(TEXT("Conflicting explicit revert leaves generated curve untouched"), Asset->GetDataModel()->FindFloatCurve(FAnimationCurveIdentifier(TEXT("RM_Dist"), ERawCurveTrackTypes::RCT_Float)));
	TestFalse(TEXT("Engine explicit revert removes snapshot even when restore is refused"), Modifier->CanRevert(Asset));
	return true;
}
#endif
