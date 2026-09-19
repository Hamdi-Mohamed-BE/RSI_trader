# Seven active ORBs — below-1R comparison, latest two months

Window: **19 July–18 September 2026**. Each configuration starts separately with **$10,000** and a **1% current-equity risk input**. This is not a combined portfolio.

## Side-by-side results

Numbers below are uninterrupted strategy results over the window, not a challenge cash balance after a breach or phase reset.

| EA | Current target / return | 0.5R return / win rate | 0.75R return / win rate | Trades: current / 0.5R / 0.75R |
|---|---:|---:|---:|---:|
| XAU ORB Volume Profile | 2.5R / +0.76% | +1.98% / 75.00% | +1.03% / 66.67% | 12 / 12 / 12 |
| XAU ORB Volume Confirmed | 2.5R / +4.70% | +0.51% / 75.00% | +1.42% / 75.00% | 4 / 4 / 4 |
| XAU ORB New York M30 | 1.5R / +0.46% | +1.63% / 75.00% | +0.46% / 50.00% | 4 / 4 / 4 |
| XAU ORB London/NY Overlap M30 | 1R / -0.14% | +1.62% / 83.33% | +0.44% / 33.33% | 6 / 6 / 6 |
| US100 ORB New York M30 | 4R / -0.53% | -0.51% / 50.00% | -0.53% / 50.00% | 2 / 2 / 2 |
| US100 H1 ORB 13UTC | 6R / -0.28% | +1.70% / 80.00% | +2.29% / 70.00% | 10 / 10 / 10 |
| US100 Selective ORB V3 | 2R / +0.21% | +0.21% / 100.00% | +0.21% / 100.00% | 1 / 1 / 1 |

## FTMO rule replay

Of the 14 below-1R configurations, **0 completed both phases**, **0 reached the first-phase objective without an earlier breach**, and **0 breached a modeled loss limit**.

[Official FTMO 2-Step rules, checked 19 September 2026](https://ftmo.com/en/trading-objectives/): +10% Phase 1, +5% Verification, four entry days per phase, $500 daily equity-loss amount and $9,000 static equity floor on a $10K account. Days reset at Prague midnight. No two-month deadline is imposed.

Phase 2, when reached, is a fresh native test at $10K from the next business day. This optimistically assumes no additional administrative handover delay. Phase outcomes use the first target/breach timestamps; a later breach in an uninterrupted comparison does not invalidate an already completed phase.

## Detailed statistics

| EA | Target | Trades | Net wins / losses | WR | Net USD | Net PF | Native max equity DD | Worst daily equity loss | Max initial price risk | Win/loss streak | Challenge outcome |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| XAU ORB Volume Profile | 2.5R (current) | 12 | 4 / 8 | 33.33% | +$76.35 | 1.16 | 3.84% | $124.43 | 1.19% | 3 / 3 | phase1_pending |
| XAU ORB Volume Profile | 0.5R (comparison) | 12 | 9 / 3 | 75.00% | +$198.46 | 1.81 | 2.60% | $114.02 | 1.17% | 8 / 2 | phase1_pending |
| XAU ORB Volume Profile | 0.75R (comparison) | 12 | 8 / 4 | 66.67% | +$103.23 | 1.30 | 2.63% | $114.02 | 1.18% | 4 / 2 | phase1_pending |
| XAU ORB Volume Confirmed | 2.5R (current) | 4 | 2 / 2 | 50.00% | +$469.62 | 5.07 | 1.26% | $113.88 | 1.15% | 2 / 1 | phase1_pending |
| XAU ORB Volume Confirmed | 0.5R (comparison) | 4 | 3 / 1 | 75.00% | +$50.62 | 1.44 | 1.12% | $113.88 | 1.15% | 3 / 1 | phase1_pending |
| XAU ORB Volume Confirmed | 0.75R (comparison) | 4 | 3 / 1 | 75.00% | +$142.11 | 2.25 | 1.11% | $113.88 | 1.16% | 3 / 1 | phase1_pending |
| XAU ORB New York M30 | 1.5R (current) | 4 | 2 / 2 | 50.00% | +$46.40 | 6.95 | 1.51% | $109.00 | 1.17% | 1 / 1 | phase1_pending |
| XAU ORB New York M30 | 0.5R (comparison) | 4 | 3 / 1 | 75.00% | +$162.53 | 25.19 | 1.51% | $109.00 | 1.16% | 3 / 1 | phase1_pending |
| XAU ORB New York M30 | 0.75R (comparison) | 4 | 2 / 2 | 50.00% | +$46.40 | 6.95 | 1.51% | $109.00 | 1.17% | 1 / 1 | phase1_pending |
| XAU ORB London/NY Overlap M30 | 1R (current) | 6 | 1 / 5 | 16.67% | -$13.92 | 0.88 | 1.97% | $110.51 | 1.15% | 1 / 5 | phase1_pending |
| XAU ORB London/NY Overlap M30 | 0.5R (comparison) | 6 | 5 / 1 | 83.33% | +$162.24 | 2.47 | 1.30% | $110.51 | 1.15% | 5 / 1 | phase1_pending |
| XAU ORB London/NY Overlap M30 | 0.75R (comparison) | 6 | 2 / 4 | 33.33% | +$43.99 | 1.39 | 1.31% | $110.51 | 1.15% | 1 / 3 | phase1_pending |
| US100 ORB New York M30 | 4R (current) | 2 | 1 / 1 | 50.00% | -$53.14 | 0.48 | 1.67% | $101.25 | 1.01% | 1 / 1 | phase1_pending |
| US100 ORB New York M30 | 0.5R (comparison) | 2 | 1 / 1 | 50.00% | -$50.84 | 0.50 | 1.67% | $101.25 | 1.01% | 1 / 1 | phase1_pending |
| US100 ORB New York M30 | 0.75R (comparison) | 2 | 1 / 1 | 50.00% | -$53.14 | 0.48 | 1.67% | $101.25 | 1.01% | 1 / 1 | phase1_pending |
| US100 H1 ORB 13UTC | 6R (current) | 10 | 6 / 4 | 60.00% | -$27.59 | 0.91 | 2.24% | $101.78 | 1.04% | 3 / 2 | phase1_pending |
| US100 H1 ORB 13UTC | 0.5R (comparison) | 10 | 8 / 2 | 80.00% | +$170.19 | 1.91 | 1.39% | $104.39 | 1.03% | 5 / 1 | phase1_pending |
| US100 H1 ORB 13UTC | 0.75R (comparison) | 10 | 7 / 3 | 70.00% | +$229.29 | 2.12 | 1.39% | $104.39 | 1.03% | 3 / 1 | phase1_pending |
| US100 Selective ORB V3 | 2R (current) | 1 | 1 / 0 | 100.00% | +$20.65 | no losing trades | 0.64% | $37.41 | 1.01% | 1 / 0 | phase1_pending |
| US100 Selective ORB V3 | 0.5R (comparison) | 1 | 1 / 0 | 100.00% | +$20.65 | no losing trades | 0.64% | $37.41 | 1.01% | 1 / 0 | phase1_pending |
| US100 Selective ORB V3 | 0.75R (comparison) | 1 | 1 / 0 | 100.00% | +$20.65 | no losing trades | 0.64% | $37.41 | 1.01% | 1 / 0 | phase1_pending |

## Costs and monthly results

| EA / target | July partial net | August net | September partial net | Commission total | Swap total |
|---|---:|---:|---:|---:|---:|
| XAU ORB Volume Profile / 2.5R | -$130.58 | +$426.21 | -$219.28 | -$4.44 | +$0.00 |
| XAU ORB Volume Profile / 0.5R | +$93.35 | +$266.11 | -$161.00 | -$4.39 | +$0.00 |
| XAU ORB Volume Profile / 0.75R | +$78.81 | +$156.47 | -$132.05 | -$4.39 | +$0.00 |
| XAU ORB Volume Confirmed / 2.5R | -$1.41 | +$584.91 | -$113.88 | -$1.61 | +$0.00 |
| XAU ORB Volume Confirmed / 0.5R | +$55.30 | +$109.20 | -$113.88 | -$1.55 | +$0.00 |
| XAU ORB Volume Confirmed / 0.75R | +$80.91 | +$175.08 | -$113.88 | -$1.61 | +$0.00 |
| XAU ORB New York M30 / 1.5R | +$0.00 | +$14.65 | +$31.75 | -$1.11 | +$0.00 |
| XAU ORB New York M30 / 0.5R | +$0.00 | +$50.95 | +$111.58 | -$1.11 | +$0.00 |
| XAU ORB New York M30 / 0.75R | +$0.00 | +$14.65 | +$31.75 | -$1.11 | +$0.00 |
| XAU ORB London/NY Overlap M30 / 1R | +$100.80 | -$0.53 | -$114.19 | -$3.26 | +$0.00 |
| XAU ORB London/NY Overlap M30 / 0.5R | +$49.63 | +$54.10 | +$58.51 | -$3.26 | +$0.00 |
| XAU ORB London/NY Overlap M30 / 0.75R | +$75.85 | -$0.53 | -$31.33 | -$3.26 | +$0.00 |
| US100 ORB New York M30 / 4R | +$0.00 | -$101.25 | +$48.11 | -$1.06 | +$0.00 |
| US100 ORB New York M30 / 0.5R | +$0.00 | -$101.25 | +$50.41 | -$1.06 | +$0.00 |
| US100 ORB New York M30 / 0.75R | +$0.00 | -$101.25 | +$48.11 | -$1.06 | +$0.00 |
| US100 H1 ORB 13UTC / 6R | +$14.68 | +$29.18 | -$71.45 | -$3.96 | +$0.00 |
| US100 H1 ORB 13UTC / 0.5R | +$51.07 | +$71.63 | +$47.49 | -$3.99 | +$0.00 |
| US100 H1 ORB 13UTC / 0.75R | +$76.79 | +$50.79 | +$101.71 | -$3.99 | +$0.00 |
| US100 Selective ORB V3 / 2R | +$0.00 | +$0.00 | +$20.65 | -$0.43 | +$0.00 |
| US100 Selective ORB V3 / 0.5R | +$0.00 | +$0.00 | +$20.65 | -$0.43 | +$0.00 |
| US100 Selective ORB V3 / 0.75R | +$0.00 | +$0.00 | +$20.65 | -$0.43 | +$0.00 |

## Known tick-gap exposure

The tester reports two entire days without real ticks: **14 and 15 September 2026**. It generated ticks from bars for those days. The counts below identify entries on those dates; they do not assert that every other minute has complete ticks. No trades are removed from the comparison.

| EA | Entries on full-gap dates: current / 0.5R / 0.75R |
|---|---:|
| XAU ORB Volume Profile | 1 / 1 / 1 |
| XAU ORB Volume Confirmed | 0 / 0 / 0 |
| XAU ORB New York M30 | 0 / 0 / 0 |
| XAU ORB London/NY Overlap M30 | 2 / 2 / 2 |
| US100 ORB New York M30 | 0 / 0 / 0 |
| US100 H1 ORB 13UTC | 1 / 1 / 1 |
| US100 Selective ORB V3 | 0 / 0 / 0 |

## Interpretation and limitations

- Seven configurations came from the active installer: two gold Volume Profile variants, gold New York M30, gold London/NY overlap M30, US100 New York M30, US100 H1 13UTC, and US100 Selective ORB V3. Archived raw research ORBs were not included.
- Entry logic, initial stop logic, breakeven/trailing and session rules are unchanged across each EA's three runs. Only TP RR is changed, with risk input standardized to 1% and the portfolio adaptive overlay disabled.
- The two Volume Profile versions retain Dynamic 50/20 management. It references TP distance: 0.5R brings its trigger to 0.25R and lock to 0.10R; 0.75R brings them to 0.375R and 0.15R. The code evaluates the closed M15 candle; these are thresholds, not guaranteed exit prices.
- These EAs retain the current round-up/minimum-lot sizing policy. Therefore 1% is an INPUT, not a hard risk cap. Actual initial price risk is shown above, and fees/slippage can increase the eventual loss further. This differs from the saved Nasdaq executable, which rounded down.
- All runs use the isolated Exness-MT5Trial16 tester, model 4 (real-tick mode), not the connected FTMO account. MT5 can generate ticks where real ticks are absent; diagnostics are retained per case. A 100% history-quality report is not a certificate of 100% real ticks.
- Spread and historical fill-price gaps are reflected in native fills. Native recorded commission and swap are included in every trade's net P/L. No additional latency/slippage stress was applied (execution delay 0).
- Tester leverage is configured at 1:30, but Exness symbol-specific margin specifications still apply. This is not verified FTMO Swing execution/margin behavior.
- A read-only audit wrapper observes native tester equity before and after strategy tick/timer events. It records floating daily equity losses, Prague-day resets and first rule/target timestamps without changing trade decisions.
- This is a short, user-selected historical window. Ranking the alternatives here is hindsight comparison, not optimization, a passing probability estimate, or evidence of future profitability.
- No production EA, installer/BAT, website, active portfolio or live trade was changed. Research-only sources, case inputs, reports and ledgers were saved.

## Evidence

`results.json` contains all summaries. Each `cases/<case>/` contains its native MT5 HTML report, full inputs, reconciled `trades.json`, `months.json`, `daily-equity.csv` and `tester-journal.txt`. `frozen-plan.json` records the comparison scope. `verification.json` records independent cash/equity reconciliation, unchanged source-set hashes, tick-gap exposure and observed native margin.
