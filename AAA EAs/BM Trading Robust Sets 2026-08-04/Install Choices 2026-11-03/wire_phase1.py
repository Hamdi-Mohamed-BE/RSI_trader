"""Phase 1 of the install-choice request (owner 2026-11-03): the Nasdaq 5M NEW/OLD stop question in every installer and the single
fully-described ON/OFF switch for the Recommended Adaptive governor. Exact assert-once replacements; originals backed up to before/.
python wire_phase1.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent; B = ROOT.parent
DOT_PKG = ". (Join-Path $PSScriptRoot '..\\..\\Calyx-InstallChoices.ps1')"
VERSION_PARAM = "[ValidateSet('','NEW','OLD')][string]$NasdaqStopVersion='',"
ASK = ("$NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion ([bool]$ValidateOnly)\n"
       "Write-Host ('Nasdaq 5M: '+(Get-CalyxNasdaqVersionText $NasdaqStopVersion))\n")
APPLY = "Set-CalyxNasdaqVersion $inputs $NasdaqStopVersion"


def patch(path, reps):
    p = B / path; raw = p.read_bytes(); crlf = b'\r\n' in raw; bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    if 'Calyx-InstallChoices' in text: print('already patched', path); return
    for old, new in reps:
        assert text.count(old) == 1, (path, old[:90], text.count(old)); text = text.replace(old, new)
    dest = ROOT / 'before' / path
    if not dest.exists(): dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)
    out = text.replace('\n', '\r\n') if crlf else text
    p.write_bytes((b'\xef\xbb\xbf' if bom else b'') + out.encode('utf-8')); print('patched', path)


def patch_helpers(path):
    p = B / path; raw = p.read_bytes(); text = raw.decode('utf-8-sig')
    old = "    if($Entry.slug -eq 'nasdaq-5m-candle-momentum'){$inputs['InpRequireDIAgreement']=if($NasdaqDIFilter -eq 'OFF'){'false'}else{'true'}}"
    if APPLY in text: print('already patched', path); return
    assert text.count(old) == 1, path
    dest = ROOT / 'before' / path
    if not dest.exists(): dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)
    new = old[:-1] + ";" + APPLY + "}"
    p.write_bytes((b'\xef\xbb\xbf' if raw.startswith(b'\xef\xbb\xbf') else b'') + text.replace(old, new).encode('utf-8')); print('patched', path)


# Prop ready / Codex (the any-broker installer is generated from it)
patch('_00 Live profiles/Packages/PropReady/Install-Portfolio.ps1', [
    ("    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',\n", "    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',\n    " + VERSION_PARAM + "\n"),
    (". (Join-Path $PSScriptRoot 'Account-Helpers.ps1')\n", ". (Join-Path $PSScriptRoot 'Account-Helpers.ps1')\n" + DOT_PKG + "\n"),
    ("    $NasdaqDIFilter=$answer\n}\n", "    $NasdaqDIFilter=$answer\n}\n" + ASK)])
patch_helpers('_00 Live profiles/Packages/PropReady/Account-Helpers.ps1')
patch_helpers('_00 Live profiles/Best Prop Portfolio 2026-10-20/Account-Helpers.ps1')
# FTMO account build
patch('_00 Live profiles/Packages/FTMO/Install-Portfolio.ps1', [
    ("    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',\n", "    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',\n    " + VERSION_PARAM + "\n"),
    ("Set-StrictMode -Version Latest\n", "Set-StrictMode -Version Latest\n" + DOT_PKG + "\n"),
    ("        $inputs['InpRequireDIAgreement']=if($DIChoice -eq 'OFF'){'false'}else{'true'}\n",
     "        $inputs['InpRequireDIAgreement']=if($DIChoice -eq 'OFF'){'false'}else{'true'}\n        " + APPLY + "\n"),
    ("    $NasdaqDIFilter=$diChoice\n}\n", "    $NasdaqDIFilter=$diChoice\n}\n" + ASK)])
# Best Prop 9 (Best Prop 15's installer is generated from it)
patch('_00 Live profiles/Best Prop Portfolio 2026-10-20/Install-BestProp.ps1', [
    ("    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='OFF',\n", "    [ValidateSet('ON','OFF')][string]$NasdaqDIFilter='OFF',\n    " + VERSION_PARAM + "\n"),
    (". (Join-Path $PSScriptRoot 'Account-Helpers.ps1')\n", ". (Join-Path $PSScriptRoot 'Account-Helpers.ps1')\n. (Join-Path $PSScriptRoot '..\\Calyx-InstallChoices.ps1')\n"),
    ("        $NasdaqDIFilter=$answer\n    }\n}\nif([double]::IsNaN($RiskValue)", "        $NasdaqDIFilter=$answer\n    }\n}\n" + ASK + "if([double]::IsNaN($RiskValue)")])
# funded_v1
patch('_00 Live profiles/Packages/FundedV1/Install-FundedV1.ps1', [
    ("    [ValidateSet('','ON','OFF')][string]$NasdaqDIFilter='',\n", "    [ValidateSet('','ON','OFF')][string]$NasdaqDIFilter='',\n    " + VERSION_PARAM + "\n"),
    (". (Join-Path $PSScriptRoot 'Account-Helpers.ps1')\n", ". (Join-Path $PSScriptRoot 'Account-Helpers.ps1')\n" + DOT_PKG + "\n"),
    ("if(-not $NasdaqDIFilter){$NasdaqDIFilter=Read-Choice 'Nasdaq 5M DI filter ON or OFF' 'ON' @('ON','OFF')}\n",
     "if(-not $NasdaqDIFilter){$NasdaqDIFilter=Read-Choice 'Nasdaq 5M DI filter ON or OFF' 'ON' @('ON','OFF')}\n" + ASK),
    ("    if($entry.slug -eq 'nasdaq-5m-candle-momentum'){$inputs['InpRequireDIAgreement']=if($NasdaqDIFilter -eq 'ON'){'true'}else{'false'}}\n",
     "    if($entry.slug -eq 'nasdaq-5m-candle-momentum'){$inputs['InpRequireDIAgreement']=if($NasdaqDIFilter -eq 'ON'){'true'}else{'false'};" + APPLY + "}\n")])
# Turbo 5 (Nasdaq DI fixed OFF)
patch('_00 Live profiles/Packages/Turbo5/Install-Turbo5.ps1', [
    ("    [ValidateSet('','Y','N')][string]$TrailEquity='',\n", "    [ValidateSet('','Y','N')][string]$TrailEquity='',\n    " + VERSION_PARAM + "\n"),
    (". (Join-Path $PSScriptRoot 'Account-Helpers.ps1')\n", ". (Join-Path $PSScriptRoot 'Account-Helpers.ps1')\n" + DOT_PKG + "\n"),
    ("    $TrailEquity=if($answer){$answer}else{'N'}\n    if($TrailEquity -notin @('Y','N')){throw 'Answer Y or N.'}\n}\n",
     "    $TrailEquity=if($answer){$answer}else{'N'}\n    if($TrailEquity -notin @('Y','N')){throw 'Answer Y or N.'}\n}\n" + ASK),
    ("    $inputs['TurboKnownFloor']=([double]$reference.known_floor).ToString('G17',$inv);",
     "    if($entry.slug -eq 'nasdaq-5m-candle-momentum'){" + APPLY + "}\n    $inputs['TurboKnownFloor']=([double]$reference.known_floor).ToString('G17',$inv);")])
# Canonical installer (every normal root BAT, claude_eas, reviwed_Eas, Full EA)
NOPROMPT = "([bool]($ValidateOnly -or $PreflightOnly -or $Yes))"
patch('_Auto Deploy/Install-BMTradingPortfolio.ps1', [
    ("    [string[]]$SkipNewsBots = @(),\n",
     "    [string[]]$SkipNewsBots = @(),\n"
     "    # 2026-11-03 owner: Nasdaq 5M stop version and the governor switch are asked at install (defaults = tested NEW / ON).\n"
     "    [ValidateSet('', 'NEW', 'OLD')][string]$NasdaqStopVersion = '',\n    [ValidateSet('', 'ON', 'OFF')][string]$AdaptiveControls = '',\n"),
    (". (Join-Path $PSScriptRoot 'Reviewed-Portfolio-Policy.ps1')\n",
     ". (Join-Path $PSScriptRoot 'Reviewed-Portfolio-Policy.ps1')\n"
     ". (Join-Path (Split-Path -Parent $PSScriptRoot) '_00 Live profiles\\Calyx-InstallChoices.ps1')\n"
     "$NasdaqStopVersion = Read-CalyxNasdaqVersion $NasdaqStopVersion " + NOPROMPT + "\n"
     "if ($UseAdaptiveProfile) { $AdaptiveControls = Read-CalyxAdaptiveControls $AdaptiveControls " + NOPROMPT + " } elseif (-not $AdaptiveControls) { $AdaptiveControls = 'OFF' }\n"
     "Write-Host ('Nasdaq 5M: ' + (Get-CalyxNasdaqVersionText $NasdaqStopVersion) + $(if ($UseAdaptiveProfile) { '; portfolio risk governor ' + $AdaptiveControls } else { '' }))\n"),
    ("        $inputs['InpRequireDIAgreement'] = if ($NasdaqDIFilter -eq 'OFF') { 'false' } else { 'true' }\n    }\n",
     "        $inputs['InpRequireDIAgreement'] = if ($NasdaqDIFilter -eq 'OFF') { 'false' } else { 'true' }\n        " + APPLY + "\n    }\n"),
    ("        $inputs['InpAdaptivePortfolioControls'] = if ($UseAdaptiveProfile) { 'true' } else { 'false' }\n",
     "        $inputs['InpAdaptivePortfolioControls'] = if ($UseAdaptiveProfile -and $AdaptiveControls -ne 'OFF') { 'true' } else { 'false' }\n"),
    ("    } elseif ($UseAdaptiveProfile) {\n        $inputs['InpAdaptivePortfolioControls'] = 'true'\n",
     "    } elseif ($UseAdaptiveProfile) {\n        $inputs['InpAdaptivePortfolioControls'] = if ($AdaptiveControls -eq 'OFF') { 'false' } else { 'true' }\n")])
# Named-profile launcher: ask once and pass down (ORB-only has no Nasdaq 5M)
patch('_00 Live profiles/Start-LiveProfile.ps1', [
    ("    [ValidateSet('','ON','OFF')][string]$UsdJpyDIFilter='',\n",
     "    [ValidateSet('','ON','OFF')][string]$UsdJpyDIFilter='',\n    [ValidateSet('','NEW','OLD')][string]$NasdaqStopVersion='',\n    [ValidateSet('','ON','OFF')][string]$AdaptiveControls='',\n"),
    ("if(-not $NasdaqDIFilter){$NasdaqDIFilter='ON'};if(-not $UsdJpyDIFilter){$UsdJpyDIFilter='ON'}\n",
     "if(-not $NasdaqDIFilter){$NasdaqDIFilter='ON'};if(-not $UsdJpyDIFilter){$UsdJpyDIFilter='ON'}\n"
     ". (Join-Path $PSScriptRoot 'Calyx-InstallChoices.ps1')\n"
     "if($Portfolio -ne 'orbs-only'){$NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion ([bool]$ValidateOnly)}\n"
     "if($Portfolio -eq 'full-eas'){$AdaptiveControls=Read-CalyxAdaptiveControls $AdaptiveControls ([bool]$ValidateOnly)}\n"),
    ("$arguments=@{RiskMode=$RiskMode;RiskValue=$RiskValue;NasdaqDIFilter=$NasdaqDIFilter;UsdJpyDIFilter=$UsdJpyDIFilter}\n",
     "$arguments=@{RiskMode=$RiskMode;RiskValue=$RiskValue;NasdaqDIFilter=$NasdaqDIFilter;UsdJpyDIFilter=$UsdJpyDIFilter}\n"
     "if($Portfolio -ne 'orbs-only'){$arguments['NasdaqStopVersion']=$NasdaqStopVersion}\nif($Portfolio -eq 'full-eas'){$arguments['AdaptiveControls']=$AdaptiveControls}\n")])
