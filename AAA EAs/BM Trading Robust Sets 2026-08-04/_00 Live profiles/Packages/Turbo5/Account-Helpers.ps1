# Pure functions only (Turbo5). Safe to import for offline fixture tests. Adapted from Packages/PropReady/Account-Helpers.ps1.
function Assert-TurboAccount([object]$Probe) {
    if(-not $Probe.ok -or -not $Probe.terminal.connected){throw 'Terminal is not connected.'}
    if([long]$Probe.account.login -le 0 -or -not [string]$Probe.account.server){throw 'Invalid account identity.'}
    if([string]$Probe.account.currency -notmatch '^[A-Z][A-Z0-9]{1,11}$'){throw 'Unsupported account currency identifier.'}
    if([int]$Probe.account.margin_mode -ne 2){throw 'The Turbo guard requires a hedging MT5 account; netting would merge the independent EAs.'}
    if(-not $Probe.account.trade_allowed -or -not $Probe.account.trade_expert){throw 'Account does not permit EA trading.'}
    if($Probe.terminal.trade_allowed){throw 'Turn Algo Trading OFF in the selected MT5 terminal, then run again.'}
    if($Probe.positions -ne 0 -or $Probe.orders -ne 0){throw 'Account must be flat with no pending orders; nothing will be closed automatically.'}
    foreach($value in @([double]$Probe.account.balance,[double]$Probe.account.equity)){
        if([double]::IsNaN($value) -or [double]::IsInfinity($value) -or $value -le 0){throw 'Account balance/equity must be positive and finite.'}
    }
    if([string]$Probe.account.server -match '[\r\n<>]' -or [long]$Probe.snapshot_utc -le 0){throw 'Unsupported account snapshot.'}
}

# The guard rebuilds the trailing floor from deals AFTER start_utc on top of reference_balance; reruns must keep both.
function Get-TurboReference([object]$Probe,[object]$Existing,[double]$AccountSize,[double]$KnownFloor) {
    if($null -eq $Existing){
        return [pscustomobject]@{version=1;login=[string]$Probe.account.login;server=[string]$Probe.account.server;
            currency=[string]$Probe.account.currency;reference_balance=[double]$Probe.account.balance;start_utc=[long]$Probe.snapshot_utc;
            account_size=$AccountSize;known_floor=$KnownFloor}
    }
    if($Existing.version -ne 1 -or [string]$Existing.login -cne [string]$Probe.account.login -or
       [string]$Existing.server -cne [string]$Probe.account.server -or [string]$Existing.currency -cne [string]$Probe.account.currency){
        throw 'Stored Turbo reference does not match this account; stop for review.'
    }
    $reference=[double]$Existing.reference_balance
    if([double]::IsNaN($reference) -or [double]::IsInfinity($reference) -or $reference -le 0 -or
       [long]$Existing.start_utc -le 0 -or [long]$Existing.start_utc -gt [long]$Probe.snapshot_utc){throw 'Invalid stored Turbo reference.'}
    if([double]$Existing.account_size -ne $AccountSize){throw "Stored account size $($Existing.account_size) differs from the one entered; stop for review."}
    return $Existing
}

function Assert-TurboConfirmation([object]$Original,[object]$Confirmation) {
    Assert-TurboAccount $Confirmation
    foreach($field in @('login','server','currency','margin_mode','balance','equity')){
        if([string]$Confirmation.account.$field -cne [string]$Original.account.$field){throw "Account $field changed during confirmation; nothing installed."}
    }
    if([string]$Confirmation.terminal.data_path -ine [string]$Original.terminal.data_path -or
       [string]$Confirmation.terminal.path -ine [string]$Original.terminal.path){throw 'Terminal changed during confirmation; nothing installed.'}
}
