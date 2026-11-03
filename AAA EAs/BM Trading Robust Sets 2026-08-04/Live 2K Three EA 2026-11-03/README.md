# $2,000 live account: Nasdaq 5M + XAU RSI VWAP + EMA3 at $80 per trade (2026-11-03)

Owner plan: about $2k of real funds within two months, only these three EAs, $80 risk per trade.
This is research only (Python replay of native data); nothing was installed. `sim.py` → `RESULTS.json`.

**Data:** five-year native MT5 Model 4 runs, 2021-10-06 → 2026-10-06. They record each trade's initial stop and costs, and the floating equity while it is open. Nasdaq 5M uses the deployed ATR6 stop.

**Sizing:**
- lots = $80 ÷ stop loss per lot, rounded UP to 0.01, minimum 0.01;
- on gold, the 0.01-lot step makes the average risk higher than $80;
- no guard; margin not modelled.

## Result: fixed $80, Nasdaq DI ON
| Period | Mean / month | Median / month | Worst month | Losing months | Trades / month (/ day) | PF | Win % |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-23 | +$123 | +$2 | −$685 | 48% | 21.9 (1.05) | 1.15 | 54.2 |
| 2023-24 | +$117 | +$262 | −$965 | 46% | 19.1 (0.95) | 1.15 | 49.6 |
| Last 2 years | +$300 | +$433 | −$616 | 20% | 22.0 (1.06) | 1.34 | 55.5 |
| Last 12 months | +$290 | +$155 | −$248 | 15% | 20.3 (1.01) | 1.34 | 55.7 |
| **All 5 years** | **+$198** | **+$232** | −$965 | 34% | 22.1 (1.03) | 1.23 | 53.9 |

**Average actual risk per trade:** $86.

**Starting at $2,000 in October 2021:**
- the account reaches $14,081 after five years (no compounding);
- the deepest closed drawdown is $2,025, and the deepest equity drawdown $2,062;
- the lowest equity, $931, came while the account was still small.

**Monte Carlo** (one year, 4,000 paths, 4-week blocks):
- year total p10 / median / p90: +$405 / +$2,436 / +$4,418, which is about $200 a month on average;
- losing year 6%;
- first 4 weeks p10 / median / p90: −$316 / +$173 / +$770;
- closed drawdown median $1,045, p95 $2,178;
- **the equity falls below $1,000 at some point in 13% of years, and below $1,500 in 30%.**

**By EA** (five years at $80):

| EA | Monthly average | Trades / month | PF |
|---|---:|---:|---:|
| Nasdaq 5M | +$106 | 14.4 | 1.18 |
| EMA3 | +$61 | 3.4 | 1.39 (average risk $105) |
| XAU RSI VWAP | +$31 | 4.2 | 1.29 (win 73%) |

## Comparisons
- **DI OFF at $80:** +$168 a month, losing year 11%, below $1,000 in 18%.
- **$40 per trade (2%), DI ON:** +$114 a month (last 2 years +$181), worst month −$502, closed drawdown p95 $1,161, below $1,000 in 2.1% of years.

## Constraint: the Nasdaq 5M EA cannot risk $80 on $2,000 today
- Its source caps risk at 1% of equity (`MathMin(InpRiskPercent,1.00)`), which is about $20 on $2,000.
- RSI VWAP and EMA3 size by % of equity with no cap: a 4% request gives $80 at $2,000 and then compounds.
- Running $80 on Nasdaq needs a code change (raise the cap or add fixed-money sizing).

## Caveats
- In-sample: these EAs and settings were chosen after viewing this history.
- 15% of the ticks are real; the rest are generated.
- The last two years were the strongest regime.
- Live slippage is not modelled.

## Four EAs: + Gold Overnight Value Area (`sim4.py` → `RESULTS-4EA.json`)
Gold Overnight Value Area has a real fixed-money mode (`InpRiskMode=1`, `InpFixedRiskMoney`), so $80 works on it today.

**Fixed $80, Nasdaq DI ON:**

| Period | Mean / month | Median / month | Worst month | Losing months | Trades / month (/ day) | PF | Win % |
|---|---:|---:|---:|---:|---:|---:|---:|
| 2021-23 | +$92 | +$132 | −$596 | 44% | 39.0 (1.87) | 1.08 | 59.5 |
| 2023-24 | +$97 | +$138 | −$827 | 46% | 34.7 (1.73) | 1.09 | 57.4 |
| Last 2 years | +$375 | +$398 | −$729 | 24% | 37.9 (1.82) | 1.33 | 61.9 |
| Last 12 months | +$422 | +$398 | −$173 | 23% | 35.8 (1.79) | 1.39 | 63.3 |
| **All 5 years** | **+$212** | **+$242** | −$827 | 34% | 38.9 (1.82) | 1.18 | 60.1 |

- **Gold Overnight's own contribution:** +$14 a month at $80; 16.8 trades a month, PF 1.05, win 68%.
- **Five-year run from $2,000:** ends at $14,949; closed drawdown $2,037; lowest equity $1,109.
- **Monte Carlo (one year):**
  - year total p10 / median / p90: +$324 / +$2,554 / +$4,752;
  - losing year 7%;
  - first 4 weeks p10 / median / p90: −$289 / +$210 / +$946;
  - closed drawdown p95 $2,259;
  - equity below $1,000 in 13.7% of years, below $1,500 in 36.6%.
- **$40 per trade:** +$118 a month (last 2 years +$214), below $1,000 in 2.8% of years.
- **DI OFF at $80:** +$182 a month, below $1,000 in 22% of years.
