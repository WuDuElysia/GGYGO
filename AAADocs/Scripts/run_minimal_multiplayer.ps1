<#
.SYNOPSIS
启动本需求自己的两个 D3D12 离屏 Editor；不占用或终止其它 Editor。
.DESCRIPTION
运行前先按看板等制作实例正常退出，重新实测内存。
此脚本只做最后的冲突检查并启动，输出与 UserDir 按试次隔离。
脚本返回 PID；等待和结果检查由当前会话继续完成。
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidateSet('all', 'attack_only', 'correction', 'initial_unavailable', 'live_first', 'closed_first', 'reacquire')]
    [string[]]$Case,
    [Parameter(Mandatory=$true)][string]$Output,
    [int]$ServerPort = 17877,
    [switch]$TailSeekProbe
)
$ErrorActionPreference = 'Stop'
$taskRoot = 'F:\ue_project\GGYGO'
$taskEngine = 'F:\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$taskPython = Join-Path $taskRoot 'AAADocs\Scripts\observe_minimal_multiplayer.py'
$taskOutput = [IO.Path]::GetFullPath($Output)
if ($Case -contains 'all' -and $Case.Count -ne 1) { throw 'all 不能与单独场景混用。' }
if ($TailSeekProbe -and ($Case.Count -ne 1 -or $Case[0] -ne 'live_first')) {
    throw '活尾追赶回归只允许独立 live_first 场景，不能混作常规晚加入验收。'
}
if (-not $taskOutput.StartsWith((Join-Path $taskRoot 'Saved\Codex\'), [StringComparison]::OrdinalIgnoreCase)) {
    throw '输出必须位于本项目 Saved\Codex 内。'
}
if (Test-Path -LiteralPath $taskOutput) { throw '输出目录已存在，请为新试次指定新目录。' }
$taskProcesses = @(Get-CimInstance Win32_Process | Where-Object {
    $_.Name -match '^UnrealEditor(-Cmd)?\.exe$' -or
    ($_.Name -match '^(dotnet|UnrealBuildTool)\.exe$' -and $_.CommandLine -match 'UnrealBuildTool')
})
if ($taskProcesses.Count) {
    $taskProcesses | Select-Object ProcessId, Name, CommandLine | Format-Table -Wrap
    throw '仍有 Editor 或 UBT；本需求等现有制作正常收尾后再起双端。'
}
$taskOS = Get-CimInstance Win32_OperatingSystem
$taskCommit = Get-CimInstance Win32_PerfFormattedData_PerfOS_Memory
$taskMemory = [ordered]@{
    available_physical_gib = [math]::Round($taskOS.FreePhysicalMemory / 1MB, 2)
    available_commit_gib = [math]::Round(($taskCommit.CommitLimit - $taskCommit.CommittedBytes) / 1GB, 2)
    measured_at = (Get-Date).ToString('o')
}
# 起步数字是既有实际双端峰值；新试次仍须观察实际增长，不能视为容量保证。
if ($taskMemory.available_physical_gib -lt 14.8 -or $taskMemory.available_commit_gib -lt 24.1) {
    $taskMemory | ConvertTo-Json
    throw '实测空闲量不足以覆盖既有双端起步峰值。'
}
$null = New-Item -ItemType Directory -Path $taskOutput
$taskMemory | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'memory.json') -Encoding utf8
$taskLaunched = @()
foreach ($taskRole in @('authority', 'observer')) {
    $taskRoleDir = Join-Path $taskOutput $taskRole
    $null = New-Item -ItemType Directory -Path $taskRoleDir
    $taskUserDir = Join-Path $taskRoleDir 'Editor'
    $taskLog = Join-Path $taskRoleDir 'editor.log'
    $taskMode = if ($taskRole -eq 'authority') { 'PIE_ListenServer' } else { 'PIE_Standalone' }
    $taskClients = if ($taskRole -eq 'authority') { 2 } else { 1 }
    $taskControlPort = if ($taskRole -eq 'authority') { 8001 } else { 8002 }
    $env:GGYGO_MULTIPLAYER_OUT = $taskOutput
    $env:GGYGO_MULTIPLAYER_ROLE = $taskRole
    $env:GGYGO_MULTIPLAYER_CASE = $Case -join ','
    $env:GGYGO_MULTIPLAYER_PORT = $ServerPort.ToString()
    $env:GGYGO_MULTIPLAYER_TAIL_PROBE = if ($TailSeekProbe) { '1' } else { '0' }
    $taskArgs = @(
        ('"' + (Join-Path $taskRoot 'GGYGO.uproject') + '"'), '/Game/Map/L_Movement_Test',
        '-d3d12', '-RenderOffScreen', '-unattended', '-nosplash', '-NoLiveCoding', '-SCCProvider=None', '-LogFlushInterval=0.02',
        '-ModelContextProtocolStartServer', ('-ModelContextProtocolPort=' + $taskControlPort),
        ('-UserDir="' + $taskUserDir + '"'), ('-AbsLog="' + $taskLog + '"'),
        '-NoAssetRegistryCacheWrite', '-ini:Engine:[LogFiles]:PurgeLogsDays=-1',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False',
        ('-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNetMode=' + $taskMode),
        ('-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:PlayNumberOfClients=' + $taskClients),
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:RunUnderOneProcess=True',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:bLaunchSeparateServer=False',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:NewWindowWidth=640',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:NewWindowHeight=360',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:ClientWindowWidth=640',
        '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:ClientWindowHeight=360',
        ('-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.LevelEditorPlaySettings]:ServerPort=' + $ServerPort),
        '-LogCmds="LogNet Log,LogNetTraffic Log,LogNetLifecycle Log,LogNetDormancy Verbose,LogGGYGOAbilitySystem Verbose,LogGGYGOMovementInputOrigin Verbose,LogGGYGOMovementInput Verbose"',
        ('-ExecCmds="py ' + $taskPython.Replace('\','/') + '"')
    )
    if ($Case -contains 'reacquire' -or $Case -contains 'all') {
        # 原生 Config 的进程内覆盖；不写配置文件，Editor 退出后即撤销。
        $taskArgs += '-ini:Engine:[/Script/OnlineSubsystemUtils.IpNetDriver]:RelevantTimeout=0.05'
    }
    $taskProcess = Start-Process -FilePath $taskEngine -ArgumentList $taskArgs -WorkingDirectory $taskRoot -WindowStyle Hidden -PassThru
    $taskLaunched += [ordered]@{role=$taskRole; pid=$taskProcess.Id; log=$taskLog; arguments=$taskArgs}
    $taskLaunched | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskOutput 'processes.json') -Encoding utf8
}
$taskLaunched | ForEach-Object { [pscustomobject]$_ } | Select-Object role, pid, log | Format-Table -AutoSize
