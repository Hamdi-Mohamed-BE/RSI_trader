# Nasdaq 5M DI added to the US100 ORB comparison

Research only — 27 September 2026. No live setup, EA, BAT, website or account changed.

## Scope and frozen method

M adds Claude's verified Nasdaq 5M Momentum DI version to the previous eight-EA research basket. M50/M33 also add one of the new US100 M15 ORBs; the two new ORB targets are alternatives, never traded together.

Claude version: DI agreement ON, period 14; EMA12; 09:30 New York M5 signal; fixed 2.5R target; ATR trailing, breakeven and dynamic trailing OFF. This is not the experimental wider-stop/ATR version. Nasdaq Overnight remains a separate EA.

Historical comparison: 4 March–30 August 2026, $10,000 start, 180 calendar days / 128 weekdays. This is the existing matched portfolio window, NOT the newer March–September standalone ORB window.

Evidence: saved native Exness real-tick MT5 ledgers with 150 ms delay, revalidated and replayed under one shared controller. No new MT5 run, optimization, live trading, or native FTMO combined-account test. New work is the shared-account replay and 6,000 matched Monte Carlo paths (three portfolios, two cost cases, 1,000 each).

Ordinary risk ceiling $71.43 per trade; news $10 per pending side. Both news sides remain reserved. Daily admission $300, aggregate initial risk $225, correlated-metal/per-symbol risk $150, projected buffer $9,200, max seven entries/day, admission stop after three closed losses, strict 0.01-lot rounding down, 80% margin ceiling and modeled 1:15 instrument leverage. Existing strategies retain priority on simultaneous admissions.

Reference costs retain native fills and commission floors. Stress is the same hypothetical sensitivity: gross wins −10%, gross losses +10%, extra Nasdaq cost 2 points, ordinary gold $0.20, gold news $1, silver $0.04, doubled negative swap/carry. These are NOT measured FTMO execution costs.

## Continuous shared-account results

Cash figures are trading P&L, not payouts. Closed DD uses realized balance; reserve DD includes a modeled open-stop reserve and is NOT actual combined intratrade equity DD.

### Stressed costs

| Portfolio | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD proxy | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Eight EAs | 237 | 39.50 | 1.85 | +$3,411.28 | 34.11% | 70.04% | 2.17 | 3.11% | 4.51% | 12/3 |
| Eight + Nasdaq 5M DI | 315 | 52.50 | 2.46 | +$2,879.08 | 28.79% | 60.95% | 1.41 | 7.33% | 8.99% | 9/6 |
| Eight + ORB 0.50R | 358 | 59.67 | 2.80 | +$2,430.49 | 24.30% | 68.99% | 1.39 | 4.09% | 6.11% | 15/5 |
| Eight + ORB 0.50R + Nasdaq 5M DI | 60 | 10.00 | 0.47 | −$763.07 | -7.63% | 56.67% | 0.54 | 8.82% | 8.93% | 7/5 |
| Eight + ORB 1/3R | 362 | 60.33 | 2.83 | +$2,786.24 | 27.86% | 72.38% | 1.52 | 4.19% | 5.94% | 16/5 |
| Eight + ORB 1/3R + Nasdaq 5M DI | 419 | 69.83 | 3.27 | +$2,220.31 | 22.20% | 64.44% | 1.24 | 7.70% | 9.04% | 12/7 |

### Reference costs

| Portfolio | Trades | /30 days | /weekday | Net USD | Return | Win rate | PF | Closed DD | Reserve DD proxy | Max W/L |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Eight EAs | 239 | 39.83 | 1.87 | +$4,954.71 | 49.55% | 70.29% | 3.00 | 2.06% | 3.02% | 12/3 |
| Eight + Nasdaq 5M DI | 322 | 53.67 | 2.52 | +$5,362.01 | 53.62% | 61.80% | 1.87 | 5.07% | 6.41% | 9/5 |
| Eight + ORB 0.50R | 362 | 60.33 | 2.83 | +$4,604.29 | 46.04% | 68.51% | 1.83 | 2.89% | 4.27% | 16/4 |
| Eight + ORB 0.50R + Nasdaq 5M DI | 433 | 72.17 | 3.38 | +$5,068.50 | 50.69% | 62.59% | 1.56 | 5.35% | 6.58% | 12/5 |
| Eight + ORB 1/3R | 363 | 60.50 | 2.84 | +$4,844.65 | 48.45% | 71.90% | 2.04 | 3.02% | 4.16% | 16/4 |
| Eight + ORB 1/3R + Nasdaq 5M DI | 436 | 72.67 | 3.41 | +$5,089.51 | 50.90% | 64.68% | 1.62 | 4.41% | 5.64% | 13/5 |

## Conditional FTMO milestones — stressed costs

1,000 matched paths per case. These frequencies are conditional on resampling 26 selected historical weeks, not calibrated future probabilities. Existing news and DI selection overlap this history.

| Portfolio | Funded 30d | Paid 60d | Paid 120d | Funded 180d | Paid 180d | Breached before reward | Internal buffer touched | Median paid days* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Eight EAs | 0.9% | 3.4% | 48.3% | 94.0% | 88.1% | 0.0% | 1/1000 | 114.6 |
| Eight + Nasdaq 5M DI | 3.6% | 6.6% | 41.6% | 73.5% | 64.5% | 0.0% | 326/1000 | 105.7 |
| Eight + ORB 0.50R | 0.8% | 2.8% | 37.1% | 81.5% | 71.0% | 0.0% | 119/1000 | 115.9 |
| Eight + ORB 0.50R + Nasdaq 5M DI | 3.6% | 6.3% | 30.8% | 53.7% | 43.1% | 0.0% | 582/1000 | 94.0 |
| Eight + ORB 1/3R | 0.7% | 3.4% | 42.3% | 86.0% | 76.8% | 0.0% | 89/1000 | 113.8 |
| Eight + ORB 1/3R + Nasdaq 5M DI | 3.5% | 6.6% | 32.7% | 58.6% | 48.3% | 0.0% | 541/1000 | 98.7 |

*Median only among paths receiving a reward within 180 days. Unfinished/risk-blocked paths are not counted as blown. Zero modeled breaches is not zero real risk.

## Nasdaq 5M contribution and full-basket change — stress

| Portfolio | DI trades | DI win rate | DI PF | DI net | Whole-basket profit change | 180d payout change |
|---|---:|---:|---:|---:|---:|---:|
| Eight + Nasdaq 5M DI | 88 | 37.50% | 0.88 | −$486.00 | −$532.20 | -23.6 pp |
| Eight + ORB 0.50R + Nasdaq 5M DI | 13 | 15.38% | 0.10 | −$759.76 | −$3,193.56 | -27.9 pp |
| Eight + ORB 1/3R + Nasdaq 5M DI | 88 | 37.50% | 0.88 | −$486.00 | −$565.93 | -28.5 pp |

Marginal portfolio effects differ from the DI EA's own P&L because shared limits may block or displace other trades.

## Monthly cash P&L — stress

| Month | Eight | +DI | +ORB 0.50R | +ORB 0.50R +DI | +ORB 1/3R | +ORB 1/3R +DI |
|---|---:|---:|---:|---:|---:|---:|
| 2026-03 | +$213.99 | −$200.24 | −$52.50 | −$763.07 | +$217.76 | −$297.27 |
| 2026-04 | +$264.54 | −$109.69 | +$522.40 | +$0.00 | +$690.65 | +$248.62 |
| 2026-05 | +$323.18 | +$504.09 | −$49.56 | +$0.00 | −$79.75 | +$230.73 |
| 2026-06 | +$805.78 | +$1,117.73 | +$695.47 | +$0.00 | +$541.20 | +$898.24 |
| 2026-07 | +$1,500.99 | +$1,461.62 | +$1,139.67 | +$0.00 | +$1,463.93 | +$1,359.94 |
| 2026-08 | +$302.80 | +$105.57 | +$175.01 | +$0.00 | −$47.56 | −$219.95 |

March and August are partial months. No withdrawals modeled in continuous-account figures.

### Why the 0.50R + DI stress case only has 60 trades

Its final admitted positions closed on 26 March, leaving $9,236.93. The projected $9,200 internal safety buffer then rejected 375 ordinary entries and 24 news-basket admissions over the replay; additional minimum-lot/margin gates also applied. No later trade was admitted. This is a risk-blocked historical path, not an FTMO breach or a six-month uninterrupted trading result. The low 0.47 trades/weekday average includes the subsequent inactive months. Monte Carlo paths reorder joint weeks, so their results need not match this single chronological path.

## Limits

- Same FTMO research model: 10%/5% phase targets, four trading days per phase, 5% daily and 10% static loss; Prague reset. Review delays two business days between phases and five to funded; reward eligibility after 14 days, flat and $25 profit, receipt four business days later, 80% share. Administrative delays are assumptions.
- Stop-reserve DD cannot establish actual daily-equity compliance. Gaps, outages, margin rules and stop slippage can exceed assumptions. No disqualification probability is modeled.
- The unmodified DI build retried failed session closes on 6 March and carried a trade to 8 March. Those outcomes remain in the ledger. Its broker-session exit handling needs review before deployment.
- New ORB 0.50R also has a retained July market-closure hold. Fixed-time exit requests cannot execute during closed markets.
- Selected/fitted history is not out-of-sample validation. Weekly resampling does not preserve future macro-release calendars. Outcomes stop at first reward request or 180 days, not lifetime account survival.
- Shared-controller skipped trades may change subsequent EA state; the saved-ledger overlay does not recreate this feedback. Pending news gross-margin reservations are conservative model rules, not verified FTMO order checks.
- News-straddle permission needs clarification under prohibited gap-trading practices. Nothing deployed or promoted.

## Evidence

FROZEN.json stores versions, settings and input hashes before replay. RESULTS.json retains controls, new historical ledgers and all 6,000 compact paths. CHECKS.json verifies old controls, exact nine-EA reproduction, cash/risk/funnel consistency and unchanged source hashes.

- [FTMO objectives](https://ftmo.com/en/comparison-table/)
- [FTMO prohibited practices](https://ftmo.com/en/forbidden-trading-practices/)
