param(
    [ValidateSet('', 'PERCENT', 'FIXED_USD')][string]$RiskMode = '',
    [double]$RiskValue = 0,
    [ValidateSet('', 'ON', 'OFF')][string]$NasdaqDIFilter = '',
    [ValidateSet('', 'ON', 'OFF')][string]$UsdJpyDIFilter = '',
    [ValidateSet('', 'NEW', 'OLD')][string]$NasdaqStopVersion = '',
    [string]$TargetTerminal = '',
    [switch]$ValidateOnly,
    [switch]$PreflightOnly,
    [switch]$Yes
)
$ErrorActionPreference = 'Stop'
# Shared install-time choices for every Calyx portfolio installer (owner request 2026-11-03: "add questions that will ask to use
# old or new version of the nasdaq 5m and enable or disable ... all the guards ... use full descriptions").
# Pure functions: no MT5, account or file access. The single source is _00 Live profiles\Calyx-InstallChoices.ps1; package builds
# copy it next to each installer. Defaults always reproduce the current tested behaviour (press Enter to keep it).

function Write-CalyxNasdaqVersionHelp {
    Write-Host ''
    Write-Host 'NASDAQ 5M CANDLE MOMENTUM - which initial stop-loss?' -ForegroundColor Cyan
    Write-Host '  Both versions: same 09:30 New York M5 signal (EMA12 + optional DI14 filter), no take profit, the stop then trails'
    Write-Host '  6 x ATR(14) behind the best price once the trade is +1R, positions may stay open overnight and over weekends.'
    Write-Host '  1 = NEW (default, deployed 2026-11-02): initial stop = 6 x ATR(14) on M5 at entry. It adapts to volatility:'
    Write-Host '      median 0.61% of price, about 0.28% in quiet markets and 1.2% in fast ones. Native MT5 2019-2026, 1% risk:'
    Write-Host '      +164%, worst closed drawdown 24%, worst year -11.6% (2020); last 5 years +113%, last 12 months +31%.'
    Write-Host '  2 = OLD (2026-09-28 to 2026-11-02): initial stop = 0.60% of the entry price, the same distance every day.'
    Write-Host '      Native MT5 2019-2026, 1% risk: +162%, worst closed drawdown 39%, worst year -27.5% (2020);'
    Write-Host '      last 5 years +220% and last 12 months +48% (most of it from the strong 2025 trend).'
    Write-Host '  Backtests are history, not a forecast. The NEW stop is steadier over 2019-2026; the OLD one earned more since late 2021.' -ForegroundColor Yellow
}

function Read-CalyxNasdaqVersion([string]$Current, [bool]$NoPrompt) {
    if ($Current) { if ($Current -notin @('NEW', 'OLD')) { throw 'Nasdaq 5M version must be NEW or OLD.' }; return $Current }
    if ($NoPrompt) { return 'NEW' }
    Write-CalyxNasdaqVersionHelp
    $answer = (Read-Host 'Nasdaq 5M stop version: 1 = NEW ATR(14) x 6, 2 = OLD 0.60% of price [1]').Trim()
    if (-not $answer -or $answer -eq '1') { return 'NEW' }
    if ($answer -eq '2') { return 'OLD' }
    throw 'Choose 1 (NEW) or 2 (OLD).'
}

# Applies the chosen stop to a Nasdaq 5M input table (hashtable / ordered dictionary of SET values). Only these two inputs differ.
function Set-CalyxNasdaqVersion($Inputs, [string]$Version) {
    if (-not $Version) { $Version = 'NEW' }   # integrity checks run before the question: blank = the default NEW stop
    foreach ($key in @('InpStopMode', 'InpInitialStopATR', 'InpInitialStopPercent')) {
        if (-not $Inputs.Contains($key)) { throw "Nasdaq 5M preset lacks $key; cannot apply the stop version." }
    }
    if ($Version -eq 'OLD') {
        if ([double]::Parse([string]$Inputs['InpInitialStopPercent'], [Globalization.CultureInfo]::InvariantCulture) -ne 0.60) { throw 'OLD version needs InpInitialStopPercent=0.60.' }
        $Inputs['InpStopMode'] = '2'; $Inputs['InpInitialStopATR'] = '4.0'
    } elseif ($Version -eq 'NEW') {
        $Inputs['InpStopMode'] = '0'; $Inputs['InpInitialStopATR'] = '6.0'
    } else { throw 'Nasdaq 5M version must be NEW or OLD.' }
}

function Get-CalyxNasdaqVersionText([string]$Version) {
    if ($Version -eq 'OLD') { 'OLD stop: 0.60% of entry price (2026-09-28 preset)' } else { 'NEW stop: 6 x ATR(14) (2026-11-02 preset)' }
}

function Write-CalyxAdaptiveHelp {
    Write-Host ''
    Write-Host 'PORTFOLIO RISK GOVERNOR (Recommended Adaptive) - ON or OFF?' -ForegroundColor Cyan
    Write-Host '  It only changes the risk of NEW entries. Open trades, their stops and targets are never touched.'
    Write-Host '  The five news EAs never use it (they keep their own news risk).'
    Write-Host '  ON (default) - every other EA applies these three rules to itself:'
    Write-Host "    1. Daily stop: no new entries for the rest of the server day once today's CLOSED losses reach 5% of the balance."
    Write-Host '    2. Drawdown taper: entry risk x0.5 while the account is 4% or more below its closed-balance peak, x0.25 at 7% or more.'
    Write-Host '    3. Loss-streak taper: entry risk x0.5 after 3 losing trades in a row of that EA, x0.25 after 5; a win resets it.'
    Write-Host '  OFF - every EA always trades its full chosen risk, including during losing streaks and drawdowns.'
    Write-Host '  The published Full EA / Recommended Adaptive results were built with it ON; OFF is not separately tested.' -ForegroundColor Yellow
}

function Read-CalyxOnOff([string]$Current, [bool]$NoPrompt, [string]$Question, [string]$Default = 'ON') {
    if ($Current) { if ($Current -notin @('ON', 'OFF')) { throw "$Question must be ON or OFF." }; return $Current }
    if ($NoPrompt) { return $Default }
    $answer = (Read-Host ("$Question ON or OFF [$Default]")).Trim().ToUpperInvariant()
    if (-not $answer) { return $Default }
    if ($answer -notin @('ON', 'OFF')) { throw "$Question must be ON or OFF." }
    return $answer
}

function Read-CalyxAdaptiveControls([string]$Current, [bool]$NoPrompt) {
    if (-not $Current -and -not $NoPrompt) { Write-CalyxAdaptiveHelp }
    return Read-CalyxOnOff $Current $NoPrompt 'Portfolio risk governor'
}

# 2026-11-03 owner: "make ask for cap option when installing the bat ... 4.5, 6, 8 and no cap and 3x, no cap per symbol".
# Prop Ready guard family only (Prop ready / Codex, FTMO any-broker, Best Prop 9 / 15). Enter keeps the tested 4.5 R / 3 R.
function Write-CalyxRiskCapHelp {
    Write-Host ''
    Write-Host 'OPEN-RISK CAPS - how much stop-loss risk may be open at the same time?' -ForegroundColor Cyan
    Write-Host '  R = your chosen risk per trade, measured on the starting balance. Every open trade counts its initial stop-loss risk.'
    Write-Host '  TOTAL cap: a new entry waits while all open trades plus the new one would exceed this many R.'
    Write-Host '    1 = 4.5 R (default, tested)   2 = 6 R   3 = 8 R   4 = no total cap'
    Write-Host '  PER-SYMBOL cap: the same rule for the trades on one symbol (gold, Nasdaq or USDJPY).'
    Write-Host '    1 = 3 R (default, tested)   2 = no per-symbol cap'
    Write-Host '  All other guards stay ON. The 3% daily reserve counts each open trade at 1.25 x its risk, so open risk stops near'
    Write-Host '  2.4% of the balance anyway (= 2.4 R at 1% risk, 4.8 R at 0.5%). At 1% risk 4.5 / 6 / 8 / none therefore behave the same.'
    Write-Host '  FTMO $100k replay (2026-11-03): 6 R = same pass rate at 1%, same Monte Carlo but a worse 2021-23 history at 0.5%.' -ForegroundColor Yellow
    Write-Host '  8 R and "no cap" were not tested. Bigger caps allow more trades (often several gold EAs) to lose at the same time.' -ForegroundColor Yellow
}

function Read-CalyxTotalRiskCap([string]$Current, [bool]$NoPrompt) {
    if ($Current) { if ($Current -notin @('4.5', '6', '8', 'NONE')) { throw 'Total open-risk cap must be 4.5, 6, 8 or NONE.' }; return $Current }
    if ($NoPrompt) { return '4.5' }
    Write-CalyxRiskCapHelp
    $answer = (Read-Host 'Total open-risk cap: 1 = 4.5 R, 2 = 6 R, 3 = 8 R, 4 = no cap [1]').Trim()
    $choice = @{ '' = '4.5'; '1' = '4.5'; '2' = '6'; '3' = '8'; '4' = 'NONE' }[$answer]
    if (-not $choice) { throw 'Choose 1, 2, 3 or 4.' }
    return $choice
}

function Read-CalyxSymbolRiskCap([string]$Current, [bool]$NoPrompt) {
    if ($Current) { if ($Current -notin @('3', 'NONE')) { throw 'Per-symbol cap must be 3 or NONE.' }; return $Current }
    if ($NoPrompt) { return '3' }
    $answer = (Read-Host 'Per-symbol open-risk cap: 1 = 3 R, 2 = no cap [1]').Trim()
    $choice = @{ '' = '3'; '1' = '3'; '2' = 'NONE' }[$answer]
    if (-not $choice) { throw 'Choose 1 or 2.' }
    return $choice
}

# Guard input value: the multiple, or 0 = that cap OFF.
function Get-CalyxCapMultiple([string]$Choice) { if ($Choice -eq 'NONE') { '0' } else { $Choice } }

# "450.00 (4.5 R)" or "no cap"; $Unit = one R in account currency.
function Get-CalyxCapText([string]$Choice, [double]$Unit) {
    if ($Choice -eq 'NONE') { return 'no cap' }
    $m = [double]::Parse($Choice, [Globalization.CultureInfo]::InvariantCulture)
    return ('{0:N2} ({1} R)' -f ($Unit * $m), $Choice)
}

$PackageRoot = $PSScriptRoot

function Assert-ChildPath([string]$Root, [string]$Path) {
    $base = [IO.Path]::GetFullPath($Root).TrimEnd('\') + '\'
    $full = [IO.Path]::GetFullPath($Path)
    if (-not $full.StartsWith($base, [StringComparison]::OrdinalIgnoreCase)) { throw 'Unsafe path outside the intended directory.' }
    $cursor = $full
    while ($cursor -and $cursor.Length -ge $base.TrimEnd('\').Length) {
        if (Test-Path -LiteralPath $cursor) {
            if ((Get-Item -LiteralPath $cursor -Force).Attributes -band [IO.FileAttributes]::ReparsePoint) { throw 'Linked directories are not supported by this installer.' }
        }
        $cursor = [IO.Path]::GetDirectoryName($cursor)
    }
    return $full
}
function Test-Package {
    $hashes = Get-Content -LiteralPath (Join-Path $PackageRoot 'Checksums.json') -Raw | ConvertFrom-Json
    foreach ($property in $hashes.PSObject.Properties) {
        $file = Assert-ChildPath $PackageRoot (Join-Path $PackageRoot $property.Name)
        if (-not (Test-Path -LiteralPath $file -PathType Leaf)) { throw "Missing package file: $($property.Name)" }
        $sha=[Security.Cryptography.SHA256]::Create()
        try { $digest=[BitConverter]::ToString($sha.ComputeHash([IO.File]::ReadAllBytes($file))).Replace('-','') } finally { $sha.Dispose() }
        if ($digest -ine $property.Value) { throw "Package integrity check failed: $($property.Name). Extract the complete ZIP again." }
    }
    $package = Get-Content -LiteralPath (Join-Path $PackageRoot 'Package.json') -Raw | ConvertFrom-Json
    if ($package.entries.Count -ne 4 -or @($package.entries.key | Sort-Object -Unique).Count -ne 4) { throw 'Portfolio roster is incomplete or duplicated.' }
    if (@($package.entries | Where-Object { $_.key -in $package.orb_keys -and [double]$_.inputs.InpRewardRisk -ne 0.5 }).Count -ne 0) { throw 'An ORB target is not 0.5R.' }
    foreach ($entry in $package.entries) {
        [void](Assert-ChildPath $PackageRoot (Join-Path $PackageRoot $entry.expert))
        [void](Assert-ChildPath $PackageRoot (Join-Path $PackageRoot $entry.settings))
    }
    if (@($package.entries.magic | Sort-Object -Unique).Count -ne 4) { throw 'Duplicate portfolio magic numbers.' }
    return $package
}
function Assert-Risk([string]$Mode, [double]$Amount) {
    if ($Mode -notin @('PERCENT', 'FIXED_USD') -or [double]::IsNaN($Amount) -or [double]::IsInfinity($Amount) -or $Amount -le 0) { throw 'Select a positive fixed-USD amount or percentage.' }
    if ($Mode -eq 'PERCENT' -and $Amount -gt 10) { throw 'This package supports percentages greater than 0 and no higher than 10% per trade.' }
}
function Assert-RunningTerminal([object]$Candidate) {
    if (-not $Candidate.Running -or -not $Candidate.DataRoot) { throw 'Open a normal MT5 terminal and log into the desired account first. Portable/tester terminals are not supported.' }
    $processes = @(Get-CimInstance Win32_Process | Where-Object { $_.ExecutablePath -ieq $Candidate.Path -and $_.Name -match '^terminal(64)?\.exe$' })
    if ($processes.Count -ne 1) { throw 'The chosen terminal must have exactly one running process.' }
    if ([string]$processes[0].CommandLine -match '(?i)(?:^|\s)[/-](portable|tester|config)(?:[:=\s"]|$)') { throw 'Portable, custom-config and tester terminals are not supported. Open the normal MT5 terminal.' }
    $normalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    [void](Assert-ChildPath $normalRoot $Candidate.DataRoot)
}
function Invoke-AccountProbe([string]$Terminal) {
    $uv = Get-Command uv.exe -ErrorAction SilentlyContinue
    $python = Get-Command python.exe -ErrorAction SilentlyContinue
    $previousPreference = $ErrorActionPreference
    $ErrorActionPreference = 'Continue'
    try {
        if ($uv) {
            $lines = @(& $uv.Source run --no-project --python 3.12 --with MetaTrader5 python (Join-Path $PackageRoot 'Probe-MT5.py') --terminal $Terminal 2>&1)
        } elseif ($python) {
            $lines = @(& $python.Source (Join-Path $PackageRoot 'Probe-MT5.py') --terminal $Terminal 2>&1)
        } else { throw 'Install uv, or Python 3 with the MetaTrader5 package, then run this BAT again.' }
        $code = $LASTEXITCODE
    } finally { $ErrorActionPreference = $previousPreference }
    # uv dependency messages may precede the single JSON response.
    $text = $lines -join "`n"
    $start = $text.IndexOf('{')
    if ($code -ne 0 -or $start -lt 0) { throw "MT5 account detection failed. Check the running terminal/login and the Python MetaTrader5 dependency.`n$text" }
    $probe = $text.Substring($start) | ConvertFrom-Json
    if (-not $probe.ok) { throw 'Unable to read the active MT5 account.' }
    return $probe
}
function Assert-Account([object]$Probe, [object]$Candidate, [string]$Mode) {
    if (-not $Probe.terminal.connected -or [long]$Probe.account.login -le 0) { throw 'The selected MT5 account is not connected and logged in.' }
    if ([IO.Path]::GetFullPath($Probe.terminal.path).TrimEnd('\') -ine [IO.Path]::GetDirectoryName([IO.Path]::GetFullPath($Candidate.Path))) { throw 'The API returned a different terminal installation.' }
    if ([IO.Path]::GetFullPath($Probe.terminal.data_path).TrimEnd('\') -ine [IO.Path]::GetFullPath($Candidate.DataRoot).TrimEnd('\')) { throw 'The API returned a different MT5 data directory.' }
    if ([int]$Probe.account.margin_mode -ne 2) { throw 'These selected EAs require a hedging account, not a netting account.' }
    if (-not $Probe.account.trade_allowed) { throw 'Trading is not allowed on this account. Check investor/read-only login.' }
    if ($Mode -eq 'FIXED_USD' -and (([string]$Probe.account.currency) -cnotmatch '^[A-Z]{3}$' -or $Probe.account.currency -in @('USC','EUC','GBC'))) { throw 'Fixed USD cannot infer non-standard/cent currencies; select percentage risk.' }
    foreach ($name in @('balance', 'equity')) {
        $amount = [double]$Probe.account.$name
        if ([double]::IsNaN($amount) -or [double]::IsInfinity($amount) -or $amount -le 0) { throw "Account $name must be positive and finite." }
    }
    if ([string]$Probe.account.server -match '[\r\n\t=<>]' -or -not $Probe.account.server) { throw 'Unsupported account server identifier.' }
}
function Get-Portfolio([object]$Package, [object]$Probe) {
    $aliases = @{ USDJPY = @('USDJPY'); USTEC = @('USTEC', 'US100', 'NAS100', 'UT100', 'NDX100', 'NASDAQ', 'NQ100', 'NASDAQ100'); XAUUSD = @('XAUUSD', 'GOLD') }
    $mapping = @{}
    foreach ($canonical in @('USDJPY', 'USTEC', 'XAUUSD')) {
        $symbol = Find-BrokerSymbol @($Probe.symbols | Where-Object { [int]$_.trade_mode -eq 4 }) $aliases[$canonical]
        if (-not $symbol -or [string]$symbol.name -match '[\r\n\t=<>]') { throw "No fully tradable CFD symbol was found for $canonical. No partial portfolio will be installed." }
        $mapping[$canonical] = [string]$symbol.name
    }
    foreach ($entry in $Package.entries) {
        [pscustomobject]@{ Key=$entry.key; Label=$entry.label; BrokerSymbol=$mapping[$entry.canonical]; Period=[int]$entry.period; Magic=[long]$entry.magic; Hourly=[bool]$entry.hourly; Expert=[IO.Path]::GetFileName($entry.expert); ExpertFullPath=(Join-Path $PackageRoot $entry.expert); SetFullPath=(Join-Path $PackageRoot $entry.settings) }
    }
}
function Get-EffectiveInputs([object]$Item) {
    $inputs = Read-SetInputs $Item.SetFullPath
    $cash = $RiskMode -eq 'FIXED_USD'
    $inputs['InpRiskPercent'] = '0.5' # Native calibration; selected allocation is separate.
    $inputs['InpPortfolioPercent'] = if ($cash) { '0.5' } else { $RiskValue.ToString('G17', [Globalization.CultureInfo]::InvariantCulture) }
    $inputs['InpAdaptivePortfolioControls'] = 'false'
    $inputs['InpPortfolioRiskMode'] = if ($cash) { '1' } else { '0' }
    $inputs['InpPortfolioFixedUSD'] = if ($cash) { $RiskValue.ToString('G17', [Globalization.CultureInfo]::InvariantCulture) } else { '50.0' }
    $inputs['InpPortfolioExpectedLogin'] = [string]$ActiveLogin
    $inputs['InpPortfolioExpectedServer'] = [string]$ActiveServer
    $inputs['InpPortfolioExpectedSymbol'] = [string]$Item.BrokerSymbol
    $inputs['InpPortfolioInstallNonce'] = [string]$InstallNonce
    if ($Item.Key -eq 'nasdaq-5m-candle-momentum') { $inputs['InpRequireDIAgreement']=if ($NasdaqDIFilter -eq 'OFF') { 'false' } else { 'true' } ; Set-CalyxNasdaqVersion $inputs $NasdaqStopVersion }
    if ($Item.Key -eq 'usdjpy-london-open-momentum') { $inputs['InpRequireDIAgreement']=if ($UsdJpyDIFilter -eq 'OFF') { 'false' } else { 'true' } }
    if ($Item.Hourly) {
        $inputs['InpSizingMode'] = if ($cash) { '2' } else { '1' }
        $inputs['InpFixedRiskMoney'] = if ($cash) { $inputs['InpPortfolioFixedUSD'] } else { '100.0' }
        $inputs['InpAllowRealAccount'] = 'true'
    }
    return $inputs
}
function Assert-ChartInputs([string]$Path, [object[]]$Items) {
    Test-ManagedProfile $Path $Items 'Chart audit'
    for ($index=0; $index -lt $Items.Count; $index++) {
        $text = Get-Content -LiteralPath (Join-Path $Path ('chart{0:D2}.chr' -f ($index+1))) -Raw
        $inputs = Get-EffectiveInputs $Items[$index]
        foreach ($key in $inputs.Keys) {
            if (-not ($text -match ('(?m)^' + [regex]::Escape("$key=$($inputs[$key])") + '\r?$'))) { throw "Risk/settings verification failed for $($Items[$index].Label): $key" }
        }
    }
}
function Get-PreviousProfile([string]$DataRoot) {
    $config = Join-Path $DataRoot 'config\common.ini'
    if (Test-Path -LiteralPath $config) {
        $section = ''
        foreach ($line in Get-Content -LiteralPath $config) {
            if ($line -match '^\[(.+)\]') { $section=$matches[1] }
            if ($section -ieq 'Charts' -and $line -match '^ProfileLast=(.+)$') {
                $name=$matches[1].Trim()
                if ($name -notmatch '[\\/:<>"\r\n]' -and $name -notin @('.', '..') -and (Test-Path -LiteralPath (Join-Path $DataRoot "MQL5\Profiles\Charts\$name"))) { return $name }
            }
        }
    }
    return 'Default'
}
function Start-Profile([string]$Terminal, [string]$Name) {
    if ($Name -match '["\r\n]') { throw 'Invalid profile name.' }
    [void](Start-Process -FilePath $Terminal -ArgumentList ('/profile:"{0}"' -f $Name) -WindowStyle Hidden -PassThru)
}
function Test-Loaded([string]$CommonFiles, [object[]]$Items) {
    $ready = 0
    foreach ($item in $Items) {
        $marker = Join-Path $CommonFiles ("CalyxCurrent14ORB05-$($item.Magic).tsv")
        if (-not (Test-Path -LiteralPath $marker)) { continue }
        try {
            $parts = (Get-Content -LiteralPath $marker -Raw).Trim() -split "`t"
            $now=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
            $mode=if ($RiskMode -eq 'FIXED_USD') { '1' } else { '0' }
            $cash=if ($RiskMode -eq 'FIXED_USD') { $RiskValue } else { 50.0 }
            if ($parts.Count -eq 8 -and [Math]::Abs($now-[long]$parts[0]) -le 120 -and $parts[1] -ceq [string]$ActiveLogin -and $parts[2] -ceq $ActiveServer -and $parts[3] -ceq $item.BrokerSymbol -and $parts[4] -ceq [string]$item.Magic -and $parts[5] -ceq $InstallNonce -and $parts[6] -eq $mode -and [Math]::Abs([double]::Parse($parts[7],[Globalization.CultureInfo]::InvariantCulture)-$cash) -lt 0.00000001) { $ready++ }
        } catch { }
    }
    return $ready -eq 4
}

function Main {
    $package = Test-Package
    . (Join-Path $PackageRoot 'Installer-Helpers.ps1')
    # A failure must unwind the transaction instead of terminating from a helper.
    function Stop-WithMessage([string]$Message) { throw $Message }
    $ProfileName = [string]$package.profile
    $ExpertFolderName = $ProfileName
    if ($ValidateOnly) {
        if ($RiskMode) { Assert-Risk $RiskMode $RiskValue }
        Write-Host 'Validated all selected compiled EAs, presets and installer files. No MT5/API/account accessed.' -ForegroundColor Green
        return
    }
    if (-not $RiskMode) {
        Write-Host 'CALYX - P4 PORTFOLIO (NO GUARD)' -ForegroundColor Green
        Write-Host '1 = fixed USD per trade; 2 = dynamic percentage per trade'
        $choice=Read-Host 'Risk mode [2]'
        if (-not $choice) { $choice='2' }
        if ($choice -notin @('1','2')) { throw 'Choose 1 or 2.' }
        $script:RiskMode=if ($choice -eq '1') { 'FIXED_USD' } else { 'PERCENT' }
    }
    if ($RiskValue -eq 0) {
        $question=if ($RiskMode -eq 'FIXED_USD') { 'USD per trade (for example 50)' } else { 'Percentage per trade [0.5]' }
        $answer=Read-Host $question
        if (-not $answer -and $RiskMode -eq 'PERCENT') { $answer='0.5' }
        $parsed=0.0
        if (-not [double]::TryParse($answer, [Globalization.NumberStyles]::Float, [Globalization.CultureInfo]::InvariantCulture, [ref]$parsed)) { throw 'Enter a number using a decimal point.' }
        $script:RiskValue=$parsed
    }
    Assert-Risk $RiskMode $RiskValue
    Write-Host 'PER TRADE / PER EA, not a portfolio cap. Broker minimum/rounding, gaps and costs can exceed the target.' -ForegroundColor Yellow
    Write-Host 'NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades.' -ForegroundColor Yellow
    $NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion $false
    foreach ($parameter in @('NasdaqDIFilter','UsdJpyDIFilter')) {
        if (-not (Get-Variable -Name $parameter -ValueOnly)) {
            $label=if ($parameter -eq 'NasdaqDIFilter') {'Nasdaq 5M'} else {'USDJPY London'}
            $answer=(Read-Host "$label DI filter ON or OFF (P4 tested OFF) [OFF]").Trim().ToUpperInvariant(); if (-not $answer) { $answer='OFF' }
            if ($answer -notin @('ON','OFF')) { throw 'Choose ON or OFF.' }; Set-Variable -Scope Script -Name $parameter -Value $answer
        }
    }
    Write-Host 'P4 was tested with the Nasdaq DI filter OFF.' -ForegroundColor Yellow
    $candidates=@(Get-Mt5Candidates | Where-Object { $_.Running })
    if ($candidates.Count -eq 0) { throw 'Open your normal MT5 terminal and log into the target account first.' }
    if ($TargetTerminal -and -not @($candidates | Where-Object { [IO.Path]::GetFullPath($_.Path) -ieq [IO.Path]::GetFullPath($TargetTerminal) }).Count) { throw 'The requested target terminal is not running.' }
    $selected=Select-Mt5Candidate $candidates
    Assert-RunningTerminal $selected
    $probe=Invoke-AccountProbe $selected.Path
    Assert-Account $probe $selected $RiskMode
    $portfolio=@(Get-Portfolio $package $probe)
    $ActiveLogin=[string]$probe.account.login
    $ActiveServer=[string]$probe.account.server
    $InstallNonce=[guid]::NewGuid().ToString('N')
    Write-Host ("Active account: {0} / {1} / {2}" -f $ActiveLogin,$ActiveServer,$probe.account.currency) -ForegroundColor Cyan
    foreach ($item in $portfolio) { Write-Host ("  {0}: {1}, {2} minutes" -f $item.Label,$item.BrokerSymbol,$item.Period) }
    Write-Host ("Chosen risk: {0} {1} per trade. Nasdaq DI=$NasdaqDIFilter; USDJPY DI=$UsdJpyDIFilter." -f $RiskValue,$RiskMode)
    Write-Host ("A separate 4-chart profile will replace current chart management, not delete it. {0} open position(s) will NOT be closed. EAs excluded from this profile will stop managing their trades." -f $probe.account.open_positions) -ForegroundColor Yellow
    Write-Host 'MT5 will restart once. Algo Trading preferences stay unchanged; profile-change protection may switch it OFF. Check the toolbar afterwards.' -ForegroundColor Yellow
    if ($PreflightOnly) { Write-Host 'Preflight complete; no terminal restart or MT5 data-folder writes. Symbol inspection may subscribe Market Watch symbols.'; return }
    if (-not $Yes -and (Read-Host 'Apply these selected EAs to this account? [y/N]') -notin @('y','Y','yes','YES')) { Write-Host 'Cancelled. No portfolio installed.'; return }
    Assert-RunningTerminal $selected
    $latest=Invoke-AccountProbe $selected.Path
    Assert-Account $latest $selected $RiskMode
    if ([string]$latest.account.login -cne $ActiveLogin -or [string]$latest.account.server -cne $ActiveServer) { throw 'The account changed during setup. Nothing installed; run again.' }
    $dataRoot=[IO.Path]::GetFullPath($selected.DataRoot)
    $stage=Assert-ChildPath $dataRoot (Join-Path $dataRoot "MQL5\Profiles\CalyxP4Setup\$InstallNonce")
    [void](New-Item -ItemType Directory -Path $stage)
    $targets=@(
        @{Name='Experts'; Path=(Join-Path $dataRoot "MQL5\Experts\$ProfileName")},
        @{Name='Settings'; Path=(Join-Path $dataRoot "MQL5\Profiles\Tester\$ProfileName")},
        @{Name='Charts'; Path=(Join-Path $dataRoot "MQL5\Profiles\Charts\$ProfileName")}
    )
    foreach ($target in $targets) {
        $target.Path=Assert-ChildPath $dataRoot $target.Path
        [void](New-Item -ItemType Directory -Path (Join-Path $stage $target.Name))
    }
    $previousProfile=Get-PreviousProfile $dataRoot
    for ($index=0; $index -lt $portfolio.Count; $index++) {
        $item=$portfolio[$index]
        Copy-Item -LiteralPath $item.ExpertFullPath -Destination (Join-Path $stage "Experts\$($item.Expert)")
        $inputs=Get-EffectiveInputs $item
        $setText=@($inputs.Keys | ForEach-Object { "$_=$($inputs[$_])" }) -join "`r`n"
        [IO.File]::WriteAllText((Join-Path $stage "Settings\$($item.Key).set"), $setText+"`r`n", [Text.Encoding]::Unicode)
        $chart=New-ChartText $item $item.BrokerSymbol ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds()+$index) $index
        [IO.File]::WriteAllText((Join-Path $stage ('Charts\chart{0:D2}.chr' -f ($index+1))), $chart, [Text.Encoding]::Unicode)
    }
    [IO.File]::WriteAllText((Join-Path $stage 'Charts\order.wnd'), ((1..$portfolio.Count | ForEach-Object { 'chart{0:D2}.chr' -f $_ }) -join "`r`n")+"`r`n", [Text.Encoding]::Unicode)
    Assert-ChartInputs (Join-Path $stage 'Charts') $portfolio
    $moved=@(); $installed=@(); $closed=$false
    try {
        Close-TargetTerminal $selected.Path
        $closed=$true
        foreach ($target in $targets) {
            if (Test-Path -LiteralPath $target.Path) {
                $backup=Join-Path $stage ("Backup-"+$target.Name)
                [void](Assert-ChildPath $dataRoot $backup)
                Move-Item -LiteralPath $target.Path -Destination $backup
                $moved+=$target
            }
            [void](New-Item -ItemType Directory -Path ([IO.Path]::GetDirectoryName($target.Path)) -Force)
            Move-Item -LiteralPath (Join-Path $stage $target.Name) -Destination $target.Path
            $installed+=$target
        }
        Assert-ChartInputs $targets[2].Path $portfolio
        $receipt=@{Version=$package.version; Account=$ActiveLogin; Server=$ActiveServer; RiskMode=$RiskMode; RiskValue=$RiskValue; NasdaqDI=$NasdaqDIFilter; UsdJpyDI=$UsdJpyDIFilter; Profile=$ProfileName; PreviousProfile=$previousProfile; CreatedUtc=[DateTime]::UtcNow.ToString('o'); Nonce=$InstallNonce; Entries=$portfolio; Status='Awaiting initialization'; Backups=$stage}
        $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $stage 'Receipt.json') -Encoding UTF8
        Start-Profile $selected.Path $ProfileName
        $commonFiles=Join-Path $probe.terminal.commondata_path 'Files'
        $deadline=[DateTime]::UtcNow.AddSeconds(120)
        do { Start-Sleep -Milliseconds 1000; $loaded=Test-Loaded $commonFiles $portfolio } while (-not $loaded -and [DateTime]::UtcNow -lt $deadline)
        if (-not $loaded) { throw 'All selected EA initialization confirmations were not received. Check MT5 Experts/Journal for missing market history or EA load errors.' }
        $after=Invoke-AccountProbe $selected.Path
        Assert-Account $after $selected $RiskMode
        if ([string]$after.account.login -cne $ActiveLogin -or [string]$after.account.server -cne $ActiveServer) { throw 'MT5 restarted on a different account. The account-bound EAs will not trade it.' }
        $receipt.Status='All selected initialized'; $receipt | ConvertTo-Json -Depth 8 | Set-Content -LiteralPath (Join-Path $stage 'Receipt.json') -Encoding UTF8
        Write-Host 'SUCCESS: all selected EAs initialized on the selected account. Check Algo Trading is ON if you want live trading.' -ForegroundColor Green
        Write-Host "Backup/settings receipt: $stage"
    } catch {
        $failure=$_.Exception.Message
        if ($closed) {
            try {
                Close-TargetTerminal $selected.Path
                foreach ($target in $installed) {
                    [void](Assert-ChildPath $dataRoot $target.Path)
                    if (Test-Path -LiteralPath $target.Path) { Move-Item -LiteralPath $target.Path -Destination (Join-Path $stage ('Failed-'+$target.Name)) }
                }
                foreach ($target in $moved) { Move-Item -LiteralPath (Join-Path $stage ('Backup-'+$target.Name)) -Destination $target.Path }
                Start-Profile $selected.Path $previousProfile
                Write-Host 'Previous profile/files restored. No positions were closed; trades could have occurred while the new profile was running.' -ForegroundColor Yellow
            } catch { Write-Host "Automatic recovery could not finish. Files are recoverable in $stage. Restore the previous profile in MT5; do not run duplicate EAs." -ForegroundColor Red }
        }
        throw $failure
    }
}
try { Main; exit 0 } catch { Write-Host $_.Exception.Message -ForegroundColor Red; exit 1 }
