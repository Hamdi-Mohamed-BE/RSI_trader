# FTMO Swing vs FundedNext Stellar Instant — current-EA simulation

Research completed 28 September 2026. No purchases, production changes, live account actions or Git push. This is the approved two-account follow-up, not a new simulation of FundingPips, FNL or every product.

## Decision

Stellar Instant reaches a **small first reward request sooner** in this model. FTMO is the better structural fit for the current multi-EA system and offers larger modeled reward cash, but passage takes much longer. Neither is purchase-ready on this evidence alone: added costs sharply reduce results, target-broker lots and execution are not validated, and this year overlaps prior strategy selection. Do not treat the percentages below as calibrated live probabilities.

The existing-guard FTMO case outperforms the tighter guard proposals on this history. This is not proof that more risk is safer: changed admission caps change which EAs trade. The seven configurations were fixed before this study’s results.

## What was tested

972 audited source trades, 13 EAs, News OFF, common window **2025-09-27 through 2026-09-24** (363 calendar days). Nasdaq uses DI14 + EMA12, 0.60% initial price stop, ATR6 trailing from 1R, no fixed TP. Source orders and fills are from native Exness MT5 research reports; shared equity is reconstructed from M1 prices, not a target-broker native portfolio backtest.

500 paired four-week-block samples per configuration per cost case; 7 configurations × 2 cases = **7,000 modeled paths**. They all reuse the same limited historical evidence. No bootstrap can remove overfitting or invent unseen crash regimes.

Reference costs include published commission assumptions and source negative swaps. Stress worsens gross winners by 10% and losers by 10%, adds adverse fill movement and higher carrying costs, and applies an extra 10% haircut to other Instant winning trades for incomplete news-calendar coverage. This is a hypothetical joint sensitivity, not measured broker slippage.

## First payout-request frequency: all starts in the denominator

Every cell is **reference / stress**. Request eligibility is not approval or money received. Each side is 500 scenarios. 30/60/120/180 mean calendar days, not exact calendar months.

| Configuration | 30 days | 60 days | 120 days | 180 days |
| --- | --- | --- | --- | --- |
| FTMO 0.25% tighter | 0.0% / 0.0% | 0.0% / 0.0% | 0.8% / 0.0% | 24.4% / 0.6% |
| FTMO 0.50% tighter | 0.0% / 0.0% | 0.4% / 0.0% | 22.8% / 4.0% | 55.2% / 10.8% |
| FTMO 0.50% existing guards | 0.0% / 0.0% | 2.4% / 0.0% | 56.8% / 11.8% | 87.0% / 34.4% |
| Instant 0.15% full basket | 70.2% / 15.4% | 92.8% / 39.0% | 99.6% / 61.2% | 99.8% / 72.4% |
| Instant 0.25% full basket | 81.6% / 41.2% | 96.2% / 58.6% | 99.2% / 70.8% | 99.8% / 77.2% |
| Instant 0.25% core4 | 70.8% / 39.8% | 88.2% / 60.4% | 95.2% / 72.0% | 98.6% / 77.2% |
| Instant core4 / withdraw all | 70.8% / 39.8% | 88.2% / 60.4% | 95.2% / 72.0% | 98.6% / 77.2% |


## FTMO stages and timing

Times below are cumulative calendar days from starting the challenge, conditional on reaching the milestone within 180 days. Median (10th–90th percentile), with completing count n out of 500. Different milestones have different successful subsets. Model assumptions add two business days before Verification and five before funded activation; these are not firm promises.

| Case | Phase 1 passed | Phase 2 passed | Funded activation | First request |
| --- | --- | --- | --- | --- |
| FTMO 0.25% tighter / reference | 112.9 (66.7–161.2); n=383 | 147.3 (113.8–172.9); n=200 | 149.0 (119.8–176.0); n=180 | 157.9 (133.4–178.6); n=122 |
| FTMO 0.25% tighter / stress | 140.9 (100.2–172.0); n=83 | 160.7 (143.1–177.5); n=8 | 162.0 (146.3–175.9); n=6 | 177.6 (156.2–177.9); n=3 |
| FTMO 0.50% tighter / reference | 66.7 (33.8–137.6); n=416 | 112.8 (62.1–162.9); n=337 | 116.1 (67.7–164.3); n=327 | 128.6 (85.3–170.8); n=276 |
| FTMO 0.50% tighter / stress | 92.0 (46.6–161.2); n=213 | 128.1 (78.2–166.1); n=90 | 133.8 (84.0–172.0); n=87 | 125.2 (94.1–172.0); n=54 |
| FTMO 0.50% existing guards / reference | 46.8 (28.1–96.7); n=487 | 80.9 (46.9–135.6); n=462 | 87.7 (53.6–137.5); n=457 | 105.9 (70.8–149.9); n=435 |
| FTMO 0.50% existing guards / stress | 80.7 (42.6–147.6); n=347 | 115.7 (72.3–165.2); n=227 | 121.1 (78.8–165.6); n=218 | 133.6 (94.5–169.0); n=172 |


| Case | Verification duration after assumed activation, days |
| --- | --- |
| FTMO 0.25% tighter / reference | 43.1 (24.0–71.1); n=200 |
| FTMO 0.25% tighter / stress | 52.4 (34.5–85.0); n=8 |
| FTMO 0.50% tighter / reference | 29.9 (11.3–77.7); n=337 |
| FTMO 0.50% tighter / stress | 36.0 (16.8–82.5); n=90 |
| FTMO 0.50% existing guards / reference | 24.0 (9.1–59.9); n=462 |
| FTMO 0.50% existing guards / stress | 30.7 (14.1–68.2); n=227 |


No tested FTMO scenario reached a reward request within 30 days. A successful-path median is not an average waiting time for all buyers: many paths remain unfinished at day 180.

## Cash rewards, fees and the Instant trap

USD cash is after the modeled 80% FTMO / 70% Instant split, but before purchase fee, EA add-on, VPS, tax, payment charges and FX. Mean 180-day cash includes zero-reward paths. It excludes account balance gains not withdrawn and the FTMO fee refund.

| Case | Costs | First-request day median (p10–p90); n | Median first cash if paid | Mean total cash by day 180 | No request / still active |
| --- | --- | --- | --- | --- | --- |
| FTMO 0.25% tighter | Reference | 157.9 (133.4–178.6); n=122 | $107.13 | $62.39 | 378 |
| FTMO 0.25% tighter | Stress | 177.6 (156.2–177.9); n=3 | $103.61 | $1.03 | 497 |
| FTMO 0.50% tighter | Reference | 128.6 (85.3–170.8); n=276 | $166.05 | $388.89 | 224 |
| FTMO 0.50% tighter | Stress | 125.2 (94.1–172.0); n=54 | $138.15 | $47.51 | 446 |
| FTMO 0.50% existing guards | Reference | 105.9 (70.8–149.9); n=435 | $267.00 | $1,123.27 | 65 |
| FTMO 0.50% existing guards | Stress | 133.6 (94.5–169.0); n=172 | $174.64 | $185.04 | 328 |
| Instant 0.15% full basket | Reference | 23.6 (14.6–53.0); n=499 | $40.63 | $123.63 | 1 |
| Instant 0.15% full basket | Stress | 58.0 (15.8–141.8); n=362 | $40.56 | $45.22 | 138 |
| Instant 0.25% full basket | Reference | 16.8 (14.6–38.7); n=499 | $53.25 | $151.11 | 1 |
| Instant 0.25% full basket | Stress | 28.9 (14.6–107.0); n=386 | $41.60 | $57.61 | 114 |
| Instant 0.25% core4 | Reference | 17.0 (14.6–63.1); n=493 | $46.36 | $101.61 | 7 |
| Instant 0.25% core4 | Stress | 29.6 (15.6–107.1); n=386 | $39.91 | $47.22 | 114 |
| Instant core4 / withdraw all | Reference | 17.0 (14.6–63.1); n=493 | $46.36 | $138.47 | 7 |
| Instant core4 / withdraw all | Stress | 29.6 (15.6–107.1); n=386 | $39.91 | $51.70 | 114 |


Cost assumptions carried forward from the checked offers: FTMO $10K fee **€89**, refundable with the first qualifying reward; Instant $5K **$104.99 with INSTANT30**, otherwise $149.99, plus an **unverified paid EA add-on**. Reconfirm checkout; no purchase was made. The $25 and $50 add-on columns below are hypothetical sensitivity amounts, not advertised fee quotes. FTMO’s EUR fee is not silently converted into USD.

| Instant case | Costs | Cash ≥$104.99 | Cash ≥$129.99 | Cash ≥$154.99 | Cash ≥$149.99 |
| --- | --- | --- | --- | --- | --- |
| Instant 0.15% full basket | Reference | 282/500 (56.4%) | 187/500 (37.4%) | 108/500 (21.6%) | 121/500 (24.2%) |
| Instant 0.15% full basket | Stress | 2/500 (0.4%) | 0/500 (0.0%) | 0/500 (0.0%) | 0/500 (0.0%) |
| Instant 0.25% full basket | Reference | 366/500 (73.2%) | 279/500 (55.8%) | 209/500 (41.8%) | 224/500 (44.8%) |
| Instant 0.25% full basket | Stress | 5/500 (1.0%) | 4/500 (0.8%) | 1/500 (0.2%) | 1/500 (0.2%) |
| Instant 0.25% core4 | Reference | 166/500 (33.2%) | 84/500 (16.8%) | 40/500 (8.0%) | 47/500 (9.4%) |
| Instant 0.25% core4 | Stress | 0/500 (0.0%) | 0/500 (0.0%) | 0/500 (0.0%) | 0/500 (0.0%) |
| Instant core4 / withdraw all | Reference | 440/500 (88.0%) | 343/500 (68.6%) | 191/500 (38.2%) | 221/500 (44.2%) |
| Instant core4 / withdraw all | Stress | 55/500 (11.0%) | 7/500 (1.4%) | 1/500 (0.2%) | 2/500 (0.4%) |


A $5K Instant account starts with only $300 of formal loss headroom. The proposed policy withdraws only cash that leaves at least $150 above its non-decreasing loss floor. Risk then shrinks with available headroom. Once the floor reaches $5,000, withdrawing the entire profit can breach the account. The all-profit comparison is diagnostic, not recommended. [Official withdrawal examples](https://help.fundednext.com/en/articles/12439744-what-will-happen-to-the-maximum-loss-limit-after-a-trader-withdraws-from-a-stellar-instant-account).

## Breach versus stalled progress

No modeled loss-limit breaches occurred in these 7,000 source-history bootstrap runs or the rolling historical runs. **This does not establish a 0% live blow-up probability.** Admission controls can reject trades, the model cannot recreate all intraminute prices/gaps, and profitable in-sample source blocks do not represent all future market regimes. Synthetic tests deliberately create floating-loss and withdrawal breaches and confirm that the engine catches them.

| Case | Costs | Breach before first request | Breach after request | No entry in last 30 days | Median ending balance minus floor |
| --- | --- | --- | --- | --- | --- |
| FTMO 0.25% tighter | Reference | 0 | 0 | 0 | $1,146.52 |
| FTMO 0.25% tighter | Stress | 0 | 0 | 7 | $1,210.72 |
| FTMO 0.50% tighter | Reference | 0 | 0 | 53 | $997.47 |
| FTMO 0.50% tighter | Stress | 0 | 0 | 172 | $707.95 |
| FTMO 0.50% existing guards | Reference | 0 | 0 | 21 | $1,006.30 |
| FTMO 0.50% existing guards | Stress | 0 | 0 | 126 | $837.13 |
| Instant 0.15% full basket | Reference | 0 | 0 | 0 | $158.13 |
| Instant 0.15% full basket | Stress | 0 | 0 | 0 | $183.03 |
| Instant 0.25% full basket | Reference | 0 | 0 | 0 | $152.69 |
| Instant 0.25% full basket | Stress | 0 | 0 | 0 | $139.86 |
| Instant 0.25% core4 | Reference | 0 | 0 | 0 | $157.59 |
| Instant 0.25% core4 | Stress | 0 | 0 | 0 | $152.25 |
| Instant core4 / withdraw all | Reference | 0 | 0 | 10 | $80.31 |
| Instant core4 / withdraw all | Stress | 0 | 0 | 0 | $145.12 |


Each count is out of 500. No-entry is an inactivity diagnostic, not necessarily permanent failure. Ending balance headroom excludes floating P&L; all modeled breach tests include reconstructed floating equity.

## Historical continuous replay — no phase resets or withdrawals

These are account-equity research returns, not cash payout returns. Maximum equity drawdown uses the within-minute adverse envelope, divided by initial capital. It can exceed 10% while still staying above FTMO’s static loss floor after prior gains. Trades/day uses every Monday–Friday in the common window, including holidays, not only days that traded.

| Case | Costs | Return | Trades | Per weekday | Win rate | PF | Equity DD | Max win/loss streak |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FTMO 0.25% tighter | Reference | +26.34% | 657 | 2.54 | 49.16% | 1.43 | 3.50% | 6/12 |
| FTMO 0.25% tighter | Stress | +7.06% | 657 | 2.54 | 47.95% | 1.10 | 6.24% | 6/12 |
| FTMO 0.50% tighter | Reference | +36.89% | 540 | 2.08 | 49.44% | 1.38 | 10.78% | 8/10 |
| FTMO 0.50% tighter | Stress | +6.83% | 530 | 2.05 | 48.68% | 1.06 | 20.33% | 8/10 |
| FTMO 0.50% existing guards | Reference | +63.37% | 770 | 2.97 | 52.73% | 1.49 | 6.87% | 11/15 |
| FTMO 0.50% existing guards | Stress | +22.98% | 768 | 2.97 | 51.95% | 1.16 | 11.51% | 11/15 |
| Instant 0.15% full basket | Reference | +12.75% | 489 | 1.89 | 50.51% | 1.56 | 1.32% | 10/9 |
| Instant 0.15% full basket | Stress | +1.71% | 487 | 1.88 | 49.28% | 1.07 | 2.74% | 10/8 |
| Instant 0.25% full basket | Reference | +20.27% | 444 | 1.71 | 49.55% | 1.57 | 2.35% | 8/8 |
| Instant 0.25% full basket | Stress | +1.50% | 455 | 1.76 | 48.13% | 1.04 | 4.17% | 9/9 |
| Instant 0.25% core4 | Reference | +14.18% | 369 | 1.42 | 51.22% | 1.50 | 2.43% | 10/9 |
| Instant 0.25% core4 | Stress | +0.94% | 372 | 1.44 | 49.19% | 1.04 | 4.18% | 10/8 |
| Instant core4 / withdraw all | Reference | +14.18% | 369 | 1.42 | 51.22% | 1.50 | 2.43% | 10/9 |
| Instant core4 / withdraw all | Stress | +0.94% | 372 | 1.44 | 49.19% | 1.04 | 4.18% | 10/8 |


## What actually traded

All 13 EAs were offered signals, but position sizing, minimum lots, margin and portfolio risk controls reject many. Lot minimum/step is assumed 0.01 in harmonized source contract units; the target-account values are not confirmed. In particular, do not interpret the Instant full-basket results as proof that its small account can run the complete gold package.

| EA | Source trades | FTMO existing | FTMO tighter 0.50% | Instant full 0.25% | Instant core4 |
| --- | --- | --- | --- | --- | --- |
| xau-rsi-vwap | 47 | 22 | 14 | 0 | 0 |
| gold-overnight-value-area | 199 | 124 | 72 | 0 | 1 |
| xau-squeeze-momentum-standard | 18 | 2 | 1 | 0 | 0 |
| dmc-fresh-reaction-us100 | 11 | 9 | 5 | 8 | 0 |
| ema3 | 42 | 2 | 1 | 0 | 0 |
| xau-trend-progression | 22 | 11 | 7 | 0 | 0 |
| xau-orb-london-ny-overlap-m30 | 25 | 24 | 16 | 13 | 0 |
| nasdaq-overnight | 73 | 52 | 40 | 65 | 69 |
| us100-h1-orb-13utc | 73 | 70 | 27 | 50 | 0 |
| usdjpy-london-open-momentum | 134 | 134 | 116 | 132 | 132 |
| us100-month-end-flow | 34 | 32 | 5 | 17 | 0 |
| dmc-current-xau | 116 | 116 | 110 | 0 | 0 |
| nasdaq-5m-candle-momentum | 178 | 172 | 126 | 159 | 167 |


| Case | lot | margin | risk | daily | loss_stop | phase_wait | same_ea | payout_pause |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| FTMO 0.50% existing guards | 149 | 0 | 7 | 2 | 44 | 0 | 0 | 0 |
| FTMO 0.50% tighter | 156 | 1 | 141 | 120 | 14 | 0 | 0 | 0 |
| Instant 0.25% full basket | 450 | 1 | 1 | 75 | 1 | 0 | 0 | 0 |
| Instant 0.25% core4 | 197 | 0 | 0 | 17 | 1 | 0 | 0 | 0 |


## Actual rolling historical starts — separate from bootstrap

Monday starts, fully observed windows only. There are 48 / 44 / 35 / 26 starts for 30 / 60 / 120 / 180 days. They overlap heavily and are not independent trials. This table reports reference / stress first-request counts.

| Case | 30 days | 60 days | 120 days | 180 days |
| --- | --- | --- | --- | --- |
| FTMO 0.25% tighter | 0/48 / 0/48 | 0/44 / 0/44 | 0/35 / 0/35 | 6/26 / 0/26 |
| FTMO 0.50% tighter | 0/48 / 0/48 | 0/44 / 0/44 | 9/35 / 0/35 | 20/26 / 2/26 |
| FTMO 0.50% existing guards | 0/48 / 0/48 | 1/44 / 0/44 | 29/35 / 0/35 | 26/26 / 14/26 |
| Instant 0.15% full basket | 32/48 / 7/48 | 44/44 / 20/44 | 35/35 / 28/35 | 26/26 / 26/26 |
| Instant 0.25% full basket | 38/48 / 21/48 | 42/44 / 28/44 | 35/35 / 27/35 | 26/26 / 24/26 |
| Instant 0.25% core4 | 34/48 / 20/48 | 39/44 / 26/44 | 34/35 / 26/35 | 26/26 / 23/26 |
| Instant core4 / withdraw all | 34/48 / 20/48 | 39/44 / 26/44 | 34/35 / 26/35 | 26/26 / 23/26 |


## Proposed risk settings and deployment status

| Setting | FTMO existing-guard reference | FTMO tighter proposal | Instant proposal |
| --- | --- | --- | --- |
| Per-entry stop risk cap | $50 | $25 or $50 | $7.50 or $12.50; also ≤5% available headroom |
| Aggregate planned risk | $225 | $150 | Total 1.25R + cost reserves ≤20% available headroom |
| Same-symbol risk | $150 | $75 | ≤10% available headroom |
| Internal daily admission budget | $300 | $150 | $37.50 |
| Margin admission cap | 80% | 30% | 30% |
| New entries/day | 7 | 7 | 7 |
| Stop new entries after losing closes/day | 3 | 3 | 3 |
| Withdrawal buffer | Static floor; modeled profit withdrawn | Static floor; modeled profit withdrawn | $150 above trailing floor retained |
| News Pulse | OFF | OFF | OFF |


Available Instant headroom = min(balance, sampled equity) − current loss floor − $10. Initial trade risks are maxima, not promises of exact realized loss. Reserve adds 1.25× stop risk plus $5 on FTMO / $2.50 on Instant per position. No minimum-lot upsize. These are admission limits, not guaranteed daily maximum losses. Existing-guard exposure is more permissive and must not be called safer because its fitted-year result is better.

Keep each strategy’s tested trade exit, including Nasdaq ATR trailing. Do not add an untested global trailing stop just to obtain an earlier payout. The account trailing-loss floor and an individual trade’s trailing stop are different mechanisms. No new strategy exits were invented here.

## Compatibility and gates before buying

- FTMO Swing supports the overnight/weekend style of this package. Use 2-Step Swing, not a different FTMO product with different rules. [Swing rules](https://ftmo.com/en/faq/ftmo-swing-account-type/).

- Stellar Instant requires the paid EA permission on MT4/MT5 and compliant distinct strategies; Telegram/WhatsApp integrations are prohibited. [EA policy](https://help.fundednext.com/en/articles/11641338-can-i-use-ea-in-stellar-instant).

- News Pulse OFF does not remove news exposure: other bots can open or close around releases. Only 29 saved timestamps were checked; 17 source trades are close to those events. The complete firm calendar must be mapped before claiming compliance. [Instant news treatment](https://help.fundednext.com/en/articles/11641410-is-news-trading-allowed-in-the-stellar-instant-accounts).

- Verify country/residency eligibility, exact checkout price and EA add-on, minimum lots/contract sizes, spread/swap schedules and account agreement. Do not assume the computer timezone proves residency.

- Replay the unchanged package with actual target-account demo specifications, then forward-test. No purchase or live configuration change is justified by these fitted-history probabilities alone.

## Evidence limits and validation

1,075,059 M1 bars; 889,624 per-position path minutes. Max native cash reconciliation error 1.1e-13. Worst source path -2.44R, retained rather than clipped at the initial stop. The Nasdaq example is a weekend gap on an April 2026 trade.

171 automated audit assertions passed, including 13 synthetic rule/accounting tests. All recorded source hashes remain unchanged. The lower-fidelity sampled-equity variant is saved beside the adverse-envelope rolling results in RESULTS.json. Source data, scripts, frozen parameters and all rejected configurations are retained locally.

Read AMENDMENTS.md for timing, partial-minute gaps, absent spread values, swap approximation, conservative withdrawal ratchet, bootstrap boundary distortions and other limitations. Test success proves internal implementation checks, not trading profitability or firm approval.

## Official rule references

- [FTMO 2-Step objectives](https://ftmo.com/en/trading-objectives/): evaluation targets, daily/static loss limits and opening-day requirements.

- [FTMO rewards](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/): request timing and reward share. Actual review and transfer add time after eligibility.

- [Instant loss limits](https://help.fundednext.com/en/articles/11641163-what-are-the-daily-loss-limit-and-the-maximum-loss-limit-for-the-stellar-instant-accounts).

- [Instant reward eligibility](https://help.fundednext.com/en/articles/11641693-what-is-the-eligibility-criteria-for-my-performance-reward-in-the-stellar-instant-account).

- [Instant commissions](https://help.fundednext.com/en/articles/11641300-what-are-the-commission-charges-for-the-stellar-instant-account) and [leverage](https://help.fundednext.com/en/articles/11641369-what-is-the-leverage-provided-in-the-stellar-instant-accounts).

## Bottom line

**For fastest small reward eligibility: Instant. For this existing EA system and larger reward potential: FTMO Swing. For a purchase today based on a guaranteed quick return: neither.** The evidence supports target-broker validation, not a promise of funding next month or a risk-free instant payout.
