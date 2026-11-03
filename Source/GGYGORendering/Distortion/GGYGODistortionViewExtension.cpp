/** @file GGYGODistortionViewExtension.cpp
 *  @brief 项目双场的公开View入口和完整default→overlay合成；不使用Renderer私有运行布局。
 */
#include "GGYGODistortionViewExtension.h"
#include "GGYGODistortionSubsystem.h"
#include "PostProcess/PostProcessMaterialInputs.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGOSignedFieldFamily.h"
#include "GlobalShader.h"
#include "PixelShaderUtils.h"
#include "RenderGraphBuilder.h"
#include "RenderGraphUtils.h"
#include "SceneTexturesConfig.h"
#include "ScreenPass.h"
#include "ShaderParameterStruct.h"

namespace
{
class FGGYGODistortionCompositePS final : public FGlobalShader
{
public:
	DECLARE_GLOBAL_SHADER(FGGYGODistortionCompositePS);
	SHADER_USE_PARAMETER_STRUCT(FGGYGODistortionCompositePS, FGlobalShader);
	BEGIN_SHADER_PARAMETER_STRUCT(FParameters, )
		SHADER_PARAMETER(FVector2f, OutputViewMin)
		SHADER_PARAMETER(FVector2f, OutputViewInvSize)
		SHADER_PARAMETER(FVector3f, RGBShift)
		SHADER_PARAMETER_RDG_TEXTURE(Texture2D, SceneTexture)
		SHADER_PARAMETER_RDG_TEXTURE(Texture2D, FieldTexture)
		SHADER_PARAMETER_SAMPLER(SamplerState, SceneSampler)
		SHADER_PARAMETER_SAMPLER(SamplerState, FieldSampler)
		RENDER_TARGET_BINDING_SLOTS()
	END_SHADER_PARAMETER_STRUCT()
	static bool ShouldCompilePermutation(const FGlobalShaderPermutationParameters& Parameters)
	{
		return !IsMobilePlatform(Parameters.Platform)
			&& IsFeatureLevelSupported(Parameters.Platform, ERHIFeatureLevel::SM5);
	}
};
IMPLEMENT_GLOBAL_SHADER(FGGYGODistortionCompositePS,
	"/GGYGORendering/Private/GGYGODistortionComposite.usf", "MainPS", SF_Pixel);

FRDGTextureRef CropViewport(FRDGBuilder& GraphBuilder, FScreenPassTexture Input, const TCHAR* Name)
{
	if (Input.ViewRect.Min == FIntPoint::ZeroValue && Input.ViewRect.Size() == Input.Texture->Desc.Extent)
	{
		return Input.Texture;
	}
	const FRDGTextureDesc Desc = FRDGTextureDesc::Create2D(Input.ViewRect.Size(), Input.Texture->Desc.Format,
		FClearValueBinding::None, TexCreate_ShaderResource | TexCreate_RenderTargetable);
	FRDGTextureRef Cropped = GraphBuilder.CreateTexture(Desc, Name);
	AddCopyTexturePass(GraphBuilder, Input.Texture, Cropped, Input.ViewRect.Min,
		FIntPoint::ZeroValue, Input.ViewRect.Size());
	return Cropped;
}

FScreenPassTexture CompositeOne(FRDGBuilder& GraphBuilder, const FSceneView& View,
	FScreenPassTexture Scene, FScreenPassTexture Field, const FVector3f& RGBShift,
	const FGGYGODistortionViewPolicy& Policy, const TCHAR* Name)
{
	FRDGTextureRef SceneViewport = CropViewport(GraphBuilder, Scene, TEXT("GGYGO.Field.SceneViewport"));
	FRDGTextureRef FieldViewport = CropViewport(GraphBuilder, Field, TEXT("GGYGO.Field.FieldViewport"));
	const FRDGTextureDesc Desc = FRDGTextureDesc::Create2D(Scene.Texture->Desc.Extent,
		Scene.Texture->Desc.Format, FClearValueBinding::None, TexCreate_ShaderResource | TexCreate_RenderTargetable);
	FRDGTextureRef Output = GraphBuilder.CreateTexture(Desc, Name);
	auto* Parameters = GraphBuilder.AllocParameters<FGGYGODistortionCompositePS::FParameters>();
	Parameters->OutputViewMin = FVector2f(Scene.ViewRect.Min);
	Parameters->OutputViewInvSize = FVector2f(1.0f / Scene.ViewRect.Width(), 1.0f / Scene.ViewRect.Height());
	Parameters->RGBShift = RGBShift;
	Parameters->SceneTexture = SceneViewport;
	Parameters->FieldTexture = FieldViewport;
	Parameters->SceneSampler = Policy.SceneSampler;
	Parameters->FieldSampler = Policy.FieldSampler;
	Parameters->RenderTargets[0] = FRenderTargetBinding(Output, ERenderTargetLoadAction::ENoAction);
	TShaderMapRef<FGGYGODistortionCompositePS> Shader(GetGlobalShaderMap(View.GetFeatureLevel()));
	FPixelShaderUtils::AddFullscreenPass(GraphBuilder, GetGlobalShaderMap(View.GetFeatureLevel()),
		RDG_EVENT_NAME("GGYGO Complete RGB Field Composite"), Shader, Parameters, Scene.ViewRect);
	return FScreenPassTexture(Output, Scene.ViewRect);
}
}
#endif

DEFINE_LOG_CATEGORY_STATIC(LogGGYGOFieldComposite, Log, All);

FGGYGODistortionViewExtension::FGGYGODistortionViewExtension(const FAutoRegister& AutoRegister,
	UGGYGODistortionSubsystem* InSubsystem)
	: FWorldSceneViewExtension(AutoRegister, InSubsystem->GetWorld()), Subsystem(InSubsystem) {}

void FGGYGODistortionViewExtension::SetupViewFamily(FSceneViewFamily& Family)
{
#if GGYGO_WITH_DISTORTION_FIELD
	check(IsInGameThread());
	UGGYGODistortionSubsystem* Owner = Subsystem.Get();
	if (!Owner) { return; }
	const auto Snapshot = Owner->CreateFamilySnapshot();
	if (Subsystem.Get() != Owner || !Snapshot) { return; }
	Family.GetOrCreateExtentionData<FGGYGOSignedFieldFamily>()->InitializeOnce(Snapshot.ToSharedRef());
#endif
}

void FGGYGODistortionViewExtension::PreRenderView_RenderThread(FRDGBuilder& GraphBuilder, FSceneView& View)
{
#if GGYGO_WITH_DISTORTION_FIELD
	if (View.Family)
	{
		if (const auto* Family = View.Family->GetExtentionData<FGGYGOSignedFieldFamily>())
		{
			Family->BeginView(GraphBuilder, View);
		}
	}
#endif
}

void FGGYGODistortionViewExtension::SubscribeToPostProcessingPass(EPostProcessingPass Pass,
	const FSceneView& View, FPostProcessingPassDelegateArray& Callbacks, bool bIsPassEnabled)
{
#if GGYGO_WITH_DISTORTION_FIELD
	check(IsInRenderingThread());
	const auto* Family = View.Family ? View.Family->GetExtentionData<FGGYGOSignedFieldFamily>() : nullptr;
	const auto* Policy = Family ? Family->GetPolicy() : nullptr;
	if (Pass == EPostProcessingPass::BeforeDOF && bIsPassEnabled && Policy
		&& Policy->Stage == EGGYGODistortionStage::BeforeDOF)
	{
		Callbacks.Add(FPostProcessingPassDelegate::CreateRaw(this, &FGGYGODistortionViewExtension::CompositeBeforeDOF));
	}
#endif
}

FScreenPassTexture FGGYGODistortionViewExtension::CompositeBeforeDOF(FRDGBuilder& GraphBuilder,
	const FSceneView& View, const FPostProcessMaterialInputs& Inputs)
{
	check(IsInRenderingThread());
	FScreenPassTexture Output;
	FString Failure;
	if (TryCompositeView(GraphBuilder, View, Inputs, Output, Failure))
	{
		LastCompositeFailure.Reset();
		return Output;
	}
	if (Failure != LastCompositeFailure)
	{
		UE_LOG(LogGGYGOFieldComposite, Error, TEXT("双场未合成：%s"), *Failure);
		LastCompositeFailure = Failure;
	}
	// 后处理失败保留原场景和诊断，field几何仍由原专属通路持有。
	return Inputs.ReturnUntouchedSceneColorForPostProcessing(GraphBuilder);
}

bool FGGYGODistortionViewExtension::TryCompositeView(FRDGBuilder& GraphBuilder, const FSceneView& View,
	const FPostProcessMaterialInputs& Inputs, FScreenPassTexture& OutColor, FString& OutReason) const
{
#if GGYGO_WITH_DISTORTION_FIELD
	const FGGYGOSignedFieldFamily* Family = View.Family
		? View.Family->GetExtentionData<FGGYGOSignedFieldFamily>() : nullptr;
	const FGGYGODistortionViewPolicy* Policy = Family ? Family->GetPolicy() : nullptr;
	const FScreenPassTextureSlice Input = Inputs.GetInput(EPostProcessMaterialInput::SceneColor);
	if (!Family || !Policy || !Input.IsValid() || !Inputs.SceneTextures.SceneTextures
		|| !Policy->SceneSampler.IsValid() || !Policy->FieldSampler.IsValid())
	{
		OutReason = TEXT("原family/策略/场景slice/深度或真实sampler尚未就绪");
		return false;
	}
	FRDGTextureRef Depth = Inputs.SceneTextures.SceneTextures->GetParameters()->SceneDepthTexture;
	FGGYGOSignedFieldTextures Fields;
	if (!Family->Accumulate(GraphBuilder, View, Inputs.SceneTextures.SceneTextures.GetUniformBuffer(), Depth, Input.ViewRect, Fields, OutReason))
	{
		return false;
	}
	if (!Fields.Default && !Fields.Overlay)
	{
		OutColor = Inputs.ReturnUntouchedSceneColorForPostProcessing(GraphBuilder);
		return true;
	}
	check(Fields.Default && Fields.Overlay);
	// 合成前保持输入slice的ViewRect；最终输出阶段才使用OverrideOutput。
	FScreenPassTexture Scene = FScreenPassTexture::CopyFromSlice(GraphBuilder, Input);
	Scene = CompositeOne(GraphBuilder, View, Scene, FScreenPassTexture(Fields.Default, Input.ViewRect),
		Policy->DefaultRGBShift, *Policy, TEXT("GGYGO.Field.DefaultComposite"));
	Scene = CompositeOne(GraphBuilder, View, Scene, FScreenPassTexture(Fields.Overlay, Input.ViewRect),
		Policy->OverlayRGBShift, *Policy, TEXT("GGYGO.Field.OverlayComposite"));
	if (Inputs.OverrideOutput.IsValid())
	{
		if (Scene.ViewRect.Size() != Inputs.OverrideOutput.ViewRect.Size())
		{
			OutReason = TEXT("field输出与原pass OverrideOutput的像素范围不一致");
			return false;
		}
		AddCopyTexturePass(GraphBuilder, Scene.Texture, Inputs.OverrideOutput.Texture, Scene.ViewRect.Min,
			Inputs.OverrideOutput.ViewRect.Min, Scene.ViewRect.Size());
		Scene = FScreenPassTexture(Inputs.OverrideOutput.Texture, Inputs.OverrideOutput.ViewRect);
	}
	OutColor = Scene;
	OutReason.Reset();
	return true;
#else
	OutReason = TEXT("本构建已显式关闭field，不执行或注册合成");
	return false;
#endif
}

void FGGYGODistortionViewExtension::DetachSubsystem() { Subsystem.Reset(); }
