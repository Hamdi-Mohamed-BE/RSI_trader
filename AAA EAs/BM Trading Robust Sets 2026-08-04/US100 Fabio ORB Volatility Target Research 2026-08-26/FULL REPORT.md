# US100 Fabio ORB with volatility-targeted sizing — native MT5 validation

Research date: 2026-08-26

## Verdict

**RESEARCH-ONLY; DO NOT DEPLOY YET.** The literal transcript version and a training-selected derivative are reported separately. The selected derivative was chosen without looking at locked data.

## Native MT5 results

| Version | Segment / model | Return | PF | Win rate | Equity DD | Trades | Quality |
|---|---|---:|---:|---:|---:|---:|---:|
| Screen-selected ORB15 | Training / 1-minute OHLC | +15.35% | 1.06 | 50.97% | 18.15% | 514 | 98% |
| Screen-selected ORB15 | Validation / 1-minute OHLC | +23.20% | 1.27 | 52.36% | 8.56% | 191 | 98% |
| Screen-selected ORB15 | Locked / Every Tick | +4.82% | 1.07 | 56.58% | 13.16% | 152 | 100% |
| Screen-selected ORB15 | Latest year / Every Tick | +1.61% | 1.03 | 56.49% | 13.16% | 131 | 100% |
| Screen-selected ORB15 | Full / 1-minute OHLC | +51.28% | 1.11 | 52.28% | 18.15% | 857 | 98% |
| Literal ORB30 | Training / 1-minute OHLC | +7.88% | 1.04 | 54.81% | 12.04% | 655 | 98% |
| Literal ORB30 | Validation / 1-minute OHLC | +11.03% | 1.13 | 53.08% | 9.93% | 260 | 98% |
| Literal ORB30 | Locked / Every Tick | +9.08% | 1.18 | 59.56% | 8.92% | 183 | 100% |
| Literal ORB30 | Latest year / Every Tick | +9.08% | 1.20 | 59.63% | 8.92% | 161 | 100% |
| Literal ORB30 | Full / 1-minute OHLC | +31.97% | 1.09 | 55.19% | 12.04% | 1098 | 98% |

## Exact rules

- Literal: use the 09:30–10:00 New York range; after a completed M5 candle closes above its high, enter long on the next tick; stop at the ORB low; target 1R; close at 15:00 New York; one trade per day.
- Selected derivative: use the first 15 minutes; require a bullish breakout close before 10:30; stop at the ORB low; target 1.5R; close at 15:00 New York.
- Both size the position from the actual entry-to-stop distance so each trade risks 1% of current equity.
- No delta filter is used. Exness USTEC cannot provide CME aggressive buy/sell delta.

## Test controls

- Exness USTEC, $10,000 initial balance, 1:2000 leverage.
- Native spread, commissions and swaps are reflected in MT5; random execution delay is enabled.
- Training: 2020–2023. Validation: 2024–June 2025. Locked: July 2025–August 2026. Latest-year and locked runs use 100% MT5 Every Tick modeling.
- Available Exness history begins in 2020, so the video’s claim that the edge weakened before 2019 could not be independently tested here.

## Deployment

The active BAT, active presets, installed EAs and website were not changed by this isolated validation.
