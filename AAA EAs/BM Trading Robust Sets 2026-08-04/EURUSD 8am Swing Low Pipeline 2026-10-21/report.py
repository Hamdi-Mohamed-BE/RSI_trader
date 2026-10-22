"""Summarise the EURUSD 8am swing-low pipeline (tables) and run the labelled post-rejection DIAGNOSTIC of the six rejected
finalists on validation + OOS (Model 4). The diagnostic changes no decision: both tracks were already REJECTED_AT_PLATEAU.

python report.py
"""
import json, statistics
from collections import defaultdict
from pathlib import Path
import pipeline as pl, runner as rn

R = Path(__file__).resolve().parent
NAMES = dict(tf={15: 'M15', 30: 'M30', 60: 'H1'}, entry={0: 'market', 1: 'limit', 2: 'stop-entry'}, dir={0: 'long after low', 1: 'short after high', 2: 'both'},
             trend={0: 'none', 1: 'H1 EMA200 side', 2: 'EMA50 slope', 3: 'D1 EMA20 side'}, atr_regime={0: 'any', 1: 'ATR above median', 2: 'ATR below median'},
             dow={0: 'all days', 1: 'skip Mon', 2: 'skip Fri', 3: 'skip Mon+Fri'})


def describe(c):
    clock = 'London' if c['clock'] == 0 else 'New York'
    entry = NAMES['entry'][c['entry']] + (f" {c['entry_k']:g} ATR" if c['entry'] == 1 else '')
    stop = f"pivot - {c['stop_val']:g} ATR (min {c['min_stop']:g})" if c['stop_type'] == 0 else f"{c['stop_val']:g} ATR"
    exit_ = (f"TP {c['tp_r']:g}R " if c['tp_r'] else '') + (f"{c['hold_h']:g} h" if c['hold_h'] else '') + (' session end' if c['exit_mode'] == 1 else '')
    mg = (f"BE {c['be_r']:g}R" if c['be_r'] else '') + (f" trail {c['trail_atr']:g} ATR from {c['trail_start_r']:g}R" if c['trail_atr'] else '') or 'none'
    flt = ', '.join(x for x in [NAMES['trend'][c['trend']] if c['trend'] else '', f"ADX>={c['adx_min']:g}" if c['adx_min'] else '',
                                NAMES['atr_regime'][c['atr_regime']] if c['atr_regime'] else '', NAMES['dow'][c['dow']] if c['dow'] else ''] if x) or 'none'
    return (f"{clock} {c['hour']:02d}:{c['minute']:02d} | {NAMES['tf'][c['tf']]} fractal {c['n']} window {c['w']}{' lower-low' if c['ll'] else ''} | "
            f"{NAMES['dir'][c['dir']]} | {entry} | stop {stop} | mgmt {mg} | exit {exit_.strip()} | filters {flt}")


def mrow(m):
    return (f"{m['trades']} | {m['per_month']} | {m['per_day']} | {m['return_pct']:+.1f}% | {m['pf'] and round(m['pf'], 2)} | {m['win_rate_pct']:.1f}% | "
            f"{m['closed_dd']}% | {m['equity_dd']:.1f}% | {m['max_win_streak']}/{m['max_loss_streak']}")


def main():
    allr = pl.read(R / 'SEARCH RESULTS.json'); lines = ['# EURUSD 8am swing low pipeline — tables (generated)', '']
    lines += [f"Configurations tested (all stages, both tracks, incl. plateau grids): **{len(allr)}**; parity: {json.dumps(pl.read(R / 'PARITY.json'))}", '']
    HDR = '| Trades | / month | / day | Return | PF | Win % | Closed DD | Equity DD | Max win / loss streak |'
    finals = {}
    for track in ('london', 'newyork'):
        trail = pl.read(R / f'SEARCH-{track}.json'); lines += [f'## {track} — staged search on development 2016-10-17 → 2023-10-17 (Model 1)', '']
        lines += ['| Stage | Tested | Best carried configuration | ' + HDR[2:], '|---|---|---|---|---|---|---|---|---|---|---|---|']
        for s in trail:
            t = s['top'][0]; lines.append(f"| {s['stage']} | {s['tested']} | {describe(t['parameters'])} | {mrow(t['metrics'])} |")
        lines.append('')
        # side-by-side per dimension: best result per option in its stage
        rec = defaultdict(list)
        for x in allr:
            if x['track'] == track: rec[x['stage']].append(x)
        dims = [('swing', 'tf'), ('swing', 'n'), ('swing', 'w'), ('swing', 'll'), ('entry', 'entry'), ('stop', 'stop_type'), ('mgmt', 'be_r'), ('mgmt', 'trail_atr'),
                ('exit', 'tp_r'), ('exit', 'hold_h'), ('anchor', 'hour'), ('direction', 'dir'), ('filters', 'trend'), ('filters', 'adx_min'), ('filters', 'atr_regime'), ('filters', 'dow')]
        lines += [f'### {track} — best development result per option (side by side)', '', '| Dimension | Option | Best PF | Trades | Return | Configs |', '|---|---|---|---|---|---|']
        for st, key in dims:
            groups = defaultdict(list)
            for x in rec[st]: groups[x['parameters'][key]].append(x)
            for opt, xs in sorted(groups.items()):
                b = max(xs, key=lambda x: (x['metrics']['pf'] or 0) if x['metrics']['trades'] >= 60 else -1)
                lab = NAMES.get(key, {}).get(int(opt), opt) if key in NAMES else opt
                lines.append(f"| {st}: {key} | {lab} | {b['metrics']['pf'] and round(b['metrics']['pf'], 2)} | {b['metrics']['trades']} | {b['metrics']['return_pct']:+.1f}% | {len(xs)} |")
        lines.append('')
        plat = pl.read(R / f'PLATEAU-{track}.json'); finals[track] = [p['parameters'] for p in plat]
        lines += [f'### {track} — plateau (joint ±1 step grid: freshness window × exit × anchor ±30 min, development)', '',
                  '| Finalist | Configuration | Dev PF / trades / return | Neighbours | Profitable neighbours | Median neighbour PF | Plateau |', '|---|---|---|---|---|---|---|']
        for p in plat:
            d = p['dev']; lines.append(f"| {p['final'] + 1} | {describe(p['parameters'])} | {d['pf']:.2f} / {d['trades']} / {d['return_pct']:+.1f}% | {p['neighbours']} | "
                                       f"{100 * p['positive_share']:.0f}% | {p['median_pf']:.2f} | {'PASS' if p['passed'] else '**FAIL**'} |")
        lines.append('')
    # diagnostic: rejected finalists on validation + OOS (Model 4)
    cases = finals['london'] + finals['newyork']; diag = {}
    with rn.lease():
        val = rn.batch('diagnostic-finalists-val-m4', cases, *pl.VAL, model=4); oos = rn.batch('diagnostic-finalists-oos-m4', cases, *pl.OOS, model=4)
    lines += ['## POST-REJECTION DIAGNOSTIC (not a selection): the six rejected finalists, Model 4', '',
              '| Track / finalist | Window | ' + HDR[2:], '|---|---|---|---|---|---|---|---|---|---|---|']
    for i, c in enumerate(cases):
        tr = 'London' if c['clock'] == 0 else 'New York'; k = i % 3 + 1
        for wname, recs in (('Validation 2023-24', val), ('OOS 2024-26', oos)):
            lines.append(f"| {tr} {k} | {wname} | {mrow(recs[i]['metrics'])} |"); diag[f'{tr} {k} {wname}'] = recs[i]['metrics']
    rn.save(R / 'DIAGNOSTIC.json', diag)
    (R / 'TABLES.md').write_text('\n'.join(lines) + '\n', encoding='utf-8'); print('\n'.join(lines))


if __name__ == '__main__':
    main()
