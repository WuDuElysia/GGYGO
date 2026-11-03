/** @file GGYGORenderingModule.cpp
 *  @brief 在全局 Shader 初始化前注册项目 Shader 目录。
 */
#include "Modules/ModuleManager.h"
#include "Async/TaskGraphInterfaces.h"
#include "Misc/Paths.h"
#include "RenderingThread.h"
#include "ShaderCore.h"

class FGGYGORenderingModule final : public IModuleInterface
{
public:
	virtual void StartupModule() override
	{
		AddShaderSourceDirectoryMapping(TEXT("/GGYGORendering"),
			FPaths::ConvertRelativePathToFull(FPaths::Combine(FPaths::ProjectDir(), TEXT("Shaders"))));
	}

	virtual void ShutdownModule() override
	{
		// World 先撤销发布；已提交的 family/graph 先归还，才允许模块结束。
		FlushRenderingCommands();
		// RT 最后一个 family 的 deleter 会投递 GT 释放；先消费再结束模块代码寿命。
		if (FTaskGraphInterface::IsRunning())
		{
			FTaskGraphInterface::Get().ProcessThreadUntilIdle(ENamedThreads::GameThread);
		}
	}

	virtual bool SupportsDynamicReloading() override { return false; }
};

IMPLEMENT_MODULE(FGGYGORenderingModule, GGYGORendering);
