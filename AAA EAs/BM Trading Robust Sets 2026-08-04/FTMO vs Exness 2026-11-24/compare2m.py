"""FTMO vs Exness, last 2 months (owner 2026-11-24). Best 1-Step no-guard package EX5s + inputs (InpPortfolioPercent 1.0; InpRiskPercent stays 0.5 = RiskSupport
calibration), each EA alone, $10k, Model 4 real ticks, 150 ms, 2026-09-22 -> data end 2026-11-20. Two runs per EA in the ISOLATED research terminal:
  EXNESS = the broker's own symbol (USTEC / XAUUSD / USDJPY / UK100);
  FTMO   = custom symbol <NAME>.ftmo built from FTMO-Server4 real ticks + M1 bars (export_ftmo.py, ImportFTMO.mq5; UTC clock, specs cloned from Exness).
Comparison in R (net / $100), Nasdaq 5M x0.75 as installed. Commission: none on the custom symbols (FTMO charges commission on some instruments) - see REPORT.
python compare2m.py run | report"""
import gzip, importlib.util, json, os, shutil, sys
from collections import defaultdict
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; B = H.parent; PKG = B / '_00 Live profiles/Packages/Best1Step'
START, END = '2026.09.22', '2026.11.21'
TF = {5: 'M5', 15: 'M15', 30: 'M30', 60: 'H1', 240: 'H4'}
FTMO = {'USTEC': 'US100.ftmo', 'XAUUSD': 'XAUUSD.ftmo', 'USDJPY': 'USDJPY.ftmo', 'UK100': 'UK100.ftmo'}
FACTOR = {'nasdaq-5m-candle-momentum': 0.75}


def harness():
    spec = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def entries(): return json.loads((PKG / 'Package.json').read_text(encoding='utf-8-sig'))['entries']


def run():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; dest = b.TESTER / 'MQL5/Experts/CalyxFTMOvsExness'; dest.mkdir(parents=True, exist_ok=True)
    for e in entries():
        for feed in ('EXNESS', 'FTMO'):
            sym = e['canonical'] if feed == 'EXNESS' else FTMO[e['canonical']]
            name = f"{e['key']}-{feed}"; final = H / 'native' / f'nw-{name}'
            if (final / 'trades.json.gz').exists(): continue
            fn = f"{e['key']}.ex5"; shutil.copy2(PKG / e['expert'], dest / fn)
            inp = dict(e['inputs'], InpPortfolioPercent='1.0', InpCalyxNoOpposite='false', InpCalyxNewsBlock='false')
            b.CONFIG.update(model=4, end_date=END, periods={'m': START}, deposit=10000, currency='USD', execution_delay_ms=150, profile='Calyx Research Empty',
                            timeout_seconds=7200, period=TF[int(e['period'])], expert_dir='CalyxFTMOvsExness', expert_file=fn, controls={}, common_inputs={}, variants={name: {'label': name, 'inputs': inp}})
            try: b.run_case(sym, name, 'm')
            except SystemExit as x: print('run_case exit', x)
            src = H / 'native' / f'nw-{sym}-{name}-m'
            if src.exists(): shutil.move(str(src), str(final))
            print('DONE', name, flush=True)
    print('RUN DONE', flush=True)


def report():
    out = {'per_ea': {}, 'trades': {}}; tot = defaultdict(list)
    for e in entries():
        row = {}
        for feed in ('EXNESS', 'FTMO'):
            p = H / 'native' / f"nw-{e['key']}-{feed}" / 'trades.json.gz'
            T = json.loads(gzip.open(p).read()) if p.exists() else None
            if T is None: row[feed] = None; continue
            f = FACTOR.get(e['key'], 1.0); R = [t['net_profit'] / 100 * f for t in T]; tot[feed] += R
            g = sum(x for x in R if x > 0); l = -sum(x for x in R if x < 0)
            row[feed] = dict(trades=len(T), wins=sum(x > 0 for x in R), R=round(sum(R), 2), PF=round(g / l, 2) if l else None)
            out['trades'][f"{e['key']}-{feed}"] = [(t['open_time'][:16], t['side'], round(r, 2), t.get('exit_comment', '')[:12]) for t, r in zip(T, R)]
        ex, ft = out['trades'].get(f"{e['key']}-EXNESS", []), out['trades'].get(f"{e['key']}-FTMO", [])
        exk = {(x[0][:13], x[1]) for x in ex}; ftk = {(x[0][:13], x[1]) for x in ft}
        row['same_entry_hour_and_side'] = len(exk & ftk); row['only_exness'] = len(exk - ftk); row['only_ftmo'] = len(ftk - exk)
        out['per_ea'][e['label']] = row
    for feed, R in tot.items():
        g = sum(x for x in R if x > 0); l = -sum(x for x in R if x < 0)
        out[f'TOTAL_{feed}'] = dict(trades=len(R), wins=sum(x > 0 for x in R), R=round(sum(R), 2), PF=round(g / l, 2) if l else None)
    (H / 'COMPARE_2M.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    print(json.dumps({k: v for k, v in out.items() if k != 'trades'}, indent=1))


if __name__ == '__main__':
    {'run': run, 'report': report}[sys.argv[1]]()
