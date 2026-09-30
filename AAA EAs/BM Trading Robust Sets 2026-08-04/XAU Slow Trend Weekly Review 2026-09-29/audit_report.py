"""Independent native-ledger checks and a transparent results-only report."""
from pathlib import Path
from datetime import datetime,timedelta
from collections import Counter
import json,hashlib,gzip
from bs4 import BeautifulSoup
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'XAU Slow Trend Filter Review 2026-09-29'
NAMES={'baseline':'Current rules','adx20-di-rising':'ADX/DI + rising ADX','calendar':'Once/calendar week','rolling7':'Seven-day entry cooldown','adx-calendar':'ADX/DI + once/week','adx-rolling7':'ADX/DI + seven-day cooldown'}
CANDIDATES=['calendar','rolling7','adx-calendar','adx-rolling7']
ORDER=['baseline','adx20-di-rising']+CANDIDATES
def load(p):return json.loads(p.read_text())
def save(p,v):p.write_text(json.dumps(v,indent=2,allow_nan=False),encoding='utf-8')
def get(v,w,model):
    name=f'{v}-{w}-m{model}'
    p=ROOT/'native'/name/'result.json'
    if not p.exists():p=OLD/'native'/name/'result.json'
    r=load(p);r['evidence_path']=str(p);return r
def table(rows):
    s='| Version | Return | PF | Equity DD | Win rate | Trades / month / weekday | Max W / L streak |\n|---|---:|---:|---:|---:|---:|---:|\n'
    for r in rows:
        m=r['metrics'];pf=f"{m['profit_factor']:.2f}" if m['profit_factor'] is not None else 'n/a'
        s+=f"| {NAMES[r['variant']]} | {m['return_pct']:+.2f}% | {pf} | {m['equity_dd_pct']:.2f}% | {m['win_rate_pct']:.2f}% | {m['trades']} / {m['trades_per_month']:.2f} / {m['trades_per_weekday']:.3f} | {m['max_win_streak']} / {m['max_loss_streak']} |\n"
    return s
def main():
    sel=load(ROOT/'SELECTION.json');chosen=sel['chosen'];checks=[]
    paths=sorted((ROOT/'native').glob('*/result.json'))
    assert len(paths)==15,'Incomplete bounded test schedule'
    for path in paths:
        r=load(path);m=r['metrics'];ts=load(path.with_name('trades.json'))
        assert len(ts)==m['trades'] and abs(sum(t['net_profit'] for t in ts)-m['net_profit'])<.05
        mode=int(r['inputs']['ResearchWeeklyMode']);week_counts=Counter();previous=None;min_entry_hours=None
        start=datetime.strptime(r['start'],'%Y.%m.%d');end=datetime.strptime(r['end'],'%Y.%m.%d')
        for t in ts:
            opened=datetime.fromisoformat(t['open_time']);closed=datetime.fromisoformat(t['close_time'])
            assert start<=opened<=closed<end
            assert t['symbol']=='XAUUSD' and t['volume']>0
            assert abs(t['gross_profit']+t['commission']+t['swap']-t['net_profit'])<.011
            profit=(t['close_price']-t['open_price'])*(1 if t['side']=='Long' else -1)*100*t['volume']
            assert abs(t['gross_profit']-profit)<.06
            # Independent calendar implementation: Python weekday() uses Monday=0.
            monday=opened.date()-timedelta(days=opened.weekday());week_counts[str(monday)]+=1
            if previous:
                assert opened>=datetime.fromisoformat(previous['close_time']),'Overlap'
                spacing=(opened-datetime.fromisoformat(previous['open_time'])).total_seconds()
                assert spacing>=86400,'Original entry cooldown failed'
                if mode==2:assert spacing>=604800,'Rolling-week rule failed'
                hours=spacing/3600;min_entry_hours=hours if min_entry_hours is None else min(min_entry_hours,hours)
            previous=t
        if mode==1:assert max(week_counts.values(),default=0)<=1,'Calendar-week rule failed'
        journal=gzip.decompress(path.with_name('journal.txt.gz').read_bytes()).decode()
        assert 'WEEKLY SELF TEST PASS' in journal
        assert not any(r['flags'].values()),r['flags']
        soup=BeautifulSoup(gzip.decompress(path.with_name('report.htm.gz').read_bytes()),'html.parser')
        quality=next(tr.get_text(' ',strip=True) for tr in soup.find_all('tr') if 'History Quality:' in tr.get_text())
        if r['model']==4:
            assert 'generating based on real ticks' in journal
            assert ('100% real ticks' if r['window']=='6m' else '73% real ticks') in quality,quality
        checks.append(dict(case=r['case'],trades=len(ts),cash_reconciled=True,no_overlap=True,weekly_mode=mode,weekly_rule_passed=True,max_entries_calendar_week=max(week_counts.values(),default=0),min_entry_spacing_hours=min_entry_hours,reported_history_quality=quality))
    build=load(ROOT/'BUILD.json');assert all(hashlib.sha256(Path(p).read_bytes()).hexdigest()==h for p,h in build.items())
    assert load(ROOT/'PARITY.json')['passed']
    audit=dict(passed=True,completed_tests=len(paths),checks=checks);save(ROOT/'AUDIT.json',audit)
    recent=[get(v,'6m',4) for v in ORDER];year=[get(v,'1y',4) for v in ['baseline','adx20-di-rising',chosen]]
    dev=[get(v,'dev',1) for v in ORDER];val=[get(v,'val',1) for v in ORDER]
    by={r['variant']:r for r in recent};mc=by[chosen]['metrics'];my=year[-1]['metrics']
    passes_recent=mc['return_pct']>0 and my['return_pct']>0
    verdict=('Positive in both recent windows, but still exploratory and not approved for deployment.' if passes_recent else 'The older-window selection still loses in at least one recent window: no deployment recommendation.')
    best_recent=max((r for r in recent if r['variant'] in CANDIDATES),key=lambda r:r['metrics']['return_pct'])
    bm=best_recent['metrics'];bd=next(r['metrics'] for r in dev if r['variant']==best_recent['variant'])
    text=f'''# XAU Slow Trend — weekly entry limit results

29 September 2026. Isolated research only. **Active MT5, installed EA, portfolio and website were not changed.**

## Outcome

Selected on the older development/validation windows, before any new recent tests: **{NAMES[chosen]}**. Older-window eligibility passed: **{sel['older_windows_pass']}**. {verdict}

The highest recent six-month return among the four weekly variants was **{NAMES[best_recent['variant']]}**: **{bm['return_pct']:+.2f}%**, PF **{bm['profit_factor']:.2f}**, **{bm['trades']} trades**. Its older three-year result was **{bd['return_pct']:+.2f}%**, PF **{bd['profit_factor']:.2f}**. Reporting this retrospective winner is not a new selection or proof of a durable edge.

This follow-up is exploratory after the previous ADX study failed the latest six months. Those periods and the baseline were already seen; do not call this a fresh holdout, an optimized production bot, or a completed full validation pipeline. We tested four predefined variants, without weekday selection, stop/target changes or increased position risk.

## Recent six months — all variants, native Model4

2026-03-27 to 2026-09-27 (end exclusive). Same USD10,000 start and nominal 1% risk. “Once/week” is a maximum, not an instruction to force trades.

'''+table(recent)
    text+='\n## Recent year — previously selected weekly candidate\n\n2025-09-27 to 2026-09-27. Native Model4; the six-month window overlaps this one and is not independent evidence. Other weekly variants were not tested over this recent year.\n\n'+table(year)
    text+='\n## Older development — full comparison\n\n2021-09-27 to 2024-09-27. Native Model1 1-minute OHLC screening, not real-tick proof.\n\n'+table(dev)
    text+='\n## Older validation — full comparison\n\n2024-09-27 to 2025-09-27. Native Model1. Require development >=20 trades, positive return, PF>=1.15; validation >=10 trades, positive return, PF>=1.10. Rank eligible candidates by validation return/equity drawdown.\n\n'+table(val)
    text+='''
## What the entry rules do — and do not do

- **Calendar week:** only the first qualifying entry after Monday 00:00 broker time is permitted that week. The existing 24-hour entry-to-entry guard remains. A position may stay open across multiple weeks. No forced Monday entry or Friday close.
- **Rolling seven days:** at least 168 hours from the preceding entry, regardless of when it exits. One open position maximum remains.
- **ADX/DI versions:** native ADX14 >=20, +DI>-DI for longs or -DI>+DI for shorts, and ADX[1]>ADX[2], all from closed H4 candles. Existing momentum/EMA rules still apply.
- **Manual closure:** closing a position does not reset the last-entry clock. That blocks replacements until the entry cap expires, but if the entry is already a week old, a replacement may be permitted immediately. A “pause after my manual close until I re-arm it” control is a separate operational safeguard, not tested profit enhancement here.
- **Risk:** no compensating increase in lot size. Original nominal 1% equity sizing rounds lots upward, so actual stop risk can exceed 1%. A lower drawdown with fewer trades is not by itself a stronger edge.

## Native execution and evidence limits

- Same isolated Exness-MT5Trial16 XAUUSD CFD tester as the previous study, H4, USD10,000, 150ms execution delay, broker spread/commission/swap. Active demo account is Trial15. This is not a replay of your manually closed trades or other portfolio bots.
- Baseline inputs follow the saved configuration, corroborated in the previous account audit by actual H4 ATR stop/6R target geometry. Active chart inputs cannot be read directly through the Python MT5 API; exact live configuration equivalence remains an assumption, not a newly verified fact.
- Stop remains 1.5 × ATR14, target 6R, both sides, no new exit management. Each window starts flat and liquidates remaining exposure at the tester end. Six-month results are independent simulations, not sliced yearly returns.
- Model4 real ticks begin 2026-01-01 in the retained broker history. One-year reports specify **73% real ticks**, with generated fallback earlier; six-month reports specify **100% real ticks**. These explicit real-tick percentages were checked in each native report, not inferred from a generic history-quality label.
- Fifteen new native tests completed: two off-switch parity runs, eight older-window screens, four recent six-month tests and one recent-year test. Existing control results are reused from the dated prior study where not rerun. The new default-off weekly EA reproduced the baseline's 38-trade one-year Model1 ledger and the ADX control's 45-trade one-year Model4 ledger exactly, including all prices, sizes, times and net costs. This is bounded parity, not proof under all live conditions.
- Native equity drawdown includes floating losses; it is not a closed-balance calculation. Trade/month uses calendar-month equivalents, and trade/weekday uses Monday-Friday counts rather than exact broker sessions. Win/loss streaks use net cash after costs.
- Calendar/rolling arithmetic self-tests passed inside the native EA. Independent ledger checks passed for cash totals, contract-size price P&L, no overlapping positions, 24-hour original spacing, and the selected calendar or rolling-week restriction. Source/include/binary hashes remained unchanged. Native compile: zero errors/warnings. No invalid stops/volumes, insufficient-funds, stop-out or market-closed errors detected.
- Only a small number of recent trades remain after throttling. There is no multiple-testing adjustment, Monte Carlo, extra-cost stress grid, independent-broker test, or new forward-test evidence here. Broker swap specifications are not a verified historical schedule. No promise of profitability or safe drawdown follows from this study.

## Sources and local evidence

Calendar conversion follows [MQL5 date/time fields](https://www.mql5.com/en/docs/constants/structures/mqldatetime); broker week uses [Exness MetaTrader GMT+0 time](https://get.exness.help/hc/en-us/articles/360014390760-What-is-the-default-timezone-set-for-MetaTrader). Native indicator definitions: [iADX buffers](https://www.mql5.com/en/docs/indicators/iadx). Testing limitations: [real/generated tick behavior](https://www.metatrader5.com/en/terminal/help/algotrading/tick_generation).

Local protocol, build hashes, selection and audit are retained as PROTOCOL.md, BUILD.json, PARITY.json, SELECTION.json and AUDIT.json. Every native report and trade ledger is retained under native/. Private tester login settings are not included in this report. Prior control evidence is in the sibling XAU Slow Trend Filter Review 2026-09-29/native/ directory.
'''
    coverage=sorted(set(line.split('\t')[-1] for r in recent+year for line in r.get('tick_coverage',[])))
    text+='\n### Retained tick coverage messages\n\n'+'\n'.join('- '+line for line in coverage)+'\n'
    (ROOT/'REPORT.md').write_text(text,encoding='utf-8')
    summary=dict(selected=chosen,older_windows_pass=sel['older_windows_pass'],verdict=verdict,recent6m=recent,recent1y=year,audit_passed=True,completed_native_tests=len(paths))
    save(ROOT/'SUMMARY.json',summary)
    print(json.dumps(dict(selected=chosen,verdict=verdict,recent6m=[dict(version=r['variant'],**r['metrics']) for r in recent],recent1y=[dict(version=r['variant'],**r['metrics']) for r in year]),indent=2))
if __name__=='__main__':main()
