# DMC Cheat-Sheet Rules — Regime/Origin-Held Research

## Decision

**Do not replace either current DMC with the screenshot-enhanced regime gate.** On XAU it produced an attractive 80% locked win rate, but that came from only five trades. Across the nominal three-year window it reduced Fresh Reaction from 55 to 19 trades, lowered return from +35.84% to +10.92%, lowered PF from 2.46 to 2.28, and increased drawdown from 4.22% to 5.56%. On the currently connected US100 symbol the gate produced no trades, and that symbol has insufficient backfill for a valid three-year conclusion.

Nothing in the active EAs, BAT installers or website was changed.

## Mechanical translation of the screenshot

- **Buy a level once / pass-throughs weaken it:** retained the already-validated fresh-reaction gate (maximum one prior M15 touch). Strict first-touch was previously weaker on XAU development data.
- **Higher-timeframe levels win:** retained the validated W1/MN1 body-level proximity filter within 0.25 D1 ATR.
- **Origin-to-distal level must hold / know trend and range:** tested a no-lookahead D1 Markov regime proxy. It only permits a long or short when transitions learned strictly from earlier completed D1 states support that direction. The screenshot does not define a mechanical origin-picking rule, so this is explicitly a proxy rather than a claim to reproduce the author's discretionary chart marking.
- **Each level has an attached target:** not re-enabled. The prior 1.7R–3R structural-room tests collapsed the trade sample and were rejected.

## Matched side-by-side — untouched locked year

| Asset / version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| XAU current DMC control | +12.18% | 1.18 | 40.52% | 9.94% | 116 | 1.82 | 1.02 |
| XAU Fresh Reaction currently saved | +6.88% | 1.90 | 46.67% | 3.11% | 15 | 2.62 | 2.03 |
| XAU screenshot regime proxy | +7.70% | 9.36 | 80.00% | 1.93% | 5 | 0.77 | 3.64 |
| US100 Fresh Reaction currently saved | +3.71% | 1.89 | 66.67% | 2.99% | 12 | 1.40 | 1.19 |
| US100 screenshot regime proxy | +0.00% | 0.00 | 0.00% | 0.00% | 0 | 0.00 | 0.00 |

## Matched side-by-side — full three years

| Asset / version | Return | PF | Win rate | Max DD | Trades | Sharpe | Recovery |
|---|---:|---:|---:|---:|---:|---:|---:|
| XAU current DMC control | +50.71% | 1.29 | 41.30% | 12.40% | 247 | 1.63 | 3.19 |
| XAU Fresh Reaction currently saved | +35.84% | 2.46 | 60.00% | 4.22% | 55 | 3.74 | 6.94 |
| XAU screenshot regime proxy | +10.92% | 2.28 | 52.63% | 5.56% | 19 | 2.71 | 1.80 |
| US100 Fresh Reaction currently saved | +5.74% | 2.35 | 69.23% | 2.99% | 13 | 2.40 | 1.81 |
| US100 screenshot regime proxy | +0.00% | 0.00 | 0.00% | 0.00% | 0 | 0.00 | 0.00 |

## Development-only regime screen

| Asset | Variant | Return | PF | Win rate | Max DD | Trades |
|---|---|---:|---:|---:|---:|---:|
| XAU | markov-20d-5pct | -3.04% | 0.00 | 0.00% | 3.38% | 3 |
| XAU | markov-40d-5pct | +6.06% | 2.32 | 50.00% | 2.91% | 10 |
| XAU | markov-60d-5pct | +4.44% | 1.68 | 46.15% | 5.41% | 13 |
| US100 | markov-20d-5pct | +0.00% | 0.00 | 0.00% | 0.00% | 0 |
| US100 | markov-40d-5pct | +0.00% | 0.00 | 0.00% | 0.00% | 0 |
| US100 | markov-60d-5pct | +0.00% | 0.00 | 0.00% | 0.00% | 0 |

## Frozen candidates

- XAU: markov-60d-5pct
- US100: no viable candidate; all three regime windows produced zero trades on the available history.

## Monte Carlo — three-year frozen candidates

| Asset | P(profit) | Return P5 / median / P95 | DD median / P95 | Trades |
|---|---:|---:|---:|---:|
| XAU | 95.55% | +0.13% / +10.97% / +20.92% | 2.71% / 6.10% | 19 |
| US100 | 0.00% | +0.00% / +0.00% / +0.00% | 0.00% / 0.00% | 0 |

## Test conditions

Current connected Exness Trial15 account, native MT5, `XAUUSDr` / `USTECr`, USD 10,000, 1% dynamic equity risk, H1, matched symbols and sessions, development 2023-09-01 through 2025-08-31, untouched lock 2025-09-01 through 2026-09-01, and exact three-year reference 2023-09-01 through 2026-09-01. Locked and three-year runs use Every Tick with random execution delay and recorded broker costs.

## Data-quality limitation

The locked XAU reports have 99% history quality and are the cleanest new evidence. The nominal three-year XAU reports show 34% history quality on the current account, while the development screens show 3%; those longer figures are useful only as directional references. The current `USTECr` report contains 6,936 H1 bars (roughly one year of market history), so its row must not be represented as genuine three-year coverage.

Historical results are not guaranteed future profitability.
