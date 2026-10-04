// Editor-only asset preparation. Action selection and runtime execution belong to BP/GAS.
#include "Animation/Notifies/GGYGOAnimNotifyState_GameplayEventWindow.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimInstance.h"
#include "Animation/AnimMontage.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "AnimationBlueprintLibrary.h"
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
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "Misc/FileHelper.h"
#include "Misc/PackageName.h"
#include "Misc/Paths.h"
#include "Rendering/SkeletalMeshModel.h"
#include "Rendering/SkeletalMeshLODModel.h"
#include "Serialization/JsonSerializer.h"
#include "System/GGYGOGameplayTags.h"
#include "UObject/MetaData.h"
#include "UObject/SavePackage.h"

namespace KevinCombatAssets
{
constexpr TCHAR OwnerKey[] = TEXT("GGYGO.AssetBuilder");
constexpr TCHAR OwnerValue[] = TEXT("KevinCombatAssets.v1");
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

bool BuildMontage(const FJson& Action, USkeleton* Skeleton, FName Slot, FJson& Row)
{
	const FString Path = Action->GetStringField(TEXT("montage"));
	Row->SetStringField(TEXT("asset"), Path);
	Row->SetStringField(TEXT("status"), TEXT("validation_failed"));
	FString SequencePath = Action->GetStringField(TEXT("sequence_override"));
	if (SequencePath.IsEmpty())
	{
		if (Action->GetBoolField(TEXT("require_sequence_override"))) return Fail(Path + TEXT(": required derived sequence missing"));
		SequencePath = Action->GetStringField(TEXT("source_sequence"));
	}
	UAnimSequence* Sequence = Load<UAnimSequence>(SequencePath);
	if (!Sequence || Sequence->GetSkeleton() != Skeleton || Sequence->GetPlayLength() <= 0.f || !FMath::IsNearlyEqual(Sequence->RateScale, 1.f))
		return Fail(Path + TEXT(": invalid sequence or skeleton"));
	if (Action->GetBoolField(TEXT("require_sequence_override")) && Sequence->bEnableRootMotion)
		return Fail(Path + TEXT(": derived sequence must not enable root motion"));
	const float Length = Sequence->GetPlayLength();
	const float BlendIn = Action->GetNumberField(TEXT("blend_in_seconds"));
	const float BlendOut = Action->GetNumberField(TEXT("blend_out_seconds"));
	if (!FMath::IsFinite(BlendIn) || !FMath::IsFinite(BlendOut) || BlendIn < 0 || BlendOut < 0)
		return Fail(Path + TEXT(": invalid blends"));
	const bool Damage = Action->GetBoolField(TEXT("damage_enabled"));
	const auto& Windows = Action->GetArrayField(TEXT("hit_windows"));
	if (Damage && (Action->GetStringField(TEXT("window_source")) != TEXT("manual_candidate") || Windows.IsEmpty()))
		return Fail(Path + TEXT(": damage needs explicitly annotated candidate windows"));
	if (!Damage && !Windows.IsEmpty()) return Fail(Path + TEXT(": disabled damage must have empty windows"));
	float PreviousEnd = -1.f;
	for (const auto& Value : Windows)
	{
		const FJson Window = Value->AsObject();
		if (!Window) return Fail(Path + TEXT(": invalid window object"));
		const float Start = Window->GetNumberField(TEXT("start_seconds"));
		const float End = Window->GetNumberField(TEXT("end_seconds"));
		if (!FMath::IsFinite(Start) || !FMath::IsFinite(End) || Start < 0 || Start <= PreviousEnd || End <= Start || End >= Length - FMath::Min(BlendOut, Length * .25f))
			return Fail(Path + TEXT(": windows must be ordered, separated, and before blend-out"));
		PreviousEnd = End;
	}
	UAnimMontage* Montage = Load<UAnimMontage>(Path);
	if (Montage && (!Owned(Montage) || Montage->GetPackage()->IsDirty()))
		return Fail(Path + TEXT(": refuses foreign or unsaved asset"));
	if (Montage)
	{
		// Existing assets are authored content. Metadata is provenance, not permission to overwrite.
		Row->SetStringField(TEXT("status"), TEXT("existing_preserved"));
		if (Montage->GetSkeleton() != Skeleton || Montage->SlotAnimTracks.Num() != 1
			|| Montage->SlotAnimTracks[0].SlotName != Slot
			|| Montage->SlotAnimTracks[0].AnimTrack.AnimSegments.Num() != 1
			|| Montage->CompositeSections.Num() != 1 || !Montage->CompositeSections[0].NextSectionName.IsNone())
			return Fail(Path + TEXT(": existing montage differs from required playback contract; preserved"));
		const FAnimSegment& Existing = Montage->SlotAnimTracks[0].AnimTrack.AnimSegments[0];
		if (Existing.GetAnimReference() != Sequence || Existing.LoopingCount != 1
			|| !FMath::IsNearlyEqual(Existing.AnimPlayRate, 1.f)
			|| !FMath::IsNearlyZero(Existing.StartPos) || !FMath::IsNearlyZero(Existing.AnimStartTime)
			|| !FMath::IsNearlyEqual(Existing.AnimEndTime, Length, .001f))
			return Fail(Path + TEXT(": existing sequence/segment differs; preserved"));
		TArray<const FAnimNotifyEvent*> HitEvents;
		for (const FAnimNotifyEvent& Event : Montage->Notifies)
			if (Event.NotifyStateClass && Event.NotifyStateClass->IsA<UGGYGOAnimNotifyState_GameplayEventWindow>()) HitEvents.Add(&Event);
		HitEvents.Sort([](const FAnimNotifyEvent& A, const FAnimNotifyEvent& B) { return A.GetTime() < B.GetTime(); });
		if (HitEvents.Num() != Windows.Num()) return Fail(Path + TEXT(": authored gameplay windows differ; preserved"));
		for (int32 Index = 0; Index < HitEvents.Num(); ++Index)
		{
			const auto Expected = Windows[Index]->AsObject();
			if (!FMath::IsNearlyEqual(HitEvents[Index]->GetTime(), static_cast<float>(Expected->GetNumberField(TEXT("start_seconds"))), .001f)
				|| !FMath::IsNearlyEqual(HitEvents[Index]->GetTime() + HitEvents[Index]->GetDuration(), static_cast<float>(Expected->GetNumberField(TEXT("end_seconds"))), .001f))
				return Fail(Path + TEXT(": authored gameplay window times differ; preserved"));
		}
		DescribeMontage(Montage, Slot, Action, Row);
		return true;
	}
	if (!Montage)
	{
		if (FPackageName::DoesPackageExist(Path)) return Fail(Path + TEXT(": existing package has wrong asset type"));
		UAnimMontageFactory* Factory = NewObject<UAnimMontageFactory>();
		Factory->SourceAnimation = Sequence;
		Montage = Cast<UAnimMontage>(Factory->FactoryCreateNew(UAnimMontage::StaticClass(), CreatePackage(*Path),
			FName(*FPackageName::GetLongPackageAssetName(Path)), RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
		if (!Montage) return Fail(Path + TEXT(": factory failed"));
		FAssetRegistryModule::AssetCreated(Montage);
		MarkOwned(Montage);
	}
	Row->SetStringField(TEXT("status"), TEXT("created"));
	Montage->Modify();
	Montage->SlotAnimTracks.Reset();
	FSlotAnimationTrack& Track = Montage->SlotAnimTracks.AddDefaulted_GetRef();
	Track.SlotName = Slot;
	FAnimSegment& Segment = Track.AnimTrack.AnimSegments.AddDefaulted_GetRef();
	Segment.SetAnimReference(Sequence, true);
	Segment.StartPos = 0.f;
	Segment.AnimStartTime = 0.f;
	Segment.AnimEndTime = Length;
	Segment.AnimPlayRate = 1.f;
	Segment.LoopingCount = 1;
	Segment.UpdateCachedPlayLength();
	Montage->SetCompositeLength(Length);
	Montage->CompositeSections.Reset();
	Montage->AddAnimCompositeSection(TEXT("Main"), 0.f);
	Montage->CompositeSections[0].NextSectionName = NAME_None;
	Montage->BlendIn.SetBlendTime(FMath::Min(BlendIn, Length * .25f));
	Montage->BlendOut.SetBlendTime(FMath::Min(BlendOut, Length * .25f));
	Montage->BlendOutTriggerTime = -1.f;
	Montage->bEnableAutoBlendOut = true;
	Montage->Notifies.Reset();
	const FName NotifyTrack(TEXT("ManualCandidateHitWindow"));
	if (!UAnimationBlueprintLibrary::IsValidAnimNotifyTrackName(Montage, NotifyTrack))
		UAnimationBlueprintLibrary::AddAnimationNotifyTrack(Montage, NotifyTrack, FLinearColor::Red);
	for (const auto& Value : Windows)
	{
		const auto Window = Value->AsObject();
		const float Start = Window->GetNumberField(TEXT("start_seconds"));
		auto* Notify = Cast<UGGYGOAnimNotifyState_GameplayEventWindow>(UAnimationBlueprintLibrary::AddAnimationNotifyStateEvent(
			Montage, NotifyTrack, Start, Window->GetNumberField(TEXT("end_seconds")) - Start,
			UGGYGOAnimNotifyState_GameplayEventWindow::StaticClass()));
		if (!Notify) return Fail(Path + TEXT(": notify creation failed"));
		Notify->InitializeEventTags(GGYGOGameplayTags::Event_Montage_HitWindowBegin, GGYGOGameplayTags::Event_Montage_HitWindowEnd);
	}
	Montage->GetPackage()->GetMetaData().SetValue(Montage, TEXT("WindowSource"), *Action->GetStringField(TEXT("window_source")));
	Montage->PostEditChange();
	DescribeMontage(Montage, Slot, Action, Row);
	return Save(Montage);
}

// Use imported UE geometry, never assume a source FBX axis survives import unchanged.
bool BuildSockets(USkeletalMesh* Mesh, const FJson& Config, FJson& Report)
{
	if (!Config->GetBoolField(TEXT("enabled"))) return true;
	if (Mesh->GetPackage()->IsDirty()) return Fail(TEXT("Mesh has unsaved changes; refusing socket save"));
	const FName Bone(*Config->GetStringField(TEXT("parent_bone")));
	const FName Material(*Config->GetStringField(TEXT("material_slot")));
	const FName Names[] = {FName(*Config->GetStringField(TEXT("start_socket"))), FName(*Config->GetStringField(TEXT("end_socket")))};
	if (Names[0].IsNone() || Names[1].IsNone() || Names[0] == Names[1]) return Fail(TEXT("Socket names must be distinct"));
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
	TArray<FVector> Points;
	for (const auto& Section : Imported->LODModels[0].Sections)
	{
		if (!Mesh->GetMaterials().IsValidIndex(Section.MaterialIndex) || Mesh->GetMaterials()[Section.MaterialIndex].MaterialSlotName != Material) continue;
		for (const auto& Vertex : Section.SoftVertices)
		{
			uint16 LocalBone = 0;
			if (!Vertex.GetRigidWeightBone(LocalBone) || !Section.BoneMap.IsValidIndex(LocalBone) || Section.BoneMap[LocalBone] != BoneIndex)
				return Fail(TEXT("Weapon section is not rigidly weighted to configured bone"));
			Points.Add(ComponentPose[BoneIndex].InverseTransformPosition(FVector(Vertex.Position)));
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
	if (Max - Min < 1) return Fail(TEXT("Weapon trace length is degenerate"));
	USkeletalMeshSocket* Sockets[2] = {};
	for (int32 I = 0; I < 2; ++I)
	{
		for (USkeletalMeshSocket* Socket : Mesh->GetMeshOnlySocketList()) if (Socket && Socket->SocketName == Names[I]) Sockets[I] = Socket;
		if (Sockets[I] && !Owned(Sockets[I])) return Fail(TEXT("Refusing foreign socket"));
		if (!Sockets[I] && Mesh->FindSocket(Names[I])) return Fail(TEXT("Socket name already exists on skeleton"));
	}
	if (Sockets[0] || Sockets[1])
	{
		Report->SetStringField(TEXT("status"), TEXT("existing_preserved"));
		if (!Sockets[0] || !Sockets[1] || Sockets[0]->BoneName != Bone || Sockets[1]->BoneName != Bone
			|| FVector::Distance(Sockets[0]->RelativeLocation, Sockets[1]->RelativeLocation) < 1.)
			return Fail(TEXT("Existing socket pair is incomplete/invalid; preserved, no automatic repair"));
		Report->SetStringField(TEXT("start_bone_local_cm"), Sockets[0]->RelativeLocation.ToString());
		Report->SetStringField(TEXT("end_bone_local_cm"), Sockets[1]->RelativeLocation.ToString());
		Report->SetNumberField(TEXT("segment_length_cm"), FVector::Distance(Sockets[0]->RelativeLocation, Sockets[1]->RelativeLocation));
		Report->SetStringField(TEXT("bone"), Bone.ToString());
		return true;
	}
	Report->SetStringField(TEXT("status"), TEXT("created"));
	Mesh->Modify();
	for (int32 I = 0; I < 2; ++I)
	{
		if (!Sockets[I])
		{
			Sockets[I] = NewObject<USkeletalMeshSocket>(Mesh, NAME_None, RF_Transactional);
			Mesh->GetMeshOnlySocketList().Add(Sockets[I]);
			MarkOwned(Sockets[I]);
		}
		Sockets[I]->SocketName = Names[I]; Sockets[I]->BoneName = Bone;
		Sockets[I]->RelativeLocation = Mean + Axis * (I == 0 ? Min : Max);
		Sockets[I]->RelativeRotation = FRotator::ZeroRotator;
		Sockets[I]->RelativeScale = FVector::OneVector;
		Report->SetStringField(I == 0 ? TEXT("start_bone_local_cm") : TEXT("end_bone_local_cm"), Sockets[I]->RelativeLocation.ToString());
	}
	Report->SetStringField(TEXT("bone"), Bone.ToString());
	Report->SetNumberField(TEXT("ue_section_vertices"), Points.Num());
	Report->SetNumberField(TEXT("segment_length_cm"), Max - Min);
	Report->SetNumberField(TEXT("geometry_max_radial_extent_cm"), Radius);
	Report->SetBoolField(TEXT("all_vertices_rigid_to_bone"), true);
	Mesh->PostEditChange();
	return Save(Mesh);
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
bool BuildAnimBP(const FJson& Config, USkeleton* Skeleton, USkeletalMesh* Mesh, FName Slot, FJson& Report)
{
	const FString Path = Config->GetStringField(TEXT("asset"));
	UAnimSequence* StandBy = Load<UAnimSequence>(Config->GetStringField(TEXT("idle_sequence")));
	if (!StandBy || StandBy->GetSkeleton() != Skeleton) return Fail(TEXT("Invalid idle animation"));
	UAnimBlueprint* BP = Load<UAnimBlueprint>(Path);
	if (BP && (!Owned(BP) || BP->GetPackage()->IsDirty())) return Fail(TEXT("Refusing foreign/unsaved AnimBP"));
	if (BP)
	{
		Report->SetStringField(TEXT("status"), TEXT("existing_preserved"));
		bool bHasSlot = false;
		for (const UEdGraph* Graph : BP->FunctionGraphs)
			for (const UEdGraphNode* Node : Graph->Nodes)
				if (const auto* SlotNode = Cast<UAnimGraphNode_Slot>(Node))
					bHasSlot |= SlotNode->Node.SlotName == Slot;
		if (BP->TargetSkeleton != Skeleton || !BP->GeneratedClass || !bHasSlot
			|| (BP->Status != BS_UpToDate && BP->Status != BS_UpToDateWithWarnings))
			return Fail(TEXT("Existing AnimBP skeleton/compiled status/Slot fails contract; graph preserved"));
		Report->SetStringField(TEXT("asset"), BP->GetPathName());
		Report->SetBoolField(TEXT("compiled_slot_contract"), true);
		return true;
	}
	if (!BP)
	{
		if (FPackageName::DoesPackageExist(Path)) return Fail(TEXT("AnimBP package already exists with wrong type"));
		UAnimBlueprintFactory* Factory = NewObject<UAnimBlueprintFactory>();
		Factory->ParentClass = UAnimInstance::StaticClass(); Factory->TargetSkeleton = Skeleton; Factory->PreviewSkeletalMesh = Mesh;
		BP = Cast<UAnimBlueprint>(Factory->FactoryCreateNew(UAnimBlueprint::StaticClass(), CreatePackage(*Path), FName(*FPackageName::GetLongPackageAssetName(Path)), RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
		if (!BP) return Fail(TEXT("AnimBP factory failed"));
		FAssetRegistryModule::AssetCreated(BP); MarkOwned(BP);
	}
	Report->SetStringField(TEXT("status"), TEXT("created"));
	UEdGraph* Graph = nullptr;
	for (UEdGraph* Candidate : BP->FunctionGraphs) if (Candidate->GetFName() == TEXT("AnimGraph")) Graph = Candidate;
	if (!Graph) return Fail(TEXT("AnimBP has no AnimGraph"));
	BP->Modify(); Graph->Modify();
	const auto OldNodes = Graph->Nodes;
	for (UEdGraphNode* Node : OldNodes) Graph->RemoveNode(Node);
	auto* Player = AddNode<UAnimGraphNode_SequencePlayer>(Graph, -500);
	Player->Node.SetSequence(StandBy); Player->Node.SetLoopAnimation(true);
	auto* SlotNode = AddNode<UAnimGraphNode_Slot>(Graph, -250); SlotNode->Node.SlotName = Slot;
	auto* Root = AddNode<UAnimGraphNode_Root>(Graph, 0);
	UEdGraphPin* Output = Pin(Player, EGPD_Output); UEdGraphPin* SlotInput = Pin(SlotNode, EGPD_Input);
	UEdGraphPin* SlotOutput = Pin(SlotNode, EGPD_Output); UEdGraphPin* RootInput = Pin(Root, EGPD_Input);
	if (!Output || !SlotInput || !SlotOutput || !RootInput || !Graph->GetSchema()->TryCreateConnection(Output, SlotInput) || !Graph->GetSchema()->TryCreateConnection(SlotOutput, RootInput))
		return Fail(TEXT("AnimBP pose links failed"));
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
	FKismetEditorUtilities::CompileBlueprint(BP);
	if (BP->Status == BS_Error || !BP->GeneratedClass) return Fail(TEXT("AnimBP compilation failed"));
	Report->SetStringField(TEXT("asset"), BP->GetPathName());
	Report->SetStringField(TEXT("idle_sequence"), StandBy->GetPathName());
	Report->SetBoolField(TEXT("compiled_pose_chain"), Graph->Nodes.Num() == 3 && Output->LinkedTo.Contains(SlotInput) && SlotOutput->LinkedTo.Contains(RootInput));
	return Save(BP);
}

void Build(const TArray<FString>& Args)
{
	const FString Filename = Args.IsEmpty() ? FPaths::ProjectDir() / TEXT("AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Montage_Config.json") : Args[0];
	FString Text; FJson Config;
	if (!FFileHelper::LoadFileToString(Text, *Filename) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Config) || !Config) { Fail(TEXT("Cannot read config")); return; }
	USkeletalMesh* Mesh = Load<USkeletalMesh>(Config->GetStringField(TEXT("mesh")));
	USkeleton* Skeleton = Load<USkeleton>(Config->GetStringField(TEXT("skeleton")));
	const FName Slot(*Config->GetStringField(TEXT("slot")));
	if (!Mesh || !Skeleton || Mesh->GetSkeleton() != Skeleton || Slot.IsNone()) { Fail(TEXT("Invalid mesh/skeleton/slot")); return; }
	if (!Skeleton->ContainsSlotName(Slot))
	{
		if (Skeleton->GetPackage()->IsDirty()) { Fail(TEXT("Skeleton has unsaved changes")); return; }
		Skeleton->Modify(); Skeleton->RegisterSlotNode(Slot);
		if (!Save(Skeleton)) return;
	}
	FJson Report = MakeShared<FJsonObject>(), SocketReport = MakeShared<FJsonObject>(), BPReport = MakeShared<FJsonObject>();
	bool Success = BuildSockets(Mesh, Config->GetObjectField(TEXT("socket_config")), SocketReport);
	Success = BuildAnimBP(Config->GetObjectField(TEXT("anim_blueprint")), Skeleton, Mesh, Slot, BPReport) && Success;
	TArray<TSharedPtr<FJsonValue>> Rows;
	for (const auto& Value : Config->GetArrayField(TEXT("actions")))
	{
		const FJson Action = Value->AsObject();
		if (!Action || !Action->GetBoolField(TEXT("enabled"))) continue;
		FJson Row = MakeShared<FJsonObject>();
		const bool Saved = BuildMontage(Action, Skeleton, Slot, Row);
		Row->SetBoolField(TEXT("success"), Saved);
		Row->SetBoolField(TEXT("saved_this_run"), Saved && Row->GetStringField(TEXT("status")) == TEXT("created")); Success = Saved && Success;
		Rows.Add(MakeShared<FJsonValueObject>(Row));
	}
	Report->SetBoolField(TEXT("success"), Success);
	Report->SetObjectField(TEXT("sockets"), SocketReport); Report->SetObjectField(TEXT("anim_blueprint"), BPReport);
	Report->SetArrayField(TEXT("montages"), Rows);
	FString Output; FJsonSerializer::Serialize(Report.ToSharedRef(), TJsonWriterFactory<>::Create(&Output));
	FFileHelper::SaveStringToFile(Output, *(FPaths::ProjectSavedDir() / TEXT("Codex/kevin_combat_asset_report.json")));
	UE_LOG(LogTemp, Display, TEXT("KevinCombatAssets: success=%d, montages=%d; see Saved/Codex/kevin_combat_asset_report.json"), Success, Rows.Num());
}
FAutoConsoleCommand Command(TEXT("GGYGO.BuildKevinCombatAssets"), TEXT("Build config-owned Kevin animation assets; optional config filename."), FConsoleCommandWithArgsDelegate::CreateStatic(&Build));
}

#if WITH_DEV_AUTOMATION_TESTS
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
    UAnimBlueprint* BP = NewObject<UAnimBlueprint>(Package);
    BP->TargetSkeleton = Idle->GetSkeleton();
    BP->GeneratedClass = UAnimInstance::StaticClass(); // read-only contract fixture; no compile/save
    BP->Status = BS_UpToDate;
    UEdGraph* Graph = NewObject<UEdGraph>(BP);
    BP->FunctionGraphs.Add(Graph);
    auto* Slot = NewObject<UAnimGraphNode_Slot>(Graph);
    Slot->Node.SlotName = TEXT("DefaultSlot");
    Slot->NodeComment = TEXT("artist-owned topology");
    Graph->Nodes.Add(Slot);
    auto* ExtraNode = NewObject<UEdGraphNode>(Graph);
    Graph->Nodes.Add(ExtraNode);
    MarkOwned(BP);
    Package->SetDirtyFlag(false);
    FJson Config = MakeShared<FJsonObject>(), Report = MakeShared<FJsonObject>();
    Config->SetStringField(TEXT("asset"), BP->GetPathName());
    Config->SetStringField(TEXT("idle_sequence"), Idle->GetPathName());
    TestTrue(TEXT("Existing compiled Slot contract verified"), BuildAnimBP(Config, Idle->GetSkeleton(), nullptr, TEXT("DefaultSlot"), Report));
    TestEqual(TEXT("Authored nodes preserved"), Graph->Nodes.Num(), 2);
    TestTrue(TEXT("Extra authored node kept"), Graph->Nodes.Contains(ExtraNode));
    TestEqual(TEXT("Artist annotation kept"), Slot->NodeComment, FString(TEXT("artist-owned topology")));
    TestFalse(TEXT("Read-only verification does not dirty package"), Package->IsDirty());
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
    MarkOwned(Montage); Package->SetDirtyFlag(false);
    FJson Action = MakeShared<FJsonObject>(), Row = MakeShared<FJsonObject>();
    Action->SetStringField(TEXT("montage"), Montage->GetPathName());
    Action->SetStringField(TEXT("sequence_override"), Idle->GetPathName());
    Action->SetBoolField(TEXT("require_sequence_override"), false);
    Action->SetBoolField(TEXT("damage_enabled"), false);
    Action->SetStringField(TEXT("window_source"), TEXT("unavailable"));
    Action->SetArrayField(TEXT("hit_windows"), TArray<TSharedPtr<FJsonValue>>{});
    Action->SetNumberField(TEXT("blend_in_seconds"), .1); Action->SetNumberField(TEXT("blend_out_seconds"), .1);
    TestTrue(TEXT("Existing montage validates without regeneration"), BuildMontage(Action, Idle->GetSkeleton(), TEXT("DefaultSlot"), Row));
    TestEqual(TEXT("Artist notify survives"), Montage->Notifies[0].NotifyName, FName(TEXT("ArtistFootstep")));
    TestEqual(TEXT("Artist blend survives"), Montage->BlendIn.GetBlendTime(), .42f);
    TestFalse(TEXT("Montage verification does not dirty package"), Package->IsDirty());
    return true;
}
#endif
