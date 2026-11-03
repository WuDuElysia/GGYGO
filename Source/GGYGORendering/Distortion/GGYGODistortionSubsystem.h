/** @file GGYGODistortionSubsystem.h
 *  @brief World 内管理原 field source 的登记，并向每个 family 发布不可变输入。
 */
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GGYGODistortionSubsystem.generated.h"

class FGGYGODistortionViewExtension;
class FGGYGOSignedFieldSnapshot;
class UGGYGODistortionFieldComponent;

UCLASS()
class GGYGORENDERING_API UGGYGODistortionSubsystem : public UWorldSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	bool RegisterSource(UGGYGODistortionFieldComponent& Source, FString& OutReason);
	void UnregisterSource(const UGGYGODistortionFieldComponent& Source);
	TSharedPtr<const FGGYGOSignedFieldSnapshot, ESPMode::ThreadSafe> CreateFamilySnapshot();

protected:
	virtual bool DoesSupportWorldType(EWorldType::Type WorldType) const override;

private:
	void ReportFailure(const FString& Failure);

	// 登记不延长 FX/Actor 生命周期；family 单独持有原材质直至 graph 归还。
	TArray<TWeakObjectPtr<UGGYGODistortionFieldComponent>> Sources;
	TSharedPtr<FGGYGODistortionViewExtension, ESPMode::ThreadSafe> ViewExtension;
	FString LastFailure;
	bool bAcceptSources = false;
};
