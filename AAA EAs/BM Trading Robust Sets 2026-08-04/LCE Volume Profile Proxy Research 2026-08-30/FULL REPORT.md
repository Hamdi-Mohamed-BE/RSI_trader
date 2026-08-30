# LCE volume-profile level breakout — MT5 walk-forward validation

This is a transparent proxy for the public LCE rules. The proprietary hand-drawn level chart is replaced by rolling tick-volume high-volume nodes fixed at the New York open.

## Locked last-year results

| Symbol | Selected variant | Development return / PF | Locked return / PF | Win rate | Equity DD | Trades | Decision |
|---|---|---:|---:|---:|---:|---:|---|
| BTCUSD | early-20d-score1 | +15.65% / 1.27 | +17.28% / 1.22 | 32.80% | 11.31% | 189 | KEEP CANDIDATE |
| USTEC | quality-20d-score1-r125 | +2.85% / 1.06 | +14.24% / 1.28 | 36.89% | 10.38% | 103 | WATCH — NOT ROBUST |
| US500 | literal-20d-neutral-rth | +47.81% / 1.59 | -4.42% / 0.96 | 36.07% | 20.55% | 244 | REJECT |
| XAUUSD | robust-40d-score1 | +4.98% / 1.08 | -8.06% / 0.89 | 28.19% | 23.12% | 149 | REJECT |

## Test integrity

- Exness MT5 Trial 16; native Every Tick model with random execution delay.
- $10,000 initial balance, 1:2000 leverage and 1% equity risk per trade.
- Development: 2024-08-29 through 2025-08-28. Untouched locked test: 2025-08-29 through 2026-08-28.
- Broker spread, commission and swap are included.
- CFD tick volume is only a broker-activity proxy; it is not centralized CME volume.
- No active BAT or website file was changed.
