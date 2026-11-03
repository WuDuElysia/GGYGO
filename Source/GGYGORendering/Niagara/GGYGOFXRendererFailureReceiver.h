/** @file GGYGOFXRendererFailureReceiver.h
 *  @brief 原Niagara实例的渲染首错接缝；清理由原FX拥有者沿既有生命周期执行。
 */
#pragma once

#include "CoreMinimal.h"
#include "UObject/Interface.h"
#include "GGYGOFXRendererFailureReceiver.generated.h"

class UNiagaraSystem;

UINTERFACE(MinimalAPI)
class UGGYGOFXRendererFailureReceiver : public UInterface
{
	GENERATED_BODY()
};

/** Renderer只报告原来源事实，不停止或重置FX；接收者核原窗口/World/System/id后消费首错。
 *  GT调用；跨线程投递仅持原组件/系统弱引用与原id，过期投递不能清理后继实例。
 */
class GGYGORENDERING_API IGGYGOFXRendererFailureReceiver
{
	GENERATED_BODY()

public:
	/** @param OriginalSystem 报错时原实例使用的真实System。
	 *  @param OriginalInstanceId 原Niagara实例id，不能在投递时改取后继id。
	 *  @param SourceReference 原Renderer/资产路径，由配置提供，不猜来源。
	 *  @param Reason 首个具体失败原因；不将坏数据改成空输出成功。
	 */
	virtual void ReportFXRendererFailure(UNiagaraSystem* OriginalSystem, uint64 OriginalInstanceId,
		const FString& SourceReference, const FString& Reason) = 0;
};
