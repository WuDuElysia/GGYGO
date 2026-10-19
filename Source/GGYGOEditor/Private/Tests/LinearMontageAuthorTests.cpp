/** @file LinearMontageAuthorTests.cpp @brief 新线性 Montage 的原生速率映射、来源拒绝和只读验证专项。 */
#if WITH_DEV_AUTOMATION_TESTS
#include "GGYGOLinearMontageAuthorLibrary.h"
#include "AnimationAssetSafetyTestUtils.h"

#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "AnimationBlueprintLibrary.h"
#include "Animation/AnimData/CurveIdentifier.h"
#include "Animation/AnimMontage.h"
#include "Misc/AutomationTest.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/UnrealType.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGGYGOLinearMontageAuthorTest, "GGYGO.Editor.Animation.LinearMontageAuthor",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGGYGOLinearMontageAuthorTest::RunTest(const FString& Parameters)
{
	UPackage* Package = AnimationAssetSafetyTests::Package();
	UAnimSequence* Main = AnimationAssetSafetyTests::Sequence(Package);
	if (!TestNotNull(TEXT("真实原生测试源"), Main)) { return false; }
	// End 是同一 Skeleton 的独立原生源，不经过资产克隆的加载／压缩生命周期。
	UAnimSequence* End = NewObject<UAnimSequence>(Package, TEXT("CompleteEnd"));
	End->SetSkeleton(Main->GetSkeleton());
	auto& EndController = End->GetController();
	EndController.InitializeModel();
	EndController.SetFrameRate(FFrameRate(1, 1), false);
	EndController.SetNumberOfFrames(FFrameNumber(1), false);
	if (!TestTrue(TEXT("完整 End 的真实骨轨"), EndController.AddBoneCurve(TEXT("root"), false))
		|| !TestTrue(TEXT("完整 End 的真实骨键"), EndController.SetBoneTrackKeys(TEXT("root"),
			TArray<FVector>{FVector::ZeroVector, FVector(100, 0, 0)},
			TArray<FQuat>{FQuat::Identity, FQuat::Identity},
			TArray<FVector>{FVector::OneVector, FVector::OneVector}, false))) { return false; }
	const TArray<UAnimSequence*> Sources{Main, End};
	for (UAnimSequence* Source : Sources)
	{
		for (FName Name : {FName(TEXT("RootMotion_PosX")), FName(TEXT("RootMotion_PosY")),
			FName(TEXT("RootMotion_PosZ")), FName(TEXT("RootMotion_Yaw"))})
		{
			const FAnimationCurveIdentifier Id(Name, ERawCurveTrackTypes::RCT_Float);
			if (!TestTrue(TEXT("创建测试源真实曲线"), Source->GetController().AddCurve(Id, 0, false))
				|| !TestTrue(TEXT("写入测试源真实曲线键"), Source->GetController().SetCurveKeys(Id,
					TArray<FRichCurveKey>{FRichCurveKey(0.f, 0.f), FRichCurveKey(1.f, 0.f)}, false))) { return false; }
		}
		Source->GetController().NotifyPopulated();
	}
	Main->RateScale = 2.f;
	End->RateScale = 0.5f;
	const FName Slot(TEXT("TestLinearSlot"));
	Main->GetSkeleton()->RegisterSlotNode(Slot);
	UAnimMontage* Montage = NewObject<UAnimMontage>(Package);
	Montage->SetSkeleton(Main->GetSkeleton());
	const TArray<FName> Names{TEXT("First"), TEXT("Last")};
	// 1 Hz 原生 Montage 帧域不能表示 2.5 秒完整末端。
	// 继续要求原 Movement 严格拒绝，不放宽终端容差或用 3 秒替代完整源。
	const auto Unrepresentable = UGGYGOLinearMontageAuthorLibrary::AuthorNewMontage(Montage, Slot, Sources, Names);
	TestFalse(TEXT("不可表示的完整末端拒绝"), Unrepresentable.bSucceeded);
	TestTrue(TEXT("保留原生末端诊断"), Unrepresentable.Error.Contains(TEXT("native terminal endpoint")));
	TestEqual(TEXT("不可表示末端不签发长度"), Unrepresentable.DurationSeconds, 0.f);
	TestTrue(TEXT("不可表示末端不签发区段坐标"), Unrepresentable.SectionStarts.IsEmpty());

	// 正向速率映射使用明确可表示的测试源帧域；2 Hz 下 2.5 秒为原生五帧。
	// 只配置本专项的两个临时源，不给通用作者添加固定 FPS 或第二种时钟。
	for (UAnimSequence* Source : Sources)
	{
		auto& Controller = Source->GetController();
		Controller.SetFrameRate(FFrameRate(2, 1), false);
		if (Source->GetDataModelInterface()->GetNumberOfFrames() != 2)
		{ Controller.SetNumberOfFrames(FFrameNumber(2), false); }
		if (!TestTrue(TEXT("可表示源的真实完整骨轨"), Controller.SetBoneTrackKeys(TEXT("root"),
			TArray<FVector>{FVector::ZeroVector, FVector(50, 0, 0), FVector(100, 0, 0)},
			TArray<FQuat>{FQuat::Identity, FQuat::Identity, FQuat::Identity},
			TArray<FVector>{FVector::OneVector, FVector::OneVector, FVector::OneVector}, false))) { return false; }
		// 原生 Populated 通知将完整 DataModel 帧域发布到 Sequence 的目标采样域。
		Controller.NotifyPopulated();
		TestEqual(TEXT("临时源仍是完整一秒"), Source->GetPlayLength(), 1.f);
		TestEqual(TEXT("原生源采样域明确为两帧每秒"), Source->GetSamplingFrameRate(), FFrameRate(2, 1));
	}
	Montage = NewObject<UAnimMontage>(Package);
	Montage->SetSkeleton(Main->GetSkeleton());
	const auto Authored = UGGYGOLinearMontageAuthorLibrary::AuthorNewMontage(Montage, Slot, Sources, Names);
	if (!TestTrue(Authored.Error, Authored.bSucceeded)) { return false; }
	TestEqual(TEXT("源 RateScale 只映射一次"), Authored.DurationSeconds, 2.5f);
	TestEqual(TEXT("完整 Main 的原生区段末端"), Authored.SectionStarts[1], 0.5f);
	TestEqual(TEXT("最终区段自然终止"), Montage->CompositeSections.Last().NextSectionName, NAME_None);
	Package->SetDirtyFlag(false); // 仅本专项的临时夹具，用于检测只读入口是否产生 dirty。
	const bool bDirtyBefore = Package->IsDirty();
	const auto Read = UGGYGOLinearMontageAuthorLibrary::ValidateMontage(Montage, Slot, Sources, Names);
	TestTrue(Read.Error, Read.bSucceeded);
	TestEqual(TEXT("只读不改变 dirty"), Package->IsDirty(), bDirtyBefore);

	// 拒绝发生在改新对象之前；不以原生 near-zero -> 1 的分支替换输入。
	UAnimMontage* Invalid = NewObject<UAnimMontage>(Package);
	Invalid->SetSkeleton(Main->GetSkeleton());
	const int32 TracksBefore = Invalid->SlotAnimTracks.Num();
	Main->RateScale = 1e-12f;
	const auto BadRate = UGGYGOLinearMontageAuthorLibrary::AuthorNewMontage(Invalid, Slot, Sources, Names);
	TestFalse(TEXT("近零源速率明确拒绝"), BadRate.bSucceeded);
	TestEqual(TEXT("失败不发布长度"), BadRate.DurationSeconds, 0.f);
	TestTrue(TEXT("失败不发布区段坐标"), BadRate.SectionStarts.IsEmpty());
	TestEqual(TEXT("输入拒绝不改轨道"), Invalid->SlotAnimTracks.Num(), TracksBefore);
	Main->RateScale = 2.f;
	const auto DuplicateNames = UGGYGOLinearMontageAuthorLibrary::AuthorNewMontage(Invalid, Slot, Sources, {Names[0], Names[0]});
	TestFalse(TEXT("重复名称拒绝"), DuplicateNames.bSucceeded);

	End->GetController().RemoveCurve(FAnimationCurveIdentifier(TEXT("RootMotion_Yaw"), ERawCurveTrackTypes::RCT_Float), false);
	const auto MixedYaw = UGGYGOLinearMontageAuthorLibrary::ValidateMontage(Montage, Slot, Sources, Names);
	TestFalse(TEXT("混合 Yaw 能力由原 Movement 校验拒绝"), MixedYaw.bSucceeded);
	TestTrue(TEXT("保留实际曲线诊断"), MixedYaw.Error.Contains(TEXT("RootMotion_Yaw")));
	TestEqual(TEXT("失败读回不签发旧成功长度"), MixedYaw.DurationSeconds, 0.f);
	return true;
}

// 具名命名空间：Unity 合并编译单元时与其它测试辅助隔离。
namespace LinearMontageTimelineFactsTests
{
	uint32 FloatBits(float Value)
	{
		uint32 Result = 0;
		FMemory::Memcpy(&Result, &Value, sizeof(Result));
		return Result;
	}

	const FGGYGOMontageTimelineNotifyFact* FindFact(const FGGYGOMontageTimelineFacts& Facts, const UObject* Notify)
	{
		const FString Path = GetPathNameSafe(Notify);
		return Facts.Notifies.FindByPredicate([&Path](const FGGYGOMontageTimelineNotifyFact& Fact)
		{
			return Fact.NotifyObject == Path;
		});
	}

	const FAnimNotifyEvent* FindEvent(const UAnimMontage* Montage, const UAnimNotify* Notify)
	{
		return Montage->Notifies.FindByPredicate([Notify](const FAnimNotifyEvent& Event)
		{
			return Event.Notify.Get() == Notify;
		});
	}
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGGYGOMontageTimelineFactsTest, "GGYGO.Editor.Animation.MontageTimelineFacts",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGGYGOMontageTimelineFactsTest::RunTest(const FString& Parameters)
{
	using namespace LinearMontageTimelineFactsTests;
	UPackage* Package = AnimationAssetSafetyTests::Package();
	UAnimSequence* Main = AnimationAssetSafetyTests::Sequence(Package);
	if (!TestNotNull(TEXT("真实原生测试源"), Main)) { return false; }
	UAnimSequence* End = NewObject<UAnimSequence>(Package, TEXT("TimelineEnd"));
	End->SetSkeleton(Main->GetSkeleton());
	End->GetController().InitializeModel();
	End->GetController().SetFrameRate(FFrameRate(1, 1), false);
	End->GetController().SetNumberOfFrames(FFrameNumber(1), false);
	if (!TestTrue(TEXT("End 真实骨轨"), End->GetController().AddBoneCurve(TEXT("root"), false))) { return false; }
	const TArray<UAnimSequence*> Sources{Main, End};
	// 沿用 LinearMontageAuthor 已通过的可表示夹具：2 Hz 完整一秒源、RateScale 2／0.5。
	for (UAnimSequence* Source : Sources)
	{
		auto& Controller = Source->GetController();
		for (FName Name : {FName(TEXT("RootMotion_PosX")), FName(TEXT("RootMotion_PosY")),
			FName(TEXT("RootMotion_PosZ")), FName(TEXT("RootMotion_Yaw"))})
		{
			const FAnimationCurveIdentifier Id(Name, ERawCurveTrackTypes::RCT_Float);
			if (!TestTrue(TEXT("创建测试源真实曲线"), Controller.AddCurve(Id, 0, false))
				|| !TestTrue(TEXT("写入测试源真实曲线键"), Controller.SetCurveKeys(Id,
					TArray<FRichCurveKey>{FRichCurveKey(0.f, 0.f), FRichCurveKey(1.f, 0.f)}, false))) { return false; }
		}
		Controller.SetFrameRate(FFrameRate(2, 1), false);
		if (Source->GetDataModelInterface()->GetNumberOfFrames() != 2)
		{ Controller.SetNumberOfFrames(FFrameNumber(2), false); }
		if (!TestTrue(TEXT("可表示源的真实完整骨轨"), Controller.SetBoneTrackKeys(TEXT("root"),
			TArray<FVector>{FVector::ZeroVector, FVector(50, 0, 0), FVector(100, 0, 0)},
			TArray<FQuat>{FQuat::Identity, FQuat::Identity, FQuat::Identity},
			TArray<FVector>{FVector::OneVector, FVector::OneVector, FVector::OneVector}, false))) { return false; }
		Controller.NotifyPopulated();
		if (!TestEqual(TEXT("临时源仍是完整一秒"), Source->GetPlayLength(), 1.f)
			|| !TestEqual(TEXT("原生源采样域明确为两帧每秒"), Source->GetSamplingFrameRate(), FFrameRate(2, 1))) { return false; }
	}
	Main->RateScale = 2.f;
	End->RateScale = 0.5f;
	const FName Slot(TEXT("TestTimelineSlot"));
	Main->GetSkeleton()->RegisterSlotNode(Slot);
	UAnimMontage* Montage = NewObject<UAnimMontage>(Package);
	Montage->SetSkeleton(Main->GetSkeleton());
	const TArray<FName> Names{TEXT("Main"), TEXT("End")};
	const auto Authored = UGGYGOLinearMontageAuthorLibrary::AuthorNewMontage(Montage, Slot, Sources, Names);
	if (!TestTrue(Authored.Error, Authored.bSucceeded) || !TestEqual(TEXT("两段区段"), Authored.SectionStarts.Num(), 2)) { return false; }

	// Main 终点权威是 End Section 的原生 GetTime，与 GA 读取同源。
	const float MainEnd = Montage->GetAnimCompositeSection(Montage->GetSectionIndex(Names[1])).GetTime();
	TestTrue(TEXT("End Section 与作者结果逐位一致"), FloatBits(MainEnd) == FloatBits(Authored.SectionStarts[1]));
	const FName Track(TEXT("ActionSignal"));
	UAnimationBlueprintLibrary::AddAnimationNotifyTrack(Montage, Track);
	UAnimNotify* Attack = UAnimationBlueprintLibrary::AddAnimationNotifyEvent(
		Montage, Track, 0.25f, UAnimNotify_PlayMontageNotify::StaticClass());
	UAnimNotify* Move = UAnimationBlueprintLibrary::AddAnimationNotifyEvent(
		Montage, Track, MainEnd, UAnimNotify_PlayMontageNotify::StaticClass());
	FNameProperty* NameProperty = FindFProperty<FNameProperty>(UAnimNotify_PlayMontageNotify::StaticClass(), TEXT("NotifyName"));
	if (!TestNotNull(TEXT("原生攻击点"), Attack) || !TestNotNull(TEXT("原生移动点"), Move)
		|| !TestNotNull(TEXT("stock NotifyName 反射属性"), NameProperty)) { return false; }
	NameProperty->SetPropertyValue_InContainer(Attack, FName(TEXT("Event.Montage.CancelPoint")));
	NameProperty->SetPropertyValue_InContainer(Move, FName(TEXT("Event.Montage.MoveCancelPoint")));
	const FAnimNotifyEvent* MoveEvent = FindEvent(Montage, Move);
	const FAnimNotifyEvent* AttackEvent = FindEvent(Montage, Attack);
	if (!TestNotNull(TEXT("移动点原生事件"), MoveEvent) || !TestNotNull(TEXT("攻击点原生事件"), AttackEvent)) { return false; }
	TestTrue(TEXT("stock 点为原生 BranchingPoint"), MoveEvent->IsBranchingPoint() && AttackEvent->IsBranchingPoint());

	const TArray<FAnimNotifyEvent> NotifiesBefore = Montage->Notifies;
	TArray<float> SectionTimesBefore;
	for (const FCompositeSection& Section : Montage->CompositeSections) { SectionTimesBefore.Add(Section.GetTime()); }
	Package->SetDirtyFlag(false); // 仅本专项的临时夹具，用于检测只读入口是否产生 dirty。
	const auto Facts = UGGYGOLinearMontageAuthorLibrary::ReadMontageTimelineFacts(Montage);
	if (!TestTrue(Facts.Error, Facts.bSucceeded)) { return false; }
	TestFalse(TEXT("只读不产生 dirty"), Package->IsDirty());
	bool bTimelineKept = Montage->Notifies.Num() == NotifiesBefore.Num()
		&& Montage->CompositeSections.Num() == SectionTimesBefore.Num();
	for (int32 Index = 0; bTimelineKept && Index < NotifiesBefore.Num(); ++Index)
	{
		const FAnimNotifyEvent& Before = NotifiesBefore[Index];
		const FAnimNotifyEvent& After = Montage->Notifies[Index];
		bTimelineKept = Before.Notify == After.Notify && Before.Guid == After.Guid && Before.TrackIndex == After.TrackIndex
			&& FloatBits(Before.GetTime()) == FloatBits(After.GetTime()) && FloatBits(Before.TriggerTimeOffset) == FloatBits(After.TriggerTimeOffset);
	}
	for (int32 Index = 0; bTimelineKept && Index < SectionTimesBefore.Num(); ++Index)
	{
		bTimelineKept = FloatBits(SectionTimesBefore[Index]) == FloatBits(Montage->CompositeSections[Index].GetTime());
	}
	TestTrue(TEXT("只读不改变原生 Notify／Section 时间轴"), bTimelineKept);

	TestTrue(TEXT("PlayLength 逐位读回"), FloatBits(Facts.PlayLength) == FloatBits(Montage->GetPlayLength()));
	if (!TestEqual(TEXT("Section 数量"), Facts.Sections.Num(), 2) || !TestEqual(TEXT("段数量"), Facts.Segments.Num(), 2)) { return false; }
	TestEqual(TEXT("Main→End"), Facts.Sections[0].NextSectionName, Names[1]);
	TestEqual(TEXT("End 为末段"), Facts.Sections[1].NextSectionName, FName(NAME_None));
	TestTrue(TEXT("End Section 时间逐位读回"), FloatBits(Facts.Sections[1].Time) == FloatBits(MainEnd));
	TestTrue(TEXT("End 段起点逐位读回"), FloatBits(Facts.Segments[1].StartPos)
		== FloatBits(Montage->SlotAnimTracks[0].AnimTrack.AnimSegments[1].StartPos));
	TestEqual(TEXT("段 Slot 名"), Facts.Segments[1].SlotName, Slot);

	const FGGYGOMontageTimelineNotifyFact* MoveFact = FindFact(Facts, Move);
	const FGGYGOMontageTimelineNotifyFact* AttackFact = FindFact(Facts, Attack);
	if (!TestNotNull(TEXT("移动点事实"), MoveFact) || !TestNotNull(TEXT("攻击点事实"), AttackFact)) { return false; }
	// 声明位置等于 Main 终点；段界上的引擎合法 OffsetBefore 原样留存，实际触发早于 Main 终点，
	// 开放移动必须由 GA 以原实例实时位置判断，本事实不授予权限。
	TestTrue(TEXT("移动点声明时间等于 Main 终点"), FloatBits(MoveFact->Time) == FloatBits(MainEnd));
	TestTrue(TEXT("段界原生 OffsetBefore"), FloatBits(MoveFact->TriggerTimeOffset) == FloatBits(-UE_KINDA_SMALL_NUMBER));
	TestTrue(TEXT("移动点 GetTriggerTime 逐位读回"), FloatBits(MoveFact->TriggerTime) == FloatBits(MoveEvent->GetTriggerTime())
		&& FloatBits(MoveFact->TriggerTime) == FloatBits(MainEnd + (-UE_KINDA_SMALL_NUMBER)));
	TestTrue(TEXT("原生实际触发早于 Main 终点"), MoveFact->TriggerTime < MainEnd);
	TestEqual(TEXT("移动点 stock 名"), MoveFact->StockNotifyName, FName(TEXT("Event.Montage.MoveCancelPoint")));
	TestEqual(TEXT("stock 点类"), MoveFact->NotifyClass, UAnimNotify_PlayMontageNotify::StaticClass()->GetPathName());
	TestTrue(TEXT("移动点无 State 且零时长"), MoveFact->StateClass.IsEmpty() && MoveFact->Duration == 0.f);
	TestTrue(TEXT("移动点 BranchingPoint 且链接本 Montage"), MoveFact->bIsBranchingPoint && MoveFact->bLinkedToSelf);
	TestFalse(TEXT("编辑器 Guid 可读"), MoveFact->Guid.IsEmpty());
	TestTrue(TEXT("Main 内攻击点无偏移"), FloatBits(AttackFact->TriggerTimeOffset) == FloatBits(0.f)
		&& FloatBits(AttackFact->TriggerTime) == FloatBits(0.25f) && AttackFact->bIsBranchingPoint);
	TestEqual(TEXT("攻击点 stock 名"), AttackFact->StockNotifyName, FName(TEXT("Event.Montage.CancelPoint")));

	const auto Invalid = UGGYGOLinearMontageAuthorLibrary::ReadMontageTimelineFacts(nullptr);
	TestFalse(TEXT("无效输入明确失败"), Invalid.bSucceeded);
	TestTrue(TEXT("失败不签发事实"), Invalid.Sections.IsEmpty() && Invalid.Segments.IsEmpty()
		&& Invalid.Notifies.IsEmpty() && Invalid.PlayLength == 0.f);
	TestTrue(TEXT("失败保留定位诊断"), Invalid.Error.Contains(TEXT("MontageTimelineFacts")));
	return true;
}
#endif
