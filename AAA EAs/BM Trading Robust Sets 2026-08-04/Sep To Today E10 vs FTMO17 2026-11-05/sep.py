"""Owner 2026-11-05: compare E10 and FTMO17 from the start of September to today, including today's open trades. Native Model 4, 150 ms, $10k, 1%, real ticks, 2026-09-01 to the end of the available data (ToDate 2026-11-06), every EA starting flat on Sep 1, same EX5s and inputs as
Merged E10 FTMO17 2026-11-05/native.py. Trades the tester closes as 'end of test' are the ones still open at the data end, marked at the last price. E10 3 Way Gold = the '3WG BRK' trades. Portfolio replay from $10k as analyze.py (closed balance): no guard, Prop guard, 1-Step guard, at 0.5% and 1%.
Run from AAA EAs/EA store: uv run python "<this>" native, then uv run python "<this>" report. -> RESULTS.json, RESULTS.md"""
import gzip, importlib.util, json, os, shutil, sys, time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; M = PACKAGE / 'Merged E10 FTMO17 2026-11-05'
EXTRA = {'orb-volume-profile-volume-confirmed': 'ORB Volume Profile Volume Confirmed', 'orb-volume-profile': 'ORB Volume Profile', 'sell-nasdaq-15min': 'Sell Nasdaq 15min', 'xau-regime-switch': 'XAU Regime Switch', 'xau-elliott-wave-1-2-3': 'XAU Elliott Wave 1-2-3'}
E10_KEYS = {'usdjpy-london-open-momentum', 'ema3', 'nasdaq-5m-candle-momentum', 'xau-rsi-vwap'} | set(EXTRA)


def native():
    spec = importlib.util.spec_from_file_location('octrun', PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/run.py'); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o); b = o.b
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    b.CONFIG.update(periods={'sep': '2026.09.01'}, end_date='2026.11.06', deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=7200, expert_dir='CalyxSepToday', controls={}, variants={})
    dest = b.TESTER / 'MQL5/Experts/CalyxSepToday'; dest.mkdir(parents=True, exist_ok=True)
    jobs = [(k, str(o.C14 / e['expert']), e['canonical'], o.TF[e['period']], {a: str(v).lower() if isinstance(v, bool) else str(v) for a, v in i.items()}) for k, tag, e, i in o.cases() if tag == 'NEW']
    labels = {v: k for k, v in EXTRA.items()}
    jobs += [(labels[it['label']], it['expert_path'], it['canonical'], o.TF[int(it['period'])], i) for slug, tag, it, i in o.full_cases() if tag == 'FULL' and it['label'] in labels]
    assert len(jobs) == 22; plan = []
    for key, ex5, sym, per, inputs in jobs:
        name = f'{key}.ex5'; shutil.copy2(ex5, dest / name); b.CONFIG['variants'][key] = {'label': key, 'inputs': {}}; b.CONFIG['common_inputs'] = inputs; b.CONFIG['expert_file'] = name; b.CONFIG['period'] = per
        plan.append(dict(key=key, symbol=sym, period=per, case=f'nw-{sym}-{key}-sep')); (H / 'PLAN.json').write_text(json.dumps(plan, indent=1), encoding='utf-8')
        for attempt in range(4):
            try:
                b.run_case(sym, key, 'sep'); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', key, flush=True); time.sleep(60)
    print('ALL DONE', datetime.now(timezone.utc).isoformat(), flush=True)


def report():
    src = (M / 'analyze.py').read_text(encoding='utf-8').split('LEDGERS = {k: ledger(k) for k in RUNS}')[0].replace("H = Path(__file__).resolve().parent;", f"H = Path(r'{M}');")
    tail = (M / 'analyze.py').read_text(encoding='utf-8'); rep = tail[tail.index('def weekdays(a, b):'):tail.index('out = dict(native_checks')]
    ns = dict(__name__='defs', __file__=str(M / 'analyze.py')); exec(compile(src + '\n' + rep, 'defs', 'exec'), ns); replay = ns['replay']; ns['WINDOWS']['sep'] = ('2026-09-01', '2026-11-06')
    plan = json.loads((H / 'PLAN.json').read_text(encoding='utf-8')); ALL = {}; bad = []; last = ''
    for p in plan:
        d = H / 'native' / p['case']; meta = json.loads((d / 'run.json').read_text(encoding='utf-8')) if (d / 'run.json').exists() else dict(ok=False)
        if not meta.get('ok'): bad.append(p['key']); ALL[p['key']] = []; continue
        T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda x: x['close_time']); bal = 1e4; rows = []
        for x in T:
            r = x['net_profit'] / (0.01 * bal); bal += x['net_profit']; last = max(last, x['close_time'])
            rows.append(dict(key=p['key'], symbol=p['symbol'], o=datetime.fromisoformat(x['open_time']).replace(tzinfo=timezone.utc), c=datetime.fromisoformat(x['close_time']).replace(tzinfo=timezone.utc), R=r, comment=x.get('entry_comment') or '', eot='end of test' in (x.get('exit_comment') or '').lower(), side=x['side'], open_price=x['open_price'], close_price=x['close_price'], open_time=x['open_time']))
        ALL[p['key']] = rows
    PORT = {'FTMO17': [r for k, v in ALL.items() if k not in EXTRA for r in v], 'E10': [r for k, v in ALL.items() if k in E10_KEYS for r in v] + [r for r in ALL.get('3-way-gold', []) if r['comment'].startswith('3WG BRK')]}
    out = dict(bad=bad, last_close=last, portfolios={}, per_ea={}, open={})
    L = [f'Data to {last} (server time, about UTC). Failed runs: {bad or "none"}.', '', '| Portfolio | Version | Risk | Return | Of which still open | PF | Win % | Trades taken (of signals) | Per weekday | Closed DD | Best / worst day |', '|---|---|---|---:|---:|---:|---:|---|---:|---:|---|']
    NAMES = {'NONE': 'No guard', 'PROP': 'Prop guard', 'ONESTEP': '1-Step guard'}
    for n, rows in PORT.items():
        out['portfolios'][n] = {}
        for mode in NAMES:
            for risk in (0.005, 0.01):
                x = replay(rows, 'sep', mode, risk); out['portfolios'][n][f'{mode}-{risk * 100:g}'] = x
                L.append(f"| {n} | {NAMES[mode]} | {risk * 100:g}% | {x['ret']:+.2f}% | | {x['pf']} | {x['win']} | {x['trades']} ({x['signals']}) | {x['per_weekday']} | {x['closed_dd']}% | {x['best_day']:+.2f}% / {x['worst_day']:+.2f}% |")
        opened = [r for r in rows if r['eot']]; out['open'][n] = [dict(ea=r['key'], symbol=r['symbol'], side=r['side'], opened=r['open_time'][:16], entry=r['open_price'], last=r['close_price'], open_r=round(r['R'], 2)) for r in sorted(opened, key=lambda r: -r['R'])]
    L += ['', '| Portfolio | Open trades at the data end | Open R in total | Closed R | Total R | Trades (/weekday) |', '|---|---:|---:|---:|---:|---|']
    for n, rows in PORT.items():
        o_ = sum(r['R'] for r in rows if r['eot']); c_ = sum(r['R'] for r in rows if not r['eot']); L.append(f"| {n} | {sum(r['eot'] for r in rows)} | {o_:+.2f} | {c_:+.2f} | {o_ + c_:+.2f} | {len(rows)} ({len(rows) / ns['weekdays']('2026-09-01', '2026-11-06'):.2f}) |")
    L += ['', '| EA | FTMO17 | E10 | Closed trades / wins | Closed R | Open now: side, entry -> last, open R |', '|---|---|---|---|---:|---|']
    for k, rows in sorted(ALL.items(), key=lambda kv: -sum(r['R'] for r in kv[1])):
        rs = [r for r in rows if not r['eot'] and (True)]; op = [r for r in rows if r['eot']]
        out['per_ea'][k] = dict(closed=len(rs), wins=sum(r['R'] > 0 for r in rs), closed_r=round(sum(r['R'] for r in rs), 2), open=[dict(side=r['side'], comment=r['comment'][:12], entry=r['open_price'], last=r['close_price'], open_r=round(r['R'], 2)) for r in op])
        o_t = '; '.join(f"{r['side']} {r['comment'][:7] if k == '3-way-gold' else ''} {r['open_price']} -> {r['close_price']}, {r['R']:+.2f}R" for r in op) or '-'
        L.append(f"| {k} | {'yes' if k not in EXTRA else '-'} | {'yes' if k in E10_KEYS else ('breakout only' if k == '3-way-gold' else '-')} | {len(rs)} / {sum(r['R'] > 0 for r in rs)} | {sum(r['R'] for r in rs):+.2f} | {o_t} |")
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1, default=str), encoding='utf-8'); (H / 'RESULTS.md').write_text('\n'.join(L) + '\n', encoding='utf-8'); print('\n'.join(L))


if __name__ == '__main__':
    native() if sys.argv[1] == 'native' else report()
