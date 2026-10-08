$ErrorActionPreference='Stop'
$PackageRoot=$PSScriptRoot
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot 'Install-FivePortfolio.ps1'),[ref]$null,[ref]$null)
foreach ($node in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -notin @('Main','Stop-WithMessage')},$true)) { . ([scriptblock]::Create($node.Extent.Text)) }
$main=$ast.Find({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -eq 'Main'},$true).Extent.Text
$main=$main.Replace('function Main {','function Invoke-MockMain {').Replace(". (Join-Path `$PackageRoot 'Installer-Helpers.ps1')",'. $MockHelperPath')
. ([scriptblock]::Create($main))
$root=Assert-ChildPath $PackageRoot (Join-Path $PackageRoot ('NativeTests\transaction-'+[guid]::NewGuid().ToString('N')))
[void](New-Item -Path $root -ItemType Directory)
$MockHelperPath=Join-Path $root 'Mocks.ps1'
$mockCode=@'
function Get-Mt5Candidates { return $MockCandidate }
function Assert-RunningTerminal { }
function Invoke-AccountProbe { return $MockProbe }
function Close-TargetTerminal { $script:Closed++ }
function Start-Profile([string]$Terminal,[string]$Name) {
    $script:Started+=@($Name)
    if ($Name -ne 'Calyx FIVE EA PORTFOLIO') { return }
    if ($MockMode -eq 'FAIL') { throw 'Injected restart failure - offline test' }
    foreach ($item in $portfolio) {
        $cash=if($RiskMode -eq 'FIXED_USD'){$RiskValue}else{50.0}
        $mode=if($RiskMode -eq 'FIXED_USD'){'1'}else{'0'}
        $parts=@([DateTimeOffset]::UtcNow.ToUnixTimeSeconds(),$ActiveLogin,$ActiveServer,$item.BrokerSymbol,$item.Magic,$InstallNonce,$mode,$cash)
        [IO.File]::WriteAllText((Join-Path $MockProbe.terminal.commondata_path "Files\CalyxFivePortfolio-$($item.Magic).tsv"),($parts -join "`t")+"`n")
    }
}
'@
$helpers=Get-Content -LiteralPath (Join-Path $PackageRoot 'Installer-Helpers.ps1') -Raw
[IO.File]::WriteAllText($MockHelperPath,$helpers+"`n"+$mockCode,[Text.UTF8Encoding]::new($false))
$checks=0
foreach ($MockMode in @('SUCCESS','FAIL')) {
    $data=Join-Path $root $MockMode
    $common=Join-Path $data 'Common'
    [void](New-Item -Path (Join-Path $common 'Files') -ItemType Directory -Force)
    $profile='Calyx FIVE EA PORTFOLIO'
    $managed=@("MQL5\Experts\$profile","MQL5\Profiles\Tester\$profile","MQL5\Profiles\Charts\$profile")
    foreach ($relative in $managed) {
        $directory=Join-Path $data $relative
        [void](New-Item -Path $directory -ItemType Directory -Force)
        [IO.File]::WriteAllText((Join-Path $directory 'previous-owned-file.txt'),'preserved original')
    }
    $untouched=Join-Path $data 'MQL5\Profiles\Charts\Unrelated User Profile'
    [void](New-Item -Path $untouched -ItemType Directory -Force)
    [IO.File]::WriteAllText((Join-Path $untouched 'user.txt'),'do not change')
    $MockCandidate=[pscustomobject]@{Path='C:\Mock MT5\terminal64.exe';DataRoot=$data;Running=$true;ProcessIds=@(999999)}
    $MockProbe=[pscustomobject]@{
        ok=$true
        terminal=[pscustomobject]@{connected=$true;path='C:\Mock MT5';data_path=$data;commondata_path=$common}
        account=[pscustomobject]@{login='12345';server='Mock-Broker';currency='USD';margin_mode=2;balance=10000;equity=10000;trade_allowed=$true;open_positions=0}
        symbols=@('US30m','USTECm','XAUUSDm'|ForEach-Object{[pscustomobject]@{name=$_;path='CFD';trade_mode=4;visible=$true}})
    }
    $RiskMode='FIXED_USD';$RiskValue=50.0;$TargetTerminal='';$Yes=$true;$ValidateOnly=$false;$PreflightOnly=$false;$Closed=0;$Started=@()
    $rejected=$false
    try { Invoke-MockMain } catch { if ($_.Exception.Message -notlike 'Injected restart*') { throw };$rejected=$true }
    if ((Get-Content -LiteralPath (Join-Path $untouched 'user.txt') -Raw) -ne 'do not change') { throw 'Unrelated profile changed' };$checks++
    if ($MockMode -eq 'SUCCESS') {
        if ($rejected -or $Closed -ne 1 -or $Started.Count -ne 1) { throw 'Wrong successful restart sequence' };$checks++
        if (@(Get-ChildItem -LiteralPath (Join-Path $data $managed[0]) -Filter '*.ex5').Count -ne 5) { throw 'Five EA binaries missing' };$checks++
        if (@(Get-ChildItem -LiteralPath (Join-Path $data $managed[1]) -Filter '*.set').Count -ne 5) { throw 'Five installed SET files missing' };$checks++
        if (@(Get-ChildItem -LiteralPath (Join-Path $data $managed[2]) -Filter '*.chr').Count -ne 5) { throw 'Five charts missing' };$checks++
        $receipts=@(Get-ChildItem -LiteralPath (Join-Path $data 'MQL5\Profiles\CalyxFiveSetup') -Filter 'Receipt.json' -Recurse)
        $receipt=Get-Content -LiteralPath $receipts[0].FullName -Raw|ConvertFrom-Json
        if ($receipt.Status -ne 'All five initialized' -or $receipt.RiskValue -ne 50) { throw 'Bad installation receipt' };$checks++
        foreach ($relative in $managed) {
            $name=@{ $managed[0]='Experts';$managed[1]='Settings';$managed[2]='Charts'}[$relative]
            if ((Get-Content -LiteralPath (Join-Path $receipt.Backups "Backup-$name\previous-owned-file.txt") -Raw) -ne 'preserved original') { throw 'Backup lost' };$checks++
        }
    } else {
        if (-not $rejected -or $Closed -ne 2 -or $Started.Count -ne 2 -or $Started[1] -ne 'Default') { throw 'Recovery/restart sequence wrong' };$checks++
        foreach ($relative in $managed) { if ((Get-Content -LiteralPath (Join-Path $data "$relative\previous-owned-file.txt") -Raw) -ne 'preserved original') { throw 'Recovery failed' };$checks++ }
    }
}
Write-Host "PASS: $checks offline end-to-end install/backup/initialization/rollback checks; no real MT5/API/process used." -ForegroundColor Green
@{passed=$true;checks=$checks;real_processes_used=$false;real_account_accessed=$false} | ConvertTo-Json | Set-Content -LiteralPath (Join-Path $PackageRoot 'TRANSACTION-TESTS.json') -Encoding UTF8
