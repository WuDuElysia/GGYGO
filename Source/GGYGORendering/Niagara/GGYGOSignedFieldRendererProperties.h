/** @file GGYGOSignedFieldRendererProperties.h
 *  @brief 原Niagara系统内的双场renderer配置；角色差异与输入契约由资产明确提供。
 */
#pragma once

#include "CoreMinimal.h"
#include "NiagaraMeshRendererProperties.h"
#include "NiagaraSpriteRendererProperties.h"
#include "GGYGOSignedFieldRendererProperties.generated.h"

UENUM(BlueprintType)
enum class EGGYGOSignedFieldTransformOwner : uint8
{
	Unconfigured,
	/** VF提供未补偿native基底；原材质唯一处理affine/法线/pivot/viewport。 */
	MaterialWorldPositionOffset
};

UENUM(BlueprintType)
enum class EGGYGOSignedFieldSpriteBasis : uint8
{
	Unconfigured,
	NativeViewPlane,
	NativeVelocityAligned,
	CameraPositionWithViewRoll
};

/** 每个真实geometry variant单独配置，不由源MID或首批样本推断streams。 */
USTRUCT(BlueprintType)
struct GGYGORENDERING_API FGGYGOSignedFieldStreamContract
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Contract")
	bool bConfigured = false;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Contract")
	FString SourceReference;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Contract")
	EGGYGOSignedFieldTransformOwner TransformOwner = EGGYGOSignedFieldTransformOwner::Unconfigured;

	/** DP0..3每项四个分量，共16位；只检查真实源材质使用的分量，不补零伪造流。 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Contract", meta=(ClampMin="0", ClampMax="65535"))
	int32 RequiredDynamicParameterComponents = 0;

	/** 原geometry/affine的保守bound来源；不以固定大bounds替代生产者。 */
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Source Contract")
	FString BoundsReference;

	bool Validate(FString& OutReason) const;
};

/** 保留原Mesh属性/变量绑定与calculator；只替换renderer和双MRT绘制接缝。 */
UCLASS(EditInlineNew, BlueprintType, meta=(DisplayName="GGYGO Signed Field Mesh Renderer"))
class GGYGORENDERING_API UGGYGOSignedFieldMeshRendererProperties final : public UNiagaraMeshRendererProperties
{
	GENERATED_BODY()
public:
	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Signed Field")
	FGGYGOSignedFieldStreamContract FieldStreams;

	virtual FNiagaraRenderer* CreateEmitterRenderer(ERHIFeatureLevel::Type FeatureLevel,
		const FNiagaraEmitterInstance* Emitter, const FNiagaraSystemInstanceController& Controller) override;
	virtual void ForEachMesh(FNiagaraSystemInstance* SystemInstance, TFunction<void(int32)> NumMeshes,
		TFunction<void(const FNiagaraMeshRendererMeshProperties&)> Iterate) const override;
	virtual const FVertexFactoryType* GetVertexFactoryType() const override;
	virtual void CollectPSOPrecacheData(const FNiagaraEmitterInstance* Emitter, FPSOPrecacheParamsList& OutParams) const override;
	bool ValidateFieldConfiguration(FString& OutReason) const;
};

/** Stretch/Billboard共享原粒子流；实际基底明确配置，signed尺寸/pivot修正仍属WPO。 */
UCLASS(EditInlineNew, BlueprintType, meta=(DisplayName="GGYGO Signed Field Sprite Renderer"))
class GGYGORENDERING_API UGGYGOSignedFieldSpriteRendererProperties final : public UNiagaraSpriteRendererProperties
{
	GENERATED_BODY()
public:
	UGGYGOSignedFieldSpriteRendererProperties();

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Signed Field")
	FGGYGOSignedFieldStreamContract FieldStreams;

	UPROPERTY(EditAnywhere, BlueprintReadOnly, Category="Signed Field")
	EGGYGOSignedFieldSpriteBasis FieldBasis = EGGYGOSignedFieldSpriteBasis::Unconfigured;

	virtual FNiagaraRenderer* CreateEmitterRenderer(ERHIFeatureLevel::Type FeatureLevel,
		const FNiagaraEmitterInstance* Emitter, const FNiagaraSystemInstanceController& Controller) override;
	virtual const FVertexFactoryType* GetVertexFactoryType() const override;
	virtual void CollectPSOPrecacheData(const FNiagaraEmitterInstance* Emitter, FPSOPrecacheParamsList& OutParams) const override;
	bool ValidateFieldConfiguration(FString& OutReason) const;
};
