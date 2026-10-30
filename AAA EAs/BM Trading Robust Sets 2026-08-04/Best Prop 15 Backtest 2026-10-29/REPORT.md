# Best Prop 15 vs Best Prop 9: in-sample / out-of-sample backtest (2026-10-29)

**What was tested:** the built Best Prop 15 package (Best Prop 9 + EMA3, 3 Way Gold, Gold Overnight, DMC Current XAU, DMC Fresh Reaction XAU, DMC Fresh Reaction US100) against Best Prop 9.

**How:** a Python replay of the five-year native Model-4 trade ledgers (2021-10-07 → 2026-10-06), run through the frozen Best Prop retest engine with the exact package guard on a $10,000 account:
- $100 risk per entry, $450 total open, $300 per symbol;
- $300 daily reserve, $9,200 entry buffer, $9,000 floor;
- 7 entries / 3 losses per day; lots rounded down.

`bp15.py`; raw output in `RESULTS.json` (1,035 s).

**Parity:** the Best Prop 9 rows reproduce the frozen retest `RESULTS.json` exactly: OOS challenge, continuous OOS and the 2,000-path Monte Carlo.

**Split:** the shared `data_split.py` planner.
- Development: 2021-10-07 → 2023-10-06.
- Validation: 2023-10-06 → 2024-10-06.
- OOS: the last two years, 2024-10-06 → 2026-10-06.

> **The OOS is previously viewed, not untouched.** Every EA and setting was chosen after this history existed. 3 Way Gold was optimised on 2021–2026: its untouched holdout was 2019–2021, and it lost there. Older ticks are generated (real ticks only from 2026-01). This is a replay of single-EA runs, not one simultaneous MT5 account. The numbers are historical scenarios, not forecasts.

## 1. FTMO 2-step challenge: every weekday start, 180-day horizon (recorded costs; fixed-cost stress in brackets)
| Period | Starts | Pass both ≤180 d, **BP15** / BP9 | Funded ≤90 d, BP15 / BP9 | Median days to funded, BP15 / BP9 | Breach | Stuck at buffer, BP15 / BP9 | Median trades per attempt, BP15 / BP9 |
|---|---:|---:|---:|---:|---:|---:|---:|
| Development 2021-23 (in-sample) | 392 | **36%** (16%) / 52% (35%) | 16% / 29% | 97 / 78 | 0% | 57% / 69% | 104 / 80 |
| Validation 2023-24 (in-sample) | 133 | **56%** (45%) / 53% (38%) | 17% / 42% | 119 / 75 | 0% | 69% / 62% | 89 / 77 |
| **OOS 2024-26** | 394 | **95%** (95%) / 90% (87%) | 70% / 69% | 71 / 64 | 0% | 22% / 20% | 76 / 69 |
| All 2021-26 | 1,176 | **63%** (54%) / 61% (52%) | 34% / 43% | 85 / 70 | 0% | 44% / 53% | 85 / 71 |
| **Monte Carlo** (2,000 four-week-block paths, 5-year pool) | 2,000 | **61%** (48%) / 56% (43%) | 30% / 39% | 92 / 71 | 0% | 49% / 53% | 93 / – |

Equity drawdown during attempts, p95: OOS $1,320 vs $1,058; Monte Carlo $1,287 vs $1,460. Worst day: $295 vs $257.

## 2. Continuous funded-style run (fresh $10k at each window start, no targets, same guard)
| Window | Portfolio | Return | PF | Win rate | Trades (/ month, / day) | Closed DD | Equity DD | Worst day | Positive months |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| Validation 2023-24 | **BP15** | **+56.6%** | 1.55 | 59.9% | 319 (26.5, 1.22) | $1,073 (10.7%) | $1,194 | $215 | 8/13 |
| | BP9 | +48.5% | 1.26 | 51.7% | 437 (36.3, 1.67) | $2,708 (27.1%) | $2,764 | $223 | 8/13 |
| **OOS 2024-26** | **BP15** | **+190.2%** | 1.61 | 61.1% | 1,032 (43.0, 1.98) | $870 (8.7%) | $1,320 | $295 | 22/25 |
| | BP9 | +170.8% | 1.52 | 56.8% | 908 (37.9, 1.74) | $1,292 (12.9%) | $1,375 | $257 | 21/25 |
| OOS, cost stress | BP15 | +165.7% | 1.52 | 60.4% | 1,029 | $910 | $1,362 | $326 | 22/25 |
| | BP9 | −7.7% (froze at the buffer after an early loss; without the buffer +145.5%, PF 1.43) | | | | | | | |
| Development / all from 2021-10-07 | both | **lost the first weeks** | | | | | | | |

**Development window detail:** BP15 was −7.6% after 50 trades and BP9 −7.4% after 11 trades. Both then froze at the $9,200 buffer. Without the buffer (diagnostic only), both reach the −10% floor within weeks: BP15 at −8.8% equity after 80 trades, BP9 at −10.1% after 15. A continuous run that starts on 2021-10-07 is therefore not informative. The challenge rows in section 1, which start on every weekday, are the in-sample evidence.

## 3. What the six added EAs contributed (BP15 continuous, net $ on $10k)
| EA | Validation 2023-24 | OOS 2024-26 |
|---|---:|---:|
| DMC Current XAU | +$341 | **+$3,054** |
| Gold Overnight Value Area | +$168 | +$1,454 |
| EMA3 | +$90 | +$1,189 |
| 3 Way Gold (3 modules) | +$856 | +$1,680 |
| DMC Fresh Reaction US100 | +$251 | +$645 |
| DMC Fresh Reaction XAU | −$14 (6 trades) | +$606 (5 trades) |

In the short development stretch, before the freeze, EMA3 lost $281 and Gold Overnight lost $80.

**Crowding:** with eight gold EAs, the $300 daily reserve blocked far more entries in BP15 (OOS 816 vs 155; validation 596 vs 51). There were 94 OOS entries below the minimum lot.

## Verdict
- **Return and drawdown:** BP15 earned more with smaller drawdowns in both the validation year and the OOS window. Validation PF was 1.55 vs 1.26 and closed DD 11% vs 27%; OOS was +190% vs +171%, with closed DD 9% vs 13%.
- **Pass rate:** slightly higher (63% vs 61% overall, Monte Carlo 61% vs 56%), and **stress-robust in OOS** (95% vs 87%).
- **Speed:** BP15 is **slower to funded**. The overall median is 85 vs 70 days and Monte Carlo 92 vs 71; only 34% vs 43% were funded within 90 days.
- **Development period:** BP15 is **clearly worse in 2021-23**: 36% vs 52% pass, and only 16% under cost stress.
- **Where the advantage comes from:** the validation and OOS years. That is the regime where 3 Way Gold was fitted and the gold EAs trended. It is not untouched evidence.
- **Overall:** **not a clear upgrade.** Choose BP15 for higher in-sample-recent returns and pass odds. Choose BP9 for faster funding and better behaviour in the weak 2021-23 regime. Neither is a forecast.

## Addendum: one-step challenge (owner: "what about 1 step phase challenges?")
**Script and tables:** `onestep.py`; full tables in `ONESTEP.md`; raw output in `ONESTEP-*.json`. It uses the same engine, streams, starts and costs as above.

**Rules:** FundedNext Stellar 1-Step, as in the owner's screenshot:
- +10% target in one phase;
- 3% daily loss from the day-start balance;
- **6% static** max loss (floor $9,400 on $10k);
- at least 2 trading days.

**Guards tested:**
- `INSTALLED-1.0`: the packages as built. Their $9,200 buffer sits *below* the 1-step floor, so it cannot protect it.
- `ONESTEP-1.0` / `-0.5`: a hypothetical 1-step guard (buffer $9,550, daily latch $250) at $100 / $50 per entry. This guard is **not built**.

**Monte Carlo, 1,000 paths (history over all starts in brackets):**

| Portfolio / guard | Pass ≤180 d | ≤30 d | ≤60 d | Breach | Stuck at the guard buffer | Median days to pass |
|---|---:|---:|---:|---:|---:|---:|
| **BP15 installed (1%)** | **73%** (70%) | 21% | 43% | **25%** (27%) | 2% | 51 (45) |
| BP9 installed (1%) | 66% (69%) | 28% | 51% | **33%** (31%) | 0% | **36** (35) |
| BP15 1-step guard 1% | 56% (55%) | 16% | 35% | 0% | 44% | 46 (50) |
| BP9 1-step guard 1% | 46% (54%) | 18% | 34% | 0% | 54% | 39 (43) |
| BP15 1-step guard 0.5% | 70% (64%) | 6% | 24% | 0% | 25% | 75 (65) |
| BP9 1-step guard 0.5% | 65% (71%) | 3% | 19% | 0% | 26% | 86 (76) |

**By period:**
- BP15 installed passed in 51% / 68% / **96%** of history starts in 2021-23 / 2023-24 / 2024-26.
- BP9 installed: 59% / 65% / 93%.

**Compared with FTMO 2-step:** the 1-step challenge is **about twice as fast**. BP9's median is 36 days vs 71 to funded on the 2-step; BP15's is 51 vs 92. But with the guards as built, about **1 in 4 (BP15) to 1 in 3 (BP9) attempts breach** the 6% floor.

**Trade-off of a 1-step-tuned guard:** it removes the breaches but freezes 25–54% of accounts at the buffer. Those are not breached, but they are dead unless re-baselined. Daily breaches were 0% in every variant: the $300 daily reserve keeps planned stop risk inside the 3% limit. Gaps, slippage and 3 Way Gold's missing intratrade marks are not modelled.
