/** @file GGYGOProjectedDecalRendererProperties.h
 *  @brief 原生Decal投影的逐粒子向量参数配置；数据仍来自原Niagara CPU实例。
 */
#pragma once

#include "NiagaraDecalRendererProperties.h"
#include "GGYGOProjectedDecalRendererProperties.generated.h"

class UNiagaraSystem;
class UMaterial;
class UMaterialInterface;
class UWorld;

/** 单次作者调用读取的原 World 平台资源状态；不缓存或替代运行时 field 资格。 */
USTRUCT(BlueprintType)
struct GGYGORENDERING_API FGGYGOMaterialCompilationState
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") bool bReady = false;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") FString MaterialPath;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") FString WorldPath;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") int32 ShaderPlatform = INDEX_NONE;
	/** 无独立静态变体的 MI 可能使用 Parent 的资源；这里记录实际资源所有者。 */
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") FString ResourceMaterialPath;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") bool bResourceAvailable = false;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") bool bShaderMapComplete = false;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") bool bShaderMapPresent = false;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") bool bCompilationFinalized = false;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") bool bCompiledSuccessfully = false;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") bool bValidForRendering = false;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") TArray<FString> CompileErrors;
	UPROPERTY(BlueprintReadOnly, Category = "Material Compilation") FString Error;
};

/** 原生Decal的Color/Fade之外的payload由私有MID承接，配置不编码角色或Shader编号。 */
UCLASS(EditInlineNew, meta = (DisplayName = "GGYGO Projected Decal Renderer"))
class GGYGORENDERING_API UGGYGOProjectedDecalRendererProperties final : public UNiagaraRendererProperties
{
	GENERATED_BODY()
public:
	UGGYGOProjectedDecalRendererProperties();
	/** Native类型为MinimalAPI，持有并经基类虚接口调用，不链接未导出的实现。 */
	UPROPERTY(VisibleAnywhere, Instanced, Category = "Native Projection")
	TObjectPtr<UNiagaraDecalRendererProperties> NativeDecal;
	/** 原作者用已有绑定工具配置此子对象；同步已有Emitter版本，不创建替代对象。 */
	UFUNCTION(BlueprintCallable, Category = "Native Projection")
	UNiagaraDecalRendererProperties* GetNativeDecalForAuthoring();
	/** 制作窗将唯一原NS的User Material参数与Native子对象绑定；不编译或保存资产。 */
	UFUNCTION(BlueprintCallable, Category = "Native Projection", meta = (DevelopmentOnly))
	bool BindSourceUserMaterialForAuthoring(UNiagaraSystem* System, FName UserParameterName,
		UMaterialInterface* Material, FString& Error);
	/** 读取原CacheFromCompiledData结果；不编译、不构造数据集，不证明运行帧或GPU。 */
	UFUNCTION(BlueprintCallable, Category = "Source Payload")
	bool ReadCompiledPayloadLayoutForAuthoring(TArray<FName>& ValidVectorAttributes,
		TArray<FName>& InvalidVectorAttributes, bool& bNativeGeometryValid, FString& Error) const;
	/** 只读真实MaterialResource/ShaderMap；Decal没有Surface代表性指令数也须明确核准入。 */
	UFUNCTION(BlueprintCallable, Category = "Native Projection")
	static bool ReadMaterialCompilationForAuthoring(UMaterial* Material, bool& bShaderMapComplete,
		TArray<FString>& CompileErrors, FString& Error);
	/** Editor 作者完成准确 MaterialInterface 在指定 World 平台的已有派生编译。
	 * World/Scene/原资源必须真实存在；不借其它平台替代。
	 * 不重建图或保存包。
	 * 返回完整失败状态，供原资源门核收；Ready 不代表 field 角色或 GPU/画面验收。 */
	UFUNCTION(BlueprintCallable, Category = "Material Compilation")
	static FGGYGOMaterialCompilationState CompleteMaterialCompilationForAuthoring(
		UMaterialInterface* Material, UWorld* World);
	/** 读取唯一原Native Mesh renderer的真实当前/派生Prev绑定及两种编译布局；不造历史值。 */
	UFUNCTION(BlueprintCallable, Category = "Native Projection")
	static bool ReadNativeMeshMotionForAuthoring(UNiagaraSystem* System, FName EmitterName, int32 RendererIndex,
		bool& bNeedsPrecise, TArray<FName>& CurrentAttributes, TArray<FName>& PreviousAttributes,
		TArray<bool>& CurrentLayoutValid, TArray<bool>& PreviousLayoutValid, FString& Error);
	UPROPERTY(EditAnywhere, Category = "Source Payload") bool bPayloadConfigured = false;
	/** 原资产/Renderer路径，用于定位原FX首错。 */
	UPROPERTY(EditAnywhere, Category = "Source Payload") FString SourceReference;
	/** 完整Particles命名空间，类型必须为float4；不把缺项改成默认向量。 */
	UPROPERTY(EditAnywhere, Category = "Source Payload") TArray<FName> ParticleVectorAttributes;
	/** 与属性逐项对应的真实Material vector参数名。 */
	UPROPERTY(EditAnywhere, Category = "Source Payload") TArray<FName> MaterialVectorParameters;
	/** 非None时写原System Age；源时间换算由材质计划明确给出。 */
	UPROPERTY(EditAnywhere, Category = "Source Payload") FName SimulationAgeParameter;
	/** 明确的实时MID容量；超过额度报告失败，不丢粒子或换统一材质。 */
	UPROPERTY(EditAnywhere, Category = "Source Payload") int32 MaxMaterialInstances = 0;

	virtual FNiagaraRenderer* CreateEmitterRenderer(ERHIFeatureLevel::Type FeatureLevel,
		const FNiagaraEmitterInstance* Emitter, const FNiagaraSystemInstanceController& InController) override;
	virtual FNiagaraBoundsCalculator* CreateBoundsCalculator() override;
	virtual void GetUsedMaterials(const FNiagaraEmitterInstance* Emitter, TArray<UMaterialInterface*>& Materials) const override;
	virtual ENiagaraRendererSourceDataMode GetCurrentSourceMode() const override;
	virtual bool PopulateRequiredBindings(FNiagaraParameterStore& Store) override;
	virtual void UpdateSourceModeDerivates(ENiagaraRendererSourceDataMode Mode, bool bFromPropertyEdit = false) override;
	virtual bool NeedsSystemPostTick() const override { return true; }
	virtual bool NeedsSystemCompletion() const override { return true; }
	virtual bool IsSimTargetSupported(ENiagaraSimTarget Target) const override
	{ return Target == ENiagaraSimTarget::CPUSim; }
	virtual void CacheFromCompiledData(const FNiagaraDataSetCompiledData* CompiledData) override;
#if WITH_EDITORONLY_DATA
	virtual TArray<FNiagaraVariable> GetBoundAttributes() const override;
#endif
	bool ValidatePayloadConfiguration(FString& Error) const;
	bool ValidateCompiledPayloadLayout(FString& Error) const;
	TArray<FNiagaraDataSetAccessor<FVector4f>> VectorAccessors;
private:
	// 原CacheFromCompiledData生成的布局依赖名；配置改名后不能把旧offset当成当前布局。
	TArray<FName> CompiledVectorAttributeNames;
	TArray<FName> CompiledNativeGeometryNames;
};
