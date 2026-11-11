"""Owner 2026-11-10. Native MT5 Model 4, 150 ms, $10k, 1% per EA standalone, isolated research tester only (normal MT5 untouched).
  recent : the 13 pool EAs (search.py), 2026-09-01 -> 2026-11-11 exclusive (tester data ends 2026-11-10), same EX5s/inputs as their FTMO streams
           (Current 14 wrappers / Full EA presets as in Portfolio October 2026 ATR6 2026-11-03/run.py; Nasdaq 5M = deployed REPLACE, Edge 10 inputs, DI OFF;
           Vault Break / Overnight Bias ORB / Gold Band Wave = their research EX5s, tested inputs). 3 Way Gold runs all modules; only magic 930930101 is used later.
  web    : Overnight Bias ORB, Vault Break, Gold Band Wave for the website: 6m / 1y / 3y / 5y ending 2026-11-11 exclusive.
Run from AAA EAs/EA store:  uv run python "<this>" recent | web"""
import importlib.util, json, os, shutil, sys, time
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; B = H.parent
spec = importlib.util.spec_from_file_location('p7', B / 'Portfolio P7 2026-11-10/p7.py'); P7 = importlib.util.module_from_spec(spec); spec.loader.exec_module(P7)
END = '2026.11.11'
POOL = ['3-way-gold', 'ema3', 'gold-band-wave', 'nasdaq-5m-candle-momentum', 'orb-volume-profile', 'orb-volume-profile-volume-confirmed', 'overnight-bias-orb', 'sell-nasdaq-15min',
        'us100-selective-orb-v3', 'usdjpy-london-open-momentum', 'vault-break', 'xau-rsi-vwap', 'xau-squeeze-momentum-standard']
FULL = {'ORB Volume Profile': 'orb-volume-profile', 'ORB Volume Profile Volume Confirmed': 'orb-volume-profile-volume-confirmed', 'Sell Nasdaq 15min': 'sell-nasdaq-15min'}
WEB = {'overnight-bias-orb': 'ONB', 'vault-break': 'VAULT', 'gold-band-wave': 'GBW'}
WEB_PERIODS = {'6m': '2026.05.11', '1y': '2025.11.11', '3y': '2023.11.11', '5y': '2021.11.11'}


def harness():
    spec = importlib.util.spec_from_file_location('octrun', B / 'Portfolio October 2026 ATR6 2026-11-03/run.py'); o = importlib.util.module_from_spec(spec); spec.loader.exec_module(o)
    return o


def jobs(o):
    out = {}
    for k, tag, e, i in o.cases():
        if tag == 'NEW' and k in POOL:
            out[k] = (str(o.C14 / e['expert']), e['canonical'], o.TF[e['period']], {a: str(v).lower() if isinstance(v, bool) else str(v) for a, v in i.items()})
    for slug, tag, it, i in o.full_cases():
        if tag == 'FULL' and it['label'] in FULL: out[FULL[it['label']]] = (it['expert_path'], it['canonical'], o.TF[int(it['period'])], i)
    for label, (slug, _t, sym, per, src, inputs) in P7.NEW.items():   # overrides C14 Nasdaq with the deployed REPLACE build (DI OFF), as in the P7 stream
        out[slug] = (str(Path(src).with_suffix('.ex5')), sym, per, dict(inputs or P7.edge_nasdaq()))
    out = {k: v for k, v in out.items() if k in POOL}
    assert sorted(out) == sorted(POOL), sorted(set(POOL) ^ set(out))
    return out


def run(stage):
    o = harness(); b = o.b; b.ROOT = H; b.OUT = H / f'native-{stage}'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); assert not b.isolated_running(), 'Tester is occupied'
    periods = {'recent': {'r2m': '2026.09.01'}, 'web': WEB_PERIODS}[stage]
    b.CONFIG.update(periods=periods, end_date=END, deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=21600,
                    expert_dir='CalyxMerge1Step', controls={}, variants={})
    dest = b.TESTER / 'MQL5/Experts/CalyxMerge1Step'; dest.mkdir(parents=True, exist_ok=True); J = jobs(o)
    keys = POOL if stage == 'recent' else list(WEB)
    plan = []
    for key in keys:
        ex5, sym, per, inputs = J[key]; name = f'{key}.ex5'; shutil.copy2(ex5, dest / name)
        b.CONFIG['variants'][key] = {'label': key, 'inputs': {}}; b.CONFIG['common_inputs'] = inputs; b.CONFIG['expert_file'] = name; b.CONFIG['period'] = per
        for pk in periods:
            plan.append(dict(key=key, symbol=sym, period=per, window=pk, expert=ex5, ex5_sha=b.sha(Path(ex5)), inputs=inputs))
            (H / f'PLAN-{stage}.json').write_text(json.dumps(plan, indent=1), encoding='utf-8')
            if (b.OUT / f'nw-{sym}-{key}-{pk}' / 'trades.json.gz').exists(): continue
            for attempt in range(4):
                try:
                    b.run_case(sym, key, pk); break
                except SystemExit:
                    print('RETRY' if attempt < 3 else 'CASE FAILED', key, pk, flush=True); time.sleep(60)
    print('STAGE DONE', stage, flush=True)


if __name__ == '__main__':
    run(sys.argv[1])
