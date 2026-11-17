"""Owner 2026-11-16: "show me UK100 bot performance over last 2 months, nasdaq 5 and overnight bias orb too".
The exact Best 1-Step no-guard package EX5s + package inputs (Packages/Best1Step), risk 1% of balance (InpPortfolioPercent 1.0; InpRiskPercent must stay 0.5 = wrapper calibration),
$10k each, native Model 4, 150 ms, 2026-09-16 -> 2026-11-16 (end exclusive). Nasdaq 5M as packaged (DI OFF, REPLACE) plus a DI ON copy.
No weekend-flat helper in the tester (the package's weekend close is a separate chart EA). Run from AAA EAs/EA store: uv run python "<this>" run | report"""
import gzip, importlib.util, json, os, shutil, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; B = H.parent; PKG = B / '_00 Live profiles/Packages/Best1Step'
START, END = '2026-09-16', '2026-11-16'
TF = {5: 'M5', 15: 'M15', 60: 'H1', 240: 'H4'}
CASES = [('UK100', 'uk100-monday-dip', {}), ('NAS5M_DIOFF', 'nasdaq-5m-candle-momentum', {}),
         ('NAS5M_DION', 'nasdaq-5m-candle-momentum', {'InpRequireDIAgreement': 'true'}), ('ONB', 'overnight-bias-orb', {})]


def harness():
    spec = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def run():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'
    pk = json.loads((PKG / 'Package.json').read_text(encoding='utf-8-sig')); dest = b.TESTER / 'MQL5/Experts/CalyxLast2M'; dest.mkdir(parents=True, exist_ok=True)
    for name, key, extra in CASES:
        if (H / 'native' / f'nw-{name}-{name}-2m' / 'trades.json.gz').exists(): continue
        e = next(x for x in pk['entries'] if x['key'] == key); fn = key + '.ex5'; shutil.copy2(PKG / e['expert'], dest / fn)
        inputs = dict(e['inputs'], InpPortfolioPercent='1.0', **extra)   # InpRiskPercent stays 0.5 (wrapper calibration check); InpPortfolioPercent sizes the trade
        b.CONFIG.update(model=4, end_date=END.replace('-', '.'), periods={'2m': START.replace('-', '.')}, deposit=10000, currency='USD', execution_delay_ms=150,
                        profile='Calyx Research Empty', timeout_seconds=7200, period=TF[int(e['period'])], expert_dir='CalyxLast2M', expert_file=fn, controls={},
                        common_inputs={}, variants={name: {'label': name, 'inputs': inputs}})
        sym = e['canonical']
        b.run_case(sym, name, '2m')
        src = H / 'native' / f'nw-{sym}-{name}-2m'; dst = H / 'native' / f'nw-{name}-{name}-2m'
        if src.exists() and src != dst: shutil.move(str(src), str(dst))
        print('DONE', name, flush=True)
    print('RUN DONE', flush=True)


def report():
    out = {}
    months = (datetime.fromisoformat(END) - datetime.fromisoformat(START)).days / 30.4375
    for name, _, _ in CASES:
        d = H / 'native' / f'nw-{name}-{name}-2m'; T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda t: t['close_time']); m = json.loads((d / 'run.json').read_text())['metrics']
        bal = pk = 1e4; dd = 0; R = []; wk = defaultdict(float); rows = []
        for t in T:
            r = t['net_profit'] / (0.01 * bal); R.append(r); bal += t['net_profit']; pk = max(pk, bal); dd = max(dd, 1 - bal / pk)
            rows.append(dict(open=t['open_time'][:16], close=t['close_time'][:16], side=t['side'], r=round(r, 2), net=round(t['net_profit'], 2)))
        w = [x for x in R if x > 0]; l = [x for x in R if x < 0]
        out[name] = dict(trades=len(T), per_month=round(len(T) / months, 1), per_day=round(len(T) / months / 21, 2), ret=m['return_pct'], net=round(sum(t['net_profit'] for t in T), 2),
                         total_r=round(sum(R), 2), pf=round(sum(w) / -sum(l), 2) if l else None, win=round(100 * len(w) / max(1, len(R)), 1),
                         avg_win_r=round(sum(w) / len(w), 2) if w else None, avg_loss_r=round(sum(l) / len(l), 2) if l else None, best_r=round(max(R), 2) if R else None,
                         worst_r=round(min(R), 2) if R else None, closed_dd=round(100 * dd, 2), mt5_dd=m['max_drawdown_pct'], ticks=json.loads((d / 'run.json').read_text()).get('metrics', {}).get('history_quality'), trades_list=rows)
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    for k, v in out.items(): print(k, {x: y for x, y in v.items() if x != 'trades_list'})


if __name__ == '__main__':
    {'run': run, 'report': report}[sys.argv[1]]()
