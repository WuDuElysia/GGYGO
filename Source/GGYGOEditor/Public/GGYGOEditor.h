// Copyright Epic Games, Inc. All Rights Reserved.
/** @file GGYGOEditor.h @brief 项目编辑器模块及原生工具注册生命周期。 */

#pragma once

#include "CoreMinimal.h"
#include "Modules/ModuleManager.h"

/**
 * GGYGOEditor —— 编辑器专用模块。
 * 存放编辑器动画工具，并接入特效编译工具的原生注册生命周期。
 */
class FGGYGOEditorModule : public IModuleInterface
{
public:
	virtual void StartupModule() override;
	virtual void ShutdownModule() override;

private:
	void RegisterNiagaraCompileTools();
	void UnregisterNiagaraCompileTools();
};
