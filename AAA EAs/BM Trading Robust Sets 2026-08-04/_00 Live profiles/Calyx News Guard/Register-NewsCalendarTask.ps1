# Creates / refreshes the Windows scheduled task "Calyx News Calendar" (2026-11-20).
# Uses the ScheduledTasks module instead of schtasks.exe: schtasks /TR broke on paths with spaces ("Invalid argument/option - 'EAs\BM'").
# Runs Update-NewsCalendar.ps1 hidden at 06:00 and 18:00 (FTMO publishes the next week's list during the week), catches up after the PC was off.
# Runs as the current user while logged on (no password stored). Returns $true on success.
[CmdletBinding()]
param()
$ErrorActionPreference = 'Stop'
$script = Join-Path $PSScriptRoot 'Update-NewsCalendar.ps1'
try {
    if (-not (Test-Path -LiteralPath $script)) { throw "missing $script" }
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoLogo -NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File "{0}" -Quiet' -f $script)
    $triggers = @((New-ScheduledTaskTrigger -Daily -At '06:00'), (New-ScheduledTaskTrigger -Daily -At '18:00'))
    $settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    Register-ScheduledTask -TaskName 'Calyx News Calendar' -Action $action -Trigger $triggers -Settings $settings `
        -Description 'Calyx News Guard: downloads the FTMO restricted-news calendar (ForexFactory fallback) for the News Guard chart.' -Force | Out-Null
    Write-Host 'Daily task "Calyx News Calendar" ready (06:00 and 18:00).' -ForegroundColor Green
    return $true
} catch {
    Write-Host ('Could not create the daily task: {0}' -f $_.Exception.Message) -ForegroundColor Red
    Write-Host 'Run "Update News Calendar.bat" yourself every day instead.' -ForegroundColor Red
    return $false
}
