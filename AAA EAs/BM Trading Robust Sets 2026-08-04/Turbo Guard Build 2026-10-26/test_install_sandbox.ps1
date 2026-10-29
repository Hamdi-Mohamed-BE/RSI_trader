# Sandbox test of Packages/Turbo5/Install-Turbo5.ps1: runs the real installer statements against a FAKE terminal data folder.
# Replaced only: terminal discovery, the python account probe (fixture JSON), Close-TargetTerminal, Start-Process and the typed prompts.
# Never touches a real MT5 terminal or account.
$ErrorActionPreference='Stop'
$pkg='C:\Users\hama101\Desktop\geek\ai trader\AAA EAs\BM Trading Robust Sets 2026-08-04\_00 Live profiles\Packages\Turbo5'
$sandbox=Join-Path $env:TEMP ('turbo5-sandbox-'+[guid]::NewGuid().ToString('N').Substring(0,8))
$data=Join-Path $sandbox 'data'
New-Item -ItemType Directory -Force -Path (Join-Path $data 'MQL5\Experts'),(Join-Path $data 'MQL5\Profiles\Charts'),(Join-Path $data 'MQL5\Profiles\Tester'),(Join-Path $data 'MQL5\Files'),(Join-Path $data 'config') | Out-Null
Set-Content -LiteralPath (Join-Path $data 'config\common.ini') -Value "[Experts]`r`nEnabled=1`r`n[Charts]`r`nProfileLast=Default`r`n" -Encoding Unicode
$probe=[ordered]@{ok=$true;snapshot_utc=[long](([DateTimeOffset]::UtcNow).ToUnixTimeSeconds());
    account=[ordered]@{login=12345678;server='Turbo-Demo';company='Fixture Broker';currency='USD';balance=50000.0;equity=50000.0;leverage=30;margin_mode=2;trade_allowed=$true;trade_expert=$true};
    terminal=[ordered]@{path='C:\fake\terminal64.exe';data_path=$data;connected=$true;trade_allowed=$false};positions=0;orders=0;
    symbols=@([ordered]@{name='XAUUSD';path='Metals\XAUUSD';visible=$true;trade_mode=4;volume_min=0.01;volume_max=100;volume_step=0.01;trade_contract_size=100},
              [ordered]@{name='USTEC';path='Indices\USTEC';visible=$true;trade_mode=4;volume_min=0.01;volume_max=100;volume_step=0.01;trade_contract_size=1})}
$probeFile=Join-Path $sandbox 'probe.json'; ($probe | ConvertTo-Json -Depth 6) | Set-Content -LiteralPath $probeFile -Encoding UTF8
$src=Get-Content -Raw -LiteralPath (Join-Path $pkg 'Install-Turbo5.ps1')
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
$copy=Join-Path $pkg ('_sandbox-'+[guid]::NewGuid().ToString('N').Substring(0,8)+'.ps1')
Set-Content -LiteralPath $copy -Value $src -Encoding UTF8
try {
    & $copy -AccountSize 50000 -KnownFloor 0 -TrailEquity N
    $profile=@(Get-ChildItem (Join-Path $data 'MQL5\Profiles\Charts') -Directory | Where-Object Name -like 'Calyx-Turbo5-12345678-*')
    if($profile.Count -ne 1){throw 'profile folder missing'}
    $charts=@(Get-ChildItem $profile[0].FullName -Filter 'chart*.chr'); if($charts.Count -ne 5){throw "expected 5 charts, got $($charts.Count)"}
    $ex=@(Get-ChildItem (Join-Path $data ('MQL5\Experts\'+$profile[0].Name)) -Filter *.ex5); if($ex.Count -ne 5){throw 'expected 5 EX5'}
    $sets=@(Get-ChildItem (Join-Path $data ('MQL5\Profiles\Tester\'+$profile[0].Name)) -Filter *.set); if($sets.Count -ne 5){throw 'expected 5 SETs'}
    foreach($s in $sets){
        $t=Get-Content -Raw -LiteralPath $s.FullName
        foreach($need in @('TurboGuardMode=1','TurboExpectedLogin=12345678','TurboExpectedServer=Turbo-Demo','TurboExpectedCurrency=USD','TurboAccountSize=50000','TurboReferenceBalance=50000','TurboTesterRewards=false','TurboTrailEquity=false','InpRiskPercent=0.75')){
            if(-not $t.Contains($need)){throw "$($s.Name) missing $need"}
        }
        if($t -notmatch 'TurboStartUtcTime=\d{10}'){throw "$($s.Name) start time not armed"}
        if($t -notmatch 'TurboExpectedSymbol=(XAUUSD|USTEC)'){throw "$($s.Name) symbol not bound"}
    }
    $chartText=($charts | ForEach-Object {Get-Content -Raw -LiteralPath $_.FullName}) -join "`n"
    foreach($need in @('TurboGuardMode=1','TurboExpectedLogin=12345678')){ if(-not $chartText.Contains($need)){throw "charts missing $need"} }
    $state=@(Get-ChildItem (Join-Path $data 'MQL5\Files') -Filter 'Calyx-Turbo5-12345678-*.json'); if($state.Count -ne 1){throw 'state file missing'}
    $ini=Get-Content -Raw -LiteralPath (Join-Path $data 'config\common.ini')
    if($ini -notmatch 'Enabled=0' -or $ini -notmatch [regex]::Escape('ProfileLast='+$profile[0].Name)){throw 'common.ini not updated (Algo OFF / profile)'}
    if(-not (Test-Path (Join-Path $profile[0].FullName 'DEPLOYMENT.txt'))){throw 'DEPLOYMENT.txt missing'}
    # Rerun keeps the saved baseline (new profile, same reference / start time).
    $first=Get-Content -Raw -LiteralPath $state[0].FullName | ConvertFrom-Json
    Start-Sleep -Seconds 1
    & $copy -AccountSize 50000 -KnownFloor 0 -TrailEquity N
    $second=Get-Content -Raw -LiteralPath $state[0].FullName | ConvertFrom-Json
    if($first.start_utc -ne $second.start_utc -or $first.reference_balance -ne $second.reference_balance){throw 'rerun changed the saved baseline'}
    if(@(Get-ChildItem (Join-Path $data 'MQL5\Profiles\Charts') -Directory | Where-Object Name -like 'Calyx-Turbo5-*').Count -ne 2){throw 'rerun did not create a new profile'}
    Write-Host 'SANDBOX PASS: 5 charts / 5 EX5 / 5 armed SETs, account + symbol binding, state file kept on rerun, Algo OFF, profile set. No real terminal touched.'
} catch { Write-Host ("FAIL: "+$_.Exception.Message); Write-Host $_.InvocationInfo.PositionMessage; Write-Host $_.ScriptStackTrace; exit 1 } finally { Remove-Item -LiteralPath $copy -Force; Remove-Item -LiteralPath $sandbox -Recurse -Force }
