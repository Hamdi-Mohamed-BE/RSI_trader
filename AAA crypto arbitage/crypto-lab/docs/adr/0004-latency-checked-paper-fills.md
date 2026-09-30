# ADR 0004: Latency-checked paper fills and honest metrics

- **Status:** Accepted (2026-09-29)

## Context
Arbitrage detections are easy to overstate. Filling a paper trade at the same prices that triggered the detection
assumes zero latency and no competition, which makes almost every detection look profitable. Social-media claims
that motivated this project (e.g. "$2K → $11K overnight") have no verifiable trade history.

## Decision
- A PAPER fill is priced from a **second order-book fetch** taken `paper_latency_ms` (default 1.5 s) after
  detection, at the **same size**, with the market's own **fee schedule** charged **per matched level**.
- If the edge is gone, the attempt is recorded as **missed**, with the reason. If paper capital is insufficient, it
  is also recorded as missed. The filled-to-missed ratio is a first-class metric.
- Book freshness uses the **local receive time**. The CLOB `timestamp` is the last book change, so quiet but
  current books must not be discarded.
- Each scan records **near-miss** sums (lowest YES+NO ask, highest YES+NO bid), so "no opportunities" is visible as
  a measured distance, not silence.
- Results use one standard table (trades, per month/day, return, PF, win rate, consistency, streaks, Sharpe,
  balance DD). **Missing data is shown as missing**: equity DD is *n/a* until mark-to-market exists.

## Alternatives considered
- *Fill at detection prices*: simpler, but systematically optimistic.
- *Full queue and latency simulation on recorded L2 data*: more realistic. Planned once recordings exist; the
  current model is a first, coarse filter.

## Consequences
- \+ Paper results are conservative by construction and comparable across runs.
- − Queue position, partial fills, merge/split gas and relayer limits are still unmodelled.
  `extra_cost_per_leg_usdc` provides a manual allowance until a recorded-data simulator exists.
