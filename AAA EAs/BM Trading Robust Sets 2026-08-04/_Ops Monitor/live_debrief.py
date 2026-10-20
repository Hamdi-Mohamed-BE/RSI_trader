"""Item 2b: weekly live debrief — demo account vs the same week's native backtest, per EA, plus kill-switch status.

Judges EXECUTION against the backtest of the same frozen EX5/SET, never the result. Read-only inputs:
  output/live/latest.json (fetch_live.py), output/debrief/<start>_<end>/ (debrief_backtest.py), output/KILL_SWITCHES.json,
  optional output/event_sheet/latest.json (event_sheet.py) for news-entry timing.

uv run python ".../_Ops Monitor/live_debrief.py" --start 2026-10-12 --end 2026-10-19 --risk-pct 1.0
"""
import argparse, gzip, json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from common import OUT, magic_map, now_utc, products, roster, save
from robustness import longest_losing_streak, max_drawdown

DEAL_REASON = {0: 'client', 1: 'mobile', 2: 'web', 3: 'expert', 4: 'sl', 5: 'tp', 6: 'stop_out', 7: 'rollover', 8: 'vmargin', 9: 'split'}
TF_MIN = {'M1': 1, 'M5': 5, 'M15': 15, 'M30': 30, 'H1': 60, 'H4': 240, 'D1': 1440}
NEWS = {'news-pulse-xau', 'news-pulse-xag', 'news-pulse-btc', 'news-pulse-eurusd', 'gold-news-v9-direction'}
CLIENT = {93095001 + i: f'client-top5-{i + 1}' for i in range(5)}


def ts(epoch):
    return datetime.fromtimestamp(epoch, timezone.utc)


def parse(s):
    return datetime.fromisoformat(str(s).replace('.', '-').replace(' ', 'T')[:19]).replace(tzinfo=timezone.utc)


def live_positions(snap, mm):
    deals = sorted(snap['deals'], key=lambda d: (d['time_msc'], d['ticket']))
    balance, bal_before = 0.0, {}
    groups = defaultdict(list)
    for d in deals:
        if d['type'] in (0, 1) and d['position_id']:
            if d['entry'] == 0 and d['position_id'] not in bal_before:
                bal_before[d['position_id']] = balance
            groups[d['position_id']].append(d)
        balance += d['profit'] + d['commission'] + d['swap'] + d.get('fee', 0)
    out = []
    for pid, rows in groups.items():
        ins = [r for r in rows if r['entry'] in (0, 2)]; outs = [r for r in rows if r['entry'] in (1, 2, 3)]
        if not ins:
            continue
        magic = next((r['magic'] for r in ins if r['magic']), ins[0]['magic'])
        slug = mm.get(magic) or CLIENT.get(magic) or (f'manual' if magic == 0 else f'magic-{magic}')
        out.append(dict(position_id=pid, magic=magic, slug=slug, symbol=ins[0]['symbol'], side='Long' if ins[0]['type'] == 0 else 'Short',
                        open=ts(ins[0]['time_msc'] / 1000), close=ts(outs[-1]['time_msc'] / 1000) if outs else None,
                        closed=bool(outs) and sum(r['volume'] for r in outs) >= sum(r['volume'] for r in ins) - 1e-9,
                        exit_kind=DEAL_REASON.get(outs[-1]['reason'], str(outs[-1]['reason'])) if outs else 'open',
                        net=round(sum(r['profit'] + r['commission'] + r['swap'] + r.get('fee', 0) for r in rows), 2),
                        balance_before=round(bal_before.get(pid, 0.0), 2), entry_comment=ins[0]['comment']))
    return out


def backtest_trades(folder: Path):
    sel = json.loads((folder / 'selection.json').read_text())
    res = {}
    for row in sel['rows']:
        run = folder / 'native' / f"nw-{row['symbol']}-{row['slug']}-wk"
        meta = json.loads((run / 'run.json').read_text()) if (run / 'run.json').exists() else None
        tr = json.loads(gzip.decompress((run / 'trades.json.gz').read_bytes())) if (run / 'trades.json.gz').exists() else None
        kind = lambda c: 'sl' if str(c).lower().startswith('sl') else 'tp' if str(c).lower().startswith('tp') else 'expert'  # noqa: E731
        res[row['slug']] = dict(row=row, meta=meta, trades=None if tr is None else [
            dict(side=t['side'], open=parse(t['open_time']), close=parse(t['close_time']), exit_kind=kind(t.get('exit_comment')), net=t['net_profit'])
            for t in tr])
    return res


def match(bt, lv, tf_min):
    tol = max(5, min(60, tf_min)) * 60
    used, pairs, missed = set(), [], []
    for t in sorted(bt, key=lambda x: x['open']):
        best = None
        for i, l in enumerate(lv):
            if i in used or l['side'] != t['side']:
                continue
            d = abs((l['open'] - t['open']).total_seconds())
            if d <= tol and (best is None or d < best[1]):
                best = (i, d)
        if best is None:
            missed.append(t); continue
        used.add(best[0]); l = lv[best[0]]
        close_d = abs((l['close'] - t['close']).total_seconds()) if l['close'] else None
        status = 'MATCH'
        if best[1] > 120:
            status = 'TIMING'
        elif l['close'] is None or not l['closed']:
            status = 'OPEN_ON_DEMO'
        elif l['exit_kind'] != t['exit_kind'] or close_d > tol:
            status = 'EXIT_DIFF'
        pairs.append(dict(status=status, open_offset_s=round((l['open'] - t['open']).total_seconds()), close_offset_s=None if close_d is None else round(close_d),
                          bt_exit=t['exit_kind'], live_exit=l['exit_kind'], bt_sign=(t['net'] > 0) - (t['net'] < 0), live_sign=(l['net'] > 0) - (l['net'] < 0),
                          live_open=l['open'].isoformat(), position_id=l['position_id']))
    extra = [l for i, l in enumerate(lv) if i not in used]
    return pairs, missed, extra


def main():
    ap = argparse.ArgumentParser(); ap.add_argument('--start', required=True); ap.add_argument('--end', required=True)
    ap.add_argument('--risk-pct', type=float, default=1.0, help='assumed live risk per trade for R conversion')
    a = ap.parse_args()
    start, end = datetime.fromisoformat(a.start).replace(tzinfo=timezone.utc), datetime.fromisoformat(a.end).replace(tzinfo=timezone.utc)
    folder = OUT / 'debrief' / f'{a.start}_{a.end}'
    snap = json.loads((OUT / 'live' / 'latest.json').read_text(encoding='utf-8'))
    mm = magic_map(); phases = roster(); prods = products()
    allpos = live_positions(snap, mm)
    week = [p for p in allpos if start <= p['open'] < end]
    bts = backtest_trades(folder) if (folder / 'selection.json').exists() else {}
    kills = {r['slug']: r for r in json.loads((OUT / 'KILL_SWITCHES.json').read_text(encoding='utf-8'))['rows']}
    sheet_path = OUT / 'event_sheet' / 'latest.json'
    events = json.loads(sheet_path.read_text(encoding='utf-8'))['events'] if sheet_path.exists() else []

    manual = [p for p in allpos if p['exit_kind'] in ('client', 'mobile', 'web') and p['close'] and start <= p['close'] < end]
    ea_entries = [ts(d['time_msc'] / 1000) for d in snap['deals'] if d['type'] in (0, 1) and d['entry'] == 0 and d['reason'] == 3]
    last_ea_entry = max(ea_entries).isoformat() if ea_entries else None
    by_slug = defaultdict(list)
    for p in week:
        by_slug[p['slug']].append(p)
    rows = []
    for slug in sorted(set(by_slug) | set(bts)):
        lv = by_slug.get(slug, []); bt = bts.get(slug)
        tf = TF_MIN.get(prods[slug].timeframe if slug in prods else 'M15', 15)
        row = dict(slug=slug, label=prods[slug].label if slug in prods else slug, phase=phases.get(slug, 'not-in-roster'), live=len(lv))
        if slug in NEWS:
            offs = []
            for p in lv:
                near = min(events, key=lambda e: abs(e['epoch'] - p['open'].timestamp()), default=None)
                offs.append(None if not near else round(p['open'].timestamp() - near['epoch']))
            row.update(kind='news', backtest=None, entry_offsets_vs_nearest_official_event_s=offs)
        elif bt is None:
            row.update(kind='no-backtest', backtest=None)
        elif bt['trades'] is None:
            row.update(kind='backtest-failed', backtest=None, audit=(bt['meta'] or {}).get('audited'))
        else:
            pairs, missed, extra = match(bt['trades'], lv, tf)
            c = Counter(p['status'] for p in pairs)
            row.update(kind='compared', backtest=len(bt['trades']), audited=(bt['meta'] or {}).get('audited'), match=c.get('MATCH', 0), timing=c.get('TIMING', 0),
                       exit_diff=c.get('EXIT_DIFF', 0), missed=len(missed), extra=len(extra),
                       sign_agree=sum(p['bt_sign'] == p['live_sign'] for p in pairs), pairs=pairs,
                       missed_opens=[m['open'].isoformat() for m in missed], extra_opens=[e['open'].isoformat() for e in extra])
        # kill-switch status on ALL live history of this EA (R at the assumed risk)
        hist = sorted((p for p in allpos if p['slug'] == slug and p['closed']), key=lambda p: p['close'])
        rs = [p['net'] / (a.risk_pct / 100 * p['balance_before']) for p in hist if p['balance_before'] > 0]
        k = kills.get(slug)
        if rs:
            dd, streak = max_drawdown(rs), longest_losing_streak(rs)
            cur = 0
            for v in reversed(rs):
                if v < 0: cur += 1
                elif v > 0: break
            status = 'NO_THRESHOLD'
            if k and k.get('status') == 'SET':
                status = 'KILL' if dd >= k['kill']['drawdown_r'] or cur >= k['kill']['losing_streak'] else \
                         'WATCH' if dd >= k['watch']['drawdown_r'] or cur >= k['watch']['losing_streak'] else 'OK'
            row.update(live_closed_total=len(rs), live_total_r=round(sum(rs), 2), live_dd_r=round(dd, 2), live_max_streak=streak, live_current_streak=cur, kill_status=status,
                       kill_thresholds=None if not k or k.get('status') != 'SET' else dict(watch_dd=k['watch']['drawdown_r'], kill_dd=k['kill']['drawdown_r'],
                                                                                           watch_streak=k['watch']['losing_streak'], kill_streak=k['kill']['losing_streak']))
        rows.append(row)

    comp = [r for r in rows if r.get('kind') == 'compared']
    roster_live = [r for r in comp if r['phase'] == 'live']
    total_bt = sum(r['backtest'] for r in comp); matched = sum(r['match'] for r in comp)
    missed = sum(r['missed'] for r in comp); extra = sum(r['extra'] for r in comp)
    off_roster = [r for r in rows if r['live'] and r['phase'] not in ('live',)]
    silent = [r for r in roster_live if r['backtest'] and not r['live']]
    kill_flags = [r for r in rows if r.get('kill_status') in ('KILL', 'WATCH')]
    change = ('Check that the reviewed profile is attached on the demo (EAs are opening trades, last EA entry ' + str(last_ea_entry)[:16] + ' UTC): '
              f"{len(silent)} live-roster EAs traded in the backtest but not on the demo ({', '.join(r['label'] for r in silent)})." if len(silent) >= 3 else
              f"Stop manual closes of EA positions ({len(manual)} this week) or add the reason to an exit rule." if manual else
          f"Remove the off-roster EAs from the demo terminal ({', '.join(r['label'] + ' [' + r['phase'] + ']' for r in off_roster)})." if off_roster else
              f"Review {kill_flags[0]['label']} ({kill_flags[0]['kill_status']}): live drawdown {kill_flags[0]['live_dd_r']}R." if kill_flags else
              'Investigate the largest timing / exit deviation listed below.' if (total_bt and matched < total_bt) else 'No change: execution matched the backtest.')
    memo = dict(window=[a.start, a.end], generated_utc=now_utc().isoformat(), account=snap['account'] | {'balance': None, 'equity': None},
                algo_trading_allowed_at_snapshot=snap['terminal_state']['trade_allowed'], snapshot_utc=snap['fetched_utc'], risk_pct_assumed=a.risk_pct,
                counts=dict(live_positions=len(week), backtest_trades=total_bt, matched=matched, missed=missed, extra=extra),
                last_ea_entry_utc=last_ea_entry, manual_closes=[dict(slug=p['slug'], symbol=p['symbol'], closed=p['close'].isoformat(), exit=p['exit_kind'], net=p['net']) for p in manual],
                one_change=change, rows=rows)
    save('DEBRIEF.json', memo, folder=folder)

    st = lambda r: r.get('kill_status', '—')  # noqa: E731
    md = [f'# Weekly live debrief {a.start} → {a.end} (end exclusive, server time)', '',
          f"Demo account {snap['account']['server']} {snap['account']['login_masked']} (trade_mode {snap['account']['trade_mode']}, 0 = demo). "
          f"Snapshot {snap['fetched_utc'][:16]} UTC. Last EA-opened entry: **{str(last_ea_entry)[:16]} UTC** (the MT5 API's terminal trade_allowed flag "
          f"read {snap['terminal_state']['trade_allowed']}; EA entries are the reliable evidence that Algo Trading is on).", '',
          'Judges execution against the same week\'s native backtest of the same frozen EX5/SET (isolated tester, Exness-MT5Trial16, Model 4), '
          'never the result. The demo runs on Exness-MT5Trial15: quotes and spreads differ, so small timing differences are expected.', '',
          '## 1. Counts', '',
          f"- Live positions opened in the window: **{len(week)}**. Backtest trades (non-news EAs): **{total_bt}**.",
          f"- Matched (same side, entry within one bar, same exit type): **{matched}**; extra on demo: **{extra}**.",
          f"- Missed on demo: **{missed}** = **{sum(r['missed'] for r in roster_live)}** for live-phase EAs (a fault to explain) + "
          f"**{missed - sum(r['missed'] for r in roster_live)}** for paused/review EAs (expected: they should not trade).",
          f"- Live-roster EAs that traded in the backtest but not on the demo: **{len(silent)}**.",
          f"- EAs trading on the demo that are NOT in the live phase: **{len(off_roster)}** ({', '.join(r['label'] + ' [' + r['phase'] + ']' for r in off_roster) or 'none'}).",
          f"- Manual / mobile / web closes of positions in the window: **{len(manual)}** " + (f"({'; '.join(p['slug'] + ' ' + p['symbol'] + ' ' + p['close'].strftime('%a %m-%d %H:%M') + ' ' + p['exit_kind'] for p in manual)})" if manual else '') + '.', '',
          '## 2. Per EA', '',
          '| Phase | EA | Live | Backtest | Match | Timing | Exit diff | Missed | Extra | Result sign agrees | Kill switch |',
          '|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|']
    order = {'live': 0, 'paused': 1, 'review': 2}
    for r in sorted(rows, key=lambda r: (order.get(r['phase'], 3), r['label'])):
        if r.get('kind') == 'compared':
            md.append(f"| {r['phase']} | {r['label']} | {r['live']} | {r['backtest']} | {r['match']} | {r['timing']} | {r['exit_diff']} | {r['missed']} | {r['extra']} | "
                      f"{r['sign_agree']}/{r['match'] + r['timing'] + r['exit_diff']} | {st(r)} |")
        elif r.get('kind') == 'news':
            offs = ', '.join('—' if o is None else f'{o:+d}s' for o in r['entry_offsets_vs_nearest_official_event_s']) or '—'
            md.append(f"| {r['phase']} | {r['label']} | {r['live']} | no tester | — | — | — | — | — | entry vs event: {offs} | {st(r)} |")
        else:
            md.append(f"| {r['phase']} | {r['label']} | {r['live']} | {r.get('kind')} | — | — | — | — | — | — | {st(r)} |")
    md += ['', '## 3. Kill-switch status (all live history of each EA, R at the assumed risk)', '',
           f"R = net / ({a.risk_pct}% × balance before entry). Live BAT risk, adaptive tapers and news percentages can differ per EA, so treat R as approximate.", '',
           '| EA | Live closed trades | Live total R | Live max DD R | WATCH / KILL DD R | Current losing streak | WATCH / KILL streak | Status |', '|---|---:|---:|---:|---|---:|---|---|']
    for r in sorted((r for r in rows if 'live_closed_total' in r), key=lambda r: ({'KILL': 0, 'WATCH': 1}.get(r['kill_status'], 2), r['label'])):
        t = r.get('kill_thresholds') or {}
        md.append(f"| {r['label']} | {r['live_closed_total']} | {r['live_total_r']:+.2f} | {r['live_dd_r']} | {t.get('watch_dd', '—')} / {t.get('kill_dd', '—')} | "
                  f"{r['live_current_streak']} | {t.get('watch_streak', '—')} / {t.get('kill_streak', '—')} | **{r['kill_status']}** |")
    md += ['', '## 4. One change for next week (proposal; the owner decides)', '', f'- {change}', '',
           '## 5. What this does NOT show', '',
           '- Whether any EA has an edge: one week is far too short. This checks execution and wiring only.',
           '- News EAs: no tester evidence after 2026-09-11; only their entry times versus official event times are listed.',
           '- Backtest and demo use different Exness servers; a TIMING or EXIT_DIFF can be a quote difference, not a fault.',
           '- Live R uses one assumed risk %, not each EA\'s actual planned stop risk.']
    (folder / 'DEBRIEF.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print('\n'.join(md[:20])); print('...'); print('ONE CHANGE:', change)


if __name__ == '__main__':
    main()
