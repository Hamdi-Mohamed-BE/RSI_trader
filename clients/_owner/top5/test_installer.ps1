$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$env:CALYX_LIBRARY_ONLY='1'
$env:CALYX_BUNDLE_FILE=Join-Path (Split-Path -Parent (Split-Path -Parent $root)) 'top 5\Install Top 5.bat'
. (Join-Path $root 'installer.generated.ps1')
Check-Bundle
$tokens=$null;$parseErrors=$null
$null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $root 'installer.generated.ps1'),[ref]$tokens,[ref]$parseErrors)
if($parseErrors.Count){throw ($parseErrors|Out-String)}
$fixture=Join-Path $root ('installer-fixture-'+[Guid]::NewGuid().ToString('N'))
$source=Join-Path $fixture 'MQL5\Profiles\Charts\Original'
$null=New-Item -ItemType Directory -Path $source -Force
$foreign='<chart>'+"`r`n"+'id=12'+"`r`n"+'symbol=EURUSD'+"`r`n"+'<expert>'+"`r`n"+'InpMagic=1234'+"`r`n"+'</expert>'+"`r`n"+'</chart>'
[IO.File]::WriteAllText((Join-Path $source 'chart01.chr'),$foreign,[Text.Encoding]::Unicode)
$before=File-Hash (Join-Path $source 'chart01.chr')
$symbols=@{XAUUSD='XAUUSD.a';USTEC='US100.a'}
foreach($mode in @(0,1)) {
    $risk=if($mode -eq 0){50}else{0.5}
    $dest=Write-Profile $fixture 'Original' ('Client-'+$mode) 123456 'Demo-Test' $symbols $mode $risk
    $files=@(Get-ChildItem -LiteralPath $dest -Filter '*.chr')
    if($files.Count -ne 6){throw 'Expected one preserved chart and five EAs'}
    if((File-Hash (Join-Path $source 'chart01.chr')) -ne $before){throw 'Original profile changed'}
    if((File-Hash (Join-Path $dest 'chart01.chr')) -ne $before){throw 'Foreign chart changed'}
    $all=($files|ForEach-Object{[IO.File]::ReadAllText($_.FullName)}) -join "`n"
    if(([regex]::Matches($all,'ClientExpectedLogin=123456')).Count -ne 5){throw 'Missing account locks'}
    if(([regex]::Matches($all,"ClientRiskMode=$mode")).Count -ne 5){throw 'Wrong risk mode'}
    if(([regex]::Matches($all,'(?m)^grid=1\r?$')).Count -ne 5){throw 'Chart ID replacement corrupted settings'}
    if(([regex]::Matches($all,'ClientExpectedSymbol=US100.a')).Count -ne 2){throw 'Wrong Nasdaq symbols'}
    # Renewal replaces the five client charts in a new clone, never duplicates them.
    $second=Write-Profile $fixture ('Client-'+$mode) ('Renew-'+$mode) 123456 'Demo-Test' $symbols $mode $risk
    if(@(Get-ChildItem -LiteralPath $second -Filter '*.chr').Count -ne 6){throw 'Renewal duplicated charts'}
}
$originalMagic=[string]$Package.entries[0].original_magic
[IO.File]::WriteAllText((Join-Path $source 'chart02.chr'),("<inputs>`r`nInpMagic=$originalMagic`r`n</inputs>"),[Text.Encoding]::Unicode)
$blocked=$false
try{$null=Write-Profile $fixture 'Original' 'Must-Not-Create' 123456 'Demo-Test' $symbols 0 50}catch{$blocked=$_.Exception.Message -like '*already attached*'}
if(!$blocked -or (Test-Path -LiteralPath (Join-Path $fixture 'MQL5\Profiles\Charts\Must-Not-Create'))){throw 'Duplicate original EA not safely blocked'}
Write-Host 'PASS: both sizing modes, five charts, account/symbol locks, preserve foreign charts, renew without duplicates, block original EAs.'
Write-Host ('Fixture retained: '+$fixture)
