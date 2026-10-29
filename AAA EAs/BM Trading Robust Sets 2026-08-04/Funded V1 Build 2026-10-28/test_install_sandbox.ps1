# Sandbox test of Packages/FundedV1/Install-FundedV1.ps1 (adapted from the Turbo5 sandbox test): runs the real installer statements against a
# FAKE terminal data folder. Replaced only: terminal discovery, the python account probe (fixture JSON), Close-TargetTerminal, Start-Process,
# the typed confirmation, and (run 2) Read-Host with a scripted answer list. Never touches a real MT5 terminal or account.
$ErrorActionPreference='Stop'
$pkg='C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\BM Trading Robust Sets 2026-08-04\_00 Live profiles\Packages\FundedV1'
$sandbox=Join-Path $env:TEMP ('fundedv1-sandbox-'+[guid]::NewGuid().ToString('N').Substring(0,8))
$data=Join-Path $sandbox 'data'
New-Item -ItemType Directory -Force -Path (Join-Path $data 'MQL5\Experts'),(Join-Path $data 'MQL5\Profiles\Charts'),(Join-Path $data 'MQL5\Profiles\Tester'),(Join-Path $data 'MQL5\Files'),(Join-Path $data 'config') | Out-Null
Set-Content -LiteralPath (Join-Path $data 'config\common.ini') -Value "[Experts]`r`nEnabled=1`r`n[Charts]`r`nProfileLast=Default`r`n" -Encoding Unicode
$probe=[ordered]@{ok=$true;snapshot_utc=[long](([DateTimeOffset]::UtcNow).ToUnixTimeSeconds());
    account=[ordered]@{login=185928;server='Leveraged-Demo';company='Fixture Broker';currency='USD';balance=50000.0;equity=50000.0;leverage=30;margin_mode=2;trade_allowed=$true;trade_expert=$true};
    terminal=[ordered]@{path='C:\fake\terminal64.exe';data_path=$data;connected=$true;trade_allowed=$false};positions=0;orders=0;
    symbols=@([ordered]@{name='XAUUSD';path='Metals\XAUUSD';visible=$true;trade_mode=4;volume_min=0.01;volume_max=100;volume_step=0.01;trade_contract_size=100},
              [ordered]@{name='NAS100';path='Indices\NAS100';visible=$true;trade_mode=4;volume_min=0.1;volume_max=100;volume_step=0.1;trade_contract_size=1})}
$probeFile=Join-Path $sandbox 'probe.json'; ($probe | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $probeFile -Encoding UTF8
$src=Get-Content -Raw -LiteralPath (Join-Path $pkg 'Install-FundedV1.ps1')
$reps=@(
 @('$candidates=@(Get-Mt5Candidates | Where-Object {$_.Running -and $_.Path -notmatch ''(?i)\\(_Backtests|Tester|temp)\\''})', '$candidates=@([pscustomobject]@{Path=''C:\fake\terminal64.exe'';Running=$true})'),
 @('$selected=Select-Mt5Candidate $candidates', '$selected=$candidates[0]'),
 @('$python=(Get-Command python.exe -ErrorAction Stop).Source', '$python=$null'),
 @('$probeText=(& $python (Join-Path $PSScriptRoot ''probe_account.py'') --terminal $terminalPath) -join "`n"', ('$probeText=Get-Content -Raw -LiteralPath '''+$probeFile+''';$global:LASTEXITCODE=0')),
 @('$confirmationText=(& $python (Join-Path $PSScriptRoot ''probe_account.py'') --terminal $terminalPath) -join "`n"', ('$confirmationText=Get-Content -Raw -LiteralPath '''+$probeFile+''';$global:LASTEXITCODE=0')),
 @('if((Read-Host "Type exactly: $expected") -cne $expected)', 'if($expected -cne $expected)'),
 @('Close-TargetTerminal $terminalPath', '# sandbox: terminal not closed'),
 @('Start-Process -FilePath $terminalPath -ArgumentList (''/profile:"''+$ProfileName+''"'') -WindowStyle Hidden', '# sandbox: terminal not started'))
foreach($r in $reps){ if(-not $src.Contains($r[0])){throw "sandbox anchor missing: $($r[0])"}; $src=$src.Replace($r[0],$r[1]) }
# Run 2 answers, in prompt order: size, max loss, trail type, lock, firm daily, reset hour, basis, dashboard floor, risk, taper, open, symbol,
# daily loss, daily win, buffer, news minutes, news pending, Nasdaq DI.
$scripted='$global:FV1Answers=[System.Collections.Queue]::new(@("50000","6","0","Y","3","0","1","","0.3","5","1.5","1","1.5","1","0.3","10","N","ON"))'+"`r`n"+
          'function Read-Host([string]$Prompt){if($global:FV1Answers -and $global:FV1Answers.Count){return $global:FV1Answers.Dequeue()};throw "unexpected prompt: $Prompt"}'+"`r`n"
$copy=Join-Path $pkg ('_sandbox-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.ps1')
$copy2=Join-Path $pkg ('_sandbox2-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.ps1')
Set-Content -LiteralPath $copy -Value $src -Encoding UTF8
$i=$src.IndexOf('Set-StrictMode'); Set-Content -LiteralPath $copy2 -Value ($src.Substring(0,$i)+$scripted+$src.Substring($i)) -Encoding UTF8
function Get-Set([string]$profileName,[string]$like){
    $f=@(Get-ChildItem (Join-Path $data ('MQL5\Profiles\Tester\'+$profileName)) -Filter *.set | Where-Object Name -like $like)
    if($f.Count -ne 1){throw "set $like missing"}; return Get-Content -Raw -LiteralPath $f[0].FullName
}
try {
    # Run 1: all defaults, Nasdaq DI OFF.
    & $copy -UseDefaults -NasdaqDIFilter OFF
    $p1=@(Get-ChildItem (Join-Path $data 'MQL5\Profiles\Charts') -Directory | Where-Object Name -like 'Calyx-FundedV1-185928-*')
    if($p1.Count -ne 1){throw 'profile folder missing'}
    $charts=@(Get-ChildItem $p1[0].FullName -Filter 'chart*.chr'); if($charts.Count -ne 9){throw "expected 9 charts, got $($charts.Count)"}
    $ex=@(Get-ChildItem (Join-Path $data ('MQL5\Experts\'+$p1[0].Name)) -Filter *.ex5); if($ex.Count -ne 8){throw "expected 8 distinct EX5 (the two ORBs share one), got $($ex.Count)"}
    $sets=@(Get-ChildItem (Join-Path $data ('MQL5\Profiles\Tester\'+$p1[0].Name)) -Filter *.set); if($sets.Count -ne 9){throw 'expected 9 SETs'}
    foreach($s in $sets){
        $t=Get-Content -Raw -LiteralPath $s.FullName
        foreach($need in @('FundedGuardMode=1','FundedExpectedLogin=185928','FundedExpectedServer=Leveraged-Demo','FundedExpectedCurrency=USD','FundedAccountSize=50000',
                           'FundedReferenceBalance=50000','FundedRiskPercent=0.5','FundedRoomTaperPercent=5','FundedMaxOpenRiskPercent=2','FundedMaxSymbolRiskPercent=1.5',
                           'FundedMaxDailyLossPercent=2','FundedMaxDailyWinPercent=0.75','FundedMaxLossPercent=6','FundedTrailMode=0','FundedLockAtInitial=true',
                           'FundedBufferPercent=0.25','FundedFirmDailyPercent=3','FundedDayResetUtcHour=0','FundedDailyBasis=1','FundedNewsBlackoutMinutes=5','InpRiskPercent=0.75')){
            if(-not $t.Contains($need)){throw "$($s.Name) missing $need"}
        }
        if($t -notmatch 'FundedStartUtcTime=\d{10}'){throw "$($s.Name) start time not armed"}
        if($t -notmatch 'FundedExpectedSymbol=(XAUUSD|NAS100)'){throw "$($s.Name) symbol not bound"}
    }
    if((Get-Set $p1[0].Name '*Nasdaq 5M*') -notmatch 'InpRequireDIAgreement=false'){throw 'DI OFF not applied'}
    if((Get-Set $p1[0].Name '*Volume Confirmed*') -notmatch 'InpRewardRisk=0\.5'){throw 'Volume Confirmed lost 0.5R'}
    if((Get-Set $p1[0].Name '*London NY*') -notmatch 'InpRewardRisk=0\.5'){throw 'London-NY ORB lost 0.5R'}
    if((Get-Set $p1[0].Name '*Nasdaq 5M*') -notmatch 'FundedExpectedSymbol=NAS100'){throw 'Nasdaq alias NAS100 not resolved'}
    $state=@(Get-ChildItem (Join-Path $data 'MQL5\Files') -Filter 'Calyx-FundedV1-185928-*.json'); if($state.Count -ne 1){throw 'state file missing'}
    $ini=Get-Content -Raw -LiteralPath (Join-Path $data 'config\common.ini')
    if($ini -notmatch 'Enabled=0' -or $ini -notmatch [regex]::Escape('ProfileLast='+$p1[0].Name)){throw 'common.ini not updated (Algo OFF / profile)'}
    $first=Get-Content -Raw -LiteralPath $state[0].FullName | ConvertFrom-Json
    Start-Sleep -Seconds 1
    # Run 2: typed answers through every prompt.
    & $copy2
    $p2=@(Get-ChildItem (Join-Path $data 'MQL5\Profiles\Charts') -Directory | Where-Object Name -like 'Calyx-FundedV1-185928-*' | Sort-Object Name)
    if($p2.Count -ne 2){throw 'rerun did not create a new profile'}
    $t=Get-Set $p2[1].Name '*RSI VWAP*'
    foreach($need in @('FundedRiskPercent=0.3','FundedMaxOpenRiskPercent=1.5','FundedMaxSymbolRiskPercent=1','FundedMaxDailyLossPercent=1.5','FundedMaxDailyWinPercent=1',
                       'FundedBufferPercent=0.3','FundedNewsBlackoutMinutes=10','InpRiskPercent=0.45')){ if(-not $t.Contains($need)){throw "typed answer not applied: $need"} }
    if((Get-Set $p2[1].Name '*Nasdaq 5M*') -notmatch 'InpRequireDIAgreement=true'){throw 'DI ON not applied'}
    $second=Get-Content -Raw -LiteralPath $state[0].FullName | ConvertFrom-Json
    if($first.start_utc -ne $second.start_utc -or $first.reference_balance -ne $second.reference_balance){throw 'rerun changed the saved baseline'}
    Write-Host 'SANDBOX PASS: defaults run (9 charts / 8 EX5 / 9 armed SETs, DI OFF, both ORBs 0.5R, NAS100 alias, Algo OFF, state saved) + typed-answers run (all prompts applied, DI ON, baseline kept). No real terminal touched.'
} catch { Write-Host ("FAIL: "+$_.Exception.Message); Write-Host $_.InvocationInfo.PositionMessage; Write-Host $_.ScriptStackTrace; exit 1 } finally { Remove-Item -LiteralPath $copy,$copy2 -Force; Remove-Item -LiteralPath $sandbox -Recurse -Force }
