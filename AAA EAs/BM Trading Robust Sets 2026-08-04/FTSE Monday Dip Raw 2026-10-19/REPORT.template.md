# FTSE 100 Monday dip + stretch-below-mean — RAW test report, 2020–2023 (2026-10-19)

**Verdict: RAW GATE FAILED.** Rule 1, Rule 2 and both rules together all lose money over 2020–2023. No version survives to optimisation.

- **Rule 2 is no better than random.** "Far below the 40-hour average, RSI < 35" does about as well as random long entries with the same exits:
  - Rule 2 alone: PF 0.77.
  - Random-entry controls: PF 0.65–0.77.
- **Rule 1 (Monday dip) is flat to slightly negative:** −1.02%, PF 0.97, 104 trades.
  - It does beat the same rule run Tuesday–Friday (PF 0.65), so Mondays are relatively better.
  - It made money only in 2020 (+7.11%) and lost in 2021, 2022 and 2023.
  - It is slightly positive before commission and swap: +$197 gross against −$299 of costs.
- **All seven declared threshold changes also lose** (−28% to −55%), and none has a single positive year.
  - The clip says "results hold when thresholds move". Here they do hold, but only as losses.

Research only. Nothing was installed, attached, deployed or pushed:
- No live or Ava terminal was touched.
- 2024–2026 was not run, so that period stays unseen.

## What was tested

The rules come from the clip pasted by the user and were frozen before the first run; see [RULES.md](RULES.md).

- **Instrument and signals:** `UK100` (Exness FTSE 100 CFD), H1 signals on the closed bar, market buy on the next bar.
- **Rule 1:** on a London Monday, if RSI(14) < 40, buy.
  - Stop 2.5 ATR(14), target 2R, exit after 24 h.
  - At most one entry per Monday.
- **Rule 2:** if close ≤ SMA(40) − 1.5 ATR and RSI < 35, buy.
  - Stop 2 ATR, target 2R, exit after 24 h.
- **Positions:** one open position per rule.
- **Setup:**
  - Native MT5 Model 4, 150 ms delay, $10,000 USD, broker spread, commission and swap.
  - **0.75% equity risk per trade**, as in the clip, with lots rounded up.
  - Window 2020-01-01 → 2024-01-01 (exclusive).
- **Not tested:** the clip's "third rule inside the bot" is not disclosed.

Metric definitions:
- **/day** is per weekday.
- **Consistency** is the share of the 48 calendar months that were profitable.
- **Sharpe** is annualised from daily returns (√252).
- **Bal DD** is the closed-balance drawdown from the ledger; **Eq DD** is the floating-equity drawdown from the MT5 report.
- **Mean R** is net P&L per trade divided by 0.75% of the balance before it.

## Main versions

{{MAIN}}

## Controls

{{CONTROLS}}

{{CTL}}

![Closed balance 2020–2023](balance.png)

## Year by year

{{YEARS}}

## Declared sensitivity (BOTH with one threshold moved; not used to pick a winner)

{{SENS}}

{{YEARS_SENS}}

## Gate (predeclared in RULES.md)

{{GATE}}

- **Beats control** is technically "yes" for R2 and BOTH: PF 0.77 / 0.80 against a random mean of 0.73. But one random seed (RNG1) matches R2's PF exactly, so this is not a meaningful edge.
- **Clean** is "no" for R2 and BOTH: 2 of 599 Rule-2 signals fell in a bar where trading was closed, and the market buy was rejected and skipped. This does not change the conclusion.

## Costs and holding

{{COSTS}}

- **Rule 2 loses before costs:** gross −$3.2k. Commission and overnight swap add another −$1.4k.
- **Rule 1's small gross profit is wiped out by costs.**
- **Weekend gaps:** a Friday entry that is still open after 24 h closes at the Sunday 22:05 reopen. This happened 58 times for Rule 2.

## Signal and execution counters (EA journal)

{{COUNTERS}}

## Compared with the clip

| | Clip (since 2017, three rules) | This test (2020–2023, two disclosed rules, BOTH) |
|---|---|---|
| Trades per year | 1,908 / ~9.7 y ≈ 196 | 701 / 4 y ≈ 175 |
| Win rate | 50.8% | 38.8% |
| Return | +312.9% at 0.75% risk | −46.75% at 0.75% risk |
| Max DD | 12% | 54.0% equity |

The clip says its thresholds were chosen on the same years it tested, and its third rule is secret. Our data, cost model and gap-filling defaults also differ from theirs; see the limitations below. None of these explains a gap this large in Rule 2: it does no better than random entries.

## Survivor recommendation for optimisation

**None.**
- Under PIPELINE.md a raw failure stops here.
- **Rule 1** is the only part with a relative effect (Monday beats Tuesday–Friday). But it is not profitable after costs, makes about 2 trades a month, and was positive in only 1 of 4 years.
- The clip also claims the Monday dip appears on the DAX, S&P 500 and Nasdaq. A separate raw test of Rule 1 alone on those indices would be the only follow-up worth considering, and it would need your request.

<!-- best-day-dependence:start -->
## Best-day dependence (added 2026-10-20)

Rule (PIPELINE.md stage 4, 2026-10-20): a positive total FAILS if it turns ≤ 0 without its single best day or single best trade. The 5-best-days and worst-day columns are diagnostics.

| Run | Trades | Total $ | Best day | w/o best day $ | w/o best trade $ | w/o 5 best days $ | w/o worst day $ | Verdict |
|---|---:|---:|---|---:|---:|---:|---:|---|
| UK100-BOTH-2020_2023 | 701 | -4,675 | 2020-01-07 +226 | -4,901 | -4,841 | -5,571 | -4,289 | **n/a (already ≤ 0)** |
| UK100-C1TF-2020_2023 | 455 | -4,737 | 2020-01-17 +148 | -4,885 | -4,885 | -5,432 | -4,566 | **n/a (already ≤ 0)** |
| UK100-R1-2020_2023 | 104 | -102 | 2021-09-06 +157 | -259 | -259 | -882 | -17 | **n/a (already ≤ 0)** |
| UK100-R2-2020_2023 | 597 | -4,602 | 2021-01-04 +171 | -4,773 | -4,770 | -5,395 | -4,301 | **n/a (already ≤ 0)** |
| UK100-RNG1-2020_2023 | 559 | -4,228 | 2020-04-17 +174 | -4,402 | -4,402 | -5,005 | -4,071 | **n/a (already ≤ 0)** |
| UK100-RNG2-2020_2023 | 585 | -5,043 | 2020-11-03 +247 | -5,290 | -5,200 | -6,054 | -4,825 | **n/a (already ≤ 0)** |
| UK100-RNG3-2020_2023 | 591 | -6,202 | 2021-03-26 +228 | -6,430 | -6,354 | -7,048 | -6,053 | **n/a (already ≤ 0)** |
| UK100-S_CASH-2020_2023 | 520 | -2,808 | 2021-06-21 +263 | -3,071 | -2,991 | -4,048 | -2,391 | **n/a (already ≤ 0)** |
| UK100-S_DIST10-2020_2023 | 707 | -4,619 | 2020-01-07 +226 | -4,845 | -4,785 | -5,525 | -4,232 | **n/a (already ≤ 0)** |
| UK100-S_DIST20-2020_2023 | 681 | -4,200 | 2020-01-07 +224 | -4,423 | -4,365 | -5,120 | -3,807 | **n/a (already ≤ 0)** |
| UK100-S_R1RSI35-2020_2023 | 662 | -4,300 | 2020-06-29 +265 | -4,565 | -4,468 | -5,437 | -3,982 | **n/a (already ≤ 0)** |
| UK100-S_R1RSI45-2020_2023 | 732 | -4,645 | 2021-01-04 +305 | -4,950 | -4,813 | -5,631 | -4,254 | **n/a (already ≤ 0)** |
| UK100-S_R2RSI30-2020_2023 | 454 | -3,322 | 2020-05-26 +177 | -3,499 | -3,499 | -4,110 | -3,020 | **n/a (already ≤ 0)** |
| UK100-S_R2RSI40-2020_2023 | 908 | -5,546 | 2020-11-24 +254 | -5,801 | -5,714 | -6,660 | -5,187 | **n/a (already ≤ 0)** |
<!-- best-day-dependence:end -->

## Limitations

- **Tick data:**
  - Real UK100 ticks start 2026-01-02, so the whole 2020–2023 window uses **MT5-generated ticks from M1 bars**.
  - Spreads come from the M1 bars.
  - Results can differ from real-tick execution.
- **Defaults we chose** for things the clip does not specify:
  - RSI/ATR period 14;
  - "far below" = 1.5 ATR;
  - "weak" = RSI < 40;
  - London Monday;
  - all broker hours, with the cash session tested as a sensitivity;
  - one position per rule.
- **Rule attribution inside BOTH:** when Rules 1 and 2 hold longs at the same time, the report parser pairs exits with entries first-in-first-out.
  - BOTH's totals, trade count and P&L are correct, because each exit deal's P&L is native.
  - Splitting BOTH's trades by rule is **not** reliable, so rule-level evidence comes from the standalone R1 and R2 runs.
- **Overlap with the validation window:** under the 2026-10-06 split rule (study end 2026-10-19), 2023-10-19 → 2023-12-31 belongs to the validation year and is now viewed. 2024–2026 was not run.
- **Evidence type:** each run is a standalone single-strategy native test on an Exness demo feed, not FTMO or another broker's execution.

## Audit

- **14 runs (3 main, 4 control, 7 sensitivity) plus 1 smoke run:**
  - exit code 0;
  - expert, symbol, period and inputs verified in every native report.
- **Journal flags:** `init_failed`, `no_history`, `size_below_min` and `critical` are all 0.
- **Market-closed rejections:** the `rejected` lines are market-closed entry rejects only (counted under place fails above). Close fails are 0 in every run.
- **Smoke-test fix:** the first smoke run showed time exits retrying while the market was closed. The EA was changed before the grid to wait for the broker trade session, and the smoke test was re-run clean. The final EA source and EX5 are the ones in `EA/`. Source sha256 `35c015debe5e63a90b61bad8e6da8d07fa017e91d10925026c4f9ea0194ceb63`, EX5 `af7354c2d8fbcbd298ce56566ebdc699ec44cd40602760e651d07002c09487cf` (0 errors, 0 warnings).
- **Random-control probability:** set by frequency matching only, p = R2 entries / R2 flat bars = 597 / 16,525 = 0.03613; see [RNG_FREQUENCY.json](RNG_FREQUENCY.json).

## Files

- **Inputs:** [RULES.md](RULES.md), [run-config.json](run-config.json), [EA/](EA/).
- **Native evidence:** `native/nw-UK100-*/` holds the run.json, report, SET, tester.ini, journal and ledger for each run.
- **Outputs:** [RESULTS.json](RESULTS.json), [RESULTS.md](RESULTS.md), [balance.png](balance.png).
- **Scripts:**
  - [run.py](run.py): the harness, which reuses `No Wick Candle Raw 2026-09-25/run_nw.py`.
  - [analyse.py](analyse.py): the analysis, which also builds this report from `REPORT.template.md`.
