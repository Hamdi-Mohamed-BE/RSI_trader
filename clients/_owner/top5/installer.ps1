$ErrorActionPreference = 'Stop'
Set-StrictMode -Version Latest
$Package = [Text.Encoding]::UTF8.GetString([Convert]::FromBase64String('__MANIFEST_B64__')) | ConvertFrom-Json
$Bundle = Split-Path -Parent $env:CALYX_BUNDLE_FILE
$Unicode = [Text.Encoding]::Unicode
__CHART_FUNCTION__

function File-Hash([string]$Path) {
    $algorithm = [Security.Cryptography.SHA256]::Create()
    $stream = [IO.File]::OpenRead($Path)
    try { return ([BitConverter]::ToString($algorithm.ComputeHash($stream))).Replace('-','').ToLowerInvariant() }
    finally { $stream.Dispose(); $algorithm.Dispose() }
}

function Check-Bundle {
    foreach ($ea in $Package.entries) {
        $p = Join-Path $Bundle $ea.expert
        if (!(Test-Path -LiteralPath $p -PathType Leaf)) { throw "Missing compiled bot: $($ea.expert). Extract all seven files together." }
        if ((File-Hash $p) -ine $ea.ex5_sha256) { throw "File verification failed: $($ea.expert). Ask the owner for a fresh package." }
    }
}
function Read-Choice([string]$Prompt, [int]$Count) {
    $answer = Read-Host $Prompt
    $number = 0
    if (![int]::TryParse($answer, [ref]$number) -or $number -lt 1 -or $number -gt $Count) { throw 'Invalid selection. Nothing has been installed.' }
    return $number - 1
}
function Safe-Line([string]$Value, [string]$Label) {
    if ([string]::IsNullOrWhiteSpace($Value) -or $Value -match '[\r\n<>="\\/]') { throw "Invalid $Label" }
    return $Value.Trim()
}
function Test-Running([string]$Exe) {
    foreach ($p in @(Get-Process -Name terminal64 -ErrorAction SilentlyContinue)) {
        try { $processPath = $p.Path } catch { return $true }
        if (!$processPath) { return $true }
        if ($processPath -ieq $Exe) { return $true }
    }
    return $false
}
function Ini-Value([string]$Path, [string]$Section, [string]$Key) {
    if (!(Test-Path -LiteralPath $Path)) { return '' }
    $inside=$false
    foreach ($line in [IO.File]::ReadAllLines($Path)) {
        if ($line -match '^\s*\[([^\]]+)\]') { $inside=$Matches[1] -ieq $Section; continue }
        if ($inside -and $line -match ('^\s*'+[regex]::Escape($Key)+'\s*=(.*)$')) { return $Matches[1].Trim() }
    }
    return ''
}
__SYMBOL_MAPPING_FUNCTIONS__
__AUTO_SETUP_FUNCTIONS__
function Write-Profile([string]$DataDir, [string]$SourceProfile, [string]$ProfileName, [long]$Login, [string]$Server, [hashtable]$Symbols, [int]$RiskMode, [double]$RiskValue) {
    $charts = Join-Path $DataDir 'MQL5\Profiles\Charts'
    $sourceDir = Join-Path $charts $SourceProfile
    $profileDir = Join-Path $charts $ProfileName
    if (Test-Path -LiteralPath $profileDir) { throw 'Destination already exists; restart installer to create a fresh profile.' }
    $oldMagic = @($Package.entries | ForEach-Object { [string]$_.original_magic })
    $clientMagic = @($Package.entries | ForEach-Object { [string]$_.inputs.InpMagic })
    $sourceFiles = @(Get-ChildItem -LiteralPath $sourceDir -Filter '*.chr' -File)
    foreach ($file in $sourceFiles) {
        $content = [IO.File]::ReadAllText($file.FullName)
        foreach ($magic in $oldMagic) {
            if ($content -match "(?m)^InpMagic=$magic(?:\|.*)?\r?`$") { throw 'An original version of one of these bots is already attached. Review/remove that chart first to prevent duplicate trading.' }
        }
    }
    $null = New-Item -ItemType Directory -Path $profileDir
    # Copy all chart/profile data, leaving the original profile intact as the backup.
    foreach ($file in @(Get-ChildItem -LiteralPath $sourceDir -File)) { Copy-Item -LiteralPath $file.FullName -Destination $profileDir }
    $index = 1
    foreach ($file in @(Get-ChildItem -LiteralPath $profileDir -Filter '*.chr' -File)) {
        $content = [IO.File]::ReadAllText($file.FullName)
        $ours = $false
        foreach ($magic in $clientMagic) { if ($content -match "(?m)^InpMagic=$magic(?:\|.*)?\r?`$") { $ours = $true } }
        if ($ours) { Remove-Item -LiteralPath $file.FullName } # Only duplicates in the NEW inactive profile.
    }
    foreach ($ea in $Package.entries) {
        while (Test-Path -LiteralPath (Join-Path $profileDir ('chart{0:D2}.chr' -f $index))) { $index++ }
        $inputs = [ordered]@{}
        foreach ($prop in $ea.inputs.PSObject.Properties) { $inputs[$prop.Name] = [string]$prop.Value }
        $inputs['ClientRiskMode'] = [string]$RiskMode
        $inputs['ClientRiskValue'] = $RiskValue.ToString('0.########', [Globalization.CultureInfo]::InvariantCulture)
        $inputs['ClientExpectedLogin'] = [string]$Login
        $inputs['ClientExpectedServer'] = $Server
        $inputs['ClientExpectedSymbol'] = $Symbols[$ea.symbol]
        $name = [IO.Path]::GetFileNameWithoutExtension($ea.expert)
        $minutes = switch ($ea.period) { 'M1' {1} 'M5' {5} 'M15' {15} 'M30' {30} 'H1' {60} 'H4' {240} 'D1' {1440} default {throw 'Unsupported timeframe'} }
        $chart = New-ChartText $Symbols[$ea.symbol] $minutes $name ("Experts\CalyxTop5\" + $ea.expert) $inputs
        # The user explicitly confirms attachment. Global AutoTrading is NEVER changed.
        $chart = $chart.Replace('expertmode=0','expertmode=1') -replace '(?m)^id=1\r?$', ('id=' + ([DateTimeOffset]::UtcNow.ToUnixTimeMilliseconds() + $index))
        [IO.File]::WriteAllText((Join-Path $profileDir ('chart{0:D2}.chr' -f $index)), $chart, $Unicode)
        $index++
    }
    return $profileDir
}
function Main {
    Check-Bundle
    if ($env:CALYX_VALIDATE_ONLY -eq '1') { Write-Host 'PASS: five EX5 hashes, embedded settings and installer loaded. No MT5 changes.'; return }
    Write-Host "`nCALYX - TOP FIVE CLIENT EDITION" -ForegroundColor Green
    Write-Host "Licence expiry: $($Package.licence.expires_utc) (UTC/broker clock, whichever reaches it first)."
    if ([DateTimeOffset]::UtcNow -ge [DateTimeOffset]::Parse($Package.licence.expires_utc)) { throw 'Package has expired. Ask owner to renew the compiled bots.' }
    Write-Host 'USD HEDGING accounts only. This is real trading software, not a paper simulator.' -ForegroundColor Yellow
    Write-Host 'Risk is PER TRADE, PER BOT, not a portfolio cap. Five bots can stack risk; fees/gaps can exceed the planned stop.'
    $terminalRoot = Join-Path $env:APPDATA 'MetaQuotes\Terminal'
    $candidates = @()
    if (Test-Path -LiteralPath $terminalRoot) {
        foreach ($dir in @(Get-ChildItem -LiteralPath $terminalRoot -Directory)) {
            $originFile = Join-Path $dir.FullName 'origin.txt'
            if (!(Test-Path -LiteralPath $originFile)) { continue }
            $origin = [IO.File]::ReadAllText($originFile).Trim()
            $exe = Join-Path $origin 'terminal64.exe'
            if (!(Test-Path -LiteralPath $exe) -or !(Test-Path -LiteralPath (Join-Path $dir.FullName 'MQL5'))) { continue }
            if (($origin + ' ' + $dir.FullName) -match '(?i)ava|backtest|research|tester|MT5-DMC') { continue }
            $candidates += [pscustomobject]@{ Data=$dir.FullName; Exe=$exe; Running=(Test-Running $exe) }
        }
    }
    if ($candidates.Count -eq 0) { throw 'No supported standard MT5 installation found. Open MT5 once. Portable/research terminals are not auto-installed.' }
    $target=Get-OnlyActiveTarget $candidates @(Get-Process -Name terminal64 -ErrorAction SilentlyContinue)
    Write-Host 'Enter risk and the exact Gold/Nasdaq symbols from Market Watch. Setup restarts MT5 once; EA management briefly pauses. AutoTrading stays unchanged.'
    Write-Host 'Submitting the final symbol starts setup. If AutoTrading is already on, bots may trade immediately after installation. Symbols are not automatically verified.' -ForegroundColor Yellow
    $mode = Read-Choice 'Risk: 1 = fixed USD per trade; 2 = percent of current BALANCE' 2
    $valueText = Read-Host $(if ($mode -eq 0) {'USD risk per trade (example: 50)'} else {'Balance percent per trade (example: 0.5; maximum 5)'})
    $value = 0.0
    if (![double]::TryParse($valueText,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$value) -or [double]::IsNaN($value) -or [double]::IsInfinity($value) -or $value -le 0 -or ($mode -eq 1 -and $value -gt 5)) { throw 'Invalid risk amount. Use a dot for decimals.' }
    $symbols=@{}
    $symbols['XAUUSD']=Safe-Line (Read-Host 'Exact Gold / USD symbol (examples: XAUUSD, XAUUSDr, GOLD)') 'Gold symbol'
    $symbols['USTEC']=Safe-Line (Read-Host 'Exact Nasdaq 100 CFD symbol (examples: USTECr, US100, NAS100)') 'Nasdaq symbol'
    if($symbols['XAUUSD'] -ieq $symbols['USTEC']){throw 'Gold and Nasdaq must have different symbols. No terminal changed.'}
    $restoreNeeded=$false
    try {
    Close-SelectedTerminal $target.Exe
    $restoreNeeded=$true
    $context=Read-SavedContext $target
    $loginId=$context.Login;$server=$context.Server;$source=$context.Profile
    if ($Package.licence.bound_login -gt 0 -and $loginId -ne $Package.licence.bound_login) { throw 'This package is licensed to a different account.' }
    if ($Package.licence.bound_server -and $server -cne $Package.licence.bound_server) { throw 'Broker server does not match licence.' }
    Write-Host 'Using your entered symbols. Account/server and current profile were read from saved MT5 settings. USD hedging compatibility is enforced by the EAs on startup.'
    $saved=Read-SavedContext $target
    if($saved.Login -ne $loginId -or $saved.Server -cne $server -or $saved.Profile -cne $source){throw 'Account/profile changed during setup. No client profile will be activated.'}
    Check-Bundle
    $profileName = 'Calyx Top5 ' + (Get-Date -Format 'yyyyMMdd-HHmmss')
    $profileDir = Write-Profile $target.Data $source $profileName $loginId $server $symbols $mode $value
    $expertDir = Join-Path $target.Data 'MQL5\Experts\CalyxTop5'
    $null = New-Item -ItemType Directory -Path $expertDir -Force
    # Keep previous binaries for recovery on renewals; nothing is deleted from the old profile.
    $backup = Join-Path $target.Data ('CalyxBackups\' + $profileName)
    foreach ($ea in $Package.entries) {
        $destination = Join-Path $expertDir $ea.expert
        if (Test-Path -LiteralPath $destination) { $null = New-Item -ItemType Directory -Path $backup -Force; Copy-Item -LiteralPath $destination -Destination $backup }
        Copy-Item -LiteralPath (Join-Path $Bundle $ea.expert) -Destination $destination
        if ((File-Hash $destination) -ine $ea.ex5_sha256) { throw 'Installed binary verification failed. Do not enable trading; contact owner.' }
    }
    Write-Host "Installed. Original profile retained: $source. New profile: $profileName" -ForegroundColor Green
    Write-Host 'At expiry NEW entries stop, own pending entries are cancelled; open positions keep SL/TP/trailing/time management while MT5 stays connected.'
    Write-Host 'To stop trading manually, disable Algo Trading. To roll back charts, select the original profile. Renewals need replacement EX5s from the owner.'
    Start-SelectedTerminal $target.Exe ('/profile:"' + $profileName + '"')
    $restoreNeeded=$false
    Write-Host 'Check all five charts and the Experts log. If Algo Trading is OFF, enable it yourself only after checking account, symbols and risk.'
    } finally {
        if($restoreNeeded){
            # Restore normal startup, never force-kill. Do not mask the original error.
            try {
                if(Test-Running $target.Exe){Close-SelectedTerminal $target.Exe}
                Start-SelectedTerminal $target.Exe
                Write-Host 'Original MT5 session restarted; client setup did not finish.' -ForegroundColor Yellow
            } catch { Write-Warning 'MT5 could not be restored automatically. Reopen it normally; the original profile is retained.' }
        }
    }
}
if ($env:CALYX_LIBRARY_ONLY -ne '1') { Main }
