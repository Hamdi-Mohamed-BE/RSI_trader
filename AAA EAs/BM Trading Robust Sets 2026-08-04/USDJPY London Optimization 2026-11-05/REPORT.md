# USDJPY London Open optimisation: result (2026-11-10)

**Verdict: REJECTED AT VALIDATION. Keep the deployed settings.** Plan frozen 2026-11-05 (PLAN.md); 364 native runs (RUNS.jsonl); research EA parity with production 731/731 trades.
Native, 150 ms, $10k, 1%. Development is Model 1 screening + the baseline in Model 4; validation and OOS are Model 4, each run once. Windows: dev 2019-01 -> 2023-11 (58 months),
validation 2023-11 -> 2024-11 (12 months), OOS 2024-11 -> 2026-11 (24 months, previously viewed). Trades/day uses 21 trading days per month.

| Version | Window | Return | PF | Trades | /month | /day | Win | Equity DD | Return/DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Current (deployed) | dev | +49.4% | 1.28 | 455 | 7.8 | 0.37 | 52.3% | 11.0% | 4.51 |
| Best dev (finalist 1) | dev (Model 1) | +85.6% | 1.34 | 589 | 10.2 | 0.48 | - | 8.4% | 10.14 |
| Current | validation | +44.7% | 2.46 | 91 | 7.6 | 0.36 | 58.2% | 8.8% | 5.07 |
| Finalist 1 | validation | +7.1% | 1.14 | 134 | 11.2 | 0.53 | 45.5% | 11.8% | 0.60 |
| Finalist 2 | validation | +6.8% | 1.14 | 134 | 11.2 | 0.53 | 44.8% | 11.9% | 0.57 |
| Finalist 3 (no Friday) | validation | +10.6% | 1.35 | 91 | 7.6 | 0.36 | 48.4% | 9.7% | 1.09 |
| Current | OOS | +25.5% | 1.44 | 185 | 7.7 | 0.37 | 50.3% | 5.8% | 4.36 |
| Finalist 3 (diagnostic only) | OOS | +31.0% | 1.60 | 167 | 7.0 | 0.33 | 50.9% | 8.0% | 3.89 |

Finalists change: 90-minute formation, exit 18:00 London, no minimum signal size, DI filter off, ATR x8 trail from +1R (or +1.5R), lock +0.25R at +1.5R; finalist 3 also skips Friday.
All three pass the plateau (100% of 22-23 neighbours profitable on dev) but none beats the current settings on validation, so no candidate reaches OOS or Monte Carlo.
The diagnostic OOS run of finalist 3 makes more money (+31.0% vs +25.5%) but with a deeper drawdown (8.0% vs 5.8%), so its return/DD is lower: it would not have passed the OOS gate either.
The current settings were chosen on 2021-24 data, so their validation lead is partly in-sample. Nothing installed or changed.
