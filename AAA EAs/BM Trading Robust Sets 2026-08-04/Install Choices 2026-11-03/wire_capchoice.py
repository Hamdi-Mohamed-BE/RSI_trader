"""Open-risk cap choice at install (owner 2026-11-03: "make ask for cap option when installing the bat" + "make it 4.5,6,8 and no cap
and 3x , no cap per symbol"). Prop Ready guard family: Prop ready / Codex, FTMO any-broker, Best Prop 9, Best Prop 15.
  * Guard: two new inputs, FTMOTotalRiskMultiple (default 4.5; 0 = no total cap) and FTMOSymbolRiskMultiple (default 3; 0 = no
    per-symbol cap). Defaults are bit-identical to the old constants: x*(4.5/100.0) == x*0.045 and x*(3.0/100.0) == x*0.03 in IEEE
    doubles (correctly rounded division of exact operands). Every other guard rule is unchanged.
  * Installers ask: total 4.5 / 6 / 8 / none, per symbol 3 / none (Enter = tested default); -ValidateOnly never asks.
  * Every wrapper is recompiled (MetaEditor only, no terminal); PACKAGE.json / copies / READMEs get the new hashes.
Stages:  python wire_capchoice.py patch | compile <PropReady|FTMO-AnyBroker|BP9|BP15> | finish
Originals backed up to before-capchoice/."""
import hashlib, json, shutil, subprocess, sys, time
from pathlib import Path

ROOT = Path(__file__).resolve().parent; B = ROOT.parent; LIVE = B / '_00 Live profiles'
EDITOR = B / '_Backtests' / 'MT5-DMC-20260811' / 'MetaEditor64.exe'
PKGS = {'PropReady': LIVE / 'Packages/PropReady', 'FTMO-AnyBroker': LIVE / 'Packages/FTMO-AnyBroker',
        'BP9': LIVE / 'Best Prop Portfolio 2026-10-20', 'BP15': LIVE / 'Best Prop 15 Portfolio 2026-10-29'}
SHAMAP = ROOT / 'capchoice-sha-map.json'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def backup(p):
    dest = ROOT / 'before-capchoice' / p.relative_to(B)
    if not dest.exists(): dest.parent.mkdir(parents=True, exist_ok=True); shutil.copy2(p, dest)


def patch(p, reps, marker):
    raw = p.read_bytes(); crlf = b'\r\n' in raw; bom = raw.startswith(b'\xef\xbb\xbf')
    text = raw.decode('utf-8-sig').replace('\r\n', '\n')
    if marker in text: print('already patched', p.relative_to(B)); return
    for old, new in reps:
        assert text.count(old) == 1, (str(p), old[:100], text.count(old)); text = text.replace(old, new)
    backup(p); out = text.replace('\n', '\r\n') if crlf else text
    p.write_bytes((b'\xef\xbb\xbf' if bom else b'') + out.encode('utf-8')); print('patched', p.relative_to(B))


GUARD = [
    (" Totals scale: 4.5x open, 3x per symbol\n",
     " Totals: the two multiples below\n"
     "input double FTMOTotalRiskMultiple=4.5; // total open stop risk = this x the per-entry cap; 0 = no total cap (installer: 4.5 / 6 / 8 / none, 2026-11-03)\n"
     "input double FTMOSymbolRiskMultiple=3.0; // same-symbol open stop risk = this x the per-entry cap; 0 = no per-symbol cap (installer: 3 / none)\n"),
    ("double FTMOTotalRiskCap(){return FTMOReferenceBalance*FTMORiskCapPercent*0.045;}",
     "double FTMOTotalRiskCap(){return FTMOTotalRiskMultiple<=0?DBL_MAX:FTMOReferenceBalance*FTMORiskCapPercent*(FTMOTotalRiskMultiple/100.0);}"),
    ("double FTMOSymbolRiskCap(){return FTMOReferenceBalance*FTMORiskCapPercent*0.03;}",
     "double FTMOSymbolRiskCap(){return FTMOSymbolRiskMultiple<=0?DBL_MAX:FTMOReferenceBalance*FTMORiskCapPercent*(FTMOSymbolRiskMultiple/100.0);}"),
    ("\nbool FTMOAllocationValid() {\n",
     "\nbool FTMOCapMultipleValid(const double m){return MathIsValidNumber(m) && (m==0 || (m>=1 && m<=20));}   // 0 = that cap OFF\n"
     "bool FTMOAllocationValid() {\n"),
    ("&& MathIsValidNumber(FTMORiskCapPercent) && FTMORiskCapPercent>0 && FTMORiskCapPercent<=2.0;",
     "&& MathIsValidNumber(FTMORiskCapPercent) && FTMORiskCapPercent>0 && FTMORiskCapPercent<=2.0\n"
     "      && FTMOCapMultipleValid(FTMOTotalRiskMultiple) && FTMOCapMultipleValid(FTMOSymbolRiskMultiple);"),
]
BP_COMMENT = ("total open 4.5x and same-symbol 3x that cap", "total open 4.5x (or 6x / 8x / none) and same-symbol 3x (or none) that cap")

CHOICES = r'''
# 2026-11-03 owner: "make ask for cap option when installing the bat ... 4.5, 6, 8 and no cap and 3x, no cap per symbol".
# Prop Ready guard family only (Prop ready / Codex, FTMO any-broker, Best Prop 9 / 15). Enter keeps the tested 4.5 R / 3 R.
function Write-CalyxRiskCapHelp {
    Write-Host ''
    Write-Host 'OPEN-RISK CAPS - how much stop-loss risk may be open at the same time?' -ForegroundColor Cyan
    Write-Host '  R = your chosen risk per trade, measured on the starting balance. Every open trade counts its initial stop-loss risk.'
    Write-Host '  TOTAL cap: a new entry waits while all open trades plus the new one would exceed this many R.'
    Write-Host '    1 = 4.5 R (default, tested)   2 = 6 R   3 = 8 R   4 = no total cap'
    Write-Host '  PER-SYMBOL cap: the same rule for the trades on one symbol (gold, Nasdaq or USDJPY).'
    Write-Host '    1 = 3 R (default, tested)   2 = no per-symbol cap'
    Write-Host '  All other guards stay ON. The 3% daily reserve counts each open trade at 1.25 x its risk, so open risk stops near'
    Write-Host '  2.4% of the balance anyway (= 2.4 R at 1% risk, 4.8 R at 0.5%). At 1% risk 4.5 / 6 / 8 / none therefore behave the same.'
    Write-Host '  FTMO $100k replay (2026-11-03): 6 R = same pass rate at 1%, same Monte Carlo but a worse 2021-23 history at 0.5%.' -ForegroundColor Yellow
    Write-Host '  8 R and "no cap" were not tested. Bigger caps allow more trades (often several gold EAs) to lose at the same time.' -ForegroundColor Yellow
}

function Read-CalyxTotalRiskCap([string]$Current, [bool]$NoPrompt) {
    if ($Current) { if ($Current -notin @('4.5', '6', '8', 'NONE')) { throw 'Total open-risk cap must be 4.5, 6, 8 or NONE.' }; return $Current }
    if ($NoPrompt) { return '4.5' }
    Write-CalyxRiskCapHelp
    $answer = (Read-Host 'Total open-risk cap: 1 = 4.5 R, 2 = 6 R, 3 = 8 R, 4 = no cap [1]').Trim()
    $choice = @{ '' = '4.5'; '1' = '4.5'; '2' = '6'; '3' = '8'; '4' = 'NONE' }[$answer]
    if (-not $choice) { throw 'Choose 1, 2, 3 or 4.' }
    return $choice
}

function Read-CalyxSymbolRiskCap([string]$Current, [bool]$NoPrompt) {
    if ($Current) { if ($Current -notin @('3', 'NONE')) { throw 'Per-symbol cap must be 3 or NONE.' }; return $Current }
    if ($NoPrompt) { return '3' }
    $answer = (Read-Host 'Per-symbol open-risk cap: 1 = 3 R, 2 = no cap [1]').Trim()
    $choice = @{ '' = '3'; '1' = '3'; '2' = 'NONE' }[$answer]
    if (-not $choice) { throw 'Choose 1 or 2.' }
    return $choice
}

# Guard input value: the multiple, or 0 = that cap OFF.
function Get-CalyxCapMultiple([string]$Choice) { if ($Choice -eq 'NONE') { '0' } else { $Choice } }

# "450.00 (4.5 R)" or "no cap"; $Unit = one R in account currency.
function Get-CalyxCapText([string]$Choice, [double]$Unit) {
    if ($Choice -eq 'NONE') { return 'no cap' }
    $m = [double]::Parse($Choice, [Globalization.CultureInfo]::InvariantCulture)
    return ('{0:N2} ({1} R)' -f ($Unit * $m), $Choice)
}
'''

UNIT = "($initial*$capPercent/100)"
INSTALLERS = {
    LIVE / 'Packages/PropReady/Install-Portfolio.ps1':
        "Write-Host \"Limits: $([math]::Round($initial*$capPercent*0.045,2)) open risk; $([math]::Round($initial*$capPercent*0.03,2)) per symbol; ",
    LIVE / 'Best Prop Portfolio 2026-10-20/Install-BestProp.ps1':
        "Write-Host \"Limits: $([math]::Round($initial*$capPercent*0.045,2)) total open risk; $([math]::Round($initial*$capPercent*0.03,2)) per symbol; ",
}


def do_patch():
    for name, d in PKGS.items():
        for g in (d / 'CalyxFTMOGuard.mqh', d / 'package' / 'CalyxFTMOGuard.mqh'):
            reps = GUARD + ([BP_COMMENT] if name in ('BP9', 'BP15') else [])
            patch(g, reps, 'FTMOTotalRiskMultiple')
        assert sha(d / 'CalyxFTMOGuard.mqh') == sha(d / 'package' / 'CalyxFTMOGuard.mqh'), name
    assert sha(PKGS['PropReady'] / 'CalyxFTMOGuard.mqh') == sha(PKGS['FTMO-AnyBroker'] / 'CalyxFTMOGuard.mqh')
    # generators: keep their guard assertions true and the Best Prop header comment consistent
    patch(PKGS['BP9'] / 'build.py', [
        ("    assert 'FTMOReferenceBalance*FTMORiskCapPercent*0.045;' in g and 'FTMOReferenceBalance*FTMORiskCapPercent*0.03;' in g\n",
         "    assert 'FTMOReferenceBalance*FTMORiskCapPercent*(FTMOTotalRiskMultiple/100.0);' in g and 'FTMOSymbolRiskMultiple=3.0;' in g   # 2026-11-03 cap choice\n"),
        ("'// total open 4.5x and same-symbol 3x that cap, of the frozen", "'// total open 4.5x (or 6x / 8x / none) and same-symbol 3x (or none) that cap, of the frozen")],
        'FTMOTotalRiskMultiple')
    patch(PKGS['BP15'] / 'build.py', [
        ("'FTMOReferenceBalance*FTMORiskCapPercent*0.045;',\n                      'FTMOReferenceBalance*FTMORiskCapPercent*0.03;',",
         "'FTMOReferenceBalance*FTMORiskCapPercent*(FTMOTotalRiskMultiple/100.0);',\n                      'FTMOReferenceBalance*FTMORiskCapPercent*(FTMOSymbolRiskMultiple/100.0);',")],
        'FTMOTotalRiskMultiple')
    # shared prompts
    ch = LIVE / 'Calyx-InstallChoices.ps1'
    if 'Read-CalyxTotalRiskCap' not in ch.read_text(encoding='utf-8-sig'):
        backup(ch); raw = ch.read_bytes(); crlf = b'\r\n' in raw
        ch.write_bytes(raw + (CHOICES.replace('\n', '\r\n') if crlf else CHOICES).encode('utf-8')); print('patched', ch.relative_to(B))
    for path, limits in INSTALLERS.items():
        patch(path, [
            ("    [ValidateSet('','NEW','OLD')][string]$NasdaqStopVersion='',\n",
             "    [ValidateSet('','NEW','OLD')][string]$NasdaqStopVersion='',\n"
             "    [ValidateSet('','4.5','6','8','NONE')][string]$TotalRiskCap='',\n    [ValidateSet('','3','NONE')][string]$SymbolRiskCap='',\n"),
            ("Write-Host ('Nasdaq 5M: '+(Get-CalyxNasdaqVersionText $NasdaqStopVersion))\n",
             "Write-Host ('Nasdaq 5M: '+(Get-CalyxNasdaqVersionText $NasdaqStopVersion))\n"
             "$TotalRiskCap=Read-CalyxTotalRiskCap $TotalRiskCap ([bool]$ValidateOnly)\n"
             "$SymbolRiskCap=Read-CalyxSymbolRiskCap $SymbolRiskCap ([bool]$ValidateOnly)\n"
             "Write-Host (\"Open-risk caps: total \"+$(if($TotalRiskCap -eq 'NONE'){'no cap'}else{\"$TotalRiskCap R\"})+\"; per symbol \"+$(if($SymbolRiskCap -eq 'NONE'){'no cap'}else{\"$SymbolRiskCap R\"}))\n"),
            ("    $inputs['FTMORiskCapPercent']=$capText\n",
             "    $inputs['FTMORiskCapPercent']=$capText\n"
             "    $inputs['FTMOTotalRiskMultiple']=Get-CalyxCapMultiple $TotalRiskCap;$inputs['FTMOSymbolRiskMultiple']=Get-CalyxCapMultiple $SymbolRiskCap\n"),
            (limits, f"Write-Host \"Limits: total open risk $(Get-CalyxCapText $TotalRiskCap {UNIT}); per symbol $(Get-CalyxCapText $SymbolRiskCap {UNIT}); "),
            ("(per-entry cap $capPercent% of reference)", "(per-entry cap $capPercent% of reference); open-risk caps total $TotalRiskCap R / symbol $SymbolRiskCap R"),
        ], 'Read-CalyxTotalRiskCap')


def compile_ea(path):
    log = path.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{EDITOR}" /portable /compile:"{path}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    raw = log.read_bytes(); text = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig', errors='replace')
    assert '0 errors, 0 warnings' in text, text[-2000:]
    ex5 = path.with_suffix('.ex5'); assert ex5.is_file() and ex5.stat().st_mtime >= started - 2, path
    print('COMPILED', path.stem, flush=True)


def do_compile(name):
    d = PKGS[name] / 'package'; m = json.loads(SHAMAP.read_text()) if SHAMAP.exists() else {}
    for w in sorted(d.glob('*.mq5')):
        ex5 = w.with_suffix('.ex5'); old = sha(ex5)
        if any(v.get('file') == str(ex5) for v in m.values()): print('skip (done)', w.stem); continue
        backup(ex5); compile_ea(w)
        m[old] = dict(new=sha(ex5), file=str(ex5)); SHAMAP.write_text(json.dumps(m, indent=1))


def do_finish():
    m = {k: v['new'] for k, v in json.loads(SHAMAP.read_text()).items()}
    for name, d in PKGS.items():                               # guard shas: old from backup, new from disk
        old = sha(ROOT / 'before-capchoice' / (d / 'CalyxFTMOGuard.mqh').relative_to(B)); new = sha(d / 'CalyxFTMOGuard.mqh')
        assert m.get(old, new) == new, ('conflicting guard map', name); m[old] = new
    # EAs/ copies (Best Prop 9 / 15 keep their own; Prop ready / FTMO folders are regenerated by tools.build_live_profiles launchers)
    for name in ('BP9', 'BP15'):
        for ex5 in (PKGS[name] / 'EAs').glob('*.ex5'):
            src = PKGS[name] / 'package' / ex5.name; assert src.is_file(), ex5
            backup(ex5); shutil.copy2(src, ex5)
    skip = ('superseded', 'before', 'INVALID')
    for f in [p for p in LIVE.rglob('*') if p.suffix in ('.json', '.md', '.txt') and p.is_file() and not any(s in str(p) for s in skip)]:
        raw = f.read_bytes()
        try: t = raw.decode('utf-8')                           # bytes as-is: keeps BOM and line endings
        except UnicodeDecodeError: continue                    # UTF-16 guides etc. carry no hashes
        n = 0
        for old, new in m.items():
            if old in t: n += t.count(old); t = t.replace(old, new)
        if n: backup(f); f.write_bytes(t.encode('utf-8')); print('rehashed', f.relative_to(LIVE), n)
    for name, d in PKGS.items():                               # every manifest entry matches the disk again
        man = json.loads((d / 'PACKAGE.json').read_text(encoding='utf-8-sig'))
        assert man['guard_sha'] == sha(d / 'CalyxFTMOGuard.mqh'), name
        for fn, digest in man['files'].items(): assert sha(d / 'package' / fn) == digest, (name, fn)
        for e in man['entries']: assert sha(d / 'package' / e['expert']) == e['expert_sha'], (name, e['expert'])
        print('manifest OK', name, len(man['entries']))


if __name__ == '__main__':
    {'patch': lambda: do_patch(), 'compile': lambda: do_compile(sys.argv[2]), 'finish': lambda: do_finish()}[sys.argv[1]]()
