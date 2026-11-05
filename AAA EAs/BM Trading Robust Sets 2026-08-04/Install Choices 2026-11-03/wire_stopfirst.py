"""Owner 2026-11-05: every profile asks the Nasdaq 5M stop (ATR6 or 0.60%) first, then the DI filter. Asserted single-line edits, backups in before-stopfirst/.
Read-CalyxNasdaqVersion returns a value already chosen, so the later call in each installer stays as a harmless no-op. python wire_stopfirst.py patch"""
import shutil
from pathlib import Path

H = Path(__file__).resolve().parent; B = H.parent; L = B / '_00 Live profiles'; BAK = H / 'before-stopfirst'
STOP = '$NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion ([bool]$ValidateOnly)'
PROMPT = "if($PromptNasdaqDIFilter -and -not $PSBoundParameters.ContainsKey('NasdaqDIFilter') -and -not $ValidateOnly){"


def edit(path, ops):
    raw = path.read_bytes(); bom = raw.startswith(b'\xef\xbb\xbf'); text = raw.decode('utf-8-sig'); nl = '\r\n' if '\r\n' in text else '\n'; lines = text.split(nl)
    dest = BAK / path.relative_to(B); dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copy2(path, dest)
    for kind, anchor, new in ops:
        hits = [i for i, x in enumerate(lines) if x.startswith(anchor)]; assert len(hits) == 1, (path.name, anchor[:70], len(hits)); i = hits[0]
        if kind == 'before': lines[i:i] = new if isinstance(new, list) else [new]
        elif kind == 'replace': lines[i] = new
        elif kind == 'remove': del lines[i]
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'') + nl.join(lines).encode('utf-8')); print('patched', path.relative_to(B))


def main():
    edit(L / 'Start-LiveProfile.ps1', [('remove', ". (Join-Path $PSScriptRoot 'Calyx-InstallChoices.ps1')", None), ('remove', "if($Portfolio -ne 'orbs-only'){$NasdaqStopVersion=Read-CalyxNasdaqVersion", None),
                                       ('before', "foreach($field in @('NasdaqDIFilter','UsdJpyDIFilter')){", [". (Join-Path $PSScriptRoot 'Calyx-InstallChoices.ps1')", "if($Portfolio -ne 'orbs-only'){" + STOP + "}"])])
    edit(L / 'Best Prop Portfolio 2026-10-20/Install-BestProp.ps1', [('before', "    if(-not $PSBoundParameters.ContainsKey('NasdaqDIFilter')){", '    $NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion $false')])
    for p in ('Packages/PropReady/Install-Portfolio.ps1', 'Packages/FTMO-AnyBroker/Install-Portfolio.ps1', 'Packages/FTMO/Install-Portfolio.ps1'): edit(L / p, [('before', PROMPT, STOP)])
    edit(L / 'Packages/FundedV1/Install-FundedV1.ps1', [('before', "if(-not $NasdaqDIFilter){$NasdaqDIFilter=Read-Choice 'Nasdaq 5M DI filter", STOP)])
    edit(L / 'Packages/Turbo5/Install-Turbo5.ps1', [
        ('before', "    [ValidateSet('','NEW','OLD')][string]$NasdaqStopVersion='',", "    [ValidateSet('','ON','OFF')][string]$NasdaqDIFilter='',"),
        ('before', "$serverHasher=[Security.Cryptography.SHA256]::Create()", ["if(-not $NasdaqDIFilter){   # 2026-11-05 owner: asked here too. OFF is what this profile was tested and packaged with.",
                                                                          "    $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF [OFF]').Trim().ToUpperInvariant();if(-not $answer){$answer='OFF'}",
                                                                          "    if($answer -notin @('ON','OFF')){throw 'DI choice must be ON or OFF.'};$NasdaqDIFilter=$answer", "}",
                                                                          "if($NasdaqDIFilter -eq 'ON'){Write-Host 'DI ON is a custom selection: the Turbo 5 tests used DI OFF.' -ForegroundColor Yellow}"]),
        ('replace', "    if($entry.slug -eq 'nasdaq-5m-candle-momentum'){Set-CalyxNasdaqVersion $inputs $NasdaqStopVersion}", "    if($entry.slug -eq 'nasdaq-5m-candle-momentum'){$inputs['InpRequireDIAgreement']=if($NasdaqDIFilter -eq 'ON'){'true'}else{'false'};Set-CalyxNasdaqVersion $inputs $NasdaqStopVersion}"),
        ('replace', "Write-Host 'Nasdaq 5M DI filter: OFF. News and hourly EAs: not included.", 'Write-Host "Nasdaq 5M DI filter: $NasdaqDIFilter. News and hourly EAs: not included. No automatic liquidation. Gaps/slippage/costs can exceed planned stop risk."')])
    A = B / '_Auto Deploy'
    edit(A / 'Start-Dynamic-Portfolio.ps1', [
        ('before', "    [switch]$PromptNasdaqDIFilter,", "    [ValidateSet('', 'NEW', 'OLD')][string]$NasdaqStopVersion = '',"),
        ('replace', "if ($PromptNasdaqDIFilter -and -not $PSBoundParameters.ContainsKey('NasdaqDIFilter') -and -not $ValidateOnly) {", "if (-not $PSBoundParameters.ContainsKey('NasdaqDIFilter') -and -not $ValidateOnly -and -not $PreflightOnly -and -not $Yes) {   # 2026-11-05 owner: always asked, after the stop"),
        ('before', "$installer = Join-Path $PSScriptRoot 'Install-BMTradingPortfolio.ps1'", ". (Join-Path (Split-Path -Parent $PSScriptRoot) '_00 Live profiles\\Calyx-InstallChoices.ps1')"),
        ('replace', "Write-Host (\"  Nasdaq 5M DI14 filter: {0}; EMA12, ATR14 x6 initial stop (2026-11-02), ATR6 trail from +1R and no TP unchanged.\" -f $NasdaqDIFilter)", "Write-Host (\"  Nasdaq 5M DI14 filter: {0}; {1}; EMA12, ATR6 trail from +1R and no TP unchanged.\" -f $NasdaqDIFilter, (Get-CalyxNasdaqVersionText $NasdaqStopVersion))"),
        ('before', "$arguments += @('-NasdaqDIFilter', $NasdaqDIFilter)", "$arguments += @('-NasdaqStopVersion', $NasdaqStopVersion)")])
    text = (A / 'Start-Dynamic-Portfolio.ps1').read_bytes().decode('utf-8-sig'); nl = '\r\n' if '\r\n' in text else '\n'
    a = "if (-not $PSBoundParameters.ContainsKey('NasdaqDIFilter') -and -not $ValidateOnly -and -not $PreflightOnly -and -not $Yes) {"; assert text.count(a) == 1
    edit(A / 'Start-Dynamic-Portfolio.ps1', [('before', a, "$NasdaqStopVersion = Read-CalyxNasdaqVersion $NasdaqStopVersion ([bool]($ValidateOnly -or $PreflightOnly -or $Yes))")])
    edit(A / 'Start-Reviewed-Portfolio.ps1', [
        ('before', "    [string]$TargetTerminal='',", "    [ValidateSet('','NEW','OLD')][string]$NasdaqStopVersion='',"),
        ('before', ". (Join-Path $PSScriptRoot 'Reviewed-Portfolio-Policy.ps1')", ". (Join-Path (Split-Path -Parent $PSScriptRoot) '_00 Live profiles\\Calyx-InstallChoices.ps1')"),
        ('before', "    foreach ($entry in @($manifest.entries | Where-Object { $_.phase -eq 'live' -and $_.PSObject.Properties['di_input'] })) {", "    $NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion $false"),
        ('before', "if ([double]::IsNaN($RiskValue) -or [double]::IsInfinity($RiskValue) -or $RiskValue -le 0", "if (-not $NasdaqStopVersion) { $NasdaqStopVersion='NEW' }")])
    text = (A / 'Start-Reviewed-Portfolio.ps1').read_bytes().decode('utf-8-sig'); line = next(x for x in text.splitlines() if x.startswith("$invoke=@('-NoLogo'"))
    edit(A / 'Start-Reviewed-Portfolio.ps1', [('replace', "$invoke=@('-NoLogo'", line.replace("'-UseReviewedSelections',", "'-UseReviewedSelections','-NasdaqStopVersion',$NasdaqStopVersion,", 1))]); assert "'-UseReviewedSelections'," in line
    # The Current 14 builder inserts the stop question: put it ahead of its DI loop. Edge 10, Mixed 22 and current14_orb05.bat are generated from this.
    bp = B / 'Current14 Plus ORB05 Portfolio 2026-10-08/Build-Package.py'; dest = BAK / bp.relative_to(B); dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copy2(bp, dest)
    s = bp.read_text(encoding='utf-8'); old = '''s=sub1(s,"$candidates=@(Get-Mt5Candidates | Where-Object { $_.Running })","$NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion $false\\n    $candidates=@(Get-Mt5Candidates | Where-Object { $_.Running })")'''
    assert s.count(old) == 1; bp.write_text(s.replace(old, '''s=sub1(s,"    foreach ($parameter in @('NasdaqDIFilter','UsdJpyDIFilter')) {","    $NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion $false\\n    foreach ($parameter in @('NasdaqDIFilter','UsdJpyDIFilter')) {")'''), encoding='utf-8'); print('patched', bp.relative_to(B))
    e = L / 'Edge 10 - no guard/build.py'; dest = BAK / e.relative_to(B); dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copy2(e, dest)
    s = e.read_text(encoding='utf-8'); old = "if __name__ == '__main__':\n    build()\n"; assert s.count(old) == 1
    e.write_text(s.replace(old, """def refresh_installer():
    # python build.py installer: regenerate only the installer and the checksums; the compiled EAs and their parity evidence stay as they are.
    installer(10); paths = [TARGET / n for n in ('Package.json', 'Install-Portfolio.ps1', 'Installer-Helpers.ps1', 'Probe-MT5.py')] + sorted((TARGET / 'Experts').glob('*.ex5')) + sorted((TARGET / 'Sets').glob('*.set'))
    BL.save(TARGET / 'Checksums.json', {str(p.relative_to(TARGET)).replace(chr(92), '/'): BL.sha(p) for p in paths}); print('installer refreshed')


if __name__ == '__main__':
    refresh_installer() if sys.argv[1:] == ['installer'] else build()
"""), encoding='utf-8'); print('patched', e.relative_to(B))


if __name__ == '__main__':
    main()
