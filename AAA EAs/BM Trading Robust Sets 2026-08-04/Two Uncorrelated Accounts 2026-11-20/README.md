# Two Uncorrelated Accounts (2026-11-20)

Owner: "two uncorrelated profiles from the Best 1-Step profile, so when we buy 2 accounts it's almost 100% one of them passes; aim for 1 month".
`study.py` (plan frozen in its docstring) -> `RESULTS.json`. Data: Multi Firm Funded `INPUTS_N75.json` (recommended list, Nasdaq x0.75, weekend flat),
3,499 trades 2021-10 -> 2026-10, 5-minute marks. FTMO 1-Step rules, first attempt, no guard. Split + risks chosen on 740 DEV starts (2021-10 -> 2024-08);
reported on 480 TEST starts (2024-10 -> 2026-08, not used for choosing) and 2,000 Monte Carlo paths (same block draws for both accounts).

## P(at least one account passes) within 30 / 60 days, %

| Plan | Dev | Test | Monte Carlo | Both breach within 60 d (MC) |
|---|---|---|---|---|
| 1 account, full profile 0.75% | 12.8 / 34.7 | 38.5 / 79.2 | 20.9 / 52.5 | 3.6 |
| 1 account, full profile 1% | 20.1 / 31.6 | 39.6 / 65.2 | 24.3 / 46.2 | 41.2 |
| 2 accounts, full profile 1% + 1.5% | 25.3 / 33.5 | 47.7 / 67.7 | 32.4 / 50.6 | 37.6 |
| **2 accounts split by symbol: A = gold + UK100 + USDJPY 1.25%, B = Nasdaq 1.5%** | 33.5 / 56.6 | 51.5 / 79.4 | **42.6 / 67.2** | 13.4 |
| best split overall (A = 3WG+EMA3+ORBVC+SEL+JPY) | 39.3 / 60.4 | 48.1 / 76.0 | 40.0 / 61.7 | 21.4 |

- Accounts A (3WG, Asia, EMA3, ORB VP VC, UK100, USDJPY, RSI VWAP) and B (Nasdaq 5M, Overnight Bias ORB, Selective V3): daily correlation -0.012.
  Each alone within 30 days (MC): A 24.5%, B 23.8%; breach within 60 days A 29.8%, B 45.2%. Median day of the first pass 27.
- Splits that share a symbol across the two accounts had 80-142 opposite-position overlaps; FTMO forbids opposite trades across accounts, so only
  symbol-disjoint splits are usable. The chosen one is the best symbol-disjoint split on DEV.
- "Almost 100% within 1 month" is NOT reachable: the best 2-account plan gives ~43% (MC) / 52% (test) within 30 days and ~67-79% within 60 days.
- Not modelled: the guard (at 1.25-1.5% its 2.5% daily reserve would allow ~1 open trade at a time: fewer breaches, slower), news closes, $10k lot
  rounding. In-sample EA list. Fees: 2 x ~$92 ($10k FTMO 1-Step).
