# Prop Ready on FTMO Swing: older history and bootstrap (2026-10-20)

Requested by the owner after the Bear review of the FTMO Dial Study ("yes run both").

**Verdict:** the 2025-26 year was unusually good for this portfolio.
- **At today's $50 risk:**
  - Over 2021-2025 starts, Prop Ready passed both FTMO phases within 180 days in only **31-43%** of starts. The median among passers was 108-119 days (115-126 days to funded).
  - The 5-year bootstrap gives **35-52%**, median 124-130 days.
- **At $100:** faster (median about 65-73 days) and more passes (**47-64%**). It **fails** the pre-declared older-history rule: completion is far below 95%, and the worst drawdown from peak reached $1,740-1,836.
- **Breaches:** none in any test, because the guard stops new entries near $9,200. The real failure mode is **stalling**, not breaching. 12-30% of $50 accounts and 50-59% of $100 accounts hit that entry buffer at least once.
- **2023 was nearly impossible:** only 1.9% of 2023 starts passed within 180 days at $50.

Nothing was changed in any package, guard, SET or terminal.

## Method

- **Data:** native 5-year candidate streams for the nine Prop Ready EAs, rebuilt with a generalised copy of the Faster Screen `prepare.py`.
  - Parity gate: the rebuilt 2025-10-06 to 2026-10-06 stream is **identical** to the Faster Screen inputs.
- **Engine:** the FTMO Dial Study `DialTrial` over the Faster Screen engine, with the same guard, costs, marks and FTMO 2-step Swing rules.
- **Part A, older replay:** every Prague weekday start with a full 180-day follow-up from 2021-10-07 to 2025-10-06, 915 starts.
  - Previously inspected history: the EAs were developed on overlapping years. These are not untouched data.
- **Part B, bootstrap:** 4-week, Monday-aligned blocks. 7 blocks make one 196-day path, cut at 180 days.
  - 2,000 paths per pool; FLAT50 and FLAT100 are run on identical paths.
  - Pools: 5 years, and the older 4 years only.
- **Pre-declared:** policies, rules and labels are in `PLAN.json`, and hashes in `FROZEN.json`, before any outcome. Two configurations were tested in this study.

"Pass" = both phases completed within the 180-day analysis horizon. FTMO itself has no time limit, but a stalled account near the $9,200 buffer cannot take new trades under the guard.

## Part A — older history replay (2021-10-07 → 2025-10-06, 915 starts)

| Policy | Costs | Handover | Breaches | Both phases ≤ 60 / 90 / 120 / 180 days | Unfinished at 180 d | Median days to both (completed) | Median days to funded | Phase 1 ≤ 60 d | Worst equity DD $ | Worst day $ | Distinct pass dates | Median trades (/month, /weekday) |
|---|---|---|---:|---|---:|---:|---:|---:|---:|---:|---:|---|
| FLAT50 | recorded | next day | 0.0% | 1.8% / 8.8% / 23.4% / 43.0% | 57.0% | 115 | 122 | 19.0% | 1,259 | 248 | 39 | 209 (38.72, 1.781) |
| FLAT50 | recorded | 2 business days | 0.0% | 1.5% / 12.3% / 27.8% / 43.1% | 56.9% | 108.5 | 115.5 | 19.0% | 1,259 | 248 | 33 | 207 (38.49, 1.77) |
| FLAT50 | stress | next day | 0.0% | 0.7% / 4.3% / 16.4% / 30.8% | 69.2% | 118.5 | 125.5 | 14.3% | 1,311 | 250 | 22 | 205 (38.39, 1.766) |
| FLAT50 | stress | 2 business days | 0.0% | 0.5% / 4.0% / 16.5% / 31.5% | 68.5% | 119 | 126 | 14.3% | 1,311 | 250 | 19 | 205 (38.05, 1.75) |
| FLAT100 | recorded | next day | 0.0% | 25.4% / 41.9% / 51.1% / 58.5% | 41.5% | 65 | 72 | 47.8% | 1,740 | 270 | 55 | 67 (30.44, 1.4) |
| FLAT100 | recorded | 2 business days | 0.0% | 25.1% / 42.0% / 50.6% / 58.5% | 41.5% | 66 | 73 | 47.8% | 1,740 | 270 | 53 | 66 (29.5, 1.357) |
| FLAT100 | stress | next day | 0.0% | 21.9% / 32.7% / 40.3% / 46.9% | 53.1% | 65 | 72 | 37.6% | 1,836 | 256 | 43 | 60 (23.0, 1.058) |
| FLAT100 | stress | 2 business days | 0.0% | 20.9% / 34.0% / 40.0% / 47.1% | 52.9% | 66 | 73 | 37.6% | 1,836 | 256 | 37 | 61 (23.0, 1.058) |

### By start year (recorded costs, next-day handover)

| Policy | Start year | Starts | Both ≤ 180 d | Median days to both | Breaches | Worst equity DD $ |
|---|---|---:|---:|---:|---:|---:|
| FLAT50 | 2021 | 62 | 35.5% | 161.5 | 0.0% | 976 |
| FLAT50 | 2022 | 260 | 41.5% | 120.5 | 0.0% | 1,110 |
| FLAT50 | 2023 | 260 | 1.9% | 177 | 0.0% | 1,259 |
| FLAT50 | 2024 | 262 | 71.4% | 109 | 0.0% | 1,012 |
| FLAT50 | 2025 | 71 | 100.0% | 95 | 0.0% | 496 |
| FLAT100 | 2021 | 62 | 40.3% | 141 | 0.0% | 1,194 |
| FLAT100 | 2022 | 260 | 90.4% | 77 | 0.0% | 1,140 |
| FLAT100 | 2023 | 260 | 15.0% | 109 | 0.0% | 1,740 |
| FLAT100 | 2024 | 262 | 67.2% | 50 | 0.0% | 1,584 |
| FLAT100 | 2025 | 71 | 84.5% | 50.5 | 0.0% | 1,057 |

FLAT100 survives the pre-declared older-history rule: **False**


## Part B — 4-week block bootstrap (2,000 paired paths per pool, seed 20261020; 1 end-censored candidates excluded)

| Pool | Policy | Costs | P(breach) | P(both ≤ 60 / 90 / 120 / 180 d) | P(unfinished at 180 d) | Median days to both | Median days to funded | Equity DD p95 / p99 $ | Worst day p95 / p99 $ | Median trades (/month) |
|---|---|---|---:|---|---:|---:|---:|---|---|---|
| 5y | FLAT50 | recorded | 0.0% | 2.0% / 10.8% / 23.2% / 51.5% | 48.4% | 124 | 131 | 985 / 1,224 | 177 / 248 | 207 (38.52) |
| 5y | FLAT50 | stress | 0.0% | 1.2% / 6.5% / 14.5% / 35.4% | 64.6% | 130 | 137 | 1,082 / 1,311 | 188 / 250 | 216 (38.39) |
| 5y | FLAT100 | recorded | 0.0% | 24.9% / 43.9% / 54.8% / 63.6% | 36.4% | 71 | 78 | 1,358 / 1,652 | 242 / 257 | 76 (32.59) |
| 5y | FLAT100 | stress | 0.0% | 18.4% / 33.4% / 41.3% / 49.6% | 50.4% | 73 | 80 | 1,454 / 1,670 | 256 / 271 | 74 (30.44) |
| older4y | FLAT50 | recorded | 0.0% | 1.5% / 7.1% / 17.5% / 40.5% | 59.6% | 128 | 135 | 1,059 / 1,259 | 177 / 248 | 218 (38.93) |
| older4y | FLAT50 | stress | 0.0% | 1.1% / 4.5% / 10.2% / 25.1% | 75.0% | 131 | 138 | 1,174 / 1,380 | 188 / 250 | 222 (38.55) |
| older4y | FLAT100 | recorded | 0.0% | 21.9% / 38.0% / 46.6% / 54.4% | 45.6% | 68 | 75 | 1,416 / 1,675 | 239 / 242 | 71 (31.8) |
| older4y | FLAT100 | stress | 0.0% | 16.7% / 29.1% / 35.4% / 41.3% | 58.7% | 68 | 75 | 1,510 / 1,727 | 249 / 256 | 65 (21.81) |

FLAT100 P(breach) ≤ 5% in all pools and cost scenarios: **True**; ≤ 1%: **True**


## What this does NOT prove

- **Not untouched data.** All years were previously inspected, and the basket and EA settings were chosen with knowledge of them.
- **The bootstrap only reshuffles history.** It re-orders the historical signals in 4-week blocks; it does not create new market paths. Cross-block dependence is weakened.
- **Simulated fills and costs.** Prices come from Exness tester data with generated ticks before 2026, equity is sampled every 5 minutes, and costs are modelled rather than FTMO's own.
- **Real-terminal behaviour is not modelled.** Skipped entries cannot create the new signals they would have triggered, and the real guard can behave differently from the model (see the dial study's Bear review).

## Files

- [PLAN.json](PLAN.json), [FROZEN.json](FROZEN.json), [prepare.py](prepare.py), [run.py](run.py), [tables.py](tables.py).
- [OLDER-SUMMARY.json](OLDER-SUMMARY.json) and `OLDER.json.gz` (per-start rows).
- [BOOTSTRAP-SUMMARY.json](BOOTSTRAP-SUMMARY.json).
- `SOURCES.json`, which records the parity PASS and the source hashes.
