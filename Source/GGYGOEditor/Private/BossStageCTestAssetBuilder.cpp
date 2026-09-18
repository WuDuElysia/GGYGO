/** @file BossStageCTestAssetBuilder.cpp @brief 可重复生成 BOSSAI 阶段 C 的最小测试资产 */
#include "AI/Boss/BehaviorTree/BTTask_GGYGOActivateAbility.h"
#include "AI/Boss/BehaviorTree/BTTask_GGYGOChooseBossAction.h"
#include "Animation/Notifies/GGYGOAnimNotifyState_GameplayEventWindow.h"
#include "AnimationBlueprintLibrary.h"
#include "Animation/AnimSequence.h"
#include "AssetRegistry/AssetRegistryModule.h"
#include "BehaviorTree/BehaviorTree.h"
#include "BehaviorTree/BlackboardData.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Name.h"
#include "BehaviorTree/Blackboard/BlackboardKeyType_Object.h"
#include "BehaviorTree/Composites/BTComposite_Sequence.h"
#include "BehaviorTree/Tasks/BTTask_Wait.h"
#include "Factories/AnimMontageFactory.h"
#include "GameFramework/Actor.h"
#include "HAL/IConsoleManager.h"
#include "Misc/PackageName.h"
#include "System/GGYGOGameplayTags.h"
#include "UObject/SavePackage.h"

namespace GGYGOBossStageCTestAssets
{
	constexpr TCHAR AssetFolder[] = TEXT("/Game/AI/Boss/Test");
	constexpr TCHAR SourceAnimationPath[] =
		TEXT("/Game/Characters/Player/Pyrios/Animation/Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_01.Avatar_Male_Size03_Pyrois_Ani_Attack_Normal_01");

	template <typename T>
	T* LoadOrCreateAsset(const TCHAR* AssetName)
	{
		const FString PackageName = FString::Printf(TEXT("%s/%s"), AssetFolder, AssetName);
		const FString ObjectPath = FString::Printf(TEXT("%s.%s"), *PackageName, AssetName);
		if (T* Existing = LoadObject<T>(nullptr, *ObjectPath))
		{
			return Existing;
		}

		UPackage* Package = CreatePackage(*PackageName);
		T* Asset = NewObject<T>(Package, AssetName, RF_Public | RF_Standalone | RF_Transactional);
		FAssetRegistryModule::AssetCreated(Asset);
		return Asset;
	}

	bool SaveAsset(UObject* Asset)
	{
		if (!Asset)
		{
			return false;
		}

		UPackage* Package = Asset->GetOutermost();
		Package->MarkPackageDirty();
		const FString Filename = FPackageName::LongPackageNameToFilename(
			Package->GetName(), FPackageName::GetAssetPackageExtension());
		FSavePackageArgs SaveArgs;
		SaveArgs.TopLevelFlags = RF_Public | RF_Standalone;
		SaveArgs.SaveFlags = SAVE_NoError;
		return UPackage::SavePackage(Package, Asset, *Filename, SaveArgs);
	}

	UBlackboardData* BuildBlackboard()
	{
		UBlackboardData* Blackboard = LoadOrCreateAsset<UBlackboardData>(TEXT("BB_Boss_Test"));
		Blackboard->Modify();
		Blackboard->Keys.Reset();

		Blackboard->UpdatePersistentKey<UBlackboardKeyType_Name>(TEXT("SelectedAction"));
		if (UBlackboardKeyType_Object* TargetKey =
			Blackboard->UpdatePersistentKey<UBlackboardKeyType_Object>(TEXT("TargetActor")))
		{
			TargetKey->BaseClass = AActor::StaticClass();
		}
		Blackboard->UpdateKeyIDs();
		Blackboard->UpdateIfHasSynchronizedKeys();
		return SaveAsset(Blackboard) ? Blackboard : nullptr;
	}

	UBehaviorTree* BuildBehaviorTree(UBlackboardData* Blackboard)
	{
		if (!Blackboard)
		{
			return nullptr;
		}

		UBehaviorTree* Tree = LoadOrCreateAsset<UBehaviorTree>(TEXT("BT_Boss_Test"));
		Tree->Modify();
		Tree->BlackboardAsset = Blackboard;
		Tree->RootDecorators.Reset();
		Tree->RootDecoratorOps.Reset();

		UBTComposite_Sequence* Sequence = NewObject<UBTComposite_Sequence>(Tree, TEXT("ActionLoop"), RF_Transactional);
		UBTTask_GGYGOChooseBossAction* Choose =
			NewObject<UBTTask_GGYGOChooseBossAction>(Tree, TEXT("ChooseAction"), RF_Transactional);
		UBTTask_GGYGOActivateAbility* Activate =
			NewObject<UBTTask_GGYGOActivateAbility>(Tree, TEXT("ActivateAbility"), RF_Transactional);
		UBTTask_Wait* Wait = NewObject<UBTTask_Wait>(Tree, TEXT("ActionInterval"), RF_Transactional);
		Wait->WaitTime = 0.75f;
		Wait->RandomDeviation = 0.0f;

		Sequence->Children.Reset();
		Sequence->Children.AddDefaulted_GetRef().ChildTask = Choose;
		Sequence->Children.AddDefaulted_GetRef().ChildTask = Activate;
		Sequence->Children.AddDefaulted_GetRef().ChildTask = Wait;
		Tree->RootNode = Sequence;
		return SaveAsset(Tree) ? Tree : nullptr;
	}

	UAnimMontage* BuildAttackMontage()
	{
		UAnimSequence* SourceAnimation = LoadObject<UAnimSequence>(nullptr, SourceAnimationPath);
		if (!SourceAnimation)
		{
			UE_LOG(LogTemp, Error, TEXT("BOSSAI 阶段 C：找不到测试攻击动画 [%s]。"), SourceAnimationPath);
			return nullptr;
		}

		constexpr TCHAR MontageName[] = TEXT("AM_BossMelee_Test");
		const FString PackageName = FString::Printf(TEXT("%s/%s"), AssetFolder, MontageName);
		const FString ObjectPath = FString::Printf(TEXT("%s.%s"), *PackageName, MontageName);
		UAnimMontage* Montage = LoadObject<UAnimMontage>(nullptr, *ObjectPath);
		if (!Montage)
		{
			UPackage* Package = CreatePackage(*PackageName);
			UAnimMontageFactory* Factory = NewObject<UAnimMontageFactory>();
			Factory->SourceAnimation = SourceAnimation;
			Montage = Cast<UAnimMontage>(Factory->FactoryCreateNew(
				UAnimMontage::StaticClass(), Package, MontageName,
				RF_Public | RF_Standalone | RF_Transactional, nullptr, GWarn));
			if (Montage)
			{
				FAssetRegistryModule::AssetCreated(Montage);
			}
		}
		if (!Montage)
		{
			return nullptr;
		}

		Montage->Modify();
		const FName NotifyTrackName(TEXT("BossHitWindow"));
		UAnimationBlueprintLibrary::RemoveAnimationNotifyEventsByTrack(Montage, NotifyTrackName);
		if (!UAnimationBlueprintLibrary::IsValidAnimNotifyTrackName(Montage, NotifyTrackName))
		{
			UAnimationBlueprintLibrary::AddAnimationNotifyTrack(Montage, NotifyTrackName, FLinearColor::Red);
		}

		const float StartTime = FMath::Min(0.45f, Montage->GetPlayLength() * 0.35f);
		const float Duration = FMath::Min(0.35f, FMath::Max(0.05f, Montage->GetPlayLength() - StartTime - 0.05f));
		if (UGGYGOAnimNotifyState_GameplayEventWindow* EventWindow =
			Cast<UGGYGOAnimNotifyState_GameplayEventWindow>(
				UAnimationBlueprintLibrary::AddAnimationNotifyStateEvent(
					Montage, NotifyTrackName, StartTime, Duration,
					UGGYGOAnimNotifyState_GameplayEventWindow::StaticClass())))
		{
			EventWindow->InitializeEventTags(
				GGYGOGameplayTags::Event_Montage_HitWindowBegin,
				GGYGOGameplayTags::Event_Montage_HitWindowEnd);
		}

		return SaveAsset(Montage) ? Montage : nullptr;
	}

	void Build()
	{
		UBlackboardData* Blackboard = BuildBlackboard();
		UBehaviorTree* Tree = BuildBehaviorTree(Blackboard);
		UAnimMontage* Montage = BuildAttackMontage();
		if (Blackboard && Tree && Montage)
		{
			UE_LOG(LogTemp, Display,
				TEXT("BOSSAI 阶段 C 测试资产生成完成：[%s]、[%s]、[%s]。"),
				*GetNameSafe(Blackboard), *GetNameSafe(Tree), *GetNameSafe(Montage));
		}
		else
		{
			UE_LOG(LogTemp, Error, TEXT("BOSSAI 阶段 C 测试资产生成失败，请检查上方日志。"));
		}
	}

	FAutoConsoleCommand BuildCommand(
		TEXT("GGYGO.BuildBossStageCTestAssets"),
		TEXT("生成或更新 BOSSAI 阶段 C 的 Blackboard、BehaviorTree 与攻击 Montage。"),
		FConsoleCommandDelegate::CreateStatic(&Build));
}
