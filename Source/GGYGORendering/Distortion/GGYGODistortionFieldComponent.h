/** @file GGYGODistortionFieldComponent.h
 *  @brief 将既有 primitive 的 field 材质接入主视图；不创建粒子或模拟时钟。
 */
#pragma once

#include "CoreMinimal.h"
#include "Components/ActorComponent.h"
#include "Engine/EngineTypes.h"
#include "GGYGODistortionFieldComponent.generated.h"

class UGGYGODistortionProfile;
class UGGYGODistortionSubsystem;
class UMaterialInterface;
class UPrimitiveComponent;
class UWorld;

UENUM(BlueprintType)
enum class EGGYGODistortionMaterialRole : uint8 { Unavailable, NoCustomField, DualSignedField, Invalid };

UCLASS(ClassGroup=(Rendering), meta=(BlueprintSpawnableComponent))
class GGYGORENDERING_API UGGYGODistortionFieldComponent : public UActorComponent
{
	GENERATED_BODY()

public:
	UGGYGODistortionFieldComponent();

	/** GT查询原材质的完整声明；普通声明不要求ShaderMap/VF就绪。
	 * Editor沿实际继承/函数/layer缓存及图核查；来源不完整返回Unavailable，编译错误返回Invalid。
	 * DualSignedField只表示声明含field，实际GPU资格仍须QueryMaterialFieldRole。 */
	UFUNCTION(BlueprintCallable, Category="Distortion|Validation")
	static EGGYGODistortionMaterialRole QueryMaterialFieldDeclaration(
		UMaterialInterface* Material, UWorld* World, FString& OutReason);

	/** GT查询指定World平台下原材质的编译角色；未就绪不代表普通材质。
	 * 只证明当前shader角色，不证明原renderer/材质资产/画面资格；不使用fallback。 */
	UFUNCTION(BlueprintCallable, Category="Distortion|Validation")
	static EGGYGODistortionMaterialRole QueryMaterialFieldRole(
		UMaterialInterface* Material, UWorld* World, FString& OutReason);

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distortion")
	bool bEnableField = false;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distortion",
		meta=(UseComponentPicker, AllowedClasses="/Script/Engine.PrimitiveComponent"))
	FComponentReference TargetPrimitive;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distortion")
	TObjectPtr<UGGYGODistortionProfile> Profile;

	/** 原 renderer 实际使用的 field 材质；不得包含普通颜色材质。 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distortion")
	TArray<TObjectPtr<UMaterialInterface>> FieldMaterials;

	/** 原builder对两路float4输出、零普通颜色、alpha/DP/VF的实际读回入口。 */
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Distortion")
	FString MaterialContractEvidence;

	/** FX 完成原 renderer/材质配置后调用；返回是否已登记，未就绪须稍后显式重试。 */
	UFUNCTION(BlueprintCallable, Category="Distortion")
	bool RefreshFieldRegistration();

	bool ResolveFieldInputs(UPrimitiveComponent*& OutPrimitive,
		TArray<UMaterialInterface*>& OutMaterials, FString& OutReason) const;

protected:
	virtual void OnRegister() override;
	virtual void OnUnregister() override;
#if WITH_EDITOR
	virtual void PostEditChangeProperty(FPropertyChangedEvent& PropertyChangedEvent) override;
#endif

private:
	TWeakObjectPtr<UGGYGODistortionSubsystem> RegisteredSubsystem;
};
