$ErrorActionPreference='Stop'
$PackageRoot=$PSScriptRoot
$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PackageRoot 'Install-Portfolio.ps1'),[ref]$null,[ref]$errors)
if($errors.Count){throw ($errors.Message -join '; ')}
foreach($node in $ast.FindAll({param($n) $n -is [Management.Automation.Language.FunctionDefinitionAst] -and $n.Name -notin @('Main','Stop-WithMessage')},$true)){. ([scriptblock]::Create($node.Extent.Text))}
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
function Read-Host([string]$Prompt) {
 if($MockMode -eq 'DEFAULTS' -and $Prompt -match 'Risk mode|Percentage per trade|DI filter'){return ''}
 throw "Unexpected interactive prompt in offline test: $Prompt"
}
function Start-Profile([string]$Terminal,[string]$Name) {
 $script:Started+=@($Name)
 if($Name -ne 'Calyx CURRENT14 ORB05'){return}
 if($MockMode -eq 'FAIL'){throw 'Injected restart failure - offline test'}
 foreach($item in $portfolio){
  $cash=if($RiskMode -eq 'FIXED_USD'){$RiskValue}else{50.0};$mode=if($RiskMode -eq 'FIXED_USD'){'1'}else{'0'}
  $parts=@([DateTimeOffset]::UtcNow.ToUnixTimeSeconds(),$ActiveLogin,$ActiveServer,$item.BrokerSymbol,$item.Magic,$InstallNonce,$mode,$cash)
  [IO.File]::WriteAllText((Join-Path $MockProbe.terminal.commondata_path "Files\CalyxCurrent14ORB05-$($item.Magic).tsv"),($parts -join "`t")+"`n")
 }
}
'@
$helpers=Get-Content -LiteralPath (Join-Path $PackageRoot 'Installer-Helpers.ps1') -Raw
[IO.File]::WriteAllText($MockHelperPath,$helpers+"`n"+$mockCode,[Text.UTF8Encoding]::new($false))
$checks=0
foreach($MockMode in @('SUCCESS','FAIL','DEFAULTS')){
 $data=Join-Path $root $MockMode;$common=Join-Path $data 'Common'
 [void](New-Item -Path (Join-Path $common 'Files') -ItemType Directory -Force)
 $profile='Calyx CURRENT14 ORB05';$managed=@("MQL5\Experts\$profile","MQL5\Profiles\Tester\$profile","MQL5\Profiles\Charts\$profile")
 foreach($relative in $managed){$dir=Join-Path $data $relative;[void](New-Item -Path $dir -ItemType Directory -Force);[IO.File]::WriteAllText((Join-Path $dir 'previous-owned-file.txt'),'preserved original')}
 $untouched=Join-Path $data 'MQL5\Profiles\Charts\Unrelated User Profile'
 [void](New-Item -Path $untouched -ItemType Directory -Force);[IO.File]::WriteAllText((Join-Path $untouched 'user.txt'),'do not change')
 $MockCandidate=[pscustomobject]@{Path='C:\Mock MT5\terminal64.exe';DataRoot=$data;Running=$true;ProcessIds=@(999999)}
 $MockProbe=[pscustomobject]@{
  terminal=[pscustomobject]@{connected=$true;path='C:\Mock MT5';data_path=$data;commondata_path=$common}
  account=[pscustomobject]@{login='12345';server='Mock-Broker';currency='EUR';margin_mode=2;balance=15000;equity=15000;trade_allowed=$true;open_positions=0}
  symbols=@('USDJPYm','USTECm','XAUUSDm'|ForEach-Object{[pscustomobject]@{name=$_;path='CFD';trade_mode=4;visible=$true}})
 }
 $RiskMode='PERCENT';$RiskValue=1.5;$NasdaqDIFilter='OFF';$UsdJpyDIFilter='ON';$TargetTerminal='';$Yes=$true;$ValidateOnly=$false;$PreflightOnly=$false;$Closed=0;$Started=@()
 if($MockMode -eq 'DEFAULTS'){$RiskMode='';$RiskValue=0;$NasdaqDIFilter='';$UsdJpyDIFilter=''}
 $rejected=$false
 try{Invoke-MockMain}catch{if($_.Exception.Message -notlike 'Injected restart*'){throw};$rejected=$true}
 if((Get-Content -LiteralPath (Join-Path $untouched 'user.txt') -Raw) -ne 'do not change'){throw 'Unrelated profile changed'};$checks++
 if($MockMode -ne 'FAIL'){
  if($rejected -or $Closed -ne 1 -or $Started.Count -ne 1){throw 'Wrong success restart sequence'};$checks++
  foreach($i in @(0,1,2)){$filter=@('*.ex5','*.set','*.chr')[$i];if(@(Get-ChildItem -LiteralPath (Join-Path $data $managed[$i]) -Filter $filter).Count -ne 15){throw 'Missing portfolio files'};$checks++}
  $receipts=@(Get-ChildItem -LiteralPath (Join-Path $data 'MQL5\Profiles\CalyxCurrent14ORB05Setup') -Filter Receipt.json -Recurse)
  $receipt=Get-Content -LiteralPath $receipts[0].FullName -Raw|ConvertFrom-Json
  $expectedRisk=if($MockMode -eq 'DEFAULTS'){0.5}else{1.5};$expectedNasdaqDI=if($MockMode -eq 'DEFAULTS'){'ON'}else{'OFF'}
  if($receipt.Status -ne 'All selected initialized' -or $receipt.RiskValue -ne $expectedRisk -or $receipt.NasdaqDI -ne $expectedNasdaqDI -or $receipt.UsdJpyDI -ne 'ON'){throw 'Bad receipt'};$checks++
  foreach($name in @('Experts','Settings','Charts')){if((Get-Content -LiteralPath (Join-Path $receipt.Backups "Backup-$name\previous-owned-file.txt") -Raw) -ne 'preserved original'){throw 'Backup lost'};$checks++}
 }else{
  if(-not $rejected -or $Closed -ne 2 -or $Started.Count -ne 2 -or $Started[1] -ne 'Default'){throw 'Wrong recovery sequence'};$checks++
  foreach($relative in $managed){if((Get-Content -LiteralPath (Join-Path $data "$relative\previous-owned-file.txt") -Raw) -ne 'preserved original'){throw 'Recovery failed'};$checks++}
 }
}
@{passed=$true;checks=$checks;live_account_access=$false;real_processes_used=$false}|ConvertTo-Json|Set-Content -LiteralPath (Join-Path $PackageRoot 'TRANSACTION-TESTS.json') -Encoding UTF8
Write-Host "PASS: $checks simulated end-to-end installation, initialization, backup and rollback checks."
