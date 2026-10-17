"""User request 2026-10-09: simulate every EA over the last two weeks and combine the results.

Reuses the audited Recent EA Shortlist 2026-09-30 / No Wick Candle Raw 2026-09-25 harness unchanged: isolated tester
only, one test at a time, frozen EX5 + SET snapshots, report-input checks, FIFO-fragment recombination.
Each EA runs standalone ($10,000, its selected recommended mode, 1% risk as in its SET); the combined portfolio is a
LEDGER OVERLAY of those standalone runs, not one shared-account native test.

python run.py freeze | run | summary
"""
import os, sys, json, importlib.util, shutil, hashlib, gzip, re, inspect
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
from app.catalog import get_catalog  # noqa: E402
from app.mt5_evidence_jobs import _set_values, _materialized_values  # noqa: E402
import app.mt5_evidence_jobs as parser  # noqa: E402

code = inspect.getsource(parser._native_trades).replace('"number": len(trades) + 1,', '"exit_deal": cells[1], "number": len(trades) + 1,')
scope = dict(vars(parser)); exec(code, scope)


def closing_deals(path, label):
    fragments = scope['_native_trades'](path, label); grouped = {}
    for t in fragments:
        key = t['exit_deal']
        if key not in grouped:
            grouped[key] = dict(t); continue
        g = grouped[key]
        for field in ('volume', 'gross_profit', 'commission', 'swap', 'total_costs', 'net_profit'):
            g[field] += t[field]
        g['open_time'] = min(g['open_time'], t['open_time'])
    out = list(grouped.values())
    for i, t in enumerate(out):
        t['number'] = i + 1; t['result'] = 'Win' if t['net_profit'] > 0 else 'Loss' if t['net_profit'] < 0 else 'Flat'
    return out


b._native_trades = closing_deals
PRIVATE = b.CONFIG['login']
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
START, END = '2026.09.25', '2026.10.09'
b.CONFIG.update(periods={'2w': START}, end_date=END, deposit=10000, currency='USD', model=4, execution_delay_ms=150,
                profile='Calyx Research Empty', timeout_seconds=3600, expert_dir='CalyxTwoWeek20261009')
# Cannot be simulated honestly for this window: News Pulse needs a verified point-in-time calendar (the checked-in
# verified tester calendar ends 2026-09-11); Gold News V9 needs the external AI-news service. Their demo-account
# results are reported instead.
EXCLUDED = {'news-pulse-xau': 'no verified tester calendar after 2026-09-11', 'news-pulse-xag': 'no verified tester calendar after 2026-09-11',
            'news-pulse-btc': 'no verified tester calendar after 2026-09-11', 'news-pulse-eurusd': 'no verified tester calendar after 2026-09-11',
            'gold-news-v9-direction': 'needs the external AI-news service; no tester evidence exists'}
REVIEWED = json.loads((PACKAGE / 'Reviewed EA Deployment 2026-10-06/selection.json').read_text(encoding='utf-8-sig'))
PHASE = {e['slug']: e['phase'] for e in REVIEWED['entries']}


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def freeze():
    if (ROOT / 'selection.json').exists():
        return json.loads((ROOT / 'selection.json').read_text())
    rows = []
    for p in get_catalog():
        if p.slug in EXCLUDED:
            continue
        mode = 'dynamic' if p.recommended_dynamic_mode else 'safe' if p.recommended_safe_mode else 'standard'
        ex = PACKAGE / (p.dynamic_expert_source if mode == 'dynamic' else p.expert_source)
        st = PACKAGE / (p.dynamic_set_source if mode == 'dynamic' else (p.safe_set_source or p.set_source) if mode == 'safe' else p.set_source)
        variants = [(p.slug, {})]
        # The reviewed profile runs Trend Progression with its saved 1.5R overrides; simulate both.
        reviewed = next((e for e in REVIEWED['entries'] if e['slug'] == p.slug and e.get('input_overrides')), None)
        if reviewed:
            variants.append((p.slug + '--reviewed', reviewed['input_overrides']))
        for case_slug, overrides in variants:
            dst = ROOT / 'snapshot' / case_slug; dst.mkdir(parents=True, exist_ok=True)
            shutil.copy2(ex, dst / 'selected.ex5'); shutil.copy2(st, dst / 'original.set')
            inputs = _materialized_values(_set_values(st, mode == 'safe')) | overrides
            (dst / 'inputs.json').write_text(json.dumps(inputs, indent=2))
            source = ex.with_suffix('.mq5')
            rows.append(dict(slug=case_slug, product=p.slug, label=p.label + (' (reviewed 1.5R)' if overrides else ''), mode=mode,
                             phase=PHASE.get(p.slug, '-'), symbol=p.canonical, period=p.timeframe, expert=str(ex), set=str(st),
                             ex5_sha256=sha(ex), set_sha256=sha(st), source_sha256=sha(source) if source.exists() else None,
                             adaptive=inputs.get('InpAdaptivePortfolioControls'), inputs=inputs))
    (ROOT / 'selection.json').write_text(json.dumps(dict(start=START, end=END, excluded=EXCLUDED, rows=rows), indent=2))
    return json.loads((ROOT / 'selection.json').read_text())


def run():
    sel = freeze(); rows = sel['rows']
    assert not b.isolated_running() and not b.port_3000_busy(), 'Tester is occupied; leave other work alone'
    profile = b.TESTER / 'MQL5/Profiles/Charts' / b.CONFIG['profile']
    assert profile.is_dir() and not list(profile.glob('*.chr'))
    common = b.text(b.TESTER / 'Config/common.ini')
    assert int(re.search(r'(?im)^Login\s*=\s*(\d+)', common).group(1)) == int(PRIVATE)
    del common
    b.OUT.mkdir(exist_ok=True)
    failures = []
    for row in rows:
        slug = row['slug']; dest = b.TESTER / 'MQL5/Experts' / b.CONFIG['expert_dir']; dest.mkdir(parents=True, exist_ok=True)
        src = ROOT / 'snapshot' / slug / 'selected.ex5'; assert sha(src) == row['ex5_sha256']
        shutil.copy2(src, dest / (slug + '.ex5'))
        b.CONFIG.update(expert_file=slug + '.ex5', period=row['period'], common_inputs=row['inputs'], variants={slug: {'inputs': {}}})
        done = b.OUT / f"nw-{row['symbol']}-{slug}-2w" / 'run.json'
        if done.exists() and json.loads(done.read_text()).get('audited'):
            continue
        try:
            m = b.run_case(row['symbol'], slug, '2w')
        except SystemExit:
            failures.append(slug); b.status(state='running', event=f'CASE FAILED {slug}; continuing'); continue
        folder = b.OUT / m['case']; report = b.REPORT_DIR / (m['case'] + '.htm')
        actual = b._report_inputs(report)
        missing = [k for k, v in row['inputs'].items() if k not in actual or not b._same_setting(v, actual[k])]
        trades = closing_deals(report, m['case'])
        (folder / 'trades.json.gz').write_bytes(gzip.compress(json.dumps(trades).encode(), mtime=0))
        m['input_mismatch'] = missing[:20]
        m['trade_count_ok'] = len(trades) == m['metrics']['trades']
        m['cash_ok'] = abs(sum(t['net_profit'] for t in trades) - m['metrics']['net_profit']) <= max(.05, len(trades) * .011)
        m['ex5_sha256'] = row['ex5_sha256']
        m['metrics']['relative_equity_dd_pct'] = b._number(b._metric(b._read_report(report), 'Equity Drawdown Relative'))
        m['audited'] = not missing and m['trade_count_ok'] and m['cash_ok'] and not m['journal_flags']['init_failed'] and not m['journal_flags']['critical']
        done.write_text(json.dumps(m, indent=2))
        if not m['audited']:
            failures.append(slug); b.status(event=f'AUDIT FLAG {slug}: missing={missing[:5]} trades_ok={m["trade_count_ok"]} cash_ok={m["cash_ok"]} flags={m["journal_flags"]}')
    b.status(state='ALL DONE', event=f'All cases attempted; failures/flags: {failures}')


if __name__ == '__main__':
    cmd = sys.argv[1]
    if cmd == 'freeze':
        s = freeze()
        for r in s['rows']:
            print(f"{r['phase']:7} {r['label'][:40]:40} {r['symbol']:8} {r['period']:4} {r['mode']:8} adaptive={r['adaptive']} risk={r['inputs'].get('InpRiskPercent', r['inputs'].get('RiskPercent', '?'))}")
        print(len(s['rows']), 'cases; excluded:', list(s['excluded']))
    elif cmd == 'run':
        run()
