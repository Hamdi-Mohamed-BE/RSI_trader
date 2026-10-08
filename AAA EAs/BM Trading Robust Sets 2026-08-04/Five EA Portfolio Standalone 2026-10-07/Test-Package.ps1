$ErrorActionPreference='Stop'
$PackageRoot=$PSScriptRoot
$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot 'Install-FivePortfolio.ps1'),[ref]$null,[ref]$errors)
if ($errors.Count) { throw ($errors.Message -join '; ') }
# Load function definitions only. Never invoke Main, account API or terminal enumeration.
foreach ($node in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -ne 'Main'}, $true)) {
    if ($node.Name -ne 'Stop-WithMessage') { . ([scriptblock]::Create($node.Extent.Text)) }
}
. (Join-Path $PackageRoot 'Installer-Helpers.ps1')
function Stop-WithMessage([string]$Message) { throw $Message }
function Assert([bool]$Condition, [string]$Label) { if (-not $Condition) { throw "FAILED: $Label" }; $script:Checks++ }
function Reject([scriptblock]$Action, [string]$Label) { $rejected=$false; try { & $Action } catch { $rejected=$true }; Assert $rejected $Label }
$Checks=0
$package=Test-Package
$ProfileName=$package.profile
$ExpertFolderName=$ProfileName
$ActiveLogin='12345'; $ActiveServer='Mock-Broker-Hedge'; $InstallNonce='test-only-not-live'
$candidate=[pscustomobject]@{Path='C:\Mock MT5\terminal64.exe'; DataRoot='C:\MockData\Terminal\123456'; Running=$true}
$probe=[pscustomobject]@{
    ok=$true
    terminal=[pscustomobject]@{connected=$true; path='C:\Mock MT5'; data_path=$candidate.DataRoot}
    account=[pscustomobject]@{login=$ActiveLogin; server=$ActiveServer; currency='USD'; margin_mode=2; balance=10000; equity=9000; trade_allowed=$true}
    symbols=@('US30m','USTECm','XAUUSDm' | ForEach-Object { [pscustomobject]@{name=$_; path='CFD'; trade_mode=4; visible=$true} })
}
Assert-Account $probe $candidate 'FIXED_USD'; Assert $true 'USD hedging account accepted'
$portfolio=@(Get-Portfolio $package $probe)
Assert ($portfolio.Count -eq 5) 'five symbols/periods matched'
Assert ($portfolio[2].BrokerSymbol -eq 'USTECm' -and $portfolio[2].Period -eq 5) 'Nasdaq M5 suffix mapping'
foreach ($mode in @('PERCENT','FIXED_USD')) {
    foreach ($amount in @(0.5,1,7.5)) {
        Assert-Risk $mode $amount
        $RiskMode=$mode; $RiskValue=[double]$amount
        foreach ($item in $portfolio) {
            $inputs=Get-EffectiveInputs $item
            Assert ($inputs['InpPortfolioExpectedLogin'] -eq $ActiveLogin -and $inputs['InpPortfolioExpectedSymbol'] -eq $item.BrokerSymbol) 'account/symbol binding'
            Assert ($inputs['InpPortfolioExpectedServer'] -eq $ActiveServer -and $inputs['InpPortfolioInstallNonce'] -eq $InstallNonce) 'server/nonce binding'
            Assert ($inputs['InpMagic'] -eq [string]$item.Magic) 'original magic retained'
            if ($mode -eq 'PERCENT') {
                Assert ([double]$inputs['InpRiskPercent'] -eq $amount -and $inputs['InpPortfolioRiskMode'] -eq '0') 'dynamic percent not capped at one'
                if ($item.Hourly) { Assert ($inputs['InpSizingMode'] -eq '1') 'hourly balance percent' }
            } else {
                Assert ([double]$inputs['InpPortfolioFixedUSD'] -eq $amount -and $inputs['InpPortfolioRiskMode'] -eq '1') 'true fixed cash allocation'
                if ($item.Hourly) { Assert ($inputs['InpSizingMode'] -eq '2' -and [double]$inputs['InpFixedRiskMoney'] -eq $amount) 'hourly fixed cash' }
            }
            $base=Read-SetInputs $item.SetFullPath
            $allowed=@('InpRiskPercent','InpPortfolioRiskMode','InpPortfolioFixedUSD','InpPortfolioExpectedLogin','InpPortfolioExpectedServer','InpPortfolioExpectedSymbol','InpPortfolioInstallNonce','InpSizingMode','InpFixedRiskMoney','InpAllowRealAccount','InpAdaptivePortfolioControls')
            foreach ($key in $base.Keys) { if ($key -notin $allowed) { Assert ($inputs[$key] -ceq $base[$key]) "unchanged rule $($item.Key).$key" } }
        }
    }
}
foreach ($amount in @(0,-1,[double]::NaN,[double]::PositiveInfinity)) { Reject { Assert-Risk 'FIXED_USD' $amount } 'bad cash rejected'; Reject { Assert-Risk 'PERCENT' $amount } 'bad percentage rejected' }
Reject { Assert-Risk 'PERCENT' 10.01 } 'above max percent rejected'
Reject { Assert-Risk 'OTHER' 1 } 'invalid mode rejected'
$probe.account.currency='EUR'; Reject { Assert-Account $probe $candidate 'FIXED_USD' } 'USD currency enforced'
Assert-Account $probe $candidate 'PERCENT'; Assert $true 'non-USD percentage allowed'
$probe.account.currency='USD'; $probe.account.margin_mode=0; Reject { Assert-Account $probe $candidate 'PERCENT' } 'netting rejected'; $probe.account.margin_mode=2
$probe.account.trade_allowed=$false; Reject { Assert-Account $probe $candidate 'PERCENT' } 'read-only trading rejected'; $probe.account.trade_allowed=$true
$probe.terminal.data_path='C:\OtherData'; Reject { Assert-Account $probe $candidate 'PERCENT' } 'wrong API terminal data path rejected'; $probe.terminal.data_path=$candidate.DataRoot
$originalSymbols=$probe.symbols; $probe.symbols=@($probe.symbols | Where-Object { $_.name -ne 'XAUUSDm' }); Reject { Get-Portfolio $package $probe } 'missing asset fails whole portfolio'; $probe.symbols=$originalSymbols
Reject { Assert-ChildPath $PackageRoot (Join-Path $PackageRoot '..\escape') } 'path traversal rejected'
$testRoot=Assert-ChildPath $PackageRoot (Join-Path $PackageRoot ('NativeTests\offline-'+[guid]::NewGuid().ToString('N')))
[void](New-Item -Path $testRoot -ItemType Directory)
$RiskMode='FIXED_USD'; $RiskValue=50.0
for ($index=0; $index -lt $portfolio.Count; $index++) {
    $item=$portfolio[$index]
    [IO.File]::WriteAllText((Join-Path $testRoot ('chart{0:D2}.chr' -f ($index+1))), (New-ChartText $item $item.BrokerSymbol (1000+$index) $index), [Text.Encoding]::Unicode)
}
Assert-ChartInputs $testRoot $portfolio; Assert $true 'all five offline charts and full inputs verified'
$chart=Join-Path $testRoot 'chart03.chr'
$text=Get-Content -LiteralPath $chart -Raw
[IO.File]::WriteAllText($chart, $text.Replace('InpPortfolioFixedUSD=50','InpPortfolioFixedUSD=51'), [Text.Encoding]::Unicode)
Reject { Assert-ChartInputs $testRoot $portfolio } 'corrupt chart risk rejected'
# No account/terminal action even if those calls were accidentally added to ValidateOnly.
function Get-CimInstance { throw 'Live enumeration forbidden by offline tests.' }
function Invoke-AccountProbe { throw 'Live API forbidden by offline tests.' }
$mainNode=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Main'}, $true)
. ([scriptblock]::Create($mainNode.Extent.Text))
$ValidateOnly=$true
Main
Assert $true 'ValidateOnly completed without enumeration or API'
Write-Host "PASS: $Checks offline risk, account, symbol, chart and preservation checks. No MT5 account was accessed." -ForegroundColor Green
@{checks=$Checks; offline_pass=$true; no_live_account_access=$true; utc=[DateTime]::UtcNow.ToString('o')} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PackageRoot 'TESTS.json') -Encoding UTF8
