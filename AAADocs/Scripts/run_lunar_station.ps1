# 在副本项目启动独立的制作或试玩实例，输出保存在本次试次目录。
param([ValidateSet('Build','Lighting','Lower','Upper','P3Control')][string]$Mode='Build',
      [string]$Engine='F:/UE5.9/UE_5.9',
      [string]$FFmpeg,[switch]$CheckReturn)
$ErrorActionPreference='Stop'
if ($CheckReturn -and $Mode -ne 'Upper') { throw '折返检查需要上层路线' }
$projectRoot=(Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$project=Join-Path $projectRoot 'GGYGO.uproject'
if ((Get-Content -Raw $project | ConvertFrom-Json).EngineAssociation -ne '5.9') { throw '仅供 5.9 副本使用' }
$output=Join-Path $projectRoot ('Saved/Codex/LunarStation/'+(Get-Date -Format yyyyMMdd_HHmmssfff)+'_'+$Mode)
New-Item -ItemType Directory -Path $output | Out-Null
$env:GGYGO_STATION_OUTPUT=$output
$env:GGYGO_STATION_ROUTE=$Mode
$env:GGYGO_STATION_CHECK_RETURN=if ($CheckReturn) {'1'} else {'0'}
$env:GGYGO_STATION_FFMPEG=if ($FFmpeg) {(Resolve-Path -LiteralPath $FFmpeg).Path} else {''}
$arguments=@($project,'-unattended','-NoSplash','-NoLiveCoding','-SCCProvider=None','-notraceserver','-traceautostart=0',
    ('-UserDir="'+$output+'/Editor"'),('-AbsLog="'+$output+'/editor.log"'),'-LogFlushInterval=0.05',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:LoadLevelAtStartup=None',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False')
if ($Mode -in @('Build','Lighting')) {
    $binary=Join-Path $Engine 'Engine/Binaries/Win64/UnrealEditor-Cmd.exe'
    $arguments+=@('-d3d12','-AllowCommandletRendering','-RenderOffScreen','-run=pythonscript',('-script="'+$PSScriptRoot+'/build_lunar_station.py"'))
} else {
    $binary=Join-Path $Engine 'Engine/Binaries/Win64/UnrealEditor.exe'
    $entryMap=if ($Mode -eq 'P3Control') {'/Game/Map/BH3/L_KevinBoss_P3'} else {'/Game/Map/LunarStation/L_LunarStation'}
    $arguments+=@($entryMap,'-d3d12','-RenderOffScreen','-LogCmds="LogGGYGOMovementInput Verbose"',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:LastExecutedPlayModeType=PlayMode_InEditorFloating',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNetMode=PIE_Standalone',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNumberOfClients=1',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:NewWindowWidth=1280',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:NewWindowHeight=720',
        ('-ExecCmds="py '+$PSScriptRoot.Replace('\','/')+'/walk_lunar_station.py"'))
}
$process=Start-Process -FilePath $binary -ArgumentList $arguments -WorkingDirectory $projectRoot -WindowStyle Hidden -PassThru
[pscustomobject]@{Id=$process.Id;Mode=$Mode;Output=$output} | ConvertTo-Json
