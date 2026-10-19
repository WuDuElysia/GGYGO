/** @file GGYGOViewportReadbackLibrary.h @brief 原游戏 viewport 的 SDR PNG 与玩家自然成功投影的有限只读观察。 */
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GGYGOViewportReadbackLibrary.generated.h"

class FSceneViewport;
class FViewport;
class ISlateViewport;
class SViewport;
class UGameViewportClient;
class ULocalPlayer;
class UWorld;
class UGGYGOCameraMode;
class FSceneView;
class FSceneViewFamily;
struct FGGYGOPlayerViewObservationState;
struct FGGYGOPlayerViewExtension;

/** 状态只属于当前读回资源，不表示玩法、文件写入或视觉验收完成。 */
UENUM(BlueprintType)
enum class EGGYGOViewportReadbackStatus : uint8
{
	Pending,
	Reading,
	Complete,
	Failed,
	Cancelled
};

/** 同一请求的值记录；Complete 后保留到任务对象回收，不强持有原 World 或 viewport。 */
USTRUCT(BlueprintType)
struct FGGYGOViewportReadbackResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	EGGYGOViewportReadbackStatus Status = EGGYGOViewportReadbackStatus::Failed;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString WorldPath;
	/** 原生 UObject UniqueID 的十进制值，只在所属进程及本次请求范围解释。 */
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString WorldObjectId;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString GameViewportClientPath;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString GameViewportClientObjectId;
	/** 原生 FViewport 地址仅作本次请求的不透明身份；存活与换代另由原弱接口核验。 */
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString ViewportIdentity;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FName WorldContextHandle;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	int32 PIEInstance = INDEX_NONE;
	/** 原生 EWorldType::Type 与 ENetMode 的原值。 */
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	uint8 WorldType = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	uint8 NetMode = 0;
	/** 三个原生 GFrameCounter 分列；值观察的 RenderCallbackFrame 为 SetupView，不表示 GPU 完成。 */
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString RequestFrame;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString RenderCallbackFrame;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString ReadbackCompleteFrame;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FIntPoint RenderTargetSize = FIntPoint::ZeroValue;
	/** 原生读回表面的 EPixelFormat 原值；不是 PNG 的 RGBA8 编码类型。 */
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	int32 RenderTargetFormat = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	bool bHDR = false;
	/** 值观察模式不读像素；Complete 表示已捕获匹配的自然 SetupView。 */
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	bool bPlayerViewOnly = false;
	/** 当前有限玩家投影观察的纯值 JSON；不代表确认位精确写入时刻或 GPU 完成。 */
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString PlayerViewJson;
	/** 像素模式仅 Complete 有 PNG。RGB 沿原生 SDR ReadPixels，Alpha 置 255。 */
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	TArray<uint8> PngBytes;
	UPROPERTY(BlueprintReadOnly, Category = "Editor|Viewport")
	FString Error = TEXT("[Editor.ViewportReadback] 请求尚未初始化。");
};

/**
 * 调用方持有的单次原生读回资源。仅订阅匹配 viewport 的自然渲染事件；不驱动世界、相机或绘制。
 * 完成/失败/释放、原 World 清理、PIE 结束及对象销毁均归还自己的委托。调用方离开等待时应 Release。
 */
UCLASS(BlueprintType)
class GGYGOEDITOR_API UGGYGOViewportReadbackTask : public UObject
{
	GENERATED_BODY()

public:
	/** 当前结果的值复制。等待期间发现原身份退役时，结束本任务并给出失败；不访问后继资源。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Viewport")
	FGGYGOViewportReadbackResult ReadResult();

	/** 幂等归还自己的回调；未完成请求变为 Cancelled，既有终态及 PNG 值保持。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Viewport")
	void Release();

	virtual void BeginDestroy() override;

private:
	friend class UGGYGOViewportReadbackLibrary;
	friend struct FGGYGOPlayerViewExtension;
	void Initialize(UWorld* ExpectedWorld, bool bReadPixels = true);
	void InitializePlayerView(ULocalPlayer* ExpectedPlayer, TSubclassOf<UGGYGOCameraMode> ExpectedMode, int32 MaxDraws);
	bool PinOriginalPlayer(FString& OutError, bool& bOutReady);
	void OnPlayerDrawBegin();
	void OnPlayerDrawEnd();
	void OnPlayerViewSetup(FSceneViewFamily& ViewFamily, FSceneView& View);
	void UpdatePlayerViewJson();
	bool PinOriginalViewport(TSharedPtr<ISlateViewport>& OutInterface, FString& OutError) const;
	void OnViewportRendered(FViewport* Viewport);
	void OnViewportCloseRequested(FViewport* Viewport);
	void OnWorldCleanup(UWorld* World, bool bSessionEnded, bool bCleanupResources);
	void OnEndPIE(bool bSimulating);
	void Fail(const FString& Reason);
	void DetachCallbacks();

	UPROPERTY(Transient)
	FGGYGOViewportReadbackResult Result;
	UPROPERTY(Transient)
	TWeakObjectPtr<UWorld> OriginalWorld;
	UPROPERTY(Transient)
	TWeakObjectPtr<UGameViewportClient> OriginalClient;
	/** widget/interface 的原共享控制块证明存活，避免把复用的 raw 地址当成原 viewport。 */
	TWeakPtr<SViewport> OriginalWidget;
	TWeakPtr<ISlateViewport> OriginalInterface;
	/** 只在原 interface 已 Pin 且当前 client 仍持有该对象时使用。 */
	FSceneViewport* OriginalViewport = nullptr;
	FDelegateHandle RenderedHandle;
	FDelegateHandle CloseHandle;
	FDelegateHandle WorldCleanupHandle;
	FDelegateHandle EndPIEHandle;
	TSharedPtr<FGGYGOPlayerViewObservationState> PlayerView;
};

/** 通用 Editor 诊断入口；PNG 落盘及路径/hash 读回由宿主拥有。 */
UCLASS()
class GGYGOEDITOR_API UGGYGOViewportReadbackLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/** 等待 ExpectedWorld 的原游戏 viewport 下一次自然绘制，然后同步读回一次 SDR PNG。
	 * @param ExpectedWorld 明确的实际游戏 World；原 viewport/接口尚未就绪时明确失败，不选择其它目标。
	 * @return 调用方持有并最终 Release 的任务；失败也返回带可定位诊断的原任务。
	 * Complete 只证明该目标的原生读回及 PNG 编码完成。宿主分别记录文件完成和原 Finalize 的时机边界。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Viewport")
	static UGGYGOViewportReadbackTask* BeginGameViewportReadback(UWorld* ExpectedWorld);

	/** 首个生产 Draw 前布防，观察原玩家自然 SetupView；不调用相机求值、GetProjectionData 或 Draw。
	 * @param ExpectedPlayer 明确属于原 World/viewport 的实际 LocalPlayer；PC/PCM/Pawn 就绪后只固定一次。
	 * @param ExpectedMode 原配置明确的精确 CameraMode 类；不构造、不加载或替换模式。
	 * @param MaxDraws 1..4096 的自然 Draw 容量；未取得匹配视图则失败，由宿主截止或 finally Release。
	 * @return 同一任务的值观察模式。已确认后才布防只证首次观察，不证首次确认或确认位写入时刻。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Viewport")
	static UGGYGOViewportReadbackTask* BeginPlayerViewObservation(UWorld* ExpectedWorld,
		ULocalPlayer* ExpectedPlayer, TSubclassOf<UGGYGOCameraMode> ExpectedMode, int32 MaxDraws);
};
