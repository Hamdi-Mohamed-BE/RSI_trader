# Broker metadata, never a blind substring match or cached symbols from another server.
function Read-BrokerCatalog([string]$Path,[string]$Nonce,[long]$Login,[string]$Server) {
    if (!(Test-Path -LiteralPath $Path -PathType Leaf)) { throw 'Detector has not produced a fresh snapshot. Run it in the selected MT5, then try again.' }
    $rows=@(Import-Csv -LiteralPath $Path -Delimiter "`t" -Encoding Unicode)
    if (!$rows.Count) { throw 'Broker returned an empty symbol catalogue.' }
    $now=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()
    foreach ($r in $rows) {
        if ($r.schema -ne '1' -or $r.nonce -cne $Nonce -or $r.login -ne [string]$Login -or $r.server -cne $Server) { throw 'Symbol snapshot belongs to a different request/account/server.' }
        if ($r.account_currency -cne 'USD' -or $r.margin_mode -ne '2') { throw 'The connected MT5 account is not USD hedging. No bots will be installed.' }
        if ([math]::Abs($now-[long]$r.generated_utc) -gt 900) { throw 'Symbol snapshot is stale. Re-run the detector.' }
        $null=Safe-Line $r.name 'broker symbol'
    }
    if (@($rows.name | Select-Object -Unique).Count -ne $rows.Count) { throw 'Duplicate symbol records in snapshot.' }
    return $rows
}
function Find-SymbolCandidates($Rows,[string]$Canonical) {
    foreach ($r in $Rows) {
        if ($r.custom -ne '0' -or $r.trade -ne 'SYMBOL_TRADE_MODE_FULL' -or $r.profit -cne 'USD' -or [long]$r.expiry -ne 0) { continue }
        if ($r.calc -notin @('SYMBOL_CALC_MODE_FOREX','SYMBOL_CALC_MODE_FOREX_NO_LEVERAGE','SYMBOL_CALC_MODE_CFD','SYMBOL_CALC_MODE_CFDINDEX','SYMBOL_CALC_MODE_CFDLEVERAGE')) { continue }
        $valid=$true
        foreach ($field in @('contract','tick_size','volume_min','volume_step')) {
            $num=0.0
            if (![double]::TryParse($r.$field,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$num) -or [double]::IsInfinity($num) -or [double]::IsNaN($num) -or $num -le 0) { $valid=$false }
        }
        if (!$valid) { continue }
        $words=$r.name+' '+$r.description+' '+$r.path
        if ($words -match '(?i)\b(futures?|options?|ETF|ETN|shares?|equities|synthetic|volatility|inverse)\b') { continue }
        $name=($r.name -replace '[^A-Za-z0-9]','').ToUpperInvariant()
        $desc=$r.description
        $match=$false
        if ($Canonical -eq 'XAUUSD') {
            # Currency metadata rules out XAUEUR/XAUAUD, including symbols called just GOLD.
            $match=($r.base -ceq 'XAU' -or $name -match 'XAUUSD' -or ($name -match 'GOLD' -and $desc -match '(?i)gold|XAU'))
        } elseif ($Canonical -eq 'USTEC') {
            if ($r.calc -notin @('SYMBOL_CALC_MODE_CFD','SYMBOL_CALC_MODE_CFDINDEX','SYMBOL_CALC_MODE_CFDLEVERAGE')) { continue }
            # Reject broad Nasdaq Composite, Nasdaq stock shares, NQ/MNQ and dated futures.
            if ($words -match '(?i)composite|nasdaq\s*inc\b') { continue }
            $alias=$name -match 'USTEC|US100|NAS100|NASDAQ100|NDX100|USTECH100|TECH100'
            $identity=$desc -match '(?i)(nasdaq|nas|us\s*tech|us\s*technology|tech|ndx)[\s._-]*100|US100|USTEC'
            $match=$identity -or ($alias -and $desc -match '(?i)nasdaq|us\s*tech|us\s*technology')
        }
        if ($match) { $r }
    }
}
function Select-BrokerSymbols($Rows) {
    $mapping=@{}
    foreach ($canonical in @($Package.entries.symbol | Select-Object -Unique)) {
        $matches=@(Find-SymbolCandidates $Rows $canonical | Sort-Object name)
        if (!$matches.Count) { throw "No compatible USD spot/CFD match for $canonical. Do not substitute futures or a different index. Ask the owner to review the broker's catalogue." }
        Write-Host "`n$canonical - compatible broker symbols:"
        for($i=0;$i -lt $matches.Count;$i++) {
            $m=$matches[$i]
            Write-Host ("{0}. {1} | {2} | contract={3}; min lot={4}; step={5}; Market Watch={6}" -f ($i+1),$m.name,$m.description,$m.contract,$m.volume_min,$m.volume_step,$m.selected)
        }
        $pick=0
        if ($matches.Count -gt 1) { $pick=Read-Choice 'Multiple valid contracts: choose the one for this account (no default guess)' $matches.Count }
        $mapping[$canonical]=[string]$matches[$pick].name
        Write-Host ("Mapped {0} -> {1}" -f $canonical,$mapping[$canonical]) -ForegroundColor Green
    }
    return $mapping
}
function Discover-BrokerSymbols($Target,[long]$Login,[string]$Server) {
    if (!(Test-Running $Target.Exe)) { throw 'Open the selected MT5 and log into the intended account before discovery. The detector does not log you in.' }
    Write-Host 'The BAT can read the real broker catalogue through a read-only MT5 detector. No Python, DLLs, orders or global AutoTrading changes.'
    if ((Read-Host 'Press Enter to install the detector in this terminal, or type CANCEL') -ne '') { throw 'Cancelled before discovery.' }
    $scriptDir=Join-Path $Target.Data 'MQL5\Scripts\CalyxTop5'
    $fileDir=Join-Path $Target.Data 'MQL5\Files\CalyxTop5'
    $null=New-Item -ItemType Directory -Path $scriptDir -Force
    $null=New-Item -ItemType Directory -Path $fileDir -Force
    $scriptPath=Join-Path $scriptDir 'Detect Broker Symbols.ex5'
    [IO.File]::WriteAllBytes($scriptPath,[Convert]::FromBase64String('__DETECTOR_B64__'))
    if ((File-Hash $scriptPath) -cne '__DETECTOR_SHA256__') { throw 'Detector verification failed.' }
    $nonce=[Guid]::NewGuid().ToString('N')
    [IO.File]::WriteAllLines((Join-Path $fileDir 'discovery-request.txt'),@($nonce,[string]$Login,$Server),[Text.Encoding]::Unicode)
    Write-Host 'In the SAME MT5: Navigator > Scripts > right-click Refresh > CalyxTop5 > Detect Broker Symbols.' -ForegroundColor Cyan
    Write-Host 'Double-click that detector on a chart WITHOUT another script running. Leave existing EAs in place; do not enable AutoTrading for this step.'
    Write-Host 'After its completion message, return here. It only reads the broker symbols and writes a local snapshot.'
    $null=Read-Host 'Press Enter after the detector says complete'
    $rows=Read-BrokerCatalog (Join-Path $fileDir ("symbols-$nonce.tsv")) $nonce $Login $Server
    return Select-BrokerSymbols $rows
}
