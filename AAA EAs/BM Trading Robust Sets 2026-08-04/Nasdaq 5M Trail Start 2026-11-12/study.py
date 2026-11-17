"""Owner 2026-11-12: "what if we disable 'nothing moves until +1R'". Deployed Nasdaq 5M EX5 (2488443f62a8, REPLACE), Edge 10 inputs, 1%, $10k, Model 4, 150 ms.
Only InpTrailStartR changes: TS1 = 1.0 (production), TS0 = 0.0 (ATR6 trail from entry). DI OFF and DI ON. Windows: 1y (2025-11-12 -> 2026-11-12) and all (2019-07-16 ->).
Run from AAA EAs/EA store: uv run python "<this>" run | report"""
import gzip, hashlib, importlib.util, json, os, shutil, sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; B = H.parent
spec = importlib.util.spec_from_file_location('carry', B / 'Nasdaq 5M Carry Fix 2026-11-09/carry.py'); C = importlib.util.module_from_spec(spec); spec.loader.exec_module(C)
EX5 = B / 'Nasdaq 5M Carry Replace Deployment 2026-11-09/EA/Nasdaq 5M DI Wide ATR EA.ex5'; END = '2026-11-12'
PER = {'1y': '2025-11-12', 'all': '2019-07-16'}; VAR = {'TS1': dict(InpTrailStartR='1.0'), 'TS0': dict(InpTrailStartR='0.0'),
       # QuantLab-like (inferred from their public 2026-04-07 example trade: stop = 8.0 x ATR14 at entry, stop 5.0-5.8 x ATR behind the low before 0.95R): 8 ATR stop, 5 ATR trail from entry
       'QL': dict(InpInitialStopATR='8.0', InpTrailingATR='5.0', InpTrailStartR='0.0')}


def run():
    assert hashlib.sha256(EX5.read_bytes()).hexdigest().startswith('2488443f62a8')
    b = C.harness(); b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    for per, start in PER.items():                      # owner 2026-11-12: last year first
        for di in (False, True):
            C.setup(b, di); shutil.copy2(EX5, b.TESTER / 'MQL5/Experts/CalyxCarry/deployed.ex5'); b.CONFIG['end_date'] = END.replace('-', '.'); b.CONFIG['expert_file'] = 'deployed.ex5'
            b.CONFIG['periods'] = {per: start.replace('-', '.')}
            for v, inp in VAR.items():
                key = v + ('_DION' if di else '_DIOFF')
                if (H / 'native' / f'nw-USTEC-{key}-{per}' / 'trades.json.gz').exists(): continue
                b.CONFIG['variants'] = {key: {'label': key, 'inputs': dict(inp)}}
                for attempt in range(3):
                    try: b.run_case('USTEC', key, per); break
                    except SystemExit: print('RETRY', key, per, flush=True)
                print('DONE', key, per, flush=True)
    print('RUN DONE', flush=True)


def stats(key, per):
    d = H / 'native' / f'nw-USTEC-{key}-{per}'; T = sorted(json.loads(gzip.open(d / 'trades.json.gz').read()), key=lambda t: t['close_time']); m = json.loads((d / 'run.json').read_text())['metrics']
    bal = pk = 1e4; dd = 0; R = []; days = defaultdict(float); held = []
    for t in T:
        R.append(t['net_profit'] / (0.01 * bal)); bal += t['net_profit']; pk = max(pk, bal); dd = max(dd, 1 - bal / pk); days[t['close_time'][:10]] += t['net_profit']
        held.append((datetime.fromisoformat(t['close_time'][:19]) - datetime.fromisoformat(t['open_time'][:19])).total_seconds() / 3600)
    months = (datetime.fromisoformat(END) - datetime.fromisoformat(PER[per])).days / 30.4375; w = [x for x in R if x > 0]; l = [x for x in R if x < 0]
    streak = s = 0
    for x in R: s = s + 1 if x < 0 else 0; streak = max(streak, s)
    return dict(trades=len(T), per_month=round(len(T) / months, 1), per_day=round(len(T) / months / 21, 2), ret=m['return_pct'], pf=round(sum(w) / -sum(l), 2), win=round(100 * len(w) / len(R), 1),
                avg_win_r=round(sum(w) / len(w), 2), avg_loss_r=round(sum(l) / len(l), 2), total_r=round(sum(R), 1), best_r=round(max(R), 1), closed_dd=round(100 * dd, 1), mt5_dd=m['max_drawdown_pct'],
                worst_day=round(100 * min(days.values()) / 1e4, 2), loss_streak=streak, median_hold_h=round(sorted(held)[len(held) // 2], 1))


def report():
    out = {f'{v}_{di}_{per}': stats(f'{v}_{di}', per) for di in ('DIOFF', 'DION') for per in PER for v in VAR}
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    for k, s in out.items(): print(k, s)


if __name__ == '__main__':
    {'run': run, 'report': report}[sys.argv[1]]()
