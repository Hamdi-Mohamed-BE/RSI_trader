"""FTSE 100 three-setup raw study. Reuses the audited No Wick Candle Raw 2026-09-25 harness unchanged (isolated tester only,
one test at a time, report-input checks, resumable) with the FIFO-fragment fix of the 2026-10-19 FTSE study.

python run.py compile | smoke | main | control
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
b.TESTER = PACKAGE / b.CONFIG['isolated_tester']
b.ROOT = ROOT; b.OUT = ROOT / 'native'; b.STATUS = b.OUT / 'status.json'
b.REPORT_DIR = b.TESTER / 'reports' / 'calyx-no-wick'
SYM = 'UK100'


def summary_line(case):
    s = gzip.decompress((b.OUT / case / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    m = re.findall(r'FTSE3_SUMMARY ([^\r\n]*)', s)
    return {k: int(v) for k, v in (kv.split('=') for kv in m[-1].split())} if m else None


def set_random_probability():
    """Frequency matching only: p = entries / flat bars of the frozen 5y S1 and S3 runs."""
    s1, s3 = summary_line(f'nw-{SYM}-S1-5y'), summary_line(f'nw-{SYM}-S3-5y')
    if not s1 or not s3:
        b.fail('S1/S3 5y summaries missing; run main first')
    p = {'SET_FROM_S1': round(s1['s1_entries'] / s1['s1_flat_bars'], 5), 'SET_FROM_S3': round((s3['s3_long'] + s3['s3_short']) / s3['s3_flat_bars'], 5)}
    raw = json.loads(CFG_PATH.read_text(encoding='utf-8'))
    for v in raw['controls'].values():
        if v['inputs'].get('InpRandomProb') in p:
            v['inputs']['InpRandomProb'] = f"{p[v['inputs']['InpRandomProb']]}"
    CFG_PATH.write_text(json.dumps(raw, indent=2), encoding='utf-8'); b.CONFIG['controls'] = raw['controls']
    (ROOT / 'RNG_FREQUENCY.json').write_text(json.dumps(dict(source='5y FTSE3_SUMMARY', s1=s1, s3=s3, p=p), indent=1), encoding='utf-8')


if __name__ == '__main__':
    stage = sys.argv[1]
    b.OUT.mkdir(parents=True, exist_ok=True)
    if b.isolated_running():
        b.fail('Isolated research terminal is already running.')
    if stage == 'compile':
        b.compile_ea(); b.install_experts()
    elif stage == 'smoke':
        b.CONFIG['periods'] = {'smoke': '2026.10.01'}
        b.run_case(SYM, 'ALL', 'smoke')
    elif stage == 'main':
        for per in b.CONFIG['periods']:
            for v in b.CONFIG['variants']:
                b.run_case(SYM, v, per)
    elif stage == 'control':
        set_random_probability()
        for v in b.CONFIG['controls']:
            b.run_case(SYM, v, '5y')
    b.status(event='STAGE DONE ' + stage)
