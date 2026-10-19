/** @file GGYGOLinearMontageAuthorLibrary.h @brief 完整源线性 Montage 的编辑器制作、只读验证及原生时间轴事实读取入口。 */
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GGYGOLinearMontageAuthorLibrary.generated.h"

class UAnimMontage;
class UAnimSequence;

/** 本次调用的实际原生读回；失败不签发可用长度或区段坐标。 */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOLinearMontageAuthorResult
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	bool bSucceeded = false;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString Error;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float DurationSeconds = 0.0f;

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	TArray<float> SectionStarts;
};

/** 一个 CompositeSection 的当前原生读回；Time 为 FCompositeSection::GetTime（Montage 绝对秒）。 */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOMontageTimelineSectionFact
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FName SectionName;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FName NextSectionName;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float Time = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 SlotIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 SegmentIndex = INDEX_NONE;
};

/** 一个 Slot 段的当前原生几何；StartPos／EndPos 为 Montage 绝对秒。 */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOMontageTimelineSegmentFact
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FName SlotName;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 SlotIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 SegmentIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float StartPos = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float EndPos = 0.0f;
	/** 段引用对象路径；无引用为空。 */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString AnimReference;
};

/** 一个 Montage Notify 声明的当前原生读回。
 *  Time=GetTime（作者声明位置），TriggerTimeOffset 为引擎保存的偏移，TriggerTime=GetTriggerTime。
 *  只描述资产声明，不代表派发、播放实例或任何能力权限。 */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOMontageTimelineNotifyFact
{
	GENERATED_BODY()

	/** 编辑器数据 Guid；不可用时为空，消费者应拒绝。 */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString Guid;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 TrackIndex = INDEX_NONE;
	/** Notify 对象的类路径；没有 Notify 对象时为空。 */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString NotifyClass;
	/** Notify 或 NotifyState 对象路径。 */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString NotifyObject;
	/** PlayMontageNotify／Window（含子类）用于原生 Broadcast 的 NotifyName；其它类型为 None。 */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FName StockNotifyName;
	/** NotifyState 对象的类路径；没有时为空。 */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString StateClass;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float Time = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float TriggerTimeOffset = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float TriggerTime = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float Duration = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float EndTriggerTime = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 SlotIndex = INDEX_NONE;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	int32 SegmentIndex = INDEX_NONE;
	/** 作者链接方式：Absolute／Relative／Proportional。 */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString LinkMethod;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	bool bIsBranchingPoint = false;
	/** LinkedMontage 是否为被读取的 Montage 本身。 */
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	bool bLinkedToSelf = false;
};

/** 本次调用对输入 Montage 的原生时间轴读回；不缓存，失败时不签发任何时间或声明。 */
USTRUCT(BlueprintType)
struct GGYGOEDITOR_API FGGYGOMontageTimelineFacts
{
	GENERATED_BODY()

	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	bool bSucceeded = false;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	FString Error;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	float PlayLength = 0.0f;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	TArray<FGGYGOMontageTimelineSectionFact> Sections;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	TArray<FGGYGOMontageTimelineSegmentFact> Segments;
	UPROPERTY(BlueprintReadOnly, Category = "GGYGO|Editor|Animation")
	TArray<FGGYGOMontageTimelineNotifyFact> Notifies;
};

/** 不保存包，不编辑源、Skeleton 或运行时；调用者拥有新对象和失败产物的清理决定。 */
UCLASS()
class GGYGOEDITOR_API UGGYGOLinearMontageAuthorLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * 仅配置调用者新建、尚未在磁盘存在的 Montage。每源完整播放一次，segment rate=1，
	 * 区段按原生 GetLength 相邻连接，最后 Next=None；不设置表现参数或创建 Notify。
	 * 原 SourceBinding 和 Movement 验证负责完整轨迹及 PosXYZ/Yaw 合同。
	 * @param Sequences 已就绪的准确源；不加载或替换缺失来源。
	 * @param SectionNames 与源逐一对应的唯一非空名称。
	 * @return 实际验证结果；失败可留下新对象的未保存状态，不回滚或清退其它资源。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOLinearMontageAuthorResult AuthorNewMontage(UAnimMontage* Montage, FName SlotName,
		const TArray<UAnimSequence*>& Sequences, const TArray<FName>& SectionNames);

	/** 对准确预期源和线性区段只读验证；供保存前和独立冷加载后消费，不写资产或创建 controller。 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOLinearMontageAuthorResult ValidateMontage(UAnimMontage* Montage, FName SlotName,
		const TArray<UAnimSequence*>& Sequences, const TArray<FName>& SectionNames);

	/**
	 * GameThread 只读复制任意现有 Montage 的 Section、Slot 段和 Notify 声明原生时间。
	 * 不 Modify、刷新缓存、重链接、PostEditChange 或保存；不验证完整源，也不替代 ValidateMontage。
	 * @param Montage 当前调用者持有的 Montage；结果只属于本次调用，不在库内缓存。
	 * @return 原生事实；输入无效或不在 GameThread 时 bSucceeded=false 且数组为空。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Animation")
	static FGGYGOMontageTimelineFacts ReadMontageTimelineFacts(const UAnimMontage* Montage);
};
