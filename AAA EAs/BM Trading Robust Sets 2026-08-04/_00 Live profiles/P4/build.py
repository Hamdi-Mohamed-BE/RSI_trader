"""Build the P4 profile (owner 2026-11-10): Overnight Bias ORB (US100 M15), Nasdaq 5M REPLACE (DI OFF default), EMA3 (gold H4), Gold Band Wave (gold H4),
the four EAs of Portfolio P7 2026-11-10 (p7.py P4_EAS). Offline: MetaEditor compile only, no MT5 terminal. Same method and installers as Core 9 (../Core 9/build.py):

  * P4 - FTMO 1-Step guard.bat -> 1-Step/  ftmo 1_step guard (10% EOD-trailing, 3% daily, best day <= 50%), own state key P4O
  * P4 - FTMO 2-Step guard.bat -> 2-Step/  broker-neutral Prop Ready guard (FTMO 2-step limits), own state key P4T
  * P4 - no guard.bat          -> ../Packages/P4  no guard (RiskSupport sizing: % of equity or fixed USD per trade)

Nasdaq 5M and EMA3: guarded = the FTMO-AnyBroker wrappers + SETs (Nasdaq REPLACE EX5 since 2026-11-09), no guard = the Edge 10 EX5s (no recompile).
Overnight Bias ORB (Video Ideas Raw EA, InpStrategy 4) and Gold Band Wave are RESEARCH sources; the wrappers include them with three asserted edits that leave the
tester path unchanged:
  1. LIVE CLOCK (ONB): the research EA assumes a UTC server (InpServerUtcOffsetHours=0, Exness). Live it now uses TimeTradeServer()-TimeGMT() rounded to 30 min,
     as Nasdaq 5M's InpAutoServerUtcOffsetLive does; in the tester it keeps the input.
  2. RESTART (GBW): the exit follows the direction of the signal that opened the trade (memory only). After a restart that is unknown, so the open position's own
     direction is used (identical in the tester, where the two always agree).
  3. InpAdaptivePortfolioControls input added (unused) so the installers' preset checks apply unchanged. No guard only: the lot budget is UR_RiskBudget()
     (installer's % of equity or fixed USD) instead of balance x InpRiskPercent.
Gold Band Wave works on H4 bars: brokers whose server clock is not UTC (FTMO: UTC+2/+3) have different H4 bars, so signals differ from the Exness tests.

python build.py            full build (compiles 2 x 4 guarded wrappers + 2 no-guard wrappers)
python build.py installer  regenerate the installers + helpers only
Run from AAA EAs/EA store:  uv run python "<this>" """
import hashlib, importlib.util, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent; LIVE = HERE.parent; ROOT = LIVE.parent
spec = importlib.util.spec_from_file_location('core9_build', LIVE / 'Core 9/build.py'); C9 = importlib.util.module_from_spec(spec); spec.loader.exec_module(C9)
BL = C9.BL; read, write, sub1, sha, compile_ea, set_values = C9.read, C9.write, C9.sub1, C9.sha, C9.compile_ea, C9.set_values
ANY, F1S, BP15, EDGE = C9.ANY, C9.F1S, C9.BP15, C9.EDGE; NOGUARD = LIVE / 'Packages/P4'
VERSION = 'P4-20261110'
VIDEO_SRC = ROOT / 'Video ORB VWAP Ideas Raw 2026-11-09/EA/Video Ideas Raw EA.mq5'; GBW_SRC = ROOT / 'Gold Band Wave Raw 2026-11-10/EA/Gold Band Wave Raw EA.mq5'
FROM_ANY = ['nasdaq-5m-candle-momentum', 'ema3']
# tested inputs = Portfolio P7 2026-11-10/p7.py NEW (VIDEO_COMMON + InpStrategy 4; GBW_INPUTS), risk calibrated to 0.5 like every packaged wrapper
RESEARCH = {
    'overnight-bias-orb': dict(label='Overnight Bias ORB', symbol='USTEC', timeframe='M15', period=15, source=VIDEO_SRC,
                               inputs=dict(InpStrategy='4', InpUseBias='true', InpRandomDirection='false', InpSeed='1', InpRiskPercent='0.5', InpServerUtcOffsetHours='0', InpMagic='91109001', InpDeviationPoints='50')),
    'gold-band-wave': dict(label='Gold Band Wave', symbol='XAUUSD', timeframe='H4', period=240, source=GBW_SRC,
                           inputs=dict(InpRiskPercent='0.5', InpMagic='91110001', InpTrendPeriod='200', InpShortBB='20', InpLongBB='50', InpBBDeviation='2.0', InpSignalPeriod='9', InpATRPeriod='14', InpStopATR='2.0',
                                       InpRandomDirection='false', InpSeed='1', InpDeviationPoints='50'))}
SLUGS = ['overnight-bias-orb', 'nasdaq-5m-candle-momentum', 'ema3', 'gold-band-wave']
VARIANTS = {'1-Step': dict(tag='P4O', ruleset='FTMO_1STEP', script='Install-P4-1Step.ps1'), '2-Step': dict(tag='P4T', ruleset='FTMO_2STEP', script='Install-P4-2Step.ps1')}


def research_text(slug, noguard):
    """The three asserted edits of the module docstring."""
    t = read(RESEARCH[slug]['source'])
    if slug == 'overnight-bias-orb':
        t = sub1(t, 'input int    InpServerUtcOffsetHours=0;\n', 'input int    InpServerUtcOffsetHours=0;   // tester only; live uses the broker clock (P4 build)\n')
        t = sub1(t, 'datetime MakeUtc(', """int SrvOffSec()   // P4 build: live = broker server clock minus UTC, tester = the input (unchanged)
  {
   if((bool)MQLInfoInteger(MQL_TESTER)) return InpServerUtcOffsetHours*3600;
   datetime server=TimeTradeServer(),utc=TimeGMT();
   if(server<=0 || utc<=0) return InpServerUtcOffsetHours*3600;
   return (int)MathRound((double)(server-utc)/1800.0)*1800;
  }
datetime MakeUtc(""")
        t = sub1(t, 'datetime utc=server-InpServerUtcOffsetHours*3600;', 'datetime utc=server-SrvOffSec();')
        t = sub1(t, 'return ny-off*3600+InpServerUtcOffsetHours*3600;', 'return ny-off*3600+SrvOffSec();')
        assert t.count('InpServerUtcOffsetHours') == 4, t.count('InpServerUtcOffsetHours')
        anchor = 'input int    InpDeviationPoints=50;\n'
    else:
        t = sub1(t, 'if(Position(ticket,dir) && cross==-g_rule_dir)', 'if(Position(ticket,dir) && cross==-(g_rule_dir!=0 ? g_rule_dir : dir))   // P4 build: after a restart use the position direction')
        anchor = 'input int    InpDeviationPoints=50;\n'
    t = sub1(t, anchor, anchor + 'input bool   InpAdaptivePortfolioControls=false;   // P4 build: unused, kept for the installer preset checks\n')
    if noguard: t = sub1(t, 'double raw=AccountInfoDouble(ACCOUNT_BALANCE)*InpRiskPercent/100.0/MathAbs(one);', 'double raw=UR_RiskBudget()/MathAbs(one);   // P4 no guard: installer budget (RiskSupport.mqh)')
    return t


def guard_text(variant):
    if variant == '1-Step':
        g = read(F1S / 'CalyxFTMOGuard.mqh'); assert sha(F1S / 'CalyxFTMOGuard.mqh') == json.loads(read(F1S / 'PACKAGE.json'))['guard_sha'], 'ftmo 1_step guard altered'
        return sub1(g, 'return "F1S"+IntegerToString(FTMOExpectedLogin)', 'return "P4O"+IntegerToString(FTMOExpectedLogin)')
    g = read(ANY / 'CalyxFTMOGuard.mqh'); assert sha(ANY / 'CalyxFTMOGuard.mqh') == json.loads(read(ANY / 'PACKAGE.json'))['guard_sha'], 'any-broker guard altered'
    return sub1(g, 'return "PR9"+IntegerToString(FTMOExpectedLogin)', 'return "P4T"+IntegerToString(FTMOExpectedLogin)')


def flat_include(slug, target, shim, noguard):
    """Research EAs have no includes except <Trade/Trade.mqh>; write the edited source flat into target."""
    t = research_text(slug, noguard)
    if shim:
        t = sub1(t, '#include <Trade/Trade.mqh>', '#include "FTMO_Trade.mqh"'); t = re.sub(r'\bOrderSend\(', 'FTMOOrderSend(', t)
    assert '#include "' not in t.replace('#include "FTMO_Trade.mqh"', '')
    name = f'src_p4_{slug}.mqh'; write(target / name, t); return name


def build_guarded(variant, anyb):
    cfg = VARIANTS[variant]; root = HERE / variant; pkg = root / 'package'; tag = cfg['tag']
    for d in (pkg, root / 'EAs', root / 'Sets'):
        if d.exists(): shutil.rmtree(d)                  # this profile's own generated folders only
        d.mkdir(parents=True)
    guard = guard_text(variant); write(root / 'CalyxFTMOGuard.mqh', guard); write(pkg / 'CalyxFTMOGuard.mqh', guard)
    for f in (ANY / 'package').iterdir():
        if f.suffix == '.mqh' and f.name != 'CalyxFTMOGuard.mqh': shutil.copy2(f, pkg / f.name)
    entries = []; magics = {}
    for slug in SLUGS:
        stem = f'{tag}-{slug}'
        if slug in FROM_ANY:
            e = next(x for x in anyb['entries'] if x['slug'] == slug); label, symbol, timeframe = e['label'], e['symbol'], e['timeframe']
            write(pkg / f'{stem}.mq5', read(ANY / 'package' / (Path(e['expert']).stem + '.mq5'))); values = set_values(ANY / 'package' / e['settings']); source = ('FTMO-AnyBroker', e['expert'], e['settings'])
        else:
            r = RESEARCH[slug]; label, symbol, timeframe = r['label'], r['symbol'], r['timeframe']; include = flat_include(slug, pkg, True, False)
            code = ('#property strict\n#include "CalyxFTMOGuard.mqh"\n#define OnInit FTMO_StrategyInit\n#define OnTick FTMO_StrategyTick\n#include "' + include + '"\n#undef OnInit\n#undef OnTick\n'
                    'int OnInit(){ if(FTMOInit()!=INIT_SUCCEEDED)return INIT_FAILED; return FTMO_StrategyInit(); }\nvoid OnTick(){ if(FTMOPulse())FTMO_StrategyTick(); }\n')
            write(pkg / f'{stem}.mq5', code); values = dict(r['inputs'], InpAdaptivePortfolioControls='false'); source = ('research', str(r['source']), 'p7.py NEW inputs')
        compile_ea(pkg / f'{stem}.mq5')
        assert values['InpRiskPercent'] == '0.5' and values.get('InpAdaptivePortfolioControls') == 'false', slug
        if slug == 'nasdaq-5m-candle-momentum': values['InpRequireDIAgreement'] = 'false'          # P4 tested DI OFF; the installer asks
        values.update(FTMOAllocationMode='1', FTMOAllocationValue='0.5', FTMOPhase='1', **C9.UNARMED)
        if variant == '1-Step': values.update(C9.RULES_1STEP)
        magic = values.get('InpMagic'); assert magic and magic not in magics, ('magic clash', slug, magic); magics[magic] = slug
        write(pkg / f'{stem}.set', '\n'.join(f'{k}={v}' for k, v in values.items()) + '\n')
        shutil.copy2(pkg / f'{stem}.ex5', root / 'EAs' / f'{stem}.ex5'); shutil.copy2(pkg / f'{stem}.set', root / 'Sets' / f'{stem}.set')
        entries.append(dict(slug=slug, label=label, symbol=symbol, timeframe=timeframe, expert=f'{stem}.ex5', settings=f'{stem}.set', magic=magic, source_package=source[0], source_expert=source[1], source_settings=source[2], expert_sha=sha(pkg / f'{stem}.ex5'), settings_sha=sha(pkg / f'{stem}.set')))
    files = {p.name: sha(p) for p in pkg.iterdir() if p.is_file() and p.suffix != '.log'}
    out = dict(version=f'{VERSION}-{variant}', ruleset=cfg['ruleset'], entries=entries, news_enabled=False, currency_mode='ACCOUNT_CURRENCY', hedging_required=True, reference_mode='FRESH_BASELINE_EVERY_RUN', default_phase='Challenge',
               risk_cap_fraction=0.005, total_risk_fraction=0.0225, symbol_risk_fraction=0.015, strategy_risk_percent='0.5 (installer: 1.5x the chosen risk, max 5)', nasdaq_di_default='OFF',
               research_eas='overnight-bias-orb, gold-band-wave: research sources with the asserted P4 edits (build.py docstring)', guard_sha=sha(root / 'CalyxFTMOGuard.mqh'), guard_state_prefix=tag,
               source_package=dict(name=ANY.name, version=anyb['version'], guard_sha=anyb['guard_sha']), files=files)
    write(root / 'PACKAGE.json', json.dumps(out, indent=2) + '\n'); print('Built', variant, len(entries), 'EAs', flush=True)


ROSTER = "'overnight-bias-orb', 'nasdaq-5m-candle-momentum', 'ema3', 'gold-band-wave'"


def p4_installer(text, variant):
    text, n = re.subn(r"\$expected=@\('[^)]*\)", lambda m: '$expected=@(' + ROSTER + ')', text, count=1); assert n == 1
    for a, b in [("if($manifest.entries.Count -ne 9 -or", "if($manifest.entries.Count -ne 4 -or"), ("[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='ON',", "[ValidateSet('ON','OFF')][string]$NasdaqDIFilter='OFF',"),
                 ("(Read-Host 'Nasdaq 5M DI filter ON or OFF [ON]')", "(Read-Host 'Nasdaq 5M DI filter ON or OFF (P4 tested OFF) [OFF]')"),
                 ("throw 'Core 9 roster changed.'", "throw 'P4 roster changed.'"), ('Nasdaq DI default ON.', 'Nasdaq DI default OFF.')]:
        text = sub1(text, a, b)
    text = sub1(text, "        $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF (P4 tested OFF) [OFF]').Trim().ToUpperInvariant()\n        if(-not $answer){$answer='ON'}\n",
                "        $answer=(Read-Host 'Nasdaq 5M DI filter ON or OFF (P4 tested OFF) [OFF]').Trim().ToUpperInvariant()\n        if(-not $answer){$answer='OFF'}\n")
    # the USDJPY question never appears: the BAT passes -UsdJpyDIFilter OFF and P4 has no USDJPY EA
    text = text.replace('Calyx-Core9-', 'Calyx-P4-').replace('CORE9 ', 'P4 ').replace('.core9-', '.p4-').replace('Core 9/build.py', 'P4/build.py')
    for a, b in [('Core 9', 'P4'), ('CORE 9', 'P4'), ('nine guarded EAs', 'four guarded EAs'), ('nine EAs', 'four EAs'), ('all nine charts', 'all four charts'), ('PASS: 9 integrity', 'PASS: 4 integrity'),
                 ('3 Way Gold breakout only', 'Overnight Bias ORB, Nasdaq 5M, EMA3, Gold Band Wave'), ('Nasdaq DI: $NasdaqDIFilter / USDJPY DI: $UsdJpyDIFilter (ADX20 kept).', 'Nasdaq DI: $NasdaqDIFilter.'),
                 ('Nasdaq DI: $NasdaqDIFilter; USDJPY DI: $UsdJpyDIFilter', 'Nasdaq DI: $NasdaqDIFilter'), ('five ORBs: 0.5R; ', '')]:
        assert a in text, (variant, a); text = text.replace(a, b)
    if variant == '1-Step': text = sub1(text, '# P4 2026-11-05: four EAs', '# P4 2026-11-10: Overnight Bias ORB, Nasdaq 5M REPLACE, EMA3, Gold Band Wave')
    else: text = sub1(text, '# P4 2026-11-05: four EAs', '# P4 2026-11-10: Overnight Bias ORB, Nasdaq 5M REPLACE, EMA3, Gold Band Wave; four EAs')
    for bad in ('Core 9', 'Core9', 'CORE9', 'nine', 'usdjpy-london', 'us100-selective'):
        assert bad not in text, (variant, bad)
    return text


def write_installers():
    C9i = {'1-Step': C9.installer_1step, '2-Step': C9.installer_2step}
    for v, f in C9i.items():
        text = p4_installer(f().replace('\r\n', '\n'), v); (HERE / v / VARIANTS[v]['script']).write_bytes(text.replace('\n', '\r\n').encode('utf-8'))
    h1 = sub1(read(F1S / 'Account-Helpers.ps1'), "throw 'FTMO 1-Step requires a hedging MT5 account", "throw 'P4 requires a hedging MT5 account"); h2 = sub1(read(BP15 / 'Account-Helpers.ps1'), "throw 'Best Prop 15 requires a hedging MT5 account", "throw 'P4 requires a hedging MT5 account")
    (HERE / '1-Step/Account-Helpers.ps1').write_bytes(h1.replace('\n', '\r\n').encode('utf-8')); (HERE / '2-Step/Account-Helpers.ps1').write_bytes(h2.replace('\n', '\r\n').encode('utf-8'))
    shutil.copy2(F1S / 'probe_account.py', HERE / '1-Step/probe_account.py'); shutil.copy2(BP15 / 'probe_account.py', HERE / '2-Step/probe_account.py')
    print('installers + helpers written', flush=True)


def build_noguard(edge):
    if NOGUARD.exists(): shutil.rmtree(NOGUARD)          # generated package only
    for d in ('Experts', 'Sets', 'Sources'): (NOGUARD / d).mkdir(parents=True)
    shutil.copy2(BL.CURRENT / 'RiskSupport.mqh', NOGUARD / 'RiskSupport.mqh'); assert BL.sha(BL.CURRENT / 'RiskSupport.mqh') == BL.sha(EDGE / 'RiskSupport.mqh')
    entries = []
    for slug in SLUGS:
        if slug in FROM_ANY:
            e = next(x for x in edge['entries'] if x['key'] == slug); shutil.copy2(EDGE / e['expert'], NOGUARD / e['expert']); shutil.copy2(EDGE / e['settings'], NOGUARD / e['settings'])
            e = {k: v for k, v in e.items() if k not in ('source', 'production_source', 'production_sha256')}
            if slug == 'nasdaq-5m-candle-momentum': e['inputs'] = dict(e['inputs'], InpRequireDIAgreement='false')
        else:
            r = RESEARCH[slug]; include = flat_include(slug, NOGUARD / 'Sources', False, True); name = 'Calyx P4 - ' + slug
            BL.write(NOGUARD / 'Sources' / (name + '.mq5'), '#property strict\n#include "../RiskSupport.mqh"\n#define OnInit UR_StrategyInit\n#define OnTick UR_StrategyTick\n#include "' + include + '"\n#undef OnInit\n#undef OnTick\n'
                     'int OnInit(){if(!UR_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;int r=UR_StrategyInit();if(r==INIT_SUCCEEDED)UR_Heartbeat(InpMagic,true);return r;}\n'
                     'void OnTick(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTick();}\n')
            inputs = dict(r['inputs'], InpAdaptivePortfolioControls='false', InpPortfolioRiskMode='0', InpPortfolioPercent='0.5', InpPortfolioFixedUSD='50.0', InpPortfolioExpectedLogin='0', InpPortfolioExpectedServer='', InpPortfolioExpectedSymbol='', InpPortfolioInstallNonce='')
            BL.write(NOGUARD / 'Sets' / (slug + '.set'), '\n'.join(k + '=' + v for k, v in inputs.items()) + '\n')
            BL.compile_ea(NOGUARD / 'Sources' / (name + '.mq5')); shutil.copy2(NOGUARD / 'Sources' / (name + '.ex5'), NOGUARD / 'Experts' / (name + '.ex5'))
            e = dict(key=slug, label=r['label'], canonical=r['symbol'], period=r['period'], magic=int(inputs['InpMagic']), hourly=False, expert='Experts/' + name + '.ex5', settings='Sets/' + slug + '.set', inputs=inputs, di_input=None,
                     research_source=str(r['source']), research_sha256=BL.sha(r['source']))
        entries.append(e)
    assert [e['key'] for e in entries] == SLUGS and len({e['magic'] for e in entries}) == 4
    for name in ('Installer-Helpers.ps1', 'Probe-MT5.py'): shutil.copy2(BL.CURRENT / name, NOGUARD / name)
    text = BL.read(BL.CURRENT / 'Install-Portfolio.ps1')
    for old, new, count in [('.Count -ne 17', '.Count -ne 4', 3), ('return $ready -eq 17', 'return $ready -eq 4', 1), ('17-chart', '4-chart', 1), ("'CALYX - CURRENT14 + ORB05 PORTFOLIO'", "'CALYX - P4 PORTFOLIO (NO GUARD)'", 1),
                            ('No FTMO restrictions, no shared $400/$450 daily stop. This is NOT the previously simulated guarded portfolio. Three-Way Gold risk applies to each module.',
                             'NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades.', 1),
                            ("$answer=(Read-Host \"$label DI filter ON or OFF [ON]\").Trim().ToUpperInvariant(); if (-not $answer) { $answer='ON' }", "$answer=(Read-Host \"$label DI filter ON or OFF (P4 tested OFF) [OFF]\").Trim().ToUpperInvariant(); if (-not $answer) { $answer='OFF' }", 1),
                            ('DI OFF changes the tested preset. USDJPY ADX20 remains enabled.', 'P4 was tested with the Nasdaq DI filter OFF.', 1),
                            ('CalyxCurrent14ORB05Setup', 'CalyxP4Setup', None)]:
        found = text.count(old); assert found and (count is None or found == count), (old, found)
        text = text.replace(old, new)
    BL.write(NOGUARD / 'Install-Portfolio.ps1', text)
    BL.save(NOGUARD / 'Package.json', dict(version=f'{VERSION}-NOGUARD', profile='Calyx P4 NOGUARD', entries=entries, orb_keys=[], default_percent=0.5, required_margin_mode=2, news=False, ftmo_guard=False, shared_daily_stop=False, adaptive_governor=False,
                                           selection='Owner 2026-11-10: the four EAs kept from Portfolio P7 2026-11-10 (in-sample, selection-biased).', compatibility=edge['compatibility'], no_live_installation=True,
                                           sources=dict(edge10=edge['version'], research=['Video ORB VWAP Ideas Raw 2026-11-09', 'Gold Band Wave Raw 2026-11-10'])))
    paths = [NOGUARD / n for n in ('Package.json', 'Install-Portfolio.ps1', 'Installer-Helpers.ps1', 'Probe-MT5.py')] + sorted((NOGUARD / 'Experts').glob('*.ex5')) + sorted((NOGUARD / 'Sets').glob('*.set'))
    BL.save(NOGUARD / 'Checksums.json', {str(p.relative_to(NOGUARD)).replace(chr(92), '/'): BL.sha(p) for p in paths}); print('Built no guard, 4 EAs', flush=True)


def main():
    anyb = json.loads(read(ANY / 'PACKAGE.json')); edge = json.loads(read(EDGE / 'Package.json'))
    for name, digest in anyb['files'].items(): assert sha(ANY / 'package' / name) == digest, ('package altered', name)
    sources = (ANY, F1S, BP15, EDGE, BL.CURRENT, VIDEO_SRC.parent, GBW_SRC.parent, LIVE / 'Core 9')
    before = {str(p): sha(p) for src in sources for p in src.rglob('*') if p.is_file()}
    build_noguard(edge)
    for v in VARIANTS: build_guarded(v, anyb)
    write_installers()
    assert {str(p): sha(p) for src in sources for p in src.rglob('*') if p.is_file()} == before, 'source packages must stay unchanged'
    print('DONE', VERSION, 'no MT5 terminal touched', flush=True)


if __name__ == '__main__':
    write_installers() if sys.argv[1:] == ['installer'] else main()
