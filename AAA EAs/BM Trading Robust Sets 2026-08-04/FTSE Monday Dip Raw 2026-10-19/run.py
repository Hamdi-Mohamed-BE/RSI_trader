"""FTSE 100 Monday dip raw study. Reuses the audited No Wick Candle Raw 2026-09-25 harness unchanged
(isolated tester only, one test at a time, report-input checks, resumable).

python run.py compile | smoke | main | control | sens
"""
import gzip, importlib.util, inspect, json, os, re, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
import app.mt5_evidence_jobs as parser  # noqa: E402

# Recombine FIFO fragments by exit deal (same fix as Recent EA Shortlist 2026-09-30).
code = inspect.getsource(parser._native_trades).replace('"number": len(trades) + 1,', '"exit_deal": cells[1], "number": len(trades) + 1,')
scope = dict(vars(parser)); exec(code, scope)


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
        t['number'] = i + 1; t['result'] = 'Win' if t['net_profit'] > 0 else 'Loss' if t['net_profit'] < 0 else 'Flat'
    return out


CFG_PATH = ROOT / 'run-config.json'
b._native_trades = closing_deals
b.CONFIG = json.loads(CFG_PATH.read_text(encoding='utf-8'))
b.CONFIG['controls'] = {**b.CONFIG['controls'], **b.CONFIG['sensitivity']}   # lookup only; the stages below pick the lists
b.TESTER = PACKAGE / b.CONFIG['isolated_tester']
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
b.REPORT_DIR = b.TESTER / 'reports' / 'calyx-no-wick'
SYM, PER = 'UK100', '2020_2023'


def summary_line(case):
    s = gzip.decompress((b.OUT / case / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    m = re.findall(r'FTSE_SUMMARY ([^\r\n]*)', s)
    return dict(kv.split('=') for kv in m[-1].split()) if m else None


def set_random_probability():
    """Frequency matching only: p = R2 entries / R2 flat bars, from the frozen R2 run."""
    s = summary_line(f'nw-{SYM}-R2-{PER}')
    if not s:
        b.fail('R2 summary missing; run main first')
    p = round(int(s['r2_entries']) / int(s['r2_flat_bars']), 5)
    raw = json.loads(CFG_PATH.read_text(encoding='utf-8'))
    for k in ('RNG1', 'RNG2', 'RNG3'):
        if raw['controls'][k]['inputs']['InpRandomProb'] == 'SET_FROM_R2':
            raw['controls'][k]['inputs']['InpRandomProb'] = f'{p}'
        b.CONFIG['controls'][k]['inputs']['InpRandomProb'] = raw['controls'][k]['inputs']['InpRandomProb']
    CFG_PATH.write_text(json.dumps(raw, indent=2), encoding='utf-8')
    (ROOT / 'RNG_FREQUENCY.json').write_text(json.dumps(dict(source='R2 FTSE_SUMMARY', r2=s, p=p), indent=1), encoding='utf-8')
    return p


if __name__ == '__main__':
    stage = sys.argv[1]
    b.OUT.mkdir(parents=True, exist_ok=True)
    if b.isolated_running():
        b.fail('Isolated research terminal is already running.')
    if stage == 'compile':
        b.compile_ea(); b.install_experts()
    elif stage == 'smoke':
        b.CONFIG['periods'] = {'smoke': '2023.10.01'}
        b.run_case(SYM, 'BOTH', 'smoke')
    elif stage == 'main':
        b.main_grid()
    elif stage == 'control':
        set_random_probability()
        for v in ('C1TF', 'RNG1', 'RNG2', 'RNG3'):
            b.run_case(SYM, v, PER)
    elif stage == 'sens':
        for v in json.loads(CFG_PATH.read_text(encoding='utf-8'))['sensitivity']:
            b.run_case(SYM, v, PER)
    b.status(event='STAGE DONE ' + stage)
