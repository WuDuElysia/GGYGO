/** @file GGYGOPrimitiveDataReadLibrary.h
 *  @brief 向编辑器脚本提供实际运行时图元数据的只读快照。
 */
#pragma once

#include "CoreMinimal.h"
#include "Kismet/BlueprintFunctionLibrary.h"
#include "GGYGOPrimitiveDataReadLibrary.generated.h"

class UPrimitiveComponent;

/** 编辑器验证工具；不持有图元、不修改数据或驱动渲染生命周期。 */
UCLASS()
class GGYGOEDITOR_API UGGYGOPrimitiveDataReadLibrary : public UBlueprintFunctionLibrary
{
	GENERATED_BODY()

public:
	/**
	 * 复制图元当前送往渲染器的 Custom Primitive Data，保留原始长度及数值。
	 * @param Primitive 实际被验证的图元组件。
	 * @param OutData 当前运行时数据的副本；成功时允许原生空数组。
	 * @param OutError 无效图元的可定位原因；失败清空 OutData。
	 * @return 图元有效且已读取。数据是否满足具体材质契约由调用者验证。
	 */
	UFUNCTION(BlueprintCallable, Category = "GGYGO|Editor|Rendering")
	static bool ReadRuntimeCustomPrimitiveData(
		const UPrimitiveComponent* Primitive,
		TArray<float>& OutData,
		FString& OutError);
};
