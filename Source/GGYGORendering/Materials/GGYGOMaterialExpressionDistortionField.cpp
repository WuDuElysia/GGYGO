/** @file GGYGOMaterialExpressionDistortionField.cpp
 *  @brief 在Legacy编译器中保留原o0/o1两路float4依赖与field ShaderTag。
 */
#include "GGYGOMaterialExpressionDistortionField.h"

#if WITH_EDITOR
#include "MaterialCompiler.h"
#endif

UGGYGOMaterialExpressionDistortionField::UGGYGOMaterialExpressionDistortionField()
{
#if WITH_EDITORONLY_DATA
	bCollapsed = true;
	Outputs.Reset();
	MenuCategories.Add(NSLOCTEXT("GGYGORendering", "DistortionCategory", "GGYGO Rendering"));
#endif
}

#if WITH_EDITOR
int32 UGGYGOMaterialExpressionDistortionField::Compile(FMaterialCompiler* Compiler, int32 OutputIndex)
{
#if !GGYGO_WITH_DISTORTION_FIELD
	return Compiler->Errorf(TEXT("本构建已显式关闭Signed Distortion Field后端，不能编译field材质。"));
#else
	if (!bStreamContractConfigured || RequiredDynamicParameterComponents < 0 || RequiredDynamicParameterComponents > 65535)
	{
		return Compiler->Errorf(TEXT("Signed Distortion Field缺少该variant明确的16位DP分量合同。"));
	}
	FExpressionInput* Input = GetInput(OutputIndex);
	if (!Input || !DefaultField.GetTracedInput().Expression || !OverlayField.GetTracedInput().Expression)
	{
		return Compiler->Errorf(TEXT("Signed Distortion Field requires connected DefaultField and OverlayField float4 inputs."));
	}
	const int32 Value = Input->Compile(Compiler);
	if (Value == INDEX_NONE)
	{
		return INDEX_NONE;
	}
	if (Compiler->GetType(Value) != MCT_Float4)
	{
		return Compiler->Errorf(TEXT("Signed Distortion Field input must be float4; missing channels are not synthesized."));
	}
	return Compiler->CustomOutput(this, OutputIndex, Value);
#endif
}

void UGGYGOMaterialExpressionDistortionField::GetCaption(TArray<FString>& OutCaptions) const
{
	OutCaptions.Add(TEXT("Signed Distortion Fields (Default / Overlay RGBA)"));
}

FExpressionInput* UGGYGOMaterialExpressionDistortionField::GetInput(int32 InputIndex)
{
	switch (InputIndex)
	{
	case 0: return &DefaultField;
	case 1: return &OverlayField;
	default: return nullptr;
	}
}

FName UGGYGOMaterialExpressionDistortionField::GetInputName(int32 InputIndex) const
{
	switch (InputIndex)
	{
	case 0: return TEXT("DefaultField");
	case 1: return TEXT("OverlayField");
	default: return NAME_None;
	}
}

void UGGYGOMaterialExpressionDistortionField::GetShaderTags(TArray<FName>& ShaderTagsOut)
{
	ShaderTagsOut.AddUnique(TEXT("SignedDistortionField"));
	for (uint32 Parameter = 0; Parameter < 4; ++Parameter)
	{
		if ((uint32(RequiredDynamicParameterComponents) & (15u << (4 * Parameter))) != 0)
		{
			ShaderTagsOut.AddUnique(FName(*FString::Printf(TEXT("GGYGOSignedField.RequiresDP%u"), Parameter)));
		}
	}
}
#endif
