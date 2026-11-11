# Gold Band Wave optimisation: result (2026-11-11)

**Verdict: REJECTED IN DEVELOPMENT. Keep the current (raw) rules.** Plan frozen 2026-11-10 (PLAN.md); 39 native runs (RUNS.jsonl).
Parity: path-only. All 455 trades have identical times, sides and prices to the raw EA. The tester's XAUUSD swap rate changed after the raw run (swap -$1,731.85 raw vs -$1,696.34 now), which also changed 3 lot sizes (PARITY.json).
XAUUSD H4, native, 150 ms, $10k, 1%. Windows: dev 2019-01 -> 2023-11-11 (58.3 months), validation -> 2024-11-11 (12), OOS -> 2026-11-11 (24, previously viewed). 21 trading days per month.

**Why it stopped:** the search keeps a stage's change only if it reaches PF >= 1.15 with >= 100 trades and a profit on development. The current rules lose slightly on 2019-23 (-2.6%, PF 0.98).
None of the 34 one-step changes (timeframe, bands, deviation, signal, trend filter, stop, target, exit, management, direction) came close: the best had PF 1.05 (stop 1 ATR: +10.2%, DD 25.1%).
Only 6 of 34 were profitable. With nothing eligible, the search never combined changes, so combinations are untested (a limit of the frozen method, disclosed).

| Version | Window | Return | PF | Trades | /month | /day | Win | Equity DD |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| Current | dev | -2.6% | 0.98 | 293 | 5.0 | 0.24 | 41.3% | 19.3% |
| Best one-step change (stop 1 ATR) | dev (Model 1) | +10.2% | 1.05 | 293 | 5.0 | 0.24 | - | 25.1% |
| Current | validation | +22.7% | 2.01 | 55 | 4.6 | 0.22 | 50.9% | 6.7% |
| Current | OOS | +27.3% | 1.48 | 107 | 4.5 | 0.21 | 47.7% | 9.7% |
| Current | all 2019-01 -> 2026-11 | +49.4% | 1.22 | 455 | 4.8 | 0.23 | 44.0% | 19.3% |
| Buy and hold XAUUSD CFD | all | +116.5% | - | 1 | - | - | - | 48.8% |

Monte Carlo on the current rules, all years: resample 6.3% red (gate <= 5%: FAIL), randomize 2.0% (pass); same as the raw study.
Buy and hold: gold dev -16.9% (swap -69.4%), validation +28.3%, OOS +43.9%, all +116.5% with a 48.8% drawdown. GBW makes less money than holding gold, with a much smaller drawdown (19% vs 49%).
All of the current rules' profit comes from 2023-11 onwards (gold bull market). Nothing installed or changed.
