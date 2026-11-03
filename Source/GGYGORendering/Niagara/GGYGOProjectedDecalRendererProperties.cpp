/** @file GGYGOProjectedDecalRendererProperties.cpp
 *  @brief 声明实际CPU属性依赖并校验逐粒子Material参数合同。
 */
#include "GGYGOProjectedDecalRendererProperties.h"
#include "GGYGOProjectedDecalRenderer.h"

#include "Engine/Engine.h"
#include "Engine/World.h"
#include "Materials/Material.h"
#include "MaterialShared.h"
#include "NiagaraEmitter.h"
#include "NiagaraMeshRendererProperties.h"
#include "NiagaraSystem.h"
#include "SceneInterface.h"
#include "ShaderCore.h"
#include "UObject/StrongObjectPtr.h"

UGGYGOProjectedDecalRendererProperties::UGGYGOProjectedDecalRendererProperties()
{
	NativeDecal = CreateDefaultSubobject<UNiagaraDecalRendererProperties>(TEXT("NativeDecal"));
}

UNiagaraDecalRendererProperties* UGGYGOProjectedDecalRendererProperties::GetNativeDecalForAuthoring()
{
	if (NativeDecal) NativeDecal->OuterEmitterVersion = OuterEmitterVersion;
	return NativeDecal;
}

bool UGGYGOProjectedDecalRendererProperties::BindSourceUserMaterialForAuthoring(
	UNiagaraSystem* System, FName UserParameterName, UMaterialInterface* Material, FString& Error)
{
	Error.Reset();
#if WITH_EDITOR && WITH_EDITORONLY_DATA
	const FString Name = UserParameterName.ToString();
	if (!IsInGameThread() || !GIsEditor || !IsValid(System) || System->IsTemplate()
		|| !IsValid(Material) || !IsValid(NativeDecal) || !Name.StartsWith(TEXT("User.")) || Name.Len() <= 5
		|| !Material->GetMaterial() || Material->GetMaterial()->MaterialDomain != MD_DeferredDecal)
	{ Error = TEXT("投影UserMaterial制作需要Editor中的准确NS/Decal Material/User参数"); return false; }
	if (GEngine)
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
			if (Context.WorldType == EWorldType::PIE)
			{ Error = TEXT("PIE期间不修改投影资产绑定"); return false; }
	const FNiagaraVariable Parameter(FNiagaraTypeDefinition::GetUMaterialDef(), UserParameterName);
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	const TStrongObjectPtr<UGGYGOProjectedDecalRendererProperties> OriginalRenderer(this);
	const TStrongObjectPtr<UNiagaraDecalRendererProperties> OriginalNative(NativeDecal.Get());
	const TStrongObjectPtr<UMaterialInterface> OriginalMaterial(Material);
	const auto IsOriginalRenderer = [&]()
	{
		if (!IsValid(System) || !IsValid(this) || !IsValid(Material) || !IsValid(OriginalNative.Get())
			|| NativeDecal != OriginalNative.Get()) return false;
		int32 Matches = 0;
		for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
			if (const FVersionedNiagaraEmitterData* Data = Handle.GetEmitterData())
				for (const UNiagaraRendererProperties* Renderer : Data->GetRenderers())
					if (Renderer == this) ++Matches;
		return Matches == 1;
	};
	const auto BindingAvailable = [&]()
	{
		const auto& Binding = NativeDecal->MaterialParameterBinding;
		if (Binding.ResolvedParameter.IsValid() && Binding.ResolvedParameter != Parameter) return false;
		if (Binding.AliasedParameter.IsValid() && Binding.AliasedParameter != Parameter) return false;
		const auto& Store = System->GetExposedParameters();
		for (const auto& Existing : Store.ReadParameterVariables())
			if (Existing.GetName() == Parameter.GetName() && Existing.GetType() != Parameter.GetType()) return false;
		return Store.IndexOf(Parameter) == INDEX_NONE || Store.GetUObject(Parameter).Get() == Material;
	};
	if (!IsOriginalRenderer() || !BindingAvailable())
	{ Error = TEXT("投影绑定不是唯一原NS/renderer或已有冲突User参数"); return false; }
	System->Modify();
	Modify();
	OriginalNative->Modify();
	if (!IsOriginalRenderer() || !BindingAvailable())
	{ Error = TEXT("Modify期间原投影renderer/User参数已改变"); return false; }
	auto& Store = System->GetExposedParameters();
	if (Store.IndexOf(Parameter) == INDEX_NONE) Store.AddParameter(Parameter, false);
	Store.SetUObject(Material, Parameter);
	NativeDecal->Material = Material;
	NativeDecal->MaterialParameterBinding.ResolvedParameter = Parameter;
	NativeDecal->MaterialParameterBinding.AliasedParameter = Parameter;
	NativeDecal->PostEditChange();
	if (!IsOriginalRenderer() || !BindingAvailable() || NativeDecal->Material != Material
		|| NativeDecal->MaterialParameterBinding.ResolvedParameter != Parameter
		|| NativeDecal->MaterialParameterBinding.AliasedParameter != Parameter
		|| System->GetExposedParameters().GetUObject(Parameter).Get() != Material)
	{ Error = TEXT("原投影UserMaterial写后绑定/参数读回不符"); return false; }
	System->MarkPackageDirty();
	return true;
#else
	Error = TEXT("投影UserMaterial绑定仅供Editor制作");
	return false;
#endif
}

FNiagaraRenderer* UGGYGOProjectedDecalRendererProperties::CreateEmitterRenderer(
	ERHIFeatureLevel::Type FeatureLevel, const FNiagaraEmitterInstance* Emitter,
	const FNiagaraSystemInstanceController&)
{
	FString Error;
	if (!ValidatePayloadConfiguration(Error))
	{
		FGGYGOProjectedDecalRenderer::ReportCreationFailure(Emitter, SourceReference, Error);
		return nullptr;
	}
	return new FGGYGOProjectedDecalRenderer(FeatureLevel, this, Emitter);
}

FNiagaraBoundsCalculator* UGGYGOProjectedDecalRendererProperties::CreateBoundsCalculator()
{
	UNiagaraRendererProperties* Native = NativeDecal.Get();
	return Native ? Native->CreateBoundsCalculator() : nullptr;
}

void UGGYGOProjectedDecalRendererProperties::GetUsedMaterials(
	const FNiagaraEmitterInstance* Emitter, TArray<UMaterialInterface*>& Materials) const
{
	const UNiagaraRendererProperties* Native = NativeDecal.Get();
	if (Native) Native->GetUsedMaterials(Emitter, Materials);
}

ENiagaraRendererSourceDataMode UGGYGOProjectedDecalRendererProperties::GetCurrentSourceMode() const
{
	// 本扩展只有CPU逐粒子合同；Native子对象选择其它模式会在配置校验中拒绝。
	return ENiagaraRendererSourceDataMode::Particles;
}

bool UGGYGOProjectedDecalRendererProperties::PopulateRequiredBindings(FNiagaraParameterStore& Store)
{
	const bool Added = Super::PopulateRequiredBindings(Store);
	UNiagaraRendererProperties* Native = NativeDecal.Get();
	return Native ? Native->PopulateRequiredBindings(Store) || Added : Added;
}

void UGGYGOProjectedDecalRendererProperties::UpdateSourceModeDerivates(
	ENiagaraRendererSourceDataMode Mode, bool bFromPropertyEdit)
{
	Super::UpdateSourceModeDerivates(Mode, bFromPropertyEdit);
	if (NativeDecal)
	{
		NativeDecal->OuterEmitterVersion = OuterEmitterVersion;
		UNiagaraDecalRendererProperties* Native = NativeDecal.Get();
		Native->UpdateSourceModeDerivates(Mode, bFromPropertyEdit);
	}
}

void UGGYGOProjectedDecalRendererProperties::CacheFromCompiledData(const FNiagaraDataSetCompiledData* CompiledData)
{
	Super::CacheFromCompiledData(CompiledData);
	if (NativeDecal)
	{
		NativeDecal->OuterEmitterVersion = OuterEmitterVersion;
		UNiagaraRendererProperties* Native = NativeDecal.Get();
		Native->CacheFromCompiledData(CompiledData);
	}
	VectorAccessors.Reset();
	CompiledVectorAttributeNames = ParticleVectorAttributes;
	CompiledNativeGeometryNames.Reset();
	if (NativeDecal)
	{
		CompiledNativeGeometryNames = {NativeDecal->PositionBinding.GetDataSetBindableVariable().GetName(),
			NativeDecal->DecalOrientationBinding.GetDataSetBindableVariable().GetName(),
			NativeDecal->DecalSizeBinding.GetDataSetBindableVariable().GetName(),
			NativeDecal->DecalVisibleBinding.GetDataSetBindableVariable().GetName(),
			NativeDecal->DecalSortOrderBinding.GetDataSetBindableVariable().GetName()};
	}
	VectorAccessors.SetNum(ParticleVectorAttributes.Num());
	for (int32 Index = 0; Index < ParticleVectorAttributes.Num(); ++Index)
	{
		FString Name = ParticleVectorAttributes[Index].ToString();
		if (Name.RemoveFromStart(TEXT("Particles.")))
			VectorAccessors[Index].Init(CompiledData, FName(*Name));
	}
}

bool UGGYGOProjectedDecalRendererProperties::ReadCompiledPayloadLayoutForAuthoring(
	TArray<FName>& ValidVectorAttributes, TArray<FName>& InvalidVectorAttributes,
	bool& bNativeGeometryValid, FString& Error) const
{
	ValidVectorAttributes.Reset();
	InvalidVectorAttributes.Reset();
	bNativeGeometryValid = false;
	Error.Reset();
	if (!IsInGameThread())
	{ Error = TEXT("投影编译布局只读查询需要GameThread"); return false; }
	if (!ValidatePayloadConfiguration(Error)) return false;
	const bool bSameVectorLayout = CompiledVectorAttributeNames == ParticleVectorAttributes;
	for (int32 Index = 0; Index < ParticleVectorAttributes.Num(); ++Index)
	{
		if (bSameVectorLayout && VectorAccessors.IsValidIndex(Index) && VectorAccessors[Index].IsValid())
			ValidVectorAttributes.Add(ParticleVectorAttributes[Index]);
		else
			InvalidVectorAttributes.Add(ParticleVectorAttributes[Index]);
	}
	const TArray<FName> CurrentGeometryNames = {NativeDecal->PositionBinding.GetDataSetBindableVariable().GetName(),
		NativeDecal->DecalOrientationBinding.GetDataSetBindableVariable().GetName(),
		NativeDecal->DecalSizeBinding.GetDataSetBindableVariable().GetName(),
		NativeDecal->DecalVisibleBinding.GetDataSetBindableVariable().GetName(),
		NativeDecal->DecalSortOrderBinding.GetDataSetBindableVariable().GetName()};
	bNativeGeometryValid = CompiledNativeGeometryNames == CurrentGeometryNames
		&& NativeDecal->PositionDataSetAccessor.IsValid() && NativeDecal->DecalOrientationDataSetAccessor.IsValid()
		&& NativeDecal->DecalSizeDataSetAccessor.IsValid() && NativeDecal->DecalVisibleAccessor.IsValid()
		&& NativeDecal->DecalSortOrderDataSetAccessor.IsValid();
	if (!InvalidVectorAttributes.IsEmpty() || !bNativeGeometryValid)
	{
		Error = FString::Printf(TEXT("%s：原编译布局有%d项float4无效，Native几何有效=%d；配置改名后须重编译"),
			*SourceReference, InvalidVectorAttributes.Num(), bNativeGeometryValid);
		return false;
	}
	return true;
}

bool UGGYGOProjectedDecalRendererProperties::ValidateCompiledPayloadLayout(FString& Error) const
{
	Error.Reset();
	if (!bPayloadConfigured || !IsValid(NativeDecal) || NativeDecal->SourceMode != ENiagaraRendererSourceDataMode::Particles
		|| CompiledVectorAttributeNames != ParticleVectorAttributes
		|| VectorAccessors.Num() != ParticleVectorAttributes.Num()
		|| MaterialVectorParameters.Num() != ParticleVectorAttributes.Num()
		|| CompiledNativeGeometryNames.Num() != 5
		|| CompiledNativeGeometryNames[0] != NativeDecal->PositionBinding.GetDataSetBindableVariable().GetName()
		|| CompiledNativeGeometryNames[1] != NativeDecal->DecalOrientationBinding.GetDataSetBindableVariable().GetName()
		|| CompiledNativeGeometryNames[2] != NativeDecal->DecalSizeBinding.GetDataSetBindableVariable().GetName()
		|| CompiledNativeGeometryNames[3] != NativeDecal->DecalVisibleBinding.GetDataSetBindableVariable().GetName()
		|| CompiledNativeGeometryNames[4] != NativeDecal->DecalSortOrderBinding.GetDataSetBindableVariable().GetName()
		|| !NativeDecal->PositionDataSetAccessor.IsValid() || !NativeDecal->DecalOrientationDataSetAccessor.IsValid()
		|| !NativeDecal->DecalSizeDataSetAccessor.IsValid() || !NativeDecal->DecalVisibleAccessor.IsValid()
		|| !NativeDecal->DecalSortOrderDataSetAccessor.IsValid())
	{ Error = TEXT("投影原编译布局与当前配置/Native几何不符，需重编译"); return false; }
	for (const auto& Accessor : VectorAccessors)
		if (!Accessor.IsValid())
		{ Error = TEXT("投影原编译布局缺float4属性"); return false; }
	return true;
}

bool UGGYGOProjectedDecalRendererProperties::ReadMaterialCompilationForAuthoring(
	UMaterial* Material, bool& bShaderMapComplete, TArray<FString>& CompileErrors, FString& Error)
{
	bShaderMapComplete = false;
	CompileErrors.Reset();
	Error.Reset();
	// Python bool 返回 false 时不保留 out 参数，失败原因同时写入 UE 日志。
	const auto LogFailure = [&]()
	{
		const FString MaterialPath = GetPathNameSafe(Material);
		UE_LOG(LogTemp, Warning, TEXT("ReadMaterialCompilationForAuthoring Material=%s Error=%s CompileErrors=%d"),
			*MaterialPath, *Error, CompileErrors.Num());
		for (const FString& CompileError : CompileErrors)
		{
			UE_LOG(LogTemp, Warning, TEXT("ReadMaterialCompilationForAuthoring Material=%s CompileError=%s"),
				*MaterialPath, *CompileError);
		}
	};
	if (!IsInGameThread() || !IsValid(Material))
	{ Error = TEXT("材质ShaderMap只读查询需要GameThread及真实Master"); LogFailure(); return false; }
#if WITH_EDITOR
	const FMaterialResource* Resource = Material->GetMaterialResource(GMaxRHIShaderPlatform);
	if (!Resource)
	{ Error = TEXT("真实Master没有当前RHI MaterialResource"); LogFailure(); return false; }
	CompileErrors = Resource->GetCompileErrors();
	const FMaterialShaderMap* ShaderMap = Resource->GetGameThreadShaderMap();
	bShaderMapComplete = Resource->IsGameThreadShaderMapComplete();
	if (!CompileErrors.IsEmpty() || !bShaderMapComplete || !ShaderMap || !ShaderMap->IsValidForRendering())
	{ Error = TEXT("当前RHI ShaderMap缺失、未完成、不可渲染或有真实编译错误"); LogFailure(); return false; }
	return true;
#else
	Error = TEXT("材质编译诊断只供Editor作者读取");
	LogFailure();
	return false;
#endif
}

FGGYGOMaterialCompilationState UGGYGOProjectedDecalRendererProperties::CompleteMaterialCompilationForAuthoring(
	UMaterialInterface* Material, UWorld* World)
{
	FGGYGOMaterialCompilationState Result;
	Result.MaterialPath = GetPathNameSafe(Material);
	Result.WorldPath = GetPathNameSafe(World);
#if WITH_EDITOR
	if (!IsInGameThread() || !GIsEditor || !IsValid(Material) || !IsValid(World)
		|| World->bIsTearingDown || !World->Scene)
	{ Result.Error = TEXT("材质编译完成需要非归还中的 Editor 原 MaterialInterface/World/Scene 及 GameThread"); return Result; }
	if (GEngine)
		for (const FWorldContext& Context : GEngine->GetWorldContexts())
			if (Context.WorldType == EWorldType::PIE)
			{ Result.Error = TEXT("PIE 期间不执行作者材质编译完成"); return Result; }
	const FSceneInterface* OriginalScene = World->Scene;
	const EShaderPlatform ShaderPlatform = OriginalScene->GetShaderPlatform();
	Result.ShaderPlatform = static_cast<int32>(ShaderPlatform);
	FMaterialResource* Resource = Material->GetMaterialResource(ShaderPlatform);
	if (!Resource)
	{ Result.Error = TEXT("原 MaterialInterface 在本次明确平台没有资源；未使用 fallback"); return Result; }
	const TStrongObjectPtr<UMaterialInterface> OriginalMaterial(Material);
	const TStrongObjectPtr<UWorld> OriginalWorld(World);
	const auto IsOriginalResource = [&]()
	{
		return IsValid(OriginalMaterial.Get()) && IsValid(OriginalWorld.Get()) && !World->bIsTearingDown
			&& World->Scene == OriginalScene && OriginalScene->GetShaderPlatform() == ShaderPlatform
			&& Material->GetMaterialResource(ShaderPlatform) == Resource;
	};
	// 沿该资源的原生编译生命周期完成既有派生工作，不重编整个材质或其它平台。
	if (!Resource->IsGameThreadShaderMapComplete())
	{
		Resource->SubmitCompileJobs_GameThread(EShaderCompileJobPriority::High);
	}
	Resource->FinishCompilation();
	// 两个原生入口都可能完成 CacheShaders 回调；分别核返栈，避免再解引用已被替换的原资源。
	if (!IsOriginalResource())
	{ Result.Error = TEXT("编译完成返栈时原 MaterialInterface/World/Scene/平台或资源已改变"); return Result; }
	const bool bResourceCompilationFinished = Resource->IsCompilationFinished();
	if (!IsOriginalResource())
	{ Result.Error = TEXT("读取编译完成状态返栈时原 MaterialInterface/World/Scene/平台或资源已改变"); return Result; }
	Result.bResourceAvailable = true;
	Result.ResourceMaterialPath = GetPathNameSafe(Resource->GetMaterialInterface());
	Result.CompileErrors = Resource->GetCompileErrors();
	Result.bShaderMapComplete = Resource->IsGameThreadShaderMapComplete();
	const FMaterialShaderMap* Map = Resource->GetGameThreadShaderMap();
	Result.bShaderMapPresent = Map != nullptr;
	// ODSC 冻结快照可保留 false 过程标记；它们只作诊断，不替代资源完成和 shader 内容完整性。
	Result.bCompilationFinalized = Map && Map->IsCompilationFinalized();
	Result.bCompiledSuccessfully = Map && Map->CompiledSuccessfully();
	Result.bValidForRendering = Map && Map->IsValidForRendering(false);
	Result.bReady = bResourceCompilationFinished && Result.CompileErrors.IsEmpty()
		&& Result.bShaderMapComplete && Result.bShaderMapPresent && Result.bValidForRendering;
	if (!Result.bReady)
	{
		Result.Error = FString::Printf(TEXT("原平台材质编译未就绪或失败：ShaderPlatform=%d ResourceFinished=%d GTComplete=%d Map=%d Finalized=%d CompiledSuccessfully=%d ValidForRendering=%d CompileErrors=%d"),
			Result.ShaderPlatform, bResourceCompilationFinished, Result.bShaderMapComplete, Result.bShaderMapPresent, Result.bCompilationFinalized,
			Result.bCompiledSuccessfully, Result.bValidForRendering, Result.CompileErrors.Num());
	}
#else
	Result.Error = TEXT("材质编译完成只供 Editor 作者调用");
#endif
	return Result;
}

bool UGGYGOProjectedDecalRendererProperties::ReadNativeMeshMotionForAuthoring(
	UNiagaraSystem* System, FName EmitterName, int32 RendererIndex, bool& bNeedsPrecise,
	TArray<FName>& CurrentAttributes, TArray<FName>& PreviousAttributes,
	TArray<bool>& CurrentLayoutValid, TArray<bool>& PreviousLayoutValid, FString& Error)
{
	bNeedsPrecise = false;
	CurrentAttributes.Reset();
	PreviousAttributes.Reset();
	CurrentLayoutValid.Reset();
	PreviousLayoutValid.Reset();
	Error.Reset();
	if (!IsInGameThread() || !IsValid(System) || EmitterName.IsNone() || RendererIndex < 0)
	{ Error = TEXT("Native Mesh motion只读查询需要GameThread及准确NS/Emitter/index"); return false; }
#if WITH_EDITORONLY_DATA
	if (System->HasOutstandingCompilationRequests(true) || System->NeedsRequestCompile())
	{ Error = TEXT("原NS编译尚未完成，不能沿旧Renderer布局认证当前输入"); return false; }
#endif
	const UNiagaraMeshRendererProperties* Mesh = nullptr;
	int32 Matches = 0;
	for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
	{
		if (Handle.GetName() != EmitterName) continue;
		++Matches;
		const FVersionedNiagaraEmitterData* Data = Handle.GetEmitterData();
		if (Data && Data->GetRenderers().IsValidIndex(RendererIndex))
			Mesh = Cast<UNiagaraMeshRendererProperties>(Data->GetRenderers()[RendererIndex]);
	}
	if (Matches != 1 || !IsValid(Mesh) || Mesh->GetClass() != UNiagaraMeshRendererProperties::StaticClass()
		|| Mesh->SourceMode != ENiagaraRendererSourceDataMode::Particles)
	{ Error = TEXT("Native Mesh motion需要唯一原Particles-mode标准Mesh renderer"); return false; }
	bNeedsPrecise = Mesh->NeedsPreciseMotionVectors();
	const auto Sorted = Mesh->RendererLayoutWithCustomSorting.GetVFVariables_GameThread();
	const auto Unsorted = Mesh->RendererLayoutWithoutCustomSorting.GetVFVariables_GameThread();
	const FNiagaraVariableAttributeBinding* Current[] = {&Mesh->PositionBinding, &Mesh->ScaleBinding, &Mesh->MeshOrientationBinding};
	const FNiagaraVariableAttributeBinding* Previous[] = {&Mesh->PrevPositionBinding, &Mesh->PrevScaleBinding, &Mesh->PrevMeshOrientationBinding};
	const int32 CurrentSlots[] = {ENiagaraMeshVFLayout::Position, ENiagaraMeshVFLayout::Scale, ENiagaraMeshVFLayout::Rotation};
	const int32 PreviousSlots[] = {ENiagaraMeshVFLayout::PrevPosition, ENiagaraMeshVFLayout::PrevScale, ENiagaraMeshVFLayout::PrevRotation};
	const int32 Components[] = {3, 3, 4};
	const FNiagaraTypeDefinition Types[] = {FNiagaraTypeDefinition::GetPositionDef(),
		FNiagaraTypeDefinition::GetVec3Def(), FNiagaraTypeDefinition::GetQuatDef()};
	const auto HasLayout = [&](const FNiagaraVariableAttributeBinding& Binding, int32 Slot, int32 ComponentCount,
		const FNiagaraTypeDefinition& Type)
	{
		return Binding.DoesBindingExistOnSource() && Binding.GetDataSetBindableVariable().GetType() == Type
			&& Sorted.IsValidIndex(Slot) && Unsorted.IsValidIndex(Slot)
			&& Sorted[Slot].GetRawDatasetOffset() != INDEX_NONE && Unsorted[Slot].GetRawDatasetOffset() != INDEX_NONE
			&& Sorted[Slot].GetNumComponents() == ComponentCount && Unsorted[Slot].GetNumComponents() == ComponentCount;
	};
	bool bValid = true;
	for (int32 Index = 0; Index < 3; ++Index)
	{
		CurrentAttributes.Add(Current[Index]->GetParamMapBindableVariable().GetName());
		PreviousAttributes.Add(Previous[Index]->GetParamMapBindableVariable().GetName());
		const bool bCurrent = HasLayout(*Current[Index], CurrentSlots[Index], Components[Index], Types[Index]);
		const bool bPrevious = bNeedsPrecise && HasLayout(*Previous[Index], PreviousSlots[Index], Components[Index], Types[Index]);
		CurrentLayoutValid.Add(bCurrent);
		PreviousLayoutValid.Add(bPrevious);
		bValid &= bCurrent && (!bNeedsPrecise || bPrevious);
	}
	if (!bValid) Error = TEXT("Native Mesh motion缺真实typed Current/Previous布局；不接受current offset代Prev");
	return bValid;
}

#if WITH_EDITORONLY_DATA
TArray<FNiagaraVariable> UGGYGOProjectedDecalRendererProperties::GetBoundAttributes() const
{
	TArray<FNiagaraVariable> Result = Super::GetBoundAttributes();
	const UNiagaraRendererProperties* Native = NativeDecal.Get();
	if (Native)
		for (const auto& Attribute : Native->GetBoundAttributes()) Result.AddUnique(Attribute);
	for (const FName Name : ParticleVectorAttributes)
		Result.AddUnique(FNiagaraVariable(FNiagaraTypeDefinition::GetVec4Def(), Name));
	return Result;
}
#endif

bool UGGYGOProjectedDecalRendererProperties::ValidatePayloadConfiguration(FString& Error) const
{
	Error.Reset();
	if (!bPayloadConfigured || SourceReference.IsEmpty() || MaxMaterialInstances <= 0
		|| !NativeDecal || NativeDecal->SourceMode != ENiagaraRendererSourceDataMode::Particles || ParticleVectorAttributes.IsEmpty()
		|| ParticleVectorAttributes.Num() != MaterialVectorParameters.Num())
	{ Error = TEXT("投影payload须显式配置原来源、Particles模式、容量及一一对应的向量参数"); return false; }
	// 每粒子值与Age由同次CPU采样提交；不混用另一个per-Emitter更新时点。
	if (NativeDecal->MaterialParameters.HasAnyBindings())
	{ Error = TEXT("投影payload不混用Native per-Emitter MaterialParameters；动态值须列入本合同"); return false; }
	TSet<FName> Attributes, Parameters;
	for (int32 Index = 0; Index < ParticleVectorAttributes.Num(); ++Index)
	{
		const FName Attribute = ParticleVectorAttributes[Index], Parameter = MaterialVectorParameters[Index];
		const FString Text = Attribute.ToString();
		if (!Text.StartsWith(TEXT("Particles.")) || Text.Len() <= 10 || Parameter.IsNone()
			|| Attributes.Contains(Attribute) || Parameters.Contains(Parameter) || Parameter == SimulationAgeParameter)
		{ Error = TEXT("投影payload的命名空间、重复项或Material参数类型合同无效"); return false; }
		Attributes.Add(Attribute);
		Parameters.Add(Parameter);
	}
	return true;
}
