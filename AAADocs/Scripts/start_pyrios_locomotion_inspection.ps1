<#
@file start_pyrios_locomotion_inspection.ps1
@brief 在统筹已分配的独占窗口中启动只读检查宿主并持有真实进程句柄。

RunName 必须是未使用的 Saved/Codex 子目录；两 DLL 身份取自当前协调好的
构建交接。本入口启动标准 Editor；指定 StartupScript 时通过原生 ExecCmds
调用已冻结的只读检查脚本，否则 MCP 就绪后由调用方核对宿主身份并读取。
检查结束后请求该宿主正常退出，不启动 PIE 或进行资产生产。
就绪失败也保留句柄等待正常退出，不强杀、保存或丢弃任何资产。
#>
param(
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Za-z0-9_]+$')]
    [string]$RunName,
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$RuntimeDllSha,
    [Parameter(Mandatory=$true)]
    [ValidatePattern('^[A-Fa-f0-9]{64}$')]
    [string]$EditorDllSha,
    [string]$InputProtectionManifest,
    [string]$StartupScript
)

$ErrorActionPreference = 'Stop'
$taskRoot = 'F:\ue_project\GGYGO'
$taskExe = 'F:\UE_5.8\Engine\Binaries\Win64\UnrealEditor.exe'
$taskOutput = Join-Path $taskRoot ('Saved\Codex\' + $RunName)
$taskRuntime = Join-Path $taskRoot 'Binaries\Win64\UnrealEditor-GGYGO.dll'
$taskEditor = Join-Path $taskRoot 'Binaries\Win64\UnrealEditor-GGYGOEditor.dll'
if ((Get-FileHash -LiteralPath $taskRuntime -Algorithm SHA256).Hash -ne $RuntimeDllSha -or
    (Get-FileHash -LiteralPath $taskEditor -Algorithm SHA256).Hash -ne $EditorDllSha) {
    throw 'DLL 不属于当前构建交接；停止启动'
}

function Get-InspectionRelatedProcesses {
    Get-CimInstance Win32_Process | Where-Object {
        $_.Name -like 'UnrealEditor*.exe' -or
        $_.Name -in @('ShaderCompileWorker.exe', 'UnrealBuildTool.exe', 'LiveCodingConsole.exe', 'AutomationTool.exe') -or
        ($_.Name -eq 'dotnet.exe' -and
            ([string]::IsNullOrWhiteSpace($_.CommandLine) -or $_.CommandLine -match 'UnrealBuildTool|AutomationTool'))
    } | Select-Object ProcessId, ParentProcessId, Name
}

function Get-InspectionProtectedSnapshot {
    $taskRequired = @(
        'Binaries/Win64/UnrealEditor-GGYGO.dll', 'Binaries/Win64/UnrealEditor-GGYGOEditor.dll',
        'Content/BP/Anim/ABP_Pyrios.uasset', 'Content/BP/Character/Player/BP_PC_Pyrios.uasset',
        'Content/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model.uasset',
        'Content/Characters/Player/Pyrios/Avatar_Male_Size03_Pyrois_Model_Skeleton.uasset',
        'Config/DefaultEngine.ini', 'Config/DefaultEditor.ini', 'GGYGO.uproject',
        'AAADocs/Scripts/inspect_pyrios_locomotion_pose.py',
        'AAADocs/Scripts/start_pyrios_locomotion_inspection.ps1', 'AAADocs/Scripts/ue_mcp.py'
    ) | ForEach-Object { [IO.Path]::GetFullPath((Join-Path $taskRoot $_)) }
    $taskRootPrefix = $taskRoot.TrimEnd('\') + '\'
    if (-not [string]::IsNullOrWhiteSpace($StartupScript)) {
        $taskStartupPath = [IO.Path]::GetFullPath((Join-Path $taskRoot $StartupScript))
        if (-not $taskStartupPath.StartsWith($taskRootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw '启动检查脚本须位于当前工程内'
        }
        $taskRequired += $taskStartupPath
    }
    if (-not [string]::IsNullOrWhiteSpace($InputProtectionManifest)) {
        $taskManifestPath = [IO.Path]::GetFullPath((Join-Path $taskRoot $InputProtectionManifest))
        if (-not $taskManifestPath.StartsWith($taskRootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
            throw '附加保护清单须位于当前工程内'
        }
        $taskManifest = Get-Content -LiteralPath $taskManifestPath -Raw -Encoding utf8 | ConvertFrom-Json
        if ($null -eq $taskManifest.inputs -or @($taskManifest.inputs.PSObject.Properties).Count -eq 0) {
            throw '附加保护清单缺少真实 inputs'
        }
        $taskRequired += $taskManifestPath
        foreach ($taskInputName in $taskManifest.inputs.PSObject.Properties.Name) {
            if ([IO.Path]::IsPathRooted($taskInputName)) { throw '附加保护输入须为工程相对路径' }
            $taskInputPath = [IO.Path]::GetFullPath((Join-Path $taskRoot $taskInputName))
            if (-not $taskInputPath.StartsWith($taskRootPrefix, [StringComparison]::OrdinalIgnoreCase)) {
                throw '附加保护输入越出当前工程'
            }
            $taskRequired += $taskInputPath
        }
    }
    $taskInventory = @(
        Get-ChildItem -LiteralPath (Join-Path $taskRoot 'Content') -Recurse -File |
            Where-Object { $_.Extension -in '.uasset', '.umap', '.uexp', '.ubulk' }
        Get-ChildItem -LiteralPath (Join-Path $taskRoot 'Source') -Recurse -File |
            Where-Object { $_.Extension -in '.h', '.cpp', '.cs' }
        Get-ChildItem -LiteralPath (Join-Path $taskRoot 'Config') -Recurse -File |
            Where-Object { $_.Extension -eq '.ini' }
        Get-ChildItem -LiteralPath (Join-Path $taskRoot 'AAADocs') -Recurse -File |
            Where-Object { $_.Extension -in '.hlsl', '.hlsli', '.usf', '.ush' }
        $taskShaders = Join-Path $taskRoot 'Shaders'
        if (Test-Path -LiteralPath $taskShaders) {
            Get-ChildItem -LiteralPath $taskShaders -Recurse -File
        }
    ) | ForEach-Object { $_.FullName }
    foreach ($taskPath in @($taskRequired + $taskInventory | Sort-Object -Unique)) {
        if (-not (Test-Path -LiteralPath $taskPath -PathType Leaf)) {
            [PSCustomObject]@{path=$taskPath; missing=$true; size=$null; last_write_utc_ticks=$null; sha256=$null}
            continue
        }
        $taskInfo = Get-Item -LiteralPath $taskPath
        [PSCustomObject]@{
            path=$taskInfo.FullName; size=$taskInfo.Length; last_write_utc_ticks=$taskInfo.LastWriteTimeUtc.Ticks
            sha256=(Get-FileHash -LiteralPath $taskPath -Algorithm SHA256).Hash
        }
    }
}

$taskProcesses = @(Get-InspectionRelatedProcesses)
$taskListeners = @([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
    Where-Object { $_.Port -in 8000, 8001, 8002 })
if ($taskProcesses.Count -ne 0 -or $taskListeners.Count -ne 0) {
    throw '相关 UE/构建进程或 MCP 端口已占用；交统筹重新协调窗口'
}
if (Test-Path -LiteralPath $taskOutput) { throw '拒绝复用或覆盖原检查目录' }
New-Item -ItemType Directory -Path $taskOutput | Out-Null

$taskProtected = @(Get-InspectionProtectedSnapshot)
if (@($taskProtected | Where-Object { $_.missing }).Count -ne 0) {
    throw '必需保护文件缺失；停止启动'
}
[PSCustomObject]@{
    schema='GGYGO.LocomotionInspectionBefore/v1'
    protected=$taskProtected
    inspector_sha256=(Get-FileHash -LiteralPath (Join-Path $taskRoot 'AAADocs/Scripts/inspect_pyrios_locomotion_pose.py') -Algorithm SHA256).Hash
    input_protection_manifest=$InputProtectionManifest
    startup_script=$StartupScript
    processes=@(); ports=@(); utc=[DateTime]::UtcNow.ToString('o')
} | ConvertTo-Json -Depth 6 | Set-Content -LiteralPath (Join-Path $taskOutput 'before.json') -Encoding utf8

$taskArgs = @(
    '"F:\ue_project\GGYGO\GGYGO.uproject"', '/Engine/Maps/Entry',
    '-unattended', '-NoSplash', '-NoSound', '-NoLiveCoding', '-SCCProvider=None',
    '-stdout', '-FullStdOutLogOutput', '-ForceLogFlush',
    '-ModelContextProtocolStartServer', '-ModelContextProtocolPort=8000',
    ('-AbsLog="' + (Join-Path $taskOutput 'editor.log') + '"'),
    '-ini:EditorPerProjectUserSettings:[/Script/UnrealEd.EditorLoadingSavingSettings]:bAutoSaveEnable=False'
)
if (-not [string]::IsNullOrWhiteSpace($StartupScript)) {
    $taskArgs += '-ExecCmds="py ' + [IO.Path]::GetFullPath((Join-Path $taskRoot $StartupScript)).Replace('\', '/') + '"'
}
$taskProcess = Start-Process -FilePath $taskExe -ArgumentList $taskArgs -WorkingDirectory $taskRoot `
    -WindowStyle Hidden -PassThru -RedirectStandardOutput (Join-Path $taskOutput 'stdout.log') `
    -RedirectStandardError (Join-Path $taskOutput 'stderr.log')
# 持有同一个 Process 对象直至退出；不凭另一 sandbox 中的 PID 查询判定宿主退出。
$taskReady = $false
try {
    $taskHost = [PSCustomObject]@{
        schema='GGYGO.LocomotionInspectionHost/v1'; pid=$taskProcess.Id; launch_parent=$PID
        exe=$taskExe; reserved_port=8000; args=$taskArgs
    }
    $taskHost | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath (Join-Path $taskOutput 'host.json') -Encoding utf8
    $taskHost | ConvertTo-Json -Depth 5 -Compress | Write-Output
    $taskDeadline = [DateTime]::UtcNow.AddSeconds(90)
    while (-not $taskProcess.HasExited -and [DateTime]::UtcNow -lt $taskDeadline) {
        $taskPort = @(Get-NetTCPConnection -State Listen -LocalPort 8000 -ErrorAction SilentlyContinue)
        if ($taskPort.Count -gt 0) {
            if (@($taskPort | Where-Object { $_.OwningProcess -ne $taskProcess.Id }).Count -gt 0) {
                throw '8000 监听者不是自有宿主；停止检查，等待正常退出'
            }
            $taskReady = $true
            break
        }
        Start-Sleep -Milliseconds 500
    }
    [PSCustomObject]@{pid=$taskProcess.Id; mcp_listening=$taskReady; inspection_executed=$false} |
        ConvertTo-Json -Compress | Write-Output
} catch {
    [PSCustomObject]@{pid=$taskProcess.Id; readiness_error=$_.Exception.Message; inspection_executed=$false} |
        ConvertTo-Json -Compress | Write-Output
} finally {
    while (-not $taskProcess.WaitForExit(1000)) { }
    $taskExit = [PSCustomObject]@{
        schema='GGYGO.LocomotionInspectionHostExit/v1'; pid=$taskProcess.Id
        exit_code=$taskProcess.ExitCode; utc=[DateTime]::UtcNow.ToString('o')
    }
    $taskExit | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $taskOutput 'host_exit.json') -Encoding utf8
    $taskExit | ConvertTo-Json -Compress | Write-Output
}
# 退出收据只表达实际宿主退出；检查与共享归还另按读回及保护判定。
try {
    $taskAfter = @(Get-InspectionProtectedSnapshot)
    $taskBeforeByPath = @{}
    $taskAfterByPath = @{}
    foreach ($taskEntry in $taskProtected) { $taskBeforeByPath[$taskEntry.path] = $taskEntry }
    foreach ($taskEntry in $taskAfter) { $taskAfterByPath[$taskEntry.path] = $taskEntry }
    $taskChanged = @(@($taskBeforeByPath.Keys) + @($taskAfterByPath.Keys) | Sort-Object -Unique | Where-Object {
        $taskOld = $taskBeforeByPath[$_]
        $taskNew = $taskAfterByPath[$_]
        $null -eq $taskOld -or $null -eq $taskNew -or $taskOld.sha256 -ne $taskNew.sha256 -or
            $taskOld.size -ne $taskNew.size -or $taskOld.last_write_utc_ticks -ne $taskNew.last_write_utc_ticks
    })
    $taskResultFile = Join-Path $taskOutput 'readback.json'
    $taskResult = $null
    $taskResultSha = $null
    $taskResultError = $null
    $taskResultExists = Test-Path -LiteralPath $taskResultFile -PathType Leaf
    if ($taskResultExists) {
        $taskResultSha = (Get-FileHash -LiteralPath $taskResultFile -Algorithm SHA256).Hash
        try {
            $taskResult = Get-Content -LiteralPath $taskResultFile -Raw -Encoding utf8 | ConvertFrom-Json
            if ($taskResult.schema -ne 'GGYGO.PyriosLocomotionInspection/v1' -or $taskResult.pid -ne $taskProcess.Id) {
                throw 'Inspector 结果的 schema/PID 与自有宿主不匹配'
            }
        } catch {
            $taskResultError = $_.Exception.Message
        }
    }
    $taskRemaining = @(Get-InspectionRelatedProcesses)
    $taskPortsAfter = @([System.Net.NetworkInformation.IPGlobalProperties]::GetIPGlobalProperties().GetActiveTcpListeners() |
        Where-Object { $_.Port -in 8000, 8001, 8002 } | ForEach-Object { $_.Port })
    $taskLog = Join-Path $taskOutput 'editor.log'
    $taskLogExists = Test-Path -LiteralPath $taskLog -PathType Leaf
    $taskSaves = @(if ($taskLogExists) {
        Select-String -LiteralPath $taskLog -Pattern 'LogSavePackage|Saving package|SavePackage' |
            ForEach-Object { $_.Line }
    })
    $taskDirty = $(if ($null -ne $taskResult -and $null -eq $taskResultError) { $taskResult.dirty_after } else { $null })
    $taskDirtyClean = $null -ne $taskDirty -and
        ($taskDirty.PSObject.Properties.Name -contains 'content') -and
        ($taskDirty.PSObject.Properties.Name -contains 'maps') -and
        @($taskDirty.content).Count -eq 0 -and @($taskDirty.maps).Count -eq 0
    $taskReturn = [PSCustomObject]@{
        schema='GGYGO.LocomotionInspectionReturn/v1'; pid=$taskProcess.Id; host_exit=$taskExit
        mcp_listening_observed=$taskReady; inspection_result_exists=$taskResultExists
        inspection_completed=($null -ne $taskResult -and $null -eq $taskResultError -and $taskResult.inspection_completed -eq $true)
        report_sha256=$taskResultSha; report_error=$taskResultError
        dirty_observed=$taskDirty; dirty_clean=$taskDirtyClean
        protected_count=$taskProtected.Count; protected_after=$taskAfter; changed_files=$taskChanged
        all_protected_unchanged=($taskChanged.Count -eq 0); processes=$taskRemaining; ports=$taskPortsAfter
        shared_idle=($taskRemaining.Count -eq 0 -and $taskPortsAfter.Count -eq 0)
        editor_log_exists=$taskLogExists; save_package_log_lines=$taskSaves; utc=[DateTime]::UtcNow.ToString('o')
    }
    $taskReturn | ConvertTo-Json -Depth 7 | Set-Content -LiteralPath (Join-Path $taskOutput 'after.json') -Encoding utf8
    [PSCustomObject]@{
        pid=$taskProcess.Id; inspection_completed=$taskReturn.inspection_completed
        all_protected_unchanged=$taskReturn.all_protected_unchanged; shared_idle=$taskReturn.shared_idle
        dirty_clean=$taskDirtyClean; report_sha256=$taskResultSha; return_record=(Join-Path $taskOutput 'after.json')
    } | ConvertTo-Json -Compress | Write-Output
    if ($taskProcess.ExitCode -ne 0) { exit $taskProcess.ExitCode }
    if (-not $taskReturn.inspection_completed -or -not $taskReturn.all_protected_unchanged -or
        -not $taskReturn.shared_idle -or -not $taskDirtyClean -or -not $taskLogExists -or $taskSaves.Count -ne 0) { exit 1 }
} catch {
    [PSCustomObject]@{
        schema='GGYGO.LocomotionInspectionReturnFailure/v1'; pid=$taskProcess.Id; host_exit=$taskExit
        error=$_.Exception.Message; utc=[DateTime]::UtcNow.ToString('o')
    } | ConvertTo-Json -Depth 4 | Set-Content -LiteralPath (Join-Path $taskOutput 'after_failure.json') -Encoding utf8
    throw
}
