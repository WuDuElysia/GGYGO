/** @file GGYGODistortionFieldComponent.cpp
 *  @brief 随组件注册/注销提交 field source，支持编辑器属性修改后的刷新。
 */
#include "GGYGODistortionFieldComponent.h"

#include "GGYGODistortionProfile.h"
#include "GGYGODistortionSubsystem.h"
#include "Components/PrimitiveComponent.h"
#if GGYGO_WITH_DISTORTION_FIELD
#include "GGYGOSignedFieldMeshPass.h"
#include "NiagaraComponent.h"
#endif
#include "Engine/World.h"
#include "Materials/Material.h"
#include "Materials/MaterialInterface.h"
#include "Materials/MaterialInstance.h"
#if WITH_EDITOR
#include "MaterialCachedData.h"
#include "Materials/MaterialExpressionMaterialFunctionCall.h"
#include "Materials/MaterialFunctionInterface.h"
#include "Materials/GGYGOMaterialExpressionDistortionField.h"
#endif
#include "MaterialShared.h"
#include "SceneInterface.h"

UGGYGODistortionFieldComponent::UGGYGODistortionFieldComponent()
{
	PrimaryComponentTick.bCanEverTick = false;
}

#if WITH_EDITOR
namespace
{
bool ReadFieldExpressions(TConstArrayView<TObjectPtr<UMaterialExpression>> Expressions,
	const TSet<const UMaterialFunctionInterface*>& CachedFunctions, bool& bDeclaresField,
	bool& bUsesLayers, FString& Reason)
{
	for (const UMaterialExpression* Expression : Expressions)
	{
		// 原生UpdateForExpressions允许已移除节点留下的空槽。
		if (!Expression) { continue; }
		if (!IsValid(Expression) || Expression->HasAnyFlags(RF_NeedLoad | RF_NeedPostLoad))
		{ Reason = TEXT("原材质表达式尚未完整加载"); return false; }
		bDeclaresField |= Expression->IsA<UGGYGOMaterialExpressionDistortionField>();
		const auto* Call = Cast<UMaterialExpressionMaterialFunctionCall>(Expression);
		const auto* Function = UMaterial::GetExpressionFunctionPointer(Expression);
		if ((Call && !Function) || (Function && !CachedFunctions.Contains(Function)))
		{ Reason = TEXT("原材质函数缺实际来源或不在当前声明缓存中"); return false; }
		bUsesLayers |= UMaterial::GetExpressionLayers(Expression).IsSet();
	}
	return true;
}
}
#endif

EGGYGODistortionMaterialRole UGGYGODistortionFieldComponent::QueryMaterialFieldDeclaration(
	UMaterialInterface* Material, UWorld* World, FString& OutReason)
{
	check(IsInGameThread());
	OutReason.Reset();
	if (!IsValid(Material) || !IsValid(World) || World->bIsTearingDown)
	{ OutReason = TEXT("原材质/World无效或正在归还"); return EGGYGODistortionMaterialRole::Invalid; }
#if WITH_EDITOR
	// 直接走原Parent，防止MI缺父/循环时GetMaterial隐式交回默认材质。
	TSet<const UMaterialInterface*> Parents;
	const UMaterialInterface* Current = Material;
	while (IsValid(Current))
	{
		if (Parents.Contains(Current))
		{ OutReason = TEXT("原材质Parent存在循环"); return EGGYGODistortionMaterialRole::Invalid; }
		if (Current->HasAnyFlags(RF_NeedLoad | RF_NeedPostLoad))
		{ OutReason = TEXT("原材质继承链尚未加载完成"); return EGGYGODistortionMaterialRole::Unavailable; }
		Parents.Add(Current);
		const UMaterialInstance* Instance = Cast<UMaterialInstance>(Current);
		if (!Instance) { break; }
		Current = Instance->Parent;
	}
	const UMaterial* Base = Cast<UMaterial>(Current);
	if (!IsValid(Base))
	{ OutReason = TEXT("原材质缺有效Parent/基础图"); return EGGYGODistortionMaterialRole::Invalid; }
	const FSceneInterface* Scene = World->Scene;
	if (Scene)
	{
		const auto Platform = Scene->GetShaderPlatform();
		const auto* Resource = Platform != EShaderPlatform::SP_NumPlatforms ? Material->GetMaterialResource(Platform) : nullptr;
		if (!IsValid(Material) || !IsValid(World) || World->bIsTearingDown || World->Scene != Scene)
		{ OutReason = TEXT("查询声明时原材质/World已经改变"); return EGGYGODistortionMaterialRole::Invalid; }
		if (Resource && !Resource->GetCompileErrors().IsEmpty())
		{ OutReason = TEXT("原材质存在实际编译错误"); return EGGYGODistortionMaterialRole::Invalid; }
	}
	const auto& Data = Material->GetCachedExpressionData();
	if (&Data == &FMaterialCachedExpressionData::EmptyData || !Data.EditorOnlyData.IsValid())
	{ OutReason = TEXT("缺原材质完整表达式声明缓存"); return EGGYGODistortionMaterialRole::Unavailable; }
	TSet<const UMaterialFunctionInterface*> Functions;
	for (const auto& Info : Data.FunctionInfos)
	{
		const auto* Function = Info.Function.Get();
		if (!IsValid(Function) || Function->HasAnyFlags(RF_NeedLoad | RF_NeedPostLoad)
			|| Function->StateId != Info.StateId || !Function->GetBaseFunction())
		{ OutReason = TEXT("原函数/layer声明未加载或StateId已改变"); return EGGYGODistortionMaterialRole::Unavailable; }
		Functions.Add(Function);
	}
	bool bField = Data.EditorOnlyData->ShaderTags.Contains(FName(TEXT("SignedDistortionField")));
	bool bUsesLayers = false;
	if (!ReadFieldExpressions(Base->GetExpressionCollection().Expressions, Functions, bField, bUsesLayers, OutReason))
		return EGGYGODistortionMaterialRole::Unavailable;
	for (const auto* Function : Functions)
		if (!ReadFieldExpressions(Function->GetExpressions(), Functions, bField, bUsesLayers, OutReason))
			return EGGYGODistortionMaterialRole::Unavailable;
	if (bUsesLayers)
	{
		if (!Data.bHasMaterialLayers)
		{ OutReason = TEXT("原材质layer声明缓存尚未生成"); return EGGYGODistortionMaterialRole::Unavailable; }
		// MI可覆盖基础图的Layers；沿当前缓存中的真实函数，空blend槽遵循原生无函数语义。
		for (const auto* Layers : {&Data.MaterialLayers.Layers, &Data.MaterialLayers.Blends})
			for (const UMaterialFunctionInterface* Layer : *Layers)
				if (Layer && !Functions.Contains(Layer))
				{ OutReason = TEXT("当前材质layer/blend来源不在完整声明缓存中"); return EGGYGODistortionMaterialRole::Unavailable; }
	}
	return bField ? EGGYGODistortionMaterialRole::DualSignedField : EGGYGODistortionMaterialRole::NoCustomField;
#else
	// Cooked未另持源图声明；只有已存在的真实角色证书可提供明确分类。
	return QueryMaterialFieldRole(Material, World, OutReason);
#endif
}

EGGYGODistortionMaterialRole UGGYGODistortionFieldComponent::QueryMaterialFieldRole(
	UMaterialInterface* Material, UWorld* World, FString& OutReason)
{
	check(IsInGameThread());
	OutReason.Reset();
	if (!IsValid(Material) || !IsValid(World) || World->bIsTearingDown)
	{
		OutReason = TEXT("原材质/World无效或正在归还");
		return EGGYGODistortionMaterialRole::Invalid;
	}
#if GGYGO_WITH_DISTORTION_FIELD
	const FSceneInterface* Scene = World->Scene;
	if (!Scene)
	{
		OutReason = TEXT("原World尚无Scene，不能判作普通材质");
		return EGGYGODistortionMaterialRole::Unavailable;
	}
	const FMaterialResource* Resource = Material->GetMaterialResource(Scene->GetShaderPlatform());
	if (!IsValid(Material) || !IsValid(World) || World->bIsTearingDown || World->Scene != Scene)
	{
		OutReason = TEXT("查询原材质资源时材质/World已改变");
		return EGGYGODistortionMaterialRole::Invalid;
	}
	if (!Resource)
	{
		OutReason = TEXT("原材质在当前World平台无可读资源；未使用fallback");
		return EGGYGODistortionMaterialRole::Unavailable;
	}
#if WITH_EDITOR
	if (!Resource->GetCompileErrors().IsEmpty())
	{
		OutReason = TEXT("原材质存在实际编译错误，不能认证 field 角色：\n")
			+ FString::Join(Resource->GetCompileErrors(), TEXT("\n"));
		return EGGYGODistortionMaterialRole::Invalid;
	}
#endif
	const EGGYGODistortionMaterialRole Role = QueryGGYGOSignedFieldCompiledRole_GameThread(*Resource, OutReason);
#if WITH_EDITOR
	// 编辑器额外拦截已声明field节点但尚无对应编译角色的坏图；Cooked判定不依赖这些tag。
	if (Role == EGGYGODistortionMaterialRole::NoCustomField)
	{
		const UMaterial* Base = Material->GetMaterial();
		TArray<FName> Tags;
		if (Base) { Base->GetShaderTags(Tags); }
		if (Tags.Contains(FName(TEXT("SignedDistortionField"))))
		{
			OutReason = TEXT("材质已声明field节点，当前编译map尚无对应角色；不能当作普通材质");
			return EGGYGODistortionMaterialRole::Unavailable;
		}
	}
#endif
	return Role;
#else
	OutReason = TEXT("本构建已显式关闭Distortion Field后端，不能认证材质的field角色");
	return EGGYGODistortionMaterialRole::Unavailable;
#endif
}

void UGGYGODistortionFieldComponent::OnRegister()
{
	Super::OnRegister();
	RefreshFieldRegistration();
}

void UGGYGODistortionFieldComponent::OnUnregister()
{
	UGGYGODistortionSubsystem* Previous = RegisteredSubsystem.Get();
	RegisteredSubsystem.Reset();
	if (Previous)
	{
		Previous->UnregisterSource(*this);
	}
	Super::OnUnregister();
}

bool UGGYGODistortionFieldComponent::RefreshFieldRegistration()
{
	check(IsInGameThread());
	if (UGGYGODistortionSubsystem* Previous = RegisteredSubsystem.Get())
	{
		RegisteredSubsystem.Reset();
		Previous->UnregisterSource(*this);
	}
	if (!bEnableField || !IsRegistered())
	{
		return false;
	}
#if !GGYGO_WITH_DISTORTION_FIELD
	UE_LOG(LogTemp, Warning, TEXT("[GGYGODistortion] %s 未登记：本构建已显式关闭Field后端"), *GetPathName());
	return false;
#else
	UWorld* World = GetWorld();
	UGGYGODistortionSubsystem* Current = World ? World->GetSubsystem<UGGYGODistortionSubsystem>() : nullptr;
	FString Reason;
	// 编译角色在显式登记/配置变化时核对；family逐帧解析仍由原RT绘制准入保护。
	for (UMaterialInterface* Material : FieldMaterials)
	{
		if (QueryMaterialFieldRole(Material, World, Reason) != EGGYGODistortionMaterialRole::DualSignedField)
		{
			UE_LOG(LogTemp, Warning, TEXT("[GGYGODistortion] %s 未登记双路field材质 %s：%s"),
				*GetPathName(), *GetPathNameSafe(Material), *Reason);
			return false;
		}
	}
	if (!Current || !Current->RegisterSource(*this, Reason))
	{
		UE_LOG(LogTemp, Warning, TEXT("[GGYGODistortion] %s 登记失败：%s"),
			*GetPathName(), Current ? *Reason : TEXT("当前 World 无渲染子系统"));
		return false;
	}
	RegisteredSubsystem = Current;
	return true;
#endif
}

bool UGGYGODistortionFieldComponent::ResolveFieldInputs(UPrimitiveComponent*& OutPrimitive,
	TArray<UMaterialInterface*>& OutMaterials, FString& OutReason) const
{
	check(IsInGameThread());
	OutPrimitive = nullptr;
	OutMaterials.Reset();
	if (!bEnableField || !IsRegistered() || !IsValid(Profile)
		|| MaterialContractEvidence.TrimStartAndEnd().IsEmpty() || FieldMaterials.IsEmpty())
	{
		OutReason = TEXT("source 未启用/注册，或 Profile / 材质 / 材质契约来源缺失");
		return false;
	}
	if (TargetPrimitive.ComponentProperty.IsNone() && TargetPrimitive.PathToComponent.IsEmpty()
		&& !TargetPrimitive.OverrideComponent.IsValid())
	{
		OutReason = TEXT("须明确选择原 primitive component");
		return false;
	}
	UPrimitiveComponent* Primitive = Cast<UPrimitiveComponent>(TargetPrimitive.GetComponent(GetOwner()));
	if (!IsValid(Primitive) || Primitive->GetWorld() != GetWorld() || !Primitive->IsRegistered()
		|| !Primitive->bRenderInMainPass)
	{
		OutReason = TEXT("原 primitive 尚未注册到同 World 的 MainPass");
		return false;
	}
#if GGYGO_WITH_DISTORTION_FIELD
	const UNiagaraComponent* Niagara = Cast<UNiagaraComponent>(Primitive);
	if (!Niagara || !Niagara->GetAsset())
	{
		OutReason = TEXT("当前field绘制接缝只支持原Niagara系统的自有renderer；目标须有明确NS资产");
		return false;
	}
#endif
	TArray<UMaterialInterface*> UsedMaterials;
	Primitive->GetUsedMaterials(UsedMaterials);
	// GetUsedMaterials 是原 renderer 的虚调用；返回后仍须消费同一个有效 primitive。
	if (!IsValid(Primitive) || !Primitive->IsRegistered() || !IsRegistered()
		|| TargetPrimitive.GetComponent(GetOwner()) != Primitive)
	{
		OutReason = TEXT("取得材质时原 primitive/source 已改变");
		return false;
	}
	for (UMaterialInterface* Material : FieldMaterials)
	{
		if (!IsValid(Material) || !UsedMaterials.Contains(Material))
		{
			OutReason = FString::Printf(TEXT("field 材质未被原 primitive 使用：%s"), *GetPathNameSafe(Material));
			return false;
		}
		UMaterial* Base = Material->GetMaterial();
		if (Base && Base->bEnableNewHLSLGenerator)
		{
			OutReason = FString::Printf(TEXT("field 要求显式 Legacy 编译配置；当前 MIR 入口未导出：%s"), *Material->GetPathName());
			return false;
		}
		if (!Base || Base->MaterialDomain != MD_Surface || !IsTranslucentBlendMode(Material->GetBlendMode()))
		{
			OutReason = FString::Printf(TEXT("材质没有明确的translucent surface资格：%s"), *Material->GetPathName());
			return false;
		}
		OutMaterials.AddUnique(Material);
	}
	OutPrimitive = Primitive;
	OutReason.Reset();
	return true;
}

#if WITH_EDITOR
void UGGYGODistortionFieldComponent::PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent)
{
	// Super 可能重建组件，故只在其返回后对仍注册的本对象刷新。
	Super::PostEditChangeProperty(PropertyChangedEvent);
	if (IsValid(this) && IsRegistered())
	{
		RefreshFieldRegistration();
	}
}
#endif
