/** @file GGYGOPlayerInputBridgeLibrary.h
 *  @brief 向 Editor 脚本提供权威输入装配、软件数字键和暂停 owner 查询。
 */
#pragma once

#include "CoreMinimal.h"
#include "InputCoreTypes.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "Misc/CoreMiscDefines.h"
#include "GGYGOPlayerInputBridgeLibrary.generated.h"

class APlayerController;
class APawn;
class UInputComponent;
class ULocalPlayer;
class UPlayerInput;
class UWorld;
class APlayerState;
class AWorldSettings;

/** 只表示原输入装配的当前状态，不表示技能或设备验收。 */
UENUM(BlueprintType)
enum class EGGYGOPlayerInputAssemblyStatus : uint8
{
	Ready,
	Waiting,
	Invalid
};

/** Editor 专用查询及软件键事件桥；不持有输入资源或驱动输入消费。 */
UCLASS()
class GGYGOEDITOR_API UGGYGOPlayerInputBridgeLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * 从调用者已核定的 LocalPlayer 读取原 World 中的实际输入对象。
	 * Waiting/Invalid 清空对象输出并给出诊断；Ready 只证明装配身份。
	 * PrimaryInputDevice 允许原生无效值，不据此猜默认设备或升级物理证明。
	 * @param OriginalWorld 调用者已核定的原 PIE World。
	 * @param OriginalLocalPlayer 调用者已核定来源的 LocalPlayer，不由本接口搜索或选槽位。
	 * @param OutPlayerController 原 LocalPlayer 实际关联的 GGYGO PC。
	 * @param OutPawn 原 PC 实际附身的 Pawn。
	 * @param OutPlayerInput 原 PC 持有的 GGYGOPlayerInput，属于 EnhancedPlayerInput。
	 * @param OutPawnInputComponent 原受控 Pawn 的 GGYGOInputComponent，不取 PC 自有组件。
	 * @param OutPlatformUser 原 LocalPlayer 的平台用户原值。
	 * @param OutPrimaryInputDevice 原生 primary 设备映射，允许无效值。
	 * @param OutDiagnostic Waiting/Invalid 的可定位原因；Ready 时为空。
	 * @return Ready 为装配身份完整，Waiting 为真实装配未就绪，Invalid 为来源或配置错误。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Input")
	static EGGYGOPlayerInputAssemblyStatus ReadLocalPlayerInputAssembly(
		UWorld* OriginalWorld, ULocalPlayer* OriginalLocalPlayer,
		APlayerController*& OutPlayerController, APawn*& OutPawn,
		UPlayerInput*& OutPlayerInput, UInputComponent*& OutPawnInputComponent,
		FPlatformUserId& OutPlatformUser, FInputDeviceId& OutPrimaryInputDevice,
		FString& OutDiagnostic);

	/**
	 * 向精确原装配提交数字键 Press/Release；不跟随后继 PC/Pawn/输入对象。
	 * true 仅表示已调用原 PC.InputKey；OutHandled 是该调用的原生返回值。
	 * 消费方须分帧调用并核实际 Action/ASC/生命周期，不以本返回值认定激活。
	 * 消费方负责原装配的 Release／停止清理，不向后继装配发送补偿事件。
	 * @param OriginalWorld 首次 Ready 时固定的原 PIE World。
	 * @param OriginalLocalPlayer 首次 Ready 时固定的原 LocalPlayer。
	 * @param OriginalPlayerController 首次 Ready 返回的原 PC。
	 * @param OriginalPawn 首次 Ready 返回的原受控 Pawn。
	 * @param OriginalPlayerInput 首次 Ready 返回的原 PlayerInput。
	 * @param OriginalPawnInputComponent 首次 Ready 返回的原 Pawn.InputComponent。
	 * @param InputDevice 明确提供且仍属于原平台用户的设备 ID，不补造默认设备。
	 * @param Key 有效数字键，不接受模拟轴值。
	 * @param bPressed true 提交 IE_Pressed，false 提交 IE_Released。
	 * @param OutHandled 原 PC.InputKey 的返回值；拒绝提交时为 false。
	 * @param OutDiagnostic 拒绝提交的原因；成功调用时为空。
	 * @return true 仅表示已调用原 PC.InputKey；false 表示未提交，不代表技能结果。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Input")
	static bool SubmitDigitalKeyEvent(
		UWorld* OriginalWorld, ULocalPlayer* OriginalLocalPlayer,
		APlayerController* OriginalPlayerController, APawn* OriginalPawn,
		UPlayerInput* OriginalPlayerInput, UInputComponent* OriginalPawnInputComponent,
		FInputDeviceId InputDevice, const FKey& Key, bool bPressed,
		bool& OutHandled, FString& OutDiagnostic);

	/**
	 * 从原 WorldSettings 读取实际暂停 owner；允许原生空 owner，不替代暂停行为。
	 * @param OriginalWorld 调用者已核定的原 PIE World。
	 * @param OutWorldSettings 原 World 的实际 WorldSettings。
	 * @param OutPaused 原 World.IsPaused 的当前值，不替代 owner 读回。
	 * @param OutPauserPlayerState 原 WorldSettings.GetPauserPlayerState 的原值，允许为空。
	 * @param OutDiagnostic 查询失败的来源或就绪原因；成功时为空。
	 * @return true 表示完成只读快照；false 表示未能读取，输出不可作为暂停证据。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Input")
	static bool ReadWorldPauseState(UWorld* OriginalWorld, AWorldSettings*& OutWorldSettings,
		bool& OutPaused, APlayerState*& OutPauserPlayerState, FString& OutDiagnostic);
};
