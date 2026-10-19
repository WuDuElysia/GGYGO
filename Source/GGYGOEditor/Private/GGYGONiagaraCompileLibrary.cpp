/** @file GGYGONiagaraCompileLibrary.cpp @brief 连接 Niagara 原生编译收束及真实布局诊断。 */
#include "GGYGONiagaraCompileLibrary.h"

#include "Editor.h"
#include "Misc/App.h"
#include "NiagaraEmitter.h"
#include "NiagaraScript.h"
#include "NiagaraScriptSourceBase.h"
#include "NiagaraSystem.h"
#include "UObject/StrongObjectPtr.h"

FGGYGONiagaraCompileState UGGYGONiagaraCompileLibrary::ReadSystemState(UNiagaraSystem* System)
{
	FGGYGONiagaraCompileState Result;
	Result.SystemPath = GetPathNameSafe(System);
	if (!IsInGameThread() || !IsValid(System))
	{
		Result.Error = TEXT("原生 Niagara 状态查询需要 GameThread 上的有效原资产。");
		return Result;
	}
	// 公开接口完成必要加载；不复制私有 Ready/PSO 分支。
	Result.bSystemValid = System->IsValid();
	Result.bNativeReady = System->IsReadyToRun();
	Result.bCompilationPending = System->HasOutstandingCompilationRequests(true);
	Result.bNeedsCompileRequest = System->NeedsRequestCompile();
	Result.bActiveCompilations = System->HasActiveCompilations();
	Result.EmitterCount = System->GetEmitterHandles().Num();
	Result.CompiledEmitterCount = System->GetEmitterCompiledData().Num();
	for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
	{
		Result.EmitterNames.Add(Handle.GetName());
		Result.EmitterEnabled.Add(Handle.GetIsEnabled());
	}
	const UNiagaraScript* Spawn = System->GetSystemSpawnScript();
	const UNiagaraScript* Update = System->GetSystemUpdateScript();
	if (!Spawn || !Update)
	{
		Result.Error = TEXT("原 Niagara System 缺少 Spawn 或 Update Script。");
		return Result;
	}
	const TArray<FNiagaraVariableBase>& SpawnAttributes = Spawn->GetVMExecutableData().Attributes;
	const TArray<FNiagaraVariableBase>& UpdateAttributes = Update->GetVMExecutableData().Attributes;
	Result.SpawnAttributeCount = SpawnAttributes.Num();
	Result.UpdateAttributeCount = UpdateAttributes.Num();
	Result.bVMAttributesEqual = SpawnAttributes == UpdateAttributes;
	return Result;
}

FGGYGONiagaraCompileState UGGYGONiagaraCompileLibrary::CompletePendingCompilation(UNiagaraSystem* System)
{
	FGGYGONiagaraCompileState Result;
	Result.SystemPath = GetPathNameSafe(System);
	if (!IsInGameThread() || !IsValid(System) || !GEditor || GEditor->PlayWorld || !FApp::CanEverRender())
	{
		Result.Error = TEXT("编译收束需要有效原资产及非 PIE、可渲染的原生 Editor GameThread。");
		return Result;
	}
	if (!System->GetSystemSpawnScript() || !System->GetSystemUpdateScript())
	{
		Result.Error = TEXT("编译收束的原 Niagara System 缺少 Spawn 或 Update Script。");
		return Result;
	}
	TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	// 原生自行处理待发起请求、结果提取和内部重试，不复制编译状态机。
	System->WaitForCompilationComplete(true, false);
	return ReadSystemState(OriginalSystem.Get());
}

FGGYGONiagaraCompileState UGGYGONiagaraCompileLibrary::ForceCompile(UNiagaraSystem* System)
{
	FGGYGONiagaraCompileState Result;
	Result.SystemPath = GetPathNameSafe(System);
	if (!IsInGameThread() || !IsValid(System) || !GEditor || GEditor->PlayWorld || !FApp::CanEverRender())
	{
		Result.Error = TEXT("完整编译需要有效原资产及非 PIE、可渲染的原生 Editor GameThread。");
		return Result;
	}
	TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	UNiagaraScript* Spawn = System->GetSystemSpawnScript();
	UNiagaraScript* Update = System->GetSystemUpdateScript();
	// RequestCompile(true) 的原生强制路径断言同一 System 源图，并访问全部 Emitter 源图。
	if (!Spawn || !Update || !IsValid(Spawn->GetLatestSource())
		|| Spawn->GetLatestSource() != Update->GetLatestSource())
	{
		Result.Error = TEXT("完整编译需要 Spawn/Update 共享有效原 System 源图。");
		return Result;
	}
	for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
	{
		const FVersionedNiagaraEmitterData* Data = Handle.GetEmitterData();
		if (Data && !IsValid(Data->GraphSource))
		{
			Result.Error = FString::Printf(TEXT("完整编译缺少 Emitter '%s' 的原源图。"), *Handle.GetName().ToString());
			return Result;
		}
	}
	const bool bRequested = System->RequestCompile(true);
	if (!bRequested)
	{
		Result = ReadSystemState(System);
		Result.Error = TEXT("Niagara 原生 RequestCompile(true) 未发出完整编译请求。");
		return Result;
	}
	System->WaitForCompilationComplete(true, false);
	Result = ReadSystemState(OriginalSystem.Get());
	Result.bForceCompileRequested = true;
	return Result;
}
