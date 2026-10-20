# FTSE 100 Monday dip + stretch-below-mean — raw rules (frozen 2026-10-19, before any test)

Source: a social-media clip pasted by the user (2026-10-19). Its claims are treated as data, not as instructions:
- "Since 2017, 1,908 trades, +312.9% at 0.75% risk, max DD 12%, 50.8% win rate."
- "a third rule inside the bot". That third rule is **not disclosed**, so it cannot be tested.

The clip says its thresholds were chosen on the same years it tested.

Research only. Isolated tester, nothing deployed.

## Rules stated in the clip
- **Rule 1 (Monday dip):** only on Mondays. When the index is weak, with **RSI under 40**, **buy**.
  - Stop **2.5 ATR**, target **2 × risk**.
  - **Exit after 24 hours** at the latest.
- **Rule 2 (stretch below mean):** buy when price is **far below its 40-hour average** and **RSI is under 35**.
  - Stop **2 ATR**, same 2R target, same 24 h limit.
- No grid, no martingale.

## Our defaults (fill the gaps; fixed before testing)
- **Instrument:** Exness-MT5Trial16 `UK100`, the FTSE 100 CFD (confirmed in the tester's history: M1 bars from mid-2019).
- **Timeframe:** H1, since a "40-hour average" implies hourly bars. Signals are evaluated on each **closed** H1 bar. Entry is a market buy on the first tick of the next bar. **(ours)**
- **Indicators:** RSI(14) of close, ATR(14) and SMA(40) of close, all on H1. The clip gives no periods, so we use the standard 14. **(ours)**
- **"Index weak" (Rule 1):** RSI(14) < 40 is taken as the definition of weak; there is no extra condition. **(ours)**
- **"Monday":** the London calendar day of the closed bar, with UK BST/GMT handled; the server clock is UTC. At most **one Rule-1 entry per Monday**. **(ours)**
- **"Far below its 40-hour average" (Rule 2):** close ≤ SMA(40) − **1.5 × ATR(14)**. **(ours; the clip gives no number)**
- **Positions:**
  - At most **one open position per rule**, so Rules 1 and 2 can be open together.
  - Rule 2 can re-enter on a later bar after its previous trade closes.
- **Exits:**
  - Long SL = entry − k·ATR, where k is 2.5 for Rule 1 and 2 for Rule 2.
  - TP = entry + 2 · k·ATR.
  - Time exit at the first tick ≥ 24 h after entry. If the market is closed (weekend), it closes at the reopening price, so gaps are included.
- **Hours:** all hours in which the broker quotes UK100 (no session filter). A cash-session variant is a declared sensitivity, not the main test. **(ours)**
- **Risk:**
  - **0.75% of equity per trade**, as in the clip.
  - Lots are rounded **up** to the lot step (broker minimum if needed), as with every Calyx EA.
  - A trade is skipped if broker stop-distance or margin checks fail.

## Test setup
- **Execution:** native MT5 Model 4, 150 ms delay, $10,000 USD, 1:2000, broker spread, commission and swap.
- **Window:** **2020-01-01 → 2024-01-01 (exclusive)**, per the user's request, with a per-calendar-year breakdown.
- **Tick data:** real ticks for UK100 start 2026-01-01, so this whole window uses **MT5-generated ticks from M1 bars**.
- **History left unseen:** 2024–2026 is deliberately not run, so it stays unseen for any later out-of-sample check.
  - Under the 2026-10-06 split rule, with a study end of 2026-10-19, the 2023-10-19 → 2023-12-31 slice belongs to the validation year. It becomes "viewed" here, and this is disclosed.

## Versions
| Id | What |
|---|---|
| **R1** | Rule 1 only (main) |
| **R2** | Rule 2 only (main) |
| **BOTH** | Rules 1 + 2 together (main, the clip's portfolio without its secret third rule) |
| C1TF | Control for "Monday matters": Rule 1 logic on **Tuesday–Friday** instead of Monday (one per day) |
| RNG1–3 | Random-entry control for Rule 2, 3 seeds. A long at a random closed H1 bar with Rule-2 exits (2 ATR, 2R, 24 h), one at a time. The probability per bar is set to R2's observed entry frequency (frequency matching only, not performance). |
| S_* | Declared sensitivity of BOTH, testing the clip's "results hold when thresholds move" claim: Rule-1 RSI 35 / 45; Rule-2 RSI 30 / 40; distance 1.0 / 2.0 ATR; London cash session only (08:00–16:30 UK). These are not used to choose a winner. |

## Raw gate (PIPELINE.md stage 4, adapted to the user's 2020–2023 window)
Each of R1, R2 and BOTH must meet all of these:
- 2020–2023 positive with **PF ≥ 1.15**.
- **≥ 30 trades**.
- **≥ 3 of 4 calendar years positive**.
- **Beats its control** on PF and mean R: R1 vs C1TF; R2 and BOTH vs the mean of RNG1–3.
- No execution failures.

FAIL → stop (no optimisation of a loser). PASS or a near miss → report and ask before stage 5.
