/** @file GGYGOCharacterLightSources.h
 *  @brief 原FX实例的瞬时Point灯事实与无Tick登记；角色原采样入口独占选灯。
 */
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "GGYGOCharacterLightSources.generated.h"

enum class EGGYGOCharacterLightSourceReadiness : uint8
{
	Ready,
	WaitingForSimulation,
	Invalid,
	/** SelectLights的外部来源本次失败；保真实错误，不使角色自身配置永久无效。 */
	SourceFailed
};

/** 与原Native LightRenderer相同的一盏当前可绘灯，不含新模拟或选择结果。 */
struct GGYGORENDERING_API FGGYGOCharacterPointLight
{
	uint64 StableKey = 0;
	FVector PositionWorldCm = FVector::ZeroVector;
	FLinearColor Color = FLinearColor::Black;
	float RadiusCm = 0;
	/** Native LightEntry.Exponent：0为inverse squared，其余值原样保留作映射依据。 */
	float NativeFalloffExponent = 0;
};

/** Getter同次从原已完成CPU数据派生，返回后不保留DataSet指针；仅本次采样有效。 */
struct GGYGORENDERING_API FGGYGOCharacterPointLightFrame
{
	uint64 InstanceId = 0;
	double SimulationAgeSeconds = 0;
	TArray<FGGYGOCharacterPointLight> Lights;
};

DECLARE_DELEGATE_RetVal_TwoParams(EGGYGOCharacterLightSourceReadiness,
	FGGYGOReadCharacterPointLights, FGGYGOCharacterPointLightFrame&, FString&);

UENUM(BlueprintType)
enum class EGGYGOCharacterFXLightMode : uint8
{
	Disabled,
	/** 用原半径映射Nap的Point衰减；保原四灯数学，非Native任意Exponent的硬件等价。 */
	NapPointFromNativeRadius
};

/** 频繁调整的来源选择/额度/亮度由角色BP提供；场景显式槽始终保留。 */
USTRUCT(BlueprintType)
struct GGYGORENDERING_API FGGYGOCharacterFXLightSelection
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite) EGGYGOCharacterFXLightMode Mode = EGGYGOCharacterFXLightMode::Disabled;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bConfigured = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 MaxLights = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float IntensityScale = 0;
};

struct GGYGORENDERING_API FGGYGOCharacterSelectedPointLight
{
	uint64 SourceHandle = 0;
	uint64 InstanceId = 0;
	double SimulationAgeSeconds = 0;
	FGGYGOCharacterPointLight Light;
	FVector4 Attenuation = FVector4(0, 0, 0, 0);
};

/** 仅持弱来源/弱Getter登记，无Tick、不缓存灯样本；FX负责在原实例结束前注销handle。 */
UCLASS()
class GGYGORENDERING_API UGGYGOCharacterLightSources final : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	bool RegisterSource(UObject* SourceOwner, uint64 OriginalInstanceId, FGGYGOReadCharacterPointLights Getter,
		uint64& OutHandle, FString& OutError);
	void UnregisterSource(uint64 Handle);
	virtual void Deinitialize() override;
	static bool ValidateSelection(const FGGYGOCharacterFXLightSelection& Configuration, FString& OutError);
	/** 只选remaining额度；来源失败返回SourceFailed，自身输入/World无效返回Invalid。
	 * 失败/等待不发半份候选；来源拥有者保原首错释放，角色可沿原Tick重新采样。
	 */
	EGGYGOCharacterLightSourceReadiness SelectLights(const FVector& PositionWorldCm, int32 RemainingSlots,
		const FGGYGOCharacterFXLightSelection& Configuration,
		TArray<FGGYGOCharacterSelectedPointLight>& OutLights, FString& OutError);
private:
	struct FSource
	{
		TWeakObjectPtr<UObject> Owner;
		uint64 InstanceId = 0;
		FGGYGOReadCharacterPointLights Getter;
	};
	TMap<uint64, FSource> Sources;
	uint64 NextHandle = 1;
};
