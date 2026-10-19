/** @file GGYGOLinearMontageAuthorLibrary.cpp @brief 通过原生帧域、区段和动作来源验证制作新线性 Montage，并只读复制 Montage 时间轴事实。 */
#include "GGYGOLinearMontageAuthorLibrary.h"

#include "Animation/Data/GGYGOActionMotionSourceBinding.h"
#include "Character/Data/GGYGOActionMotionEvaluation.h"

#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimCompositeBase.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"

namespace
{
	FGGYGOLinearMontageAuthorResult Fail(const UAnimMontage* Montage, const FString& Reason)
	{
		FGGYGOLinearMontageAuthorResult Result;
		Result.Error = FString::Printf(TEXT("[Animation.LinearMontageAuthor] Montage='%s': %s"),
			*GetPathNameSafe(Montage), *Reason);
		return Result;
	}

	bool ValidateInputs(UAnimMontage* Montage, FName SlotName, const TArray<UAnimSequence*>& Sequences,
		const TArray<FName>& Names, FString& Error)
	{
		if (!IsValid(Montage) || !IsValid(Montage->GetSkeleton()) || SlotName.IsNone()
			|| !Montage->GetSkeleton()->ContainsSlotName(SlotName) || Sequences.IsEmpty() || Sequences.Num() != Names.Num())
		{
			Error = TEXT("Montage/Skeleton、既有 Slot 或逐一对应的完整源区段无效。");
			return false;
		}
		TSet<FName> Seen;
		for (int32 Index = 0; Index < Sequences.Num(); ++Index)
		{
			UAnimSequence* Sequence = Sequences[Index];
			if (!IsValid(Sequence) || Sequence->GetSkeleton() != Montage->GetSkeleton()
				|| !FMath::IsFinite(Sequence->GetPlayLength()) || Sequence->GetPlayLength() <= 0.0f
				|| !FMath::IsFinite(Sequence->RateScale) || Sequence->RateScale <= 0.0f || FMath::IsNearlyZero(Sequence->RateScale)
				|| Sequence->GetSamplingFrameRate().Numerator <= 0 || Sequence->GetSamplingFrameRate().Denominator <= 0
				|| Names[Index].IsNone() || Seen.Contains(Names[Index]))
			{
				Error = FString::Printf(TEXT("源[%d]='%s' 的 Skeleton/长度/正向非零 RateScale/采样率或区段名称无效。"),
					Index, *GetPathNameSafe(Sequence));
				return false;
			}
			Seen.Add(Names[Index]);
		}
		return true;
	}
}

FGGYGOLinearMontageAuthorResult UGGYGOLinearMontageAuthorLibrary::AuthorNewMontage(UAnimMontage* Montage,
	FName SlotName, const TArray<UAnimSequence*>& Sequences, const TArray<FName>& SectionNames)
{
	FString Error;
	if (!ValidateInputs(Montage, SlotName, Sequences, SectionNames, Error)) { return Fail(Montage, Error); }
	if (FPackageName::DoesPackageExist(Montage->GetOutermost()->GetName()) || !Montage->Notifies.IsEmpty())
	{ return Fail(Montage, TEXT("只允许未在磁盘存在、没有作者 Notify 的新 Montage；拒绝覆盖既有工作。")); }
	if (!Montage->GetDataModelInterface().GetInterface())
	{ return Fail(Montage, TEXT("新 Montage 没有现成 DataModel。")); }

	FSlotAnimationTrack Track;
	Track.SlotName = SlotName;
	float Position = 0.0f;
	for (UAnimSequence* Sequence : Sequences)
	{
		FAnimSegment Segment;
		Segment.SetAnimReference(Sequence, true);
		Segment.StartPos = Position;
		Segment.AnimStartTime = 0.0f;
		Segment.AnimEndTime = Sequence->GetPlayLength();
		Segment.AnimPlayRate = 1.0f;
		Segment.LoopingCount = 1;
		Segment.UpdateCachedPlayLength();
		const float NextPosition = Segment.GetEndPos();
		if (!FMath::IsFinite(NextPosition) || NextPosition <= Position)
		{ return Fail(Montage, TEXT("完整源无法在原生 float 位置域中组成正长度相邻区段。")); }
		Track.AnimTrack.AnimSegments.Add(Segment);
		Position = NextPosition;
	}

	Montage->Modify();
	Montage->SlotAnimTracks = {MoveTemp(Track)};
	Montage->CompositeSections.Reset();
	// 公开入口属于 UAnimCompositeBase；虚分派仍执行该 Montage 的原生实现。
	static_cast<UAnimCompositeBase*>(Montage)->UpdateCommonTargetFrameRate();
	const FFrameRate Rate = Montage->GetCommonTargetFrameRate();
	if (Rate.Numerator <= 0 || Rate.Denominator <= 0)
	{ return Fail(Montage, TEXT("源采样域不能形成有效 CommonTarget；不代用固定帧率。")); }
	const double FrameCoordinate = static_cast<double>(Position) * Rate.AsDecimal();
	if (!FMath::IsFinite(FrameCoordinate) || FrameCoordinate <= 0.0 || FrameCoordinate > static_cast<double>(MAX_int32) - 0.5)
	{ return Fail(Montage, TEXT("完整末端超过原生 FFrameNumber 可表示域。")); }
	Montage->GetController().SetFrameRate(Rate, false);
	if (Montage->GetDataModelInterface()->GetFrameRate() != Rate)
	{ return Fail(Montage, TEXT("原生 controller 未形成准确 Montage 帧域。")); }
	Montage->SetCompositeLength(Position);
	for (int32 Index = 0; Index < SectionNames.Num(); ++Index)
	{
		if (Montage->AddAnimCompositeSection(SectionNames[Index], Montage->SlotAnimTracks[0].AnimTrack.AnimSegments[Index].StartPos) != Index)
		{ return Fail(Montage, TEXT("原生 AddAnimCompositeSection 未创建准确区段。")); }
	}
	for (int32 Index = 0; Index < SectionNames.Num(); ++Index)
	{
		Montage->CompositeSections[Index].NextSectionName = SectionNames.IsValidIndex(Index + 1) ? SectionNames[Index + 1] : NAME_None;
	}
	Montage->PostEditChange();
	return ValidateMontage(Montage, SlotName, Sequences, SectionNames);
}

FGGYGOLinearMontageAuthorResult UGGYGOLinearMontageAuthorLibrary::ValidateMontage(UAnimMontage* Montage,
	FName SlotName, const TArray<UAnimSequence*>& Sequences, const TArray<FName>& SectionNames)
{
	FString Error;
	if (!ValidateInputs(Montage, SlotName, Sequences, SectionNames, Error)) { return Fail(Montage, Error); }
	if (Montage->SlotAnimTracks.Num() != 1 || Montage->SlotAnimTracks[0].SlotName != SlotName
		|| Montage->SlotAnimTracks[0].AnimTrack.AnimSegments.Num() != Sequences.Num()
		|| Montage->CompositeSections.Num() != SectionNames.Num())
	{ return Fail(Montage, TEXT("必须是准确唯一 Slot、逐源完整 segment 和逐一对应的区段。")); }
	FGGYGOLinearMontageAuthorResult Result;
	float Position = 0.0f;
	for (int32 Index = 0; Index < Sequences.Num(); ++Index)
	{
		const FAnimSegment& Segment = Montage->SlotAnimTracks[0].AnimTrack.AnimSegments[Index];
		const FCompositeSection& Section = Montage->CompositeSections[Index];
		const FName NextName = SectionNames.IsValidIndex(Index + 1) ? SectionNames[Index + 1] : NAME_None;
		if (Segment.GetAnimReference() != Sequences[Index] || Segment.StartPos != Position || Segment.AnimStartTime != 0.0f
			|| Segment.AnimEndTime != Sequences[Index]->GetPlayLength() || Segment.AnimPlayRate != 1.0f || Segment.LoopingCount != 1
			|| Section.SectionName != SectionNames[Index] || Section.GetTime() != Position || Section.NextSectionName != NextName)
		{ return Fail(Montage, FString::Printf(TEXT("源／区段[%d] 不是完整相邻线性配置。"), Index)); }
		Result.SectionStarts.Add(Section.GetTime());
		Position = Segment.GetEndPos();
	}
	// 沿用真实生产绑定的末端 float/帧域证据及 Movement 能力校验，不另设秒数宽容。
	FGGYGOActionMotionSourceBindingPtr Binding;
	if (!GGYGOActionMotionSource::BuildSourceBindingRange(Montage, SlotName, SectionNames[0], SectionNames.Last(), Binding, Error)
		|| !GGYGOActionMotionEvaluation::ValidateSource(*Binding, Error))
	{ return Fail(Montage, Error); }
	Result.bSucceeded = true;
	Result.DurationSeconds = Montage->GetPlayLength();
	return Result;
}
// 具名命名空间：Unity 合并编译单元时不与其它文件的匿名辅助函数同名冲突。
namespace GGYGOMontageTimelineFactsPrivate
{
	FString DescribeLinkMethod(EAnimLinkMethod::Type Method)
	{
		switch (Method)
		{
		case EAnimLinkMethod::Absolute: return TEXT("Absolute");
		case EAnimLinkMethod::Relative: return TEXT("Relative");
		case EAnimLinkMethod::Proportional: return TEXT("Proportional");
		default: return TEXT("Unknown");
		}
	}

	/** 原生 Broadcast 使用的 FName；按限定名调用，不经 Blueprint 显示名覆盖。 */
	FName ReadStockNotifyName(const FAnimNotifyEvent& Event)
	{
		if (const UAnimNotify_PlayMontageNotify* Point = Cast<UAnimNotify_PlayMontageNotify>(Event.Notify.Get()))
		{
			return FName(*Point->UAnimNotify_PlayMontageNotify::GetNotifyName_Implementation());
		}
		if (const UAnimNotify_PlayMontageNotifyWindow* Window =
			Cast<UAnimNotify_PlayMontageNotifyWindow>(Event.NotifyStateClass.Get()))
		{
			return FName(*Window->UAnimNotify_PlayMontageNotifyWindow::GetNotifyName_Implementation());
		}
		return NAME_None;
	}
}

FGGYGOMontageTimelineFacts UGGYGOLinearMontageAuthorLibrary::ReadMontageTimelineFacts(const UAnimMontage* Montage)
{
	using namespace GGYGOMontageTimelineFactsPrivate;
	FGGYGOMontageTimelineFacts Facts;
	if (!IsInGameThread() || !IsValid(Montage))
	{
		Facts.Error = FString::Printf(TEXT("[Animation.MontageTimelineFacts] Montage='%s': 只在 GameThread 读取有效 Montage。"),
			*GetPathNameSafe(Montage));
		return Facts;
	}
	// 纯复制当前原生字段：不调用 Modify、RefreshCacheData、Update/Link 或任何验证器。
	Facts.PlayLength = Montage->GetPlayLength();
	for (const FCompositeSection& Section : Montage->CompositeSections)
	{
		FGGYGOMontageTimelineSectionFact& Out = Facts.Sections.AddDefaulted_GetRef();
		Out.SectionName = Section.SectionName;
		Out.NextSectionName = Section.NextSectionName;
		Out.Time = Section.GetTime();
		Out.SlotIndex = Section.GetSlotIndex();
		Out.SegmentIndex = Section.GetSegmentIndex();
	}
	for (int32 SlotIndex = 0; SlotIndex < Montage->SlotAnimTracks.Num(); ++SlotIndex)
	{
		const FSlotAnimationTrack& Slot = Montage->SlotAnimTracks[SlotIndex];
		for (int32 SegmentIndex = 0; SegmentIndex < Slot.AnimTrack.AnimSegments.Num(); ++SegmentIndex)
		{
			const FAnimSegment& Segment = Slot.AnimTrack.AnimSegments[SegmentIndex];
			FGGYGOMontageTimelineSegmentFact& Out = Facts.Segments.AddDefaulted_GetRef();
			Out.SlotName = Slot.SlotName;
			Out.SlotIndex = SlotIndex;
			Out.SegmentIndex = SegmentIndex;
			Out.StartPos = Segment.StartPos;
			Out.EndPos = Segment.GetEndPos();
			Out.AnimReference = GetPathNameSafe(Segment.GetAnimReference().Get());
			if (Out.AnimReference == TEXT("None")) { Out.AnimReference.Reset(); }
		}
	}
	for (const FAnimNotifyEvent& Event : Montage->Notifies)
	{
		FGGYGOMontageTimelineNotifyFact& Out = Facts.Notifies.AddDefaulted_GetRef();
#if WITH_EDITORONLY_DATA
		if (Event.Guid.IsValid()) { Out.Guid = Event.Guid.ToString(EGuidFormats::Digits); }
#endif
		Out.TrackIndex = Event.TrackIndex;
		if (const UAnimNotify* Notify = Event.Notify.Get())
		{
			Out.NotifyClass = Notify->GetClass()->GetPathName();
			Out.NotifyObject = Notify->GetPathName();
		}
		if (const UAnimNotifyState* State = Event.NotifyStateClass.Get())
		{
			Out.StateClass = State->GetClass()->GetPathName();
			if (Out.NotifyObject.IsEmpty()) { Out.NotifyObject = State->GetPathName(); }
		}
		Out.StockNotifyName = ReadStockNotifyName(Event);
		Out.Time = Event.GetTime();
		Out.TriggerTimeOffset = Event.TriggerTimeOffset;
		Out.TriggerTime = Event.GetTriggerTime();
		Out.Duration = Event.GetDuration();
		Out.EndTriggerTime = Event.GetEndTriggerTime();
		Out.SlotIndex = Event.GetSlotIndex();
		Out.SegmentIndex = Event.GetSegmentIndex();
		Out.LinkMethod = DescribeLinkMethod(Event.GetLinkMethod());
		Out.bIsBranchingPoint = Event.IsBranchingPoint();
		Out.bLinkedToSelf = Event.GetLinkedMontage() == Montage;
	}
	Facts.bSucceeded = true;
	return Facts;
}
