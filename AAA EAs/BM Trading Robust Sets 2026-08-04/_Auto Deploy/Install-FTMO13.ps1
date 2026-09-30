[CmdletBinding()]
param(
    [string]$TargetTerminal,
    [ValidateSet('Challenge','Verification','Funded')][string]$Phase='Challenge',
    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',
    [switch]$PromptNasdaqDIFilter,
    [switch]$ValidateOnly,
    [switch]$PreflightOnly
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $PSScriptRoot
$StudyRoot=Join-Path $PackageRoot 'FTMO Thirteen EA Deployment 2026-09-27'
$Package=Join-Path $StudyRoot 'package'
$manifest=Get-Content -Raw -LiteralPath (Join-Path $StudyRoot 'PACKAGE.json') | ConvertFrom-Json
$Unicode=New-Object System.Text.UnicodeEncoding($false,$true)

# Import only pure helper declarations. NEVER execute the ordinary portfolio installer:
# that path starts the separate Gold News V9 service and enables automatic trading.
$tokens=$null;$parseErrors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile(
    (Join-Path $PSScriptRoot 'Install-BMTradingPortfolio.ps1'),[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw 'Shared installer parse failure'}
$helpers=@('Stop-WithMessage','Get-Mt5Candidates','Select-Mt5Candidate','Normalize-Symbol',
           'Find-BrokerSymbol','Read-SetInputs','New-ChartText','Test-ManagedProfile',
           'Set-IniValue','Close-TargetTerminal')
foreach($helper in $helpers){
    $def=@($ast.FindAll({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst]},$true) |
           Where-Object Name -eq $helper)
    if($def.Count -ne 1){throw "Missing/ambiguous helper: $helper"}
    . ([scriptblock]::Create($def[0].Extent.Text))
}
function Get-EffectiveInputs([object]$Item){return $Item.EffectiveInputs}
function Get-FTMOPresetInputs([object]$Entry, [ValidateSet('ON','OFF')][string]$DIChoice='ON') {
    $inputs=Read-SetInputs (Join-Path $Package $Entry.settings)
    if($Entry.slug -eq 'nasdaq-5m-candle-momentum'){
        if(-not $inputs.Contains('InpRequireDIAgreement')){throw 'Nasdaq preset does not support DI selection.'}
        $inputs['InpRequireDIAgreement']=if($DIChoice -eq 'OFF'){'false'}else{'true'}
    }
    return $inputs
}
function Assert-Package {
    if((Get-FileHash -LiteralPath (Join-Path $StudyRoot 'CalyxFTMOGuard.mqh') -Algorithm SHA256).Hash -ine $manifest.guard_sha){
        throw 'Risk guard changed since compilation. Rebuild and verify the package first.'
    }
    if($manifest.news_enabled -or $manifest.risk_usd -ne 50 -or $manifest.entries.Count -ne 14){
        throw 'Unexpected portfolio policy'
    }
    if(@($manifest.entries | Where-Object slug -match 'news').Count){throw 'News must stay OFF'}
    foreach($file in $manifest.files.PSObject.Properties){
        $path=Join-Path $Package $file.Name
        if(-not(Test-Path -LiteralPath $path)){throw "Missing package file: $($file.Name)"}
        if((Get-FileHash -LiteralPath $path -Algorithm SHA256).Hash -ine $file.Value){throw "Changed package file: $($file.Name)"}
    }
    foreach($entry in $manifest.entries){
        $inputs=Read-SetInputs (Join-Path $Package $entry.settings)
        if($inputs['FTMOExpectedLogin'] -ne '0'){throw 'Distributed settings must be unarmed'}
        if($inputs['InpRiskPercent'] -ne '0.5'){throw 'Unexpected risk input'}
        if($inputs['InpAdaptivePortfolioControls'] -ne 'false'){throw 'Adaptive risk must be OFF'}
        if(-not(Test-Path -LiteralPath (Join-Path $Package $entry.expert))){throw 'Missing compiled EA'}
    }
}
Assert-Package
if($PromptNasdaqDIFilter -and -not $PSBoundParameters.ContainsKey('NasdaqDIFilter') -and -not $ValidateOnly){
    $diChoice=(Read-Host 'Nasdaq 5M DI14 filter ON or OFF [ON]').Trim().ToUpperInvariant()
    if(-not $diChoice){$diChoice='ON'}
    if($diChoice -notin @('ON','OFF')){throw 'Nasdaq DI filter must be ON or OFF.'}
    $NasdaqDIFilter=$diChoice
}
Write-Host ("Nasdaq 5M DI14 filter: {0}; wider stop and ATR trailing unchanged." -f $NasdaqDIFilter)
if($NasdaqDIFilter -eq 'OFF'){Write-Host 'DI OFF is a custom selection; published DI-ON results do not describe it.' -ForegroundColor Yellow}
if($ValidateOnly){
    foreach($entry in $manifest.entries){$null=Get-FTMOPresetInputs $entry $NasdaqDIFilter}
    Write-Host 'PASS: 14 integrity-checked guarded EAs (incl. 3 Way Gold, market entries), fixed $50 maximum stop risk, no news. No account accessed.';exit 0
}

$candidates=@(Get-Mt5Candidates | Where-Object {
    $_.Running -and $_.Path -notmatch '(?i)\\(_Backtests|Tester|temp)\\|Ava'
})
if($candidates.Count -eq 0){throw 'Open your FTMO terminal and log in first. Research and Ava terminals are excluded.'}
if($TargetTerminal -and -not @($candidates | Where-Object Path -eq $TargetTerminal).Count){
    throw 'Target must be an already running normal MT5 terminal.'
}
$selected=Select-Mt5Candidate $candidates
$terminalPath=[IO.Path]::GetFullPath($selected.Path)
$python=(Get-Command python.exe -ErrorAction Stop).Source
$probeText=(& $python (Join-Path $StudyRoot 'probe_ftmo.py') --terminal $terminalPath) -join "`n"
if($LASTEXITCODE -ne 0){throw 'Account preflight failed; nothing installed.'}
$probe=$probeText | ConvertFrom-Json
if(-not $probe.ok -or -not $probe.terminal.connected){throw 'Terminal is not connected.'}
if($probe.account.company -notmatch '(?i)FTMO' -or $probe.account.currency -ne 'USD'){
    throw 'This launcher only accepts an FTMO USD account.'
}
if([int]$probe.account.margin_mode -ne 2){throw 'Separate-EA portfolio requires hedging mode.'}
if(-not $probe.account.trade_allowed -or -not $probe.account.trade_expert){throw 'Account does not permit EA trading.'}
if($probe.terminal.trade_allowed){throw 'Turn Algo Trading OFF in the selected MT5 terminal, then run again.'}
if($probe.positions -ne 0 -or $probe.orders -ne 0){throw 'Account must be flat with no pending orders; nothing will be closed automatically.'}
if($probe.account.balance -lt 9200 -or $probe.account.balance -gt 15000){
    throw 'Balance outside this $10K profile range. Confirm account size separately.'
}
if($probe.account.leverage -gt 30){throw 'Account leverage does not match the intended Swing profile (up to 1:30).'}
$dataRoot=[IO.Path]::GetFullPath([string]$probe.terminal.data_path)
if(-not(Test-Path -LiteralPath (Join-Path $dataRoot 'MQL5'))){throw 'Invalid terminal data folder'}
$login=[string]$probe.account.login
$server=[string]$probe.account.server
if($server -match '[\r\n<>]'){throw 'Unsupported server name'}
$phaseNumber=@{Challenge=1;Verification=2;Funded=3}[$Phase]
$aliasMap=@{
    XAUUSD=@('XAUUSD','GOLD')
    USTEC=@('USTEC','US100','NAS100','NDX100','UT100','NASDAQ100')
    USDJPY=@('USDJPY')
}
$resolved=@{}
foreach($symbol in $aliasMap.Keys){
    $match=Find-BrokerSymbol $probe.symbols $aliasMap[$symbol]
    if(-not $match -or [int]$match.trade_mode -ne 4){throw "No fully tradeable cash symbol for $symbol"}
    if($match.volume_min -le 0 -or $match.volume_step -le 0){throw "Invalid volume rules: $($match.name)"}
    $resolved[$symbol]=$match.name
}
$ProfileName='CF13-'+$login+'-'+(Get-Date -Format 'yyyyMMdd-HHmmss')
$ExpertFolderName=$ProfileName
$portfolio=@()
foreach($entry in $manifest.entries){
    $inputs=Get-FTMOPresetInputs $entry $NasdaqDIFilter
    $inputs['FTMOExpectedLogin']=$login
    $inputs['FTMOExpectedServer']=$server
    $inputs['FTMOExpectedSymbol']=$resolved[$entry.symbol]
    $inputs['FTMOPhase']=[string]$phaseNumber
    if($inputs.Contains('InpExpectedLogin')){$inputs['InpExpectedLogin']=$login;$inputs['InpExpectedServer']=$server}
    $tf=[string]$entry.timeframe
    $minutes=if($tf.StartsWith('H')){60*[int]$tf.Substring(1)}elseif($tf.StartsWith('M')){[int]$tf.Substring(1)}else{throw 'Unsupported timeframe'}
    $portfolio+=[pscustomobject]@{
        Label=$entry.label;Expert=$entry.expert;Period=$minutes;BrokerSymbol=$resolved[$entry.symbol]
        ExpertFullPath=(Join-Path $Package $entry.expert);EffectiveInputs=$inputs
    }
}
Write-Host "FTMO $Phase / login $login / $server / $($probe.account.balance) USD"
Write-Host '14 EAs incl. 3 Way Gold (3 modules, market entries); News Pulse and Gold News V9 OFF. $50 maximum stop risk per trade, rounded DOWN.'
Write-Host 'Limits: $225 open risk; $150 per symbol; $300 daily reserved loss; $9,200 equity buffer.'
Write-Host 'Seven entries/day maximum; no new entries after three net losing positions; 80% margin cap.'
Write-Host 'These are entry guards, not guaranteed protection from gaps, outages or FTMO rule breaches.'
Write-Host ("Nasdaq: DI14 {0} + 0.60% price stop + ATR6 from +1R, no TP; overnight/weekend holding." -f $NasdaqDIFilter)
Write-Host 'Old fixed-target FTMO pass-rate/timing estimates do not apply to this revised portfolio.'
$portfolio | Select-Object Label,BrokerSymbol,Period | Format-Table -AutoSize
if($PreflightOnly){Write-Host 'Preflight complete. Nothing installed or restarted.';exit 0}
Write-Host 'Use ONE terminal only for this account. Disable all other copies/VPS/manual trading.'
Write-Host 'Only select this profile for a USD $10,000 FTMO 2-Step Swing account; MT5 cannot prove the purchased product.'
$expected="FTMO SWING 10000 $login $Phase"
if((Read-Host "Type exactly: $expected") -cne $expected){throw 'Confirmation mismatch. Nothing installed.'}

# Clean close only; never force-kill a trading terminal.
Close-TargetTerminal $terminalPath
$mql=Join-Path $dataRoot 'MQL5'
$experts=Join-Path (Join-Path $mql 'Experts') $ExpertFolderName
$profilesRoot=Join-Path $mql 'Profiles\Charts'
$profile=Join-Path $profilesRoot $ProfileName
$sets=Join-Path (Join-Path $mql 'Profiles\Tester') $ProfileName
foreach($dest in @($experts,$profile,$sets)){
    if(Test-Path -LiteralPath $dest){throw "Refusing to overwrite existing directory: $dest"}
    [void](New-Item -ItemType Directory -Path $dest -Force)
}
for($i=0;$i -lt $portfolio.Count;$i++){
    $item=$portfolio[$i]
    Copy-Item -LiteralPath $item.ExpertFullPath -Destination (Join-Path $experts $item.Expert)
    $setText=(@($item.EffectiveInputs.Keys | ForEach-Object {"$_=$($item.EffectiveInputs[$_])"}) -join "`r`n")+"`r`n"
    [IO.File]::WriteAllText((Join-Path $sets ($item.Expert -replace '\.ex5$','.set')),$setText,[Text.UTF8Encoding]::new($false))
    $chart=New-ChartText $item $item.BrokerSymbol ([DateTime]::UtcNow.Ticks+$i) $i
    [IO.File]::WriteAllText((Join-Path $profile ('chart{0:D2}.chr' -f ($i+1))),$chart.TrimStart(),$Unicode)
}
$order=((1..$portfolio.Count | ForEach-Object {'chart{0:D2}.chr' -f $_}) -join "`r`n")+"`r`n"
[IO.File]::WriteAllText((Join-Path $profile 'order.wnd'),$order,$Unicode)
Test-ManagedProfile $profile $portfolio 'FTMO installed profile'
$commonIni=Join-Path $dataRoot 'config\common.ini'
if(-not(Test-Path -LiteralPath $commonIni)){throw 'Cannot locate common.ini. Files installed, but terminal NOT restarted.'}
Copy-Item -LiteralPath $commonIni -Destination ($commonIni+'.ftmo13-backup-'+(Get-Date -Format 'yyyyMMdd-HHmmss'))
# Deliberately do not arm trading from a BAT; user reviews active account and charts first.
Set-IniValue $commonIni 'Experts' 'Enabled' '0'
Set-IniValue $commonIni 'Experts' 'Account' '1'
Set-IniValue $commonIni 'Charts' 'ProfileLast' $ProfileName
[IO.File]::WriteAllText((Join-Path $profile 'DEPLOYMENT.txt'),
    "Account: $login`r`nServer: $server`r`nPhase: $Phase`r`nNews: OFF`r`nNasdaq DI14: $NasdaqDIFilter`r`nRisk: max USD 50 stop risk; costs/gaps extra.`r`n",[Text.UTF8Encoding]::new($false))
Start-Process -FilePath $terminalPath -ArgumentList ('/profile:"'+$ProfileName+'"') -WindowStyle Hidden
Write-Host "Installed profile $ProfileName. Algo Trading remains OFF."
Write-Host ('Review all {0} charts and account details. Enable Algo Trading yourself only when satisfied.' -f $portfolio.Count)
Write-Host 'New phase/account requires running this launcher again. No automatic phase/account switching.'
