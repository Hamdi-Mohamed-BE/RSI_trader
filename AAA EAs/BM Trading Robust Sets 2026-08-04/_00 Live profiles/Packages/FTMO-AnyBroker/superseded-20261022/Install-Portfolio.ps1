[CmdletBinding()]
param(
    [string]$TargetTerminal,
    [ValidateSet('PERCENT','FIXED_USD')][string]$RiskMode='FIXED_USD',
    [double]$RiskValue=50,
    [ValidateSet('ON','OFF')][string]$UsdJpyDIFilter='ON',
    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',
    [ValidateSet('Challenge','Verification','Funded')][string]$Phase='Funded',
    [ValidateSet('PropReady','Codex_Best_FTMO')][string]$ProfileVariant='PropReady',
    [string]$GoldSymbol,
    [string]$NasdaqSymbol,
    [string]$UsdJpySymbol,
    [switch]$PromptNasdaqDIFilter,
    [switch]$ValidateOnly,
    [switch]$PreflightOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$Package=Join-Path $PSScriptRoot 'package'
. (Join-Path $PSScriptRoot 'Account-Helpers.ps1')
# Any-broker test build: extended cash-symbol matching and exact overrides are always available.
$isCodexProfile=$true
$profileDisplay='FTMO ANY BROKER'
$profileFolderPrefix='Calyx-FTMO17-AnyBroker'
$profileDeploymentLabel='FTMO guarded 17 any-broker test'
$profileValidationLabel='FTMO any-broker installed profile'
$profileBackupSuffix='.ftmo-any-broker-backup-'
if(-not $isCodexProfile -and ($GoldSymbol -or $NasdaqSymbol -or $UsdJpySymbol)){
    throw 'Exact symbol overrides are available only for Codex_Best_FTMO.'
}

# Import declarations, never execute the ordinary installer or its news service.
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
function Find-CodexCashSymbol([object[]]$Symbols,[string[]]$Aliases,[string]$ExactName,[string]$Label){
    # Broker symbols are written verbatim into chart and input records.
    $unsafeSymbolPattern='[\p{Cc}\p{Cf}\p{Zl}\p{Zp}<>=]'
    if($ExactName -match $unsafeSymbolPattern){throw 'Unsafe exact broker symbol name; control characters and chart delimiters are not allowed.'}
    $tradeable=@($Symbols | Where-Object {[int]$_.trade_mode -eq 4})
    $match=$null
    if(-not $ExactName){$match=Find-BrokerSymbol $tradeable $Aliases}
    if(-not $ExactName -and -not $match){
        Write-Host "No automatic cash-symbol match for $Label. Use the exact equivalent shown in this broker's Market Watch; futures are not supported." -ForegroundColor Yellow
        $ExactName=Read-Host "Exact $Label cash symbol (blank cancels)"
        if($ExactName -match $unsafeSymbolPattern){throw 'Unsafe exact broker symbol name; control characters and chart delimiters are not allowed.'}
        $ExactName=$ExactName.Trim()
        if(-not $ExactName){throw "No $Label symbol selected. Nothing installed."}
    }
    if($ExactName){
        $matches=@($tradeable | Where-Object {[string]$_.name -ieq $ExactName})
        if($matches.Count -ne 1){throw "Exact fully tradeable broker symbol not found: $ExactName"}
        $match=$matches[0]
    }
    if(-not $match){throw "No fully tradeable cash symbol for $Label."}
    if([string]::IsNullOrWhiteSpace([string]$match.name) -or [string]$match.name -match $unsafeSymbolPattern){
        throw 'Unsafe selected broker symbol name; control characters and chart delimiters are not allowed.'
    }
    if(([string]$match.path+' '+[string]$match.name) -match '(?i)future'){
        throw "Futures substitution is not supported: $($match.name)"
    }
    $numericRules=@{}
    foreach($field in @('volume_min','volume_max','volume_step','trade_contract_size')){
        try{$number=[double]$match.$field}catch{throw "Invalid cash-contract numeric rule: $field"}
        if([double]::IsNaN($number) -or [double]::IsInfinity($number) -or $number -le 0){
            throw "Invalid cash-contract numeric rule: $field"
        }
        $numericRules[$field]=$number
    }
    if($numericRules['volume_max'] -lt $numericRules['volume_min']){
        throw "Invalid cash-contract volume rules: $($match.name)"
    }
    return $match
}
function Get-PropReadyHash([string]$Path){
    $stream=[IO.File]::OpenRead($Path);$hash=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
    finally{$hash.Dispose();$stream.Dispose()}
}
function Assert-PropReadyPackage {
    if($manifest.entries.Count -ne 17 -or $manifest.news_enabled -or $manifest.currency_mode -ne 'ACCOUNT_CURRENCY' -or
       $manifest.risk_cap_fraction -ne 0.005 -or -not $manifest.hedging_required){throw 'Unexpected FTMO any-broker package policy.'}
    $expected=@('xau-rsi-vwap','gold-overnight-value-area','xau-squeeze-momentum-standard','dmc-fresh-reaction-us100','ema3','xau-trend-progression','xau-orb-london-ny-overlap-m30','nasdaq-overnight','us100-h1-orb-13utc','usdjpy-london-open-momentum','us100-month-end-flow','dmc-current-xau','nasdaq-5m-candle-momentum','3-way-gold','us100-orb-new-york-m30','us100-selective-orb-v3','xau-orb-new-york-m30')
    if(@($manifest.entries | Group-Object slug | Where-Object Count -ne 1).Count -or
       @($manifest.entries | Where-Object slug -notin $expected).Count){throw 'FTMO any-broker roster changed.'}
    if((Get-PropReadyHash (Join-Path $PSScriptRoot 'CalyxFTMOGuard.mqh')) -ine $manifest.guard_sha){throw 'Guard changed; rebuild package first.'}
    foreach($file in $manifest.files.PSObject.Properties){
        $path=Join-Path $Package $file.Name
        if(-not(Test-Path -LiteralPath $path) -or (Get-PropReadyHash $path) -ine $file.Value){throw "Missing/altered package file: $($file.Name)"}
    }
    foreach($entry in $manifest.entries){
        $inputs=Read-SetInputs (Join-Path $Package $entry.settings)
        if($inputs['FTMOExpectedLogin'] -ne '0' -or $inputs['FTMOReferenceBalance'] -ne '0' -or $inputs['FTMOStartUtcTime'] -ne '0' -or
           $inputs['InpRiskPercent'] -ne '0.5' -or $inputs['InpAdaptivePortfolioControls'] -ne 'false'){throw 'Distributed settings must be unarmed, with unchanged strategy risk inputs.'}
        if($entry.slug -match '-orb-' -and $inputs['InpRewardRisk'] -ne '0.5'){throw 'All five ORBs must retain 0.5R.'}
        if(-not(Test-Path -LiteralPath (Join-Path $Package $entry.expert))){throw 'Missing compiled EA.'}
    }
}
if([double]::IsNaN($RiskValue) -or [double]::IsInfinity($RiskValue) -or $RiskValue -le 0 -or ($RiskMode -eq 'PERCENT' -and $RiskValue -gt 10)){throw 'Invalid risk selection.'}
$manifest=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'PACKAGE.json') | ConvertFrom-Json
Assert-PropReadyPackage
if($PromptNasdaqDIFilter -and -not $PSBoundParameters.ContainsKey('NasdaqDIFilter') -and -not $ValidateOnly){
    $answer=(Read-Host 'Nasdaq DI ON or OFF [ON]').Trim().ToUpperInvariant()
    if(-not $answer){$answer='ON'}
    if($answer -notin @('ON','OFF')){throw 'DI choice must be ON or OFF.'}
    $NasdaqDIFilter=$answer
}
Write-Host "${profileDisplay}: the 17 FTMO-guarded EAs / five ORBs at 0.5R / broker-neutral TEST build for any MT5 hedging account." -ForegroundColor Cyan
Write-Host 'Fixed cash is in ACCOUNT CURRENCY (USD on a USD account); % uses current equity. Legacy parameter name: FIXED_USD.'
Write-Host 'Allocation is capped at 0.5% of saved initial balance and at the original strategy volume; lots round DOWN.' -ForegroundColor Yellow
if($ValidateOnly){
    foreach($entry in $manifest.entries){$null=Get-PropReadyPresetInputs $entry}
    Write-Host 'PASS: 17 integrity-checked guarded EAs (any-broker test build); all five ORBs at 0.5R. No account accessed.';exit 0
}

$candidates=@(Get-Mt5Candidates | Where-Object {
    $_.Running -and $_.Path -notmatch '(?i)\\(_Backtests|Tester|temp)\\'
})
if($candidates.Count -eq 0){throw 'Open your intended normal MT5 terminal and log into your demo or live account first.'}
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
# Branding must not reset the retained account baseline or shared safety state.
$statePath=Join-Path $dataRoot ("MQL5\Files\Calyx-PropReady-$login-$serverHash.json")
$oldState=if(Test-Path -LiteralPath $statePath){Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json}else{$null}
$reference=Get-PropReadyReference $probe $oldState
$initial=[double]$reference.reference_balance
if([double]$probe.account.equity -lt $initial*0.92){throw 'Account is below the retained 92% entry buffer; stop for review. Reinstallation does not reset losses.'}
$phaseNumber=@{Challenge=1;Verification=2;Funded=3}[$Phase]
$aliasMap=@{XAUUSD=@('XAUUSD','GOLD');USTEC=@('USTEC','US100','NAS100','NDX100','UT100','NASDAQ100','NASUSD','USTECH','USNDX');USDJPY=@('USDJPY')}
$exactSymbols=@{XAUUSD=$GoldSymbol;USTEC=$NasdaqSymbol;USDJPY=$UsdJpySymbol}
if($isCodexProfile){
    $aliasMap['USTEC']+=@('USA100','NAS100.cash','US100.cash','USTEC.cash','NASDAQ','USTECH100','USNAS100','USNDX100','NAS100USD')
}
$resolved=@{}
foreach($symbol in $aliasMap.Keys){
    $match=if($isCodexProfile){Find-CodexCashSymbol @($probe.symbols) $aliasMap[$symbol] $exactSymbols[$symbol] $symbol}else{
        Find-BrokerSymbol @($probe.symbols | Where-Object {[int]$_.trade_mode -eq 4}) $aliasMap[$symbol]
    }
    if(-not $match){throw "No fully tradeable cash symbol for $symbol. Netting/futures substitution is not supported."}
    if($match.volume_min -le 0 -or $match.volume_step -le 0){throw "Invalid volume rules: $($match.name)"}
    $resolved[$symbol]=$match.name
}
$ProfileName=$profileFolderPrefix+'-'+$login+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')
$ExpertFolderName=$ProfileName
$portfolio=@()
foreach($entry in $manifest.entries){
    $inputs=Get-PropReadyPresetInputs $entry
    $inputs['FTMOExpectedLogin']=$login;$inputs['FTMOExpectedServer']=$server;$inputs['FTMOExpectedSymbol']=$resolved[$entry.symbol]
    $inputs['FTMOExpectedCurrency']=$currency
    $inputs['FTMOReferenceBalance']=$initial.ToString('G17',[Globalization.CultureInfo]::InvariantCulture)
    $inputs['FTMOStartUtcTime']=[string]$reference.start_utc;$inputs['FTMOPhase']=[string]$phaseNumber
    if($inputs.Contains('InpExpectedLogin')){$inputs['InpExpectedLogin']=$login;$inputs['InpExpectedServer']=$server}
    $tf=[string]$entry.timeframe
    $minutes=if($tf.StartsWith('H')){60*[int]$tf.Substring(1)}elseif($tf.StartsWith('M')){[int]$tf.Substring(1)}else{throw 'Unsupported timeframe.'}
    $portfolio+=[pscustomobject]@{Label=$entry.label;Expert=$entry.expert;Period=$minutes;BrokerSymbol=$resolved[$entry.symbol];
        ExpertFullPath=(Join-Path $Package $entry.expert);EffectiveInputs=$inputs}
}
Write-Host "Broker: $($probe.account.company) / login $login / $server / balance $($probe.account.balance) $currency"
Write-Host "Saved risk reference: $initial $currency; phase $Phase (Funded = continuous demo/live mode, no phase profit stop)."
Write-Host "Requested risk: $RiskValue $RiskMode; planned per-entry maximum: $($initial*0.005) $currency."
Write-Host "Limits: $($initial*0.0225) open risk; $($initial*0.015) per symbol; $($initial*0.03) daily reserved loss; $($initial*0.92) equity entry buffer."
Write-Host 'Seven entries / three net losing positions maximum per Prague day; 80% protected-equity margin cap.'
Write-Host 'Initial deployment starts a new baseline; reruns retain it. No automatic liquidation. Gaps/costs may exceed planned risk.'
Write-Host "Nasdaq DI: $NasdaqDIFilter / USDJPY DI: $UsdJpyDIFilter (ADX20 retained). News and hourly EAs OFF."
Write-Host 'Other broker, currency, balance or DI/risk choices do NOT inherit historical FTMO pass rates or guarantee any firm compliance.' -ForegroundColor Yellow
$portfolio | Select-Object Label,BrokerSymbol,Period | Format-Table -AutoSize
if($PreflightOnly){Write-Host 'Preflight complete. Nothing installed or restarted.';exit 0}
Write-Host 'Use one terminal/copy for this account. Stop other VPS/manual trading before confirming.'
$expected="$profileDisplay $login $currency $Phase"
if((Read-Host "Type exactly: $expected") -cne $expected){throw 'Confirmation mismatch. Nothing installed.'}
$confirmationText=(& $python (Join-Path $PSScriptRoot 'probe_account.py') --terminal $terminalPath) -join "`n"
if($LASTEXITCODE -ne 0){throw 'Final account check failed; nothing installed.'}
$confirmation=$confirmationText | ConvertFrom-Json
Assert-PropReadyConfirmation $probe $confirmation
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
Test-ManagedProfile $profile $portfolio $profileValidationLabel
# Preserve baseline on reruns; never clear terminal global-variable safety latches.
if(-not(Test-Path -LiteralPath $statePath)){
    [void](New-Item -ItemType Directory -Path (Split-Path -Parent $statePath) -Force)
    [IO.File]::WriteAllText($statePath,($reference | ConvertTo-Json),[Text.UTF8Encoding]::new($false))
}
$commonIni=Join-Path $dataRoot 'config\common.ini'
if(-not(Test-Path -LiteralPath $commonIni)){throw 'Cannot locate common.ini. Files installed, terminal NOT restarted.'}
Copy-Item -LiteralPath $commonIni -Destination ($commonIni+$profileBackupSuffix+(Get-Date -Format 'yyyyMMdd-HHmmss'))
Set-IniValue $commonIni 'Experts' 'Enabled' '0'
Set-IniValue $commonIni 'Experts' 'Account' '1'
Set-IniValue $commonIni 'Charts' 'ProfileLast' $ProfileName
[IO.File]::WriteAllText((Join-Path $profile 'DEPLOYMENT.txt'),
    "Portfolio: $profileDeploymentLabel broker-neutral`r`nAccount: $login / $server / $currency`r`nPhase: $Phase`r`nReference: $initial; start UTC: $($reference.start_utc)`r`nRequested allocation: $RiskMode $RiskValue`r`nNasdaq DI: $NasdaqDIFilter; USDJPY DI: $UsdJpyDIFilter`r`nNews: OFF; five ORBs: 0.5R; Algo Trading: OFF`r`n",[Text.UTF8Encoding]::new($false))
Start-Process -FilePath $terminalPath -ArgumentList ('/profile:"'+$ProfileName+'"') -WindowStyle Hidden
Write-Host "Installed $ProfileName. Review all 17 charts and inputs; Algo Trading remains OFF."
Write-Host 'Enable Algo Trading yourself only when satisfied. No orders were placed by this installer.'
