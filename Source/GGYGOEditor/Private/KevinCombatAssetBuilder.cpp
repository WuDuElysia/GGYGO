/** @file KevinCombatAssetBuilder.cpp @brief Explicit Kevin Slot registration and new-only animation preparation; gameplay belongs to BP/GAS. */
#include "Animation/Notifies/GGYGOAnimNotifyState_GameplayEventWindow.h"
#include "Animation/Runtime/GGYGOMontageGuardAnimInstance.h"
#include "Animation/Data/GGYGOActionMotionSourceBinding.h"
#include "Character/Data/GGYGOActionMotionEvaluation.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "AnimationBlueprintLibrary.h"
#include "AnimationGraphSchema.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_Slot.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphSchema.h"
#include "Engine/SkeletalMesh.h"
#include "Engine/SkeletalMeshSocket.h"
#include "Factories/AnimBlueprintFactory.h"
#include "Factories/AnimMontageFactory.h"
#include "HAL/IConsoleManager.h"
#include "HAL/FileManager.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Serialization/JsonSerializer.h"
#include "Serialization/MemoryWriter.h"
#include "Serialization/ObjectAndNameAsStringProxyArchive.h"
#include "Serialization/StructuredArchiveAdapters.h"
#include "System/GGYGOGameplayTags.h"
#include "UObject/MetaData.h"
#include "UObject/Package.h"
#include "UObject/SavePackage.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectHash.h"
#include "UObject/UnrealType.h"

namespace KevinCombatAssets
{
constexpr TCHAR OwnerKey[] = TEXT("GGYGO.AssetBuilder");
constexpr TCHAR OwnerValue[] = TEXT("KevinCombatAssets.v2");
using FJson = TSharedPtr<FJsonObject>;

bool Fail(const FString& Message)
{
	UE_LOG(LogTemp, Error, TEXT("KevinCombatAssets: %s"), *Message);
	return false;
}
bool Owned(UObject* Object)
{
	return Object->GetPackage()->GetMetaData().GetValue(Object, OwnerKey) == OwnerValue;
}
void MarkOwned(UObject* Object)
{
	Object->GetPackage()->GetMetaData().SetValue(Object, OwnerKey, OwnerValue);
}
bool Save(UObject* Asset)
{
	UPackage* Package = Asset->GetPackage();
	Package->MarkPackageDirty();
	FSavePackageArgs Args;
	Args.TopLevelFlags = RF_Public | RF_Standalone;
	Args.SaveFlags = SAVE_NoError;
	return UPackage::SavePackage(Package, Asset,
		*FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
}
FString ObjectPath(const FString& Package)
{
	return Package.Contains(TEXT(".")) ? Package : Package + TEXT(".") + FPackageName::GetLongPackageAssetName(Package);
}
template<typename T> T* Load(const FString& Path) { return LoadObject<T>(nullptr, *ObjectPath(Path)); }

void DescribeMontage(UAnimMontage* Montage, FName Slot, const FJson& Action, FJson& Row)
{
	Row->SetStringField(TEXT("sequence"), Montage->SlotAnimTracks[0].AnimTrack.AnimSegments[0].GetAnimReference()->GetPathName());
	Row->SetNumberField(TEXT("length_seconds"), Montage->GetPlayLength());
	Row->SetNumberField(TEXT("window_count"), Montage->Notifies.Num());
	TArray<TSharedPtr<FJsonValue>> WindowRows;
	for (const FAnimNotifyEvent& Event : Montage->Notifies)
	{
		FJson Window = MakeShared<FJsonObject>();
		Window->SetNumberField(TEXT("start_seconds"), Event.GetTime());
		Window->SetNumberField(TEXT("end_seconds"), Event.GetTime() + Event.GetDuration());
		Window->SetStringField(TEXT("notify_class"), Event.NotifyStateClass ? Event.NotifyStateClass->GetClass()->GetPathName() : FString());
		WindowRows.Add(MakeShared<FJsonValueObject>(Window));
	}
	Row->SetArrayField(TEXT("windows"), WindowRows);
	Row->SetStringField(TEXT("window_source"), Action->GetStringField(TEXT("window_source")));
	Row->SetStringField(TEXT("slot"), Slot.ToString());
	Row->SetBoolField(TEXT("single_section_stops"), Montage->CompositeSections.Num() == 1 && Montage->CompositeSections[0].NextSectionName.IsNone());
}

struct FPreparedMontage
{
	FString Path;
	TStrongObjectPtr<UAnimSequence> Sequence;
	TStrongObjectPtr<UAnimMontage> Existing;
	TArray<FVector2f> Windows;
	float BlendIn = 0.f, BlendOut = 0.f;
	FString WindowSource;
	bool bRequiresXYZ = false;
};

bool ValidateMotionMontage(UAnimMontage* Montage, FName Slot)
{
	FGGYGOActionMotionSourceBindingPtr Binding;
	FString Error;
	return (GGYGOActionMotionSource::BuildSourceBinding(Montage, Slot, TEXT("Main"), Binding, Error)
		&& GGYGOActionMotionEvaluation::ValidateSource(*Binding, Error))
		|| Fail(Montage->GetPathName() + TEXT(": ") + Error);
}

bool PrepareMontage(const FJson& Action, USkeleton* Skeleton, FName Slot, FPreparedMontage& Plan, FJson& Row)
{
	FString SequencePath;
	bool bDamage = false;
	const TArray<TSharedPtr<FJsonValue>>* Windows = nullptr;
	if (!Action || !Action->TryGetStringField(TEXT("montage"), Plan.Path)
		|| !Action->TryGetStringField(TEXT("sequence_override"), SequencePath)
		|| !Action->TryGetBoolField(TEXT("require_sequence_override"), Plan.bRequiresXYZ)
		|| !Action->TryGetBoolField(TEXT("damage_enabled"), bDamage)
		|| !Action->TryGetArrayField(TEXT("hit_windows"), Windows)
		|| !Action->TryGetStringField(TEXT("window_source"), Plan.WindowSource)
		|| !Action->TryGetNumberField(TEXT("blend_in_seconds"), Plan.BlendIn)
		|| !Action->TryGetNumberField(TEXT("blend_out_seconds"), Plan.BlendOut))
		return Fail(TEXT("Selected action has missing/invalid montage configuration"));
	Row->SetStringField(TEXT("asset"), Plan.Path);
	Row->SetStringField(TEXT("status"), TEXT("validation_failed"));
	if (SequencePath.IsEmpty())
	{
		if (Plan.bRequiresXYZ || !Action->TryGetStringField(TEXT("source_sequence"), SequencePath))
			return Fail(Plan.Path + TEXT(": required derived sequence missing"));
	}
	Plan.Sequence.Reset(Load<UAnimSequence>(SequencePath));
	UAnimSequence* Sequence = Plan.Sequence.Get();
	if (!Sequence || Sequence->GetPackage()->IsDirty() || Sequence->GetSkeleton() != Skeleton
		|| !FMath::IsFinite(Sequence->GetPlayLength()) || Sequence->GetPlayLength() <= 0.f
		|| !FMath::IsNearlyEqual(Sequence->RateScale, 1.f))
		return Fail(Plan.Path + TEXT(": invalid/unsaved sequence, skeleton, length or rate: ") + SequencePath);
	if (Plan.bRequiresXYZ)
	{
		if (Sequence->bEnableRootMotion || Sequence->bForceRootLock
			|| Sequence->GetPackage()->GetMetaData().GetValue(Sequence, TEXT("GGYGO.MotionBuilder")) != TEXT("KevinMontageXYZ.v2")
			|| Sequence->GetPackage()->GetMetaData().GetValue(Sequence, TEXT("GGYGO.MotionCurveSpace")) != TEXT("ActorLocalCmXYZ.v1")
			|| !Sequence->HasCurveData(TEXT("RootMotion_PosX"), false)
			|| !Sequence->HasCurveData(TEXT("RootMotion_PosY"), false)
			|| !Sequence->HasCurveData(TEXT("RootMotion_PosZ"), false))
			return Fail(Plan.Path + TEXT(": derived pose needs verified actor-local XYZ curves and disabled native root motion"));
	}
	const float Length = Sequence->GetPlayLength();
	if (!FMath::IsFinite(Plan.BlendIn) || !FMath::IsFinite(Plan.BlendOut)
		|| Plan.BlendIn < 0 || Plan.BlendOut < 0 || Plan.BlendIn >= Length || Plan.BlendOut >= Length)
		return Fail(Plan.Path + TEXT(": explicit blends must be finite, nonnegative and shorter than the clip"));
	bool bConfirmed = false;
	if (bDamage && (!Action->TryGetBoolField(TEXT("hit_windows_confirmed"), bConfirmed) || !bConfirmed
		|| Plan.WindowSource != TEXT("manual_candidate") || Windows->IsEmpty()))
		return Fail(Plan.Path + TEXT(": damage needs technically verified test windows; selected candidates are still unverified"));
	if (!bDamage && !Windows->IsEmpty()) return Fail(Plan.Path + TEXT(": disabled damage must have empty windows"));
	float PreviousEnd = -1.f;
	for (const auto& Value : *Windows)
	{
		const FJson Window = Value->AsObject();
		FVector2f Range;
		if (!Window || !Window->TryGetNumberField(TEXT("start_seconds"), Range.X)
			|| !Window->TryGetNumberField(TEXT("end_seconds"), Range.Y)
			|| !FMath::IsFinite(Range.X) || !FMath::IsFinite(Range.Y)
			|| Range.X < 0 || Range.X <= PreviousEnd || Range.Y <= Range.X || Range.Y >= Length - Plan.BlendOut)
			return Fail(Plan.Path + TEXT(": windows must be ordered, separated, and before configured blend-out"));
		Plan.Windows.Add(Range);
		PreviousEnd = Range.Y;
	}
	UObject* Object = Load<UObject>(Plan.Path);
	UAnimMontage* Montage = Cast<UAnimMontage>(Object);
	if (Object && (!Montage || !Owned(Montage) || Montage->GetPackage()->IsDirty()))
		return Fail(Plan.Path + TEXT(": refuses wrong type, foreign or unsaved asset"));
	if (!Montage)
	{
		if (FPackageName::DoesPackageExist(Plan.Path)) return Fail(Plan.Path + TEXT(": existing package could not be loaded"));
		if (const UPackage* Package = FindPackage(nullptr, *Plan.Path))
			if (Package->IsDirty()) return Fail(Plan.Path + TEXT(": unsaved target package; inspect before retry"));
		Row->SetStringField(TEXT("status"), TEXT("planned_missing"));
		return true;
	}
	Plan.Existing.Reset(Montage);
	// Ownership proves provenance only. Authored assets are inspected and never regenerated.
	if (Montage->GetSkeleton() != Skeleton || Montage->SlotAnimTracks.Num() != 1
		|| Montage->SlotAnimTracks[0].SlotName != Slot
		|| Montage->SlotAnimTracks[0].AnimTrack.AnimSegments.Num() != 1
		|| Montage->CompositeSections.Num() != 1 || Montage->CompositeSections[0].SectionName != TEXT("Main")
		|| !FMath::IsNearlyZero(Montage->CompositeSections[0].GetTime())
		|| !Montage->CompositeSections[0].NextSectionName.IsNone() || !FMath::IsNearlyEqual(Montage->RateScale, 1.f)
		|| !FMath::IsNearlyEqual(Montage->GetPlayLength(), Length, .001f) || !Montage->bEnableAutoBlendOut)
		return Fail(Plan.Path + TEXT(": authored montage differs from required full-clip playback; preserved"));
	const FAnimSegment& Segment = Montage->SlotAnimTracks[0].AnimTrack.AnimSegments[0];
	if (Segment.GetAnimReference() != Sequence || Segment.LoopingCount != 1
		|| !FMath::IsNearlyEqual(Segment.AnimPlayRate, 1.f) || !FMath::IsNearlyZero(Segment.StartPos)
		|| !FMath::IsNearlyZero(Segment.AnimStartTime) || !FMath::IsNearlyEqual(Segment.AnimEndTime, Length, .001f))
		return Fail(Plan.Path + TEXT(": authored segment differs; preserved"));
	TArray<const FAnimNotifyEvent*> HitEvents;
	for (const FAnimNotifyEvent& Event : Montage->Notifies)
		if (Event.NotifyStateClass && Event.NotifyStateClass->IsA<UGGYGOAnimNotifyState_GameplayEventWindow>()) HitEvents.Add(&Event);
	HitEvents.Sort([](const FAnimNotifyEvent& A, const FAnimNotifyEvent& B) { return A.GetTime() < B.GetTime(); });
	if (HitEvents.Num() != Plan.Windows.Num()) return Fail(Plan.Path + TEXT(": authored gameplay windows differ; preserved"));
	const FStructProperty* BeginProperty = FindFProperty<FStructProperty>(UGGYGOAnimNotifyState_GameplayEventWindow::StaticClass(), TEXT("BeginEventTag"));
	const FStructProperty* EndProperty = FindFProperty<FStructProperty>(UGGYGOAnimNotifyState_GameplayEventWindow::StaticClass(), TEXT("EndEventTag"));
	for (int32 Index = 0; Index < HitEvents.Num(); ++Index)
	{
		const FAnimNotifyEvent& Event = *HitEvents[Index];
		if (!BeginProperty || !EndProperty
			|| *BeginProperty->ContainerPtrToValuePtr<FGameplayTag>(Event.NotifyStateClass.Get()) != GGYGOGameplayTags::Event_Montage_HitWindowBegin
			|| *EndProperty->ContainerPtrToValuePtr<FGameplayTag>(Event.NotifyStateClass.Get()) != GGYGOGameplayTags::Event_Montage_HitWindowEnd
			|| !FMath::IsNearlyEqual(Event.GetTime(), Plan.Windows[Index].X, .001f)
			|| !FMath::IsNearlyEqual(Event.GetTime() + Event.GetDuration(), Plan.Windows[Index].Y, .001f)
			|| Plan.Windows[Index].Y >= Length - Montage->BlendOut.GetBlendTime())
			return Fail(Plan.Path + TEXT(": authored hit tags/times/blend-out differ; preserved"));
	}
	if (Plan.bRequiresXYZ && !ValidateMotionMontage(Montage, Slot)) return false;
	DescribeMontage(Montage, Slot, Action, Row);
	Row->SetStringField(TEXT("status"), TEXT("existing_preserved"));
	return true;
}

bool CreateMontage(const FPreparedMontage& Plan, FName Slot, FJson& Row)
{
	if (Plan.Existing) return true;
	UAnimMontageFactory* Factory = NewObject<UAnimMontageFactory>();
	Factory->SourceAnimation = Plan.Sequence.Get();
	UAnimMontage* Montage = Cast<UAnimMontage>(Factory->FactoryCreateNew(UAnimMontage::StaticClass(), CreatePackage(*Plan.Path),
		FName(*FPackageName::GetLongPackageAssetName(Plan.Path)), RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
	if (!Montage) return Fail(Plan.Path + TEXT(": factory failed"));
	TStrongObjectPtr<UAnimMontage> KeepAlive(Montage);
	MarkOwned(Montage);
	Montage->SlotAnimTracks.Reset();
	FSlotAnimationTrack& Track = Montage->SlotAnimTracks.AddDefaulted_GetRef();
	Track.SlotName = Slot;
	FAnimSegment& Segment = Track.AnimTrack.AnimSegments.AddDefaulted_GetRef();
	Segment.SetAnimReference(Plan.Sequence.Get(), true);
	Segment.StartPos = Segment.AnimStartTime = 0.f;
	Segment.AnimEndTime = Plan.Sequence->GetPlayLength();
	Segment.AnimPlayRate = 1.f;
	Segment.LoopingCount = 1;
	Segment.UpdateCachedPlayLength();
	Montage->SetCompositeLength(Plan.Sequence->GetPlayLength());
	Montage->CompositeSections.Reset();
	Montage->AddAnimCompositeSection(TEXT("Main"), 0.f);
	Montage->CompositeSections[0].NextSectionName = NAME_None;
	Montage->BlendIn.SetBlendTime(Plan.BlendIn);
	Montage->BlendOut.SetBlendTime(Plan.BlendOut);
	Montage->RateScale = 1.f;
	Montage->BlendOutTriggerTime = -1.f;
	Montage->bEnableAutoBlendOut = true;
	Montage->Notifies.Reset();
	if (!Plan.Windows.IsEmpty())
	{
		const FName NotifyTrack(TEXT("ConfirmedHitWindow"));
		UAnimationBlueprintLibrary::AddAnimationNotifyTrack(Montage, NotifyTrack, FLinearColor::Red);
		for (const FVector2f& Range : Plan.Windows)
		{
			auto* Notify = Cast<UGGYGOAnimNotifyState_GameplayEventWindow>(UAnimationBlueprintLibrary::AddAnimationNotifyStateEvent(
				Montage, NotifyTrack, Range.X, Range.Y - Range.X, UGGYGOAnimNotifyState_GameplayEventWindow::StaticClass()));
			if (!Notify) return Fail(Plan.Path + TEXT(": notify creation failed; new package remains unsaved"));
			Notify->InitializeEventTags(GGYGOGameplayTags::Event_Montage_HitWindowBegin, GGYGOGameplayTags::Event_Montage_HitWindowEnd);
		}
	}
	Montage->GetPackage()->GetMetaData().SetValue(Montage, TEXT("WindowSource"), *Plan.WindowSource);
	Montage->PostEditChange();
	if (Plan.bRequiresXYZ && !ValidateMotionMontage(Montage, Slot)) return false;
	FAssetRegistryModule::AssetCreated(Montage);
	if (!Save(Montage)) return Fail(Plan.Path + TEXT(": save failed; inspect the new package before retry"));
	Row->SetStringField(TEXT("status"), TEXT("created"));
	Row->SetBoolField(TEXT("saved_this_run"), true);
	return true;
}

struct FPreparedSockets
{
	FName Bone;
	FName Names[2];
	FVector Locations[2];
	USkeletalMeshSocket* Existing[2] = {};
};

void DescribeSocketPoint(const FJson& Report, const TCHAR* Key, const FVector& Point)
{
	TArray<TSharedPtr<FJsonValue>> Values;
	for (int32 Axis = 0; Axis < 3; ++Axis) Values.Add(MakeShared<FJsonValueNumber>(Point[Axis]));
	Report->SetArrayField(Key, Values);
}

bool MatchesSocket(USkeletalMesh* Mesh, USkeletalMeshSocket* Socket, FName Bone, const FVector& Location)
{
	return Socket && Socket->GetClass() == USkeletalMeshSocket::StaticClass() && Socket->GetOuter() == Mesh && Owned(Socket)
		&& Socket->BoneName == Bone && Socket->RelativeLocation.Equals(Location, 1.e-4)
		&& Socket->RelativeRotation.Equals(FRotator::ZeroRotator, 1.e-4)
		&& Socket->RelativeScale.Equals(FVector::OneVector, 1.e-4) && Socket->bForceAlwaysAnimated;
}

// Use imported UE geometry, never assume a source FBX axis survives import unchanged.
bool AuditSockets(USkeletalMesh* Mesh, const FJson& Config, FJson& Report, FPreparedSockets* Prepared = nullptr)
{
	Report->SetBoolField(TEXT("saved_this_run"), false);
	Report->SetBoolField(TEXT("write_performed"), false);
	Report->SetBoolField(TEXT("visually_confirmed"), false);
	Report->SetBoolField(TEXT("project_blade_candidate"), true);
	FString BoneText, MaterialText, StartText, EndText, Method;
	bool bEnabled = false;
	if (!Config || !Config->TryGetStringField(TEXT("parent_bone"), BoneText)
		|| !Config->TryGetStringField(TEXT("material_slot"), MaterialText)
		|| !Config->TryGetStringField(TEXT("start_socket"), StartText)
		|| !Config->TryGetStringField(TEXT("end_socket"), EndText)
		|| !Config->TryGetStringField(TEXT("method"), Method) || Method != TEXT("weapon_section_principal_axis_extents")
		|| !Config->TryGetBoolField(TEXT("enabled"), bEnabled))
		return Fail(Mesh->GetPathName() + TEXT(": explicit weapon geometry/socket configuration missing or invalid"));
	const FName Bone(*BoneText), Material(*MaterialText);
	const FName Names[] = {FName(*StartText), FName(*EndText)};
	if (Bone.IsNone() || Material.IsNone() || Names[0].IsNone() || Names[1].IsNone() || Names[0] == Names[1])
		return Fail(Mesh->GetPathName() + TEXT(": bone/material and distinct socket names required"));
	Report->SetBoolField(TEXT("configuration_enabled"), bEnabled);
	const auto& Ref = Mesh->GetRefSkeleton();
	const int32 BoneIndex = Ref.FindBoneIndex(Bone);
	const auto* Imported = Mesh->GetImportedModel();
	if (BoneIndex == INDEX_NONE || !Imported || Imported->LODModels.IsEmpty()) return Fail(TEXT("Missing socket bone/LOD0"));
	TArray<FTransform> ComponentPose;
	for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
	{
		const int32 Parent = Ref.GetParentIndex(Index);
		ComponentPose.Add(Parent == INDEX_NONE ? Ref.GetRefBonePose()[Index] : Ref.GetRefBonePose()[Index] * ComponentPose[Parent]);
	}
	if (!ComponentPose[BoneIndex].IsValid()) return Fail(Mesh->GetPathName() + TEXT(": invalid socket bone reference pose: ") + BoneText);
	TArray<FVector> Points;
	for (const auto& Section : Imported->LODModels[0].Sections)
	{
		if (!Mesh->GetMaterials().IsValidIndex(Section.MaterialIndex) || Mesh->GetMaterials()[Section.MaterialIndex].MaterialSlotName != Material) continue;
		for (const auto& Vertex : Section.SoftVertices)
		{
			uint16 LocalBone = 0;
			if (!Vertex.GetRigidWeightBone(LocalBone) || !Section.BoneMap.IsValidIndex(LocalBone) || Section.BoneMap[LocalBone] != BoneIndex)
				return Fail(TEXT("Weapon section is not rigidly weighted to configured bone"));
			const FVector Point = ComponentPose[BoneIndex].InverseTransformPosition(FVector(Vertex.Position));
			if (Point.ContainsNaN()) return Fail(Mesh->GetPathName() + TEXT(": nonfinite weapon vertex in ") + MaterialText);
			Points.Add(Point);
		}
	}
	if (Points.Num() < 2) return Fail(TEXT("Weapon section has no geometry"));
	FVector Mean = FVector::ZeroVector;
	for (const FVector& Point : Points) Mean += Point;
	Mean /= Points.Num();
	double Cov[3][3] = {};
	for (const FVector& Point : Points)
	{
		const FVector D = Point - Mean;
		for (int32 I = 0; I < 3; ++I) for (int32 J = 0; J < 3; ++J) Cov[I][J] += D[I] * D[J];
	}
	int32 Major = 0;
	for (int32 I = 1; I < 3; ++I) if (Cov[I][I] > Cov[Major][Major]) Major = I;
	FVector Axis = FVector::ZeroVector;
	Axis[Major] = 1;
	for (int32 Iteration = 0; Iteration < 32; ++Iteration)
	{
		FVector Next = FVector::ZeroVector;
		for (int32 I = 0; I < 3; ++I) for (int32 J = 0; J < 3; ++J) Next[I] += Cov[I][J] * Axis[J];
		if (!Next.Normalize()) return Fail(TEXT("Degenerate weapon geometry"));
		Axis = Next;
	}
	if (Axis[Major] < 0) Axis *= -1;
	double Min = TNumericLimits<double>::Max(), Max = TNumericLimits<double>::Lowest(), Radius = 0;
	for (const FVector& Point : Points)
	{
		const FVector D = Point - Mean;
		const double Projection = FVector::DotProduct(D, Axis);
		Min = FMath::Min(Min, Projection); Max = FMath::Max(Max, Projection);
		Radius = FMath::Max(Radius, (D - Projection * Axis).Length());
	}
	const FVector Locations[] = {Mean + Axis * Min, Mean + Axis * Max};
	if (!FMath::IsFinite(Max - Min) || !FMath::IsFinite(Radius) || Max - Min < 1
		|| Locations[0].ContainsNaN() || Locations[1].ContainsNaN()) return Fail(TEXT("Weapon trace geometry is nonfinite/degenerate"));
	USkeletalMeshSocket* Sockets[2] = {};
	for (int32 I = 0; I < 2; ++I)
	{
		if (Mesh->GetSkeleton()->FindSocket(Names[I])) return Fail(Mesh->GetPathName() + TEXT(": socket name already exists on Skeleton: ") + Names[I].ToString());
		for (USkeletalMeshSocket* Socket : Mesh->GetMeshOnlySocketList())
		{
			if (!Socket) return Fail(Mesh->GetPathName() + TEXT(": existing Mesh socket list contains null"));
			if (Socket->SocketName != Names[I]) continue;
			if (Sockets[I]) return Fail(Mesh->GetPathName() + TEXT(": duplicate Mesh socket: ") + Names[I].ToString());
			Sockets[I] = Socket;
			if (Socket->GetClass() != USkeletalMeshSocket::StaticClass() || Socket->GetOuter() != Mesh || !Owned(Socket))
				return Fail(Mesh->GetPathName() + TEXT(": refuses foreign/wrong-type socket: ") + Socket->GetPathName());
		}
	}
	Report->SetStringField(TEXT("start_bone_local_cm"), Locations[0].ToString());
	Report->SetStringField(TEXT("end_bone_local_cm"), Locations[1].ToString());
	DescribeSocketPoint(Report, TEXT("start_bone_local_xyz_cm"), Locations[0]);
	DescribeSocketPoint(Report, TEXT("end_bone_local_xyz_cm"), Locations[1]);
	Report->SetStringField(TEXT("bone"), Bone.ToString());
	Report->SetNumberField(TEXT("ue_section_vertices"), Points.Num());
	Report->SetNumberField(TEXT("segment_length_cm"), Max - Min);
	Report->SetNumberField(TEXT("geometry_max_radial_extent_cm"), Radius);
	Report->SetBoolField(TEXT("all_vertices_rigid_to_bone"), true);
	if (Sockets[0] || Sockets[1])
	{
		if (!Sockets[0] || !Sockets[1]) return Fail(Mesh->GetPathName() + TEXT(": owned socket pair is incomplete; no automatic repair"));
		for (int32 I = 0; I < 2; ++I)
			if (!MatchesSocket(Mesh, Sockets[I], Bone, Locations[I]))
				return Fail(Mesh->GetPathName() + TEXT(": owned socket disagrees with exact project geometry/transform: ") + Sockets[I]->GetPathName());
		Report->SetStringField(TEXT("status"), TEXT("existing_preserved"));
		Report->SetBoolField(TEXT("existing_owned_pair_verified"), true);
	}
	else
	{
		Report->SetStringField(TEXT("status"), TEXT("geometry_candidate_sockets_missing"));
		Report->SetBoolField(TEXT("existing_owned_pair_verified"), false);
	}
	if (Prepared)
	{
		Prepared->Bone = Bone;
		for (int32 I = 0; I < 2; ++I)
		{
			Prepared->Names[I] = Names[I]; Prepared->Locations[I] = Locations[I]; Prepared->Existing[I] = Sockets[I];
		}
	}
	return true;
}

UEdGraphPin* Pin(UEdGraphNode* Node, EEdGraphPinDirection Direction)
{
	for (auto* Item : Node->Pins) if (Item->Direction == Direction && Item->PinType.PinCategory == TEXT("struct")) return Item;
	return nullptr;
}
template<typename T> T* AddNode(UEdGraph* Graph, int32 X)
{
	T* Node = NewObject<T>(Graph, NAME_None, RF_Transactional);
	Graph->AddNode(Node, false, false); Node->CreateNewGuid(); Node->PostPlacedNewNode(); Node->AllocateDefaultPins(); Node->NodePosX = X;
	return Node;
}
bool HasIdleSlotChain(UAnimBlueprint* BP, UAnimSequence* StandBy, FName Slot)
{
	for (UEdGraph* Graph : BP->FunctionGraphs)
	{
		if (Graph->GetFName() != TEXT("AnimGraph")) continue;
		UAnimGraphNode_Root* Root = nullptr;
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			if (auto* Candidate = Cast<UAnimGraphNode_Root>(Node))
			{
				if (Root) return false;
				Root = Candidate;
			}
		}
		UEdGraphPin* RootInput = Root ? Pin(Root, EGPD_Input) : nullptr;
		if (!RootInput || RootInput->LinkedTo.Num() != 1) return false;
		auto* SlotNode = Cast<UAnimGraphNode_Slot>(RootInput->LinkedTo[0]->GetOwningNode());
		if (!SlotNode || SlotNode->Node.SlotName != Slot || RootInput->LinkedTo[0] != Pin(SlotNode, EGPD_Output)) return false;
		UEdGraphPin* SlotInput = Pin(SlotNode, EGPD_Input);
		if (!SlotInput || SlotInput->LinkedTo.Num() != 1) return false;
		auto* Player = Cast<UAnimGraphNode_SequencePlayer>(SlotInput->LinkedTo[0]->GetOwningNode());
		if (!Player || SlotInput->LinkedTo[0] != Pin(Player, EGPD_Output)
			|| Player->Node.GetSequence() != StandBy || !Player->Node.IsLooping()) return false;
		for (UEdGraphPin* Input : Player->Pins)
			if (Input->Direction == EGPD_Input && !Input->LinkedTo.IsEmpty()) return false;
		return true;
	}
	return false;
}

struct FPreparedAnimBP
{
	FString Path;
	TStrongObjectPtr<UAnimSequence> StandBy;
	TStrongObjectPtr<UAnimBlueprint> Existing;
};

bool PrepareAnimBP(const FJson& Config, USkeleton* Skeleton, FName Slot, FPreparedAnimBP& Plan, FJson& Report)
{
	FString IdlePath, Mode;
	if (!Config || !Config->TryGetStringField(TEXT("asset"), Plan.Path)
		|| !Config->TryGetStringField(TEXT("idle_sequence"), IdlePath)
		|| !Config->TryGetStringField(TEXT("mode"), Mode) || Mode != TEXT("guard_standard_slot_idle_loop"))
		return Fail(TEXT("AnimBP asset/idle/explicit ordinary Guard mode missing or invalid"));
	Report->SetStringField(TEXT("asset"), Plan.Path);
	Plan.StandBy.Reset(Load<UAnimSequence>(IdlePath));
	if (!Plan.StandBy || Plan.StandBy->GetSkeleton() != Skeleton || Plan.StandBy->GetPackage()->IsDirty()
		|| !FMath::IsFinite(Plan.StandBy->GetPlayLength()) || Plan.StandBy->GetPlayLength() <= 0)
		return Fail(Plan.Path + TEXT(": invalid/unsaved idle animation: ") + IdlePath);
	UObject* Object = Load<UObject>(Plan.Path);
	UAnimBlueprint* BP = Cast<UAnimBlueprint>(Object);
	if (Object && (!BP || !Owned(BP) || BP->GetPackage()->IsDirty()))
		return Fail(Plan.Path + TEXT(": refuses wrong type, foreign/unsaved AnimBP"));
	if (!BP)
	{
		if (FPackageName::DoesPackageExist(Plan.Path)) return Fail(Plan.Path + TEXT(": existing AnimBP package could not be loaded"));
		if (const UPackage* Package = FindPackage(nullptr, *Plan.Path))
			if (Package->IsDirty()) return Fail(Plan.Path + TEXT(": unsaved target package; inspect before retry"));
		Report->SetStringField(TEXT("status"), TEXT("planned_missing"));
		return true;
	}
	const auto* Defaults = BP->GeneratedClass ? Cast<UGGYGOMontageGuardAnimInstance>(BP->GeneratedClass->GetDefaultObject()) : nullptr;
	if (BP->TargetSkeleton != Skeleton || BP->ParentClass != UGGYGOMontageGuardAnimInstance::StaticClass()
		|| !Defaults || !Defaults->RequiredPoseCorrectionSlot.IsNone() || !HasIdleSlotChain(BP, Plan.StandBy.Get(), Slot)
		|| (BP->Status != BS_UpToDate && BP->Status != BS_UpToDateWithWarnings))
		return Fail(Plan.Path + TEXT(": compiled Guard/ordinary Slot/idle chain contract failed; graph preserved"));
	Plan.Existing.Reset(BP);
	Report->SetStringField(TEXT("status"), TEXT("existing_preserved"));
	Report->SetBoolField(TEXT("compiled_pose_chain"), true);
	return true;
}

bool CreateAnimBP(const FPreparedAnimBP& Plan, USkeleton* Skeleton, USkeletalMesh* Mesh, FName Slot, FJson& Report)
{
	if (Plan.Existing) return true;
	UAnimBlueprintFactory* Factory = NewObject<UAnimBlueprintFactory>();
	Factory->ParentClass = UGGYGOMontageGuardAnimInstance::StaticClass();
	Factory->TargetSkeleton = Skeleton;
	Factory->PreviewSkeletalMesh = Mesh;
	UAnimBlueprint* BP = Cast<UAnimBlueprint>(Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(), CreatePackage(*Plan.Path),
		FName(*FPackageName::GetLongPackageAssetName(Plan.Path)), RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
	if (!BP) return Fail(Plan.Path + TEXT(": AnimBP factory failed"));
	TStrongObjectPtr<UAnimBlueprint> KeepAlive(BP);
	MarkOwned(BP);
	UEdGraph* Graph = nullptr;
	for (UEdGraph* Candidate : BP->FunctionGraphs) if (Candidate->GetFName() == TEXT("AnimGraph")) Graph = Candidate;
	if (!Graph || !Graph->GetSchema()) return Fail(Plan.Path + TEXT(": AnimGraph/schema missing"));
	// Only a newly created factory graph is replaced. Existing authored topology is read-only.
	const auto FactoryNodes = Graph->Nodes;
	for (UEdGraphNode* Node : FactoryNodes) Graph->RemoveNode(Node);
	auto* Player = AddNode<UAnimGraphNode_SequencePlayer>(Graph, -500);
	Player->Node.SetSequence(Plan.StandBy.Get());
	Player->Node.SetLoopAnimation(true);
	auto* SlotNode = AddNode<UAnimGraphNode_Slot>(Graph, -250);
	SlotNode->Node.SlotName = Slot;
	auto* Root = AddNode<UAnimGraphNode_Root>(Graph, 0);
	UEdGraphPin* Output = Pin(Player, EGPD_Output); UEdGraphPin* SlotInput = Pin(SlotNode, EGPD_Input);
	UEdGraphPin* SlotOutput = Pin(SlotNode, EGPD_Output); UEdGraphPin* RootInput = Pin(Root, EGPD_Input);
	if (!Output || !SlotInput || !SlotOutput || !RootInput
		|| !Graph->GetSchema()->TryCreateConnection(Output, SlotInput)
		|| !Graph->GetSchema()->TryCreateConnection(SlotOutput, RootInput))
		return Fail(Plan.Path + TEXT(": AnimBP pose links failed"));
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);
	const auto* Defaults = BP->GeneratedClass ? Cast<UGGYGOMontageGuardAnimInstance>(BP->GeneratedClass->GetDefaultObject()) : nullptr;
	if ((BP->Status != BS_UpToDate && BP->Status != BS_UpToDateWithWarnings) || !Defaults
		|| !Defaults->RequiredPoseCorrectionSlot.IsNone() || !HasIdleSlotChain(BP, Plan.StandBy.Get(), Slot))
		return Fail(Plan.Path + TEXT(": AnimBP compile/Guard/pose contract failed; new package remains unsaved"));
	FAssetRegistryModule::AssetCreated(BP);
	if (!Save(BP)) return Fail(Plan.Path + TEXT(": AnimBP save failed; inspect before retry"));
	Report->SetStringField(TEXT("status"), TEXT("created"));
	Report->SetBoolField(TEXT("compiled_pose_chain"), true);
	Report->SetBoolField(TEXT("saved_this_run"), true);
	return true;
}

bool CheckNewTargets(const TArray<FString>& Args, const TArray<FString>& Missing)
{
	TSet<FString> Approved;
	for (int32 Index = 2; Index < Args.Num(); ++Index)
	{
		if (!Missing.Contains(Args[Index]) || Approved.Contains(Args[Index]))
			return Fail(TEXT("Approved new package list must exactly match missing targets: ") + Args[Index]);
		Approved.Add(Args[Index]);
	}
	for (const FString& Path : Missing)
	{
		if (!Approved.Contains(Path)) return Fail(TEXT("Missing explicit new-package authorization: ") + Path);
		if (UPackage* Package = FindPackage(nullptr, *Path))
			if (Package->IsDirty()) return Fail(Path + TEXT(": unsaved package exists; inspect before retry"));
	}
	return true;
}

bool ValidateSlotGroups(const USkeleton* Skeleton, FName Slot, FName& SerializedGroup)
{
	SerializedGroup = NAME_None;
	TSet<FName> Groups, Slots;
	for (const FAnimSlotGroup& Group : Skeleton->GetSlotGroups())
	{
		if (Group.GroupName.IsNone() || Groups.Contains(Group.GroupName))
			return Fail(Skeleton->GetPathName() + TEXT(": invalid/duplicate serialized Slot group"));
		Groups.Add(Group.GroupName);
		for (FName Name : Group.SlotNames)
		{
			if (Name.IsNone() || Slots.Contains(Name) || !Skeleton->ContainsSlotName(Name)
				|| Skeleton->GetSlotGroupName(Name) != Group.GroupName)
				return Fail(Skeleton->GetPathName() + TEXT(": serialized Slot groups/native mapping disagree: ") + Name.ToString());
			Slots.Add(Name);
			if (Name == Slot) SerializedGroup = Group.GroupName;
		}
	}
	return (Skeleton->ContainsSlotName(Slot) == !SerializedGroup.IsNone())
		|| Fail(Skeleton->GetPathName() + TEXT(": required Slot serialized/native presence disagrees: ") + Slot.ToString());
}

void DescribeSkeletonSlot(const USkeleton* Skeleton, FName Slot, FJson& Row)
{
	Row->SetStringField(TEXT("asset"), Skeleton->GetPathName());
	Row->SetStringField(TEXT("slot"), Slot.ToString());
	Row->SetBoolField(TEXT("native_slot_present"), Skeleton->ContainsSlotName(Slot));
	Row->SetStringField(TEXT("native_slot_group"), Skeleton->ContainsSlotName(Slot) ? Skeleton->GetSlotGroupName(Slot).ToString() : FString());
	TArray<TSharedPtr<FJsonValue>> Groups;
	for (const FAnimSlotGroup& Group : Skeleton->GetSlotGroups())
	{
		FJson Item = MakeShared<FJsonObject>();
		Item->SetStringField(TEXT("group"), Group.GroupName.ToString());
		TArray<TSharedPtr<FJsonValue>> Slots;
		for (FName Name : Group.SlotNames) Slots.Add(MakeShared<FJsonValueString>(Name.ToString()));
		Item->SetArrayField(TEXT("slots"), Slots);
		Groups.Add(MakeShared<FJsonValueObject>(Item));
	}
	Row->SetArrayField(TEXT("slot_groups"), Groups);
	Row->SetStringField(TEXT("skeleton_guid"), Skeleton->GetGuid().ToString());
	Row->SetNumberField(TEXT("raw_bone_count"), Skeleton->GetReferenceSkeleton().GetRawBoneNum());
	Row->SetNumberField(TEXT("retarget_source_count"), Skeleton->AnimRetargetSources.Num());
	Row->SetNumberField(TEXT("compatible_skeleton_count"), Skeleton->GetCompatibleSkeletons().Num());
	Row->SetNumberField(TEXT("socket_count"), Skeleton->Sockets.Num());
}

// Same-call, exact binary comparison; never serializes the Skeleton UObject itself
// (USkeleton::Serialize rebuilds its Slot map). No protection state survives this call.
bool ReadSlotProtection(USkeleton* Skeleton, TArray<uint8>& Bytes)
{
	Bytes.Reset();
	FMemoryWriter MemoryWriter(Bytes);
	FObjectAndNameAsStringProxyArchive Proxy(MemoryWriter, false);
	FArchive& Writer = Proxy;
	const auto WriteProperties = [&Writer](UObject* Object)
	{
		for (TFieldIterator<FProperty> It(Object->GetClass()); It; ++It)
		{
			FProperty* Property = *It;
			if (Property->GetFName() != TEXT("SlotGroups") && !Property->HasAnyPropertyFlags(CPF_Transient))
				Property->SerializeBinProperty(FStructuredArchiveFromArchive(Writer).GetSlot(), Object);
		}
	};
	WriteProperties(Skeleton);
	for (USkeletalMeshSocket* Socket : Skeleton->Sockets) if (Socket) WriteProperties(Socket);
	FReferenceSkeleton Reference = Skeleton->GetReferenceSkeleton();
	FGuid Guid = Skeleton->GetGuid();
	Writer << Reference << Guid;
	for (const auto& Entry : Skeleton->AnimRetargetSources)
	{
		FName Name = Entry.Key;
		FReferencePose Pose = Entry.Value;
		Writer << Name;
		FReferencePose::StaticStruct()->SerializeItem(FStructuredArchiveFromArchive(Writer).GetSlot(), &Pose, nullptr);
	}
	TArray<FName> MarkerNames = Skeleton->GetExistingMarkerNames();
	Writer << MarkerNames;
	FMetaData& MetaData = Skeleton->GetPackage()->GetMetaData();
	Writer << MetaData;
	return !Writer.IsError() || Fail(Skeleton->GetPathName() + TEXT(": protected Skeleton data serialization failed"));
}

/** Exact same-call protection of the existing Mesh and Skeleton; new Socket metadata is separate. */
bool ReadSocketProtection(USkeletalMesh* Mesh, USkeleton* Skeleton,
	const TArray<TStrongObjectPtr<UObject>>& OriginalMeshObjects, TArray<uint8>& Bytes)
{
	// Keep the established Skeleton reader, then include the Slot field it excludes
	// for registration and the native map facts. Socket preparation changes none of them.
	if (!ReadSlotProtection(Skeleton, Bytes)) return false;
	FMemoryWriter MemoryWriter(Bytes);
	MemoryWriter.Seek(Bytes.Num());
	FObjectAndNameAsStringProxyArchive Proxy(MemoryWriter, false);
	FArchive& Writer = Proxy;
	FProperty* Groups = FindFProperty<FProperty>(Skeleton->GetClass(), TEXT("SlotGroups"));
	if (!Groups) return Fail(Skeleton->GetPathName() + TEXT(": native SlotGroups protection unavailable"));
	Groups->SerializeBinProperty(FStructuredArchiveFromArchive(Writer).GetSlot(), Skeleton);
	for (const FAnimSlotGroup& Group : Skeleton->GetSlotGroups())
		for (FName SlotName : Group.SlotNames)
		{
			FName NativeGroup = Skeleton->GetSlotGroupName(SlotName);
			Writer << NativeGroup;
		}
	for (const TStrongObjectPtr<UObject>& Original : OriginalMeshObjects)
	{
		UObject* Object = Original.Get();
		FString Path = Object->GetPathName();
		Writer << Path;
		for (TFieldIterator<FProperty> It(Object->GetClass()); It; ++It)
		{
			FProperty* Property = *It;
			if (!Property->HasAnyPropertyFlags(CPF_Transient) && !(Object == Mesh && Property->GetFName() == TEXT("Sockets")))
				Property->SerializeBinProperty(FStructuredArchiveFromArchive(Writer).GetSlot(), Object);
		}
		const TMap<FName, FString>* Meta = FMetaData::GetMapForObject(Object);
		bool bHasMetadata = Meta != nullptr;
		Writer << bHasMetadata;
		if (Meta)
		{
			TMap<FName, FString> Values = *Meta;
			Writer << Values;
		}
	}
	FReferenceSkeleton Reference = Mesh->GetRefSkeleton();
	Writer << Reference;
	return !Writer.IsError() || Fail(Mesh->GetPathName() + TEXT(": protected Mesh/Skeleton data serialization failed"));
}

/** Explicit Mesh-only construction; no RenameSocket or Skeleton mutation is involved. */
bool BuildSockets(USkeletalMesh* Mesh, USkeleton* Skeleton, const FPreparedSockets& Plan,
	const FString& ApprovedPackage, const FString& BackupArgument, FJson& Row)
{
	const FString MeshPackage = Mesh->GetPackage()->GetName();
	if (MeshPackage != TEXT("/Game/Characters/Boss/Kevin/DemonBattle/Mesh/SK_Kevin_DemonBattle")
		|| ApprovedPackage != MeshPackage || !FPackageName::DoesPackageExist(MeshPackage)
		|| Mesh->GetPackage() == Skeleton->GetPackage())
		return Fail(Mesh->GetPathName() + TEXT(": build-sockets requires the exact existing Kevin Mesh package with a separate Skeleton: ") + ApprovedPackage);
	TArray<UObject*> PackageObjects;
	GetObjectsWithOuter(Mesh->GetPackage(), PackageObjects, EGetObjectsFlags::None);
	for (UObject* Object : PackageObjects)
		if (Object != Mesh && Object->IsAsset()) return Fail(MeshPackage + TEXT(": refuses another asset in the same package: ") + Object->GetPathName());
	if (Plan.Existing[0]) return true; // Already audited complete, owned and exact; no backup, Modify or Save.
	FString Backup = FPaths::ConvertRelativePathToFull(BackupArgument);
	FPaths::NormalizeFilename(Backup);
	if (!FPaths::CollapseRelativeDirectories(Backup) || !FPaths::IsUnderDirectory(Backup, FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir()))
		|| FPaths::GetExtension(Backup) != TEXT("uasset") || IFileManager::Get().FileExists(*Backup))
		return Fail(MeshPackage + TEXT(": backup must be a new explicit .uasset path inside project Saved: ") + BackupArgument);
	const FString SourceFile = FPackageName::LongPackageNameToFilename(MeshPackage, FPackageName::GetAssetPackageExtension());
	if (!IFileManager::Get().MakeDirectory(*FPaths::GetPath(Backup), true)
		|| IFileManager::Get().Copy(*Backup, *SourceFile, false) != COPY_OK)
		return Fail(MeshPackage + TEXT(": exact original Mesh backup failed: ") + Backup);
	Row->SetStringField(TEXT("backup_file"), Backup);
	Row->SetBoolField(TEXT("backup_copy_success"), true);
	TArray<UObject*> MeshObjects;
	GetObjectsWithOuter(Mesh->GetPackage(), MeshObjects, EGetObjectsFlags::IncludeNestedObjects);
	TArray<TStrongObjectPtr<UObject>> Originals;
	for (UObject* Object : MeshObjects) Originals.Emplace(Object);
	TArray<uint8> ProtectedBefore, ProtectedAfter;
	if (!ReadSocketProtection(Mesh, Skeleton, Originals, ProtectedBefore)) return false;
	auto ExpectedSockets = Mesh->GetMeshOnlySocketList();
	TStrongObjectPtr<USkeletalMeshSocket> Created[2];
	for (int32 I = 0; I < 2; ++I)
	{
		Created[I].Reset(NewObject<USkeletalMeshSocket>(Mesh, NAME_None, RF_Transactional));
		USkeletalMeshSocket* Socket = Created[I].Get();
		Socket->SocketName = Plan.Names[I]; Socket->BoneName = Plan.Bone;
		Socket->RelativeLocation = Plan.Locations[I]; Socket->RelativeRotation = FRotator::ZeroRotator;
		Socket->RelativeScale = FVector::OneVector; Socket->bForceAlwaysAnimated = true;
		MarkOwned(Socket);
		ExpectedSockets.Add(Socket);
	}
	Mesh->Modify();
	Row->SetBoolField(TEXT("write_performed"), true);
	for (const TStrongObjectPtr<USkeletalMeshSocket>& Socket : Created) Mesh->AddSocket(Socket.Get(), false);
	const auto HasExactPair = [&]()
	{
		if (Mesh->GetMeshOnlySocketList() != ExpectedSockets) return false;
		for (int32 I = 0; I < 2; ++I)
			if (Skeleton->FindSocket(Plan.Names[I]) || Mesh->FindSocket(Plan.Names[I]) != Created[I].Get()
				|| !MatchesSocket(Mesh, Created[I].Get(), Plan.Bone, Plan.Locations[I])) return false;
		return true;
	};
	if (!HasExactPair() || Skeleton->GetPackage()->IsDirty()
		|| !ReadSocketProtection(Mesh, Skeleton, Originals, ProtectedAfter) || ProtectedAfter != ProtectedBefore)
	{
		Row->SetStringField(TEXT("status"), TEXT("creation_validation_failed"));
		return Fail(MeshPackage + TEXT(": Socket construction changed protected data or exact pair; not saved, inspect before retry"));
	}
	if (!Save(Mesh))
	{
		Row->SetStringField(TEXT("status"), TEXT("save_failed"));
		return Fail(MeshPackage + TEXT(": single Mesh Socket save failed; inspect before retry"));
	}
	Row->SetBoolField(TEXT("saved_this_run"), true);
	const bool bProtected = ReadSocketProtection(Mesh, Skeleton, Originals, ProtectedAfter) && ProtectedAfter == ProtectedBefore;
	Row->SetBoolField(TEXT("protected_data_unchanged"), bProtected);
	if (!bProtected || !HasExactPair() || Mesh->GetPackage()->IsDirty() || Skeleton->GetPackage()->IsDirty())
	{
		Row->SetStringField(TEXT("status"), TEXT("saved_validation_failed"));
		return Fail(MeshPackage + TEXT(": saved Mesh pair/protected data/clean-package contract failed"));
	}
	Row->SetStringField(TEXT("status"), TEXT("created_and_saved"));
	Row->SetBoolField(TEXT("existing_owned_pair_verified"), true);
	return true;
}

/** Register only the explicitly approved existing Kevin Skeleton's missing Slot and save that one package. */
bool PrepareSlot(const FString& ApprovedPackage, const FString& SkeletonPath, USkeleton* Skeleton, FName Slot, FJson& Row)
{
	Row->SetStringField(TEXT("status"), TEXT("validation_failed"));
	Row->SetBoolField(TEXT("saved_this_run"), false);
	Row->SetBoolField(TEXT("write_performed"), false);
	if (SkeletonPath != TEXT("/Game/Characters/Boss/Kevin/DemonBattle/Mesh/SK_Kevin_DemonBattle_Skeleton")
		|| ApprovedPackage != SkeletonPath || Skeleton->GetPackage()->GetName() != SkeletonPath
		|| !FPackageName::DoesPackageExist(SkeletonPath))
		return Fail(Skeleton->GetPathName() + TEXT(": prepare-slot needs the exact existing configured Kevin Skeleton package argument: ") + ApprovedPackage);
	TArray<UObject*> PackageObjects;
	GetObjectsWithOuter(Skeleton->GetPackage(), PackageObjects, EGetObjectsFlags::None);
	for (UObject* Object : PackageObjects)
		if (Object != Skeleton && Object->IsAsset())
			return Fail(SkeletonPath + TEXT(": refuses to save a package containing another asset: ") + Object->GetPathName());
	FName SerializedGroup;
	if (!ValidateSlotGroups(Skeleton, Slot, SerializedGroup)) return false;
	if (!SerializedGroup.IsNone())
	{
		Row->SetStringField(TEXT("status"), TEXT("already_present"));
		return true;
	}
	TArray<uint8> ProtectedBefore, ProtectedAfter;
	if (!ReadSlotProtection(Skeleton, ProtectedBefore)) return false;
	TArray<FAnimSlotGroup> ExpectedGroups = Skeleton->GetSlotGroups();
	FAnimSlotGroup* DefaultGroup = ExpectedGroups.FindByPredicate([](const FAnimSlotGroup& Group)
		{ return Group.GroupName == FAnimSlotGroup::DefaultGroupName; });
	if (!DefaultGroup)
	{
		DefaultGroup = &ExpectedGroups.AddDefaulted_GetRef();
		DefaultGroup->GroupName = FAnimSlotGroup::DefaultGroupName;
	}
	DefaultGroup->SlotNames.Add(Slot);
	const auto HasExpectedGroups = [&ExpectedGroups, Skeleton]()
	{
		const TArray<FAnimSlotGroup>& Actual = Skeleton->GetSlotGroups();
		if (Actual.Num() != ExpectedGroups.Num()) return false;
		for (int32 Index = 0; Index < Actual.Num(); ++Index)
			if (Actual[Index].GroupName != ExpectedGroups[Index].GroupName || Actual[Index].SlotNames != ExpectedGroups[Index].SlotNames) return false;
		return true;
	};
	Skeleton->Modify();
	Row->SetBoolField(TEXT("write_performed"), true);
	if (!Skeleton->RegisterSlotNode(Slot) || !Skeleton->ContainsSlotName(Slot)
		|| Skeleton->GetSlotGroupName(Slot) != FAnimSlotGroup::DefaultGroupName || !HasExpectedGroups()
		|| !ReadSlotProtection(Skeleton, ProtectedAfter) || ProtectedAfter != ProtectedBefore)
	{
		Row->SetStringField(TEXT("status"), TEXT("registration_failed"));
		return Fail(SkeletonPath + TEXT(": native Slot registration changed unexpected groups or protected Skeleton data; package not saved, inspect before retry"));
	}
	if (!Save(Skeleton))
	{
		Row->SetStringField(TEXT("status"), TEXT("save_failed"));
		return Fail(SkeletonPath + TEXT(": exact Skeleton package save failed; inspect before retry"));
	}
	Row->SetBoolField(TEXT("saved_this_run"), true);
	const bool bProtected = ReadSlotProtection(Skeleton, ProtectedAfter) && ProtectedAfter == ProtectedBefore;
	Row->SetBoolField(TEXT("protected_data_unchanged"), bProtected);
	if (Skeleton->GetPackage()->IsDirty() || !ValidateSlotGroups(Skeleton, Slot, SerializedGroup)
		|| SerializedGroup != FAnimSlotGroup::DefaultGroupName || !HasExpectedGroups() || !bProtected)
	{
		Row->SetStringField(TEXT("status"), TEXT("saved_validation_failed"));
		return Fail(SkeletonPath + TEXT(": save completed but Slot/protected data/clean-package contract failed; inspect saved package"));
	}
	Row->SetStringField(TEXT("status"), TEXT("registered_and_saved"));
	return true;
}

void Build(const TArray<FString>& Args)
{
	if (Args.Num() < 2)
	{
		Fail(TEXT("Expected <audit-standby|build-standby|audit-actions|build-actions|audit-sockets|build-sockets|prepare-slot> <config> [exact new packages; or exact existing Mesh plus new Saved backup for build-sockets; or exact Skeleton for prepare-slot]"));
		return;
	}
	const bool bStandby = Args[0] == TEXT("audit-standby") || Args[0] == TEXT("build-standby");
	const bool bActions = Args[0] == TEXT("audit-actions") || Args[0] == TEXT("build-actions");
	const bool bSockets = Args[0] == TEXT("audit-sockets") || Args[0] == TEXT("build-sockets");
	const bool bBuildSockets = Args[0] == TEXT("build-sockets");
	const bool bPrepareSlot = Args[0] == TEXT("prepare-slot");
	const bool bWrite = Args[0] == TEXT("build-standby") || Args[0] == TEXT("build-actions") || bPrepareSlot || bBuildSockets;
	if ((!bStandby && !bActions && !bSockets && !bPrepareSlot) || (!bWrite && Args.Num() != 2)
		|| (bPrepareSlot && Args.Num() != 3) || (bBuildSockets && Args.Num() != 4))
	{
		Fail(TEXT("Unknown mode or unexpected audit arguments"));
		return;
	}
	FString Text; FJson Config;
	int32 Schema = 0;
	FString MeshPath, SkeletonPath, SlotName;
	if (!FFileHelper::LoadFileToString(Text, *Args[1]) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Config)
		|| !Config || !Config->TryGetNumberField(TEXT("schema_version"), Schema) || Schema != 2
		|| !Config->TryGetStringField(TEXT("mesh"), MeshPath) || !Config->TryGetStringField(TEXT("skeleton"), SkeletonPath)
		|| !Config->TryGetStringField(TEXT("slot"), SlotName))
	{ Fail(TEXT("Unreadable schema2 config: ") + Args[1]); return; }
	USkeletalMesh* Mesh = Load<USkeletalMesh>(MeshPath);
	USkeleton* Skeleton = Load<USkeleton>(SkeletonPath);
	TStrongObjectPtr<USkeletalMesh> KeepMesh(Mesh);
	TStrongObjectPtr<USkeleton> KeepSkeleton(Skeleton);
	const FName Slot(*SlotName);
	if (!Mesh || !Skeleton || Mesh->GetSkeleton() != Skeleton || Mesh->GetPackage()->IsDirty()
		|| Skeleton->GetPackage()->IsDirty() || Slot != TEXT("DefaultSlot"))
	{ Fail(TEXT("Invalid/unsaved Kevin mesh/skeleton or non-DefaultSlot config: ") + MeshPath + TEXT(" / ") + SkeletonPath); return; }
	FJson Report = MakeShared<FJsonObject>();
	FJson SkeletonRow = MakeShared<FJsonObject>();
	bool bSuccess = false;
	TArray<FString> Missing;
	FName SerializedGroup;
	// Animation generation still requires prior explicit registration; it never repairs or saves the Skeleton.
	if (bPrepareSlot)
		bSuccess = PrepareSlot(Args[2], SkeletonPath, Skeleton, Slot, SkeletonRow);
	else if (!bSockets && (!ValidateSlotGroups(Skeleton, Slot, SerializedGroup) || !Skeleton->ContainsSlotName(Slot)))
	{
		SkeletonRow->SetStringField(TEXT("status"), TEXT("validation_failed"));
		if (!Skeleton->ContainsSlotName(Slot)) Fail(SkeletonPath + TEXT(": required Slot is missing; animation generation does not save the Skeleton"));
	}
	else if (bSockets)
	{
		const FJson* SocketConfig = nullptr;
		FJson Row = MakeShared<FJsonObject>();
		bSuccess = Config->TryGetObjectField(TEXT("socket_config"), SocketConfig);
		if (!bSuccess) Fail(TEXT("Socket audit config missing/invalid"));
		else
		{
			// Explicit Socket modes select the geometry candidate, independently of gameplay enablement.
			FPreparedSockets Plan;
			bSuccess = AuditSockets(Mesh, *SocketConfig, Row, &Plan);
			if (bSuccess && bBuildSockets) bSuccess = BuildSockets(Mesh, Skeleton, Plan, Args[2], Args[3], Row);
		}
		Report->SetObjectField(TEXT("sockets"), Row);
	}
	else if (bStandby)
	{
		const FJson* BPConfig = nullptr;
		FPreparedAnimBP Plan; FJson Row = MakeShared<FJsonObject>();
		bSuccess = Config->TryGetObjectField(TEXT("anim_blueprint"), BPConfig)
			&& PrepareAnimBP(*BPConfig, Skeleton, Slot, Plan, Row);
		if (bSuccess && (!FPackageName::IsValidLongPackageName(Plan.Path)
			|| (Plan.Existing && !FPackageName::DoesPackageExist(Plan.Path))
			|| !Plan.Path.StartsWith(TEXT("/Game/Characters/Boss/Kevin/DemonBattle/Animation/"))))
			bSuccess = Fail(TEXT("AnimBP target must be an explicit Kevin Animation package"));
		if (bSuccess && !Plan.Existing) Missing.Add(Plan.Path);
		if (bSuccess && bWrite) bSuccess = CheckNewTargets(Args, Missing) && CreateAnimBP(Plan, Skeleton, Mesh, Slot, Row);
		Report->SetObjectField(TEXT("anim_blueprint"), Row);
	}
	else
	{
		const TArray<TSharedPtr<FJsonValue>>* Selected = nullptr;
		const TArray<TSharedPtr<FJsonValue>>* Catalog = nullptr;
		if (!Config->TryGetArrayField(TEXT("selected_actions"), Selected) || Selected->IsEmpty()
			|| !Config->TryGetArrayField(TEXT("actions"), Catalog))
		{ Fail(TEXT("Explicit nonempty selected_actions/catalog required; no default action batch")); return; }
		TArray<FPreparedMontage> Plans;
		TArray<TSharedPtr<FJsonValue>> Rows;
		TSet<FString> Names, Targets;
		bSuccess = true;
		for (const auto& Value : *Selected)
		{
			FString Name;
			if (!Value->TryGetString(Name) || Name.IsEmpty() || Names.Contains(Name))
			{ bSuccess = Fail(TEXT("Invalid/duplicate selected action")); break; }
			Names.Add(Name);
			FJson Action;
			for (const auto& Entry : *Catalog)
			{
				FString Candidate;
				const FJson Object = Entry->AsObject();
				if (Object && Object->TryGetStringField(TEXT("source_clip"), Candidate) && Candidate == Name)
				{
					if (Action) { bSuccess = Fail(TEXT("Ambiguous catalog action: ") + Name); break; }
					Action = Object;
				}
			}
			if (!bSuccess) break;
			if (!Action) { bSuccess = Fail(TEXT("Selected action missing from catalog: ") + Name); break; }
			FJson Row = MakeShared<FJsonObject>();
			FPreparedMontage Plan;
			Rows.Add(MakeShared<FJsonValueObject>(Row));
			bSuccess = PrepareMontage(Action, Skeleton, Slot, Plan, Row);
			if (!bSuccess) break;
			if (!Plan.bRequiresXYZ || !FPackageName::IsValidLongPackageName(Plan.Path)
				|| (Plan.Existing && !FPackageName::DoesPackageExist(Plan.Path))
				|| !Plan.Path.StartsWith(TEXT("/Game/Characters/Boss/Kevin/DemonBattle/Animation/Montage/"))
				|| Targets.Contains(Plan.Path))
			{ bSuccess = Fail(Name + TEXT(": needs unique Kevin montage target and paired XYZ derived sequence")); break; }
			Targets.Add(Plan.Path);
			if (!Plan.Existing) Missing.Add(Plan.Path);
			Plans.Add(MoveTemp(Plan));
		}
		// Preflight the complete selected batch before the first factory/save operation.
		if (bSuccess && bWrite)
		{
			bSuccess = CheckNewTargets(Args, Missing);
			for (int32 Index = 0; bSuccess && Index < Plans.Num(); ++Index)
			{
				FJson Row = Rows[Index]->AsObject();
				bSuccess = CreateMontage(Plans[Index], Slot, Row);
			}
		}
		Report->SetArrayField(TEXT("montages"), Rows);
	}
	DescribeSkeletonSlot(Skeleton, Slot, SkeletonRow);
	Report->SetObjectField(TEXT("skeleton"), SkeletonRow);
	Report->SetBoolField(TEXT("success"), bSuccess);
	Report->SetBoolField(TEXT("write_requested"), bWrite);
	Report->SetStringField(TEXT("mode"), Args[0]);
	FString Output;
	FJsonSerializer::Serialize(Report.ToSharedRef(), TJsonWriterFactory<>::Create(&Output));
	UE_LOG(LogTemp, Display, TEXT("KevinCombatAssets: %s"), *Output);
}
FAutoConsoleCommand Command(TEXT("GGYGO.BuildKevinCombatAssets"),
	TEXT("Explicit animation audit/new-only build modes and prepare-slot, config, exact new packages for build or exact existing Skeleton for prepare-slot; never regenerates authored animation assets."),
	FConsoleCommandWithArgsDelegate::CreateStatic(&Build));
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Animation/AnimBlueprintGeneratedClass.h"
#include "EdGraphNode_Comment.h"
#include "Kismet2/CompilerResultsLog.h"
#include "Tests/AnimationAssetSafetyTestUtils.h"
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKevinAuthoredGraphSafetyTest, "GGYGO.Editor.Animation.KevinPreserveAuthoredGraph",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKevinAuthoredGraphSafetyTest::RunTest(const FString& Parameters)
{
    using namespace KevinCombatAssets;
    UPackage* Package = AnimationAssetSafetyTests::Package();
    UAnimSequence* Idle = AnimationAssetSafetyTests::Sequence(Package);
    if (!TestNotNull(TEXT("Valid animation sequence fixture"), Idle)) { return false; }
    TStrongObjectPtr<UAnimSequence> KeepIdle(Idle);
    TStrongObjectPtr<UAnimBlueprintFactory> Factory(NewObject<UAnimBlueprintFactory>());
    Factory->ParentClass = UGGYGOMontageGuardAnimInstance::StaticClass();
    Factory->TargetSkeleton = Idle->GetSkeleton();
    UAnimBlueprint* BP = Cast<UAnimBlueprint>(Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(), Package,
        FName(TEXT("ABP_KevinAuthoredGraphFixture")), RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
    if (!TestNotNull(TEXT("Real animation Blueprint factory fixture"), BP)) { return false; }
    TStrongObjectPtr<UAnimBlueprint> KeepBP(BP);
    UEdGraph* Graph = nullptr;
    for (UEdGraph* Candidate : BP->FunctionGraphs)
    {
        if (Candidate->GetFName() == TEXT("AnimGraph"))
        {
            if (!TestNull(TEXT("Factory has one AnimGraph"), Graph)) { return false; }
            Graph = Candidate;
        }
    }
    if (!TestNotNull(TEXT("Factory AnimGraph"), Graph)
        || !TestNotNull(TEXT("Factory AnimGraph schema"), Graph->GetSchema())) { return false; }
    const auto FactoryNodes = Graph->Nodes;
    for (UEdGraphNode* Node : FactoryNodes) { Graph->RemoveNode(Node); }
    auto* Player = AddNode<UAnimGraphNode_SequencePlayer>(Graph, -500);
    Player->Node.SetSequence(Idle); Player->Node.SetLoopAnimation(true);
    auto* Slot = AddNode<UAnimGraphNode_Slot>(Graph, -250);
    auto* Root = AddNode<UAnimGraphNode_Root>(Graph, 0);
    Slot->Node.SlotName = TEXT("DefaultSlot");
    Slot->NodeComment = TEXT("artist-owned topology");
    UEdGraphPin* PlayerOutput = Pin(Player, EGPD_Output);
    UEdGraphPin* SlotInput = Pin(Slot, EGPD_Input);
    UEdGraphPin* SlotOutput = Pin(Slot, EGPD_Output);
    UEdGraphPin* RootInput = Pin(Root, EGPD_Input);
    if (!TestNotNull(TEXT("StandBy pose output"), PlayerOutput) || !TestNotNull(TEXT("Slot pose input"), SlotInput)
        || !TestNotNull(TEXT("Slot pose output"), SlotOutput) || !TestNotNull(TEXT("Root pose input"), RootInput)
        || !TestTrue(TEXT("Real StandBy to Slot connection"), Graph->GetSchema()->TryCreateConnection(PlayerOutput, SlotInput))
        || !TestTrue(TEXT("Real Slot to Root connection"), Graph->GetSchema()->TryCreateConnection(SlotOutput, RootInput))) { return false; }
    auto* ExtraNode = AddNode<UEdGraphNode_Comment>(Graph, -750);
    ExtraNode->NodeComment = TEXT("artist-owned extra node");
    MarkOwned(BP);
    // Schema edits invalidate compilation. Only the native compiler establishes
    // the generated class and status consumed by the read-only production audit.
    FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
    FCompilerResultsLog CompileResults;
    FKismetEditorUtilities::CompileBlueprint(BP, EBlueprintCompileOptions::None, &CompileResults);
    if (!TestEqual(TEXT("Authored fixture native compile errors"), CompileResults.NumErrors, 0)
        || !TestTrue(TEXT("Authored fixture native compile status"), BP->Status == BS_UpToDate || BP->Status == BS_UpToDateWithWarnings))
    {
        return false;
    }
    auto* CompiledClass = Cast<UAnimBlueprintGeneratedClass>(BP->GeneratedClass);
    if (!TestNotNull(TEXT("Real compiled animation Blueprint class"), CompiledClass)
        || !TestTrue(TEXT("Generated class belongs to authored fixture"), CompiledClass->ClassGeneratedBy == BP)) { return false; }
    const auto* Defaults = Cast<UGGYGOMontageGuardAnimInstance>(CompiledClass->GetDefaultObject());
    if (!TestNotNull(TEXT("Compiled fixture Guard defaults"), Defaults)
        || !TestTrue(TEXT("Compiled fixture uses ordinary Slot mode"), Defaults->RequiredPoseCorrectionSlot.IsNone())
        || !TestTrue(TEXT("Compiled fixture has original StandBy Slot Root chain"), HasIdleSlotChain(BP, Idle, TEXT("DefaultSlot")))) { return false; }
    // Fixture construction may dirty its temporary package; the audit begins clean.
    Package->SetDirtyFlag(false);
    FJson Config = MakeShared<FJsonObject>(), Report = MakeShared<FJsonObject>();
    Config->SetStringField(TEXT("asset"), BP->GetPathName());
    Config->SetStringField(TEXT("idle_sequence"), Idle->GetPathName());
    Config->SetStringField(TEXT("mode"), TEXT("guard_standard_slot_idle_loop"));
    FPreparedAnimBP BPPlan;
    TestTrue(TEXT("Existing compiled Guard pose chain verified"), PrepareAnimBP(Config, Idle->GetSkeleton(), TEXT("DefaultSlot"), BPPlan, Report));
    TestEqual(TEXT("Authored nodes preserved"), Graph->Nodes.Num(), 4);
    TestTrue(TEXT("Extra authored node kept"), Graph->Nodes.Contains(ExtraNode));
    TestEqual(TEXT("Extra artist annotation kept"), ExtraNode->NodeComment, FString(TEXT("artist-owned extra node")));
    TestEqual(TEXT("Artist annotation kept"), Slot->NodeComment, FString(TEXT("artist-owned topology")));
    TestFalse(TEXT("Read-only verification does not dirty package"), Package->IsDirty());
    Pin(Root, EGPD_Input)->BreakAllPinLinks();
    Package->SetDirtyFlag(false);
    FPreparedAnimBP DisconnectedPlan;
    AddExpectedError(TEXT("compiled Guard/ordinary Slot/idle chain contract failed"), EAutomationExpectedErrorFlags::Contains, 1);
    TestFalse(TEXT("Disconnected same-named Slot cannot prove output contract"), PrepareAnimBP(Config, Idle->GetSkeleton(), TEXT("DefaultSlot"), DisconnectedPlan, Report));
    TestEqual(TEXT("Rejected graph is preserved"), Graph->Nodes.Num(), 4);
    TestFalse(TEXT("Rejected graph stays clean"), Package->IsDirty());
    UAnimMontage* Montage = NewObject<UAnimMontage>(Package);
    Montage->SetSkeleton(Idle->GetSkeleton());
    Montage->SlotAnimTracks.Reset();
    auto& Track = Montage->SlotAnimTracks.AddDefaulted_GetRef();
    Track.SlotName = TEXT("DefaultSlot");
    auto& Segment = Track.AnimTrack.AnimSegments.AddDefaulted_GetRef();
    Segment.SetAnimReference(Idle, true);
    Segment.StartPos = 0; Segment.AnimStartTime = 0; Segment.AnimEndTime = Idle->GetPlayLength();
    Segment.AnimPlayRate = 1; Segment.LoopingCount = 1;
    Montage->SetCompositeLength(Idle->GetPlayLength());
    Montage->CompositeSections.Reset(); Montage->AddAnimCompositeSection(TEXT("Main"), 0);
    Montage->CompositeSections[0].NextSectionName = NAME_None;
    Montage->Notifies.AddDefaulted_GetRef().NotifyName = TEXT("ArtistFootstep");
    Montage->BlendIn.SetBlendTime(.42f);
    Montage->bEnableAutoBlendOut = true;
    Montage->RateScale = 1.f;
    MarkOwned(Montage); Package->SetDirtyFlag(false);
    FJson Action = MakeShared<FJsonObject>(), Row = MakeShared<FJsonObject>();
    Action->SetStringField(TEXT("montage"), Montage->GetPathName());
    Action->SetStringField(TEXT("sequence_override"), Idle->GetPathName());
    Action->SetBoolField(TEXT("require_sequence_override"), false);
    Action->SetBoolField(TEXT("damage_enabled"), false);
    Action->SetStringField(TEXT("window_source"), TEXT("unavailable"));
    Action->SetArrayField(TEXT("hit_windows"), TArray<TSharedPtr<FJsonValue>>{});
    Action->SetNumberField(TEXT("blend_in_seconds"), .1); Action->SetNumberField(TEXT("blend_out_seconds"), .1);
    FPreparedMontage MontagePlan;
    TestTrue(TEXT("Existing montage validates without regeneration"), PrepareMontage(Action, Idle->GetSkeleton(), TEXT("DefaultSlot"), MontagePlan, Row));
    TestEqual(TEXT("Artist notify survives"), Montage->Notifies[0].NotifyName, FName(TEXT("ArtistFootstep")));
    TestEqual(TEXT("Artist blend survives"), Montage->BlendIn.GetBlendTime(), .42f);
    TestFalse(TEXT("Montage verification does not dirty package"), Package->IsDirty());
    return true;
}
#endif
