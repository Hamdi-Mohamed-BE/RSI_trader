# Raw EMA + anchored VWAP pullback

Highest raw one-year net return: Gold (+6.20%). This ranks this frozen adaptation only, not the original trader or a verified live edge.

| Asset | Window | Net return | Net PF | Win rate | Positions | Equity DD | Closed DD | Closed Sharpe | Max win/loss run | Mean net R | Win-rate95% CI |
|---|---|---|---|---|---|---|---|---|---|---|---|
| US100 | 1y | -10.92% | 0.219 | 13.9% | 36 | 12.94% | 11.43% | -3.49 | 2 / 14 | -0.645 | 6.1–28.7% |
| US100 | 3m | -3.13% | 0.306 | 18.2% | 11 | 4.16% | 3.71% | -3.47 | 1 / 7 | -0.586 | 5.1–47.7% |
| US30 | 1y | -8.71% | 0.428 | 22.0% | 41 | 16.24% | 9.74% | -2.28 | 2 / 10 | -0.443 | 12.0–36.7% |
| US30 | 3m | -3.46% | 0.113 | 20.0% | 10 | 4.10% | 3.85% | -4.94 | 1 / 5 | -0.715 | 5.7–51.0% |
| UK100 | 1y | +5.49% | 1.552 | 18.5% | 27 | 15.28% | 6.84% | 0.50 | 2 / 10 | 0.448 | 8.2–36.7% |
| UK100 | 3m | -3.87% | 0.000 | 0.0% | 9 | 4.70% | 3.87% | — | 0 / 9 | -0.882 | 0.0–29.9% |
| Gold | 1y | +6.20% | 2.018 | 33.3% | 24 | 10.70% | 2.24% | 1.01 | 2 / 5 | 0.780 | 18.0–53.3% |
| Gold | 3m | -1.48% | 0.174 | 16.7% | 6 | 3.22% | 1.80% | — | 1 / 5 | -0.537 | 3.0–56.4% |
| BTC | 1y | -1.70% | 0.795 | 34.5% | 29 | 8.03% | 5.10% | -0.35 | 2 / 8 | -0.132 | 19.9–52.7% |
| BTC | 3m | -0.18% | 0.804 | 60.0% | 5 | 4.17% | 0.52% | — | 2 / 1 | -0.085 | 23.1–88.2% |

- Mechanical adaptation of a discretionary STOCK strategy to broker CFDs and BTC. It does not reproduce stock/theme selection, first-pullback judgement, minute-precise anchors or subjective exits. No parameters were optimized.
- Each asset/window starts independently at$10,000 with no inherited positions, not a shared portfolio. The3month run is a fresh start, not just a slice of the1year ledger.0.5%balance risk is a requested initial-stop budget; fees, adverse fills and gaps can exceed it. Minimum-lot rounding isDOWN; unaffordable trades are skipped.
- Isolated Exness-MT5Trial16 research terminal; active account isExness-MT5Trial15 and was not changed. Native Model4 requested with150ms delay and recorded spread/commission/swap. History-quality percentages include400days of no-trading warmup. Inspect per-run real-tick start dates in SUMMARY.json; pre-2026 ticks may be generated. No measured extra-cost stress yet.
- AVWAP is a broker tick-volume, completed-H1 typical-price proxy anchored at a confirmed D1 pivot, not exchange trade volume. Daily EMA/ATR features and anchors use only information available before entry.
- Same NY09:30–11:30 weekday entry window on all assets; UK100 is not tested at the London open. This is intentional baseline comparability, not an asset-specific session optimization.
- Daily9EMA runner exit plus20%-original-volume trims at3R/5R. Shorts use the same management, unlike the discretionary faster covering in the interview. Small volume can prevent valid partial exits.
- A position can have multiple exit deals; win rate, PF and trade counts here use NET completed positions, not winning exit-deal counts. Closed charts attribute all costs/partials to final close; native equity DD includes the actual floating path.
- One-year and three-month windows overlap. The recent window is not independent validation. Raw profit alone is not a promotion/pass/payout claim. No long-history pipeline or Monte Carlo requested or run here.
- End-of-test liquidations and carryovers are counted in the coverage table, not removed. A long runner near the boundary may affect net outcomes.
- UK30 is absent from the connected broker symbol list; no fake result or UK100 substitution. All live charts, BATs, website catalogue, FTMO presets and remote Git remain unchanged.
