# Overnight Bias ORB (US100): optimisation plan, frozen 2026-11-10 before any result

**Owner request (2026-11-10):** optimise every strategy added today.
- The current raw version stays active, unchanged, in the P4 BATs and on the website.
- Any result here is a research candidate until the owner decides.

**Data split:** `data_split.research_split('2019-01-01', '2026-11-11')`. USTEC history starts 2019-07-16.
- Development: 2019-07 to 2023-11.
- Validation: the following 12 months, to 2024-11.
- OOS: the last 2 calendar years. It was previously seen in the raw study, so it is not untouched.

**Engine:** `../research_opt_engine.py`, the same method as USDJPY London Optimization 2026-11-05. Every run is recorded in RUNS.jsonl.
- **Research EA:** `EA/Overnight Bias ORB Research EA.mq5` is built by `build_ea.py` from the raw EA with asserted edits. All defaults equal the raw rules.
- **Parity:** before any search, the defaults must reproduce the raw ledger (`nw-USTEC-ONB-all`, 782 trades) trade for trade.
- **Screening:** native Model 1. Finalists are confirmed in Model 4, and Model 4 decides every gate.
- **Run settings:** $10k, 1% risk, 150 ms delay.

**Staged search, top 3 settings carried forward per stage:**
1. Opening range: 15 / 30 / 45 / 60 min.
2. Bias: top/bottom fraction 0.25 / 1/3 / 0.4 / 0.5, or bias off.
3. Overnight range start: 00:00 / 02:00 / 04:00 NY.
4. ADX minimum: off / 15 / 20 / 25 / 30.
5. Stop: 0.15 to 0.5 x the 15-day average true range.
6. Target: 1 / 1.5 / 2 / 2.5 / 3 / 4 / 5 / 6 R, or none.
7. Management: static; break-even at 0.5 / 1 R; trailing from 1 / 1.5 / 2 R at 0.5 / 1 R distance.
8. Last entry: 12:00 / 14:00 / 15:00 / 15:15.
9. Flat time: 15:00 / 15:30 / 15:55.
10. Direction: long only / short only / both.
11. Trades a day: 1 / 2.
12. Weekdays: all / Mon-Thu / Tue-Fri / Tue-Thu.

**Development score:** return / equity drawdown, with PF >= 1.15, >= 100 trades and positive return.

**Gates, in order:**
1. **Plateau:** at least 70% of the finalist's one-step neighbours are profitable on development.
2. **Validation (once):** positive, PF >= 1.15, and return / DD better than the raw version.
3. **OOS (once):** positive, PF >= 1.15, and return / DD not below the raw version.
4. **Monte Carlo** (three-way, all years): resample red <= 5% and randomize red <= 10%, for both the raw version and the candidate. Buy and hold USTEC is shown alongside.

If nothing passes, the raw version stays, and the best-validation candidate is shown as a labelled diagnostic only.
