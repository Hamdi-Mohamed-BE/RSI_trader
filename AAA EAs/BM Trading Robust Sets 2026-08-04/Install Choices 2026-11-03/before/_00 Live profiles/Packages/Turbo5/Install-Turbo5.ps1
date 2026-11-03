[CmdletBinding()]
param(
    [string]$TargetTerminal,
    [double]$AccountSize=0,
    [double]$KnownFloor=-1,
    [ValidateSet('','Y','N')][string]$TrailEquity='',
    [switch]$ValidateOnly,
    [switch]$PreflightOnly
)
# Turbo5 installer (2026-10-27), adapted from Packages/PropReady/Install-Portfolio.ps1: same flat-account / Algo-OFF / typed-confirmation /
# new-profile flow. Installs the 5 Turbo-guarded EAs on an ALREADY RUNNING normal MT5 terminal. Places no orders; Algo Trading stays OFF.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$Package=Join-Path $PSScriptRoot 'package'
. (Join-Path $PSScriptRoot 'Account-Helpers.ps1')

# Import declarations, never execute the ordinary installer.
$tokens=$null;$parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile(
    (Join-Path $PackageRoot '_Auto Deploy\Install-BMTradingPortfolio.ps1'),[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw 'Shared installer parse failure.'}
foreach($helper in @('Stop-WithMessage','Get-Mt5Candidates','Select-Mt5Candidate','Normalize-Symbol',
    'Find-BrokerSymbol','Read-SetInputs','New-ChartText','Test-ManagedProfile','Set-IniValue','Close-TargetTerminal')){
    $definition=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]},$true) | Where-Object Name -eq $helper)
    if($definition.Count -ne 1){throw "Missing/ambiguous helper: $helper"}
    . ([scriptblock]::Create($definition[0].Extent.Text))
}
function Get-EffectiveInputs([object]$Item){return $Item.EffectiveInputs}
function Get-TurboHash([string]$Path){
    $stream=[IO.File]::OpenRead($Path);$hash=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
    finally{$hash.Dispose();$stream.Dispose()}
}
function Assert-TurboPackage {
    $expected=@('nasdaq-5m-candle-momentum','xau-rsi-vwap','gold-overnight-value-area','3-way-gold','ema3')
    if($manifest.entries.Count -ne 5 -or $manifest.news_enabled -or -not $manifest.hedging_required -or $manifest.ea_risk_request_percent -ne 0.75){throw 'Unexpected Turbo5 package policy.'}
    if(@($manifest.entries | Group-Object slug | Where-Object Count -ne 1).Count -or @($manifest.entries | Where-Object slug -notin $expected).Count){throw 'Turbo5 roster changed.'}
    if((Get-TurboHash (Join-Path $PSScriptRoot 'CalyxTurboGuard.mqh')) -ine $manifest.guard_sha){throw 'Guard changed; rebuild package first.'}
    foreach($file in $manifest.files.PSObject.Properties){
        $path=Join-Path $Package $file.Name
        if(-not(Test-Path -LiteralPath $path) -or (Get-TurboHash $path) -ine $file.Value){throw "Missing/altered package file: $($file.Name)"}
    }
    foreach($entry in $manifest.entries){
        $inputs=Read-SetInputs (Join-Path $Package $entry.settings)
        if($inputs['TurboGuardMode'] -ne '1' -or $inputs['TurboExpectedLogin'] -ne '0' -or $inputs['TurboReferenceBalance'] -ne '0' -or $inputs['TurboStartUtcTime'] -ne '0' -or
           $inputs['TurboTesterRewards'] -ne 'false' -or $inputs['InpRiskPercent'] -ne '0.75' -or $inputs['InpAdaptivePortfolioControls'] -ne 'false'){throw 'Distributed settings must be unarmed, guard ON, unchanged strategy inputs.'}
        if($entry.slug -eq 'nasdaq-5m-candle-momentum' -and $inputs['InpRequireDIAgreement'] -ne 'false'){throw 'Nasdaq 5M must have the DI filter OFF.'}
        if(-not(Test-Path -LiteralPath (Join-Path $Package $entry.expert))){throw 'Missing compiled EA.'}
    }
}
$manifest=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'PACKAGE.json') | ConvertFrom-Json
Assert-TurboPackage
Write-Host 'TURBO 5 GUARDED: Nasdaq 5M (DI OFF), XAU RSI VWAP, Gold Overnight Value Area, 3 Way Gold, EMA3 - Turbo $50k reward-account guard.' -ForegroundColor Cyan
Write-Host 'Every entry: risk = min(0.75% of account size, 5% of the room above the trailing floor), cut to fit all limits, lots round DOWN, skipped under 0.05%.'
Write-Host 'Limits: open risk 2%; per symbol 1.5%; daily soft stop 2% (realised loss + open stops); keep 0.25% above the floor; no new entries once the day is up 0.75%.' -ForegroundColor Yellow
if($ValidateOnly){Write-Host 'PASS: 5 integrity-checked Turbo-guarded EAs; settings unarmed; Nasdaq DI OFF. No account accessed.';exit 0}

$candidates=@(Get-Mt5Candidates | Where-Object {$_.Running -and $_.Path -notmatch '(?i)\\(_Backtests|Tester|temp)\\'})
if($candidates.Count -eq 0){throw 'Open your intended normal MT5 terminal and log into your Turbo account first.'}
if($TargetTerminal -and -not @($candidates | Where-Object Path -eq $TargetTerminal).Count){throw 'Target must be an already running normal MT5 terminal.'}
$selected=Select-Mt5Candidate $candidates
$terminalPath=[IO.Path]::GetFullPath($selected.Path)
$python=(Get-Command python.exe -ErrorAction Stop).Source
$probeText=(& $python (Join-Path $PSScriptRoot 'probe_account.py') --terminal $terminalPath) -join "`n"
if($LASTEXITCODE -ne 0){throw 'Account preflight failed; nothing installed.'}
$probe=$probeText | ConvertFrom-Json
Assert-TurboAccount $probe
$dataRoot=[IO.Path]::GetFullPath([string]$probe.terminal.data_path)
if(-not(Test-Path -LiteralPath (Join-Path $dataRoot 'MQL5'))){throw 'Invalid terminal data folder.'}
$login=[string]$probe.account.login;$server=[string]$probe.account.server;$currency=[string]$probe.account.currency
$balance=[double]$probe.account.balance;$equity=[double]$probe.account.equity
Write-Host "Broker: $($probe.account.company) / login $login / $server / balance $balance $currency / leverage 1:$($probe.account.leverage)"

$inv=[Globalization.CultureInfo]::InvariantCulture
if($AccountSize -le 0){
    $raw=(Read-Host 'Turbo account size in account currency [50000]').Trim()
    $AccountSize=if($raw){[double]::Parse($raw,$inv)}else{50000}
}
if([double]::IsNaN($AccountSize) -or $AccountSize -le 0){throw 'Invalid account size.'}
$defaultFloor=$balance-0.06*$AccountSize
if($KnownFloor -lt 0){
    Write-Host "Enter the CURRENT max-loss level shown on your Turbo dashboard (the balance/equity level that breaches the account)."
    $raw=(Read-Host ("Max-loss level [{0}] (blank = balance - 6%)" -f $defaultFloor.ToString('0.00',$inv))).Trim()
    $KnownFloor=if($raw){[double]::Parse($raw,$inv)}else{0}
}
if($KnownFloor -ne 0 -and ($KnownFloor -ge $balance -or $KnownFloor -lt $balance-0.06*$AccountSize-1)){throw 'Max-loss level must be below the balance and within 6% of the account size of it.'}
if(-not $TrailEquity){
    $answer=(Read-Host 'Does Turbo trail the max loss on EQUITY (open profit) instead of closed balance? Y/N [N]').Trim().ToUpperInvariant()
    $TrailEquity=if($answer){$answer}else{'N'}
    if($TrailEquity -notin @('Y','N')){throw 'Answer Y or N.'}
}
$serverHasher=[Security.Cryptography.SHA256]::Create()
try{$serverHash=([BitConverter]::ToString($serverHasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($server)))).Replace('-','').Substring(0,16)}finally{$serverHasher.Dispose()}
# Reruns must not reset the retained baseline (the guard rebuilds the trailing floor from deals after start_utc).
$statePath=Join-Path $dataRoot ("MQL5\Files\Calyx-Turbo5-$login-$serverHash.json")
$oldState=if(Test-Path -LiteralPath $statePath){Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json}else{$null}
$reference=Get-TurboReference $probe $oldState $AccountSize $KnownFloor
$floor=if([double]$reference.known_floor -gt 0){[double]$reference.known_floor}else{[double]$reference.reference_balance-0.06*$AccountSize}
if($equity -le $floor+0.0025*$AccountSize+0.0005*$AccountSize){throw "Equity $equity is too close to the max-loss level $floor; the guard would admit nothing. Stop for review."}

$aliasMap=@{XAUUSD=@('XAUUSD','GOLD');USTEC=@('USTEC','US100','NAS100','NDX100','UT100','NASDAQ100','NASUSD','USTECH','USNDX')}
$resolved=@{}
foreach($symbol in $aliasMap.Keys){
    $match=Find-BrokerSymbol @($probe.symbols | Where-Object {[int]$_.trade_mode -eq 4}) $aliasMap[$symbol]
    if(-not $match){throw "No fully tradeable cash symbol for $symbol. Netting/futures substitution is not supported."}
    if($match.volume_min -le 0 -or $match.volume_step -le 0){throw "Invalid volume rules: $($match.name)"}
    $resolved[$symbol]=$match.name
}
$ProfileName='Calyx-Turbo5-'+$login+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')
$ExpertFolderName=$ProfileName
$portfolio=@()
foreach($entry in $manifest.entries){
    $inputs=Read-SetInputs (Join-Path $Package $entry.settings)
    $inputs['TurboExpectedLogin']=$login;$inputs['TurboExpectedServer']=$server;$inputs['TurboExpectedSymbol']=$resolved[$entry.symbol]
    $inputs['TurboExpectedCurrency']=$currency;$inputs['TurboAccountSize']=$AccountSize.ToString('G17',$inv)
    $inputs['TurboReferenceBalance']=([double]$reference.reference_balance).ToString('G17',$inv);$inputs['TurboStartUtcTime']=[string]$reference.start_utc
    $inputs['TurboKnownFloor']=([double]$reference.known_floor).ToString('G17',$inv);$inputs['TurboTrailEquity']=if($TrailEquity -eq 'Y'){'true'}else{'false'}
    $tf=[string]$entry.timeframe
    $minutes=if($tf.StartsWith('H')){60*[int]$tf.Substring(1)}elseif($tf.StartsWith('M')){[int]$tf.Substring(1)}else{throw 'Unsupported timeframe.'}
    $portfolio+=[pscustomobject]@{Label=$entry.label;Expert=$entry.expert;Period=$minutes;BrokerSymbol=$resolved[$entry.symbol];
        ExpertFullPath=(Join-Path $Package $entry.expert);EffectiveInputs=$inputs}
}
Write-Host "Account size $AccountSize; saved reference balance $($reference.reference_balance) $currency; trailing floor now $floor ($(if($TrailEquity -eq 'Y'){'equity'}else{'closed balance'}) trailing, re-based after withdrawals)."
Write-Host ("Per-entry maximum {0}; open risk {1}; per symbol {2}; daily soft stop {3}; profit cap {4}; buffer {5}." -f (0.0075*$AccountSize),(0.02*$AccountSize),(0.015*$AccountSize),(0.02*$AccountSize),(0.0075*$AccountSize),(0.0025*$AccountSize))
Write-Host 'Nasdaq 5M DI filter: OFF. News and hourly EAs: not included. No automatic liquidation. Gaps/slippage/costs can exceed planned stop risk.'
Write-Host 'CONFIRM WITH TURBO: balance vs equity trailing, lock at start balance, floor after payouts, daily-loss basis, EA/news/hedging permissions.' -ForegroundColor Yellow
$portfolio | Select-Object Label,BrokerSymbol,Period | Format-Table -AutoSize
if($PreflightOnly){Write-Host 'Preflight complete. Nothing installed or restarted.';exit 0}
Write-Host 'Use one terminal for this account. Stop other VPS/manual trading before confirming.'
$expected="TURBO5 $login $currency"
if((Read-Host "Type exactly: $expected") -cne $expected){throw 'Confirmation mismatch. Nothing installed.'}
$confirmationText=(& $python (Join-Path $PSScriptRoot 'probe_account.py') --terminal $terminalPath) -join "`n"
if($LASTEXITCODE -ne 0){throw 'Final account check failed; nothing installed.'}
$confirmation=$confirmationText | ConvertFrom-Json
Assert-TurboConfirmation $probe $confirmation
Close-TargetTerminal $terminalPath
$mql=Join-Path $dataRoot 'MQL5'
$experts=Join-Path (Join-Path $mql 'Experts') $ExpertFolderName
$profile=Join-Path (Join-Path $mql 'Profiles\Charts') $ProfileName
$sets=Join-Path (Join-Path $mql 'Profiles\Tester') $ProfileName
foreach($dest in @($experts,$profile,$sets)){
    if(Test-Path -LiteralPath $dest){throw "Refusing to overwrite existing directory: $dest"}
    [void](New-Item -ItemType Directory -Path $dest -Force)
}
$unicode=New-Object System.Text.UnicodeEncoding($false,$true)
for($i=0;$i -lt $portfolio.Count;$i++){
    $item=$portfolio[$i]
    Copy-Item -LiteralPath $item.ExpertFullPath -Destination (Join-Path $experts $item.Expert)
    $setText=(@($item.EffectiveInputs.Keys | ForEach-Object {"$_=$($item.EffectiveInputs[$_])"}) -join "`r`n")+"`r`n"
    [IO.File]::WriteAllText((Join-Path $sets ($item.Expert -replace '\.ex5$','.set')),$setText,[Text.UTF8Encoding]::new($false))
    $chart=New-ChartText $item $item.BrokerSymbol ([DateTime]::UtcNow.Ticks+$i) $i
    [IO.File]::WriteAllText((Join-Path $profile ('chart{0:D2}.chr' -f ($i+1))),$chart.TrimStart(),$unicode)
}
$order=((1..$portfolio.Count | ForEach-Object {'chart{0:D2}.chr' -f $_}) -join "`r`n")+"`r`n"
[IO.File]::WriteAllText((Join-Path $profile 'order.wnd'),$order,$unicode)
Test-ManagedProfile $profile $portfolio 'Turbo5 installed profile'
if(-not(Test-Path -LiteralPath $statePath)){
    [void](New-Item -ItemType Directory -Path (Split-Path -Parent $statePath) -Force)
    [IO.File]::WriteAllText($statePath,($reference | ConvertTo-Json),[Text.UTF8Encoding]::new($false))
}
$commonIni=Join-Path $dataRoot 'config\common.ini'
if(-not(Test-Path -LiteralPath $commonIni)){throw 'Cannot locate common.ini. Files installed, terminal NOT restarted.'}
Copy-Item -LiteralPath $commonIni -Destination ($commonIni+'.turbo5-backup-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
Set-IniValue $commonIni 'Experts' 'Enabled' '0'
Set-IniValue $commonIni 'Experts' 'Account' '1'
Set-IniValue $commonIni 'Charts' 'ProfileLast' $ProfileName
[IO.File]::WriteAllText((Join-Path $profile 'DEPLOYMENT.txt'),
    "Portfolio: Turbo 5 guarded ($($manifest.version))`r`nAccount: $login / $server / $currency`r`nAccount size: $AccountSize; reference: $($reference.reference_balance); start UTC: $($reference.start_utc)`r`nFloor now: $floor; equity trailing: $TrailEquity`r`nNasdaq DI: OFF; Algo Trading: OFF`r`n",[Text.UTF8Encoding]::new($false))
Start-Process -FilePath $terminalPath -ArgumentList ('/profile:"'+$ProfileName+'"') -WindowStyle Hidden
Write-Host "Installed $ProfileName. Review all five charts and inputs; Algo Trading remains OFF."
Write-Host 'Enable Algo Trading yourself only when satisfied. No orders were placed by this installer.'
