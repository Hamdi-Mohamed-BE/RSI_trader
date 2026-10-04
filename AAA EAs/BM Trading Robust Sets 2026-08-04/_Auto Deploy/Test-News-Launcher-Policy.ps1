Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
. (Join-Path $PSScriptRoot 'News-Launcher-Policy.ps1')
$fake = @(
    [pscustomobject]@{Label='News Pulse XAU';Expert='News Pulse.ex5';Canonical='XAUUSD'},
    [pscustomobject]@{Label='Gold News V9 Direction';Expert='GoldNewsV9EA.ex5';Canonical='XAUUSD'},
    [pscustomobject]@{Label='News Pulse XAG';Expert='News Pulse.ex5';Canonical='XAGUSD'},
    [pscustomobject]@{Label='News Pulse BTC';Expert='News Pulse.ex5';Canonical='BTCUSD'},
    [pscustomobject]@{Label='News Pulse EURUSD';Expert='News Pulse.ex5';Canonical='EURUSD'},
    [pscustomobject]@{Label='Other future news EA';Expert='Some News.ex5';Canonical='US500'},
    [pscustomobject]@{Label='Nasdaq trend';Expert='trend.ex5';Canonical='USTEC'},
    [pscustomobject]@{Label='BTC momentum';Expert='momentum.ex5';Canonical='BTCUSD'}
)
$actual = @(Select-NormalNewsItems $fake)
if ($actual.Count -ne 7) { throw 'Normal manifest filtering failed.' }
if (@($actual | Where-Object Label -eq 'Other future news EA').Count) { throw 'Unapproved news was retained.' }
$ava = @(Select-XauNewsOnlyItems @([pscustomobject]@{Label='News Pulse XAU';Expert='News Pulse.ex5';Symbol='MGCZ26'},[pscustomobject]@{Label='News Pulse XAG';Expert='News Pulse.ex5';Symbol='SILZ26'}))
if ($ava.Count -ne 1 -or $ava[0].Symbol -ne 'MGCZ26') { throw 'Ava filtering failed.' }
$rejected=$false
try { $null = @(Select-NormalNewsItems @([pscustomobject]@{Label='News Pulse XAU';Expert='News Pulse.ex5';Canonical='BTCUSD'})) } catch { $rejected=$true }
if (-not $rejected) { throw 'Mislabeled non-gold news was accepted.' }
foreach ($file in @('Install-BMTradingPortfolio.ps1','Start-Dynamic-Portfolio.ps1','News-Launcher-Policy.ps1')) {
    $tokens=$null;$errors=$null
    $null=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot $file),[ref]$tokens,[ref]$errors)
    if ($errors.Count) { throw "$file parse errors: $errors" }
}
$PackageRoot=Split-Path -Parent $PSScriptRoot
$ast=[Management.Automation.Language.Parser]::ParseFile((Join-Path $PSScriptRoot 'Install-BMTradingPortfolio.ps1'),[ref]$null,[ref]$null)
$definition=$ast.Find({param($node) $node -is [Management.Automation.Language.FunctionDefinitionAst] -and $node.Name -eq 'Get-PortfolioItems'},$true)
. ([scriptblock]::Create($definition.Extent.Text))
foreach ($mode in @('Standard','Safe','Recommended','Claude','Adaptive')) {
    $UseRecommendedSelections=$mode -in @('Recommended','Claude','Adaptive')
    $UseClaudeSelections=$mode -eq 'Claude'
    $UseAdaptiveProfile=$mode -eq 'Adaptive'
    $IsFullSafe=$mode -eq 'Safe'
    $real=@(Get-PortfolioItems)
    $news=@($real | Where-Object { $_.Label -match '(?i)news' -or $_.Expert -match '(?i)news' })
    if ($real.Count -ne 37 -or $news.Count -ne 5) {throw "$mode actual manifest invalid"}
    Write-Host "PASS: actual $mode manifest has 37 EAs, all five selected news EAs."
}
$avaFile=Join-Path $PackageRoot 'Ava Futures Portfolio Research 2026-09-09\Install-AvaFuturesTop10.ps1'
$tokens=$null;$errors=$null
$ast=[Management.Automation.Language.Parser]::ParseFile($avaFile,[ref]$tokens,[ref]$errors)
if ($errors.Count) {throw "Ava installer parse errors: $errors"}
$assignment=$ast.Find({param($node) $node -is [Management.Automation.Language.AssignmentStatementAst] -and $node.Left.Extent.Text -eq '$portfolio' -and $node.Right.Extent.Text -like '@(*'},$true)
# Evaluate only the literal manifest: never evaluate the installer body.
$AvaScriptRoot=Split-Path -Parent $avaFile
$portfolio=@(Invoke-Expression ($assignment.Right.Extent.Text.Replace('$PSScriptRoot','$AvaScriptRoot')))
$ava=@(Select-XauNewsOnlyItems $portfolio)
if ($ava.Count -ne 8 -or @($ava | Where-Object Label -eq 'News Pulse XAG').Count -or @($ava | Where-Object Label -eq 'News Pulse XAU').Count -ne 1) {throw 'Actual Ava manifest invalid'}
Write-Host 'PASS: actual Ava manifest has 8 EAs and gold-only news. No account accessed.'
Write-Host 'PASS: all five normal news systems restored; unknown news blocked; non-news and separate Ava policy unchanged; all shared scripts parse.'
