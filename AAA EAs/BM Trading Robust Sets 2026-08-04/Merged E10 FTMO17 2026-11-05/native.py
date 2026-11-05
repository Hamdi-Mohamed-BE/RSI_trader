"""All the years for the merged 22 EAs (owner 2026-11-05). Native Model 4, 150 ms, $10k, each EA standalone at 1% from 2019-01-01 to 2026-11-01 exclusive
(the full tester history; ticks are generated before 2026-01-01, real after). FTMO17's 17 use the Current 14 + ORB wrapper EX5s and package inputs, the five E10-only
bots use the production EX5 with the Full EA preset, governor off, as in Portfolio October 2026 ATR6 2026-11-03/run.py. Then the buy-and-hold benchmark
(Calyx Research Pipeline/buy_hold.py) for XAUUSD, USTEC and USDJPY on the data_split windows and every calendar year.
Run from AAA EAs/EA store:  uv run python "<this>" """
import importlib.util, json, os, shutil, sys, time
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parent; PIPE = PACKAGE.parent / 'Calyx Research Pipeline'
sys.path.insert(0, str(PIPE))
import buy_hold, data_split  # noqa: E402
SPLIT = data_split.research_split('2019-01-01', '2026-11-01')
WINDOWS = {'dev': (SPLIT['development']['start'], SPLIT['development']['end_exclusive']), 'val': (SPLIT['validation']['start'], SPLIT['validation']['end_exclusive']),
           'oos': (SPLIT['oos']['start'], SPLIT['oos']['end_exclusive']), 'all': ('2019-01-01', '2026-11-01')}
YEARS = {str(y): (f'{y}-01-01', f'{y + 1}-01-01' if y < 2026 else '2026-11-01') for y in range(2019, 2027)}
EXTRA = {'orb-volume-profile-volume-confirmed': 'ORB Volume Profile Volume Confirmed', 'orb-volume-profile': 'ORB Volume Profile', 'sell-nasdaq-15min': 'Sell Nasdaq 15min',
         'xau-regime-switch': 'XAU Regime Switch', 'xau-elliott-wave-1-2-3': 'XAU Elliott Wave 1-2-3'}


def strategy_runs():
    spec = importlib.util.spec_from_file_location('octrun', PACKAGE / 'Portfolio October 2026 ATR6 2026-11-03/run.py')
    o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o); b = o.b
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True)
    b.CONFIG.update(periods={'all': '2019.01.01'}, end_date='2026.11.01', deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty',
                    timeout_seconds=21600, expert_dir='CalyxMerged22', controls={}, variants={})
    assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts/CalyxMerged22'; dest.mkdir(parents=True, exist_ok=True)
    jobs = [(k, str(o.C14 / e['expert']), e['canonical'], o.TF[e['period']], {a: str(v).lower() if isinstance(v, bool) else str(v) for a, v in i.items()}) for k, tag, e, i in o.cases() if tag == 'NEW']
    labels = {v: k for k, v in EXTRA.items()}
    jobs += [(labels[it['label']], it['expert_path'], it['canonical'], o.TF[int(it['period'])], i) for slug, tag, it, i in o.full_cases() if tag == 'FULL' and it['label'] in labels]
    assert len(jobs) == 22 and len({j[0] for j in jobs}) == 22
    plan = []
    for key, ex5, sym, per, inputs in jobs:
        name = f'{key}.ex5'; shutil.copy2(ex5, dest / name)
        b.CONFIG['variants'][key] = {'label': key, 'inputs': {}}; b.CONFIG['common_inputs'] = inputs; b.CONFIG['expert_file'] = name; b.CONFIG['period'] = per
        plan.append(dict(key=key, symbol=sym, period=per, expert=ex5, ex5_sha=b.sha(Path(ex5)), case=f'nw-{sym}-{key}-all'))
        (H / 'NATIVE_PLAN.json').write_text(json.dumps(dict(split=SPLIT, windows=WINDOWS, years=YEARS, runs=plan), indent=1), encoding='utf-8')
        for attempt in range(4):                         # the tester agent can time out at startup when the CPU is busy
            try:
                b.run_case(sym, key, 'all'); break
            except SystemExit:
                print('RETRY' if attempt < 3 else 'CASE FAILED', key, flush=True); time.sleep(60)
    print('EAS DONE', flush=True)


def benchmarks():
    for sym in ('XAUUSD', 'USTEC', 'USDJPY'):
        res = buy_hold.run(H, sym, {**WINDOWS, **YEARS})
        print('BUYHOLD', sym, {k: (v['return_pct'], v['max_dd_pct']) for k, v in res.items()}, flush=True)
    print('BENCHMARKS DONE', flush=True)


if __name__ == '__main__':
    what = sys.argv[1] if len(sys.argv) > 1 else 'both'
    if what in ('hold', 'both'): benchmarks()
    if what in ('eas', 'both'): strategy_runs()
    print('ALL DONE', flush=True)
