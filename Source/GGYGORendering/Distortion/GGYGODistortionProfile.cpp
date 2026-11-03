/** @file GGYGODistortionProfile.cpp
 *  @brief 按明确来源模式校验同一组配置，不把项目移植标作原运行已证。
 */
#include "GGYGODistortionProfile.h"

#include "RHI.h"
#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGODistortionRenderTypes.h"
#include "DynamicRHI.h"
#include "RHICommandList.h"
#endif

namespace
{
bool HasReference(const FString& Reference)
{
	return !Reference.TrimStartAndEnd().IsEmpty();
}

bool TryAddress(EGGYGODistortionAddress Address, ESamplerAddressMode& OutAddress)
{
	switch (Address)
	{
	case EGGYGODistortionAddress::Wrap: OutAddress = AM_Wrap; return true;
	case EGGYGODistortionAddress::Clamp: OutAddress = AM_Clamp; return true;
	case EGGYGODistortionAddress::Mirror: OutAddress = AM_Mirror; return true;
	case EGGYGODistortionAddress::Border: OutAddress = AM_Border; return true;
	default: return false;
	}
}

bool TrySampler(const FGGYGODistortionSampler& Source, bool bRequireSourceEvidence,
	FSamplerStateInitializerRHI& OutSampler)
{
	ESamplerFilter Filter;
	switch (Source.Filter)
	{
	case EGGYGODistortionFilter::Point: Filter = SF_Point; break;
	case EGGYGODistortionFilter::Bilinear: Filter = SF_Bilinear; break;
	case EGGYGODistortionFilter::Trilinear: Filter = SF_Trilinear; break;
	default: return false;
	}
	ESamplerAddressMode U, V;
	if ((bRequireSourceEvidence && !HasReference(Source.SourceEvidence))
		|| !TryAddress(Source.AddressU, U) || !TryAddress(Source.AddressV, V))
	{
		return false;
	}
	// 两种模式均显式选择LOD0；只有原运行模式另要求此选择的源等价证据。
	OutSampler = FSamplerStateInitializerRHI(Filter, U, V, AM_Clamp,
		0.0f, 0, 0.0f, 0.0f, Source.BorderColor.ToPackedARGB());
	return true;
}
}

bool UGGYGODistortionProfile::TryBuildParameters(FSamplerStateInitializerRHI& OutSceneSampler,
	FSamplerStateInitializerRHI& OutFieldSampler, FString& OutReason) const
{
	check(IsInGameThread());
	OutReason.Reset();
	switch (PolicyMode)
	{
	case EGGYGODistortionPolicyMode::ProjectConfigured:
		if (!HasReference(ConfigurationReference))
		{
			OutReason = TEXT("项目移植配置缺少明确决定入口");
			return false;
		}
		break;
	case EGGYGODistortionPolicyMode::SourceRuntimeVerified:
		break;
	default:
		OutReason = TEXT("未明确选择失真策略来源模式");
		return false;
	}
	const bool bRequireSourceEvidence = PolicyMode == EGGYGODistortionPolicyMode::SourceRuntimeVerified;
	if (bRequireSourceEvidence && (!HasReference(PrecisionEvidence)
		|| !HasReference(DefaultRGBShiftEvidence) || !HasReference(OverlayRGBShiftEvidence)
		|| !HasReference(DefaultConsumerEvidence) || !HasReference(OrderEvidence)
		|| !HasReference(StageEvidence) || !HasReference(MipZeroEvidence) || !HasReference(DepthSnapshotEvidence)
		|| !HasReference(ViewportMappingEvidence) || !HasReference(FieldEncodingEvidence)))
	{
		OutReason = TEXT("原运行已证模式的实际证据缺失；不会自动切换项目移植模式");
		return false;
	}
	switch (Precision)
	{
	case EGGYGODistortionPrecision::Float16RGBA:
	case EGGYGODistortionPrecision::Float32RGBA: break;
	default: OutReason = TEXT("field RT 精度未明确配置或不支持"); return false;
	}
	const FVector3f DefaultShift(DefaultRGBShift);
	const FVector3f OverlayShift(OverlayRGBShift);
	if (!bDefaultRGBShiftConfigured || !bOverlayRGBShiftConfigured
		|| DefaultRGBShift.ContainsNaN() || DefaultShift.ContainsNaN()
		|| OverlayRGBShift.ContainsNaN() || OverlayShift.ContainsNaN())
	{
		OutReason = TEXT("default / overlay RGBShift 未显式配置或含非有限数");
		return false;
	}
	if (Stage != EGGYGODistortionStage::BeforeDOF
		|| Order != EGGYGODistortionOrder::DefaultThenOverlay
		|| MipPolicy != EGGYGODistortionMipPolicy::ExplicitMipZero
		|| DepthBinding != EGGYGODistortionDepthBinding::CurrentMainViewHardOcclusion
		|| ViewportBinding != EGGYGODistortionViewportBinding::CurrentViewRect
		|| FieldEncoding != EGGYGODistortionFieldEncoding::RawSignedRGBA)
	{
		OutReason = TEXT("stage / LOD / current-view depth / viewport UV / raw field绑定合同未明确配置");
		return false;
	}
	if (!TrySampler(SceneSampler, bRequireSourceEvidence, OutSceneSampler)
		|| !TrySampler(FieldSampler, bRequireSourceEvidence, OutFieldSampler))
	{
		OutReason = TEXT("scene / field sampler未明确配置，或原运行模式缺采样器证据");
		return false;
	}
	return true;
}

bool UGGYGODistortionProfile::ValidateConfiguration(FString& OutReason) const
{
	FSamplerStateInitializerRHI SceneState, FieldState;
	return TryBuildParameters(SceneState, FieldState, OutReason);
}

bool UGGYGODistortionProfile::TryBuildPolicy(FGGYGODistortionViewPolicy& OutPolicy, FString& OutReason) const
{
#if GGYGO_WITH_DISTORTION_FIELD
	FSamplerStateInitializerRHI SceneState, FieldState;
	if (!TryBuildParameters(SceneState, FieldState, OutReason))
	{
		return false;
	}
	// 唯一GT纯校验已限定来源/精度/完整合同；此处只适配后端，不再复制校验规则。
	FGGYGODistortionViewPolicy Candidate;
	Candidate.Stage = Stage;
	Candidate.Format = Precision == EGGYGODistortionPrecision::Float16RGBA ? PF_FloatRGBA : PF_A32B32G32R32F;
	Candidate.DefaultRGBShift = FVector3f(DefaultRGBShift);
	Candidate.OverlayRGBShift = FVector3f(OverlayRGBShift);
	// 同一策略携带明确的公开阶段、格式及两路完整参数。
	if (!GDynamicRHI)
	{
		OutReason = TEXT("RHI尚未初始化");
		return false;
	}
	EPixelFormatCapabilities RequiredCapabilities = EPixelFormatCapabilities::Texture2D
		| EPixelFormatCapabilities::RenderTarget | EPixelFormatCapabilities::TextureSample
		| EPixelFormatCapabilities::TextureBlendable;
	if (FieldSampler.Filter != EGGYGODistortionFilter::Point)
	{
		RequiredCapabilities |= EPixelFormatCapabilities::TextureFilterable;
	}
	if (!RHIPixelFormatHasCapabilities(Candidate.Format, RequiredCapabilities))
	{
		OutReason = TEXT("当前RHI不支持显式field格式的双场累加/采样能力，不降为另一精度");
		return false;
	}
	Candidate.SceneSampler = RHICreateSamplerState(SceneState);
	Candidate.FieldSampler = RHICreateSamplerState(FieldState);
	if (!Candidate.SceneSampler.IsValid() || !Candidate.FieldSampler.IsValid())
	{
		OutReason = TEXT("RHI未创建实际采样器");
		return false;
	}
	OutPolicy = MoveTemp(Candidate);
	return true;
#else
	OutReason = TEXT("本构建已显式关闭Distortion Field后端；有效配置不代表可创建渲染策略");
	return false;
#endif
}
