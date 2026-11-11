"""Owner 2026-11-11: "update all profiles to go flat before weekend and holidays". Wires the Calyx Weekend Flat helper chart into every maintained installer.
Asserted edits (every anchor must match), backups of the original files in before/ (kept on re-runs), idempotent (marker 'Calyx Weekend Flat').

  python wire_weekendflat.py patch      edit installers, copy the EX5 into the no-guard packages, refresh their Checksums.json
  python wire_weekendflat.py manifest   write WEEKEND_FLAT.json (EX5 sha) after a compile

Families: A = guarded installers (dot-source Calyx-InstallChoices.ps1), B = Current 14-derived package installers (inline copies of the choice functions,
Installer-Helpers.ps1 chart audit), C = the canonical _Auto Deploy/Install-BMTradingPortfolio.ps1 (Full EA, reviewed, dynamic, Start-LiveProfile routes)."""
import hashlib, json, shutil, sys
from pathlib import Path

H = Path(__file__).resolve().parent; L = H.parent; B = L.parent; BAK = H / 'before'
FUNCS = (H / 'WeekendFlat-Functions.ps1').read_text(encoding='utf-8').replace('\r\n', '\n').rstrip('\n').split('\n')
MARK = 'Calyx Weekend Flat'
COUNT_OLD = "-Filter 'chart*.chr' -File -ErrorAction SilentlyContinue | Sort-Object Name)"
COUNT_NEW = "-Filter 'chart*.chr' -File -ErrorAction SilentlyContinue | Sort-Object Name | Where-Object { -not ([string](Get-Content -LiteralPath $_.FullName -Raw)).Contains('path=Experts\\Calyx Weekend Flat\\') })   # Calyx Weekend Flat helper chart is not a portfolio chart"
A = ['Best 1-Step/1-Step/Install-Best1Step-1Step.ps1', 'Core 9/1-Step/Install-Core9-1Step.ps1', 'Core 9/2-Step/Install-Core9-2Step.ps1', 'P4/1-Step/Install-P4-1Step.ps1',
     'P4/2-Step/Install-P4-2Step.ps1', 'Best Prop 15 Portfolio 2026-10-29/Install-BestProp15.ps1', 'Best Prop Portfolio 2026-10-20/Install-BestProp.ps1', 'ftmo 1_step/Install-FTMO1Step.ps1',
     'Packages/PropReady/Install-Portfolio.ps1', 'Packages/FTMO-AnyBroker/Install-Portfolio.ps1', 'Packages/FTMO/Install-Portfolio.ps1', 'Packages/FundedV1/Install-FundedV1.ps1',
     'Packages/Turbo5/Install-Turbo5.ps1']
BPK = ['Packages/Best1Step', 'Packages/Core9', 'Packages/Edge10', 'Packages/Mixed22', 'Packages/P4', 'Packages/ORB-only']
CUR = B / 'Current14 Plus ORB05 Portfolio 2026-10-08'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def load(path):
    raw = path.read_bytes(); bom = raw.startswith(b'\xef\xbb\xbf'); text = raw.decode('utf-8-sig'); nl = '\r\n' if '\r\n' in text else '\n'
    return text.split(nl), bom, nl


def save(path, lines, bom, nl):
    dest = BAK / path.relative_to(B.parent); dest.parent.mkdir(parents=True, exist_ok=True)
    if not dest.exists(): shutil.copy2(path, dest)
    path.write_bytes((b'\xef\xbb\xbf' if bom else b'') + nl.join(lines).encode('utf-8')); print('patched', path.relative_to(B))


def find(lines, anchor, path, exact=False, last=False):
    hits = [i for i, x in enumerate(lines) if (x == anchor if exact else x.strip().startswith(anchor.strip()))]
    assert hits and (last or len(hits) == 1), (path.name, anchor[:80], len(hits)); return hits[-1]


def patch_a(rel):
    p = L / rel; lines, bom, nl = load(p)
    if any("Read-CalyxWeekendFlat" in x for x in lines): print('already', rel); return
    i = find(lines, "[ValidateSet('','NEW','OLD')][string]$NasdaqStopVersion=''", p); ind = lines[i][:len(lines[i]) - len(lines[i].lstrip())]
    lines.insert(i, ind + "[ValidateSet('','ON','OFF')][string]$WeekendFlat='',")
    i = find(lines, "$NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion ([bool]$ValidateOnly)", p, exact=True, last=True)
    lines.insert(i + 1, "$WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat ([bool]$ValidateOnly)   # Calyx Weekend Flat (2026-11-11)")
    i = find(lines, "Test-ManagedProfile $profile $portfolio", p)
    lines.insert(i + 1, "Add-CalyxWeekendFlatChart $WeekendFlat $profile $dataRoot ([string]$portfolio[0].BrokerSymbol) ''   # Calyx Weekend Flat (2026-11-11)")
    save(p, lines, bom, nl)


def patch_b(pkg):
    """pkg = package folder holding Install-Portfolio.ps1 + Installer-Helpers.ps1 (+ Checksums.json)."""
    p = pkg / 'Install-Portfolio.ps1'; lines, bom, nl = load(p)
    if not any("Read-CalyxWeekendFlat" in x for x in lines):
        orb = not any(x.strip().startswith("[ValidateSet('', 'NEW', 'OLD')][string]$NasdaqStopVersion") for x in lines)
        i = find(lines, "[string]$TargetTerminal = ''," if orb else "[ValidateSet('', 'NEW', 'OLD')][string]$NasdaqStopVersion = ''", p)
        lines.insert(i, "    [ValidateSet('', 'ON', 'OFF')][string]$WeekendFlat = '',")
        i = find(lines, "function Main {" if orb else "function Read-CalyxNasdaqVersion", p); lines[i:i] = FUNCS + ['']
        i = find(lines, "    Assert-Risk $RiskMode $RiskValue" if orb else "$NasdaqStopVersion=Read-CalyxNasdaqVersion $NasdaqStopVersion $false", p, exact=orb)
        lines.insert(i + 1, "    $WeekendFlat=Read-CalyxWeekendFlat $WeekendFlat $false   # Calyx Weekend Flat (2026-11-11)")
        i = find(lines, "Assert-ChartInputs (Join-Path $stage 'Charts') $portfolio", p)
        lines.insert(i + 1, "    Add-CalyxWeekendFlatChart $WeekendFlat (Join-Path $stage 'Charts') $dataRoot ([string]$portfolio[0].BrokerSymbol) $PackageRoot   # Calyx Weekend Flat (2026-11-11)")
        save(p, lines, bom, nl)
    h = pkg / 'Installer-Helpers.ps1'; lines, bom, nl = load(h)
    if not any(MARK in x for x in lines):
        i = find(lines, "$chartFiles = @(Get-ChildItem -LiteralPath $ProfilePath " + COUNT_OLD, h); lines[i] = lines[i].replace(COUNT_OLD, COUNT_NEW); save(h, lines, bom, nl)
    shutil.copy2(H / 'Calyx Weekend Flat.ex5', pkg / 'Calyx Weekend Flat.ex5')
    ck = pkg / 'Checksums.json'
    if ck.exists():
        d = json.loads(ck.read_text(encoding='utf-8-sig'))
        for rel in list(d) + ['Calyx Weekend Flat.ex5']: d[rel] = sha(pkg / rel)
        ck.write_text(json.dumps(d, indent=2) + '\n', encoding='utf-8'); print('checksums', ck.relative_to(B))


def patch_c():
    p = B / '_Auto Deploy/Install-BMTradingPortfolio.ps1'; lines, bom, nl = load(p)
    if any("Read-CalyxWeekendFlat" in x for x in lines): print('already canonical'); return
    i = find(lines, "[ValidateSet('', 'NEW', 'OLD')][string]$NasdaqStopVersion", p); lines.insert(i, "    [ValidateSet('', 'ON', 'OFF')][string]$WeekendFlat = '',")
    i = find(lines, "$NasdaqStopVersion = Read-CalyxNasdaqVersion", p)
    lines.insert(i + 1, "$WeekendFlat = Read-CalyxWeekendFlat $WeekendFlat ([bool]($ValidateOnly -or $PreflightOnly -or $Yes))   # Calyx Weekend Flat (2026-11-11)")
    i = find(lines, "Test-ManagedProfile $profileTargetFull $portfolio 'Before MT5 start'", p)
    lines.insert(i + 1, "Add-CalyxWeekendFlatChart $WeekendFlat $profileTargetFull $dataRoot ([string]$portfolio[0].BrokerSymbol) ''   # Calyx Weekend Flat (2026-11-11)")
    i = find(lines, "$chartFiles = @(Get-ChildItem -LiteralPath $ProfilePath " + COUNT_OLD, p); lines[i] = lines[i].replace(COUNT_OLD, COUNT_NEW)
    save(p, lines, bom, nl)


def patch_shared():
    p = L / 'Calyx-InstallChoices.ps1'; lines, bom, nl = load(p)
    if any("Read-CalyxWeekendFlat" in x for x in lines): print('already shared'); return
    while lines and lines[-1] == '': lines.pop()
    save(p, lines + [''] + FUNCS + [''], bom, nl)


def manifest():
    ex5 = H / 'Calyx Weekend Flat.ex5'; d = dict(ex5_sha256=sha(ex5), source_sha256=sha(H / 'Calyx Weekend Flat.mq5'), built='2026-11-11', version='1.00')
    (H / 'WEEKEND_FLAT.json').write_text(json.dumps(d, indent=2) + '\n', encoding='utf-8'); print(d)


def main():
    assert (H / 'WEEKEND_FLAT.json').exists() and json.loads((H / 'WEEKEND_FLAT.json').read_text())['ex5_sha256'] == sha(H / 'Calyx Weekend Flat.ex5'), 'run manifest first'
    patch_shared()
    for rel in A: patch_a(rel)
    for rel in BPK: patch_b(L / rel)
    patch_b(CUR); patch_c()


if __name__ == '__main__':
    manifest() if sys.argv[1:] == ['manifest'] else main()
