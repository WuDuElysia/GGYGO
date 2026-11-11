/** @file GGYGOCharacterShadowCapture.cpp
 *  @brief 原生SceneDepth/R32f输入、显式预算与捕获资源归还。
 */
#include "GGYGOCharacterShadowCapture.h"

#include "Components/DirectionalLightComponent.h"
#include "Components/SceneCaptureComponent2D.h"
#include "Components/SkeletalMeshComponent.h"
#include "Engine/DirectionalLight.h"
#include "Engine/TextureRenderTarget2D.h"
#include "Engine/World.h"
#include "DynamicRHI.h"
#include "GameFramework/Actor.h"
#include "Materials/MaterialInstanceDynamic.h"
#include "Math/OrthoMatrix.h"
#include "RHI.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectIterator.h"

namespace
{
FName ShadowName(const TCHAR* Family, int32 Index)
{
	return FName(*FString::Printf(TEXT("Shadow%s%d"), Family, Index));
}

bool FiniteNonnegative(float Value) { return FMath::IsFinite(Value) && Value >= 0; }
}

struct FGGYGOCharacterShadowCapture::FResources
{
	TArray<TStrongObjectPtr<USceneCaptureComponent2D>> Captures;
	TArray<TStrongObjectPtr<UTextureRenderTarget2D>> Textures;
	TArray<TWeakObjectPtr<UMaterialInstanceDynamic>> Materials;
	TWeakObjectPtr<USkeletalMeshComponent> Mesh;
	int32 ObjectResolution = 0;
	int32 CascadeResolution = 0;
};

FGGYGOCharacterShadowCapture::FGGYGOCharacterShadowCapture() = default;

FGGYGOCharacterShadowCapture::~FGGYGOCharacterShadowCapture()
{
	check(IsInGameThread());
	auto Retired = MoveTemp(Resources);
	if (!Retired) { return; }
	for (const auto& WeakMaterial : Retired->Materials)
	{
		auto* Material = WeakMaterial.Get();
		if (!Material || !IsValid(Material->Parent)) { continue; }
		for (int32 Index = 0; Index < Retired->Textures.Num(); ++Index)
		{
			UTexture* Current = nullptr;
			UTexture* Parent = nullptr;
			const FName Name = ShadowName(TEXT("Depth"), Index);
			if (Material->GetTextureParameterValue(FHashedMaterialParameterInfo(Name), Current)
				&& Current == Retired->Textures[Index].Get()
				&& Material->Parent->GetTextureParameterValue(FHashedMaterialParameterInfo(Name), Parent))
				Material->SetTextureParameterValue(Name, Parent);
		}
		Material->SetScalarParameterValue(TEXT("UseCharacterShadowCaptures"), 0);
	}
	for (const auto& Capture : Retired->Captures)
	{
		if (IsValid(Capture.Get()))
		{
			Capture->TextureTarget = nullptr;
			Capture->DestroyComponent(); // 原生OnUnregister撤销尚未执行的capture。
		}
	}
	// 原生ReleaseResource按渲染队列归还RHI资源，UTexture的销毁栅栏保护已排队命令。
	// 本次GT退役即放弃Capture和RT的强引用，允许随原World进入同一次GC。
	for (const auto& Texture : Retired->Textures)
	{
		Texture->ReleaseResource();
	}
}

bool FGGYGOCharacterShadowCapture::ValidateSettings(const FGGYGOCharacterShadowSettings& S, FString& Reason)
{
	if (S.Mode == EGGYGOCharacterShadowMode::CharacterTrace) { Reason.Reset(); return true; }
	if (S.Mode != EGGYGOCharacterShadowMode::DepthCaptures || !S.bConfigured
		|| S.ObjectResolution <= 0 || S.ObjectResolution > 4096
		|| S.CascadeResolution <= 0 || S.CascadeResolution > 4096
		|| !FMath::IsPowerOfTwo(S.ObjectResolution) || !FMath::IsPowerOfTwo(S.CascadeResolution)
		|| !FMath::IsFinite(S.DepthHalfExtentCm) || S.DepthHalfExtentCm <= 1 || S.DepthHalfExtentCm > MAX_flt * 0.5f
		|| !FiniteNonnegative(S.ObjectMarginCm) || !FiniteNonnegative(S.DepthBiasCm)
		|| !FiniteNonnegative(S.NormalBiasCm) || !FiniteNonnegative(S.FilterRadiusTexels)
		|| !FiniteNonnegative(S.Strength) || S.Strength > 1)
	{ Reason = TEXT("阴影深度捕获模式缺完整配置或参数无效"); return false; }
	double Previous = 0;
	for (int32 Index = 0; Index < 4; ++Index)
	{
		const double Width = S.CascadeWidthsCm[Index];
		if (!FMath::IsFinite(Width) || Width <= Previous || Width > MAX_flt)
		{ Reason = TEXT("四级联宽度必须是递增的有限正厘米值"); return false; }
		Previous = Width;
	}
	const int64 Bytes = (int64(S.ObjectResolution) * S.ObjectResolution
		+ 4 * int64(S.CascadeResolution) * S.CascadeResolution) * 4;
	if (S.MaxOutputBytes <= 0 || Bytes > S.MaxOutputBytes)
	{ Reason = FString::Printf(TEXT("阴影输出需要%lldB，超过明确配置预算%lldB"), Bytes, S.MaxOutputBytes); return false; }
	Reason.Reset();
	return true;
}

bool FGGYGOCharacterShadowCapture::ValidateMaterial(const UMaterialInterface& Material, FString& Reason)
{
	float Scalar;
	FLinearColor Vector;
	UTexture* Texture;
	for (int32 Index = 0; Index < 5; ++Index)
	{
		if (!Material.GetTextureParameterValue(FHashedMaterialParameterInfo(ShadowName(TEXT("Depth"), Index)), Texture)
			|| !Material.GetVectorParameterValue(FHashedMaterialParameterInfo(ShadowName(TEXT("Origin"), Index)), Vector))
		{ Reason = TEXT("材质缺完整五路ShadowDepth/ShadowOrigin接口"); return false; }
	}
	for (const TCHAR* Name : {TEXT("ShadowForward"), TEXT("ShadowRight"), TEXT("ShadowUp"), TEXT("ShadowCascadeWidths")})
		if (!Material.GetVectorParameterValue(FHashedMaterialParameterInfo(Name), Vector))
		{ Reason = FString::Printf(TEXT("材质缺%s"), Name); return false; }
	for (const TCHAR* Name : {TEXT("UseCharacterShadowCaptures"), TEXT("ShadowObjectWidth"), TEXT("ShadowNear"),
		TEXT("ShadowFar"), TEXT("ShadowDepthBias"), TEXT("ShadowNormalBias"), TEXT("ShadowFilterRadius"), TEXT("ShadowStrength")})
		if (!Material.GetScalarParameterValue(FHashedMaterialParameterInfo(Name), Scalar))
		{ Reason = FString::Printf(TEXT("材质缺%s"), Name); return false; }
	Reason.Reset();
	return true;
}

bool FGGYGOCharacterShadowCapture::Update(UActorComponent& Owner, USkeletalMeshComponent& Mesh,
	const ADirectionalLight& Light, const FGGYGOCharacterShadowSettings& S,
	TConstArrayView<UMaterialInstanceDynamic*> Materials, FString& Reason)
{
	check(IsInGameThread());
	if (!ValidateSettings(S, Reason)) { return false; }
	if (S.Mode != EGGYGOCharacterShadowMode::DepthCaptures)
	{ Reason = TEXT("深度生产者只接受明确DepthCaptures模式"); return false; }
	UWorld* World = Owner.GetWorld();
	const auto* Directional = Cast<UDirectionalLightComponent>(Light.GetLightComponent());
	if (!GDynamicRHI || !IsValid(World) || !IsValid(Owner.GetOwner()) || !Owner.IsRegistered()
		|| !World->Scene || World->bIsTearingDown || Mesh.GetWorld() != World || Light.GetWorld() != World
		|| !Mesh.IsRegistered() || !IsValid(Directional) || !Directional->IsRegistered() || Materials.IsEmpty())
	{ Reason = TEXT("阴影生产者缺同World已注册的原Mesh/主灯/MID"); return false; }
	if (!FMath::IsFinite(Directional->Intensity) || Directional->Intensity < 0)
	{ Reason = TEXT("阴影生产者的实际主灯强度无效"); return false; }
	const bool bShadowsEnabled = Directional->CastShadows && !Light.IsHidden() && Directional->IsVisible()
		&& Directional->bAffectsWorld && Directional->Intensity > 0;
	if (!RHIPixelFormatHasCapabilities(PF_R32_FLOAT, EPixelFormatCapabilities::Texture2D
		| EPixelFormatCapabilities::RenderTarget | EPixelFormatCapabilities::TextureSample))
	{ Reason = TEXT("当前RHI不支持配置的R32f深度输出/采样；不降为其它格式"); return false; }
	for (const auto* Material : Materials)
		if (!IsValid(Material) || (!Resources && !ValidateMaterial(*Material, Reason)))
		{ if (Reason.IsEmpty()) { Reason = TEXT("阴影原MID已失效"); } return false; }
	const FVector Center = Mesh.Bounds.Origin;
	const FVector Forward = Directional->GetForwardVector();
	const FVector Right = Directional->GetRightVector();
	const FVector Up = Directional->GetUpVector();
	const FVector Origin = Center - Forward * S.DepthHalfExtentCm;
	// 原生 CalcBounds 只把半径/半轴乘 BoundsScale、不移中心；该倍率是给剔除与 VSM 缓存失效用的保守扩张，
	// 对象捕获按除回倍率后的姿态包围取景，避免扩张后对象阴影图分辨率被稀释。
	const double ObjectWidth = Mesh.BoundsScale > 0
		? 2 * (Mesh.Bounds.SphereRadius / Mesh.BoundsScale + S.ObjectMarginCm) : 0;
	if (Center.ContainsNaN() || Origin.ContainsNaN() || Forward.ContainsNaN() || Right.ContainsNaN() || Up.ContainsNaN()
		|| !FMath::IsFinite(ObjectWidth) || ObjectWidth <= 0 || ObjectWidth > MAX_flt
		|| ObjectWidth * 0.5 + 1 >= S.DepthHalfExtentCm
		|| FMath::Abs(Origin.X) > MAX_flt || FMath::Abs(Origin.Y) > MAX_flt || FMath::Abs(Origin.Z) > MAX_flt)
	{ Reason = TEXT("原Mesh bounds/光源变换超出有效float32阴影输入范围"); return false; }
	if (!Resources)
	{
		Resources = MakeUnique<FResources>();
		Resources->Mesh = &Mesh;
		Resources->ObjectResolution = S.ObjectResolution;
		Resources->CascadeResolution = S.CascadeResolution;
		for (auto* Material : Materials) { Resources->Materials.Add(Material); }
		for (int32 Index = 0; Index < 5; ++Index)
		{
			auto* Target = NewObject<UTextureRenderTarget2D>(&Owner, NAME_None, RF_Transient | RF_DuplicateTransient);
			Target->RenderTargetFormat = RTF_R32f;
			Target->bForceLinearGamma = true;
			Target->bAutoGenerateMips = false;
			Target->Filter = TF_Nearest;
			Target->ClearColor = FLinearColor(MAX_flt, MAX_flt, MAX_flt, MAX_flt);
			const int32 Resolution = Index == 0 ? S.ObjectResolution : S.CascadeResolution;
			Target->InitAutoFormat(Resolution, Resolution);
			Resources->Textures.Emplace(Target);
			auto* Capture = NewObject<USceneCaptureComponent2D>(Owner.GetOwner(), NAME_None,
				RF_Transient | RF_DuplicateTransient | RF_TextExportTransient);
			// 捕获频率沿原生SceneCapture帧更新；本类仅在原表现入口更新配置/投影。
			Capture->bCaptureEveryFrame = true;
			Capture->bCaptureOnMovement = false;
			Capture->bAlwaysPersistRenderingState = false;
			Capture->bRenderInMainRenderer = false;
			Capture->ProjectionType = ECameraProjectionMode::Orthographic;
			Capture->bAutoCalculateOrthoPlanes = false;
			Capture->bUpdateOrthoPlanes = false;
			Capture->bUseCustomProjectionMatrix = true;
			Capture->CaptureSource = SCS_SceneDepth;
			Capture->TextureTarget = Target;
			Capture->SetupAttachment(&Mesh);
			Capture->SetAbsolute(false, true, true);
			Capture->ShowFlags.SetLighting(false);
			Capture->ShowFlags.SetDynamicShadows(false);
			Capture->ShowFlags.SetPostProcessing(false);
			Capture->ShowFlags.SetAtmosphere(false);
			Capture->ShowFlags.SetFog(false);
			Capture->ShowFlags.SetVolumetricFog(false);
			Capture->ShowFlags.SetParticles(false);
			Capture->ShowFlags.SetNiagara(false);
			Capture->PostProcessSettings.bOverride_DynamicGlobalIlluminationMethod = true;
			Capture->PostProcessSettings.DynamicGlobalIlluminationMethod = EDynamicGlobalIlluminationMethod::None;
			Capture->PostProcessSettings.bOverride_ReflectionMethod = true;
			Capture->PostProcessSettings.ReflectionMethod = EReflectionMethod::None;
			if (Index == 0)
			{
				Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_UseShowOnlyList;
				Capture->ShowOnlyComponents.Add(&Mesh);
			}
			else
			{
				Capture->PrimitiveRenderMode = ESceneCapturePrimitiveRenderMode::PRM_RenderScenePrimitives;
				Capture->HiddenActors.Add(Owner.GetOwner());
			}
			Resources->Captures.Emplace(Capture);
			Capture->RegisterComponent();
			if (!IsValid(&Owner) || !Owner.IsRegistered() || Owner.GetWorld() != World || World->bIsTearingDown
				|| !IsValid(&Mesh) || !Capture->IsRegistered())
			{ Reason = TEXT("注册深度捕获时原组件/World已改变"); return false; }
		}
	}
	const FResources* const Current = Resources.Get();
	if (Current->Mesh.Get() != &Mesh || Current->ObjectResolution != S.ObjectResolution
		|| Current->CascadeResolution != S.CascadeResolution)
	{ Reason = TEXT("阴影租用期的Mesh/RT尺寸已改变；须显式RefreshMaterials归还后重建"); return false; }
	TArray<TWeakObjectPtr<UPrimitiveComponent>> NonCasters;
	for (TObjectIterator<UPrimitiveComponent> It; It; ++It)
	{
		if (IsValid(*It) && It->GetWorld() == World && It->IsRegistered()
			&& (!It->CastShadow || (It->Mobility == EComponentMobility::Static
				? !Directional->CastStaticShadows : !Directional->CastDynamicShadows)))
			NonCasters.Add(*It);
	}
	for (int32 Index = 0; Index < 5; ++Index)
	{
		const float Width = Index == 0 ? float(ObjectWidth) : float(S.CascadeWidthsCm[Index - 1]);
		auto* Capture = Current->Captures[Index].Get();
		Capture->HiddenComponents = NonCasters;
		Capture->SetVisibility(bShadowsEnabled);
		Capture->OrthoWidth = Width;
		Capture->CustomProjectionMatrix = FReversedZOrthoMatrix(Width * 0.5, Width * 0.5,
			1.0 / (2.0 * S.DepthHalfExtentCm - 1.0), -1.0);
		Capture->SetWorldLocationAndRotation(Origin, Directional->GetComponentQuat());
		Capture->CaptureSceneDeferred();
	}
	for (auto* Material : Materials)
	{
		if (!IsValid(Material)) { Reason = TEXT("排入深度捕获时原MID已失效"); return false; }
		const FVector LocalOrigin = Mesh.GetComponentTransform().InverseTransformPosition(Origin);
		if (LocalOrigin.ContainsNaN()) { Reason = TEXT("阴影原Mesh变换不可逆"); return false; }
		for (int32 Index = 0; Index < 5; ++Index)
		{
			Material->SetTextureParameterValue(ShadowName(TEXT("Depth"), Index), Current->Textures[Index].Get());
			Material->SetVectorParameterValue(ShadowName(TEXT("Origin"), Index), FLinearColor(LocalOrigin.X, LocalOrigin.Y, LocalOrigin.Z));
		}
		Material->SetVectorParameterValue(TEXT("ShadowForward"), FLinearColor(Forward.X, Forward.Y, Forward.Z));
		Material->SetVectorParameterValue(TEXT("ShadowRight"), FLinearColor(Right.X, Right.Y, Right.Z));
		Material->SetVectorParameterValue(TEXT("ShadowUp"), FLinearColor(Up.X, Up.Y, Up.Z));
		Material->SetVectorParameterValue(TEXT("ShadowCascadeWidths"), FLinearColor(S.CascadeWidthsCm.X,
			S.CascadeWidthsCm.Y, S.CascadeWidthsCm.Z, S.CascadeWidthsCm.W));
		Material->SetScalarParameterValue(TEXT("ShadowObjectWidth"), ObjectWidth);
		Material->SetScalarParameterValue(TEXT("ShadowNear"), 1);
		Material->SetScalarParameterValue(TEXT("ShadowFar"), 2 * S.DepthHalfExtentCm);
		Material->SetScalarParameterValue(TEXT("ShadowDepthBias"), S.DepthBiasCm);
		Material->SetScalarParameterValue(TEXT("ShadowNormalBias"), S.NormalBiasCm);
		Material->SetScalarParameterValue(TEXT("ShadowFilterRadius"), S.FilterRadiusTexels);
		Material->SetScalarParameterValue(TEXT("ShadowStrength"), bShadowsEnabled ? S.Strength : 0);
		Material->SetScalarParameterValue(TEXT("UseCharacterShadowCaptures"), 1);
	}
	Reason.Reset();
	return true;
}
