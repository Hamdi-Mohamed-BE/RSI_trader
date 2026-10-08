$ErrorActionPreference='Stop'
$PackageRoot=$PSScriptRoot
$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot 'Install-Portfolio.ps1'),[ref]$null,[ref]$errors)
if($errors.Count){throw ($errors.Message -join '; ')}
foreach($node in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -notin @('Main','Stop-WithMessage')},$true)){. ([scriptblock]::Create($node.Extent.Text))}
. (Join-Path $PackageRoot 'Installer-Helpers.ps1')
function Stop-WithMessage([string]$Message){throw $Message}
function Assert([bool]$Condition,[string]$Label){if(-not $Condition){throw "FAILED: $Label"};$script:Checks++}
function Reject([scriptblock]$Action,[string]$Label){$bad=$false;try{& $Action}catch{$bad=$true};Assert $bad $Label}
$Checks=0
$package=Test-Package
$ProfileName=$package.profile;$ExpertFolderName=$ProfileName
Assert ($package.entries.Count -eq 15 -and $package.orb_keys.Count -eq 3) 'deduplicated 15-EA roster / three ORBs'
Assert (-not $package.ftmo_guard -and -not $package.shared_daily_stop) 'no FTMO guard or implicit daily stop'
Assert (@($package.entries|Where-Object{$_.key -in $package.orb_keys -and [double]$_.inputs.InpRewardRisk -eq 0.5}).Count -eq 3) 'all selected ORBs 0.5R'
Assert (@($package.entries|Where-Object{$_.key -eq 'us100-selective-orb-v3'}).Count -eq 0) 'untested 0.5R V3 excluded'
$ActiveLogin='12345';$ActiveServer='Mock-Broker-Hedge';$InstallNonce='offline-test'
$candidate=[pscustomobject]@{Path='C:\Mock MT5\terminal64.exe';DataRoot='C:\MockData\Terminal\123456';Running=$true}
$probe=[pscustomobject]@{
    terminal=[pscustomobject]@{connected=$true;path='C:\Mock MT5';data_path=$candidate.DataRoot}
    account=[pscustomobject]@{login=$ActiveLogin;server=$ActiveServer;currency='USD';margin_mode=2;balance=15000;equity=13500;trade_allowed=$true}
    symbols=@('USDJPYm','USTECm','XAUUSDm'|ForEach-Object{[pscustomobject]@{name=$_;path='CFD';trade_mode=4;visible=$true}})
}
Assert-Account $probe $candidate 'FIXED_USD'
$portfolio=@(Get-Portfolio $package $probe)
Assert ($portfolio.Count -eq 15) 'whole portfolio mapped'
foreach($item in $portfolio){Assert ($item.BrokerSymbol -in @('USDJPYm','USTECm','XAUUSDm')) 'suffix mapping'}
foreach($NasdaqDIFilter in @('ON','OFF')){foreach($UsdJpyDIFilter in @('ON','OFF')){
 foreach($mode in @('PERCENT','FIXED_USD')){
  $amounts=if($mode -eq 'PERCENT'){@(0.5,1,2,7.5)}else{@(50,200)}
  foreach($amount in $amounts){
   $RiskMode=$mode;$RiskValue=[double]$amount;Assert-Risk $mode $RiskValue
   foreach($item in $portfolio){
    $inputs=Get-EffectiveInputs $item
    Assert ([double]$inputs['InpRiskPercent'] -eq 0.5) 'native calibration retained'
    Assert ($inputs['InpPortfolioExpectedLogin'] -eq $ActiveLogin -and $inputs['InpPortfolioExpectedServer'] -eq $ActiveServer -and $inputs['InpPortfolioExpectedSymbol'] -eq $item.BrokerSymbol -and $inputs['InpPortfolioInstallNonce'] -eq $InstallNonce) 'account binding'
    Assert ($inputs['InpMagic'] -eq [string]$item.Magic) 'original magic retained'
    if($mode -eq 'PERCENT'){Assert ([double]$inputs['InpPortfolioPercent'] -eq $amount -and $inputs['InpPortfolioRiskMode'] -eq '0') 'chosen percent not FTMO clamped'}
    else{Assert ([double]$inputs['InpPortfolioFixedUSD'] -eq $amount -and $inputs['InpPortfolioRiskMode'] -eq '1') 'chosen fixed USD'}
    $base=Read-SetInputs $item.SetFullPath
    foreach($key in $base.Keys){if($key -notlike 'InpPortfolio*' -and $key -ne 'InpRequireDIAgreement'){Assert ($inputs[$key] -ceq $base[$key]) "signal/exit preserved $($item.Key).$key"}}
    if($item.Key -eq 'nasdaq-5m-candle-momentum'){Assert ($inputs['InpRequireDIAgreement'] -eq ($NasdaqDIFilter -eq 'ON').ToString().ToLowerInvariant()) 'Nasdaq DI choice'}
    if($item.Key -eq 'usdjpy-london-open-momentum'){
     Assert ($inputs['InpRequireDIAgreement'] -eq ($UsdJpyDIFilter -eq 'ON').ToString().ToLowerInvariant()) 'USDJPY DI choice'
     Assert ($inputs['InpUseADXFilter'] -eq 'true' -and [double]$inputs['InpADXMinimum'] -eq 20) 'USDJPY ADX20 unaffected'
    }
   }
  }
 }
}}
foreach($amount in @(0,-1,[double]::NaN,[double]::PositiveInfinity)){Reject {Assert-Risk 'PERCENT' $amount} 'invalid percentage rejected';Reject {Assert-Risk 'FIXED_USD' $amount} 'invalid cash rejected'}
Reject {Assert-Risk 'PERCENT' 10.01} 'over limit percentage rejected'
Reject {Assert-Risk 'OTHER' 1} 'invalid risk mode rejected'
foreach($currency in @('USD','EUR','GBP','JPY')){$probe.account.currency=$currency;Assert-Account $probe $candidate 'PERCENT';Assert-Account $probe $candidate 'FIXED_USD';Assert $true 'standard account currency accepted'}
foreach($currency in @('USC','EUC','USDc')){$probe.account.currency=$currency;Reject {Assert-Account $probe $candidate 'FIXED_USD'} 'cent cash conversion not guessed';Assert-Account $probe $candidate 'PERCENT'}
$probe.account.currency='USD';$probe.account.margin_mode=0;Reject {Assert-Account $probe $candidate 'PERCENT'} 'netting rejected';$probe.account.margin_mode=2
$probe.account.trade_allowed=$false;Reject {Assert-Account $probe $candidate 'PERCENT'} 'investor account rejected';$probe.account.trade_allowed=$true
$probe.terminal.data_path='C:\Other';Reject {Assert-Account $probe $candidate 'PERCENT'} 'wrong API terminal rejected';$probe.terminal.data_path=$candidate.DataRoot
$original=$probe.symbols;$probe.symbols=@($original|Where-Object{$_.name -ne 'USDJPYm'});Reject {Get-Portfolio $package $probe} 'no partial portfolio';$probe.symbols=$original
Reject {Assert-ChildPath $PackageRoot (Join-Path $PackageRoot '..\escape')} 'path traversal rejected'
$testRoot=Assert-ChildPath $PackageRoot (Join-Path $PackageRoot ('NativeTests\offline-'+[guid]::NewGuid().ToString('N')))
[void](New-Item -Path $testRoot -ItemType Directory)
$RiskMode='FIXED_USD';$RiskValue=200.0;$NasdaqDIFilter='OFF';$UsdJpyDIFilter='ON'
for($i=0;$i -lt $portfolio.Count;$i++){$item=$portfolio[$i];[IO.File]::WriteAllText((Join-Path $testRoot ('chart{0:D2}.chr' -f ($i+1))),(New-ChartText $item $item.BrokerSymbol (1000+$i) $i),[Text.Encoding]::Unicode)}
Assert-ChartInputs $testRoot $portfolio;Assert $true 'all 15 exact chart inputs validated'
$chart=Join-Path $testRoot 'chart13.chr';$text=Get-Content -LiteralPath $chart -Raw
[IO.File]::WriteAllText($chart,$text.Replace('InpPortfolioFixedUSD=200','InpPortfolioFixedUSD=201'),[Text.Encoding]::Unicode)
Reject {Assert-ChartInputs $testRoot $portfolio} 'corrupt chart cash rejected'
function Get-CimInstance{throw 'Live enumeration forbidden'}
function Invoke-AccountProbe{throw 'Live account API forbidden'}
$main=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Main'},$true)
. ([scriptblock]::Create($main.Extent.Text))
$ValidateOnly=$true;Main;Assert $true 'ValidateOnly without terminal enumeration or account API'
@{checks=$Checks;passed=$true;live_account_access=$false;utc=[DateTime]::UtcNow.ToString('o')}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PackageRoot 'TESTS.json') -Encoding UTF8
Write-Host "PASS: $Checks offline roster, risk, DI, account, preservation and chart checks."
