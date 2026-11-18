"""Native parity of the rebuilt Best 1-Step no-guard wrappers (Calyx No Opposite shim) vs the tested EX5s.
Each EA alone, package inputs, 1% (InpPortfolioPercent 1.0; InpRiskPercent stays 0.5), $10k, Model 4, 150 ms, 2026-08-16 -> 2026-11-16 (real ticks).
Cases per EA: OLD = tested EX5; OFF = new EX5 with InpCalyxNoOpposite=false (must be identical); ON = new EX5 with the rule (one EA alone:
identical unless the EA itself holds opposite sides). python parity.py run | report"""
import gzip, importlib.util, json, os, shutil, sys
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; L = H.parents[1]; B = L.parent; PKG = L / 'Packages/Best1Step'
START, END = '2026-08-16', '2026-11-16'
TF = {5: 'M5', 15: 'M15', 30: 'M30', 60: 'H1', 240: 'H4'}


def harness():
    spec = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def cases():
    pk = json.loads((PKG / 'Package.json').read_text(encoding='utf-8-sig'))
    for e in pk['entries']:
        new = PKG / e['expert']; inputs = dict(e['inputs'], InpPortfolioPercent='1.0')
        old = (L / 'Packages' / e['from_package'] / e['tested_expert']) if e.get('tested_expert') else None
        if e['key'] == 'uk100-monday-dip': old = None      # no earlier no-guard wrapper of this exact build in a package; the 11-11 UK wrapper parity (183/183 vs raw) stands
        yield e, old, new, inputs


def run():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'; dest = b.TESTER / 'MQL5/Experts/CalyxCNOParity'; dest.mkdir(parents=True, exist_ok=True)
    for e, old, new, inputs in cases():
        todo = [('OFF', new, dict(inputs, InpCalyxNoOpposite='false')), ('ON', new, dict(inputs, InpCalyxNoOpposite='true'))]
        if old: todo.insert(0, ('OLD', old, {k: v for k, v in inputs.items() if k != 'InpCalyxNoOpposite'}))
        for tag, ex5, inp in todo:
            name = f"{e['key']}-{tag}"; final = H / 'native' / f'nw-{name}'
            if (final / 'trades.json.gz').exists(): continue
            fn = f"{e['key']}-{tag}.ex5"; shutil.copy2(ex5, dest / fn)
            b.CONFIG.update(model=4, end_date=END.replace('-', '.'), periods={'p': START.replace('-', '.')}, deposit=10000, currency='USD', execution_delay_ms=150, profile='Calyx Research Empty',
                            timeout_seconds=7200, period=TF[int(e['period'])], expert_dir='CalyxCNOParity', expert_file=fn, controls={}, common_inputs={}, variants={name: {'label': name, 'inputs': inp}})
            b.run_case(e['canonical'], name, 'p')
            src = H / 'native' / f"nw-{e['canonical']}-{name}-p"
            if src.exists(): shutil.move(str(src), str(final))
            print('DONE', name, flush=True)
    print('RUN DONE', flush=True)


def key(t): return (t['open_time'][:19], t['side'], round(t['volume'], 4), t['close_time'][:19], round(t['net_profit'], 2))


def report():
    out = {}
    for e, old, new, inputs in cases():
        T = {}
        for tag in ('OLD', 'OFF', 'ON'):
            p = H / 'native' / f"nw-{e['key']}-{tag}" / 'trades.json.gz'
            if p.exists(): T[tag] = [key(t) for t in sorted(json.loads(gzip.open(p).read()), key=lambda t: (t['open_time'], t['close_time']))]
        r = {k: dict(trades=len(v), net=round(sum(x[4] for x in v), 2)) for k, v in T.items()}
        if 'OLD' in T: r['OFF_equals_OLD'] = T['OFF'] == T['OLD']
        r['ON_equals_OFF'] = T.get('ON') == T.get('OFF')
        out[e['key']] = r; print(e['key'], r)
    (H / 'PARITY.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    {'run': run, 'report': report}[sys.argv[1]]()
