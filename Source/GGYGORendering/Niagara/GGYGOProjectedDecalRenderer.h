/** @file GGYGOProjectedDecalRenderer.h
 *  @brief 沿原Niagara GT更新承接完整payload，再复用原生Decal投影与Scene代理生命周期。
 */
#pragma once

#include "NiagaraRendererDecals.h"
#include <atomic>

class UNiagaraComponent;
class UNiagaraSystem;
class UGGYGOProjectedDecalRendererProperties;

/** 仅增加同帧私有MID的生产/归还，不新增模拟、Tick或FX完成状态。 */
class FGGYGOProjectedDecalRenderer final : public FNiagaraRendererDecals
{
public:
	FGGYGOProjectedDecalRenderer(ERHIFeatureLevel::Type InFeatureLevel,
		const UGGYGOProjectedDecalRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter);
	static void ReportCreationFailure(const FNiagaraEmitterInstance* Emitter, const FString& SourceReference,
		const FString& Reason);
	virtual ~FGGYGOProjectedDecalRenderer() override;
	virtual void PostSystemTick_GameThread(const UNiagaraRendererProperties* Properties,
		const FNiagaraEmitterInstance* Emitter) override;
	virtual void OnSystemComplete_GameThread(const UNiagaraRendererProperties* Properties,
		const FNiagaraEmitterInstance* Emitter) override;
	virtual void DestroyRenderState_Concurrent() override;
	virtual FNiagaraDynamicDataBase* GenerateDynamicData(const FNiagaraSceneProxy* Proxy,
		const UNiagaraRendererProperties* Properties, const FNiagaraEmitterInstance* Emitter) const override;
private:
	struct FPayload;
	bool PreparePayload_GameThread(const UNiagaraRendererProperties* Properties,
		const FNiagaraEmitterInstance* Emitter) const;
	void RetirePayload() const;
	void ReportFailure(const FString& SourceReference, const FString& Reason) const;
	TWeakObjectPtr<UNiagaraComponent> OriginalComponent;
	TWeakObjectPtr<UNiagaraSystem> OriginalSystem;
	uint64 OriginalInstanceId = 0;
	mutable FCriticalSection PayloadLock;
	// 仅匹配原实例的当前模拟数据；由GT PostTick或本次GT提交准备。
	mutable TSharedPtr<FPayload, ESPMode::ThreadSafe> Payload;
	// Scene中最后提交的代理仍在使用这批MID；只作GPU资源租用，不能作为后继采样输入。
	mutable TSharedPtr<FPayload, ESPMode::ThreadSafe> SubmittedPayload;
	// 只抑制同Renderer寿命内重复首错；原FX拥有者决定结束原实例。
	mutable std::atomic<bool> bFailureReported{false};
};
