# Frozen standalone prop overlays

Research only. Each of 5 protected variants on 2 symbols is tested separately, not stacked onto the 13-EA live portfolio. Reference data: native last-year fills and each trade's minute equity plus lowest tick equity within each minute. No-stop controls are excluded. Source broker min lots/step are proxies, not confirmed FTMO/FundedNext symbol specifications.

## Profiles

- FTMO $10K **2-Step Swing**: 10% then 5% closed-balance targets; 4 different entry days per phase; 5% daily loss from Prague midnight balance, 10% static total loss; floating P&L and costs included. Simulated handover delays 2 business days after phase 1 and 5 after phase 2 (ours, not promised firm service times). Initial stop-risk caps 0.25% and 0.50%; margin cap 30% of balance at 1:15 index leverage assumption. Swing avoids standard funded news/weekend restrictions.
- FundedNext $5K **Stellar Instant CFD**, not FNL futures: no challenge; funded from day zero. 6% balance-trailing loss floor capped at original capital, including post-withdrawal ratchet. No daily firm loss limit. Risk caps 0.15% and 0.25%, additionally no more than 5% of remaining loss headroom after a 0.2%-capital buffer. Margin cap 30% at 1:5 index leverage. EA addon required; bot eligibility is conditional, not approval from FundedNext.
- Both: floor to source 0.01 lot steps, USTEC minimum 0.05 / US500 0.14; never round up to force a trade. Fixed risk on original capital, further headroom/margin restrictions. One position only; at most 3 realized losses in a firm day. Admission reserve 1.25 x initial stop risk plus 0.05% capital. FTMO stops admitting trades beyond 1.5% daily budget or 2% buffer to total floor; Instant 0.75% daily budget and 0.2% floor buffer, reserve <=20% headroom. These are entry guards, not intratrade forced liquidation overlays. Hard SL comes from the native EA.

## Milestones and withdrawals

FTMO funded payout request after at least 14 calendar days from first funded trade and >=$25 gross, 80% trader share assumption. Instant: request at EOD after 5% cycle growth or after 14 days with >=1%; 70% starting share assumption. Instant withdraws only amount above original capital that still leaves >=3% original capital above the trailing floor; minimum gross withdrawal $50. Paid cash is a modelled reward after split, NOT money received; KYC, rule review, transfer/processor delay and fees not modelled. Fees for purchasing accounts/addons not deducted, so this is not purchase-ROI analysis.

Quick Strike: >=30% of cycle positive net trading profits earned on positions held <=30 seconds is flagged as incompatible for our simulation; not called a drawdown breach. This is a conservative stop, not a prediction of warnings, partial forfeitures or discretionary closure. Negative quick trades are not counted as positive profit.

Source financing included in native cash. Reference round-trip commission floor $0.70 per CFD lot, if native was lower. Reference known-news deduction removes 60% of positive net profit for entry/exit within +/-5min of 29 locally available release timestamps. This is an INCOMPLETE news calendar, not complete compliance validation. Stress adds 10% adverse adjustment to positive/negative gross cash and floating P&L, 1bp entry-notional equivalent cost each round trip, 2bps/day additional financing on overnight holds, and 10% positive-profit deduction outside known news windows (60% inside). These extra stresses are hypothetical sensitivity assumptions, not measured future spreads/financing/unknown-news loss.

Source-cost warning: the native order journal contains many zero-spread bid/ask samples. Logged quotes are duplicated between terminal/agent logs and are not the full tick series, so their median is a diagnostic rather than a representative cost estimate. Real ticks do not certify broker-independent tradability. Native swap metadata is current at each test, not an audited historical financing series. The reference case is therefore a source-feed scenario, not a reliable best estimate of future prop execution. Stress can demonstrate fragility but cannot validate missing target-broker costs.

Rule-source conflict: on the review date the Stellar Instant product page lists index leverage 1:10, while the dedicated help-center leverage article lists 1:5. We retain the stricter 1:5 assumption from the predeclared protocol rather than selecting whichever produces faster payout. Actual checkout/account specifications need written confirmation. These results are labelled conditional on 1:5, not a definitive description of every newly sold Instant account. FTMO's Swing index 1:15 is supported by its official account-explanation article; actual symbol specifications still control.

- https://fundednext.com/cfds/stellar-instant
- https://ftmo.com/en/blog/a-few-answers-to-your-questions/

## Sampling and clocks

Payout threshold clarification: the FTMO model's $25 gross is our conservative bank-transfer assumption, not an official universal minimum. The official page currently states $20 minimum closed profit for bank wire and $50 for crypto. This simulation does not establish crypto-withdrawal eligibility for rewards below that higher threshold. Fourteen full elapsed days is also a conservative timing convention; approval and transfer still take additional time.

500 moving 28-calendar-day entry-block paths with weekly-spaced blocks from the last year, seed 9282601; report 60/120/180 calendar days. Preserve within-block order, zero-trade days and full overnight holds. NY local entry/exit times preserved. Source blocks whose daylight-saving holding duration cannot match destination are excluded from that destination. No Friday trade truncation at block boundary. This conditioning reduces independent sample variety; bootstrap frequencies are scenario frequencies, not independently validated live pass probabilities. Also report actual weekly-start rolling windows and the historical full-year replay. Periods and variants overlap heavily, no holdout or multiple-testing-adjusted inference.

Prague day resets are checked INSIDE overnight event loops, against balance rather than equity. Minute interval minima can straddle a reset by less than a minute and make a boundary check conservative. Maximum equity-DD from the overlay uses minute-observed peaks and intra-minute minima, not a full peak-tick reconstruction; firm floor checks use intra-minute worst equity. Native headline drawdown is MT5's own full equity measure.

Block-boundary implementation: a Friday hold spanning a Monday exchange holiday can last until Tuesday. The next sampled whole block must start after that existing position closes; an incompatible full path is rejected and redrawn (bounded at 10,000 attempts), without inspecting its profit. No open trade is truncated and no simultaneous position is fabricated. Along with DST compatibility this conditions the bootstrap and reduces source variety; synthetic paths are stress scenarios, not literal forecasts of future exchange calendars.

No deployment recommendation solely from a simulated payout; raw pipeline gates, untouched validation, complete target-broker costs/news/calendar/specs and portfolio overlap remain mandatory.

This is an offline position-size overlay, not a fresh native test for each account. It linearly rescales recorded fills and floating paths and uses the realised fill-to-stop distance as unit risk. It does not recreate size-dependent fills, the exact pre-fill quote used for order sizing, margin-tier changes or other EAs' simultaneous exposure. Entry guards can leave an account inactive near a loss buffer without a formal breach; unresolved paths are not successes. Each strategy is standalone, so the results do not establish how adding it affects the existing portfolio.

Official rules checked 2026-09-28:
- https://ftmo.com/en/trading-objectives/
- https://ftmo.com/faq/ftmo-swing-account-type/
- https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/
- https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts
- https://help.fundednext.com/en/articles/11641693-what-is-the-eligibility-criteria-for-my-performance-reward-in-the-stellar-instant-account
- https://help.fundednext.com/en/articles/12439744-what-will-happen-to-the-maximum-loss-limit-after-a-trader-withdraws-from-a-stellar-instant-account
- https://help.fundednext.com/en/articles/11641338-can-i-use-ea-in-stellar-instant
- https://help.fundednext.com/en/articles/11641369-what-is-the-leverage-provided-in-the-stellar-instant-accounts
- https://help.fundednext.com/en/articles/14702484-understanding-the-quick-strike-parameter-on-fundednext
- https://help.fundednext.com/en/articles/11641410-is-news-trading-allowed-in-the-stellar-instant-accounts
