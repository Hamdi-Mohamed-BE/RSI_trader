"""Tester audit of Calyx Weekend Flat (2026-11-11). Native Model 4 in the isolated research tester, InpTestOpen=true (a 0.01 position at 11:00 New York every weekday
while flat). Checks every test position was closed by the helper before the weekend / holiday break, and reports when.
Run from AAA EAs/EA store:  uv run python "<this>" run | report"""
import gzip, importlib.util, json, os, re, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

os.environ['EA_STORE_DISABLE_MT5'] = '1'
H = Path(__file__).resolve().parent; PACKAGE = H.parents[1]
CASES = [(s, w) for s in ('USTEC', 'XAUUSD', 'USDJPY') for w in ('winter', 'summer')]
WIN = {'winter': ('2025.11.17', '2026.01.10'), 'summer': ('2026.05.18', '2026.07.11')}


def harness():
    spec = importlib.util.spec_from_file_location('baseline', PACKAGE / 'No Wick Candle Raw 2026-09-25/run_nw.py'); b = importlib.util.module_from_spec(spec); spec.loader.exec_module(b)
    b.ROOT = H; b.OUT = H / 'tester'; b.STATUS = b.OUT / 'status.json'; b.OUT.mkdir(exist_ok=True); return b


def run():
    b = harness(); assert not b.isolated_running(), 'Tester is occupied'
    import shutil
    dest = b.TESTER / 'MQL5/Experts/CalyxWeekendFlatTest'; dest.mkdir(parents=True, exist_ok=True); shutil.copy2(H / 'Calyx Weekend Flat.ex5', dest / 'cwf.ex5')
    b.CONFIG.update(deposit=10000, currency='USD', model=4, execution_delay_ms=150, profile='Calyx Research Empty', timeout_seconds=3600, period='M1',
                    expert_dir='CalyxWeekendFlatTest', expert_file='cwf.ex5', controls={}, variants={'CWF': {'label': 'CWF', 'inputs': {}}},
                    common_inputs=dict(InpEnabled='true', InpLeadMinutes='30', InpMinBreakMinutes='120', InpHolidayRules='true', InpHolidayFlatHourNY='12', InpHolidayFile='',
                                       InpIncludeManual='false', InpDeletePending='true', InpTimerSeconds='5', InpServerUtcOffsetHours='0', InpTestOpen='true'))
    for sym, w in CASES:
        if (b.OUT / f'nw-{sym}-CWF-{w}' / 'trades.json.gz').exists(): continue
        b.CONFIG['periods'] = {w: WIN[w][0]}; b.CONFIG['end_date'] = WIN[w][1]; b.run_case(sym, 'CWF', w)
    print('RUN DONE', flush=True)


def ny(utc):
    y = utc.year; on = datetime(y, 3, 8, 7, tzinfo=timezone.utc); on += timedelta(days=(6 - on.weekday()) % 7); off = datetime(y, 11, 1, 6, tzinfo=timezone.utc); off += timedelta(days=(6 - off.weekday()) % 7)
    return utc - timedelta(hours=4 if on <= utc < off else 5)


def report():
    out = {}
    for sym, w in CASES:
        d = H / 'tester' / f'nw-{sym}-CWF-{w}'
        T = json.loads(gzip.open(d / 'trades.json.gz').read()); j = gzip.open(d / 'journal.txt.gz').read().decode('utf-8', 'replace')
        closes = [l for l in j.splitlines() if 'CWF_CLOSE ' in l and 'Core' in l]
        rows = []
        for t in T:
            o = datetime.fromisoformat(t['open_time']).replace(tzinfo=timezone.utc); c = datetime.fromisoformat(t['close_time']).replace(tzinfo=timezone.utc)
            rows.append(dict(open_ny=ny(o).strftime('%a %Y-%m-%d %H:%M'), close_ny=ny(c).strftime('%a %Y-%m-%d %H:%M'), close_utc=c.strftime('%a %H:%M'), hours=round((c - o).total_seconds() / 3600, 1),
                             reason=t.get('exit_comment')))
        held_weekend = []
        for t, r in zip(T, rows):
            o = ny(datetime.fromisoformat(t['open_time']).replace(tzinfo=timezone.utc)); c = ny(datetime.fromisoformat(t['close_time']).replace(tzinfo=timezone.utc)); x = o
            while x.date() <= c.date():
                if x.weekday() == 5: held_weekend.append(r); break
                x += timedelta(days=1)
        spec = next((l for l in j.splitlines() if 'CWF_SPEC' in l and 'Core' in l), '')
        summ = next((l for l in j.splitlines() if 'CWF_SUMMARY' in l and 'Core' in l), '')
        out[f'{sym}-{w}'] = dict(trades=len(rows), helper_closes=len(closes), held_over_72h=held_weekend, spec=spec[-200:], summary=summ[-120:],
                                 close_times={r['close_ny'][:3] + ' ' + r['close_ny'][-5:] + ' NY': 0 for r in rows}, rows=rows)
        cnt = {}
        for r in rows: k = r['close_ny'][:3] + ' ' + r['close_ny'][-5:]; cnt[k] = cnt.get(k, 0) + 1
        out[f'{sym}-{w}']['close_times'] = dict(sorted(cnt.items(), key=lambda kv: -kv[1])[:12])
    (H / 'TEST_RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8')
    for k, v in out.items(): print(k, 'trades', v['trades'], 'helper closes', v['helper_closes'], 'held>72h', len(v['held_over_72h']), v['close_times'], v['summary'][-60:])


if __name__ == '__main__':
    run() if sys.argv[1:] == ['run'] else report()
