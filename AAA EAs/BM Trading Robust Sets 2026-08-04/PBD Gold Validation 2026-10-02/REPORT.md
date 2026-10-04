# Gold PBD validation — NOT VALIDATED

Frozen rules, no optimisation.

| Window | Dates | Return | Net PF | Win rate | Native equity DD | Trades | Trades/mo | Trades/weekday | Closed Sharpe | Max W/L run | Tick quality |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 5 years | 2021.10.02 → 2026.10.02 exclusive | -11.44% | 0.912 | 46.3% | 32.13% | 285 | 4.75 | 0.219 | -0.21 | 8/8 | 15% real ticks |
| 3 years | 2023.10.02 → 2026.10.02 exclusive | -2.15% | 0.973 | 46.6% | 23.08% | 174 | 4.83 | 0.222 | -0.03 | 8/6 | 25% real ticks |
| Last year (parity) | 2025.10.02 → 2026.10.02 exclusive | +11.97% | 1.391 | 50.0% | 10.03% | 66 | 5.5 | 0.253 | 1.07 | 8/6 | 75% real ticks |
| 2026 real ticks | 2026.01.01 → 2026.10.02 exclusive | +17.64% | 1.764 | 54.7% | 6.05% | 53 | 5.89 | 0.27 | 1.84 | 8/6 | 100% real ticks |
| 6 months / original150ms | 2026.04.02 → 2026.10.02 exclusive | +17.58% | 2.179 | 55.9% | 5.48% | 34 | 5.66 | 0.26 | 2.45 | 8/6 | 100% real ticks |
| Last year / 500ms | 2025.10.02 → 2026.10.02 exclusive | +11.83% | 1.389 | 50.0% | 9.99% | 66 | 5.5 | 0.253 | 1.07 | 8/6 | 75% real ticks |
| 6 months / 500ms | 2026.04.02 → 2026.10.02 exclusive | +17.43% | 2.176 | 55.9% | 5.39% | 34 | 5.66 | 0.26 | 2.43 | 8/6 | 100% real ticks |

## Independent annual starts

| Window | Dates | Return | Net PF | Win rate | Native equity DD | Trades | Trades/mo | Trades/weekday | Closed Sharpe | Max W/L run | Tick quality |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Independent 2021–2022 | 2021.10.02 → 2022.10.02 exclusive | -1.39% | 0.952 | 48.3% | 9.68% | 58 | 4.84 | 0.223 | -0.11 | 4/8 | 0% real ticks |
| Independent 2022–2023 | 2022.10.02 → 2023.10.02 exclusive | -7.85% | 0.733 | 43.4% | 11.82% | 53 | 4.42 | 0.204 | -0.88 | 6/5 | 0% real ticks |
| Independent 2023–2024 | 2023.10.02 → 2024.10.02 exclusive | -11.56% | 0.630 | 44.1% | 15.05% | 59 | 4.91 | 0.225 | -1.60 | 4/6 | 0% real ticks |
| Independent 2024–2025 | 2024.10.02 → 2025.10.02 exclusive | -1.09% | 0.957 | 44.9% | 13.60% | 49 | 4.09 | 0.188 | -0.05 | 4/5 | 0% real ticks |
| Independent 2025–2026 | 2025.10.02 → 2026.10.02 exclusive | +11.97% | 1.391 | 50.0% | 10.03% | 66 | 5.5 | 0.253 | 1.07 | 8/6 | 75% real ticks |

## Conclusion and limitations

- Historical raw gate FAILED on both3y/5y: negative return, PF below1.15. No random controls, parameter search or promotion started.
- This verdict applies to the explicitly frozen Exness tick-volume PBD proxy, NOT every discretionary PBD model or genuine exchange order-flow profile.
- Exact original source preserved; fresh parity run matched all66 prior one-year positions, numeric trade fields and modules (deal identifiers excluded). No active EAs, terminals/accounts, BATs, website or Git remote changed.
- Independent reconstruction checked 897 positions across overlapping new windows and 235,680 exported M1 profile inputs. Zero nonzero exchange-real-volume bars. Both direction and D-extension rules remain unchanged.
- Exness real ticks start Jan2026.5y/3y execution is predominantly generated, with historic M1 spread/tick-volume assumptions. Annual older tests have0% real ticks. Profiles spread M1 quote-count volume uniformly over each bar range, not actual trades at prices. No second data source verifies this.
- All windows except disjoint annual comparisons overlap. The candidate was chosen after reviewing12 current asset/module combinations and broader prior ideas. This is a frozen historical extension, NOT an untouched prospective holdout.
- DD tables use native tick-path floating-equity drawdown. Closing plots and MC omit floating losses. The sampled equity graph is minute resolution. Neither bootstrap breach outputs nor historic profit frequencies are FTMO/live pass or payout forecasts.
- Separate fresh $10k per native run;1% requested pre-cost balance risk with floor lots. Fills/fees/gaps may exceed it. Do not sum independent test returns. Closed Sharpe uses realized daily changes, not native report Sharpe.
- Measured last-year adverse ENTRY friction sum$42.63; observed p95$21.5411/lot. Stress adds one extra such cost per traded lot, on top of costs already present. This is an observed broker entry-friction shock, not independently measured future spread/exit slippage.
- Native500ms changes simulated market-order/EA-close delay but not necessarily server-side stop/TP latency. It tests execution sensitivity, not a guaranteed future fill.
- Risk-unit MC compounds observed net returns at1%risk, ignoring changing lot floor and signal eligibility. Removal does not regenerate trades that might become eligible after a missed fill. Reshuffle changes DD/streaks, not compounded return.
- Canonical measured entry-friction shock, chronological consistency and statistical gates failed or remain insufficient. No true volume-at-price, matched-control advantage, pristine holdout or prospective demo. NOT LIVE ELIGIBLE.
