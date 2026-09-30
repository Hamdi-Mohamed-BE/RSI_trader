# FTMO 13-EA risk comparison — frozen 2026-09-29

Offline research only. No trading terminal, orders, settings or deployment changes.

Use the unchanged current-13 saved entry/exit streams and minute price history from the Daily Equity Controls Audit, recent-prepared.npz. Preserve the existing audit files. Period: 2025-09-27 through 2026-09-25, approximately one year. These are historical source-trade overlays, not independent native full-EA portfolio reruns or an out-of-sample validation.

Primary comparisons on initial USD 10,000, News OFF:

| Policy | Initial-stop risk per accepted trade | Daily equity loss close | Daily equity profit close |
|---|---:|---:|---:|
| Prior benchmark | $50 / 0.5% initial | $200 / 2% | $400 / 4% |
| Requested | $150 / 1.5% initial | $500 / 5% | $800 / 8% |
| Requested with buffer | $150 / 1.5% initial | $400 / 4% | $800 / 8% |
| Middle-risk diagnostic | $100 / 1% initial | $300 / 3% | $800 / 8% |

These fixed-risk comparisons preserve the earlier benchmark's sizing convention. Also run the requested settings with risk recalculated at 1.5% of current equity as a sensitivity. Risk budgets exclude fees, slippage and gaps, and sizes round down to available lot steps; trades below minimum size or above margin availability are skipped. No aggregate open-risk cap is added. These controls replace, rather than stack with, the original BAT governors, matching the prior audit. Daily control amounts and FTMO loss amounts stay anchored to initial $10,000, relative to Prague-midnight balance. Open P/L and estimated costs count.

The FTMO account fails when observed equity crosses its independent $500 daily or $1,000 total loss limits. A $500 internal stop is not a safety buffer. Liquidation happens at the next available minute open, with a five-minute alternative. Minute OHLC adverse envelopes flag possible additional intra-minute failures, not confirmed synchronized equity breaches. No results after a modeled failure count toward account success.

Run reference costs, higher costs, higher costs plus 10% weaker trade outcomes, and five-minute liquidation. Reuse prior conservative FTMO Swing margin/commission assumptions. Continuous full-period runs and weekly-start phase/reward paths are separate experiments.

Lifecycle: +10% phase 1 and +5% phase 2, four distinct opening days each, flat to pass. Assume two business days between phases, five before funding. First reward request at least 14 calendar days after first funded entry, flat, at least $50 profit. Model 80% trader share, full profit withdrawal, and two business days between funded cycles. These are assumptions, not service promises. Challenge fees, refunds, taxes, rejection/payment processing and retries excluded. Use only full 180-day windows for headline rates. Starts overlap and are not independent trials or future probabilities. Timing is conditional on completion; failures and unresolved paths remain in payout-rate denominators.

Verify copied-engine defaults reproduce the old engine and saved baseline; run synthetic sizing/loss-boundary tests and accounting checks for all stages. Keep raw metrics, paths, input hashes and limitations with the report. No parameter search or cherry-picking beyond these predeclared comparisons.
