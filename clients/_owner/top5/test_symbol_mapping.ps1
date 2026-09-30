$ErrorActionPreference='Stop'
$root=Split-Path -Parent $MyInvocation.MyCommand.Path
$env:CALYX_LIBRARY_ONLY='1'
$env:CALYX_BUNDLE_FILE=Join-Path (Split-Path -Parent (Split-Path -Parent $root)) 'top 5\Install Top 5.bat'
. (Join-Path $root 'installer.generated.ps1')
function Row($name,$desc,$base,$calc='SYMBOL_CALC_MODE_CFD') {
    [pscustomobject]@{schema='1';nonce='test';login='123';server='Demo-Test';account_currency='USD';margin_mode='2';generated_utc=[string][DateTimeOffset]::UtcNow.ToUnixTimeSeconds();name=$name;description=$desc;path='CFD';base=$base;profit='USD';calc=$calc;trade='SYMBOL_TRADE_MODE_FULL';custom='0';expiry='0';contract='100';tick_size='0.01';volume_min='0.01';volume_step='0.01';selected='0'}
}
foreach($name in @('XAUUSD','XAUUSDm','XAUUSD.a','GOLD.a')) {
    if(@(Find-SymbolCandidates @(Row $name 'Gold spot' 'XAU') 'XAUUSD').Count -ne 1){throw "Gold alias failed: $name"}
}
foreach($name in @('USTEC','US100.a','NAS100m','Nasdaq100.cash')) {
    if(@(Find-SymbolCandidates @(Row $name 'Nasdaq 100 cash index' 'USD') 'USTEC').Count -ne 1){throw "Nasdaq alias failed: $name"}
}
foreach($field in @('profit','custom','trade','expiry','calc','contract','tick_size','volume_min','volume_step')) {
    $r=Row 'XAUUSD' 'Gold spot' 'XAU'
    $bad=@{profit='EUR';custom='1';trade='SYMBOL_TRADE_MODE_CLOSEONLY';expiry='1800000000';calc='SYMBOL_CALC_MODE_FUTURES';contract='0';tick_size='NaN';volume_min='-1';volume_step='0'}
    $r.$field=$bad[$field]
    if(@(Find-SymbolCandidates @($r) 'XAUUSD').Count){throw "Unsafe contract accepted: $field"}
}
foreach($desc in @('Nasdaq Composite','Nasdaq 100 futures','Nasdaq 100 ETF','Nasdaq Inc shares','S&P 500')) {
    if(@(Find-SymbolCandidates @(Row 'OTHER' $desc 'USD') 'USTEC').Count){throw "Wrong index accepted: $desc"}
}
$gold=Row 'GOLD.a' 'Gold spot' 'XAU';$nas=Row 'US100.a' 'Nasdaq 100' 'USD'
$mapped=Select-BrokerSymbols @($gold,$nas)
if($mapped.XAUUSD -ne 'GOLD.a' -or $mapped.USTEC -ne 'US100.a'){throw 'Unique mapping failed'}
$script:choices=0
function Read-Choice($Prompt,$Count){$script:choices++;return 1}
$mapped=Select-BrokerSymbols @($gold,$nas,(Row 'XAUUSDm' 'Gold spot' 'XAU'))
if($script:choices -ne 1 -or $mapped.XAUUSD -ne 'XAUUSDm'){throw 'Ambiguous mapping did not ask for selection'}
$snapshot=Join-Path $root ('symbol-fixture-'+[Guid]::NewGuid().ToString('N')+'.tsv')
@($gold,$nas)|Export-Csv -LiteralPath $snapshot -Delimiter "`t" -Encoding Unicode -NoTypeInformation
if(@(Read-BrokerCatalog $snapshot 'test' 123 'Demo-Test').Count -ne 2){throw 'Valid catalogue failed'}
foreach($kind in @('nonce','login','server','stale','currency','netting','duplicate')) {
    $r=Row 'GOLD.a' 'Gold spot' 'XAU';$rows=@($r)
    switch($kind){nonce{$r.nonce='wrong'}login{$r.login='999'}server{$r.server='Wrong'}stale{$r.generated_utc='1'}currency{$r.account_currency='EUR'}netting{$r.margin_mode='0'}duplicate{$rows=@($r,$r)}}
    $rows|Export-Csv -LiteralPath $snapshot -Delimiter "`t" -Encoding Unicode -NoTypeInformation
    $blocked=$false
    try{$null=Read-BrokerCatalog $snapshot 'test' 123 'Demo-Test'}catch{$blocked=$true}
    if(!$blocked){throw "Invalid snapshot accepted: $kind"}
}
Write-Host 'PASS: broker aliases, contract exclusions, unique mapping, ambiguous selection, fresh account-bound snapshots.'
