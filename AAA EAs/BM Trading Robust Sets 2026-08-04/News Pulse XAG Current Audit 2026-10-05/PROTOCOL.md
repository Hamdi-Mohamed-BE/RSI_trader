# News Pulse XAG — exact-current diagnostic audit

Frozen before results, 5 October 2026. Research only. No production/BAT/website/account changes.

## Control and rules

The control is the exact shipped Multi Asset Event v2.21 EX5 and the normal installer's 12B XAG two-sided SET. Its August replay is compared trade-for-trade to a tester-only instrumented copy. The copy adds diagnostics and a receipt-backed tester calendar, not trading rules. No optimisation is authorised by a favourable diagnostic number alone.

USD 10,000, Exness XAGUSD/M1, leverage 1:2000, Model 4, current broker costs. 0.75% equity per enabled side, both sides remain armed (not OCO). Upward/minimum lot rounding unchanged. No Markov/dynamic/adaptive gates. Cash risk is not a guaranteed loss ceiling.

The asset/event overrides, not the fallback SET geometry, apply:

| Event | Lead | Anchor | Price offset | Price SL distance | Trailing | Liquidation |
|---|---:|---|---:|---:|---|---|
| NFP | 15s | current Ask/Bid | 0.12 | 0.02 | off | release +60s |
| CPI | 10s | previous completed M1 high/low | 0.02 | 0.02 | off | release +60s |
| FOMC | 120s | previous completed M1 high/low | 0.12 | 0.02 | starts +0.5R, gap 0.40 | release +60s |

Definitive placement rejection repairs from a fresh quote, then same-side market fallback. Unknown execution must reconcile, not blind-retry. Broker geometry may widen the stop. This audit is not a live-chart installation check.

## Frozen cases

Separate USD 10,000 starts; UTC [inclusive start, exclusive end].

- Original and audit parity: 2026-08-01 → 2026-09-01, 150ms.
- Year: 2025-10-05 → 2026-10-05, 150ms.
- Six months: 2026-04-05 → 2026-10-05, 150ms.
- Three months: 2026-07-05 → 2026-10-05, 150ms.
- Three-month request-latency sensitivity: same dates, 3000ms. Not an alternate strategy and not additional pending-trigger server latency.

## Integrity and gates

Exclusive OS lease and the isolated tester only; empty chart profile, live Experts disabled, cloud/remote off. Never connect to or restart active terminals. Compile zero errors/warnings. Freeze production/helper/SET/calendar receipt and research hashes. Exact report inputs/date/symbol/delay checked. Native full deal rows, full position cash, exposure and final account reconcile. Streaks follow final native closing-deal sequence. Record native symbol contract/tick specifications and OrderCalcProfit request geometry; independently check cash conversion against every exit deal before reporting actual initial risk.

All events in the official receipt-backed schedule remain in setup denominator, even if untradable. Classify missing sessions separately; do not quietly delete them after results. Require no unexplained duplicate accepted side, uncertainty, liquidation or trailing errors for execution qualification. Record liquidation lateness; operational allowance 2× delay +2s is an audit tolerance, not permission to extend the strategy's 60-second design. Report actual initial stop exposure divided by pre-send cash budget and realised loss separately.

Recent tests are descriptive. Before any 3-/5-year optimisation, credible historical event-second bid/ask and pre-release calendar availability must be established. Known XAU history limitations are not assumed to prove XAG's dates; inspect XAG's own journals. If the XAG year uses generated/absent event-time ticks, do not launch 3-/5-year searches. Mark older tests NOT RUN at the input-quality gate, not failed measured returns. Do not tune on mixed news ticks, invent a control advantage, run Monte Carlo promotion or issue FTMO/payout forecasts. Raw pipeline 3-/5-year positive/PF≥1.15/≥30 positions and independent control are prerequisites, not substitutes for input integrity. Historical event-specific XAG selection was fitted through September 2026; overlapping returns are in-sample, not independent validation.

The calendar reuses the previously captured official BLS/Fed archive and FXMacroData receipts (fresh receipt history begins 2026-07-27 and is truncated). No macro actuals/forecasts/revisions or manually assumed release times. Before-order live historical schedule availability is unproven.

Stop after this EA for user review. No new BAT, live deployment, removals or Git write operations.
