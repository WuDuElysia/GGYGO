/** Kevin 资产制作：Health 只读驱动非循环死亡姿态，不执行死亡业务或启动第二个 Montage。 */
#include "KevinBossAnimBlueprintAuthor.h"
#include "Animation/AnimBlueprint.h"
#include "Animation/AnimInstance.h"
#include "AnimGraphNode_BlendListByBool.h"
#include "AnimGraphNode_Root.h"
#include "AnimGraphNode_SequencePlayer.h"
#include "AnimGraphNode_Slot.h"
#include "Character/Components/GGYGOHealthComponent.h"
#include "EdGraph/EdGraph.h"
#include "EdGraphSchema_K2.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/NavMovementComponent.h"
#include "K2Node_CallFunction.h"
#include "K2Node_Event.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_VariableGet.h"
#include "K2Node_VariableSet.h"
#include "Kismet/KismetMathLibrary.h"
#include "Kismet/KismetSystemLibrary.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include "UObject/UnrealType.h"

namespace KevinBossAnimation
{
namespace
{
	const FName DeathVariable(TEXT("bKevinDeathFromHealth"));
	const FName AirVariable(TEXT("bKevinAirFromMovement"));
	template<typename T, typename F> T* AddConfigured(UEdGraph* Graph, F&& Configure)
	{
		T* Node = NewObject<T>(Graph, NAME_None, RF_Transactional);
		Configure(Node);
		Graph->AddNode(Node, false, false);
		Node->CreateNewGuid(); Node->PostPlacedNewNode(); Node->AllocateDefaultPins();
		return Node;
	}
	template<typename T> T* Add(UEdGraph* Graph)
	{
		return AddConfigured<T>(Graph, [](T*) {});
	}
	UEdGraphPin* Pose(UEdGraphNode* Node, EEdGraphPinDirection Direction)
	{
		for (UEdGraphPin* Pin : Node->Pins)
			if (Pin->Direction == Direction && Pin->PinType.PinCategory == TEXT("struct")) return Pin;
		return nullptr;
	}
	bool Link(UEdGraph* Graph, UEdGraphPin* A, UEdGraphPin* B)
	{
		return A && B && Graph->GetSchema()->TryCreateConnection(A, B);
	}
}

bool HasHealthDeathChain(UAnimBlueprint* BP, UAnimSequence* Death, FName Slot)
{
	for (UEdGraph* Graph : BP->FunctionGraphs)
	{
		if (Graph->GetFName() != TEXT("AnimGraph")) continue;
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			auto* Root = Cast<UAnimGraphNode_Root>(Node);
			if (!Root) continue;
			const UEdGraphPin* Input = Pose(Root, EGPD_Input);
			if (!Input || Input->LinkedTo.Num() != 1) return false;
			auto* Blend = Cast<UAnimGraphNode_BlendListByBool>(Input->LinkedTo[0]->GetOwningNode());
			if (!Blend) return false;
			const UEdGraphPin* DeadPin = Blend->FindPin(TEXT("BlendPose_0"));
			const UEdGraphPin* AlivePin = Blend->FindPin(TEXT("BlendPose_1"));
			const UEdGraphPin* Active = Blend->FindPin(TEXT("bActiveValue"));
			if (!DeadPin || DeadPin->LinkedTo.Num() != 1 || !AlivePin || AlivePin->LinkedTo.Num() != 1
				|| !Active || Active->LinkedTo.Num() != 1) return false;
			const auto* Player = Cast<UAnimGraphNode_SequencePlayer>(DeadPin->LinkedTo[0]->GetOwningNode());
			const auto* SlotNode = Cast<UAnimGraphNode_Slot>(AlivePin->LinkedTo[0]->GetOwningNode());
			const auto* Value = Cast<UK2Node_VariableGet>(Active->LinkedTo[0]->GetOwningNode());
			return Player && Player->Node.GetSequence() == Death && !Player->Node.IsLooping()
				&& SlotNode && SlotNode->Node.SlotName == Slot
				&& Value && Value->VariableReference.GetMemberName() == DeathVariable;
		}
	}
	return false;
}

bool CanAddHealthDeath(UAnimBlueprint* BP, FString& Error)
{
	UEdGraph* Events = BP->UbergraphPages.IsEmpty() ? nullptr : BP->UbergraphPages[0];
	if (!Events || !Events->GetSchema()) { Error = TEXT("missing EventGraph"); return false; }
	for (const FBPVariableDescription& Variable : BP->NewVariables)
		if (Variable.VarName == DeathVariable || Variable.VarName == AirVariable)
		{ Error = TEXT("existing presentation variable is preserved"); return false; }
	UK2Node_Event* Update = nullptr;
	for (UEdGraphNode* Node : Events->Nodes)
		if (auto* Event = Cast<UK2Node_Event>(Node))
			if (Event->EventReference.GetMemberName() == TEXT("BlueprintUpdateAnimation"))
			{
				if (Update || !Event->FindPin(UEdGraphSchema_K2::PN_Then)
					|| !Event->FindPin(UEdGraphSchema_K2::PN_Then)->LinkedTo.IsEmpty())
				{ Error = TEXT("authored UpdateAnimation is preserved"); return false; }
				Update = Event;
			}
	return true;
}

bool AddHealthDeath(UAnimBlueprint* BP, UEdGraph* Graph, UAnimSequence* Death, UAnimSequence* Air,
	UAnimGraphNode_Root* Root, FString& Error)
{
	UEdGraph* Events = BP->UbergraphPages[0];
	UFunction* OwnerFunction = UAnimInstance::StaticClass()->FindFunctionByName(TEXT("GetOwningActor"));
	UFunction* HealthFunction = UGGYGOHealthComponent::StaticClass()->FindFunctionByName(TEXT("FindHealthComponent"));
	UFunction* ValidFunction = UKismetSystemLibrary::StaticClass()->FindFunctionByName(TEXT("IsValid"));
	UFunction* StateFunction = UGGYGOHealthComponent::StaticClass()->FindFunctionByName(TEXT("GetDeathState"));
	UFunction* CompareFunction = UKismetMathLibrary::StaticClass()->FindFunctionByName(TEXT("NotEqual_ByteByte"));
	UFunction* PawnFunction = UAnimInstance::StaticClass()->FindFunctionByName(TEXT("TryGetPawnOwner"));
	UFunction* MovementFunction = APawn::StaticClass()->FindFunctionByName(TEXT("GetMovementComponent"));
	UFunction* FallingFunction = UNavMovementComponent::StaticClass()->FindFunctionByName(TEXT("IsFalling"));
	UFunction* FlyingFunction = UNavMovementComponent::StaticClass()->FindFunctionByName(TEXT("IsFlying"));
	UFunction* OrFunction = UKismetMathLibrary::StaticClass()->FindFunctionByName(TEXT("BooleanOR"));
	if (!OwnerFunction || !HealthFunction || !ValidFunction || !StateFunction || !CompareFunction
		|| !PawnFunction || !MovementFunction || !FallingFunction || !FlyingFunction || !OrFunction)
	{ Error = TEXT("required reflected Health/owner functions are unavailable"); return false; }
	UK2Node_Event* Update = nullptr;
	for (UEdGraphNode* Node : Events->Nodes)
		if (auto* Event = Cast<UK2Node_Event>(Node))
			if (Event->EventReference.GetMemberName() == TEXT("BlueprintUpdateAnimation"))
			{
				if (Update || !Event->FindPin(UEdGraphSchema_K2::PN_Then)
					|| !Event->FindPin(UEdGraphSchema_K2::PN_Then)->LinkedTo.IsEmpty())
				{ Error = TEXT("authored UpdateAnimation is preserved"); return false; }
				Update = Event;
			}
	FEdGraphPinType Boolean;
	Boolean.PinCategory = UEdGraphSchema_K2::PC_Boolean;
	if (!FBlueprintEditorUtils::AddMemberVariable(BP, DeathVariable, Boolean, TEXT("false"))
		|| !FBlueprintEditorUtils::AddMemberVariable(BP, AirVariable, Boolean, TEXT("false")))
	{ Error = TEXT("death presentation variable already exists"); return false; }
	if (!Update)
	{
		Update = AddConfigured<UK2Node_Event>(Events, [](UK2Node_Event* Node)
		{
			Node->EventReference.SetExternalMember(TEXT("BlueprintUpdateAnimation"), UAnimInstance::StaticClass());
			Node->bOverrideFunction = true;
		});
	}
	const auto Call = [Events](UFunction* Function)
	{
		return AddConfigured<UK2Node_CallFunction>(Events,
			[Function](UK2Node_CallFunction* Node) { Node->SetFromFunction(Function); });
	};
	auto* Owner = Call(OwnerFunction);
	auto* Health = Call(HealthFunction);
	auto* Valid = Call(ValidFunction);
	auto* State = Call(StateFunction);
	auto* Compare = Call(CompareFunction);
	auto* Branch = Add<UK2Node_IfThenElse>(Events);
	auto* Set = AddConfigured<UK2Node_VariableSet>(Events,
		[](UK2Node_VariableSet* Node) { Node->VariableReference.SetSelfMember(DeathVariable); });
	Update->NodePosX = -800; Update->NodePosY = 0;
	Owner->NodePosX = -1200; Owner->NodePosY = 350;
	Health->NodePosX = -950; Health->NodePosY = 350;
	Valid->NodePosX = -650; Valid->NodePosY = 150;
	State->NodePosX = -650; State->NodePosY = 350;
	Compare->NodePosX = -350; Compare->NodePosY = 350;
	Branch->NodePosX = -350; Branch->NodePosY = 0;
	Set->NodePosX = 0; Set->NodePosY = 0;
	// Persona 无 Health 时保持初始预览；生产 Pawn 的 Health 是装配入口必需依赖。
	if (!Link(Events, Update->FindPin(UEdGraphSchema_K2::PN_Then), Branch->FindPin(UEdGraphSchema_K2::PN_Execute))
		|| !Link(Events, Owner->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Health->FindPin(TEXT("Actor")))
		|| !Link(Events, Health->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Valid->FindPin(TEXT("Object")))
		|| !Link(Events, Valid->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Branch->FindPin(UEdGraphSchema_K2::PN_Condition))
		|| !Link(Events, Branch->FindPin(UEdGraphSchema_K2::PN_Then), Set->FindPin(UEdGraphSchema_K2::PN_Execute))
		|| !Link(Events, Health->FindPin(UEdGraphSchema_K2::PN_ReturnValue), State->FindPin(UEdGraphSchema_K2::PN_Self))
		|| !Link(Events, State->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Compare->FindPin(TEXT("A")))
		|| !Link(Events, Compare->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Set->FindPin(DeathVariable)))
	{ Error = TEXT("Health death event links failed; inspect unsaved graph"); return false; }
	Compare->FindPin(TEXT("B"))->DefaultValue = TEXT("0");
	// 只读取 CMC 模式事实；起飞、重力接管与真实 Landed 的业务编排属于 GA BP。
	auto* Pawn = Call(PawnFunction);
	auto* Movement = Call(MovementFunction);
	auto* Falling = Call(FallingFunction);
	auto* Flying = Call(FlyingFunction);
	auto* Or = Call(OrFunction);
	auto* SetAir = AddConfigured<UK2Node_VariableSet>(Events,
		[](UK2Node_VariableSet* Node) { Node->VariableReference.SetSelfMember(AirVariable); });
	Pawn->NodePosX = -1200; Pawn->NodePosY = 650;
	Movement->NodePosX = -950; Movement->NodePosY = 650;
	Falling->NodePosX = -650; Falling->NodePosY = 600;
	Flying->NodePosX = -650; Flying->NodePosY = 800;
	Or->NodePosX = -350; Or->NodePosY = 650;
	SetAir->NodePosX = 300; SetAir->NodePosY = 0;
	if (!Link(Events, Pawn->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Movement->FindPin(UEdGraphSchema_K2::PN_Self))
		|| !Link(Events, Movement->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Falling->FindPin(UEdGraphSchema_K2::PN_Self))
		|| !Link(Events, Movement->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Flying->FindPin(UEdGraphSchema_K2::PN_Self))
		|| !Link(Events, Falling->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Or->FindPin(TEXT("A")))
		|| !Link(Events, Flying->FindPin(UEdGraphSchema_K2::PN_ReturnValue), Or->FindPin(TEXT("B")))
		|| !Link(Events, Or->FindPin(UEdGraphSchema_K2::PN_ReturnValue), SetAir->FindPin(AirVariable))
		|| !Link(Events, Set->FindPin(UEdGraphSchema_K2::PN_Then), SetAir->FindPin(UEdGraphSchema_K2::PN_Execute)))
	{ Error = TEXT("movement presentation links failed"); return false; }
	UEdGraphPin* RootInput = Pose(Root, EGPD_Input);
	if (!RootInput || RootInput->LinkedTo.Num() != 1) { Error = TEXT("missing original alive pose"); return false; }
	UEdGraphPin* Alive = RootInput->LinkedTo[0];
	auto* SlotNode = Cast<UAnimGraphNode_Slot>(Alive->GetOwningNode());
	UEdGraphPin* SlotInput = SlotNode ? Pose(SlotNode, EGPD_Input) : nullptr;
	if (!SlotInput || SlotInput->LinkedTo.Num() != 1) { Error = TEXT("missing ordinary Slot base pose"); return false; }
	UEdGraphPin* Idle = SlotInput->LinkedTo[0];
	auto* AirBlend = Add<UAnimGraphNode_BlendListByBool>(Graph);
	auto* AirPlayer = Add<UAnimGraphNode_SequencePlayer>(Graph);
	auto* AirValue = AddConfigured<UK2Node_VariableGet>(Graph,
		[](UK2Node_VariableGet* Node) { Node->VariableReference.SetSelfMember(AirVariable); });
	AirPlayer->Node.SetSequence(Air); AirPlayer->Node.SetLoopAnimation(true);
	Idle->GetOwningNode()->NodePosX = -850;
	AirBlend->NodePosX = -500; AirBlend->NodePosY = 0;
	AirPlayer->NodePosX = -850; AirPlayer->NodePosY = -250;
	AirValue->NodePosX = -850; AirValue->NodePosY = 250;
	Graph->GetSchema()->BreakPinLinks(*SlotInput, true);
	if (!Link(Graph, Pose(AirPlayer, EGPD_Output), AirBlend->FindPin(TEXT("BlendPose_0")))
		|| !Link(Graph, Idle, AirBlend->FindPin(TEXT("BlendPose_1")))
		|| !Link(Graph, AirValue->FindPin(AirVariable), AirBlend->FindPin(TEXT("bActiveValue")))
		|| !Link(Graph, Pose(AirBlend, EGPD_Output), SlotInput))
	{ Error = TEXT("airborne base pose links failed"); return false; }
	auto* Blend = Add<UAnimGraphNode_BlendListByBool>(Graph);
	Blend->NodePosX = 100; Root->NodePosX = 400;
	auto* ChildMode = FindFProperty<FEnumProperty>(FAnimNode_BlendListBase::StaticStruct(), TEXT("ChildUpateMode"));
	if (!ChildMode) { Error = TEXT("editable child update mode is unavailable"); return false; }
	ChildMode->GetUnderlyingProperty()->SetIntPropertyValue(ChildMode->ContainerPtrToValuePtr<void>(&Blend->Node),
		static_cast<uint64>(EBlendListChildUpdateMode::ResetChildOnActivate));
	auto* DeathPlayer = Add<UAnimGraphNode_SequencePlayer>(Graph);
	DeathPlayer->NodePosX = -300; DeathPlayer->NodePosY = -250;
	DeathPlayer->Node.SetSequence(Death); DeathPlayer->Node.SetLoopAnimation(false);
	auto* Value = AddConfigured<UK2Node_VariableGet>(Graph,
		[](UK2Node_VariableGet* Node) { Node->VariableReference.SetSelfMember(DeathVariable); });
	Value->NodePosX = -300; Value->NodePosY = 250;
	Graph->GetSchema()->BreakPinLinks(*RootInput, true);
	if (!Link(Graph, Alive, Blend->FindPin(TEXT("BlendPose_1")))
		|| !Link(Graph, Pose(DeathPlayer, EGPD_Output), Blend->FindPin(TEXT("BlendPose_0")))
		|| !Link(Graph, Value->FindPin(DeathVariable), Blend->FindPin(TEXT("bActiveValue")))
		|| !Link(Graph, Pose(Blend, EGPD_Output), RootInput))
	{ Error = TEXT("death pose links failed; inspect unsaved graph"); return false; }
	return true;
}
}
