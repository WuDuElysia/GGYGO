#pragma once

#include "CoreMinimal.h"
#include "GGYGOAnimationCurveSnapshotLibrary.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GGYGOLocomotionMotionProfileAuthorLibrary.generated.h"

class UAnimSequence;
class UGGYGOLocomotionMotionProfile;

UENUM(BlueprintType)
enum class EGGYGOLocomotionProfileAuthorStatus : uint8
{
	Failed,
	CreatedUnsaved,
	ExistingMatched
};

/** Actual embedded FRichCurve fields. Profile storage has no source curve Name or Flags. */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOLocomotionRichCurveReadback
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	bool bHasExternalCurve = false;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float DefaultValue = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 PreInfinityExtrap = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 PostInfinityExtrap = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	TArray<FGGYGOFloatCurveKeySnapshot> Keys;
};

/** Read from the target object after validation, retaining its actual float Duration precision. */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOLocomotionProfileReadback
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float Duration = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	bool bLoop = false;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString SourceAssetIdentifier;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString SourceFingerprint;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FGGYGOLocomotionRichCurveReadback SpeedCurve;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FGGYGOLocomotionRichCurveReadback DirectionXCurve;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FGGYGOLocomotionRichCurveReadback DirectionYCurve;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FGGYGOLocomotionRichCurveReadback YawCurve;
};

/** Failed results have no Profile or partial readback; Error identifies the rejected contract. */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOLocomotionProfileAuthorResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	EGGYGOLocomotionProfileAuthorStatus Status = EGGYGOLocomotionProfileAuthorStatus::Failed;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	TObjectPtr<UGGYGOLocomotionMotionProfile> Profile = nullptr;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FGGYGOLocomotionProfileReadback Readback;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString Error;
};

/** Editor authoring only; runtime selection, playback and movement remain with Movement/CMC. */
UCLASS()
class GGYGOEDITOR_API UGGYGOLocomotionMotionProfileAuthorLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Requires the complete successful R3 snapshot in Speed/DirX/DirY/Yaw order and an
	 * exact source object path. DurationSeconds must match R1's binary64 duration;
	 * the target stores its explicit float conversion. All curve fields compare by
	 * value, with floating fields compared by raw bits, including inactive weights.
	 *
	 * A missing canonical /Game/Package.Object target is created in memory only,
	 * after a transient candidate passes ValidateProfile and full field readback.
	 * Existing targets must be clean and match every stored field; no overwrite.
	 * CreatedUnsaved transfers the pending object's save/discard responsibility to
	 * the caller. This function does not register assets, save packages or wire a
	 * MovementSet. Failure discards only this call's Profile. Creation/dirty
	 * callbacks can introduce independent package state, so a new package is
	 * preserved on failure and identified in Error; its dirty flag/lifecycle is
	 * never rolled back. A Profile rooted by a callback or containing foreign
	 * nested objects is also preserved with a diagnostic. Existing objects and
	 * foreign package contents are kept.
	 *
	 * SourceFingerprint is locomotion-richcurve-v1:blake3-256:<64 lowercase hex>.
	 * Its canonical stream uses little-endian uint32/uint64 and length-prefixed
	 * UTF-8 (uint32 byte length, no terminator): version domain, actual source path,
	 * duration binary64 bits, uint32 curve count (4), then curves in fixed order.
	 * Each curve contributes name, flags as uint32, default float bits, pre/post
	 * modes as uint32, uint32 key count, then each key's six float bit patterns
	 * (Time, Value, Arrive/LeaveTangent, Arrive/LeaveTangentWeight) and three uint32
	 * modes (Interp, Tangent, TangentWeight), preserving key order. bLoop is
	 * separately checked configuration. This is not a whole-asset/disk fingerprint.
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOLocomotionProfileAuthorResult CreateOrInspectProfile(
		const UAnimSequence* Source,
		const FString& ExpectedSourceAssetIdentifier,
		const FGGYGOFloatCurveReadResult& ExpectedSnapshot,
		const FString& TargetProfileObjectPath,
		double DurationSeconds,
		bool bLoop);
};
