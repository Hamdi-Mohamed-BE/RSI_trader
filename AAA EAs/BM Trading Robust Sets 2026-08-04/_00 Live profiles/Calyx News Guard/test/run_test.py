"""Native tester audit of Calyx News Guard: XAUUSD M5, 2026-11-10 -> 2026-11-12, two USD test events (2026.11.10 15:30 and 2026.11.11 19:00 server = UTC),
window -5/+5 min, close lead 90 s, InpTestOpen=true (a 0.01 test buy every 15 min while flat and not blocked). Checks: every test position open at
(event - 5 min - 90 s) is closed before the window starts, no test position opens between the lead start and the window end, opens resume after it.
python run_test.py -> test/RESULTS.json"""
import gzip, importlib.util, json, os, re, shutil, subprocess, time
from datetime import datetime, timedelta
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; G = H.parent; L = G.parent; B = L.parent
EVENTS = ['2026.11.10 15:30', '2026.11.11 19:00']; BEFORE, AFTER, LEAD = 5, 5, 90


def harness():
    spec = importlib.util.spec_from_file_location('baseline', B / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'native'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def main():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'
    dest = b.TESTER / 'MQL5/Experts/CalyxNewsGuardTest'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(G / 'Calyx News Guard.ex5', dest / 'news-guard.ex5')
    b.CONFIG.update(model=4, end_date='2026.11.12', periods={'t': '2026.11.10'}, deposit=10000, currency='USD', execution_delay_ms=150, profile='Calyx Research Empty',
                    timeout_seconds=1800, period='M5', expert_dir='CalyxNewsGuardTest', expert_file='news-guard.ex5', controls={}, common_inputs={},
                    variants={'NG': {'label': 'NG', 'inputs': dict(InpTestEvents=';'.join(e + '|USD' for e in EVENTS), InpTestOpen='true', InpBeforeMinutes=str(BEFORE),
                                                                  InpAfterMinutes=str(AFTER), InpCloseLeadSeconds=str(LEAD), InpTimerSeconds='2')}})
    try: b.run_case('XAUUSD', 'NG', 't')
    except SystemExit as e: print('run_case exit', e)
    d = H / 'native' / 'nw-XAUUSD-NG-t'; j = gzip.decompress((d / 'journal.txt.gz').read_bytes()).decode('utf-8', 'replace')
    T = json.loads(gzip.open(d / 'trades.json.gz').read())
    checks = []
    for e in EVENTS:
        ev = datetime.strptime(e, '%Y.%m.%d %H:%M'); lead = ev - timedelta(minutes=BEFORE, seconds=LEAD); ws = ev - timedelta(minutes=BEFORE); we = ev + timedelta(minutes=AFTER)
        held = [t for t in T if datetime.fromisoformat(t['open_time'][:19]) < lead and datetime.fromisoformat(t['close_time'][:19]) >= lead]
        closed_ok = all(lead <= datetime.fromisoformat(t['close_time'][:19]) < ws for t in held)
        opened_inside = [t for t in T if lead <= datetime.fromisoformat(t['open_time'][:19]) < we]
        resumed = any(we <= datetime.fromisoformat(t['open_time'][:19]) < we + timedelta(minutes=30) for t in T)
        checks.append(dict(event=e, positions_held_into_lead=len(held), closed_before_window=closed_ok, close_times=[t['close_time'][:19] for t in held],
                           opens_inside_block=len(opened_inside), opens_resume_within_30min=resumed))
    summ = re.findall(r'CALYX_NEWS_GUARD_SUMMARY[^\r\n]*', j)
    out = dict(checks=checks, summary=summ[:1], trades=len(T), passed=all(c['positions_held_into_lead'] >= 1 and c['closed_before_window'] and c['opens_inside_block'] == 0 and c['opens_resume_within_30min'] for c in checks))
    (H / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
