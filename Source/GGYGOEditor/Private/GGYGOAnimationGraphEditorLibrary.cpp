/** @file GGYGOAnimationGraphEditorLibrary.cpp @brief 通过公开图/曲线接口提供脚本未暴露的必要作者操作。 */
#include "GGYGOAnimationGraphEditorLibrary.h"

#include "AnimGraphNode_Base.h"
#include "AnimGraphNode_StateMachineBase.h"
#include "AnimStateNode.h"
#include "AnimStateNodeBase.h"
#include "AnimStateTransitionNode.h"
#include "AnimationGraphSchema.h"
#include "AnimationStateMachineGraph.h"
#include "AnimationTransitionGraph.h"
#include "Editor.h"
#include "Animation/AnimBlueprint.h"
#include "EdGraph/EdGraph.h"
#include "K2Node_AnimGetter.h"
#include "K2Node_CallFunction.h"
#include "K2Node_FunctionEntry.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "Misc/PackageName.h"
#include "UObject/Package.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/UnrealType.h"

FGGYGOAnimationGraphEditResult UGGYGOAnimationGraphEditorLibrary::CreateAnimationNode(UBlueprint* Owner,
	UEdGraph* Graph, UClass* NodeClass, FVector2D Position)
{
	check(IsInGameThread());
	FGGYGOAnimationGraphEditResult Result;
	const UAnimationGraphSchema* Schema = Graph ? Cast<UAnimationGraphSchema>(Graph->GetSchema()) : nullptr;
	if (!Cast<UAnimBlueprint>(Owner) || !Graph || Graph->GetTypedOuter<UBlueprint>() != Owner
		|| !Schema || !GEditor || GEditor->PlayWorld)
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Owner=%s Graph=%s 需要同一原 AnimBlueprint 的非 PIE 动画作者图。"),
			*GetPathNameSafe(Owner), *GetPathNameSafe(Graph));
		return Result;
	}
	if (!NodeClass || !NodeClass->IsChildOf(UAnimGraphNode_Base::StaticClass())
		|| NodeClass->HasAnyClassFlags(CLASS_Abstract | CLASS_Deprecated | CLASS_NewerVersionExists)
		|| !NodeClass->GetDefaultObject<UAnimGraphNode_Base>()->IsCompatibleWithGraph(Graph))
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Graph=%s Class=%s 不是与原图兼容的可构造动画节点。"),
			*GetPathNameSafe(Graph), *GetPathNameSafe(NodeClass));
		return Result;
	}
	if (!FMath::IsFinite(Position.X) || !FMath::IsFinite(Position.Y)
		|| Position.X < MIN_int32 || Position.X > MAX_int32 || Position.Y < MIN_int32 || Position.Y > MAX_int32)
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Graph=%s 作者图位置超出有限 int32 范围。"), *Graph->GetPathName());
		return Result;
	}
	Owner->Modify();
	Graph->Modify();
	FGraphNodeCreator<UAnimGraphNode_Base> Creator(*Graph);
	UAnimGraphNode_Base* Node = Creator.CreateUserInvokedNode(false, NodeClass);
	Node->NodePosX = static_cast<int32>(Position.X);
	Node->NodePosY = static_cast<int32>(Position.Y);
	Creator.Finalize();
	// 与 UE 作者入口相同：由 schema 先处理节点引起的结构变化，未处理时
	// 按原节点声明标记 Blueprint。不绕过 schema，也不自行推进或求值。
	if (!Schema->MarkBlueprintDirtyFromNewNode(Owner, Node))
	{
		if (Node->NodeCausesStructuralBlueprintChange())
		{
			FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(Owner);
		}
		else
		{
			FBlueprintEditorUtils::MarkBlueprintAsModified(Owner);
		}
	}
	Graph->NotifyGraphChanged();
	Result.Node = Node;
	Result.bSucceeded = true;
	return Result;
}

FGGYGOAnimationGetterAssociation UGGYGOAnimationGraphEditorLibrary::ReadGetterAssociation(UObject* Node)
{
	check(IsInGameThread());
	FGGYGOAnimationGetterAssociation Result;
	const UK2Node_AnimGetter* Getter = Cast<UK2Node_AnimGetter>(Node);
	if (!Getter)
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Node=%s 不是原 K2 AnimGetter。"), *GetPathNameSafe(Node));
		return Result;
	}
	// 这些是 UE C++ 公开的作者图关联。Python 因缺少 Edit/BlueprintVisible
	// 标志不暴露它们；这里不使用反射私有地址、派生访问或引擎改动。
	Result.SourceNode = Getter->SourceNode;
	Result.SourceStateNode = Getter->SourceStateNode;
	Result.SourceStateGraph = Getter->SourceStateNode ? Getter->SourceStateNode->GetBoundGraph() : nullptr;
	Result.GetterClass = Getter->GetterClass;
	Result.SourceBlueprintPath = GetPathNameSafe(Getter->SourceAnimBlueprint.Get());
	Result.FunctionName = GetCalledFunctionName(Node);
	Result.bSucceeded = true;
	return Result;
}

FGGYGOAnimationFunctionEntryAuthoringResult UGGYGOAnimationGraphEditorLibrary::ReadFunctionEntryAuthoring(
	UBlueprint* Owner, UEdGraph* FunctionGraph, UObject* EntryNode)
{
	check(IsInGameThread());
	FGGYGOAnimationFunctionEntryAuthoringResult Result;
	const UAnimBlueprint* AnimOwner = Cast<UAnimBlueprint>(Owner);
	const UK2Node_FunctionEntry* Entry = Cast<UK2Node_FunctionEntry>(EntryNode);
	if (!IsValid(AnimOwner) || AnimOwner->IsTemplate() || !IsValid(FunctionGraph) || !IsValid(Entry)
		|| Entry->IsTemplate() || FunctionGraph->GetTypedOuter<UBlueprint>() != AnimOwner
		|| !AnimOwner->FunctionGraphs.Contains(FunctionGraph) || Entry->GetOuter() != FunctionGraph
		|| !FunctionGraph->Nodes.Contains(Entry))
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Owner=%s FunctionGraph=%s Entry=%s 需要同一原 AnimBlueprint 所登记函数图中的实际 Entry 成员，拒绝 CDO 和游离对象。"),
			*GetPathNameSafe(Owner), *GetPathNameSafe(FunctionGraph), *GetPathNameSafe(EntryNode));
		return Result;
	}
	int32 EntryCount = 0;
	for (const UEdGraphNode* Candidate : FunctionGraph->Nodes)
	{
		if (Cast<UK2Node_FunctionEntry>(Candidate))
		{
			++EntryCount;
		}
	}
	if (EntryCount != 1)
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] FunctionGraph=%s Entry=%s 函数图必须恰有一个 FunctionEntry，实际 EntryCount=%d。"),
			*FunctionGraph->GetPathName(), *Entry->GetPathName(), EntryCount);
		return Result;
	}
	Result.bThreadSafe = Entry->MetaData.bThreadSafe;
	Result.ExtraFlags = Entry->GetExtraFlags();
	Result.FunctionFlags = Entry->GetFunctionFlags();
	Result.bSucceeded = true;
	return Result;
}

FGGYGOAnimationNodeAuthoringResult UGGYGOAnimationGraphEditorLibrary::ReadAnimationNodeAuthoring(
	UBlueprint* Owner, UObject* Node)
{
	check(IsInGameThread());
	FGGYGOAnimationNodeAuthoringResult Result;
	const UAnimBlueprint* AnimOwner = Cast<UAnimBlueprint>(Owner);
	const UAnimGraphNode_Base* AnimationNode = Cast<UAnimGraphNode_Base>(Node);
	// 直接读取 Outer，避免对错误身份的节点调用 GetGraph 触发引擎 ensure。
	UEdGraph* Graph = IsValid(AnimationNode) ? Cast<UEdGraph>(AnimationNode->GetOuter()) : nullptr;
	if (!IsValid(AnimOwner) || AnimOwner->IsTemplate() || !IsValid(AnimationNode)
		|| AnimationNode->IsTemplate() || !IsValid(Graph) || Graph->GetTypedOuter<UBlueprint>() != AnimOwner
		|| !Graph->Nodes.Contains(AnimationNode))
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Owner=%s Graph=%s Node=%s 需要同一原 AnimBlueprint 作者图中的实际动画节点成员，拒绝 CDO 和游离对象。"),
			*GetPathNameSafe(Owner), *GetPathNameSafe(Graph), *GetPathNameSafe(Node));
		return Result;
	}
	TArray<UEdGraph*> AuthoringGraphs;
	AnimOwner->GetAllGraphs(AuthoringGraphs);
	if (!AuthoringGraphs.Contains(Graph))
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Owner=%s Graph=%s Node=%s 作者图未登记在 Owner 的完整图集合中。"),
			*Owner->GetPathName(), *Graph->GetPathName(), *AnimationNode->GetPathName());
		return Result;
	}
	Result.AlwaysDynamicProperties = AnimationNode->AlwaysDynamicProperties.Array();
	Result.AlwaysDynamicProperties.Sort(FNameLexicalLess());
	Result.bSucceeded = true;
	return Result;
}

FName UGGYGOAnimationGraphEditorLibrary::GetCalledFunctionName(UObject* Node)
{
	check(IsInGameThread());
	const UK2Node_CallFunction* Call = Cast<UK2Node_CallFunction>(Node);
	const UFunction* Function = Call ? Call->GetTargetFunction() : nullptr;
	return Function ? Function->GetFName() : NAME_None;
}

TArray<FGGYGOFloatCurveKeySnapshot> UGGYGOAnimationGraphEditorLibrary::ReadRuntimeCurveKeys(const FRuntimeFloatCurve& Curve)
{
	check(IsInGameThread());
	TArray<FGGYGOFloatCurveKeySnapshot> Result;
	for (const FRichCurveKey& Key : Curve.GetRichCurveConst()->GetConstRefOfKeys())
	{
		FGGYGOFloatCurveKeySnapshot& Item = Result.AddDefaulted_GetRef();
		Item.Time = Key.Time;
		Item.Value = Key.Value;
		Item.ArriveTangent = Key.ArriveTangent;
		Item.LeaveTangent = Key.LeaveTangent;
		Item.ArriveTangentWeight = Key.ArriveTangentWeight;
		Item.LeaveTangentWeight = Key.LeaveTangentWeight;
		Item.InterpMode = static_cast<int32>(Key.InterpMode.GetValue());
		Item.TangentMode = static_cast<int32>(Key.TangentMode.GetValue());
		Item.TangentWeightMode = static_cast<int32>(Key.TangentWeightMode.GetValue());
	}
	return Result;
}

FGGYGOAnimationGraphEditResult UGGYGOAnimationGraphEditorLibrary::MarkAnimationNodePropertiesDynamic(UBlueprint* Owner, UObject* Node,
	const TArray<FName>& Properties)
{
	check(IsInGameThread());
	FGGYGOAnimationGraphEditResult Result;
	UAnimGraphNode_Base* AnimationNode = Cast<UAnimGraphNode_Base>(Node);
	if (!Cast<UAnimBlueprint>(Owner) || !AnimationNode || AnimationNode->GetTypedOuter<UBlueprint>() != Owner
		|| Properties.IsEmpty() || !GEditor || GEditor->PlayWorld)
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Owner=%s Node=%s 需要同一原 AnimBlueprint 的非 PIE 作者图和明确属性。"),
			*GetPathNameSafe(Owner), *GetPathNameSafe(Node));
		return Result;
	}
	const UScriptStruct* Type = AnimationNode->GetFNodeType();
	for (FName Name : Properties)
	{
		const FProperty* Property = Type ? Type->FindPropertyByName(Name) : nullptr;
		if (!Property || !Property->HasAnyPropertyFlags(CPF_Edit) || !Property->HasMetaData(TEXT("FoldProperty")))
		{
			Result.Error = FString::Printf(TEXT("[Animation.Graph] Node=%s Property=%s 不是原节点可编辑 FoldProperty。"),
				*AnimationNode->GetPathName(), *Name.ToString());
			return Result;
		}
	}
	bool bChanged = false;
	for (FName Name : Properties)
	{
		if (!AnimationNode->AlwaysDynamicProperties.Contains(Name))
		{
			if (!bChanged)
			{
				AnimationNode->Modify();
				bChanged = true;
			}
			AnimationNode->AlwaysDynamicProperties.Add(Name);
		}
	}
	if (bChanged)
	{
		FBlueprintEditorUtils::MarkBlueprintAsModified(Owner);
	}
	Result.bSucceeded = true;
	return Result;
}

FGGYGOAnimationStateTransitionsResult UGGYGOAnimationGraphEditorLibrary::ReadStateMachineTransitions(
	UBlueprint* Owner, UEdGraph* StateMachineGraph)
{
	check(IsInGameThread());
	FGGYGOAnimationStateTransitionsResult Result;
	const auto Fail = [&Result, StateMachineGraph](const UObject* Object, const TCHAR* Reason)
	{
		Result = FGGYGOAnimationStateTransitionsResult();
		Result.Error = FString::Printf(TEXT("[Animation.Graph] StateMachine=%s Object=%s %s"),
			*GetPathNameSafe(StateMachineGraph), *GetPathNameSafe(Object), Reason);
		return Result;
	};
	UAnimationStateMachineGraph* Machine = Cast<UAnimationStateMachineGraph>(StateMachineGraph);
	const UAnimGraphNode_StateMachineBase* OwnerNode = Machine ? Machine->OwnerAnimGraphNode.Get() : nullptr;
	if (!Cast<UAnimBlueprint>(Owner) || !Machine || !OwnerNode || Machine->GetOuter() != OwnerNode
		|| OwnerNode->EditorStateMachineGraph != Machine || OwnerNode->GetTypedOuter<UBlueprint>() != Owner)
	{
		return Fail(Owner, TEXT("需要原 AnimBlueprint 的状态机节点反向持有的作者状态机图。"));
	}
	TSet<const UEdGraphNode*> Members;
	for (const UEdGraphNode* Node : Machine->Nodes)
	{
		// UE 图节点以所属 UEdGraph 为 Outer（UEdGraphNode::GetGraph 即 Cast 其 Outer）；
		// 直接比较 Outer，避免对异常节点触发 GetGraph 的 ensure。
		if (!Node || Node->GetOuter() != Machine)
		{
			return Fail(Node ? static_cast<const UObject*>(Node) : Machine, TEXT("状态机节点为空或其 Outer 不是本状态机图。"));
		}
		Members.Add(Node);
	}
	// 端点只接受本机普通状态及其自有子图；Alias/Conduit 的展开语义不在本接口内推断。
	const auto ReadState = [&Members](const UEdGraphNode* Node, UEdGraph*& OutGraph)
	{
		const UAnimStateNode* State = Cast<UAnimStateNode>(Node);
		OutGraph = State ? State->BoundGraph.Get() : nullptr;
		return State && Members.Contains(State) && OutGraph && OutGraph->GetOuter() == State;
	};
	for (UEdGraphNode* Node : Machine->Nodes)
	{
		UAnimStateTransitionNode* Transition = Cast<UAnimStateTransitionNode>(Node);
		if (!Transition)
		{
			continue;
		}
		// 原生 GetPreviousState/GetNextState 直接取 Pins[0/1]->LinkedTo[0]；先确认两端各恰一条连接。
		const TArray<UEdGraphPin*>& Pins = Transition->Pins;
		if (Pins.Num() != 2 || !Pins[0] || !Pins[1] || Pins[0]->Direction != EGPD_Input
			|| Pins[1]->Direction != EGPD_Output || Pins[0]->LinkedTo.Num() != 1 || Pins[1]->LinkedTo.Num() != 1
			|| !Pins[0]->LinkedTo[0] || !Pins[1]->LinkedTo[0])
		{
			return Fail(Transition, TEXT("过渡必须恰有一个原生输入端点和一个输出端点。"));
		}
		UAnimStateNodeBase* Previous = Transition->GetPreviousState();
		UAnimStateNodeBase* Next = Transition->GetNextState();
		UEdGraph* PreviousGraph = nullptr;
		UEdGraph* NextGraph = nullptr;
		if (Previous != Pins[0]->LinkedTo[0]->GetOwningNode() || Next != Pins[1]->LinkedTo[0]->GetOwningNode()
			|| !ReadState(Previous, PreviousGraph) || !ReadState(Next, NextGraph))
		{
			return Fail(Transition, TEXT("过渡端点不是本状态机自有子图的普通状态；Alias/Conduit 端点不受支持。"));
		}
		UAnimationTransitionGraph* Rule = Cast<UAnimationTransitionGraph>(Transition->BoundGraph);
		if (!Rule || !Rule->GetResultNode() || Rule->GetTypedOuter<UBlueprint>() != Owner)
		{
			return Fail(Transition, TEXT("过渡缺少同一 Owner 中带原生结果节点的规则图。"));
		}
		FGGYGOAnimationStateTransitionInfo& Info = Result.Transitions.AddDefaulted_GetRef();
		Info.PreviousStateGraph = PreviousGraph;
		Info.NextStateGraph = NextGraph;
		Info.Transition = Transition;
		Info.RuleGraph = Rule;
		Info.bRuleGraphOwned = Rule->GetOuter() == Transition;
		Info.PreviousState = Previous;
		Info.NextState = Next;
		Info.bBidirectional = Transition->Bidirectional;
		Info.bSharedRules = Transition->bSharedRules;
		Info.bBoundGraphShared = Transition->IsBoundGraphShared();
		Info.bDisabled = Transition->bDisabled;
		Info.bAutomaticRule = Transition->bAutomaticRuleBasedOnSequencePlayerInState;
		Info.LogicType = static_cast<uint8>(Transition->LogicType.GetValue());
		Info.bHasCustomTransitionGraph = Transition->GetCustomTransitionGraph() != nullptr;
	}
	Result.StateMachineGraph = Machine;
	Result.bSucceeded = true;
	return Result;
}

FGGYGOBlueprintDuplicateResult UGGYGOAnimationGraphEditorLibrary::DuplicateAnimBlueprintToTemp(UBlueprint* Source,
	const FString& TempPackageName)
{
	check(IsInGameThread());
	FGGYGOBlueprintDuplicateResult Result;
	UAnimBlueprint* SourceAnim = Cast<UAnimBlueprint>(Source);
	if (!SourceAnim || !SourceAnim->GeneratedClass || !GEditor || GEditor->PlayWorld)
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Source=%s 需要已生成类的原 AnimBlueprint，且不在 PIE 中。"),
			*GetPathNameSafe(Source));
		return Result;
	}
	// /Temp 是只读挂载根，必须显式允许只读根才是合法包名；这也保证副本不进入可保存的内容根。
	FText Reason;
	const FString AssetName = FPackageName::GetLongPackageAssetName(TempPackageName);
	if (!TempPackageName.StartsWith(TEXT("/Temp/"), ESearchCase::CaseSensitive)
		|| !FPackageName::IsValidLongPackageName(TempPackageName, /*bIncludeReadOnlyRoots=*/true, &Reason)
		|| AssetName.IsEmpty() || !FName(*AssetName).IsValidObjectName(Reason))
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Destination=%s 不是合法 /Temp 资产包名：%s"),
			*TempPackageName, *Reason.ToString());
		return Result;
	}
	if (FindPackage(nullptr, *TempPackageName))
	{
		// 不覆盖、不复用已有包：旧副本可能仍被验证宿主持有或处于诊断现场。
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Destination=%s 已有已加载包，拒绝覆盖。"), *TempPackageName);
		return Result;
	}
	UPackage* SourcePackage = SourceAnim->GetPackage();
	const bool bSourceWasDirty = SourcePackage->IsDirty();
	UPackage* Package = CreatePackage(*TempPackageName);
	// 与 UE 资产复制同一原生入口；UBlueprint::PostDuplicate 为副本编译出属于新包的生成类。
	FObjectDuplicationParameters Parameters = InitStaticDuplicateObjectParams(SourceAnim, Package, FName(*AssetName), RF_AllFlags);
	UAnimBlueprint* Copy = Cast<UAnimBlueprint>(StaticDuplicateObjectEx(Parameters));
	Result.Blueprint = Copy;
	const UClass* CopyClass = Copy ? Copy->GeneratedClass.Get() : nullptr;
	if (!Copy || Copy == SourceAnim || Copy->GetOuter() != Package || !CopyClass || CopyClass == SourceAnim->GeneratedClass
		|| CopyClass->GetOutermost() != Package || Copy->ParentClass != SourceAnim->ParentClass
		|| Copy->TargetSkeleton != SourceAnim->TargetSkeleton)
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Source=%s Copy=%s Class=%s 副本未在目标包生成独立类或父类/骨架不一致。"),
			*SourceAnim->GetPathName(), *GetPathNameSafe(Copy), *GetPathNameSafe(CopyClass));
		return Result;
	}
	if (!bSourceWasDirty && SourcePackage->IsDirty())
	{
		Result.Error = FString::Printf(TEXT("[Animation.Graph] Source=%s 复制后源包变脏；未回滚、未清除 dirty。"),
			*SourcePackage->GetName());
		return Result;
	}
	Result.bSucceeded = true;
	return Result;
}
