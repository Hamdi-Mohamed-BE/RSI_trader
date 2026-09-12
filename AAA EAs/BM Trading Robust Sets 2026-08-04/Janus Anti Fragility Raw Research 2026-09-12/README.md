# Janus Anti-Fragility — raw US100/XAU CFD review

Status: **research only; not integrated into Calyx, an EA, or any BAT**.

This is the untouched Janus switching logic from upstream commit
`535996d8d4dff9f0f8cd3ccc30dc50ef34c6776c`, applied to the connected
Exness MT5 account's native `USTEC` growth leg and `XAUUSD` defensive leg.
The broker does not expose SPY or GLD, so this is a CFD adaptation rather
than a reproduction of the repository's canonical SPY/GLD study.

## Data and test contract

- MT5 server: `Exness-MT5Trial16`
- Raw common D1 history used for indicator warm-up: 2019-07-16 to 2026-09-11
- Displayed test: 2023-09-11 to 2026-09-11
- Common D1 bars in displayed test: 935
- Starting comparison balance: USD 10,000
- No parameter optimization
- Signal is calculated at the daily close and allocation is applied with the
  repository's one-day lag.
- Normal regime holds `USTEC`; stress regime holds `XAUUSD`.
- There is no SL, TP, trailing stop, or percentage-risk trade sizing in the
  raw repository strategy.

## Raw result

| Scenario | Return | Final USD 10K | CAGR | Sharpe | Max DD |
|---|---:|---:|---:|---:|---:|
| Gross | +51.13% | $15,112.58 | 11.77% | 0.67 | 25.30% |
| Repository base costs | +46.11% | $14,611.02 | 10.76% | 0.62 | 25.31% |
| Repository stress costs | +37.73% | $13,773.24 | 9.01% | 0.54 | 25.33% |
| USTEC buy and hold | +91.84% | $19,183.85 | 19.19% | 0.99 | 25.30% |
| XAUUSD buy and hold | +126.67% | $22,666.88 | 24.68% | 1.23 | 27.70% |

Base-cost holding statistics: 13 uninterrupted holdings, 9 wins, 4 losses,
69.23% win rate, 4.71 segment profit factor, five maximum consecutive wins,
and one maximum consecutive loss. The small sample makes those trade-level
figures unstable.

The strategy made 12 allocation switches: six entries into the gold stress
leg and six exits. Effective exposure was 77.11% USTEC and 22.89% XAUUSD.
The final signal and effective holding on 2026-09-11 were both Normal/USTEC.

## Cost limitation

The base and stress cases use the upstream repository's percentage cost
assumptions: 12 bps or 33 bps per unit of turnover plus its daily carry
assumptions. They are not reconstructed Exness commission and swap charges.
An executable MT5 validation would be required before treating the result as
broker-net evidence.

## Decision

Do not add this raw version to the active system yet. Although it reduced the
gold-only drawdown slightly, its return, Sharpe and Calmar were below both
single-leg benchmarks, and the apparent 69.23% win rate comes from only 13
multi-day holdings. It may still be useful later as a risk-regime overlay, but
that would be a new optimized variant rather than the untouched paper logic.

The upstream repository is all-rights-reserved and permits only private,
non-commercial educational use without written authorization. Do not publish,
sell, or distribute an implementation without the author's permission.

