#include "GGYGOLocomotionMotionProfileAuthorLibrary.h"

#include "Animation/AnimSequence.h"
#include "Character/Data/GGYGOLocomotionMotionProfile.h"
#include "Containers/StringConv.h"
#include "GGYGOAnimationCurveReadLibrary.h"
#include "Hash/Blake3.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/UObjectHash.h"

namespace GGYGOLocomotionProfileAuthoring
{
	uint32 FloatBits(float Value)
	{
		static_assert(sizeof(float) == sizeof(uint32));
		uint32 Bits;
		FMemory::Memcpy(&Bits, &Value, sizeof(Bits));
		return Bits;
	}

	uint64 DoubleBits(double Value)
	{
		static_assert(sizeof(double) == sizeof(uint64));
		uint64 Bits;
		FMemory::Memcpy(&Bits, &Value, sizeof(Bits));
		return Bits;
	}

	FGGYGOFloatCurveKeySnapshot ReadKey(const FRichCurveKey& Key)
	{
		FGGYGOFloatCurveKeySnapshot Result;
		Result.Time = Key.Time;
		Result.Value = Key.Value;
		Result.ArriveTangent = Key.ArriveTangent;
		Result.LeaveTangent = Key.LeaveTangent;
		Result.ArriveTangentWeight = Key.ArriveTangentWeight;
		Result.LeaveTangentWeight = Key.LeaveTangentWeight;
		Result.InterpMode = static_cast<int32>(Key.InterpMode.GetValue());
		Result.TangentMode = static_cast<int32>(Key.TangentMode.GetValue());
		Result.TangentWeightMode = static_cast<int32>(Key.TangentWeightMode.GetValue());
		return Result;
	}

	bool MatchKey(const FRichCurveKey& Actual, const FGGYGOFloatCurveKeySnapshot& Expected,
		FString& OutField)
	{
		const FGGYGOFloatCurveKeySnapshot Read = ReadKey(Actual);
#define GGYGO_MATCH_KEY_FLOAT(Field) \
		if (FloatBits(Read.Field) != FloatBits(Expected.Field)) { OutField = TEXT(#Field); return false; }
		GGYGO_MATCH_KEY_FLOAT(Time)
		GGYGO_MATCH_KEY_FLOAT(Value)
		GGYGO_MATCH_KEY_FLOAT(ArriveTangent)
		GGYGO_MATCH_KEY_FLOAT(LeaveTangent)
		GGYGO_MATCH_KEY_FLOAT(ArriveTangentWeight)
		GGYGO_MATCH_KEY_FLOAT(LeaveTangentWeight)
#undef GGYGO_MATCH_KEY_FLOAT
#define GGYGO_MATCH_KEY_MODE(Field) \
		if (Read.Field != Expected.Field) { OutField = TEXT(#Field); return false; }
		GGYGO_MATCH_KEY_MODE(InterpMode)
		GGYGO_MATCH_KEY_MODE(TangentMode)
		GGYGO_MATCH_KEY_MODE(TangentWeightMode)
#undef GGYGO_MATCH_KEY_MODE
		return true;
	}

	bool MatchRichCurve(const FRichCurve& Actual, float DefaultValue, int32 PreInfinityExtrap,
		int32 PostInfinityExtrap, const TArray<FGGYGOFloatCurveKeySnapshot>& Keys, FString& OutField)
	{
		if (FloatBits(Actual.DefaultValue) != FloatBits(DefaultValue))
		{
			OutField = TEXT("DefaultValue");
			return false;
		}
		if (static_cast<int32>(Actual.PreInfinityExtrap.GetValue()) != PreInfinityExtrap)
		{
			OutField = TEXT("PreInfinityExtrap");
			return false;
		}
		if (static_cast<int32>(Actual.PostInfinityExtrap.GetValue()) != PostInfinityExtrap)
		{
			OutField = TEXT("PostInfinityExtrap");
			return false;
		}
		const TArray<FRichCurveKey>& ActualKeys = Actual.GetConstRefOfKeys();
		if (ActualKeys.Num() != Keys.Num())
		{
			OutField = TEXT("Keys.Num");
			return false;
		}
		for (int32 Index = 0; Index < ActualKeys.Num(); ++Index)
		{
			if (!MatchKey(ActualKeys[Index], Keys[Index], OutField))
			{
				OutField = FString::Printf(TEXT("Keys[%d].%s"), Index, *OutField);
				return false;
			}
		}
		return true;
	}

	FGGYGOLocomotionRichCurveReadback ReadRuntimeCurve(const FRuntimeFloatCurve& RuntimeCurve)
	{
		FGGYGOLocomotionRichCurveReadback Read;
		Read.bHasExternalCurve = RuntimeCurve.ExternalCurve != nullptr;
		const FRichCurve& Curve = RuntimeCurve.EditorCurveData;
		Read.DefaultValue = Curve.DefaultValue;
		Read.PreInfinityExtrap = static_cast<int32>(Curve.PreInfinityExtrap.GetValue());
		Read.PostInfinityExtrap = static_cast<int32>(Curve.PostInfinityExtrap.GetValue());
		Read.Keys.Reserve(Curve.GetConstRefOfKeys().Num());
		for (const FRichCurveKey& Key : Curve.GetConstRefOfKeys())
		{
			Read.Keys.Add(ReadKey(Key));
		}
		return Read;
	}

	FGGYGOLocomotionProfileReadback ReadProfile(const UGGYGOLocomotionMotionProfile& Profile)
	{
		FGGYGOLocomotionProfileReadback Read;
		Read.Duration = Profile.Duration;
		Read.bLoop = Profile.bLoop;
		Read.SourceAssetIdentifier = Profile.SourceAssetIdentifier;
		Read.SourceFingerprint = Profile.SourceFingerprint;
		Read.SpeedCurve = ReadRuntimeCurve(Profile.SpeedCurve);
		Read.DirectionXCurve = ReadRuntimeCurve(Profile.DirectionXCurve);
		Read.DirectionYCurve = ReadRuntimeCurve(Profile.DirectionYCurve);
		Read.YawCurve = ReadRuntimeCurve(Profile.YawCurve);
		return Read;
	}

	const TArray<FName>& CurveNames()
	{
		static const TArray<FName> Names = {
			TEXT("RootMotion_Speed"), TEXT("RootMotion_DirX"),
			TEXT("RootMotion_DirY"), TEXT("RootMotion_Yaw") };
		return Names;
	}

	bool ReadAndMatchSource(const UAnimSequence* Source, const FString& SourceIdentifier,
		const FGGYGOFloatCurveReadResult& Expected, double DurationSeconds,
		TArray<FFloatCurve>& OutCurves, FString& OutError)
	{
		OutCurves.Reset();
		OutError.Reset();
		if (!IsValid(Source) || !Source->GetPathName().Equals(SourceIdentifier, ESearchCase::CaseSensitive))
		{
			OutError = TEXT("SourceAssetIdentifier differs from the current valid source object path");
			return false;
		}
		if (!Expected.bSucceeded || !Expected.Error.IsEmpty() || Expected.Curves.Num() != CurveNames().Num())
		{
			OutError = TEXT("ExpectedSnapshot must be successful, without an error, and contain exactly four curves");
			return false;
		}
		double ActualDuration = 0.0;
		if (!UGGYGOAnimationCurveReadLibrary::ReadFloatCurves(Source, CurveNames(), OutCurves,
			ActualDuration, OutError))
		{
			return false;
		}
		if (DoubleBits(ActualDuration) != DoubleBits(DurationSeconds)
			|| DoubleBits(ActualDuration) != DoubleBits(Expected.DurationSeconds))
		{
			OutError = TEXT("DurationSeconds/ExpectedSnapshot.DurationSeconds differs from R1 source duration bits");
			return false;
		}
		if (OutCurves.Num() != CurveNames().Num())
		{
			OutError = TEXT("R1 returned an unexpected curve count");
			return false;
		}
		for (int32 Index = 0; Index < OutCurves.Num(); ++Index)
		{
			const FFloatCurve& Actual = OutCurves[Index];
			const FGGYGOFloatCurveSnapshot& Snapshot = Expected.Curves[Index];
			FString Field;
			if (!Actual.GetName().ToString().Equals(Snapshot.Name.ToString(), ESearchCase::CaseSensitive))
			{
				Field = TEXT("Name/order");
			}
			else if (Actual.GetCurveTypeFlags() != Snapshot.Flags)
			{
				Field = TEXT("Flags");
			}
			else if (MatchRichCurve(Actual.FloatCurve, Snapshot.DefaultValue, Snapshot.PreInfinityExtrap,
				Snapshot.PostInfinityExtrap, Snapshot.Keys, Field))
			{
				continue;
			}
			OutError = FString::Printf(TEXT("ExpectedSnapshot.Curves[%d] (%s).%s differs from R1"),
				Index, *Actual.GetName().ToString(), *Field);
			return false;
		}
		return true;
	}

	/** Writes canonical field bytes, never native structs, padding or host-endian representations. */
	class FSourceFingerprintWriter
	{
	public:
		void UInt32(uint32 Value)
		{
			uint8 Bytes[4];
			for (uint32 Index = 0; Index < 4; ++Index)
			{
				Bytes[Index] = static_cast<uint8>(Value >> (Index * 8));
			}
			Hasher.Update(Bytes, sizeof(Bytes));
		}

		void UInt64(uint64 Value)
		{
			uint8 Bytes[8];
			for (uint32 Index = 0; Index < 8; ++Index)
			{
				Bytes[Index] = static_cast<uint8>(Value >> (Index * 8));
			}
			Hasher.Update(Bytes, sizeof(Bytes));
		}

		void Utf8(const FString& Value)
		{
			const FTCHARToUTF8 Encoded(*Value);
			UInt32(static_cast<uint32>(Encoded.Length()));
			Hasher.Update(Encoded.Get(), static_cast<uint64>(Encoded.Length()));
		}

		FString Finish() const
		{
			const FBlake3Hash Hash = Hasher.Finalize();
			const TCHAR* Hex = TEXT("0123456789abcdef");
			FString Result = TEXT("locomotion-richcurve-v1:blake3-256:");
			for (uint8 Byte : Hash.GetBytes())
			{
				Result.AppendChar(Hex[Byte >> 4]);
				Result.AppendChar(Hex[Byte & 15]);
			}
			return Result;
		}

	private:
		FBlake3 Hasher;
	};

	FString Fingerprint(const FString& SourceIdentifier, double DurationSeconds,
		const TArray<FFloatCurve>& Curves)
	{
		FSourceFingerprintWriter Writer;
		Writer.Utf8(TEXT("locomotion-richcurve-v1"));
		Writer.Utf8(SourceIdentifier);
		Writer.UInt64(DoubleBits(DurationSeconds));
		Writer.UInt32(static_cast<uint32>(Curves.Num()));
		for (const FFloatCurve& Curve : Curves)
		{
			Writer.Utf8(Curve.GetName().ToString());
			Writer.UInt32(static_cast<uint32>(Curve.GetCurveTypeFlags()));
			Writer.UInt32(FloatBits(Curve.FloatCurve.DefaultValue));
			Writer.UInt32(static_cast<uint32>(Curve.FloatCurve.PreInfinityExtrap.GetValue()));
			Writer.UInt32(static_cast<uint32>(Curve.FloatCurve.PostInfinityExtrap.GetValue()));
			Writer.UInt32(static_cast<uint32>(Curve.FloatCurve.GetConstRefOfKeys().Num()));
			for (const FRichCurveKey& Key : Curve.FloatCurve.GetConstRefOfKeys())
			{
				Writer.UInt32(FloatBits(Key.Time));
				Writer.UInt32(FloatBits(Key.Value));
				Writer.UInt32(FloatBits(Key.ArriveTangent));
				Writer.UInt32(FloatBits(Key.LeaveTangent));
				Writer.UInt32(FloatBits(Key.ArriveTangentWeight));
				Writer.UInt32(FloatBits(Key.LeaveTangentWeight));
				Writer.UInt32(static_cast<uint32>(Key.InterpMode.GetValue()));
				Writer.UInt32(static_cast<uint32>(Key.TangentMode.GetValue()));
				Writer.UInt32(static_cast<uint32>(Key.TangentWeightMode.GetValue()));
			}
		}
		return Writer.Finish();
	}

	void Populate(UGGYGOLocomotionMotionProfile& Profile, const TArray<FFloatCurve>& Curves,
		float Duration, bool bLoop, const FString& SourceIdentifier, const FString& SourceFingerprint)
	{
		FRuntimeFloatCurve* Targets[] = { &Profile.SpeedCurve, &Profile.DirectionXCurve,
			&Profile.DirectionYCurve, &Profile.YawCurve };
		for (int32 Index = 0; Index < UE_ARRAY_COUNT(Targets); ++Index)
		{
			Targets[Index]->ExternalCurve = nullptr;
			Targets[Index]->EditorCurveData = Curves[Index].FloatCurve;
		}
		Profile.Duration = Duration;
		Profile.bLoop = bLoop;
		Profile.SourceAssetIdentifier = SourceIdentifier;
		Profile.SourceFingerprint = SourceFingerprint;
	}

	bool ValidateAndRead(const UGGYGOLocomotionMotionProfile& Profile,
		const FGGYGOFloatCurveReadResult& ExpectedSnapshot, float Duration, bool bLoop,
		const FString& SourceIdentifier, const FString& SourceFingerprint,
		FGGYGOLocomotionProfileReadback& OutReadback, FString& OutError)
	{
		OutReadback = FGGYGOLocomotionProfileReadback();
		OutError.Reset();
		if (FloatBits(Profile.Duration) != FloatBits(Duration)) { OutError = TEXT("Duration bits differ"); return false; }
		if (Profile.bLoop != bLoop) { OutError = TEXT("bLoop differs"); return false; }
		if (!Profile.SourceAssetIdentifier.Equals(SourceIdentifier, ESearchCase::CaseSensitive))
		{
			OutError = TEXT("SourceAssetIdentifier differs");
			return false;
		}
		if (!Profile.SourceFingerprint.Equals(SourceFingerprint, ESearchCase::CaseSensitive))
		{
			OutError = TEXT("SourceFingerprint differs");
			return false;
		}
		const FRuntimeFloatCurve* Curves[] = { &Profile.SpeedCurve, &Profile.DirectionXCurve,
			&Profile.DirectionYCurve, &Profile.YawCurve };
		for (int32 Index = 0; Index < UE_ARRAY_COUNT(Curves); ++Index)
		{
			FString Field;
			const FGGYGOFloatCurveSnapshot& Expected = ExpectedSnapshot.Curves[Index];
			if (Curves[Index]->ExternalCurve != nullptr)
			{
				Field = TEXT("ExternalCurve must be null");
			}
			else if (MatchRichCurve(Curves[Index]->EditorCurveData, Expected.DefaultValue,
				Expected.PreInfinityExtrap, Expected.PostInfinityExtrap, Expected.Keys, Field))
			{
				continue;
			}
			OutError = FString::Printf(TEXT("Target curve %s.%s"), *CurveNames()[Index].ToString(), *Field);
			return false;
		}
		if (!Profile.ValidateProfile(OutError))
		{
			OutError = TEXT("ValidateProfile: ") + OutError;
			return false;
		}
		OutReadback = ReadProfile(Profile);
		return true;
	}

	bool CheckNewPackage(const UPackage* Package, const FString& PackageName,
		const UGGYGOLocomotionMotionProfile* OwnedProfile, bool bExpectedDirty, FString& OutError)
	{
		if (!IsValid(Package) || Package->GetOuter() != nullptr || Package->IsRooted()
			|| Package->HasAnyFlags(RF_Transient)
			|| !Package->GetPathName().Equals(PackageName, ESearchCase::CaseSensitive)
			|| FindPackage(nullptr, *PackageName) != Package || Package->IsDirty() != bExpectedDirty)
		{
			OutError = TEXT("New package identity/lifecycle/dirty state changed during an editor callback");
			return false;
		}
		TArray<UObject*> Contents;
		GetObjectsWithOuter(Package, Contents, EGetObjectsFlags::IncludeNestedObjects);
		for (const UObject* Object : Contents)
		{
			if (Object != OwnedProfile)
			{
				OutError = FString::Printf(TEXT("New package contains an object not owned by this call: %s"),
					*Object->GetPathName());
				return false;
			}
		}
		return true;
	}

	/** Owns only the exact scratch/new Profile. Package references never grant exclusive state ownership. */
	struct FOwnedProfile
	{
		TStrongObjectPtr<UGGYGOLocomotionMotionProfile> Profile;
		TStrongObjectPtr<UPackage> Package;
		bool bTransferred = false;
		bool bCleanupCompleted = false;

		FString Cleanup()
		{
			if (bTransferred || bCleanupCompleted)
			{
				return FString();
			}
			bCleanupCompleted = true;
			FString Diagnostic;
			if (IsValid(Profile.Get()))
			{
				TArray<UObject*> NestedObjects;
				GetObjectsWithOuter(Profile.Get(), NestedObjects, EGetObjectsFlags::IncludeNestedObjects);
				if (Profile->IsRooted())
				{
					Diagnostic = FString::Printf(TEXT("Profile preserved because a callback rooted it: %s. "),
						*Profile->GetPathName());
				}
				else if (!NestedObjects.IsEmpty())
				{
					Diagnostic = FString::Printf(TEXT("Profile preserved because it contains a foreign nested object: %s in %s. "),
						*NestedObjects[0]->GetPathName(), *Profile->GetPathName());
				}
				else
				{
					Profile->ClearFlags(RF_Public | RF_Standalone);
					Profile->SetFlags(RF_Transient);
					Profile->MarkAsGarbage();
				}
			}
			if (Package.IsValid())
			{
				// UObject creation and dirty notifications cross reentrant callbacks. Contents alone
				// cannot prove ownership of arbitrary package state; never clear/garbage the package.
				Diagnostic += FString::Printf(TEXT("New package preserved at %s: callback-modified package state "
					"cannot be proven exclusive to this call; dirty flag and lifecycle left intact."),
					*Package->GetPathName());
			}
			return Diagnostic;
		}

		~FOwnedProfile()
		{
			Cleanup();
		}
	};
}

FGGYGOLocomotionProfileAuthorResult UGGYGOLocomotionMotionProfileAuthorLibrary::CreateOrInspectProfile(
	const UAnimSequence* Source, const FString& ExpectedSourceAssetIdentifier,
	const FGGYGOFloatCurveReadResult& ExpectedSnapshot, const FString& TargetProfileObjectPath,
	double DurationSeconds, bool bLoop)
{
	using namespace GGYGOLocomotionProfileAuthoring;
	FString ActualSourceIdentifier = TEXT("<not inspected>");
	FOwnedProfile Candidate;
	FOwnedProfile Created;
	const auto Fail = [&](const FString& Reason)
	{
		const FString CandidateCleanup = Candidate.Cleanup();
		const FString CreatedCleanup = Created.Cleanup();
		FGGYGOLocomotionProfileAuthorResult Result;
		Result.Error = FString::Printf(TEXT("[GGYGOEditor.ProfileAuthor] Source=%s ExpectedSource=%s Target=%s: %s%s%s"),
			*ActualSourceIdentifier, *ExpectedSourceAssetIdentifier, *TargetProfileObjectPath, *Reason,
			CandidateCleanup.IsEmpty() ? TEXT("") : *(TEXT("; ") + CandidateCleanup),
			CreatedCleanup.IsEmpty() ? TEXT("") : *(TEXT("; ") + CreatedCleanup));
		return Result;
	};
	if (!IsInGameThread()) { return Fail(TEXT("Authoring requires the game thread")); }
	if (!IsValid(Source)) { return Fail(TEXT("Source is null or invalid")); }
	ActualSourceIdentifier = Source->GetPathName();
	TStrongObjectPtr<const UAnimSequence> SourceLifetime(Source);
	TArray<FFloatCurve> SourceCurves;
	FString Error;
	if (!ReadAndMatchSource(Source, ExpectedSourceAssetIdentifier, ExpectedSnapshot,
		DurationSeconds, SourceCurves, Error))
	{
		return Fail(Error);
	}

	FText PathError;
	if (!FPackageName::IsValidObjectPath(TargetProfileObjectPath, &PathError)
		|| TargetProfileObjectPath.Contains(TEXT(":")))
	{
		return Fail(TEXT("Target must be a canonical top-level object path: ") + PathError.ToString());
	}
	const FString PackageName = FPackageName::ObjectPathToPackageName(TargetProfileObjectPath);
	const FString ObjectName = FPackageName::ObjectPathToObjectName(TargetProfileObjectPath);
	if (!PackageName.StartsWith(TEXT("/Game/"), ESearchCase::CaseSensitive)
		|| !FPackageName::IsValidLongPackageName(PackageName, false, &PathError)
		|| ObjectName.IsEmpty()
		|| !TargetProfileObjectPath.Equals(PackageName + TEXT(".") + ObjectName, ESearchCase::CaseSensitive))
	{
		return Fail(TEXT("Target must explicitly identify a valid /Game/Package.Object: ") + PathError.ToString());
	}
	if (!FMath::IsFinite(DurationSeconds) || DurationSeconds <= 0.0
		|| DurationSeconds > static_cast<double>(MAX_flt))
	{
		return Fail(TEXT("DurationSeconds must be finite, positive and within the finite float storage range"));
	}
	const float StoredDuration = static_cast<float>(DurationSeconds);
	const FString SourceFingerprint = Fingerprint(ExpectedSourceAssetIdentifier, DurationSeconds, SourceCurves);

	Candidate.Profile.Reset(NewObject<UGGYGOLocomotionMotionProfile>(GetTransientPackage(), NAME_None, RF_Transient));
	if (!Candidate.Profile.IsValid()) { return Fail(TEXT("Transient candidate creation failed")); }
	Populate(*Candidate.Profile, SourceCurves, StoredDuration, bLoop, ExpectedSourceAssetIdentifier, SourceFingerprint);
	FGGYGOLocomotionProfileReadback Readback;
	if (!ValidateAndRead(*Candidate.Profile, ExpectedSnapshot, StoredDuration, bLoop,
		ExpectedSourceAssetIdentifier, SourceFingerprint, Readback, Error))
	{
		return Fail(TEXT("Transient candidate rejected: ") + Error);
	}

	UObject* Existing = FindObject<UObject>(nullptr, *TargetProfileObjectPath);
	const bool bPackageOnDisk = FPackageName::DoesPackageExist(PackageName);
	if (!Existing && bPackageOnDisk)
	{
		Existing = LoadObject<UObject>(nullptr, *TargetProfileObjectPath, nullptr, LOAD_NoWarn);
		if (!Existing) { return Fail(TEXT("Target package exists on disk but the requested object cannot be loaded")); }
	}
	if (Existing)
	{
		TStrongObjectPtr<UObject> ExistingLifetime(Existing);
		UGGYGOLocomotionMotionProfile* Profile = Cast<UGGYGOLocomotionMotionProfile>(Existing);
		if (!IsValid(Profile)) { return Fail(TEXT("Existing target is not a valid locomotion motion Profile")); }
		if (!Profile->GetPathName().Equals(TargetProfileObjectPath, ESearchCase::CaseSensitive))
		{
			return Fail(TEXT("Existing target resolved to a different object path"));
		}
		if (Profile->GetOutermost()->IsDirty()) { return Fail(TEXT("Existing target package is dirty; inspection refused")); }
		// Loading may run PostLoad callbacks. Re-read source once, with no retries or alternate source.
		if (!ReadAndMatchSource(Source, ExpectedSourceAssetIdentifier, ExpectedSnapshot,
			DurationSeconds, SourceCurves, Error)) { return Fail(TEXT("Source changed during inspection: ") + Error); }
		if (!ValidateAndRead(*Profile, ExpectedSnapshot, StoredDuration, bLoop,
			ExpectedSourceAssetIdentifier, SourceFingerprint, Readback, Error))
		{
			return Fail(TEXT("Existing target rejected without overwrite: ") + Error);
		}
		const FString CleanupError = Candidate.Cleanup();
		if (!CleanupError.IsEmpty()) { return Fail(CleanupError); }
		FGGYGOLocomotionProfileAuthorResult Result;
		Result.Status = EGGYGOLocomotionProfileAuthorStatus::ExistingMatched;
		Result.Profile = Profile;
		Result.Readback = MoveTemp(Readback);
		return Result;
	}
	if (FindPackage(nullptr, *PackageName))
	{
		return Fail(TEXT("Target package is already loaded without the requested object; creation refused"));
	}
	// Recheck immediately before taking ownership; never reuse or clean an existing package.
	if (FindObject<UObject>(nullptr, *TargetProfileObjectPath) || FPackageName::DoesPackageExist(PackageName))
	{
		return Fail(TEXT("Target became occupied before creation"));
	}

	Created.Package.Reset(CreatePackage(*PackageName));
	if (!Created.Package.IsValid()) { return Fail(TEXT("Target package creation failed")); }
	// CreatePackage runs UObject creation listeners. Its returned identity and contents are not assumed intact.
	if (!CheckNewPackage(Created.Package.Get(), PackageName, nullptr, false, Error)) { return Fail(Error); }
	if (!ReadAndMatchSource(Source, ExpectedSourceAssetIdentifier, ExpectedSnapshot,
		DurationSeconds, SourceCurves, Error)) { return Fail(TEXT("Source changed during package creation: ") + Error); }
	const FName TargetName(*ObjectName);
	if (FPackageName::DoesPackageExist(PackageName) || FindObject<UObject>(nullptr, *TargetProfileObjectPath)
		|| FindObjectFast<UObject>(Created.Package.Get(), TargetName))
	{
		return Fail(TEXT("Target name/package became occupied during package creation; object creation refused"));
	}
	Created.Profile.Reset(NewObject<UGGYGOLocomotionMotionProfile>(Created.Package.Get(), TargetName,
		RF_Public | RF_Standalone | RF_Transactional));
	if (!IsValid(Created.Profile.Get()) || Created.Profile->IsRooted()
		|| Created.Profile->GetOuter() != Created.Package.Get()
		|| FindObjectFast<UObject>(Created.Package.Get(), TargetName) != Created.Profile.Get()
		|| !Created.Profile->GetPathName().Equals(TargetProfileObjectPath, ESearchCase::CaseSensitive))
	{
		return Fail(TEXT("Created Profile identity/lifecycle changed during object creation"));
	}
	if (!CheckNewPackage(Created.Package.Get(), PackageName, Created.Profile.Get(), false, Error)) { return Fail(Error); }
	Populate(*Created.Profile, SourceCurves, StoredDuration, bLoop, ExpectedSourceAssetIdentifier, SourceFingerprint);
	if (!ValidateAndRead(*Created.Profile, ExpectedSnapshot, StoredDuration, bLoop,
		ExpectedSourceAssetIdentifier, SourceFingerprint, Readback, Error))
	{
		return Fail(TEXT("Created target rejected: ") + Error);
	}
	if (!Created.Profile->MarkPackageDirty()) { return Fail(TEXT("New target package could not be marked dirty")); }
	// Dirty notifications may invoke editor callbacks; verify both contracts before transferring ownership.
	if (!ReadAndMatchSource(Source, ExpectedSourceAssetIdentifier, ExpectedSnapshot,
		DurationSeconds, SourceCurves, Error)) { return Fail(TEXT("Source changed during creation: ") + Error); }
	if (!CheckNewPackage(Created.Package.Get(), PackageName, Created.Profile.Get(), true, Error)) { return Fail(Error); }
	if (!IsValid(Created.Profile.Get()) || Created.Profile->IsRooted()
		|| Created.Profile->GetOuter() != Created.Package.Get()
		|| FindObjectFast<UObject>(Created.Package.Get(), TargetName) != Created.Profile.Get()
		|| !Created.Profile->GetPathName().Equals(TargetProfileObjectPath, ESearchCase::CaseSensitive))
	{
		return Fail(TEXT("Created target lifecycle/path/dirty state changed before handoff"));
	}
	if (!ValidateAndRead(*Created.Profile, ExpectedSnapshot, StoredDuration, bLoop,
		ExpectedSourceAssetIdentifier, SourceFingerprint, Readback, Error))
	{
		return Fail(TEXT("Created target changed before handoff: ") + Error);
	}
	const FString CleanupError = Candidate.Cleanup();
	if (!CleanupError.IsEmpty()) { return Fail(CleanupError); }
	FGGYGOLocomotionProfileAuthorResult Result;
	Result.Status = EGGYGOLocomotionProfileAuthorStatus::CreatedUnsaved;
	Result.Profile = Created.Profile.Get();
	Result.Readback = MoveTemp(Readback);
	Created.bTransferred = true;
	return Result;
}
