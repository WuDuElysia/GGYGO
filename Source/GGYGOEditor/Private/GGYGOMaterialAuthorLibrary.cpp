#include "GGYGOMaterialAuthorLibrary.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Materials/MaterialInstance.h"
#include "MaterialShared.h"

#include UE_INLINE_GENERATED_CPP_BY_NAME(GGYGOMaterialAuthorLibrary)

FGGYGOMaterialInstanceResourceState UGGYGOMaterialAuthorLibrary::ReadMaterialInstanceResourceForAuthoring(
	UMaterialInstance* Instance)
{
	FGGYGOMaterialInstanceResourceState Result;
	if (!IsInGameThread() || !GIsEditor || !GEngine || !IsValid(Instance))
	{ Result.Error = TEXT("材质实例资源读回需要 Editor GameThread 和有效原实例"); return Result; }
	for (const FWorldContext& Context : GEngine->GetWorldContexts())
	{
		if (Context.WorldType == EWorldType::PIE)
		{ Result.Error = TEXT("PIE 期间不执行作者材质实例资源读回"); return Result; }
	}

	const UMaterialInterface* Parent = Instance->Parent.Get();
	const EShaderPlatform ShaderPlatform = GMaxRHIShaderPlatform;
	Result.InstancePath = Instance->GetPathName();
	Result.ParentPath = GetPathNameSafe(Parent);
	Result.ShaderPlatform = static_cast<int32>(ShaderPlatform);
	Result.bHasStaticPermutationResource = Instance->bHasStaticPermutationResource;
	if (ShaderPlatform == EShaderPlatform::SP_NumPlatforms)
	{ Result.Error = TEXT("当前 RHI 没有有效 ShaderPlatform"); return Result; }

	const bool bValidParent = IsValid(Parent) && Parent != Instance;
	// 有静态置换时，原实例 getter 独立查询自身资源，否则会沿 Parent 查询。
	const FMaterialResource* Resource = Result.bHasStaticPermutationResource || bValidParent
		? Instance->GetMaterialResource(ShaderPlatform) : nullptr;
	const FMaterialResource* ParentResource = bValidParent ? Parent->GetMaterialResource(ShaderPlatform) : nullptr;
	const UMaterialInterface* ResourceOwner = Resource ? Resource->GetMaterialInterface() : nullptr;
	Result.ResourceMaterialPath = GetPathNameSafe(ResourceOwner);
	Result.bSharesParentResource = Resource && ParentResource && Resource == ParentResource;
	if (!bValidParent)
	{ Result.Error = TEXT("材质实例缺少有效的直连 Parent"); return Result; }
	if (!Resource || !ParentResource)
	{
		Result.Error = FString::Printf(TEXT("当前 RHI 缺少原材质资源：Instance=%d Parent=%d"),
			Resource != nullptr, ParentResource != nullptr);
		return Result;
	}

	const UMaterialInterface* ParentResourceOwner = ParentResource->GetMaterialInterface();
	if (!IsValid(ParentResourceOwner) || ParentResourceOwner == Instance || !Instance->IsChildOf(ParentResourceOwner))
	{
		Result.Error = FString::Printf(TEXT("直连 Parent 的资源所有者不在原 Parent 链中：%s"),
			*GetPathNameSafe(ParentResourceOwner));
		return Result;
	}
	const bool bInstanceResourceMatches = Result.bHasStaticPermutationResource
		? ResourceOwner == Instance && !Result.bSharesParentResource : Result.bSharesParentResource;
	if (!bInstanceResourceMatches)
	{ Result.Error = TEXT("原实例资源归属与静态置换标志不一致"); return Result; }
	Result.bReadbackComplete = true;
	return Result;
}
