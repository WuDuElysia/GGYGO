/** @file GGYGODistortionProfile.h
 *  @brief World/View公共失真配置；项目移植选择与原运行证据分别记录。
 */
#pragma once

#include "CoreMinimal.h"
#include "Engine/DataAsset.h"
#include "GGYGODistortionProfile.generated.h"

struct FGGYGODistortionViewPolicy;
struct FSamplerStateInitializerRHI;

UENUM(BlueprintType)
enum class EGGYGODistortionPolicyMode : uint8 { Unconfigured, ProjectConfigured, SourceRuntimeVerified };

UENUM(BlueprintType)
enum class EGGYGODistortionPrecision : uint8 { Unknown, Float16RGBA, Float32RGBA };

UENUM(BlueprintType)
enum class EGGYGODistortionStage : uint8 { Unknown, AfterNativeDistortionMerge, BeforeDOF };

UENUM(BlueprintType)
enum class EGGYGODistortionOrder : uint8 { Unconfigured, DefaultThenOverlay };

UENUM(BlueprintType)
enum class EGGYGODistortionFilter : uint8 { Unknown, Point, Bilinear, Trilinear };

UENUM(BlueprintType)
enum class EGGYGODistortionAddress : uint8 { Unknown, Wrap, Clamp, Mirror, Border };

UENUM(BlueprintType)
enum class EGGYGODistortionMipPolicy : uint8 { Unconfigured, ExplicitMipZero };

UENUM(BlueprintType)
enum class EGGYGODistortionViewportBinding : uint8 { Unconfigured, CurrentViewRect };

UENUM(BlueprintType)
enum class EGGYGODistortionDepthBinding : uint8 { Unconfigured, CurrentMainViewHardOcclusion };

UENUM(BlueprintType)
enum class EGGYGODistortionFieldEncoding : uint8 { Unconfigured, RawSignedRGBA };

/** 明确的二维采样器；SourceEvidence只在原运行已证模式要求。 */
USTRUCT(BlueprintType)
struct FGGYGODistortionSampler
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sampler")
	EGGYGODistortionFilter Filter = EGGYGODistortionFilter::Unknown;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sampler")
	EGGYGODistortionAddress AddressU = EGGYGODistortionAddress::Unknown;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sampler")
	EGGYGODistortionAddress AddressV = EGGYGODistortionAddress::Unknown;

	/** Border模式的明确RGBA8颜色；Clamp/Wrap不使用此值。 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Sampler")
	FColor BorderColor = FColor::Black;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Source Runtime Evidence")
	FString SourceEvidence;
};

/** 常改值留在资产；同一World显式使用同一Profile，不从缺证据自动切换模式。 */
UCLASS(BlueprintType)
class GGYGORENDERING_API UGGYGODistortionProfile : public UDataAsset
{
	GENERATED_BODY()

public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Policy")
	EGGYGODistortionPolicyMode PolicyMode = EGGYGODistortionPolicyMode::Unconfigured;

	/** 项目移植模式的明确决定入口；不表示原版运行provider已证。 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Policy")
	FString ConfigurationReference;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Distortion")
	EGGYGODistortionPrecision Precision = EGGYGODistortionPrecision::Unknown;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString PrecisionEvidence;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Distortion")
	FVector DefaultRGBShift = FVector::ZeroVector;

	/** 零也是合法艺术选择，但须显式确认已配置，不能把默认零当就绪。 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Distortion")
	bool bDefaultRGBShiftConfigured = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Distortion")
	FVector OverlayRGBShift = FVector::ZeroVector;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Distortion")
	bool bOverlayRGBShiftConfigured = false;

	/** 两路各自求和、各自采样，不能先将两张场相加。 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Distortion")
	EGGYGODistortionOrder Order = EGGYGODistortionOrder::Unconfigured;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString DefaultRGBShiftEvidence;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString OverlayRGBShiftEvidence;

	/** 原运行模式必须另有default消费者及两路先后关系的证据。 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString DefaultConsumerEvidence;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString OrderEvidence;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Distortion")
	FGGYGODistortionSampler SceneSampler;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Distortion")
	FGGYGODistortionSampler FieldSampler;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Distortion")
	EGGYGODistortionStage Stage = EGGYGODistortionStage::Unknown;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Bindings")
	EGGYGODistortionMipPolicy MipPolicy = EGGYGODistortionMipPolicy::Unconfigured;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Bindings")
	EGGYGODistortionViewportBinding ViewportBinding = EGGYGODistortionViewportBinding::Unconfigured;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Bindings")
	EGGYGODistortionDepthBinding DepthBinding = EGGYGODistortionDepthBinding::Unconfigured;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Bindings")
	EGGYGODistortionFieldEncoding FieldEncoding = EGGYGODistortionFieldEncoding::Unconfigured;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString StageEvidence;

	/** 原运行scene/field采样等价证据；不用于producer全部纹理。 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString MipZeroEvidence;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString DepthSnapshotEvidence;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString ViewportMappingEvidence;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Runtime Evidence")
	FString FieldEncodingEvidence;

	/** GT纯配置校验；不要求World/RHI，不创建采样器，不认证实际材质或画面。 */
	UFUNCTION(BlueprintCallable, Category="Distortion|Validation")
	bool ValidateConfiguration(FString& OutReason) const;

	/** GT生成含真实RHI采样器的不可变策略；失败不给可用策略。 */
	bool TryBuildPolicy(FGGYGODistortionViewPolicy& OutPolicy, FString& OutReason) const;

private:
	bool TryBuildParameters(FSamplerStateInitializerRHI& OutSceneSampler,
		FSamplerStateInitializerRHI& OutFieldSampler, FString& OutReason) const;
};
