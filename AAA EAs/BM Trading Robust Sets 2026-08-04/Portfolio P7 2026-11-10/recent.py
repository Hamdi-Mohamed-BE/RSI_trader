"""Owner 2026-11-10: P7 EA by EA for October and November so far. Native Model 4 (recorded ticks in 2026), 150 ms, $10k, each EA standalone at 1%,
2026-10-01 -> 2026-11-11 exclusive (data to the latest the tester has). EMA3 / RSI VWAP / ORB VP: the same EX5s and inputs as Merged E10 FTMO17 2026-11-05/native.py;
Vault Break / Overnight Bias ORB: the video research EX5; Nasdaq 5M: the deployed REPLACE EX5 with the Edge 10 inputs, DI OFF; Gold Band Wave: its research EX5.
Run from AAA EAs/EA store: uv run python "<this>" native, then uv run python "<this>" report -> RECENT.json, RECENT.md"""
import gzip, importlib.util, json, os, shutil, sys, time
from collections import defaultdict
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent
spec = importlib.util.spec_from_file_location('p7', H / 'p7.py'); P7 = importlib.util.module_from_spec(spec); spec.loader.exec_module(P7)
START, END = '2026.10.01', '2026.11.11'
MONTHS = {'October': ('2026-10-01', '2026-11-01'), 'November so far': ('2026-11-01', '2026-11-11')}


def jobs():
    spec = importlib.util.spec_from_file_location('octrun', PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/run.py'); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
    out = [(k, str(o.C14 / e['expert']), e['canonical'], o.TF[e['period']], {a: str(v).lower() if isinstance(v, bool) else str(v) for a, v in i.items()}) for k, tag, e, i in o.cases() if tag == 'NEW' and k in ('ema3', 'xau-rsi-vwap')]
    out += [('orb-volume-profile', it['expert_path'], it['canonical'], o.TF[int(it['period'])], i) for slug, tag, it, i in o.full_cases() if tag == 'FULL' and it['label'] == 'ORB Volume Profile']
    for label, (slug, _t, sym, per, src, inputs) in P7.NEW.items():
        out.append((slug, str(Path(src).with_suffix('.ex5')), sym, per, dict(inputs or P7.edge_nasdaq())))
    assert sorted(j[0] for j in out) == sorted(P7.EAS), [j[0] for j in out]
    return o, out


def native():
    o, todo = jobs(); b = o.b; b.ROOT = H; b.OUT = H / 'recent'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    b.CONFIG.update(periods={'recent': START}, end_date=END, deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=7200, expert_dir='CalyxP7Recent', controls={}, variants={})
    dest = b.TESTER / 'MQL5/Experts/CalyxP7Recent'; dest.mkdir(parents=True, exist_ok=True)
    for key, ex5, sym, per, inputs in todo:
        name = f'{key}.ex5'; shutil.copy2(ex5, dest / name); b.CONFIG['variants'][key] = {'label': key, 'inputs': {}}; b.CONFIG['common_inputs'] = inputs; b.CONFIG['expert_file'] = name; b.CONFIG['period'] = per
        for attempt in range(4):
            try:
                b.run_case(sym, key, 'recent'); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', key, flush=True); time.sleep(60)
        print('DONE', key, flush=True)


def report():
    o, todo = jobs(); out = dict(eas={}, portfolio={}); allrows = []; last = ''
    for key, ex5, sym, per, inputs in todo:
        d = H / 'recent' / f'nw-{sym}-{key}-recent'
        if not (d / 'trades.json.gz').exists(): out['eas'][key] = 'missing'; continue
        T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4; rows = []
        for t in T:
            rows.append(dict(o=t['open_time'], c=t['close_time'], r=t['net_profit'] / (0.01 * bal), net=t['net_profit'], open_at_end='end of test' in (t.get('exit_comment') or '').lower())); bal += t['net_profit']; last = max(last, t['close_time'])
        allrows += [dict(r, ea=key) for r in rows]; out['eas'][key] = {}
        for m, (a, b_) in MONTHS.items():
            x = [r for r in rows if a <= r['o'][:10] < b_]; gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0)
            out['eas'][key][m] = dict(trades=len(x), wins=sum(r['r'] > 0 for r in x), win=round(100 * sum(r['r'] > 0 for r in x) / len(x), 1) if x else None, pf=round(gw / gl, 2) if gl else None,
                                      total_r=round(sum(r['r'] for r in x), 2), usd_at_1pct_10k=round(sum(r['net'] for r in x), 2), still_open=sum(r['open_at_end'] for r in x))
    for m, (a, b_) in MONTHS.items():
        x = sorted((r for r in allrows if a <= r['o'][:10] < b_), key=lambda r: r['c']); eq = pk = dd = 0.0; days = defaultdict(float)
        for r in x:
            eq += r['r']; pk = max(pk, eq); dd = max(dd, pk - eq); days[r['c'][:10]] += r['r']
        gw = sum(r['r'] for r in x if r['r'] > 0); gl = -sum(r['r'] for r in x if r['r'] < 0)
        out['portfolio'][m] = dict(trades=len(x), win=round(100 * sum(r['r'] > 0 for r in x) / len(x), 1) if x else None, pf=round(gw / gl, 2) if gl else None, total_r=round(sum(r['r'] for r in x), 2),
                                   closed_dd_r=round(dd, 2), worst_day_r=round(min(days.values()), 2) if days else None, best_day_r=round(max(days.values()), 2) if days else None)
    out['last_close'] = last
    (H / 'RECENT.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1)[:6000])


if __name__ == '__main__':
    {'native': native, 'report': report}[sys.argv[1]]()
