/** @file GGYGODistortionRenderTypes.h
 *  @brief 项目双场绘制的不可变配置；不依赖Renderer私有family或引擎覆层。
 */
#pragma once

#include "CoreMinimal.h"
#include "GGYGODistortionProfile.h"
#include "PixelFormat.h"
#include "RenderGraphFwd.h"
#include "RHIResources.h"

/** 每组四个分量压成一个DP slot位；不扩展分量或填充数据。 */
inline uint32 GetGGYGOSignedFieldDynamicParameterSlots(uint32 Components)
{
	uint32 Slots = 0;
	for (uint32 Parameter = 0; Parameter < 4; ++Parameter)
	{
		if ((Components & (15u << (4 * Parameter))) != 0) { Slots |= 1u << Parameter; }
	}
	return Slots;
}

/** GT从Profile构造；同一family只消费这一份配置及采样器。 */
struct FGGYGODistortionViewPolicy
{
	EGGYGODistortionStage Stage = EGGYGODistortionStage::Unknown;
	EPixelFormat Format = PF_Unknown;
	FVector3f DefaultRGBShift = FVector3f::ZeroVector;
	FVector3f OverlayRGBShift = FVector3f::ZeroVector;
	FSamplerStateRHIRef SceneSampler;
	FSamplerStateRHIRef FieldSampler;
};

/** 仅一次实际View/Graph的结果；两路始终独立，不能先相加或缩成RG。 */
struct FGGYGOSignedFieldTextures
{
	FRDGTextureRef Default = nullptr;
	FRDGTextureRef Overlay = nullptr;
};
