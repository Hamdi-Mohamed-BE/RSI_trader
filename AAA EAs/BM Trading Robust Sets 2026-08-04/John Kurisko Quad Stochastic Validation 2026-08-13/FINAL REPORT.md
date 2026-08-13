# John Kurisko quad-stochastic strategy — validation report

Source video: https://www.youtube.com/watch?v=PpysVy2NNQ4

## Verdict

**REJECTED as a mechanical EA and not added to the active MT5/BAT portfolio.**

Neither the literal video rules nor any training-selected mechanical variation passed the 2022–2024 training gate. All four frozen/literal variants then lost money in the untouched 2025–2026 validation. The least-bad result was the stricter continuation setup, which lost **15.91%** with PF **0.55**.

This does not prove that John Kurisko cannot trade the discretionary method profitably. It shows that the publicly described stochastic rules do not reproduce the claimed edge when converted into a repeatable EA and charged realistic broker execution.

## Test design

- Markets: BTCUSD, XAUUSD, US100, US30, and EURUSD.
- Data: broker-sourced M1 OHLC, recorded spread, and broker contract/volume specifications.
- Coverage: 2022-01-02 through 2026-08-09, depending on market availability.
- Training/selection: 2022-01-01 through 2024-12-31.
- Untouched validation: 2025-01-01 through 2026-08-10.
- Initial balance: $10,000 per market; $50,000 equal-weight portfolio.
- Risk: 1% of current equity per trade, capped at 3x notional exposure.
- Entry/rotation exit: next one-minute open after a closed-bar signal.
- Costs: recorded spread plus 5% of spread as additional slippage on every fill.
- Stops: beyond the signal wick, padded by ATR; adverse intrabar stop execution modeled.
- No future pivots, no same-bar signal entries, and no inspection of the holdout during selection.

## Untouched portfolio results

| Interpretation | Final balance | Return | PF | Win rate | Trades | Max equity DD |
|---|---:|---:|---:|---:|---:|---:|
| Literal “super signal” | $13,837.06 | -72.33% | 0.69 | 41.38% | 29,695 | 72.49% |
| Literal continuation flag | $29,137.93 | -41.72% | 0.61 | 33.97% | 7,898 | 41.72% |
| Frozen reversal | $25,757.01 | -48.49% | 0.70 | 40.44% | 13,837 | 48.70% |
| Frozen continuation | $42,043.16 | -15.91% | 0.55 | 32.26% | 1,903 | 15.92% |

## Least-bad frozen continuation by market

| Market | Return | PF | Win rate | Trades | Max equity DD |
|---|---:|---:|---:|---:|---:|
| BTCUSD | -43.96% | 0.41 | 31.92% | 473 | 44.02% |
| XAUUSD | -10.13% | 0.59 | 37.85% | 251 | 12.46% |
| US100 | -4.02% | 0.88 | 39.21% | 403 | 9.84% |
| US30 | -0.94% | 0.95 | 36.99% | 346 | 2.69% |
| EURUSD | -20.51% | 0.19 | 19.07% | 430 | 20.74% |

US30 was closest to break-even, but PF below 1 and a negative return still fail validation.

## Frozen settings

The training-selected reversal used a maximum 12-bar pivot separation, a five-point stochastic divergence, a second 9-3 pivot at/inside the 20/80 boundary, no more than 0.5 ATR price extension, a 0.1 ATR stop buffer, and a 20-bar time stop.

The training-selected continuation was deliberately stricter than the literal video version: 60-10 embedded beyond 90/10, 9-3 reaching 20/80, price on the correct side of EMA20, only the first two pullbacks per embedded segment, a 0.1 ATR stop buffer, and a 20-bar time stop.

Neither configuration passed the training gate. The least-bad training median returns were -82.96% for reversal and -19.44% for continuation, with zero profitable training instruments for both.

## Why the video’s “98%” is not evidence

At approximately 25:30–26:11, the video shows 156 trades and 98% profitable on a Bitcoin chart. The speaker immediately says he does not know what the display is counting, does not rely on it, and that ES parameters were still applied to Bitcoin. It is therefore not a reproducible Bitcoin backtest.

The literal super-signal holdout won only 41.38% after execution. Its zero-cost directional reconstruction was still only 53.09% wins and PF 0.98. The training-frozen reversal was approximately break-even before execution (PF 1.01) but lost badly after spread/slippage. This is the clearest diagnosis: any raw oscillator edge is too small for one-minute CFD execution.

## Execution-cost diagnosis

| Interpretation | Actual net P/L | Estimated execution cost | Net before modeled costs | PF before modeled costs |
|---|---:|---:|---:|---:|
| Literal super signal | -$36,162.94 | $34,477.48 | -$1,685.46 | 0.98 |
| Literal continuation | -$20,862.07 | $16,074.23 | -$4,787.83 | 0.89 |
| Frozen reversal | -$24,242.99 | $24,804.81 | +$561.82 | 1.01 |
| Frozen continuation | -$7,956.84 | $6,438.59 | -$1,518.25 | 0.89 |

The frozen reversal’s tiny pre-cost edge is not tradable: execution turns it into a large loss. BTCUSD is especially unsuitable through this CFD feed because its median recorded spread was approximately $35.

## Important limitations

- The speaker explicitly describes channel selection and “market pulse” as discretionary and says he does not believe in mechanical backtesting for the full method.
- The video does not provide an exact, machine-readable 1-2-3 channel algorithm. I did not invent a future-aware pivot channel because that would introduce hindsight.
- Historical major-news timestamps were not present in the supplied broker files, so the requested no-news discretion could not be fully replicated. A news filter may reduce trades, but it would need an externally archived release calendar and cannot be assumed to transform PF 0.55–0.95 into a robust edge.
- M1 OHLC cannot resolve the exact tick order inside a candle. Stops were treated conservatively, and signals were never filled before the next bar.

## Saved evidence

- `VIDEO RULE MAPPING.md` — timestamped rule extraction and mechanical assumptions.
- `validate_quad_stochastic.py` — reproducible validation engine.
- `Results/training-ranking.csv` — training candidate ranking.
- `Results/frozen-configs.json` — parameters locked before holdout.
- `Results/holdout-by-instrument.csv` — market-by-market statistics.
- `Results/holdout-portfolio-summary.csv` — portfolio statistics.
- `Results/*-trades.csv` and `Results/*-equity.csv` — full audit trail.
- `Results/final-results.json` — machine-readable complete result.
- `Results/holdout-equity.png` — portfolio and instrument equity charts.

## Deployment status

No MQL5 live EA was built or installed, no set file was promoted, and no active BAT/MT5 configuration was changed. The strategy failed the minimum PF, profitability, and drawdown requirements.
