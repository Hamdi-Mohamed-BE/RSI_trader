[CmdletBinding()]
param([int]$TimeoutSeconds=1800)

Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$packageRoot=Split-Path -Parent $root
$testerRoot=Join-Path $packageRoot '_Backtests\MT5-DMC-20260811'
$terminal=Join-Path $testerRoot 'terminal64.exe'
$config=Join-Path $testerRoot 'backtest-configs\active-bat-20260812\09-ninja-turtle-scalper.ini'
$report=Join-Path $testerRoot 'reports\active-bat-20260812\09-ninja-turtle-scalper.htm'
$output=Join-Path $root 'MT5 Reports'
Remove-Item -LiteralPath $report -Force -ErrorAction SilentlyContinue
Get-ChildItem -LiteralPath (Split-Path -Parent $report) -Filter '09-ninja-turtle-scalper*.png' -ErrorAction SilentlyContinue | Remove-Item -Force
$process=Start-Process -FilePath $terminal -ArgumentList @('/portable',('/config:"'+$config+'"')) -PassThru -WindowStyle Hidden
try{Wait-Process -Id $process.Id -Timeout $TimeoutSeconds -ErrorAction Stop}catch{Stop-Process -Id $process.Id -Force -ErrorAction SilentlyContinue;throw 'Ninja retest timed out.'}
if(-not (Test-Path -LiteralPath $report)){throw 'Ninja retest did not create a report.'}
Get-ChildItem -LiteralPath (Split-Path -Parent $report) -Filter '09-ninja-turtle-scalper*' | Copy-Item -Destination $output -Force
