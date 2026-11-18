"""Native tester check of the no-opposite rule (CNO Test.mq5), rule ON and OFF, USTEC M1, 2026-10-06 -> 2026-10-08 (real ticks), isolated tester.
python run_test.py  -> test/RESULTS.json (every CNO_TEST line + pass/fail)"""
import gzip, importlib.util, json, os, re, shutil, subprocess, sys, time
os.environ["EA_STORE_DISABLE_MT5"] = "1"
from pathlib import Path

H = Path(__file__).resolve().parent; L = H.parents[1]; B = L.parent
EDITOR = B / '_Backtests/MT5-DMC-20260811/MetaEditor64.exe'


def harness():
    spec = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def compile_test():
    src = H / 'CNO Test.mq5'; log = src.with_suffix('.compile.log'); started = time.time()
    subprocess.run(f'"{EDITOR}" /portable /compile:"{src}" /log:"{log}"', creationflags=subprocess.CREATE_NO_WINDOW, timeout=120)
    text = log.read_bytes().decode('utf-16', errors='replace') if log.read_bytes()[:2] == b'\xff\xfe' else log.read_text(errors='replace')
    assert '0 errors, 0 warnings' in text, text[-3000:]
    assert src.with_suffix('.ex5').stat().st_mtime >= started - 2; print('compiled', flush=True)


def main():
    compile_test(); b = harness(); assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts/CalyxCNOTest'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(H / 'CNO Test.ex5', dest / 'CNO Test.ex5')
    out = {}
    for name, on in (('ON', 'true'), ('OFF', 'false')):
        b.CONFIG.update(model=4, end_date='2026.10.08', periods={'t': '2026.10.06'}, deposit=100000, currency='USD', execution_delay_ms=150, profile='Calyx Research Empty',
                        timeout_seconds=1800, period='M1', expert_dir='CalyxCNOTest', expert_file='CNO Test.ex5', controls={}, common_inputs={},
                        variants={name: {'label': name, 'inputs': {'InpCalyxNoOpposite': on}}})
        try:
            b.run_case('USTEC', name, 't')
        except SystemExit as e:
            print('run_case exit', e, flush=True)
        d = H / 'native' / f'nw-USTEC-{name}-t'; j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', errors='replace')
        lines = re.findall(r'CNO_TEST [^\r\n]*', j); cno = re.findall(r'Calyx no-opposite: [^\r\n]*', j)
        out[name] = dict(lines=lines, rule_messages=cno[:20], fails=sum('FAIL' in x for x in lines), passes=sum('PASS' in x for x in lines), done=any('DONE' in x for x in lines))
        print(name, out[name]['passes'], 'pass', out[name]['fails'], 'fail', 'done' if out[name]['done'] else 'NOT DONE', flush=True)
        for x in lines: print('   ', x)
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')


if __name__ == '__main__':
    main()
