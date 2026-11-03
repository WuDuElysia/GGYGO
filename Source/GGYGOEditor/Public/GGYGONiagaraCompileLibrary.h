/** @file GGYGONiagaraCompileLibrary.h @brief 编辑器 Niagara 有限批量制作、编译收束与即时结果读回。 */
#pragma once

#include "CoreMinimal.h"
#include "NiagaraTypes.h"
#include "NiagaraExternalSystemEditorUtilities.h"
#include "ToolsetRegistry/ToolsetDefinition.h"
#include "GGYGONiagaraCompileLibrary.generated.h"

class UNiagaraSystem;
class UNiagaraEmitter;
class UNiagaraScript;
class UNiagaraRendererProperties;
class UNiagaraDataInterface;
class UMaterialInterface;

/** 原资产编译表示的即时配置读回；不创建作者 VM、不查询 Ready 或等待编译。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraAuthoringCompilationSettings
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bCompileForEdit = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bUsesRapidIterationParameters = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 一次原生查询的快照；不持有资源，不代表首粒子或动作播放已验证。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraCompileState
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bForceCompileRequested = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bCompilationPending = false;
	/** 原生尚有待发起的编译请求；不等同于编译任务已经运行。 */
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bNeedsCompileRequest = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bActiveCompilations = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bSystemValid = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bNativeReady = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	bool bVMAttributesEqual = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	int32 EmitterCount = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	int32 CompiledEmitterCount = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	int32 SpawnAttributeCount = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	int32 UpdateAttributeCount = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	TArray<FName> EmitterNames;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	TArray<bool> EmitterEnabled;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara")
	FString Error;
};

/** 同 GT 的完整编译诊断快照；bSucceeded 仅表示读取成功，编译成败由 CompileState 判断。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraCompileDiagnostics
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FNiagaraExt_SystemCompileState CompileState;
};

/** 原生粒子 DataSet 的实际字段；名称保留编译后的原文，不补回 Particles.。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraDataSetAttribute
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FName Name;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString TypePath;
};

/** 一次只读的源 emitter 编译快照；仅 bReady 时 Attributes 是有效完整清单，变更后须重新查询。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraEmitterDataSetState
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bReady = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGGYGONiagaraCompileState SystemState;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FName EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 HandleIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGuid EmitterHandleId;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString UniqueEmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FName DataSetName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bRequiresPersistentIDs = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraDataSetAttribute> Attributes;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 实际加载的标准 Ribbon CDO 与 typed 作者入口；默认值不替代实例的显式配置。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraRibbonUniqueIDSupport
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bSupported = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererClass;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bDefaultLinkOrderUseUniqueId = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString DefaultRibbonIdTypePath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 准确 Ribbon 槽的即时快照；bApplied 证明配置读回，bReady 才发布编译缓存 accessor。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraRibbonUniqueIDState
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bApplied = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bReady = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGuid EmitterHandleId;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 RendererIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererClass;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bLinkOrderUseUniqueId = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RibbonLinkOrderAttribute;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RibbonLinkOrderTypePath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RibbonIdAttribute;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RibbonIdDataSetAttribute;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RibbonIdTypePath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bInt32LinkOrderAccessorValid = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bFloatLinkOrderAccessorValid = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bInt32RibbonIdAccessorValid = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bFullRibbonIdAccessorValid = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString UniqueIdTypePath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** Native Sprite 绑定的即时读回；bLayoutValid 仅在实例 bReady 的编译快照中有效。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraSpriteBindingState
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString PropertyName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Attribute;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString DataSetAttribute;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString TypePath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bBindingExistsOnSource = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bIsCachedParticleValue = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bLayoutValid = false;
};

/** 实际 Sprite CDO 的八组 current/派生 previous 身份；不发布编译布局或写入缓存。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraSpriteMotionSupport
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bSupported = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererClass;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraSpriteBindingState> CurrentBindings;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraSpriteBindingState> PreviousBindings;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 原 CPU Sprite 的绑定及两套 VF 布局快照；变更后重新读取，不代表 RT/GPU 或画面验收。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraSpriteMotionState
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bReady = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGuid EmitterHandleId;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 RendererIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererClass;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SourceMode;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bNeedsPreciseMotionVectors = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraSpriteBindingState> CurrentBindings;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraSpriteBindingState> PreviousBindings;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 只读实际加载的 CPU DI ABI；不代表模拟、编译或画面已经验证。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraRuntimeFailureSupport
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bSupported = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString DataInterfaceClass;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString FunctionName;
	/** 当前桥实际读取的通用粒子失败属性；作者据此拒绝旧加载软件。 */
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString FailureAttribute;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 PerInstanceBytes = 0;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 原 Alive 赋值图的实际接线读回；调用者仍负责本批编译与精确保存。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraRuntimeFailureBinding
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bApplied = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bGraphChanged = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString ModuleName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString ScriptName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SourceReference;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString OriginalAliveExpression;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString DataInterfaceClass;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString InterfaceParameter;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString FailureAttribute;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** Native Mesh UserMaterial的实际参数/renderer读回；只用于本批拥有的新NS。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraUserMaterialBinding
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bApplied = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 RendererIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString ParameterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString MaterialPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 制作目标或函数签名中的具名类型。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraAuthoringTarget
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Niagara") FName Name;
	UPROPERTY(EditAnywhere, Category = "Niagara") FNiagaraTypeDefinition Type;
};

/** DI 纯函数的一个显式值输入；表达式只允许值，不承载 Function body。 */
USTRUCT(BlueprintType, meta = (ScriptName = "GGYGONiagaraAssignmentDIInput"))
struct FGGYGONiagaraAssignmentDIInput
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Niagara") FName Name;
	UPROPERTY(EditAnywhere, Category = "Niagara") FNiagaraTypeDefinition Type;
	UPROPERTY(EditAnywhere, Category = "Niagara") FString HlslExpression;
};

/** 本次 authoring 后逐目标的真实 Custom output；仅在 bApplied 时可用于后继消费。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraAssignmentOutputBinding
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FName Target;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FName OutputPin;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString TypePath;
};

/** 原 assignment 的即时接线读回；图与 DI 由原 NS 拥有，不持有运行时资源。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraAssignmentDIBinding
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bApplied = false;
	/** 失败为 true 时保留实际脏图；调用方须停止该 NS 的制作与保存，由其资产窗口处理。 */
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bGraphChanged = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString ScriptName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString ModuleName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGuid AssignmentGuid;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGuid CustomGuid;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString DataInterfaceClass;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString DataInterfacePath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FName FunctionName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraAssignmentDIInput> FunctionInputs;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraAuthoringTarget> FunctionOutputs;
	/** 本次实际无实例数据 DI 可绑定该 CPU 签名；不代表运行时或完整 NS 验收。 */
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bFunctionBound = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FName InterfaceParameter;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bInterfaceEqualsTemplate = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString CustomUsage;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraAssignmentOutputBinding> Outputs;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString HlslBody;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 原计划中的一次独立 ParamMap 写入；数组顺序就是模块执行顺序，不合并相邻目标。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraStackAssignment
{
	GENERATED_BODY()

	UPROPERTY(EditAnywhere, Category = "Niagara") FName Name;
	UPROPERTY(EditAnywhere, Category = "Niagara") FNiagaraTypeDefinition Type;
	UPROPERTY(EditAnywhere, Category = "Niagara") FString HlslExpression;
};

/** 批量插入后，从实际节点和原生输入读回的单项结果。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraStackAssignmentResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 Index = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString ModuleName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGuid NodeGuid;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FName Target;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString TypePath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString HlslExpression;
};

/** 只表示本段作者调用及退栈事实；不表示编译、保存或内存峰值已验证。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraStackBatchResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bApplied = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bGraphChanged = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString ScriptName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 FailedIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraStackAssignmentResult> Modules;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bViewModelReleased = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bTransactionClosed = false;
	/** 调用方还须等本工具返回、确认无 pending 并通过原资源门；本接口不执行 GC。 */
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bReadyForGarbageCollection = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 原 renderer 数组的即时身份，不冒充完整脚本栈拓扑。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraAuthoringRenderer
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 RendererIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererClass;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererPath;
};

USTRUCT(BlueprintType)
struct FGGYGONiagaraAuthoringEmitter
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString UniqueEmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGuid EmitterHandleId;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bEnabled = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SimTarget;
};

/** 无 VM 数据作者调用的读回；不持有资产，不代表编译或保存完成。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraAuthoringData
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString UniqueEmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGuid EmitterHandleId;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 RendererIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererClass;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString RendererPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString PropertyValues;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraAuthoringEmitter> Emitters;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraAuthoringRenderer> Renderers;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bTransactionClosed = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 原 Niagara StackInputValue 直接复用 Toolset typed wire、枚举及 HLSL 解析。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraAuthoringInput
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Niagara") TArray<FName> NamePath;
	UPROPERTY(EditAnywhere, Category = "Niagara") FNiagaraExt_StackInputValue InputData;
};

/** 一次有限有序制作单元；只接受 Module / Assignments / ParticleRead / AssignmentDI。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraAuthoringWorkItem
{
	GENERATED_BODY()
	UPROPERTY(EditAnywhere, Category = "Niagara") FString Kind;
	UPROPERTY(EditAnywhere, Category = "Niagara") FString EmitterName;
	UPROPERTY(EditAnywhere, Category = "Niagara") FString ScriptName;
	UPROPERTY(EditAnywhere, Category = "Niagara") TObjectPtr<UNiagaraScript> ModuleAsset = nullptr;
	UPROPERTY(EditAnywhere, Category = "Niagara") TArray<FGGYGONiagaraAuthoringInput> Inputs;
	UPROPERTY(EditAnywhere, Category = "Niagara") TArray<FGGYGONiagaraStackAssignment> Assignments;
	UPROPERTY(EditAnywhere, Category = "Niagara") FString FailureSourceReference;
	UPROPERTY(EditAnywhere, Category = "Niagara") FString OriginalAliveExpression;
	UPROPERTY(EditAnywhere, Category = "Niagara") TObjectPtr<UNiagaraDataInterface> InterfaceTemplate = nullptr;
	UPROPERTY(EditAnywhere, Category = "Niagara") TArray<FGGYGONiagaraAuthoringTarget> OutputTargets;
	/** AssignmentDI 使用实际 DI 纯函数签名；不接受调用方提供的 body。 */
	UPROPERTY(EditAnywhere, Category = "Niagara") FName FunctionName;
	UPROPERTY(EditAnywhere, Category = "Niagara") TArray<FGGYGONiagaraAssignmentDIInput> FunctionInputs;
	UPROPERTY(EditAnywhere, Category = "Niagara") FString HlslBodyTemplate;
};

USTRUCT(BlueprintType)
struct FGGYGONiagaraAuthoringWorkResult
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 Index = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Kind;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString EmitterName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString ScriptName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString ModuleName;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGuid NodeGuid;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 FailedSubIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraAuthoringInput> Inputs;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraStackAssignmentResult> Modules;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGGYGONiagaraRuntimeFailureBinding RuntimeFailureBinding;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FGGYGONiagaraAssignmentDIBinding AssignmentDIBinding;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 本批 VM/事务已归还才允许调用方退栈后 GC；不宣称编译任务或内存已释放。 */
USTRUCT(BlueprintType)
struct FGGYGONiagaraAuthoringBatchResult
{
	GENERATED_BODY()
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bApplied = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bGraphChanged = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString SystemPath;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") int32 FailedIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") TArray<FGGYGONiagaraAuthoringWorkResult> Items;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bViewModelReleased = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bTransactionClosed = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") bool bReadyForGarbageCollection = false;
	UPROPERTY(BlueprintReadOnly, Category = "Niagara") FString Error;
};

/** 标准 Editor Python 与既有 Toolset Registry 共用的薄入口；不保存或重建资产。 */
UCLASS()
class GGYGOEDITOR_API UGGYGONiagaraCompileLibrary : public UToolsetDefinition
{
	GENERATED_BODY()

public:
	/** 新包创建前核当前 DLL 的有限作者 ABI；不创建 VM、编译或资产。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static bool AuthoringReadSupport();

	/** 使用原生公开创建入口和准确 SetName；不创建全 NS 的 ViewModel。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringData AuthoringAddEmitter(UNiagaraSystem* System, UNiagaraEmitter* TemplateEmitter,
		const FString& EmitterName);

	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringData AuthoringGetSystemSummary(UNiagaraSystem* System);

	/** 只读 renderer 身份列表；不初始化四个脚本栈。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringData AuthoringGetRendererIdentities(UNiagaraSystem* System, const FString& EmitterName);

	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringData AuthoringGetEmitterData(UNiagaraSystem* System, const FString& EmitterName);

	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringData AuthoringSetEmitterData(UNiagaraSystem* System, const FString& EmitterName,
		const FString& PropertyValues);

	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringData AuthoringAddRenderer(UNiagaraSystem* System, const FString& EmitterName,
		TSubclassOf<UNiagaraRendererProperties> RendererClass);

	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringData AuthoringGetRendererData(UNiagaraSystem* System, const FString& EmitterName,
		int32 RendererIndex);

	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringData AuthoringSetRendererData(UNiagaraSystem* System, const FString& EmitterName,
		int32 RendererIndex, const FString& PropertyValues);

	/** 同一有限计划共用一份 data-only Context；原生初始化行为保留，不逐 emitter 强制编译。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringBatchResult ApplyAuthoringStackBatch(UNiagaraSystem* System,
		const TArray<FGGYGONiagaraAuthoringWorkItem>& WorkItems);

	/** 查询真实 CDO 的 current/previous 属性身份，不将 Transient previous 当作可配置输入。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraSpriteMotionSupport ReadSpriteMotionSupport();

	/** 只读准确 Sprite 实例的已编译绑定/VF 槽；复用原 DataSet 就绪校验，不刷新派生缓存。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraSpriteMotionState ReadSpriteMotionState(UNiagaraSystem* System,
		const FString& EmitterName, int32 RendererIndex);

	/** 查询实际 Ribbon CDO 的隐藏排序位与 ID 类型，并确认本 DLL 的 typed 接口。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraRibbonUniqueIDSupport ReadRibbonUniqueIDSupport();

	/** 为准确 CPU Ribbon 启用出生 UniqueID 排序、解绑 Float 排序；空属性名显式解绑，否则绑定完整 NiagaraID。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraRibbonUniqueIDState ConfigureRibbonUniqueID(UNiagaraSystem* System,
		const FString& EmitterName, int32 RendererIndex, const FString& RibbonIdAttribute);

	/** 只读原 NS 已就绪 DataSet 及 renderer 的实际缓存；不请求编译、刷新缓存或保存。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraRibbonUniqueIDState ReadRibbonUniqueIDState(UNiagaraSystem* System,
		const FString& EmitterName, int32 RendererIndex);

	/** 在准确脚本末尾批插独立 assignment，再按原顺序应用 HLSL；DI 屏障由调用方拆段。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraStackBatchResult ApplyStackBatch(UNiagaraSystem* System, const FString& EmitterName,
		const FString& ScriptName, const TArray<FGGYGONiagaraStackAssignment>& Assignments);

	/** 资产变更前查询实际加载的UserMaterial桥，旧DLL缺入口时不得先建部分NS。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static bool ReadMeshUserMaterialSupport();

	/** 给本批新NS声明准确Material用户参数并接同一Mesh renderer；拒绝覆盖别的绑定，不保存。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraUserMaterialBinding BindMeshUserMaterial(UNiagaraSystem* System,
		const FString& EmitterName, int32 RendererIndex, const FString& ParameterName, UMaterialInterface* Material);

	/** 在资产变更前检查实际加载的 CPU DI 函数签名及必需来源字段。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraRuntimeFailureSupport ReadRuntimeFailureSupport();

	/** 只接准确 Spawn/Update Alive assignment 的 typed DI；保留原 Alive 表达式，不编译或保存。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraRuntimeFailureBinding ConnectRuntimeFailureToAlive(
		UNiagaraSystem* System, const FString& EmitterName, const FString& ModuleName, const FString& SourceReference,
		const FString& ScriptName = TEXT("ParticleUpdateScript"));

	/** 在新 NS 制作前核对实际加载的通用 assignment DI 作者桥。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static bool ReadAssignmentDataInterfaceSupport();

	/**
	 * 为调用方拥有的新 CPU assignment 接入 DI 和显式多输出；保留原节点及上游 ParamMap。
	 * @param InterfaceTemplate 调用方配置的非 CDO DI；原生 CopyTo/Equals 复制核对，模板不转移所有权。
	 * @param OutputTargets 原 assignment 预先声明的全部目标，首项已有唯一 HlslExpression seed，其余无连线。
	 * @param HlslBodyTemplate Function 语句体；{{DI}} 和 {{OUT:完整目标名}} 替换为 native 实际 pin 名。
	 * @return bApplied 仅表示图读回；失败且 bGraphChanged 时保留脏图，由资产窗口拥有者处理，禁止继续编译保存。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAssignmentDIBinding ConnectAssignmentDataInterface(UNiagaraSystem* System,
		const FString& EmitterName, const FString& ScriptName, const FString& ModuleName,
		UNiagaraDataInterface* InterfaceTemplate, const TArray<FName>& OutputTargets, const FString& HlslBodyTemplate);

	/** @param System 原资产；只查询公开原生状态及完整有序 VM 属性，不触发强制编译。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraCompileState ReadSystemState(UNiagaraSystem* System);

	/**
	 * 以默认 Context 直接读取原生完整编译诊断，避免创建作者 VM 时发起编译。
	 * @param System GameThread 上的准确有效原资产。
	 * @return 对象路径、完整 CompileState 及 Context 错误；读取成功仍须核全部编译状态与脚本错误。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable, ScriptName = "read_system_compile_diagnostics"), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraCompileDiagnostics ReadSystemCompileDiagnostics(UNiagaraSystem* System);

	/** 只读公开编译模式；不切换 Edit 状态，不请求编译或创建作者 VM。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable, ScriptName = "read_authoring_compilation_settings"), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringCompilationSettings ReadAuthoringCompilationSettings(UNiagaraSystem* System);

	/**
	 * 在本轮可写的新 NS 开始制作前，显式配置 Edit/Cook 两种模式的 RI 保留策略；不会在保存前恢复。
	 * @param System 非 PIE Editor GameThread 上、无作者 VM/活动事务的原资产；不用于修改只读既有成果。
	 * @param bUseRapidIterationParameters true 使用原生 RI 参数 store，false 将数值烘焙到脚本；不改变公式或参数值。
	 * @return 实际公开模式的即时读回。配置不等待编译，不代表内存、编译、保存或 Cook 验收。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable, ScriptName = "configure_authoring_compilation"), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraAuthoringCompilationSettings ConfigureAuthoringCompilation(UNiagaraSystem* System, bool bUseRapidIterationParameters);

	/**
	 * 查询准确 enabled CPU 源 handle 的完整实际 DataSet name/type；不请求编译、保存或运行。
	 * 源/编译未同步、未 Ready、身份或清单不一致时拒绝发布 Attributes，不以旧编译产物或数量代替。
	 * @return bReady 仅证明本次编译快照有效；调用者仍须核所需字段、native 允许类型及每次 DI 查询的 Valid。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraEmitterDataSetState ReadEmitterDataSetAttributes(UNiagaraSystem* System, const FString& EmitterName);

	/**
	 * 由原生等待入口发起已有待编译请求并提取 GPU/VM 结果；不显式请求强制编译或保存。
	 * @param System 非 PIE、可渲染 Editor GameThread 上的原资产。
	 * @return 收束后的即时状态；原生内部重试、失败和未 Ready 均由调用方如实检查。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraCompileState CompletePendingCompilation(UNiagaraSystem* System);

	/** 原 Niagara manager 当前活动 System 任务限额；只读，入口无效时返回 INDEX_NONE。 */
	UFUNCTION(BlueprintCallable, meta = (AICallable, ScriptName = "get_authoring_compile_task_limit"), Category = "GGYGO|Editor|FX")
	static int32 GetAuthoringCompileTaskLimit();

	/**
	 * 独占生产 Editor 的 AsyncTasks 编译后端中，将已配置限额1置0以延后不完整图启动，或在段末还原1。
	 * @param ExpectedLimit 本次交换前必须实际持有的0/1；不匹配时不写入。
	 * @param NewLimit 只接受1→0或0→1，保留原CVar优先级及tag；dirty通知和原入队均继续。
	 * @return 是否实际交换。调用方以局部原值持有恢复义务，finally恢复且窗口内不yield/请求等待。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable, ScriptName = "try_set_authoring_compile_task_limit"), Category = "GGYGO|Editor|FX")
	static bool TrySetAuthoringCompileTaskLimit(int32 ExpectedLimit, int32 NewLimit);

	/**
	 * 有限制作批归还 VM/事务后，对当前原 NS 请求非强制编译，收束 GPU/VM 及当前 Editor Shader 队列。
	 * Shader 等待覆盖当前 Editor，制作方须持有独占生产窗口；队列清空不表示进程驻留内存已释放。
	 * @param System 当前累计制作的原资产；不得在仍有作者 VM/事务时调用。
	 * @return 当前批的真实编译状态；不保存。完整制作的最终验收仍须核全部脚本、renderer 与真实布局。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable, ScriptName = "compile_authoring_batch"), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraCompileState CompileAuthoringBatch(UNiagaraSystem* System);

	/**
	 * 请求原资产完整编译并由原生编译器等待 GPU/VM 结果；不创建等待器或保存资产。
	 * @param System 必须具有编辑器源图，且 Editor 不在 PIE。
	 * @return 原生请求是否发出和收束后的即时结果；调用方负责准入及精确保存。
	 */
	UFUNCTION(BlueprintCallable, meta = (AICallable), Category = "GGYGO|Editor|FX")
	static FGGYGONiagaraCompileState ForceCompile(UNiagaraSystem* System);
};
