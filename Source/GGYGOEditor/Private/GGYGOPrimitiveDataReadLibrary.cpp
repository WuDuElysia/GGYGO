/** @file GGYGOPrimitiveDataReadLibrary.cpp
 *  @brief 通过引擎公开 getter 读取图元数据，不读取序列化默认值。
 */
#include "GGYGOPrimitiveDataReadLibrary.h"

#include "Components/PrimitiveComponent.h"

bool UGGYGOPrimitiveDataReadLibrary::ReadRuntimeCustomPrimitiveData(
	const UPrimitiveComponent* Primitive,
	TArray<float>& OutData,
	FString& OutError)
{
	OutData.Reset();
	OutError.Reset();
	if (!IsValid(Primitive))
	{
		OutError = FString::Printf(TEXT("[Rendering][PrimitiveDataRead] Primitive='%s': 无效图元，无法读取运行时数据。"),
			*GetPathNameSafe(Primitive));
		return false;
	}

	OutData = Primitive->GetCustomPrimitiveData().Data;
	return true;
}
