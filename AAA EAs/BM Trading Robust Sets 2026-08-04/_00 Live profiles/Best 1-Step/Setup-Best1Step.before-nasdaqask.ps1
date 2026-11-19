# Best 1-Step all-in-one setup (owner 2026-11-18: "one script file that will apply all these extra stuff ... all into 1 place").
# 1. asks the account type -> fills in every installer answer (phase, risk, weekend flat, no-opposite, news guard, Nasdaq / DI / caps defaults)
# 2. downloads the news calendar now
# 3. creates / refreshes the daily Windows task "Calyx News Calendar" (06:00) - asked, default yes
# 4. runs the right Best 1-Step installer with those answers. The installer still asks for each EA (Enter = install) and for its
#    typed confirmation; it restarts MT5 into a new profile with Algo Trading OFF and never places orders.
# Windows PowerShell 5.1. Nothing here touches MT5 except step 4 (the normal installer).
[CmdletBinding()]
param([ValidateSet('', '1', '2', '3', '4', '5', '6', '7')][string]$Type = '', [switch]$ValidateOnly)   # -Type 2 = skip the account-type question
Set-StrictMode -Version 2.0
$ErrorActionPreference = 'Stop'
$here = $PSScriptRoot
$news = Join-Path (Split-Path -Parent $here) 'Calyx News Guard'
$updaterBat = Join-Path $news 'Update News Calendar.bat'
$guarded = Join-Path $here '1-Step\Install-Best1Step-1Step.ps1'
$noguard = Join-Path (Split-Path -Parent $here) 'Packages\Best1Step\Install-Portfolio.ps1'
foreach ($p in @($updaterBat, (Join-Path $news 'Update-NewsCalendar.ps1'), $guarded, $noguard)) { if (-not (Test-Path -LiteralPath $p)) { throw "Missing file: $p" } }

# account type -> installer answers (firm rules from the 2026-11-17/18 email replies; risk = tested best in Best 1-Step Add Gold 2026-11-18)
$types = [ordered]@{
    '1' = @{ Name = 'FTMO 1-Step - CHALLENGE';  Guard = $true;  Phase = 'Challenge'; Risk = 0.75; Weekend = 'ON'; NoOpp = 'OFF'; News = 'OFF'; Why = 'news allowed in evaluations' }
    '2' = @{ Name = 'FTMO 1-Step - FUNDED';     Guard = $true;  Phase = 'Funded';    Risk = 0.5;  Weekend = 'ON'; NoOpp = 'OFF'; News = '2';   Why = 'funded Standard: no trading +-2 min around news, flat before weekends' }
    '3' = @{ Name = 'FTMO 2-Step - CHALLENGE';  Guard = $false; Phase = '';          Risk = 0.75; Weekend = 'ON'; NoOpp = 'OFF'; News = 'OFF'; Why = 'news allowed in evaluations' }
    '4' = @{ Name = 'FTMO 2-Step - FUNDED';     Guard = $false; Phase = '';          Risk = 0.5;  Weekend = 'ON'; NoOpp = 'OFF'; News = '2';   Why = 'funded Standard: +-2 min news, flat before weekends' }
    '5' = @{ Name = 'The5ers High Stakes';      Guard = $false; Phase = '';          Risk = 0.75; Weekend = 'ON'; NoOpp = 'OFF'; News = '2';   Why = 'no trades +-2 min around high-impact news' }
    '6' = @{ Name = 'FundingPips';              Guard = $false; Phase = '';          Risk = 0.75; Weekend = 'ON'; NoOpp = 'ON';  News = '5';   Why = 'news +-5 min = profit removed; no hedging' }
}
Write-Host ''
Write-Host 'BEST 1-STEP - ALL-IN-ONE SETUP (10 EAs, Nasdaq 5M at 0.75x risk)' -ForegroundColor Green
Write-Host 'Before you start: MT5 open and logged in on the prop account, NO open positions / orders, Algo Trading OFF, hedging account.' -ForegroundColor Yellow
Write-Host ''
foreach ($k in $types.Keys) { $t = $types[$k]; Write-Host ('  {0} = {1,-26} risk {2}%  weekend flat {3}  no-opposite {4}  news guard {5}' -f $k, $t.Name, $t.Risk, $t.Weekend, $t.NoOpp, $t.News) }
Write-Host '  7 = Custom: the normal installer asks every question'
if ($Type) { $choice = $Type } elseif ($ValidateOnly) { $choice = '1' } else { $choice = (Read-Host 'Account type 1-7').Trim() }
if ($ValidateOnly -and $choice -eq '7') { throw 'Validate types 1-6.' }
if ($choice -eq '7') { $t = $null } elseif ($types.Contains($choice)) { $t = $types[$choice] } else { throw 'Choose 1 to 7.' }

$risk = 0.0
if ($t) {
    Write-Host ("{0}: {1}" -f $t.Name, $t.Why) -ForegroundColor Cyan
    $risk = [double]$t.Risk
    if (-not $ValidateOnly) {
        $answer = (Read-Host ("Risk per trade in % [{0}]  (0.75 = faster pass, 0.5 = safer)" -f $t.Risk)).Trim()
        if ($answer) { if (-not [double]::TryParse($answer, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$risk)) { throw 'Enter a number with a decimal point, e.g. 0.5' } }
    }
    if ($risk -le 0 -or $risk -gt 2) { throw 'Risk must be above 0 and at most 2%.' }
}

# step 2: calendar now
$newsOn = (-not $t) -or ($t.News -ne 'OFF')
Write-Host ''; Write-Host 'STEP 1/3 - news calendar' -ForegroundColor Cyan
if ($ValidateOnly) { Write-Host '  (validate only: not downloaded)' }
else {
    & cmd.exe /c "call `"$updaterBat`" -Quiet"
    if ($LASTEXITCODE -ne 0) {
        Write-Host 'Calendar download FAILED.' -ForegroundColor Red
        if ($newsOn -and (Read-Host 'Continue anyway? The news guard cannot block anything without a calendar. y/N') -notin @('y', 'Y')) { Write-Host 'Stopped. Nothing installed.'; exit 1 }
    }
}

# step 3: daily task
Write-Host ''; Write-Host 'STEP 2/3 - daily calendar update (Windows Task Scheduler, 06:00, task "Calyx News Calendar")' -ForegroundColor Cyan
if ($ValidateOnly) { Write-Host '  (validate only: not created)' }
else {
    $have = $false; try { $null = & schtasks.exe /Query /TN 'Calyx News Calendar' 2>$null; $have = ($LASTEXITCODE -eq 0) } catch { $have = $false }
    $q = if ($have) { 'Task already exists. Refresh it? Y/n' } else { 'Create the daily task? Y/n' }
    if ((Read-Host $q).Trim() -notin @('n', 'N', 'no', 'NO')) {
        $tr = '"' + $updaterBat + '" -Quiet'
        & schtasks.exe /Create /F /TN 'Calyx News Calendar' /SC DAILY /ST 06:00 /TR $tr | Out-Host
        if ($LASTEXITCODE -ne 0) { Write-Host 'Could not create the task: run "Update News Calendar.bat" yourself every day.' -ForegroundColor Red }
    } else { Write-Host '  Skipped: run "Update News Calendar.bat" yourself every day.' -ForegroundColor Yellow }
}

# step 4: installer
Write-Host ''; Write-Host 'STEP 3/3 - install the EAs' -ForegroundColor Cyan
$inv = [Globalization.CultureInfo]::InvariantCulture
if (-not $t) {
    $script = $noguard; $args2 = @()
    if ((Read-Host 'Custom: 1 = FTMO 1-Step guard installer, 2 = no-guard installer [2]').Trim() -eq '1') { $script = $guarded; $args2 = @('-Interactive') }
} elseif ($t.Guard) {
    $script = $guarded
    $args2 = @('-Interactive', '-Phase', $t.Phase, '-RiskMode', 'PERCENT', '-RiskValue', $risk.ToString($inv), '-NasdaqDIFilter', 'OFF', '-UsdJpyDIFilter', 'ON',
               '-NasdaqStopVersion', 'NEW', '-TotalRiskCap', '4.5', '-SymbolRiskCap', '3', '-WeekendFlat', $t.Weekend, '-NoOpposite', $t.NoOpp, '-NewsGuard', $t.News, '-NasdaqRiskFactor', '0.75')
} else {
    $script = $noguard
    $args2 = @('-RiskMode', 'PERCENT', '-RiskValue', $risk.ToString($inv), '-NasdaqDIFilter', 'OFF', '-UsdJpyDIFilter', 'ON', '-NasdaqStopVersion', 'NEW',
               '-WeekendFlat', $t.Weekend, '-NoOpposite', $t.NoOpp, '-NewsGuard', $t.News, '-NasdaqRiskFactor', '0.75')
}
if ($ValidateOnly) { $args2 += '-ValidateOnly' }
else { Write-Host 'The installer now asks for EACH EA: press Enter 10 times to install all 10 (the tested set), then type its confirmation.' -ForegroundColor Yellow }
Write-Host ('Running: {0} {1}' -f (Split-Path -Leaf $script), ($args2 -join ' '))
& powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $script @args2
$code = $LASTEXITCODE
Write-Host ''
if ($code -eq 0 -and -not $ValidateOnly) {
    Write-Host 'DONE. Now in MT5: check the new profile (10 EA charts + Calyx Weekend Flat + Calyx News Guard if ON), then turn Algo Trading ON yourself.' -ForegroundColor Green
} elseif ($code -ne 0) { Write-Host ("Installer stopped (exit {0}). Read the message above before running it again." -f $code) -ForegroundColor Red }
exit $code
