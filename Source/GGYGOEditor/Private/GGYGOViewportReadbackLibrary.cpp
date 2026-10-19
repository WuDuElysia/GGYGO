/** @file GGYGOViewportReadbackLibrary.cpp @brief 沿原 viewport/SetupView 采集表面或投影值并归还当前任务资源。 */
#include "GGYGOViewportReadbackLibrary.h"

#include "Camera/GGYGOCameraComponent.h"
#include "Camera/GGYGOCameraMode.h"
#include "Camera/GGYGOPlayerCameraManager.h"
#include "Editor.h"
#include "Engine/Engine.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "RHIResources.h"
#include "SceneInterface.h"
#include "SceneView.h"
#include "SceneViewExtension.h"
#include "Serialization/JsonSerializer.h"
#include "Slate/SceneViewport.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/SViewport.h"

namespace GGYGOViewportReadback
{
	FString NativeFrame()
	{
		return FString::Printf(TEXT("%llu"), GFrameCounter);
	}
}

/** 只属于这次 Editor 观察；运行时相机仍是唯一确认与 POV 写端。 */
struct FGGYGOPlayerViewObservationState
{
	TWeakObjectPtr<ULocalPlayer> Player;
	TWeakObjectPtr<UClass> ModeClass;
	TWeakObjectPtr<APlayerController> Controller;
	TWeakObjectPtr<AGGYGOPlayerCameraManager> Manager;
	TWeakObjectPtr<APawn> Pawn;
	TWeakObjectPtr<UGGYGOCameraComponent> Camera;
	TSharedPtr<ISceneViewExtension, ESPMode::ThreadSafe> Extension;
	FDelegateHandle BeginDrawHandle;
	FDelegateHandle EndDrawHandle;
	TSharedPtr<FJsonObject> Source = MakeShared<FJsonObject>();
	TSharedPtr<FJsonObject> LastDraw = MakeShared<FJsonObject>();
	TSharedPtr<FJsonObject> Projection;
	int32 MaxDraws = 0;
	int32 DrawCount = 0;
	int32 ControllerId = INDEX_NONE;
	bool bPlayerPinned = false;
	bool bDrawOpen = false;
	bool bArmConfirmationKnown = false;
	bool bConfirmedAtArm = false;
	bool bSawUnconfirmed = false;
	bool bReleased = false;
};

/** 只消费自然玩家视图；渲染线程回调全部沿基类空实现。 */
struct FGGYGOPlayerViewExtension final : FSceneViewExtensionBase
{
	FGGYGOPlayerViewExtension(const FAutoRegister& AutoRegister, UGGYGOViewportReadbackTask* InTask)
		: FSceneViewExtensionBase(AutoRegister), Task(InTask) {}
	virtual bool IsActiveThisFrame_Internal(const FSceneViewExtensionContext& Context) const override
	{
		if (!IsInGameThread()) { return false; }
		const UGGYGOViewportReadbackTask* Original = Task.Get();
		return Original && Original->Result.Status == EGGYGOViewportReadbackStatus::Pending
			&& Original->PlayerView.IsValid() && !Original->PlayerView->bReleased
			&& Context.Viewport == Original->OriginalViewport && Context.GetWorld() == Original->OriginalWorld.Get();
	}
	virtual void SetupView(FSceneViewFamily& Family, FSceneView& View) override
	{
		if (UGGYGOViewportReadbackTask* Original = Task.Get()) { Original->OnPlayerViewSetup(Family, View); }
	}
	TWeakObjectPtr<UGGYGOViewportReadbackTask> Task;
};

UGGYGOViewportReadbackTask* UGGYGOViewportReadbackLibrary::BeginGameViewportReadback(UWorld* ExpectedWorld)
{
	check(IsInGameThread());
	UGGYGOViewportReadbackTask* Task = NewObject<UGGYGOViewportReadbackTask>(GetTransientPackage(), NAME_None, RF_Transient);
	Task->Initialize(ExpectedWorld);
	return Task;
}

UGGYGOViewportReadbackTask* UGGYGOViewportReadbackLibrary::BeginPlayerViewObservation(UWorld* ExpectedWorld,
	ULocalPlayer* ExpectedPlayer, TSubclassOf<UGGYGOCameraMode> ExpectedMode, int32 MaxDraws)
{
	check(IsInGameThread());
	UGGYGOViewportReadbackTask* Task = NewObject<UGGYGOViewportReadbackTask>(GetTransientPackage(), NAME_None, RF_Transient);
	Task->Initialize(ExpectedWorld, false);
	if (Task->Result.Status == EGGYGOViewportReadbackStatus::Pending)
	{
		Task->InitializePlayerView(ExpectedPlayer, ExpectedMode, MaxDraws);
	}
	return Task;
}

void UGGYGOViewportReadbackTask::Initialize(UWorld* ExpectedWorld, bool bReadPixels)
{
	Result.bPlayerViewOnly = !bReadPixels;
	Result.Status = EGGYGOViewportReadbackStatus::Pending;
	Result.Error.Reset();
	Result.RequestFrame = GGYGOViewportReadback::NativeFrame();
	Result.WorldPath = GetPathNameSafe(ExpectedWorld);
	if (!IsValid(ExpectedWorld) || !ExpectedWorld->IsGameWorld() || !GEngine)
	{
		Fail(TEXT("需要明确且存活的游戏 World。"));
		return;
	}
	UGameViewportClient* Client = ExpectedWorld->GetGameViewport();
	const FWorldContext* Context = GEngine->GetWorldContextFromWorld(ExpectedWorld);
	if (!IsValid(Client) || Client->GetWorld() != ExpectedWorld || !Context)
	{
		Fail(TEXT("ExpectedWorld 没有属于它的游戏 viewport client 或原生 WorldContext。"));
		return;
	}
	OriginalWorld = ExpectedWorld;
	OriginalClient = Client;
	OriginalViewport = Client->GetGameViewport();
	const TSharedPtr<SViewport> Widget = Client->GetGameViewportWidget();
	OriginalWidget = Widget;
	OriginalInterface = Widget ? Widget->GetViewportInterface() : TWeakPtr<ISlateViewport>();
	Result.WorldObjectId = FString::Printf(TEXT("%u"), ExpectedWorld->GetUniqueID());
	Result.GameViewportClientPath = Client->GetPathName();
	Result.GameViewportClientObjectId = FString::Printf(TEXT("%u"), Client->GetUniqueID());
	Result.ViewportIdentity = FString::Printf(TEXT("%p"), static_cast<FViewport*>(OriginalViewport));
	Result.WorldContextHandle = Context->ContextHandle;
	Result.PIEInstance = Context->PIEInstance;
	Result.WorldType = static_cast<uint8>(ExpectedWorld->WorldType);
	Result.NetMode = static_cast<uint8>(ExpectedWorld->GetNetMode());
	TSharedPtr<ISlateViewport> Interface;
	FString Error;
	if (!PinOriginalViewport(Interface, Error))
	{
		Fail(Error);
		return;
	}
	if (bReadPixels)
	{
		RenderedHandle = UGameViewportClient::OnViewportRendered().AddUObject(this, &ThisClass::OnViewportRendered);
	}
	CloseHandle = Client->OnCloseRequested().AddUObject(this, &ThisClass::OnViewportCloseRequested);
	WorldCleanupHandle = FWorldDelegates::OnWorldCleanup.AddUObject(this, &ThisClass::OnWorldCleanup);
	EndPIEHandle = FEditorDelegates::EndPIE.AddUObject(this, &ThisClass::OnEndPIE);
}

void UGGYGOViewportReadbackTask::InitializePlayerView(ULocalPlayer* ExpectedPlayer,
	TSubclassOf<UGGYGOCameraMode> ExpectedMode, int32 MaxDraws)
{
	if (!IsValid(ExpectedPlayer) || !ExpectedMode || MaxDraws < 1 || MaxDraws > 4096)
	{
		Fail(TEXT("玩家视图观察须明确原 LocalPlayer、精确 CameraMode 类及 1..4096 的自然 Draw 上限。"));
		return;
	}
	PlayerView = MakeShared<FGGYGOPlayerViewObservationState>();
	PlayerView->Player = ExpectedPlayer;
	PlayerView->ModeClass = ExpectedMode.Get();
	PlayerView->MaxDraws = MaxDraws;
	PlayerView->Source->SetStringField(TEXT("local_player"), ExpectedPlayer->GetPathName());
	PlayerView->Source->SetStringField(TEXT("local_player_id"), LexToString(ExpectedPlayer->GetUniqueID()));
	PlayerView->Source->SetStringField(TEXT("expected_mode_class"), ExpectedMode->GetPathName());
	bool bReady;
	FString Error;
	if (!PinOriginalPlayer(Error, bReady)) { Fail(Error); return; }
	PlayerView->bArmConfirmationKnown = bReady;
	PlayerView->bConfirmedAtArm = bReady && PlayerView->Manager->HasConfirmedNativeCameraView();
	PlayerView->bSawUnconfirmed = bReady && !PlayerView->bConfirmedAtArm;
	UGameViewportClient* Client = OriginalClient.Get();
	PlayerView->BeginDrawHandle = Client->OnBeginDraw().AddUObject(this, &ThisClass::OnPlayerDrawBegin);
	PlayerView->EndDrawHandle = Client->OnEndDraw().AddUObject(this, &ThisClass::OnPlayerDrawEnd);
	PlayerView->Extension = FSceneViewExtensions::NewExtension<FGGYGOPlayerViewExtension>(this);
}

bool UGGYGOViewportReadbackTask::PinOriginalPlayer(FString& OutError, bool& bOutReady)
{
	bOutReady = false;
	ULocalPlayer* Player = PlayerView->Player.Get();
	UWorld* World = OriginalWorld.Get();
	if (!IsValid(Player) || !PlayerView->ModeClass.IsValid() || Player->GetWorld() != World
		|| Player->ViewportClient != OriginalClient.Get())
	{
		OutError = TEXT("原 LocalPlayer/World/viewport 或指定模式类已经失效或换代。");
		return false;
	}
	APlayerController* Controller = Player->PlayerController.Get();
	APlayerCameraManager* Manager = IsValid(Controller) ? Controller->PlayerCameraManager.Get() : nullptr;
	APawn* Pawn = IsValid(Controller) ? Controller->GetPawn() : nullptr;
	if (!PlayerView->bPlayerPinned && (!IsValid(Controller) || !IsValid(Manager) || !IsValid(Pawn)))
	{
		return true; // 原生装配尚未就绪；只等这个原 LocalPlayer，不选择其它玩家。
	}
	AGGYGOPlayerCameraManager* CameraManager = Cast<AGGYGOPlayerCameraManager>(Manager);
	if (!IsValid(Controller) || !IsValid(CameraManager) || !IsValid(Pawn)
		|| Controller->GetWorld() != World || CameraManager->GetWorld() != World || Pawn->GetWorld() != World
		|| Controller->GetLocalPlayer() != Player || CameraManager->APlayerCameraManager::GetOwningPlayerController() != Controller)
	{
		OutError = TEXT("原玩家 PC/项目 PCM/Pawn/World 关联不成立。");
		return false;
	}
	if (!PlayerView->bPlayerPinned)
	{
		PlayerView->Controller = Controller;
		PlayerView->Manager = CameraManager;
		PlayerView->Pawn = Pawn;
		PlayerView->ControllerId = Player->GetControllerId();
		PlayerView->bPlayerPinned = true;
		for (const auto& Item : {TPair<const TCHAR*, UObject*>(TEXT("pc"), Controller),
			{TEXT("pcm"), CameraManager}, {TEXT("pawn"), Pawn}})
		{
			PlayerView->Source->SetStringField(Item.Key, Item.Value->GetPathName());
			PlayerView->Source->SetStringField(FString(Item.Key) + TEXT("_id"), LexToString(Item.Value->GetUniqueID()));
		}
	}
	if (PlayerView->Controller != Controller || PlayerView->Manager != CameraManager || PlayerView->Pawn != Pawn
		|| PlayerView->ControllerId != Player->GetControllerId())
	{
		OutError = TEXT("已固定的原 PC/PCM/Pawn/ControllerId 已换代。");
		return false;
	}
	if (PlayerView->Camera.IsExplicitlyNull())
	{
		UGGYGOCameraComponent* Camera = UGGYGOCameraComponent::FindCameraComponent(Pawn);
		if (!IsValid(Camera) && !CameraManager->HasConfirmedNativeCameraView()) { return true; }
		if (!IsValid(Camera))
		{
			OutError = TEXT("原 PCM 已确认但原 Pawn 没有真实 CameraComponent。");
			return false;
		}
		PlayerView->Camera = Camera;
		PlayerView->Source->SetStringField(TEXT("camera"), Camera->GetPathName());
		PlayerView->Source->SetStringField(TEXT("camera_id"), LexToString(Camera->GetUniqueID()));
	}
	if (!PlayerView->Camera.IsValid() || PlayerView->Camera->GetOwner() != Pawn)
	{
		OutError = TEXT("已固定的原 CameraComponent 已退役或换源。");
		return false;
	}
	bOutReady = true;
	return true;
}

void UGGYGOViewportReadbackTask::OnPlayerDrawBegin()
{
	check(IsInGameThread());
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending) { return; }
	TSharedPtr<ISlateViewport> Interface;
	bool bReady;
	FString Error;
	if (!PinOriginalViewport(Interface, Error) || !PinOriginalPlayer(Error, bReady)) { Fail(Error); return; }
	PlayerView->bDrawOpen = true;
	++PlayerView->DrawCount;
	PlayerView->LastDraw = MakeShared<FJsonObject>();
	PlayerView->LastDraw->SetStringField(TEXT("begin_frame"), GGYGOViewportReadback::NativeFrame());
	PlayerView->LastDraw->SetBoolField(TEXT("original_player_ready"), bReady);
	if (bReady)
	{
		const bool bConfirmed = PlayerView->Manager->HasConfirmedNativeCameraView();
		PlayerView->bSawUnconfirmed |= !bConfirmed;
		PlayerView->LastDraw->SetBoolField(TEXT("confirmed_at_begin_draw"), bConfirmed);
		PlayerView->LastDraw->SetNumberField(TEXT("publication_state"), static_cast<uint8>(PlayerView->Manager->GetCameraPublicationState()));
		PlayerView->LastDraw->SetNumberField(TEXT("camera_cache_time"), PlayerView->Manager->GetCameraCacheTime());
	}
}

void UGGYGOViewportReadbackTask::OnPlayerDrawEnd()
{
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending) { return; }
	PlayerView->bDrawOpen = false;
	if (PlayerView->DrawCount >= PlayerView->MaxDraws)
	{
		Fail(TEXT("自然 Draw 已到明确上限，尚未取得原玩家完整投影成功后的匹配 SetupView。"));
	}
}

void UGGYGOViewportReadbackTask::OnPlayerViewSetup(FSceneViewFamily& ViewFamily, FSceneView& View)
{
	check(IsInGameThread());
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending || !PlayerView.IsValid()
		|| ViewFamily.RenderTarget != static_cast<FViewport*>(OriginalViewport)
		|| !ViewFamily.Scene || ViewFamily.Scene->GetWorld() != OriginalWorld.Get()) { return; }
	TSharedPtr<ISlateViewport> Interface;
	bool bReady;
	FString Error;
	if (!PinOriginalViewport(Interface, Error) || !PinOriginalPlayer(Error, bReady)) { Fail(Error); return; }
	if (!bReady || View.PlayerIndex != PlayerView->ControllerId) { return; }
	if (!PlayerView->bDrawOpen)
	{
		Fail(TEXT("匹配视图所在 Draw 开始前没有布防见证，不能认证本次投影观察。"));
		return;
	}
	if (View.ViewActor.ActorUniqueId != PlayerView->Pawn->GetUniqueID()
		|| !PlayerView->Manager->HasConfirmedNativeCameraView())
	{
		Fail(TEXT("自然 SetupView 的原 ViewActor 或 PCM 确认状态不匹配。"));
		return;
	}
	const FGGYGOCameraModeObservation Mode = PlayerView->Camera->QueryCameraMode(PlayerView->ModeClass.Get());
	const bool bModeEligible = Mode.Status == EGGYGOCameraModeObservationStatus::Available && Mode.bActive && Mode.bInPool
		&& IsValid(Mode.Mode) && Mode.Mode->GetClass() == PlayerView->ModeClass.Get()
		&& Mode.OriginalOwner == PlayerView->Pawn.Get() && Mode.OriginalComponent == PlayerView->Camera.Get();
	const FMatrix& Matrix = View.ViewMatrices.GetProjectionMatrix();
	TArray<TSharedPtr<FJsonValue>> Values;
	for (int32 Row = 0; Row != 4; ++Row)
	{
		for (int32 Column = 0; Column != 4; ++Column)
		{
			if (!FMath::IsFinite(Matrix.M[Row][Column])) { Fail(TEXT("自然投影矩阵含非有限值。")); return; }
			Values.Add(MakeShared<FJsonValueNumber>(Matrix.M[Row][Column]));
		}
	}
	PlayerView->Projection = MakeShared<FJsonObject>();
	PlayerView->Projection->SetStringField(TEXT("frame"), GGYGOViewportReadback::NativeFrame());
	PlayerView->Projection->SetNumberField(TEXT("mode_query_status"), static_cast<uint8>(Mode.Status));
	PlayerView->Projection->SetStringField(TEXT("mode_query_diagnostic"), Mode.Diagnostic);
	PlayerView->Projection->SetBoolField(TEXT("mode_active_in_pool"), bModeEligible);
	if (bModeEligible)
	{
		PlayerView->Projection->SetStringField(TEXT("mode"), Mode.Mode->GetPathName());
		PlayerView->Projection->SetStringField(TEXT("mode_id"), LexToString(Mode.Mode->GetUniqueID()));
		PlayerView->Projection->SetStringField(TEXT("stack"), GetPathNameSafe(Mode.OriginalStack));
	}
	PlayerView->Projection->SetBoolField(TEXT("full_local_player_projection_returned"), true);
	PlayerView->Projection->SetNumberField(TEXT("player_index"), View.PlayerIndex);
	PlayerView->Projection->SetStringField(TEXT("view_actor_id"), LexToString(View.ViewActor.ActorUniqueId));
	PlayerView->Projection->SetBoolField(TEXT("armed_before_matched_draw"), true);
	PlayerView->Projection->SetNumberField(TEXT("stereo_view_index"), View.StereoViewIndex);
	PlayerView->Projection->SetNumberField(TEXT("camera_cache_time"), PlayerView->Manager->GetCameraCacheTime());
	PlayerView->Projection->SetNumberField(TEXT("publication_state"), static_cast<uint8>(PlayerView->Manager->GetCameraPublicationState()));
	PlayerView->Projection->SetArrayField(TEXT("projection_matrix_row_major"), Values);
	PlayerView->Projection->SetNumberField(TEXT("view_rect_min_x"), View.UnscaledViewRect.Min.X);
	PlayerView->Projection->SetNumberField(TEXT("view_rect_min_y"), View.UnscaledViewRect.Min.Y);
	PlayerView->Projection->SetNumberField(TEXT("view_rect_max_x"), View.UnscaledViewRect.Max.X);
	PlayerView->Projection->SetNumberField(TEXT("view_rect_max_y"), View.UnscaledViewRect.Max.Y);
	const FMinimalViewInfo& Cache = PlayerView->Manager->APlayerCameraManager::GetCameraCacheView();
	PlayerView->Projection->SetStringField(TEXT("native_cache_location"), Cache.Location.ToString());
	PlayerView->Projection->SetStringField(TEXT("native_cache_rotation"), Cache.Rotation.ToString());
	PlayerView->Projection->SetNumberField(TEXT("native_cache_fov"), Cache.FOV);
	PlayerView->Projection->SetStringField(TEXT("view_location"), View.ViewLocation.ToString());
	PlayerView->Projection->SetStringField(TEXT("view_rotation"), View.ViewRotation.ToString());
	Result.RenderTargetSize = OriginalViewport->GetRenderTargetTextureSizeXY();
	Result.RenderCallbackFrame = GGYGOViewportReadback::NativeFrame();
	Result.ReadbackCompleteFrame = Result.RenderCallbackFrame;
	Result.Status = EGGYGOViewportReadbackStatus::Complete;
	DetachCallbacks();
}

void UGGYGOViewportReadbackTask::UpdatePlayerViewJson()
{
	if (!PlayerView.IsValid()) { return; }
	auto Json = MakeShared<FJsonObject>();
	Json->SetStringField(TEXT("schema"), TEXT("GGYGO.PlayerViewObservation/v1"));
	Json->SetStringField(TEXT("meaning"), TEXT("仅本次布防后的首个匹配自然 SetupView；确认位精确写入时刻及全局首 Draw 未观察。"));
	Json->SetObjectField(TEXT("original_player"), PlayerView->Source);
	Json->SetObjectField(TEXT("last_draw"), PlayerView->LastDraw);
	if (PlayerView->Projection.IsValid()) { Json->SetObjectField(TEXT("projection"), PlayerView->Projection); }
	Json->SetBoolField(TEXT("arm_confirmation_known"), PlayerView->bArmConfirmationKnown);
	Json->SetBoolField(TEXT("confirmed_at_arm"), PlayerView->bConfirmedAtArm);
	Json->SetBoolField(TEXT("unconfirmed_state_observed"), PlayerView->bSawUnconfirmed);
	Json->SetBoolField(TEXT("first_confirmation_write_observed"), false);
	Json->SetBoolField(TEXT("first_observed_only"), !PlayerView->bArmConfirmationKnown || PlayerView->bConfirmedAtArm);
	Json->SetNumberField(TEXT("draws_since_arm"), PlayerView->DrawCount);
	Json->SetNumberField(TEXT("draw_limit"), PlayerView->MaxDraws);
	Json->SetBoolField(TEXT("subscriptions_released"), PlayerView->bReleased);
	FString Payload;
	if (FJsonSerializer::Serialize(Json, TJsonWriterFactory<>::Create(&Payload)))
	{
		Result.PlayerViewJson = MoveTemp(Payload);
	}
	else
	{
		Result.PlayerViewJson = TEXT("{\"schema\":\"GGYGO.PlayerViewObservation/v1\",\"serialization_failed\":true}");
	}
}

bool UGGYGOViewportReadbackTask::PinOriginalViewport(TSharedPtr<ISlateViewport>& OutInterface, FString& OutError) const
{
	OutInterface = OriginalInterface.Pin();
	UWorld* World = OriginalWorld.Get();
	UGameViewportClient* Client = OriginalClient.Get();
	const TSharedPtr<SViewport> Widget = OriginalWidget.Pin();
	if (!IsValid(World) || !IsValid(Client) || !OutInterface || !Widget || !OriginalViewport
		|| World->GetGameViewport() != Client || Client->GetWorld() != World
		|| Client->GetGameViewport() != OriginalViewport || Client->GetGameViewportWidget() != Widget
		|| Widget->GetViewportInterface().Pin() != OutInterface
		|| OutInterface.Get() != static_cast<ISlateViewport*>(OriginalViewport))
	{
		OutError = TEXT("原 World/client/widget/viewport 已退役、换代或接口尚未就绪。");
		return false;
	}
	// 到这里才由 Pin 的原共享对象保护 viewport 的调用；不解引用失去原接口的 raw 地址。
	const FWorldContext* Context = GEngine ? GEngine->GetWorldContextFromWorld(World) : nullptr;
	if (!Context || Context->ContextHandle != Result.WorldContextHandle || Context->PIEInstance != Result.PIEInstance
		|| static_cast<uint8>(World->WorldType) != Result.WorldType || static_cast<uint8>(World->GetNetMode()) != Result.NetMode
		|| OriginalViewport->GetClient() != Client)
	{
		OutError = TEXT("原 WorldContext/PIE/NetMode 或实际 viewport client 已变化。");
		return false;
	}
	return true;
}

void UGGYGOViewportReadbackTask::OnViewportRendered(FViewport* Viewport)
{
	check(IsInGameThread());
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending)
	{
		return;
	}
	TSharedPtr<ISlateViewport> Interface;
	FString Error;
	if (!PinOriginalViewport(Interface, Error))
	{
		Fail(Error);
		return;
	}
	if (Viewport != static_cast<FViewport*>(OriginalViewport))
	{
		return;
	}
	// Remove 仅摘除自身条目；原生广播锁内会延后 compact。读回可能 Flush 并返入，先禁止重复消费。
	const TStrongObjectPtr<UGGYGOViewportReadbackTask> TaskScope(this);
	Result.Status = EGGYGOViewportReadbackStatus::Reading;
	Result.RenderCallbackFrame = GGYGOViewportReadback::NativeFrame();
	UGameViewportClient::OnViewportRendered().Remove(RenderedHandle);
	RenderedHandle.Reset();
	const FIntPoint Size = Viewport->GetRenderTargetTextureSizeXY();
	Result.RenderTargetSize = Size;
	Result.bHDR = Viewport->GetSceneHDREnabled();
	const auto& Surface = Viewport->GetShaderResourceTexture();
	if (!Surface.IsValid() || Size.X <= 0 || Size.Y <= 0 || static_cast<int64>(Size.X) * Size.Y > MAX_int32)
	{
		Fail(TEXT("原生读回表面无效，或 RT 尺寸不能由 FColor 数组表示。"));
		return;
	}
	// 取值块内借用描述符；跨 ReadPixels/Flush 只保留普通字段值，避免构造描述符的 GPU mask。
	EPixelFormat SurfaceFormat;
	ETextureDimension SurfaceDimension;
	uint16 SurfaceArraySize;
	uint8 SurfaceNumSamples;
	FIntPoint SurfaceExtent;
	{
		const FRHITextureDesc& Description = Surface->GetDesc();
		SurfaceFormat = Description.Format;
		SurfaceDimension = Description.Dimension;
		SurfaceArraySize = Description.ArraySize;
		SurfaceNumSamples = Description.NumSamples;
		SurfaceExtent = Description.Extent;
	}
	Result.RenderTargetFormat = static_cast<int32>(SurfaceFormat);
	if (Result.bHDR || SurfaceDimension != ETextureDimension::Texture2D || SurfaceArraySize != 1
		|| SurfaceNumSamples != 1 || SurfaceExtent != Size)
	{
		Fail(TEXT("仅支持尺寸明确的单层、单采样 2D SDR 表面；HDR、数组、MSAA 或尺寸不一致不能作为本次 PNG。"));
		return;
	}
	TArray<FColor> Pixels;
	const bool bRead = GetViewportScreenShot(Viewport, Pixels, FIntRect(FIntPoint::ZeroValue, Size));
	// ReadPixels 会排入原生 ReadSurfaceData 并 FlushRenderingCommands；期间可处理生命周期回调。
	if (Result.Status != EGGYGOViewportReadbackStatus::Reading)
	{
		return;
	}
	TSharedPtr<ISlateViewport> CurrentInterface;
	if (!PinOriginalViewport(CurrentInterface, Error))
	{
		Fail(Error);
		return;
	}
	const auto& CurrentSurface = Viewport->GetShaderResourceTexture();
	if (!bRead || Pixels.Num() != static_cast<int64>(Size.X) * Size.Y || !CurrentSurface.IsValid()
		|| Viewport->GetRenderTargetTextureSizeXY() != Size || Viewport->GetSceneHDREnabled() != Result.bHDR
		|| CurrentSurface->GetDesc().Extent != SurfaceExtent || CurrentSurface->GetDesc().Format != SurfaceFormat
		|| CurrentSurface->GetDesc().Dimension != SurfaceDimension || CurrentSurface->GetDesc().ArraySize != SurfaceArraySize
		|| CurrentSurface->GetDesc().NumSamples != SurfaceNumSamples)
	{
		Fail(TEXT("原生像素读回失败，或返栈后读回表面的尺寸/格式/HDR 已改变。"));
		return;
	}
	for (FColor& Color : Pixels)
	{
		Color.A = 255;
	}
	TArray64<uint8> Png;
	FImageUtils::PNGCompressImageArray(Size.X, Size.Y, TArrayView64<const FColor>(Pixels.GetData(), Pixels.Num()), Png);
	if (Result.Status != EGGYGOViewportReadbackStatus::Reading)
	{
		return;
	}
	if (!PinOriginalViewport(CurrentInterface, Error))
	{
		Fail(Error);
		return;
	}
	if (Png.IsEmpty() || Png.Num() > MAX_int32)
	{
		Fail(TEXT("原生 PNG 编码为空或超出反射字节数组容量。"));
		return;
	}
	Result.PngBytes.Append(Png.GetData(), static_cast<int32>(Png.Num()));
	Result.ReadbackCompleteFrame = GGYGOViewportReadback::NativeFrame();
	Result.Status = EGGYGOViewportReadbackStatus::Complete;
	DetachCallbacks();
}

FGGYGOViewportReadbackResult UGGYGOViewportReadbackTask::ReadResult()
{
	check(IsInGameThread());
	if (Result.Status == EGGYGOViewportReadbackStatus::Pending || Result.Status == EGGYGOViewportReadbackStatus::Reading)
	{
		TSharedPtr<ISlateViewport> Interface;
		FString Error;
		if (!PinOriginalViewport(Interface, Error))
		{
			Fail(Error);
		}
	}
	UpdatePlayerViewJson();
	return Result;
}

void UGGYGOViewportReadbackTask::Release()
{
	check(IsInGameThread());
	if (Result.Status == EGGYGOViewportReadbackStatus::Pending || Result.Status == EGGYGOViewportReadbackStatus::Reading)
	{
		Result.Status = EGGYGOViewportReadbackStatus::Cancelled;
		Result.Error = TEXT("[Editor.ViewportReadback] 调用方释放了尚未完成的原请求。");
	}
	DetachCallbacks();
}

void UGGYGOViewportReadbackTask::OnViewportCloseRequested(FViewport* Viewport)
{
	if (Viewport == static_cast<FViewport*>(OriginalViewport))
	{
		Fail(TEXT("原 viewport 请求关闭，读回未完成。"));
	}
}

void UGGYGOViewportReadbackTask::OnWorldCleanup(UWorld* World, bool bSessionEnded, bool bCleanupResources)
{
	if (World == OriginalWorld.Get())
	{
		Fail(TEXT("原 World 正在清理，读回未完成。"));
	}
}

void UGGYGOViewportReadbackTask::OnEndPIE(bool bSimulating)
{
	if (Result.WorldType == static_cast<uint8>(EWorldType::PIE))
	{
		Fail(TEXT("原 PIE 会话结束，读回未完成。"));
	}
}

void UGGYGOViewportReadbackTask::Fail(const FString& Reason)
{
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending && Result.Status != EGGYGOViewportReadbackStatus::Reading)
	{
		return;
	}
	Result.Status = EGGYGOViewportReadbackStatus::Failed;
	Result.Error = FString::Printf(TEXT("[Editor.ViewportReadback] World=%s Client=%s Viewport=%s %s"),
		*Result.WorldPath, *Result.GameViewportClientPath, *Result.ViewportIdentity, *Reason);
	DetachCallbacks();
}

void UGGYGOViewportReadbackTask::DetachCallbacks()
{
	if (PlayerView.IsValid())
	{
		const FDelegateHandle Begin = PlayerView->BeginDrawHandle;
		const FDelegateHandle End = PlayerView->EndDrawHandle;
		PlayerView->BeginDrawHandle.Reset();
		PlayerView->EndDrawHandle.Reset();
		PlayerView->bReleased = true;
		PlayerView->bDrawOpen = false;
		PlayerView->Extension.Reset();
		if (UGameViewportClient* Client = OriginalClient.Get())
		{
			if (Begin.IsValid()) { Client->OnBeginDraw().Remove(Begin); }
			if (End.IsValid()) { Client->OnEndDraw().Remove(End); }
		}
	}
	if (RenderedHandle.IsValid())
	{
		UGameViewportClient::OnViewportRendered().Remove(RenderedHandle);
	}
	RenderedHandle.Reset();
	if (CloseHandle.IsValid())
	{
		if (UGameViewportClient* Client = OriginalClient.Get())
		{
			Client->OnCloseRequested().Remove(CloseHandle);
		}
	}
	CloseHandle.Reset();
	if (WorldCleanupHandle.IsValid())
	{
		FWorldDelegates::OnWorldCleanup.Remove(WorldCleanupHandle);
	}
	WorldCleanupHandle.Reset();
	if (EndPIEHandle.IsValid())
	{
		FEditorDelegates::EndPIE.Remove(EndPIEHandle);
	}
	EndPIEHandle.Reset();
	OriginalWorld.Reset();
	OriginalClient.Reset();
	OriginalWidget.Reset();
	OriginalInterface.Reset();
	OriginalViewport = nullptr;
}

void UGGYGOViewportReadbackTask::BeginDestroy()
{
	Release();
	Super::BeginDestroy();
}
