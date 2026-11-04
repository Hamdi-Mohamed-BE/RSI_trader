# ftmo 1_step (built 2026-11-04)

Run `ftmo 1_step.bat`. It installs the 17 FTMO-guarded EAs (Current 14 + five ORBs at 0.5R) with a guard built for the
**FTMO 1-Step** rules. The rules were read from ftmo.com on 2026-11-03.

| FTMO 1-Step rule | Firm limit | What the guard does |
|---|---|---|
| Profit target | +10% | Challenge mode stops new entries at +10%, but only once the best-day rule holds |
| Max daily loss | 3% of the initial capital, from each midnight (Prague) balance | new entries only if the projected daily loss stays ≤ 2.5%; the day latches at 2.5%; an equity touch of 3% latches a breach stop |
| Max loss | 10%, end-of-day trailing: floor = highest midnight balance − 10%, only rises | new entries only if projected equity stays ≥ floor + 2%; an equity touch of the floor latches a breach stop |
| Best day (consistency) | best day ≤ 50% of total profit (not a breach; you must keep trading) | no new entries for the rest of the day once today's P&L reaches 4.5% |

Unchanged from the tested Prop Ready guard:
- per-trade cap = your chosen risk;
- open-risk caps 4.5 R total / 3 R per symbol (install question);
- 7 entries / 3 losing positions a day, 80% margin cap;
- SL required, no pending orders, account / symbol locks;
- the EA request is 1.5x your risk and the guard cuts it down.

Its own state key (`F1S`), so it never shares latches with Prop ready / any-broker on the same login. Every limit is an EA input
(`FTMO1*`).

**The installer asks:**
- phase: 1-Step Challenge or Funded / continuous;
- risk type and value (default 0.5% of equity);
- Nasdaq and USDJPY DI (default ON);
- Nasdaq stop version (default NEW ATR6);
- open-risk caps.

The account must be flat; every run starts a fresh baseline. It ends with a typed confirmation and a new 17-chart profile with
Algo Trading OFF. It never places orders.

**Limits — read before use:**
- Admission guard only: it never closes trades. A gap or several open losers can still breach FTMO's limits.
- After an FTMO reward (balance withdrawal) the guard blocks new entries (fail-closed ledger). Rerun the installer to start a new
  baseline.
- FTMO measures the trailing floor and the best day on its own server data. The guard rebuilds them from MT5 deal history at
  Prague midnight and counts deal net on the deal day.
- Not tested natively: the guard refuses the MT5 tester. Verified by compile (17/17, 0 errors / 0 warnings), package hashes,
  `-ValidateOnly`, and a Python model of the same rules (`Prop Portfolio Selection 2026-11-03/f1_profile.py`).

Build: `python build.py` (recompiles), `python build.py installer` (installer only). Sources: `Packages/FTMO-AnyBroker` (unchanged) and
the Best Prop 9 installer.

## Simulated results (Python model of this guard, FTMO17 stream, $100k, 2026-11-04)
| Risk | Pass ≤180 d (MC) | Breach | Stuck at the trailing buffer | Median days to pass |
|---|---:|---:|---:|---:|
| 0.5% (default) | 79% | 0% | 16% | 85 |
| 0.75% | 67% | 0% | 32% | 68 |
| 1% | 56% | 2.3% | 41% | 67 |

The full table is in `Prop Portfolio Selection 2026-11-03/RESULTS.md`. In-sample; not a forecast.

**Do not rerun the installer mid-challenge after a loss.** Each run starts a fresh baseline from the current balance, while FTMO's
floor keeps trailing the original high-water mark. A rerun therefore moves the guard floor below FTMO's.
