[CmdletBinding()]
param(
    [string]$TargetTerminal,
    [switch]$UseDefaults,                # accept every default without prompting (account size, guard limits, DI ON)
    [ValidateSet('','ON','OFF')][string]$NasdaqDIFilter='',
    [string]$GoldSymbol='',
    [string]$NasdaqSymbol='',
    [switch]$ValidateOnly,
    [switch]$PreflightOnly
)
# funded_v1 installer (2026-10-28), adapted from Packages/Turbo5/Install-Turbo5.ps1 (Prop Ready flow: flat account, Algo Trading OFF,
# typed confirmation, NEW profile, saved baseline). Installs 9 guarded EAs on an ALREADY RUNNING normal MT5 terminal of ANY broker
# (hedging). Asks for every guard limit; Enter keeps the default (Leveraged $50k rules). Places no orders; Algo Trading stays OFF.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=[IO.Path]::GetFullPath((Join-Path $PSScriptRoot '..\..\..'))
$Package=Join-Path $PSScriptRoot 'package'
. (Join-Path $PSScriptRoot 'Account-Helpers.ps1')
$inv=[Globalization.CultureInfo]::InvariantCulture

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
function Get-FundedHash([string]$Path){
    $stream=[IO.File]::OpenRead($Path);$hash=[Security.Cryptography.SHA256]::Create()
    try{return ([BitConverter]::ToString($hash.ComputeHash($stream))).Replace('-','').ToLowerInvariant()}
    finally{$hash.Dispose();$stream.Dispose()}
}
function Read-Number([string]$Question,[double]$Default,[double]$Min,[double]$Max){
    if($UseDefaults){return $Default}
    $raw=(Read-Host ("$Question [{0}]" -f $Default.ToString('G',$inv))).Trim()
    if(-not $raw){return $Default}
    $value=0.0
    if(-not [double]::TryParse($raw,[Globalization.NumberStyles]::Float,$inv,[ref]$value) -or $value -lt $Min -or $value -gt $Max){throw "$Question must be a number from $Min to $Max."}
    return $value
}
function Read-Choice([string]$Question,[string]$Default,[string[]]$Allowed){
    if($UseDefaults){return $Default}
    $raw=(Read-Host "$Question [$Default]").Trim().ToUpperInvariant()
    if(-not $raw){return $Default}
    if($raw -notin $Allowed){throw "$Question must be one of: $($Allowed -join ', ')."}
    return $raw
}
# Broker symbols are written verbatim into chart and input records (same checks as the Codex_Best_FTMO installer).
function Find-FundedCashSymbol([object[]]$Symbols,[string[]]$Aliases,[string]$ExactName,[string]$Label){
    $unsafe='[\p{Cc}\p{Cf}\p{Zl}\p{Zp}<>=]'
    if($ExactName -match $unsafe){throw 'Unsafe exact broker symbol name.'}
    $tradeable=@($Symbols | Where-Object {[int]$_.trade_mode -eq 4})
    $match=$null
    if(-not $ExactName){$match=Find-BrokerSymbol $tradeable $Aliases}
    if(-not $ExactName -and -not $match){
        Write-Host "No automatic match for $Label. Type the exact cash symbol shown in this broker's Market Watch (futures are not supported)." -ForegroundColor Yellow
        $ExactName=(Read-Host "Exact $Label symbol (blank cancels)").Trim()
        if($ExactName -match $unsafe){throw 'Unsafe exact broker symbol name.'}
        if(-not $ExactName){throw "No $Label symbol selected. Nothing installed."}
    }
    if($ExactName){
        $found=@($tradeable | Where-Object {[string]$_.name -ieq $ExactName})
        if($found.Count -ne 1){throw "Exact fully tradeable broker symbol not found: $ExactName"}
        $match=$found[0]
    }
    if(-not $match){throw "No fully tradeable cash symbol for $Label."}
    if(([string]$match.path+' '+[string]$match.name) -match '(?i)future'){throw "Futures substitution is not supported: $($match.name)"}
    foreach($field in @('volume_min','volume_max','volume_step','trade_contract_size')){
        if([double]$match.$field -le 0){throw "Invalid cash-contract rule $field for $($match.name)"}
    }
    return $match
}
function Assert-FundedPackage {
    $expected=@('nasdaq-5m-candle-momentum','ema3','3-way-gold','orb-volume-profile-volume-confirmed','xau-orb-london-ny-overlap-m30',
        'dmc-fresh-reaction-us100','dmc-current-xau','xau-rsi-vwap','gold-overnight-value-area')
    if($manifest.entries.Count -ne 9 -or $manifest.news_eas -or -not $manifest.hedging_required){throw 'Unexpected funded_v1 package policy.'}
    if(@($manifest.entries | Group-Object slug | Where-Object Count -ne 1).Count -or @($manifest.entries | Where-Object slug -notin $expected).Count){throw 'funded_v1 roster changed.'}
    if((Get-FundedHash (Join-Path $PSScriptRoot 'CalyxFundedGuard.mqh')) -ine $manifest.guard_sha){throw 'Guard changed; rebuild package first.'}
    foreach($file in $manifest.files.PSObject.Properties){
        $path=Join-Path $Package $file.Name
        if(-not(Test-Path -LiteralPath $path) -or (Get-FundedHash $path) -ine $file.Value){throw "Missing/altered package file: $($file.Name)"}
    }
    foreach($entry in $manifest.entries){
        $inputs=Read-SetInputs (Join-Path $Package $entry.settings)
        if($inputs['FundedGuardMode'] -ne '1' -or $inputs['FundedExpectedLogin'] -ne '0' -or $inputs['FundedReferenceBalance'] -ne '0' -or $inputs['FundedStartUtcTime'] -ne '0' -or
           $inputs['InpAdaptivePortfolioControls'] -ne 'false'){throw 'Distributed settings must be unarmed, guard ON, adaptive off.'}
        if($entry.slug -in @('orb-volume-profile-volume-confirmed','xau-orb-london-ny-overlap-m30') -and $inputs['InpRewardRisk'] -ne '0.5'){throw 'Both ORBs must keep 0.5R.'}
        if(-not(Test-Path -LiteralPath (Join-Path $Package $entry.expert))){throw 'Missing compiled EA.'}
    }
}
$manifest=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'PACKAGE.json') | ConvertFrom-Json
Assert-FundedPackage
Write-Host 'FUNDED_V1: Nasdaq 5M, EMA3, 3 Way Gold, ORB VP Volume Confirmed 0.5R, XAU ORB London-NY 0.5R, DMC Fresh Reaction US100, DMC Current XAU, XAU RSI VWAP, Gold Overnight Value Area.' -ForegroundColor Cyan
Write-Host 'One account-wide guard: every entry sized to your risk and cut to fit the limits; daily win / daily loss / floor buffer CLOSE ALL trades.'
if($ValidateOnly){Write-Host 'PASS: 9 integrity-checked funded_v1 EAs; settings unarmed; both ORBs 0.5R. No account accessed.';exit 0}

$candidates=@(Get-Mt5Candidates | Where-Object {$_.Running -and $_.Path -notmatch '(?i)\\(_Backtests|Tester|temp)\\'})
if($candidates.Count -eq 0){throw 'Open your intended normal MT5 terminal and log into the funded account first.'}
if($TargetTerminal -and -not @($candidates | Where-Object Path -eq $TargetTerminal).Count){throw 'Target must be an already running normal MT5 terminal.'}
$selected=Select-Mt5Candidate $candidates
$terminalPath=[IO.Path]::GetFullPath($selected.Path)
$python=(Get-Command python.exe -ErrorAction Stop).Source
$probeText=(& $python (Join-Path $PSScriptRoot 'probe_account.py') --terminal $terminalPath) -join "`n"
if($LASTEXITCODE -ne 0){throw 'Account preflight failed; nothing installed.'}
$probe=$probeText | ConvertFrom-Json
Assert-FundedAccount $probe
$dataRoot=[IO.Path]::GetFullPath([string]$probe.terminal.data_path)
if(-not(Test-Path -LiteralPath (Join-Path $dataRoot 'MQL5'))){throw 'Invalid terminal data folder.'}
$login=[string]$probe.account.login;$server=[string]$probe.account.server;$currency=[string]$probe.account.currency
$balance=[double]$probe.account.balance;$equity=[double]$probe.account.equity
Write-Host "Broker: $($probe.account.company) / login $login / $server / balance $balance $currency / leverage 1:$($probe.account.leverage)"

Write-Host ''
Write-Host 'Firm rules (Enter keeps the default = Leveraged $50k reward account):' -ForegroundColor Cyan
$size=Read-Number 'Account size (firm nominal) in account currency' 50000 100 100000000
$maxLoss=Read-Number 'Firm max loss % (trailing amount)' 6 0.5 50
$trailMode=[int](Read-Number 'Max-loss type: 0 = trails highest closed balance, 1 = trails equity high-water, 2 = static' 0 0 2)
$lock=Read-Choice 'Floor locks at the initial balance once reached and after payouts? Y/N' 'Y' @('Y','N')
$firmDaily=Read-Number 'Firm daily loss %' 3 0.5 50
$resetHour=[int](Read-Number 'Daily reset hour (UTC)' 0 0 23)
$basis=[int](Read-Number 'Daily loss measured from: 1 = higher of balance/equity at reset, 0 = balance' 1 0 1)
$defaultFloor=$balance-$maxLoss/100*$size
Write-Host "Current max-loss level on your dashboard (the level that breaches the account). Blank = computed ($($defaultFloor.ToString('0.00',$inv)))."
$knownFloor=if($UseDefaults){0}else{$raw=(Read-Host 'Max-loss level [computed]').Trim();if($raw){[double]::Parse($raw,$inv)}else{0}}
if($knownFloor -ne 0 -and $knownFloor -ge $balance){throw 'Max-loss level must be below the balance.'}
Write-Host ''
Write-Host 'Guard limits (your own risk management; Enter keeps the default):' -ForegroundColor Cyan
$risk=Read-Number 'Risk per trade % of account size' 0.5 0.01 5
$taper=Read-Number 'Also cap each trade at % of the room above the floor (0 = off)' 5 0 100
$maxOpen=Read-Number 'Max open risk % (all stops + pending orders)' 2 0.05 20
$maxSym=Read-Number 'Max open risk per symbol %' 1.5 0.05 20
$dailyLoss=Read-Number 'Max daily loss % (close ALL trades and stop for the day)' 2 0.1 50
$dailyWin=Read-Number 'Max daily win % (close ALL trades and stop for the day; 0 = off)' 0.75 0 50
$buffer=Read-Number 'Buffer above the max-loss level % (close ALL trades if equity reaches it)' 0.25 0 50
$news=[int](Read-Number 'No new entries this many minutes either side of high-impact USD news (0 = off)' 5 0 120)
$newsPending=Read-Choice 'Delete pending orders inside news windows? Y/N (strategies may not re-place them)' 'N' @('Y','N')
if(-not $NasdaqDIFilter){$NasdaqDIFilter=Read-Choice 'Nasdaq 5M DI filter ON or OFF' 'ON' @('ON','OFF')}
if($risk -gt $maxOpen){throw 'Risk per trade cannot exceed max open risk.'}
if($dailyLoss -gt $firmDaily){throw 'Max daily loss cannot exceed the firm daily loss.'}
if($buffer -ge $maxLoss){throw 'Buffer must be smaller than the max loss.'}

$serverHasher=[Security.Cryptography.SHA256]::Create()
try{$serverHash=([BitConverter]::ToString($serverHasher.ComputeHash([Text.Encoding]::UTF8.GetBytes($server)))).Replace('-','').Substring(0,16)}finally{$serverHasher.Dispose()}
# Reruns keep the saved baseline (the guard rebuilds the floor from deals after start_utc).
$statePath=Join-Path $dataRoot ("MQL5\Files\Calyx-FundedV1-$login-$serverHash.json")
$oldState=if(Test-Path -LiteralPath $statePath){Get-Content -Raw -LiteralPath $statePath | ConvertFrom-Json}else{$null}
$reference=Get-FundedReference $probe $oldState $size $knownFloor
$floor=if([double]$reference.known_floor -gt 0){[double]$reference.known_floor}elseif($trailMode -eq 2){[double]$reference.reference_balance-$maxLoss/100*$size}else{[double]$reference.reference_balance-$maxLoss/100*$size}
if($lock -eq 'Y' -and $floor -gt $size){$floor=$size}
if($equity -le $floor+($buffer+0.05)/100*$size){throw "Equity $equity is too close to the max-loss level $floor; the guard would admit nothing. Stop for review."}

$aliasMap=@{XAUUSD=@('XAUUSD','GOLD','XAUUSD.','XAUUSDm');USTEC=@('USTEC','US100','NAS100','NDX100','UT100','NASDAQ100','NASUSD','USTECH','USNDX','USTECH100','NAS100.cash','US100.cash')}
$exact=@{XAUUSD=$GoldSymbol;USTEC=$NasdaqSymbol}
$resolved=@{}
foreach($symbol in $aliasMap.Keys){$resolved[$symbol]=(Find-FundedCashSymbol @($probe.symbols) $aliasMap[$symbol] $exact[$symbol] $symbol).name}
$eaRisk=[Math]::Min([double]5,[Math]::Round(1.5*$risk,4))   # the EA asks for more; the guard cuts every entry to its own budget
$ProfileName='Calyx-FundedV1-'+$login+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')
$ExpertFolderName=$ProfileName
$portfolio=@()
foreach($entry in $manifest.entries){
    $inputs=Read-SetInputs (Join-Path $Package $entry.settings)
    $inputs['InpRiskPercent']=$eaRisk.ToString('G',$inv)
    if($entry.slug -eq 'nasdaq-5m-candle-momentum'){$inputs['InpRequireDIAgreement']=if($NasdaqDIFilter -eq 'ON'){'true'}else{'false'}}
    $guard=[ordered]@{FundedAccountSize=$size;FundedRiskPercent=$risk;FundedRoomTaperPercent=$taper;FundedMaxOpenRiskPercent=$maxOpen;FundedMaxSymbolRiskPercent=$maxSym;
        FundedMaxDailyLossPercent=$dailyLoss;FundedMaxDailyWinPercent=$dailyWin;FundedMaxLossPercent=$maxLoss;FundedBufferPercent=$buffer;FundedFirmDailyPercent=$firmDaily;
        FundedReferenceBalance=[double]$reference.reference_balance;FundedKnownFloor=[double]$reference.known_floor}
    foreach($k in $guard.Keys){$inputs[$k]=([double]$guard[$k]).ToString('R',$inv)}
    $inputs['FundedTrailMode']=[string]$trailMode;$inputs['FundedLockAtInitial']=if($lock -eq 'Y'){'true'}else{'false'}
    $inputs['FundedDayResetUtcHour']=[string]$resetHour;$inputs['FundedDailyBasis']=[string]$basis;$inputs['FundedNewsBlackoutMinutes']=[string]$news
    $inputs['FundedNewsCancelPending']=if($newsPending -eq 'Y'){'true'}else{'false'}
    $inputs['FundedExpectedLogin']=$login;$inputs['FundedExpectedServer']=$server;$inputs['FundedExpectedSymbol']=$resolved[$entry.symbol]
    $inputs['FundedExpectedCurrency']=$currency;$inputs['FundedStartUtcTime']=[string]$reference.start_utc
    $tf=[string]$entry.timeframe
    $minutes=if($tf.StartsWith('H')){60*[int]$tf.Substring(1)}elseif($tf.StartsWith('M')){[int]$tf.Substring(1)}else{throw 'Unsupported timeframe.'}
    $portfolio+=[pscustomobject]@{Label=$entry.label;Expert=$entry.expert;Period=$minutes;BrokerSymbol=$resolved[$entry.symbol];
        ExpertFullPath=(Join-Path $Package $entry.expert);EffectiveInputs=$inputs}
}
$pct={param($p)($p/100*$size).ToString('0.00',$inv)}
Write-Host ''
Write-Host "Account size $size; saved reference balance $($reference.reference_balance) $currency; max-loss level now $floor."
Write-Host ("Per trade {0}% = {1}; open {2}; per symbol {3}; daily loss {4} (close all); daily win {5} (close all); buffer {6}." -f $risk,(& $pct $risk),(& $pct $maxOpen),(& $pct $maxSym),(& $pct $dailyLoss),$(if($dailyWin -gt 0){& $pct $dailyWin}else{'off'}),(& $pct $buffer))
Write-Host "Firm: max loss $maxLoss% type $trailMode lock $lock; daily $firmDaily% from $(if($basis -eq 1){'max(balance,equity)'}else{'balance'}) at $($resetHour):00 UTC. News +-$news min. Nasdaq DI $NasdaqDIFilter."
Write-Host 'No guarantee: gaps, slippage and costs can exceed planned stops; SL/TP fills inside news windows are not prevented.' -ForegroundColor Yellow
$portfolio | Select-Object Label,BrokerSymbol,Period | Format-Table -AutoSize
if($PreflightOnly){Write-Host 'Preflight complete. Nothing installed or restarted.';exit 0}
Write-Host 'Use one terminal for this account. Stop other VPS/manual trading before confirming.'
$expected="FUNDED_V1 $login $currency"
if((Read-Host "Type exactly: $expected") -cne $expected){throw 'Confirmation mismatch. Nothing installed.'}
$confirmationText=(& $python (Join-Path $PSScriptRoot 'probe_account.py') --terminal $terminalPath) -join "`n"
if($LASTEXITCODE -ne 0){throw 'Final account check failed; nothing installed.'}
$confirmation=$confirmationText | ConvertFrom-Json
Assert-FundedConfirmation $probe $confirmation
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
    if(-not(Test-Path -LiteralPath (Join-Path $experts $item.Expert))){Copy-Item -LiteralPath $item.ExpertFullPath -Destination (Join-Path $experts $item.Expert)}
    $setText=(@($item.EffectiveInputs.Keys | ForEach-Object {"$_=$($item.EffectiveInputs[$_])"}) -join "`r`n")+"`r`n"
    [IO.File]::WriteAllText((Join-Path $sets ('{0:D2} '-f ($i+1)+($item.Label -replace '[^A-Za-z0-9 ]','')+'.set')),$setText,[Text.UTF8Encoding]::new($false))
    $chart=New-ChartText $item $item.BrokerSymbol ([DateTime]::UtcNow.Ticks+$i) $i
    [IO.File]::WriteAllText((Join-Path $profile ('chart{0:D2}.chr' -f ($i+1))),$chart.TrimStart(),$unicode)
}
$order=((1..$portfolio.Count | ForEach-Object {'chart{0:D2}.chr' -f $_}) -join "`r`n")+"`r`n"
[IO.File]::WriteAllText((Join-Path $profile 'order.wnd'),$order,$unicode)
Test-ManagedProfile $profile $portfolio 'funded_v1 installed profile'
if(-not(Test-Path -LiteralPath $statePath)){
    [void](New-Item -ItemType Directory -Path (Split-Path -Parent $statePath) -Force)
    [IO.File]::WriteAllText($statePath,($reference | ConvertTo-Json),[Text.UTF8Encoding]::new($false))
}
$commonIni=Join-Path $dataRoot 'config\common.ini'
if(-not(Test-Path -LiteralPath $commonIni)){throw 'Cannot locate common.ini. Files installed, terminal NOT restarted.'}
Copy-Item -LiteralPath $commonIni -Destination ($commonIni+'.funded-v1-backup-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
Set-IniValue $commonIni 'Experts' 'Enabled' '0'
Set-IniValue $commonIni 'Experts' 'Account' '1'
Set-IniValue $commonIni 'Charts' 'ProfileLast' $ProfileName
[IO.File]::WriteAllText((Join-Path $profile 'DEPLOYMENT.txt'),
    "Portfolio: funded_v1 ($($manifest.version))`r`nAccount: $login / $server / $currency`r`nSize $size; reference $($reference.reference_balance); start UTC $($reference.start_utc); floor $floor`r`nRisk $risk% taper $taper% open $maxOpen% symbol $maxSym% daily loss $dailyLoss% daily win $dailyWin% buffer $buffer%`r`nFirm: max loss $maxLoss% type $trailMode lock $lock; daily $firmDaily% basis $basis reset $($resetHour):00 UTC; news $news min; Nasdaq DI $NasdaqDIFilter; Algo Trading OFF`r`n",[Text.UTF8Encoding]::new($false))
Start-Process -FilePath $terminalPath -ArgumentList ('/profile:"'+$ProfileName+'"') -WindowStyle Hidden
Write-Host "Installed $ProfileName. Review all nine charts and inputs; Algo Trading remains OFF."
Write-Host 'Enable Algo Trading yourself only when satisfied. No orders were placed by this installer.'
