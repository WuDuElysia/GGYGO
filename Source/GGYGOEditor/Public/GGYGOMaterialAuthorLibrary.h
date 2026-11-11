#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"
#include "GGYGOMaterialAuthorLibrary.generated.h"

class UMaterialInstance;

/** Editor 作者查询当前平台时的单次材质实例资源事实。 */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOMaterialInstanceResourceState
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Material Resource") bool bReadbackComplete = false;
	UPROPERTY(BlueprintReadOnly, Category = "Material Resource") FString InstancePath;
	UPROPERTY(BlueprintReadOnly, Category = "Material Resource") FString ParentPath;
	/** 实例资源的真实所有者，可能是 Parent 链中的上游材质。 */
	UPROPERTY(BlueprintReadOnly, Category = "Material Resource") FString ResourceMaterialPath;
	UPROPERTY(BlueprintReadOnly, Category = "Material Resource") int32 ShaderPlatform = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Material Resource") bool bHasStaticPermutationResource = false;
	/** 实例和直连 Parent 的资源均非空，且指向同一资源。 */
	UPROPERTY(BlueprintReadOnly, Category = "Material Resource") bool bSharesParentResource = false;
	UPROPERTY(BlueprintReadOnly, Category = "Material Resource") FString Error;
};

UCLASS()
class GGYGOEDITOR_API UGGYGOMaterialAuthorLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** 非 PIE 的 Editor GameThread 上查询原实例、直连 Parent 及当前平台资源归属。 */
	UFUNCTION(BlueprintCallable, Category = "Material Resource")
	static FGGYGOMaterialInstanceResourceState ReadMaterialInstanceResourceForAuthoring(UMaterialInstance* Instance);
};
