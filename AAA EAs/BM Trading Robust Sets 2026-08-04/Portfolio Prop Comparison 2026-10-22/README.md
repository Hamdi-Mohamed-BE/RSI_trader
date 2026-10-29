# Portfolio Prop Comparison 2026-10-22 — method (written before any result)

**Owner request:** for all five portfolios, show the FTMO pass rate and median pass days at 0.5%, 0.75% and 1% risk;
then the expected monthly income after getting funded at the same risks, and the days until the funded account breaches.
Research only (Python replay). No MT5 terminal and no trading.

## Portfolios
The five that can run under prop rules:

| Portfolio | EAs | Signal stream | Guard |
|---|---|---|---|
| FTMO guarded | 17 (Current 14 + 3 ORBs) | five-year native runs, LONG `ftmo` mapping | Calyx guard |
| Current 14 + ORB 0.5R | same 17 EAs | `current14-orb05` mapping (identical signals) | **none** |
| ORB-only | 5 ORBs | `orbs-only` mapping | **none** |
| Prop ready | 9 | retest INPUTS-DI_ON (Nasdaq DI ON) | Calyx guard |
| Best Prop | 9 | retest INPUTS-DI_OFF (Nasdaq DI OFF) | Calyx guard |

**Excluded:** the Full 37-EA portfolio. Its hourly EAs have no stop-loss and its news EAs place two-sided pending orders;
the guard refuses both, and per-trade stop risk is undefined for the no-stop EAs.

## Risk definition
"Risk r" means each entry risks r% of current equity to its initial stop.
- **Guarded portfolios:** entries are capped at r% of the saved initial balance. Guard limits scale with r: total open
  risk 4.5r, per symbol 3r. The $300-per-$10k daily reserve, the 92% entry buffer and the 90% floor are fixed, as in both
  packages.
  - Prop ready at 0.5% and Best Prop at 1% are the exact installed packages.
  - The other combinations are hypothetical: the FTMO and Prop ready installers cap at 0.5%, and Best Prop's real guard
    keeps 4.5% / 3% totals at lower requests. In the earlier study the difference was about 0.5%.
  - Lots use the guard-exact rule from FTMO First Payout Study `lowrisk.py`: floor(min(request, budget / unit)), with
    budget = min(cap, r × equity).
- **Unguarded portfolios:** lots are r% of equity, rounded UP (Calyx standard), using the broker minimum if below. There is
  no daily, total, per-symbol or buffer guard. Only FTMO's own rules apply: breach at a 5% daily loss from the
  Prague-midnight anchor, or at 10% total (sampled equity).
  - Assumption: the trader stops new entries once the phase target is reached and waits to be flat, which an FTMO pass
    requires anyway.
- **3 Way Gold** (in both 17-EA portfolios) runs three concurrent modules with partial exits.
  - Each module is replayed as its own lane, and partial exits are collapsed at the final close.
  - Its intratrade floating marks are not reconstructed: P&L is booked at close, so intratrade drawdown for its positions
    is understated.

## Evidence
Frozen engines are used unchanged: FTMO Faster Portfolio Screen core engine → Dial Study trial → FTMO First Payout Study
sizes / income / lowrisk. Account $100,000, recorded Exness costs, next-Prague-midnight phase handover.

**Parity checks**
- The new FTMO17 stream's nine shared EAs are identical to the retest DI ON stream.
- The funded model for Best Prop at 1% exactly reproduces `LOWRISK-SET_1.00-recorded_exness` history (`PARITY.json`).

**Challenge (both phases within 180 days of purchase)**
- History: every weekday start with a 180-day horizon inside 2021-10-07 → 2026-10-06.
- Monte Carlo: 2,000 block-bootstrap paths (4-week Monday-aligned blocks, 7 blocks), seed as in the retest.
- Metrics: pass rate, funded within 90 days, breach, stuck at the buffer, median days to pass both phases, median days to
  funded access (+5 business days illustration).

**Funded $100k (income model of FTMO First Payout Study `income.py`)**
- Rewards: 80% split, first request 14 days after the first trade, then every 14 days (minimum $20). The balance is
  re-based to $100k after each reward, i.e. the guard is assumed re-baselined.
- Run until breach (FTMO rule) or freeze (guard buffer blocks entries for 30 days while flat).
- History: 12-month horizon, every weekday start through 2025-10-06. Monte Carlo: 36 months, 2,000 paths.
- Metrics: average monthly income while trading, median days until the account ends, breach % vs frozen %, total income,
  trades per month and per weekday.

## Caveats (apply to every number)
- In-sample: the EAs, settings and packages were chosen after seeing this history. Older ticks are generated (15% real
  ticks in the five-year sources).
- Sampled equity, not tick-level floating equity. Not a native simultaneous MT5 account test.
- FTMO's real rules and payout terms can change. Pass rates are scenario frequencies, not forecasts.

## Results (added after all 30 runs; full tables in TABLES.md, raw in RESULT-*.json)

**Parity:** funded Best Prop at 1% / 0.5% reproduces FTMO First Payout Study LOWRISK SET_1.00 / CAPS_0.50 exactly.

**Monte Carlo, $100k**

| Portfolio | Risk | Pass both ≤180 d | Median days to pass | Challenge breach | Funded income / month | Median days until it ends | How it ends | Trades / month |
|---|---|---:|---:|---:|---:|---:|---|---:|
| FTMO guarded 17 | 0.5 / 0.75 / 1% | 62 / 69 / 58% | 110 / 94 / 82 | 0% | $2,634 / $3,613 / $3,725 | 1,061 / 358 / 170 | freeze 50 / 89 / 100% | 61 / 48 / 33 |
| Current 14 + ORB, no guard | 0.5 / 0.75 / 1% | 76 / 81 / 64% | 98 / 74 / 53 | 4 / 13 / 35% | $3,618 / $5,736 / $7,319 | >1,092 / 358 / 86 | breach 45 / 89 / 100% | 85 |
| ORB-only, no guard | 0.5 / 0.75 / 1% | 0 / 0 / 2% | – | 0% | $310 / $469 / $642 | >1,092 | breach 0 / 5 / 18% | 9.6 |
| Prop ready 9 (DI ON) | 0.5 / 0.75 / 1% | 53 / 70 / 62% | 123 / 89 / 67 | 0% | $2,257 / $3,701 / $4,841 | 847 / 232 / 105 | freeze 59 / 97 / 100% | 39 / 38 / 35 |
| Best Prop 9 (DI OFF) | 0.5 / 0.75 / 1% | 49 / 63 / 54% | 122 / 87 / 60 | 0% | $2,192 / $3,625 / $5,109 | 529 / 148 / 79 | freeze 77 / 99 / 100% | 43 / 42 / 38 |

**Reading the table**
- Guarded accounts never breach in this model; they freeze when the static 92% buffer blocks entries. Unguarded accounts
  breach.
- ORB-only trades too little (about 10 trades a month) to make +10% within 180 days.
- The 0.75% / 1% rows for FTMO and Prop ready are hypothetical guards: their installers cap at 0.5%.
