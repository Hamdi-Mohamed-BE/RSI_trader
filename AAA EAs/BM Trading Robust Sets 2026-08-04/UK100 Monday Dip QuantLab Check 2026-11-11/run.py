"""UK100 Monday dip: our raw rules vs QuantLab's published rules (owner 2026-11-11: "our results seem off compared to QuantLab, investigate").
Research copy of the FTSE raw EA with three switches (defaults = raw). Native Model 4, UK100 H1, 2019-08-01 -> 2026-09-28 (QuantLab data end), 0.75%."""
import gzip, json, shutil, subprocess, sys, time
from collections import defaultdict
from pathlib import Path
H = Path(__file__).resolve().parent; B = H.parent; FT = B / 'FTSE Three Setup Raw 2026-10-27'
sys.argv = [sys.argv[0]] + (sys.argv[1:] or ['run'])
import importlib.util
spec = importlib.util.spec_from_file_location('ftse_run', FT / 'run.py'); R = importlib.util.module_from_spec(spec); spec.loader.exec_module(R); b = R.b
V = {'RAW': {}, 'MULTI': dict(InpS2OnePerDay='false'), 'EET': dict(InpS2DayClock='1'), 'SD03': dict(InpS2SdBelow='0.3'),
     'QL_ALL': dict(InpS2OnePerDay='false', InpS2DayClock='1', InpS2SdBelow='0.3')}
def run():
    src = H / 'EA/FTSE Monday QL Check EA.mq5'; log = src.with_suffix('.compile.log')
    subprocess.run(f'"{b.TESTER / "MetaEditor64.exe"}" /portable /compile:"{src}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=300)
    r = log.read_bytes(); assert '0 errors, 0 warnings' in r.decode('utf-16' if r.startswith(b'\xff\xfe') else 'utf-8-sig'), 'compile'
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running()
    dest = b.TESTER / 'MQL5/Experts/CalyxFtseQL'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(src.with_suffix('.ex5'), dest / 'ftse-ql.ex5')
    b.CONFIG.update(model=4, end_date='2026.09.28', periods={'ql': '2019.08.01'}, expert_dir='CalyxFtseQL', expert_file='ftse-ql.ex5', controls={},
                    variants={k: {'label': k, 'inputs': dict(InpSetup1='false', InpSetup2='true', InpSetup3='false', **v)} for k, v in V.items()})
    for k in V: b.run_case('UK100', k, 'ql')
def report():
    out = {}
    for k in V:
        T = sorted(json.loads(gzip.open(H / 'native' / f'nw-UK100-{k}-ql' / 'trades.json.gz').read()), key=lambda t: t['close_time']); bal = 1e4; rs = []; yrs = defaultdict(lambda: [0, 0.0])
        for t in T: r = t['net_profit'] / (0.0075 * bal); bal += t['net_profit']; rs.append(r); yrs[t['open_time'][:4]][0] += 1; yrs[t['open_time'][:4]][1] += r
        gw = sum(x for x in rs if x > 0); gl = -sum(x for x in rs if x < 0)
        out[k] = dict(trades=len(rs), days=len({t['open_time'][:10] for t in T}), win=round(100 * sum(x > 0 for x in rs) / len(rs), 1), total_r=round(sum(rs), 1),
                      per_trade=round(sum(rs) / len(rs), 3), pf=round(gw / gl, 2), years={y: (v[0], round(v[1], 1)) for y, v in sorted(yrs.items())})
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    for k, v in out.items(): print(k, v)
if __name__ == '__main__':
    run() if sys.argv[1] == 'run' else report()
