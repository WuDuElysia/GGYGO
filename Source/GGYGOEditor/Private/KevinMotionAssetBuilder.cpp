/** @file KevinMotionAssetBuilder.cpp @brief Source-verified, new-only paired in-place poses and actor-local XYZ montage curves. */
#include "Animation/AnimSequence.h"
#include "Animation/Skeleton.h"
#include "Animation/AnimData/IAnimationDataModel.h"
#include "Animation/AnimData/IAnimationDataController.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "Dom/JsonObject.h"
#include "HAL/IConsoleManager.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/PackageName.h"
#include "Serialization/JsonReader.h"
#include "Serialization/JsonSerializer.h"
#include "UObject/MetaData.h"
#include "UObject/SavePackage.h"
#include "UObject/StrongObjectPtr.h"

namespace GGYGOKevinMotion
{
	constexpr TCHAR Base[] = TEXT("/Game/Characters/Boss/Kevin/DemonBattle/Animation/");
	constexpr TCHAR OwnerKey[] = TEXT("GGYGO.MotionBuilder");
	constexpr TCHAR OwnerValue[] = TEXT("KevinMontageXYZ.v2");
	constexpr TCHAR CurveSpace[] = TEXT("ActorLocalCmXYZ.v1");
	constexpr TCHAR MontageConfig[] = TEXT("AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Montage_Config.json");
	constexpr TCHAR BasisConfig[] = TEXT("AAADocs/Assets/BH3/KevinDemonBattle/BH3_Kevin_Combat_Wiring_Config.json");
	const FName CurveNames[] = {TEXT("RootMotion_PosX"), TEXT("RootMotion_PosY"), TEXT("RootMotion_PosZ")};
	using FJson = TSharedPtr<FJsonObject>;

	bool Fail(const FString& Context, const FString& Reason)
	{
		UE_LOG(LogTemp, Error, TEXT("[KevinMotion] %s: %s"), *Context, *Reason);
		return false;
	}

	TArray<TSharedPtr<FJsonValue>> VectorJson(const FVector& V)
	{
		return {MakeShared<FJsonValueNumber>(V.X), MakeShared<FJsonValueNumber>(V.Y), MakeShared<FJsonValueNumber>(V.Z)};
	}

	bool ReadNumbers(const FJson& Object, const TCHAR* Key, int32 Count, double* Out)
	{
		const TArray<TSharedPtr<FJsonValue>>* Values = nullptr;
		if (!Object || !Object->TryGetArrayField(Key, Values) || Values->Num() != Count) return false;
		for (int32 Index = 0; Index < Count; ++Index)
			if (!(*Values)[Index]->TryGetNumber(Out[Index]) || !FMath::IsFinite(Out[Index])) return false;
		return true;
	}

	struct FBasis
	{
		FQuat Rotation;
		FVector Scale;
	};

	bool ReadBasis(const FJson& Object, FBasis& Basis)
	{
		bool bConfirmed = false;
		double Q[4], S[3];
		if (!Object || !Object->TryGetBoolField(TEXT("confirmed"), bConfirmed) || !bConfirmed
			|| !ReadNumbers(Object, TEXT("mesh_relative_rotation_xyzw"), 4, Q)
			|| !ReadNumbers(Object, TEXT("mesh_relative_scale"), 3, S))
			return Fail(TEXT("motion_asset_basis"), TEXT("confirmed quaternion/scale required; provisional assembly is not a motion basis"));
		Basis.Rotation = FQuat(Q[0], Q[1], Q[2], Q[3]);
		Basis.Scale = FVector(S[0], S[1], S[2]);
		if (!FMath::IsNearlyEqual(Basis.Rotation.SizeSquared(), 1., .00001) || Basis.Scale.X <= 0 || Basis.Scale.Y <= 0 || Basis.Scale.Z <= 0
			|| !FMath::IsNearlyEqual(Basis.Scale.X, Basis.Scale.Y, 0.00001)
			|| !FMath::IsNearlyEqual(Basis.Scale.X, Basis.Scale.Z, 0.00001))
			return Fail(TEXT("motion_asset_basis"), TEXT("normalized xyzw and finite positive uniform mesh scale required; no inferred transform"));
		return true;
	}

	bool LoadJson(const FString& Path, FJson& Document)
	{
		FString Text;
		return (FFileHelper::LoadFileToString(Text, *Path)
			&& FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Text), Document) && Document)
			|| Fail(Path, TEXT("unreadable JSON document"));
	}

	struct FTrack
	{
		TArray<FTransform> Keys;
		FTransform Reference;
		// An absent track means the engine reference pose; one key is an explicit static track.
		FTransform At(int32 Frame) const { return Keys.IsEmpty() ? Reference : Keys[Keys.Num() == 1 ? 0 : Frame]; }
	};

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

	/** Import-coordinate evidence only; generated motion always uses the original UE component pose. */
	struct FAxisMap
	{
		int32 Axis[3] = {0, 1, 2};
		FVector Sign = FVector::OneVector;
		FVector Map(const FVector& V) const { return FVector(V[Axis[0]], V[Axis[1]], V[Axis[2]]) * Sign; }
		FQuat MapRotation(const FQuat& Q) const
		{
			const double Determinant = FVector::DotProduct(FVector::CrossProduct(Map(FVector::ForwardVector), Map(FVector::RightVector)), Map(FVector::UpVector));
			const FVector Axial = Map(FVector(Q.X, Q.Y, Q.Z)) * Determinant;
			return FQuat(Axial.X, Axial.Y, Axial.Z, Q.W);
		}
	};

	// Existing content is only inspected. A producer marker never grants overwrite permission.
	bool CanInspectExisting(UObject* Object, UClass* ExpectedClass)
	{
		return Object && Object->IsA(ExpectedClass) && !Object->GetPackage()->IsDirty()
			&& Object->GetPackage()->GetMetaData().GetValue(Object, OwnerKey) == OwnerValue;
	}

	template<typename T> bool InspectOutput(const FString& Path, T*& Existing)
	{
		UObject* Object = LoadObject<UObject>(nullptr, *(Path + TEXT(".") + FPackageName::GetLongPackageAssetName(Path)));
		Existing = Cast<T>(Object);
		if (!Object)
		{
			const UPackage* Package = FindPackage(nullptr, *Path);
			return !FPackageName::DoesPackageExist(Path) && (!Package || !Package->IsDirty());
		}
		return FPackageName::DoesPackageExist(Path) && CanInspectExisting(Object, T::StaticClass());
	}

	/** Effective clip bounds are independent of exported support keys outside the native animation. */
	bool MatchesNativeClipRange(const double* Range, double NativeDuration)
	{
		return FMath::IsFinite(NativeDuration) && NativeDuration > 0
			&& FMath::IsNearlyZero(Range[0], .00001)
			&& FMath::IsNearlyEqual(Range[1], NativeDuration, .0001);
	}

	struct FPreparedMotion
	{
		FString Name, Path, SourceHash;
		FName Bone;
		FBasis Basis;
		TStrongObjectPtr<UAnimSequence> Source, Existing;
		TArray<FVector> Positions, Scales, ActorDisplacements;
		TArray<FQuat> Rotations;
		TArray<float> Times;
		FJson Report;
	};

	FString BasisStamp(const FBasis& Basis)
	{
		FJson Object = MakeShared<FJsonObject>();
		Object->SetBoolField(TEXT("confirmed"), true);
		Object->SetArrayField(TEXT("mesh_relative_rotation_xyzw"), {
			MakeShared<FJsonValueNumber>(Basis.Rotation.X), MakeShared<FJsonValueNumber>(Basis.Rotation.Y),
			MakeShared<FJsonValueNumber>(Basis.Rotation.Z), MakeShared<FJsonValueNumber>(Basis.Rotation.W)});
		Object->SetArrayField(TEXT("mesh_relative_scale"), VectorJson(Basis.Scale));
		FString Text;
		FJsonSerializer::Serialize(Object.ToSharedRef(), TJsonWriterFactory<>::Create(&Text));
		return Text;
	}

	bool DecomposeXYZ(const FTransform& Original, const FTransform& OriginalLocal, const FTransform& Parent,
		const FVector& FirstPosition, const FQuat& MeshToActor, FTransform& InPlaceLocal, FVector& ActorDelta)
	{
		const FVector Scale = Parent.GetScale3D();
		if (Parent.ContainsNaN() || FMath::IsNearlyZero(Scale.X) || FMath::IsNearlyZero(Scale.Y) || FMath::IsNearlyZero(Scale.Z)) return false;
		InPlaceLocal = FTransform(OriginalLocal.GetRotation(), Parent.InverseTransformPosition(FirstPosition), OriginalLocal.GetScale3D());
		ActorDelta = MeshToActor.RotateVector(Original.GetTranslation() - FirstPosition);
		return !InPlaceLocal.ContainsNaN() && !ActorDelta.ContainsNaN();
	}

	bool SameCurve(const FRichCurve& A, const FRichCurve& B)
	{
		return A.GetConstRefOfKeys() == B.GetConstRefOfKeys() && A.DefaultValue == B.DefaultValue
			&& A.PreInfinityExtrap == B.PreInfinityExtrap && A.PostInfinityExtrap == B.PostInfinityExtrap;
	}

	bool ValidateDerived(const FPreparedMotion& Plan, UAnimSequence* Derived)
	{
		const IAnimationDataModel* SourceModel = Plan.Source->GetDataModel();
		const IAnimationDataModel* Model = Derived->GetDataModel();
		FMetaData& Metadata = Derived->GetPackage()->GetMetaData();
		FJson StoredJson;
		FBasis Stored;
		const FString Stamp = Metadata.GetValue(Derived, TEXT("GGYGO.MotionAssetBasis"));
		if (!FJsonSerializer::Deserialize(TJsonReaderFactory<>::Create(Stamp), StoredJson) || !StoredJson
			|| !ReadBasis(StoredJson, Stored) || !Stored.Rotation.Equals(Plan.Basis.Rotation, .00001)
			|| !Stored.Scale.Equals(Plan.Basis.Scale, .00001))
			return Fail(Plan.Path, TEXT("derived basis provenance differs; existing asset preserved"));
		if (!Model || Derived->GetSkeleton() != Plan.Source->GetSkeleton() || Derived->bEnableRootMotion
			|| Derived->bForceRootLock || !FMath::IsNearlyEqual(Derived->RateScale, 1.f)
			|| Model->GetNumberOfKeys() != Plan.Times.Num() || Model->GetFrameRate() != SourceModel->GetFrameRate()
			|| !FMath::IsNearlyEqual(Derived->GetPlayLength(), Plan.Source->GetPlayLength(), .001f)
			|| Model->GetNumBoneTracks() != SourceModel->GetNumBoneTracks()
			|| Metadata.GetValue(Derived, TEXT("GGYGO.MotionCurveSpace")) != CurveSpace
			|| Metadata.GetValue(Derived, TEXT("GGYGO.MotionSourceFBXSHA256")) != Plan.SourceHash)
			return Fail(Plan.Path, TEXT("derived pose/grid/source/basis contract differs; existing asset preserved"));
		TArray<FName> Names;
		SourceModel->GetBoneTrackNames(Names);
		for (FName Name : Names)
		{
			if (!Model->IsValidBoneTrackName(Name)) return Fail(Plan.Path, TEXT("derived bone track missing"));
			TArray<FTransform> Actual, Expected;
			Model->GetBoneTrackTransforms(Name, Actual);
			if (Name == Plan.Bone)
			{
				if (Actual.Num() != Plan.Times.Num()) return Fail(Plan.Path, TEXT("derived motion-bone grid differs"));
				for (int32 Frame = 0; Frame < Actual.Num(); ++Frame)
					if (!Actual[Frame].Equals(FTransform(Plan.Rotations[Frame], Plan.Positions[Frame], Plan.Scales[Frame]), .001))
						return Fail(Plan.Path, TEXT("paired in-place pose differs"));
			}
			else
			{
				SourceModel->GetBoneTrackTransforms(Name, Expected);
				if (Actual.Num() != Expected.Num()) return Fail(Plan.Path, TEXT("non-motion bone grid changed"));
				for (int32 Frame = 0; Frame < Actual.Num(); ++Frame)
					if (!Actual[Frame].Equals(Expected[Frame], .001))
						return Fail(Plan.Path, TEXT("non-motion bone changed"));
			}
		}
		if (Model->GetFloatCurves().Num() != SourceModel->GetFloatCurves().Num() + 3)
			return Fail(Plan.Path, TEXT("derived float-curve set differs"));
		for (const FFloatCurve& SourceCurve : SourceModel->GetFloatCurves())
		{
			const FFloatCurve* Actual = Model->FindFloatCurve(FAnimationCurveIdentifier(SourceCurve.GetName(), ERawCurveTrackTypes::RCT_Float));
			if (!Actual || Actual->GetCurveTypeFlags() != SourceCurve.GetCurveTypeFlags() || !SameCurve(Actual->FloatCurve, SourceCurve.FloatCurve))
				return Fail(Plan.Path, TEXT("unrelated source curve changed"));
		}
		for (int32 Axis = 0; Axis < 3; ++Axis)
		{
			const FFloatCurve* Curve = Model->FindFloatCurve(FAnimationCurveIdentifier(CurveNames[Axis], ERawCurveTrackTypes::RCT_Float));
			if (!Curve || !Derived->HasCurveData(CurveNames[Axis], false)
				|| Curve->FloatCurve.PreInfinityExtrap != RCCE_Constant || Curve->FloatCurve.PostInfinityExtrap != RCCE_Constant)
				return Fail(Plan.Path, TEXT("required native XYZ curve missing or extrapolation differs"));
			const TArray<FRichCurveKey>& Keys = Curve->FloatCurve.GetConstRefOfKeys();
			if (Keys.Num() != Plan.Times.Num()) return Fail(Plan.Path, TEXT("XYZ curve key count differs"));
			for (int32 Frame = 0; Frame < Keys.Num(); ++Frame)
				if (!FMath::IsNearlyEqual(Keys[Frame].Time, Plan.Times[Frame], .0001f)
					|| !FMath::IsNearlyEqual(Keys[Frame].Value, static_cast<float>(Plan.ActorDisplacements[Frame][Axis]), .001f)
					|| Keys[Frame].InterpMode != RCIM_Linear)
					return Fail(Plan.Path, TEXT("XYZ curve differs from paired full trajectory"));
		}
		return true;
	}

	bool Prepare(const FJson& Clip, const FBasis& Basis, FPreparedMotion& Plan)
	{
		FString SourcePath, BoneName;
		const TArray<TSharedPtr<FJsonValue>>* Samples = nullptr;
		double AuditedDuration = 0, ClipRange[2];
		if (!Clip || !Clip->TryGetStringField(TEXT("source_clip"), Plan.Name)
			|| !Clip->TryGetStringField(TEXT("source_sequence"), SourcePath)
			|| !Clip->TryGetStringField(TEXT("derived_sequence"), Plan.Path)
			|| !Clip->TryGetStringField(TEXT("motion_bone"), BoneName) || BoneName.IsEmpty()
			|| !Clip->TryGetStringField(TEXT("fbx_sha256"), Plan.SourceHash) || Plan.SourceHash.Len() != 64
			|| !Clip->TryGetNumberField(TEXT("duration"), AuditedDuration) || !FMath::IsFinite(AuditedDuration)
			|| !ReadNumbers(Clip, TEXT("clip_range_seconds"), 2, ClipRange)
			|| !Clip->TryGetArrayField(TEXT("samples"), Samples))
			return Fail(TEXT("selected clip"), TEXT("invalid schema2 source audit"));
		Plan.Report->SetStringField(TEXT("source_clip"), Plan.Name);
		Plan.Report->SetStringField(TEXT("sequence"), Plan.Path);
		if (!FPackageName::IsValidLongPackageName(SourcePath) || SourcePath != FString(Base) + TEXT("AS_") + Plan.Name
			|| !FPackageName::IsValidLongPackageName(Plan.Path) || !Plan.Path.StartsWith(FString(Base) + TEXT("Derived/")))
			return Fail(Plan.Name, TEXT("source/derived paths outside the explicit Kevin animation contract"));
		Plan.Source.Reset(LoadObject<UAnimSequence>(nullptr, *(SourcePath + TEXT(".") + FPackageName::GetLongPackageAssetName(SourcePath))));
		if (!Plan.Source || !Plan.Source->GetSkeleton() || !Plan.Source->GetDataModel()
			|| !FPackageName::DoesPackageExist(SourcePath) || Plan.Source->GetPackage()->IsDirty()
			|| Plan.Source->GetSkeleton()->GetPackage()->IsDirty())
			return Fail(SourcePath, TEXT("missing/unsaved source, data model or skeleton"));
		Plan.Basis = Basis;
		Plan.Bone = FName(*BoneName);
		const IAnimationDataModel* Model = Plan.Source->GetDataModel();
		const FReferenceSkeleton& Ref = Plan.Source->GetSkeleton()->GetReferenceSkeleton();
		const int32 Bone = Ref.FindBoneIndex(Plan.Bone);
		const int32 Count = Model->GetNumberOfKeys();
		const float Duration = Plan.Source->GetPlayLength();
		if (Bone == INDEX_NONE || !Model->IsValidBoneTrackName(Plan.Bone) || Count < 2
			|| Count != Model->GetNumberOfFrames() + 1 || Samples->Num() != Count || Model->GetFrameRate().Numerator <= 0
			|| Model->GetFrameRate().Denominator <= 0 || !FMath::IsFinite(Duration) || Duration <= 0
			|| !MatchesNativeClipRange(ClipRange, Model->GetPlayLength())
			|| !FMath::IsNearlyEqual(AuditedDuration, ClipRange[1], .00001)
			|| !FMath::IsNearlyEqual(Plan.Source->RateScale, 1.f) || !FMath::IsNearlyEqual(static_cast<double>(Duration), AuditedDuration, .001))
			return Fail(SourcePath, TEXT("source key grid/duration/rate/motion bone differs from audited FBX"));
		for (FName Name : CurveNames)
			if (Model->FindFloatCurve(FAnimationCurveIdentifier(Name, ERawCurveTrackTypes::RCT_Float)))
				return Fail(SourcePath, TEXT("reserved XYZ curve already authored on source; no replacement"));
		TArray<FTrack> Tracks;
		Tracks.SetNum(Ref.GetNum());
		for (int32 Index = 0; Index < Ref.GetNum(); ++Index)
		{
			FTrack& Track = Tracks[Index];
			Track.Reference = Ref.GetRefBonePose()[Index];
			if (Track.Reference.ContainsNaN() || !Track.Reference.GetRotation().IsNormalized())
				return Fail(SourcePath, TEXT("invalid reference-pose transform: ") + Ref.GetBoneName(Index).ToString());
			if (!Model->IsValidBoneTrackName(Ref.GetBoneName(Index))) continue;
			Model->GetBoneTrackTransforms(Ref.GetBoneName(Index), Track.Keys);
			if (Track.Keys.Num() != 1 && Track.Keys.Num() != Count)
				return Fail(SourcePath, TEXT("bone track is neither explicit static nor complete source grid: ") + Ref.GetBoneName(Index).ToString());
			for (const FTransform& Key : Track.Keys)
				if (Key.ContainsNaN() || !Key.GetRotation().IsNormalized())
					return Fail(SourcePath, TEXT("invalid bone transform: ") + Ref.GetBoneName(Index).ToString());
		}
		TArray<FTransform> Original;
		TArray<FVector> FbxPositions;
		TArray<FQuat> FbxRotations;
		for (int32 Frame = 0; Frame < Count; ++Frame)
		{
			const FJson Sample = (*Samples)[Frame]->AsObject();
			double Time = 0, T[3], Q[4];
			const double GridTime = Model->GetFrameRate().AsSeconds(FFrameTime(Frame));
			if (!Sample || !Sample->TryGetNumberField(TEXT("time"), Time) || !FMath::IsFinite(Time)
				|| FMath::Abs(GridTime - Time) > .001 || !ReadNumbers(Sample, TEXT("fbx_translation_cm"), 3, T)
				|| !ReadNumbers(Sample, TEXT("fbx_rotation_xyzw"), 4, Q))
				return Fail(Plan.Name, TEXT("FBX sample time/finite coordinates do not match UE source grid"));
			const FQuat Rotation(Q[0], Q[1], Q[2], Q[3]);
			if (!Rotation.IsNormalized()) return Fail(Plan.Name, TEXT("audited FBX quaternion is not normalized"));
			const FTransform Component = ComponentAt(Tracks, Ref, Bone, Frame);
			if (Component.ContainsNaN() || !Component.GetRotation().IsNormalized())
				return Fail(SourcePath, TEXT("invalid original motion-bone component transform"));
			Original.Add(Component);
			FbxPositions.Add(FVector(T[0], T[1], T[2]));
			FbxRotations.Add(Rotation);
			Plan.Times.Add(Frame == Count - 1 ? Duration : static_cast<float>(GridTime));
		}
		if (!FMath::IsNearlyEqual(Model->GetFrameRate().AsSeconds(FFrameTime(Count - 1)), static_cast<double>(Duration), .0001))
			return Fail(Plan.Name, TEXT("native last frame does not cover full clip duration"));
		FAxisMap Mapping;
		double TranslationError = 0, RotationError = 0;
		int32 MatchingMaps = 0;
		const int32 Permutations[6][3] = {{0,1,2},{0,2,1},{1,0,2},{1,2,0},{2,0,1},{2,1,0}};
		for (const auto& Permutation : Permutations)
			for (int32 Bits = 0; Bits < 8; ++Bits)
			{
				FAxisMap Candidate;
				for (int32 Axis = 0; Axis < 3; ++Axis) Candidate.Axis[Axis] = Permutation[Axis];
				Candidate.Sign = FVector(Bits & 1 ? -1 : 1, Bits & 2 ? -1 : 1, Bits & 4 ? -1 : 1);
				double PositionError = 0, AngleError = 0;
				for (int32 Frame = 0; Frame < Count; ++Frame)
				{
					PositionError = FMath::Max(PositionError, FVector::Distance(Original[Frame].GetTranslation() - Original[0].GetTranslation(),
						Candidate.Map(FbxPositions[Frame] - FbxPositions[0])));
					const FQuat UE = Original[Frame].GetRotation() * Original[0].GetRotation().Inverse();
					const FQuat FBX = Candidate.MapRotation(FbxRotations[Frame] * FbxRotations[0].Inverse());
					AngleError = FMath::Max(AngleError, FMath::RadiansToDegrees(UE.AngularDistance(FBX)));
				}
				if (PositionError <= .25 && AngleError <= .25 && Candidate.Axis[2] == 1)
				{
					++MatchingMaps; Mapping = Candidate; TranslationError = PositionError; RotationError = AngleError;
				}
			}
		if (MatchingMaps != 1)
			return Fail(Plan.Name, FString::Printf(TEXT("FBX/UE full-pose axis evidence is missing or ambiguous (%d matching maps); no inferred basis"), MatchingMaps));
		Plan.Report->SetArrayField(TEXT("axis_permutation"), {MakeShared<FJsonValueNumber>(Mapping.Axis[0]), MakeShared<FJsonValueNumber>(Mapping.Axis[1]), MakeShared<FJsonValueNumber>(Mapping.Axis[2])});
		Plan.Report->SetArrayField(TEXT("axis_sign"), VectorJson(Mapping.Sign));
		Plan.Report->SetNumberField(TEXT("fbx_to_ue_translation_error_cm"), TranslationError);
		Plan.Report->SetNumberField(TEXT("fbx_to_ue_relative_rotation_error_deg"), RotationError);
		const int32 Parent = Ref.GetParentIndex(Bone);
		double Residual = 0, ReconstructionError = 0;
		for (int32 Frame = 0; Frame < Count; ++Frame)
		{
			const FTransform ParentPose = ComponentAt(Tracks, Ref, Parent, Frame);
			const FTransform OriginalLocal = Tracks[Bone].At(Frame);
			// Preserve original local rotation/scale exactly; only the translation track is rebased.
			FTransform Local;
			FVector ActorDelta;
			if (!DecomposeXYZ(Original[Frame], OriginalLocal, ParentPose, Original[0].GetTranslation(), Basis.Rotation, Local, ActorDelta))
				return Fail(Plan.Name, TEXT("paired pose has noninvertible parent or nonfinite motion"));
			Plan.Positions.Add(Local.GetTranslation());
			Plan.Rotations.Add(OriginalLocal.GetRotation());
			Plan.Scales.Add(OriginalLocal.GetScale3D());
			// UE imports are already cm. Uniform mesh scale is applied once by CMC, never baked here.
			Plan.ActorDisplacements.Add(ActorDelta);
			const FTransform Rebuilt = Local * ParentPose;
			Residual = FMath::Max(Residual, FVector::Distance(Rebuilt.GetTranslation(), Original[0].GetTranslation()));
			ReconstructionError = FMath::Max(ReconstructionError, FVector::Distance(Rebuilt.GetTranslation() + Basis.Rotation.UnrotateVector(Plan.ActorDisplacements.Last()), Original[Frame].GetTranslation()));
			if (!Rebuilt.GetRotation().Equals(Original[Frame].GetRotation(), .001)
				|| !Rebuilt.GetScale3D().Equals(Original[Frame].GetScale3D(), .001))
				return Fail(Plan.Name, TEXT("paired decomposition changed source rotation/scale"));
		}
		if (Residual > .001 || ReconstructionError > .001) return Fail(Plan.Name, TEXT("full XYZ paired decomposition exceeds tolerance"));
		Plan.Report->SetNumberField(TEXT("in_place_residual_xyz_cm"), Residual);
		Plan.Report->SetNumberField(TEXT("reconstruction_error_xyz_cm"), ReconstructionError);
		Plan.Report->SetArrayField(TEXT("ue_first_position_cm"), VectorJson(Original[0].GetTranslation()));
		Plan.Report->SetArrayField(TEXT("last_actor_displacement_cm"), VectorJson(Plan.ActorDisplacements.Last()));
		Plan.Report->SetNumberField(TEXT("duration"), Duration);
		Plan.Report->SetNumberField(TEXT("keys"), Count);
		UAnimSequence* Existing = nullptr;
		if (!InspectOutput(Plan.Path, Existing)) return Fail(Plan.Path, TEXT("wrong type/owner/dirty/unpersisted output; preserved"));
		Plan.Existing.Reset(Existing);
		if (Existing && !ValidateDerived(Plan, Existing)) return false;
		Plan.Report->SetBoolField(TEXT("saved_this_run"), false);
		Plan.Report->SetStringField(TEXT("status"), Existing ? TEXT("existing_verified_preserved") : TEXT("planned_missing"));
		return true;
	}

	bool Create(const FPreparedMotion& Plan)
	{
		if (Plan.Existing) return true;
		UAnimSequence* Derived = DuplicateObject<UAnimSequence>(Plan.Source.Get(), CreatePackage(*Plan.Path), *FPackageName::GetLongPackageAssetName(Plan.Path));
		if (!Derived) return Fail(Plan.Path, TEXT("unable to duplicate source"));
		TStrongObjectPtr<UAnimSequence> KeepAlive(Derived);
		Derived->SetFlags(RF_Public | RF_Standalone | RF_Transactional);
		IAnimationDataController& Controller = Derived->GetController();
		Controller.OpenBracket(FText::FromString(TEXT("Pair full XYZ in-place pose and actor-local curves")), false);
		bool bWritten = Controller.SetBoneTrackKeys(Plan.Bone, Plan.Positions, Plan.Rotations, Plan.Scales, false);
		for (int32 Axis = 0; bWritten && Axis < 3; ++Axis)
		{
			TArray<FRichCurveKey> Keys;
			for (int32 Frame = 0; Frame < Plan.Times.Num(); ++Frame)
			{
				FRichCurveKey Key(Plan.Times[Frame], static_cast<float>(Plan.ActorDisplacements[Frame][Axis]));
				Key.InterpMode = RCIM_Linear;
				Keys.Add(Key);
			}
			const FAnimationCurveIdentifier Id(CurveNames[Axis], ERawCurveTrackTypes::RCT_Float);
			bWritten = Controller.AddCurve(Id, AACF_DefaultCurve, false) && Controller.SetCurveKeys(Id, Keys, false);
		}
		Controller.CloseBracket(false);
		if (!bWritten) return Fail(Plan.Path, TEXT("paired bone/curve write failed; new package remains unsaved"));
		Derived->bEnableRootMotion = Derived->bForceRootLock = false;
		Derived->RateScale = 1.f;
		FMetaData& Metadata = Derived->GetPackage()->GetMetaData();
		Metadata.SetValue(Derived, OwnerKey, OwnerValue);
		Metadata.SetValue(Derived, TEXT("GGYGO.MotionCurveSpace"), CurveSpace);
		Metadata.SetValue(Derived, TEXT("GGYGO.MotionAssetBasis"), *BasisStamp(Plan.Basis));
		Metadata.SetValue(Derived, TEXT("GGYGO.MotionSourceFBXSHA256"), *Plan.SourceHash);
		Derived->PostEditChange();
		if (!ValidateDerived(Plan, Derived)) return false;
		FAssetRegistryModule::AssetCreated(Derived);
		Derived->MarkPackageDirty();
		FSavePackageArgs Args;
		Args.TopLevelFlags = RF_Public | RF_Standalone;
		Args.SaveFlags = SAVE_NoError;
		if (!UPackage::SavePackage(Derived->GetPackage(), Derived,
			*FPackageName::LongPackageNameToFilename(Plan.Path, FPackageName::GetAssetPackageExtension()), Args))
			return Fail(Plan.Path, TEXT("save failed; inspect partial output before retry"));
		Plan.Report->SetBoolField(TEXT("saved_this_run"), true);
		Plan.Report->SetStringField(TEXT("status"), TEXT("created"));
		return true;
	}

	void Run(const TArray<FString>& Args)
	{
		if (Args.Num() < 2 || (Args[0] != TEXT("audit") && Args[0] != TEXT("build")) || (Args[0] == TEXT("audit") && Args.Num() != 2))
		{ Fail(TEXT("command"), TEXT("expected <audit|build> <schema2-source-audit> [exact missing derived packages for build]")); return; }
		const bool bWrite = Args[0] == TEXT("build");
		FJson Document, Wiring, Config;
		if (!LoadJson(Args[1], Document) || !LoadJson(FPaths::ProjectDir() / BasisConfig, Wiring)
			|| !LoadJson(FPaths::ProjectDir() / MontageConfig, Config)) return;
		int32 Schema = 0, ConfigSchema = 0;
		FString BasisPath, SelectionPath;
		const FJson *Snapshot = nullptr, *Current = nullptr;
		const TArray<TSharedPtr<FJsonValue>> *Clips = nullptr, *Selected = nullptr, *Catalog = nullptr;
		if (!Document->TryGetNumberField(TEXT("schema"), Schema) || Schema != 2
			|| !Document->TryGetStringField(TEXT("basis_config"), BasisPath) || BasisPath != BasisConfig
			|| !Document->TryGetStringField(TEXT("montage_config"), SelectionPath) || SelectionPath != MontageConfig
			|| !Document->TryGetObjectField(TEXT("motion_asset_basis"), Snapshot)
			|| !Wiring->TryGetObjectField(TEXT("motion_asset_basis"), Current)
			|| !Document->TryGetArrayField(TEXT("clips"), Clips)
			|| !Config->TryGetNumberField(TEXT("schema_version"), ConfigSchema) || ConfigSchema != 2
			|| !Config->TryGetArrayField(TEXT("selected_actions"), Selected) || Selected->IsEmpty()
			|| !Config->TryGetArrayField(TEXT("actions"), Catalog) || Clips->Num() != Selected->Num())
		{ Fail(Args[1], TEXT("schema2, authoritative basis/selection paths and exact selected clip set required")); return; }
		FBasis Basis, Audited;
		if (!ReadBasis(*Current, Basis) || !ReadBasis(*Snapshot, Audited)) return;
		if (!Basis.Rotation.Equals(Audited.Rotation, .00001) || !Basis.Scale.Equals(Audited.Scale, .00001))
		{ Fail(Args[1], TEXT("basis snapshot is stale; audit the confirmed Wiring configuration again")); return; }
		TArray<FPreparedMotion> Plans;
		TSet<FString> Names, Targets;
		TArray<FString> Missing;
		TArray<TSharedPtr<FJsonValue>> Rows;
		bool bSuccess = true;
		for (int32 Index = 0; Index < Selected->Num(); ++Index)
		{
			FString Name;
			const FJson Clip = (*Clips)[Index]->AsObject();
			FString ClipName, ClipSource, ClipDerived, ClipBone;
			if (!(*Selected)[Index]->TryGetString(Name) || Name.IsEmpty() || Names.Contains(Name)
				|| !Clip || !Clip->TryGetStringField(TEXT("source_clip"), ClipName) || ClipName != Name
				|| !Clip->TryGetStringField(TEXT("source_sequence"), ClipSource)
				|| !Clip->TryGetStringField(TEXT("derived_sequence"), ClipDerived)
				|| !Clip->TryGetStringField(TEXT("motion_bone"), ClipBone))
			{ bSuccess = Fail(Args[1], TEXT("source audit does not match the ordered unique selected_actions")); break; }
			Names.Add(Name);
			FJson Action;
			for (const auto& Entry : *Catalog)
			{
				FString Candidate; const FJson Object = Entry->AsObject();
				if (Object && Object->TryGetStringField(TEXT("source_clip"), Candidate) && Candidate == Name)
				{
					if (Action) { bSuccess = Fail(Name, TEXT("ambiguous action catalog")); break; }
					Action = Object;
				}
			}
			FString ExpectedSource, ExpectedDerived, ExpectedBone;
			bool bRequired = false;
			if (!bSuccess) break;
			if (!Action || !Action->TryGetStringField(TEXT("source_sequence"), ExpectedSource) || ExpectedSource != ClipSource
				|| !Action->TryGetStringField(TEXT("sequence_override"), ExpectedDerived) || ExpectedDerived != ClipDerived
				|| !Action->TryGetStringField(TEXT("motion_bone"), ExpectedBone) || ExpectedBone != ClipBone
				|| !Action->TryGetBoolField(TEXT("require_sequence_override"), bRequired) || !bRequired || Targets.Contains(ClipDerived))
			{ bSuccess = Fail(Name, TEXT("stale/duplicate derived source, bone or selection contract")); break; }
			Targets.Add(ClipDerived);
			FPreparedMotion Plan; Plan.Report = MakeShared<FJsonObject>();
			Rows.Add(MakeShared<FJsonValueObject>(Plan.Report));
			bSuccess = Prepare(Clip, Basis, Plan);
			if (!bSuccess) break;
			if (!Plan.Existing) Missing.Add(Plan.Path);
			Plans.Add(MoveTemp(Plan));
		}
		if (bSuccess && bWrite)
		{
			TSet<FString> Approved;
			for (int32 Index = 2; Index < Args.Num(); ++Index)
			{
				if (!Missing.Contains(Args[Index]) || Approved.Contains(Args[Index]))
				{ bSuccess = Fail(Args[Index], TEXT("approved new packages must exactly match missing selected outputs")); break; }
				Approved.Add(Args[Index]);
			}
			for (const FString& Path : Missing)
				if (bSuccess && !Approved.Contains(Path)) bSuccess = Fail(Path, TEXT("explicit new-package authorization required"));
			// All sources, generated baselines and targets are prepared before any asset is created.
			for (const FPreparedMotion& Plan : Plans)
			{
				if (!bSuccess) break;
				bSuccess = Create(Plan);
			}
		}
		FJson Report = MakeShared<FJsonObject>();
		Report->SetBoolField(TEXT("success"), bSuccess);
		Report->SetBoolField(TEXT("write_requested"), bWrite);
		Report->SetArrayField(TEXT("clips"), Rows);
		FString Output;
		FJsonSerializer::Serialize(Report.ToSharedRef(), TJsonWriterFactory<>::Create(&Output));
		UE_LOG(LogTemp, Display, TEXT("[KevinMotion] %s"), *Output);
	}

	FAutoConsoleCommand Command(TEXT("GGYGO.BuildKevinMotionAssets"),
		TEXT("Explicit audit/build, schema2 source-audit path, and exact missing derived packages for build. No CurveVector/Profile assets or overwrites."),
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
	UAnimSequence* Asset = NewObject<UAnimSequence>(Package, *FPackageName::GetLongPackageAssetName(Package->GetName()));
	Package->GetMetaData().SetValue(Asset, OwnerKey, OwnerValue);
	Package->SetDirtyFlag(false);
	TestTrue(TEXT("Clean owned output passes memory guard"), CanInspectExisting(Asset, UAnimSequence::StaticClass()));
	TestFalse(TEXT("Owner marker cannot authorize wrong asset type"), CanInspectExisting(Asset, USkeleton::StaticClass()));
	UAnimSequence* Found = nullptr;
	TestFalse(TEXT("Unpersisted in-memory output is not a verified asset"), InspectOutput(Package->GetName(), Found));
	Package->SetDirtyFlag(true);
	TestFalse(TEXT("Unsaved edits reject all writes"), CanInspectExisting(Asset, UAnimSequence::StaticClass()));
	TestTrue(TEXT("Inspection retains dirty state"), Package->IsDirty());
	const double EffectiveRange[] = {0., 2.}, ExportSupportRange[] = {0., 2.0166667};
	TestTrue(TEXT("Effective clip range preserves the native final frame"), MatchesNativeClipRange(EffectiveRange, 2.));
	TestFalse(TEXT("Export support cannot extend the native clip"), MatchesNativeClipRange(ExportSupportRange, 2.));
	// Preserve the original nonzero offset/Q/S while removing real vertical motion.
	const FQuat MeshToActor(FVector::UpVector, HALF_PI);
	const FTransform Parent(FQuat(FVector::UpVector, .3), FVector(12, -8, 4), FVector(2));
	const FTransform FirstLocal(FQuat(FVector::ForwardVector, .2), FVector(30, 15, 70), FVector(1.1));
	const FTransform LastLocal(FirstLocal.GetRotation(), FirstLocal.GetTranslation() + FVector(25, -10, 35), FirstLocal.GetScale3D());
	const FTransform First = FirstLocal * Parent, Last = LastLocal * Parent;
	FTransform InPlace;
	FVector ActorDelta;
	TestTrue(TEXT("XYZ decomposition accepts valid original parent"), DecomposeXYZ(Last, LastLocal, Parent, First.GetTranslation(), MeshToActor, InPlace, ActorDelta));
	TestTrue(TEXT("Vertical component survives"), FMath::IsNearlyEqual(ActorDelta.Z, 70., .001));
	TestTrue(TEXT("Full in-place offset stays at first component pose"), (InPlace * Parent).GetTranslation().Equals(First.GetTranslation(), .001));
	TestTrue(TEXT("Actor curve reconstructs all XYZ"), ((InPlace * Parent).GetTranslation() + MeshToActor.UnrotateVector(ActorDelta)).Equals(Last.GetTranslation(), .001));
	TestTrue(TEXT("Original rotation retained"), InPlace.GetRotation().Equals(LastLocal.GetRotation()));
	TestTrue(TEXT("Original scale retained"), InPlace.GetScale3D().Equals(LastLocal.GetScale3D()));
	FVector InitialDelta;
	TestTrue(TEXT("First offset is not discarded"), DecomposeXYZ(First, FirstLocal, Parent, First.GetTranslation(), MeshToActor, InPlace, InitialDelta)
		&& InPlace.Equals(FirstLocal, .001) && InitialDelta.IsNearlyZero());
	return true;
}
#endif
