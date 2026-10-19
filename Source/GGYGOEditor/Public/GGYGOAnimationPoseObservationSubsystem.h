/** @file GGYGOAnimationPoseObservationSubsystem.h @brief 原 Mesh 自然完成骨骼求值后的有界只读观测。 */
#pragma once

#include "CoreMinimal.h"
#include "Subsystems/EngineSubsystem.h"
#include "GGYGOAnimationPoseObservationSubsystem.generated.h"

class ACharacter;
class UGGYGOAnimInstanceBase;
class UGGYGOCharacterMovementComponent;
class USkeletalMesh;
class USkeletalMeshComponent;
class FJsonObject;

/**
 * 仅在 GGYGOEditor 模块加载，随 Editor 进程的 Engine 生命周期拥有观察回调与值记录。
 * 不得刷新骨骼、推进动画/世界、保存包或改变运动状态。
 * Begin 后等待原 Mesh 的 BoneTransformsFinalized；显式 Stop、EndPIE、身份失效、
 * 达到容量和 Deinitialize 均释放回调。读取结果不会把观察事实判为专项通过。
 */
UCLASS()
class GGYGOEDITOR_API UGGYGOAnimationPoseObservationSubsystem : public UEngineSubsystem
{
	GENERATED_BODY()

public:
	virtual void Initialize(FSubsystemCollectionBase& Collection) override;
	virtual void Deinitialize() override;

	/** @param BoneNames 实际生产 Mesh 中需要观察的骨骼；不能用缺失骨骼的默认变换代替。
	 * @param MaxRecords 原生 finalize 回调记录上限，范围 1..4096。
	 * @return 是否成功注册；成功注册不代表已经发生过求值。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Animation|Observation")
	bool BeginObservation(USkeletalMeshComponent* Mesh, const TArray<FName>& BoneNames,
		int32 MaxRecords, FString& OutDiagnostic);

	/** 幂等释放自己的回调，保留已记录事实供读回。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Animation|Observation")
	void StopObservation();

	/**
	 * 返回指定范围的原生记录 JSON，保留完整 Records 供无参全量取证。
	 * 不持有动作 binding、资源或播放许可，读取不推进观察位置。
	 * @param FirstRecordIndex 原 Records 的绝对下标，合法范围为 0..record_count（含末端）。
	 * @param MaxRecordCount -1 读取余下全部，0 只读元信息，正数最多读取指定条数。
	 * @return 原字段及 record_count、records_start_index、read_success；非法范围返回
	 * read_success=false、diagnostic 和空 records，观察状态及完整记录保持原状。
	 */
	UFUNCTION(BlueprintPure, Category = "GGYGO|Animation|Observation")
	FString GetObservationJson(int32 FirstRecordIndex = 0, int32 MaxRecordCount = -1) const;

private:
	void OnBoneTransformsFinalized();
	void OnEndPIE(bool bSimulating);
	void ReleaseObservation(const FString& Reason);

	TWeakObjectPtr<USkeletalMeshComponent> ObservedMesh;
	TWeakObjectPtr<USkeletalMesh> ObservedMeshAsset;
	TWeakObjectPtr<UGGYGOAnimInstanceBase> ObservedAnim;
	TWeakObjectPtr<ACharacter> ObservedCharacter;
	TWeakObjectPtr<UGGYGOCharacterMovementComponent> ObservedMovement;
	TArray<FName> ObservedBoneNames;
	TArray<TSharedPtr<FJsonObject>> Records;
	FDelegateHandle FinalizedHandle;
	FDelegateHandle EndPIEHandle;
	int32 RecordLimit = 0;
	FString MeshPath;
	FString StopReason = TEXT("NotStarted");
};
