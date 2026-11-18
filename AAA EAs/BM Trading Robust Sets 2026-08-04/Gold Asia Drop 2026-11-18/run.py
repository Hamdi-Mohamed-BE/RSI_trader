"""Gold Asia drop 2026-11-18: which of our gold EAs traded the fall (XAUUSD 3,849 at 00:00 UTC -> 3,764.6 at 07:30 UTC, -2.2%; low 3,742.7 by 13:00 UTC).
Every XAUUSD EA of the Full EA portfolio (installer effective inputs, FULL_ITEMS.json of Portfolio October 2026 ATR6 2026-11-03; risk 1%, adaptive governor off)
+ Gold Band Wave (Packages/P4 no-guard wrapper). News EAs excluded (they trade scheduled releases only).
Native Model 4 (real ticks), 150 ms, $10k each, standalone, 2026-11-01 -> 2026-11-19 (the tester stops at the last available data).
Run from AAA EAs/EA store:  uv run python "<this>" run | report"""
import gzip, importlib.util, inspect, json, os, shutil, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent
spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
import app.mt5_evidence_jobs as parser  # noqa: E402

code = inspect.getsource(parser._native_trades).replace('"number": len(trades) + 1,', '"exit_deal": cells[1], "number": len(trades) + 1,')
scope = dict(vars(parser)); exec(code, scope)


def closing_deals(path, label):
    grouped = {}
    for t in scope['_native_trades'](path, label):
        g = grouped.get(t['exit_deal'])
        if g is None: grouped[t['exit_deal']] = dict(t); continue
        for f in ('volume', 'gross_profit', 'commission', 'swap', 'total_costs', 'net_profit'): g[f] += t[f]
        g['open_time'] = min(g['open_time'], t['open_time'])
    out = list(grouped.values())
    for i, t in enumerate(out): t['number'] = i + 1; t['result'] = 'Win' if t['net_profit'] > 0 else 'Loss' if t['net_profit'] < 0 else 'Flat'
    return out


b._native_trades = closing_deals
b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
b.CONFIG.update(periods={'nov': '2026.11.01'}, end_date='2026.11.19', deposit=10000, currency='USD', model=4, execution_delay_ms=150,
                profile='Calyx Research Empty', timeout_seconds=3600, expert_dir='CalyxGoldAsiaDrop', controls={}, variants={})
TF = {1: 'M1', 5: 'M5', 15: 'M15', 30: 'M30', 60: 'H1', 240: 'H4'}
RISK_KEYS = ('InpRiskPercent', 'InpGridRiskPercent', 'InpMomentumRiskPercent', 'InpContrarianRiskPercent')
FULL = PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/FULL_ITEMS.json'
P4 = PACKAGE / '_00 Live profiles/Packages/P4'


def cases():
    out = []
    for it in json.loads(FULL.read_text(encoding='utf-8-sig')):
        if it['canonical'] != 'XAUUSD': continue
        inputs = {k: str(v) for k, v in it['inputs'].items()}
        for k in RISK_KEYS:
            if k in inputs: inputs[k] = '1.0'
        inputs['InpAdaptivePortfolioControls'] = 'false'
        slug = ''.join(c if c.isalnum() else '-' for c in it['label'].lower()).strip('-')
        out.append(dict(slug=slug, label=it['label'], ex5=Path(it['expert_path']), period=TF[int(it['period'])], inputs=inputs))
    pk = json.loads((P4 / 'Package.json').read_text(encoding='utf-8-sig')); e = next(x for x in pk['entries'] if x['key'] == 'gold-band-wave')
    out.append(dict(slug='gold-band-wave', label='Gold Band Wave', ex5=P4 / e['expert'], period=TF[int(e['period'])], inputs=dict(e['inputs'], InpPortfolioPercent='1.0')))
    return out


def run():
    assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True); plan = []
    for c in cases():
        name = c['slug'] + '.ex5'; shutil.copy2(c['ex5'], dest / name)
        b.CONFIG['variants'] = {c['slug']: {'label': c['label'], 'inputs': {}}}; b.CONFIG['common_inputs'] = c['inputs']
        b.CONFIG['expert_file'] = name; b.CONFIG['period'] = c['period']
        plan.append(dict(slug=c['slug'], label=c['label'], period=c['period'], ex5=str(c['ex5']), ex5_sha=b.sha(c['ex5'])))
        (H / 'PLAN.json').write_text(json.dumps(plan, indent=1), encoding='utf-8')
        if (b.OUT / f"nw-XAUUSD-{c['slug']}-nov" / 'trades.json.gz').exists(): continue
        try: b.run_case('XAUUSD', c['slug'], 'nov')
        except SystemExit: print('CASE FAILED', c['slug'], flush=True)
    print('RUN DONE', flush=True)


def report():
    out = {}
    for c in cases():
        d = b.OUT / f"nw-XAUUSD-{c['slug']}-nov"
        if not (d / 'trades.json.gz').exists(): out[c['label']] = 'no run'; continue
        T = json.loads(gzip.open(d / 'trades.json.gz').read())
        today = [t for t in T if t['close_time'][:10] == '2026-11-18' or t['open_time'][:10] == '2026-11-18']
        j = gzip.open(d / 'journal.txt.gz').read().decode('utf-8', 'replace')
        end_open = 'end of test' in j.lower()
        out[c['label']] = dict(period=c['period'], trades_today=[dict(side=t['side'], open=t['open_time'][:16], close=t['close_time'][:16], open_price=t['open_price'], close_price=t['close_price'],
                                                                     net=round(t['net_profit'], 2), r=round(t['net_profit'] / 100.0, 2), exit=t.get('exit_comment', '')) for t in today],
                               net_today=round(sum(t['net_profit'] for t in today), 2), month_trades=len(T), month_net=round(sum(t['net_profit'] for t in T), 2))
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    for k, v in sorted(out.items(), key=lambda kv: -(kv[1]['net_today'] if isinstance(kv[1], dict) else -1e9)):
        if not isinstance(v, dict): print(k, v); continue
        print(f"{k:38s} {v['period']:4s} today {v['net_today']:+8.2f}  ({len(v['trades_today'])} trades)  Nov {v['month_net']:+8.2f} ({v['month_trades']})")
        for t in v['trades_today']: print('      ', t)


if __name__ == '__main__':
    {'run': run, 'report': report}[sys.argv[1]]()
