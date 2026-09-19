# Gold + Silver News Pulse: $10K Swing research comparison

Research only, 19 September 2026. No BAT, live orders, EA settings or website changes.

## What was tested

- Same seven-EA portfolio and source window as the prior plan: 7 September 2021 to 31 August 2026, end exclusive. 251 overlapping 60-day windows, plus 207 one-year windows. These are retrospectively selected historical replays, not calibrated future probabilities.
- The FTMO XAUUSD tick probe again returned no ticks. Results use saved Exness trades with fixed Swing margin assumptions; not fresh FTMO native tick backtests.
- Both news caches report only 13% real ticks. Older generated ticks and the 1 ms source tester delay are particularly weak evidence for news execution. No claims of deployment readiness.
- Full official-source calendar: 157 releases in the common interval, including releases that produced no fills. Reserve BOTH sides of every enabled symbol at T-30; gold still uses its recorded T-15 entry/fill behavior. Reservations expire at T+60. No assumption that only the winning side needs margin.
- Shared admission is all-or-none across the selected metals. No removal of the opposite order merely because one side fills or loses. Previously reserved fills keep their original volume. No margin hedging relief is assumed.
- Reserve $7/lot gold and $50/lot silver commission plus 1.5x initial-stop risk for news sizing. Silver's cached commission was materially higher than the earlier generic allowance. Commission stress still uses the greater of recorded charges and the model minimum; budgets are allowances, not guaranteed loss caps.
- Up to four ordinary entries and ONE news release per Prague day (up to four news fills, eight total). Stop admitting new risk after three losing closes or $150 closed daily loss. Both news sides already reserved can still fill. Maximum shared risk $150, metals $100, prospective daily loss $200; margin <=60% of conservative equity.
- Ordinary per-trade budget .50% in evaluation and .25% funded. News budgets halve on 4% drawdown/three EA losses, and are capped at .15% per side funded. Round lots DOWN and skip the whole basket if any minimum lot exceeds its budget. The $12.50-side plans can become untradeable after taper; $15 per side remains above both minimum-lot allowances after halving, down to the model safety floor.
- This changes news admission versus the previous exploratory replay: reservations happen BEFORE release, use a full calendar, share metals limits, include higher silver commission allowance, and use a separate one-release daily quota. Baseline and gold-only are rerun for fair comparisons.
- Source scenario retains saved fills/commission/swap. Stress reduces normal winners 10%, expands losses 10%, adds .02R; news winners -35%, losers +25%, plus .15R. Severe normal -25%/+30%/.10R; news -60%/+100%/.50R. Carry assumptions and phase/payout timing are unchanged from PLAN.md.
- No continuous floating-equity path, actual pre-event quote/spread checks, or new broker rejection/fill modeling is available. Native missed/changed entries cannot be recovered from saved deals. Calendar reservations assume a valid setup at each scheduled event and can conservatively block trades that production would not place. Source and stressed columns are hypothetical sensitivities.

## Risk allocations (planned per side, before rounding)

| Plan | Gold per side | Silver per side | All four-side budget | Reserved news margin at modeled current prices |
|---|---:|---:|---:|---:|
| Seven only | $0.00 | $0.00 | $0.00 | $0 |
| Gold only | $25.00 | $0.00 | $50.00 | $2,319 |
| Silver only | $0.00 | $25.00 | $50.00 | $2,150 |
| Both small | $12.50 | $12.50 | $50.00 | $1,876 |
| Both 15 | $15.00 | $15.00 | $60.00 | $2,593 |
| Gold weighted | $25.00 | $12.50 | $75.00 | $3,036 |
| Gold 25 silver 15 | $25.00 | $15.00 | $80.00 | $3,752 |
| Silver weighted | $12.50 | $25.00 | $75.00 | $3,309 |
| Both larger | $25.00 | $25.00 | $100.00 | $4,469 |

## 60-day results

| Plan | Cost scenario | Median closed trades | Median news fills | Median ending balance | Paired median balance difference vs seven | Worst closed-balance DD | Funded by 30d | Funded by 60d | Reward >=$100 by 60d |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Seven only | source | 23 | 0 | $10,289.12 | $+0.00 | 4.61% | 0.0% | 0.0% | 0.0% |
| Gold only | source | 28 | 5 | $10,345.20 | $+34.89 | 4.54% | 0.0% | 0.0% | 0.0% |
| Silver only | source | 27 | 5 | $10,332.65 | $+13.28 | 4.51% | 0.0% | 0.0% | 0.0% |
| Both small | source | 32 | 9 | $10,320.75 | $+17.72 | 4.48% | 0.0% | 0.0% | 0.0% |
| Both 15 | source | 32 | 10 | $10,320.61 | $+18.53 | 4.43% | 0.0% | 0.0% | 0.0% |
| Gold weighted | source | 30 | 8 | $10,329.06 | $+27.20 | 4.51% | 0.0% | 0.0% | 0.0% |
| Gold 25 silver 15 | source | 29 | 6 | $10,317.86 | $+17.72 | 4.62% | 0.0% | 0.0% | 0.0% |
| Silver weighted | source | 30 | 8 | $10,326.88 | $+21.30 | 4.61% | 0.0% | 0.0% | 0.0% |
| Both larger | source | 29 | 6 | $10,321.85 | $+18.93 | 4.62% | 0.0% | 0.0% | 0.0% |
| Seven only | stress | 23 | 0 | $10,116.02 | $+0.00 | 5.12% | 0.0% | 0.0% | 0.0% |
| Gold only | stress | 28 | 5 | $10,150.55 | $+1.11 | 5.11% | 0.0% | 0.0% | 0.0% |
| Silver only | stress | 27 | 5 | $10,129.65 | $-8.85 | 5.26% | 0.0% | 0.0% | 0.0% |
| Both small | stress | 32 | 9 | $10,136.29 | $-2.21 | 5.16% | 0.0% | 0.0% | 0.0% |
| Both 15 | stress | 32 | 10 | $10,140.25 | $-4.14 | 5.22% | 0.0% | 0.0% | 0.0% |
| Gold weighted | stress | 30 | 8 | $10,125.15 | $-2.09 | 5.23% | 0.0% | 0.0% | 0.0% |
| Gold 25 silver 15 | stress | 29 | 6 | $10,134.35 | $-5.00 | 5.12% | 0.0% | 0.0% | 0.0% |
| Silver weighted | stress | 30 | 8 | $10,128.99 | $-3.36 | 5.36% | 0.0% | 0.0% | 0.0% |
| Both larger | stress | 29 | 6 | $10,145.35 | $-5.04 | 5.20% | 0.0% | 0.0% | 0.0% |
| Seven only | severe | 22 | 0 | $9,871.50 | $+0.00 | 6.05% | 0.0% | 0.0% | 0.0% |
| Gold only | severe | 27 | 5 | $9,819.96 | $-32.10 | 6.18% | 0.0% | 0.0% | 0.0% |
| Silver only | severe | 27 | 5 | $9,828.48 | $-33.20 | 6.11% | 0.0% | 0.0% | 0.0% |
| Both small | severe | 29 | 7 | $9,843.92 | $-23.04 | 6.13% | 0.0% | 0.0% | 0.0% |
| Both 15 | severe | 32 | 10 | $9,813.83 | $-36.47 | 6.31% | 0.0% | 0.0% | 0.0% |
| Gold weighted | severe | 29 | 6 | $9,832.63 | $-36.34 | 6.20% | 0.0% | 0.0% | 0.0% |
| Gold 25 silver 15 | severe | 30 | 7 | $9,801.62 | $-44.78 | 6.09% | 0.0% | 0.0% | 0.0% |
| Silver weighted | severe | 30 | 8 | $9,811.81 | $-40.71 | 6.12% | 0.0% | 0.0% | 0.0% |
| Both larger | severe | 29 | 7 | $9,801.18 | $-49.80 | 6.18% | 0.0% | 0.0% | 0.0% |

Balance is simulated account capital, not withdrawable income; phase resets can affect it. Drawdown is closed-balance only. Zero endpoint breaches cannot certify FTMO equity compliance.

## One-year context (stressed)

| Plan | Funded by 365 days | Reward >=$100 by 365 days | Closed-balance safety halt | Inactivity stop |
|---|---:|---:|---:|---:|
| Seven only | 40.1% | 20.8% | 0.0% | 10.6% |
| Gold only | 41.1% | 22.2% | 0.0% | 12.1% |
| Silver only | 35.3% | 20.8% | 0.0% | 11.6% |
| Both small | 37.7% | 18.8% | 0.0% | 11.1% |
| Both 15 | 35.7% | 21.7% | 0.0% | 11.6% |
| Gold weighted | 38.2% | 18.8% | 0.0% | 10.6% |
| Gold 25 silver 15 | 37.2% | 19.8% | 0.0% | 11.1% |
| Silver weighted | 35.7% | 22.7% | 0.0% | 10.6% |
| Both larger | 37.7% | 20.8% | 0.0% | 11.6% |

## News standalone stress screen

| EA | Trades | Source net win rate | Stressed net win rate | Stressed equal-risk PF |
|---|---:|---:|---:|---:|
| news-pulse-xau/standard | 155 | 67.1% | 55.5% | 1.97 |
| news-pulse-xag/standard | 151 | 53.6% | 44.4% | 1.21 |

## Interpretation

Gold-only is the first candidate to validate, not a statistically established winner. If both metals are required, start research/forward validation at $15 planned per side, $60 maximum budget per release, with shared guards. This retains room for risk taper and avoids the $12.50 minimum-lot trap. Increasing both to $25 raises margin consumption and blocks more release baskets without producing short-deadline passes.
Do not interpret the difference between two portfolio median balances as the typical improvement on the same starting date. Under stress, both at $15 has a paired median 60-day change of -$4.14 versus the seven-EA baseline even though its unpaired median balance is higher. This is not evidence that adding silver reliably improves the portfolio. All compared 60-day variants have zero modeled funding/payout successes; real-world probabilities remain unknown.

## Conditions before any deployment

Keep both pending directions, but share account-level risk limits. No adaptive bypass. Confirm exact news-straddle permission with FTMO: Swing permits news, but prohibited gap-trading and abusive execution rules still apply. Validate real FTMO event ticks, spreads, commission, symbol contract sizes/leverage, stop/freeze levels, and margin before treating this shortlist as executable. No live equity safety claim is made.

[Swing rules](https://ftmo.com/en/faq/ftmo-swing-account-type/) | [Forbidden practices](https://ftmo.com/en/forbidden-trading-practices/)
