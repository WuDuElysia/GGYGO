// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GGYGOAnimationCurveSnapshotLibrary.generated.h"

class UAnimSequence;

/** Complete key values; modes retain their native numeric values, including Hidden None entries. */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOFloatCurveKeySnapshot
{
	GENERATED_BODY()

public:
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float Time = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float Value = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float ArriveTangent = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float LeaveTangent = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float ArriveTangentWeight = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float LeaveTangentWeight = 0.0f;

	/** Native ERichCurveInterpMode value. */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 InterpMode = 0;

	/** Native ERichCurveTangentMode value. */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 TangentMode = 0;

	/** Native ERichCurveTangentWeightMode value. */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 TangentWeightMode = 0;
};

/** Independent values from R1's public DataModel snapshot, with keys in their original order. */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOFloatCurveSnapshot
{
	GENERATED_BODY()

public:
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FName Name = NAME_None;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 Flags = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float DefaultValue = 0.0f;

	/** Native ERichCurveExtrapolation value. */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 PreInfinityExtrap = 0;

	/** Native ERichCurveExtrapolation value. */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 PostInfinityExtrap = 0;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	TArray<FGGYGOFloatCurveKeySnapshot> Keys;
};

/** One return value preserves failure diagnostics without a bool/out-parameter Python conversion. */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOFloatCurveReadResult
{
	GENERATED_BODY()

public:
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	bool bSucceeded = false;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	TArray<FGGYGOFloatCurveSnapshot> Curves;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	double DurationSeconds = 0.0;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString Error;
};

/** Exposes R1's validated curve values through public reflected fields. */
UCLASS()
class GGYGOEDITOR_API UGGYGOAnimationCurveSnapshotLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Calls R1 exactly once; R1 owns source lookup, validation and diagnostic text.
	 * Success copies all agreed curve/key values in requested order without conversion of precision.
	 * Failure returns false, empty curves, zero duration and the original R1 error.
	 * Values describe this call only; subsequent source edits require another explicit call.
	 * Does not expose source/model references, load or modify assets, or claim Channel/disk equivalence.
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOFloatCurveReadResult ReadFloatCurveSnapshot(
		const UAnimSequence* Source,
		const TArray<FName>& CurveNames);
};
