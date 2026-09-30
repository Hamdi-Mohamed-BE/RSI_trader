$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$env:CALYX_LIBRARY_ONLY='1';$env:CALYX_BUNDLE_FILE=Join-Path (Split-Path -Parent (Split-Path -Parent $root)) 'top 5\Install Top 5.bat'
. (Join-Path $root 'installer.generated.ps1')
function Get-CimInstance { [pscustomobject]@{CommandLine='"C:\MT5\terminal64.exe"'} }
function Read-Choice($Prompt,$Count){return 0}
$target=[pscustomobject]@{Exe='C:\MT5\terminal64.exe';Data='C:\unused';Running=$true}
$p=[pscustomobject]@{Path=$target.Exe;Id=123}
if((Get-OnlyActiveTarget @($target) @($p)).Exe -ne $target.Exe){throw 'Single terminal detection failed'}
foreach($processes in @(@(),@($p,$p))){$blocked=$false;try{$null=Get-OnlyActiveTarget @($target) $processes}catch{$blocked=$true};if(!$blocked){throw 'Ambiguous terminal accepted'}}
$second=[pscustomobject]@{Exe='C:\Second MT5\terminal64.exe';Data='C:\other';Running=$true}
$p2=[pscustomobject]@{Path=$second.Exe;Id=456;MainWindowTitle='Second broker demo'}
function Read-Choice($Prompt,$Count){if($Count -ne 2){throw 'Expected two terminals'};return 1}
if((Get-OnlyActiveTarget @($target,$second) @($p,$p2)).Exe -ne $second.Exe){throw 'Chosen terminal not honored'}
function Read-Choice($Prompt,$Count){return 0}
if((Get-OnlyActiveTarget @($target) @($p,$p2)).Exe -ne $target.Exe){throw 'Unrelated terminal should not block selected terminal'}
function Get-CimInstance { [pscustomobject]@{CommandLine='terminal64.exe /portable'} }
$blocked=$false;try{$null=Get-OnlyActiveTarget @($target) @($p)}catch{$blocked=$true};if(!$blocked){throw 'Portable process accepted'}
# Stub the already-tested classifier to focus on automatic ambiguity handling.
$fixture=Join-Path $root ('recovery-fixture-'+[Guid]::NewGuid().ToString('N'))
$dir=Join-Path $fixture 'MQL5\Files\CalyxTop5';$null=New-Item -ItemType Directory -Path $dir -Force
$cfgDir=Join-Path $fixture 'config';$null=New-Item -ItemType Directory -Path $cfgDir -Force
[IO.File]::WriteAllText((Join-Path $cfgDir 'common.ini'),"[Charts]`r`nProfileLast=Original`r`n",[Text.Encoding]::Unicode)
$config=Join-Path $dir 'startup-0123456789abcdef0123456789abcdef.ini'
$content="[Charts]`r`nProfileLast=Original`r`n[StartUp]`r`nScript=CalyxTop5\Detect Broker Symbols`r`nSymbol=XAUUSDr`r`nPeriod=M1`r`nShutdownTerminal=0`r`n"
[IO.File]::WriteAllText($config,$content,[Text.Encoding]::Unicode)
$command='terminal64.exe /config:"'+$config+'"'
if(!(Test-CalyxRecoveryConfig $command $fixture)){throw 'Our recovery config rejected'}
if(Test-CalyxRecoveryConfig ($command+' /config:other.ini') $fixture){throw 'Multiple configs accepted'}
[IO.File]::WriteAllText($config,($content+"[Experts]`r`nAllowLiveTrading=1`r`n"),[Text.Encoding]::Unicode)
if(Test-CalyxRecoveryConfig $command $fixture){throw 'Trading override accepted'}
[IO.File]::WriteAllText($config,($content.Replace('Original','Other')),[Text.Encoding]::Unicode)
if(Test-CalyxRecoveryConfig $command $fixture){throw 'Mismatched profile accepted'}
function Find-SymbolCandidates($Rows,$Canonical){$Rows|Where-Object{$_.canonical -eq $Canonical}}
$g=[pscustomobject]@{canonical='XAUUSD';name='GOLD';selected='1'}
$n=[pscustomobject]@{canonical='USTEC';name='US100';selected='1'}
$n2=[pscustomobject]@{canonical='USTEC';name='NAS100';selected='0'}
$map=Select-AutomaticSymbols @($g,$n,$n2)
if($map.USTEC -ne 'US100' -or $map.XAUUSD -ne 'GOLD'){throw 'Market Watch preference failed'}
$n2.selected='1';$blocked=$false;try{$null=Select-AutomaticSymbols @($g,$n,$n2)}catch{$blocked=$true};if(!$blocked){throw 'Ambiguous symbols accepted'}
$blocked=$false;try{$null=Select-AutomaticSymbols @($g)}catch{$blocked=$true};if(!$blocked){throw 'Missing instrument accepted'}
$main=(Get-Command Main).Definition
if(([regex]::Matches($main,'Read-Host')).Count -ne 3 -or ([regex]::Matches($main,'Read-Choice')).Count -ne 1){throw 'Expected risk amount and two symbol prompts'}
if($main -match 'Discover-Automatically|Discover-BrokerSymbols'){throw 'Manual symbol mode must never invoke the detector'}
if($main -match 'USD HEDGING.+Read-Host|Type APPLY|Choose the MT5'){throw 'Old onboarding prompts remain'}
foreach($fn in @('Discover-Automatically','Close-SelectedTerminal','Read-SavedContext','Select-AutomaticSymbols')){if((Get-Command $fn).Definition -match 'Read-Host|Read-Choice|Stop-Process'){throw "Interactive or forced-close path: $fn"}}
Write-Host 'PASS: automatic terminal preflight, unsupported process rejection, risk and two symbol prompts, detector bypassed, no force-kill.'
