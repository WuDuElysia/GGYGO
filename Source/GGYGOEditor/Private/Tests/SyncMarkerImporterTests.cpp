/** @file SyncMarkerImporterTests.cpp @brief 验证编辑器迁移后的旧类引用及真实导入入口。 */

#include "SyncMarkerImporter.h"

#if WITH_DEV_AUTOMATION_TESTS
#include "Animation/AnimSequence.h"
#include "Engine/MemberReference.h"
#include "HAL/FileManager.h"
#include "HAL/IConsoleManager.h"
#include "Misc/AutomationTest.h"
#include "Misc/FileHelper.h"
#include "Misc/Paths.h"
#include "Misc/ScopeExit.h"
#include "UObject/Package.h"
#include "UObject/CoreRedirects.h"
#include "UObject/SoftObjectPath.h"
#include "UObject/StrongObjectPtr.h"

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSyncMarkerImporterRedirectTest,
	"GGYGO.Editor.Animation.SyncMarkerImporter.LegacyReferences",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FSyncMarkerImporterRedirectTest::RunTest(const FString& Parameters)
{
	UClass* EditorClass = USyncMarkerImporter::StaticClass();
	TestEqual(TEXT("类只由编辑器模块提供"), EditorClass->GetPathName(), FString(TEXT("/Script/GGYGOEditor.SyncMarkerImporter")));
	// 与 FLinkerLoad::FixupImportMap 的 Class import 修正使用同一入口。
	// 裸 LoadClass 路径和 ImportText 不经过这一资产加载步骤。
	const FCoreRedirectObjectName RedirectedName = FCoreRedirects::GetRedirectedName(ECoreRedirectFlags::Type_Class,
		FCoreRedirectObjectName(TEXT("/Script/GGYGO.SyncMarkerImporter")));
	TestEqual(TEXT("旧 Class import 定向到编辑器类"), RedirectedName.ToString(), EditorClass->GetPathName());
	UClass* ImportedClass = LoadClass<UObject>(nullptr, *RedirectedName.ToString());
	TestEqual(TEXT("修正后的硬类引用可加载"), ImportedClass, EditorClass);
	FSoftObjectPath OldPath(TEXT("/Script/GGYGO.SyncMarkerImporter"));
	TestTrue(TEXT("旧软引用应用 CoreRedirects"), OldPath.FixupCoreRedirects());
	TestEqual(TEXT("软引用指向同一编辑器类"), OldPath.TryLoad(), static_cast<UObject*>(EditorClass));

	for (const FName FunctionName : {GET_FUNCTION_NAME_CHECKED(USyncMarkerImporter, ImportSingleJson),
		GET_FUNCTION_NAME_CHECKED(USyncMarkerImporter, ImportSyncMarkersFromDirectory)})
	{
		FMemberReference MemberReference;
		MemberReference.SetExternalMember(FunctionName, ImportedClass);
		UFunction* Function = EditorClass->FindFunctionByName(FunctionName);
		TestNotNull(TEXT("原反射函数仍存在"), Function);
		TestEqual(TEXT("Class import 修正后，蓝图成员引用解析到原函数"), MemberReference.ResolveMember<UFunction>(), Function);
	}
	TestNotNull(TEXT("原控制台命令仍已注册"), IConsoleManager::Get().FindConsoleObject(TEXT("SyncMarkerImport")));
	return true;
}

IMPLEMENT_SIMPLE_AUTOMATION_TEST(FSyncMarkerImporterEntryTest,
	"GGYGO.Editor.Animation.SyncMarkerImporter.ImportEntries",
	EAutomationTestFlags::EditorContext | EAutomationTestFlags::EngineFilter)

bool FSyncMarkerImporterEntryTest::RunTest(const FString& Parameters)
{
	const FString Id = FGuid::NewGuid().ToString(EGuidFormats::Digits);
	const FString AssetDirectory = TEXT("/Temp/SyncMarkerImporter_") + Id;
	const FString JsonDirectory = FPaths::ConvertRelativePathToFull(FPaths::ProjectSavedDir() / TEXT("Automation/SyncMarkerImporter") / Id);
	const FString JsonPath = JsonDirectory / TEXT("Clip.json");
	UPackage* Package = CreatePackage(*(AssetDirectory / TEXT("Clip")));
	TStrongObjectPtr<UAnimSequence> Sequence(NewObject<UAnimSequence>(Package, TEXT("Clip"), RF_Public));
	// 仅写本测试新建的临时动画；从不保存项目包。
	ON_SCOPE_EXIT
	{
		Package->SetDirtyFlag(false);
		IFileManager::Get().Delete(*JsonPath);
		IFileManager::Get().DeleteDirectory(*JsonDirectory);
	};
	if (!TestTrue(TEXT("创建自有 JSON 目录"), IFileManager::Get().MakeDirectory(*JsonDirectory, true))) { return false; }
	const FString Json = TEXT(R"([{"Type":"AnimSequence","Properties":{"AuthoredSyncMarkers":[{"MarkerName":"Left","Time":0.1},{"MarkerName":"Right","Time":0.4}]}}])");
	if (!TestTrue(TEXT("写入自有导入样本"), FFileHelper::SaveStringToFile(Json, *JsonPath))) { return false; }
	TestTrue(TEXT("单文件真实入口成功"), USyncMarkerImporter::ImportSingleJson(JsonPath, AssetDirectory));
	TestEqual(TEXT("单文件写入两项 Marker"), Sequence->AuthoredSyncMarkers.Num(), 2);
	if (Sequence->AuthoredSyncMarkers.Num() == 2)
	{
		TestEqual(TEXT("首个 Marker 名称"), Sequence->AuthoredSyncMarkers[0].MarkerName, FName(TEXT("Left")));
		TestEqual(TEXT("首个 Marker 时点"), Sequence->AuthoredSyncMarkers[0].Time, 0.1f);
		TestEqual(TEXT("第二个 Marker 名称"), Sequence->AuthoredSyncMarkers[1].MarkerName, FName(TEXT("Right")));
		TestEqual(TEXT("第二个 Marker 时点"), Sequence->AuthoredSyncMarkers[1].Time, 0.4f);
	}
	TestTrue(TEXT("导入标脏，交调用方保存"), Package->IsDirty());
	Sequence->AuthoredSyncMarkers.Empty();
	Package->SetDirtyFlag(false);
	const FString Command = FString::Printf(TEXT("SyncMarkerImport \"%s\" \"%s\" Locomotion"), *JsonDirectory, *AssetDirectory);
	TestTrue(TEXT("原控制台命令执行批量入口"), IConsoleManager::Get().ProcessUserConsoleInput(*Command, *GLog, nullptr));
	TestEqual(TEXT("批量入口实际重写两项 Marker"), Sequence->AuthoredSyncMarkers.Num(), 2);
	TestTrue(TEXT("批量入口同样标脏"), Package->IsDirty());
	return true;
}
#endif
