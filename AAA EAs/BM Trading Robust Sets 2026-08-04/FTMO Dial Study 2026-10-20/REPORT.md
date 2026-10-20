# FTMO dial study: Prop Ready on FTMO Swing $10k (2026-10-20)

> **Status after the Bear review (fresh-context reviewer, same day): NOT DECISION-READY.** The review found unanswered attacks; see "Bear review" at the end. Treat FLAT100 as a hypothesis to test, not a setting to deploy.

**Question:** can we pass both FTMO phases faster than the current flat $50 per trade by sizing on the room left above FTMO's $9,000 floor (the AI Trading Library's "dial"), without the stuck or failed accounts seen at $200?

**Answer:** yes, in this history. **A flat $100 per trade** ranked first under the rule declared before the runs.

- **Median days to pass both phases:** 67–71, down from 99.5–119 at $50.
- **Pass record:** every start passed both phases, with zero FTMO breaches in all four cost and handover scenarios.
- **The price:** the worst equity drawdown roughly doubles, from $353 to **$653 of the $1,000 allowed**. The worst day rises from $147 to **$271 of the $500 allowed**.
- **The library's dial** ($100 normal, $50 below 50% room, $25 below 25% room) is almost identical to flat $100, because the room rarely fell below 50%. It caused slightly fewer buffer blocks and was up to 1.5 days slower.
- **Flat $200** is the fastest (median 49–56 days), but **7–14 of 134 starts were still stuck at day 180** with equity sitting just above the $9,200 buffer. Its worst drawdown was **$943–984**, within $16–57 of the FTMO failure line. It fails the declared criteria.

Research only. No BAT, SET, guard, package, account or MT5 setting was changed. The Prop Ready guard currently caps each entry at 0.5% ($50). Running at $100 would need its per-entry cap raised to 1%, and the total and per-symbol open-risk caps raised to 4.5% and 3%, while keeping the $300 daily reserve. That is a deployment change only you can authorise.

## Method

- **Engine and data:** the 2026-10-16 FTMO Faster Portfolio Screen, reused **unchanged** and hash-checked in `FROZEN.json`.
  - Basket `CORE4_PLUS_FIVE_ORBS_05R`, the same nine EAs as `Packages/PropReady`.
  - 134 Prague weekday starts from 2025-10-06 to 2026-04-09, each followed for 180 days.
  - FTMO 2-step rules: +10% then +5%, at least 4 trading days per phase, static $9,000 floor, $500 daily loss limit.
- **What changed:** only the per-entry risk cap, through a subclass in `run.py`. The total and per-symbol open-risk caps scale with the per-entry cap.
- **What stayed fixed for every policy:** the account-level protections. That is the $300 daily latch and reserve, the $9,200 entry buffer, 7 entries and 3 losing closes per day, the margin proxy and the hard-failure test.
- **Parity check:** **FLAT50 reproduced all 536 source trial records exactly**, so the harness is the same model.
- **Pre-declared:** six policies, an eligibility rule and a ranking rule, all in `PLAN.json` before any outcome.
  - Eligible = zero hard failures and at least 95% of starts completing both phases within 180 days, in every scenario and in the Jan-2026+ subgroup.
  - Ranking = worst-scenario median days, then the share done within 90 days, then the smaller cap.

## Results (all 134 starts; ranges cover the four cost and handover scenarios)

| Policy | Both phases done (of 134) | FTMO breaches | Median days to both phases | Median days to funded (+5 business days review) | Done within 60 / 90 / 120 days | Phase 1 within 60 days | Worst equity drawdown (limit $1,000) | Worst day (limit $500) | Starts that hit the $9,200 buffer | Eligible |
|---|---:|---:|---:|---:|---|---:|---:|---:|---:|---|
| **FLAT50** (current) | 134 | 0 | 99.5–119 | 106.5–126 | 0% / 11–33% / 55–84% | 41–52% | $315–353 | $139–147 | 0 | yes |
| **FLAT100** | 134 | 0 | **67–71** | **74–78** | 23–35% / 65–73% / 89–99% | 66–78% | $634–653 | $257–271 | 3–7 | **yes, ranked 1st** |
| DIAL_LIB ($100 / $50 / $25) | 134 | 0 | 67–72.5 | 74–79.5 | 23–35% / 63–72% / 84–99% | 66–78% | $634–653 | $257–271 | 1–5 | yes, 2nd |
| DIAL_START ($150 near start, stepping down) | 134 | 0 | 76.5–81.5 | 83.5–88.5 | 27–34% / 60–67% / 89–93% | 74–83% | $908–937 | $259–267 | 0 | yes, 3rd |
| DIAL_GAIN ($150 only when in profit) | 110–132 | 0 | 76–102.5 | 83–109.5 | 12–34% / 34–61% / 52–84% | 51–63% | $933–945 | $257–271 | 0 | no (24 starts unfinished under cost stress) |
| FLAT200 | 120–127 | 0 | 49–56 | 56–63 | 55–72% / 81–89% / 90–95% | 89–95% | **$943–984** | $226–254 | 64–87 | no (7–14 starts stuck) |

- **Worst drawdown and worst day** are sampled 5-minute equity, not tick equity. True intraday extremes can be larger.
- **Jan-2026+ subgroup (71 starts):** FLAT100 passed both phases in 71/71, median 69–72 days. FLAT50 passed 71/71, median 94–110 days.

## What this does NOT prove

- **Not a forecast.** It is a retrospective replay of the same year the basket was chosen on, with overlapping starts. "134/134" means it never failed in this history, not a 100% future chance.
- **The margin of safety shrinks at $100.** FLAT100 used up to 65% of FTMO's total loss allowance and 54% of the daily allowance in this year. A worse year than this one could breach at $100 where $50 would survive. The $50 setting's worst case used only 35%.
- **Simulated fills and costs.** Prices are replayed from Exness test data rather than FTMO's own. Sampled equity can miss intraday spikes.
- **Signals can't react to the new sizing.** Signals and exits come from the standalone EA runs. Entries skipped by the guard cannot create the new signals they would have triggered live.
- **Six configurations were tested.** The winner is the simplest change, not a tuned value, but it was still chosen from this sample.

## Bear review (2026-10-20, fresh context, read-only): ATTACKS UNANSWERED — fix before deciding

I re-checked the reviewer's key numbers from `OUTCOMES.json.gz`.

1. **Selection on top of selection, and no data split.**
   - The basket won a 12-basket screen on this same year, and $200 had already been seen as "faster but stuck". A $100/1% diagnostic also ran on a 13-EA basket over an overlapping year.
   - "6 tested configurations" therefore understates the search, and there is no development, validation or two-year out-of-sample split (PIPELINE 5.1).
   - Fix: replay frozen FLAT50 and FLAT100 on the older 2021-10→2025-10 history that the source runs cover. Label any years used to fit the EAs as previously inspected.
2. **"134/134" is a handful of paths.** Verified: FLAT100's completions fall on only **15–17 distinct pass dates**, with 39–41 starts finishing on 2026-04-30 alone.
   - Stage 6 still needs a block bootstrap of the frozen stream at $50 and $100: the chance of a breach, and the 95th-percentile total and daily drawdown against $1,000 and $500.
3. **The tested setup is not the Prop Ready package.**
   - The guard hashes differ: the model uses FTMO guard `0378db52…`, the package ships `2999964d…`. No Prop Ready EX5 or SET hashes appear in the source inputs.
   - The package's default phase "Funded" has no target stop.
   - $100 needs the **EA risk request raised to 1% as well as the guard caps**, since `run.py` scales both. Raising only the cap would leave trades near $50.
   - Fix: a hashed $100 build run in Challenge/Verification phase, plus a guard parity fixture.
4. **FLAT100 is not just $50 × 2.**
   - Verified: the unchanged $300 daily reserve blocks **1,463–1,740** entries (0 at $50), and the median trade count drops from **124 to 81–84**.
   - Which trade gets in therefore depends on arrival order, which was never varied. The blocked trades were net winners, so this does not flatter FLAT100.
   - Fix: add randomised entry-order sensitivity, and add the trades, trades/month and trades/day columns.
5. **Realism limits weigh more at $100.** Extra XAU RSI VWAP trades appear only at $100 (minimum-lot effects). 63 starts begin on generated ticks. Equity is sampled every 5 minutes.

Handled well, per the reviewer:
- the exact FLAT50 parity (536/536) and hash freeze;
- the policies, eligibility and no-relax rule declared before running;
- no look-ahead found;
- the cost-stress and handover scenarios.

## Files

- [PLAN.json](PLAN.json): pre-declared policies, eligibility and ranking.
- [FROZEN.json](FROZEN.json): input and engine hashes.
- [run.py](run.py): subclass engine with the FLAT50 parity assertion.
- [SUMMARY.json](SUMMARY.json): every policy × scenario × subgroup.
- `OUTCOMES.json.gz`: all 3,216 trial records.
