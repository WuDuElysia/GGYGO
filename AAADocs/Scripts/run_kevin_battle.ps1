# 只启动我方单机诊断实例；完整战斗使用生产 BT 和原玩家输入。
param([Parameter(Mandatory=$true)][string]$RunName, [switch]$DeathShadow)
$ErrorActionPreference='Stop'
$taskDriver=if ($DeathShadow) { 'observe_kevin_death_shadow.py' } else { 'observe_kevin_battle.py' }
$taskRoot='F:/ue_project/GGYGO'
$taskRun=Join-Path $taskRoot ('Saved/Codex/KevinFinalBattle/'+$RunName)
if (Test-Path -LiteralPath $taskRun) { throw '不得覆盖旧试次' }
$taskConflicts=@(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -or
    ($_.Name -match '^(dotnet|UnrealBuildTool)\.exe$' -and $_.CommandLine -match 'UnrealBuildTool')
})
if ($taskConflicts.Count) { throw '有 UE 或 UBT 占用' }
New-Item -ItemType Directory -Path $taskRun | Out-Null
$env:GGYGO_KEVIN_LOG=Join-Path $taskRun 'editor.log'
$env:GGYGO_KEVIN_DIAGNOSTIC_CAMERA='1'
$taskArgs=@('F:/ue_project/GGYGO/GGYGO.uproject', '-d3d12','-RenderOffScreen','-unattended','-NoSplash','-NoLiveCoding',
    '-SCCProvider=None','-NoAssetRegistryCacheWrite','-notraceserver','-traceautostart=0','-LogFlushInterval=0.02',
    ('-UserDir="'+$taskRun+'/Editor"'),('-AbsLog="'+$taskRun+'/editor.log"'),
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:LoadLevelAtStartup=None',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:LastExecutedPlayModeType=PlayMode_InEditorFloating',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNetMode=PIE_Standalone',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNumberOfClients=1',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:RunUnderOneProcess=True',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:NewWindowWidth=1280',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:NewWindowHeight=720',
    ('-ExecCmds="py '+$PSScriptRoot.Replace('\','/')+'/'+$taskDriver+'"'))
$taskProcess=Start-Process -FilePath 'F:/UE_5.8/Engine/Binaries/Win64/UnrealEditor.exe' -ArgumentList $taskArgs -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru
@{pid=$taskProcess.Id;arguments=$taskArgs} | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskRun 'process.json') -Encoding utf8
$taskProcess.Id
