/** @file GGYGOSignedFieldVertexFactory.h
 *  @brief 复用公开Niagara基底和完整粒子输入；field手工实例绘制不消费GPUScene。
 */
#pragma once

#include "CoreMinimal.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "NiagaraMeshVertexFactory.h"
#include "NiagaraSpriteVertexFactory.h"

/** 只改变绘制接缝；source affine、法线、pivot及viewport仍由原材质WPO唯一处理。 */
class FGGYGOSignedFieldMeshVertexFactory final : public FNiagaraMeshVertexFactory
{
	DECLARE_VERTEX_FACTORY_TYPE(FGGYGOSignedFieldMeshVertexFactory);
public:
	explicit FGGYGOSignedFieldMeshVertexFactory(ERHIFeatureLevel::Type FeatureLevel)
		: FNiagaraMeshVertexFactory(NVFT_Mesh, FeatureLevel)
	{
		EnablePrimitiveIDElement(false);
	}
	static void ModifyCompilationEnvironment(const FVertexFactoryShaderPermutationParameters& Parameters,
		FShaderCompilerEnvironment& Environment);
	static void GetPSOPrecacheVertexFetchElements(EVertexInputStreamType StreamType,
		FVertexDeclarationElementList& Elements);
};

/** View平面或VelocityAligned基底沿原Niagara算法，不在此伸长、镜像或缩放viewport。 */
class FGGYGOSignedFieldSpriteVertexFactory : public FNiagaraSpriteVertexFactory
{
	DECLARE_VERTEX_FACTORY_TYPE(FGGYGOSignedFieldSpriteVertexFactory);
public:
	explicit FGGYGOSignedFieldSpriteVertexFactory(ERHIFeatureLevel::Type FeatureLevel)
		: FNiagaraSpriteVertexFactory(NVFT_Sprite, FeatureLevel) {}
};

/** 逐粒子朝Camera位置，并保当前View的roll；区别于UE的固定world-Z Position facing。 */
class FGGYGOSignedFieldCameraPositionVertexFactory final : public FNiagaraSpriteVertexFactory
{
	DECLARE_VERTEX_FACTORY_TYPE(FGGYGOSignedFieldCameraPositionVertexFactory);
public:
	explicit FGGYGOSignedFieldCameraPositionVertexFactory(ERHIFeatureLevel::Type FeatureLevel)
		: FNiagaraSpriteVertexFactory(NVFT_Sprite, FeatureLevel) {}
};
#endif
