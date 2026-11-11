#include "GGYGOBossAbilityAssetConfiguration.h"
#include "AbilitySystem/Attributes/GGYGOHealthSet.h"
#include "GameplayEffect.h"
#include "GameplayEffectComponents/TargetTagsGameplayEffectComponent.h"
#include "Animation/AnimMontage.h"
#include "Animation/Data/GGYGOActionMotionSourceBinding.h"
#include "AI/Boss/Abilities/GGYGOBossMeleeAbility.h"

#include UE_INLINE_GENERATED_CPP_BY_NAME(GGYGOBossAbilityAssetConfiguration)

static bool ConfigureInitialAttributesImpl(UGameplayEffect* Effect,
	float MaxHealth, float Health, float MaxPoise, float Poise, FString& Error)
{
	if (!IsValid(Effect) || !Effect->HasAnyFlags(RF_ClassDefaultObject)
		|| !FMath::IsFinite(MaxHealth) || MaxHealth <= 0.0f || !FMath::IsFinite(Health) || Health <= 0.0f || Health > MaxHealth
		|| !FMath::IsFinite(MaxPoise) || MaxPoise < 0.0f || !FMath::IsFinite(Poise) || Poise < 0.0f || Poise > MaxPoise)
	{ Error = TEXT("初始化GE需要有效CDO及合法生命/韧性初值。"); return false; }
	Effect->Modify();
	Effect->DurationPolicy = EGameplayEffectDurationType::Instant;
	Effect->Modifiers.Reset();
	const auto Add = [Effect](FGameplayAttribute Attribute, float Value)
	{
		FGameplayModifierInfo Modifier;
		Modifier.Attribute = Attribute;
		Modifier.ModifierOp = EGameplayModOp::Override;
		Modifier.ModifierMagnitude = FScalableFloat(Value);
		Effect->Modifiers.Add(Modifier);
	};
	Add(UGGYGOHealthSet::GetMaxHealthAttribute(), MaxHealth);
	Add(UGGYGOHealthSet::GetHealthAttribute(), Health);
	Add(UGGYGOHealthSet::GetMaxPoiseAttribute(), MaxPoise);
	Add(UGGYGOHealthSet::GetPoiseAttribute(), Poise);
	Error.Reset();
	return true;
}

static bool ConfigureCooldownImpl(UGameplayEffect* Effect,
	float Seconds, FGameplayTag Tag, FString& Error)
{
	if (!IsValid(Effect) || !Effect->HasAnyFlags(RF_ClassDefaultObject) || !FMath::IsFinite(Seconds) || Seconds <= 0.0f || !Tag.IsValid())
	{ Error = TEXT("冷却GE需要有效CDO、正时长及具名冷却Tag。"); return false; }
	Effect->Modify();
	Effect->DurationPolicy = EGameplayEffectDurationType::HasDuration;
	Effect->DurationMagnitude = FScalableFloat(Seconds);
	FInheritedTagContainer Tags;
	Tags.Added.AddTag(Tag);
	Effect->FindOrAddComponent<UTargetTagsGameplayEffectComponent>().SetAndApplyTargetTagChanges(Tags);
	Error.Reset();
	return true;
}

static bool ValidateInitialAttributesImpl(const UGameplayEffect* Effect,
	float MaxHealth, float Health, float MaxPoise, float Poise, FString& Error)
{
	if (!IsValid(Effect) || Effect->DurationPolicy != EGameplayEffectDurationType::Instant || Effect->Modifiers.Num() != 4)
	{ Error = TEXT("实际初始化GE不是四项即时Modifier。"); return false; }
	const FGameplayAttribute Attributes[] = {UGGYGOHealthSet::GetMaxHealthAttribute(), UGGYGOHealthSet::GetHealthAttribute(),
		UGGYGOHealthSet::GetMaxPoiseAttribute(), UGGYGOHealthSet::GetPoiseAttribute()};
	const float Values[] = {MaxHealth, Health, MaxPoise, Poise};
	for (int32 Index = 0; Index < 4; ++Index)
	{
		const FGameplayModifierInfo& Modifier = Effect->Modifiers[Index];
		float Value = 0.0f;
		if (Modifier.Attribute != Attributes[Index] || Modifier.ModifierOp != EGameplayModOp::Override
			|| !Modifier.ModifierMagnitude.GetStaticMagnitudeIfPossible(1.0f, Value) || Value != Values[Index])
		{ Error = FString::Printf(TEXT("初始化GE实际Modifier[%d]不匹配。"), Index); return false; }
	}
	Error.Reset(); return true;
}

static bool ValidateCooldownImpl(const UGameplayEffect* Effect,
	float Seconds, FGameplayTag Tag, FString& Error)
{
	float Duration = 0.0f;
	if (!IsValid(Effect) || Effect->DurationPolicy != EGameplayEffectDurationType::HasDuration
		|| !Effect->DurationMagnitude.GetStaticMagnitudeIfPossible(1.0f, Duration) || Duration != Seconds
		|| Effect->GetGrantedTags().Num() != 1 || !Effect->GetGrantedTags().HasTagExact(Tag))
	{ Error = TEXT("实际冷却GE时长或唯一授予Tag不匹配。"); return false; }
	Error.Reset(); return true;
}

static bool ValidateRecoveryMontageImpl(UAnimMontage* Montage, FName Slot, FString& Error)
{
	if (!IsValid(Montage) || Montage->HasRootMotion() || Montage->CompositeSections.Num() != 1
		|| Montage->GetSectionName(0) != TEXT("Main") || Montage->SlotAnimTracks.Num() != 1
		|| Montage->GetAnimCompositeSection(0).GetTime() != 0.0f || !Montage->GetAnimCompositeSection(0).NextSectionName.IsNone()
		|| Montage->SlotAnimTracks[0].SlotName != Slot || !FMath::IsFinite(Montage->GetPlayLength()) || Montage->GetPlayLength() <= 0.0f)
	{ Error = TEXT("纯姿态收尾需要有效完整单Main/Slot、正时长且禁用RootMotion；不要求或执行XYZ。"); return false; }
	// 只验证原姿态时间映射；不要求XYZ曲线，也不交CMC执行。
	FGGYGOActionMotionSourceBindingPtr Source;
	return GGYGOActionMotionSource::BuildSourceBinding(Montage, Slot, TEXT("Main"), Source, Error);
}

static bool ValidateAbilityImpl(const UGGYGOBossMeleeAbility* Ability, FString& Error)
{
	if (!IsValid(Ability) || !Ability->HasAnyFlags(RF_ClassDefaultObject))
	{ Error = TEXT("需要实际Boss能力CDO。"); return false; }
	return Ability->ValidateMeleeConfiguration(Error);
}

FGGYGOBossAssetResult UGGYGOBossAbilityAssetConfiguration::ConfigureInitialAttributes(UGameplayEffect* Effect, float MaxHealth, float Health, float MaxPoise, float Poise)
{
	FString Error;
	const bool bSuccess = ConfigureInitialAttributesImpl(Effect, MaxHealth, Health, MaxPoise, Poise, Error);
	return {bSuccess, MoveTemp(Error)};
}

FGGYGOBossAssetResult UGGYGOBossAbilityAssetConfiguration::ConfigureCooldown(UGameplayEffect* Effect, float Seconds, FGameplayTag Tag)
{
	FString Error;
	const bool bSuccess = ConfigureCooldownImpl(Effect, Seconds, Tag, Error);
	return {bSuccess, MoveTemp(Error)};
}

FGGYGOBossAssetResult UGGYGOBossAbilityAssetConfiguration::ValidateInitialAttributes(const UGameplayEffect* Effect, float MaxHealth, float Health, float MaxPoise, float Poise)
{
	FString Error;
	const bool bSuccess = ValidateInitialAttributesImpl(Effect, MaxHealth, Health, MaxPoise, Poise, Error);
	return {bSuccess, MoveTemp(Error)};
}

FGGYGOBossAssetResult UGGYGOBossAbilityAssetConfiguration::ValidateCooldown(const UGameplayEffect* Effect, float Seconds, FGameplayTag Tag)
{
	FString Error;
	const bool bSuccess = ValidateCooldownImpl(Effect, Seconds, Tag, Error);
	return {bSuccess, MoveTemp(Error)};
}

FGGYGOBossAssetResult UGGYGOBossAbilityAssetConfiguration::ValidateRecoveryMontage(UAnimMontage* Montage, FName Slot)
{
	FString Error;
	const bool bSuccess = ValidateRecoveryMontageImpl(Montage, Slot, Error);
	return {bSuccess, MoveTemp(Error)};
}

FGGYGOBossAssetResult UGGYGOBossAbilityAssetConfiguration::ValidateAbility(const UGGYGOBossMeleeAbility* Ability)
{
	FString Error;
	const bool bSuccess = ValidateAbilityImpl(Ability, Error);
	return {bSuccess, MoveTemp(Error)};
}
