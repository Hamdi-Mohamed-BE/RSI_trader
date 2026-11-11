"""Native comparison (Model 4, 150 ms, $10k, M15 USTEC, 2019-01-01 -> 2026-11-11 excl., preset = Merged E10 FTMO17 2026-11-05 long-history run's SET):
OLD = original EX5 (before/), FIX_1 = fixed EX5, InpMaxAttemptsPerDay=1 (must equal OLD), FIX_2 / FIX_3 = re-arm after a stop-out (research).
Run from AAA EAs/EA store: uv run python "<this>" run | report"""
import gzip, importlib.util, json, os, shutil, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; B = H.parent
NEW = B / 'Sell Nasdaq 15min Research 2026-09-08/Dynamic Exit Research/EA/Sell Nasdaq 15min Dynamic Exit Research EA.ex5'
OLD = H / 'before/Sell Nasdaq 15min Research 2026-09-08/Dynamic Exit Research/EA/Sell Nasdaq 15min Dynamic Exit Research EA.ex5'
SET = B / 'Merged E10 FTMO17 2026-11-05/native/nw-USTEC-sell-nasdaq-15min-all/nw-USTEC-sell-nasdaq-15min-all.set'
CASES = {'OLD': ('old.ex5', {}), 'FIX_1': ('fix.ex5', {'InpMaxAttemptsPerDay': '1'}), 'FIX_2': ('fix.ex5', {'InpMaxAttemptsPerDay': '2'}), 'FIX_3': ('fix.ex5', {'InpMaxAttemptsPerDay': '3'})}
START, END = '2019-01-01', '2026-11-11'


def set_inputs(p):
    raw = p.read_bytes(); t = raw.decode('utf-16' if raw.startswith((b'\xff\xfe', b'\xfe\xff')) else 'utf-8-sig'); out = {}
    for line in t.splitlines():
        if '=' in line and not line.startswith(';'): k, v = line.split('=', 1); out[k.strip()] = v.split('||')[0].strip()
    return out


def run():
    spec = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts/CalyxSellNasFix'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(OLD, dest / 'old.ex5'); shutil.copy2(NEW, dest / 'fix.ex5')
    base = set_inputs(SET)
    b.CONFIG.update(periods={'all': START.replace('-', '.')}, end_date=END.replace('-', '.'), deposit=10000, currency='USD', model=4, execution_delay_ms=150, period='M15',
                    profile='Calyx Research Empty', timeout_seconds=14400, expert_dir='CalyxSellNasFix', controls={}, variants={}, common_inputs=base)
    for k, (ex5, extra) in CASES.items():
        if (b.OUT / f'nw-USTEC-{k}-all' / 'trades.json.gz').exists(): continue
        b.CONFIG['expert_file'] = ex5; b.CONFIG['variants'] = {k: {'label': k, 'inputs': extra}}; b.run_case('USTEC', k, 'all')
    print('RUN DONE', flush=True)


def rows(k):
    T = sorted(json.loads(gzip.open(H / 'native' / f'nw-USTEC-{k}-all' / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4; out = []
    for t in T: out.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (0.01 * bal), key=(t['open_time'], t['side'], round(t['open_price'], 2)))); bal += t['net_profit']
    return out, bal


def stats(x, a, b_):
    x = [r for r in x if a <= r['o'][:10] < b_]; gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0); eq = pk = dd = 0.0; days = defaultdict(int)
    for r in x: eq += r['r']; pk = max(pk, eq); dd = max(dd, pk - eq); days[r['o'][:10]] += 1
    months = (datetime.fromisoformat(b_) - datetime.fromisoformat(a)).days / 30.4375
    return dict(trades=len(x), per_month=round(len(x) / months, 2), per_day=round(len(x) / months / 21, 3), total_r=round(sum(r['r'] for r in x), 1), pf=round(gw / gl, 2) if gl else None,
                win=round(100 * sum(r['r'] > 0 for r in x) / max(1, len(x)), 1), closed_dd_r=round(dd, 1), days_with_2plus=sum(1 for v in days.values() if v >= 2))


def report():
    W = {'all': (START, END), 'dev 2019-23': (START, '2023-11-11'), 'val 23-24': ('2023-11-11', '2024-11-11'), 'oos 24-26': ('2024-11-11', END), 'last year': ('2025-11-11', END)}
    out = {}; R = {}
    for k in CASES:
        R[k], bal = rows(k); out[k] = dict(final_balance=round(bal, 2), windows={w: stats(R[k], *v) for w, v in W.items()},
                                         years={str(y): stats(R[k], f'{y}-01-01', f'{y + 1}-01-01' if y < 2026 else END)['total_r'] for y in range(2019, 2027)})
    out['parity_OLD_vs_FIX_1'] = dict(identical_entries=[r['key'] for r in R['OLD']] == [r['key'] for r in R['FIX_1']], old=len(R['OLD']), fix1=len(R['FIX_1']))
    for k in ('FIX_2', 'FIX_3'):
        base = {r['key'] for r in R['FIX_1']}; extra = [r for r in R[k] if r['key'] not in base]
        out[k]['extra_trades'] = dict(n=len(extra), total_r=round(sum(r['r'] for r in extra), 1), win=round(100 * sum(r['r'] > 0 for r in extra) / max(1, len(extra)), 1))
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1)[:6000])


if __name__ == '__main__':
    run() if sys.argv[1:] == ['run'] else report()
