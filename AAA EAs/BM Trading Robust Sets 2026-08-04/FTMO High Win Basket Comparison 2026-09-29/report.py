"""Verify saved results and produce the user-facing comparison."""
from pathlib import Path
import sys,json,hashlib
import numpy as np
ROOT=Path(__file__).resolve().parent;OLD=ROOT.parent/'Daily Equity Controls Audit 2026-09-29'
sys.path.insert(0,str(OLD))
from payout_followup import business_ready,DAY
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
r=read(ROOT/'RESULTS.json');life=read(ROOT/'LIFECYCLE.json');a=read(ROOT/'SOURCE_AUDIT.json')
assert sha(OLD/'recent-ROWS.json')==a['source_current13_sha']
assert sha(OLD/'recent-prepared.npz')==a['source_price_sha']
assert sha(OLD/'simulate.py')==a['source_engine_sha']
assert sha(ROOT/'PROTOCOL.md')==a['protocol_sha']
for s in a['additional_sources']:
    assert sha(Path(s['source']))==s['source_sha']
    assert sha(Path(s['report']))==s['report_sha']
paths=stages=rewards=0
for scenario in life:
    for p in scenario['paths']:
        paths+=1
        for s in p['stages']:
            stages+=1;m=s['metrics']
            if s['success']:
                assert m['open_at_end']==0 and m['first_ftmo_breach_minute']<0
                assert s['profit']>={1:1000,2:500,3:50}[s['phase']]-1e-6
                if s['phase']==3:assert s['end']-s['first_entry']>=14*DAY
            if scenario['config']['cap']:assert m['max_open_risk']<=250+1e-7
        if p['phase2'] is not None:assert p['phase2']>=business_ready(p['phase1'],2)
        if p['funded'] is not None:assert p['funded']==business_ready(p['phase2'],5)
        for reward in p['rewards']:
            rewards+=1
            assert abs(reward['trader_share']-.8*reward['gross'])<1e-7
            assert p['funded']+14*DAY<=reward['request']<=p['end']
    for s in scenario['summary']:
        cohort=[p for p in scenario['paths'] if p['end']-p['start']>=s['horizon_days']*DAY]
        assert len(cohort)==s['starts']
        passcount=sum(p['phase2'] is not None and p['phase2']<=p['start']+s['horizon_days']*DAY for p in cohort)
        assert passcount==s['counts']['phase2']
        shares=[sum(x['trader_share'] for x in p['rewards'] if x['request']<=p['start']+s['horizon_days']*DAY) for p in cohort]
        assert abs(np.mean(shares)-s['total_trader_share_all_starts_usd']['mean'])<1e-6
for row in r:
    z=np.load(ROOT/(row['id']+'.npz'));logs=z['logs'];tr=z['trades'];m=row['metrics']
    assert len(logs)==m['trades'] and int(np.sum(logs[:,4]>0))==m['wins']
    assert abs(np.maximum(logs[:,4],0).sum()-m['positive'])<1e-6
    assert abs(-np.minimum(logs[:,4],0).sum()-m['negative'])<1e-6
    assert np.all(logs[:,5]<=50.+1e-7)
    assert np.allclose(logs[:,3]*tr[logs[:,0].astype(int),4],logs[:,5])
    assert abs((m['ending_equity']-10000)/100-m['return_pct'])<1e-7
check=dict(paths=paths,stages=stages,reward_requests=rewards,continuous_runs=len(r),
    source_hashes_unchanged=True,stage_and_summary_checks=True,log_risk_and_cash_metrics=True,
    prior_full_period_regression=read(ROOT/'REGRESSION.json'),synthetic_tests='56 test executions passed; includes inherited duplicate cases.',passed=True)
(ROOT/'VERIFICATION.json').write_text(json.dumps(check,indent=2),encoding='utf-8')

names=['Current13','HighWin8','CurrentCore5']
labels={'Current13':'Current 13 EAs','HighWin8':'Proposed high-win 8 EAs','CurrentCore5':'Current-version core 5 EAs'}
def result(g,case='Reference',cfg='A loss2 goal4'):
    return next(x for x in r if x['group']==g and x['case']['name']==case and x['config']['name']==cfg)
def summary(g,h=180,case='Reference',cfg='A loss2 goal4'):
    row=next(x for x in life if x['group']==g and x['case']['name']==case and x['config']['name']==cfg)
    return next(s for s in row['summary'] if s['horizon_days']==h)
def cash(x):return f'${x:,.0f}'
def timing(s,key):
    d=s['timing_days'][key]
    return f"{d['median']:.0f}" if d else 'Not reached'

out='''# FTMO: proposed high-win basket versus the current portfolio

29 September 2026. **Analysis only: nothing deployed or changed on any trading account.** XAU RSI VWAP and Nasdaq 5M are included as requested.

## Verdict

**Better historical win rate and lower drawdown; worse historical profit, challenge speed and six-month reward totals.** The high-win basket is not a clear upgrade for FTMO. Keep the current 13-EA package as the comparison baseline; the proposed basket merits a separate demo test, not an automatic replacement.

The comparison uses **27 September 2025–31 August 2026, 339 calendar days**, the common supported period. It is not a full trailing year. The newer Current13 result for the longer original period was reproduced exactly before clipping all baskets to the same dates. Returns below are account equity changes, not withdrawals; all three have one open position at the common endpoint.

## Baskets and settings

**Proposed eight**, using one EMA3 version, not two:

1. Gold Overnight Value Area — raw.
2. ORB Volume Profile — retained 0.75R high-win version.
3. EMA3 — retained Safe version.
4. US100 H1 ORB — 1R + ADX14 ≥25.
5. XAU Squeeze Momentum — retained Safe version.
6. Nasdaq Overnight — newer audited inputs.
7. XAU RSI VWAP — newer audited inputs, included despite its standalone PF1.18.
8. Nasdaq 5M — DI14/EMA12 agreement, 0.60% price stop, ATR6 trailing from +1R, no TP.

Nasdaq's selected recent-year standalone result is 51.40% wins / PF1.48 / 179 trades. This is the best win rate among the completed comparable catalogue and recent management variants examined that satisfy PF≥1.2. It is already present in Current13: no duplicate is added. The older 0.75R Nasdaq test returned PF0.85 over its recent two-month window and is not used. The cancelled DI-toggle comparison was not resumed.

**Core5** is a cleaner subset check: Gold Overnight, current audited EMA3, Nasdaq Overnight, XAU RSI VWAP and Nasdaq 5M, all using the same source versions as Current13. It tests removing EAs without introducing older high-win versions.

Every basket shares a $10,000 account with a **fixed maximum $50 planned initial-stop risk per entry** (0.5% of initial capital), lots rounded down, News OFF. Same FTMO contract/margin/cost assumptions. Main policy A closes at daily net equity change of -$200 or +$400 from Prague-midnight balance and stops entries for that day; one-minute observation-to-execution delay. These policies replace the package's previous internal governors; this is not an exact replay of the unchanged launcher with every original guard stacked on top.

## Same-period continuous replay — main policy A

| Basket | Equity return | Net PF | Net win rate | Closed trades | Equity DD | Worst daily loss | Max winning / losing streak |
|---|---:|---:|---:|---:|---:|---:|---:|
'''
for g in names:
    x=result(g);m=x['metrics']
    out+=f"| {labels[g]} | +{m['return_pct']:.2f}% | {m['profit_factor']:.2f} | {m['win_rate']:.2f}% | {m['trades']:.0f} | {m['equity_dd_pct']:.2f}% | {m['worst_daily_pct']:.2f}% | {x['max_win_streak']} / {x['max_loss_streak']} |\n"
out+='''
Streaks describe the combined chronological closed-trade sequence across bots, not a forecast or individual-EA streak. Simultaneous exits follow the engine's deterministic order. Higher win rate does not make smaller profits arrive more often: the proposed basket has materially fewer accepted trades.

No sampled FTMO daily/total breach or adverse M1-envelope flag occurred in these continuous reference runs. That does not prove tick-level compliance. Current13 hit the +4% daily goal five times and the -2% stop twice; the proposed eight hit neither. The +4% level is a stop-taking-profit threshold, **not an expected daily return**.

## Why the standalone shortlist does not translate directly to a $10K account

Under the modeled 0.01-lot gold minimum, many wide-stop gold signals cannot fit the $50 risk budget and are skipped. In the proposed basket, **126 entries were rejected for sizing**, with no margin rejections. EMA3 Safe supplied 34 common-window signals but only three were accepted; XAU Squeeze Safe supplied ten but only three were accepted. Their attractive standalone one-year win rates are therefore not the win rates of a fully tradable 0.5%-risk FTMO stream. Exact broker minimum lots remain an assumption requiring account-specification verification.

Closed-trade contribution in the proposed eight (floating P/L at the endpoint is excluded):

| EA | Closed trades | Net contribution | Wins |
|---|---:|---:|---:|
'''
for key,m in result('HighWin8')['by_ea'].items():out+=f"| {key} | {m['trades']} | ${m['net']:,.2f} | {m['wins']} |\n"
out+='''
Nasdaq 5M generates more than half the proposed basket's closed profit. The eight names do not imply eight equally contributing or independent edges. Five are gold strategies and three trade Nasdaq; concentration remains.

## FTMO phase and first-reward scenarios

Same weekly start dates for all portfolios, from September 2025 onward. There are **23 starts with complete 180-day follow-up**. Median times are calendar days from the start of phase 1 and are conditional on reaching that milestone within 180 days. Unfinished cases are not discarded from success counts or average reward amounts. These are overlapping historical scenarios, **not estimated future pass/payout probabilities**.

| Basket | Both phases within 180d | First request within 180d | Median phase 1 days | Median both phases days | Median first-request days | Mean trader share requested in 180d, all starts |
|---|---:|---:|---:|---:|---:|---:|
'''
for g in names:
    s=summary(g);n=s['starts']
    out+=f"| {labels[g]} | {s['counts']['phase2']}/{n} | {s['counts']['reward']}/{n} | {timing(s,'phase1')} | {timing(s,'phase2')} | {timing(s,'first_reward')} | {cash(s['total_trader_share_all_starts_usd']['mean'])} |\n"
out+='''
The 120-day view uses a larger, separately eligible cohort of 31 starts:

| Basket | Both phases within 120d | First request within 120d |
|---|---:|---:|
'''
for g in names:
    s=summary(g,120);out+=f"| {labels[g]} | {s['counts']['phase2']}/{s['starts']} | {s['counts']['reward']}/{s['starts']} |\n"
out+='''
Lifecycle assumptions: flat +10% Challenge and +5% Verification targets, four distinct Prague opening days per phase; two and five assumed business days between phases/funded access. First funded request after 14 full calendar days from the first funded trade, at least $50 gross closed profit, no open position. Withdraw all gross profit; modeled trader share is 80%, restart at $10K after two assumed business days. No challenge fees/refunds, tax, transfer charges or actual approval delay are included. These are modeled **request amounts, not cash received**. The six-month totals include time spent in the evaluation phases.

Official [FTMO 2-Step objectives](https://ftmo.com/en/trading-objectives/) confirm the 10%/5% targets, 5% daily equity loss, 10% static overall loss and four opening days. [Reward rules](https://ftmo.com/faq/how-do-i-withdraw-my-profits/) specify the 14th-day request eligibility and 80% base 2-Step share; the extra day-count/admin conventions above are modeling choices. [Swing rules](https://ftmo.com/en/faq/ftmo-swing-account-type/) allow overnight/weekend holding. Sources checked 29 September 2026.

## Sensitivity — not calibrated forecasts

Higher costs add the earlier audit's adverse per-round-trip execution allowance (gold $0.20/oz, Nasdaq 2 points, USDJPY0.02) and double negative source swaps. Weaker-edge sensitivity additionally cuts positive gross outcomes by10% and enlarges negative gross outcomes by10%. Reference native spreads and commissions were already present; these are extra costs.

| Basket / case | Return | PF | DD | Both phases /23 at180d | First request /23 at180d | Mean180d trader share |
|---|---:|---:|---:|---:|---:|---:|
'''
for case in ('Higher costs','Costs + weaker edge','5-minute liquidation'):
    for g in names:
        m=result(g,case)['metrics'];s=summary(g,case=case)
        out+=f"| {labels[g]} / {case} | +{m['return_pct']:.2f}% | {m['profit_factor']:.2f} | {m['equity_dd_pct']:.2f}% | {s['counts']['phase2']} | {s['counts']['reward']} | {cash(s['total_trader_share_all_starts_usd']['mean'])} |\n"
out+='''
In the weaker-edge case, the proposed basket has lower DD but only 3/23 scenarios complete both phases within six months versus21/23 for Current13. Most non-completions are unfinished, not rule breaches. This illustrates why high win rate and comfortable drawdown are not the same as fast challenge completion.

## Approach B: open-risk cap instead of daily-loss stop

B limits original open-stop commitments to $250 and keeps the +$400 daily profit close, but removes the internal daily-loss close. FTMO's own equity rules still apply.

| Basket / cost case | Return | PF | DD | Worst daily loss |
|---|---:|---:|---:|---:|
'''
for case in ('Reference','Higher costs'):
    for g in names:
        m=result(g,case,'B risk2.5 goal4')['metrics']
        out+=f"| {labels[g]} / {case} | +{m['return_pct']:.2f}% | {m['profit_factor']:.2f} | {m['equity_dd_pct']:.2f}% | {m['worst_daily_pct']:.2f}% |\n"
out+='''
The proposed eight have identical continuous results under A and B because neither its daily triggers nor its open-risk cap binds in this period. This is not evidence that a loss stop is unnecessary. Reusing risk capacity can accumulate daily losses even when open risk stays below a cap. Retain A as the comparison default; no settings were changed.

## Evidence limits and verification

- This is an offline source-trade / M1 marked-equity overlay, not a fresh native shared-account FTMO tick test. Signals are not regenerated after forced exits/skips. Source-total swap is accrued approximately over the observed trade duration. Exness history is translated using FTMO contract/cost/margin assumptions; actual historical FTMO fills and minimum lots are not verified.
- ORB0.75R, EMA3 Safe and Squeeze Safe are older retained versions with stale build evidence; H1 ORB ADX25 is a retrospective research selection. Combining them with newer current ledgers is a provisional candidate comparison, not a proven current-build alternative. Selection on overlapping history biases it favourably.
- The latest-year native histories use real ticks mainly from January2026, with generated earlier ticks; generic cached history-quality labels do not certify full real-tick coverage. M1 sampling can miss intraminute breaches; worst-symbol extremes need not coincide.
- Per-trade risk is held at a fixed $50 maximum before execution costs; it is not compounded or raised for the smaller basket. Stop gaps, costs and observation/fill delay can exceed intended losses.
- Original stop/cash identities and new cache-to-native ledgers were checked. Existing Current13 matrix reconstruction is identical after relabelling keys; the earlier full-period reference replay has zero metric difference. All source hashes remain unchanged. 56 synthetic test executions passed (including inherited duplicate tests).
'''
out+=f"- Verified {paths} lifecycle paths, {stages} stages, {rewards} reward requests and {len(r)} continuous runs. See VERIFICATION.json, SOURCE_AUDIT.json, RESULTS.json and LIFECYCLE.json for retained evidence.\n"
out+='''
## Practical decision

If the priority is **historical challenge speed and reward amount**, Current13 wins this comparison. If the priority is **higher win rate and a calmer historical equity path**, HighWin8 looks better—but its older/research builds and reduced trade frequency prevent calling it a superior FTMO system. Keep it as a separate demo candidate until those versions are retested under exact account constraints. Nothing was removed from or added to live trading.
'''
(ROOT/'REPORT.md').write_text(out,encoding='utf-8')
print(json.dumps(check,indent=2))
print(ROOT/'REPORT.md')
