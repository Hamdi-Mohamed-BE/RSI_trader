"""TrendSpider "QLD Claude AI Scalper" raw study (RULES.md). Reuses the audited No Wick Candle Raw 2026-09-25 harness
(isolated tester only, one test at a time, report-input checks, resumable) with the FIFO-fragment fix.
Run from AAA EAs/EA store:  uv run python "<study>/run.py" compile | smoke | main | control | sens
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
SESSION = {'USTEC': '1', 'US30': '1', 'US500': '1', 'XAUUSD': '0'}      # indices: NY regular session; gold: every bar


def summary(case):
    s = gzip.decompress((b.OUT / case / 'journal.txt.gz').read_bytes()).decode('utf-8', 'ignore')
    m = re.findall(r'TSBV_SUMMARY ([^\r\n]*)', s)
    return dict(kv.split('=') for kv in m[-1].split()) if m else None


def run(sym, variant, period='full'):
    """Per-symbol session mode (flipped for S_SESS); the random probability comes from that symbol's MAIN frequency."""
    raw = json.loads(CFG_PATH.read_text(encoding='utf-8'))['variants'][variant]
    inputs = dict(raw['inputs'])
    inputs['InpSessionMode'] = ('0' if SESSION[sym] == '1' else '1') if variant == 'S_SESS' else SESSION[sym]
    if inputs.get('InpRandomProb') == 'SET_FROM_MAIN':
        s = summary(f'nw-{sym}-MAIN-full')
        if not s: b.fail(f'MAIN summary missing for {sym}; run main first')
        inputs['InpRandomProb'] = f"{int(s['signals']) / max(int(s['flatbars']), 1):.6f}"
        freq = json.loads((ROOT / 'RNG_FREQUENCY.json').read_text()) if (ROOT / 'RNG_FREQUENCY.json').exists() else {}
        freq[sym] = dict(signals=int(s['signals']), flat_session_bars=int(s['flatbars']), p=float(inputs['InpRandomProb']))
        (ROOT / 'RNG_FREQUENCY.json').write_text(json.dumps(freq, indent=1))
    b.CONFIG['variants'][variant] = {'label': raw['label'], 'inputs': inputs}
    return b.run_case(sym, variant, period)


if __name__ == '__main__':
    stage = sys.argv[1]
    b.OUT.mkdir(parents=True, exist_ok=True)
    if b.isolated_running():
        b.fail('Isolated research terminal is already running.')
    if stage == 'compile':
        b.compile_ea(); b.install_experts()
    elif stage == 'smoke':
        run('USTEC', 'MAIN', 'smoke'); run('XAUUSD', 'MAIN', 'smoke')
    elif stage == 'main':
        for s in b.CONFIG['symbols']: run(s, 'MAIN')
    elif stage == 'control':
        for v in ('RND1', 'RND2', 'RND3'):
            for s in b.CONFIG['symbols']: run(s, v)
    elif stage == 'sens':
        for v in ('S_SESS', 'S_NOVOL', 'S_2X'):
            for s in b.CONFIG['symbols']: run(s, v)
    b.status(event='STAGE DONE ' + stage)
