/**
 * @file GGYGONiagaraMeshDrawTestProbe.h
 * @brief 原主视口单次 Draw 的 Niagara 动态 MeshBatch 测试取证。
 */

#pragma once

#include "CoreMinimal.h"
#include "UObject/Object.h"
#include "GGYGONiagaraMeshDrawTestProbe.generated.h"

class APawn;
class FGGYGONiagaraMeshDrawTestView;
class FViewport;
class UGameViewportClient;
class ULocalPlayer;
class UMaterialInterface;
class UNiagaraComponent;

UENUM()
enum class EGGYGONiagaraMeshDrawCoverage : uint8
{
	Pending,
	Covered,
	Uncovered
};

USTRUCT()
struct FGGYGONiagaraMeshDrawRTProxy
{
	GENERATED_BODY()

	// 代理名称仅用于诊断，原批次归属仍用指针身份。
	UPROPERTY()
	FString ProxyName;

	UPROPERTY()
	FName ResourceStatus;

	UPROPERTY()
	int32 BlendMode = INDEX_NONE;

	UPROPERTY()
	int32 MaterialDomain = INDEX_NONE;

	UPROPERTY()
	bool bAfterDOF = false;

	UPROPERTY()
	bool bAfterMotionBlur = false;

	UPROPERTY()
	bool bShaderMapComplete = false;
};

USTRUCT()
struct FGGYGONiagaraMeshDrawRTMaterial
{
	GENERATED_BODY()

	UPROPERTY()
	FName BatchStatus;

	UPROPERTY()
	int32 FeatureLevel = INDEX_NONE;

	UPROPERTY()
	int32 ShaderPlatform = INDEX_NONE;

	UPROPERTY()
	FName VertexFactoryType;

	UPROPERTY()
	bool bUseForMaterial = false;

	UPROPERTY()
	bool bVertexFactorySupportsGPUScene = false;

	UPROPERTY()
	FGGYGONiagaraMeshDrawRTProxy Original;

	// 原生链提供的候选顺序。候选不代表 Pass 选择结果。
	UPROPERTY()
	TArray<FGGYGONiagaraMeshDrawRTProxy> FallbackCandidates;

	UPROPERTY()
	FName FallbackStatus;

	UPROPERTY()
	FName ShaderKeyCoverage;
};

USTRUCT()
struct FGGYGONiagaraMeshDrawBatchCounts
{
	GENERATED_BODY()

	UPROPERTY()
	FString MaterialPath;

	UPROPERTY()
	int32 MeshBatches = INDEX_NONE;

	// 每个 Pass 独立计数。键缺席表示该 Pass 无候选，仅在 Covered 时有效。
	UPROPERTY()
	TMap<FString, int32> PassCandidates;

	// 仅对三份目标材质的唯一已归属批次提供 RT 状态。
	UPROPERTY()
	FGGYGONiagaraMeshDrawRTMaterial RTMaterial;
};

USTRUCT()
struct FGGYGONiagaraMeshDrawTestResult
{
	GENERATED_BODY()

	UPROPERTY()
	EGGYGONiagaraMeshDrawCoverage Coverage = EGGYGONiagaraMeshDrawCoverage::Pending;

	UPROPERTY()
	FName Reason;

	UPROPERTY()
	int64 FrameCounter = INDEX_NONE;

	UPROPERTY()
	int64 WorldObjectId = 0;

	UPROPERTY()
	FString ViewportIdentity;

	UPROPERTY()
	FString ComponentPath;

	UPROPERTY()
	int64 PrimitiveComponentId = 0;

	UPROPERTY()
	int64 NiagaraInstanceId = INDEX_NONE;

	UPROPERTY()
	int32 ComponentMeshBatches = INDEX_NONE;

	/** 原 RT SceneView 的投影输入；仅供同帧 CPU 属性/画面对齐，不代表发光区或最终 Draw。 */
	UPROPERTY()
	FIntRect UnscaledViewRect;

	UPROPERTY()
	FIntRect RenderViewRect;

	/** 原 ViewProjection，按行主序保存 16 项，不含其它样本或后续镜头。 */
	UPROPERTY()
	TArray<double> ViewProjectionMatrix;

	// 按 BeginNextDraw 的材质入参顺序返回。
	UPROPERTY()
	TArray<FGGYGONiagaraMeshDrawBatchCounts> Materials;

	UPROPERTY()
	FGGYGONiagaraMeshDrawBatchCounts Unattributed;
};

UCLASS(Transient)
class GGYGOEDITOR_API UGGYGONiagaraMeshDrawTestProbe : public UObject
{
	GENERATED_BODY()

public:
	/** 在原测试选中的下一次 Draw 前调用。每样本独立持有至终态/Cancel；同 Family 最多三份。 */
	UFUNCTION()
	static UGGYGONiagaraMeshDrawTestProbe* BeginNextDraw(ULocalPlayer* Player, APawn* ViewPawn,
		UNiagaraComponent* Component, const TArray<UMaterialInterface*>& Materials);

	/** 由原样本的 OnDrawn 同步确认，必须处在本次 BeginDraw 到 OnViewportRendered 之间。 */
	UFUNCTION()
	bool ConfirmOriginalDraw(UNiagaraComponent* Component);

	/** 非阻塞，返回本次被确认 Draw 的终态或 Pending。 */
	UFUNCTION()
	FGGYGONiagaraMeshDrawTestResult Poll();

	UFUNCTION()
	void Cancel();

	virtual void BeginDestroy() override;

private:
	void OnBeginDraw();
	void OnViewportRendered(FViewport* Viewport);
	bool HasOriginalInstance(UNiagaraComponent* Component) const;
	void FinishUncovered(FName Reason);
	void Detach();

	TWeakObjectPtr<UGameViewportClient> Client;
	TWeakObjectPtr<UNiagaraComponent> ObservedComponent;
	TSharedPtr<FGGYGONiagaraMeshDrawTestView, ESPMode::ThreadSafe> ViewExtension;
	FDelegateHandle BeginDrawHandle;
	FDelegateHandle ViewportRenderedHandle;
	FGGYGONiagaraMeshDrawTestResult Result;
	double DeadlineSeconds = 0.0;
	bool bOriginalDrawConfirmed = false;
	bool bViewportRendered = false;

	// 在原 RenderFamily 完成取证前保持精确材质代理的对象身份。
	UPROPERTY(Transient)
	TArray<TObjectPtr<UMaterialInterface>> ObservedMaterials;
};
