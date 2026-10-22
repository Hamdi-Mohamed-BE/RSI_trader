# FTMO First Payout Study 2026-10-20 — Best Prop Portfolio (DI OFF)

**Question:** realistic first payout value and days, for 10k / 20k / 25k / 50k / 100k accounts.
**Model:** the built `_00 Live profiles/Best Prop Portfolio 2026-10-20` package (9 EAs, 1% guard cap, 4.5% total, 3% per
symbol, 3% daily reserve, 92% equity buffer). Python replay of recorded EA trades, not native MT5 and not live FTMO.
FTMO payout rules: first request on/after day 14 from the first funded trade, flat account, 80% split, fee refunded with
the first reward, $20 minimum, then 2–4 business days FTMO review + payment (not modelled). See PLAN.md (+ addendum).

## Gates
- Funded model with payout tracking reproduces the retest continuous OOS exactly (4/4 DI × cost) and the OOS
  challenge summary (2/2). The size-scaled code at 10k reproduces every 10k summary exactly (funded, funded MC,
  end-to-end, end-to-end MC). Inputs/engines frozen (FROZEN.json, FROZEN-SIZES.json); PLAN.md body unchanged
  after the freeze (only the addendum is new — hash checked).

## Headline — from buying the challenge (Monte Carlo, 2,000 paths, recorded costs, next-midnight handover)

| Account | Fee | Get funded | Days to funded (median / mean) | First payout at all | Paid ≤120 d | Days to payout request (median / mean) | Payout if paid (median / mean) | Expected payout per challenge bought | Trades / month | / day |
|---|---|---|---|---|---|---|---|---|---|---|
| $10,000 | €155 | 56% | 72 / 78 | 49% | 38% | 88 / 96 | $245 / $334 | $164 | 37.7 | 1.73 |
| $20,000 | not an FTMO size | 55% | 68 / 75 | 48% | 39% | 87 / 92 | $485 / $650 | $310 | 37.7 | 1.73 |
| $25,000 | €250 | 55% | 68 / 75 | 47% | 39% | 86 / 92 | $602 / $812 | $383 | 37.7 | 1.73 |
| $50,000 | €345 | 55% | 68 / 74 | 47% | 39% | 85 / 90 | $1,220 / $1,633 | $760 | 37.7 | 1.73 |
| $100,000 | €540 | 55% | 68 / 74 | 47% | 39% | 85 / 90 | $2,418 / $3,246 | $1,513 | 37.7 | 1.73 |

Add 2–4 business days for FTMO review and payment. Stress costs + two-business-day handover: funded 42–44%, paid 34–36%,
median 89–94 days, expected payout per challenge $114 / $224 / $281 / $560 / $1,114. The fee is refunded only with a
reward; a frozen account (below) never pays it back unless the owner intervenes.

## Funded account only (already funded; Monte Carlo, recorded costs; $20 earliest policy)

| Account | Paid ≤30 d | Paid ≤180 d | Request day (median / mean) | Payout (median / mean, p25–p75) | Expected per funded account | Breach before payout | Stuck at 92% buffer | Trades / month | / day |
|---|---|---|---|---|---|---|---|---|---|
| $10,000 | 78% | 83% | 15 / 18.5 | $242 / $332 ($91–$461) | $277 | 0% | 16% | 37.7 | 1.73 |
| $20,000 | 78% | 83% | 15 / 17.9 | $483 / $667 ($194–$920) | $554 | 0% | 16% | 37.7 | 1.73 |
| $25,000 | 78% | 83% | 15 / 17.9 | $603 / $833 ($222–$1,155) | $691 | 0% | 17% | 37.7 | 1.73 |
| $50,000 | 78% | 82% | 15 / 17.3 | $1,201 / $1,680 ($451–$2,310) | $1,382 | 0% | 18% | 37.7 | 1.73 |
| $100,000 | 78% | 82% | 15 / 17.3 | $2,404 / $3,339 ($887–$4,619) | $2,746 | 0% | 18% | 37.7 | 1.73 |

## By history window (10k; other sizes in SIZES.md)
End to end, base: development starts 2021-23: funded 42%, paid 37%, median 93 d; validation 2023-24: funded 54%, paid
38%, median 79 d; OOS 2024-26: funded 86%, paid 86%, median 79 d; all history: funded 56%, paid 49%, median 84 d.
Funded only, $20 policy: development 86% paid, validation 86%, OOS 97%, all 86%. The last two years were the best regime.

## Payout timing choice (10k funded only, Monte Carlo, recorded) — descriptive, not a selection
| Request when closed profit ≥ | Paid ≤180 d | Median request day | Median payout | Expected per funded account |
|---|---|---|---|---|
| $20 (earliest) | 83% | 15 | $242 | $277 |
| $250 (2.5%) | 80% | 16 | $329 | $340 |
| $500 (5%) | 77% | 22 | $518 | $458 |
| $1,000 (10%) | 72% | 39 | $876 | $683 |
Only the FIRST reward is modelled; after any reward the account keeps trading, so a small early reward is not lost profit.

## Findings
1. Roughly half of challenges bought end in a first payout; the median wait is about 3 months from purchase (85–88 d
   request + 2–4 business days). The other half are NOT breached — they freeze. 10k historical starts
   (`why_not_funded.py`): 0 breaches; 55.8% funded; 42.5% stuck below the 92% buffer at day 180 (25.7% in phase 1,
   16.8% in phase 2); 1.7% still trading. Monte Carlo: 43.5% challenge frozen, 6.9% funded-then-frozen, 49.1% paid.
   FTMO 2-Step has no time limit, so a frozen account is not failed, but the guard will never trade it again.
2. Once funded, 0% breached before the first payout in every window, but 16–18% stall: equity drifts under the 92%
   entry buffer and the guard blocks all new trades. That account is not breached but earns nothing until reviewed.
3. Payouts scale with size (median ~2.4% of the account at the earliest request, mean ~3.3%). $20k+ is 1–2 points
   worse than $10k: at $10k, rounding DOWN to the 0.01 lot step under-sizes some trades below 1% (a small brake);
   no trades were skipped for minimum lot at any size.
4. DI ON (comparison only, 10k): end-to-end paid 57% (MC 58%) vs DI OFF 49%; funded-only similar (87–88%).

## Limitations
In-sample: the package was chosen after viewing this whole history; the OOS window is not untouched. Python replay of
recorded EA signals (Exness proxy costs/lots; earlier ticks generated, real from 2026-01-01), not native MT5 or FTMO
execution. Monte Carlo resamples 4-week blocks of the same history. FTMO processing, consistency reviews and rule
changes are not modelled; 20k has no FTMO product. Fees are EUR, payouts USD (not converted). Not a forecast; not
financial advice.

Files: PLAN.md, run.py, sizes.py, tables.py, sizes_table.py, RESULTS.json, RESULTS-SIZE-*.json, TABLES.md, SIZES.md,
OUTCOMES.json.gz, FROZEN.json, FROZEN-SIZES.json, run.log, sizes-*.log.

## Addendum 2 — one funded $100k account: income until it ends (income.py, INCOME.md)
**As built, income stops after the first reward.** CalyxFTMOGuard `FTMOLedger` fails closed on any balance operation
after the frozen start ("Any funding/withdrawal/adjustment after deployment invalidates the frozen capital baseline"),
so FTMO's reward withdrawal blocks every new entry; reinstalling on the same login keeps the state file. Model below
ASSUMES the owner re-baselines after every reward (new login: run the installer; same login: delete the
Calyx-BestProp9 state file, then run it) and the account restarts at $100k. Parity: payouts off at k = 1 reproduces the
retest continuous OOS exactly; every run passed the withdrawn + balance = trade-net accounting identity.

| $100k, request every 14 d when profit ≥ $20, recorded costs | Accounts | Ended ≤6 m | ≤12 m | How it ends | Median days to end | Mean days alive | Payouts (median) | Avg monthly income while alive | Total income until end (median / mean) | Trades / month | / day |
|---|---|---|---|---|---|---|---|---|---|---|---|
| History, 12-month horizon, all starts | 1,043 | 79% | 94% | 0% breach / 94% frozen / 6% alive | 91 | 119 | 5 | $4,916 | $13,232 / $19,185 | 37.8 | 1.74 |
| History, OOS 2024-25 starts | 261 | 54% | 81% | 0% / 81% / 19% | 159 | — | 9 | $6,004 | $36,351 / $37,729 | 36.9 | 1.70 |
| History, development starts | 521 | 82% | 97% | 0% / 97% / 3% | 58 | — | 2 | $3,193 | $6,073 / $10,594 | 39.9 | 1.83 |
| Monte Carlo, 36-month horizon | 2,000 | 81% | 97% | 0% / 100% frozen by 36 m | 78 | 110 | 4 | $5,136 | $10,892 / $18,628 | 38.5 | 1.77 |
Stress costs: Monte Carlo median 60 days, $4,514/month while alive, total $6,945 / $12,422. A 2% ($2,000) minimum
request changes little (MC median 74 days, $5,193/month, total $10,548 / $18,116).

**No account was breached; every account ends by FREEZING.** Each reward resets the balance to $100k, so the cushion
above the 92% entry buffer is zero after every payout; the next ~8% drawdown blocks all entries permanently. The FTMO
account is then still open at roughly $92–93k but the bots never trade again without intervention. EUR 540 fee refund
with the first reward and the scaling plan are not included. In-sample; not a forecast.

## Addendum 3 — lower risk after getting funded ($100k, lowrisk.py, LOWRISK.md)
Guard-exact sizing (min(1% of reference, R% of current equity), floor). LEGACY 1.00 reproduces income.py exactly.
Monte Carlo 36 months, recorded costs, $20 reward every 14 days, guard re-baselined after each reward:

| Funded risk per trade | Avg monthly income while trading | Median days until bots stop | Still trading at 36 m | Total income (median / mean) | First reward (median) | Trades / month | / day |
|---|---|---|---|---|---|---|---|
| 1.00% (current package) | $5,109 | 79 | 0% | $11,031 / $18,718 | $2,381 | 38.4 | 1.77 |
| 0.75% (installer input) | $3,654 | 148 | 1% | $15,897 / $25,930 | $1,759 | 42.1 | 1.94 |
| 0.50% (installer input) | $2,203 | 532 | 23% | $37,026 / $42,479 | $1,149 | 43.4 | 2.00 |
| 0.25% (installer input) | $992 | > 1,092 | 93% | $34,782 / $34,497 | $561 | 43.5 | 2.00 |
| 0.50% + caps 2.25%/1.5% (guard change) | $2,192 | 529 | 23% | $36,840 / $42,196 | $1,151 | 43.4 | 2.00 |

Mean total income by evidence (1.00 / 0.75 / 0.50 / 0.25%): MC recorded $18.7k / $25.9k / $42.5k / $34.5k; MC stress
$12.5k / $15.6k / $22.5k / $23.1k; history development starts (12 m) $10.7k / $8.6k / $12.6k / $7.2k; history OOS
starts (12 m) $39.1k / $61.5k / $41.9k / $20.8k (12-month and 36-month horizons truncate long-lived accounts).
0% breaches at every level. Lower risk = lower monthly income but far longer life and, in every evidence set except the
best (OOS) regime where 0.75% led, the highest total at 0.50%. The capped guard variant equals the installer input,
so lowering funded risk needs NO guard code change (installer prompt / -RiskValue). The reward re-baseline limitation
still applies. In-sample; picking a level from this is an owner decision, not validated selection.
