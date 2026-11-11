/** @file GGYGOBossCombatAssetLibrary.cpp */
#include "GGYGOBossCombatAssetLibrary.h"

#include "AI/Boss/BehaviorTree/BTTask_GGYGOActivateAbility.h"
#include "AI/Boss/BehaviorTree/BTTask_GGYGOChooseBossAction.h"
#include "AI/Boss/GGYGOBossDefinition.h"
#include "AI/Boss/GGYGOBossState.h"
#include "AI/Boss/GGYGOBossAIController.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Name.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Object.h"
#include "BehaviorTree/Composites/BTComposite_Selector.h"
#include "BehaviorTree/Composites/BTComposite_Sequence.h"
#include "BehaviorTree/Tasks/BTTask_MoveTo.h"
#include "BehaviorTree/Tasks/BTTask_RotateToFaceBBEntry.h"
#include "BehaviorTree/Tasks/BTTask_Wait.h"
#include "BehaviorTree/BTService.h"
#include "BehaviorTree/Services/BTService_BlueprintBase.h"
#include "BlueprintGameplayTagLibrary.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraphSchema_K2.h"
#include "Engine/Blueprint.h"
#include "GameFramework/Actor.h"
#include "GameFramework/Pawn.h"
#include "K2Node_BreakStruct.h"
#include "K2Node_CallFunction.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_Event.h"
#include "K2Node_GetArrayItem.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_VariableGet.h"
#include "Kismet/KismetMathLibrary.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Kismet2/KismetEditorUtilities.h"
#include "KismetCompiler.h"
#include "UObject/UnrealType.h"

#include UE_INLINE_GENERATED_CPP_BY_NAME(GGYGOBossCombatAssetLibrary)

namespace
{
	struct FDecisionGraph
	{
		UEdGraph* Graph;
		FString& Error;
		template <typename T> T* Node(int32 X, int32 Y)
		{
			T* Result = NewObject<T>(Graph, NAME_None, RF_Transactional);
			Graph->AddNode(Result, false, false);
			Result->CreateNewGuid(); Result->NodePosX = X; Result->NodePosY = Y;
			return Result;
		}
		void Finish(UK2Node* Value) { Value->PostPlacedNewNode(); Value->AllocateDefaultPins(); }
		void Link(UEdGraphPin* From, UEdGraphPin* To)
		{
			if (!From || !To || !GetDefault<UEdGraphSchema_K2>()->TryCreateConnection(From, To))
			{
				if (Error.IsEmpty()) { Error = TEXT("业务图引脚连接失败；保留现场，不保存。"); }
			}
		}
		UK2Node_CallFunction* Call(UClass* Owner, FName Name, int32 X, int32 Y)
		{
			auto* Result = Node<UK2Node_CallFunction>(X, Y);
			Result->SetFromFunction(Owner->FindFunctionByName(Name)); Finish(Result); return Result;
		}
		UK2Node_VariableGet* Variable(UClass* Owner, FName Name, UEdGraphPin* Source, int32 X, int32 Y)
		{
			auto* Result = Node<UK2Node_VariableGet>(X, Y);
			Result->VariableReference.SetExternalMember(Name, Owner); Finish(Result);
			Link(Source, Result->FindPin(UEdGraphSchema_K2::PN_Self)); return Result;
		}
		UK2Node_IfThenElse* Branch(int32 X, int32 Y)
		{
			auto* Result = Node<UK2Node_IfThenElse>(X, Y); Finish(Result); return Result;
		}
		UK2Node_Event* Event(UClass* Owner, FName Name)
		{
			auto* Result = Node<UK2Node_Event>(0, 0);
			Result->EventReference.SetExternalMember(Name, Owner); Result->bOverrideFunction = true; Finish(Result); return Result;
		}
	};

	UEdGraphPin* ReturnPin(UK2Node* Node) { return Node->FindPin(UEdGraphSchema_K2::PN_ReturnValue); }
	UEdGraphPin* SelfPin(UK2Node* Node) { return Node->FindPin(UEdGraphSchema_K2::PN_Self); }
	UEdGraphPin* ExecPin(UK2Node* Node) { return Node->FindPin(UEdGraphSchema_K2::PN_Execute); }
	UEdGraphPin* ThenPin(UK2Node* Node) { return Node->FindPin(UEdGraphSchema_K2::PN_Then); }

	UEdGraph* PrepareDecisionGraph(UBlueprint* Blueprint, FString& Error)
	{
		if (Blueprint->UbergraphPages.Num() > 1) { Error = TEXT("已有多个事件图，拒绝覆盖。"); return nullptr; }
		UEdGraph* Graph = Blueprint->UbergraphPages.IsEmpty() ? nullptr : Blueprint->UbergraphPages[0];
		if (Graph)
		{
			for (UEdGraphNode* Node : Graph->Nodes)
			{
				if (!Node->IsA<UK2Node_Event>() || Node->Pins.ContainsByPredicate(
					[](const UEdGraphPin* Pin) { return !Pin->LinkedTo.IsEmpty(); }))
				{
					Error = TEXT("已有业务图，拒绝重建；请核实际图差异。"); return nullptr;
				}
			}
			const auto PreviousNodes = Graph->Nodes;
			for (UEdGraphNode* Node : PreviousNodes) { Node->DestroyNode(); }
		}
		else
		{
			Graph = FBlueprintEditorUtils::CreateNewGraph(Blueprint, TEXT("EventGraph"), UEdGraph::StaticClass(), UEdGraphSchema_K2::StaticClass());
			FBlueprintEditorUtils::AddUbergraphPage(Blueprint, Graph);
		}
		return Graph;
	}

	bool CompileDecisionBlueprint(UBlueprint* Blueprint, FString& Error)
	{
		FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Blueprint);
		FCompilerResultsLog Log;
		FKismetEditorUtilities::CompileBlueprint(Blueprint, EBlueprintCompileOptions::None, &Log);
		if (Log.NumErrors || Log.NumWarnings || Blueprint->Status != BS_UpToDate)
		{
			Error = FString::Printf(TEXT("蓝图 [%s] 编译未干净通过：Errors=%d Warnings=%d。"),
				*Blueprint->GetPathName(), Log.NumErrors, Log.NumWarnings); return false;
		}
		return true;
	}

	FBlackboardKeySelector* KeySelector(UBTNode* Node, FName PropertyName)
	{
		FStructProperty* Property = FindFProperty<FStructProperty>(Node->GetClass(), PropertyName);
		return Property && Property->Struct == FBlackboardKeySelector::StaticStruct()
			? Property->ContainerPtrToValuePtr<FBlackboardKeySelector>(Node) : nullptr;
	}

	void SetKey(UBTNode* Node, FName PropertyName, FName KeyName)
	{
		// 读取编辑器可编辑的反射属性，与细节面板写入相同；不接触运行时节点内存。
		FBlackboardKeySelector* Selector = KeySelector(Node, PropertyName);
		check(Selector);
		Selector->SelectedKeyName = KeyName;
	}

	bool HasKey(const UBTNode* Node, FName PropertyName, FName KeyName)
	{
		const FBlackboardKeySelector* Selector = Node ? KeySelector(const_cast<UBTNode*>(Node), PropertyName) : nullptr;
		return Selector && Selector->SelectedKeyName == KeyName;
	}

	template <typename PropertyType>
	const PropertyType* RequireServiceField(FName FieldName, FString& OutError)
	{
		const PropertyType* Property = FindFProperty<PropertyType>(UBTService::StaticClass(), FieldName);
		if (!Property && OutError.IsEmpty())
		{
			OutError = FString::Printf(TEXT("原生类 [%s] 必需字段 [%s] 缺失或类型不符，拒绝制作/读回。"),
				*UBTService::StaticClass()->GetPathName(), *FieldName.ToString());
		}
		return Property;
	}

	UBTTask_Wait* MakeWait(UBehaviorTree* Tree, float Interval)
	{
		UBTTask_Wait* Wait = NewObject<UBTTask_Wait>(Tree, NAME_None, RF_Transactional);
		Wait->WaitTime = Interval;
		Wait->RandomDeviation = 0.0f;
		return Wait;
	}
}

FGGYGOBossCombatAssetResult UGGYGOBossCombatAssetLibrary::BuildDecisionBlueprints(UBlueprint* StateBlueprint,
	UBlueprint* TargetServiceBlueprint, const UGGYGOBossDefinition* Definition)
{
	FGGYGOBossCombatAssetResult Result;
	Result.bSucceeded = BuildDecisionBlueprintsInternal(StateBlueprint, TargetServiceBlueprint, Definition, Result.Error);
	return Result;
}

FGGYGOBossCombatAssetResult UGGYGOBossCombatAssetLibrary::ValidateDecisionBlueprints(const UBlueprint* StateBlueprint,
	const UBlueprint* TargetServiceBlueprint, const UGGYGOBossDefinition* Definition)
{
	FGGYGOBossCombatAssetResult Result;
	Result.bSucceeded = ValidateDecisionBlueprintsInternal(StateBlueprint, TargetServiceBlueprint, Definition, Result.Error);
	return Result;
}

FGGYGOBossCombatAssetResult UGGYGOBossCombatAssetLibrary::BuildCombatTree(UBehaviorTree* Tree,
	UBlackboardData* Blackboard, const UGGYGOBossDefinition* Definition, float DecisionInterval, float TargetInterval, bool bUseNativeApproach)
{
	FGGYGOBossCombatAssetResult Result;
	Result.bSucceeded = BuildCombatTreeInternal(Tree, Blackboard, Definition, DecisionInterval, TargetInterval, bUseNativeApproach, Result.Error);
	return Result;
}

FGGYGOBossCombatAssetResult UGGYGOBossCombatAssetLibrary::ValidateCombatTree(const UBehaviorTree* Tree,
	const UBlackboardData* Blackboard, const UGGYGOBossDefinition* Definition, float DecisionInterval, float TargetInterval, bool bUseNativeApproach)
{
	FGGYGOBossCombatAssetResult Result;
	Result.bSucceeded = ValidateCombatTreeInternal(Tree, Blackboard, Definition, DecisionInterval, TargetInterval, bUseNativeApproach, Result.Error);
	return Result;
}

bool UGGYGOBossCombatAssetLibrary::BuildDecisionBlueprintsInternal(UBlueprint* StateBlueprint, UBlueprint* TargetServiceBlueprint,
	const UGGYGOBossDefinition* Definition, FString& OutError)
{
	OutError.Reset();
	if (!StateBlueprint || !TargetServiceBlueprint || !Definition || Definition->Phases.Num() != 2
		|| StateBlueprint->ParentClass != AGGYGOBossState::StaticClass()
		|| TargetServiceBlueprint->ParentClass != UBTService_BlueprintBase::StaticClass())
	{
		OutError = TEXT("需要原生BossState/BTService子蓝图及明确两阶段定义。"); return false;
	}
	if (ValidateDecisionBlueprintsInternal(StateBlueprint, TargetServiceBlueprint, Definition, OutError)) { return true; }
	OutError.Reset();
	const FBoolProperty* SearchStartField = RequireServiceField<FBoolProperty>(TEXT("bCallTickOnSearchStart"), OutError);
	const FFloatProperty* DeviationField = RequireServiceField<FFloatProperty>(TEXT("RandomDeviation"), OutError);
	if (!SearchStartField || !DeviationField) { return false; }
	UEdGraph* StateEvents = PrepareDecisionGraph(StateBlueprint, OutError);
	if (!StateEvents) { return false; }
	UEdGraph* TargetEvents = PrepareDecisionGraph(TargetServiceBlueprint, OutError);
	if (!TargetEvents) { return false; }
	FDecisionGraph S{ StateEvents, OutError };
	auto* HealthEvent = S.Event(AGGYGOBossState::StaticClass(), TEXT("OnBossHealthChanged"));
	HealthEvent->NodeComment = TEXT("生命事实到阶段条件：初始阶段、存活且不高于下一阶段阈值时换池");
	auto* DefinitionCall = S.Call(AGGYGOBossState::StaticClass(), TEXT("GetBossDefinition"), 0, -600);
	auto* InitialTag = S.Variable(UGGYGOBossDefinition::StaticClass(), TEXT("InitialPhaseTag"), ReturnPin(DefinitionCall), 260, -600);
	auto* CurrentTag = S.Call(AGGYGOBossState::StaticClass(), TEXT("GetCurrentPhaseTag"), 260, -440);
	auto* SamePhase = S.Call(UBlueprintGameplayTagLibrary::StaticClass(), TEXT("EqualEqual_GameplayTag"), 520, -520);
	S.Link(InitialTag->GetValuePin(), SamePhase->FindPin(TEXT("A")));
	S.Link(ReturnPin(CurrentTag), SamePhase->FindPin(TEXT("B")));
	auto* PositiveHealth = S.Call(UKismetMathLibrary::StaticClass(), TEXT("Greater_DoubleDouble"), 260, 100);
	auto* PositiveMax = S.Call(UKismetMathLibrary::StaticClass(), TEXT("Greater_DoubleDouble"), 260, 300);
	S.Link(HealthEvent->FindPin(TEXT("Health")), PositiveHealth->FindPin(TEXT("A")));
	S.Link(HealthEvent->FindPin(TEXT("MaxHealth")), PositiveMax->FindPin(TEXT("A")));
	auto* Alive = S.Call(UKismetMathLibrary::StaticClass(), TEXT("BooleanAND"), 520, 120);
	S.Link(ReturnPin(PositiveHealth), Alive->FindPin(TEXT("A"))); S.Link(ReturnPin(PositiveMax), Alive->FindPin(TEXT("B")));
	auto* CanProgress = S.Call(UKismetMathLibrary::StaticClass(), TEXT("BooleanAND"), 760, -120);
	S.Link(ReturnPin(Alive), CanProgress->FindPin(TEXT("A"))); S.Link(ReturnPin(SamePhase), CanProgress->FindPin(TEXT("B")));
	auto* Gate = S.Branch(1000, 0);
	S.Link(ThenPin(HealthEvent), ExecPin(Gate)); S.Link(ReturnPin(CanProgress), Gate->GetConditionPin());
	auto* Phases = S.Variable(UGGYGOBossDefinition::StaticClass(), TEXT("Phases"), ReturnPin(DefinitionCall), 520, -820);
	auto* Next = S.Node<UK2Node_GetArrayItem>(780, -820); S.Finish(Next);
	Next->GetIndexPin()->DefaultValue = TEXT("1"); S.Link(Phases->GetValuePin(), Next->GetTargetArrayPin());
	auto* NextFields = S.Node<UK2Node_BreakStruct>(1040, -820);
	NextFields->StructType = FGGYGOBossPhaseDefinition::StaticStruct(); S.Finish(NextFields);
	S.Link(Next->GetResultPin(), NextFields->FindPin(FGGYGOBossPhaseDefinition::StaticStruct()->GetFName()));
	auto* Fraction = S.Call(UKismetMathLibrary::StaticClass(), TEXT("Divide_DoubleDouble"), 1000, 280);
	S.Link(HealthEvent->FindPin(TEXT("Health")), Fraction->FindPin(TEXT("A")));
	S.Link(HealthEvent->FindPin(TEXT("MaxHealth")), Fraction->FindPin(TEXT("B")));
	auto* Threshold = S.Call(UKismetMathLibrary::StaticClass(), TEXT("LessEqual_DoubleDouble"), 1280, 280);
	S.Link(ReturnPin(Fraction), Threshold->FindPin(TEXT("A")));
	S.Link(NextFields->FindPin(TEXT("EnterHealthThreshold")), Threshold->FindPin(TEXT("B")));
	auto* AtThreshold = S.Branch(1500, 0); S.Link(ThenPin(Gate), ExecPin(AtThreshold));
	S.Link(ReturnPin(Threshold), AtThreshold->GetConditionPin());
	auto* SetPhase = S.Call(AGGYGOBossState::StaticClass(), TEXT("SetCurrentPhase"), 1760, 0);
	S.Link(ThenPin(AtThreshold), ExecPin(SetPhase));
	S.Link(NextFields->FindPin(TEXT("PhaseTag")), SetPhase->FindPin(TEXT("NewPhaseTag")));
	if (!OutError.IsEmpty() || !CompileDecisionBlueprint(StateBlueprint, OutError)) { return false; }

	FDecisionGraph T{ TargetEvents, OutError };
	auto* Tick = T.Event(UBTService_BlueprintBase::StaticClass(), TEXT("ReceiveTickAI"));
	Tick->NodeComment = TEXT("保持仍受控且在丢失距离内的原目标；否则按获取范围重新查询");
	auto* Controller = T.Node<UK2Node_DynamicCast>(280, 0);
	Controller->TargetType = AGGYGOBossAIController::StaticClass(); T.Finish(Controller); Controller->SetPurity(false);
	T.Link(ThenPin(Tick), ExecPin(Controller)); T.Link(Tick->FindPin(TEXT("OwnerController")), Controller->GetCastSourcePin());
	auto* ValidPawn = T.Call(UKismetSystemLibrary::StaticClass(), TEXT("IsValid"), 280, 260);
	T.Link(Tick->FindPin(TEXT("ControlledPawn")), ValidPawn->FindPin(TEXT("Object")));
	auto* PawnGate = T.Branch(560, 0); T.Link(Controller->GetValidCastPin(), ExecPin(PawnGate));
	T.Link(ReturnPin(ValidPawn), PawnGate->GetConditionPin());
	auto* Target = T.Call(AGGYGOBossAIController::StaticClass(), TEXT("GetCombatTarget"), 560, -300);
	T.Link(Controller->GetCastResultPin(), SelfPin(Target));
	auto* PlayerPawn = T.Node<UK2Node_DynamicCast>(840, 0);
	PlayerPawn->TargetType = APawn::StaticClass(); T.Finish(PlayerPawn); PlayerPawn->SetPurity(false);
	T.Link(ThenPin(PawnGate), ExecPin(PlayerPawn)); T.Link(ReturnPin(Target), PlayerPawn->GetCastSourcePin());
	auto* Controlled = T.Call(APawn::StaticClass(), TEXT("IsPlayerControlled"), 840, 260);
	T.Link(PlayerPawn->GetCastResultPin(), SelfPin(Controlled));
	auto* PlayerGate = T.Branch(1120, 0); T.Link(PlayerPawn->GetValidCastPin(), ExecPin(PlayerGate));
	T.Link(ReturnPin(Controlled), PlayerGate->GetConditionPin());
	auto* State = T.Call(AGGYGOBossAIController::StaticClass(), TEXT("GetBossState"), 560, -600);
	T.Link(Controller->GetCastResultPin(), SelfPin(State));
	auto* Data = T.Call(AGGYGOBossState::StaticClass(), TEXT("GetBossDefinition"), 840, -600);
	T.Link(ReturnPin(State), SelfPin(Data));
	auto* LoseDistance = T.Variable(UGGYGOBossDefinition::StaticClass(), TEXT("TargetLoseDistance"), ReturnPin(Data), 1120, -500);
	auto* Distance = T.Call(AActor::StaticClass(), TEXT("GetDistanceTo"), 1120, 260);
	T.Link(Tick->FindPin(TEXT("ControlledPawn")), SelfPin(Distance));
	T.Link(PlayerPawn->GetCastResultPin(), Distance->FindPin(TEXT("OtherActor")));
	auto* InRange = T.Call(UKismetMathLibrary::StaticClass(), TEXT("LessEqual_DoubleDouble"), 1400, 260);
	T.Link(ReturnPin(Distance), InRange->FindPin(TEXT("A"))); T.Link(LoseDistance->GetValuePin(), InRange->FindPin(TEXT("B")));
	auto* Keep = T.Branch(1680, 0); T.Link(ThenPin(PlayerGate), ExecPin(Keep));
	T.Link(ReturnPin(InRange), Keep->GetConditionPin());
	auto* AcquireDistance = T.Variable(UGGYGOBossDefinition::StaticClass(), TEXT("TargetAcquireDistance"), ReturnPin(Data), 1400, -760);
	auto* Nearest = T.Call(AGGYGOBossAIController::StaticClass(), TEXT("FindNearestCombatTarget"), 1680, -620);
	T.Link(Controller->GetCastResultPin(), SelfPin(Nearest)); T.Link(AcquireDistance->GetValuePin(), Nearest->FindPin(TEXT("MaxDistance")));
	auto* SetTarget = T.Call(AGGYGOBossAIController::StaticClass(), TEXT("SetCombatTarget"), 1960, 400);
	T.Link(Controller->GetCastResultPin(), SelfPin(SetTarget)); T.Link(ReturnPin(Nearest), SetTarget->FindPin(TEXT("Target")));
	T.Link(PlayerPawn->GetInvalidCastPin(), ExecPin(SetTarget));
	T.Link(PlayerGate->GetElsePin(), ExecPin(SetTarget)); T.Link(Keep->GetElsePin(), ExecPin(SetTarget));
	if (!OutError.IsEmpty() || !CompileDecisionBlueprint(TargetServiceBlueprint, OutError)) { return false; }
	UObject* ServiceDefaults = TargetServiceBlueprint->GeneratedClass->GetDefaultObject();
	SearchStartField->SetPropertyValue_InContainer(ServiceDefaults, true);
	DeviationField->SetPropertyValue_InContainer(ServiceDefaults, 0.0f);
	return ValidateDecisionBlueprintsInternal(StateBlueprint, TargetServiceBlueprint, Definition, OutError);
}

bool UGGYGOBossCombatAssetLibrary::ValidateDecisionBlueprintsInternal(const UBlueprint* StateBlueprint,
	const UBlueprint* TargetServiceBlueprint, const UGGYGOBossDefinition* Definition, FString& OutError)
{
	OutError.Reset();
	if (!StateBlueprint || !TargetServiceBlueprint || !Definition || Definition->Phases.Num() != 2
		|| StateBlueprint->ParentClass != AGGYGOBossState::StaticClass()
		|| TargetServiceBlueprint->ParentClass != UBTService_BlueprintBase::StaticClass()
		|| StateBlueprint->Status != BS_UpToDate || TargetServiceBlueprint->Status != BS_UpToDate
		|| StateBlueprint->UbergraphPages.Num() != 1 || TargetServiceBlueprint->UbergraphPages.Num() != 1
		|| !StateBlueprint->UbergraphPages[0] || !TargetServiceBlueprint->UbergraphPages[0]
		|| !StateBlueprint->GeneratedClass || !TargetServiceBlueprint->GeneratedClass)
	{
		OutError = TEXT("阶段/目标蓝图缺少实际已编译事件图或父类不符。"); return false;
	}
	const auto FindCall = [](const UBlueprint* BP, FName Name) -> const UK2Node_CallFunction*
	{
		const UK2Node_CallFunction* Found = nullptr;
		for (const UEdGraphNode* Node : BP->UbergraphPages[0]->Nodes)
		{
			if (const auto* Call = Cast<UK2Node_CallFunction>(Node); Call && Call->FunctionReference.GetMemberName() == Name)
			{
				if (Found) { return nullptr; } Found = Call;
			}
		}
		return Found;
	};
	const auto HasEvent = [](const UBlueprint* BP, FName Name)
	{
		return BP->UbergraphPages[0]->Nodes.ContainsByPredicate([Name](const UEdGraphNode* Node)
		{
			const auto* Event = Cast<UK2Node_Event>(Node);
			const UEdGraphPin* Then = Event ? Event->FindPin(UEdGraphSchema_K2::PN_Then) : nullptr;
			return Event && Event->EventReference.GetMemberName() == Name && Then && Then->LinkedTo.Num() == 1;
		});
	};
	const auto* SetPhase = FindCall(StateBlueprint, TEXT("SetCurrentPhase"));
	const auto* SetTarget = FindCall(TargetServiceBlueprint, TEXT("SetCombatTarget"));
	if (!HasEvent(StateBlueprint, TEXT("OnBossHealthChanged")) || !SetPhase
		|| !FindCall(StateBlueprint, TEXT("Divide_DoubleDouble")) || !FindCall(StateBlueprint, TEXT("LessEqual_DoubleDouble"))
		|| !SetPhase->FindPin(TEXT("NewPhaseTag")) || SetPhase->FindPin(TEXT("NewPhaseTag"))->LinkedTo.Num() != 1
		|| !SetPhase->FindPin(UEdGraphSchema_K2::PN_Execute)
		|| SetPhase->FindPin(UEdGraphSchema_K2::PN_Execute)->LinkedTo.Num() != 1
		|| !HasEvent(TargetServiceBlueprint, TEXT("ReceiveTickAI")) || !SetTarget
		|| !FindCall(TargetServiceBlueprint, TEXT("GetCombatTarget")) || !FindCall(TargetServiceBlueprint, TEXT("FindNearestCombatTarget"))
		|| !FindCall(TargetServiceBlueprint, TEXT("IsPlayerControlled")) || !FindCall(TargetServiceBlueprint, TEXT("GetDistanceTo"))
		|| !SetTarget->FindPin(TEXT("Target")) || SetTarget->FindPin(TEXT("Target"))->LinkedTo.Num() != 1
		|| !SetTarget->FindPin(UEdGraphSchema_K2::PN_Execute)
		|| SetTarget->FindPin(UEdGraphSchema_K2::PN_Execute)->LinkedTo.Num() != 3)
	{
		OutError = TEXT("实际图缺少阶段条件/动作池接口，或目标保持/重新查询的完整数据路径。"); return false;
	}
	const UObject* ServiceDefaults = TargetServiceBlueprint->GeneratedClass->GetDefaultObject();
	const FBoolProperty* SearchStartField = RequireServiceField<FBoolProperty>(TEXT("bCallTickOnSearchStart"), OutError);
	const FFloatProperty* DeviationField = RequireServiceField<FFloatProperty>(TEXT("RandomDeviation"), OutError);
	if (!SearchStartField || !DeviationField) { return false; }
	if (!SearchStartField->GetPropertyValue_InContainer(ServiceDefaults)
		|| DeviationField->GetPropertyValue_InContainer(ServiceDefaults) != 0.0f)
	{
		OutError = TEXT("目标服务缺少首轮搜索查询或含未配置随机更新偏差。"); return false;
	}
	return true;
}

bool UGGYGOBossCombatAssetLibrary::BuildCombatTreeInternal(UBehaviorTree* Tree, UBlackboardData* Blackboard,
	const UGGYGOBossDefinition* Definition, float DecisionInterval, float TargetInterval, bool bUseNativeApproach, FString& OutError)
{
	OutError.Reset();
	if (Definition && !Definition->ValidateCombatConfiguration(OutError)) { return false; }
	if (!Tree || !Blackboard || !Definition || !FMath::IsFinite(DecisionInterval) || DecisionInterval <= 0.0f
		|| !FMath::IsFinite(TargetInterval) || TargetInterval <= 0.0f || Definition->CombatTargetKey.IsNone()
		|| !Definition->CombatTargetService)
	{
		OutError = TEXT("需要指定 BB/BT/Definition、目标Key、目标服务类及有限正决策/目标更新间隔。");
		return false;
	}
	const FFloatProperty* IntervalField = RequireServiceField<FFloatProperty>(TEXT("Interval"), OutError);
	if (!IntervalField) { return false; }
	Blackboard->Modify();
	Blackboard->Keys.Reset();
	Blackboard->Parent = nullptr;
	Blackboard->UpdatePersistentKey<UBlackboardKeyType_Name>(TEXT("SelectedAction"));
	Blackboard->UpdatePersistentKey<UBlackboardKeyType_Object>(Definition->CombatTargetKey)->BaseClass = AActor::StaticClass();
	Blackboard->UpdateKeyIDs();
	Blackboard->UpdateIfHasSynchronizedKeys();
	Tree->Modify();
	Tree->BlackboardAsset = Blackboard;
	Tree->RootDecorators.Reset();
	Tree->RootDecoratorOps.Reset();
	UBTComposite_Selector* Root = NewObject<UBTComposite_Selector>(Tree, NAME_None, RF_Transactional);
	UBTService* Service = NewObject<UBTService>(Tree, Definition->CombatTargetService, NAME_None, RF_Transactional);
	IntervalField->SetPropertyValue_InContainer(Service, TargetInterval);
	Root->Services.Add(Service);
	UBTComposite_Sequence* Attack = NewObject<UBTComposite_Sequence>(Tree, NAME_None, RF_Transactional);
	UBTTask_RotateToFaceBBEntry* Face = NewObject<UBTTask_RotateToFaceBBEntry>(Tree, NAME_None, RF_Transactional);
	SetKey(Face, TEXT("BlackboardKey"), Definition->CombatTargetKey);
	UBTTask_GGYGOChooseBossAction* Choose = NewObject<UBTTask_GGYGOChooseBossAction>(Tree, NAME_None, RF_Transactional);
	SetKey(Choose, TEXT("TargetActorKey"), Definition->CombatTargetKey);
	UBTTask_GGYGOActivateAbility* Activate = NewObject<UBTTask_GGYGOActivateAbility>(Tree, NAME_None, RF_Transactional);
	Attack->Children.AddDefaulted_GetRef().ChildTask = Face;
	Attack->Children.AddDefaulted_GetRef().ChildTask = Choose;
	Attack->Children.AddDefaulted_GetRef().ChildTask = Activate;
	Attack->Children.AddDefaulted_GetRef().ChildTask = MakeWait(Tree, DecisionInterval);
	Root->Children.AddDefaulted_GetRef().ChildComposite = Attack;
	// 由作者明确选择是否制作原生寻路分支；能力位移模式的距离策略留在动作池资产。
	if (bUseNativeApproach)
	{
		UBTComposite_Sequence* Approach = NewObject<UBTComposite_Sequence>(Tree, NAME_None, RF_Transactional);
		UBTTask_MoveTo* Move = NewObject<UBTTask_MoveTo>(Tree, NAME_None, RF_Transactional);
		SetKey(Move, TEXT("BlackboardKey"), Definition->CombatTargetKey);
		Move->AcceptableRadius = Definition->ApproachDistance;
		Approach->Children.AddDefaulted_GetRef().ChildTask = Move;
		Approach->Children.AddDefaulted_GetRef().ChildTask = MakeWait(Tree, DecisionInterval);
		Root->Children.AddDefaulted_GetRef().ChildComposite = Approach;
	}
	Root->Children.AddDefaulted_GetRef().ChildTask = MakeWait(Tree, DecisionInterval);
	Tree->RootNode = Root;
	return ValidateCombatTreeInternal(Tree, Blackboard, Definition, DecisionInterval, TargetInterval, bUseNativeApproach, OutError);
}

bool UGGYGOBossCombatAssetLibrary::ValidateCombatTreeInternal(const UBehaviorTree* Tree, const UBlackboardData* Blackboard,
	const UGGYGOBossDefinition* Definition, float DecisionInterval, float TargetInterval, bool bUseNativeApproach, FString& OutError)
{
	OutError.Reset();
	const FFloatProperty* IntervalField = RequireServiceField<FFloatProperty>(TEXT("Interval"), OutError);
	if (!IntervalField) { return false; }
	const UBTComposite_Selector* Root = Tree ? Cast<UBTComposite_Selector>(Tree->RootNode) : nullptr;
	if (!Blackboard || !Definition || !Tree || Tree->BlackboardAsset != Blackboard || Blackboard->Parent
		|| Blackboard->Keys.Num() < 2 || Blackboard->Keys.Num() > 3 || !Root
		|| Root->Children.Num() != (bUseNativeApproach ? 3 : 2) || Root->Services.Num() != 1
		|| !Root->Services[0] || Root->Services[0]->GetClass() != Definition->CombatTargetService.Get()
		|| IntervalField->GetPropertyValue_InContainer(Root->Services[0]) != TargetInterval)
	{
		OutError = TEXT("BB/BT 根选择器、目标服务或更新间隔不匹配。");
		return false;
	}
	const FBlackboardEntry* TargetKey = Blackboard->Keys.FindByPredicate(
		[Definition](const FBlackboardEntry& Key) { return Key.EntryName == Definition->CombatTargetKey; });
	const FBlackboardEntry* ActionKey = Blackboard->Keys.FindByPredicate(
		[](const FBlackboardEntry& Key) { return Key.EntryName == TEXT("SelectedAction"); });
	const FBlackboardEntry* SelfKey = Blackboard->Keys.FindByPredicate(
		[](const FBlackboardEntry& Key) { return Key.EntryName == FBlackboard::KeySelf; });
	const UBTComposite_Sequence* Attack = Cast<UBTComposite_Sequence>(Root->Children[0].ChildComposite);
	if (!TargetKey || !TargetKey->KeyType || !TargetKey->KeyType->IsA<UBlackboardKeyType_Object>()
		|| !ActionKey || !ActionKey->KeyType || !ActionKey->KeyType->IsA<UBlackboardKeyType_Name>()
		|| (Blackboard->Keys.Num() == 3 && (!SelfKey || !SelfKey->KeyType || !SelfKey->KeyType->IsA<UBlackboardKeyType_Object>()))
		|| !Attack || Attack->Children.Num() != 4
		|| !Cast<UBTTask_RotateToFaceBBEntry>(Attack->Children[0].ChildTask)
		|| !Cast<UBTTask_GGYGOChooseBossAction>(Attack->Children[1].ChildTask)
		|| !Cast<UBTTask_GGYGOActivateAbility>(Attack->Children[2].ChildTask)
		|| !HasKey(Attack->Children[0].ChildTask, TEXT("BlackboardKey"), Definition->CombatTargetKey)
		|| !HasKey(Attack->Children[1].ChildTask, TEXT("TargetActorKey"), Definition->CombatTargetKey))
	{
		OutError = TEXT("目标/动作 Key 或攻击节点顺序不匹配。");
		return false;
	}
	TArray<const UBTTask_Wait*> Waits = { Cast<UBTTask_Wait>(Attack->Children[3].ChildTask),
		Cast<UBTTask_Wait>(Root->Children.Last().ChildTask) };
	if (bUseNativeApproach)
	{
		const UBTComposite_Sequence* Approach = Cast<UBTComposite_Sequence>(Root->Children[1].ChildComposite);
		if (!Approach || Approach->Children.Num() != 2)
		{ OutError = TEXT("原生寻路分支不匹配。"); return false; }
		const UBTTask_MoveTo* Move = Cast<UBTTask_MoveTo>(Approach->Children[0].ChildTask);
		if (!Move || !HasKey(Move, TEXT("BlackboardKey"), Definition->CombatTargetKey)
			|| !Move->AcceptableRadius.GetKey().IsNone()
			|| Move->AcceptableRadius.GetValue(static_cast<const UBlackboardComponent*>(nullptr)) != Definition->ApproachDistance)
		{ OutError = TEXT("原生 MoveTo 的目标或停止距离不匹配。"); return false; }
		Waits.Add(Cast<UBTTask_Wait>(Approach->Children[1].ChildTask));
	}
	for (const UBTTask_Wait* Wait : Waits)
	{
		if (!Wait || !Wait->WaitTime.GetKey().IsNone() || !Wait->RandomDeviation.GetKey().IsNone()
			|| Wait->WaitTime.GetValue(static_cast<const UBlackboardComponent*>(nullptr)) != DecisionInterval
			|| Wait->RandomDeviation.GetValue(static_cast<const UBlackboardComponent*>(nullptr)) != 0.0f)
		{
			OutError = TEXT("决策等待间隔不匹配。");
			return false;
		}
	}
	return true;
}
