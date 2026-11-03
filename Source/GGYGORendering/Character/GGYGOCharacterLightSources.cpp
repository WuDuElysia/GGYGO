/** @file GGYGOCharacterLightSources.cpp
 *  @brief 同次核真实来源/实例并按Nap贡献与稳定key选余槽，不持跨帧灯缓存。
 */
#include "GGYGOCharacterLightSources.h"

#include "Engine/World.h"

bool UGGYGOCharacterLightSources::RegisterSource(UObject* SourceOwner, uint64 OriginalInstanceId,
	FGGYGOReadCharacterPointLights Getter, uint64& OutHandle, FString& OutError)
{
	check(IsInGameThread());
	OutHandle = 0;
	OutError.Reset();
	if (!IsValid(SourceOwner) || SourceOwner->GetWorld() != GetWorld() || !GetWorld()
		|| GetWorld()->bIsTearingDown || GetWorld()->GetNetMode() == NM_DedicatedServer
		|| !OriginalInstanceId || !Getter.IsBound() || NextHandle == MAX_uint64)
	{ OutError = TEXT("FX灯来源缺同World原Owner/实例/弱Getter或handle已耗尽"); return false; }
	for (const auto& Pair : Sources)
		if (Pair.Value.Owner == SourceOwner && Pair.Value.InstanceId == OriginalInstanceId)
		{ OutError = TEXT("同一FX实例已有Point灯来源登记"); return false; }
	OutHandle = NextHandle++;
	Sources.Add(OutHandle, {SourceOwner, OriginalInstanceId, MoveTemp(Getter)});
	return true;
}

void UGGYGOCharacterLightSources::UnregisterSource(uint64 Handle)
{
	check(IsInGameThread());
	Sources.Remove(Handle);
}

void UGGYGOCharacterLightSources::Deinitialize()
{
	Sources.Reset();
	Super::Deinitialize();
}

bool UGGYGOCharacterLightSources::ValidateSelection(const FGGYGOCharacterFXLightSelection& C, FString& OutError)
{
	OutError.Reset();
	if (C.Mode == EGGYGOCharacterFXLightMode::Disabled) return true;
	if (C.Mode != EGGYGOCharacterFXLightMode::NapPointFromNativeRadius || !C.bConfigured
		|| C.MaxLights < 1 || C.MaxLights > 4 || !FMath::IsFinite(C.IntensityScale) || C.IntensityScale < 0)
	{ OutError = TEXT("FX选灯需要明确模式、1..4额度及有限非负强度"); return false; }
	return true;
}

EGGYGOCharacterLightSourceReadiness UGGYGOCharacterLightSources::SelectLights(const FVector& PositionWorldCm,
	int32 RemainingSlots, const FGGYGOCharacterFXLightSelection& Configuration,
	TArray<FGGYGOCharacterSelectedPointLight>& OutLights, FString& OutError)
{
	check(IsInGameThread());
	const FGGYGOCharacterFXLightSelection C = Configuration;
	UWorld* const OriginalWorld = GetWorld();
	OutLights.Reset();
	if (!ValidateSelection(C, OutError) || PositionWorldCm.ContainsNaN() || PositionWorldCm.GetAbsMax() * 0.01 > MAX_flt
		|| !OriginalWorld || OriginalWorld->bIsTearingDown || RemainingSlots < 0 || RemainingSlots > 4)
	{
		if (OutError.IsEmpty()) OutError = TEXT("FX选灯的实际角色位置/剩余额度无效");
		return EGGYGOCharacterLightSourceReadiness::Invalid;
	}
	if (C.Mode == EGGYGOCharacterFXLightMode::Disabled || !RemainingSlots || !C.IntensityScale)
		return EGGYGOCharacterLightSourceReadiness::Ready;
	struct FCandidate { FGGYGOCharacterSelectedPointLight Sample; double Contribution = 0; };
	TArray<FCandidate> Candidates;
	TArray<uint64> Handles;
	Sources.GenerateKeyArray(Handles);
	Handles.Sort();
	for (uint64 Handle : Handles)
	{
		const FSource* Source = Sources.Find(Handle);
		if (!Source) continue;
		const FSource Original = *Source;
		if (!Original.Owner.IsValid() || Original.Owner->GetWorld() != GetWorld())
		{ Sources.Remove(Handle); continue; } // 原Owner寿命结束；与仍存活的失败Getter区分。
		if (!Original.Getter.IsBound())
		{
			// 弱回调端点寿命已结束，摘除原登记；本次仍失败，不把退役改为空灯成功。
			Sources.Remove(Handle);
			OutError = FString::Printf(TEXT("FX灯来源%llu仍存活但Getter已失效"), Handle);
			return EGGYGOCharacterLightSourceReadiness::SourceFailed;
		}
		FGGYGOCharacterPointLightFrame Frame;
		FString Error;
		const auto Readiness = Original.Getter.Execute(Frame, Error);
		if (!IsValid(this) || GetWorld() != OriginalWorld || OriginalWorld->bIsTearingDown)
		{ OutError = TEXT("采样期间原灯来源World已归还"); return EGGYGOCharacterLightSourceReadiness::Invalid; }
		// 失败清理也可能注销本来源；注销不能把Getter的真实失败改成正常空灯。
		if (Readiness != EGGYGOCharacterLightSourceReadiness::Ready
			&& Readiness != EGGYGOCharacterLightSourceReadiness::WaitingForSimulation)
		{
			OutError = FString::Printf(TEXT("FX灯%llu实例%llu: %s"), Handle, Original.InstanceId, *Error);
			return EGGYGOCharacterLightSourceReadiness::SourceFailed;
		}
		// Getter可结束原FX并注销；返栈后只消费原handle/弱端点/实例仍相同的数据。
		Source = Sources.Find(Handle);
		if (!Source) continue;
		if (Source->Owner != Original.Owner || Source->InstanceId != Original.InstanceId || !Original.Owner.IsValid())
		{ OutError = FString::Printf(TEXT("采样期间FX灯%llu实例%llu来源身份改变"), Handle, Original.InstanceId); return EGGYGOCharacterLightSourceReadiness::SourceFailed; }
		if (Original.Owner->GetWorld() != OriginalWorld) { Sources.Remove(Handle); continue; }
		if (Readiness != EGGYGOCharacterLightSourceReadiness::Ready)
		{
			OutError = FString::Printf(TEXT("FX灯%llu实例%llu: %s"), Handle, Original.InstanceId, *Error);
			return Readiness;
		}
		if (Frame.InstanceId != Original.InstanceId || !FMath::IsFinite(Frame.SimulationAgeSeconds) || Frame.SimulationAgeSeconds < 0)
		{ OutError = FString::Printf(TEXT("FX灯%llu实例%llu帧缺准确实例/实际模拟年龄"), Handle, Original.InstanceId); return EGGYGOCharacterLightSourceReadiness::SourceFailed; }
		TSet<uint64> Keys;
		for (const auto& Light : Frame.Lights)
		{
			if (Keys.Contains(Light.StableKey) || Light.PositionWorldCm.ContainsNaN() || Light.PositionWorldCm.GetAbsMax() * 0.01 > MAX_flt
				|| !FMath::IsFinite(Light.RadiusCm) || Light.RadiusCm <= 0
				|| !FMath::IsFinite(Light.NativeFalloffExponent) || Light.NativeFalloffExponent < 0
				|| !FMath::IsFinite(Light.Color.R) || !FMath::IsFinite(Light.Color.G) || !FMath::IsFinite(Light.Color.B) || !FMath::IsFinite(Light.Color.A))
			{ OutError = FString::Printf(TEXT("FX灯%llu的实际Point字段/稳定key无效"), Handle); return EGGYGOCharacterLightSourceReadiness::SourceFailed; }
			Keys.Add(Light.StableKey);
			const double RadiusMeters = double(Light.RadiusCm) * 0.01;
			const double InverseRadiusSquared = 1.0 / FMath::Square(RadiusMeters);
			const double DistanceSquared = FMath::Max((Light.PositionWorldCm * 0.01 - PositionWorldCm * 0.01).SizeSquared(), double(MIN_flt));
			double Range = DistanceSquared * InverseRadiusSquared;
			const bool bInverseSquared = Light.NativeFalloffExponent == 0;
			if (bInverseSquared) Range *= Range;
			const double Attenuation = FMath::Square(FMath::Clamp(1.0 - Range, 0.0, 1.0)) / (bInverseSquared ? DistanceSquared : 1.0);
			const double ColorMagnitude = FMath::Max3(FMath::Abs(double(Light.Color.R)), FMath::Abs(double(Light.Color.G)), FMath::Abs(double(Light.Color.B)));
			const double Contribution = ColorMagnitude * double(C.IntensityScale) * Attenuation;
			const FLinearColor Color = Light.Color * C.IntensityScale;
			if (!FMath::IsFinite(InverseRadiusSquared) || InverseRadiusSquared > MAX_flt || !FMath::IsFinite(Contribution)
				|| !FMath::IsFinite(Color.R) || !FMath::IsFinite(Color.G) || !FMath::IsFinite(Color.B))
			{ OutError = FString::Printf(TEXT("FX灯%llu半径/强度映射不能表示为材质float32"), Handle); return EGGYGOCharacterLightSourceReadiness::SourceFailed; }
			if (Contribution <= 0) continue;
			FGGYGOCharacterSelectedPointLight Sample;
			Sample.SourceHandle = Handle;
			Sample.InstanceId = Frame.InstanceId;
			Sample.SimulationAgeSeconds = Frame.SimulationAgeSeconds;
			Sample.Light = Light;
			Sample.Light.Color = Color;
			Sample.Attenuation = FVector4(InverseRadiusSquared, bInverseSquared ? 0 : -1, 0, 1);
			Candidates.Add({MoveTemp(Sample), Contribution});
		}
	}
	Candidates.Sort([](const FCandidate& A, const FCandidate& B)
	{
		if (A.Contribution != B.Contribution) return A.Contribution > B.Contribution;
		if (A.Sample.SourceHandle != B.Sample.SourceHandle) return A.Sample.SourceHandle < B.Sample.SourceHandle;
		return A.Sample.Light.StableKey < B.Sample.Light.StableKey;
	});
	const int32 Count = FMath::Min3(RemainingSlots, C.MaxLights, Candidates.Num());
	for (int32 Index = 0; Index < Count; ++Index) OutLights.Add(MoveTemp(Candidates[Index].Sample));
	return EGGYGOCharacterLightSourceReadiness::Ready;
}
