// Copyright Epic Games, Inc. All Rights Reserved.
/** @file GGYGOEditor.cpp @brief 项目编辑器模块的原生工具注册与退役。 */

#include "GGYGOEditor.h"
#include "GGYGONiagaraCompileLibrary.h"

#include "Misc/CoreDelegates.h"
#include "ToolsetRegistry/UToolsetRegistry.h"

IMPLEMENT_MODULE(FGGYGOEditorModule, GGYGOEditor);

void FGGYGOEditorModule::StartupModule()
{
	FCoreDelegates::OnAllModuleLoadingPhasesComplete.AddRaw(this, &FGGYGOEditorModule::RegisterNiagaraCompileTools);
	FCoreDelegates::OnPreExit.AddRaw(this, &FGGYGOEditorModule::UnregisterNiagaraCompileTools);
	RegisterNiagaraCompileTools();
}

void FGGYGOEditorModule::ShutdownModule()
{
	FCoreDelegates::OnAllModuleLoadingPhasesComplete.RemoveAll(this);
	FCoreDelegates::OnPreExit.RemoveAll(this);
	UnregisterNiagaraCompileTools();
}

void FGGYGOEditorModule::RegisterNiagaraCompileTools()
{
	// 启动早期 Registry 尚未可用；由同一个原生加载完成信号注册，不另设重试器。
	if (UToolsetRegistry::IsAvailable()
		&& !UToolsetRegistry::IsToolsetClassRegistered(UGGYGONiagaraCompileLibrary::StaticClass()))
	{
		UToolsetRegistry::RegisterToolsetClass(UGGYGONiagaraCompileLibrary::StaticClass());
	}
}

void FGGYGOEditorModule::UnregisterNiagaraCompileTools()
{
	if (UObjectInitialized() && UToolsetRegistry::IsAvailable())
	{
		UToolsetRegistry::UnregisterToolsetClass(UGGYGONiagaraCompileLibrary::StaticClass());
	}
}
