/** @file GGYGOSignedFieldRendererProperties.cpp
 *  @brief 配置校验及原Niagara factory入口；关闭态明确拒绝，不改成普通颜色或另起模拟。
 */
#include "GGYGOSignedFieldRendererProperties.h"

#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGOSignedFieldMeshRenderer.h"
#include "GGYGOSignedFieldSpriteRenderer.h"
#include "GGYGOSignedFieldVertexFactory.h"
#endif
#include "NiagaraEmitterInstance.h"

DEFINE_LOG_CATEGORY_STATIC(LogGGYGOSignedFieldRenderer, Log, All);

bool FGGYGOSignedFieldStreamContract::Validate(FString& OutReason) const
{
	if (!bConfigured || SourceReference.TrimStartAndEnd().IsEmpty()
		|| BoundsReference.TrimStartAndEnd().IsEmpty()
		|| TransformOwner != EGGYGOSignedFieldTransformOwner::MaterialWorldPositionOffset
		|| RequiredDynamicParameterComponents < 0 || RequiredDynamicParameterComponents > 65535)
	{
		OutReason = TEXT("field缺少实际variant的streams/bounds来源或唯一WPO变换合同，DP分量mask须为16位");
		return false;
	}
	OutReason.Reset();
	return true;
}

bool UGGYGOSignedFieldMeshRendererProperties::ValidateFieldConfiguration(FString& OutReason) const
{
	if (!FieldStreams.Validate(OutReason)) { return false; }
	if (SourceMode != ENiagaraRendererSourceDataMode::Particles || Meshes.IsEmpty()
		|| FacingMode != ENiagaraMeshFacingMode::Default || bEnableFrustumCulling
		|| bEnableCameraDistanceCulling || MeshIndexBinding.CanBindToHostParameterMap()
		|| SortMode != ENiagaraSortMode::None || !MeshesBinding.ResolvedParameter.GetName().IsNone())
	{
		OutReason = TEXT("field Mesh要求原Particles、明确Mesh、未补偿默认实例基底，并关闭未校正粒子球裁剪；View映射由源WPO合同提供");
		return false;
	}
	for (const FNiagaraMeshRendererMeshProperties& Mesh : Meshes)
	{
		if (!Mesh.Mesh || Mesh.LODMode != ENiagaraMeshLODMode::LODLevel
			|| !Mesh.MeshParameterBinding.ResolvedParameter.GetName().IsNone())
		{
			OutReason = TEXT("field Mesh需要明确静态Mesh与固定LOD；动态Mesh数组/参数尚无同一数据来源合同");
			return false;
		}
	}
	if ((uint32(FieldStreams.RequiredDynamicParameterComponents) & ~MaterialParamValidMask) != 0)
	{
		OutReason = TEXT("Mesh实际编译绑定缺少源材质必需DP分量");
		return false;
	}
	OutReason.Reset();
	return true;
}

void UGGYGOSignedFieldMeshRendererProperties::ForEachMesh(FNiagaraSystemInstance*,
	TFunction<void(int32)> NumMeshes, TFunction<void(const FNiagaraMeshRendererMeshProperties&)> Iterate) const
{
	// 原MinimalAPI的实现未导出；此公开接口按同一已校验静态属性枚举，不访问其私有数组。
	NumMeshes(Meshes.Num());
	for (const FNiagaraMeshRendererMeshProperties& Mesh : Meshes) { Iterate(Mesh); }
}

const FVertexFactoryType* UGGYGOSignedFieldMeshRendererProperties::GetVertexFactoryType() const
{
#if GGYGO_WITH_DISTORTION_FIELD
	return &FGGYGOSignedFieldMeshVertexFactory::StaticType;
#else
	return nullptr;
#endif
}

const FVertexFactoryType* UGGYGOSignedFieldSpriteRendererProperties::GetVertexFactoryType() const
{
#if GGYGO_WITH_DISTORTION_FIELD
	return FieldBasis == EGGYGOSignedFieldSpriteBasis::CameraPositionWithViewRoll
		? &FGGYGOSignedFieldCameraPositionVertexFactory::StaticType : &FGGYGOSignedFieldSpriteVertexFactory::StaticType;
#else
	return nullptr;
#endif
}

void UGGYGOSignedFieldMeshRendererProperties::CollectPSOPrecacheData(
	const FNiagaraEmitterInstance* Emitter, FPSOPrecacheParamsList& OutParams) const
{
#if GGYGO_WITH_DISTORTION_FIELD
	Super::CollectPSOPrecacheData(Emitter, OutParams);
#endif
}

void UGGYGOSignedFieldSpriteRendererProperties::CollectPSOPrecacheData(
	const FNiagaraEmitterInstance* Emitter, FPSOPrecacheParamsList& OutParams) const
{
#if GGYGO_WITH_DISTORTION_FIELD
	Super::CollectPSOPrecacheData(Emitter, OutParams);
#endif
}

UGGYGOSignedFieldSpriteRendererProperties::UGGYGOSignedFieldSpriteRendererProperties()
{
	// 原shader/WPO管理覆盖率、尺寸及颜色；native像素覆盖率不能再次修改PCol或扩quad。
	PixelCoverageMode = ENiagaraRendererPixelCoverageMode::Disabled;
#if WITH_EDITORONLY_DATA
	bUseMaterialCutoutTexture = false;
	CutoutTexture = nullptr;
#endif
}

bool UGGYGOSignedFieldSpriteRendererProperties::ValidateFieldConfiguration(FString& OutReason) const
{
	if (!FieldStreams.Validate(OutReason)) { return false; }
	const bool bView = FieldBasis == EGGYGOSignedFieldSpriteBasis::NativeViewPlane
		&& Alignment == ENiagaraSpriteAlignment::Unaligned
		&& (FacingMode == ENiagaraSpriteFacingMode::FaceCamera || FacingMode == ENiagaraSpriteFacingMode::FaceCameraPlane);
	const bool bVelocity = FieldBasis == EGGYGOSignedFieldSpriteBasis::NativeVelocityAligned
		&& Alignment == ENiagaraSpriteAlignment::VelocityAligned && FacingMode == ENiagaraSpriteFacingMode::FaceCamera;
	const bool bPosition = FieldBasis == EGGYGOSignedFieldSpriteBasis::CameraPositionWithViewRoll
		&& Alignment == ENiagaraSpriteAlignment::Unaligned && FacingMode == ENiagaraSpriteFacingMode::FaceCamera;
	if (SourceMode != ENiagaraRendererSourceDataMode::Particles || !(bView || bVelocity || bPosition)
		|| PixelCoverageMode != ENiagaraRendererPixelCoverageMode::Disabled
		|| bEnableCameraDistanceCulling || PivotInUVSpace != FVector2D(0.5, 0.5)
		|| SortMode != ENiagaraSortMode::None)
	{
		OutReason = TEXT("field Sprite基底与原native Facing/Alignment不匹配，或像素覆盖率会重复修改原quad/PCol");
		return false;
	}
#if WITH_EDITORONLY_DATA
	if (bUseMaterialCutoutTexture || CutoutTexture)
	{
		OutReason = TEXT("源Sprite/WPO需要原始0..1完整quad，不能由native cutout再裁剪几何");
		return false;
	}
#endif
	if ((uint32(FieldStreams.RequiredDynamicParameterComponents) & ~MaterialParamValidMask) != 0)
	{
		OutReason = TEXT("Sprite实际编译绑定缺少源材质必需DP分量");
		return false;
	}
	OutReason.Reset();
	return true;
}

FNiagaraRenderer* UGGYGOSignedFieldMeshRendererProperties::CreateEmitterRenderer(
	ERHIFeatureLevel::Type FeatureLevel, const FNiagaraEmitterInstance* Emitter,
	const FNiagaraSystemInstanceController& Controller)
{
#if GGYGO_WITH_DISTORTION_FIELD
	FString Reason;
	if (!Emitter || Emitter->GetSimTarget() != ENiagaraSimTarget::CPUSim || !ValidateFieldConfiguration(Reason))
	{
		UE_LOG(LogGGYGOSignedFieldRenderer, Warning, TEXT("%s 未创建field Mesh：%s"),
			*GetPathName(), Reason.IsEmpty() ? TEXT("原CPU Emitter尚未就绪或目标不受支持") : *Reason);
		return nullptr;
	}
	auto* Renderer = new FGGYGOSignedFieldMeshRenderer(FeatureLevel, this, Emitter);
	Renderer->Initialize(this, Emitter, Controller);
	return Renderer;
#else
	UE_LOG(LogGGYGOSignedFieldRenderer, Warning, TEXT("%s 未创建field Mesh：本构建能力已显式关闭"), *GetPathName());
	return nullptr;
#endif
}

FNiagaraRenderer* UGGYGOSignedFieldSpriteRendererProperties::CreateEmitterRenderer(
	ERHIFeatureLevel::Type FeatureLevel, const FNiagaraEmitterInstance* Emitter,
	const FNiagaraSystemInstanceController& Controller)
{
#if GGYGO_WITH_DISTORTION_FIELD
	FString Reason;
	if (!Emitter || Emitter->GetSimTarget() != ENiagaraSimTarget::CPUSim || !ValidateFieldConfiguration(Reason))
	{
		UE_LOG(LogGGYGOSignedFieldRenderer, Warning, TEXT("%s 未创建field Sprite：%s"),
			*GetPathName(), Reason.IsEmpty() ? TEXT("原CPU Emitter尚未就绪或目标不受支持") : *Reason);
		return nullptr;
	}
	auto* Renderer = new FGGYGOSignedFieldSpriteRenderer(FeatureLevel, this, Emitter);
	Renderer->Initialize(this, Emitter, Controller);
	return Renderer;
#else
	UE_LOG(LogGGYGOSignedFieldRenderer, Warning, TEXT("%s 未创建field Sprite：本构建能力已显式关闭"), *GetPathName());
	return nullptr;
#endif
}
