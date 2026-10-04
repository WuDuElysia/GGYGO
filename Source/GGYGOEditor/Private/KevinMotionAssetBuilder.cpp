/** Production tool only: original sequences are read-only; paired derived poses and curves share one trajectory. */
#include "Character/Data/GGYGOActionMotionProfile.h"
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Curves/CurveVector.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/MetaData.h"
#include "UObject/SavePackage.h"

namespace GGYGOKevinMotion
{
	constexpr TCHAR Base[] = TEXT("/Game/Characters/Boss/Kevin/DemonBattle");
	constexpr TCHAR OwnerKey[] = TEXT("GGYGO.MotionBuilder");
	constexpr TCHAR OwnerValue[] = TEXT("KevinGroundMotion.v1");
	const FName MotionBone(TEXT("Bip001"));

	struct FTrack
	{
		TArray<FTransform> Keys;
		FTransform Reference;
		FTransform At(int32 Frame) const { return Keys.IsEmpty() ? Reference : Keys[FMath::Min(Frame, Keys.Num() - 1)]; }
	};

	TArray<TSharedPtr<FJsonValue>> VectorJson(const FVector& V)
	{
		return { MakeShared<FJsonValueNumber>(V.X), MakeShared<FJsonValueNumber>(V.Y), MakeShared<FJsonValueNumber>(V.Z) };
	}

	FVector JsonVector(const TArray<TSharedPtr<FJsonValue>>& V)
	{
		return FVector(V[0]->AsNumber(), V[1]->AsNumber(), V[2]->AsNumber());
	}

	FQuat JsonQuat(const TArray<TSharedPtr<FJsonValue>>& V)
	{
		return FQuat(V[0]->AsNumber(), V[1]->AsNumber(), V[2]->AsNumber(), V[3]->AsNumber()).GetNormalized();
	}

	FTransform ComponentAt(const TArray<FTrack>& Tracks, const FReferenceSkeleton& Ref, int32 Bone, int32 Frame)
	{
		FTransform Value = FTransform::Identity;
		while (Bone != INDEX_NONE)
		{
			Value = Value * Tracks[Bone].At(Frame);
			Bone = Ref.GetParentIndex(Bone);
		}
		return Value;
	}

	/** An inferred orthogonal signed axis permutation, validated against every imported frame. */
	struct FAxisMap
	{
		int32 Axis[3] = {0, 1, 2};
		FVector Sign = FVector::OneVector;
		FVector Map(const FVector& V) const { return FVector(V[Axis[0]], V[Axis[1]], V[Axis[2]]) * Sign; }
		FQuat MapRotation(const FQuat& Q) const
		{
			const double Determinant = FVector::DotProduct(FVector::CrossProduct(Map(FVector::ForwardVector), Map(FVector::RightVector)), Map(FVector::UpVector));
			const FVector Axial = Map(FVector(Q.X, Q.Y, Q.Z)) * Determinant;
			return FQuat(Axial.X, Axial.Y, Axial.Z, Q.W).GetNormalized();
		}
	};

	// Existing content is only inspected. A builder tag never authorizes replacing edits.
	bool CanInspectExisting(UObject* Object, UClass* ExpectedClass)
	{
		return Object && Object->IsA(ExpectedClass) && !Object->GetPackage()->IsDirty()
			&& Object->GetPackage()->GetMetaData().GetValue(Object, OwnerKey) == OwnerValue;
	}

	template<typename T> bool InspectOutput(const FString& Path, T*& Existing)
	{
		UObject* Object = LoadObject<UObject>(nullptr, *(Path + TEXT(".") + FPackageName::GetLongPackageAssetName(Path)));
		Existing = Cast<T>(Object);
		if (!Object) return !FPackageName::DoesPackageExist(Path);
		return FPackageName::DoesPackageExist(Path) && CanInspectExisting(Object, T::StaticClass());
	}

	template<typename T> T* CreateAsset(const FString& Path)
	{
		T* Asset = NewObject<T>(CreatePackage(*Path), *FPackageName::GetLongPackageAssetName(Path), RF_Public | RF_Standalone | RF_Transactional);
		FAssetRegistryModule::AssetCreated(Asset);
		return Asset;
	}

	bool Save(UObject* Asset)
	{
		UPackage* Package = Asset->GetOutermost();
		Package->GetMetaData().SetValue(Asset, OwnerKey, OwnerValue);
		Asset->MarkPackageDirty();
		FSavePackageArgs Args;
		Args.TopLevelFlags = RF_Public | RF_Standalone;
		Args.SaveFlags = SAVE_NoError;
		return UPackage::SavePackage(Package, Asset,
			*FPackageName::LongPackageNameToFilename(Package->GetName(), FPackageName::GetAssetPackageExtension()), Args);
	}

	bool Build(const TSharedPtr<FJsonObject>& Clip, bool bWrite, TSharedRef<FJsonObject> Report)
	{
		const FString Suffix = Clip->GetStringField(TEXT("suffix"));
		Report->SetStringField(TEXT("suffix"), Suffix);
		const auto Fail = [&Report](const FString& Reason)
		{
			Report->SetStringField(TEXT("error"), Reason);
			UE_LOG(LogTemp, Error, TEXT("[KevinMotion] %s"), *Reason);
			return false;
		};
		if (Suffix != TEXT("01") && Suffix != TEXT("02")) return Fail(TEXT("Only initial Ice01/02 are configured."));
		UAnimSequence* Source = LoadObject<UAnimSequence>(nullptr, *Clip->GetStringField(TEXT("source_sequence")));
		if (!Source || !Source->GetSkeleton() || !Source->GetDataModel() || Source->GetPackage()->IsDirty()) return Fail(TEXT("Missing source animation/model/skeleton."));
		const IAnimationDataModel* Model = Source->GetDataModel();
		const FReferenceSkeleton& Ref = Source->GetSkeleton()->GetReferenceSkeleton();
		const int32 Bone = Ref.FindBoneIndex(MotionBone);
		const int32 Count = Model->GetNumberOfKeys();
		const float Duration = Source->GetPlayLength();
		const auto& Samples = Clip->GetArrayField(TEXT("samples"));
		if (Bone == INDEX_NONE || Count < 2 || Samples.Num() != Count || !FMath::IsNearlyEqual(Source->RateScale, 1.f)
			|| !FMath::IsNearlyEqual(Duration, static_cast<float>(Clip->GetNumberField(TEXT("duration"))), 0.001f))
			return Fail(TEXT("Source key grid, duration, RateScale or motion bone differs from audited FBX."));

		TArray<FTrack> Tracks;
		Tracks.SetNum(Ref.GetNum());
		for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
		{
			Tracks[Index].Reference = Ref.GetRefBonePose()[Index];
			if (Model->IsValidBoneTrackName(Ref.GetBoneName(Index))) Model->GetBoneTrackTransforms(Ref.GetBoneName(Index), Tracks[Index].Keys);
		}
		TArray<FTransform> Original;
		TArray<FVector> FbxPositions;
		TArray<FQuat> FbxRotations;
		for (int32 Frame = 0; Frame < Count; ++Frame)
		{
			const TSharedPtr<FJsonObject> Sample = Samples[Frame]->AsObject();
			const double Time = Model->GetFrameRate().AsSeconds(FFrameTime(Frame));
			if (FMath::Abs(Time - Sample->GetNumberField(TEXT("time"))) > 0.001)
				return Fail(TEXT("UE / FBX sample times do not match."));
			Original.Add(ComponentAt(Tracks, Ref, Bone, Frame));
			FbxPositions.Add(JsonVector(Sample->GetArrayField(TEXT("fbx_translation_cm"))));
			FbxRotations.Add(JsonQuat(Sample->GetArrayField(TEXT("fbx_rotation_xyzw"))));
		}

		FAxisMap Best;
		double BestError = TNumericLimits<double>::Max();
		const int32 Permutations[6][3] = {{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}};
		for (const auto& Permutation : Permutations)
		{
			for (int32 Bits = 0; Bits < 8; ++Bits)
			{
				FAxisMap Candidate;
				for (int32 Axis = 0; Axis < 3; ++Axis) Candidate.Axis[Axis] = Permutation[Axis];
				Candidate.Sign = FVector(Bits & 1 ? -1 : 1, Bits & 2 ? -1 : 1, Bits & 4 ? -1 : 1);
				double Error = 0.;
				for (int32 Frame = 0; Frame < Count; ++Frame)
					Error = FMath::Max(Error, FVector::Distance(Original[Frame].GetTranslation() - Original[0].GetTranslation(), Candidate.Map(FbxPositions[Frame] - FbxPositions[0])));
				if (Error < BestError) { Best = Candidate; BestError = Error; }
			}
		}
		double RotationError = 0.;
		for (int32 Frame = 0; Frame < Count; ++Frame)
		{
			const FQuat UEDelta = Original[Frame].GetRotation() * Original[0].GetRotation().Inverse();
			const FQuat FbxDelta = Best.MapRotation(FbxRotations[Frame] * FbxRotations[0].Inverse());
			RotationError = FMath::Max(RotationError, FMath::RadiansToDegrees(UEDelta.AngularDistance(FbxDelta)));
		}
		Report->SetNumberField(TEXT("fbx_to_ue_translation_error_cm"), BestError);
		Report->SetNumberField(TEXT("fbx_to_ue_relative_rotation_error_deg"), RotationError);
		Report->SetArrayField(TEXT("axis_permutation"), {MakeShared<FJsonValueNumber>(Best.Axis[0]), MakeShared<FJsonValueNumber>(Best.Axis[1]), MakeShared<FJsonValueNumber>(Best.Axis[2])});
		Report->SetArrayField(TEXT("axis_sign"), VectorJson(Best.Sign));
		Report->SetArrayField(TEXT("ue_first_position_cm"), VectorJson(Original[0].GetTranslation()));
		Report->SetArrayField(TEXT("fbx_first_position_cm"), VectorJson(FbxPositions[0]));
		Report->SetStringField(TEXT("source_fbx_sha256"), Clip->GetStringField(TEXT("fbx_sha256")));
		if (BestError > 0.25 || RotationError > 0.25 || Best.Axis[2] != 1)
			return Fail(TEXT("Imported pose does not match audited FBX axis/units/rotation; no assets written."));

		TArray<FVector> Positions, Scales, Displacements;
		TArray<FQuat> Rotations;
		double Residual = 0., ReconstructionError = 0.;
		const int32 Parent = Ref.GetParentIndex(Bone);
		for (int32 Frame = 0; Frame < Count; ++Frame)
		{
			FVector Delta = Original[Frame].GetTranslation() - Original[0].GetTranslation();
			Delta.Z = 0.;
			FTransform InPlace = Original[Frame];
			InPlace.AddToTranslation(-Delta);
			const FTransform ParentTransform = ComponentAt(Tracks, Ref, Parent, Frame);
			const FTransform Local = InPlace.GetRelativeTransform(ParentTransform);
			Positions.Add(Local.GetTranslation());
			Rotations.Add(Local.GetRotation());
			Scales.Add(Local.GetScale3D());
			Displacements.Add(Delta);
			const FTransform Rebuilt = Local * ParentTransform;
			Residual = FMath::Max(Residual, FVector::Dist2D(Rebuilt.GetTranslation(), Original[0].GetTranslation()));
			ReconstructionError = FMath::Max(ReconstructionError, FVector::Distance(Rebuilt.GetTranslation() + Delta, Original[Frame].GetTranslation()));
		}
		Report->SetNumberField(TEXT("in_place_residual_cm"), Residual);
		Report->SetNumberField(TEXT("reconstruction_error_cm"), ReconstructionError);
		Report->SetNumberField(TEXT("duration"), Duration);
		Report->SetNumberField(TEXT("keys"), Count);
		Report->SetArrayField(TEXT("last_displacement_cm"), VectorJson(Displacements.Last()));
		if (Residual > 0.001 || ReconstructionError > 0.001) return Fail(TEXT("Pose decomposition residual exceeds tolerance."));

		const FString Stem = TEXT("Kevin_Ice_Attack_") + Suffix;
		const FString SequencePath = FString(Base) + TEXT("/Animation/Derived/AS_") + Stem + TEXT("_InPlace");
		const FString CurvePath = FString(Base) + TEXT("/Motion/CV_") + Stem + TEXT("_Translation");
		const FString ProfilePath = FString(Base) + TEXT("/Motion/DA_") + Stem + TEXT("_Motion");
		Report->SetStringField(TEXT("sequence"), SequencePath);
		Report->SetStringField(TEXT("curve"), CurvePath);
		Report->SetStringField(TEXT("profile"), ProfilePath);
		UAnimSequence* Derived = nullptr;
		UCurveVector* Curve = nullptr;
		UGGYGOActionMotionProfile* Profile = nullptr;
		if (!InspectOutput(SequencePath, Derived) || !InspectOutput(CurvePath, Curve) || !InspectOutput(ProfilePath, Profile))
			return Fail(TEXT("Output type/owner/dirty-package check failed; all existing assets preserved."));
		// Compare the full generated pose/curve baseline without writing. No stored stamp
		// can establish that an asset has not been hand-edited since the stamp was saved.
		if (Derived)
		{
			const IAnimationDataModel* ExistingModel = Derived->GetDataModel();
			if (!ExistingModel || Derived->GetSkeleton() != Source->GetSkeleton() || Derived->bEnableRootMotion
				|| Derived->bForceRootLock || !FMath::IsNearlyEqual(Derived->RateScale, 1.f)
				|| ExistingModel->GetNumberOfKeys() != Count || !FMath::IsNearlyEqual(Derived->GetPlayLength(), Duration, .001f)
				|| ExistingModel->GetNumBoneTracks() != Model->GetNumBoneTracks())
				return Fail(TEXT("Existing derived sequence differs from generated baseline; preserved."));
			TArray<FName> TrackNames;
			Model->GetBoneTrackNames(TrackNames);
			for (FName Name : TrackNames)
			{
				TArray<FTransform> Actual;
				if (!ExistingModel->IsValidBoneTrackName(Name)) return Fail(TEXT("Existing derived sequence missing track; preserved."));
				ExistingModel->GetBoneTrackTransforms(Name, Actual);
				const int32 TrackIndex = Ref.FindBoneIndex(Name);
				if (TrackIndex == INDEX_NONE || Actual.Num() != Count) return Fail(TEXT("Existing track grid differs; preserved."));
				for (int32 Frame = 0; Frame < Count; ++Frame)
				{
					const FTransform Expected = Name == MotionBone ? FTransform(Rotations[Frame], Positions[Frame], Scales[Frame]) : Tracks[TrackIndex].At(Frame);
					if (!Actual[Frame].Equals(Expected, .001)) return Fail(TEXT("Existing pose differs from generated baseline; preserved."));
				}
			}
		}
		if (Curve)
		{
			for (int32 Axis = 0; Axis < 3; ++Axis)
			{
				const auto& Keys = Curve->FloatCurves[Axis].GetConstRefOfKeys();
				if (Keys.Num() != Count) return Fail(TEXT("Existing curve key count differs; preserved."));
				for (int32 Frame = 0; Frame < Count; ++Frame)
				{
					const float Time = Frame == Count - 1 ? Duration : static_cast<float>(Model->GetFrameRate().AsSeconds(FFrameTime(Frame)));
					if (!FMath::IsNearlyEqual(Keys[Frame].Time, Time, .0001f) || !FMath::IsNearlyEqual(Keys[Frame].Value, static_cast<float>(Displacements[Frame][Axis]), .001f) || Keys[Frame].InterpMode != RCIM_Linear)
						return Fail(TEXT("Existing curve differs from generated baseline; preserved."));
				}
			}
		}
		FString ValidationError;
		if (Profile && (!Curve || Profile->TranslationCurve != Curve || !FMath::IsNearlyEqual(Profile->Duration, Duration, .001f) || !Profile->ValidateMotion(ValidationError)))
			return Fail(TEXT("Existing profile differs from trajectory contract; preserved. ") + ValidationError);
		Report->SetBoolField(TEXT("saved_this_run"), false);
		Report->SetStringField(TEXT("status"), TEXT("existing_preserved_or_missing"));
		if (!bWrite) return true;
		const bool bCreateDerived = !Derived, bCreateCurve = !Curve, bCreateProfile = !Profile;
		if (bCreateDerived)
		{
			Derived = DuplicateObject<UAnimSequence>(Source, CreatePackage(*SequencePath), *FPackageName::GetLongPackageAssetName(SequencePath));
			if (!Derived) return Fail(TEXT("Unable to duplicate source."));
			FAssetRegistryModule::AssetCreated(Derived);
			IAnimationDataController& Controller = Derived->GetController();
			Controller.OpenBracket(FText::FromString(TEXT("Bake ground action in place")), false);
			const bool bKeysWritten = Controller.SetBoneTrackKeys(MotionBone, Positions, Rotations, Scales, false);
			Controller.CloseBracket(false);
			if (!bKeysWritten) return Fail(TEXT("Unable to write derived bone keys."));
			Derived->bEnableRootMotion = false; Derived->bForceRootLock = false; Derived->RateScale = 1.f;
		}
		if (bCreateCurve)
		{
			Curve = CreateAsset<UCurveVector>(CurvePath);
			for (int32 Frame = 0; Frame < Count; ++Frame)
			{
				const float Time = Frame == Count - 1 ? Duration : static_cast<float>(Model->GetFrameRate().AsSeconds(FFrameTime(Frame)));
				for (int32 Axis = 0; Axis < 3; ++Axis)
				{
					const FKeyHandle Key = Curve->FloatCurves[Axis].AddKey(Time, Displacements[Frame][Axis]);
					Curve->FloatCurves[Axis].SetKeyInterpMode(Key, RCIM_Linear);
				}
			}
		}
		if (bCreateProfile)
		{
			Profile = CreateAsset<UGGYGOActionMotionProfile>(ProfilePath);
			Profile->TranslationCurve = Curve; Profile->Duration = Duration;
		}
		if (!Profile->ValidateMotion(ValidationError)) return Fail(ValidationError);
		// Save only assets created by this invocation, never incidental edits on loaded ones.
		if ((bCreateDerived && !Save(Derived)) || (bCreateCurve && !Save(Curve)) || (bCreateProfile && !Save(Profile)))
			return Fail(TEXT("Could not save all new assets; inspect partial output before retry."));
		Report->SetBoolField(TEXT("saved_this_run"), bCreateDerived || bCreateCurve || bCreateProfile);
		Report->SetStringField(TEXT("status"), bCreateDerived || bCreateCurve || bCreateProfile ? TEXT("created_missing_preserved_existing") : TEXT("existing_verified_preserved"));
		return true;
	}

	void Run(const TArray<FString>& Args)
	{
		const bool bWrite = Args.Num() > 0 && Args[0] == TEXT("build");
		const FString Input = Args.Num() > 1 ? Args[1] : FPaths::ProjectSavedDir() / TEXT("Codex/kevin_motion_source.json");
		FString Text;
		TSharedPtr<FJsonObject> Document;
		if (!FFileHelper::LoadFileToString(Text, *Input) || !FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Document)
			|| !Document.IsValid() || Document->GetIntegerField(TEXT("schema")) != 1)
		{
			UE_LOG(LogTemp, Error, TEXT("[KevinMotion] Run audit_kevin_action_motion.py first; unreadable input %s"), *Input);
			return;
		}
		TSharedRef<FJsonObject> Report = MakeShared<FJsonObject>();
		TArray<TSharedPtr<FJsonValue>> Results;
		bool bSuccess = true;
		for (const auto& Value : Document->GetArrayField(TEXT("clips")))
		{
			TSharedRef<FJsonObject> Row = MakeShared<FJsonObject>();
			const bool bClipSuccess = Build(Value->AsObject(), bWrite, Row);
			Row->SetBoolField(TEXT("success"), bClipSuccess);
			bSuccess &= bClipSuccess;
			Results.Add(MakeShared<FJsonValueObject>(Row));
		}
		Report->SetBoolField(TEXT("success"), bSuccess);
		Report->SetBoolField(TEXT("write_requested"), bWrite);
		Report->SetArrayField(TEXT("clips"), Results);
		FString Output;
		FJsonSerializer::Serialize(Report, TJsonWriterFactory<>::Create(&Output));
		FFileHelper::SaveStringToFile(Output, *(FPaths::ProjectSavedDir() / TEXT("Codex/kevin_motion_build_report.json")));
		UE_LOG(LogTemp, Display, TEXT("[KevinMotion] %s %s. See Saved/Codex/kevin_motion_build_report.json"), bWrite ? TEXT("Build") : TEXT("Audit"), bSuccess ? TEXT("passed") : TEXT("failed"));
	}

	FAutoConsoleCommand Command(TEXT("GGYGO.BuildKevinMotionAssets"),
		TEXT("GGYGO.BuildKevinMotionAssets [audit|build] [source-audit-json]. Defaults to read-only audit."),
		FConsoleCommandWithArgsDelegate::CreateStatic(&Run));
}

#if WITH_DEV_AUTOMATION_TESTS
#include "Tests/AnimationAssetSafetyTestUtils.h"
#include "Misc/AutomationTest.h"
IMPLEMENT_SIMPLE_AUTOMATION_TEST(FKevinMotionOutputSafetyTest, "GGYGO.Editor.Animation.KevinMotionOutputGuard",
    EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)
bool FKevinMotionOutputSafetyTest::RunTest(const FString& Parameters)
{
    using namespace GGYGOKevinMotion;
    UPackage* Package = AnimationAssetSafetyTests::Package();
    // InspectOutput expects a package asset path; use the package's short name.
    UCurveVector* Asset = NewObject<UCurveVector>(Package, *FPackageName::GetLongPackageAssetName(Package->GetName()));
    Package->GetMetaData().SetValue(Asset, OwnerKey, OwnerValue);
    Package->SetDirtyFlag(false);
    TestTrue(TEXT("Clean owned output passes memory guard"), CanInspectExisting(Asset, UCurveVector::StaticClass()));
    TestFalse(TEXT("Owner marker cannot authorize wrong asset type"), CanInspectExisting(Asset, UAnimSequence::StaticClass()));
    UCurveVector* Found = nullptr;
    TestFalse(TEXT("Unpersisted in-memory output is not a verified asset"), InspectOutput(Package->GetName(), Found));
    Package->SetDirtyFlag(true);
    TestFalse(TEXT("Unsaved edits reject all writes"), CanInspectExisting(Asset, UCurveVector::StaticClass()));
    TestTrue(TEXT("Inspection retains dirty state"), Package->IsDirty());
    return true;
}
#endif
