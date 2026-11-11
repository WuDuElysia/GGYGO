/** 通用 Boss GA 共享流程图制作；具体招式子蓝图只配资产/参数。 */
#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GGYGOBossAbilityGraphLibrary.generated.h"
class UBlueprint;
/** 原生结果值；Python不再把失败OutError吞成None。 */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOBossGraphResult
{
	GENERATED_BODY()
	FGGYGOBossGraphResult() = default;
	FGGYGOBossGraphResult(bool bValue, FString Message) : bSucceeded(bValue), Error(MoveTemp(Message)) {}
	UPROPERTY(BlueprintReadOnly)
	bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly)
	FString Error;
};
UCLASS()
class GGYGOEDITOR_API UGGYGOBossAbilityGraphLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Boss")
	static FGGYGOBossGraphResult BuildActionGraph(UBlueprint* Blueprint, bool bFlightLanding);
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Boss")
	static FGGYGOBossGraphResult ValidateActionGraph(const UBlueprint* Blueprint, bool bFlightLanding);
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Boss")
	static FGGYGOBossGraphResult BuildDeathGraph(UBlueprint* Blueprint);
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Boss")
	static FGGYGOBossGraphResult ValidateDeathGraph(const UBlueprint* Blueprint);
};
