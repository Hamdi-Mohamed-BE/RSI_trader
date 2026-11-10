"""P4 parity: the no-guard wrappers of the two research EAs (Packages/P4, with the P4 edits) vs the tested research EX5s, native Model 4, 150 ms, $10k,
2026-05-01 -> 2026-11-11 exclusive (recorded ticks). Same strategy inputs; research at InpRiskPercent 1.0 (balance), wrapper at InpPortfolioPercent 1.0 (equity),
so lots can differ slightly; parity = same entries (open time, side) and same exits (close time). Isolated tester only.
Run from AAA EAs/EA store:  uv run python "<this>" native | report"""
import gzip, importlib.util, json, os, shutil, sys, time
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; P4 = H.parent; LIVE = P4.parent; B = LIVE.parent
START, END = '2026.05.01', '2026.11.11'
pkg = json.loads((LIVE / 'Packages/P4/Package.json').read_text(encoding='utf-8-sig')); E = {e['key']: e for e in pkg['entries']}
CASES = {'ONB-RESEARCH': ('USTEC', 'M15', B / 'Video ORB VWAP Ideas Raw 2026-11-09/EA/Video Ideas Raw EA.ex5', dict({k: v for k, v in E['overnight-bias-orb']['inputs'].items() if not k.startswith('InpPortfolio') and k != 'InpAdaptivePortfolioControls'}, InpRiskPercent='1.0')),
         'ONB-P4': ('USTEC', 'M15', LIVE / 'Packages/P4' / E['overnight-bias-orb']['expert'], dict(E['overnight-bias-orb']['inputs'], InpPortfolioPercent='1.0')),
         'GBW-RESEARCH': ('XAUUSD', 'H4', B / 'Gold Band Wave Raw 2026-11-10/EA/Gold Band Wave Raw EA.ex5', dict({k: v for k, v in E['gold-band-wave']['inputs'].items() if not k.startswith('InpPortfolio') and k != 'InpAdaptivePortfolioControls'}, InpRiskPercent='1.0')),
         'GBW-P4': ('XAUUSD', 'H4', LIVE / 'Packages/P4' / E['gold-band-wave']['expert'], dict(E['gold-band-wave']['inputs'], InpPortfolioPercent='1.0'))}


def harness():
    spec = importlib.util.spec_from_file_location('octrun', B / 'Portfolio October 2026 ATR6 2026-11-03/run.py'); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
    return o


def native():
    o = harness(); b = o.b; b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    b.CONFIG.update(periods={'p6m': START}, end_date=END, deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=7200, expert_dir='CalyxP4Parity', controls={}, variants={})
    dest = b.TESTER / 'MQL5/Experts/CalyxP4Parity'; dest.mkdir(parents=True, exist_ok=True)
    for key, (sym, per, ex5, inputs) in CASES.items():
        name = f'{key}.ex5'; shutil.copy2(ex5, dest / name); b.CONFIG['variants'][key] = {'label': key, 'inputs': {}}; b.CONFIG['common_inputs'] = inputs; b.CONFIG['expert_file'] = name; b.CONFIG['period'] = o.TF[{'M15': 15, 'H4': 240}[per]]
        for attempt in range(4):
            try:
                b.run_case(sym, key, 'p6m'); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', key, flush=True); time.sleep(60)
        print('DONE', key, flush=True)


def report():
    out = {}
    for ea, sym in (('ONB', 'USTEC'), ('GBW', 'XAUUSD')):
        L = {}
        for v in ('RESEARCH', 'P4'):
            d = H / 'native' / f'nw-{sym}-{ea}-{v}-p6m'; T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda t: t['open_time'])
            L[v] = T
        a = [(t['open_time'], t.get('side') or t.get('type'), t['close_time']) for t in L['RESEARCH']]; b = [(t['open_time'], t.get('side') or t.get('type'), t['close_time']) for t in L['P4']]
        out[ea] = dict(research_trades=len(a), p4_trades=len(b), identical_entries_exits=a == b, research_net=round(sum(t['net_profit'] for t in L['RESEARCH']), 2), p4_net=round(sum(t['net_profit'] for t in L['P4']), 2),
                       first_difference=next(((x, y) for x, y in zip(a, b) if x != y), None))
    out['PASS'] = all(out[k]['identical_entries_exits'] and out[k]['research_trades'] > 0 for k in ('ONB', 'GBW'))
    (H / 'PARITY.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); print(json.dumps(out, indent=1, default=str))


if __name__ == '__main__':
    {'native': native, 'report': report}[sys.argv[1]]()
