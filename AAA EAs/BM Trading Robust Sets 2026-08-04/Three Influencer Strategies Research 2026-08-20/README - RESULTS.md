# Three Influencer Strategies — Native MT5 Validation

Date completed: 2026-08-20

## Decision

None of the three strategies passed locked validation strongly enough to add to the active installation BAT. The active portfolio was not changed.

Strategy 3 on GBPJPY remained slightly profitable out of sample, but +1.14% from only 17 trades with PF 1.11 is not enough evidence for deployment. Its set is labelled `RESEARCH ONLY`; all other locked candidates are labelled `REJECTED`.

## Test protocol

- Broker and data: Exness MT5, broker symbols and contract specifications
- Account: simulated USD 10,000, leverage 1:2000
- Risk: 1% target risk per trade
- Training screen: 2020-01-01 through 2024-12-31, native MT5 M1 modelling
- Locked validation: 2025-01-01 through 2026-08-19, native MT5 every-tick modelling
- Execution: randomized delay
- Costs: broker spread is present in bid/ask ticks; commission and swap are included in net results
- No locked-period settings were fed back into the parameter search

All percentages shown below are total return for the stated period, not annualized return.

## Main comparison

| Strategy / selected candidate | Training return | Training PF | Training win rate | Training max equity DD | Training trades | Locked return | Locked PF | Locked win rate | Locked max equity DD | Locked trades | Verdict |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1. USTEC 10AM AMD/FVG, body >= 0.4 ATR, 2R | +159.85% | 1.13 | 40.03% | 26.68% | 1,144 | -9.57% | 0.95 | 38.46% | 19.63% | 364 | Reject |
| 2. USTEC 09:30 one-minute ORB, breakout, RV >= 0.8, 2R | +6.06% | 1.12 | 48.28% | 13.14% | 87 | -13.13% | 0.69 | 21.92% | 16.63% | 73 | Reject |
| 3. GBPJPY 01:00 UTC sweep, 15-minute drive, efficiency >= 0.65 | +10.01% | 1.54 | 48.28% | 5.53% | 29 | +1.14% | 1.11 | 47.06% | 5.43% | 17 | Research only |

## Locked validation — full statistics for the selected candidate from each strategy

| Metric | 1. 10AM AMD/FVG | 2. 09:30 ORB | 3. Asia sweep |
|---|---:|---:|---:|
| Symbol / timeframe | USTEC M1 | USTEC M1 | GBPJPY M1 |
| Initial balance | $10,000.00 | $10,000.00 | $10,000.00 |
| Final balance | $9,043.08 | $8,687.47 | $10,113.89 |
| Net profit | -$956.92 | -$1,312.53 | +$113.89 |
| Total return | -9.57% | -13.13% | +1.14% |
| Max equity drawdown | $1,990.67 / 19.63% | $1,733.23 / 16.63% | $560.38 / 5.43% |
| Max balance drawdown | $1,895.87 / 18.86% | $1,671.18 / 16.13% | $404.26 / 3.97% |
| Profit factor | 0.95 | 0.69 | 1.11 |
| Win rate | 38.46% | 21.92% | 47.06% |
| Wins / losses | 140 / 224 | 16 / 57 | 8 / 9 |
| Trades | 364 | 73 | 17 |
| Gross profit | $19,059.61 | $2,896.21 | $1,181.06 |
| Gross loss | -$20,016.53 | -$4,208.74 | -$1,067.17 |
| Largest win | $417.61 | $203.33 | $247.93 |
| Largest loss | -$298.52 | -$103.48 | -$104.30 |
| Average win | $136.14 | $181.01 | $147.63 |
| Average loss | -$86.78 | -$71.29 | -$101.64 |
| Expected payoff / trade | -$2.63 | -$17.98 | +$6.70 |
| Commission | -$577.16 | -$145.34 | -$152.44 |
| Swap | -$36.02 | $0.00 | $0.00 |
| History quality | 100% | 100% | 100% |

## Important fidelity findings

### Strategy 1 — 10AM AMD/FVG

The discretionary terms were made deterministic: a 09:30–09:59 New York accumulation range, sweep/manipulation, ATR-normalized displacement as change in state of delivery, three-candle FVG, midpoint retracement, and prior range extremes/fallback R target. The strict NQ/US500 SMT proxy generated zero trades during the five-year screen. Therefore, the tradeable candidate disabled mandatory SMT and must not be represented as a full mechanical proof of every rule claimed in the video.

The large training return did not survive locked validation. PF near 1.1 in training plus a regime reversal out of sample indicates a weak/unstable edge.

### Strategy 2 — 09:30 one-minute ORB

This version uses the exact 09:30 New York one-minute range, breakout/retest modes, relative tick volume, range/ATR filtering, ATR regime filtering, VWAP, optional EMA filtering, and risk-based sizing. Exness USTEC is a CFD, so its volume is broker tick volume—not centralized CME NQ futures volume.

The immediate-breakout candidate failed clearly. The retest version also failed locked validation: -1.24%, PF 0.76, 28.57% wins, 4.89% equity DD, and only seven trades.

### Strategy 3 — second Asia hour sweep

Because the source never defines the session timezone, 00:00, 01:00 and 02:00 UTC were screened. The rules require a prior-H1 sweep, sustained first-half drive, second-half M1 structure shift, midpoint retracement, stop beyond the sweep extreme, and a range/R-based target.

The apparently spectacular strict candidate was a tiny-sample trap: training PF 28.93 and 100% wins came from only nine trades; locked validation then produced -4.84%, PF 0.26, 14.29% wins, and seven trades. The broader GBPJPY candidate was slightly positive but still statistically weak.

## Equity graphs — locked validation

### Strategy 1

![Strategy 1 locked equity](Backtest%20Reports/Locked%20Validation/s1-fvg1-body04-rr20.png)

### Strategy 2

![Strategy 2 locked equity](Backtest%20Reports/Locked%20Validation/s2-entry0-rv08-range002-rr2.png)

### Strategy 3

![Strategy 3 locked equity](Backtest%20Reports/Locked%20Validation/s3-gbpjpy-h1-drive15-eff065.png)

## Files

- EA source and compiled files: `EA`
- Base and labelled candidate sets: `Sets`
- Five-year training reports and graphs: `Backtest Reports/Training`
- Locked every-tick reports and graphs: `Backtest Reports/Locked Validation`
- Machine-readable summaries: `training-results.csv/json` and `locked-results.csv/json` inside their report folders

