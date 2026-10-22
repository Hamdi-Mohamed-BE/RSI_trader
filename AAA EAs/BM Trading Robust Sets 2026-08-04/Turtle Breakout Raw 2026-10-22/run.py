"""Turtle breakout portfolio raw study. Reuses the audited No Wick Candle Raw 2026-09-25 harness unchanged (isolated
tester only, one test at a time, report-input checks, resumable), with the FIFO-fragment fix of the FTSE study.

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


def summaries(case):
    s = gzip.decompress((b.OUT / case / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    rows = {}
    for m in re.findall(r'TURTLE_SUMMARY ([^\r\n]*)', s):
        d = dict(kv.split('=') for kv in m.split()); rows[d['sym']] = d
    return rows


def set_random_probability():
    """Frequency matching only: p = signals / symbol trading days, from each frozen 5y main run."""
    raw = json.loads(CFG_PATH.read_text(encoding='utf-8')); info = {}
    for v in ('DAY', 'HOLD'):
        rows = summaries(f'nw-{SYM}-{v}-5y')
        if not rows:
            b.fail(f'{v} 5y summary missing; run main first')
        sig = sum(int(r['signals']) for r in rows.values()); days = sum(int(r['days']) for r in rows.values())
        p = round(sig / days, 5); info[v] = dict(signals=sig, symbol_days=days, p=p, per_symbol=rows)
        for k in (f'RND_{v}1', f'RND_{v}2', f'RND_{v}3'):
            if raw['controls'][k]['inputs']['InpRandomProb'] == f'SET_FROM_{v}':
                raw['controls'][k]['inputs']['InpRandomProb'] = f'{p}'
            b.CONFIG['controls'][k]['inputs']['InpRandomProb'] = raw['controls'][k]['inputs']['InpRandomProb']
    CFG_PATH.write_text(json.dumps(raw, indent=2), encoding='utf-8')
    (ROOT / 'RNG_FREQUENCY.json').write_text(json.dumps(info, indent=1), encoding='utf-8')
    return info


if __name__ == '__main__':
    stage = sys.argv[1]
    b.OUT.mkdir(parents=True, exist_ok=True)
    if b.isolated_running():
        b.fail('Isolated research terminal is already running.')
    if stage == 'compile':
        b.compile_ea(); b.install_experts()
    elif stage == 'smoke':
        b.CONFIG['periods'] = {'smoke': '2026.07.01'}
        b.run_case(SYM, 'DAY', 'smoke'); b.run_case(SYM, 'HOLD', 'smoke')
    elif stage == 'smokew':   # US-winter DAY check (session-table close fix)
        b.CONFIG['periods'] = {'smokew': '2025.11.03'}; b.CONFIG['end_date'] = '2026.01.20'
        b.run_case(SYM, 'DAY', 'smokew')
    elif stage == 'smoke23':   # 2023 summer DAY check (Friday index quotes stop at 15:58 NY)
        b.CONFIG['periods'] = {'smoke23': '2023.06.01'}; b.CONFIG['end_date'] = '2023.08.01'
        b.run_case(SYM, 'DAY', 'smoke23')
    elif stage == 'smoke22':   # 2022 summer DAY check (index quotes stop before 16:30 NY)
        b.CONFIG['periods'] = {'smoke22': '2022.06.01'}; b.CONFIG['end_date'] = '2022.09.01'
        b.run_case(SYM, 'DAY', 'smoke22')
    elif stage == 'parity':   # HOLD must be unchanged by DAY-only fixes: rerun the HOLD smoke into a separate folder
        b.OUT = ROOT / (sys.argv[2] if len(sys.argv) > 2 else 'native-parity'); b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
        b.CONFIG['periods'] = {'smoke': '2026.07.01'}
        b.run_case(SYM, 'HOLD', 'smoke')
    elif stage == 'main':
        b.main_grid()
    elif stage == 'day':
        for per in b.CONFIG['periods']:
            b.run_case(SYM, 'DAY', per)
    elif stage == 'control':
        set_random_probability()
        for v in json.loads(CFG_PATH.read_text(encoding='utf-8'))['controls']:
            b.run_case(SYM, v, '5y')
    elif stage == 'sens':
        for v in json.loads(CFG_PATH.read_text(encoding='utf-8'))['sensitivity']:
            b.run_case(SYM, v, '5y')
    b.status(event='STAGE DONE ' + stage)
