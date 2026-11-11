/** @file GGYGONiagaraMaterialPreparation.h
 *  @brief 为明确的 Niagara 系统及最终对象绑定准备当前 World 的材质资源。
 */
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/WorldSubsystem.h"
#include "TimerManager.h"
#include "UObject/Object.h"
#include "GGYGONiagaraMaterialPreparation.generated.h"

class UNiagaraComponent;
class UNiagaraSystem;
class UGGYGONiagaraMaterialPreparation;
struct FGGYGONiagaraPreparationWork;
struct FGGYGONiagaraPreparedResources;

UENUM(BlueprintType)
enum class EGGYGONiagaraMaterialPreparationState : uint8
{
	Pending,
	Ready,
	Failed,
	Cancelled
};

/** BP 选择系统和对象绑定。未列出的 User 对象沿该系统的原 ExposedParameters 解析。 */
USTRUCT(BlueprintType)
struct GGYGORENDERING_API FGGYGONiagaraSystemPreparation
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Niagara Preparation")
	TObjectPtr<UNiagaraSystem> System;

	UPROPERTY(EditAnywhere, BlueprintReadWrite, Category="Niagara Preparation")
	TMap<FName, TObjectPtr<UObject>> UserObjectOverrides;
};

DECLARE_DYNAMIC_MULTICAST_DELEGATE_OneParam(FGGYGONiagaraMaterialPreparationFinished,
	UGGYGONiagaraMaterialPreparation*, Request);

/** 原平台资源的派生就绪记录，生命周期仅为本 World；不调度 Niagara 或角色业务。 */
UCLASS()
class GGYGORENDERING_API UGGYGONiagaraMaterialPreparationWorld : public UWorldSubsystem
{
	GENERATED_BODY()
public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;
private:
	friend class UGGYGONiagaraMaterialPreparation;
	TSharedPtr<FGGYGONiagaraPreparedResources> Resources;
};

/** 调用方持有请求；先绑定 OnFinished 再 Start。Start 可同步 Ready。
 * Ready 只证明此输入闭包的原材质/平台/VF 资源，不证明最终 Draw、像素或动作表现。
 * Cancel 不取消共享引擎编译，仅结束本请求并解除观察；终态通知最多一次。
 */
UCLASS(BlueprintType, Transient)
class GGYGORENDERING_API UGGYGONiagaraMaterialPreparation : public UObject
{
	GENERATED_BODY()
public:
	UGGYGONiagaraMaterialPreparation(const FObjectInitializer& ObjectInitializer);
	// 供 UE 重载使用，定义放在 Work 完整可见的实现文件中。
	UGGYGONiagaraMaterialPreparation(FVTableHelper& Helper);
	virtual ~UGGYGONiagaraMaterialPreparation() override;

	UFUNCTION(BlueprintCallable, Category="Niagara Preparation")
	static UGGYGONiagaraMaterialPreparation* CreateForSystems(UObject* Owner, UWorld* World,
		const TArray<FGGYGONiagaraSystemPreparation>& Systems);

	/** 无调用方对象覆盖的原系统列表；与带绑定入口消费同一准备机制。 */
	UFUNCTION(BlueprintCallable, Category="Niagara Preparation", meta=(WorldContext="WorldContextObject"))
	static UGGYGONiagaraMaterialPreparation* CreateForSystemAssets(UObject* Owner, const UObject* WorldContextObject,
		const TArray<UNiagaraSystem*>& Systems);

	/** 原组件须已 SetAsset/注册且装好最终对象覆盖；不要求 Controller，不激活/模拟组件。 */
	UFUNCTION(BlueprintCallable, Category="Niagara Preparation")
	static UGGYGONiagaraMaterialPreparation* CreateForComponents(UObject* Owner,
		const TArray<UNiagaraComponent*>& Components);

	UFUNCTION(BlueprintCallable, Category="Niagara Preparation")
	void Start();
	UFUNCTION(BlueprintCallable, Category="Niagara Preparation")
	void Cancel();
	UFUNCTION(BlueprintPure, Category="Niagara Preparation")
	EGGYGONiagaraMaterialPreparationState GetState() const { return State; }
	UFUNCTION(BlueprintPure, Category="Niagara Preparation")
	FString GetError() const { return Error; }

	UPROPERTY(BlueprintAssignable, Category="Niagara Preparation")
	FGGYGONiagaraMaterialPreparationFinished OnFinished;

	virtual void BeginDestroy() override;
private:
	void Advance();
	void Finish(EGGYGONiagaraMaterialPreparationState NewState, FString Reason);
	void Detach();
	void OnWorldCleanup(UWorld* World, bool bSessionEnded, bool bCleanupResources);
	void OnTimeout();
	void OnRenderResourcesRead(bool bReady, FString Reason);

	UPROPERTY(Transient)
	TArray<FGGYGONiagaraSystemPreparation> RequestedSystems;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UNiagaraComponent>> RequestedComponents;
	UPROPERTY(Transient)
	TArray<TObjectPtr<UObject>> RetainedInputs;
	TWeakObjectPtr<UWorld> RequestedWorld;
	TUniquePtr<FGGYGONiagaraPreparationWork> Work;
	FDelegateHandle WorldCleanupHandle;
	FDelegateHandle AssetCompiledHandle;
	FDelegateHandle MaterialCompiledHandle;
	FTimerHandle TimeoutHandle;
	EGGYGONiagaraMaterialPreparationState State = EGGYGONiagaraMaterialPreparationState::Pending;
	FString Error;
	bool bStarted = false;
	/** Start 时的帧号与 World 时间，只供终态诊断给出 Pending→终态时序；不参与就绪判断。 */
	uint64 StartFrame = 0;
	double StartWorldSeconds = -1.0;
};
