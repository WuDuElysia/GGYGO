#include "GGYGOBossAbilityGraphLibrary.h"
#include "AI/Boss/Abilities/GGYGOBossAttackAbility.h"
#include "AI/Boss/Abilities/GGYGOBossDeathAbility.h"
#include "AI/Boss/GGYGOBossAIController.h"
#include "EdGraph/EdGraph.h"
#include "EdGraphSchema_K2.h"
#include "Engine/Blueprint.h"
#include "Engine/Engine.h"
#include "Engine/World.h"
#include "GameFramework/PlayerController.h"
#include "K2Node_CallFunction.h"
#include "K2Node_DynamicCast.h"
#include "K2Node_Event.h"
#include "K2Node_IfThenElse.h"
#include "K2Node_VariableGet.h"
#include "Kismet2/BlueprintEditorUtils.h"
#include UE_INLINE_GENERATED_CPP_BY_NAME(GGYGOBossAbilityGraphLibrary)

namespace
{

	UClass* ActionClass()
	{
		return UGGYGOBossAttackAbility::StaticClass();

	}
	UClass* DeathClass()
	{
		return UGGYGOBossDeathAbility::StaticClass();

	}
	UEdGraphPin* Pin(UEdGraphNode* N, FName P)
	{
		return N ? N->FindPin(P) : nullptr;

	}
	bool Linked(UEdGraphNode* A, FName Out, UEdGraphNode* B, FName In)

	{

		const auto* P = Pin(A, Out);
		const auto* Q = Pin(B, In);
		return P && Q && Q->LinkedTo.Num() == 1 && Q->LinkedTo[0] == P && P->LinkedTo.Contains(const_cast<UEdGraphPin*>(Q));

	}
	bool NoLink(UEdGraphNode* N, FName P)
	{
		const auto* V = Pin(N,P);
		return V && V->LinkedTo.IsEmpty();

	}
	bool Literal(UEdGraphNode* N, FName P, const TCHAR* Value)

	{
		const auto* V=Pin(N,P);
		return V && V->LinkedTo.IsEmpty() && V->DefaultValue==Value;

	}
	UK2Node_Event* Event(const UEdGraph* G, FName Name)

	{

		UK2Node_Event* Found=nullptr;
		if (!G) return nullptr;
		for (UEdGraphNode* N:G->Nodes) if (auto* E=Cast<UK2Node_Event>(N))
		if (E->EventReference.GetMemberName()==Name)
		{
			if (Found) return nullptr;
			Found=E;

		}
		return Found;

	}
	UK2Node_CallFunction* AsCall(UEdGraphNode* N, UClass* Owner, FName Name)

	{

		auto* C=Cast<UK2Node_CallFunction>(N);
		UFunction* Expected = Owner->FindFunctionByName(Name);
		return C && Expected && C->GetTargetFunction()==Expected ? C:nullptr;

	}
	UK2Node_CallFunction* After(UEdGraphNode* N, FName Out, FName Name, UClass* Owner=nullptr)

	{

		const auto* P=Pin(N,Out);
		auto* C=P && P->LinkedTo.Num()==1 ? AsCall(P->LinkedTo[0]->GetOwningNode(),Owner?Owner:ActionClass(),Name):nullptr;
		return C && Linked(N,Out,C,UEdGraphSchema_K2::PN_Execute) ? C:nullptr;

	}
	UK2Node_CallFunction* InputCall(UEdGraphNode* N,FName In,UClass* Owner,FName Name)

	{

		const auto* P=Pin(N,In);
		return P && P->LinkedTo.Num()==1 ? AsCall(P->LinkedTo[0]->GetOwningNode(),Owner,Name):nullptr;

	}
	bool VarInput(UEdGraphNode* N,FName In,FName Name)

	{

		const auto* P=Pin(N,In);
		auto* V=P && P->LinkedTo.Num()==1 ? Cast<UK2Node_VariableGet>(P->LinkedTo[0]->GetOwningNode()):nullptr;
		return V && V->VariableReference.GetMemberName()==Name && P->LinkedTo[0]==V->GetValuePin();

	}
	UK2Node_IfThenElse* GuardAfter(UEdGraphNode* N)

	{

		const auto* P=Pin(N,UEdGraphSchema_K2::PN_Then);
		auto* B=P && P->LinkedTo.Num()==1 ? Cast<UK2Node_IfThenElse>(P->LinkedTo[0]->GetOwningNode()):nullptr;
		return B && Linked(N,UEdGraphSchema_K2::PN_Then,B,UEdGraphSchema_K2::PN_Execute)
		&& Linked(N,UEdGraphSchema_K2::PN_ReturnValue,B,UEdGraphSchema_K2::PN_Condition)?B:nullptr;

	}
	UK2Node_DynamicCast* CastAfter(UEdGraphNode* N,FName Out,UClass* Type)

	{

		const auto* P=Pin(N,Out);
		auto* C=P && P->LinkedTo.Num()==1 ? Cast<UK2Node_DynamicCast>(P->LinkedTo[0]->GetOwningNode()):nullptr;
		return C && C->TargetType==Type && Linked(N,Out,C,UEdGraphSchema_K2::PN_Execute)?C:nullptr;

	}
	bool Failure(UK2Node_Event* E,UK2Node_CallFunction* Op,UK2Node_IfThenElse* B,UClass* Owner=nullptr)

	{

		auto* F=After(B,UEdGraphSchema_K2::PN_Else,Owner==DeathClass()?TEXT("FailBossDeath"):TEXT("FailBossAction"),Owner);
		return F && Linked(E,TEXT("Token"),F,TEXT("Token")) && Linked(Op,TEXT("OutError"),F,TEXT("Reason"));

	}
	bool Finish(UK2Node_Event* E,UClass* Owner=nullptr)

	{

		auto* F=After(E,UEdGraphSchema_K2::PN_Then,Owner==DeathClass()?TEXT("FinishBossDeath"):TEXT("FinishBossAction"),Owner);
		return F && Linked(E,TEXT("Token"),F,TEXT("Token")) && Literal(F,TEXT("bCancelled"),TEXT("false"));

	}
	UEdGraph* Existing(const UBlueprint* BP,UClass* Parent)

	{

		return BP && BP->ParentClass && BP->ParentClass->IsChildOf(Parent) && BP->UbergraphPages.Num()==1 ? BP->UbergraphPages[0]:nullptr;

	}
	UEdGraph* NewGraph(UBlueprint* BP,UClass* Parent,FString& Error)

	{

		if (!BP || !BP->ParentClass || !BP->ParentClass->IsChildOf(Parent) || BP->UbergraphPages.Num()>1)

		{
			Error=TEXT("需要原生机制的共享流程Blueprint。");
			return nullptr;

		}
		if (GEngine) for (const auto& C:GEngine->GetWorldContexts()) if(C.WorldType==EWorldType::PIE)

		{
			Error=TEXT("PIE期间禁止改共享流程图。");
			return nullptr;

		}
		UEdGraph* G=BP->UbergraphPages.IsEmpty()?nullptr:BP->UbergraphPages[0];
		if (G && G->Nodes.ContainsByPredicate([](const UEdGraphNode* Node)
			{ return !Node->IsAutomaticallyPlacedGhostNode(); }))
		{
			Error=TEXT("已有非匹配作者图，拒绝覆盖；保留现场。");
			return nullptr;

		}
		// Blueprint 工厂会放置禁用的 Activate／End 占位事件；保留这些原生占位节点。
		BP->Modify();
		if (!G)
		{
			G=FBlueprintEditorUtils::CreateNewGraph(BP,TEXT("EventGraph"),UEdGraph::StaticClass(),UEdGraphSchema_K2::StaticClass());
			FBlueprintEditorUtils::AddUbergraphPage(BP,G);

		}
		return G;

	}
	/** 仅用引擎K2作者API的局部工厂；不解释运行时任务或维护第二套流程状态。 */
	struct FAuthor

	{

		UEdGraph* G;
		FString& Error;
		UClass* Owner;
		template<typename T>T* Add(int32 X,int32 Y)

		{
			auto* N=NewObject<T>(G,NAME_None,RF_Transactional);
			G->AddNode(N,false,false);
			N->CreateNewGuid();
			N->NodePosX=X;
			N->NodePosY=Y;
			return N;

		}
		void Pins(UK2Node* N)
		{
			N->PostPlacedNewNode();
			N->AllocateDefaultPins();
		}
		void Link(UEdGraphNode* A,FName Out,UEdGraphNode* B,FName In)

		{

			auto* P=Pin(A,Out);
			auto* Q=Pin(B,In);
			if(!P || !Q || !G->GetSchema()->TryCreateConnection(P,Q)) if(Error.IsEmpty())Error=FString::Printf(TEXT("共享图连接失败：%s→%s。"),*Out.ToString(),*In.ToString());

		}
		UK2Node_CallFunction* Call(FName Name,int32 X,int32 Y,UClass* Class=nullptr)

		{

			UFunction* F=(Class?Class:Owner)->FindFunctionByName(Name);
			if(!F)
			{
				Error=TEXT("缺少真实公开函数：")+Name.ToString();
				return nullptr;
			}
			auto* N=Add<UK2Node_CallFunction>(X,Y);
			N->SetFromFunction(F);
			Pins(N);
			return N;

		}
		UK2Node_Event* Ev(FName Name,int32 Y)

		{
			auto* N=Add<UK2Node_Event>(0,Y);
			N->EventReference.SetExternalMember(Name,Owner);
			N->bOverrideFunction=true;
			Pins(N);
			return N;
		}
		UK2Node_VariableGet* Var(FName Name,int32 X,int32 Y)

		{
			auto* N=Add<UK2Node_VariableGet>(X,Y);
			N->VariableReference.SetSelfMember(Name);
			Pins(N);
			return N;
		}
		UK2Node_DynamicCast* CastNode(UClass* Type,int32 X,int32 Y)

		{
			auto* N=Add<UK2Node_DynamicCast>(X,Y);
			N->TargetType=Type;
			Pins(N);
			N->SetPurity(false);
			return N;
		}
		void Set(UEdGraphNode* N,FName Name,const FString& Value)

		{
			if(auto* P=Pin(N,Name))G->GetSchema()->TrySetDefaultValue(*P,Value);
			else Error=TEXT("缺少作者参数：")+Name.ToString();
		}
		UK2Node_CallFunction* FailNode(UK2Node_Event* E,int32 X,int32 Y,const FString& Reason=FString())

		{
			auto* F=Call(Owner==DeathClass()?TEXT("FailBossDeath"):TEXT("FailBossAction"),X,Y);
			Link(E,TEXT("Token"),F,TEXT("Token"));
			if(!Reason.IsEmpty())Set(F,TEXT("Reason"),Reason);
			return F;
		}
		UK2Node_IfThenElse* Guard(UK2Node_Event* E,UK2Node_CallFunction* Op,int32 X,int32 Y)

		{

			auto* B=Add<UK2Node_IfThenElse>(X,Y);
			Pins(B);
			Link(Op,UEdGraphSchema_K2::PN_Then,B,UEdGraphSchema_K2::PN_Execute);
			Link(Op,UEdGraphSchema_K2::PN_ReturnValue,B,UEdGraphSchema_K2::PN_Condition);
			auto* F=FailNode(E,X+300,Y+180);
			Link(B,UEdGraphSchema_K2::PN_Else,F,UEdGraphSchema_K2::PN_Execute);
			Link(Op,TEXT("OutError"),F,TEXT("Reason"));
			return B;

		}
		void End(UK2Node_Event* E,int32 Y)

		{
			auto* F=Call(Owner==DeathClass()?TEXT("FinishBossDeath"):TEXT("FinishBossAction"),300,Y);
			Set(F,TEXT("bCancelled"),TEXT("false"));
			Link(E,UEdGraphSchema_K2::PN_Then,F,UEdGraphSchema_K2::PN_Execute);
			Link(E,TEXT("Token"),F,TEXT("Token"));
		}

	};
}

static bool ValidateActionGraphImpl(const UBlueprint* BP,bool bFlightLanding,FString& Error)
{

	Error.Reset();
	const auto Bad=[&Error]()
	{
		Error=TEXT("共享GA实际图的策略、原Token连接或流程参数不匹配。");
		return false;
	};
	auto* G=Existing(BP,ActionClass());
	if(!G)return Bad();
	auto* P=Event(G,TEXT("PrepareBossAction"));
	auto* C=CastAfter(P,UEdGraphSchema_K2::PN_Then,AGGYGOBossAIController::StaticClass());
	auto* Controller=C?InputCall(C,C->GetCastSourcePin()->PinName,APawn::StaticClass(),TEXT("GetController")):nullptr;
	auto* Avatar=InputCall(Controller,UEdGraphSchema_K2::PN_Self,ActionClass(),TEXT("GetBossCharacter"));
	auto* Bind=C?After(C,C->GetValidCastPin()->PinName,TEXT("BindBossTarget")):nullptr;
	auto* Target=InputCall(Bind,TEXT("Target"),AGGYGOBossAIController::StaticClass(),TEXT("GetCombatTarget"));
	auto* BindGate=GuardAfter(Bind);
	auto* CastFail=C?After(C,C->GetInvalidCastPin()->PinName,TEXT("FailBossAction")):nullptr;
	if(!Avatar || !BindGate || !Target || !CastFail || !Linked(P,TEXT("Token"),Avatar,TEXT("Token"))
	|| !Linked(C,C->GetCastResultPin()->PinName,Target,UEdGraphSchema_K2::PN_Self) || !Linked(P,TEXT("Token"),Bind,TEXT("Token"))
	|| !Linked(P,TEXT("Token"),CastFail,TEXT("Token")) || !Failure(P,Bind,BindGate))return Bad();
	auto* H=Event(G,TEXT("BossHitWindow"));
	auto* Execute=After(H,UEdGraphSchema_K2::PN_Then,TEXT("ExecuteBossWindow"));
	auto* Gate=GuardAfter(Execute);
	auto* Basis=InputCall(Execute,TEXT("AreaBasis"),AActor::StaticClass(),TEXT("GetTransform"));
	auto* BasisAvatar=InputCall(Basis,UEdGraphSchema_K2::PN_Self,ActionClass(),TEXT("GetBossCharacter"));
	auto* Location=InputCall(Execute,TEXT("ProjectileAimPoint"),AActor::StaticClass(),TEXT("K2_GetActorLocation"));
	auto* Aim=InputCall(Location,UEdGraphSchema_K2::PN_Self,ActionClass(),TEXT("GetBoundBossTarget"));
	if(!Gate || !BasisAvatar || !Aim || !Linked(H,TEXT("Token"),Execute,TEXT("Token")) || !Linked(H,TEXT("Window"),Execute,TEXT("Window"))
	|| !Linked(H,TEXT("Token"),BasisAvatar,TEXT("Token")) || !Linked(H,TEXT("Token"),Aim,TEXT("Token")) || !Failure(H,Execute,Gate) || !NoLink(Gate,UEdGraphSchema_K2::PN_Then))return Bad();
	auto* Invalid=Event(G,TEXT("BossTargetInvalidated"));
	auto* InvalidEnd=After(Invalid,UEdGraphSchema_K2::PN_Then,TEXT("FailBossAction"));
	auto* Changed=Event(G,TEXT("BossTargetControlChanged"));
	auto* Player=CastAfter(Changed,UEdGraphSchema_K2::PN_Then,APlayerController::StaticClass());
	auto* Lost=Player?After(Player,Player->GetInvalidCastPin()->PinName,TEXT("FailBossAction")):nullptr;
	if(!InvalidEnd || !Player || !Lost || !Linked(Invalid,TEXT("Token"),InvalidEnd,TEXT("Token")) || !Linked(Invalid,TEXT("Reason"),InvalidEnd,TEXT("Reason"))
	|| !Linked(Changed,TEXT("NewController"),Player,Player->GetCastSourcePin()->PinName) || !Linked(Changed,TEXT("Token"),Lost,TEXT("Token")) || !NoLink(Player,Player->GetValidCastPin()->PinName))return Bad();
	auto* Completed=Event(G,TEXT("MontageActionFinished"));
	if(!bFlightLanding)return NoLink(BindGate,UEdGraphSchema_K2::PN_Then) && Finish(Completed)?true:Bad();
	auto* Acquire=After(BindGate,UEdGraphSchema_K2::PN_Then,TEXT("AcquireBossFlight"));
	auto* AG=GuardAfter(Acquire);
	auto* Release=After(Completed,UEdGraphSchema_K2::PN_Then,TEXT("ReleaseBossFlight"));
	auto* RG=GuardAfter(Release);
	auto* Wait=After(RG,UEdGraphSchema_K2::PN_Then,TEXT("WaitBossLanding"));
	auto* WG=GuardAfter(Wait);
	auto* Landed=Event(G,TEXT("BossLanded"));
	auto* Recovery=After(Landed,UEdGraphSchema_K2::PN_Then,TEXT("PlayBossRecoveryPresentation"));
	auto* PG=GuardAfter(Recovery);
	if(!AG || !RG || !WG || !PG || !Linked(P,TEXT("Token"),Acquire,TEXT("Token")) || !Failure(P,Acquire,AG)
	|| !NoLink(AG,UEdGraphSchema_K2::PN_Then) || !Linked(Completed,TEXT("Token"),Release,TEXT("Token")) || !Literal(Release,TEXT("bEnterFalling"),TEXT("true"))
	|| !Failure(Completed,Release,RG) || !Linked(Completed,TEXT("Token"),Wait,TEXT("Token")) || !VarInput(Wait,TEXT("TimeoutSeconds"),TEXT("LandingTimeoutSeconds"))
	|| !Failure(Completed,Wait,WG) || !NoLink(WG,UEdGraphSchema_K2::PN_Then) || !Linked(Landed,TEXT("Token"),Recovery,TEXT("Token"))
	|| !VarInput(Recovery,TEXT("Montage"),TEXT("LandingRecoveryMontage")) || !VarInput(Recovery,TEXT("PlayRate"),TEXT("RecoveryPlayRate"))
	|| !VarInput(Recovery,TEXT("FX"),TEXT("RecoveryFX")) || !Failure(Landed,Recovery,PG) || !NoLink(PG,UEdGraphSchema_K2::PN_Then)
	|| !Finish(Event(G,TEXT("RecoveryMontageFinished"))))return Bad();
	return true;
}

static bool BuildActionGraphImpl(UBlueprint* BP,bool bFlightLanding,FString& Error)
{

	if(ValidateActionGraphImpl(BP,bFlightLanding,Error))return true;
	Error.Reset();
	auto* G=NewGraph(BP,ActionClass(),Error);
	if(!G)return false;
	FAuthor A
	{
		G,Error,ActionClass()
	};
	auto* P=A.Ev(TEXT("PrepareBossAction"),0);
	auto* Avatar=A.Call(TEXT("GetBossCharacter"),100,-350);
	A.Link(P,TEXT("Token"),Avatar,TEXT("Token"));
	auto* Controller=A.Call(TEXT("GetController"),360,-350,APawn::StaticClass());
	A.Link(Avatar,UEdGraphSchema_K2::PN_ReturnValue,Controller,UEdGraphSchema_K2::PN_Self);
	auto* Cast=A.CastNode(AGGYGOBossAIController::StaticClass(),300,0);
	A.Link(P,UEdGraphSchema_K2::PN_Then,Cast,UEdGraphSchema_K2::PN_Execute);
	A.Link(Controller,UEdGraphSchema_K2::PN_ReturnValue,Cast,Cast->GetCastSourcePin()->PinName);
	auto* Target=A.Call(TEXT("GetCombatTarget"),580,-350,AGGYGOBossAIController::StaticClass());
	A.Link(Cast,Cast->GetCastResultPin()->PinName,Target,UEdGraphSchema_K2::PN_Self);
	auto* Bind=A.Call(TEXT("BindBossTarget"),600,0);
	A.Link(Cast,Cast->GetValidCastPin()->PinName,Bind,UEdGraphSchema_K2::PN_Execute);
	A.Link(P,TEXT("Token"),Bind,TEXT("Token"));
	A.Link(Target,UEdGraphSchema_K2::PN_ReturnValue,Bind,TEXT("Target"));
	auto* Failed=A.FailNode(P,600,300,TEXT("共享策略需要BossController明确提供目标。"));
	A.Link(Cast,Cast->GetInvalidCastPin()->PinName,Failed,UEdGraphSchema_K2::PN_Execute);
	auto* BG=A.Guard(P,Bind,900,0);
	auto* H=A.Ev(TEXT("BossHitWindow"),900);
	auto* Self=A.Call(TEXT("GetBossCharacter"),100,550);
	A.Link(H,TEXT("Token"),Self,TEXT("Token"));
	auto* Basis=A.Call(TEXT("GetTransform"),380,550,AActor::StaticClass());
	A.Link(Self,UEdGraphSchema_K2::PN_ReturnValue,Basis,UEdGraphSchema_K2::PN_Self);
	auto* Aim=A.Call(TEXT("GetBoundBossTarget"),100,700);
	A.Link(H,TEXT("Token"),Aim,TEXT("Token"));
	auto* Point=A.Call(TEXT("K2_GetActorLocation"),380,700,AActor::StaticClass());
	A.Link(Aim,UEdGraphSchema_K2::PN_ReturnValue,Point,UEdGraphSchema_K2::PN_Self);
	auto* Execute=A.Call(TEXT("ExecuteBossWindow"),620,900);
	A.Link(H,UEdGraphSchema_K2::PN_Then,Execute,UEdGraphSchema_K2::PN_Execute);
	A.Link(H,TEXT("Token"),Execute,TEXT("Token"));
	A.Link(H,TEXT("Window"),Execute,TEXT("Window"));
	A.Link(Basis,UEdGraphSchema_K2::PN_ReturnValue,Execute,TEXT("AreaBasis"));
	A.Link(Point,UEdGraphSchema_K2::PN_ReturnValue,Execute,TEXT("ProjectileAimPoint"));
	A.Guard(H,Execute,1000,900);
	auto* I=A.Ev(TEXT("BossTargetInvalidated"),1600);
	auto* IF=A.FailNode(I,300,1600);
	A.Link(I,UEdGraphSchema_K2::PN_Then,IF,UEdGraphSchema_K2::PN_Execute);
	A.Link(I,TEXT("Reason"),IF,TEXT("Reason"));
	auto* C=A.Ev(TEXT("BossTargetControlChanged"),2000);
	auto* Player=A.CastNode(APlayerController::StaticClass(),300,2000);
	A.Link(C,UEdGraphSchema_K2::PN_Then,Player,UEdGraphSchema_K2::PN_Execute);
	A.Link(C,TEXT("NewController"),Player,Player->GetCastSourcePin()->PinName);
	auto* Lost=A.FailNode(C,600,2200,TEXT("原目标失去玩家控制。"));
	A.Link(Player,Player->GetInvalidCastPin()->PinName,Lost,UEdGraphSchema_K2::PN_Execute);
	auto* Done=A.Ev(TEXT("MontageActionFinished"),2700);
	if(!bFlightLanding)A.End(Done,2700);
	else

	{

		auto* Acquire=A.Call(TEXT("AcquireBossFlight"),1200,0);
		A.Link(BG,UEdGraphSchema_K2::PN_Then,Acquire,UEdGraphSchema_K2::PN_Execute);
		A.Link(P,TEXT("Token"),Acquire,TEXT("Token"));
		A.Guard(P,Acquire,1500,0);
		auto* Release=A.Call(TEXT("ReleaseBossFlight"),300,2700);
		A.Set(Release,TEXT("bEnterFalling"),TEXT("true"));
		A.Link(Done,UEdGraphSchema_K2::PN_Then,Release,UEdGraphSchema_K2::PN_Execute);
		A.Link(Done,TEXT("Token"),Release,TEXT("Token"));
		auto* RG=A.Guard(Done,Release,600,2700);
		auto* Wait=A.Call(TEXT("WaitBossLanding"),950,2700);
		A.Link(RG,UEdGraphSchema_K2::PN_Then,Wait,UEdGraphSchema_K2::PN_Execute);
		A.Link(Done,TEXT("Token"),Wait,TEXT("Token"));
		auto* Time=A.Var(TEXT("LandingTimeoutSeconds"),900,2500);
		A.Link(Time,TEXT("LandingTimeoutSeconds"),Wait,TEXT("TimeoutSeconds"));
		A.Guard(Done,Wait,1300,2700);
		auto* L=A.Ev(TEXT("BossLanded"),3400);
		auto* Recovery=A.Call(TEXT("PlayBossRecoveryPresentation"),300,3400);
		A.Link(L,UEdGraphSchema_K2::PN_Then,Recovery,UEdGraphSchema_K2::PN_Execute);
		A.Link(L,TEXT("Token"),Recovery,TEXT("Token"));
		for(const auto& Pair:TArray<TPair<FName,FName>>
		{
			{
				TEXT("LandingRecoveryMontage"),TEXT("Montage")
			},
			{
				TEXT("RecoveryPlayRate"),TEXT("PlayRate")
			},
			{
				TEXT("RecoveryFX"),TEXT("FX")
			}
		})

		{
			auto* V=A.Var(Pair.Key,0,3650);
			A.Link(V,Pair.Key,Recovery,Pair.Value);
		}
		A.Guard(L,Recovery,650,3400);
		A.End(A.Ev(TEXT("RecoveryMontageFinished"),4000),4000);

	}
	if(!Error.IsEmpty())return false;
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
	return ValidateActionGraphImpl(BP,bFlightLanding,Error);
}

static bool ValidateDeathGraphImpl(const UBlueprint* BP,FString& Error)
{

	Error.Reset();
	auto* G=Existing(BP,DeathClass());
	auto* P=Event(G,TEXT("PrepareBossDeath"));
	auto* Cancel=After(P,UEdGraphSchema_K2::PN_Then,TEXT("CancelOtherBossActions"),DeathClass());
	auto* CG=GuardAfter(Cancel);
	auto* Start=After(CG,UEdGraphSchema_K2::PN_Then,TEXT("StartBossDeathState"),DeathClass());
	auto* SG=GuardAfter(Start);
	auto* Wait=After(SG,UEdGraphSchema_K2::PN_Then,TEXT("WaitBossDeathPresentation"),DeathClass());
	auto* WG=GuardAfter(Wait);
	if(!G || !CG || !SG || !WG || !Linked(P,TEXT("Token"),Cancel,TEXT("Token")) || !Linked(P,TEXT("Token"),Start,TEXT("Token"))
	|| !Linked(P,TEXT("Token"),Wait,TEXT("Token")) || !VarInput(Wait,TEXT("Seconds"),TEXT("PresentationSeconds"))
	|| !Failure(P,Cancel,CG,DeathClass()) || !Failure(P,Start,SG,DeathClass()) || !Failure(P,Wait,WG,DeathClass())
	|| !NoLink(WG,UEdGraphSchema_K2::PN_Then) || !Finish(Event(G,TEXT("BossDeathPresentationFinished")),DeathClass()))

	{
		Error=TEXT("死亡共享图的正常顺序、等待参数或原Token/失败连接不匹配。");
		return false;
	}
	return true;
}

static bool BuildDeathGraphImpl(UBlueprint* BP,FString& Error)
{

	if(ValidateDeathGraphImpl(BP,Error))return true;
	Error.Reset();
	auto* G=NewGraph(BP,DeathClass(),Error);
	if(!G)return false;
	FAuthor A
	{
		G,Error,DeathClass()
	};
	auto* P=A.Ev(TEXT("PrepareBossDeath"),0);
	auto* Cancel=A.Call(TEXT("CancelOtherBossActions"),300,0);
	A.Link(P,UEdGraphSchema_K2::PN_Then,Cancel,UEdGraphSchema_K2::PN_Execute);
	A.Link(P,TEXT("Token"),Cancel,TEXT("Token"));
	auto* CG=A.Guard(P,Cancel,600,0);
	auto* Start=A.Call(TEXT("StartBossDeathState"),900,0);
	A.Link(CG,UEdGraphSchema_K2::PN_Then,Start,UEdGraphSchema_K2::PN_Execute);
	A.Link(P,TEXT("Token"),Start,TEXT("Token"));
	auto* SG=A.Guard(P,Start,1200,0);
	auto* Wait=A.Call(TEXT("WaitBossDeathPresentation"),1500,0);
	A.Link(SG,UEdGraphSchema_K2::PN_Then,Wait,UEdGraphSchema_K2::PN_Execute);
	A.Link(P,TEXT("Token"),Wait,TEXT("Token"));
	auto* Duration=A.Var(TEXT("PresentationSeconds"),1400,-240);
	A.Link(Duration,TEXT("PresentationSeconds"),Wait,TEXT("Seconds"));
	A.Guard(P,Wait,1800,0);
	A.End(A.Ev(TEXT("BossDeathPresentationFinished"),700),700);
	if(!Error.IsEmpty())return false;
	FBlueprintEditorUtils::MarkBlueprintAsStructurallyModified(BP);
	return ValidateDeathGraphImpl(BP,Error);
}

FGGYGOBossGraphResult UGGYGOBossAbilityGraphLibrary::BuildActionGraph(UBlueprint* BP, bool bFlightLanding)
{
	FString Error;
	const bool bSuccess = BuildActionGraphImpl(BP, bFlightLanding, Error);
	return {bSuccess, MoveTemp(Error)};
}

FGGYGOBossGraphResult UGGYGOBossAbilityGraphLibrary::ValidateActionGraph(const UBlueprint* BP, bool bFlightLanding)
{
	FString Error;
	const bool bSuccess = ValidateActionGraphImpl(BP, bFlightLanding, Error);
	return {bSuccess, MoveTemp(Error)};
}

FGGYGOBossGraphResult UGGYGOBossAbilityGraphLibrary::BuildDeathGraph(UBlueprint* BP)
{
	FString Error;
	const bool bSuccess = BuildDeathGraphImpl(BP, Error);
	return {bSuccess, MoveTemp(Error)};
}

FGGYGOBossGraphResult UGGYGOBossAbilityGraphLibrary::ValidateDeathGraph(const UBlueprint* BP)
{
	FString Error;
	const bool bSuccess = ValidateDeathGraphImpl(BP, Error);
	return {bSuccess, MoveTemp(Error)};
}
