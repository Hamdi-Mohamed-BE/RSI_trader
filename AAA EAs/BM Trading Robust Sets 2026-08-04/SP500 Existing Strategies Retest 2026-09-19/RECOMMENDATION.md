# Review checkpoint — S&P 500 transfer

Twelve active ORB/US100 presets were independently retested on the dynamically resolved US500 contract, using the connected Exness Zero demo account's contract and native costs. Dates: 2025-09-19 to 2026-09-19 exclusive. USD 10,000 per test, unchanged 1% standalone base risk, 150 ms native execution delay. Only DMC's broker-clock bindings changed. All original sources/includes/SETs remained unchanged; all twelve native ledgers reconcile.

This completes the requested initial S&P 500 transfer screen, not a US500 optimization or deployment pipeline. The archived research variants and non-US100, non-ORB EAs were outside the agreed scope.

## Candidates worth further validation

1. **Nasdaq Overnight transferred to US500:** +5.75%, 74 trades, 68.92% net win rate, PF 1.92, 1.21% maximum observed equity drawdown. Best conservative result in this sample. The 2% price-distance emergency stop means the 1% planned loss budget is much larger than a typical overnight loss; do not mistake this for a guarantee of future small losses. Net profit includes $108.47 swap and $13.44 commission. January-onward entries remained positive, PF 1.74.
2. **H1 ORB 13UTC transferred to US500:** +16.83%, 69 trades, 53.62% wins, PF 1.50, equity DD 9.26%. Best ORB candidate in this screen. January-onward entries remained positive, PF 1.38. No overnight trades or observed late session exits in this run.
3. **Month End Flow transferred to US500:** +10.60%, 34 trades, 47.06% wins, PF 1.61, equity DD 5.39%. Promising but a small sample; requires a longer-period test. One overnight holding and market-closed messages require review of actual session exits.

## Watch or skip

- **5M Candle Momentum:** highest return (+21.74%, 256 trades), but PF only 1.12 and equity DD 12.78%. January-onward PF weakens to 1.06. There were 11 session exits over one minute late and 8 overnight holds, with broker market-closed errors. Not the strongest risk-adjusted candidate and not proof of a strict intraday-only strategy.
- **Sell Nasdaq dynamic:** +8.14% overall, but January-onward entries lose $258.02 with PF 0.86. Watch/research, not promotion.
- **XAU overlap M30 preset:** +0.84%, PF 1.11, 22 trades; too weak/small overall for promotion.
- The negative transfers and zero-trade XAU New York M30 preset do not justify deployment as-is. A zero-trade result provides no win-rate or profitability evidence.

## Evidence limitations

- All twelve MT5 reports show 71% real-tick quality; real ticks begin 2026-01-01. Earlier dates use generated ticks. This is not one year of complete real-tick validation.
- Spread, commission and swap are recorded native costs. A fixed 150 ms delay is a simulation assumption, not measured live slippage.
- These are independent accounts, not all EAs trading one shared account. Returns cannot simply be added.
- Minimum volume/upward rounding can exceed the saved 1% risk. Native relative and tick-observed equity DD are both retained; the larger is reported.
- Technical reconciliation passing does not establish future profitability or eliminate strategy/model risk.

## Next stage requested by user

Gold overnight **Value Area** remains research-only and has **not** been added to any BAT, website portfolio or live terminal. Its full pipeline is next after this S&P comparison/review: wider historical coverage, frozen baseline, causal parameter search, chronological validation, parameter-neighbor and execution-cost stress, native confirmation, then a documented promotion decision. The already-viewed one-year raw result must not be relabeled an untouched holdout. Do not deploy Gold merely because the raw year was positive.

Results, detailed settings, monthly USD, cost tables and execution caveats: `RESULTS.md`. Independent ledger checks: `VERIFICATION.md`. Full raw native artifacts and per-trade data: `native/`.
