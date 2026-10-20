"""Item 2a: native backtests of every non-news catalogue EA for one live-debrief window (isolated tester only).

Generalises All EA Two Week Simulation 2026-10-09/run.py (same audited harness: one test at a time, frozen EX5 + SET
snapshots, report-input checks, FIFO fragment recombination by exit deal). Never touches the normal terminal or Ava.

uv run python ".../_Ops Monitor/debrief_backtest.py" --start 2026-10-12 --end 2026-10-19
"""
import argparse, gzip, hashlib, importlib.util, inspect, json, re, shutil
from pathlib import Path

from common import OUT, PACKAGE, get_catalog, recommended_mode, roster

spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
from app.mt5_evidence_jobs import _materialized_values, _set_values  # noqa: E402
import app.mt5_evidence_jobs as parser  # noqa: E402

code = inspect.getsource(parser._native_trades).replace('"number": len(trades) + 1,', '"exit_deal": cells[1], "number": len(trades) + 1,')
scope = dict(vars(parser)); exec(code, scope)
NO_TESTER = {'news-pulse-xau': 'verified tester calendar ends 2026-09-11 (see event_sheet.py)', 'news-pulse-xag': 'same', 'news-pulse-btc': 'same',
             'news-pulse-eurusd': 'same', 'gold-news-v9-direction': 'needs the external AI-news service'}
SYMBOL_ALIAS = {'US100': 'USTEC'}          # installer canonical tester symbol (2026-10-09 study)


def closing_deals(path, label):
    grouped = {}
    for t in scope['_native_trades'](path, label):
        g = grouped.get(t['exit_deal'])
        if g is None:
            grouped[t['exit_deal']] = dict(t); continue
        for f in ('volume', 'gross_profit', 'commission', 'swap', 'total_costs', 'net_profit'):
            g[f] += t[f]
        g['open_time'] = min(g['open_time'], t['open_time'])
    out = list(grouped.values())
    for i, t in enumerate(out):
        t['number'] = i + 1
    return out


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def freeze(root: Path, start: str, end: str) -> dict:
    sel_path = root / 'selection.json'
    if sel_path.exists():
        return json.loads(sel_path.read_text())
    phases = roster(); rows = []
    reviewed = json.loads((PACKAGE / 'Reviewed EA Deployment 2026-10-06/selection.json').read_text(encoding='utf-8-sig'))
    for p in get_catalog():
        if p.slug in NO_TESTER:
            continue
        mode = recommended_mode(p)
        ex = PACKAGE / (p.dynamic_expert_source if mode == 'dynamic' else p.expert_source)
        st = PACKAGE / (p.dynamic_set_source if mode == 'dynamic' else (p.safe_set_source or p.set_source) if mode == 'safe' else p.set_source)
        overrides = next((e.get('input_overrides') or {} for e in reviewed['entries'] if e['slug'] == p.slug), {})
        inputs = _materialized_values(_set_values(st, mode == 'safe')) | overrides
        dst = root / 'snapshot' / p.slug; dst.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ex, dst / 'selected.ex5'); shutil.copy2(st, dst / 'original.set')
        magic = next((inputs[k] for k in ('InpMagic', 'InpMagicNumber', 'MagicNumber', 'Magic') if k in inputs), None)
        rows.append(dict(slug=p.slug, label=p.label, phase=phases.get(p.slug, '-'), mode=mode, symbol=SYMBOL_ALIAS.get(p.canonical, p.canonical),
                         period=p.timeframe, expert=str(ex), set=str(st), ex5_sha256=sha(ex), set_sha256=sha(st), magic=magic,
                         reviewed_overrides=overrides, inputs=inputs))
    sel = dict(start=start, end=end, no_tester=NO_TESTER, rows=rows)
    sel_path.write_text(json.dumps(sel, indent=1))
    return sel


def run(root: Path, start: str, end: str):
    sel = freeze(root, start, end)
    b.ROOT = root; b.OUT = root / 'native'; b.STATUS = b.OUT / 'status.json'; b._native_trades = closing_deals
    b.CONFIG.update(periods={'wk': start.replace('-', '.')}, end_date=end.replace('-', '.'), deposit=10000, currency='USD', model=4,
                    execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=3600, expert_dir='CalyxDebrief' + start.replace('-', ''))
    assert not b.isolated_running() and not b.port_3000_busy(), 'Isolated tester is occupied; leave other work alone'
    b.OUT.mkdir(parents=True, exist_ok=True); failures = []
    for row in sel['rows']:
        slug = row['slug']; dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
        src = root / 'snapshot' / slug / 'selected.ex5'; assert sha(src) == row['ex5_sha256']
        shutil.copy2(src, dest / (slug + '.ex5'))
        b.CONFIG.update(expert_file=slug + '.ex5', period=row['period'], common_inputs=row['inputs'], variants={slug: {'inputs': {}}})
        done = b.OUT / f"nw-{row['symbol']}-{slug}-wk" / 'run.json'
        if done.exists() and json.loads(done.read_text()).get('audited') is not None:
            continue
        try:
            m = b.run_case(row['symbol'], slug, 'wk')
        except SystemExit:
            failures.append(slug); b.status(state='running', event=f'CASE FAILED {slug}; continuing'); continue
        report = b.REPORT_DIR / (m['case'] + '.htm')
        actual = b._report_inputs(report)
        missing = [k for k, v in row['inputs'].items() if k not in actual or not b._same_setting(v, actual[k])]
        trades = closing_deals(report, m['case'])
        (b.OUT / m['case'] / 'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(), mtime=0))
        m.update(input_mismatch=missing[:20], trade_count_ok=len(trades) == m['metrics']['trades'],
                 cash_ok=abs(sum(t['net_profit'] for t in trades) - m['metrics']['net_profit']) <= max(.05, len(trades) * .011))
        m['audited'] = bool(not missing and m['trade_count_ok'] and m['cash_ok'] and not m['journal_flags']['init_failed'] and not m['journal_flags']['critical'])
        done.write_text(json.dumps(m, indent=1))
        if not m['audited']:
            failures.append(slug)
    b.status(state='ALL DONE', event=f'debrief backtests done; failures/flags: {failures}')
    print('failures/flags:', failures)


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('--start', required=True); ap.add_argument('--end', required=True)
    a = ap.parse_args()
    root = OUT / 'debrief' / f'{a.start}_{a.end}'; root.mkdir(parents=True, exist_ok=True)
    run(root, a.start, a.end)
