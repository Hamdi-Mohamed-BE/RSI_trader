# Offline assertion suite. Imports declarations, never installer top-level actions.
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$PackageRoot=Split-Path -Parent $PSScriptRoot
$installer=Join-Path $PackageRoot '_Auto Deploy\Install-BMTradingPortfolio.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($installer,[ref]$tokens,[ref]$errors)
if($errors.Count){throw 'Parse error'}
$want=@('Get-PortfolioItems','Read-SetInputs','Test-NewsAdaptiveExemption','Get-EffectiveInputs',
        'New-ChartText','Normalize-Symbol','Find-BrokerSymbol','Test-ManagedProfile','Stop-WithMessage')
foreach($def in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst]},$true)){
    if($def.Name -in $want){. ([scriptblock]::Create($def.Extent.Text))}
}
$UsesDynamicRisk=$false;$RiskMode='DEFAULT';$EffectiveAdaptiveRiskPercent=1.0
$IsAdaptiveAccount=$true;$IsSmallAccount=$false;$UseRecommendedSelections=$false
$UseClaudeSelections=$false;$UseAdaptiveProfile=$false;$IsFullSafe=$false
$checks=0
foreach($mode in @('STANDARD','SAFE','RECOMMENDED','ADAPTIVE','CLAUDE','100K','900','DYNAMIC')){
    $IsFullSafe=$mode -eq 'SAFE'
    $UseRecommendedSelections=$mode -in @('RECOMMENDED','ADAPTIVE','CLAUDE')
    $UseClaudeSelections=$mode -eq 'CLAUDE'
    $UseAdaptiveProfile=$mode -eq 'ADAPTIVE'
    $IsAdaptiveAccount=$mode -notin @('100K','900')
    $IsSmallAccount=$mode -eq '900'
    $UsesDynamicRisk=$mode -eq 'DYNAMIC'
    $RiskMode=if($UsesDynamicRisk){'FIXED_USD'}else{'DEFAULT'}
    $item=@(Get-PortfolioItems | Where-Object Label -eq 'Nasdaq 5M Candle Momentum')[0]
    $percent=if($UseAdaptiveProfile){.25}elseif($UsesDynamicRisk){.5}else{1.0}
    $item | Add-Member EffectiveRiskPercent $percent
    $item | Add-Member EffectiveRisk ($percent*100)
    $inputs=Get-EffectiveInputs $item
    foreach($pair in @{
        InpRequireDIAgreement='true';InpDIPeriod='14';InpEMAPeriod='12';
        InpUseFixedTarget='false';InpStopMode='2';InpInitialStopPercent='0.60';
        InpUseATRTrailing='true';InpTrailingATR='6.0';InpTrailStartR='1.0';
        InpCloseAtSessionEnd='false';InpUseMATrailing='false';
        InpUseBreakEven='false';InpUseDynamicTrailingSL='false';
        InpUseMarkovRegimeFilter='false'
    }.GetEnumerator()){
        if($inputs[$pair.Key] -ne $pair.Value){throw "$mode wrong $($pair.Key): $($inputs[$pair.Key])"}
        $checks++
    }
    if([double]$inputs['InpRiskPercent'] -ne $percent){throw "$mode changed risk"}
    if($item.ExpertFullPath -notlike '*DI Wide ATR EA.ex5'){throw "$mode wrong build"}
    if(-not(Test-Path -LiteralPath $item.ExpertFullPath)){throw "$mode missing binary"}
    Write-Host "PASS $mode : DI14 / EMA12 / 0.60% price SL / ATR6 +1R / no TP; risk $percent"
}
$ftmoScript=Join-Path $PackageRoot '_Auto Deploy\Install-FTMO13.ps1'
$ftmoAst=[Management.Automation.Language.Parser]::ParseFile($ftmoScript,[ref]$tokens,[ref]$errors)
if($errors.Count){throw ($errors | Out-String)}
$guard=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'CalyxFTMOGuard.mqh')
if($guard -notmatch 'risk>FTMO_RISK' -or $guard -notmatch 'MathFloor' -or $guard -match 'OrderSendAsync\('){throw 'Guard invariant failed'}
$ftmoText=Get-Content -Raw -LiteralPath $ftmoScript
if($ftmoText -match "Set-IniValue .+ 'Enabled' '1'"){throw 'Launcher must NOT arm'}
if($ftmoText -match 'Install-GoldNews|RuntimeOnly'){throw 'News runtime forbidden'}
$package=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'PACKAGE.json') | ConvertFrom-Json
if($package.entries.Count -ne 13 -or $package.news_enabled){throw 'Wrong FTMO lineup'}
$ExpertFolderName='OFFLINE-FTMO13'
function Get-EffectiveInputs([object]$Item){return $Item.EffectiveInputs}
$out=Join-Path $PSScriptRoot 'offline-chart-check'
[void](New-Item -ItemType Directory -Path $out -Force)
$portfolio=@();$Unicode=New-Object System.Text.UnicodeEncoding($false,$true)
foreach($e in $package.entries){
    $tf=[string]$e.timeframe
    $minutes=if($tf.StartsWith('H')){60*[int]$tf.Substring(1)}else{[int]$tf.Substring(1)}
    $in=Read-SetInputs (Join-Path (Join-Path $PSScriptRoot 'package') $e.settings)
    if($e.slug -eq 'nasdaq-5m-candle-momentum'){
        if($in['InpUseATRTrailing'] -ne 'true' -or $in['InpStopMode'] -ne '2' -or
           $in['InpInitialStopPercent'] -ne '0.60' -or $in['InpUseFixedTarget'] -ne 'false' -or
           $in['InpCloseAtSessionEnd'] -ne 'false' -or $in['InpRiskPercent'] -ne '0.5'){
            throw 'FTMO Nasdaq management or risk mismatch'
        }
    }
    $in['FTMOExpectedLogin']='123456';$in['FTMOExpectedServer']='FTMO.UnitTest';$in['FTMOExpectedSymbol']=$e.symbol
    $p=[pscustomobject]@{Label=$e.label;Expert=$e.expert;Period=$minutes;BrokerSymbol=$e.symbol;EffectiveInputs=$in}
    $portfolio+=$p;$i=$portfolio.Count-1
    $chart=New-ChartText $p $p.BrokerSymbol (1000+$i) $i
    [IO.File]::WriteAllText((Join-Path $out ('chart{0:D2}.chr' -f ($i+1))),$chart.TrimStart(),$Unicode)
    if($chart -notmatch 'FTMOExpectedLogin=123456' -or $chart -notmatch 'FTMOPhase=1'){throw 'Missing chart lock'}
}
Test-ManagedProfile $out $portfolio 'Offline FTMO13'
# Never run these launchers. Validate route and annotation directly.
$bats=@(Get-ChildItem -LiteralPath $PackageRoot -Filter '*.bat' | Where-Object Name -notmatch '^(AVA |FTMO )')
if($bats.Count -ne 8){throw "Unexpected maintained BAT count: $($bats.Count)"}
foreach($bat in $bats){
    $t=Get-Content -Raw -LiteralPath $bat.FullName
    if($t -notmatch 'DI14' -or $t -notmatch '(Start-Dynamic-Portfolio|Install-BMTradingPortfolio)\.ps1'){throw "Unverified route: $($bat.Name)"}
}
$result=@{nasdaq_parameter_assertions=$checks;normal_launchers=$bats.Count;ftmo_charts=13;
          news_enabled=$false;runtime_started=$false;account_accessed=$false}
$result | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PSScriptRoot 'LAUNCHER_CHECKS.json') -Encoding UTF8
Write-Host 'ALL OFFLINE LAUNCHER CHECKS PASSED.'
