"""Edge 10, no guard (owner 2026-11-04: "Build E10 as an installable profile with no guards for now"). The ten bots tested in
Edge Portfolio E10 2026-11-04: USDJPY London, EMA3, ORB VP Volume Confirmed, ORB VP, Sell Nasdaq 15min, XAU Regime Switch,
XAU Elliott Wave 1-2-3, Nasdaq 5M (deployed ATR6 stop, DI asked), XAU RSI VWAP, 3 Way Gold breakout module only (market entries).
Same build method as the ORB-only package (EA store tools/build_live_profiles.orb_package): the production source of each EA is
included unchanged except that CalyxAdaptiveRiskMultiplier returns the installer's chosen risk (RiskSupport.mqh: % of equity or
fixed USD per trade; no FTMO guard, no shared daily stop, no adaptive governor). Strategy inputs = the Full EA presets (FULL_ITEMS.json
of the October study, which match the tested long-history runs input for input), risk inputs calibrated to 0.5 as the wrapper needs.
Installer = the Current 14 + ORB 0.5R installer, transformed for 10 entries. Output: ../Packages/Edge10.
Run from AAA EAs/EA store:  uv run python "<this>"      (compiles 10 EAs with the isolated MetaEditor; no MT5 terminal)"""
import hashlib, json, re, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'EA store'))
from tools import build_live_profiles as BL  # noqa: E402

B = BL.B; TARGET = BL.R / 'Packages/Edge10'; VERSION = 'EDGE10-NOGUARD-20261104'
ITEMS = {i['label']: i for i in json.loads(BL.read(B / 'Portfolio October 2026 ATR6 2026-11-03/FULL_ITEMS.json'))}
MEMBERS = [('usdjpy-london-open-momentum', 'USDJPY London Open Momentum'), ('ema3', 'AAA Final EMA3'),
           ('orb-volume-profile-volume-confirmed', 'ORB Volume Profile Volume Confirmed'), ('orb-volume-profile', 'ORB Volume Profile'),
           ('xau-regime-switch', 'XAU Regime Switch'),   # 2026-11-11 owner: Sell Nasdaq 15min removed for now (low win rate)
           ('xau-elliott-wave-1-2-3', 'XAU Elliott Wave 1-2-3'), ('nasdaq-5m-candle-momentum', 'Nasdaq 5M Candle Momentum'),
           ('xau-rsi-vwap', 'XAU RSI VWAP'), ('3-way-gold', '3 Way Gold')]
OVERRIDES = {'3-way-gold': dict(InpEnableMomentum='false', InpEnableBreakout='true', InpEnableTurnOfMonth='false', InpMarketEntries='true')}
RISK_KEYS = ('InpRiskPercent', 'InpGridRiskPercent', 'InpMomentumRiskPercent', 'InpContrarianRiskPercent')
DI = {'nasdaq-5m-candle-momentum': 'InpRequireDIAgreement', 'usdjpy-london-open-momentum': 'InpRequireDIAgreement'}


def build():
    if TARGET.exists(): shutil.rmtree(TARGET)        # generated package only (rebuilt from sources every run)
    (TARGET / 'Sources').mkdir(parents=True); original = {}; cache = {}

    def graph(path):                                  # as BL.orb_package: copy the include graph, swap the risk multiplier
        path = path.resolve()
        if path in cache: return cache[path]
        original[str(path)] = BL.sha(path)
        name = 'src_' + hashlib.sha256(str(path.relative_to(B)).encode()).hexdigest()[:12] + '.mqh'; cache[path] = name
        text = BL.read(path)
        if 'double CalyxAdaptiveRiskMultiplier(' in text:
            m = re.search(r'double\s+CalyxAdaptiveRiskMultiplier\s*\([^)]*\)\s*\{', text); i = m.end(); depth = 1
            while depth:
                depth += {'{': 1, '}': -1}.get(text[i], 0); i += 1
            text = text[:m.end()] + '\n   return UR_RiskMultiplier();\n' + text[i - 1:]
        text = re.sub(r'#include\s+"([^"]+)"', lambda g: '#include "' + graph(path.parent / g[1].replace(chr(92), '/')) + '"', text)
        BL.write(TARGET / 'Sources' / name, text)
        return name

    entries = []
    for slug, label in MEMBERS:
        item = ITEMS[label]; source = Path(item['expert_path']).with_suffix('.mq5'); include = graph(source)
        inputs = {k: str(v) for k, v in item['inputs'].items()}; inputs.update(OVERRIDES.get(slug, {}))
        for k in RISK_KEYS:
            if k in inputs: inputs[k] = '0.5'
        if 'InpRiskMode' in inputs: inputs['InpRiskMode'] = '0'
        inputs.update(InpAdaptivePortfolioControls='false', InpPortfolioRiskMode='0', InpPortfolioPercent='0.5', InpPortfolioFixedUSD='50.0',
                      InpPortfolioExpectedLogin='0', InpPortfolioExpectedServer='', InpPortfolioExpectedSymbol='', InpPortfolioInstallNonce='')

        def expansion(name, seen=None):
            seen = set() if seen is None else seen
            if name in seen: return ''
            seen.add(name); text = BL.read(TARGET / 'Sources' / name)
            return text + '\n' + '\n'.join(expansion(c, seen) for c in re.findall(r'#include "(src_[^"]+)"', text))
        expanded = expansion(include); assert 'return UR_RiskMultiplier();' in expanded, slug
        name = 'Calyx Edge10 - ' + slug
        text = ('#property strict\n#include "../RiskSupport.mqh"\n#define OnInit UR_StrategyInit\n#define OnTick UR_StrategyTick\n'
                '#define OnTimer UR_StrategyTimer\n#include "' + include + '"\n#undef OnInit\n#undef OnTick\n#undef OnTimer\n'
                'int OnInit(){if(!UR_InputsValid(InpRiskPercent))return INIT_PARAMETERS_INCORRECT;int r=UR_StrategyInit();if(r==INIT_SUCCEEDED)UR_Heartbeat(InpMagic,true);return r;}\n'
                'void OnTick(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTick();}\n')
        if re.search(r'void\s+OnTimer\s*\(', expanded):
            text += 'void OnTimer(){if(!UR_BindingOK())return;UR_Heartbeat(InpMagic);UR_StrategyTimer();}\n'
        BL.write(TARGET / 'Sources' / (name + '.mq5'), text)
        BL.write(TARGET / 'Sets' / (slug + '.set'), '\n'.join(k + '=' + v for k, v in inputs.items()) + '\n')
        entries.append(dict(key=slug, label=label, canonical=item['canonical'], period=int(item['period']), magic=int(inputs['InpMagic']), hourly=False,
                            expert='Experts/' + name + '.ex5', settings='Sets/' + slug + '.set', inputs=inputs, di_input=DI.get(slug),
                            source='Sources/' + name + '.mq5', production_source=str(source), production_sha256=BL.sha(source)))
    for name in ('RiskSupport.mqh', 'Installer-Helpers.ps1', 'Probe-MT5.py'):
        shutil.copy2(BL.CURRENT / name, TARGET / name)
    (TARGET / 'Experts').mkdir(exist_ok=True)
    for e in entries:
        path = TARGET / e['source']; BL.compile_ea(path); shutil.copy2(path.with_suffix('.ex5'), TARGET / e['expert'])
    installer(len(entries))
    manifest = dict(version=VERSION, profile='Calyx EDGE10 NOGUARD', entries=entries, orb_keys=[], default_percent=0.5, required_margin_mode=2,
                    news=False, ftmo_guard=False, shared_daily_stop=False, adaptive_governor=False,
                    selection='Owner 2026-11-04: Edge Scan 2026-11-04 list + Nasdaq 5M + XAU RSI VWAP; tested in Edge Portfolio E10 2026-11-04 (in-sample, selection-biased).',
                    compatibility='MT5 demo/live hedging accounts; percentage in account currency, fixed USD with fresh direct currency conversion. Netting and MT4 not supported.',
                    no_live_installation=True, original_hashes=original)
    assert len(entries) == len(MEMBERS) and len({e['magic'] for e in entries}) == len(MEMBERS) and len({e['key'] for e in entries}) == len(MEMBERS)
    BL.save(TARGET / 'Package.json', manifest)
    paths = [TARGET / n for n in ('Package.json', 'Install-Portfolio.ps1', 'Installer-Helpers.ps1', 'Probe-MT5.py')]
    paths += sorted((TARGET / 'Experts').glob('*.ex5')) + sorted((TARGET / 'Sets').glob('*.set'))
    BL.save(TARGET / 'Checksums.json', {str(p.relative_to(TARGET)).replace(chr(92), '/'): BL.sha(p) for p in paths})
    assert all(BL.sha(Path(p)) == d for p, d in original.items()), 'a production source changed during the build'
    print('BUILT', VERSION, len(entries), 'EAs')


def installer(n):
    text = BL.read(BL.CURRENT / 'Install-Portfolio.ps1')
    reps = [('.Count -ne 17', f'.Count -ne {n}', 3), ('return $ready -eq 17', f'return $ready -eq {n}', 1), ('17-chart', f'{n}-chart', 1),
            ("'CALYX - CURRENT14 + ORB05 PORTFOLIO'", "'CALYX - EDGE 10 PORTFOLIO (NO GUARD)'", 1),
            ('No FTMO restrictions, no shared $400/$450 daily stop. This is NOT the previously simulated guarded portfolio. Three-Way Gold risk applies to each module.',
             'NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades. 3 Way Gold runs its breakout module only.', 1),
            ('CalyxCurrent14ORB05Setup', 'CalyxEdge10Setup', None)]
    for old, new, count in reps:
        found = text.count(old); assert found and (count is None or found == count), (old, found)
        text = text.replace(old, new)
    BL.write(TARGET / 'Install-Portfolio.ps1', text)


def refresh_installer():
    # python build.py installer: regenerate only the installer and the checksums; the compiled EAs and their parity evidence stay as they are.
    installer(len(json.loads(BL.read(TARGET / 'Package.json'))['entries'])); paths = [TARGET / n for n in ('Package.json', 'Install-Portfolio.ps1', 'Installer-Helpers.ps1', 'Probe-MT5.py')] + sorted((TARGET / 'Experts').glob('*.ex5')) + sorted((TARGET / 'Sets').glob('*.set'))
    BL.save(TARGET / 'Checksums.json', {str(p.relative_to(TARGET)).replace(chr(92), '/'): BL.sha(p) for p in paths}); print('installer refreshed')


if __name__ == '__main__':
    refresh_installer() if sys.argv[1:] == ['installer'] else build()
