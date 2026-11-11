"""Parity: Best 1-Step no-guard UK100 Monday wrapper (Packages/Best1Step) vs the raw FTSE EA (RAW-ql run), native Model 4, UK100 H1, 2019-08-01 -> 2026-09-28.
Same entries / exits (time, side, prices) required; lots differ only by the sizing source."""
import gzip, json, shutil, sys
from pathlib import Path
import importlib.util
H = Path(__file__).resolve().parent; B = H.parent; FT = B / 'FTSE Three Setup Raw 2026-10-27'; PKG = B / '_00 Live profiles/Packages/Best1Step'
sys.argv = [sys.argv[0], 'noop']
spec = importlib.util.spec_from_file_location('ftse_run', FT / 'run.py'); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R); b = R.b
b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; assert not b.isolated_running()
dest = b.TESTER / 'MQL5/Experts/CalyxFtseQL'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(PKG / 'Experts/Calyx Best1Step - uk100-monday-dip.ex5', dest / 'b1-uk100.ex5')
pk = json.loads((PKG / 'Package.json').read_text(encoding='utf-8')); e = next(x for x in pk['entries'] if x['key'] == 'uk100-monday-dip')
inputs = dict(e['inputs'], InpPortfolioPercent='0.75')
b.CONFIG.update(model=4, end_date='2026.09.28', periods={'ql': '2019.08.01'}, expert_dir='CalyxFtseQL', expert_file='b1-uk100.ex5', controls={}, common_inputs={},
                variants={'B1WRAP': {'label': 'Best 1-Step no-guard wrapper', 'inputs': inputs}})
b.run_case('UK100', 'B1WRAP', 'ql')
key = lambda t: (t['open_time'], t['close_time'], t['side'], round(t['open_price'], 2), round(t['close_price'], 2))  # noqa: E731
a = [key(t) for t in json.loads(gzip.open(H / 'native/nw-UK100-RAW-ql/trades.json.gz').read())]
w = [key(t) for t in json.loads(gzip.open(H / 'native/nw-UK100-B1WRAP-ql/trades.json.gz').read())]
res = dict(raw=len(a), wrapper=len(w), identical=a == w, only_raw=[x for x in a if x not in w][:5], only_wrapper=[x for x in w if x not in a][:5])
(H / 'PARITY_B1.json').write_text(json.dumps(res, indent=1), encoding='utf-8'); print(res)
