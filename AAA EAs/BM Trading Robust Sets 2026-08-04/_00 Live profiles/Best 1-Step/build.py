"""Build the Best 1-Step profile (owner 2026-11-11: "nasdaq 5m and overnight bias orb and gold band wave and EMA3 are must have ... best portfolio for 1 step ...
create guard and no guard bat files"). Evidence: ../../Best 1-Step Search 2026-11-11/ (FINAL.json, REPORT.md).

Roster = Core 9 + P4 = 11 EAs: Nasdaq 5M (REPLACE, DI OFF default as tested), USDJPY London (DI ON as tested), 3 Way Gold breakout only, Sell Nasdaq 15min, EMA3,
ORB VP Volume Confirmed, XAU Squeeze, US100 Selective ORB V3 (0.5R), XAU RSI VWAP, Overnight Bias ORB, Gold Band Wave. This is the 'ref:Core9+P4' row of the search
(GUARD 0.5%), chosen over the rule's forced pick (11 EAs at 0.75% incl. Vault Break) because it is better on validation, OOS and MC; see REPORT.md.

  * Best 1-Step - FTMO 1-Step guard.bat -> 1-Step/  ftmo 1_step guard (10% EOD-trailing, 3% daily, best day <= 50%), own state key B1O, default risk 0.5%
  * Best 1-Step - no guard.bat          -> ../Packages/Best1Step  no guard, the already compiled Core 9 / P4 no-guard EX5s (no recompile)

Guarded wrappers: exactly the Core 9 build (../Core 9/build.py: FTMO-AnyBroker wrappers, Sell Nasdaq held stop, ORB VP VC) plus the P4 research wrappers
(../P4/build.py: Overnight Bias ORB live broker clock, Gold Band Wave restart-safe exit). Offline: MetaEditor compile only, no MT5 terminal.

python build.py            full build (compiles 11 guarded wrappers)
python build.py installer  regenerate the installer + helpers only
Run from AAA EAs/EA store:  uv run python "<this>" """
import importlib.util, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; LIVE = HERE.parent; ROOT = LIVE.parent


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m


C9 = load('core9_build', LIVE / 'Core 9/build.py'); P4 = load('p4_build', LIVE / 'P4/build.py')
BL = C9.BL; read, write, sub1, sha, compile_ea, set_values = C9.read, C9.write, C9.sub1, C9.sha, C9.compile_ea, C9.set_values
ANY, F1S, EDGE = C9.ANY, C9.F1S, C9.EDGE; NOGUARD = LIVE / 'Packages/Best1Step'; CORE9_NG = LIVE / 'Packages/Core9'; P4_NG = LIVE / 'Packages/P4'
VERSION = 'BEST1STEP-20261111'; TAG = 'B1O'; SCRIPT = 'Install-Best1Step-1Step.ps1'
RESEARCH = ['overnight-bias-orb', 'gold-band-wave']
SLUGS = C9.SLUGS + RESEARCH
assert len(SLUGS) == 11 and len(set(SLUGS)) == 11


def guard_text():
    g = read(F1S / 'CalyxFTMOGuard.mqh'); assert sha(F1S / 'CalyxFTMOGuard.mqh') == json.loads(read(F1S / 'PACKAGE.json'))['guard_sha'], 'ftmo 1_step guard altered'
    return sub1(g, 'return "F1S"+IntegerToString(FTMOExpectedLogin)', 'return "' + TAG + '"+IntegerToString(FTMOExpectedLogin)')


def build_guarded(anyb, edge):
    root = HERE / '1-Step'; pkg = root / 'package'
    for d in (pkg, root / 'EAs', root / 'Sets'):
        if d.exists(): shutil.rmtree(d)                  # this profile's own generated folders only
        d.mkdir(parents=True)
    guard = guard_text(); write(root / 'CalyxFTMOGuard.mqh', guard); write(pkg / 'CalyxFTMOGuard.mqh', guard)
    for f in (ANY / 'package').iterdir():
        if f.suffix == '.mqh' and f.name != 'CalyxFTMOGuard.mqh': shutil.copy2(f, pkg / f.name)
    entries = []; magics = {}; cache = {}
    for slug in SLUGS:
        stem = f'{TAG}-{slug}'
        if slug in C9.FROM_ANY:
            e = next(x for x in anyb['entries'] if x['slug'] == slug); label, symbol, timeframe = e['label'], e['symbol'], e['timeframe']
            write(pkg / f'{stem}.mq5', read(ANY / 'package' / (Path(e['expert']).stem + '.mq5'))); values = set_values(ANY / 'package' / e['settings']); source = ('FTMO-AnyBroker', e['expert'], e['settings'])
        elif slug in C9.FROM_EDGE:
            e = next(x for x in edge['entries'] if x['key'] == slug); label, symbol, timeframe = C9.FROM_EDGE[slug]; assert e['canonical'] == symbol
            include = C9.graph_copy(Path(e['production_source']), pkg, cache, True, C9.virtual_stop if slug == 'sell-nasdaq-15min' else None)
            code = ('#property strict\n#include "CalyxFTMOGuard.mqh"\n#define OnInit FTMO_StrategyInit\n#define OnTick FTMO_StrategyTick\n#define OnTimer FTMO_StrategyTimer\n#include "' + include + '"\n#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
                    'int OnInit(){ if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED; return FTMO_StrategyInit(); }\nvoid OnTick(){ if(FTMOPulse())FTMO_StrategyTick(); }\n')
            if re.search(r'void\s+OnTimer\s*\(', C9.expansion(pkg, include)): code += 'void OnTimer(){ if(FTMOPulse())FTMO_StrategyTimer(); }\n'
            write(pkg / f'{stem}.mq5', code); values = {k: str(v) for k, v in e['inputs'].items()}; source = ('Edge10', e['production_source'], e['settings'])
            if slug == 'sell-nasdaq-15min': assert 'trade.SellStop(' not in read(pkg / include)
        else:
            r = P4.RESEARCH[slug]; label, symbol, timeframe = r['label'], r['symbol'], r['timeframe']; include = P4.flat_include(slug, pkg, True, False)
            code = ('#property strict\n#include "CalyxFTMOGuard.mqh"\n#define OnInit FTMO_StrategyInit\n#define OnTick FTMO_StrategyTick\n#include "' + include + '"\n#undef OnInit\n#undef OnTick\n'
                    'int OnInit(){ if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED; return FTMO_StrategyInit(); }\nvoid OnTick(){ if(FTMOPulse())FTMO_StrategyTick(); }\n')
            write(pkg / f'{stem}.mq5', code); values = dict(r['inputs'], InpAdaptivePortfolioControls='false'); source = ('research (P4 edits)', str(r['source']), 'p7.py NEW inputs')
        compile_ea(pkg / f'{stem}.mq5')
        assert values['InpRiskPercent'] == '0.5' and values.get('InpAdaptivePortfolioControls') == 'false', slug
        if slug == 'us100-selective-orb-v3': assert values['InpRewardRisk'] == '0.5'
        if slug == '3-way-gold':
            assert values['InpMarketEntries'] == 'true'; values.update(InpEnableMomentum='false', InpEnableBreakout='true', InpEnableTurnOfMonth='false')
        if slug == 'nasdaq-5m-candle-momentum': values['InpRequireDIAgreement'] = 'false'          # tested DI OFF (pool stream); the installer asks
        if slug == 'usdjpy-london-open-momentum': assert values['InpRequireDIAgreement'] == 'true'    # tested DI ON (Core 9 stream)
        values.update(FTMOAllocationMode='1', FTMOAllocationValue='0.5', FTMOPhase='1', **C9.UNARMED); values.update(C9.RULES_1STEP)
        magic = values.get('InpMagic') or values.get('InpMagicBase'); assert magic and magic not in magics, ('magic clash', slug, magic); magics[magic] = slug
        write(pkg / f'{stem}.set', '\n'.join(f'{k}={v}' for k, v in values.items()) + '\n')
        shutil.copy2(pkg / f'{stem}.ex5', root / 'EAs' / f'{stem}.ex5'); shutil.copy2(pkg / f'{stem}.set', root / 'Sets' / f'{stem}.set')
        entries.append(dict(slug=slug, label=label, symbol=symbol, timeframe=timeframe, expert=f'{stem}.ex5', settings=f'{stem}.set', magic=magic, source_package=source[0], source_expert=source[1], source_settings=source[2], expert_sha=sha(pkg / f'{stem}.ex5'), settings_sha=sha(pkg / f'{stem}.set')))
    files = {p.name: sha(p) for p in pkg.iterdir() if p.is_file() and p.suffix != '.log'}
    out = dict(version=f'{VERSION}-1-Step', ruleset='FTMO_1STEP', entries=entries, news_enabled=False, currency_mode='ACCOUNT_CURRENCY', hedging_required=True, reference_mode='FRESH_BASELINE_EVERY_RUN', default_phase='Challenge',
               risk_cap_fraction=0.005, total_risk_fraction=0.0225, symbol_risk_fraction=0.015, strategy_risk_percent='0.5 (installer: 1.5x the chosen risk, max 5)', nasdaq_di_default='OFF', usdjpy_di_default='ON',
               sell_nasdaq='stop held in the EA, sold at market (these guards refuse pending orders)', research_eas='overnight-bias-orb, gold-band-wave: research sources with the asserted P4 edits (../P4/build.py)',
               guard_sha=sha(root / 'CalyxFTMOGuard.mqh'), guard_state_prefix=TAG, source_package=dict(name=ANY.name, version=anyb['version'], guard_sha=anyb['guard_sha']), files=files)
    write(root / 'PACKAGE.json', json.dumps(out, indent=2) + '\n'); print('Built 1-Step', len(entries), 'EAs', flush=True)


ROSTER = ',\n        '.join(', '.join(f"'{x}'" for x in SLUGS[i:i + 4]) for i in range(0, len(SLUGS), 4))


def installer():
    s = C9.installer_1step().replace('\r\n', '\n')
    s, n = re.subn(r"\$expected=@\('[^)]*\)", lambda m: '$expected=@(' + ROSTER + ')', s, count=1); assert n == 1
    for a, b in [("[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',", "[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='OFF',"),
                 ("# Core 9 2026-11-05: nine EAs with the FTMO 1-Step guard", "# Best 1-Step 2026-11-11: Core 9 + Overnight Bias ORB + Gold Band Wave, eleven EAs with the FTMO 1-Step guard"),
                 ("# GENERATED by Core 9/build.py from ftmo 1_step/Install-FTMO1Step.ps1; do not edit by hand.", "# GENERATED by Best 1-Step/build.py (via Core 9/build.py) from ftmo 1_step/Install-FTMO1Step.ps1; do not edit by hand."),
                 ("if($manifest.entries.Count -ne 9 -or", "if($manifest.entries.Count -ne 11 -or"),
                 ("        $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF [ON]').Trim().ToUpperInvariant()\n        if(-not $answer){$answer='ON'}\n",
                  "        $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF (tested OFF) [OFF]').Trim().ToUpperInvariant()\n        if(-not $answer){$answer='OFF'}\n"),
                 ("3 Way Gold breakout only", "3 Way Gold breakout only / Overnight Bias ORB + Gold Band Wave"),
                 ("Nasdaq DI default ON.", "Nasdaq DI default OFF.")]:
        s = sub1(s, a, b)
    for a, b in [('Calyx-Core9-1Step-', 'Calyx-Best1Step-'), ('CORE9 1STEP', 'BEST1STEP'), ('.core9-1step-backup-', '.best1step-backup-'), ('CORE 9', 'BEST 1-STEP'), ('Core 9', 'Best 1-Step'),
                 ('nine guarded EAs', 'eleven guarded EAs'), ('nine EAs', 'eleven EAs'), ('all nine charts', 'all eleven charts'), ('PASS: 9 integrity', 'PASS: 11 integrity')]:
        assert a in s, a; s = s.replace(a, b)
    for bad in ('Core9', 'CORE9', 'core9', 'nine'): assert bad not in s, bad
    return s.replace('\n', '\r\n')


def write_installers():
    root = HERE / '1-Step'; root.mkdir(exist_ok=True)
    (root / SCRIPT).write_bytes(installer().encode('utf-8'))
    h = sub1(read(F1S / 'Account-Helpers.ps1'), "throw 'FTMO 1-Step requires a hedging MT5 account", "throw 'Best 1-Step requires a hedging MT5 account")
    (root / 'Account-Helpers.ps1').write_bytes(h.replace('\n', '\r\n').encode('utf-8')); shutil.copy2(F1S / 'probe_account.py', root / 'probe_account.py')
    print('installer + helpers written', flush=True)


def build_noguard():
    """No recompile: the Core 9 no-guard EX5s (minus its DI-ON Nasdaq) + the P4 no-guard Nasdaq (Edge10, DI OFF) and research EX5s."""
    c9 = json.loads(read(CORE9_NG / 'Package.json')); p4 = json.loads(read(P4_NG / 'Package.json'))
    for pk in (CORE9_NG, P4_NG):
        for rel, digest in json.loads(read(pk / 'Checksums.json')).items(): assert BL.sha(pk / rel) == digest, ('package altered', pk.name, rel)
    assert BL.sha(CORE9_NG / 'RiskSupport.mqh') == BL.sha(P4_NG / 'RiskSupport.mqh')
    if NOGUARD.exists(): shutil.rmtree(NOGUARD)          # generated package only
    (NOGUARD / 'Experts').mkdir(parents=True); (NOGUARD / 'Sets').mkdir(); entries = []
    pick = [(CORE9_NG, e) for e in c9['entries'] if e['key'] != 'nasdaq-5m-candle-momentum'] + [(P4_NG, e) for e in p4['entries'] if e['key'] in ('nasdaq-5m-candle-momentum', 'overnight-bias-orb', 'gold-band-wave')]
    for root, e in pick:
        shutil.copy2(root / e['expert'], NOGUARD / e['expert']); shutil.copy2(root / e['settings'], NOGUARD / e['settings']); entries.append(dict(e, from_package=root.name))
    entries.sort(key=lambda e: SLUGS.index(e['key']))
    assert [e['key'] for e in entries] == SLUGS and len({e['magic'] for e in entries}) == 11
    assert next(e for e in entries if e['key'] == 'nasdaq-5m-candle-momentum')['inputs']['InpRequireDIAgreement'] == 'false'
    assert next(e for e in entries if e['key'] == 'usdjpy-london-open-momentum')['inputs']['InpRequireDIAgreement'] == 'true'
    for name in ('RiskSupport.mqh', 'Installer-Helpers.ps1', 'Probe-MT5.py'): shutil.copy2(BL.CURRENT / name, NOGUARD / name)
    text = BL.read(BL.CURRENT / 'Install-Portfolio.ps1')
    for old, new, count in [('.Count -ne 17', '.Count -ne 11', 3), ('return $ready -eq 17', 'return $ready -eq 11', 1), ('17-chart', '11-chart', 1), ("'CALYX - CURRENT14 + ORB05 PORTFOLIO'", "'CALYX - BEST 1-STEP PORTFOLIO (NO GUARD)'", 1),
                            ('No FTMO restrictions, no shared $400/$450 daily stop. This is NOT the previously simulated guarded portfolio. Three-Way Gold risk applies to each module.',
                             'NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades. 3 Way Gold runs its breakout module only.', 1),
                            ("$answer=(Read-Host \"$label DI filter ON or OFF [ON]\").Trim().ToUpperInvariant(); if (-not $answer) { $answer='ON' }",
                             "$tested=if ($parameter -eq 'NasdaqDIFilter') {'OFF'} else {'ON'}; $answer=(Read-Host \"$label DI filter ON or OFF (tested $tested) [$tested]\").Trim().ToUpperInvariant(); if (-not $answer) { $answer=$tested }", 1),
                            ('DI OFF changes the tested preset. USDJPY ADX20 remains enabled.', 'Best 1-Step was tested with Nasdaq DI OFF and USDJPY DI ON (ADX20 kept).', 1),
                            ('CalyxCurrent14ORB05Setup', 'CalyxBest1StepSetup', None)]:
        found = text.count(old); assert found and (count is None or found == count), (old, found)
        text = text.replace(old, new)
    BL.write(NOGUARD / 'Install-Portfolio.ps1', text)
    BL.save(NOGUARD / 'Package.json', dict(version=f'{VERSION}-NOGUARD', profile='Calyx BEST1STEP NOGUARD', entries=entries, orb_keys=['us100-selective-orb-v3'], default_percent=0.5, required_margin_mode=2, news=False, ftmo_guard=False,
                                           shared_daily_stop=False, adaptive_governor=False, selection='Owner 2026-11-11: Core 9 + P4 (Best 1-Step Search 2026-11-11, in-sample, selection-biased).', compatibility=c9['compatibility'],
                                           no_live_installation=True, sources=dict(core9=c9['version'], p4=p4['version'])))
    paths = [NOGUARD / n for n in ('Package.json', 'Install-Portfolio.ps1', 'Installer-Helpers.ps1', 'Probe-MT5.py')] + sorted((NOGUARD / 'Experts').glob('*.ex5')) + sorted((NOGUARD / 'Sets').glob('*.set'))
    BL.save(NOGUARD / 'Checksums.json', {str(p.relative_to(NOGUARD)).replace(chr(92), '/'): BL.sha(p) for p in paths}); print('Built no guard, 11 EAs (no recompile)', flush=True)


def main():
    anyb = json.loads(read(ANY / 'PACKAGE.json')); edge = json.loads(read(EDGE / 'Package.json'))
    for name, digest in anyb['files'].items(): assert sha(ANY / 'package' / name) == digest, ('package altered', name)
    sources = (ANY, F1S, EDGE, BL.CURRENT, CORE9_NG, P4_NG, LIVE / 'Core 9', LIVE / 'P4', P4.VIDEO_SRC.parent, P4.GBW_SRC.parent)
    before = {str(p): sha(p) for src in sources for p in src.rglob('*') if p.is_file()}
    build_noguard(); build_guarded(anyb, edge); write_installers()
    assert {str(p): sha(p) for src in sources for p in src.rglob('*') if p.is_file()} == before, 'source packages must stay unchanged'
    print('DONE', VERSION, 'no MT5 terminal touched', flush=True)


if __name__ == '__main__':
    write_installers() if sys.argv[1:] == ['installer'] else main()
