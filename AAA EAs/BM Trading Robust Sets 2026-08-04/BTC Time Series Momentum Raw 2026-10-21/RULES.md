# BTC time-series momentum + volatility targeting — raw rules (frozen 2026-10-21, before any test)

Source: a social-media clip pasted by the user (2026-10-21), treated as data. Its rules:
- **Rule 1:** look at Bitcoin's 30-day return. If it is positive, go long. If it is negative, go flat (spot) or short (perps).
- **Rule 2 (volatility targeting):** position size = target volatility ÷ current volatility, with a 20% target. At 60%
  volatility you hold 1/3 of capital; at 90%, about 22%.
- Rebalance weekly; exit when the signal flips.
- The clip admits it loses in choppy markets and wins on a few big trends. It gives no results.
Research only. Isolated tester, nothing deployed.

## Our defaults (fixed before testing)
- **Instrument:** Exness-MT5Trial16 `BTCUSD` CFD, which trades 7 days a week. Server clock UTC; daily decisions on the first
  tick of each D1 bar (00:00 UTC). M1 history from 2014; real ticks only from 2026-01 (earlier ticks generated).
- **30-day return:** close[1] ÷ close[31] − 1 on D1 closes (30 calendar days).
- **Volatility (ours):** sample standard deviation of the last 30 daily log returns × √365 (annualised, crypto 365 days).
- **Size:** notional = min(1.0, 20% ÷ volatility) × equity. Cap 1.0× because spot can't be levered (ours).
  Volume = notional ÷ (price × contract size), rounded to the NEAREST lot step (not risk-based, so not rounded up).
  Deposit **$100,000**, so the 0.01-lot step is fine-grained (ours); results are reported in %.
- **Signal timing (ours):** the signal is checked every day. A flip closes everything, and opens the new direction if there is one.
- **Rebalance (ours):** every Monday 00:00 UTC, resize to the target if it differs by ≥ 5% (add a position or partially close).
- **No stop loss or target** (none in the clip). Broker spread, commission and swap apply.

## Versions
| Id | What |
|---|---|
| **LF** | Main, spot: long when the 30-day return is > 0, otherwise flat |
| **LS** | Main, perps: long when > 0, short when < 0 |
| BH | Benchmark: buy and hold 1× notional from the first day, never resized |
| VTL | Control for Rule 1: always long, vol-targeted and weekly rebalanced (the signal removed) |
| FIX | Control for Rule 2: LF signal with a fixed 1× notional (vol targeting removed) |
| RND1–3 | Control: random long/flat, daily flip probability matched to LF's flip rate, vol-targeted (3 seeds) |
| S_L20 / S_L60 / S_L90 | Sensitivity: lookback 20 / 60 / 90 days |
| S_T10 / S_T30 | Sensitivity: target volatility 10% / 30% |
| S_V60 | Sensitivity: 60-day volatility window |
| S_CAP2 | Sensitivity: leverage cap 2× (perp-style) |
| S_D1 | Sensitivity: rebalance daily |
| S_WK | Sensitivity: signal checked weekly only (Monday) |

## Test setup and gate
- **Execution:** native MT5 Model 4, 150 ms, $100,000 USD, 1:2000. End 2026-10-20 exclusive.
- **Windows (revised after the 49-day smoke test, before any real run):**
  - Model 4 on BTC's 24/7 ticks takes about 7 minutes per 5-year run.
  - Gate/confirmation (Model 4): separate native 6m / 1y / 3y / 5y runs for LF and LS.
  - Comparison screen (Model 1, 1-minute OHLC, PIPELINE stage 3 "fast screen"): one 5y run for LF, LS, BH, VTL, every
    control and every sensitivity. Controls are compared only with the same-model LF / LS, so the comparisons are like for like.
  - Per-year table and windows from the daily equity log.
- **Metrics:** equity-based daily Sharpe (√365), CAGR, max equity drawdown, exposure, flips, positions, trades/month and
  trades/day, PF and win rate per signal episode (flip to flip) and per closed position.
- **Raw gate (PIPELINE.md stage 4, adapted to a portfolio rule):** for LF and for LS, each must meet all of these:
  - positive on 3y and 5y with episode PF ≥ 1.15;
  - ≥ 30 closed positions;
  - 5y Sharpe above both the VTL control and the RND mean;
  - no flip to ≤ 0 without the best day or best trade.
  Buy and hold is reported as the benchmark, not a gate.
