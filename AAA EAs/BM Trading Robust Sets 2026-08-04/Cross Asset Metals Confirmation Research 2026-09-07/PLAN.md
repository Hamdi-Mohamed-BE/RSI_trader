# Step 4 — XAU/XAG Cross-Asset Confirmation

Research-only confirmation overlay. No EA, SET, BAT, website, cache, or
recommended-portfolio file may change before the untouched-period gate passes
and the user reviews the result.

## Goal

Test whether completed XAUUSD and XAGUSD daily information can improve existing
metal strategy entries after the strategy itself triggers. The peer signal is a
veto only; it never creates a trade.

## Scope

- Existing recommended non-news XAU and XAG native-MT5 trade ledgers.
- Exact stored 1% risk outcomes; news EAs and the already gated XAU regime
  switch are excluded.
- Development selection: 2023-09-01 through 2025-08-31.
- Untouched locked year: 2025-09-01 through 2026-08-31.
- Full three-year context: 2023-09-01 through 2026-08-31.
- Maximum four concurrent metals positions (4% initial correlated risk).
- Only completed prior UTC daily closes are available to a new trade.

## Candidate confirmation families

- XAU/XAG directional agreement.
- Trade direction confirmed by the peer metal.
- Peer impulse normalized by recent volatility.
- Rolling-correlation plus peer-direction confirmation.
- Relative XAU/XAG ratio convergence and continuation.

The rule is selected once on the combined development portfolio. It is not
re-optimized per EA or on the locked year.

## Promotion gate

The selected rule must be non-baseline, retain at least 40% of locked trades and
80 locked trades, improve locked return and profit factor, not worsen drawdown,
remain profitable under an extra 0.05R per-trade cost, show a positive 5th
percentile in 5,000 block-bootstrap paths, and be positive in at least four of
the six consecutive half-year slices. A passing ledger gate would still need a
copied-EA implementation and native MT5 replay before deployment.
