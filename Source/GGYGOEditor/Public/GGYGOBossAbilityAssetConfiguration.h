/** @file GGYGOBossAbilityAssetConfiguration.h @brief 编辑器制作通用 GE 数据；不代运行时结算 */
#pragma once
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GameplayTagContainer.h"
#include "GGYGOBossAbilityAssetConfiguration.generated.h"
class UGameplayEffect;
class UAnimMontage;
class UGGYGOBossMeleeAbility;
/** 完整保留原生成功/失败与诊断，避免Python隐式丢弃bool/OutError。 */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOBossAssetResult
{
	GENERATED_BODY()
	FGGYGOBossAssetResult() = default;
	FGGYGOBossAssetResult(bool bValue, FString Message) : bSucceeded(bValue), Error(MoveTemp(Message)) {}
	UPROPERTY(BlueprintReadOnly)
	bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly)
	FString Error;
};
UCLASS()
class GGYGOEDITOR_API UGGYGOBossAbilityAssetConfiguration : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Boss|制作", meta = (DevelopmentOnly))
	static FGGYGOBossAssetResult ConfigureInitialAttributes(UGameplayEffect* Effect, float MaxHealth, float Health,
		float MaxPoise, float Poise);
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Boss|制作", meta = (DevelopmentOnly))
	static FGGYGOBossAssetResult ConfigureCooldown(UGameplayEffect* Effect, float Seconds, FGameplayTag Tag);
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Boss|制作")
	static FGGYGOBossAssetResult ValidateInitialAttributes(const UGameplayEffect* Effect, float MaxHealth, float Health,
		float MaxPoise, float Poise);
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Boss|制作")
	static FGGYGOBossAssetResult ValidateCooldown(const UGameplayEffect* Effect, float Seconds, FGameplayTag Tag);
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Boss|制作")
	static FGGYGOBossAssetResult ValidateRecoveryMontage(UAnimMontage* Montage, FName Slot);
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Boss|制作")
	static FGGYGOBossAssetResult ValidateAbility(const UGGYGOBossMeleeAbility* Ability);
};
