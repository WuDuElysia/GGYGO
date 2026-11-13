<# .SYNOPSIS 启动正式 P3 联机专项的自有 D3D12 Editor；不保存资产。 #>
param([Parameter(Mandatory=$true)][string]$Output)
$ErrorActionPreference = 'Stop'
$taskRoot = 'F:\ue_project\GGYGO'
$taskOutput = [IO.Path]::GetFullPath($Output)
if (-not $taskOutput.StartsWith((Join-Path $taskRoot 'Saved\Codex\'), [StringComparison]::OrdinalIgnoreCase)) {
    throw '输出必须位于本项目 Saved\Codex 内。'
}
if (Test-Path -LiteralPath $taskOutput) { throw '试次目录已存在。' }
$taskProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -or
    ($_.Name -match '^(dotnet|UnrealBuildTool)\.exe$' -and $_.CommandLine -match 'UnrealBuildTool')
})
if ($taskProcesses.Count) { throw '仍有 Editor 或 UBT，不能占用。' }
$null = New-Item -ItemType Directory -Path $taskOutput
$env:GGYGO_KEVIN_NETWORK_OUT = $taskOutput
$taskArgs = @(
    ('"'+(Join-Path $taskRoot 'GGYGO.uproject')+'"'), '/Game/Map/BH3/L_KevinBoss_P3',
    '-d3d12', '-RenderOffScreen', '-unattended', '-nosplash', '-NoLiveCoding', '-SCCProvider=None', '-NoAssetRegistryCacheWrite',
    '-LogFlushInterval=0.02', '-notraceserver', '-traceautostart=0',
    ('-UserDir="'+(Join-Path $taskOutput 'Editor')+'"'), ('-AbsLog="'+(Join-Path $taskOutput 'editor.log')+'"'),
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorPerformanceSettings]:bThrottleCPUWhenNotForeground=False',
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:ServerPort=17877',
    '-LogCmds="LogNet Log,LogNetTraffic Verbose,LogNetLifecycle Log,LogGGYGOAbilitySystem Verbose"',
    ('-ExecCmds="py '+(Join-Path $taskRoot 'AAADocs/Scripts/observe_kevin_multiplayer.py').Replace('\','/')+'"')
)
$taskProcess = Start-Process -FilePath 'F:\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe' -ArgumentList $taskArgs -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru
[ordered]@{pid=$taskProcess.Id; log=(Join-Path $taskOutput 'editor.log'); arguments=$taskArgs} |
    ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskOutput 'process.json') -Encoding utf8
$taskProcess.Id
