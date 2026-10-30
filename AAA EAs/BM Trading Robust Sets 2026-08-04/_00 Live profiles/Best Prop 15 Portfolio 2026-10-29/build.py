"""Build the Best Prop 15 Portfolio (owner 2026-10-29): the Best Prop 9 EAs + EMA3, 3 Way Gold, Gold Overnight Value Area and all three
DMCs (DMC Current XAU, DMC Fresh Reaction XAU, DMC Fresh Reaction US100). Offline: MetaEditor compile only, no MT5 terminal.

Sources (integrity-checked, never written):
  * Packages/PropReady      -> the nine Best Prop EAs (same wrappers / SETs Best Prop 9 uses);
  * Packages/FTMO-AnyBroker -> EMA3, 3 Way Gold (market entries: the guard admits no pending orders), Gold Overnight, DMC Current XAU,
                               DMC Fresh Reaction US100 (wrappers compiled against the SAME Prop Ready guard, sha-checked);
  * DMC Fresh Reaction XAU  -> the Fresh Reaction wrapper (same EA source as US100) + the catalog preset
                               `Selected Portfolio Settings 2026-09-01/21 DMC Fresh Reaction XAU - ASIA 3R - DYNAMIC 50-20.set`,
                               converted exactly as the FTMO build converted the US100 preset (adaptive off + unarmed guard inputs).
Guard = Best Prop 9's guard (1% per entry, 4.5% total open, 3% per symbol, 3% daily reserve, 92% buffer, 90% floor, 5% daily loss,
7 entries / 3 losses per day) with its own state key "BP15" so it never shares latches with Best Prop 9. Every strategy
InpRiskPercent = 1.0; Nasdaq 5M DI OFF by default; five ORBs keep 0.5R. Strategy signals, stops and targets unchanged.
The installer is generated from Best Prop 9's installer by asserted text substitutions.

python build.py
"""
import hashlib, json, shutil, subprocess, time
from pathlib import Path

HERE = Path(__file__).resolve().parent
LIVE = HERE.parent
ROOT = LIVE.parent                                           # BM Trading Robust Sets 2026-08-04
PROP = LIVE / 'Packages' / 'PropReady'
ANY = LIVE / 'Packages' / 'FTMO-AnyBroker'
BP9 = LIVE / 'Best Prop Portfolio 2026-10-20'
XAU_FRESH_SET = ROOT / 'Selected Portfolio Settings 2026-09-01' / '21 DMC Fresh Reaction XAU - ASIA 3R - DYNAMIC 50-20.set'
PKG = HERE / 'package'; EAS = HERE / 'EAs'; SETS = HERE / 'Sets'
EDITOR = ROOT / '_Backtests' / 'MT5-DMC-20260811' / 'MetaEditor64.exe'
VERSION = 'BEST-PROP15-CHOSENRISK-DIOFF-20261030'   # 2026-10-30: per-entry cap = the installer's chosen risk (default 1%)
ADDED = ['ema3', '3-way-gold', 'gold-overnight-value-area', 'dmc-current-xau', 'dmc-fresh-reaction-us100']
FRESH_XAU = dict(slug='dmc-fresh-reaction-xau', label='DMC Fresh Reaction XAU', symbol='XAUUSD', timeframe='H1')
UNARMED = dict(FTMOExpectedLogin='0', FTMOExpectedServer='', FTMOExpectedSymbol='', FTMOExpectedCurrency='', FTMOReferenceBalance='0',
               FTMOStartUtcTime='0')


def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def read(p):
    raw = Path(p).read_bytes()
    return raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig').replace('\r\n', '\n')


def sub1(text, old, new):
    assert text.count(old) == 1, ('expected exactly one occurrence', old)
    return text.replace(old, new)


def set_values(path):
    out = {}
    for line in read(path).splitlines():
        if '=' in line and not line.startswith(';'):
            k, v = line.split('=', 1); out[k.strip()] = v.strip().split('||')[0]      # optimizer format -> value
    return out


def check_package(src, n):
    m = json.loads(read(src / 'PACKAGE.json'))
    for name, digest in m['files'].items():
        assert sha(src / 'package' / name) == digest, (src.name, 'package altered', name)
    assert sha(src / 'CalyxFTMOGuard.mqh') == m['guard_sha'] and len(m['entries']) == n
    return m


def guard_text():
    g = read(BP9 / 'CalyxFTMOGuard.mqh')
    assert sha(BP9 / 'CalyxFTMOGuard.mqh') == json.loads(read(BP9 / 'PACKAGE.json'))['guard_sha'], 'Best Prop 9 guard altered'
    assert g.count('Best Prop 9') >= 6
    g = g.replace('Best Prop 9', 'Best Prop 15')             # journal / reject messages only
    g = sub1(g, '// Best Prop Portfolio 2026-10-20: derived from the Prop Ready guard.',
             '// Best Prop 15 Portfolio 2026-10-29: the Best Prop 9 guard (same limits) with its own state key BP15.\n'
             '// Best Prop Portfolio 2026-10-20: derived from the Prop Ready guard.')
    g = sub1(g, 'return "BP9"+IntegerToString(FTMOExpectedLogin)', 'return "BP15"+IntegerToString(FTMOExpectedLogin)')
    for unchanged in ('input double FTMORiskCapPercent=1.0;', 'FTMOReferenceBalance*FTMORiskCapPercent/100.0;', 'FTMOReferenceBalance*FTMORiskCapPercent*0.045;',
                      'FTMOReferenceBalance*FTMORiskCapPercent*0.03;', 'FTMOReferenceBalance*0.03;', 'FTMOReferenceBalance*0.92;',
                      'FTMOReferenceBalance*0.90;', 'FTMOReferenceBalance*0.05;', 'ftmo_entries>=7 || losses>=3', 'FTMOLotsDown('):
        assert unchanged in g, unchanged
    return g


def compile_ea(path):
    log = path.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{EDITOR}" /portable /compile:"{path}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=240)
    text = read(log)
    assert '0 errors, 0 warnings' in text, text[-3000:]
    ex5 = path.with_suffix('.ex5'); assert ex5.is_file() and ex5.stat().st_mtime >= started - 2
    print('COMPILED', path.stem, flush=True)


def installer_text():
    s = read(BP9 / 'Install-BestProp.ps1')
    rep = [
        ("# Best Prop Portfolio 2026-10-20: the Prop Ready nine EAs at 1% (USD 100 on 10k) with the rebuilt 1% guard.",
         "# Best Prop 15 Portfolio 2026-10-29: Best Prop 9 + EMA3, 3 Way Gold, Gold Overnight and the three DMCs, same guard (cap = chosen risk).\n"
         "# GENERATED by build.py from Best Prop Portfolio 2026-10-20/Install-BestProp.ps1; do not edit by hand."),
        ("if($manifest.entries.Count -ne 9 -or", "if($manifest.entries.Count -ne 15 -or"),
        ("'us100-h1-orb-13utc','us100-orb-new-york-m30','us100-selective-orb-v3','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30')",
         "'us100-h1-orb-13utc','us100-orb-new-york-m30','us100-selective-orb-v3','xau-orb-new-york-m30','xau-orb-london-ny-overlap-m30',\n"
         "        'ema3','3-way-gold','gold-overnight-value-area','dmc-current-xau','dmc-fresh-reaction-xau','dmc-fresh-reaction-us100')"),
        ("throw 'Best Prop roster changed.'", "throw 'Best Prop 15 roster changed.'"),
        ("Write-Host 'BEST PROP PORTFOLIO - nine EAs, 1% risk per trade (capped at 1% of the starting balance).'",
         "Write-Host 'BEST PROP 15 PORTFOLIO - fifteen EAs; you choose the risk per trade (max 2% of the starting balance) and the DI filters.'"),
        ("Write-Host 'BEST PROP PORTFOLIO: nine EAs / five ORBs at 0.5R / broker-neutral MT5 hedging profile.'",
         "Write-Host 'BEST PROP 15 PORTFOLIO: fifteen EAs / five ORBs at 0.5R / broker-neutral MT5 hedging profile.'"),
        ("Write-Host 'PASS: 9 integrity-checked guarded EAs", "Write-Host 'PASS: 15 integrity-checked guarded EAs"),
        ('("MQL5\\Files\\Calyx-BestProp9-$login-$serverHash.json")', '("MQL5\\Files\\Calyx-BestProp15-$login-$serverHash.json")'),
        ("$ProfileName='Calyx-BestProp9-'+$login", "$ProfileName='Calyx-BestProp15-'+$login"),
        ('$expected="BEST PROP $login $currency $Phase"', '$expected="BEST PROP 15 $login $currency $Phase"'),
        ("'Best Prop installed profile'", "'Best Prop 15 installed profile'"),
        ("'.best-prop-backup-'", "'.best-prop15-backup-'"),
        ('"Portfolio: Best Prop Portfolio 2026-10-20 (nine EAs, 1%)', '"Portfolio: Best Prop 15 Portfolio 2026-10-29 (fifteen EAs)'),
        ('Review all nine charts and inputs', 'Review all fifteen charts and inputs'),
        # owner 2026-10-29: custom risk (type + value) and a DI choice for every EA that has one (Nasdaq 5M, USDJPY)
        ("""    if(-not $PSBoundParameters.ContainsKey('RiskValue')){
        $answer=(Read-Host 'Risk per trade, % of current equity, e.g. 0.5 / 1.0 / 2.0 (max 2) [1.0]').Trim()
        if($answer){$RiskValue=[double]::Parse($answer,[Globalization.CultureInfo]::InvariantCulture)}
    }""",
         """    if(-not $PSBoundParameters.ContainsKey('RiskMode')){
        $answer=(Read-Host 'Risk type: 1 = % of current equity, 2 = fixed amount per trade in the account currency [1]').Trim()
        if(-not $answer){$answer='1'}
        $RiskMode=@{'1'='PERCENT';'2'='FIXED_USD'}[$answer]
        if(-not $RiskMode){throw 'Risk type must be 1 or 2.'}
    }
    if(-not $PSBoundParameters.ContainsKey('RiskValue')){
        $prompt=if($RiskMode -eq 'PERCENT'){'Risk per trade, % of current equity, e.g. 0.25 / 0.5 / 1.0 / 2.0 (max 2) [1.0]'}else{'Risk per trade, fixed amount in the account currency, e.g. 500 (max 2% of the starting balance) [100]'}
        $answer=(Read-Host $prompt).Trim()
        $RiskValue=if($answer){[double]::Parse($answer.Replace(',','.'),[Globalization.CultureInfo]::InvariantCulture)}elseif($RiskMode -eq 'PERCENT'){1.0}else{100.0}
    }"""),
        ("""        $NasdaqDIFilter=$answer
    }
}""",
         """        $NasdaqDIFilter=$answer
    }
    if(-not $PSBoundParameters.ContainsKey('UsdJpyDIFilter')){
        $answer=(Read-Host 'USDJPY London DI filter ON or OFF (its ADX20 filter stays on) [ON]').Trim().ToUpperInvariant()
        if(-not $answer){$answer='ON'}
        if($answer -notin @('ON','OFF')){throw 'DI choice must be ON or OFF.'}
        $UsdJpyDIFilter=$answer
    }
}"""),
    ]
    for a, b in rep:
        s = sub1(s, a, b)
    return s.replace('\n', '\r\n')


def main():
    prop = check_package(PROP, 9); anyb = check_package(ANY, 17)
    assert prop['guard_sha'] == anyb['guard_sha'], 'the two source packages must share the Prop Ready guard'
    before = {str(p): sha(p) for src in (PROP, ANY, BP9) for p in src.rglob('*') if p.is_file()}
    for d in (PKG, EAS, SETS):
        if d.exists():
            shutil.rmtree(d)                                   # only this package's own generated folders
        d.mkdir(parents=True)
    guard = guard_text()
    (HERE / 'CalyxFTMOGuard.mqh').write_text(guard, encoding='utf-8'); (PKG / 'CalyxFTMOGuard.mqh').write_text(guard, encoding='utf-8')
    for src in (PROP, ANY):                                   # shared strategy sources + trade shim (identical names must be identical files)
        for f in (src / 'package').iterdir():
            if f.suffix == '.mqh' and f.name != 'CalyxFTMOGuard.mqh':
                if (PKG / f.name).exists():
                    assert sha(PKG / f.name) == sha(f), ('conflicting shared source', f.name)
                else:
                    shutil.copy2(f, PKG / f.name)
    jobs = [(e, PROP, None) for e in prop['entries']] + [(next(e for e in anyb['entries'] if e['slug'] == s), ANY, None) for s in ADDED]
    us = next(e for e in anyb['entries'] if e['slug'] == 'dmc-fresh-reaction-us100')
    jobs.append((dict(us, **FRESH_XAU, settings=None), ANY, XAU_FRESH_SET))
    entries = []; magics = {}
    for e, src, preset in jobs:
        slug = e['slug']; stem = 'BP15-' + slug
        (PKG / (stem + '.mq5')).write_text(read(src / 'package' / (Path(e['expert']).stem + '.mq5')), encoding='utf-8')
        compile_ea(PKG / (stem + '.mq5'))
        if preset is None:
            values = set_values(src / 'package' / e['settings'])
        else:                                                  # catalog preset -> same conversion the FTMO build applied to US100
            ref_src = set_values(ROOT / 'Selected Portfolio Settings 2026-09-01' / '22 DMC Fresh Reaction US100 - NEW YORK 2R - DYNAMIC 50-20.set')
            ref_pkg = set_values(ANY / 'package' / us['settings'])
            added = {k: v for k, v in ref_pkg.items() if k not in ref_src}
            assert {k for k in ref_pkg if k in ref_src and ref_pkg[k] != ref_src[k]} == {'InpRiskPercent'}, 'unexpected FTMO conversion'
            values = set_values(preset); assert values['InpMagic'] == '1090901' and values['InpRewardRisk'] == '3.0'
            values.update(added); values['InpRiskPercent'] = '0.5'
        assert values['InpRiskPercent'] == '0.5', (slug, values.get('InpRiskPercent'))
        assert values.get('InpAdaptivePortfolioControls') == 'false', slug
        values['InpRiskPercent'] = '1.0'
        if slug == 'nasdaq-5m-candle-momentum': values['InpRequireDIAgreement'] = 'false'
        if slug == 'usdjpy-london-open-momentum':
            assert values['InpRequireDIAgreement'] == 'true' and values['InpUseADXFilter'] == 'true' and values['InpADXMinimum'] == '20'
        if '-orb-' in slug: assert values['InpRewardRisk'] == '0.5'
        if slug == '3-way-gold': assert values['InpMarketEntries'] == 'true'
        values.update(FTMOAllocationMode='1', FTMOAllocationValue='1.0', FTMOPhase='1', **UNARMED)
        magic = values.get('InpMagic') or values.get('InpMagicBase'); assert magic and magic not in magics, ('magic clash', slug, magic)
        magics[magic] = slug
        (PKG / (stem + '.set')).write_text('\n'.join(f'{k}={v}' for k, v in values.items()) + '\n', encoding='utf-8')
        shutil.copy2(PKG / (stem + '.ex5'), EAS / (stem + '.ex5')); shutil.copy2(PKG / (stem + '.set'), SETS / (stem + '.set'))
        entries.append(dict(slug=slug, label=e['label'], symbol=e['symbol'], timeframe=e['timeframe'], expert=stem + '.ex5', settings=stem + '.set',
                            magic=magic, source_package=src.name, source_expert=e['expert'],
                            source_settings=str(preset.relative_to(ROOT)) if preset else e['settings'],
                            expert_sha=sha(PKG / (stem + '.ex5')), settings_sha=sha(PKG / (stem + '.set'))))
    files = {p.name: sha(p) for p in PKG.iterdir() if p.is_file() and p.suffix != '.log'}
    out = dict(version=VERSION, entries=entries, news_enabled=False, currency_mode='ACCOUNT_CURRENCY', hedging_required=True,
               reference_mode='PERSISTED_FIRST_INSTALL_BALANCE', default_phase='Challenge', default_allocation='1% of current equity',
               risk_cap_fraction=0.01, total_risk_fraction=0.045, symbol_risk_fraction=0.03, daily_reserve_fraction=0.03,
               entry_buffer_fraction=0.92, hard_floor_fraction=0.90, daily_hard_loss_fraction=0.05, strategy_risk_percent='1.0',
               nasdaq_di_default='OFF', usdjpy_di_default='ON', guard_sha=sha(HERE / 'CalyxFTMOGuard.mqh'), guard_state_prefix='BP15',
               source_packages={PROP.name: prop['version'], ANY.name: anyb['version']}, source_guard_sha=prop['guard_sha'], files=files)
    (HERE / 'PACKAGE.json').write_text(json.dumps(out, indent=2) + '\n', encoding='utf-8')
    (HERE / 'Install-BestProp15.ps1').write_bytes(installer_text().encode('utf-8'))
    helpers = sub1(read(BP9 / 'Account-Helpers.ps1'), "throw 'Best Prop 9 requires a hedging MT5 account", "throw 'Best Prop 15 requires a hedging MT5 account")
    (HERE / 'Account-Helpers.ps1').write_bytes(helpers.replace('\n', '\r\n').encode('utf-8'))
    shutil.copy2(BP9 / 'probe_account.py', HERE / 'probe_account.py')
    assert {str(p): sha(p) for src in (PROP, ANY, BP9) for p in src.rglob('*') if p.is_file()} == before, 'source packages must stay unchanged'
    print(f'Built {len(entries)} EAs ({VERSION}); magics {sorted(magics)}; sources unchanged; no MT5 terminal touched.')


def installer_only():
    """Regenerate only the installer (it is not part of the hashed package); no compile, EX5/SETs untouched."""
    (HERE / 'Install-BestProp15.ps1').write_bytes(installer_text().encode('utf-8')); print('installer regenerated')


if __name__ == '__main__':
    import sys
    installer_only() if sys.argv[1:] == ['installer'] else main()
