"""USDJPY NY open exit — native runs + comparison tables (PLAN.md). Isolated tester only.

python run.py native | table
"""
import copy, importlib.util, json, msvcrt, statistics, sys
from datetime import date, datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

R = Path(__file__).resolve().parent; B = R.parent; NRR = B / 'Negative RR Study 2026-10-21'
SLUG = 'usdjpy-london-open-momentum'
VARIANTS = {'ny0800': ('NY FX open 08:00 NY (13:00 London)', '13.0'), 'ny0930': ('NY equity open 09:30 NY (14:30 London)', '14.5')}


def read(p): return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def load(name, path):
    s = importlib.util.spec_from_file_location(name, path); m = importlib.util.module_from_spec(s); s.loader.exec_module(m); return m


def native():
    rn = load('rn', NRR / 'run_native.py'); rn.R = R
    row, _ = rn.base_rows()[SLUG]; status = read(R / 'RUN_STATUS.json') if (R / 'RUN_STATUS.json').exists() else {}
    for key, (label, hour) in VARIANTS.items():
        if key in status: continue
        r = copy.deepcopy(row); ov = {'InpExitLondonHour': hour}; r['input_settings'].update(ov); r['candidate_overrides'] = ov; r['case_id'] = f'{SLUG}-{key}'
        res = rn.run_one(r, key, 'half'); p = R / key / 'native' / res['tag'] / 'results.json'
        assert float(res['inputs']['InpExitLondonHour']) == float(hour)
        status[key] = dict(path=str(p), sha256=rn.sha(p), trades=len(res['trades']), seconds=round(res['seconds']), overrides=ov)
        (R / 'RUN_STATUS.json').write_text(json.dumps(status, indent=1), encoding='utf-8'); print('DONE', key, status[key], flush=True)


def gap_week(epoch):
    t = datetime.fromtimestamp(epoch, timezone.utc)
    return (t.astimezone(ZoneInfo('Europe/London')).utcoffset() - t.astimezone(ZoneInfo('America/New_York')).utcoffset()).total_seconds() != 5 * 3600


def table():
    sa = load('sa', NRR / 'standalone.py'); status = read(R / 'RUN_STATUS.json')
    runs = {'current': ('Current: 16:00 London (11:00 NY)', read(read(NRR / 'RUN_STATUS.json')['complete'][f'base|{SLUG}']['path']))}
    for key, (label, _) in VARIANTS.items(): runs[key] = (label, read(status[key]['path']))
    out = {}; lines = ['# USDJPY London Open — exit at New York open vs current (generated)', '',
                       'Native MT5 Model 4, 150 ms, $10k, 1% risk, 2021-10-06 -> 2026-10-06. Windows by trade open date.', '']
    for w, (a, b) in sa.WINDOWS.items():
        lines += [f'## {w}', '', '| Exit | Trades | / month | / day | Win rate | PF | Avg R | Return | Closed DD | Avg hold (h) | Stop exits | Time/other exits |' + (' 5y native equity DD |' if w == '5 years' else ''),
                  '|---|---|---|---|---|---|---|---|---|---|---|---|' + ('---|' if w == '5 years' else '')]
        for key, (label, res) in runs.items():
            s = sa.stats(res, 'USDJPY', a, b)
            ts = [t for t in res['trades'] if sa.ep(date.fromisoformat(a)) <= t['open_epoch'] < sa.ep(date.fromisoformat(b))]
            hold = round(statistics.fmean((t['close_epoch'] - t['open_epoch']) / 3600 for t in ts), 2) if ts else None
            s['avg_hold_h'] = hold; out.setdefault(w, {})[key] = s
            lines.append(f"| {label} | {s['trades']} | {s['per_month']} | {s['per_day']} | {s['win_rate']}% | {s['pf']} | {s['avg_r']} | {s['ret']}% | {s['closed_dd']}% | {hold} | {s['sl']}% | {100 - s['sl'] - s['tp']}% |"
                         + (f" {res['metrics']['equity_dd_pct']}% |" if w == '5 years' else ''))
        lines.append('')
    gaps = {k: sum(gap_week(t['open_epoch']) for t in res['trades']) for k, (_, res) in runs.items()}
    lines += [f"US/UK DST-gap trades (London exit lands 1 h after the NY open): {gaps['ny0800']} of {len(runs['ny0800'][1]['trades'])} (NY 08:00), "
              f"{gaps['ny0930']} of {len(runs['ny0930'][1]['trades'])} (NY 09:30).", '']
    out['dst_gap_trades'] = gaps
    (R / 'RESULTS.json').write_text(json.dumps(out, indent=1), encoding='utf-8'); (R / 'RESULTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8'); print('\n'.join(lines))


if __name__ == '__main__':
    if sys.argv[1] == 'native':
        with (B / 'LTA VWAP Developing POC Comparison 2026-10-05' / 'tester.lock').open('a+b') as lock:
            lock.seek(0); msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1); native()
    else: table()
