"""BTC time-series momentum + vol targeting raw study. Reuses the audited No Wick Candle Raw 2026-09-25 harness unchanged (isolated
tester only, one test at a time, report-input checks, resumable), with the FIFO-fragment fix of the FTSE study.

python run.py compile | smoke | main | screen
"""
import gzip, importlib.util, inspect, json, os, re, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
ROOT = Path(__file__).resolve().parent
PACKAGE = ROOT.parent
spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py')
b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
import app.mt5_evidence_jobs as parser  # noqa: E402

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
SYM = 'BTCUSD'


def summary_line(case):
    s = gzip.decompress((b.OUT / case / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    m = re.findall(r'TSM_SUMMARY ([^\r\n]*)', s)
    return dict(kv.split('=') for kv in m[-1].split()) if m else None


def set_random_probability():
    """Frequency matching only: p = LF flips / days, from the frozen 5y LF run."""
    raw = json.loads(CFG_PATH.read_text(encoding='utf-8'))
    s = summary_line(f'nw-{SYM}-LF-5y')
    if not s:
        b.fail('LF 5y summary missing; run main first')
    p = round(int(s['flips']) / int(s['days']), 5)
    for k in ('RND1', 'RND2', 'RND3'):
        if raw['controls'][k]['inputs']['InpFlipProb'] == 'SET_FROM_LF':
            raw['controls'][k]['inputs']['InpFlipProb'] = f'{p}'
        b.CONFIG['controls'][k]['inputs']['InpFlipProb'] = raw['controls'][k]['inputs']['InpFlipProb']
    CFG_PATH.write_text(json.dumps(raw, indent=2), encoding='utf-8')
    (ROOT / 'RNG_FREQUENCY.json').write_text(json.dumps(dict(source='LF 5y TSM_SUMMARY', summary=s, p=p), indent=1), encoding='utf-8')
    return p


if __name__ == '__main__':
    stage = sys.argv[1]
    b.OUT.mkdir(parents=True, exist_ok=True)
    if b.isolated_running():
        b.fail('Isolated research terminal is already running.')
    if stage == 'compile':
        b.compile_ea(); b.install_experts()
    elif stage == 'smoke':
        b.CONFIG['periods'] = {'smoke': '2026.09.01'}
        b.run_case(SYM, 'LF', 'smoke')
    elif stage == 'main':          # gate / confirmation: Model 4, separate windows
        for v in ('LF', 'LS'):
            for per in ('6m', '1y', '3y', '5y'):
                b.run_case(SYM, v, per)
    elif stage == 'screen':        # like-for-like comparison screen: Model 1, 5y
        set_random_probability(); b.CONFIG['model'] = 1
        raw = json.loads(CFG_PATH.read_text(encoding='utf-8'))
        for v in ['LF', 'LS', 'BH', 'VTL', *raw['controls'], *raw['sensitivity']]:
            b.run_case(SYM, v, '5y_m1')
    b.status(event='STAGE DONE ' + stage)
