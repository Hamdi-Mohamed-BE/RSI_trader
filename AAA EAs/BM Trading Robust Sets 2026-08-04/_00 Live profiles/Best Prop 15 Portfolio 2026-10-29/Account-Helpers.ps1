# Pure functions only. Safe to import for offline fixture tests.
function Assert-PropReadyAccount([object]$Probe) {
    if(-not $Probe.ok -or -not $Probe.terminal.connected){throw 'Terminal is not connected.'}
    if([long]$Probe.account.login -le 0 -or -not [string]$Probe.account.server){throw 'Invalid account identity.'}
    if([string]$Probe.account.currency -notmatch '^[A-Z][A-Z0-9]{1,11}$'){throw 'Unsupported account currency identifier.'}
    if([int]$Probe.account.margin_mode -ne 2){throw 'Best Prop 15 requires a hedging MT5 account; netting would merge the independent EAs.'}
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
        throw 'Stored Best Prop risk reference does not match this account; stop for review.'
    }
    $reference=[double]$Existing.reference_balance
    if([double]::IsNaN($reference) -or [double]::IsInfinity($reference) -or $reference -le 0 -or
       [long]$Existing.start_utc -le 0 -or [long]$Existing.start_utc -gt [long]$Probe.snapshot_utc){throw 'Invalid stored risk reference.'}
    return $Existing
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
