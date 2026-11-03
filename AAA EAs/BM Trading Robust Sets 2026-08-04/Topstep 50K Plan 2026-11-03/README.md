# Topstep 50K Combine: XAU RSI VWAP + Nasdaq 5M, about $400 per trade (2026-11-03)

Owner plan: pass in 2–3 weeks. Target +$3,000 before the $2,000 trailing Maximum Loss Limit, with a $1,000 daily loss limit.
This is research only (Python replay); nothing was installed or traded. `sim.py` → `RESULTS.json`; the method is in the `sim.py` docstring.

**Rules modelled:**
- $2,000 MLL trailing the highest end-of-day balance and stopping at $50,000, checked against intraday equity;
- $1,000 daily loss limit: flatten and stop for that day, not a fail;
- 50% consistency rule;
- flat by 15:10 Chicago.

Third-party sources disagree on some details, so verify the rules on help.topstep.com.

**Signals and sizing:**
- From the five-year native CFD runs (2021-10 → 2026-10), converted to MNQ ($2/pt) and MGC (10 oz).
- Futures commissions replace CFD costs; no swap.
- Contracts = round($400 ÷ stop per contract), minimum 1; skip a signal if 1 contract risks more than $800.
- Each "attempt" starts on one weekday; about 1,234 starts.

## Recommended setup: RSI VWAP + Nasdaq 5M (ATR6 stop, forced flat at 15:10 Chicago), $400
| Time allowed | Pass | Fail (MLL) | Still open | Median days when passing |
|---|---:|---:|---:|---:|
| 2 weeks (10 trading days) | 3% (2021-23 3%, last 2 years 4%) | 7% | 90% | 8 |
| **3 weeks (15)** | **8%** (2021-23 6%, last 2 years 11%) | 15% | 78% | 11 |
| 12 weeks (60) | **39%** (2021-23 24%, 2023-24 26%, last 2 years 64%) | 46% (last 2 years 28%) | 15% | 29 |

- The median attempt places about 12 trades in 3 weeks and 23 in 12 weeks.
- 365 of the 881 Nasdaq trades and 50 of the 259 RSI trades were forced flat at 15:10 Chicago.

## Other options (pass / fail)
| Plan | Risk | 3 weeks | 12 weeks |
|---|---|---|---|
| Same plan | $500 | 10% / 26% | 41% / 56% |
| Same plan | $600 | 11% / 42% | 29% / 66% |
| Nasdaq day version (1.30% stop, close 15:55 New York) + RSI | $400 | 3% / 5% | 37% / 30% (last 2 years 62% / 14%) |
| Nasdaq ATR6 only | $400 | 6% / 11% | 37% / 45% |
| RSI VWAP only | any | 0% pass | too few trades and too small to reach $3,000 |

On the day version, one MNQ contract risks about $650 at current prices, so it oversizes at $400. At $300 its signals are skipped.

## Caveats
- In-sample.
- CFD prices stand in for futures (basis, spread and fills differ).
- Manual or copied execution adds delay.
- Counterfactual re-entries after a forced close are not reconstructed.
- The day version has no intraday marks (optimistic for the MLL).
