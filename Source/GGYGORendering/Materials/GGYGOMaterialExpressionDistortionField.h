/** @file GGYGOMaterialExpressionDistortionField.h
 *  @brief 原default与overlay各自输出完整signed RGBA，保留两路编译依赖。
 */
#pragma once

#include "CoreMinimal.h"
#include "MaterialExpressionIO.h"
#include "MaterialValueType.h"
#include "Materials/MaterialExpressionCustomOutput.h"
#include "GGYGOMaterialExpressionDistortionField.generated.h"

UCLASS(CollapseCategories, HideCategories=Object)
class GGYGORENDERING_API UGGYGOMaterialExpressionDistortionField : public UMaterialExpressionCustomOutput
{
	GENERATED_BODY()

public:
	UGGYGOMaterialExpressionDistortionField();

	UPROPERTY(meta=(RequiredInput="true"))
	FExpressionInput DefaultField;

	UPROPERTY(meta=(RequiredInput="true"))
	FExpressionInput OverlayField;

	/** 来源为与该材质geometry variant相同的FieldStreams合同，未配置不能编译为field。 */
	UPROPERTY(EditAnywhere, Category="Source Contract")
	bool bStreamContractConfigured = false;

	UPROPERTY(EditAnywhere, Category="Source Contract", meta=(ClampMin="0", ClampMax="65535"))
	int32 RequiredDynamicParameterComponents = 0;

	virtual int32 GetNumOutputs() const override { return 2; }
	virtual int32 GetMaxOutputs() const override { return 2; }
	virtual FString GetFunctionName() const override { return TEXT("GetSignedDistortionField"); }
	virtual FString GetDisplayName() const override { return TEXT("Signed Distortion Field"); }
#if WITH_EDITOR
	virtual int32 Compile(FMaterialCompiler* Compiler, int32 OutputIndex) override;
	virtual void GetCaption(TArray<FString>& OutCaptions) const override;
	virtual FExpressionInput* GetInput(int32 InputIndex) override;
	virtual FName GetInputName(int32 InputIndex) const override;
	virtual EMaterialValueType GetInputValueType(int32 InputIndex) override { return MCT_Float4; }
	virtual void GetShaderTags(TArray<FName>& ShaderTagsOut) override;
#endif
};
