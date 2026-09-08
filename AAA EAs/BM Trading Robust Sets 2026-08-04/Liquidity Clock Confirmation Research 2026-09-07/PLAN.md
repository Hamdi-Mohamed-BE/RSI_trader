# Step 3 — Liquidity-Clock Confirmation

Research-only veto overlay. No production EA, SET, BAT, website or portfolio
file may change before review and native confirmation.

## Goal

Test whether the most recent completed M5 broker tick count is unusually high
relative to the same five-minute clock slot on prior trading days. This differs
from a simple rolling-volume average, which confuses normal session changes
with exceptional activity.

## Scope

- Current LTA Volume Profile XAU native trade ledger.
- All available optimized LVN native ledgers.
- All available active ORB configuration ledgers.
- Development: 2023-09-01 through 2025-08-31.
- Untouched locked year: 2025-09-01 through 2026-08-31.
- Same-clock lookbacks: 10, 20 and 40 prior observations.
- Minimum activity ratios: 0.50 through 1.50, plus the unchanged baseline.

## Gate

The overlay must be chosen on development only, retain an adequate sample,
then improve locked PF and drawdown without reducing locked return. A positive
Monte Carlo P5 and adequate trade count are required before any native-EA
implementation is considered.

This first pass is deliberately a trade-ledger veto reconstruction. It can
remove a historical entry but cannot invent later entries that a skipped live
position might have allowed. Any passing result therefore still requires a
copied-EA implementation and native MT5 replay before promotion.
