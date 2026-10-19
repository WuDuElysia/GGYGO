/** @file GGYGOPlayerInputBridgeLibrary.cpp
 *  @brief 通过公开 C++ 接口读取原输入装配及暂停 owner，并向原 PC 提交软件数字键。
 */
#include "GGYGOPlayerInputBridgeLibrary.h"

#include "Input/GGYGOInputComponent.h"
#include "Input/GGYGOPlayerInput.h"
#include "Player/GGYGOPlayerController.h"

#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "EnhancedPlayerInput.h"
#include "GameFramework/InputDeviceLibrary.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerState.h"
#include "GameFramework/WorldSettings.h"
#include "HAL/PlatformTime.h"
#include "InputKeyEventArgs.h"

namespace GGYGOPlayerInputBridge
{
	/** 仅在当前调用中使用；不缓存或持有后继权限。 */
	struct FResolvedAssembly
	{
		AGGYGOPlayerController* PlayerController = nullptr;
		APawn* Pawn = nullptr;
		UEnhancedPlayerInput* PlayerInput = nullptr;
		UGGYGOInputComponent* PawnInputComponent = nullptr;
	};

	static EGGYGOPlayerInputAssemblyStatus Diagnose(
		EGGYGOPlayerInputAssemblyStatus Status, const UWorld* World,
		const ULocalPlayer* LocalPlayer, const TCHAR* Reason, FString& OutDiagnostic)
	{
		OutDiagnostic = FString::Printf(TEXT("[Input][PlayerInputBridge] World='%s' LocalPlayer='%s': %s"),
			*GetPathNameSafe(World), *GetPathNameSafe(LocalPlayer), Reason);
		return Status;
	}

	static EGGYGOPlayerInputAssemblyStatus Resolve(
		UWorld* World, ULocalPlayer* LocalPlayer, FResolvedAssembly& Out, FString& OutDiagnostic)
	{
		using EStatus = EGGYGOPlayerInputAssemblyStatus;
		Out = {};
		OutDiagnostic.Reset();
		if (!IsInGameThread() || !IsValid(World) || !IsValid(LocalPlayer) || World->WorldType != EWorldType::PIE)
		{
			return Diagnose(EStatus::Invalid, World, LocalPlayer, TEXT("必须提供 GameThread 上有效的原 PIE World 与 LocalPlayer。"), OutDiagnostic);
		}
		UWorld* LocalWorld = LocalPlayer->GetWorld();
		if (!LocalWorld)
		{
			return Diagnose(EStatus::Waiting, World, LocalPlayer, TEXT("原 LocalPlayer 的 Viewport World 尚未就绪。"), OutDiagnostic);
		}
		if (LocalWorld != World)
		{
			return Diagnose(EStatus::Invalid, World, LocalPlayer, TEXT("原 LocalPlayer 不属于指定 World。"), OutDiagnostic);
		}
		APlayerController* Controller = LocalPlayer->GetPlayerController(World);
		if (!Controller)
		{
			return Diagnose(EStatus::Waiting, World, LocalPlayer, TEXT("原 LocalPlayer 的 PlayerController 尚未就绪。"), OutDiagnostic);
		}
		if (!IsValid(Controller))
		{
			return Diagnose(EStatus::Invalid, World, LocalPlayer, TEXT("原 LocalPlayer 指向已退役的 PlayerController。"), OutDiagnostic);
		}
		ULocalPlayer* AttachedLocalPlayer = Controller->GetLocalPlayer();
		if (!AttachedLocalPlayer)
		{
			return Diagnose(EStatus::Waiting, World, LocalPlayer, TEXT("原 PlayerController 的 LocalPlayer 绑定尚未完成。"), OutDiagnostic);
		}
		AGGYGOPlayerController* GGYGOController = Cast<AGGYGOPlayerController>(Controller);
		if (!GGYGOController || Controller->GetWorld() != World || AttachedLocalPlayer != LocalPlayer
			|| !Controller->IsLocalPlayerController())
		{
			return Diagnose(EStatus::Invalid, World, LocalPlayer, TEXT("PC 类型、World 或双向 LocalPlayer 身份不匹配。"), OutDiagnostic);
		}
		if (!Controller->PlayerInput)
		{
			return Diagnose(EStatus::Waiting, World, LocalPlayer, TEXT("原 PlayerInput 尚未完成装配。"), OutDiagnostic);
		}
		UEnhancedPlayerInput* PlayerInput = Cast<UEnhancedPlayerInput>(Controller->PlayerInput);
		if (!IsValid(PlayerInput) || !PlayerInput->IsA<UGGYGOPlayerInput>() || PlayerInput->GetOuter() != Controller)
		{
			return Diagnose(EStatus::Invalid, World, LocalPlayer,
				TEXT("原 GGYGOPlayerInput 的类型或所有者不匹配。"), OutDiagnostic);
		}
		APawn* Pawn = Controller->GetPawn();
		if (!Pawn)
		{
			return Diagnose(EStatus::Waiting, World, LocalPlayer, TEXT("原 PC 尚未附身 Pawn。"), OutDiagnostic);
		}
		if (!IsValid(Pawn) || Pawn->GetWorld() != World)
		{
			return Diagnose(EStatus::Invalid, World, LocalPlayer, TEXT("原 Pawn 已退役或 World 不匹配。"), OutDiagnostic);
		}
		if (!Pawn->GetController())
		{
			return Diagnose(EStatus::Waiting, World, LocalPlayer, TEXT("原 Pawn 的双向附身尚未完成。"), OutDiagnostic);
		}
		if (Pawn->GetController() != Controller)
		{
			return Diagnose(EStatus::Invalid, World, LocalPlayer, TEXT("原 Pawn 的 Controller 不匹配。"), OutDiagnostic);
		}
		if (!Pawn->InputComponent)
		{
			return Diagnose(EStatus::Waiting, World, LocalPlayer, TEXT("原 Pawn.InputComponent 尚未完成装配。"), OutDiagnostic);
		}
		UGGYGOInputComponent* InputComponent = Cast<UGGYGOInputComponent>(Pawn->InputComponent);
		if (!IsValid(InputComponent) || InputComponent->GetOwner() != Pawn)
		{
			return Diagnose(EStatus::Invalid, World, LocalPlayer, TEXT("原 Pawn GGYGOInputComponent 的类型或所有者不匹配。"), OutDiagnostic);
		}
		Out = {GGYGOController, Pawn, PlayerInput, InputComponent};
		return EStatus::Ready;
	}
}

EGGYGOPlayerInputAssemblyStatus UGGYGOPlayerInputBridgeLibrary::ReadLocalPlayerInputAssembly(
	UWorld* OriginalWorld, ULocalPlayer* OriginalLocalPlayer,
	APlayerController*& OutPlayerController, APawn*& OutPawn,
	UPlayerInput*& OutPlayerInput, UInputComponent*& OutPawnInputComponent,
	FPlatformUserId& OutPlatformUser, FInputDeviceId& OutPrimaryInputDevice, FString& OutDiagnostic)
{
	OutPlayerController = nullptr;
	OutPawn = nullptr;
	OutPlayerInput = nullptr;
	OutPawnInputComponent = nullptr;
	OutPlatformUser = FPlatformUserId();
	OutPrimaryInputDevice = FInputDeviceId();
	GGYGOPlayerInputBridge::FResolvedAssembly Assembly;
	const EGGYGOPlayerInputAssemblyStatus Status = GGYGOPlayerInputBridge::Resolve(
		OriginalWorld, OriginalLocalPlayer, Assembly, OutDiagnostic);
	if (Status != EGGYGOPlayerInputAssemblyStatus::Ready) { return Status; }
	OutPlayerController = Assembly.PlayerController;
	OutPawn = Assembly.Pawn;
	OutPlayerInput = Assembly.PlayerInput;
	OutPawnInputComponent = Assembly.PawnInputComponent;
	OutPlatformUser = OriginalLocalPlayer->GetPlatformUserId();
	OutPrimaryInputDevice = UInputDeviceLibrary::GetPrimaryInputDeviceForUser(OutPlatformUser);
	return Status;
}

bool UGGYGOPlayerInputBridgeLibrary::SubmitDigitalKeyEvent(
	UWorld* OriginalWorld, ULocalPlayer* OriginalLocalPlayer,
	APlayerController* OriginalPlayerController, APawn* OriginalPawn,
	UPlayerInput* OriginalPlayerInput, UInputComponent* OriginalPawnInputComponent,
	FInputDeviceId InputDevice, const FKey& Key, bool bPressed, bool& OutHandled, FString& OutDiagnostic)
{
	OutHandled = false;
	GGYGOPlayerInputBridge::FResolvedAssembly Assembly;
	if (GGYGOPlayerInputBridge::Resolve(OriginalWorld, OriginalLocalPlayer, Assembly, OutDiagnostic)
		!= EGGYGOPlayerInputAssemblyStatus::Ready) { return false; }
	using EStatus = EGGYGOPlayerInputAssemblyStatus;
	if (Assembly.PlayerController != OriginalPlayerController || Assembly.Pawn != OriginalPawn
		|| Assembly.PlayerInput != OriginalPlayerInput || Assembly.PawnInputComponent != OriginalPawnInputComponent)
	{
		GGYGOPlayerInputBridge::Diagnose(EStatus::Invalid, OriginalWorld, OriginalLocalPlayer,
			TEXT("当前装配已替换原对象，拒绝跟随后继装配发送键事件。"), OutDiagnostic);
		return false;
	}
	const FPlatformUserId User = OriginalLocalPlayer->GetPlatformUserId();
	if (!Key.IsValid() || !Key.IsDigital() || !User.IsValid() || !InputDevice.IsValid()
		|| UInputDeviceLibrary::GetUserForInputDevice(InputDevice) != User
		|| OriginalPlayerController->GetPlatformUserId() != User)
	{
		GGYGOPlayerInputBridge::Diagnose(EStatus::Invalid, OriginalWorld, OriginalLocalPlayer,
			TEXT("数字键无效或设备不属于原 LocalPlayer／PC 的 PlatformUser。"), OutDiagnostic);
		return false;
	}
	UGameViewportClient* ViewportClient = OriginalLocalPlayer->ViewportClient;
	if (!IsValid(ViewportClient) || !ViewportClient->Viewport)
	{
		GGYGOPlayerInputBridge::Diagnose(EStatus::Waiting, OriginalWorld, OriginalLocalPlayer,
			TEXT("原 LocalPlayer 的 Viewport 尚未就绪，未提交键事件。"), OutDiagnostic);
		return false;
	}
	const FInputKeyEventArgs Event(ViewportClient->Viewport,
		InputDevice, Key, bPressed ? IE_Pressed : IE_Released, bPressed ? 1.0f : 0.0f, false, FPlatformTime::Cycles64());
	OutHandled = OriginalPlayerController->InputKey(Event);
	return true;
}

bool UGGYGOPlayerInputBridgeLibrary::ReadWorldPauseState(UWorld* OriginalWorld,
	AWorldSettings*& OutWorldSettings, bool& OutPaused, APlayerState*& OutPauserPlayerState,
	FString& OutDiagnostic)
{
	OutWorldSettings = nullptr;
	OutPaused = false;
	OutPauserPlayerState = nullptr;
	OutDiagnostic.Reset();
	if (!IsInGameThread() || !IsValid(OriginalWorld) || OriginalWorld->WorldType != EWorldType::PIE)
	{
		GGYGOPlayerInputBridge::Diagnose(EGGYGOPlayerInputAssemblyStatus::Invalid, OriginalWorld, nullptr,
			TEXT("暂停查询必须指定 GameThread 上有效的原 PIE World。"), OutDiagnostic);
		return false;
	}
	AWorldSettings* Settings = OriginalWorld->GetWorldSettings(false, false);
	if (!IsValid(Settings) || Settings->GetWorld() != OriginalWorld)
	{
		GGYGOPlayerInputBridge::Diagnose(EGGYGOPlayerInputAssemblyStatus::Invalid, OriginalWorld, nullptr,
			TEXT("原 WorldSettings 尚未就绪或 World 来源不匹配。"), OutDiagnostic);
		return false;
	}
	OutWorldSettings = Settings;
	OutPaused = OriginalWorld->IsPaused();
	OutPauserPlayerState = Settings->GetPauserPlayerState();
	return true;
}
