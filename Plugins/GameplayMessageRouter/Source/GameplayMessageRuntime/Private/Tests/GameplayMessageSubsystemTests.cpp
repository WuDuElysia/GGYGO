/** @file GameplayMessageSubsystemTests.cpp @brief 验证父通道失效监听的清理及子通道订阅隔离。 */

#include "GameFramework/GameplayMessageSubsystem.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "GameFramework/AsyncAction_ListenForGameplayMessage.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/World.h"
#include "Misc/AutomationTest.h"
#include "NativeGameplayTags.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"

namespace GameplayMessageSubsystemTests
{
	UE_DEFINE_GAMEPLAY_TAG_STATIC(ParentChannel, "GameplayMessageRouter.Test.ExpiredType");
	UE_DEFINE_GAMEPLAY_TAG_STATIC(ChildChannel, "GameplayMessageRouter.Test.ExpiredType.Child");

	struct FGameInstanceScope
	{
		TStrongObjectPtr<UGameInstance> GameInstance{NewObject<UGameInstance>(GEngine)};

		FGameInstanceScope()
		{
			GameInstance->InitializeStandalone(TEXT("GameplayMessageListenerTest"));
		}

		~FGameInstanceScope()
		{
			UWorld* World = GameInstance->GetWorld();
			GameInstance->Shutdown();
			if (World)
			{
				World->DestroyWorld(false);
				GEngine->DestroyWorldContext(World);
				World->GetPackage()->SetDirtyFlag(false);
			}
		}
	};
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FGameplayMessageExpiredParentListenerTest,
	"GGYGO.Messages.Router.ExpiredParentListener",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FGameplayMessageExpiredParentListenerTest::RunTest(const FString& Parameters)
{
	using namespace GameplayMessageSubsystemTests;
	FGameInstanceScope Scope;
	UGameplayMessageSubsystem* Router = Scope.GameInstance->GetSubsystem<UGameplayMessageSubsystem>();
	if (!TestNotNull(TEXT("真实 GameInstance 消息路由"), Router)) { return false; }

	// 走蓝图异步监听的真实入口。动态类型退役后，路由和 Action 中的弱引用一起失效。
	UScriptStruct* PayloadType = NewObject<UScriptStruct>();
	TWeakObjectPtr<UScriptStruct> WeakPayloadType(PayloadType);
	TStrongObjectPtr<UAsyncAction_ListenForGameplayMessage> ExpiredListener(
		UAsyncAction_ListenForGameplayMessage::ListenForGameplayMessages(
			Scope.GameInstance->GetWorld(), ParentChannel, PayloadType, EGameplayMessageMatch::PartialMatch));
	if (!TestNotNull(TEXT("父通道异步监听"), ExpiredListener.Get())) { return false; }
	ExpiredListener->Activate();

	int32 ChildCalls = 0;
	int32 ParentPartialCalls = 0;
	int32 ParentExactCalls = 0;
	const FVector Message(1.0, 2.0, 3.0);
	// 父、子通道分别注册首个监听，使它们处在原来会误删子监听的场景中。
	FGameplayMessageListenerHandle ChildHandle = Router->RegisterListener<FVector>(ChildChannel,
		[this, &ChildCalls, Message](FGameplayTag Channel, const FVector& Payload)
		{
			++ChildCalls;
			TestEqual(TEXT("子监听仍收到原广播通道"), Channel, ChildChannel.GetTag());
			TestEqual(TEXT("子监听仍收到原载荷"), Payload, Message);
		});
	FGameplayMessageListenerHandle ParentPartialHandle = Router->RegisterListener<FVector>(ParentChannel,
		[&ParentPartialCalls](FGameplayTag, const FVector&) { ++ParentPartialCalls; }, EGameplayMessageMatch::PartialMatch);
	FGameplayMessageListenerHandle ParentExactHandle = Router->RegisterListener<FVector>(ParentChannel,
		[&ParentExactCalls](FGameplayTag, const FVector&) { ++ParentExactCalls; });

	PayloadType->MarkAsGarbage();
	TestFalse(TEXT("监听类型确实已失效"), WeakPayloadType.IsValid());
	AddExpectedError(TEXT("Listener struct type has gone invalid"), EAutomationExpectedErrorFlags::Contains, 1);
	Router->BroadcastMessage(ChildChannel, Message);
	Router->BroadcastMessage(ChildChannel, Message);
	TestEqual(TEXT("清理父监听后，子监听连续收到两次广播"), ChildCalls, 2);
	TestEqual(TEXT("有效父级 PartialMatch 连续收到两次广播"), ParentPartialCalls, 2);
	TestEqual(TEXT("父级 ExactMatch 不接收子通道广播"), ParentExactCalls, 0);

	Router->BroadcastMessage(ParentChannel, Message);
	TestEqual(TEXT("父通道再次广播不重复诊断已清理监听"), ParentPartialCalls, 3);
	TestEqual(TEXT("有效 ExactMatch 仍收到父通道广播"), ParentExactCalls, 1);
	ExpiredListener->SetReadyToDestroy();
	ChildHandle.Unregister();
	ParentPartialHandle.Unregister();
	ParentExactHandle.Unregister();
	return true;
}
#endif
