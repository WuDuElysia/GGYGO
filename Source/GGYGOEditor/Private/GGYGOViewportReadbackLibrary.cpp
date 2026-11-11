/** @file GGYGOViewportReadbackLibrary.cpp @brief 沿原 viewport/SetupView 采集表面或投影值并归还当前任务资源。 */
#include "GGYGOViewportReadbackLibrary.h"

#include "Async/TaskGraphInterfaces.h"
#include "Camera/GGYGOCameraComponent.h"
#include "Camera/GGYGOCameraMode.h"
#include "Camera/GGYGOPlayerCameraManager.h"
#include "Editor.h"
#include "Engine/Engine.h"
#include "Engine/GameInstance.h"
#include "Engine/GameViewportClient.h"
#include "Engine/LocalPlayer.h"
#include "Engine/World.h"
#include "GameFramework/Pawn.h"
#include "GameFramework/PlayerController.h"
#include "ImageUtils.h"
#include "IImageWrapperModule.h"
#include "Misc/Paths.h"
#include "Misc/ScopeLock.h"
#include "Modules/ModuleManager.h"
#include "RenderingThread.h"
#include "RHIGPUReadback.h"
#include "RHIResources.h"
#include "RHISurfaceDataConversion.h"
#include "SceneInterface.h"
#include "SceneView.h"
#include "SceneViewExtension.h"
#include "Serialization/JsonSerializer.h"
#include "Settings/LevelEditorPlaySettings.h"
#include "Slate/SceneViewport.h"
#include "UObject/Package.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/UObjectGlobals.h"
#include "Widgets/SViewport.h"
#if PLATFORM_WINDOWS && PLATFORM_64BITS
#include "Windows/WindowsHWrapper.h"
#endif

namespace GGYGOViewportReadback
{
	FString NativeFrame()
	{
		return FString::Printf(TEXT("%llu"), GFrameCounter);
	}
}

/** 每个像素任务独占；RT只管staging，后台只管自有CPU数据，均不解引用UObject或原viewport。 */
struct FGGYGOViewportPixelReadbackState
{
	FCriticalSection Mutex;
	TAtomic<bool> bCancelled{false};
	TAtomic<bool> bRenderPending{false};
	TAtomic<bool> bRenderReleased{true};
	TAtomic<bool> bCleanupPending{false};
	TUniquePtr<FRHIGPUTextureReadback> Readback; // 仅RT创建、映射和销毁。
	FGraphEventRef Worker;
	bool bWorkerQueued = false;
	bool bCopyQueued = false;
	bool bCpuReady = false;
	bool bEncoded = false;
	bool bFileWritten = false;
	bool bFileVerified = false;
	bool bFileHandleReleased = true;
	bool bCloseMeasured = false;
	bool bConvertedMeasured = false;
	bool bEncodedMeasured = false;
	bool bWriteMeasured = false;
	bool bVerifyMeasured = false;
	FIntPoint Size = FIntPoint::ZeroValue;
	EPixelFormat Format = PF_Unknown;
	FString OutputPath;
	int32 MaxPngBytes = 0; // 在 GT 建立任务时设定，随后由后台只读。
	FString Error;
	int64 FileSize = 0;
	TArray<uint8> EncodedBytes; // 仅兼容bytes模式；ToFile不向GT传PNG数组。
	double CopySubmitSeconds = 0;
	double ReadyObservedDelaySeconds = 0;
	double MapCopySeconds = 0;
	double ConvertSeconds = 0;
	double EncodeSeconds = 0;
	double WriteSeconds = 0;
	double VerifySeconds = 0;
	double CloseSeconds = 0;

	void SetError(const FString& Value)
	{
		FScopeLock Lock(&Mutex);
		if (Error.IsEmpty()) { Error = Value; }
	}
};

namespace GGYGOViewportReadback
{
	using FPixelState = TSharedPtr<FGGYGOViewportPixelReadbackState, ESPMode::ThreadSafe>;
	// 诊断资源预算，拒绝巨幅表面；不改变游戏分辨率，也不偷换其它表面。
	constexpr int64 MaxRawReadbackBytes = 256LL * 1024 * 1024;

	void WritePngExclusive(const FPixelState& State, const TArray64<uint8>& Png)
	{
#if PLATFORM_WINDOWS && PLATFORM_64BITS
		if (State->bCancelled.Load()) { return; }
		if (State->MaxPngBytes > 0 && Png.Num() > State->MaxPngBytes)
		{
			State->SetError(FString::Printf(TEXT("PngByteLimitExceeded: EncodedBytes=%lld MaxPngBytes=%d"),
				Png.Num(), State->MaxPngBytes));
			return;
		}
		const double WriteStart = FPlatformTime::Seconds();
		HANDLE Handle = ::CreateFileW(*State->OutputPath, GENERIC_READ | GENERIC_WRITE, 0, nullptr,
			CREATE_NEW, FILE_ATTRIBUTE_NORMAL, nullptr);
		if (Handle == INVALID_HANDLE_VALUE)
		{
			const DWORD Error = ::GetLastError();
			{
				FScopeLock Lock(&State->Mutex);
				State->WriteSeconds = FPlatformTime::Seconds() - WriteStart;
				State->bWriteMeasured = true;
			}
			State->SetError(FString::Printf(TEXT("Win64 CREATE_NEW失败，错误%u；不覆盖文件或创建目录。"), Error));
			return;
		}
		{
			FScopeLock Lock(&State->Mutex);
			State->bFileHandleReleased = false;
		}
		// 独占原句柄一经创建，所有路径都走下面唯一Close；取消不删除本次实际部分文件。
		int64 Offset = 0;
		DWORD IoError = ERROR_SUCCESS;
		FString IoStage;
		bool bWriteOK = true;
		while (Offset < Png.Num() && !State->bCancelled.Load())
		{
			const DWORD Want = static_cast<DWORD>(FMath::Min<int64>(Png.Num() - Offset, 64 * 1024));
			DWORD Done = 0;
			const bool bWritten = ::WriteFile(Handle, Png.GetData() + Offset, Want, &Done, nullptr) != 0;
			if (!bWritten || Done == 0)
			{
				IoError = bWritten ? ERROR_WRITE_FAULT : ::GetLastError();
				IoStage = TEXT("WriteFile");
				bWriteOK = false;
				break;
			}
			Offset += Done;
		}
		bWriteOK = bWriteOK && Offset == Png.Num();
		{
			FScopeLock Lock(&State->Mutex);
			State->WriteSeconds = FPlatformTime::Seconds() - WriteStart;
			State->bWriteMeasured = true;
		}

		const double VerifyStart = FPlatformTime::Seconds();
		LARGE_INTEGER ActualSize{}, Begin{};
		const bool bSizeKnown = ::GetFileSizeEx(Handle, &ActualSize) != 0;
		if (!bSizeKnown) { IoError = ::GetLastError(); IoStage = TEXT("GetFileSizeEx"); }
		bool bVerified = false;
		if (bWriteOK && !State->bCancelled.Load() && bSizeKnown && ActualSize.QuadPart == Png.Num()
			&& ::SetFilePointerEx(Handle, Begin, nullptr, FILE_BEGIN))
		{
			TArray<uint8> Chunk;
			Chunk.SetNumUninitialized(64 * 1024);
			Offset = 0;
			bVerified = true;
			while (Offset < Png.Num() && !State->bCancelled.Load())
			{
				const DWORD Want = static_cast<DWORD>(FMath::Min<int64>(Png.Num() - Offset, Chunk.Num()));
				DWORD Done = 0;
				const bool bRead = ::ReadFile(Handle, Chunk.GetData(), Want, &Done, nullptr) != 0;
				if (!bRead || Done == 0)
				{
					IoError = bRead ? ERROR_HANDLE_EOF : ::GetLastError();
					IoStage = TEXT("ReadFile");
					bVerified = false;
					break;
				}
				if (FMemory::Memcmp(Chunk.GetData(), Png.GetData() + Offset, Done) != 0)
				{
					IoError = ERROR_CRC;
					IoStage = TEXT("CompareBeforeClose");
					bVerified = false;
					break;
				}
				Offset += Done;
			}
			bVerified = bVerified && Offset == Png.Num();
		}
		else if (bWriteOK && !State->bCancelled.Load() && bSizeKnown)
		{
			IoStage = ActualSize.QuadPart == Png.Num() ? TEXT("SetFilePointerEx") : TEXT("SizeBeforeClose");
			IoError = ActualSize.QuadPart == Png.Num() ? ::GetLastError() : ERROR_INVALID_DATA;
		}
		const double VerifySeconds = FPlatformTime::Seconds() - VerifyStart;
		const double CloseStart = FPlatformTime::Seconds();
		const bool bClosed = ::CloseHandle(Handle) != 0;
		const DWORD CloseError = bClosed ? ERROR_SUCCESS : ::GetLastError();
		{
			FScopeLock Lock(&State->Mutex);
			State->CloseSeconds = FPlatformTime::Seconds() - CloseStart;
			State->bCloseMeasured = true;
			State->bFileHandleReleased = bClosed;
			State->bFileWritten = bWriteOK && bClosed;
			State->bFileVerified = bVerified; // 明确是同一独占句柄内、关闭前的字节验证。
			State->VerifySeconds = VerifySeconds;
			State->bVerifyMeasured = true;
			State->FileSize = bSizeKnown ? ActualSize.QuadPart : 0;
			State->bEncoded = true;
		}
		if (!bClosed) { State->SetError(FString::Printf(TEXT("原PNG句柄关闭失败，错误%u；不能签资源归还。"), CloseError)); }
		else if (!bWriteOK || !bVerified)
		{
			State->SetError(State->bCancelled.Load() ? TEXT("PNG任务被取消，原句柄已关闭；保留本次实际文件。")
				: FString::Printf(TEXT("PNG写入或关闭前验证未完成，阶段%s，错误%u；保留本次实际文件。"), *IoStage, IoError));
		}
#else
		State->SetError(TEXT("新ToFile排他创建仅支持Win64；其它平台不退回非排他写入。"));
#endif
	}

	void EncodeAndWrite(const FPixelState& State, TArray64<uint8>& Raw)
	{
		if (IsInGameThread()) { State->SetError(TEXT("任务执行器未提供后台线程，拒绝在GT编码/写盘。")); return; }
		if (State->bCancelled.Load()) { return; }
		TArray64<FColor> Colors;
		Colors.SetNumUninitialized(static_cast<int64>(State->Size.X) * State->Size.Y);
		const double ConvertStart = FPlatformTime::Seconds();
		const uint32 Pitch = static_cast<uint32>(State->Size.X) * sizeof(FColor);
		switch (State->Format)
		{
		case PF_B8G8R8A8:
			ConvertRawB8G8R8A8DataToFColor(State->Size.X, State->Size.Y, Raw.GetData(), Pitch, Colors.GetData());
			break;
		case PF_R8G8B8A8:
			ConvertRawR8G8B8A8DataToFColor(State->Size.X, State->Size.Y, Raw.GetData(), Pitch, Colors.GetData());
			break;
		case PF_A2B10G10R10:
			ConvertRawR10G10B10A2DataToFColor(State->Size.X, State->Size.Y, Raw.GetData(), Pitch, Colors.GetData());
			break;
		default:
			State->SetError(TEXT("后台收到未获准的SDR像素格式。"));
			return;
		}
		for (FColor& Color : Colors) { Color.A = 255; }
		{
			FScopeLock Lock(&State->Mutex);
			State->ConvertSeconds = FPlatformTime::Seconds() - ConvertStart;
			State->bConvertedMeasured = true;
		}
		Raw.Empty();
		if (State->bCancelled.Load()) { return; }
		TArray64<uint8> Png;
		const double EncodeStart = FPlatformTime::Seconds();
		FImageUtils::PNGCompressImageArray(State->Size.X, State->Size.Y,
			TArrayView64<const FColor>(Colors.GetData(), Colors.Num()), Png);
		{
			FScopeLock Lock(&State->Mutex);
			State->EncodeSeconds = FPlatformTime::Seconds() - EncodeStart;
			State->bEncodedMeasured = true;
		}
		Colors.Empty();
		if (Png.IsEmpty() || Png.Num() > MAX_int32)
		{
			State->SetError(TEXT("后台PNG编码为空或超出原bytes接口容量。"));
			return;
		}
		if (State->bCancelled.Load()) { return; }
		if (State->OutputPath.IsEmpty())
		{
			TArray<uint8> Encoded;
			Encoded.Append(Png.GetData(), static_cast<int32>(Png.Num()));
			FScopeLock Lock(&State->Mutex);
			State->EncodedBytes = MoveTemp(Encoded);
			State->bEncoded = true;
			return;
		}

		WritePngExclusive(State, Png);
	}

	void QueuePixelCleanup(const FPixelState& State)
	{
		if ((State->bRenderReleased.Load() && !State->bRenderPending.Load()) || State->bCleanupPending.Exchange(true)) { return; }
		ENQUEUE_RENDER_COMMAND(GGYGOViewportReleaseStaging)([State](FRHICommandListImmediate&)
		{
			State->Readback.Reset();
			State->bRenderReleased.Store(true);
			State->bCleanupPending.Store(false);
		});
	}

	void QueuePixelPoll(const FPixelState& State)
	{
		if (State->bCancelled.Load()) { QueuePixelCleanup(State); return; }
		if (State->bRenderReleased.Load() || State->bRenderPending.Exchange(true)) { return; }
		ENQUEUE_RENDER_COMMAND(GGYGOViewportPollStaging)([State](FRHICommandListImmediate&)
		{
			if (IsInGameThread())
			{
				State->SetError(TEXT("渲染线程已停止，拒绝在GT映射像素。"));
				State->Readback.Reset();
				State->bRenderReleased.Store(true);
				State->bRenderPending.Store(false);
				return;
			}
			if (State->bCancelled.Load())
			{
				State->Readback.Reset();
				State->bRenderReleased.Store(true);
				State->bRenderPending.Store(false);
				return;
			}
			if (!State->Readback)
			{
				State->SetError(TEXT("原GPU staging对象丢失。"));
				State->bRenderReleased.Store(true);
				State->bRenderPending.Store(false);
				return;
			}
			if (!State->Readback->IsReady()) { State->bRenderPending.Store(false); return; }
			const double MapStart = FPlatformTime::Seconds();
			int32 RowPitch = 0, BufferHeight = 0;
			void* Mapped = State->Readback->Lock(RowPitch, &BufferHeight);
			if (!Mapped || RowPitch < State->Size.X || BufferHeight < State->Size.Y)
			{
				if (Mapped) { State->Readback->Unlock(); }
				State->SetError(TEXT("就绪staging映射为空或row pitch/高度不足。"));
				State->Readback.Reset();
				State->bRenderReleased.Store(true);
				State->bRenderPending.Store(false);
				return;
			}
			TArray64<uint8> Raw;
			const int64 RowBytes = static_cast<int64>(State->Size.X) * sizeof(FColor);
			Raw.SetNumUninitialized(RowBytes * State->Size.Y);
			for (int32 Y = 0; Y < State->Size.Y; ++Y)
			{
				FMemory::Memcpy(Raw.GetData() + Y * RowBytes,
					static_cast<uint8*>(Mapped) + static_cast<int64>(Y) * RowPitch * sizeof(FColor), RowBytes);
			}
			State->Readback->Unlock();
			State->Readback.Reset();
			State->bRenderReleased.Store(true);
			{
				FScopeLock Lock(&State->Mutex);
				State->MapCopySeconds = FPlatformTime::Seconds() - MapStart;
				State->ReadyObservedDelaySeconds = MapStart - State->CopySubmitSeconds;
				State->bCpuReady = true;
				State->bWorkerQueued = true;
			}
			// 调度到现有引擎后台任务执行器；GT只轮询图事件完成，不Wait，不创建帧调度器。
			FGraphEventRef Worker = FFunctionGraphTask::CreateAndDispatchWhenReady(
				[State, Raw = MoveTemp(Raw)]() mutable { EncodeAndWrite(State, Raw); },
				TStatId(), nullptr, ENamedThreads::AnyBackgroundThreadNormalTask);
			{
				FScopeLock Lock(&State->Mutex);
				State->Worker = Worker;
			}
			State->bRenderPending.Store(false);
		});
	}
}

/** 只属于这次 Editor 观察；运行时相机仍是唯一确认与 POV 写端。 */
struct FGGYGOPlayerViewObservationState
{
	TWeakObjectPtr<UWorld> EditorWorld;
	TWeakObjectPtr<UGameInstance> Instance;
	TWeakObjectPtr<ULocalPlayer> Player;
	TWeakObjectPtr<UClass> ModeClass;
	TWeakObjectPtr<APlayerController> Controller;
	TWeakObjectPtr<AGGYGOPlayerCameraManager> Manager;
	TWeakObjectPtr<APawn> Pawn;
	TWeakObjectPtr<UGGYGOCameraComponent> Camera;
	TSharedPtr<ISceneViewExtension, ESPMode::ThreadSafe> Extension;
	FDelegateHandle BeginDrawHandle;
	FDelegateHandle EndDrawHandle;
	FDelegateHandle MapReadyHandle;
	FDelegateHandle PlayerAddedHandle;
	FDelegateHandle ViewportCreatedHandle;
	FDelegateHandle CancelPIEHandle;
	TSharedPtr<FJsonObject> Source = MakeShared<FJsonObject>();
	TSharedPtr<FJsonObject> Startup = MakeShared<FJsonObject>();
	TSharedPtr<FJsonObject> FirstDraw;
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
	bool bBeforePIE = false;
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

UGGYGOViewportReadbackTask* UGGYGOViewportReadbackLibrary::BeginGameViewportReadbackToFile(
	UWorld* ExpectedWorld, const FString& AbsolutePngPath, int32 MaxPngBytes)
{
	check(IsInGameThread());
	UGGYGOViewportReadbackTask* Task = NewObject<UGGYGOViewportReadbackTask>(GetTransientPackage(), NAME_None, RF_Transient);
	if (AbsolutePngPath.IsEmpty() || MaxPngBytes < 0)
	{
		Task->Result.Status = EGGYGOViewportReadbackStatus::Pending;
		Task->Fail(AbsolutePngPath.IsEmpty() ? TEXT("ToFile必须明确绝对PNG输出路径。")
			: TEXT("ToFile MaxPngBytes 须为非负字节数。"));
		return Task;
	}
	Task->Initialize(ExpectedWorld, true, AbsolutePngPath, MaxPngBytes);
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

UGGYGOViewportReadbackTask* UGGYGOViewportReadbackLibrary::BeginNextPIEPlayerViewObservation(UWorld* ExpectedEditorWorld,
	TSubclassOf<UGGYGOCameraMode> ExpectedMode, int32 MaxDraws)
{
	check(IsInGameThread());
	UGGYGOViewportReadbackTask* Task = NewObject<UGGYGOViewportReadbackTask>(GetTransientPackage(), NAME_None, RF_Transient);
	Task->InitializeBeforePIE(ExpectedEditorWorld, ExpectedMode, MaxDraws);
	return Task;
}

void UGGYGOViewportReadbackTask::Initialize(UWorld* ExpectedWorld, bool bReadPixels, const FString& AbsolutePngPath,
	int32 MaxPngBytes)
{
	Result.bPlayerViewOnly = !bReadPixels;
	Result.Status = EGGYGOViewportReadbackStatus::Pending;
	Result.Error.Reset();
	Result.RequestFrame = GGYGOViewportReadback::NativeFrame();
	Result.WorldPath = GetPathNameSafe(ExpectedWorld);
	if (bReadPixels)
	{
		// 标准Editor应已预载；不在动作切点LoadModule，也绝不让后台线程触发模块加载。
		if (!FModuleManager::GetModulePtr<IImageWrapperModule>(TEXT("ImageWrapper")))
		{
			Fail(TEXT("ImageWrapper尚未在GT预载；须在启动阶段准备，不在捕获切点同步加载。"));
			return;
		}
		PixelReadback = MakeShared<FGGYGOViewportPixelReadbackState, ESPMode::ThreadSafe>();
		if (!AbsolutePngPath.IsEmpty())
		{
#if !(PLATFORM_WINDOWS && PLATFORM_64BITS)
			Fail(TEXT("新ToFile排他创建仅支持Win64；旧bytes入口不受此限制。"));
			return;
#endif
			FString Output = AbsolutePngPath;
			FPaths::NormalizeFilename(Output);
			if (FPaths::IsRelative(Output) || !FPaths::CollapseRelativeDirectories(Output)
				|| !FPaths::GetExtension(Output).Equals(TEXT("png"), ESearchCase::IgnoreCase))
			{
				Fail(FString::Printf(TEXT("ToFile目标无效：%s；须明确绝对PNG路径。"), *Output));
				return;
			}
			Result.OutputFilePath = Output;
			PixelReadback->OutputPath = Output;
			PixelReadback->MaxPngBytes = MaxPngBytes;
		}
	}
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
	RegisterPlayerViewCallbacks();
}

void UGGYGOViewportReadbackTask::InitializeBeforePIE(UWorld* ExpectedEditorWorld,
	TSubclassOf<UGGYGOCameraMode> ExpectedMode, int32 MaxDraws)
{
	Result.bPlayerViewOnly = true;
	Result.Status = EGGYGOViewportReadbackStatus::Pending;
	Result.Error.Reset();
	Result.RequestFrame = GGYGOViewportReadback::NativeFrame();
	if (!GEditor || !GEngine || !IsValid(ExpectedEditorWorld) || ExpectedEditorWorld->WorldType != EWorldType::Editor
		|| GEditor->GetEditorWorldContext().World() != ExpectedEditorWorld || !ExpectedMode || MaxDraws < 1 || MaxDraws > 4096)
	{
		Fail(TEXT("预布防需要当前原编辑器地图、精确模式类及 1..4096 的自然 Draw 上限。"));
		return;
	}
	for (const FWorldContext& Context : GEngine->GetWorldContexts())
	{
		if (Context.WorldType == EWorldType::PIE)
		{
			Fail(TEXT("已有 PIE WorldContext，不能认证下一次请求的首 Draw。"));
			return;
		}
	}
	const ULevelEditorPlaySettings* Settings = GetDefault<ULevelEditorPlaySettings>();
	EPlayNetMode NetMode;
	int32 Clients;
	bool bOneProcess;
	// 这些 getter 的返回值描述选项是否启用；Out 参数才是原配置值。
	Settings->GetPlayNetMode(NetMode);
	Settings->GetPlayNumberOfClients(Clients);
	Settings->GetRunUnderOneProcess(bOneProcess);
	if (GEditor->PlayWorld || GEditor->GetPlaySessionRequest().IsSet() || GEditor->IsSimulateInEditorInProgress() || NetMode != PIE_Standalone
		|| Clients != 1 || !bOneProcess || Settings->bLaunchSeparateServer)
	{
		Fail(TEXT("首 Draw 预布防只接受未开始的单客户端、同进程 Standalone PIE。"));
		return;
	}
	PlayerView = MakeShared<FGGYGOPlayerViewObservationState>();
	PlayerView->bBeforePIE = true;
	PlayerView->EditorWorld = ExpectedEditorWorld;
	PlayerView->ModeClass = ExpectedMode.Get();
	PlayerView->MaxDraws = MaxDraws;
	PlayerView->Source->SetStringField(TEXT("expected_mode_class"), ExpectedMode->GetPathName());
	PlayerView->Startup->SetStringField(TEXT("editor_world"), ExpectedEditorWorld->GetPathName());
	PlayerView->Startup->SetStringField(TEXT("editor_world_id"), LexToString(ExpectedEditorWorld->GetUniqueID()));
	PlayerView->Startup->SetStringField(TEXT("armed_frame"), Result.RequestFrame);
	PlayerView->MapReadyHandle = FWorldDelegates::OnPIEMapReady.AddUObject(this, &ThisClass::OnPIEMapReady);
	PlayerView->ViewportCreatedHandle = UGameViewportClient::OnViewportCreated().AddUObject(this, &ThisClass::OnInitialViewportCreated);
	PlayerView->CancelPIEHandle = FEditorDelegates::CancelPIE.AddUObject(this, &ThisClass::OnCancelPIE);
	WorldCleanupHandle = FWorldDelegates::OnWorldCleanup.AddUObject(this, &ThisClass::OnWorldCleanup);
	EndPIEHandle = FEditorDelegates::EndPIE.AddUObject(this, &ThisClass::OnEndPIE);
}

void UGGYGOViewportReadbackTask::OnPIEMapReady(UGameInstance* Instance)
{
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending) { return; }
	UWorld* EditorWorld = PlayerView->EditorWorld.Get();
	UWorld* World = IsValid(Instance) ? Instance->GetWorld() : nullptr;
	const FWorldContext* Context = IsValid(World) && GEngine ? GEngine->GetWorldContextFromWorld(World) : nullptr;
	int32 PIEContexts = 0;
	if (GEngine)
	{
		for (const FWorldContext& Item : GEngine->GetWorldContexts()) { PIEContexts += Item.WorldType == EWorldType::PIE ? 1 : 0; }
	}
	if (!PlayerView->Instance.IsExplicitlyNull() || !IsValid(EditorWorld) || !IsValid(World) || !Context
		|| World->WorldType != EWorldType::PIE || World->GetNetMode() != NM_Standalone || PIEContexts != 1
		|| World->GetGameInstance() != Instance || Instance->GetLocalPlayers().Num() != 0 || Instance->GetGameViewportClient()
		|| UWorld::RemovePIEPrefix(World->GetOutermost()->GetName()) != EditorWorld->GetOutermost()->GetName())
	{
		Fail(TEXT("PIE MapReady 的原地图、唯一 GI/WorldContext 或尚未创建玩家/viewport 的启动顺序不成立。"));
		return;
	}
	PlayerView->Instance = Instance;
	OriginalWorld = World;
	Result.WorldPath = World->GetPathName();
	Result.WorldObjectId = LexToString(World->GetUniqueID());
	Result.WorldContextHandle = Context->ContextHandle;
	Result.PIEInstance = Context->PIEInstance;
	Result.WorldType = static_cast<uint8>(World->WorldType);
	Result.NetMode = static_cast<uint8>(World->GetNetMode());
	PlayerView->Startup->SetStringField(TEXT("map_ready_frame"), GGYGOViewportReadback::NativeFrame());
	PlayerView->Startup->SetStringField(TEXT("game_instance"), Instance->GetPathName());
	PlayerView->Startup->SetStringField(TEXT("game_instance_id"), LexToString(Instance->GetUniqueID()));
	PlayerView->PlayerAddedHandle = Instance->OnLocalPlayerAddedEvent.AddUObject(this, &ThisClass::OnLocalPlayerAdded);
}

void UGGYGOViewportReadbackTask::OnLocalPlayerAdded(ULocalPlayer* Player)
{
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending) { return; }
	UGameInstance* Instance = PlayerView->Instance.Get();
	UWorld* World = OriginalWorld.Get();
	UGameViewportClient* Client = IsValid(Instance) ? Instance->GetGameViewportClient() : nullptr;
	if (!PlayerView->Player.IsExplicitlyNull() || !IsValid(Instance) || !IsValid(Player) || !IsValid(World)
		|| !IsValid(Client) || Instance->GetWorld() != World || Instance->GetLocalPlayers().Num() != 1
		|| Instance->GetLocalPlayers()[0] != Player || Player->GetWorld() != World || Client->GetWorld() != World
		|| Player->ViewportClient != Client || Client->GetGameViewport())
	{
		Fail(TEXT("LocalPlayerAdded 不是原 GI 的唯一玩家/client，或游戏 viewport 已存在而无法证明首 Draw。"));
		return;
	}
	PlayerView->Player = Player;
	OriginalClient = Client;
	Result.GameViewportClientPath = Client->GetPathName();
	Result.GameViewportClientObjectId = LexToString(Client->GetUniqueID());
	PlayerView->Source->SetStringField(TEXT("local_player"), Player->GetPathName());
	PlayerView->Source->SetStringField(TEXT("local_player_id"), LexToString(Player->GetUniqueID()));
	PlayerView->Startup->SetStringField(TEXT("local_player_added_frame"), GGYGOViewportReadback::NativeFrame());
	CloseHandle = Client->OnCloseRequested().AddUObject(this, &ThisClass::OnViewportCloseRequested);
	RegisterPlayerViewCallbacks();
}

bool UGGYGOViewportReadbackTask::CaptureInitialViewport(FString& OutError)
{
	TSharedPtr<ISlateViewport> Interface;
	if (!OriginalViewport)
	{
		UGameViewportClient* Client = OriginalClient.Get();
		UWorld* World = OriginalWorld.Get();
		if (!IsValid(Client) || !IsValid(World) || Client->GetWorld() != World || World->GetGameViewport() != Client)
		{
			OutError = TEXT("原启动 client/World 尚未关联或已退役。");
			return false;
		}
		const TSharedPtr<SViewport> Widget = Client->GetGameViewportWidget();
		Interface = Widget ? Widget->GetViewportInterface().Pin() : nullptr;
		FSceneViewport* Viewport = Client->GetGameViewport();
		if (!Widget || !Interface || !Viewport || Interface.Get() != static_cast<ISlateViewport*>(Viewport))
		{
			OutError = TEXT("原 client 的首个 viewport/widget/interface 尚未完整建立。");
			return false;
		}
		OriginalViewport = Viewport;
		OriginalWidget = Widget;
		OriginalInterface = Interface;
		Result.ViewportIdentity = FString::Printf(TEXT("%p"), static_cast<FViewport*>(Viewport));
		PlayerView->Startup->SetStringField(TEXT("viewport_bound_frame"), GGYGOViewportReadback::NativeFrame());
	}
	return PinOriginalViewport(Interface, OutError);
}

void UGGYGOViewportReadbackTask::OnInitialViewportCreated()
{
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending) { return; }
	FString Error;
	if (!CaptureInitialViewport(Error)) { Fail(Error); return; }
	PlayerView->Startup->SetStringField(TEXT("viewport_created_frame"), GGYGOViewportReadback::NativeFrame());
}

void UGGYGOViewportReadbackTask::OnCancelPIE()
{
	Fail(TEXT("原 PIE 启动请求取消，首 Draw 观察未完成。"));
}

void UGGYGOViewportReadbackTask::RegisterPlayerViewCallbacks()
{
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
	if (PlayerView->bDrawOpen) { Fail(TEXT("原玩家 Draw 重入，不能合并两次自然绘制。")); return; }
	PlayerView->bDrawOpen = true;
	++PlayerView->DrawCount;
	PlayerView->LastDraw = MakeShared<FJsonObject>();
	PlayerView->LastDraw->SetStringField(TEXT("begin_frame"), GGYGOViewportReadback::NativeFrame());
	PlayerView->LastDraw->SetNumberField(TEXT("draw_ordinal"), PlayerView->DrawCount);
	if (PlayerView->DrawCount == 1) { PlayerView->FirstDraw = PlayerView->LastDraw; }
	TSharedPtr<ISlateViewport> Interface;
	bool bReady;
	FString Error;
	// 有的原生窗口在 OnViewportCreated 广播前就开始 Draw；同一原 client 的首次固定仍在
	// BeginDraw 的实际回调内完成，早于引擎 GatherActiveExtensions，不重放或补造 BeginDraw。
	if (PlayerView->bBeforePIE && !CaptureInitialViewport(Error)) { Fail(Error); return; }
	if (!PinOriginalViewport(Interface, Error) || !PinOriginalPlayer(Error, bReady)) { Fail(Error); return; }
	PlayerView->LastDraw->SetBoolField(TEXT("original_scope_verified"), true);
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
	if (!PlayerView->bDrawOpen) { Fail(TEXT("原 EndDraw 没有对应的自然 BeginDraw。")); return; }
	TSharedPtr<ISlateViewport> Interface;
	bool bReady;
	FString Error;
	if (!PinOriginalViewport(Interface, Error) || !PinOriginalPlayer(Error, bReady)) { Fail(Error); return; }
	PlayerView->LastDraw->SetStringField(TEXT("end_frame"), GGYGOViewportReadback::NativeFrame());
	PlayerView->bDrawOpen = false;
	if (PlayerView->Projection.IsValid())
	{
		if (!bReady) { Fail(TEXT("匹配 SetupView 后原玩家在 EndDraw 前已退役。")); return; }
		Result.ReadbackCompleteFrame = GGYGOViewportReadback::NativeFrame();
		Result.Status = EGGYGOViewportReadbackStatus::Complete;
		DetachCallbacks();
		return;
	}
	if (PlayerView->DrawCount >= PlayerView->MaxDraws)
	{
		Fail(TEXT("自然 Draw 已到明确上限，尚未取得原玩家完整投影成功后的匹配 SetupView。"));
	}
}

void UGGYGOViewportReadbackTask::OnPlayerViewSetup(FSceneViewFamily& ViewFamily, FSceneView& View)
{
	check(IsInGameThread());
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending || !PlayerView.IsValid()
		|| PlayerView->Projection.IsValid()
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
	PlayerView->Projection->SetNumberField(TEXT("draw_ordinal"), PlayerView->DrawCount);
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
}

void UGGYGOViewportReadbackTask::UpdatePlayerViewJson()
{
	if (!PlayerView.IsValid()) { return; }
	auto Json = MakeShared<FJsonObject>();
	Json->SetStringField(TEXT("schema"), TEXT("GGYGO.PlayerViewObservation/v1"));
	Json->SetStringField(TEXT("meaning"), TEXT("首个自然 Draw 与首个匹配成功 SetupView 分列；预布防模式从原 PIE 创建链见证首 Draw，确认位精确写入时刻未观察。"));
	Json->SetObjectField(TEXT("original_player"), PlayerView->Source);
	Json->SetObjectField(TEXT("startup"), PlayerView->Startup);
	if (PlayerView->FirstDraw.IsValid()) { Json->SetObjectField(TEXT("first_draw"), PlayerView->FirstDraw); }
	Json->SetObjectField(TEXT("last_draw"), PlayerView->LastDraw);
	if (PlayerView->Projection.IsValid()) { Json->SetObjectField(TEXT("projection"), PlayerView->Projection); }
	Json->SetBoolField(TEXT("arm_confirmation_known"), PlayerView->bArmConfirmationKnown);
	Json->SetBoolField(TEXT("confirmed_at_arm"), PlayerView->bConfirmedAtArm);
	Json->SetBoolField(TEXT("unconfirmed_state_observed"), PlayerView->bSawUnconfirmed);
	Json->SetBoolField(TEXT("first_confirmation_write_observed"), false);
	Json->SetBoolField(TEXT("prearmed_before_pie"), PlayerView->bBeforePIE);
	bool bFirstScopeVerified = false;
	if (PlayerView->FirstDraw.IsValid()) { PlayerView->FirstDraw->TryGetBoolField(TEXT("original_scope_verified"), bFirstScopeVerified); }
	Json->SetBoolField(TEXT("first_natural_draw_proven"), PlayerView->bBeforePIE && bFirstScopeVerified
		&& PlayerView->FirstDraw->HasTypedField<EJson::String>(TEXT("end_frame")));
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
	if (Result.Status != EGGYGOViewportReadbackStatus::Pending) { return; }
	TSharedPtr<ISlateViewport> Interface;
	FString Error;
	if (!PinOriginalViewport(Interface, Error)) { Fail(Error); return; }
	if (Viewport != static_cast<FViewport*>(OriginalViewport)) { return; }
	if (!GIsThreadedRendering) { Fail(TEXT("异步像素读回需要活动渲染线程，不同步退回GT。")); return; }
	const FIntPoint Size = Viewport->GetRenderTargetTextureSizeXY();
	const FTextureRHIRef Surface = Viewport->GetShaderResourceTexture();
	Result.RenderTargetSize = Size;
	Result.bHDR = Viewport->GetSceneHDREnabled();
	if (!Surface.IsValid() || Size.X <= 0 || Size.Y <= 0
		|| static_cast<int64>(Size.X) * Size.Y * sizeof(FColor) > GGYGOViewportReadback::MaxRawReadbackBytes)
	{
		Fail(TEXT("原表面为空或超过256MiB单任务像素预算。"));
		return;
	}
	EPixelFormat Format;
	{
		const FRHITextureDesc& Desc = Surface->GetDesc();
		Format = Desc.Format;
		if (Result.bHDR || Desc.Dimension != ETextureDimension::Texture2D || Desc.ArraySize != 1
			|| Desc.NumSamples != 1 || Desc.Extent != Size
			|| (Format != PF_B8G8R8A8 && Format != PF_R8G8B8A8 && Format != PF_A2B10G10R10))
		{
			Fail(TEXT("仅支持明确的单层单采样SDR BGRA8/RGBA8/R10G10B10A2原表面。"));
			return;
		}
	}
	check(PixelReadback.IsValid());
	Result.RenderTargetFormat = static_cast<int32>(Format);
	Result.RenderCallbackFrame = GGYGOViewportReadback::NativeFrame();
	Result.Status = EGGYGOViewportReadbackStatus::Reading;
	UGameViewportClient::OnViewportRendered().Remove(RenderedHandle);
	RenderedHandle.Reset();
	const auto State = PixelReadback;
	State->Size = Size;
	State->Format = Format;
	State->bRenderReleased.Store(false);
	State->bRenderPending.Store(true);
	ENQUEUE_RENDER_COMMAND(GGYGOViewportCopyToStaging)([State, Surface](FRHICommandListImmediate& RHICmdList)
	{
		if (IsInGameThread())
		{
			State->SetError(TEXT("捕获命令未进入RT，拒绝同步读回。"));
			State->bRenderReleased.Store(true);
			State->bRenderPending.Store(false);
			return;
		}
		if (State->bCancelled.Load())
		{
			State->bRenderReleased.Store(true);
			State->bRenderPending.Store(false);
			return;
		}
		State->Readback = MakeUnique<FRHIGPUTextureReadback>(FName(TEXT("GGYGOViewportReadback")));
		State->Readback->EnqueueCopy(RHICmdList, Surface.GetReference());
		{
			FScopeLock Lock(&State->Mutex);
			State->CopySubmitSeconds = FPlatformTime::Seconds();
			State->bCopyQueued = true;
		}
		State->bRenderPending.Store(false);
	});
}

void UGGYGOViewportReadbackTask::UpdateResourceReleaseState()
{
	bool bPixelReleased = true;
	if (PixelReadback.IsValid())
	{
		FScopeLock Lock(&PixelReadback->Mutex);
		bPixelReleased = PixelReadback->bRenderReleased.Load() && !PixelReadback->bRenderPending.Load()
			&& !PixelReadback->bCleanupPending.Load()
			&& PixelReadback->bFileHandleReleased
			&& (!PixelReadback->bWorkerQueued || (PixelReadback->Worker.IsValid() && PixelReadback->Worker->IsComplete()));
	}
	Result.bResourcesReleased = bPixelReleased && !RenderedHandle.IsValid() && !CloseHandle.IsValid()
		&& !WorldCleanupHandle.IsValid() && !EndPIEHandle.IsValid()
		&& (!PlayerView.IsValid() || PlayerView->bReleased);
}

void UGGYGOViewportReadbackTask::CancelPixelReadback()
{
	if (!PixelReadback.IsValid()) { return; }
	PixelReadback->bCancelled.Store(true);
	GGYGOViewportReadback::QueuePixelCleanup(PixelReadback);
}

void UGGYGOViewportReadbackTask::AdvancePixelReadback()
{
	if (!PixelReadback.IsValid()) { UpdateResourceReleaseState(); return; }
	const auto State = PixelReadback;
	if (State->bCancelled.Load()) { GGYGOViewportReadback::QueuePixelCleanup(State); }
	else if (Result.Status == EGGYGOViewportReadbackStatus::Reading) { GGYGOViewportReadback::QueuePixelPoll(State); }
	FString Error;
	bool bDone = false;
	TSharedRef<FJsonObject> Timings = MakeShared<FJsonObject>();
	Timings->SetStringField(TEXT("schema"), TEXT("GGYGO.ViewportPixelStages/v1"));
	Timings->SetStringField(TEXT("scope"), TEXT("RT/worker CPU段及ready观察延迟；不是GPU硬件计时；帧号只在GT观察并发布。"));
	{
		FScopeLock Lock(&State->Mutex);
		const bool bWorkerComplete = State->bWorkerQueued && State->Worker.IsValid() && State->Worker->IsComplete();
		Timings->SetBoolField(TEXT("copy_queued"), State->bCopyQueued);
		Timings->SetBoolField(TEXT("cpu_pixels_ready"), State->bCpuReady);
		Timings->SetBoolField(TEXT("worker_complete"), bWorkerComplete);
		Timings->SetBoolField(TEXT("file_handle_released"), State->bFileHandleReleased);
		if (!State->OutputPath.IsEmpty())
		{
			Timings->SetStringField(TEXT("file_verify_scope"), TEXT("same_exclusive_handle_before_close"));
		}
		if (State->bCopyQueued) { Timings->SetNumberField(TEXT("copy_submit_seconds"), State->CopySubmitSeconds); }
		if (State->bCpuReady)
		{
			Timings->SetNumberField(TEXT("ready_observed_delay_seconds"), State->ReadyObservedDelaySeconds);
			Timings->SetNumberField(TEXT("map_copy_seconds"), State->MapCopySeconds);
			if (Result.ReadbackCompleteFrame.IsEmpty()) { Result.ReadbackCompleteFrame = GGYGOViewportReadback::NativeFrame(); }
		}
		if (State->bConvertedMeasured) { Timings->SetNumberField(TEXT("pixel_conversion_seconds"), State->ConvertSeconds); }
		if (State->bEncodedMeasured) { Timings->SetNumberField(TEXT("png_encode_seconds"), State->EncodeSeconds); }
		if (State->bWriteMeasured) { Timings->SetNumberField(TEXT("file_write_seconds"), State->WriteSeconds); }
		if (State->bVerifyMeasured) { Timings->SetNumberField(TEXT("file_verify_seconds"), State->VerifySeconds); }
		if (State->bCloseMeasured) { Timings->SetNumberField(TEXT("file_close_seconds"), State->CloseSeconds); }
		Result.OutputFileSizeBytes = State->FileSize;
		Result.bFileWriteComplete = State->bFileWritten;
		Result.bFileReadbackVerified = State->bFileVerified;
		if (State->bFileWritten && Result.FileWriteCompleteObservedFrame.IsEmpty())
		{
			Result.FileWriteCompleteObservedFrame = GGYGOViewportReadback::NativeFrame();
		}
		Error = State->Error;
		bDone = bWorkerComplete && State->bEncoded && State->bRenderReleased.Load()
			&& !State->bRenderPending.Load() && !State->bCleanupPending.Load()
			&& State->bFileHandleReleased
			&& (State->OutputPath.IsEmpty() || (State->bFileWritten && State->bFileVerified));
		if (bDone && !State->bCancelled.Load() && Result.Status == EGGYGOViewportReadbackStatus::Reading && Error.IsEmpty())
		{
			Result.PngBytes = MoveTemp(State->EncodedBytes);
		}
	}
	FJsonSerializer::Serialize(Timings, TJsonWriterFactory<>::Create(&Result.StageTimingsJson));
	if (!Error.IsEmpty()) { Fail(Error); }
	if (bDone && !State->bCancelled.Load() && Result.Status == EGGYGOViewportReadbackStatus::Reading && Error.IsEmpty())
	{
		Result.Status = EGGYGOViewportReadbackStatus::Complete;
		DetachCallbacks();
	}
	UpdateResourceReleaseState();
}

FGGYGOViewportReadbackResult UGGYGOViewportReadbackTask::ReadResult()
{
	check(IsInGameThread());
	if (Result.Status == EGGYGOViewportReadbackStatus::Pending || Result.Status == EGGYGOViewportReadbackStatus::Reading)
	{
		if (PlayerView.IsValid() && PlayerView->bBeforePIE)
		{
			UGameInstance* Instance = PlayerView->Instance.Get();
			ULocalPlayer* Player = PlayerView->Player.Get();
			if (!PlayerView->EditorWorld.IsValid()
				|| (!PlayerView->Instance.IsExplicitlyNull() && (!IsValid(Instance) || !OriginalWorld.IsValid()
					|| Instance->GetWorld() != OriginalWorld.Get()))
				|| (!PlayerView->Player.IsExplicitlyNull() && (!IsValid(Player) || !IsValid(Instance)
					|| Instance->GetLocalPlayers().Num() != 1 || Instance->GetLocalPlayers()[0] != Player
					|| !OriginalClient.IsValid() || Player->ViewportClient != OriginalClient.Get()
					|| OriginalClient->GetWorld() != OriginalWorld.Get())))
			{
				Fail(TEXT("原 PIE 启动范围、GI 或唯一 LocalPlayer 已退役。"));
			}
			if (!OriginalViewport)
			{
				UpdatePlayerViewJson();
				return Result; // 只由原生创建/Draw 事件布防；读取不替宿主轮询建立 viewport。
			}
		}
		TSharedPtr<ISlateViewport> Interface;
		FString Error;
		if (!PinOriginalViewport(Interface, Error))
		{
			Fail(Error);
		}
	}
	AdvancePixelReadback();
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
	if (Result.Status != EGGYGOViewportReadbackStatus::Complete) { CancelPixelReadback(); }
	DetachCallbacks();
	UpdateResourceReleaseState();
}

void UGGYGOViewportReadbackTask::OnViewportCloseRequested(FViewport* Viewport)
{
	if (Viewport == static_cast<FViewport*>(OriginalViewport)
		|| (PlayerView.IsValid() && PlayerView->bBeforePIE && !OriginalViewport))
	{
		Fail(TEXT("原 viewport 请求关闭，读回未完成。"));
	}
}

void UGGYGOViewportReadbackTask::OnWorldCleanup(UWorld* World, bool bSessionEnded, bool bCleanupResources)
{
	if (World == OriginalWorld.Get() || (PlayerView.IsValid() && PlayerView->bBeforePIE && World == PlayerView->EditorWorld.Get()))
	{
		Fail(TEXT("原 World 正在清理，读回未完成。"));
	}
}

void UGGYGOViewportReadbackTask::OnEndPIE(bool bSimulating)
{
	if (Result.WorldType == static_cast<uint8>(EWorldType::PIE) || (PlayerView.IsValid() && PlayerView->bBeforePIE))
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
	CancelPixelReadback();
	DetachCallbacks();
	UpdateResourceReleaseState();
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
		if (PlayerView->MapReadyHandle.IsValid()) { FWorldDelegates::OnPIEMapReady.Remove(PlayerView->MapReadyHandle); }
		PlayerView->MapReadyHandle.Reset();
		if (UGameInstance* Instance = PlayerView->Instance.Get())
		{
			if (PlayerView->PlayerAddedHandle.IsValid()) { Instance->OnLocalPlayerAddedEvent.Remove(PlayerView->PlayerAddedHandle); }
		}
		PlayerView->PlayerAddedHandle.Reset();
		if (PlayerView->ViewportCreatedHandle.IsValid()) { UGameViewportClient::OnViewportCreated().Remove(PlayerView->ViewportCreatedHandle); }
		PlayerView->ViewportCreatedHandle.Reset();
		if (PlayerView->CancelPIEHandle.IsValid()) { FEditorDelegates::CancelPIE.Remove(PlayerView->CancelPIEHandle); }
		PlayerView->CancelPIEHandle.Reset();
		PlayerView->Instance.Reset();
		PlayerView->EditorWorld.Reset();
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
