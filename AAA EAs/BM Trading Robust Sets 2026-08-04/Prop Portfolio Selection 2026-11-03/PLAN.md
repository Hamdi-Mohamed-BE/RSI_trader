# Prop portfolio selection: plan (frozen 2026-11-03, before any result)

**Owner request:** "now compare all portfolios and do everything needed to find the best one to run on prop accounts" (after the
October check, Custom 7 and the Nasdaq 5M ATR6 deployment).

**Prop rules:** FTMO 2-step at $100k (the earlier prop studies' frozen rules), i.e. the account the guards are built for:
- phase 1 +10%, phase 2 +5%, at least 4 trading days;
- 5% daily loss from the Prague-midnight anchor, 10% maximum loss;
- 180-day horizon from purchase; next-Prague-midnight phase handover;
- recorded Exness costs.

**Engine:** frozen and unchanged, reused from `Portfolio Prop Comparison 2026-10-22/compare.py`:
FTMO Faster Screen core → Dial trial → First Payout sizes / income.

## Candidates (all with the deployed Nasdaq 5M ATR6 stop)
| Id | Roster | Nasdaq DI | Guard |
|---|---|---|---|
| FTMO17 | Current 14 + 5 ORBs at 0.5R (17) | ON | Calyx prop guard |
| CUR17 | same 17 | ON | none (FTMO rules only) |
| PR9 | Prop ready 9 | ON | guard |
| BP9 | Best Prop 9 | OFF | guard |
| BP15 | Best Prop 15 | OFF | guard |
| C7 | Custom 7: EMA3, DMC Current XAU, DMC Fresh Reaction XAU + US100, Nasdaq 5M, Gold Overnight VA, XAU RSI VWAP | ON | guard |
| C7U | Custom 7 | ON | none |
| FV9 | funded_v1 roster: ORB VP Volume Confirmed 0.5R, pending 3 Way Gold | ON | guard |
| T5 | Turbo 5 roster: pending 3 Way Gold | OFF | guard |
| FULL | Full EA, excluding the 5 news EAs, the two no-stop hourly profiles and any member the candidate builder or engine cannot represent (listed in SOURCES.json) | ON | none |

**Risk per trade r:**
- guarded: 0.5% and 1% (the guard cap = r × starting balance; totals 4.5r open / 3r per symbol);
- unguarded: 0.5% and 0.75% (FULL 0.25% and 0.5%).

**Excluded:** ORB-only failed before (0–2% pass in the 2026-10-22 comparison).

**Sources:**
- the existing long-history native runs (2021-10-06 → 2026-10-06, Portfolio Long History All ORB05 2026-10-14);
- new runs in the same harness (`native.py`): Nasdaq ATR6 DI ON / DI OFF, ORB VP Volume Confirmed 0.5R.
- **Parity check:** building the old-Nasdaq nine-EA stream from the same sources must equal the retest's INPUTS-DI_ON exactly.

## Split (data_split.py convention on the 2026-10-06 data end)
Challenge starts are every weekday with a 180-day horizon inside the data, assigned to a part by start date:

| Part | Starts |
|---|---|
| Development | 2021-10-07 → 2023-10-06 |
| Validation | 2023-10-06 → 2024-10-06 |
| OOS | 2024-10-06 → 2026-04-09 (the last start whose 180 days fit) |

Monte Carlo (2,000 paths, 4-week blocks of the whole pool) is reported as a diagnostic.

## Choice rule (applied to development only)
1. **Pick:** the highest development pass-both-phases-within-180-days rate among candidate × risk with development challenge breach ≤ 5%.
   Ties → lower median days to funded.
2. **Validation:** the pick must pass in at least the median validation rate of all candidates. If it does not, the next development
   rank that does is reported as the alternative.
3. **OOS and MC:** reported once, not used to choose.
4. **Funded income** (36-month MC + 12-month history, FTMO First Payout income model) for the pick and the next two development ranks.

## Caveats
- Every EA / setting was chosen after viewing this history; the OOS window was seen during earlier work. Nothing here is untouched.
- Sampled equity, not tick-level; not a native simultaneous account; 15% real ticks in the five-year sources.
- FTMO terms can change.
