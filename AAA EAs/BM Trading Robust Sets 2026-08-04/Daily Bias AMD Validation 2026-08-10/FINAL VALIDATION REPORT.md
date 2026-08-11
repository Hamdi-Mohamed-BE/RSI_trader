# Daily Bias + AMD strategy validation

Completed: 2026-08-10

## Verdict

**The mechanical version of the idea does not pass validation on XAU, BTC, EURUSD, GBPJPY, US30 or US100. It should not be added to the active EA portfolio.**

The test searched 384 reasonable interpretations using 2022-2023 training data and 2024 validation data. Each selected configuration was then frozen before the untouched 2025-2026 holdout was read.

| Market | Full trades | Full return | Full PF | Win rate | Max DD | Untouched return | Untouched PF | Decision |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| XAU | 140 | +7.19% | 1.12 | 42.14% | 9.69% | -0.67% | 0.98 | Fail |
| BTC | 135 | +12.33% | 1.21 | 36.30% | 14.18% | +13.90% | 1.46 | Fail: training PF 0.69 |
| EURUSD | 80 | -6.28% | 0.87 | 28.75% | 12.55% | -5.79% | 0.61 | Fail |
| GBPJPY | 321 | -13.82% | 0.94 | 35.83% | 21.51% | -17.40% | 0.72 | Fail |
| US30 | 68 | +8.58% | 1.29 | 20.59% | 7.33% | -6.40% | 0.48 | Fail |
| US100 | 76 | +1.09% | 1.05 | 18.42% | 12.29% | -4.83% | 0.60 | Fail |

BTC is not a valid exception. Its selected rule lost 6.87% with PF 0.69 in the original 2022-2023 training period, then improved later. Passing only the future segment does not establish a stable edge.

## What was tested

The transcript contains discretionary language that cannot be backtested literally, including “rejection candle,” “change of character,” “supply zone,” “breaker block,” and moving to break-even “as soon as possible.” The following rules make its central idea explicit without using future information:

1. Align daily candles and sessions to Europe/London time.
2. Use only completed daily candles for the next trading day's bias.
3. Continuation bias: the latest two daily candles point the same way, or the latest directional body engulfs the preceding body. The latest body must be at least 30% of its range.
4. Reversal bias: the latest daily candle sweeps the preceding high/low and its body engulfs the preceding opposite candle.
5. Optionally reject a third consecutive same-direction daily setup, reflecting the video's warning about three aggressive days.
6. Treat 00:00-08:00 London as Asia accumulation.
7. From 08:00-16:00 London, require a sweep against the daily bias through the Asia high or low.
8. Require a bullish/bearish M5 or M15 engulfing confirmation. The stricter variant must also close beyond the preceding candle's extreme.
9. Enter either at the next market price or on a 61.8% pullback within four confirmation bars.
10. Place the stop beyond the manipulation extreme with a 5% Asia-range buffer.
11. Test 2R and 3R targets, with either no management or break-even at 1R.
12. Permit at most one trade per market per day and close any remaining trade at 16:00 London.

## Test controls

- Initial balance: USD 10,000.
- Risk: 1% of current closed balance per trade.
- Training: 2022-2023.
- Validation: 2024.
- Untouched holdout: 2025 through 2026-08-09.
- Data: MEXAtlantic M1 broker bars.
- Costs: observed minute-by-minute broker spread included. Median BTC spread was approximately USD 35.
- Conservative execution: if stop and target were both reachable in the same M1 bar, the stop was assumed first.
- No commission, swap or additional slippage was included, so the result is still somewhat optimistic.
- This is an M1 bar replay, not a tick-by-tick MT5 Strategy Tester certification.

## Period stability

| Market | 2022-2023 train | 2024 validation | 2025-2026 untouched | Stability conclusion |
|---|---|---|---|---|
| XAU | +4.54%, PF 1.18, 60 trades | +3.22%, PF 1.20, 37 | -0.67%, PF 0.98, 43 | Edge disappeared |
| BTC | -6.87%, PF 0.69, 46 | +5.90%, PF 1.80, 24 | +13.90%, PF 1.46, 65 | Regime change; failed training |
| EURUSD | +1.59%, PF 1.11, 30 | -2.08%, PF 0.85, 24 | -5.79%, PF 0.61, 26 | Failed validation and holdout |
| GBPJPY | +2.09%, PF 1.04, 144 | +2.20%, PF 1.08, 73 | -17.40%, PF 0.72, 104 | Severe holdout failure |
| US30 | +10.19%, PF 1.84, 29 | +5.27%, PF 1.80, 19 | -6.40%, PF 0.48, 20 | Strong overfit signature |
| US100 | +4.23%, PF 1.22, 43 | +1.91%, PF 1.50, 10 | -4.83%, PF 0.60, 23 | Holdout failure |

## Best selected configuration by market

All six optimizers selected **continuation**, not the video's “A+ reversal,” as their highest-ranked daily bias.

| Market | Skip third day | Confirmation | Entry | Asia sweep buffer | Target | Management |
|---|---|---|---|---:|---:|---|
| XAU | Yes | M15 close-break engulf | Market | 5% | 3R | None |
| BTC | Yes | M15 close-break engulf | Market | 0% | 3R | Break-even at 1R |
| EURUSD | Yes | M15 close-break engulf | 61.8% pullback | 0% | 2R | Break-even at 1R |
| GBPJPY | No | M5 close-break engulf | Market | 0% | 3R | None |
| US30 | Yes | M5 body engulf | 61.8% pullback | 5% | 3R | Break-even at 1R |
| US100 | Yes | M5 body engulf | 61.8% pullback | 0% | 3R | Break-even at 1R |

The need for materially different settings across markets is evidence that the transcript describes a discretionary framework, not one stable universal rule.

## Direct check of the daily-bias claim

The continuation bias alone predicted the direction of the untouched day's candle at approximately:

| Market | Signals | Correct direction |
|---|---:|---:|
| XAU | 201 | 47.76% |
| BTC | 277 | 54.87% |
| EURUSD | 254 | 49.61% |
| GBPJPY | 256 | 46.88% |
| US30 | 176 | 42.61% |
| US100 | 189 | 52.91% |

This does not support the video's suggestion that the two-candle bias mechanically unlocks a high daily win rate.

## One universal rule across all six markets

The best rule selected from the combined training and validation data was:

- Continuation bias; skip the third same-direction daily setup.
- M15 close-break engulfing confirmation.
- Market entry after any Asia-boundary sweep.
- 2R target, no break-even.

Its combined result was:

| Period | Trades | Return | PF | Max DD |
|---|---:|---:|---:|---:|
| 2022-2023 training | 444 | -21.64% | 0.91 | 26.45% |
| 2024 validation | 245 | -14.61% | 0.89 | 22.77% |
| 2025-2026 untouched | 349 | +22.02% | 1.13 | 14.88% |
| Full 2022-2026 | 1,038 | -18.36% | 0.98 | 40.74% |

The universal rule fails decisively. The positive recent segment does not repair the losses and instability in the earlier independent periods.

## Admission gate

A market must have positive return and PF above 1 in training, validation and holdout, at least eight holdout trades, full-period PF of at least 1.15, and maximum closed-balance drawdown no greater than 15%. None passed.

No EA, save file or active BAT entry was created from this idea.

## Saved evidence

- `Results/summary.csv`: final market comparison.
- `Results/results.json`: full configurations and period statistics.
- `Results/configuration-ranking-*.csv`: all 384 tested configurations for each market.
- `Results/selected-trades-*.csv`: every trade produced by the frozen selected rule.
- `Results/daily-bias-direction-accuracy.csv`: direct daily-bias accuracy check.
- `Results/equity-*.png`: each selected equity graph and the universal combined graph.
- `Data/manifest.json`: BTC and GBPJPY data specifications and file hashes. The four previously cached feeds retain their hashes in the Apex/IVB research data manifest.
