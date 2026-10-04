// Copyright Epic Games, Inc. All Rights Reserved.

#pragma once

#include "CoreMinimal.h"
#include "Animation/AnimCurveTypes.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GGYGOAnimationCurveReadLibrary.generated.h"

class UAnimSequence;

/** Read-only snapshots of curves supplied by an animation's current public DataModel. */
UCLASS()
class GGYGOEDITOR_API UGGYGOAnimationCurveReadLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * Copies complete float curves in requested order and reads the source play length.
	 * Empty curves, finite negative values/times, native None modes and MAX_flt defaults are preserved.
	 * Failure clears curves/duration and reports the object, curve/key and invalid field where applicable.
	 * Does not load, modify or save assets, and does not claim the underlying Channel or disk bytes match.
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static bool ReadFloatCurves(
		const UAnimSequence* Source,
		const TArray<FName>& CurveNames,
		TArray<FFloatCurve>& OutCurves,
		double& OutDurationSeconds,
		FString& OutError);
};
