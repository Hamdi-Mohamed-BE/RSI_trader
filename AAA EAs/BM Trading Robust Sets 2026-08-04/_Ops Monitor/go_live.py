"""Item 4b: go-live checklist (the library's six questions) and the monthly EA review, from monitor outputs.

checklist : per EA, six yes/no questions before moving from demo to a real-money or funded account.
monthly   : per EA, KEEP / ENFORCE / QUESTION / WATCH / KILL / OFF-ROSTER for one calendar month, from the weekly
            debriefs in that month + kill-switch status. Verdicts recommend; the owner decides. Never changes anything.

uv run python ".../_Ops Monitor/go_live.py" checklist
uv run python ".../_Ops Monitor/go_live.py" monthly --month 2026-10
"""
import argparse, json
from collections import defaultdict

from common import OUT, now_utc, products, roster, save

NEWS = {'news-pulse-xau', 'news-pulse-xag', 'news-pulse-btc', 'news-pulse-eurusd', 'gold-news-v9-direction'}
EXTERNAL = {'gold-news-v9-direction': 'needs the external AI-news service'}
NO_STOP = {'us30-hourly-profiles', 'us100-hourly-profiles'}


def debriefs(month: str | None = None):
    out = []
    for p in sorted((OUT / 'debrief').glob('*/DEBRIEF.json')):
        d = json.loads(p.read_text(encoding='utf-8'))
        if month is None or d['window'][0][:7] == month or d['window'][1][:7] == month:
            out.append(d)
    return out


def merged_rows(ds):
    agg = defaultdict(lambda: defaultdict(int)); last = {}
    for d in ds:
        for r in d['rows']:
            a = agg[r['slug']]
            for k in ('live', 'backtest', 'match', 'timing', 'exit_diff', 'missed', 'extra'):
                a[k] += r.get(k) or 0
            a['weeks'] += 1
            last[r['slug']] = r
    return agg, last


def checklist():
    kills = {r['slug']: r for r in json.loads((OUT / 'KILL_SWITCHES.json').read_text(encoding='utf-8'))['rows']}
    ds = debriefs(); agg, last = merged_rows(ds); phases = roster(); rows = []
    for slug, p in products().items():
        a = agg.get(slug, {}); l = last.get(slug, {}); k = kills.get(slug, {})
        compared = a.get('match', 0) + a.get('timing', 0) + a.get('exit_diff', 0) + a.get('missed', 0) + a.get('extra', 0)
        q = {}
        q['1_mechanical'] = ('YES, external dependency: ' + EXTERNAL[slug]) if slug in EXTERNAL else 'YES (compiled MQL5, frozen SET)'
        if slug in NEWS:
            q['2_followed'] = 'NOT CHECKABLE: no tester evidence after the verified calendar; entry timing only (event sheet)'
        elif compared >= 10:
            rate = a.get('match', 0) / compared
            q['2_followed'] = f"{'YES' if rate >= .8 else 'NO'}: {a.get('match', 0)}/{compared} backtest/live trades matched over {a.get('weeks', 0)} debrief week(s)"
        else:
            q['2_followed'] = f"NOT YET: {compared} comparable trades over {a.get('weeks', 0)} week(s); need >= 10 and 8 weeks"
        n_live = l.get('live_closed_total', 0)
        q['3_logged'] = f"{'YES' if n_live >= 30 else 'NOT YET'}: {n_live} closed demo trades (need >= 30)"
        q['4_bounded'] = (f"YES: KILL at {k['kill']['drawdown_r']}R drawdown or {k['kill']['losing_streak']} losses in a row (WATCH {k['watch']['drawdown_r']}R / {k['watch']['losing_streak']})"
                          if k.get('status') == 'SET' else ('NO: no stop loss, R undefined — needs a cash-based limit' if slug in NO_STOP else 'NO: no threshold (insufficient evidence)'))
        q['5_allowed'] = ('OWNER TO CONFIRM IN WRITING: broker/firm automation rules; FTMO lists EAs as allowed unless a forbidden practice, '
                          'and the pre-news straddle needs written clarification' if slug in NEWS else
                          'OWNER TO CONFIRM IN WRITING: broker/firm automation rules for the target account type')
        q['6_owned'] = 'OWNER TO CONFIRM: time/skill/budget to monitor and maintain'
        yes = sum(v.startswith('YES') for v in q.values())
        rows.append(dict(slug=slug, label=p.label, phase=phases.get(slug, '-'), answers=q, yes=yes,
                         ready='READY TO STEP UP' if yes == 6 else f'HOLD ON DEMO ({6 - yes} open)'))
    save('GO_LIVE_CHECKLIST.json', dict(generated_utc=now_utc().isoformat(), debrief_weeks=len(ds), rows=rows))
    order = {'live': 0, 'paused': 1, 'review': 2}
    md = ['# Go-live checklist (six questions per EA)', '',
          f'Generated {now_utc():%Y-%m-%d %H:%M} UTC from {len(ds)} weekly debrief(s), the kill-switch table and the reviewed roster. '
          'Six YES answers before an EA steps up from demo to a real-money or funded account; any NO / NOT YET means hold on demo and keep logging. '
          'Questions 5 and 6 can only be answered by the owner.', '',
          '| Phase | EA | 1 Mechanical | 2 Followed (live = backtest) | 3 Logged (≥30 demo trades) | 4 Bounded (kill switch) | Verdict |', '|---|---|---|---|---|---|---|']
    for r in sorted(rows, key=lambda r: (order.get(r['phase'], 3), r['label'])):
        q = r['answers']
        md.append(f"| {r['phase']} | {r['label']} | {q['1_mechanical']} | {q['2_followed']} | {q['3_logged']} | {q['4_bounded']} | **{r['ready']}** |")
    md += ['', 'For every EA: **5 Allowed** — confirm in writing that the broker/firm permits automated trading on the account type '
           '(news EAs: get written clarification on the pre-news straddle). **6 Owned** — confirm you can monitor it and switch it off.']
    (OUT / 'GO_LIVE_CHECKLIST.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f"{sum(r['ready'].startswith('READY') for r in rows)} ready / {len(rows)}; debrief weeks {len(ds)}")


def monthly(month: str):
    ds = debriefs(month); agg, last = merged_rows(ds); phases = roster(); rows = []
    for slug, p in products().items():
        a = agg.get(slug, {}); l = last.get(slug, {}); phase = phases.get(slug, '-')
        dev = a.get('missed', 0) + a.get('extra', 0) + a.get('timing', 0) + a.get('exit_diff', 0)
        ks = l.get('kill_status')
        if ks == 'KILL': v = 'KILL (recommend switching off and reviewing)'
        elif ks == 'WATCH': v = 'WATCH (drawdown or losing streak above the 95th percentile)'
        elif a.get('live', 0) and phase != 'live': v = f'OFF-ROSTER (traded while {phase})'
        elif phase != 'live': v = f'NOT TRADING ({phase}, as intended)'
        elif dev >= 2: v = f'ENFORCE ({dev} execution deviations: fix wiring/attachment before judging the EA)'
        elif not a.get('live', 0) and not a.get('backtest', 0): v = 'QUESTION (no live or backtest trades this month: not tested, not a failure)'
        elif not a.get('live', 0): v = 'ENFORCE (backtest traded, demo did not)'
        else: v = 'KEEP'
        rows.append(dict(slug=slug, label=p.label, phase=phase, weeks=a.get('weeks', 0), live=a.get('live', 0), backtest=a.get('backtest', 0),
                         matched=a.get('match', 0), deviations=dev, kill_status=ks, verdict=v))
    save(f'MONTHLY_REVIEW_{month}.json', dict(generated_utc=now_utc().isoformat(), month=month, debrief_weeks=len(ds), rows=rows))
    order = {'live': 0, 'paused': 1, 'review': 2}
    md = [f'# Monthly EA review — {month}', '', f'From {len(ds)} weekly debrief(s). Counts behaviour and wiring, not edge: one month cannot show whether an EA '
          'makes money. At most one EA should be switched off and one re-wired per month; the owner decides.', '',
          '| Phase | EA | Debrief weeks | Live trades | Backtest trades | Matched | Deviations | Kill switch | Verdict |', '|---|---|---:|---:|---:|---:|---:|---|---|']
    for r in sorted(rows, key=lambda r: (order.get(r['phase'], 3), r['label'])):
        md.append(f"| {r['phase']} | {r['label']} | {r['weeks']} | {r['live']} | {r['backtest']} | {r['matched']} | {r['deviations']} | {r['kill_status'] or '—'} | {r['verdict']} |")
    (OUT / f'MONTHLY_REVIEW_{month}.md').write_text('\n'.join(md) + '\n', encoding='utf-8')
    print(f'{month}: {len(rows)} EAs, {len(ds)} debrief week(s)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('cmd', choices=['checklist', 'monthly']); ap.add_argument('--month')
    a = ap.parse_args()
    checklist() if a.cmd == 'checklist' else monthly(a.month or now_utc().strftime('%Y-%m'))
