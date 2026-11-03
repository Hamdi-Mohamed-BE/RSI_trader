[CmdletBinding()]
param(
    [string]$TargetTerminal,
    [ValidateSet('PERCENT','FIXED_USD')][string]$RiskMode='PERCENT',
    [double]$RiskValue=1.0,
    [ValidateSet('ON','OFF')][string]$UsdJpyDIFilter='ON',
    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='OFF',
    [ValidateSet('Challenge','Verification','Funded')][string]$Phase='Challenge',
    [switch]$Interactive,
    [switch]$ValidateOnly,
    [switch]$PreflightOnly
)
# Best Prop Portfolio 2026-10-20: the Prop Ready nine EAs at 1% (USD 100 on 10k) with the rebuilt 1% guard.
# Works on any MT5 HEDGING account (any broker, currency, balance). Derived from Packages/PropReady/Install-Portfolio.ps1.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..'))
$Package=Join-Path $PSScriptRoot 'package'
. (Join-Path $PSScriptRoot 'Account-Helpers.ps1')

# Import declarations only from the shared installer; never execute it or its news service.
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
function Get-BestPropHash([string]$Path){
    $stream=[IO.File]::OpenRead($Path);$hash=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
    finally{$hash.Dispose();$stream.Dispose()}
}
function Assert-BestPropPackage {
    if($manifest.entries.Count -ne 9 -or $manifest.news_enabled -or $manifest.currency_mode -ne 'ACCOUNT_CURRENCY' -or
       $manifest.risk_cap_fraction -ne 0.01 -or $manifest.total_risk_fraction -ne 0.045 -or $manifest.symbol_risk_fraction -ne 0.03 -or
       -not $manifest.hedging_required){throw 'Unexpected Best Prop package policy.'}
    $expected=@('nasdaq-5m-candle-momentum','usdjpy-london-open-momentum','us100-month-end-flow','xau-rsi-vwap',
        'us100-h1-orb-13utc','us100-orb-new-york-m30','us100-selective-orb-v3','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30')
    if(@($manifest.entries | Group-Object slug | Where-Object Count -ne 1).Count -or
       @($manifest.entries | Where-Object slug -notin $expected).Count){throw 'Best Prop roster changed.'}
    if((Get-BestPropHash (Join-Path $PSScriptRoot 'CalyxFTMOGuard.mqh')) -ine $manifest.guard_sha){throw 'Guard changed; rebuild the package first (python build.py).'}
    foreach($file in $manifest.files.PSObject.Properties){
        $path=Join-Path $Package $file.Name
        if(-not(Test-Path -LiteralPath $path) -or (Get-BestPropHash $path) -ine $file.Value){throw "Missing/altered package file: $($file.Name)"}
    }
    foreach($entry in $manifest.entries){
        $inputs=Read-SetInputs (Join-Path $Package $entry.settings)
        if($inputs['FTMOExpectedLogin'] -ne '0' -or $inputs['FTMOReferenceBalance'] -ne '0' -or $inputs['FTMOStartUtcTime'] -ne '0' -or
           $inputs['InpRiskPercent'] -ne '1.0' -or $inputs['InpAdaptivePortfolioControls'] -ne 'false'){throw 'Distributed settings must be unarmed with InpRiskPercent=1.0.'}
        if($entry.slug -match '-orb-' -and $inputs['InpRewardRisk'] -ne '0.5'){throw 'All five ORBs must retain 0.5R.'}
        if(-not(Test-Path -LiteralPath (Join-Path $Package $entry.expert))){throw 'Missing compiled EA.'}
    }
}
$manifest=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'PACKAGE.json') | ConvertFrom-Json
Assert-BestPropPackage

if($Interactive -and -not $ValidateOnly){
    Write-Host ''
    Write-Host 'BEST PROP PORTFOLIO - nine EAs, 1% risk per trade (capped at 1% of the starting balance).' -ForegroundColor Cyan
    if(-not $PSBoundParameters.ContainsKey('Phase')){
        $answer=(Read-Host 'Phase: 1 = Challenge (stop at +10%), 2 = Verification (stop at +5%), 3 = Funded (no target) [1]').Trim()
        if(-not $answer){$answer='1'}
        $Phase=@{'1'='Challenge';'2'='Verification';'3'='Funded'}[$answer]
        if(-not $Phase){throw 'Phase must be 1, 2 or 3.'}
    }
    if(-not $PSBoundParameters.ContainsKey('RiskValue')){
        $answer=(Read-Host 'Risk per trade, % of current equity, e.g. 0.5 / 1.0 / 2.0 (max 2) [1.0]').Trim()
        if($answer){$RiskValue=[double]::Parse($answer,[Globalization.CultureInfo]::InvariantCulture)}
    }
    if(-not $PSBoundParameters.ContainsKey('NasdaqDIFilter')){
        $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF [OFF]').Trim().ToUpperInvariant()
        if(-not $answer){$answer='OFF'}
        if($answer -notin @('ON','OFF')){throw 'DI choice must be ON or OFF.'}
        $NasdaqDIFilter=$answer
    }
}
if([double]::IsNaN($RiskValue) -or [double]::IsInfinity($RiskValue) -or $RiskValue -le 0 -or ($RiskMode -eq 'PERCENT' -and $RiskValue -gt 10)){throw 'Invalid risk selection.'}
Write-Host 'BEST PROP PORTFOLIO: nine EAs / five ORBs at 0.5R / broker-neutral MT5 hedging profile.' -ForegroundColor Cyan
Write-Host 'Each trade risks the amount you chose (at most 2% of the saved starting balance) and never more than the strategy request; lots round DOWN.' -ForegroundColor Yellow
if($ValidateOnly){
    foreach($entry in $manifest.entries){$null=Get-PropReadyPresetInputs $entry}
    Write-Host 'PASS: 9 integrity-checked guarded EAs (1% cap, 4.5% total, 3% per symbol); ORBs 0.5R; Nasdaq DI default OFF. No account accessed.';exit 0
}

$candidates=@(Get-Mt5Candidates | Where-Object {
    $_.Running -and $_.Path -notmatch '(?i)\\(_Backtests|Tester|temp)\\'
})
if($candidates.Count -eq 0){throw 'Open your intended MT5 terminal and log into the account first.'}
if($TargetTerminal -and -not @($candidates | Where-Object Path -eq $TargetTerminal).Count){throw 'Target must be an already running normal MT5 terminal.'}
$selected=Select-Mt5Candidate $candidates
$terminalPath=[IO.Path]::GetFullPath($selected.Path)
$python=(Get-Command python.exe -ErrorAction Stop).Source
$probeText=(& $python (Join-Path $PSScriptRoot 'probe_account.py') --terminal $terminalPath) -join "`n"
if($LASTEXITCODE -ne 0){throw 'Account preflight failed; nothing installed.'}
$probe=$probeText | ConvertFrom-Json
Assert-PropReadyAccount $probe
$dataRoot=[IO.Path]::GetFullPath([string]$probe.terminal.data_path)
if(-not(Test-Path -LiteralPath (Join-Path $dataRoot 'MQL5'))){throw 'Invalid terminal data folder.'}
$login=[string]$probe.account.login;$server=[string]$probe.account.server;$currency=[string]$probe.account.currency
$serverHasher=[Security.Cryptography.SHA256]::Create()
try{$serverHash=([BitConverter]::ToString($serverHasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($server)))).Replace('-','').Substring(0,16)}finally{$serverHasher.Dispose()}
# The saved baseline is never reset by reinstalling; a new account (login) gets its own baseline.
$statePath=Join-Path $dataRoot ("MQL5\Files\Calyx-BestProp9-$login-$serverHash.json")
$oldState=if(Test-Path -LiteralPath $statePath){Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json}else{$null}
$chosen=Select-PropReadyReference $probe $oldState (-not $ValidateOnly)
$reference=$chosen.reference
$initial=[double]$reference.reference_balance
# 2026-10-30 owner: the per-entry cap is the chosen risk (fixed cash -> % of the saved starting balance), not a fixed 1%.
$capPercent=Resolve-RiskCapPercent $RiskMode $RiskValue $initial
$capText=$capPercent.ToString('G17',[Globalization.CultureInfo]::InvariantCulture)
if([double]$probe.account.equity -lt $initial*0.92){throw 'Account is below the retained 92% entry buffer; stop for review. Reinstallation does not reset losses.'}
$phaseNumber=@{Challenge=1;Verification=2;Funded=3}[$Phase]
$aliasMap=@{XAUUSD=@('XAUUSD','GOLD');USTEC=@('USTEC','US100','NAS100','NDX100','UT100','NASDAQ100','NASUSD','USTECH','USNDX');USDJPY=@('USDJPY')}
$resolved=@{}
foreach($symbol in $aliasMap.Keys){
    $match=Find-BrokerSymbol @($probe.symbols | Where-Object {[int]$_.trade_mode -eq 4}) $aliasMap[$symbol]
    if(-not $match){throw "No fully tradeable cash symbol for $symbol on this broker. Netting/futures substitution is not supported."}
    if($match.volume_min -le 0 -or $match.volume_step -le 0){throw "Invalid volume rules: $($match.name)"}
    $resolved[$symbol]=$match.name
}
$ProfileName='Calyx-BestProp9-'+$login+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')
$ExpertFolderName=$ProfileName
$portfolio=@()
foreach($entry in $manifest.entries){
    $inputs=Get-PropReadyPresetInputs $entry
    $inputs['FTMOExpectedLogin']=$login;$inputs['FTMOExpectedServer']=$server;$inputs['FTMOExpectedSymbol']=$resolved[$entry.symbol]
    $inputs['FTMOExpectedCurrency']=$currency
    $inputs['FTMOReferenceBalance']=$initial.ToString('G17',[Globalization.CultureInfo]::InvariantCulture)
    $inputs['FTMOStartUtcTime']=[string]$reference.start_utc;$inputs['FTMOPhase']=[string]$phaseNumber
    $inputs['FTMORiskCapPercent']=$capText
    if($inputs.Contains('InpExpectedLogin')){$inputs['InpExpectedLogin']=$login;$inputs['InpExpectedServer']=$server}
    $tf=[string]$entry.timeframe
    $minutes=if($tf.StartsWith('H')){60*[int]$tf.Substring(1)}elseif($tf.StartsWith('M')){[int]$tf.Substring(1)}else{throw 'Unsupported timeframe.'}
    $portfolio+=[pscustomobject]@{Label=$entry.label;Expert=$entry.expert;Period=$minutes;BrokerSymbol=$resolved[$entry.symbol];
        ExpertFullPath=(Join-Path $Package $entry.expert);EffectiveInputs=$inputs}
}
Write-Host "Broker: $($probe.account.company) / login $login / $server / balance $($probe.account.balance) $currency"
Write-Host "Saved risk reference: $initial $currency; phase $Phase."
Write-Host "Requested risk: $RiskValue $RiskMode = $capPercent% of the saved starting balance; per-entry maximum: $([math]::Round($initial*$capPercent/100,2)) $currency."
Write-Host "Limits: $([math]::Round($initial*$capPercent*0.045,2)) total open risk; $([math]::Round($initial*$capPercent*0.03,2)) per symbol; $($initial*0.03) daily reserved loss; $($initial*0.92) equity entry buffer."
Write-Host 'Seven entries / three losing positions maximum per Prague day; 80% protected-equity margin cap.'
Write-Host "Nasdaq DI: $NasdaqDIFilter / USDJPY DI: $UsdJpyDIFilter (ADX20 kept). News and hourly EAs are not included."
Write-Host 'Historical FTMO replay results do not guarantee any future result or any firm rule compliance.' -ForegroundColor Yellow
$portfolio | Select-Object Label,BrokerSymbol,Period | Format-Table -AutoSize
if($PreflightOnly){Write-Host 'Preflight complete. Nothing installed or restarted.';exit 0}
Write-Host 'Use one terminal/copy for this account. Stop other VPS/manual trading before confirming.'
$expected="BEST PROP $login $currency $Phase"
if((Read-Host "Type exactly: $expected") -cne $expected){throw 'Confirmation mismatch. Nothing installed.'}
$confirmationText=(& $python (Join-Path $PSScriptRoot 'probe_account.py') --terminal $terminalPath) -join "`n"
if($LASTEXITCODE -ne 0){throw 'Final account check failed; nothing installed.'}
$confirmation=$confirmationText | ConvertFrom-Json
Assert-PropReadyConfirmation $probe $confirmation
Close-TargetTerminal $terminalPath
$mql=Join-Path $dataRoot 'MQL5'
$experts=Join-Path (Join-Path $mql 'Experts') $ProfileName
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
Test-ManagedProfile $profile $portfolio 'Best Prop installed profile'
if($chosen.write){                                       # first install, or the user chose to start fresh
    [void](New-Item -ItemType Directory -Path (Split-Path -Parent $statePath) -Force)
    [IO.File]::WriteAllText($statePath,($reference | ConvertTo-Json),[Text.UTF8Encoding]::new($false))
}
$commonIni=Join-Path $dataRoot 'config\common.ini'
if(-not(Test-Path -LiteralPath $commonIni)){throw 'Cannot locate common.ini. Files installed, terminal NOT restarted.'}
Copy-Item -LiteralPath $commonIni -Destination ($commonIni+'.best-prop-backup-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
Set-IniValue $commonIni 'Experts' 'Enabled' '0'
Set-IniValue $commonIni 'Experts' 'Account' '1'
Set-IniValue $commonIni 'Charts' 'ProfileLast' $ProfileName
[IO.File]::WriteAllText((Join-Path $profile 'DEPLOYMENT.txt'),
    "Portfolio: Best Prop Portfolio 2026-10-20 (nine EAs, 1%)`r`nAccount: $login / $server / $currency`r`nPhase: $Phase`r`nReference: $initial; start UTC: $($reference.start_utc)`r`nRequested allocation: $RiskMode $RiskValue (per-entry cap $capPercent% of reference)`r`nNasdaq DI: $NasdaqDIFilter; USDJPY DI: $UsdJpyDIFilter`r`nNews: OFF; five ORBs: 0.5R; Algo Trading: OFF`r`n",[Text.UTF8Encoding]::new($false))
Start-Process -FilePath $terminalPath -ArgumentList ('/profile:"'+$ProfileName+'"') -WindowStyle Hidden
Write-Host "Installed $ProfileName. Review all nine charts and inputs; Algo Trading remains OFF."
Write-Host 'Turn Algo Trading ON yourself when satisfied. No orders were placed by this installer.'
