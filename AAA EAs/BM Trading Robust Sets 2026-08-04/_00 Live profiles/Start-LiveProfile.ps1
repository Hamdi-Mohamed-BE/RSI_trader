[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidateSet('ftmo','ftmo-any-broker','current14-orb05','orbs-only','full-eas','prop-ready','codex-best-ftmo')][string]$Portfolio,
    [ValidateSet('','PERCENT','FIXED_USD')][string]$RiskMode='',
    [double]$RiskValue=0,
    [double]$NewsRiskPercent=0,
    [ValidateSet('','ON','OFF')][string]$NasdaqDIFilter='',
    [ValidateSet('','ON','OFF')][string]$UsdJpyDIFilter='',
    [ValidateSet('Challenge','Verification','Funded')][string]$Phase='Challenge',
    [string]$GoldSymbol='',
    [string]$NasdaqSymbol='',
    [string]$UsdJpySymbol='',
    [string]$TargetTerminal='',
    [switch]$ValidateOnly,
    [switch]$PreflightOnly,
    [switch]$Yes
)
Set-StrictMode -Version Latest
$ErrorActionPreference='Stop'
$root=[IO.Path]::GetFullPath((Split-Path -Parent $PSScriptRoot))
$config=Get-Content -Raw -LiteralPath (Join-Path $PSScriptRoot 'Profiles.json') | ConvertFrom-Json
$selected=@($config.profiles | Where-Object slug -eq $Portfolio)
if($selected.Count -ne 1){throw 'Portfolio configuration missing or duplicated.'}
$selected=$selected[0]

function Read-PositiveNumber([string]$Question,[double]$Default) {
    $raw=(Read-Host ($Question+' ['+$Default.ToString('G17',[Globalization.CultureInfo]::InvariantCulture)+']')).Trim()
    if(-not $raw){return $Default}
    $value=0.0
    if(-not [double]::TryParse($raw,[Globalization.NumberStyles]::Float,[Globalization.CultureInfo]::InvariantCulture,[ref]$value)){throw 'Enter a number using a dot for decimals.'}
    return $value
}
function Assert-LiveProfileRisk([string]$Mode,[double]$Value) {
    if($Mode -notin @('PERCENT','FIXED_USD') -or [double]::IsNaN($Value) -or [double]::IsInfinity($Value) -or $Value -le 0){throw 'Risk must be a positive finite number.'}
    if($Mode -eq 'PERCENT' -and $Value -gt 10){throw 'Percentage risk may not exceed 10% per trade.'}
}

Write-Host ('CALYX PORTFOLIO: '+$selected.name) -ForegroundColor Cyan
Write-Host $selected.warning -ForegroundColor Yellow
if(-not $RiskMode){
    if($ValidateOnly){$RiskMode=$selected.default_mode}
    else {
        $default=if($selected.default_mode -eq 'FIXED_USD'){'2'}else{'1'}
        if($Portfolio -in @('prop-ready','codex-best-ftmo','ftmo-any-broker')){Write-Host '1 = percentage of current equity; 2 = fixed cash in account currency per trade (USD on USD accounts)'}
        else{Write-Host '1 = percentage of current equity; 2 = fixed USD per trade'}
        $choice=(Read-Host "Risk type [$default]").Trim();if(-not $choice){$choice=$default}
        $RiskMode=switch($choice){'1'{'PERCENT'}'2'{'FIXED_USD'}default{throw 'Choose 1 or 2.'}}
    }
}
if($RiskValue -eq 0){
    $default=if($RiskMode -eq 'PERCENT'){[double]$selected.default_percent}else{[double]$selected.default_usd}
    $RiskValue=if($ValidateOnly){$default}else{Read-PositiveNumber $(if($RiskMode -eq 'PERCENT'){'Percent per trade'}elseif($Portfolio -in @('prop-ready','codex-best-ftmo','ftmo-any-broker')){'Cash per trade in account currency'}else{'USD per trade'}) $default}
}
Assert-LiveProfileRisk $RiskMode $RiskValue
if($Portfolio -eq 'full-eas'){
    if($NewsRiskPercent -eq 0){$NewsRiskPercent=if($ValidateOnly){[double]$selected.default_news_percent}else{Read-PositiveNumber 'Separate news percent per ORDER (two sides double one event risk)' ([double]$selected.default_news_percent)}}
    Assert-LiveProfileRisk 'PERCENT' $NewsRiskPercent
}
foreach($field in @('NasdaqDIFilter','UsdJpyDIFilter')){
    if($field -notin $selected.di_parameters){continue}
    if(-not (Get-Variable -Name $field -ValueOnly)){
        $label=if($field -eq 'NasdaqDIFilter'){'Nasdaq 5M'}else{'USDJPY London'}
        $answer=if($ValidateOnly){'ON'}else{(Read-Host ($label+' DI filter ON or OFF [ON]')).Trim().ToUpperInvariant()}
        if(-not $answer){$answer='ON'};if($answer -notin @('ON','OFF')){throw 'DI choice must be ON or OFF.'}
        Set-Variable -Name $field -Value $answer
    }
}
if(-not $NasdaqDIFilter){$NasdaqDIFilter='ON'};if(-not $UsdJpyDIFilter){$UsdJpyDIFilter='ON'}
if($Portfolio -eq 'codex-best-ftmo' -and -not $PSBoundParameters.ContainsKey('Phase') -and -not $ValidateOnly){
    Write-Host '1 = Challenge (+10% target); 2 = Verification (+5% target); 3 = continuous demo/live (no profit-target entry stop)'
    $phaseChoice=(Read-Host 'Account mode [1]').Trim();if(-not $phaseChoice){$phaseChoice='1'}
    $Phase=switch($phaseChoice){'1'{'Challenge'}'2'{'Verification'}'3'{'Funded'}default{throw 'Choose 1, 2 or 3.'}}
}
if($Portfolio -eq 'ftmo-any-broker' -and -not $PSBoundParameters.ContainsKey('Phase')){
    $Phase='Funded'
    if(-not $ValidateOnly){
        Write-Host '1 = Challenge (+10% target); 2 = Verification (+5% target); 3 = continuous demo/live (no profit-target entry stop)'
        $phaseChoice=(Read-Host 'Account mode [3]').Trim();if(-not $phaseChoice){$phaseChoice='3'}
        $Phase=switch($phaseChoice){'1'{'Challenge'}'2'{'Verification'}'3'{'Funded'}default{throw 'Choose 1, 2 or 3.'}}
    }
}
if($Portfolio -notin @('codex-best-ftmo','ftmo-any-broker') -and ($GoldSymbol -or $NasdaqSymbol -or $UsdJpySymbol)){
    throw 'Explicit broker-symbol overrides are supported by Codex_Best_FTMO and the FTMO any-broker test build only.'
}
Write-Host "Selected risk: $RiskValue $RiskMode per trade; DI choices change the published tested preset."
$arguments=@{RiskMode=$RiskMode;RiskValue=$RiskValue;NasdaqDIFilter=$NasdaqDIFilter;UsdJpyDIFilter=$UsdJpyDIFilter}
$global:LASTEXITCODE=0
if($ValidateOnly){$arguments.ValidateOnly=$true}
if($PreflightOnly){$arguments.PreflightOnly=$true}
if($TargetTerminal){$arguments.TargetTerminal=$TargetTerminal}
switch($Portfolio){
    'prop-ready' {
        $arguments.Phase=if($PSBoundParameters.ContainsKey('Phase')){$Phase}else{'Funded'}
        & (Join-Path $PSScriptRoot 'Packages\PropReady\Install-Portfolio.ps1') @arguments
    }
    'ftmo' {
        $arguments.Phase=$Phase
        & (Join-Path $PSScriptRoot 'Packages\FTMO\Install-Portfolio.ps1') @arguments
    }
    'ftmo-any-broker' {
        $arguments.Phase=$Phase
        $arguments.GoldSymbol=$GoldSymbol
        $arguments.NasdaqSymbol=$NasdaqSymbol
        $arguments.UsdJpySymbol=$UsdJpySymbol
        & (Join-Path $PSScriptRoot 'Packages\FTMO-AnyBroker\Install-Portfolio.ps1') @arguments
    }
    'codex-best-ftmo' {
        $arguments.Phase=$Phase
        $arguments.ProfileVariant='Codex_Best_FTMO'
        $arguments.GoldSymbol=$GoldSymbol
        $arguments.NasdaqSymbol=$NasdaqSymbol
        $arguments.UsdJpySymbol=$UsdJpySymbol
        & (Join-Path $PSScriptRoot 'Packages\PropReady\Install-Portfolio.ps1') @arguments
    }
    'current14-orb05' {
        if($Yes){$arguments.Yes=$true}
        & (Join-Path $root 'Current14 Plus ORB05 Portfolio 2026-10-08\Install-Portfolio.ps1') @arguments
    }
    'orbs-only' {
        if($Yes){$arguments.Yes=$true}
        & (Join-Path $PSScriptRoot 'Packages\ORB-only\Install-Portfolio.ps1') @arguments
    }
    'full-eas' {
        $arguments.NewsRiskPercent=$NewsRiskPercent
        $arguments.HourlyRiskPercent=if($RiskMode -eq 'PERCENT'){$RiskValue}else{[double]$selected.default_percent}
        $arguments.AccountProfile='AUTO';$arguments.SafetyMode='STANDARD'
        $arguments.UseRecommendedSelections=$true;$arguments.UseAdaptiveProfile=$true
        $arguments.ApplyLiveProfileDIChoices=$true
        if($Yes){$arguments.Yes=$true}
        & (Join-Path $root '_Auto Deploy\Install-BMTradingPortfolio.ps1') @arguments
    }
}
exit $LASTEXITCODE
