"""Risk bug fix (owner 2026-11-03: "i used ... ANY BROKER TEST.bat ... 100k for 1% risk ... it opened risk with 100$ fix ... fix this kind of
bug everywhere" + "make it refresh it always when re run it first"). Prop Ready guard family only (Prop ready / Codex, FTMO any-broker via
its generator, Best Prop 9 and Best Prop 15 via its generator):
 1. Every rerun starts a FRESH baseline from the current balance (the owner's choice), so caps and limits always follow today's account
    size. Latched breach / day stops are keyed by login+server, not by install, and stay latched.
 2. The strategies' own risk request is raised to 1.5x the chosen risk (max 5%), as funded_v1 already does. The guard never sends more
    than the strategy's own volume, so the pinned preset (0.5% Prop ready / any-broker, 1.0% Best Prop) silently capped higher choices.
    The guard still cuts every entry to exactly the chosen risk. Nasdaq 5M keeps its own 1% code cap.
Exact assert-once replacements; originals backed up to before/. python wire_riskfix.py"""
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent; B = ROOT.parent


def patch(path, reps, marker):
    p = B / path; raw = p.read_bytes(); crlf = b'\r\n' in raw; bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    if marker in text: print('already patched', path); return
    for old, new in reps:
        assert text.count(old) == 1, (path, old[:90], text.count(old)); text = text.replace(old, new)
    dest = ROOT / 'before-riskfix' / path
    if not dest.exists(): dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)
    out = text.replace('\n', '\r\n') if crlf else text
    p.write_bytes((b'\xef\xbb\xbf' if bom else b'') + out.encode('utf-8')); print('patched', path)


SELECT_OLD = """    $saved=Get-PropReadyReference $Probe $Existing
    if($null -eq $Existing){return [pscustomobject]@{reference=$saved;write=$true}}
    $was=[double]$saved.reference_balance;$now=[double]$Probe.account.balance
    if(-not $Ask -or [math]::Abs($now-$was) -le 0.005*$was){return [pscustomobject]@{reference=$saved;write=$false}}
"""
SELECT_NEW = """    $saved=Get-PropReadyReference $Probe $Existing
    if($null -eq $Existing){return [pscustomobject]@{reference=$saved;write=$true}}
    $was=[double]$saved.reference_balance;$now=[double]$Probe.account.balance
    if(-not $Ask){return [pscustomobject]@{reference=$saved;write=$false}}   # -ValidateOnly: read only
    # 2026-11-03 owner: every rerun starts FRESH from the current balance, so the per-trade cap and every limit follow today's account
    # size (an old saved baseline, e.g. 10,000 on a 100,000 account, made 1% = 100). Latched breach / day stops stay latched.
    Write-Host ("Rerun: new starting balance {0:N2} (previous saved {1:N2}). Every risk cap and loss limit is measured from the new value." -f $now,$was) -ForegroundColor Yellow
    return [pscustomobject]@{reference=(Get-PropReadyReference $Probe $null);write=$true}
"""
EA_RISK = ("    $inputs['FTMORiskCapPercent']=$capText\n"
           "    # 2026-11-03 fix: the guard never sends more than the strategy's own volume, so the strategy must ask for MORE than the chosen risk\n"
           "    # (1.5x, max 5%, as funded_v1); the guard then cuts every entry to exactly the chosen risk. Nasdaq 5M keeps its own 1% code cap.\n"
           "    $eaRisk=[Math]::Min(5.0,[Math]::Round(1.5*$capPercent,6)).ToString('G17',[Globalization.CultureInfo]::InvariantCulture)\n"
           "    foreach($riskKey in @('InpRiskPercent','InpMomentumRiskPercent','InpContrarianRiskPercent')){if($inputs.Contains($riskKey)){$inputs[$riskKey]=$eaRisk}}\n")
for helpers in ('_00 Live profiles/Packages/PropReady/Account-Helpers.ps1', '_00 Live profiles/Best Prop Portfolio 2026-10-20/Account-Helpers.ps1'):
    patch(helpers, [(SELECT_OLD, SELECT_NEW)], 'every rerun starts FRESH')
for installer in ('_00 Live profiles/Packages/PropReady/Install-Portfolio.ps1', '_00 Live profiles/Best Prop Portfolio 2026-10-20/Install-BestProp.ps1'):
    patch(installer, [("    $inputs['FTMORiskCapPercent']=$capText\n", EA_RISK)], '$eaRisk=')

# 3. Wording: reruns no longer retain the old baseline; warn that a prop firm's own limits still use the ORIGINAL balance.
WARN = ("Write-Host 'Every run starts a NEW baseline from the current balance (owner 2026-11-03). On a prop account that is already down, the firm still measures its loss limits from the ORIGINAL balance, so the guard floor/buffer can sit below the firm floor.' -ForegroundColor Yellow\n")
BUFFER_OLD = "if([double]$probe.account.equity -lt $initial*0.92){throw 'Account is below the retained 92% entry buffer; stop for review. Reinstallation does not reset losses.'}\n"
BUFFER_NEW = "if([double]$probe.account.equity -lt $initial*0.92){throw 'Equity is below 92% of the starting balance; stop for review.'}\n" + WARN
WRITE_OLD = "if($chosen.write){                                       # first install, or the user chose to start fresh\n"
WRITE_NEW = "if($chosen.write){                                       # first install or rerun: always a fresh baseline (owner 2026-11-03)\n"
patch('_00 Live profiles/Packages/PropReady/Install-Portfolio.ps1', [(BUFFER_OLD, BUFFER_NEW), (WRITE_OLD, WRITE_NEW),
      ("Write-Host 'Initial deployment starts a new baseline; reruns retain it. No automatic liquidation. Gaps/costs may exceed planned risk.'\n",
       "Write-Host 'No automatic liquidation. Gaps/costs may exceed planned risk.'\n"),
      ("# Preserve the baseline on reruns unless the user chose to start fresh; never clear terminal global-variable safety latches.\n",
       "# Write the fresh baseline; never clear terminal global-variable safety latches.\n")], 'Every run starts a NEW baseline')
patch('_00 Live profiles/Best Prop Portfolio 2026-10-20/Install-BestProp.ps1', [(BUFFER_OLD, BUFFER_NEW), (WRITE_OLD, WRITE_NEW)], 'Every run starts a NEW baseline')
