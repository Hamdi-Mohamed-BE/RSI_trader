# USDJPY London Open Momentum: OOS windows + Monte Carlo (2026-11-04)

**Setup:**
- **EA:** production EX5 (`c36eb37aa963`) with the Full EA preset (`PLAN.json`): London 08:00, 60-minute formation, Wednesday–Friday, ADX20 + DI,
  5 ATR stop, break-even at 0.75R, 16:00 London time exit.
- **Test:** 1% risk, governor off. Native Model 4, $10k fresh per window, 150 ms.
- **Windows:** shared `data_split.py` windows to 2026-11-01. The OOS window was previously viewed, since the settings were chosen on this history.
- **Checks:** 4/4 runs OK, inputs applied, 0 rejected. Real ticks only from 2026-01-01.
- **Files:** `run.py` (native), `analyze.py` → `ANALYSIS.json`.

## Windows
| Window | Net | PF | Win % | Trades | / month | / weekday | Mean R | Closed DD | MT5 DD (maximal) | Losing streak | Best-day check |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| Dev 2019-01 → 2023-11 | +49.4% | 1.28 | 45.7% | 455 | 7.9 | 0.36 | +0.094 | 9.7% | 10.4% | 8 | PASS |
| Val 2023-11 → 2024-11 | +44.7% | 2.48 | 52.7% | 91 | 7.6 | 0.35 | +0.421 | 4.4% | 8.8% | 6 | PASS |
| OOS 2024-11 → 2026-11 | +25.5% | 1.44 | 46.0% | 185 | 7.7 | 0.36 | +0.128 | 4.8% | 5.8% | 6 | PASS |
| All 2019-01 → 2026-11 | +170.4% | 1.50 | 46.7% | 731 | 7.8 | 0.36 | +0.143 | 9.7% | 8.8% | 8 | PASS |

## Breakdown of all trades (2019-01 → 2026-11)
- **By year (R):**

  | 2019 | 2020 | 2021 | 2022 | 2023 | 2024 | 2025 | 2026 |
  |---:|---:|---:|---:|---:|---:|---:|---:|
  | −7.9 (PF 0.76) | +17.4 | +4.3 | +19.4 | +11.4 | +33.5 | +8.9 | +17.5 |

  7 of 8 years positive. Months: 59 of 94 positive; worst 2026-10 −2.7R, best 2026-04 +12.2R.
- **By weekday:** Wednesday +43.3R (PF 1.64), Thursday +38.7R (1.63), Friday +22.4R (1.23).
- **By side:** long +51.8R (PF 1.41, 411 trades), short +52.5R (PF 1.61, 320 trades).
- **By exit:**
  - 16:00 time exit: 487 trades (70% winners), +278R.
  - Initial stop: 173 trades, −173R.
  - Break-even stop: 71 trades, −1R.
- **Costs:** commission $955; swap $0, since trades close the same day.

## Monte Carlo
- **Three-way (1,000 runs):**
  - Full sample: reshuffle — real DD 10.1R, worse than only 16.6% of the shuffles, so the real order was kind. Plan from the shuffle
    p95 of 19.6R (about 20% at 1%).
  - Resample: 0% red (PASS); OOS sample 4.2% red (PASS, borderline).
  - Randomize (drop 10% + 0.05R): 0% red (PASS); OOS sample 0.3%.
  - One year (93 trades): resample 11.3% red; randomize 24.1% red (drop-only 11.2%, cost-only 22.6%).
  - Extra-cost ladder, one year: 0.02R 16% / 0.05R 24% / 0.10R 38% / 0.20R 68% red. Break-even extra cost 0.143R per trade.
- **Day-block bootstrap (10,000 paths):**
  - 3 months: 29% lose, median +2.6%.
  - 12 months: 11.5% lose, median +12.6%, 5th percentile −4.0%, DD p95 12.3%, losing streak p95 10.
  - Bootstrapping only the OOS window gives the same picture (12 months 12% lose).

**Verdict:**
- **Passes every stage-6 gate.**
  - The edge holds in validation and OOS and does not rely on a best day.
  - Long and short both make money.
- **Weaknesses:**
  - It is a low-frequency EA (about 1.8 trades a week), so one year is short: about 1 year in 9 loses.
  - All of the profit comes from the time exit; stops are full −1R losses.
  - Friday is the weakest day.
  - 2019 lost.

## Addendum: Monday and Tuesday (owner 2026-11-04)
**Why they are off:** the 2026-09-08 London Open pipeline weekday step chose Wednesday–Friday. It used development data
2021-09 → 2024-09, Model 1, before the ADX filter was added:

| Days | PF | Trades | Drawdown |
|---|---:|---:|---:|
| Wed–Fri (chosen) | 1.78 | 418 | 7.4% |
| Mon–Fri | 1.40 | 695 | 9.7% |
| Mon–Wed | 1.29 | 424 | 14.8% |

No market reason was recorded; it was a data-driven choice.

**Test (`run_days.py`, `days.py` → `DAYS.json`):**
- **Runs:** the same production EX5 / preset / windows with Monday and Tuesday ON (ALL5), 4 native Model 4 runs, 0 rejected.
- **Method:** trades close at 16:00 the same day, so the ALL5 ledger split by weekday is each day's own result.
- **Parity:** the ALL5 Wednesday–Friday entries equal the production entries in all 4 windows.

| Window | Production Wed–Fri: R / PF / trades | Mon–Fri: R / PF / trades | Monday: R / PF / n | Tuesday: R / PF / n |
|---|---|---|---|---|
| Dev 2019-01 → 2023-11 | +42.7 / 1.29 / 455 | +40.4 / 1.16 / 763 | +3.3 / 1.06 / 158 | −5.7 / 0.88 / 150 |
| Val 2023-11 → 2024-11 | +38.3 / 2.57 / 91 | +33.2 / 1.73 / 151 | +1.7 / 1.24 / 31 | −6.8 / 0.51 / 29 |
| OOS 2024-11 → 2026-11 | +23.6 / 1.44 / 185 | +16.7 / 1.18 / 301 | −3.0 / 0.84 / 64 | −4.3 / 0.79 / 52 |
| All 2019-01 → 2026-11 | +104.4 / 1.46 / 731 (7.8 / month) | +90.0 / 1.23 / 1,215 (12.9 / month) | +2.0 / 1.03 / 253 | −16.6 / 0.80 / 231 |

- **All period, % of account:** Wed–Fri +170.4% with R drawdown 10.1; Mon–Fri +130.4% with R drawdown 19.7.
- **Monday + Tuesday together:** −14.5R, PF 0.91 in every window.
- **By year (R):**
  - Monday: +1.8, +5.7, +1.3, −1.4, −6.5, +4.2, −7.1, +3.9.
  - Tuesday: −6.3, −4.4, −4.4, +9.8, −4.2, −2.9, −5.9, +1.8.
- **2019 → 2021-08 was not in the original selection:** Tuesday still lost there.
- **Three-way MC:**
  - Mon–Fri: one-year resample red 18% vs 11%; randomize red 40% vs 24%; shuffle p95 DD 30R vs 20R.
- **Verdict:** keep Monday and Tuesday OFF.
  - Monday is about flat (break-even after costs).
  - Tuesday loses.
  - Adding them raises trades by 66% but cuts profit and doubles the drawdown.
