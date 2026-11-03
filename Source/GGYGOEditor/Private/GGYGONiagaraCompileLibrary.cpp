/** @file GGYGONiagaraCompileLibrary.cpp @brief Niagara 有限批量制作、原生编译收束及真实布局诊断。 */
#include "GGYGONiagaraCompileLibrary.h"

#include "FX/Components/GGYGOFXNiagaraComponent.h"
#include "FX/DataInterfaces/GGYGOFXMathDataInterface.h"
#include "EdGraph/EdGraph.h"
#include "EdGraph/EdGraphNode.h"
#include "EdGraph/EdGraphPin.h"
#include "EdGraph/EdGraphSchema.h"
#include "EdGraphSchema_Niagara.h"
#include "NiagaraDataInterface.h"
#include "NiagaraClipboard.h"
#include "NiagaraExternalSystemEditorUtilities.h"
#include "NiagaraGraph.h"
#include "NiagaraNodeAssignment.h"
#include "NiagaraNodeCustomHlsl.h"
#include "NiagaraNodeInput.h"
#include "NiagaraNodeOutput.h"
#include "NiagaraScriptSource.h"
#include "ToolsetRegistry/ToolsetLibrary.h"
#include "UObject/PropertyAccessUtil.h"
#include "UObject/UObjectHash.h"
#include "UObject/UObjectGlobals.h"
#include "UObject/UnrealType.h"
#include "ViewModels/Stack/NiagaraParameterHandle.h"
#include "ViewModels/Stack/NiagaraStackGraphUtilities.h"
#include "ViewModels/NiagaraEmitterHandleViewModel.h"
#include "ViewModels/NiagaraSystemViewModel.h"
#include "ViewModels/Stack/NiagaraStackFunctionInput.h"
#include "ViewModels/Stack/NiagaraStackModuleItem.h"
#include "ViewModels/Stack/NiagaraStackScriptItemGroup.h"
#include "ViewModels/Stack/NiagaraStackViewModel.h"
#include "ScopedTransaction.h"

#include "Editor.h"
#include "Editor/Transactor.h"
#include "FileHelpers.h"
#include "HAL/PlatformMemory.h"
#include "HAL/PlatformProcess.h"
#include "HAL/IConsoleManager.h"
#include "Misc/OutputDeviceRedirector.h"
#include "AssetCompilingManager.h"
#include "IAssetCompilingManager.h"
#include "ShaderCompiler.h"
#include "NiagaraEditorUtilities.h"
#include "NiagaraEditorModule.h"
#include "Modules/ModuleManager.h"
#include "NiagaraNodeFunctionCall.h"
#include "NiagaraRendererProperties.h"
#include "Misc/App.h"
#include "Misc/DateTime.h"
#include "Misc/ScopeExit.h"
#include "Internationalization/Regex.h"
#include "NiagaraEmitter.h"
#include "NiagaraMeshRendererProperties.h"
#include "NiagaraRibbonRendererProperties.h"
#include "NiagaraSpriteRendererProperties.h"
#include "NiagaraUserRedirectionParameterStore.h"
#include "Materials/MaterialInterface.h"
#include "NiagaraScript.h"
#include "NiagaraSettings.h"
#include "NiagaraScriptSourceBase.h"
#include "NiagaraSystem.h"
#include "UObject/StrongObjectPtr.h"
#include "UObject/Package.h"

namespace
{
	FString NiagaraBindingTypePath(const FNiagaraTypeDefinition& Type)
	{
		const UObject* Object = Type.IsValid() ? (Type.IsEnum()
			? static_cast<const UObject*>(Type.GetEnum()) : Type.GetStruct()) : nullptr;
		return GetPathNameSafe(Object);
	}

	void ReadRibbonBindings(const UNiagaraRibbonRendererProperties& Ribbon, FGGYGONiagaraRibbonUniqueIDState& Result)
	{
		Result.bLinkOrderUseUniqueId = Ribbon.bLinkOrderUseUniqueID;
		Result.RibbonLinkOrderAttribute = Ribbon.RibbonLinkOrderBinding.GetParamMapBindableVariable().GetName().ToString();
		Result.RibbonLinkOrderTypePath = NiagaraBindingTypePath(Ribbon.RibbonLinkOrderBinding.GetType());
		Result.RibbonIdAttribute = Ribbon.RibbonIdBinding.GetParamMapBindableVariable().GetName().ToString();
		Result.RibbonIdDataSetAttribute = Ribbon.RibbonIdBinding.GetDataSetBindableVariable().GetName().ToString();
		Result.RibbonIdTypePath = NiagaraBindingTypePath(Ribbon.RibbonIdBinding.GetType());
	}

	bool ReadSpriteBindings(const UNiagaraSpriteRendererProperties& Sprite, bool bReadLayout,
		TArray<FGGYGONiagaraSpriteBindingState>& Current, TArray<FGGYGONiagaraSpriteBindingState>& Previous)
	{
		struct FBindingPair
		{
			const TCHAR* Name;
			const FNiagaraVariableAttributeBinding* Current;
			const FNiagaraVariableAttributeBinding* Previous;
			int32 CurrentSlot;
			int32 PreviousSlot;
			int32 Components;
			FNiagaraTypeDefinition Type;
		};
		const FBindingPair Pairs[] = {
			{TEXT("PositionBinding"), &Sprite.PositionBinding, &Sprite.PrevPositionBinding,
				ENiagaraSpriteVFLayout::Position, ENiagaraSpriteVFLayout::PrevPosition, 3, FNiagaraTypeDefinition::GetPositionDef()},
			{TEXT("VelocityBinding"), &Sprite.VelocityBinding, &Sprite.PrevVelocityBinding,
				ENiagaraSpriteVFLayout::Velocity, ENiagaraSpriteVFLayout::PrevVelocity, 3, FNiagaraTypeDefinition::GetVec3Def()},
			{TEXT("SpriteSizeBinding"), &Sprite.SpriteSizeBinding, &Sprite.PrevSpriteSizeBinding,
				ENiagaraSpriteVFLayout::Size, ENiagaraSpriteVFLayout::PrevSize, 2, FNiagaraTypeDefinition::GetVec2Def()},
			{TEXT("SpriteRotationBinding"), &Sprite.SpriteRotationBinding, &Sprite.PrevSpriteRotationBinding,
				ENiagaraSpriteVFLayout::Rotation, ENiagaraSpriteVFLayout::PrevRotation, 1, FNiagaraTypeDefinition::GetFloatDef()},
			{TEXT("SpriteFacingBinding"), &Sprite.SpriteFacingBinding, &Sprite.PrevSpriteFacingBinding,
				ENiagaraSpriteVFLayout::Facing, ENiagaraSpriteVFLayout::PrevFacing, 3, FNiagaraTypeDefinition::GetVec3Def()},
			{TEXT("SpriteAlignmentBinding"), &Sprite.SpriteAlignmentBinding, &Sprite.PrevSpriteAlignmentBinding,
				ENiagaraSpriteVFLayout::Alignment, ENiagaraSpriteVFLayout::PrevAlignment, 3, FNiagaraTypeDefinition::GetVec3Def()},
			{TEXT("CameraOffsetBinding"), &Sprite.CameraOffsetBinding, &Sprite.PrevCameraOffsetBinding,
				ENiagaraSpriteVFLayout::CameraOffset, ENiagaraSpriteVFLayout::PrevCameraOffset, 1, FNiagaraTypeDefinition::GetFloatDef()},
			{TEXT("PivotOffsetBinding"), &Sprite.PivotOffsetBinding, &Sprite.PrevPivotOffsetBinding,
				ENiagaraSpriteVFLayout::PivotOffset, ENiagaraSpriteVFLayout::PrevPivotOffset, 2, FNiagaraTypeDefinition::GetVec2Def()}
		};
		Current.Reset();
		Previous.Reset();
		const auto Sorted = Sprite.RendererLayoutWithCustomSort.GetVFVariables_GameThread();
		const auto Unsorted = Sprite.RendererLayoutWithoutCustomSort.GetVFVariables_GameThread();
		bool bTypesMatch = true;
		for (const FBindingPair& Pair : Pairs)
		{
			const auto Read = [&](const FNiagaraVariableAttributeBinding& Binding, const FString& PropertyName, int32 Slot)
			{
				FGGYGONiagaraSpriteBindingState Row;
				Row.PropertyName = PropertyName;
				Row.Attribute = Binding.GetParamMapBindableVariable().GetName().ToString();
				Row.DataSetAttribute = Binding.GetDataSetBindableVariable().GetName().ToString();
				Row.TypePath = NiagaraBindingTypePath(Binding.GetType());
				Row.bBindingExistsOnSource = Binding.DoesBindingExistOnSource();
				Row.bIsCachedParticleValue = Binding.IsParticleBinding();
				// 存在标志不代替原生 VF 布局；Previous 可由空 emitter 上下文派生而保持 exists=false。
				Row.bLayoutValid = bReadLayout && Binding.GetType() == Pair.Type
					&& Sorted.IsValidIndex(Slot) && Unsorted.IsValidIndex(Slot)
					&& Sorted[Slot].GetRawDatasetOffset() != INDEX_NONE && Unsorted[Slot].GetRawDatasetOffset() != INDEX_NONE
					&& Sorted[Slot].GetNumComponents() == Pair.Components && Unsorted[Slot].GetNumComponents() == Pair.Components;
				return Row;
			};
			Current.Add(Read(*Pair.Current, Pair.Name, Pair.CurrentSlot));
			Previous.Add(Read(*Pair.Previous, FString(TEXT("Prev")) + Pair.Name, Pair.PreviousSlot));
			bTypesMatch &= Pair.Current->GetType() == Pair.Type && Pair.Previous->GetType() == Pair.Type;
		}
		return bTypesMatch;
	}

	UNiagaraRibbonRendererProperties* ResolveRibbonRenderer(UNiagaraSystem* System, const FString& EmitterName,
		int32 RendererIndex, FGGYGONiagaraRibbonUniqueIDState& Result)
	{
		Result.SystemPath = GetPathNameSafe(System);
		Result.EmitterName = EmitterName;
		Result.RendererIndex = RendererIndex;
		if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || !IsValid(System) || System->IsTemplate() || EmitterName.IsEmpty())
		{ Result.Error = TEXT("Ribbon 查询需要非 PIE Editor 的准确原 System/Emitter/renderer 槽。"); return nullptr; }
		const FNiagaraEmitterHandle* Found = nullptr;
		for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
		{
			if (Handle.GetName().ToString() != EmitterName) { continue; }
			if (Found) { Result.Error = TEXT("Ribbon 原 emitter 名称不唯一。"); return nullptr; }
			Found = &Handle;
		}
		const FVersionedNiagaraEmitterData* Data = Found ? Found->GetEmitterData() : nullptr;
		if (!Found || !Found->GetId().IsValid() || !Found->GetIsEnabled() || !Data
			|| Data->SimTarget != ENiagaraSimTarget::CPUSim || !Data->GetRenderers().IsValidIndex(RendererIndex))
		{ Result.Error = TEXT("Ribbon 缺少 enabled CPU emitter 或准确 renderer 槽。"); return nullptr; }
		auto* Ribbon = Cast<UNiagaraRibbonRendererProperties>(Data->GetRenderers()[RendererIndex]);
		if (!IsValid(Ribbon) || Ribbon->GetClass() != UNiagaraRibbonRendererProperties::StaticClass() || Ribbon->IsTemplate())
		{ Result.Error = TEXT("原 renderer 槽不是标准 Native Ribbon 实例。"); return nullptr; }
		Result.EmitterHandleId = Found->GetId();
		Result.RendererPath = Ribbon->GetPathName();
		Result.RendererClass = Ribbon->GetClass()->GetPathName();
		return Ribbon;
	}
}

FGGYGONiagaraSpriteMotionSupport UGGYGONiagaraCompileLibrary::ReadSpriteMotionSupport()
{
	FGGYGONiagaraSpriteMotionSupport Result;
	if (!IsInGameThread()) { Result.Error = TEXT("Sprite 支持查询需要 GameThread。"); return Result; }
	const auto* Defaults = GetDefault<UNiagaraSpriteRendererProperties>();
	Result.RendererClass = Defaults->GetClass()->GetPathName();
	const UFunction* Read = StaticClass()->FindFunctionByName(TEXT("ReadSpriteMotionState"));
	if (!Read || !Read->HasAllFunctionFlags(FUNC_Native) || Read->NumParms != 4
		|| !ReadSpriteBindings(*Defaults, false, Result.CurrentBindings, Result.PreviousBindings))
	{ Result.Error = TEXT("实际 Sprite CDO 或本 DLL 缺少八组 typed current/previous 只读接口。"); return Result; }
	Result.bSupported = true;
	return Result;
}

FGGYGONiagaraSpriteMotionState UGGYGONiagaraCompileLibrary::ReadSpriteMotionState(UNiagaraSystem* System,
	const FString& EmitterName, int32 RendererIndex)
{
	FGGYGONiagaraSpriteMotionState Result;
	Result.SystemPath = GetPathNameSafe(System);
	Result.EmitterName = EmitterName;
	Result.RendererIndex = RendererIndex;
	if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || !IsValid(System) || System->IsTemplate())
	{ Result.Error = TEXT("Sprite 编译查询需要非 PIE Editor 的准确原 System。"); return Result; }
	const auto Layout = ReadEmitterDataSetAttributes(System, EmitterName);
	if (!Layout.bReady) { Result.Error = Layout.Error; return Result; }
	// 原 DataSet 入口已核唯一 enabled CPU handle、当前源图及编译索引；本段不触发外调或刷新。
	const FVersionedNiagaraEmitterData* Data = System->GetEmitterHandles()[Layout.HandleIndex].GetEmitterData();
	const auto* Sprite = Data->GetRenderers().IsValidIndex(RendererIndex)
		? Cast<UNiagaraSpriteRendererProperties>(Data->GetRenderers()[RendererIndex]) : nullptr;
	if (!IsValid(Sprite) || Sprite->GetClass() != UNiagaraSpriteRendererProperties::StaticClass())
	{ Result.Error = TEXT("原 emitter 槽不是准确标准 Native Sprite renderer。"); return Result; }
	Result.EmitterHandleId = Layout.EmitterHandleId;
	Result.RendererPath = Sprite->GetPathName();
	Result.RendererClass = Sprite->GetClass()->GetPathName();
	Result.SourceMode = StaticEnum<ENiagaraRendererSourceDataMode>()->GetNameStringByValue(static_cast<int64>(Sprite->SourceMode));
	Result.bNeedsPreciseMotionVectors = Sprite->NeedsPreciseMotionVectors();
	if (!ReadSpriteBindings(*Sprite, true, Result.CurrentBindings, Result.PreviousBindings))
	{ Result.Error = TEXT("Sprite 当前绑定或派生 previous 的实际类型与 Native VF 不符。"); return Result; }
	Result.bReady = true;
	return Result;
}

FGGYGONiagaraRibbonUniqueIDSupport UGGYGONiagaraCompileLibrary::ReadRibbonUniqueIDSupport()
{
	FGGYGONiagaraRibbonUniqueIDSupport Result;
	if (!IsInGameThread()) { Result.Error = TEXT("Ribbon 支持查询需要 GameThread。"); return Result; }
	const auto* Defaults = GetDefault<UNiagaraRibbonRendererProperties>();
	Result.RendererClass = Defaults->GetClass()->GetPathName();
	Result.bDefaultLinkOrderUseUniqueId = Defaults->bLinkOrderUseUniqueID;
	Result.DefaultRibbonIdTypePath = NiagaraBindingTypePath(Defaults->RibbonIdBinding.GetType());
	const FBoolProperty* Flag = FindFProperty<FBoolProperty>(Defaults->GetClass(),
		GET_MEMBER_NAME_CHECKED(UNiagaraRibbonRendererProperties, bLinkOrderUseUniqueID));
	const UFunction* Configure = StaticClass()->FindFunctionByName(TEXT("ConfigureRibbonUniqueID"));
	const UFunction* Read = StaticClass()->FindFunctionByName(TEXT("ReadRibbonUniqueIDState"));
	if (!Flag || Defaults->RibbonIdBinding.GetType() != FNiagaraTypeDefinition::GetIDDef()
		|| !Configure || !Configure->HasAllFunctionFlags(FUNC_Native) || Configure->NumParms != 5
		|| !Read || !Read->HasAllFunctionFlags(FUNC_Native) || Read->NumParms != 4)
	{ Result.Error = TEXT("实际 Ribbon CDO 或本 DLL 缺少 UniqueID/完整 NiagaraID typed 作者接口。"); return Result; }
	Result.bSupported = true;
	return Result;
}

FGGYGONiagaraRibbonUniqueIDState UGGYGONiagaraCompileLibrary::ConfigureRibbonUniqueID(UNiagaraSystem* System,
	const FString& EmitterName, int32 RendererIndex, const FString& RibbonIdAttribute)
{
	FGGYGONiagaraRibbonUniqueIDState Result;
	auto* Ribbon = ResolveRibbonRenderer(System, EmitterName, RendererIndex, Result);
	if (!Ribbon) { return Result; }
	if (!RibbonIdAttribute.IsEmpty() && (!RibbonIdAttribute.StartsWith(TEXT("Particles.")) || RibbonIdAttribute.Len() <= 10))
	{ Result.Error = TEXT("Ribbon ID 必须是准确 Particles 属性；空串只表示显式解绑。"); return Result; }
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	const TStrongObjectPtr<UNiagaraRibbonRendererProperties> OriginalRenderer(Ribbon);
	const auto IsOriginalRenderer = [&]()
	{
		FGGYGONiagaraRibbonUniqueIDState Current;
		return ResolveRibbonRenderer(System, EmitterName, RendererIndex, Current) == Ribbon
			&& Current.EmitterHandleId == Result.EmitterHandleId;
	};
	System->Modify();
	Ribbon->Modify();
	if (!IsOriginalRenderer()) { Result.Error = TEXT("Modify 期间原 Ribbon 身份改变。"); return Result; }
	Ribbon->bLinkOrderUseUniqueID = true;
	Ribbon->RibbonLinkOrderBinding.Setup(FNiagaraVariableBase(FNiagaraTypeDefinition::GetFloatDef(), NAME_None),
		FNiagaraVariable(FNiagaraTypeDefinition::GetFloatDef(), NAME_None));
	const FName IdName = RibbonIdAttribute.IsEmpty() ? NAME_None : FName(*RibbonIdAttribute);
	Ribbon->RibbonIdBinding.Setup(FNiagaraVariableBase(FNiagaraTypeDefinition::GetIDDef(), IdName),
		FNiagaraVariable(FNiagaraTypeDefinition::GetIDDef(), NAME_None));
	Ribbon->PostEditChange();
	if (!IsOriginalRenderer()) { Result.Error = TEXT("Editor 通知后原 Ribbon 身份改变。"); return Result; }
	System->MarkPackageDirty();
	if (!IsOriginalRenderer()) { Result.Error = TEXT("标记 dirty 后原 Ribbon 身份改变。"); return Result; }
	ReadRibbonBindings(*Ribbon, Result);
	if (!Result.bLinkOrderUseUniqueId || Ribbon->RibbonLinkOrderBinding.IsValid()
		|| Ribbon->RibbonLinkOrderBinding.GetType() != FNiagaraTypeDefinition::GetFloatDef()
		|| Ribbon->RibbonIdBinding.GetParamMapBindableVariable().GetName() != IdName
		|| Ribbon->RibbonIdBinding.GetType() != FNiagaraTypeDefinition::GetIDDef())
	{ Result.Error = TEXT("Ribbon UniqueID 排序或完整 NiagaraID 绑定写后读回不符。"); return Result; }
	Result.bApplied = true;
	return Result;
}

FGGYGONiagaraRibbonUniqueIDState UGGYGONiagaraCompileLibrary::ReadRibbonUniqueIDState(UNiagaraSystem* System,
	const FString& EmitterName, int32 RendererIndex)
{
	FGGYGONiagaraRibbonUniqueIDState Result;
	const auto* Ribbon = ResolveRibbonRenderer(System, EmitterName, RendererIndex, Result);
	if (!Ribbon) { return Result; }
	ReadRibbonBindings(*Ribbon, Result);
	const auto Layout = ReadEmitterDataSetAttributes(System, EmitterName);
	if (!Layout.bReady || Layout.EmitterHandleId != Result.EmitterHandleId)
	{ Result.Error = TEXT("Ribbon 编译快照尚未就绪或 emitter 身份不同：") + Layout.Error; return Result; }
	int32 UniqueIDCount = 0;
	for (const FGGYGONiagaraDataSetAttribute& Attribute : Layout.Attributes)
	{
		if (Attribute.Name != FName(TEXT("UniqueID"))) { continue; }
		++UniqueIDCount;
		Result.UniqueIdTypePath = Attribute.TypePath;
	}
	if (UniqueIDCount != 1 || Result.UniqueIdTypePath != NiagaraBindingTypePath(FNiagaraTypeDefinition::GetIntDef()))
	{ Result.Error = TEXT("Ribbon 当前编译 DataSet 缺少唯一 Int32 UniqueID。"); return Result; }
	Result.bInt32LinkOrderAccessorValid = Ribbon->RibbonLinkOrderInt32Accessor.IsValid();
	Result.bFloatLinkOrderAccessorValid = Ribbon->RibbonLinkOrderFloatAccessor.IsValid();
	Result.bInt32RibbonIdAccessorValid = Ribbon->RibbonIdDataSetAccessor.IsValid();
	Result.bFullRibbonIdAccessorValid = Ribbon->RibbonFullIDDataSetAccessor.IsValid();
	Result.bReady = true;
	return Result;
}

bool UGGYGONiagaraCompileLibrary::ReadMeshUserMaterialSupport()
{
	const UFunction* Function = StaticClass()->FindFunctionByName(TEXT("BindMeshUserMaterial"));
	return Function && Function->HasAllFunctionFlags(FUNC_Native) && Function->NumParms == 6;
}

FGGYGONiagaraUserMaterialBinding UGGYGONiagaraCompileLibrary::BindMeshUserMaterial(UNiagaraSystem* System,
	const FString& EmitterName, int32 RendererIndex, const FString& ParameterName, UMaterialInterface* Material)
{
	FGGYGONiagaraUserMaterialBinding Result;
	Result.SystemPath = GetPathNameSafe(System);
	Result.EmitterName = EmitterName;
	Result.RendererIndex = RendererIndex;
	Result.ParameterName = ParameterName;
	Result.MaterialPath = GetPathNameSafe(Material);
	const FNiagaraVariable Parameter(FNiagaraTypeDefinition::GetUMaterialDef(), FName(*ParameterName));
	if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || !IsValid(System) || !IsValid(Material)
		|| System->IsTemplate() || !FNameBuilder(Parameter.GetName()).ToView().StartsWith(TEXT("User.")))
	{ Result.Error = TEXT("UserMaterial接线需要非PIE Editor中的准确原NS/Material/User参数"); return Result; }
	UNiagaraMeshRendererProperties* Mesh = nullptr;
	FGuid EmitterId;
	int32 Matches = 0;
	for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
	{
		if (Handle.GetName().ToString() != EmitterName) { continue; }
		++Matches;
		EmitterId = Handle.GetId();
		const FVersionedNiagaraEmitterData* Data = Handle.GetEmitterData();
		if (Data && Data->GetRenderers().IsValidIndex(RendererIndex))
			Mesh = Cast<UNiagaraMeshRendererProperties>(Data->GetRenderers()[RendererIndex]);
	}
	if (Matches != 1 || !IsValid(Mesh) || Mesh->GetClass() != UNiagaraMeshRendererProperties::StaticClass()
		|| Mesh->SourceMode != ENiagaraRendererSourceDataMode::Emitter || !Mesh->bOverrideMaterials
		|| Mesh->OverrideMaterials.Num() != 1 || Mesh->OverrideMaterials[0].ExplicitMat != Material)
	{ Result.Error = TEXT("UserMaterial需要唯一原Emitter/标准Mesh renderer及准确单槽ExplicitMat"); return Result; }
	const FNiagaraVariable& Existing = Mesh->OverrideMaterials[0].UserParamBinding.Parameter;
	if (Existing.IsValid() && Existing != Parameter)
	{ Result.Error = TEXT("原Mesh renderer已有其它UserMaterial绑定"); return Result; }
	FNiagaraUserRedirectionParameterStore& Store = System->GetExposedParameters();
	for (const FNiagaraVariableWithOffset& Value : Store.ReadParameterVariables())
		if (Value.GetName() == Parameter.GetName() && Value.GetType() != Parameter.GetType())
		{ Result.Error = TEXT("同名用户参数已有其它类型"); return Result; }
	if (Store.IndexOf(Parameter) != INDEX_NONE && Store.GetUObject(Parameter).Get() != Material)
	{ Result.Error = TEXT("原NS的UserMaterial已有其它材质值"); return Result; }
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	const TStrongObjectPtr<UNiagaraMeshRendererProperties> OriginalRenderer(Mesh);
	const TStrongObjectPtr<UMaterialInterface> OriginalMaterial(Material);
	const auto IsOriginalRenderer = [&]()
	{
		if (!IsValid(System) || !IsValid(Mesh) || !IsValid(Material) || System->GetPathName() != Result.SystemPath) { return false; }
		for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
		{
			if (Handle.GetId() != EmitterId || Handle.GetName().ToString() != EmitterName) { continue; }
			const FVersionedNiagaraEmitterData* Data = Handle.GetEmitterData();
			return Data && Data->GetRenderers().IsValidIndex(RendererIndex) && Data->GetRenderers()[RendererIndex] == Mesh;
		}
		return false;
	};
	System->Modify();
	Mesh->Modify();
	if (!IsOriginalRenderer()) { Result.Error = TEXT("Modify期间原Emitter/renderer已改变"); return Result; }
	if (Store.IndexOf(Parameter) == INDEX_NONE) { Store.AddParameter(Parameter, false); }
	Store.SetUObject(Material, Parameter);
	Mesh->OverrideMaterials[0].UserParamBinding.Parameter = Parameter;
	Mesh->PostEditChange();
	if (!IsOriginalRenderer() || Mesh->OverrideMaterials.Num() != 1
		|| Mesh->OverrideMaterials[0].UserParamBinding.Parameter != Parameter
		|| Store.GetUObject(Parameter).Get() != Material)
	{ Result.Error = TEXT("原UserMaterial参数/renderer写后读回不符"); return Result; }
	System->MarkPackageDirty();
	Result.bApplied = true;
	return Result;
}

FGGYGONiagaraAuthoringCompilationSettings UGGYGONiagaraCompileLibrary::ReadAuthoringCompilationSettings(UNiagaraSystem* System)
{
	FGGYGONiagaraAuthoringCompilationSettings Result;
	Result.SystemPath = GetPathNameSafe(System);
	if (!IsInGameThread() || !IsValid(System))
	{
		Result.Error = TEXT("编译表示查询需要 GameThread 上的有效原 Niagara System。");
		return Result;
	}
	Result.bCompileForEdit = System->GetCompileForEdit();
	Result.bUsesRapidIterationParameters = System->ShouldUseRapidIterationParameters();
	Result.bSucceeded = true;
	return Result;
}

FGGYGONiagaraAuthoringCompilationSettings UGGYGONiagaraCompileLibrary::ConfigureAuthoringCompilation(
	UNiagaraSystem* System, bool bUseRapidIterationParameters)
{
	FGGYGONiagaraAuthoringCompilationSettings Result;
	Result.SystemPath = GetPathNameSafe(System);
	if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || !IsValid(System) || System->IsTemplate())
	{
		Result.Error = TEXT("编译表示配置需要非 PIE Editor GameThread 上的准确原 Niagara System。");
		return Result;
	}
	auto& NiagaraEditor = FModuleManager::LoadModuleChecked<FNiagaraEditorModule>(TEXT("NiagaraEditor"));
	if (GEditor->IsTransactionActive() || NiagaraEditor.GetExistingViewModelForSystem(System).IsValid())
	{
		Result.Error = TEXT("已有作者 VM 或 Editor 活动事务，不能修改持久编译表示。");
		return Result;
	}
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	System->Modify();
	System->PreEditChange(nullptr);
	// 公开 setter 同时设置 Edit/Cook 两旗；保留 CompileForEdit、trim 和 debug switch 的原语义。
	System->SetBakeOutRapidIterationOnCook(!bUseRapidIterationParameters);
	System->PostEditChange();
	Result = ReadAuthoringCompilationSettings(OriginalSystem.Get());
	if (Result.bSucceeded && Result.bUsesRapidIterationParameters != bUseRapidIterationParameters)
	{
		Result.bSucceeded = false;
		Result.Error = TEXT("原 Niagara System 的实际 RI 编译表示与请求不一致，停止制作。");
	}
	return Result;
}

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

FGGYGONiagaraCompileDiagnostics UGGYGONiagaraCompileLibrary::ReadSystemCompileDiagnostics(UNiagaraSystem* System)
{
	FGGYGONiagaraCompileDiagnostics Result;
	Result.SystemPath = GetPathNameSafe(System);
	if (!IsInGameThread() || !IsValid(System))
	{
		Result.Error = TEXT("完整 Niagara 编译诊断需要 GameThread 上的有效原资产。");
		return Result;
	}
	// 原 getter 只需 CheckSystem；带 System 的 Context 构造会经 VM 初始化重新请求编译。
	FNiagaraExternalEditContext Context;
	UNiagaraExternalEditUtilities::GetSystemCompileState(System, Result.CompileState, Context);
	for (const FText& Item : Context.Errors)
	{
		if (!Result.Error.IsEmpty()) { Result.Error += LINE_TERMINATOR; }
		Result.Error += Item.ToString();
	}
	Result.bSucceeded = !Context.HasErrors();
	return Result;
}

FGGYGONiagaraEmitterDataSetState UGGYGONiagaraCompileLibrary::ReadEmitterDataSetAttributes(
	UNiagaraSystem* System, const FString& EmitterName)
{
	FGGYGONiagaraEmitterDataSetState Result;
	Result.EmitterName = FName(*EmitterName);
	Result.SystemState = ReadSystemState(System);
	const FGGYGONiagaraCompileState& State = Result.SystemState;
	if (!State.Error.IsEmpty() || !State.bSystemValid || !State.bNativeReady || State.bCompilationPending
		|| State.bNeedsCompileRequest || State.bActiveCompilations || Result.EmitterName.IsNone())
	{ Result.Error = TEXT("完整 DataSet 查询需要 GameThread 上有效、无待编译请求且 Native Ready 的准确源 NS/Emitter。"); return Result; }

	const auto& Handles = System->GetEmitterHandles();
	for (int32 Index = 0; Index < Handles.Num(); ++Index)
	{
		if (Handles[Index].GetName() == Result.EmitterName)
		{
			if (Result.HandleIndex != INDEX_NONE)
			{ Result.Error = TEXT("源 emitter handle 名称不唯一。"); return Result; }
			Result.HandleIndex = Index;
		}
	}
	if (Result.HandleIndex == INDEX_NONE)
	{ Result.Error = TEXT("找不到准确源 emitter handle。"); return Result; }
	const FNiagaraEmitterHandle& Handle = Handles[Result.HandleIndex];
	const FVersionedNiagaraEmitterData* Data = Handle.GetEmitterData();
	const UNiagaraEmitter* Emitter = Handle.GetInstance().Emitter;
	Result.EmitterHandleId = Handle.GetId();
	if (!Result.EmitterHandleId.IsValid() || !Handle.GetIsEnabled() || !Data || !IsValid(Emitter)
		|| Data->SimTarget != ENiagaraSimTarget::CPUSim)
	{ Result.Error = TEXT("完整 DataSet 查询只接受 enabled 标准 CPU emitter。"); return Result; }
	Result.EmitterName = Handle.GetName();
	Result.UniqueEmitterName = Emitter->GetUniqueEmitterName();
	const UNiagaraScript* Spawn = Data->SpawnScriptProps.Script;
	const UNiagaraScript* Update = Data->UpdateScriptProps.Script;
	if (Result.UniqueEmitterName.IsEmpty() || !IsValid(Spawn) || !IsValid(Update)
		|| !Spawn->IsReadyToRun(ENiagaraSimTarget::CPUSim) || !Update->IsReadyToRun(ENiagaraSimTarget::CPUSim)
		|| !Spawn->AreScriptAndSourceSynchronized() || !Update->AreScriptAndSourceSynchronized())
	{ Result.Error = TEXT("源 CPU Spawn/Update 缺失、未就绪或与当前源图不同步，不能读取旧字段。"); return Result; }

	const auto& CompiledEmitters = System->GetEmitterCompiledData();
	if (CompiledEmitters.Num() != Handles.Num() || !CompiledEmitters.IsValidIndex(Result.HandleIndex))
	{ Result.Error = TEXT("源 handle 与完整 compiled emitter 索引集合不一致。"); return Result; }
	const FNiagaraDataSetCompiledData& DataSet = CompiledEmitters[Result.HandleIndex]->DataSetCompiledData;
	if (Handle.GetIdName().IsNone() || DataSet.ID.Name != Handle.GetIdName() || DataSet.ID.Type != ENiagaraDataSetType::ParticleData
		|| DataSet.SimTarget != ENiagaraSimTarget::CPUSim || DataSet.Variables.IsEmpty())
	{ Result.Error = TEXT("源粒子 DataSet 身份、CPU 类型或实际字段清单无效。"); return Result; }
	TArray<FNiagaraVariableBase> SourceAttributes;
	Data->GatherCompiledParticleAttributes(SourceAttributes);
	if (SourceAttributes != DataSet.Variables)
	{ Result.Error = TEXT("源脚本当前完整属性与 runtime 初始化使用的 DataSet 不一致。"); return Result; }

	TArray<FGGYGONiagaraDataSetAttribute> Attributes;
	Attributes.Reserve(DataSet.Variables.Num());
	for (const FNiagaraVariableBase& Variable : DataSet.Variables)
	{
		const FNiagaraTypeDefinition& Type = Variable.GetType();
		const UObject* TypeObject = nullptr;
		if (Type.IsValid())
			TypeObject = Type.IsEnum() ? static_cast<const UObject*>(Type.GetEnum()) : Type.GetStruct();
		if (Variable.GetName().IsNone() || !IsValid(TypeObject))
		{ Result.Error = TEXT("源 DataSet 含无效名称或真实类型，拒绝发布部分清单。"); return Result; }
		auto& Attribute = Attributes.AddDefaulted_GetRef();
		Attribute.Name = Variable.GetName();
		Attribute.TypePath = TypeObject->GetPathName();
	}
	Result.DataSetName = DataSet.ID.Name;
	Result.bRequiresPersistentIDs = DataSet.bRequiresPersistentIDs;
	Result.Attributes = MoveTemp(Attributes);
	Result.bReady = true;
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
	FAssetCompilingManager::Get().ProcessAsyncTasks(false);
	return ReadSystemState(OriginalSystem.Get());
}

namespace
{
	void LogForceCompileBoundary(UNiagaraSystem* System, const TCHAR* Phase, bool bRequested)
	{
		TArray<UPackage*> ContentPackages;
		TArray<UPackage*> MapPackages;
		FEditorFileUtils::GetDirtyContentPackages(ContentPackages);
		FEditorFileUtils::GetDirtyWorldPackages(MapPackages);
		TArray<FString> ContentPaths;
		TArray<FString> MapPaths;
		for (const UPackage* Package : ContentPackages) { ContentPaths.Add(Package->GetName()); }
		for (const UPackage* Package : MapPackages) { MapPaths.Add(Package->GetName()); }
		ContentPaths.Sort(); MapPaths.Sort();
		const UPackage* Target = System->GetOutermost();
		UE_LOG(LogTemp, Display, TEXT("Niagara ForceCompile 边界：Phase=%s PID=%u UTC=%s System=%s TargetPackage=%s TargetDirty=%d Requested=%d CurrentEditorDirtyContent=[%s] CurrentEditorDirtyMaps=[%s]；仅此时点，不替代阻塞期间dirty读回。"),
			Phase, FPlatformProcess::GetCurrentProcessId(), *FDateTime::UtcNow().ToIso8601(), *System->GetPathName(),
			*Target->GetName(), Target->IsDirty(), bRequested, *FString::Join(ContentPaths, TEXT(",")), *FString::Join(MapPaths, TEXT(",")));
		if (GLog) { GLog->FlushThreadedLogs(); GLog->Flush(); }
	}
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
	bool bRequested = false;
	LogForceCompileBoundary(System, TEXT("BeforeRequest"), bRequested);
	ON_SCOPE_EXIT { LogForceCompileBoundary(OriginalSystem.Get(), TEXT("Return"), bRequested); };
	bRequested = System->RequestCompile(true);
	if (!bRequested)
	{
		Result = ReadSystemState(System);
		Result.Error = TEXT("Niagara 原生 RequestCompile(true) 未发出完整编译请求。");
		return Result;
	}
	System->WaitForCompilationComplete(true, false);
	// 让原资源编译管理器退役已提取任务；不引入 World Tick 或另一套编译调度。
	FAssetCompilingManager::Get().ProcessAsyncTasks(false);
	Result = ReadSystemState(OriginalSystem.Get());
	Result.bForceCompileRequested = true;
	return Result;
}

namespace
{
	void LogAuthoringMemoryBoundary(UNiagaraSystem* System, const TCHAR* Phase,
		const FString& EmitterName = FString(), int32 RendererIndex = INDEX_NONE)
	{
		int32 NiagaraQueuedAndActive = INDEX_NONE;
		for (const IAssetCompilingManager* Manager : FAssetCompilingManager::Get().GetRegisteredManagers())
		{
			if (Manager->GetAssetTypeName() == FName(TEXT("UE-NiagaraSystem")))
			{
				// 原公开计数不含已完成但等待提取的请求，不能将其0写成全部任务内存已释放。
				NiagaraQueuedAndActive = Manager->GetNumRemainingAssets();
				break;
			}
		}
		const UTransactor* Transactions = GEditor ? GEditor->Trans.Get() : nullptr;
		const FPlatformMemoryStats Memory = FPlatformMemory::GetStats();
		UE_LOG(LogTemp, Display, TEXT("Niagara 制作内存边界：Phase=%s System=%s Emitters=%d Emitter=%s Renderer=%d UECommitBytes=%llu UEWorkingSetBytes=%llu UndoAvailable=%d UndoBytes=%llu UndoTransactions=%d NiagaraQueuedAndActive=%d；Undo序列化量与队列计数不等于保活对象或进程全部内存。"),
			Phase, *GetPathNameSafe(System), System->GetEmitterHandles().Num(), *EmitterName, RendererIndex,
			static_cast<uint64>(Memory.UsedVirtual), static_cast<uint64>(Memory.UsedPhysical), static_cast<int32>(Transactions != nullptr),
			Transactions ? static_cast<uint64>(Transactions->GetUndoSize()) : 0,
			Transactions ? Transactions->GetQueueLength() : INDEX_NONE, NiagaraQueuedAndActive);
	}

	IConsoleVariable* FindAuthoringCompileTaskLimit()
	{
		if (!IsInGameThread() || !GEditor || GEditor->PlayWorld)
		{
			UE_LOG(LogTemp, Error, TEXT("制作编译限额只供非 PIE Editor GameThread 的独占生产窗口使用。"));
			return nullptr;
		}
		IConsoleVariable* Limit = IConsoleManager::Get().FindConsoleVariable(TEXT("fx.Niagara.Compilation.MaxActiveTaskCount"));
		if (!Limit) { UE_LOG(LogTemp, Error, TEXT("当前软件缺少原生 Niagara 编译任务限额。")); }
		return Limit;
	}
}

int32 UGGYGONiagaraCompileLibrary::GetAuthoringCompileTaskLimit()
{
	const IConsoleVariable* Limit = FindAuthoringCompileTaskLimit();
	return Limit ? Limit->GetInt() : INDEX_NONE;
}

bool UGGYGONiagaraCompileLibrary::TrySetAuthoringCompileTaskLimit(int32 ExpectedLimit, int32 NewLimit)
{
	IConsoleVariable* Limit = FindAuthoringCompileTaskLimit();
	if (!Limit) { return false; }
	// 仅借用已配置的单活动 System 任务限额；原值与恢复义务由同步制作段的调用方持有。
	if (!((ExpectedLimit == 1 && NewLimit == 0) || (ExpectedLimit == 0 && NewLimit == 1))
		|| Limit->GetInt() != ExpectedLimit)
	{
		UE_LOG(LogTemp, Error, TEXT("制作编译限额交接不符：Expected=%d Actual=%d Requested=%d。"),
			ExpectedLimit, Limit->GetInt(), NewLimit);
		return false;
	}
	if (NewLimit == 0 && GetDefault<UNiagaraSettings>()->CompilationMode != ENiagaraCompilationMode::AsyncTasks)
	{
		UE_LOG(LogTemp, Error, TEXT("当前 Niagara 编译后端不受此任务限额控制，拒绝暂停启动；不自动切换编译模式。"));
		return false;
	}
	const EConsoleVariableFlags Priority = static_cast<EConsoleVariableFlags>(Limit->GetFlags() & ECVF_SetByMask);
	// 公开接口保留原优先级及 tag；不覆盖配置层级或建立另一个调度器。
	Limit->ReplaceCurrentPriorityAndTag(NewLimit, Priority, Priority);
	const bool bApplied = Limit->GetInt() == NewLimit && (Limit->GetFlags() & ECVF_SetByMask) == Priority;
	UE_LOG(LogTemp, Display, TEXT("Niagara 制作编译限额：Previous=%d Requested=%d Actual=%d Applied=%d Priority=%u"),
		ExpectedLimit, NewLimit, Limit->GetInt(), static_cast<int32>(bApplied), static_cast<uint32>(Priority));
	return bApplied;
}

FGGYGONiagaraCompileState UGGYGONiagaraCompileLibrary::CompileAuthoringBatch(UNiagaraSystem* System)
{
	FGGYGONiagaraCompileState Result;
	Result.SystemPath = GetPathNameSafe(System);
	if (!IsInGameThread() || !IsValid(System) || !GEditor || GEditor->PlayWorld || !FApp::CanEverRender())
	{
		Result.Error = TEXT("分批编译需要非 PIE、可渲染 Editor GameThread 上的有效原 NS。");
		return Result;
	}
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	auto& NiagaraEditor = FModuleManager::LoadModuleChecked<FNiagaraEditorModule>(TEXT("NiagaraEditor"));
	if (GEditor->IsTransactionActive() || NiagaraEditor.GetExistingViewModelForSystem(System).IsValid())
	{
		Result.Error = TEXT("有限制作批尚未归还作者 VM/事务，不能进入批间编译。");
		return Result;
	}
	if (GetAuthoringCompileTaskLimit() <= 0)
	{
		Result.Error = TEXT("原生 Niagara 编译启动限额尚未归还为正值，不能进入批间等待。");
		return Result;
	}
	const UNiagaraScript* Spawn = System->GetSystemSpawnScript();
	const UNiagaraScript* Update = System->GetSystemUpdateScript();
	if (!Spawn || !Update || !IsValid(Spawn->GetLatestSource())
		|| Spawn->GetLatestSource() != Update->GetLatestSource())
	{
		Result.Error = TEXT("分批编译需要 Spawn/Update 共享有效原 System 源图。");
		return Result;
	}
	for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
	{
		const FVersionedNiagaraEmitterData* Data = Handle.GetEmitterData();
		if (Data && !IsValid(Data->GraphSource))
		{
			Result.Error = FString::Printf(TEXT("分批编译缺少 Emitter '%s' 的原源图。"), *Handle.GetName().ToString());
			return Result;
		}
	}
	LogAuthoringMemoryBoundary(System, TEXT("BatchBeforeCompile"));
	ON_SCOPE_EXIT { LogAuthoringMemoryBoundary(OriginalSystem.Get(), TEXT("BatchReturn")); };
	UE_LOG(LogTemp, Display, TEXT("Niagara 分批编译表示：System=%s CompileForEdit=%d UsesRI=%d"),
		*Result.SystemPath, static_cast<int32>(System->GetCompileForEdit()),
		static_cast<int32>(System->ShouldUseRapidIterationParameters()));
	// 原生按当前图/依赖决定需要编译的脚本；不主动强制换缓存键，保留原生失败/重试语义。
	const bool bRequested = System->RequestCompile(false);
	UE_LOG(LogTemp, Display, TEXT("Niagara 分批编译请求：System=%s Emitters=%d Requested=%d"),
		*Result.SystemPath, System->GetEmitterHandles().Num(), static_cast<int32>(bRequested));
	// 等当前原 NS 的最新请求，也让原生 FIFO 中先前已失效请求完成退役；Abort 本身不代表释放。
	Result = CompletePendingCompilation(OriginalSystem.Get());
	if (Result.Error.IsEmpty())
	{
		if (!GShaderCompilingManager)
		{
			Result.Error = TEXT("分批编译缺少当前 Editor 的原生 Shader 编译管理器。");
		}
		else
		{
			// VM Ready 只覆盖本 NS；原生 renderer/材质通知还可能留下 Editor Shader 工作。
			const int32 BeforeShaderJobs = GShaderCompilingManager->GetNumRemainingJobs();
			const bool bBeforeShaderMaps = GShaderCompilingManager->HasShaderJobs();
			GShaderCompilingManager->FinishAllCompilation();
			// Shader 结果的回调可能更新原资产；仍由原 NS 等待入口处理其正常后继请求。
			Result = CompletePendingCompilation(OriginalSystem.Get());
			const int32 AfterShaderJobs = GShaderCompilingManager->GetNumRemainingJobs();
			const bool bAfterShaderMaps = GShaderCompilingManager->HasShaderJobs();
			UE_LOG(LogTemp, Display, TEXT("Niagara 批间 Shader 退役：System=%s BeforeJobs=%d BeforeShaderMaps=%d AfterJobs=%d AfterShaderMaps=%d；Editor 队列状态不等于进程驻留内存。"),
				*Result.SystemPath, BeforeShaderJobs, static_cast<int32>(bBeforeShaderMaps),
				AfterShaderJobs, static_cast<int32>(bAfterShaderMaps));
			if (Result.Error.IsEmpty() && (AfterShaderJobs != 0 || bAfterShaderMaps))
			{
				Result.Error = TEXT("当前 Editor 的 Shader 工作尚未完整退役，不进入下一制作批。");
			}
		}
	}
	if (Result.Error.IsEmpty() && !Result.bCompilationPending)
	{
		// 聚合 UpToDate 可掩盖 Unknown；按原生实际编译清单核每份当前源码/VM 身份与结果。
		const auto CheckScript = [&Result](const UNiagaraScript* Script)
		{
			if (!IsValid(Script)) { Result.Error = TEXT("分批编译缺少原生脚本。"); return false; }
			if (!Script->IsCompilable()) { return true; } // Emitter 脚本内联到 System，不拥有独立 VM 状态。
			const FNiagaraVMExecutableData& VM = Script->GetVMExecutableData();
			if (Script->GetUsage() == ENiagaraScriptUsage::SystemSpawnScript
				|| Script->GetUsage() == ENiagaraScriptUsage::SystemUpdateScript)
			{
				UE_LOG(LogTemp, Display, TEXT("Niagara 系统脚本编译读回：Script=%s UsesRI=%d RIParameters=%d RIBytes=%d HlslChars=%d Ops=%u"),
					*Script->GetPathName(), static_cast<int32>(Script->GetVMExecutableDataCompilationId().bUsesRapidIterationParams),
					Script->RapidIterationParameters.Num(), Script->RapidIterationParameters.GetParameterDataArray().Num(),
					VM.LastHlslTranslation.Len(), VM.LastOpCount);
			}
			const ENiagaraScriptCompileStatus Status = VM.LastCompileStatus;
			if ((Status != ENiagaraScriptCompileStatus::NCS_UpToDate
				&& Status != ENiagaraScriptCompileStatus::NCS_UpToDateWithWarnings
				&& Status != ENiagaraScriptCompileStatus::NCS_ComputeUpToDateWithWarnings)
				|| !VM.ErrorMsg.IsEmpty() || !Script->AreScriptAndSourceSynchronized())
			{
				Result.Error = FString::Printf(TEXT("分批编译脚本未成功或源码/VM 未同步：%s Status=%d Error=%s"),
					*Script->GetPathName(), static_cast<int32>(Status), *VM.ErrorMsg);
				return false;
			}
			return true;
		};
		if (CheckScript(System->GetSystemSpawnScript()) && CheckScript(System->GetSystemUpdateScript()))
		{
			for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
			{
				if (!Handle.GetIsEnabled()) { continue; }
				if (const FVersionedNiagaraEmitterData* Data = Handle.GetEmitterData())
				{
					TArray<UNiagaraScript*> Scripts;
					Data->GetScripts(Scripts, false, true);
					for (const UNiagaraScript* Script : Scripts) { if (!CheckScript(Script)) { break; } }
					if (!Result.Error.IsEmpty()) { break; }
				}
			}
		}
	}
	UE_LOG(LogTemp, Display, TEXT("Niagara 分批编译归还：System=%s Emitters=%d Pending=%d Active=%d NeedsRequest=%d Ready=%d Error=%s"),
		*Result.SystemPath, Result.EmitterCount, static_cast<int32>(Result.bCompilationPending),
		static_cast<int32>(Result.bActiveCompilations), static_cast<int32>(Result.bNeedsCompileRequest),
		static_cast<int32>(Result.bNativeReady), *Result.Error);
	return Result;
}

namespace
{
	/** 原 assignment 的值来源；不跨到 FunctionScript 内部或别的 ParamMap。 */
	struct FAliveExpression
	{
		UNiagaraNodeCustomHlsl* Node = nullptr;
		UEdGraphPin* MapInput = nullptr;
		UEdGraphPin* BoolOutput = nullptr;
		UEdGraphPin* OverridePin = nullptr;
	};

	UEdGraphPin* FindTypedPin(UEdGraphNode* Node, EEdGraphPinDirection Direction, const FNiagaraTypeDefinition& Type)
	{
		UEdGraphPin* Result = nullptr;
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin && Pin->Direction == Direction && UEdGraphSchema_Niagara::PinToTypeDefinition(Pin) == Type)
			{
				if (Result) { return nullptr; }
				Result = Pin;
			}
		}
		return Result;
	}

	bool ReadAliveExpression(UNiagaraNodeAssignment* Assignment, FAliveExpression& Out, FString& Error)
	{
		Out = {};
		UEdGraphPin* AssignmentMap = FindTypedPin(Assignment, EGPD_Input, FNiagaraTypeDefinition::GetParameterMapDef());
		UEdGraphNode* Override = AssignmentMap && AssignmentMap->LinkedTo.Num() == 1
			? AssignmentMap->LinkedTo[0]->GetOwningNode() : nullptr;
		const FName OverrideName(*(Assignment->GetFunctionName() + TEXT(".Particles.Alive")));
		if (!Override || Override->GetGraph() != Assignment->GetGraph()
			|| Override->GetClass()->GetPathName() != TEXT("/Script/NiagaraEditor.NiagaraNodeParameterMapSet"))
		{ Error = TEXT("原 Alive assignment 缺少同图唯一 override ParamMapSet。"); return false; }
		for (UEdGraphPin* Pin : Override->Pins)
		{
			if (Pin && Pin->Direction == EGPD_Input && Pin->PinName == OverrideName)
			{
				if (Out.OverridePin) { Error = TEXT("原 Alive override 输入重复。"); return false; }
				Out.OverridePin = Pin;
			}
		}
		UEdGraphPin* Value = Out.OverridePin && Out.OverridePin->LinkedTo.Num() == 1 ? Out.OverridePin->LinkedTo[0] : nullptr;
		Out.Node = Value ? Cast<UNiagaraNodeCustomHlsl>(Value->GetOwningNode()) : nullptr;
		if (!Out.Node || Out.Node->GetGraph() != Assignment->GetGraph()
			|| Out.Node->ScriptUsage != ENiagaraScriptUsage::DynamicInput)
		{ Error = TEXT("原 Alive override 不是同图唯一 CustomHlsl DynamicInput。"); return false; }
		Out.BoolOutput = FindTypedPin(Out.Node, EGPD_Output, FNiagaraTypeDefinition::GetBoolDef());
		Out.MapInput = FindTypedPin(Out.Node, EGPD_Input, FNiagaraTypeDefinition::GetParameterMapDef());
		UEdGraphPin* OverrideMap = FindTypedPin(Override, EGPD_Input, FNiagaraTypeDefinition::GetParameterMapDef());
		if (Value != Out.BoolOutput || Value->LinkedTo.Num() != 1 || Value->LinkedTo[0] != Out.OverridePin
			|| !Out.MapInput || Out.MapInput->LinkedTo.Num() != 1 || !OverrideMap || OverrideMap->LinkedTo.Num() != 1
			|| Out.MapInput->LinkedTo[0] != OverrideMap->LinkedTo[0])
		{ Error = TEXT("原 Alive Bool 输出或上游 ParamMap 关系不准确。"); return false; }
		return true;
	}

	UEdGraphPin* FindFailureAddPin(const FAliveExpression& Alive, FString& Error)
	{
		UEdGraphPin* Add = nullptr;
		for (UEdGraphPin* Pin : Alive.Node->Pins)
		{
			// UE 的公开动态 Add 针 schema；不调用未导出的 RequestNewTypedPin。
			if (Pin && Pin->Direction == EGPD_Input && Pin->PinType.PinCategory == UEdGraphSchema_Niagara::PinCategoryMisc
				&& Pin->PinType.PinSubCategory == FName(TEXT("DynamicAddPin")) && Pin->LinkedTo.IsEmpty())
			{
				if (Add) { Error = TEXT("原 CustomHlsl 输入 Add 针不唯一。"); return nullptr; }
				Add = Pin;
			}
			else if (Pin && Pin->Direction == EGPD_Input && Pin != Alive.MapInput)
			{ Error = TEXT("原 Alive CustomHlsl 已含额外输入，不能覆盖其接线。"); return nullptr; }
		}
		if (!Add) { Error = TEXT("原 CustomHlsl 缺少可用输入 Add 针。"); }
		return Add;
	}

	void InitializeDataInterfaceParameterInput(UNiagaraNodeInput& Input, const UNiagaraGraph& Graph,
		const FNiagaraTypeDefinition& Type, FName VariableName)
	{
		Input.Input = FNiagaraVariable(Type, VariableName);
		Input.Usage = ENiagaraInputNodeUsage::Parameter;
		Input.ExposureOptions.bExposed = false;
		Input.ExposureOptions.bRequired = false;
		// Engine 的标准初始化不导出；沿公开字段保留其同图追加排序，不能让 DI 排到 InputMap 前。
		int32 HighestSortPriority = -1;
		for (const UEdGraphNode* Node : Graph.Nodes)
		{
			const UNiagaraNodeInput* Existing = Cast<UNiagaraNodeInput>(Node);
			if (Existing && Existing->Usage == ENiagaraInputNodeUsage::Parameter)
			{
				HighestSortPriority = FMath::Max(HighestSortPriority, Existing->CallSortPriority);
			}
		}
		Input.CallSortPriority = HighestSortPriority + 1;
	}

	bool ConnectFailureInput(UNiagaraGraph* Graph, UNiagaraNodeAssignment* Assignment, FAliveExpression& Alive, const FName VariableName,
		const FString& SourceReference, UNiagaraNodeInput*& Input, UGGYGONiagaraRuntimeFailureDataInterface*& Interface, FName& OutLocalName, FString& Error)
	{
		const FNiagaraTypeDefinition Type(UGGYGONiagaraRuntimeFailureDataInterface::StaticClass());
		if (!FindFailureAddPin(Alive, Error)) { return false; }
		const TWeakObjectPtr<UNiagaraGraph> OriginalGraph(Graph);
		const TWeakObjectPtr<UNiagaraNodeAssignment> OriginalAssignment(Assignment);
		const TWeakObjectPtr<UNiagaraNodeCustomHlsl> OriginalCustom(Alive.Node);
		const TWeakObjectPtr<UEdGraphNode> OriginalMapSource(Alive.MapInput->LinkedTo[0]->GetOwningNode());
		const FGuid MapSourcePinId = Alive.MapInput->LinkedTo[0]->PinId;
		const FGuid AssignmentGuid = Assignment->NodeGuid;
		const FGuid CustomGuid = Alive.Node->NodeGuid;
		Graph->Modify();
		// 原生按变量名归并 DI；不同 Alive assignment 必须具有独立来源。
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			const UNiagaraNodeInput* Existing = Cast<UNiagaraNodeInput>(Node);
			if (Existing && Existing->Input.GetName() == VariableName)
			{ Error = TEXT("运行失败 DI 变量名已被原图占用。"); return false; }
		}
		Input = NewObject<UNiagaraNodeInput>(Graph, NAME_None, RF_Transactional);
		InitializeDataInterfaceParameterInput(*Input, *Graph, Type, VariableName);
		const TWeakObjectPtr<UNiagaraNodeInput> OriginalInput(Input);
		const auto ReacquireAlive = [&]()
		{
			Graph = OriginalGraph.Get();
			Assignment = OriginalAssignment.Get();
			Input = OriginalInput.Get();
			auto* Custom = OriginalCustom.Get();
			if (!Graph || !Assignment || !Custom || !Input || !OriginalMapSource.IsValid()
				|| Assignment->GetOuter() != Graph || Custom->GetOuter() != Graph
				|| Input->GetOuter() != Graph || !Graph->Nodes.Contains(Assignment) || !Graph->Nodes.Contains(Custom)
				|| OriginalMapSource->GetOuter() != Graph || !Graph->Nodes.Contains(OriginalMapSource.Get())
				|| !Graph->Nodes.Contains(Input) || Assignment->NodeGuid != AssignmentGuid || Custom->NodeGuid != CustomGuid
				|| Input->Input.GetType() != Type || Input->Input.GetName() != VariableName
				|| Input->Usage != ENiagaraInputNodeUsage::Parameter || Input->ExposureOptions.bExposed)
			{ Error = TEXT("原生图回调后原 Alive/Graph/Input 身份或同图成员关系已失效。"); return false; }
			FAliveExpression Current;
			if (!ReadAliveExpression(Assignment, Current, Error)) { return false; }
			if (Current.Node != Custom || Current.MapInput->LinkedTo[0]->GetOwningNode() != OriginalMapSource.Get()
				|| Current.MapInput->LinkedTo[0]->PinId != MapSourcePinId)
			{ Error = TEXT("原生图回调替换了原 Alive Custom 或上游 ParamMap。"); return false; }
			Alive = Current;
			return true;
		};
		// AddNode 即使 bFromUI=false 也会同步广播 GraphChanged，返栈先重取原对象。
		Graph->AddNode(Input, false, false);
		if (!ReacquireAlive()) { return false; }
		Input->CreateNewGuid();
		const FGuid InputGuid = Input->NodeGuid;
		// 通过 Engine 基类虚入口，由原生创建 DI 子对象与正确 typed output。
		static_cast<UEdGraphNode*>(Input)->AllocateDefaultPins();
		if (!ReacquireAlive()) { return false; }
		if (Input->NodeGuid != InputGuid) { Error = TEXT("分配 pins 后原失败 DI Input 身份已变化。"); return false; }
		TArray<UObject*> Children;
		GetObjectsWithOuter(Input, Children, EGetObjectsFlags::None);
		Interface = nullptr;
		for (UObject* Child : Children)
		{
			if (IsValid(Child) && Child->GetOuter() == Input && Child->GetClass() == Type.GetClass())
			{
				if (Interface) { Error = TEXT("原生 InputNode 创建了多个失败 DI 子对象。"); return false; }
				Interface = Cast<UGGYGONiagaraRuntimeFailureDataInterface>(Child);
			}
		}
		UEdGraphPin* Output = FindTypedPin(Input, EGPD_Output, Type);
		if (!Interface || !Output || !Output->LinkedTo.IsEmpty())
		{ Error = TEXT("原生 InputNode 未生成准确失败 DI 子对象及 typed output。"); return false; }
		Interface->Modify();
		Interface->SourceReference = SourceReference;
		UEdGraphPin* Add = FindFailureAddPin(Alive, Error);
		if (!Add) { return false; }
		const UEdGraphSchema* Schema = Graph->GetSchema();
		const TWeakObjectPtr<UGGYGONiagaraRuntimeFailureDataInterface> OriginalInterface(Interface);
		if (!Schema || !Schema->TryCreateConnection(Output, Add))
		{ Error = TEXT("原生 schema 拒绝将失败 DI 接入原 CustomHlsl Add 针。"); return false; }
		if (!ReacquireAlive()) { return false; }
		Interface = OriginalInterface.Get();
		if (Input->NodeGuid != InputGuid || !Interface || Interface->GetOuter() != Input)
		{ Error = TEXT("原生接线回调后原失败 DI/Input 身份已失效。"); return false; }
		Output = FindTypedPin(Input, EGPD_Output, Type);
		UEdGraphPin* LinkedInput = Output && Output->LinkedTo.Num() == 1 ? Output->LinkedTo[0] : nullptr;
		if (!LinkedInput || LinkedInput->GetOwningNode() != Alive.Node || LinkedInput->Direction != EGPD_Input
			|| LinkedInput->LinkedTo.Num() != 1 || LinkedInput->LinkedTo[0] != Output
			|| UEdGraphSchema_Niagara::PinToTypeDefinition(LinkedInput) != Type
			|| Interface->SourceReference != SourceReference)
		{ Error = TEXT("原生 typed DI 接线及来源读回不一致。"); return false; }
		OutLocalName = LinkedInput->PinName;
		if (OutLocalName.IsNone()) { Error = TEXT("原生 DI typed 输入缺少本地函数针名。"); return false; }
		return true;
	}
}

FGGYGONiagaraRuntimeFailureSupport UGGYGONiagaraCompileLibrary::ReadRuntimeFailureSupport()
{
	FGGYGONiagaraRuntimeFailureSupport Result;
	if (!IsInGameThread()) { Result.Error = TEXT("运行失败 DI 查询需要 GameThread。"); return Result; }
	const auto* Interface = GetDefault<UGGYGONiagaraRuntimeFailureDataInterface>();
	Result.DataInterfaceClass = Interface->GetClass()->GetPathName();
	Result.FunctionName = TEXT("ReportFailure");
	Result.FailureAttribute = TEXT("Particles.UEFX_RuntimeFailure");
	Result.PerInstanceBytes = Interface->PerInstanceDataSize();
	TArray<FNiagaraFunctionSignature> Functions;
	Interface->GetFunctionSignatures(Functions);
	const FStrProperty* Source = FindFProperty<FStrProperty>(Interface->GetClass(), GET_MEMBER_NAME_CHECKED(UGGYGONiagaraRuntimeFailureDataInterface, SourceReference));
	if (!Source || !Source->HasAllPropertyFlags(CPF_Edit) || Result.PerInstanceBytes <= 0
		|| !Interface->HasPostSimulateTick() || Interface->PostSimulateCanOverlapFrames()
		|| !Interface->CanExecuteOnTarget(ENiagaraSimTarget::CPUSim)
		|| Interface->CanExecuteOnTarget(ENiagaraSimTarget::GPUComputeSim) || Functions.Num() != 1)
	{ Result.Error = TEXT("实际加载的失败 DI 缺少可编辑来源、持久内存或串行 CPU post-sim 约定。"); return Result; }
	const FNiagaraFunctionSignature& Function = Functions[0];
	if (Function.Name != FName(*Result.FunctionName) || !Function.bMemberFunction || Function.bRequiresContext
		|| Function.bRequiresExecPin || !Function.bWriteFunction || !Function.bSupportsCPU || Function.bSupportsGPU
		|| Function.Inputs.Num() != 3 || Function.Outputs.Num() != 1
		|| Function.Inputs[0].GetType() != FNiagaraTypeDefinition(Interface->GetClass())
		|| Function.Inputs[1].GetType() != FNiagaraTypeDefinition::GetFloatDef()
		|| Function.Inputs[2].GetType() != FNiagaraTypeDefinition::GetBoolDef()
		|| Function.Outputs[0].GetType() != FNiagaraTypeDefinition::GetBoolDef()
		|| (Function.ModuleUsageBitmask != 0
			&& (!UNiagaraScript::IsSupportedUsageContextForBitmask(Function.ModuleUsageBitmask, ENiagaraScriptUsage::ParticleSpawnScript)
				|| !UNiagaraScript::IsSupportedUsageContextForBitmask(Function.ModuleUsageBitmask, ENiagaraScriptUsage::ParticleUpdateScript))))
	{ Result.Error = TEXT("实际 ReportFailure ABI 不符合 Spawn/Update 的 Float/OriginalAlive → KeepAlive。"); return Result; }
	Result.bSupported = true;
	return Result;
}

namespace
{
FGGYGONiagaraRuntimeFailureBinding ConnectRuntimeFailureWithContext(UNiagaraSystem* System,
	const FString& EmitterName, const FString& ModuleName, const FString& SourceReference, const FString& ScriptName,
	FNiagaraExternalEditContext* SharedContext, const FString* ExpectedAliveExpression)
{
	FGGYGONiagaraRuntimeFailureBinding Result;
	Result.SystemPath = GetPathNameSafe(System);
	Result.EmitterName = EmitterName;
	Result.ModuleName = ModuleName;
	Result.ScriptName = ScriptName;
	Result.SourceReference = SourceReference;
	const auto Support = UGGYGONiagaraCompileLibrary::ReadRuntimeFailureSupport();
	Result.DataInterfaceClass = Support.DataInterfaceClass;
	Result.FailureAttribute = Support.FailureAttribute;
	if (!Support.bSupported) { Result.Error = Support.Error; return Result; }
	if (!IsValid(System) || !GEditor || GEditor->PlayWorld || EmitterName.IsEmpty() || ModuleName.IsEmpty()
		|| SourceReference.TrimStartAndEnd().IsEmpty()
		|| (ScriptName != TEXT("ParticleSpawnScript") && ScriptName != TEXT("ParticleUpdateScript")))
	{ Result.Error = TEXT("失败 DI 接线需要非 PIE Editor、准确原 System/Emitter/Spawn或Update/Module 与来源。"); return Result; }
	TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	FNiagaraExt_StackItemReference Location(System, FName(*EmitterName), FName(*ScriptName), FName(*ModuleName));
	TUniquePtr<FNiagaraExternalEditContext> OwnedContext;
	if (!SharedContext) { OwnedContext = MakeUnique<FNiagaraExternalEditContext>(System); SharedContext = OwnedContext.Get(); }
	FNiagaraExternalEditContext& Context = *SharedContext;
	FNiagaraExt_ScriptStackTopology Topology;
	UNiagaraExternalEditUtilities::GetScriptStackTopology(Location, Topology, Context);
	int32 Count = 0;
	for (const FNiagaraExt_ModuleTopology& Module : Topology.Modules)
	{
		if (Module.ModuleName == Location.ModuleName && Module.Enabled && Module.bIsSetParametersModule) { ++Count; }
	}
	if (Context.HasErrors() || Topology.ScriptName != Location.ScriptName || Count != 1)
	{ Result.Error = TEXT("指定 Module 不是准确 Spawn/Update 栈中唯一启用的 assignment。"); return Result; }
	UNiagaraGraph* Graph = nullptr;
	for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
	{
		if (Handle.GetName() == Location.EmitterName)
		{
			const auto* Data = Handle.GetEmitterData();
			const auto* Source = Data ? Cast<UNiagaraScriptSource>(Data->GraphSource) : nullptr;
			if (Graph) { Result.Error = TEXT("原 Emitter 名称不唯一。"); return Result; }
			Graph = Source ? Source->NodeGraph.Get() : nullptr;
		}
	}
	if (!Graph) { Result.Error = TEXT("准确原 Emitter 缺少可编辑 Niagara 源图。"); return Result; }
	UNiagaraNodeAssignment* Assignment = nullptr;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		auto* Candidate = Cast<UNiagaraNodeAssignment>(Node);
		if (Candidate && Candidate->GetFunctionName() == ModuleName)
		{
			if (Assignment) { Result.Error = TEXT("同图原 assignment 名称不唯一。"); return Result; }
			Assignment = Candidate;
		}
	}
	if (!Assignment || Assignment->NumTargets() != 1
		|| Assignment->GetAssignmentTarget(0).GetName() != FName(TEXT("Particles.Alive"))
		|| Assignment->GetAssignmentTarget(0).GetType() != FNiagaraTypeDefinition::GetBoolDef())
	{ Result.Error = TEXT("原 assignment 必须只写 Bool Particles.Alive。"); return Result; }
	FAliveExpression Alive;
	if (!ReadAliveExpression(Assignment, Alive, Result.Error)) { return Result; }
	const TWeakObjectPtr<UNiagaraNodeAssignment> OriginalAssignment(Assignment);
	// CustomHlsl 是标准 EditAnywhere 字符串；只走 Editor 属性入口，不读写私有 Signature。
	FStrProperty* HlslProperty = FindFProperty<FStrProperty>(Alive.Node->GetClass(), TEXT("CustomHlsl"));
	if (!HlslProperty || !HlslProperty->HasAllPropertyFlags(CPF_Edit) || HlslProperty->HasAnyPropertyFlags(CPF_EditConst))
	{ Result.Error = TEXT("原 CustomHlsl 缺少标准可编辑代码属性。"); return Result; }
	Result.OriginalAliveExpression = HlslProperty->GetPropertyValue_InContainer(Alive.Node);
	if (ExpectedAliveExpression && Result.OriginalAliveExpression != *ExpectedAliveExpression)
	{ Result.Error = TEXT("原 Alive 表达式与本批明确输入不同，未接失败 DI。"); return Result; }
	if (Result.OriginalAliveExpression.TrimStartAndEnd().IsEmpty())
	{ Result.Error = TEXT("原 Alive 表达式为空，不能替换原粒子筛选谓词。"); return Result; }
	const FName VariableName(*(TEXT("UEFXRuntimeFailure_") + Assignment->NodeGuid.ToString(EGuidFormats::Digits)));
	Result.bGraphChanged = true;
	FName LocalName;
	UNiagaraNodeInput* Input = nullptr;
	UGGYGONiagaraRuntimeFailureDataInterface* Interface = nullptr;
	if (!ConnectFailureInput(Graph, Assignment, Alive, VariableName, SourceReference, Input, Interface, LocalName, Result.Error)) { return Result; }
	if (HlslProperty->GetPropertyValue_InContainer(Alive.Node) != Result.OriginalAliveExpression)
	{ Result.Error = TEXT("DI 接线期间原 Alive 表达式已改变。"); return Result; }
	const TWeakObjectPtr<UNiagaraNodeCustomHlsl> OriginalNode(Alive.Node);
	const FName OutputName = Alive.BoolOutput->PinName;
	const FString Expression = FString::Printf(TEXT("(%s.ReportFailure(%s, (%s), %s), %s)"),
		*LocalName.ToString(), *Support.FailureAttribute, *Result.OriginalAliveExpression,
		*OutputName.ToString(), *OutputName.ToString());
	Alive.Node->Modify();
	UObject* Editable = Alive.Node;
	Editable->PreEditChange(HlslProperty);
	HlslProperty->SetPropertyValue_InContainer(Editable, Expression);
	FPropertyChangedEvent Change(HlslProperty, EPropertyChangeType::ValueSet);
	// 基类虚入口由原生 CustomHlsl 刷新并通知重编译，typed DI/Map/output 留在原节点。
	Editable->PostEditChangeProperty(Change);
	FAliveExpression Final;
	if (!OriginalAssignment.IsValid() || !Graph->Nodes.Contains(OriginalAssignment.Get()) || !OriginalNode.IsValid())
	{ Result.Error = TEXT("Editor 属性更新后原 assignment 或 CustomHlsl 已退役。"); return Result; }
	if (!ReadAliveExpression(OriginalAssignment.Get(), Final, Result.Error)) { return Result; }
	if (Final.Node != OriginalNode.Get() || Final.BoolOutput->PinName != OutputName
		|| HlslProperty->GetPropertyValue_InContainer(Final.Node) != Expression
		|| !IsValid(Input) || !Graph->Nodes.Contains(Input) || Input->GetGraph() != Graph
		|| !IsValid(Interface) || Interface->GetOuter() != Input || Interface->SourceReference != SourceReference
		|| Input->Input.GetName() != VariableName || Input->Input.GetType() != FNiagaraTypeDefinition(Interface->GetClass()))
	{ Result.Error = TEXT("Editor 属性更新后原节点、代码、DI 或来源已变化。"); return Result; }
	UEdGraphPin* DIOutput = FindTypedPin(Input, EGPD_Output, FNiagaraTypeDefinition(Interface->GetClass()));
	UEdGraphPin* DIInput = DIOutput && DIOutput->LinkedTo.Num() == 1 ? DIOutput->LinkedTo[0] : nullptr;
	if (!DIInput || DIInput->GetOwningNode() != Final.Node || DIInput->PinName != LocalName
		|| DIInput->Direction != EGPD_Input || DIInput->LinkedTo.Num() != 1 || DIInput->LinkedTo[0] != DIOutput
		|| UEdGraphSchema_Niagara::PinToTypeDefinition(DIInput) != FNiagaraTypeDefinition(Interface->GetClass()))
	{ Result.Error = TEXT("Editor 属性更新后准确 typed DI 接线已变化。"); return Result; }
	Result.InterfaceParameter = LocalName.ToString();
	Result.bApplied = true;
	return Result;
}
}

FGGYGONiagaraRuntimeFailureBinding UGGYGONiagaraCompileLibrary::ConnectRuntimeFailureToAlive(
	UNiagaraSystem* System, const FString& EmitterName, const FString& ModuleName, const FString& SourceReference,
	const FString& ScriptName)
{
	return ConnectRuntimeFailureWithContext(System, EmitterName, ModuleName, SourceReference, ScriptName, nullptr, nullptr);
}

namespace
{
	UEdGraphPin* FindAssignmentPin(UEdGraphNode* Node, EEdGraphPinDirection Direction, FName Name)
	{
		UEdGraphPin* Result = nullptr;
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (Pin && Pin->Direction == Direction && Pin->PinName == Name)
			{
				if (Result) { return nullptr; }
				Result = Pin;
			}
		}
		return Result;
	}

	bool IsAssignmentAddPin(const UEdGraphPin* Pin)
	{
		return Pin && Pin->PinType.PinCategory == UEdGraphSchema_Niagara::PinCategoryMisc
			&& Pin->PinType.PinSubCategory == FName(TEXT("DynamicAddPin"));
	}

	UEdGraphPin* FindAssignmentAddPin(UEdGraphNode* Node, EEdGraphPinDirection Direction)
	{
		UEdGraphPin* Result = nullptr;
		for (UEdGraphPin* Pin : Node->Pins)
		{
			if (IsAssignmentAddPin(Pin) && Pin->Direction == Direction && Pin->LinkedTo.IsEmpty())
			{
				if (Result) { return nullptr; }
				Result = Pin;
			}
		}
		return Result;
	}
}

bool UGGYGONiagaraCompileLibrary::ReadAssignmentDataInterfaceSupport()
{
	const UFunction* Function = StaticClass()->FindFunctionByName(TEXT("ConnectAssignmentDataInterface"));
	return Function && Function->HasAllFunctionFlags(FUNC_Native) && Function->NumParms == 8;
}

namespace
{
/** 仅支持本批纯数学签名的实际值类型，不把未知类型转换成替代输出。 */
const TCHAR* AssignmentFunctionValueType(const FNiagaraTypeDefinition& Type)
{
	if (Type == FNiagaraTypeDefinition::GetVec3Def()) { return TEXT("float3"); }
	if (Type == FNiagaraTypeDefinition::GetQuatDef()) { return TEXT("float4"); }
	return nullptr;
}

bool ReadAssignmentSignature(UNiagaraDataInterface* Interface, FName FunctionName,
	FNiagaraFunctionSignature& Signature, FString& Error)
{
	if (!IsValid(Interface) || !Interface->CanExecuteOnTarget(ENiagaraSimTarget::CPUSim)
		|| Interface->PerInstanceDataSize() != 0 || FunctionName.IsNone())
	{ Error = TEXT("AssignmentDI 需要无实例数据的 CPU DI 及明确函数。"); return false; }
	TArray<FNiagaraFunctionSignature> Signatures;
	Interface->GetFunctionSignatures(Signatures);
	int32 Matches = 0;
	for (const auto& Candidate : Signatures)
	{
		if (Candidate.Name == FunctionName) { Signature = Candidate; ++Matches; }
	}
	if (Matches != 1 || !Signature.bMemberFunction || !Signature.bSupportsCPU
		|| Signature.bRequiresContext || Signature.bWriteFunction || Signature.Inputs.IsEmpty()
		|| Signature.Inputs[0].GetType() != FNiagaraTypeDefinition(Interface->GetClass()) || Signature.Outputs.IsEmpty())
	{ Error = TEXT("AssignmentDI 缺唯一匹配的 CPU 纯函数签名。"); return false; }
	for (int32 Index = 1; Index < Signature.Inputs.Num(); ++Index)
	{
		if (!AssignmentFunctionValueType(Signature.Inputs[Index].GetType()))
		{ Error = TEXT("AssignmentDI 函数输入不是本批支持的 Vector/Quat 值。"); return false; }
	}
	for (const auto& Output : Signature.Outputs)
	{
		if (!AssignmentFunctionValueType(Output.GetType()))
		{ Error = TEXT("AssignmentDI 函数输出不是本批支持的 Vector/Quat 值。"); return false; }
	}
	return true;
}

bool BindAssignmentFunction(UNiagaraDataInterface* Interface, const FNiagaraFunctionSignature& Signature, FName OwnerName)
{
	FVMExternalFunctionBindingInfo Binding;
	Binding.Name = Signature.Name;
	Binding.OwnerName = OwnerName;
	// 无实例数据的 DI 不注入 UserPtr；按真实值类型的 float 分量绑定。
	for (int32 Index = 1; Index < Signature.Inputs.Num(); ++Index)
	{
		for (int32 Component = 0; Component < Signature.Inputs[Index].GetType().GetSize() / static_cast<int32>(sizeof(float)); ++Component)
		{ Binding.InputParamLocations.Add(false); }
	}
	for (const auto& Output : Signature.Outputs) { Binding.NumOutputs += Output.GetType().GetSize() / static_cast<int32>(sizeof(float)); }
	FVMExternalFunction Function;
	Interface->GetVMExternalFunction(Binding, nullptr, Function);
	return Function.IsBound();
}

bool ReadMathAssignmentSupport()
{
	auto* Interface = GetMutableDefault<UGGYGOFXMathDataInterface>();
	if (!Interface || Interface->CanExecuteOnTarget(ENiagaraSimTarget::GPUComputeSim)) { return false; }
	const auto Vec3 = FNiagaraTypeDefinition::GetVec3Def();
	const auto Quat = FNiagaraTypeDefinition::GetQuatDef();
	const auto Check = [Interface](FName Name, const TArray<FNiagaraVariable>& Inputs, const TArray<FNiagaraVariable>& Outputs)
	{
		FNiagaraFunctionSignature Signature;
		FString Error;
		if (!ReadAssignmentSignature(Interface, Name, Signature, Error) || Signature.bSupportsGPU
			|| Signature.Inputs[0].GetName() != FName(TEXT("Math"))
			|| Signature.Inputs.Num() != Inputs.Num() + 1 || Signature.Outputs.Num() != Outputs.Num())
		{
			UE_LOG(LogTemp, Error, TEXT("Math DI 作者接口不符：%s %s"), *Name.ToString(), *Error);
			return false;
		}
		for (int32 Index = 0; Index < Inputs.Num(); ++Index)
		{
			if (Signature.Inputs[Index + 1].GetName() != Inputs[Index].GetName()
				|| Signature.Inputs[Index + 1].GetType() != Inputs[Index].GetType())
			{ UE_LOG(LogTemp, Error, TEXT("Math DI %s 输入 %d 名称/类型不符。"), *Name.ToString(), Index); return false; }
		}
		for (int32 Index = 0; Index < Outputs.Num(); ++Index)
		{
			if (Signature.Outputs[Index].GetName() != Outputs[Index].GetName()
				|| Signature.Outputs[Index].GetType() != Outputs[Index].GetType())
			{ UE_LOG(LogTemp, Error, TEXT("Math DI %s 输出 %d 名称/类型不符。"), *Name.ToString(), Index); return false; }
		}
		if (!BindAssignmentFunction(Interface, Signature, FName(TEXT("Math"))))
		{ UE_LOG(LogTemp, Error, TEXT("Math DI %s 不能绑定实际 CPU 签名。"), *Name.ToString()); return false; }
		return true;
	};
	return Check(TEXT("ComposeAffineStep"),
		{FNiagaraVariable(Vec3, TEXT("ParentPosition")), FNiagaraVariable(Vec3, TEXT("ParentColumn0")),
		 FNiagaraVariable(Vec3, TEXT("ParentColumn1")), FNiagaraVariable(Vec3, TEXT("ParentColumn2")),
		 FNiagaraVariable(Vec3, TEXT("LocalPosition")), FNiagaraVariable(Quat, TEXT("LocalRotation")), FNiagaraVariable(Vec3, TEXT("LocalScale"))},
		{FNiagaraVariable(Vec3, TEXT("NextPosition")), FNiagaraVariable(Vec3, TEXT("NextColumn0")),
		 FNiagaraVariable(Vec3, TEXT("NextColumn1")), FNiagaraVariable(Vec3, TEXT("NextColumn2"))})
		&& Check(TEXT("EulerZXY"), {FNiagaraVariable(Vec3, TEXT("Euler"))}, {FNiagaraVariable(Quat, TEXT("Quaternion"))});
}

bool ReadAssignmentFunction(UNiagaraDataInterface* Interface, const FGGYGONiagaraAuthoringWorkItem& Work,
	FNiagaraFunctionSignature& Signature, FString& Body, FString& Error)
{
	if (!Work.HlslBodyTemplate.IsEmpty())
	{ Error = TEXT("AssignmentDI body 必须由原生函数签名生成。"); return false; }
	if (!ReadAssignmentSignature(Interface, Work.FunctionName, Signature, Error)) { return false; }
	if (Signature.Inputs.Num() != Work.FunctionInputs.Num() + 1 || Signature.Outputs.Num() != Work.OutputTargets.Num())
	{ Error = TEXT("AssignmentDI 缺完整有序输入/输出。"); return false; }
	Body.Reset();
	for (int32 Index = 0; Index < Work.FunctionInputs.Num(); ++Index)
	{
		const auto& Input = Work.FunctionInputs[Index];
		const auto& Actual = Signature.Inputs[Index + 1];
		const TCHAR* HlslType = AssignmentFunctionValueType(Actual.GetType());
		if (Input.Name != Actual.GetName() || Input.Type != Actual.GetType()
			|| Input.HlslExpression.TrimStartAndEnd().IsEmpty())
		{ Error = FString::Printf(TEXT("AssignmentDI 输入 %d 的实际名称、类型或值表达式不符。"), Index); return false; }
		for (TCHAR Character : Input.HlslExpression)
		{
			if (Character == TEXT(';') || Character == TEXT('{') || Character == TEXT('}')
				|| Character == TEXT('#') || Character == TEXT('\n') || Character == TEXT('\r'))
			{ Error = TEXT("AssignmentDI 输入必须是单个值表达式，不能注入语句体。"); return false; }
		}
		Body += FString::Printf(TEXT("%s GGYGODIArgument_%d = (%s);\n"), HlslType, Index, *Input.HlslExpression);
	}
	Body += TEXT("{{DI}}.") + Signature.Name.ToString() + TEXT("(");
	bool bFirst = true;
	for (int32 Index = 0; Index < Work.FunctionInputs.Num(); ++Index)
	{
		if (!bFirst) { Body += TEXT(", "); }
		Body += FString::Printf(TEXT("GGYGODIArgument_%d"), Index);
		bFirst = false;
	}
	TSet<FName> Targets;
	for (int32 Index = 0; Index < Work.OutputTargets.Num(); ++Index)
	{
		const auto& Target = Work.OutputTargets[Index];
		if (Target.Name.IsNone() || Targets.Contains(Target.Name) || Target.Type != Signature.Outputs[Index].GetType())
		{ Error = FString::Printf(TEXT("AssignmentDI 输出 %d 的实际类型或唯一目标不符。"), Index); return false; }
		Targets.Add(Target.Name);
		if (!bFirst) { Body += TEXT(", "); }
		Body += TEXT("{{OUT:") + Target.Name.ToString() + TEXT("}}");
		bFirst = false;
	}
	Body += TEXT(");\n");
	return true;
}

FGGYGONiagaraAssignmentDIBinding ConnectAssignmentWithContext(UNiagaraSystem* System,
	const FString& EmitterName, const FString& ScriptName, const FString& ModuleName,
	UNiagaraDataInterface* InterfaceTemplate, const TArray<FName>& OutputTargets, const FString& HlslBodyTemplate,
	FNiagaraExternalEditContext* SharedContext, const FGGYGONiagaraAuthoringWorkItem* FunctionWork = nullptr)
{
	FGGYGONiagaraAssignmentDIBinding Result;
	Result.SystemPath = GetPathNameSafe(System);
	Result.EmitterName = EmitterName;
	Result.ScriptName = ScriptName;
	Result.ModuleName = ModuleName;
	Result.DataInterfaceClass = IsValid(InterfaceTemplate) ? InterfaceTemplate->GetClass()->GetPathName() : FString();
	if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || !IsValid(System) || System->IsTemplate()
		|| !IsValid(InterfaceTemplate) || InterfaceTemplate->IsTemplate() || OutputTargets.IsEmpty()
		|| !InterfaceTemplate->CanExecuteOnTarget(ENiagaraSimTarget::CPUSim)
		|| (ScriptName != TEXT("ParticleSpawnScript") && ScriptName != TEXT("ParticleUpdateScript")
			&& ScriptName != TEXT("EmitterSpawnScript") && ScriptName != TEXT("EmitterUpdateScript")))
	{ Result.Error = TEXT("DI authoring 需要非 PIE Editor、新 NS、可执行 CPU DI 及准确标准栈和目标。"); return Result; }

	TSet<FName> TargetNames;
	FString CheckedTemplate = HlslBodyTemplate;
	if (!CheckedTemplate.Contains(TEXT("{{DI}}"), ESearchCase::CaseSensitive))
	{ Result.Error = TEXT("Function body 缺少实际 DI pin 占位符。"); return Result; }
	CheckedTemplate.ReplaceInline(TEXT("{{DI}}"), TEXT("DI"), ESearchCase::CaseSensitive);
	for (FName Target : OutputTargets)
	{
		const FString Token = TEXT("{{OUT:") + Target.ToString() + TEXT("}}");
		if (Target.IsNone() || TargetNames.Contains(Target) || !CheckedTemplate.Contains(Token, ESearchCase::CaseSensitive))
		{ Result.Error = TEXT("输出目标为空、重复或缺少准确 body 占位符。"); return Result; }
		TargetNames.Add(Target);
		CheckedTemplate.ReplaceInline(*Token, TEXT("Output"), ESearchCase::CaseSensitive);
	}
	if (CheckedTemplate.Contains(TEXT("{{")) || CheckedTemplate.Contains(TEXT("}}")))
	{ Result.Error = TEXT("Function body 含未识别的 pin 占位符。"); return Result; }

	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	const TStrongObjectPtr<UNiagaraDataInterface> OriginalTemplate(InterfaceTemplate);
	FNiagaraExt_StackItemReference Location(System, FName(*EmitterName), FName(*ScriptName), FName(*ModuleName));
	TUniquePtr<FNiagaraExternalEditContext> OwnedContext;
	if (!SharedContext) { OwnedContext = MakeUnique<FNiagaraExternalEditContext>(System); SharedContext = OwnedContext.Get(); }
	FNiagaraExternalEditContext& Context = *SharedContext;
	FNiagaraExt_ScriptStackTopology Topology;
	UNiagaraExternalEditUtilities::GetScriptStackTopology(Location, Topology, Context);
	int32 Matches = 0;
	for (const FNiagaraExt_ModuleTopology& Module : Topology.Modules)
	{
		if (Module.ModuleName == Location.ModuleName && Module.Enabled && Module.bIsSetParametersModule) { ++Matches; }
	}
	if (Context.HasErrors() || Topology.ScriptName != Location.ScriptName || Matches != 1)
	{ Result.Error = TEXT("指定栈中缺少唯一启用的原 assignment。"); return Result; }

	UNiagaraGraph* Graph = nullptr;
	UNiagaraScriptSource* EmitterSource = nullptr;
	FGuid EmitterHandleId;
	for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
	{
		if (Handle.GetName() != Location.EmitterName) { continue; }
		const auto* Data = Handle.GetEmitterData();
		auto* Source = Data ? Cast<UNiagaraScriptSource>(Data->GraphSource) : nullptr;
		if (Graph || !Data || Data->SimTarget != ENiagaraSimTarget::CPUSim || !Source || !Source->NodeGraph)
		{ Result.Error = TEXT("原 emitter 不唯一、不是 CPU 或缺少可编辑源图。"); return Result; }
		Graph = Source->NodeGraph;
		EmitterSource = Source;
		EmitterHandleId = Handle.GetId();
	}
	if (!Graph) { Result.Error = TEXT("找不到指定原 emitter 的源图。"); return Result; }
	UNiagaraNodeAssignment* Assignment = nullptr;
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		auto* Candidate = Cast<UNiagaraNodeAssignment>(Node);
		if (Candidate && Candidate->GetFunctionName() == ModuleName)
		{
			if (Assignment) { Result.Error = TEXT("同图原 assignment 名称不唯一。"); return Result; }
			Assignment = Candidate;
		}
	}
	if (!Assignment || Assignment->NumTargets() != OutputTargets.Num())
	{ Result.Error = TEXT("原 assignment 的全部目标必须与本次显式输出一致。"); return Result; }
	TArray<FNiagaraTypeDefinition> Types;
	for (FName Target : OutputTargets)
	{
		const int32 Index = Assignment->FindAssignmentTarget(Target);
		if (Index == INDEX_NONE) { Result.Error = TEXT("原 assignment 缺少显式输出目标：") + Target.ToString(); return Result; }
		const auto Type = Assignment->GetAssignmentTarget(Index).GetType();
		if (!Type.IsValid() || Type.IsDataInterface() || Type.IsStatic() || Type == FNiagaraTypeDefinition::GetParameterMapDef())
		{ Result.Error = TEXT("输出必须是原 assignment 已声明的非 static 值类型。"); return Result; }
		Types.Add(Type);
	}

	UEdGraphPin* AssignmentMap = FindTypedPin(Assignment, EGPD_Input, FNiagaraTypeDefinition::GetParameterMapDef());
	UEdGraphNode* Override = AssignmentMap && AssignmentMap->LinkedTo.Num() == 1 ? AssignmentMap->LinkedTo[0]->GetOwningNode() : nullptr;
	if (!Override || Override->GetGraph() != Graph
		|| Override->GetClass()->GetPathName() != TEXT("/Script/NiagaraEditor.NiagaraNodeParameterMapSet"))
	{ Result.Error = TEXT("原 assignment 缺少准确同图 override ParamMapSet。"); return Result; }
	TArray<FName> OverrideNames;
	for (int32 Index = 0; Index < OutputTargets.Num(); ++Index)
	{
		const FName Name(*(Assignment->GetFunctionName() + TEXT(".") + OutputTargets[Index].ToString()));
		OverrideNames.Add(Name);
		UEdGraphPin* Pin = FindAssignmentPin(Override, EGPD_Input, Name);
		if ((Index == 0 && (!Pin || Pin->LinkedTo.Num() != 1))
			|| (Pin && UEdGraphSchema_Niagara::PinToTypeDefinition(Pin) != Types[Index])
			|| (Index > 0 && Pin && !Pin->LinkedTo.IsEmpty()))
		{ Result.Error = TEXT("首目标须有原 seed，其余目标不能覆盖已有连线。"); return Result; }
	}
	UEdGraphPin* Seed = FindAssignmentPin(Override, EGPD_Input, OverrideNames[0])->LinkedTo[0];
	auto* Custom = Cast<UNiagaraNodeCustomHlsl>(Seed->GetOwningNode());
	if (!Custom || Custom->GetGraph() != Graph || Custom->ScriptUsage != ENiagaraScriptUsage::DynamicInput
		|| Seed->Direction != EGPD_Output || Seed->LinkedTo.Num() != 1
		|| UEdGraphSchema_Niagara::PinToTypeDefinition(Seed) != Types[0]
		|| !FindAssignmentAddPin(Custom, EGPD_Input) || !FindAssignmentAddPin(Custom, EGPD_Output))
	{ Result.Error = TEXT("首目标缺少同图、未接其它功能的原 Custom DynamicInput seed。"); return Result; }
	UEdGraphPin* CustomMap = FindTypedPin(Custom, EGPD_Input, FNiagaraTypeDefinition::GetParameterMapDef());
	UEdGraphPin* OverrideMap = FindTypedPin(Override, EGPD_Input, FNiagaraTypeDefinition::GetParameterMapDef());
	if (!CustomMap || CustomMap->LinkedTo.Num() != 1 || !OverrideMap || OverrideMap->LinkedTo.Num() != 1
		|| CustomMap->LinkedTo[0] != OverrideMap->LinkedTo[0])
	{ Result.Error = TEXT("原 Custom 与 override 没有消费同一个准确上游 ParamMap。"); return Result; }
	for (UEdGraphPin* Pin : Custom->Pins)
	{
		if (!IsAssignmentAddPin(Pin) && Pin != CustomMap && Pin != Seed)
		{ Result.Error = TEXT("原 Custom 已含其它 typed pins，拒绝覆盖既有用途。"); return Result; }
	}
	FStrProperty* CodeProperty = FindFProperty<FStrProperty>(Custom->GetClass(), TEXT("CustomHlsl"));
	if (!CodeProperty || !CodeProperty->HasAllPropertyFlags(CPF_Edit) || CodeProperty->HasAnyPropertyFlags(CPF_EditConst))
	{ Result.Error = TEXT("原 Custom 缺少标准可编辑 HLSL 属性。"); return Result; }
	const FName VariableName(*(TEXT("GGYGOAssignmentDI_") + Assignment->NodeGuid.ToString(EGuidFormats::Digits)));
	for (UEdGraphNode* Node : Graph->Nodes)
	{
		const auto* Existing = Cast<UNiagaraNodeInput>(Node);
		if (Existing && Existing->Input.GetName() == VariableName)
		{ Result.Error = TEXT("本 assignment 的 DI 变量名已存在，拒绝重复接线。"); return Result; }
	}

	Result.AssignmentGuid = Assignment->NodeGuid;
	Result.CustomGuid = Custom->NodeGuid;
	const TWeakObjectPtr<UNiagaraGraph> OriginalGraph(Graph);
	const TWeakObjectPtr<UNiagaraScriptSource> OriginalSource(EmitterSource);
	const TWeakObjectPtr<UNiagaraNodeAssignment> OriginalAssignment(Assignment);
	const TWeakObjectPtr<UNiagaraNodeCustomHlsl> OriginalCustom(Custom);
	const TWeakObjectPtr<UEdGraphNode> OriginalOverride(Override);
	const TWeakObjectPtr<UEdGraphNode> OriginalMapSource(CustomMap->LinkedTo[0]->GetOwningNode());
	const FGuid MapSourcePinId = CustomMap->LinkedTo[0]->PinId;
	const auto OriginalNodesRemain = [&]()
	{
		if (!IsValid(System) || !IsValid(Graph)) { return false; }
		const FVersionedNiagaraEmitterData* CurrentData = nullptr;
		for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
		{
			if (Handle.GetId() == EmitterHandleId) { CurrentData = Handle.GetEmitterData(); break; }
		}
		return CurrentData && CurrentData->GraphSource == OriginalSource.Get()
			&& OriginalSource.IsValid() && OriginalSource->NodeGraph == Graph
			&& OriginalAssignment.IsValid() && OriginalCustom.IsValid() && OriginalOverride.IsValid() && OriginalMapSource.IsValid()
			&& OriginalAssignment->GetOuter() == Graph && OriginalCustom->GetOuter() == Graph
			&& OriginalOverride->GetOuter() == Graph && OriginalMapSource->GetOuter() == Graph
			&& Graph->Nodes.Contains(OriginalAssignment.Get()) && Graph->Nodes.Contains(OriginalCustom.Get())
			&& Graph->Nodes.Contains(OriginalOverride.Get()) && Graph->Nodes.Contains(OriginalMapSource.Get())
			&& OriginalAssignment->NodeGuid == Result.AssignmentGuid && OriginalCustom->NodeGuid == Result.CustomGuid;
	};
	const FScopedTransaction Transaction(NSLOCTEXT("GGYGONiagara", "AssignmentDI", "接入 assignment DI 多输出"));
	System->Modify();
	Graph->Modify();
	Assignment->Modify();
	Custom->Modify();
	Result.bGraphChanged = true;
	// Function 是原生 Custom 的普通用法；DynamicInput 只能具有一个 rvalue 输出。
	Custom->ScriptUsage = ENiagaraScriptUsage::Function;
	const FNiagaraTypeDefinition DIType(InterfaceTemplate->GetClass());
	auto* Input = NewObject<UNiagaraNodeInput>(Graph, NAME_None, RF_Transactional);
	InitializeDataInterfaceParameterInput(*Input, *Graph, DIType, VariableName);
	const TWeakObjectPtr<UNiagaraNodeInput> OriginalInput(Input);
	Graph->AddNode(Input, false, false);
	Graph = OriginalGraph.Get();
	Input = OriginalInput.Get();
	if (!OriginalNodesRemain() || !Input || Input->GetOuter() != Graph || !Graph->Nodes.Contains(Input)
		|| Input->Input.GetType() != DIType || Input->Input.GetName() != VariableName
		|| Input->Usage != ENiagaraInputNodeUsage::Parameter || Input->ExposureOptions.bExposed)
	{ Result.Error = TEXT("AddNode 回调后原图、Custom 或新增 Input 已失效。"); return Result; }
	Assignment = OriginalAssignment.Get();
	Custom = OriginalCustom.Get();
	Override = OriginalOverride.Get();
	Input->CreateNewGuid();
	const FGuid InputGuid = Input->NodeGuid;
	static_cast<UEdGraphNode*>(Input)->AllocateDefaultPins();
	Graph = OriginalGraph.Get();
	Input = OriginalInput.Get();
	if (!OriginalNodesRemain() || !Input || Input->GetOuter() != Graph || !Graph->Nodes.Contains(Input)
		|| Input->NodeGuid != InputGuid || Input->Input.GetType() != DIType || Input->Input.GetName() != VariableName
		|| Input->Usage != ENiagaraInputNodeUsage::Parameter || Input->ExposureOptions.bExposed)
	{ Result.Error = TEXT("原生分配 pins 后原图或新增 Input 已退役。"); return Result; }
	Assignment = OriginalAssignment.Get();
	Custom = OriginalCustom.Get();
	Override = OriginalOverride.Get();
	TArray<UObject*> Children;
	GetObjectsWithOuter(Input, Children, EGetObjectsFlags::None);
	UNiagaraDataInterface* Interface = nullptr;
	for (UObject* Child : Children)
	{
		if (IsValid(Child) && Child->GetOuter() == Input && Child->GetClass() == InterfaceTemplate->GetClass())
		{
			if (Interface) { Result.Error = TEXT("原生 Input 创建了多个同类 DI。"); return Result; }
			Interface = Cast<UNiagaraDataInterface>(Child);
		}
	}
	if (Interface) { Interface->Modify(); }
	if (!Interface || !IsValid(InterfaceTemplate) || !InterfaceTemplate->CopyTo(Interface) || !OriginalNodesRemain()
		|| !IsValid(Input) || !Graph->Nodes.Contains(Input) || !IsValid(Interface) || Interface->GetOuter() != Input
		|| !IsValid(InterfaceTemplate) || !InterfaceTemplate->Equals(Interface))
	{ Result.Error = TEXT("DI 原生复制或回调后的原图身份核验失败；保留脏图，停止本 NS 制作。"); return Result; }
	const TWeakObjectPtr<UNiagaraDataInterface> OriginalInterface(Interface);
	const UEdGraphSchema* Schema = Graph->GetSchema();
	UEdGraphPin* DIOutput = FindTypedPin(Input, EGPD_Output, DIType);
	UEdGraphPin* InputAdd = FindAssignmentAddPin(Custom, EGPD_Input);
	if (!Schema || !DIOutput || !InputAdd || !Schema->TryCreateConnection(DIOutput, InputAdd) || !OriginalNodesRemain()
		|| !OriginalInput.IsValid() || !OriginalInterface.IsValid() || !Graph->Nodes.Contains(OriginalInput.Get()))
	{ Result.Error = TEXT("原生 schema 未能将 typed DI 接入原 Custom。"); return Result; }
	DIOutput = FindTypedPin(Input, EGPD_Output, DIType);
	if (!DIOutput || DIOutput->LinkedTo.Num() != 1 || DIOutput->LinkedTo[0]->GetOwningNode() != Custom)
	{ Result.Error = TEXT("接线后缺少原 Custom 的准确 DI input。"); return Result; }
	Result.InterfaceParameter = DIOutput->LinkedTo[0]->PinName;

	for (int32 Index = 0; Index < OutputTargets.Num(); ++Index)
	{
		if (!OriginalNodesRemain()) { Result.Error = TEXT("添加输出期间原节点退役。"); return Result; }
		if (Index > 0)
		{
			UEdGraphPin& TargetPin = FNiagaraStackGraphUtilities::GetOrCreateStackFunctionInputOverridePin(*Assignment,
				FNiagaraParameterHandle(OverrideNames[Index]), Types[Index], FGuid(), FGuid());
			if (!OriginalNodesRemain()) { Result.Error = TEXT("创建目标 override 后原节点退役。"); return Result; }
			UEdGraphPin* OutputAdd = FindAssignmentAddPin(Custom, EGPD_Output);
			if (TargetPin.GetOwningNode() != Override || !TargetPin.LinkedTo.IsEmpty() || !OutputAdd
				|| !Schema->TryCreateConnection(OutputAdd, &TargetPin) || !OriginalNodesRemain())
			{ Result.Error = TEXT("原生 schema 未能将多输出接到同 assignment 的准确目标。"); return Result; }
		}
		UEdGraphPin* TargetPin = FindAssignmentPin(Override, EGPD_Input, OverrideNames[Index]);
		UEdGraphPin* Value = TargetPin && TargetPin->LinkedTo.Num() == 1 ? TargetPin->LinkedTo[0] : nullptr;
		if (!Value || Value->GetOwningNode() != Custom || Value->Direction != EGPD_Output
			|| Value->LinkedTo.Num() != 1 || Value->LinkedTo[0] != TargetPin
			|| UEdGraphSchema_Niagara::PinToTypeDefinition(Value) != Types[Index])
		{ Result.Error = TEXT("实际输出类型、归属或单一目标连线不一致。"); return Result; }
		if (Index > 0)
		{
			// assignment 目标保留完整路径；Function 输出须用局部名，重命名事件同步原生 Signature。
			const FName LocalName(*FString::Printf(TEXT("GGYGOOutput_%d"), Index));
			const FText LocalNameText = FText::FromName(LocalName);
			FText RenameError;
			UNiagaraNode* CustomNode = Custom;
			if (!CustomNode->VerifyEditablePinName(LocalNameText, RenameError, Value))
			{ Result.Error = TEXT("原 Custom 附加输出局部名无效：") + RenameError.ToString(); return Result; }
			if (!CustomNode->CommitEditablePinName(LocalNameText, Value, false) || !OriginalNodesRemain())
			{ Result.Error = TEXT("原 Custom 附加输出重命名失败或原节点退役。"); return Result; }
			TargetPin = FindAssignmentPin(OriginalOverride.Get(), EGPD_Input, OverrideNames[Index]);
			Value = TargetPin && TargetPin->LinkedTo.Num() == 1 ? TargetPin->LinkedTo[0] : nullptr;
			if (!Value || Value->GetOwningNode() != OriginalCustom.Get() || Value->Direction != EGPD_Output
				|| Value->PinName != LocalName || Value->LinkedTo.Num() != 1 || Value->LinkedTo[0] != TargetPin
				|| UEdGraphSchema_Niagara::PinToTypeDefinition(Value) != Types[Index])
			{ Result.Error = TEXT("重命名后原输出局部名、类型或单一目标连线不一致。"); return Result; }
		}
		auto& Binding = Result.Outputs.AddDefaulted_GetRef();
		Binding.Target = OutputTargets[Index];
		Binding.OutputPin = Value->PinName;
		Binding.TypePath = Types[Index].IsEnum() ? Types[Index].GetEnum()->GetPathName() : Types[Index].GetStruct()->GetPathName();
	}

	Result.HlslBody = HlslBodyTemplate.Replace(TEXT("{{DI}}"), *Result.InterfaceParameter.ToString(), ESearchCase::CaseSensitive);
	for (const auto& Binding : Result.Outputs)
	{
		const FString Token = TEXT("{{OUT:") + Binding.Target.ToString() + TEXT("}}");
		Result.HlslBody.ReplaceInline(*Token, *Binding.OutputPin.ToString(), ESearchCase::CaseSensitive);
	}
	UObject* Editable = Custom;
	Editable->PreEditChange(CodeProperty);
	if (!OriginalNodesRemain()) { Result.Error = TEXT("PreEditChange 后原节点退役。"); return Result; }
	CodeProperty->SetPropertyValue_InContainer(Editable, Result.HlslBody);
	FPropertyChangedEvent Change(CodeProperty, EPropertyChangeType::ValueSet);
	Editable->PostEditChangeProperty(Change);
	if (!OriginalNodesRemain() || !OriginalInput.IsValid() || !OriginalInterface.IsValid()
		|| !Graph->Nodes.Contains(OriginalInput.Get()) || OriginalInput->NodeGuid != InputGuid
		|| OriginalInterface->GetOuter() != OriginalInput.Get()
		|| OriginalInput->Input.GetType() != DIType || OriginalInput->Input.GetName() != VariableName
		|| Custom->ScriptUsage != ENiagaraScriptUsage::Function
		|| CodeProperty->GetPropertyValue_InContainer(Custom) != Result.HlslBody)
	{ Result.Error = TEXT("属性刷新后原节点、DI、Function 用法或 body 已变化。"); return Result; }
	AssignmentMap = FindTypedPin(Assignment, EGPD_Input, FNiagaraTypeDefinition::GetParameterMapDef());
	CustomMap = FindTypedPin(Custom, EGPD_Input, FNiagaraTypeDefinition::GetParameterMapDef());
	OverrideMap = FindTypedPin(Override, EGPD_Input, FNiagaraTypeDefinition::GetParameterMapDef());
	DIOutput = FindTypedPin(Input, EGPD_Output, DIType);
	UEdGraphPin* DIInput = DIOutput && DIOutput->LinkedTo.Num() == 1 ? DIOutput->LinkedTo[0] : nullptr;
	if (!AssignmentMap || AssignmentMap->LinkedTo.Num() != 1 || AssignmentMap->LinkedTo[0]->GetOwningNode() != Override
		|| !CustomMap || CustomMap->LinkedTo.Num() != 1 || !OverrideMap || OverrideMap->LinkedTo.Num() != 1
		|| CustomMap->LinkedTo[0] != OverrideMap->LinkedTo[0]
		|| CustomMap->LinkedTo[0]->GetOwningNode() != OriginalMapSource.Get() || CustomMap->LinkedTo[0]->PinId != MapSourcePinId
		|| !DIInput || DIInput->GetOwningNode() != Custom || DIInput->Direction != EGPD_Input
		|| DIInput->PinName != Result.InterfaceParameter || DIInput->LinkedTo.Num() != 1 || DIInput->LinkedTo[0] != DIOutput
		|| UEdGraphSchema_Niagara::PinToTypeDefinition(DIInput) != DIType
		|| !IsValid(InterfaceTemplate) || !InterfaceTemplate->Equals(Interface))
	{ Result.Error = TEXT("属性刷新后同一 ParamMap 或 typed DI/模板值接线读回不一致。"); return Result; }
	int32 InputCount = 0;
	int32 OutputCount = 0;
	for (UEdGraphPin* Pin : Custom->Pins)
	{
		if (IsAssignmentAddPin(Pin)) { continue; }
		if (Pin->Direction == EGPD_Input) { ++InputCount; }
		else if (Pin->Direction == EGPD_Output) { ++OutputCount; }
	}
	if (InputCount != 2 || OutputCount != OutputTargets.Num() || Assignment->NumTargets() != OutputTargets.Num()
		|| Custom->Signature.Outputs.Num() != OutputTargets.Num())
	{ Result.Error = TEXT("刷新后的完整输入/输出集合、Signature 或 assignment 目标集合已变化。"); return Result; }
	for (int32 Index = 0; Index < Result.Outputs.Num(); ++Index)
	{
		const int32 TargetIndex = Assignment->FindAssignmentTarget(OutputTargets[Index]);
		UEdGraphPin* TargetPin = FindAssignmentPin(Override, EGPD_Input, OverrideNames[Index]);
		UEdGraphPin* Value = FindAssignmentPin(Custom, EGPD_Output, Result.Outputs[Index].OutputPin);
		if (TargetIndex == INDEX_NONE || Assignment->GetAssignmentTarget(TargetIndex).GetType() != Types[Index]
			|| !TargetPin || UEdGraphSchema_Niagara::PinToTypeDefinition(TargetPin) != Types[Index]
			|| !Value || Value->LinkedTo.Num() != 1 || Value->LinkedTo[0] != TargetPin
			|| TargetPin->LinkedTo.Num() != 1 || TargetPin->LinkedTo[0] != Value
			|| UEdGraphSchema_Niagara::PinToTypeDefinition(Value) != Types[Index]
			|| Custom->Signature.Outputs[Index].GetName() != Value->PinName || Custom->Signature.Outputs[Index].GetType() != Types[Index])
		{ Result.Error = TEXT("属性刷新后某个显式多输出目标的连线、类型或 Signature 已变化。"); return Result; }
	}
	Result.DataInterfacePath = Interface->GetPathName();
	if (FunctionWork)
	{
		FNiagaraFunctionSignature Signature;
		FString ActualTemplate;
		if (!ReadAssignmentFunction(Interface, *FunctionWork, Signature, ActualTemplate, Result.Error)
			|| ActualTemplate != HlslBodyTemplate)
		{ if (Result.Error.IsEmpty()) { Result.Error = TEXT("实际 DI 函数签名与已接线 body 不符。"); } return Result; }
		if (!BindAssignmentFunction(Interface, Signature, Result.InterfaceParameter) || !OriginalNodesRemain() || !OriginalInterface.IsValid())
		{ Result.Error = TEXT("实际无实例数据 DI 不能绑定所声明的 CPU 纯函数。"); return Result; }
		Result.FunctionName = Signature.Name;
		for (int32 Index = 0; Index < FunctionWork->FunctionInputs.Num(); ++Index)
		{
			auto& FunctionInput = Result.FunctionInputs.AddDefaulted_GetRef();
			FunctionInput.Name = Signature.Inputs[Index + 1].GetName();
			FunctionInput.Type = Signature.Inputs[Index + 1].GetType();
			FunctionInput.HlslExpression = FunctionWork->FunctionInputs[Index].HlslExpression;
		}
		for (const auto& Output : Signature.Outputs)
		{
			auto& Target = Result.FunctionOutputs.AddDefaulted_GetRef();
			Target.Name = Output.GetName(); Target.Type = Output.GetType();
		}
		Result.bFunctionBound = true;
	}
	Result.bInterfaceEqualsTemplate = true;
	Result.CustomUsage = TEXT("Function");
	Result.bApplied = true;
	return Result;
}
}

FGGYGONiagaraAssignmentDIBinding UGGYGONiagaraCompileLibrary::ConnectAssignmentDataInterface(UNiagaraSystem* System,
	const FString& EmitterName, const FString& ScriptName, const FString& ModuleName,
	UNiagaraDataInterface* InterfaceTemplate, const TArray<FName>& OutputTargets, const FString& HlslBodyTemplate)
{
	return ConnectAssignmentWithContext(System, EmitterName, ScriptName, ModuleName,
		InterfaceTemplate, OutputTargets, HlslBodyTemplate, nullptr);
}

namespace
{
	bool BeginAuthoringData(UNiagaraSystem* System, FGGYGONiagaraAuthoringData& Result)
	{
		Result.SystemPath = GetPathNameSafe(System);
		if (!IsInGameThread() || !GEditor || GEditor->PlayWorld || !IsValid(System) || System->IsTemplate())
		{ Result.Error = TEXT("数据制作需要非 PIE Editor GameThread 的准确原 Niagara System。"); return false; }
		if (GEditor->IsTransactionActive())
		{ Result.Error = TEXT("已有 Editor 活动事务，不借用其它作者的事务。"); return false; }
		return true;
	}

	bool ReadAuthoringErrors(const FNiagaraExternalEditContext& Context, FString& Error)
	{
		for (const FText& Item : Context.Errors)
		{
			if (!Error.IsEmpty()) { Error += LINE_TERMINATOR; }
			Error += Item.ToString();
		}
		return !Context.HasErrors();
	}

	FNiagaraExt_StackItemReference AuthoringReference(UNiagaraSystem* System, const FString& EmitterName,
		const FString& ScriptName = FString(), const FString& ModuleName = FString(), int32 RendererIndex = INDEX_NONE)
	{
		FNiagaraExt_StackItemReference Ref;
		Ref.System = System;
		Ref.EmitterName = FName(*EmitterName);
		Ref.ScriptName = FName(*ScriptName);
		Ref.ModuleName = FName(*ModuleName);
		Ref.RendererIndex = RendererIndex;
		return Ref;
	}

	FNiagaraEmitterHandle* FindAuthoringEmitter(UNiagaraSystem* System, const FString& Name, FString& Error,
		const FGuid& Identity = FGuid())
	{
		FNiagaraEmitterHandle* Found = nullptr;
		for (FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
		{
			if (Identity.IsValid() ? Handle.GetId() != Identity : Handle.GetName() != FName(*Name)) { continue; }
			if (Found) { Error = TEXT("原 emitter 身份不唯一：") + Name; return nullptr; }
			Found = &Handle;
		}
		if (!Found || !Found->GetId().IsValid() || !IsValid(Found->GetInstance().Emitter) || !Found->GetEmitterData())
		{ Error = TEXT("准确原 emitter 或版本数据无效：") + Name; return nullptr; }
		return Found;
	}

	void FillAuthoringEmitter(const FNiagaraEmitterHandle& Handle, FGGYGONiagaraAuthoringData& Result)
	{
		Result.EmitterName = Handle.GetName().ToString();
		Result.EmitterHandleId = Handle.GetId();
		Result.UniqueEmitterName = Handle.GetInstance().Emitter->GetUniqueEmitterName();
	}

	bool ReadAuthoringRendererIdentities(const FNiagaraEmitterHandle& Handle, FGGYGONiagaraAuthoringData& Result)
	{
		FillAuthoringEmitter(Handle, Result);
		const auto& Renderers = Handle.GetEmitterData()->GetRenderers();
		for (int32 Index = 0; Index < Renderers.Num(); ++Index)
		{
			const UNiagaraRendererProperties* Renderer = Renderers[Index];
			if (!IsValid(Renderer)) { Result.Error = TEXT("原 renderer 数组存在失效项。"); return false; }
			auto& Row = Result.Renderers.AddDefaulted_GetRef();
			Row.RendererIndex = Index;
			Row.RendererClass = Renderer->GetClass()->GetPathName();
			Row.RendererPath = Renderer->GetPathName();
		}
		return true;
	}

	void FinishAuthoringData(FGGYGONiagaraAuthoringData& Result)
	{
		Result.bTransactionClosed = GEditor && !GEditor->IsTransactionActive();
		if (!Result.bTransactionClosed && Result.Error.IsEmpty()) { Result.Error = TEXT("数据作者事务尚未归还。"); }
		Result.bSucceeded = Result.Error.IsEmpty() && Result.bTransactionClosed;
	}

	bool ReadAuthoringEmitterData(UNiagaraSystem* System, const FNiagaraEmitterHandle& Handle,
		FGGYGONiagaraAuthoringData& Result)
	{
		FillAuthoringEmitter(Handle, Result);
		FNiagaraExternalEditContext Context;
		FNiagaraExt_EmitterData Data;
		UNiagaraExternalEditUtilities::GetEmitterData(AuthoringReference(System, Result.EmitterName), Data, Context);
		if (!ReadAuthoringErrors(Context, Result.Error)) { return false; }
		Result.PropertyValues = MoveTemp(Data.PropertyValues);
		return true;
	}

	UNiagaraRendererProperties* FindAuthoringRenderer(FNiagaraEmitterHandle& Handle, int32 Index, FString& Error)
	{
		const auto& Renderers = Handle.GetEmitterData()->GetRenderers();
		if (!Renderers.IsValidIndex(Index) || !IsValid(Renderers[Index]))
		{ Error = TEXT("原 emitter 没有准确存活的 renderer index。"); return nullptr; }
		return Renderers[Index];
	}

	bool ReadAuthoringRendererData(UNiagaraSystem* System, FNiagaraEmitterHandle& Handle, int32 Index,
		FGGYGONiagaraAuthoringData& Result)
	{
		UNiagaraRendererProperties* Renderer = FindAuthoringRenderer(Handle, Index, Result.Error);
		if (!Renderer) { return false; }
		FillAuthoringEmitter(Handle, Result);
		Result.RendererIndex = Index;
		Result.RendererClass = Renderer->GetClass()->GetPathName();
		Result.RendererPath = Renderer->GetPathName();
		const TStrongObjectPtr<UNiagaraRendererProperties> OriginalRenderer(Renderer);
		FNiagaraExternalEditContext Context;
		FNiagaraExt_RendererData Data;
		UNiagaraExternalEditUtilities::GetRendererData(AuthoringReference(System, Result.EmitterName,
			FString(), FString(), Index), Data, Context);
		if (!ReadAuthoringErrors(Context, Result.Error)) { return false; }
		Result.PropertyValues = MoveTemp(Data.PropertyValues);
		return true;
	}

	bool RequiresRendererSourceRefresh(const FProperty* Property)
	{
		// 原 Mesh/Sprite PostEdit 对 SourceMode、attribute binding、material binding 数组走同一派生刷新。
		if (Property->GetFName() == GET_MEMBER_NAME_CHECKED(UNiagaraMeshRendererProperties, SourceMode)) { return true; }
		if (const auto* Struct = CastField<FStructProperty>(Property))
		{
			return Struct->Struct == FNiagaraVariableAttributeBinding::StaticStruct();
		}
		const auto* Array = CastField<FArrayProperty>(Property);
		const auto* Element = Array ? CastField<FStructProperty>(Array->Inner) : nullptr;
		return Element && Element->Struct == FNiagaraMaterialAttributeBinding::StaticStruct();
	}

	bool ApplyRendererPropertyBatch(UNiagaraRendererProperties* Renderer, const FString& PropertyValues, FString& Error)
	{
		// 只暂存 renderer；无 Emitter outer，原属性通知不会为目标 NS 生成中间编译请求。
		const TStrongObjectPtr<UNiagaraRendererProperties> Staged(Cast<UNiagaraRendererProperties>(
			StaticDuplicateObject(Renderer, GetTransientPackage())));
		if (!Staged.IsValid()) { Error = TEXT("不能创建 renderer 的临时属性编辑副本。"); return false; }
		Staged->SetFlags(RF_Transient);
		Staged->ClearFlags(RF_Public | RF_Standalone | RF_Transactional);
		TArray<FName> WrittenNames;
		// 沿当前原 provider 的公开实现保留权限、blocklist、JSON/对象/枚举/类型转换，不另建解析器。
		if (!UToolsetLibrary::SetObjectProperties(Staged.Get(), PropertyValues, WrittenNames, EBypassContainerCheck::Yes))
		{ Error = TEXT("Renderer 批属性校验失败；原对象尚未写入，请查原 Toolset 属性诊断。"); return false; }
		TArray<FProperty*> Properties;
		FProperty* SourceRefreshProperty = nullptr;
		bool bWritesMotionVector = false;
		for (const FName Name : WrittenNames)
		{
			FProperty* Property = PropertyAccessUtil::FindPropertyByName(Name, Renderer->GetClass());
			if (!Property) { Error = TEXT("批属性的原 renderer 字段已不存在：") + Name.ToString(); return false; }
			Properties.Add(Property);
			if (!SourceRefreshProperty && RequiresRendererSourceRefresh(Property)) { SourceRefreshProperty = Property; }
			bWritesMotionVector |= Property->GetFName() == GET_MEMBER_NAME_CHECKED(UNiagaraRendererProperties, MotionVectorSetting);
		}
		if (Properties.IsEmpty()) { return true; }
		FVersionedNiagaraEmitterData* EmitterData = Renderer->GetEmitterData();
		if (SourceRefreshProperty && bWritesMotionVector && (!EmitterData || !IsValid(EmitterData->GraphSource)))
		{ Error = TEXT("MotionVector 批属性缺少原 emitter 源图，不能提交。"); return false; }

		// 与原生 set_editor_properties 一样，整批 Pre/Post 包围无单字段通知的公开属性复制。
		Renderer->PreEditChange(nullptr);
		ON_SCOPE_EXIT { Renderer->PostEditChange(); };
		for (FProperty* Property : Properties)
		{
			const EPropertyAccessResultFlags Access = PropertyAccessUtil::SetPropertyValue_Object(Property, Renderer, Property,
				Property->ContainerPtrToValuePtr<void>(Staged.Get()), INDEX_NONE,
				PropertyAccessUtil::EditorReadOnlyFlags, EPropertyAccessChangeNotifyMode::Never);
			if (Access != EPropertyAccessResultFlags::Success)
			{
				Error = FString::Printf(TEXT("原 renderer 批属性提交失败：%s Access=%u；保留实际部分写入。"),
					*Property->GetName(), static_cast<uint32>(Access));
				return false;
			}
		}
		if (SourceRefreshProperty)
		{
			// 先保留原 MotionVector dirty；该接口只更新图 ChangeId，不发编译请求。
			if (bWritesMotionVector) { EmitterData->GraphSource->MarkNotSynchronized(TEXT("Renderer MotionVectorSetting changed")); }
			// 一次真实字段事件走原 protected 派生链：缓存全部绑定、previous/参数 rename、原更新上下文及请求。
			FPropertyChangedEvent SourceEvent(SourceRefreshProperty, EPropertyChangeType::ValueSet);
			Renderer->PostEditChangeProperty(SourceEvent);
		}
		for (FProperty* Property : Properties)
		{
			if (Property == SourceRefreshProperty) { continue; }
			const bool bGroupedSource = SourceRefreshProperty && (RequiresRendererSourceRefresh(Property)
				|| Property->GetFName() == GET_MEMBER_NAME_CHECKED(UNiagaraRendererProperties, MotionVectorSetting));
			// 已收束的派生字段仍发整成员通知，保留成员初始化状态及观察者身份，不重复启动同一派生链。
			FPropertyChangedEvent Event(bGroupedSource ? nullptr : Property, EPropertyChangeType::ValueSet);
			Event.SetActiveMemberProperty(Property);
			Renderer->PostEditChangeProperty(Event);
		}
		// 其余真实字段事件保留 Mesh 的 clamp/flipbook/MIC、Sprite 的 Cutout/DDC/MIC 及原 bindings 重建。
		return true;
	}
}

FGGYGONiagaraAuthoringData UGGYGONiagaraCompileLibrary::AuthoringAddEmitter(UNiagaraSystem* System,
	UNiagaraEmitter* TemplateEmitter, const FString& EmitterName)
{
	FGGYGONiagaraAuthoringData Result;
	if (!BeginAuthoringData(System, Result)) { return Result; }
	const FName RequestedName(*EmitterName);
	if (RequestedName.IsNone() || !IsValid(TemplateEmitter) || TemplateEmitter->IsTemplate()
		|| !TemplateEmitter->GetEmitterData(TemplateEmitter->GetExposedVersion().VersionGuid))
	{ Result.Error = TEXT("Emitter 创建需要准确非空名称及真实版本模板。"); return Result; }
	for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
	{
		if (Handle.GetName() == RequestedName) { Result.Error = TEXT("请求的 emitter 名称已存在：") + EmitterName; return Result; }
	}
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	const TStrongObjectPtr<UNiagaraEmitter> OriginalTemplate(TemplateEmitter);
	const int32 BeforeCount = System->GetEmitterHandles().Num();
	FGuid CreatedId;
	{
		const FScopedTransaction Transaction(NSLOCTEXT("GGYGONiagara", "AuthoringAddEmitter", "创建准确 Niagara emitter"));
		CreatedId = FNiagaraEditorUtilities::AddEmitterToSystem(*System, *TemplateEmitter,
			TemplateEmitter->GetExposedVersion().VersionGuid, true);
		if (!CreatedId.IsValid()) { Result.Error = TEXT("原生创建没有返回有效 emitter handle ID。"); return Result; }
		FNiagaraEmitterHandle* Created = FindAuthoringEmitter(System, EmitterName, Result.Error, CreatedId);
		if (!Created || System->GetEmitterHandles().Num() != BeforeCount + 1)
		{ if (Result.Error.IsEmpty()) { Result.Error = TEXT("原生创建改变了预期 emitter 集合。"); } return Result; }
		Created->SetName(RequestedName, *System);
	}
	FNiagaraEmitterHandle* Created = FindAuthoringEmitter(System, EmitterName, Result.Error, CreatedId);
	if (!Created) { return Result; }
	if (Created->GetName().ToString() != EmitterName || Created->GetInstance().Emitter->GetUniqueEmitterName() != EmitterName)
	{ Result.Error = TEXT("原生作者名称或 unique emitter name 不同于准确请求，拒绝后缀替代。"); return Result; }
	FillAuthoringEmitter(*Created, Result);
	FinishAuthoringData(Result);
	return Result;
}

FGGYGONiagaraAuthoringData UGGYGONiagaraCompileLibrary::AuthoringGetSystemSummary(UNiagaraSystem* System)
{
	FGGYGONiagaraAuthoringData Result;
	if (!BeginAuthoringData(System, Result)) { return Result; }
	TSet<FName> Names;
	for (const FNiagaraEmitterHandle& Handle : System->GetEmitterHandles())
	{
		if (Names.Contains(Handle.GetName()) || !Handle.GetId().IsValid() || !IsValid(Handle.GetInstance().Emitter) || !Handle.GetEmitterData())
		{ Result.Error = TEXT("原 system emitter 名称、身份或数据无效。"); return Result; }
		Names.Add(Handle.GetName());
		auto& Row = Result.Emitters.AddDefaulted_GetRef();
		Row.EmitterName = Handle.GetName().ToString();
		Row.UniqueEmitterName = Handle.GetInstance().Emitter->GetUniqueEmitterName();
		Row.EmitterHandleId = Handle.GetId();
		Row.bEnabled = Handle.GetIsEnabled();
		Row.SimTarget = StaticEnum<ENiagaraSimTarget>()->GetNameStringByValue(static_cast<int64>(Handle.GetEmitterData()->SimTarget));
	}
	FinishAuthoringData(Result);
	return Result;
}

FGGYGONiagaraAuthoringData UGGYGONiagaraCompileLibrary::AuthoringGetRendererIdentities(UNiagaraSystem* System,
	const FString& EmitterName)
{
	FGGYGONiagaraAuthoringData Result;
	if (!BeginAuthoringData(System, Result)) { return Result; }
	if (const auto* Handle = FindAuthoringEmitter(System, EmitterName, Result.Error)) { ReadAuthoringRendererIdentities(*Handle, Result); }
	FinishAuthoringData(Result);
	return Result;
}

FGGYGONiagaraAuthoringData UGGYGONiagaraCompileLibrary::AuthoringGetEmitterData(UNiagaraSystem* System,
	const FString& EmitterName)
{
	FGGYGONiagaraAuthoringData Result;
	if (!BeginAuthoringData(System, Result)) { return Result; }
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	if (const auto* Handle = FindAuthoringEmitter(System, EmitterName, Result.Error)) { ReadAuthoringEmitterData(System, *Handle, Result); }
	FinishAuthoringData(Result);
	return Result;
}

FGGYGONiagaraAuthoringData UGGYGONiagaraCompileLibrary::AuthoringSetEmitterData(UNiagaraSystem* System,
	const FString& EmitterName, const FString& PropertyValues)
{
	FGGYGONiagaraAuthoringData Result;
	if (!BeginAuthoringData(System, Result)) { return Result; }
	if (PropertyValues.TrimStartAndEnd().IsEmpty()) { Result.Error = TEXT("Emitter 属性写入缺显式 JSON。"); return Result; }
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	auto* Before = FindAuthoringEmitter(System, EmitterName, Result.Error);
	if (!Before) { return Result; }
	const FGuid Id = Before->GetId();
	const TStrongObjectPtr<UNiagaraEmitter> OriginalEmitter(Before->GetInstance().Emitter);
	FNiagaraExternalEditContext Context;
	FNiagaraExt_EmitterData Data; Data.PropertyValues = PropertyValues;
	UNiagaraExternalEditUtilities::SetEmitterData(AuthoringReference(System, EmitterName), Data, Context);
	if (!ReadAuthoringErrors(Context, Result.Error)) { return Result; }
	auto* After = FindAuthoringEmitter(System, EmitterName, Result.Error, Id);
	if (!After || After->GetInstance().Emitter != OriginalEmitter.Get())
	{ if (Result.Error.IsEmpty()) { Result.Error = TEXT("属性通知后原 emitter 已改变。"); } return Result; }
	ReadAuthoringEmitterData(System, *After, Result);
	FinishAuthoringData(Result);
	return Result;
}

FGGYGONiagaraAuthoringData UGGYGONiagaraCompileLibrary::AuthoringAddRenderer(UNiagaraSystem* System,
	const FString& EmitterName, TSubclassOf<UNiagaraRendererProperties> RendererClass)
{
	FGGYGONiagaraAuthoringData Result;
	if (!BeginAuthoringData(System, Result)) { return Result; }
	if (!RendererClass || RendererClass->HasAnyClassFlags(CLASS_Abstract))
	{ Result.Error = TEXT("Renderer 创建缺少准确可实例化 class。"); return Result; }
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	auto* Before = FindAuthoringEmitter(System, EmitterName, Result.Error);
	if (!Before) { return Result; }
	const FGuid Id = Before->GetId();
	const int32 BeforeCount = Before->GetEmitterData()->GetRenderers().Num();
	const TStrongObjectPtr<UNiagaraEmitter> OriginalEmitter(Before->GetInstance().Emitter);
	FNiagaraExternalEditContext Context;
	FNiagaraExt_RendererRef Added;
	UNiagaraExternalEditUtilities::AddRenderer(AuthoringReference(System, EmitterName), RendererClass, Added, Context);
	if (!ReadAuthoringErrors(Context, Result.Error)) { return Result; }
	auto* After = FindAuthoringEmitter(System, EmitterName, Result.Error, Id);
	if (!After || After->GetInstance().Emitter != OriginalEmitter.Get()
		|| After->GetEmitterData()->GetRenderers().Num() != BeforeCount + 1 || Added.RendererIndex != BeforeCount)
	{ if (Result.Error.IsEmpty()) { Result.Error = TEXT("Renderer 创建改变了原 emitter/数组或插入顺序。"); } return Result; }
	UNiagaraRendererProperties* Renderer = FindAuthoringRenderer(*After, Added.RendererIndex, Result.Error);
	if (!Renderer || Renderer->GetClass() != RendererClass.Get())
	{ if (Result.Error.IsEmpty()) { Result.Error = TEXT("原生新 renderer class 不同于请求。"); } return Result; }
	FillAuthoringEmitter(*After, Result);
	Result.RendererIndex = Added.RendererIndex;
	Result.RendererClass = Renderer->GetClass()->GetPathName();
	Result.RendererPath = Renderer->GetPathName();
	FinishAuthoringData(Result);
	return Result;
}

FGGYGONiagaraAuthoringData UGGYGONiagaraCompileLibrary::AuthoringGetRendererData(UNiagaraSystem* System,
	const FString& EmitterName, int32 RendererIndex)
{
	FGGYGONiagaraAuthoringData Result;
	if (!BeginAuthoringData(System, Result)) { return Result; }
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	if (auto* Handle = FindAuthoringEmitter(System, EmitterName, Result.Error)) { ReadAuthoringRendererData(System, *Handle, RendererIndex, Result); }
	FinishAuthoringData(Result);
	return Result;
}

FGGYGONiagaraAuthoringData UGGYGONiagaraCompileLibrary::AuthoringSetRendererData(UNiagaraSystem* System,
	const FString& EmitterName, int32 RendererIndex, const FString& PropertyValues)
{
	FGGYGONiagaraAuthoringData Result;
	if (!BeginAuthoringData(System, Result)) { return Result; }
	if (PropertyValues.TrimStartAndEnd().IsEmpty()) { Result.Error = TEXT("Renderer 属性写入缺显式 JSON。"); return Result; }
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	auto* Before = FindAuthoringEmitter(System, EmitterName, Result.Error);
	if (!Before) { return Result; }
	const FGuid Id = Before->GetId();
	const TStrongObjectPtr<UNiagaraEmitter> OriginalEmitter(Before->GetInstance().Emitter);
	UNiagaraRendererProperties* Renderer = FindAuthoringRenderer(*Before, RendererIndex, Result.Error);
	if (!Renderer) { return Result; }
	const TStrongObjectPtr<UNiagaraRendererProperties> OriginalRenderer(Renderer);
	LogAuthoringMemoryBoundary(System, TEXT("RendererBeforeWrite"), EmitterName, RendererIndex);
	ON_SCOPE_EXIT { LogAuthoringMemoryBoundary(OriginalSystem.Get(), TEXT("RendererReturn"), EmitterName, RendererIndex); };
	FNiagaraExternalEditContext Context;
	if ((Renderer->IsA<UNiagaraMeshRendererProperties>() || Renderer->IsA<UNiagaraSpriteRendererProperties>())
		&& GetAuthoringCompileTaskLimit() == 0)
	{
		// 原受控同步制作段完整提交 Mesh/Sprite（含原派生类）属性；其它调用保留原工具路径。
		if (!ApplyRendererPropertyBatch(Renderer, PropertyValues, Result.Error)) { return Result; }
	}
	else
	{
		FNiagaraExt_RendererData Data; Data.PropertyValues = PropertyValues;
		UNiagaraExternalEditUtilities::SetRendererData(AuthoringReference(System, EmitterName, FString(), FString(), RendererIndex), Data, Context);
	}
	LogAuthoringMemoryBoundary(System, TEXT("RendererAfterWrite"), EmitterName, RendererIndex);
	if (!ReadAuthoringErrors(Context, Result.Error)) { return Result; }
	auto* After = FindAuthoringEmitter(System, EmitterName, Result.Error, Id);
	if (!After || After->GetInstance().Emitter != OriginalEmitter.Get()
		|| FindAuthoringRenderer(*After, RendererIndex, Result.Error) != OriginalRenderer.Get())
	{ if (Result.Error.IsEmpty()) { Result.Error = TEXT("属性通知后原 renderer 身份已改变。"); } return Result; }
	ReadAuthoringRendererData(System, *After, RendererIndex, Result);
	FinishAuthoringData(Result);
	return Result;
}

namespace
{
	FString AuthoringTypePath(const FNiagaraTypeDefinition& Type)
	{
		return GetPathNameSafe(Type.IsEnum() ? static_cast<const UObject*>(Type.GetEnum()) : Type.GetStruct());
	}

	UNiagaraNodeFunctionCall* FindAuthoringNode(UNiagaraSystem* System, const FString& EmitterName,
		const FString& ModuleName, FString& Error)
	{
		const UNiagaraScriptSource* Source = nullptr;
		if (EmitterName.IsEmpty())
		{
			const UNiagaraScript* Script = System->GetSystemSpawnScript();
			Source = Script ? Cast<UNiagaraScriptSource>(Script->GetLatestSource()) : nullptr;
		}
		else
		{
			const FNiagaraEmitterHandle* Handle = FindAuthoringEmitter(System, EmitterName, Error);
			Source = Handle ? Cast<UNiagaraScriptSource>(Handle->GetEmitterData()->GraphSource) : nullptr;
		}
		UNiagaraGraph* Graph = Source ? Source->NodeGraph.Get() : nullptr;
		if (!Graph) { if (Error.IsEmpty()) { Error = TEXT("准确作者目标缺可编辑源图。"); } return nullptr; }
		UNiagaraNodeFunctionCall* Found = nullptr;
		for (UEdGraphNode* Node : Graph->Nodes)
		{
			auto* Candidate = Cast<UNiagaraNodeFunctionCall>(Node);
			if (Candidate && Candidate->GetFunctionName() == ModuleName)
			{
				if (Found) { Error = TEXT("原图模块名不唯一：") + ModuleName; return nullptr; }
				Found = Candidate;
			}
		}
		if (!IsValid(Found) || !Found->NodeGuid.IsValid())
		{ Error = TEXT("无法读回原模块节点及 GUID：") + ModuleName; return nullptr; }
		return Found;
	}


	UNiagaraStackScriptItemGroup* FindAuthoringScript(const TSharedRef<FNiagaraSystemViewModel>& ViewModel,
		const FString& EmitterName, const FString& ScriptName, FString& Error)
	{
		const int64 UsageValue = StaticEnum<ENiagaraScriptUsage>()->GetValueByNameString(ScriptName);
		if (UsageValue == INDEX_NONE)
		{ Error = TEXT("未知 Niagara ScriptUsage：") + ScriptName; return nullptr; }
		UNiagaraStackViewModel* Stack = nullptr;
		if (EmitterName.IsEmpty()) { Stack = ViewModel->GetSystemStackViewModel(); }
		else
		{
			for (const TSharedRef<FNiagaraEmitterHandleViewModel>& Emitter : ViewModel->GetEmitterHandleViewModels())
			{
				const FNiagaraEmitterHandle* Handle = Emitter->GetEmitterHandle();
				if (Handle && Handle->GetName() == FName(*EmitterName))
				{
					if (Stack) { Error = TEXT("Emitter 名称不唯一：") + EmitterName; return nullptr; }
					Stack = Emitter->GetEmitterStackViewModel();
				}
			}
		}
		UNiagaraStackEntry* Root = Stack ? Stack->GetRootEntry() : nullptr;
		if (!IsValid(Root) || Root->IsFinalized())
		{ Error = TEXT("原 System/Emitter 没有有效作者栈：") + EmitterName; return nullptr; }
		TArray<UNiagaraStackScriptItemGroup*> Groups;
		Root->GetUnfilteredChildrenOfType(Groups, true);
		UNiagaraStackScriptItemGroup* Match = nullptr;
		for (UNiagaraStackScriptItemGroup* Group : Groups)
		{
			if (Group->GetScriptUsage() == static_cast<ENiagaraScriptUsage>(UsageValue)
				&& !Group->GetScriptUsageId().IsValid())
			{
				if (Match) { Error = TEXT("默认 ScriptUsage 栈不唯一：") + ScriptName; return nullptr; }
				Match = Group;
			}
		}
		if (!Match) { Error = TEXT("找不到默认 ScriptUsage 栈：") + ScriptName; }
		return Match;
	}

	bool RefreshAuthoringModuleInputs(UNiagaraSystem* System, const FGGYGONiagaraAuthoringWorkItem& Work,
		const TSharedRef<FNiagaraSystemViewModel>& ViewModel, const FString& ModuleName, const FGuid& NodeGuid, FString& Error)
	{
		UNiagaraStackScriptItemGroup* Group = FindAuthoringScript(ViewModel, Work.EmitterName, Work.ScriptName, Error);
		if (!Group) { return false; }
		TArray<UNiagaraStackModuleItem*> Modules;
		Group->GetUnfilteredChildrenOfType(Modules);
		UNiagaraStackModuleItem* const* Found = Modules.FindByPredicate([&NodeGuid](UNiagaraStackModuleItem* Module)
		{
			return IsValid(Module) && !Module->IsFinalized() && Module->GetModuleNode().NodeGuid == NodeGuid;
		});
		if (!Found || (*Found)->GetModuleNode().GetFunctionName() != ModuleName)
		{ Error = TEXT("输入写后找不到同一作者栈的原模块，未刷新其它模块。"); return false; }
		const TWeakObjectPtr<UNiagaraStackModuleItem> OriginalModule(*Found);
		const TWeakObjectPtr<UNiagaraNodeFunctionCall> OriginalNode(&(*Found)->GetModuleNode());
		// hidden 位由父输入树推送；局部递归刷新重算 switch/条件，不触发全 NS RefreshAll。
		(*Found)->RefreshChildren();
		if (!OriginalModule.IsValid() || OriginalModule->IsFinalized() || !OriginalNode.IsValid()
			|| &OriginalModule->GetModuleNode() != OriginalNode.Get() || OriginalNode->NodeGuid != NodeGuid
			|| FindAuthoringNode(System, Work.EmitterName, ModuleName, Error) != OriginalNode.Get())
		{ if (Error.IsEmpty()) { Error = TEXT("局部输入树刷新后原模块或节点已退役。"); } return false; }
		return true;
	}

	/** 仅在当前追加段内保存原模块身份；来源为原 Group 直接子项，不持有输入树或跨调用缓存。 */
	struct FAuthoringModuleIdentity
	{
		TWeakObjectPtr<UNiagaraNodeFunctionCall> Node;
		FGuid NodeGuid;
		FString ModuleName;
		UClass* NodeClass = nullptr;
		TWeakObjectPtr<UNiagaraScript> Script;
		bool bEnabled = false;
	};

	bool ReadAuthoringModules(UNiagaraStackScriptItemGroup* Group,
		TArray<FAuthoringModuleIdentity>& Modules, FString& Error)
	{
		UNiagaraNodeOutput* Output = IsValid(Group) && !Group->IsFinalized() ? Group->GetScriptOutputNode() : nullptr;
		if (!IsValid(Output)) { Error = TEXT("原作者栈或输出节点已退役。"); return false; }
		TArray<UNiagaraStackModuleItem*> Items;
		// Group 原生刷新按执行顺序保存直接 ModuleItem，不递归输入，也不调用隐含全栈遍历的 GetModuleIndex。
		Group->GetUnfilteredChildrenOfType(Items);
		for (UNiagaraStackModuleItem* Item : Items)
		{
			if (!IsValid(Item) || Item->IsFinalized()) { Error = TEXT("原作者模块项已退役。"); return false; }
			UNiagaraNodeFunctionCall& Node = Item->GetModuleNode();
			if (!Node.NodeGuid.IsValid() || Node.GetGraph() != Output->GetGraph())
			{ Error = TEXT("原作者模块 GUID 或图归属无效。"); return false; }
			auto& Row = Modules.AddDefaulted_GetRef();
			Row.Node = &Node; Row.NodeGuid = Node.NodeGuid; Row.ModuleName = Node.GetFunctionName();
			Row.NodeClass = Node.GetClass(); Row.Script = Node.FunctionScript.Get(); Row.bEnabled = Item->GetIsEnabled();
		}
		return true;
	}

	bool SameAuthoringModule(const FAuthoringModuleIdentity& A, const FAuthoringModuleIdentity& B)
	{
		return A.Node.IsValid() && B.Node.IsValid() && A.Node == B.Node && A.NodeGuid == B.NodeGuid
			&& A.ModuleName == B.ModuleName && A.NodeClass == B.NodeClass && A.Script == B.Script && A.bEnabled == B.bEnabled;
	}

	bool RefreshAndVerifyAuthoringAppend(const TWeakObjectPtr<UNiagaraStackScriptItemGroup>& Group,
		const TArray<FAuthoringModuleIdentity>& Before, const TArray<FAuthoringModuleIdentity>& Added,
		int32& FailedAddedIndex, FString& Error)
	{
		FailedAddedIndex = INDEX_NONE;
		if (!Group.IsValid() || Group->IsFinalized()) { Error = TEXT("追加后原作者栈已退役。"); return false; }
		Group->RefreshChildren();
		TArray<FAuthoringModuleIdentity> After;
		if (!ReadAuthoringModules(Group.Get(), After, Error)) { return false; }
		if (After.Num() != Before.Num() + Added.Num())
		{ Error = TEXT("追加后的实际模块集合数量不符。"); return false; }
		for (int32 Index = 0; Index < Before.Num(); ++Index)
		{
			if (!SameAuthoringModule(Before[Index], After[Index]))
			{ Error = FString::Printf(TEXT("追加改变了原模块前缀身份或执行顺序：%d。"), Index); return false; }
		}
		for (int32 Index = 0; Index < Added.Num(); ++Index)
		{
			if (!SameAuthoringModule(Added[Index], After[Before.Num() + Index]))
			{ FailedAddedIndex = Index; Error = TEXT("新增模块的实际身份、顺序、类型、Script 或启用状态不符。"); return false; }
		}
		return true;
	}

	bool AddAuthoringModuleNode(UNiagaraSystem* System, UNiagaraNodeOutput* Output, UNiagaraScript* ModuleAsset,
		const TArray<FGGYGONiagaraAuthoringTarget>& Targets, FAuthoringModuleIdentity& Added, bool& bGraphChanged, FString& Error)
	{
		if (!IsValid(Output)) { Error = TEXT("追加前原作者输出已退役。"); return false; }
		bGraphChanged = true;
		System->Modify();
		UNiagaraNodeFunctionCall* Node = nullptr;
		if (ModuleAsset)
		{
			Node = FNiagaraStackGraphUtilities::AddScriptModuleToStack(ModuleAsset, *Output, INDEX_NONE,
				FString(), ModuleAsset->GetLatestScriptData()->Version.VersionGuid);
		}
		else
		{
			TArray<FNiagaraVariable> Variables;
			TArray<FString> Defaults;
			for (const auto& Target : Targets) { Variables.Emplace(Target.Type, Target.Name); Defaults.Add(FString()); }
			Node = FNiagaraStackGraphUtilities::AddParameterModuleToStack(Variables, *Output, INDEX_NONE, Defaults);
		}
		if (!IsValid(Node) || !Node->NodeGuid.IsValid() || Node->GetGraph() != Output->GetGraph()
			|| Node->IsA<UNiagaraNodeAssignment>() != (ModuleAsset == nullptr)
			|| (ModuleAsset && Node->FunctionScript != ModuleAsset))
		{ Error = TEXT("原生图入口未返回准确新模块及请求类型、Script。"); return false; }
		Added.Node = Node; Added.NodeGuid = Node->NodeGuid; Added.ModuleName = Node->GetFunctionName();
		Added.NodeClass = Node->GetClass(); Added.Script = Node->FunctionScript.Get(); Added.bEnabled = true;
		return true;
	}

	bool AppendAuthoringModule(UNiagaraSystem* System, const FGGYGONiagaraAuthoringWorkItem& Work,
		UNiagaraScript* ModuleAsset, const TArray<FGGYGONiagaraAuthoringTarget>& Targets,
		const TSharedRef<FNiagaraSystemViewModel>& ViewModel,
		FString& ModuleName, FGuid& NodeGuid, bool& bGraphChanged, FString& Error)
	{
		const TWeakObjectPtr<UNiagaraStackScriptItemGroup> Group(FindAuthoringScript(ViewModel, Work.EmitterName, Work.ScriptName, Error));
		if (!Group.IsValid()) { return false; }
		TArray<FAuthoringModuleIdentity> Before;
		if (!ReadAuthoringModules(Group.Get(), Before, Error)) { return false; }
		TArray<FAuthoringModuleIdentity> Added;
		auto& NewModule = Added.AddDefaulted_GetRef();
		if (!AddAuthoringModuleNode(System, Group->GetScriptOutputNode(), ModuleAsset, Targets, NewModule, bGraphChanged, Error)) { return false; }
		ModuleName = NewModule.ModuleName; NodeGuid = NewModule.NodeGuid;
		int32 FailedAddedIndex;
		return RefreshAndVerifyAuthoringAppend(Group, Before, Added, FailedAddedIndex, Error);
	}

	bool AppendAuthoringAssignmentSegment(UNiagaraSystem* System, const FGGYGONiagaraAuthoringWorkItem& Work,
		const TSharedRef<FNiagaraSystemViewModel>& ViewModel, int32 Begin, int32 End,
		FGGYGONiagaraAuthoringWorkResult& Result, bool& bGraphChanged)
	{
		const TWeakObjectPtr<UNiagaraStackScriptItemGroup> Group(FindAuthoringScript(ViewModel, Work.EmitterName, Work.ScriptName, Result.Error));
		if (!Group.IsValid()) { return false; }
		TArray<FAuthoringModuleIdentity> Before;
		if (!ReadAuthoringModules(Group.Get(), Before, Result.Error)) { return false; }
		const TWeakObjectPtr<UNiagaraNodeOutput> Output(Group->GetScriptOutputNode());
		TArray<FAuthoringModuleIdentity> Added;
		Added.Reserve(End - Begin);
		for (int32 Index = Begin; Index < End; ++Index)
		{
			Result.FailedSubIndex = Index;
			TArray<FGGYGONiagaraAuthoringTarget> Targets;
			auto& Target = Targets.AddDefaulted_GetRef();
			Target.Name = Work.Assignments[Index].Name; Target.Type = Work.Assignments[Index].Type;
			auto& NewModule = Added.AddDefaulted_GetRef();
			if (!AddAuthoringModuleNode(System, Output.Get(), nullptr, Targets, NewModule, bGraphChanged, Result.Error)) { return false; }
			auto& Receipt = Result.Modules.AddDefaulted_GetRef();
			Receipt.Index = Index; Receipt.ModuleName = NewModule.ModuleName; Receipt.NodeGuid = NewModule.NodeGuid;
		}
		int32 FailedAddedIndex;
		if (!RefreshAndVerifyAuthoringAppend(Group, Before, Added, FailedAddedIndex, Result.Error))
		{
			Result.FailedSubIndex = FailedAddedIndex == INDEX_NONE ? Begin : Begin + FailedAddedIndex;
			return false;
		}
		return true;
	}

	bool SetAuthoringInput(UNiagaraSystem* System, const FGGYGONiagaraAuthoringWorkItem& Work,
		const FString& ModuleName, const FGuid& NodeGuid, const FGGYGONiagaraAuthoringInput& Requested,
		FNiagaraExternalEditContext& Context, FGGYGONiagaraAuthoringInput& Actual, FString& Error)
	{
		auto Ref = AuthoringReference(System, Work.EmitterName, Work.ScriptName, ModuleName);
		Ref.InputNameStack = Requested.NamePath;
		// 保留原 inline/static/edit-condition 校验和 typed setter，不复制其私有解析器。
		UNiagaraExternalEditUtilities::SetStackInputData(Ref, Requested.InputData, Context);
		if (!ReadAuthoringErrors(Context, Error)) { return false; }
		// setter 可因 static switch/条件变化替换输入；新引用重新解析，不复用其单操作缓存。
		auto ReadRef = AuthoringReference(System, Work.EmitterName, Work.ScriptName, ModuleName);
		ReadRef.InputNameStack = Requested.NamePath;
		FNiagaraExt_StackInputValue Readback;
		UNiagaraExternalEditUtilities::GetStackInputData(ReadRef, Readback, Context);
		if (!ReadAuthoringErrors(Context, Error)) { return false; }
		UNiagaraNodeFunctionCall* Node = FindAuthoringNode(System, Work.EmitterName, ModuleName, Error);
		if (!Node || Node->NodeGuid != NodeGuid || !Readback.IsValid())
		{ if (Error.IsEmpty()) { Error = TEXT("输入写后原模块身份或实际值无效。"); } return false; }
		Actual.NamePath = Requested.NamePath;
		Actual.InputData = MoveTemp(Readback);
		return true;
	}

	bool SetAuthoringExpression(UNiagaraSystem* System, const FGGYGONiagaraAuthoringWorkItem& Work,
		const FString& ModuleName, const FGuid& NodeGuid, FName Target, const FString& Expression,
		FNiagaraExternalEditContext& Context, FString& Error)
	{
		FGGYGONiagaraAuthoringInput Requested;
		Requested.NamePath.Add(Target);
		Requested.InputData.InitializeAs<FNiagaraExt_StackInputData_HlslExpression>().HlslExpression = Expression;
		FGGYGONiagaraAuthoringInput Actual;
		if (!SetAuthoringInput(System, Work, ModuleName, NodeGuid, Requested, Context, Actual, Error)) { return false; }
		const auto* Value = Actual.InputData.GetPtr<FNiagaraExt_StackInputData_HlslExpression>();
		if (!Value || Value->HlslExpression != Expression)
		{ Error = TEXT("原 HLSL 表达式写后读回不符。"); return false; }
		return true;
	}

	bool ReadAuthoringFloatLiteral(const FString& Text, float& Value)
	{
		// 只识别十进制字面；不把八进制、转换、括号或算式当成常量折叠。
		static const FRegexPattern Pattern(TEXT("^[+-]?(?:(?:0|[1-9][0-9]*)(?:\\.[0-9]*)?|\\.[0-9]+)(?:[eE][+-]?[0-9]+)?[fF]?$"));
		FRegexMatcher Match(Pattern, Text);
		if (!Match.FindNext()) { return false; }
		if (!Text.Contains(TEXT(".")) && !Text.Contains(TEXT("e"), ESearchCase::IgnoreCase)
			&& !Text.EndsWith(TEXT("f"), ESearchCase::IgnoreCase))
		{
			const int64 Integer = FCString::Strtoi64(*Text, nullptr, 10);
			if (Integer < MIN_int32 || Integer > MAX_int32) { return false; }
			// 裸整数先按 HLSL 整数语义转换；-0 转 float 为正零，-0.0/-0e0/-0f 才保留浮点负零。
			Value = static_cast<float>(Integer);
			return true;
		}
		Value = FCString::Atof(*Text);
		return FMath::IsFinite(Value);
	}

	bool MakeAuthoringLiteral(const FGGYGONiagaraStackAssignment& Assignment, FNiagaraExt_StackInputValue& Value)
	{
		const FString Expression = Assignment.HlslExpression.TrimStartAndEnd();
		if (Assignment.Type == FNiagaraTypeDefinition::GetBoolDef())
		{
			if (Expression != TEXT("true") && Expression != TEXT("false")) { return false; }
			Value.InitializeAs<FNiagaraBool>().SetValue(Expression == TEXT("true"));
			return true;
		}
		const int32 Count = Assignment.Type == FNiagaraTypeDefinition::GetFloatDef() ? 1
			: Assignment.Type == FNiagaraTypeDefinition::GetVec3Def() ? 3
			: Assignment.Type == FNiagaraTypeDefinition::GetQuatDef() ? 4 : 0;
		if (Count == 0) { return false; }
		TArray<FString> Components;
		if (Count == 1) { Components.Add(Expression); }
		else
		{
			const FString Constructor = FString::Printf(TEXT("float%d"), Count);
			if (!Expression.StartsWith(Constructor, ESearchCase::CaseSensitive)) { return false; }
			const FString Arguments = Expression.Mid(Constructor.Len()).TrimStartAndEnd();
			if (!Arguments.StartsWith(TEXT("(")) || !Arguments.EndsWith(TEXT(")"))) { return false; }
			Arguments.Mid(1, Arguments.Len() - 2).ParseIntoArray(Components, TEXT(","), false);
			if (Components.Num() != Count) { return false; }
		}
		float Values[4] = {};
		for (int32 Index = 0; Index < Count; ++Index)
		{
			if (!ReadAuthoringFloatLiteral(Components[Index].TrimStartAndEnd(), Values[Index])) { return false; }
		}
		if (Count == 1) { Value.InitializeAs<FNiagaraFloat>().Value = Values[0]; }
		else if (Count == 3)
		{
			const FVector3f Literal(Values[0], Values[1], Values[2]);
			Value.InitializeAs(FNiagaraTypeDefinition::GetVec3Struct(), reinterpret_cast<const uint8*>(&Literal));
		}
		else
		{
			const FQuat4f Literal(Values[0], Values[1], Values[2], Values[3]);
			Value.InitializeAs(FNiagaraTypeDefinition::GetQuatStruct(), reinterpret_cast<const uint8*>(&Literal));
		}
		return true;
	}

	bool SameAuthoringFloatBits(const float& Left, const float& Right)
	{
		return FMemory::Memcmp(&Left, &Right, sizeof(float)) == 0;
	}

	bool SameAuthoringLiteral(const FNiagaraExt_StackInputValue& Expected, const FNiagaraExt_StackInputValue& Actual)
	{
		// 调用方已核同一实际 struct；逐字段比较，避免把结构填充或 Quat 归一化带入值契约。
		if (const auto* Value = Expected.GetPtr<FNiagaraFloat>())
		{ return SameAuthoringFloatBits(Value->Value, Actual.Get<FNiagaraFloat>().Value); }
		if (const auto* Value = Expected.GetPtr<FNiagaraBool>())
		{ return Value->GetRawValue() == Actual.Get<FNiagaraBool>().GetRawValue(); }
		// float 数学类型通过 Niagara 实际注册的反射 struct 识别，不依赖 TBaseStructure 的模板特化。
		if (Expected.GetScriptStruct() == FNiagaraTypeDefinition::GetVec3Struct())
		{
			const auto& Value = *reinterpret_cast<const FVector3f*>(Expected.GetMemory());
			const auto& Readback = *reinterpret_cast<const FVector3f*>(Actual.GetMemory());
			return SameAuthoringFloatBits(Value.X, Readback.X) && SameAuthoringFloatBits(Value.Y, Readback.Y)
				&& SameAuthoringFloatBits(Value.Z, Readback.Z);
		}
		if (Expected.GetScriptStruct() == FNiagaraTypeDefinition::GetQuatStruct())
		{
			const auto& Value = *reinterpret_cast<const FQuat4f*>(Expected.GetMemory());
			const auto& Readback = *reinterpret_cast<const FQuat4f*>(Actual.GetMemory());
			return SameAuthoringFloatBits(Value.X, Readback.X) && SameAuthoringFloatBits(Value.Y, Readback.Y)
				&& SameAuthoringFloatBits(Value.Z, Readback.Z) && SameAuthoringFloatBits(Value.W, Readback.W);
		}
		return false;
	}

	/** 本次作者调用中已经成功接线的 DI 输出；只在同 emitter/stage 内消费，返栈即失效。 */
	struct FAuthoringLinkedOutput
	{
		FString EmitterName;
		FString ScriptName;
		FNiagaraVariableBase Variable;
	};

	bool SetAuthoringSystemAssignmentInput(UNiagaraSystem* System, const FGGYGONiagaraAuthoringWorkItem& Work,
		const FGGYGONiagaraStackAssignment& Assignment, const FGGYGONiagaraStackAssignmentResult& Receipt,
		const TArray<FAuthoringLinkedOutput>& LinkedOutputs, FNiagaraExternalEditContext& Context,
		FGGYGONiagaraAuthoringInput& Actual, FString& Error)
	{
		FGGYGONiagaraAuthoringInput Requested;
		Requested.NamePath.Add(Assignment.Name);
		if (!MakeAuthoringLiteral(Assignment, Requested.InputData))
		{
			const FString Expression = Assignment.HlslExpression.TrimStartAndEnd();
			for (const auto& Output : LinkedOutputs)
			{
				if (Output.EmitterName != Work.EmitterName || Output.ScriptName != Work.ScriptName
					|| Output.Variable.GetName().ToString() != Expression) { continue; }
				if (Output.Variable.GetType() != Assignment.Type)
				{ Error = TEXT("前序 DI 输出与 System assignment 的实际类型不同。"); return false; }
				auto& Linked = Requested.InputData.InitializeAs<FNiagaraExt_StackInputData_Linked>();
				Linked.LinkedVariable.Name = Output.Variable.GetName();
				Linked.LinkedVariable.Type = Output.Variable.GetType();
				break;
			}
			if (!Requested.InputData.IsValid())
			{
				// 复杂式及其它合法输入表示继续走原 HLSL；不改变公式、求值或 rand 的顺序。
				Requested.InputData.InitializeAs<FNiagaraExt_StackInputData_HlslExpression>().HlslExpression = Assignment.HlslExpression;
			}
		}
		if (!SetAuthoringInput(System, Work, Receipt.ModuleName, Receipt.NodeGuid, Requested, Context, Actual, Error)) { return false; }
		if (Requested.InputData.GetScriptStruct() != Actual.InputData.GetScriptStruct())
		{ Error = TEXT("System assignment 写后实际输入表示类型不同。"); return false; }
		if (const auto* Linked = Requested.InputData.GetPtr<FNiagaraExt_StackInputData_Linked>())
		{
			const auto& Readback = Actual.InputData.Get<FNiagaraExt_StackInputData_Linked>();
			if (Readback.LinkedVariable.Name == Linked->LinkedVariable.Name && Readback.LinkedVariable.Type == Linked->LinkedVariable.Type) { return true; }
		}
		else if (const auto* Hlsl = Requested.InputData.GetPtr<FNiagaraExt_StackInputData_HlslExpression>())
		{
			if (Actual.InputData.Get<FNiagaraExt_StackInputData_HlslExpression>().HlslExpression == Hlsl->HlslExpression) { return true; }
		}
		else
		{
			if (SameAuthoringLiteral(Requested.InputData, Actual.InputData)) { return true; }
		}
		Error = TEXT("System assignment 写后实际 typed 值／链接／HLSL 不符。");
		return false;
	}

	bool ValidateAuthoringWork(UNiagaraSystem* System, const FGGYGONiagaraAuthoringWorkItem& Work, FString& Error)
	{
		const int64 Usage = StaticEnum<ENiagaraScriptUsage>()->GetValueByNameString(Work.ScriptName);
		if (Usage == INDEX_NONE || (Work.EmitterName.IsEmpty()
			? (Usage != static_cast<int64>(ENiagaraScriptUsage::SystemSpawnScript)
				&& Usage != static_cast<int64>(ENiagaraScriptUsage::SystemUpdateScript))
			: !FindAuthoringEmitter(System, Work.EmitterName, Error)))
		{ if (Error.IsEmpty()) { Error = TEXT("制作项缺准确 emitter 或 System ScriptUsage。"); } return false; }
		if (Work.Kind == TEXT("Module"))
		{
			if (!IsValid(Work.ModuleAsset) || !Work.ModuleAsset->GetLatestScriptData())
			{ Error = TEXT("Module 制作项缺真实模块 Script。"); return false; }
			for (const auto& Input : Work.Inputs)
			{
				if (Input.NamePath.IsEmpty() || !Input.InputData.IsValid() || Input.NamePath.Contains(NAME_None))
				{ Error = TEXT("Module 输入缺准确名称路径或原 typed InputData。"); return false; }
			}
			return true;
		}
		if (Work.Kind == TEXT("Assignments"))
		{
			if (Work.Assignments.IsEmpty()) { Error = TEXT("Assignments 制作项为空。"); return false; }
			int32 AliveCount = 0;
			for (const auto& Assignment : Work.Assignments)
			{
				if (Assignment.Name.IsNone() || !Assignment.Type.IsValid() || Assignment.HlslExpression.TrimStartAndEnd().IsEmpty())
				{ Error = TEXT("assignment 缺名称、真实类型或原表达式。"); return false; }
				if (Assignment.Name == FName(TEXT("Particles.Alive")))
				{
					++AliveCount;
					if (!Work.FailureSourceReference.IsEmpty() && (Assignment.Type != FNiagaraTypeDefinition::GetBoolDef()
						|| Assignment.HlslExpression != Work.OriginalAliveExpression))
					{ Error = TEXT("失败上报必须对应本项原 Bool Alive 表达式。"); return false; }
				}
			}
			if (Work.FailureSourceReference.IsEmpty() != Work.OriginalAliveExpression.IsEmpty()
				|| (!Work.FailureSourceReference.IsEmpty() && (AliveCount != 1
					|| (Work.ScriptName != TEXT("ParticleSpawnScript") && Work.ScriptName != TEXT("ParticleUpdateScript")))))
			{ Error = TEXT("失败来源、原 Alive 或 Spawn/Update 屏障不完整。"); return false; }
			return true;
		}
		if (Work.Kind == TEXT("ParticleRead"))
		{
			if (!IsValid(Work.InterfaceTemplate) || Work.OutputTargets.IsEmpty()
				|| Work.OutputTargets[0].Type != FNiagaraTypeDefinition::GetBoolDef() || Work.HlslBodyTemplate.IsEmpty())
			{ Error = TEXT("ParticleRead 缺原 DI 模板、typed 输出或明确 Bool seed。"); return false; }
			TSet<FName> Names;
			for (const auto& Target : Work.OutputTargets)
			{
				if (Target.Name.IsNone() || !Target.Type.IsValid() || Names.Contains(Target.Name))
				{ Error = TEXT("ParticleRead typed 输出无效或重复。"); return false; }
				Names.Add(Target.Name);
			}
			return true;
		}
		if (Work.Kind == TEXT("AssignmentDI"))
		{
			if (!IsValid(Work.InterfaceTemplate) || Work.InterfaceTemplate->IsTemplate())
			{ Error = TEXT("AssignmentDI 制作需要实际非 CDO 模板对象。"); return false; }
			FNiagaraFunctionSignature Signature;
			FString Body;
			return ReadAssignmentFunction(Work.InterfaceTemplate, Work, Signature, Body, Error);
		}
		Error = TEXT("不支持的有限制作 Kind：") + Work.Kind;
		return false;
	}

	bool ApplyAuthoringWork(UNiagaraSystem* System, const FGGYGONiagaraAuthoringWorkItem& Work,
		FNiagaraExternalEditContext& Context, const TSharedRef<FNiagaraSystemViewModel>& ViewModel,
		FGGYGONiagaraAuthoringWorkResult& Result, bool& bGraphChanged,
		bool bUseNativeSystemInputs, const TArray<FAuthoringLinkedOutput>& LinkedOutputs)
	{
		if (Work.Kind == TEXT("Module"))
		{
			if (!AppendAuthoringModule(System, Work, Work.ModuleAsset, {}, ViewModel, Result.ModuleName, Result.NodeGuid, bGraphChanged, Result.Error)) { return false; }
			for (int32 Index = 0; Index < Work.Inputs.Num(); ++Index)
			{
				Result.FailedSubIndex = Index;
				auto& Actual = Result.Inputs.AddDefaulted_GetRef();
				if (!SetAuthoringInput(System, Work, Result.ModuleName, Result.NodeGuid, Work.Inputs[Index], Context, Actual, Result.Error)) { return false; }
				if (!RefreshAuthoringModuleInputs(System, Work, ViewModel, Result.ModuleName, Result.NodeGuid, Result.Error)) { return false; }
			}
		}
		else if (Work.Kind == TEXT("Assignments"))
		{
			int32 Begin = 0;
			while (Begin < Work.Assignments.Num())
			{
				int32 End = Begin;
				do
				{
					const bool bFailureBarrier = !Work.FailureSourceReference.IsEmpty()
						&& Work.Assignments[End].Name == FName(TEXT("Particles.Alive"));
					++End;
					if (bFailureBarrier) { break; }
				} while (End < Work.Assignments.Num());
				// 段内先按原序建独立节点，再合并原栈刷新；Alive 后继段须等待原 DI 接线成功。
				Result.FailedSubIndex = Begin;
				if (!AppendAuthoringAssignmentSegment(System, Work, ViewModel, Begin, End, Result, bGraphChanged)) { return false; }
				for (int32 Index = Begin; Index < End; ++Index)
				{
					Result.FailedSubIndex = Index;
					const auto& Assignment = Work.Assignments[Index];
					auto& Receipt = Result.Modules[Index];
					const bool bSystemInput = bUseNativeSystemInputs
						&& (Work.ScriptName == TEXT("EmitterSpawnScript") || Work.ScriptName == TEXT("EmitterUpdateScript"));
					if (bSystemInput)
					{
						auto& Actual = Result.Inputs.AddDefaulted_GetRef();
						if (!SetAuthoringSystemAssignmentInput(System, Work, Assignment, Receipt, LinkedOutputs, Context, Actual, Result.Error)) { return false; }
						const auto* Hlsl = Actual.InputData.GetPtr<FNiagaraExt_StackInputData_HlslExpression>();
						Receipt.HlslExpression = Hlsl ? Hlsl->HlslExpression : FString();
					}
					else
					{
						if (!SetAuthoringExpression(System, Work, Receipt.ModuleName, Receipt.NodeGuid, Assignment.Name,
							Assignment.HlslExpression, Context, Result.Error)) { return false; }
						Receipt.HlslExpression = Assignment.HlslExpression;
					}
					const auto* Node = Cast<UNiagaraNodeAssignment>(FindAuthoringNode(System, Work.EmitterName, Receipt.ModuleName, Result.Error));
					if (!Node || Node->NumTargets() != 1 || Node->GetAssignmentTarget(0).GetName() != Assignment.Name
						|| Node->GetAssignmentTarget(0).GetType() != Assignment.Type)
					{ if (Result.Error.IsEmpty()) { Result.Error = TEXT("实际独立 assignment 名称或类型不符。"); } return false; }
					Receipt.Target = Assignment.Name;
					Receipt.TypePath = AuthoringTypePath(Assignment.Type);
					if (Assignment.Name == FName(TEXT("Particles.Alive")) && !Work.FailureSourceReference.IsEmpty())
					{
						// 在原 Alive 后立即接原 DI，后继 assignment 不越过失败屏障。
						Result.RuntimeFailureBinding = ConnectRuntimeFailureWithContext(System, Work.EmitterName,
							Receipt.ModuleName, Work.FailureSourceReference, Work.ScriptName, &Context, &Work.OriginalAliveExpression);
						if (!Result.RuntimeFailureBinding.bApplied || !Result.RuntimeFailureBinding.Error.IsEmpty())
						{ Result.Error = Result.RuntimeFailureBinding.Error; return false; }
					}
				}
				Begin = End;
			}
		}
		else
		{
			const bool bFunctionAssignment = Work.Kind == TEXT("AssignmentDI");
			FString Body = Work.HlslBodyTemplate;
			FString Seed;
			if (bFunctionAssignment)
			{
				FNiagaraFunctionSignature Signature;
				if (!ReadAssignmentFunction(Work.InterfaceTemplate, Work, Signature, Body, Result.Error)) { return false; }
				Seed = Work.OutputTargets[0].Type == FNiagaraTypeDefinition::GetVec3Def()
					? TEXT("float3(0.0, 0.0, 0.0)") : TEXT("float4(0.0, 0.0, 0.0, 0.0)");
			}
			else { Seed = TEXT("false"); } // 原 ParticleRead 的 Bool seed。
			if (!AppendAuthoringModule(System, Work, nullptr, Work.OutputTargets, ViewModel, Result.ModuleName, Result.NodeGuid, bGraphChanged, Result.Error)) { return false; }
			if (!SetAuthoringExpression(System, Work, Result.ModuleName, Result.NodeGuid, Work.OutputTargets[0].Name,
				Seed, Context, Result.Error)) { return false; }
			TArray<FName> Names;
			for (const auto& Target : Work.OutputTargets) { Names.Add(Target.Name); }
			Result.AssignmentDIBinding = ConnectAssignmentWithContext(System, Work.EmitterName, Work.ScriptName,
				Result.ModuleName, Work.InterfaceTemplate, Names, Body, &Context, bFunctionAssignment ? &Work : nullptr);
			if (!Result.AssignmentDIBinding.bApplied || !Result.AssignmentDIBinding.Error.IsEmpty())
			{ Result.Error = Result.AssignmentDIBinding.Error; return false; }
		}
		Result.FailedSubIndex = INDEX_NONE;
		return true;
	}
}

bool UGGYGONiagaraCompileLibrary::AuthoringReadSupport()
{
	const UFunction* ReadLimit = StaticClass()->FindFunctionByName(TEXT("GetAuthoringCompileTaskLimit"));
	const UFunction* SetLimit = StaticClass()->FindFunctionByName(TEXT("TrySetAuthoringCompileTaskLimit"));
	if (!ReadLimit || !SetLimit || !ReadLimit->HasAllFunctionFlags(FUNC_Native) || !SetLimit->HasAllFunctionFlags(FUNC_Native)
		|| ReadLimit->NumParms != 1 || SetLimit->NumParms != 3
		|| !CastField<FIntProperty>(ReadLimit->GetReturnProperty()) || !CastField<FBoolProperty>(SetLimit->GetReturnProperty())
		|| !FindFProperty<FIntProperty>(SetLimit, TEXT("ExpectedLimit")) || !FindFProperty<FIntProperty>(SetLimit, TEXT("NewLimit")))
	{ return false; }
	const struct { const TCHAR* Name; int32 Parms; UScriptStruct* ReturnType; } Methods[] = {
		{TEXT("AuthoringAddEmitter"), 4, FGGYGONiagaraAuthoringData::StaticStruct()},
		{TEXT("AuthoringGetSystemSummary"), 2, FGGYGONiagaraAuthoringData::StaticStruct()},
		{TEXT("AuthoringGetRendererIdentities"), 3, FGGYGONiagaraAuthoringData::StaticStruct()},
		{TEXT("AuthoringGetEmitterData"), 3, FGGYGONiagaraAuthoringData::StaticStruct()},
		{TEXT("AuthoringSetEmitterData"), 4, FGGYGONiagaraAuthoringData::StaticStruct()},
		{TEXT("AuthoringAddRenderer"), 4, FGGYGONiagaraAuthoringData::StaticStruct()},
		{TEXT("AuthoringGetRendererData"), 4, FGGYGONiagaraAuthoringData::StaticStruct()},
		{TEXT("AuthoringSetRendererData"), 5, FGGYGONiagaraAuthoringData::StaticStruct()},
		{TEXT("CompileAuthoringBatch"), 2, FGGYGONiagaraCompileState::StaticStruct()},
		{TEXT("ReadAuthoringCompilationSettings"), 2, FGGYGONiagaraAuthoringCompilationSettings::StaticStruct()},
		{TEXT("ConfigureAuthoringCompilation"), 3, FGGYGONiagaraAuthoringCompilationSettings::StaticStruct()},
		{TEXT("ApplyAuthoringStackBatch"), 3, FGGYGONiagaraAuthoringBatchResult::StaticStruct()}};
	for (const auto& Method : Methods)
	{
		const UFunction* Function = StaticClass()->FindFunctionByName(FName(Method.Name));
		const FStructProperty* Return = Function ? CastField<FStructProperty>(Function->GetReturnProperty()) : nullptr;
		const auto* SystemInput = Function ? FindFProperty<FObjectPropertyBase>(Function, TEXT("System")) : nullptr;
		if (!Function || !Function->HasAllFunctionFlags(FUNC_Native) || Function->NumParms != Method.Parms
			|| !Return || Return->Struct != Method.ReturnType || !SystemInput
			|| SystemInput->PropertyClass != UNiagaraSystem::StaticClass()) { return false; }
	}
	const UFunction* Apply = StaticClass()->FindFunctionByName(TEXT("ApplyAuthoringStackBatch"));
	const auto* WorkArray = FindFProperty<FArrayProperty>(Apply, TEXT("WorkItems"));
	const auto* Work = WorkArray ? CastField<FStructProperty>(WorkArray->Inner) : nullptr;
	const auto* Inputs = FindFProperty<FArrayProperty>(FGGYGONiagaraAuthoringWorkItem::StaticStruct(), TEXT("Inputs"));
	const auto* Input = Inputs ? CastField<FStructProperty>(Inputs->Inner) : nullptr;
	const auto* Data = FindFProperty<FStructProperty>(FGGYGONiagaraAuthoringInput::StaticStruct(), TEXT("InputData"));
	const auto* Names = FindFProperty<FArrayProperty>(FGGYGONiagaraAuthoringInput::StaticStruct(), TEXT("NamePath"));
	const auto StructArray = [](UStruct* Owner, const TCHAR* Name, UScriptStruct* Expected)
	{
		const auto* Array = FindFProperty<FArrayProperty>(Owner, FName(Name));
		const auto* Element = Array ? CastField<FStructProperty>(Array->Inner) : nullptr;
		return Element && Element->Struct == Expected;
	};
	auto* WorkType = FGGYGONiagaraAuthoringWorkItem::StaticStruct();
	auto* BindingType = FGGYGONiagaraAssignmentDIBinding::StaticStruct();
	auto* FunctionInputType = FGGYGONiagaraAssignmentDIInput::StaticStruct();
	const auto* ValueType = FindFProperty<FStructProperty>(FunctionInputType, TEXT("Type"));
	return Work && Work->Struct == FGGYGONiagaraAuthoringWorkItem::StaticStruct()
		&& Input && Input->Struct == FGGYGONiagaraAuthoringInput::StaticStruct()
		&& Data && Data->Struct == FNiagaraExt_StackInputValue::StaticStruct()
		&& Names && CastField<FNameProperty>(Names->Inner)
		&& FindFProperty<FNameProperty>(WorkType, TEXT("FunctionName"))
		&& StructArray(WorkType, TEXT("FunctionInputs"), FunctionInputType)
		&& StructArray(WorkType, TEXT("OutputTargets"), FGGYGONiagaraAuthoringTarget::StaticStruct())
		&& FindFProperty<FNameProperty>(FunctionInputType, TEXT("Name"))
		&& ValueType && ValueType->Struct == FNiagaraTypeDefinition::StaticStruct()
		&& FindFProperty<FStrProperty>(FunctionInputType, TEXT("HlslExpression"))
		&& FindFProperty<FNameProperty>(BindingType, TEXT("FunctionName"))
		&& FindFProperty<FStrProperty>(BindingType, TEXT("DataInterfacePath"))
		&& FindFProperty<FBoolProperty>(BindingType, TEXT("bFunctionBound"))
		&& StructArray(BindingType, TEXT("FunctionInputs"), FunctionInputType)
		&& StructArray(BindingType, TEXT("FunctionOutputs"), FGGYGONiagaraAuthoringTarget::StaticStruct())
		&& ReadAssignmentDataInterfaceSupport() && ReadMathAssignmentSupport();
}

namespace
{
FGGYGONiagaraAuthoringBatchResult ApplyAuthoringStackBatchInternal(UNiagaraSystem* System,
	const TArray<FGGYGONiagaraAuthoringWorkItem>& WorkItems, bool bUseNativeSystemInputs)
{
	FGGYGONiagaraAuthoringBatchResult Result;
	Result.SystemPath = GetPathNameSafe(System);
	FGGYGONiagaraAuthoringData Admission;
	if (!BeginAuthoringData(System, Admission) || WorkItems.IsEmpty())
	{ Result.Error = Admission.Error.IsEmpty() ? TEXT("有限 Stack 制作计划为空。") : Admission.Error; return Result; }
	for (int32 Index = 0; Index < WorkItems.Num(); ++Index)
	{
		if (!ValidateAuthoringWork(System, WorkItems[Index], Result.Error)) { Result.FailedIndex = Index; return Result; }
	}
	const TStrongObjectPtr<UNiagaraSystem> OriginalSystem(System);
	auto& NiagaraEditor = FModuleManager::LoadModuleChecked<FNiagaraEditorModule>(TEXT("NiagaraEditor"));
	if (NiagaraEditor.GetExistingViewModelForSystem(System).IsValid())
	{ Result.Error = TEXT("原 NS 已有 Editor ViewModel，不能借用其它作者的编辑状态。"); return Result; }
	TWeakPtr<FNiagaraSystemViewModel> RetiredViewModel;
	{
		const FScopedTransaction Transaction(NSLOCTEXT("GGYGONiagara", "AuthoringStackBatch", "应用完整有序 Niagara 制作计划"));
		const bool bOriginalCompileForEdit = System->GetCompileForEdit();
		ON_SCOPE_EXIT
		{
			System->SetCompileForEdit(bOriginalCompileForEdit);
			UE_LOG(LogTemp, Display, TEXT("Niagara 有限 Stack 编辑归还：System=%s OriginalCompileForEdit=%d CompileForEdit=%d RI=%d"),
				*Result.SystemPath, static_cast<int32>(bOriginalCompileForEdit),
				static_cast<int32>(System->GetCompileForEdit()), static_cast<int32>(System->ShouldUseRapidIterationParameters()));
		};
		// 只借原生编辑模式；RI=false 保留原合法写入路径，不改资产的 bake 配置。
		System->SetCompileForEdit(true);
		const bool bAuthoringUsesRapidIteration = System->ShouldUseRapidIterationParameters();
		UE_LOG(LogTemp, Display, TEXT("Niagara 有限 Stack 编辑：System=%s OriginalCompileForEdit=%d CompileForEdit=%d RI=%d；RI 仅影响候选 local 值，原 HLSL/DI 与输入校验保持"),
			*Result.SystemPath, static_cast<int32>(bOriginalCompileForEdit),
			static_cast<int32>(System->GetCompileForEdit()), static_cast<int32>(bAuthoringUsesRapidIteration));
		TUniquePtr<FNiagaraExternalEditContext> Context = MakeUnique<FNiagaraExternalEditContext>(System);
		// 通过公开模块入口取得本 Context 刚注册的唯一 VM，不访问 Context 私有成员或另建 VM。
		TSharedPtr<FNiagaraSystemViewModel> ViewModel = NiagaraEditor.GetExistingViewModelForSystem(System);
		RetiredViewModel = ViewModel;
		Result.bApplied = ReadAuthoringErrors(*Context, Result.Error) && ViewModel.IsValid();
		if (!ViewModel.IsValid() && Result.Error.IsEmpty()) { Result.Error = TEXT("原生 Context 未注册本批作者 VM。"); }
		TArray<FAuthoringLinkedOutput> LinkedOutputs;
		for (int32 Index = 0; Result.bApplied && Index < WorkItems.Num(); ++Index)
		{
			Result.FailedIndex = Index;
			const auto& Work = WorkItems[Index];
			if (Index == 0 || (Index + 1) % 100 == 0 || Index == WorkItems.Num() - 1)
			{
				UE_LOG(LogTemp, Display, TEXT("Niagara 有限 Stack 工作项进入：Index=%d Num=%d Kind=%s Emitter=%s Script=%s"),
					Index, WorkItems.Num(), *Work.Kind, *Work.EmitterName, *Work.ScriptName);
			}
			auto& Item = Result.Items.AddDefaulted_GetRef();
			Item.Index = Index; Item.Kind = Work.Kind; Item.EmitterName = Work.EmitterName; Item.ScriptName = Work.ScriptName;
			Result.bApplied = ApplyAuthoringWork(System, Work, *Context, ViewModel.ToSharedRef(), Item, Result.bGraphChanged,
				bUseNativeSystemInputs, LinkedOutputs);
			if (Result.bApplied && bUseNativeSystemInputs && Work.Kind == TEXT("AssignmentDI")
				&& (Work.ScriptName == TEXT("EmitterSpawnScript") || Work.ScriptName == TEXT("EmitterUpdateScript")))
			{
				// 仅在原 ConnectAssignmentWithContext 完整实际读回后发布同次调用的输出事实。
				for (const auto& Output : Work.OutputTargets)
				{
					LinkedOutputs.Add({Work.EmitterName, Work.ScriptName, FNiagaraVariableBase(Output.Type, Output.Name)});
				}
			}
			if (!Result.bApplied)
			{
				for (const FText& NativeError : Context->Errors)
				{
					const FString Message = NativeError.ToString();
					if (!Item.Error.Contains(Message)) { Item.Error += LINE_TERMINATOR + Message; }
				}
				Result.Error = FString::Printf(TEXT("制作项 %d %s/%s/%s：%s"),
					Index, *Work.EmitterName, *Work.ScriptName, *Work.Kind, *Item.Error);
			}
		}
		if (Result.bApplied) { Result.FailedIndex = INDEX_NONE; }
		Context.Reset();
		ViewModel.Reset();
	}
	// 弱引用核本批唯一 VM 的真实释放；原 NS 的编译任务仍由原生收束入口处理。
	Result.bViewModelReleased = !RetiredViewModel.IsValid();
	Result.bTransactionClosed = GEditor && !GEditor->IsTransactionActive();
	Result.bReadyForGarbageCollection = Result.bViewModelReleased && Result.bTransactionClosed;
	if (!Result.bReadyForGarbageCollection)
	{ Result.bApplied = false; Result.Error += TEXT(" 本批 VM/事务未归还，不得进入 GC。"); }
	UE_LOG(LogTemp, Display, TEXT("Niagara 有限 Stack 结果：System=%s bApplied=%d Items=%d FailedIndex=%d Error=%s bViewModelReleased=%d bTransactionClosed=%d bReadyForGarbageCollection=%d"),
		*Result.SystemPath, static_cast<int32>(Result.bApplied), Result.Items.Num(), Result.FailedIndex, *Result.Error,
		static_cast<int32>(Result.bViewModelReleased), static_cast<int32>(Result.bTransactionClosed),
		static_cast<int32>(Result.bReadyForGarbageCollection));
	return Result;
}
}

FGGYGONiagaraAuthoringBatchResult UGGYGONiagaraCompileLibrary::ApplyAuthoringStackBatch(UNiagaraSystem* System,
	const TArray<FGGYGONiagaraAuthoringWorkItem>& WorkItems)
{
	return ApplyAuthoringStackBatchInternal(System, WorkItems, true);
}

FGGYGONiagaraStackBatchResult UGGYGONiagaraCompileLibrary::ApplyStackBatch(UNiagaraSystem* System,
	const FString& EmitterName, const FString& ScriptName, const TArray<FGGYGONiagaraStackAssignment>& Assignments)
{
	FGGYGONiagaraAuthoringWorkItem Work;
	Work.Kind = TEXT("Assignments"); Work.EmitterName = EmitterName; Work.ScriptName = ScriptName; Work.Assignments = Assignments;
	// 旧入口没有逐项 typed Inputs，继续保持其实际 HLSL 写后读回契约。
	const auto Batch = ApplyAuthoringStackBatchInternal(System, {Work}, false);
	FGGYGONiagaraStackBatchResult Result;
	Result.SystemPath = Batch.SystemPath; Result.EmitterName = EmitterName; Result.ScriptName = ScriptName;
	Result.bApplied = Batch.bApplied; Result.bGraphChanged = Batch.bGraphChanged; Result.Error = Batch.Error;
	Result.bViewModelReleased = Batch.bViewModelReleased; Result.bTransactionClosed = Batch.bTransactionClosed;
	Result.bReadyForGarbageCollection = Batch.bReadyForGarbageCollection;
	if (!Batch.Items.IsEmpty()) { Result.Modules = Batch.Items[0].Modules; Result.FailedIndex = Batch.Items[0].FailedSubIndex; }
	return Result;
}
