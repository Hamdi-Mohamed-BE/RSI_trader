# Turbo $50k funded portfolio — REPORT (2026-10-26)

**Request:** the best portfolio and risk-management profile for the owner's $50k Turbo reward account, tested at
0.3 / 0.5 / 0.6 / 0.75 / 1% risk per trade.
- Plan and addenda: `PLAN.md`. Every table: `RESULTS.md`.
- Saved portfolio: `_00 Live profiles/Turbo 50k Funded Portfolio 2026-10-26/` (research files only; no guard EA, no
  installer).

## Method in short
- **Data:** frozen native ledgers of 30 stop-defined EAs (the website Full EA stream, minus news and no-stop hourly
  bots).
- **Simulator:** numba replay of the firm rules as modelled:
  - 3% daily loss on the day-start balance;
  - $3,000 trailing floor below the highest closed balance, re-based after each reward;
  - rewards every 14 days with 3 profitable days and the 20% consistency rule; 80% share.
- **Our guard:** max open risk, per-symbol cap, daily soft stop, trailing buffer and room taper. Each trade is cut to fit
  every limit.
- **Breach check:** balance minus every open stop (conservative).
- **Selection:** basket chosen on 2021–23 by backward elimination; the guard chosen on 2021–23 for each risk level.
  Then validation 2023–24, OOS 2024–26 and a mandatory 3-year Monte Carlo (1,000 paths) plus real-history starts.
- **Three fixes before the final numbers** (Addenda 1–4):
  - A median objective that tied at $0.
  - A freeze-detection bug.
  - Entries that were skipped rather than downsized.
  - **Consequence:** the OOS was viewed while these fixes were made, so it is **previously viewed**, not untouched.

## Results (3-year MC, pessimistic model; 1-year history in brackets)

| Risk | Trader income / day / week / month (median) | 12-month total, median (history) | Gross P&L / month | Breach | Frozen by trailing floor | Median account life | Worst day | Worst week | Worst DD (stop-marked) | Win / loss streak avg (max) | Trades / month / day |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 0.3% | $26 / $184 / $801 | $5,079 ($4,140) | $866 | 0% | 96% in 3 y (65% in 1 y) | 261 d | −$1,001 | −$2,126 | $3,219 | 2.1 / 2.2 (14 / 16) | 86 / 2.8 |
| 0.5% | $19 / $132 / $572 | $4,407 ($3,520) | $774 | 0% | 97% (69%) | 222 d | −$1,026 | −$2,308 | $3,060 | 2.0 / 2.2 (18 / 17) | 74 / 2.4 |
| 0.6% | $20 / $139 / $604 | $4,542 ($3,662) | $832 | 0% | 98% (73%) | 204 d | −$1,079 | −$2,315 | $3,345 | 2.1 / 2.2 (15 / 19) | 82 / 2.7 |
| **0.75%** | $22 / $153 / $665 | $4,956 ($5,298) | $941 | 0% | 99% (77%) | 192 d | −$1,315 | −$2,331 | $3,160 | 2.1 / 2.2 (15 / 17) | 90 / 3.0 |
| 1.0% | $16 / $115 / $502 | $3,966 ($5,894) | $976 | 0% | 100% (83%) | 145 d | −$1,345 | −$2,384 | $3,415 | 2.1 / 2.2 (14 / 18) | 100 / 3.3 |

Notes on the table:
- "Worst" = the worst of 1,000 three-year paths.
- Worst DD is measured on cumulative trading P&L across reward resets, so it can exceed the $3,000 trailing room.
- Daily figures are per calendar day.

## Reading it
- **The guard stops breaches.** 0% breach at every level, including when all open stops are hit together. The worst
  day (−$1,000 to −$1,345) stays inside the firm's $1,500 daily limit.
- **What ends these accounts is the trailing floor plus the 20% consistency rule.**
  - Profits raise the floor, but a reward is allowed only after the best day falls to 20% of the cycle profit, so
    rewards come slowly.
  - A pullback of about $2,750 from a peak then leaves no room to trade: the account **freezes** (not breached, but
    finished).
  - Median life is 6–9 months. Only 0–4% of 3-year paths are still trading.
- **Income while the account lives:** about $500–800 per month median, or $3.5–6.1k median per account in total. About
  32–50% of accounts never reach a reward.
- **The 5-day reward cycle changes nothing.** The 3-profitable-day and 20% consistency checks, not the calendar, are
  what delay rewards.
- **Static-floor sensitivity:** if the max loss is a fixed $3,000 below the start, freezes fall to 54–70% and income
  rises to about $950–1,250 per month. The trailing rule alone costs roughly a third of the income. Confirm the exact
  trailing mechanics with the firm.
- **Evaluation (new accounts):** 73–80% pass the +6% target, median 38–64 days, 0% breach.

## Recommendation
- **Predeclared rule → 0.75% per trade** (best validation mean income with ≤ 10% breach). It earns well in real
  history: $5.3k median in 12 months.
- **Lower-volatility alternative → 0.3%.** It has the best 3-year Monte Carlo median ($801 per month), the longest life
  (261 days), the fewest freezes in 1 year (65%) and the smallest worst day (−$1,001). Its mean is almost equal to
  0.75%.
- **Avoid 1%:** it has the shortest life (145 days) and the most freezes.

## Limits
- **In-sample:** EAs and settings were chosen on this history; ticks before 2026 are generated.
- **Previously viewed OOS** (see above).
- **No floating equity:** the breach check uses stop-marked equity, not real floating equity.
- **Not modelled:** 1:30 leverage limits.
- **Unconfirmed rule details:** the trailing, daily-basis and consistency definitions are assumptions.
- **Missing guard:** the profile needs a guard EA with a trailing floor, which does not exist yet. Running the SETs
  without it gives no protection.
- Not a forecast and not advice.
