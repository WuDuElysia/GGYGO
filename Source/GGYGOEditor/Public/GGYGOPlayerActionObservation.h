/** @file GGYGOPlayerActionObservation.h @brief 原 GA／Task／CMC 与网络 FX 发布、资源归还的有界值观察。 */
#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "GGYGOPlayerActionObservation.generated.h"

class APawn;
class UAnimMontage;
class USkeletalMeshComponent;
class UWorld;
class UAbilitySystemComponent;
class UGGYGOAbilitySystemComponent;
class UGGYGOPlayerComboAbility;
class FGGYGOAbilityTerminationCompletedNotice;
struct FGGYGOMontageFXObservationFact;

/** 一对象一观察窗；既有宿主调用 Sample，不注册 Tick、不驱动输入／动画／结束。
 * Combo 历史由原 GA 写入，完整退出由 ASC 签发；FX 事实由原 publisher/组件写入。
 * 显式 Stop、容量、原 World 清理、EndPIE 和对象销毁解除本窗订阅，保留纯数据。
 * 采到事实不代表 E、姿态、声音、设备或联机验收。 */
UCLASS(Transient, BlueprintType)
class GGYGOEDITOR_API UGGYGOPlayerActionObservation : public UObject
{
	GENERATED_BODY()
public:
	/** 调用方持有返回对象，并在其宿主 finally 中 Stop；不 Root、不持有 Actor 强引用。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Combat|Observation")
	static UGGYGOPlayerActionObservation* CreateObservation();

	/** @param Ability 同 ASC 的实际原实例，拒绝 CDO、未起段、歧义或已换源。
	 * @param TrialId 宿主实际采用的非空标识；不自动产生或替换本轮标识。
	 * @param MaxRecords 1..4096 的有限采样容量。
	 * @return 原源捕获及订阅成功；不代表任何完成事实已发生。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Combat|Observation")
	bool BeginObservation(UGGYGOPlayerComboAbility* Ability, UGGYGOAbilitySystemComponent* ASC,
		APawn* Pawn, USkeletalMeshComponent* Mesh, UAnimMontage* Montage,
		const FString& TrialId, int32 MaxRecords, FString& OutDiagnostic);

	/** 触发前固定原网络 ASC/Pawn/Mesh，观察 FX 原发布与归还；支持没有本地 GA 的 SimulatedProxy。
	 * @param Issuer 实际实现 MontageFXHost 的原 ASC；不从 CDO、其它 Avatar 或后继注册猜来源。
	 * @param MaxRecords 1..4096，Runtime 收件窗和 Editor 值记录均有界，溢出明确报证据不完整。
	 * @return 安装原 owner 的精确只读 view；没有发布记录也不推断结束或资源已归还。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|FX|Observation")
	bool BeginFXObservation(UAbilitySystemComponent* Issuer, APawn* Pawn, USkeletalMeshComponent* Mesh,
		const FString& TrialId, int32 MaxRecords, FString& OutDiagnostic);

	/** @param ElapsedSeconds 既有宿主提供的实际单调时间；不得倒退，不创建另一时钟。
	 * @return 是否记录此采样；原 Task 已退役时实时快照明确不可用，原历史独立保留。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Combat|Observation")
	bool Sample(double ElapsedSeconds, FString& OutDiagnostic);

	/** 幂等解除精确自有订阅和原源引用；纯数据保留供读回。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Combat|Observation")
	void StopObservation();

	UFUNCTION(BlueprintPure, Category = "GGYGO|Combat|Observation")
	FString GetObservationJson() const;

	virtual void BeginDestroy() override;
private:
	struct FState;
	TSharedPtr<FState> State;
	void OnOriginalTerminationCompleted(const FGGYGOAbilityTerminationCompletedNotice& Notice);
	void OnWorldCleanup(UWorld* World, bool bSessionEnded, bool bCleanupResources);
	void OnEndPIE(bool bSimulating);
	void ReleaseObservation(const FString& Reason);
	bool SampleFX(double ElapsedSeconds, FString& OutDiagnostic);
	bool AppendFXFacts(const TArray<FGGYGOMontageFXObservationFact>& Facts, double ElapsedSeconds, FString& OutDiagnostic);
};
