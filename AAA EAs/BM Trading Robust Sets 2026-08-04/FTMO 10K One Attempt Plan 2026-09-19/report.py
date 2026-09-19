"""Reproducible user-facing preliminary report; no EA or installer changes."""
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
results=json.loads((OUT/'results.json').read_text())['results']
extended=json.loads((OUT/'extended.json').read_text())
screen=json.loads((OUT/'screen.json').read_text())
chosen=next(r for r in results if r['name']=='Robust seven' and r['severity']=='stress')
lines=['# FTMO $10K 2-Step Swing: preliminary one-attempt plan',
       '', 'Prepared 19 September 2026. Research only: no BAT, live trading, terminal configuration, website, or portfolio changes.',
       '', '## Decision', '',
       'Do not buy on the expectation of a reliable pass in 30 days or a payout in 60 days. The current evidence does not support that promise. The candidate for further FTMO validation is the seven-EA balanced portfolio below. This is a shortlist, not a proven globally optimal combination.',
       '', '## Evidence and method', '',
       '- Latest saved Exness native-MT5 deal ledgers, common interval 7 September 2021 to 31 August 2026 (end exclusive). One shared $10,000 account, chronological entries/exits, shared limits and margin. No repurchases or retries.',
       '- 10 declared portfolio/risk configurations, three cost scenarios, 251 overlapping 60-calendar-day windows starting Mondays. Each configuration also has 1,000 seeded resamples of those complete windows, preserving cross-EA correlation. These are not 1,000 independent future paths or extra information.',
       '- Earlier/recent splits at 1 September 2024 are diagnostics only. These EAs and the shortlist were selected retrospectively; neither split is a genuinely untouched out-of-sample validation.',
       '- FTMO is used only as a tick-data source at the user\'s request. The 18 September XAUUSD sample request returned zero ticks. None of these results is a new native FTMO tick backtest.',
       '- Normal trades use reconstructed initial cash risk, which is an estimate; News XAU/XAG have explicit $400 stop risk per 1.0 lot. Lots round DOWN to .01; skip if the minimum lot is too large. All costs and size assumptions are in simulate.py.',
       '- Source scenario retains recorded broker spread in fills and recorded commission/swap. It is an optimistic broker-transfer reference, NOT an FTMO cost result.',
       '- Stress scenario reduces normal gross winners by 10%, enlarges gross losers by 10%, and subtracts .02R extra execution cost. News winners are reduced 35%, losers enlarged 25%, plus .15R. Severe uses normal -25%/+30%/.10R; news -60%/+100%/.50R. These are sensitivity assumptions, not measured FTMO slippage distributions.',
       '- Stress commissions are at least $7/lot round trip on metals/FX, $.70/lot on US100; negative recorded swap is doubled and compared with a conservative current-rate carry scenario. Positive swaps are not credited. USDJPY adds the contractual 0.7% realized-P/L conversion adjustment. Carry is posted at exit, so nightly equity-limit effects are not precisely reconstructed.',
       '- Swing margin assumptions: gold 1:15, silver 1:9, US100 1:15, USDJPY 1:30. Margin pricing uses a conservative September price floor and no hedge relief; maximum margin 60% of conservative equity. Contract sizes and current instrument costs still require validation on the actual Swing product.',
       '- Two evaluation phases reset separately; four distinct Prague-calendar entry days in each, no Best Day rule. Allow two business days for phase transition and five for funded activation (planning assumptions, not promised service times). Conservatively stop a phase after 30 days without a new entry; this models contractual suspension/termination risk, not an automatic drawdown breach.',
       '- First reward model: funded profit after trading costs at least $225, leave $100 buffer, distribute the remainder at 80%, request only flat with no reserved orders and at least 14 days after the first funded trade; add four business days for processing. Taxes, payout currency conversion, transfer fees, and challenge-fee refunds excluded from modeled reward.',
       '- Trades crossing the horizon remain open, rather than being removed using future exit information. Stops are not artificially closed at profit targets; the model waits for native exits.',
       '- Major limitation: saved deals do not contain continuous floating equity or original stops for all EAs. Stop envelopes are diagnostics, not real mark-to-market equity. Zero recorded-close breaches DOES NOT mean zero real breach probability. News reservations begin at first recorded fill, not original pre-release placement; never-filled events have no trade records. This further limits the conditional-news comparison.',
       '', '## EA shortlist', '',
       'All seven use their saved entry/exit settings. Up to 0.50% ($50) per ordinary trade INCLUDING the modeled cost reserve, then 0.25% funded. Figures below are recomputed from closed trades in the common window; breakevens count in the win-rate denominator. PF is equal-risk-normalized after stress, not the original compounded cash PF.',
       '', '| EA / mode | Trades | Source net win rate | Stressed equal-risk PF |',
       '|---|---:|---:|---:|']
for key in chosen['keys']:
    r=next(x for x in screen if x['key']==key)
    a,b=r['full_source'],r['full_stress']
    lines.append(f"| {key} | {a['trades']} | {a['win_rate']:.1f}% | {b['pf']:.2f} |")
lines += ['', 'The first five have positive stressed expectancy in both diagnostic subperiods. H1 ORB and EMA3 Safe improve activity/diversification but were negative in the earlier stressed subperiod: they are conditional candidates requiring forward validation, not uniformly robust winners.',
          '', 'RSI VWAP is not core merely because of its high win rate: stressed equal-risk PF is about 1.01. Nasdaq Overnight, DMC Current, standard LTA, and Nasdaq 5M fail this cost-resilience screen. No martingale/recovery grid. BTC/ETH are not supported in this comparison; do not infer that their spectacular cached returns transfer to low-leverage Swing.',
          '', '## Two-month account results', '',
          'Median ending balance includes any stage resets; it is NOT cash income. All probabilities in these tables are historical-window frequencies, not forecasts.',
          '', '| Combination | Scenario | Median closed trades / 60d | Median balance | Funded by day 30 | Funded by day 60 | Reward >=$100 by day 60 |',
          '|---|---|---:|---:|---:|---:|---:|']
names=['Core balanced','Diversified faster','Robust five','Robust seven','Robust seven faster','Robust seven plus conditional XAU']
for r in results:
    if r['name'] not in names or r['severity']=='severe':continue
    a=r['full']
    lines.append(f"| {r['name']} | {r['severity']} | {a['median_trades']:g} | ${a['median_balance']:,.0f} | {a['funded30']:.1f}% | {a['funded60']:.1f}% | {a['payout60']:.1f}% |")
lines += ['', 'Recommended seven-EA model: 0/251 windows funded by day 30, and 0/251 delivered the modeled first reward by day 60. The 1,000 whole-window resamples also produced zero successes for those deadlines. This does not prove the true probability is zero; no calibrated real-world percentage can be given from these data.',
          '', '## Risk sensitivity: recommended seven', '',
          '| Scenario | Median balance at 60d | Worst closed-balance drawdown across windows | Maximum daily initial-stop envelope loss | Recorded-close breaches |',
          '|---|---:|---:|---:|---:|']
for r in results:
    if r['name']!='Robust seven':continue
    a=r['full']
    lines.append(f"| {r['severity']} | ${a['median_balance']:,.0f} | {a['max_closed_dd']:.2f}% | ${a['max_stop_envelope_daily_loss']:,.0f} | {a['breach60']:.1f}% |")
lines += ['', 'Do not use the last column as real account safety odds: intratrade equity, gaps beyond assumed stress, stale feeds, manual orders, forbidden-practice decisions, and actual FTMO fills are not represented.',
          '', '## Longer-horizon context', '',
          '| Portfolio | Scenario | Days allowed | Funded | First reward | Inactivity stop | Median funding days among successes only |',
          '|---|---|---:|---:|---:|---:|---:|']
for r in extended:
    if r['name'] not in ['Robust seven','Robust seven faster','Robust seven plus conditional XAU']:continue
    med=r['median_funded_days_if_funded']
    lines.append(f"| {r['name']} | {r['severity']} | {r['horizon']} | {r['funded_by_horizon']:.1f}% | {r['payout_by_horizon']:.1f}% | {r['inactivity_by_horizon']:.1f}% | {round(med) if med is not None else '-'} |")
lines += ['', 'These longer-horizon diagnostics include the public evaluation inactivity rule but not a future client-specific funded agreement, discretionary compliance review or KYC rejection. They are not a reason to buy a challenge or assume waiting guarantees success.',
          '', '## Proposed risk policy (not installed)', '',
          '| Control | Evaluation | Funded / first reward |',
          '|---|---|---|',
          '| Ordinary per-trade all-in planned budget | Up to .50% / $50 | Up to .25% / $25 |',
          '| Combined open positions plus pending risk | $150 maximum including cost reserve | $150 hard ceiling; normally much lower |',
          '| Correlated symbol/metal group | $100 total, never a separate allowance per EA | Same ceiling |',
          '| Entry throttle | At most 4 new filled positions/day; stop new entries after 3 losing closes or $150 closed daily loss | Same |',
          '| Prospective daily loss | Reject entry if daily closed loss + open/pending stress envelope would exceed $200 | Same |',
          '| Equity safeguard for implementation | Cancel pending and request flatten at $200 daily EQUITY loss or $9,400 equity; execution can overshoot | Same |',
          '| Drawdown/streak taper | Halve budget after 4% closed drawdown or 3 consecutive EA losses; never double to recover | Same |',
          '| Minimum lots | Round DOWN; skip oversized minimum lot. Never the current round-up/always-trade override | Same |',
          '| Margin | Maximum 60% conservative equity; reserve room for both news sides if approved | Same |',
          '| Session clock | Europe/Prague with DST, including overnight floating P/L and fees | Same |',
          '', 'The replay tests entry throttles and endpoint balance rules. The proposed live equity flattening safeguard is NOT simulated because a continuous equity path is missing. Do not describe it as already implemented or proven.',
          '', 'News Pulse XAU is OPTIONAL ONLY after exact strategy permission and clean FTMO tick validation. Proposed maximum .25%/$25 per side, .50%/$50 per event, both sides charged to shared limits; no adaptive bypass. XAG/BTC and Gold News V9 stay out initially. The news model is illustrative, not deployment authorization.',
          '', '## Official rules checked', '',
          '- [2-Step objectives](https://ftmo.com/en/trading-objectives/): 10% phase-one and 5% phase-two targets, four separate entry days per phase, 5% initial daily loss allowance and static 10% total loss. Limits apply to equity including floating P/L, swaps and commissions. Daily reset is 00:00 CE(S)T. No evaluation time limit.',
          '- [Consistency](https://ftmo.com/en/faq/do-you-have-any-consistency-rules/): no additional consistency requirement beyond applicable objectives and sustainable risk management. The 50% Best Day Rule belongs to 1-Step, not this 2-Step plan. No published fixed daily trade quota or universal per-trade percentage is assumed; our tighter limits are our policy.',
          '- [Swing](https://ftmo.com/en/faq/ftmo-swing-account-type/): select Swing at purchase, only with 2-Step. Standard cannot later convert to Swing. News, overnight and weekend holding are allowed, subject to forbidden practices.',
          '- [Gold leverage update](https://ftmo.com/en/blog/trading-updates/trading-update-2-feb-2026/): gold Swing leverage changed from 1:9 to 1:15. Do not apply FX 1:30 to every asset.',
          '- [Reward](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/): 80% initial 2-Step share, claim from day 14 after first funded trade, flat/no pending orders. Review and sending each typically need 1-2 business days. Challenge profits are not withdrawable rewards.',
          '- [Fee](https://ftmo.com/faq/why-is-there-a-fee/): one-time fee covers both evaluation stages; refund is tied to a qualifying first reward, not merely passing. Use actual checkout fee/tax/currency, not an old screenshot.',
          '- [EAs](https://ftmo.com/en/faq/which-instruments-can-i-trade-and-what-strategies-am-i-allowed-to-use/): allowed if legitimate and live-replicable; third-party identical strategies may create allocation issues. Avoid platform hyperactivity and the 200 concurrent-order limit.',
          '- [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/): no delay/error exploitation, manipulative cross-account hedging, overexposure, or prohibited gap trading; >2,000 daily requests can cause sanctions. Swing news permission is not blanket approval of our T-minus-15-second two-sided straddle. Obtain written clarification before relying on that bot.',
          '- [Identity](https://ftmo.com/en/faq/when-do-i-complete-ftmo-identity/): verification follows the two successful stages. Allow time for review, KYC, agreement and account setup; no guaranteed date.',
          '- [Eligibility](https://ftmo.com/en/faq/who-can-join-ftmo/): 18+, eligibility and sanctions checks apply. Tunisia is not in the currently published excluded-country list; local payment/tax rules and final approval still need checking.',
          '', 'The 22-page Global Challenge Terms, updated 4 August 2026, were also read. Clause 5.8.4 requires activation within 30 calendar days; suspension can be renewed on request within six months. Clause 13.2.3 permits termination after 30 days without a new trade, or more than 30 days spent in an 8%-10% loss; artificial trades to circumvent the latter are not acceptable. Clause 7.6 permits individually imposed risk, volume, leverage and consistency restrictions. Clause 5.3.4 adds a 0.7% realized-P/L conversion adjustment for differing P/L and account currencies. Clause 12 makes the first trade relevant to losing the 14-day withdrawal right. Passing numerical targets does not guarantee acceptance. The future funded-account agreement must still be reviewed. Source: FTMO-global-terms-source.pdf in this folder, downloaded from the official Terms page.',
          '', '## Practical timeline', '',
          'Assume trading begins Monday 21 September 2026. The tests use 30/60 elapsed calendar days (21 October / 20 November checkpoints), not a promise to finish by those dates. First validate FTMO tick coverage and run the shortlisted bots unchanged with target Swing contract settings. Confirm broker time mapping, margin, symbol names, commissions, rollover, stop/freeze distances, duplicate-EA prevention and portfolio-level guard persistence. Forward-test on a $10K Swing demo for at least 10 trading days before paying on the expectation that this setup works.',
          '', 'After phase one, stop trading and wait for Verification credentials; after phase two, complete KYC/agreement. On funded, lower risk to $25 and target a modest first qualifying reward. Example: $225 net funded profit, retain $100, distribute $125, trader share $100 before tax/transfer costs. The challenge-fee refund is separate and conditional.',
          '', 'If October ends without passing, do not increase risk to chase the calendar. There is no evidence-supported two-month income promise here.',
          '', '## Verification', '',
          'Nine focused tests pass: no dropping trades crossing the horizon; no oversized minimum-lot forcing; four trading days are not four same-day trades; phase/reward delays; daily entry limit; three-loss stop; Prague summer/winter midnight; rollover triple-day and business-day counting; inactivity is not unlimited free waiting. The deeper review also separated source-broker costs from assumed FTMO stress and marked the missing intratrade-equity evidence.',
          '']
(OUT/'PLAN.md').write_text('\n'.join(lines),encoding='utf-8')
print(OUT/'PLAN.md')
