"""Mixed 22, no guard (owner 2026-11-05: "build mixed with no guards too in the same folder"). FTMO17's 17 EAs + the five E10-only bots, exactly what Merged E10 FTMO17 2026-11-05 tested.
No recompile: the 17 wrapper EX5s + SETs come from the Current 14 + ORB 0.5R package (the ones native.py ran), the five from Packages/Edge10 (native parity 10/10 with production). Both use the same RiskSupport.mqh,
asserted below. 3 Way Gold keeps all three modules with market entries, as tested. Installer = the Current 14 + ORB installer, adapted for 22 entries. Output: ../Packages/Mixed22.
Run from AAA EAs/EA store:  uv run python "<this>"      (no MT5 and no compile)"""
import json, shutil, sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[2] / 'EA store'))
from tools import build_live_profiles as BL  # noqa: E402

TARGET = BL.R / 'Packages/Mixed22'; EDGE = BL.R / 'Packages/Edge10'; VERSION = 'MIXED22-NOGUARD-20261105'
EXTRA = ('orb-volume-profile-volume-confirmed', 'orb-volume-profile', 'xau-regime-switch', 'xau-elliott-wave-1-2-3')   # 2026-11-11 owner: Sell Nasdaq 15min removed for now
N = 17 + len(EXTRA)


def build():
    assert BL.sha(BL.CURRENT / 'RiskSupport.mqh') == BL.sha(EDGE / 'RiskSupport.mqh'), 'the two packages size trades differently'
    cur = json.loads(BL.read(BL.CURRENT / 'Package.json')); edge = json.loads(BL.read(EDGE / 'Package.json'))
    if TARGET.exists(): shutil.rmtree(TARGET)            # generated package only
    (TARGET / 'Experts').mkdir(parents=True); (TARGET / 'Sets').mkdir()
    entries = []
    for root, e in [(BL.CURRENT, x) for x in cur['entries']] + [(EDGE, x) for x in edge['entries'] if x['key'] in EXTRA]:
        shutil.copy2(root / e['expert'], TARGET / e['expert']); shutil.copy2(root / e['settings'], TARGET / e['settings'])
        entries.append({k: v for k, v in e.items() if k not in ('source', 'production_source', 'production_sha256')})
    assert len(entries) == N and len({e['key'] for e in entries}) == N and len({e['magic'] for e in entries}) == N
    three = next(e for e in entries if e['key'] == '3-way-gold')['inputs']
    assert three['InpMarketEntries'] == 'true' and all(three[k] == 'true' for k in ('InpEnableMomentum', 'InpEnableBreakout', 'InpEnableTurnOfMonth'))
    nas = next(e for e in entries if e['key'] == 'nasdaq-5m-candle-momentum')['inputs']; assert nas['InpStopMode'] == '0' and nas['InpInitialStopATR'] == '6.0'
    for name in ('RiskSupport.mqh', 'Installer-Helpers.ps1', 'Probe-MT5.py'): shutil.copy2(BL.CURRENT / name, TARGET / name)
    text = BL.read(BL.CURRENT / 'Install-Portfolio.ps1')
    for old, new, count in [('.Count -ne 17', f'.Count -ne {N}', 3), ('return $ready -eq 17', f'return $ready -eq {N}', 1), ('17-chart', f'{N}-chart', 1), ("'CALYX - CURRENT14 + ORB05 PORTFOLIO'", "'CALYX - MIXED 22 PORTFOLIO (NO GUARD)'", 1),
                            ('No FTMO restrictions, no shared $400/$450 daily stop. This is NOT the previously simulated guarded portfolio. Three-Way Gold risk applies to each module.',
                             'NO GUARD: no FTMO / prop limits, no shared daily stop, no adaptive governor. Risk is per trade per EA and stacks across open trades; 21 EAs can hold many trades at once. Three-Way Gold risk applies to each module.', 1),
                            ('CalyxCurrent14ORB05Setup', 'CalyxMixed22Setup', None)]:
        found = text.count(old); assert found and (count is None or found == count), (old, found)
        text = text.replace(old, new)
    BL.write(TARGET / 'Install-Portfolio.ps1', text)
    BL.save(TARGET / 'Package.json', dict(version=VERSION, profile='Calyx MIXED22 NOGUARD', entries=entries, orb_keys=cur['orb_keys'], default_percent=0.5, required_margin_mode=2, news=False, ftmo_guard=False, shared_daily_stop=False, adaptive_governor=False,
                                          selection='Owner 2026-11-05: FTMO17 + the five E10-only bots, as tested in Merged E10 FTMO17 2026-11-05.', compatibility=cur['compatibility'], no_live_installation=True,
                                          sources=dict(current14=cur['version'], edge10=edge['version'])))
    paths = [TARGET / n for n in ('Package.json', 'Install-Portfolio.ps1', 'Installer-Helpers.ps1', 'Probe-MT5.py')] + sorted((TARGET / 'Experts').glob('*.ex5')) + sorted((TARGET / 'Sets').glob('*.set'))
    BL.save(TARGET / 'Checksums.json', {str(p.relative_to(TARGET)).replace(chr(92), '/'): BL.sha(p) for p in paths})
    print('BUILT', VERSION, len(entries), 'EAs')


if __name__ == '__main__':
    build()
