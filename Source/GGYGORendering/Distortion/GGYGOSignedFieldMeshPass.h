/** @file GGYGOSignedFieldMeshPass.h
 *  @brief 原View中的项目mesh shader绘制入口与编译角色；不选择合成阶段。
 */
#pragma once

#include "CoreMinimal.h"
#include "GGYGODistortionRenderTypes.h"

class FMaterial;
struct FMeshBatch;
class FPrimitiveSceneProxy;
class FSceneView;
class FSceneTextureUniformParameters;
enum class EGGYGODistortionMaterialRole : uint8;

#if GGYGO_WITH_DISTORTION_FIELD
/** 仅有效至原collector/当前Graph归还；从不跨帧缓存proxy或MeshBatch。 */
struct FGGYGOSignedFieldDraw
{
	const FMeshBatch* Mesh = nullptr;
	const FPrimitiveSceneProxy* Primitive = nullptr;
	uint32 RequiredDynamicParameterSlots = 0;
};

EGGYGODistortionMaterialRole QueryGGYGOSignedFieldCompiledRole_GameThread(
	const FMaterial& Material, FString& OutReason);

bool AccumulateGGYGOSignedFields(FRDGBuilder& GraphBuilder, const FSceneView& View,
	TRDGUniformBufferRef<FSceneTextureUniformParameters> SceneTextures,
	FRDGTextureRef Depth, FIntRect ViewRect, const FGGYGODistortionViewPolicy& Policy,
	TConstArrayView<FGGYGOSignedFieldDraw> Draws, FGGYGOSignedFieldTextures& OutTextures,
	FString& OutReason);
#endif
