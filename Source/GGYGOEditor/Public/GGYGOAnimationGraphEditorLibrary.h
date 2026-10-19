/** @file GGYGOAnimationGraphEditorLibrary.h @brief 动画图公开关联、原生节点、显式动态属性与状态机过渡读取的编辑器入口。 */
#pragma once

#include "CoreMinimal.h"
#include "Curves/CurveFloat.h"
#include "GGYGOAnimationCurveSnapshotLibrary.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GGYGOAnimationGraphEditorLibrary.generated.h"

class UBlueprint;
class UEdGraph;
class UEdGraphNode;

/** 当前一次读取的作者图关联；对象引用不代表播放来源或运行帧已经验证。 */
USTRUCT(BlueprintType)
struct FGGYGOAnimationGetterAssociation
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UObject> SourceNode = nullptr;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UObject> SourceStateNode = nullptr;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UEdGraph> SourceStateGraph = nullptr;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UClass> GetterClass = nullptr;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	FString SourceBlueprintPath;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	FName FunctionName;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	FString Error;
};

/** 单次函数 Entry 作者配置读值；false 和零 flags 不代表读取失败或配置已验收。 */
USTRUCT(BlueprintType)
struct FGGYGOAnimationFunctionEntryAuthoringResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bThreadSafe = false;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	int32 ExtraFlags = 0;
	/** 原生 GetFunctionFlags：解析到的函数 flags 与本 Entry 的 ExtraFlags 合并值。 */
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	int32 FunctionFlags = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	FString Error;
};

/** 单次动画节点作者配置读值；返回完整动态属性集合，空集合也可读取成功。 */
USTRUCT(BlueprintType)
struct FGGYGOAnimationNodeAuthoringResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bSucceeded = false;
	/** 原节点集合的值复制，按 FName 字典序排序，不筛选或补入业务所需属性。 */
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TArray<FName> AlwaysDynamicProperties;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	FString Error;
};

/** 单次作者图编辑结果；保留失败诊断，不依赖脚本 bool/out 参数转换。 */
USTRUCT(BlueprintType)
struct FGGYGOAnimationGraphEditResult
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	FString Error;
	/** 原 Blueprint 图拥有新节点；动态属性操作不创建节点。 */
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UEdGraphNode> Node = nullptr;
};

/** 一条过渡的作者事实。方向取自原生输入/输出 pin 的唯一连接，不代表运行时当前状态。 */
USTRUCT(BlueprintType)
struct FGGYGOAnimationStateTransitionInfo
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UEdGraphNode> Transition = nullptr;
	/** 实际求值的规则图；共享规则时可能由另一过渡拥有。 */
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UEdGraph> RuleGraph = nullptr;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bRuleGraphOwned = false;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UEdGraphNode> PreviousState = nullptr;
	/** 前一普通状态自身拥有的姿态子图。 */
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UEdGraph> PreviousStateGraph = nullptr;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UEdGraphNode> NextState = nullptr;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UEdGraph> NextStateGraph = nullptr;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bBidirectional = false;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bSharedRules = false;
	/** 原生 IsBoundGraphShared：另一状态类节点持有同一规则图。 */
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bBoundGraphShared = false;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bDisabled = false;
	/** 自动规则按相关资产剩余时间触发，可绕过规则图结果。 */
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bAutomaticRule = false;
	/** 原生 ETransitionLogicType 值；Custom 使用另一张混合图。 */
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	uint8 LogicType = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bHasCustomTransitionGraph = false;
};

/** 单个作者状态机的全部过渡；任一过渡端点或规则图失效时整体失败，不返回部分结果。 */
USTRUCT(BlueprintType)
struct FGGYGOAnimationStateTransitionsResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	FString Error;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UEdGraph> StateMachineGraph = nullptr;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TArray<FGGYGOAnimationStateTransitionInfo> Transitions;
};

/** 一次 /Temp 蓝图副本结果；失败时 Blueprint 仅在副本已创建但校验失败时非空，供调用方定位诊断。 */
USTRUCT(BlueprintType)
struct FGGYGOBlueprintDuplicateResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	FString Error;
	UPROPERTY(BlueprintReadOnly, Category = "Animation|Graph")
	TObjectPtr<UBlueprint> Blueprint = nullptr;
};

/** 无常驻状态。只使用 UE 公开的作者图数据及 API，不访问引擎私有执行缓存。 */
UCLASS()
class GGYGOEDITOR_API UGGYGOAnimationGraphEditorLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** 在明确 Owner 的非 PIE 动画作者图中，通过原生 creator 创建指定动画节点。
	 * @param NodeClass 原 UAnimGraphNode_Base 的可构造派生类，不使用本地化菜单名。
	 * @param Position 作者图位置，不影响运行时姿态。
	 * @return 节点由原图拥有；失败在修改图前返回诊断。调用方保护 dirty，连接后
	 * 完整编译、精确读回并单包保存；本入口不保存或求值。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOAnimationGraphEditResult CreateAnimationNode(UBlueprint* Owner, UEdGraph* Graph,
		UClass* NodeClass, FVector2D Position);

	/** 精确返回原 K2 AnimGetter 的公开图关联；不靠标题推测来源。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOAnimationGetterAssociation ReadGetterAssociation(UObject* Node);

	/** 只读同一原 AnimBlueprint 所登记函数图中唯一 Entry 的作者配置。
	 * @param FunctionGraph Owner 的 FunctionGraphs 实际成员。
	 * @param EntryNode 该图实际拥有并登记的唯一 UK2Node_FunctionEntry，拒绝 CDO 和游离节点。
	 * @return 当前调用的值复制；合法 false/零值仍成功，业务权限由调用方校验。不修改、编译或保存。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOAnimationFunctionEntryAuthoringResult ReadFunctionEntryAuthoring(UBlueprint* Owner,
		UEdGraph* FunctionGraph, UObject* EntryNode);

	/** 只读同一原 AnimBlueprint 所登记作者图中实际动画节点的完整动态属性集合。
	 * @param Node 原 UAnimGraphNode_Base 成员，拒绝 CDO、游离节点和未登记的图。
	 * @return 当前调用的稳定排序值复制；空集合仍成功，必需属性由调用方校验。不修改、编译或保存。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOAnimationNodeAuthoringResult ReadAnimationNodeAuthoring(UBlueprint* Owner, UObject* Node);

	/** 通过原生 GetTargetFunction 读取调用目标；非调用节点或未解析目标返回 None。 */
	UFUNCTION(BlueprintPure, Category = "GGYGO|Editor|Animation")
	static FName GetCalledFunctionName(UObject* Node);

	/** 原曲线的公开 const key 视图值复制；空数组仅表示原曲线无键，不代表配置有效。 */
	UFUNCTION(BlueprintPure, Category = "GGYGO|Editor|Animation")
	static TArray<FGGYGOFloatCurveKeySnapshot> ReadRuntimeCurveKeys(const FRuntimeFloatCurve& Curve);

	/** 在明确 Owner 的非 PIE 作者图中，将指定可编辑 FoldProperty 标为始终动态。
	 * 校验全部属性后才写，不主动重建、编译、保存、求值或改变运行时姿态；调用方负责
	 * 原始 dirty 保护、完整编译与精确读回。幂等，不删除原来已有的动态属性。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOAnimationGraphEditResult MarkAnimationNodePropertiesDynamic(UBlueprint* Owner, UObject* Node,
		const TArray<FName>& Properties);

	/** 只读列出原 AnimBlueprint 拥有的一个作者状态机中全部过渡的原生端点与规则标志。
	 * 过渡节点不是 K2 节点，脚本图编辑接口无法枚举；共享规则的过渡也不拥有可列出的规则图。
	 * 当前只支持普通状态端点，Alias/Conduit 等端点明确拒绝。不修改、编译或求值。
	 * @param StateMachineGraph 由该 Owner 中状态机节点反向持有的作者图。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOAnimationStateTransitionsResult ReadStateMachineTransitions(UBlueprint* Owner, UEdGraph* StateMachineGraph);

	/** 非 PIE 时把一个已加载 AnimBlueprint 复制到全新的 /Temp 包，供验证宿主在副本上做图编辑与编译。
	 * /Temp 是只读挂载根：AssetTools/EditorAssetLibrary 复制会拒绝，也不会被内容保存流程写盘。
	 * 原生 PostDuplicate 为副本重新生成自己的类；不通知资产注册表、不主动标脏、不保存。
	 * 源包若因复制变脏则返回失败（不回滚、不清 dirty），由调用方的 dirty 保护如实记录。
	 * @param TempPackageName 必须以 /Temp/ 开头且尚无已加载包；资产名取包名末段。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOBlueprintDuplicateResult DuplicateAnimBlueprintToTemp(UBlueprint* Source, const FString& TempPackageName);
};
