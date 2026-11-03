/** @file GGYGOLinearMontageAuthorLibrary.cpp @brief 原生线性 Montage 制作、Notify 原位迁时及时间轴事实读取。 */
#include "GGYGOLinearMontageAuthorLibrary.h"

#include "Animation/Data/GGYGOActionMotionSourceBinding.h"
#include "Character/Data/GGYGOActionMotionEvaluation.h"

#include "AnimNotifies/AnimNotify_PlayMontageNotify.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimCompositeBase.h"
#include "Animation/AnimLinkableElement.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimNotifies/AnimNotify.h"
#include "Animation/AnimNotifies/AnimNotifyState.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Editor.h"
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

	FGGYGOMontageTimelineNotifyFact ReadNotifyFact(const UAnimMontage* Montage, const FAnimNotifyEvent& Event)
	{
		FGGYGOMontageTimelineNotifyFact Out;
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
		return Out;
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
		Facts.Notifies.Add(ReadNotifyFact(Montage, Event));
	}
	Facts.bSucceeded = true;
	return Facts;
}

namespace GGYGOMontageNotifyRetimePrivate
{
	int32 FindUniqueNotify(const UAnimMontage* Montage, const FGuid& Guid)
	{
		int32 Found = INDEX_NONE;
		for (int32 Index = 0; Index < Montage->Notifies.Num(); ++Index)
		{
			if (Montage->Notifies[Index].Guid == Guid)
			{
				if (Found != INDEX_NONE) { return INDEX_NONE; }
				Found = Index;
			}
		}
		return Found;
	}

	/** Modify／缓存刷新可同步广播；只比较本次栈上原生快照，不覆盖外调产生的后继工作。 */
	bool MatchesNotifySnapshot(const UAnimMontage* Montage, const TArray<FAnimNotifyEvent>& Expected)
	{
		if (Montage->Notifies.Num() != Expected.Num()) { return false; }
		for (int32 Index = 0; Index < Expected.Num(); ++Index)
		{
			if (!FAnimNotifyEvent::StaticStruct()->CompareScriptStruct(&Montage->Notifies[Index], &Expected[Index], PPF_None))
			{
				return false;
			}
		}
		return true;
	}

	bool ValidateRetime(UAnimMontage* Montage, const FGuid& Guid, UAnimNotify* ExpectedNotify,
		float ExpectedTime, float NewTime, int32& NotifyIndex, FString& Error)
	{
		if (!GEditor || GEditor->PlayWorld || !IsValid(Montage) || !IsValid(ExpectedNotify)
			|| ExpectedNotify->GetOuter() != Montage)
		{
			Error = TEXT("需要非 PIE Editor 中仍由原 Montage 直接持有的有效 Notify 对象。");
			return false;
		}
		// RefreshCacheData 会向已加载子 Montage 传播；父资产的派生数据也不是本入口的写入范围。
		if (Montage->HasParentAsset() || !Montage->ChildrenAssets.IsEmpty())
		{
			Error = TEXT("拒绝父／子资产关联的 Montage，避免刷新跨资产传播或覆盖派生数据。");
			return false;
		}
		const float Length = Montage->GetPlayLength();
		if (!FMath::IsFinite(Length) || Length <= 0.0f || !FMath::IsFinite(ExpectedTime)
			|| !FMath::IsFinite(NewTime) || ExpectedTime < 0.0f || ExpectedTime > Length || NewTime < 0.0f || NewTime > Length)
		{
			Error = TEXT("原时间／目标时间必须是 Montage 有效长度范围内的有限绝对秒。");
			return false;
		}
		NotifyIndex = FindUniqueNotify(Montage, Guid);
		if (NotifyIndex == INDEX_NONE)
		{
			Error = TEXT("Guid 未匹配到唯一现有 Notify。");
			return false;
		}
		const FAnimNotifyEvent& Event = Montage->Notifies[NotifyIndex];
		if (Event.Notify != ExpectedNotify || Event.NotifyStateClass || Event.Duration != 0.0f
			|| Event.GetTime() != ExpectedTime || Event.GetLinkedMontage() != Montage)
		{
			Error = TEXT("Guid 对应的原对象、点 Notify 类型、零 Duration、准确原时间或原 Montage 链接已不匹配。");
			return false;
		}
		if (!Montage->SlotAnimTracks.IsValidIndex(Event.GetSlotIndex())
			|| (Event.GetLinkMethod() != EAnimLinkMethod::Absolute && Event.GetLinkMethod() != EAnimLinkMethod::Relative
				&& Event.GetLinkMethod() != EAnimLinkMethod::Proportional))
		{
			Error = TEXT("原 Notify 的 Slot 或 LinkMethod 无效。");
			return false;
		}
		const FAnimTrack& Track = Montage->SlotAnimTracks[Event.GetSlotIndex()].AnimTrack;
		const int32 SegmentIndex = Track.GetSegmentIndexAtTime(NewTime);
		if (!Track.AnimSegments.IsValidIndex(SegmentIndex)
			|| !IsValid(Track.AnimSegments[SegmentIndex].GetAnimReference().Get())
			|| !FMath::IsFinite(Track.AnimSegments[SegmentIndex].GetLength()) || Track.AnimSegments[SegmentIndex].GetLength() <= 0.0f)
		{
			Error = TEXT("目标没有有效正长度源 segment 覆盖；拒绝 Link 自动退回 Absolute 链接。");
			return false;
		}
		// 原生 RefreshCacheData 会修复无效轨道及同轨近同刻事件；准入沿其同一比较规则拒绝改动其它声明。
		for (int32 Index = 0; Index < Montage->Notifies.Num(); ++Index)
		{
			const FAnimNotifyEvent& Current = Montage->Notifies[Index];
			const float Time = Index == NotifyIndex ? NewTime : Current.GetTime();
			if (!Montage->AnimNotifyTracks.IsValidIndex(Current.TrackIndex) || !FMath::IsFinite(Time)
				|| !FMath::IsFinite(Current.GetTriggerTime()) || !FMath::IsFinite(Current.GetEndTriggerTime()))
			{
				Error = FString::Printf(TEXT("Notify[%d] 轨道／时间无效；拒绝缓存刷新隐式修复。"), Index);
				return false;
			}
			for (int32 OtherIndex = 0; OtherIndex < Index; ++OtherIndex)
			{
				const FAnimNotifyEvent& Other = Montage->Notifies[OtherIndex];
				const float OtherTime = OtherIndex == NotifyIndex ? NewTime : Other.GetTime();
				if (Current.TrackIndex == Other.TrackIndex && FMath::IsNearlyEqual(Time, OtherTime))
				{
					Error = FString::Printf(TEXT("Notify[%d]/[%d] 同轨近同刻；缓存刷新会改写轨道，拒绝迁时。"), Index, OtherIndex);
					return false;
				}
			}
		}
		return true;
	}
}

FGGYGOMontageNotifyRetimeResult UGGYGOLinearMontageAuthorLibrary::RetimeMontagePointNotifyByGuid(
	UAnimMontage* Montage, const FString& NotifyGuid, UAnimNotify* ExpectedNotify, float ExpectedAbsoluteTime, float NewAbsoluteTime)
{
	using namespace GGYGOMontageNotifyRetimePrivate;
	using namespace GGYGOMontageTimelineFactsPrivate;
	FGGYGOMontageNotifyRetimeResult Result;
	// 先检查线程，避免错误路径访问 UObject；诊断路径在合法线程内一次捕获。
	if (!IsInGameThread())
	{
		Result.Error = TEXT("[Animation.MontageNotifyRetime] 只允许在 GameThread 调用。");
		return Result;
	}
	const FString MontagePath = GetPathNameSafe(Montage);
	auto FailRetime = [&Result, &MontagePath, &NotifyGuid](const FString& Reason)
	{
		Result.Error = FString::Printf(TEXT("[Animation.MontageNotifyRetime] Montage='%s' Guid='%s': %s"),
			*MontagePath, *NotifyGuid, *Reason);
		return Result;
	};
	FGuid Guid;
	if (!FGuid::ParseExact(NotifyGuid, EGuidFormats::Digits, Guid) || !Guid.IsValid())
	{
		return FailRetime(TEXT("需要有效的 32 位 Digits Guid。"));
	}
	FString Error;
	int32 NotifyIndex = INDEX_NONE;
	if (!ValidateRetime(Montage, Guid, ExpectedNotify, ExpectedAbsoluteTime, NewAbsoluteTime, NotifyIndex, Error))
	{
		return FailRetime(Error);
	}
	Result.Before = ReadNotifyFact(Montage, Montage->Notifies[NotifyIndex]);
	if (NewAbsoluteTime == ExpectedAbsoluteTime)
	{
		Result.After = Result.Before;
		Result.bSucceeded = true;
		return Result;
	}

	const TWeakObjectPtr<UAnimMontage> OriginalMontage = Montage;
	const TWeakObjectPtr<UAnimNotify> OriginalNotify = ExpectedNotify;
	TArray<FAnimNotifyEvent> ExpectedNotifies = Montage->Notifies;
	Montage->Modify();
	Montage = OriginalMontage.Get();
	ExpectedNotify = OriginalNotify.Get();
	if (!ValidateRetime(Montage, Guid, ExpectedNotify, ExpectedAbsoluteTime, NewAbsoluteTime, NotifyIndex, Error))
	{
		return FailRetime(Error);
	}
	if (!MatchesNotifySnapshot(Montage, ExpectedNotifies))
	{
		return FailRetime(TEXT("Modify 外调改变了原 Notify 声明；拒绝继续写入。"));
	}

	// CalculateOffsetForNotify 是未单独导出的虚接口，须保留原生分派；返回后重取原对象与声明。
	const EAnimEventTriggerOffsets::Type Offset = Montage->CalculateOffsetForNotify(NewAbsoluteTime);
	Montage = OriginalMontage.Get();
	ExpectedNotify = OriginalNotify.Get();
	if (!ValidateRetime(Montage, Guid, ExpectedNotify, ExpectedAbsoluteTime, NewAbsoluteTime, NotifyIndex, Error))
	{
		return FailRetime(Error);
	}
	if (!MatchesNotifySnapshot(Montage, ExpectedNotifies))
	{
		return FailRetime(TEXT("offset 计算外调改变了原 Notify 声明；拒绝继续写入。"));
	}
	{
		FAnimNotifyEvent& Event = Montage->Notifies[NotifyIndex];
		Result.bWriteApplied = true;
		Event.Link(Montage, NewAbsoluteTime, Event.GetSlotIndex());
		Event.SetTime(NewAbsoluteTime);
		// 沿 Persona 的原生政策保留已有作者偏移，必要时形成目标边界 offset。
		Event.RefreshTriggerOffset(Offset);
	}
	ExpectedNotifies = Montage->Notifies;
	ExpectedNotifies.Sort();
	// 会排序、重建轨道／BranchingPoint 缓存并广播；此处之后不保留任何数组元素地址。
	Montage->RefreshCacheData();
	Montage = OriginalMontage.Get();
	ExpectedNotify = OriginalNotify.Get();
	if (!ValidateRetime(Montage, Guid, ExpectedNotify, NewAbsoluteTime, NewAbsoluteTime, NotifyIndex, Error))
	{
		return FailRetime(Error);
	}
	Result.After = ReadNotifyFact(Montage, Montage->Notifies[NotifyIndex]);
	if (!MatchesNotifySnapshot(Montage, ExpectedNotifies))
	{
		return FailRetime(TEXT("缓存刷新外调改变了原 Notify 声明；保留未保存现场，拒绝报告成功。"));
	}
	Result.bSucceeded = true;
	return Result;
}

namespace GGYGOMontageNotifyStateRetimePrivate
{
	bool ValidateEndpoint(const UAnimMontage* Montage, const FAnimLinkableElement& Link,
		float TargetTime, FString& Error)
	{
		if (Link.GetLinkedMontage() != Montage || !Montage->SlotAnimTracks.IsValidIndex(Link.GetSlotIndex())
			|| (Link.GetLinkMethod() != EAnimLinkMethod::Absolute && Link.GetLinkMethod() != EAnimLinkMethod::Relative
				&& Link.GetLinkMethod() != EAnimLinkMethod::Proportional))
		{
			Error = TEXT("State 原端点的 Montage、Slot 或 LinkMethod 无效。");
			return false;
		}
		const FAnimTrack& Track = Montage->SlotAnimTracks[Link.GetSlotIndex()].AnimTrack;
		const int32 CurrentSegment = Link.GetSegmentIndex();
		const int32 TargetSegment = Track.GetSegmentIndexAtTime(TargetTime);
		if (!Track.AnimSegments.IsValidIndex(CurrentSegment) || !Track.AnimSegments.IsValidIndex(TargetSegment)
			|| !IsValid(Link.GetLinkedSequence())
			|| Link.GetLinkedSequence() != Track.AnimSegments[CurrentSegment].GetAnimReference().Get()
			|| !FMath::IsFinite(Track.AnimSegments[CurrentSegment].GetLength())
			|| Track.AnimSegments[CurrentSegment].GetLength() <= 0.0f
			|| !IsValid(Track.AnimSegments[TargetSegment].GetAnimReference().Get())
			|| !FMath::IsFinite(Track.AnimSegments[TargetSegment].GetLength())
			|| Track.AnimSegments[TargetSegment].GetLength() <= 0.0f)
		{
			Error = TEXT("State 原链接或目标 segment/source 无效；拒绝 Link 自动退回 Absolute。");
			return false;
		}
		return true;
	}

	bool ValidateRetime(UAnimMontage* Montage, const FGuid& Guid, UAnimNotifyState* ExpectedState,
		float ExpectedTime, float ExpectedDuration, float NewTime, float NewEnd, int32& NotifyIndex, FString& Error)
	{
		using namespace GGYGOMontageNotifyRetimePrivate;
		if (!GEditor || GEditor->PlayWorld || !IsValid(Montage) || !IsValid(ExpectedState)
			|| ExpectedState->GetOuter() != Montage)
		{
			Error = TEXT("需要非 PIE Editor 中仍由原 Montage 直接持有的有效 State 对象。");
			return false;
		}
		if (Montage->HasParentAsset() || !Montage->ChildrenAssets.IsEmpty())
		{
			Error = TEXT("拒绝父／子资产关联的 Montage，避免缓存刷新跨资产传播。");
			return false;
		}
		const float Length = Montage->GetPlayLength();
		if (!FMath::IsFinite(Length) || Length <= 0.0f || !FMath::IsFinite(ExpectedTime)
			|| !FMath::IsFinite(ExpectedDuration) || ExpectedTime < 0.0f || ExpectedDuration <= 0.0f
			|| !FMath::IsFinite(NewTime) || !FMath::IsFinite(NewEnd) || NewTime < 0.0f
			|| NewTime >= NewEnd || NewEnd > Length || !FMath::IsFinite(NewEnd - NewTime))
		{
			Error = TEXT("原时间／时长及目标两端必须为 Montage 域内的有限正区间。");
			return false;
		}
		NotifyIndex = FindUniqueNotify(Montage, Guid);
		if (NotifyIndex == INDEX_NONE)
		{
			Error = TEXT("Guid 未匹配到唯一现有 State。");
			return false;
		}
		const FAnimNotifyEvent& Event = Montage->Notifies[NotifyIndex];
		if (Event.Notify || Event.NotifyStateClass != ExpectedState || Event.GetTime() != ExpectedTime
			|| Event.GetDuration() != ExpectedDuration || !FMath::IsFinite(Event.Duration) || Event.Duration <= 0.0f
			|| !FMath::IsFinite(Event.EndLink.GetTime()) || Event.EndLink.GetTime() > Length
			|| Event.MontageTickType != EMontageNotifyTickType::Queued || Event.IsBranchingPoint())
		{
			Error = TEXT("原 State 对象、精确 time/duration、Queued 或原结束链接已不匹配。");
			return false;
		}
		if (!ValidateEndpoint(Montage, Event, NewTime, Error)
			|| !ValidateEndpoint(Montage, Event.EndLink, NewEnd, Error))
		{
			return false;
		}
		// 沿 RefreshCacheData 的轨道修复条件准入，避免迁时顺带改写其它 Notify。
		for (int32 Index = 0; Index < Montage->Notifies.Num(); ++Index)
		{
			const FAnimNotifyEvent& Current = Montage->Notifies[Index];
			const float Time = Index == NotifyIndex ? NewTime : Current.GetTime();
			if (!Montage->AnimNotifyTracks.IsValidIndex(Current.TrackIndex) || !FMath::IsFinite(Time)
				|| !FMath::IsFinite(Current.GetTriggerTime()) || !FMath::IsFinite(Current.GetEndTriggerTime()))
			{
				Error = TEXT("原 Notify 轨道／触发时间无效；拒绝缓存隐式修复。");
				return false;
			}
			for (int32 OtherIndex = 0; OtherIndex < Index; ++OtherIndex)
			{
				const FAnimNotifyEvent& Other = Montage->Notifies[OtherIndex];
				const float OtherTime = OtherIndex == NotifyIndex ? NewTime : Other.GetTime();
				if (Current.TrackIndex == Other.TrackIndex && FMath::IsNearlyEqual(Time, OtherTime))
				{
					Error = TEXT("目标产生同轨近同刻 Notify；拒绝缓存重排作者轨道。");
					return false;
				}
			}
		}
		return true;
	}
}

FGGYGOMontageNotifyRetimeResult UGGYGOLinearMontageAuthorLibrary::RetimeMontageNotifyStateByGuid(
	UAnimMontage* Montage, const FString& NotifyGuid, UAnimNotifyState* ExpectedState, float ExpectedAbsoluteTime,
	float ExpectedDuration, float NewAbsoluteTime, float NewEndAbsoluteTime)
{
	using namespace GGYGOMontageNotifyRetimePrivate;
	using namespace GGYGOMontageTimelineFactsPrivate;
	FGGYGOMontageNotifyRetimeResult Result;
	if (!IsInGameThread())
	{
		Result.Error = TEXT("[Animation.MontageStateRetime] 只允许在 GameThread 调用。");
		return Result;
	}
	const FString MontagePath = GetPathNameSafe(Montage);
	auto FailRetime = [&Result, &MontagePath, &NotifyGuid](const FString& Reason)
	{
		Result.Error = FString::Printf(TEXT("[Animation.MontageStateRetime] Montage='%s' Guid='%s': %s"),
			*MontagePath, *NotifyGuid, *Reason);
		return Result;
	};
	FGuid Guid;
	if (!FGuid::ParseExact(NotifyGuid, EGuidFormats::Digits, Guid) || !Guid.IsValid())
	{
		return FailRetime(TEXT("需要有效的 32 位 Digits Guid。"));
	}
	FString Error;
	int32 NotifyIndex = INDEX_NONE;
	if (!GGYGOMontageNotifyStateRetimePrivate::ValidateRetime(Montage, Guid, ExpectedState,
		ExpectedAbsoluteTime, ExpectedDuration, NewAbsoluteTime, NewEndAbsoluteTime, NotifyIndex, Error))
	{
		return FailRetime(Error);
	}
	Result.Before = ReadNotifyFact(Montage, Montage->Notifies[NotifyIndex]);
	if (NewAbsoluteTime == ExpectedAbsoluteTime && NewEndAbsoluteTime == Montage->Notifies[NotifyIndex].EndLink.GetTime())
	{
		Result.After = Result.Before;
		Result.bSucceeded = true;
		return Result;
	}
	const TWeakObjectPtr<UAnimMontage> OriginalMontage = Montage;
	const TWeakObjectPtr<UAnimNotifyState> OriginalState = ExpectedState;
	TArray<FAnimNotifyEvent> ExpectedNotifies = Montage->Notifies;
	Montage->Modify();
	Montage = OriginalMontage.Get();
	ExpectedState = OriginalState.Get();
	if (!GGYGOMontageNotifyStateRetimePrivate::ValidateRetime(Montage, Guid, ExpectedState,
		ExpectedAbsoluteTime, ExpectedDuration, NewAbsoluteTime, NewEndAbsoluteTime, NotifyIndex, Error)
		|| !MatchesNotifySnapshot(Montage, ExpectedNotifies))
	{
		return FailRetime(Error.IsEmpty() ? FString(TEXT("Modify 外调改变了原 Notify 声明。")) : Error);
	}
	EAnimEventTriggerOffsets::Type Offsets[2];
	const float Endpoints[2] = {NewAbsoluteTime, NewEndAbsoluteTime};
	for (int32 Endpoint = 0; Endpoint < 2; ++Endpoint)
	{
		// 虚调用可同步外调；每端返回后重取原对象、Guid 和完整声明，不留数组元素地址。
		Offsets[Endpoint] = Montage->CalculateOffsetForNotify(Endpoints[Endpoint]);
		Montage = OriginalMontage.Get();
		ExpectedState = OriginalState.Get();
		if (!GGYGOMontageNotifyStateRetimePrivate::ValidateRetime(Montage, Guid, ExpectedState,
			ExpectedAbsoluteTime, ExpectedDuration, NewAbsoluteTime, NewEndAbsoluteTime, NotifyIndex, Error)
			|| !MatchesNotifySnapshot(Montage, ExpectedNotifies))
		{
			return FailRetime(Error.IsEmpty() ? FString(TEXT("端点 offset 外调改变了原 Notify 声明。")) : Error);
		}
	}
	{
		FAnimNotifyEvent& Event = Montage->Notifies[NotifyIndex];
		const int32 StartSlot = Event.GetSlotIndex();
		const int32 EndSlot = Event.EndLink.GetSlotIndex();
		Result.bWriteApplied = true;
		Event.Link(Montage, NewAbsoluteTime, StartSlot);
		Event.SetTime(NewAbsoluteTime);
		Event.SetDuration(NewEndAbsoluteTime - NewAbsoluteTime);
		Event.EndLink.Link(Montage, NewEndAbsoluteTime, EndSlot);
		Event.RefreshTriggerOffset(Offsets[0]);
		Event.RefreshEndTriggerOffset(Offsets[1]);
	}
	ExpectedNotifies = Montage->Notifies;
	ExpectedNotifies.Sort();
	Montage->RefreshCacheData();
	Montage = OriginalMontage.Get();
	ExpectedState = OriginalState.Get();
	if (!GGYGOMontageNotifyStateRetimePrivate::ValidateRetime(Montage, Guid, ExpectedState,
		NewAbsoluteTime, NewEndAbsoluteTime - NewAbsoluteTime, NewAbsoluteTime, NewEndAbsoluteTime, NotifyIndex, Error))
	{
		return FailRetime(Error);
	}
	Result.After = ReadNotifyFact(Montage, Montage->Notifies[NotifyIndex]);
	if (Montage->Notifies[NotifyIndex].EndLink.GetTime() != NewEndAbsoluteTime)
	{
		return FailRetime(TEXT("原生结束链接未精确落到目标终点；保留未保存现场。"));
	}
	if (!MatchesNotifySnapshot(Montage, ExpectedNotifies))
	{
		return FailRetime(TEXT("缓存刷新外调改变了原 Notify 声明；保留未保存现场。"));
	}
	Result.bSucceeded = true;
	return Result;
}
