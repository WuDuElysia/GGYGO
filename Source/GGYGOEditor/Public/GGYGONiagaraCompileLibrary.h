/** @file GGYGONiagaraCompileLibrary.h @brief 编辑器原生 Niagara 编译收束与即时结果读回。 */
#pragma once

#include "CoreMinimal.h"
#include "ToolsetRegistry/ToolsetDefinition.h"
#include "GGYGONiagaraCompileLibrary.generated.h"

class UNiagaraSystem;

/** 一次原生查询的快照；不持有资源，不代表首粒子或动作播放已验证。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraCompileState
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bForceCompileRequested = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bCompilationPending = false;
	/** 原生尚有待发起的编译请求；不等同于编译任务已经运行。 */
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bNeedsCompileRequest = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bActiveCompilations = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bSystemValid = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bNativeReady = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bVMAttributesEqual = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	int32 EmitterCount = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	int32 CompiledEmitterCount = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	int32 SpawnAttributeCount = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	int32 UpdateAttributeCount = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	TArray<FName> EmitterNames;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	TArray<bool> EmitterEnabled;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	FString Error;
};

/** 标准 Editor Python 与既有 Toolset Registry 共用的薄入口；不保存或重建资产。 */
UCLASS()
class GGYGOEDITOR_API UGGYGONiagaraCompileLibrary : public UToolsetDefinition
{
	GENERATED_BODY()

public:
	/** @param System 原资产；只查询公开原生状态及完整有序 VM 属性，不触发强制编译。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraCompileState ReadSystemState(UNiagaraSystem* System);

	/**
	 * 由原生等待入口发起已有待编译请求并提取 GPU/VM 结果；不显式请求强制编译或保存。
	 * @param System 非 PIE、可渲染 Editor GameThread 上的原资产。
	 * @return 收束后的即时状态；原生内部重试、失败和未 Ready 均由调用方如实检查。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraCompileState CompletePendingCompilation(UNiagaraSystem* System);

	/**
	 * 请求原资产完整编译并由原生编译器等待 GPU/VM 结果；不创建等待器或保存资产。
	 * @param System 必须具有编辑器源图，且 Editor 不在 PIE。
	 * @return 原生请求是否发出和收束后的即时结果；调用方负责准入及精确保存。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraCompileState ForceCompile(UNiagaraSystem* System);
};
