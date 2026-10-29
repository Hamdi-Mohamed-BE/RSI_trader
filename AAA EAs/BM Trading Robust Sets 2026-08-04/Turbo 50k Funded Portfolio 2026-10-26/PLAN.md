# Turbo 50k funded portfolio 2026-10-26 — plan (written before any result)

**Owner request:**
- Build the best portfolio for the "Turbo" programme in the screenshot, for an existing $50k funded (reward) account,
  and save it.
- Show average daily / weekly / monthly income, average win and loss streaks, worst simulated drawdown, worst day,
  worst week and days to breach.
- Test 0.3 / 0.5 / 0.6 / 0.75 / 1% risk per trade.
- Design the full risk-management profile (max daily loss, max open risk, etc.).

Research only: Python/numba replay of frozen native ledgers. No MT5, nothing installed.

## Firm rules (screenshot; A = assumption, confirm with the firm)
- **Reward account:** daily loss 3%, max loss 6% trailing, 3 profitable days (≥ 0.5%) needed, 20% consistency rule,
  1:30 leverage, 80% / 95% share, rewards every 5 / 14 days, no time limit.
- **Evaluation:** target 6%, daily loss 3%, max loss 6% trailing, no minimum days and no consistency rule.
- **A1, daily loss:** 3% of the day-start closed balance. The day is broker server time (UTC+2/+3, EU DST).
- **A2, trailing max loss:** 6% of the initial $50k ($3,000) below the highest closed balance reached. It is re-based
  after every reward withdrawal (balance back to $50k and floor back to $47k). There is no lock at the initial balance.
- **A3, rewards:**
  - Checked every 14 days (conservative; the 5-day cadence is a sensitivity).
  - Eligible when cycle profit > 0 and at least 3 days closed ≥ +$250 (0.5%).
  - **Consistency (A4):** the best single day's profit is ≤ 20% of the cycle's profit. If the account is not eligible,
    it is rechecked every following day.
  - Withdraw all profit above $50k; the trader keeps 80% (95% shown as an upside).
- **A5, breach bracket** (the ledger has no floating equity):
  - OPTIMISTIC: closed balance.
  - PESSIMISTIC: balance minus every open position at its full stop.
  - The guard below is designed so that the pessimistic model can only breach on losses beyond the stops (gaps and
    slippage).
- **A6, leverage:** 1:30 margin is not modelled (fractional lots).

## EA universe
- **Stream:** `Portfolio Long History All ORB05 2026-10-14` `full-eas` (the website stream), 2021-10-06 → 2026-10-05.
- **Excluded:**
  - The four News Pulse EAs: news-spike ledgers are not credible.
  - US30 / US100 hourly: no stop-loss, which a 3% daily limit cannot tolerate.
  - Gold News V9: no ledger.
- **That leaves 30 stop-defined EAs.** 3 Way Gold is "watch only" and is allowed only if selection keeps it.

## Risk-management profile (the guard), searched on development only
- **Per-trade risk r** (fixed $, % of the initial $50k): 0.3 / 0.5 / 0.6 / 0.75 / 1% (the owner's levels).
- **Max total open risk at stop:** 1.0 / 1.5 / 2.0 / 2.5% (must be ≥ r).
- **Max open risk per symbol:** 1 × or 2 × r.
- **Daily soft stop:** no new entry if today's realised loss plus all open stops would exceed 1.0 / 1.5 / 2.0 / 2.5%
  (the firm limit is 3%).
- **Trailing buffer:** no new entry if balance minus all open stops would fall within 0.5 / 1.0 / 1.5% of the trailing
  floor.
- **Room taper:** off, or risk per trade ≤ 10% / 20% of (balance − open stops − floor), so trading continues smaller
  near the floor. A trade under $25 of risk is skipped.

## Selection (data_split.py: dev 2021-10-06 → 2023-10-05, val → 2024-10-05, OOS → 2026-10-05)
1. **Basket:** backward elimination on development MC at a reference profile (r 0.5%, open 2%, symbol 2r, daily 2%,
   buffer 1%, taper off).
   - Objective: median 12-month trader income, pessimistic model.
   - An EA is removed while that raises the objective by ≥ 1%.
2. **Guard:** for each r, the guard grid on development MC. Chosen = the highest median 12-month trader income with
   12-month pessimistic breach ≤ 10%; if none qualifies, the lowest breach.
3. **Validation:** the chosen profiles are reported on validation (MC + history).
   - **Recommended r:** the highest validation median 12-month income among those with validation pessimistic
     breach ≤ 10%.
4. **OOS** is run once for the five chosen profiles. **Mandatory Monte Carlo:** all-period 1,000 paths × 3 years, plus
   every weekday history start with a 12-month horizon, plus the 5-day reward sensitivity and an evaluation-phase run.

## Addendum 1 (after a degenerate first selection run; before any result was used)
- **What went wrong:** at the reference profile, almost every development path freezes or breaches before its first
  reward. Median 12-month income is therefore $0 for nearly every basket, so the median objective tied at zero and
  elimination removed 27 of 30 EAs on ties.
- **Fix for selection and the guard grid:**
  - The objective becomes the **mean** 12-month trader income (pessimistic model).
  - Ties are broken by the lower (breach + freeze) share.
  - An EA is removed only while that raises the mean by ≥ 1% and ≥ $1.
- **The guard rule keeps the breach ≤ 10% condition** and adds freeze ≤ 25% (12 months) for "qualified".
- **Validation and the recommendation** use the mean too. Medians are still reported.

## Reported per risk level (all-period MC + history)
- **Income:**
  - Trader income per day / week / month (80%; 95% upside).
  - Gross trading profit per day / week / month.
- **Streaks:** average and maximum win / loss streak (trades).
- **Drawdown:** worst simulated drawdown (closed and stop-marked; worst, p95, median).
- **Worst day and worst week:** worst and 5th percentile.
- **Breach:** days to breach (share by 3 / 6 / 12 / 36 months; median among breached); freeze share.
- **Payouts:** count and first payout day.
- **Trades:** trades / month and / day.
- **Evaluation phase:** pass rate and days.

In-sample (EAs chosen on this history; ticks before 2026 generated). Not a forecast, not advice.

## Addendum 2 (bug fix, after the first full run)
- **The v1 freeze check** ran only after processed events. An account whose entries were all blocked stayed "alive"
  without trading, which understated freezes. Example: 3-year trades / month 7 versus 22 in year 1 at 0.5%.
- **v2** also checks at the start of every server day. All stages (select, grid, validate, OOS, final) were rerun with
  the same rules and seeds. The v1 outputs are kept in `v1-freeze-check-bug/`.
- **Status of the OOS:** it was viewed once in v1. The v2 OOS is therefore **previously viewed**, not untouched.

## Addendum 3 (guard design change, after the v2 run)
- **v2 kept the v1 logic,** which skipped any entry that did not fit a limit. One traced path then refused 3,509
  entries after day 100: its room was $540, the buffer $500 and the taper risk $108. That account was effectively dead
  without being counted as frozen.
- **v3 guard:** each trade is cut down to the largest risk that fits every limit (max open, per symbol, daily soft stop,
  trailing buffer, taper). The minimum is $25. The account is frozen when the room above floor + buffer is below $25.
- **Rerun:** all stages were rerun with the same seeds. v2 outputs are kept in `v2-skip-not-fit/`. The OOS stays
  **previously viewed**.

## Addendum 4 (after the v3 grid; before validation and OOS of v3)
- **Why the selection rule changed:** with the honest freeze count, no development guard met "freeze ≤ 25%" (all froze
  82–99%). The fallback then picked the first grid row on a tie.
- **Guard rule now:** maximise development mean 12-month income with 12-month breach ≤ 10%. Mean income already
  includes accounts that freeze or breach early. Tie: lower (breach + freeze).
- **Added sensitivity:** a STATIC 6% floor (no trailing; re-based after rewards), to show how much the trailing rule
  alone costs. The firm's exact trailing mechanics must be confirmed.
- **Basket selection** (reference guard, mean objective) is unchanged and rerun with v3 code.
