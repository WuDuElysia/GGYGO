/** @file GGYGOBossCombatAssetLibrary.h @brief Boss 战斗树的编辑器制作与读回 */
#pragma once

#include "Kismet/BlueprintFunctionLibrary.h"

#include "GGYGOBossCombatAssetLibrary.generated.h"

class UBehaviorTree;
class UBlackboardData;
class UGGYGOBossDefinition;
class UBlueprint;

/** Python/蓝图始终取得同一种结果；失败诊断不经过 bool+Out 参数的绑定折叠。 */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOBossCombatAssetResult
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Boss")
	bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Boss")
	FString Error;
};

UCLASS()
class GGYGOEDITOR_API UGGYGOBossCombatAssetLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()
public:
	/** 制作真实可编辑的生命条件事件图与目标策略服务图；保留已有人工作图，不保存。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Boss")
	static FGGYGOBossCombatAssetResult BuildDecisionBlueprints(UBlueprint* StateBlueprint, UBlueprint* TargetServiceBlueprint,
		const UGGYGOBossDefinition* Definition);

	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Boss")
	static FGGYGOBossCombatAssetResult ValidateDecisionBlueprints(const UBlueprint* StateBlueprint, const UBlueprint* TargetServiceBlueprint,
		const UGGYGOBossDefinition* Definition);

	/** 仅编辑指定 BB/BT，不保存、不启动行为树；调用方负责所有权、脏包和准确保存范围。
	 * @param bUseNativeApproach 是否制作原生 MoveTo 分支；关闭时由动作池配置接近目标的能力。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Boss")
	static FGGYGOBossCombatAssetResult BuildCombatTree(UBehaviorTree* Tree, UBlackboardData* Blackboard,
		const UGGYGOBossDefinition* Definition, float DecisionInterval, float TargetInterval, bool bUseNativeApproach = true);

	/** 核对实际节点、Key、目标服务、原生移动与等待参数；不会重建或修复资产。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Boss")
	static FGGYGOBossCombatAssetResult ValidateCombatTree(const UBehaviorTree* Tree, const UBlackboardData* Blackboard,
		const UGGYGOBossDefinition* Definition, float DecisionInterval, float TargetInterval, bool bUseNativeApproach = true);

private:
	static bool BuildDecisionBlueprintsInternal(UBlueprint* StateBlueprint, UBlueprint* TargetServiceBlueprint,
		const UGGYGOBossDefinition* Definition, FString& OutError);
	static bool ValidateDecisionBlueprintsInternal(const UBlueprint* StateBlueprint, const UBlueprint* TargetServiceBlueprint,
		const UGGYGOBossDefinition* Definition, FString& OutError);
	static bool BuildCombatTreeInternal(UBehaviorTree* Tree, UBlackboardData* Blackboard,
		const UGGYGOBossDefinition* Definition, float DecisionInterval, float TargetInterval, bool bUseNativeApproach, FString& OutError);
	static bool ValidateCombatTreeInternal(const UBehaviorTree* Tree, const UBlackboardData* Blackboard,
		const UGGYGOBossDefinition* Definition, float DecisionInterval, float TargetInterval, bool bUseNativeApproach, FString& OutError);
};
