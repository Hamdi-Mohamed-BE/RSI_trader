# Pure functions only. Safe to import for offline fixture tests.
function Assert-PropReadyAccount([object]$Probe) {
    if(-not $Probe.ok -or -not $Probe.terminal.connected){throw 'Terminal is not connected.'}
    if([long]$Probe.account.login -le 0 -or -not [string]$Probe.account.server){throw 'Invalid account identity.'}
    if([string]$Probe.account.currency -notmatch '^[A-Z][A-Z0-9]{1,11}$'){throw 'Unsupported account currency identifier.'}
    if([int]$Probe.account.margin_mode -ne 2){throw 'Prop Ready requires a hedging MT5 account; netting would merge the independent EAs.'}
    if(-not $Probe.account.trade_allowed -or -not $Probe.account.trade_expert){throw 'Account does not permit EA trading.'}
    if($Probe.terminal.trade_allowed){throw 'Turn Algo Trading OFF in the selected MT5 terminal, then run again.'}
    if($Probe.positions -ne 0 -or $Probe.orders -ne 0){throw 'Account must be flat with no pending orders; nothing will be closed automatically.'}
    foreach($value in @([double]$Probe.account.balance,[double]$Probe.account.equity)){
        if([double]::IsNaN($value) -or [double]::IsInfinity($value) -or $value -le 0){throw 'Account balance/equity must be positive and finite.'}
    }
    if([string]$Probe.account.server -match '[\r\n<>]' -or [long]$Probe.snapshot_utc -le 0){throw 'Unsupported account snapshot.'}
}

function Get-PropReadyReference([object]$Probe,[object]$Existing=$null) {
    if($null -eq $Existing){
        return [pscustomobject]@{version=1;login=[string]$Probe.account.login;server=[string]$Probe.account.server;
            currency=[string]$Probe.account.currency;reference_balance=[double]$Probe.account.balance;start_utc=[long]$Probe.snapshot_utc}
    }
    if($Existing.version -ne 1 -or [string]$Existing.login -cne [string]$Probe.account.login -or
       [string]$Existing.server -cne [string]$Probe.account.server -or [string]$Existing.currency -cne [string]$Probe.account.currency){
        throw 'Stored Prop Ready risk reference does not match this account; stop for review.'
    }
    $reference=[double]$Existing.reference_balance
    if([double]::IsNaN($reference) -or [double]::IsInfinity($reference) -or $reference -le 0 -or
       [long]$Existing.start_utc -le 0 -or [long]$Existing.start_utc -gt [long]$Probe.snapshot_utc){throw 'Invalid stored risk reference.'}
    return $Existing
}

function Resolve-RiskCapPercent([string]$Mode,[double]$Value,[double]$Reference) {
    # 2026-10-30 owner: the guard's per-entry cap follows the chosen risk instead of a fixed share of the saved balance.
    $pct=if($Mode -eq 'PERCENT'){$Value}else{100.0*$Value/$Reference}
    if([double]::IsNaN($pct) -or [double]::IsInfinity($pct) -or $pct -le 0){throw 'Invalid risk selection.'}
    if($pct -gt 2.0){throw ("Chosen risk = {0:0.###}% of the saved starting balance; the maximum is 2% (the guard's 3% daily reserve would refuse larger entries)." -f $pct)}
    return [math]::Round($pct,6)
}

function Select-PropReadyReference([object]$Probe,[object]$Existing,[bool]$Ask) {
    # Returns the reference to use and whether the state file must be (re)written. A saved baseline is kept unless the
    # user explicitly starts fresh, because re-basing moves every loss limit.
    $saved=Get-PropReadyReference $Probe $Existing
    if($null -eq $Existing){return [pscustomobject]@{reference=$saved;write=$true}}
    $was=[double]$saved.reference_balance;$now=[double]$Probe.account.balance
    if(-not $Ask -or [math]::Abs($now-$was) -le 0.005*$was){return [pscustomobject]@{reference=$saved;write=$false}}
    Write-Host ("Saved starting balance for this login: {0:N2}; current balance: {1:N2}." -f $was,$now) -ForegroundColor Yellow
    Write-Host 'Every risk cap and loss limit is measured from the SAVED starting balance.'
    Write-Host '1 = keep the saved starting balance (loss limits stay where they are)'
    Write-Host '2 = start fresh from the current balance (after a deposit, a reset or a new account size)'
    $answer=(Read-Host 'Starting balance [1]').Trim();if(-not $answer){$answer='1'}
    if($answer -eq '1'){return [pscustomobject]@{reference=$saved;write=$false}}
    if($answer -ne '2'){throw 'Choose 1 or 2.'}
    return [pscustomobject]@{reference=(Get-PropReadyReference $Probe $null);write=$true}
}

function Assert-PropReadyConfirmation([object]$Original,[object]$Confirmation) {
    Assert-PropReadyAccount $Confirmation
    foreach($field in @('login','server','currency','margin_mode','balance','equity')){
        if([string]$Confirmation.account.$field -cne [string]$Original.account.$field){throw "Account $field changed during confirmation; nothing installed."}
    }
    if([string]$Confirmation.terminal.data_path -ine [string]$Original.terminal.data_path -or
       [string]$Confirmation.terminal.path -ine [string]$Original.terminal.path){throw 'Terminal changed during confirmation; nothing installed.'}
}

function Get-PropReadyPresetInputs([object]$Entry) {
    $inputs=Read-SetInputs (Join-Path $Package $Entry.settings)
    if($Entry.slug -eq 'nasdaq-5m-candle-momentum'){$inputs['InpRequireDIAgreement']=if($NasdaqDIFilter -eq 'OFF'){'false'}else{'true'}}
    if($Entry.slug -eq 'usdjpy-london-open-momentum'){$inputs['InpRequireDIAgreement']=if($UsdJpyDIFilter -eq 'OFF'){'false'}else{'true'}}
    $inputs['FTMOAllocationMode']=if($RiskMode -eq 'FIXED_USD'){'0'}else{'1'}
    $inputs['FTMOAllocationValue']=$RiskValue.ToString('G17',[Globalization.CultureInfo]::InvariantCulture)
    return $inputs
}
