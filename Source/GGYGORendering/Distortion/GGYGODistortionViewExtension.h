/** @file GGYGODistortionViewExtension.h
 *  @brief 按公开family/View回调冻结并收集原Niagara数据，合成入口与阶段选择分离。
 */
#pragma once

#include "CoreMinimal.h"
#include "SceneViewExtension.h"

class UGGYGODistortionSubsystem;
struct FPostProcessMaterialInputs;
struct FScreenPassTexture;

class FGGYGODistortionViewExtension final : public FWorldSceneViewExtension
{
public:
	FGGYGODistortionViewExtension(const FAutoRegister& AutoRegister, UGGYGODistortionSubsystem* Subsystem);
	virtual void SetupViewFamily(FSceneViewFamily& Family) override;
	virtual void SetupView(FSceneViewFamily&, FSceneView&) override {}
	virtual void BeginRenderViewFamily(FSceneViewFamily&) override {}
	virtual void PreRenderView_RenderThread(FRDGBuilder& GraphBuilder, FSceneView& View) override;
	virtual void SubscribeToPostProcessingPass(EPostProcessingPass Pass, const FSceneView& View,
		FPostProcessingPassDelegateArray& Callbacks, bool bIsPassEnabled) override;
	/** 公共阶段只消费同一次View/Graph的完整配置及几何。 */
	bool TryCompositeView(FRDGBuilder& GraphBuilder, const FSceneView& View,
		const FPostProcessMaterialInputs& Inputs, FScreenPassTexture& OutColor, FString& OutReason) const;
	void DetachSubsystem();
private:
	FScreenPassTexture CompositeBeforeDOF(FRDGBuilder& GraphBuilder, const FSceneView& View,
		const FPostProcessMaterialInputs& Inputs);
	// RT独占的当前失败诊断；成功后清理，避免稳定失败逐帧刷屏。
	FString LastCompositeFailure;
	TWeakObjectPtr<UGGYGODistortionSubsystem> Subsystem;
};
