/** @file GGYGOCharacterShadowCapture.h
 *  @brief 原生逐帧深度捕获的角色阴影输入；配置由原角色表现入口更新。
 */
#pragma once

#include "CoreMinimal.h"
#include "GGYGOCharacterShadowCapture.generated.h"

class ADirectionalLight;
class UActorComponent;
class UMaterialInstanceDynamic;
class UMaterialInterface;
class USkeletalMeshComponent;

UENUM(BlueprintType)
enum class EGGYGOCharacterShadowMode : uint8 { CharacterTrace, DepthCaptures };

/** 由BP/配置明确提供；尺寸、空间范围和比较参数分别可调，不内置角色业务。 */
USTRUCT(BlueprintType)
struct GGYGORENDERING_API FGGYGOCharacterShadowSettings
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite) EGGYGOCharacterShadowMode Mode = EGGYGOCharacterShadowMode::CharacterTrace;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) bool bConfigured = false;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 ObjectResolution = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) int32 CascadeResolution = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) FVector4 CascadeWidthsCm = FVector4(0, 0, 0, 0);
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float DepthHalfExtentCm = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float ObjectMarginCm = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float DepthBiasCm = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float NormalBiasCm = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float FilterRadiusTexels = 0;
	UPROPERTY(EditAnywhere, BlueprintReadWrite) float Strength = 0;
	/** 显式持久输出预算；改分辨率时须同时调整预算，不静默增大配置。 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite) int64 MaxOutputBytes = 0;
};

/** 私有临时capture/RT由同一租用期拥有；无Tick、世界登记表或生产材质写入。 */
class GGYGORENDERING_API FGGYGOCharacterShadowCapture
{
public:
	FGGYGOCharacterShadowCapture();
	~FGGYGOCharacterShadowCapture();
	static bool ValidateSettings(const FGGYGOCharacterShadowSettings& Settings, FString& Reason);
	static bool ValidateMaterial(const UMaterialInterface& Material, FString& Reason);
	/** 排入原生延迟capture并更新原MID；返回不表示捕获完成或视觉验收。 */
	bool Update(UActorComponent& Owner, USkeletalMeshComponent& Mesh, const ADirectionalLight& Light,
		const FGGYGOCharacterShadowSettings& Settings, TConstArrayView<UMaterialInstanceDynamic*> Materials,
		FString& Reason);
private:
	struct FResources;
	TSharedPtr<FResources, ESPMode::ThreadSafe> Resources;
};
