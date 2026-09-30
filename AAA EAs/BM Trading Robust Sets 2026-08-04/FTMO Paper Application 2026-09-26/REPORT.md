# Which paper works best for our FTMO case?

26 September 2026 — $10,000, one FTMO 2-Step Swing account. Research only.

## Conclusion

**Paper 3 is the best modeling foundation, not a proven trading strategy.** Combine its contract-specific barriers with fixed dollar risk (a useful lesson from paper 1), and report both funding and actual cash receipts (paper 2). We did not replicate all three papers as if they were EAs.

These tests do not establish a reliable one-month funded / two-month paid plan. The news portfolios win on fitted history, but that is not independent evidence of an 80% future payout chance. Non-news rankings change with the source period and costs.

## What was actually run

112,000 path-horizon evaluations: 28 portfolio/pool/cost cases × 4 calendar horizons × 1,000 jointly resampled paths. These are correlated comparisons sharing random draws, NOT 112,000 independent historical samples. Original MT5 ledgers end 30 August 2026. No new MT5 tester runs or live-account queries were made.

Recent pool: 26 weeks (2 March–30 August 2026). Longer non-news pool: 101 weeks (23 September 2024–30 August 2026). Both have previously researched strategies; neither is a pristine untouched holdout.

## Paper fit

| Paper | Useful contribution | Why its headline result is not our forecast |
|---|---|---|
| 1. Inherent Value / fixed-size | Consistent sizing and full fee/payout cash accounting | Random-direction MNQ, Topstep rules, repeated purchases over ten years; not our one FTMO account. A code-review concern was that its entry minute is skipped when checking exits. |
| 2. Price of a Funded Account | Separates passing, first payout and contract value | Gaussian daily P&L and daily-close checks do not capture our intraday/news gaps. Its illustrative evaluation deadlines differ from unlimited FTMO evaluation. Daily volatility of 2% is not risk of 2% per trade. |
| 3. Valuing evaluation contracts | Models static vs trailing barriers, timing, daily limits and economic value | Best framework, but still needs our actual fills, dependence, contract and costs; its published pass probabilities are not our EA probabilities. |

## First payout receipt: matched recent pool, stressed execution

All percentages below are conditional simulation frequencies, not validated real-world probabilities. Ordinary risk is fixed initial dollars; news always $10 per side. Both pending news orders are retained.

| Portfolio | 30d paid | 60d paid | 120d paid | 180d paid | 180d funded | 180d unfinished |
|---|---:|---:|---:|---:|---:|---:|
| Five EAs / $50 | 0.0% | 0.0% | 0.8% | 4.2% | 8.2% | 95.8% |
| Five EAs / $71.43 | 0.0% | 0.0% | 3.4% | 9.0% | 14.9% | 91.0% |
| Eight EAs / $50 | 0.0% | 0.0% | 0.6% | 5.2% | 8.4% | 94.8% |
| Eight EAs / $71.43 | 0.0% | 0.0% | 3.3% | 8.2% | 13.8% | 91.8% |
| Eight EAs / $100 | 0.0% | 0.2% | 3.1% | 6.3% | 11.7% | 93.7% |
| Raw Gold / $71.43 | 0.0% | 0.0% | 0.0% | 1.2% | 3.4% | 98.8% |
| Raw Gold + news / $71.43 + $10 | 0.0% | 2.0% | 35.7% | 78.5% | 88.2% | 21.5% |
| High-win + news / $71.43 + $10 | 0.0% | 3.5% | 39.6% | 80.4% | 88.8% | 19.6% |

Unfinished is not breached: it includes evaluation still running and funded accounts that have not received their first reward. All cells produced zero hard breaches under the modeled gates. That is not evidence of zero real breach risk: floating equity is only a stop-loss reserve, and gaps/platform failures are not bounded by it.

## Source-period and cost sensitivity: first payout by 180 days

| Portfolio | Recent reference | Recent stress | Longer reference | Longer stress |
|---|---:|---:|---:|---:|
| Five EAs / $50 | 10.0% | 4.2% | 30.8% | 8.0% |
| Five EAs / $71.43 | 24.5% | 9.0% | 42.6% | 11.8% |
| Eight EAs / $50 | 13.6% | 5.2% | 35.9% | 8.8% |
| Eight EAs / $71.43 | 26.8% | 8.2% | 47.5% | 13.9% |
| Eight EAs / $100 | 23.3% | 6.3% | 59.5% | 18.8% |
| Raw Gold / $71.43 | 7.6% | 1.2% | 0.0% | 0.0% |
| Raw Gold + news / $71.43 + $10 | 95.9% | 78.5% | Not enough news coverage | Not enough news coverage |
| High-win + news / $71.43 + $10 | 97.1% | 80.4% | Not enough news coverage | Not enough news coverage |

The news combinations cannot be assigned comparable longer-pool estimates without inventing missing events. Adding more EAs or increasing risk does not reliably improve the result.

## Actual chronology: 4 March–30 August 2026, stressed, continuous account

A fixed $10K account without evaluation phase resets or payouts. Shared risk/margin gates still apply. This is a saved-ledger replay, not a new native FTMO backtest. Return is not cash income.

| Portfolio | Closed trades | Trades/week | Net return | Win rate | PF | Closed-balance DD | Stop-reserve DD | Max W/L streak |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Five EAs / $50 | 100 | 3.89 | 2.02% | 36.0% | 1.08 | 9.58% | 11.24% | 4/13 |
| Five EAs / $71.43 | 99 | 3.85 | 2.93% | 36.4% | 1.08 | 12.46% | 14.27% | 4/13 |
| Eight EAs / $50 | 120 | 4.67 | 3.24% | 36.7% | 1.10 | 8.57% | 10.25% | 4/8 |
| Eight EAs / $71.43 | 115 | 4.47 | 0.23% | 35.7% | 1.01 | 14.12% | 15.97% | 4/15 |
| Eight EAs / $100 | 70 | 2.72 | -7.67% | 31.4% | 0.80 | 14.52% | 14.65% | 4/14 |
| Raw Gold / $71.43 | 97 | 3.77 | 8.21% | 74.2% | 1.71 | 2.65% | 4.15% | 11/3 |
| Raw Gold + news / $71.43 + $10 | 124 | 4.82 | 30.38% | 71.0% | 2.82 | 2.25% | 3.50% | 11/3 |
| High-win + news / $71.43 + $10 | 196 | 7.62 | 32.42% | 69.9% | 2.05 | 3.11% | 5.54% | 8/3 |

Peak-to-trough drawdown can exceed 10% without violating a static 10%-of-initial-capital loss floor; do not conflate these quantities. The stop-reserve drawdown is not measured tick-equity drawdown.

## Cash economics: 180 days, recent pool, stress

First reward only; 80% trader share already applied. $100 fee is an illustration, NOT an FTMO checkout quote. Assume fee refunded with first reward. Net cash = mean received reward − fee × (1 − payout probability). Unfinished accounts retain possible future value; taxes, VPS and currency conversion are excluded.

| Portfolio | Median reward if paid | Mean reward per initial purchase | Net cash using $100 fee | Fee break-even by this horizon | 95% MC interval for receipt |
|---|---:|---:|---:|---:|---:|
| Five EAs / $50 | $205.17 | $8.20 | $-87.60 | $8.56 | 3.1–5.6% |
| Five EAs / $71.43 | $211.99 | $21.41 | $-69.59 | $23.52 | 7.4–10.9% |
| Eight EAs / $50 | $148.87 | $8.96 | $-85.84 | $9.45 | 4.0–6.8% |
| Eight EAs / $71.43 | $225.74 | $20.88 | $-70.92 | $22.75 | 6.7–10.1% |
| Eight EAs / $100 | $152.65 | $14.61 | $-79.09 | $15.59 | 5.0–8.0% |
| Raw Gold / $71.43 | $72.63 | $1.12 | $-97.68 | $1.13 | 0.7–2.1% |
| Raw Gold + news / $71.43 + $10 | $148.69 | $192.33 | $170.83 | $894.55 | 75.8–80.9% |
| High-win + news / $71.43 + $10 | $160.37 | $201.86 | $182.26 | $1,029.91 | 77.8–82.7% |

Monte Carlo intervals describe randomness in drawing paths from the same small dataset only. They do not cover parameter fitting, future market behavior, missing intraday equity or payout eligibility. Zero observed outcomes in 1,000 paths does not establish mathematical impossibility.

## Actual chronological challenge outcome

| Portfolio | Funded | First reward received | Reward amount | Request date | Receipt date |
|---|---|---|---:|---|---|
| Five EAs / $50 | False | False | $0.00 | — | — |
| Five EAs / $71.43 | False | False | $0.00 | — | — |
| Eight EAs / $50 | False | False | $0.00 | — | — |
| Eight EAs / $71.43 | False | False | $0.00 | — | — |
| Eight EAs / $100 | False | False | $0.00 | — | — |
| Raw Gold / $71.43 | False | False | $0.00 | — | — |
| Raw Gold + news / $71.43 + $10 | True | True | $317.07 | 2026-07-23T14:08:41+00:00 | 2026-07-29T14:08:41+00:00 |
| High-win + news / $71.43 + $10 | True | True | $266.20 | 2026-07-23T14:08:41+00:00 | 2026-07-29T14:08:41+00:00 |

## Portfolio membership

### Five EAs / $50

xau-squeeze-momentum-standard/standard, usdjpy-london-open-momentum/standard, xau-trend-progression/standard, us100-orb-new-york-m30/standard, xau-elliott-wave-1-2-3/standard

### Five EAs / $71.43

xau-squeeze-momentum-standard/standard, usdjpy-london-open-momentum/standard, xau-trend-progression/standard, us100-orb-new-york-m30/standard, xau-elliott-wave-1-2-3/standard

### Eight EAs / $50

usdjpy-london-open-momentum/standard, xau-trend-progression/standard, xau-squeeze-momentum-standard/standard, us100-selective-orb-v3/standard, orb-volume-profile/safe, eth-top-down-fvg-liquidity/safe, xau-elliott-wave-1-2-3/standard, us100-orb-new-york-m30/standard

### Eight EAs / $71.43

usdjpy-london-open-momentum/standard, xau-trend-progression/standard, xau-squeeze-momentum-standard/standard, us100-selective-orb-v3/standard, orb-volume-profile/safe, eth-top-down-fvg-liquidity/safe, xau-elliott-wave-1-2-3/standard, us100-orb-new-york-m30/standard

### Eight EAs / $100

usdjpy-london-open-momentum/standard, xau-trend-progression/standard, xau-squeeze-momentum-standard/standard, us100-selective-orb-v3/standard, orb-volume-profile/safe, eth-top-down-fvg-liquidity/safe, xau-elliott-wave-1-2-3/standard, us100-orb-new-york-m30/standard

### Raw Gold / $71.43

gold-overnight-value-area/standard

### Raw Gold + news / $71.43 + $10

gold-overnight-value-area/standard, news-pulse-xau/standard, news-pulse-xag/standard

### High-win + news / $71.43 + $10

gold-overnight-value-area/standard, xau-rsi-vwap/standard, nasdaq-overnight/standard, news-pulse-xau/standard, news-pulse-xag/standard

## Coverage by EA, recent joint pool

| EA | Observed entries |
|---|---:|
| eth-top-down-fvg-liquidity/safe | 9 |
| gold-overnight-value-area/standard | 100 |
| nasdaq-overnight/standard | 56 |
| news-pulse-xag/standard | 17 |
| news-pulse-xau/standard | 20 |
| orb-volume-profile/safe | 17 |
| us100-orb-new-york-m30/standard | 13 |
| us100-selective-orb-v3/standard | 3 |
| usdjpy-london-open-momentum/standard | 66 |
| xau-elliott-wave-1-2-3/standard | 9 |
| xau-rsi-vwap/standard | 32 |
| xau-squeeze-momentum-standard/standard | 7 |
| xau-trend-progression/standard | 11 |

## Risk controls and limitations

Internal settings tested: $300 daily admission budget, $225 simultaneous initial risk, $150 correlated-metal/per-symbol cap, $9,200 internal total buffer, at most seven entries/day and no new entries after three closed losses. Lot sizes round up in 0.01 steps, so actual initial risk can exceed the nominal setting. These are scenario choices, not optimized recommendations.

The simulation includes shared margin and reserves both news sides. It does not re-run skipped-trade effects on every EA state, replay historical bid/ask ticks, model emergency close failure, estimate account disqualification likelihood, or establish long-run funded-account survival after the first reward.

FTMO Swing permits news trading generally, but FTMO also forbids specified gap-trading practices around scheduled news. The exact pre-event two-sided News Pulse method needs written confirmation from FTMO before treating payout eligibility as established. Do not deploy it based on this table.

## Verification

Source hashes match the existing manifest; nine original deterministic engine tests pass, seven additional assertions pass, and eight saved historical result fields reproduce exactly. All 112 outcome cells reconcile, funded probability is at least payout probability, and historical ledgers reconcile to final cash balances. No production imports or MT5 connections were made.

## Sources and complete assumptions

- [FTMO 2-Step comparison](https://ftmo.com/en/comparison-table/)
- [Reward timing and share](https://ftmo.com/en/faq/how-do-i-withdraw-my-profits/)
- [Forbidden trading practices](https://ftmo.com/en/forbidden-trading-practices/)
- [Paper 1](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7514219)
- [Paper 2](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7178078)
- [Paper 3](https://papers.ssrn.com/sol3/papers.cfm?abstract_id=7260819)
- PROTOCOL.md contains full costs, margin assumptions, delays and caveats.
- RESULTS.json contains every outcome, historical trade record and admission counter.
