"""Build the Best Prop Portfolio (Prop Ready nine EAs at 1% / $100 on $10k). Offline: MetaEditor compile only, no MT5 terminal.

Derived from Packages/PropReady (integrity-checked, never written). Changes, all from the 2026-10-20 FTMO studies:
  guard per-entry cap 0.5% -> 1%, total open initial risk 2.25% -> 4.5%, same-symbol 1.5% -> 3% (daily reserve 3%,
  92% entry buffer, 90% floor and 5% daily hard loss unchanged); every strategy InpRiskPercent 0.5 -> 1.0 so the strategy
  request reaches the new cap; allocation default = 1% of current equity; default phase = Challenge;
  Nasdaq 5M DI agreement OFF by default (owner request). Strategy signals, stops, targets and the five 0.5R ORBs unchanged.

python build.py
"""
import hashlib, json, re, shutil, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent
SOURCE = LIVE / 'Packages' / 'PropReady'
PKG = HERE / 'package'; EAS = HERE / 'EAs'; SETS = HERE / 'Sets'
EDITOR = LIVE.parent / '_Backtests' / 'MT5-DMC-20260811' / 'MetaEditor64.exe'
VERSION = 'BEST-PROP9-1PCT-DIOFF-20261020'


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    raw = Path(p).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')


def sub1(text, old, new):
    assert text.count(old) == 1, ('expected exactly one occurrence', old)
    return text.replace(old, new)


def guard_text():
    g = read(SOURCE / 'CalyxFTMOGuard.mqh')
    g = sub1(g, '#define CALYX_PROP_READY_GUARD\n', '#define CALYX_PROP_READY_GUARD\n'
             '// Best Prop Portfolio 2026-10-20: derived from the Prop Ready guard. Per-entry cap 1%, total open risk 4.5%,\n'
             '// same-symbol 3% of the frozen reference balance; daily reserve 3%, 92% buffer, 90% floor, 5% daily loss unchanged.\n')
    g = sub1(g, 'input int FTMOAllocationMode=0;', 'input int FTMOAllocationMode=1;')
    g = sub1(g, 'input double FTMOAllocationValue=50.0;', 'input double FTMOAllocationValue=1.0;')
    g = sub1(g, 'input int    FTMOPhase=3;', 'input int    FTMOPhase=1;')
    g = sub1(g, 'double FTMORiskCap(){return FTMOReferenceBalance*0.005;}', 'double FTMORiskCap(){return FTMOReferenceBalance*0.01;}')
    g = sub1(g, 'double FTMOTotalRiskCap(){return FTMOReferenceBalance*0.0225;}', 'double FTMOTotalRiskCap(){return FTMOReferenceBalance*0.045;}')
    g = sub1(g, 'double FTMOSymbolRiskCap(){return FTMOReferenceBalance*0.015;}', 'double FTMOSymbolRiskCap(){return FTMOReferenceBalance*0.03;}')
    g = sub1(g, 'return "PR9"+IntegerToString(FTMOExpectedLogin)', 'return "BP9"+IntegerToString(FTMOExpectedLogin)')
    assert g.count('Prop ready') >= 6
    g = g.replace('Prop ready', 'Best Prop 9')              # journal / reject messages only
    for unchanged in ('FTMOReferenceBalance*0.03;', 'FTMOReferenceBalance*0.92;', 'FTMOReferenceBalance*0.90;', 'FTMOReferenceBalance*0.05;',
                      'ftmo_entries>=7 || losses>=3', 'FTMOLotsDown('):
        assert unchanged in g, unchanged
    return g


def compile_ea(path):
    log = path.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{EDITOR}" /portable /compile:"{path}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=180)
    text = read(log)
    assert '0 errors, 0 warnings' in text, text[-3000:]
    ex5 = path.with_suffix('.ex5'); assert ex5.is_file() and ex5.stat().st_mtime >= started - 2
    print('COMPILED', path.stem, flush=True)


def main():
    manifest = json.loads(read(SOURCE / 'PACKAGE.json'))
    before = {str(p): sha(p) for p in SOURCE.rglob('*') if p.is_file()}
    for name, digest in manifest['files'].items():
        assert sha(SOURCE / 'package' / name) == digest, ('Prop Ready package altered', name)
    assert sha(SOURCE / 'CalyxFTMOGuard.mqh') == manifest['guard_sha']
    assert len(manifest['entries']) == 9
    for d in (PKG, EAS, SETS):
        if d.exists():
            shutil.rmtree(d)                                   # only this package's own generated folders
        d.mkdir(parents=True)
    guard = guard_text()
    (HERE / 'CalyxFTMOGuard.mqh').write_text(guard, encoding='utf-8')
    (PKG / 'CalyxFTMOGuard.mqh').write_text(guard, encoding='utf-8')
    for f in (SOURCE / 'package').iterdir():                # shared sources (strategy code, trade shim)
        if f.suffix == '.mqh' and f.name != 'CalyxFTMOGuard.mqh':
            shutil.copy2(f, PKG / f.name)
    entries = []
    for e in manifest['entries']:
        slug = e['slug']; old_stem = Path(e['expert']).stem; stem = 'BP9-' + slug
        wrapper = read(SOURCE / 'package' / (old_stem + '.mq5'))
        (PKG / (stem + '.mq5')).write_text(wrapper, encoding='utf-8')
        compile_ea(PKG / (stem + '.mq5'))
        values = {}
        for line in read(SOURCE / 'package' / e['settings']).splitlines():
            if '=' in line:
                k, v = line.split('=', 1); values[k.strip()] = v.strip()
        assert values['InpRiskPercent'] == '0.5'
        values['InpRiskPercent'] = '1.0'
        if slug == 'nasdaq-5m-candle-momentum':
            values['InpRequireDIAgreement'] = 'false'
        if slug == 'usdjpy-london-open-momentum':
            assert values['InpRequireDIAgreement'] == 'true' and values['InpUseADXFilter'] == 'true' and values['InpADXMinimum'] == '20'
        if '-orb-' in slug:
            assert values['InpRewardRisk'] == '0.5'
        values.update(FTMOAllocationMode='1', FTMOAllocationValue='1.0', FTMOPhase='1', FTMOExpectedLogin='0', FTMOExpectedServer='',
                      FTMOExpectedSymbol='', FTMOExpectedCurrency='', FTMOReferenceBalance='0', FTMOStartUtcTime='0')
        set_text = '\n'.join(f'{k}={v}' for k, v in values.items()) + '\n'
        (PKG / (stem + '.set')).write_text(set_text, encoding='utf-8')
        shutil.copy2(PKG / (stem + '.ex5'), EAS / (stem + '.ex5'))
        shutil.copy2(PKG / (stem + '.set'), SETS / (stem + '.set'))
        entries.append(dict(slug=slug, label=e['label'], symbol=e['symbol'], timeframe=e['timeframe'], expert=stem + '.ex5', settings=stem + '.set',
                            magic=values.get('InpMagic'), source_expert=e['expert'], source_settings=e['settings'],
                            expert_sha=sha(PKG / (stem + '.ex5')), settings_sha=sha(PKG / (stem + '.set'))))
    files = {p.name: sha(p) for p in PKG.iterdir() if p.is_file() and p.suffix != '.log'}
    out = dict(version=VERSION, entries=entries, news_enabled=False, currency_mode='ACCOUNT_CURRENCY', hedging_required=True,
               reference_mode='PERSISTED_FIRST_INSTALL_BALANCE', default_phase='Challenge', default_allocation='1% of current equity',
               risk_cap_fraction=0.01, total_risk_fraction=0.045, symbol_risk_fraction=0.03, daily_reserve_fraction=0.03,
               entry_buffer_fraction=0.92, hard_floor_fraction=0.90, daily_hard_loss_fraction=0.05, strategy_risk_percent='1.0',
               nasdaq_di_default='OFF', usdjpy_di_default='ON', guard_sha=sha(HERE / 'CalyxFTMOGuard.mqh'),
               source_package=str(SOURCE), source_version=manifest['version'], source_guard_sha=manifest['guard_sha'], files=files)
    (HERE / 'PACKAGE.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    assert {str(p): sha(p) for p in SOURCE.rglob('*') if p.is_file()} == before, 'Prop Ready package must stay unchanged'
    print(f'Built {len(entries)} EAs ({VERSION}); Prop Ready package unchanged; no MT5 terminal touched.')


if __name__ == '__main__':
    main()
