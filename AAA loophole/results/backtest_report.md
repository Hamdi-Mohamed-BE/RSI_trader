# Nasdaq Loophole Research — Initial Locked Backtest

Generated from data available through **2026-07-31**.

## Result that matters: untouched NQ test (2021-present)

| Metric | Result |
|---|---:|
| Trades | 24 |
| Profit factor | 1.87 |
| Win rate | 83.33% |
| Maximum drawdown | 1.17% |
| Total return at 0.5% initial risk/trade | 1.40% |
| Net R | 2.79R |
| Mean trade | 0.116R |

The maximum drawdown and return use fractional sizing at **0.5% of current equity per initial stop**. They are closed-trade figures and do not include taxes, financing, broker margin rules, or intraday mark-to-market drawdown.

## Locked rule

`PB_long_MA100_RSI2_E5_X70_ATR3_H10_T0`

- Family: pullback_rsi
- Direction: long
- Trend regime: 100-day moving average
- RSI period / entry / exit: 2 / 5 / 70
- Breakout lookback / exit EMA: 0 / 0
- Initial stop: 3 × ATR(14)
- Profit target: 0R (`0` means no fixed target)
- Maximum holding period: 10 sessions
- Signal is calculated after the close; execution is at the next open.

## Honest experiment design

- 720 bounded hypotheses were evaluated.
- Selection data only: 2000–2020, divided into three non-overlapping robustness folds.
- Locked unseen test: 2021 through 2026-07-31.
- Independent implementation check: the locked rule was also run on QQQ during the same test dates.
- NQ cost assumption: 0.5 index points slippage per side plus 0.62 point round-trip commission equivalent (conservative MNQ-style assumption).
- If a daily bar touches both stop and target, the stop is assumed to occur first.
- Entry and indicator calculations contain no same-bar look-ahead.

## Comparison

| Dataset | Period | Trades | Profit factor | Win rate | Max DD | Return at 0.5% risk/trade |
|---|---|---:|---:|---:|---:|---:|
| NQ development | 2000–2020 | 68 | 2.32 | 79.41% | 1.60% | 5.50% |
| NQ untouched test | 2021–present | 24 | 1.87 | 83.33% | 1.17% | 1.40% |
| QQQ cross-check | 2021–present | 22 | 2.48 | 81.82% | 0.85% | 1.76% |

NQ buy-and-hold over the test window returned 123.91% with a 35.28% daily-close drawdown. This is context, not a directly equivalent risk comparison.

## Uncertainty check

Bootstrapping the unseen NQ trades 5,000 times produced a 95% profit-factor interval of **0.70–30.08**. The resampled probability of PF > 1 was **88.08%**. A wide interval means the sample is still too small to claim a durable edge.

## Important limitations

This is a research result, not proof of a live-trading loophole. Yahoo's `NQ=F` is a continuous daily series, not a broker's US100 tick feed. It can hide rollover details and cannot model intraday order sequence, spread expansion, rejected orders, latency, financing, or prop-firm rules. Before real money, rerun the locked rule on the exact broker feed, then perform paper and small-size forward tests.

## Reproduce

```powershell
python nasdaq_loophole_backtest.py
```
